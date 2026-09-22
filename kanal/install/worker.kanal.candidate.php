<?php
// Installed outside the public web directory; invoked by the hosting scheduler.
if (isset($_SERVER['REQUEST_METHOD'])) { http_response_code(404); exit; }
umask(0077);
require '/home/portatifevcom/domains/portatifev.com/public_html/portman/lib.php';
// Reuse existing chat functions and settings in this server-only scheduled process.
if (is_file(__DIR__.'/task2/natural/feature.php')) {
    try {
        require_once '/home/portatifevcom/domains/portatifev.com/public_html/developer/config.php';
        require_once '/home/portatifevcom/domains/portatifev.com/public_html/developer/ai.php';
        require_once __DIR__.'/task2/feature.php';
        require_once __DIR__.'/task2/natural/feature.php';
        pm_nl_run(); pm_nl_health();
        if (is_file(__DIR__.'/task2/natural/self-test.php')) require __DIR__.'/task2/natural/self-test.php';
    } catch (Throwable $e) { error_log('Portman natural worker stopped; inspect private state.'); }
}
try { pm_archive_pending(45); }
catch (Throwable $e) { error_log('Portman archive worker could not complete.'); }
// Isolated Task 2 sender; generation is a separate scheduled Python job.
if (is_file(__DIR__.'/task2/feature.php')) {
    try { require_once __DIR__.'/task2/feature.php'; pm_house_run(); pm_house_publish(); pm_house_health(); }
    catch (Throwable $e) { error_log('Portman house sender stopped; inspect private state.'); }
}

// PORTMAN CLOUD: existing scheduler; no local/hosting CAD execution.
if (is_file(__DIR__.'/task3/feature.php')) {
    try { require_once '/home/portatifevcom/domains/portatifev.com/public_html/developer/config.php'; require_once __DIR__.'/task3/feature.php'; pm_cloud_tick(); }
    catch (Throwable $e) { error_log('Portman cloud worker stopped; inspect private task3 state.'); }
}

// PORTMAN KANAL: gönderici/yayıncı (metin + PDF); üretici ayrı cron'daki kanal/worker.py (task2/venv Python). Ana anahtar kanal/settings.json → enabled.
if (is_file(__DIR__.'/kanal/feature.php')) {
    try { require_once '/home/portatifevcom/domains/portatifev.com/public_html/developer/config.php'; require_once __DIR__.'/kanal/feature.php'; pm_kanal_tick(); }
    catch (Throwable $e) { error_log('Portman kanal tick stopped; inspect private kanal state.'); }
}
