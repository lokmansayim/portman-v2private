#!/usr/bin/env python3
"""PORTMAN VPS AJANI v1.2 — hosting API'sinden (kanal/api.php) iş çeker, Beyin+Motor ile üretir, sonucu geri yollar.

Hosting kontrol düzlemidir: kuyruk, gönderim, WhatsApp anahtarı, durum dosyaları hostingte. Bu ajan yalnız dışarı bağlanır
(hosting API + OpenAI). Hiçbir WhatsApp mesajı göndermez. Paket (worker.py, beyin/, motor/ …) hostingten çekilir ve
sha256 değişince kendini günceller; ayarlar hostingten okunur (settings.worker != "vps" ise iş almaz; kalıcı modda
"off" iken yalnız açık işleri bitirir, bkz. "kalıcı mod" bölümü). PORTMAN_PG_DSN varsa kalıcı mod (İE-02, Postgres).

Ortam (/etc/portman/agent.env): PORTMAN_API_URL, PORTMAN_API_TOKEN, PORTMAN_HOME (/opt/portman)
Dizinler: $PORTMAN_HOME/app (paket), data (durum/, projects/, self-test), logs, pkg
"""
from __future__ import annotations
import hashlib, http.client, io, json, os, shutil, socket, sys, time, traceback, urllib.error, urllib.request, uuid, zipfile
from pathlib import Path

SURUM = "vps-agent-v1.2"
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
    except (OSError, http.client.HTTPException) as e:        # cevap okunurken kopma/zaman aşımı: sonuç bilinmiyor
        raise ApiHatasi(f"bağlantı {op}: {type(e).__name__}: {str(e)[:160]}") from None


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
    # Paketteki agent.py bu dosyadan farklıysa kendini de günceller (derlenebilirlik denetimiyle; bootstrap'ı yeniden çalıştırmadan ajan düzeltmesi).
    try:
        yeni_ajan = yeni / "agent.py"; ben = Path(__file__).resolve()
        if yeni_ajan.exists() and yeni_ajan.read_bytes() != ben.read_bytes():
            import py_compile
            py_compile.compile(str(yeni_ajan), doraise=True)
            gecici = ben.with_suffix(".py.new"); gecici.write_bytes(yeni_ajan.read_bytes()); gecici.chmod(0o640); gecici.replace(ben)
            log("agent.py paketten güncellendi")
    except Exception as e:
        log("agent.py güncellenemedi (eski sürüm sürüyor):", str(e)[:160])
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
    else:
        os.environ.pop("OPENAI_API_KEY", None)     # hosting anahtar göndermeyi kestiyse eski anahtar süreçte kalmaz (denetim bulgusu F10)
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


# ───────────────────────── kalıcı mod (İE-02: Postgres) ─────────────────────────
# PORTMAN_PG_DSN tanımlıysa (/etc/portman/pg.env) konuşma ve iş durumunun asıl kaydı Postgres'tir; dosya modu (isi_yap,
# data/durum/) bu ajanda çalışmaz. Hosting WhatsApp tarafında kalır: kuyruk (claim), gönderim (tick), gönderim durumu
# (giden_durum). Tek etkin işleyici settings.worker ile seçilir:
#   "vps"     → bu ajan hosting'ten iş alır ve işler;
#   "off"     → kimse iş almaz; bu ajan yalnız Postgres'te açık kalan işleri bitirir ve sonuçlarını hosting'e verir (boşaltma,
#               geri dönüşte kapı H);
#   "hosting" → hosting'in worker.py'si işler; bu ajan hiçbir şey yapmaz (iki işleyici aynı konuşmaya yazmasın).
PG_DSN = os.environ.get("PORTMAN_PG_DSN", "")
GEREKEN_API = (1, 2)                     # kanal/api.php v1.2: giden_durum ve context_id
HOSTING_TAKILI_SN = 600                  # kanal/feature.php PM_KANAL_STALE: claim, bundan eski 'processing' satırı 'failed' yapar
KIRA_SN = 120                            # D-03: 3 deneme × 120 sn = 360 sn < 600 sn; tükenme bildirimi de hosting vazgeçmeden verilir
TESLIM_VAZGEC_SN = 900                   # geçici hatayla hosting'e verilemeyen sonuç bu kadar sürerse 'gonderilmedi' (uyarıya düşer)
KESIN_RED = ("bad_path", "file_size", "pdf_invalid", "row_inbound_mismatch")      # aynı istek her seferinde reddedilir
_kalici: dict = {"depo": None, "K": None, "son_esitleme": 0.0, "son_uyari": 0.0, "teslim_hata": {}}
_dur = {"istendi": False}


