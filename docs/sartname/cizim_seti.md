# Çizim seti standardı

Kaynak: Lokman, 7 Ekim 2026 07:45. "Çizimlerin bu halini çok beğendim burada kalalım sadece açıklamalar kısmını düzelteceğiz"; "çizimler persfektifler çok güzel olmuş bunları kurala ekle paftadaki açıklamaları düzelteceğiz". Onaylanan set, 6–7 Ekim kör testinde (KT-01) bir çelik projenin DWG ve SKP'sinden üretilen çizimlerdir (Lokman, 6 Ekim 21:22: "plan, görünüşler, IFC persfektifler şeklinde").

Standardın kendisi veridir: `deneme/2026-10-06_kor_test/cizim_seti.json`. Bu belge onu anlatır.

## Kural

- Model verilince set, tek bir Yapı Tanımı'ndan (0.5) aynı betiklerle üretilir. Çizimde LLM yoktur: aynı tanım aynı çizimi verir (K05). Plan, görünüşler, pafta, çatısız görünüm ve arka perspektifler her üretimde bayt bayt aynıdır. IFC'de kimlikler ve zaman damgası her üretimde değişir (içerik aynı); ön perspektiflerde ve makaslı görünümde üst üste binen yüzlerin çizim sırası yüzünden pikselin binde üçünden azı değişebilir.
- Setin biçimi (görünüşler, bakış açıları, renkler, ölçü zincirleri) Lokman'ın onayı olmadan değiştirilmez.
- Paftadaki açıklama satırları bu onayın dışındadır: Lokman'la birlikte düzeltilecek.
- Çizimlerdeki sayılar yükleme listesinin girdisiyle aynı hesaptan gelir: paftada yazan çatı yüzeyi, kaplama dizilimi ve iniş sayısı listedekilerle aynıdır.
- Çizimler taslaktır: her paftanın başlığında "TASLAK · üretim projesi değildir" yazar.

## Set

Tek komut: `bash deneme/2026-10-06_kor_test/cizim_seti_kos.sh <tanım.json> <çıktı klasörü> [python] [--yontem panel|omega_asik]`. Komut on iki çıktıyı üretir, hepsinin var olduğunu ve IFC'nin şema doğrulamasından hatasız geçtiğini denetler; eksik ya da hata varsa çıkış kodu 1.

| Çıktı | Dosya | Üzerinde ne var |
|---|---|---|
| Plan | `<kod>_plan.png` | Duvarlar (dış koyu, iç açık), mahal adı ve alanı (kaplanmış yüzler arası), pencere ve kapı etiketleri, kapı açılımları, veranda taraması, giriş oku, dıştan ölçü zincirleri (cm) |
| Dört görünüş | `<kod>_gorunusler.png` | Ön (giriş), arka, sol, sağ: duvarlar, doğramalar, çatı, baca; genişlik, duvar ve mahya yükseklikleri |
| Pafta | `<kod>_pafta.png` | Tek sayfa: başlık, plan, çatı planı, dört görünüş, altta iki sütun açıklama |
| IFC4 modeli | `<kod>.ifc`, `<kod>.ozet.json` | Duvar panelleri, boşluklar ve doğramalar, mahaller, tavan, çatı ve düzlemleri, makaslar (sadeleştirilmiş), veranda dikme ve kirişleri, baca; şema hatası 0 olmalı |
| Perspektifler | `<kod>_perspektif_on_sag.png`, `_on_sol`, `_arka_sol`, `_arka_sag` | IFC'den dört köşeden görüntü; kamera yükseklik açısı 24° |
| Çatısız görünüm | `<kod>_catisiz.png` | Çatı, tavan ve makaslar gizli; mahaller renkli ve etiketli |
| Makaslı görünüm | `<kod>_makasli.png` | Çatı kaplaması ve tavan gizli; makaslar görünür |
| Geometri denetimi | `<kod>_geometri.json` | IFC'den üçgenlenen nesne ve üçgen sayıları |

Çatı planında: düzlemler, eğim okları ve yüzdeleri, mahya, kırma ve vadi boyları, dere inişleri (sarı nokta), çatının bir duvara dayandığı kenar (turuncu), cephe çizgisi (kesik).

