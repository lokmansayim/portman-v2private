<?php
require __DIR__ . '/config.php';
require __DIR__ . '/ai.php';

/* 1) DOGRULAMA (Meta, webhook adresini kaydederken GET ile gelir) */
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (($_GET['hub_mode'] ?? '') === 'subscribe'
        && ($_GET['hub_verify_token'] ?? '') === $VERIFY_TOKEN) {
        header('Content-Type: text/plain');
        echo $_GET['hub_challenge'] ?? '';
    } else {
        http_response_code(403);
    }
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit;
}

/* 2) GELEN BILDIRIMLER */
$yeniMesajlar = [];   // otomatik yanit icin: [wa_id, isim, tip, icerik]
$pmNaturalOwned = [];
$pmKanalOwned = [];   // PORTMAN KANAL: sahiplenilen mesaj kimlikleri

try {
    $portmanRaw = (string)file_get_contents('php://input');
    require_once __DIR__ . '/portman_bridge.php';
    portmanBridgeCapture($portmanRaw, $_SERVER['HTTP_X_HUB_SIGNATURE_256'] ?? '');
    // Portman persists the signed queue without requiring a browser or local computer.
    if (is_file(dirname(__DIR__) . '/portman/lib.php') && is_file('/home/portatifevcom/portman_app/config.json')) {
        try { require_once dirname(__DIR__) . '/portman/lib.php'; pm_sync(); }
        catch (Throwable $ignored) { error_log('Portman queue import deferred to scheduled worker.'); }
    }
    // PORTMAN PDF TEST: isolated module; settings.json disables sending.
    $pmPdfModule = '/home/portatifevcom/portman_app/test_pdf/feature.php';
    if (is_file($pmPdfModule) && function_exists('pm_config')) {
        try {
            require_once $pmPdfModule;
            pm_pdf_capture($portmanRaw, $_SERVER['HTTP_X_HUB_SIGNATURE_256'] ?? '');
        } catch (Throwable $ignored) { error_log('Portman PDF capture failed; no unverified send.'); }
    }
    // Task 2 only queues signed requests. Drawing runs in the server scheduler.
    $pmHouseModule='/home/portatifevcom/portman_app/task2/feature.php';
    if (is_file($pmHouseModule) && function_exists('pm_config')) {
        try { require_once $pmHouseModule; pm_house_capture($portmanRaw,$_SERVER['HTTP_X_HUB_SIGNATURE_256']??''); }
        catch (Throwable $ignored) { error_log('Portman house capture stopped; no unverified send.'); }
    }
    // Natural drawing requests use the same chat connection with one validated tool.
    $pmNaturalModule='/home/portatifevcom/portman_app/task2/natural/feature.php';
    if (is_file($pmNaturalModule) && function_exists('pm_house_store')) {
        try { require_once $pmNaturalModule; $pmNaturalOwned=pm_nl_capture($portmanRaw,$_SERVER['HTTP_X_HUB_SIGNATURE_256']??''); }
        catch (Throwable $ignored) { error_log('Portman natural capture failed; inspect private state.'); }
    }
    // Task 3: verified WhatsApp input starts an OpenAI-hosted Portman job.
    $pmCloudModule='/home/portatifevcom/portman_app/task3/feature.php';
    if (is_file($pmCloudModule) && function_exists('pm_config')) {
        try { require_once $pmCloudModule; pm_cloud_capture($portmanRaw,$_SERVER['HTTP_X_HUB_SIGNATURE_256']??''); }
        catch (Throwable $ignored) { error_log('Portman cloud capture stopped; inspect private state.'); }
    }
    // PORTMAN KANAL: izinli göndericilerin (Patron / kayıtlı bayi) mesajlarını kural katmanı kuyruğuna alır; sahiplenilenler sohbet botuna gitmez.
    $pmKanalModule='/home/portatifevcom/portman_app/kanal/feature.php';
    if (is_file($pmKanalModule) && function_exists('pm_config')) {
        try { require_once $pmKanalModule; $pmKanalOwned=pm_kanal_capture($portmanRaw,$_SERVER['HTTP_X_HUB_SIGNATURE_256']??''); }
        catch (Throwable $ignored) { error_log('Portman kanal capture stopped; inspect private kanal state.'); }
    }
    $data = json_decode($portmanRaw, true);
    if (!is_array($data)) { http_response_code(200); exit; }

    foreach (($data['entry'] ?? []) as $entry) {
        foreach (($entry['changes'] ?? []) as $change) {
            $value = $change['value'] ?? [];

            $isimler = [];
            foreach (($value['contacts'] ?? []) as $c) {
                if (!empty($c['wa_id'])) $isimler[$c['wa_id']] = $c['profile']['name'] ?? '';
            }

            foreach (($value['messages'] ?? []) as $msg) {
                // This exact Patron command never enters the normal chatbot.
                if (function_exists('pm_pdf_is_command') && pm_pdf_is_command($msg)) continue;
                if (function_exists('pm_house_is_command') && pm_house_is_command($msg)) continue;
                if (isset($pmNaturalOwned[$msg['id']??''])) continue;
                if (function_exists('pm_cloud_owned') && pm_cloud_owned($msg)) continue;
                $from = (string)($msg['from'] ?? '');
                if ($from === '') continue;
                $msgId = (string)($msg['id'] ?? '');
                if (mesajVarMi($msgId)) continue;          // Meta ayni bildirimi tekrarladi

                $tip  = $msg['type'] ?? 'text';
                $isim = $isimler[$from] ?? ($value['contacts'][0]['profile']['name'] ?? '');

                switch ($tip) {
                    case 'text':
                        $icerik = $msg['text']['body'] ?? '';
                        break;
                    case 'image': case 'video': case 'audio': case 'document': case 'sticker':
                        $yol    = medyaIndir($msg[$tip]['id'] ?? '');
                        $baslik = $msg[$tip]['caption'] ?? ($msg[$tip]['filename'] ?? '');
                        $icerik = ($yol ?: '[indirilemedi]') . '|' . $baslik;
                        break;
                    case 'location':
                        $icerik = '[konum] ' . ($msg['location']['latitude'] ?? '') . ',' . ($msg['location']['longitude'] ?? '');
                        break;
                    case 'button':
                        $icerik = $msg['button']['text'] ?? '';
                        break;
                    case 'interactive':
                        $icerik = $msg['interactive']['button_reply']['title']
                               ?? $msg['interactive']['list_reply']['title'] ?? '';
                        break;
                    case 'reaction':
                        $icerik = '[tepki] ' . ($msg['reaction']['emoji'] ?? '');
                        break;
                    default:
                        $icerik = '[' . $tip . ']';
                }

                mesajKaydet($from, $isim, 'gelen', $tip, $icerik, $msgId);
                if (isset($pmKanalOwned[$msgId])) continue;   // PORTMAN KANAL sahiplendi: sohbet botu cevap vermez (mesaj panelde kayıtlı)

                /* Meta'nin geciktirip tekrar gonderdigi eski mesajlara (15 dk+) otomatik yanit verme */
                $zaman = (int)($msg['timestamp'] ?? time());
                if ($tip !== 'reaction' && time() - $zaman < 900) $yeniMesajlar[] = [$from, $isim, $tip, $icerik];
            }

            foreach (($value['statuses'] ?? []) as $st) {
                if (empty($st['id'])) continue;
                $durum = $st['status'] ?? '';
                if ($durum === 'failed' && !empty($st['errors'][0]['title'])) {
                    hataLog('Gonderim basarisiz ' . $st['id'] . ': ' . $st['errors'][0]['title']);
                }
                durumGuncelle($st['id'], $durum);
            }
        }
    }
} catch (Throwable $e) {
    hataLog('webhook: ' . $e->getMessage());
    http_response_code(500);
    exit;
}

/* 3) OTOMATIK YANIT: once Meta'ya 200 don, sonra yapay zekayi cagir */
erkenYanit();
// Runs entirely on the existing hosting server, after the webhook acknowledgement.
if (function_exists('pm_pdf_run')) {
    try { pm_pdf_run(); pm_pdf_publish(); pm_pdf_health(); }
    catch (Throwable $ignored) { error_log('Portman PDF processing stopped; inspect persistent PDF state.'); }
}
foreach ($yeniMesajlar as [$wa_id, $isim, $tip, $icerik]) {
    try {
        otomatikYanit($wa_id, $isim, $tip, $icerik);
    } catch (Throwable $e) {
        hataLog("otomatikYanit ($wa_id): " . $e->getMessage());
    }
}
