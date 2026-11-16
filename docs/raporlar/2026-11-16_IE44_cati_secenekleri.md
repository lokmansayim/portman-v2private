# İE-44 · Havuz evlerinin çatı seçenekleri: toplu koşu (16 Kasım 2026, 09:05 UTC)

Komut: `python -m araclar.cati_secenekleri_toplu --cikti <klasör> --is 4` (main `6477280` + PR #249'un havuz denetimi, yerel çalışma
kopyası). Araç yalnız okur; kayda yazmaz. Zaten çatı seçeneği olan ev: PA-06.

Sonuç: 38 ev, 76 seçenek. Hazır 9, denetimi bekliyor 16,
Motor'da çizilemedi 51. "Evin çatısı": o tür evin kendi çatısıdır, seçenek kurulmaz.

| Ev | m² | Oda | Evin çatısı | Kırma (K) | Beşik + salonda cumba (C) | Beşik (B) |
|---|---|---|---|---|---|---|
| PA-29 | 40 | 1+1 | Beşik + iki cumba | çizilemedi | evin çatısı | çizilemedi |
| PA-27 | 45 | 1+1 | Beşik + iki cumba | çizilemedi | evin çatısı | çizilemedi |
| PA-28 | 46 | 1+1 | Beşik + iki cumba | çizilemedi | evin çatısı | çizilemedi |
| PA-23 | 49 | 2+1 | Beşik, kalkan önde | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-44 | 49 | 2+1 | Beşik, kalkan önde | çizilemedi | çizilemedi | evin çatısı |
| PA-31 | 59 | 2+1 | Beşik + cumba | çizilemedi | evin çatısı | hazır |
| PA-01 (mühürlü, M-07) | 60 | 2+1 | Beşik, kalkan önde | çizilemedi | çizilemedi | evin çatısı |
| PA-14 | 60 | 2+1 | Beşik + cumba | çizilemedi | evin çatısı | hazır |
| PA-18 | 60 | 2+1 | Beşik, kalkan önde | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-25 | 61 | 2+1 | Beşik, kalkan yanda | çizilemedi | hazır | evin çatısı |
| PA-36 | 62 | 2+1 | Beşik, kalkan önde | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-02 (mühürlü, M-07) | 64 | 2+1 | Beşik, kalkan yanda (verandada kırma) | çizilemedi | çizilemedi | evin çatısı |
| PA-09 | 64 | 2+1 | Beşik, kalkan yanda (verandada kırma) | çizilemedi | çizilemedi | evin çatısı |
| PA-20 | 64 | 2+1 | Beşik, kalkan yanda (verandada kırma) | çizilemedi | çizilemedi | evin çatısı |
| PA-32 | 69 | 2+1 | Beşik + cumba | çizilemedi | evin çatısı | denetimi bekliyor |
| PA-35 | 69 | 2+1 | Beşik, kalkan önde (verandada tek eğim) | çizilemedi | çizilemedi | evin çatısı |
| PA-03 (mühürlü, M-07) | 70 | 2+1 | Beşik, kalkan önde (verandada tek eğim) | çizilemedi | çizilemedi | evin çatısı |
| PA-15 | 70 | 2+1 | Beşik + cumba | çizilemedi | evin çatısı | denetimi bekliyor |
| PA-26 | 71 | 2+1 | Beşik, kalkan önde (verandada tek eğim) | çizilemedi | çizilemedi | evin çatısı |
| PA-24 | 77 | 2+1 | Kırma, bir ucu kalkan | evin çatısı | hazır | denetimi bekliyor |
| PA-04 | 78 | 2+1 | Beşik + cumba | çizilemedi | evin çatısı | çizilemedi |
| PA-34 | 78 | 2+1 | Kırma, bir ucu kalkan | evin çatısı | hazır | denetimi bekliyor |
| PA-16 | 80 | 2+1 | Beşik, kalkan önde | çizilemedi | denetimi bekliyor | evin çatısı |
| PA-21 | 80 | 3+1 | Beşik, kalkan önde | çizilemedi | çizilemedi | evin çatısı |
| PA-05 (mühürlü, M-07) | 82 | 2+1 | Beşik + cumba | çizilemedi | evin çatısı | çizilemedi |
| PA-30 | 83 | 3+1 | Beşik, kalkan yanda | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-19 | 84 | 2+1 | Beşik, kalkan önde | denetimi bekliyor | hazır | evin çatısı |
| PA-12 | 85 | 3+1 | Beşik, kalkan yanda | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-07 (mühürlü, M-16) | 90 | 3+1 | Beşik, kalkan önde | çizilemedi | çizilemedi | evin çatısı |
| PA-11 | 91 | 3+1 | Beşik + cumba | çizilemedi | evin çatısı | hazır |
| PA-17 | 91 | 3+1 | Beşik + cumba | çizilemedi | evin çatısı | çizilemedi |
| PA-37 | 91 | 3+1 | Beşik + cumba | çizilemedi | evin çatısı | denetimi bekliyor |
| PA-10 | 95 | 3+1 | Beşik, kalkan yanda | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-38 | 95 | 3+1 | Beşik, kalkan yanda | denetimi bekliyor | çizilemedi | evin çatısı |
| PA-22 (mühürlü, M-12) | 102 | 2+1 | Beşik, kalkan yanda | çizilemedi | çizilemedi | evin çatısı |
| PA-08 | 140 | 3+1 | Kırma | evin çatısı | hazır | denetimi bekliyor |
| PA-33 | 142 | 3+1 | Kırma | evin çatısı | hazır | denetimi bekliyor |
| PA-13 | 143 | 4+1 | Beşik, kalkan önde | çizilemedi | çizilemedi | evin çatısı |

