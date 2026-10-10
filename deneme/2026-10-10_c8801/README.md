# 10 Ekim 2026 · Ç8801: kural kitabının yeni bir modelde sınanması

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı. Motor öteki klasörlerde: `../2026-10-06_kor_test/` (tanımdan girdi, çizim seti), `../2026-10-03_yukleme/` (yükleme listesi), kurallar `../../kurallar/`.

Lokman, 10 Ekim 2026 11:39: "seninle yazdığımız kurallar bu kadar farklı model bence kafi istersen testini bir sonraki model olan ç8801 de yap".

Ç8801 PortatifEv'in katalog modelidir: tek kat çelik, 2+1, 88 m² (veranda dahil). Kör test değildir: bu model için arşivde yükleme listesi, montaj paftası ve karkas modeli (SKP) yok. Sınav şu: kural kitabı, kuralları yazılırken hiç görülmemiş bir modelde, elle düzeltme yapılmadan çizim setini ve listeyi çıkarabiliyor mu; kuralın kapsamadığı yerler nerede. Liste Lokman'ın incelemesi içindir.

## Girdi

- **Kaynaklar** (PortatifEv arşivi, `Arşiv/TEK KAT ÇELİK/`): planlar DWG'sindeki Ç8801 planı (duvar çizgileri, pencere ve kapı blokları, ölçüler; LibreDWG ile DXF'e çevrildi), katalog paftası `PORT-Ç8801.jpg` (aynı plan, ölçü zincirleri, mahal alanları) ve üç katalog görseli (`ç_8801_1_R_Photo - 1, 2, 5.jpg`; çatı ve veranda).
- **Tanım** (`tanim/C8801.json`, Yapı Tanımı 0.5; `tanim/c8801_tanim_uret.py` üretir). Dış ölçü 1024 × 860 cm; batı blok 624 × 640, doğu kanat 400 × 860, güneybatıda 624 × 220 veranda. Baz paketin duvarı: 8 cm karkas, iki yüzde 1,25 cm kaplama. 6 dış, 7 iç duvar; 9 pencere (120/180 üç, 80/180, 120/120 dört, 60/40), dış kapı 95 × 210, beş iç kapı 90 × 214. Panel adetleri kuraldan tahmin (katalog modeli).
- **Mahaller** (kaplanmış yüzler arası; katalog etiketi parantezde): yaşam alanı 21,34 (21,0) · mutfak 10,05 (10,0) · hol 7,38 (7,3) · yatak odası 12,74 (12,6) · yatak odası 11,79 (11,6) · banyo 4,68 (4,7) · veranda 13,73 (13,8) m². Kapalı net 67,98 m²; bina alanı 88,06 m² (katalogdaki 88 m² verandayı içerir).
- **OSB takviyesi:** yaşam alanı ile mutfak arasındaki duvarın iki yüzü (TV ünitesi, mutfak dolabı; katalog paftasındaki eşyadan).

## Çatı: varsayım (Lokman'a soruldu)

Görsellerde: L biçimli beşik; batı blokta batıya bakan kalkan, doğu kanatta güneye bakan kalkan; doğu cephede saçak boydan boya (doğuda kalkan yok); iki mahya aynı yükseklikte birleşiyor. Kuzey cephe görsellerde yok.

Varsayım: kanadın mahyası kuzey–güney boydan boya (güneyde ve kuzeyde kalkan); batı bloğun mahyası doğu–batı, kanadın mahyasına aynı kotta bağlanır, iki yanında birer vadi. Saçak 30 cm, saçak kotu 280 (makas üstü). Standart eğim %33'tür (Excel hesaplama motoru, Ç8201, kör test projeleri). Ama batı bloğun açıklığı (640 cm) kanadınkinden (400 cm) büyük: iki yüz de %33 olursa batı bloğun mahyası kanadınkinden 40 cm yüksek kalır ve doğuda bir kalkan gerekir; görsellerde yok. Mahyalar aynı kotta ancak eğimler farklıysa buluşur. Varsayım: batı blok %33, kanat %50,2 (mahya kotu 395,5). Görsellerde de kanadın kalkanı dik görünüyor. Öteki seçenek (kanat %33, batı blok %21,7; mahya 355,9) üreticideki `STANDART` sabitiyle denenir.

Sonuç: 5 düzlem, yüzey 92,82 m² (plan 86,0); saçak 23,88 m · mahya 17,74 · vadi 8,69 · alın (kalkan kenarı) 17,67 m. Kalkanlar: batı 4,65, kanadın güneyi 3,01, kuzeyi 3,03 m².

## Veranda: çatısız (pergola)

