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
- **`teslim/T1012CV_muhendis.zip`:** IFC4, DXF, yükleme listesi (PDF ve md), pafta, makaslı ve çatısız görünüm.
  - Liste bayiye gitmez (CIO kararı).
  - Kesit yok; istenirse çizilir.

## Dosyalar

| Yol | İçerik |
|---|---|
| `tanim/t1012_tanim_uret.py` | Yapı Tanımı üretici. Seçenek `--cati besik`, `cumba` ya da `cifte`; bu iş `cifte`. Ölçüler plan fotoğrafından perspektif düzeltmesiyle okundu (±5 cm) |
| `tanim/T1012CV.json` | Yapı Tanımı 0.5 |
| `motor_farki.patch` | Genel motorun (`deneme/2026-10-06_kor_test`) bu iş için genişletilmiş hali. Ayrıntısı aşağıda. Depodaki motor değişmedi; eklentiler İE-08'e taşınacak |
| `cizimler/T1012CV_A/` | Çizim seti (12 çıktı) ve DXF (`T1012CV.dxf`) |
| `sonuc/` | Liste girdisi ve yükleme listesi (json, md) |
| `teslim/` | Bayi PDF'i ve mühendis zip'i, gönderildiği gibi |
| `teslim_paketi.py` | Teslim paketlerini dizer |
| `yakin.py` | Yakın plan denetim görüntüsü: zemin pembe çizilir; boşluk varsa pembe görünür |
| `ie08/` | İE-08'e taşıma: PR #11'in `motor/genel/` paketine iki yama ve kanıt çıktıları (aşağıda) |

`motor_farki.patch` şu eklentileri içerir:
- eğimli pencere;
- eğimli tavan;
- kalkanda `ust_disarida` (duvara dayanan alçak çatının altındaki dolgu);
- alın bandı payı (3 mm; yüzler çakışınca perspektifte noktalı desen oluşuyordu);
- ölçü zinciri: örtülü kenarlar ve 1 cm'den yakın noktalar atılır, art arda kısa ölçüler iki yana yazılır;
- dikme yüzleri;
- antetsiz sayfalar;
- DXF (`dxf_genel.py`, yeni dosya).

**DXF.** Lokman 15:52'de sordu: "DXF üretimi P6001'de vardı, aynı şekilde çelik de üretebilir miyiz?" `dxf_genel.py` genel motorun modelinden DXF yazar.
- P6001'in kuralları: R2018, birim cm, `PORTMAN` yazı ve ölçü stili.
- Model alanında plan, çatı planı, dört görünüş ve açıklamalar; Türkçe katmanlar; ölçüler gerçek DXF ölçüsü.
- Görünüşlerde arkada kalan çizgiler atılır; yüz dolguları ayrı katmanda (`GORUNUS_DOLGU`) ve kapatılabilir.
- Dosya yazıldıktan sonra yeniden açılıp denetlenir: bu işte ve KT-01'de denetim hatası 0.
- P6001'deki pano blokları ve BOM verisi yok, çünkü çelikte duvar serbest akslı ve liste ayrı üretiliyor. Antet yok.

## Yeniden üretme

Depo kökünden:

```bash
D=$PWD; K=$(mktemp -d); mkdir -p $K/deneme
cp -a deneme/2026-10-06_kor_test $K/deneme/
ln -s $D/kurallar $K/kurallar; ln -s $D/deneme/2026-10-03_yukleme $K/deneme/2026-10-03_yukleme
(cd $K && patch -p1 < $D/deneme/2026-10-12_ilk_is/motor_farki.patch)
python deneme/2026-10-12_ilk_is/tanim/t1012_tanim_uret.py $K/T1012CV.json --cati cifte
bash $K/deneme/2026-10-06_kor_test/cizim_seti_kos.sh $K/T1012CV.json $K/T1012CV_A python
(cd $K/deneme/2026-10-06_kor_test && python dxf_genel.py $K/T1012CV.json $K/T1012CV_A/T1012CV.dxf)
```

**Kanıt:** Depodaki dosyalardan yeniden üretim 12 Ekim 2026'da denendi. Tanım, plan, pafta, görünüşler ve liste girdisi bayt bayt aynı çıktı. DXF'in varlıkları da aynı çıktı; başlıktaki tarih her üretimde değişir.

## İE-08'e taşıma: DXF bozulmadan

