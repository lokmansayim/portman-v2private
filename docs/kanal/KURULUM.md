# PORTMAN KANAL v1 — kurulum adımları (yarın, DirectAdmin'den, Lokman izlerken)

Hedef: 444 80 56 hattına **Patron numarasından** gelen mesaj → hosting'de Beyin (LLM çıkarım + kural) → Motor (PDF) → Patron'a **gerçek**
metin + PDF. Sunucuya dokunulan yerler: `portman_app/kanal/` (yeni klasör), `portman_app/worker.php` (sona 5 satır), `developer/webhook.php`
(3 ekleme), 1 cron satırı, `task2/settings.json` + `task3/settings.json` (enabled=false). Başka hiçbir dosya değişmez.

Her adım geri alınabilir (bkz. `GERI_ALMA.md`). Sır (API anahtarı, parola, erişim jetonu) hiçbir dosyaya, sohbete, rapora yazılmaz.

## 0. Ön kontrol (5 dk, salt okunur)
- [ ] `developer/webhook.php` canlı içeriği okunur, 20 Eylül paketindeki `webhook.candidate.php` ile karşılaştırılır (sha256). Sonuç not edilir.
- [ ] `portman_app/worker.php` canlı içeriği okunur (bugün 21.09 hash'i `gorev3/worker.candidate.php` ile aynıydı).
- [ ] `task2/venv/bin/python` var (Görev 2 cron'u bununla çalışıyor).

## 1. Yedek (DirectAdmin dosya yöneticisi → Copy)
- [ ] `developer/webhook.php` → `developer/webhook.before-kanal-20260922.php`
- [ ] `portman_app/worker.php` → `portman_app/worker.before-kanal-20260922.php`
- [ ] `portman_app/task2/settings.json` → `task2/settings.before-kanal-20260922.json`; `task3/settings.json` → `task3/settings.before-kanal-20260922.json`

## 2. Paketi yükle
- [ ] ZIP'i dosya yöneticisiyle `/home/portatifevcom/portman_app/` altına yükle → **Extract** → `portman_app/kanal/` oluşur (feature.php, worker.py,
      settings.json, beyin/, motor/, is_emri/, ref_source-6x8.dxf, ref_h-connector.json, DejaVuSans.ttf, self-test-request.json, tests/, install/).
- [ ] `kanal/settings.json` **enabled=false** kalır (paket böyle gelir).

## 3. Cron satırı (yalnız Python üretici)
- [ ] `install/cron.txt` içindeki satırı ekle (dakikada bir; Görev 2'nin venv Python'u).
- [ ] 1–3 dk bekle → `kanal/install-report.json` oluşur (shapely + pydantic venv'e kurulur; `returncode: 0` beklenir).
- [ ] Sonraki dakika → `kanal/self-test-result.json` **state: passed** (15 mesaj kural koşumu, İş Emri, Motor PDF doğrulaması; hiçbir şey
      gönderilmez) ve `kanal/worker-health.json` (checked_at her dakika ilerler). Öz-testteki `llm` adımı: anahtar dosyası bulunursa
      **tek** gerçek OpenAI çağrısı yapar (birkaç bin token) ve token/süre yazar; bulunmazsa "atlandı" der.
      - `atlandı: anahtar bulunamadı` görünürse: `settings.json → ayarlar_json` yolu panelin gerçek ayar dosyasını göstermiyordur; yol düzeltilir,
        `self-test-result.json` silinir → öz-test bir dakika sonra yeniden koşar.

## 4. PHP tarafı
- [ ] `portman_app/worker.php` sonuna `install/worker.php.yama.txt` bloğu (ya da dosya bütünüyle `install/worker.kanal.candidate.php`).
- [ ] 1 dk bekle → `kanal/health.json` ve `kanal/preflight.json` oluşur. **preflight.json → ready: true** olmalı
      (access_token/app_secret var, Patron kaydı bulundu, ayarlar_json'da anahtar var, venv var, referans dosyaları var).
- [ ] `developer/webhook.php`'ye 3 ekleme (`install/webhook.php.yama.txt`). Kaydettikten sonra tarayıcıdan `https://portatifev.com/developer/webhook.php`
      GET → 403 (normal; sözdizimi hatasında 500 görülürdü).

## 5. Diğer görevleri kapat (aynı mesajı iki modül işlemesin)
- [ ] `task3/settings.json` → `"enabled": false`   (Görev 3, OpenAI bulut CAD)
- [ ] `task2/settings.json` → `"enabled": false`   (Görev 2, sabit 6x8)
- Sohbet botu **kapatılmaz**: Patron modunda kanal Patron mesajlarını sahiplenir, bot onlara cevap vermez; diğer numaralar bugünkü gibi.

## 6. Kuru çalışma (gönderim yok)
- [ ] `kanal/settings.json`: `"enabled": true`, `"dry_run": true` (enabled_at 0 kalabilir: 15 dakikadan eski mesaj zaten alınmaz).
- [ ] Lokman Patron telefonundan yazar: **"Katalogdaki P6001 modelinin aynalanmış halini istiyorum"**
- [ ] 1–2 dk: `kanal/state.json` → inbound satırı `done`, result.eylem `is_emri`, result.llm token/süre; outbound 2 satır **held**;
      `kanal/projects/PM-PATRON-.../r01/` altında PDF + validation.json (passed true). Sohbet botu cevap vermemiş olmalı.
- [ ] PDF panelden/dosya yöneticisinden açılıp bakılır.

## 7. Gerçek gönderim
- [ ] `"dry_run": false` → Lokman **yeni** bir mesaj yazar (held satırlar gönderilmez; yeni mesaj gerekir), örn. "P6001 aynalı, yatak odası 1 penceresi 120x180".
- [ ] Beklenen: ~1 dk içinde metin cevabı (+ "— teknik:" satırı), hemen ardından PDF belge. `state.json` outbound → accepted → sent/delivered/read.
- [ ] Başarısızsa: `kanal/health.json → error`, `worker.log`, `state.json → error` alanları; hiçbir satır otomatik tekrar gönderilmez.

## 8. Kill switch (her an)
- `kanal/settings.json → "enabled": false` → webhook hiçbir mesajı sahiplenmez (bot bugünkü gibi), tick hiçbir şey göndermez, worker üretmez.
- Sadece gönderimi durdurmak: `"dry_run": true`.

## Zaman beklentisi (mesaj → PDF)
Webhook anında kuyruk (0 s) → Python cron ≤ 60 s bekleme + LLM 2–6 s + Motor 12–40 s → PHP cron ≤ 60 s → Meta. Toplam tipik **1,5–3 dk**.
