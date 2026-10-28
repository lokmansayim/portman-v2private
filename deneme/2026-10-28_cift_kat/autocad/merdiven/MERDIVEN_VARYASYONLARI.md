# Merdiven varyasyonları · tek yerde (İE-22, 28 Ekim 2026)

Lokman (28.10 12:16): "Tüm merdiven varyasyonlarının olduğu DWG vardı; Google Drive'da CADler klasörüne bak." Drive `CADler`
(klasör kimliği `1dc8ShOCrZnIniS8tuWyHN6JLQlhieOHp`, 100+ dosya) tarandı; **merdiven** geçen 10 dosya indirildi ve okundu. Dosya adlarında
müşteri adları var; burada maskelendi.

## 1. Prefabrik merdiven planları (sade çizgi çizimleri, mm, AC1027)

| Dosya (Drive adı → buradaki ad) | Tip | Kutu | Kol eni | Basamak | Sayı | Sahanlık | Not |
|---|---|---|---|---|---|---|---|
| `merdiven (2020-06-08).dxf` → `merdiven_cift_kollu_U_252x281_kol126.dxf` | **çift kollu U** (iki paralel kol) | 252 × 281 cm | **126** (= 1 pano 125,5 + 0,5) | 25 cm | 8 + 8 = 16 | 81 cm derin (alt uçta) | kol boyu 200; kat farkı 282 için rıht ≈ 17,6 |
| `[kişi] MERDİVEN.dxf` → `merdiven_tek_kollu_duz_375x122.dxf` | **tek kollu düz** | 375 × 122,5 cm | 122,5 | 25 cm | 15 | yok | kat farkı 282 için rıht ≈ 18,8; yanında 20,7 × 29,5 küçük detay (kiriş/limon?) |
| `Merdiven.dwg` → `Merdiven_CADler.dwg` (git dışı) | ? (AC1027, 101 KB) | — | — | — | — | — | Bulutta okunamaz (DWG); **AutoCAD'de salt okunur açılıp bakılacak** — Lokman'ın dediği "tüm varyasyonlar" bu olabilir |

## 2. Çelik merdiven panel çizimleri (ARK/LCAD hafif çelik yazılımı çıktıları; 3DFACE/SOLID; etiketler `80-120D07` = 80×120 profil, D/B/K/T parça kodu)

| Drive adı (maskeli) | İçerik | Kutu |
|---|---|---|
| `MERDİVEN PLAN.dxf` | merdiven paneli yerleşimi, 32 parça etiketi (80-120 B/D/K, 80-080 T) | 340 × 298 cm |
| `MERDİVEN YERLEŞİM PLANI.dxf` | LCAD duvar/kiriş/makas katmanları, DÝ01–DÝ26 parça etiketleri | 202 × 232 cm |
| `merdiven (2020-12-01).dxf` | 80-120 D01–D19 panel etiketli yerleşim | 463 × 139 cm |
| `[kişi] MERDİVEN PLAN.dxf` | 80-120 D01–D23 | 471 × 147 cm |
| `[kişi] MERDİVEN TAŞIYICI PANELLER.dxf` | taşıyıcı paneller, 14 etiket | 340 × 298 cm |
| `[kişi] - MERDİVEN PANELLERİ.dxf` | panel üretim föyleri: KUŞAK ×93, DİKME ×78, ÇAPRAZ ×14; Tip/Adet/Uzunluk(mm)/Toplam ağırlık tabloları (237, 1259, 1613 mm…) | 8.195 × 354 cm (yan yana föyler) |
| `[kişi] MERDİVEN.dwg` | DWG; okunmadı | — |

Bunlar **çelik hattı** (karkas merdiven) referanslarıdır; prefabrik çift kat için merdiven kuralı değildir, ama "merdiven paneli" mantığı
(taşıyıcı panel + kuşak/dikme/çapraz) ileride çelik çift kat için kullanılabilir.

Teknik not: Drive'daki eski DXF'ler Türkçe yerel ayarla yazılmış (ondalık **virgül**: `0,500000`); ezdxf kesri atıyor → sayı satırlarındaki
virgül noktaya çevrilerek okundu (`indirilen/cadler/duzeltilmis/`, bulut). Buraya alınan iki DXF düzeltilmiş kopyalardır.

## 3. Soru 2–3 için adaylar (Lokman karar verir)

- Bu evde merdiven kutusu planda 200 × 260 iç (taslakta 245 iç, 2 pano) + arkaya 125,5 çıkma. **Çift kollu U** (kol 126 + 126 = 252 > 245; 1 pano kola
  tam oturuyor, 2 pano kutuya 7 cm sığmıyor → kutu 2 pano + 10 cm ya da kol 120) ya da **tek kollu düz** (375 cm boy: 260 + 125,5 çıkma = 385,5 iç
  derinliğe sığar; kol 122,5 ≤ 245). Şablon 2024 örneğinde (1410×530) merdiven 193 cm'lik HOL+MERDİVEN'de düz kol.
- Kat farkı: 250 + 30 + 2 = 282 (R02 ara kat) → 16 rıht × 17,6 ya da 15 × 18,8; basamak 25 cm her iki çizimde de sabit.
- Şablon notu: 1. kat merdiven boşluğu çevresindeki iç duvarlar 100'lük ('+' işareti).
