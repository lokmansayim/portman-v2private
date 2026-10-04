---
paths:
  - "kanal/**"
  - "vps/**"
  - "hosting/**"
---

# Kanal, VPS ve hosting kuralları (K06, K07, K09, K12–K14, D-03, D-04)

- Hibrit mimari: hosting = kontrol düzlemi (Meta webhook, kuyruk, gönderim, WhatsApp anahtarı); VPS = üretici; ajan yalnız dışarıdan bağlanır, WhatsApp'a kendisi göndermez (K12, `vps/agent.py`).
- Buradaki her değişiklik canlıya gidebilir: paket sha'sı değişir, ajan kendini günceller (K14). Bu yüzden `kanal/`, `vps/` ve paket dosyalarında değişiklik = **canlı değişiklik adayı**; Lokman'ın ayrı onayı olmadan paket üretilmez, hosting'e dosya yazılmaz.
- `hosting/` canlı dosyaların kayıt kopyasıdır; düzenlenmez, yalnız karşılaştırma için okunur.
- Öz-test asla WhatsApp'a göndermez; Patron modu ve kill switch korunur (K07, K09). Gerçek mesajla deneme ücretli denemedir, önceden bildirilir.
- Eşleşme anahtarı `hash_equals` ile kontrol edilir; yanlışsa 401 + 1 sn bekleme (K13). Komut kanalı (`vps_komut`) kapalı başlar ve açılmaz (K14).
- Kalıcı akış: asıl kayıt Postgres, tek etkin işleyici `settings.worker` (D-04); yarım iş en çok 3 kez alınır, yalnız geçici teknik hatada (D-03). Veritabanı eski yedekle ezilmez.
- Numaralar günlüğe ve kanıta yalnız maskeli ya da özetiyle yazılır (`maske()`; K09). WhatsApp kimliği numarayı içerir: ham haliyle yazılmaz.
- PHP tarafı testleri (`php kanal/tests/offline_test.php <lib.php>`) hosting'in gerçek `lib.php`'sini ister; o dosya depoda yoktur, temiz kopyası Lokman'ın Mac'indedir.
- Bilinen açık riskler: imzasız paket (K25), root parolayla SSH (kapatılması canlı değişikliktir), anahtar son kullanma tarihi (DURUM.md). Bunlara dokunan iş önce DURUM'daki riski günceller.
