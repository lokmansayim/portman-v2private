# Çift kat prefabrik · kural çıktısı (İE-22, 28 Ekim 2026)

Lokman'ın isteği (28 Ekim 2026): "çift kat prefabrik için kurala aldığın her şeyi en sonunda bana çıktı olarak ver." Bu belge o çıktıdır:
bugün iki katlı prefabrik için **kurala alınan her madde**, kaynağı ve durumu ile. Kaynaklar: Lokman'ın 28 Ekim sözleri; prefabrik çizim
kuralları v1.4.3 (`ref_prefabrik/astra_v1_4_3/prefabrik-cizim-kurallari.md`, K02); tek kat prefabrik Motor'unun bugünkü kuralları
(`.claude/rules/motor-cizim.md`: İE-11, İE-12, İE-17, D-12, D-14, D-15, BK-13, BK-14); Astra'nın çift kat R02 kaydı
(`ref_prefabrik/cift_kat_R02/`; **veri**, kural değil, D-12); pilot kapsamı D-26. Ev: Lokman'ın 28 Ekim'de gönderdiği iki kat planı (zemin ve 1. kat).

**Durum sözlüğü.** `Lokman` = Lokman'ın açık sözü, kesin. `Tek kat` = tek kat prefabrik kuralı, çift kata aynen (Lokman 28.10: "çift kat ile tek kat
arasındaki fark merdiven; geriye kalan, döşeme, çatı birebir aynı"). `R02` = Astra'nın 12 Eylül çift kat kaydından alınan değer; teyit bekler.
`Kabul` = bu taslak için çalışma kabulü; Lokman değiştirebilir. `Soru` = kural yok, uydurulmadı (K21); Lokman'ın cevabıyla kurala girer.

## 1. Kat ilkesi

| # | Kural | Durum |
|---|---|---|
| 1.1 | İki katlı prefabrik, tek katlı prefabrikin kurallarıyla çizilir. **Tek fark merdivendir.** Döşeme ve çatı tek katla birebir aynıdır. | Lokman, 28.10 |
| 1.2 | Her katın planı ayrı bir kat planıdır (zemin kat, 1. kat); iki kat aynı gövdeyi, aynı pano ızgarasını, aynı dış köşeleri ve aynı merdiven kutusunu paylaşır; iç bölmeler ve açıklıklar katta farklı olabilir. | Kabul (plandan: iki katın dış ölçüleri, merdiven kutusu ve balkonu aynı yerde) |
| 1.3 | Çift kat canlıya pilottan sonra gider; pilot tek katlı prefabrik ve tek katlı çeliktir. Yerelde geliştirme ve çizim serbesttir. | D-26 (25.10) |
| 1.4 | Beyin bugün 2 katlı planı "çizilemez" diye işaretler (`beyin/gorsel_okuma.py`); Motor `kat_sayisi ≠ 1` İş Emri'ni açık hatayla reddeder. Çift kat İE-22 ile açılır; o güne kadar bayiye otomatik çizilmez. | Bugünkü kod |

## 2. Gövde ve pano ızgarası (tek kattan aynen)

