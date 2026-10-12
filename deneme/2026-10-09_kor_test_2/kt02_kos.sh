#!/usr/bin/env bash
# KT-02 (ikinci kör test): kural seti 0.15 ile iki liste (dondurulan listeler; Lokman'ın 9 Ekim 22:22 cevaplarından önceki set). B: projenin yapıldığı yöntemle (tavan omegası ve aşık); A: çelik standardıyla
# (çatı ve tavan paneli). Elektrik sayıları projenin elektrik paftasından (`sonuc/KT02_pafta_sayimi.json`); iniş sayısı kuraldan.
# Tanım: `tanim/KT02.json` (dondurulan tanım; `tanim/kt02_tanim_uret.py` üretir; 9 Ekim 2026 22:22'den beri depoda, Lokman'ın onayıyla). Yolu verilir.
# Cevaplardan sonraki listeler güncel kural setiyle: kt02_cevaplar_kos.sh.
# Geçici dosya yazmaz, hiçbir dosyayı silmez. Kullanım: bash kt02_kos.sh tanim/KT02.json [python]
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt02_kos.sh <KT02.json> [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
export PORTMAN_KURALLAR="$(cd ../../kurallar/liste && pwd)/setler/0.15.json"   # dondurulan listeler (9 Ekim 2026 21:40) 0.15 kural setiyle (o günkü set) bayt bayt aynı çıkar
"$PY" -c 'import json, os, sys; s = json.load(open(os.environ["PORTMAN_KURALLAR"], encoding="utf-8"))["sema"]; sys.exit(0 if "/0.15" in s else f"kt02_kos.sh 0.15 kural setiyle koşar; seçilen dosya: {s}")'
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
