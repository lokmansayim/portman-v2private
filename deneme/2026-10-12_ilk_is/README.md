# İlk gerçek iş · T1012-CV · 12 Ekim 2026

**Milat.** Bu, Portman'ın ilk gerçek işidir. Lokman, 12 Ekim 2026 15:30: "Portman ilk işini aldı bunu milad olarak kaydet".

Bir bayi 12:41'de talep gönderdi: tek katlı bir ev. Plan fotoğrafı 747 × 1012 (75,6 m²), imarlı oturum 76 m². Canlı Portman bu talebi alamıyordu, çünkü mod `kayitli` ve genel motor canlıda değil. Çizimi İE-05'in genel motoruyla Code yaptı, Lokman bayiye iletti. Canlıya dokunulmadı.

## Sonuç

- Tek kat çelik, 2+1.
- Çatı KT-01'in biçiminde: beşik + çift cumba. Cumbada 30 cm pencere çıkıntısı ve onun küçük üçgen çatısı var.
- 50 cm veranda; sağ ön köşede dikme.
- Oturum veranda dahil 74,11 m², 747 × 1012'nin içinde. Salon 35,6 m².
- Çizim setinde 12 çıktının 12'si üretildi, IFC4 şema hatası 0.

## Lokman'ın kararları (12 Ekim 2026)

| Saat | Karar |
|---|---|
| 12:49 | Yapı çelik |
| 13:05 | Çatı KT-01'inki |
| 13:17 | Seçenek 2: beşik + cumba |
| 13:49 | Çift cumba (öne 30 cm çıkıntı); pencerenin ortası cumba makasının ortasında; 1 m veranda |
| 14:05 | Pencerenin üstü çıkıntı gibi eğimli; salonda eğimli tavan |
| 14:06 | Cumba makası ile çıkıntı makası arası 30 cm |
| 14:07 | Verandadaki pencere çelik kapı ile sağ köşe arasında ortada; simetri kuralı (`kurallar/model/yerlesim.json`) |
| 14:19 | Pencere ile çıkıntı makası arası 30 cm; pencere görseldeki gibi |
| 14:31 | Görünüşlerdeki boşluklar giderilecek; kesit verilmeyecek |
| 14:46 | Cumba ve veranda saçağı aynı hatta; çıkıntı 30 cm önde, kendi saçağı 30 cm (`kurallar/model/yerlesim.json` › `sacak_hizasi`) |
| 15:10 | Dikme görünüşlerde çizilecek |
| 15:11 | Veranda 50 cm |
| 15:30 | Milat. Bu işin çizim kuralı ve şablonu kullanılabilir. Antet kalkar: sayfa başlığı, TASLAK satırı ve 6 Ekim "Örnek Şablon"unun antet kutusu (`kurallar/cizim/cizim_seti.json` › `antet`). |

## Teslim

Bayiye Lokman iletir.

- **`teslim/T1012CV_bayi.pdf`:** 3 sayfa, antetsiz.
  1. Sunum: plan, iki ön perspektif, ön ve sol görünüş, kısa not.
  2. Pafta.
  3. Dört perspektif.
- **`teslim/T1012CV_muhendis.zip`:** IFC4, yükleme listesi (PDF ve md), pafta, makaslı ve çatısız görünüm.
  - Liste bayiye gitmez (CIO kararı).
  - Kesit yok; istenirse çizilir.

## Dosyalar

| Yol | İçerik |
|---|---|
| `tanim/t1012_tanim_uret.py` | Yapı Tanımı üretici. Seçenek `--cati besik`, `cumba` ya da `cifte`; bu iş `cifte`. Ölçüler plan fotoğrafından perspektif düzeltmesiyle okundu (±5 cm) |
| `tanim/T1012CV.json` | Yapı Tanımı 0.5 |
| `motor_farki.patch` | Genel motorun (`deneme/2026-10-06_kor_test`) bu iş için genişletilmiş hali. Ayrıntısı aşağıda. Depodaki motor değişmedi; eklentiler İE-08'e taşınacak |
| `cizimler/T1012CV_A/` | Çizim seti (12 çıktı) |
| `sonuc/` | Liste girdisi ve yükleme listesi (json, md) |
| `teslim/` | Bayi PDF'i ve mühendis zip'i, gönderildiği gibi |
| `teslim_paketi.py` | Teslim paketlerini dizer |
| `yakin.py` | Yakın plan denetim görüntüsü: zemin pembe çizilir; boşluk varsa pembe görünür |

`motor_farki.patch` şu eklentileri içerir:
- eğimli pencere;
- eğimli tavan;
- kalkanda `ust_disarida` (duvara dayanan alçak çatının altındaki dolgu);
- alın bandı payı (3 mm; yüzler çakışınca perspektifte noktalı desen oluşuyordu);
- ölçü zinciri: örtülü kenarlar ve 1 cm'den yakın noktalar atılır, art arda kısa ölçüler iki yana yazılır;
- dikme yüzleri;
- antetsiz sayfalar.

## Yeniden üretme

Depo kökünden:

```bash
D=$PWD; K=$(mktemp -d); mkdir -p $K/deneme
cp -a deneme/2026-10-06_kor_test $K/deneme/
ln -s $D/kurallar $K/kurallar; ln -s $D/deneme/2026-10-03_yukleme $K/deneme/2026-10-03_yukleme
(cd $K && patch -p1 < $D/deneme/2026-10-12_ilk_is/motor_farki.patch)
python deneme/2026-10-12_ilk_is/tanim/t1012_tanim_uret.py $K/T1012CV.json --cati cifte
bash $K/deneme/2026-10-06_kor_test/cizim_seti_kos.sh $K/T1012CV.json $K/T1012CV_A python
```

**Kanıt:** Depodaki dosyalardan yeniden üretim 12 Ekim 2026'da denendi. Tanım, plan, pafta, görünüşler ve liste girdisi bayt bayt aynı çıktı.

## Açık konular

- Liste düz tavana göre. Eğimli tavanın taşıyıcısını ve malzemesini mühendis belirleyecek; statik proje de mühendisin.
- Salonla yatak odaları arasındaki duvarın 270 cm üstündeki üçgen IFC'de yok.
- IFC'de veranda tavanı yok; liste kuralında var (Boardex, saçağın ucuna kadar).
- Belediyedeki mimar DWG ya da DXF isteyebilir. Genel motor bunları üretmiyor.

Ad, telefon ve fiyat yok. Bayinin fotoğrafları ve mesajları depoya girmedi.
