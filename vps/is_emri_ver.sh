#!/usr/bin/env bash
# PORTMAN · İE-34 · bayinin onayladığı planın İş Emri'ni ver (root; salt okunur). Montaj rehberi bu İş Emri'nden bulutta, `main`'deki
# koddan üretilir (`python -m araclar.paket --is-emri <dosya> <çıktı> --render`; D-28). Lokman Mac'inden koşar:
#   ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/is_emri_ver.sh' > onayli_planlar.txt 2>&1           (son 10 onaylı plan)
#   ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/is_emri_ver.sh <İş Emri no> <rev>' > is_emri.json 2>&1
# Yalnız bayinin onayladığı revizyon gelir (revizyonlar.durum = 'onaylandi'). Çıktı yalnız İş Emri'nin JSON'udur; içindeki her metinde
# telefon numarasına benzeyen dizge "…" olur (beyin/numara.py; K09). Bayi kodu, bayi adı, müşteri adı ve talep metni İş Emri'nde durur:
# dosyanın buluta gelmesi yeni veri paylaşımıdır (ilk seferde Lokman'ın onayı). Listede gönderen numarası yazılmaz.
# Veritabanına yazmaz (READ ONLY işlem); LLM ve WhatsApp yok.
# Sınama: PM_KOK, PM_PSQL, PM_PYTHON.
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"
GUNCEL="$KOK/guncel"; [ -f "$GUNCEL/beyin/numara.py" ] || GUNCEL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
PY="${PM_PYTHON:-$GUNCEL/venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
dur() { echo "DUR: $*" >&2; exit 1; }
cd /tmp

if [ $# -eq 0 ]; then
  echo "== son 10 onaylı plan (salt okunur · $(date '+%Y-%m-%d %H:%M:%S %Z'))"
  $PSQL -v ON_ERROR_STOP=1 <<'SQL' | sed 's/^/   /'
BEGIN READ ONLY;
SELECT is_emri_no || ' r' || lpad(rev::text, 2, '0') || ' · bayi ' || coalesce(bayi_kod, '?') || ' · '
       || coalesce(is_emri->'yapi'->>'sistem', 'prefabrik') || ' · onaylandı ' || to_char(onaylandi AT TIME ZONE 'Europe/Istanbul', 'YYYY-MM-DD HH24:MI')
  FROM revizyonlar WHERE durum = 'onaylandi' ORDER BY onaylandi DESC NULLS LAST, id DESC LIMIT 10;
COMMIT;
SQL
  echo "   İş Emri'ni almak: is_emri_ver.sh <İş Emri no> <rev> (ör. is_emri_ver.sh PM-K12-20261110-001 1)"
  exit 0
fi
[ $# -eq 2 ] || { echo "kullanım: is_emri_ver.sh [<İş Emri no> <rev>]" >&2; exit 2; }
NO="$1"; REV="$2"
[[ "$NO" =~ ^[A-Za-z0-9._-]{1,80}$ ]] || dur "İş Emri no biçimi tanınmadı: '$NO'"
[[ "$REV" =~ ^[0-9]{1,3}$ ]] || dur "rev bir sayı olmalı (1, 2, …): '$REV'"
GEC="$(mktemp /tmp/portman_is_emri_XXXXXX)"; chmod 600 "$GEC"
trap 'rm -f "$GEC"' EXIT
$PSQL -v ON_ERROR_STOP=1 -v no="$NO" -v rev="$REV" > "$GEC" <<'SQL' || dur "veritabanı okunamadı"
BEGIN READ ONLY;
SELECT is_emri::text FROM revizyonlar WHERE is_emri_no = :'no' AND rev = :'rev'::int AND durum = 'onaylandi';
COMMIT;
SQL
sed -i '/^\s*$/d' "$GEC"
[ -s "$GEC" ] || dur "$NO r$(printf %02d "$((10#$REV))") onaylı değil ya da yok (yalnız bayinin onayladığı revizyon verilir; liste: is_emri_ver.sh)"
"$PY" - "$GEC" "$GUNCEL" <<'PY' || dur "İş Emri JSON'u okunamadı"
import json, sys
sys.path.insert(0, sys.argv[2])
from beyin import numara


def maskele(x):
    if isinstance(x, str):
        return numara.maskele(x)
    if isinstance(x, list):
        return [maskele(y) for y in x]
    if isinstance(x, dict):
        return {k: maskele(v) for k, v in x.items()}
    return x


with open(sys.argv[1], encoding="utf-8") as f:
    print(json.dumps(maskele(json.loads(f.read())), ensure_ascii=False, indent=1))
PY
