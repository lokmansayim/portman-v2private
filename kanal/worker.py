"""PORTMAN KANAL v1 — Python üretici (hosting cron'u, dakikada bir; task2/venv Python'u ile).

Kuyruktaki gelen WhatsApp mesajı (state.json → inbound, PHP webhook yazar)
  → Beyin: LLM çıkarım (yalnız "bayi ne dedi?") + deterministik kural katmanı
  → giden METİN satırı (state.json → outbound; PHP tick gönderir)
  → İş Emri çıktıysa Motor (DXF → yeniden aç → doğrula → PDF) → giden BELGE satırı
  → yönlendirme / hata → Patron'a bildirim satırı.

Bu dosya WhatsApp'a, OpenAI dışında hiçbir yere bağlanmaz ve HİÇBİR ŞEY GÖNDERMEZ. Gönderim yalnız feature.php::pm_kanal_tick.
Kurulum öz-testi (self-test-request.json) state.json'a dokunmaz; çıktıları checks/ altına yazar.
"""
from __future__ import annotations
import fcntl, hashlib, importlib, json, os, subprocess, sys, time, traceback, warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

KOD = Path(__file__).resolve().parent                                   # kod (beyin/, motor/, is_emri/ …)
KANAL = Path(os.environ.get("PORTMAN_KANAL_DIR") or KOD).resolve()     # veri (settings/state/durum/projects); hostingte kodla aynı dizin
sys.path.insert(0, str(KOD))
os.umask(0o077)
SURUM = "kanal-v1.1.1"
STALE_S = 600           # 'processing' bu kadar süre ilerlemezse başarısız sayılır (otomatik tekrar yok)
GELEN_YAZILI = ("text", "button", "interactive")


# ───────────────────────── dosya yardımcıları ─────────────────────────
def oku(p: Path, varsayilan=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return varsayilan


def yaz(p: Path, veri) -> None:
    tmp = p.with_name(p.name + "." + hashlib.sha256(os.urandom(8)).hexdigest()[:8] + ".tmp")
    tmp.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def ayarlar() -> dict:
    return oku(KANAL / "settings.json", {}) or {}


def state_change(fn):
    """state.json'u PHP ile paylaşılan state.lock altında değiştir (flock; PHP tarafı aynı dosyayı kilitler)."""
    with (KANAL / "state.lock").open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            p = KANAL / "state.json"
            state = _normal(oku(p))
            sonuc = fn(state)
            yaz(p, state)
            return sonuc
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _normal(state) -> dict:
    """PHP boş diziyi [] yazar; Python tarafında sözlük bekleriz."""
    if not isinstance(state, dict):
        state = {}
    state.setdefault("version", 1)
    for k in ("inbound", "outbound"):
        if not isinstance(state.get(k), dict):
            state[k] = {}
    return state


def log(*parca) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *parca, flush=True)


def maske(numara: str) -> str:
    return "…" + str(numara)[-4:] if numara else "-"


# ───────────────────────── bağımlılıklar ─────────────────────────
GEREKLI = {"shapely": "shapely", "pydantic": "pydantic", "ezdxf": "ezdxf", "fitz": "pymupdf", "numpy": "numpy"}


def bagimliliklar_hazir() -> bool:
    """Eksik paket varsa venv pip'iyle bir kez kurmayı dener (install-report.json); bu tikte üretim yapmaz."""
    eksik = []
    for mod in GEREKLI:
        try:
            importlib.import_module(mod)
        except Exception:
            eksik.append(mod)
    if not eksik:
        return True
    rapor_p = KANAL / "install-report.json"
    rapor = oku(rapor_p, {}) or {}
    if rapor.get("attempts", 0) >= 3:
        log("bağımlılık eksik, kurulum 3 kez denendi; elle müdahale gerekli:", eksik)
        return False
    paketler = [GEREKLI[m] for m in eksik]
    log("eksik paket kuruluyor:", paketler)
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", *paketler],
                           capture_output=True, text=True, timeout=900)
        sonuc = {"returncode": r.returncode, "stdout": r.stdout[-3000:], "stderr": r.stderr[-3000:]}
    except Exception as e:
        sonuc = {"returncode": -1, "stdout": "", "stderr": str(e)[:500]}
    rapor = {"attempts": rapor.get("attempts", 0) + 1, "at": int(time.time()), "python": sys.executable, "packages": paketler, **sonuc}
    yaz(rapor_p, rapor)
    return False


