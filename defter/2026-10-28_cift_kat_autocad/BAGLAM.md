# Bağlam · çift kat prefabrik, AutoCAD'de beraber çizim (28 Ekim 2026)

## Amaç (Lokman'ın sözleriyle)
- "Sıfırdan çift kat prefabrik çiziyoruz; el yordamıyla iş yapıyoruz." AutoCAD Mac'te açık.
- "Şablon 2024'teki çizim mantığını kullan: önce kuralları yeni bir AutoCAD sayfasında kullanarak çiz, sonra düzeltmeleri yapacağız."
- Kural belgesindeki 9 soru sırayla, tek tek sorulur; cevap belgeye tarihli yazılır. "Çiz" denince AutoCAD'de çizilir.
- Onaylanan kural → İş Emri JSON → Motor'la yeniden üretim. Teslim Motor'un DXF'idir; AutoCAD kuralı bulmanın yoludur (K02, D-12).

## Nerede ne var
- Dal: `claude/loving-ptolemy-s3j4oc` (git işleri **bulut kopyasında**; Mac'teki depo `main`'de, dosyalar oraya yalnız kopyalanır — Lokman silme izni vermedi, git kilit dosyası silemediği için dal Mac'te değiştirilmedi).
- Kural belgesi: `docs/sartname/cift_kat_prefabrik_kurallari.md` (§11 sorular; cevaplar §12'ye tarihli).
- İş emri: `docs/is_emirleri/IE-22.md` (plan; PR-1 onay bekliyor). Devir: `docs/devir/2026-10-28_IE-22_Devri.md`.
- Motor taslakları: `deneme/2026-10-28_cift_kat/sonuc/zemin_kat/Portman_IE22-CK01-ZEMIN_r01.dxf`, `…/birinci_kat/Portman_IE22-CK01-KAT1_r01.dxf` (cm). **Üstüne yazılmaz.**
- Yeni AutoCAD çizimi: `deneme/2026-10-28_cift_kat/autocad/` (ayrı dosya).
- Mac yolu: `~/Desktop/Claude Portman Çalışması/30_IE06/depo/`.

## Beş satırda kural (ayrıntı `kaynak_kopyalari/docs/cift_kat_prefabrik_kurallari.md`)
1. Çift kat = tek kat kuralları + merdiven. Döşeme ve çatı birebir aynı (Lokman 28.10).
2. Pano aksı 125,5 cm; yarım pano 62,75. Dış duvar 10 cm, iç 6 cm. Pano yüksekliği 250.
3. Bu ev: gövde 763 × 706; x 6 tam pano, y 5,5 pano (son pano önde 121,25 kesik). Dizilim arka-sol. Makas y'yi geçer.
4. Pencere üst kotu 200, eşik = 200 − boy; 120/125 → eşik 75. Dış kapı 90, iç 82, yükseklik 200.
5. Çatı beşik %33, saçak 30, topuk 10. Her pano ekinde H profili; dört kollu (+) birleşimden kaçınılır.

## Bugünkü Motor'un çizemedikleri (AutoCAD'de elle, PR-1 girdisi)
Merdiven çıkması (arkaya 125,5), merdivenin kendisi, balkonun 30 cm taşması, iki kat tek dosyada, ara kat, Fransız pencere 120/200.

## Karar verilenler (bu oturum)
- Git bulutta, Mac'e kopya (Lokman "evet devam et", 10:54).

## Açık sorular (sırayla sorulacak; cevaplar kural belgesi §12'ye)
1 giriş kapısı · 2 merdiven kutusu 2 / 1,5 pano · 3 merdiven ölçüleri · 4 Fransız pencere 120/200 · 5 çıkmanın çatısı · 6 ara kat ·
7 balkon taşması · 8 sürekli köşe profili · 9 706 / 710,25.
Ayrıca: "Şablon 2024" (150 MB `Guncel_Sablon_2024.dxf`, depoda değil, Lokman'ın klasöründe; K03 blok adları beklemede) — çizim mantığı
ne demek: katman/blok şeması mı, yoksa "kuralla çiz, sonra düzelt" sırası mı? Sırası gelince tek soru.
