#!/usr/bin/env bash
# PORTMAN · Montaj rehberini rehber.portatifev.com'da statik yayınla (kart 104, 25.10.2026; root).
# Tek dosya olarak koşar: deneme/2026-10-24_montaj_rehberi/yayin/paketle.py paketi aşağıdaki işaretin yerine gömer
# (cikti/rehber_kur.sh). Bu dosyanın kendisi paketsizdir; doğrudan koşulursa "paket gömülü değil" der.
# Mac'ten (Lokman):
#   kuru koşu : ssh portman-vps 'timeout 300 bash -s -- --dene'   < rehber_kur.sh > rehber_dene.txt 2>&1
#   uygula    : ssh portman-vps 'timeout 300 bash -s -- --uygula' < rehber_kur.sh > rehber_uygula.txt 2>&1
#   geri al   : ssh portman-vps 'timeout 300 bash -s -- --geri'   < rehber_kur.sh > rehber_geri.txt 2>&1
# Dokunduğu yerler: /var/www/rehber (surumler/<zaman> + guncel bağı + onceki), /etc/nginx/sites-available/rehber.conf
#   (+ sites-enabled bağı), Let's Encrypt'te yeni rehber.portatifev.com sertifikası (webroot /var/www/portman-acme; mevcut hesap).
# Dokunmadığı: portman.conf, Portman servisleri, ufw, veritabanı, /etc/portman. Canlı /saglik önce ve sonra ölçülür.
# Geri dönüş (--geri): önceki rehber sürümü varsa ona döner; yoksa rehber.conf nginx'ten çıkarılır (dosya .kapali-<zaman>
#   adıyla saklanır), nginx -t + reload. Dosyalar ve sertifika yerinde kalır (silme ayrı onay).
# Çıktıda sır yok: yalnız durum, yol, başlık ve sağlık kodu yazılır.
set -euo pipefail
MOD="${1:---dene}"
ALAN=rehber.portatifev.com
CANLI=portman.portatifev.com
KOK=/var/www/rehber
WEBROOT=/var/www/portman-acme
NG=/etc/nginx
CONF=$NG/sites-available/rehber.conf
BAG=$NG/sites-enabled/rehber.conf
LE=/etc/letsencrypt/live/$ALAN
ZAMAN=$(date +%Y%m%d%H%M%S)

# __PAKET_YERI__

dur() { echo "DUR: $*"; echo "== sonuç: durdu ($MOD); yukarıdaki satırlar neyin değiştiğini söyler"; exit 1; }
adim() { echo; echo "[$1] $2"; }
saglik() { curl -s -o /dev/null -m 10 -w '%{http_code}' "https://$CANLI/saglik" </dev/null || true; }
servisler() {
  local s
  for s in nginx portman-webhook portman-agent portman-gonderici portman-panel; do
    printf '%s=%s ' "$s" "$(systemctl is-active "$s" 2>/dev/null || true)"
  done
  echo
}
nginx_t() { nginx -t >"$TMP/nginx_t.txt" 2>&1 || { sed 's/^/   /' "$TMP/nginx_t.txt"; return 1; }; }

