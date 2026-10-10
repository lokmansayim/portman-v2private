# 10 Ekim 2026 · Ç8801: kural kitabının yeni bir modelde sınanması

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı. Motor öteki klasörlerde: `../2026-10-06_kor_test/` (tanımdan girdi, çizim seti), `../2026-10-03_yukleme/` (yükleme listesi), kurallar `../../kurallar/`.

Lokman, 10 Ekim 2026 11:39: "seninle yazdığımız kurallar bu kadar farklı model bence kafi istersen testini bir sonraki model olan ç8801 de yap".

Ç8801 PortatifEv'in katalog modelidir: tek kat çelik, 2+1, 88 m² (veranda dahil). Kör test değildir: bu model için arşivde yükleme listesi, montaj paftası ve karkas modeli (SKP) yok. Sınav şu: kural kitabı, kuralları yazılırken hiç görülmemiş bir modelde, elle düzeltme yapılmadan çizim setini ve listeyi çıkarabiliyor mu; kuralın kapsamadığı yerler nerede. Liste Lokman'ın incelemesi içindir.

## Girdi

- **Kaynaklar** (PortatifEv arşivi, `Arşiv/TEK KAT ÇELİK/`): planlar DWG'sindeki Ç8801 planı (duvar çizgileri, pencere ve kapı blokları, ölçüler; LibreDWG ile DXF'e çevrildi), katalog paftası `PORT-Ç8801.jpg` (aynı plan, ölçü zincirleri, mahal alanları) ve üç katalog görseli (`ç_8801_1_R_Photo - 1, 2, 5.jpg`; veranda). Çatı Lokman'ın cevabından (aşağıda).
- **Tanım** (`tanim/C8801.json`, Yapı Tanımı 0.5; `tanim/c8801_tanim_uret.py` üretir). Dış ölçü 1024 × 860 cm; batı blok 624 × 640, doğu kanat 400 × 860, güneybatıda 624 × 220 veranda. Baz paketin duvarı: 8 cm karkas, iki yüzde 1,25 cm kaplama. 6 dış, 7 iç duvar; 9 pencere (120/180 üç, 80/180, 120/120 dört, 60/40), dış kapı 95 × 210, beş iç kapı 90 × 214. Panel adetleri kuraldan tahmin (katalog modeli).
- **Mahaller** (kaplanmış yüzler arası; katalog etiketi parantezde): yaşam alanı 21,34 (21,0) · mutfak 10,05 (10,0) · hol 7,38 (7,3) · yatak odası 12,74 (12,6) · yatak odası 11,79 (11,6) · banyo 4,68 (4,7) · veranda 13,73 (13,8) m². Kapalı net 67,98 m²; bina alanı 88,06 m² (katalogdaki 88 m² verandayı içerir).
- **OSB takviyesi:** yaşam alanı ile mutfak arasındaki duvarın iki yüzü (TV ünitesi, mutfak dolabı; katalog paftasındaki eşyadan).

## Çatı: katalog ve iki varyant

Lokman, 10 Ekim 2026 13:33, ilk varsayımı düzeltti: "cumba arkaya doğru uzanmıyor uzun kenardaki çatıya girip kalıyor yani kısa kenardaki çatı devam ediyor". Düzeltmenin iki okuması çizildi, numaralı seçenek olarak soruldu. 14:46'daki cevap: "3 modelin de gayet güzel hatta çatı olarak 3'üde olur çokta güzel olur hatta ben 1. versiyonu beğendim ama asıl katalogdaki model 2. versiyon".

Üç çatı da aynı planda; saçak 30 cm, saçak kotu 280 (makas üstü). Tanımları `tanim/c8801_tanim_uret.py` üretir (`--cati katalog|K|L`). Varyant adları (K, L) geçicidir; model bankasında Lokman verir.