def kalici_kip(ayar_uzak: dict) -> str | None:
    """Kalıcı modda bu turun işi: "is_al" (worker=vps), "bosalt" (worker=off: iş alınmaz, açık işler biter) ya da None
    (enabled değil ya da worker=hosting: ajan hiçbir şey yapmaz)."""
    if ayar_uzak.get("enabled") is not True:
        return None
    return {"vps": "is_al", "off": "bosalt"}.get(str(ayar_uzak.get("worker")))


def _api_surumu(ayar_uzak: dict) -> tuple:
    import re
    m = re.match(r"kanal-api-v(\d+)\.(\d+)", str(ayar_uzak.get("api") or ""))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def kalici_hazir(ayar_uzak: dict) -> str | None:
    """Kalıcı mod bu turda çalışabilir mi? Çalışamıyorsa nedeni döner (ajan iş almaz, yalnız sağlık bildirir)."""
    if _api_surumu(ayar_uzak) < GEREKEN_API:
        return f"hosting API {ayar_uzak.get('api')!r}; kalıcı mod için kanal-api-v1.2 gerekli (kanal/api.php yüklenmemiş)"
    if _kalici["depo"] is None:
        worker_modulu()
        import depo as D, kalici as K     # paketle.py pakete koyar (kökte, worker.py'nin yanında)
        d = D.Depo(PG_DSN)
        eksik = d.eksik_goc()
        if eksik:
            return f"Postgres göçü uygulanmamış: {eksik} (onaylı adımda: python app/kalici.py goc)"
        n = d.olu_kiralari_birak(socket.gethostname(), K.isleyici_adi())
        if n:
            log("yeniden başlama: yarım kalan", n, "işin kirası düşürüldü; hemen yeniden alınacak (D-03)")
        _kalici.update(depo=d, K=K)
    return None


def _is_normal(job: dict) -> dict:
    if isinstance(job.get("test_cikarim"), dict):          # yalnız yerel test: PHP boş sözlüğü [] yazar
        for k in ("bina_ozellikleri",):
            if job["test_cikarim"].get(k) == []: job["test_cikarim"][k] = {}
    return job


# Hosting'ten alınıp Postgres'e yazılamayan mesaj (ör. Postgres o an yeniden başlıyor) diske yazılır ve bir sonraki turun
# başında Postgres'e alınır. Hosting'teki satır 'processing' kaldığı için kuyruktan ikinci kez gelmez; bu dosya olmasa mesaj
# 600 sn sonra hosting'te 'failed' olur ve cevapsız kalırdı.
def _bekleyen_dizini() -> Path:
    return DATA / "kalici_bekleyen"


def bekleyene_yaz(job: dict) -> Path:
    dz = _bekleyen_dizini(); dz.mkdir(parents=True, exist_ok=True)
    p = dz / f"{hashlib.sha256(job['id'].encode()).hexdigest()[:16]}.json"
    gecici = p.with_suffix(".tmp")
    gecici.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8"); os.chmod(gecici, 0o600); gecici.replace(p)
    return p


def mesaji_al(d, job: dict) -> None:
    if d.mesaj_kaydet(job):
        log("iş alındı → Postgres", job["id"][:20], "kimden", maske(job.get("sender", "")), "tür", job.get("type"))
    else:
        tekrar_gelen(d, job)


def bekleyenleri_al(d) -> int:
    dz = _bekleyen_dizini()
    if not dz.exists():
        return 0
    n = 0
    for f in sorted(dz.glob("*.json"), key=lambda x: x.stat().st_mtime):
        mesaji_al(d, json.loads(f.read_text(encoding="utf-8")))       # Postgres yine yoksa hata yükselir, dosya kalır
        f.unlink(); n += 1
    return n


