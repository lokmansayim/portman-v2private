# KT-02 · dondurma kaydı

Kendi listemiz, klasördeki yükleme listesi açılmadan önce burada donduruldu. Bu dosyanın girdiği commit'in tarihi kanıttır: yükleme listesi o commit'ten sonra açılır.

Dondurma: 9 Ekim 2026, 21:40 (+03).

## Açılmayan dosyalar

İkisinin de yalnız boyutu, değiştirilme tarihi ve özeti (SHA-256) alındı (9 Ekim 2026, 21:38 +03; Lokman'ın Mac'inde, bağlı klasörde). İçerikleri okunmadı. Dosya adlarının başındaki ad maskelendi.

| Dosya | Boyut | Değiştirilme (UTC) | SHA-256 |
|---|---|---|---|
| `… 90 M2 YUKLEME LISTESI.xlsx` (gerçek yükleme listesi) | 186 835 bayt | 2026-10-07 04:54 | `551b7d6817e4924f6605596d9e003d3c7f78fe514faa98201163e885edd839e1` |
| `… 90 M2 YUKLEME LISTESI.pdf` (aynı listenin PDF'i) | 248 779 bayt | 2026-10-07 04:54 | `11b0d65959596c703a50e36692c3e306a10a65370c260fb3d77df57e56b97b06` |

Kıyas başlarken iki dosyanın özeti yeniden alınır; bu satırlarla aynı olmalıdır.

## Dondurulan dosyalar

| Dosya | İçerik | SHA-256 |
|---|---|---|
| `KT02_pafta_sayimi.json` | Elektrik paftasından sayım | `9131081446880a81e4aaddeab3259a673a46e8441e5a8fcb1e7afef28717881d` |
| `KT02_B_girdi.json` | Metraj girdisi, yöntem B (yapıldığı gibi) | `0a7960edb4f5f1ae0d5f1ee8d1902ab22145c68ee99ff5bb45d173ef37adc0b2` |
| `KT02_B_yukleme.json` | Yükleme listemiz, yöntem B, 84 satır | `cc300406e9c09e303bdc77f59a1ea7e3f18dcdc2cff8c4c510cc3fd73b699ed6` |
| `KT02_B_yukleme.md` | Aynı liste, okunur tablo | `291af1ff88aeaac7e9aaf2b153d389821835d83cf3cba30a109d6180e129e8d1` |
| `KT02_A_girdi.json` | Metraj girdisi, yöntem A (çelik standardı) | `9ca9caee4b05aa7dcd1d8d7eb51ae3b3872982aea35ae6a98d2225c7c40d5086` |
| `KT02_A_yukleme.json` | Yükleme listemiz, yöntem A, 84 satır | `1f01ecd1175f4f61fd2664a8e817c972391768cb4d3e02283c1603c60b8f5079` |
| `KT02_A_yukleme.md` | Aynı liste, okunur tablo | `56590d18f7c7849f830e4c4ea4037ef8b9cd7763fdcced4730bdf0e6edad547c` |

Depoda olmayanlar (müşteri projesinin geometrisi; Lokman'ın onayıyla girer): `KT02.json` (tanım) `37fdf1e77913b4a3165443b256cf2e5858e9df196a38e0a7ffd6b3bdf409ffbd`; `KT02_profil_boylari.json` (üretim dosyasından) `67d5fc441c1643184073745761e91c9efd4dc7a89a83fdd0f238914a1ee9c994`; `kt02_tanim_uret.py` `eb771bf727e57d9640fbdece29cf0697e715e5abbb45bdbf8ebd3f5801e9ae20`.

Kaynak dosyaların özeti (girdi): montaj paftası (PDF, 8 sayfa) `a407124bea0dd73c13d4f5a78b91aef1a1044015704e85206091d7b7accb871f`; çatı kaplama malzemesi (PDF; girdi değil) `1c12d5b93cba82adbc595aad79cfde3a2d698444ea26718863d385efd4e8b517`; üretim dosyası (ZIP, 101 CSV) `e622a288b018c2edb7e2ab197557341eb901a145b435c96afa2481c9ab02b693`.

Dondurmadan hemen önce iki girdi ve iki liste, bu commit'teki kodla tanımdan yeniden üretildi (`kt02_kos.sh`): bayt bayt aynı.

## Girdi olarak kullanılanlar

- Montaj paftası: müşteri onay paftası (plan, mahal adları ve alanları, doğrama etiketleri, teknik özellikler, açıklama notları 1–6), duvar paneli yerleşimi ile makas ve panel yerleşimi (yerler), elektrik yerleşimi (sayılar).
- Üretim dosyası: her çerçevenin üyeleri (boy, et kalınlığı, yer); açıklıkların yeri ve boyu.

## Girdi olarak kullanılmayanlar

- Yükleme listesi (PDF ve Excel; açılmadı).
- Paftalardaki adetler: çatı kaplaması, tavan omegası, aşık, dere inişi; çatı kaplama malzemesi paftası. Kıyasta ikinci ölçüt olarak kullanılacak. Dere paftasına yalnız sundurma çatısının biçimi için bakıldı.

## Kararlar

Liste öncesi kararlar ve motor değişiklikleri: `../README.md`.
