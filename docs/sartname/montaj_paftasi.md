# Montaj paftası: klasörlerdeki örnekler, içerikleri ve yükleme listesiyle bağı

Kayıt tarihi: 4 Ekim 2026. Dayanak: Lokman, 4 Ekim 17:46 (liste sayfasındaki "Kesim planı paftası: açılımı, kesim planını ve ölçüleri tek bir PDF paftada toplayayım mı?" sorusuna): "BOM dan sonra montaj paftası için ayrı çalışacağız klasörleri dolaş ve montaj paftalarını bul ne demek istediğimi anlarsın".

Bu belge o dolaşmanın kaydıdır: montaj paftası nedir, hangi paftalardan oluşur, üzerinde ne yazar, yükleme listesiyle bağı nedir. Pafta üretimi bu belgenin konusu değil: ayrı bir iş, yükleme listesinden (BOM) sonra. "Çıkarım" diye işaretlenenler Claude'un okumasıdır; teyit edilene kadar kural sayılmaz.

## Anlaşılan

- **Montaj paftası tek bir çizim değil.** Her proje için hazırlanan, ortak çerçeveli bir pafta setidir. Çıkarım: montajcı sahada bununla çalışır; yükleme listesiyle birlikte gider (klasör adları: "Montaj Paftaları", "Yükleme ve Montaj", "Montaj Pafta ve Yükleme").
- **Kesim planı o setin bir paftasıdır.** Ç8201 için üretilen çatı açılımı ve kesim planı, setteki "çatı kaplaması yerleşim planı" paftasının kırma çatıdaki karşılığıdır. Ayrı bir belge olarak değil, setin içinde verilecek.
- **Liste ile pafta aynı dizilimi anlatır.** Gerçek listelerdeki dizilime bağlı sayılar (kaplama adedi ve boyu, iniş sayısı, tavan omegası) paftadan geliyor (aşağıda). Çıkarım: pafta çalışmasında dizilim bir kez kurulur; liste de pafta da ondan üretilir, çatı kaplamasında yapıldığı gibi.
- Önceki yol haritasında "üretim paftası (sonraki aşama)" diye geçen iş budur (21 Eylül notu: ön onay paftasının hedef formatı; Lokman'ın Mac çalışma klasöründe, `01_Talep_Semasi/`).

## Nerede, ne kadar

Lokman'ın bağladığı üç klasör salt okunur dolaşıldı (4 Ekim 2026). Finans, sözleşme ve resmi evrak klasörleri açılmadı. Sayım kuralı: adında "montaj" ya da "pafta" geçen klasörler ve dosyalar.

| Ne | Sayı |
|---|---|
| Adında "montaj" ya da "pafta" geçen klasör | 13 (11'i 2025–2026 bayi projelerinde, 2'si 2019 ve 2020 tarihli proje klasörlerinde) |
| Bu klasörlerdeki PDF | 84: 80 pafta, 4 yükleme listesi. Yıla göre: 2019'da 6, 2020'de 5, 2025'te 64, 2026'da 9 |
| Kâğıt boyu | A4 41, A3 8, A1 9, A0 26. En yeni set (Ocak 2026) A3 ve numaralı (1–8) |
| Adında "montaj" ya da "pafta" geçen dosya | 85: 30 DWG, 25 PDF, 23 BAK ve 7 başka dosya |
| Şablon | Şirket klasörünün kökünde "Güncel Şablon 2024" (DWG ve DXF): pafta çerçeveleri, başlıklar ve "Omega ve Aşık" ölçü stili içinde; A3 ve A4 yatay ve dikey yerleşim sayfaları var |

Pafta türüne göre (80 pafta; tür, paftanın başlık yazısından):

| Pafta | PDF | Klasör |
|---|---|---|
| Tavan omega yerleşim planı | 9 | 8 |
| Makas ve dere yerleşim planı | 9 | 8 |
| Aşık yerleşim planı | 8 | 8 |
| Çatı kaplaması yerleşim planı | 8 | 8 |
| Müşteri onay paftası | 7 | 7 |
| Elektrik yerleşim planı | 7 | 7 |
| Duvar panelleri yerleşim planı | 7 | 6 |
| Montaj ve elektrik planı (prefabrik) | 5 | 4 |
| Özel büküm sac paftaları | 4 | 2 |
| Döşeme yerleşim planı | 2 | 2 |
| Döşeme kaplaması (Betopan) yerleşim planı | 2 | 2 |
| Merdiven yerleşim planı | 1 | 1 |
| Duvar kaplamaları (OSB) yerleşim planı | 1 | 1 |
| Başlığı okunamayan (2019 seti taranmış görüntü; 2020 setinde ve iki yeni paftada başlık yazısı yok) | 10 | 4 |

## Proje klasörünün düzeni

Yedi proje klasöründe aynı alt klasörler var: `ALPHA`, `Arkitech`, `DXF`, `Fotoğraflar`, `LyteCad`, `Malzeme Listesi`, `Montaj Paftaları`, `PROJE`, `Pencere Siparişi`, `SKETCHUP`, `Sözleşme`, `Üretim Dosyası` ve bir çalışma takvimi dosyası.

- Paftaların kaynağı `PROJE` klasöründeki tek bir ana DWG'dir ("… MONTAJ PAFTALARI"). İncelenen iki ana DWG'de bütün paftalar model alanında yan yana çizilmiş; `Montaj Paftaları` klasöründeki PDF'ler oradan, pafta başına bir dosya olarak basılmış.
- Ana DWG'deki sıra (tek kat): beton planı → müşteri onay paftası → zemin kat duvar panelleri → makas ve dere → tavan omega → aşık → çatı kaplaması → elektrik. Aynı dosyada çift kat için ikinci bir sıra duruyor (şablondan): 1. kat duvar panelleri, 1. kat tavan omega, duvar kaplamaları ve merdiven eklenmiş.
- Yükleme listesi bazı projelerde paftalarla aynı klasörde duruyor (üç klasörde çalışma kitabı, ikisinde PDF); standart düzende ayrı bir `Malzeme Listesi` klasörü var.

## Çerçeve (bütün paftalarda ortak)

- **Sol sütun: proje ek detayları.** Bina yüksekliği; dış ve iç duvar kalınlığı; panel türü; çatı şekli; dış ve iç cephe kaplaması; çatı kaplaması ve rengi; dış kapı; iç kapılar; dış ve iç cephe boyası; tavan şekli; saçak rengi; saçak çıkması; dere inişi ve rengi (prefabrik setlerde yağmur oluğu ve iniş borusu); açıklama. Altında serbest metin için bir kutu.
- **Sağ sütun.** "Çatı şekli" (küçük çatı çizimi ve numaralı notlar); "montaj detayları" (detay çizimleri: dış duvar köşe birleşimi, dış duvar ile iç duvarın T bağlantısı, çatı detayı 1/5); paftaya göre değişen üçüncü bir kutu ("pencere görünüşleri", "çatı detayları", "kaplama malzemesi", "lejant").
- **Alt şerit.** Pafta başlığı, satış temsilcisi, müşteri ya da proje adı, çizen, logo.
- Panel türü alanında üç değer görüldü: çelik karkas, pres panel, poliüretan panel.

## Setteki paftalar

Çelik tek kat (105 m², Kasım 2025; 8 pafta) örnek alınarak:

| Pafta | Üzerinde ne var |
|---|---|
| Müşteri onay paftası | Tefrişli kat planı, oda adları ve alanları, toplam alan ("veranda hariç"), doğrama etiketleri (K: 90/210, 200/180 sürgülü…), pencere görünüşleri, proje ek detayları |
| Zemin kat duvar panelleri yerleşim planı | Planda panel adları (D01–D36, K01), ölçü zincirleri, birleşim detayları. Notlar: "Duvar birleşimleri köşebent ile birleştirilecektir", "Dış duvarlarda çift kat izolasyon malzemesi kullanılacaktır" |
| Zemin kat tavan omega yerleşim planı | Oda oda omega hatları; her parçanın boyu yazılı (tam parça 365). Not: "Ters tavan yapılacaktır" |
| Makas ve dere yerleşim planı | Makas adları (MK01–MK20) ve aralıkları (yazı 117 cm: makaslar arası net açıklık; makas 8 cm, eksen aralığı 125 cm), dere hattı, iniş işaretleri (iç içe iki daire), dış ölçüler. Not: "Alın ve saçak çıkmaları 30 cm olacaktır" |
| Aşık yerleşim planı | Çatı yüzleri açılmış; aşık hatları ve parça boyları (tam parça 410). Not: "Aşıklar 60 cm aralıklarla…"; mahya aşığı 20 cm'de |
| Çatı kaplaması yerleşim planı | Yüzler açılmış ve şeritlere bölünmüş; kaplamanın adı, boyu ve adedi ("87 × 300: 24 adet; 87 × 280: 30 adet"); çatı alanı (124 m²) ve kaplama alanı (135 m²); "çatı izolasyonu: çift serim" |
| Duvar kaplamaları yerleşim planı | OSB gelen duvarlar ölçüleriyle: "mutfak dolabı arkası ve TV arkası OSB" (üç duvar: 330 + 820 + 436 cm) |
| Elektrik yerleşim planı | Tefrişli planda anahtar, priz, aydınlatma, zil, uydu ve sigorta kutusu işaretleri; lejant; malzeme notu |

Öteki ürünlerde:

- **Prefabrik tek kat** (pres panel ve poliüretan panel; 2025 ve Ocak 2026 setleri): müşteri onay paftası; montaj ve elektrik planı (panel yerleşimi ile elektrik aynı paftada); tavan omega; makas ve dere; aşık; çatı kaplaması; bazı setlerde ayrı elektrik planı. Ocak 2026 seti sekiz numaralı A3 pafta; yükleme listesi aynı klasörde.
- **Çelik çift kat** (160 m²; 13 pafta): zemin ve 1. kat duvar yerleşimi; zemin ve 1. kat tavan omega; döşeme yerleşimi; döşeme kaplaması (Betopan); merdiven; makas ve dere; çatı kaplaması; elektrik; müşteri onay paftası; iki özel büküm sac paftası (alın sacı, saçak sacı). Aşık paftası yok. Çatı kaplaması paftasında bir metraj kutusu var: sandviç panel boy boy adet (630 cm 10 adet, 450 cm 10 adet, 200 cm 4 adet), tepe mahya 12 m, alın sacı 25 m, dere altı sacı 23 m, saçaklar için Boardex 13 m, saçak ile duvar birleşimi köşebent 25 m, "Sandviç Panel Kapak L saç: 20 m".
- **Beton planı** ana DWG'de var; basılı setlerde görülmedi.
- Döşeme Betopan'ı için ayrı bir "kesim planı" çizimi de var (ana DWG'lerde, başka bir projeden kalmış): kesim planı kavramı bugünkü uygulamada döşemede kullanılıyor.

