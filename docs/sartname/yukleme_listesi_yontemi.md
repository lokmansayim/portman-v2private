# Çelik yükleme listesi: yöntem ve taslak (3–9 Ekim 2026)

Son güncelleme: 9 Ekim 2026 22:37. Lokman, 3 Ekim 12:03: yükleme listesi sistemi kurulacak. Bundan sonraki çelik modellerde model verilecek, liste aynı sistemle dönecek. Kapsam: tek kat çelik, çift katın üst katı ve çatı ailesi. Canlıya alınacak.

Deneme kodu: `deneme/2026-10-03_yukleme/`. Hesapta LLM yok: aynı girdi her zaman aynı listeyi verir. Buradaki tablolar ve sayılar hesap çıktılarından üretilir (`belge_uret.py`; tablolar `sonuc/tablolar.md`).

## Kaynaklar

1. **Lokman'ın söyledikleri.** 3 Ekim 13:27'de on bir soruya verdiği cevaplar (aşağıda), 4 Ekim 01:24'teki düzeltmesi (tavan ve çatı panelinin ağırlığı), 4 Ekim 01:42'deki düzeltmesi (baz kaplama; kırma çatıda kaplama adedinin çatı açılımından bulunması), 4 Ekim 15:18'de altı soruya, 16:18'de üç soruya ve 17:46'da iki soruya verdiği cevaplar, 7 Ekim 07:45'te kör testin on iki sorusuna verdiği cevaplar ile 08:02'deki beş düzeltmesi, 8 Ekim 00:45'te dokuz soruya ve 07:23'te üç soruya verdiği cevaplar, 9 Ekim 22:22'de ikinci kör testin dört sorusuna verdiği cevaplar (hepsi aşağıda) ve önceki kurallar. Lokman'ın söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerlidir (15:18: en iyi bilgiyi kendisi verecek).
2. **Mühendisin cevapları.** PortatifEv'in inşaat mühendisi Ubeydullah'ın üç tur cevabı: 3 Ekim 14:50 sürümündeki yedi soruya (Lokman 3 Ekim 18:14'te iletti), 19:12 sürümündeki yedi soruya (Lokman 4 Ekim 01:24'te iletti) ve 4 Ekim 02:58 sürümündeki on iki soruya (Lokman 4 Ekim 12:14'te iletti). Üçü de aşağıda. Kurallarda durumu `muhendis`. İkinci turun iki cevabını (baz kaplama; kırma çatıda kaplama adedi) Lokman 01:42'de düzeltti. Üçüncü turun mesajında cevapların kimden olduğu yazmıyor; 11. cevaptaki anlatım mühendisin olduğu için on iki cevap da mühendisin sayıldı.
3. **Gerçek yükleme listeleri.** Lokman'ın bağladığı klasördeki çalışma kitapları. Üçü hesap sayfalarıyla okundu. Üçünde de çatı yöntem B ile (tavan omegası, aşık, saçak sacı) hazırlanmış: PortatifEv bugüne kadar çelikte de bu yöntemi uygulamış. Şimdi baz alınan yöntem A için karşılaştırılacak gerçek liste yok.
   - **90 m²**, beşik çatı, OSB üstü metal kiremit, karkas 80 mm (30 Eylül 2025).
   - **62 m²**, kırma çatı, sandviç panel, dış karkas 140 mm, verandalı (19 Eylül 2025). Ç8201'e en yakın örnek.
   - **105 m²**, beşik + cumba çatı, tek kat panel, dış karkas 140 mm (dosya tarihi 26 Kasım 2025; 11 Kasım tarihli önceki sürümüne de bakıldı).
   - **98,7 m²**, beşik + cumba çatı, sandviç panel, müştemilatlı (Eylül 2026). Kör testte kullanıldı (KT-01): bu belgedeki kurallarla kendi listemiz çıkarıldıktan sonra açıldı. O da yöntem B ile hazırlanmış. Aşağıda "Kör test" bölümü.
   - **90 m²** (ikinci kör test, KT-02), dört omuz çatı, sandviç panel, korkuluklu veranda ve girişte kendi çatısı olan açık sundurma (Ağustos 2026). Model montaj paftasından ve üretim dosyasından (rulo form makinesinin CSV'leri) kuruldu; liste, kendi listemiz donduruluncaya kadar açılmadı. Yöntem B. Aşağıda "Kör test: KT-02" bölümü.
4. **Excel hesaplama motoru** (`CTKBF V1.1`). Lokman, 13:27: "biz Excel'de hesaplama motoru kullanırken…". Sayfaları: müşteri talebi (girdiler), proje detayları, dış ve iç duvar tonajı, çatı tonajı, çatı kaplama malzemesi, pencere, malzemeler (formüller), notlar. Buradan çelik birim ağırlıkları ile listede elle yazılan kalemlerin formülleri alındı. Fiyatlar alınmadı.
5. **Mühendisin 10 × 10 m çatı metrajı** (aynı klasörde; beşik ve dört omuz, yöntem B). Kuralları sınamak için kullanıldı; fiyatlar alınmadı.
6. **Montaj paftaları** (aynı klasörlerde). Lokman'ın 4 Ekim 17:46 mesajı üzerine bulundu ve incelendi: 13 klasörde 84 PDF, proje başına bir ana DWG. Üç gerçek listenin projelerinin paftaları listelerle karşılaştırıldı (aşağıda, 17:46 bölümü). Ayrıntı: `docs/sartname/montaj_paftasi.md`.

Bayi, müşteri ve öteki personel adları alınmadı. Çalışma kitapları depoda değil; Lokman'ın Mac'inde.

## Lokman'ın cevapları (3 Ekim 13:27) ve uygulanışı

| # | Konu | Cevap (özet) | Uygulama |
|---|---|---|---|
| 1 | Çelik kg | Excel motorundaki gibi: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek. İleride Blender eklentisi (şimdi değil). | Duvar kg = duvar boyu × motorun birim ağırlığı. Dikme, kiriş ve makas motorun ortalamasıyla, "şimdilik" notuyla (mühendis, 4 Ekim 12:14: "şimdilik Excel hesaplama motoruna uy"). Tavan ve çatı paneli 100 m² için verilen ağırlıktan, alana oranla (ağırlıklar Lokman'ın 4 Ekim düzeltmesiyle). |
| 2 | Çatı örtüsü | "Çatı kaplaması" seçenektir: tek kat panel, sandviç panel, OSB + nem bariyeri + kiremit desen sac vb.; ötekiler zamanla verilecek. Hafif çelikte normalde makas arasına tavan paneli, üstüne çatı paneli konur; "ama biz prefabrikte kullandığımız metod olan tavan omegası, aşık, alın sacı ve saçak sacı yöntemini uyguluyoruz". İki varyant var; şimdilik çatı ve tavan panelli yöntem baz. | Çatı yöntemi A; kaplama seçenek. Baz pakette tek kat panel (Lokman, 4 Ekim 01:42); motordaki altı kaplama da hesaplanıyor. Lokman 7 Ekim 07:45'te kesinleştirdi: çelikte her çatı tipinde çatı ve tavan paneli; omega ve aşıklı yöntem yalnız prefabrikte (aşağıda). |
| 3 | Veranda kolonu ve kirişi | Kaplanıyor. Her projede sırt 80 mm (çelik karkas), genişlik 30 cm. Bu projede verandanın bütün çerçevesi böyle: kirişler yanlarda ve karşıda; altlarında 240 cm, kiriş gibi dikmeler. | Ç8201: dikme 3 × 240 cm, kiriş 12,38 m; kaplama çevreleri 0,76 ve 0,68 m. Çizime işlendi. |
| 4 | Yeşil alçıpan | Doğru: duvarda ıslak hacim; tavanda ıslak hacim ile veranda tavanı. | O gün hesap değişmedi. Lokman 7 Ekim 07:45'te veranda tavanını ayırdı: çelik yapıda her zaman Boardex, prefabrikte yeşil alçıpan (aşağıda). |
| 5 | Köşebent | Kural olarak bina m² ÷ 2,5; 50 ya da 70 olması çok önemli değil. | Yerini mühendisin plandan hesaplayan formülü aldı (18:14): Ç8201'de 59 (m² ÷ 2,5 ile 33'tü; veranda tavanı eklenmeden önce 51). m² ÷ 2,5 kurallarda yedek olarak duruyor. Lokman, 7 Ekim: köşebent önemli bir detay değil; mevcut kural uygulanır. |
| 6 | Dere inişi | Her köşeye bir; 10 metrelik cephenin ortasına bir daha (14 metrede üç tane konmaz); 82 m²'de toplam 6. | Kural kodda. Ç8201: 6; çatı planında işaretli. Mühendis: iniş plana bakarak yerleştirilir (18:14); elle yerleştirilirse o sayı kullanılır. Lokman, 7 Ekim 07:45: "her saçak köşesine ve çok uzun dere boyarında ortaya 1 tane daha"; eşik artık dere boyuyla ölçülüyor (9 m; 8 Ekim 00:45'te onaylandı). Ç8201'de yine 6. |
| 7 | Bindirme, mahyalar | Saçak, mahya ve alın sacında bindirme hep 30 cm (fire dahil); örnek: "saçak sacı L:2800 ise cephe 10 metre ÷ 2,5". Ters mahya: cumbalı çatıda vadi. Özel mahya: ana bina ile veranda çatısının birleşimi. | O gün: mahya (L 2800) ÷ 2,5 → 11; yöntem B'de saçak ve alın sacı listelerde L 2500 olduğu için ÷ 2,2 (çıkarım); dere sayılmadı, 20 cm'de kaldı. **Lokman 7 Ekim 07:45'te değiştirdi:** "Bindirmeleri 20 cm yap 30 cm banada çok geldi". Şimdi mahya ÷ 2,6 → 11; saçak ve alın sacı ÷ 2,3; dere ÷ 3,8. |
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
- Okuma: cevaptaki "anahtar" tekli anahtar, "priz" tekli priz sayıldı. "En uzak mesafe" o gün motordaki gibi kapalı kısmın köşegeni alınmıştı (Ç8201: 11,34 m). Lokman 7 Ekim 07:45'te kuralı söyledi: sigorta × sigortadan en uzak mesafe. Sigorta kutusu, tanımda yeri yazmıyorsa giriş kapısında sayılır; mesafe oradan kapalı kısmın en uzak köşesine ölçülür (Ç8201: 8,60 m). Motor 3 × 2,5 kabloda uydu prizini de sayıyor, hesap öyle yapıldı (fark 2 m). Buat için oda sayısı planın mahal sayısı alındı (Ç8201: 5). Mühendis üçüncü cevaplarda ikisini de teyit etti: "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli."

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
| 7 | Çatı müdahale kapağı ve mahya bandı listeye girsin mi? | "Çatı müdahale kapağı müşterinin talebine göre ekleniyor. Herhangi bir detay belirtilmemişse yani standart bir pakette çatı müdahale kapağı göndermiyoruz. Mahya bandını ekle." | Mahya bandı eklendi. O gün mahya uzunluğundan hesaplandı (Ç8201'de 3 rulo); üçüncü cevaplardaki formülle 4 rulo. Çatı müdahale kapağı o gün standart listeden çıkarıldı (müşteri isterse eklenirdi). **Lokman 7 Ekim 07:45'te düzeltti:** acil müdahale kapağı her yapıya 1 adet, standart (aşağıda). |

## Lokman'ın ikinci düzeltmesi (4 Ekim 01:42): baz kaplama ve çatı açılımı

Lokman: "mühendis 2 cevapta hata yapmış onları düzeltmem gerekiyor".

1. **Baz kaplama.** "çatıda baz model Tek Kat panel olarak geçiyor". Uygulama: baz paketin çatı kaplaması tek kat panel; Ç8201'in tanımı ve listesi buna göre. Sandviç panel seçenek. O gün 87 cm kapatan panelle hesaplandı; güncel ürün 100 cm kapatıyor (Lokman, 15:18).
2. **Kırma çatıda kaplama adedi.** "biz AutoCAD bulaşmak istemiyoruz"; "sen eğime göre 82 m² olduğu gibi çatıyı çizip sonra çatıyı açman lazım zarfı açar gibi yüzeye dizilimini bulmak için". "çatı formunun çapraz kesimleri diğer tarafa kullanabilirsin": sol taraftaki üçgende kullanılan panel sağ tarafa aynı açıyla; ön taraftaki yamuktan çıkan açılı kesilmiş parçalar arka taraftaki aynı biçimdeki açılı yere.

Uygulama (`deneme/2026-10-03_yukleme/cati_acilim.py`). Taşma mühendisin üçüncü cevaplarıyla (12:14) eklendi; dizilimin başladığı yer, kesim payı, yedek ve kapatma genişlikleri Lokman'ın 15:18 cevaplarıyla kesinleşti; panel boyunun uzatılması 16:18 cevabıyla kural oldu; panel boyu 7 Ekim 07:45 cevabıyla 10 mm'ye yukarı yuvarlanıyor (aşağıdaki bölümler):

- **Açılım.** Çatının dört yüzü gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ). Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Ç8201'de 426,5 cm; saçaklar 1154 ve 810 cm, mahya 344 cm. Kırma çizgisi açılımda dört yüzde de aynı açıdadır.
- **Dizilim.** Her yüz, saçağa dik, kaplamanın kapattığı genişlikte şeritlere bölünür. Dizilim her yüzde, dışarıdan bakışla sol köşeden başlar (Lokman, 4 Ekim 15:18: "her köşeden başlayacak gibi hesapla"); son şerit dar kalabilir. Mahyanın altındaki şeritler tam boydur; kırmaya gelen şeritler çapraz kesilir.
- **Kapatma genişliği.** Ürüne göre değişir (Lokman, 15:18). Güncel: tek kat panel 100, sandviç panel 100 (80 cm kapatanı da var), kiremit desen sac 100, trapez sac 80 cm. 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Girdide `cati.kapatma_m` yazıyorsa o kullanılır.
- **Taşma** (mühendis, 4 Ekim 12:14). Kaplama saçaktan 5 cm dışarı uzatılır. Panel boyunun tabanı = eğimli boy + 5 cm, 10 mm'ye yukarı (Lokman, 7 Ekim 07:45: "yukarı yuvarla"; önce mm'ye yukarıydı): Ç8201'de 4314,8 mm → L 4320 (önce L 4315). Açılımda her parçanın boyu 5 cm artar. Excel motorundaki sac boyu: eğimli boy + 0,05, mm'ye yukarı. Panel boyu gerçek listeden geliyorsa ona dokunulmaz; kısaysa taşma panelin yettiği kadar alınır (62 m² örnekte 3,8 cm).
- **Panel boyu uzatma** (Lokman, 4 Ekim 16:18; pay koşulu 7 Ekim'den beri taban boyda da aranır; 8 Ekim 00:45: boyda 3 cm'e kadar fark tolere edilebilir, hesap kapandı). Boy 1'er cm uzatılarak denenir, en çok 3 cm; adet düşüyorsa ya da taban boyda pay inceyse liste uzun boyu yazar. Taşma değişmez. Ç8201'de 4 Ekim'de L 4315 → L 4325 (27 → 25 adet); şimdi taban L 4320, liste L 4330 × 25. Ayrıntı aşağıda, "Panel boyu uzatma kuralı" başlığında.
- **Artan parça.** Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır. Alt parça olduğu gibi kullanılır. Üst parça, düz ucu saçağa gelecek biçimde karşı yüze konur; orada aynı açılı yere oturur (ön yüzün sol kırması ↔ arka yüzün sol kırması, dışarıdan bakışla; planda çapraz köşeler). Parça ters yüz edilmez. Kiremit desen sacda artan parça kullanılmaz: desen ters gelir (mühendis, 4 Ekim 12:14).
- **Eşleme.** En uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır. İki parçanın birlikte istediği boy: uzun kenarlarının toplamı − bir şeritlik boy farkı + kesim payı.
- **Kesim payı** (Lokman onayladı, 4 Ekim 15:18). 5 mm: çapraz kesimde iki parçanın arasına ve aynı panelden çıkan dikdörtgenlerin arasına.
- **Yedek ve bindirme.** Yedek panel eklenmez: kesim planı montajcıya verilir (Lokman, 15:18). Boy bindirmesi yok (panel tek boyda).
- **Öteki başlangıçlar.** Bilgi için beş başlangıç daha denenir: uzun yüzlerde sol köşeden, kısa yüzlerde ortadan · uzun yüzlerde ortadan, kısa yüzlerde sol köşeden · her yüzde ortadan · her yüzde sağ köşeden · karşılıklı yüzlerde planda aynı uçtan. En az paneli veren dizilim tabloda ayrı sütunda. "Ortadan": yüzün ortasına bir ek yeri gelir, şeritler iki yana eşit dağılır.

