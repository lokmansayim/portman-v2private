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
const PM_KANAL_SURUM = 'kanal-v1.0';
const PM_KANAL_STALE = 600;

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
            $yeni[$mid] = ['id' => $mid, 'sender' => $from, 'name' => $names[$from] ?? '', 'role' => $bayi['rol'] ?? 'bayi', 'bayi' => $bayi,
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
            $path = (string)($r['file'] ?? ''); $real = $path !== '' ? realpath($path) : false;
            if ($real === false || !str_starts_with($real, PM_KANAL_DIR.'/projects/') || !is_file($real) || filesize($real) < 1 || filesize($real) > 25 * 1024 * 1024) throw new RuntimeException('local_file_invalid');
            if (!empty($r['sha256']) && !hash_equals($r['sha256'], hash_file('sha256', $real))) throw new RuntimeException('local_file_changed');
            if (!str_starts_with((string)file_get_contents($real, false, null, 0, 5), '%PDF-')) throw new RuntimeException('pdf_invalid');
            $media = (string)($r['media_id'] ?? '');
            if (!ctype_digit($media) || $media === '') {
                pm_kanal_update($id, ['state' => 'uploading', 'attempts' => ($r['attempts'] ?? 0) + 1, 'to_resolved' => $to, 'send_started_at' => time()]);
                $upload = pm_remote('https://graph.facebook.com/'.$cfg['graph_version'].'/'.$cfg['phone_number_id'].'/media', $cfg['access_token'], 'POST',
                    ['messaging_product' => 'whatsapp', 'type' => 'application/pdf', 'file' => new CURLFile($real, 'application/pdf', (string)$r['filename'])]);
                $media = (string)($upload['id'] ?? '');
                if (!ctype_digit($media) || $media === '') throw new RuntimeException('media_response');
                pm_kanal_update($id, ['media_id' => $media]);
            }
            $payload['type'] = 'document';
            $payload['document'] = ['id' => $media, 'filename' => (string)$r['filename']];
            if (trim((string)($r['body'] ?? '')) !== '') $payload['document']['caption'] = mb_substr((string)$r['body'], 0, 1000);
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
            $retry = ($r['state'] ?? '') === 'upload_failed' && ($r['attempts'] ?? 0) < 2 && ($r['kind'] ?? '') === 'document';
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
            $d['outgoing'][$id] = ['request_id' => $id, 'parent_message_id' => $r['inbound_id'], 'recipient' => $r['to_resolved'] ?? $r['to'],
                'kind' => $r['kind'] === 'document' ? 'document' : 'text', 'body' => (string)($r['body'] ?? ''), 'filename' => $r['filename'] ?? null,
                'sha256' => $r['sha256'] ?? null, 'local_file' => null, 'mime' => $r['mime'] ?? null, 'transport' => $r['kind'] === 'document' ? 'media' : 'text',
                'state' => $r['state'], 'timestamp' => $r['created_at'], 'updated' => $r['updated_at'], 'phone_number_id' => $r['phone_number_id'] ?? null,
                'wamid' => $r['wamid'], 'media_id' => $r['media_id'] ?? null, 'error' => $r['error'], 'request_accepted_at' => $r['request_accepted_at'],
                'delivery_state' => $r['delivery_state'] ?? null, 'evidence' => 'İmzalı WhatsApp → Portman kanal (Beyin+Motor, hosting) → '.($r['kind'] === 'document' ? 'PDF' : 'metin')];
        }
    });
    if (($settings['panel_kaydi'] ?? true) !== true || !function_exists('mesajKaydet')) return;
    foreach ($rows as $id => $r) {
        if (!empty($r['self_test']) || !empty($r['panel_logged']) || !is_string($r['wamid'] ?? null)) continue;
        $icerik = $r['kind'] === 'document' ? '📎 '.($r['filename'] ?? 'belge.pdf').(trim((string)$r['body']) !== '' ? ' — '.$r['body'] : '') : (string)$r['body'];
        try { mesajKaydet($r['to_resolved'] ?? $r['to'], 'Portman', 'giden', 'text', $icerik, $r['wamid'], ['ai' => true, 'portman' => 'kanal']); }
        catch (Throwable $e) { error_log('Portman kanal panel kaydı: '.$e->getMessage()); }
        pm_kanal_update($id, ['panel_logged' => true]);
    }
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