## Kırma çatıda bugünkü uygulama

- Sekiz çatı kaplaması paftasının hepsi beşik çatıda: yüz dikdörtgendir, şerit sayısı ve boyu doğrudan okunur.
- Klasörlerdeki kırma (dört omuz) çatılı tek projede (62 m², sandviç panel) kaplama paftası yalnız ana DWG'de duruyor; PDF'i basılmamış. Paftada dört yüz dikdörtgen çizilmiş: iki yüzde onar şerit, iki yüzde dört ve üç şerit; ayrıca giriş saçağı için iki kısa parça. Yazılar: "Sandviç Panel 4 cm", 100 × 320 "27 adet", 100 × 100 "2 adet", "Çatı alanı: 77,5 m²", "Kaplama alanı: 88,5 m²". Listedeki 27 uzun ve 2 kısa panel buradan.
- Çapraz kesim, artan parçanın karşı yüzde kullanılması ve hangi parçanın hangi panelden çıktığı paftada yok. Ç8201 için üretilen açılım, kesim planı ve kesim ölçüleri (`deneme/2026-10-03_yukleme/sonuc/`) bu boşluğu dolduruyor; bugünkü uygulamanın ilerisinde.

## Paftalar ile yükleme listesinin bağı (üç gerçek proje)

Üç gerçek listenin projelerinin paftaları listelerle karşılaştırıldı: 62 ve 90 m² projelerde ana DWG, 105 m² projede PDF paftalar. Tablo ve okuma `yukleme_listesi_yontemi.md`'de ("Montaj paftalarının yükleme listesiyle bağı"); özet:

