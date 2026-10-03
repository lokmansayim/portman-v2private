#!/usr/bin/env bash
# Bütün hesapları sırayla koşar: üç gerçek listeyle karşılaştırma, Ç8201 (baz, dış 140, kaplama seçenekleri, yöntem B), tablolar.
# Kullanım: bash hepsini_kos.sh [python]
set -euo pipefail
cd "$(dirname "$0")"
PY="${1:-python}"
C=../2026-10-02_celik
for n in 90 62 105; do
  "$PY" yukleme.py ornek_${n}m2_girdi.json --karsilastir ornek_${n}m2_gercek_liste.json --cikti sonuc/ornek_${n}m2_karsilastirma.json | grep "karşılaştırılan" | cut -d';' -f1
done
"$PY" girdi_uret.py $C/C8201.json > /dev/null
"$PY" yukleme.py sonuc/C8201_girdi.json --cikti sonuc/C8201_yukleme_taslak.json --md sonuc/C8201_yukleme_taslak.md > /dev/null
"$PY" yukleme.py sonuc/C8201_girdi.json --kaplama tek_kat_panel --cikti sonuc/C8201_kaplama_tek_kat_panel.json --md sonuc/C8201_kaplama_tek_kat_panel.md > /dev/null
"$PY" yukleme.py sonuc/C8201_girdi.json --kaplama osb_kiremit --cikti sonuc/C8201_kaplama_osb_kiremit.json --md sonuc/C8201_kaplama_osb_kiremit.md > /dev/null
"$PY" yukleme.py sonuc/C8201_girdi.json --bayi ORNEK-BAYI-3 --cikti sonuc/C8201_yontem_B.json --md sonuc/C8201_yontem_B.md > /dev/null
"$PY" girdi_uret.py $C/C8201.json --secenek $C/secenekler/dis_karkas_140.json > /dev/null
"$PY" yukleme.py sonuc/C8201_dis_karkas_140_girdi.json --cikti sonuc/C8201_dis_karkas_140_yukleme_taslak.json --md sonuc/C8201_dis_karkas_140_yukleme_taslak.md > /dev/null
"$PY" tablo_uret.py
