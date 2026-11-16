# 16 Kasım 2026 · Havuz denetimi: havuzdaki her ev 3 Eylül'den bugüne kurallarla

- **Aktif iş:** havuz denetimi, dal `claude/project-thread-ly824o` (Lokman 07:05:58, 07:07:03: "hepsinin kontrolleri yapılsın öyle girsin havuza").
- **Yapılan:** `araclar/havuz_denetimi.py` (yalnız okur): her evi bugünkü kodla kurar; Motor uyarısı, liste yazılır mı, adetsiz satır,
  3D kurulur mu, 3D makas yeri ve sayısı, 3D kırma çatı, gerçek projenin makas sayısı (HD-01…HD-10). Kural envanteri ve sonuç
  `docs/raporlar/2026-11-16_havuz_denetimi.md`, ev ev tablo `…_tablo.md`. Test `testler/test_havuz_denetimi.py`.
- **Sonuç:** 57 ev (40 prefabrik, 17 çelik): hata 20 (6 sorun: kırma çatı 3D'de beşik 5, 3D kurulmuyor 8, liste yazılmıyor 4,
  adetsiz veranda çatı paneli 3, 3D makas sayısı listeden farklı 4), yalnız uyarı 14, temiz 23. Hiçbir ev ve kayıt değişmedi.
- **Kayıt kapısı (D-112, BK-47; Lokman 08:07:06 kartı "Evet, hatalı yeni ev girmesin"):** `aday_kaydet.py` (prefabrik, çelik) ve
  `cati_varyanti_kaydet.py` havuza yeni ev yazmadan denetimi koşar; hata sınıfı (HD-01, 03, 04, 05, 08, 10) kaydı durdurur, uyarı
  kayda yazılır. Var olan 20 ev havuzda kalır. Test 11 (`testler/test_havuz_denetimi.py`).
- **HD-11 (16 Kasım ~08:40, koordinatörün 08:18 notu):** çelik tanımın çatı kaplaması ↔ gerçek projenin teknik özellikleri (bilgi,
  kapıya girmez). Dört ev farklı: KT-07 (sandviç ↔ OSB + metal kiremit), KT-11 (tek kat ↔ OSB + shingle), KT-12 ve KT-13 (tek kat ↔
  OSB + metal kiremit). Hangisi esas (gerçek proje mi, D-87 standardı tek kat panel mi) Lokman'ın kararı; tanım ondan önce değişmez.
- **Durum:** Yerelde çalışıyor; PR #249 Ready, doğrulama bekleniyor. Birleştirmeyi Lokman yapar.
- **Sıradaki:** PR yeşilde bağlantı Lokman'a; kaplama kararı; sorunlar Motor bakım sohbetlerinde (BK-45 liste, BK-46 3D). Açık soru:
  2019–2020 paftalarında saçak 25 cm.