- **Çatı kaplaması.** Listedeki adet ve boy paftadakinin aynısı: 62 m²'de 27 + 2 kısa; 105 m²'de 24 + 30; 90 m²'de çatı OSB'si 39 ve metal kiremit 28 + 2. Paftadaki "kaplama alanı" adet × boy × kapatma genişliğine denk geliyor (62 m²: 27 × 3,2 + 2 × 1,0 = 88,4 m²).
- **Dere inişi.** Listedeki sayı paftadaki iniş işaretlerinin sayısı: 62 m²'de 7 (dört köşe, arka cephede bir tane, giriş saçağının iki ön köşesi; ön cephenin ortasında yok), 105 m²'de 10. 90 m²'de (beşik çatı) paftada 8, listede 7: üç saçak çizgisinin uçlarında altı, iki uzun saçağın ortasına yakın iki; verandanın kademeli kısa saçağının iç köşedeki ucundaki işaret çizginin üzerinde değil, yanında. Lokman'ın kuralı ("her köşeye iniş") hesapta dört köşe sayıldığı için 6 veriyordu; aradaki farkın nedeni buymuş. Köşenin nasıl sayılacağı Lokman'a soruldu.
- **Tavan omegası.** Üç projede de listedeki adet, paftadaki parçaların 365'lik boylara en iyi yerleşiminden bir fazla (25 + 1, 39 + 1, 43 + 1). Alan formülümüz 26, 37 ve 42 veriyor. Hatlar 60,0 cm aralıklı (62 ve 90 m² projelerde ölçüldü).
- **Aşık.** Hatlar 60,0 cm aralıklı (62 ve 90 m² projelerde ölçüldü; biri sandviç panelli), mahya aşığı 20 cm'de. Listedeki adet paftadaki en az boydan 0–2 fazla (39 / 41, 55 / 57, 71 / 71).
- **OSB takviyesi.** Paftada dolap ve TV arkası duvarlar işaretli (105 m²: brüt 42,8 m²; listede net 39,3 m², 15 levha). Lokman'ın 4 Ekim 16:18 kuralıyla aynı.
- **Elektrik.** Excel motorunun notu: sayılar "montaj paftasından sayılır".
- **Öteki izler.** Dış duvarda çift kat izolasyon (140 mm karkaslı projede); "saçak çıkması: 30 cm / saçak sacı üzerinde boardex" (62 m²); çatı izolasyonunda "çift serim" (105 m²); çift kat projede "Sandviç Panel Kapak L saç: 20 m" (iki ana yüzde onar şerit × 100 cm: kapama saçak boyunca).

