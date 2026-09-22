"""Uçtan uca YEREL VPS testi (Meta yok, OpenAI yok): PHP yakalama → hosting API (php -S) → VPS ajanı (paket indirir,
manuel çıkarımla üretir, sonucu multipart yollar) → PHP tick (sahte Meta) → doğrulama. Canlı hiçbir şeye dokunmaz.
Çalıştırma: python3 kanal/tests/e2e_vps.py <portman/lib.php yolu>
"""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KANAL = ROOT / "kanal"
lib = sys.argv[1] if len(sys.argv) > 1 else ""
if not Path(lib).is_file():
    raise SystemExit("lib.php yolu gerekli")
tmp = Path(tempfile.mkdtemp(prefix="pm_vps_e2e_"))
kopya = tmp / "kanal"
shutil.copytree(KANAL, kopya, ignore=shutil.ignore_patterns("__pycache__", "state.json", "state.lock", "worker.lock", "tick.lock", "projects", "durum", "checks", "*.log", "self-test-result.json", "package", "api_token.txt"))
(kopya / "self-test-request.json").unlink(missing_ok=True)
for d in ("beyin", "motor", "is_emri"):          # paket kopyaları yerine kaynak dizinler
    if (kopya / d).exists(): shutil.rmtree(kopya / d)
    shutil.copytree(ROOT / d, kopya / d, ignore=shutil.ignore_patterns("__pycache__", "durum"))
s = json.loads((KANAL / "settings.json").read_text(encoding="utf-8"))
s.update(enabled=True, enabled_at=int(time.time()) - 3600, dry_run=False, mode="patron", worker="vps", vps_poll_s=1, ayarlar_json="/yok/ayarlar.json")
s["llm"]["backend"] = "manuel"
(kopya / "settings.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
TOKEN = hashlib.sha256(os.urandom(16)).hexdigest()
(kopya / "api_token.txt").write_text(TOKEN + "\n")
# paket: kopya'dan (worker.py + beyin/motor/is_emri + referanslar + agent.py)
(kopya / "package").mkdir()
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(kopya / "worker.py", "worker.py")
    for ad in ("ref_h-connector.json", "ref_source-6x8.dxf", "DejaVuSans.ttf"):
        z.write(kopya / ad, ad)
    for d in ("beyin", "motor", "is_emri"):
        for p in (kopya / d).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts: z.write(p, f"{d}/{p.relative_to(kopya / d).as_posix()}")
    z.write(ROOT / "vps" / "agent.py", "agent.py"); z.writestr("SURUM.txt", "test\n")
raw = buf.getvalue(); PAKET_SHA = hashlib.sha256(raw).hexdigest()
(kopya / "package" / "current.zip").write_bytes(raw); (kopya / "package" / "current.sha256").write_text(PAKET_SHA + "\n")
www = tmp / "www"; www.mkdir(); shutil.copy(kopya / "tests" / "api_endpoint_test.php", www / "kanal_api.php")
env = {**os.environ, "PM_TEST_TMP": str(tmp), "PM_TEST_LIB": lib}
php_steps = ["php", str(kopya / "tests" / "e2e_steps.php")]

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout, r.stderr); raise SystemExit(f"komut başarısız: {cmd}")
    return r.stdout.strip()

sonuc = []
def ok(c, ne): sonuc.append(c); print(("  ✓ " if c else "  ✗ ") + ne)

