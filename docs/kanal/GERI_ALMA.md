# Geri alma (her adım tek başına yeter; sıra önemsiz)

| Ne | Nasıl | Etki |
|---|---|---|
| Kanalı durdur | `portman_app/kanal/settings.json` → `"enabled": false` | Webhook sahiplenmez, tick göndermez, worker üretmez. Sohbet botu bugünkü gibi. |
| Gönderimi durdur | `"dry_run": true` | Üretim sürer, giden satırlar `held` olur; asla gönderilmez. |
| webhook.php | `developer/webhook.before-kanal-20260921.php` → `webhook.php` (Copy/rename) ya da 3 eklemeyi sil | Kanal yakalaması tamamen çıkar. |
| worker.php | `portman_app/worker.before-kanal-20260921.php` → `worker.php` ya da sondaki 5 satırı sil | PHP tick çıkar (gönderim/sağlık yok). |
| Cron | DirectAdmin > Cron Jobs → `kanal/worker.py` satırını sil | Python üretici çıkar. |
| Görev 2/3 | `task2/settings.json`, `task3/settings.json` → yedeklerinden geri (`enabled: true`) | Eski sabit-komut akışları geri gelir. |
| Paket | `portman_app/kanal/` klasörünü sil (ya da yeniden adlandır) | `is_file()` kontrolleri sayesinde webhook/worker hata vermez. |

Not: Kanal, mevcut dosyalardan hiçbirini yerinde düzenlemez (webhook.php ve worker.php'deki eklemeler dışında); `store.json`'a yalnız
Görev 3 ile aynı biçimde `outgoing` satırı ekler ve gelen mesajları `pm_ingest` ile (idempotent) kaydeder. `task2/venv`'e eklenen
`shapely` ve `pydantic` paketleri Görev 2'yi etkilemez (house.py onları kullanmaz).

Yedek adları kurulum günü (21.09.2026) tarihiyle oluşturuldu: `worker.before-kanal-20260921.php`, `webhook.before-kanal-20260921.php` — geri almadan önce DirectAdmin'de dosyanın gerçekten bu adla var olduğunu ve sha256'sının `2026-09-21_Kanal_Canli_Kanit.md`'deki değerle tuttuğunu doğrulayın (denetim bulgusu F07).
