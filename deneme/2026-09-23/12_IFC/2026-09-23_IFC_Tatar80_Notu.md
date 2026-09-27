# Tatar 80 m² — IFC4 yapı modeli (23 Eylül 2026)

**Kaynak:** Blender modeliyle aynı girdi, `11_Blender/blender_girdi.json`. Bu dosya Mustafa Tatar'ın 16.09 PDF'inden okundu. Model bayinin planının birebir karşılığıdır.

**Üretim:** Yalnız IfcOpenShell 0.8.5 kullanıldı; Blender'a gerek yok. Süre 1,8 saniye.

**Dosya:** `Tatar_80m2_bayi_plani.ifc` (IFC4, metre).

## İçerik
| IFC sınıfı | Adet | Ne |
|---|---|---|
| IfcWall | 65 | Bayinin her pano parçası ayrı duvar. 2 tipe bağlı: PE-DIS-100 ve PE-IC-60. Katmanlar 8 mm fibercement + EPS + 8 mm fibercement. |
| IfcOpeningElement | 19 | Panoları gerçekten kesen boşluklar: 11 pencere boşluğu (3 pencere iki panoya bölünüyor) ve 8 kapı boşluğu. |
| IfcWindow / IfcDoor | 8 / 1 | PVC pencereler ve çelik dış kapı. İç kapılar kapsam dışı, yalnız boşlukları var. |
| IfcSpace | 9 | 8 oda ve veranda. Her birinde net alan ve bayinin etiketindeki alan birlikte duruyor. |
| IfcSlab | 5 | Zemin betonu (bayi/saha), ana çatının 2 yüzü, veranda çatısının 2 yüzü. |
| IfcRoof | 2 | Ana beşik ve veranda beşiği. |
| IfcElementAssembly (TRUSS) → IfcMember | 9 → 72 | Makaslar ve elemanları. |
| IfcColumn / IfcBeam / IfcPlate | 2 / 4 / 3 | Veranda dikmeleri, kirişler, alın dolguları. |

Her panoda şu bilgiler var:
- `Pset_WallCommon`: dış/iç ve pano sınıfı.
- `PortatifEv_Pano`: BOM kalemi, sınıf, boy, kalınlık, açıklıklar, pencere ekin üstünde mi, kaynak parça numarası.
- `Qto_WallBaseQuantities`: uzunluk, yükseklik, brüt ve net yüzey, brüt ve net hacim.

## Doğrulama
- **Şema:** IfcOpenShell doğrulamasında **0 hata**.
- **Çift sayım:** IFC'den sayılan 35 kalem Blender sahnesinden sayılan 35 kalemle **birebir aynı**, 0 fark.
- **Metraj:** Dış duvar 34,68 m, iç duvar 31,51 m. Bu değerler bayinin çizimiyle ve Motor'un dış duvar sonucuyla aynı.
- **Boşluk kesimi:** IfcOpenShell'in geometri motoru boşlukları kesip panoları üçgenlere çevirdi. Pano hacimlerinin toplamı 11,5086 m³ çıktı. Bu, modeldeki net hacim değerine **%0,0 farkla** eşit: boşluklar gerçekten kesiliyor ve hesaplanan miktarlar doğru.
- **Bayi çizimindeki hatalar modelde işaretli:** Pano ekine denk gelen 3 pencerenin taşındığı 6 pano `PencerePanoEkinde = True` olarak işaretli. Bonsai'de bu özelliğe göre süzülebilir.

## Nasıl açılır
- **Bonsai:** Blender'da *Edit → Preferences → Get Extensions* altında "Bonsai" kurulur (Blender 4.2 ve sonrası). Ardından *File → Open IFC Project*.
- **Diğer programlar:** IFC4 olduğu için ArchiCAD, Revit ve IFC görüntüleyiciler de açar.

## Dosyalar
- `Tatar_80m2_bayi_plani.ifc`
- `ifc_bom.csv`: IFC'den sayılan malzeme listesi.
- `ifc_geometri_denetimi.json`: hacim kontrolü.
- `ifc_01_dis_gorunus.png`, `ifc_02_catisiz.png`: IfcOpenShell'in ürettiği geometriden alınan render.
- `kod/ifc_uret.py`: JSON'dan IFC üretir. `python3 ifc_uret.py blender_girdi.json model.ifc`
- `kod/ifc_gorsel.py`: geometri, hacim kontrolü ve render (render için bpy gerekir).

## Açık noktalar
- Ön onay paftası (plan, görünüş, ölçü) hâlâ Motor'un DXF/PDF'inden üretiliyor. IFC'den 2D pafta üretimi henüz yok.
- IfcOpenShell VPS'te denenmedi. Natro'nun işlemcisinde çalıştığı ayrıca doğrulanmalı.
- Varsayımlar Blender notundakiyle aynı: veranda beşiği, kapı boşlukları 200 cm, pencere eşikleri, alın dolgusu ve makas aralığı.