| | Ç8801 (katalog, 2. versiyon) | Ç8801-K (1. versiyon) | Ç8801-L (ilk varsayım) |
|---|---|---|---|
| Biçim | Ana çatı doğu–batı, iki ucunda kalkan. Cumba (doğu kanadın güney ucu) güneye bakan kalkanla biter; mahyası ana çatının güney yüzüne girip biter (iki vadi) | Ana çatının batı ucu kalkan, doğu ucu kırma; cumbanın doğu yüzü doğu kırmasıyla aynı düzlem: doğu cephede saçak boydan boya | Kanadın mahyası kuzey–güney boydan boya (güneyde ve kuzeyde kalkan); batı bloğun mahyası ona aynı kotta bağlanır |
| Eğim | Bütün yüzler %33; cumbanın mahyası ana mahyadan 40 cm alçak | Bütün yüzler %33 | Batı blok %33, kanat %50,2 (açıklıklar 640 ve 400 cm; mahyalar aynı kotta) |
| Düzlem · yüzey | 4 · 90,56 m² (plan 86,0) | 4 · 90,56 m² | 5 · 92,82 m² |
| Kenarlar (m) | saçak 21,48 · mahya 15,34 · vadi 6,68 · alın 19,59 | saçak 28,48 · mahya 11,84 · kırma 6,83 · vadi 3,34 · alın 12,22 | saçak 23,88 · mahya 17,74 · vadi 8,69 · alın 17,67 |
| Kalkanlar (m²) | batı 4,65 · doğu 4,65 · cumbanın güneyi 2,12 | batı 4,65 · cumbanın güneyi 2,12 | batı 4,65 · kanadın güneyi 3,01 · kuzeyi 3,03 |

Katalog görseli 2'de doğu cephede saçak kesintisiz görünüyor (K gibi); Lokman'a göre katalogdaki ürün 2. versiyon. Görsel ile ürün ayrışabiliyor: bayiye gidecek çizim, Lokman'ın onayladığı tanımdan üretilir, görselden değil.

Lokman'ın yönü (14:46): "sen 2 iş yapacaksın 1 devamlı modelde üreteceksin 2. bayilerede bu modelleri sunacaksın yani yanlışlıkla doğru yaptın". Varyantlar bunun için saklanıyor: aynı plana üç çatı, üçünün de listesi ve çizim seti. Model bankasına adaydırlar.

## Veranda: çatısız (pergola)

