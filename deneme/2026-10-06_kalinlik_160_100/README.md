# 6 Ekim 2026 · el çiziminden 3+1: duvar kalınlığı (dış 160 / iç 100 mm), ölçüye kesim, görünüşler, pano pano IFC ve yükleme listesi

Deneme kodu; canlıda değil, Motor'un yerine geçmez. Canlı `motor/` değişmedi.

> **12 Ekim 2026 notu (İE-10, D-10):** buradaki 160 / 100 mm duvar kalınlığı **standart değildir**; müşteriden gelen özel bir örnekti
> (Lokman: "binde bir gelir"). Prefabrik standardı dış 100 / iç 60 mm'dir; 160 / 100 yalnız `kurallar/model/secenekler/duvar_kalinligi_160_100.json`
> seçeneğidir. Bu klasördeki ölçüye kesim, görünüş, IFC, 3D sayfası ve yükleme listesi çalışmaları kalınlıktan bağımsız olarak geçerlidir.

İstekler (Lokman, 6 Ekim):
- 18:28 — el çizimi 3+1 plan prefabrik standardında, P6001 mantığında çizilecek; dış duvar 160 mm, iç duvar 100 mm, yükseklik 2800 mm.
- 18:50 — dış ölçüler 10,50 × 11,50 m, veranda yok. Çizim kuralı: her pano 1255 mm; dizilim yapının bitiş noktasına geldiğinde son parça kesilir, özel ölçülü olur.
- 18:58 — Ç8201'deki gibi görünüşler; Blender / IFC çizimlerindeki gibi pano pano.
- 19:11 — Astra dönemindeki yükleme listesi (Mac'te `AI Çizim Dosyaları`) örnek alınarak, daha iyisi olacak şekilde BOM listesi.
- 21:26 — videolardaki 44 çatı şekli, kurallarımıza göre, Astra'nın yaptığı gibi uygulanabilir mi?
- 21:00 — plan çok iyi; 3D sayfası yine beğenilmedi, örnek olarak Astra'nın sunum sayfası gösterildi (Mac'te `~/Documents/Codex/2026-09-30/…/outputs/Uc_Model_Sunum/Incele.html`).
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
| `sayfa_3b.py` | IFC'den 3D sunum sayfası (tek dosya, three.js gömülü), Astra'nın 30 Eylül sunum sayfasının düzeninde: başlık bandı, çerçeveli sahne, yan pano ve plan; "Dış görünüş / Üstten bak / Çatıyı aç / Çatı iskeleti / Pano renkleri / Oda adları / Döndür"; parçaların sırayla belirdiği "Oluşumu oynat" ve sürgüsü; malzemeli görünüş (ışık, gölge, trapez sac çatı); panoya tıklayınca pafta kodu ve ölçüsü. Yayın için kısa kopyasını da yazar |
| `cati_secenekleri.py` | Aynı gövdenin üzerine altı çatı seçeneği (A–F); örtü, kalkan kapaması ve pano akslarındaki makaslar kuraldan hesaplanır. `sayfa_3b.py` bunları kart olarak sayfaya koyar |
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

## Sonuç · 3D sunum sayfası, ikinci tur (6 Ekim 2026 21:30)

- Lokman 21:00'de sayfayı yine beğenmedi ve Astra'nın sayfasını gösterdi. Dosya Mac'te bulundu ve okundu (yalnız okundu; depoya kopyalanmadı): üç modelin SketchUp kaynağından aktarıldığı bir sunum sayfası. Farkı yapan üç şey: düzen (başlık bandı, çerçeveli sahne, yanında bilgi ve plan), malzemeli görünüş (ışık, ton eşleme, dokulu çatı) ve parçaların sırayla belirdiği oluşum sürgüsü.
- `sayfa_3b.py` bu düzende yeniden yazıldı. Model yine İş Emri'nden üretilen IFC'den gelir; Astra'nın modelindeki gibi SKP'den değil. Bu yüzden her pano ayrı parçadır ve pafta kodunu taşır; buna karşılık SKP'deki mobilya, perde, kaplama dokusu gibi ayrıntılar yoktur.
- Duvar yüzeyleri düz gölgeleniyor (önceki sayfada köşelerde parlama vardı: köşe normalleri ortaklanıyordu). Çatı trapez sac dokusuyla, hadveler mahyadan saçağa.
- "Çatıyı aç" örtüyü, alınları ve makasları kaldırır, kamerayı yukarı alır ve oda adlarını gösterir (adlar plan paftasındakiyle aynı). "Çatı iskeleti" yalnız örtüyü kaldırır.
- Tarayıcı sınaması (Chromium; masaüstü 1440 × 900 açık tema, telefon 400 × 800 koyu tema): sürükleyince döndü, tekerlekle yakınlaştı, çatı açıldı (örtü 0, makas 0, yedi oda adı), iskelet (makas 80 parça), pano renkleri, sürgü %45'te 36 dış + 30 iç pano ve çatı yok, oluşum oynadı, panoya tıklayınca kodu geldi, "Döndür" çevirdi, plan büyüyüp kapandı, yatay kaydırma yok, sayfa hatası yok.
- Çatı rengi bilinmediği için gri. Renkler sunum içindir.

