# Montaj rehberi, render ve Alpha Mini denemesi (24 Ekim 2026)

Deneme; canlıda değil. Üç iş buradan devam eder, her birinin devir notu `docs/devir/` altında:

| İş | Devir notu | Klasör |
|---|---|---|
| Alpha Mini imalat çıktısı (.bde) | `docs/devir/2026-10-24_Alpha_Mini_Devri.md` | `alpha_mini/` |
| Render (köşe ve ev) | `docs/devir/2026-10-24_Render_Devri.md` | `render/` |
| Render'lı rehberin VPS'te herkese açık yayını | `docs/devir/2026-10-24_Rehber_Yayin_Devri.md` | `rehber/` + `render/gorsel/` |

## Klasörler

- `rehber/`: IKEA tarzı etkileşimli 3B montaj rehberi (PK-01, 60 m², 17 adım, oda oda dizilim; her parça kimlik kartına bağlı).
  - `build_data.py`: depodaki pafta katmanından (`testler/kimlik/veri/PK01_pafta_katmani.json`) ve kartlardan (`kurallar/urun/kartlar.json`) `data.json`'u kurar.
  - `template.html`: sayfa (Three.js 0.160.0, jsdelivr importmap).
  - `uret.py`: tek dosya HTML'i üretir; `--proje` başlıktaki adı verir (depoda ve herkese açık çıktıda kod kalır).
  - `test/`: Playwright ekran görüntüsü ve geometri dökümü betikleri.
- `render/`: Blender Cycles render hattı.
  - `export.js`: rehberin 3B modelini GLB'ye aktarır.
  - `ev_render.py`: evin tamamını render eder; görünümler `on_sag`, `arka_sol`, `catisiz`, `kalkan`, `detay`.
  - `kose_render.py` ve `pafta.py`: köşe direkleri (B-01, B-02) ve etiketli pafta.
  - `kose_cizim.py`: köşe okuma çizimi.
  - `gorsel/`: çıktılar.
- `alpha_mini/`: makine dosyası okuma.
  - `bde_oku.py`: .bde okuyucu.
  - `skp_oku.py` ve `makas*.py`: SketchUp okuma (openskp).
  - `kaynak/`: iki gerçek çatı makası .bde dosyası (dosya adları maskeli).

## Ortam (bulut kabında denendi)

- Sayfa üretimi: `python3 rehber/uret.py cikti.html`. Veriyi yeniden kurmak için önce `python3 rehber/build_data.py`.
- Ekran görüntüsü ve dışa aktarma için Node ve Playwright gerekir. Ayrı bir klasörde `npm i three@0.160.0` kurulur; betikler `SP/t/node_modules/three`, `SP/montaj-rehberi.html` ve `SP/render/` düzenini bekler (SP = betiğe verilen klasör).
- Render: `python3.11 -m venv v && v/bin/pip install bpy==4.2.0`, sonra `v/bin/python render/ev_render.py on_sag cikti.png 64 1.0`. 2 çekirdekte süreler:
  - köşe görünümü, 64 örnek: yaklaşık 3 dk;
  - ev görünümü, 16 örnek, yarım çözünürlük: yaklaşık 25 sn.
- SKP okuma: `pip install openskp==1.3.0`, ağsız (`unshare -n`) koşturuldu. Yalnız SketchUp 2020 ve sonrası dosyaları okur.
- DWG okuma: LibreDWG 0.13.3 (GitHub release tarball'ından derlendi): `dwg2dxf`, sonra ezdxf. Kırık MTEXT satırı birleştirilerek düzeltildi.
