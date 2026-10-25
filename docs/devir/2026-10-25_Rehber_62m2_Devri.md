# Devir · 62 m² bayi projesi (beşik + cumba) montaj rehberi · 25 Ekim 2026

Dal: `claude/montaj-rehberi-devir`. Betikler: `deneme/2026-10-25_rehber_62m2/` (README orada). Deneme; canlıda değil.

## Ne yapıldı

Lokman'ın Mac'indeki proje klasörü (DWG, SKP, yükleme listesi) okunarak PK-01 rehberinin aynısı bu proje için kuruldu. Bütün çıktılar o klasörde.

- **Rehber.** 19 adım, 421 parça, kimlik kartlı (akşam düzeltmelerinden sonra; ilk sürüm 18 adım, 420 parça).
  - Oda sırası (Lokman): Yatak 1 → banyo → hol → yatak 2 → salon-mutfak.
  - Başlıkta bayi adı Lokman'ın seçimiyle var. Özel artefakt ve Mac klasörü; depoda `__PROJE__`.
  - Özel artefakt: https://claude.ai/artifact/7B6xsSZsnAKhf3HoSpWZV2 (sürüm 2, akşam düzeltmeleriyle; render'lar `gorsel/` altında).
  - Mac klasörü: `Montaj Rehberi/` (html + `gorsel/`), `3B Model/`, `3D Yazıcı Maket/`, `BENİOKU.md`.
- **Render.** 7 görünüm (ön-sol, ön-sağ, arka-sol, çatısız, çatı katmanları, iç köşe, baş makas kesiti), etiketli pafta. "Adımı render göster" Lokman'ın isteğiyle kaldırıldı.
- **Model ve maket.**
  - GLB: 421 parça, kart bilgisi `extras`'ta.
  - 1:50 maket: gövde ve çıkarılabilir çatı, kapalı STL, 4 köşe tırnağı. Lokman sonra 3D yazıcıda basacak.
- **Yükleme listesiyle karşılaştırma:** pano, H, köşe, veranda, makas, trapez, pencere ve kapı adetleri listeyle aynı. Tablo proje klasöründeki `BENİOKU.md`'de.

## PK-01'den farklar

- **Cumba.** İkinci beşik, verandanın üstünde; ana mahyayla aynı yükseklikte, iki dere (vadi) hattı.
  - MKS09 veranda ön kirişinde, MKS10 yan kirişlerde.
  - MKS11–12 ara makas, ana makasların üst başlıklarına oturur.
- **Çatı.**
  - Katmanlar: makas → aşık → trapez (80 cm kapatır). OSB ve nem bariyeri yok (Lokman, akşam).
  - Ters mahya ve trapez sac mahyası.
- **Kalkan.** Üç kalkan; kalkan parçaları (betopan, Z, C kapama, alın sacı, alt uç) genel bir kalkan çerçevesiyle kurulur.
- **Duvar.** Ön duvarda iki betopan kaplı çelik karkas duvar (DVR01/02); iç duvar–dış duvar birleşiminde çektirme U'su.

## Akşam düzeltmeleri (Lokman, 25 Ekim)

1. **Nem bariyeri ve OSB yok.** OSB/nem adımı (eski 15) çıktı; trapez doğrudan aşıkların üstünde, alın sacı ~10 cm. Paftadaki "OSB + nem bariyeri" notu bu projede geçerli değil.
2. **Makas uçlarına artan betopan.** Kalkan uç dolguları, 125 × 250'lerin eğimle kesilen artanından; artık varsayım değil.
3. **Cephe fugalı.** Dış panolarda alttan 6 × (38 + 2 cm fuga), üstte 10 cm bant (pafta 6, fugalı duvar detayı). Modelde 5 mm oluk, makette 0,5 × 0,3 mm.
4. **Baş makas detayı ve 100'lük omegalar (Lokman çizimi ve ölçüleri).** 100'lük omegalar 10,5 cm, dış kanat dış duvara tam yaslı, içte 5 mm (silikonize mastik). Baş makas omegası: 3 cm derinlik, içte 3 cm açık yanak, dışta 1 cm U yanak; 8 mm betopan U'ya girer, makasa dayanır. Baş makaslar 1 mm dışarı (dış kanatla aynı hiza). Z önceki çizimdeki gibi.
5. **İç duvar üstlerine 60'lık duvar omegası:** 6,5 cm açıklık, 3 cm derinlik, 3 cm kulaklar (listede 60'lık omega toplamı 127,64 m = tavan 111,8 + iç duvar ~15).
5b. **Büyük pencereler:** DVR (251 × 250 çelik karkas) pencere yanları da fugalı.
6. **Ters tavan alçıpanı** tavan omegalarından sonra (yeni adım 14; banyoda yeşil; verandada listedeki boardex).
7. **10 cm rulo cam yünü** çatı kapanmadan (yeni adım 16): her makas aralığına bir şerit, cumbada makas yönünde yatay iki şerit; rehberde rulo açılarak serilir, kamera bütün şeritleri gösterir.

1 ve 2'yi "nem bariyeri ve OSB yok" ve "makas uçlarına artan betopanları döşe" cümlelerinin, gönderilen teyit listesinin 1. ve 3. maddesine cevap olduğu okumasıyla yaptım; Lokman'a söylendi.

## Teyit bekleyenler (Lokman)

1. Trapezde paftada çizili olmayan 7 üçgen kesim parçası (mahya ile dere arası).
2. Alın sacı yüksekliği ~10 cm (trapez kenar hadvesine göre; PK-01'de 13).
3. Cumba sağ deresinin ön dereye iç köşede bağlanması.
4. PK-01'den aynen alınan kesitler: köşe, Z, C kapama, saçak ve alın sacı.
5. Fuga derinliği (paftada yok; modelde 5 mm).
6. Baş makas omegasının U dudağı ~2 cm (ölçü verilmedi).

Teyit edilenler: omega ölçüleri, alçıpan ve cam yünü dizilimi (Lokman, 25 Ekim gece).

## Bu oturumda PK-01 düzeltmesi

Makas kartında eksik virgül yüzünden makasa dokununca kart açılmıyordu (`['Profil', …] ['Kart ölçüsü', …]`).
- `deneme/2026-10-24_montaj_rehberi/rehber/template.html` düzeltildi; kart satırı süzgeci `r && r[1]`.
- PK-01 artefaktı güncellendi.

## Sıradaki

- Lokman rehbere ve render'lara bakar, varsayımları teyit eder.
- Maketin baskısı Lokman'da. Önce ölçek (1:50) ve baskı yönü denenir.
- VPS yayını (kart 104): iki rehber (PK-01 ve bu proje) aynı paketle yayınlanabilir.
  - Herkese açık sürümde başlık kod ya da model adı olur; iç notlar temizlenir (`2026-10-24_Rehber_Yayin_Devri.md`).
