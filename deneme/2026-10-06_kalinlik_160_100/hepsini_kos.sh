#!/usr/bin/env bash
# 6 Ekim 2026 denemesinin bütün çıktılarını sırayla üretir ve kanıtları sonuc/ altına kopyalar.
#   bash hepsini_kos.sh [python] [bpy'li python]
# İkinci Python (Blender modülü, 3.13) verilmezse 3D görseller atlanır.
# PORTMAN_XLSX_RECALC bir "recalc.py" yolunu gösteriyorsa Excel formülleri LibreOffice ile hesaplanıp dosyaya yazılır;
# göstermiyorsa formüller dosya Excel'de açılınca hesaplanır.
set -euo pipefail
BURASI="$(cd "$(dirname "$0")" && pwd)"
PY="${1:-$HOME/.cache/portman-venv/bin/python}"; BPY="${2:-}"
NO="PM-DENEME-3ARTI1-1150x1050"; IE="$BURASI/is_emri_3arti1_1150x1050.json"
C="$BURASI/cikti/$NO"; S="$BURASI/sonuc/$NO"
"$PY" "$BURASI/kos.py" --sonuc
"$PY" "$BURASI/gorunus.py" "$IE" | tail -1
"$PY" "$BURASI/ifc_3b.py" "$IE" | grep '"gecti"'
"$PY" "$BURASI/yukleme_listesi.py" "$IE" > /dev/null
if [[ -n "${PORTMAN_XLSX_RECALC:-}" ]]; then python3 "$PORTMAN_XLSX_RECALC" "$C"/yukleme/*.xlsx 60; fi
if [[ -n "$BPY" ]]; then "$BPY" "$BURASI/ifc_gorsel.py" "$C"/ifc/*.ifc "$C/3b" --render > "$C/render.log" 2>&1; fi
for d in gorunus ifc yukleme 3b; do
  [[ -d "$C/$d" ]] || continue
  mkdir -p "$S/$d"; cp "$C/$d"/* "$S/$d"/
done
echo "kanıtlar: $S"
