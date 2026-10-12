# 6–7 Ekim 2026 · kör test (KT-01) ve genel model motoru

Deneme kodu; canlıda değil, Motor'un yerine geçmez. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı. Kıyasın raporu: `docs/raporlar/2026-10-07_Kor_Test_KT01.md`. Lokman'ın 7 Ekim 07:45 kararlarından sonraki durum aşağıda ("Kararlardan sonra"); 8 Ekim 00:45 ve 07:23 cevaplarından sonraki durum onların altında.

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
| `tanim/` | KT-01'in tanımı: kör (`KT01.json`) ve düzeltilmiş (`KT01_duzeltilmis.json`), ikisini üreten betikler, SKP'den okunan profil boyları. 8 Ekim 2026'dan beri depoda (Lokman'ın onayıyla) |
| `cizimler/` | KT-01'in çizim seti, iki yöntemle (`KT01_B`: yapıldığı gibi; `KT01_A`: çelik standardı); `cizim_seti_kos.sh` çıktısı (8 Ekim 2026) |
| `saglama.py` | Genel hat Ç8201'de 0.4 hattıyla aynı metrajı ve aynı iki listeyi (satır satır) veriyor mu; genel dizilim eski kırma dizilimiyle aynı adedi veriyor mu; panel boyu kuralı (yuvarlama, uzatma, pay) iki motorda aynı boyu ve adedi seçiyor mu; özet `sonuc/saglama.json` |
| `kurallar_oku.py` | Kural setini `../2026-10-03_yukleme/kural.py` üzerinden okur (güncel set ya da `PORTMAN_KURALLAR` ile seçilen eski set) |
| `tavan_genel.py` | Tavan omegası dizilimi (Eylül 2026 paftasındaki gibi: her gözde ilk hat duvar yüzünde); yalnız `--sablon 2026` ile kullanılır |
| `skp_profil.py` | Karkas modelinden (SKP) panel panel üye boyları ve et kalınlığı: çelik ağırlığının girdisi |
| `kiyas.py`, `kiyas_farklar.json`, `kiyas_kos.sh` | Gerçek liste ile dört listemizin satır satır kıyası; her farkın elle yazılmış sınıfı ve nedeni (kod sayımla denetler). 7 Ekim 03:46'daki durumun kaydıdır: `kiyas_kos.sh` o günkü kural setine (0.12) sabittir ve çıktıları bayt bayt aynı üretir |
| `kararlar_kos.sh`, `kararlar_kiyas.py`, `kararlar_notlari.json` | Lokman'ın 7 ve 8 Ekim kararlarından sonra: güncel kural setiyle iki liste (B: yapıldığı yöntem; A: çelik standardı) ve gerçek listeyle durum tablosu (`sonuc/KT01_kararlar_*`). Her fark satırının türü ve nedeni elle yazılıdır; kod adetlerle denetler. Betiğe üçüncü argüman olarak eski bir set verilirse (0.13) o günkü tablo üretilir: açıklamalar `kararlar_notlari_setleri/<set>.json`dan |
| `kararlar_sayfa.py` | Kararlardan sonraki durumu tek bir okunur sayfaya (HTML) çevirir; çıktısı depoya yazılmaz |
| `../../kurallar/cizim/cizim_seti.json`, `cizim_seti_kos.sh` | Çizim seti standardı (10 Ekim 2026'ya kadar bu klasördeydi) (Lokman, 7 Ekim 07:45: "bunları kurala ekle") ve seti tek komutla üreten, tam olduğunu denetleyen betik; anlatımı `docs/sartname/cizim_seti.md` |
| `sablon_eski_listeler.py` | Eylül 2026 katmanı 2025 tarihli üç gerçek listede ne veriyor |
| `kiyas_sayfa.py` | Kıyası ve rapordaki karar, hata ve soru tablolarını tek bir okunur sayfaya (HTML) çevirir; çıktısı depoya yazılmaz |
| `sonuc/` | KT-01'in dondurulan girdisi ve listesi, dondurma kaydı, gerçek listenin adsız ve fiyatsız dökümü, düzeltilmiş girdi ve üç liste, kıyas tabloları; kararlardan sonraki iki girdi, iki liste ve durum tablosu (`KT01_kararlar_*`) |

Hesap `../2026-10-03_yukleme/yukleme.py`'de kaldı; genel model için eklenen alanlar geriye dönük uyumlu (eski girdilerin çıktıları bayt bayt aynı). Kör testle gelen kurallar `kurallar.json`'da (`cok_duzlemli_cati`, `duvar_dibi`, `ek_yapi_ve_korkuluk`, `kapsam_alici`, `nem_bariyeri_dis_cephe`, `elektrik_oda_ek`); o gün hepsi varsayımdı, `duvar_dibi` 8 Ekim'de karara bağlandı (özel mahya).

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
bash kiyas_kos.sh tanim/KT01_duzeltilmis.json   # düzeltilmiş girdi, üç liste ve kıyas tabloları (sonuc/); 0.12 kural setiyle (7 Ekim 03:46 kaydı)
bash kararlar_kos.sh tanim/KT01_duzeltilmis.json   # kararlardan sonra: güncel kural setiyle A ve B listeleri, durum tablosu (sonuc/KT01_kararlar_*)
bash kararlar_kos.sh tanim/KT01_duzeltilmis.json python3 0.13   # 7 Ekim 10:55 tablosu, o günkü kural seti ve açıklamalarla (sonra güncel setle yeniden koşulmalı)
python kararlar_sayfa.py --cikti KT01_kararlardan_sonra.html --zaman "8 Ekim 2026 02:00"   # kararlardan sonraki durumun sayfası (depo dışına)
bash cizim_seti_kos.sh tanim.json cikti [python] [--yontem panel|omega_asik]   # çizim seti: on iki çıktı ve denetimi
python kiyas_sayfa.py --cikti KT01_kiyas.html --zaman "7 Ekim 2026 03:30"   # kıyasın okunur sayfası (depo dışına)
python saglama.py                               # genel motorun, panel boyu kuralının ve Eylül 2026 katmanının sağlaması (yaklaşık bir dakika)
```

KT-01'in tanımı ve ondan üretilen çizimler 8 Ekim 2026'dan beri depoda: `tanim/`, `cizimler/` (Lokman, 07:23: "Evet ekle"). Kaynak dosyalar (DWG, SKP, gerçek liste) depoda değil.

## Kör test protokolü

1. Klasördeki gerçek liste ve Excel hesaplama motoru, kendi listemiz üretilip depoya kaydedilene kadar açılmadı (yalnız dosya boyutu ve özeti alındı; `sonuc/KT01_dondurma.md`).
2. Girdi yalnız DWG'deki zemin kat planı, teknik özellikler ve açıklama notları ile SKP karkas modelinden okundu. Montaj paftalarındaki adetler (kaplama, omega, aşık, iniş) girdi olarak kullanılmadı.
3. Kuralların kapsamadığı her yerde karar listeden önce verildi ve yazıldı (aşağıda).
4. Kıyasta her fark sınıflanır: girdi hatası · kural hatası · karar farkı (bugünkü kural o günkü uygulamadan farklı) · listenin elle yuvarlaması · paftadan sayılan kalem. Yalnız ilk ikisi hata sayılır; bir satırın birden çok nedeni varsa sınıf asıl nedendir, bizim payımız ayrıca yazılır.

## Liste çıkmadan önce verilen kararlar

Kuralların söylemediği, projeden doğan durumlar. Liste çıkarılırken (6 Ekim) hepsi `varsayim` ya da `soru` durumundaydı; sonraki durumları bu bölümün sonunda ve 7–8 Ekim bölümlerinde.

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

## Kararlardan sonra (7 Ekim 2026; kural seti 0.13)

Lokman raporun on iki sorusunu 7 Ekim 07:45'te cevapladı, 08:02'de beş okumayı düzeltti (cevaplar ve uygulanışı: `docs/sartname/yukleme_listesi_yontemi.md`). KT-01 güncel kurallarla iki kez hesaplandı (`kararlar_kos.sh`; tablo `sonuc/KT01_kararlar_kiyas.md`). Bu bölüm 7 Ekim'deki durumun kaydıdır (0.13); depodaki tablo güncel setle (0.14) üretilir, aradaki fark bir sonraki bölümde:

| Liste | Aynı satır | Dosya |
|---|---|---|
| Düzeltilmiş (7 Ekim 03:46; kararlardan önce) | 48 / 98 | `sonuc/KT01_duzeltilmis_yukleme.json` |
| Kararlardan sonra, yapıldığı yöntemle (B: tavan omegası ve aşık); elektrik sayıları paftadan | 63 / 98 | `sonuc/KT01_kararlar_B_yukleme.json` |
| Kararlardan sonra, çelik standardıyla (A: çatı ve tavan paneli) | 60 / 98 | `sonuc/KT01_kararlar_A_yukleme.json` |

- **Yeni tutan 15 satır:** 10'u kararlardan (5'i iniş kuralından: iniş borusu ve ona bağlı kalemler; eşik öneri, teyit bekliyor), 5'i elektrik sayılarının paftadan alınmasından. Önce tutan hiçbir satır bozulmadı. 21 satırın adedi değişti (15 kararlarla, 6 pafta sayımıyla).
- **B'de farklı kalan 35 satır:** 12 satırda Lokman'ın kararı o listeden farklı (liste o gün başka uygulamayla hazırlanmış); 3 satır yöntemden (omega, aşık, saçak omegası: çelikte artık yok); 16 satır listenin elle hesabı, yuvarlaması ya da elle dizilimi; 2 satır ölçünün alındığı yüzden (karar: bizdeki); 2 satır kural bekliyor.
- **A listesi** bu proje bugün sipariş edilse çıkacak listedir: omega ve aşık yok; tavan ve çatı paneli, saçak altı ve saçak yüzü Boardex'i var. Gerçek listede olmayan 5 satırı var. Çelik: gerçek liste 1 937 kg, B 1 937 kg, A 2 588 kg.
- **Okuma.** Aynı satır sayısı kuralların o listeye benzerliğini gösterir, doğruluğunu değil: kararların bir kısmı o listeyi düzeltiyor (Boardex kalınlığı, çatı şiltesi, duvar izolasyonu, vida katsayıları).
- **Kural setleri.** 03:46 kıyası 0.12 setiyle, kararlardan sonraki tablo güncel setle üretilir; ikisi de yeniden üretilebilir. Yeni davranışlar kuraldaki anahtarlara bağlı: bugünkü kod 0.12 setiyle 03:46 çıktılarını bayt bayt aynı veriyor.
- **Liste öncesi kararların son durumu.** Orta inişin eşiği: öneri 9 m dere boyu; 5 köşe + 2 orta = 7 iniş (pafta ve liste 7). Kablo mesafesi: sigortadan (10,06 m; NYM 137 ve 115 m, listede elle 140 ve 120). Mastik: pencere başına 1, 7 adet (listede 3; karar farkı). Ölçü: kaplanmış yüz (bizdeki). Duvar dibi: damlalık listeden çıkık; o kenara ne konacağı soru. Müştemilat: Lokman "göz ardı et" dedi; mevcut hesap duruyor.

## 8 Ekim 00:45 cevaplarından sonra (kural seti 0.14)

Lokman, 7 Ekim'de açık kalan dokuz soruyu 8 Ekim 00:45'te cevapladı (cevaplar ve uygulanışı: `docs/sartname/yukleme_listesi_yontemi.md`). KT-01 güncel setle yeniden hesaplandı; `sonuc/KT01_kararlar_*` dosyaları bu durumu gösterir.

- **Aynı satır sayısı değişmedi:** B 63 / 98, A 60 / 98. Yeni tutan 15 satır aynı (10'u kararlardan, 5'i pafta sayımından); önce tutan hiçbir satır bozulmadı.
- **B'de farklı kalan 35 satırın türü:** karar 14 (önce 12), yöntem 3, elle 16, ölçü 2, soru 0 (önce 2). İki soru satırı, gerçek listedeki iki damlalık satırıydı (bina ve müştemilat); ikisi de karar farkı oldu. Mastik 7 Ekim'de de karar farkıydı; yalnız adedi değişti:
  - *Damlalık (bina ve müştemilat).* Çatının duvara dayandığı kenara özel mahya konur: 11,35 m ÷ (2,8 − 0,20) → 5 adet, L 2800. Geçici "duvar dibi sacı" satırı kalktı; adet aynı. Gerçek listede o kenarda damlalık var (3 + 3 = 6); bizim listemizde damlalık yok (Lokman çıkardı). Adet mahyadaki gibi toplam boydan hesaplanıyor (Claude'un uygulaması; soruldu): her yapının kenarı ayrı yuvarlansa 3 + 3 = 6 olurdu. Özel mahya mahya bandına sayılmıyor (3 rulo; listede damlalıkla 4) ve satıra renk yazılmıyor: ikisi de soruldu.
  - *Silikonize mastik.* Pencereler alıcıya aitse mastik yazılmaz: bizim listemizde satır yok (7 Ekim'de 7 adetti). Gerçek listede 3.
- **03:46'ya göre adedi değişen satır 20** (14'ü kararlarla, 6'sı pafta sayımıyla). 7 Ekim'de 21'di: mastik satırı yeniden 03:46'daki gibi yok.
- **Onaylananlar; adet değişmedi:** iniş eşiği 9 m dere boyu (7 iniş; pafta ve liste 7); sandviç panel kapamasının hesabı (14; listede L 2800 ile 12); sigorta kutusunun yeri (giriş).
- **A listesi.** Gerçek listede olmayan satır 6 oldu (önce 5). Kalkan kenarının Boardex'i onaylandı (4 levha; durumu `lokman`). Yeni satır "Kalkan kenarı üst kapaması" adetsiz ve `soru` durumunda: ölçüsü ana çatının kalkan kenarlarının boyu (20,97 m; çatı panelli müştemilatın 6,74 m'lik alınları hariç); hangi malzeme olduğu soruldu. Notundaki "alın sacının ölçüsüyle 10 adet ederdi" yalnız bilgidir. Levha satırları listede üreticinin adıyla yazılıyor.
- **Trapez vida (5,5 × 25).** Davranış değişmedi (B 1000, A 1250; listede 1800); parça C profillerin sayımı örnekle yeniden soruldu.
- **Çelik.** Değişmedi: gerçek liste 1 937 kg, B 1 937 kg, A 2 588 kg.
- **Çizimler.** Plan, pafta ve dört görünüş iki yöntemde de 7 Ekim'dekilerle bayt bayt aynı; çizim betiklerine dokunulmadı.
- **Değişmezler.** Bugünkü kod 0.12 setiyle 7 Ekim 03:46 çıktılarını (kıyas tabloları ve çizimler dahil; `kiyas_kos.sh`), 0.13 setiyle 7 Ekim 10:55 çıktılarını (`kararlar_kos.sh <tanım> <python> 0.13`) bayt bayt aynı veriyor (`../2026-10-03_yukleme/kural_setleri/`, `kararlar_notlari_setleri/`).
- **Denetim (8 Ekim).** Cevaplarla ilgili satırlar (iniş, kapama, özel mahya, kalkan kenarı, mastik, trapez vida, yazılan adlar) hesap koduna bakmayan ayrı bir oturumda yeniden hesaplandı: A ve B listelerinde hepsi aynı. Kod ayrı bir oturumda incelendi; bulguları işlendi (ayrıntı: `docs/sartname/yukleme_listesi_yontemi.md`, "Denetim (8 Ekim)").
- **Liste öncesi kararların son durumu (8 Ekim).** Orta inişin eşiği: onaylandı. Kablo mesafesi: sigortadan; kutu girişte (onaylandı). Mastik: pencereler alıcıya ait, yazılmaz. Duvar dibi: özel mahya. Ölçü: kaplanmış yüz. Kalkan kenarı: Boardex; üstüne gelecek malzeme soru.

## 8 Ekim 07:23 cevaplarından sonra (kural seti 0.15)

Lokman 00:45'ten sonra açık kalan üç soruyu 07:23'te cevapladı; 1. cevabın okunuşunu 07:41'de onayladı ("evet 1. cevabı doğru anlamışsın"). Cevaplar ve uygulanışı: `docs/sartname/yukleme_listesi_yontemi.md`, "Lokman'ın cevapları (8 Ekim 07:23 ve 07:41)". Bu projede değişenler (`sonuc/KT01_kararlar_*`):

- **Kalkan kenarı** ("Alın kapama saçak değil sadece makasın eğimli kenarı kadar kapanıyor 4 omuz veya kırma çatılarda yok"). Çelik standardı listesinde adetsiz "kalkan kenarı üst kapaması" satırının yerine **alın kapama** geldi: boyu makasın eğimli kenarı kadar (20,97 m; çatı panelli müştemilatın alınları hariç), parça L 2500, 20 cm bindirme → 10 adet, saçak ve alın renginde (antrasit gri). Kalkan kenarının Boardex'i saçak gibi değil, yalnız makasın eğimli kenarının yüzü: 4 → 2 levha.
- **Trapez vida (5,5 × 25)** ("C profiller hiç önemli değil öylesine gönderiyoruz göz ardı et"). Parça C profiller sayılmıyor: B 922 → 862 vida, A 1092 → 1032; pakete yuvarlanınca adet değişmedi (B 1000, A 1250; gerçek listede 1800).
- **Özel mahya** ("Özel mahya çok nadir kullanılıyor sadece bina yanında ek veranda varsa (yani tasarıma bağlı) veya müştemilat gibi ek bir çıkıntı yada bazı cumbalı çatılarda (çatı içinden küçük bir çatı daha çıkıyor) varsa kullanılır mahya bandıyla alakası yok"). Kural değişmedi: çatının duvara dayandığı kenarlar bu projede veranda sundurması ve müştemilattan doğuyor; 5 adet. Mahya bandına girmiyor (3 rulo).
- **Gerçek listeyle aynı satır:** değişmedi: B 63 / 98, A 60 / 98; farklı kalan 35 satırın türleri aynı (karar 14, yöntem 3, elle 16, ölçü 2). A listesinde gerçek listede olmayan satır yine 6; alın kapama artık adetli.
- **Değişmezler.** Bugünkü kod 0.12, 0.13 ve 0.14 setleriyle kendi günlerindeki çıktıları bayt bayt aynı veriyor (`kararlar_kos.sh tanim/KT01_duzeltilmis.json <python> 0.14` 8 Ekim 03:13 tablosunu üretir; açıklamaları `kararlar_notlari_setleri/0.14.json`da).
- **Tanım ve çizimler depoda** (Lokman, 8 Ekim 07:23: "Evet ekle"): `tanim/KT01.json` (kör liste bununla çıkarıldı), `tanim/KT01_duzeltilmis.json` (kıyastan sonra düzeltilmiş), ikisini üreten betikler (`kt01_tanim_uret.py`, `kt01_tanim_duzeltilmis.py`) ve SKP'den okunan profil boyları (`KT01_profil_boylari.json`); iki tanım betiklerden bayt bayt aynı yeniden üretiliyor. Çizim seti iki yöntemle `cizimler/KT01_B` (yapıldığı gibi) ve `cizimler/KT01_A` (çelik standardı) altında: plan, dört görünüş, pafta, IFC4, dört perspektif, çatısız ve makaslı görünüm. Plan, görünüşler, pafta, çatısız görünüm ve arka perspektifler her üretimde bayt bayt aynı; IFC'de kimlikler ve zaman damgası her üretimde değişir (içerik aynı), ön perspektiflerde ve makaslı görünümde üst üste binen yüzlerin çizim sırası yüzünden pikselin binde üçünden azı değişebilir.

## 10 Ekim cevaplarından sonra (kural seti 0.18)

Lokman, KT-03'ün sorularına 10 Ekim 10:18'de verdiği cevaplarla tek eğimli çatı panelli çatıların nasıl bittiğini beş fotoğrafla gösterdi (10:29); müştemilat için 10:39: "hayır istediğim o 5 görseldeki gibi olması çok güzel duruyor". Bu projede değişenler (`sonuc/KT01_kararlar_*`):

- **Müştemilatın panel çatısı** beş fotoğraftaki gibi: saçakta dere (dere 7 → 8, dere kapağı 4 → 6, dere kelepçesi 56 → 64, iniş 7 → 9 ve ona bağlı dört satır) ve özel büküm saçak sacı (3, yeni satır); eğik kenarlarda sundurma kapama (3, yeni satır). Müştemilatın Boardex şeridinden yalnız alt payı kalır (12,20 m × 0,15 m; 11 → 10 levha); yüzü kapamayla kapanır (okuma; Lokman, 10 Ekim 11:39: "evet doğru anladın").
- **Gerçek listeyle aynı satır:** B 63 → 55 / 98, A 60 → 52 / 98. KT-01'in gerçek listesinde ve dere paftasında müştemilatta dere yok: dere, dere kapağı, dere kelepçesi ve beş iniş satırı karar farkı olarak yazıldı (`kararlar_notlari.json`). 03:46'da tutup bozulan satır 3 (dere, kapak, kelepçe). Yeni iki satır gerçek listede yok; nedenleri `kararlar_notlari.json`ın `listede_olmayan` alanında, `kararlar_kiyas.py` denetler.
- **Çizimler.** Planın ve paftanın yeni hali `cizimler/KT01_{A,B}/` altında: çatı planında müştemilatın saçağında iki iniş daha (9); dış kaplama satırında "çatı panelinin saçak ve alın altı". Öteki çizimler içerikçe aynı (IFC'de kimlik ve zaman, geometri özetinde sıra, makaslı görünümde ve perspektiflerde görüntü işleme gürültüsü hariç).
- **Değişmezler.** Bugünkü kod 0.12–0.17 setleriyle kendi günlerinin çıktılarını bayt bayt aynı veriyor (`kararlar_kos.sh tanim/KT01_duzeltilmis.json <python> 0.17` 10 Ekim 10:47 tablosunu üretir; açıklamaları `kararlar_notlari_setleri/0.17.json`da); 0.12 ve 0.17 ile planı, paftayı ve görünüşleri de.

**Kural seti 0.19 (10 Ekim 11:39):** kısa derede tek iniş ve alçak çatı köşesinin ayrımı (yalnız tek inişli küçük çatıda iniş yok). Bu projede böyle bir hat ya da köşe yok: listeler ve çizimler aynı, yalnız iniş satırının notu değişti. `kararlar_kos.sh tanim/KT01_duzeltilmis.json <python> 0.18` 11:21 tablosunu üretir (açıklamaları `kararlar_notlari_setleri/0.18.json`da).

**Çatısız veranda (10 Ekim 2026; ilk örnek katalog modeli Ç8801, `../2026-10-10_c8801/`):** tanımda verandanın örtüsü yazılabilir (`ortu`: `cati`, `pergola` ya da `acik`; yazılmamışsa çatının altında; `yapi.py`). Çatısız verandanın tavanı yoktur: `girdi_genel.py` veranda tavanını, tavan panelini, köşebentteki veranda çevresini, tavan omegasını ve şilteyi onsuz hesaplar, çatı çeliğinin oturumundan düşer (bina alanına girer); `ifc_genel.py` tavan koymaz; `yukleme.py` yeşil tavan satırının formülünü ve notunu buna göre yazar. Kural değil, modelin anlatılabilmesi için. Alan yoksa hesap öncekiyle aynı (eski bütün çıktılar bayt bayt aynı). Pafta bilgi satırı, tanımda çatı kaplaması yazmıyorsa kural kitabındaki baz paket kaplamasını yazar (önceden "—"; eski tanımların hepsinde kaplama yazılı).

## Sağlama

- `saglama.py`: Ç8201 genel hattan geçirildi; mahal alanı, çevresi, köşeleri, boşlukları, dış çevre, iç duvar boyu, çatı ölçüleri, OSB takviyesi ve iki yükleme listesinin (baz ve sandviç panel) bütün satırları 0.4 hattıyla aynı. Genel dizilim 840 kırma çatı denemesinde eski dizilimle aynı adedi verdi. Bu sağlama, KT-01 listesi dondurulmadan önce genel motorda üç hata buldurdu (köşe payının yazıldığı duvar, iç duvar boyunun ölçüsü, L birleşimde duvar yüzü); düzeltildi.
- `saglama.py` panel boyu kuralını (10 mm'ye yukarı yuvarlama, uzatma, pay koşulu) iki motorda karşılaştırır: genel motorun seçtiği boy, adet ve uzatmanın nedeni, rastgele 150 kırma çatı ve kaplamada kırma motorununkiyle aynı (7 Ekim). İki motor ölçütü ayrı ayrı kurar; 7 Ekim incelemesi ikisinin ayrıştığını bulmuştu, eşitlendi.
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

Depodaki dosyalarda müşteri, bayi ve çalışan adı, telefon ve fiyat yok. Kaynak dosyalar (DWG, SKP, liste) depoya alınmadı. Gerçek listenin dökümü (`sonuc/KT01_gercek_liste.json`) kalem, boyut, adet, ağırlık, hücre formülü ve açıklama sütunlarını içerir; ad, iletişim ve hazırlayan satırları alınmadı, dosya adının başı maskelendi. Tanımlar (`tanim/`) müşteri projesinin geometrisidir; Lokman'ın onayıyla depoda (8 Ekim 2026); ad, telefon ve fiyat içermez.
