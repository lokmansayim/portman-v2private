#!/usr/bin/env bash
# Çizim setini (plan, dört görünüş, pafta, IFC4, perspektifler) bir Yapı Tanımı'ndan üretir ve setin tam olduğunu denetler.
# Setin içeriği `cizim_seti.json`dadır (Lokman onayladı, 7 Ekim 2026 07:45); ayrıntı: docs/sartname/cizim_seti.md.
# Çıktı klasörü depo dışında olmalı: müşteri projelerinin çizimleri depoya ayrı onayla girer (KT-01'in onaylı seti `cizimler/` altında; Lokman, 8 Ekim 2026 07:23).
# Plan, görünüşler ve pafta her üretimde bayt bayt aynıdır; IFC'de kimlikler ve zaman damgası her üretimde değişir. Geçici dosya yazmaz, hiçbir dosyayı silmez.
# Kullanım: bash cizim_seti_kos.sh <tanım.json> <çıktı klasörü> [python] [--yontem panel|omega_asik]
#   Çıkış kodu: eksik ya da boş çıktı varsa ya da IFC şema hatası varsa 1.
set -euo pipefail
KULLANIM="Kullanım: bash cizim_seti_kos.sh <tanım.json> <çıktı klasörü> [python] [--yontem panel|omega_asik]"
T=$(realpath "${1:?$KULLANIM}")
mkdir -p "${2:?$KULLANIM}"
C=$(realpath "$2")
shift 2
PY=python3
if [ $# -gt 0 ] && [ "${1#--}" = "$1" ]; then PY=$1; shift; fi      # üçüncü argüman seçenek değilse yorumlayıcıdır
cd "$(dirname "$0")"
KOD=$("$PY" -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["kod"].replace("Ç", "C").replace("-", ""))' "$T")
"$PY" ciz_genel.py "$T" --cikti "$C" "$@"
"$PY" ifc_genel.py "$T" "$C/$KOD.ifc" "$@" > /dev/null       # yöntem seçeneği IFC'ye de geçer (çatının `Yontem` ve `UstYapi` özellikleri)
"$PY" perspektif.py "$C/$KOD.ifc" "$C" "$KOD" > /dev/null
"$PY" - "$C" "$KOD" <<'PY'
import json, sys
from pathlib import Path
cikti, kod = Path(sys.argv[1]), sys.argv[2]
seti = json.loads(Path("cizim_seti.json").read_text(encoding="utf-8"))
eksik = [c["dosya"].format(kod=kod) for c in seti["ciktilar"] if not (cikti / c["dosya"].format(kod=kod)).is_file() or (cikti / c["dosya"].format(kod=kod)).stat().st_size == 0]
ozet = json.loads((cikti / f"{kod}.ozet.json").read_text(encoding="utf-8")) if not eksik else {}
print(f"çizim seti: {len(seti['ciktilar']) - len(eksik)} / {len(seti['ciktilar'])} çıktı" + (f" · eksik: {', '.join(eksik)}" if eksik else f" · IFC {ozet['sema']}, şema hatası {ozet['sema_hatasi']}"))
sys.exit(1 if eksik or ozet.get("sema_hatasi") else 0)
PY
