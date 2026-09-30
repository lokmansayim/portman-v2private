# Aynı Mac'te yeniden çalışma

Paket dosyalarını doğrulamak için bu klasörde `python3 devri_kontrol_et.py` yeterlidir. Bu yalnız dosya/rapor bütünlüğü kontrolüdür; Blender/IFC geometrisini baştan üretmez.

Tam üretim **tek komutla her platformda çalışır diye sunulmuyor**. Kodlar mevcut Mac ve kaynak sürümlerine bağlı yerel prototiptir. Bağımlılıklar `ORTAM.json` içindedir; Blender/SketchUp SDK/IfcOpenShell ikili dosyaları bu devirde çoğaltılmadı. Bu Mac'te mevcutlar. Yeni kurulum/indirme otomatik yapılmaz.

## Bağımlılıklar

- Blender 5.2.1 LTS; kendi Python'u 3.13.13, bpy ve mathutils.
- Mevcut Bonsai dağıtımından çıkarılmış IfcOpenShell 0.8.5: `ORTAM.json → ifc_runtime`. ABI macOS arm64/Python 3.13'e bağlıdır.
- SketchUp C API yalnız özgün SKP'yi yeniden okumak için gerekir. Kaydedilmiş normalize scene.json ile devam etmekte SDK çağrısı gerekmez.
- Pillow: doku gömme ve karşılaştırma görselleri. Node/Playwright/Chrome: isteğe bağlı tarayıcı kontrolleri.
- Yerel Three.js ve lisansı HTML teslimlerinin vendor/ klasörlerinde bulunur.

## Devir paketini değiştirmeden aday üretme sırası

1. Yeni ve boş bir yerel deneme klasörü kullan. Ana repo, kaynak DWG/SKP ve bu devir klasörüne çıktı yazma. Bu bir üretim motoru kurulumu değildir; aynı verinin kontrollü yeniden koşusudur.
2. Deneme kökünde eski betiklerin beklediği dizin düzenini kur:
   - `kod_arsivi/skp_import/` → `work/skp_import/`
   - `veri/skp/Pxxxx/{scene.json,selected.json,source.blend,textures/}` → `work/skp_import/Pxxxx/`
   - `kod_arsivi/p9401_cati/` ve `veri/p9401_cati/*_selected.json` → `work/p9401_cati/`
   - `kod_arsivi/roof_qa/` → `work/roof_qa/`
   - `kaynaklar/uc_model/` → `outputs/Ilk_3_Model_Kaynaklari/`
   - `teslimler/Uc_Model_Sunum/` ve `teslimler/P9401_Cati_Alternatifleri/` → aynı isimli `outputs/` alt klasörleri. Bu, HTML şablonlarını/lisanslarını da getirir; Python bunları sıfırdan yazmıyor.
3. Doku yollarını yeni deneme klasöründeki `textures/` dosyalarına bağla; tarihli kaynak yolu/hash alanlarını değiştirme. Kopyalanan source.blend içindeki harici görüntü yollarını da kontrol et. Mevcut Mac'teki orijinal çalışma alanı durduğu sürece eski doku yolları çalışır, fakat bu taşınabilirlik kanıtı değildir.
4. `export_ifc.py` ve kontrol betiklerinin `work/ifc_runtime` beklentisini mevcut salt okunur IfcOpenShell yoluna bağla veya yalnız deneme kopyasında açık parametreye çevir. Yeni bağımlılık indirme.
5. Bütün komutların çalışma dizini deneme kökü olsun. `prepare_viewer_data.py` üç kaydı birlikte okur; seçili geometri ve model.js dosyalarını yeniler.
6. Her P9201/P9401/P9501 için Blender ile `correct_blend_transforms.py -- MODEL` çalıştır. Betik aynı kaynak köşelerini geri yükler, tam dönüşümü uygular ve `finalize_blend.py` ile sunumları üretir. **make_blend.py'yi bu sıraya koyma.**
7. Her model için Blender ile `export_ifc.py -- MODEL`; ardından `verify_saved.py`. `roof_qa/verify_world.py -- MODEL` ile kaydedilmiş Blender dosyasını da tekrar açıp karşılaştır.
8. P9401 çatılarında `create_variants.py`, her A/B/C/D için Blender `render_variants.py -- HARF`, ardından `export_variants.py` ve `verify_ifc.py`. `contact.py` yalnız tamamlanmış son PNG'lerden pafta üretir.
9. HTML testlerini **yeni adayın gerçek URL/dosya yoluna** yönlendir. Çatı ayırma/kaldırma, görünür eleman sayıları, seçenek değişimi ve mobil düzeni kontrol et.

Betik çağrısı biçimi: `BLENDER_YOLU --background --python BETIK_YOLU -- MODEL_VEYA_SECENEK`. Yolları `ORTAM.json` ve yeni deneme klasöründen al; bu belgede komutları yanlışlıkla eski çalışma alanına yazacak bir toplu kurulum betiği yoktur.

## Başarı kapıları

- Yeniden açılan dosyada nesne kaybı/çoğalması olmamalı; kaynak kimliği ve SHA korunmalı.
- IFC `schema_issues`, `geometry_errors`, `saved_topology_mismatch_nodes` boş olmalı; koordinat farkı açık sayısal eşikle kontrol edilmeli.
- Blender kaydedilmiş dünya köşeleri kaynağa karşı kontrol edilmeli. Mevcut sayısal toleransları üretim toleransı diye sunma.
- Çatı B/C/D'de gövde korunmalı; öneri parçaları ve varsayımları etiketli kalmalı.
- Bu kapılar geçse bile kaynak revizyon uyumu, Lokman seçimi ve üretim kabulü otomatik verilmez.

## Kaynak sürümü değişirse

Mevcut source.blend ile yeni scene.json eşleşmezse düzeltme betiğine devam etme. Sıfırdan okuma/kurma kodunu önce bakım maddeleriyle düzelt, kaynak kimliği eşlemesini yeniden kur, yeni çıktı revizyonu kullan. Ham dönüşüm kanıtlarını ve önceki kabul kayıtlarını koru.
