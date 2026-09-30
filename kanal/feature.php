<?php
declare(strict_types=1);
/*
 PORTMAN KANAL v1 — hosting tarafı (PHP 8.2).
 Yalnız şunları yapar: imzalı Meta webhook'undan izinli göndericilerin mesajlarını KUYRUĞA alır (state.json → inbound),
 Python üreticinin (worker.py, ayrı cron) yazdığı giden satırlarını Meta'ya GÖNDERİR (metin / PDF belge), teslimat durumlarını
 izler, panele yayınlar. OpenAI'ye bağlanmaz, çizim yapmaz. Öz-test satırı ya da imzalı webhook'tan gelmeyen ebeveyn asla gönderilmez.
 Belirsiz kalan POST otomatik tekrar edilmez (Görev 2/3 ile aynı ilke). Ana anahtar: settings.json → enabled.
 Gerekli mevcut fonksiyonlar: portman/lib.php (pm_config, pm_store, pm_ingest, pm_valid_signature, pm_read, pm_write, pm_remote, pm_graph,
 pm_contact) ve developer/config.php (numaralarOku, ayarlarOku, isteğe bağlı mesajKaydet).
*/
if (!defined('PM_KANAL_DIR')) define('PM_KANAL_DIR', __DIR__);
const PM_KANAL_SURUM = 'kanal-v1.3';   // v1.2 (İE-02): gelen satırda context_id · v1.3 (İE-04): reply_id; image ve interactive gönderimi
const PM_KANAL_STALE = 600;
const PM_KANAL_MAX_IMAGE = 5 * 1024 * 1024;          // WhatsApp görsel sınırı
// WhatsApp Cloud API etkileşimli mesaj sınırları (ajan da aynı sınırlarla üretir; burada gönderimden önce yeniden denetlenir)
const PM_KANAL_WA = ['buton' => 3, 'buton_baslik' => 20, 'buton_id' => 256, 'liste_dugme' => 20, 'liste_satir' => 10, 'satir_baslik' => 24,
                     'satir_aciklama' => 72, 'satir_id' => 200, 'bolum_baslik' => 24, 'govde' => 1024, 'altbilgi' => 60, 'baslik_metin' => 60, 'cta_metin' => 20];

function pm_kanal_settings(): array { $p = PM_KANAL_DIR.'/settings.json'; return is_file($p) ? pm_read($p) : []; }
function pm_kanal_enabled(): bool { return (pm_kanal_settings()['enabled'] ?? false) === true; }

/* state.json: {version, inbound{wamid→satır}, outbound{id→satır}} — Python worker.py ile aynı state.lock (flock) altında paylaşılır. */
function pm_kanal_store(callable $fn) {
    $f = fopen(PM_KANAL_DIR.'/state.lock', 'c');
    if (!$f || !flock($f, LOCK_EX)) throw new RuntimeException('kanal_state_lock');
    @chmod(PM_KANAL_DIR.'/state.lock', 0600);
    try {
        $p = PM_KANAL_DIR.'/state.json';
        $s = is_file($p) ? pm_read($p) : ['version' => 1, 'inbound' => [], 'outbound' => []];
        if (!is_array($s['inbound'] ?? null)) $s['inbound'] = [];
        if (!is_array($s['outbound'] ?? null)) $s['outbound'] = [];
        $r = $fn($s);
        pm_write($p, $s);
        return $r;
    } finally { flock($f, LOCK_UN); fclose($f); }
}
function pm_kanal_update(string $id, array $fields): void {
    pm_kanal_store(function (&$s) use ($id, $fields) {
        if (!isset($s['outbound'][$id])) return;
        $s['outbound'][$id] = array_replace($s['outbound'][$id], $fields, ['updated_at' => time()]);
    });
}

/* Kimlik: panelin numara kaydı (developer/config.php → numaralarOku). Patron = adı "Patron" olan kayıt; kod yazılmaz. */
function pm_kanal_numaralar(): array { $n = function_exists('numaralarOku') ? numaralarOku() : []; return is_array($n) ? $n : []; }
function pm_kanal_patron(): ?string {
    foreach (pm_kanal_numaralar() as $no => $p) {
        if (is_array($p) && mb_strtolower(trim((string)($p['ad'] ?? '')), 'UTF-8') === 'patron' && pm_contact((string)$no)) return (string)$no;
    }
    return null;
}
function pm_kanal_bayi(string $sender): ?array {
    $p = pm_kanal_numaralar()[$sender] ?? null;
    if (!is_array($p)) return null;
    $ad = trim((string)($p['ad'] ?? '')); $patron = mb_strtolower($ad, 'UTF-8') === 'patron';
    return ['kod' => $patron ? 'PATRON' : (string)($p['kod'] ?? ('B'.substr($sender, -4))), 'ad' => $ad !== '' ? $ad : $sender,
            'firma' => (string)($p['firma'] ?? ''), 'rol' => $patron ? 'patron' : 'bayi'];
}
function pm_kanal_allowed(string $sender, array $settings): bool {
    $mode = (string)($settings['mode'] ?? 'patron'); $b = pm_kanal_bayi($sender);
    if ($mode === 'hepsi') return true;
    if ($mode === 'kayitli') return $b !== null;
    return $b !== null && $b['rol'] === 'patron';
}
function pm_kanal_text(array $m): string {
    $kind = (string)($m['type'] ?? ''); $media = is_array($m[$kind] ?? null) ? $m[$kind] : [];
    return match ($kind) {
        'text' => (string)($m['text']['body'] ?? ''),
        'button' => (string)($m['button']['text'] ?? ''),
        'interactive' => (string)($m['interactive']['button_reply']['title'] ?? $m['interactive']['list_reply']['title'] ?? ''),
        'image', 'document', 'video', 'audio', 'sticker' => (string)($media['caption'] ?? $media['filename'] ?? ''),
        'location' => 'Konum: '.($media['name'] ?? $media['address'] ?? '').' '.($media['latitude'] ?? '').', '.($media['longitude'] ?? ''),
        default => '',
    };
}

