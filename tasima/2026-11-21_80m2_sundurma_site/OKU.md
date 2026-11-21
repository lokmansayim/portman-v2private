# rehber.portatifev.com · 80 m² 2+1 sundurmalı rehberin eklenmesi (main'den, 21 Kasım 2026)

Kaynak: `main` 275962cd (PR #301; rehber PR #300). Komut: `python -m araclar.paket.site <çıktı> --npm <three-0.160.0, fontsource 5.1.0 ×3> --esbuild <esbuild 0.24.0> --onceki <2026-11-20_85m2_yenileme/rehber_kur.sh>`.
Paket: 196 dosya; paket sha256 `0ef0a8cb70b27cf09578006367396282223472558fb5e424c46045b7fd0eb16b`.
`rehber_kur.sh` sha256 `0eb1df03a8ce7b455b273a25540ebaaf172fc8fa394338dfc27b1dcf4aaba863` (10,19 MB).
Bu paket, PR dalından kurulan denemeyle bayt bayt aynı.

Dayanak: Lokman, 21 Kasım 2026 10:00:33 UTC "evet ekle" (rehber siteye eklensin). Rehberin damlalığı ve mastiği önceden onaylı ("damlalığı onaylıyorum", "bu şekilde onaylıyorum").

## Canlıdaki siteden farkı (sürüm 20261120232952)

- Canlının 172 dosyasından 170'i bayt bayt aynı. Öteki 6 rehber canlıdaki paketten bayt bayt alındı.
- Değişen 2 dosya: `index.html` (açılışa 80 m² 2+1 · Sundurmalı kartı), `oyun/gorsel/kapak.jpg` (her kurulumda yeniden çekilir; oyunun evi aynı).
- Yeni 24 dosya: `80m2-sundurma/` (20 adım, 511 parça, ön onay paftası).
- Silinen dosya yok.
- Tarayıcı denemesi (masaüstü, telefon): `tarayici_denemesi.txt` "SONUÇ: bulgu yok", `ekran/`.

## Kurulum (Lokman'ın Mac'i; bu klasörde, Terminal'de)

DİKKAT: 3. adım canlı değişikliktir. Eski sürüm silinmez. Geri dönüş 5. adımdadır.

1. Canlı hâlâ eski paket mi? Beklenen son satır: `SONUÇ: site paketle aynı`.
   `bash canli_denetim.sh onceki_SHA256SUMS > rehber_canli_once_1121.txt 2>&1`
2. Kuru koşu. Beklenen son satır: `== sonuç: kuru koşu bitti, hiçbir şey değişmedi`.
   `ssh portman-vps 'timeout 300 bash -s -- --dene' < rehber_kur.sh > rehber_dene_1121.txt 2>&1`
3. Uygula. Beklenen son satır: `== sonuç: yayında https://rehber.portatifev.com/ · sürüm <zaman>`.
   `ssh portman-vps 'timeout 300 bash -s -- --uygula' < rehber_kur.sh > rehber_uygula_1121.txt 2>&1`
4. Canlı denetim. Beklenen son satır: `SONUÇ: site paketle aynı`.
   `bash canli_denetim.sh SHA256SUMS > rehber_canli_denetim_1121.txt 2>&1`
5. Yalnız sorun varsa geri al (20261120232952'ye döner):
   `ssh portman-vps 'timeout 300 bash -s -- --geri' < rehber_kur.sh > rehber_geri_1121.txt 2>&1`

1. adım "FARK VAR" derse dur: canlı site 20 Kasım 23:29 İstanbul kurulumundan beri değişmiş demektir; 2. adıma geçme. Çıktı dosyalarını bu klasöre koyun; rehber sohbeti okur.

## Sonraki ekleme

Bir sonraki rehber eklemesi `--onceki` olarak bu klasörün `rehber_kur.sh`'sini kullanır; `rehberler.json › sabit_paket` bu paketin sürümü ve özetiyle güncellenir, 80m2-sundurma satırı `"sabit": true` olur.