## Seçenek seçenek

- **PA-29-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-29-B** Beşik: çizilemedi. Gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)
- **PA-27-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-27-B** Beşik: çizilemedi. Gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)
- **PA-28-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-28-B** Beşik: çizilemedi. Gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)
- **PA-23-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. Yükleme listesi bu çatıda yazılamıyor; liste bakım işi bitince yeniden denetlenir.
- **PA-23-C** Beşik + salonda cumba: çizilemedi. Salon ön cephenin %100'ini kaplıyor; cumba bütün cephe olur
- **PA-44-K** Kırma: çizilemedi. Ev kareye çok yakın: kırmanın mahyası 15 cm'den kısa kalıyor (Motor kurmadı).
- **PA-44-C** Beşik + salonda cumba: çizilemedi. Salon ön cephenin %100'ini kaplıyor; cumba bütün cephe olur
- **PA-31-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-31-B** Beşik: hazır. not yok
- **PA-01-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-01-C** Beşik + salonda cumba: çizilemedi. Gövde girintili: çıkıntısız cumba girintisiz gövdede kurulur
- **PA-14-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-14-B** Beşik: hazır. not yok
- **PA-18-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. Yükleme listesi bu çatıda yazılamıyor; liste bakım işi bitince yeniden denetlenir.
- **PA-18-C** Beşik + salonda cumba: çizilemedi. Salon ön cepheye değmiyor (önünde veranda ya da başka oda var)
- **PA-25-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-25-C** Beşik + salonda cumba: hazır. 3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).
- **PA-36-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. Yükleme listesi bu çatıda yazılamıyor; liste bakım işi bitince yeniden denetlenir.
- **PA-36-C** Beşik + salonda cumba: çizilemedi. Salon ön cepheye değmiyor (önünde veranda ya da başka oda var)
- **PA-02-K** Kırma: çizilemedi. Verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz
- **PA-02-C** Beşik + salonda cumba: çizilemedi. Verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz
- **PA-09-K** Kırma: çizilemedi. Verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz
- **PA-09-C** Beşik + salonda cumba: çizilemedi. Verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz
- **PA-20-K** Kırma: çizilemedi. Verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz
- **PA-20-C** Beşik + salonda cumba: çizilemedi. Verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz
- **PA-32-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-32-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-35-K** Kırma: çizilemedi. Verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz
- **PA-35-C** Beşik + salonda cumba: çizilemedi. Verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz
- **PA-03-K** Kırma: çizilemedi. Verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz
- **PA-03-C** Beşik + salonda cumba: çizilemedi. Verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz
- **PA-15-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-15-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-26-K** Kırma: çizilemedi. Verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz
- **PA-26-C** Beşik + salonda cumba: çizilemedi. Verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz
- **PA-24-C** Beşik + salonda cumba: hazır. Makas evin uzun kenarını geçiyor; mühendis bakar (87 m²'nin cumbalı çatısındaki gibi).; 3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).
- **PA-24-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-04-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-04-B** Beşik: çizilemedi. Gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)
- **PA-34-C** Beşik + salonda cumba: hazır. Makas evin uzun kenarını geçiyor; mühendis bakar (87 m²'nin cumbalı çatısındaki gibi).; 3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).
- **PA-34-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-16-K** Kırma: çizilemedi. Ev kareye çok yakın: kırmanın mahyası 15 cm'den kısa kalıyor (Motor kurmadı).
- **PA-16-C** Beşik + salonda cumba: denetimi bekliyor. 3D model kurulamıyor.
- **PA-21-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-21-C** Beşik + salonda cumba: çizilemedi. Gövde girintili: çıkıntısız cumba girintisiz gövdede kurulur
- **PA-05-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-05-B** Beşik: çizilemedi. Gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)
- **PA-30-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-30-C** Beşik + salonda cumba: çizilemedi. Salon ön cepheye değmiyor (önünde veranda ya da başka oda var)
- **PA-19-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. Yükleme listesi bu çatıda yazılamıyor; liste bakım işi bitince yeniden denetlenir.
- **PA-19-C** Beşik + salonda cumba: hazır. Makas evin uzun kenarını geçiyor; mühendis bakar (87 m²'nin cumbalı çatısındaki gibi).; 3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).
- **PA-12-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-12-C** Beşik + salonda cumba: çizilemedi. Salon ön cepheye değmiyor (önünde veranda ya da başka oda var)
- **PA-07-K** Kırma: çizilemedi. Taşan verandası var: Motor beşik dışı çatıyı taşan verandayla birlikte çizmiyor.
- **PA-07-C** Beşik + salonda cumba: çizilemedi. Taşan verandası var: Motor beşik dışı çatıyı taşan verandayla birlikte çizmiyor.
- **PA-11-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-11-B** Beşik: hazır. not yok
- **PA-17-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-17-B** Beşik: çizilemedi. Gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)
- **PA-37-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-37-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-10-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-10-C** Beşik + salonda cumba: çizilemedi. Salon ön cepheye değmiyor (önünde veranda ya da başka oda var)
- **PA-38-K** Kırma: denetimi bekliyor. 3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-38-C** Beşik + salonda cumba: çizilemedi. Salon ön cepheye değmiyor (önünde veranda ya da başka oda var)
- **PA-22-K** Kırma: çizilemedi. Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı).
- **PA-22-C** Beşik + salonda cumba: çizilemedi. Salon ön cephenin %81'ini kaplıyor; cumba bütün cephe olur
- **PA-08-C** Beşik + salonda cumba: hazır. 3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).
- **PA-08-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-33-C** Beşik + salonda cumba: hazır. 3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).
- **PA-33-B** Beşik: denetimi bekliyor. 3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir.
- **PA-13-K** Kırma: çizilemedi. Gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar
- **PA-13-C** Beşik + salonda cumba: çizilemedi. Gövde girintili: çıkıntısız cumba girintisiz gövdede kurulur

