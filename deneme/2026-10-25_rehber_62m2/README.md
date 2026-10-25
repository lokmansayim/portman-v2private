# Deneme · 62 m² prefabrik montaj rehberi (beşik + cumba) · 25 Ekim 2026

Bir bayi projesinin (900 × 600 cm, veranda üstünde cumba) montaj rehberi. Kaynak: bayinin DWG'si (19 pafta), SketchUp modeli ve yükleme listesi; Lokman'ın Mac'indeki proje klasöründen okundu.

- **Bu klasörde** yalnız betikler ve okunan veri var; proje ve bayi adı yok (sayfa başlığı `uret.py --proje` ile verilir).
- **Kaynak dosyalar ve çıktılar** (rehber HTML, render'lar, GLB, maket STL) Lokman'ın proje klasöründe.
- **Durum:** deneme; canlıda değil.

## Hat

1. **Okuma** (`okuma/`, ezdxf 1.4.5).
   - DWG LibreDWG ile DXF'e çevrilir; `dxf_onar.py` satır kırılmış MTEXT'i onarır.
   - Pafta, pano, pencere ve kapı `MIMARI PLANSS` bloğundan okunur (`plan_blok.py`).
   - H'lar: H profil paftasındaki çemberlerden, tür çember renginden (`hlar.py`: 215 dübelli & kulaklı, 114 dübelli, 31 standart, 240 3'lü kulaklı, 30 3'lü standart).
   - Ayrıca: tavan omegası (`omega.py`), aşık sıraları ve boyları (`asik.py`), dere ve iniş (`inis.py`).
   - Makasların yeri, boyu ve yüksekliği SketchUp modelinden (`skp` okuyucusu önceki denemede, `2026-10-24_montaj_rehberi/alpha_mini`).
2. **Veri:** `rehber/build_data.py` → `data.json`.
   - İçerik: 39 pano, 30 H, 6 köşe direği, 2 çektirme U'su, veranda, 12 makas, 45 tavan omegası, aşık ve kaplama paftası.
   - Oda sırası (Lokman): Yatak 1 → banyo → hol → yatak 2 → salon-mutfak.
3. **Sayfa:** `python rehber/uret.py <çıktı.html> --proje "<başlık>" [--gorsel]`.
   - Girdi: `kabuk.html` (PK-01 rehberinin arayüzü) + `sahne.js` (Three.js 0.160 sahnesi).
   - 18 adım, 420 parça. Kartı olmayan parçalarda yükleme listesindeki ad yazar.
4. **Model ve kameralar:** `node test/export.js <rehber.html> <model.glb>`.
   - Parça adları `s{adım}_{sıra}`, malzeme adları anahtar; kimlik kartı `extras`'ta.
   - Adım kameraları `model_kamera.json`'a yazılır.
5. **Render:** `render/render.py` (Blender 4.2 bpy, Cycles), iki kip:
   - `gorunum <ad> <png> 64 1.0` — altı görünüm: `on_sol`, `on_sag`, `arka_sol`, `catisiz`, `cati_katman`, `ic_kose`;
   - `adim hepsi <klasör> 24 1.0` — 19 kare.
6. **Maket:** `python maket/maket.py rehber/data.json <klasör> 50 <önek>` → 1:50 kapalı STL.
   - Parçalar: gövde ve çıkarılabilir çatı, 4 köşe tırnağı.
   - Bağımlılık: `trimesh`, `manifold3d`.
7. **Kontrol:**
   - `node test/test.js <html> <klasör> "0;6;11;16"` — ekran görüntüleri;
   - `node test/kartlar.js <html>` — her parçanın kart satırları.

## Bu projede yeni olanlar (PK-01'e göre)

- **Cumba.** İkinci beşik, ana çatıya dik.
  - Mahyası ana mahyayla aynı yükseklikte; iki dere (vadi) hattı var.
  - MKS09 veranda ön kirişinde, MKS10 yan kirişlerde. MKS11–12 ara makaslar: ana makasların üst başlığına oturur.
- **Çatı katmanları.** OSB 11 mm + nem bariyeri + trapez (80 cm kapatır); ters mahya; trapez sac mahyası.
- **Genel çatı yüzü sistemi.**
  - Her yüz yerel s (eğim boyunca), t (saçak boyunca), n (dik) koordinatlarında kurulur.
  - Levhalar dışbükey çokgen kırpmayla dere hattında kesilir.
- **Kalkan çerçevesi.** Üç kalkan için genel: baş makas betopanı, Z, C kapama, alın sacı ve alt uç.
- **Veranda.** Kolonlar, kirişler, özel köşe direği A ve özel H (C).

## Varsayımlar (Lokman'ın teyidini bekler)

1. **OSB dizilimi.** OSB yerleşim paftası DWG'de boş (paftada 25 adet).
2. **Trapez kesim parçaları.** Paftadaki 29 levhanın dışında 7 üçgen kesim parçası (mahya ile dere arası).
3. **Kalkan betopanı köşe dolguları.**
4. **Kesitler.** PK-01'deki köşe, Z, C kapama, saçak ve alın sacı kesitleri aynen alındı.
5. **Alın sacı.** Trapez kenar hadvesine göre ~11 cm.
6. **Dere iç köşesi.** Cumba sağ deresi ön dereye iç köşede bağlanır.

## PK-01 düzeltmesi (bu oturum)

PK-01 rehberinde makas kartında eksik virgül vardı (`['Profil', …] ['Kart ölçüsü', …]`); makasa dokununca kart açılmıyordu.
- `2026-10-24_montaj_rehberi/rehber/template.html` düzeltildi.
- Kart satırı süzgeci `r && r[1]` yapıldı.