# ───────────────────────── sağlık ─────────────────────────
def saglik(ek: dict | None = None) -> None:
    st = _normal(oku(KANAL / "state.json", {}))
    sayim = {}
    for r in (st.get("inbound") or {}).values():
        sayim[r.get("state", "?")] = sayim.get(r.get("state", "?"), 0) + 1
    cikis = {}
    for r in (st.get("outbound") or {}).values():
        cikis[r.get("state", "?")] = cikis.get(r.get("state", "?"), 0) + 1
    yaz(KANAL / "worker-health.json", {"checked_at": int(time.time()), "surum": SURUM, "python": sys.version.split()[0],
                                       "enabled": ayarlar().get("enabled") is True, "inbound": sayim, "outbound": cikis, **(ek or {})})


# ───────────────────────── öz-test ─────────────────────────
def oz_test(settings: dict) -> None:
    """self-test-request.json varsa ve sonucu yoksa bir kez koşar. state.json'a dokunmaz, hiçbir şey göndermez."""
    istek_p = KANAL / "self-test-request.json"
    if not istek_p.exists():
        istek_p = KOD / "self-test-request.json"     # VPS: istek paketle gelir, sonuç veri dizinine yazılır
    sonuc_p = KANAL / "self-test-result.json"
    if not istek_p.exists() or sonuc_p.exists():
        return
    istek = oku(istek_p, {}) or {}
    baslangic = time.time()
    sonuc = {"state": "running", "started_at": int(baslangic), "surum": SURUM, "python": sys.version.split()[0], "adimlar": {}}
    yaz(sonuc_p, sonuc)
    kok = KANAL / "checks" / "selftest"
    kok.mkdir(parents=True, exist_ok=True)
    try:
        import ezdxf, shapely, pydantic, fitz  # noqa
        sonuc["adimlar"]["surumler"] = {"ezdxf": ezdxf.__version__, "shapely": shapely.__version__, "pydantic": pydantic.VERSION,
                                       "pymupdf": getattr(fitz, "VersionBind", getattr(fitz, "version", ("?",))[0])}
        # 1) Beyin kural katmanı: 15 mesajlık koşum (LLM yok; hazır çıkarımlar)
        from beyin import harness
        ok, toplam = harness.main(durum_dir=kok / "durum", sessiz=True, rapor_yaz=False)
        sonuc["adimlar"]["beyin_harness"] = {"uyumlu": ok, "toplam": toplam, "passed": ok == toplam}
        # 2) Manuel çıkarım → kural → İş Emri → Motor (çizim + doğrulama), PDF checks/ altında kalır
        from beyin import llm, katalog as KT
        from beyin.konusma import Konusma
        from beyin.karar import karar_ver
        from motor import dxf_out
        talep, _ = llm.cikar_detayli(istek["mesaj"], backend="manuel", hazir=istek["hazir_cikarim"])
        k = Konusma("SELFTEST", kok / "durum")
        bayi = {"kod": "TEST", "ad": "Öz-test", "firma": "PortatifEv", "rol": "patron"}
        karar = karar_ver(talep, k, bayi, KT.Katalog(), metin=istek["mesaj"])
        sonuc["adimlar"]["karar"] = {"eylem": karar.eylem, "gerekce": karar.gerekce, "passed": karar.eylem == "is_emri"}
        if karar.eylem == "is_emri":
            t0 = time.time()
            m = dxf_out.uret(karar.is_emri, kok / "cizim")
            v = oku(kok / "cizim" / "validation.json", {}) or {}
            sonuc["adimlar"]["motor"] = {"sure_s": round(time.time() - t0, 1), "pdf": m.get("pdf"), "pdf_sha256": m.get("pdf_sha256"),
                                        "dxf_sha256": m.get("dxf_sha256"), "validation_passed": v.get("passed"),
                                        "errors": (v.get("errors") or [])[:5], "passed": v.get("passed") is True}
        # 3) LLM yolu (isteğe bağlı; anahtar sunucudaki ayar dosyasından, hiçbir yere yazılmaz)
        if istek.get("llm_dene") and settings.get("llm", {}).get("backend", "openai_chat") != "manuel":
            try:
                llm.anahtar_bul(settings["llm"].get("backend", "openai_chat"), ayarlar_json=settings.get("ayarlar_json"))
            except llm.LLMHatasi as e:
                sonuc["adimlar"]["llm"] = {"passed": None, "atlandi": str(e)[:200]}
            try:
                if "llm" in sonuc["adimlar"]:
                    raise StopIteration
                t0 = time.time()
                tl, meta = llm.cikar_guvenli(istek.get("llm_mesaj") or istek["mesaj"], backend=settings["llm"].get("backend", "openai_chat"),
                                             model=settings["llm"].get("model") or None, ayarlar_json=settings.get("ayarlar_json"),
                                             timeout=int(settings["llm"].get("timeout_s", 60)))
                sonuc["adimlar"]["llm"] = {"passed": True, "niyet": tl.niyet, "katalog_kodu": tl.katalog_kodu,
                                          "varyantlar": [x.tur for x in tl.varyantlar], "guven": tl.guven, "ozet": tl.ozet, **meta}
            except StopIteration:
                pass
            except Exception as e:
                sonuc["adimlar"]["llm"] = {"passed": False, "hata": str(e)[:300]}
        sonuc["state"] = "passed" if all(a.get("passed") is not False for a in sonuc["adimlar"].values() if isinstance(a, dict)) else "failed"
    except Exception:
        sonuc["state"] = "failed"; sonuc["traceback"] = traceback.format_exc()[-4000:]
    sonuc["finished_at"] = int(time.time()); sonuc["sure_s"] = round(time.time() - baslangic, 1)
    sonuc["not"] = "Öz-test hiçbir WhatsApp mesajı göndermez; state.json'a satır yazmaz."
    yaz(sonuc_p, sonuc)
    log("öz-test", sonuc["state"], f"{sonuc['sure_s']} s")


