# Modeller (Yapı Tanımı 0.5) · İE-08

Genel motorun (`motor/genel/`) çizdiği modellerin tanımları. Her dosya bir modeldir (şema `portman.yapi_tanimi/0.5-taslak`): duvarlar
(cm, serbest aks), mahaller, açıklıklar, çatı düzlemleri. Kurallar `kurallar/`dadır; aynı kural kitabı hangi tanıma uygulanırsa o modelin
çizim seti ve yükleme listesi çıkar (`python -m motor.genel.uret modeller/<KOD>.json <çıktı>`). Bu klasör sürümle sunucuya gider.
Model bankası (Postgres, panel, sürüm ve satış kaydı) ayrı iştir (İE-09); o gelene kadar kayıt bu klasör ve `beyin/veri/adaylar.json`'dur.

Dosyalar ie-05 ve deneme klasörlerindeki tanımların **bayt bayt kopyasıdır** (12 Ekim 2026); kaynağı ve doğrulama durumu (D-07):

| Dosya | Kod | Ne | Kaynak (tanımın `kaynak` alanı ayrıntılı) | Doğrulama | Aslı |
|---|---|---|---|---|---|
| `C8201.json` | Ç8201 | Katalog, tek kat çelik, 2+1, 82 m² | Arşiv DWG planı; İE-05'in ilk modeli; 0.5 sürümü (0.4'ten çevrildi, `saglama` ile aynı metraj) | Çizim setiyle doğrulandı (İE-05; D-07'de `cizim_seti`) | `deneme/2026-10-06_kor_test/C8201_05.json` |
| `C8801.json` | Ç8801 | Katalog, tek kat çelik, 2+1, 88 m²; **katalog çatısı** (Lokman 10 Ekim 14:46: "2. versiyon") | Arşiv DWG planı ve katalog paftası; çatı katalog görsellerinden, Lokman'ın 13:33 düzeltmesiyle | Çizim seti 12/12, IFC şema hatası 0; Lokman çatıyı onayladı | `deneme/2026-10-10_c8801/tanim/C8801.json` |
| `C8801K.json` | Ç8801-K | Aynı planın çatı varyantı K (doğu ucu kırma) | Lokman 14:46: "çatı olarak 3'ü de olur"; 1. versiyon | Çizim seti 12/12 | `deneme/2026-10-10_c8801/tanim/C8801K.json` |
| `C8801L.json` | Ç8801-L | Aynı planın çatı varyantı L (kanadın mahyası boydan boya) | İlk okuma; Lokman: üçü de olur | Çizim seti 12/12 | `deneme/2026-10-10_c8801/tanim/C8801L.json` |
| `KT01.json` | KT-01 | Müşteri projesi (kör test 1), tek kat çelik, 98,7 m², beşik + cumba, müştemilatlı | DWG ve SKP'den; kıyastan sonra **düzeltilmiş** tanım (`duzeltmeler` alanı, 7 düzeltme) | Çizim seti 12/12; gerçek yükleme listesiyle kıyaslandı (`docs/raporlar/2026-10-07_Kor_Test_KT01.md`) | `deneme/2026-10-06_kor_test/tanim/KT01_duzeltilmis.json` |
| `KT02.json` | KT-02 | Müşteri projesi (kör test 2), 90 m², dört omuz, korkuluklu veranda, sundurma | Montaj paftası ve üretim dosyasından; düzeltilmiş tanım (1 düzeltme) | Çizim seti 12/12; gerçek listeyle kıyas (`2026-10-09_Kor_Test_KT02.md`) | `deneme/2026-10-09_kor_test_2/tanim/KT02_duzeltilmis.json` |
| `KT03.json` | KT-03 | Müşteri projesi (kör test 3), 80 m², kanatlı kırma, panel çatılı veranda ve sundurma, iki baca | Montaj paftasından (üretim dosyası yok); düzeltilmiş tanım (2 düzeltme) | Çizim seti 12/12; gerçek listeyle kıyas (`2026-10-10_Kor_Test_KT03.md`) | `deneme/2026-10-09_kor_test_3/tanim/KT03_duzeltilmis.json` |

Kurallar:
- **Kör tanımlar** (`KT0x.json`, kıyastan önceki) ve A/B çizim setleri `deneme/` altında tarih kaydı olarak durur; canlıya düzeltilmiş tanım ve **yöntem A** (çatı ve tavan paneli; çelik standardı, Lokman 7 Ekim 07:45) gider. B (omega ve aşık; yapıldığı gibi) yalnız kıyas ve altın test içindir.
- KT projeleri müşteri projesidir: bayiye **adsız** sunulur (kod, m², oda programı); kaynak dosyalar (DWG, SKP, gerçek liste) depoda yoktur.
- Varyant kodları tiresiz anılır (`Ç8801K`, `Ç8801L`; katalog kod kalıbı `[PÇ]\d{4}[A-Z]?`); bayiye "Ç8801-K" diye gösterilir.
- Bir tanım değişirse yeni dosya ya da sürüm eklenir; altın testler (`testler/referans/`, `genel_parmak_izleri.txt`) referansı D-02 kuralıyla yeniden dondurulur.
