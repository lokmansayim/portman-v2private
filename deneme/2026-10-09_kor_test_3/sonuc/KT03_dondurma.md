# KT-03 · dondurma kaydı

Kendi listemiz, klasördeki yükleme listesi açılmadan önce burada donduruldu. Bu dosyanın girdiği commit'in tarihi kanıttır: yükleme listesi o commit'ten sonra açılır.

Dondurma: 9 Ekim 2026, gece yarısından hemen önce (bu dosyanın girdiği commit'in saati kanıttır; +03).

## Açılmayan dosyalar

İkisinin de yalnız boyutu, değiştirilme tarihi ve özeti (SHA-256) alındı (9 Ekim 2026, 23:02 +03; Lokman'ın Mac'inde, bağlı klasörde). İçerikleri okunmadı. Dosya adları müşteri ve bayi adı taşıdığı için yazılmadı.

| Dosya | Boyut | Değiştirilme (UTC) | SHA-256 |
|---|---|---|---|
| Gerçek yükleme listesi (Excel) | 28 331 bayt | 2026-10-07 04:49 | `6974f6a6cc6bfc3ffd0f6ac98284f5b42429d9f2af64bb69032e2ca3fe5c30f3` |
| Aynı listenin PDF'i | 174 391 bayt | 2026-10-07 04:49 | `1193ec24fc206127a660f49bdf72b4dfd80de3806e6b07d5294731e6a3812925` |

Kıyas başlarken iki dosyanın özeti yeniden alınır; bu satırlarla aynı olmalıdır.

## Dondurulan dosyalar

| Dosya | İçerik | SHA-256 |
|---|---|---|
| `KT03_pafta_sayimi.json` | Elektrik paftasından sayım | `bd383584ee17348867b8d082f7bbf3a9b2e2f03dff812dc99ce17d10adac5f98` |
| `KT03_B_girdi.json` | Metraj girdisi, yöntem B (yapıldığı gibi) | `6390b20ffdb6a12c0ddd397ca489131ee9f2bf5b5a69312d23568a1523fc60bb` |
| `KT03_B_yukleme.json` | Yükleme listemiz, yöntem B, 96 satır | `69dfc56e78108f70f4ea86aea96bea3c6555424f393f412daaa72e086b0cb8f5` |
| `KT03_B_yukleme.md` | Aynı liste, okunur tablo | `94cb1aa06c33a17010e79c388149cb95770c4943cc1e61ef33210733293dd5e9` |
| `KT03_A_girdi.json` | Metraj girdisi, yöntem A (çelik standardı) | `3d511efbf440ca947e16f0be2b99a268c9d7547b1fac1374fd67f053221adfd6` |
| `KT03_A_yukleme.json` | Yükleme listemiz, yöntem A, 96 satır | `8a4f72f36fe44fc37d6b4fa2afc89f67daee5eb7f74ab78abdb48074cc85df5e` |
| `KT03_A_yukleme.md` | Aynı liste, okunur tablo | `a9e4751540ec3c2be9c0ec8a9896e07df82e6ce3f581b2cfeec35e199ce3bcfd` |

Depoda olmayanlar (müşteri projesinin geometrisi; Lokman'ın onayıyla girer): `KT03.json` (tanım) `342f17385838e933182d40dea75b3812c8ad082bb9c5aea294bf20cc4bc8aaae`; `kt03_tanim_uret.py` `085ce076d9f51943d702df78be4b428dbf413c2328227257bd77aa60dc4c0d8c`; çizim seti (iki yöntemle, 12'şer çıktı).

Kaynak dosyanın özeti (girdi): montaj paftası (PDF, yedi sayfa) `78f3314e5f9fa9914e0277d44e6938eed4fe69d25ed4dbec5f348528fe9c473d` (2 273 714 bayt, 2026-10-07 04:48 UTC). Üretim dosyası yok.

Dondurmadan hemen önce iki girdi ve iki liste, bu commit'teki kodla tanımdan yeniden üretildi (`kt03_kos.sh`): bayt bayt aynı.

## Girdi olarak kullanılanlar

- Montaj paftası: müşteri onay paftası (plan, mahal adları ve alanları, doğrama etiketleri, teknik özellikler, açıklama notları 1–7, pencere detayı), duvar paneli yerleşimi (yerler, ölçü zincirleri, veranda ve sundurma kesitleri, notlar), makas ve dere yerleşimi (makasların ve çatı panellerinin yeri, çatının biçimi), elektrik yerleşimi (sayılar).

## Girdi olarak kullanılmayanlar

- Yükleme listesi (PDF ve Excel; açılmadı).
- Paftalardaki adetler: çatı kaplaması, tavan omegası, aşık, dere inişi. Kıyasta ikinci ölçüt olarak kullanılacak. Makas ve dere paftasına çatının biçimi için bakıldı; verandanın çatısındaki iniş işaretleri girdi yapılmadı (README, karar 3).

## Kararlar

Liste öncesi kararlar ve motor değişiklikleri: `../README.md`.
