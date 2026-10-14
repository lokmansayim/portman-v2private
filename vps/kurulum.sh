#!/usr/bin/env bash
# PORTMAN · VPS kurulumu (İE-06, Kapı 2; Ubuntu 24.04, root olarak; TEKRAR KOŞULABİLİR: var olanı bozmaz, sır yazdırmaz, hiçbir
# şey silmez). Depo sunucuda henüz yokken stdin'den koşar; bu yüzden birim ve yapılandırma dosyaları bu betiğin içinde gömülüdür
# (vps/systemd, vps/nginx, vps/sshd, vps/fail2ban, vps/logrotate altındaki dosyalarla birebir aynı; test_kurulum.py denetler).
#   ssh portman-vps 'PM_ALAN=portman.portatifev.com PM_EPOSTA=<e-posta> bash -s' < vps/kurulum.sh > ie06_2_kurulum.txt 2>&1
# Yaptıkları: paketler; saat dilimi; 'portman' kullanıcısı; /opt/portman/{surumler,data,logs,kaynak} ve /etc/portman (700);
# dağıtım anahtarı (ed25519; yalnız AÇIK anahtar ekrana); Postgres yalnız yerel (pg_kurulum.sh'nin denetimleri), 'portman' rolü
# (peer, parolasız), boş 'portman' veritabanı; nginx (80: ACME + https'e yönlendirme; sertifika varsa 443: yalnız /webhook,
# /saglik, /panel/); certbot (alan adı bu sunucuya bakıyorsa; bakmıyorsa atlar ve söyler); ufw (gelen reddet; 22/80/443);
# fail2ban; sshd parolasız giriş (YALNIZ authorized_keys doluysa; sözdizimi geçmezse drop-in geri alınır); unattended-upgrades;
# systemd birimleri (etkin; servisler ilk sürümle, guncelle.sh ile başlar); settings.json (enabled false, dry_run true, patron);
# panel.env'de oturum anahtarı (yazdırılmaz). DURUR: PM_ALAN yoksa; Postgres yerel dışı dinliyorsa; 'portman' veritabanının sahibi
# başkaysa; certbot ya da nginx yapılandırması başarısızsa.
# Yapmadıkları: sürüm kurmaz (guncelle.sh), sır koymaz (sir_koy.py, panel_parola.py, yedek_kur.sh), Meta'ya dokunmaz.
# Sınama: PM_TEST=1 (apt, kullanıcı, certbot, ufw, fail2ban, sshd reload, nginx -t atlanır) + PM_KOK, PM_ETC, PM_SYSTEMD_DIR,
# PM_NGINX_DIR, PM_SSHD_DIR, PM_SSH_YETKILI, PM_FAIL2BAN_DIR, PM_LOGROTATE_DIR, PM_LE_DIR, PM_WEBROOT, PM_SYSTEMCTL, PM_SSHD,
# PM_SSH_KEYGEN, PM_SUNUCU_IP, PM_DNS_IP, PM_PG, PM_PG_PORTMAN, PM_PG_PORT, PM_DB; PM_YALNIZ_ISLEVLER=1 yalnız işlevleri yükler.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_SUSPEND=1 NEEDRESTART_MODE=l
TEST="${PM_TEST:-}"
ALAN="${PM_ALAN:-}"; EPOSTA="${PM_EPOSTA:-}"
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"
SYSTEMD_DIR="${PM_SYSTEMD_DIR:-/etc/systemd/system}"; NGINX_DIR="${PM_NGINX_DIR:-/etc/nginx}"
SSHD_DIR="${PM_SSHD_DIR:-/etc/ssh/sshd_config.d}"; SSH_YETKILI="${PM_SSH_YETKILI:-/root/.ssh/authorized_keys}"
F2B_DIR="${PM_FAIL2BAN_DIR:-/etc/fail2ban/jail.d}"; LOGROTATE_DIR="${PM_LOGROTATE_DIR:-/etc/logrotate.d}"
LE_DIR="${PM_LE_DIR:-/etc/letsencrypt}"; WEBROOT="${PM_WEBROOT:-/var/www/portman-acme}"
SSHD="${PM_SSHD:-sshd}"; SSH_KEYGEN="${PM_SSH_KEYGEN:-ssh-keygen}"
DB="${PM_DB:-portman}"; PORT="${PM_PG_PORT:-5432}"; KULLANICI="${PM_KULLANICI:-portman}"
if [ -n "$TEST" ]; then
  read -r -a PG <<< "${PM_PG:-}"; read -r -a PG_PORTMAN <<< "${PM_PG_PORTMAN:-}"; SU=(); SU_PORTMAN=(); SYSTEMCTL="${PM_SYSTEMCTL:-true}"
