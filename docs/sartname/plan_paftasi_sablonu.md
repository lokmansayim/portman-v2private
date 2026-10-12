# Plan paftası şablonu ve her işte üretilecek çizimler

Kaynak: Lokman, 6 Ekim 2026 19:46. Ekinde "Örnek Şablon" adlı tek sayfalık PDF vardı (AutoCAD çıktısı).
Şablon dosyası kişi adı ve gerçek bir proje kodu taşıdığı için depoya alınmadı; burada yalnız düzeni ve ölçüleri durur.

## Kurallar (Lokman, 6 Ekim 19:46)

1. **Plan paftası bundan sonra "Örnek Şablon"un aynısı olur.** Önceki plan paftasında eksik yoktu, çizim kuralları doğru uygulanmıştı; değişen paftanın biçimidir.
2. **Görünüşler her seferinde üretilir.** Dört cephe: ön, arka, sol, sağ.
3. **Çizim pano pano yapılır.** Görünüşlerde ve 3B modelde her pano ayrı parçadır ve pafta kodunu taşır (Ö1…, A1…, SL1…, SĞ1…).

Bunların dışında kalanlar (yükleme listesi, IFC, Blender dosyası) için "her seferinde" denmedi; istenince üretilir.

## Şablonun düzeni (ölçülen)

Sayfa A4 yatay, 842 × 595 pt. Ölçüler pt; x soldan, y yukarıdan. Köşeler yuvarlak (yarıçap ≈ 4 pt), çizgi 0,72 pt siyah.

| Alan | Sol, üst, sağ, alt | İçerik |
|---|---|---|
| Dış çerçeve | 10,3 · 2,4 · 835,8 · 590,8 | Köşeli, kalın |
| Çizim alanı | 22,9 · 15,0 · 686,8 · 522,3 | Plan, sol yan görünüş, ön görünüş |
| Bina özellikleri | 691,9 · 15,0 · 824,9 · 249,9 | Başlık ve 15 satır; sütun bölmesi x = 761,4 |
| Özel istekler | 691,7 · 255,6 · 824,6 · 521,0 | Numaralı maddeler |
| Antet sol | 22,9 · 528,6 · 277,9 · 578,3 | Şablonda boş |
| Antet orta | 282,4 · 528,6 · 686,8 · 578,3 | 4 satır; sütun bölmesi x = 423,8 |
| Antet sağ | 691,7 · 527,2 · 824,6 · 578,3 | 4 satır; sütun bölmesi x = 760,1 |

Çizim alanının içi:

- **Plan** ortada, üstte. Arka cephe yukarıda, ön cephe aşağıda.
- **Sol yan görünüş** planın solunda, 90° döndürülmüş: zemin solda, çatı plana bakar. Düşeyde planla aynı hizadadır (arka uç yukarıda).
- **Ön görünüş** planın altında, planla aynı x hizasında. Sağında duvar yüksekliği ölçüsü.
- Görünüş başlıkları gri, altı çizili: "SOL YAN GÖRÜNÜŞ" (dikey), "ÖN GÖRÜNÜŞ".

Tablolar:

- **Bina özellikleri** satırları, sırayla: Bina Yüksekliği, Dış Duvarlar, İç Duvarlar, Panel Türü, Çatı Şekli, Çatı Eğimi, Çatı Kaplaması, Çatı Kaplama Rengi, Dış Kapı, İç Kapılar, Pencereler, Vasistaslar, Dış Boya Rengi, İç Boya Rengi, Köşe ve Söveler.
- **Antet orta** satırları: Proje Kodu, İlgili Kişi-Telefon, Sevk Adresi, Proje Adı & M².
- **Antet sağ** satırları: Tarih, Çizen, Kontrol, Onay.
- Bilinmeyen değer "..." yazılır (şablonda da öyle).

Yazı ve renk:

| Öğe | Yazı | Renk |
|---|---|---|
| Tablo ve antet | Comic Sans MS, 7,3 pt | Siyah |
| "BİNA ÖZELLİKLERİ" başlığı | Comic Sans MS, 10,9 pt | Koyu kırmızı `#991B1E` |
| Özel istekler | Comic Sans MS, 7,6 pt | Koyu kırmızı `#991B1E` |
| Ölçü yazısı | Arial, 10,7 pt | Siyah |
| Ölçü çizgisi ve çentiği | — | Açık mavi `#6EC2DD` |
| Mahal adı ve m² | Arial, 8,4 ve 8,6 pt | Gri `#939598` |
| Pencere etiketi (120x120, V.60x40) | Comic Sans MS, 5,0 pt | Siyah |
| Kapı eni | Comic Sans MS, 3,6 pt | Gri |
| Tefriş (tezgah, eviye, ocak, klozet, lavabo, duş) | — | Turuncu `#DDA56E` |
| Açık mahal (veranda) kenarı | Kesik çizgi | Kırmızı `#FF0000` |
| Görünüş başlığı | Comic Sans MS, 8,0 pt, altı çizili | Gri |

Plan çizimi:

- Duvarlar çift çizgi; pano ekleri duvarı kesen kısa çizgiyle görünür. Köşe ve birleşim parçaları açık mavi küçük kutu.
- Mahal adı büyük harf, altında tam sayıya yuvarlanmış m². Yaşam alanı "SALON+MUTFAK" diye yazılır.
- Kapı: kanat açık mavi kalın çizgi, açılma yayı siyah kesik çizgi, yanında eni.
- Pencere: duvar içinde açık mavi çerçeve, etiketi dış yüzde.
- Ölçü zinciri dört yanda: içte oda bölmeleri, dışta toplam dış ölçü. Ölçüler cm, tam sayı; parçaların toplamı dış ölçüye eşittir.
- Şablonun ölçeği 0,2975 pt/cm (yaklaşık 1:95). Yapı büyüdükçe ölçek çizim alanına sığacak kadar küçülür; şablondakinden büyük tutulmaz.