## Sonuç · çatı seçenekleri (6 Ekim 2026 22:10)

İstek (21:26): videolardaki 44 çatı şekli, kurallarımıza göre, Astra'nın P9401'de yaptığı gibi (dört seçenek, kartlarla).

Videoya bakıldı (Lokman'ın 29 Eylül'de verdiği altı videodan "44 farklı seçenek" olanı; Mac'te Astra'nın devir klasöründe; yalnız okundu). 44 seçenek çatı değil, aynı ev için 44 **plan ve kütle biçimi**: T, L, H ve haç planlar, yan yana ya da bağlantılı iki-üç gövde, avlulu, iki katlı ve çatı katlı evler; aralarında düz gövdeli olanların çatısı beşik, kırma (piramit), tek eğimli ya da düz. Küçük resimler videoda yaklaşık 40 piksel; tek tek ölçü okunmaz, biçim ailesi seçilir. Kabaca: 44'ün üçte biri tek gövdeli dikdörtgen, yarıya yakını farklı plan biçimi, kalanı iki katlı.

Şartname (`docs/sartname/cati.md`): çatı aileleri beşik, cumba, dört omuz/kırma; eğim değişmez (%33); saçak 30, topuk 10. Buna göre aynı gövdenin (11,50 × 10,50 m, tek kat) üzerine altı seçenek üretildi:

| Kod | Çatı | Durum | Mahya / üst kot | Makas | Not |
|---|---|---|---|---|---|
| A | Beşik, mahya ön cepheye paralel | Kurallı | 4,73 m | 10 × 10,50 m | Bugünkü çatı (IFC'deki) |
| B | Beşik, kalkan ön cephede | Kurallı | 4,90 m | 10 × 11,50 m | Arkadaki 30 cm'lik pano yüzünden son iki makas 30 cm arayla düşer |
| C | Kırma (dört omuz) | Biçim kurallı; makas dizilimi çıkarım | 4,73 m | 10 kademeli | Mahya 1,00 m; dört kırma hattı 8,06 m; kalkan duvar yok |
| D | Tek eğimli | Öneri; kural dışı (eğim %10) | önde 2,90 · arkada 4,01 m | 10 tek eğimli | %33 ile arka duvar 6,56 m'ye çıkar |
| E | Parapetli düz | Öneri; kural dışı | parapet üstü 3,25 m | 8 düz kiriş | Su tahliyesi çözülmedi |
| F | Üç mahyalı | Öneri; eğim kurala uygun, iç dere kuralı yok | 3,63 m | 10 üç gözlü | İki iç dere |

- Eğim sabit olduğu için A, B, C ve F'de örtü alanı aynıdır (141,4 m²); değişen mahya ve kırma hattı boyu, kalkan duvar alanı ve makas açıklığıdır.
- Geometri `cati_secenekleri.py`'de kuraldan hesaplanır; sayfa yalnız gösterir. A'nın ölçüleri görünüş paftası ve IFC ile aynı (mahya 473,15 cm, örtü üstü 487,15 cm, örtü 141,43 m²). Makas biçimleri şematiktir.
- Seçenekler yalnız 3D sayfasındadır. Plan paftası, görünüşler, IFC, Blender dosyası ve yükleme listesi A çatısıyla duruyor; bir seçenek seçilince o çatıyla yeniden üretilir.
- Videodaki öteki biçimler çatı seçimi değil, plan değişikliğidir (T, L, avlulu, iki katlı): ayrı İş Emri ister. Cumbalı çatı da gövdede çıkma (cumba) olmadan uygulanmaz.
- Tarayıcı sınaması (Chromium; masaüstü ve telefon): altı kartın görseli oluştu; her kartta örtü, kalkan ve makas parçaları değişti, üst kotlar hesapla aynı (4,872 · 5,036 · 4,872 · 4,150 · 3,285 · 3,772 m); çatı açma, iskelet, oluşum sürgüsü ve çevirme her seçenekte çalışıyor; sayfa hatası yok.

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
