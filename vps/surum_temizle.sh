#!/usr/bin/env bash
# PORTMAN · eski sürüm dizinlerini kaldırır (İE-06; SİLME KAPISI: Lokman ayrı onayla koşar). En yeni PM_TUT (3) sürüm ile 'guncel'
# ve 'onceki' bağlantılarının hedefleri her zaman kalır. PM_ONAY=evet verilmezse yalnız listeler, hiçbir şey silmez.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/surum_temizle.sh'                 (liste)
#   ssh portman-vps 'PM_ONAY=evet bash /opt/portman/guncel/vps/surum_temizle.sh'    (sil)
# Sınama: PM_KOK, PM_TUT.
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; TUT="${PM_TUT:-3}"; ONAY="${PM_ONAY:-}"
[[ "$TUT" =~ ^[1-9][0-9]?$ ]] || { echo "DUR: PM_TUT 1–99 olmalı" >&2; exit 1; }
echo "== Portman sürüm temizliği · $(date '+%Y-%m-%d %H:%M:%S %Z') · en yeni $TUT sürüm ve bağlı sürümler kalır"
KORU=""
for b in guncel onceki; do [ -L "$KOK/$b" ] && KORU="$KORU $(readlink -f "$KOK/$b")"; done
ADAYLAR=()
n=0
while IFS= read -r d; do
  [ -n "$d" ] || continue
  n=$((n + 1))
  tam="$(readlink -f "$d")"
  if [ $n -le "$TUT" ] || [[ " $KORU " == *" $tam "* ]]; then echo "   kalır: $(basename "$d")"; else ADAYLAR+=("$d"); fi
done < <(ls -1dt "$KOK/surumler"/*/ "$KOK/surumler"/.yarim-*/ 2>/dev/null | sed 's:/$::' || true)
if [ ${#ADAYLAR[@]} -eq 0 ]; then echo "   silinecek sürüm yok"; echo "== bitti"; exit 0; fi
for d in "${ADAYLAR[@]}"; do echo "   silinecek: $(basename "$d") ($(du -sh "$d" 2>/dev/null | cut -f1))"; done
if [ "$ONAY" != "evet" ]; then echo "   PM_ONAY=evet verilmedi: hiçbir şey silinmedi (liste yukarıda)"; echo "== bitti"; exit 0; fi
for d in "${ADAYLAR[@]}"; do
  case "$d" in "$KOK/surumler"/*) rm -rf -- "$d"; echo "   silindi: $(basename "$d")" ;; *) echo "   atlandı (beklenmeyen yol): $d" ;; esac
done
echo "== bitti: $(ls -1d "$KOK/surumler"/*/ 2>/dev/null | wc -l) sürüm kaldı"