/* İE-04: etkileşimli cevabın kimliği: interactive.button_reply.id | interactive.list_reply.id | button.payload (şablon butonu). */
function pm_kanal_reply(array $m): array {
    $type = (string)($m['type'] ?? ''); $id = null; $kind = null;
    if ($type === 'interactive' && is_array($m['interactive'] ?? null)) {
        foreach (['button_reply', 'list_reply'] as $k) if (is_array($m['interactive'][$k] ?? null) && isset($m['interactive'][$k]['id'])) { $id = (string)$m['interactive'][$k]['id']; $kind = $k; }
    } elseif ($type === 'button' && is_array($m['button'] ?? null) && isset($m['button']['payload'])) { $id = (string)$m['button']['payload']; $kind = 'button'; }
    if ($id === null || $id === '' || strlen($id) > 256 || preg_match('/[\x00-\x1F]/', $id)) return [null, null];
    return [$id, $kind];
}

/* İE-04: satırın dosyası (PDF, PNG, JPEG): projects/ altında, kayıtlı özetle aynı, türü başlığından. Dönen: [gerçek yol, mime]. */
function pm_kanal_dosya(array $r, array $izinli): array {
    $path = (string)($r['file'] ?? ''); $real = $path !== '' ? realpath($path) : false;
    if ($real === false || !str_starts_with($real, PM_KANAL_DIR.'/projects/') || !is_file($real) || filesize($real) < 1) throw new RuntimeException('local_file_invalid');
    if (!empty($r['sha256']) && !hash_equals((string)$r['sha256'], hash_file('sha256', $real))) throw new RuntimeException('local_file_changed');
    $bas = (string)file_get_contents($real, false, null, 0, 8);
    $mime = str_starts_with($bas, '%PDF-') ? 'application/pdf' : (str_starts_with($bas, "\x89PNG\r\n\x1a\n") ? 'image/png' : (str_starts_with($bas, "\xFF\xD8\xFF") ? 'image/jpeg' : ''));
    if ($mime === '' || !in_array($mime, $izinli, true)) throw new RuntimeException($mime === '' ? 'file_type_unknown' : 'file_type_not_allowed');
    if ($mime === 'application/pdf' && filesize($real) > 25 * 1024 * 1024) throw new RuntimeException('pdf_too_large');
    if ($mime !== 'application/pdf' && filesize($real) > PM_KANAL_MAX_IMAGE) throw new RuntimeException('image_too_large');
    return [$real, $mime];
}

/* İE-04: medya yükleme (bir kez; media_id satırda saklanır, yeniden denemede yeniden yüklenmez). */
function pm_kanal_medya(string $id, array $r, string $real, string $mime, array $cfg, string $anahtar = 'media_id'): string {
    $media = (string)($r[$anahtar] ?? '');
    if (ctype_digit($media) && $media !== '') return $media;
    pm_kanal_update($id, ['state' => 'uploading', 'attempts' => ($r['attempts'] ?? 0) + 1, 'send_started_at' => time()]);
    $upload = pm_remote('https://graph.facebook.com/'.$cfg['graph_version'].'/'.$cfg['phone_number_id'].'/media', $cfg['access_token'], 'POST',
        ['messaging_product' => 'whatsapp', 'type' => $mime, 'file' => new CURLFile($real, $mime, (string)($r['filename'] ?? basename($real)))]);
    $media = (string)($upload['id'] ?? '');
    if (!ctype_digit($media) || $media === '') throw new RuntimeException('media_response');
    pm_kanal_update($id, [$anahtar => $media]);
    return $media;
}

