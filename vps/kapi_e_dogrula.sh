#!/usr/bin/env bash
# PORTMAN · Kapı E doğrulaması (İE-02). SALT OKUNUR: hiçbir dosyayı, ayarı ya da servisi değiştirmez.
#   ssh root@<VPS> 'bash -s' < kapi_e_dogrula.sh
# Gösterir: ajan ve paket sürümü, kurulu uygulamanın paketle aynı olduğu, DOSYA MODU (Postgres'e geçilmediği), öz-testin sonucu ve
# LLM token sayıları, E başladıktan sonraki günlük olayları (paket güncellemesi, başlama, işler ve giden mesaj sayısı, hatalar),
# hosting API sürümü ve ayarlar. Yazdırmaz: anahtar, telefon numarası, mesaj metni, LLM çıktısı.
# Test için: PM_HOME, PM_ENV, PM_BASLANGIC ("YYYY-MM-DD HH:MM:SS"; varsayılan 28.09 23:00).
set -u
export PM_HOME="${PM_HOME:-/opt/portman}" PM_ENV="${PM_ENV:-/etc/portman/agent.env}" PM_BASLANGIC="${PM_BASLANGIC:-2026-09-28 23:00:00}"
echo "== Kapı E · salt okunur doğrulama · betik 2026-09-28b · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- servis"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
echo "   PORTMAN_PG_DSN: $(grep -c '^PORTMAN_PG_DSN=' "$PM_ENV" 2>/dev/null || true) · /etc/portman/pg.env: $([ -e /etc/portman/pg.env ] && echo VAR || echo yok) · kalici.conf: $([ -e /etc/systemd/system/portman-agent.service.d/kalici.conf ] && echo VAR || echo yok)"
python3 - <<'PY'
import hashlib, io, json, os, re, time, urllib.error, urllib.request, zipfile
from pathlib import Path
HOME, ENV, BAS = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"]), os.environ["PM_BASLANGIC"]
iz = lambda b: hashlib.sha256(b).hexdigest()
app = HOME / "app"
def oku(p):
    try: return p.read_text().strip()
    except OSError: return ""
pksha = oku(app / "PACKAGE_SHA256")
ajan = re.search(r'SURUM = "([^"]+)"', oku(HOME / "agent.py")); isci = re.search(r'SURUM = "([^"]+)"', oku(app / "worker.py"))
print("-- sürümler")
print(f"   ajan {ajan.group(1) if ajan else '?'} · işçi {isci.group(1) if isci else '?'} · paket {oku(app / 'SURUM.txt') or '?'} · PACKAGE_SHA256 {pksha[:16] or 'yok'}")
z = HOME / "pkg" / f"{pksha}.zip"
if pksha and z.exists():
    raw = z.read_bytes()
    print(f"   pkg zip gerçek sha {iz(raw)[:16]} ({'adıyla aynı' if iz(raw) == pksha else 'ADIYLA FARKLI'})")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        adlar = [a for a in zf.namelist() if not a.endswith("/")]
        farkli = [a for a in adlar if not (app / a).is_file() or iz((app / a).read_bytes()) != iz(zf.read(a))]
        print(f"   kurulu uygulama ↔ paket: {len(adlar) - len(farkli)}/{len(adlar)} aynı · farklı ya da eksik {len(farkli)} {farkli[:5]}")
        if "agent.py" in adlar:
            print(f"   /opt/portman/agent.py ↔ paketteki agent.py: {'aynı' if (HOME / 'agent.py').exists() and iz((HOME / 'agent.py').read_bytes()) == iz(zf.read('agent.py')) else 'FARKLI'}")
print("-- öz-test (yeni paket için bir kez; WhatsApp'a göndermez)")
st = HOME / "data" / "self-test-result.json"
try:
    j = json.loads(st.read_text()); l = (j.get("adimlar") or {}).get("llm") or {}
    bitis = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(j["finished_at"])) if j.get("finished_at") else "-"
    print(f"   durum {j.get('state')} · bitiş {bitis} · {j.get('sure_s')} sn · işçi {j.get('surum')}")
    print(f"   adımlar: " + ", ".join(f"{k} {'geçti' if (v or {}).get('passed') else ('atlandı' if (v or {}).get('passed') is None else 'GEÇMEDİ')}" for k, v in (j.get("adimlar") or {}).items() if isinstance(v, dict)))
    if l:
        print(f"   LLM: {l.get('model')} · giriş {l.get('girdi_token')} · çıkış {l.get('cikti_token')} token · tekrar {'evet' if l.get('tekrar') else 'hayır'} · {l.get('sure_ms')} ms")
