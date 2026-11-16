# Havuz denetimi · 16 Kasım 2026

**Neden.** Lokman, 16 Kasım 2026: "cumbalı çatıları doğru çizgidiğine emin misin" (07:03:40), "hepsinin kontrolleri yapılsın öyle girsin havuza hata olmasın" (07:05:58), "sadece çatı değil ne varsa yani kontrolcü her yaptığımı yeni ta 3 eylülden bugüne kontrolleri yapsın öyle alsın havuza havuz hatalı olmasın" (07:07:03), "ben burda tek tek her yapı ile uğraşıyorum" (07:07:14).

**Ne yapıldı.** 3 Eylül'den bugüne kural ve kararlar (K01–K25, Z-01–Z-10, D-01…D-110'un 100 dosyası, PC-01…PC-43, M-01…M-18) konu konu gruplandı; her grubun havuz evinde bugün neyle denetlendiği yazıldı (bölüm 1). Havuz hakeminin bakmadığı kalemler için yalnız okuyan bir denetim yazıldı (`araclar/havuz_denetimi.py`, bölüm 2) ve havuzdaki 57 ev (40 prefabrik, 17 çelik) bununla tarandı (bölüm 3). Hiçbir ev, kayıt ya da kural değişmedi; havuzdan ev çıkmadı.

