<?php
declare(strict_types=1);
/* Yerel test uç noktası (php -S ile): sahte panel/lib kancaları + gerçek feature.php + api.php.
   Ortam: PM_TEST_TMP (geçici kök), PM_TEST_LIB (lib.php yolu). Meta/OpenAI yok. */
$tmp = getenv('PM_TEST_TMP'); $libPath = getenv('PM_TEST_LIB');
$PHONE = '106000000000001'; $PATRON = '905000000001'; $SECRET = 'test-app-secret';
define('PM_DATA', "$tmp/data"); define('PM_QUEUE', "$tmp/queue"); define('PM_OFFLINE_TEST', true); define('PM_KANAL_DIR', "$tmp/kanal");
function numaralarOku(): array { global $PATRON; return [$PATRON => ['ad' => 'Patron', 'firma' => 'PortatifEv']]; }
function ayarlarOku(): array { return ['openai_key' => 'sk-test-not-real-key', 'model' => 'gpt-4o-mini']; }
$GLOBALS['pm_test_remote'] = function ($url, $token, $method, $body) use ($tmp) {
    $log = "$tmp/meta_calls.jsonl"; file_put_contents($log, json_encode(['url' => $url, 'method' => $method, 'body' => is_string($body) ? json_decode($body, true) : 'multipart'], JSON_UNESCAPED_UNICODE)."\n", FILE_APPEND);
    if (str_ends_with($url, '/media')) return ['id' => '918800000000001'];
    $to = json_decode($body, true)['to']; $n = count(file($log));
    return ['contacts' => [['input' => $to, 'wa_id' => $to]], 'messages' => [['id' => 'wamid.OUT'.$n]]];
};
require $libPath; require PM_KANAL_DIR.'/feature.php'; require PM_KANAL_DIR.'/api.php';
pm_kanal_api();
