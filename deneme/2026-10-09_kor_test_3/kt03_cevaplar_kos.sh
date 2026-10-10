#!/usr/bin/env bash
# KT-03, Lokman'ın 10 Ekim 2026 cevaplarından sonra (10:18, 10:29, 10:37, 10:39): güncel kural setiyle (kurallar/liste/kurallar.json; 0.18 ve sonrası)
# düzeltilmiş tanımdan iki liste ve gerçek listeyle tablo (`sonuc/KT03_cevaplar_*`). Cevaplar: tek eğimli çatı panelli çatılar (veranda, sundurma,
# müştemilat) "o 5 görseldeki gibi": saçakta dere ve özel büküm saçak sacı, yanlarda sundurma kapama, Boardex şeridi yok, veranda ve sundurmanın tavanı
# saçağıyla; alçak bir çatının üstüne düşen köşeye iniş yok; çatı çıkış kapağı ve bacanın içi listede yok; taharet musluğu vitrifiye dahilse ıslak hacim
# başına 4; saçak omegası çelik standardında yok (öyleydi). Tanım ve çizimler depoda (`tanim/`, `cizimler/`).
# Satır notları: `kt03_farklar.json` + `kt03_cevaplar_notlari.json` (üstüne yazar; kör listenin sınıfları değişmez).
# 10 Ekim 00:24 kıyasının kendisi kt03_kiyas_kos.sh ile (kural seti 0.17). Geçici dosya yazmaz, hiçbir dosyayı silmez.
# Kullanım: bash kt03_cevaplar_kos.sh tanim/KT03_duzeltilmis.json [python]   Çıkış kodu: denetim sorunu varsa 1.
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt03_cevaplar_kos.sh tanim/KT03_duzeltilmis.json [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR      # güncel kural seti (kurallar/liste/kurallar.json): ortamda başka bir set seçili kalmış olmasın
"$PY" -c 'import json, sys; t = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if t.get("duzeltmeler") else "Bu tanımda `duzeltmeler` alanı yok: düzeltilmiş tanımla koşulur.")' "$T"
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (üçüncü kör test projesi; montaj paftasından; kıyastan sonra düzeltildi; Lokman'ın 10 Ekim 2026 cevaplarından sonra)"
"$PY" "$G" "$T" --dosya sonuc/KT03_cevaplar_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" "$G" "$T" --yontem panel --dosya sonuc/KT03_cevaplar_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in B A; do
  "$PY" "$Y" "sonuc/KT03_cevaplar_${X}_girdi.json" --elektrik-sayimi sonuc/KT03_pafta_sayimi.json \
      --cikti "sonuc/KT03_cevaplar_${X}_yukleme.json" --md "sonuc/KT03_cevaplar_${X}_yukleme.md" > /dev/null
done
"$PY" kt03_kiyas.py --kor-b sonuc/KT03_B_yukleme.json --kor-a sonuc/KT03_A_yukleme.json \
    --duz-b sonuc/KT03_cevaplar_B_yukleme.json --duz-a sonuc/KT03_cevaplar_A_yukleme.json --ek-notlar kt03_cevaplar_notlari.json \
    --md sonuc/KT03_cevaplar_kiyas.md --json sonuc/KT03_cevaplar_kiyas.json
