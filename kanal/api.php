<?php
declare(strict_types=1);
/*
 PORTMAN KANAL v1.1 — VPS işçisi için hosting API'si (kontrol düzlemi hostingte kalır).
 VPS'teki ajan (agent.py) buraya YALNIZ dışarıdan bağlanır (hosting VPS'e bağlanmaz):
   settings   → ayarlar + paket özeti (+ LLM anahtarı, yalnız settings.vps_llm_key_from_hosting true ise)
   package    → güncel işçi paketi (zip)
   claim      → en eski 'queued' gelen satırını 'processing' yapar, satırı + görüşme durumunu (durum/<sender>.json) verir
   result     → giden satırları + PDF/DXF dosyaları + güncel durum; state.json'a yazar (tick gönderir)
   heartbeat  → vps-health.json / worker-health.json
   log        → vps.log (2 MB döner)
 Kimlik: X-Portman-Token başlığı == kanal/api_token.txt (hash_equals). Eşleşmeyen istek 401 + 1 s bekleme.
 Ana anahtarlar: settings.json → enabled (tümü), worker ("hosting" | "vps" | "off": claim yalnız "vps" iken iş verir).
 WhatsApp erişim anahtarı VPS'e hiçbir zaman gitmez; gönderim yalnız feature.php::pm_kanal_tick.
*/
if (!defined('PM_KANAL_DIR')) define('PM_KANAL_DIR', __DIR__);
const PM_KANAL_API_SURUM = 'kanal-api-v1.1';
const PM_KANAL_API_MAX_PDF = 25 * 1024 * 1024;
const PM_KANAL_API_MAX_FILE = 40 * 1024 * 1024;

function pm_kanal_api_token(): ?string {
    $p = PM_KANAL_DIR.'/api_token.txt';
    if (!is_file($p)) return null;
    $t = trim((string)file_get_contents($p));
    return (strlen($t) >= 32 && strlen($t) <= 128 && ctype_alnum($t)) ? $t : null;
}

function pm_kanal_api_json(int $code, array $body): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
}

function pm_kanal_api_audit(string $op, bool $ok, string $not = ''): void {
    try {
        $p = PM_KANAL_DIR.'/api-audit.json';
        $a = is_file($p) ? (pm_read($p) ?: []) : [];
        $a['last'] = ['at' => time(), 'op' => $op, 'ok' => $ok, 'note' => mb_substr($not, 0, 120), 'ip' => $_SERVER['REMOTE_ADDR'] ?? null];
        $k = $ok ? 'ok' : 'fail';
        $a['counts'][$k] = ($a['counts'][$k] ?? 0) + 1;
        if (!$ok) { $a['fails'][] = $a['last']; $a['fails'] = array_slice($a['fails'], -20); }
        pm_write($p, $a);
    } catch (Throwable $e) { error_log('Portman kanal api audit: '.$e->getMessage()); }
}

/* Paket: kanal/package/current.zip (+ current.sha256 isteğe bağlı; yoksa hesaplanır) */
function pm_kanal_api_paket(): ?array {
    $z = PM_KANAL_DIR.'/package/current.zip';
    if (!is_file($z)) return null;
    $shaP = PM_KANAL_DIR.'/package/current.sha256';
    $sha = is_file($shaP) ? trim((string)file_get_contents($shaP)) : '';
    if (!preg_match('/^[0-9a-f]{64}$/', $sha)) $sha = hash_file('sha256', $z);
    return ['file' => 'current.zip', 'sha256' => $sha, 'size' => filesize($z), 'mtime' => filemtime($z),
            'surum' => is_file(PM_KANAL_DIR.'/package/SURUM.txt') ? trim((string)file_get_contents(PM_KANAL_DIR.'/package/SURUM.txt')) : null];
}

