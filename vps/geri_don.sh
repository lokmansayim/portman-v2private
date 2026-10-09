#!/usr/bin/env bash
# PORTMAN · önceki sürüme dönüş (İE-06, karar 7; root; TEK KOMUT). 'guncel' ile 'onceki' bağlantıları yer değiştirir, servisler
# yeniden başlar, durum.sh koşar. Veritabanına ve şemaya dokunmaz (göçler yalnız ekler; N sürümü N+1 şemasında çalışır).
#   ssh portman-vps 'bash /opt/portman/guncel/vps/geri_don.sh' > ie06_12_geri.txt 2>&1
# DURUR: 'onceki' bağlantısı yoksa. İleri almak için yeniden guncelle.sh <etiket>.
# Sınama: PM_KOK, PM_SYSTEMCTL, PM_TEST=1 (durum.sh atlanır).
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; TEST="${PM_TEST:-}"
SERVISLER="portman-webhook portman-gonderici portman-agent portman-panel"
dur() { echo "DUR: $*" >&2; exit 1; }
echo "== Portman sürüm geri dönüşü · $(date '+%Y-%m-%d %H:%M:%S %Z')"
[ -L "$KOK/onceki" ] || dur "önceki sürüm yok ($KOK/onceki); dönülecek yer yok"
[ -L "$KOK/guncel" ] || dur "güncel sürüm bağlantısı yok ($KOK/guncel)"
GUNCEL="$(readlink -f "$KOK/guncel")"; ONCEKI="$(readlink -f "$KOK/onceki")"
[ -f "$ONCEKI/SURUM" ] || dur "önceki sürüm dizini eksik ya da bozuk: $ONCEKI"
echo "   $(cat "$GUNCEL/SURUM" 2>/dev/null || echo '?') → $(cat "$ONCEKI/SURUM")"
$SYSTEMCTL stop $SERVISLER >/dev/null 2>&1 || true
ln -sfn "$ONCEKI" "$KOK/guncel.yeni"; mv -T "$KOK/guncel.yeni" "$KOK/guncel"
ln -sfn "$GUNCEL" "$KOK/onceki.yeni"; mv -T "$KOK/onceki.yeni" "$KOK/onceki"
$SYSTEMCTL daemon-reload >/dev/null 2>&1 || true
$SYSTEMCTL start $SERVISLER || dur "servisler başlatılamadı (journalctl -u portman-webhook)"
echo "   guncel → $(readlink "$KOK/guncel") · onceki → $(readlink "$KOK/onceki") · servisler yeniden başlatıldı"
if [ -z "$TEST" ] && [ -f "$KOK/guncel/vps/durum.sh" ]; then bash "$KOK/guncel/vps/durum.sh" || true; fi
echo "== bitti: $(cat "$KOK/guncel/SURUM") etkin"
