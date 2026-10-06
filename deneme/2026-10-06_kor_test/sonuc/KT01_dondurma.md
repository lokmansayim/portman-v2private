# KT-01 · dondurma kaydı

Kendi listemiz, klasördeki gerçek liste açılmadan önce burada donduruldu. Bu dosyanın girdiği commit'in tarihi kanıttır: gerçek liste ve Excel hesaplama motoru o commit'ten sonra açıldı.

Dondurma: 6 Ekim 2026, 22:45 (+03).

## Açılmayan dosyalar

İkisinin de yalnız boyutu, değiştirilme tarihi ve özeti (SHA-256) alındı (6 Ekim 2026, 22:38:57 +03). İçerikleri okunmadı. Listenin dosya adının başındaki ad maskelendi.

| Dosya | Boyut | Değiştirilme (UTC) | SHA-256 |
|---|---|---|---|
| `… YUKLEME LISTESI.xlsx` (gerçek yükleme listesi) | 188 843 bayt | 2026-09-07 06:31 | `a7ff25e64bbee1c7a39961761bc4e11c0d82a8db0e251d4172029243d93a232b` |
| `CTKBF V1.1.xlsm` (Excel hesaplama motoru) | 93 755 bayt | 2026-09-27 16:43 | `f22eb38b8a6ce0b97b7c201eddf902437ddb56e47f2f75d895f70db8806f4587` |

Kıyas başlarken iki dosyanın özeti yeniden alınır; bu satırlarla aynı olmalıdır.

## Dondurulan dosyalar

| Dosya | İçerik | SHA-256 |
|---|---|---|
| `KT01_girdi.json` | Metraj girdisi (modelden) | `d00f77505b2d25db58aab571a747f1af5af585005e2fb056b2b2557f4d13ec9b` |
| `KT01_yukleme.json` | Yükleme listemiz, 80 satır | `8ff2af385a94d35c49ae53a768f52c012df2d34c02240e97f38c45c266f31c83` |
| `KT01_yukleme.md` | Aynı liste, okunur tablo | `4d89b2877c804fac0ebf18db3ca5e8c190e369ba15bf0b30c06314e7e0cc15d0` |

Model tanımı (`KT01.json`, depoda değil): `011ce9a42831d0db36ea814e3510eae489543581adfb362d884c3ee081185bb7`.

Dondurmadan hemen önce girdi ve liste, bu commit'teki kodla tanımdan yeniden üretildi: liste (JSON ve tablo) bayt bayt aynı; girdide yalnız `kaynak` satırının metni farklı.

## Girdi olarak kullanılanlar

- DWG: zemin kat planı (duvarlar, mahal adları ve alanları, doğrama ölçüleri), teknik özellikler ve açıklama notları (1–10).
- SKP: karkas modeli (duvar panellerinin yeri ve yüksekliği, makaslar, kirişler, çatı yüzleri).

## Girdi olarak kullanılmayanlar

- Gerçek yükleme listesi ve Excel hesaplama motoru (açılmadı).
- Montaj paftalarındaki adetler: çatı kaplaması, tavan omegası, aşık, dere inişi. Kıyasta ikinci ölçüt olarak kullanılacak.

## Kararlar

Kuralların söylemediği on beş durumun kararı listeden önce verildi; `../README.md` içinde "Liste çıkmadan önce verilen kararlar" başlığında yazılı.

## Listenin özeti

- Çelik: 52 panel, 1 995 kg (dış 9 · iç 6 · müştemilat 3 · korkuluk ve giriş çerçevesi 3 · baca 4 · dikme 1 · kiriş 3 · makas 16 · ek yapının çatı paneli 1 · boy C profil 6).
- Metal aksam: saçak sacı 14 · saçak omegası 14 · alın sacı 13 · tavan omegası 34 · aşık 50 · köşebent 67.
- Dış cephe: Boardex 53 · nem bariyeri 140 m².
- İç cephe: duvar alçıpan beyaz 56, yeşil 7 · tavan alçıpan beyaz 26, yeşil 6 · iç duvar OSB 64 · duvar izolasyonu 14 paket.
- Çatı: sandviç panel 33 (L 5072 × 16, L 3421 × 6, L 2874 × 5, L 2345 × 6) · mahya 5 · sandviç panel kapaması 14 · ters mahya 2 · duvar dibi sacı 5 · mahya bandı 2 · çatı şiltesi 10.
- Dere: metal dere 8 · iniş 7 · açık dirsek 14 · kapalı dirsek 7 · iniş kelepçesi 14 · dere kapağı 6 · dere kelepçesi 64.
- İç kapı: 3 (90 × 214 iki adet, 80 × 214 bir adet).
- Elektrik, vida ve sarf: listedeki gibi (ör. duy 7, tekli priz 17, NYM 3 × 2,5 182 m; alçıpan vidası 6 000, OSB vidası 3 000).
- Listede olmayanlar (alıcıya ait): dış kapı, pencere, boya, vitrifiye, sıhhi tesisat.