Görsellerde verandanın üstünde çatı yok; ahşap pergola ve ahşap korkuluk var. Tanımda verandanın örtüsü yazılır (`ortu: "pergola"`). Çatısız verandanın tavanı yoktur: veranda tavanı (Boardex), tavan paneli, köşebentteki veranda çevresi ve tavan omegası onu saymaz; çatı çeliğinin oturumundan (tavan ve çatı paneli) ve şilte hesabından düşülür. Bina alanına girer. Pergola ve korkuluk modelde ve listede yok (Lokman'a soruldu: listede olacak mı, malzemesi ne).

Bu, motora eklenen tek yenilik (kural değil, modelin anlatılabilmesi için): `yapi.py` (örtü alanı), `girdi_genel.py`, `yukleme.py` (yeşil tavan satırının formülü ve notu, şilte), `ifc_genel.py` (verandada tavan yok). Tanımda alan yoksa (bütün eski modeller) hesap öncekiyle aynı; değişmezler denendi (aşağıda). Pafta bilgi satırında, tanımda çatı kaplaması yazmıyorsa kural kitabındaki baz paket kaplaması yazılır (önceden "—").

## Liste (kural seti 0.19, yöntem A: çatı ve tavan paneli)

`sonuc/C8801_yukleme.md` (93 satır). Öne çıkanlar:

- **Çelik** 2.332 kg: dış duvar 37,68 m (766 kg), iç duvar 23,23 m (459 kg), çatı makasları 86 m² × 5,65 kg/m² (motorun "beşik + cumba" ortalaması; 486 kg), tavan ve çatı paneli verandasız oturumla 74,34 m² (264 + 327 kg).
- **Çatı:** tek kat panel 15 × L 3740 + 21 × L 2630 = 36. Vadinin kestiği 13 şerit eşlenemiyor: kesilen parça şeridin çoğu, artan küçük bir üçgen. Mahya 7, ters mahya 4, kenar kutusu 8, mahya bandı 4, şilte 9.
- **Kalkan kenarı** (yöntem A, Lokman 8 Ekim): Boardex yüz 3,30 m² (2 levha), alın kapama 17,67 m (8 × L 2500).
- **Dere:** 23,88 m (7 × L 4000), 4 hat, 6 serbest uç (kapak 6). **İniş 7:** dört dış köşe, verandanın iç köşesi (iki derenin buluştuğu, vadinin indiği köşe), batı bloğun kuzey saçağının doğu ucu ve doğu saçağının ortası (9,2 m; 9 m'yi geçiyor). Kanadın veranda üstündeki 2,2 m'lik deresinde tek iniş (0.19: kısa derede tek iniş): serbest ucu düştü.
- **Dış cephe Boardex** 96,52 m² (37 levha): duvarlar 85,82 m² net + kalkanlar 10,68 m². Veranda tavanı satırı yok.
- **İç:** duvar alçıpan beyaz 58, yeşil 8; tavan beyaz 23, yeşil 2 (yalnız banyo); OSB takviyesi 9.

Aynı kurallarla Ç8201'in listesiyle yan yana: `sonuc/C8801_C8201_yan_yana.md`. Farkların hepsi modelden: Ç8801'de veranda dikmesi, kirişi ve tavanı yok (çatısız); kalkan, alın kapama, ters mahya ve kenar kutusu var (beşik + cumba; Ç8201 dört omuz); dere kısa (beşikte kalkan kenarında dere yok); dış cephe ve iç duvarlar uzun (L plan, daha çok oda duvarı).

## Bulgular

1. Kural kitabı bu modelde elle düzeltme olmadan çalıştı; yeni kural gerekmedi. Kısa dere (0.19), kalkan kenarı (0.15), ters mahya kenar kutusu, serbest uçta dere kapağı, OSB takviyesi kuralları ilk kez görülen bir çatıda beklendiği gibi uygulandı.
2. Kuralın kapsamadığı tek şey çatısız veranda; motora eklendi (yukarıda). Kural sorusu: pergola ve korkuluk.
3. Kesin olmayan tek girdi çatı. Biçim değişirse kaplama, mahya, vadi, alın, kalkan ve dere satırları değişir; duvar, iç kaplama, kapı ve pencere, elektrik, tesisat ve boya değişmez. Eğim seçeneği listeyi az değiştiriyor: kanat %33, batı blok %21,7 olsaydı (`STANDART = "kanat"`) panel boyları L 3640 ve L 2480 olurdu (adet aynı, 36), dış cephe Boardex bir levha az (36), alın kapama ve ters mahya aynı.

## Çizim seti

`cizimler/C8801_A/` (yöntem A): plan, çatı planı, dört görünüş, pafta, IFC4 (şema hatası 0), dört perspektif, çatısız ve makaslı görünüm. Görünüşler ve perspektifler katalog görselleriyle karşılaştırıldı: batı kalkanı, kanadın güney kalkanı, doğu cephede kesintisiz saçak, pencere ve kapı yerleri aynı. Pergola ve korkuluk çizilmedi. Makas yerleşimi yok (katalog modeli; çatı çeliği motorun ortalamasıyla).

## Kullanım

```
bash c8801_kos.sh ~/.cache/portman-venv/bin/python
```

Tanım değişirse önce `python tanim/c8801_tanim_uret.py tanim/C8801.json`. Betik geçici dosya yazmaz, hiçbir dosyayı silmez.
