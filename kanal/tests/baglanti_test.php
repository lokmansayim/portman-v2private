<?php
declare(strict_types=1);
/*
 PORTMAN KANAL — İE-02 bağlantı testi (context_id, giden_durum). Çevrimdışı; offline_test.php ile aynı düzen. Gerçek portman/lib.php (ya da paketteki lib.snapshot.php) + PM_OFFLINE_TEST kancaları:
 Meta'ya HİÇBİR bağlantı yok (pm_remote sahte), OpenAI yok, geçici PM_DATA. Çalıştırma:
   php tests/baglanti_test.php [lib.php yolu]
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
require dirname(__DIR__).'/api.php';
function oid(string $x): string { return 'out_'.substr(hash('sha256', $x), 0, 24); }

echo "1) Yakalama: alıntılanan mesajın kimliği (context_id)\n";
settings(['worker' => 'vps']);
$m1 = msg('wamid.C1', $PATRON, 'onaylıyorum'); $m1['context'] = ['from' => '4448056', 'id' => 'wamid.GIDEN42'];
$m2 = msg('wamid.C2', $PATRON, 'P6001 aynalı');
$m3 = msg('wamid.C3', $PATRON, 'tamam'); $m3['context'] = ['id' => 'baska-bir-sey'];
$raw = payload([$m1, $m2, $m3], [], [['wa_id' => $PATRON, 'profile' => ['name' => 'Lokman']]]);
pm_kanal_capture($raw, sig($raw));
$in = pm_kanal_store(fn(&$s) => $s['inbound']);
ok(($in['wamid.C1']['context_id'] ?? null) === 'wamid.GIDEN42', 'alıntılı cevap: context_id kuyruk satırında');
ok(array_key_exists('context_id', $in['wamid.C2']) && $in['wamid.C2']['context_id'] === null, 'alıntısız mesaj: context_id null');
ok($in['wamid.C3']['context_id'] === null, 'wamid. ile başlamayan alıntı kimliği alınmaz');
$c = pm_kanal_api_claim(pm_kanal_settings());
ok(($c['job']['id'] ?? '') !== '' && array_key_exists('context_id', $c['job']), 'claim: iş satırı context_id ile ajana gider');

echo "2) giden_durum: kabul (API) ve teslim (Meta bildirimi) ayrı\n";
$now = time(); $T = oid('metin'); $D = oid('belge'); $U = oid('belirsiz'); $H = oid('bekleyen');
$pdf = "%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"; $pdfPath = PM_KANAL_DIR.'/projects/PM-TEST/r01/Portman_PM-TEST_r01.pdf'; file_put_contents($pdfPath, $pdf);
$satir = fn($id, $seq, $ek = []) => array_replace(['id' => $id, 'kind' => 'text', 'to' => $PATRON, 'body' => 'metin', 'tur' => 'cevap', 'inbound_id' => 'wamid.C2', 'seq' => $seq,
    'state' => 'pending', 'wamid' => null, 'media_id' => null, 'attempts' => 0, 'error' => null, 'created_at' => $now + $seq, 'updated_at' => $now], $ek);
pm_kanal_store(function (&$s) use ($satir, $T, $D, $pdfPath, $pdf) {
    $s['outbound'][$T] = $satir($T, 1);
    $s['outbound'][$D] = $satir($D, 2, ['kind' => 'document', 'tur' => 'belge', 'body' => 'PM-TEST r01', 'file' => $pdfPath, 'filename' => 'Portman_PM-TEST_r01.pdf',
        'mime' => 'application/pdf', 'sha256' => hash('sha256', $pdf)]);
});
pm_kanal_tick();
$o = pm_kanal_store(fn(&$s) => $s['outbound']);
ok($o[$T]['state'] === 'accepted' && $o[$D]['state'] === 'accepted', 'tik: iki satır API tarafından kabul edildi');
$teslimTs = time() - 5;
$rawS = payload([], [['id' => $o[$D]['wamid'], 'status' => 'delivered', 'timestamp' => (string)$teslimTs, 'recipient_id' => $PATRON],
                     ['id' => $o[$D]['wamid'], 'status' => 'read', 'timestamp' => (string)($teslimTs + 3), 'recipient_id' => $PATRON]]);
pm_kanal_capture($rawS, sig($rawS));
pm_kanal_store(function (&$s) use ($satir, $U, $H) { $s['outbound'][$U] = $satir($U, 3, ['state' => 'uncertain', 'attempts' => 1, 'error' => 'Gönderim sonucu belirsiz']);
                                                   $s['outbound'][$H] = $satir($H, 4, ['state' => 'held', 'error' => 'Gönderilmedi: reply_window_closed']); });
$ids = [$T, $D, $U, $H, oid('olmayan'), 'out_KOTU', 'x'];
$g = pm_kanal_api_giden_durum(['ids' => $ids]); $g = json_decode(json_encode($g), true);
ok(count($g['satirlar']) === 4 && !isset($g['satirlar'][oid('olmayan')]), 'yalnız var olan ve biçimi doğru kimlikler döner');
ok($g['satirlar'][$T]['state'] === 'accepted' && str_starts_with((string)$g['satirlar'][$T]['wamid'], 'wamid.') && is_int($g['satirlar'][$T]['request_accepted_at'])
   && $g['satirlar'][$T]['delivered_at'] === null, 'metin: API kabul etti; teslim bildirimi yok → delivered_at null (kabul teslim sayılmaz)');
ok($g['satirlar'][$D]['state'] === 'read' && $g['satirlar'][$D]['delivery_state'] === 'read' && $g['satirlar'][$D]['delivered_at'] === $teslimTs,
   'belge: ilk "delivered" anı teslim zamanı (Meta zamanı), durum read');
ok($g['satirlar'][$U]['state'] === 'uncertain' && $g['satirlar'][$H]['state'] === 'held', 'belirsiz ve tutulan satırlar olduğu gibi');
$cok = []; for ($i = 0; $i < 250; $i++) $cok[] = oid("n$i");
ok(count(json_decode(json_encode(pm_kanal_api_giden_durum(['ids' => $cok])), true)['satirlar']) === 0, 'en çok 200 kimlik okunur; boş yanıt nesne');

echo "3) API girişi: giden_durum op'u ve kimlik doğrulama\n";
$tok = bin2hex(random_bytes(32)); file_put_contents(PM_KANAL_DIR.'/api_token.txt', $tok."\n");
ob_start(); @pm_kanal_api(json_encode(['ids' => [$D]]), [], [], ['op' => 'giden_durum'], ['token' => $tok]); $cev = json_decode((string)ob_get_clean(), true);
ok(($cev['satirlar'][$D]['state'] ?? '') === 'read', 'op=giden_durum doğru anahtarla çalışır');
ob_start(); @pm_kanal_api(json_encode(['ids' => [$D]]), [], [], ['op' => 'giden_durum'], ['token' => str_repeat('0', 64)]); $cev = json_decode((string)ob_get_clean(), true);
ok(($cev['error'] ?? '') === 'unauthorized', 'yanlış anahtar → yetkisiz');
ob_start(); @pm_kanal_api(json_encode(['ids' => []]), [], [], ['op' => 'settings'], ['token' => $tok]); $cev = json_decode((string)ob_get_clean(), true);
ok(($cev['api'] ?? '') === 'kanal-api-v1.2', 'settings: api sürümü v1.2 (ajan kalıcı modda bunu ister)');
ok(!str_contains((string)file_get_contents(PM_KANAL_DIR.'/state.json'), $tok), 'eşleşme anahtarı state.json\'a yazılmadı');

echo "\nSONUÇ: $pass geçti, $fail kaldı  (geçici dizin: $tmp)\n";
exit($fail ? 1 : 0);
