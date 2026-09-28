#!/usr/bin/env bash
# PORTMAN · VPS'e Postgres kurulumu (İE-02, onay kapısı D). Ubuntu 24.04, root olarak; tekrar çalıştırılabilir (var olanı bozmaz).
#   ssh root@<VPS> 'bash -s' < vps/pg_kurulum.sh
# Yaptıkları: Postgres 16 (Ubuntu deposu), yalnız yerel bağlantı; 'portman' rolü ve veritabanı (PAROLASIZ: yerel soket + peer
# kimlik doğrulaması; ajan 'portman' sistem kullanıcısıyla çalıştığı için sır yok); saf psycopg sürücüsü ajanın venv'ine;
# günlük pg_dump yedeği; bir yedek alıp AYRI ve bu çalıştırmanın açtığı bir veritabanına geri yükleme denemesi.
# Yedeklerin OTOMATİK SİLİNMESİ varsayılan olarak KAPALI (pilot). Açmak ayrı bir tercih ve ayrı onaydır:
#   ssh root@<VPS> 'PM_YEDEK_SAKLA_GUN=14 bash -s' < vps/pg_kurulum.sh      (14 günden eski yedekler silinir)
# DURUR (uyarıp geçmez): Postgres yerel adresler dışında dinliyorsa; pg_hba yerel olmayan bir adrese izin veriyorsa; 5432 portu
# yerel olmayan bir adreste açıksa; güvenlik duvarında 5432 kuralı varsa; 'portman' veritabanı var ama sahibi 'portman' değilse;
# PM_YEDEK_SAKLA_GUN geçersizse. Geri yükleme denemesi yalnız bu çalıştırmanın açıp işaretlediği veritabanını siler; aynı adda
# başka bir veritabanı varsa dokunmaz ve durur.
# Yapmadıkları: ajanı kalıcı moda almaz (PORTMAN_PG_DSN yazılmaz), göç uygulamaz, trafiği değiştirmez, 5432'yi açmaz.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
HOME_DIR=/opt/portman
DB="${PM_DB:-portman}"                          # yalnız yerel sınamada değişir
YEDEK="${PM_YEDEK:-/var/backups/portman}"
CRON_DOSYA="${PM_CRON_DOSYA:-/etc/cron.d/portman-pg-yedek}"
SAKLA="${PM_YEDEK_SAKLA_GUN:-}"
PORT="${PM_PG_PORT:-5432}"
TEST="${PM_TEST:-}"                             # yalnız yerel sınama: paket/pip/cron'u atlar; bağlantı PM_PG ile verilir
if [ -n "$TEST" ]; then read -r -a PG <<< "${PM_PG:-}"; read -r -a PG_PORTMAN <<< "${PM_PG_PORTMAN:-}"; SU=(); SU_PORTMAN=()
else PG=(); PG_PORTMAN=(); SU=(sudo -u postgres); SU_PORTMAN=(sudo -u portman); fi

dur() { echo "DURDU: $*" >&2; exit 1; }
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
[ -n "${PM_YALNIZ_ISLEVLER:-}" ] && return 0 2>/dev/null   # sınama: yalnız işlevleri yükle

if [ -n "$SAKLA" ] && ! [[ "$SAKLA" =~ ^[1-9][0-9]{0,3}$ ]]; then dur "PM_YEDEK_SAKLA_GUN geçersiz: '$SAKLA' (boş ya da 1–9999 gün)"; fi
kimlik "$DB"

echo "== [1/6] Postgres paketi"
if [ -z "$TEST" ]; then
  apt-get update -q
  apt-get install -y -q postgresql postgresql-client libpq5 >/dev/null
  systemctl enable --now postgresql >/dev/null
fi
psql --version

echo "== [2/6] yalnız yerel bağlantı denetimi (sağlanmıyorsa durur)"
LISTEN="$(psql_su -tAc "SHOW listen_addresses")"
yerel_dinleme "$LISTEN" || dur "listen_addresses='$LISTEN' yerel değil; postgresql.conf'ta 'localhost' yapılmadan kurulum sürmez"
HBA="$(psql_su -tAc "SELECT coalesce(address, '') FROM pg_hba_file_rules WHERE type LIKE 'host%' AND error IS NULL")"
yerel_hba "$HBA" || dur "pg_hba.conf yerel olmayan bir adrese TCP bağlantısı açıyor; o satır kaldırılmadan kurulum sürmez"
if command -v ss >/dev/null 2>&1; then
  SOKET="$(ss -Hltn "sport = :$PORT" 2>/dev/null | awk '{print $4}')"
  yerel_soketler "$SOKET" || dur "$PORT portu yerel olmayan bir adreste dinleniyor: $(echo $SOKET)"
fi
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -Eq "(^|[^0-9])$PORT(/tcp)?([^0-9]|$)"; then
  dur "güvenlik duvarında $PORT kuralı var; kaldırılmadan kurulum sürmez"
