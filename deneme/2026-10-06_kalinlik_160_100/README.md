# 6 Ekim 2026 · duvar kalınlığı seçeneği (dış 160 / iç 100 mm) ve el çiziminden 3+1

Deneme kodu; canlıda değil, Motor'un yerine geçmez. Canlı `motor/` değişmedi.

İstek (Lokman, 6 Ekim 18:28): el çizimi 3+1 plan prefabrik standardında, P6001 mantığında çizilecek; dış duvar 160 mm, iç duvar 100 mm, yükseklik 2800 mm.

| Dosya | İçerik |
|---|---|
| `yama.py` | `motor/` altındaki dört dosyayı okur, kalınlığın sabit yazıldığı yerleri İş Emri'ndeki `yapi.duvar_kalinligi_cm` alanına bağlar, `cikti/motor_k/` altına yazar. Yama yeri kaynakta beklenen sayıda bulunmazsa durur |
| `is_emri_3arti1_9x10.json` | El çiziminin İş Emri (9 × 10 pano); varsayımlar dosyanın içinde |
| `kos.py` | Sağlama (kalınlık alanı yokken deneme kopyası = canlı Motor) ve çizim |
| `sonuc/` | Son koşunun kanıtları: PDF, DXF, önizleme, BOM, doğrulama, `motor_k.diff` (Motor'a göre fark) |
| `cikti/` | Koşu çıktıları (depoya girmez) |

## Çalıştırma

```
python deneme/2026-10-06_kalinlik_160_100/kos.py --sonuc
```

## Sonuç (6 Ekim 2026 18:45)

- Sağlama: P6001, 6×8 ve Yan Verandalı 6×8,5 İş Emri'lerinde deneme kopyası canlı Motor'la aynı geometriyi, doğrulamayı ve BOM'u verdi (36, 41 ve 52 pano).
- 3+1: doğrulama geçti. Dış ölçü 1161,5 × 1271 cm (gövde 1161,5 × 1020; önde 251 cm veranda). 62 pano (34 dış, 28 iç), 8 pencere, 6 kapı, 6 köşe parçası, 4 üçlü H.
- Aks kuralı kalınlıkla genelleşti: düşey akslar dış duvarın iç yüzünden başlar (16 cm), yatay akslar duvar eksenindedir (8 cm); dış ölçü = pano × 125,5 + 32 (x) ve + 16 (y).

| Mahal | El çiziminde | Planda (net) |
|---|---|---|
| Dış ölçü (teras hariç) | 11,50 × 10,50 m | 11,615 × 10,20 m |
| Yaşam alanı | 4,50 × 10,00 · 45,0 m² | 4,97 × 9,88 · 49,3 m² |
| Yatak odası 1 (ebeveyn) | 4,30 × 4,40 · 19,0 m² | 4,29 × 4,26 · 18,3 m² |
| Hol | 4,30 × 1,50 · 6,45 m² | 4,29 × 1,78 · 7,65 m² |
| Yatak odası 2 | 3,00 × 4,00 · 12,0 m² | 3,04 × 3,64 · 11,0 m² |
| Yatak odası 3 | 3,00 × 4,00 · 12,0 m² | 3,09 × 3,64 · 11,2 m² |
| Ebeveyn banyosu | 1,80 × 2,95 · 5,3 m² | 1,83 × 3,01 · 5,5 m² |
| Banyo | 1,80 × 2,95 · 5,3 m² | 1,83 × 3,04 · 5,6 m² |
| Teras / veranda | 2,40 m · 27,6 m² | 2,51 m · 29,2 m² |

Kapalı net toplam 108,6 m² (çizimde 105,0 m²).

## Çıkarımlar (teyit edilene kadar kural değil)

- Bağlantılar: dış köşe parçası 160 × 80, iç köşe 100 × 50 (katalogdaki B02 ile aynı ölçüye düştü), üçlü H 100. 60 mm'lik üçlü H bloğu 100/60 oranında büyütüldü.
- Pencere üst kotu 200 cm sabit; 280 cm duvarda lento 80 cm (250'de 50, çelik 270'te 70 ile aynı mantık).
- Pencere sembolü duvar kalınlığının ortasında; iç kapı kasası açıldığı odanın yüzünde.
- Yeni pano kodları (D09–D13, I12–I17, B05, B06) çalışma kopyasında; ana kataloğa yazılmadı.

## Motor'da görülenler

- Kalınlık Motor'un dört dosyasında sabit yazılı; yerleri `sonuc/motor_k.diff`'te. Kalıcı seçenek olması ayrı bir iş emri ister.
- Malzeme kataloğunda pano kodunun anahtarı yalnız boy ve türdür; kalınlık ve yükseklik anahtarda yok. 280 cm ya da 160 mm bir pano bugün 100 mm / 250 cm'lik D01 kodunu alır.
- Doğrulama, duvarların dış kutuyu (0, 0, W, H) doldurmasını bekliyor; cephenin tamamı veranda olunca geçmiyor. Denemede denetim Plan'ın ayak izine ve açık mahallerle birlikte dış kutuya bakıyor.
- Paftada alt sıra sabit konumda; geniş binada çatı profili başlığı notların üstüne biniyor. Denemede alt sıra çatı yüksekliği kadar aşağı kayıyor.
- Katalog dışı pencere ölçüsü (240/240, 150/240, 100/240, 180/120, 60/60) Motor'da yok; standart ölçülere çevrildi.

## Lokman'dan beklenenler

1. 160 mm dış ve 100 mm iç duvarda köşe ve H bağlantı profilleri (mühendis).
2. Geniş pencereler standart ölçülere çevrilsin mi, özel doğrama mı?
3. Derinlik: çizimin yazılı ölçüsü 10,50 m (8 pano, 10,20 m); oda ölçülerinin toplamı 10,80 m (8,5 pano, 10,83 m). 8 pano alındı.
4. Çatı tipi (çizimde yok; beşik %33 varsayıldı) ve veranda dikmelerinin yeri.