**Kapsam dışı.** Köşe verandasının çatısı (52, 55 ve 67 m²; kendi sohbetinde), disk arşivinin beş yeni evi (kendi sohbetinde; komut onlara verildi), kayıt kapısına yeni kalem eklemek (Lokman'ın onayıyla, bölüm 4).

## 1. Kurallar havuz evinde bugün neyle denetleniyor

Sınıflar: **H** havuz hakemi (`araclar/havuz_hakemi.py`; kayıt `aday_kaydet.py --havuz --kart` geçmezse yazılmaz) · **D** Motor doğrulaması (kayıt aracı geçmesini ister) · **A** Motor her çizimde anahtarsız uygular, testi yalnız hedef örnekte · **K** yalnız İş Emri'nde anahtar varsa · **Y** havuza girişte bugün hiç denetlenmiyor (bu denetimin kalemi parantezde).

| Konu | Kurallar | Bugün | Boşluk |
|---|---|---|---|
| Plan kimliği: dış ölçü, brüt, oda programı, pencere, kapı, açık mahal, kat | D-87, D-95, M-18, İE-38 | H | – |
| Standart pano, kısa parça silme, ölçüye kesim | D-30 (PC-07), D-69 (PC-37), D-91, D-92 (PC-39), BK-31, D-103 | H (standart, silme ve kesim kipleri) + K | Kısa pano uyarısı (10,5 ve 18 cm) kayda girerken görülmüyor (Y: HD-02) |
| Çizim doğrulaması: duvar, açıklık, kanat çakışması, K23 | K02, K16, K23, D-13 | D | – |
| Köşe, T ve H birleşimleri | D-29 (PC-03), D-49, D-96 (PC-40), D-104 (PC-41), D-105 (PC-42), D-108 (PC-44) | A + K | "Dört kollu birleşim profili kural kitabında yok" uyarısı (Y: HD-02) |
| Pencere ve kapı yeri | D-13, BK-13, PC-02, PC-31, D-46 (PC-33), PC-34 | A + K | "Geniş pencere oda ortasına alınmadı" uyarısı (Y: HD-02) |
| Ön onay çiziminin düzeni | M-02, D-29, D-30, D-31, D-34, PC-01…PC-29 | A (hedef örnek TK-02, TK-01 r07) | Havuz evinin çizimi hedefle kıyaslanmaz; kural her çizimde aynı koddan |
| Çatı biçimi: beşik, cumba, kırma, girinti, kubbe, mahal çatısı | M-07, D-44, D-47, D-54 (PC-35), PC-36, PC-38, İE-17, İE-24 | A + K; makas planı yalnız M-07'nin dört evinde ve İE-29'un üç paftasında | Makas sayısı paftayla (Y: HD-07), 3D çatı biçimi (Y: HD-10) |
| Taşan veranda çatısı | D-29 m.1, PC-01, PC-09, PC-38, D-52, D-56 (PC-34), D-109 (PC-45) | A + K | "Çatısı İş Emri'nde yok", "dere çizimde yok" uyarısı (Y: HD-02) |
| Omega | M-01, M-03, M-04, D-32, D-39, D-41 | A (listede; hedef PK-01, TK-01, TK-03) | Liste yazılmazsa uygulanmaz (Y: HD-03) |
| Çatı kaplaması | M-06, M-11, M-16, D-40, D-50, D-74 | A (listede) | Liste yazılmazsa uygulanmaz (Y: HD-03) |
| Yükleme listesi tamlığı | BK-12, D-45, D-47, K21 | Y | Liste yazılıyor mu (HD-03), adetsiz ya da "Kural yok" satırı (HD-04) |
| Tavan kirişi | D-107 (PC-43) | A | Kiriş konamazsa liste "Kural yok" yazar (Y: HD-04) |
| 3D model (IFC) ve 3D sayfası | Z-07, BK-12 PR-R, İE-21 | Y | 3D kuruluyor mu (HD-05), makas yeri uyarısı (HD-06), makas sayısı listeyle (HD-08, HD-09), kırma çatı (HD-10) |
| Montaj rehberi | M-13, M-17, D-53, D-73 | Rehber istenince kendi denetimiyle | Havuza girişte bakılmıyor (bu denetimin dışında) |
| Teklif ve fiyat | M-14, M-15, D-64, D-72 | Teklif istenince | Havuza girişle ilgisi yok |
| Çelik: duvar paneli, çizim seti, 15 cm notu, çatı kaplaması | M-09, M-10, D-10, D-16, D-97, D-98, D-100 | A (genel motor altın testleri); bankada çelik hakemi (İE-16) | Karkas kuralı uyarıları (Y: HD-02); havuz evi standart çatı kaplamasıyla (Y: HD-11, uyarı) |
| Mühendis paftası hata kaynağı | Lokman, 15 Kasım 2026 09:45 | – | Fark eskizle gösterilir; denetim yalnız farkı bulur (HD-07, bilgi) |

## 2. Denetim komutu

```
python -m araclar.havuz_denetimi --is 4 --kart-klasoru <Proje_Karti> --json sonuc.json --md sonuc.md
python -m araclar.havuz_denetimi --is-emri <İş Emri.json> --kart AP-NN --kart-klasoru <Proje_Karti>   # havuza girmemiş ev
python -m araclar.havuz_denetimi --yalniz PA23 PA44                                                  # havuzdan yalnız bu kodlar
```

Yalnız okur; çıkış 1 en az bir evde hata demektir. Kalemler:

| Kalem | Ne | Sınıf |
|---|---|---|
| HD-01 | Motor kurar, çizim doğrulaması geçer | hata |
| HD-02 | Motor uyarısı yok (çatı, veranda, köşe, pano, pencere; çelikte karkas kuralı) | uyarı |
| HD-03 | Yükleme listesi yazılır | hata |
| HD-04 | Listede adetsiz ya da "Kural yok" satırı yok | hata |
| HD-05 | 3D model (IFC) kurulur | hata |
| HD-06 | 3D modelde makas yeri uyarısı yok | uyarı |
| HD-08 | 3D'deki makas sayısı her çatı parçasında listedekiyle aynı | hata |
| HD-09 | Listede makaslı her çatı parçası 3D'de de makaslı | uyarı |
| HD-10 | 3D'deki ana çatı İş Emri'nin çatı biçiminde | hata |
| HD-07 | Makas sayısı gerçek projenin kartıyla (`--kart-klasoru` verilirse) | bilgi |
| HD-11 | Çelik: havuz evi standart çatı kaplamasıyla (`cati.kaplama`, yoksa baz paket = tek kat panel; Lokman 16 Kasım 08:27:26 kartı) | uyarı |

Çelik evde (genel motor) HD-01…HD-05 ve HD-11 denetlenir; tabloda öteki kalemler "–".

## 3. Sonuç (16 Kasım 2026, `main` 4a654e9f, `--is 4`, 2 dk 18 sn)

57 ev: hepsi HD-01'den geçti. Hata 20 ev, yalnız uyarı 14 ev, temiz 23 ev (HD-11 eklenince yalnız uyarı 19, temiz 18: beş çelik ev yalnız standart dışı kaplamadan). Ev ev tablo: `docs/raporlar/2026-11-16_havuz_denetimi_tablo.md`.

| Sorun | Evler | Kalem | Bayiye etkisi | Nerede düzelir |
|---|---|---|---|---|
| 3D'de kırma çatı beşik çiziliyor (`ifc_uret.cati` kırmayı tanımıyor; makaslar y'yi geçince `_cati_y` her ön duvar ekine makas koyuyor) | PA-08 (140 m² 3+1), PA-33 (142 m² 3+1), PA-24 (77 m² 2+1), PA-34 (78 m² 2+1), PA-06-K (87 m² 2+1) | HD-10, HD-08 | 3D sayfasında yanlış çatı | Motor bakımı |
| 3D kurulmuyor: kubbe (`ifc_uret.hazirla` → `dxf_out.Cizici.pano_blok` KeyError 'kubbe') | PA-09 (64 m²), PA-20 (64 m²), PA-16 (80 m²) | HD-05 | 3D sayfası yok | Motor bakımı (kod hatası) |
| 3D kurulmuyor: girintili gövde + çapraz cumba (İE-24 A4, bilinen) | PA-05 (82 m²), PA-17 (91 m²), PA-27, 28, 29 (45, 46, 40 m²) | HD-05 | 3D sayfası yok | Motor bakımı |
| Liste yazılmıyor: iki cumba; mahyası y boyunca iki uçlu kırma | PA-27, 28, 29; PA-06-K | HD-03 | Liste ve teklif yok | Motor bakımı (liste) |
| Listede adetsiz satır: "Çatı paneli (hafif çelik) · VERANDA çatısı", Kural yok | PA-03 (70 m²), PA-26 (71 m²), PA-35 (69 m²) | HD-04 | Teklifte veranda çatı paneli eksik | Lokman'ın kuralı (K21) |
| 3D makas sayısı listeden farklı (`_cati_y`'de düzenlilik denetimi yok; disk arşivi sohbetinin bulgusu, 37 ve 59 m²'de de) | PA-12 (85 m²: 3D 13, liste 11), PA-30 (83 m²: 12, 10), PA-25 (61 m²: 8, 7), PA-22 (102 m²: 5, 7) | HD-08 | 3D ve kart modelinde makas fazla ya da eksik | Motor bakımı |