conf_80() {
  cat <<EOF
# Montaj rehberi · statik, herkese açık (kart 104). vps/rehber_yayin.sh yazar; elle değiştirme.
limit_req_zone \$binary_remote_addr zone=rh_genel:5m rate=20r/s;
log_format rh_kisa '\$remote_addr \$request_method \$uri \$status \$body_bytes_sent \$request_time';

server {
    listen 80;
    listen [::]:80;
    server_name $ALAN;
    server_tokens off;
    access_log /var/log/nginx/rehber.access.log rh_kisa;
    location ^~ /.well-known/acme-challenge/ { root $WEBROOT; }
    location / { return 301 https://\$host\$request_uri; }
}
EOF
}

conf_443() {   # $1 sertifika klasörü
  cat <<EOF

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $ALAN;
    server_tokens off;
    access_log /var/log/nginx/rehber.access.log rh_kisa;

    ssl_certificate $1/fullchain.pem;
    ssl_certificate_key $1/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_tickets off;

    root $KOK/guncel;
    index index.html;
    autoindex off;
    charset utf-8;
    client_max_body_size 1k;
    limit_req zone=rh_genel burst=100 nodelay;
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types application/javascript text/css application/json image/svg+xml;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy no-referrer always;
    add_header X-Robots-Tag "noindex, nofollow" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
    add_header Cross-Origin-Opener-Policy same-origin always;

    location = /index.html { limit_except GET HEAD { deny all; } expires -1; }
    location = /SHA256SUMS { return 404; }
    location ~ /\. { return 404; }
    location / { limit_except GET HEAD { deny all; } try_files \$uri \$uri/ =404; expires 7d; }
}
EOF
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

adim 0 "Ön koşullar ($MOD)"
case "$MOD" in --dene|--uygula|--geri) ;; *) dur "bilinmeyen mod: $MOD (--dene | --uygula | --geri)";; esac
[ "$(id -u)" = 0 ] || dur "root olarak koşmalı"
for k in nginx certbot curl sha256sum tar base64 getent; do command -v "$k" >/dev/null || dur "$k yok"; done
[ -f "$NG/sites-available/portman.conf" ] || dur "portman.conf yok; bu betik canlı Portman sunucusu için"
[ -d "$WEBROOT" ] || dur "ACME klasörü yok: $WEBROOT"
nginx_t || dur "nginx -t şu anda da geçmiyor; hiçbir şeye dokunulmadı"
echo "   nginx -t: tamam (değişiklikten önce)"
DIGER=$(grep -rlE "server_name[^;]*\b$ALAN\b" "$NG/sites-enabled/" 2>/dev/null | grep -v '/rehber.conf$' || true)
[ -z "$DIGER" ] || dur "$ALAN başka bir sitede tanımlı: $DIGER"
SAGLIK_ONCE=$(saglik)
echo "   canlı $CANLI/saglik önce: $SAGLIK_ONCE"
echo "   servisler önce: $(servisler)"
echo "   rehber şu an: $({ [ -L "$KOK/guncel" ] && readlink -f "$KOK/guncel"; } || echo 'kurulu değil') · nginx sitesi: $([ -L "$BAG" ] && echo açık || echo yok) · sertifika: $([ -f "$LE/fullchain.pem" ] && echo var || echo yok)"

if [ "$MOD" = --geri ]; then
  adim 1 "Geri dönüş"
  ONCEKI=$(cat "$KOK/onceki" 2>/dev/null || true)
  SIMDI=$({ [ -L "$KOK/guncel" ] && readlink -f "$KOK/guncel"; } || true)
  if [ -n "$ONCEKI" ] && [ -d "$ONCEKI" ] && [ "$ONCEKI" != "$SIMDI" ]; then
    ln -sfn "$ONCEKI" "$KOK/guncel.yeni" && mv -Tf "$KOK/guncel.yeni" "$KOK/guncel"
    echo "$SIMDI" > "$KOK/onceki"
    echo "   rehber önceki sürüme döndü: $ONCEKI (nginx değişmedi; tekrar --geri bu sürüme geri getirir)"
  elif [ -f "$CONF" ] || [ -L "$BAG" ]; then
    rm -f "$BAG"
    if ! nginx_t; then ln -sfn "$CONF" "$BAG"; dur "nginx -t rehber çıkarılınca geçmedi; bağ geri kondu, reload yok"; fi
    systemctl reload nginx
    [ -f "$CONF" ] && mv -f "$CONF" "$CONF.kapali-$ZAMAN"
    echo "   rehber nginx'ten çıkarıldı; yapılandırma $CONF.kapali-$ZAMAN olarak saklandı; dosyalar ve sertifika yerinde"
  else
    echo "   geri alınacak bir şey yok"
  fi
  echo "   canlı /saglik sonra: $(saglik) (önce $SAGLIK_ONCE)"
  echo "   servisler sonra: $(servisler)"
  echo "== sonuç: geri dönüş bitti"
  exit 0
fi

adim 1 "Paket"
declare -F paket_yaz >/dev/null || dur "paket gömülü değil; paketle.py'nin ürettiği rehber_kur.sh koşulmalı"
paket_yaz "$TMP/p.tgz"
echo "$PAKET_SHA256  $TMP/p.tgz" | sha256sum -c --quiet - || dur "paket özeti tutmadı (dosya bozulmuş)"
mkdir "$TMP/a"
tar xzf "$TMP/p.tgz" -C "$TMP/a" --no-same-owner --no-same-permissions
( cd "$TMP/a" && sha256sum -c --quiet SHA256SUMS ) || dur "paket içi SHA256SUMS tutmadı"
[ -f "$TMP/a/index.html" ] || dur "pakette index.html yok"
echo "   paket tamam: $(find "$TMP/a" -type f | wc -l) dosya, $(du -sh "$TMP/a" | cut -f1); sha256 ${PAKET_SHA256:0:16}…"

