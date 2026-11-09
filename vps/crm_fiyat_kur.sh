#!/usr/bin/env bash
# PORTMAN · CRM fiyat zamanlayıcısını çalışan sunucuya kurar (İE-35, D-72; root; bir kez, İE-35'i taşıyan sürüm guncelle.sh ile
# kurulduktan sonra). Yeni sunucuda kurulum.sh aynı birimleri zaten yazar; bu betik yalnız var olan sunucu içindir. TEKRAR KOŞULABİLİR.
# Yaptıkları: sürümdeki vps/systemd/portman-crm-fiyat.{service,timer} → /etc/systemd/system (aynıysa dokunmaz); daemon-reload;
# zamanlayıcıyı etkinleştirir (her gün 06:15); çekimi bir kez hemen koşar ve sonucunu yazar. Hiçbir şey silmez; servislere dokunmaz.
#   ssh -n portman-vps 'timeout 180 bash /opt/portman/guncel/vps/crm_fiyat_kur.sh' > crm_fiyat_kur.txt 2>&1
# Sınama: PM_KOK, PM_GUNCEL, PM_SYSTEMD_DIR, PM_SYSTEMCTL, PM_JOURNALCTL.
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; GUNCEL="${PM_GUNCEL:-$KOK/guncel}"
SYSTEMD_DIR="${PM_SYSTEMD_DIR:-/etc/systemd/system}"; SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; JOURNALCTL="${PM_JOURNALCTL:-journalctl}"
dur() { echo "DUR: $*" >&2; exit 1; }
echo "== Portman CRM fiyat zamanlayıcısı kurulumu · $(date '+%Y-%m-%d %H:%M:%S %Z')"
[ -f "$GUNCEL/vps/crm_fiyat.sh" ] || dur "$GUNCEL/vps/crm_fiyat.sh yok: önce İE-35'i taşıyan sürümü guncelle.sh ile kurun"
install -d -m 755 "$SYSTEMD_DIR"
for b in portman-crm-fiyat.service portman-crm-fiyat.timer; do
  KAYNAK="$GUNCEL/vps/systemd/$b"
  [ -f "$KAYNAK" ] || dur "$KAYNAK yok"
  if cmp -s "$KAYNAK" "$SYSTEMD_DIR/$b"; then
    echo "   $b aynı, dokunulmadı"
  else
    install -m 644 "$KAYNAK" "$SYSTEMD_DIR/$b"; echo "   $b yazıldı"
  fi
done
$SYSTEMCTL daemon-reload
$SYSTEMCTL enable --now portman-crm-fiyat.timer >/dev/null 2>&1 || dur "zamanlayıcı etkinleştirilemedi (journalctl -u portman-crm-fiyat.timer)"
echo "   zamanlayıcı: $($SYSTEMCTL is-enabled portman-crm-fiyat.timer 2>/dev/null || true) / $($SYSTEMCTL is-active portman-crm-fiyat.timer 2>/dev/null || true)"
echo "-- ilk çekim (portman-crm-fiyat.service)"
SONUC=0; $SYSTEMCTL start portman-crm-fiyat.service || SONUC=$?
$JOURNALCTL -u portman-crm-fiyat.service -n 12 --no-pager -o cat 2>/dev/null || true
[ "$SONUC" = 0 ] || dur "ilk çekim başarısız (çıkış $SONUC); zamanlayıcı kurulu, yarın 06:15'te yeniden dener"
echo "   son çekim: $(cat "$KOK/data/crm/son_cekim.json" 2>/dev/null || echo yok)"
$SYSTEMCTL list-timers portman-crm-fiyat.timer --no-pager 2>/dev/null | head -3 || true
echo "== bitti"