Lokman, 12 Ekim 16:37: "DXF üretimi varsa hiç bozmayalım". İE-08'in PR #11'i (`claude/trusting-ramanujan-6hmgdf`, uç `8717793`) genel motoru `motor/genel/` paketine taşıyor. Bu işin eklentileri o pakete `ie08/` altındaki iki yamayla geçer. İkisi de PR #11'in ucuna kaymadan uygulanır (depo kökünden `patch -p1`).

| Yama | İçerik | Var olan çıktılara etkisi |
|---|---|---|
| `ie08_dxf.patch` | `motor/genel/dxf_genel.py`; yeni dosya, göreli içe aktarma. Kullanım: `python -m motor.genel.dxf_genel <tanım> <çıktı.dxf>` | Yok; başka modül onu çağırmıyor |
| `ie08_motor_eklentileri.patch` | `motor_farki.patch`'in öteki parçaları: eğimli pencere ve tavan, `ust_disarida`, alın payı, ölçü zinciri, dikme yüzleri, antetsiz sayfalar | Plan PNG'si (antet ve zincir) ile IFC izi (alın payı) değişir; liste aynı kalır. Referans kararla yeniden dondurulur (antet: Lokman, 15:30) |

Kanıt (12 Ekim 2026; çıktılar `ie08/kanit/` altında):
- **P6001, bu dalda:** `dogrula.py` (`de2ddca`): DXF 18/18 ve PDF 18/18 aynı; `motor_p6001` aynı (36 pano, 773 × 763); harness 22/22. Fark yalnız bilinen sır taramasında (`ie05_dogrula.txt`).
- **P6001, PR #11'de:** `motor/`, `kanal/` ve `beyin/` altında var olan hiçbir dosya değişmiyor; yalnız `motor/genel/` ekleniyor. P6001'in DXF izleri PR'ın yedi referans klasöründe, PDF izleri 2026-09-28b'den beri altısında aynı.
- **Yalnız `ie08_dxf.patch`:** `pytest testler/genel` 25/25 geçti. `vps/genel_dene.py` Ç8801 için "AYNI" dedi. Yedi modelin DXF'i yazıldı, denetim hatası 0 (`pr11_dxf_denetim.txt`).
  - PR'ın `dogrula.py`'si (tam koşu): P6001 DXF 18/18 ve PDF 18/18 aynı, genel motor izleri 151/151 aynı (`pr11_dogrula.txt`, `pr11_kontrol.txt`).
  - Bu çalışma alanının venv'i ie-05'in sabitleriyle kurulu (PyMuPDF 1.26.0); PR #11 sabitleri yükseltiyor (PyMuPDF 1.28.2, shapely 2.2.0). Bayi paftasının PDF izi PyMuPDF'in sözcük okumasına dayandığından 11 pafta PDF'i ilk koşuda "farklı" göründü. Saf PR #11 ağacı da aynı farkı verdi; aynı PDF'ler PR'ın PyMuPDF'iyle izlenince 11'i de referansla aynı çıktı.
- **İki yama birlikte:** T1012-CV'nin plan, görünüşler, pafta, IFC özeti, liste girdisi ve yükleme listesi teslim edilenlerle bayt bayt aynı; DXF içerik izi aynı. Ç8801'in altın değerinde plan PNG'si ve IFC izi değişir; bu beklenen.

**Canlı zincir.** `kanal/worker.py` Motor'un çıktısından `dxf` ve `dxf_sha256` okur (PR #11'de 342–343. satırlar); `kanal/depo.py` `dxf_sha256`'yı kaydeder. İE-08 Adım 10'da bu okuma `m.get` olacak. Genel motorun manifestinde DXF yoksa çelik işlerinde DXF kaydı boş kalır. DXF'in bozulmaması için genel motor da `dxf` ve `dxf_sha256` vermeli; `dxf_genel.py` bunu sağlar.

**Birleştirme.** Bu dal ile PR #11 birleşirken yalnız `DURUM.md` ve `kurallar/README.md` çakışıyor (`git merge-tree`); ikisi de belge.

## Açık konular

- Liste düz tavana göre. Eğimli tavanın taşıyıcısını ve malzemesini mühendis belirleyecek; statik proje de mühendisin.
- Salonla yatak odaları arasındaki duvarın 270 cm üstündeki üçgen IFC'de yok.
- IFC'de veranda tavanı yok; liste kuralında var (Boardex, saçağın ucuna kadar).
- DWG yok; DXF var (R2018). Daha eski bir AutoCAD sürümü gerekirse DXF o sürümde de yazılabilir.

Ad, telefon ve fiyat yok. Bayinin fotoğrafları ve mesajları depoya girmedi.
