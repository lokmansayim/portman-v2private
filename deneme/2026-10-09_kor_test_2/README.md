# 9 Ekim 2026 · ikinci kör test (KT-02)

Deneme kodu; canlıda değil. İE-05 taslağının (`docs/is_emirleri/IE-05.md`) devamı. Genel model motoru ve hesap öteki klasörlerde: `../2026-10-06_kor_test/` (tanımdan girdi, çizim seti), `../2026-10-03_yukleme/` (yükleme listesi, kural seti).

Lokman, 9 Ekim 2026 21:07: "bir test daha yapalım". Aynı gün Mac'teki bir klasörü bu oturuma bağladı: içinde 90 m²'lik bir çelik projenin montaj paftası (PDF), çatı kaplama malzemesi paftası (PDF), üretim dosyası (rulo form makinesinin CSV'leri, ZIP) ve yükleme listesi (PDF ve Excel) var. KT-01'deki gibi: modeli kur, çizim setini ve kurallarımızla kendi listemizi çıkar, listeyi gerçek liste açılmadan dondur, sonra kıyasla.

Proje (KT-02): tek kat çelik, 2+1, 90 m² (paftadaki toplam brüt alan; veranda dahil); dört omuz çatı, sandviç panel; güneyde kolonlu ve korkuluklu veranda (ana çatının altında), batıda giriş kapısının önünde kendi küçük çatısı olan sundurma; yöntem B (tavan omegası ve aşık; paftada ikisinin de yerleşim planı var). Müşteri ve bayi adı kayıtlarda geçmez. Montaj paftasının tarihi Ağustos 2026.

## Kör test protokolü (KT-01'deki gibi)

1. Klasördeki yükleme listesi (PDF ve Excel), kendi listemiz üretilip depoya kaydedilene kadar açılmadı; yalnız boyutu, değiştirilme tarihi ve özeti (SHA-256) alındı (`sonuc/KT02_dondurma.md`).
2. Girdi: montaj paftasındaki müşteri onay paftası (plan, teknik özellikler, açıklama notları), duvar paneli yerleşimi ile makas ve panel yerleşimi (yerler), elektrik yerleşimi (sayılar) ve üretim dosyası (çerçevelerin boyları, açıklıklar, et kalınlığı). Paftalardaki adetler (çatı kaplaması, tavan omegası, aşık, dere inişi) ve çatı kaplama malzemesi paftası girdi olarak kullanılmadı; dere paftasına yalnız sundurma çatısının biçimi için bakıldı.
3. Kuralların kapsamadığı her yerde karar listeden önce verildi ve yazıldı (aşağıda).
4. Kıyasta her fark sınıflanır: girdi hatası · kural hatası · karar farkı · listenin elle yuvarlaması · paftadan sayılan kalem. Yalnız ilk ikisi hata sayılır.

## Girdi

- **Tanım** (`KT02.json`, Yapı Tanımı 0.5; `kt02_tanim_uret.py` üretir; müşteri projesinin geometrisi olduğu için depoya Lokman'ın onayıyla girer, şimdilik depo dışında; özeti dondurma kaydında). Duvarlar, kirişler ve kolonlar üretim dosyasındaki çerçeve boylarıyla, duvar paneli paftasındaki yerlerinde (paftanın vektör çizgileri duvarlarla ölçeklenerek okundu). Açıklıklar çerçevelerdeki dikme ve başlıklardan: 120/180 iki, 120/120, 120/100, 60/40, 300/200 (pencere ve doğramalar alıcıya ait); dış kapı 95 × 210; dört iç kapı 90 × 214 (banyo dahil). Mahallerin karkas yüzleri arası alanları paftadaki etiketlerle aynı: yatak odaları 14,32 / 14,26 · hol 7,09 / 7,08 · banyo 4,34 / 4,33 · yaşama mekânı 26,43 / 26,42 · sundurma 2,24 / 2,25 m².
- **Çatı:** dört omuz, saçak 30 cm (makas 8240 = karkas 764 + 2 × 30), eğim 0,32878 (makasların üst başlığı), saçak kotu 280. Plan 824 × 1224 cm, mahya 400 cm. Sundurmanın çatısı: üç yüzlü (güney, kuzey, batı kırma ucu), 210 cm geniş; doğu ucu ana çatının saçak ucunda biter, ana saçağın üstünde kalan üçgen kalkan sayıldı.
- **Çelik:** üretim dosyasından (`../2026-10-06_kor_test/uretim_profil.py`): 101 çerçeve, 1 577 üye, 1 421,37 m; 0,8 mm 650,14 m, 1,2 mm 748,57 m, 1,5 mm 22,65 m (tek kiriş, KRS06).
- **Elektrik** (`sonuc/KT02_pafta_sayimi.json`; elektrik yerleşim paftasından): 5 tijli duy, 4 glop, 5 tekli ve 2 çiftli anahtar, 16 tekli ve 2 çiftli priz, 1 uydu prizi.

## Liste çıkmadan önce verilen kararlar

1. **Boya.** Açıklama 5 "Boya alıcıya ait" diyor: bütün boya (tavan boyası ve astar dahil) listeye yazılmadı. KT-01'de teknik özelliklerde yalnız dış ve iç cephe boyası yazıyordu ve gerçek listede tavan boyası ile astar vardı.
2. **Tesisat.** Notlarda tesisat yok (KT-01'de "tesisat alıcıya ait" yazıyordu): sıhhi tesisat grubu listede. Vitrifiye ve pencere alıcıya ait.
3. **Nem bariyeri.** Açıklama 1 (Boardex + çelik karkas + OSB + alçıpan) nem bariyeri yazmıyor: satır yok.
4. **Elektrik işaretleri.** Tek tırnaklı anahtar tekli, çift tırnaklı (lejanttaki) çiftli sayıldı; aynı uçtan çıkan iki priz (TV duvarı, ocak) çiftli priz. Sigorta kutusu paftada giriş kapısının yanında: kural zaten girişi alıyor. "Prizler antrasit renk" listeye yazılmadı (elektrik satırlarında renk kuralı yok).
5. **Sundurma.** Veranda gibi açık alan sayıldı (tavanı Boardex, köşebentte tavan çevresi). Çatısının ana saçağın üstünde kalan üçgeni kalkan (Boardex); o üçgenin iki eğik kenarı alın kenarı: yöntem B'de alın sacı ve baş makas Z'si, yöntem A'da alın kapama. Sundurmanın derelerinin ana saçakta biten iki ucu serbest uç (dere kapağı 2); iniş kuralı 8 köşe + 2 orta = 10.
6. **Çelik grupları.** Makaslar (33: 10 ana, 18 saçak, 5 sundurma), çatı panelleri (31: kırma uçları, saçak, sundurma), veranda destekleri (4) ve 1,5 mm kiriş (1) ayrı satır; ağırlık modeldeki profil boyundan. 80 × 45 × 1,5 profilin birim ağırlığı kuralda yok: o satırda kg yazılmadı (soru), toplama girmedi.
7. **Alan.** Oturum 92,27 m² (sundurma dahil); paftadaki toplam brüt alan 90 m². m²'ye bağlı satırlar 92 ile hesaplandı (kural böyle).
8. **Yöntem.** B: projenin yapıldığı yöntem (paftada tavan omegası ve aşık). A: çelik standardı (Lokman, 7 Ekim 2026). İkisi de çıkarıldı.

## Motor değişiklikleri (liste öncesi; kural değil, modelin anlatılabilmesi için)

- `girdi_genel.py`: kirişin açık parçaları ayrı bölgelere yazılabilir (`acik_bolgeler`: KRS06 hem verandada hem yaşama mekânında); kiriş başka bir çelik grubuna yazılabilir (`celik_grubu`); modeldeki öteki gruplar ayrı satır olur (`celik_modeli.ek_satirlar`).
- `yukleme.py`: `ek_satirlar` için çelik satırları (birim ağırlık kuralda yoksa kg yazılmaz, `soru`).
- `uretim_profil.py` (yeni): üretim dosyasından çerçeve çerçeve profil boyu ve et kalınlığı.
- Değişmezler denendi: bugünkü kod 0.12, 0.13 ve 0.14 setleriyle kendi günlerinin çıktılarını, 0.15 setiyle 8 Ekim 08:17'deki (`602fdc1`) çıktıları bayt bayt aynı veriyor; `saglama.py` ve çokgen sınaması toplam sorun 0.

## Çalıştırma

```
python ../2026-10-06_kor_test/uretim_profil.py <üretim klasörü> --json KT02_profil_boylari.json
python kt02_tanim_uret.py KT02.json KT02_profil_boylari.json          # tanım (depo dışında; Lokman'ın onayıyla depoya girer)
bash kt02_kos.sh KT02.json [python]                                   # iki girdi ve iki liste (sonuc/)
bash ../2026-10-06_kor_test/cizim_seti_kos.sh KT02.json <çıktı> [python] [--yontem panel]   # çizim seti (depo dışına)
```

## Kişisel veri

Depodaki dosyalarda müşteri, bayi ve çalışan adı, telefon ve fiyat yok. Kaynak dosyalar (paftalar, üretim dosyası, liste) depoya alınmadı; tanım ve çizimler şimdilik depo dışında.