else
  PG=(); PG_PORTMAN=(); SU=(sudo -u postgres); SU_PORTMAN=(sudo -u "$KULLANICI"); SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"
fi

dur() { echo "DUR: $*" >&2; exit 1; }
psql_su() { "${SU[@]}" psql -X -q -v ON_ERROR_STOP=1 "${PG[@]}" "$@"; }
kimlik() { [[ "$1" =~ ^[a-z_][a-z0-9_]*$ ]] || dur "geçersiz ad: $1"; }

# Yalnız yerel dinleme: listen_addresses'in her öğesi localhost / 127.0.0.1 / ::1 olmalı (boş: yalnız Unix soketi).
yerel_dinleme() {
  local a
  IFS=',' read -r -a _ogeler <<< "$1"
  for a in "${_ogeler[@]}"; do
    a="$(echo "$a" | tr -d '[:space:]')"
    case "$a" in ""|localhost|127.0.0.1|::1) ;; *) return 1 ;; esac
  done
  return 0
}
# pg_hba: TCP kuralları ('host…') yalnız yerel adresler için olabilir.
yerel_hba() {
  local satir
  while IFS= read -r satir; do
    [ -z "$satir" ] && continue
    case "$satir" in 127.0.0.1|::1|localhost|samehost) ;; *) return 1 ;; esac
  done <<< "$1"
  return 0
}
# ss çıktısında 5432'yi dinleyen her adres yerel olmalı.
yerel_soketler() {
  local adres
  while IFS= read -r adres; do
    [ -z "$adres" ] && continue
    case "$adres" in 127.0.0.1:"$PORT"|"[::1]:$PORT"|"::1:$PORT") ;; *) return 1 ;; esac
  done <<< "$1"
  return 0
}

