<?php
declare(strict_types=1);
/* Uçtan uca yerel test için PHP adımları: php tests/e2e_steps.php <init|capture|tick|dump> <tmpdir> [lib.php] — Meta/OpenAI yok. */
[$_, $step, $tmp] = $argv + [null, null, null]; $libPath = $argv[3] ?? (__DIR__.'/lib.snapshot.php');
$PHONE = '106000000000001'; $PATRON = '905000000001'; $SECRET = 'test-app-secret';
define('PM_DATA', "$tmp/data"); define('PM_QUEUE', "$tmp/queue"); define('PM_OFFLINE_TEST', true); define('PM_KANAL_DIR', "$tmp/kanal");
function numaralarOku(): array { global $PATRON; return [$PATRON => ['ad' => 'Patron', 'firma' => 'PortatifEv']]; }
function ayarlarOku(): array { return ['openai_key' => '', 'model' => 'gpt-4o-mini']; }
$GLOBALS['pm_test_remote'] = function ($url, $token, $method, $body) use ($tmp) {
    $log = "$tmp/meta_calls.jsonl"; file_put_contents($log, json_encode(['url' => $url, 'method' => $method, 'body' => is_string($body) ? json_decode($body, true) : 'multipart'], JSON_UNESCAPED_UNICODE)."\n", FILE_APPEND);
    if (str_ends_with($url, '/media')) return ['id' => '918800000000001'];
    $to = json_decode($body, true)['to']; $n = count(file($log));
    return ['contacts' => [['input' => $to, 'wa_id' => $to]], 'messages' => [['id' => 'wamid.OUT'.$n]]];
};
require $libPath; require dirname(__DIR__).'/feature.php';
if ($step === 'init') {
    @mkdir(PM_DATA.'/files', 0700, true); @mkdir(PM_QUEUE, 0700, true);
    pm_write(PM_DATA.'/config.json', ['phone_number_id' => $PHONE, 'graph_version' => 'v26.0', 'credential_source' => 'local', 'access_token' => 'TEST-TOKEN', 'app_secret' => $SECRET, 'connection_verified_at' => time() - 86400]);
    pm_write(PM_DATA.'/store.json', ['messages' => [], 'statuses' => [], 'outgoing' => [], 'events' => [], 'bridge' => ['cursor' => 0, 'event_received_at' => 0, 'imported_events' => 0, 'checked_at' => 0, 'error' => null]]);
    echo "init ok\n"; exit;
}
if ($step === 'capture') {
    $text = $argv[4] ?? 'P6001 aynalı'; $id = $argv[5] ?? 'wamid.E2E1'; $ctx = $argv[6] ?? '';   // İE-02: isteğe bağlı alıntı (context.id)
    $m = ['from' => $PATRON, 'id' => $id, 'timestamp' => (string)time(), 'type' => 'text', 'text' => ['body' => $text]];
    if ($ctx !== '') $m['context'] = ['from' => '4448056', 'id' => $ctx];
    $raw = json_encode(['object' => 'whatsapp_business_account', 'entry' => [['id' => 'waba', 'changes' => [['field' => 'messages', 'value' => ['messaging_product' => 'whatsapp',
        'metadata' => ['display_phone_number' => '4448056', 'phone_number_id' => $PHONE], 'contacts' => [['wa_id' => $PATRON, 'profile' => ['name' => 'Lokman']]],
        'messages' => [$m]]]]]]], JSON_UNESCAPED_UNICODE);
    $owned = pm_kanal_capture($raw, 'sha256='.hash_hmac('sha256', $raw, $SECRET));
    echo json_encode(['owned' => array_keys($owned)])."\n"; exit;
}
if ($step === 'button') {   // İE-04: buton cevabı — php e2e_steps.php button <tmp> <lib> <reply_id> <baslik> <mesaj id> <cevaplanan wamid>
    $rid = $argv[4] ?? ''; $baslik = $argv[5] ?? 'Onayla'; $id = $argv[6] ?? 'wamid.E2EB1'; $ctx = $argv[7] ?? '';
    $m = ['from' => $PATRON, 'id' => $id, 'timestamp' => (string)time(), 'type' => 'interactive', 'interactive' => ['type' => 'button_reply', 'button_reply' => ['id' => $rid, 'title' => $baslik]]];
    if ($ctx !== '') $m['context'] = ['from' => '4448056', 'id' => $ctx];
    $raw = json_encode(['object' => 'whatsapp_business_account', 'entry' => [['id' => 'waba', 'changes' => [['field' => 'messages', 'value' => ['messaging_product' => 'whatsapp',
        'metadata' => ['display_phone_number' => '4448056', 'phone_number_id' => $PHONE], 'contacts' => [['wa_id' => $PATRON, 'profile' => ['name' => 'Lokman']]],
        'messages' => [$m]]]]]]], JSON_UNESCAPED_UNICODE);
    $owned = pm_kanal_capture($raw, 'sha256='.hash_hmac('sha256', $raw, $SECRET));
    echo json_encode(['owned' => array_keys($owned)])."\n"; exit;
}
if ($step === 'status') {   // İE-02: imzalı Meta durum bildirimi (delivered/read/failed) — php e2e_steps.php status <tmp> <lib> <wamid> <durum> [zaman]
    $wamid = $argv[4] ?? ''; $kind = $argv[5] ?? 'delivered'; $ts = (int)($argv[6] ?? time());
    $raw = json_encode(['object' => 'whatsapp_business_account', 'entry' => [['id' => 'waba', 'changes' => [['field' => 'messages', 'value' => ['messaging_product' => 'whatsapp',
        'metadata' => ['display_phone_number' => '4448056', 'phone_number_id' => $PHONE], 'statuses' => [['id' => $wamid, 'status' => $kind, 'timestamp' => (string)$ts, 'recipient_id' => $PATRON]]]]]]]]);
    pm_kanal_capture($raw, 'sha256='.hash_hmac('sha256', $raw, $SECRET));
    echo json_encode(['ok' => true])."\n"; exit;
}
if ($step === 'requeue') {  // İE-02: işlenmiş bir gelen satırı kuyruğa geri koyar (aynı kanal mesajının yeniden işlenmesi)
    $id = $argv[4] ?? ''; pm_kanal_store(function (&$s) use ($id) { if (isset($s['inbound'][$id])) $s['inbound'][$id]['state'] = 'queued'; });
    echo json_encode(['ok' => true])."\n"; exit;
}
if ($step === 'tick') { pm_kanal_tick(); echo json_encode(pm_read(PM_KANAL_DIR.'/health.json'), JSON_UNESCAPED_UNICODE)."\n"; exit; }
if ($step === 'dump') { echo json_encode(['state' => pm_kanal_store(fn(&$s) => $s), 'outgoing' => pm_store(fn(&$d) => $d['outgoing'])], JSON_UNESCAPED_UNICODE)."\n"; exit; }
fwrite(STDERR, "adım? init|capture|button|status|requeue|tick|dump\n"); exit(2);
