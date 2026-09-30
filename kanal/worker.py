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
SURUM = "kanal-v1.3"    # İE-04 mesaj katmanı: image ve interactive satırlar, buton cevaplarının kimlikle çözümü
STALE_S = 600           # 'processing' bu kadar süre ilerlemezse başarısız sayılır (otomatik tekrar yok)
GELEN_YAZILI = ("text", "button", "interactive")
# Kısa cevaplı sorular buton taşır (kimlik dilbilgisi: kanal/etkilesim.py). Metinle cevap yolu her zaman açık kalır.
SORU_BUTONLARI = {"pencere_islem": [("q:pencere_islem:degistir", "Değiştir"), ("q:pencere_islem:ekle", "Ekle")],
                  "yeni_mi_degisiklik": [("q:yeni_mi_degisiklik:yeni", "Yeni talep"), ("q:yeni_mi_degisiklik:degisiklik", "Değişiklik")]}
# WhatsApp Cloud API sınırları (feature.php aynı sınırları gönderimden önce yeniden denetler)
WA_BUTON = 3; WA_BUTON_BASLIK = 20; WA_LISTE_SATIR = 10; WA_SATIR_BASLIK = 24; WA_SATIR_ACIKLAMA = 72; WA_GOVDE = 1024; WA_ALTBILGI = 60


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


def _kes(m: str | None, n: int) -> str:
    m = " ".join(str(m or "").split())
    return m if len(m) <= n else m[:n - 1] + "…"


def giden_gorsel(gelen: dict, dosya: Path, ad: str, aciklama: str, sira: int, sha: str, is_emri_no: str | None = None,
                 revizyon: int | None = None) -> dict:
    """Plan görseli (PNG/JPEG ≤5 MB) satırı; altyazı ≤1024."""
    r = giden_metin(gelen, aciklama[:1024], sira, tur="gorsel")
    r.update(kind="image", file=str(dosya), filename=ad, mime="image/png" if str(ad).lower().endswith(".png") else "image/jpeg", sha256=sha,
             is_emri_no=is_emri_no, revizyon=revizyon)
    return r


def giden_etkilesim(gelen: dict, metin: str, sira: int, butonlar: list[tuple[str, str]] | None = None, liste: dict | None = None,
                    baglanti: dict | None = None, gorsel: dict | None = None, altbilgi: str | None = None, tur: str = "cevap",
                    is_emri_no: str | None = None, revizyon: int | None = None) -> dict:
    """Etkileşimli satır: butonlar [(id, başlık)] (≤3) | liste {"dugme", "bolumler": [{"baslik", "satirlar": [{"id","baslik","aciklama"}]}]} (≤10 satır)
    | baglanti {"metin", "url"}. gorsel: {"file","filename","sha256","mime"} başlık görseli (buton ve bağlantı mesajında). Sınırlar kesilerek uygulanır;
    feature.php gönderimden önce yeniden denetler. Gövde metni 'body'de de durur (panel ve yedek)."""
    r = giden_metin(gelen, metin[:WA_GOVDE], sira, tur=tur)
    i: dict = {"body": {"text": _kes(metin, WA_GOVDE)}}
    if altbilgi:
        i["footer"] = {"text": _kes(altbilgi, WA_ALTBILGI)}
    if liste:
        satir_sayisi = 0; bolumler = []
        for b in liste.get("bolumler") or []:
            rows = []
            for x in b.get("satirlar") or []:
                if satir_sayisi >= WA_LISTE_SATIR:
                    break
                rows.append({"id": str(x["id"])[:200], "title": _kes(x["baslik"], WA_SATIR_BASLIK), "description": _kes(x.get("aciklama") or "", WA_SATIR_ACIKLAMA)})
                satir_sayisi += 1
            if rows:
                bolumler.append({"title": _kes(b.get("baslik") or "Seçenekler", WA_SATIR_BASLIK), "rows": rows})
        i["type"] = "list"; i["action"] = {"button": _kes(liste.get("dugme") or "Seçenekleri gör", WA_BUTON_BASLIK), "sections": bolumler}
    elif baglanti:
        i["type"] = "cta_url"; i["action"] = {"name": "cta_url", "parameters": {"display_text": _kes(baglanti["metin"], WA_BUTON_BASLIK), "url": str(baglanti["url"])}}
    else:
        i["type"] = "button"
        i["action"] = {"buttons": [{"type": "reply", "reply": {"id": str(bid)[:256], "title": _kes(bas, WA_BUTON_BASLIK)}} for bid, bas in (butonlar or [])[:WA_BUTON]]}
    if gorsel and i["type"] in ("button", "cta_url"):
        i["header"] = {"type": "image", "file": str(gorsel["file"])}
        r.update(file=str(gorsel["file"]), filename=gorsel.get("filename") or Path(str(gorsel["file"])).name, sha256=gorsel.get("sha256"),
                 mime=gorsel.get("mime") or "image/png")
    r.update(kind="interactive", interactive=i, is_emri_no=is_emri_no, revizyon=revizyon)
    return r


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def giden_bul_dosya(context_id: str) -> dict | None:
    """Dosya modu: state.json'daki giden satırlardan WhatsApp kimliği eşleşen (cevaplanan mesaj)."""
    st = _normal(oku(KANAL / "state.json", {}))
    for r in (st.get("outbound") or {}).values():
        if r.get("wamid") == context_id:
            return r
    return None


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


