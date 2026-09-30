# Model ve kabul durumu

| Model / revizyon | Yapılan | Açık durum |
|---|---|---|
| P9201 · SKP-inceleme-01 | Kaynak SKP → HTML/Blender/PNG/geometrik IFC4; aktarım kontrolü geçti | Plan/üretim kabulü yok. Eski motor r01 düzeltmesi yapılmadı. |
| P9401 · SKP-inceleme-01 | SKP'deki soldaki yapı kopyası → aynı teslimler | Kopya seçimi, JPG/SKP revizyon uyumu, kaynak/üretim kabulü bekliyor. |
| P9501 · SKP-inceleme-01 | SKP → aynı teslimler; shear ve homojen dönüşüm düzeltildi | Çatı/veranda ve kaynak revizyon farkı açık; eski motor r01 açıklıkları eksik. |
| P9401 · CATI-A-01 | Kaynak beşik + veranda beşik kolu, nötr karşılaştırma | Kaynak çatı; katalog uyumu ve kabul açık. |
| P9401 · CATI-B-01 | Sade kırma önerisi | Lokman seçmedi. Çatı/taşıyıcı/drenaj teknik tasarımı yapılmadı. |
| P9401 · CATI-C-01 | Tek eğim ve yeni üst kapamalar | Lokman seçmedi. Yeni ölçüler öneri; teknik tasarım açık. |
| P9401 · CATI-D-01 | Parapetli yatay görünüş önerisi | Lokman seçmedi. İç eğim/drenaj/katman çözümü yok. |

Çatı revizyonlarının tam kimliği `P9401-CATI-A-01` … `P9401-CATI-D-01`. Üç model sunumu için kimlik `SKP-inceleme-01`; motor r01/r02 numarasıyla karıştırılmamalı.

## Kaynak–eski motor farklarının ilk kontrolü

- **P9201:** JPG yaşam 32,7 / r01 27,552; hol 1,5 / 6,599; veranda JPG 15,7, eski DXF çıkarım etiketi 16,5, r01 18,900 m². Kaynak 6 pencere/5 kapı; adetler aynı olsa da konum farkları var. Ayrıntılı F01–F08 kaydı `durum/P9201_Ilk_Is_Emri.md` içinde.
- **P9401:** JPG veranda 12,0 / r01 7,875 m². Verandanın yaklaşık 62 cm öne taşan kısmı eski çıkarımda kesilmiş. Kaynak 7 pencere/5 kapı; pencere/kapı merkez kaymaları ve 1 cm ölçü zinciri yuvarlama farkları açık.
- **P9501:** JPG 9 pencere parçası / 7 kapı; r01 5 pencere / 3 kapı. Cumba üç parça tek takım sayılırsa kaynak 7 pencere takımıdır. JPG'de ayrı çamaşır mahalli yok, DXF çıkarımında var. Sağ veranda çıkması eski çıkarımda kesilmiş. SKP çatı/veranda biçimi de katalogdan farklı.

Alan etiketlerinin toplamı katalog başlığının net/brüt anlamını tek başına çözmez. Bu farkların hepsi “çizim hatası” diye kapatılmadı; kaynak revizyonu/ölçü anlamı kararları ayrı tutulacak.

## Kontrolün doğruladığı ve doğrulamadığı

- Üç IFC4 şema/geometri kontrolünden geçti; kaydedilen koordinatlar ve üçgen bağlantıları seçili aktarım verisiyle eşleşti.
- Üç son Blender dosyası kaynak dünya köşeleriyle karşılaştırıldı; ölçülen sayısal farklar raporlarda.
- P9401 çatı seçeneklerinde kaynak gövde değiştirilmedi; yeni çatı/kapama/parapet parçaları öneri olarak etiketli.
- Çevrimdışı HTML açılışı, model/seçenek değiştirme, çatı açma/kaldırma, animasyon ve mobil genişlik kontrolleri yapıldı.
- Bu sonuçlar JPG/DWG kaynak sadakati, gerçek açıklık boşluğu semantiği, katı cisim/taşıyıcı doğruluğu, BOM veya üretim kabulü değildir.
- IFC, kaynak kimlikli `IfcBuildingElementProxy` geometri taşır. Ön yüz malzemeleri aktarılmıştır; arka yüz malzemeleri ayrıca temsil edilmiyor. Nötr renk paleti sunum tercihidir.

Kabul: **Lokman görsel kabulü bekliyor; teknik üretim kabulü yok; Claude entegrasyonu yapılmadı; canlı değişiklik yok.**