function pm_kanal_api_settings_out(array $settings): array {
    $out = ['api' => PM_KANAL_API_SURUM, 'now' => time(), 'enabled' => ($settings['enabled'] ?? false) === true, 'worker' => (string)($settings['worker'] ?? 'hosting'),
            'dry_run' => ($settings['dry_run'] ?? false) === true, 'mode' => $settings['mode'] ?? 'patron',
            'llm' => array_intersect_key(is_array($settings['llm'] ?? null) ? $settings['llm'] : [], array_flip(['backend', 'model', 'timeout_s'])),
            'patron_teknik_not' => ($settings['patron_teknik_not'] ?? true) === true, 'poll_s' => (int)($settings['vps_poll_s'] ?? 4),
            'package' => pm_kanal_api_paket()];
    if (($settings['vps_llm_key_from_hosting'] ?? true) === true) {
        $key = '';
        $ayarJson = (string)($settings['ayarlar_json'] ?? '');
        if ($ayarJson !== '' && is_file($ayarJson)) $key = trim((string)(json_decode((string)file_get_contents($ayarJson), true)['openai_key'] ?? ''));
        if ($key === '' && function_exists('ayarlarOku')) $key = trim((string)((ayarlarOku() ?: [])['openai_key'] ?? ''));
        if ($key !== '') $out['openai_key'] = $key;          // yalnız kimliği doğrulanmış ajana, HTTPS üzerinden; diske yazılmaz
    }
    return $out;
}

/* claim: worker.py::is_al ile aynı kural (takılı 'processing' → failed; en eski queued → processing) */
function pm_kanal_api_claim(array $settings): array {
    if (($settings['enabled'] ?? false) !== true) return ['job' => null, 'reason' => 'disabled'];
    if ((string)($settings['worker'] ?? 'hosting') !== 'vps') return ['job' => null, 'reason' => 'worker='.(string)($settings['worker'] ?? 'hosting')];
    $job = pm_kanal_store(function (&$s) {
        $now = time();
        foreach ($s['inbound'] as &$r) {
            if (($r['state'] ?? '') === 'processing' && ($r['updated_at'] ?? 0) < $now - PM_KANAL_STALE) {
                $r['state'] = 'failed'; $r['error'] = 'İşlem teyit edilmeden bitti; otomatik tekrar yok.'; $r['updated_at'] = $now;
            }
        } unset($r);
        $aday = null;
        foreach ($s['inbound'] as $id => $r) {
            if (($r['state'] ?? '') !== 'queued' || !empty($r['self_test'])) continue;
            if ($aday === null || [$r['timestamp'] ?? 0, $r['received_at'] ?? 0] < [$aday['timestamp'] ?? 0, $aday['received_at'] ?? 0]) $aday = $r + ['id' => $id];
        }
        if ($aday === null) return null;
        $id = $aday['id'];
        $s['inbound'][$id]['state'] = 'processing'; $s['inbound'][$id]['attempts'] = ($s['inbound'][$id]['attempts'] ?? 0) + 1;
        $s['inbound'][$id]['started_at'] = $now; $s['inbound'][$id]['updated_at'] = $now; $s['inbound'][$id]['worker'] = 'vps';
        return $s['inbound'][$id] + ['id' => $id];
    });
    if ($job === null) return ['job' => null];
    $durum = null; $sender = (string)($job['sender'] ?? '');
    if ($sender !== '' && pm_contact($sender) && is_file(PM_KANAL_DIR.'/durum/'.$sender.'.json')) $durum = pm_read(PM_KANAL_DIR.'/durum/'.$sender.'.json');
    return ['job' => $job, 'durum' => $durum];
}

