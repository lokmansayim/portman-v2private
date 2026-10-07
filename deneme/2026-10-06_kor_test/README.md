# 6–7 Ekim 2026 · kör test (KT-01) ve genel model motoru

Deneme kodu; canlıda değil, Motor'un yerine geçmez. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı. Kıyasın raporu: `docs/raporlar/2026-10-07_Kor_Test_KT01.md`.

Lokman, 6 Ekim 2026 21:22: klasördeki DWG bizim plan, görünüş, IFC ve perspektiflerimize çevrilecek; kurallarımızla kendi yükleme listemiz çıkarılacak; en son klasördeki gerçek listeyle kıyaslanacak, hata varsa düzeltilecek.

Proje (KT-01): tek kat çelik, 2+1, müştemilatlı, 98,65 m²; çatı beşik + cumba, veranda sundurması ve müştemilat çatısı; sandviç panel; yöntem B (tavan omegası ve aşık). Müşteri ve bayi adı kayıtlarda geçmez.

## Neden yeni bir motor

Ç8201 için yazılan kod (`../2026-10-02_celik`) yalnız dikdörtgen kapalı kutuyu, yanında dikdörtgen verandayı ve dikdörtgen kırma çatıyı kurabiliyordu. KT-01 bunlara uymuyor: ek yapı (müştemilat), binanın köşesinde korkuluklu veranda, farklı yükseklikte duvarlar, beş düzlemli çatı (mahya, kırma, vadi, duvara dayanan kenarlar). Lokman'ın hedefi "model verilecek, liste aynı sistemle dönecek" olduğu için motor genelleştirildi; projeye özel hesap yazılmadı.