| # | Kural | Durum |
|---|---|---|
| 2.1 | Model birimi cm, gerçek boyut; tam pano ve aks aralığı **125,5 cm**; isteğe bağlı iç duvar adımı yarım pano **62,75**. | Tek kat (v1.4.3) |
| 2.2 | Dış duvar **100 mm**, iç duvar **60 mm** (160/100 yalnız müşteri seçeneği). | Tek kat (D-12) |
| 2.3 | Pano yüksekliği yalnız **250 / 280 / 300**; her katta aynı kural. Bu evde 250. | Tek kat (D-14) · Kabul (250) |
| 2.4 | Makasın oturduğu iki duvar köşeden geçer (o yönde dış ölçü = pano × 125,5 + 10, akslar duvar ekseninden 5 + 125,5k); kalkan duvarları araya girer (dış ölçü = pano × 125,5 + 20, akslar iç yüzden 10 + 125,5k). İş Emri'nde `yapi.kisa_kenar`. | Tek kat (İE-17, on montaj paftası) |
| 2.5 | Bu evde makas derinliği (y, 706) geçer: x = 6 tam pano (763 = 6 × 125,5 + 10 — planın dış eni pano düzenine tam oturuyor), y ölçüye kesim (706 = 5,5 pano ızgarası, kesilmiş son pano önde 121,25). | Kabul (plandan) |
| 2.6 | Dış ölçü verildiyse yapı o ölçüde kesilir, tam panoya yuvarlanmaz; kesilen özel pano dizilimin son ucunda. Dizilim arkadan ve soldan (`arka-sol`): kesilmiş pano önde ve sağda. | Tek kat (6.10 kuralı, İE-11) · Kabul (arka-sol; arka duvar tam panolu, ön cephe kesimli) |
| 2.7 | Pano ekleri yalnız tam akslarda, iç duvar T'de bölünmez (`hiza: tam_izgara`); kesilmiş son pano ızgaranın sondan bir önceki aksından başlar (`son_pano: son_aks`). | Tek kat (İE-17, AP paftaları) |
| 2.8 | İki katta da ızgara aynıdır: üst katın panoları zemin katın pano eklerinin tam üstüne gelir (düşey yükler ve köşe profili için). | Kabul (R02'de de böyle: "iki kat aynı plan, aynı aks ızgarası") · Lokman'ın teyidi gerekir |
| 2.9 | Her pano ekinde H profili (dışarıdan 5 cm, eke ortalı); T birleşiminde üçlü H; dört kollu (+) birleşim kural kitabında yok, kaçınılır (BK-14 yalnız uyarıyla izin verir). **Çift katta iç duvarlar da 100'lük** (Lokman 13:32 "güncel şablondaki gibi içler 100'lük olacak"): iç pano `100'LÜK …`, T'de `100X100 3 LÜ H BAĞLANTI DİREĞİ`, gerçek iç köşede `2X100X100 İÇ KÖŞE DİREĞİ` (şablon blokları). Motor bugün iç = dış kalınlığı reddediyor (İE-22 bulgu 7). | Lokman 13:32 · Motor: bulgu 7 |
| 2.10 | **Çift kat aks kuralı (Astra R02; Lokman 13:30 "aksları bir taraftan açman lazım, yine 125,50 ama 5 köşe profil farkı var"):** dört köşede 100×100 kolon olduğundan akslar **her iki yönde kolonun iç yüzünden** başlar: X = 10 + 125,5k, Y = 10 + 125,5k; cephe = 10 kolon + n × 125,5 + özel son pano + 10 kolon (R02: 100 + 9 × 1255 + 1005 + 100 = 12500). Tek kattaki "makasın oturduğu duvar köşeden geçer, aks 5 + 125,5k" kuralı (2.4) çift katta geçerli değil: o yönde akslar 5 cm kayar, son pano 5 cm kısalır. Bu evde: x 10 + 5 × 125,5 + 115,5 + 10 = 763; y 10 + 125,5k (zaten öyle), son pano 58,5. Yatay iç duvarın ilk panosu 120,5 değil 125,5 (aks kolon yüzünde). Çizimde: Motor 753'lük gövdeyle üretildi, üretici sol dış duvarı yerinde bırakıp içleri +5, sağ dış duvarı +10 kaydırdı; Motor'a kural İE-22 PR-1 (bulgu 8). | Lokman 13:30 · R02 |

## 3. Kapı ve pencere (tek kattan aynen)

| # | Kural | Durum |
|---|---|---|
| 3.1 | Pencere ölçüsü "ENxBOY" tam cm; en 30–247, boy 20–180; **üst kot 200**, eşik = 200 − boy. Panodan geniş pencere (en > 121,5) 251'lik pencereli panoda. | Tek kat (BK-13) |
| 3.2 | Plandaki "120/125 standart pencere" → 120x125 (eşik 75); "60/125" → 60x125 (eşik 75); "60/40" → 60x40 (eşik 160). | Kabul (plandaki yazıdan; katalogda 120x125 yoktu, BK-13 serbest ölçüye izin verir) |
| 3.3 | Plandaki "120/200 Fransız pencere": boy 200, Motor'un sınırı 180'i aşıyor (üst kot 200 → eşik 0 = kapı gibi). Taslakta **120x180 (eşik 20)** alındı. | **Soru 4** (Fransız pencere nedir: 120x180 mi, döşemeden başlayan 120x200 doğrama mı, balkon kapısı mı?) |
| 3.4 | Pencere odaya ortalı (`pencere: oda_ortasi`; ızgara panosu oda ortasından en çok ¼ pano kaçıyorsa ızgara kalır); kapı mantıkla: dayanaklı panoda, menteşe o uçta, oda kapısı bölmeye 11,5 cm yaslı, dış kapı panoda ortada. | Tek kat (D-15) |
| 3.5 | Dış kapı 90, iç kapı 82 (çalışma kabulü, K04 açık). Kapı yüksekliği çizimde 200 (katalogda ürün yüksekliği yok). | Tek kat (K04, v1.4.3) |
| 3.6 | Giriş kapısı sağ cephede, WC holünün sağ dış duvarında, 90'lık, içeri açılır (Lokman 28.10 12:34; §12). Panoda ortada; menteşe yönü düzeltme turunda. | Kabul (Soru 1 kapandı) |
| 3.7 | Üst kattan balkona kapı dış kapıdır (balkon açık mahal); planda ODA 2'nin balkona bakan yan duvarında. | Kabul (plandan) |

## 4. Çatı (tek kattan aynen; Lokman: "çatı birebir aynı")

| # | Kural | Durum |
|---|---|---|
| 4.1 | Çatı üst katın duvarlarının üstüne tek kattaki gibi oturur: beşik, iki yüzde **%33** (derece değil), iki yanda **30 cm** yatay saçak, uçta **10 cm** dik topuk; mahya yüksekliği = 10 + (saçaklı açıklık / 2) × 0,33. Ana makas kısa kenarı geçer. | Lokman 28.10 + tek kat (v1.4.3) |
| 4.2 | Bu evde makas y'yi (706) geçer, mahya x boyunca; saçaklarla açıklık 766, mahya 10 + 383 × 0,33 = 136,4 (Motor çıktısında 145,8: Motor saçağı 823'e göre, 763 + 60, hesaplıyor; prefabrik çatıda hangi açıklığın esas olduğu İE-17'de kıyas tablosuyla). | Kabul · İE-17 kıyası |
| 4.3 | Prefabrik çatı yöntemi B: tavan omegası, aşık, alın sacı, saçak sacı (çelikteki panel yöntemi değil); yükleme listesi kuralları `kurallar/liste/prefabrik.json`. Çift katta çatı satırları tek kattaki gibi, yalnız üst kat için. | Tek kat (Lokman 7.10, BK-12) |
| 4.4 | Merdiven kutusu arkaya 1 pano çıkıyor: ana çatı onu örtmez. Çıkmanın çatısı (arka cumba mı, ana çatının uzatılması mı, tek eğimli mi) kuralda yok. | **Soru 5** |
| 4.5 | Çatı tek kattaki gibi IFC'de ve görünüşte; çift katta ön görünüş iki kat yüksekliğinde (2 × 250 + ara kat). | Kabul |

## 5. Döşeme ve ara kat (Lokman: "döşeme birebir aynı")

| # | Kural | Durum |
|---|---|---|
| 5.1 | Döşeme tek kattaki ile birebir aynıdır: katlar arasında yeni bir döşeme kuralı yazılmaz. | Lokman, 28.10 |
| 5.2 | Ara kat kotu ve kalınlığı: R02'de zemin duvarı 0–2500, çelik kiriş bölgesi 2500–2800 (300), Betopan 2800–2820 (20), üst duvar 2820–5320; toplam **5320 mm**. Kesit, açıklık hesabı ve kiriş adedi R02'de tanımlı değil ("taşıyıcı detay değil"). | R02 (veri) · **Soru 6** (ara kat yüksekliği ve malzemesi: 320 mm doğru mu; 100'lük alt çerçeve üst katta da var mı?) |
| 5.3 | Üst kat döşemesinin yükleme listesi satırları (ara kat kirişi, Betopan, alt çerçeve) tek katın taban satırlarıyla aynı kuraldan mı sayılır? | **Soru 6** |

## 6. Merdiven (tek fark)

| # | Kural | Durum |
|---|---|---|
| 6.1 | Merdiven, çift katı tek kattan ayıran tek elemandır (Lokman). Motor'da bugün merdiven yoktur; R02'de de çizilmemişti ("üst kat girişi çözümsüz"). İE-22 merdiveni İş Emri'ne ekler. | Lokman, 28.10 · Bugünkü kod |
| 6.2 | **Merdiven kovası dıştan dışa 271** = 10 profil + 2 × 125,5 pano + 10 profil (Lokman 14:42); kova duvarlarının **iç yüzleri akslarda** (323,75 / 574,75), iç 251 = tam 2 pano; çıkma dış 271 × 125,5, arka duvarı 2 tam pano, dört köşesinde ve gövdeyle birleşimlerinde 100×100 profil. Önceki okuma (akslara ortalı duvar, 261/251) kalktı. Önceki satır: Merdiven kovası pano aksında (Lokman 13:30 "merdiven kovası ile oda duvarlarını da şaşırmışsın" — 13:00'teki "aynı buradaki gibi" merdivenin düzeni içindir, ölçüler ızgaradan): kova = 2 pano, duvar aksları **323,75 / 574,75** (çift kat ızgarası; oda duvarlarıyla aynı akslar), 100'lük duvarlarla iç 241; gövdede derinlik 570,5–696 (önü HOL'e açık sınır); arkaya **çıkma 1 pano** (dış 706–831,5; duvarları akslara ortalı 10'luk dış pano; yan 115,5, arka 125,5 + 115,5; arka köşelerde ve gövdeyle birleşim noktalarında 100×100 profil — Lokman 13:57). Planın 200/220'si uygulanmadı (ızgara dışı). | Lokman 13:30 |
| 6.3 | Merdiven düzeni planın aynısı (13:00), ölçüler kovadan: **çift kollu U**, kol 120,5 (241 / 2); sağ kol 5 düz basamak (25), çıkmada **6 dönel basamak** (180°, merkez gövde dış yüz hizasında kutu ortası), sol kol 5 düz → **16 rıht** (282/16 = 17,6); başlangıç sağ kolda önde (daire), üst kata sol koldan önden varış (ok). Sahanlık yok (dönel). Korkuluk planda yok. | Lokman 13:00 · korkuluk açık |
| 6.4 | Merdiven boşluğu üst kat döşemesinde açık kalır; merdiven mahali her iki katta aynı yerde. Merdivenle hol arası duvarsız (açık sınır). | Kabul (plandan) |
| 6.5 | Üst katta merdiven kutusunun arka duvarında 120/125 pencere (planda var); zemin katta o duvarda açıklık yok. Üst katta kutunun önü hole açık; zemin katta planda ön duvar çizili (giriş açıklığı planda yok → **Soru 2b**). | Plandan |

## 7. Balkon ve açık mahaller

| # | Kural | Durum |
|---|---|---|
| 7.1 | Balkon açık mahaldir (`balkon`); açık kenarları planda çift sıra kırmızı kesik çizgiyle gösterilir (veranda profili kuralı); net alan açık dış kenara kadar. | Tek kat (v1.4.3, Motor) |
| 7.2 | Balkon iki katta aynı yerde: gövdenin ön sağ girintisinde (mutfağın / ODA 3'ün önünde), planda 337 × 165; **balkon kiriş çizgisi gövde önünden 40 cm dışarıda** (Lokman 14:43; planda 40 — önce 30 okunmuştu). Taslakta gövdenin içindeki parça; çizimde 40'lık çıkma çizgi. | Lokman 14:43 · **Soru 7** kalan: üst balkon döşemesi/korkuluğu; alt köşede dikme mi konsol mu? |
| 7.3 | Balkonun ön sağ köşesinde 10 × 10 dikme (tek kattaki veranda kuralı). | Kabul |

## 8. Düşey taşıyıcı ve sayım

| # | Kural | Durum |
|---|---|---|
| 8.1 | Dış köşelerde **100 × 100 kutu profil** köşe direği, iki kat boyu sürekli (Lokman 12:09, 13:13 "köşeler 100*100 kutu profil olacak demiştim"); R02: 100 × 100 × 5320 (sayımda bir kez). Çizimde Güncel Şablon 2024'ün `100X100 DIŞ KÖŞE DİREĞİ` bloğu (10×10 kırmızı kutu + pano çıkıntıları; şablonda `2X100X100 DIŞ KÖŞE DİREĞİ` varyantı da var). Et kalınlığı tanımsız. | Lokman · et kalınlığı **Soru 8** |
| 8.2 | Sayım kat kat yapılır (zemin, üst), ortak parçalar (sürekli köşe profili, çatı) bir kez; her kat kendi pano, kapı, pencere, H ve köşe parçalarıyla. Kapılı/pencereli pano tek pano sayılır, doğrama ayrı. | R02 + tek kat (v1.4.3) · Kabul |
| 8.3 | Prefabrik yükleme listesi kuralları (`motor/prefabrik_liste.py`, `kurallar/liste/prefabrik.json`) kat başına koşar; döşeme ve merdiven satırları yeni kural ister. | Kabul · Soru 6 |

## 9. Çizim çıktısı

| # | Kural | Durum |
|---|---|---|
| 9.1 | Her kat için ön onay PDF'indeki üçlü (akslı plan, net alanlı kopya, saha montaj planı) ve DXF; ön görünüş iki katlı, çatı profili tek. DXF cm, AutoCAD'de açılır; blok ve katman adları tek kattaki gibi (Astra v1.4.3 şeması, K03). | Tek kat (İE-12, K02, K03) · Kabul (iki katın tek dosyada yan yana mı, ayrı mı: İE-22 PR-1'de) |
| 9.2 | DXF yeniden açılıp doğrulanmadan PDF yok (K23); doğrulama geçmezse yalnız `.HATALI.pdf`. Çift katta iki katın doğrulaması ayrı ayrı geçer. | Tek kat (K23) |
| 9.3 | Antette kat sayısı 2, kat adı; bayi paftasında TASLAK (D-10). | Kabul |

## 10. Bu evin ızgara uyarlaması (plan → taslak)

Plandaki ölçüler duvar aksı, cm. Taslakta x sol dış yüzden, y arka dış yüzden (dizilim arka-sol). Sapma = taslak − plan.

| Öğe | Planda | Taslakta | Sapma |
|---|---|---|---|
| Gövde (dış) | 763 × 706 | 763 × 706 | 0 (x 6 pano tam; y 5,5 pano, kesilmiş son pano 121,25) |
| Merdiven kutusu sol duvarı (x) | 342 | 318,75 | −23,25 |
| Merdiven kutusu sağ duvarı (x) | 552 | 569,75 | +17,75 (kutu iç eni 200 → 245) |
| Merdiven çıkması (arkaya) | 125 | 125,5 (Motor'da yok) | +0,5 |
| Zemin: ODA/SALON ve hol/salon duvarı (y) | 302 | 323,75 | +21,75 |
| Zemin: merdiven altı / WC duvarı (y) | 150 | 135,5 | −14,5 |
| Zemin: SALON/MUTFAK duvarı (x) | 472 | 507 | +35 |
| Balkonun sol duvarı (x, iki kat) | 421 | 444,25 | +23,25 (kademe 51 → 62,75) |
| Mutfak / ODA 3 ön duvarı (y) | 566 | 574,75 | +8,75 |
| Balkon derinliği (dış yüzden) | 165 (30 taşma dahil) | 116,25 (taşma yok) | −48,75 |
| 1. kat: ODA 1/ODA 2 duvarı (y) | 242 | 261 | +19 |
| 1. kat: banyo alt duvarı (y) | 306 | 323,75 | +17,75 |
| 1. kat: holün alt duvarı, ODA 3 girintisi (y) | 359 | 386,5 | +27,5 |

Net alanlar (m², kapı eşikleri hariç; plan → Motor): zemin ODA 9,38 → 9,50 · SALON 17,00 → 17,42 · MUTFAK 7,13 → 5,90 · BALKON 5,93 → 3,96 (taşma yok) ·
HOL 4,47 · WC 2,21 · WC HOLÜ 3,29 · MERDİVEN (gövde parçası) 3,15; 1. kat ODA 1 7,42 → 7,58 · ODA 2 15,66 → 14,67 · ODA 3 8,80 → 8,93 · BANYO 5,70 → 5,60 ·
HOL 6,00 · BALKON 5,93 → 3,96.

Neden 2 pano merdiven kutusu: 1,5 pano (182 iç) seçilince salon–mutfak duvarı ile hol–WC holü duvarı aynı aksta (507) çakışıp dört kollu birleşim
doğuruyor (kural kitabında yok); 2 pano ile her birleşim T ve köşe. Bedeli: WC sütunu ve banyo 196 → 180, mutfak 276 → 243. Salon penceresi
odaya ortalanınca Motor kesilmiş son panonun derzine 0,6 cm kala bitip kıymık pano üretti (Motor bulgusu, İE-22'de); taslakta pencere ızgara
panosunda (plandakinden 51 cm arkada).

## 11. Sorular (Lokman'a; cevap kurala girer)

1. ~~**Giriş kapısı** nerede?~~ **Cevaplandı 28.10 12:34** (§12): sağ cephe, WC holü, 90, içeri açılır.
2. ~~**Merdiven kutusu** 2 pano mı 1,5 pano mı?~~ **Cevaplandı 13:00:** planın aynısı, 200 iç / 220 dış (§12). Açık: **2b** zemin katta merdivene giriş (ön duvar planda çizili); pano aksı uyumu Soru 9'da.
3. ~~**Merdiven** ölçüleri~~ **Cevaplandı 13:00 (plandan):** çift kollu U, kol 100, 5 + 6 dönel + 5 = 16 rıht, basamak 25 (§12). Açık: korkuluk.
4. **Fransız pencere 120/200**: 120x180 mi, döşemeden başlayan 120x200 doğrama mı (Motor sınırı 180; yeni kural ister)?
5. **Merdiven çıkmasının çatısı**: arka cumba, ana çatının uzatılması, tek eğim?
6. **Ara kat**: yükseklik ve malzeme (R02: 300 çelik kiriş + 20 Betopan = 320 mm; toplam 5320); 100'lük alt çerçeve üst katta var mı; liste satırları.
7. **Balkon**: 30 cm taşma kalacak mı; üst balkon döşemesi/korkuluğu; alt köşede dikme mi konsol mu?
8. **Düşey köşe profili**: 100 × 100 × 5320 sürekli (R02) doğru mu; et kalınlığı?
9. **Ölçü sadakati**: gövde 706 korunup son pano kesilsin mi (bugünkü taslak), yoksa 5,5 tam pano = 710,25 mi?

Lokman'ın cevapları bu belgeye tarihli eklenir; kural haline gelen madde `.claude/rules/motor-cizim.md`'ye ve gerekirse `KARARLAR/`'a geçer (D-07, K21).

## 12. Cevaplar ve kararlar (tarihli)

| Tarih | Soru / madde | Lokman'ın sözü | Kurala etkisi |
|---|---|---|---|
| 28.10.2026 12:09 | **Soru 8** (köşe profili) ve **1.1 / 2.8** (ızgara) | "Çift katın tek kattan en büyük farkı köşe direkleri **100×100 profil**; **pano dizilimi aynı**." Astra'yla yapılmış 150 m² çift kat (R02, 12.500 × 6.000, döşeme detaylarına kadar) Mac'te; referans alınacak. | 8.1: dört dış köşede 100×100 sürekli köşe direği (R02'deki 100 × 100 × 5320 ile uyumlu; et kalınlığı hâlâ **Soru**). 2.8 teyit: iki katta ızgara ve pano dizilimi tek katla aynı. Şablon 2024 notu da aynı yönde: köşe direkleri kutu profil, tek parça, ankrajlı (`deneme/2026-10-28_cift_kat/autocad/sablon_inceleme/RAPOR.md` §4). |
| 28.10.2026 12:34 | **Soru 1** (giriş kapısı) | Plan görselinde kırmızı daireyle işaretledi: giriş kapısı **sağ cephede, WC holünün (WC ile mutfak arasındaki 152'lik hol) sağ dış duvarında**, ~90'lık, **içeri açılır**. | 3.6 kapandı: `zemin_kat.json`'a `{"tur":"dis_kapi","olcu":90,"arasi":["__DIS__","WC HOLÜ"],"duvar":"sag","pano":0}` eklendi; Motor zemin katı yeniden üretti (validation_passed True, kapı 7, BOM K03 dış kapı 90 ×1). Motor kapıyı **kendisi çizdi**: `BOM_D18_1255p0_DIS_K02` @ (763, 445) rot 90, açıklık panoda ortada (462,75–552,75), menteşe HOL tarafında (üst), kanat WC holüne süpürür. (12:45'te "Motor sembolü çizmedi" diye elle kırmızı kapı çizilmişti; yanlış bulguydu — üreticinin ad değiştirmesi iç sembolü bozmuştu; 13:05'te kaldırıldı, Motor bulgusu **yazılmadı**.) Menteşe yönü sorulmadı; Lokman düzeltme turunda söyler. |
| 28.10.2026 13:00 | **Soru 2 ve 3** (merdiven kutusu ve merdiven) | Planda merdiveni kırmızı daireyle işaretleyip "**Aynı buradaki gibi çiz**" dedi. | 6.2–6.3: kutu iç 200 × 260 yazılı (hesapla 250), dış 220, çıkma 125, duvarlar 337/557; çift kollu U, kol 100, 5 + 6 dönel + 5 = 16 rıht, basamak 25; zemin ve 1. kat aynı çizim (1. katta ön açık, arka duvarda 120/125 pencere). AutoCAD çizimine bire bir işlendi (`MERDIVEN` / `MERDIVEN_DUVAR` katmanları, üretici `merdiven_ciz`). Motor'a işlenmesi pano aksı kararını bekler (Soru 9). |
| 28.10.2026 13:02 | Dış kapı çizimi | "Dış kapıda Güncel Şablon 2024'te var." | Dış kapılı panoların çizimi Motor'un Astra sembolü yerine şablonun `100'LÜK 125'LİK KAPILI PANO(80'LİK)` çizimi (10'luk pano bandı, H profilli kasa, kanat, yay) 90'a ve pano enine uyarlanarak (`sablon_kapili_pano`); adlar aynı (`100'LÜK 125'LİK KAPILI PANO(90'LIK)`, `100'LÜK 116.25'LİK KAPILI PANO(90'LIK) [SOL]`). Şablondaki serbest dış kapı bloğu `100 LÜK ÇELİK KAPI 90X120` (100 cm'lik pano) çizgi duvarlı projelerde kullanılıyor; blok mantıklı örnek (86,5 m² İDA) 125'lik kapılı panoyu kullanıyor. İç kapılar henüz Motor sembolü (sırası gelince). |
| 28.10.2026 13:13 | **Soru 8** (köşe profili) | "Köşeler 100*100 kutu profil olacak demiştim." | 8.1: çizimde köşeler şablonun `100X100 DIŞ KÖŞE DİREĞİ` bloğu (6 köşe × 2 kat, aynı sürekli profil; köşe yönüne göre aynalı). Motor'un 5×10 köşe parçası kalktı. Et kalınlığı hâlâ soru. |
| 28.10.2026 13:15 | Ölçü biçimi | "Ölçülendirmede 125.5 yani virgülden sonra 2 rakam olsun, çünkü 126 gösteriyor." | Çizimde ölçü stili `dimdec 2, dimzin 0, dimdsep ','` → 125,50 / 763,00. (Neden 126'ydı: Motor'un stilinde `dimrnd 0` açık yazılı; ezdxf bunu tam sayıya yuvarlama sayıyor; üretici o alanı atıyor. Motor'un kendi PDF/DXF'i etkilenmedi; Motor'a taşınması K02 kapsamı, ayrı iş.) |
| 28.10.2026 13:30 | Aks kuralı, kova ve oda duvarları | "Astra'nın çift kat çizim kurallarına bak; aksları bir taraftan açman lazım — yine 125,50 ama çift katta 5 köşe profil farkı var; merdiven kovası ile oda duvarlarını da şaşırmışsın." | 2.10 (R02: akslar kolon iç yüzünden 10 + 125,5k; x'te 5 cm kayma, son pano 115,5) ve 6.2 (kova 2 pano aksta, 323,75/574,75; planın 337/557'si kalktı). Çizim yeniden üretildi (`ck_izgara/`, `cift_kat_izgara`). |
| 28.10.2026 13:32 | İç duvar kalınlığı | "Güncel şablondaki gibi içler 100'lük olacak." | 2.9: iç duvar 10 cm, `100'LÜK` iç panolar, 100X100 üçlü H ve 2X100X100 iç köşe (şablon blokları). Motor iç = dış kalınlığı reddediyor ("katman adları ayrışmıyor, deneme sınırı") → deneme betiği sınırı atladı; İE-22 bulgu 7. Sonuç: 10'luk duvarla WC holü 168 iç → karşılıklı 90 + 82 kanat çakıştı (validate); HOL–WC HOLÜ kapısı HOL'e açıldı (düzeltme turunda karar). |
| 28.10.2026 13:57 | Çıkma–gövde birleşimi profilleri | Planda çıkma yan duvarlarının arka duvarla birleştiği iki noktayı kırmızı kareyle işaretleyip "Profil" yazdı: "Çizdiğim yerlere profil koy." | 8.1 ek: çıkmanın gövdeye bağlandığı iki T noktasında da 100×100 kutu profil (şablon bloğu); çıkmanın arka köşelerinde de (varsayım, 13:30'dan). Ortak profil sayısı 6 + 2 + 2 = 10 (iki kat boyu sürekli varsayımı; Soru 8 et kalınlığı). |
| 28.10.2026 14:31–14:43 | PDF düzeltmeleri (sayfa 1, zemin) | İşaretler: iç zincirler karalı; çıkma "251"/"125,5"; kapı yerleri (ODA, WC, mutfak ×2); HOL–WC HOLÜ; balkon. Sözle: "iç ölçüleri boş ver, bir A4'e yalnız dış ölçüler ve zemin kat"; "profiller yok" (A4'te katmanı gizlemiştim); "**kova dıştan dışa 271**: 2 × 125,5 pano + 10'ar profil"; "WC holünden içeri girince karşında duvar var, adam nasıl girecek"; "**balkon kiriş çizgisini 40 dışarı al**". | 6.2 (271), 7.2 (40); İş Emri (ck_izgara/zemin): HOL–WC HOLÜ **açık sınır**; ODA kapısı ODA/SALON duvarına bitişik köşede (`duvar_ucu: on`), WC kapısı sağ köşede WC'ye (`sag`), WC HOLÜ–MUTFAK kapısı SALON/MUTFAK duvarına bitişik uçta (`sol`), SALON–MUTFAK kapısı balkon duvarına bitişik uçta (`on`). Tek A4 dış ölçü paftası (`a4_dis_olcu.py`): üst 313,75 \| 271 \| 178,25; 763; 706; çıkma 125,5; 831,5; alt 454,25 \| 308,75; taşma 40. Giriş kapısı yanındaki işaret henüz okunmadı. |
| 28.10.2026 15:18–15:23 | **Dizilim (zemin)** | Arka sıra soldan sağa: "10 köşe profili + 2,5 pano \| 10 + 1,5 pano (kova) + 10 \| 1 pano + 105,5 + 10". Sol taraf önden arkaya: "10 köşe profil + 3 pano + 2 pano + 58,5 özel + 10 köşe". "Sağ tarafta 40 balkon çıkması serbest ölçü." | Kural: **pano dizileri köşe profillerinin arasında sayılır**; her kova köşesinde 10×10 profil; iç duvarlar 100'lük, dış duvara H ile bağlanır (profil yok). Arka sıra 763'te özel pano **95,5** (Lokman'ın 105,5'i 773 eder — soruldu). Sol: ODA/SALON duvarı 386,5 aksında, ODA 2 pano + 58,5. Kova 1,5 pano (188,25 iç; 14:42'deki 271/2 pano kalktı). Çizim artık Motor planını yamamak yerine dizilim listelerinden kurulur (`uret_cift_kat_bloklu.py › ZEMIN`, `zemin_dizilimden`); sağ ve ön kenar ile iç duvarlar Motor dizilimine yakın, Lokman verdikçe değişir. |
| 28.10.2026 15:49–15:51 | İç duvar dizilimi (ODA/SALON hattı) | "Holden salona açılan kapıyı mirror yap, mutfağa koy; mutfak kapısı ölçüsüz." "ODA ve salonu bölen duvarları sadece H ile böl, araya profil atma; 125,5 × 5 pano, 2'si kapı; en sona (mutfak bitişi) 105,5 pano." | Kural: **iç duvar hatlarında profil yok, T'ler üçlü H**; ODA/SALON–HOL/SALON–mutfak üstü tek hat: 4 × 125,5 (4.'sü hol–salon kapısı) \| T 10 (salon/mutfak duvarı 512–522, aks 517) \| 125,5 (mutfak kapısı = hol–salon kapısının T'ye göre aynası; ayrı ölçü yok) \| 105,5. Balkon arka duvarı aynı sütunla: 57,75 \| T \| balkon kapısı 125,5 \| 105,5 pencereli. Kova duvarı bu hatta H ile oturur. |
| 28.10.2026 15:53–15:57 | Giriş kapısı yeri, iç köşe parçası, dış köşe yönü, aks deseni | "Ana giriş kapısını WC holü yarım pano içeri al; mutfakta bir tane 100×50 köşe, çizim kurallarında var, iç köşe (100'lük); WC'de de profil kullanmışsın, hatalı." "Dış köşelerinin de yönü yanlış." "Aks çizgilerini balkon çizgisi gibi yap; aralıkları çok açık ve uzun olmuş; silik olması iyi olmuş." | Sağ cephe arkadan öne: 10 \| 125,5 \| 62,75 \| giriş 90 (125,5) \| 125,5 \| 120,5 \| 10 → balkon profili 126,25–136,25. Kural (8.1 ek): **iç L köşelerde 100×50 iç köşe parçası** (şablon "2X100X100 İÇ KÖŞE" mantığı, 100'lük): WC önü–kova köşesi (522, 565,5) ve mutfak/balkon köşesi (444,25, 126,25); dış köşe ve çıkma köşelerinde 100×100 profil kalır. **Dış köşe profilinin çıkıntıları o köşede birleşen duvarlara bakar**; kova–arka duvar T'lerinde iki yönlü (üç kol). Akslar: gri, DASHED deseni (12,5 çizgi – 7,5 boşluk), balkon kiriş çizgisiyle aynı. |
| 29.10.2026 00:13–00:28 | **Aks düzeni ve iç duvar yerleşimi (Lokman AutoCAD'de kendi düzeltti)** | Lokman v10'u AutoCAD'de düzeltti (`…r01_lokman_0013.dxf`, bulutta v10 ile varlık varlık okundu): y akslarını önden 10 + 125,5k'ya taşıdı; x'e 323,75 / 449,25 / 700,25 ekledi, 753 çizgisini sildi; kova duvarlarını 318,75–328,75 ve 507–517'ye, mutfak ön duvarını 130,5–140,5'e, mutfak kapısını 512–637,5'e, WC kapısını 517'ye kaydırdı; sağ cephede girişi 62,75 içeri aldı; WC arka duvarını elle 1 pano + 110,5 çizdi; iki hatta 637,5–647,5'te 10'luk boşluk bıraktı; 6 üçlü H'yi sildi ("hatalıydı"); salon/mutfak duvarını sildi. "Öncelikli olarak dış ölçüler önemli, sonra akslar çok önemli." "Adım adım çizelim; sen önce olanı çiz, ben sonra bakıp söyleyeceğim." | Kural (2.10 ek): **y aksları önden** 10 + 125,5k; **iç duvarlar aks ortalı** (aks duvar ekseninde); kova duvar aksları 323,75 ve 512 → **kova aks-aks 1,5 pano** (iç 178,25); ek x aksları: kova sol C1 323,75, salon–balkon duvarı D1 449,25, giriş nişi F1 700,25; 753 aks değil. Giriş: sağ cephede **62,75 niş** (386,5–512 arası, dönüş duvarları akslarda, kapı 115,5'lik panoda). Çizim v11 (A049) Lokman'ın düzeni + doldurulan boşluklar: kova sol 517–570,5 dolu 53,5; çıkma arkası 125,5 + 52,75; sağ duvar arkadan 62,75 \| 116,25 \| niş \| 115,5 \| 125,5; WC arka 125,5 (60/40) + 110,5; WC ön kapı + 110,5; salon/mutfak duvarı 637,5–647,5 (mutfak 105,5 genişlik — **soruldu**, Lokman bakacak); üçlü H beş T'de. Dış ölçüler değişmedi: 763 × 706, çıkma 841,5, balkon kirişi −40. |
| 28.10.2026 | Blok adları (K03) | "Her blok malzeme kartındaki gibi isim isim olsun" (Güncel Şablon 2024 blok mantığı). | Yeni çift kat çizimi Şablon 2024 blok adlarıyla (`100'LÜK 125'LİK PANO`, `100'LÜK 125'LİK (120x100) PENCERELİ PANO`, `100X100 DIŞ KÖŞE DİREĞİ`…); Motor eşleme taslağı RAPOR §2. K03 kararı Lokman'da. |