Bilgi (HD-07, hata değil):

- Cumba iç ucu kuralıyla açıklanan farklar (D-44, Lokman 2 Kasım 16:50): PA-02 (64 m²: liste 12, proje 13), PA-03 (70 m²: 10, 11), PA-09 (64 m²: 15, 16), PA-13 (143 m² çift cumba: 17, 19), PA-21 (80 m² 3+1: 10, 11).
- Kısa parçası silinen evler (D-92, BK-31): PA-30 (83 m²: 10, kaynak ev 11), PA-35 (69 m²: 8, kaynak ev 10); makas aralığı 125,5 cm'yi geçmiyor.
- Kuralla açıklanmayan, eskizle sorulacak: PA-16 (80 m² kubbeli: liste 11, proje 9; İE-29'da açık), PA-20 (64 m² kubbeli: 16, 14; İE-29'da açık), PA-22 (102 m² teraslı: liste 7 makas hattı, gerçek liste 14 yarım makas).

Çelik çatı kaplaması (HD-11; koordinatörün 16 Kasım 08:18 notu). İlk sürüm tanımın kaplamasını gerçek projeyle kıyasladı: dört ev farklıydı (KT-07 sandviç panel ↔ "OSB + nem bariyeri + metal kiremit"; KT-11 tek kat panel ↔ "OSB + membran + shingle"; KT-12, KT-13 tek kat panel ↔ "OSB + membran + metal kiremit"). İki okuma vardı: gerçek proje ya da havuz standardı (D-87 › Standart; M-16: çelikte standart tek kat panel). Lokman 16 Kasım 2026 08:27:26 UTC karar kartı: soru "Havuzdaki çelik evler hangi çatı kaplamasıyla çizilsin?", seçim "Standart: tek kat panel" (seçeneğin sonucu: "Havuzdaki her çelik ev tek kat panelle çizilir, bayi kaplamayı formda seçer. Bugün sandviç panelli 10 çelik ev değişir."). HD-11 artık standardı denetler (uyarı, kaydı durdurmaz): sandviç panelli 10 ev standart dışında: KT-01 (99 m²), KT-02 (92), KT-03 (94), KT-04 (124), KT-05…KT-08 (90), KT-09 (81), KT-10 (82). Değişiklik ayrı Motor bakım sohbetinde; tanım dosyaları bu denetimde değişmedi.

