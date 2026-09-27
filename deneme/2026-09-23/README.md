# 23 Eylül denemeleri

Bu klasör, 23 Eylülde depo dışında yapılan dört denemenin kodunu, notlarını ve küçük çıktılarını taşır. Kaynağı Lokman'ın masaüstündeki "Claude Portman Çalışması" klasöründe 10–13 numaralı klasörlerdir. Denemeler v1.1.1'de ve canlıda yok. 28 Eylülde depodaki v1.1.1 üzerinde yeniden koşuldular; 14 kontrolün 14'ü o günkü sonuçla aynı çıktı.

| Klasör | Ne yapıyor | Girdi |
|---|---|---|
| `10_Cozumleyici/` | Bayinin vektör PDF'ini okur → Ölçülü Kroki → serbest akslı İş Emri → yamalı Motor (DXF, PDF, BOM). `kod/motor_serbest_aks.patch` Motor'a serbest aks ekler. | Tatar 80 m² bayi planı (16.09) |
| `11_Blender/` | Aynı PDF'ten pano pano Blender modeli; BOM sahnedeki nesnelerden sayılır. | Tatar 80 m² |
| `12_IFC/` | Aynı girdiden IFC4 modeli (IfcOpenShell 0.8.5); şema doğrulaması, çift sayım ve hacim denetimi. | Tatar 80 m² |
| `13_Kiyas/` | Yan Verandalı 2+1'in İş Emri'nden IFC4 ve Astra'nın Blender modeliyle eleman eleman kıyas. | `is_emri/YAN_VERANDALI_2plus1_6x8p5.json` |

Her klasörde o günün notu (`2026-09-23_*.md`) sonuçları ve açık soruları anlatır.

## Yeniden koşmak

```
python3 deneme/2026-09-23/yeniden_kos.py --bpy <bpy==5.0.1 kurulu python>
```

Betik v1.1.1 ağacını geçici bir klasöre kopyalar, yamayı orada uygular ve betikleri orada tek bir `cozumleyici` paketinde birleştirir. 23 Eylülde betikler böyle tek pakette çalışıyordu; buradaki klasörlere bölünmüş hâlleriyle doğrudan çalışmazlar. Depo koduna dokunulmaz.

Gerekenler: ezdxf 1.4.4, pymupdf, shapely, pydantic, numpy, pillow, ifcopenshell 0.8.5. Blender adımı için bpy 5.0.1 (ayrı sanal ortam önerilir); verilmezse o adım atlanır.

`ifc_uret.py`'nin iki sürümü var. `12_IFC/kod/` sürümü Tatar modelini üretti. `13_Kiyas/kod/` sürümü daha yeni ve BOM kodlarını da yazıyor; Kıyas onunla yapıldı.

## 28 Eylül yeniden koşum sonucu

| Kontrol | Sonuç |
|---|---|
| PDF okuyucu: `kroki.json` | Aynı. Ölçek modülden 1,63924, ölçü yazılarından 1,64014 cm/pt (fark %0,05). |
| Serbest aks: `is_emri.json`, `donusum_raporu.json` | Aynı |
| Yamalı Motor: `validation.json`, `bom.json`, `bom.csv` | Aynı (doğrulama geçti; hata 0, uyarı 0) |
| Blender girdisi: `blender_girdi.json` | Aynı |
| IFC: sınıf sayıları | Aynı (65 IfcWall, 19 IfcOpeningElement, 8 IfcWindow, 1 IfcDoor, 9 IfcSpace) |
| IFC: şema doğrulaması | Geçti, 0 hata |
| IFC: `ifc_bom.csv` | Aynı |
| Çift sayım: IFC ↔ Blender BOM | Aynı, 35 kalem |
| IFC: geometri hacim denetimi | Aynı: net hacim 11,5086 m³, fark %0,0 |
| Blender (bpy 5.0.1): `blender_bom.csv`, `blender_ozet.json` | Aynı (65 pano nesnesi) |
| Kıyas: `motor_girdi.json` | Aynı |
| Kıyas: `kiyas.json`, `kiyas_tablosu.csv` | Aynı. Astra'nın 67 elemanından 65'i birebir; 2'si Astra'da 3B değil (veranda profili). Açıklık 13/13. |

## Dışarıda bırakılanlar

Görseller (PNG, yaklaşık 20 MB), `.blend` ve `.glb` modelleri, Tatar Motor çıktılarının DXF, PDF ve önizlemesi. Hepsi yukarıdaki betikle yeniden üretilebilir; asılları masaüstü klasöründe duruyor.

## Kişisel veri

Bayi PDF'i yalnız oda adlarını ve ölçüleri içeriyor; ad, telefon ya da adres yok (28.09'da kontrol edildi). Dosya adlarında ve notlarda bayinin adı geçiyor. Metin dosyaları telefon numarası, e-posta ve anahtar kalıplarına göre tarandı; bulgu yok.