/* İE-04: etkileşimli mesajın Meta payload'ı; sınırlar burada da denetlenir (aşan satır gönderilmez: interactive_invalid). */
function pm_kanal_interactive(array $r, ?string $headerMediaId): array {
    $L = PM_KANAL_WA; $i = is_array($r['interactive'] ?? null) ? $r['interactive'] : [];
    $tip = (string)($i['type'] ?? ''); $govde = trim((string)($i['body']['text'] ?? $r['body'] ?? ''));
    $kes = fn($v, $n) => mb_strlen($v, 'UTF-8') <= $n;
    if (!in_array($tip, ['button', 'list', 'cta_url'], true)) throw new RuntimeException('interactive_invalid: type');
    if ($govde === '' || !$kes($govde, $L['govde'])) throw new RuntimeException('interactive_invalid: body');
    $out = ['type' => $tip, 'body' => ['text' => $govde]];
    if (isset($i['footer']['text']) && trim((string)$i['footer']['text']) !== '') {
        if (!$kes((string)$i['footer']['text'], $L['altbilgi'])) throw new RuntimeException('interactive_invalid: footer');
        $out['footer'] = ['text' => (string)$i['footer']['text']];
    }
    $h = is_array($i['header'] ?? null) ? $i['header'] : null;
    if ($h !== null) {
        if (($h['type'] ?? '') === 'image') {
            if ($tip === 'list') throw new RuntimeException('interactive_invalid: list header image');
            if ($headerMediaId === null) throw new RuntimeException('interactive_invalid: header media');
            $out['header'] = ['type' => 'image', 'image' => ['id' => $headerMediaId]];
        } elseif (($h['type'] ?? '') === 'text') {
            if (!$kes((string)($h['text'] ?? ''), $L['baslik_metin'])) throw new RuntimeException('interactive_invalid: header text');
            $out['header'] = ['type' => 'text', 'text' => (string)$h['text']];
        } else throw new RuntimeException('interactive_invalid: header type');
    }
    $a = is_array($i['action'] ?? null) ? $i['action'] : [];
    if ($tip === 'button') {
        $butonlar = is_array($a['buttons'] ?? null) ? $a['buttons'] : []; $ids = [];
        if (count($butonlar) < 1 || count($butonlar) > $L['buton']) throw new RuntimeException('interactive_invalid: buttons');
        $out['action'] = ['buttons' => []];
        foreach ($butonlar as $b) {
            $rid = (string)($b['reply']['id'] ?? $b['id'] ?? ''); $baslik = (string)($b['reply']['title'] ?? $b['title'] ?? '');
            if ($rid === '' || !$kes($rid, $L['buton_id']) || $baslik === '' || !$kes($baslik, $L['buton_baslik']) || isset($ids[$rid])) throw new RuntimeException('interactive_invalid: button');
            $ids[$rid] = true; $out['action']['buttons'][] = ['type' => 'reply', 'reply' => ['id' => $rid, 'title' => $baslik]];
        }
    } elseif ($tip === 'list') {
        $dugme = (string)($a['button'] ?? ''); $n = 0; $ids = []; $bolumler = [];
        if ($dugme === '' || !$kes($dugme, $L['liste_dugme'])) throw new RuntimeException('interactive_invalid: list button');
        foreach ((is_array($a['sections'] ?? null) ? $a['sections'] : []) as $sec) {
            $rows = [];
            foreach ((is_array($sec['rows'] ?? null) ? $sec['rows'] : []) as $row) {
                $rid = (string)($row['id'] ?? ''); $baslik = (string)($row['title'] ?? ''); $ac = (string)($row['description'] ?? '');
                if ($rid === '' || !$kes($rid, $L['satir_id']) || $baslik === '' || !$kes($baslik, $L['satir_baslik']) || !$kes($ac, $L['satir_aciklama']) || isset($ids[$rid])) throw new RuntimeException('interactive_invalid: row');
                $ids[$rid] = true; $n++; $x = ['id' => $rid, 'title' => $baslik]; if ($ac !== '') $x['description'] = $ac; $rows[] = $x;
            }
            if ($rows) { $t = (string)($sec['title'] ?? ''); if (!$kes($t, $L['bolum_baslik'])) throw new RuntimeException('interactive_invalid: section'); $bolumler[] = ($t !== '' ? ['title' => $t] : []) + ['rows' => $rows]; }
        }
        if ($n < 1 || $n > $L['liste_satir']) throw new RuntimeException('interactive_invalid: rows');
        $out['action'] = ['button' => $dugme, 'sections' => $bolumler];
    } else {
        $p = is_array($a['parameters'] ?? null) ? $a['parameters'] : []; $url = (string)($p['url'] ?? ''); $metin = (string)($p['display_text'] ?? '');
        if ($metin === '' || !$kes($metin, $L['cta_metin']) || !preg_match('#^https://[^\s"\'<>]{4,1900}$#u', $url)) throw new RuntimeException('interactive_invalid: cta_url');
        $out['action'] = ['name' => 'cta_url', 'parameters' => ['display_text' => $metin, 'url' => $url]];
    }
    return $out;
}

