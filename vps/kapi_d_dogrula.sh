#!/usr/bin/env bash
# PORTMAN · Kapı D sonrası SALT OKUNUR doğrulama (İE-02). Hiçbir dosyayı, ayarı, veritabanını ya da servisi değiştirmez.
# Mac'ten, Lokman çalıştırır:  ssh root@<VPS> 'bash -s' < kapi_d_dogrula.sh
# Gösterir: kurulan Postgres sürümü; yalnız yerelden bağlantı (listen, pg_hba, açık soketler, güvenlik duvarı); portman rolü ve
# veritabanı (sahip, parolasız, süper kullanıcı değil); peer bağlantısı ve ajanın venv'indeki psycopg; yedek klasörü, cron satırı
# (otomatik silme yok) ve deneme yedeğinin okunabildiği; Portman servisinin sağlığı ve DOSYA MODUNDA kaldığı.
# Yazdırmaz: anahtar değeri (agent.env'den yalnız satır adları), telefon numarası, mesaj metni.
set -u
cd /tmp
DB=portman; YEDEK=/var/backups/portman; CRON=/etc/cron.d/portman-pg-yedek; HOME_DIR=/opt/portman; ENV_DOSYA=/etc/portman/agent.env
pgs() { sudo -u postgres psql -X -q -tA "$@" 2>&1 | tr '\n' ' ' | sed 's/ *$//'; }

echo "== Kapı D · salt okunur doğrulama · betik 2026-09-28 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- Postgres"
echo "   paket: $(dpkg-query -W -f='${Package} ${Version}' postgresql-16 2>/dev/null || echo yok) · psql: $(psql --version 2>/dev/null || echo yok)"
echo "   sunucu sürümü: $(pgs -c 'SHOW server_version')"
echo "   servis: $(systemctl is-active postgresql 2>/dev/null || true) / $(systemctl is-enabled postgresql 2>/dev/null || true)"
pg_lsclusters 2>/dev/null | sed 's/^/   /'
echo "   listen_addresses: $(pgs -c 'SHOW listen_addresses')"
echo "   5432'yi dinleyen adresler: $(ss -Hltn 'sport = :5432' 2>/dev/null | awk '{print $4}' | tr '\n' ' ')"
echo "   pg_hba TCP kuralları: $(pgs -c "SELECT coalesce(string_agg(type || ' ' || coalesce(address, '-'), ', '), 'yok') FROM pg_hba_file_rules WHERE type LIKE 'host%' AND error IS NULL") · hatalı satır: $(pgs -c 'SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL')"
echo "   güvenlik duvarı: $(ufw status 2>/dev/null | head -1 || echo yok) · 5432 kuralı: $(ufw status 2>/dev/null | grep -Ec '(^|[^0-9])5432(/tcp)?([^0-9]|$)' || true)"

echo "-- rol ve veritabanı"
echo "   rol: $(pgs -c "SELECT rolname || ' login=' || rolcanlogin || ' superuser=' || rolsuper || ' createdb=' || rolcreatedb || ' createrole=' || rolcreaterole || ' parola=' || (rolpassword IS NOT NULL) FROM pg_authid WHERE rolname = 'portman'")"
echo "   veritabanları: $(pgs -c "SELECT string_agg(datname || ' (sahibi ' || pg_get_userbyid(datdba) || ', ' || pg_encoding_to_char(encoding) || ')', ', ' ORDER BY datname) FROM pg_database WHERE datname LIKE 'portman%'")"
echo "   deneme veritabanı kalıntısı: $(pgs -c "SELECT count(*) FROM pg_database WHERE datname LIKE 'portman_geri_deneme%'")"
echo "   portman içindeki tablo sayısı: $(sudo -u postgres psql -X -q -tA -d "$DB" -c "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')" 2>&1)"
echo "   peer bağlantısı (portman kullanıcısı, parolasız): $(sudo -u portman psql -X -q -tA -F ' @ ' -d "$DB" -c 'SELECT current_user, current_database()' 2>&1 | tail -1)"
echo "   psycopg (ajanın venv'i): $(sudo -u portman "$HOME_DIR/venv/bin/python" -c "import psycopg; c = psycopg.connect('dbname=portman'); print(psycopg.__version__, psycopg.pq.__impl__, 'libpq', psycopg.pq.version(), 'bağlantı', c.execute('select 1').fetchone()[0])" 2>&1 | tail -1)"