fi
echo "   tamam: listen_addresses='$LISTEN', pg_hba yalnız yerel, $PORT dışarıda dinlenmiyor"

echo "== [3/6] rol ve veritabanı (parolasız, peer)"
if [ "$(psql_su -tAc "SELECT count(*) FROM pg_roles WHERE rolname = 'portman'")" != "1" ]; then
  psql_su -c "CREATE ROLE portman LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"
fi
SAHIP="$(psql_su -tAc "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$DB'")"
if [ -z "$SAHIP" ]; then
  psql_su -c "CREATE DATABASE $DB OWNER portman ENCODING 'UTF8' TEMPLATE template0"
elif [ "$SAHIP" != "portman" ]; then
  dur "'$DB' veritabanı zaten var ve sahibi '$SAHIP' (portman değil); dokunulmadı"
else
  echo "   '$DB' zaten var, sahibi portman: kullanılır (içine dokunulmaz)"
fi
"${SU_PORTMAN[@]}" psql -X -q "${PG_PORTMAN[@]}" -d "$DB" -tAc "SELECT '   bağlantı: ' || current_user || ' @ ' || current_database()"

echo "== [4/6] Python sürücüsü (saf psycopg; sistem libpq)"
if [ -z "$TEST" ]; then
  sudo -u portman "$HOME_DIR/venv/bin/pip" install -q "psycopg==3.3.6"
  sudo -u portman "$HOME_DIR/venv/bin/python" -c "import psycopg; c = psycopg.connect('dbname=portman'); print('   psycopg', psycopg.__version__, psycopg.pq.__impl__, 'bağlantı', c.execute('select 1').fetchone()[0])"
fi

echo "== [5/6] günlük yedek: 03:17, $YEDEK"
install -d -m 700 "$YEDEK"
if [ -z "$TEST" ]; then chown postgres:postgres "$YEDEK"; fi
YEDEK_KOMUTU="pg_dump -Fc -d $DB -f $YEDEK/portman-\$(date +\\%Y\\%m\\%d).dump"
if [ -n "$SAKLA" ]; then
  YEDEK_KOMUTU="$YEDEK_KOMUTU && find $YEDEK -name 'portman-2*.dump' -mtime +$SAKLA -delete"
  echo "   otomatik silme AÇIK: $SAKLA günden eski yedekler silinir (ayrı onayla açıldı)"
else
  echo "   otomatik silme KAPALI (pilot varsayılanı): yedekler silinmez; disk dolulukla izlenir"
fi
cat > "$CRON_DOSYA" <<EOF
# Portman Postgres günlük yedeği (İE-02). Otomatik silme: ${SAKLA:+$SAKLA gün}${SAKLA:-kapalı}. Geri yükleme: docs/is_emirleri/IE-02-canli.md
17 3 * * * postgres $YEDEK_KOMUTU
EOF
chmod 644 "$CRON_DOSYA"

echo "== [6/6] yedek + bu çalıştırmanın açtığı ayrı veritabanına geri yükleme denemesi"
CALISMA="${PM_CALISMA:-$(date +%Y%m%d%H%M%S)_$$}"      # PM_CALISMA yalnız sınamada
DENEME="portman_geri_deneme_${CALISMA}"; kimlik "$DENEME"
ISARET="portman-geri-yukleme-denemesi:${CALISMA}"
DOSYA="$YEDEK/kurulum-deneme-${CALISMA}.dump"
"${SU[@]}" pg_dump -Fc "${PG[@]}" -d "$DB" -f "$DOSYA"
[ "$(psql_su -tAc "SELECT count(*) FROM pg_database WHERE datname = '$DENEME'")" = "0" ] || dur "'$DENEME' zaten var; dokunulmadı"
psql_su -c "CREATE DATABASE $DENEME" -c "COMMENT ON DATABASE $DENEME IS '$ISARET'"
if "${SU[@]}" pg_restore --exit-on-error "${PG[@]}" -d "$DENEME" "$DOSYA"; then
  echo "   geri yükleme: tamam ($DOSYA)"
  if [ "$(psql_su -tAc "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = '$DENEME'")" = "$ISARET" ]; then
    psql_su -c "DROP DATABASE $DENEME"
    echo "   deneme veritabanı silindi (bu çalıştırmanın açtığı ve işaretlediği: $DENEME)"
  else
    dur "'$DENEME' işareti beklenenle aynı değil; silinmedi"
  fi
else
  dur "geri yükleme başarısız; '$DENEME' incelenmek üzere bırakıldı"
fi
echo
echo "Kuruldu. Ajan hâlâ dosya modunda (PORTMAN_PG_DSN yok). Göç ve geçiş ayrı onaylı adımdır (docs/is_emirleri/IE-02-canli.md)."