/* Webhook: imza doğrulanır, ana kayda (store.json) yazılır, izinli göndericinin mesajı kuyruğa alınır; sahiplenilenler döner (sohbet botuna gitmez). */
function pm_kanal_capture(string $raw, string $signature): array {
    $owned = []; $settings = pm_kanal_settings();
    if (($settings['enabled'] ?? false) !== true) return $owned;
    $cfg = pm_config();
    if (strlen($raw) > 2097152 || !pm_valid_signature($raw, $signature, $cfg)) return $owned;
    $p = json_decode($raw, true);
    if (!is_array($p) || ($p['object'] ?? '') !== 'whatsapp_business_account') return $owned;
    pm_store(function (&$s) use ($p, $cfg) { pm_ingest($s, $p, $cfg); });
    $simdi = time(); $yeni = [];
    foreach (($p['entry'] ?? []) as $entry) foreach (($entry['changes'] ?? []) as $change) {
        $v = $change['value'] ?? [];
        if (($change['field'] ?? '') !== 'messages' || ($v['metadata']['phone_number_id'] ?? '') !== $cfg['phone_number_id']) continue;
        foreach (($v['statuses'] ?? []) as $st) { try { pm_kanal_status($st, $cfg); } catch (Throwable $e) { error_log('Portman kanal status: '.$e->getMessage()); } }
        $names = [];
        foreach (($v['contacts'] ?? []) as $c) $names[(string)($c['wa_id'] ?? '')] = (string)($c['profile']['name'] ?? '');
        foreach (($v['messages'] ?? []) as $m) {
            $mid = (string)($m['id'] ?? ''); $from = (string)($m['from'] ?? ''); $type = (string)($m['type'] ?? ''); $ts = (int)($m['timestamp'] ?? 0);
            if (!str_starts_with($mid, 'wamid.') || strlen($mid) > 300 || !pm_contact($from) || $type === 'reaction') continue;
            if (function_exists('pm_cloud_owned') && pm_cloud_owned($m)) continue;          // Görev 3 açıksa onun komutu
            if (function_exists('pm_house_is_command') && pm_house_is_command($m)) continue; // Görev 2 komutu
            if (function_exists('pm_pdf_is_command') && pm_pdf_is_command($m)) continue;     // Görev 1 komutu
            if (!pm_kanal_allowed($from, $settings)) continue;
            $owned[$mid] = true;
            if ($ts < (int)($settings['enabled_at'] ?? 0) || $ts > $simdi + 60 || $simdi - $ts >= 900) continue; // eski / geç tekrar teslim: kuyruğa alma
            $bayi = pm_kanal_bayi($from); $media = is_array($m[$type] ?? null) ? $m[$type] : [];
            // İE-02: bayi bir mesajı alıntılayarak cevap verdiyse alıntılanan mesajın kimliği (onayı doğru revizyona bağlamak için)
            $ctx = is_array($m['context'] ?? null) ? (string)($m['context']['id'] ?? '') : '';
            // İE-04: buton ya da liste cevabının KİMLİĞİ (görünen başlık text'te kalır; ajan yalnız kimliği seçim sayar)
            [$reply, $replyKind] = pm_kanal_reply($m);
            $yeni[$mid] = ['id' => $mid, 'context_id' => (str_starts_with($ctx, 'wamid.') && strlen($ctx) <= 300) ? $ctx : null,
                'reply_id' => $reply, 'reply_kind' => $replyKind,
                'sender' => $from, 'name' => $names[$from] ?? '', 'role' => $bayi['rol'] ?? 'bayi', 'bayi' => $bayi,
                'type' => $type, 'text' => mb_substr(pm_kanal_text($m), 0, 4000), 'media_id' => $media['id'] ?? null, 'filename' => $media['filename'] ?? null,
                'timestamp' => $ts, 'received_at' => $simdi, 'phone_number_id' => $cfg['phone_number_id'], 'source' => 'Meta imzalı webhook',
                'mode' => (string)($settings['mode'] ?? 'patron'), 'state' => 'queued', 'attempts' => 0, 'result' => null, 'error' => null, 'updated_at' => $simdi];
        }
    }
    if ($yeni) pm_kanal_store(function (&$s) use ($yeni) { foreach ($yeni as $id => $row) if (!isset($s['inbound'][$id])) $s['inbound'][$id] = $row; });
    return $owned;
}