adim 2 "DNS"
YERELLER=$(ip -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | sort -u)
# ahostsv6 IPv4 kaydını ::ffff:a.b.c.d biçiminde de verir; o biçim IPv4'e indirilir (25.10: bu yüzden ilk --uygula durdu)
COZUM=$( { getent ahostsv4 "$ALAN"; getent ahostsv6 "$ALAN"; } 2>/dev/null | awk '{print $1}' | sed 's/^::ffff://I' | sort -u || true)
IPV4=$(echo "$YERELLER" | grep -v ':' | head -1 || true)
echo "   sunucu IPv4: ${IPV4:-?} · $ALAN çözümü: ${COZUM:-(kayıt yok)}"
DNS_OK=1
[ -n "$COZUM" ] || DNS_OK=0
for ip in $COZUM; do echo "$YERELLER" | grep -qxF "$ip" || { DNS_OK=0; echo "   bu sunucuda olmayan adres: $ip"; }; done
if [ "$DNS_OK" = 0 ] && [ -n "$COZUM" ]; then   # NAT arkasında adres arayüzde görünmez: ACME yolundan gerçek erişimi sına
  JETON="rh-$ZAMAN-$$"; install -d -m 755 "$WEBROOT/.well-known/acme-challenge"
  echo "$JETON" > "$WEBROOT/.well-known/acme-challenge/$JETON"
  GELEN=$(curl -s -m 8 "http://$ALAN/.well-known/acme-challenge/$JETON" </dev/null || true)
  rm -f "$WEBROOT/.well-known/acme-challenge/$JETON"
  [ "$GELEN" = "$JETON" ] && { DNS_OK=1; echo "   adres arayüzde yok ama http://$ALAN bu sunucuya ulaşıyor (NAT)"; }
fi
if [ "$DNS_OK" = 1 ]; then echo "   DNS tamam: $ALAN bu sunucuya bakıyor"
else echo "   DNS hazır değil → DirectAdmin › DNS Yönetimi'nde A kaydı: ad 'rehber', değer ${IPV4:-<sunucu IPv4>} (AAAA ekleme)"; fi

if [ "$MOD" = --dene ]; then
  adim 3 "Kuru koşu: yapılandırma sınaması (geçici kopyada; canlı nginx'e dokunulmaz)"
  SERT_DENE="$LE"
  if [ ! -f "$LE/fullchain.pem" ]; then
    if [ -f /etc/ssl/certs/ssl-cert-snakeoil.pem ] && [ -f /etc/ssl/private/ssl-cert-snakeoil.key ]; then
      mkdir -p "$TMP/sert"; cp /etc/ssl/certs/ssl-cert-snakeoil.pem "$TMP/sert/fullchain.pem"
      cp /etc/ssl/private/ssl-cert-snakeoil.key "$TMP/sert/privkey.pem"; SERT_DENE="$TMP/sert"
      echo "   sertifika henüz yok; sınama geçici deneme sertifikasıyla"
    else SERT_DENE=""; echo "   sertifika henüz yok; 443 bloğu sınanmadı (yalnız 80)"; fi
  fi
  { conf_80; [ -n "$SERT_DENE" ] && conf_443 "$SERT_DENE"; } > "$TMP/rehber.conf"
  sed "s#root $KOK/guncel;#root $TMP/a;#" -i "$TMP/rehber.conf"
  cat > "$TMP/nginx.conf" <<EOF