## Şablondan kalan yazılar ve elle düzeltmeler

Pafta çalışmasının neyi düzelteceğini gösterdiği için kaydedildi:

- "Çatı m²: 120" yazısı üç projenin aşık paftasında da aynı; bu projelerin çatı alanları kendi kaplama paftalarında 77,5, 107,3 ve 124 m².
- Bir makas paftasında iki makasın arası için not düşülmüş: ölçü çelik detay yazılımında düzeltilmiş, paftada yalnız ölçü yazısı değiştirilmiş.
- Çerçevede doldurulmamış ya da soru işaretli alanlar var ("30 cm / BORDEX?").
- Kırma çatının kaplama paftası dikdörtgen yüzlerle çizilmiş (yukarıda).

## Pafta üretimi için gereken veri

| Pafta | Gereken veri | Bugün elimizde |
|---|---|---|
| Müşteri onay paftası | Plan, odalar, doğramalar, tefriş, seçenekler | Plan ve görünüşler tanım dosyasından çiziliyor (`deneme/2026-10-02_celik/`); canlıdaki Motor bayiye giden planı çiziyor. Tefriş ve bu çerçeve yok |
| Duvar panelleri | Karkas panel bölümlemesi (panel adı, boyu, yeri), birleşim detayları | Yok. Çelik kg duvar boyu × birim ağırlıkla hesaplanıyor |
| Tavan omega | Odalar, omega aralığı (60 cm), parça boyu (365) | Dizilim yok; adet alan formülüyle (yalnız yöntem B) |
| Makas ve dere | Makas dizilimi (ad, aralık), saçak çizgisi, iniş yerleri | İniş kuralı ve çatı planı var; makas dizilimi yok (makas ve kiriş ölçüsü açık) |
| Aşık | Çatı açılımı, aşık aralığı (60 cm; mahya aşığı 20 cm), parça boyu (410) | Kırma çatının açılımı var; aşık dizilimi yok (yalnız yöntem B) |
| Çatı kaplaması | Çatı açılımı, dizilim, kesim planı | Var (kırma çatı): açılım, kesim planı, kesim ölçüleri. Beşik çatı ve cumbalı çatı yok |
| Duvar kaplamaları (OSB) | Dolap ve TV ünitesi gelen duvarlar | Var: kural ve modelin tanımındaki duvarlar |
| Elektrik | Odaların işlevi, işaretlerin yeri | Sayım var (oda başına kural); işaretlerin plandaki yeri yok |
| Çerçeve | Proje ek detayları, notlar, detay çizimleri | Seçeneklerin çoğu tanımda ve kurallarda; çerçeve ve detay çizimleri şablonda |