except (OSError, ValueError, KeyError) as e:
    print(f"   öz-test sonucu yok ya da okunamadı ({type(e).__name__})")
print(f"-- günlük ({BAS} sonrası; numara, kimlik ve metin yazılmaz)")
g = HOME / "logs" / "agent.log"
satirlar = [s for s in g.read_text(errors="replace").splitlines() if s[:19] >= BAS] if g.exists() else []
sayac = {"api": 0, "beklenmeyen": 0, "iş alındı": 0, "iş bitti": 0, "giden": 0}
for s in satirlar:
    t = s[:19]; r = s[20:]
    if r.startswith(("paket güncelleniyor", "paket kuruldu", "agent.py paketten", "agent.py güncellenemedi", "öz-test")):
        print(f"   {t} · {re.sub(r'[0-9a-f]{16,}', '…', r)[:90]}")
    elif r.startswith("başladı"):
        m = re.search(r"(vps-agent-v[\d.]+).* mod (.+)$", r); print(f"   {t} · başladı {m.group(1) if m else '?'} · mod {m.group(2) if m else '?'}")
    elif r.startswith("iş alındı"):
        sayac["iş alındı"] += 1; print(f"   {t} · iş alındı")
    elif r.startswith("iş bitti"):
        sayac["iş bitti"] += 1
        m = re.search(r"→ (\S+) .* ([\d.]+) s giden: (\d+)", r)
        if m: sayac["giden"] += int(m.group(3))
        print(f"   {t} · iş bitti → {m.group(1) if m else '?'} · {m.group(2) if m else '?'} sn · giden {m.group(3) if m else '?'}")
    elif " api:" in " " + r or r.startswith("api:"):
        sayac["api"] += 1; kod = re.search(r"HTTP (\d{3}) (\w+)", r); print(f"   {t} · api hatası {kod.group(1) + ' ' + kod.group(2) if kod else 'bağlantı/diğer'}")
    elif r.startswith("beklenmeyen") or r.startswith("sonuç gönderilemedi"):
        sayac["beklenmeyen"] += 1; print(f"   {t} · {r.split(':')[0]}")
print(f"   özet: iş alındı {sayac['iş alındı']} · iş bitti {sayac['iş bitti']} · işlerin giden mesajı {sayac['giden']} · api hatası {sayac['api']} · beklenmeyen/gönderilemedi {sayac['beklenmeyen']}")
print(f"   gönderilemeyip bekleyen sonuç: {len(list((HOME / 'data' / 'pending').glob('*.json')))}")
print("-- hosting (ajanın anahtarıyla op=settings; anahtar yazılmaz)")
env = {}
try:
    for s in ENV.read_text().splitlines():
        if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-e"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode()); pk = j.get("package") or {}
    print(f"   HTTP 200 · api {j.get('api')} · enabled {j.get('enabled')} · worker {j.get('worker')} · mode {j.get('mode')} · dry_run {j.get('dry_run')} · vps_komut {j.get('vps_komut')}")
    print(f"   LLM ayarı: backend {(j.get('llm') or {}).get('backend')} · model {(j.get('llm') or {}).get('model')} · agent.env'de ANTHROPIC_API_KEY: {'var' if env.get('ANTHROPIC_API_KEY') else 'yok'}")
    print(f"   hosting'in dağıttığı paket: {pk.get('surum')} · {str(pk.get('sha256'))[:16]} · VPS'teki kurulu paketle {'aynı' if pk.get('sha256') == pksha else 'FARKLI'}")
except urllib.error.HTTPError as e:
    print(f"   HTTP {e.code}")
except Exception as e:
    print(f"   ulaşılamadı ({type(e).__name__})")
PY
echo "== bitti"
