# kaynak_inceleme · SKP kaynak modeli → geometrik IFC4, denetim, P9401 çatı karşılaştırması

Codex'in 30.09.2026 devrindeki yerel prototipi (üç model: P9201, P9401, P9501; P9401 çatı seçenekleri A–D) mevcut depoya bağlayan **yerel entegrasyon adayı**. Kabul raporu: `docs/raporlar/2026-09-30_Codex_Devir_Kabul.md`.

## Yeri: üretim hattının yanında, içinde değil

| Yol | Girdi | Çıktı | Rol |
|---|---|---|---|
| Motor (`motor/`) | İş Emri | DXF, PDF, BOM | Üretim çizimi. **Değişmedi.** |
| IFC/Blender 23.09 (`deneme/2026-09-23/`) | İş Emri | Semantik IFC4 (IfcWall, IfcOpeningElement…), Blender pano modeli | Üretim 3D'si. İE-04 adım 5'te Motor hattına alınacak. **Değişmedi.** |
| **kaynak_inceleme** (bu paket) | Katalog SKP'sinden okunmuş sahne (`scene.json` → `selected.json`) | Geometrik IFC4 (`IfcBuildingElementProxy`), denetim raporları | Kaynak incelemesi: katalog 3D kaynağının kimlikli, denetlenebilir kopyası. K-A9 kaynak uygunluk denetimine üçüncü kaynak (JPG ve DXF'in yanında) olabilir. |

Bu paket BOM, pano, BIM sınıfı ya da üretim kabulü üretmez. Lokman'ın görsel seçimi ve Ubeydullah'ın teknik kabulü ayrı kayıtlardır.

## Modüller

| Modül | Yerine geçtiği Codex betiği | Ne yapar |
|---|---|---|
| `geometri.py` | (mathutils hesabı) | Dünya dönüşümü. `blender32` kipi Blender'ın float32 hesabını birebir taklit eder; Codex'in IFC koordinatları bayt bayt yeniden çıkar. `float64` kipi daha hassastır (fark < 1 µm). Normalize edilmemiş dönüşümü reddeder. |
| `ifc_yaz.py` | `export_ifc.py` + `export_variants.py` (metin değiştirip exec eden sarmalayıcı) | Tek, açık parametreli IFC yazıcı. Blender gerekmez. Model ve çatı seçeneği için `model_tanimi` / `cati_tanimi`. |
| `ifc_dogrula.py` | `verify_saved.py`, `verify_ifc.py` (başarısızlıkta durmuyordu) | Bağlayıcı kapılar: şema, nesne kümesi, koordinat, topoloji, özellikler, geometri motoru. Biri kalırsa çıkış 1. `karsilastir`: iki IFC tarih damgaları dışında aynı mı. |
| `secim.py` + `veri/secim_<kod>.json` | `prepare_viewer_data.py` içindeki sıra numaralı listeler | Çatı ve dışlanan grupları SketchUp kalıcı kimliği + SKP SHA256 ile kaydeder. SHA farklıysa ya da kimlik belirsizse durur. |
| `cati.py` | `render_variants.py` içindeki gövde kontrolü | A–D'de kaynak gövdenin birebir korunduğunu, öneri parçalarının etiketli olduğunu denetler. |
| `blender_dogrula.py` | `verify_world.py`, `check_saved_blend.py` | Kaydedilmiş `.blend` dosyalarını bpy ile açıp bağlayıcı kapılarla denetler. |
| `dogrula_devir.py` | `devri_kontrol_et.py` (yalnız hash ve kayıtlı raporları okuyordu) | Devrin bütününü bağımsız yeniden üretir ve denetler. |
| `veri/kaynaklar.json` | `Kaynak_Kaydi.json`, `DOSYA_MANIFESTI.json` | Köken kaydı: SKP, JPG, DWG, JSON, IFC, .blend dosyalarının SHA256'sı ve revizyon kimlikleri. Durum ya da kabul tutmaz. |

## Veri

Büyük dosyalar (SKP'den türetilmiş JSON'lar ~95 MB, IFC'ler ~60 MB, `.blend`'ler ~75 MB) depoda **değildir**. Lokman'ın Mac'inde, Codex devir klasöründedir: `~/Documents/Codex/2026-09-30/merhaba-bilge-ben-lokman-ekledi-im/outputs/Claude_Devir_2026-09-30/`. Depoya alınması yeni veri paylaşımıdır ve Lokman'ın onayını ister.

## Kullanım (depo kökünde)

```
source ~/.cache/portman-venv/bin/activate          # bash araclar/ortam_kur.sh
python -m kaynak_inceleme.dogrula_devir --veri <devir klasörü> --cikti <boş klasör>
python -m kaynak_inceleme.ifc_yaz --secili <selected.json> --cikti <klasör> [--cati B] [--dogrula]
python -m kaynak_inceleme.ifc_dogrula --ifc <x.ifc> --secili <selected.json> [--cati B] [--karsilastir <y.ifc>]

# Blender dosyaları (bpy 5.2.x, Python 3.13; ayrı sanal ortam):
uv venv --python 3.13 ~/.cache/portman-bpy && uv pip install --python ~/.cache/portman-bpy/bin/python bpy==5.2.2
~/.cache/portman-bpy/bin/python -m kaynak_inceleme.blender_dogrula --veri <devir klasörü> --cikti <klasör>

# Testler (sentetik veri; gerçek veriyle bütünleşik test için PORTMAN_KAYNAK_VERI=<devir klasörü>):
python -m pytest -q testler/kaynak_inceleme
```

Ağ, LLM, WhatsApp ya da canlı sunucu kullanılmaz. Veri klasörüne yazılmaz; hiçbir dosya silinmez.
