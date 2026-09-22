<?php
declare(strict_types=1);
/* PORTMAN KANAL — VPS işçisi için hosting API uç noktası. Yer: public_html/developer/kanal_api.php
   Kimlik: X-Portman-Token == portman_app/kanal/api_token.txt (dosya yoksa 503 "unpaired").
   Yalnız kanal/api.php'deki işlemler; WhatsApp anahtarı dışarı çıkmaz, gönderim yalnız cron tick'te. */
umask(0077);
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'HEAD') { http_response_code(200); exit; }
require __DIR__.'/config.php';                                            // numaralarOku, ayarlarOku, mesajKaydet
require dirname(__DIR__).'/portman/lib.php';                              // pm_config, pm_store, pm_read, pm_write, pm_contact …
$kanal = '/home/portatifevcom/portman_app/kanal';
if (!is_file($kanal.'/feature.php') || !is_file($kanal.'/api.php')) { http_response_code(503); header('Content-Type: application/json'); echo '{"error":"kanal_missing"}'; exit; }
require $kanal.'/feature.php';
require $kanal.'/api.php';
pm_kanal_api();
