#!/usr/bin/env bash
# KT-01, Lokman'ın 7 ve 8 Ekim 2026 kararlarından sonra: güncel kural setiyle iki liste ve durum tablosu (`sonuc/KT01_kararlar_*`).
#   B: projenin yapıldığı yöntemle (tavan omegası ve aşık)   A: çelik standardıyla (çatı ve tavan paneli)
# Elektrik sayıları projenin paftasından (`sonuc/KT01_pafta_sayimi.json`); iniş sayısı kuraldan.
# Tanım: `tanim/KT01_duzeltilmis.json` (8 Ekim 2026'dan beri depoda); yolu verilir, düzeltilmiş tanım olmalı. Geçici dosya yazmaz, hiçbir dosyayı silmez.
# 7 Ekim 03:46 kıyasının kendisi kiyas_kos.sh ile, o günkü kural setiyle (0.12) üretilir.
# Kullanım: bash kararlar_kos.sh tanim/KT01_duzeltilmis.json [python] [kural seti]      Çıkış kodu kararlar_kiyas.py'ninkidir: denetim sorunu varsa 1.
# Kural seti verilirse (ör. 0.13) o günkü tablo yeniden üretilir: kurallar `../2026-10-03_yukleme/kural_setleri/<set>.json`dan, satır açıklamaları
# `kararlar_notlari_setleri/<set>.json`dan okunur (açıklamalar adetlerle birlikte denetlendiği için her setin kendi açıklamaları vardır).
# Çıktılar yine `sonuc/KT01_kararlar_*` üzerine yazılır: eski setle koşulduktan sonra güncel setle yeniden koşulmalıdır.
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kararlar_kos.sh <tanım.json> [python] [kural seti]}")
PY=${2:-python3}
SET=${3:-}
cd "$(dirname "$0")"
if [ -n "$SET" ]; then
  export PORTMAN_KURALLAR="$(realpath "../2026-10-03_yukleme/kural_setleri/$SET.json")"
  NOTLAR="kararlar_notlari_setleri/$SET.json"
  [ -f "$NOTLAR" ] || { echo "Bu kural seti için açıklama dosyası yok: $NOTLAR" >&2; exit 2; }
else
  unset PORTMAN_KURALLAR      # güncel kural seti (kurallar.json): ortamda başka bir set seçili kalmış olmasın
  NOTLAR=kararlar_notlari.json
fi
"$PY" -c 'import json, sys; t = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if t.get("duzeltmeler") else "Bu tanımda `duzeltmeler` alanı yok: düzeltilmiş tanımla koşulur.")' "$T"
Y=../2026-10-03_yukleme/yukleme.py
K="Yapı Tanımı 0.5 (kör test projesi; DWG ve SKP'den; kıyastan sonra düzeltildi)"
"$PY" girdi_genel.py "$T" --dosya sonuc/KT01_kararlar_B_girdi.json --uzerine-yaz --kaynak "$K; yöntem B (yapıldığı gibi)" > /dev/null
"$PY" girdi_genel.py "$T" --yontem panel --dosya sonuc/KT01_kararlar_A_girdi.json --uzerine-yaz --kaynak "$K; yöntem A (çelik standardı)" > /dev/null
for X in A B; do
  "$PY" "$Y" "sonuc/KT01_kararlar_${X}_girdi.json" --elektrik-sayimi sonuc/KT01_pafta_sayimi.json \
      --cikti "sonuc/KT01_kararlar_${X}_yukleme.json" --md "sonuc/KT01_kararlar_${X}_yukleme.md" > /dev/null
done
"$PY" kararlar_kiyas.py --b sonuc/KT01_kararlar_B_yukleme.json --a sonuc/KT01_kararlar_A_yukleme.json --notlar "$NOTLAR" --md sonuc/KT01_kararlar_kiyas.md --json sonuc/KT01_kararlar_kiyas.json
