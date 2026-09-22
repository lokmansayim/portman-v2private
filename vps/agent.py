#!/usr/bin/env python3
"""PORTMAN VPS AJANI v1.1 — hosting API'sinden (kanal/api.php) iş çeker, Beyin+Motor ile üretir, sonucu geri yollar.

Hosting kontrol düzlemidir: kuyruk, gönderim, WhatsApp anahtarı, durum dosyaları hostingte. Bu ajan yalnız dışarı bağlanır
(hosting API + OpenAI). Hiçbir WhatsApp mesajı göndermez. Paket (worker.py, beyin/, motor/ …) hostingten çekilir ve
sha256 değişince kendini günceller; ayarlar hostingten okunur (settings.worker != "vps" ise boşta bekler).

Ortam (/etc/portman/agent.env): PORTMAN_API_URL, PORTMAN_API_TOKEN, PORTMAN_HOME (/opt/portman)
Dizinler: $PORTMAN_HOME/app (paket), data (durum/, projects/, self-test), logs, pkg
"""
from __future__ import annotations
import hashlib, io, json, os, shutil, socket, sys, time, traceback, urllib.error, urllib.request, uuid, zipfile
from pathlib import Path

SURUM = "vps-agent-v1.1"
HOME = Path(os.environ.get("PORTMAN_HOME", "/opt/portman"))
API = os.environ.get("PORTMAN_API_URL", "").rstrip("?")
TOKEN = os.environ.get("PORTMAN_API_TOKEN", "")
APP, DATA, LOGS, PKG = HOME / "app", HOME / "data", HOME / "logs", HOME / "pkg"
BASLANGIC = time.time()
ONESHOT = os.environ.get("PORTMAN_AGENT_ONESHOT") == "1"     # test: tek iş (ya da paket güncellemesi) sonrası çık
_log_kuyruk: list[str] = []
_sayac = {"done": 0, "failed": 0, "errors": []}