/* Meta durum bildirimi (sent/delivered/read/failed) → giden satırı; eşleşme wamid ya da biz_opaque_callback_data ile. */
function pm_kanal_status(array $status, array $cfg): void {
    $mid = (string)($status['id'] ?? ''); $recipient = (string)($status['recipient_id'] ?? ''); $kind = (string)($status['status'] ?? '');
    if (!str_starts_with($mid, 'wamid.') || !in_array($kind, ['sent', 'delivered', 'read', 'failed'], true)) return;
    $opaque = $status['biz_opaque_callback_data'] ?? null;
    pm_kanal_store(function (&$s) use ($status, $mid, $recipient, $kind, $opaque, $cfg) {
        $ranks = ['accepted' => 0, 'sent' => 1, 'failed' => 2, 'delivered' => 3, 'read' => 4];
        foreach ($s['outbound'] as $id => &$r) {
            if (!empty($r['self_test']) || ($r['phone_number_id'] ?? $cfg['phone_number_id']) !== $cfg['phone_number_id']) continue;
            $byWamid = ($r['wamid'] ?? null) === $mid;
            $byOpaque = is_string($opaque) && $opaque === $id && ($r['wamid'] ?? null) === null && ($r['attempts'] ?? 0) >= 1;
            if (!$byWamid && !$byOpaque) continue;
            if (($r['to_resolved'] ?? null) !== null && $r['to_resolved'] !== $recipient) continue;
            $r['wamid'] = $mid;
            $event = ['status' => $kind, 'timestamp' => (int)($status['timestamp'] ?? 0), 'received_at' => time(),
                'errors' => array_map(fn($e) => ['code' => (int)($e['code'] ?? 0), 'title' => mb_substr((string)($e['title'] ?? ''), 0, 120)], $status['errors'] ?? [])];
            $r['delivery_events'][hash('sha256', json_encode([$mid, $kind, $event['timestamp']]))] = $event;
            if (($r['delivery_state'] ?? null) === null || $ranks[$kind] >= ($ranks[$r['delivery_state']] ?? 0)) { $r['delivery_state'] = $kind; $r['state'] = $kind; }
            if (($r['request_accepted_at'] ?? null) === null) { $r['request_accepted_at'] = time(); $r['acceptance_source'] = 'signed_status_webhook'; }
            if ($kind === 'failed') $r['error'] = 'Meta teslimat hatası: '.implode('; ', array_map(fn($e) => $e['code'].' '.$e['title'], $event['errors']));
            $r['updated_at'] = time();
        } unset($r);
    });
}

/* Alıcının bu hatta son gelen mesajı (24 saatlik serbest yanıt penceresi için). */
function pm_kanal_son_gelen(string $numara, array $cfg): int {
    return (int)pm_store(function (&$d) use ($numara, $cfg) {
        $son = 0;
        foreach ($d['messages'] as $m) if (($m['sender'] ?? '') === $numara && ($m['phone_number_id'] ?? '') === $cfg['phone_number_id'] && (int)$m['timestamp'] <= time()) $son = max($son, (int)$m['timestamp']);
        return $son;
    });
}

/* Tek giden satırı gönder. Belirsiz kalan messages POST'u tekrar edilmez. */
function pm_kanal_send(string $id, array $r, array $cfg, array $settings): void {
    if (!empty($r['self_test']) || !str_starts_with((string)($r['inbound_id'] ?? ''), 'wamid.')) throw new RuntimeException('test_cannot_send');
    if (!pm_kanal_enabled() || empty($cfg['connection_verified_at'])) throw new RuntimeException('disabled_or_unverified');
    $in = pm_kanal_store(fn(&$s) => $s['inbound'][$r['inbound_id']] ?? null);
    if (!$in || ($in['source'] ?? '') !== 'Meta imzalı webhook' || ($in['phone_number_id'] ?? '') !== $cfg['phone_number_id']) throw new RuntimeException('inbox_not_verified');
    $bildirim = ($r['to'] ?? '') === 'PATRON';
    $to = $bildirim ? pm_kanal_patron() : (string)$r['to'];
    if (!$to || !pm_contact($to)) throw new RuntimeException('recipient_unknown');
    if (!$bildirim && $to !== $in['sender']) throw new RuntimeException('recipient_mismatch');
    $son = $bildirim ? pm_kanal_son_gelen($to, $cfg) : (int)$in['timestamp'];
    if (!$son || time() - $son >= 86400) throw new RuntimeException('reply_window_closed');
    $kind = (string)($r['kind'] ?? 'text'); $attempted = false;
    try {
        $payload = ['messaging_product' => 'whatsapp', 'recipient_type' => 'individual', 'to' => $to, 'biz_opaque_callback_data' => $id];
        if ($kind === 'document') {
            [$real, $mime] = pm_kanal_dosya($r, ['application/pdf']);
            pm_kanal_update($id, ['to_resolved' => $to]);
            $media = pm_kanal_medya($id, $r, $real, $mime, $cfg);
            $payload['type'] = 'document';
            $payload['document'] = ['id' => $media, 'filename' => (string)$r['filename']];
            if (trim((string)($r['body'] ?? '')) !== '') $payload['document']['caption'] = mb_substr((string)$r['body'], 0, 1000);
        } elseif ($kind === 'image') {                                   // İE-04: plan görseli (PNG/JPEG ≤5 MB)
            [$real, $mime] = pm_kanal_dosya($r, ['image/png', 'image/jpeg']);
            pm_kanal_update($id, ['to_resolved' => $to]);
            $media = pm_kanal_medya($id, $r, $real, $mime, $cfg);
            $payload['type'] = 'image'; $payload['image'] = ['id' => $media];
            if (trim((string)($r['body'] ?? '')) !== '') $payload['image']['caption'] = mb_substr((string)$r['body'], 0, 1024);
        } elseif ($kind === 'interactive') {                             // İE-04: buton, liste, bağlantı butonu (başlıkta görsel olabilir)
            $headerMedia = null;
            if ((($r['interactive']['header']['type'] ?? '') === 'image')) {
                [$real, $mime] = pm_kanal_dosya($r, ['image/png', 'image/jpeg']);
                pm_kanal_update($id, ['to_resolved' => $to]);
                $headerMedia = pm_kanal_medya($id, $r, $real, $mime, $cfg);
            }
            $payload['type'] = 'interactive'; $payload['interactive'] = pm_kanal_interactive($r, $headerMedia);
        } else {
            if (trim((string)($r['body'] ?? '')) === '') throw new RuntimeException('empty_text');
            $payload['type'] = 'text'; $payload['text'] = ['body' => mb_substr((string)$r['body'], 0, 4000), 'preview_url' => false];
        }
        if (!pm_kanal_enabled()) throw new RuntimeException('disabled_before_send');
        pm_kanal_update($id, ['state' => 'sending', 'attempts' => ($r['attempts'] ?? 0) + 1, 'to_resolved' => $to, 'send_started_at' => time(), 'graph_version' => $cfg['graph_version']]);
        $attempted = true;
        $res = pm_graph($cfg['phone_number_id'].'/messages', 'POST', $payload, $cfg);
        $wamid = $res['messages'][0]['id'] ?? null; $ok = false;
        foreach (($res['contacts'] ?? []) as $c) if (($c['input'] ?? null) === $to && pm_contact((string)($c['wa_id'] ?? ''))) $ok = true;
        if (!is_string($wamid) || !str_starts_with($wamid, 'wamid.') || !$ok) throw new RuntimeException('send_response_uncertain');
        pm_kanal_store(function (&$s) use ($id, $wamid) {
            $row = &$s['outbound'][$id];
            if (($row['wamid'] ?? null) !== null && $row['wamid'] !== $wamid) throw new RuntimeException('wamid_mismatch');
            $row['wamid'] = $wamid; $row['request_accepted_at'] = time(); $row['acceptance_source'] = 'messages_api';
            $row['state'] = $row['delivery_state'] ?? 'accepted'; $row['error'] = null; $row['updated_at'] = time();
        });
    } catch (Throwable $e) {
        $msg = $e->getMessage();
        pm_kanal_store(function (&$s) use ($id, $attempted, $msg) {
            $row = &$s['outbound'][$id];
            if (($row['request_accepted_at'] ?? null) !== null) return;
            $row['state'] = $attempted ? 'uncertain' : 'upload_failed';
            $row['error'] = ($attempted ? 'Gönderim sonucu belirsiz; otomatik tekrar yok. ' : 'Yükleme/doğrulama başarısız; gönderilmedi. ').mb_substr($msg, 0, 160);
            $row['updated_at'] = time();
        });
        throw $e;
    }
}

