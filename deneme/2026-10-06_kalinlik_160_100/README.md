# 6 Ekim 2026 · el çiziminden 3+1: duvar kalınlığı (dış 160 / iç 100 mm), ölçüye kesim, görünüşler, pano pano IFC ve yükleme listesi

Deneme kodu; canlıda değil, Motor'un yerine geçmez. Canlı `motor/` değişmedi.

İstekler (Lokman, 6 Ekim):
- 18:28 — el çizimi 3+1 plan prefabrik standardında, P6001 mantığında çizilecek; dış duvar 160 mm, iç duvar 100 mm, yükseklik 2800 mm.
- 18:50 — dış ölçüler 10,50 × 11,50 m, veranda yok. Çizim kuralı: her pano 1255 mm; dizilim yapının bitiş noktasına geldiğinde son parça kesilir, özel ölçülü olur.
- 18:58 — Ç8201'deki gibi görünüşler; Blender / IFC çizimlerindeki gibi pano pano.
- 19:11 — Astra dönemindeki yükleme listesi (Mac'te `AI Çizim Dosyaları`) örnek alınarak, daha iyisi olacak şekilde BOM listesi.
- 19:46 — geri bildirim: plan paftası bundan sonra ekteki "Örnek Şablon"un aynısı olacak; görünüşler her seferinde üretilecek; pano pano çizim kural. IFC Blender'da açılmadı; HTML'de fareyle çevirme ve çatı kaldırma çalışmadı. Kurallar: `docs/sartname/plan_paftasi_sablonu.md`.

| Dosya | İçerik |
|---|---|
| `yama.py` | `motor/` altındaki dört dosyayı okur, sabit yazılı yerleri İş Emri alanlarına bağlar, `cikti/motor_k/` altına yazar. Yama yeri kaynakta beklenen sayıda bulunmazsa durur |
| `is_emri_3arti1_1150x1050.json` | Geçerli İş Emri: dış ölçü 1150 × 1050 cm, verandasız; varsayımlar dosyanın içinde |
| `is_emri_3arti1_9x10.json` | İlk deneme (18:28): tam panoya yuvarlanmış, verandalı 9 × 10 pano. 18:50 isteğiyle geçersiz; kalınlık seçeneğinin ikinci örneği olarak koşuyor |
| `kos.py` | Sağlama (yeni alanlar yokken deneme kopyası = canlı Motor) ve iki çizim |
| `sablon_pafta.py` | Plan paftası, "Örnek Şablon" düzeninde (A4 yatay): plan, sol yan ve ön görünüş, bina özellikleri, özel istekler, antet. Yazı tipleri `font/` altında |
| `gorunus.py` | Dört görünüş paftası: her dış pano ayrı dikdörtgen, cephedeki sıra koduyla (Ö1…, A1…, SL1…, SĞ1…); kesilmiş panolar mor |
| `ifc_3b.py` | Pano pano IFC4 modeli (her pano bir IfcWall) ve tek dosyalık 3D sayfası; dosyayı yeniden açıp plan, Motor BOM'u ve görünüş paftasıyla karşılaştırır |
| `sayfa_3b.py` | IFC'den 3D sayfası (tek dosya, three.js gömülü): fareyle ya da parmakla çevirme, tekerlekle yakınlaştırma, ekranda görünüş düğmeleri; çatı, makas ve iç duvar aç / kapa; panoya tıklayınca pafta kodu ve ölçüsü. Yayın için kısa kopyasını da yazar |
| `ifc_gorsel.py` | IFC'den Blender (bpy, Cycles) görselleri; pano hacmini modeldeki metrajla karşılaştırır. `--blend` ile Blender'da doğrudan açılan `.blend` ve `.glb` dosyalarını yazar, dosyayı yeniden açıp denetler. Ayrı sanal ortam ister (Python 3.13, `pip install bpy ifcopenshell`) |
| `yukleme_listesi.py` | Yükleme listesi (Excel): Sayım, YÜKLEME, Metraj ve Açık konular sayfaları; bütün adetler formül |
| `hepsini_kos.sh` | Hepsini sırayla koşar, kanıtları `sonuc/` altına kopyalar |
| `sonuc/<iş emri no>/` | Son koşunun kanıtları: PDF, DXF, önizleme, BOM, doğrulama. `sonuc/motor_k.diff` Motor'a göre fark |
| `cikti/` | Koşu çıktıları (depoya girmez) |

## İş Emri'ne eklenen alanlar (yalnız denemede)

| Alan | Anlamı | Verilmezse |
|---|---|---|
| `yapi.duvar_kalinligi_cm` `{dis, ic}` | Dış ve iç duvar kalınlığı | 10 / 6 |
| `yapi.dis_olcu_cm` `{x, y}` | Dış ölçü; son aks yapının bitişine çekilir, son pano kesilir | Tam modül |
| dış kapıda `arasi: ["__DIS__", mahal]` ve `duvar` | Verandasız yapıda doğrudan dışarı açılan kapı ve cephesi | — |
| `pafta_uyarilari` | Paftanın altına yazılan uyarılar | Yok |
| `pafta` | Şablon paftasının antet ve tablo bilgileri, özel istekler, mahal adı karşılıkları, etiket yerleri | Bilinmeyen "..." |
| `tefris` | Şematik tefriş (tezgah, eviye, ocak, klozet, lavabo, duş); ölçü taşımaz | Yok |

## Çalıştırma

```
python deneme/2026-10-06_kalinlik_160_100/kos.py --sonuc
bash deneme/2026-10-06_kalinlik_160_100/hepsini_kos.sh [python] [bpy'li python]
```

`kos.py`, `cikti/<iş emri no>/` klasörünü baştan yazar; öteki çıktılar ondan sonra üretilmelidir (`hepsini_kos.sh` sırayı tutar).

## Sonuç · plan (6 Ekim 2026 18:57)

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

## Sonuç · görünüşler, IFC ve yükleme listesi (6 Ekim 2026 19:30)

- Görünüş paftası: dört cephe, cephe başına 9 pano (36 dış pano; 4'ü kesilmiş: 114 cm × 2, 30 cm × 2). Duvar 280, mahya kotu 473,1 (makas üstü), çatı üstü 487,1 cm.
- Çatı yönü: makaslar kısa kenarı (derinlik, 1050 cm) geçiyor, mahya ön cepheye paralel (`cati.makas_ekseni: "y"`). Ön ve arka görünüşte saçak, yan görünüşlerde kalkan görünür. Plan paftasındaki ön görünüş ve çatı profili Motor'un sabit yönüyle çizildiği için bununla çelişir; geçerli olan görünüş paftasıdır.
- IFC: 66 IfcWall (tipler PE-DIS-160 ve PE-IC-100), 8 pencere, 6 kapı, 7 mahal, 10 makas (pano akslarında), şema hatası 0. Yeniden açılan dosyada pano adedi, boy / kalınlık / yükseklik dağılımı, pano kodları (Motor BOM'u) ve dış pano boyları (görünüş paftası) aynı; mahya kotu aynı (473,1).
- Geometri: duvarların kutusu 11,50 × 10,50 × 2,80 m; panoların boşluk kesilmiş hacmi modeldeki metrajla aynı (24,9084 m³).
- Yükleme listesi: 44 kalem, 117 formül, hata yok. Sayılan kodlar Motor BOM'uyla aynı. Türetilen 14 kuralın 13'ü P6001'in gerçek yükleme listesindeki adedi veriyor; mahya parçası vermiyor (kural 4, liste 3).

| Astra listesi (Cumbalı 6×5, 7 Eylül) | Bu liste |
|---|---|
| Yalnız çizilmiş bloklar: pano, doğrama, köşe, üçlü H, veranda profili | Bunlara ek: pano eki H'ları, alt çerçeve, kör kasa, makas, çatı kaplaması, mahya, saçak ve alın sacı, aşık, şilte, tavan alçıpanı, dere |
| Sayım satırı: blok adı ve merkez koordinatı | Sayım satırı: cephe, pafta kodu (Ö1…), boy, kalınlık, yükseklik, açıklık, IFC adı |
| Çatı, profil ve tavan "çizimde tanımlı değil" diye dışarıda | Kuralı bilinenler formülle içeride; her kuralın dayanağı ve P6001 sağlaması Metraj sayfasında; kuralı bilinmeyenler Açık konular sayfasında |

## Sonuç · şablon paftası, 3D sayfası ve Blender dosyası (6 Ekim 2026 20:15)

- Plan paftası şablonun çerçeveleriyle çizildi (A4 yatay, 842 × 595 pt; ölçüler şablon PDF'inden okundu). Ölçek 0,238 pt/cm (yaklaşık 1:119); şablonda 0,2975 (yaklaşık 1:95). Zincirler: arka 518 + 314 + 318, ön 518 + 439 + 193, sağ 322 + 314 + 414; her biri dış ölçüye eşit (1150, 1050). Mahal alanları tam sayı m².
- Ön görünüş bu paftada doğru yönde: saçak önde, kalkan sol yanda (makaslar 10,50 m'lik kenarı geçiyor). Motor'un eski plan paftasındaki çelişki bu paftada yok.
- Şablon PDF'i kişi adı ve gerçek proje kodu taşıdığı için depoya alınmadı. Antette Çizen "Portman", Kontrol ve Onay "...".
- 3D sayfası yeniden yazıldı. Eski sayfada çatı örtüsü "çatı" listesinde olmadığı için düğme onu gizlemiyordu. Tarayıcı sınaması (Chromium; masaüstü 1280 × 800 ve telefon 400 × 760): sürükleyince döndü, tekerlekle yakınlaştı, çatı düğmesi dört parçayı gizledi, makaslar gizlendi, yedi oda adı göründü, panoya tıklayınca kodu ve ölçüsü geldi, konsolda hata yok.
- Blender, IFC'yi Bonsai eklentisi olmadan açmaz. `.blend` dosyası Blender 5.2.2 ile yazıldı, yeniden açılıp denetlendi: 66 pano, hepsi pafta kodlu, kutu 11,50 × 10,50 × 2,80 m; on katman (çatıyı kaldırmak için 05 ve 06 kapatılır).
- Lokman'ın ortamında eski sayfada çevirmenin neden çalışmadığı bilinmiyor; Chromium'da çalışıyordu. Astra'nın sayfası görülmedi.

## Çıkarımlar (teyit edilene kadar kural değil)

- Dizilimin başlangıç ucu: soldan ve önden. Kesilen parça sağ ve arka uçta.
- İç duvarlar aks üstünde kalır (tam ya da yarım pano); el çizimindeki oda ölçüsüne en yakın aksa oturtuldu.
- Bağlantılar: dış köşe parçası 160 × 80, iç köşe 100 × 50 (katalogdaki B02 ile aynı ölçüye düştü), üçlü H 100.
- Pencere üst kotu 200 cm sabit; 280 cm duvarda lento 80 cm.
- Yeni pano kodları çalışma kopyasında; ana kataloğa yazılmadı.
- Makaslar pano akslarında: iki baş makas kalkan duvarların ekseninde, orta makaslar pano eklerinde (P6001 gerçek listesinde 6 pano boyunca 2 baş + 5 orta).
- Yükleme listesindeki "liste kuralı" kalemleri tek bir gerçek listeden (P6001, 60 m², 2021–2022) çıkarıldı; o listede tutmaları teyit değildir.
- Dere kalemleri çelik listelerinin kuralıyla hesaplandı; prefabrik pakette dere olup olmadığı bilinmiyor.
- IFC'de 160 mm panonun katmanları 8 + 144 + 8 mm yazıldı (100 mm panodaki 8 + 84 + 8'den); teyit bekliyor.

## Motor'da görülenler

- Kalınlık Motor'un dört dosyasında sabit yazılı; yerleri `sonuc/motor_k.diff`'te.
- Ölçüye kesim Motor'da yok (`yapi.ozel_pano` "desteklemiyor" diye durur). Kalıcı olması ayrı bir iş emri ister.
- Malzeme kataloğunda pano kodunun anahtarı yalnız boy ve türdür; kalınlık ve yükseklik anahtarda yok.
- Dış kapı yalnız verandadan açılabiliyor; verandasız yapı çizilemiyor.
- Doğrulama, duvarların dış kutuyu doldurmasını bekliyor; cephenin tamamı veranda olunca geçmiyor.
- Ön görünüş ve çatı profili ön cepheyi kısa kenar sayar. Bu yapıda ön cephe 11,50 m ile uzun kenardır; makaslar kısa kenara (10,50 m) dönecekse görünüş ve profil yanlış yönde çiziliyor.
- Katalog dışı pencere ölçüsü Motor'da yok; standart ölçülere çevrildi.

## Lokman'dan beklenenler

Yükleme listesinin "Açık konular" sayfasında on üç madde var; öne çıkanlar:

1. Kesilen parça çok dar çıkınca (arkada 30 cm, iç duvarda 22 cm) ne yapılır: böyle mi kalır, bir önceki panoyla mı paylaştırılır? En az pano boyu var mı?
2. Çatı yönü: makaslar 10,50 m'lik kenarı mı geçecek?
3. 160 mm dış ve 100 mm iç duvarda köşe ve H bağlantı profilleri (mühendis).
4. Geniş pencereler standart ölçülere çevrilsin mi, özel doğrama mı?