def tekrar_gelen(d, job: dict) -> None:
    """Hosting aynı kanal mesajını yeniden verdi (Postgres'te zaten var): ikinci iş açılmaz.
    - İlk iş sürüyor: hosting'teki satırı ilk işin sonucu kapatır.
    - İlk iş bitmiş, satırlarının bir kısmı hosting'e hiç verilememiş (ör. hosting satırı 'takılı' sayıp reddetmişti) ya da
      hâlâ bekliyor: o satırlar bu yeni alımla hosting'e verilir; bayi cevabını alır. Gönderim tekrarı değildir: hosting'e bir
      kez verilmiş satır yeniden verilmez.
    - İlk işin satırları zaten hosting'te: hosting'teki satır boş bir sonuçla kapanır."""
    m = d.mesaj_durumu(job["id"])
    if m and m["is_durum"] in ("bitti", "basarisiz"):
        yeniden = d.hostinge_yeniden_dene(m["is_id"])
        if yeniden or m["bekleyen_giden"]:
            log("tekrar gelen mesaj", job["id"][:20], ": ikinci iş açılmadı; ilk işin (", m["is_id"], ") hosting'e verilmemiş",
                yeniden + m["bekleyen_giden"], "satırı bu alımla veriliyor")
            return
        cikti = {"satirlar": [], "sonuc": {"eylem": "yoksay", "gerekce": "tekrar gelen mesaj: Postgres'te zaten işlendi", "worker": "vps"}}
        istek("result", multipart=multipart_kodla({"inbound_id": job["id"], "cikti": json.dumps(cikti, ensure_ascii=False)}, []), timeout=60)
        log("tekrar gelen mesaj", job["id"][:20], ": ikinci iş açılmadı (ilk iş", m["is_id"], m["is_durum"] + ")")
    else:
        log("tekrar gelen mesaj", job["id"][:20], ": ilk iş sürüyor; ikinci iş açılmadı")


def _hata_sinifi(m: str) -> str:
    """Hosting'in result hatası: 'mutabakat' (gelen satırı orada artık işlenmekte değil: satırlar oraya ulaşmış mı bakılır),
    'kesin' (aynı istek her seferinde reddedilir) ya da 'gecici' (ağ, 5xx, 401/403 ör. anahtar yenilenirken, 429, dosya ya
    da kilit hatası; api.php her PHP istisnasını 422 döner, bu yüzden 422'nin yalnız bilinen kesin nedenleri kesindir)."""
    if m.startswith("HTTP 422") and ("inbound_not_claimed_by_vps" in m or "inbound_unknown" in m):
        return "mutabakat"
    if m.startswith("HTTP 413") or (m.startswith("HTTP 422") and any(k in m for k in KESIN_RED)):
        return "kesin"
    return "gecici"


def hostinge_teslim(d) -> int:
    """Bitmiş (ya da başarısız) işlerin giden satırlarını hosting'e verir (result). Hosting satırları kimliğe göre
    tekilleştirir, bu yüzden cevabı kaybolan çağrı güvenle yeniden denenir: hosting "işlenmekte değil" derse giden_durum ile
    satırların orada olup olmadığına bakılır. Geçici hata yeniden denenir; TESLIM_VAZGEC_SN boyunca sürerse satırlar
    'gonderilmedi' olur. Bu bir WhatsApp gönderimi değildir; gönderimi hosting yapar, sonucu belirsizse tekrar etmez.
    Dönen: hosting'e verilen iş sayısı."""
    n = 0; hatalar = _kalici["teslim_hata"]
    for is_id in d.teslim_bekleyen_isler():
        pk = d.teslim_paketi(is_id)
        dosyalar, alanlar, gidecek, bozuk = [], {"inbound_id": pk["inbound_id"]}, [], []
        for i, s in enumerate(pk["cikti"]["satirlar"]):
            s = dict(s)
            if s.get("kind") == "document":
                p = Path(s.get("file") or "")
                try:
                    veri = p.read_bytes()
                    rel = "projects/" + p.resolve().relative_to((DATA / "projects").resolve()).as_posix()
                    saglam = hashlib.sha256(veri).hexdigest() == s.get("sha256")
                except (OSError, ValueError):
                    saglam = False
                if not saglam:
                    bozuk.append(s["id"]); continue
                alan = f"file_{i}"
                dosyalar.append((alan, p.name, veri)); alanlar[f"path_{alan}"] = rel; s["file"] = rel
            gidecek.append(s)
        if bozuk:
            d.hostinge_verilemedi(bozuk, "PDF dosyası yok ya da kayıttan sonra değişmiş; hosting'e verilmedi")
            log("PDF kayıtla uyuşmuyor, hosting'e verilmedi: iş", is_id)
        ids = [s["id"] for s in gidecek]
        alanlar["cikti"] = json.dumps({**pk["cikti"], "satirlar": gidecek}, ensure_ascii=False)
        if pk["durum"] is not None:
            alanlar["durum"] = json.dumps(pk["durum"], ensure_ascii=False)       # hosting'teki durum/ aynası (panel, geri dönüş)
        try:
            istek("result", multipart=multipart_kodla(alanlar, dosyalar), timeout=180)
            d.hostinge_verildi(ids); hatalar.pop(is_id, None); n += 1
        except ApiHatasi as e:
            m = str(e); sinif = _hata_sinifi(m)
            if sinif == "mutabakat":
                orada = set(istek("giden_durum", body={"ids": ids}, timeout=30).get("satirlar") or {})
                d.hostinge_verildi([i for i in ids if i in orada])
                yok = [i for i in ids if i not in orada]
                if yok:
                    d.hostinge_verilemedi(yok, f"hosting kabul etmedi: {m[:160]}")
                    log("hosting sonucu kabul etmedi:", pk["inbound_id"][:20], m[:120])
                hatalar.pop(is_id, None)
            elif sinif == "kesin":
                d.hostinge_verilemedi(ids, f"hosting reddetti: {m[:160]}"); hatalar.pop(is_id, None)
                log("hosting sonucu reddetti (kesin):", m[:160])
            else:
                ilk = hatalar.setdefault(is_id, time.time())
                if time.time() - ilk >= TESLIM_VAZGEC_SN:
                    d.hostinge_verilemedi(ids, f"hosting'e {TESLIM_VAZGEC_SN // 60} dakika boyunca verilemedi: {m[:140]}"); hatalar.pop(is_id, None)
                    log("hosting'e verilemedi, vazgeçildi: iş", is_id, m[:120])
                else:
                    log("hosting'e teslim ertelendi (yeniden denenecek):", m[:160]); break
    return n