/* Dakikalık tik: takılı satırları belirsiz say, bekleyenleri sırayla gönder, panele yayınla, sağlık yaz. */
function pm_kanal_tick(): void {
    $lock = fopen(PM_KANAL_DIR.'/tick.lock', 'c');
    if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) return;
    @chmod(PM_KANAL_DIR.'/tick.lock', 0600);
    $sent = 0; $failed = 0; $held = 0; $err = null; $settings = pm_kanal_settings();
    try {
        if (($settings['enabled'] ?? false) !== true) return;
        $cfg = pm_config();
        pm_kanal_store(function (&$s) {
            foreach ($s['outbound'] as &$r) {
                if (in_array($r['state'] ?? '', ['uploading', 'sending'], true) && ($r['updated_at'] ?? 0) < time() - PM_KANAL_STALE) {
                    $r['state'] = $r['state'] === 'sending' ? 'uncertain' : 'upload_failed';
                    $r['error'] = 'Önceki işlem teyit edilmeden bitti; otomatik tekrar yok.'; $r['updated_at'] = time();
                }
            } unset($r);
        });
        $rows = pm_kanal_store(fn(&$s) => $s['outbound']);
        uasort($rows, fn($a, $b) => [$a['created_at'] ?? 0, $a['inbound_id'] ?? '', $a['seq'] ?? 0] <=> [$b['created_at'] ?? 0, $b['inbound_id'] ?? '', $b['seq'] ?? 0]);
        $deadline = time() + 40;
        foreach ($rows as $id => $r) {
            if (time() > $deadline) break;
            $retry = ($r['state'] ?? '') === 'upload_failed' && ($r['attempts'] ?? 0) < 2 && in_array($r['kind'] ?? '', ['document', 'image', 'interactive'], true)
                     && !str_starts_with((string)($r['error'] ?? ''), 'Yükleme/doğrulama başarısız; gönderilmedi. interactive_invalid');
            if (($r['state'] ?? '') !== 'pending' && !$retry) continue;
            if (($settings['dry_run'] ?? false) === true) { pm_kanal_update($id, ['state' => 'held', 'error' => 'dry_run: gönderilmedi (sonradan da gönderilmez)']); $held++; continue; }
            try { pm_kanal_send($id, $r, $cfg, $settings); $sent++; }
            catch (Throwable $e) {
                $failed++;
                if (in_array($e->getMessage(), ['reply_window_closed', 'recipient_unknown', 'test_cannot_send', 'recipient_mismatch', 'inbox_not_verified'], true))
                    pm_kanal_update($id, ['state' => 'held', 'error' => 'Gönderilmedi: '.$e->getMessage()]);
            }
        }
        pm_kanal_publish($settings);
    } catch (Throwable $e) { $err = mb_substr($e->getMessage(), 0, 200); }
    finally {
        try {
            $sayim = pm_kanal_store(function (&$s) {
                $c = ['inbound' => [], 'outbound' => []];
                foreach ($s['inbound'] as $r) $c['inbound'][$r['state'] ?? '?'] = ($c['inbound'][$r['state'] ?? '?'] ?? 0) + 1;
                foreach ($s['outbound'] as $r) $c['outbound'][$r['state'] ?? '?'] = ($c['outbound'][$r['state'] ?? '?'] ?? 0) + 1;
                return $c;
            });
            pm_write(PM_KANAL_DIR.'/health.json', ['checked_at' => time(), 'surum' => PM_KANAL_SURUM, 'server' => gethostname(), 'php' => PHP_VERSION,
                'enabled' => ($settings['enabled'] ?? false) === true, 'dry_run' => ($settings['dry_run'] ?? false) === true, 'mode' => $settings['mode'] ?? null,
                'sent' => $sent, 'failed' => $failed, 'held' => $held, 'error' => $err, 'counts' => $sayim,
                'python_worker_checked_at' => (is_file(PM_KANAL_DIR.'/worker-health.json') ? (pm_read(PM_KANAL_DIR.'/worker-health.json')['checked_at'] ?? null) : null)]);
            $pf = PM_KANAL_DIR.'/preflight.json';
            if (!is_file($pf) || filemtime($pf) < time() - 600) pm_kanal_preflight();
        } catch (Throwable $e) { error_log('Portman kanal health: '.$e->getMessage()); }
        flock($lock, LOCK_UN); fclose($lock);
    }
}

