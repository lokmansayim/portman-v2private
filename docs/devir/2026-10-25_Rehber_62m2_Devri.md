# Devir · 62 m² bayi projesi (beşik + cumba) montaj rehberi · 25 Ekim 2026

Dal: `claude/montaj-rehberi-devir`. Betikler: `deneme/2026-10-25_rehber_62m2/` (README orada). Deneme; canlıda değil.

## Ne yapıldı

Lokman'ın Mac'indeki proje klasörü (DWG, SKP, yükleme listesi) okunarak PK-01 rehberinin aynısı bu proje için kuruldu. Bütün çıktılar o klasörde.

- **Rehber.** 20 adım (sıra Lokman'ın, 26 Ekim: makaslar tek adım, izolasyon aşıklardan önce, saçak sacı aşıklardan sonra, dere ve inişler ile alın sacları ayrı, ters mahya trapezden önce), 419 parça, kimlik kartlı (gece düzeltmelerinden sonra; ilk sürüm 18 adım, 420 parça).
  - Oda sırası (Lokman): Yatak 1 → banyo → hol → yatak 2 → salon-mutfak.
  - Başlıkta bayi adı Lokman'ın seçimiyle var. Özel artefakt ve Mac klasörü; depoda `__PROJE__`.
  - Özel artefakt: https://claude.ai/artifact/7B6xsSZsnAKhf3HoSpWZV2 (sürüm 2, akşam düzeltmeleriyle; render'lar `gorsel/` altında).
  - Mac klasörü: `Montaj Rehberi/` (html + `gorsel/`), `3B Model/`, `3D Yazıcı Maket/`, `BENİOKU.md`.
- **Render.** 7 görünüm (ön-sol, ön-sağ, arka-sol, çatısız, çatı katmanları, iç köşe, baş makas kesiti), etiketli pafta. "Adımı render göster" Lokman'ın isteğiyle kaldırıldı.
- **Model ve maket.**
  - GLB: 419 parça, kart bilgisi `extras`'ta (rehberdeki cam yünü ruloları geçici, GLB'ye girmez).
  - 1:50 maket: gövde ve çıkarılabilir çatı, kapalı STL, 4 köşe tırnağı. Lokman sonra 3D yazıcıda basacak.
- **Yükleme listesiyle karşılaştırma:** pano, H, köşe, veranda, makas, trapez, pencere ve kapı adetleri listeyle aynı. Tablo proje klasöründeki `BENİOKU.md`'de.

## PK-01'den farklar

- **Cumba.** İkinci beşik, verandanın üstünde; ana mahyayla aynı yükseklikte, iki dere (vadi) hattı.
  - MKS09 veranda ön kirişinde, MKS10 yan kirişlerde.
  - MKS11–12 ara makas, ana makasların üst başlıklarına oturur.
- **Çatı.**
  - Katmanlar: makas → aşık → cam yünü → trapez 27/200-6 (100 cm kapatır, 0,5 mm). OSB ve nem bariyeri yok (Lokman, akşam).
  - Ters mahya ve trapez sac mahyası.
- **Kalkan.** Üç kalkan; kalkan parçaları (betopan, Z, C kapama, alın sacı) genel bir kalkan çerçevesiyle kurulur; ayrı alt uç parçası yok (26 Ekim).
- **Duvar.** Ön duvarda iki betopan kaplı çelik karkas duvar (DVR01/02); iç duvar–dış duvar birleşiminde çektirme U'su.

## Akşam düzeltmeleri (Lokman, 25 Ekim)

