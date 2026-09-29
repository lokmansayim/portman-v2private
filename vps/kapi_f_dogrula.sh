#!/usr/bin/env bash
# PORTMAN · Kapı F sonu (İE-02): kalıcı mod ve servis sağlığı · SALT OKUNUR. Hiçbir dosyayı, ayarı, veritabanını ya da servisi değiştirmez.
#   ssh portman-vps 'bash -s' < kapi_f_dogrula.sh > 8_son.txt
# Gösterir: servis ve kalıcı mod dosyaları, hosting ayarı (worker, mod, Opus ayarı, paket), F başladıktan sonraki günlük olayları,
# Postgres kayıt sayıları ve sağlık (açık iş, gönderilemeyen ya da belirsiz satır, diskte bekleyen mesaj), kaynak ↔ Postgres
# karşılaştırmasının yeniden koşusu (E projesi dahil). Yazdırmaz: anahtar, numara, mesaj metni.
# Test için: PM_HOME, PM_ENV, PM_GECIS, PM_PY, PM_OLARAK, PM_BASLANGIC.
# Gövde tek işlevdir ve girdisi /dev/null'dur: 'bash -s' betiği girdiden okurken içindeki bir komut (ör. sudo) betiğin kalanını
# yutmasın (29.09 F.5'te aktarmadan sonraki satırlar böyle çalışmadı). Bash işlevi çalıştırmadan önce dosyanın tamamını okur.
ana() {
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PM_ENV="${PM_ENV:-/etc/portman/agent.env}"; GECIS="${PM_GECIS:-/var/tmp/portman-gecis}"
PY="${PM_PY:-$PM_HOME/venv/bin/python}"; APP="$PM_HOME/app"; BAS="${PM_BASLANGIC:-2026-09-29 01:30:00}"
OLARAK="${PM_OLARAK:-sudo -u portman env PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=$PM_HOME/data}"
ETC="${PM_ETC:-/etc/portman}"; DROPIN="${PM_DROPIN:-/etc/systemd/system/portman-agent.service.d}"
echo "== Kapı F · kalıcı mod ve sağlık · salt okunur · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- servis"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
echo "   pg.env: $([ -e "$ETC/pg.env" ] && stat -c '%U:%G %a' "$ETC/pg.env" || echo yok) · kalici.conf: $([ -e "$DROPIN/kalici.conf" ] && echo VAR || echo yok) · agent.env'de PORTMAN_PG_DSN: $(grep -c '^PORTMAN_PG_DSN=' "$PM_ENV" 2>/dev/null || true)"
PID="$(systemctl show portman-agent -p MainPID --value 2>/dev/null)"
echo "   ajan sürecinin ortamında PORTMAN_PG_DSN (1 olmalı): $( { tr '\0' '\n' < "/proc/$PID/environ"; } 2>/dev/null | grep -c '^PORTMAN_PG_DSN=' || true)"
PM_HOME="$PM_HOME" PM_ENV="$PM_ENV" BAS="$BAS" python3 - <<'PY'
import json, os, re, urllib.error, urllib.request
from pathlib import Path
HOME, ENV, BAS = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"]), os.environ["BAS"]
oku = lambda p: p.read_text().strip() if p.exists() else ""
pksha = oku(HOME / "app" / "PACKAGE_SHA256")
print("-- hosting (ajanın anahtarıyla op=settings; anahtar yazılmaz)")
try:
    env = {}
    for s in ENV.read_text().splitlines():
        if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-f"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode()); pk = j.get("package") or {}
    print(f"   api {j.get('api')} · enabled {j.get('enabled')} · worker {j.get('worker')} · mode {j.get('mode')} · dry_run {j.get('dry_run')} · vps_komut {j.get('vps_komut')}")
    print(f"   llm {(j.get('llm') or {}).get('backend')}/{(j.get('llm') or {}).get('model')} · paket {str(pk.get('sha256'))[:16]} ({'VPS ile aynı' if pk.get('sha256') == pksha else 'FARKLI'})")
except urllib.error.HTTPError as e:
    print(f"   HTTP {e.code}")
except Exception as e:
    print(f"   ulaşılamadı ({type(e).__name__})")
print(f"-- günlük ({BAS} sonrası; numara ve metin yazılmaz)")
g = HOME / "logs" / "agent.log"
s = [x for x in (g.read_text(errors="replace").splitlines() if g.exists() else []) if x[:19] >= BAS]
for x in s:
    r = x[20:]
    if r.startswith(("başladı", "paket", "agent.py", "öz-test", "kalıcı mod bekliyor", "yeniden başlama", "durduruldu")):
        print(f"   {x[:19]} · {re.sub(r'[0-9a-f]{16,}', '…', r)[:110]}")
sayac = {a: sum(a in " " + x[20:] for x in s) for a in ("mod kalıcı (Postgres)", "mod dosya", "kalıcı mod bekliyor", "Postgres'e ulaşılamadı",
                                                    " api:", "beklenmeyen", "iş alındı", "hosting sonucu almadı", "diskteki mesaj")}
print(f"   sayılar: {sayac}")
print(f"   gönderilemeyip bekleyen sonuç (dosya modu): {len(list((HOME / 'data' / 'pending').glob('*.json')))} · "
      f"Postgres'e yazılmayı bekleyen: {len(list((HOME / 'data' / 'kalici_bekleyen').glob('*.json')))} · "
      f"yazılamayan: {len(list((HOME / 'data' / 'kalici_bekleyen' / 'hatali').glob('*.json')))}")
st = json.loads(oku(HOME / "data" / "self-test-result.json") or "{}")
print(f"   öz-test: {st.get('state')} (paket başına bir kez; yeniden koşmadıysa LLM çağrısı yok)")
PY
echo "-- Postgres sağlığı"
KOD="$(cat <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import depo
d = depo.Depo()
with d.baglan() as c:
    print("sunucu:", c.execute("SHOW server_version").fetchone()["server_version"], "· eksik göç:", d.eksik_goc())
    print("açık iş:", d.acik_is_sayisi(), "· işler:", {r["durum"]: r["n"] for r in c.execute("SELECT durum, count(*) AS n FROM isler GROUP BY 1 ORDER BY 1")})
    print("giden:", {r["durum"]: r["n"] for r in c.execute("SELECT durum, count(*) AS n FROM giden GROUP BY 1 ORDER BY 1")} or "yok",
          "· son 24 saat:", d.gonderilemeyen_sayisi(24, 300))
    print("F'den sonra işlenen iş:", c.execute("SELECT count(*) AS n FROM isler WHERE basladi IS NOT NULL").fetchone()["n"],
          "(içe aktarılan işlerde başlama anı yok)")
PY
)"
$OLARAK "$PY" -c "$KOD" "$APP" 2>&1 | sed 's/^/   /'
if [ -f "$GECIS/kapi_f.py" ] && [ -d "$GECIS/kanal" ]; then
  echo "-- kaynak ↔ Postgres (F.5'teki karşılaştırmanın yeniden koşusu; F'den sonra iş işlendiyse konuşma özeti değişir)"
  $OLARAK "$PY" "$GECIS/kapi_f.py" karsilastir "$GECIS/kanal" --veri "$PM_HOME/data" 2>&1 | sed 's/^/ /'
fi
echo "== bitti"
}
ana "$@" < /dev/null
