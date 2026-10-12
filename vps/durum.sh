#!/usr/bin/env bash
# PORTMAN · durum (İE-06; SALT OKUNUR; root). Hiçbir şeyi değiştirmez; LLM ya da WhatsApp çağrısı yapmaz. Gösterir: sürümler,
# servisler ve zamanlayıcılar, sağlık (/saglik), sertifika, ufw, sshd etkin değerleri, disk, Postgres sayımları (numara ve metin
# yok), nabız dosyaları, son günlük satırları (uzun sayılar maskeli). Sır değeri yazmaz.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/durum.sh' > durum_$(date +%Y%m%d).txt
# Sınama: PM_KOK, PM_ETC, PM_SYSTEMCTL, PM_SSHD, PM_UFW, PM_JOURNALCTL, PM_PSQL, PM_SAGLIK_URL, PM_LE_DIR, PM_ALAN.
set -uo pipefail
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; DATA="$KOK/data"
SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; SSHD="${PM_SSHD:-sshd}"; UFW="${PM_UFW:-ufw}"; JOURNALCTL="${PM_JOURNALCTL:-journalctl}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"; SAGLIK_URL="${PM_SAGLIK_URL:-http://127.0.0.1:8081/saglik}"
LE_DIR="${PM_LE_DIR:-/etc/letsencrypt}"; ALAN="${PM_ALAN:-$(cat "$ETC/alan" 2>/dev/null || true)}"
cd /tmp
maskele() { sed -E 's/[0-9]{7,}/[…]/g; s/wamid\.[A-Za-z0-9=._-]+/wamid.[…]/g'; }
echo "== Portman durum · salt okunur · $(date '+%Y-%m-%d %H:%M:%S %Z') · alan: ${ALAN:-?}"
echo "-- sürüm"
echo "   guncel: $( [ -L "$KOK/guncel" ] && cat "$KOK/guncel/SURUM" 2>/dev/null || echo yok ) · onceki: $( [ -L "$KOK/onceki" ] && cat "$KOK/onceki/SURUM" 2>/dev/null || echo yok ) · sürüm dizinleri: $(ls -1d "$KOK/surumler"/*/ 2>/dev/null | wc -l)"
echo "   perspektif (VTK, BK-07): $(cat "$KOK/guncel/PERSPEKTIF" 2>/dev/null || echo 'kayıt yok (bu sürümde denenmedi)')"
echo "   genel motor (İE-08): $(cat "$KOK/guncel/GENEL" 2>/dev/null || echo 'kayıt yok (bu sürümde denenmedi)')"
echo "-- çekirdek (BK-07)"
REBOOT_REQ="${PM_REBOOT_REQ:-/var/run/reboot-required}"; BOOT_DIR="${PM_BOOT_DIR:-/boot}"
KURULU="$(ls -1 "$BOOT_DIR"/vmlinuz-* 2>/dev/null | sed 's/.*vmlinuz-//' | sort -V | tail -1 || true)"
echo "   çalışan: $(uname -r) · kurulu en yeni: ${KURULU:-?} · yeniden başlatma gerekli: $([ -f "$REBOOT_REQ" ] && echo evet || echo hayır) · açılış: $(uptime -s 2>/dev/null || echo '?')"
echo "-- servisler"
for s in portman-webhook portman-gonderici portman-agent portman-panel portman-yedek.timer portman-nabiz.timer nginx postgresql fail2ban; do
  printf '   %-22s %s\n' "$s" "$($SYSTEMCTL is-active "$s" 2>/dev/null || echo '?')"
done
echo "-- sağlık ($SAGLIK_URL)"
echo "   $(curl -s --max-time 5 -w ' [HTTP %{http_code}]' "$SAGLIK_URL" 2>/dev/null | head -c 400 || echo 'cevap yok')"
echo "-- sertifika"
if [ -n "$ALAN" ] && [ -f "$LE_DIR/live/$ALAN/fullchain.pem" ]; then
  echo "   bitiş: $(openssl x509 -enddate -noout -in "$LE_DIR/live/$ALAN/fullchain.pem" 2>/dev/null | cut -d= -f2)"
else
  echo "   yok"
fi
echo "-- ufw"
$UFW status 2>/dev/null | grep -E '^(Status|[0-9]+/tcp)' | sed 's/^/   /' || echo "   okunamadı"
echo "-- sshd etkin değerler"
{ $SSHD -T 2>/dev/null || true; } | awk 'tolower($1) ~ /^(passwordauthentication|permitrootlogin|kbdinteractiveauthentication|pubkeyauthentication)$/ {print "   " $0}'
echo "-- disk"
df -h "$KOK" 2>/dev/null | awk 'NR==2 {printf "   %s kullanılan %s / %s (%s)\n", $6, $3, $2, $5}'
echo "-- Postgres (portman) sayımlar"
SQL="SELECT 'bayi(aktif) '||(SELECT count(*) FROM bayiler WHERE aktif)||' · mesaj '||(SELECT count(*) FROM mesajlar)||' · iş '||(SELECT count(*) FROM isler)||' · açık iş '||(SELECT count(*) FROM isler WHERE durum IN ('sirada','isleniyor'))||' · giden '||(SELECT count(*) FROM giden)||' · bekleyen giden '||(SELECT count(*) FROM giden WHERE durum = 'bekliyor')||' · son 24 saat gelen '||(SELECT count(*) FROM mesajlar WHERE alindi >= now() - interval '24 hours')||' · panel kilit (24 saat) '||(SELECT count(*) FROM panel_girisler WHERE sonuc = 'kilitli' AND zaman >= now() - interval '24 hours')||' · şema '||(SELECT max(surum) FROM sema_surumu)"
OUT="$($PSQL -c "$SQL" 2>&1)" && echo "   $OUT" || echo "   sorgu başarısız: $(echo "$OUT" | head -1 | cut -c1-120)"
echo "-- nabız dosyaları ($DATA/nabiz)"
for f in agent gonderici yedek nabiz; do
  if [ -f "$DATA/nabiz/$f.json" ]; then
    printf '   %-10s %s\n' "$f" "$(python3 -c 'import json,sys,time; d=json.load(open(sys.argv[1])); z=int(d.get("zaman",0)); print(f"{int(time.time())-z} sn önce", {k:v for k,v in d.items() if k in ("surum","enabled","bitti","basarisiz","sorunlar","dosya","boyut")})' "$DATA/nabiz/$f.json" 2>/dev/null)"
  else
    printf '   %-10s yok\n' "$f"
  fi
done
echo "-- son günlük (10 satır; maskeli)"
for s in portman-webhook portman-gonderici portman-agent portman-panel; do
  echo "   [$s]"; $JOURNALCTL -u "$s" -n 10 --no-pager -o cat 2>/dev/null | maskele | cut -c1-160 | sed 's/^/      /' || echo "      okunamadı"
done
echo "== bitti"