def durum_esitle(d) -> int:
    """Hosting'teki gönderim ve teslim durumunu Postgres'e işler: API kabulü (kabul_edildi, wamid, kabul zamanı) ve Meta'nın
    bildirimleri (ilk 'sent' anı; delivered/read/failed) ayrı alanlardır."""
    ids = d.esitlenecek_satirlar()
    if not ids:
        return 0
    satirlar = istek("giden_durum", body={"ids": ids}, timeout=30).get("satirlar") or {}
    for i, st in satirlar.items():
        d.hosting_durumu_isle(i, st)
    return len(satirlar)


def kalici_tur(ayar: dict, is_al: bool = True) -> bool:
    """Kalıcı modda bir tur. Sıra önemlidir:
      1. Postgres'e bağlanılamıyorsa tur burada biter: hosting'ten mesaj alınmaz (alınıp yazılamazsa kaybolurdu).
      2. Önceki turda alınıp Postgres'e yazılamamış mesajlar yazılır.
      3. Bitmiş işlerin sonuçları hosting'e verilir. claim'den ÖNCE: claim hosting'te 600 sn'yi aşan 'processing' satırları
         'failed' yapar; uzun bir hosting/ağ kesintisinden sonra bekleyen cevaplar böylece reddedilmeden verilir.
      4. is_al ise (worker=vps) hosting'ten bir mesaj alınır ve Postgres'e yazılır; boşaltmada (worker=off) alınmaz.
      5. Açık iş varsa gönderim/teslim durumu eşitlenir (onay denetimi hosting'in son bildiğini görsün), bir iş işlenir.
      6. Sonuç hosting'e verilir; durum dönemsel olarak eşitlenir.
    Bir şey yapıldıysa True."""
    d, K = _kalici["depo"], _kalici["K"]
    d.saglik()
    yapildi = bool(bekleyenleri_al(d))
    if hostinge_teslim(d):
        yapildi = True
    if is_al:
        job = istek("claim", body={}, timeout=30).get("job")
        if job:
            job = _is_normal(job)
            try:
                mesaji_al(d, job)
            except ApiHatasi:
                raise                             # tekrar gelen mesajın kapanışı gönderilemedi; mesaj Postgres'te
            except Exception:
                p = bekleyene_yaz(job)
                log("mesaj Postgres'e yazılamadı; diske alındı, sonraki turda yazılacak:", job["id"][:20], p.name)
                raise
            yapildi = True
    if d.acik_is_sayisi():
        # İşlemeden önce gönderim/teslim durumu tazelenir: bayi PDF'i görüp hemen "onaylıyorum" yazdıysa onay denetimi
        # hosting'in son bildiğini (API kabulü, Meta bildirimleri) görmeli; yoksa ulaşmış plan "ulaşmadı" sayılırdı.
        durum_esitle(d); _kalici["son_esitleme"] = time.time()
    r = K.bir_is(d, {**ayar, "kira_sn": KIRA_SN, "en_cok_deneme": 3}, K.isleyici_adi())
    if r is not None:
        yapildi = True
        _sayac["done" if r.get("durum") == "bitti" else "failed"] += r.get("durum") in ("bitti", "basarisiz")
        log("iş", r.get("is_id"), r.get("durum"), "→", r.get("eylem"), "giden:", r.get("giden"))
    if hostinge_teslim(d):
        yapildi = True
    if yapildi or time.time() - _kalici["son_esitleme"] > 15:
        if durum_esitle(d):
            yapildi = True
        _kalici["son_esitleme"] = time.time()
    return yapildi


