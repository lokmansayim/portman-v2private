#!/usr/bin/env bash
# KT-02 kıyası: düzeltilmiş tanımla (yalnız girdi hatamız düzeltildi) iki liste, Eylül 2026 katmanıyla B (bilgi), iki kural sorusunun
# "ne olur" listesi (bilgi) ve gerçek listeyle tablo.
# Dondurulan listeler (sonuc/KT02_{A,B}_yukleme.json) değişmez; bu betik onlara yazmaz. Tanım: `tanim/KT02_duzeltilmis.json` (depoda); yolu verilir.
# Bu, Lokman'ın 9 Ekim 22:22 cevaplarından önceki kıyasın kaydıdır (kural seti 0.15). Cevaplardan sonrası: kt02_cevaplar_kos.sh (güncel set).
# Geçici dosya yazmaz, hiçbir dosyayı silmez. Kullanım: bash kt02_kiyas_kos.sh tanim/KT02_duzeltilmis.json [python]   Çıkış kodu: denetim sorunu varsa 1.
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kt02_kiyas_kos.sh <KT02_duzeltilmis.json> [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
export PORTMAN_KURALLAR="$(cd ../2026-10-03_yukleme && pwd)/kural_setleri/0.15.json"   # 9 Ekim 2026 22:05 kıyası 0.15 kural setiyle (o günkü set) bayt bayt aynı çıkar
"$PY" -c 'import json, os, sys; s = json.load(open(os.environ["PORTMAN_KURALLAR"], encoding="utf-8"))["sema"]; sys.exit(0 if "/0.15" in s else f"kt02_kiyas_kos.sh 0.15 kural setiyle koşar; seçilen dosya: {s}")'
"$PY" -c 'import json, sys; t = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if t.get("duzeltmeler") else "Bu tanımda `duzeltmeler` alanı yok: düzeltilmiş tanımla koşulur.")' "$T"
G=../2026-10-06_kor_test/girdi_genel.py
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (ikinci kör test projesi; montaj paftası ve üretim dosyasından; kıyastan sonra düzeltildi)"
"$PY" "$G" "$T" --dosya sonuc/KT02_duzeltilmis_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" "$G" "$T" --yontem panel --dosya sonuc/KT02_duzeltilmis_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in B A; do
  "$PY" "$Y" "sonuc/KT02_duzeltilmis_${X}_girdi.json" --elektrik-sayimi sonuc/KT02_pafta_sayimi.json \
      --cikti "sonuc/KT02_duzeltilmis_${X}_yukleme.json" --md "sonuc/KT02_duzeltilmis_${X}_yukleme.md" > /dev/null
done
"$PY" "$Y" sonuc/KT02_duzeltilmis_B_girdi.json --sablon 2026 --elektrik-sayimi sonuc/KT02_pafta_sayimi.json \
    --cikti sonuc/KT02_duzeltilmis_B_2026.json --md sonuc/KT02_duzeltilmis_B_2026.md > /dev/null
# ne olur (yalnız bilgi): iki kural sorusu gerçek listedeki gibi cevaplanırsa (bina alanı 90, korkuluk Boardex'e girmez); kural değişmez
"$PY" kt02_ne_olur.py sonuc/KT02_duzeltilmis_B_girdi.json sonuc/KT02_ne_olur_B_girdi.json > /dev/null
"$PY" "$Y" sonuc/KT02_ne_olur_B_girdi.json --elektrik-sayimi sonuc/KT02_pafta_sayimi.json \
    --cikti sonuc/KT02_ne_olur_B_yukleme.json --md sonuc/KT02_ne_olur_B_yukleme.md > /dev/null
"$PY" kt02_kiyas.py --kor-b sonuc/KT02_B_yukleme.json --kor-a sonuc/KT02_A_yukleme.json \
    --duz-b sonuc/KT02_duzeltilmis_B_yukleme.json --duz-a sonuc/KT02_duzeltilmis_A_yukleme.json --sablon-b sonuc/KT02_duzeltilmis_B_2026.json \
    --ne-olur-b sonuc/KT02_ne_olur_B_yukleme.json --md sonuc/KT02_kiyas.md --json sonuc/KT02_kiyas.json
