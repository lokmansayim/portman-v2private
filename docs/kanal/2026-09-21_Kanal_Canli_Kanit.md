# Portman Kanal v1 — canlı kurulum ve kanıt (21 Eylül 2026, 21:03–21:57)

Kaynak: sunucudaki `portman_app/kanal/state.json`, `health.json`, `worker.log`, `self-test-result.json`, `preflight.json` ve Meta durum
webhook'ları (DirectAdmin dosya yöneticisi üzerinden okundu). Telefon → `…1244` (PATRON), wamid'ler kısaltıldı. Saatler +03:00.

## 1. Sunucuda değişenler (hepsi geri alınabilir; `GERI_ALMA.md`)
| # | Değişiklik | Kim | Doğrulama |
|---|---|---|---|
| 1 | `portman_app/portman_kanal_v1.0_20260921.zip` yüklendi (621.223 B) ve açıldı → `portman_app/kanal/` (45 dosya, 2.983.949 B) | Lokman yükledi (dosya seçimi), Claude açtı | sha256 feature.php `91c954a6…`, worker.py `631d7b0d…` = paket |
| 2 | Cron eklendi: `* * * * * task2/venv/bin/python portman_app/kanal/worker.py >> kanal/worker.log 2>&1` | Claude | `CMD_API_CRON_JOBS` |
| 3 | **Görev 2 Python cron'u silindi** (`task2/worker.py` satırı) — bellek sınırı bulgusu (aşağıda) | Lokman onayladı (CONFIRM) | cron listesi 2 satır |
| 4 | `portman_app/worker.php` → yedek `worker.before-kanal-20260921.php` (1.783 B, sha `020b8fd8…`); yeni `worker.php` = `install/worker.kanal.candidate.php` (2.256 B, sha `b131914…`) | rename Claude, copy Lokman | hash |
| 5 | `developer/webhook.php` → yedek `webhook.before-kanal-20260921.php` (7.276 B, sha `6951c026…`); yeni `webhook.php` = `install/webhook.kanal.candidate.php` (8.033 B, sha `baf42c36…`) | copy Lokman, rename Claude | hash; GET → HTTP 403 (normal) |
| 6 | `kanal/settings.json`: enabled true, dry_run true → sonra false | Claude (panel editörü) | JSON geçerli |
| 7 | `kanal/beyin/konusma.py` güncellendi (varyant tekilleştirme düzeltmesi; sha `d98fb026…`) | Lokman seçti, Claude yükledi | hash |
| 8 | `task3/settings.json` ve `task2/settings.json` → `enabled: false` | Claude (panel editörü) | JSON geçerli |
Sohbet botu (`ai.php`) ve panel dosyalarına dokunulmadı. `task2/venv`'e `shapely 2.1.2` + `pydantic 2.13.5` kuruldu (worker.py kendisi; `install-report.json`).

## 2. Öz-test (sunucuda, 21:29:01–21:29:28, hiçbir şey göndermeden)
ezdxf 1.4.4 · shapely 2.1.2 · pydantic 2.13.5 · PyMuPDF 1.26.0 · Python 3.11.9 · Beyin 15/15 · İş Emri (P6001 ayna_x) · Motor **21,9 s**, doğrulama geçti ·
**Gerçek OpenAI çağrısı**: gpt-4o-mini-2024-07-18, 3.082 girdi + 225 çıktı token, 4,4 s → niyet yeni_talep, P6001, ayna_x, pencere 120x180 doğru okundu.
`preflight.json → ready: true` (token/secret var, Patron kaydı bulundu, anahtar dosyası var, venv var, referans dosyaları var).

## 3. Gerçek mesajlar (Patron telefonu → 444 80 56)
| # | Mesaj (gelen) | Beyin | Motor | Gönderim | Toplam |
|---|---|---|---|---|---|
| 1 | 21:43:04 "Katalogdaki P6001 modelinin aynalanmış halini istiyorum" | yeni_talep, ayna_x; 3.068+89 token, 2,8 s | `PM-PATRON-…-16245` r01, 16,2 s, geçti | **kuru çalışma** → 2 satır `held` (gönderilmedi) | 19,3 s işleme |
| 2 | 21:47:34 "P6001 aynalı olsun, yatak odası 1 penceresi 120x180" | revizyon; 3.118+230 token, 8,5 s | `…-16491` r02, 16,2 s, geçti — **hata:** ayna iki kez uygulandı (düz plan) | metin kabul 21:49:02 → read 21:49:09; PDF kabul 21:49:07 → read 21:49:09 | **1 dk 35 sn** |
| 3 | 21:53:54 "Planı aynalı olarak tekrar gönderir misin?" (düzeltme sonrası) | revizyon; 3.109+173 token, 2,6 s | `…-16845` r03, 13,3 s, geçti — ayna **bir kez** + pencere 120x180 | metin read 21:55:03; PDF read 21:55:08 | **1 dk 14 sn** |
Sohbet botu hiçbirine cevap vermedi; giden mesajlar panelin sohbet kaydına da yazıldı (`panel_logged: true`).

## 4. Bulgular
- **Bellek sınırı (LVE):** iki Python cron'u aynı saniyede PyMuPDF yüklerken `MemoryError` (task2/worker.log'da 21:19'dan itibaren her dakika iz).
  Görev 2 Python cron'u silinince kanal worker'ı sorunsuz. Tek Python görevi + PHP tick bu hostingte çalışıyor; ikinci ağır Python
  süreci eklenemez → VPS gerekçesi.
- **Beyin hatası (düzeltildi):** revizyonda önceki taslaktaki `ayna_x` ile yeni mesajdaki `ayna_x` birleşince iki kez ayna = düz plan.
  `konusma.birlestir` artık listeleri tekilleştiriyor (ayna bayrak gibi; pencere değişikliği mahal başına sonuncu). Yerel 15/15 + 12/12, canlı #3 ile kanıtlandı.
- Token maliyeti mesaj başına ~3,1–3,4 bin (bulut sisteminin 200 bin tokeninin ~%1,6'sı); süre 1,2–1,6 dk (bulutta 3,5 dk).

## 5. Şu anki anahtarlar
`kanal/settings.json`: **enabled true, dry_run false, mode patron** (yalnız Patron; bayiler sohbet botunda). `task2`/`task3` enabled false; Görev 2 Python cron'u yok.
Durdurmak için: `kanal/settings.json → "enabled": false`.
