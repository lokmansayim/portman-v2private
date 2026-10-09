#!/usr/bin/env bash
# PORTMAN · eski VPS arşivi (İE-06, Kapı 0; isteğe bağlı; SALT OKUNUR; root; v1.3 düzeni). pg_dump -Fc portman + /opt/portman/data
# (*.env hariç; /etc/portman girmez) → /root/portman-arsiv-<tarih>.tgz; boyut ve sha256 yazılır. Mac'e scp ile alınır; Kapı 1
# sunucuyu siler. Hiçbir şeyi değiştirmez. Sınama: PM_HOME, PM_PG_DUMP, PM_CIKTI_DIR, PM_DB.
set -euo pipefail
HOME_DIR="${PM_HOME:-/opt/portman}"; CIKTI_DIR="${PM_CIKTI_DIR:-/root}"; DB="${PM_DB:-portman}"
PG_DUMP="${PM_PG_DUMP:-sudo -u postgres pg_dump}"
dur() { echo "DUR: $*" >&2; exit 1; }
cd /tmp; umask 077
TARIH="$(date +%Y%m%d-%H%M%S)"; HEDEF="$CIKTI_DIR/portman-arsiv-$TARIH.tgz"
GECICI="$(mktemp -d "$CIKTI_DIR/.arsiv.XXXXXX")"; trap 'rm -rf "$GECICI"' EXIT
echo "== Portman eski VPS arşivi · $(date '+%Y-%m-%d %H:%M:%S %Z')"
$PG_DUMP -Fc -d "$DB" > "$GECICI/portman.dump" || dur "pg_dump başarısız"
echo "   pg_dump: $(stat -c %s "$GECICI/portman.dump") B"
[ -d "$HOME_DIR/data" ] || dur "$HOME_DIR/data yok"
tar -C "$HOME_DIR" --exclude='*.env' --exclude='*.lock' -cf "$GECICI/data.tar" data || dur "data arşivi alınamadı"
echo "   data: $(stat -c %s "$GECICI/data.tar") B ($(tar -tf "$GECICI/data.tar" | wc -l) öğe; *.env hariç)"
tar -C "$GECICI" -czf "$HEDEF" portman.dump data.tar
chmod 600 "$HEDEF"
echo "   arşiv: $HEDEF · $(stat -c %s "$HEDEF") B · sha256 $(sha256sum "$HEDEF" | cut -c1-64)"
echo "   Mac'e: scp portman-vps:$HEDEF ~/Desktop/\"Claude Portman Çalışması\"/30_IE06/"
echo "== bitti"
