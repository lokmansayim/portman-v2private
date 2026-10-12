#!/usr/bin/env bash
# Bütün hesapları sırayla koşar: üç gerçek listeyle karşılaştırma, Ç8201 (baz, dış 140, altı çatı kaplaması, yöntem B), çatı açılımı, tablolar.
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
for kp in tek_kat_panel sandvic_panel osb_kiremit osb_trapez trapez_sac osb_shingle; do
  "$PY" yukleme.py sonuc/C8201_girdi.json --kaplama $kp --cikti sonuc/C8201_kaplama_$kp.json --md sonuc/C8201_kaplama_$kp.md > /dev/null
done
# çatı açılımı ve kaplama dizilimi (kırma çatıda adet buradan): baz kaplama çizimle; şerit dizilen öteki kaplamalar yalnız JSON
"$PY" cati_acilim.py sonuc/C8201_girdi.json --cikti sonuc/C8201_cati_acilim.json --acilim-png sonuc/C8201_cati_acilim.png --kesim-png sonuc/C8201_cati_kesim.png \
  --olcu-md sonuc/C8201_cati_kesim_olculeri.md | sed -n 1,4p
for kp in sandvic_panel osb_kiremit trapez_sac; do
  "$PY" cati_acilim.py sonuc/C8201_girdi.json --kaplama $kp --cikti sonuc/C8201_cati_acilim_$kp.json | sed -n 3,4p
done
"$PY" yukleme.py sonuc/C8201_girdi.json --bayi ORNEK-BAYI-3 --cikti sonuc/C8201_yontem_B.json --md sonuc/C8201_yontem_B.md > /dev/null
"$PY" girdi_uret.py $C/C8201.json --secenek ../../kurallar/model/secenekler/dis_karkas_140.json > /dev/null
"$PY" yukleme.py sonuc/C8201_dis_karkas_140_girdi.json --cikti sonuc/C8201_dis_karkas_140_yukleme_taslak.json --md sonuc/C8201_dis_karkas_140_yukleme_taslak.md > /dev/null
"$PY" tablo_uret.py
# çatı açılımının geometrik sağlaması (çokgenlerle; panel boyu uzatma kuralı dahil; yaklaşık bir dakika). Sorun varsa çıkış kodu 1.
"$PY" cati_acilim_saglama.py | tail -1
