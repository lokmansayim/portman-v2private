#!/usr/bin/env bash
# PORTMAN · VPS'e Postgres kurulumu (İE-02, onay kapısı C). Ubuntu 24.04, root olarak bir kez; tekrar çalıştırılabilir.
#   ssh root@<VPS> 'bash -s' < vps/pg_kurulum.sh
# Yaptıkları: Postgres 16 (Ubuntu deposu), yalnız yerel bağlantı; 'portman' rolü ve veritabanı (PAROLASIZ: yerel soket +
# peer kimlik doğrulaması; ajan 'portman' sistem kullanıcısıyla çalıştığı için sır yok); saf psycopg sürücüsü ajanın
# venv'ine; günlük pg_dump yedeği (14 gün saklanır, daha eskisi silinir — bu silme bu onayın parçasıdır).
# Yapmadıkları: ajanı kalıcı moda almaz (PORTMAN_PG_DSN yazılmaz), göç uygulamaz, trafiği değiştirmez, 5432'yi açmaz.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
HOME_DIR=/opt/portman

echo "== [1/6] Postgres paketi"
apt-get update -q
apt-get install -y -q postgresql postgresql-client libpq5 >/dev/null
systemctl enable --now postgresql >/dev/null
psql --version

echo "== [2/6] yalnız yerel bağlantı (beklenen: localhost; güvenlik duvarında 5432 açılmaz)"
sudo -u postgres psql -tAc "SHOW listen_addresses"
if ufw status 2>/dev/null | grep -q "5432"; then echo "UYARI: ufw'de 5432 kuralı var; kaldırılmadı, bakılmalı"; fi

echo "== [3/6] rol ve veritabanı (parolasız, peer)"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'portman'" | grep -q 1 \
  || sudo -u postgres createuser --no-superuser --no-createdb --no-createrole portman
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'portman'" | grep -q 1 \
  || sudo -u postgres createdb -O portman -E UTF8 portman
sudo -u portman psql -d portman -tAc "SELECT current_user || ' @ ' || current_database()"

echo "== [4/6] Python sürücüsü (saf psycopg; sistem libpq)"
sudo -u portman "$HOME_DIR/venv/bin/pip" install -q "psycopg==3.3.6"
sudo -u portman "$HOME_DIR/venv/bin/python" -c "import psycopg; c = psycopg.connect('dbname=portman'); print('   psycopg', psycopg.__version__, psycopg.pq.__impl__, 'bağlantı', c.execute('select 1').fetchone()[0])"

echo "== [5/6] günlük yedek: 03:17, /var/backups/portman, 14 gün"
install -d -o postgres -g postgres -m 700 /var/backups/portman
cat > /etc/cron.d/portman-pg-yedek <<'EOF'
# Portman Postgres günlük yedeği (İE-02). Geri yükleme: docs/is_emirleri/IE-02-canli.md
17 3 * * * postgres pg_dump -Fc -d portman -f /var/backups/portman/portman-$(date +\%Y\%m\%d).dump && find /var/backups/portman -name 'portman-2*.dump' -mtime +14 -delete
EOF
chmod 644 /etc/cron.d/portman-pg-yedek

echo "== [6/6] yedek + ayrı veritabanına geri yükleme denemesi (boş veritabanıyla)"
sudo -u postgres pg_dump -Fc -d portman -f /var/backups/portman/kurulum-deneme.dump
sudo -u postgres createdb portman_geri_deneme
sudo -u postgres pg_restore --exit-on-error -d portman_geri_deneme /var/backups/portman/kurulum-deneme.dump && echo "   geri yükleme: tamam"
sudo -u postgres dropdb portman_geri_deneme
echo
echo "Kuruldu. Ajan hâlâ dosya modunda (PORTMAN_PG_DSN yok). Göç ve geçiş ayrı onaylı adımdır (docs/is_emirleri/IE-02-canli.md)."
