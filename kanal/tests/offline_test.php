<?php
declare(strict_types=1);
/*
 PORTMAN KANAL — çevrimdışı PHP testi. Gerçek portman/lib.php (ya da paketteki lib.snapshot.php) + PM_OFFLINE_TEST kancaları:
 Meta'ya HİÇBİR bağlantı yok (pm_remote sahte), OpenAI yok, geçici PM_DATA. Çalıştırma:
   php tests/offline_test.php [lib.php yolu]
*/
$libPath = $argv[1] ?? (__DIR__.'/lib.snapshot.php');
if (!is_file($libPath)) { fwrite(STDERR, "lib bulunamadı: $libPath\n"); exit(2); }
$tmp = sys_get_temp_dir().'/pm_kanal_test_'.bin2hex(random_bytes(4));
mkdir($tmp, 0700, true); mkdir("$tmp/data/files", 0700, true); mkdir("$tmp/queue", 0700, true); mkdir("$tmp/kanal/projects/PM-TEST/r01", 0700, true);
define('PM_DATA', "$tmp/data"); define('PM_QUEUE', "$tmp/queue"); define('PM_OFFLINE_TEST', true); define('PM_KANAL_DIR', "$tmp/kanal");
$PHONE = '106000000000001'; $PATRON = '905000000001'; $BAYI = '905000000002'; $YABANCI = '905000000009'; $SECRET = 'test-app-secret';
file_put_contents(PM_DATA.'/config.json', json_encode(['phone_number_id' => $PHONE, 'graph_version' => 'v26.0', 'credential_source' => 'local',
    'access_token' => 'TEST-TOKEN', 'app_secret' => $SECRET, 'connection_verified_at' => time() - 86400, 'waba_id' => 'w', 'app_id' => 'a']));
file_put_contents(PM_DATA.'/store.json', json_encode(['messages' => [], 'statuses' => [], 'outgoing' => [], 'events' => [],
    'bridge' => ['cursor' => 0, 'event_received_at' => 0, 'imported_events' => 0, 'checked_at' => 0, 'error' => null]]));
// sahte panel fonksiyonları (developer/config.php yerine)
function numaralarOku(): array { global $PATRON, $BAYI; return [$PATRON => ['ad' => 'Patron', 'firma' => 'PortatifEv', 'otomatik' => 1], $BAYI => ['ad' => 'Ahmet Bey', 'firma' => 'Test A.Ş.', 'otomatik' => 1]]; }
function ayarlarOku(): array { return ['openai_key' => 'sk-test-not-real', 'model' => 'gpt-4o-mini', 'ai_aktif' => 1]; }
$PANEL = []; function mesajKaydet($wa_id, $isim, $yon, $tip, $icerik, $msgId, $ek = []) { $GLOBALS['PANEL'][] = [$wa_id, $yon, $tip, mb_substr((string)$icerik, 0, 60), $msgId]; }
$CALLS = []; $GLOBALS['pm_test_remote'] = function ($url, $token, $method, $body, $contentType, $binary) use (&$CALLS) {
    $CALLS[] = [$url, $method, is_string($body) ? json_decode($body, true) : (is_array($body) ? array_map(fn($v) => $v instanceof CURLFile ? 'CURLFile:'.basename($v->getFilename()) : $v, $body) : null)];
    if (str_ends_with($url, '/media')) return ['id' => '918800000000001'];
    if (str_ends_with($url, '/messages')) { $to = json_decode($body, true)['to']; return ['messaging_product' => 'whatsapp', 'contacts' => [['input' => $to, 'wa_id' => $to]], 'messages' => [['id' => 'wamid.OUT'.count($CALLS)]]]; }
    throw new RuntimeException('beklenmeyen url '.$url);
};
require $libPath;
require dirname(__DIR__).'/feature.php';
$pass = 0; $fail = 0;
function ok(bool $c, string $ne): void { global $pass, $fail; echo ($c ? '  ✓ ' : '  ✗ ').$ne."\n"; $c ? $pass++ : $fail++; }
function payload(array $messages, array $statuses = [], array $contacts = []): string {
    global $PHONE;
    return json_encode(['object' => 'whatsapp_business_account', 'entry' => [['id' => 'waba', 'changes' => [['field' => 'messages',
        'value' => ['messaging_product' => 'whatsapp', 'metadata' => ['display_phone_number' => '4448056', 'phone_number_id' => $PHONE], 'contacts' => $contacts, 'messages' => $messages, 'statuses' => $statuses]]]]]], JSON_UNESCAPED_UNICODE);
}
function sig(string $raw): string { global $SECRET; return 'sha256='.hash_hmac('sha256', $raw, $SECRET); }
function msg(string $id, string $from, string $text, ?int $ts = null, string $type = 'text'): array {
    $m = ['from' => $from, 'id' => $id, 'timestamp' => (string)($ts ?? time()), 'type' => $type];
    if ($type === 'text') $m['text'] = ['body' => $text]; elseif ($type === 'image') $m['image'] = ['id' => '777', 'mime_type' => 'image/jpeg', 'caption' => $text]; elseif ($type === 'reaction') $m['reaction'] = ['emoji' => '👍', 'message_id' => 'wamid.X'];
    return $m;
}
function settings(array $over = []): void { pm_write(PM_KANAL_DIR.'/settings.json', array_replace(['enabled' => true, 'enabled_at' => time() - 3600, 'dry_run' => false, 'mode' => 'patron',
    'llm' => ['backend' => 'openai_chat', 'model' => 'gpt-4o-mini'], 'ayarlar_json' => '/yok/ayarlar.json', 'patron_teknik_not' => true, 'panel_kaydi' => true], $over)); }

