# 9 Ekim 2026 · üçüncü kör test (KT-03)

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı. Genel model motoru ve hesap öteki klasörlerde: `../2026-10-06_kor_test/` (tanımdan girdi, çizim seti), `../2026-10-03_yukleme/` (yükleme listesi, kural seti).

Lokman, 9 Ekim 2026 22:47: "sonra bunu test et". Aynı anda Mac'teki bir klasörü bu oturuma bağladı: içinde 80 m²'lik bir çelik projenin montaj paftası (PDF, yedi sayfa) ve yükleme listesi (PDF ve Excel) var. Bu kez üretim dosyası yok. KT-01 ve KT-02'deki gibi: modeli kur, çizim setini ve kurallarımızla kendi listemizi çıkar, listeyi gerçek liste açılmadan dondur, sonra kıyasla.

Proje (KT-03): tek kat çelik, 2+1 (salon, iki yatak odası; ayrı mutfak, banyo, hol), 80 m² (kapalı kısım); dış duvar karkası 140 mm, iç duvar 80 mm; kırma çatı, güneyde bir kanat, 6 cm poliüretan sandviç panel; güneybatıda (salonun önünde, mutfağın batısında) kolonlu, korkuluksuz veranda, doğuda giriş kapısının önünde sundurma; veranda ve sundurmanın kendi tek eğimli panel çatıları; iki baca; yöntem B (paftada tavan omegası ve aşık yerleşimi var). Müşteri ve bayi adı kayıtlarda geçmez. Montaj paftasının tarihi Eylül 2026.

## Kör test protokolü (KT-01 ve KT-02'deki gibi)

1. Klasördeki yükleme listesi (PDF ve Excel), kendi listemiz üretilip depoya kaydedilene kadar açılmadı; yalnız boyutu, değiştirilme tarihi ve özeti (SHA-256) alındı (`sonuc/KT03_dondurma.md`).
2. Girdi: montaj paftasındaki müşteri onay paftası (plan, teknik özellikler, açıklama notları, pencere detayı), duvar paneli yerleşimi (yerler, ölçü zincirleri, veranda ve sundurma kesitleri), makas ve dere yerleşimi (makasların ve çatı panellerinin yeri, çatının biçimi) ve elektrik yerleşimi (sayılar). Paftalardaki adetler (çatı kaplaması, tavan omegası, aşık, dere inişi) girdi olarak kullanılmadı.
3. Kuralların kapsamadığı her yerde karar listeden önce verildi ve yazıldı (aşağıda).
4. Kıyasta her fark sınıflanır: girdi hatası · kural hatası · karar farkı · listenin elle yuvarlaması · paftadan sayılan kalem. Yalnız ilk ikisi hata sayılır.

## Girdi

- **Tanım** (`tanim/KT03.json`, Yapı Tanımı 0.5; `tanim/kt03_tanim_uret.py` üretir; özeti dondurma kaydında). Müşteri projesinin geometrisidir; Lokman'ın onayıyla depoda (10 Ekim 2026: "Eklensin"). Duvarlar duvar paneli paftasındaki 26 panel (D01–D26: 15 dış, 11 iç), yerleri paftanın vektör çizgilerinden; boyları paftadaki ölçü zincirleriyle ±0,5 cm içinde. Dış duvar 14 cm, iç duvar 8 cm. Açıklıklar paftadaki dikme ve başlıklardan: 150/130 üç, 200/220 sürgülü iki (salon ve mutfak, verandaya), 100/70, 50/50 (pencereler Winsa, antrasit); dış kapı 95 × 210; beş iç kapı (dördü 90, banyo 80; iç kapılar alıcıya ait).
- **Mahaller** (karkas yüzleri arası; paftanın iç ölçüleriyle aynı): salon 16,69 · yatak odası 12,62 · çocuk odası 12,38 · hol 7,72 · mutfak 14,18 · banyo 6,93 m². Müşteri onay paftasındaki etiketler 0,0–0,44 m² büyük (17,13 · 12,84 · 12,6 · 7,73 · 14,39 · 7,08); etiket alanının neyle ölçüldüğü bilinmiyor, hesaba girmez. Verandanın etiketi (14,84) çatının saçağıyla (362 × 410).
- **Çatı:** kırma; saçak çizgileri karkasın dış yüzünden 30 cm (makas paftası: "Saçaklar ve alın çıkmaları 30 cm"); eğim 0,33, saçak kotu 280. Yüzler saçak çizgilerinin düz iskeleti: sekiz yüz, üç mahya (7,47 m), sekiz kırma (27,27 m), iki vadi (7,98 m). Veranda çatısı tek eğimli çatı paneli, eğim 0,08835 (kesit: kolonda 224,6, orta kolonda 238,32, bina duvarında 251,97), saçak dış kolondan 51,92 (eğik); sundurma çatısı eğim 0,17094 (bina duvarında 260, kolonda 240, açıklık 117), saçak kolonun dış yüzünden 30.
- **Çelik:** üretim dosyası yok. Panel adetleri paftadaki yerleşimden: dış duvar 15, iç 11, kolon 4 (K02, K03, K06, K07), kiriş 3 (K01, K04, K05), makas 36 (MK01–MK36), veranda ve sundurma çatı paneli 4 (Ç13–Ç16), baca 2 × 4. Ağırlık motorun proje ortalamalarından (katalog yolu; kural seti `celik`).
- **Elektrik** (`sonuc/KT03_pafta_sayimi.json`; elektrik yerleşim paftasından): 7 tijli duy, 4 glop, 5 tekli ve 3 çiftli anahtar, 13 tekli ve 4 çiftli priz, 1 uydu prizi.