/* result: multipart — cikti (JSON), durum (JSON, isteğe bağlı), file_<i> dosyaları (projects/... altına) */
function pm_kanal_api_result(array $post, array $files): array {
    $cikti = json_decode((string)($post['cikti'] ?? ''), true);
    $inboundId = (string)($post['inbound_id'] ?? '');
    if (!is_array($cikti) || !is_array($cikti['satirlar'] ?? null) || !is_array($cikti['sonuc'] ?? null) || $inboundId === '') throw new RuntimeException('bad_result');
    $in = pm_kanal_store(fn(&$s) => $s['inbound'][$inboundId] ?? null);
    if (!$in) throw new RuntimeException('inbound_unknown');
    if (($in['state'] ?? '') !== 'processing' || ($in['worker'] ?? '') !== 'vps') throw new RuntimeException('inbound_not_claimed_by_vps');
    // dosyalar: yalnız projects/<no>/rNN/<ad>; yol temizliği; PDF başlığı; sha eşleşmesi
    $yazilan = [];
    foreach ($files as $alan => $f) {
        if (!is_array($f) || ($f['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) continue;
        $hedef = (string)($post['path_'.$alan] ?? '');
        if (!preg_match('#^projects/[A-Za-z0-9_.-]{1,80}/r[0-9]{2}/[A-Za-z0-9_.-]{1,120}$#', $hedef) || str_contains($hedef, '..')) throw new RuntimeException('bad_path');
        if (($f['size'] ?? 0) < 1 || ($f['size'] ?? 0) > PM_KANAL_API_MAX_FILE) throw new RuntimeException('file_size');
        $tam = PM_KANAL_DIR.'/'.$hedef;
        if (!is_dir(dirname($tam))) @mkdir(dirname($tam), 0700, true);
        if (str_ends_with(strtolower($hedef), '.pdf')) {
            if (($f['size'] ?? 0) > PM_KANAL_API_MAX_PDF || !str_starts_with((string)file_get_contents($f['tmp_name'], false, null, 0, 5), '%PDF-')) throw new RuntimeException('pdf_invalid');
        }
        if (!move_uploaded_file($f['tmp_name'], $tam) && !@rename($f['tmp_name'], $tam)) throw new RuntimeException('file_write');
        @chmod($tam, 0600);
        $yazilan[$hedef] = $tam;
    }
    foreach ($cikti['satirlar'] as &$r) {
        if (($r['kind'] ?? 'text') === 'document') {
            $rel = (string)($r['file'] ?? '');
            if (!isset($yazilan[$rel])) throw new RuntimeException('document_file_missing');
            if (!empty($r['sha256']) && !hash_equals((string)$r['sha256'], hash_file('sha256', $yazilan[$rel]))) throw new RuntimeException('document_sha_mismatch');
            $r['file'] = $yazilan[$rel];
        }
        if (($r['inbound_id'] ?? '') !== $inboundId) throw new RuntimeException('row_inbound_mismatch');
        $r['worker'] = 'vps';
    } unset($r);
    // görüşme durumu (yalnız bu gelenin göndericisi için)
    if (isset($post['durum']) && (string)$post['durum'] !== '') {
        $d = json_decode((string)$post['durum'], true);
        $sender = (string)($in['sender'] ?? '');
        if (is_array($d) && $sender !== '' && pm_contact($sender)) {
            if (!is_dir(PM_KANAL_DIR.'/durum')) @mkdir(PM_KANAL_DIR.'/durum', 0700, true);
            pm_write(PM_KANAL_DIR.'/durum/'.$sender.'.json', $d);
        }
    }
    $n = pm_kanal_store(function (&$s) use ($cikti, $inboundId) {
        $now = time(); $n = 0;
        foreach ($cikti['satirlar'] as $r) {
            if (!isset($s['outbound'][$r['id']])) { $s['outbound'][$r['id']] = $r; $n++; }
        }
        if (isset($s['inbound'][$inboundId])) {
            $s['inbound'][$inboundId] = array_replace($s['inbound'][$inboundId], ['state' => !empty($cikti['hata']) ? 'failed' : 'done', 'result' => $cikti['sonuc'],
                'outbound_ids' => array_column($cikti['satirlar'], 'id'), 'error' => $cikti['hata'] ?? null, 'finished_at' => $now, 'updated_at' => $now]);
        }
        return $n;
    });
    return ['ok' => true, 'outbound' => $n, 'files' => count($yazilan)];
}

function pm_kanal_api_heartbeat(array $body): array {
    $izin = array_flip(['surum', 'python', 'package_sha256', 'uptime_s', 'load', 'disk_free_mb', 'mem_free_mb', 'last_job', 'jobs_done', 'jobs_failed', 'self_test', 'host', 'started_at', 'errors']);
    $h = array_intersect_key($body, $izin);
    $h['checked_at'] = time(); $h['worker'] = 'vps'; $h['ip'] = $_SERVER['REMOTE_ADDR'] ?? null;
    pm_write(PM_KANAL_DIR.'/vps-health.json', $h);
    $settings = pm_kanal_settings();
    if ((string)($settings['worker'] ?? 'hosting') === 'vps') pm_write(PM_KANAL_DIR.'/worker-health.json', $h + ['enabled' => ($settings['enabled'] ?? false) === true]);
    return ['ok' => true, 'worker' => (string)($settings['worker'] ?? 'hosting'), 'enabled' => ($settings['enabled'] ?? false) === true];
}

function pm_kanal_api_log(array $body): array {
    $lines = is_array($body['lines'] ?? null) ? $body['lines'] : [];
    $p = PM_KANAL_DIR.'/vps.log';
    if (is_file($p) && filesize($p) > 2 * 1024 * 1024) @rename($p, $p.'.1');
    $f = fopen($p, 'a');
    if ($f) {
        @chmod($p, 0600);
        foreach (array_slice($lines, 0, 200) as $l) fwrite($f, mb_substr(preg_replace('/[\r\n]+/', ' ', (string)$l), 0, 1000)."\n");
        fclose($f);
    }
    return ['ok' => true, 'n' => min(count($lines), 200)];
}

/* Giriş noktası (developer/kanal_api.php çağırır). $raw/$files test için verilebilir. */
function pm_kanal_api(?string $raw = null, ?array $files = null, ?array $post = null, ?array $query = null, ?array $headers = null): void {
    $q = $query ?? $_GET; $post = $post ?? $_POST; $files = $files ?? $_FILES;
    $op = preg_replace('/[^a-z_]/', '', (string)($q['op'] ?? ''));
    $hdr = $headers ?? ['token' => $_SERVER['HTTP_X_PORTMAN_TOKEN'] ?? ''];
    $token = pm_kanal_api_token();
    if ($token === null) { pm_kanal_api_json(503, ['error' => 'unpaired', 'hint' => 'kanal/api_token.txt yok']); return; }
    $verilen = (string)($hdr['token'] ?? '');
    if ($verilen === '' || !hash_equals($token, $verilen)) { pm_kanal_api_audit($op, false, 'bad_token'); sleep(1); pm_kanal_api_json(401, ['error' => 'unauthorized']); return; }
    $settings = pm_kanal_settings();
    try {
        switch ($op) {
            case 'settings':
                pm_kanal_api_json(200, pm_kanal_api_settings_out($settings)); break;
            case 'package':
                $pk = pm_kanal_api_paket();
                if (!$pk) { pm_kanal_api_json(404, ['error' => 'no_package']); break; }
                $z = PM_KANAL_DIR.'/package/current.zip';
                header('Content-Type: application/zip'); header('Content-Length: '.(string)filesize($z)); header('X-Package-Sha256: '.$pk['sha256']);
                header('Content-Disposition: attachment; filename="portman_worker.zip"');
                readfile($z); break;
            case 'claim':
                pm_kanal_api_json(200, pm_kanal_api_claim($settings)); break;
            case 'result':
                pm_kanal_api_json(200, pm_kanal_api_result($post, $files)); break;
            case 'heartbeat':
            case 'log':
                $body = json_decode($raw ?? (string)file_get_contents('php://input'), true);
                if (!is_array($body)) throw new RuntimeException('bad_json');
                pm_kanal_api_json(200, $op === 'heartbeat' ? pm_kanal_api_heartbeat($body) : pm_kanal_api_log($body)); break;
            default:
                pm_kanal_api_json(400, ['error' => 'unknown_op']); pm_kanal_api_audit($op, false, 'unknown_op'); return;
        }
        pm_kanal_api_audit($op, true);
    } catch (Throwable $e) {
        pm_kanal_api_audit($op, false, $e->getMessage());
        pm_kanal_api_json(422, ['error' => mb_substr($e->getMessage(), 0, 160)]);
    }
}