Betikler: `ciz_genel.py` (plan, görünüşler, pafta), `ifc_genel.py` (IFC ve şema doğrulaması), `perspektif.py` (IFC'den görüntüler; ekransız). Hepsi `deneme/2026-10-06_kor_test/` altında; deneme kodudur, canlıda değildir.

## Paftadaki açıklamalar (düzeltilecek)

Paftanın altında iki sütun var. Satırlar `girdi_genel.py`'deki `bilgi_satirlari`ndan gelir.

| Sütun | Satır | İçerik |
|---|---|---|
| Sol | Dış ölçü | En × boy (cm), oturum alanı |
| Sol | Mahaller | Mahal mahal alan (kaplanmış yüzler arası), veranda, kapalı net alan |
| Sol | Duvar | Karkas, dış ve iç kaplama kalınlığı, yükseklik, panel sayıları |
| Sol | Pencereler | Üst kot, iç ve dış kapı boşlukları |
| Sol | Dış kaplama (Boardex) | Duvar yüzleri − boşluklar + dikme, kiriş, kalkan ve baca; fire hariç levha |
| Sağ | Çatı | Tip, düzlem sayısı ve eğimleri |
| Sağ | Yöntem | Çatı yöntemi, kaplama, saçak, topuk |
| Sağ | Çatı yüzeyi | Yüzey ve plan alanı, mahya kotu |
| Sağ | Kenarlar | Saçak, mahya, kırma, vadi, alın, duvar dibi boyları |
| Sağ | Kaplama dizilimi | Panel boyları ve adetleri, kapatma genişliği |
| Sağ | Kalkanlar | Kalkan alanları |
| Sağ | Dere inişi | Adet ve kural; çizilmeyenler; birim |

Lokman hangi satırların nasıl düzeltileceğini söyleyecek (7 Ekim 07:45: "paftadaki açıklamaları düzelteceğiz"). 7 Ekim kararlarıyla kendiliğinden değişenler: yöntem satırı çelikte "A · çatı ve tavan paneli"; kaplama diziliminde boylar 10 mm'ye yukarı; dere inişinde kural "boyu 9 m'yi geçen dere hattının ortası" (eşik onaylandı: Lokman, 8 Ekim 00:45).

8 Ekim 00:45 cevaplarından sonra paftada yazanla listede yazan iki yerde ayrışıyor; ikisi de açıklamalar birlikte düzeltilirken ele alınacak (biçim onaylı olduğu için pafta metnine dokunulmadı):

- **"Dış kaplama (Boardex)" satırı.** Listede levha artık üreticinin adıyla yazılıyor (OUTWEAR Dış Cephe Levhası; "üreticide ne yazıyorsa onu yaz"). Paftada şirketteki ad duruyor.
- **"Duvar dibi" kenarı.** Çatının bir duvara dayandığı kenar (çatı planında turuncu) listede özel mahya olarak sayılıyor ("özel mahya"). Paftanın "Kenarlar" satırında ad "duvar dibi" olarak duruyor.

Paftanın kendisi bu cevaplarla değişmedi: 8 Ekim'de çizim betiklerinde çıktıyı değiştiren bir değişiklik yok (`girdi_genel.py`de yalnız bir yorum satırı); KT-01'in planı, paftası ve dört görünüşü iki yöntemde de güncel kural setiyle (0.14) yeniden üretildi ve 7 Ekim'dekilerle bayt bayt aynı çıktı.

## Denenenler

- KT-01 (98,65 m², beşik + cumba çatı, müştemilatlı): set 7 Ekim 03:46'da Lokman'a dosya olarak verildi; onaylanan çizimler bunlar. Tanımı ve çizimleri 8 Ekim 2026'dan beri depoda (Lokman, 07:23: "Evet ekle"): tanım `deneme/2026-10-06_kor_test/tanim/`, set iki yöntemle `deneme/2026-10-06_kor_test/cizimler/KT01_B` (yapıldığı gibi) ve `KT01_A` (çelik standardı).
- Ç8201 (82 m², kırma çatı): aynı komut `C8201_05.json` tanımıyla on iki çıktının on ikisini üretiyor; IFC4, şema hatası 0 (7 Ekim).

## Sınırlar

- Subasman ve merdiven çizilmez. Kat döşemesi ve çift kat kapsam dışı.
- Makaslar IFC'de sadeleştirilmiştir (alt başlık, üst başlıklar, dikmeler); karkas çizimi değildir.
- Montaj paftası seti (duvar panelleri, makas ve dere, çatı kaplaması yerleşimi, elektrik) ayrı iştir: yükleme listesinden sonra (`montaj_paftasi.md`).
- Çok küçük ölçü aralıklarında (30 cm ve altı) ölçü yazıları üst üste gelebiliyor; Ç8201'in planında görülüyor. Biçim onaylı olduğu için dokunulmadı; açıklamalar düzeltilirken sorulacak.
