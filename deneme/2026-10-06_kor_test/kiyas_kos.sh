#!/usr/bin/env bash
# KT-01 kıyası: düzeltilmiş tanımdan metraj girdisi, üç liste ve kıyas tablosu (`sonuc/`).
#   bugünkü kurallar · + Eylül 2026 uygulaması (--sablon 2026) · + pafta sayımı (elektrik, iniş)
# Ayrıca Eylül 2026 uygulamasının 2025 tarihli üç örnek listedeki sonucu.
# Tanım depoda değil (müşteri projesinin geometrisi; İE-05 gereği ayrı onayla eklenir): yolu verilir. Düzeltilmiş tanım olmalı (`duzeltmeler` alanı):
# dondurulan tanımla koşulursa "düzeltilmiş" listeler yanlış adla üretilir.
# Geçici dosya yazmaz, hiçbir dosyayı silmez; yalnız `sonuc/` altındaki kendi çıktılarını yeniden yazar.
# Kullanım: bash kiyas_kos.sh <KT01_duzeltilmis.json> [python]
# Çıkış kodu kiyas.py'ninkidir: sınıflama sorunu varsa 1.
set -euo pipefail
T=$(realpath "${1:?Kullanım: bash kiyas_kos.sh <tanım.json> [python]}")
PY=${2:-python3}
cd "$(dirname "$0")"
"$PY" -c 'import json, sys; t = json.load(open(sys.argv[1], encoding="utf-8")); sys.exit(0 if t.get("duzeltmeler") else "Bu tanımda `duzeltmeler` alanı yok: kıyas düzeltilmiş tanımla koşulur.")' "$T"
Y=../2026-10-03_yukleme/yukleme.py
D=sonuc/KT01_duzeltilmis
"$PY" girdi_genel.py "$T" --dosya "${D}_girdi.json" --uzerine-yaz --kaynak "Yapı Tanımı 0.5 (kör test projesi; DWG ve SKP'den; kıyastan sonra düzeltildi)" > /dev/null
"$PY" "$Y" "${D}_girdi.json" --cikti "${D}_yukleme.json" --md "${D}_yukleme.md" > /dev/null
"$PY" "$Y" "${D}_girdi.json" --sablon 2026 --cikti "${D}_2026.json" --md "${D}_2026.md" > /dev/null
"$PY" "$Y" "${D}_girdi.json" --sablon 2026 --elektrik-sayimi sonuc/KT01_pafta_sayimi.json --inis-plan 7 --cikti "${D}_2026_pafta.json" --md "${D}_2026_pafta.md" > /dev/null
kod=0
"$PY" kiyas.py --kor sonuc/KT01_yukleme.json --duzeltilmis "${D}_yukleme.json" --sablon "${D}_2026.json" --pafta "${D}_2026_pafta.json" \
    --md sonuc/KT01_kiyas.md --json sonuc/KT01_kiyas.json --ozet || kod=$?
# Eylül 2026 uygulaması 2025 tarihli üç gerçek listede ne veriyor (karar için; `sonuc/sablon_2026_eski_listeler.md`)
"$PY" sablon_eski_listeler.py --md sonuc/sablon_2026_eski_listeler.md --ozet
exit $kod
