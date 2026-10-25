# Devir · Render işi (köşe direkleri ve evin tamamı) · 24 Ekim 2026

Dal: `claude/montaj-rehberi-devir`. Dosyalar: `deneme/2026-10-24_montaj_rehberi/` (`rehber/`, `render/`). Deneme; canlıda değil.

## Nerede kaldık

- **Montaj rehberi** (Lokman'ın özel claude.ai artefaktı, https://claude.ai/artifact/QYQ2NEmwNBjuYrwqGxdhXH, sürüm 8):
  - 17 adım; oda oda dizilim; her parça kimlik kartına bağlı; aşık ve tavan omegası animasyonlu.
  - Artefaktta başlık gerçek proje adıyla. Depodaki şablonda `__PROJE__` var: `uret.py --proje …`.
- **Köşe render'ı tamam** (`render/gorsel/kose_render.png`). Lokman "çok güzel olmuş" dedi ve evin tamamını **aynı ayarda** istedi.
  - İçerik: B-01 13 × 13 ve B-02 9 × 9, dışarıdan ve oda tarafından; Blender Cycles 64 örnek.
- **Ev render'ı:**
  - Hat kuruldu: rehber → `export.js` → GLB → `ev_render.py`.
  - Yarım çözünürlükte, 16 örnekli denemeler var: `ev_test_on`, `ev_test_kalkan`, `ev_test_detay`.
  - **Son render'lar alınmadı**: 1600 × 1000, 64 örnek, görünüm başına 4–6 dk.

## Bu oturumda Lokman'ın düzeltmeleri (24 Ekim, rehbere işlendi)

- **Köşe direkleri.** Kanat = duvar kalınlığı + 3 cm.
  - Dış köşe 13 × 13 (10'luk, B-01): dış köşeler ve veranda iç köşesi.
  - İç köşe 9 × 9 (6'lık, B-02): 6 cm iç duvarın oda içindeki köşesi (yatak 1 / banyo).
  - Biçim aynı; sac 1 mm.
- **Saçak sacı.** Saçak omegasından sonra, makaslardan önce takılır (adım 10). Profil: tırnak 3 → saçak altı 30 → alın 13 → kıvrım 10.
- **Alın sacı.** Saçak sacıyla **birebir aynı profil**, kalkanda eğim boyunca. Tırnak baş makasın üst başlığına girer.
- **Dereler binayla birlikte iner.** Örnek: Lokman'ın verdiği tedarikçi, https://www.eksizoluk.gen.tr/galvaniz-oluk.html (galvaniz eksiz oluk; iniş Ø70 ya da Ø100).
  - Uygulanan: K kesit 15 × 11,4 cm (38'lik açınım), sırtı alına asılı, iki ucunda kapak.
  - Her inişte listedeki takım: iniş aparatı, 2 açık dirsek (kaz boynu), boru, 2 kelepçe, kapalı dirsek.
- **Diğerleri.** İç duvar H'leri kulaksız. Pencereler ve dış kapı modelde. Pres panel 8 mm betopan + EPS + 8 mm betopan.

## Claude'un varsaydıkları (Lokman'ın teyidini bekliyor)

- 6'lık köşede iç kanat 8,5 cm (13'lükteki 12,5'in karşılığı).
- Saçak sacı kıvrımı 10 cm (nottan okundu).
- **Kalkan köşe dolguları.** Paftadaki 4 betopan 51–548,7 cm arasını kapatıyor. Köşedeki 51 cm'lik üçgenler için kesimden birer parça eklendi (kartında "paftada yok, teyit bekliyor").
- Kalkan betopanı baş makasın dış yüzünde ve üst başlığı da kapatıyor.
- Uçtaki inişler, paftadaki dere ucundan köşeye 12 cm yakın duvar üstüne alındı.
- Makas çubuk kesiti yönü (Alpha Mini devrindeki madde 4).
- Lokman dere için bir fotoğraf göndereceğini söyledi; gelirse oluk ve iniş ona göre düzeltilir.

## Açık görsel kusurlar (son render'dan önce)

1. Saçak sacının kalkan ucu açık görünüyor (köşede koyu dikdörtgen). Alın sacıyla köşe birleşimi kapatılmalı.
2. Camlar koyu. İç mekân boş olduğu için normal, ama ön cephede hafif yansıma istenebilir.
3. Ufuk çizgisi: zemin ile arka plan geçişini yumuşatmak gerekebilir.

## Nasıl koşulur

1. **Sayfa:** `python3 rehber/uret.py <SP>/montaj-rehberi.html`.
2. **GLB:** `<SP>/t` içinde `npm i three@0.160.0 playwright`, sonra `node render/export.js <SP>` → `<SP>/render/huma.glb`.
   - Betik malzemeleri renkten tanır. `BASE` renkleri değişirse `export.js`'teki kopya da güncellenir.
3. **Render:** `v/bin/python render/ev_render.py <görünüm> çıktı.png 64 1.0`. GLB betiğin klasöründe aranır; `huma.glb`'yi `render/`'a koy.
   - Görünümler: `on_sag`, `arka_sol`, `catisiz` (çatı adımları 9–16 gizli), `kalkan`, `detay`.
   - Işık: güneş + gri gradyan ortam. Malzemeler köşe render'ıyla aynı.
4. **Köşe:** `kose_render.py <dis|ic> <disaridan|iceriden> çıktı.png 64`, sonra `pafta.py`.
   - Etiket noktaları için `NORENDER=1` ile koşulur. Görünüm katmanı güncellenmeden kamera izdüşümü yanlış çıkar; betikte düzeltildi.

## Sıradaki adımlar

1. Açık görsel kusur 1 düzeltilir; artefakt güncellenir (artefakt başlığındaki ad Lokman'a sorulmadan değiştirilmez).
2. Üç son görünüm alınır (`on_sag`, `arka_sol`, `catisiz`). Köşe paftası gibi tek, etiketli bir pafta yapılır.
3. Render'lar rehbere eklenir ("render'lı montaj rehberi"): genel bakışta galeri, son adımda bitmiş ev görseli. Bu, yayın işinin girdisidir (`2026-10-24_Rehber_Yayin_Devri.md`).
4. İstenirse adım başına render (ör. oda oda dizilimin üç karesi) ya da kısa animasyon.

## Güncelleme · 24 Ekim 2026 öğleden sonra (aynı oturum, kart 103)

**Yapıldı:**
- **Son render'lar alındı** (1600 × 1000, 64 örnek, görünüm başına ~3–4 dk): ön-sağ, arka-sol, çatısız, köşe (`kose_dere`) ve ortografik kalkan kesiti (`kalkan_kesit`).
- **Etiketli pafta:** `render/gorsel/ev_render_pafta.png`.
- **Galeri:** rehbere "Render görselleri" düğmesi ve galeri eklendi; görseller `rehber/gorsel/*.jpg`.
- **Artefakt:** sürüm 9; görseller artefaktın yan dosyaları (`gorsel/…`).
- **Lokman'ın 24 Ekim öğleden sonra düzeltmeleri işlendi:**
  - **Kalkan kenarı** (`render/gorsel/kalkan_kesit_cizimi.png`, Lokman'ın çizimi):
    - baş makas Z'si: makas ve betopan üstünden geçer, betopan yüzünden 3 cm çentikle iner, altta 3 cm dışarı kıvrılır;
    - alın sacı makas üstünün 3 cm altından başlar, tırnağı Z'ye girer;
    - C kapama aşık uçlarını kapatır;
    - alın sacının üstünde, saçak sacına ek olarak trapezin kenar hadvesini kavrayan bir kıvrım var.
  - **Çatı hadveleri** gerçek trapez kesiti oldu: taban 9, tepe 3, yükseklik 3 cm, ~25 cm aralık, iki kalkan kenarında birer hadve.
  - **Köşe** (fotoğraflar):
    - alın sacı aşağı iner ve derenin alnını kapatır, alttan düz kesilir;
    - saçak sacının saçak altı alın sacına kadar uzar, alnı ve üst kıvrımı makas topuğunda kesilir.
  - **Dere ve iniş:** dere antrasit boyalı K kesit; iniş dikdörtgen kesitli ve oluklu (~8 × 6 cm), antrasit, kaz boynu ve kelepçeyle binayla iner.
- **Lokman'ın kararı:** montaj rehberi ve render'lar ham malzemeyle kalır (betopan, galvaniz). Boyalı bitmiş görünüme (beyaz duvar, antrasit profil) "sonra bakarız".

**Kalan:**
- Bitmiş görünüm (boyama) ayrı iş.
- Teyit bekleyenler:
  - kalkan köşe dolguları;
  - 6'lık iç kanat 8,5 cm;
  - saçak kıvrımı 10 cm;
  - makas çubuk kesiti yönü;
  - köşede alın sacı alt ucunun yatay kesim yüksekliği (derenin altından, saçak altı hizası varsayıldı).

## Güncelleme · 24 Ekim 2026, 15:10 (adım adım render)

Lokman'ın seçimi: montaj dizilimi adım adım render.
- `render/adim_render.py`, 18 kare: genel bakış ve 17 adım.
  - Her karede o adıma kadarki parçalar görünür, o adımın yeni parçaları turuncu.
  - Kamera rehberin `preset()` açılarıyla aynı; 1280 × 800, 24 örnek, kare başına ~1,5 dk.
- Kareler `rehber/gorsel/adim/adim_NN.jpg`.
- Rehberde **Adımı render göster** düğmesi: açıkken her adımda o adımın karesi görünür; Oynat ile kare kare ilerler; tekrar basınca 3B'ye döner.
- Adım 12, 14 ve 16'nın metinleri Z, C kapama ve alın sacı ayrıntılarıyla güncellendi.
- Artefakt sürüm 10.
- Model değişirse kareler yeniden üretilir: `export.js`, sonra `adim_render.py 24 1.0`, sonra JPEG'e çevirme (`ev_pafta.py`'deki gibi).
