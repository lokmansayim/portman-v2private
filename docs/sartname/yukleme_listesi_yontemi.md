# Çelik yükleme listesi: yöntem ve taslak (3–4 Ekim 2026)

Son güncelleme: 4 Ekim 2026 16:13. Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Deneme kodu: `deneme/2026-10-03_yukleme/`. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir. Buradaki tablolar ve sayılar hesap çıktılarından üretilir (`belge_uret.py`; tablolar `sonuc/tablolar.md`).

## Kaynaklar

1. **Lokman'ın söyledikleri.** 3 Ekim 13:27'de on bir soruya verdiği cevaplar (aşağıda), 4 Ekim 01:24'teki düzeltmesi (tavan ve çatı panelinin ağırlığı), 4 Ekim 01:42'deki düzeltmesi (baz kaplama; kırma çatıda kaplama adedinin çatı açılımından bulunması), 4 Ekim 15:18'de altı soruya verdiği cevaplar (aşağıda) ve önceki kurallar. Lokman'ın söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerlidir (15:18: en iyi bilgiyi kendisi verecek).
2. **Mühendisin cevapları.** PortatifEv'in inşaat mühendisi Ubeydullah'ın üç tur cevabı: 3 Ekim 14:50 sürümündeki yedi soruya (Lokman 3 Ekim 18:14'te iletti), 19:12 sürümündeki yedi soruya (Lokman 4 Ekim 01:24'te iletti) ve 4 Ekim 02:58 sürümündeki on iki soruya (Lokman 4 Ekim 12:14'te iletti). Üçü de aşağıda. Kurallarda durumu `muhendis`. İkinci turun iki cevabını (baz kaplama; kırma çatıda kaplama adedi) Lokman 01:42'de düzeltti. Üçüncü turun mesajında cevapların kimden olduğu yazmıyor; 11. cevaptaki anlatım mühendisin olduğu için on iki cevap da mühendisin sayıldı.
3. **Gerçek yükleme listeleri.** Lokman'ın bağladığı klasördeki çalışma kitapları. Üçü hesap sayfalarıyla okundu. Üçünde de çatı yöntem B ile (tavan omegası, aşık, saçak sacı) hazırlanmış: PortatifEv bugüne kadar çelikte de bu yöntemi uygulamış. Şimdi baz alınan yöntem A için karşılaştırılacak gerçek liste yok.
   - **90 m²**, beşik çatı, OSB üstü metal kiremit, karkas 80 mm (30 Eylül 2025).
   - **62 m²**, kırma çatı, sandviç panel, dış karkas 140 mm, verandalı (19 Eylül 2025). Ç8201'e en yakın örnek.
   - **105 m²**, beşik + cumba çatı, tek kat panel, dış karkas 140 mm (dosya tarihi 26 Kasım 2025; 11 Kasım tarihli önceki sürümüne de bakıldı).
4. **Excel hesaplama motoru** (`CTKBF V1.1`). Lokman, 13:27: "biz Excel'de hesaplama motoru kullanırken…". Sayfaları: müşteri talebi (girdiler), proje detayları, dış ve iç duvar tonajı, çatı tonajı, çatı kaplama malzemesi, pencere, malzemeler (formüller), notlar. Buradan çelik birim ağırlıkları ile listede elle yazılan kalemlerin formülleri alındı. Fiyatlar alınmadı.
5. **Mühendisin 10 × 10 m çatı metrajı** (aynı klasörde; beşik ve dört omuz, yöntem B). Kuralları sınamak için kullanıldı; fiyatlar alınmadı.

Bayi, müşteri ve öteki personel adları alınmadı. Çalışma kitapları depoda değil; Lokman'ın Mac'inde.

## Lokman'ın cevapları (3 Ekim 13:27) ve uygulanışı

| # | Konu | Cevap (özet) | Uygulama |
|---|---|---|---|
| 1 | Çelik kg | Excel motorundaki gibi: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek. İleride Blender eklentisi (şimdi değil). | Duvar kg = duvar boyu × motorun birim ağırlığı. Dikme, kiriş ve makas motorun ortalamasıyla, "şimdilik" notuyla (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"). Tavan ve çatı paneli 100 m² için verilen ağırlıktan, alana oranla (ağırlıklar Lokman'ın 4 Ekim düzeltmesiyle). |
| 2 | Çatı örtüsü | "Çatı kaplaması" seçenektir: tek kat panel, sandviç panel, OSB + nem bariyeri + kiremit desen sac vb.; ötekiler zamanla verilecek. Hafif çelikte normalde makas arasına tavan paneli, üstüne çatı paneli konur; "ama biz prefabrikte kullandığımız metod olan tavan omegası, aşık, alın sacı ve saçak sacı yöntemini uyguluyoruz". İki varyant var; şimdilik çatı ve tavan panelli yöntem baz. | Çatı yöntemi A; kaplama seçenek. Baz pakette tek kat panel (Lokman, 4 Ekim 01:42); motordaki altı kaplama da hesaplanıyor. |
| 3 | Veranda kolonu ve kirişi | Kaplanıyor. Her projede sırt 80 mm (çelik karkas), genişlik 30 cm. Bu projede verandanın bütün çerçevesi böyle: kirişler yanlarda ve karşıda; altlarında 240 cm, kiriş gibi dikmeler. | Ç8201: dikme 3 × 240 cm, kiriş 12,38 m; kaplama çevreleri 0,76 ve 0,68 m. Çizime işlendi. |
| 4 | Yeşil alçıpan | Doğru: duvarda ıslak hacim; tavanda ıslak hacim ile veranda tavanı. | Hesap değişmedi; kural teyitli. |
| 5 | Köşebent | Kural olarak bina m² ÷ 2,5; 50 ya da 70 olması çok önemli değil. | Yerini mühendisin plandan hesaplayan formülü aldı (18:14): Ç8201'de 59 (m² ÷ 2,5 ile 33'tü; veranda tavanı eklenmeden önce 51). m² ÷ 2,5 kurallarda yedek olarak duruyor. |
| 6 | Dere inişi | Her köşeye bir; 10 metrelik cephenin ortasına bir daha (14 metrede üç tane konmaz); 82 m²'de toplam 6. | Kural kodda. Ç8201: 6; çatı planında işaretli. Mühendis: iniş plana bakarak yerleştirilir (18:14); elle yerleştirilirse o sayı kullanılır. |
| 7 | Bindirme, mahyalar | Saçak, mahya ve alın sacında bindirme hep 30 cm (fire dahil); örnek: "saçak sacı L:2800 ise cephe 10 metre ÷ 2,5". Ters mahya: cumbalı çatıda vadi. Özel mahya: ana bina ile veranda çatısının birleşimi. | Mahya (L 2800) ÷ 2,5 → 11. Yöntem B'de saçak ve alın sacı listelerde L 2500 olduğu için ÷ 2,2 (çıkarım). Dere sayılmadı: 20 cm'de kaldı (soru). |
| 8 | Saçak altı | İki yöntem birlikte kullanılmaz; saçak sacı varsa Boardex kaplanmaz. Ç8201 Boardex kaplamalı, çatı ve tavan panelli. | Baz listede saçak sacı yok; saçaklar için Boardex var. Saçak yüzü de Boardex; saçak omegası yok (mühendis, 18:14). |
| 9 | İç duvarda OSB | İçlerde OSB yoksa mutfak dolabı ve TV ünitesi takılırken mukavemet sağlasın diye gönderilen ürün; "salonun bir odası ile mutfağın 1 odasının tüm yüzeyini hesapla". | Mühendisin cevabıyla (18:14): yalnız dolap ve TV ünitesi gelen duvarlar. Ç8201: 24,5 m² → 9 levha (önce bütün Yaşam Alanı: 42,5 m², 15 levha). Duvar seçimini mühendis doğruladı (4 Ekim). |
| 10 | İç kapı | Boşluk en 90, yükseklik 214; kasa sağda, solda, üstte 5'er cm; altta 5 cm şap ve 2–3 cm parke; kanat 200'e düşer. | Dört iç kapı da 90 × 214 (banyo dahil); kanat 200. Kanat eni 80: listelerdeki "80'lik kanat"tan ve 90 − 2 × 5'ten. |
| 11 | Vida, boya, elektrik, tesisat | Bütün paketlerde var; bayilerle paylaşılan katalog ve fiyat listelerinde de. Bayi kuralı olarak ele alınacak (örnek: bir bayi için çelikte standart ne, bir başkası için prefabrikte standart ne); canlıda bayi numaraları birincil anahtar, liste mesajı atana göre. | Dört grup varsayılan olarak listede; bayi kuralıyla kapatılır. |

## Mühendisin ilk cevapları (Lokman 3 Ekim 18:14'te iletti) ve uygulanışı

Sorular 14:50 sürümündeki yedi soruydu. "Denetim" sütunu, cevabın elimizdeki kaynaklarla karşılaştırmasıdır. Sonradan değişenler "Uygulama" sütununda belirtildi.

| # | Soru | Cevap | Denetim | Uygulama |
|---|---|---|---|---|
| 1 | Et kalınlığı neye göre seçiliyor? | Duvarların kg/m değerleri: 80 × 0,8 iç 13; 80 × 1,2 dış 20,33 ve iç 19,75; 140 × 0,8 dış 18,20 ve iç 12,06; 140 × 1,2 dış 29,04. "140x0,8 duvarı 80x1,2 duvarına göre daha hafif olduğunu görebiliriz." | Değerler motorun duvar tonajı sayfasındakilerle aynı. Seçim ölçütü cevapta yok. 12,06 tek bir projenin 80 × 0,8 iç duvarı; 13,00 iki projenin ortalaması. Motorun verisinde 140 × 0,8 dış duvar yalnız iki katlı iki projenin üst katında; tek katlı 140'lık örnekte (55 m²) dış duvar 1,2 mm. | Birim ağırlıklar değişmedi; iç duvar 80 × 0,8 için 13,00. Seçim ölçütü ikinci cevaplarla geldi (aşağıda): tek katta ve zemin katta 1,2 mm. |
| 2 | Tavan ve çatı panelinin ölçüsü, adedi, kg'ı? Saçak omegası gerekiyor mu? Saçak yüzü Boardex mi? | Motor çatıları dört grupta (beşik, beşik + cumba, beşik + 2 cumba, dört omuz) ortalama ağırlıkla hesaplıyor; çatıdaki Boardex kaplaması motorda henüz hesaplanmıyor. "10 m x 10 m (100 m2) bir binada tavan paneli koyduğumuzu düşünürsek (8 adet) tavan paneli ağırlığı 429,83 kg, çatı paneli (12 parça) koyduğumuzda 561,6 kg geliyor. Saçak omegası gerekmiyor. Saçak yüzü de boardex ile kaplanıyor." | 429,83 ve 561,6 okunan çalışma kitaplarında bulunamadı; mühendisin beyanı olarak kayıtlı. Hangi çatı tipi, saçak ve eğim için olduğu yazılmadı. Motorda "saçaklar için Boardex" satırı gerçekten 0. | kg ve adet çatının örttüğü oturum alanına oranlandı: o gün Ç8201'de tavan paneli 353 kg, çatı paneli 461 kg; çelik toplamı 1902 → 2716 kg. Ağırlıkları Lokman 4 Ekim'de düzeltti (aşağıda). Saçak omegası satırı kalktı. Saçak yüzü için Boardex teyitli. |
| 3 | Baz pakette hangi çatı kaplaması var? | Motordaki kaplamalar: OSB + membran + shingle; OSB + nem bariyeri + trapez sac; trapez sac; tek kat panel; sandviç panel; OSB + membran + metal kiremit. | Motorun seçenek listesi aynı. Baz paket cevapta yok. Motorun trapez sac ve metal kiremit adedi formülü hatalı görünüyor (aşağıda "Excel motoruyla ilgili gözlemler"). | Altı seçenek hesaplanıyor. Lokman'ın "OSB + nem bariyeri + kiremit desen sac"ı motorun "OSB + membran + metal kiremit"iyle eşlendi (motor o seçenekte nem bariyeri hesaplıyor, membran hesaplamıyor). Baz paket: mühendis ikinci cevaplarda sandviç panel yazdı; Lokman tek kat panel diye düzeltti (4 Ekim 01:42). |
| 4 | OSB takviyesi bütün oda mı, yalnız o duvarlar mı? | "Bütün oda değil sadece dolap ve TV ünitesi gelen duvar metrajı alınır." | Gerçek listelerdeki alanlar (35 ve 39 m²) bütün odadan (72 ve 112 m²) küçük: cevapla aynı yönde. | Modelin tanımına dolap ve TV duvarları yazılır. Ç8201'de katalog görselinden üç duvar: banyo ile mutfak arası duvar 2,49 m (mutfak dolabı); üst dış duvar 2,96 m (mutfak dolabı ve eviye); hol ile yaşam alanı arası duvar 4,80 m (TV ünitesi). Net 24,5 m² → 9 levha. Duvar seçimini mühendis ikinci cevaplarda doğruladı. |
| 5 | Köşebent: m² ÷ 2,5 gerçek listelerin yarısını veriyor. | "Köşebent hesabı bina içerisinde bulunan bütün odaların tavan çevresi uzunluğu ile bütün oda iç köşe uzunlukları (standart kat yüksekliğimiz 2,7 metre alınır) toplamının 2,5 metreye bölünmesiyle bulunur." | Motordaki formül aynı yapıda ama plansız: (uzun × 6 + kısa × 6 + 9 × 4 × 2,7) ÷ 2,5. Üç gerçek listede iç köşe sayısı bilinmiyor (planları yok); aşağıdaki tablo. | Ç8201 (planından): (69,72 + veranda tavanı 19,88 + 21 × 2,7) ÷ 2,5 → 59. Yalnız iç köşeler sayılır. Veranda tavanının çevresi üçüncü cevaplarla eklendi (önce 51). |
| 6 | İniş sayısı iki listede kuraldan bir fazla. | "Dere inişi plana bakarak yerleştirilmesi doğru olur. Normalde düz bir saçakta ortalama 5 metrede bir dere inişi yazılır." | Mühendisin 10 × 10 m metrajında dört omuz çatıda 8, beşik çatıda 6 iniş var: Lokman'ın kuralı ikisini de veriyor. Motorun formülü farklı (dere adedi ÷ 5 + 6). | Kural değişmedi (Ç8201: 6). Tanımda iniş yerleri elle verilirse (`cati.inis_noktalari`) o sayı kullanılır. Listelerdeki 7'ler plana göre yerleşimle açıklanıyor. |
| 7 | Elektrik sayıları paftadan mı, oda başına kuraldan mı? | Oda başına kural; "%75 lik bir doğruluk payı olacağı düşünülerek" (aşağıda). | 105 m² listenin pafta sayımıyla sınandı (aşağıda): kural 41, sayım 48 parça. | Pafta sayımı varsa o; yoksa kural. Ç8201: duy 6, glop 3, tekli anahtar 5, çiftli anahtar 2, tekli priz 16, çiftli priz 2, uydu prizi 1, sigorta 9. Yaşam Alanı'nda salon ve mutfak kuralları birlikte uygulandı (mühendis ikinci cevaplarda doğruladı). |

### Elektrik kuralı (mühendis)

| Oda | Duy | Glop | Tekli anahtar | Çiftli anahtar | Tekli priz | Çiftli priz | Uydu prizi |
|---|---|---|---|---|---|---|---|
| Yatak odası | 1 | | 1 | | 3 | | |
| Banyo | | 1 | 1 | | 2 | | |
| Salon | 2 | | | 1 | 3 | 1 | 1 |
| Mutfak | 1 | | 1 | | 5 | 1 | |
| Hol | 1 | | 1 | | | | |
| Veranda | | 2 | | 1 | | | |

- Her duy ve glop için bir ampul.
- Bina başına (cevapta holün altında): 12'li sigorta kutusu 1, sigorta 9, besleme kablosu 5 m, zil 1, kaçak akım rölesi 1; salonda 25 m uydu kablosu.
- Buat kasa = anahtar + priz + oda sayısı.
- 3 × 2,5 kablo = sigorta adedi × sigortadan evin en uzak mesafesi + (tekli priz + 2 × çiftli priz) × 2. 2 × 1,5 kablo = sigorta adedi × en uzak mesafe + (tekli anahtar + 2 × çiftli anahtar) × 2.
- Okuma: cevaptaki "anahtar" tekli anahtar, "priz" tekli priz sayıldı. "En uzak mesafe" motordaki gibi kapalı kısmın köşegeni alındı (Ç8201: 11,34 m); motor 3 × 2,5 kabloda uydu prizini de sayıyor, hesap öyle yapıldı (fark 2 m). Buat için oda sayısı planın mahal sayısı alındı (Ç8201: 5). Mühendis üçüncü cevaplarda ikisini de teyit etti: "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli."

Ç8201'de oda oda:

| Mahal | Kural | Tijli duy | Yuvarlak glop | Tekli anahtar | Çiftli anahtar | Tekli priz | Çiftli priz | Uydu prizi |
|---|---|---|---|---|---|---|---|---|
| Yatak Odası 1 | yatak odası | 1 |  | 1 |  | 3 |  |  |
| Yatak Odası 2 | yatak odası | 1 |  | 1 |  | 3 |  |  |
| Banyo | banyo |  | 1 | 1 |  | 2 |  |  |
| Hol | hol | 1 |  | 1 |  |  |  |  |
| Yaşam Alanı | salon + mutfak | 3 |  | 1 | 1 | 8 | 2 | 1 |
| Veranda | veranda |  | 2 |  | 1 |  |  |  |
| Toplam | | 6 | 3 | 5 | 2 | 16 | 2 | 1 |

Kuralın sınaması: 105 m² gerçek listede pafta sayımı var. O listenin odalarına kural uygulanınca ("oda" yatak odası sayıldı; veranda bilgisi yok):

| Kalem | Kural | Pafta sayımı (liste) |
|---|---|---|
| Tijli duy | 7 | 10 |
| Yuvarlak glop | 2 | 4 |
| Tekli anahtar | 7 | 4 |
| Çiftli anahtar | 1 | 5 |
| Tekli priz | 21 | 20 |
| Çiftli priz | 2 | 4 |
| Uydu prizi | 1 | 1 |
| Toplam | 41 | 48 |
| W otomat (sigorta) | 9 | 9 |

Toplamda kural sayımın %85'ini veriyor; kalem kalem farklar büyük (çiftli anahtar 1 / 5, glop 2 / 4). Bu, mühendisin söylediği %75'lik doğruluk payıyla uyumlu. Tek liste; kanıt sayılmaz.

### Köşebent kuralının gerçek listelerle karşılaştırması

| Liste | Oda çevreleri (m) | Oda sayısı | Hesap (oda başına 4 iç köşe) | Listede | Listedeki adedin denk geldiği iç köşe |
|---|---|---|---|---|---|
| 90 m² | 87,84 | 5 | 57 | 70 | 32,3 |
| 62 m² | 51,83 | 4 | 39 | 50 | 27,1 |
| 105 m² | 109,81 | 6 | 70 | 85 | 38,0 |

Ç8201 (planından): oda çevreleri 69,72 m, veranda tavanının çevresi 19,88 m, iç köşe 21; (69,72 + 19,88 + 21 × 2,7) ÷ 2,5 = 58,5 → 59 adet.

Listelerdeki adetler, her odada ortalama 6–7 iç köşe varsa formülle çıkar. Salon, mutfak ve holün tek mahal olduğu planlarda bu olabilir; planlar elde olmadığı için sınanamadı. Ç8201'in planı sade: beş mahal, 21 iç köşe. Veranda tavanının çevresi (üçüncü cevaplar) örneklerde bilinmediği için bu tabloya eklenmedi; verandalı projede eklenince fark azalır.

## Lokman'ın düzeltmesi ve mühendisin ikinci cevapları (4 Ekim 01:24) ve uygulanışı

**Düzeltme (Lokman).** 100 m² için "Tavan paneli ağırlık: 354,84 kg · Çatı paneli ağırlık: 440,32 kg"; "yine 82 m² ye oranlama yapabilirsin". Önceki değerler 429,83 ve 561,6 kg'dı. Ç8201'de (oturum 82,05 m²) tavan paneli 353 → 291 kg, çatı paneli 461 → 361 kg; çelik toplamı 2716 → 2555 kg. Oranlama böylece Lokman'ın onayıyla. Adetler (100 m²'de 8 ve 12) mühendisin ilk cevabından; düzeltmede adet verilmedi.