def kalici_uyarilari() -> list[str]:
    """Sağlık bildirimine (vps-health.json 'errors') eklenen uyarılar: bayiye ya da Patron'a ulaşmadığı bilinen ya da sonucu
    belirsiz giden satırlar, diskte bekleyen mesajlar. Ayrıntı: kanit_sorgulari.sql 6."""
    d = _kalici["depo"]
    if d is None:
        return []
    u = []
    try:
        say = d.gonderilemeyen_sayisi(24)
        if say["gonderilmedi"] or say["belirsiz"]:
            u.append(f"kalıcı: son 24 saatte {say['gonderilmedi']} giden satır gönderilmedi, {say['belirsiz']} satırın sonucu belirsiz")
    except Exception as e:
        u.append(f"kalıcı: Postgres okunamadı ({type(e).__name__})")
    dz = _bekleyen_dizini()
    if dz.exists() and any(dz.glob("*.json")):
        u.append(f"kalıcı: {len(list(dz.glob('*.json')))} mesaj Postgres'e yazılmayı bekliyor (diskte)")
    return u


# ───────────────────────── komut kanalı (isteğe bağlı) ─────────────────────────
def komut_calistir() -> bool:
    """settings.vps_komut açıkken hostingteki komutlar/<id>.json'u portman kullanıcısı olarak çalıştırır; sonucu geri yollar."""
    import subprocess
    c = istek("komut_al", body={}, timeout=30)
    k = c.get("komut")
    if not k:
        return False
    log("komut alındı:", k["id"], repr(k["komut"][:120]))
    t0 = time.time()
    try:
        r = subprocess.run(["/bin/bash", "-lc", k["komut"]], capture_output=True, text=True, timeout=min(int(k.get("timeout_s") or 600), 1800),
                           cwd=k.get("cwd") or str(HOME), env={**os.environ, "PORTMAN_HOME": str(HOME)})
        sonuc = {"id": k["id"], "exit": r.returncode, "stdout": r.stdout[-200000:], "stderr": r.stderr[-50000:], "sure_s": round(time.time() - t0, 1)}
    except subprocess.TimeoutExpired as e:
        sonuc = {"id": k["id"], "exit": -1, "stdout": (e.stdout or "")[-200000:] if isinstance(e.stdout, str) else "", "stderr": "zaman aşımı", "sure_s": round(time.time() - t0, 1)}
    except Exception as e:
        sonuc = {"id": k["id"], "exit": -2, "stdout": "", "stderr": str(e)[:2000], "sure_s": round(time.time() - t0, 1)}
    istek("komut_sonuc", body=sonuc, timeout=60)
    log("komut bitti:", k["id"], "exit", sonuc["exit"], f"{sonuc['sure_s']} s")
    return True


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
    body = {"surum": SURUM + (" kalici" if PG_DSN else ""), "python": sys.version.split()[0], "package_sha256": pk_sha, "uptime_s": int(time.time() - BASLANGIC),
            "load": [round(x, 2) for x in load] if load else None, "disk_free_mb": (st.free // 2**20) if st else None, "mem_free_mb": mem_free,
            "last_job": son_is, "jobs_done": _sayac["done"], "jobs_failed": _sayac["failed"], "self_test": self_test, "host": socket.gethostname(),
            "started_at": int(BASLANGIC), "errors": _sayac["errors"][-5:] + kalici_uyarilari()}
    return istek("heartbeat", body=body, timeout=30)


_log_hata = {"ardisik": 0}


def gunlukleri_gonder() -> None:
    """Birikmiş günlük satırlarını hostinge yazar. Yanıtın ok/n alanı denetlenir; kabul edilmeyen satırlar kuyruğa geri konur ve hata
    genel hata sayacına düşer (denetim bulgusu F06: önceki sürüm yanıtı denetlemiyor, hatayı sayaca yazmıyordu)."""
    if not _log_kuyruk: return
    satirlar = list(_log_kuyruk); _log_kuyruk.clear()
    try:
        r = istek("log", body={"lines": satirlar}, timeout=30)
        n = int(r.get("n") or 0) if isinstance(r, dict) else 0
        if not (isinstance(r, dict) and r.get("ok") is True and n == min(len(satirlar), 200)):
            raise ApiHatasi(f"log kabul edilmedi: yanıt={str(r)[:120]} gönderilen={len(satirlar)}")
        if len(satirlar) > 200:
            _log_kuyruk[:0] = satirlar[200:]
        _log_hata["ardisik"] = 0
    except Exception as e:
        _log_hata["ardisik"] += 1
        _sayac["errors"].append(f"log: {str(e)[:100]} (ardışık {_log_hata['ardisik']})"); del _sayac["errors"][:-20]
        _log_kuyruk[:0] = satirlar[-50:]


# ───────────────────────── ana döngü ─────────────────────────
def main() -> int:
    log("başladı", SURUM, "home", HOME, "api", API.split("?")[0] if API else "-", "mod", "kalıcı (Postgres)" if PG_DSN else "dosya")
    import signal
    # SIGTERM (systemctl restart/stop): elindeki adımı bitirir, sonra çıkar. Kalıcı modda yarıda kalan iş de kaybolmaz:
    # yeniden başlayan ajan ölü sürecin kirasını düşürür (olu_kiralari_birak).
    signal.signal(signal.SIGTERM, lambda *_: _dur.__setitem__("istendi", True))
    for d in (APP, DATA, LOGS, PKG, DATA / "pending"):
        d.mkdir(parents=True, exist_ok=True)
    son_ayar_t = 0.0; son_hb_t = 0.0; ayar_uzak = {}; son_is = None; poll = 4
    oz_test_yapildi = False
    while not _dur["istendi"]:
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
            if ayar_uzak.get("vps_komut") is True:
                try:
                    while komut_calistir():
                        gunlukleri_gonder()
                except ApiHatasi as e:
                    log("komut kanalı:", str(e)[:160])
            if simdi - son_hb_t > 60:
                heartbeat(yerel_paket_sha(), son_is); son_hb_t = simdi; gunlukleri_gonder()
            isci = ayar_uzak.get("worker")
            if PG_DSN:                                    # kalıcı mod: dosya modu bu ajanda çalışmaz
                kip = kalici_kip(ayar_uzak)
                if kip is None:
                    time.sleep(poll * 3); continue        # kapalı ya da hosting işliyor: tek etkin işleyici
                neden = kalici_hazir(ayar_uzak)
                if neden:
                    if time.time() - _kalici["son_uyari"] > 300:
                        log("kalıcı mod bekliyor:", neden); _kalici["son_uyari"] = time.time(); gunlukleri_gonder()
                    time.sleep(poll * 3); continue
                # worker=off: iş alınmaz; Postgres'te açık kalan işler biter ve sonuçları hosting'e verilir (boşaltma)
                if kalici_tur(ayar, is_al=(kip == "is_al")):
                    heartbeat(yerel_paket_sha(), {"mod": "kalici", "at": int(time.time())}); son_hb_t = time.time(); gunlukleri_gonder()
                    if ONESHOT and not _kalici["depo"].teslim_bekleyen_isler() and _kalici["depo"].acik_is_sayisi() == 0:
                        return 0
                else:
                    if ONESHOT and time.time() - BASLANGIC > 90:
                        log("oneshot: iş yok"); return 4
                    time.sleep(poll if kip == "is_al" else poll * 3)
                continue
            if isci != "vps" or ayar_uzak.get("enabled") is not True:
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
        except Exception as e:
            if type(e).__module__.startswith("psycopg"):      # Postgres kapalı/yeniden başlıyor: iş alınmadı; tur yeniden denenir
                if time.time() - _kalici["son_uyari"] > 300:
                    log("Postgres'e ulaşılamadı; hosting'ten iş alınmıyor:", type(e).__name__, str(e)[:120]); _kalici["son_uyari"] = time.time()
                _sayac["errors"].append(f"postgres: {type(e).__name__}"); del _sayac["errors"][:-20]; time.sleep(15); continue
            log("beklenmeyen:", traceback.format_exc()[-800:]); _sayac["errors"].append("beklenmeyen hata"); time.sleep(15)
    log("durduruldu (SIGTERM): eldeki adım bitti"); gunlukleri_gonder()
    return 0


if __name__ == "__main__":
    sys.exit(main())