/* Panele yayın: store.json → outgoing (Görev 3 ile aynı biçim); isteğe bağlı panelin sohbet kaydına (mesajKaydet) tek sefer. */
function pm_kanal_publish(array $settings): void {
    $rows = pm_kanal_store(fn(&$s) => $s['outbound']);
    pm_store(function (&$d) use ($rows) {
        foreach ($rows as $id => $r) {
            if (!empty($r['self_test']) || ($r['request_accepted_at'] ?? null) === null) continue;
            $medya = in_array($r['kind'], ['document', 'image'], true) || !empty($r['file']);
            $d['outgoing'][$id] = ['request_id' => $id, 'parent_message_id' => $r['inbound_id'], 'recipient' => $r['to_resolved'] ?? $r['to'],
                'kind' => $medya ? 'document' : 'text', 'body' => pm_kanal_panel_metni($r), 'filename' => $r['filename'] ?? null,
                'sha256' => $r['sha256'] ?? null, 'local_file' => null, 'mime' => $r['mime'] ?? null, 'transport' => $medya ? 'media' : 'text',
                'state' => $r['state'], 'timestamp' => $r['created_at'], 'updated' => $r['updated_at'], 'phone_number_id' => $r['phone_number_id'] ?? null,
                'wamid' => $r['wamid'], 'media_id' => $r['media_id'] ?? null, 'error' => $r['error'], 'request_accepted_at' => $r['request_accepted_at'],
                'delivery_state' => $r['delivery_state'] ?? null, 'kanal_kind' => $r['kind'],
                'evidence' => 'İmzalı WhatsApp → Portman kanal (Beyin+Motor, hosting) → '.(['document' => 'PDF', 'image' => 'görsel', 'interactive' => 'etkileşimli mesaj'][$r['kind']] ?? 'metin')];
        }
    });
    if (($settings['panel_kaydi'] ?? true) !== true || !function_exists('mesajKaydet')) return;
    foreach ($rows as $id => $r) {
        if (!empty($r['self_test']) || !empty($r['panel_logged']) || !is_string($r['wamid'] ?? null)) continue;
        $icerik = $r['kind'] === 'document' ? '📎 '.($r['filename'] ?? 'belge.pdf').(trim((string)$r['body']) !== '' ? ' — '.$r['body'] : '')
                : ($r['kind'] === 'image' ? '🖼 '.($r['filename'] ?? 'gorsel.png').(trim((string)$r['body']) !== '' ? ' — '.$r['body'] : '') : pm_kanal_panel_metni($r));
        try { mesajKaydet($r['to_resolved'] ?? $r['to'], 'Portman', 'giden', 'text', $icerik, $r['wamid'], ['ai' => true, 'portman' => 'kanal']); }
        catch (Throwable $e) { error_log('Portman kanal panel kaydı: '.$e->getMessage()); }
        pm_kanal_update($id, ['panel_logged' => true]);
    }
}

