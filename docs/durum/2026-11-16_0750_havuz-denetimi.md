# 16 Kasım 2026 · Havuz denetimi: havuzdaki her ev 3 Eylül'den bugüne kurallarla

- **Aktif iş:** havuz denetimi, dal `claude/project-thread-ly824o` (Lokman 07:05:58, 07:07:03: "hepsinin kontrolleri yapılsın öyle girsin havuza").
- **Yapılan:** `araclar/havuz_denetimi.py` (yalnız okur): her evi bugünkü kodla kurar; Motor uyarısı, liste yazılır mı, adetsiz satır,
  3D kurulur mu, 3D makas yeri ve sayısı, 3D kırma çatı, gerçek projenin makas sayısı (HD-01…HD-10). Kural envanteri ve sonuç
  `docs/raporlar/2026-11-16_havuz_denetimi.md`, ev ev tablo `…_tablo.md`. Test `testler/test_havuz_denetimi.py` (4 test).
- **Sonuç:** 57 ev (40 prefabrik, 17 çelik): hata 20 (6 sorun: kırma çatı 3D'de beşik 5, 3D kurulmuyor 8, liste yazılmıyor 4,
  adetsiz veranda çatı paneli 3, 3D makas sayısı listeden farklı 4), yalnız uyarı 14, temiz 23. Hiçbir ev ve kayıt değişmedi.
- **Durum:** Yerelde çalışıyor (yalnız rapor). Kayıt kapısına bağlamak Lokman'ın kartında (16 Kasım 07:3x).
- **Sıradaki:** Lokman'ın kart cevabı; sorunlar ayrı Motor bakım sohbetlerine (koordinatör). Açık soru: 2019–2020 paftalarında saçak 25 cm.
