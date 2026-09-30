# Kod haritası ve kullanım durumu

Bu kodlar yerel kaynak inceleme/sunum prototipidir; üretim Motor'una takılmaya hazır genel bir kütüphane değildir. Ana depo kodu kopyalanıp yeni motor kurulmadı. HTML/JS görüntüleyiciler `teslimler/` altında bağımsız kaynak kod olarak da mevcuttur.

## Mevcut veriyle kullanılabilen adımlar

| Kod | İşlev | Koşul |
|---|---|---|
| `kod_arsivi/skp_import/read_skp.py` | SketchUp C API ile yüz/mesh, grup, doku, kimlik ve dönüşüm okur | macOS SDK yolu mevcut olmalı. Matris w normalizasyonu son sürümde var. Yeni okuma eski ham matris kanıtını korumaz; eski veri üstüne yazma. |
| `prepare_viewer_data.py` | Üç modelin seçili geometri/çatı/peyzaj ayrımı, HTML payload | Seçim listeleri bu SKP SHA'larına ve sıra numaralarına özel. SKP değişince yeniden eşleştir. |
| `correct_blend_transforms.py` | Aynı kaynak mesh köşelerini yeniden yükler, tam dünya matrisini köşelere uygular; ardından finalizer çalışır | Normalize scene + aynı kaynak/topolojiye ait source.blend gerekir. Yeni kaynağa körlemesine uygulanmaz. |
| `finalize_blend.py` | Seçili yapı/çatı koleksiyonları, kaynak kimliği, animasyon, paketlenmiş .blend ve iki PNG | Girdi source.blend önceden düzeltilmiş olmalı. |
| `export_ifc.py` | Seçili geometriyi IFC4 proxy elemanlar ve kaynak özellikleriyle yazar; yeniden açıp kontrol eder | Normalize selected.json. Semantik pano/duvar BIM üreticisi değildir. |
| `verify_saved.py` | IFC'de saklanan koordinat ve üçgen bağlantılarını girdiye karşılaştırır | Tanılama raporudur; başarısızlık koşullarını ayrıca kontrol et. |
| `kod_arsivi/p9401_cati/create_variants.py` | P9401 A/B/C/D verileri ve tasarım kaydı | P9401’e özel sabit kaynak sınırları ve öneri değerleri içerir. |
| `render_variants.py` | Mevcut P9401 gövdesi üzerine ayrı öneri parçaları; nötr görünüş, .blend, PNG, gövde kontrolü | Düzeltilmiş kaynak P9401_inceleme.blend gerekir. Shader node.type kullanır. |
| `export_variants.py` | Dört tam model için IFC çıkarımı | export_ifc.py'nin metnine birebir replace yapar. İki dosya birlikte sabitlenmiştir; üretim entegrasyonunda açık parametreli fonksiyona çevrilmeli. |
| `verify_ifc.py` | Dört varyantın saklanan IFC geometri kontrolü | Rapor alanlarını ayrıca başarısızlık kapısı olarak değerlendir. |
| `contact.py` | Dört çıktı PNG'sinden karşılaştırma paftası | Pillow ve yerel font yolu gerekir; geometrik model üretmez. |
| `kod_arsivi/roof_qa/verify_world.py` | Kayıtlı Blender dünya köşelerini kaynakla karşılaştırır | Test toleransı üretim toleransı değildir. |

İlk tablodaki kısa dosya adlarının klasörü `kod_arsivi/skp_import/`; diğerleri açık belirtilmiştir.

## Tarihsel / doğrudan çalıştırılmaması gereken betikler

- **make_blend.py:** Eski başlangıç betiği. `ob.matrix_world=m` shear dönüşümünü bozabilir; İngilizce node adlarına bağlıdır. Devirde aynı kaynak için mevcut düzeltilmiş source.blend esas alınır. Sıfırdan okuyucu zinciri entegrasyonunda dünya koordinatlarını mesh'e uygulayan yol ve node.type erişimiyle düzeltilmeden kullanma.
- **normalize_world.py:** Bir defalık veri ve okuyucu kodu göçü; betik koduna metin yaması da yapar. Normal üretim sırasına koyma.
- **prepare_delivery.py:** O oturuma özel belge/HTML yaması. Yeniden çalıştırılması eski metinleri geri getirebilir; tekrar üretim adımı değildir.
- **cut_preview.py:** Geçici kesit denemesi; teslim üretiminde kullanılmaz.
- **package_delivery.py** mevcutsa: Oturum paketlemesi içindir; yeni adayın bütün testlerinin yerine geçmez.
- **.cjs tarayıcı testleri:** Çalışan kontrollerin kaynakları korunmuştur fakat URL, uygulama ve modül yolları Mac'e/ilk çalışma alanına sabittir. Yeni aday sınanırken bu yollar yeni aday klasörüne açıkça yönlendirilmeli; eski teslimi test edip yeni aday geçti denmemeli.
- `roof_qa/check_*.py`, `p9401_cati_qa/inspect_roof.py` vb.: Teşhis/araştırma. Bazı JSON'lar düzeltilmeden önceki hatayı kanıtlar; son kabul raporu olarak okunmaz.

## Claude entegrasyonunda ilk teknik borçlar

1. Kaynak hashine bağlı seçim listelerini kalıcı kaynak kimliği eşlemesine bağla; rastgele yeni SKP'ye aynı node numaraları uygulanmasın.
2. Girdi/çıktı ve bağımlılık yollarını açık parametre yap. Aynı Mac'teki mutlak doku yolları taşınabilir paket yolu değildir.
3. IFC exporter metnini replace eden sarmalayıcı yerine ortak, açık parametreli bir fonksiyon kullan; mevcut Motor/IFC hattıyla eşleştirmeyi önce çıkar.
4. Kaydedilmiş dosyaları yeniden açan testlerin raporunu bağlayıcı çıkış koşullarına bağla. Şema hatası, geometri hatası, nesne kaybı, koordinat/topoloji farkı varsa aday başarısız olsun.
5. Arka yüz malzemesi, IFC sınıflandırma ve pano/BOM ilişkisini tamamlandı sayma; sonraki kapsama kayıtlı bırak.

Bunlar devir inceleme maddeleridir. Bu tur ana depoya bu değişiklikleri uygulamadık.