echo "-- yedek"
echo "   klasör: $(stat -c '%U:%G %a' "$YEDEK" 2>/dev/null || echo yok)"
ls -l --time-style='+%Y-%m-%d %H:%M' "$YEDEK" 2>/dev/null | awk 'NR > 1 {print "   " $6 " " $7 " · " $5 " B · " $8}'
echo "   cron dosyası: $(stat -c '%U:%G %a' "$CRON" 2>/dev/null || echo yok)"
grep -v '^#' "$CRON" 2>/dev/null | sed 's/^/   /'
echo "   cron'da otomatik silme: $(grep -c -- '-delete' "$CRON" 2>/dev/null || true)"
SON="$(ls -t "$YEDEK"/kurulum-deneme-*.dump 2>/dev/null | head -1)"
if [ -n "$SON" ]; then
  echo "   son deneme yedeği pg_restore ile okunuyor mu: $(sudo -u postgres pg_restore --list "$SON" >/dev/null 2>&1 && echo evet || echo HAYIR)"
fi

echo "-- Portman servisi (dosya modunda kalmalı)"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
echo "   agent.env satır adları: $(sed -n 's/^\([A-Z_]*\)=.*/\1/p' "$ENV_DOSYA" 2>/dev/null | tr '\n' ' ')"
echo "   PORTMAN_PG_DSN: $(grep -c '^PORTMAN_PG_DSN=' "$ENV_DOSYA" 2>/dev/null || true) · /etc/portman/pg.env: $([ -e /etc/portman/pg.env ] && echo VAR || echo yok) · kalici.conf: $([ -e /etc/systemd/system/portman-agent.service.d/kalici.conf ] && echo VAR || echo yok)"
echo "   ajan: $(grep -m1 -o "vps-agent-v[0-9.]*" "$HOME_DIR/agent.py" 2>/dev/null) · gönderilemeyip bekleyen sonuç: $(ls "$HOME_DIR"/data/pending/*.json 2>/dev/null | wc -l)"
python3 - <<'PY'
import json, time, urllib.error, urllib.request
from pathlib import Path
g = Path("/opt/portman/logs/agent.log")
if g.exists():
    satirlar = g.read_text(errors="replace").splitlines()
    sinir = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 7200))
    son = [s for s in satirlar if s[:19] >= sinir]
    baslama = [s[:19] for s in satirlar if " başladı " in s]
    print(f"   günlük (son 2 saat): {len(son)} satır · 'api:' hatası {sum(' api:' in s for s in son)} · 'beklenmeyen' {sum('beklenmeyen' in s for s in son)} · son başlama {baslama[-1] if baslama else '-'}")
env = {}
try:
    for s in Path("/etc/portman/agent.env").read_text().splitlines():
        if "=" in s:
            k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
except OSError:
    pass
try:
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings",
                                 headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-d"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode()); kod = r.status
    print(f"   hosting op=settings (ajanın anahtarıyla): HTTP {kod} · api {j.get('api')} · worker {j.get('worker')} · mode {j.get('mode')} · enabled {j.get('enabled')} · dry_run {j.get('dry_run')}")
except urllib.error.HTTPError as e:
    print(f"   hosting op=settings: HTTP {e.code}")
except Exception as e:
    print(f"   hosting op=settings: ulaşılamadı ({type(e).__name__})")
PY
echo "== bitti"