pid $TMP/nginx.pid;
error_log $TMP/error.log;
events {}
http { include $NG/mime.types; $(for f in "$NG"/sites-enabled/*; do [ "$(basename "$f")" = rehber.conf ] || printf 'include %s; ' "$f"; done) include $TMP/rehber.conf; }
EOF
  if nginx -t -c "$TMP/nginx.conf" >"$TMP/t.txt" 2>&1; then echo "   nginx -t (portman.conf + yeni rehber.conf birlikte): tamam"
  else sed 's/^/   /' "$TMP/t.txt"; dur "yeni yapılandırma sınamada geçmedi; hiçbir şey değişmedi"; fi
  adim 4 "Uygulamada olacaklar"
  echo "   1) $KOK/surumler/<zaman>/ kurulur, $KOK/guncel ona bağlanır (önceki sürüm $KOK/onceki'ye yazılır)"
  echo "   2) $CONF yazılır$([ -f "$CONF" ] && echo " (eskisi .onceki-<zaman> olarak saklanır)"); nginx -t; geçmezse eski dosya geri, reload yok"
  [ -f "$LE/fullchain.pem" ] || echo "   3) önce yalnız 80 bloğu → reload → certbot webroot ile $ALAN sertifikası → 443 bloğu → nginx -t → reload"
  echo "   4) sunucu içinden curl ile 200, başlıklar, 404'ler; canlı /saglik önce/sonra karşılaştırılır"
  [ "$DNS_OK" = 1 ] || echo "   ! DNS hazır olmadan --uygula durur (önce A kaydı)"
  echo "== sonuç: kuru koşu bitti, hiçbir şey değişmedi"
  exit 0
fi

# --uygula
[ "$DNS_OK" = 1 ] || dur "DNS henüz bu sunucuya bakmıyor; önce A kaydı (yukarıda). Hiçbir şey değişmedi"

adim 3 "Dosyalar"
install -d -m 755 "$KOK" "$KOK/surumler"
SURUM="$KOK/surumler/$ZAMAN"
cp -r "$TMP/a" "$SURUM"
chown -R root:root "$SURUM"; find "$SURUM" -type d -exec chmod 755 {} +; find "$SURUM" -type f -exec chmod 644 {} +
ESKI=$({ [ -L "$KOK/guncel" ] && readlink -f "$KOK/guncel"; } || true)
[ -n "$ESKI" ] && echo "$ESKI" > "$KOK/onceki"
ln -sfn "$SURUM" "$KOK/guncel.yeni" && mv -Tf "$KOK/guncel.yeni" "$KOK/guncel"
echo "   sürüm: $SURUM (önceki: ${ESKI:-yok})"

adim 4 "nginx ve sertifika"
YEDEK=""
if [ -f "$CONF" ]; then YEDEK="$CONF.onceki-$ZAMAN"; cp -p "$CONF" "$YEDEK"; fi
geri_nginx() {
  if [ -n "$YEDEK" ]; then cp -p "$YEDEK" "$CONF"; else rm -f "$CONF" "$BAG"; fi
  if nginx_t; then systemctl reload nginx || true; fi
}
if [ ! -f "$LE/fullchain.pem" ]; then
  conf_80 > "$CONF"; ln -sfn "$CONF" "$BAG"
  nginx_t || { geri_nginx; dur "nginx -t (80 bloğu) geçmedi; eski hâl geri kondu"; }
  systemctl reload nginx || { geri_nginx; dur "reload başarısız; eski hâl geri kondu"; }
  echo "   80 bloğu yayında (ACME için); certbot…"
  if ! certbot certonly --webroot -w "$WEBROOT" -d "$ALAN" --non-interactive --agree-tos --keep-until-expiring -q </dev/null; then
    geri_nginx; dur "certbot başarısız (80 dışarıdan erişilebilir mi, DNS yayıldı mı?); nginx eski hâline döndü"
  fi
  echo "   sertifika alındı: $(openssl x509 -enddate -noout -in "$LE/fullchain.pem" 2>/dev/null | cut -d= -f2)"
fi
{ conf_80; conf_443 "$LE"; } > "$CONF"; ln -sfn "$CONF" "$BAG"
nginx_t || { geri_nginx; dur "nginx -t (tam yapılandırma) geçmedi; eski hâl geri kondu"; }
systemctl reload nginx || { geri_nginx; dur "reload başarısız; eski hâl geri kondu"; }
echo "   nginx: rehber.conf uygulandı, nginx -t tamam, yeniden yüklendi · yedek: ${YEDEK:-yok (ilk yazım)}"

adim 5 "Doğrulama (sunucu içinden)"
sleep 1
R=(--noproxy '*' --resolve "$ALAN:443:127.0.0.1" --resolve "$ALAN:80:127.0.0.1" -s -m 10 ${RH_CURL_EK:-})
kod() { curl "${R[@]}" -o /dev/null -w '%{http_code}' "$1" </dev/null || true; }
echo "   GET /                     → $(kod "https://$ALAN/")"
echo "   GET /js/three.module.js   → $(kod "https://$ALAN/js/three.module.js")"
echo "   GET /gorsel/ev_on_sag.jpg → $(kod "https://$ALAN/gorsel/ev_on_sag.jpg")"
echo "   GET /gorsel/ (liste)      → $(kod "https://$ALAN/gorsel/") (403/404 beklenir)"
echo "   GET /SHA256SUMS           → $(kod "https://$ALAN/SHA256SUMS") (404 beklenir)"
echo "   POST /                    → $(curl "${R[@]}" -o /dev/null -w '%{http_code}' -X POST "https://$ALAN/" </dev/null || true) (403 beklenir)"
echo "   http:// yönlendirme       → $(kod "http://$ALAN/") (301 beklenir)"
echo "   başlıklar:"
curl "${R[@]}" -I "https://$ALAN/" </dev/null | grep -iE '^(HTTP|content-type|cache-control|strict|x-content|x-frame|referrer|x-robots|permissions|cross-origin)' | sed 's/^/     /' || true
SAGLIK_SONRA=$(saglik)
echo "   canlı $CANLI/saglik sonra: $SAGLIK_SONRA (önce $SAGLIK_ONCE)"
echo "   servisler sonra: $(servisler)"
[ "$SAGLIK_SONRA" = "$SAGLIK_ONCE" ] || echo "UYARI: canlı sağlık kodu değişti; gerekirse --geri"
echo "== sonuç: yayında https://$ALAN/ · sürüm $ZAMAN"