Ayrıntılı bulgular (havuz denetiminin HD kalemleri, Motor uyarıları) aracın `sonuc.json` dosyasındadır.

## Ek (16 Kasım 09:45 UTC): kayıt ve düz iskelet denemesi

- **Kayıt (D-115):** Lokman'ın kartı 08:46:30 "9'u girsin, bekleyenler size gelsin". Dokuz seçenek main'deki
  `cati_varyanti_kaydet.py` ile kaydedildi; dokuzu da kayıt anındaki havuz denetiminden geçti (D-112).
- **Düz iskelet (straight skeleton), Lokman 09:29:31 isteği:** "sen bu çatı olayını repoları incele Straight skeleton vardı bunları bir
  incele yani modelden çatı çıkartabiliriz". Depoda iskelet elle üç yerde kullanılmış: Ç8801-K (doğu ucu kırma) ve Ç8801-D (tam kırma)
  düzlemleri, KT-03 (`deneme/2026-10-09_kor_test_3/tanim/kt03_tanim_uret.py`) ve ÇP-03 (`testler/celik/projeler/CP03`). Genel araç yok;
  plan üretimi işinde (İE-14) genel iskelet ve L kırma kapsam dışı kalmıştı.
- **Deneme (yalnız görsel, Motor'a dokunmadan, yeni paket kurmadan):** gövde çizgisi saçak payıyla büyütülür, içe doğru eşit adımla
  daraltılır; her noktanın ilk ulaştığı kenar çatı yüzünü verir (kırma). 91 m² (PA-17), 143 m² (PA-13), 46 m² (PA-28) evde kırma çıktı.
  Görseller PF `Cati_Secimi/Havuz_Toplu/2026-11-16_iskelet_denemesi/`.
- **Açılabilecek seçenek:** çizilemeyen 26 kırma seçeneğinin 15'inde tek engel gövde biçimi (köşe yönü 6, girinti 4, kareye yakın 2,
  birlikte 3). İkisi mühürlü evde (PA-01-K, PA-05-K; M-07), 13'ü açılabilir.
- **Sınırlar:** iskelet yalnız kırma verir (beşik ve cumba için kalkan kuralı ya da ağırlıklı iskelet gerekir); küçük girintide ince şerit
  kalır (143 m²); verandanın kendi çatısı ayrı iş (46 m²); makas, aşık ve yükleme listesi bu yüzlerden Motor'da kurulmalı (Motor bakımı).
- **Hazır kütüphaneler (lisans):** CGAL Straight_skeleton_2, 5.6'dan beri ağırlıklı iskelet (kalkan kurar; GPL ya da ücretli);
  bpypolyskel (GPL-3.0, yalnız kırma); polyskel (LGPL-3.0; yazarı bazı girdilerde hatalı olduğunu yazıyor); ladybug-geometry-polyskel (PyPI).
  Kurulmadı. Karar Lokman'da (kart: ayrı Motor bakım işi açılsın mı).
