#!/usr/bin/env bash
# PORTMAN · nginx yapılandırmasını sürümden uygula (BK-07 S2; root). vps/guncelle.sh her sürümde [7/7] adımı olarak çağırır;
# tek başına da koşar (belgelenmiş tek seferlik adım). Sürüm dizinindeki vps/nginx/portman.conf'u kurulum.sh gibi işler
# (__ALAN__ → /etc/portman/alan; sertifika yoksa 443 bloğu çıkar) ve /etc/nginx/sites-available/portman.conf ile karşılaştırır:
#   aynıysa  → "nginx: değişiklik yok", hiçbir şeye dokunmaz;
#   farklıysa → eski dosyayı portman.conf.onceki-<zaman> olarak saklar (silmez), yenisini yazar, nginx -t; geçerse reload;
#               düşerse eski dosya geri konur ve "UYARI" ile çıkış 1 (nginx'e dokunulmaz; sürüm etkin kalır).
# geri_don.sh nginx'i geri almaz (bilerek): sınır yalnız büyür; önceki sürüm aynı yapılandırmayla çalışır.
# İE-21: yapılandırmadan önce 3D yayın dizinini açar (data/yayin/3d, portman, 755; kanal/ucb_yayin.py yazar, nginx /3d/<anahtar>/ ile sunar)
# ve nginx'in data'dan geçebilmesi için data'ya o+x verir (liste yok). Servisler UMask 0077 ile yazar; data'nın kökünde portman'ın olup
# başkasına açık kalmış bir şey varsa (yayin dışında) o izinleri kapatılır; sahibi başkası olan açık girdinin (ör. root'un ayar.sh ile
# yazdığı settings.json, sır içermez) yalnız adı yazılır, dokunulmaz (servis okuyamaz olmasın). Her sürümde aynı sonucu verir; data yoksa atlanır.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/nginx_uygula.sh /opt/portman/guncel' > bk07_nginx.txt 2>&1
# Sınama: PM_ETC, PM_NGINX_DIR, PM_LE_DIR, PM_ALAN, PM_SYSTEMCTL, PM_DATA, PM_KULLANICI, PM_TEST=1 (nginx -t, reload ve chown atlanır).
set -euo pipefail
SURUM_DIZINI="${1:-/opt/portman/guncel}"
ETC="${PM_ETC:-/etc/portman}"; NGINX_DIR="${PM_NGINX_DIR:-/etc/nginx}"; LE_DIR="${PM_LE_DIR:-/etc/letsencrypt}"
SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; TEST="${PM_TEST:-}"; DATA="${PM_DATA:-/opt/portman/data}"; KULLANICI="${PM_KULLANICI:-portman}"
ALAN="${PM_ALAN:-$(cat "$ETC/alan" 2>/dev/null || true)}"
dur() { echo "UYARI: $*" >&2; echo "nginx: değişmedi"; exit 1; }
SABLON="$SURUM_DIZINI/vps/nginx/portman.conf"
[ -f "$SABLON" ] || dur "şablon yok: $SABLON"
[[ "$ALAN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || dur "alan adı okunamadı ($ETC/alan ya da PM_ALAN)"
if [ -d "$DATA" ]; then
  if [ -z "$TEST" ]; then install -d -m 755 -o "$KULLANICI" -g "$KULLANICI" "$DATA/yayin" "$DATA/yayin/3d"; else install -d -m 755 "$DATA/yayin" "$DATA/yayin/3d"; fi
  chmod o+x "$DATA"
  KAPANDI="$(find "$DATA" -mindepth 1 -maxdepth 1 ! -name yayin -user "$KULLANICI" -perm /o=rwx -printf '%f ' -exec chmod o-rwx {} + 2>/dev/null || true)"
  ACIK="$(find "$DATA" -mindepth 1 -maxdepth 1 ! -name yayin ! -user "$KULLANICI" -perm /o=rwx -printf '%f ' 2>/dev/null || true)"
  echo "yayın: $DATA/yayin/3d hazır (755; data $(stat -c %a "$DATA"))${KAPANDI:+ · başkasına açıktı, kapatıldı: ${KAPANDI% }}${ACIK:+ · sahibi $KULLANICI değil, dokunulmadı: ${ACIK% }}"
else
  echo "yayın: $DATA yok, 3D yayın dizini atlandı"
fi
HEDEF="$NGINX_DIR/sites-available/portman.conf"
SERT="$LE_DIR/live/$ALAN/fullchain.pem"
install -d -m 755 "$NGINX_DIR/sites-available" "$NGINX_DIR/sites-enabled"
YENI="$HEDEF.yeni"
if [ -f "$SERT" ]; then sed "s/__ALAN__/$ALAN/g" "$SABLON" > "$YENI"; BLOK="80+443"
else sed '/# --443-BASLA--/,/# --443-BITIS--/d' "$SABLON" | sed "s/__ALAN__/$ALAN/g" > "$YENI"; BLOK="yalnız 80 (sertifika yok)"; fi
if [ -f "$HEDEF" ] && cmp -s "$HEDEF" "$YENI"; then
  rm -f "$YENI"
  [ -L "$NGINX_DIR/sites-enabled/portman.conf" ] || { ln -sfn "$HEDEF" "$NGINX_DIR/sites-enabled/portman.conf"; echo "nginx: sites-enabled bağı eksikti, yeniden kuruldu (reload gerekir: systemctl reload nginx)"; }
  echo "nginx: değişiklik yok ($HEDEF sürümdeki yapılandırmayla aynı; $BLOK)"
  exit 0
fi
YEDEK=""
if [ -f "$HEDEF" ]; then
  YEDEK="$HEDEF.onceki-$(date +%Y%m%d%H%M%S)"; n=1
  while [ -e "$YEDEK" ]; do YEDEK="$HEDEF.onceki-$(date +%Y%m%d%H%M%S)-$n"; n=$((n + 1)); done   # aynı saniyede ikinci yedek ezilmesin
  cp -p "$HEDEF" "$YEDEK"
fi
mv -f "$YENI" "$HEDEF"
ln -sfn "$HEDEF" "$NGINX_DIR/sites-enabled/portman.conf"
if [ -z "$TEST" ]; then
  if ! nginx -t 2>"$HEDEF.nginx_t"; then
    if [ -n "$YEDEK" ]; then cp -p "$YEDEK" "$HEDEF"; else rm -f "$HEDEF" "$NGINX_DIR/sites-enabled/portman.conf"; fi
    sed 's/^/   /' "$HEDEF.nginx_t" >&2; rm -f "$HEDEF.nginx_t"
    dur "nginx -t geçmedi; önceki dosya geri kondu${YEDEK:+ ($YEDEK)}, nginx yeniden yüklenmedi"
  fi
  rm -f "$HEDEF.nginx_t"
  if ! $SYSTEMCTL reload nginx; then
    if [ -n "$YEDEK" ]; then cp -p "$YEDEK" "$HEDEF"; else rm -f "$HEDEF" "$NGINX_DIR/sites-enabled/portman.conf"; fi
    dur "nginx yeniden yüklenemedi (systemctl status nginx); önceki dosya geri kondu${YEDEK:+ ($YEDEK)}, çalışan nginx değişmedi"
  fi
fi
PANEL="$(grep -o 'location /panel/.*client_max_body_size [0-9]*m' "$HEDEF" | grep -o '[0-9]*m$' || true)"
echo "nginx: uygulandı ($BLOK; /panel/ ${PANEL:-yok (443 bloğu yok)}$([ -n "$TEST" ] && echo '; PM_TEST: nginx -t ve reload atlandı' || echo '; nginx -t tamam, yeniden yüklendi')) · yedek: ${YEDEK:-yok (ilk yazım)}"
