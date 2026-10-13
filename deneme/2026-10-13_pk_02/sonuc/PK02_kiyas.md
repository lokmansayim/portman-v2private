# PK-02 · Mehmet Balaban 58 m² · kendi listemiz ↔ gerçek yükleme listesi (kör test adım 4)

- **Sıra kanıtı:** kendi listemiz `d31c35c` (13 Ekim 2026 11:20:47 +03) → gerçek liste Mac'te mühürle karşılaştırıldı (SHA `9081e5e1…961f28` aynı, 11:21:08) ve 11:21:21'de açıldı.
- **Gerçek liste:** `gercek/MEHMET_BALABAN_58M2_YUKLEME_LISTESI.xlsx`, sayfa "PREFABRİK"; okunmuş hali `gercek/PK02_gercek.json` (95 adetli satır).
  Şablon **"LOFTEV YÜKLEME LİSTESİ"**, hazırlayan Büşra Nur Gürgün, **20 Kasım 2025**, sevkiyat Silivri. Formül sütunu yok.
  PK-01'inki "PORTATİFEV YÜKLEME LİSTESİ" (Ubeydullah Özer, 1 Ekim 2026): iki ayrı uygulama, aradaki farkların çoğu buradan.
- **Bizim liste:** `PK02_liste.json` / `.xlsx`, üretici sürüm 2 (99 satır; varsayılan, pafta ve aday sütunları).

Sınıflar PK-01'deki gibi: **girdi** (okuma / İş Emri hatamız) · **kural** (kuralımız yanlış) · **karar** (iki fabrika listesi farklı yapıyor; Lokman seçer) ·
**elle** (formülle açıklanamayan sevk adedi) · **eksik** (gerçekte var, bizde kural yok) · **pafta** (Motor çizimi paftadan farklı).

## Özet

| Sonuç (gerçek listenin 95 satırı) | Satır | Not |
|---|---|---|
| Varsayılan adetle aynı | 42 | panoların 10'u, köşe, H 60 ve 3'lü H 60, saçak omegası / sacı, alın sacı, makas 7, sandviç panel 17 × L 4300, mahya, dere takımının 5'i, pencereler, elektrikte 10 |
| Toplam aynı, ayrım aday kuralla tuttu | 2 | 3'lü H kulaklı 2 / dübelli 3 |
| Farklı: Motor çizimi paftadan farklı (pafta) | 6 | pano 820, 390, 60 × 1250, 310; H kulaklı / dübelli toplamı 18 ↔ 17 |
| Farklı: kural / girdi (bizim hatamız) | 12 | aşağıda "Bizim hatalarımız" |
| Farklı: karar (iki uygulama ayrışıyor) | 16 | aşağıda "Karar" |
| Farklı: elle ya da göz sayımı | 10 | aşık 35 ↔ 34, tavan H'ı 75 ↔ 73, dere kelepçesi 50 ↔ 48, 60'lık alt çerçeve 9 ↔ 8, betopan H'ı 3 ↔ 5, elektrikte 5 |
| Bizde yok (eksik) | 7 | baş makas menfezi 3, W otomat 9, vida: 5,5 × 25 / 5,5 × 60 / kesme taşı / çırpı ipi, pencere vidası (bizim hatamız) |

**Liste açılmadan yapılan üç düzeltme tuttu:** makas 7 (eski formül 8), aşık sırası yüz başına 8 (sandviç ve aşık boyları paftayla aynı), sandviç panel 17 × L 4300.
**PK-01'den çıkan hipotez tuttu:** kulaklı H = saçak duvarındaki (makas ayağının geldiği) ek. Gerçek 8 / 9 ve 2 / 3; bizim aday 8 / 10 ve 2 / 3 (10 ↔ 9 Motor'un fazladan bir ekinden).
**Pafta tuttu:** derinlik 739,25 (yan duvarın ön parçası listede 625; 745 olsaydı 680 olurdu).

## Grup grup

### 1001 Panel

| Gerçek | Adet | Bizim | Sonuç | Sınıf |
|---|---|---|---|---|
| 100'lük dolu 1250 / 625 | 15 / 2 | 15 / 2 | ✓ | |
| 100'lük dolu 820 | 2 | 0 (Motor: 830 + 420 + 385) | ✗ | **pafta** (Motor bulgusu 1: ortalanan pencerenin iki yanı) — paftanın panolarıyla 2 ✓ |
| 100'lük dolu 390 | 1 | 385 × 2 | ✗ | pafta (fazla parça) + **karar** (yuvarlama: 39 cm → 390; PK-01'de 37 → 365, 32 → 315) |
| Vasistaslı pano · pencere üst 4 · alt 2 + 2 · çelik kapı panosu | ✓ | ✓ | ✓ | |
| 60'lık dolu 1250 / 575 / 310 | 10 / 1 / 1 | 9 / 1 / 355 + 1200 | ✗ ✓ ✗ | **pafta** (Motor bulgusu 2: iç duvar dış duvarın iç yüzünden başlıyor); 31 → 310 yuvarlaması karar |
| 60'lık karkaslı + kasalı 1250 / 1220 | 2 / 2 | 2 / 2 | ✓ | |

