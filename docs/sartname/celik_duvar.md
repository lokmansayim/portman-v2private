# A1 · Çelik (LGF) duvar sistemi

Kaynak: Lokman'ın anlattıkları (1–2 Ekim 2026). Madde sonundaki tarih, söylendiği günü gösterir.

## Paketler ve katmanlar

| Paket | Dış duvar (dıştan içe) | İç duvar |
|---|---|---|
| Baz (başlangıç) paketi | Boardex + 80 mm çelik karkas (içinde mineral yün) + alçıpan | Alçıpan + 80 mm çelik karkas + alçıpan |
| Bir üst paket | Dış duvar karkası 140 mm | — |
| Onun üstü | — | İç duvarlarda 11 mm OSB gibi eklemeler |

- Boardex 12,5 mm; alçıpan 12,5 mm. (2 Ekim 20:24)
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

## Çıkarımlar (teyit bekliyor)

- 240'lık levha tam dört dikme aralığına oturur (4 × 60); yatay profiller 120 ve 240'taki levha ek yerlerine denk gelir.
- 122 × 244 levhada aynı düzen 61 cm aksla çalışır; yükseklik 270'te sabitse üstte 30 değil 26 cm kalır.
- Levha adedi = metraj ÷ levha alanı (120 × 240 için 2,88 m²), yukarı yuvarlanır.
- 270 cm duvarda lento 70 cm ise açıklıkların üst kotu 200 cm olur; pencere denizliği = 200 − pencere yüksekliği (120/180'de 20, 120/100'de 100, 60/40'ta 160 cm). Modeller pencerelerde bunu doğruluyor; kapılarda doğrulamıyor (başlık 214 ve 210).

## Açık sorular

- Mineral yün kalınlığı (80 mm ve 140 mm karkas için ayrı ayrı).
- Boardex kalınlığı: 2 Ekim'de 12,5 mm denildi; 2025 tarihli bir yükleme listesinde 8 mm yazıyor (`yukleme_listesi_celik.md`).
- Lento ve kapı yüksekliği: yükleme listesinde kapılar 90 × 214 ve 90 × 210; üç modelde de iç kapı başlığı 214, dış kapı başlığı 210 kotunda. "Lento her zaman 70 cm" pencereler için mi?
- Varsayılan levha: 120 × 240 (60 aks) mı, 122 × 244 (61 aks) mı? Modellerde dikme 61, kuşak 122; bir modelde dikme 62,5.
- Profil başlığı 45 mm mi, 54 mm mi? (Yükleme listesi 45; 81 m² model 54.)
- Bayiye giden ölçü bitmiş dış yüzden dış yüze mi?
- Paketlerin adları ve tam içerikleri.
