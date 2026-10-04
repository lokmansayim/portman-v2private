# A1 · Çelik (LGF) duvar sistemi

Kaynak: Lokman'ın anlattıkları (1–4 Ekim 2026; 4 Ekim 15:18 cevapları dahil) ve inşaat mühendisi Ubeydullah'ın üç tur cevabı (Lokman 3 Ekim 18:14'te, 4 Ekim 01:24'te ve 4 Ekim 12:14'te iletti). Lokman'ın söylediği ile mühendisin söylediği çelişirse Lokman'ınki geçerlidir (4 Ekim 15:18). Madde sonundaki tarih, söylendiği günü gösterir.

## Paketler ve katmanlar

| Paket | Dış duvar (dıştan içe) | İç duvar |
|---|---|---|
| Baz (başlangıç) paketi | Boardex + 80 mm çelik karkas (içinde mineral yün) + alçıpan | Alçıpan + 80 mm çelik karkas + alçıpan |
| Bir üst paket | Dış duvar karkası 140 mm | — |
| Onun üstü | — | İç duvarlarda 11 mm OSB gibi eklemeler |

- Boardex 12,5 mm; alçıpan 12,5 mm. (2 Ekim 20:24) Mühendis teyit etti: "Boardex 12.5 mm. OSB 11 mm." (4 Ekim 12:14) 2025 tarihli listelerde Boardex 8 mm, OSB 9 mm yazıyor; Excel motorunda Boardex 8 mm.
- Boardex zayiatı %8. (Mühendis, 4 Ekim 12:14) 2025 listelerinin çalışma kitabında %15'ti; o listelerdeki adetler %15'e uyuyor. Fark soruldu; Lokman: "devam et" (4 Ekim 15:18).
- Baz pakette duvar kalınlığı katmanların toplamıdır: 12,5 + 80 + 12,5 = 105 mm, yani dış duvar da iç duvar da 10,5 cm. (2 Ekim 20:24)
- Arşivdeki çizimlerde dış duvar 12, iç duvar 11 cm çizilmiş. Fark, çelikteki birleşimlerde vida kabarması ya da içlerde ince sıyırma sıva payıdır. Hesapta kullanılmaz: duvar "sıfır hatalı ve sıvasız" kabul edilir. (2 Ekim 20:24)
- Sıva grubu genelde verilmez. (2 Ekim 20:24)
- Çalışma baz paketle başlar ("bu şekilde başla"). Üst paketler modifikasyon olarak sonra gelir. (2 Ekim 20:15)
- 140 mm karkas yalnız dış duvarlarda uygulanır. Bayi "dışlar 140'lık olsun" dediğinde bu anlaşılmalı; seçim WhatsApp'ta onay kutulu formla da alınabilir (ayrı konu). (3 Ekim 11:49)
- Çatı ayrıntıları sonra gelecek. (2 Ekim 20:15)
- Katalogda teknik detaylar var. (2 Ekim 20:15)
- Çıplak (kaplamasız) karkas: dış duvar genelde 140 ve 80 mm; iç duvar %95 80 mm, 90 mm çok nadir, şimdilik göz ardı. (1 Ekim)
- İç paneller genellikle OSB + alçıpan. (1 Ekim)

## Ölçüyü belirleyenler

- Çelik yapı içindeki yalıtıma ve dışındaki kaplamaya göre ölçülendirilir. (1 Ekim)
- Yalıtım: mineral yün ya da taş yünü; en 60, boy 120; kalınlık değişir. (1 Ekim)
- Kaplama: Boardex 120 × 240. Dışta Boardex 122 × 244 gelirse genişlikte akslar 61 cm konabilir; yükseklik değişmez. (1 Ekim)
- Yükseklik genelde 270 cm. (1 Ekim)
- Çelikte aks mantığı teknik olarak yok; ama kaplama ve yalıtım malzemeleri yüzünden ölçü tamamen serbest değil. (2 Ekim 19:21)

## Ölçünün alındığı yer

- Dış duvarlar dıştan, iç duvarlar tam ortadan (aks) alınır. (2 Ekim 20:40)
- Sonuç: duvar kalınlığı değişse de dış ölçü değişmez; mahaller büyür ya da küçülür. Ç8201'de 12/11 cm yerine 10,5 cm duvarla kapalı net alan 57,8'den 58,4 m²'ye çıkar (`deneme/2026-10-02_celik/`).

## Açıklıklar

- Lentolar her zaman 70 cm olacak; geriye ne kalırsa. (2 Ekim 20:40)
- Çelik (LGF) yapılarda iç kapı için bırakılan boşluk: en 90, yükseklik 214 cm. Kasa sağda, solda ve üstte 5'er cm; altta 5 cm şap ve 2–3 cm parke payı; kanat 200 cm'e düşer. Hesap buna göre yapılır. (3 Ekim 13:27)
- Çıkarım: kanat eni 80 cm (90 − 2 × 5; listelerde "80'lik kanat").
- "Dış kapı boşluğu 95x210, iç oda kapı boşluğu 90x214 alınır." (Mühendis, 4 Ekim 12:14) Listelerde de boşluk 95 × 210, kapı 90 × 210; üç modelde dış kapı başlığı 210.
- Çıkarım: lento 70 cm kuralı pencerelerde uygulanıyor (üst kot 200); kapı boşlukları 214 (iç) ve 210 (dış).

## İç duvarda OSB takviyesi

- İç duvarlarda OSB yoksa, mutfak dolabı ve TV ünitesi takılırken mukavemet sağlasın diye OSB gönderilir: "salonun bir odası ile mutfağın 1 odasının tüm yüzeyini hesapla". (3 Ekim 13:27)
- "Bütün oda değil sadece dolap ve TV ünitesi gelen duvar metrajı alınır." (Mühendis, 3 Ekim 18:14)
- Uygulama: dolap ve TV ünitesi gelen duvarlar modelin tanımına yazılır (`osb_takviye.duvarlar`); her duvarın o odaya bakan yüzünün tamamı alınır, o yüzdeki boşluklar düşülür. Önceki okuma (salon ve mutfağın bulunduğu mahalin bütün duvarları) kalktı.
- Ç8201'de duvarlar katalog görselinden seçildi: banyo ile mutfak arası duvar, üst dış duvar (tezgâh ve eviye), hol ile yaşam alanı arası duvar (TV). 24,5 m² → 9 levha; planda turuncu çizgi.
- Seçimi mühendis doğruladı: "Evet doğru yeri almışsın. Ancak bunun yeri en doğru şekilde genel mimari planda mutfak tezgahı ve TV ünitesi yeri gösterilirse o kısımlar alınarak bulunabilir." (Lokman 4 Ekim 01:24'te iletti) Kural: yer, mimari plandaki tezgâh ve TV ünitesi yerinden alınır.
- "Duvarın tamamını al." (Mühendis, 4 Ekim 12:14) Duvarın yalnız dolap gelen bölümü değil, o yüzünün tamamı alınır.
- Klima duvarı sorusu üzerine Lokman (4 Ekim 15:18): "sen ilk seferdeki gibi say bayi maliyeti de göz önüne alıyor bunu bayiye belirtmem lazım şimdilik hangisi az ise onu baz al". Okuma (teyidi istendi): iki hesap yapılır. Biri odanın bütün yüzeyi (ilk hesap; 3 Ekim 13:27 kuralı), öteki yalnız dolap ve TV duvarları. Az olan baz alınır; öteki, bayiye belirtilmek üzere satırın notunda durur. Ç8201: duvarlar 24,5 m² → 9 levha (baz); Yaşam Alanı'nın bütün duvar yüzleri 42,5 m² → 15 levha (notta). Klima duvarı baz hesapta sayılmaz.

## Çelik ağırlığı

- Excel hesaplama motorundaki gibi hesaplanır: çeliğin et kalınlığı ve sırt kalınlığına göre, ortalama cephe uzunluğundan. Dış cephe (140'lıksa 140) ve iç cephe (80) uzunluğuyla kg verilir. (3 Ekim 13:27)
- Kirişler ve makaslar yaklaşık bir makas ölçüsünden ayrıca verilecek; sonra hesaplama motoruna eklenecek. (3 Ekim 13:27) O zamana kadar: "şimdilik Excel hesaplama motoruna uy". (Mühendis, 4 Ekim 12:14) Lokman: "şimdilik motoru kastas al"; motoru inceleyecek. (4 Ekim 15:18)
- İleride karkas için bir Blender eklentisi yapılacak: Vertex BD ya da FrameCAD gibi, SketchUp'taki eklenti (MRD framework) gibi. Şimdi konu değil. (3 Ekim 13:27)
- Motordaki birim ağırlıklar (kg/m), üç gerçek listeyle karşılaştırma ve et kalınlığı kuralının listelerle karşılaştırması: `yukleme_listesi_yontemi.md`.
- Mühendis birim ağırlıkları aynı değerlerle yazdı ve 140 × 0,8 duvarın 80 × 1,2 duvardan hafif olduğunu belirtti; kalınlığın neye göre seçildiğini yazmadı. (3 Ekim 18:14)
- Yöntem A'nın tavan ve çatı paneli: 100 m² binada tavan paneli 354,84 kg, çatı paneli 440,32 kg; alana oranlanır. (Lokman, 4 Ekim 01:24) Mühendisin 3 Ekim cevabında 8 adet 429,83 kg ve 12 parça 561,6 kg'dı; adetler oradan; mühendis 4 Ekim 12:14'te teyit etti ("100m2 için bu adetler üzerinden ilerleyebilrsin"). Ayrıntı `cati.md`.

### Et kalınlığı (mühendis; Lokman 4 Ekim 01:24'te iletti)

- Tek katlı binada zemin kattaki çelik 140 × 45 × 1,2 ya da 80 × 45 × 1,2 alınır.
- İki katlı binada zemin kat yine 140 × 45 × 1,2 ya da 80 × 45 × 1,2; üst kat 140 × 45 × 0,8 ya da 80 × 45 × 0,8.
- İki katlıda üst katta büyük pencere varsa (200 cm ve daha geniş) o duvar 1,2 mm alınır; genelde üst katta bir ya da iki duvar böyle tasarlanır.
- Okuma: cevapta "12 mm" ve "8 mm" yazıyor; 1,2 ve 0,8 mm'dir (aynı cevapta "1,2 mm et kalınlığında" diye de geçiyor).
- Uygulama: tek katta ve zemin katta dış ve iç duvarlar 1,2 mm; üst katta 0,8 mm. Üst kattaki geniş pencereli duvar kuralı kayıtlı (`kurallar.json`, `celik.et_kalinligi_duvar`); çift kat modeli gelince uygulanacak.
- "Tek katta et kalınlığını 1,2 mm alarak devam ediyoruz." (Mühendis, 4 Ekim 12:14) 2025 tarihli iki tek katlı 140'lık listedeki 0,8 mm eski uygulama olarak kayıtlı.

## Köşebent ve elektrik

- Köşebent = (bütün odaların tavan çevresi + bütün oda iç köşeleri × 2,7 m) ÷ 2,5. (Mühendis, 3 Ekim 18:14) Lokman'ın 13:27'deki m² ÷ 2,5 kuralının yerine geçti; o kural plan bilinmediğinde yedek.
- "Odaya doğru çıkıntı yapan köşeler sayılmıyor. Veranda tavan çevresi sayılır." (Mühendis, 4 Ekim 12:14) Uygulama: veranda tavanının çevresi brüt ölçüyle tavan çevrelerine eklenir; verandada köşe boyu eklenmez (okuma).
- Elektrik sayıları oda başına bir kuralla, yaklaşık %75 doğrulukla hesaplanabilir. (Mühendis, 3 Ekim 18:14) Kural ve sınaması: `yukleme_listesi_yontemi.md`. Modelin tanımında her mahalin işlevi yazılır.
- Buat kasa için "Veranda hariç odaları say. Yatak odası ve banyodaki prizler tekli." (Mühendis, 4 Ekim 12:14)

## Veranda çerçevesi

- Kaplanır; her projede sırtı 80 mm (çelik karkas), genişliği 30 cm. Ç8201'de kirişler yanlara ve karşıya, altlarına 240 cm dikme. (3 Ekim 13:27) Ayrıntı `cati.md`.

## Dış kaplama düzeni (270 cm)

- Boardex levha yatay durur: yatayda 240, düşeyde 120. (2 Ekim 19:31)
- Binanın alt tarafı bu şekilde bir sıra kaplanır; üstüne aynı şekilde bir sıra daha. (2 Ekim 19:31)
- En son 30 cm kalır; o kısım Boardex kesilerek yapılır. (2 Ekim 19:31)

## Karkas

- Dikeyde 60 ya da 61 cm aralıklarla, yatayda 120 cm aralıklarla. (2 Ekim 19:31)
- Dikeyde taşıyıcılık için kesiksiz profil; yatayda daha çok kaplama ve statik için kesikli profil. (2 Ekim 19:31)
- Köşelerde, pencere ve kapı üstlerinde çaprazlar atılır. Mimari için önemli değil; ek bilgi. (2 Ekim 19:31)
- FrameCAD gibi yazılımlar karkası tasarlayıp pafta ve makine verisi üretir; aynı mantık, kendi ölçüleriyle. (1 Ekim)

## Metraj

- Dış Boardex metrajı = dış duvarların tüm çevre uzunluğu × yükseklik − kapı ve pencere boşlukları. (2 Ekim 19:52)
- Yükleme listesi de çıkarılacak. (2 Ekim 19:52)

## Modellerden ölçülenler (2 Ekim 21:40; ayrıntı `skp_olcumleri.md`)

Üç çelik projenin SketchUp modelinden (62, 81 ve 90 m²) alındı; Lokman'ın teyidini bekliyor.

- Duvar yüksekliği üç modelde de 270,0 cm.
- Karkas derinliği: 81 ve 90 m² modellerde dış ve iç 80 mm; 62 m² modelde dış 140 mm, iç 80 mm.
- Dikme aralığı: iki modelde 61 cm, 90 m² modelde 62,5 cm.
- Yatay kuşaklar 122–124 ve 242–246 kotlarında.
- Pencere üst kotu 200 (lento 70). İç kapı başlığı 214, dış kapı başlığı 210: üç modelde de.
- Profil: 81 m² modelde C 80 × 54 × 10, et 1,2 mm; öteki iki modelde başlık 45 mm.
- 81 m² modelde 17 duvar paneli var; panel boyları 125–569 cm.

## Seçenek: dış duvar karkası 140 mm (3 Ekim 2026)

Tanım dosyası: `deneme/2026-10-02_celik/secenekler/dis_karkas_140.json`. Model tanımı değişmez; seçenek yalnız dış duvar tipini `DIS-140` yapar.

- Dış duvar kalınlığı katmanlardan: 12,5 + 140 + 12,5 = 165 mm (16,5 cm). İç duvarlar 10,5 cm kalır.
- Dış ölçü değişmez (dış duvarlar dıştan ölçülür); duvar içeri doğru kalınlaşır, dış duvara komşu mahaller küçülür.
- İç duvar aksları, açıklıklar ve çatı değişmez.
- Dış Boardex metrajı değişmez; dış duvarın iç yüzü (alçıpan yüzü) biraz azalır.
- Ç8201'e uygulaması: `modeller/C8201.md`.
- Çıkarım (teyit bekliyor): 140 mm pakette Boardex ve alçıpan baz paketle aynı sayıldı; yalnız karkas değişti.
- Yalıtım: 140 mm karkasta dış duvar yalıtımı çift kat (gerçek listelerden; 100 m² listede kalemin adında yazıyor, 105 m² listenin hesap sayfasında "dış × 2").
- Çelik: mühendisin kuralıyla tek katta dış duvar 140 × 45 × 1,2, iç duvar 80 × 45 × 1,2 (4 Ekim). 3 Ekim'de 0,8 mm varsayılmıştı: 140 mm dış karkaslı iki gerçek listede (2025, tek kat) dış duvar panellerinin çoğu 0,8 mm (üçer paneli 1,2 mm), iç duvarlar 80 × 0,8. O iki liste kurala uymuyor; mühendis kuralı yineledi (4 Ekim 12:14), listeler eski uygulama. Excel motorunun verisi kuralla uyumlu: 140 × 0,8 dış duvar yalnız iki katlı iki projenin üst katında; tek katlı 140'lık örnekte (55 m²) dış duvar 1,2 mm.
- Yöntem B'de (saçak sacı) dış duvar 14 cm olunca geniş saçak omegası (180 × 2500) kullanılır (Excel motorundaki not).

## Çıkarımlar (teyit bekliyor)

- 240'lık levha tam dört dikme aralığına oturur (4 × 60); yatay profiller 120 ve 240'taki levha ek yerlerine denk gelir.
- 122 × 244 levhada aynı düzen 61 cm aksla çalışır; yükseklik 270'te sabitse üstte 30 değil 26 cm kalır.
- Levha adedi = metraj ÷ levha alanı (120 × 240 için 2,88 m²), yukarı yuvarlanır.
- 270 cm duvarda lento 70 cm ise pencerelerin üst kotu 200 cm olur; pencere denizliği = 200 − pencere yüksekliği (120/180'de 20, 120/100'de 100, 60/40'ta 160 cm). Modeller pencerelerde bunu doğruluyor. Kapılar ayrı: iç 214 (Lokman, 3 Ekim 13:27), dış 210 (mühendis, 4 Ekim 12:14; modeller ve listeler).

## Açık sorular

- Mineral yün kalınlığı (80 mm ve 140 mm karkas için ayrı ayrı).
- OSB takviyesi: "ilk seferdeki gibi say … hangisi az ise onu baz al" sözünün okunuşu (iki hesap; az olan baz: Ç8201'de 9 levha, öteki 15 levha notta) teyit bekliyor.
- Varsayılan levha: 120 × 240 (60 aks) mı, 122 × 244 (61 aks) mı? Modellerde dikme 61, kuşak 122; bir modelde dikme 62,5.
- Profil başlığı 45 mm mi, 54 mm mi? (Yükleme listesi 45; 81 m² model 54.)
- Bayiye giden ölçü bitmiş dış yüzden dış yüze mi?
- Paketlerin adları ve tam içerikleri.

Kapananlar (mühendis, 4 Ekim 12:14): Boardex 12,5 mm ve OSB 11 mm; dış kapı boşluğu 95 × 210; tek katta et kalınlığı 1,2 mm; OSB takviyesinde duvarın tamamı.

Kapananlar (Lokman, 4 Ekim 15:18): Boardex zayiatı %8 ile devam (2025 listelerinden 2–3 levha az çıkıyor; `yukleme_listesi_yontemi.md`); klima duvarı baz hesapta sayılmaz; makas ve kirişte Excel motoru kıstas.
