# rehber.portatifev.com · 85 m² 2+1 rehberinin yenilenmesi (main'den, 20 Kasım 2026)

Kaynak: `main` 68497c8 (PR #295; içinde #280 ve #291 cumba aşık düzeltmeleri, #290 veranda kirişi 37,5 cm içeride). Komut: `python -m araclar.paket.site <çıktı> --npm <three-0.160.0, fontsource 5.1.0 ×3> --esbuild <esbuild 0.24.0> --onceki <2026-11-20_oyun/rehber_kur.sh>`.
Paket: 172 dosya; paket sha256 `236d6549840b26a7b86f0e6766dc8cc5131b24926672308e6ef6f61a81bd3176`.
`rehber_kur.sh` sha256 `b7a84e13a46357f8a5340a921cd67c68a3be50cab8e0e79f509a586532ddac33` (8,88 MB).
Bu paket, Lokman'a gösterilen denemeyle bayt bayt aynı (paket ve `rehber_kur.sh` özetleri aynı).

Dayanak: Lokman, 20 Kasım 2026 kartları: 12:21:28 UTC "Evet, yenilensin"; 13:46:42 UTC "Evet, yeni planla"; 14:10:38 UTC "Evet, kurulsun" (main'den üretilen paket denemeyle aynıysa Mac'ten kurulur). Rehberin paftası ve DXF'i 14:45:56 UTC "onaylıyorum".

## Canlıdaki siteden farkı (sürüm 20261120161856)

- Canlının 172 dosyasından 166'sı bayt bayt aynı. Öteki 5 rehber canlıdaki paketten bayt bayt alındı.
- Değişen 6 dosya:
  - `85m2/index.html`, `85m2/gorsel/kapak.jpg`, `85m2/gorsel/onay_pafta.jpg`: r06 planı (veranda kirişi 37,5 cm içeride, cumbada aşık 49).
  - `index.html` (açılış): 85 m² kartında "82,91 m² brüt · 77,83 m² net".
  - `oyun/ev.glb`, `oyun/gorsel/kapak.jpg`: cumba arkasındaki aşık düzeltmesi (oyunun evinde aşık parçası 71 → 73).
- Yeni ya da silinen dosya yok.
- Tarayıcı denemesi (masaüstü, telefon): `tarayici_denemesi.txt`, `ekran/`.

## Kurulum (Lokman'ın Mac'i; bu klasörde)

DİKKAT: 3. adım canlı değişikliktir. Eski sürüm silinmez. Geri dönüş 5. adımdadır.

1. Canlı hâlâ eski paket mi? Beklenen son satır: `SONUÇ: site paketle aynı`.
   `bash canli_denetim.sh onceki_SHA256SUMS > rehber_canli_once_1120b.txt 2>&1`
2. Kuru koşu. Beklenen son satır: `== sonuç: kuru koşu bitti, hiçbir şey değişmedi`.
   `ssh portman-vps 'timeout 300 bash -s -- --dene' < rehber_kur.sh > rehber_dene_1120b.txt 2>&1`
3. Uygula. Beklenen son satır: `== sonuç: yayında https://rehber.portatifev.com/ · sürüm <zaman>`.
   `ssh portman-vps 'timeout 300 bash -s -- --uygula' < rehber_kur.sh > rehber_uygula_1120b.txt 2>&1`
4. Canlı denetim. Beklenen son satır: `SONUÇ: site paketle aynı`.
   `bash canli_denetim.sh SHA256SUMS > rehber_canli_denetim_1120b.txt 2>&1`
5. Yalnız sorun varsa geri al (20261120161856'ya döner):
   `ssh portman-vps 'timeout 300 bash -s -- --geri' < rehber_kur.sh > rehber_geri_1120b.txt 2>&1`

1. adım "FARK VAR" derse dur: canlı site oyun kurulumundan (20 Kasım 16:18 İstanbul) beri değişmiş demektir; 2. adıma geçme. Çıktı dosyalarını bu klasöre koyun; rehber sohbeti okur.

## Sonraki ekleme

Bir sonraki rehber eklemesi `--onceki` olarak bu klasörün `rehber_kur.sh`'sini kullanır; `rehberler.json › sabit_paket` bu paketin sürümü ve özetiyle güncellenir, 85m2 satırı `"sabit": true` olur.
