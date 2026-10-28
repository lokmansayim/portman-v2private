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
| 2.9 | Her pano ekinde H profili (dışarıdan 5 cm, eke ortalı); gerçek iç köşede 30×60 köşe parçası; T birleşiminde üçlü H; dört kollu (+) birleşim kural kitabında yok, kaçınılır (BK-14 yalnız uyarıyla izin verir). | Tek kat (v1.4.3, İE-12, BK-14) |

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
| 6.2 | Merdiven kutusu **planın aynısı** (Lokman 28.10 13:00 "Aynı buradaki gibi çiz"): iç 200 × 260 yazılı (hesapla 125 gövde + 10 duvar bandı + 115 çıkma = 250; 10 cm fark teyit ister), dış 220, duvar 10; duvarlar x 337/557 (ODA 327 + 10; WC 196 + 10 = 763 ✓); ön duvar y 561–571 (hol 152, WC'nin ön duvarıyla aynı hiza); çıkma arkaya 125 (dış). Pano aksına (318,75/569,75, 245 iç) oturmuyor → Motor'a işlerken iç panolar kesilir ya da kutu aksa çekilir: **Soru 9 ile karar**. Motor taslağı hâlâ 2 pano (245). | Lokman 13:00 (AutoCAD çiziminde bire bir) · Motor: Soru 9 |
| 6.3 | Merdiven planın aynısı (13:00): **çift kollu U**, kol 100 (2 × 100 = 200 iç); sağ kol 5 düz basamak (25), çıkmada **6 dönel basamak** (180°, merkez gövde dış yüz hizasında kutu ortası), sol kol 5 düz → **16 rıht** (282/16 = 17,6); başlangıç sağ kolda önde (daire), üst kata sol koldan önden varış (ok). Sahanlık yok (dönel). Korkuluk planda yok. | Lokman 13:00 · korkuluk açık |
| 6.4 | Merdiven boşluğu üst kat döşemesinde açık kalır; merdiven mahali her iki katta aynı yerde. Merdivenle hol arası duvarsız (açık sınır). | Kabul (plandan) |
| 6.5 | Üst katta merdiven kutusunun arka duvarında 120/125 pencere (planda var); zemin katta o duvarda açıklık yok. Üst katta kutunun önü hole açık; zemin katta planda ön duvar çizili (giriş açıklığı planda yok → **Soru 2b**). | Plandan |

## 7. Balkon ve açık mahaller

| # | Kural | Durum |
|---|---|---|
| 7.1 | Balkon açık mahaldir (`balkon`); açık kenarları planda çift sıra kırmızı kesik çizgiyle gösterilir (veranda profili kuralı); net alan açık dış kenara kadar. | Tek kat (v1.4.3, Motor) |
| 7.2 | Balkon iki katta aynı yerde: gövdenin ön sağ girintisinde (mutfağın / ODA 3'ün önünde), planda 337 × 165, gövde önünden 30 cm taşıyor. Taslakta gövdenin içindeki parça (taşma yok). | Kabul · **Soru 7** (taşma 30 cm kalacak mı; üst balkonun döşemesi ve korkuluğu; alt balkon köşesinde dikme mi konsol mu?) |
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
| 28.10.2026 | Blok adları (K03) | "Her blok malzeme kartındaki gibi isim isim olsun" (Güncel Şablon 2024 blok mantığı). | Yeni çift kat çizimi Şablon 2024 blok adlarıyla (`100'LÜK 125'LİK PANO`, `100'LÜK 125'LİK (120x100) PENCERELİ PANO`, `100X100 DIŞ KÖŞE DİREĞİ`…); Motor eşleme taslağı RAPOR §2. K03 kararı Lokman'da. |
