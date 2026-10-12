#!/usr/bin/env bash
# PORTMAN · İE-08 Adım 8 · yedi çelik adayın mühendis kabul kaydı (K-A10; root). Mühendis yedi modeli kabul paketiyle tek oturumda
# gördükten sonra, yalnız kabul ettiği kodlar Postgres `adaylar` tablosuna 'gecerli' + muhendis_kabulu{kim, tarih, not} ile yazılır;
# kabul edilmeyen aday yazılmaz, bayiye sunulmaz. Mühendisin adı yalnız komut satırından gelir; depoya (git), günlüğe ve çıktıya girmez.
# Canlı değişikliktir: Lokman'ın ayrı onayıyla, PR-2a birleşip sürüm güncellendikten sonra, canlı A2 denemesinden önce koşar.
#   ssh portman-vps 'bash -s' -- "Ç8801,Ç8801K,Ç8801L,Ç8201,KT01,KT02,KT03" "<mühendisin adı>" "2026-10-13" "<notu>" "<paket tarihi>" < vps/ie08_adaylar.sh
#   ... "--kuru" ile başlayan ilk argüman: yazmadan ne yazılacağını söyler.
# Sınama: PM_KOK, PM_ETC, PM_PYTHON (venv yerine), PM_PG_DSN (env dosyası yerine).
set -uo pipefail
KURU=""
if [ "${1:-}" = "--kuru" ]; then KURU="--kuru"; shift; fi
KODLAR="${1:-}"; KIM="${2:-}"; TARIH="${3:-$(date +%Y-%m-%d)}"; NOT="${4:-}"; PAKET="${5:-}"
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"
dur() { echo "DUR: $*" >&2; exit 1; }
[ -n "$KODLAR" ] || dur "kabul edilen kod listesi boş (örn. Ç8801,Ç8801K,Ç8801L)"
[ -n "$KIM" ] || dur "mühendisin adı boş"
GUNCEL="$KOK/guncel"; [ -d "$GUNCEL/araclar" ] || GUNCEL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
[ -f "$GUNCEL/araclar/aday_kabul.py" ] || dur "araclar/aday_kabul.py yok: sürüm İE-08 PR-2a'dan eski mi? ($GUNCEL)"
[ -f "$GUNCEL/beyin/veri/adaylar.json" ] || dur "beyin/veri/adaylar.json sürümde yok"
PY="${PM_PYTHON:-$GUNCEL/venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
if [ -n "${PM_PG_DSN:-}" ]; then DSN="$PM_PG_DSN"
elif [ -f "$ETC/agent.env" ]; then DSN="$(grep -E '^PORTMAN_PG_DSN=' "$ETC/agent.env" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"
else DSN="dbname=portman"; fi
[ -n "$DSN" ] || DSN="dbname=portman"
echo "== Portman aday kabul kaydı · $(date '+%Y-%m-%d %H:%M:%S %Z') · sürüm $(cat "$GUNCEL/SURUM" 2>/dev/null || echo '?')"
echo "   kodlar: $KODLAR · tarih: $TARIH · kim: ${KIM:0:1}… (ad çıktıya girmez)"
cd /tmp
# Ajanla aynı kimlik ve DSN (systemd: PORTMAN_PG_DSN=dbname=portman, kullanıcı portman; guncelle.sh de göçleri böyle koşar)
if [ -n "${PM_OLARAK+x}" ]; then read -r -a OLARAK <<< "$PM_OLARAK"; elif [ "$(id -u)" = "0" ] && id portman >/dev/null 2>&1; then OLARAK=(sudo -u portman); else OLARAK=(); fi
"${OLARAK[@]}" env PORTMAN_PG_DSN="$DSN" HOME="${HOME:-/tmp}" "$PY" "$GUNCEL/araclar/aday_kabul.py" $KURU --kodlar "$KODLAR" --kim "$KIM" --tarih "$TARIH" --not "$NOT" --paket "$PAKET"
RC=$?
[ "$RC" = "0" ] || dur "kabul kaydı yazılamadı (çıkış $RC)"
echo "   tamam. Canlı A2 denemesi artık bu adayları sunar (bayi 'Ç8801' ya da '88 m² 2+1 çelik' yazınca)."
