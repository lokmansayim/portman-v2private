# Eylül 2026 uygulaması, 2025 tarihli üç gerçek listede

`sablon_eski_listeler.py` ile üretilir; elle düzeltilmez. Aynı satır / karşılaştırılan satır: gerçek listede adı aynı olan ve adedi hesaplanan kalemler.

Okuma: Eylül 2026 uygulaması 2025 listelerinde bugünkü kurallardan daha çok satır tutmuyorsa o listeler başka bir uygulamayla hazırlanmış demektir (hangi kalemlerin tutmaya başladığı, hangilerinin bozulduğu aşağıdaki tablolarda). Tavan omegası ve aşıkta şablonun formülü paftadaki toplam boy üzerinedir; örnek girdilerde pafta toplamı olmadığı için burada kuralın kendi toplamı kullanıldı. Paftalardaki toplamlarla (62 · 90 · 105 m²) şablonun formülü tavan omegasında 28 · 41 · 45 (listeler 26 · 40 · 44), aşıkta 44 · 62 · 78 (listeler 41 · 57 · 71) veriyor (`kurallar.json` → `tavan_omegasi_aralik_m`, `asik.zayiat`).

| Liste | Bugünkü kurallar | + Eylül 2026 uygulaması |
|---|---|---|
| 90 m² (Eylül 2025; beşik) | 15 / 29 | 14 / 29 |
| 62 m² (Eylül 2025; kırma) | 28 / 41 | 22 / 41 |
| 105 m² (Kasım 2025; beşik + cumba) | 31 / 49 | 31 / 49 |

## 90 m² (Eylül 2025; beşik)

| Kalem | Gerçek liste | Bugünkü kurallar | + Eylül 2026 | Sonuç |
|---|---|---|---|---|
| Aşık | 57 | 56 | 63 | uzaklaştı |
| Dayson | 6 | 6 | 3 | tutuyordu, bozuldu |
| Duvar izolasyonu | 18 | 18 | 19 | tutuyordu, bozuldu |
| Köşebent | 70 | 57 | 60 | yaklaştı |
| Saçak sacı (30'luk) | 14 | 15 | 14 | tutmaya başladı |
| Tavan omegası (60'lık) | 40 | 37 | 43 | aynı uzaklıkta, öbür yanda |

Katmanda adı değişen kalemler (adet aynı; karşılaştırma listedeki adla): Çatı şiltesi 80 mm → Çatı izolasyonu 100 mm.

## 62 m² (Eylül 2025; kırma)

| Kalem | Gerçek liste | Bugünkü kurallar | + Eylül 2026 | Sonuç |
|---|---|---|---|---|
| 230'luk kesme taşı | 5 | 5 | 2 | tutuyordu, bozuldu |
| Alçıpan vidası (3,5 × 35) | 4000 | 4000 | 5000 | tutuyordu, bozuldu |
| Aşık | 41 | 41 | 46 | tutuyordu, bozuldu |
| Duvar izolasyonu | 19 | 19 | 20 | tutuyordu, bozuldu |
| Köşebent | 50 | 39 | 42 | yaklaştı |
| OSB ve yalıpan vidası (3,9 × 32) | 3500 | 3500 | 4000 | tutuyordu, bozuldu |
| Sandviç panel kapaması | 16 | 16 | 15 | tutuyordu, bozuldu |
| Saçak sacı (30'luk) | 17 | 18 | 17 | tutmaya başladı |
| Tavan omegası (60'lık) | 26 | 26 | 32 | tutuyordu, bozuldu |

Katmanda adı değişen kalemler (adet aynı; karşılaştırma listedeki adla): Çatı şiltesi 80 mm → Çatı izolasyonu 100 mm.

## 105 m² (Kasım 2025; beşik + cumba)

| Kalem | Gerçek liste | Bugünkü kurallar | + Eylül 2026 | Sonuç |
|---|---|---|---|---|
| 230'luk kesme taşı | 7 | 7 | 3 | tutuyordu, bozuldu |
| Alçıpan vidası (3,5 × 35) | 8500 | 7250 | 9250 | yaklaştı |
| Dayson | 6 | 7 | 4 | uzaklaştı |
| Duvar izolasyonu | 38 | 39 | 41 | uzaklaştı |
| Köşebent | 85 | 70 | 73 | yaklaştı |
| OSB ve yalıpan vidası (3,9 × 32) | 1500 | 1000 | 1500 | tutmaya başladı |
| Tavan omegası (60'lık) | 44 | 42 | 48 | uzaklaştı |

Katmanın eklediği, bu listede olmayan kalemler: Ters mahya kenar kutusu (6).
