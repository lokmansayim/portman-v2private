# Astra'nın Blender modeli ile Portman IFC modelinin kıyası: Yan Verandalı 2+1 (23 Eylül 2026)

## Neyi neyle kıyasladık
Tatar 80 m² için Astra'nın Blender dosyası yok. Mac'teki tek eşleşen proje Yan Verandalı 2+1 (6×8,5 pano). Kıyas bu projeyle yapıldı.

| | Astra | Portman |
|---|---|---|
| Kaynak | `yeni-2plus1-yan-verandali.dwg`. Bu dosya AutoCAD'den DXF'e, oradan `model_data.json`'a, oradan Blender'a aktarıldı. | Aynı projenin İş Emri (`YAN_VERANDALI_2plus1_6x8p5.json`). Motor kurallı planı üretir, plan IFC4'e çevrilir ve Bonsai ile açılır. |
| Model dosyası | `Documents/Codex/2026-09-05/.../yan-verandali-2plus1-R01/model.blend`: 232 nesne | `YanVerandali_2plus1_Motor.ifc`: 188 IFC nesnesi, 52 IfcWall |
| Aynı kaynak mı? | Kaynak DXF ve BOM kaydının SHA-256 özetleri depodaki `ref_yan` dosyalarıyla **aynı**. | |

Astra'nın `.blend` dosyası açılmadı ve değiştirilmedi. Nesneleri yalnız açık Blender sahnesine kopyalandı ve yana kaydırıldı.

## Sonuç: geometri ve BOM aynı
Karşılaştırma toleransı **1 mm**, Astra'nın kendi sayısal toleransı.

| Konu | Astra | Portman IFC | Sonuç |
|---|---|---|---|
| Pano | 52 | 52 IfcWall | **52/52 aynı.** Plan kutusu ve 3B kutu farkı 0 mm. Pano hacim toplamı 10,98913 m³ ile 10,98912 m³; fark %0,0001. |
| Köşe ve üçlü H bağlantı (B01, B02×6, B03×4) | 11 | 11 IfcMember | Plan konumları aynı. B03 temsili farklı, aşağıda. |
| Veranda dikmesi (B04) | 2 | 2 IfcColumn | Aynı. |
| Veranda profili (V03, V04) | 3B yok, yalnız referans çizgisi | 2 IfcBeam | Plan kutusu aynı. Kot bizde varsayım: 240–250 cm. |
| Pencere | 4×120×120, 2×120×180, 1×60×40 | Aynı | **7/7 aynı.** Konum ve kot 0 mm farkla; eşikler 80, 20 ve 160 cm, üst kot 200 cm. |
| Kapı ve geçiş | K02 97 cm, 4×K01 82 cm, 1 kapısız geçiş | Aynı | **6/6 aynı.** Kapı yüksekliği 200 cm; geçiş boşluğunda dolgu yok. |
| Mahal alanları | 7 alan (DWG yazısı) | 7 IfcSpace | **7/7 aynı**, fark 0,0000 m². |
| BOM | 26 kod, 79 adet | 26 kod, 79 adet | **Astra DWG, Motor DXF ve IFC üçü de aynı.** Tablo: `bom_uclu_kiyas.csv`. |

**Karşılaştırmanın kendisi sınandı.** Bizim modele bilerek iki hata koydum: bir panoyu 2 cm kaydırdım, bir pencerenin eşiğini 10 cm kaldırdım. Kıyas ikisini de yakaladı. "Aynı" sonucu gerçek bir ölçüm.