## Baz alınan yöntem için örnek yok

Bulunan paftaların hepsi tavan omegası ve aşıkla hazırlanmış (yöntem B). Baz alınan yöntemde (A: çatı ve tavan paneli; Lokman, 3 Ekim 13:27) tavan omegası ve aşık yok. Çıkarım: A yönteminde bu iki paftanın yerini tavan paneli ve çatı paneli yerleşimi alır; klasörlerde örneği yok, Lokman'a sorulacak.

## Pafta işi başlarken sorulacaklar

1. Duvar ve makas panellerinin bölümlemesi (D01…, MK01…) çelik detay yazılımından mı alınacak, Portman mı üretecek?
2. A yönteminde tavan paneli ve çatı paneli paftası nasıl olmalı (örnek yok)?
3. Pafta boyu: son set A3 ve numaralı; öncekiler A4 ve A0. Standart hangisi?
4. Çerçevedeki logo ve künye bayiye göre değişiyor mu?
5. Elektrik işaretlerinin yeri kuraldan mı çıkacak, elle mi yerleştirilecek?
6. Beton planı ve özel büküm sac paftaları sete dahil mi?
7. Kırma çatıda kaplama paftası: açılım ve kesim planı tek paftada mı, iki paftada mı; kısa yüzlerdeki 10 cm'lik son şerit nasıl gösterilecek?

## Sınırlar

- 84 PDF'in yazıları betikle okundu (başlık ve çerçeve alanları); dört set (çelik tek kat 105 m², çelik tek kat sandviç panelli, çelik çift kat, prefabrik Ocak 2026) ve iki ana DWG (62 ve 90 m²) pafta pafta incelendi. 2019 setinin PDF'leri taranmış görüntü; yazıları okunamadı.
- Ana DWG'ler bulutta açık kaynak LibreDWG ile DXF'e çevrilip okundu; Lokman'ın Mac'ine bir şey kurulmadı, dosyalar değişmedi.
- Parça boyları 62 ve 90 m² projelerde "Omega ve Aşık" ölçü stiliyle yazılmış ölçülerden, 105 m² projede PDF'teki ölçü yazılarından alındı. "En iyi yerleşim" kesim payı sayılmadan hesaplandı; 105 m² aşık paftasında boydan uzun iki ölçü tam boy ve artan parça diye bölündü, saçak sırasındaki iki ölçü parça sayıldı (sayılmazsa en az boy 71 yerine 69).
- Bağımsız denetim (4 Ekim): sayım, bu hesabı ve sonuçlarını görmeyen ayrı bir Claude oturumuna yeniden yaptırıldı. Parça sayıları, toplam boylar, en az boy sayıları (alt sınırla kanıtlı), iniş işaretlerinin sayısı ve yeri, kaplama yazıları ve hat aralıkları aynı çıktı. Klasör sayımı (13 klasör, 84 PDF) ayrıca denetlenmedi; sayım betiği iki kez koşuldu.
- Müşteri, bayi, çizen ve satış temsilcisi adları alınmadı. Paftalar ve DWG'ler Lokman'ın Mac'inde; çevrilmiş DXF'ler ve onlardan üretilen görüntüler yalnız bu oturumun geçici alanında. Hiçbiri depoda değil.
