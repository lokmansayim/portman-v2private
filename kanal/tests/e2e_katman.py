"""İE-04 · uçtan uca YEREL test, mesaj katmanı AÇIK: GERÇEK PHP hattı (feature.php v1.3 + api.php v1.3 + portman/lib.php, php -S) →
VPS ajanı (kalıcı mod, Postgres) → hosting'e görsel başlıklı buton mesajı + PDF → PHP tick (sahte Meta: medya yükleme + interactive) →
buton cevabı (reply_id + context) → ajan onayı doğru revizyona bağlar; eski buton reddedilir. Meta ve LLM yok; canlıya dokunmaz.

Çalıştırma: PORTMAN_TEST_PG="host=… user=…" python3 kanal/tests/e2e_katman.py <portman/lib.php yolu>
"""
import hashlib, io, json, os, shutil, subprocess, sys, tempfile, time, uuid, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KANAL = ROOT / "kanal"
lib = sys.argv[1] if len(sys.argv) > 1 else ""
ADMIN = os.environ.get("PORTMAN_TEST_PG", "")
if not Path(lib).is_file():
    raise SystemExit("lib.php yolu gerekli (portman/lib.php; depoda yok)")
if not ADMIN:
    raise SystemExit("PORTMAN_TEST_PG gerekli (Postgres)")
import psycopg  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="pm_katman_e2e_"))
kopya = tmp / "kanal"
shutil.copytree(KANAL, kopya, ignore=shutil.ignore_patterns("__pycache__", "state.json", "state.lock", "worker.lock", "tick.lock", "projects", "durum",
                                                            "checks", "*.log", "self-test-result.json", "package", "api_token.txt"))
(kopya / "self-test-request.json").unlink(missing_ok=True)
for d in ("beyin", "motor", "is_emri"):
    if (kopya / d).exists(): shutil.rmtree(kopya / d)
    shutil.copytree(ROOT / d, kopya / d, ignore=shutil.ignore_patterns("__pycache__", "durum"))
s = json.loads((KANAL / "settings.example.json").read_text(encoding="utf-8"))
s.setdefault("llm", {}); s["llm"].update(backend="manuel", model="test", timeout_s=5)
s.update(enabled=True, enabled_at=int(time.time()) - 3600, dry_run=False, mode="patron", worker="vps", vps_poll_s=1, ayarlar_json="/yok/ayarlar.json",
         mesaj_katmani=True, ucb_taban_url="https://ornek.invalid/portman/3d")          # İE-04: katman açık (hosting ayarı)
(kopya / "settings.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
TOKEN = hashlib.sha256(os.urandom(16)).hexdigest()
(kopya / "api_token.txt").write_text(TOKEN + "\n")
(kopya / "package").mkdir()
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for ad in ("worker.py", "depo.py", "kalici.py", "depo_aktar.py", "etkilesim.py", "ref_h-connector.json", "ref_source-6x8.dxf", "DejaVuSans.ttf"):
        z.write(kopya / ad, ad)
    for g in sorted((kopya / "goc").glob("*.sql")):
        z.write(g, f"goc/{g.name}")
    for d in ("beyin", "motor", "is_emri"):
        for p in (kopya / d).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts: z.write(p, f"{d}/{p.relative_to(kopya / d).as_posix()}")
    z.write(ROOT / "vps" / "agent.py", "agent.py"); z.writestr("SURUM.txt", "test-katman\n")
raw = buf.getvalue(); PAKET_SHA = hashlib.sha256(raw).hexdigest()
(kopya / "package" / "current.zip").write_bytes(raw); (kopya / "package" / "current.sha256").write_text(PAKET_SHA + "\n")
www = tmp / "www"; www.mkdir(); shutil.copy(kopya / "tests" / "api_endpoint_test.php", www / "kanal_api.php")
env = {**os.environ, "PM_TEST_TMP": str(tmp), "PM_TEST_LIB": lib}
php_steps = ["php", str(kopya / "tests" / "e2e_steps.php")]
dbad = "e2ek_" + uuid.uuid4().hex[:8]
with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
    c.execute(f"CREATE DATABASE {dbad}")
DSN = f"{ADMIN} dbname={dbad}"
sys.path[:0] = [str(KANAL), str(ROOT)]
from depo import Depo  # noqa: E402
depo = Depo(DSN); depo.goc_uygula()


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:]); raise SystemExit(f"komut başarısız: {cmd}")
    return r.stdout.strip()