echo "1) Yakalama — imza, mod, sahiplenme\n";
settings(['enabled' => false]);
$raw = payload([msg('wamid.P1', $PATRON, 'P6001 aynalı')], [], [['wa_id' => $PATRON, 'profile' => ['name' => 'Lokman']]]);
ok(pm_kanal_capture($raw, sig($raw)) === [], 'enabled=false → hiçbir mesaj sahiplenilmez');
settings();
ok(pm_kanal_capture($raw, 'sha256=yanlis') === [], 'yanlış imza → sahiplenme yok');
$owned = pm_kanal_capture($raw, sig($raw));
ok(isset($owned['wamid.P1']), 'Patron metni sahiplenildi');
$st = pm_kanal_store(fn(&$s) => $s);
ok(($st['inbound']['wamid.P1']['state'] ?? '') === 'queued' && $st['inbound']['wamid.P1']['role'] === 'patron' && $st['inbound']['wamid.P1']['bayi']['kod'] === 'PATRON' && $st['inbound']['wamid.P1']['name'] === 'Lokman', 'kuyruk satırı: queued, role=patron, kod=PATRON, ad');
ok(pm_store(fn(&$d) => isset($d['messages']['wamid.P1'])), 'ana kayıt (store.json) da yazıldı (pm_ingest)');
ok(pm_kanal_capture($raw, sig($raw)) === ['wamid.P1' => true] && count(pm_kanal_store(fn(&$s) => $s['inbound'])) === 1, 'tekrar teslim: sahiplenir, ikinci satır açmaz');
$raw2 = payload([msg('wamid.B1', $BAYI, 'P8501 mirror'), msg('wamid.Y1', $YABANCI, 'merhaba'), msg('wamid.R1', $PATRON, '', null, 'reaction'), msg('wamid.E1', $PATRON, 'eski', time() - 1000)]);
$owned = pm_kanal_capture($raw2, sig($raw2));
ok(!isset($owned['wamid.B1']) && !isset($owned['wamid.Y1']), 'mode=patron: bayi ve kayıtsız sahiplenilmez (sohbet botu devam)');
ok(!isset($owned['wamid.R1']), 'tepki mesajı sahiplenilmez');
ok(isset($owned['wamid.E1']) && !isset(pm_kanal_store(fn(&$s) => $s['inbound'])['wamid.E1']), '15 dk+ eski Patron mesajı: sahiplenilir ama kuyruğa alınmaz');
settings(['mode' => 'kayitli']);
$owned = pm_kanal_capture($raw2, sig($raw2));
ok(isset($owned['wamid.B1']) && !isset($owned['wamid.Y1']), 'mode=kayitli: bayi sahiplenildi, kayıtsız değil');
settings(['mode' => 'hepsi']);
$owned = pm_kanal_capture($raw2, sig($raw2));
ok(isset($owned['wamid.Y1']) && pm_kanal_store(fn(&$s) => $s['inbound']['wamid.Y1']['bayi']) === null, 'mode=hepsi: kayıtsız sahiplenildi, bayi=null (Beyin yönlendirir)');
$raw3 = payload([msg('wamid.I1', $PATRON, 'kroki', null, 'image')]);
settings();
pm_kanal_capture($raw3, sig($raw3));
$r = pm_kanal_store(fn(&$s) => $s['inbound']['wamid.I1']);
ok($r['type'] === 'image' && $r['media_id'] === '777' && $r['text'] === 'kroki', 'medya mesajı: tür/medya kimliği/başlık kuyrukta');

