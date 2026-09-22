"""Uçtan uca YEREL test (Meta yok, OpenAI yok): PHP yakalama → Python worker (manuel çıkarım) → PHP tick (sahte Meta) → doğrulama.
Çalıştırma: python3 tests/e2e_local.py [portman/lib.php yolu]   (kanal/ kopyası geçici dizinde kurulur; canlı state'e dokunmaz)
"""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

KANAL = Path(__file__).resolve().parents[1]
tmp = Path(tempfile.mkdtemp(prefix="pm_kanal_e2e_"))
kopya = tmp / "kanal"
shutil.copytree(KANAL, kopya, ignore=shutil.ignore_patterns("__pycache__", "state.json", "state.lock", "worker.lock", "tick.lock", "projects", "durum", "checks", "*.log", "self-test-result.json"))
(kopya / "self-test-request.json").unlink(missing_ok=True)   # bu testte öz-test koşmasın
s = json.loads((kopya / "settings.json").read_text(encoding="utf-8"))
s.update(enabled=True, enabled_at=int(time.time()) - 3600, dry_run=False, mode="patron"); s["llm"]["backend"] = "manuel"
(kopya / "settings.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
php = ["php", str(kopya / "tests" / "e2e_steps.php")]
lib = sys.argv[1] if len(sys.argv) > 1 else str(kopya / "tests" / "lib.snapshot.php")
if not Path(lib).is_file():
    raise SystemExit(f"lib.php bulunamadı: {lib}  (parametre olarak portman/lib.php yolunu verin)")
hazir = {r["id"]: r["talep"] for r in json.loads((kopya / "beyin" / "testler" / "cikarim_a.json").read_text(encoding="utf-8"))}
mesajlar = {r["id"]: r for r in json.loads((kopya / "beyin" / "testler" / "mesajlar.json").read_text(encoding="utf-8"))}

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr); raise SystemExit(f"komut başarısız: {cmd}")
    return r.stdout.strip()

sonuc = []
def ok(c, ne): sonuc.append(c); print(("  ✓ " if c else "  ✗ ") + ne)

print("1) PHP yakalama (imzalı sahte webhook)")
run(php + ["init", str(tmp), lib])
out = json.loads(run(php + ["capture", str(tmp), lib, mesajlar[1]["mesaj"], "wamid.E2E1"]).splitlines()[-1])
ok(out["owned"] == ["wamid.E2E1"], "Patron mesajı sahiplenildi")
st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
ok(st["inbound"]["wamid.E2E1"]["state"] == "queued", "PHP'nin yazdığı kuyruk satırı Python'da okunuyor")

print("2) Python worker (manuel çıkarım; LLM yerine hazır çıktı)")
st["inbound"]["wamid.E2E1"]["test_cikarim"] = hazir[1]
(kopya / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
t0 = time.time(); log = run([sys.executable, str(kopya / "worker.py")]); sure = time.time() - t0
st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
r = st["inbound"]["wamid.E2E1"]
ok(r["state"] == "done" and r["result"]["eylem"] == "is_emri", f"işlendi → is_emri ({r['result'].get('is_emri_no')}), {sure:.1f} s")
outs = sorted(st["outbound"].values(), key=lambda x: x["seq"])
ok(len(outs) == 2 and outs[0]["kind"] == "text" and outs[1]["kind"] == "document" and outs[1]["state"] == "pending", "giden: metin + PDF belge satırı (pending)")
pdf = Path(outs[1]["file"]); ok(pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-" and pdf.stat().st_size > 50000, f"PDF üretildi ({pdf.stat().st_size if pdf.exists() else 0} B)")
val = json.loads((pdf.parent / "validation.json").read_text(encoding="utf-8")); ok(val.get("passed") is True, "motor doğrulaması geçti")

print("3) PHP tick (sahte Meta) → gönderim ve panel yayını")
h = json.loads(run(php + ["tick", str(tmp), lib]).splitlines()[-1])
dump = json.loads(run(php + ["dump", str(tmp), lib]).splitlines()[-1])
o = dump["state"]["outbound"]
ok(h["sent"] == 2 and all(x["state"] == "accepted" and x["wamid"] for x in o.values()), "2 satır gönderildi → accepted + wamid")
calls = [json.loads(l) for l in (tmp / "meta_calls.jsonl").read_text(encoding="utf-8").splitlines()]
ok([c["url"].rsplit("/", 1)[-1] for c in calls] == ["messages", "media", "messages"] and calls[2]["body"]["type"] == "document"
   and calls[2]["body"]["document"]["filename"] == pdf.name, "Meta çağrıları: metin → medya yükleme → belge (dosya adı doğru)")
ok(set(dump["outgoing"]) == set(o), "store.json outgoing'e yayınlandı")
ok("sk-" not in (kopya / "state.json").read_text() and "TEST-TOKEN" not in (kopya / "state.json").read_text(), "state.json'da anahtar/jeton yok")

print("4) Aynı gönderenden ikinci mesaj: onay")
out = json.loads(run(php + ["capture", str(tmp), lib, "onaylıyorum", "wamid.E2E2"]).splitlines()[-1])
st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
st["inbound"]["wamid.E2E2"]["test_cikarim"] = {"niyet": "onay", "guven": "yuksek", "ozet": "Planı onaylıyorsunuz."}
(kopya / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
run([sys.executable, str(kopya / "worker.py")])
st = json.loads((kopya / "state.json").read_text(encoding="utf-8"))
r2 = st["inbound"]["wamid.E2E2"]; cev = [x for x in st["outbound"].values() if x["inbound_id"] == "wamid.E2E2"]
ok(r2["result"]["gerekce"] == "plan onaylandı" and len(cev) == 1 and "Onayınız kaydedildi" in cev[0]["body"], "konuşma durumu korunmuş: onay kaydedildi")
h = json.loads(run(php + ["tick", str(tmp), lib]).splitlines()[-1]); ok(h["sent"] == 1, "onay cevabı gönderildi")

print(f"\nSONUÇ: {sum(sonuc)}/{len(sonuc)} geçti  (geçici dizin: {tmp})")
if all(sonuc):
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if all(sonuc) else 1)
