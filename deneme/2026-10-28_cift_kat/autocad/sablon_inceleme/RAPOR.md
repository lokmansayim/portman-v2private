# Güncel Şablon 2024 · tam inceleme raporu (28 Ekim 2026, 11:20–11:45)

Lokman'ın isteği: "Güncel Şablon 2024'ü tamamen incele, her yerini gez, ne yakalayabilirsen." Yöntem: AutoCAD'de `DXFOUT`
(157 MB, AC1032/R2018, cm) → `envanter.py` akış taraması (5 sn) → ezdxf ile blok kütüphanesi ve kümeleme. Kaynak DWG
(`~/Desktop/Portatifev Toptan/Güncel Şablon 2024.dwg`) **değiştirilmedi, kaydedilmedi.**

Dosyalar (bu klasör): `envanter.py` (araç) · `envanter.md` / `envanter.json` (ham sayım; git dışı) · `bloklar_adli.md` (278 adlı blok) ·
`notlar_tam.md` (76 uzun not) · `kumeler.json` (92 blok kümesi) · `sablon_bloklari.dxf` (17 MB blok kütüphanesi; git dışı).

## 1. Sayılar

| Ölçü | Değer |
|---|---|
| Model varlığı | 453.940 (LINE 346.954 · LWPOLYLINE 31.170 · SOLID 29.362 · ARC 9.040 · MTEXT 7.432 · DIMENSION 6.970 · HATCH 6.904 · TEXT 5.058 · INSERT 3.141) |
| Pafta alanı | 0 varlık; layoutlar A3-D, A3-Y, A4-D, A4-Y (boş çerçeveler) — her şey model alanında |
| Katman | 277 (en yoğun: DUVAR 112.610 · 0 95.315 · TARAMA 54.509 · LCAD_TRUSS 51.388 · LCAD_WALL 38.916 · BCAD_TRUSS 16.461 · 25.kapı-penc 12.953 · PENCERE 5.740 · YAZI 4.935 · ANTET 3.710 · Press Panel 3.207 · DETAYLAR 2.973 · Çelik Profil 1.386 · betopan 1.159 · ÖLÇÜLENDİRME 1.146 · KAPI 748 · ÇATI 694) |
| Blok tanımı | 7.995; **7.607'si `*D` isimsiz ölçü bloğu, 104 `*U`; adlı 278** |
| Sınırlar | x 1.355.779–1.648.734 · y 286.220–674.069 (yaklaşık 2,9 × 3,9 km'lik dağınık alan); INSUNITS 5 (cm), LTSCALE 0,5 |
| Kaynak izleri | ArchiCAD katmanları, "www.PislikMimar.com", LCAD/BCAD (çatı makası programı), PDF4_* (PDF'ten alınmış çizimler): şablon onlarca ayrı çizimin birleşimi |

## 2. Blok mantığı (malzeme kartı adlarıyla)

Panolar ve profiller **malzeme adıyla** bloktur; blok sayısı = malzeme sayısı. Geometri Lokman'ın ızgarasıyla birebir (125,5 pano, 10 cm duvar).

| Blok adı (şablondaki yazımıyla) | INSERT | Geometri |
|---|---|---|
| 100 LIK DOLU PANO 125 LİK | 202 | 125,5 × 10 dikdörtgen |
| 100'LÜK 125'LİK PANO | 86 | 125,5 × 10 dikdörtgen |
| 100'LÜK 125'LİK (120x100) PENCERELİ PANO | 61 | 125,5 × 15,6 (pencere sembolü dışa taşar) |
| 100 LIK PENCERELİ PANO 122.5 LUK | 37 | 100 × 13,5 (eski seri; 609 varlık) |
| 100'LÜK 125'LİK KAPILI PANO(80'LİK) | 24 | 125,5 × 85,6 (kapı yayı dahil) |
| 100'LÜK 120'LİK KAPILI PANO (80'LİK) | 16 | — |
| 100'LÜK 115'LİK KAPILI PANO(80'LİK) · 100'LÜK 117'LİK PANO (117,5 × 10) · 60'LIK 122'LİK / 125'LİK KAPILI PANO(80'LİK) · 100'LÜK 125'LİK (60x40) VASİSTASLI PANO · 100'LÜK 250'LİK_CIFT_KANATLI_KAPI | 1–15 | kesik ve özel panolar da ayrı blok |
| 100 LÜK ÇELİK KAPI 90X120 | 17 | 100 × 95 |
| 100X100 2 Lİ H DİREĞİ · 3 LÜ H BAĞLANTI DİREĞİ · 4 LÜ H BAĞLANTI DİREĞİ (+ KULAKLI türleri) | — | 10×5 · 12,5×10 · 15×10 |
| 100X100 DIŞ KÖŞE DİREĞİ · 2X100X100 İÇ KÖŞE DİREĞİ (60, 80 türleri de var) | — | 12,5×12,5 · 10×10 |
| 100 LIK / 80 LIK / 60 LIK TAVAN OMEGASI · 100 LÜK / 80 LİK / 60 LIK SAÇAK OMEGASI | — | 15 × 2,5 |
| PENCERE_VASİSTAS_60x40 (60×40) · 120x120 (18) · 160 200 P (12) · ON_PENCERE_SABLON_120180 · ON_KAPI_SABLON | — | pencere/kapı sembolleri |
| iç kapı (26) · KAPI90 (21) · Konteyner İç Oda Kapısı (25) · 90'lık Dış Konteyner kapısı · K2 ÇELİK | — | kapı sembolleri (iç kapı 1.414 varlık: ağır) |
| Tefriş: DUŞ TEKNESİ 80x80, LAVABO_, KLOZET-, FIRIN_, evy., saksı masa · Elektrik: priz (282), ANAHTAR (229), aydınlatma (98), FDPRİZ, APLİK, ANAHTAR TEKLİ · loftev logo (96) | — | |
| Çöp adlı bloklar (HJKHJKH, sfjh, erfjn, JELKDJSL …) ≈ 40 | — | kütüphaneye alındı ama kullanılmaz |

Tam liste: `bloklar_adli.md`. Şablonun kendi ad kuralı: **`<kalınlık mm>'LÜK <en cm>'LİK [(pencere ENxBOY) PENCERELİ | KAPILI (kapı en'LİK) | VASİSTASLI] PANO`**.
Portman Motor'u bugün Astra v1.4.3 şemasını kullanır (`BOM_D01_1255p0_DIS_DOLU`, `BOM_I11_1255p0_IC_K01_SAG_UST`…); K03 "Güncel Şablon 2024 blok adlarına geçiş beklemede". Eşleme taslağı:

| Motor (Astra v1.4.3) | Şablon 2024 karşılığı | Not |
|---|---|---|
| BOM_D01_1255p0_DIS_DOLU | 100'LÜK 125'LİK PANO | birebir |
| BOM_D06_627p5_DIS_DOLU | — (62,75 yarım pano şablonda yok) | kurala göre yeni ad: 100'LÜK 62,5'LİK PANO |
| BOM_D13_1255p0_DIS_P120x125 | — (şablonda 120x100 var) | 100'LÜK 125'LİK (120x125) PENCERELİ PANO |
| BOM_D11_1255p0_DIS_P60x125 | — | 100'LÜK 125'LİK (60x125) PENCERELİ PANO |
| BOM_I01_1255p0_IC_DOLU | — (60'lık dolu pano şablonda blok değil) | 60'LIK 125'LİK PANO |
| BOM_I11_1255p0_IC_K01_* | 60'LIK 125'LİK KAPILI PANO(80'LİK) | Motor kapısı 82 (K04), şablon 80 |
| BOM_B02_DIS_KOSE_50x100 | 100X100 DIŞ KÖŞE DİREĞİ | |
| BOM_B03_UCLU_H_60 | 100X100X60 3 LÜ KULAKLI H BAĞLANTI DİREĞİ / 60X60 3 LÜ H BAĞLANTI DİREĞİ | hangisi: Lokman |
| BOM_B04_VERANDA_DIKME_100x100 | 100X100 DIŞ KÖŞE DİREĞİ (?) | |

## 3. Şablondaki projeler (blok kümelerinden ve başlıklardan)

- **Çift kat, blok mantığıyla çizilmiş:** "86,5 m² GİRİŞ KATI İDA PREFABRİK" + "86,5 m² 1.KAT İDA PREFABRİK" (Alt Kat 39,62 · Üst Kat 42,88 · toplam 78,5 m², brüt 82,5): 117'lik pano ×15, 120x100 pencereli ×14, 125'lik dolu ×8, kapılı panolar ×21 (100'lük 125 · 60'lık 125 · 60'lık 122 yedişer), vasistas ×3, 120'lik kapılı ×2. Model x 1.441.910–1.459.453, y 649.483–654.919 (Küme 1).
- **Ekrandaki çift kat (PORTATİFEV 150 = 2 × 75 m²):** 1410 × 530 gövde; akslar üstte 193 | 126 | 309 | 251 | 387 | 145, altta 193 | 685 | 387 | 145; zemin: HOL+MERDİVEN 9,10 · BANYO 4,40 · YATAK 11,30 · YATAK 9,15 · SALON+MUTFAK 19,00 · HOL 8,13 · VERANDA 8,00; 1. kat aynı gövde, VERANDA → BALKON 8,00, merdiven duvarında 80/120; pencereler 60/40 (banyo), 120/120 ×2, 120/100 (mutfak), 160/180 (salon sağ); solda 150 × 178 KANOPİ; yarım pano ölçüleri 62,75 / 57,75 / 70,75 / 65,75; 2 "ÇELİK" dış kapı altta; elektrik paftası (vavien, zil, data, uydu). Duvarları **blok değil çizgi** (DUVAR/PENCERE/TARAMA katmanları). Sağda ÇATI ŞEKLİ, PANEL DETAYI, Zemin Detayı, Pencere Detayı, PENCERE GÖRÜNÜŞLERİ. Elektrik planı başlığı (1.414.849, 560.360).
- **Üç katlı ofis (184 + 200 + 200 m²):** "ZEMİN KAT PLANI 184 m² / 1. KAT PLANI 200 m² / 2. KAT PLANI 200 m²", "1 BODRUM KAT"; notları (yemekhane, muhasebe, pazarlama) §4'te. Döşeme paftaları: "1.KAT DÖŞEME YERLEŞİM PLANI", "2.KAT …", "1.KAT DÖŞEME BETOPANI YERLEŞİM PLANI", "ZEMİN KAT TAVAN OMEGA YERLEŞİM PLANI (Ters Tavan)", "1. KAT TAVAN OMEGA YERLEŞİM PLANI (Dizme Tavan)", "ARAKAT Z Sİ".
- **"ZEMİN KAT PLANI 59 m²"**, "ZEMİN KAT ALAN 107,62 / 99 m²", "Manisa Diamond 102 m² PREFABRİK KONUT" (Küme 3: 125'lik dolu ×44, kapılı ×8), "61,5 m² PREFABRİK KONUT (ps1060, 74,42 m²)", "42 m² / 59,5 m² BİRLEŞİM KONTEYNER", "Brüt Alan 30 m²", "TOPLANTI ODASI 30 m²".
- **Montaj pafta setleri:** "PREBARİK BİNA - MONTAJ PAFTALARI" ×8 kopya (ANTET, h=750), her sette BAĞLANTI APARAT ŞABLONU, Bağ Kirişi Detayı, "10 ADET / 54 ADET / 20 ADET" sayım yazıları; MONTAJ DETAYLARI ×74, ÇATI ŞEKLİ ×75, Çatı Detayı ×70, PENCERE GÖRÜNÜŞLERİ ×42, PANEL DETAYI ×27, Zemin Detayı ×23, Pencere Detayı ×21.
- **Çatı tipleri:** BEŞİK, KIRMA, CUMBALI, 74 / 82 (İKİLİ BEŞİK) / 92 KAMPANYA ÇATI, BEŞİK CUMBALI VE KUBBELİ; "çelik çatı makası (100'lük omega)" ×35; TAVAN OMEGA, AŞIK, MAKAS VE DERE, ÇATI KAPLAMASI YERLEŞİM PLANLARI; "Çatı Saçak (20 cm)", "Çatı eğimi % 30".
- **Diğer:** YERLEŞİM PLANI 1/200 (bir parsel; adres bilgisi — buraya yazılmadı), İKRANUR PREFABRİK BETOPAN KESİM PLANI, KABLO ŞAFTI VE DETAYI, ELEKTRİK GRUBU lejantı, konteyner serisi blokları.

## 4. Notlardan çıkan çok kat kuralları (şablonun kendi sözleri; `notlar_tam.md`)

1. "Tüm kirişler H profillerin üzerine bindirilecek, **kesinlikle dolu pano üzerine kiriş bindirilmeyecektir**. İstisnai olarak karkaslı paneller üzerine bindirilme projeye uygun olarak yapılabilir." → **Soru 6 (ara kat)** için kural adayı.
2. "Döşeme kirişleri **80'lik** profilden" (bir projede) / "**140'lık** profilden" (öteki projede); "döşeme arasında izolasyon **taş yünü**". → Soru 6.
3. "1. KAT MERDİVEN BOŞLUĞUNDAKİ İÇ DUVARLAR **100'LÜK** olarak tasarlanmıştır; projede '+' işaretiyle gösterilmiştir." → **Soru 2/3 (merdiven)**: merdiven boşluğu çevresi 100'lük iç duvar.
4. "1. KAT KÖŞE DİREKLERİNDE **KUTU PROFİL**"; "zemin katta tüm köşe direkleri ve kolonlar kutu profil; kutu profil kolonlar **tek parça** halinde zemine ankrajlanacak, her kutu profil için en az **4 dübel**; içi taralı olmayan kutu profiller H:250." → **Soru 8 (sürekli köşe profili)**: şablon da sürekli/tek parça köşe direğini destekliyor.
5. "Dış cephe duvarları karkaslı; tüm bağlantı **H profilleri dış cephede t:1,5, iç cephede t:1,2 et kalınlığında**." → Soru 8 (et kalınlığı).
6. "İç köşe birleşimlerinde **60'lık köşe direği**"; "2. kat planında 70x180 pencereler karkaslı pano".
7. "Zemin kat dış cephe duvarları, kapı ve muhtelif pencere panelleri **karkaslı**" (çok katlı projede).
8. Beton planı: "beton kotunda ve terazisinde dökülecek; taralı kısımlar boş; C25".
9. Doğrama notu (tekrar eden): "verilen ölçüler iç ölçülerdir; dıştan binmeli, içten pervaz matik; çift açılım; renk iç-dış aynı; pervaz 15 cm".

## 5. Lokman'ın 9 sorusuna şablonun söyledikleri (karar Lokman'ın)

| Soru | Şablonda bulunan |
|---|---|
| 1 giriş kapısı | 1410×530 örneğinde dış kapılar "ÇELİK" etiketli, ön (alt) cephede, holün önünde; kanopi girişte |
| 2 merdiven kutusu | örnekte 193 cm'lik HOL+MERDİVEN (≈1,5 pano); merdiven boşluğu iç duvarları 100'lük |
| 3 merdiven | örnekte düz kollu, 193 eninde, sahanlıksız görünüyor; ölçü notu yok |
| 4 Fransız pencere | şablonda "160/180" ve "120/200" yok; "ON_PENCERE_SABLON_120180" bloğu var |
| 5 çıkmanın çatısı | "ZEMİN KAT KANOPİ MAKAS YERLEŞİM PLANI" (kanopi ayrı makas) |
| 6 ara kat | döşeme kirişi 80'lik/140'lık profil, H profil üstüne; taş yünü; "1.KAT DÖŞEME BETOPANI YERLEŞİM PLANI"; "ARAKAT Z Sİ" |
| 7 balkon | 1. katta BALKON 8,00 m², zemindeki VERANDA ile aynı yerde; B KORKULUK katmanı (522 varlık) |
| 8 köşe profili | kutu profil köşe direği, tek parça, ankrajlı, ≥4 dübel; H profil et kalınlığı dış 1,5 / iç 1,2 |
| 9 706 / 710,25 | örnek ev 1410 × 530: 530 = 4 × 125,5 + 28 → kesimli; 1410 = 11 × 125,5 + 29,5 → şablon da ölçüye kesiyor |

## 6. Uyarılar

- DXFOUT sonrası AutoCAD'in açık belgesi `Guncel_Sablon_2024.dxf` oldu; DWG diskte aynen. İncelemeden önce sekmede "*" görülmüştü (değişiklik işareti; kaynağı bilinmiyor) — DWG kaydedilmedi.
- Şablonda kişi adları (antet, proje başlığı) var; bu rapora ve defter'e yazılmadı (KVKK kuralı).
- `sablon_bloklari.dxf` 17 MB: "iç kapı" ve "çelik kapı1" blokları 1.400'er varlıkla ağır; yeni çizimde kullanılmadan önce sadeleştirilmeli.