# ───────── gömülü dosyalar (vps/systemd, vps/nginx, vps/sshd, vps/fail2ban, vps/logrotate ile birebir aynı) ─────────
nginx_sablon() { cat <<'EOF'
# Portman · nginx sitesi (İE-06). kurulum.sh __ALAN__ yerine alan adını yazar; sertifika yoksa 443 bloğunu (BASLA..BITIS) çıkarır.
# Dışa açık yollar yalnız: /webhook (Meta), /saglik (dış izleyici), /panel/ (yönetici). Gerisi 404. Erişim günlüğünde sorgu dizesi yok
# (hub.verify_token GET sorgusunda gelir; $uri onu içermez); /panel/ yolları günlüğe hiç yazılmaz (URL'de numara var; K09).
# Ubuntu 24.04'ün nginx'i 1.24: "http2 on;" yönergesi yok, http2 listen parametresiyle verilir.
log_format pm_kisa '$remote_addr $request_method $uri $status $body_bytes_sent $request_time';
limit_req_zone $binary_remote_addr zone=pm_giris:1m rate=10r/m;
limit_req_zone $binary_remote_addr zone=pm_genel:10m rate=30r/s;

server {
    listen 80;
    listen [::]:80;
    server_name __ALAN__;
    server_tokens off;
    access_log /var/log/nginx/portman.access.log pm_kisa;
    location ^~ /.well-known/acme-challenge/ { root /var/www/portman-acme; }
    location / { return 301 https://$host$request_uri; }
}

# --443-BASLA--
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name __ALAN__;
    server_tokens off;
    access_log /var/log/nginx/portman.access.log pm_kisa;

    ssl_certificate /etc/letsencrypt/live/__ALAN__/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/__ALAN__/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:pm_ssl:5m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy no-referrer always;
    client_max_body_size 3m;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_read_timeout 30s;

    location = /webhook { limit_req zone=pm_genel burst=50 nodelay; proxy_pass http://127.0.0.1:8081; }
    location = /saglik { limit_req zone=pm_genel burst=20 nodelay; proxy_pass http://127.0.0.1:8081; }
    location = /panel/giris { limit_req zone=pm_giris burst=5 nodelay; access_log off; proxy_pass http://127.0.0.1:8082; }
    location /panel/ { limit_req zone=pm_genel burst=50 nodelay; access_log off; client_max_body_size 12m; proxy_pass http://127.0.0.1:8082; }   # İE-07: panelden PDF (10 MiB)
    location = /panel { return 301 /panel/; }
    location / { return 404; }
}
# --443-BITIS--
EOF
}

sshd_sablon() { cat <<'EOF'
# Portman · sshd sertleştirme (İE-06, BK-04'ten). Ubuntu 24.04 sshd_config.d dosyalarını ad sırasıyla okur ve İLK değeri kullanır;
# bu dosya 50-cloud-init.conf'tan önce okunsun diye 00- ile başlar. kurulum.sh yalnız authorized_keys doluysa yazar.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
EOF
}

fail2ban_sablon() { cat <<'EOF'
# Portman · fail2ban jail'leri (İE-06). sshd: parola kapalı olsa da anahtar denemeleri; nginx-limit-req: hız sınırını aşan IP'ler.
[DEFAULT]
bantime = 1h
findtime = 10m

[sshd]
enabled = true
backend = systemd
maxretry = 5

[nginx-limit-req]
enabled = true
logpath = /var/log/nginx/error.log
maxretry = 10
EOF
}

logrotate_sablon() { cat <<'EOF'
/opt/portman/logs/*.log {
    weekly
    rotate 8
    compress
    delaycompress
    missingok
    notifempty
    create 0640 portman portman
}
EOF
}

birim_sablon() {   # $1: birim adı
  case "$1" in
  portman-webhook.service) cat <<'EOF'
[Unit]
Description=Portman Meta webhook (gunicorn, 127.0.0.1:8081)
After=network-online.target postgresql.service
Wants=network-online.target
ConditionPathExists=/opt/portman/guncel/SURUM

[Service]
Type=simple
User=portman
Group=portman
WorkingDirectory=/opt/portman/guncel
EnvironmentFile=-/etc/portman/whatsapp.env
Environment=PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=/opt/portman/data PYTHONUNBUFFERED=1 HOME=/opt/portman/data
ExecStart=/opt/portman/guncel/venv/bin/gunicorn --chdir /opt/portman/guncel/kanal --bind 127.0.0.1:8081 --workers 2 --timeout 60 --access-logfile - --access-logformat "%%(h)s %%(m)s %%(U)s %%(s)s %%(B)s %%(M)sms" webhook:uygulama
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/portman/data
UMask=0077

[Install]
WantedBy=multi-user.target
EOF
  ;;
  portman-panel.service) cat <<'EOF'
[Unit]
Description=Portman yönetim paneli (gunicorn, 127.0.0.1:8082)
After=network-online.target postgresql.service
Wants=network-online.target
ConditionPathExists=/opt/portman/guncel/SURUM

[Service]
Type=simple
User=portman
Group=portman
WorkingDirectory=/opt/portman/guncel
EnvironmentFile=-/etc/portman/panel.env
Environment=PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=/opt/portman/data PYTHONUNBUFFERED=1 HOME=/opt/portman/data
ExecStart=/opt/portman/guncel/venv/bin/gunicorn --chdir /opt/portman/guncel/kanal --bind 127.0.0.1:8082 --workers 1 --timeout 60 panel:uygulama
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/portman/data
UMask=0077

[Install]
WantedBy=multi-user.target
EOF
  ;;
  portman-agent.service) cat <<'EOF'
[Unit]
Description=Portman ajanı (Beyin + Motor; Postgres kuyruğu)
After=network-online.target postgresql.service
Wants=network-online.target
ConditionPathExists=/opt/portman/guncel/SURUM

[Service]
Type=simple
User=portman
Group=portman
WorkingDirectory=/opt/portman/guncel
EnvironmentFile=-/etc/portman/llm.env
Environment=PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=/opt/portman/data PYTHONUNBUFFERED=1 HOME=/opt/portman/data MPLCONFIGDIR=/opt/portman/data/.mpl
ExecStart=/opt/portman/guncel/venv/bin/python /opt/portman/guncel/vps/agent.py
Restart=always
RestartSec=5
TimeoutStopSec=900
KillMode=mixed
MemoryMax=6G
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/portman/data
UMask=0077

[Install]
WantedBy=multi-user.target
EOF
  ;;
  portman-gonderici.service) cat <<'EOF'
[Unit]
Description=Portman göndericisi (Meta Cloud API; giden kuyruğu, medya)
After=network-online.target postgresql.service
Wants=network-online.target
ConditionPathExists=/opt/portman/guncel/SURUM

[Service]
Type=simple
User=portman
Group=portman
WorkingDirectory=/opt/portman/guncel
EnvironmentFile=-/etc/portman/whatsapp.env
Environment=PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=/opt/portman/data PYTHONUNBUFFERED=1 HOME=/opt/portman/data
ExecStart=/opt/portman/guncel/venv/bin/python /opt/portman/guncel/kanal/gonderici.py
Restart=always
RestartSec=5
TimeoutStopSec=120
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/portman/data
UMask=0077

[Install]
WantedBy=multi-user.target
EOF
  ;;
  portman-yedek.service) cat <<'EOF'
[Unit]
Description=Portman günlük şifreli yedek (pg_dump + data → age → Drive)
After=postgresql.service
ConditionPathExists=/opt/portman/guncel/vps/yedek.sh

[Service]
Type=oneshot
ExecStart=/bin/bash /opt/portman/guncel/vps/yedek.sh
Nice=10
IOSchedulingClass=idle
EOF
  ;;
  portman-yedek.timer) cat <<'EOF'
[Unit]
Description=Portman yedek zamanlayıcısı (her gece 03:40)

[Timer]
OnCalendar=*-*-* 03:40:00
Persistent=true
RandomizedDelaySec=600

[Install]
WantedBy=timers.target
EOF
  ;;
  portman-nabiz.service) cat <<'EOF'
[Unit]
Description=Portman nabız denetimi (servisler, Postgres, sertifika, disk, yedek yaşı; sorunda Patron'a uyarı)
After=postgresql.service network-online.target
ConditionPathExists=/opt/portman/guncel/vps/nabiz.sh

[Service]
Type=oneshot
ExecStart=/bin/bash /opt/portman/guncel/vps/nabiz.sh
EOF
  ;;
  portman-nabiz.timer) cat <<'EOF'
[Unit]
Description=Portman nabız zamanlayıcısı (5 dakikada bir)

[Timer]
OnCalendar=*:0/5
AccuracySec=30s

[Install]
WantedBy=timers.target
EOF
  ;;
  *) return 1 ;;
  esac
}
BIRIMLER="portman-webhook.service portman-panel.service portman-agent.service portman-gonderici.service portman-yedek.service portman-yedek.timer portman-nabiz.service portman-nabiz.timer"

[ -n "${PM_YALNIZ_ISLEVLER:-}" ] && return 0 2>/dev/null   # sınama: yalnız işlevleri yükle

# ───────────────────────── gövde ─────────────────────────
[[ "$ALAN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || dur "PM_ALAN gerekli (ör. PM_ALAN=portman.portatifev.com)"
kimlik "$DB"; kimlik "$KULLANICI"
cd /tmp
if [ -z "$TEST" ]; then [ "$(id -u)" = "0" ] || dur "root olarak çalıştırılmalı"; fi
umask 022
echo "== Portman VPS kurulumu (İE-06) · betik 2026-10-09 · $(date '+%Y-%m-%d %H:%M:%S %Z') · alan: $ALAN${TEST:+ · PM_TEST}"

echo "== [1/9] paketler ve saat dilimi"
if [ -z "$TEST" ]; then
  apt-get update -q
  apt-get install -y -q python3 python3-venv python3-pip git curl ca-certificates openssl postgresql postgresql-client libpq5 nginx certbot \
    ufw fail2ban unattended-upgrades age rclone fonts-dejavu-core >/dev/null
  timedatectl set-timezone Europe/Istanbul || true
  echo "   $(python3 --version 2>&1) · $(psql --version 2>&1) · $(nginx -v 2>&1) · $(age --version 2>&1 | head -1) · $(rclone version 2>/dev/null | head -1)"
else
  echo "   PM_TEST: atlandı"
fi

echo "== [2/9] kullanıcı ve dizinler"
if [ -z "$TEST" ]; then
  id -u "$KULLANICI" >/dev/null 2>&1 || useradd --system --home-dir "$KOK" --shell /usr/sbin/nologin "$KULLANICI"
fi
install -d -m 755 "$KOK" "$KOK/surumler" "$KOK/kaynak" "$WEBROOT"
install -d -m 750 "$KOK/data" "$KOK/data/projects" "$KOK/data/nabiz" "$KOK/logs"
install -d -m 700 "$ETC"
if [ -z "$TEST" ]; then chown -R "$KULLANICI:$KULLANICI" "$KOK/data" "$KOK/logs"; fi
echo "   $KOK/{surumler,data,logs,kaynak} · $ETC (700) · ACME kökü $WEBROOT"

echo "== [3/9] dağıtım anahtarı (GitHub deploy key, yalnız okuma)"
if [ ! -f "$ETC/deploy_key" ]; then
  "$SSH_KEYGEN" -q -t ed25519 -N "" -C "portman-vps-deploy" -f "$ETC/deploy_key"
  echo "   yeni anahtar üretildi"
else
  echo "   var olan anahtar korundu"
fi
chmod 600 "$ETC/deploy_key"; chmod 644 "$ETC/deploy_key.pub"
echo "   GitHub → depo → Settings → Deploy keys → Add deploy key (Allow write access İŞARETSİZ). Açık anahtar:"
echo "   $(cat "$ETC/deploy_key.pub")"
# GitHub'ın yayımlanmış SSH sunucu anahtarı (ed25519; docs.github.com "GitHub's SSH key fingerprints"): guncelle.sh ilk çekişte
# sunucuyu buna göre doğrular (TOFU değil). Uymazsa: ssh-keyscan -t ed25519 github.com > /etc/portman/known_hosts
if [ ! -s "$ETC/known_hosts" ]; then
  echo "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl" > "$ETC/known_hosts"
  chmod 644 "$ETC/known_hosts"; echo "   GitHub sunucu anahtarı sabitlendi: $ETC/known_hosts"
fi

echo "== [4/9] Postgres: yalnız yerel bağlantı, '$KULLANICI' rolü (peer, parolasız), '$DB' veritabanı"
if [ -z "$TEST" ]; then systemctl enable --now postgresql >/dev/null; fi
LISTEN="$(psql_su -tAc "SHOW listen_addresses")"
yerel_dinleme "$LISTEN" || dur "listen_addresses='$LISTEN' yerel değil; postgresql.conf'ta 'localhost' yapılmadan kurulum sürmez"
HBA="$(psql_su -tAc "SELECT coalesce(address, '') FROM pg_hba_file_rules WHERE type LIKE 'host%' AND error IS NULL")"
yerel_hba "$HBA" || dur "pg_hba.conf yerel olmayan bir adrese TCP bağlantısı açıyor; o satır kaldırılmadan kurulum sürmez"
if command -v ss >/dev/null 2>&1; then
  SOKET="$(ss -Hltn "sport = :$PORT" 2>/dev/null | awk '{print $4}' || true)"
  yerel_soketler "$SOKET" || dur "$PORT portu yerel olmayan bir adreste dinleniyor: $(echo $SOKET)"
fi
if [ "$(psql_su -tAc "SELECT count(*) FROM pg_roles WHERE rolname = '$KULLANICI'")" != "1" ]; then
  psql_su -c "CREATE ROLE $KULLANICI LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"
fi
SAHIP="$(psql_su -tAc "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$DB'")"
if [ -z "$SAHIP" ]; then
  psql_su -c "CREATE DATABASE $DB OWNER $KULLANICI ENCODING 'UTF8' TEMPLATE template0"
  echo "   '$DB' oluşturuldu (boş; göçleri guncelle.sh uygular)"
elif [ "$SAHIP" != "$KULLANICI" ]; then
  dur "'$DB' veritabanı zaten var ve sahibi '$SAHIP' ($KULLANICI değil); dokunulmadı"
else
  echo "   '$DB' zaten var, sahibi $KULLANICI: kullanılır (içine dokunulmaz)"
fi
"${SU_PORTMAN[@]}" psql -X -q "${PG_PORTMAN[@]}" -d "$DB" -tAc "SELECT '   bağlantı: ' || current_user || ' @ ' || current_database()"
echo "   tamam: listen_addresses='$LISTEN', pg_hba yalnız yerel, $PORT dışarıda dinlenmiyor"

echo "== [5/9] nginx ve sertifika"
install -d -m 755 "$NGINX_DIR/sites-available" "$NGINX_DIR/sites-enabled"
SERT="$LE_DIR/live/$ALAN/fullchain.pem"
nginx_yaz() {   # $1: 1 → 443 bloğu dahil; önceki dosya .onceki olarak saklanır (nginx -t düşerse geri konur)
  local hedef="$NGINX_DIR/sites-available/portman.conf"
  if [ "$1" = "1" ]; then nginx_sablon | sed "s/__ALAN__/$ALAN/g" > "$hedef.yeni"
  else nginx_sablon | sed '/# --443-BASLA--/,/# --443-BITIS--/d' | sed "s/__ALAN__/$ALAN/g" > "$hedef.yeni"; fi
  [ -f "$hedef" ] && cp -p "$hedef" "$hedef.onceki"
  mv -f "$hedef.yeni" "$hedef"
  ln -sfn "$hedef" "$NGINX_DIR/sites-enabled/portman.conf"
}
nginx_yenile() {
  local hedef="$NGINX_DIR/sites-available/portman.conf"
  if [ -z "$TEST" ]; then
    if ! nginx -t >/dev/null 2>&1; then
      if [ -f "$hedef.onceki" ]; then mv -f "$hedef.onceki" "$hedef"; else rm -f "$hedef" "$NGINX_DIR/sites-enabled/portman.conf"; fi
      dur "nginx yapılandırması geçersiz (nginx -t çıktısına bakın); önceki dosya geri kondu, nginx'e dokunulmadı"
    fi
    $SYSTEMCTL enable --now nginx >/dev/null 2>&1 || true
    $SYSTEMCTL reload nginx
  fi
}
SUNUCU_IP="${PM_SUNUCU_IP:-$( { hostname -I 2>/dev/null || true; } | awk '{print $1}')}"
DNS_IP="${PM_DNS_IP:-$( { getent ahostsv4 "$ALAN" 2>/dev/null || true; } | awk '{print $1; exit}')}"
if [ ! -f "$SERT" ]; then
  nginx_yaz 0; nginx_yenile
  if [ -n "$SUNUCU_IP" ] && [ "$DNS_IP" = "$SUNUCU_IP" ]; then
    [ -n "$EPOSTA" ] || dur "PM_EPOSTA gerekli (Let's Encrypt son kullanma bildirimleri için)"
    echo "   alan adı bu sunucuya bakıyor; sertifika alınıyor (Let's Encrypt, webroot)"
    if [ -z "$TEST" ]; then
      certbot certonly --webroot -w "$WEBROOT" -d "$ALAN" -m "$EPOSTA" --agree-tos --non-interactive --no-eff-email --keep-until-expiring -q \
        || dur "certbot başarısız (çıktı yukarıda); 80 portu dışarıdan erişilebilir mi, DNS doğru mu?"
    else
      echo "   PM_TEST: certbot atlandı"
    fi
  else
    echo "   sertifika YOK ve alan adı henüz bu sunucuya bakmıyor (DNS: ${DNS_IP:-yok} · sunucu: ${SUNUCU_IP:-?}); 443 kapalı."
    echo "   DNS A kaydı yazıldıktan sonra bu betik aynı komutla yeniden koşar (Kapı 3)."
  fi
fi
install -d -m 755 "$LE_DIR/renewal-hooks/deploy"
printf '#!/usr/bin/env bash\n# Portman: sertifika yenilenince nginx yeniden yükler (certbot deploy hook)\nsystemctl reload nginx\n' > "$LE_DIR/renewal-hooks/deploy/portman-nginx.sh"
chmod 755 "$LE_DIR/renewal-hooks/deploy/portman-nginx.sh"
if [ -f "$SERT" ]; then
  nginx_yaz 1; nginx_yenile
  echo "   443 açık: yalnız /webhook, /saglik, /panel/ · sertifika bitiş: $(openssl x509 -enddate -noout -in "$SERT" 2>/dev/null | cut -d= -f2 || echo '?')"
else
  echo "   nginx: yalnız 80 (ACME ve https'e yönlendirme)"
fi

echo "== [6/9] güvenlik duvarı, fail2ban, sshd, otomatik güvenlik güncellemeleri"
if [ -z "$TEST" ]; then
  ufw --force default deny incoming >/dev/null; ufw --force default allow outgoing >/dev/null
  ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
  ufw --force enable >/dev/null
  echo "   ufw: $(ufw status | grep -E '^Status' || true)"; ufw status | grep -E '^(22|80|443)/tcp' | sed 's/^/   /' || true
else
  echo "   PM_TEST: ufw atlandı (gelen reddet; 22/80/443)"
fi
install -d -m 755 "$F2B_DIR"
fail2ban_sablon > "$F2B_DIR/portman.local"
if [ -z "$TEST" ]; then $SYSTEMCTL enable --now fail2ban >/dev/null 2>&1 || true; fail2ban-client reload >/dev/null 2>&1 || true; fi
echo "   fail2ban: sshd ve nginx-limit-req ($F2B_DIR/portman.local)"
install -d -m 755 "$SSHD_DIR"
if [ -s "$SSH_YETKILI" ]; then
  DROPIN="$SSHD_DIR/00-portman.conf"
  sshd_sablon > "$DROPIN.yeni"
  if [ -f "$DROPIN" ] && cmp -s "$DROPIN" "$DROPIN.yeni"; then
    rm -f "$DROPIN.yeni"; echo "   sshd drop-in zaten yerinde: $DROPIN"
  else
    [ -f "$DROPIN" ] && cp -p "$DROPIN" "$DROPIN.onceki"
    mv -f "$DROPIN.yeni" "$DROPIN"
    if ! $SSHD -t >/dev/null 2>&1; then
      if [ -f "$DROPIN.onceki" ]; then mv -f "$DROPIN.onceki" "$DROPIN"; else rm -f "$DROPIN"; fi
      dur "sshd sözdizimi geçmedi (sshd -t); drop-in geri alındı, sshd'ye dokunulmadı"
    fi
    if [ -z "$TEST" ]; then $SYSTEMCTL reload ssh; fi
    echo "   sshd drop-in yazıldı: $DROPIN (parolalı giriş kapalı; açık oturumlar kopmaz)"
  fi
  ETKIN="$( { $SSHD -T 2>/dev/null || true; } | awk 'tolower($1) == "passwordauthentication" {print $2; exit}')"
  echo "   sshd etkin değer: passwordauthentication ${ETKIN:-?}"
  [ "$ETKIN" = "no" ] || echo "   UYARI: etkin değer 'no' değil; $SSHD_DIR altında daha önce okunan bir dosya olabilir (ls $SSHD_DIR)"
else
  echo "   sshd: yetkili anahtar yok ($SSH_YETKILI boş) → parolalı giriş KAPATILMADI. Önce Mac'ten ssh-copy-id, sonra bu betik yeniden."
fi
if [ -z "$TEST" ]; then dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true; fi

echo "== [7/9] systemd birimleri ve logrotate"
install -d -m 755 "$SYSTEMD_DIR" "$LOGROTATE_DIR"
for b in $BIRIMLER; do birim_sablon "$b" > "$SYSTEMD_DIR/$b"; done
logrotate_sablon > "$LOGROTATE_DIR/portman"
$SYSTEMCTL daemon-reload
$SYSTEMCTL enable portman-webhook portman-agent portman-gonderici portman-panel portman-yedek.timer portman-nabiz.timer >/dev/null 2>&1 || true
$SYSTEMCTL start portman-nabiz.timer portman-yedek.timer >/dev/null 2>&1 || true
echo "   birimler: $BIRIMLER"
echo "   servisler ilk sürümle başlar (guncelle.sh); zamanlayıcılar açık (yedek 03:40, nabız 5 dk)"

echo "== [8/9] ayarlar ve panel oturum anahtarı"
if [ ! -f "$KOK/data/settings.json" ]; then
  cat > "$KOK/data/settings.json" <<'EOF'
{
 "enabled": false,
 "enabled_at": 0,
 "dry_run": true,
 "mode": "patron",
 "llm": {"backend": "anthropic", "model": "claude-opus-5-5", "timeout_s": 60},
 "patron_teknik_not": false,
 "mesaj_katmani": true,
 "ucb_taban_url": null,
 "kayitsiz_cevap": "Bu hat PortatifEv bayileri için Portman planlama hattıdır. Kayıtlı bayi değilseniz lütfen PortatifEv ofisiyle görüşün.",
 "sablon_patron_bildirim": null,
 "sablon_bayi_dosyalar_hazir": null,
 "sablon_muhendis_kontrol": null,
 "sablon_muhendis_hatirlatma": null,
 "sablon_bayi_karsilama": null,
 "sablon_bayi_bilgi_hazir": null,
 "sablon_dil": "tr",
 "plan_uretimi": {"acik": false, "model": "claude-opus-5-5", "effort": "low", "en_cok_cagri": 2, "timeout_s": 60},
 "llm_once_revizyon": {"acik": false, "mod": "kapali", "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60}
}
EOF
  chmod 640 "$KOK/data/settings.json"
  echo "   settings.json yazıldı: enabled false, dry_run true, mode patron"
else
  echo "   settings.json var; korundu"
fi
if [ -z "$TEST" ]; then chown "$KULLANICI:$KULLANICI" "$KOK/data/settings.json"; fi
printf '%s\n' "$ALAN" > "$ETC/alan"
umask 077
for f in llm.env whatsapp.env; do [ -f "$ETC/$f" ] || : > "$ETC/$f"; chmod 600 "$ETC/$f"; done
if ! grep -q '^PANEL_SIR=' "$ETC/panel.env" 2>/dev/null; then
  { [ -f "$ETC/panel.env" ] && cat "$ETC/panel.env"; printf 'PANEL_SIR=%s\n' "$(openssl rand -hex 32)"; } > "$ETC/panel.env.yeni"
  mv -f "$ETC/panel.env.yeni" "$ETC/panel.env"
  echo "   panel oturum anahtarı üretildi (panel.env; değer yazdırılmaz)"
else
  echo "   panel oturum anahtarı var; korundu"
fi
chmod 600 "$ETC/panel.env"
umask 022

echo "== [9/9] özet"
echo "   sürüm: $( [ -L "$KOK/guncel" ] && readlink "$KOK/guncel" || echo 'yok (Kapı 4: guncelle.sh <etiket>)')"
echo "   sertifika: $( [ -f "$SERT" ] && echo var || echo yok ) · sırlar: $ETC/{llm,whatsapp,panel}.env (sir_koy.py, panel_parola.py ile dolar)"
echo "   sağlık: sürüm kurulunca https://$ALAN/saglik"
echo "Kuruldu ($(date '+%Y-%m-%d %H:%M:%S %Z')). Sırada: Kapı 3 (DNS A kaydı → bu betik yeniden), Kapı M (etiket), Kapı 4: ssh portman-vps 'bash -s' < vps/guncelle.sh <etiket>"