sonuc = []
def ok(c, ne): sonuc.append(bool(c)); print(("  ✓ " if c else "  ✗ ") + ne)
def q(sql, *a):
    with depo.baglan() as c: return c.execute(sql, a).fetchall()
def state(): return json.loads((kopya / "state.json").read_text(encoding="utf-8"))
def hazir_ekle(mid, talep):
    st = state(); st["inbound"][mid]["test_cikarim"] = talep
    (kopya / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
def meta_cagrilari():
    p = tmp / "meta_calls.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


port = 8899 + (os.getpid() % 300)
srv = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", str(www)], env=env, stdout=(tmp / "php.log").open("w"), stderr=subprocess.STDOUT)
time.sleep(1.5)
vhome = tmp / "vpshome"
aenv = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI", "ANTHROPIC"))}
aenv.update(PORTMAN_HOME=str(vhome), PORTMAN_API_URL=f"http://127.0.0.1:{port}/kanal_api.php", PORTMAN_API_TOKEN=TOKEN,
            PORTMAN_AGENT_ONESHOT="1", PORTMAN_PG_DSN=DSN)
def ajan(beklenen=(0,)):
    r = subprocess.run([sys.executable, str(ROOT / "vps" / "agent.py")], env=aenv, capture_output=True, text=True, timeout=600)
    if r.returncode not in beklenen: print(r.stdout[-3000:], r.stderr[-2000:])
    return r.returncode
try:
    print("1) katman açık: P6001 talebi → ajan → görsel başlıklı buton mesajı + PDF + 3D bağlantısı hosting'e (gerçek api.php)")
    run(php_steps + ["init", str(tmp), lib])
    run(php_steps + ["capture", str(tmp), lib, "P6001 aynalı", "wamid.K1"])
    hazir_ekle("wamid.K1", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "P6001 aynalı", "katalog_kodu": "P6001",
                            "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}]})
    ok(ajan((3,)) == 3 and (vhome / "app" / "etkilesim.py").exists(), "ilk çalıştırma: paket kuruldu (etkilesim.py dahil)")
    ok(ajan() == 0, "ikinci çalıştırma: iş işlendi ve hosting'e verildi")
    gin = state()["inbound"]["wamid.K1"]
    ok(gin["state"] == "done" and gin["result"]["eylem"] == "is_emri", "hosting kuyruğu: done, is_emri")
    o = state()["outbound"]
    kinds = [r["kind"] for r in sorted(o.values(), key=lambda r: r["seq"])]
    ok(kinds == ["interactive", "document", "interactive", "text"], f"hosting'e gelen satırlar (son metin: Patron teknik notu): {kinds}")
    b = next(r for r in o.values() if r["kind"] == "interactive" and r["interactive"]["type"] == "button")
    ok(b["file"].startswith(str(kopya / "projects/")) and Path(b["file"]).is_file() and Path(b["file"]).read_bytes()[:4] == b"\x89PNG"
       and b["interactive"]["header"]["file"] == b["file"], "başlık görseli (PNG) api.php ile projects/ altına alındı; yol yeniden yazıldı")
    rev = q("SELECT is_emri_no, rev, ekler FROM revizyonlar")[0]
    no = rev["is_emri_no"]
    ok(sorted(x["reply"]["id"] for x in b["interactive"]["action"]["buttons"]) == sorted([f"o:{no}:1", f"r:{no}:1"]), "butonlar: o:/r: kimlikleri revizyonla aynı")
    ok(rev["ekler"]["ifc"]["sema_hatasi"] == 0 and rev["ekler"]["ucb"]["url"] == f"https://ornek.invalid/portman/3d/{no}/r01/", "Postgres: ekler (IFC şema 0, 3D url)")

    print("2) PHP tick (sahte Meta): medya yükleme + interactive + document + cta_url")
    run(php_steps + ["tick", str(tmp), lib])
    o = state()["outbound"]
    ok(all(r["state"] == "accepted" for r in o.values()), "hosting: dört satır da API tarafından kabul edildi")
    c = meta_cagrilari()
    tipler = [("media" if x["url"].endswith("/media") else x["body"].get("type", "?") + ("/" + x["body"]["interactive"]["type"] if x["body"].get("type") == "interactive" else "")) for x in c]
    ok(tipler == ["media", "interactive/button", "media", "document", "interactive/cta_url", "text"], f"Meta çağrıları: {tipler}")
    ok(c[1]["body"]["interactive"]["header"]["image"]["id"] == "918800000000001" and len(c[1]["body"]["interactive"]["action"]["buttons"]) == 2, "buton mesajı: medya kimlikli başlık görseli, 2 buton")
    ok(c[4]["body"]["interactive"]["action"]["parameters"]["url"].endswith(f"/{no}/r01/"), "bağlantı butonu: 3D url")
    buton_wamid = b["wamid"] if (b := next(r for r in state()["outbound"].values() if r["kind"] == "interactive" and r["interactive"]["type"] == "button")) else None
    pdf = next(r for r in state()["outbound"].values() if r["kind"] == "document")
    run(php_steps + ["status", str(tmp), lib, pdf["wamid"], "delivered", str(int(time.time()) - 1)])
    ok(ajan((0, 4)) in (0, 4), "ajan eşitleme turu (kabul + teslim)")
    g = q("SELECT durum, dis_id FROM giden WHERE kind = 'interactive' ORDER BY sira")[0]
    ok(g["durum"] == "kabul_edildi" and g["dis_id"] == buton_wamid, "Postgres: buton satırının wamid'i kayıtlı (context doğrulaması için)")

    print("3) buton cevabı: eski/yanlış kimlik reddedilir; doğru 'Onayla' onayı doğru revizyona bağlar; LLM çağrılmaz")
    time.sleep(1.2)
    run(php_steps + ["button", str(tmp), lib, f"o:{no}:9", "Onayla", "wamid.KB1", buton_wamid])
    ok(state()["inbound"]["wamid.KB1"].get("reply_id") == f"o:{no}:9" and state()["inbound"]["wamid.KB1"].get("context_id") == buton_wamid, "PHP: reply_id + context_id kuyrukta")
    ok(ajan() == 0, "ajan: eski kimlik işlendi")
    r1 = state()["inbound"]["wamid.KB1"]["result"]
    ok(r1["eylem"] == "cevapla" and "eski buton" in r1["gerekce"] and q("SELECT durum FROM revizyonlar")[0]["durum"] == "onay_bekliyor", "eski kimlik: cevap verildi, revizyon değişmedi")
    run(php_steps + ["button", str(tmp), lib, f"o:{no}:1", "Onayla", "wamid.KB2", buton_wamid])
    ok(ajan() == 0, "ajan: onay butonu işlendi")
    r2 = state()["inbound"]["wamid.KB2"]["result"]
    j = q("SELECT cikarim FROM isler ORDER BY id DESC LIMIT 1")[0]["cikarim"]
    ok(r2["gerekce"] == "plan onaylandı" and j["meta"]["backend"] == "etkilesim", "onay: plan onaylandı, çıkarım kaynağı 'etkilesim' (LLM yok)")
    z = q("SELECT revizyon_durumu, onay_alintisi FROM onay_zinciri")[0]
    ok(z["revizyon_durumu"] == "onaylandi" and z["onay_alintisi"] == buton_wamid, "onay zinciri: onaylandı; alıntı = buton mesajı")
    run(php_steps + ["tick", str(tmp), lib])
    son = [r for r in state()["outbound"].values() if r["inbound_id"] in ("wamid.KB1", "wamid.KB2")]
    ok(all(r["kind"] == "text" and r["state"] == "accepted" for r in son) and len(son) == 4, "cevaplar (ve Patron teknik notları) metin olarak gönderildi")
    cikan = json.loads(run(php_steps + ["dump", str(tmp), lib]))["outgoing"]
    etk = [v for v in cikan.values() if v.get("kanal_kind") == "interactive"]
    ok(len(etk) == 2 and not any("o:" + no in json.dumps(v) for v in etk) and "[Onayla | Revize et]" in etk[0]["body"], "panele yayın: etkileşimli mesajlar buton başlıklarıyla, kimlik yok (Patron teknik notu kimliği taşıyabilir)")
finally:
    srv.terminate()
    with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {dbad} WITH (FORCE)")
print(f"{sum(sonuc)}/{len(sonuc)} geçti — geçici dizin: {tmp}")
sys.exit(0 if all(sonuc) else 1)