# ───────────────────────── üretim ─────────────────────────
def is_al():
    """En eski 'queued' gelen mesajı 'processing' yap; takılı kalanları (STALE_S) başarısız say."""
    def fn(state):
        simdi = int(time.time())
        for r in state["inbound"].values():
            if r.get("state") == "processing" and r.get("updated_at", 0) < simdi - STALE_S:
                r.update(state="failed", error="İşlem teyit edilmeden bitti; otomatik tekrar yok.", updated_at=simdi)
        adaylar = [r for r in state["inbound"].values() if r.get("state") == "queued" and not r.get("self_test")]
        if not adaylar:
            return None
        r = min(adaylar, key=lambda x: (x.get("timestamp", 0), x.get("received_at", 0)))
        r.update(state="processing", attempts=r.get("attempts", 0) + 1, started_at=simdi, updated_at=simdi)
        return dict(r)
    return state_change(fn)


def satir_id(gelen_id: str, sira: int) -> str:
    return "out_" + hashlib.sha256(f"{gelen_id}|{sira}".encode()).hexdigest()[:24]


def giden_metin(gelen: dict, metin: str, sira: int, to: str | None = None, tur: str = "cevap") -> dict:
    return {"id": satir_id(gelen["id"], sira), "kind": "text", "to": to or gelen["sender"], "body": metin[:4000], "tur": tur,
            "inbound_id": gelen["id"], "seq": sira, "state": "pending", "wamid": None, "media_id": None, "attempts": 0,
            "error": None, "delivery_state": None, "created_at": int(time.time()), "updated_at": int(time.time())}


def giden_belge(gelen: dict, dosya: Path, ad: str, aciklama: str, sira: int, is_emri_no: str, revizyon: int, sha: str) -> dict:
    r = giden_metin(gelen, aciklama[:1000], sira, tur="belge")
    r.update(kind="document", file=str(dosya), filename=ad, mime="application/pdf", sha256=sha, is_emri_no=is_emri_no, revizyon=revizyon)
    return r


def baglam_ozeti(k) -> str:
    d = k.d
    if d.get("asama") == "topluyor" and d.get("taslak"):
        t = d["taslak"]
        parca = [f"aşama: bilgi toplanıyor", f"taslak özeti: {t.get('ozet', '')}"]
        if t.get("katalog_kodu"): parca.append(f"katalog kodu: {t['katalog_kodu']}")
        if t.get("oda_programi"): parca.append(f"oda programı: {t['oda_programi']}")
        if d.get("son_soru_alani"): parca.append(f"bayiye sorulan son soru alanı: {d['son_soru_alani']}")
        return "; ".join(parca)
    if d.get("asama") in ("onay_bekliyor", "uretildi") and d.get("son_is_emri"):
        return f"aşama: ön onay planı gönderildi ({d['son_is_emri'].get('is_emri_no')}), bayinin onay/revizyon cevabı bekleniyor"
    return ""


def teknik_not(karar, talep, meta: dict, cizim: dict | None) -> str:
    p = [f"eylem={karar.eylem}", f"gerekçe={karar.gerekce}", f"niyet={talep.niyet}/{talep.guven}"]
    if meta.get("backend") != "manuel":
        p.append(f"LLM {meta.get('model')} {meta.get('girdi_token')}+{meta.get('cikti_token')} token {meta.get('sure_ms')} ms" + (" (tekrar)" if meta.get("tekrar") else ""))
    if cizim:
        p.append(f"çizim {cizim.get('sure_s')} s, doğrulama {'geçti' if cizim.get('passed') else 'GEÇMEDİ'}")
    return "\n— teknik: " + " | ".join(p)


