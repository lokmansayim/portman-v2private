#!/usr/bin/env bash
# PORTMAN · Kapı F.2 (İE-02): geçiş öncesi SALT OKUNUR durum. Hiçbir dosyayı, ayarı, veritabanını ya da servisi değiştirmez.
#   ssh portman-vps 'bash -s' < kapi_f_on.sh > 2_on_durum.txt
# Gösterir: hosting ayarı (worker off olmalı; mod, Opus ayarı, paket), ajanın elinde iş olup olmadığı, gönderilemeyip bekleyen sonuç,
# ajanın dosya modunda olduğu, Postgres'teki portman veritabanının BOŞ olduğu (tablo yok), VPS'teki konuşma ve proje dosyalarının
# sayısı ve E projesinin r01 dosyaları (ad, boyut, özet). Yazdırmaz: anahtar, numara, mesaj metni.
# Test için: PM_HOME, PM_ENV, PM_BASLANGIC, PM_PSQL (postgres olarak psql), PM_PROJE.
set -u
export PM_HOME="${PM_HOME:-/opt/portman}" PM_ENV="${PM_ENV:-/etc/portman/agent.env}" PM_BASLANGIC="${PM_BASLANGIC:-2026-09-29 01:30:00}"
export PM_PROJE="${PM_PROJE:-PM-PATRON-20260929-33807}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA}"; DB="${PM_DB:-portman}"
echo "== Kapı F.2 · geçiş öncesi salt okunur durum · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- servis"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
echo "   PORTMAN_PG_DSN: $(grep -c '^PORTMAN_PG_DSN=' "$PM_ENV" 2>/dev/null || true) · /etc/portman/pg.env: $([ -e /etc/portman/pg.env ] && echo VAR || echo yok) · kalici.conf: $([ -e /etc/systemd/system/portman-agent.service.d/kalici.conf ] && echo VAR || echo yok)"
echo "-- Postgres (portman veritabanı BOŞ olmalı: tablo yok)"
echo "   veritabanları: $($PSQL -d postgres -c "SELECT string_agg(datname || ' (sahibi ' || pg_get_userbyid(datdba) || ')', ', ' ORDER BY datname) FROM pg_database WHERE datname LIKE 'portman%'" 2>&1 | tr '\n' ' ')"
TAB="$($PSQL -d "$DB" -c "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')" 2>&1 | tr -d ' \n')"
echo "   portman içindeki tablo sayısı: $TAB"
if [ "$TAB" != "0" ]; then
  echo "   tablolar: $($PSQL -d "$DB" -c "SELECT string_agg(schemaname || '.' || tablename, ' ' ORDER BY 1) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')" 2>&1 | tr '\n' ' ')"
fi
python3 - <<'PY'
import hashlib, json, os, re, time, urllib.error, urllib.request
from pathlib import Path
HOME, ENV, BAS, PROJE = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"]), os.environ["PM_BASLANGIC"], os.environ["PM_PROJE"]
DATA = HOME / "data"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
oku = lambda p: p.read_text().strip() if p.exists() else ""
pksha = oku(HOME / "app" / "PACKAGE_SHA256")
ajan = re.search(r'SURUM = "([^"]+)"', oku(HOME / "agent.py"))
print(f"-- ajan {ajan.group(1) if ajan else '?'} · paket {pksha[:16] or 'yok'}")
g = HOME / "logs" / "agent.log"
satirlar = g.read_text(errors="replace").splitlines() if g.exists() else []
bas = [i for i, s in enumerate(satirlar) if s[20:].startswith("başladı")]
son = satirlar[bas[-1]:] if bas else satirlar
if bas:
    m = re.search(r"mod (.+)$", satirlar[bas[-1]]); print(f"   son başlama {satirlar[bas[-1]][:19]} · mod {m.group(1) if m else '?'}")
alindi = [s[:19] for s in son if s[20:].startswith("iş alındı")]; bitti = [s[:19] for s in son if s[20:].startswith("iş bitti")]
acik = len(alindi) - len(bitti)
print(f"   son başlamadan beri iş alındı {len(alindi)} · bitti {len(bitti)} · elde iş: {'VAR' if acik > 0 else 'yok'}"
      + (f" · son iş {bitti[-1]}" if bitti else ""))
f_sonrasi = [s for s in satirlar if s[:19] >= BAS]
print(f"   {BAS} sonrası: iş alındı {sum(s[20:].startswith('iş alındı') for s in f_sonrasi)} · api hatası {sum(' api:' in ' ' + s[20:] for s in f_sonrasi)}"
      f" · beklenmeyen {sum(s[20:].startswith('beklenmeyen') for s in f_sonrasi)}")
bekleyen = len(list((DATA / "pending").glob("*.json")))
print(f"   gönderilemeyip bekleyen sonuç: {bekleyen}")
print("-- VPS veri dizini (dosya modu; numara ve metin yazılmaz)")
dz = DATA / "durum"
print(f"   durum/: {len(list(dz.glob('*.json'))) if dz.is_dir() else 0} konuşma dosyası · projects/: "
      f"{len([p for p in (DATA / 'projects').iterdir() if p.is_dir() and not p.name.startswith('.')]) if (DATA / 'projects').is_dir() else 0} proje klasörü")
rk = DATA / "projects" / PROJE
if rk.is_dir():
    for p in sorted(rk.rglob("*")):
        if p.is_file():
            print(f"   {PROJE}/{p.relative_to(rk)}: {p.stat().st_size} B · {sha(p)[:16]}")
else:
    print(f"   {PROJE}: klasör YOK")
ez = [p for p in dz.glob("*.json") if ((json.loads(p.read_text(encoding="utf-8")).get("son_is_emri") or {}).get("is_emri_no")) == PROJE] if dz.is_dir() else []
for p in ez:
    d = json.loads(p.read_text(encoding="utf-8"))
    kanon = json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    oz = hashlib.sha256((p.stem + "\0" + kanon + "\n").encode("utf-8")).hexdigest()[:16]
    rev = int((d.get("son_is_emri") or {}).get("revizyon") or 0)
    print(f"   {PROJE} konuşması (VPS kopyası): aşama {d.get('asama')} · r{rev:02d} · tek konuşma özeti {oz}")
print(f"   öz-test: {(json.loads(oku(DATA / 'self-test-result.json') or '{}')).get('state')}")
print("-- hosting (ajanın anahtarıyla op=settings; anahtar yazılmaz)")
env = {}
w = None
try:
    for s in ENV.read_text().splitlines():
        if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-f"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode()); pk = j.get("package") or {}
    w = j.get("worker")
    print(f"   api {j.get('api')} · enabled {j.get('enabled')} · worker {w} · mode {j.get('mode')} · dry_run {j.get('dry_run')} · vps_komut {j.get('vps_komut')}")
    print(f"   llm {(j.get('llm') or {}).get('backend')}/{(j.get('llm') or {}).get('model')} · patron_teknik_not {j.get('patron_teknik_not')} · "
          f"paket {str(pk.get('sha256'))[:16]} ({'VPS ile aynı' if pk.get('sha256') == pksha else 'FARKLI'})")
except urllib.error.HTTPError as e:
    print(f"   HTTP {e.code}")
except Exception as e:
    print(f"   ulaşılamadı ({type(e).__name__})")
print(f"== hazır mı: worker {'off ✓' if w == 'off' else repr(w) + ' ✗ (off olmalı)'} · elde iş {'yok ✓' if acik <= 0 else 'VAR ✗'} · bekleyen sonuç {'0 ✓' if not bekleyen else str(bekleyen) + ' ✗'}")
PY
echo "== bitti"
