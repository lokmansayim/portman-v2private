#!/usr/bin/env bash
# PORTMAN · Kapı F.5 (İE-02): hosting'in konuşma ve kuyruk kopyasını Postgres'e aktarır. DEĞİŞİKLİK YAPAR, yalnız şunları:
#   /var/tmp/portman-gecis sahibini portman yapar; portman veritabanına göçleri uygular (tablolar); kopyayı içe aktarır.
# Servise, ajana, hosting'e, pakete, modele ve anahtara dokunmaz; ajan dosya modunda kalır (kalıcı mod ayrı adım: F.6).
#   ssh portman-vps 'bash -s' < kapi_f_aktar.sh > 5_aktarim.txt
# Ön koşullardan biri tutmazsa HİÇBİR ŞEY yapmadan durur: kopyanın state.json'u Mac'te doğrulanan özetle aynı değilse, hosting'te
# worker off değilse, ajan dosya modunda değilse ya da elinde iş/bekleyen sonuç varsa, portman veritabanında herhangi bir tablo
# varsa (beklenmeyen dolu veritabanı: silinmez, üzerine yazılmaz). İçe aktarma yalnız boş veritabanına yapılır (depo_aktar.py).
# Sonunda kaynak ile Postgres değer yazmadan karşılaştırılır (kapi_f.py); uyuşmazlıkta çıkış kodu 2 ve "DUR".
# Test için: PM_HOME, PM_ENV, PM_GECIS, PM_PY, PM_OLARAK, PM_PSQL, PM_BEKLENEN_STATE_SHA, PM_SAHIP.
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PM_ENV="${PM_ENV:-/etc/portman/agent.env}"; GECIS="${PM_GECIS:-/var/tmp/portman-gecis}"
KANAL="$GECIS/kanal"; PY="${PM_PY:-$PM_HOME/venv/bin/python}"; APP="$PM_HOME/app"
OLARAK="${PM_OLARAK:-sudo -u portman env PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=$PM_HOME/data}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA}"; DB="${PM_DB:-portman}"
SAHIP="${PM_SAHIP:-portman:portman}"
BEKLENEN="${PM_BEKLENEN_STATE_SHA:-__STATE_SHA__}"
dur() { echo "DUR: $*"; echo "   hiçbir şey değiştirilmedi."; echo "== bitti (durdu)"; exit 1; }

echo "== Kapı F.5 · Postgres'e aktarma · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- ön koşullar (biri tutmazsa hiçbir şey yapılmaz)"
[ "$(id -u)" = "0" ] || [ -n "${PM_TEST:-}" ] || dur "root olarak çalıştırılmalı"
[[ "$BEKLENEN" =~ ^[0-9a-f]{64}$ ]] || dur "beklenen state.json özeti betiğe yazılmamış"
[ -f "$KANAL/state.json" ] && [ -d "$KANAL/durum" ] || dur "$KANAL/state.json ya da durum/ yok (scp adımı yapılmadı mı?)"
[ -f "$GECIS/kapi_f.py" ] || dur "$GECIS/kapi_f.py yok"
GERCEK="$(sha256sum "$KANAL/state.json" | cut -d' ' -f1)"
[ "$GERCEK" = "$BEKLENEN" ] || dur "kopyadaki state.json Mac'te doğrulanan yedekle aynı değil (${GERCEK:0:16} ≠ ${BEKLENEN:0:16})"
echo "   state.json Mac'teki yedekle aynı: ${GERCEK:0:16} · konuşma dosyası $(ls "$KANAL"/durum/*.json 2>/dev/null | wc -l)"
[ ! -e /etc/portman/pg.env ] && [ ! -e /etc/systemd/system/portman-agent.service.d/kalici.conf ] && ! grep -q '^PORTMAN_PG_DSN=' "$PM_ENV" \
  || dur "ajan zaten kalıcı moda ayarlı görünüyor"
BEKLEYEN="$(ls "$PM_HOME"/data/pending/*.json 2>/dev/null | wc -l)"
[ "$BEKLEYEN" = "0" ] || dur "$BEKLEYEN gönderilemeyip bekleyen sonuç var"
PM_ENV="$PM_ENV" PM_HOME="$PM_HOME" python3 - <<'PY' || dur "hosting ayarı okunamadı ya da worker off değil ya da ajanın elinde iş var"
import json, os, sys, urllib.request
from pathlib import Path
env = {}
for s in Path(os.environ["PM_ENV"]).read_text().splitlines():
    if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-f"})