def isle(gelen: dict, settings: dict) -> dict:
    """Bir gelen mesajı işler; giden satırlarını ve sonucu döndürür (state.json'a yazmaz — çağıran yazar)."""
    from beyin import llm, katalog as KT
    from beyin.konusma import Konusma
    from beyin.karar import karar_ver
    from motor import dxf_out

    sender = gelen["sender"]; rol = gelen.get("role") or "bayi"; bayi = gelen.get("bayi")
    patron_mu = rol == "patron"
    satirlar: list[dict] = []; sira = 0
    sonuc = {"eylem": None, "gerekce": None}

    def ekle(metin: str, to: str | None = None, tur: str = "cevap"):
        nonlocal sira
        sira += 1; satirlar.append(giden_metin(gelen, metin, sira, to, tur))

    def patrona(metin: str):
        if not patron_mu:
            ekle(metin, "PATRON", "bildirim")

    kim = f"{(bayi or {}).get('ad') or gelen.get('name') or ''} ({maske(sender)})"
    if gelen.get("type") not in GELEN_YAZILI or not (gelen.get("text") or "").strip():
        ekle("Şu an yalnız yazılı talepleri işleyebiliyorum. Talebinizi yazıyla iletirseniz (örn. \"P6001 aynalı\" ya da \"7x4 m, 2+1, ön verandalı\") ön onay planını hazırlarım."
             + ("" if patron_mu else " Gönderdiğiniz dosyayı Lokman Bey'e ilettim."))
        patrona(f"Portman: {kim} yazılı olmayan mesaj gönderdi (tür: {gelen.get('type')}). Panelden bakabilirsiniz.")
        sonuc.update(eylem="cevapla", gerekce="metin dışı mesaj")
        return {"satirlar": satirlar, "sonuc": sonuc}

    k = Konusma(sender, KANAL / "durum")
    llm_ayar = settings.get("llm") or {}
    backend = llm_ayar.get("backend", "openai_chat")
    try:
        talep, meta = llm.cikar_guvenli(gelen["text"], baglam_ozeti(k), backend=backend, model=llm_ayar.get("model") or None,
                                        hazir=gelen.get("test_cikarim") if backend == "manuel" else None,   # yalnız yerel test
                                        ayarlar_json=settings.get("ayarlar_json"), timeout=int(llm_ayar.get("timeout_s", 60)))
    except Exception as e:
        hata = f"{type(e).__name__}: {str(e)[:300]}"
        ekle("Mesajınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
        patrona(f"Portman: {kim} mesajı işlenemedi (çıkarım hatası). Mesaj: \"{gelen['text'][:300]}\"")
        sonuc.update(eylem="hata", gerekce="çıkarım hatası", hata=hata)
        return {"satirlar": satirlar, "sonuc": sonuc, "hata": hata}

    karar = karar_ver(talep, k, bayi, KT.Katalog(), metin=gelen.get("text") or "")
    sonuc.update(eylem=karar.eylem, gerekce=karar.gerekce, niyet=talep.niyet, guven=talep.guven, katalog_kodu=talep.katalog_kodu,
                 varyantlar=[v.tur for v in talep.varyantlar], ozet=talep.ozet, llm=meta, asama=k.d.get("asama"))
    cizim = None
    if karar.eylem == "is_emri" and karar.is_emri:
        ie = karar.is_emri; no = ie["is_emri_no"]; rev = int(ie.get("revizyon", 1))
        hedef = KANAL / "projects" / no / f"r{rev:02d}"
        t0 = time.time()
        try:
            m = dxf_out.uret(ie, hedef)
            v = oku(hedef / "validation.json", {}) or {}
            cizim = {"sure_s": round(time.time() - t0, 1), "passed": v.get("passed") is True and bool(m.get("pdf")), "errors": (v.get("errors") or [])[:5],
                     "pdf": str(hedef / m["pdf"]) if m.get("pdf") else None, "dxf": str(hedef / m["dxf"]), "pdf_sha256": m.get("pdf_sha256"),
                     "dxf_sha256": m["dxf_sha256"], "warnings": m.get("warnings")}
        except Exception as e:
            hedef.mkdir(parents=True, exist_ok=True)
            yaz(hedef / "failure.json", {"traceback": traceback.format_exc()[-6000:], "failed_at": int(time.time())})
            cizim = {"sure_s": round(time.time() - t0, 1), "passed": False, "errors": [f"{type(e).__name__}: {str(e)[:300]}"]}
        sonuc["is_emri_no"] = no; sonuc["revizyon"] = rev; sonuc["cizim"] = cizim
    metin = karar.mesaj
    if patron_mu:
        metin = metin.replace("Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak.", "Bu talep şu an otomatik karşılanamıyor (Patron modu: ayrıca bildirim gönderilmez).")
    if patron_mu and settings.get("patron_teknik_not", True):
        metin += teknik_not(karar, talep, meta, cizim)
    ekle(metin)
    if cizim:
        if cizim["passed"]:
            sira += 1
            ad = Path(cizim["pdf"]).name
            satirlar.append(giden_belge(gelen, Path(cizim["pdf"]), ad,
                                        f"{sonuc['is_emri_no']} r{sonuc['revizyon']:02d} · ÖN ONAYA SUNULAN TASLAK · {talep.ozet or ''}".strip(),
                                        sira, sonuc["is_emri_no"], sonuc["revizyon"], cizim["pdf_sha256"]))
        else:
            ekle("Ön onay planı otomatik doğrulamadan geçmedi; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
            patrona(f"Portman: {kim} için {sonuc['is_emri_no']} çizimi doğrulamadan geçmedi: {'; '.join(cizim['errors'])[:400]}")
    if karar.eylem == "yonlendir":
        patrona(f"Portman yönlendirme: {kim} — {karar.gerekce}. Mesaj: \"{gelen['text'][:300]}\"")
    return {"satirlar": satirlar, "sonuc": sonuc}


def kaydet(gelen: dict, cikti: dict) -> None:
    def fn(state):
        simdi = int(time.time())
        for s in cikti["satirlar"]:
            if s["id"] not in state["outbound"]:
                state["outbound"][s["id"]] = s
        r = state["inbound"].get(gelen["id"])
        if r is not None:
            r.update(state="failed" if cikti.get("hata") else "done", result=cikti["sonuc"], outbound_ids=[s["id"] for s in cikti["satirlar"]],
                     error=cikti.get("hata"), finished_at=simdi, updated_at=simdi)
    state_change(fn)


def main() -> None:
    with (KANAL / "worker.lock").open("a") as kilit:
        try:
            fcntl.flock(kilit, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        settings = ayarlar()
        if settings.get("worker", "hosting") != "hosting":
            # Üretim bu makinede kapalı: bağımlılık kurulumu (pip), öz-test (gerçek LLM çağrısı olabilir) ve iş alma YAPILMAZ; yalnız sağlık yazılır.
            # (Denetim bulgusu F09: önceki sıra worker=vps iken de pip/öz-test yan etkisine izin veriyordu.)
            saglik({"worker": settings.get("worker"), "note": "üretim bu makinede kapalı (settings.worker); pip/öz-test atlandı"}); return
        if not bagimliliklar_hazir():
            saglik({"deps": "eksik; install-report.json"}); return
        try:
            oz_test(settings)
        except Exception:
            log("öz-test çalıştırılamadı:", traceback.format_exc()[-800:])
        if settings.get("enabled") is not True:
            saglik(); return
        butce = time.time() + float(settings.get("budget_s", 45))
        en_fazla = int(settings.get("max_is_per_tick", 2)); n = 0; son = None
        while n < en_fazla and time.time() < butce:
            gelen = is_al()
            if not gelen:
                break
            n += 1; t0 = time.time()
            try:
                cikti = isle(gelen, settings)
            except Exception:
                hata = traceback.format_exc()[-2500:]
                cikti = {"satirlar": [giden_metin(gelen, "Mesajınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.", 1)]
                         + ([] if gelen.get("role") == "patron" else [giden_metin(gelen, f"Portman: {maske(gelen['sender'])} mesajı işlenirken hata oluştu; state.json/worker.log'a bakın.", 2, "PATRON", "bildirim")]),
                         "sonuc": {"eylem": "hata", "gerekce": "beklenmeyen hata"}, "hata": hata}
            kaydet(gelen, cikti)
            son = {"id": gelen["id"][:24], "eylem": cikti["sonuc"].get("eylem"), "sure_s": round(time.time() - t0, 1)}
            log("gelen", gelen["id"][:20], "kimden", maske(gelen["sender"]), "→", cikti["sonuc"].get("eylem"), f"({cikti['sonuc'].get('gerekce')})",
                f"{son['sure_s']} s", "giden:", len(cikti["satirlar"]), ("HATA: " + cikti["hata"].splitlines()[-1][:160]) if cikti.get("hata") else "")
        saglik({"last_job": son} if son else None)


if __name__ == "__main__":
    main()
