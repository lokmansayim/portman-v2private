#!/usr/bin/env bash
# KT-02 (ikinci kör test): güncel kural setiyle iki liste. B: projenin yapıldığı yöntemle (tavan omegası ve aşık); A: çelik standardıyla
# (çatı ve tavan paneli). Elektrik sayıları projenin elektrik paftasından (`sonuc/KT02_pafta_sayimi.json`); iniş sayısı kuraldan.
# Tanım (`KT02.json`, `kt02_tanim_uret.py` ile üretilir) müşteri projesinin geometrisidir; depoya Lokman'ın onayıyla girer. Yolu verilir.
# Geçici dosya yazmaz, hiçbir dosyayı silmez. Kullanım: bash kt02_kos.sh <KT02.json> [python]
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt02_kos.sh <KT02.json> [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR      # güncel kural seti (kurallar.json)
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (ikinci kör test projesi; montaj paftası ve üretim dosyasından)"
"$PY" "$G" "$T" --dosya sonuc/KT02_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" "$G" "$T" --yontem panel --dosya sonuc/KT02_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in B A; do
  "$PY" "$Y" "sonuc/KT02_${X}_girdi.json" --elektrik-sayimi sonuc/KT02_pafta_sayimi.json \
      --cikti "sonuc/KT02_${X}_yukleme.json" --md "sonuc/KT02_${X}_yukleme.md" > /dev/null
done
echo "KT-02: iki liste yazıldı (sonuc/KT02_{A,B}_yukleme.json ve .md)"
