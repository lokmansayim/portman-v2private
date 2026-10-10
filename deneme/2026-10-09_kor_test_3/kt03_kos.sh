#!/usr/bin/env bash
# KT-03 (üçüncü kör test): kural seti 0.17 ile iki liste (dondurulan listeler). B: projenin yapıldığı yöntemle (tavan omegası ve aşık);
# A: çelik standardıyla (çatı ve tavan paneli). Elektrik sayıları projenin elektrik paftasından (`sonuc/KT03_pafta_sayimi.json`); iniş sayısı kuraldan.
# Üretim dosyası yok: çelik ağırlığı motorun proje ortalamalarından, panel adetleri paftadaki yerleşimden (tanımda).
# Tanım (`KT03.json`, `kt03_tanim_uret.py` ile üretilir) müşteri projesinin geometrisidir; depoya Lokman'ın onayıyla girer. Yolu verilir.
# Kural seti 0.17'ye sabit: başka bir setle koşulursa durur (0.18 gelince 0.17 `kurallar/liste/setler/`e dondurulup buraya yazılır).
# Geçici dosya yazmaz, hiçbir dosyayı silmez. Kullanım: bash kt03_kos.sh <KT03.json> [python]
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt03_kos.sh <KT03.json> [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR      # güncel kural seti (kurallar/liste/kurallar.json; 9 Ekim 2026'da 0.17)
"$PY" -c 'import json, sys; s = json.load(open("../../kurallar/liste/kurallar.json", encoding="utf-8"))["sema"]; sys.exit(0 if "/0.17" in s else f"kt03_kos.sh 0.17 kural setiyle koşar; kurallar.json: {s}")'
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (üçüncü kör test projesi; montaj paftasından, üretim dosyası yok)"
"$PY" "$G" "$T" --dosya sonuc/KT03_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" "$G" "$T" --yontem panel --dosya sonuc/KT03_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in B A; do
  "$PY" "$Y" "sonuc/KT03_${X}_girdi.json" --elektrik-sayimi sonuc/KT03_pafta_sayimi.json \
      --cikti "sonuc/KT03_${X}_yukleme.json" --md "sonuc/KT03_${X}_yukleme.md" > /dev/null
done
echo "KT-03: iki liste yazıldı (sonuc/KT03_{A,B}_yukleme.json ve .md)"
