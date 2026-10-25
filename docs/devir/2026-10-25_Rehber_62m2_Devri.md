# Devir · 62 m² bayi projesi (beşik + cumba) montaj rehberi · 25 Ekim 2026

Dal: `claude/montaj-rehberi-devir`. Betikler: `deneme/2026-10-25_rehber_62m2/` (README orada). Deneme; canlıda değil.

## Ne yapıldı

Lokman'ın Mac'indeki proje klasörü (DWG, SKP, yükleme listesi) okunarak PK-01 rehberinin aynısı bu proje için kuruldu. Bütün çıktılar o klasörde.

- **Rehber.** 18 adım, 420 parça, kimlik kartlı.
  - Oda sırası (Lokman): Yatak 1 → banyo → hol → yatak 2 → salon-mutfak.
  - Başlıkta bayi adı Lokman'ın seçimiyle var. Özel artefakt ve Mac klasörü; depoda `__PROJE__`.
  - Özel artefakt: https://claude.ai/artifact/7B6xsSZsnAKhf3HoSpWZV2 (sürüm 1, render'lar `gorsel/` altında).
  - Mac klasörü: `Montaj Rehberi/` (html + `gorsel/`), `3B Model/`, `3D Yazıcı Maket/`, `BENİOKU.md`.
- **Render.** 6 görünüm (ön-sol, ön-sağ, arka-sol, çatısız, çatı katmanları, iç köşe), etiketli pafta, 19 adım karesi.
- **Model ve maket.**
  - GLB: 420 parça, kart bilgisi `extras`'ta.
  - 1:50 maket: gövde ve çıkarılabilir çatı, kapalı STL, 4 köşe tırnağı. Lokman sonra 3D yazıcıda basacak.
- **Yükleme listesiyle karşılaştırma:** pano, H, köşe, veranda, makas, trapez, pencere ve kapı adetleri listeyle aynı. Tablo proje klasöründeki `BENİOKU.md`'de.

## PK-01'den farklar

- **Cumba.** İkinci beşik, verandanın üstünde; ana mahyayla aynı yükseklikte, iki dere (vadi) hattı.
  - MKS09 veranda ön kirişinde, MKS10 yan kirişlerde.
  - MKS11–12 ara makas, ana makasların üst başlıklarına oturur.
- **Çatı.**
  - Katmanlar: makas → aşık → OSB 11 mm → nem bariyeri → trapez (80 cm kapatır).
  - Ters mahya ve trapez sac mahyası.
- **Kalkan.** Üç kalkan; kalkan parçaları (betopan, Z, C kapama, alın sacı, alt uç) genel bir kalkan çerçevesiyle kurulur.
- **Duvar.** Ön duvarda iki betopan kaplı çelik karkas duvar (DVR01/02); iç duvar–dış duvar birleşiminde çektirme U'su.

## Teyit bekleyenler (Lokman)

1. OSB dizilimi: OSB yerleşim paftası DWG'de boş (25 adet yazıyor).
2. Trapezde paftada çizili olmayan 7 üçgen kesim parçası (mahya ile dere arası).
3. Kalkan betopanı köşe dolguları (PK-01'deki gibi).
4. Alın sacı yüksekliği ~11 cm (trapez kenar hadvesine göre; PK-01'de 13).
5. Cumba sağ deresinin ön dereye iç köşede bağlanması.
6. PK-01'den aynen alınan kesitler: köşe, Z, C kapama, saçak ve alın sacı.

## Bu oturumda PK-01 düzeltmesi

Makas kartında eksik virgül yüzünden makasa dokununca kart açılmıyordu (`['Profil', …] ['Kart ölçüsü', …]`).
- `deneme/2026-10-24_montaj_rehberi/rehber/template.html` düzeltildi; kart satırı süzgeci `r && r[1]`.
- PK-01 artefaktı güncellendi.

## Sıradaki

- Lokman rehbere ve render'lara bakar, varsayımları teyit eder.
- Maketin baskısı Lokman'da. Önce ölçek (1:50) ve baskı yönü denenir.
- VPS yayını (kart 104): iki rehber (PK-01 ve bu proje) aynı paketle yayınlanabilir.
  - Herkese açık sürümde başlık kod ya da model adı olur; iç notlar temizlenir (`2026-10-24_Rehber_Yayin_Devri.md`).