Sorular 19:12 sürümündeki yedi soruydu. 1. ve 6. cevabı Lokman 01:42'de düzeltti; öteki beşi geçerli.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Baz pakette altı seçenekten hangi çatı kaplaması var? | "Baz paket sandviç panel olarak al." | **Lokman düzeltti (01:42):** baz kaplama tek kat panel. Sandviç panel öteki dört kaplamayla birlikte seçenek olarak hesaplanıyor. |
| 2 | Tek katta dış 140'lık duvarın et kalınlığı 0,8 mi, 1,2 mi? | Tek katlı binada zemin kattaki çelik 140x45x12 ya da 80x45x12. İki katlı binada zemin kat yine böyle; 1. kat 140x45x0,8 ya da 80x45x0,8. İki katlıda "1. Katta büyük pencereler varsa mesela 200 cm ve daha geniş pencere varsa ozaman o duvarı 1,2 mm et kalınlığında alırız. Genelde 1. Katta 1 veya 2 adet duvar bu şekilde 1,2 mm et kalınlığı olacak şekilde tasarlanıyor." | Okuma: cevaptaki "12 mm" ve "8 mm", 1,2 ve 0,8 mm'dir. Tek katta ve zemin katta dış ve iç duvarlar 1,2 mm; üst katta 0,8 mm. Dış 140 seçeneği: dış 140 × 1,2 ve iç 80 × 1,2 → çelik 2828 kg, baz paketten 273 kg ağır (3 Ekim'de 0,8 mm varsayılmış, daha hafif çıkmıştı). Üst katta geniş pencereli duvar kuralı kayıtlı; çift kat modeli gelince uygulanacak. 2025 tarihli iki tek katlı listede dış 140'lık duvarların çoğu 0,8 mm'di: kuralla uyuşmuyor. Mühendis üçüncü cevaplarda kuralı yineledi: tek katta 1,2 mm. |
| 3 | OSB takviyesi için seçilen üç duvar doğru mu? | "Evet doğru yeri almışsın. Ancak bunun yeri en doğru şekilde genel mimari planda mutfak tezgahı ve TV ünitesi yeri gösterilirse o kısımlar alınarak bulunabilir." | Seçim teyitli; satırdaki "teyit bekliyor" notu kalktı. Kural: yer, mimari plandaki tezgâh ve TV ünitesi yerinden alınır. "O kısımlar" sözü duvarın yalnız o bölümü diye de okunabiliyordu; üçüncü cevaplarla kapandı: "Duvarın tamamını al." |
| 4 | Yaşam Alanı'nda salon ve mutfak kuralları birlikte mi uygulanır? | "Evet doğru ikisini de uygulamamız gerekiyor. Çünkü mutfak eşyaları ayrı, salon eşyaları ayrı." | Teyitli; hesap değişmedi. |
| 5 | Makas ve kiriş ölçüsü gelene kadar çatı çeliği motorun ortalamasıyla; panel adedi alana oranlandı. | "Tamamdır." | Çatı çeliği motorun ortalamasıyla kalıyor (makas ölçüsü verilince değişecek; üçüncü cevaplar: "şimdilik Excel hesaplama motoruna uy"). Panel adedi alana oranlanıyor. |
| 6 | Kırma çatıda kaplama adedi yerleşimle mi bulunsun? | "Kırma çatıda çatı kaplama malzemesi hesabı sağlıklı olarak autocad üzerinden hesaplanarak yapılması daha sağlıklı. Ancak yüzeysel olarak çatı yüzey alanı m2 belirtilerek (%10 luk pay alınabilir) bu m2 olacak şekilde çatı kaplama malzemesi sipariş edilmeli şeklinde not edilebilir." | **Lokman düzeltti (01:42):** adet AutoCAD'e bırakılmaz; çatı açılımından ve dizilimden çıkar (aşağıda). %10 pay ve "sipariş bu m² olacak şekilde" notu listeden kalktı; pay kurallarda kayıt olarak duruyor. |
| 7 | Çatı müdahale kapağı ve mahya bandı listeye girsin mi? | "Çatı müdahale kapağı müşterinin talebine göre ekleniyor. Herhangi bir detay belirtilmemişse yani standart bir pakette çatı müdahale kapağı göndermiyoruz. Mahya bandını ekle." | Mahya bandı eklendi. O gün mahya uzunluğundan hesaplandı (Ç8201'de 3 rulo); üçüncü cevaplardaki formülle 4 rulo. Çatı müdahale kapağı standart listede yok; müşteri isterse eklenir (`--mudahale-kapagi`; kat adedi kadar). |

## Lokman'ın ikinci düzeltmesi (4 Ekim 01:42): baz kaplama ve çatı açılımı

Lokman: "mühendis 2 cevapta hata yapmış onları düzeltmem gerekiyor".

1. **Baz kaplama.** "çatıda baz model Tek Kat panel olarak geçiyor". Uygulama: baz paketin çatı kaplaması tek kat panel; Ç8201'in tanımı ve listesi buna göre. Sandviç panel seçenek. O gün 87 cm kapatan panelle hesaplandı; güncel ürün 100 cm kapatıyor (Lokman, 15:18).
2. **Kırma çatıda kaplama adedi.** "biz AutoCAD bulaşmak istemiyoruz"; "sen eğime göre 82 m² olduğu gibi çatıyı çizip sonra çatıyı açman lazım zarfı açar gibi yüzeye dizilimini bulmak için". "çatı formunun çapraz kesimleri diğer tarafa kullanabilirsin": sol taraftaki üçgende kullanılan panel sağ tarafa aynı açıyla; ön taraftaki yamuktan çıkan açılı kesilmiş parçalar arka taraftaki aynı biçimdeki açılı yere.

Uygulama (`deneme/2026-10-03_yukleme/cati_acilim.py`). Taşma mühendisin üçüncü cevaplarıyla (12:14) eklendi; dizilimin başladığı yer, kesim payı, yedek ve kapatma genişlikleri Lokman'ın 15:18 cevaplarıyla kesinleşti (aşağıdaki bölümler):

- **Açılım.** Çatının dört yüzü gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ). Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Ç8201'de 426,5 cm; saçaklar 1154 ve 810 cm, mahya 344 cm. Kırma çizgisi açılımda dört yüzde de aynı açıdadır.
- **Dizilim.** Her yüz, saçağa dik, kaplamanın kapattığı genişlikte şeritlere bölünür. Dizilim her yüzde, dışarıdan bakışla sol köşeden başlar (Lokman, 4 Ekim 15:18: "her köşeden başlayacak gibi hesapla"); son şerit dar kalabilir. Mahyanın altındaki şeritler tam boydur; kırmaya gelen şeritler çapraz kesilir.
- **Kapatma genişliği.** Ürüne göre değişir (Lokman, 15:18). Güncel: tek kat panel 100, sandviç panel 100 (80 cm kapatanı da var), kiremit desen sac 100, trapez sac 80 cm. 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Girdide `cati.kapatma_m` yazıyorsa o kullanılır.
- **Taşma** (mühendis, 4 Ekim 12:14). Kaplama saçaktan 5 cm dışarı uzatılır. Panel boyu = eğimli boy + 5 cm, mm'ye yukarı: Ç8201'de L 4315. Açılımda her parçanın boyu 5 cm artar. Excel motorundaki sac boyu da aynı: eğimli boy + 0,05. Panel boyu gerçek listeden geliyorsa ve kısaysa taşma panelin yettiği kadar alınır (62 m² örnekte 3,8 cm).
- **Artan parça.** Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır. Alt parça olduğu gibi kullanılır. Üst parça, düz ucu saçağa gelecek biçimde karşı yüze konur; orada aynı açılı yere oturur (ön yüzün sol kırması ↔ arka yüzün sol kırması, dışarıdan bakışla; planda çapraz köşeler). Parça ters yüz edilmez. Kiremit desen sacda artan parça kullanılmaz: desen ters gelir (mühendis, 4 Ekim 12:14).
- **Eşleme.** En uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır. İki parçanın birlikte istediği boy: uzun kenarlarının toplamı − bir şeritlik boy farkı + kesim payı.
- **Kesim payı** (Lokman onayladı, 4 Ekim 15:18). 5 mm: çapraz kesimde iki parçanın arasına ve aynı panelden çıkan dikdörtgenlerin arasına.
- **Yedek ve bindirme.** Yedek panel eklenmez: kesim planı montajcıya verilir (Lokman, 15:18). Boy bindirmesi yok (panel tek boyda).
- **Öteki başlangıçlar.** Bilgi için beş başlangıç daha denenir: uzun yüzlerde sol köşeden, kısa yüzlerde ortadan · uzun yüzlerde ortadan, kısa yüzlerde sol köşeden · her yüzde ortadan · her yüzde sağ köşeden · karşılıklı yüzlerde planda aynı uçtan. En az paneli veren dizilim tabloda ayrı sütunda. "Ortadan": yüzün ortasına bir ek yeri gelir, şeritler iki yana eşit dağılır.

Ç8201, tek kat panel: **27 adet L 4315** (10 tam boy + 17 kesilen: 14 kesimden ikişer parça çıkıyor, biri bir yüze, öteki karşı yüze; 4 kesimde artan parça kullanılmıyor). Çizimler: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_acilim.png` (açılım; her parçada panel numarası) ve `C8201_cati_kesim.png` (her panelin kesimi); döküm `C8201_cati_acilim.json`; kesim ölçüleri `C8201_cati_kesim_olculeri.md`.

| Çatı | Kaplama | Kapatır | Adet (her yüzde sol köşeden) | En az paneli veren dizilimle | Altı başlangıçla | Artan parça kullanılmazsa | Alan olarak en az | Kesim payı sıfır / 1 cm | Taşma |
|---|---|---|---|---|---|---|---|---|---|
| Ç8201 (L 4315) | Tek kat panel (baz paket) | 100 cm | 27 (10 tam boy + 17 kesilen) | 26 | 26–27 | 30 | 24 | 25 / 27 | 5,0 cm |
| Ç8201 (L 4315) | Sandviç panel | 100 cm | 27 (10 tam boy + 17 kesilen) | 26 | 26–27 | 30 | 24 | 25 / 27 | 5,0 cm |
| Ç8201 (L 4315) | Trapez sac | 80 cm | 32 (12 tam boy + 20 kesilen) | 32 | 32 | 36 | 30 | 30 / 32 | 5,0 cm |
| Ç8201 (L 4315) | Kiremit desen sac | 100 cm | 30 (10 tam boy + 20 kesilen) | 28 | 28–30 | 30 (listeye giren) | 24 | 28 / 30 | 5,0 cm |
| Ç8201 (L 4315) | Sandviç panel, 80 cm kapatan ürün | 80 cm | 32 (12 tam boy + 20 kesilen) | 32 | 32 | 36 | 30 | 30 / 32 | 5,0 cm |
| Ç8201 (L 4315) | Tek kat panel, 87 cm kapatan ürün (2025 listeleri) | 87 cm | 29 (12 tam boy + 17 kesilen) | 28 | 28–29 | 32 | 27 | 29 / 29 | 5,0 cm |
| Ç8201 (L 4315) | Kiremit desen sac, 110 cm kapatan ürün (2025 listeleri) | 110 cm | 26 (10 tam boy + 16 kesilen) | 26 | 26 | 26 (listeye giren) | 22 | 26 / 26 | 5,0 cm |
| 62 m² gerçek liste (L 3200; listede 27) | Sandviç panel | 100 cm | 28 (16 tam boy + 12 kesilen) | 28 | 28 | 32 | 25 | 28 / 28 | 3,8 cm |
| Mühendisin 10 × 10 m dört omuz metrajı (L 5900; metrajda 36) | Trapez sac | 80 cm | 28 (4 tam boy + 24 kesilen) | 28 | 28 | 32 | 26 | 28 / 28 | 5,0 cm |

Okuma:

- **Sağlama.** Aynı kural, bu koda bakmadan ayrıca hesaplandı (bağımsız denetim, 4 Ekim; 15:18 cevaplarından sonra yeniden): 100 cm kapatma, her yüzde sol köşeden ve 5 mm kesim payıyla artan parça kullanılarak 27, kullanılmadan 30; 80 cm kapatmada 32. Panel 4,320 m olursa 25, 28 ve 30; adedin düştüğü en kısa boy 4,318 m. Hepsi aynı çıktı ve bu dizilim için en az oldukları gösterildi. Önceki turda 90 adet (beş örnek × altı başlangıç × üç kesim payı) aynı çıkmıştı. Her paneldeki parçaların panele sığdığı, üst üste binmediği ve yüzdeki yerine tam oturduğu çokgenlerle sınanıyor (`cati_acilim_saglama.py`; rastgele 120 kırma çatıda, 1440 dizilimde sorun çıkmadı; kural bilerek bozulunca sınama yakalıyor). Çizim, ölçü tablosu ve sınama aynı yerleşimi kullanıyor.
- **Tek kat panel (baz paket).** 27 adet (10 tam boy + 17 kesilen); en az paneli veren dizilimle 26 olurdu (altı başlangıçla 26–27); kesim payı sıfır alınırsa 25, 1 cm alınırsa 27; panel L 4318 ve daha uzun olursa 25.
- **Sandviç panel.** 27 adet (10 tam boy + 17 kesilen); en az paneli veren dizilimle 26 olurdu (altı başlangıçla 26–27); kesim payı sıfır alınırsa 25, 1 cm alınırsa 27; panel L 4318 ve daha uzun olursa 25.
- **Trapez sac.** 32 adet (12 tam boy + 20 kesilen); altı başlangıcın hepsinde aynı; kesim payı sıfır alınırsa 30, 1 cm alınırsa 32; panel L 4318 ve daha uzun olursa 30.
- **Kiremit desen sac.** 30 adet (10 tam boy + 20 kesilen); en az paneli veren dizilimle 28 olurdu (altı başlangıçla 28–30); kesim payı sıfır alınırsa 28, 1 cm alınırsa 30; panel L 4318 ve daha uzun olursa 28; artan parça kullanılmıyor (desen ters gelir: mühendis, 4 Ekim 12:14).
- **Panel boyu (öneri; karar bekliyor).** Aşağıda, "Panel boyu" başlığında: panel L 4318 ve daha uzun sipariş edilirse tek kat panel 27 yerine 25 yetiyor.
- **Sürümler.** 02:58 (taşma ve kesim payı yok; L 4300; tek kat panel 87, kiremit desen sac 110 cm): tek kat panel 28, sandviç panel 24, trapez sac 30, kiremit desen sac 26. 13:22 (taşma 5 cm, kesim payı 5 mm, en az paneli veren başlangıç): 28, 26, 32, 26. Şimdi (her yüzde sol köşeden; tek kat panel ve kiremit desen sac 100 cm): 27, 27, 32, 30.
- **Önceki kural** (yüzey + %10, aynı panel boyu ve güncel kapatma genişlikleriyle): tek kat panelde 26, sandviç panelde 26, trapez sacda 32, kiremit desen sacda 26 verir.
- **62 m² gerçek liste** (kırma çatı, sandviç panel L 3200): listede 27 adet (ayrıca 2 adet L 1000); dizilim 28 veriyor (02:58 sürümünde, taşmasız, 26'ydı). Listedeki 27 uzun ve 2 kısa panel alan olarak 27,6 panel eder. Kısa panellerin köşe parçaları için gönderilip gönderilmediği bilinmiyor.
- **Mühendisin 10 × 10 m dört omuz metrajı** (trapez sac L 5900): metrajda 36 adet var; dizilim tablonun son satırındaki adedi veriyor. Çatı planı saçak dahil 10,6 × 10,6 m ve eğim %33 alındı; yüzey metrajdaki 118 m²'yi tutuyor.
- **Dar yerler** (bağımsız denetimin notları). Tam boy parçada pay yok: panel boyu tam eğimli boy + taşma. İki saçağın taşmalarının kesiştiği köşe (yaklaşık 5 × 5 cm) örtülmez: parçalar uzuyor, genişlemiyor. Kesim payı panel boyu yönünde ölçülüyor: çapraz kesim yaklaşık 46° olduğu için boyda 5 mm, 3,4 mm kalınlığında bir kesime denk gelir. Boyuna kesimin (dar son şerit) payı hesapta yok.
- **Sınır.** Yalnız dikdörtgen planlı, dört yanı eşit eğimli kırma çatı. Cumbalı çatıda (ters mahya) dizilim henüz yok.

## Mühendisin üçüncü cevapları (Lokman 4 Ekim 12:14'te iletti) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 02:58 sürümündeki on iki soruydu ("Sizden beklenenler"). Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Makas ve kiriş ölçüsü | "şimdilik Excel hesaplama motoruna uy" | Çatı çeliği, veranda dikmeleri ve kirişleri motorun ortalamasıyla kalıyor: 706, 46 ve 81 kg. Hesap değişmedi; makas ölçüsü verilirse değişir. |
| 2 | Tek katta et kalınlığı: kural mı, 2025 listelerindeki uygulama mı? | "Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz." | Kural geçerli; hesap değişmedi (baz 2555 kg, dış 140 2828 kg). 2025 listelerindeki 0,8 mm eski uygulama olarak kayıtlı. |
| 3 | Çatı açılımı: başlangıç köşesi, kesim payı, yedek, kiremit desen sac | "5 cm çatı yüzeyinin dışında kalacak şekilde uzatıyoruz çatı kaplamalarını. Kiremit desen sacda artan parça karşı yüzde desen ters geldiğinden kullanılmaz." | Taşma 5 cm eklendi: panel boyu L 4300 → L 4315; tek kat panel o gün yine 28 adetti (87 cm kapatan panel, en az paneli veren başlangıç). Sandviç panel 24 → 26, trapez sac 30 → 32. Kiremit desen sacda artan parçanın kullanılmaması teyitli (26 adet; 110 cm kapatan sacla). Başlangıç köşesi, kesim payı ve yedek cevaplanmadı; Lokman 15:18'de cevapladı (aşağıda). |
| 4 | Tavan ve çatı panelinin adedi; hangi çatı tipi için? | "Genelde dörtomuz çatı tipinde tavan paneli ve çatı panelini kullanıyoruz. 100m2 için bu adetler üzerinden ilerleyebilrsin." | 100 m²'de 8 ve 12 adet geçerli; alana oranla Ç8201'de 7 ve 10. Hesap değişmedi. |
| 5 | OSB takviyesi: duvarın tamamı mı, yalnız tezgâhın ve TV ünitesinin arkası mı? Klima duvarı? | "Duvarın tamamını al." | Hesap değişmedi (9 levha). Klima duvarı cevaplanmadı; Lokman 15:18'de cevapladı (aşağıda). |
| 6 | Köşebent: çıkıntı yapan köşeler ve veranda tavanı sayılır mı? | "Odaya doğru çıkıntı yapan köşeler sayılmıyor. Veranda tavan çevresi sayılır." | Veranda tavanının çevresi (19,88 m; brüt ölçüyle) eklendi: 51 → 59. Çıkıntı yapan 1 köşe sayılmıyor. Verandada köşe boyu eklenmedi. Buna bağlı trapez vida (5,5 × 25) 1000 → 1250. |
| 7 | Elektrik: buat için hangi odalar? Yatak odası ve banyodaki prizler tekli mi? | "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli." | İkisi de zaten öyleydi: oda sayısı 5, buat kasa 31. Hesap değişmedi. |
| 8 | Mahya bandı: mahya uzunluğundan mı, parça adedinden mi? | "Mahya bandı şu şekilde hesaplanır: “(Mahya Adedi * 2,8 (metre) + Ters Mahya Adedi * 2,8 (metre) + Damlalık adedi * 2,5 (metre))/10” şeklinde bulunur." | (11 × 2,8 + 0 + 0) ÷ 10 → 3 yerine 4 rulo. Damlalık okunan listelerde yok; sıfır alındı. Lokman 15:18'de damlalığı listeden tamamen çıkardı. Trapez sac seçeneklerinde motordaki gibi trapez sac mahyası × 0,8 m toplanır. |
| 9 | Dış kapı: 100 mü, 95 mi? | "Dış kapı boşluğu 95x210, iç oda kapı boşluğu 90x214 alınır." | Tanımda dış kapı boşluğu 100 → 95 cm (ekseni yerinde kaldı); plan ve paftalar yeniden çizildi. Liste hesabı zaten 95 × 210 ile yapılıyordu. |
| 10 | Boardex ve OSB kalınlığı; Boardex zayiatı | "Boardex 12.5 mm. OSB 11 mm. Boardex zayiatı %8." | Satırların boyutu 12,5 × 1200 × 2400 ve 11 × 1220 × 2440 oldu. Boardex zayiatı %15 → %8: dış cephe Boardex 33 → 31; saçak altı ve saçak yüzü aynı (5 ve 3). 2025 listelerindeki adetler %15'e uyuyor (aşağıda). |
| 11 | Excel motorundaki trapez sac formülü | Formülü yapıştırdı ve açıkladı: "Eğer K24 hücresi Trapez saç ise yüzey alanını ve trapez saç uzunluğunu hesaplayıp trapez saç uzunluğuyla trapez saç genişliği olan 0,8 metre ile çarpıyor." Yeniden kontrol edilmesini istedi: "Hangi hücreden neyi çekiyorum formül nasıl işliyor". | Formül yeniden okundu (aşağıda). Bulgu aynı: 0,8 paydanın parantezinin dışında. |
| 12 | Bayi standartları | "Şimdilik standartlarımız tam oturmadı. Tek tük bayilerin standartları var ancak bunu ileriki zamanlarda daha net söyleyebiliriz." | Bütün gruplar listede kalıyor; bayi kuralı örnek dosyasıyla duruyor. |

### Excel motorundaki çatı kaplaması formülü: hangi hücre ne, formül nasıl işliyor (11. cevap üzerine)

Motorun (`CTKBF V1.1`) MALZEMELER sayfası 4 Ekim'de yeniden okundu. Mühendisin yapıştırdığı formül 61. satırdaki (trapez sac) formüldür; aynı uzun ifade 58, 59, 61, 64, 67 ve 72. satırlarda da var. Her satırın başındaki EĞER, o satırın kaplaması seçili değilse 0 verir.

| Hücre | Ne |
|---|---|
| K10 | Bina dış uzun kenar (m) |
| K11 | Bina dış kısa kenar (m) |
| K13, K14 | Sundurma dış uzun ve kısa kenar |
| K17 | Oturum dışı veranda dış kısa kenar |
| K23 | Çatı tipi |
| K24 | Çatı kaplama |

Hepsi MUSTERI TALEP sayfasının C sütunundan gelir.

Formülün parçaları:

- **Çatı yüzeyi** = (K11 + 0,6) × √(1 + 0,33²) × (K10 + K17) + K13 × K14. Kısa kenara iki saçak (0,6 m) eklenir, %33 eğimle eğimli genişliğe çevrilir, uzun kenarla (veranda dahil) çarpılır; sundurma düz alanıyla eklenir.
- **Sac boyu** = ((K11 + 0,6) ÷ 2) × √(1 + 0,33²) + 0,05: saçaktan mahyaya eğimli boy + 5 cm taşma. B sütunu bunu mm olarak gösterir.
- **Adet** = yüzey ÷ sac boyu × kaplama katsayısı × çatı katsayısı, yukarı yuvarlanır. Kaplama katsayısı: trapez sac 0,8 · tek kat ve sandviç panel 1 · metal kiremit 1,05. Çatı katsayısı: beşik 1 · beşik + cumba 1,14 · beşik + 2 cumba 1,27 · dört omuz 1,06.

Bulgular:

1. **Parantez (işlem sırası).** Formülde `yüzey / (sac boyu) * 0,8` yazıyor. Excel bölmeyi ve çarpmayı soldan sağa yapar: sonuç (yüzey ÷ sac boyu) × 0,8'dir. Mühendisin anlattığı hesap (sac boyu × 0,8 = bir sacın kapattığı alan; yüzey ÷ o alan) için 0,8'in paydanın parantezi içinde olması gerekir: `yüzey / ((sac boyu) * 0,8)`. Şimdiki haliyle trapez sacda adet olması gerekenin 0,64 katı çıkar (0,8 × 0,8). Metal kiremitte 1,05 de aynı yerde: adet %10 fazla çıkar. Tek kat ve sandviç panelde katsayı 1 olduğu için fark yok.
2. **Uzun kenarda saçak yok.** Yüzeyde kısa kenara 0,6 eklenmiş, uzun kenara (K10 + K17) eklenmemiş. Aynı sayfadaki çatı izolasyonu satırı (84) uzun kenara da 0,6 ekliyor. 10 × 10 m binada formülün yüzeyi 111,6 m²; mühendisin kendi metrajında 118 m².
3. **Kapatma genişlikleri.** Motorda tek kat panel "100 cm kapatır", metal kiremit "105 cm kapatır" yazıyor. Kapatma ürüne göre değişiyor (Lokman, 4 Ekim 15:18): güncel ürünlerde tek kat panel, kiremit desen sac ve sandviç panel 100 cm (sandviç panelin 80 cm kapatanı da var); 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Güncel ürünle motorun tek kat panel katsayısı doğru; metal kiremit katsayısının 1,05 yerine 1 olması gerekir.
4. **Sac boyu hücresi (B61).** Yalnız "Trapez Saç" seçiliyken hesaplıyor; "OSB+Nem Bariyeri+Trapez Saç" seçiliyken 0 gösteriyor. Trapez vida (5,5 × 60) formülü (129. satır) sac boyunu bu hücreden aldığı için o seçenekte sacın vidası hesaba girmez.
5. **Sundurma.** Bu formülde sundurma alanı eğimle çarpılmıyor (K13 × K14); OSB ve nem bariyeri satırlarında (79, 81) çarpılıyor.

Örnekler (formül yazıldığı gibi → parantez düzeltilince):

| Örnek | Yüzey ÷ sac boyu | Trapez sac | Metal kiremit | Not |
|---|---|---|---|---|
| Motorun şablonundaki kayıtlı örnek (9,74 × 7,44; veranda 2,12; dört omuz) | 100,41 ÷ 4,283 = 23,44 | 20 → 32 | 27 → 24 | Şablonda metal kiremit seçili; hücrede kayıtlı değer 27 |
| Mühendisin 10 × 10 m beşik çatısı | 111,62 ÷ 5,631 = 19,82 | 16 → 25 | 21 → 19 | Metrajda 28 trapez sac var (her saçakta 10,6 ÷ 0,8 → 14). Düzeltilmiş formül 25 veriyor; kalan fark uzun kenara eklenmeyen saçaktan ve her saçağın ayrı yuvarlanmasından |
| Ç8201 (K10 8,50; K11 7,50; K17 2,44; dört omuz) | 93,31 ÷ 4,315 = 21,63 | 19 → 29 | 25 → 22 | Çatı açılımı trapez sacda 32, kiremit desen sacda 30 veriyor (artan parça kullanılmadan). Motor tek kat panelde 23 verir; açılım 27. Kiremit desen sac 100 cm kapatırken motorun doğru formülü 23 verir |

Motorun sac boyu Ç8201'de 4315 mm: listedeki L 4315 ile aynı. Yükleme listesi kaplama adedini bu formülden almıyor; kırma çatıda çatı açılımından alıyor. Bulgular motorun kendisi için.

## Lokman'ın cevapları (4 Ekim 15:18) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 13:22 sürümündeki altı soruydu. Cevaplar tırnak içinde, yazıldığı gibi. Lokman ayrıca en iyi bilgiyi kendisinin vereceğini söyledi: onun söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerli sayılır.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Çatı dizilimi: nereden başlar, kesim payı, yedek | "her köşeden başlayacak gibi hesapla yani 29 hesapla, evet kesim payı için 5 mm uygundur, senin yaptığın kesim planı ile yedek panele gerek yok bizde aynı kesim plan paftasını montajcıya vereceğiz" | Dizilim her yüzde sol köşeden başlıyor; kesim payı 5 mm ve yedeksiz adet kesinleşti. 29, 87 cm kapatan panelle çıkan adetti; 2. cevapla panel 100 cm kapatır olunca aynı kural **27** veriyor. Lokman 15:23'te teyit etti: "yok yanlış anlamadın aynen devam et". Açılım ve kesim planı yeniden çizildi; kesim ölçüleri tablosu eklendi. |
| 2 | Kapatma genişliği: tek kat panel 87 mi, 100 mü; kiremit desen sac 110 mu, 105 mi? | "aslında aldığımız ürünler değişiyor güncel olarak Tek Kat panelde 100 kapatır geliyor, kiremit desen sacıda 100 al sandviç panelde şimdilik 100 al ama 80 kapatırıda var bu bilgiyi daha sonra güncellenecek gibi hesaba kat" | Kurallarda tek kat panel 0,87 → 1,00; kiremit desen sac 1,10 → 1,00; sandviç panel 1,00 (80 cm kapatan ürün not edildi). Değerler ürüne göre değişir: girdide `cati.kapatma_m` yazıyorsa o kullanılır; üç gerçek liste örneği kendi ürünlerinin genişliğiyle (110, 100 ve 87 cm) hesaplanmaya devam ediyor, karşılaştırma değişmedi (74 / 119). Seçeneklerde sandviç panel 26 → 27, kiremit desen sac 26 → 30; sandviç panelin 80 cm kapatanıyla 32. |
| 3 | Boardex zayiatı %8 ile 2025 listelerinden az | "devam et" | %8 ile devam: dış cephe Boardex 31. |
| 4 | Damlalık hangi durumda listeye girer? | "damlalık uygulamasını yanlış buluyorum tamamen listeden çıkar, orijinal kapama aparatı var plastik ondan sipariş verirsek listeye sokarız damlalığı şimdilik çıkar hiçbir montajcı kullanmıyor" | Damlalık listede kalem olarak yoktu; mahya bandı formülündeki terimi çıkarıldı, adet değişmedi (4 rulo). Plastik kapama aparatı kurallara not edildi (`kapama_aparati`); sipariş verilirse listeye girecek. Listedeki "tek kat panel kapaması" (L 2500, 18 adet; 2025 listelerinden) duruyor: Excel motorunda damlalıktan ayrı kalem. Plastik aparatın onun yerine geçip geçmeyeceği soruldu. |
| 5 | Klima duvarı OSB takviyesinde sayılır mı? | "sen ilk seferdeki gibi say bayi maliyeti de göz önüne alıyor bunu bayiye belirtmem lazım şimdilik hangisi az ise onu baz al" | Okuma: iki hesap yapılır, az olan baz alınır. Yalnız dolap ve TV duvarları: 24,5 m² → 9 levha (baz). Odanın bütün yüzeyi (ilk hesap; Lokman'ın 3 Ekim 13:27 kuralı): 42,5 m² → 15 levha; satırın notunda, bayiye belirtilmek üzere. Klima duvarı baz hesapta sayılmıyor. Okumanın teyidi istendi. |
| 6 | Makas ve kiriş ölçüsü | "Tamam motoruda inceleyeceğim şimdilik motoru kastas al" | Çatı çeliği, veranda dikmeleri ve kirişleri Excel motorunun ortalamasıyla kalıyor: 706, 46 ve 81 kg. Lokman motoru inceleyecek. |

### Kesim planının ölçüleri

Kesim planı montajcıya verilecek (Lokman, 15:18). Çizimde ölçü yazmadığı için ölçüler ayrı bir dökümde: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_kesim_olculeri.md` (`cati_acilim.py --olcu-md`). İçinde üç tablo var:

- **Parçalar.** Yüz yüz, soldan sağa her şerit parçası: saçaktaki yeri, eni, sol ve sağ kenar boyu (saçak ucundan, taşma dahil), köşesi kesilen tam boy panelde aradaki kırık noktası, çıktığı panel.
- **Kesim ölçüleri.** Panel panel her parçanın paneldeki yeri: panelin sol ve sağ kenarında alt uçtan kaç cm ile kaç cm arası. Üst parça 180° çevrilerek karşı yüze konur; ters yüz edilmez.
- **Paneller.** Her panelden çıkan parçalar ve kullanılmayan boy.

Çizim, bu tablolar ve geometrik sağlama aynı yerleşimden üretilir. Ölçüler kaplamanın kapattığı genişliğe göredir; panelin bindirme payı ayrıca düşünülmedi.

### Panel boyu: 3 mm uzun sipariş edilirse iki panel az (öneri; karar bekliyor)

Panel boyu eğimli boy + taşma alınınca (L 4315) en uzun kesik parça ile köşe parçası aynı panelden çıkmıyor. İkisi birlikte 4 × 105,3 + 2 × 5 + 0,5 = 431,7 cm ister; panel 431,5 cm: 2,2 mm ile kaçıyor. 2. ve 3. şeritlerin eşleşmesi de aynı boyu istiyor. Bu yüzden her yüzün 4. şeridi bir paneli tek başına harcıyor (4 panel).

| Panel boyu | Tek kat panel ve sandviç panel (100 cm) | Trapez sac ve 80 cm kapatan sandviç panel | Kiremit desen sac (100 cm; artan parça yok) |
|---|---|---|---|
| L 4315 (eğimli boy + taşma) | 27 | 32 | 30 |
| L 4318 ve üzeri | 25 | 30 | 28 |

- Tek kat panelde toplam boy 116,5 m'den 108,1 m'ye iner (L 4325 ile).
- L 4318 tam eşik; pay kalsın diye L 4325 önerilir (kesim payı 1 cm olsa da yeter).
- Eksik 2,2 mm olduğu için kesim payı 2,8 mm ve altında kalırsa L 4315 ile de 25 çıkar; liste 5 mm ile hesaplıyor ve buna güvenmiyor.
- Uzun panelin bedeli: tam boy giden 10 panel 1 cm fazla gelir; saçakta taşma 6 cm olur ya da mahya ucundan 1 cm kesilir.
- Hesap bunu her modelde kendisi arıyor (`uzun_panelle`): panel boyunu 3 cm'ye kadar uzatmak adedi düşürüyorsa ilk düşüren boyu ve adedi verir. Kural yapılırsa liste uzun boyu yazar.
- Bağımsız hesap aynı eşiği ve aynı adetleri buldu.
- Karar Lokman'da: panel boyu kuralı mühendisin cevabından ve Excel motorundan geliyor (eğimli boy + 5 cm). Liste şimdilik L 4315 ve 27 adetle duruyor.

## Listenin grupları ve bayi kuralı

105 m² listedeki ve Excel motorundaki sırayla: Çelik panel · Metal aksam · Dış cephe kaplama · İç cephe kaplama · Çatı kaplamaları · Dere · Kapı ve pencere · Elektrik · Vida · Sıhhi tesisat · Boya.

- Bir grubun listeye girip girmeyeceği bayinin standardına bağlıdır. Örnek: 90 m² gerçek listede vida, elektrik ve sıhhi tesisat yok; 62 ve 105 m² listelerde var.
- Denemede: `bayi_kurallari_ornek.json` ve `yukleme.py --bayi <anahtar>`. Anahtar canlıda bayinin telefon numarası olacak; dosyada gerçek numara ya da ad yok. Kural grupları açıp kapatır; boya kovası ve vitrifiyeyi dahil eder ya da etmez; çatı yöntemini ve kaplamasını bayinin standardına çevirir.
- Hangi bayinin standardının ne olduğu soruldu. Mühendis (4 Ekim 12:14): standartlar henüz oturmadı; tek tük bayinin standardı var, ileride netleşecek. O zamana kadar bütün gruplar listede.

## Çelik: birim ağırlıklar (Excel motorundan)

Motor, gerçek projelerin tonajını duvar uzunluğuna bölerek ortalama almış (kat yüksekliği 2,70 m):

| Profil (sırt × başlık × et) | Dış duvar kg/m | İç duvar kg/m | Dikme kg/m | Kiriş kg/m |
|---|---|---|---|---|
| 80 × 45 × 0,8 | — | 13,00 | — | — |
| 80 × 45 × 1,2 | 20,33 | 19,75 | 6,42 | 6,55 |
| 140 × 45 × 0,8 | 18,20 | — | — | — |
| 140 × 45 × 1,2 | 29,04 | — | 8,26 | 8,27 |
| 140 × 45 × 1,5 | — | — | — | 11,04 |

Mühendisin tablosunda 140 × 0,8 satırında iç duvar 12,06 yazıyor: motorun sayfasında o değer, dışı 140 × 0,8 olan bir projenin 80 × 0,8 iç duvarı. Hesapta iç duvar kendi profiliyle aranır (80 × 0,8 → 13,00).

Çatı çeliği (80 × 45 × 0,8), saçak dahil çatı planının m²'si başına: beşik 5,70 · dört omuz 7,55 · beşik + cumba 5,65 · beşik + 2 cumba 6,08 kg/m². Dört omuz değeri üç projenin ortalaması (9,46 · 6,86 · 6,33).

- Hesap: duvar kg = duvar boyu × birim ağırlık. Dış duvar boyu = dış çevre; iç duvar boyu plandan (iç duvarların toplam boyu).
- Motor girdi olarak yalnız dikdörtgenin kenarlarını ve bölme sayısını alıyor; iç duvar boyunu (uzun + kısa) × (0,1543 × bölme sayısı + 0,756) diye tahmin ediyor. Planımız olduğu için gerçek boylar kullanıldı.
- Dikme = adet × 2,40 m × birim ağırlık; kiriş = boy × birim ağırlık; çatı = çatı planı × kg/m². Bunlar şimdilik böyle (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"); Lokman kiriş ve makasları bir makas ölçüsünden verirse değişir.
- **Tavan paneli ve çatı paneli** (yöntem A). 100 m² binada tavan paneli 354,84 kg, çatı paneli 440,32 kg (Lokman'ın 4 Ekim düzeltmesi; mühendisin ilk cevabında 429,83 ve 561,6 kg'dı). Adet 100 m²'de 8 ve 12 (mühendisin ilk cevabı; üçüncü cevaplarda teyit etti: bu adetlerle ilerlenir, paneller genelde dört omuz çatıda kullanılır). Hesap: çatının örttüğü oturum alanı ÷ 100 × bu değerler; adet yukarı yuvarlanır. Ç8201 (82,05 m²): 291 kg / 7 adet ve 361 kg / 10 adet. Oranlamayı Lokman onayladı; kesin adet panel yerleşiminden gelir.

### Üç gerçek listeyle karşılaştırma (kg)

| Çelik (kg) | 90 m²: hesap / liste / fark | 62 m²: hesap / liste / fark | 105 m²: hesap / liste / fark |
|---|---|---|---|
| Dış duvar | — | 527 / 577 / −%8,6 | 965 / 1055 / −%8,5 |
| İç duvar | — | 157 / 180 / −%12,8 | 382 / 410 / −%6,9 |
| Duvar toplamı | 1282 / 1345 / −%4,7 | 684 / 757 / −%9,6 | 1347 / 1465 / −%8,1 |
| Kiriş ve kolon | 88 / 100 / −%11,7 | 145 / 161 / −%9,9 | — |
| Çatı | 590 / 535 / +%10,3 | 555 / 426 / +%30,4 | — |
| Toplam | 1990 / 1980 / +%0,5 | 1415 / 1364 / +%3,7 | — |

- Toplamlar %0,5 ve %3,7 farkla tutuyor; ama parçalar tek tek tutmuyor: duvarlar %5–13 eksik, çatı %10–30 fazla. Toplamın tutması, farkların birbirini götürmesinden.
- 140 mm dış karkaslı iki listede dış duvarların çoğu 0,8 mm, üçer paneli 1,2 mm; bu iki örnekte hesap listedeki gibi 0,8 mm ile yapıldığı için dış duvar %8,5 ve %8,6 eksik çıkıyor. O iki listede dış duvar 19,9 kg/m'ye geliyor (577 kg ÷ 28,98 m ve 1055 kg ÷ 53,04 m).
- Üç liste de yöntem B'de: tavan ve çatı paneli bu karşılaştırmada yok.

### Et kalınlığı (mühendisin kuralı, 4 Ekim)

Kural: tek katlı binada ve iki katlının zemin katında duvarlar 1,2 mm (dış 140 × 45 × 1,2 ya da 80 × 45 × 1,2; iç 80 × 45 × 1,2). İki katlının üst katında 0,8 mm; üst katta 200 cm ve daha geniş pencereli duvar 1,2 mm (genelde bir ya da iki duvar). Dikme ve kiriş 1,2 mm, makas 0,8 mm: bunlar listelerden çıkarım.

| Kaynak | Dış karkas | Dış duvar | İç duvar | Kuralla |
|---|---|---|---|---|
| 90 m² liste (2025), tek kat | 80 mm | hepsi 1,2 mm | 1,2 mm | uyuyor |
| 62 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 7 panel 0,8 mm | 0,8 mm | uymuyor |
| 105 m² liste (2025), tek kat | 140 mm | 3 panel 1,2 mm · 20 panel 0,8 mm | 0,8 mm | uymuyor |
| Motorun verisi: tek katlı 140'lık örnek (55 m²) | 140 mm | 1,2 mm | 1,2 mm | uyuyor |
| Motorun verisi: iki katlı iki projenin üst katı | 140 mm | 0,8 mm | 0,8 mm | uyuyor |
| Motorun verisi: iki katlı iki projenin zemin katı | 140 mm | 1,2 mm | 1,2 mm | uyuyor |

3 Ekim'de dış 140 için 0,8 mm varsayılmıştı (2025 listelerindeki gibi); kuralla 1,2 mm oldu. Bu yüzden Ç8201'de dış 140 seçeneği artık baz paketten ağır. 2025 tarihli iki tek katlı liste kurala uymuyor; mühendis üçüncü cevaplarda kuralı yineledi ("Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz."). O listeler eski uygulama olarak kayıtlı; üç gerçek listeyle karşılaştırma o listelerdeki kalınlıklarla yapılıyor.

| Ç8201 | Baz (dış 80) | Dış 140 |
|---|---|---|
| Dış duvar (32,0 m) | 80 × 1,2: 651 kg | 140 × 1,2: 929 kg (0,8 mm olsaydı 582 kg) |
| İç duvar | 19,70 m · 80 × 1,2: 389 kg | 19,40 m · 80 × 1,2: 383 kg (0,8 mm olsaydı 252 kg) |
| Çelik toplamı | 2555 kg | 2828 kg |

## Öteki kurallar

Durum: `lokman` Lokman söyledi · `muhendis` mühendis söyledi · `excel` yükleme listesi çalışma kitabındaki formül · `motor` Excel motorundaki formül ya da not · `uydurma` gerçek listelerdeki adedi tutturan kural · `varsayim` Claude'un varsayımı · `soru` kural bilinmiyor · `bekliyor` değer henüz yok (sorulacak ya da paftadan gelecek) · `model` modeldeki açıklıklardan ya da plandan · `liste` örnekte gerçek listeden alınan sayı. Katsayılar ve kaynakları: `deneme/2026-10-03_yukleme/kurallar.json`.

- **Terim.** PortatifEv listelerinde "alın" beşik çatının kalkan yüzüdür (alın sacı, çatı alnı). Saçak ucundaki düşey yüz (topuk + çatı panelinin düşey ölçüsü; Lokman'ın deyişiyle "saçak genişliği") burada "saçak yüzü" diye geçer; önceki kayıtlarda ve kodun içinde "alın" denmişti.
- **Dış cephe** (excel; zayiat muhendis). Net alan = çevre × kat yüksekliği + dikme ve kiriş kaplaması (adet × çevre × boy) + çatı alnı (kalkan) alanları − kapı ve pencere boşlukları. Boardex = net × 1,08 ÷ (1,2 × 2,4): zayiat %8 (mühendis, 4 Ekim 12:14; motorda ve bir hesap sayfasında da %8). Listelerin çalışma kitabındaki formül %15'ti ve üç listedeki adetler %15'e uyuyor (hesap / liste, 90 · 62 · 105 m²: 45 / 46, 32 / 32, 52 / 51); %8 ile 43 / 46 · 30 / 32 · 48 / 51. Ç8201'de %8 ile 31, %15 ile 33 levha.
- **Kalınlıklar** (muhendis, 4 Ekim 12:14). Boardex 12,5 mm; OSB 11 mm. 2025 listelerinde Boardex 8 mm, OSB 9 mm yazıyor; motorda Boardex 8 mm, OSB 11 mm.
- **İç cephe** (excel). Odalar "beyaz" ve "yeşil" diye ayrılır. Oda oda: iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan = net × 1,05 ÷ (1,2 × 2,5). Tavan alçıpanı = tavan alanı × 1,05 ÷ 3,0.
- **OSB takviyesi** (muhendis). Yalnız dolap ve TV ünitesi gelen duvarlar: modelin tanımında yazılır. Her duvarın o odaya bakan yüzünün boyu × kat yüksekliği − o yüzdeki boşluklar; × 1,05 ÷ 2,98. Duvarın tamamı alınır (Lokman: "tüm yüzeyini"; mühendis, 4 Ekim 12:14: "Duvarın tamamını al."). Odanın bütün yüzeyi de hesaplanır (Lokman'ın 3 Ekim kuralı); az olan baz alınır, öteki bayiye belirtilmek üzere satırın notunda durur (Lokman, 4 Ekim 15:18). Klima duvarı baz hesapta sayılmaz. Tanımda duvar yazmıyorsa kalem hesaplanmaz.
- **Kapı boşlukları.** İç kapı 0,90 × 2,14 (lokman; çalışma kitaplarında da aynı). Dış kapı 0,95 × 2,10 (muhendis, 4 Ekim 12:14; 90 ve 105 m² listelerde de böyle, 62 m² listede 0,95 × 2,00).
- **Duvar izolasyonu** (uydurma). Dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64. 105 m² listenin hesap sayfasında "dış × 2" diye yazıyor.
- **Çatı kaplaması.** Baz pakette tek kat panel (lokman). Kırma çatıda panel ve sac adedi çatı açılımından (lokman; yukarıda "Lokman'ın ikinci düzeltmesi"): yüzler şerit şerit dizilir, çapraz kesimden artan parça karşı yüzde kullanılır. Dizilim her yüzde köşeden başlar; kesim payı 5 mm; yedek yok (lokman, 4 Ekim 15:18). Kaplama saçaktan 5 cm taşar: panel boyu = eğimli boy + 5 cm (muhendis, 4 Ekim 12:14). Çatı planı girdide yoksa yüzey × 1,10 ÷ (boy × kapatma genişliği) (uydurma). Beşik çatıda saçak boyu ÷ kapatma genişliği (uydurma). Kapatma (lokman, 4 Ekim 15:18; ürüne göre değişir): tek kat panel, sandviç panel ve kiremit desen sac 100 cm; trapez sac 80 cm (motor). Sandviç panelin 80 cm kapatanı da var. 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di.
- **Shingle ve membran** (motor). Adet = çatı yüzeyi × çatı katsayısı ÷ 8 ("adet / 8 m²"). Çatı katsayısı: beşik 1; beşik + cumba 1,14; beşik + 2 cumba 1,27; dört omuz 1,06. Gerçek listeyle karşılaştırılmadı.
- **Mahya** (lokman). Mahya hattı ÷ (2,8 − 0,30). Kırma çatıda hat = tepe + dört kırma. Trapez sac mahyası L 800: mahya hattı ÷ (0,8 − 0,20) (motor).
- **Mahya bandı** (muhendis, 4 Ekim 12:14). Mühendisin formülü: (mahya adedi × 2,8 m + ters mahya adedi × 2,8 m + damlalık adedi × 2,5 m) ÷ 10 m (rulo / 10 m), yukarı. Excel motorundaki formül aynı; motorda trapez sac mahyası × 0,8 m de toplanır, OSB mahyası ve özel mahya toplanmaz. Damlalık listeden tamamen çıkarıldı (Lokman, 4 Ekim 15:18: montajcılar kullanmıyor); terimi formülde yok. Ç8201: 11 × 2,8 ÷ 10 → 4 rulo. 01:24'teki uygulama mahya uzunluğundandı (3 rulo; açıklamalı prefabrik yükleme listesi çalışma kitabındaki formül).
- **Çatı müdahale kapağı** (muhendis). Standart pakette gönderilmez; müşteri isterse kat adedi kadar eklenir.
- **Dere** (motor). Metal dere = saçak boyu ÷ (4,0 − 0,20); Lokman'ın 30 cm kuralında dere sayılmadı. Kelepçe = dere × 8. İniş başına: boru 1, aparat 1, açık dirsek 2, kapalı dirsek 1, iniş kelepçesi 2. İniş sayısı Lokman'ın kuralıyla; plana elle yerleştirilmişse o sayı (muhendis).
- **Köşebent** (muhendis). (Odaların tavan çevresi + veranda tavanının çevresi + iç köşe sayısı × 2,7 m) ÷ 2,5. İç köşe: iki duvarın odanın içinde buluştuğu köşe. Odaya doğru çıkıntı yapan köşeler sayılmaz; veranda tavanının çevresi sayılır (4 Ekim 12:14). Veranda çevresi brüt ölçüyle alınır; verandada köşe boyu eklenmez (okuma). Planı olmayan örnekte oda başına 4 iç köşe sayılır.
- **Saçak altı ve saçak yüzü.** Yöntem A'da saçak altı Boardex (lokman); adet formülü 62 m² listeden (uydurma): saçak boyu × 0,30 × 1,08 ÷ 2,88. Saçak yüzü de Boardex (muhendis): saçak ucu çevresi × yüz yüksekliği × 1,08 ÷ 2,88. Zayiat Boardex'in %8'i (62 m² listenin formülünde %15'ti). Yöntem A'da saçak omegası yok (muhendis).
- **Yöntem B kalemleri.** Saçak sacı ve alın sacı = boy ÷ (2,5 − 0,30): 30 cm bindirme Lokman'dan; parça boyu L 2500 listelerden (÷ 2,2 çıkarım). Saçak omegası, tavan omegası ve aşık kuralları iki listeye uydurulmuştu; değişmedi.
- **Vida, boya, tesisat** (motor ve excel). Alçıpan vidası = levha × 40; OSB vidası = OSB × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; pencere vidası = pencere × 20; trapez (5,5 × 25) = aşık × 10 + omega × 10 ya da 6 + çelik panel × 10 + köşebent × 6; trapez (5,5 × 60) = m² × 2,5 + sac boyu ÷ 200 × sac adedi; panel vidası = panel boyu ÷ 200 × adet; çelik dübel = duvar paneli × 2; uçlar ve kesme taşı = m² ÷ 15; inox taş = m² ÷ 10; RYSB = m² × 7,5. Boya: 100 m²'ye dış 2, iç 2, tavan 1, astar 1 kova; dayson = m² × 0,06; köpük 2; mastik = pencere adedi. Tesisat: ıslak hacim başına 6 boru, 15 dirsek, 12 kulaklı dirsek, 6 düz T, 15 maşon, 6 iç dişli T, 3 atlama parçası; vitrifiye dahilse duşakabin, klozet, dolap ve batarya grubu.
- **Elektrik.** Pafta sayımı varsa o kullanılır (motorun notu: sayılar "montaj paftasından sayılır"). Yoksa mühendisin oda başına kuralı (yukarıda). Kablo, buat, besleme kablosu, zil, sigorta kutusu, kaçak akım rölesi ve izole bant motorun formülleriyle.

## Üç gerçek listeyle karşılaştırma (adet)

Özet: 90 m²: 29 kalemin 15 tanesinde adet aynı; 62 m²: 41 kalemin 28 tanesinde adet aynı; 105 m²: 49 kalemin 31 tanesinde adet aynı. Toplam 119 karşılaştırmanın 74 tanesi aynı.

Tam tablo: `deneme/2026-10-03_yukleme/sonuc/tablolar.md`. Adedi doğrudan listeden alınan satırlar karşılaştırmaya girmedi: dere kapağı, elektrik sayımı ve 105 m² listede iniş sayısı ile ona bağlı dört satır. 90 ve 62 m² listelerde iniş sayısı Lokman'ın kuralından hesaplandı (6; listelerde 7): bu tek fark beş satırda birden görünüyor, yani 45 farkın 10'u oradan.

**Bu bir sınama değil.** `uydurma` kuralların katsayıları 90 ve 62 m² listelere bakılarak seçilmişti; o listelerle tutması kanıt sayılmaz. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi, kesme taşı katsayısı 62 ve 105 m² listelere bakılarak seçildi. Onun da çatı planı yok: saçak, mahya, alın boyları ve elektrik sayımı listede yazan değerlerdir. Üç örnekte de çatı uzunlukları ve tavan alanları listelerdeki değerlerdir. Yani hiçbiri kör sınama değil; yöntem A için ise hiç gerçek liste yok. Mühendisin cevaplarıyla gelen kurallardan (tavan ve çatı paneli, OSB takviyesinin duvarları, saçak yüzü) hiçbiri bu üç listeyle sınanamıyor; köşebent ve elektrik kuralı yukarıda sınandı. Çatı açılımı tek bir gerçek listeyle (62 m²) karşılaştırılabildi.

Adedi tutmayan kalemler:

| Grup | Kalem | Kural | Durum | 90 m²: hesap / liste | 62 m²: hesap / liste | 105 m²: hesap / liste |
|---|---|---|---|---|---|---|
| Metal aksam | Saçak sacı (30'luk) | saçak boyu ÷ (2,5 − 0,30 bindirme) | lokman | 15 / 14 ✗ | 18 / 17 ✗ | 18 / 18 |
| Metal aksam | Alın sacı (30'luk) | alın boyu ÷ (2,5 − 0,30 bindirme) | lokman | 8 / 9 ✗ | — | 8 / 8 |
| Metal aksam | Tavan omegası (60'lık) | tavan alanı ÷ 0,60 ÷ 3,75 | uydurma | 37 / 40 ✗ | 26 / 26 | 42 / 44 ✗ |
| Metal aksam | Aşık | eğim boyunca 60 cm aralıkla sıralar + mahya aşığı; kırmada her sıra çatıyı dolanır; × 1,05 ÷ 4,2 | uydurma | 56 / 57 ✗ | 41 / 41 | — |
| Metal aksam | Köşebent | (oda tavan çevreleri 87,84 m + 20 iç köşe × 2,7 m) ÷ 2,5 | muhendis | 57 / 70 ✗ | 39 / 50 ✗ | 70 / 85 ✗ |
| Metal aksam | Saçaklar için Boardex | saçak boyu × saçak eni × 1,08 ÷ 2,88 | uydurma | — | 5 / 5 | 8 / 7 ✗ |
| Dış cephe kaplama | Dış cephe Boardex | (çevre × yükseklik + kolon/kiriş kaplaması + çatı alnı (kalkan) − boşluklar) × 1,08 ÷ 2,88 | excel | 43 / 46 ✗ | 30 / 32 ✗ | 48 / 51 ✗ |
| İç cephe kaplama | Duvar alçıpan beyaz | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0 | excel | 66 / 67 ✗ | 32 / 32 | 78 / 79 ✗ |
| İç cephe kaplama | Duvar alçıpan yeşil | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0; yeşil = ıslak hacimler | excel | 9 / 9 | 7 / 8 ✗ | 13 / 14 ✗ |
| İç cephe kaplama | Tavan alçıpan yeşil | tavan alanı × 1,05 ÷ 3,0; yeşil = ıslak hacim + veranda tavanı | lokman | 5 / 6 ✗ | 7 / 7 | 3 / 3 |
| İç cephe kaplama | OSB 9 mm (duvar) | listede yazan alan × 1,05 ÷ 2,98; alanın nasıl seçildiği listede yazmıyor | excel | 13 / 13 | — | 14 / 15 ✗ |
| İç cephe kaplama | Duvar izolasyonu | dış duvar × kat sayısı (80 mm karkasta 1, 140 mm'de 2) + iç duvar − boşluklar; ÷ 8,64 | uydurma | 18 / 18 | 19 / 19 | 39 / 38 ✗ |
| Çatı kaplamaları | Sandviç panel | çatı açılımı: yüzler şerit şerit dizilir; çapraz kesimden artan parça karşı yüzde kullanılır; panel boyu = eğimli boy + taşma | lokman | — | 28 / 27 ✗ | — |
| Dere | Dere iniş borusu | 4 köşe + 2 orta (10 m ve üzeri cepheler) | lokman | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | Dere iniş aparatı | iniş sayısı × 1 | motor | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | Açık dirsek | iniş sayısı × 2 | motor | 12 / 14 ✗ | 12 / 14 ✗ | — |
| Dere | Kapalı dirsek | iniş sayısı × 1 | motor | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | İniş kelepçesi | iniş sayısı × 2 | motor | 12 / 14 ✗ | 12 / 14 ✗ | — |
| Boya | Silikonize mastik | pencere adedi | uydurma | 6 / 8 ✗ | 6 / 8 ✗ | 8 / 8 |
| Boya | Dayson | bina m² × 0,06 | motor | 6 / 6 | 4 / 4 | 7 / 6 ✗ |
| Vida | RYSB pul başlı (3,9 × 32) | bina m² × 7,5 | motor | — | 465 / 400 ✗ | 788 / 500 ✗ |
| Vida | Alçıpan vidası (3,5 × 35) | alçıpan ve Boardex levha sayısı × 40; 250'ye yuvarlandı | excel | — | 4000 / 4000 | 7250 / 8500 ✗ |
| Vida | OSB ve yalıpan vidası (3,9 × 32) | OSB levha × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; 500'e yuvarlandı | motor | — | 3500 / 3500 | 1000 / 1500 ✗ |
| Vida | Pencere vidası (4,8 × 70) | pencere sayısı × 20 | excel | — | 120 / 120 | 160 / 180 ✗ |
| Vida | Trapez vida (5,5 × 110; sandviç panel) | panel boyu (mm) ÷ 200 × panel adedi; 250'ye yuvarlandı | motor | — | 500 / 750 ✗ | — |
| Vida | Çelik dübel (klipsli) | duvar paneli adedi × 2 | motor | — | 32 / 32 | 72 / 80 ✗ |
| Vida | Şase pul | çelik dübel adedi kadar | motor | — | 32 / 32 | 72 / 80 ✗ |
| Vida | İnox taş | bina m² ÷ 10 | excel | — | 7 / 7 | 11 / 10 ✗ |
| Elektrik | Buat kasa | anahtar + priz + oda sayısı (veranda hariç) | motor | — | — | 40 / 37 ✗ |
| Elektrik | İzole bant | bina m² × 0,06 | motor | — | — | 7 / 3 ✗ |

Okuma:

- **Köşebent.** Mühendisin formülü, oda başına 4 iç köşeyle listelerin altında kalıyor (57 / 70, 39 / 50, 70 / 85); önceki kural (m² ÷ 2,5) yarısını veriyordu. Gerçek iç köşe sayıları bilinmiyor.
- **Sandviç panel (62 m², kırma çatı).** Liste 27 adet L 3200 (ayrıca 2 adet L 1000); açılım dizilimi taşmayla 28 veriyor (taşmasız 26'ydı). Önceki kural (yüzey + %10) 27'yi tutturuyordu, ama o listeye uydurulmuştu.
- **Dış cephe Boardex.** Zayiat %8 olunca üç listede de 2–3 levha az: 43 / 46 · 30 / 32 · 48 / 51. %15 ile 45 / 46 · 32 / 32 · 52 / 51'di. Karşılaştırmadaki bir eksilme buradan (74 / 119; önce 75).
- **İniş sayısı.** Kural 90 ve 62 m² projelerde 6 veriyor (dört köşe + iki uzun cephe); listelerde 7. Mühendis: iniş plana bakarak yerleştirilir. 105 m² listede 10; cephe ölçüleri olmadığı için kural hesaplanmadı.
- **Saçak sacı.** L 2500 parça ve 30 cm bindirme (÷ 2,2) en yeni listeyi (Kasım 2025) tutturuyor; Eylül 2025 listelerinde birer fazla veriyor. Excel motorundaki 20 cm (÷ 2,3) üç listeyi de tutturuyor (14, 17, 18).
- **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var; kurala göre birlikte olmaz. 105 m² listede saçak altı 0,50 m alınmış (19,6 m² = 39,2 × 0,50).
- **Öteki levhalar** (alçıpan, OSB, izolasyon, saçak Boardex'i). Farklar 1 adet: listelerde yuvarlama bir yukarı, bir en yakına yapılmış. 105 m² listede beyaz duvar alçıpanındaki fark çalışma kitabındaki bir hücre hatasından: bir odada iki iç kapı boşluğu (3,85 m²) yerine 2 m² düşülmüş.
- **Sarf kalemleri** (RYSB, alçıpan vidası, izole bant, mastik). Motorun m² formülleri listelerdeki sayıları vermiyor. Mastik üç listede de 8.
- **Tutanlar.** Beyaz tavan alçıpanı, mahya, dere, dere kelepçesi, sıhhi tesisat (105 m²'de yedi kalemin yedisi), uçlar ve kesme taşı.

## Ç8201 taslak

Girdi: `deneme/2026-10-03_yukleme/sonuc/C8201_girdi.json` (geometri Yapı Tanımı taslağından; varsayımlar dosyanın içinde). Çatı yöntemi A; çatı kaplaması baz paketteki tek kat panel. "Dış 140" sütunu yalnız değişenleri gösterir. Bu modelin gerçek listesi yok: taslak yalnız kurallardan çıkıyor.

Not: saçaklar için Boardex'te alan liste yöntemiyle saçak boyu × 0,30 = 11,8 m² (köşeler iki kez sayılır); gerçek saçak altı 11,4 m². İkisi de 5 levha.

| Grup | Kalem | Boyut | Baz | Dış 140 | Ölçü (baz) | kg (baz) | Durum |
|---|---|---|---|---|---|---|---|
| Çelik panel | Dış cephe duvar panelleri | 80 × 45 × 1,2 | 8 | 140 × 45 × 1,2: 929 kg | 32,0 m | 651 | motor |
| Çelik panel | İç cephe duvar panelleri | 80 × 45 × 1,2 | 6 | 383 kg | 19,7 m | 389 | motor |
| Çelik panel | Veranda dikmeleri (kolon paneli) | 80 × 45 × 1,2 | 3 | aynı | 7,2 m | 46 | motor |
| Çelik panel | Veranda kirişleri (kiriş paneli) | 80 × 45 × 1,2 | 4 | aynı | 12,4 m | 81 | motor |
| Çelik panel | Çatı makas panelleri | 80 × 45 × 0,8 | 25 | aynı | 93,5 m² | 706 | motor |
| Çelik panel | Tavan paneli (makas arası) | roll form çelik | 7 | aynı | 82,0 m² | 291 | lokman |
| Çelik panel | Çatı paneli (makas üstü, sırt 80 mm) | roll form çelik | 10 | aynı | 82,0 m² | 361 | lokman |
| Çelik panel | Boy C profil | 80 × 45 × 0,8 | 3 | aynı |  | 15 | motor |
| Çelik panel | Boy C profil | 80 × 45 × 1,2 | 3 | aynı |  | 15 | motor |
| Çelik panel | Toplam (adedi ve kg'ı bilinenler) |  | 69 | 2828 kg |  | 2555 | motor |
| Metal aksam | Saçaklar için Boardex | 12,5 × 1200 × 2400 | 5 | aynı | 11,8 m² |  | uydurma |
| Metal aksam | Saçak yüzü için Boardex | 12,5 × 1200 × 2400 | 3 | aynı | 7,2 m² |  | muhendis |
| Metal aksam | Köşebent | L 2500 | 59 | aynı | 146,3 m |  | muhendis |
| Dış cephe kaplama | Dış cephe Boardex | 12,5 × 1200 × 2400 | 31 | aynı | 80,7 m² |  | excel |
| İç cephe kaplama | Duvar alçıpan beyaz | 1200 × 2500 | 47 | 46 | 132,8 m² |  | excel |
| İç cephe kaplama | Duvar alçıpan yeşil | 1200 × 2500 | 8 | aynı | 20,4 m² |  | excel |
| İç cephe kaplama | Tavan alçıpan beyaz | 1200 × 2500 | 19 | aynı | 54,1 m² |  | motor |
| İç cephe kaplama | Tavan alçıpan yeşil | 1200 × 2500 | 8 | aynı | 22,6 m² |  | lokman |
| İç cephe kaplama | OSB (TV ve mutfak dolabı arkası takviyesi) | 11 × 1220 × 2440 | 9 | aynı | 24,5 m² |  | muhendis |
| İç cephe kaplama | Duvar izolasyonu | paket 8,64 m² | 13 | 23 | 112,2 m² |  | uydurma |
| Çatı kaplamaları | Tek kat panel | L 4315 · 100 cm kapatır | 27 | aynı | 98,4 m² |  | lokman |
| Çatı kaplamaları | Metal kiremit mahyası | L 2800 | 11 | aynı | 27,0 m |  | lokman |
| Çatı kaplamaları | Tek kat panel kapaması | L 2500 | 18 | aynı | 39,3 m |  | uydurma |
| Çatı kaplamaları | Mahya bandı | rulo / 10 m | 4 | aynı | 30,8 m |  | muhendis |
| Çatı kaplamaları | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | aynı | 88,9 m² |  | uydurma |
| Dere | Metal dere | L 4000 | 11 | aynı | 39,3 m |  | motor |
| Dere | Dere iniş borusu | L 3000 | 6 | aynı |  |  | lokman |
| Dere | Dere iniş aparatı | adet | 6 | aynı |  |  | motor |
| Dere | Açık dirsek | adet | 12 | aynı |  |  | motor |
| Dere | Kapalı dirsek | adet | 6 | aynı |  |  | motor |
| Dere | İniş kelepçesi | adet | 12 | aynı |  |  | motor |
| Dere | Dere kelepçesi | adet | 88 | aynı |  |  | motor |
| Kapı ve pencere | Melamin kapı (80'lik kanat) | 90 × 214 | 4 | aynı |  |  | lokman |
| Kapı ve pencere | Kompozit çelik kapı | 90 × 210 | 1 | aynı |  |  | model |
| Kapı ve pencere | PVC pencere | 120/180 | 3 | aynı |  |  | model |
| Kapı ve pencere | PVC vasistas | 60/40 | 1 | aynı |  |  | model |
| Kapı ve pencere | PVC pencere | 120/100 | 1 | aynı |  |  | model |
| Kapı ve pencere | PVC pencere | 180/180 | 3 | aynı |  |  | model |
| Elektrik | Tijli duy | adet | 6 | aynı |  |  | muhendis |
| Elektrik | Yuvarlak glop | adet | 3 | aynı |  |  | muhendis |
| Elektrik | Ampul | adet | 9 | aynı |  |  | motor |
| Elektrik | Tekli anahtar | adet | 5 | aynı |  |  | muhendis |
| Elektrik | Çiftli anahtar | adet | 2 | aynı |  |  | muhendis |
| Elektrik | Tekli priz | adet | 16 | aynı |  |  | muhendis |
| Elektrik | Çiftli priz | adet | 2 | aynı |  |  | muhendis |
| Elektrik | Uydu prizi | adet | 1 | aynı |  |  | muhendis |
| Elektrik | W otomat (sigorta) | adet | 9 | aynı |  |  | muhendis |
| Elektrik | NYM kablo (3 × 2,5) | metre | 145 | aynı |  |  | motor |
| Elektrik | NYM kablo (2 × 1,5) | metre | 121 | aynı |  |  | motor |
| Elektrik | Buat kasa | adet | 31 | aynı |  |  | motor |
| Elektrik | Uydu kablo | metre | 25 | aynı |  |  | motor |
| Elektrik | Besleme kablosu (sigorta kutuları arası) | metre | 5 | aynı |  |  | motor |
| Elektrik | Besleme kablo borusu | metre | 5 | aynı |  |  | motor |
| Elektrik | Zil | adet | 1 | aynı |  |  | motor |
| Elektrik | Sigorta kutusu (12'li) | adet | 1 | aynı |  |  | motor |
| Elektrik | İzole bant | adet | 5 | aynı | 82,0 m² |  | motor |
| Elektrik | Kaçak akım rölesi | adet | 1 | aynı |  |  | motor |
| Vida | RYSB pul başlı (3,9 × 32) | adet | 615 | aynı | 82,0 m² |  | motor |
| Vida | Alçıpan vidası (3,5 × 35) | adet | 5000 | aynı | 121,0 levha |  | excel |
| Vida | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | aynı | 700,0 vida |  | motor |
| Vida | Pencere vidası (4,8 × 70) | adet | 160 | aynı | 8,0 pencere |  | excel |
| Vida | Trapez vida (5,5 × 25) | adet | 1250 | aynı | 1044,0 vida |  | excel |
| Vida | Trapez vida (5,5 × 60) | adet | 250 | aynı | 205,0 vida |  | motor |
| Vida | Trapez vida (5,5 × 76; tek kat panel) | adet | 750 | aynı | 582,5 vida |  | motor |
| Vida | Çelik dübel (klipsli) | adet | 28 | aynı | 14,0 panel |  | motor |
| Vida | Şase pul | adet | 28 | aynı | 14,0 panel |  | motor |
| Vida | 8'lik trapez uç | adet | 6 | aynı | 82,0 m² |  | motor |
| Vida | PH2 uç | adet | 6 | aynı | 82,0 m² |  | motor |
| Vida | 230'luk kesme taşı | adet | 6 | aynı | 82,0 m² |  | uydurma |
| Vida | İnox taş | adet | 9 | aynı | 82,0 m² |  | excel |
| Vida | Çırpı ipi | adet | 1 | aynı |  |  | motor |
| Sıhhi tesisat | Temiz su borusu | L 4000 | 6 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Normal dirsek 20 mm | adet | 15 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Kulaklı dirsek 20 mm | adet | 12 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Düz T 20 mm | adet | 6 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Maşon 20 mm | adet | 15 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | İç dişli T 20 mm | adet | 6 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Atlama parçası (yarım parmak) | adet | 3 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Duşakabin (90 × 90) | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Klozet | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Banyo dolabı | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Sıhhi tesisat | Banyo batarya grubu | takım | 1 | aynı | 1,0 ıslak hacim |  | motor |
| Boya | Dış cephe boyası | kova 17,5 kg | 2 | aynı | 82,0 m² |  | motor |
| Boya | İç cephe boyası | kova 17,5 kg | 2 | aynı | 82,0 m² |  | motor |
| Boya | Tavan boyası | kova 17,5 kg | 1 | aynı | 82,0 m² |  | motor |
| Boya | Astar | kova 17,5 kg | 1 | aynı | 82,0 m² |  | motor |
| Boya | Silikonize mastik | adet | 8 | aynı | 8,0 pencere |  | uydurma |
| Boya | Dayson | adet | 5 | aynı | 82,0 m² |  | motor |
| Boya | Poliüretan köpük | adet | 2 | aynı |  |  | motor |

### Çatı kaplaması seçenekleri

Baz pakette tek kat panel (Lokman, 4 Ekim 01:42). Altı seçenekte değişen kalemler (son üç seçenek gerçek listeyle karşılaştırılmadı):

| Seçenek | Kalem | Boyut | Adet | Durum |
|---|---|---|---|---|
| Tek kat panel (baz paket) | Tek kat panel | L 4315 · 100 cm kapatır | 27 | lokman |
| Tek kat panel (baz paket) | Metal kiremit mahyası | L 2800 | 11 | lokman |
| Tek kat panel (baz paket) | Tek kat panel kapaması | L 2500 | 18 | uydurma |
| Tek kat panel (baz paket) | Mahya bandı | rulo / 10 m | 4 | muhendis |
| Tek kat panel (baz paket) | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Tek kat panel (baz paket) | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Tek kat panel (baz paket) | Trapez vida (5,5 × 60) | adet | 250 | motor |
| Tek kat panel (baz paket) | Trapez vida (5,5 × 76; tek kat panel) | adet | 750 | motor |
| Sandviç panel | Sandviç panel | L 4315 · 100 cm kapatır | 27 | lokman |
| Sandviç panel | Metal kiremit mahyası | L 2800 | 11 | lokman |
| Sandviç panel | Sandviç panel kapaması | L 2500 | 18 | uydurma |
| Sandviç panel | Mahya bandı | rulo / 10 m | 4 | muhendis |
| Sandviç panel | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Sandviç panel | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Sandviç panel | Trapez vida (5,5 × 60) | adet | 250 | motor |
| Sandviç panel | Trapez vida (5,5 × 110; sandviç panel) | adet | 750 | motor |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Çatı OSB | 11 × 1220 × 2440 | 35 | uydurma |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Nem bariyeri | m² | 105 | motor |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Metal kiremit (kiremit desen sac) | L 4315 · 100 cm kapatır | 30 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Metal kiremit mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | OSB mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Mahya bandı | rulo / 10 m | 4 | muhendis |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Trapez vida (5,5 × 60) | adet | 1000 | motor |
| OSB + nem bariyeri + trapez sac | Çatı OSB | 11 × 1220 × 2440 | 35 | uydurma |
| OSB + nem bariyeri + trapez sac | Nem bariyeri | m² | 105 | motor |
| OSB + nem bariyeri + trapez sac | Trapez sac | L 4315 · 80 cm kapatır | 32 | lokman |
| OSB + nem bariyeri + trapez sac | Trapez sac mahyası | L 800 | 45 | motor |
| OSB + nem bariyeri + trapez sac | OSB mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + trapez sac | Mahya bandı | rulo / 10 m | 4 | muhendis |
| OSB + nem bariyeri + trapez sac | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + nem bariyeri + trapez sac | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + nem bariyeri + trapez sac | Trapez vida (5,5 × 60) | adet | 1000 | motor |
| Trapez sac | Trapez sac | L 4315 · 80 cm kapatır | 32 | lokman |
| Trapez sac | Trapez sac mahyası | L 800 | 45 | motor |
| Trapez sac | Mahya bandı | rulo / 10 m | 4 | muhendis |
| Trapez sac | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Trapez sac | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Trapez sac | Trapez vida (5,5 × 60) | adet | 1000 | motor |
| OSB + membran + shingle | Çatı OSB | 11 × 1220 × 2440 | 35 | uydurma |
| OSB + membran + shingle | Nem bariyeri | m² | 105 | motor |
| OSB + membran + shingle | Membran | adet / 8 m² | 14 | motor |
| OSB + membran + shingle | Shingle | adet / 8 m² | 14 | motor |
| OSB + membran + shingle | OSB mahyası | L 2800 | 11 | lokman |
| OSB + membran + shingle | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + membran + shingle | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + membran + shingle | Trapez vida (5,5 × 60) | adet | 250 | motor |

### Aynı model yöntem B ile

Bayi kuralı çatıyı yöntem B'ye çevirirse (`--bayi ORNEK-BAYI-3`; çıktı `sonuc/C8201_yontem_B.md`): tavan ve çatı paneli ile saçak altı ve saçak yüzü Boardex'i çıkar; saçak sacı 18, saçak omegası 18, tavan omegası 35, aşık 49 girer. Çelik 1903 kg, trapez vida (5,5 × 25) 2000 olur.

## Excel motoruyla ilgili gözlemler (mühendise iletilecek)

- **Trapez sac ve metal kiremit adedi.** Formülde 0,8 ve 1,05 paydanın parantezi dışında: kapatma genişliğine bölmek yerine çarpıyor. Hücreler, formülün işleyişi, örnekler ve öteki dört bulgu yukarıda ("Excel motorundaki çatı kaplaması formülü"). Mühendis 11. cevabında formülü yeniden kontrol etmemizi istedi; bulgu ona iletilecek. Trapez sacda motorun formülü kullanılmıyor.
- **Kırma çatıda kaplama adedi.** Motor yüzeyden hesaplıyor; notunda gerçek adedin AutoCAD'de yerleşimle bulunacağı yazıyor. Mühendisin 10 × 10 m dört omuz metrajında 118 m² yüzey için 36 adet L 5900 trapez sac var (yüzeyin 1,44 katı). 62 m² gerçek listede 27 adet L 3200 ve 2 adet L 1000 sandviç panel var (yüzeyin 1,15 katı). Lokman'ın 4 Ekim 01:42 kuralıyla adet artık çatı açılımından çıkıyor; karşılaştırma yukarıdaki tabloda.
- **Köşebent.** Motor plansız hesaplıyor: oda çevrelerini bina kenarlarının altı katı, iç köşeyi 36 sayıyor. Ç8201'in ölçüleriyle 78 verir; plandan 59.
- **Elektrik.** Motorda sayılar sabit: duy 7, glop 3, tekli anahtar 9, çiftli anahtar 2, tekli priz 22, çiftli priz 3, uydu prizi 1, sigorta 9; buat = anahtar + priz + 9.
- **İniş borusu.** Motorda dere adedi ÷ 5 + 6; mühendisin 10 × 10 m metrajındaki sayıları (8 ve 6) vermiyor (9 ve 8 verir).
- **Motorda olup listede olmayan kalemler.** Mühendisin ikinci cevaplarıyla: mahya bandı listeye eklendi; çatı müdahale kapağı standart pakette yok, müşteri isterse eklenir. Ters mahya kenar kutuları (ters mahya × 2) cumbalı çatı çalışılınca sorulacak; hesapta yok. Damlalık (L 2500; motorda 78. satır, adedi elle, şablonda 0): Lokman listeden tamamen çıkardı (4 Ekim 15:18); yerine düşünülen plastik kapama aparatı sipariş verilirse listeye girecek. Motorda panel kapamaları damlalıktan ayrı kalemler: tek kat panel kapaması (66. satır, L 2500, adedi elle) ve sandviç panel kapaması (69. satır, L 2800; saçak boyu × çatı katsayısı ÷ 2,6). Listedeki kapama 2025 listelerinden: L 2500, her saçak kenarı ÷ 2,5.

## Açık sorular

1. **Panel boyu.** Panel L 4318 ve daha uzun sipariş edilirse tek kat panel 27 yerine 25 yetiyor (yukarıda). Öneri L 4325. Kural olarak sorulan: panel boyu en çok 3 cm uzatılınca adet düşüyorsa liste uzun boyu yazsın mı? Karar Lokman'da.
2. **OSB takviyesi.** "sen ilk seferdeki gibi say … şimdilik hangisi az ise onu baz al" sözü şöyle okundu: iki hesap yapılır, az olan (9 levha) baz alınır, öteki (15 levha) bayiye belirtilir. Doğru mu?
3. **Kapatma genişlikleri.** Şimdilik tek kat panel, sandviç panel ve kiremit desen sac 100 cm; sandviç panelin 80 cm kapatanı da var. Ürün değiştikçe güncellenecek (Lokman, 4 Ekim 15:18).
4. **Excel motorundaki kaplama formülü.** Bulgular mühendise iletilecek (yukarıda): parantez, uzun kenardaki saçak, metal kiremit katsayısı, B61, sundurma.
5. **Makas ve kiriş.** Excel motoru kıstas (Lokman, 4 Ekim 15:18); Lokman motoru inceleyecek. Bir makas ölçüsü verilirse çatı çeliği, dikme ve kiriş değişir.
6. **Panel kapaması ve plastik kapama aparatı.** Listede tek kat panel kapaması (L 2500, 18 adet) duruyor: 2025 listelerinde var, Excel motorunda damlalıktan ayrı kalem. Çıkarılan yalnız damlalık mı, yoksa bu sac kapama da mı (plastik aparat onun yerine mi geçecek)? Aparat sipariş verilirse listeye girecek; adedinin kuralı o zaman.
7. **Bindirme.** Örnekte saçak sacı L 2800; listelerde L 2500. Saçak sacının boyu hangisi? Eylül 2025 listeleri 20 cm ile tutuyor. Derede ve L 800 trapez mahyasında bindirme de 30 cm mi (motorda 20 cm)?
8. **Veranda dikmeleri.** Sayısı ve yeri neye göre belirleniyor?
9. **OSB zayiatı.** %5 mi, %15 mi (105 m² listede %15)? Alçıpan %5.
10. **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var. O Boardex nereye gidiyor?
11. **Yöntem B.** Tavan omegası ve aşık aralığı 60 cm mi (sandviç panelde de)?
12. **Bayi standartları.** Henüz oturmadı (mühendis, 4 Ekim 12:14). Netleşince hangi bayide hangi gruplar, hangi çatı yöntemi ve kaplaması standart: bayi kuralı tablosuna yazılacak.
13. **Sırası gelince.** Çift kat modeli: üst katta 200 cm ve daha geniş pencereli duvarın 1,2 mm alınması (kural kayıtlı, uygulanmadı). Cumbalı çatı: ters mahya kenar kutuları ve cumbalı çatının açılımı.

Kapananlar:

- **Mühendisin 3 Ekim cevaplarıyla:** saçak omegası (gerekmiyor); saçak yüzünün malzemesi (Boardex); OSB takviyesinin kapsamı (yalnız dolap ve TV duvarları); köşebent formülü; iniş sayısındaki fark (plana göre yerleşim); elektrik sayıları (oda başına kural); çatı kaplaması seçenekleri (altı).
- **Lokman'ın 4 Ekim düzeltmeleri ve mühendisin ikinci cevaplarıyla:** tavan ve çatı panelinin ağırlığı ve alana oranlanması; baz paketin çatı kaplaması (tek kat panel; Lokman); kırma çatıda kaplama adedi (çatı açılımı ve dizilim; Lokman); et kalınlığı kuralı; OSB takviyesi için seçilen duvarlar; salon ile mutfak kurallarının birlikte uygulanması; mahya bandı (listede) ve çatı müdahale kapağı (yalnız müşteri isterse).
- **Mühendisin üçüncü cevaplarıyla (4 Ekim 12:14):** tek katta et kalınlığı (1,2 mm ile devam; 2025 listeleri eski uygulama); tavan ve çatı panelinin adedi (100 m²'de 8 ve 12); OSB takviyesinde duvarın tamamı; köşebentte çıkıntı yapan köşeler (sayılmaz) ve veranda tavanı (sayılır); buat için oda sayısı (veranda hariç) ve tekli prizler; mahya bandı formülü; dış kapı boşluğu (95 × 210); Boardex 12,5 mm, OSB 11 mm, Boardex zayiatı %8; kaplamanın saçaktan 5 cm taşması; kiremit desen sacda artan parçanın kullanılmaması.
- **Lokman'ın 4 Ekim 15:18 cevaplarıyla:** dizilimin başladığı yer (her yüzde köşeden); kesim payı (5 mm); yedek panel (yok; kesim planı montajcıya verilir); kapatma genişlikleri (güncel ürünler: 100 cm); Boardex zayiatı (%8 ile devam); damlalık (listeden çıktı); klima duvarı (baz hesapta sayılmaz; az olan baz); makas ve kirişte Excel motoru kıstas.

## Canlıya alırken (öneri; ayrı onay gerekir)

- Kurallar veridir: `kurallar.json`'daki her değer kaynağı ve durumuyla bir PostgreSQL tablosuna taşınır; kural değişince kod değişmez.
- Bayi kuralı: bayinin telefon numarası birincil anahtar; karşısında standardı (listeye giren gruplar, çatı yöntemi, çatı kaplaması, paket). Liste, mesajı atan bayinin standardına göre kurulur.
- Modelin tanımı listenin girdisidir: odaların işlevi (elektrik kuralı), dolap ve TV duvarları (OSB takviyesi), elle yerleştirilmiş iniş yerleri tanımda durur.
- Hesap deterministik bir modüldür; LLM yalnız talebi anlar (K05). Çatı açılımı da öyle: aynı çatı ve kaplama her zaman aynı dizilimi verir.
- Bunların hiçbiri yapılmadı: sunucu ve canlı değişiklik Lokman'ın ayrı onayıyla yapılır.