Görsellerde verandanın üstünde çatı yok; ahşap pergola ve ahşap korkuluk var. Tanımda verandanın örtüsü yazılır (`ortu: "pergola"`). Çatısız verandanın tavanı yoktur: veranda tavanı (Boardex), tavan paneli, köşebentteki veranda çevresi ve tavan omegası onu saymaz; çatı çeliğinin oturumundan (tavan ve çatı paneli) ve şilte hesabından düşülür. Bina alanına girer. Pergola ve korkuluk modelde ve listede yok (Lokman'a soruldu: listede olacak mı, malzemesi ne).

Bu, motora eklenen tek yenilik (kural değil, modelin anlatılabilmesi için): `yapi.py` (örtü alanı), `girdi_genel.py`, `yukleme.py` (yeşil tavan satırının formülü ve notu, şilte), `ifc_genel.py` (verandada tavan yok). Tanımda alan yoksa (bütün eski modeller) hesap öncekiyle aynı; değişmezler denendi (aşağıda). Pafta bilgi satırında, tanımda çatı kaplaması yazmıyorsa kural kitabındaki baz paket kaplaması yazılır (önceden "—").

## Liste (katalog çatısı; kural seti 0.19, yöntem A: çatı ve tavan paneli)

`sonuc/C8801_yukleme.md` (93 satır). Öne çıkanlar:

- **Çelik** 2.332 kg: dış duvar 37,68 m (766 kg), iç duvar 23,23 m (459 kg), çatı makasları 86 m² × 5,65 kg/m² (motorun "beşik + cumba" ortalaması; 486 kg; üç çatıda aynı, makas yerleşimi yok), tavan ve çatı paneli verandasız oturumla 74,34 m² (264 + 327 kg).
- **Çatı:** tek kat panel 21 × L 3740 + 10 × L 2480 = 31. Mahya 6, ters mahya 3, kenar kutusu 6, mahya bandı 3, şilte 9.
- **Kalkan kenarı** (yöntem A, Lokman 8 Ekim): Boardex yüz 3,61 m² (2 levha), alın kapama 19,59 m (9 × L 2500).
- **Dere:** 21,48 m (6 × L 4000), 4 hat (ana çatının güneyi 6,24, kuzeyi 10,84; cumbanın iki yanı 2,2'şer m), 6 serbest uç (kapak 6). **İniş 6:** kuzey saçağın iki ucu ve ortası (10,84 m; 9 m'yi geçiyor), ana çatının güney saçağının batı ucu, verandanın iç köşesi (ana çatının ve cumbanın deresi orada buluşur), cumbanın güneydoğu köşesi. Cumbanın iki yanındaki 2,2 m'lik derelerde tek iniş (0.19: kısa derede tek iniş).
- **Dış cephe Boardex** 97,24 m² (37 levha): duvarlar ve üç kalkan. Veranda tavanı satırı yok.
- **İç:** duvar alçıpan beyaz 58, yeşil 8; tavan beyaz 23, yeşil 2 (yalnız banyo); OSB takviyesi 9.

Aynı kurallarla Ç8201'in listesiyle yan yana: `sonuc/C8801_C8201_yan_yana.md`. Farkların hepsi modelden: Ç8801'de veranda dikmesi, kirişi ve tavanı yok (çatısız); kalkan, alın kapama, ters mahya ve kenar kutusu var (beşik + cumba; Ç8201 dört omuz); dere kısa (beşikte kalkan kenarında dere yok); dış cephe ve iç duvarlar uzun (L plan, daha çok oda duvarı).

## Üç çatının listesi

`sonuc/C8801_cati_varyantlari.md`: 89 kalemden 68'i üç listede aynı; farklı olan 21 kalemin hepsi çatıdan (kaplama, mahya, dere, kalkan kenarı, dış cephe, bunların vidası). Fiyat yok; adet ve ölçü.

| | Katalog | K | L |
|---|---|---|---|
| Tek kat panel | 31 (21 × L 3740 + 10 × L 2480) | 32 (20 × L 3740 + 12 × L 2480) | 36 (15 × L 3740 + 21 × L 2630) |
| Metal dere · iniş · kapak | 21,48 m (6) · 6 · 6 | 28,48 m (8) · 7 · 4 | 23,88 m (7) · 7 · 6 |
| Mahya · ters mahya | 6 · 3 | 8 · 2 | 7 · 4 |
| Alın kapama · dış cephe Boardex | 9 · 37 | 6 · 35 | 8 · 37 |

Katalog çatısı kaplamada, derede, inişte ve mahyada en az malzemeyi istiyor; kalkanı fazla (alın kapama, Boardex). Lokman'ın sorusu buydu: "asıl katalogdaki model 2. versiyon neden böyle bir sonuç var maliyet açısından". Çatı çeliği üçünde aynı: motor ortalamayla hesaplıyor (makas yerleşimi yok); makas kuralları gelince çatıya göre ayrışır.

## Bulgular

1. Kural kitabı üç çatıda da elle düzeltme olmadan çalıştı; yeni kural gerekmedi. Kısa dere (0.19), kalkan kenarı (0.15), ters mahya kenar kutusu, serbest uçta dere kapağı, OSB takviyesi kuralları ilk kez görülen çatılarda beklendiği gibi uygulandı. Çatı değişince yalnız çatı satırları değişti.
2. Kuralın kapsamadığı tek şey çatısız veranda; motora eklendi (yukarıda). Kural sorusu: pergola ve korkuluk.
3. Görsel ile ürün ayrışabiliyor (katalog görseli 2 ile katalogdaki çatı). Model bankasında kaynak, Lokman'ın onayladığı tanım olmalı.
4. Düzeltme yolu: Lokman'ın cümlesi iki biçimde okunabildi; iki okuma numaralı çizildi, Lokman numarayla seçti. Bayi akışı için önerilen yol bu: bayi tarif etmez, tanır ve seçer (devir notu: `docs/devir/2026-10-10_IE-05_Devri.md`).

## Çizim seti

`cizimler/C8801_A/` (katalog), `cizimler/C8801K_A/`, `cizimler/C8801L_A/` (yöntem A): plan, çatı planı, dört görünüş, pafta, IFC4 (şema hatası 0), dört perspektif, çatısız ve makaslı görünüm. Pergola ve korkuluk çizilmedi. Makas yerleşimi yok (katalog modeli; çatı çeliği motorun ortalamasıyla).

## Kullanım

```
bash c8801_kos.sh ~/.cache/portman-venv/bin/python
```

Üç tanımdan (katalog, K, L) listeleri, çizim setlerini ve iki tabloyu üretir. Tanım değişirse önce `python tanim/c8801_tanim_uret.py tanim/C8801.json` (varyantlar: `tanim/C8801K.json --cati K`, `tanim/C8801L.json --cati L`). Betik geçici dosya yazmaz, hiçbir dosyayı silmez.
