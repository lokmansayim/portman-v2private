# 6 Ekim 2026 · duvar kalınlığı (dış 160 / iç 100 mm), ölçüye kesim ve el çiziminden 3+1

Deneme kodu; canlıda değil, Motor'un yerine geçmez. Canlı `motor/` değişmedi.

İstekler (Lokman, 6 Ekim):
- 18:28 — el çizimi 3+1 plan prefabrik standardında, P6001 mantığında çizilecek; dış duvar 160 mm, iç duvar 100 mm, yükseklik 2800 mm.
- 18:50 — dış ölçüler 10,50 × 11,50 m, veranda yok. Çizim kuralı: her pano 1255 mm; dizilim yapının bitiş noktasına geldiğinde son parça kesilir, özel ölçülü olur.

| Dosya | İçerik |
|---|---|
| `yama.py` | `motor/` altındaki dört dosyayı okur, sabit yazılı yerleri İş Emri alanlarına bağlar, `cikti/motor_k/` altına yazar. Yama yeri kaynakta beklenen sayıda bulunmazsa durur |
| `is_emri_3arti1_1150x1050.json` | Geçerli İş Emri: dış ölçü 1150 × 1050 cm, verandasız; varsayımlar dosyanın içinde |
| `is_emri_3arti1_9x10.json` | İlk deneme (18:28): tam panoya yuvarlanmış, verandalı 9 × 10 pano. 18:50 isteğiyle geçersiz; kalınlık seçeneğinin ikinci örneği olarak koşuyor |
| `kos.py` | Sağlama (yeni alanlar yokken deneme kopyası = canlı Motor) ve iki çizim |
| `sonuc/<iş emri no>/` | Son koşunun kanıtları: PDF, DXF, önizleme, BOM, doğrulama. `sonuc/motor_k.diff` Motor'a göre fark |
| `cikti/` | Koşu çıktıları (depoya girmez) |

## İş Emri'ne eklenen alanlar (yalnız denemede)

| Alan | Anlamı | Verilmezse |
|---|---|---|
| `yapi.duvar_kalinligi_cm` `{dis, ic}` | Dış ve iç duvar kalınlığı | 10 / 6 |
| `yapi.dis_olcu_cm` `{x, y}` | Dış ölçü; son aks yapının bitişine çekilir, son pano kesilir | Tam modül |
| dış kapıda `arasi: ["__DIS__", mahal]` ve `duvar` | Verandasız yapıda doğrudan dışarı açılan kapı ve cephesi | — |
| `pafta_uyarilari` | Paftanın altına yazılan uyarılar | Yok |

## Çalıştırma

```
python deneme/2026-10-06_kalinlik_160_100/kos.py --sonuc
```

## Sonuç (6 Ekim 2026 18:57)

- Sağlama: P6001, 6×8 ve Yan Verandalı 6×8,5 İş Emri'lerinde deneme kopyası canlı Motor'la aynı geometriyi, doğrulamayı ve BOM'u verdi (36, 41 ve 52 pano).
- 1150 × 1050: doğrulama geçti. 66 pano (36 dış, 30 iç), 8 pencere, 6 kapı, 6 köşe parçası, 4 üçlü H. Kapalı net 110,75 m².
- Dizilim: genişlikte 8 tam pano + 114 cm, derinlikte 8 tam pano + 30 cm. Akslar sol dış duvarın iç yüzünden (16 cm) ve ön duvarın ekseninden (8 cm) başlar; kesilen parça sağ ve arka uçtadır.
- Özel panolar: dış 114 cm × 2 ve 30 cm × 2; iç 120,5 × 3, 117,5 × 2, 62,75 × 2, 57,75 × 3, 51,25 × 2, 22 cm × 2. 22 cm'lik parçalar arka yatak odalarının iki duvarının arka ucundadır (30 cm'lik son aks, eksi dış duvarın yarısı).

| Mahal | El çiziminde | Planda (net) |
|---|---|---|
| Dış ölçü | 11,50 × 10,50 m | 11,50 × 10,50 m |
| Yaşam alanı | 4,50 × 10,00 · 45,0 m² | 4,97 × 10,18 · 50,8 m² |
| Yatak odası 1 (ebeveyn) | 4,30 × 4,40 · 19,0 m² | 4,29 × 4,26 · 18,3 m² |
| Hol | 4,30 × 1,50 · 6,45 m² | 4,29 × 1,78 · 7,65 m² |
| Yatak odası 2 | 3,00 × 4,00 · 12,0 m² | 3,04 × 3,94 · 11,95 m² |
| Yatak odası 3 | 3,00 × 4,00 · 12,0 m² | 2,97 × 3,94 · 11,7 m² |
| Ebeveyn banyosu | 1,80 × 2,95 · 5,3 m² | 1,72 × 3,01 · 5,2 m² |
| Banyo | 1,80 × 2,95 · 5,3 m² | 1,72 × 3,04 · 5,2 m² |

El çiziminde duvarlar 25 / 15 cm; burada 16 / 10 cm olduğu için iç net ölçü 11,00 × 10,00'dan 11,18 × 10,18 m'ye çıkıyor.

## Çıkarımlar (teyit edilene kadar kural değil)

- Dizilimin başlangıç ucu: soldan ve önden. Kesilen parça sağ ve arka uçta.
- İç duvarlar aks üstünde kalır (tam ya da yarım pano); el çizimindeki oda ölçüsüne en yakın aksa oturtuldu.
- Bağlantılar: dış köşe parçası 160 × 80, iç köşe 100 × 50 (katalogdaki B02 ile aynı ölçüye düştü), üçlü H 100.
- Pencere üst kotu 200 cm sabit; 280 cm duvarda lento 80 cm.
- Yeni pano kodları çalışma kopyasında; ana kataloğa yazılmadı.

## Motor'da görülenler

- Kalınlık Motor'un dört dosyasında sabit yazılı; yerleri `sonuc/motor_k.diff`'te.
- Ölçüye kesim Motor'da yok (`yapi.ozel_pano` "desteklemiyor" diye durur). Kalıcı olması ayrı bir iş emri ister.
- Malzeme kataloğunda pano kodunun anahtarı yalnız boy ve türdür; kalınlık ve yükseklik anahtarda yok.
- Dış kapı yalnız verandadan açılabiliyor; verandasız yapı çizilemiyor.
- Doğrulama, duvarların dış kutuyu doldurmasını bekliyor; cephenin tamamı veranda olunca geçmiyor.
- Ön görünüş ve çatı profili ön cepheyi kısa kenar sayar. Bu yapıda ön cephe 11,50 m ile uzun kenardır; makaslar kısa kenara (10,50 m) dönecekse görünüş ve profil yanlış yönde çiziliyor.
- Katalog dışı pencere ölçüsü Motor'da yok; standart ölçülere çevrildi.

## Lokman'dan beklenenler

1. Kesilen parça çok dar çıkınca (arkada 30 cm, iç duvarda 22 cm) ne yapılır: böyle mi kalır, bir önceki panoyla mı paylaştırılır? En az pano boyu var mı?
2. Çatı yönü: makaslar 10,50 m'lik kenarı mı geçecek?
3. 160 mm dış ve 100 mm iç duvarda köşe ve H bağlantı profilleri (mühendis).
4. Geniş pencereler standart ölçülere çevrilsin mi, özel doğrama mı?
