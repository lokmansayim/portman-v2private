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