## Farklar: yalnız temsil ve kapsam
| Konu | Astra | Portman IFC |
|---|---|---|
| Çatı | Yok; ön görünüş çizgileri gizli referansta | Beşik çatı %33, 30 cm saçak, 10 makas (80 IfcMember), 2 alın dolgusu |
| Kapı | Plandaki açık kanat izi 200 cm'ye yükseltilmiş | Kapalı kanat ve kasa (IfcDoor) |
| Pencere | Yanaklar ve tek yüzey cam referansı | PVC kasa, orta kayıt ve cam (IfcWindow) |
| Üçlü H (B03) | Kalınlıksız çizgi yüzeyleri | 6×8,5 cm dolu kutu. İkisi de gerçek profil kesiti değil. |
| Mahal | Yazı nesnesi | IfcSpace ve net alan miktarı (Qto) |
| Zemin | Sunum düzlemi | Kapsam dışı IfcSlab (bayi/saha) |
| Bir pano | 1 ile 4 ayrı mesh parçası (yan, pencere altı, pencere üstü) | Tek IfcWall. Boşluk IfcOpeningElement ile gerçekten kesiliyor. Tip, 8 + EPS + 8 katman, özellik setleri ve miktarlar dosyada. |

## Değerlendirme
- **Astra'nın güçlü yanı izlenebilirlik:** her nesnede CAD handle, kaynak kimliği ve SHA-256 var; tekrar üretim denetleniyor. Bunu IFC'ye taşımak iyi olur: her IfcWall'a Motor DXF blok adı ve İş Emri revizyonu yazılabilir.
- **IFC'nin artısı:** Aynı geometri, üzerine sınıf, tip, malzeme katmanı ve miktar. Bonsai, ArchiCAD ve Revit açar. BOM doğrudan dosyadan sayılıyor.
- **Önerim:** Motor → IFC hattı Astra'nın DWG → Blender aktarımının yerini tutuyor, üstüne yapı bilgisi ekliyor. Astra'yla elle yapılan aktarım yerine bu hat kullanılabilir.

## Bonsai notu
Yükleme sırasında Bonsai "experienced an error" uyarısı verdi. Nedeni: kamerayı ayarlama adımı 3B görünüm arıyor, o anda ekranda yalnız Python konsolu vardı. Bu adımdan önce tüm elemanlar yüklendi (188 IFC nesnesi). IFC dosyası diskte değişmedi. Sonraki açılışta *Dosya → Open IFC Project* 3B görünüm açıkken kullanılırsa uyarı çıkmaz.

## Açık noktalar
1. **İç kapı kapsamı tutarsız.** Astra'nın ve Motor'un BOM'u iç kapıyı (K01) malzeme sayıyor. Tatar IFC'sinde iç kapıyı "bayi" diye kapsam dışı bırakmıştım. Hangisinin doğru olduğuna karar vermen gerek.
2. B03 üçlü H ve veranda profillerinin gerçek kesiti ve kotu tanımlı değil. Astra'da da değil.
3. PEV 5×4 dosyası başka bir proje: ölçü ve bölme denemesi. Kıyasa katılmadı.

## Dosyalar (13_Kiyas)
- `YanVerandali_2plus1_Motor.ifc`: bizim model.
- `bom_uclu_kiyas.csv`: Astra, Motor ve IFC BOM'u kod kod.
- `kiyas_sonuc/kiyas_tablosu.csv` ve `kiyas.json`: her Astra elemanı için eşleşen IFC ürünü, kutu farkı ve hacim farkı.
- `kiyas_01_perspektif.png`, `kiyas_02_catisiz.png`, `kiyas_03_ust_plan.png`: Blender'da, Astra'nın modeli ve bizim IFC yan yana.
- `astra_model_rapor.json`, `astra_detay.json`, `astra_kaynak/`: Astra modelinin envanteri ve Astra'nın kendi doğrulama dosyalarının kopyası.
- `kod/`: `motor_girdi.py` (İş Emri → model girdisi), `ifc_uret.py` (kod, iç kapı ve bağlantı eklendi; Tatar çıktısı değişmedi, 35 kalem aynı), `kiyas_astra.py`.
- Blender betikleri: `astra_incele.py`, `astra_detay.py`, `yukle_bizim_ifc.py`, `vitrin.py`.