/* İE-04: panel ve sohbet kaydı için etkileşimli mesajın metni: gövde + buton/liste başlıkları (kimlikler yazılmaz). */
function pm_kanal_panel_metni(array $r): string {
    $govde = (string)($r['body'] ?? '');
    if (($r['kind'] ?? '') !== 'interactive' || !is_array($r['interactive'] ?? null)) return $govde;
    $i = $r['interactive']; $a = is_array($i['action'] ?? null) ? $i['action'] : []; $ek = [];
    foreach ((is_array($a['buttons'] ?? null) ? $a['buttons'] : []) as $b) $ek[] = (string)($b['reply']['title'] ?? $b['title'] ?? '');
    foreach ((is_array($a['sections'] ?? null) ? $a['sections'] : []) as $sec) foreach ((is_array($sec['rows'] ?? null) ? $sec['rows'] : []) as $row) $ek[] = (string)($row['title'] ?? '');
    if (isset($a['parameters']['display_text'])) $ek[] = (string)$a['parameters']['display_text'].' → '.(string)($a['parameters']['url'] ?? '');
    return $govde.($ek ? ' ['.implode(' | ', array_filter($ek)).']' : '');
}

/* Kurulum ön kontrolü: sır yazmaz (yalnız var/yok); preflight.json. Hiçbir şey göndermez. */
function pm_kanal_preflight(): array {
    $settings = pm_kanal_settings(); $out = ['checked_at' => time(), 'surum' => PM_KANAL_SURUM, 'php' => PHP_VERSION, 'dir' => PM_KANAL_DIR];
    foreach (['pm_config', 'pm_store', 'pm_ingest', 'pm_valid_signature', 'pm_graph', 'pm_remote', 'numaralarOku', 'ayarlarOku', 'mesajKaydet',
              'pm_cloud_owned', 'pm_house_is_command', 'pm_pdf_is_command'] as $fn) $out['functions'][$fn] = function_exists($fn);
    try {
        $cfg = pm_config();
        $out['meta'] = ['phone_number_id' => $cfg['phone_number_id'] ?? null, 'graph_version' => $cfg['graph_version'] ?? null,
            'access_token_present' => !empty($cfg['access_token']), 'app_secret_present' => !empty($cfg['app_secret']), 'connection_verified_at' => $cfg['connection_verified_at'] ?? null];
    } catch (Throwable $e) { $out['meta'] = ['error' => mb_substr($e->getMessage(), 0, 160)]; }
    $patron = pm_kanal_patron();
    $out['numaralar'] = ['count' => count(pm_kanal_numaralar()), 'patron_found' => $patron !== null, 'patron_masked' => $patron ? '…'.substr($patron, -4) : null];
    $ayar = function_exists('ayarlarOku') ? (ayarlarOku() ?: []) : [];
    $ayarJson = (string)($settings['ayarlar_json'] ?? '');
    $out['llm'] = ['backend' => $settings['llm']['backend'] ?? null, 'model' => $settings['llm']['model'] ?? null,
        'openai_key_present_in_panel' => trim((string)($ayar['openai_key'] ?? '')) !== '', 'panel_model' => $ayar['model'] ?? null,
        'ayarlar_json_path_exists' => $ayarJson !== '' && is_file($ayarJson),
        'ayarlar_json_has_key' => $ayarJson !== '' && is_file($ayarJson) && trim((string)(json_decode((string)file_get_contents($ayarJson), true)['openai_key'] ?? '')) !== ''];
    $venv = dirname(PM_KANAL_DIR).'/task2/venv/bin/python';
    $out['python'] = ['venv_python_exists' => is_file($venv), 'worker_py_exists' => is_file(PM_KANAL_DIR.'/worker.py'),
        'worker_health' => is_file(PM_KANAL_DIR.'/worker-health.json') ? pm_read(PM_KANAL_DIR.'/worker-health.json') : null,
        'self_test' => is_file(PM_KANAL_DIR.'/self-test-result.json') ? array_intersect_key(pm_read(PM_KANAL_DIR.'/self-test-result.json'), array_flip(['state', 'sure_s', 'adimlar', 'finished_at'])) : null,
        'install_report' => is_file(PM_KANAL_DIR.'/install-report.json') ? array_intersect_key(pm_read(PM_KANAL_DIR.'/install-report.json'), array_flip(['attempts', 'returncode', 'packages', 'at'])) : null];
    $out['files'] = ['state_dir_writable' => is_writable(PM_KANAL_DIR), 'ref_dxf' => is_file(PM_KANAL_DIR.'/ref_source-6x8.dxf'), 'font' => is_file(PM_KANAL_DIR.'/DejaVuSans.ttf'),
        'templates' => array_map('basename', glob(PM_KANAL_DIR.'/is_emri/*.json') ?: [])];
    $out['settings'] = array_intersect_key($settings, array_flip(['enabled', 'enabled_at', 'dry_run', 'mode', 'patron_teknik_not', 'panel_kaydi', 'max_is_per_tick', 'budget_s']));
    $out['ready'] = ($out['meta']['access_token_present'] ?? false) && ($out['meta']['app_secret_present'] ?? false) && $out['numaralar']['patron_found']
        && $out['llm']['ayarlar_json_has_key'] && $out['python']['venv_python_exists'] && $out['files']['ref_dxf'] && $out['files']['font'];
    pm_write(PM_KANAL_DIR.'/preflight.json', $out);
    return $out;
}
