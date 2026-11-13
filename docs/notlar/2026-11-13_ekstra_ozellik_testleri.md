# Prefabrik ekstra özellik testleri · keşif ve gerçek listelerle kıyas (13 Kasım 2026)

Dayanak: Lokman, 13 Kasım 2026 21:44:01 UTC: "tüm prefabrik projelerinin iç duvarlar 100'lük çatı Sandviç yükseklik 280 gibi tüm
testlerini çıkar ve anlamlı kurallar bul ve sonuç doğru çıkana kadar test et"; 21:44:21 UTC: "yani ekstra ne kadar özellik varsa hepsini
test et". İş emri `docs/is_emirleri/BK-29.md` › Ek iş. Test `testler/motor/test_ekstra_ozellikler.py`.

Bu not ölçümdür, karar değildir. Buradaki hiçbir kural adayı koda, kural kitabına, hedef örneğe ya da fiyat eşlemesine işlenmedi; kural ve
hedef örnek yalnız Lokman'ın onayıyla değişir (D-02). Kaynak dosyalar PF `Ekstra_Ozellik_Testleri/` (çalışma notu) ve PF
`Prefabrik_28_Olcum/` (ev başına kör kıyas tabloları; gerçek değerler depoya girmez).

## Yöntem (hepsi `main` 5eaa39f0 + PR #180 üstünde, 13 Kasım 2026 22:10–22:40 UTC)

1. Dokuz havuz evi (PA-01 … PA-08, PA-06C) × 13 özellik: İş Emri'ne yalnız özelliğin anahtarı yazıldı, `motor/prefabrik_liste.is_emrinden`
   listesi tabanla kıyaslandı.
2. Aynı matris fiyatla: `araclar/fiyatla.fiyatla`, CRM eşlemesi (sahte anlık görüntü, `testler/test_crm_fiyat.sahte_anlik`) ve Kasım defteri
   (`kurallar/fiyat/defter_2026-11.json`, yön için).
3. Aynı matris ön onay çizimiyle: `motor/dxf_out.uret` (10 ev, PA-06K dahil).
4. Gerçek projeler: `testler/kor/projeler/*/is_emri.json`'dan bugünkü Motor'la liste (25 ev) ve PF'deki kıyas tablolarının gerçek satırları
   (31 ev); özelliğe özgü satırlar yan yana.

## A. Havuz evlerinde tutan kurallar (9/9 ev; testte sabit)

- Çatı rengi ve pencere rengi listeyi değiştirmez.
- Yükseklik 280 ve 300: boy taşıyan her satır (pano, köşe direği, H, üçlü H, kolon) aynı adetle yeni boya geçer; pano sayısı aynı.
  Pencere üst paneli 250'de 500, 280'de 800, 300'de 1000 mm (pencere üst kotu 200 cm). Çektirme U'su boy − 60 mm. İniş borusunun 500'lük
  parçası iki tane.
- İç duvar 100: pano sayısı aynı; 60'lık iç duvar kalemi kalmaz; çatı, dere ve elektrik grupları değişmez.
- Çatı kaplaması: yalnız Çatı ve Vida grupları değişir. Tek kat panel ve kiremit desen sacın örtüsü trapez sacla aynı yerde aynı adet.
- Ters tavan: asma tavanın üç satırı çıkar, ters tavan omegası girer. Alçıpan: beyaz ve yeşil duvar alçıpanı ile destek straforu girer.
- Bileşim: çatı kaplaması (sandviç, tek kat) ile yükseklik 280, iç 100, ters tavan ve alçıpan aynı satıra dokunmaz (8 ikili × 9 ev).

## B. Bugün çalışmayan ya da eksik çıkan yerler

1. Dış duvar 160 havuz evinde yalnız anahtarla açılmıyor (0/9): İş Emri "Sınır aks üstünde değil" diye durur. Evin sınırları 100'lük
   duvara göre yazılı; 160 için plan yeniden kurulmalı.
2. PA-06K (kırma çatı seçeneği): plan ve çatı görseli var, yükleme listesi yazılamıyor ("iki uçlu kırma: mahya y boyunca").
3. 280 ve 300'de fiyat eşlemesi eksik: 280'de 14–23, 300'de 19–27 satır "defterde yok" (pano bantları yalnız 2500; 2800'de TK-05'in
   birkaç kalemi var). Teklif toplamı 280'de 250'dekinden düşük çıkıyor: Kasım defteriyle −37.000 … −111.000 TL (300'de −84.000 …
   −182.000 TL).
4. Kiremit desen sac: "Panel kapaması L 2500" satırının adedi yok (kural yok).
5. OSB + membran + shingle: liste kuralı yok; kaplama tek kat panel gibi sayılıyor, shingle ve membran satırı yok.
6. Sandviç panelde PA-03'ün (AP-09 modeli) veranda çatısının örtüsü listede yok; ana çatının örtüsü trapezdekinden 1 fazla.
   AP-09'un gerçek listesinde veranda örtüsü ayrı satırdır (değerler PF `Ekstra_Ozellik_Testleri/calisma_notu.md`).
7. Fiyatı açık kalemler: tek kat ve sandviç panel örtüsü (birim varsayımı onay bekliyor), nem bariyeri önerisi, alçıpan destek straforu.

## C. Gerçek listelerle kıyas (özelliğe özgü satırlar)

| Konu | Proje sayısı | Sonuç |
|---|---|---|
| 280: pencere üst paneli 100 × 1250 × 800 | 2 (AP-12, AP-28) | 2/2 tutuyor |
| 280: çektirme U'su 2740 | 2 | 2/2 tutuyor |
| 280: kolon boyu | 2 | 0/2 tutuyor; gerçek boy bizimkinden kısa (bizde 2800) |
| 280: iniş borusu | 2 | 0/2 tutuyor; gerçekte tek uzun parça, bizde L 2000 + 2 × L 500 |
| 250: kolon boyu | 20 | 17 projede 2500 (tutuyor), 3 projede daha kısa |
| Sandviç: örtü adedi | 4 (AP-05, AP-09, AP-21, PK-02) | 2/4 tutuyor; ikisinde bizde 1 fazla |
| Sandviç: kapama | 4 | 1/4 tutuyor; üçünde bizde 1 fazla |
| Sandviç: düz mahya L 2800 | 4 | 4/4 tutuyor |
| Ana çatı örtü adedi (her kaplama) | 23 | bugünkü kural (yüz başına yukarı) 13/23; öteki aday (iki yüz toplam yukarı) 14/23; biri ya da öteki 18/23 |
| Örtü boyu | 23 | gerçekte çoğunlukla 50 mm'nin katı; bizde eğik boy + 5 cm, 10 mm'ye yukarı; fark 10–40 mm |
| Ters tavan omegası | 22 | 1/22 tam tutuyor; fark −12 … +19; tavan m² ile sabit oran da tutmuyor (0,57–0,82) |

Tutmayan satırların gerçek değeri depoya girmez (Lokman, 23 Ekim 2026, kart "Yalnız tutanlar"); değerler PF `Ekstra_Ozellik_Testleri/calisma_notu.md` ve
`Prefabrik_28_Olcum/`'dedir.

Okuma: 280'in kolon ve iniş borusu satırlarında veri bugünkü kuraldan farklı bir yön gösteriyor (iki proje). İniş borusu BK-25'in (D-60)
kuralı; değişmesi Lokman'ın kararıdır. Ana çatı örtü adedi, örtü boyu ve ters tavan omegasında veriden tek kural çıkmadı (11 Kasım
ölçümünün sonucuyla aynı yön: iniş, aşık ve dere kapağında da çıkmamıştı).