print("1) hosting: PHP yakalama + kuyruk (manuel çıkarım satıra iliştirilir)")
run(php_steps + ["init", str(tmp), lib])
hazir = {r["id"]: r["talep"] for r in json.loads((kopya / "beyin" / "testler" / "cikarim_a.json").read_text(encoding="utf-8"))}
mesajlar = {r["id"]: r for r in json.loads((kopya / "beyin" / "testler" / "mesajlar.json").read_text(encoding="utf-8"))}
out = json.loads(run(php_steps + ["capture", str(tmp), lib, mesajlar[1]["mesaj"], "wamid.VPS1"]).splitlines()[-1])
ok(out["owned"] == ["wamid.VPS1"], "Patron mesajı sahiplenildi")
st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
st["inbound"]["wamid.VPS1"]["test_cikarim"] = hazir[1]
(kopya / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")

print("2) hosting API (php -S) ayağa kalkıyor")
port = 8099 + (os.getpid() % 500)
srv = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", str(www)], env=env, stdout=(tmp / "php.log").open("w"), stderr=subprocess.STDOUT)
time.sleep(1.5)
import urllib.request, urllib.error
def api(op, token=TOKEN, body=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/kanal_api.php?op={op}", data=(json.dumps(body).encode() if body is not None else None),
                                 headers={"X-Portman-Token": token, **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read().decode() or "{}")
try:
    code, j = api("settings", token="yanlis" * 8)
    ok(code == 401, "yanlış anahtar → 401")
    code, j = api("settings")
    ok(code == 200 and j["worker"] == "vps" and j["package"]["sha256"] == PAKET_SHA and j.get("openai_key") == "sk-test-not-real-key", "settings: worker=vps, paket sha, LLM anahtarı (yalnız yetkili ajana)")
    code, j = api("bilinmeyen")
    ok(code == 400, "bilinmeyen op → 400")

    print("3) VPS ajanı (tek iş modu): paket indir → öz-test yok → iş al → üret → sonucu yolla")
    vhome = tmp / "vpshome"
    aenv = {**os.environ, "PORTMAN_HOME": str(vhome), "PORTMAN_API_URL": f"http://127.0.0.1:{port}/kanal_api.php", "PORTMAN_API_TOKEN": TOKEN, "PORTMAN_AGENT_ONESHOT": "1"}
    aenv.pop("OPENAI_API_KEY", None)
    t0 = time.time()
    r1 = subprocess.run([sys.executable, str(ROOT / "vps" / "agent.py")], env=aenv, capture_output=True, text=True, timeout=300)
    ok(r1.returncode == 3 and (vhome / "app" / "worker.py").exists() and (vhome / "app" / "PACKAGE_SHA256").read_text().strip() == PAKET_SHA, f"ilk çalıştırma: paket kuruldu, yeniden başlatma isteği (çıkış 3) [{r1.returncode}]")
    r2 = subprocess.run([sys.executable, str(ROOT / "vps" / "agent.py")], env=aenv, capture_output=True, text=True, timeout=600)
    sure = time.time() - t0
    ok(r2.returncode == 0, f"ikinci çalıştırma: iş alındı ve sonuç gönderildi (çıkış {r2.returncode}, {sure:.1f} s)")
    if r2.returncode != 0: print(r2.stdout[-2000:], r2.stderr[-2000:])
    st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
    r = st["inbound"]["wamid.VPS1"]
    ok(r["state"] == "done" and r.get("worker") == "vps" and r["result"]["eylem"] == "is_emri" and r["result"].get("worker") == "vps", f"hosting kuyruğu: done, worker=vps, eylem is_emri ({r['result'].get('is_emri_no')})")
    outs = sorted(st["outbound"].values(), key=lambda x: x["seq"])
    ok(len(outs) == 2 and outs[0]["kind"] == "text" and outs[1]["kind"] == "document" and outs[1]["state"] == "pending", "giden: metin + PDF belge satırı (pending)")
    pdf = Path(outs[1]["file"])
    ok(pdf.is_absolute() and str(pdf).startswith(str(kopya / "projects")) and pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-" and hashlib.sha256(pdf.read_bytes()).hexdigest() == outs[1]["sha256"], f"PDF hostinge yazıldı ({pdf.stat().st_size if pdf.exists() else 0} B), yol projects/ altında, sha eşleşti")
    ok((kopya / "durum" / f"{st['inbound']['wamid.VPS1']['sender']}.json").exists(), "görüşme durumu hostinge yazıldı (durum/<sender>.json)")
    hb = json.loads((kopya / "vps-health.json").read_text(encoding="utf-8")); wh = json.loads((kopya / "worker-health.json").read_text(encoding="utf-8"))
    ok(hb["worker"] == "vps" and hb["jobs_done"] == 1 and wh["worker"] == "vps" and hb["package_sha256"] == PAKET_SHA, "heartbeat: vps-health.json + worker-health.json")
    ok((kopya / "vps.log").exists() and "iş bitti" in (kopya / "vps.log").read_text(encoding="utf-8"), "ajan günlüğü hostinge aktı (vps.log)")
    ok("sk-" not in (kopya / "state.json").read_text() and not list(vhome.rglob("*.env")) and "sk-test" not in (vhome / "logs" / "agent.log").read_text(), "anahtar ne state.json'da ne ajan diskinde/günlüğünde")

    print("4) hosting tick (sahte Meta) → gönderim")
    h = json.loads(run(php_steps + ["tick", str(tmp), lib]).splitlines()[-1])
    dump = json.loads(run(php_steps + ["dump", str(tmp), lib]).splitlines()[-1])
    o = dump["state"]["outbound"]
    ok(h["sent"] == 2 and all(x["state"] == "accepted" and x["wamid"] for x in o.values()), "2 satır gönderildi → accepted + wamid")
    calls = [json.loads(l) for l in (tmp / "meta_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    ok([c["url"].rsplit("/", 1)[-1] for c in calls] == ["messages", "media", "messages"] and calls[2]["body"]["document"]["filename"] == pdf.name, "Meta çağrıları: metin → medya → belge")

    print("5) koruma: worker=hosting iken claim iş vermez; tekrar result reddedilir")
    s2 = json.loads((kopya / "settings.json").read_text(encoding="utf-8")); s2["worker"] = "hosting"
    (kopya / "settings.json").write_text(json.dumps(s2), encoding="utf-8")
    code, j = api("claim", body={})
    ok(code == 200 and j["job"] is None and j.get("reason") == "worker=hosting", "worker=hosting → claim boş")
    # hosting worker.py de vps modunda üretmemeli
    s2["worker"] = "vps"; (kopya / "settings.json").write_text(json.dumps(s2), encoding="utf-8")
    run(php_steps + ["capture", str(tmp), lib, "P6001 aynalı", "wamid.VPS2"])
    subprocess.run([sys.executable, str(kopya / "worker.py")], capture_output=True, text=True, timeout=120)
    st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
    ok(st["inbound"]["wamid.VPS2"]["state"] == "queued", "settings.worker=vps → hosting worker.py kuyruğa dokunmadı")
    code, j = api("result")
    ok(code == 422, "eksik/bozuk result → 422")
finally:
    srv.terminate()
print(f"\n{sum(sonuc)}/{len(sonuc)} geçti — geçici dizin: {tmp}")
sys.exit(0 if all(sonuc) else 1)