Paftanın kendi panolarıyla (`pafta_kiyas.json`) 14 satırın 12'si tutardı; kalan ikisi yalnız yuvarlama (390, 310).

### 1002 Metal aksam

| Gerçek | Adet | Bizim (varsayılan · aday) | Sonuç | Sınıf |
|---|---|---|---|---|
| Köşe direği 100 × 100 | 4 | 4 | ✓ | |
| Köşebent | **3** | 0 · aday 7 | ✗ | **karar** (PK-01: 0; Portatifev şablonu "tek kat 7") |
| H dübelli & kulaklı / dübelli | 8 / 9 | toplam 18 · aday 8 / 10 | kulaklı ✓, dübelli +1 | pafta (Motor'un fazla eki); **hipotez tuttu** |
| H standart 60 · 3'lü H 60 | 9 · 3 | 9 · 3 | ✓ | |
| 3'lü H dübelli & kulaklı / dübelli | 2 / 3 | 5 · aday 2 / 3 | toplam ✓, ayrım ✓ | hipotez tuttu |
| Çektirme U'su 60 | 2 | 2 | ✓ | |
| Çektirme U'su 100 | **6** | 2 · aday 7 | ✗ | **karar** (aşağıda: pencere karkası) — 120'lik 4 pencereyle şablon formülü (2 × 480) ÷ 244 + 2 = 5,9 → 6 ✓ |
| 100'lük pencere U'su H geçen | **8** | 1 · aday 6 | ✗ | karar — 120'lik pencere başına 2 |
| Özel pencere karkası | **yok** | 2 + 2 | fazla | karar (PK-01'de hazır karkas 3 + 2 gitti; burada karkas U'larla yerinde) |
| 60'lık duvar omegası | **16** | 21 (L 55,8 m ÷ 3,65 **+ 5**) · pafta 19 | ✗ | **kural / karar**: "+5"siz ⌈55,8 ÷ 3,65⌉ = 16 ✓ (PK-01: formül 21, girilen 8) |
| Saçak omegası · saçak sacı · alın sacı | 7 · 8 · 8 | 7 · 8 · 8 | ✓ | |
| Baş makas omegası | **7** | 6 | ✗ | **karar** (saçakla 2 × 8,05 ÷ 2,5 = 6,4 → 7; PK-01 saçaksız 12 ÷ 2,5 → 5) |
| Baş makas Z'si L 2800 | **8** | 0 · aday 7 | ✗ | **karar** (PK-01: 0). Sürüm 1'in kuralı 4 × ⌈eğik ÷ 2,8⌉ = 8 ✓ veriyordu |
| Baş makas menfezi | 3 | — | eksik | |
| Baş makas betopanı | **6** | 4 | ✗ | **kural** — aday: kalkan başına ⌈1,5 × üçgen ÷ 3,125⌉ (PK-01 4 ✓, PK-02 6 ✓) |
| 100'lük alt çerçeve | **9** | 8 · aday 9 | ✗ | **kural** — şablon formülü (dış çevre ÷ 3,75) iki projede de tuttu |
| 60'lık alt çerçeve | **9** | 8 | ✗ | elle (iç duvar 18,4 m ÷ 2,5 = 7,4; 9 için ≥ 20 m gerekir) |

### 1005 · 1006 Makas, çatı · 1004 tavan

| Gerçek | Adet | Bizim | Sonuç | Sınıf |
|---|---|---|---|---|
| Makas L 8050 (300 kg) | 7 | 2 + 5 | ✓ | P1 düzeltmesi tuttu |
| Aşık L 4200 | 35 | 34 · pafta 33 · aday 38 | ✗ 1 | elle (16 sıra × 8,33 m = 133,3 m) |
| Sandviç panel 4 cm L 4300 | 17 | 17 · L 4300 | ✓ | P3 tuttu |
| Metal kiremit mahyası | 4 | 4 | ✓ | |
| Sandviç panel kapaması | **7 (L 2500)** | 0 · aday 7 | ✗ | **karar** (PK-01: 0) |
| Mahya bandı | — | 2 | fazla | karar (PK-01: 2) |
| Çatı şiltesi 80 mm | **7** | 6 · aday 7 | ✗ | **kural** — şablon formülü (30 cm paylı taban ÷ 9,6) tuttu; PK-01'de elle (formül 6,4, girilen 4) |
| Asma tavan beyaz alçıpan | **18** (net 46,47 m²) | 20 · aday 19 | ✗ | **kural** — şablon formülü aşağı yuvarlamayla 18 ✓ (46,06 × 1,05 ÷ 3 + 2 = 18,1) |
| Asma tavan yeşil alçıpan | **3** (net 7 m²) | 0 · aday 4 | ✗ | kural — aynı formül aşağı: 3,45 → 3 ✓ (ıslak hacim yeşil) |
| Tavan H'ı | 75 | 73 | ✗ 2 | elle / yakın |
| Omega kapak L 3750 | **11** | 14 (L ÷ 3,65 **+ 3**) | ✗ | kural / karar: "+3"süz 37,4 ÷ 3,65 = 10,2 → 11 ✓ (PK-01'de +3'lü tuttu) |
| PVC plastik betopan H'ı 60 × 3000 | 3 | 5 | ✗ | elle (şablon: "3 ile 5 arası") |

### 1011 Dere · 1003 kapı ve pencere

| Gerçek | Adet | Bizim | Sonuç | Sınıf |
|---|---|---|---|---|
| Metal dere **L 8500** | 2 (16,33 m) | L 4000 × 6 | ✗ | **karar** (tek parça dere) |
| İniş aparatı · dere kapağı · açık / kapalı dirsek · PVC kelepçe | 4 · 4 · 8 / 4 · 8 | aynı | ✓ | PK-01 dersi (kapak 4) tuttu |
| **Metal** iniş borusu L 3000 | 4 | PVC L 2500 + L 500 × 4 | ✗ | **kural** — özellik "Yağmur İniş Borusu: Metal"; PK-01'de PVC idi. Sürüm 1'in L 3000'i doğruydu |
| Dere kelepçesi | 50 | 48 | ✗ 2 | elle |
| Çelik kapı (SOL) **90 × 200** | 1 | 1 · 100 × 2000 · menteşe sol | adet ✓, yön ✓, ölçü ✗ | **girdi** — kanat yayı 100 çizilmiş; ölçü yaydan okunmaz (K04: 90) |
| Amerikan kapı 80'lik kanat SOL / SAĞ | 3 / 1 | SOL 2 + SAĞ 1 (82) + SOL 1 (100) | ✗ | **girdi** — salon kapısı da 82 × 196; D-13 menteşeleri 3 SOL + 1 SAĞ ✓ |
| PVC pencere 120/120 · 120/180 · 60/40 | 2 · 2 · 1 | aynı | ✓ | |

### 1009 Depo · 1008 vida · 1007 elektrik · 1012 boya

| Gerçek | Adet | Bizim | Sonuç | Sınıf |
|---|---|---|---|---|
| Çelik dübel | **22** | 0 · aday 23 | ✗ | **karar** (PK-01: şase pul 24, dübel 0); aday "dübelli H adedi" paftayla 22 ✓ |
| Şase pul · acil müdahale kapağı | — | 23 · 1 | fazla | karar |
| RYSB pul başlı | 500 | 0 · aday 429 | ✗ | karar (250'nin katına yukarı: 500 ✓) |
| Alçıpan vidası | 250 | 0 · aday 800 | ✗ | karar |
| 16 mm betopan ve kapı kolu | 500 | 250 | ✗ | karar |
| **Prefabrik pencere vidası 4,8 × 70** | 100 | — | eksik | **kural** — PK-01 dersi 9 fazla genellendi: pencere bizimse pencere × 20 (sürüm 1 doğruydu) |
| Trapez 5,5 × 110 (sandviç) | 500 | 400 | ✗ | karar (250'nin katı 500; PK-01'de 385 → 400) |
| Trapez 5,5 × 25 · 5,5 × 60 · kesme taşı · çırpı ipi | 750 · 250 · 4 · 1 | — | eksik | şablon formülleri 250'nin katıyla 750 · 250 · 1 ✓ verir |
| 8'lik uç · PH2 · inox taş | 4 · 4 · 6 | aynı | ✓ | |
| Tijli duy · uydu kablo · besleme 5 + boru 5 · çiftli anahtar · uydu prizi · zil · sigorta kutusu · izole bant · kaçak akım | ✓ | ✓ | ✓ | elektrik planından sayım tuttu |
| Yuvarlak glop / ampul | 1 / 5 | 8 / 12 | ✗ | **girdi** — dış aplikleri (7) saydım; listede yok |
| Tekli anahtar | 6 | 5 | ✗ | göz sayımı |
| Tekli / çiftli priz | 12 / 2 | 14 / 1 | ✗ | göz sayımı (toplam priz yuvası 16 = 16 ✓) |
| NYM 3 × 2,5 / 2 × 1,5 | 135 / 120 | 130 / 100 | ✗ | elle |
| W otomat 16 A | 9 | — | eksik | |
| Dış cephe boya · mastik · dayson · köpük | 1 ("fiyatlandırma için") · 60 · 4 · 2 | 2 · 44 · 1 · 0 (aday 2) | ✗ | karar / eksik |

## Bizim hatalarımız (varsayılan hesap düzelecek; protokol §5)

1. **Kapı ölçüsü kanat yayından okunmaz** (girdi): dış kapı 90, iç kapılar 82 (K04); yay 100 çizilmiş olsa da listede 90 × 200 ve 82 × 196.
2. **Dış aplik ışık sayımına girmez** (girdi): glop yalnız ıslak hacim; ampul = duy + glop.
3. **Pencere vidası:** pencere bizimse pencere × 20 (PK-01 dersi 9 fazla genellendi).
4. **İniş borusu özelliğe bağlı:** metal → L 3000 metal; PVC → L 2500 + L 500 (PK-01 dersi 7 yalnız PVC için).
5. **100'lük alt çerçeve = dış çevre ÷ 3,75** (iki projede de tuttu; bizim pano boyu toplamı 1 eksik verdi).
6. **Baş makas betopanı:** kalkan başına ⌈1,5 × üçgen alanı ÷ 3,125⌉ (PK-01 4, PK-02 6).
7. **Çatı şiltesi:** (en + 0,6) × (boy + 0,6) ÷ 9,6 (şablon formülü).
8. **Alçıpan:** kuru tavan × 1,05 ÷ 3 + 2 beyaz, ıslak × 1,05 ÷ 3 + 1 yeşil, **aşağı yuvarla** (PK-02 18 / 3 ✓; PK-01'de elle 8 / 0).
9. **Motor (pafta):** (a) ortalanan pencerenin iki yanı eşit iki parça olmalı; (b) koşu hizasında iç duvar dış duvarın iç yüzünden başlamalı. İkisi de Motor değişikliği; Lokman'ın onayıyla ayrı iş.

## Karar bekleyenler (Lokman)

PK-01 ile PK-02'nin listeleri iki ayrı uygulama: **Portatifev şablonu** (Ubeydullah, 1 Ekim 2026) ve **Loftev şablonu** (Büşra Nur, 20 Kasım 2025).
Aşağıdakilerin hepsi "hangisi güncel kural?" sorusuna bağlanıyor:

| Kalem | PK-01 (Portatifev) | PK-02 (Loftev) |
|---|---|---|
| Baş makas Z'si | 0 | 4 × ⌈eğik ÷ 2,8⌉ = 8 |
| Köşebent | 0 | 3 |
| Pencere karkası | hazır karkas (pencere başına 1) + U'lar sabit 2 / 1 | karkas yok; çektirme U 100 formülle (6), H geçen U pencere × 2 (8) |
| Sandviç panel kapaması | 0 | ⌈saçak ÷ 2,5⌉ = 7 |
| Dere | L 4000 parça (÷ 3,8) | tek parça (saçak boyunda, L 8500) |
| Dübel / pul | şase pul = dübelli H, dübel 0 | çelik dübel = dübelli H, pul yok |
| Omega formülündeki "+5" / kapak "+3" | var (kapak 10) | yok (omega 16, kapak 11) |
| Baş makas omegası | saçaksız kalkan (5) | saçaklı makas boyu (7) |
| Sipariş boyu yuvarlaması | 37 → 365, 32 → 315 (−2,5 mm, 5'e aşağı) | 39 → 390, 31 → 310 |
| Vida takımı | betopan 250, sandviç 400 | RYSB 500, alçıpan 250, betopan 500, trapez 750 / 250 / 500 (250'nin katları), kesme taşı 4, çırpı ipi 1 |
| Mahya bandı · acil müdahale kapağı | 2 · 1 (alıcıya ait) | yok · yok |

PK-01'in açık soruları (13 Ekim) PK-02 ile şöyle değişti: **soru 3 (kulaklı H)** iki projede de tuttu, kural olarak önerilir; **soru 1 (formül mü
girilen mi)** PK-02'de formül çoğunlukla tuttu (şilte, alçıpan, alt çerçeve), PK-01'deki sapmalar elle görünüyor; **soru 4 (elektrik)** planı olan
projede plandan sayım tuttu (10 / 18 tam, toplam priz aynı).
