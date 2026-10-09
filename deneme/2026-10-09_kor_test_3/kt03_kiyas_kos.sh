#!/usr/bin/env bash
# KT-03 kıyası: düzeltilmiş tanımla (yalnız girdi hatalarımız düzeltildi) iki liste, Eylül 2026 katmanıyla B (bilgi), kural sorularının
# "ne olur" listesi (bilgi) ve gerçek listeyle tablo.
# Dondurulan listeler (sonuc/KT03_{A,B}_yukleme.json) değişmez; bu betik onlara yazmaz. Tanım: `KT03_duzeltilmis.json` (`kt03_tanim_duzeltilmis.py`
# üretir; müşteri projesinin geometrisi, depoya Lokman'ın onayıyla girer); yolu verilir.
# Kural seti 0.17'ye sabit (dondurulan listelerin seti). Geçici dosya yazmaz, hiçbir dosyayı silmez.
# Kullanım: bash kt03_kiyas_kos.sh <KT03_duzeltilmis.json> [python]   Çıkış kodu: denetim sorunu varsa 1.
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt03_kiyas_kos.sh <KT03_duzeltilmis.json> [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
unset PORTMAN_KURALLAR
"$PY" -c 'import json, sys; s = json.load(open("../2026-10-03_yukleme/kurallar.json", encoding="utf-8"))["sema"]; sys.exit(0 if "/0.17" in s else f"kt03_kiyas_kos.sh 0.17 kural setiyle koşar; kurallar.json: {s}")'
"$PY" -c 'import json, sys; t = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if t.get("duzeltmeler") else "Bu tanımda `duzeltmeler` alanı yok: düzeltilmiş tanımla koşulur.")' "$T"
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (üçüncü kör test projesi; montaj paftasından; kıyastan sonra düzeltildi)"
"$PY" "$G" "$T" --dosya sonuc/KT03_duzeltilmis_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" "$G" "$T" --yontem panel --dosya sonuc/KT03_duzeltilmis_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in B A; do
  "$PY" "$Y" "sonuc/KT03_duzeltilmis_${X}_girdi.json" --elektrik-sayimi sonuc/KT03_pafta_sayimi.json \
      --cikti "sonuc/KT03_duzeltilmis_${X}_yukleme.json" --md "sonuc/KT03_duzeltilmis_${X}_yukleme.md" > /dev/null
done
"$PY" "$Y" sonuc/KT03_duzeltilmis_B_girdi.json --sablon 2026 --elektrik-sayimi sonuc/KT03_pafta_sayimi.json \
    --cikti sonuc/KT03_duzeltilmis_B_2026.json --md sonuc/KT03_duzeltilmis_B_2026.md > /dev/null
NE=()
if [ -f kt03_ne_olur.py ]; then
  # ne olur (yalnız bilgi): kural soruları gerçek listedeki gibi cevaplanırsa; kural değişmez
  "$PY" kt03_ne_olur.py sonuc/KT03_duzeltilmis_B_girdi.json sonuc/KT03_ne_olur_B_girdi.json > /dev/null
  "$PY" "$Y" sonuc/KT03_ne_olur_B_girdi.json --elektrik-sayimi sonuc/KT03_pafta_sayimi.json \
      --cikti sonuc/KT03_ne_olur_B_yukleme.json --md sonuc/KT03_ne_olur_B_yukleme.md > /dev/null
  NE=(--ne-olur-b sonuc/KT03_ne_olur_B_yukleme.json)
fi
"$PY" kt03_kiyas.py --kor-b sonuc/KT03_B_yukleme.json --kor-a sonuc/KT03_A_yukleme.json \
    --duz-b sonuc/KT03_duzeltilmis_B_yukleme.json --duz-a sonuc/KT03_duzeltilmis_A_yukleme.json --sablon-b sonuc/KT03_duzeltilmis_B_2026.json \
    "${NE[@]}" --md sonuc/KT03_kiyas.md --json sonuc/KT03_kiyas.json