with urllib.request.urlopen(req, timeout=25) as r:
    j = json.loads(r.read().decode())
print(f"   hosting: worker {j.get('worker')} · mode {j.get('mode')} · llm {(j.get('llm') or {}).get('backend')}/{(j.get('llm') or {}).get('model')}")
g = Path(os.environ["PM_HOME"]) / "logs" / "agent.log"
s = g.read_text(errors="replace").splitlines() if g.exists() else []
bas = max([i for i, x in enumerate(s) if x[20:].startswith("başladı")] or [0])
acik = sum(x[20:].startswith("iş alındı") for x in s[bas:]) - sum(x[20:].startswith("iş bitti") for x in s[bas:])
print(f"   ajanın elinde iş: {'VAR' if acik > 0 else 'yok'}")
sys.exit(0 if j.get("worker") == "off" and acik <= 0 else 1)
PY
TAB="$($PSQL -d "$DB" -c "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')" 2>&1 | tr -d ' \n')"
[ "$TAB" = "0" ] || dur "portman veritabanı boş değil ya da okunamadı (tablo sayısı: $TAB); silinmez, üzerine yazılmaz"
echo "   portman veritabanı boş (tablo yok)"

echo "-- kopyanın sahibi portman (okuyabilsin; başkası okuyamaz)"
chown -R "$SAHIP" "$GECIS" && chmod -R u=rwX,go= "$GECIS" || dur "sahiplik değiştirilemedi"
echo "   $(stat -c '%U:%G %a' "$GECIS")"

echo "-- öncesi: kaynak özeti (Postgres boş)"
$OLARAK "$PY" "$GECIS/kapi_f.py" karsilastir "$KANAL" --veri "$PM_HOME/data" --yalniz-kaynak 2>&1 | sed 's/^/ /'

echo "-- göçler (kalici.py goc)"
OUT="$($OLARAK "$PY" "$APP/kalici.py" goc 2>&1)"; echo "$OUT" | tail -3 | sed 's/^/   /'
EKSIK="$($OLARAK "$PY" -c "import sys; sys.path.insert(0, '$APP'); import depo; print(depo.Depo().eksik_goc())" 2>&1 | tail -1)"
if [ "$EKSIK" != "[]" ]; then
  echo "DUR: göçler tamamlanmadı (eksik: $EKSIK); içe aktarma YAPILMADI. Veritabanında oluşan tablolar silinmedi."
  echo "== bitti (durdu)"; exit 1
fi
echo "   eksik göç yok"

echo "-- içe aktarma (depo_aktar.py ice; yalnız boş veritabanına; kuyrukta bekleyenler hosting'te kalır)"
OUT="$($OLARAK "$PY" "$APP/depo_aktar.py" ice --kanal "$KANAL" 2>&1)"; RC_ICE=$?; echo "$OUT" | tail -3 | sed 's/^/   /'
[ "$RC_ICE" = "0" ] || { echo "DUR: içe aktarma hata verdi (çıkış $RC_ICE); işlem geri alındı, tablolar boş kaldı, silinmedi."; echo "== bitti (durdu)"; exit 1; }
N="$($PSQL -d "$DB" -c "SELECT count(*) FROM konusmalar" 2>&1 | tr -d ' \n')"
[ "$N" != "0" ] && [[ "$N" =~ ^[0-9]+$ ]] || { echo "DUR: içe aktarma yazmadı (konuşma sayısı: $N). Tablolar silinmedi."; echo "== bitti (durdu)"; exit 1; }

echo "-- sonrası: kaynak ↔ Postgres"
$OLARAK "$PY" "$GECIS/kapi_f.py" karsilastir "$KANAL" --veri "$PM_HOME/data" 2>&1 | sed 's/^/ /'
RC="${PIPESTATUS[0]}"
echo "-- servis (değişmedi; dosya modunda)"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp --no-pager 2>&1 | sed 's/^/   /'
[ "$RC" = "0" ] || { echo "DUR: karşılaştırmada uyuşmazlık var; kalıcı moda GEÇME, asistana bildir."; echo "== bitti (durdu)"; exit 2; }
echo "== bitti: aktarma tamam; ajan hâlâ dosya modunda, worker off"