1. **Nem bariyeri ve OSB yok.** OSB/nem adımı (eski 15) çıktı; trapez doğrudan aşıkların üstünde, alın sacı ~10 cm. Paftadaki "OSB + nem bariyeri" notu bu projede geçerli değil.
2. **Makas uçlarına artan betopan.** Kalkan uç dolguları, 125 × 250'lerin eğimle kesilen artanından; artık varsayım değil. 26 Ekim: baş makasın duvar dışında kalan ucu da (saçak tarafı) kaplanır; saçak sacı ile alın sacının birleştiği köşedeki boşluk bundandı (Lokman).
3. **Cephe fugalı.** Dış panolarda alttan 6 × (38 + 2 cm fuga), üstte 10 cm bant (pafta 6, fugalı duvar detayı). Modelde 5 mm oluk, makette 0,5 × 0,3 mm.
4. **Baş makas detayı ve 100'lük omegalar (Lokman çizimi ve ölçüleri).** Pano 8 + 84 (EPS) + 8 mm; H kanadı 2 mm (1,2 mm sac, ezilmiş kıvrım); H sırt genişliği toplam 5 cm (gövdenin iki yanına 2,5 cm; Lokman'ın çiziminde 43,92 mm), 100'lük ve 60'lıkta aynı. 100'lük omegalar 10,5 cm = 2 + 100 + 2 + 1 mm, dış kanat H kanadına yaslı, içteki aralıklar silikonize mastik. Baş makas omegası: 3 cm derinlik, içte 3 cm açık yanak, dışta 1 cm U yanak; 8 mm betopan U'ya girer, makasa dayanır. Baş makaslar 3 mm dışarı (dış kanatla aynı hiza). Z önceki çizimdeki gibi.
5. **İç duvar üstlerine 60'lık duvar omegası:** 6,5 cm açıklık, 3 cm derinlik, 3 cm kulaklar (listede 60'lık omega toplamı 127,64 m = tavan 111,8 + iç duvar ~15).
5b. **Büyük pencereler:** DVR (251 × 250 çelik karkas) pencere yanları da fugalı.
6. **Ters tavan alçıpanı** tavan omegalarından sonra (adım 12; banyoda yeşil; verandada listedeki boardex).
7. **10 cm rulo cam yünü** çatı kapanmadan (adım 13): her makas aralığına bir şerit, cumbada makas yönünde yatay iki şerit; rehberde rulo açılarak serilir, kamera bütün şeritleri gösterir.
8. **Saçak, alın, makas ve dere köşesi** (Lokman'ın ev fotoğrafları ve işaretli çizimleri, 25–26 Ekim): ek parça yok, hepsi doğal duruşunda. Saçak sacının saçak altı baş makasa dayanıp kesilir, alnı ve kıvrımı köşeye kadar sürer; alın sacının saçak altı kolu makasın topuğunda kesilir, alın yüzü ve üst kıvrımı derenin ucunu içine alacak kadar geniş (~15 cm); makasın duvar dışındaki ucu betopanla kaplı. Köşe inişinde ağız borunun hizasında, kaz boynu duvara dik, boru köşe direği kaplamasının yanından iner. 10. **Pencereler** antrasit gri (RAL 7016); 180/180 Lokman çizimiyle (178 × 178 + 1'er cm pervaz payı; iki yan sabit, ortadaki iki kanat içe açılır, ortada kayıt yok). 11. **20. adımda** kanatlar ve kapılar sırayla açılıp kapanır; 120/120'de açılan kanat ve menteşe yönü varsayım. 9. **H sırtı** toplam 5 cm (gövdenin iki yanına 2,5; Lokman'ın çiziminde 43,92 mm).

1 ve 2'yi "nem bariyeri ve OSB yok" ve "makas uçlarına artan betopanları döşe" cümlelerinin, gönderilen teyit listesinin 1. ve 3. maddesine cevap olduğu okumasıyla yaptım; Lokman'a söylendi.

## Teyit bekleyenler (Lokman)

1. Trapez dizilimi: 27/200-6, 100 cm kapatır, 0,5 mm (Lokman); levhalar 100'lükle yeniden dizildi, cumbada 10 parça (listede 8).
2. Alın sacı ~15 cm: köşede dereyi içine alacak en az genişlik (Lokman, 26 Ekim: "dereyi de içine alacak şekilde genişleyecek"); kesin ölçü.
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
