# TS-01 · Diamond 45 m² (Ramazan Batmaz) · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4, pafta kipi)

- **Sıra kanıtı:**
  1. Kendi listemiz `f12cdd6` (13 Ekim 2026 14:57:39 +03).
  2. Mac'te mühür denetimi 14:57:42 (`dcfd289b…0b4`, mühürle aynı).
  3. Açılış 14:57:49.
- **Gerçek liste:** `gercek/DIAMOND_45M2_YUKLEME_LISTESI.pdf` ("PORTATİFEV YÜKLEME LİSTESİ"; Ubeydullah Özer, 31.07.2026), 137 satır, hepsi dolu. Okunmuş hali `gercek/TS01_gercek.json`.
- **Bizim liste:** `TS01_liste.json` / `.xlsx`; üreteç sürüm 7.3, pafta kipi; 125 satır.

## Özet (137 gerçek satır)

| Sonuç | Satır | Not |
|---|---|---|
| Varsayılan adetle aynı | **81** | panolar 20 / 21, köşeler, köşebent, kolon D, 3'lü H standart, çektirme 60, pencere karkası, alın, 100'lük alt çerçeve, ters mahya, tavan ve duvar alçıpanı 4 / 4, Boardex, dere, kapı menteşeleri, dübel, şase, vidaların 7'si, elektriğin 15'i (göz sayımı birebir; W otomat 8), tesisat 7, boya 7 |
| Toplam aynı, ayrım farklı | 7 | dış H 16 (gerçekte 7 + özel F + 7 + özel A); dış 3'lü H 4 (2 + özel C + 1) |
| Pafta sütunu tuttu | 7 | H standart 3, baş makas betopanı 6, makas 13, OSB 27, metal kiremit 1950 × 6 ve 1080 × 4, **iniş 7** |
| Aday sütunu tuttu | 8 | baş makas omegası 7 (saçaklı), 60'lık alt çerçeve L 2500 × 5, çatı izolasyonu 6, 5,5 × 60 500, vitrifiye 4 satır × 1 |
| Girdi / okuma farkı | 4 | sundurma kirişleri 1200 × 2 ve 1155, A–B kirişi 2800 (paftanın 4. sayfasında yoktu, kesik çizgiden okunmalıydı); 100'lük duvar omegası 2 |
| Kural farkı | 30 | aşağıda |

**Doğru toplam 103 / 137** (aynı + ayrım + pafta + aday). Önceki en iyi sonuç PK-07'de 68 / 134'tü.

Bizde fazla:
- profil vidalama aparatı (listede satırı yok);
- ayrıca "çatı müdahale kapağı" (listede yalnız "acil müdahale kapağı" var);
- boş "panel kapaması" satırı.

## Kural farkları (30 satır)

### Lokman'ın 13.10 cevaplarıyla çelişen ya da onları sınayan

1. **İniş 7: paftadaki daireler.** R3 (4 köşe + iki saçak ortası + parça başına 2) 10 verdi.
   - Bu listede orta iniş yok. Arka saçak 8,1 m, ön saçak 4,5 m.
   - Açık dirsek 14, kapalı 7 ve iniş kelepçesi 14 iniş 7 ile birebir tutuyor (× 2, × 1, × 2).
   - Bu dört satır yalnız iniş sayısı yüzünden yanlış.
2. **60'lık alt çerçeve L 2500 × 5.** Lokman "her zaman 3750" dedi (R1). Bu 2026 Portatifev listesi 2500 yazıyor; aday sütunu tuttu.

### Yeni kural adayları

| Kalem | Gerçek | Bizim | Aday kural |
|---|---|---|---|
| Betopan kaplı karkaslı duvar | 2505 | 2500 | çelik karkas duvarda sipariş boyu net − 2,5 mm (modül katı kuralı J1 yalnız yapıştırma panoda); ad "BETOPAN KAPLI KARKASLI DUVAR (150×190 PENCERE)", ölçü 80 × 45 × 12 profil |
| Çektirme U'su 100 | 2 | — | karkaslı duvar başına 1? (PK-07'de 5, açıklanamamıştı) |
| 60'lık duvar omegası | 29 | 27 | paftadaki bütün eflatun hatlar (yatay 77,17 + dikey 7,65 + sundurma 2,4 = 87,2 m) ÷ 3,65 + 5 = 28,9 |
| 100'lük saçak omegası | 7 | 8 | açık parçanın (sundurma) saçağı sayılmaz: (18,8 − 3,2) ÷ 2,5 → 7 |
| Saçak sacı | 8 | 9 | ? (18,8 ÷ 2,3 = 8,2) |
| Baş makas Z'si | 7 | 8 | ? |
| Aşık | 32 | 31 | pafta 29 |
| Metal kiremit mahyası | 6 | 5 | |
| OSB mahyası | 6 | — | OSB'li çatıda metal kiremit mahyası kadar |
| Ters mahya kenar kutusu | 8 | — | ters mahya × 2 (E2 / E3: 1 → 2) |
| Mahya bandı | 5 | 2 | bütün mahyalar (6 + 6 + 4) × 2,8 ÷ 10 = 4,5 → 5 |
| Nem bariyeri | 59,16 m² | 70 | çatı alanı m², yuvarlamasız |
| Alçıpan destek straforu | 105 m² | 2 paket | birim m², duvar yüzeyi (bizde 108,1) |
| Metal iniş borusu | L 2500 × 7 + L 500 × 7 | L 3000 × 10 | metal iniş de 2500 + 500 |
| PVC doğrama | 1 / 2 / 1, "ALICIYA AİT" | satır 0 | alıcıya ait pencere listede adetle ve damgayla yazılıyor (3 satır) |
| PVC plastik betopan H'ı | 7 | 5 | |
| Alçıpan vidası | 2200 | 2250 | levha × 40, 100'e yukarı |
| Betopan ve kapı kolu vidası | 1300 | 500 | OSB'li çatıda çok daha fazla (E2 / E3 1500 / 1450) |
| 5,5 × 25 trapez vida (aşık + omega + köşebent) | 750 | — | **üreteçte satır yok**; aşık × 23, 50'ye yukarı (TS-01 750, E5 700, E2 1000 tutuyor) |
| NYM 3 × 2,5 / 2 × 1,5 | 95 / 75 | 130 / 100 | m² × 2,1 / × 1,67? (E5 49 m² 100 / 80) |
| Zil | 1 | 0 | paftada yok ama listede her zaman 1 |
| Buat kasa | 30 | 25 | ? |
| Silikonize mastik | 30 | 34 | |

## Ders

**Paftanın kendi sayısı varsayılandan iyi.** Pafta sütunu olan 13 satırın 9'unda pafta tuttu:
- H standart, makas, OSB, metal kiremit (2 satır), betopan, iniş, dış H, dış 3'lü H.

Tavan omegasında pafta sayımımız eksikti: dikey hatları saymamıştım. Lokman'ın 10:41 ilkesi de ("montaj paftası varsa kesinlikle uygulanmıştır") bunu söylüyor.

**Öneri:** pafta kipinde pafta sütunu dolu satırlarda varsayılan pafta değeri olsun; kural sütunu adaya geçsin. Bu, protokol §5'in değişmesi demek; Lokman'a soruldu.