echo "2) Gönderim — metin, belge, Patron bildirimi, sıra\n";
$pdf = "%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"; $pdfPath = PM_KANAL_DIR.'/projects/PM-TEST/r01/Portman_PM-TEST_r01.pdf'; file_put_contents($pdfPath, $pdf);
$now = time();
$rows = [
    'out_t1' => ['id' => 'out_t1', 'kind' => 'text', 'to' => $PATRON, 'body' => 'Ön onay planını hazırlıyorum.', 'tur' => 'cevap', 'inbound_id' => 'wamid.P1', 'seq' => 1, 'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now, 'updated_at' => $now],
    'out_d1' => ['id' => 'out_d1', 'kind' => 'document', 'to' => $PATRON, 'body' => 'PM-TEST r01 · taslak', 'tur' => 'belge', 'inbound_id' => 'wamid.P1', 'seq' => 2, 'file' => $pdfPath, 'filename' => 'Portman_PM-TEST_r01.pdf', 'mime' => 'application/pdf', 'sha256' => hash('sha256', $pdf), 'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now, 'updated_at' => $now],
    'out_n1' => ['id' => 'out_n1', 'kind' => 'text', 'to' => 'PATRON', 'body' => 'Portman yönlendirme: Ahmet Bey', 'tur' => 'bildirim', 'inbound_id' => 'wamid.B1', 'seq' => 1, 'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now + 1, 'updated_at' => $now],
    'out_s1' => ['id' => 'out_s1', 'kind' => 'text', 'to' => $PATRON, 'body' => 'öz-test', 'tur' => 'cevap', 'inbound_id' => 'selftest', 'seq' => 1, 'state' => 'pending', 'self_test' => true, 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now + 2, 'updated_at' => $now],
    'out_x1' => ['id' => 'out_x1', 'kind' => 'text', 'to' => $YABANCI, 'body' => 'yanlış alıcı', 'tur' => 'cevap', 'inbound_id' => 'wamid.P1', 'seq' => 3, 'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now + 3, 'updated_at' => $now],
];
pm_kanal_store(function (&$s) use ($rows) { $s['outbound'] = $rows; });
settings(['dry_run' => true]);
pm_kanal_tick();
$o = pm_kanal_store(fn(&$s) => $s['outbound']);
ok($o['out_t1']['state'] === 'held' && $o['out_d1']['state'] === 'held' && count($CALLS) === 0, 'dry_run: satırlar held, Meta çağrısı 0');
pm_kanal_store(function (&$s) { foreach (['out_t1', 'out_d1', 'out_n1', 'out_s1', 'out_x1'] as $id) { $s['outbound'][$id]['state'] = 'pending'; $s['outbound'][$id]['error'] = null; } });
settings();
pm_kanal_tick();
$o = pm_kanal_store(fn(&$s) => $s['outbound']);
ok($o['out_t1']['state'] === 'accepted' && $o['out_t1']['wamid'] === 'wamid.OUT1' && $o['out_t1']['acceptance_source'] === 'messages_api', 'metin gönderildi → accepted, wamid');
ok($o['out_d1']['state'] === 'accepted' && $o['out_d1']['media_id'] === '918800000000001' && $o['out_d1']['wamid'] === 'wamid.OUT3', 'belge: medya yüklendi + belge mesajı → accepted');
ok($o['out_n1']['state'] === 'accepted' && $o['out_n1']['to_resolved'] === $PATRON, 'to=PATRON bildirimi numaraya çözüldü (Patron son 24 saatte yazmış)');
ok($o['out_s1']['state'] === 'held' && str_contains((string)$o['out_s1']['error'], 'test_cannot_send'), 'öz-test satırı ASLA gönderilmez');
ok($o['out_x1']['state'] === 'held' && str_contains((string)$o['out_x1']['error'], 'recipient_mismatch'), 'alıcı ≠ gelen mesajın göndereni → gönderilmez');
$sira = array_map(fn($c) => (str_ends_with($c[0], '/media') ? 'media' : ($c[2]['type'] ?? '?')).':'.($c[2]['to'] ?? ''), $CALLS);
ok($sira === ["text:$PATRON", "media:", "document:$PATRON", "text:$PATRON"], 'Meta çağrı sırası: metin → medya yükleme → belge → bildirim ('.implode(', ', $sira).')');
ok(($CALLS[2][2]['document']['filename'] ?? '') === 'Portman_PM-TEST_r01.pdf' && ($CALLS[2][2]['biz_opaque_callback_data'] ?? '') === 'out_d1' && ($CALLS[0][2]['text']['preview_url'] ?? true) === false, 'belge yükü: dosya adı, opaque id, preview_url=false');
$out = pm_store(fn(&$d) => $d['outgoing']);
ok(isset($out['out_t1'], $out['out_d1']) && !isset($out['out_s1']) && $out['out_d1']['transport'] === 'media', 'panele yayın: store.json outgoing (öz-test hariç)');
ok(count($PANEL) === 3 && $PANEL[0][1] === 'giden' && str_starts_with($PANEL[1][3], '📎 '), 'panel sohbet kaydı (mesajKaydet) 3 giden');
pm_kanal_tick();
ok(count($CALLS) === 4, 'ikinci tik: kabul edilmiş satır tekrar gönderilmez');

echo "3) Teslimat bildirimleri ve belirsizlik\n";
$rawS = payload([], [['id' => 'wamid.OUT3', 'status' => 'delivered', 'timestamp' => (string)time(), 'recipient_id' => $PATRON, 'biz_opaque_callback_data' => 'out_d1'],
                    ['id' => 'wamid.OUT1', 'status' => 'read', 'timestamp' => (string)time(), 'recipient_id' => $PATRON]]);
pm_kanal_capture($rawS, sig($rawS));
$o = pm_kanal_store(fn(&$s) => $s['outbound']);
ok($o['out_d1']['delivery_state'] === 'delivered' && $o['out_d1']['state'] === 'delivered' && $o['out_t1']['state'] === 'read', 'delivered/read durumları satıra işlendi');
$rawS2 = payload([], [['id' => 'wamid.OUT3', 'status' => 'sent', 'timestamp' => (string)time(), 'recipient_id' => $PATRON]]);
pm_kanal_capture($rawS2, sig($rawS2));
ok(pm_kanal_store(fn(&$s) => $s['outbound']['out_d1']['state']) === 'delivered', 'geç gelen "sent" daha yüksek durumu ezmez');
$GLOBALS['pm_test_remote'] = function () { throw new PMError(502, 'Meta bağlantısı tamamlanamadı; sonuç doğrulanamadı.'); };
pm_kanal_store(function (&$s) use ($now, $PATRON) { $s['outbound']['out_u1'] = ['id' => 'out_u1', 'kind' => 'text', 'to' => $PATRON, 'body' => 'belirsiz', 'tur' => 'cevap', 'inbound_id' => 'wamid.P1', 'seq' => 9, 'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now + 9, 'updated_at' => $now]; });
pm_kanal_tick(); pm_kanal_tick();
$u = pm_kanal_store(fn(&$s) => $s['outbound']['out_u1']);
ok($u['state'] === 'uncertain' && $u['attempts'] === 1, 'bağlantı kesildi → uncertain, otomatik tekrar YOK (attempts=1)');
pm_kanal_store(function (&$s) { $s['outbound']['out_z1'] = $s['outbound']['out_u1']; $s['outbound']['out_z1']['id'] = 'out_z1'; $s['outbound']['out_z1']['state'] = 'sending'; $s['outbound']['out_z1']['updated_at'] = time() - 700; });
pm_kanal_tick();
ok(pm_kanal_store(fn(&$s) => $s['outbound']['out_z1']['state']) === 'uncertain', '10 dk takılı "sending" → uncertain');
$h = pm_read(PM_KANAL_DIR.'/health.json'); $pf = pm_read(PM_KANAL_DIR.'/preflight.json');
ok(($h['enabled'] ?? null) === true && isset($h['counts']['outbound']) && $pf['numaralar']['patron_found'] === true && $pf['llm']['openai_key_present_in_panel'] === true && $pf['llm']['ayarlar_json_path_exists'] === false, 'health.json + preflight.json yazıldı (sır yok, yalnız var/yok)');
ok(!str_contains((string)file_get_contents(PM_KANAL_DIR.'/preflight.json'), 'sk-test') && !str_contains((string)file_get_contents(PM_KANAL_DIR.'/state.json'), 'TEST-TOKEN'), 'anahtar/erişim jetonu hiçbir dosyaya yazılmadı');
settings(['enabled' => false]);
pm_kanal_store(function (&$s) use ($now, $PATRON) { $s['outbound']['out_k1'] = ['id' => 'out_k1', 'kind' => 'text', 'to' => $PATRON, 'body' => 'kapalı', 'tur' => 'cevap', 'inbound_id' => 'wamid.P1', 'seq' => 11, 'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now + 11, 'updated_at' => $now]; });
$GLOBALS['pm_test_remote'] = function () use (&$CALLS) { $CALLS[] = 'KAPALIYKEN ÇAĞRI'; return []; };
pm_kanal_tick();
ok(pm_kanal_store(fn(&$s) => $s['outbound']['out_k1']['state']) === 'pending' && !in_array('KAPALIYKEN ÇAĞRI', $CALLS, true), 'enabled=false → tick hiçbir şey göndermez (kill switch)');

echo "\nSONUÇ: $pass geçti, $fail kaldı  (geçici dizin: $tmp)\n";
exit($fail ? 1 : 0);
