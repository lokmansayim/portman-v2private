# PK-03 · Doğan Prefabrik 80 m² (Nimet Bey) · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4, pafta kipi)

- **Sıra kanıtı:** kendi listemiz `022b0d3` (13 Ekim 2026 12:09:37 +03) → iki sürüm Mac'te mühürle karşılaştırıldı (12:09:43; `fe5948f5…3f04` ve
  `1a42996f…ad67` aynı) ve 12:10:02'de açıldı.
- **Gerçek liste:** 17 Eylül 2025 sürümü (montaj paftalarıyla aynı klasör), sayfa "PREFABRİK"; şablon **LOFTEV YÜKLEME LİSTESİ**, sevkiyat Keşan, 80 m².
  15 Eylül sürümünden farkı yalnız iki pano (60 × 1160 → 1220, karkaslı 1250 × 5 → 1250 × 4 + 1190 × 1). Okunmuş hali `gercek/PK03_gercek.json` (112 satır).
- **Bizim liste:** `PK03_liste.json` / `.xlsx` (üretici sürüm 3, **pafta kipi**: pano geometrisi paftanın vektörlerinden; varsayılan Portatifev).

## Özet

| Sonuç (gerçek listenin 112 satırı) | Satır | Not |
|---|---|---|
| _(ilk iki satır tek tek sayıldı; ötekiler sınıflamaya göre yaklaşık)_ | | |
| Varsayılan adetle aynı | 45 | panoların 12'si, köşe 6 + 3, veranda kirişleri 4920 / 2410 / 1155 ve kolon 2, H 60 ve 3'lü H 60, saçak ve baş makas omegası, alt çerçeve 100, makas 9, şilte 9, kapılar (çelik SAĞ 90 × 200; Amerikan 1 SOL + 4 SAĞ), pencereler, pencere vidası 120, elektrikte 12 |
| Aday sütunu tuttu | 5 | H kulaklı 10, çelik dübel 21, trapez vidası 750, köpük 2; aşık 49 pafta katmanında |
| Farklı: bizim kural hatamız | 13 | aşağıda "Bizim hatalarımız" |
| Farklı: karar (Portatifev ↔ Loftev) | 19 | baş makas Z'si 9, köşebent 5, saçak / alın sacı L 2800, 60'lık alt çerçeve L 3750, pencere U'ları, sandviç değil trapez vida takımı, boya, tesisat grubu … |
| Farklı: elle ya da göz sayımı | 18 | aşık 46 ↔ 49, tavan H'ı yok, iki pano boyu (1170, 635), anahtar 5 + 1 ↔ 4 + 2, NYM 150 / 120 … |
| Bizde yok (eksik) | 12 | ters mahya 4, trapez mahyası, yavru makas, menfez 2, alçıpan destek straforu 3, W otomat 9, sıhhi tesisat 7 satır |

**Pafta kipi işe yaradı:** 16 pano satırının 12'si birebir; kalan dördü iki modüllük pencere panosu (aşağıda, kural) ve iki boy yuvarlaması.
**D-13 menteşeleri paftadan okununca tuttu:** dış kapı SAĞ, iç kapılar 1 SOL + 4 SAĞ (listede de böyle). **Kulaklı H hipotezi üçüncü kez tuttu** (10).
**İç cephe alçıpanı (ilk tahmin)** 62 levha; gerçek 54 beyaz + 7 yeşil = 61.

## Bizim hatalarımız (sürüm 4'te düzelecek)

1. **İki modüllük pencere panosu** (160/180, 251'lik): listede tek satır "KARKASLI ÖZEL PENCERE PANOSU (160/180) 100 × 2500 × 2500"; biz üst + alt panel
   (2505) ve ayrı karkas yazdık. Sipariş boyu 2 × 1250.
2. **100'lük duvar omegası** çatı kenarına gelmeyen dış duvarlarda: salon önü 5,02 + mutfak yanı 1,16 = 6,2 m ÷ 2,5 → 3 ✓ (bizde "beşikte 0").
3. **Metal dere toplam ÷ 3,8** (Portatifev formülü): 17,7 m → 5 ✓; biz hat hat yukarı yuvarlayıp 7 dedik. PK-01'de ikisi de 6.
4. **Dere kapağı:** beşik 4 + çapraz beşik (cumba) başına 2 → 6 ✓ (kurallar.json'daki "besik_cumba: 6" doğruymuş).
5. **İniş:** paftada 6 (biz 9). Kısa veranda saçaklarında hat başına iki iniş fazla; cumba başına 2 iniş + ana çatı 4 → 6. Lokman'ın "9 m'yi geçen hatta
   orta iniş" kuralı burada uygulanmamış (arka saçak 10,1 m, orta iniş yok); PK-01'de uygulanmıştı → soru.
6. **Trapez çatıda mahya trapez mahyasıdır:** L 1000, 0,8 etkin → ana 13 + veranda 2 = 15 ✓ (biz metal kiremit mahyası 5 yazdık).
7. **Çapraz beşikte ters mahya (dere içi):** iki dere, her biri √(2,825² + 4,17² + 1,25²) ≈ 5,2 m → 10,4 ÷ 2,6 = 4 ✓.
8. **PVC plastik betopan H'ı tavan tipinden bağımsız:** ters tavanda da var (PK-02 ve PK-03'te 3; Portatifev 5).
9. **Duvar alçıpanı varsa alçıpan vidası** levha × 40, 250'nin katına: (20 + 6 + 54 + 7) × 40 = 3480 → 3750 ✓; ve **alçıpan destek straforu** yüzey ÷ 60 m² → 3 ✓.
10. **Veranda ters tavan omegası ayrı satır değil:** listede tek "60'lık duvar omegası" 39; bizim ana satır 40 tuttu (±1), ayrıca yazdığımız 6 fazla.
11. **Yavru makas:** veranda çatısının makasları "yavru makas L 5650" adıyla, paftadaki adet (MK10–MK12 → 3); biz 1 baş + 1 orta.
12. **Islak hacim alçıpanı:** bu listede mutfak da ıslak (yeşil 6 = (banyo + mutfak) × 1,05 ÷ 3 + 1); PK-02'de yalnız banyo (3) → karar sorusu.
13. **Trapez sac adedi** yarıma yuvarlanmış: 2 × 10,115 ÷ 0,8 = 25,3 → 25 (biz 26); sandviçte yukarı yuvarlama tutuyordu.

## Karar bekleyenler (Lokman)

PK-03 de Loftev şablonu; PK-02'de çıkan farkların çoğu burada da var (baş makas Z'si, köşebent, dübel, vida takımı). Yeni olanlar:
- Saçak ve alın sacı **L 2800** (PK-02'de 2500).
- 60'lık alt çerçeve **L 3750** (PK-02'de 2500).
- Dere **L 4000** (PK-02'de tek parça L 8500).
- İniş borusu özellikte metal yazdığı halde **PVC 2000 + 500**.
- Listede **sıhhi tesisat grubu** var (PK-02'de yoktu).
- Islak hacme mutfak dahil mi?
- 9 m'yi geçen saçakta orta iniş (PK-01 var, PK-03 yok).

## Motor için (genişletme iş emrine)

Paftadan okunan ama Motor'un çizemediği: 160/180 pencere ve iki modüllük pano, önde çıkıntılı L plan, çapraz beşik, ters / asma tavan ayrımı.
