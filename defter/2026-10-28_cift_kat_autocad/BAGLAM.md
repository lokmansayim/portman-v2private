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
- Git bulutta, Mac'e kopya (Lokman "evet devam et", 10:54). Silme izni yok; `.lock` ve kopya dosyalar kalır.
- Tam kontrol (fare/klavye) Lokman'ın isteğiyle (11:04); cihaz tarafı sıfırlanınca erişim yeniden istenir.
- **Kural (Lokman 12:09):** çift katta köşe direkleri 100×100 profil, pano dizilimi tek katla aynı (kural belgesi §12).
- **Blok adları:** Güncel Şablon 2024 kuralı (`<kalınlık>'LÜK <en>'LİK … PANO`; ondalık nokta, AutoCAD virgül kabul etmez). Yeni çizim: `deneme/2026-10-28_cift_kat/autocad/Portman_IE22-CK01_CIFT_KAT_sablon_bloklu_r01.dxf` (üretici `uret_cift_kat_bloklu.py`; yeniden koş: `python3 uret_cift_kat_bloklu.py` o klasörde).
- Referanslar: Şablon 2024 envanteri `autocad/sablon_inceleme/RAPOR.md`; Astra R02 `ref_prefabrik/cift_kat_R02/` (merdiveni yok); merdiven `autocad/merdiven/MERDIVEN_VARYASYONLARI.md`; pencere `autocad/PENCERE_VARYASYONLARI.md`.
- **Soru 1 kapandı (Lokman 12:34):** giriş kapısı sağ cephede, WC holünün sağ dış duvarında, 90, içeri açılır → `zemin_kat.json`'da `dis_kapi`, Motor yeniden üretti (validation True). Motor kapıyı kendisi çiziyor (`BOM_D18…_K02` rot 90); "Motor çizmedi (bulgu 7)" yanlış bulguydu, geri alındı (A025). **İE-22'de bulgu 7 yok.**
- AutoCAD'de açık sekmeler (12:57): Güncel Şablon 2024 (değişiklik işaretli, **kaydedilmeyecek**), sablon_bloklari_yapi_v2, R02 (salt okunur), yeni çift kat r01 (13:05 sürümü, kırmızı elle kapı yok).
- AutoCAD yolu: `Cmd+O` → **ekran görüntüsüyle kutunun açıldığı doğrulanır** → `Cmd+Shift+G` → yol → Enter → Open; komut satırına boşluklu yol yazılmaz; komut yazmadan önce doğru sekme doğrulanır (ERASE olayı A021, "Unknown command" olayı A025).
- `autocad/` klasöründe AutoCAD'in yazdığı `…r01.dwg` + `.bak` var (AutoCAD kendi yazıyor; git dışı). Kaynak DXF bulutla aynı. Silmek Lokman'ın.
- **13:00–13:15 kararları:** merdiven planın aynısı (kural belgesi 6.2–6.3; çizimde `merdiven_ciz`); dış kapılar şablonun kapılı pano çizimiyle (`sablon_kapili_pano`); köşeler şablonun `100X100 DIŞ KÖŞE DİREĞİ` bloğu (12 insert, aynalı); ölçüler iki ondalık virgüllü (dimrnd atıldı). Üretici: `python3 uret_cift_kat_bloklu.py` (autocad klasöründe), ~1 dk.
- Pano aksı ↔ plan ölçüsü çatışması (merdiven duvarları 337/557 vs 318,75/569,75) açık; Soru 9 ile birlikte karar.

## Açık sorular (sırayla sorulacak; cevaplar kural belgesi §12'ye)
~~1 giriş kapısı~~ (12:34) · ~~2 merdiven kutusu~~ ~~3 merdiven ölçüleri~~ (13:00 "aynı buradaki gibi": 200 iç, U, kol 100, 16 rıht) · **2b zeminde merdivene giriş (sırada)** · 3 merdiven ölçüleri · 4 Fransız pencere 120/200 · 5 çıkmanın çatısı · 6 ara kat ·
7 balkon taşması · 8 sürekli köşe profili · 9 706 / 710,25.
Ayrıca: "Şablon 2024" (150 MB `Guncel_Sablon_2024.dxf`, depoda değil, Lokman'ın klasöründe; K03 blok adları beklemede) — çizim mantığı
ne demek: katman/blok şeması mı, yoksa "kuralla çiz, sonra düzelt" sırası mı? Sırası gelince tek soru.
