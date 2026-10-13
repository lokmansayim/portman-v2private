# A2 ve A3 · Prefabrik duvar

Kaynak: Lokman'ın anlattıkları (1–2, 6 ve 12 Ekim 2026). Astra dönemindeki prefabrik çizim kuralları (v1.4.3) 12 Ekim'de
`ref_prefabrik/astra_v1_4_3/` altına alındı (girdi; kural kitabına Lokman'ın teyidiyle girer). Prefabrik ayrı pano motorunda çizilir (D-10).

## Standart duvar kalınlığı (12 Ekim 2026)

- **Dış 100 mm / iç 60 mm** standarttır (Lokman, 12 Ekim 23:10: "evet kesinlikle"; D-10). Kayıt: `kurallar/model/duvar_tipleri.json` `PE-DIS-100`, `PE-IC-60`.
- **160 / 100 mm standart değildir** ("binde bir gelir"); 6 Ekim'deki 3+1 1150 × 1050 işi müşteriden gelen özel bir örnekti. Kural kitabına girmez;
  yalnız `kurallar/model/secenekler/duvar_kalinligi_160_100.json` seçeneği olarak durur. Aşağıdaki "Duvar kalınlığı seçeneği" bölümü bu seçeneğin kaydıdır.

## Panel (A2)

- Türkiye'deki prefabrik uygulaması dünyadakinden farklı: 8 mm betopan ya da fibercement iki levha arasında 80 mm, 16 dansite strafor (EPS). (1 Ekim)
- Panel ölçüsü 125 × 250, 280 ya da 300 cm. (1 Ekim)
- **Yükseklik dağılımı (13 Ekim 07:28): %80 H 2500, %19 H 2800, %1 H 3000 mm; "bunların dışında başka ölçü yok", 260 diye bir yükseklik yok.** Kayıt: **D-12**, `kurallar/model/duvar_tipleri.json` `PE-DIS-100.pano.yukseklik_dagilimi`. Motor başka yüksekliği açık hatayla reddeder; 280 / 300 yeni kod yolundan geçer (pano kodu 2800 / 3000, lento = yükseklik − 200; pencere üst kotu 200 sabit **çıkarımdır, teyit bekler**).
- Aksların 125,5 olmasının nedeni: birleşim elemanı olarak H profil kullanılıyor. (1 Ekim)
- Astra'nın prefabrik aks mantığı doğru. (1 Ekim)

## Ölçüye kesim (özel pano)

- Her pano 1255 mm. Dizilim yapının bitiş noktasına geldiğinde son parça kesilir; özel ölçülü pano olur. (6 Ekim 18:50)
- Dış ölçü verildiyse yapı o ölçüde çizilir; tam panoya yuvarlanmaz. Örnek: 11,50 × 10,50 m, verandasız. (6 Ekim 18:50)
- Çıkarım: dizilim soldan ve önden başlar; kesilen parça sağ ve arka uçta kalır.
- Çıkarım: iç duvarlar aks üstünde kalır; her iç duvar koşusu da kendi başından 125,5 cm ilerler ve son parçası kesilir.
- Örnek (dış 160 mm): 1150 cm → 8 tam pano + 114 cm; 1050 cm → 8 tam pano + 30 cm.
- **Motor'da (İE-11, 13 Ekim 2026):** `yapi.dis_olcu_cm` verilirse yapı o ölçüde kesilir (Adım 1, 6 Ekim yaması canlı Motor'a taşındı; `deneme/2026-10-06_kalinlik_160_100/` yaması artık gerekmez).
  Kesim ucu **parametredir**: `yapi.dizilim.baslangic` `on-sol` (eski; kesilen parça sağ ve arka uçta) ya da `arka-sol` (PK-01 paftası: y arkadan sayılır, kesilen parça sağ ve **ön** uçta).
  `yapi.dizilim.hiza` `kosu` (eski: her koşu kendi başından 125,5) ya da `izgara` (PK-01 paftası: ekler ızgara akslarında; ızgara dışı başlayan segment önce bir sonraki tam aksa kadar parça alır).
  Anahtar yoksa eski davranış sürer (P6001 bayt bayt aynı).
  **Çerçeve kuralı (arka-sol):** konumlar (`konum_cm`, `ek_akslar_cm`, `konum_pano`, sol/sağ duvardaki pano dizini) arkadan sayılır; cephe adları, menteşe ve dikmeler gerçek yöndedir. Yanlış çerçevede girilen değer hata vermez, başka yere çizer — İş Emri yazarken (ve Beyin'e bağlanırken) bu kural uygulanır.

## Kapı ve pencere yerleşimi (D-13; Lokman 13 Ekim 08:53)

- **Pencere** odanın net açıklığına ortalanır. Pencereli pano 125,5 cm'dir, yanları özel pano olur (PK-01: mutfak önde 60,25 + 125,5 + 60,25, salon önde 40,5 + 125,5 + 37,5). Izgaradaki pano oda ortasından en çok ¼ pano kaçıyorsa ızgara kalır. Anahtar: `dizilim.pencere: oda_ortasi`.
- **Kapı:**
  - Ucunda açılma tarafına dik duvar olan panoya konur; menteşe o uçtadır.
  - Bölmenin iki yanındaki oda kapılarının kanatları birbirine doğru açılır, ikisi de bölmeye yaslanır.
  - Oda kapısının boşluğu menteşe ucundaki pano kenarından 11,5 cm içeridedir; dış kapı panoda ortada kalır.
  - Kanat süpürme alanları çakışmaz.
  - Anahtar: `dizilim.kapi: mantik`.
- **Köşe:** L köşenin kolları arasında kapalı oda varsa düşey duvar uzar ve köşe parçası odanın dışına düşer. Veranda içindeki köşede yatay duvar uzar. Anahtar: `dizilim.kose: oda`.
- **Veranda duvarı:** çevrede olmayan dış düşey duvar aksa ortalıdır. Anahtar: `dis_dusey_duvar: cevre_aks_disinda`.
- Hepsi PK-01 montaj paftasının vektörleriyle ölçüldü (`deneme/2026-10-13_pk_01/pafta_oku.py`). Motor bu planda 50 panonun 50'sini, 38 H işaretinin 38'ini paftayla aynı veriyor.

## Aks dışı duvar ve dış duvar T bölmesi (PK-01; İE-11)

- Gerçek projede bir duvar 125,5 ızgarasının dışında olabilir (PK-01: hol/salon ön duvarı arkadan 795). `yapi.ek_akslar_cm` ile aks tablosuna eklenir; mahaller `konum_cm` ile aks sınırlarıyla verilir (aks olmayan değer hata). Ek aks paftada ana aks sayılır.
- PK-01 paftasında dış duvar, iç duvarın geldiği T'de bölünür ve oraya **dış üçlü H** konur (`yapi.dizilim.dis_duvar_t_bolme`; katalog "Üçlü H bağlantı dış", blok `BOM_*_UCLU_H_DIS_*`). Eski kuralda dış duvar bölünmez (6×8, P6001).
- Dış kapı ya da pencere alıcıya aitse `acikliklar[].dograma: "alıcıya ait"`: BOM satırı işaretlenir, doğrama yükleme listesine girmez; `ozellikler` tablosunda da yazar.

## Duvar kalınlığı seçeneği (müşteri örneği; standart değil)

- Dış duvar 160 mm, iç duvar 100 mm, yükseklik 2800 mm istendi. (6 Ekim 18:28) — **Tek bir müşterinin isteğiydi; standart 100 / 60'tır (12 Ekim 23:10, D-10).**
- Çıkarım: akslar kalınlıkla birlikte kayar. Düşey akslar dış duvarın iç yüzünden, yatay akslar duvar ekseninden başlar; tam modülde dış ölçü = pano × 125,5 + iki dış duvar (x) ve + bir dış duvar (y).
- Çıkarım: dış köşe parçası 160 × 80, iç köşe 100 × 50, üçlü H 100.

## Köşe dikmeleri

- Tek kat prefabrikte köşe kolonu 50 × 100. (2 Ekim 20:15)
- Çift kat prefabrikte köşe kolonu 100 × 100, 532 cm profil dikme. (2 Ekim 20:15)
- Bu değişiklik aksı bozmaz, dizilimi bozar. (2 Ekim 20:15)

## Çift kat prefabrik alt kat (A3)

- Alt kat karkaslı. (2 Ekim 20:15)

## Açık sorular

- Standart dış panonun katmanları 8 + 80 + 8 = 96 mm, anma kalınlığı 100 mm (pano motoru 10 cm; Astra 100 mm): 4 mm fark nerede — levha 10 mm mi, EPS 84 mm mi? (6 Ekim denemesi 100 mm panoyu 8 + 84 + 8 almıştı.) Pano motoru ileride `duvar_tipleri.json`'a katman toplamıyla bağlanırsa P6001'in dış ölçüsü 773'ten 772,2'ye kayar; bu yüzden bağlanmadan önce cevap gerekir.
- 100 × 100 köşe dikmesiyle köşedeki panel dizilimi nasıl değişiyor?
- Alt kat karkasının profilleri ve aralıkları.
- İç duvar (6 cm) neyden oluşuyor?
- Ölçüye kesimde son parça çok dar çıkarsa (örnek: 30 cm; iç duvarda 22 cm) ne yapılır? En az pano boyu var mı? (PK-01 paftasında en dar dış parça 37, iç 32.)
- Ölçüye kesimde dizilim hangi uçtan başlar? — **Projeye göre değişiyor; parametre (İE-11 `dizilim.baslangic`).** PK-01 paftası arkadan ve ızgaraya hizalı dizer; kural mı, o paftanın tercihi mi — ikinci kör testle (çift kat) görülecek.
- PK-01 mühendis soruları: pencere ve veranda hizası paftadan cevaplandı (D-13). Tavan omega adetleri açık (PR-2).
- 160 mm dış ve 100 mm iç duvarda köşe ve H bağlantı profilleri hangileri?
- 160 mm ve 100 mm panonun katmanları (levha ve dolgu kalınlığı).
