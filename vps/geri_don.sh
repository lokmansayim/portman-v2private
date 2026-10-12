#!/usr/bin/env bash
# PORTMAN · önceki sürüme dönüş (İE-06, karar 7; root; TEK KOMUT). 'guncel' ile 'onceki' bağlantıları yer değiştirir, servisler
# yeniden başlar, /saglik beklenir (BK-07: ölçüt sürüm = önceki ve postgres = true; gelmezse UYARI ve çıkış 1, ileri alma yok),
# durum.sh koşar. Veritabanına ve şemaya dokunmaz (göçler yalnız ekler; N sürümü N+1 şemasında çalışır). nginx'e dokunmaz.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/geri_don.sh' > ie06_12_geri.txt 2>&1
# DURUR: 'onceki' bağlantısı yoksa. İleri almak için yeniden guncelle.sh <etiket>.
# Sınama: PM_KOK, PM_SYSTEMCTL, PM_SAGLIK_URL, PM_SAGLIK_BEKLE, PM_TEST=1 (durum.sh atlanır).
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; TEST="${PM_TEST:-}"
SAGLIK_URL="${PM_SAGLIK_URL:-http://127.0.0.1:8081/saglik}"; SAGLIK_BEKLE="${PM_SAGLIK_BEKLE:-60}"
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
HEDEF_SURUM="$(cat "$KOK/guncel/SURUM")"
echo "-- sağlık: $SAGLIK_URL (en çok $SAGLIK_BEKLE sn; ölçüt: surum=$HEDEF_SURUM ve postgres=true)"
OK=""; SON=""
for ((i = 0; i < SAGLIK_BEKLE; i++)); do
  SON="$(curl -s --max-time 5 "$SAGLIK_URL" 2>/dev/null || true)"
  if printf '%s' "$SON" | PM_ETIKET="$HEDEF_SURUM" python3 -c 'import json, os, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
sys.exit(0 if isinstance(d, dict) and d.get("surum") == os.environ["PM_ETIKET"] and d.get("postgres") is True else 1)'; then OK=1; break; fi
  sleep 1
done
if [ -z "$TEST" ] && [ -f "$KOK/guncel/vps/durum.sh" ]; then bash "$KOK/guncel/vps/durum.sh" || true; fi
if [ -z "$OK" ]; then
  echo "UYARI: sağlık $SAGLIK_BEKLE sn içinde $HEDEF_SURUM ile ve Postgres bağlantısıyla cevap vermedi (son cevap: ${SON:0:200}). Bağlantılar değişti, servisler $HEDEF_SURUM'de; journalctl -u portman-webhook -n 50. İleri almak: guncelle.sh <etiket>" >&2
  echo "== bitti: $HEDEF_SURUM etkin (sağlık gelmedi)"; exit 1
fi
echo "   sağlık: sürüm $HEDEF_SURUM, Postgres bağlı · ${SON:0:300}"
echo "== bitti: $HEDEF_SURUM etkin"
