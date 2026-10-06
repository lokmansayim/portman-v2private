# 6 Ekim 2026 · kör test (KT-01) ve genel model motoru

Deneme kodu; canlıda değil, Motor'un yerine geçmez. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı.

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
| `sonuc/` | KT-01'in metraj girdisi, listesi ve dondurma kaydı (ad ve fiyat yok) |

Hesap `../2026-10-03_yukleme/yukleme.py`'de kaldı; genel model için eklenen alanlar geriye dönük uyumlu (eski girdilerin çıktıları bayt bayt aynı). Yeni varsayımlar `kurallar.json`'da (`cok_duzlemli_cati`, `duvar_dibi`, `ek_yapi_ve_korkuluk`, `kapsam_alici`, `nem_bariyeri_dis_cephe`, `elektrik_oda_ek`).

## Çalıştırma

```
python yapi.py tanim.json                       # mahaller ve yüzler
python girdi_genel.py tanim.json --cikti sonuc  # metraj girdisi
python ../2026-10-03_yukleme/yukleme.py sonuc/KT01_girdi.json --cikti sonuc/KT01_yukleme.json --md sonuc/KT01_yukleme.md
python ciz_genel.py tanim.json --cikti cikti    # plan, pafta, görünüşler
python ifc_genel.py tanim.json cikti/KT01.ifc   # IFC4 + şema doğrulaması
python perspektif.py cikti/KT01.ifc cikti KT01  # perspektifler
python saglama.py                               # genel motorun sağlaması (yaklaşık bir dakika)
```

KT-01'in tanımı (`KT01.json`) ve ondan üretilen çizimler depoda değil: müşteri projesinin geometrisi, İE-05 gereği ayrı onayla eklenir. Çizimler, IFC ve perspektifler Lokman'a dosya olarak verildi.

## Kör test protokolü

1. Klasördeki gerçek liste ve Excel hesaplama motoru, kendi listemiz üretilip depoya kaydedilene kadar açılmadı (yalnız dosya boyutu ve özeti alındı; `sonuc/KT01_dondurma.md`).
2. Girdi yalnız DWG'deki zemin kat planı, teknik özellikler ve açıklama notları ile SKP karkas modelinden okundu. Montaj paftalarındaki adetler (kaplama, omega, aşık, iniş) girdi olarak kullanılmadı.
3. Kuralların kapsamadığı her yerde karar listeden önce verildi ve yazıldı (aşağıda).
4. Kıyasta her fark sınıflanır: girdi hatası · kural hatası · karar farkı (bugünkü kural o günkü uygulamadan farklı) · listenin elle yuvarlaması. Yalnız ilk ikisi hata sayılır.

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

## Sağlama

- `saglama.py`: Ç8201 genel hattan geçirildi; mahal alanı, çevresi, köşeleri, boşlukları, dış çevre, iç duvar boyu, çatı ölçüleri, OSB takviyesi ve iki yükleme listesinin (baz ve sandviç panel) bütün satırları 0.4 hattıyla aynı. Genel dizilim 840 kırma çatı denemesinde eski dizilimle aynı adedi verdi. Bu sağlama, KT-01 listesi dondurulmadan önce genel motorda üç hata buldurdu (köşe payının yazıldığı duvar, iç duvar boyunun ölçüsü, L birleşimde duvar yüzü); düzeltildi.
- KT-01 tanımı: mahallerin karkas yüzleri arası alanları DWG'deki etiketlerle karşılaştırıldı (10,86 / 10,80 · 4,00 / 3,90 · 12,99 / 13,00 · 36,27 / 36,35 · 15,65 / 15,90); oturum 98,66 m² (çizimde 98,65); çatı yüzleri SKP'deki yüzlerle aynı alanda (41,64 · 37,70 · 14,63 · 18,40 m²).
- IFC4: şema hatası 0.

## Sınırlar

- Yalnız eksenlere paralel duvarlar. Çatı düzlemleri tanımda elle verilir (modeldeki yüzlerden); düzlemlerin kesişimi koddan çıkarılmaz.
- SKP ve DWG'den tanıma geçiş elle yapıldı (ölçüler betiklerle okundu); otomatik çıkarıcı yok.
- Çok düzlemli çatıda panel boyu uzatma kuralı denenir; kesim planı çizimi henüz yalnız kırma çatıda var.
- Görünüşler yüzeylerin uzaktan yakına boyanmasıyla çizilir; iç içe geçen yüzeylerde hata verebilir.

## Kişisel veri

Depodaki dosyalarda müşteri, bayi ve çalışan adı, telefon ve fiyat yok. Kaynak dosyalar (DWG, SKP, liste) depoya alınmadı.