def katalog_nesnesi(settings: dict, kabul_edilmis: set | None = None):
    """İE-04: test adayları yalnız settings.test_adaylari true iken görünür (yerel); kalıcı mod kabul kümesini verir (K-A10)."""
    from beyin import katalog as KT
    return KT.Katalog(test_adaylari=bool(settings.get("test_adaylari")), kabul_edilmis=kabul_edilmis)


def isle(gelen: dict, settings: dict, k=None, cikarim: dict | None = None, proje_koku: Path | None = None, giden_bul=None,
         katalog=None) -> dict:
    """Bir gelen mesajı işler; giden satırlarını ve sonucu döndürür (state.json'a yazmaz — çağıran yazar).
    İE-02 (kalıcı akış, kanal/kalici.py): k verilirse konuşma dosyadan değil o nesneden okunur; cikarim verilirse
    ({"talep": …, "meta": …} ya da {"hata": …}) LLM çağrılmaz; proje_koku verilirse Motor çıktısı projects/ yerine oraya
    yazılır (kalıcı akış önce hazırlık klasörüne yazar, kayıtla birlikte yerine taşır). Hiçbiri verilmezse davranış
    v1.1.1 ile aynı.
    İE-04: gelen satırda reply_id varsa (buton ya da liste cevabı) LLM çağrılmaz; kimlik kanal/etkilesim.py ile çözülür
    (cikarim["etkilesim"] verilmişse o kullanılır). giden_bul(context_id) cevaplanan giden satırı verir (doğrulama için)."""
    from beyin.konusma import Konusma
    from beyin.karar import karar_ver
    from motor import dxf_out
    import etkilesim as ET

    sender = gelen["sender"]; rol = gelen.get("role") or "bayi"; bayi = gelen.get("bayi")
    patron_mu = rol == "patron"
    satirlar: list[dict] = []; sira = 0
    sonuc = {"eylem": None, "gerekce": None}

    def ekle(metin: str, to: str | None = None, tur: str = "cevap"):
        nonlocal sira
        sira += 1; satirlar.append(giden_metin(gelen, metin, sira, to, tur))

    def ekle_satir(r: dict):
        nonlocal sira
        sira += 1; r["seq"] = sira; r["id"] = satir_id(gelen["id"], sira); satirlar.append(r)

    def patrona(metin: str):
        if not patron_mu:
            ekle(metin, "PATRON", "bildirim")

    kim = f"{(bayi or {}).get('ad') or gelen.get('name') or ''} ({maske(sender)})"
    if gelen.get("type") not in GELEN_YAZILI or not ((gelen.get("text") or "").strip() or gelen.get("reply_id")):
        ekle("Şu an yalnız yazılı talepleri işleyebiliyorum. Talebinizi yazıyla iletirseniz (örn. \"P6001 aynalı\" ya da \"7x4 m, 2+1, ön verandalı\") ön onay planını hazırlarım."
             + ("" if patron_mu else " Gönderdiğiniz dosyayı Lokman Bey'e ilettim."))
        patrona(f"Portman: {kim} yazılı olmayan mesaj gönderdi (tür: {gelen.get('type')}). Panelden bakabilirsiniz.")
        sonuc.update(eylem="cevapla", gerekce="metin dışı mesaj")
        return {"satirlar": satirlar, "sonuc": sonuc}

    if k is None:
        k = Konusma(sender, KANAL / "durum")
    k.son_mesaj_id = gelen["id"]                  # seçenek seti kimliği bu mesajdan türer (aynı mesaj → aynı set)
    if katalog is None:
        katalog = katalog_nesnesi(settings)
    metin_kural = gelen.get("text") or ""
    etk = None
    if gelen.get("reply_id"):
        etk = (cikarim or {}).get("etkilesim") or ET.coz(gelen, k.d, giden_bul if giden_bul is not None else giden_bul_dosya)
        if not etk.get("gecerli"):
            # Eski ya da tanınmayan buton: hiçbir durum değişmez; bayiye güncel durum söylenir. (LLM çağrılmaz.)
            k.not_dus("gelen", f"buton {etk.get('kimlik')}", {"niyet": "buton", "guven": "yuksek"})
            k.not_dus("kural", f"eski buton: {etk.get('neden')}")
            k.not_dus("giden", etk["mesaj"], {"eylem": "cevapla", "gerekce": "eski buton"})
            k.kaydet()
            teknik = f"— teknik: eylem=cevapla | gerekçe=eski buton: {etk.get('neden')} | kimlik={etk.get('kimlik')}" if (patron_mu and settings.get("patron_teknik_not", True)) else ""
            if teknik and settings.get("mesaj_katmani"):
                ekle(etk["mesaj"]); ekle(teknik)
            else:
                ekle(etk["mesaj"] + ("\n" + teknik if teknik else ""))
            sonuc.update(eylem="cevapla", gerekce=f"eski buton: {etk.get('neden')}", buton=etk.get("kimlik"), asama=k.d.get("asama"))
            return {"satirlar": satirlar, "sonuc": sonuc}
        metin_kural = etk["metin"]
    try:
        if etk is not None:
            from beyin.sema import Talep
            talep, meta = Talep.model_validate(etk["talep"]), {"backend": "etkilesim", "kimlik": etk["kimlik"], "tur": etk["tur"]}
        elif cikarim is not None:
            if cikarim.get("hata"):
                raise CikarimHatasi(cikarim["hata"])
            from beyin.sema import Talep
            talep, meta = Talep.model_validate(cikarim["talep"]), dict(cikarim.get("meta") or {})
        else:
            talep, meta = cikar(gelen, settings, k)
    except Exception as e:
        hata = str(e)[:320] if isinstance(e, CikarimHatasi) else f"{type(e).__name__}: {str(e)[:300]}"
        ekle("Mesajınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
        patrona(f"Portman: {kim} mesajı işlenemedi (çıkarım hatası). Mesaj: \"{gelen['text'][:300]}\"")
        sonuc.update(eylem="hata", gerekce="çıkarım hatası", hata=hata)
        return {"satirlar": satirlar, "sonuc": sonuc, "hata": hata}

    karar = karar_ver(talep, k, bayi, katalog, metin=metin_kural)
    if etk is not None:
        sonuc["buton"] = etk["kimlik"]
    if karar.kullanilan_talep:      # D-01: bayi "yeni"/"değişiklik" diye cevap verdi; işlenen, bekletilen mesajın talebidir
        talep = type(talep).model_validate(karar.kullanilan_talep)
    sonuc.update(eylem=karar.eylem, gerekce=karar.gerekce, niyet=talep.niyet, guven=talep.guven, katalog_kodu=talep.katalog_kodu,
                 varyantlar=[v.tur for v in talep.varyantlar], ozet=talep.ozet, llm=meta, asama=k.d.get("asama"))
    cizim = None
    if karar.eylem == "is_emri" and karar.is_emri:
        ie = karar.is_emri; no = ie["is_emri_no"]; rev = int(ie.get("revizyon", 1))
        hedef = (Path(proje_koku) if proje_koku else KANAL / "projects") / no / f"r{rev:02d}"
        t0 = time.time()
        try:
            m = dxf_out.uret(ie, hedef)
            v = oku(hedef / "validation.json", {}) or {}
            cizim = {"sure_s": round(time.time() - t0, 1), "passed": v.get("passed") is True and bool(m.get("pdf")), "errors": (v.get("errors") or [])[:5],
                     "pdf": str(hedef / m["pdf"]) if m.get("pdf") else None, "dxf": str(hedef / m["dxf"]), "pdf_sha256": m.get("pdf_sha256"),
                     "dxf_sha256": m["dxf_sha256"], "warnings": m.get("warnings")}
            if cizim["passed"] and settings.get("mesaj_katmani"):
                cizim["ekler"] = ekler_uret(ie, hedef, v, settings)      # İE-04: aynı İş Emri'nden bayi görseli, IFC ve 3D sayfası
        except Exception as e:
            hedef.mkdir(parents=True, exist_ok=True)
            yaz(hedef / "failure.json", {"traceback": traceback.format_exc()[-6000:], "failed_at": int(time.time())})
            cizim = {"sure_s": round(time.time() - t0, 1), "passed": False, "errors": [f"{type(e).__name__}: {str(e)[:300]}"]}
        sonuc["is_emri_no"] = no; sonuc["revizyon"] = rev; sonuc["cizim"] = cizim
    metin = karar.mesaj
    if patron_mu:
        metin = metin.replace("Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak.", "Bu talep şu an otomatik karşılanamıyor (Patron modu: ayrıca bildirim gönderilmez).")
    teknik = teknik_not(karar, talep, meta, cizim) if (patron_mu and settings.get("patron_teknik_not", True)) else ""
    if teknik and not settings.get("mesaj_katmani"):
        metin += teknik; teknik = ""          # katman kapalı: v1.2 ile aynı tek metin
    # ── İE-04: satır türü karara göre; yalnız settings.mesaj_katmani açıkken (hosting v1.3). Kapalıyken bugünkü metin + PDF.
    # Metin yolu her zaman kalır (buton yalnız kısayoldur).
    katman = bool(settings.get("mesaj_katmani"))
    butonlar = [(b["id"], b["baslik"]) for b in (karar.butonlar or [])] or \
               ([tuple(x) for x in SORU_BUTONLARI[karar.soru_alani]] if karar.eylem == "sor" and karar.soru_alani in SORU_BUTONLARI else [])
    if not katman:
        butonlar = []
    if karar.eylem == "secenek" and karar.secenek_seti and not katman:
        ekle(metin + "\n\nSeçmek için kodunu yazın.")
        sonuc["secenek_seti"] = {"id": karar.secenek_seti["id"], "adaylar": [a["kod"] for a in karar.secenek_seti["adaylar"]]}
    elif karar.eylem == "secenek" and karar.secenek_seti:
        for r in secenek_satirlari(gelen, karar, katalog, metin, proje_koku):
            ekle_satir(r)
        sonuc["secenek_seti"] = {"id": karar.secenek_seti["id"], "adaylar": [a["kod"] for a in karar.secenek_seti["adaylar"]]}
    elif cizim and cizim["passed"] and not katman:
        ekle(metin)
        ad = Path(cizim["pdf"]).name
        ekle_satir(giden_belge(gelen, Path(cizim["pdf"]), ad, f"{sonuc['is_emri_no']} r{sonuc['revizyon']:02d} · ÖN ONAYA SUNULAN TASLAK · {talep.ozet or ''}".strip(),
                               0, sonuc["is_emri_no"], sonuc["revizyon"], cizim["pdf_sha256"]))
    elif cizim and cizim["passed"]:
        ekler = cizim.get("ekler") or {}
        no, rev = sonuc["is_emri_no"], sonuc["revizyon"]
        gorsel = ekler.get("gorsel")
        ekle_satir(giden_etkilesim(gelen, metin, 0, butonlar=[(f"o:{no}:{rev}", "Onayla"), (f"r:{no}:{rev}", "Revize et")],
                                   gorsel=gorsel, altbilgi=f"{no} r{rev:02d}", is_emri_no=no, revizyon=rev))
        ad = Path(cizim["pdf"]).name
        ekle_satir(giden_belge(gelen, Path(cizim["pdf"]), ad, f"{no} r{rev:02d} · ÖN ONAYA SUNULAN TASLAK · {talep.ozet or ''}".strip(),
                               0, no, rev, cizim["pdf_sha256"]))
        ucb = ekler.get("ucb")
        if ucb and ucb.get("url"):
            ekle_satir(giden_etkilesim(gelen, f"{no} r{rev:02d} planının basit 3D modeli. Tarayıcıda açılır; odalara dokunarak gezebilirsiniz.", 0,
                                       baglanti={"metin": "3D'de gez", "url": ucb["url"]}, tur="cevap", is_emri_no=no, revizyon=rev))
        elif ucb and ucb.get("dosya"):
            ekle(f"{no} r{rev:02d} için 3D model aynı revizyondan üretildi; bağlantısı yayınlanınca göndereceğim.")
    elif butonlar:
        ekle_satir(giden_etkilesim(gelen, metin, 0, butonlar=butonlar))
    else:
        ekle(metin)
    if teknik:
        ekle(teknik.strip())
    if cizim and not cizim["passed"]:
        ekle("Ön onay planı otomatik doğrulamadan geçmedi; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
        patrona(f"Portman: {kim} için {sonuc['is_emri_no']} çizimi doğrulamadan geçmedi: {'; '.join(cizim['errors'])[:400]}")
    if karar.eylem == "yonlendir":
        patrona(f"Portman yönlendirme: {kim} — {karar.gerekce}. Mesaj: \"{(gelen.get('text') or '')[:300]}\"")
    return {"satirlar": satirlar, "sonuc": sonuc}


def secenek_satirlari(gelen: dict, karar, katalog, metin: str, proje_koku: Path | None) -> list[dict]:
    """Seçenek seti: bileşik görsel (varsa) başlıklı buton mesajı (en çok 3 seçim) + üçten çok aday varsa tam liste."""
    st = karar.secenek_seti
    adaylar = st["adaylar"]
    butonlar = [(b["id"], b["baslik"]) for b in (karar.butonlar or [])]
    gorsel = None
    try:
        from beyin import secenek as SC
        from motor import bayi_gorseli as BG
        kok = (Path(proje_koku) if proje_koku else KANAL / "projects") / f"SECENEK-{st['id']}" / "r01"
        kok.mkdir(parents=True, exist_ok=True)
        yol = BG.bilesik_gorsel([{**a, "gorsel_yolu": (KT_KOK() / a["gorsel"]) if a.get("gorsel") else None} for a in adaylar[:SC.EN_COK_GORSEL]],
                                kok / "secenekler.png", baslik=f"{gelen.get('text') or ''}"[:60])
        if yol:
            gorsel = {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png"}
    except Exception as e:      # görsel üretilemezse metinli buton mesajı gider; akış durmaz
        log("seçenek görseli üretilemedi:", f"{type(e).__name__}: {str(e)[:160]}")
    rows = [giden_etkilesim(gelen, metin, 0, butonlar=butonlar, gorsel=gorsel, altbilgi="Butonla ya da yazarak seçin")]
    if len(adaylar) > len(butonlar):
        from beyin import secenek as SC
        liste = {"dugme": "Tüm seçenekler", "bolumler": [{"baslik": "Puana göre", "satirlar": [
            {"id": f"s:{st['id']}:{a['kod']}", "baslik": SC.kisa_ad(a), "aciklama": SC.aciklama(a)} for a in adaylar]}]}
        rows.append(giden_etkilesim(gelen, f"{len(adaylar)} seçeneğin tamamı, puanlarıyla listede.", 0, liste=liste))
    return rows


def KT_KOK() -> Path:
    from beyin import katalog as KT
    return KT.SABLON_DIR


def ekler_uret(ie: dict, hedef: Path, v: dict, settings: dict) -> dict:
    """Aynı İş Emri revizyonundan türetilen ekler: {"gorsel": {...}, "ifc": {...}, "ucb": {...}}. Her biri ayrı denenir; üretilemeyen
    ek akışı durdurmaz (satır metinle gider) ve 'hata' ile kaydedilir. Motor'un DXF/PDF'ine dokunulmaz."""
    ekler: dict = {}
    no, rev = ie.get("is_emri_no", ""), int(ie.get("revizyon") or 1)
    try:
        from motor import bayi_gorseli as BG
        yol = BG.plan_gorseli(ie, hedef / "plan_bayi.png", v)
        ekler["gorsel"] = {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png"}
    except Exception as e:
        ekler["gorsel_hata"] = f"{type(e).__name__}: {str(e)[:200]}"
    try:
        from motor import ifc_uret as IU
        ad = f"Portman_{no}_r{rev:02d}.ifc"
        oz = IU.uret(ie, hedef / ad, baslik=f"Portman — {no} r{rev:02d}")
        ekler["ifc"] = {"dosya": str(hedef / ad), "sha256": _sha(hedef / ad), **{k: oz.get(k) for k in ("duvar", "pencere", "kapi", "mahal", "sema_hatasi")}}
        try:
            from motor import ucb_sayfa as US
            html = US.uret(hedef / ad, hedef / "3d" / "index.html", baslik=f"{no} r{rev:02d}")
            taban = str(settings.get("ucb_taban_url") or "").rstrip("/")
            ekler["ucb"] = {"dosya": str(html), "sha256": _sha(html), "url": f"{taban}/{no}/r{rev:02d}/" if taban else None}
        except Exception as e:
            ekler["ucb_hata"] = f"{type(e).__name__}: {str(e)[:200]}"
    except Exception as e:
        ekler["ifc_hata"] = f"{type(e).__name__}: {str(e)[:200]}"
    return ekler


class CikarimHatasi(Exception):
    """Kayıtlı çıkarım bir hata taşıyor (kalıcı akış: LLM çağrısı önceki denemede başarısız oldu)."""


def cikar(gelen: dict, settings: dict, k):
    """LLM çıkarımı (yalnız "bayi ne dedi?"). isle() ve kalıcı akış (kanal/kalici.py) aynı yolu kullanır."""
    from beyin import llm
    llm_ayar = settings.get("llm") or {}
    backend = llm_ayar.get("backend", "openai_chat")
    return llm.cikar_guvenli(gelen["text"], baglam_ozeti(k), backend=backend, model=llm_ayar.get("model") or None,
                             hazir=gelen.get("test_cikarim") if backend == "manuel" else None,   # yalnız yerel test
                             ayarlar_json=settings.get("ayarlar_json"), timeout=int(llm_ayar.get("timeout_s", 60)))


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