Görünüş çizimi:

- Duvar beyaz, pano ekleri düşey çizgi; köşe dikmeleri gri.
- Çatı kaplaması, "Çatı Kaplama Rengi" satırındaki renkle boyanır ve trapez çizgileri taşır. Renk bilinmiyorsa gri çizilir.
- Pencerede açılan kanat kırmızı kesik üçgenle, sabit cam eğik çizgilerle gösterilir. Dış kapı kahverengi, yatay çizgili.
- Altta gri taş desenli subasman şeridi.

## Ana koddaki karşılığı (İE-08, 12 Ekim 2026)

`motor/genel/sablon_pafta.py`: aynı düzen ve kurallar (sayfa, tablolar, yazı ve renkler, ölçek), geometri genel motordan (Yapı Tanımı 0.5,
cm, serbest aks: duvarlar, mahaller ve açıklıklar `yapi.kur`, sol yan ve ön görünüş `sahne` izdüşümü, çatı profili `cati_genel`).
Çıktı `<kod>_pafta.pdf` (A4 yatay, 2 sayfa: 1. sayfa şablonun aynısı, 2. sayfa dört görünüş ve çatı planı) ve `<kod>_pafta_sablon.png`
önizleme; `python -m motor.genel.uret` her modelde üretir, bayiye giden paftadır (A3). Çelikte pano eki çizilmez (kural yok; 8a dışı).
Antet ve tablolar İş Emri zarfından ve tanımdan: Proje Kodu = İş Emri no, Proje Adı & M² = model kodu ve m², Tarih = üretim günü
(`time.gmtime`; referans koşusunda sabit), Çizen "Portman", Kontrol ve Onay "..."; Bina özellikleri tanım ve kural kitabından
(yükseklik, duvarlar, çatı şekli/eğimi/kaplaması, kapı ve pencere sayım ve ölçüleri), gerisi "..."; Özel istekler = bayinin değişiklik
cümleleri, yoksa "...". Yazı tipleri `motor/genel/font/` (Comic Relief, OFL). Genel motorun kendi `pafta.png`'si (mühendis paftası,
açıklama satırlarıyla) çizim setinde kalır, baytları değişmedi.

## Denemedeki karşılığı

`deneme/2026-10-06_kalinlik_160_100/sablon_pafta.py`, İş Emri'nden bu düzende PDF ve PNG üretir (pano birimli Motor'un deneme kopyası; tarih kaydı).

- Yazı tipi: Comic Sans MS lisanslı olduğu için eşi Comic Relief (SIL OFL; Türkçe harfleri tam) kullanıldı. Arial yerine Liberation Sans. Lokman aslını isterse yazı tipi dosyası gerekir.
- Çizime girmeyen bilgiler İş Emri'nin `pafta` bloğundan gelir: proje adı, ilgili kişi, sevk adresi, tarih, çizen, kontrol, onay, özellik satırları, özel istekler, mahal adı karşılıkları. Tefriş `tefris` listesinden gelir ve şematiktir.
- Dar mahalde (banyo) ad odaya sığmazsa yazı küçülür; yeri `pafta.etiket_yeri_cm` ile verilebilir.
- Ön ve sağ zincirde ölçü yazısı duvarla çizgi arasına düştüğü için zincir 8 pt dışarı alındı; şablonda bu yazılar pencere etiketine değiyor.

## Açık sorular

İE-08 planında (12 Ekim 2026, Soru 18–21) her biri için öneri yazıldı; plan onayıyla varsayılan karar sayıldı, Lokman itiraz ederse değişir:

- Antetin sol kutusu şablonda boş. Oraya firma logosu mu gelecek? → *Öneri: firma logosu; dosyası verilince basılır, yoksa boş kalır (bugün boş).*
- Çizen, Kontrol, Onay satırlarına kim yazılacak? → *Çizen "Portman", Kontrol "..." (8b'de mühendis adı), Onay "..." (Patron onayı sonraki iş).*
- Şablonda bir ön ve bir sol yan görünüş var. Dört görünüş ayrı paftada kalıyor; öyle mi kalsın? → *Aynı PDF'in 2. sayfası: dört görünüş ve çatı planı (ayrı dosya WhatsApp'ta ikinci belge ve ikinci ücret olurdu).*
- Panel Türü, Çatı Kaplama Rengi, boya renkleri, Köşe ve Söveler satırlarının değeri nereden gelecek (bayi talebi, model varsayılanı)? → *Panel Türü ve Çatı Kaplaması tanım + kural kitabı bazından; renkler ve Köşe/Söveler bayi söylediyse onunki, söylemediyse "..." (uydurulmaz, K21). Bayi standardı (`kurallar/bayi/<bayi>.json`) gelince oradan.*
- "İLGİLİ KİŞİ-TELEFON" alanı (ek, 12 Ekim): bayiye giden belgeye ad ve numara koyar; D-06 bayi adını kapsar, numarayı kapsamaz (Z-08). → *Yalnız bayinin (ya da firmanın) adı yazılır, telefon "..."; bayi kendi işyeri hattını ayardan girerse yazılır (ayrı küçük iş).*
- "Pano pano" kuralı çelikte duvar panelleriyle mi uygulansın? → *8a'da hayır: çelik duvar paneli bölme kuralı kural kitabında yok (`celik_duvar.md` yalnız dikme aralığını verir); kural yokken çizilen ek uydurma olur (K21). Prefabrikte (pano 1255) geçerli; çelikte pafta kuralları işinde.*
