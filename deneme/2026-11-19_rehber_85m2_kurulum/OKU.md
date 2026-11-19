# rehber.portatifev.com · 85 m² 2+1 rehberinin eklenmesi (main'den, 19 Kasım 2026)

Kaynak: `main` 86b2800 (PR #271). Komut: `python -m araclar.paket.site <çıktı> --npm <three-0.160.0, fontsource 5.1.0 ×3> --esbuild <esbuild 0.24.0> --onceki <2026-11-15_baslik_90m2/rehber_kur.sh>`.
Paket: 145 dosya; paket sha256 `9be53e8cb05326779dbc9f9535d005cff62970524e1a91514841f24f852bf41c`.
`rehber_kur.sh` sha256 `9c7bfbffb0b1e0e999a398115634d1760b4184908c24d84d6e6a07455d1bed22` (7,75 MB).

Dayanak: Lokman, 17 Kasım 2026 08:44:37 UTC "onaylıyorum şimdi bir komut daha yeni sohbette canlıya alalım"; kart 19 Kasım 2026 18:44:15 UTC "Evet, bu hâliyle" (iki yazı farkı: "Pencere kör kasası", dübel satırında şase pul yok).

## Canlıdaki siteden farkı (sürüm 20261115103639)

- Canlının 121 dosyasından 120'si bayt bayt aynı. Öteki 5 rehber canlıdaki paketten bayt bayt alındı.
- Değişen 1 dosya: `index.html` (açılış). 85 m² 2+1 kartı eklendi; başka fark yok.
- Yeni 24 dosya: `85m2/` (rehber, kapak, ön onay paftası, three.js, yazı tipleri).
- Tarayıcı denemesi (masaüstü, telefon): "SONUÇ: bulgu yok" (`tarayici_denemesi.txt`, `ekran/`).

## Kurulum (Lokman'ın Mac'i; bu klasörde)

DİKKAT: 3. adım canlı değişikliktir. Eski sürüm silinmez. Geri dönüş 5. adımdadır.

1. Canlı hâlâ eski paket mi? Beklenen son satır: `SONUÇ: site paketle aynı`.
   `bash canli_denetim.sh onceki_SHA256SUMS > rehber_canli_once_1119.txt 2>&1`
2. Kuru koşu. Beklenen son satır: `== sonuç: kuru koşu bitti, hiçbir şey değişmedi`.
   `ssh portman-vps 'timeout 300 bash -s -- --dene' < rehber_kur.sh > rehber_dene_1119.txt 2>&1`
3. Uygula. Beklenen son satır: `== sonuç: yayında https://rehber.portatifev.com/ · sürüm <zaman>`.
   `ssh portman-vps 'timeout 300 bash -s -- --uygula' < rehber_kur.sh > rehber_uygula_1119.txt 2>&1`
4. Canlı denetim. Beklenen son satır: `SONUÇ: site paketle aynı`.
   `bash canli_denetim.sh SHA256SUMS > rehber_canli_denetim_1119.txt 2>&1`
5. Yalnız sorun varsa geri al (20261115103639'a döner):
   `ssh portman-vps 'timeout 300 bash -s -- --geri' < rehber_kur.sh > rehber_geri_1119.txt 2>&1`

1. adım "FARK VAR" derse dur: canlı site 15 Kasım'dan beri değişmiş demektir; 2. adıma geçme. Çıktı dosyalarını bu klasöre koyun; rehber sohbeti okur.
