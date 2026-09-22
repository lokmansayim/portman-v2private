# Portman Kanal v1 — teslim notu (21 Eylül 2026, 20:55)

**Ne:** 444 80 56 hattından **Patron** numarasıyla gelen mesajı alıp, hosting'de anlayıp (Beyin: LLM çıkarım + kural), çizip (Motor: DXF → doğrula → PDF)
aynı hatta **gerçek metin + PDF** olarak geri gönderen paket: `portman_kanal_v1.0_20260921.zip` → sunucuda `portman_app/kanal/`.
Sunucuya **bu akşam dokunulmadı**; kurulum yarın DirectAdmin'den, sen izlerken, `kanal/install/KURULUM.md` adımlarıyla.

## Bu akşam yapılan / kanıtı
| İş | Kanıt |
|---|---|
| `kanal/feature.php` (PHP): imzalı webhook'tan yakalama, kuyruk, Meta'ya metin + PDF gönderimi, teslimat izleme, panele yayın, preflight | `php -l` temiz; `tests/offline_test.php` **30/30** (gerçek `lib.php` mantığıyla, sahte Meta) |
| `kanal/worker.py` (Python): kuyruk → Beyin → Motor → giden satırlar; eksik paketleri venv'e kurma; öz-test | `tests/e2e_local.py` **12/12** (PHP yakalama → Python → PDF 704 KB, doğrulama geçti → PHP tick → 3 Meta çağrısı → onay turu) |
| Öz-test (sunucuda ilk dakikada kendiliğinden koşar, hiç göndermez) | yerelde **passed 12,7 s**: Beyin 15/15, İş Emri, Motor doğrulaması |
| Beyin hosting'e hazır: `openai_chat` arka ucu (sohbet botunun kanıtlı API yolu), token/süre ölçümü, şema hatasında tek tekrar, anahtar panel dosyasından | harness 15/15 |
| Kurulum metinleri: cron satırı, webhook.php 3 ekleme, worker.php 5 satır, geri alma | `install/` |

## Canlıda doğrulanamayan (yarın görülecek)
- Gerçek OpenAI çağrısı (öz-test anahtarı bulursa **tek** çağrı yapar ve token/süre yazar).
- Gerçek Meta gönderimi (kuru çalışma `dry_run: true` ile önce üretim, sonra gerçek).
- Hosting Python'una `shapely` + `pydantic` kurulumu (`install-report.json`), panel dosya yolları (`preflight.json → ready`).

## Sıradaki tek iş
Yarın kurulum + Patron telefonundan ilk gerçek mesaj. Sonra: ön onay pafta formatı (akssız plan + görünüşler + künye), diğer katalog şablonları, DB.
