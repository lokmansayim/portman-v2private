#!/usr/bin/env bash
# PORTMAN · Kapı F.6 (İE-02): ajanı kalıcı moda (Postgres) alır. DEĞİŞİKLİK YAPAR, yalnız şunları:
#   /etc/portman/pg.env (PORTMAN_PG_DSN=dbname=portman; root:portman 640) ve systemd ek dosyası kalici.conf yazılır,
#   daemon-reload, portman-agent yeniden başlatılır. agent.env, paket, model, anahtar ve hosting değişmez.
#   ssh portman-vps 'bash -s' < kapi_f_kalici_ac.sh > 6_kalici.txt
# Hosting'te worker hâlâ "off" olmalı: ajan kalıcı modda başlar ama iş ALMAZ (yalnız Postgres'te açık iş varsa bitirir; yok).
# Ön koşullar: worker off; göçler tam; içe aktarma yapılmış (konuşma > 0); Postgres'te açık iş yok; bekleyen sonuç yok.
# Biri tutmazsa hiçbir şey yapılmaz. Öz-test yeniden koşmaz (bu paket için sonucu var): LLM çağrısı yok.
# Geri almak gerekirse (dosya moduna dönüş):
#   rm /etc/systemd/system/portman-agent.service.d/kalici.conf /etc/portman/pg.env; systemctl daemon-reload; systemctl restart portman-agent
# Test için: PM_HOME, PM_ENV, PM_PY, PM_OLARAK, PM_ETC, PM_DROPIN, PM_TEST.
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PM_ENV="${PM_ENV:-/etc/portman/agent.env}"; PY="${PM_PY:-$PM_HOME/venv/bin/python}"; APP="$PM_HOME/app"
OLARAK="${PM_OLARAK:-sudo -u portman env PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=$PM_HOME/data}"
ETC="${PM_ETC:-/etc/portman}"; DROPIN="${PM_DROPIN:-/etc/systemd/system/portman-agent.service.d}"
dur() { echo "DUR: $*"; echo "   hiçbir şey değiştirilmedi."; echo "== bitti (durdu)"; exit 1; }

echo "== Kapı F.6 · kalıcı modu açma · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- ön koşullar"
[ "$(id -u)" = "0" ] || [ -n "${PM_TEST:-}" ] || dur "root olarak çalıştırılmalı"
[ ! -e "$ETC/pg.env" ] && [ ! -e "$DROPIN/kalici.conf" ] || dur "pg.env ya da kalici.conf zaten var"
[ "$(ls "$PM_HOME"/data/pending/*.json 2>/dev/null | wc -l)" = "0" ] || dur "gönderilemeyip bekleyen sonuç var"
PM_ENV="$PM_ENV" python3 - <<'PY' || dur "hosting ayarı okunamadı ya da worker off değil"
import json, os, sys, urllib.request
from pathlib import Path
env = {}
for s in Path(os.environ["PM_ENV"]).read_text().splitlines():
    if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-f"})
with urllib.request.urlopen(req, timeout=25) as r:
    j = json.loads(r.read().decode())
print(f"   hosting: api {j.get('api')} · worker {j.get('worker')} · mode {j.get('mode')} · llm {(j.get('llm') or {}).get('backend')}/{(j.get('llm') or {}).get('model')}")
sys.exit(0 if j.get("worker") == "off" and str(j.get("api", "")).startswith("kanal-api-v1.2") else 1)
PY
DB_DURUM="$($OLARAK "$PY" - "$APP" <<'PY' 2>&1 | tail -1
import sys
sys.path.insert(0, sys.argv[1])
import depo
d = depo.Depo()
with d.baglan() as c:
    k = c.execute("SELECT count(*) AS n FROM konusmalar").fetchone()["n"]
    a = c.execute("SELECT count(*) AS n FROM isler WHERE durum IN ('sirada', 'isleniyor')").fetchone()["n"]
print(f"eksik_goc={d.eksik_goc()} konusma={k} acik_is={a}")
PY
)"
echo "   Postgres: $DB_DURUM"
[[ "$DB_DURUM" =~ ^eksik_goc=\[\]\ konusma=[1-9][0-9]*\ acik_is=0$ ]] || dur "Postgres hazır değil (göç eksik, içe aktarma yok ya da açık iş var)"

echo "-- kalıcı mod dosyaları"
ONCE="$(date '+%Y-%m-%d %H:%M:%S')"
umask 027
printf 'PORTMAN_PG_DSN=dbname=portman\n' > "$ETC/pg.env"
chown root:portman "$ETC/pg.env" 2>/dev/null || [ -n "${PM_TEST:-}" ]; chmod 640 "$ETC/pg.env"
mkdir -p "$DROPIN"
printf '[Service]\nEnvironmentFile=%s/pg.env\n' "$ETC" > "$DROPIN/kalici.conf"; chmod 644 "$DROPIN/kalici.conf"
echo "   $ETC/pg.env: $(stat -c '%U:%G %a' "$ETC/pg.env") · satır adı: $(sed -n 's/^\([A-Z_]*\)=.*/\1/p' "$ETC/pg.env")"
echo "   $DROPIN/kalici.conf: $(tr '\n' ' ' < "$DROPIN/kalici.conf")"
systemctl daemon-reload
systemctl restart portman-agent
echo "   servis yeniden başlatıldı ($ONCE); başlama satırı bekleniyor (en çok 90 sn)"
for i in $(seq 1 30); do
  sleep 3
  grep -a "başladı" "$PM_HOME/logs/agent.log" 2>/dev/null | awk -v t="$ONCE" 'substr($0, 1, 19) >= t' | grep -q "kalıcı (Postgres)" && break
done
echo "-- servis"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
sleep 10
echo "-- günlük ($ONCE sonrası; numara ve metin yazılmaz)"
awk -v t="$ONCE" 'substr($0, 1, 19) >= t' "$PM_HOME/logs/agent.log" 2>/dev/null | sed -E 's/[0-9a-f]{16,}/…/g' | cut -c1-140 | sed 's/^/   /'
M="$(awk -v t="$ONCE" 'substr($0, 1, 19) >= t' "$PM_HOME/logs/agent.log" 2>/dev/null)"
echo "   özet: kalıcı başlama $(grep -c 'mod kalıcı (Postgres)' <<< "$M") · 'kalıcı mod bekliyor' $(grep -c 'kalıcı mod bekliyor' <<< "$M") · Postgres'e ulaşılamadı $(grep -c "Postgres'e ulaşılamadı" <<< "$M") · api hatası $(grep -c ' api:' <<< "$M") · beklenmeyen $(grep -c 'beklenmeyen' <<< "$M") · iş alındı $(grep -c 'iş alındı' <<< "$M")"
echo "== bitti: kalıcı mod $(grep -q 'mod kalıcı (Postgres)' <<< "$M" && echo AÇIK || echo 'AÇILMADI (yukarıya bak)'); worker hâlâ off: yeni iş alınmıyor"