| Dosya | İçerik |
|---|---|
| `yapi.py` | Yapı Tanımı 0.5: duvarlar modeldeki karkas panellerinin kutularıdır; mahaller, kaplanan yüzler (dış / iç), köşeler, boşluklar koddan çıkar |
| `cati_genel.py` | Çok düzlemli çatı: kenar türleri (saçak, mahya, kırma, vadi, alın, duvar dibi), kalkanlar, aşık sıraları, kaplama dizilimi (kırma çatı diziliminin genellemesi) |
| `girdi_genel.py` | Tanımdan metraj ve yükleme listesi girdisi (`../2026-10-03_yukleme/girdi_uret.py`'nin genel hali) |
| `sahne.py`, `ciz_genel.py` | Dıştan görünen yüzeyler; plan, çatı planı, dört görünüş, pafta |
| `ifc_genel.py`, `perspektif.py` | IFC4 modeli (şema doğrulamasıyla) ve IFC'den perspektif görüntüler (VTK, ekransız) |
| `C8201_05.json` | Ç8201'in aynı modeli, 0.5 şemasıyla (elle çevrildi): genel motorun sağlaması için |
| `saglama.py` | Genel hat Ç8201'de 0.4 hattıyla aynı metrajı ve aynı iki listeyi (satır satır) veriyor mu; genel dizilim eski kırma dizilimiyle aynı adedi veriyor mu |
| `tavan_genel.py` | Tavan omegası dizilimi (Eylül 2026 paftasındaki gibi: her gözde ilk hat duvar yüzünde); yalnız `--sablon 2026` ile kullanılır |
| `skp_profil.py` | Karkas modelinden (SKP) panel panel üye boyları ve et kalınlığı: çelik ağırlığının girdisi |
| `kiyas.py`, `kiyas_farklar.json`, `kiyas_kos.sh` | Gerçek liste ile dört listemizin satır satır kıyası; her farkın elle yazılmış sınıfı ve nedeni (kod sayımla denetler) |
| `sablon_eski_listeler.py` | Eylül 2026 katmanı 2025 tarihli üç gerçek listede ne veriyor |
| `kiyas_sayfa.py` | Kıyası ve rapordaki karar, hata ve soru tablolarını tek bir okunur sayfaya (HTML) çevirir; çıktısı depoya yazılmaz |
| `sonuc/` | KT-01'in dondurulan girdisi ve listesi, dondurma kaydı, gerçek listenin adsız ve fiyatsız dökümü, düzeltilmiş girdi ve üç liste, kıyas tabloları |

Hesap `../2026-10-03_yukleme/yukleme.py`'de kaldı; genel model için eklenen alanlar geriye dönük uyumlu (eski girdilerin çıktıları bayt bayt aynı). Yeni varsayımlar `kurallar.json`'da (`cok_duzlemli_cati`, `duvar_dibi`, `ek_yapi_ve_korkuluk`, `kapsam_alici`, `nem_bariyeri_dis_cephe`, `elektrik_oda_ek`).

## Çalıştırma

```
python yapi.py tanim.json                       # mahaller ve yüzler
python girdi_genel.py tanim.json --cikti cikti  # metraj girdisi: cikti/<kod>_girdi.json (var olan, içeriği farklı dosyanın üstüne yazmaz)
python ../2026-10-03_yukleme/yukleme.py cikti/KT01_girdi.json --cikti cikti/liste.json --md cikti/liste.md
python ../2026-10-03_yukleme/yukleme.py cikti/KT01_girdi.json --sablon 2026 --cikti cikti/liste_2026.json   # + Eylül 2026 uygulaması
python ciz_genel.py tanim.json --cikti cikti    # plan, pafta, görünüşler
python ifc_genel.py tanim.json cikti/KT01.ifc   # IFC4 + şema doğrulaması
python perspektif.py cikti/KT01.ifc cikti KT01  # perspektifler
python skp_profil.py model.pkl --json boylar.json   # karkas modelinden üye boyları ve et kalınlığı (model.pkl: ../2026-10-02_skp/kaydet.py)
bash kiyas_kos.sh KT01_duzeltilmis.json         # düzeltilmiş girdi, üç liste ve kıyas tabloları (sonuc/)
python kiyas_sayfa.py --cikti KT01_kiyas.html --zaman "7 Ekim 2026 03:30"   # kıyasın okunur sayfası (depo dışına)
python saglama.py                               # genel motorun ve Eylül 2026 katmanının sağlaması (yaklaşık bir dakika)
```

KT-01'in tanımı (`KT01.json`) ve ondan üretilen çizimler depoda değil: müşteri projesinin geometrisi, İE-05 gereği ayrı onayla eklenir. Çizimler, IFC ve perspektifler Lokman'a dosya olarak verildi.

## Kör test protokolü

1. Klasördeki gerçek liste ve Excel hesaplama motoru, kendi listemiz üretilip depoya kaydedilene kadar açılmadı (yalnız dosya boyutu ve özeti alındı; `sonuc/KT01_dondurma.md`).
2. Girdi yalnız DWG'deki zemin kat planı, teknik özellikler ve açıklama notları ile SKP karkas modelinden okundu. Montaj paftalarındaki adetler (kaplama, omega, aşık, iniş) girdi olarak kullanılmadı.
3. Kuralların kapsamadığı her yerde karar listeden önce verildi ve yazıldı (aşağıda).
4. Kıyasta her fark sınıflanır: girdi hatası · kural hatası · karar farkı (bugünkü kural o günkü uygulamadan farklı) · listenin elle yuvarlaması · paftadan sayılan kalem. Yalnız ilk ikisi hata sayılır; bir satırın birden çok nedeni varsa sınıf asıl nedendir, bizim payımız ayrıca yazılır.

## Liste çıkmadan önce verilen kararlar

Kuralların söylemediği, projeden doğan durumlar. Hepsi `varsayim` ya da `soru` durumunda; teyit bekliyor.

1. **Müştemilatın iç yüzleri.** Proje notu yalnız "80x45x08, mineral yün olmayacak" diyor; iç kaplama yazmıyor. Dış cephe paneli tarifine göre (OSB + alçıpan) sayıldı: 23,6 m² duvar, 15,3 m² tavan. Binanın müştemilata bakan duvarı notta yazdığı gibi Boardex.
2. **Müştemilat çatısı.** Çatı paneli + sandviç panel (proje notu). Çatı panelinin ağırlığı 100 m² için verilen değerden oturuma oranlandı; bu mahalde tavan omegası ve aşık sayılmadı.
3. **Müştemilat duvar çeliği.** Dış 80 × 45 × 0,8 için motorda birim ağırlık yok; iç duvarın 80 × 45 × 0,8 değeri (13,0 kg/m) alındı, yüksekliğe oranlandı.
4. **Korkuluk ve giriş çerçevesi.** Çelik: dış duvarın birim ağırlığı yüksekliğe oranlandı. Kaplama: iki yüzü de Boardex; üst yüzü sayılmadı.
5. **Baca.** Karkas dört dar panel; dış duvarın birim ağırlığıyla. Çatının üstünde kalan kısmı Boardex.
6. **Alıcıya ait olanlar.** Dış kapı, pencere, boya, vitrifiye ve tesisat listede yok. Pencere alıcıya ait olduğu için pencere vidası ve silikonize mastik de yazılmadı.
7. **Nem bariyeri.** Dış cephe için satır eklendi (Boardex'in net alanı, m²); okunan listelerde kuralı yoktu.
8. **Çatı kaplaması.** Çok düzlemli dizilim: her yüz açılır, şerit şerit dizilir; panel boyları tam boy şeritlerin boyu; çapraz kesilen parçalar eşlenir. Kırma çatı kuralının genellemesi.
9. **Duvar dibi.** Alçak çatıların duvara dayandığı kenarlar (11,35 m) için kural yok; satır mahya parçası gibi sayıldı ve `soru` olarak işaretlendi.
10. **Dere inişi.** Köşe, dere hattının ucu sayıldı: 7 iniş. (Dört köşe varsayılsaydı 4.)
11. **Elektrik.** Müştemilat için 1 duy, 1 anahtar, 1 priz. Kablo boyundaki en uzak mesafe, kapalı kısmın tamamının (müştemilat dahil) köşegeni.
12. **Panel adetleri.** Modelden (duvar panelleri, makaslar, kirişler); kg motorun ortalamalarından.
13. **Banyo kapısı.** Modelde boşluk 80 cm; kural 90 der. Modeldeki ölçü kullanıldı.
14. **Veranda.** Tavan ve köşebent hesabında brüt ölçü (Ç8201'deki gibi).
15. **İç kiriş.** Salon ile mutfak arasındaki kirişin açıkta kalan 3 metresi alçıpanla kaplı sayıldı (2,0 m²).

Kıyastan sonra bu kararların durumu (7 Ekim):

- **Tuttu:** müştemilat çatısının çatı paneli ve sandviç panelle kapatılması, o mahalde tavan omegası ve aşık olmaması (2); dış kapı, pencere, vitrifiye ve tesisatın, pencere vidasının listede olmaması (6); kaplamada panel toplamı, 33 (8); panel adetleri, on grubun onunda (12); banyo kapısı (13); iç kirişin kaplandığı (15).
- **Tutmadı, düzeltildi:** müştemilat ıslak hacim, iç yüzleri ve tavanı yeşil alçıpan (1); çelik ağırlıkları ve et kalınlıkları modelden: müştemilat duvarı, korkuluk, baca, çatı paneli (2, 3, 4, 5, 12); bacanın üst kapağı (5); boya: yalnız dış ve iç cephe boyası alıcıya ait, tavan boyası ve astar listede (6); nem bariyeri yalnız duvarlar × 1,08 (7); müştemilat saçağında dere ve iniş yok (10); müştemilat elektriği 2 glop ve 1 çiftli anahtar (11); iç kirişin kaplaması tavan satırında (15).
- **Karar ya da soru:** duvar dibinde listede damlalık var (9); orta inişin eşiği: kural 5, pafta ve liste 7 (10); kablo mesafesi listede sigortadan (11); çapraz kesilen parçaların eşlenmesi: toplam aynı, boylara dağılım farklı (8); silikonize mastik listede 3 adet, kuralı bilinmiyor (6); veranda tavanı ve köşebentte ölçü (14).

## Kıyas (6–7 Ekim 2026)

Gerçek liste, kendi listemiz depoya kaydedildikten (commit `0658a1d`, 22:47:02) sonra açıldı (22:47:34). Adedi yazılı 98 satırı dört listemizle karşılaştırıldı (`sonuc/KT01_kiyas.md`; rapor `docs/raporlar/2026-10-07_Kor_Test_KT01.md`):

| Liste | Aynı satır | Dosya |
|---|---|---|
| Kör liste (dondurulan) | 42 / 98 | `sonuc/KT01_yukleme.json` |
| Düzeltilmiş: yalnız bizim hatalarımız düzeltildi, bugünkü kurallar | 48 / 98 | `sonuc/KT01_duzeltilmis_yukleme.json` |
| + Eylül 2026 uygulaması (`--sablon 2026`) | 61 / 98 | `sonuc/KT01_duzeltilmis_2026.json` |
| + pafta sayımı (elektrik, iniş) | 71 / 98 | `sonuc/KT01_duzeltilmis_2026_pafta.json` |

Çelik: gerçek 1 936,87 kg; kör liste 1 995,20; düzeltilmiş 1 936,90 (modeldeki profil boyundan).

**Düzeltme ilkesi.** Varsayılan hesap yalnız bizim hatalarımız düzeltilerek değişti: girdi hataları (kapsam, renk), motor ve geometri hataları (aşık sıraları, kalkanlar, baca üst kapağı, dere hatları, et kalınlığının modelden okunması) ve o projede ilk kez karşılaşılan durumlarda liste öncesi verdiğimiz varsayımların yerine listedeki uygulama (müştemilat ıslak hacim ve ayrı satırlar; çatı panelli çatıda dere, saçak sacı ve alın sacı yok; nem bariyeri yalnız duvarlar; iç kirişin kaplaması tavanda; dere kapağı serbest uçlarda; baca çevresi mahya bandında; depo elektriği; çelik ağırlığı profil boyundan; baş makas Z'si). Eylül 2026 listesinin, mevcut kuralların (Lokman, mühendis, Excel motoru, 2025 notları ve listeleri) zaten kapsadığı konularda farklı yaptığı her şey `sablon_2026` katmanındadır; varsayılan değildir, hangi maddelerin kural olacağına Lokman karar verir.

**Katmanın işaretlenmesi.** `--sablon 2026` ile hesaplanan listede bir satırın durumu, varsayılan hesapla karşılaştırılarak konur: farklı olan (ya da varsayılanda olmayan) her satır `sablon`dur; aynı kalan satır varsayılan durumuyla yazılır. Farklı satırın notunda "Bugünkü kurallarla: …" yazar.

**Sınıflama.** Her farkın sınıfı `kiyas_farklar.json`'da elle yazılıdır; `kiyas.py` sayımla denetler: kör listede farklı her birimin sınıfı, son listede farklı kalan her birimin açıklaması olmalı; sınıfı bizim hatamız olmayan bir satırın adedi düzeltmelerimizle değiştiyse "bizim payımız" yazılmış olmalı; bizim listelerimizde hiçbir birime girmeyen satır kalmamalı; listeler doğru yuvada olmalı.

**Dondurulan listenin yeniden üretimi.** Commit `0658a1d`'deki kod ve `sonuc/KT01_girdi.json` ile. Bugünkü kod aynı girdiden dokuz elektrik satırını farklı verir (depo kuralı bilerek değişti).

## Sağlama

- `saglama.py`: Ç8201 genel hattan geçirildi; mahal alanı, çevresi, köşeleri, boşlukları, dış çevre, iç duvar boyu, çatı ölçüleri, OSB takviyesi ve iki yükleme listesinin (baz ve sandviç panel) bütün satırları 0.4 hattıyla aynı. Genel dizilim 840 kırma çatı denemesinde eski dizilimle aynı adedi verdi. Bu sağlama, KT-01 listesi dondurulmadan önce genel motorda üç hata buldurdu (köşe payının yazıldığı duvar, iç duvar boyunun ölçüsü, L birleşimde duvar yüzü); düzeltildi.
- `saglama.py` ayrıca Eylül 2026 katmanının değişmezlerini yedi girdide denetler: varsayılan hesapta `sablon` durumlu satır yok; varsayılan hesap, katman kurallardan silinince de aynı; katmanla farklı olan her satır `sablon`, `sablon` olan her satır gerçekten farklı.
- Bağımsız denetim (7 Ekim): kıyasın sayıları, pafta ölçümleri ve kod, işi görmeyen ayrı Claude oturumlarına iki tur denetlettirildi. Model okuyucunun toplamları (46 panel, 1223 üye, 1 369,80 m; et 0,8 mm 667,22 m, 1,2 mm 702,58 m) iki bağımsız yöntemle aynı çıktı.
- KT-01 tanımı: mahallerin karkas yüzleri arası alanları DWG'deki etiketlerle karşılaştırıldı (10,86 / 10,80 · 4,00 / 3,90 · 12,99 / 13,00 · 36,27 / 36,35 · 15,65 / 15,90); oturum 98,66 m² (çizimde 98,65); çatı yüzleri SKP'deki yüzlerle aynı alanda (41,64 · 37,70 · 14,63 · 18,40 m²).
- IFC4: şema hatası 0.

## Sınırlar

- Yalnız eksenlere paralel duvarlar. Çatı düzlemleri tanımda elle verilir (modeldeki yüzlerden); düzlemlerin kesişimi koddan çıkarılmaz.
- Genel model şimdilik yalnız sandviç panel ve tek kat panel kaplamasını hesaplar; öteki kaplamalar yalnız dikdörtgen kırma çatılı 0.4 hattında. Girdi bir yöntem (A ya da B) için üretilir: bayi kuralı yöntemi değiştiriyorsa girdi yeniden üretilmelidir (kod durdurur).
- Çelik ağırlığı modelden yalnız katı çizilmiş, panellere ayrılmış modellerde okunur; 140 mm profilin birim ağırlığı bilinmiyor (o profilde motorun ortalaması). Birim ağırlıklar tek projenin listesinden; 2025 tarihli 62 m² projede tutmuyor.
- Aşık sıraları paftayla birebir aynı değil (cumba mahyasının yanındaki iki kısa sıra, kırma köşesindeki iki eğik parça); tavan omegası diziliminde verandadaki hat boyu ve bacanın kestiği hat paftadan farklı. Ek yapı tek mahal sayılır.
- Eylül 2026 katmanı, girdide ilgili ölçü yoksa o kalemde yalnız formülü değiştirir (eski örnek girdilerde saçağın altındaki cephe boyu, tavan omegası dizilimi, duvar dibi kenarı ve sigortanın yeri yok).
- Formül metinlerinin bir kısmında katsayılar metne sabit yazılıdır; kural değeri değişirse metin de güncellenmelidir.
- SKP ve DWG'den tanıma geçiş elle yapıldı (ölçüler betiklerle okundu); otomatik çıkarıcı yok.
- Çok düzlemli çatıda panel boyu uzatma kuralı denenir; kesim planı çizimi henüz yalnız kırma çatıda var.
- Görünüşler yüzeylerin uzaktan yakına boyanmasıyla çizilir; iç içe geçen yüzeylerde hata verebilir.

## Kişisel veri

Depodaki dosyalarda müşteri, bayi ve çalışan adı, telefon ve fiyat yok. Kaynak dosyalar (DWG, SKP, liste) depoya alınmadı. Gerçek listenin dökümü (`sonuc/KT01_gercek_liste.json`) kalem, boyut, adet, ağırlık, hücre formülü ve açıklama sütunlarını içerir; ad, iletişim ve hazırlayan satırları alınmadı, dosya adının başı maskelendi. Düzeltilmiş tanım (`KT01_duzeltilmis.json`) müşteri projesinin geometrisidir; depoda değil.