Uyarılar (HD-02, HD-06, HD-09; HD-11 yukarıda; HD-11 öncesi 14 evde yalnız uyarı): dört kollu birleşim profili kural kitabında yok (PA-07, PA-13, PA-16); kısa pano 10,5 cm (PA-25), 18 cm × 2 (PA-27); 160×180 ve 150×190 pencere oda ortasına alınmadı (PA-06, 06-C, 06-K, 27, 28, 29); `kisa_kenar: y` doğrulanmalı (PA-06-C, PA-24, PA-34); köşe paftadan (PA-01, PA-16; M-07); 3D makas yeri düzensiz, eşit aralık alındı (PA-04, 06, 06-C, 06-K, 07, 23); listedeki veranda ve köşe kırması makası 3D'de yok (PA-02, PA-07); çelikte karkas kuralının "makas yok" uyarısı (KT-07, KT-08, KT-09) ve modeldeki kapı ölçüsü kuraldan farklı (KT-01, KT-03, KT-13). Taşan verandası varsayılan çatı alan ("çatısı İş Emri'nde yok") ya da "dere çizimde yok" uyarısı veren ev yok.

**Açık soru (disk arşivi sohbeti, 16 Kasım 07:35).** 2019–2020 paftalarında saçak 25 cm (59 m²: 823 = 773 + 2 × 25); havuzdaki prefabrik İş Emri'lerinin hiçbiri `sacak_cm` yazmıyor, Motor 30 alıyor. Havuz geneli bir kural sorusu; bu denetimin kalemi değil, Lokman'a ayrıca sorulur.

## 4. Kayıt kapısı (D-112, BK-47; Lokman 16 Kasım 2026 08:07:06 kartı "Evet, hatalı yeni ev girmesin")

Kayıt aracı (`aday_kaydet.py`) yeni evi havuza yazmadan önce bu denetimi koşar: hata sınıfındaki bir kalem (HD-01, 03, 04, 05, 08, 10) geçmezse kayıt yazılmaz; uyarı ve bilgi kayda yazılır, Lokman'a özetle gider. Var olan 20 ev havuzda kalır, sorunları Motor bakımıyla düzelir (her sorun ayrı bakım sohbeti, çalışma kuralı 10). Bilgi (HD-07) ve uyarı kalemleri (HD-02, 06, 09, 11) kaydı durdurmaz.
