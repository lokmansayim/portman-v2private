#!/usr/bin/env bash
# PORTMAN · sunucuyu yeniden başlat (BK-07 S5; root). Önce salt okunur bölüm: çalışan ve kurulu çekirdek, /var/run/reboot-required,
# açılış zamanı, açık iş, bekleyen giden, son yedek yaşı. Açık iş ya da bekleyen giden varsa DURUR (PM_ZORLA=1 ile geçilir).
# Sonra `systemctl reboot`: ssh bağlantısı kopar (beklenen; Mac'te exit 255). Servisler systemd ile kendiliğinden kalkar
# (WantedBy=multi-user.target; 10 Ekim 14:00 yeniden başlatmasında görüldü). Doğrulama 2–3 dk sonra durum.sh ile.
# Nabız: makine kapalıyken koşamaz; açılışta zamanlayıcı sonraki 5 dk sınırında koşar, ajan ve gönderici saniyeler içinde nabız
# yazar; bir servis kalkmazsa Patron'a uyarı gider (istenen davranış). Veritabanına, sürüm bağlantılarına ve nginx'e dokunmaz.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/yeniden_baslat.sh' > bk07_4_reboot.txt 2>&1
#   (2–3 dk sonra) ssh portman-vps 'bash /opt/portman/guncel/vps/durum.sh' > bk07_4b_durum.txt 2>&1
# Sınama: PM_KOK, PM_SYSTEMCTL, PM_PSQL, PM_REBOOT_REQ, PM_BOOT_DIR, PM_TEST=1 (reboot çağrılmaz), PM_ZORLA=1.
set -uo pipefail
KOK="${PM_KOK:-/opt/portman}"; SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; TEST="${PM_TEST:-}"; ZORLA="${PM_ZORLA:-}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"
REBOOT_REQ="${PM_REBOOT_REQ:-/var/run/reboot-required}"; BOOT_DIR="${PM_BOOT_DIR:-/boot}"
dur() { echo "DUR: $*" >&2; echo "== bitti (yeniden başlatılmadı)"; exit 1; }
cd /tmp
echo "== Portman yeniden başlatma · $(date '+%Y-%m-%d %H:%M:%S %Z')"
if [ -z "$TEST" ]; then [ "$(id -u)" = "0" ] || dur "root olarak çalıştırılmalı"; fi
KURULU="$(ls -1 "$BOOT_DIR"/vmlinuz-* 2>/dev/null | sed 's/.*vmlinuz-//' | sort -V | tail -1 || true)"
echo "-- çekirdek: çalışan $(uname -r) · kurulu en yeni ${KURULU:-?} · yeniden başlatma gerekli: $([ -f "$REBOOT_REQ" ] && echo evet || echo hayır)"
[ -s "$REBOOT_REQ.pkgs" ] && echo "   paketler: $(sort -u "$REBOOT_REQ.pkgs" | tr '\n' ' ')"
echo "-- açılış: $(uptime -s 2>/dev/null || echo '?') · $(uptime -p 2>/dev/null || echo '?')"
ACIK_IS="$($PSQL -c "SELECT count(*) FROM isler WHERE durum IN ('sirada','isleniyor')" 2>/dev/null | head -1 || echo '?')"
BEKLEYEN="$($PSQL -c "SELECT count(*) FROM giden WHERE durum = 'bekliyor'" 2>/dev/null | head -1 || echo '?')"
YEDEK="$(python3 -c 'import json,sys,time; d=json.load(open(sys.argv[1])); z=int(d.get("zaman",0)); print(f"{(int(time.time())-z)//3600} saat önce" if z else "hiç")' "$KOK/data/nabiz/yedek.json" 2>/dev/null || echo 'kayıt yok')"
echo "-- ön kontrol: açık iş ${ACIK_IS} · bekleyen giden ${BEKLEYEN} · son yedek $YEDEK · guncel $(cat "$KOK/guncel/SURUM" 2>/dev/null || echo '?')"
if [ "$ACIK_IS" != "0" ] || [ "$BEKLEYEN" != "0" ]; then
  [ -n "$ZORLA" ] || dur "açık iş ya da bekleyen giden var; bitmesini bekleyin ya da PM_ZORLA=1"
  echo "   PM_ZORLA: ön kontrol uyarısına rağmen devam"
fi
echo "-- yeniden başlatılıyor · $(date '+%H:%M:%S') · ssh bağlantısı kopar (beklenen; exit 255). 2–3 dk sonra: bash /opt/portman/guncel/vps/durum.sh"
if [ -n "$TEST" ]; then echo "   PM_TEST: systemctl reboot çağrılmadı"; echo "== bitti"; exit 0; fi
sync
exec $SYSTEMCTL reboot
