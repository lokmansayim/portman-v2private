"""İE-02 · uçtan uca YEREL test, kalıcı mod: GERÇEK PHP hattı (feature.php + api.php + portman/lib.php, php -S) → VPS ajanı
(vps/agent.py, PORTMAN_PG_DSN ile) → Postgres → PHP tick (sahte Meta) → imzalı durum bildirimi → ajan eşitler.
Meta ve OpenAI yok (manuel çıkarım); canlı hiçbir şeye dokunmaz. Sahte gönderici testlerinin sınamadığı gerçek PHP hattını
sınar; gerçek WhatsApp ve gerçek LLM'i sınamaz (onlar canlı Patron denemesinde).

Çalıştırma: PORTMAN_TEST_PG="host=… user=…" python3 kanal/tests/e2e_kalici.py <portman/lib.php yolu>
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

tmp = Path(tempfile.mkdtemp(prefix="pm_kalici_e2e_"))
kopya = tmp / "kanal"
shutil.copytree(KANAL, kopya, ignore=shutil.ignore_patterns("__pycache__", "state.json", "state.lock", "worker.lock", "tick.lock", "projects", "durum",
                                                            "checks", "*.log", "self-test-result.json", "package", "api_token.txt"))
(kopya / "self-test-request.json").unlink(missing_ok=True)
for d in ("beyin", "motor", "is_emri"):
    if (kopya / d).exists(): shutil.rmtree(kopya / d)
    shutil.copytree(ROOT / d, kopya / d, ignore=shutil.ignore_patterns("__pycache__", "durum"))
s = json.loads((KANAL / "settings.example.json").read_text(encoding="utf-8"))
s.setdefault("llm", {}); s["llm"].update(backend="manuel", model="test", timeout_s=5)
s.update(enabled=True, enabled_at=int(time.time()) - 3600, dry_run=False, mode="patron", worker="vps", vps_poll_s=1, ayarlar_json="/yok/ayarlar.json")
(kopya / "settings.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
TOKEN = hashlib.sha256(os.urandom(16)).hexdigest()
(kopya / "api_token.txt").write_text(TOKEN + "\n")
# paket: vps/paketle.py ile aynı düzen (kalıcı mod dosyaları dahil)
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
    z.write(ROOT / "vps" / "agent.py", "agent.py"); z.writestr("SURUM.txt", "test-kalici\n")
raw = buf.getvalue(); PAKET_SHA = hashlib.sha256(raw).hexdigest()
(kopya / "package" / "current.zip").write_bytes(raw); (kopya / "package" / "current.sha256").write_text(PAKET_SHA + "\n")
www = tmp / "www"; www.mkdir(); shutil.copy(kopya / "tests" / "api_endpoint_test.php", www / "kanal_api.php")
env = {**os.environ, "PM_TEST_TMP": str(tmp), "PM_TEST_LIB": lib}
php_steps = ["php", str(kopya / "tests" / "e2e_steps.php")]
dbad = "e2e_" + uuid.uuid4().hex[:8]
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


port = 8599 + (os.getpid() % 300)
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
    print("1) PHP yakalama → hosting kuyruğu; ajan (kalıcı mod) paketi kurar")
    run(php_steps + ["init", str(tmp), lib])
    run(php_steps + ["capture", str(tmp), lib, "P6001 aynalı", "wamid.K1"])
    hazir_ekle("wamid.K1", {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "P6001 aynalı", "katalog_kodu": "P6001",
                            "varyantlar": [{"tur": "ayna_x", "aciklama": "aynalı"}]})
    ok(ajan((3,)) == 3 and (vhome / "app" / "depo.py").exists() and (vhome / "app" / "goc" / "002_gonderim_kabul_teslim.sql").exists(),
       "ilk çalıştırma: paket (kalıcı mod dosyalarıyla) kuruldu")

    print("2) ajan: claim → Postgres → Beyin+Motor → result (gerçek api.php)")
    ok(ajan() == 0, "ikinci çalıştırma: iş işlendi ve hosting'e verildi")
    st = state(); gin = st["inbound"]["wamid.K1"]
    ok(gin["state"] == "done" and gin["result"]["eylem"] == "is_emri", "hosting kuyruğu: done, is_emri")
    ok([r["durum"] for r in q("SELECT durum FROM isler")] == ["bitti"] and {r["durum"] for r in q("SELECT durum FROM giden")} == {"hostingte"},
       "Postgres: iş bitti, giden satırlar hosting'te")
    ok((kopya / "durum" / f"{gin['sender']}.json").exists(), "hosting'teki durum/ aynası güncellendi")

    print("3) PHP tick (sahte Meta) → API kabul; imzalı 'delivered' bildirimi → ajan eşitler")
    run(php_steps + ["tick", str(tmp), lib])
    o = state()["outbound"]; belge = next(r for r in o.values() if r["kind"] == "document")
    ok(all(r["state"] == "accepted" for r in o.values()), "hosting: satırlar API tarafından kabul edildi")
    teslim_ts = int(time.time()) - 1
    run(php_steps + ["status", str(tmp), lib, belge["wamid"], "delivered", str(teslim_ts)])
    ok(ajan((0, 4)) in (0, 4), "ajan eşitleme turu")
    g = q("SELECT durum, dis_id, teslim_durumu, extract(epoch FROM teslim_zamani)::bigint AS t FROM giden WHERE kind = 'document'")[0]
    ok((g["durum"], g["dis_id"], g["teslim_durumu"], g["t"]) == ("kabul_edildi", belge["wamid"], "delivered", teslim_ts),
       "Postgres: PDF satırı API kabulü + Meta teslimi (ayrı alanlar)")

    print("4) güncel revizyonu alıntılayan onay (context_id) → kabul, zincir")
    time.sleep(1.2)
    run(php_steps + ["capture", str(tmp), lib, "onaylıyorum", "wamid.K2", belge["wamid"]])
    hazir_ekle("wamid.K2", {"niyet": "onay", "guven": "yuksek", "ozet": "onay"})
    ok(state()["inbound"]["wamid.K2"].get("context_id") == belge["wamid"], "PHP: context_id kuyruk satırında")
    ok(ajan() == 0, "ajan: onay işlendi")
    z = q("SELECT * FROM onay_zinciri")[0]
    ok((z["revizyon_durumu"], z["pdf_wamid"], z["onay_alintisi"]) == ("onaylandi", belge["wamid"], belge["wamid"]), "onay zinciri: revizyon onaylandı, alıntı = PDF")

    print("5) aynı kanal mesajı yeniden kuyrukta → ikinci iş yok")
    run(php_steps + ["requeue", str(tmp), lib, "wamid.K1"])
    ok(ajan((0, 4)) in (0, 4), "ajan turu")
    ok(q("SELECT count(*) n FROM isler")[0]["n"] == 2 and state()["inbound"]["wamid.K1"]["result"]["eylem"] == "yoksay",
       "Postgres'te iş sayısı değişmedi; hosting satırı 'yoksay' ile kapandı")
    ok(len(state()["outbound"]) == 3, "hosting'te yeni giden satır yok")

    print("6) süpürmeyi yalnız claim yapar: 600 sn'yi aşmış satıra, claim'den önce verilen sonuç kabul edilir (ajanın tur sırası)")
    sys.path.insert(0, str(ROOT / "vps"))
    import agent as AJ  # noqa: E402  (yalnız çok parçalı gövde kodlayıcısı için)
    import urllib.request, urllib.error  # noqa: E402

    def api(op, body=None, alanlar=None):
        url = f"http://127.0.0.1:{port}/kanal_api.php?op={op}"; h = {"X-Portman-Token": TOKEN}
        if alanlar is not None:
            ctype, veri = AJ.multipart_kodla(alanlar, []); h["Content-Type"] = ctype
        else:
            veri = json.dumps(body or {}).encode(); h["Content-Type"] = "application/json"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=veri, headers=h, method="POST"), timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def eskit(mid, sn=700):
        st = state(); st["inbound"][mid]["updated_at"] -= sn
        (kopya / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")

    def sonuc_govdesi(mid):
        satir = {"id": "out_" + uuid.uuid4().hex[:24], "kind": "text", "to": state()["inbound"][mid]["sender"], "body": "x", "tur": "cevap",
                 "inbound_id": mid, "seq": 1, "state": "pending", "wamid": None, "attempts": 0, "error": None}
        return {"inbound_id": mid, "cikti": json.dumps({"satirlar": [satir], "sonuc": {"eylem": "cevapla"}})}
    run(php_steps + ["capture", str(tmp), lib, "kesinti öncesi", "wamid.K3"])
    kod, c = api("claim")
    ok(kod == 200 and (c.get("job") or {}).get("id") == "wamid.K3", "claim: K3 işleniyor")
    eskit("wamid.K3")                                            # uzun kesinti: hosting'te 600 sn'yi aştı, arada claim yok
    kod, c = api("result", alanlar=sonuc_govdesi("wamid.K3"))
    ok(kod == 200 and state()["inbound"]["wamid.K3"]["state"] == "done", "result claim'den önce: kabul edildi (done)")
    run(php_steps + ["capture", str(tmp), lib, "süpürülecek", "wamid.K4"])
    api("claim"); eskit("wamid.K4")
    run(php_steps + ["capture", str(tmp), lib, "sonraki", "wamid.K5"])
    kod, c = api("claim")                                       # claim süpürür
    ok(state()["inbound"]["wamid.K4"]["state"] == "failed", "claim 600 sn'yi aşan satırı 'failed' yapar")
    kod, c = api("result", alanlar=sonuc_govdesi("wamid.K4"))
    ok(kod == 422 and "inbound_not_claimed_by_vps" in (c.get("error") or ""), "süpürülen satıra sonuç: 422 inbound_not_claimed_by_vps")
finally:
    srv.terminate()
    with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
        c.execute(f"DROP DATABASE IF EXISTS {dbad} WITH (FORCE)")
print(f"\n{sum(sonuc)}/{len(sonuc)} geçti — geçici dizin: {tmp}")
sys.exit(0 if all(sonuc) else 1)