# ───────────────────────── günlük ─────────────────────────
def log(*p) -> None:
    satir = time.strftime("%Y-%m-%d %H:%M:%S") + " " + " ".join(str(x) for x in p)
    print(satir, flush=True)
    try:
        LOGS.mkdir(parents=True, exist_ok=True)
        with (LOGS / "agent.log").open("a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except Exception:
        pass
    _log_kuyruk.append(satir)
    del _log_kuyruk[:-200]


def maske(s: str) -> str:
    return "…" + str(s)[-4:] if s else "-"


# ───────────────────────── HTTP ─────────────────────────
class ApiHatasi(Exception):
    pass


def istek(op: str, method: str = "GET", body: dict | None = None, multipart: tuple | None = None, timeout: int = 60, ham: bool = False):
    if not API or not TOKEN:
        raise ApiHatasi("PORTMAN_API_URL / PORTMAN_API_TOKEN eksik")
    url = f"{API}?op={op}"
    headers = {"X-Portman-Token": TOKEN, "User-Agent": SURUM}
    data = None
    if multipart is not None:
        ctype, data = multipart
        headers["Content-Type"] = ctype
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method if data is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if ham:
                return raw, dict(r.headers)
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        govde = e.read().decode("utf-8", "replace")[:300]
        raise ApiHatasi(f"HTTP {e.code} {op}: {govde}") from None
    except urllib.error.URLError as e:
        raise ApiHatasi(f"bağlantı {op}: {str(e.reason)[:200]}") from None


def multipart_kodla(alanlar: dict, dosyalar: list[tuple[str, str, bytes]]) -> tuple[str, bytes]:
    """alanlar: {ad: str}; dosyalar: [(alan, dosya_adı, içerik)]"""
    sinir = "----PortmanAjan" + uuid.uuid4().hex
    b = io.BytesIO()
    for ad, deger in alanlar.items():
        b.write(f"--{sinir}\r\nContent-Disposition: form-data; name=\"{ad}\"\r\n\r\n".encode()); b.write(str(deger).encode("utf-8")); b.write(b"\r\n")
    for alan, dosya_adi, icerik in dosyalar:
        b.write(f"--{sinir}\r\nContent-Disposition: form-data; name=\"{alan}\"; filename=\"{dosya_adi}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
        b.write(icerik); b.write(b"\r\n")
    b.write(f"--{sinir}--\r\n".encode())
    return f"multipart/form-data; boundary={sinir}", b.getvalue()


# ───────────────────────── paket ─────────────────────────
def yerel_paket_sha() -> str:
    p = APP / "PACKAGE_SHA256"
    return p.read_text().strip() if p.exists() else ""


def paketi_guncelle(pk: dict) -> bool:
    """Hostingteki paket sha'sı yerelden farklıysa indir, doğrula, app/ dizinini değiştir. True → yeniden başla."""
    if not pk or not pk.get("sha256"):
        return False
    if pk["sha256"] == yerel_paket_sha():
        return False
    log("paket güncelleniyor:", pk.get("surum"), pk["sha256"][:12], f"{pk.get('size', 0)} B")
    raw, hdr = istek("package", ham=True, timeout=300)
    sha = hashlib.sha256(raw).hexdigest()
    if sha != pk["sha256"]:
        raise ApiHatasi(f"paket sha uyuşmuyor: {sha[:12]} ≠ {pk['sha256'][:12]}")
    PKG.mkdir(parents=True, exist_ok=True)
    (PKG / f"{sha}.zip").write_bytes(raw)
    yeni = HOME / "app.new"
    if yeni.exists(): shutil.rmtree(yeni)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        kok = None
        adlar = z.namelist()
        if adlar and all(a.startswith(adlar[0].split("/")[0] + "/") for a in adlar if "/" in a) and not any(a in ("worker.py",) for a in adlar):
            kok = adlar[0].split("/")[0]
        for a in adlar:
            if a.endswith("/") or ".." in a or a.startswith("/"): continue
            hedef = yeni / (a[len(kok) + 1:] if kok else a)
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_bytes(z.read(a))
    if not (yeni / "worker.py").exists():
        raise ApiHatasi("pakette worker.py yok")
    (yeni / "PACKAGE_SHA256").write_text(sha)
    eski = HOME / "app.old"
    if eski.exists(): shutil.rmtree(eski)
    if APP.exists(): APP.rename(eski)
    yeni.rename(APP)
    # yeni paket → öz-test sonucunu sıfırla (worker.oz_test bir kez koşar)
    for f in ("self-test-result.json",):
        try: (DATA / f).unlink()
        except FileNotFoundError: pass
    log("paket kuruldu:", sha[:12], "→ yeniden başlatılıyor")
    return True


# ───────────────────────── iş ─────────────────────────
def worker_modulu():
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    os.environ["PORTMAN_KANAL_DIR"] = str(DATA)
    import importlib
    if "worker" in sys.modules:
        return sys.modules["worker"]
    return importlib.import_module("worker")


def yerel_ayarlar(uzak: dict) -> dict:
    """worker.isle'nin beklediği settings: LLM ayarları + anahtar (ortam değişkeni, diske yazılmaz)."""
    s = {"enabled": uzak.get("enabled"), "worker": uzak.get("worker"), "mode": uzak.get("mode"), "dry_run": uzak.get("dry_run"),
         "llm": uzak.get("llm") or {}, "patron_teknik_not": uzak.get("patron_teknik_not", True), "max_is_per_tick": 1, "budget_s": 600}
    key = uzak.get("openai_key")
    if key:
        os.environ["OPENAI_API_KEY"] = key
    return s


def isi_yap(job: dict, durum, ayar: dict) -> dict:
    w = worker_modulu()
    DATA.mkdir(parents=True, exist_ok=True); (DATA / "durum").mkdir(exist_ok=True); (DATA / "projects").mkdir(exist_ok=True)
    sender = str(job.get("sender", ""))
    if isinstance(job.get("test_cikarim"), dict):          # yalnız yerel test: PHP boş sözlüğü [] yazar
        for k in ("bina_ozellikleri",):
            if job["test_cikarim"].get(k) == []: job["test_cikarim"][k] = {}
    dp = DATA / "durum" / f"{sender}.json"
    if isinstance(durum, dict):
        w.yaz(dp, durum)                    # hosting = görüşme durumunun kaynağı
    t0 = time.time()
    try:
        cikti = w.isle(job, ayar)
    except Exception:
        hata = traceback.format_exc()[-2500:]
        cikti = {"satirlar": [w.giden_metin(job, "Mesajınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.", 1)]
                 + ([] if job.get("role") == "patron" else [w.giden_metin(job, f"Portman: {maske(sender)} mesajı işlenirken hata oluştu; vps.log'a bakın.", 2, "PATRON", "bildirim")]),
                 "sonuc": {"eylem": "hata", "gerekce": "beklenmeyen hata"}, "hata": hata}
    cikti["sonuc"]["worker"] = "vps"; cikti["sonuc"]["sure_s"] = round(time.time() - t0, 1)
    return cikti


def sonucu_gonder(job: dict, cikti: dict) -> dict:
    """Giden satırlar + belge dosyaları (projects/...) + güncel durum → hosting. Dosya yolu hostingte yeniden yazılır."""
    dosyalar = []; alanlar = {"inbound_id": job["id"]}
    for i, r in enumerate(cikti["satirlar"]):
        if r.get("kind") == "document":
            p = Path(r["file"])
            try:
                rel = p.resolve().relative_to((DATA / "projects").resolve())
            except ValueError:
                raise ApiHatasi(f"belge projects/ dışında: {p}")
            rel_s = "projects/" + rel.as_posix()
            alan = f"file_{i}"
            dosyalar.append((alan, p.name, p.read_bytes())); alanlar[f"path_{alan}"] = rel_s
            r["file"] = rel_s
    alanlar["cikti"] = json.dumps(cikti, ensure_ascii=False)
    dp = DATA / "durum" / f"{job.get('sender', '')}.json"
    if dp.exists():
        alanlar["durum"] = dp.read_text(encoding="utf-8")
    ctype, govde = multipart_kodla(alanlar, dosyalar)
    return istek("result", multipart=(ctype, govde), timeout=180)


def bekleyen_sonuclari_gonder() -> None:
    """Ağ hatasıyla gönderilemeyen sonuçlar (data/pending/*.json) yeniden denenir; üretim tekrarlanmaz."""
    pd = DATA / "pending"
    if not pd.exists(): return
    for f in sorted(pd.glob("*.json")):
        try:
            kayit = json.loads(f.read_text(encoding="utf-8"))
            r = sonucu_gonder(kayit["job"], kayit["cikti"])
            log("bekleyen sonuç gönderildi:", kayit["job"]["id"][:20], r)
            f.unlink()
        except Exception as e:
            log("bekleyen sonuç yine gönderilemedi:", f.name, str(e)[:160]); break


# ───────────────────────── sağlık ─────────────────────────
def heartbeat(pk_sha: str, son_is) -> dict:
    try:
        st = shutil.disk_usage(str(HOME)); load = os.getloadavg()
    except Exception:
        st = None; load = None
    mem_free = None
    try:
        for l in Path("/proc/meminfo").read_text().splitlines():
            if l.startswith("MemAvailable:"): mem_free = int(l.split()[1]) // 1024
    except Exception:
        pass
    st_p = DATA / "self-test-result.json"
    self_test = None
    if st_p.exists():
        try:
            j = json.loads(st_p.read_text(encoding="utf-8")); self_test = {k: j.get(k) for k in ("state", "sure_s", "finished_at")}
            self_test["adimlar"] = {k: (v.get("passed") if isinstance(v, dict) else v) for k, v in (j.get("adimlar") or {}).items()}
        except Exception:
            pass
    body = {"surum": SURUM, "python": sys.version.split()[0], "package_sha256": pk_sha, "uptime_s": int(time.time() - BASLANGIC),
            "load": [round(x, 2) for x in load] if load else None, "disk_free_mb": (st.free // 2**20) if st else None, "mem_free_mb": mem_free,
            "last_job": son_is, "jobs_done": _sayac["done"], "jobs_failed": _sayac["failed"], "self_test": self_test, "host": socket.gethostname(),
            "started_at": int(BASLANGIC), "errors": _sayac["errors"][-5:]}
    return istek("heartbeat", body=body, timeout=30)


def gunlukleri_gonder() -> None:
    if not _log_kuyruk: return
    satirlar = list(_log_kuyruk); _log_kuyruk.clear()
    try:
        istek("log", body={"lines": satirlar}, timeout=30)
    except Exception:
        _log_kuyruk[:0] = satirlar[-50:]


# ───────────────────────── ana döngü ─────────────────────────
def main() -> int:
    log("başladı", SURUM, "home", HOME, "api", API.split("?")[0] if API else "-")
    for d in (APP, DATA, LOGS, PKG, DATA / "pending"):
        d.mkdir(parents=True, exist_ok=True)
    son_ayar_t = 0.0; son_hb_t = 0.0; ayar_uzak = {}; son_is = None; poll = 4
    oz_test_yapildi = False
    while True:
        try:
            simdi = time.time()
            if simdi - son_ayar_t > 60 or not ayar_uzak:
                ayar_uzak = istek("settings", timeout=30); son_ayar_t = simdi
                poll = max(2, int(ayar_uzak.get("poll_s") or 4))
                if paketi_guncelle(ayar_uzak.get("package") or {}):
                    gunlukleri_gonder(); return 3          # systemd yeniden başlatır (Restart=always)
            if not (APP / "worker.py").exists():
                if simdi - son_hb_t > 60:
                    log("paket yok; hosting kanal/package/current.zip bekleniyor"); heartbeat("", None); son_hb_t = simdi; gunlukleri_gonder()
                time.sleep(15); continue
            ayar = yerel_ayarlar(ayar_uzak)
            if not oz_test_yapildi:
                try:
                    w = worker_modulu()
                    if w.bagimliliklar_hazir():
                        w.oz_test(ayar)
                except Exception:
                    log("öz-test hatası:", traceback.format_exc()[-600:])
                oz_test_yapildi = True
            bekleyen_sonuclari_gonder()
            if simdi - son_hb_t > 60:
                heartbeat(yerel_paket_sha(), son_is); son_hb_t = simdi; gunlukleri_gonder()
            if ayar_uzak.get("worker") != "vps" or ayar_uzak.get("enabled") is not True:
                time.sleep(poll * 3); continue
            c = istek("claim", body={}, timeout=30)
            job = c.get("job")
            if not job:
                if ONESHOT and time.time() - BASLANGIC > 90:
                    log("oneshot: iş yok"); return 4
                time.sleep(poll); continue
            log("iş alındı", job["id"][:20], "kimden", maske(job.get("sender", "")), "tür", job.get("type"))
            t0 = time.time()
            cikti = isi_yap(job, c.get("durum"), ayar)
            try:
                r = sonucu_gonder(job, cikti)
            except Exception as e:
                kayit = DATA / "pending" / f"{hashlib.sha256(job['id'].encode()).hexdigest()[:16]}.json"
                kayit.write_text(json.dumps({"job": job, "cikti": cikti}, ensure_ascii=False), encoding="utf-8")
                log("sonuç gönderilemedi (bekleyene alındı):", str(e)[:200]); r = {"pending": True}
            son_is = {"id": job["id"][:24], "eylem": cikti["sonuc"].get("eylem"), "sure_s": round(time.time() - t0, 1), "gonderim": r}
            _sayac["done" if not cikti.get("hata") else "failed"] += 1
            log("iş bitti", job["id"][:20], "→", cikti["sonuc"].get("eylem"), f"({cikti['sonuc'].get('gerekce')})", f"{son_is['sure_s']} s", "giden:", len(cikti["satirlar"]), r)
            heartbeat(yerel_paket_sha(), son_is); son_hb_t = time.time(); gunlukleri_gonder()
            if ONESHOT:
                return 0
        except ApiHatasi as e:
            log("api:", str(e)[:200]); _sayac["errors"].append(str(e)[:120]); del _sayac["errors"][:-20]
            time.sleep(15)
        except KeyboardInterrupt:
            return 0
        except Exception:
            log("beklenmeyen:", traceback.format_exc()[-800:]); _sayac["errors"].append("beklenmeyen hata"); time.sleep(15)


if __name__ == "__main__":
    sys.exit(main())