## Liste çıkmadan önce verilen kararlar

1. **Çelik ağırlığı.** Üretim dosyası olmadığı için ağırlık motorun ortalamalarıyla: dış duvar 140 × 45 × 1,2 için 29,04 kg/m, iç duvar 80 × 45 × 1,2 için 19,75 kg/m, kolon 6,42 kg/m, kiriş 6,55 kg/m, çatı (kırma) 7,55 kg/m² (makaslı plan). Panel adetleri paftadan. Kırma uçlarının çatı panelleri (Ç01–Ç12, Ç17, Ç18; 14 panel) ayrı satır değil: motorun çatı ortalaması bütün çatı çeliğini kapsar, ağırlıkları makas satırında. Adetteki fark bekleniyor (KT-02'de listede ayrı satırdı).
2. **Bina alanı.** Kural: kapalı kısım + veranda + açık sundurma (Lokman, 9 Ekim 22:22). Oturum 93,81 m²; m²'ye bağlı satırlar 94 ile. Projenin adı 80 m² (kapalı kısım, kaplamayla 79,1 m²). m²'ye bağlı satırlarda fark bekleniyor (karar).
3. **Veranda ve sundurma çatısı.** Açıklama 7: "tek eğimli panel olacak": çatı paneli, üstü sandviç panel (KT-01'deki çatı panelli müştemilat gibi). Kural (`ek_yapi_ve_korkuluk.cati_panelli_cati`): dere, saçak sacı, saçak omegası ve alın sacı yok; saçağı ve alınları Boardex (10 + 15 cm); KT-01'deki gibi tavan omegası da yok. Bina duvarına dayanan kenarlar (9,62 m) özel mahya satırında. Makas ve dere paftasına çatının biçimi için bakıldı: verandanın çatısının batı saçağının iki ucunda iniş işareti var. Kural değiştirilmedi; liste kuralla çıktı. Gerçek listede veranda deresi varsa kural farkıdır ve sorulur.
4. **İç kapılar** alıcıya ait (teknik özellikler ve açıklama 5): Melamin kapı satırı yok; kapı boşlukları duvar hesabında. Banyo kapısının boşluğu paftada 80 (kural 90; modeldeki ölçü).
5. **Kapsam.** Vitrifiye alıcıya ait. Sıhhi tesisat için not yok: listede. Boya listede (Polisan; dış ve iç cephe, tavan, astar). Pencereler listede (Winsa, antrasit); pencere rengi için listede renk kuralı yok, satıra renk yazılmadı. Nem bariyeri yok (açıklama 1: Boardex + çelik karkas + OSB + alçıpan).
6. **Baca.** İki baca, 38 × 38 (salonun kuzeydoğu, yatak odasının kuzeybatı köşesinde). Karkas 80 × 45 × 0,8 (KT-01'in karkas modelinde ve listesinde böyleydi); ağırlık modelsiz: iç duvarın 0,8 ortalaması bacanın boyuna oranlandı, iki baca tek satır (8 dar panel). Üst kot paftada yok: KT-01'deki gibi mahya kotunda (bacaların üstündeki mahya 381,4 cm). Çatının üstünde kalan kısmı ve üst kapağı dış cephe Boardex'inde. Açıklama 4'teki "içi de olacak" için kuralımız yok: listeye yazılmadı (soru).
7. **Kolon ve kirişler.** Veranda: üç kolon (K02, K03, K06), iki kiriş (K04 batı, K05 orta); yükseklikler kesitten, kiriş derinliği 30 cm (paftada yok; varsayım). Sundurma: bir kolon (K07), kiriş yok (paftada yalnız kolon var). Holdeki K01 kirişi holü mutfak ile banyo arasındaki duvarın hizasında enine geçer (kaplaması tavan alçıpanında).
8. **Dış duvar 140 mm.** Profil 140 × 45 × 1,2 (teknik özellikler; zemin kat et kalınlığı kuralı 1,2). Duvar paneli paftasındaki "dış duvarlarda çift kat izolasyon" notu: duvar izolasyonu listede yok (Lokman, 7 Ekim: göndermiyoruz).
9. **Elektrik işaretleri.** Tek tırnaklı anahtar tekli, çift tırnaklı çiftli; aynı uçtan çıkan iki priz çiftli priz. Zil butonu 1 (kural zaten 1). Sigorta kutusu paftada giriş kapısının yanında: kural zaten girişi alıyor.
10. **Yöntem.** B: projenin yapıldığı yöntem (paftada tavan omegası ve aşık). A: çelik standardı (Lokman, 7 Ekim 2026). İkisi de çıkarıldı.

## Motor değişiklikleri (liste öncesi; kural değil, modelin anlatılabilmesi için)

- `girdi_genel.py`: iç kapılar alıcıya aitse (`kapsam.ic_kapi: false`) Melamin kapı satırı yazılmaz. Ek yapı yokken çatı panelli çatı (veranda, sundurma): çatı paneli satırının alanı örttükleri açık alanların dış ölçüyle alanı, adedi düzlem düzlem (`cati_paneli_adedi`); kenar kaplaması bina Boardex'inde (önceden hiçbir satıra girmiyordu); tavan omegasının alanından ve yöntem A'da tavan ve çatı panelinin alanından düşülür; duvar dibi satırında adları. Modelsiz birden çok baca tek satır. Ek yapı varken hesap öncekiyle aynı.
- `yukleme.py`: çatı paneli satırının adı girdiden; satır notlarında çatı panelli çatının adı (ek yapı ya da veranda ve sundurma).
- `ifc_genel.py` (çizim): genel makas grubu (`eksen`; üstü makaslı düzlemlerin kotundan, kırma uçlarında kesik); çatı panelli açık alanın tavanı panelin altı.
- Değişmezler denendi: bugünkü kod 0.12–0.16 setleriyle kendi günlerinin çıktılarını, 0.17 setiyle bu commit'ten önceki (`033572a`) çıktıları bayt bayt aynı veriyor; KT-01 ve KT-02'nin betikleri ve çizim setleri (plan, görünüşler, pafta, çatısız görünüm, özet) aynı çıktıyı veriyor; `saglama.py` toplam sorun 0.

## Kıyas (10 Ekim 2026; gerçek liste dondurmadan sonra açıldı)

Rapor: `docs/raporlar/2026-10-10_Kor_Test_KT03.md`. Satır satır tablo: `sonuc/KT03_kiyas.md`.

Dondurma commit'i `1f7ba6c` (9 Ekim 23:55:13). Açılmayan iki dosyanın özeti 23:55:42'de yeniden alındı (dondurma kaydındakiyle aynı); liste 23:56'da açıldı. Liste adsız ve fiyatsız döküldü (`sonuc/KT03_gercek_liste.json`; birinci sayfanın malzeme satırları, 23 Eylül 2026). Excel'in ikinci sayfası (adı bir kişinin adı) okunmadı. Liste yeni şablonla: grup başlıkları, çelikte rulo form makinesi sütunu, depo ve mekanik tesisat grupları; bina alanı 80 m².

| Liste | Aynı satır (102 satırda) |
|---|---|
| Kör liste, yöntem B (dondurulan) | **46** |
| Düzeltilmiş, yöntem B (yalnız girdi hatalarımız düzeltildi; kurallar aynı) | **48** |
| + Eylül 2026 uygulaması (bilgi) | 54 |
| İki kural sorusu listedeki gibi cevaplanırsa (bilgi) | 55 |
| Kör ve düzeltilmiş, çelik standardı (A; bilgi) | 45 ve 47 |

Kör listedeki 56 farkın asıl nedeni: girdi 2 · kural 21 · karar 18 · elle 9 · pafta 6. Bizim hatamız 23 satır.

- **Girdi hatası.** Makas ve dere paftasında makas numaraları MK01 ve MK14'ü atlıyor: 34 makas. Numaraları kesintisiz sayıp 36 yazmışım; listede de 34. Ayrıca veranda ve sundurma çatısının saçak çizgisini paftadaki çizim yerine kesit detayından okumuşum (sundurma 8 cm kısa); adede etkisi yok. Düzeltilmiş tanımı `tanim/kt03_tanim_duzeltilmis.py` üretir (`tanim/KT03_duzeltilmis.json`).
- **Kural eksikleri** (raporun 4. bölümü; Lokman'a soruldu, 11. bölüm). Veranda ve sundurmanın tek eğimli panel çatısının kenarları (12 satır): listede saçaklarda dere ve iniş, özel büküm saçak sacı, eğik kenarlarda sıfır alın sacı var, Boardex şeridi yok, tavan saçağıyla; kuralımız KT-01'in müştemilatından. Üretim dosyası yokken kırma uçlarının çatı panelleri satır olmuyor (2 satır). Çatı çıkış kapağı (1). Bacanın içi: baca borusu, T, kör tapa, maşon, şapka (5). Taharet musluğu (1).
- **Karar farkları.** Bina alanı (liste 80, kural 94: uçlar, inox taş, RYSB), vida kararları (alçıpan vidası × 40, trapez vidanın omega ve aşıkta olmaması), duvar izolasyonu gönderilmiyor, yöntem B kalemlerinin formülleri, ölçünün alındığı yüz.
- **Çelik.** Panel adetleri dış ve iç duvar, baca, kolon-kiriş ve C profillerde aynı; makas düzeltilince aynı. Ağırlık üretim dosyası olmadığı için motorun ortalaması: toplam 2 556 / 2 847 kg (C profiller hariç listede).
- Elektrik paftasındaki sayılar (yeniden sayıldı) listeyle aynı; yalnız tekli priz listede bir fazla (14 / 13).

Kıyasın dosyaları:

- `kt03_kiyas.py`: kıyas ve mekanik denetimler.
- `kt03_farklar.json`: sınıflar ve nedenler; elle yazılır, kıyas denetler.
- `kt03_kiyas_kos.sh`: düzeltilmiş tanımdan iki liste, Eylül 2026 katmanı, ne olur ve tablo; kural seti 0.17'ye sabit.
- `kt03_ne_olur.py`: iki kural sorusunun (panel çatının kenarları, kırma uçlarının çatı panelleri) etkisi; yalnız bilgi.
- `kt03_sayfa.py`: Lokman'a verilen tek sayfa; depoya yazılmaz.
- `sonuc/KT03_gercek_liste.json`, `sonuc/KT03_duzeltilmis_*`, `sonuc/KT03_ne_olur_*`, `sonuc/KT03_kiyas.{md,json}`.

## Dosyalar

- `kt03_kos.sh`: tanımdan iki liste (B ve A); kural seti 0.17'ye sabit.
- `sonuc/KT03_pafta_sayimi.json`: elektrik sayımı.
- `sonuc/KT03_{B,A}_girdi.json`, `sonuc/KT03_{B,A}_yukleme.{json,md}`: dondurulan listeler (96'şar satır).
- `sonuc/KT03_dondurma.md`: dondurma kaydı.
- `tanim/`: kör ve düzeltilmiş tanım (`KT03.json`, `KT03_duzeltilmis.json`) ve onları üreten betikler; betikler tanımları bayt bayt aynı üretir (Lokman, 10 Ekim 2026: "Eklensin").
- `cizimler/KT03_A`, `cizimler/KT03_B`: düzeltilmiş tanımdan, kural seti 0.18 ile çizim seti (12'şer çıktı; `../2026-10-06_kor_test/cizim_seti_kos.sh`, A `--yontem panel`, B `--yontem omega_asik`). Plan, görünüşler, pafta, çatısız görünüm ve özet her üretimde bayt bayt aynı; IFC'de kimlikler ve zaman, geometri özetinde sıra, makaslı görünümde ve perspektiflerde görüntü işleme gürültüsü (eşiği aşan piksel farkı yok) değişir.
- `kt03_cevaplar_kos.sh`, `kt03_cevaplar_notlari.json`, `sonuc/KT03_cevaplar_*`: Lokman'ın 10 Ekim cevaplarından sonra (aşağıda).

## Lokman'ın cevaplarından sonra (10 Ekim 2026)

Lokman 10:18'de raporun yedi sorusunu cevapladı; 10:29'da tek eğimli panel çatının nasıl bittiğini gösteren beş fotoğraf, 10:37'de KT-01'in yapılmış halinin üç fotoğrafını gönderdi; 10:39'da müştemilat için "hayır istediğim o 5 görseldeki gibi olması çok güzel duruyor". Cevaplar yazıldığı gibi ve uygulanışları: `docs/sartname/yukleme_listesi_yontemi.md`, "Lokman'ın cevapları (10 Ekim 2026) ve uygulanışı". Kural seti 0.18:

- **Tek eğimli çatı panelli çatının kenarları** (`panel_cati_kenarlari`; veranda, sundurma ve müştemilat): saçakta dere ve derenin altında özel büküm saçak sacı; eğik kenarlarda sundurma kapama (adı Lokman'ın); ikisi de L 2500, 20 cm bindirme. Kenarda Boardex şeridi yok; veranda ve sundurmanın tavanı çatının planıyla (saçağıyla) Boardex. Müştemilatta saçağın ve yanların altı Boardex (15 cm), yüzü kapamayla (Claude'un okuması; Lokman'a yazıldı).
- **İniş** (`inis.alcak_cati_ustundeki_kose: false`): alçak bir çatının üstüne düşen köşeye iniş konmaz ("İniş olmasın"); her dere hattının en az bir ucunda iniş kalır. Kısa derede tek iniş: açık soru.
- **Listeye girmeyenler:** çatı çıkış kapağı ("Çatı çıkış kapağı yok"), bacanın içi ("sadece karkasını yapıyoruz göz ardı et").
- **Taharet musluğu:** vitrifiye dahilse ıslak hacim başına 4. Bu projede vitrifiye alıcıya ait: satır yok.
- **Saçak omegası:** çatı ve tavan panelli sistemlerde yok (öyleydi).
- **Kırma uçlarının çatı panelleri:** "Zaten üretim dosyası vermeyeceğiz sen kendin oluşturacaksın paftayı": bizim paftamızdan sayılacak; pafta kuralları sıradaki iş (`../../kurallar/cizim/`).

| Liste | Aynı satır (102 satırda) |
|---|---|
| Düzeltilmiş, yöntem B (0.17; 00:24 kıyası) | 48 |
| Cevaplardan sonra, yöntem B (0.18) | **59** |
| Cevaplardan sonra, çelik standardı (A; bilgi) | 58 |

Cevaplardan sonra farklı kalan 43 satır: kural 2 (kırma uçlarının çatı panelleri) · karar 25 · elle 10 · pafta 6. Panel çatının kenarları konusunun 12 satırından 11'i tutuyor; dere kelepçesi kuraldan 104 (13 dere × 8), listede 110 (formülsüz). İniş 11 (listede 11) ama dağılım farklı: paftada ana çatı 8, veranda 2, sundurma 1; bizde 7, 2, 2 (ana çatının verandanın üstüne düşen iki köşesinden biri düşüyor; sundurmanın 1,62 m'lik deresinin iki ucunda iniş). Tablo: `sonuc/KT03_cevaplar_kiyas.md`.

- `kt03_cevaplar_kos.sh tanim/KT03_duzeltilmis.json [python]`: düzeltilmiş tanımdan güncel kural setiyle (0.18 ve sonrası) iki liste ve tablo. Satır notları `kt03_farklar.json` + `kt03_cevaplar_notlari.json` (üstüne yazar: `kalan`, `pay`, giriş, adet dışı farklar); kör listenin sınıfları değişmez.
- 00:24 kıyası ve dondurulan listeler 0.17 setine sabit (`kt03_kiyas_kos.sh`, `kt03_kos.sh`); 0.18'le yeniden üretildiklerinde de bayt bayt aynı çıkıyor (betikler seti kendileri seçer).
