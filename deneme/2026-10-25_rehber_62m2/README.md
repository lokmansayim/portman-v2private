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
   - 20 adım (sıra Lokman'ın, 26 Ekim), 419 parça. Kartı olmayan parçalarda yükleme listesindeki ad yazar.
4. **Model ve kameralar:** `node test/export.js <rehber.html> <model.glb>`.
   - Parça adları `s{adım}_{sıra}`, malzeme adları anahtar; kimlik kartı `extras`'ta.
   - Adım kameraları `model_kamera.json`'a yazılır.
5. **Render:** `render/render.py` (Blender 4.2 bpy, Cycles), iki kip:
   - `gorunum <ad> <png> 64 1.0` — altı görünüm: `on_sol`, `on_sag`, `arka_sol`, `catisiz`, `cati_katman`, `ic_kose`;
   - `adim hepsi <klasör> 24 1.0` — 20 kare (genel bakış + 19 adım). Rehberde "Adımı render göster" kaldırıldı (Lokman, 25 Ekim gece); kip betikte duruyor, `hepsi.sh` çağırmıyor.
   - `gorunum bas_kesit …` — baş makas kesiti (plan y = 150'de gerçek kesit: düzlemi kesen nesneler boolean ile kesilir).
   - `gorunum kose_dis|kose_yan|kose_ust|kose_alt …` — arka-sol köşede saçak sacı, alın sacı ve dere birleşimi (inceleme için; galeride yok).
6. **Maket:** `python maket/maket.py rehber/data.json <klasör> 50 <önek>` → 1:50 kapalı STL.
   - Parçalar: gövde ve çıkarılabilir çatı, 4 köşe tırnağı.
   - Bağımlılık: `trimesh`, `manifold3d`.
7. **Kontrol:**
   - `node test/serme.js <html> <klasör> 16 <ms,…> [kamera]` ve `node test/serme2.js <html> <png> <oran> <kamera>` — rulo serme animasyonu;
   - `node test/test.js <html> <klasör> "0;6;11;16"` — ekran görüntüleri;
   - `node test/kartlar.js <html>` — her parçanın kart satırları.
   - `node test/gal.js <html> <önek>` — render galerisi açılıyor mu, görseller yükleniyor mu; "Adımı render göster" düğmesi yok mu.

## Bu projede yeni olanlar (PK-01'e göre)

- **Cumba.** İkinci beşik, ana çatıya dik.
  - Mahyası ana mahyayla aynı yükseklikte; iki dere (vadi) hattı var.
  - MKS09 veranda ön kirişinde, MKS10 yan kirişlerde. MKS11–12 ara makaslar: ana makasların üst başlığına oturur.
- **Çatı katmanları.** Trapez 27/200-6 (100 cm kapatır, 0,5 mm; hadve 27, adım 200, tepe 42 / taban 74 mm) doğrudan aşıkların üstünde; levhalar 100'lükle yeniden dizildi (paftadaki 80'lik); ters mahya; trapez sac mahyası. OSB ve nem bariyeri yok (Lokman, 25 Ekim akşamı; paftadaki not bu projede geçerli değil).
- **Cephe fugası.** Dış panoların dış betopanında 6 sıra 2 cm fuga (alttan 38 cm'de bir, üstte 10 cm bant; pafta: fugalı duvar detayı). Modelde 5 mm derin oluk; malzeme anahtarı `fuga`. Makette 0,5 × 0,3 mm oluk.
- **Makas uçları.** Kalkanlarda iki 125 × 250 betopanın dışında kalan uçlara, betopanların eğimle kesilen artanı döşenir (Lokman, 25 Ekim akşamı). Makasın duvar dışında kalan ~30 cm'lik ucu da saçak altından makasın üstüne kaplanır (26 Ekim).
- **100'lük omegalar ve baş makas detayı (Lokman çizimi ve ölçüleri, 25 Ekim).** Pano 8 + 84 (EPS) + 8 mm = 100 mm; H sacı 1,2 mm, kanat uçları ezilmiş kıvrımla 2 mm (`HS`); H sırt genişliği toplam 5 cm (gövdenin iki yanına 2,5 cm; Lokman'ın çiziminde 43,92 mm), 100'lük ve 60'lıkta aynı. 100'lük omegalar 10,5 cm = 2 + 100 + 2 mm + 1 mm, dış kanat H kanadına yaslı, içteki aralıklar silikonize mastik (modelde boşluk). Saçak omegası (Lokman çizimi): içte 3 cm kanat + içe 3 cm ayak, dışta 3 cm kanat ve eğik dudak; duvar omegası iki yanda 3 cm. Baş makas omegası: derinlik 3 cm, içte 3 cm açık yanak, dışta 1 cm U yanak; 8 mm betopan U'ya girer, makasa dayanır; baş makaslar dış kanatla aynı hizada (`build_data.py` `BAS_DIS` = 0,3). Z değişmedi.
- **Büyük pencereler.** 180/180 pencereli çelik karkas panelde (DVR, 251 × 250) pencere yanları da betopan kaplı ve fugalı.
- **İç duvar omegası.** İç duvar üstlerine 60'lık duvar omegası: 6,5 cm açıklık (6 cm pano + H sacları), 3 cm derinlik, 3 cm kulaklar (`omega_duvar` `tur='ic'`, 375'lik parçalar, kapı üstlerinden kesintisiz).
- **Ters tavan (adım 12).** Tavan omegalarının altına 12,5 mm alçıpan 120 × 250 (banyoda yeşil), verandada boardex 120 × 240.
- **Çatı izolasyonu (adım 13, aşıklardan önce).** 10 cm rulo cam yünü, her makas aralığına bir şerit; cumbada (veranda) makas yönünde yatay iki şerit; rehberde rulo açılarak serilir (`anim.serme`; rulo `userData.gecici`, GLB'ye girmez).
- **Saçak, alın ve dere birleşimi** (Lokman'ın gönderdiği ev fotoğraflarına göre). Köşede iniş ağzı derenin uç kısmında, borunun hizasında; kaz boynu duvara (cumbada veranda kolonuna) dik döner, boru köşe direği kaplamasının (13 cm) yanından iner. Saçak sacının alnı derenin bütün boyunca köşeye kadar uzar (`SACAK` `f0`/`f1`); saçak altı baş makasın betopanına dayanıp kesilir (`t0`/`t1`); alın sacının saçak altı kolu makasın topuğunda biter, alın yüzü dereyi de içine alacak kadar geniştir ve derenin ucunu kapatır; ek parça yok (Lokman'ın işaretli fotoğrafları, 26 Ekim).
- **Pencereler ve 20. adım (26 Ekim).** Antrasit gri (RAL 7016). 180/180: Lokman çizimi, 178 × 178 + 1'er cm pervaz payı, 4 bölme (iki yan sabit, ortadaki iki kanat içe açılır, ortada kayıt yok), dış pervaz. 20. adımda kanatlar ve kapılar sırayla açılıp kapanır (`anim.ackapa`: `don` düşey menteşe, `devir` vasistas, `kay` sürgü; dinlenme hâli kapalı, GLB kapalı hâlde).
- **Genel çatı yüzü sistemi.**
  - Her yüz yerel s (eğim boyunca), t (saçak boyunca), n (dik) koordinatlarında kurulur.
  - Levhalar dışbükey çokgen kırpmayla dere hattında kesilir.
- **Kalkan çerçevesi.** Üç kalkan için genel: baş makas betopanı (makas uçları dahil), Z, C kapama ve alın sacı. Ayrı alt uç parçası yok (Lokman, 26 Ekim): alın sacı dereyi de içine alacak kadar geniş (`ALIN_ALT`).
- **Veranda.** Kolonlar, kirişler, özel köşe direği A ve özel H (C).

## Varsayımlar (Lokman'ın teyidini bekler)

1. **Trapez dizilimi.** 100'lük levhayla kalkan kenarından; cumbada 10 parça (listede 8).
2. **Kesitler.** PK-01'deki köşe, Z, C kapama, saçak ve alın sacı kesitleri aynen alındı.
3. **Alın sacı.** ~15 cm: kenar hadvesinden saçak altının 6 cm altına, köşede dereyi içine alacak kadar; kesin ölçü teyit bekler.
4. **Dere iç köşesi.** Cumba sağ deresi ön dereye iç köşede bağlanır. Köşede ayrı bir parça yok (Lokman'ın yakın fotoğrafı): kalkan saçak altı saçak sacının saçak altına dayanır, arada ince bir derz kalır. Köşedeki boşluk baş makasın duvar dışındaki ucu kaplanınca kapanır (Lokman, 26 Ekim: "baş makasların uçlarında hâlâ kaplanmamış alan var"; `Baş makas betopanı · saçak ucu`, 6 parça).
5. **Fuga derinliği.** Paftada yok; modelde 5 mm.

6. **Baş makas omegasının U dudağı** ~2 cm (ölçü verilmedi).

Teyit edilenler (25 Ekim): OSB yok, kalkan uç dolguları (artan betopandan), omega ölçüleri, alçıpan ve cam yünü dizilimi.

## PK-01 düzeltmesi (bu oturum)

PK-01 rehberinde makas kartında eksik virgül vardı (`['Profil', …] ['Kart ölçüsü', …]`); makasa dokununca kart açılmıyordu.
- `2026-10-24_montaj_rehberi/rehber/template.html` düzeltildi.
- Kart satırı süzgeci `r && r[1]` yapıldı.
