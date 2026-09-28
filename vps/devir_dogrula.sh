#!/usr/bin/env bash
# PORTMAN · 29.09 Opus 5.5 geçişinin (başka bir ajanın yaptığı) SALT OKUNUR doğrulaması. Hiçbir şeyi değiştirmez.
#   ssh root@<VPS> 'bash -s' < devir_dogrula.sh
# Gösterir: servis, paket ve dosya hash'leri, beyin/llm.py'nin tam hash'i, öz-test sonucu (model ve token), agent.env satır ADLARI,
# hosting ayarı, geçiş klasöründe anahtar biçimli dizge içeren dosya sayısı (değer yazılmaz), kurulan PHP paketleri, 29.09 günlüğü.
set -u
echo "== 29.09 geçişi · salt okunur doğrulama · $(date '+%Y-%m-%d %H:%M:%S %Z')"
systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
echo "   agent.env satır adları: $(sed -n 's/^\([A-Z_]*\)=.*/\1/p' /etc/portman/agent.env | tr '\n' ' ')"
echo "   agent.env izni: $(stat -c '%a %u:%g' /etc/portman/agent.env) · PORTMAN_PG_DSN: $(grep -c '^PORTMAN_PG_DSN=' /etc/portman/agent.env || true)"
echo "   VPS'te kurulu PHP paketleri: $(dpkg-query -W -f='${Package} ${Version}\n' 'php*' 2>/dev/null | tr '\n' ';' || echo yok)"
python3 - <<'PY'
import hashlib, io, json, os, re, time, urllib.error, urllib.request, zipfile
from pathlib import Path
H = Path("/opt/portman"); app = H / "app"
iz = lambda b: hashlib.sha256(b).hexdigest()
oku = lambda p: p.read_text().strip() if p.exists() else ""
pksha = oku(app / "PACKAGE_SHA256")
print(f"-- paket: {oku(app / 'SURUM.txt')} · PACKAGE_SHA256 {pksha}")
z = H / "pkg" / f"{pksha}.zip"
if z.exists():
    raw = z.read_bytes(); print(f"   pkg zip gerçek sha {'adıyla aynı' if iz(raw) == pksha else 'ADIYLA FARKLI'} · {len(raw)} B")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        adlar = [a for a in zf.namelist() if not a.endswith("/")]
        farkli = [a for a in adlar if not (app / a).is_file() or iz((app / a).read_bytes()) != iz(zf.read(a))]
        print(f"   kurulu uygulama ↔ paket: {len(adlar) - len(farkli)}/{len(adlar)} aynı · farklı/eksik {farkli[:5]}")
        print(f"   agent.py ↔ paket: {'aynı' if iz((H / 'agent.py').read_bytes()) == iz(zf.read('agent.py')) else 'FARKLI'}")
for ad in ("beyin/llm.py", "worker.py", "agent.py", "beyin/prompt.md", "beyin/sema.py"):
    p = app / ad
    print(f"   {ad}: {iz(p.read_bytes()) if p.exists() else 'yok'}")
m = re.search(r'SURUM = "([^"]+)"', oku(H / "agent.py")); print(f"   ajan {m.group(1) if m else '?'}")
print("-- öz-test")
try:
    j = json.loads((H / "data" / "self-test-result.json").read_text()); l = (j.get("adimlar") or {}).get("llm") or {}
    print(f"   durum {j.get('state')} · bitiş {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(j.get('finished_at', 0)))} · {j.get('sure_s')} sn")
    print("   adımlar: " + ", ".join(f"{k} {'geçti' if (v or {}).get('passed') else ('—' if (v or {}).get('passed') is None else 'GEÇMEDİ')}" for k, v in (j.get("adimlar") or {}).items() if isinstance(v, dict)))
    print(f"   LLM: {l.get('backend')} {l.get('model')} · giriş {l.get('girdi_token')} · çıkış {l.get('cikti_token')} · tekrar {'evet' if l.get('tekrar') else 'hayır'} · {l.get('sure_ms')} ms")
except Exception as e:
    print("   okunamadı:", type(e).__name__)
print("-- geçiş klasörü /root/portman-migration-staging (yalnız sayılar ve dosya adları; değer yazılmaz)")
k = Path("/root/portman-migration-staging")
if k.exists():
    dosyalar = [p for p in k.rglob("*") if p.is_file()]
    desen = re.compile(rb"sk-ant-[A-Za-z0-9_\-]{20,}|sk-(?:proj-)?[A-Za-z0-9_\-]{20,}|EAA[A-Za-z0-9]{20,}|PORTMAN_API_TOKEN=[0-9a-f]{20,}|ANTHROPIC_API_KEY=\S{10,}")
    isabet = []
    for p in dosyalar:
        try:
            if p.stat().st_size < 50_000_000 and desen.search(p.read_bytes()): isabet.append(str(p.relative_to(k)))
        except OSError: pass
    print(f"   {len(dosyalar)} dosya · {sum(p.stat().st_size for p in dosyalar) // 1024} KB · anahtar biçimli dizge içeren dosya: {len(isabet)} {isabet[:10]}")
    print(f"   üst düzey: {sorted(p.name for p in k.iterdir())[:20]}")
else:
    print("   yok")
print("-- hosting (ajanın anahtarıyla op=settings; anahtar yazılmaz)")
env = dict(s.split("=", 1) for s in Path("/etc/portman/agent.env").read_text().splitlines() if "=" in s)
try:
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"].strip(), "User-Agent": "portman-devir"})
    with urllib.request.urlopen(req, timeout=25) as r:
        s = json.loads(r.read().decode()); pk = s.get("package") or {}
    print(f"   api {s.get('api')} · enabled {s.get('enabled')} · worker {s.get('worker')} · mode {s.get('mode')} · dry_run {s.get('dry_run')} · llm {s.get('llm')}")
    print(f"   hosting paketi {pk.get('surum')} · {pk.get('sha256')} · VPS'le {'aynı' if pk.get('sha256') == pksha else 'FARKLI'} · OpenAI anahtarı veriliyor: {'evet' if s.get('openai_key') else 'hayır'}")
except urllib.error.HTTPError as e:
    print(f"   HTTP {e.code}")
print("-- günlük (29.09 00:00 sonrası)")
g = H / "logs" / "agent.log"
say = {}
for s in (g.read_text(errors="replace").splitlines() if g.exists() else []):
    if s[:19] < "2026-09-29 00:00:00": continue
    r = s[20:]
    for anahtar in ("paket güncelleniyor", "paket kuruldu", "agent.py paketten", "başladı", "öz-test", "iş alındı", "iş bitti", " api:", "beklenmeyen", "sonuç gönderilemedi"):
        if r.startswith(anahtar.strip()) or anahtar in " " + r:
            say[anahtar.strip()] = say.get(anahtar.strip(), 0) + 1
            if anahtar in ("başladı", "paket kuruldu", "öz-test"): print(f"   {s[:19]} · {re.sub(r'[0-9a-f]{16,}', '…', r)[:80]}")
print(f"   sayılar: {say}")
print(f"   gönderilemeyip bekleyen sonuç: {len(list((H / 'data' / 'pending').glob('*.json')))}")
PY
echo "== bitti"