Ç8201, tek kat panel: **25 adet L 4330** (10 tam boy + 15 kesilen: 16 kesimden ikişer parça çıkıyor, biri bir yüze, öteki karşı yüze; artığı kullanılmayan kesim yok). Çizimler: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_acilim.png` (açılım; her parçada panel numarası) ve `C8201_cati_kesim.png` (her panelin kesimi); döküm `C8201_cati_acilim.json`; kesim ölçüleri `C8201_cati_kesim_olculeri.md`.

| Çatı | Kaplama | Kapatır | Panel boyu | Adet (her yüzde sol köşeden) | Taban boyla | En az paneli veren dizilimle | Altı başlangıçla | Artan parça kullanılmazsa | Alan olarak en az | Kesim payı sıfır / 1 cm | Taşma |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ç8201 | Tek kat panel (baz paket) | 100 cm | L 4330 | 25 (10 tam boy + 15 kesilen) | 25 (L 4320; pay ince: kesim payı 1 cm olsa 27) | 25 | 25–26 | 28 | 24 | 25 / 25 | 5,0 cm |
| Ç8201 | Sandviç panel | 100 cm | L 4330 | 25 (10 tam boy + 15 kesilen) | 25 (L 4320; pay ince: kesim payı 1 cm olsa 27) | 25 | 25–26 | 28 | 24 | 25 / 25 | 5,0 cm |
| Ç8201 | Trapez sac | 80 cm | L 4330 | 30 (12 tam boy + 18 kesilen) | 30 (L 4320; pay ince: kesim payı 1 cm olsa 32) | 30 | 30–32 | 34 | 29 | 30 / 30 | 5,0 cm |
| Ç8201 | Kiremit desen sac | 100 cm | L 4330 | 28 (10 tam boy + 18 kesilen) | 28 (L 4320; pay ince: kesim payı 1 cm olsa 30) | 28 | 28–29 | 28 (listeye giren) | 24 | 28 / 28 | 5,0 cm |
| Ç8201 | Sandviç panel, 80 cm kapatan ürün | 80 cm | L 4330 | 30 (12 tam boy + 18 kesilen) | 30 (L 4320; pay ince: kesim payı 1 cm olsa 32) | 30 | 30–32 | 34 | 29 | 30 / 30 | 5,0 cm |
| Ç8201 | Tek kat panel, 87 cm kapatan ürün (2025 listeleri) | 87 cm | L 4350 | 28 (12 tam boy + 16 kesilen) | 29 (L 4320) | 28 | 28–29 | 32 | 27 | 28 / 28 | 5,0 cm |
| Ç8201 | Kiremit desen sac, 110 cm kapatan ürün (2025 listeleri) | 110 cm | L 4320 | 26 (10 tam boy + 16 kesilen) | uzatma adedi düşürmüyor | 26 | 26 | 26 (listeye giren) | 22 | 26 / 26 | 5,0 cm |
| 62 m² gerçek liste (listede 27) | Sandviç panel | 100 cm | L 3200 | 28 (16 tam boy + 12 kesilen) | boy listeden | 28 | 28 | 32 | 25 | 28 / 28 | 3,8 cm |
| Mühendisin 10 × 10 m dört omuz metrajı (metrajda 36) | Trapez sac | 80 cm | L 5900 | 28 (4 tam boy + 24 kesilen) | boy listeden | 28 | 28 | 32 | 26 | 28 / 28 | 5,0 cm |

Okuma:

- **Sağlama.** Aynı kural, bu koda bakmadan ayrıca hesaplandı (bağımsız denetim, 4 Ekim; 16:18 cevabından sonra yeniden). O günkü durumda (taban L 4315) panel boyu uzatma kuralı beş durumda uygulandı: 100 cm kapatma; 80 cm; 100 cm ve artan parça kullanılmadan; 87 cm; 110 cm ve artan parça kullanılmadan. Seçilen boylar 4,325 · 4,325 · 4,325 · 4,345 · 4,315 m, adetler 25 · 30 · 28 · 28 · 26 (taban boyla 27 · 32 · 30 · 29 · 26): hepsi aynı çıktı. Tek kat panelde 25'in bu şerit dizilimi için en az olduğu gösterildi (hiçbir ikilisi aynı panele sığmayan 25 parça var); adedin düştüğü en kısa boy 4,318 m. Önceki turlarda 90 adet (beş örnek × altı başlangıç × üç kesim payı) ve 16:13 sürümünün adetleri de aynı çıkmıştı. 7 Ekim'de, yuvarlama ve pay koşulundan sonra yeniden: ayrı bir oturum bu koda ve çıktılara bakmadan beş durumu altı panel boyunda (L 4315–L 4350) ve iki kesim payında (5 mm, 1 cm) hesapladı; 60 adedin hepsi, kuralın seçtiği boylar (4,330 · 4,330 · 4,330 · 4,350 · 4,320 m) ve adetler (25 · 30 · 28 · 28 · 26) aynı çıktı. Tek kat panelde adedin aynı kaldığı en büyük kesim payı L 4320'de 7,8 mm, L 4330'da 17,8 mm bulundu. L 4330'da 25'in bu şerit dizilimi ve kesim kuralı için en az olduğu gösterildi (hiçbir ikilisi aynı panele giremeyen 25 parça var; alan olarak alt sınır 24). Her paneldeki parçaların panele sığdığı, üst üste binmediği ve yüzdeki yerine tam oturduğu çokgenlerle sınanıyor (`cati_acilim_saglama.py`; rastgele 120 kırma çatıda, 1440 dizilimde sorun çıkmadı; uzatma kuralı 450 çatı ve kaplamada denendi: 4 Ekim kuralıyla 34'ünde, şimdiki kuralla 37'sinde boy uzadı, bunların 13'ünde pay koşulundan; kural bilerek bozulunca sınama yakalıyor). Çizim, ölçü tablosu ve sınama aynı yerleşimi kullanıyor.
- **Tek kat panel (baz paket).** 25 adet (10 tam boy + 15 kesilen); altı başlangıçla 25–26; kesim payı sıfır da olsa 1 cm de olsa aynı; panel boyu L 4320 → L 4330 (pay kalsın diye: taban boyla da 25 çıkıyor, ama kesim payı 7,8 mm'yi geçerse 27 gerekir).
- **Sandviç panel.** 25 adet (10 tam boy + 15 kesilen); altı başlangıçla 25–26; kesim payı sıfır da olsa 1 cm de olsa aynı; panel boyu L 4320 → L 4330 (pay kalsın diye: taban boyla da 25 çıkıyor, ama kesim payı 7,8 mm'yi geçerse 27 gerekir).
- **Trapez sac.** 30 adet (12 tam boy + 18 kesilen); altı başlangıçla 30–32; kesim payı sıfır da olsa 1 cm de olsa aynı; panel boyu L 4320 → L 4330 (pay kalsın diye: taban boyla da 30 çıkıyor, ama kesim payı 7,8 mm'yi geçerse 32 gerekir).
- **Kiremit desen sac.** 28 adet (10 tam boy + 18 kesilen); altı başlangıçla 28–29; kesim payı sıfır da olsa 1 cm de olsa aynı; panel boyu L 4320 → L 4330 (pay kalsın diye: taban boyla da 28 çıkıyor, ama kesim payı 7,8 mm'yi geçerse 30 gerekir); artan parça kullanılmıyor (desen ters gelir: mühendis, 4 Ekim 12:14).
- **Panel boyu.** 4 Ekim'de kuralla L 4315 → L 4325 (Lokman, 16:18): taban boyla tek kat panel 27 gerekiyordu. 7 Ekim'de taban 10 mm'ye yukarı yuvarlanınca L 4320 oldu: L 4320 ile de 25 çıkıyor, ama pay ince (kesim payı 7,8 mm'yi geçerse 27); bu yüzden liste L 4330 yazıyor (aşağıda "Panel boyu uzatma kuralı").
- **Sürümler.** 02:58 (taşma ve kesim payı yok; L 4300; tek kat panel 87, kiremit desen sac 110 cm): tek kat panel 28, sandviç panel 24, trapez sac 30, kiremit desen sac 26. 13:22 (taşma 5 cm, kesim payı 5 mm, en az paneli veren başlangıç): 28, 26, 32, 26. 16:13 (her yüzde sol köşeden; tek kat panel ve kiremit desen sac 100 cm; L 4315): 27, 27, 32, 30. 16:18 (panel boyu uzatma kuralıyla L 4325): 25, 25, 30, 28. Şimdi (7 Ekim: boy 10 mm'ye yukarı, pay koşulu taban boyda da; L 4330): 25, 25, 30, 28.
- **Önceki kural** (yüzey + %10, taban panel boyu ve güncel kapatma genişlikleriyle): tek kat panelde 26, sandviç panelde 26, trapez sacda 32, kiremit desen sacda 26 verir.
- **62 m² gerçek liste** (kırma çatı, sandviç panel L 3200): listede 27 adet (ayrıca 2 adet L 1000); dizilim 28 veriyor (02:58 sürümünde, taşmasız, 26'ydı). Listedeki 27 uzun ve 2 kısa panel alan olarak 27,6 panel eder. Kısa panellerin köşe parçaları için gönderilip gönderilmediği bilinmiyor.
- **Mühendisin 10 × 10 m dört omuz metrajı** (trapez sac L 5900): metrajda 36 adet var; dizilim tablonun son satırındaki adedi veriyor. Çatı planı saçak dahil 10,6 × 10,6 m ve eğim %33 alındı; yüzey metrajdaki 118 m²'yi tutuyor.
- **Dar yerler** (bağımsız denetimin notları). Panel boyu yuvarlanıp uzatılınca tam boy parçalarda 1,5 cm fazlalık olur: mahya ucunda kalır ya da kesilir; kesilmezse o şeritlerde taşma artar. İki saçağın taşmalarının kesiştiği köşe (yaklaşık 5 × 5 cm) örtülmez: parçalar uzuyor, genişlemiyor. Kesim payı panel boyu yönünde ölçülüyor: çapraz kesim yaklaşık 46° olduğu için boyda 5 mm, 3,4 mm kalınlığında bir kesime denk gelir. Boyuna kesimin (dar son şerit) payı hesapta yok.
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
| 6 | Köşebent: çıkıntı yapan köşeler ve veranda tavanı sayılır mı? | "Odaya doğru çıkıntı yapan köşeler sayılmıyor. Veranda tavan çevresi sayılır." | Veranda tavanının çevresi (19,88 m; brüt ölçüyle) eklendi: 51 → 59. Çıkıntı yapan 1 köşe sayılmıyor. Verandada köşe boyu eklenmedi. Buna bağlı trapez vida (5,5 × 25) 1000 → 1000. |
| 7 | Elektrik: buat için hangi odalar? Yatak odası ve banyodaki prizler tekli mi? | "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli." | İkisi de zaten öyleydi: oda sayısı 5, buat kasa 31. Hesap değişmedi. |
| 8 | Mahya bandı: mahya uzunluğundan mı, parça adedinden mi? | "Mahya bandı şu şekilde hesaplanır: “(Mahya Adedi * 2,8 (metre) + Ters Mahya Adedi * 2,8 (metre) + Damlalık adedi * 2,5 (metre))/10” şeklinde bulunur." | (11 × 2,8 + 0 + 0) ÷ 10 → 3 yerine 4 rulo. Damlalık okunan listelerde yok; sıfır alındı. Lokman 15:18'de damlalığı listeden tamamen çıkardı. Trapez sac seçeneklerinde motordaki gibi trapez sac mahyası × 0,8 m toplanır. |
| 9 | Dış kapı: 100 mü, 95 mi? | "Dış kapı boşluğu 95x210, iç oda kapı boşluğu 90x214 alınır." | Tanımda dış kapı boşluğu 100 → 95 cm (ekseni yerinde kaldı); plan ve paftalar yeniden çizildi. Liste hesabı zaten 95 × 210 ile yapılıyordu. |
| 10 | Boardex ve OSB kalınlığı; Boardex zayiatı | "Boardex 12.5 mm. OSB 11 mm. Boardex zayiatı %8." | Satırların boyutu 12,5 × 1200 × 2400 ve 11 × 1220 × 2440 oldu. Boardex zayiatı %15 → %8: dış cephe Boardex 33 → 31; saçak altı ve saçak yüzü aynı (5 ve 3). 2025 listelerindeki adetler %15'e uyuyor (aşağıda). Lokman 7 Ekim 07:45'te 12,5 mm'yi teyit etti: listelerdeki 8 mm hatalı girilmiş (aşağıda). |
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
| Ç8201 (K10 8,50; K11 7,50; K17 2,44; dört omuz) | 93,31 ÷ 4,315 = 21,63 | 19 → 29 | 25 → 22 | Çatı açılımı trapez sacda 30, kiremit desen sacda 28 veriyor (artan parça kullanılmadan). Motor tek kat panelde 23 verir; açılım 25. Kiremit desen sac 100 cm kapatırken motorun doğru formülü 23 verir |

Motorun sac boyu Ç8201'de 4315 mm: eğimli boy + taşma, mm'ye yukarı. Liste bunu 10 mm'ye yukarı yuvarlıyor (L 4320; Lokman, 7 Ekim 07:45) ve pay kalsın diye L 4330 yazıyor (aşağıda "Panel boyu uzatma kuralı"). Yükleme listesi kaplama adedini bu formülden almıyor; kırma çatıda çatı açılımından alıyor. Bulgular motorun kendisi için.

## Lokman'ın cevapları (4 Ekim 15:18) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 13:22 sürümündeki altı soruydu. Cevaplar tırnak içinde, yazıldığı gibi. Lokman ayrıca en iyi bilgiyi kendisinin vereceğini söyledi: onun söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerli sayılır.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Çatı dizilimi: nereden başlar, kesim payı, yedek | "her köşeden başlayacak gibi hesapla yani 29 hesapla, evet kesim payı için 5 mm uygundur, senin yaptığın kesim planı ile yedek panele gerek yok bizde aynı kesim plan paftasını montajcıya vereceğiz" | Dizilim her yüzde sol köşeden başlıyor; kesim payı 5 mm ve yedeksiz adet kesinleşti. 29, 87 cm kapatan panelle çıkan adetti; 2. cevapla panel 100 cm kapatır olunca aynı kural **27** veriyor (16:18'den sonra panel boyu uzatılınca 25; aşağıda). Lokman 15:23'te teyit etti: "yok yanlış anlamadın aynen devam et". Açılım ve kesim planı yeniden çizildi; kesim ölçüleri tablosu eklendi. |
| 2 | Kapatma genişliği: tek kat panel 87 mi, 100 mü; kiremit desen sac 110 mu, 105 mi? | "aslında aldığımız ürünler değişiyor güncel olarak Tek Kat panelde 100 kapatır geliyor, kiremit desen sacıda 100 al sandviç panelde şimdilik 100 al ama 80 kapatırıda var bu bilgiyi daha sonra güncellenecek gibi hesaba kat" | Kurallarda tek kat panel 0,87 → 1,00; kiremit desen sac 1,10 → 1,00; sandviç panel 1,00 (80 cm kapatan ürün not edildi). Değerler ürüne göre değişir: girdide `cati.kapatma_m` yazıyorsa o kullanılır; üç gerçek liste örneği kendi ürünlerinin genişliğiyle (110, 100 ve 87 cm) hesaplanmaya devam ediyor, karşılaştırma o gün değişmedi (74 / 119). Seçeneklerde sandviç panel 26 → 27, kiremit desen sac 26 → 30; sandviç panelin 80 cm kapatanıyla 32. |
| 3 | Boardex zayiatı %8 ile 2025 listelerinden az | "devam et" | %8 ile devam: dış cephe Boardex 31. |
| 4 | Damlalık hangi durumda listeye girer? | "damlalık uygulamasını yanlış buluyorum tamamen listeden çıkar, orijinal kapama aparatı var plastik ondan sipariş verirsek listeye sokarız damlalığı şimdilik çıkar hiçbir montajcı kullanmıyor" | Damlalık listede kalem olarak yoktu; mahya bandı formülündeki terimi çıkarıldı, adet değişmedi (4 rulo). Plastik kapama aparatı kurallara not edildi (`kapama_aparati`); sipariş verilirse listeye girecek. Listedeki "tek kat panel kapaması" (L 2500, 18 adet; 2025 listelerinden) o gün duruyordu: Excel motorunda damlalıktan ayrı kalem. Soruldu; Lokman 16:18'de onu da çıkardı (aşağıda). |
| 5 | Klima duvarı OSB takviyesinde sayılır mı? | "sen ilk seferdeki gibi say bayi maliyeti de göz önüne alıyor bunu bayiye belirtmem lazım şimdilik hangisi az ise onu baz al" | Okuma: iki hesap yapılır, az olan baz alınır. Yalnız dolap ve TV duvarları: 24,5 m² → 9 levha (baz). Odanın bütün yüzeyi (ilk hesap; Lokman'ın 3 Ekim 13:27 kuralı): 42,5 m² → 15 levha; satırın notunda, bayiye belirtilmek üzere. Klima duvarı baz hesapta sayılmıyor. Okumanın teyidi istendi; Lokman 16:18'de geçerli kuralı söyledi (aşağıda). |
| 6 | Makas ve kiriş ölçüsü | "Tamam motoruda inceleyeceğim şimdilik motoru kastas al" | Çatı çeliği, veranda dikmeleri ve kirişleri Excel motorunun ortalamasıyla kalıyor: 706, 46 ve 81 kg. Lokman motoru inceleyecek. |

### Kesim planının ölçüleri

Kesim planı montajcıya verilecek (Lokman, 15:18). Çizimde ölçü yazmadığı için ölçüler ayrı bir dökümde: `deneme/2026-10-03_yukleme/sonuc/C8201_cati_kesim_olculeri.md` (`cati_acilim.py --olcu-md`). İçinde üç tablo var:

- **Parçalar.** Yüz yüz, soldan sağa her şerit parçası: saçaktaki yeri, eni, sol ve sağ kenar boyu (saçak ucundan, taşma dahil), köşesi kesilen tam boy panelde aradaki kırık noktası, çıktığı panel.
- **Kesim ölçüleri.** Panel panel her parçanın paneldeki yeri: panelin sol ve sağ kenarında alt uçtan kaç cm ile kaç cm arası. Üst parça 180° çevrilerek karşı yüze konur; ters yüz edilmez.
- **Paneller.** Her panelden çıkan parçalar ve kullanılmayan boy.

Çizim, bu tablolar ve geometrik sağlama aynı yerleşimden üretilir. Ölçüler kaplamanın kapattığı genişliğe göredir; panelin bindirme payı ayrıca düşünülmedi. Panel boyu yuvarlandığı ve uzatıldığı için (4 Ekim 16:18; 7 Ekim) tam boy panellerde 1,5 cm kullanılmayan boy görünür: panelin üst ucunda, mahya ucunda kalır.

## Lokman'ın cevapları (4 Ekim 16:18) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 16:13 sürümündeki ilk üç soruydu. Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Panel boyu: 1 cm uzun sipariş edelim mi? Kural yapayım mı: panel boyu en çok 3 cm uzatılınca adet düşüyorsa liste uzun boyu yazsın? | "evet 1. yi kural yap çok mantıklı bir çıkarım da bulunmuşsun tebrik ederim" | Kural yazıldı (`panel_boyu_uzatma`; aşağıda). Ç8201'de o gün: tek kat panel L 4315 × 27 → **L 4325 × 25**. Seçeneklerde sandviç panel 27 → 25, trapez sac 32 → 30, kiremit desen sac 30 → 28. Açılım, kesim planı ve kesim ölçüleri yeniden üretildi. 7 Ekim'den beri liste L 4330 × 25 yazıyor (aşağıda). |
| 2 | OSB takviyesi: doğru mu anladım (az olan 9 levha listede, 15 levha notta)? | "evet 9 sayısını veren hangisi ise o kuralı geçerli say" | Geçerli kural: yalnız dolap ve TV ünitesi gelen duvarlar (9 levha). "Az olan baz" uygulaması kalktı; odanın bütün yüzeyi (15 levha) yalnız bilgi olarak satırın notunda duruyor (15:18: bayiye belirtilecek). Kuralın durumu `lokman`. Klima duvarı sayılmaz. Adet değişmedi. |
| 3 | Sac kapama: o da çıksın mı (tek kat panel kapaması, L 2500, 18 adet)? | "evet tek kat panel kapasınıda çıkar aynısı geçerli" | Tek kat panel kapaması listeden çıktı (`panel_kapamasi`): liste 89 → 88 satır. Plastik kapama aparatı sipariş verilirse listeye girecek. Sandviç panel seçeneğindeki sac kapama için cevap yoktu: soruldu; Lokman 17:46'da cevapladı (aşağıda): şimdilik kalıyor. Kapaması olan 2025 listesi örneği (105 m²) kendi uygulamasıyla hesaplanıyor (`cati.panel_kapamasi`); karşılaştırma o gün değişmedi (74 / 119). |

### Panel boyu uzatma kuralı

- **Taban boy.** Eğimli boy + taşma (mühendis, 4 Ekim 12:14; Excel motorundaki sac boyu). 4 Ekim'de mm'ye yukarı yuvarlanıyordu: Ç8201'de L 4315. 7 Ekim'den beri 10 mm'ye yukarı (Lokman, 07:45): L 4320.
- **Neden** (4 Ekim). L 4315 ile en uzun kesik parça ve köşe parçası aynı panelden çıkmıyor: ikisi birlikte 4 × 105,3 + 2 × 5 + 0,5 = 431,7 cm ister; panel 431,5 cm, 2,2 mm eksik. 2. ve 3. şeritlerin eşleşmesi de aynı boyu ister. Bu yüzden o boyda her yüzün 4. şeridi bir paneli tek başına harcıyordu (4 panel).
- **Kural** (Lokman, 4 Ekim 16:18). Boy 1'er cm uzatılarak denenir, en çok 3 cm. Adet düşüyorsa liste o boyu yazar; birden çok boy düşürüyorsa en az adedi veren, eşitlikte en kısası alınır.
- **Pay koşulu** (uygulama ayrıntısı; öneride "pay kalsın diye L 4325" denmişti). Aday boyda adet, kesim payı 1 cm'ye çıksa da aynı kalmalı; kalmıyorsa o boy aday sayılmaz. 4 Ekim'de adedin düştüğü en kısa boy L 4318'di; L 4325 kesim payı 12,8 mm'ye kadar 25 veriyordu.
- **Pay koşulu taban boyda da** (7 Ekim; Claude'un uygulama ayrıntısı; Lokman, 8 Ekim 00:45: "3 cm'e kadar +- tolere edilebilir", hesap kapandı; kurallarda `panel_boyu_uzatma.taban_icin_de`). Yukarı yuvarlanınca taban L 4320 oldu. L 4320 ile de 25 panel çıkıyor, ama pay ince: aynı iki parça 431,7 cm istiyor, panel 432,0 cm; 2,8 mm kalıyor. Kesim payı 7,8 mm'yi geçerse ya da panel 3 mm kısa gelirse 27 panel gerekir. Üretici kataloglarında sandviç panelin boy toleransı, 3 m'den uzun panelde ± 10 mm yazıyor (PortatifEv'in tedarikçisininki sorulmadı). Bu yüzden koşul taban boy için de aranır: taban boyda adet, kesim payı 1 cm'ye çıkınca artıyorsa boy 1'er cm uzatılır (en çok 3 cm) ve adedi artırmadan koşulu sağlayan en kısa boy alınır. Ç8201: **L 4330 × 25**; kesim payı 17,8 mm'ye kadar 25, yani panel 10 mm kısa gelse de yetiyor. Bedeli: 25 panelde birer cm (0,25 m panel). Kuraldan `taban_icin_de` silinirse liste L 4320 × 25 yazar.
- **Taşma değişmez.** Parçalar uzamaz, panel uzar: tam boy giden 10 panelde 1,5 cm fazlalık mahya ucunda kalır ya da kesilir (kesilmezse o şeritlerde taşma 6,5 cm olur).
- **Kapsam.** Yalnız panel boyu kuraldan geldiğinde uygulanır (girdide `cati.panel_boyu_kaynak: kural`); boyu gerçek listeden gelen örneklerde uygulanmaz. Hesap deterministik: aynı çatı ve kaplama aynı boyu verir.

| Kaplama | 4 Ekim: taban L 4315 ile | 4 Ekim: kuralla | 7 Ekim: taban L 4320 ile (kesim payı 5 mm / 1 cm) | 7 Ekim: listede | Toplam boy |
|---|---|---|---|---|---|
| Tek kat panel ve sandviç panel (100 cm) | 27 | L 4325 × 25 | 25 / 27 | L 4330 × 25 | 108,3 m |
| Trapez sac ve 80 cm kapatan sandviç panel | 32 | L 4325 × 30 | 30 / 32 | L 4330 × 30 | 129,9 m |
| Kiremit desen sac (100 cm; artan parça kullanılmaz) | 30 | L 4325 × 28 | 28 / 30 | L 4330 × 28 | 121,2 m |
| Tek kat panel, 87 cm kapatan ürün (2025 listeleri) | 29 | L 4345 × 28 | 29 / 29 | L 4350 × 28 | 121,8 m |
| Kiremit desen sac, 110 cm kapatan ürün (2025 listeleri) | 26 | uzatma adedi düşürmüyor: L 4315 × 26 | 26 / 26 | L 4320 × 26 | 112,3 m |

- İlk üç satırda adet 4 Ekim'dekiyle aynı; değişen yalnız boy (L 4325 → L 4330). 87 cm'lik üründe L 4340 ile de 28 çıkıyor ama pay koşulunu sağlamıyor; kural L 4350 alıyor.
- 4 Ekim'de: kesim payı 2,8 mm ve altında kalsaydı L 4315 ile de 25 çıkardı; liste buna güvenmedi, boyu uzattı. Şimdi aynı mantık L 4320 için: 25 panel, kesim payı 7,8 mm'yi geçmedikçe çıkıyor; liste buna da güvenmiyor.
- Sağlama: 4 Ekim'de bağımsız hesap beş durumda aynı boyları ve adetleri buldu (o günkü kuralla). Şimdiki kuralla çokgen sınaması rastgele 450 çatı ve kaplamada yeniden koştu: 37'sinde boy uzadı, 13'ünde pay koşulundan; sorun yok. Bağımsız hesap 7 Ekim'de yenilendi: beş durumda aynı boylar ve adetler (yukarıda, "Sağlama").

## Lokman'ın cevapları (4 Ekim 17:46) ve uygulanışı

Sorular, liste sayfasının 4 Ekim 16:54 sürümündeki ilk iki soruydu. Cevaplar tırnak içinde, yazıldığı gibi.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Sandviç panel kapaması: o da çıksın mı? | "o kalsın şimdilik" | Sandviç panel seçeneğinde sac kapama duruyor (L 2500, 18 adet). Kuralın değeri değişmedi, kaynağı yazıldı (`panel_kapamasi`). Adet formülü o gün 2025 listelerindendi (her saçak kenarı ÷ 2,5; uydurma); 7 Ekim'de Lokman'ın tarifinden yeniden yazıldı (dere boyu ÷ 2,3; aşağıda): Ç8201'de yine 18 adet. Bir çift kat çelik projenin çatı kaplaması paftasındaki metrajda da kalem var: "Sandviç Panel Kapak L saç: 20 m" (iki ana yüzde onar şerit × 100 cm: kapama saçak boyunca). Baz listede sayı değişmedi. |
| 2 | Kesim planı paftası: açılımı, kesim planını ve ölçüleri tek bir PDF paftada toplayayım mı? | "BOM dan sonra montaj paftası için ayrı çalışacağız klasörleri dolaş ve montaj paftalarını bul ne demek istediğimi anlarsın" | Pafta şimdi hazırlanmıyor: montaj paftası, yükleme listesinden sonra ayrı bir iş. Klasörlerdeki montaj paftaları bulundu ve incelendi (`docs/sartname/montaj_paftasi.md`). Montaj paftası tek bir çizim değil; proje başına hazırlanan, ortak çerçeveli bir pafta seti. Ç8201 için üretilen açılım ve kesim planı, o setteki "çatı kaplaması yerleşim planı" paftasının kırma çatıdaki karşılığı. |

Bu turda hiçbir kuralın değeri ve listedeki hiçbir sayı değişmedi; kaynak notları eklendi.

### Montaj paftalarının yükleme listesiyle bağı

Üç gerçek listenin projelerinin paftaları listelerle karşılaştırıldı: 62 ve 90 m² projelerde ana DWG (parça boyları "Omega ve Aşık" ölçü stiliyle yazılmış), 105 m² projede PDF paftalar. "En az boy": paftadaki parçaların stok boya (omega 365, aşık 410 cm) en iyi yerleşimi; kesim payı sayılmadı; boydan uzun iki ölçü (105 m² aşık) tam boy ve artan parça diye bölündü.

| Kalem | Proje | Paftada | Listede | Hesap |
|---|---|---|---|---|
| Çatı kaplaması | 62 m² (kırma, sandviç panel) | 27 adet L 3200 + 2 adet L 1000 | 27 (+ 2 kısa) | 28 |
| Çatı kaplaması | 105 m² (beşik, tek kat panel 87 cm) | 24 adet L 3000 + 30 adet L 2800 | 24 + 30 | karşılaştırmada yok |
| Çatı OSB | 90 m² (beşik) | 39 adet (244 × 122) | 39 | 39 |
| Metal kiremit | 90 m² (beşik) | 28 adet L 3450 + 2 adet L 3000 | 30 | 30 |
| Dere inişi | 62 m² | 7 işaret | 7 | 6 |
| Dere inişi | 90 m² | 8 işaret | 7 | 6 |
| Dere inişi | 105 m² | 10 işaret | 10 | listeden alındı |
| Tavan omegası | 62 m² | 29 parça, 80,5 m; en az boy 25 | 26 | 26 |
| Tavan omegası | 90 m² | 50 parça, 130,2 m; en az boy 39 | 40 | 37 |
| Tavan omegası | 105 m² | 53 parça, 144,9 m; en az boy 43 | 44 | 42 |
| Aşık | 62 m² | 54 parça, 155,6 m; en az boy 39 | 41 | 41 |
| Aşık | 90 m² | 62 parça, 218,4 m; en az boy 55 | 57 | 56 |
| Aşık | 105 m² | 75 parça, 276,3 m; en az boy 71 | 71 | karşılaştırmada yok |

Okuma:

- **Listelerdeki dizilime bağlı sayılar paftadan geliyor.** Çatı kaplamasının adedi ve boyu üç projede de paftadakinin aynısı; iniş sayısı 62 ve 105 m² projelerde paftadaki işaret sayısı. Elektrik sayımı için motorun notu da öyle diyor ("montaj paftasından sayılır").
- **Çatı kaplaması.** Pafta her yüzü şeritlere bölüp boy ve adet yazıyor; çatı alanını ve kaplama alanını da (62 m²: 77,5 ve 88,5 m²; 105 m²: 124 ve 135 m²). İncelenen sekiz çatı kaplaması paftasının hepsi beşik çatıda. Kırma çatılı tek projede (62 m²) pafta yalnız DWG'de ve dört yüz dikdörtgen çizilmiş: çapraz kesim ve artan parçanın karşı yüzde kullanılması paftada yok. Ç8201'in açılımı ve kesim planı bu boşluğu dolduruyor.
- **Dere inişi.** 62 m² projede 7 iniş işareti var: dört köşe, arka cephede bir tane (ortaya yakın: köşelerden 655 ve 554 cm) ve giriş saçağının iki ön köşesi; ön cephenin ortasında yok. Liste de 7; kural dört köşe ve iki orta sayarak 6 veriyor. 90 m² projede (beşik çatı) 8 işaret var: üç saçak çizgisinin (iki uzun saçak ve verandanın kademeli kısa saçağı) uçlarında altı, iki uzun saçağın ortasına yakın iki; kısa saçağın iç köşedeki ucundaki işaret çizginin üzerinde değil, yanında. Liste 7, kural 6. Köşe, saçak çizgisinin bütün dış köşeleri olarak sayılırsa iki listedeki 7 çıkıyor (62 m²: altı dış köşe + arka cephe; 90 m²: beş dış köşe + iki orta). O gün kural değiştirilmedi; Lokman'a soruldu. Lokman 7 Ekim 07:45'te cevapladı: her saçak köşesine bir, çok uzun dere boylarında ortaya bir tane daha (aşağıda). Örnek girdilerde saçak çizgisi yok, dört köşe sayılıyor: 62 ve 90 m² projelerde karşılaştırma 6 / 7 görünmeye devam ediyor.
- **Tavan omegası.** Üç projede de listedeki adet, paftadaki parçaların en az boyundan bir fazla (25 + 1 = 26 · 39 + 1 = 40 · 43 + 1 = 44). Alan formülümüz 26 · 37 · 42 veriyor. Omega hatları 60,0 cm aralıklı (62 ve 90 m² projelerde ölçüldü).
- **Aşık.** Hatlar 60,0 cm aralıklı (62 ve 90 m² projelerde ölçüldü; 62 m² proje sandviç panelli), mahya aşığı 20 cm'de. Listedeki adet ile paftadaki en az boy arasında sabit bir fark yok (39 / 41 · 55 / 57 · 71 / 71).
- **Öteki izler.** Duvar panelleri paftasında "Dış duvarlarda çift kat izolasyon malzemesi kullanılacaktır" (105 m², dış karkas 140 mm: `yalitim_kat` kuralıyla aynı). Çerçevede "Saçak çıkması: 30 cm / saçak sacı üzerinde boardex" (62 m²: açık sorulardaki "iki yöntem aynı listede" için ipucu). OSB kaplama paftasında dolap ve TV arkası duvarlar işaretli (105 m²: üç duvar, 330 + 820 + 436 cm, brüt 42,8 m²; listede net 39,3 m², 15 levha). Çatı kaplaması paftasında "çatı izolasyonu: çift serim" (105 m²; listede şilte çift kat).
- **Makas aralığı.** Makas ve dere paftalarındaki 117 cm, makaslar arasındaki net açıklık (90 ve 105 m² projeler); makas 8 cm çizilmiş, eksen aralığı 125 cm (SketchUp modellerinde ölçülenle aynı; `skp_olcumleri.md`).
- **Sağlama.** Sayım, bu hesabı ve sonuçlarını görmeyen ayrı bir Claude oturumuna yeniden yaptırıldı (bağımsız denetim, 4 Ekim): parça sayıları, toplam boylar, en az boy sayıları, iniş işaretlerinin sayısı ve yeri, kaplama yazıları ve hat aralıkları aynı çıktı. En az boyun gerçekten en az olduğu alt sınırla gösterildi (yarım boydan uzun parçalar aynı boya giremez). 105 m² aşık paftasında saçak sırasındaki iki ölçü parça sayılmazsa en az boy 71 yerine 69 olur; öteki sayılar bundan etkilenmez.
- **Sonuç.** Omega ve aşık dizilimi (hatlar ve parça boyları) montaj paftası çalışmasında kurulacak; adet o zaman dizilimden sayılır, çatı kaplamasında yapıldığı gibi. O zamana kadar formüller duruyor. Ç8201'in baz listesinde (yöntem A) tavan omegası ve aşık yok; bu fark yalnız yöntem B'yi ilgilendiriyor. 7 Ekim: çelikte omega ve aşık artık hiç yok (Lokman, 07:45); dizilim işi prefabrik çalışılınca yapılacak.

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
- **Kalınlıklar** (muhendis, 4 Ekim 12:14; lokman, 7 Ekim 07:45). Boardex 12,5 mm; OSB 11 mm. 2025 listelerinde ve Eylül 2026 listesinde Boardex 8 mm, 2025 listelerinde OSB 9 mm yazıyor; motorda Boardex 8 mm, OSB 11 mm. Lokman, 7 Ekim: doğrusu 12,5 mm, 8 mm hatalı girilmiş; "resmi belgelerinde yazıyor". Kontrol edildi: üreticinin dış cephe levhasının performans beyanında kalınlık 12,5 mm; sistem kitabında 12,5 ve 15 mm; 8 mm yok. Çatı şiltesi 80 mm (lokman, 7 Ekim; listelerdeki 100 mm hatalı girilmiş).
- **İç cephe** (excel). Odalar "beyaz" ve "yeşil" diye ayrılır. Oda oda: iç çevre × kat yüksekliği − o odadaki boşluklar. Alçıpan = net × 1,05 ÷ (1,2 × 2,5). Tavan alçıpanı = tavan alanı × 1,05 ÷ 3,0; yeşil tavan yalnız ıslak hacim.
- **Veranda tavanı** (lokman, 7 Ekim 07:45). Çelik konstrüksiyon binada her zaman Boardex, prefabrikte yeşil alçıpan. Boardex = veranda tavanı (dış ölçüyle) × 1,08 ÷ 2,88; ayrı satır. Ç8201: 18,3 m² → 7 levha; yeşil tavan alçıpanı 8 → 2. Önceki kuralda veranda tavanı yeşil alçıpandı (Lokman, 3 Ekim 13:27).
- **OSB takviyesi** (lokman; ilk kez muhendis). Yalnız dolap ve TV ünitesi gelen duvarlar: modelin tanımında yazılır. Her duvarın o odaya bakan yüzünün boyu × kat yüksekliği − o yüzdeki boşluklar; × 1,05 ÷ 2,98. Duvarın tamamı alınır (Lokman: "tüm yüzeyini"; mühendis, 4 Ekim 12:14: "Duvarın tamamını al."). Geçerli kural bu (Lokman, 4 Ekim 16:18: "9 sayısını veren hangisi ise o kuralı geçerli say"). Odanın bütün yüzeyi (Lokman'ın 3 Ekim kuralı) yalnız bilgi olarak satırın notunda durur (15:18: bayiye belirtilecek). Klima duvarı sayılmaz. Tanımda duvar yazmıyorsa kalem hesaplanmaz.
- **Kapı boşlukları.** İç kapı 0,90 × 2,14 (lokman; çalışma kitaplarında da aynı). Dış kapı 0,95 × 2,10 (muhendis, 4 Ekim 12:14; 90 ve 105 m² listelerde de böyle, 62 m² listede 0,95 × 2,00).
- **Duvar izolasyonu** (lokman, 7 Ekim 07:45 ve 08:02). Gönderilmiyor; satır listeden çıktı ("Duvar izolasyonu göndermiyoruz yok say"; "evet çıkar"). Dört gerçek listede satır var. Hesabı kurallarda duruyor (dış duvar × kat sayısı + iç duvar − boşluklar; ÷ 8,64; Ç8201'de 13 paketti): `duvar_izolasyonu.listede` açılırsa geri gelir.
- **Çatı kaplaması.** Baz pakette tek kat panel (lokman). Kırma çatıda panel ve sac adedi çatı açılımından (lokman; yukarıda "Lokman'ın ikinci düzeltmesi"): yüzler şerit şerit dizilir, çapraz kesimden artan parça karşı yüzde kullanılır. Dizilim her yüzde köşeden başlar; kesim payı 5 mm; yedek yok (lokman, 4 Ekim 15:18). Kaplama saçaktan 5 cm taşar: panel boyunun tabanı = eğimli boy + 5 cm (muhendis, 4 Ekim 12:14), 10 mm'ye yukarı (lokman, 7 Ekim 07:45); adet düşüyorsa ya da taban boyda pay inceyse boy en çok 3 cm uzatılır (lokman, 4 Ekim 16:18; pay koşulu taban boyda da aranır; 8 Ekim 00:45: boyda 3 cm'e kadar fark tolere edilebilir). Çatı planı girdide yoksa yüzey × 1,10 ÷ (boy × kapatma genişliği) (uydurma). Beşik çatıda saçak boyu ÷ kapatma genişliği (uydurma). Kapatma (lokman, 4 Ekim 15:18; ürüne göre değişir): tek kat panel, sandviç panel ve kiremit desen sac 100 cm; trapez sac 80 cm (motor). Sandviç panelin 80 cm kapatanı da var. 2025 listelerinde tek kat panel 87, kiremit desen sac 110 cm'di. Panel kapaması (sac, L 2500): tek kat panelde listeden çıktı (lokman, 4 Ekim 16:18); sandviç panelde var (lokman, 4 Ekim 17:46). Kapama dere boyunca gider (lokman, 7 Ekim 07:45): adet = saçak (dere) kenarlarının toplamı ÷ (2,5 − 0,20); parça L 2500 (lokman, 08:02). Hesap Lokman'ın tarifinden geliştirildi; 8 Ekim 00:45'te onaylandı. Önceki hesap 2025 listelerindendi: her saçak kenarı ÷ 2,5, ayrı ayrı yukarı.
- **Shingle ve membran** (motor). Adet = çatı yüzeyi × çatı katsayısı ÷ 8 ("adet / 8 m²"). Çatı katsayısı: beşik 1; beşik + cumba 1,14; beşik + 2 cumba 1,27; dört omuz 1,06. Gerçek listeyle karşılaştırılmadı.
- **Mahya** (lokman; bindirme 7 Ekim 07:45). Mahya hattı ÷ (2,8 − 0,20). Kırma çatıda hat = tepe + dört kırma. Trapez sac mahyası L 800: mahya hattı ÷ (0,8 − 0,20) (motor). Bindirme önce 30 cm'di (Lokman, 3 Ekim 13:27); Excel motorunda ve Eylül 2026 listesinde 20 cm.
- **Ters mahya ve kenar kutusu** (lokman, 7 Ekim 07:45 ve 08:02). Ters mahya, cumbalı çatıda iki çatı eğiminin birleştiği vadi deredir; boyu oradan hesaplanır: vadi boyu ÷ (2,8 − 0,20). Kenar kutusu cumbalı çatılarda olmazsa olmaz; adedi çatıya göre değişir: ters mahya adedi × 2 (Excel motorundaki ve Eylül 2026 listesindeki formül). Ç8201'de vadi yok.
- **Mahya bandı** (muhendis, 4 Ekim 12:14). Mühendisin formülü: (mahya adedi × 2,8 m + ters mahya adedi × 2,8 m + damlalık adedi × 2,5 m) ÷ 10 m (rulo / 10 m), yukarı. Excel motorundaki formül aynı; motorda trapez sac mahyası × 0,8 m de toplanır, OSB mahyası ve özel mahya toplanmaz. Damlalık listeden tamamen çıkarıldı (Lokman, 4 Ekim 15:18: montajcılar kullanmıyor); terimi formülde yok. Ç8201: 11 × 2,8 ÷ 10 → 4 rulo. 01:24'teki uygulama mahya uzunluğundandı (3 rulo; açıklamalı prefabrik yükleme listesi çalışma kitabındaki formül).
- **Acil müdahale kapağı** (lokman, 7 Ekim 07:45). Dış kapı gibi her yapıya 1 adet, standart. Mühendis 4 Ekim'de "müşteri isterse" demişti; Lokman'ın söylediği geçerli.
- **Dere** (motor; bindirme lokman, 7 Ekim). Metal dere = saçak boyu ÷ (4,0 − 0,20). Kelepçe = dere × 8. İniş başına: boru 1, aparat 1, açık dirsek 2, kapalı dirsek 1, iniş kelepçesi 2.
- **Dere inişi** (lokman, 7 Ekim 07:45; eşik 8 Ekim 00:45'te onaylandı). Her saçak köşesine bir iniş; çok uzun dere boylarında ortaya bir tane daha. Kural: köşe, dere hatlarının uçlarıdır (iki hattın buluştuğu köşe tek sayılır); boyu 9 m'yi geçen dere hattının ortasına bir iniş daha, bir hatta en çok bir orta iniş. Dere hattının boyu = cephe + uçlardaki saçak. Dayanak: paftalarda ve Lokman'ın 82 m² örneğinde orta inişi olan hatlar 9,64 · 11,54 · 12,15 · 15,98 m, olmayanlar 5,18 · 6,06 · 8,10 m; eşik 8,10 ile 9,64 m arasında herhangi bir değer olabilir, 9 m alındı. Önceki uygulamada eşik cephe boyuyla ölçülüyordu (10 m). İniş plana elle yerleştirilmişse o sayı kullanılır (muhendis).
- **Köşebent** (muhendis). (Odaların tavan çevresi + veranda tavanının çevresi + iç köşe sayısı × 2,7 m) ÷ 2,5. İç köşe: iki duvarın odanın içinde buluştuğu köşe. Odaya doğru çıkıntı yapan köşeler sayılmaz; veranda tavanının çevresi sayılır (4 Ekim 12:14). Veranda çevresi brüt ölçüyle alınır; verandada köşe boyu eklenmez (okuma). Planı olmayan örnekte oda başına 4 iç köşe sayılır. Lokman, 7 Ekim 07:45 ve 08:02: köşebent önemli bir detay değil; mevcut kural uygulanır (Eylül 2026 şablonundaki + 3 ve çıkıntı köşeleri alınmadı).
- **Saçak altı ve saçak yüzü.** Yöntem A'da saçak altı Boardex (lokman); adet formülü 62 m² listeden (uydurma): saçak boyu × 0,30 × 1,08 ÷ 2,88. Saçak yüzü de Boardex (muhendis): saçak ucu çevresi × yüz yüksekliği × 1,08 ÷ 2,88. Zayiat Boardex'in %8'i (62 m² listenin formülünde %15'ti). Yöntem A'da saçak omegası yok (muhendis; lokman, 7 Ekim). Beşik çatıda kalkan kenarı (alın) yöntem A'da da Boardex kaplanır (lokman, 8 Ekim 00:45; ölçü saçaktaki gibi; `yontem_a_alin_kaplamasi`). Çatı kaplamasının üstüne bir malzeme gelmesi gerekiyor; hangisi olduğu soruldu, satırı adetsiz yazılıyor (`yontem_a_kalkan_ust_kapamasi`, soru). Dört omuz çatılı Ç8201'de böyle kenar yok. Çatının bir duvara dayandığı kenara özel mahya konur (lokman, 8 Ekim 00:45; `duvar_dibi`): L 2800, boy ÷ (2,8 − 0,20).
- **Yöntem B kalemleri** (prefabrik yöntemi). Çelikte kullanılmıyor (lokman, 7 Ekim 07:45): tavan omegası, aşık, saçak omegası, saçak sacı, alın sacı ve baş makas Z'si çelik listesinde yok; kuralları prefabrik çalışılınca birlikte kesinleşecek. O zamana kadar olduğu gibi duruyor ve yalnız karşılaştırma için hesaplanıyor: saçak sacı ve alın sacı = boy ÷ (2,5 − 0,20) (bindirme 20 cm: lokman, 7 Ekim; parça boyu L 2500 listelerden); saçak omegası, tavan omegası ve aşık kuralları iki listeye uydurulmuştu. Duvar yüzünde tavan omegası hattı yok; alın ve saçak sacı olmayınca baş makas Z'si de olmaz (lokman, 7 Ekim).
- **Vida, boya, tesisat** (motor ve excel). Alçıpan vidası = levha × 40 (lokman, 7 Ekim: levha başına 40 yeterli); OSB vidası = OSB × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; pencere vidası = pencere × 20; trapez (5,5 × 25) = çelik panel × 10 + köşebent × 6 (lokman, 7 Ekim: yalnız çelik birleşim yerleri, panel başına sağına soluna 5'er; omega ve aşık için konmaz; 08:02: köşebent terimi duruyor); trapez (5,5 × 60) = m² × 2,5 + sac boyu ÷ 200 × sac adedi; panel vidası = panel boyu ÷ 200 × adet; çelik dübel = duvar paneli × 2; uçlar ve kesme taşı = m² ÷ 15 (kesme taşı: lokman, 7 Ekim: formül ne veriyorsa); inox taş = m² ÷ 10; RYSB = m² × 7,5. Boya: 100 m²'ye dış 2, iç 2, tavan 1, astar 1 kova; dayson = m² × 0,06 (lokman, 7 Ekim: Excel motoruna uy); köpük 2; mastik = pencere adedi (lokman, 7 Ekim: pencere başına 1, boyu ne olursa olsun; pencereler alıcıya aitse yazılmaz: 8 Ekim 00:45). Tesisat: ıslak hacim başına 6 boru, 15 dirsek, 12 kulaklı dirsek, 6 düz T, 15 maşon, 6 iç dişli T, 3 atlama parçası; vitrifiye dahilse duşakabin, klozet, dolap ve batarya grubu.
- **Elektrik.** Pafta sayımı varsa o kullanılır (motorun notu: sayılar "montaj paftasından sayılır"). Yoksa mühendisin oda başına kuralı (yukarıda). Kabloda en uzak mesafe sigorta kutusundan ölçülür (lokman, 7 Ekim 07:45): kutu, tanımda yeri yazmıyorsa giriş kapısında sayılır; mesafe oradan kapalı kısmın en uzak köşesine. Buat, besleme kablosu, zil, sigorta kutusu, kaçak akım rölesi ve izole bant motorun formülleriyle.
- **Ölçü, renk, müştemilat** (lokman, 7 Ekim 07:45). Çevre ve alan kaplanmış yüzden alınır (gerçek listeler karkas yüzünden alıyor). Dere ve mastik çatı rengine bağlıdır. Müştemilat göz ardı edilir ("binde bir gelir"): kuralları için ayrıca çalışılmayacak.

## Üç gerçek listeyle karşılaştırma (adet)

Özet: 90 m²: 28 kalemin 15 tanesinde adet aynı; 62 m²: 40 kalemin 26 tanesinde adet aynı; 105 m²: 48 kalemin 31 tanesinde adet aynı. Toplam 116 karşılaştırmanın 72 tanesi aynı.

Tam tablo: `deneme/2026-10-03_yukleme/sonuc/tablolar.md`. Adedi doğrudan listeden alınan satırlar karşılaştırmaya girmedi: dere kapağı, elektrik sayımı ve 105 m² listede iniş sayısı ile ona bağlı dört satır. 90 ve 62 m² listelerde iniş sayısı Lokman'ın kuralından hesaplandı (6; listelerde 7): bu tek fark beş satırda birden görünüyor, yani 44 farkın 10'u oradan.

7 Ekim 03:46 sürümünde 119 karşılaştırmanın 74'ü aynıydı. Lokman'ın 7 Ekim kararlarıyla değişenler: duvar izolasyonu listeden çıktığı için karşılaştırılmıyor (üç satır; ikisi tutuyordu); bindirme 20 cm olunca saçak sacı 90 ve 62 m² listelerde de tutuyor (+ 2); 62 m² listede sandviç panel kapaması (16 → 17; liste 16) ve trapez vida (5,5 × 25) (1750 → 1000; liste 1750) artık tutmuyor (− 2). Sonuç 72 / 116. Veranda tavanı kuralı bu üç örneğe uygulanamıyor: girdilerinde veranda tavanı ayrı yazmıyor (o listelerde veranda tavanı yeşil alçıpan satırında); satırın notunda yazıyor. Bu listeler omega ve aşıklı yöntemle hazırlanmış 2025 uygulamasıdır; kararlar onlara uymak için değil, bundan sonraki çelik listeleri için verildi.

**Bu bir sınama değil.** `uydurma` kuralların katsayıları 90 ve 62 m² listelere bakılarak seçilmişti; o listelerle tutması kanıt sayılmaz. 105 m² liste levha, çatı ve dere kurallarından sonra eklendi; ama vida, boya, elektrik ve tesisat formülleri onunla aynı anda eklendi, kesme taşı katsayısı 62 ve 105 m² listelere bakılarak seçildi. Onun da çatı planı yok: saçak, mahya, alın boyları ve elektrik sayımı listede yazan değerlerdir. Üç örnekte de çatı uzunlukları ve tavan alanları listelerdeki değerlerdir. Yani hiçbiri kör sınama değil; yöntem A için ise hiç gerçek liste yok. Mühendisin cevaplarıyla gelen kurallardan (tavan ve çatı paneli, OSB takviyesinin duvarları, saçak yüzü) hiçbiri bu üç listeyle sınanamıyor; köşebent ve elektrik kuralı yukarıda sınandı. Çatı açılımı tek bir gerçek listeyle (62 m²) karşılaştırılabildi.

Adedi tutmayan kalemler:

| Grup | Kalem | Kural | Durum | 90 m²: hesap / liste | 62 m²: hesap / liste | 105 m²: hesap / liste |
|---|---|---|---|---|---|---|
| Metal aksam | Alın sacı (30'luk) | alın boyu ÷ (2,5 − 0,20 bindirme) | lokman | 8 / 9 ✗ | — | 8 / 8 |
| Metal aksam | Tavan omegası (60'lık) | tavan alanı ÷ 0,60 ÷ 3,75 | uydurma | 37 / 40 ✗ | 26 / 26 | 42 / 44 ✗ |
| Metal aksam | Aşık | eğim boyunca 60 cm aralıkla sıralar + mahya aşığı; kırmada her sıra çatıyı dolanır; × 1,05 ÷ 4,2 | uydurma | 56 / 57 ✗ | 41 / 41 | — |
| Metal aksam | Köşebent | (oda tavan çevreleri 87,84 m + 20 iç köşe × 2,7 m) ÷ 2,5 | muhendis | 57 / 70 ✗ | 39 / 50 ✗ | 70 / 85 ✗ |
| Metal aksam | Saçaklar için Boardex | saçak boyu × saçak eni × 1,08 ÷ 2,88 | uydurma | — | 5 / 5 | 8 / 7 ✗ |
| Dış cephe kaplama | Dış cephe Boardex | (çevre × yükseklik + kolon/kiriş kaplaması + çatı alnı (kalkan) − boşluklar) × 1,08 ÷ 2,88 | excel | 43 / 46 ✗ | 30 / 32 ✗ | 48 / 51 ✗ |
| İç cephe kaplama | Duvar alçıpan beyaz | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0 | excel | 66 / 67 ✗ | 32 / 32 | 78 / 79 ✗ |
| İç cephe kaplama | Duvar alçıpan yeşil | oda oda: (iç çevre × yükseklik − o odadaki boşluklar) toplamı × 1,05 ÷ 3,0; yeşil = ıslak hacimler | excel | 9 / 9 | 7 / 8 ✗ | 13 / 14 ✗ |
| İç cephe kaplama | Tavan alçıpan yeşil | tavan alanı × 1,05 ÷ 3,0; yeşil = ıslak hacim + veranda tavanı | lokman | 5 / 6 ✗ | 7 / 7 | 3 / 3 |
| İç cephe kaplama | OSB 9 mm (duvar) | listede yazan alan × 1,05 ÷ 2,98; alanın nasıl seçildiği listede yazmıyor | excel | 13 / 13 | — | 14 / 15 ✗ |
| Çatı kaplamaları | Sandviç panel | çatı açılımı: yüzler şerit şerit dizilir; çapraz kesimden artan parça karşı yüzde kullanılır; panel boyu = eğimli boy + taşma | lokman | — | 28 / 27 ✗ | — |
| Çatı kaplamaları | Sandviç panel kapaması | saçak (dere) boyu toplamı ÷ (2,5 − 0,20 bindirme) | lokman | — | 17 / 16 ✗ | — |
| Dere | Dere iniş borusu | 4 köşe + 2 orta (boyu 9 m'yi geçen dere hatları) | lokman | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | Dere iniş aparatı | iniş sayısı × 1 | motor | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | Açık dirsek | iniş sayısı × 2 | motor | 12 / 14 ✗ | 12 / 14 ✗ | — |
| Dere | Kapalı dirsek | iniş sayısı × 1 | motor | 6 / 7 ✗ | 6 / 7 ✗ | — |
| Dere | İniş kelepçesi | iniş sayısı × 2 | motor | 12 / 14 ✗ | 12 / 14 ✗ | — |
| Boya | Silikonize mastik | pencere adedi | lokman | 6 / 8 ✗ | 6 / 8 ✗ | 8 / 8 |
| Boya | Dayson | bina m² × 0,06 | lokman | 6 / 6 | 4 / 4 | 7 / 6 ✗ |
| Vida | RYSB pul başlı (3,9 × 32) | bina m² × 7,5 | motor | — | 465 / 400 ✗ | 788 / 500 ✗ |
| Vida | Alçıpan vidası (3,5 × 35) | alçıpan ve Boardex levha sayısı × 40; 250'ye yuvarlandı | excel | — | 4000 / 4000 | 7250 / 8500 ✗ |
| Vida | OSB ve yalıpan vidası (3,9 × 32) | OSB levha × 40 + priz × 4 + saçak sacı × 4 + dere kelepçesi × 3; 500'e yuvarlandı | motor | — | 3500 / 3500 | 1000 / 1500 ✗ |
| Vida | Pencere vidası (4,8 × 70) | pencere sayısı × 20 | excel | — | 120 / 120 | 160 / 180 ✗ |
| Vida | Trapez vida (5,5 × 25) | çelik panel × 10 + köşebent × 6; 250'ye yuvarlandı | excel | — | 1000 / 1750 ✗ | — |
| Vida | Trapez vida (5,5 × 110; sandviç panel) | panel boyu (mm) ÷ 200 × panel adedi; 250'ye yuvarlandı | motor | — | 500 / 750 ✗ | — |
| Vida | Çelik dübel (klipsli) | duvar paneli adedi × 2 | motor | — | 32 / 32 | 72 / 80 ✗ |
| Vida | Şase pul | çelik dübel adedi kadar | motor | — | 32 / 32 | 72 / 80 ✗ |
| Vida | İnox taş | bina m² ÷ 10 | excel | — | 7 / 7 | 11 / 10 ✗ |
| Elektrik | Buat kasa | anahtar + priz + oda sayısı (veranda hariç) | motor | — | — | 40 / 37 ✗ |
| Elektrik | İzole bant | bina m² × 0,06 | motor | — | — | 7 / 3 ✗ |

Okuma:

- **Köşebent.** Mühendisin formülü, oda başına 4 iç köşeyle listelerin altında kalıyor (57 / 70, 39 / 50, 70 / 85); önceki kural (m² ÷ 2,5) yarısını veriyordu. Gerçek iç köşe sayıları bilinmiyor.
- **Sandviç panel (62 m², kırma çatı).** Liste 27 adet L 3200 (ayrıca 2 adet L 1000); açılım dizilimi taşmayla 28 veriyor (taşmasız 26'ydı). Önceki kural (yüzey + %10) 27'yi tutturuyordu, ama o listeye uydurulmuştu.
- **Dış cephe Boardex.** Zayiat %8 olunca üç listede de 2–3 levha az: 43 / 46 · 30 / 32 · 48 / 51. %15 ile 45 / 46 · 32 / 32 · 52 / 51'di. Karşılaştırmadaki bir eksilme buradandı (74 / 119; önce 75).
- **İniş sayısı.** Kural 90 ve 62 m² projelerde 6 veriyor (dört köşe + iki uzun cephe); listelerde 7. Mühendis: iniş plana bakarak yerleştirilir. 105 m² listede 10; cephe ölçüleri olmadığı için kural hesaplanmadı. Montaj paftaları farkı gösteriyor (yukarıda, 17:46 bölümü): 62 m² projede 7 işaret (dört köşe, arka cephede bir, giriş saçağının iki ön köşesi), 105 m² projede 10, 90 m² projede 8.
- **Saçak sacı.** L 2500 parça ve 20 cm bindirme (÷ 2,3; Lokman, 7 Ekim) üç listeyi de tutturuyor (14, 17, 18). 30 cm ile (÷ 2,2) yalnız en yeni liste (Kasım 2025) tutuyordu; Eylül 2025 listelerinde birer fazla veriyordu.
- **Sandviç panel kapaması (62 m²).** Dere boyu toplamı ÷ 2,3 → 17; listede 16. Önceki hesap (her saçak kenarı ÷ 2,5, ayrı ayrı yukarı) o listeden alınmıştı ve 16 veriyordu.
- **Trapez vida (5,5 × 25) (62 m²).** Omega ve aşık terimleri kalkınca 1000; listede 1750 (o liste omega ve aşıklı yöntemle hazırlanmış).
- **Silikonize mastik.** Pencere başına 1 (Lokman, 7 Ekim): 90 ve 62 m² projelerde hesap 6, listelerde 8; 105 m² projede 8 / 8.
- **İki yöntem aynı listede.** 62 ve 105 m² listelerde hem saçak sacı hem saçaklar için Boardex var; kurala göre birlikte olmaz. 105 m² listede saçak altı 0,50 m alınmış (19,6 m² = 39,2 × 0,50).
- **Öteki levhalar** (alçıpan, OSB, saçak Boardex'i). Farklar 1 adet: listelerde yuvarlama bir yukarı, bir en yakına yapılmış. 105 m² listede beyaz duvar alçıpanındaki fark çalışma kitabındaki bir hücre hatasından: bir odada iki iç kapı boşluğu (3,85 m²) yerine 2 m² düşülmüş.
- **Sarf kalemleri** (RYSB, alçıpan vidası, izole bant). Motorun m² formülleri listelerdeki sayıları vermiyor.
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
| Metal aksam | Saçaklar için OUTWEAR Dış Cephe Levhası | 12,5 × 1200 × 2400 | 5 | aynı | 11,8 m² |  | uydurma |
| Metal aksam | Saçak yüzü için OUTWEAR Dış Cephe Levhası | 12,5 × 1200 × 2400 | 3 | aynı | 7,2 m² |  | muhendis |
| Metal aksam | Köşebent | L 2500 | 59 | aynı | 146,3 m |  | muhendis |
| Dış cephe kaplama | OUTWEAR Dış Cephe Levhası | 12,5 × 1200 × 2400 | 31 | aynı | 80,7 m² |  | excel |
| Dış cephe kaplama | Veranda tavanı (OUTWEAR Dış Cephe Levhası) | 12,5 × 1200 × 2400 | 7 | aynı | 18,3 m² |  | lokman |
| İç cephe kaplama | Duvar alçıpan beyaz | 1200 × 2500 | 47 | 46 | 132,8 m² |  | excel |
| İç cephe kaplama | Duvar alçıpan yeşil | 1200 × 2500 | 8 | aynı | 20,4 m² |  | excel |
| İç cephe kaplama | Tavan alçıpan beyaz | 1200 × 2500 | 19 | aynı | 54,1 m² |  | motor |
| İç cephe kaplama | Tavan alçıpan yeşil | 1200 × 2500 | 2 | aynı | 4,3 m² |  | lokman |
| İç cephe kaplama | OSB (TV ve mutfak dolabı arkası takviyesi) | 11 × 1220 × 2440 | 9 | aynı | 24,5 m² |  | lokman |
| Çatı kaplamaları | Tek kat panel | L 4330 · 100 cm kapatır | 25 | aynı | 98,4 m² |  | lokman |
| Çatı kaplamaları | Metal kiremit mahyası | L 2800 | 11 | aynı | 27,0 m |  | lokman |
| Çatı kaplamaları | Mahya bandı | rulo / 10 m | 4 | aynı | 30,8 m |  | muhendis |
| Çatı kaplamaları | Acil müdahale kapağı | adet | 1 | aynı |  |  | lokman |
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
| Elektrik | NYM kablo (3 × 2,5) | metre | 120 | aynı |  |  | lokman |
| Elektrik | NYM kablo (2 × 1,5) | metre | 96 | aynı |  |  | lokman |
| Elektrik | Buat kasa | adet | 31 | aynı |  |  | motor |
| Elektrik | Uydu kablo | metre | 25 | aynı |  |  | motor |
| Elektrik | Besleme kablosu (sigorta kutuları arası) | metre | 5 | aynı |  |  | motor |
| Elektrik | Besleme kablo borusu | metre | 5 | aynı |  |  | motor |
| Elektrik | Zil | adet | 1 | aynı |  |  | motor |
| Elektrik | Sigorta kutusu (12'li) | adet | 1 | aynı |  |  | motor |
| Elektrik | İzole bant | adet | 5 | aynı | 82,0 m² |  | motor |
| Elektrik | Kaçak akım rölesi | adet | 1 | aynı |  |  | motor |
| Vida | RYSB pul başlı (3,9 × 32) | adet | 615 | aynı | 82,0 m² |  | motor |
| Vida | Alçıpan vidası (3,5 × 35) | adet | 5000 | aynı | 122,0 levha |  | excel |
| Vida | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | aynı | 700,0 vida |  | motor |
| Vida | Pencere vidası (4,8 × 70) | adet | 160 | aynı | 8,0 pencere |  | excel |
| Vida | Trapez vida (5,5 × 25) | adet | 1000 | aynı | 984,0 vida |  | excel |
| Vida | Trapez vida (5,5 × 60) | adet | 250 | aynı | 205,0 vida |  | motor |
| Vida | Trapez vida (5,5 × 76; tek kat panel) | adet | 750 | aynı | 541,2 vida |  | motor |
| Vida | Çelik dübel (klipsli) | adet | 28 | aynı | 14,0 panel |  | motor |
| Vida | Şase pul | adet | 28 | aynı | 14,0 panel |  | motor |
| Vida | 8'lik trapez uç | adet | 6 | aynı | 82,0 m² |  | motor |
| Vida | PH2 uç | adet | 6 | aynı | 82,0 m² |  | motor |
| Vida | 230'luk kesme taşı | adet | 6 | aynı | 82,0 m² |  | lokman |
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
| Boya | Silikonize mastik | adet | 8 | aynı | 8,0 pencere |  | lokman |
| Boya | Dayson | adet | 5 | aynı | 82,0 m² |  | lokman |
| Boya | Poliüretan köpük | adet | 2 | aynı |  |  | motor |

### Çatı kaplaması seçenekleri

Baz pakette tek kat panel (Lokman, 4 Ekim 01:42). Altı seçenekte değişen kalemler (son üç seçenek gerçek listeyle karşılaştırılmadı):

| Seçenek | Kalem | Boyut | Adet | Durum |
|---|---|---|---|---|
| Tek kat panel (baz paket) | Tek kat panel | L 4330 · 100 cm kapatır | 25 | lokman |
| Tek kat panel (baz paket) | Metal kiremit mahyası | L 2800 | 11 | lokman |
| Tek kat panel (baz paket) | Mahya bandı | rulo / 10 m | 4 | muhendis |
| Tek kat panel (baz paket) | Acil müdahale kapağı | adet | 1 | lokman |
| Tek kat panel (baz paket) | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Tek kat panel (baz paket) | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Tek kat panel (baz paket) | Trapez vida (5,5 × 60) | adet | 250 | motor |
| Tek kat panel (baz paket) | Trapez vida (5,5 × 76; tek kat panel) | adet | 750 | motor |
| Sandviç panel | Sandviç panel | L 4330 · 100 cm kapatır | 25 | lokman |
| Sandviç panel | Metal kiremit mahyası | L 2800 | 11 | lokman |
| Sandviç panel | Sandviç panel kapaması | L 2500 | 18 | lokman |
| Sandviç panel | Mahya bandı | rulo / 10 m | 4 | muhendis |
| Sandviç panel | Acil müdahale kapağı | adet | 1 | lokman |
| Sandviç panel | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Sandviç panel | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Sandviç panel | Trapez vida (5,5 × 60) | adet | 250 | motor |
| Sandviç panel | Trapez vida (5,5 × 110; sandviç panel) | adet | 750 | motor |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Çatı OSB | 11 × 1220 × 2440 | 35 | uydurma |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Nem bariyeri | m² | 105 | motor |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Metal kiremit (kiremit desen sac) | L 4330 · 100 cm kapatır | 28 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Metal kiremit mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | OSB mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Mahya bandı | rulo / 10 m | 4 | muhendis |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Acil müdahale kapağı | adet | 1 | lokman |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit) | Trapez vida (5,5 × 60) | adet | 1000 | motor |
| OSB + nem bariyeri + trapez sac | Çatı OSB | 11 × 1220 × 2440 | 35 | uydurma |
| OSB + nem bariyeri + trapez sac | Nem bariyeri | m² | 105 | motor |
| OSB + nem bariyeri + trapez sac | Trapez sac | L 4330 · 80 cm kapatır | 30 | lokman |
| OSB + nem bariyeri + trapez sac | Trapez sac mahyası | L 800 | 45 | motor |
| OSB + nem bariyeri + trapez sac | OSB mahyası | L 2800 | 11 | lokman |
| OSB + nem bariyeri + trapez sac | Mahya bandı | rulo / 10 m | 4 | muhendis |
| OSB + nem bariyeri + trapez sac | Acil müdahale kapağı | adet | 1 | lokman |
| OSB + nem bariyeri + trapez sac | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + nem bariyeri + trapez sac | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + nem bariyeri + trapez sac | Trapez vida (5,5 × 60) | adet | 1000 | motor |
| Trapez sac | Trapez sac | L 4330 · 80 cm kapatır | 30 | lokman |
| Trapez sac | Trapez sac mahyası | L 800 | 45 | motor |
| Trapez sac | Mahya bandı | rulo / 10 m | 4 | muhendis |
| Trapez sac | Acil müdahale kapağı | adet | 1 | lokman |
| Trapez sac | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| Trapez sac | OSB ve yalıpan vidası (3,9 × 32) | adet | 1000 | motor |
| Trapez sac | Trapez vida (5,5 × 60) | adet | 1000 | motor |
| OSB + membran + shingle | Çatı OSB | 11 × 1220 × 2440 | 35 | uydurma |
| OSB + membran + shingle | Nem bariyeri | m² | 105 | motor |
| OSB + membran + shingle | Membran | adet / 8 m² | 14 | motor |
| OSB + membran + shingle | Shingle | adet / 8 m² | 14 | motor |
| OSB + membran + shingle | OSB mahyası | L 2800 | 11 | lokman |
| OSB + membran + shingle | Acil müdahale kapağı | adet | 1 | lokman |
| OSB + membran + shingle | Çatı şiltesi 80 mm | 9,6 m²/adet | 10 | uydurma |
| OSB + membran + shingle | OSB ve yalıpan vidası (3,9 × 32) | adet | 2500 | motor |
| OSB + membran + shingle | Trapez vida (5,5 × 60) | adet | 250 | motor |

### Aynı model yöntem B ile

Çelikte bu yöntem artık kullanılmıyor (Lokman, 7 Ekim 07:45); liste yalnız karşılaştırma için üretiliyor ve başında bunu söyleyen bir not var. Bayi kuralı çatıyı yöntem B'ye çevirirse (`--bayi ORNEK-BAYI-3`; çıktı `sonuc/C8201_yontem_B.md`): tavan ve çatı paneli ile saçak altı ve saçak yüzü Boardex'i çıkar; saçak sacı 18, saçak omegası 18, tavan omegası 35, aşık 49 girer. Çelik 1903 kg, trapez vida (5,5 × 25) 1000 olur (omega ve aşık terimleri kalkmadan önce 2000).

## Excel motoruyla ilgili gözlemler (mühendise iletilecek)

- **Trapez sac ve metal kiremit adedi.** Formülde 0,8 ve 1,05 paydanın parantezi dışında: kapatma genişliğine bölmek yerine çarpıyor. Hücreler, formülün işleyişi, örnekler ve öteki dört bulgu yukarıda ("Excel motorundaki çatı kaplaması formülü"). Mühendis 11. cevabında formülü yeniden kontrol etmemizi istedi; bulgu ona iletilecek. Trapez sacda motorun formülü kullanılmıyor.
- **Kırma çatıda kaplama adedi.** Motor yüzeyden hesaplıyor; notunda gerçek adedin AutoCAD'de yerleşimle bulunacağı yazıyor. Mühendisin 10 × 10 m dört omuz metrajında 118 m² yüzey için 36 adet L 5900 trapez sac var (yüzeyin 1,44 katı). 62 m² gerçek listede 27 adet L 3200 ve 2 adet L 1000 sandviç panel var (yüzeyin 1,15 katı). Lokman'ın 4 Ekim 01:42 kuralıyla adet artık çatı açılımından çıkıyor; karşılaştırma yukarıdaki tabloda.
- **Köşebent.** Motor plansız hesaplıyor: oda çevrelerini bina kenarlarının altı katı, iç köşeyi 36 sayıyor. Ç8201'in ölçüleriyle 78 verir; plandan 59.
- **Elektrik.** Motorda sayılar sabit: duy 7, glop 3, tekli anahtar 9, çiftli anahtar 2, tekli priz 22, çiftli priz 3, uydu prizi 1, sigorta 9; buat = anahtar + priz + 9.
- **İniş borusu.** Motorda dere adedi ÷ 5 + 6; mühendisin 10 × 10 m metrajındaki sayıları (8 ve 6) vermiyor (9 ve 8 verir).
- **Motorda olup listede olmayan kalemler.** Kalmadı. Mahya bandı listeye eklendi (mühendis, 4 Ekim). Acil müdahale kapağı her yapıya 1 adet standart (Lokman, 7 Ekim 07:45; mühendis "müşteri isterse" demişti). Ters mahya kenar kutuları (ters mahya × 2) cumbalı çatıda listede (Lokman, 7 Ekim 08:02). Damlalık (L 2500; motorda 78. satır, adedi elle, şablonda 0): Lokman listeden tamamen çıkardı (4 Ekim 15:18; 7 Ekim 07:45: "Listeden çıkar"); yerine düşünülen plastik kapama aparatı sipariş verilirse listeye girecek. Motorda panel kapamaları damlalıktan ayrı kalemler: tek kat panel kapaması (66. satır, L 2500, adedi elle) ve sandviç panel kapaması (69. satır, L 2800; saçak boyu × çatı katsayısı ÷ 2,6). Tek kat panel kapaması Lokman'ın 4 Ekim 16:18 cevabıyla çıktı; sandviç panel kapaması kalıyor (4 Ekim 17:46) ve dere boyu ÷ (2,5 − 0,20) ile hesaplanıyor (7 Ekim 07:45 ve 08:02).

## Kör test: KT-01 (6–7 Ekim 2026)

Lokman, 6 Ekim 21:22: bir başka çelik projenin (98,7 m², beşik + cumba çatı, müştemilatlı; Eylül 2026) DWG'sinden bizim çizimlerimiz ve bu kurallarla kendi listemiz çıkarıldı; liste depoya dondurulduktan sonra gerçek listeyle satır satır kıyaslandı. Rapor: `docs/raporlar/2026-10-07_Kor_Test_KT01.md`; kod ve tablolar: `deneme/2026-10-06_kor_test/`.

- **Sonuç (7 Ekim 03:46; kural seti 0.12).** Gerçek listenin 98 satırından kör listede 42'si, yalnız bizim hatalarımız düzeltilince 48'i, Eylül 2026 listesinin uygulaması da kural olursa 61'i, elektrik ve iniş sayıları paftadan alınırsa 71'i aynıydı. Kör listedeki 56 farkın 29'u bizim hatamızdı (girdi 2, kural 27).
- **Varsayılan hesaba girenler** (bizim hatalarımız; `kurallar.json`'da durumu `liste`): model verilmişse çelik ağırlığı modeldeki profil boyundan ve okunan et kalınlığından (`celik.profil_kg_m`); çok düzlemli çatıda aşık sıraları (`cok_duzlemli_cati`); ek yapının kalemleri ayrı satır, çatı panelli çatıda dere, saçak sacı ve alın sacı yok (`ek_yapi_ve_korkuluk`); dış cephe nem bariyeri yalnız duvarlar × 1,08 (`nem_bariyeri_dis_cephe`); dere kapağı dere hatlarının serbest uçlarından (`dere_kapagi_serbest_uc`); baş makas Z'si (`bas_makas_z`; uydurma); depo için elektrik (`elektrik_oda_ek`); alıcıya ait kalemler kalem kalem (`kapsam_alici`); renk (`renkli_kalemler`).
- **Eylül 2026 uygulaması.** O listenin, o günkü kurallardan farklı yaptığı on yedi şey ayrı bir katmana konmuştu (`sablon_2026`; `yukleme.py --sablon 2026`; satırların durumu `sablon`). Lokman 7 Ekim 07:45'te on yedisini de cevapladı (aşağıdaki bölüm). Katman, 03:46 kıyası yeniden üretilebilsin diye duruyor (`kiyas_kos.sh`, 0.12 setine sabit); varsayılan hesaba karışmıyor.
- **Kararlardan sonra (7–9 Ekim; kural seti 0.16, 0.15 ile aynı sonuç).** Aynı proje güncel kurallarla iki kez hesaplandı (`kararlar_kos.sh`; tablo `deneme/2026-10-06_kor_test/sonuc/KT01_kararlar_kiyas.md`). Yapıldığı yöntemle (B: tavan omegası ve aşık; elektrik sayıları paftadan) 98 satırın **63**'ü aynı; düzeltilmiş listede 48'di. Yeni tutan 15 satırın 10'u kararlardan (5'i iniş kuralından), 5'i elektrik sayılarının paftadan alınmasından; önce tutan hiçbir satır bozulmadı. Çelik standardıyla (A: çatı ve tavan paneli; bu proje bugün sipariş edilse çıkacak liste) **60**'ı aynı. B'de farklı kalan 35 satır: 14 satırda Lokman'ın kararı o listeden farklı; 3 satır yöntemden (omega, aşık, saçak omegası); 16 satır listenin elle hesabı, yuvarlaması ya da elle dizilimi; 2 satır ölçünün alındığı yüzden (karar: bizdeki); kural bekleyen satır kalmadı. 20 satırın adedi değişti: 14 satır kararlarla, 6 satır elektrik sayıları paftadan alındığı için. A listesinde gerçek listede olmayan 6 satır var: Tavan paneli (makas arası); Çatı paneli (makas üstü, sırt 80 mm); Saçaklar için OUTWEAR Dış Cephe Levhası; Saçak yüzü için OUTWEAR Dış Cephe Levhası; Alın (kalkan kenarı) için OUTWEAR Dış Cephe Levhası; Alın kapama. Çelik: gerçek liste 1937 kg, B 1937 kg, A 2588 kg (tavan ve çatı panelleri eklenir).
- **Okuma.** Aynı satır sayısı kuralların o listeye ne kadar benzediğini gösterir, doğruluğunu değil: Lokman'ın kararlarının bir kısmı o listeyi düzeltiyor (Boardex kalınlığı, çatı şiltesi, duvar izolasyonu, vida katsayıları). Kararlardan sonraki tabloda her fark satırının nedeni yazılı; elle yazılan açıklamalar hesap çıktısıyla denetleniyor (`kararlar_kiyas.py`).

## Lokman'ın cevapları (7 Ekim 07:45 ve 08:02) ve uygulanışı

Sorular, kör test raporunun on iki sorusuydu (raporun 12. bölümü); birincisi Eylül 2026 listesinin farklı yaptığı on yedi şeydi (a–q). Cevaplar tırnak içinde, yazıldığı gibi. 08:02'de beş okuma soruldu; düzeltmeleri ilgili satırda. Lokman ayrıca: "bazı kuralları yeniden optimize edeceğiz hem çizimden hem doğrulama motorundan … tüm optimizasyonu beraber yapacağız".

Kurallar bu cevaplarla 0.13 sürümü oldu. Önceki set olduğu gibi saklanıyor (`deneme/2026-10-03_yukleme/kural_setleri/0.12.json`); `PORTMAN_KURALLAR` ile seçilince 7 Ekim 03:46'daki bütün çıktılar bayt bayt aynı üretiliyor. Yeni davranışların hepsi kurallardaki bir anahtara bağlı: kod değişmeden kural değişir.

| # | Konu | Cevap | Uygulama |
|---|---|---|---|
| 1 a | Bindirme | "Bindirmeleri 20 cm yap 30 cm banada çok geldi" | Mahya, saçak sacı ve alın sacında 30 → 20 cm; dere ve trapez mahyası zaten 20 cm'di (açık soru kapandı). Ç8201: mahya ÷ 2,6 → 11; adet değişmedi. |
| 1 b; 7 | Köşebent | "Köşebent önemli değil"; "bizde ne çıkıyorsa onu uygula hiç önemli değil yani köşebent olmazsa bile binayı kurabilirler" | Kural değişmedi (mühendisin formülü; Ç8201'de 59). Şablondaki + 3 ve çıkıntı köşeleri alınmadı. |
| 1 c, d, e; 2 | Saçak omegası, tavan omegası, aşık | "Çatı ve tavan paneli var ise saçak omegası kullanmıyoruz yine dediğim gibi prefabrikte kullanacağız"; "Aynısı geçerli"; "Duvar yüzünde tavan omegası yok … hangi çatı tipi olursa olsun özellikle 4 omuz ve Beşik çatı çatı ve tavan paneli kullanacağız o yüzden Çelik Konstrüksyion yapılarda omega ve aşık olmayacak artık göz ardı et ama Prefabrik yapılarda olacak ona sıra gelince kuralları yine beraber çalışırız" | Çelikte çatı yöntemi her zaman A (`celik_cati_yontemi`). Yöntem B'nin kalemleri çelik listesinde yok; kuralları prefabrik çalışılana kadar olduğu gibi duruyor. B ile hesaplanan listenin başına "çelikte kullanılmıyor" notu düşüyor. |
| 1 f | Ters mahya ve kenar kutusu | "Ters mahya cumba şekline bağlı iki çatı eğiminin birleşitiği vadi dere oradan hesaplanıyor"; 08:02 (kenar kutusu listeye girsin mi?): "evet girsin bu tarz cumbalı çatılarda olmazsa olmazdır her cumbalı çatı için aynı değil" | Ters mahya vadinin boyundan (öyleydi). Kenar kutusu artık varsayılan listede: ters mahya × 2. Ç8201'de vadi yok; KT-01'de 4 (liste 4). |
| 1 g | Damlalık | "Listeden çıkar" | Çıkıktı (4 Ekim 15:18); öyle kaldı. Çatının bir duvara dayandığı kenara ne konacağı o gün açıktı; 8 Ekim 00:45: özel mahya. |
| 1 h | Duvar izolasyonu | "Duvar izolasyonu göndermiyoruz yok say"; 08:02 (satır çıksın mı?): "evet çıkar" | Satır listeden çıktı (Ç8201'de 13 paketti). |
| 1 i | Sandviç panel kapaması | "Aslında dere boyu ile aynı oradan yola çıkabilirsin yani binanı çatı eğiminin olduğu tarafa her zaman dere ve sandviç panel kapama gelir şöyle bizde saçaklar 30'ar cm ona göre sen bir hesap geliştir"; 08:02 (parça boyu): "en son 2500 dü diye biliyorum" | Geliştirilen hesap (8 Ekim 00:45'te onaylandı): kapama boyu = saçak (dere) kenarlarının toplamı; adet = boy ÷ (2,5 − 0,20). Ç8201, sandviç panel seçeneği: 39,28 ÷ 2,3 → 18. |
| 1 j | Veranda tavanı | "Çelik konstrüksyion binalarda her zaman boardex olmalı prefabrik yapılarda yeşil alçıpan" | Veranda tavanı Boardex satırı oldu: 18,3 m² → 7 levha; yeşil tavan alçıpanı 8 → 2. |
| 1 k | Boardex kalınlığı | "… 8 mm girmiş yanlış ver doğrusu 12.5mm resmi belgelerined yazıyor kontrol edebilirsin marka Aygyps (aytaş)" | 12,5 mm kuraldaydı (mühendis, 4 Ekim 12:14); teyit edildi. Kontrol edildi: üreticinin dış cephe levhasının performans beyanında kalınlık 12,5 mm; sistem kitabında 12,5 ve 15 mm; 8 mm yok. |
| 1 l | Çatı şiltesi | "Doğrusu 80mm ama listelerde yine boardexde olduğu gibi hatalı girilmiş" | 80 mm kuraldaydı; teyit edildi. |
| 1 m | Alçıpan ve OSB vidası | "Levha başına 40 yeterli" | Değişmedi (şablondaki 50 alınmadı). |
| 1 n | Trapez vida (5,5 × 25) | "Omega ve aşık için koyulmayacak sadece çelik birleşim yerlerine kaç panel varsa sağına soluna 5 ile çarp"; 08:02: "köşebenti çıkarma sadece mevcut kurala uy" | Aşık ve omega terimleri sıfırlandı; çelik panel × 10 ve köşebent × 6 duruyor. Ç8201 (yöntem A) değişmedi: 1000. Yöntem B listesinde 2000 → 1000. |
| 1 o | Kesme taşı | "Kesme taşı hiç önemli değil formül ne veriyorsa yeterli" | Değişmedi (m² ÷ 15). |
| 1 p | Dayson | "Tamam sen excel motoruna uy" | Değişmedi (m² × 0,06). |
| 1 q | NYM kablo | "Sigorta x sigortadan en uzak mesafe diye bir kural varsa onu uygula" | Kural Excel motorunun notunda yazılı. Mesafe artık sigorta kutusundan (tanımda yeri yoksa giriş kapısı) kapalı kısmın en uzak köşesine: Ç8201'de 8,60 m (köşegen 11,34 m'ydi). NYM 3 × 2,5: 145 → 120 m; 2 × 1,5: 121 → 96 m. |
| 3 | Müştemilat | "Müştemilatı göz ardı et binde bir gelir önemli bir konu değil" | Müştemilatla ilgili sorular kapandı; mevcut hesap olduğu gibi duruyor. |
| 4 | Dere inişi | "yani her saçak köşesine ve çok uzun dere boyarında ortaya 1 tane daha koyuyoruz nasıl kurallaştırabiliriz?" | Kural (eşiği 8 Ekim 00:45'te onaylandı): köşe = dere hatlarının uçları; boyu 9 m'yi geçen dere hattının ortasına bir iniş daha; bir hatta en çok bir. Ç8201: 6 (değişmedi). KT-01: 5 → 7 (pafta ve liste 7). Ayrıntı "Öteki kurallar"da. |
| 5 | Baş makas Z'si | "Alın ve Saçak sacı olmayınca baş makas Z side olmaz" | Yalnız yöntem B'de hesaplanıyordu; çelikte yok. |
| 6 | Mastik, acil müdahale kapağı, menfezli saçak sacı, buat | "silikonize mastik pencereler için koyuluyor boyu ne olursa olsun pencere başı 1 adet koy acil müdehale kapağı dış kapı gibi her yapıya 1 adet standart menfezli saçak sacı önemli değil prefabrik için ayrıca çalışacağız bizdekine uy" | Mastik = pencere adedi (Ç8201: 8); pencereler alıcıya aitse yazılmaz (8 Ekim 00:45). Acil müdahale kapağı her yapıya 1: Ç8201'de yeni satır. Menfezli saçak sacı prefabrikle birlikte. Buat kasada oda sayısı bizdeki gibi. |
| 8 | Ölçü | "bizdekini al" | Çevre ve alan kaplanmış yüzden (değişmedi). |
| 9 | Sandviç panel boyu | "sandviç panelde o kadar tolerans var önemli değil yukarı yuvarla"; 08:02 (10 mm'ye yukarı mı?): "evet" | Kuraldan gelen panel boyu 10 mm'ye yukarı. Ç8201: taban L 4315 → L 4320; pay koşuluyla liste L 4330 × 25 (yukarıda "Panel boyu uzatma kuralı"). |
| 10 | Dere ve mastiğin rengi | "çatı rengine" | Çatı rengine bağlı (`renkli_kalemler`). |
| 11 | Çelik birim ağırlıkları | "profil uzunluklarını çizmeden nasıl bileceğiz ki çelik karkas çizimi iş imalata verilince çıkar yani teklif ve BOM listesi için neredeyse en son aşama şimdilik bunu geç" | Geçildi. Karkas çizimi yokken çelik, Excel motorunun ortalamalarıyla hesaplanıyor; model verilmişse modeldeki profil boyundan. |
| 12 | Çizimler | "Çizimlerin bu halini çok beğendim burada kalalım sadece açıklamalar kısmını düzelteceğiz"; "çizimler persfektifler çok güzel olmuş bunları kurala ekle paftadaki açıklamaları düzelteceğiz" | Çizim seti standart olarak kaydedildi (`docs/sartname/cizim_seti.md`). Paftadaki açıklamalar birlikte düzeltilecek. Depoya eklenmesi sorusu cevaplanmadı: KT-01'in tanımı ve çizimleri depoda değil. |

Ç8201'in baz listesinde değişenler (88 → 89 satır): duvar izolasyonu çıktı; veranda tavanı (Boardex) ve acil müdahale kapağı girdi; yeşil tavan alçıpanı 8 → 2; NYM kablolar 145 → 120 ve 121 → 96 m; panel L 4325 → L 4330 (adet aynı). Öteki satırlarda adet değişmedi; kaynak ve durum notları güncellendi.

Cevaplardan çıkarılan yedi uygulama (iniş eşiği, kapama hesabı, panel boyunda pay, alıcıya ait pencerede mastik, sigorta kutusunun yeri, yöntem A'da kalkan kenarı, trapez vidada parça C profil) Lokman'a soruldu; 8 Ekim 00:45'te altısı cevaplandı (aşağıdaki bölüm), parça C profil sorusu yeniden soruldu.

Sağlama (7 Ekim): kararlarla değişen kalemler (mahya, ters mahya ve kenar kutusu, saçak ve alın sacı, kapama, veranda tavanı ve yeşil tavan, kablolar, iniş ve ona bağlı dört kalem, trapez ve alçıpan vidası, acil müdahale kapağı, mastik, panel boyu) beş listede (Ç8201 baz, sandviç panel ve yöntem B; KT-01 A ve B) ayrı bir oturumda, hesap koduna bakılmadan, girdilerden ve bu kurallardan yeniden hesaplandı: 138 karşılaştırmanın hepsi aynı çıktı. Ç8201'de sigortadan en uzak mesafe tanımdaki geometriden ayrıca bulundu (8,598 m → 8,60). O denetim, trapez vidada panel sayısının iki hatta farklı sayıldığını gösterdi (katalog modelinde parça C profiller toplamın içindeydi, modelden sayılan panellerde değildi); iki hat eşitlendi ve parça C profillerin sayılıp sayılmayacağı soruldu. Kod ayrıca üçüncü bir oturumda incelendi; bulduğu hatalar (dere hattı olmayan çatıda orta iniş, şablon katmanıyla kapama satırının notu, yeşil tavanın eksiye düşebilmesi, çizim setinde yöntem seçeneğinin IFC'ye geçmemesi, panel boyu ölçütünün iki motorda ayrışması) düzeltildi.

Panel boyu kuralı iki motorda ayrı ayrı kurulu olduğu için birbirine bağlandı: genel motorun seçtiği boy, adet ve uzatmanın nedeni rastgele 150 kırma çatı ve kaplamada kırma motorununkiyle karşılaştırılıyor (boyu uzayan 16, bunlardan pay koşuluyla uzayan 7; fark yok). Sağlamaların kendisi de sınandı: ölçüt iki motorda dokuz yerde bilerek bozuldu; yedisi yakalandı. Yakalanmayan ikisi aynı bozmanın iki motordaki eşi (pay koşulunda "1 cm payla gereken adedi düşürüyorsa" yerine "artırmıyorsa") ve sonucu değiştirmiyor: pay inceyken 3 cm içindeki bir uzatma her zaman tam düzeltiyor (6000 rastgele çatının 162'sinde pay inceydi: 160'ında 1 cm, birinde 2 cm yetti; birinde adet de düştü). Pratikte: taban boyda pay inceyse boy çoğunlukla 1 cm uzar.

## Lokman'ın cevapları (8 Ekim 00:45) ve uygulanışı

7 Ekim'de sorulan dokuz soruya verildi. Cevaplar tırnak içinde, yazıldığı gibi. Kurallar bu cevaplarla 0.14 sürümü oldu; 0.13 seti saklanıyor (`deneme/2026-10-03_yukleme/kural_setleri/0.13.json`) ve onunla 7 Ekim'deki çıktılar bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | İniş: "çok uzun" için 9 m dere boyu uygun mu? | "evet uygundur" | Kural kesinleşti: dere hatlarının uçlarına birer iniş, boyu 9 m'yi geçen hattın ortasına bir tane daha. Ç8201: 6; KT-01: 7. |
| 2 | Sandviç panel kapaması: dere boyu toplamı ÷ (2,5 − 0,20) uygun mu? | "evet uygun" | Kesinleşti. Ç8201, sandviç panel seçeneği: 18; KT-01: 14. |
| 3 | Panel boyunda pay: L 4320 mi, L 4330 mi; pay nasıl alınsın? | "3 cm'e kadar +- tolere edilebilir artık sandviç panel hesabını sonlandır" | Hesap bu haliyle kapandı: eğimli boy + taşma, 10 mm'ye yukarı; adedi düşürüyorsa ya da taban boyda pay inceyse en çok 3 cm uzatma. Ç8201: L 4330 × 25. Bu konuda yeni soru sorulmayacak. |
| 4 | Çatı ve tavan panelli beşik çatıda kalkan kenarı (alın) neyle kapanıyor? | "beşik çatıda da boardex kaplama yapılıyor ama çatı kaplamasının üstüne bir malzeme gelmesi lazım" | Kalkan kenarının Boardex kaplandığı kesinleşti. Ölçü saçağınki gibi alındı (kenar boyu × (saçak eni + saçak yüzü); soruda "saçak gibi" denmişti): kalkan kenarının çıkıntısı için ayrı bir ölçü yok. Çatı kaplamasının üstüne gelecek malzeme için satır açıldı: kalkan kenarının boyuyla, adetsiz, durumu `soru`; malzemenin adı ve parça boyu soruldu. Satır saçak altının malzemesine bağlı değil. KT-01 (çelik standardı): 20,97 m (çatı panelli ek yapının alınları hariç). |
| 5 | Çatının bir duvara dayandığı kenara ne konuyor? | "özel mahya" | O kenarların boyu özel mahya satırına yazılıyor: L 2800, boy ÷ (2,8 − 0,20). KT-01: 11,35 m → 5. Geçici "duvar dibi sacı" satırı kalktı. Adet hesabı benim uygulamam: mahyada ve kapamada olduğu gibi boylar toplanıp bir kez yuvarlanıyor; her yapının kenarı ayrı yuvarlansa 6 olurdu (satırın notunda yazıyor; soruldu). Özel mahya mahya bandı hesabına girmiyor (Excel motorundaki formülde yok) ve satıra renk yazılmıyor: ikisi de soruldu. |
| 6 | Pencereler alıcıya aitse mastik yine yazılsın mı? | "hayır yazılmasın" | Yazılmıyor (pencere vidası gibi). Pencere listedeyse pencere başına 1 (Ç8201: 8). KT-01'de mastik satırı yok (o listede 3). |
| 7 | Sigorta kutusu tanımda yoksa giriş kapısında sayılsın mı? | "evet uygun" | Kesinleşti. |
| 8 | Listede "Boardex" mi yazsın, üreticinin adı mı? | "üreticide ne yazıyorsa onu yaz" | Listede yazılan ad üreticinin ürün sayfasındaki ad: OUTWEAR Dış Cephe Levhası. Ç8201'de 4 satır. Hesabın iç anahtarı ile formül ve not metinleri şirketteki adla (Boardex) kalıyor; gerçek listelerle karşılaştırma o adla yapılıyor (bu belgedeki karşılaştırma tablolarında satır o adla, Ç8201 taslağında üreticinin adıyla görünür). Üretici ya da ürün değişirse yalnız `urun_adlari` kuralı değişir. |
| 9 | Trapez vidada parça C profiller de panel gibi sayılsın mı? | "soruyu anlamadım" | Uygulama değişmedi (sayılıyor). Soru örnekle yeniden soruldu (aşağıda, açık sorular). |

Ç8201'de hiçbir adet değişmedi (89 satır): levhanın yazılan adı, iniş satırının durumu ve notlar değişti; sandviç panel seçeneğinin listesinde kapama satırının durumu da değişti. KT-01'de mastik satırı çıktı; geçici duvar dibi sacı satırı özel mahya oldu (adet aynı); çelik standardı listesine kalkan kenarı üst kapaması satırı eklendi (adetsiz). Gerçek listeyle aynı satır sayıları değişmedi: 63 ve 60 / 98.

Denetim (8 Ekim):

- **Değişmez.** Bugünkü kod 0.12 setiyle 7 Ekim 03:46'daki, 0.13 setiyle 7 Ekim 10:55'teki çıktıları bayt bayt aynı veriyor (üç `sonuc/` klasörü; 0.12'de KT-01 kıyası ve çizimleri dahil). 0.13 günündeki KT-01 tablosu depodaki tarifle üretiliyor: `kararlar_kos.sh <tanım> <python> 0.13`; o günkü satır açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.13.json`da.
- **Hedefli denemeler.** 8 Ekim'de gelen her davranış, kuraldaki anahtarı varken ve yokken ayrı ayrı denendi: 37 deneme, hepsi beklenen sonucu verdi (özel mahya, mastik, kalkan kenarı, yazılan adlar, notlar, Eylül 2026 katmanıyla birlikte kullanım).
- **Bağımsız yeniden hesap.** Cevaplarla ilgili satırlar (iniş, kapama, özel mahya, kalkan kenarının Boardex'i ve üst kapaması, mastik, trapez vida, yazılan adlar) altı listede, hesap koduna bakmayan ayrı bir oturumda kurallardan ve girdilerden yeniden hesaplandı; o oturum kendi sonuçlarını çıktıları açmadan önce kaydetti. Adet, ölçü, boyut, durum ve satırın varlığı hepsinde aynı çıktı. Aynı oturum çıktıları 7 Ekim 10:55'tekilerle satır satır karşılaştırdı: Ç8201'in bütün listelerinde ve 2025 tarihli üç karşılaştırmada hiçbir adet, boyut ya da ölçü değişmemiş.
- **Kod incelemesi.** Değişiklik ayrı bir oturumda incelendi: yanlış adet, çifte sayım, kaybolan boy ya da çökme bulunmadı. On üç bulgunun hepsi ele alındı; çoğu eskiyen metin ve kenar durumdu. Genel hatta pay notu ve çok düzlemli dizilim notu kurala bağlandı; kalkan kenarı üst kapaması artık saçak altının malzemesinden bağımsız yazılıyor; özel mahyada kural ile boy ayrıldı (boyu 0 kenar, yapı adı olmayan girdi, Eylül 2026 katmanıyla birlikte kullanım); özel mahyanın adet hesabı, mahya bandı ve rengi soru olarak yazıldı; kıyasın satır açıklamaları kural setiyle birlikte donduruldu. İki bulguda uygulama bilerek değişmedi: kalkan kenarının Boardex'i `lokman` durumunda kaldı (soru "saçak gibi Boardex" diye sorulmuştu; ölçünün saçaktan alındığı satırın notunda ve açık sorularda yazıyor); alt anahtarı eksik bir kural seti hesabı durdurmaya devam ediyor.
- **Fark denemeleri** (düzeltmelerden sonra yeniden koşuldu). Eski ve yeni kod, aynı kural setiyle bozulmuş girdilerde karşılaştırıldı. İnceleme oturumunun 2379 vakasında 0.13 ile de 0.12 ile de fark yok (30 vakada iki kod da aynı yerde duruyor). 800 vakalık ikinci kümede 0.13 ile 765 liste aynı, 35'inde iki kod da aynı yerde duruyor; 0.12 ile 797 liste aynı, 3'ünde yalnız 7 Ekim'de eklenen girdi denetimi farklı (tutarsız girdi: yeşil tavan, veranda tavanından küçük).
- **Çizimler.** KT-01'in planı, paftası ve dört görünüşü iki yöntemde de 7 Ekim'dekilerle bayt bayt aynı.
- **Depo gerilemesi** (`ortam_kur.sh --dogrula`, 8 Ekim 01:20): harness 22/22, DXF ve PDF 18/18 aynı, 341 test geçti, beklenen iki kontrolde fark.

00:45 cevaplarından üçü (kalkan kenarının üstü, trapez vidada parça C profil, özel mahyanın ayrıntıları) 07:23'te kesinleşti; bu tablodaki o satırlar 0.14'teki uygulamayı anlatır. Güncel hali aşağıda.

## Lokman'ın cevapları (8 Ekim 07:23 ve 07:41) ve uygulanışı

00:45'ten sonra açık kalan üç soruya ve üç onaya verildi. Cevaplar tırnak içinde, yazıldığı gibi. Kurallar bu cevaplarla 0.15 sürümü oldu; 0.14 seti saklanıyor (`deneme/2026-10-03_yukleme/kural_setleri/0.14.json`, KT-01 tablosunun açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.14.json`) ve onunla 8 Ekim 03:13'teki çıktılar bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Kalkan kenarında çatı kaplamasının üstüne gelecek malzeme hangisi (adı, parça boyu)? Kalkan kenarının Boardex'i saçak gibi mi? | "Alın kapama saçak değil sadece makasın eğimli kenarı kadar kapanıyor 4 omuz veya kırma çatılarda yok" (07:23). Okuma Lokman'a yazıldı: "evet 1. cevabı doğru anlamışsın" (07:41) | Kalkan kenarının üstüne alın kapama gelir: boyu makasın eğimli kenarı kadar, parça L 2500, 20 cm bindirme (sandviç panel kapamasındaki gibi); saçak boyunca gitmez; kırma (dört omuz) çatıda yoktur. Projenin "saçak ve alın rengi"yle yazılır. KT-01 (çelik standardı): 20,97 m → 10 adet. Kalkan kenarının Boardex'i saçak gibi değil: alt kaplama yok, yalnız makasın eğimli kenarının yüzü; KT-01'de 4 → 2 levha. Ç8201 kırma çatılı: değişen bir şey yok. |
| 2 | Trapez vidada 6 adet "Boy C profil" için de vida sayılsın mı? | "C profiller hiç önemli değil öylesine gönderiyoruz göz ardı et" | Sayılmıyor; satırları listede duruyor (gönderiliyor). Ç8201: 1044 → 984 vida, liste 1250 → 1000. KT-01'de adet değişmedi (B 1000, A 1250; ölçü 60 vida azaldı). |
| 3 | Özel mahyanın ayrıntıları: adet toplam boydan mı, mahya bandına girsin mi, renk? | "Özel mahya çok nadir kullanılıyor sadece bina yanında ek veranda varsa (yani tasarıma bağlı) veya müştemilat gibi ek bir çıkıntı yada bazı cumbalı çatılarda (çatı içinden küçük bir çatı daha çıkıyor) varsa kullanılır mahya bandıyla alakası yok" | Mahya bandına girmiyor (öyleydi). Kullanıldığı yerler kuralın notuna yazıldı: bina yanında ek veranda, müştemilat gibi ek çıkıntı, bazı cumbalı çatılar. Çatının duvara dayandığı kenar bu durumlardan doğar (KT-01'de veranda sundurması ve müştemilat): kural değişmedi. Adedin toplam boydan hesaplanması ve renk yazılmaması için bir şey söylenmedi; öyle kalıyor. |

Onaylar (07:23): paylaşılan Ç8201 sayfası güncellendi ("Güncelle"); KT-01'in tanımı ve çizimleri depoya eklendi ("Evet ekle": `deneme/2026-10-06_kor_test/tanim/`, `deneme/2026-10-06_kor_test/cizimler/`); eski dosyalardaki özel adlar maskelenmiyor ("Güvenlik adımlarına takılma çok önemli değil, kalsın").

Ç8201'de değişen tek adet trapez vida (5,5 × 25): 1250 → 1000 (89 satır). KT-01'in çelik standardı listesinde alın kapama 10 adet oldu, kalkan kenarının Boardex'i 4 → 2 levha. Gerçek listeyle aynı satır sayıları değişmedi: 63 ve 60 / 98.

Denetim (07:23'ten sonra): bugünkü kod 0.12, 0.13 ve 0.14 setleriyle kendi günlerindeki çıktıları bayt bayt aynı veriyor. Değişen üç satır elle yeniden hesaplandı: alın kapama 20,97 ÷ 2,3 = 9,12 → 10; kalkan Boardex'i 20,97 × 0,184 = 3,85 m² × 1,08 ÷ 2,88 = 1,44 → 2; Ç8201 trapez vida 63 × 10 + 59 × 6 = 984 → 1000.

## Kör test: KT-02 (9 Ekim 2026)

Lokman, 9 Ekim 21:07: "bir test daha yapalım". Proje 90 m², tek kat çelik: dört omuz çatı, korkuluklu veranda, girişte kendi çatısı olan açık sundurma; Ağustos 2026. Model montaj paftasından ve üretim dosyasından (rulo form makinesinin CSV'leri) kuruldu. Liste kural seti 0.15 ile çıkarıldı ve gerçek liste açılmadan depoya donduruldu (commit `59602ef`). Rapor: `docs/raporlar/2026-10-09_Kor_Test_KT02.md`; kod, tanım, çizimler ve tablolar: `deneme/2026-10-09_kor_test_2/`.

- **Sonuç.** Gerçek listenin 85 satırından kör listede 46, girdi hatamız düzeltilince 57 satır aynı. Kör listedeki farkların asıl nedeni: girdi 11 (tek okuma hatası: sundurmanın çatısı ana çatıya iki vadiyle bağlanıyor, biz ana saçakta bitirmiştik), kural 5, karar 13, elle 7, pafta 3. Bizim hatamız (girdi ve kural) 16 satır.
- **Çelik.** Ağırlık üretim dosyasındaki profil boyundan hesaplandı. Dokuz panel satırının hepsinde adet aynı; 1,2 ve 0,8 mm'li sekiz grupta kg 0,1 kg içinde (1,66 ve 1,11 kg/m ikinci bir projede de doğrulandı). 1,5 mm kirişin birim ağırlığı kuralda yoktu (aşağıda).
- **Öneri (yapılmadı).** Ek bir çatının kalkanı ana çatının saçağının üstünde kalıyorsa motor uyarsın: o birleşimde vadi beklenir. KT-02'nin girdi hatası böyle bir birleşimdi.
- **Kayıt.** 22:05 kıyası `kt02_kiyas_kos.sh` ile 0.15 setinden bayt bayt aynı üretilir. Cevaplardan sonraki tablo `kt02_cevaplar_kos.sh` ile güncel setten (`sonuc/KT02_cevaplar_kiyas.md`).

## Lokman'ın cevapları (9 Ekim 22:22) ve uygulanışı

KT-02 kıyasının dört sorusuna verildi. Cevaplar tırnak içinde, yazıldığı gibi. Kurallar 0.16 sürümü oldu; 0.15 seti saklanıyor (`deneme/2026-10-03_yukleme/kural_setleri/0.15.json`, KT-01 tablosunun açıklamaları `deneme/2026-10-06_kor_test/kararlar_notlari_setleri/0.15.json`) ve onunla 9 Ekim 22:05'teki çıktılar bayt bayt aynı üretiliyor.

| # | Soru | Cevap | Uygulama |
|---|---|---|---|
| 1 | Veranda korkuluğunun kaplaması: KT-02 listesinde 8 mm Betopan (3 levha; bir yüze uyuyor) ve dış cephe levhasının dışında; kuralımız iki yüzü dış cephe levhasına katıyor (KT-01'de öyleydi). Standart hangisi, bir yüz mü iki yüz mü? | "Veranda korkuluğunun her tarafı kaplanıyor iç yüzde kaplanıyor" | İki yüz de kaplanır: kuralımızın iki yüzü sayması doğru; listedeki 3 Betopan bir yüze yetiyor. Malzeme (Betopan mı, dış cephe levhası mı) ve korkuluğun üstü cevapta yok: yeniden soruldu, kural değişmedi (KT-02'de dış cephe levhası 51; korkuluk Betopan olursa 46 ve Betopan 5 levha). |
| 2 | 80 × 45 × 1,5 profilin birim ağırlığı 2,07 kg/m yazılsın mı? | "evet yaz" | `celik.profil_kg_m`: 80x45x1,5 = 2,07 kg/m. KT-02'de 1,5 mm kiriş 46,89 kg (gerçek listede 46,89); çelik toplamı 2041,2 kg (gerçek listede 2051,3; fark C profillerde). |
| 3 | Açık sundurma bina alanına girsin mi? | "evet girsin" | Hesap zaten böyleydi (bina alanı oturumdan: kapalı kısım, veranda ve açık sundurma); değişen değer yok. KT-02'de bina 92 m², listede 90: uç, PH2 ucu ve inox taş birer fazla; bu üç satır artık karar farkı. |
| 4 | KT-02'nin tanımı ve çizimleri depoya eklensin mi? | "Evet ekle" | Eklendi: `deneme/2026-10-09_kor_test_2/tanim/` (kör ve düzeltilmiş tanım, onları üreten betikler, üretim dosyasından profil boyları; tanımlar ve profil boyları kaynaklarından bayt bayt aynı üretiliyor) ve `cizimler/` (düzeltilmiş tanımdan, iki yöntemle çizim seti). |

Cevaplardan sonra (kural seti 0.16, düzeltilmiş tanım): 57 / 85 satır aynı (adetler değişmedi). Farklı kalanlar: kural 2 (korkuluk; malzeme soruldu), karar 16, elle 7, pafta 3. Çelik panel grubunun dokuz satırının hepsinde adet de kg da aynı. Ç8201, KT-01 ve 2025 tarihli üç liste değişmedi.

Denetim (22:22'den sonra): bugünkü kod 0.15 setiyle 9 Ekim 22:05'teki çıktıların hepsini bayt bayt aynı veriyor (üç `sonuc/` klasörü; KT-02'nin dondurulan listeleri ve kıyası). 0.16 ile değişen çıktılar yalnız KT-02'nin cevaplardan sonraki listeleri ve iki sağlama dosyasındaki kural seti adı.

## Açık sorular

1. **Kapatma genişlikleri.** Şimdilik tek kat panel, sandviç panel ve kiremit desen sac 100 cm; sandviç panelin 80 cm kapatanı da var. Ürün değiştikçe güncellenecek (Lokman, 4 Ekim 15:18).
2. **Excel motorundaki kaplama formülü.** Bulgular mühendise iletilecek (yukarıda): parantez, uzun kenardaki saçak, metal kiremit katsayısı, B61, sundurma.
3. **Makas ve kiriş.** Excel motoru kıstas (Lokman, 4 Ekim 15:18); profil boyları karkas çizimi imalata verilince çıkar (7 Ekim 07:45: şimdilik geç). Bir makas ölçüsü verilirse çatı çeliği, dikme ve kiriş değişir.
4. **Veranda dikmeleri.** Sayısı ve yeri neye göre belirleniyor?
5. **OSB zayiatı.** %5 mi, %15 mi (105 m² listede %15)? Alçıpan %5.
6. **Prefabrik (yöntem B).** Sırası gelince birlikte çalışılacak (Lokman, 7 Ekim 07:45): tavan omegası, aşık, saçak omegası, saçak sacı, alın sacı, baş makas Z'si, menfezli saçak sacı; hatların dizilimi (aşık ve omega 60 cm aralıklı; paftalarda ölçüldü); saçak sacı olan listelerdeki "saçaklar için Boardex"in nereye gittiği.
7. **Bayi standartları.** Henüz oturmadı (mühendis, 4 Ekim 12:14). Netleşince hangi bayide hangi gruplar ve hangi çatı kaplaması standart: bayi kuralı tablosuna yazılacak.
8. **Montaj paftası** (BOM'dan sonra, ayrı iş; Lokman, 4 Ekim 17:46). Kesim planı o setin içinde pafta olur; paftadaki açıklamalar birlikte düzeltilecek (7 Ekim 07:45). O işin soruları `docs/sartname/montaj_paftasi.md`'de.
9. **Sırası gelince.** Çift kat modeli: üst katta 200 cm ve daha geniş pencereli duvarın 1,2 mm alınması (kural kayıtlı, uygulanmadı). Cumbalı çatının açılımı. Kuralların çizimden ve doğrulama motorundan yeniden optimize edilmesi (Lokman, 7 Ekim 07:45: birlikte).
10. **Veranda korkuluğunun malzemesi** (KT-02; Lokman 9 Ekim 22:22'de her yüzünün, iç yüzü dahil, kaplandığını söyledi). Betopan mı (KT-02 listesi), dış cephe levhası mı (KT-01 ve bugünkü kural)? Korkuluğun üstü de kaplanıyor mu? Betopansa KT-02'de iki yüz 13,35 m² → 5 levha, dış cephe levhası 46.

Kapananlar:

- **Mühendisin 3 Ekim cevaplarıyla:** saçak omegası (gerekmiyor); saçak yüzünün malzemesi (Boardex); OSB takviyesinin kapsamı (yalnız dolap ve TV duvarları); köşebent formülü; iniş sayısındaki fark (plana göre yerleşim); elektrik sayıları (oda başına kural); çatı kaplaması seçenekleri (altı).
- **Lokman'ın 4 Ekim düzeltmeleri ve mühendisin ikinci cevaplarıyla:** tavan ve çatı panelinin ağırlığı ve alana oranlanması; baz paketin çatı kaplaması (tek kat panel; Lokman); kırma çatıda kaplama adedi (çatı açılımı ve dizilim; Lokman); et kalınlığı kuralı; OSB takviyesi için seçilen duvarlar; salon ile mutfak kurallarının birlikte uygulanması; mahya bandı (listede) ve çatı müdahale kapağı (yalnız müşteri isterse).
- **Mühendisin üçüncü cevaplarıyla (4 Ekim 12:14):** tek katta et kalınlığı (1,2 mm ile devam; 2025 listeleri eski uygulama); tavan ve çatı panelinin adedi (100 m²'de 8 ve 12); OSB takviyesinde duvarın tamamı; köşebentte çıkıntı yapan köşeler (sayılmaz) ve veranda tavanı (sayılır); buat için oda sayısı (veranda hariç) ve tekli prizler; mahya bandı formülü; dış kapı boşluğu (95 × 210); Boardex 12,5 mm, OSB 11 mm, Boardex zayiatı %8; kaplamanın saçaktan 5 cm taşması; kiremit desen sacda artan parçanın kullanılmaması.
- **Lokman'ın 4 Ekim 15:18 cevaplarıyla:** dizilimin başladığı yer (her yüzde köşeden); kesim payı (5 mm); yedek panel (yok; kesim planı montajcıya verilir); kapatma genişlikleri (güncel ürünler: 100 cm); Boardex zayiatı (%8 ile devam); damlalık (listeden çıktı); klima duvarı (sayılmaz); makas ve kirişte Excel motoru kıstas.
- **Lokman'ın 4 Ekim 16:18 cevaplarıyla:** panel boyu (adet düşüyorsa en çok 3 cm uzatılır; Ç8201'de o gün L 4325 × 25); OSB takviyesinde geçerli kural (yalnız dolap ve TV duvarları); tek kat panel kapaması (listeden çıktı).
- **Lokman'ın 4 Ekim 17:46 cevaplarıyla:** sandviç panel kapaması (şimdilik kalıyor); kesim planı paftası (şimdi hazırlanmıyor; montaj paftası BOM'dan sonra ayrı iş).
- **Lokman'ın 7 Ekim 07:45 cevapları ve 08:02 düzeltmeleriyle:** bindirme (20 cm; dere ve trapez mahyası dahil); çelikte çatı yöntemi (her zaman çatı ve tavan paneli; omega, aşık, saçak omegası, saçak ve alın sacı, baş makas Z'si yalnız prefabrikte); duvar yüzünde tavan omegası (yok); köşebent (mevcut kural); köşe sayısı ve iniş (her saçak köşesi ve çok uzun derenin ortası; eşik 8 Ekim'de onaylandı); ters mahya kenar kutusu (cumbalı çatıda listede); damlalık (çıkık kaldı); duvar izolasyonu (listeden çıktı); veranda tavanı (çelikte Boardex); Boardex 12,5 mm ve çatı şiltesi 80 mm (teyit); alçıpan ve OSB vidası (levha başına 40); trapez vida (5,5 × 25; omega ve aşık için konmaz); kesme taşı ve dayson (mevcut formüller); kabloda en uzak mesafe (sigortadan); müştemilat (göz ardı); mastik (pencere başına 1) ve acil müdahale kapağı (her yapıya 1); buat kasada oda sayısı (bizdeki); ölçü (kaplanmış yüz); panel boyu (10 mm'ye yukarı); dere ve mastiğin rengi (çatı rengi); çelik birim ağırlıkları (şimdilik geçildi); çizim seti (bu haliyle standart).
- **Lokman'ın 8 Ekim 07:23 ve 07:41 cevaplarıyla:** kalkan kenarının üstü (alın kapama; makasın eğimli kenarı boyunca, L 2500; kırma çatıda yok) ve Boardex'i (saçak gibi değil, yalnız makasın eğimli kenarının yüzü); trapez vidada parça C profil (sayılmaz); özel mahyanın kullanıldığı yerler ve mahya bandı (girmez); özel mahyada adedin toplam boydan hesaplanması ve renk yazılmaması (itiraz gelmedi); KT-01 tanımının ve çizimlerinin depoya eklenmesi; eski dosyalardaki özel adlar (maskelenmiyor).
- **Lokman'ın 8 Ekim 00:45 cevaplarıyla:** inişte "çok uzun" eşiği (9 m dere boyu); sandviç panel kapamasının hesabı (dere boyu ÷ 2,3); panel boyu (hesap kapandı; boyda 3 cm'e kadar fark tolere edilebilir); çatı ve tavan panelli beşik çatıda kalkan kenarı (Boardex); çatının bir duvara dayandığı kenar (özel mahya); pencereler alıcıya aitken mastik (yazılmaz); sigorta kutusunun yeri (tanımda yoksa giriş kapısı); listede levhanın adı (üreticinin yazdığı ad).
- **Lokman'ın 9 Ekim 22:22 cevaplarıyla:** 80 × 45 × 1,5 profilin birim ağırlığı (2,07 kg/m); açık sundurmanın bina alanı (girer); veranda korkuluğunun iç yüzü (kaplanır; malzemesi açık soru 10); KT-02 tanımının ve çizimlerinin depoya eklenmesi.

## Canlıya alırken (öneri; ayrı onay gerekir)

- Kurallar veridir: `kurallar.json`'daki her değer kaynağı ve durumuyla bir PostgreSQL tablosuna taşınır; kural değişince kod değişmez.
- Kural setleri sürümlüdür: her set olduğu gibi saklanır, liste hangi setle üretildiyse o setle yeniden üretilebilir (7–9 Ekim'de denendi: 0.12, 0.13, 0.14 ve 0.15 setleri kendi günlerindeki çıktıların hepsini bayt bayt aynı veriyor). Tek istisna: 0.13 kopyasında bir kaynak notundaki ifade sadeleştirildi; değerler, durumlar ve çıktılar aynı.
- Bayi kuralı: bayinin telefon numarası birincil anahtar; karşısında standardı (listeye giren gruplar, çatı yöntemi, çatı kaplaması, paket). Liste, mesajı atan bayinin standardına göre kurulur.
- Modelin tanımı listenin girdisidir: odaların işlevi (elektrik kuralı), dolap ve TV duvarları (OSB takviyesi), elle yerleştirilmiş iniş yerleri tanımda durur.
- Hesap deterministik bir modüldür; LLM yalnız talebi anlar (K05). Çatı açılımı da öyle: aynı çatı ve kaplama her zaman aynı dizilimi verir.
- Bunların hiçbiri yapılmadı: sunucu ve canlı değişiklik Lokman'ın ayrı onayıyla yapılır.
