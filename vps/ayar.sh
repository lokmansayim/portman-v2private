#!/usr/bin/env bash
# PORTMAN · ayar değiştirme (İE-06; root): /opt/portman/data/settings.json'da tek anahtar. Değer JSON olarak yorumlanır
# (true, false, 5, "metin"). 'enabled true' yazılınca enabled_at da şimdi olur (eski mesajlar sahiplenilmesin). Servisler ayarı her
# turda yeniden okur; yeniden başlatma gerekmez. Sır içermez.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/ayar.sh enabled true'
#   ssh portman-vps 'bash /opt/portman/guncel/vps/ayar.sh dry_run false'
#   ssh portman-vps 'bash /opt/portman/guncel/vps/ayar.sh'            (yalnız göster)
# Sınama: PM_KOK, PM_DATA, PM_PYTHON.
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; DATA="${PM_DATA:-$KOK/data}"; PY="${PM_PYTHON:-python3}"
AYARLAR="$KOK/guncel/kanal/ayarlar.py"; [ -f "$AYARLAR" ] || AYARLAR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../kanal/ayarlar.py"
[ -f "$AYARLAR" ] || { echo "DUR: kanal/ayarlar.py bulunamadı (sürüm kurulu mu?)" >&2; exit 1; }
if [ $# -eq 0 ]; then "$PY" "$AYARLAR" --veri "$DATA" oku; exit 0; fi
[ $# -eq 2 ] || { echo "kullanım: ayar.sh <anahtar> <değer>   ya da   ayar.sh" >&2; exit 2; }
"$PY" "$AYARLAR" --veri "$DATA" yaz "$1" "$2"
