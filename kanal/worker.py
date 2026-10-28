"""PORTMAN KANAL — işleme çekirdeği (İE-06'dan beri yalnız Postgres akışı; kanal/kalici.py::bir_is çağırır).

Gelen WhatsApp mesajı (webhook → Postgres)
  → Beyin: LLM çıkarım (yalnız "bayi ne dedi?") + deterministik kural katmanı
  → giden METİN satırı (Postgres giden; kanal/gonderici.py gönderir)
  → İş Emri çıktıysa Motor (DXF → yeniden aç → doğrula → PDF) → giden BELGE satırı (+ İE-04: görsel, etkileşim, 3D)
  → yönlendirme / hata → Patron'a bildirim satırı.

Bu dosya WhatsApp'a bağlanmaz ve HİÇBİR ŞEY GÖNDERMEZ; dışarı yalnız LLM çağrısı çıkar. Kurulum öz-testi (self-test-request.json)
çıktıları checks/ altına yazar. Hosting dosya modu (state.json, cron, pip kurulumu) İE-06 ile kaldırıldı.
"""
from __future__ import annotations
import hashlib, json, os, sys, time, traceback, warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

KOD = Path(__file__).resolve().parent                                   # kod (kanal/); beyin/, motor/, is_emri/ bir üstte
KANAL = Path(os.environ.get("PORTMAN_KANAL_DIR") or KOD).resolve()     # veri (settings.json, projects/, checks/)
for _yol in (KOD.parent, KOD):
    if str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))
os.umask(0o077)
SURUM = "kanal-v2.0"    # İE-06: tek sunucu; v1.3 mesaj katmanı (image, interactive, buton kimlikleri) aynen
GELEN_YAZILI = ("text", "button", "interactive")
GORSEL_TURLERI = ("image", "document")      # İE-20: `gorsel_okuma.acik` iken okunan gelen medya (plan resmi, el çizimi, PDF)
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


def log(*parca) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *parca, flush=True)


def maske(numara: str) -> str:
    return "…" + str(numara)[-4:] if numara else "-"


# ───────────────────────── öz-test ─────────────────────────
def oz_test(settings: dict) -> None:
    """self-test-request.json varsa ve sonucu yoksa bir kez koşar (sürüm başına; vps/agent.py). Hiçbir şey göndermez."""
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
    sonuc["not"] = "Öz-test hiçbir WhatsApp mesajı göndermez; giden satırı yazmaz."
    yaz(sonuc_p, sonuc)
    log("öz-test", sonuc["state"], f"{sonuc['sure_s']} s")


# ───────────────────────── üretim ─────────────────────────
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


def bayi_tanimi(bayi: dict | None) -> str:
    """İE-08 8b M5 (D-06; iş emri M5 "bayinin hitabı, yoksa adı"): LLM bağlamında yalnız hitap, hitap yoksa ad; ikisi birden değil (veri
    en aza). Telefon numarası asla: ad numaraya düşmüşse yazılmaz, numara biçimli her şey maskelenir. Kayıtsız ya da boşsa ''."""
    b = bayi or {}
    hitap = maske_numaralar(str(b.get("hitap") or "").strip())[:40]
    if hitap:
        return f"bayinin hitabı: {hitap}"
    ad = str(b.get("ad") or "").strip()
    if not ad or ad == str(b.get("numara") or "") or ad.isdigit():
        return ""
    return f"bayinin adı: {maske_numaralar(ad)[:80]}"


def baglam_ozeti(k) -> str:
    d = k.d
    if d.get("asama") == "topluyor" and d.get("taslak"):
        t = d["taslak"]
        parca = [f"aşama: bilgi toplanıyor", f"taslak özeti: {t.get('ozet', '')}"]
        if t.get("katalog_kodu"): parca.append(f"katalog kodu: {t['katalog_kodu']}")
        if t.get("oda_programi"): parca.append(f"oda programı: {t['oda_programi']}")
        if d.get("son_soru_alani"): parca.append(f"bayiye sorulan son soru alanı: {d['son_soru_alani']}")
        y = (d.get("son_is_emri") or {}).get("yapi") or {}
        if y.get("sistem") == "celik":                                     # İE-08 A4: açık çelik plan ve uygulanmış değişiklikler (numara ve ad yok)
            parca.append(f"açık plan: çelik model {y.get('gosterim') or y.get('kod')}" + (f", uygulanan: {'; '.join(y['uygulanan'])}" if y.get("uygulanan") else ""))
        return "; ".join(parca)
    if d.get("asama") in ("onay_bekliyor", "uretildi") and d.get("son_is_emri"):
        ie = d["son_is_emri"]; y = ie.get("yapi") or {}
        celik = f", çelik model {y.get('gosterim') or y.get('kod')}" if y.get("sistem") == "celik" else ""      # İE-08: model kodu; numara ve ad yok (Z-08)
        if y.get("sistem") == "celik" and y.get("uygulanan"):            # A4: aynı projede birikmiş değişiklikler (LLM revizyonu doğru okusun)
            celik += f", uygulanan: {'; '.join(y['uygulanan'])}"
        return f"aşama: ön onay planı gönderildi ({ie.get('is_emri_no')}{celik}), bayinin onay/revizyon cevabı bekleniyor"
    return ""


def teknik_not(karar, talep, meta: dict, cizim: dict | None) -> str:
    p = [f"eylem={karar.eylem}", f"gerekçe={karar.gerekce}", f"niyet={talep.niyet}/{talep.guven}"]
    if meta.get("backend") != "manuel":
        p.append(f"LLM {meta.get('model')} {meta.get('girdi_token')}+{meta.get('cikti_token')} token {meta.get('sure_ms')} ms" + (" (tekrar)" if meta.get("tekrar") else ""))
    if cizim:
        p.append(f"çizim {cizim.get('sure_s')} s{' (genel motor' + (', perspektif ' + str(cizim.get('perspektif'))) + ')' if cizim.get('motor') == 'genel' else ''}, doğrulama {'geçti' if cizim.get('passed') else 'GEÇMEDİ'}")
        ek = cizim.get("ekler")
        if ek is not None:      # İE-04: aynı revizyondan türeyen ekler (görsel, IFC, 3D sayfası); üretilemeyen 'yok'
            p.append("ekler görsel " + ("var" if ek.get("gorsel") else "yok") + ", IFC " + ("var" if ek.get("ifc") else "yok")
                     + ", 3D " + ("bağlantı" if (ek.get("ucb") or {}).get("url") else ("sayfa" if ek.get("ucb") else "yok")))
    return "\n— teknik: " + " | ".join(p)


def katalog_nesnesi(settings: dict, kabul_edilmis: set | None = None):
    """İE-04: test adayları yalnız settings.test_adaylari true iken görünür (yerel); kalıcı mod kabul kümesini verir (K-A10)."""
    from beyin import katalog as KT
    return KT.Katalog(test_adaylari=bool(settings.get("test_adaylari")), kabul_edilmis=kabul_edilmis)


def isle(gelen: dict, settings: dict, k=None, cikarim: dict | None = None, proje_koku: Path | None = None, giden_bul=None,
         katalog=None, ek_kaydet=None, ara_gonder=None) -> dict:
    """Bir gelen mesajı işler; giden satırlarını ve sonucu döndürür (kayda yazmaz — çağıran yazar: kanal/kalici.py).
    k verilirse konuşma o nesneden okunur (Postgres); verilmezse Beyin'in dosya tabanlı Konusma'sı (yalnız yerel koşum ve
    testler). cikarim verilirse ({"talep": …, "meta": …} ya da {"hata": …}) LLM çağrılmaz; proje_koku verilirse Motor çıktısı
    projects/ yerine oraya yazılır (kalıcı akış önce hazırlık klasörüne yazar, kayıtla birlikte yerine taşır).
    İE-04: gelen satırda reply_id varsa (buton ya da liste cevabı) LLM çağrılmaz; kimlik kanal/etkilesim.py ile çözülür
    (cikarim["etkilesim"] verilmişse o kullanılır). giden_bul(context_id) cevaplanan giden satırı verir (doğrulama için);
    None ise bu doğrulama yapılmaz."""
    from beyin.konusma import Konusma
    from beyin.karar import karar_ver, plan_sonucu, PLAN_URETIMI
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

    def patrona(metin: str, sablon: bool = False, is_emri_no: str | None = None):
        """Patron'a bildirim: metin satırı (pencere açıkken gider). İE-07: sablon=True ise ek bir Meta şablon satırı yazılır
        (yönlendirme, hata, dosya penceresi); gönderici pencere kapalıysa onu gönderir, açıksa 'sablon_gereksiz' yapar (P4)."""
        if patron_mu:
            return
        ekle(metin, "PATRON", "bildirim")
        if sablon:
            import sablonlar as S
            ekle_satir(S.patron_bildirim_satiri(gelen, sira + 1, bayi, is_emri_no, baslangic.get("son_no")))

    baslangic: dict = {}                          # mesaj işlenmeden önceki taslağın son İş Emri no'su (yönlendirme taslağı siler)
    if k is not None and isinstance(getattr(k, "d", None), dict):
        baslangic["son_no"] = (k.d.get("son_is_emri") or {}).get("is_emri_no")
    kim = f"{(bayi or {}).get('ad') or gelen.get('name') or ''} ({maske(sender)})"
    reply_id = str(gelen.get("reply_id") or "")
    import sablonlar as S0
    if gelen.get("type") in GELEN_YAZILI and reply_id.startswith("dosya:") and S0.is_emri_no_gecerli(reply_id[len("dosya:"):]):
        # İE-07 P5: bayi "dosyalarınız hazır" şablonunun hızlı yanıt düğmesine bastı → Meta tarafında 24 saat penceresi açıldı.
        # LLM çağrılmaz, konuşma durumu değişmez; bayiye onaylı sabit cevap, Patron'a bildirim (metin + şablon, ekleme A).
        import sablonlar as S
        no = reply_id[len("dosya:"):][:60]
        ekle(S.BAYI_DOSYA_CEVABI)
        patrona(f"Portman: {kim} dosya penceresini açtı ({no}). Panelden dosyaları gönderebilirsiniz.", sablon=True, is_emri_no=no)
        sonuc.update(eylem="cevapla", gerekce="şablon cevabı: dosya penceresi açıldı", buton=reply_id, is_emri_no=no)
        return {"satirlar": satirlar, "sonuc": sonuc}
    if gelen.get("type") in GELEN_YAZILI and reply_id in (S0.BILGI_NASIL, S0.BILGI_HAZIR):
        # İE-08 8b M4: karşılama şablonunun "Nasıl çalışır?" düğmesi → tek sayfa PDF; "bilgi hazır" şablonunun "Bilgiyi gönder" düğmesi →
        # sabit cevap + Patron'a bildirim (pencere açıldı, Patron panelden yazar). LLM çağrılmaz, konuşma durumu değişmez.
        if reply_id == S0.BILGI_NASIL:
            try:
                yol, sha = nasil_calisir_pdf()
                ekle_satir(giden_belge(gelen, yol, "Portman_Nasil_calisir.pdf", "Portman · Nasıl çalışır?", 0, "", 0, sha))
                if form_kimligi(settings, "talep"):            # İE-20 PR-2: aynı satır [Talep formu] düğmeli
                    import talep_formu as TF
                    ekle_satir(giden_form(gelen, NASIL_TALEP.replace("yazabilirsiniz", "yazabilir ya da formu doldurabilirsiniz"), 0, "talep",
                                          settings, TF.talep_tokeni(satir_id(gelen["id"], 0)[4:16]), TF.ekran_verisi(bayi, None)))
                else:
                    ekle(NASIL_TALEP)
            except Exception as e:
                log("nasıl çalışır PDF'i üretilemedi:", type(e).__name__)
                ekle("Bilgi sayfasını şu an gönderemedim; Lokman Bey'e iletiyorum. Talebinizi bu sohbete yazabilirsiniz.")
                patrona(f"Portman: {kim} 'Nasıl çalışır?' istedi ama PDF üretilemedi; günlüğe bakın.")
            sonuc.update(eylem="cevapla", gerekce="şablon cevabı: nasıl çalışır", buton=reply_id)
        else:
            ekle(S0.BAYI_BILGI_CEVABI)
            patrona(f"Portman: {kim} bilgi penceresini açtı. Panelden yazabilirsiniz.", sablon=True)
            sonuc.update(eylem="cevapla", gerekce="şablon cevabı: bilgi penceresi açıldı", buton=reply_id)
        return {"satirlar": satirlar, "sonuc": sonuc}
    form = gelen.get("form") if isinstance(gelen.get("form"), dict) else None    # İE-20 PR-2: talep ya da revizyon formunun cevabı
    medya = gorsel_acik(settings) and (gelen.get("type") in GORSEL_TURLERI      # İE-20: çizim okunur (kalıcı akış dosyayı indirip okur)
                                       or (form is not None and form.get("tur") == "talep" and bool(form.get("dosyalar"))))
    if not medya and (gelen.get("type") not in GELEN_YAZILI or not ((gelen.get("text") or "").strip() or gelen.get("reply_id"))):
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
    fc = None; form_on = ""
    if form is not None:
        fc = (cikarim or {}).get("form") or form_cikarimi(gelen, k.d, giden_bul)
        if fc is not None and fc.get("durum") != "talep":
            return _form_cevabi(gelen, k, fc, sonuc, satirlar, ekle, patrona, kim)
        if fc is not None and medya:
            fc, medya, form_on, cikarim = _form_okumasi(fc, cikarim, gelen, patrona, kim)
        if fc is None:                                # revizyon formunun açıklaması okunur; dosyası Patron'a (işaretli plan otomatik okunmaz)
            if form.get("dosyalar"):
                patrona(f"Portman: {kim} revizyon formuna dosya ekledi; panelden bakabilirsiniz.")
        elif not medya:
            metin_kural = ""                          # formun özeti kural katmanına bayinin sözü diye gitmez
            if form.get("dosyalar") and not form_on:
                patrona(f"Portman: {kim} talep formuna dosya ekledi (çizim okuması kapalı); panelden bakabilirsiniz.")
            k.d.pop("cizim_okuma", None)              # formla gelen talep açık çizim okumasının yerine geçer
            if k.d.get("son_soru_alani") == "cizim_okuma":
                k.d["son_soru_alani"] = None
            # bayinin görmediği taslağa karışmaz: taslaktan doldurulmamış form (`taslaga` yok) açık taslağı kapatır; "Revize et" denmiş
            # plan ya da katalog kodlu taslak varken de form yeni talep
            if k.d.get("asama") == "revizyon" or (k.d.get("asama") == "topluyor" and (not fc.get("taslaga")
                                                                                     or (k.d.get("taslak") or {}).get("katalog_kodu"))):
                k.sifirla(); k.not_dus("kural", "talep formu: önceki taslak kapandı, formdaki talep yeni talep")
    etk = None
    if gelen.get("reply_id"):
        etk = (cikarim or {}).get("etkilesim") or ET.coz(gelen, k.d, giden_bul)
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
        elif fc is not None and not medya:            # İE-20 PR-2: talep formu, LLM'siz
            from beyin.sema import Talep
            talep, meta = Talep.model_validate(fc["talep"]), {"backend": "form", "tur": "talep"}
        elif medya:                                 # İE-20: okuma kalıcı akışta yapıldı (`gorsel_oku`); talep yalnız kayıt için
            from beyin.sema import Talep
            g = (cikarim or {}).get("gorsel") or {"durum": "dosya_yok"}
            if g.get("durum") == "hata":
                raise CikarimHatasi(f"çizim okunamadı: {g.get('hata')}")
            talep = Talep(niyet="yeni_talep", guven="orta", ozet="bayi çizim gönderdi")
            meta = {"backend": "gorsel", **{a: g.get(a) for a in ("model", "girdi_token", "cikti_token", "sure_ms", "cagri")}}
        elif cikarim is not None:
            if cikarim.get("hata"):
                raise CikarimHatasi(cikarim["hata"])
            from beyin.sema import Talep
            talep, meta = Talep.model_validate(cikarim["talep"]), dict(cikarim.get("meta") or {})
        else:
            talep, meta = cikar(gelen, settings, k)
    except Exception as e:
        hata = maske_numaralar(str(e))[:320] if isinstance(e, CikarimHatasi) else maske_numaralar(f"{type(e).__name__}: {str(e)}")[:300]
        ekle(("Çiziminizi şu an okuyamadım" if medya else "Mesajınızı şu an işleyemedim") + "; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
        patrona(f"Portman: {kim} " + ("çizimi okunamadı (okuma hatası); dosya panelde." if medya else "mesajı işlenemedi (çıkarım hatası).")
                + f" Mesaj: \"{maske_numaralar(gelen.get('text') or '')[:300]}\"", sablon=True)
        sonuc.update(eylem="hata", gerekce="çıkarım hatası", hata=hata)
        return {"satirlar": satirlar, "sonuc": sonuc, "hata": hata}

    d0 = _anlik(k.d)                               # İE-08 A4 "hak düşmez": çelik çizim düşerse konuşma bu duruma döner
    pu_kayit = None
    pu_ayar = settings.get("plan_uretimi") or {}
    k.plan_uretimi = bool(pu_ayar.get("acik"))       # İE-14 (D-18): kapalıysa uyan-yok dalı bugünkü davranış
    k.llm_golge = None
    son0 = k.d.get("son_is_emri") or {}
    son_y0 = son0.get("yapi") or {}                               # gölge kıyası karar öncesi açık plana karşı
    okuma_k = None
    gk = cizim_karari(gelen, settings, k, talep, etk, medya, cikarim, katalog, bayi, proje_koku, ek_kaydet)    # İE-20; None: bugünkü yol
    if gk is not None:
        karar, cizim_ek = gk
        sonuc["cizim_okuma"] = cizim_ek.get("kayit")
    else:
        cizim_ek = {}
        k.llm_yeni_plan, k.llm_degisiklik = llm_once_revizyon(k, talep, gelen, etk, cikarim, settings, katalog, ek_kaydet)
        for a, v in (("plan_duzenleme", k.llm_yeni_plan), ("llm_degisiklik", k.llm_degisiklik)):
            if v is not None:
                sonuc[a] = {b: v.get(b) for b in ("durum", "cagri", "girdi_token", "cikti_token", "hata")}
        karar = karar_ver(talep, k, bayi, katalog, metin=metin_kural)
        if getattr(k, "llm_golge", None) is not None:        # r3 P4: kararı etkilemez; kayıt (göç 008) ve iş sonucu
            from beyin import numara as _nm
            okuma_k = okuma_kiyasi(son_y0, _nm.maskele((gelen.get("text") or "").strip()), katalog, k.llm_golge)
            if okuma_k:
                okuma_k.update(is_emri_no=son0.get("is_emri_no"), rev=son0.get("revizyon"))     # okunan plan (inceleme C8), bu işin ürettiği değil
                sonuc["okuma_kiyasi"] = {"sinif": okuma_k["sinif"], "cagri": okuma_k["cagri"]}
    if karar.gerekce == PLAN_URETIMI and k.d.get("plan_istegi"):
        # İE-14: bayiye önce "hazırlıyorum", sonra üretim (LLM, en çok 3 çağrı; sonuç iş satırına yazılır, yeniden denenen iş çağırmaz),
        # yeni planın kartı ve seçenek seti (`karar.plan_sonucu`). Üretim düşerse "uygulayamadım" + Patron.
        erken = ara_gonder(karar.mesaj) if ara_gonder is not None else None   # kalıcı akış: üretimden önce yazılır, hemen gider (C7)
        if erken:
            satirlar.append({**erken, "erken": True})           # kayıtta; isi_bitir yinelemez, ajan sırası (1..n) değişmez
        else:
            ekle(karar.mesaj)
        plan_talep = k.d["plan_istegi"]["talep"]
        pu = (cikarim or {}).get("plan_uretimi")
        if pu is None:
            pu = plan_uret(k.d["plan_istegi"]["talep"], pu_ayar)
            if ek_kaydet is not None:
                ek_kaydet("plan_uretimi", pu)
        kartlar = []
        if pu.get("durum") == "gecerli":                    # r3: en çok 2 yeni plan; her birinin kartı ve doğrulama raporu (bayiye gitmez)
            for i, a in enumerate((pu.get("adaylar") or [pu])[:2]):
                kart = plan_karti(a.get("tanim"), gelen, proje_koku, i + 1)
                kartlar.append(kart)
                a["dogrulama"] = plan_dogrulamasi(a, kart)
        karar = plan_sonucu(k, katalog, pu, kartlar)
        sonuc["plan_uretimi"] = {a: pu.get(a) for a in ("durum", "cagri", "girdi_token", "cikti_token", "hata", "model", "yol", "puan", "sure_ms")}
        sonuc["plan_uretimi"]["adaylar"] = [{"yol": a.get("yol"), "puan": a.get("puan")} for a in pu.get("adaylar") or []]
        sonuc["plan_uretimi"]["basamaklar"] = [d.get("basamak") for d in pu.get("denemeler") or []]
        from beyin import plan_uretici as PU
        kodlar = [u["kod"] for u in k.d.get("uretilen_planlar") or []] if karar.eylem == "secenek" else []
        kayit = PU.kayit({"cagri": 0, "girdi_token": 0, "cikti_token": 0, **pu}, plan_talep, "kanal")
        for x, a, kod_ in zip(kayit["adaylar"], pu.get("adaylar") or [], kodlar + [None] * 2):
            x["kod"] = kod_
            x["dogrulama"] = a.get("dogrulama")
        pu_kayit = {**kayit, "plan_kodu": kodlar[0] if kodlar else None}                # göç 007 kaydı
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
        motor_adi, uret_fn = motor_sec(ie)                      # İE-08 (D-08): zarfın yapi.sistem'i motoru seçer; çağrı anında
        try:
            m = uret_fn(ie, hedef)
            v = oku(hedef / "validation.json", {}) or {}
            cizim = {"motor": motor_adi, "sure_s": round(time.time() - t0, 1), "passed": v.get("passed") is True and bool(m.get("pdf")),
                     "errors": [maske_numaralar(str(x)) for x in (v.get("errors") or [])[:5]],
                     "pdf": str(hedef / m["pdf"]) if m.get("pdf") else None, "dxf": str(hedef / m["dxf"]) if m.get("dxf") else None,
                     "pdf_sha256": m.get("pdf_sha256"), "dxf_sha256": m.get("dxf_sha256"), "warnings": m.get("warnings")}
            if motor_adi == "genel":                            # bayiye giden PDF adı prefabrikle aynı biçimde; kural seti ve perspektif kayda
                cizim["pdf_ad"] = f"Portman_{no}_r{rev:02d}.pdf"; cizim["set"] = Path(str(m.get("set") or "")).name or None
                cizim["perspektif"] = (v.get("perspektif") or {}).get("durum")
            if cizim["passed"] and settings.get("mesaj_katmani"):
                cizim["ekler"] = ekler_uret(ie, hedef, v, settings, m)   # İE-04: aynı İş Emri'nden bayi görseli, IFC ve 3D sayfası
        except Exception as e:
            hedef.mkdir(parents=True, exist_ok=True)
            yaz(hedef / "failure.json", {"traceback": maske_numaralar(traceback.format_exc()[-6000:]), "failed_at": int(time.time())})
            cizim = {"motor": motor_adi, "sure_s": round(time.time() - t0, 1), "passed": False, "errors": [maske_numaralar(f"{type(e).__name__}: {str(e)[:300]}")]}
        sonuc["is_emri_no"] = no; sonuc["revizyon"] = rev; sonuc["cizim"] = cizim
        if motor_adi == "genel" and not cizim["passed"]:
            return _cizim_hatasi(k, d0, karar, talep, meta, cizim, ie, settings, sonuc, satirlar, ekle, patrona, kim, patron_mu)
    metin = ("" if medya else form_on) + karar.mesaj           # çizim yolunda ön not ayrı satır (teyit mesajının gövdesi sınırlı)
    if form is not None:
        sonuc["form"] = {"tur": form.get("tur"), "durum": (fc or {}).get("durum") or "okundu", "dosya": len(form.get("dosyalar") or [])}
        if fc is not None and not medya and (fc.get("talep") or {}).get("ozel_istekler") and karar.eylem in ("is_emri", "secenek"):
            metin += "\n\n" + FORM_NOTU
    # PDF başlığındaki özet: soru düğmesinin cevabıysa ("kısa cevap: 2") talebin özeti (kapanış incelemesi 13.10)
    ozet_baslik = ((k.d.get("taslak") or {}).get("ozet") or "") if meta.get("tur") == "soru" else (talep.ozet or "")
    if karar.is_emri and ((karar.is_emri.get("yapi") or {}).get("bu_revizyon") or (karar.is_emri.get("talep") or {}).get("metin_koddan")):
        # BK-09 M1: çelikte değişiklik uygulandıysa; İE-14: yeni planda istek uygulanamadı ya da zaten vardı (bilgiyle yeniden çizim)
        ozet_baslik = (karar.is_emri.get("talep") or {}).get("metin") or ""          # LLM özeti değil, kodun okuması ("Uygulanan: …")
    if patron_mu:
        metin = metin.replace("Bu konuyu Lokman Bey'e iletiyorum; en kısa sürede dönüş yapılacak.", "Bu talep şu an otomatik karşılanamıyor (Patron modu: ayrıca bildirim gönderilmez).")
    teknik = teknik_not(karar, talep, meta, cizim) if (patron_mu and settings.get("patron_teknik_not", True)) else ""
    if teknik and not settings.get("mesaj_katmani"):
        metin += teknik; teknik = ""          # katman kapalı: v1.2 ile aynı tek metin
    # ── İE-04: satır türü karara göre; yalnız settings.mesaj_katmani açıkken (hosting v1.3). Kapalıyken bugünkü metin + PDF.
    # Metin yolu her zaman kalır (buton yalnız kısayoldur).
    katman = bool(settings.get("mesaj_katmani"))
    if medya and form_on:                         # İE-20 PR-2: formdaki not çizim yolunda otomatik işlenmez
        ekle(form_on)
    if cizim_ek.get("on_metin"):                  # İE-20: okumanın varsayımları gövdeye sığmadı; düğmeli mesajdan önce ayrı metin
        ekle(cizim_ek["on_metin"])
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
        kart_son_yeri(k, proje_koku)
        sonuc["secenek_seti"] = {"id": karar.secenek_seti["id"], "adaylar": [a["kod"] for a in karar.secenek_seti["adaylar"]]}
    elif cizim and cizim["passed"] and not katman:
        ekle(ek_sozu(metin, gorsel_var=False))
        ad = cizim.get("pdf_ad") or Path(cizim["pdf"]).name
        ekle_satir(giden_belge(gelen, Path(cizim["pdf"]), ad, f"{sonuc['is_emri_no']} r{sonuc['revizyon']:02d} · ÖN ONAYA SUNULAN TASLAK · {ozet_baslik}".strip(),
                               0, sonuc["is_emri_no"], sonuc["revizyon"], cizim["pdf_sha256"]))
    elif cizim and cizim["passed"]:
        ekler = cizim.get("ekler") or {}
        no, rev = sonuc["is_emri_no"], sonuc["revizyon"]
        gorsel = ekler.get("gorsel")
        ekle_satir(giden_etkilesim(gelen, ek_sozu(metin, gorsel_var=bool(gorsel)), 0, butonlar=[(f"o:{no}:{rev}", "Onayla"), (f"r:{no}:{rev}", "Revize et")],
                                   gorsel=gorsel, altbilgi=f"{no} r{rev:02d}", is_emri_no=no, revizyon=rev))
        ad = cizim.get("pdf_ad") or Path(cizim["pdf"]).name
        ekle_satir(giden_belge(gelen, Path(cizim["pdf"]), ad, f"{no} r{rev:02d} · ÖN ONAYA SUNULAN TASLAK · {ozet_baslik}".strip(),
                               0, no, rev, cizim["pdf_sha256"]))
        ucb = ekler.get("ucb")
        if ucb and ucb.get("url"):                  # İE-21: rehberin "3D'yi aç" düğmesi (metin kanal/sablonlar.py)
            import sablonlar as S
            ekle_satir(giden_etkilesim(gelen, S.ucb_metni(no, rev), 0, baglanti={"metin": S.UCB_DUGME, "url": ucb["url"]},
                                       tur="cevap", is_emri_no=no, revizyon=rev))
        # ucb_taban_url boşsa ya da yayın dizini yoksa 3D sayfası yalnız kayıtta (revizyonlar.ekler) durur; bayiye söz veren mesaj gönderilmez
    elif butonlar and karar.soru_alani == "okuma" and len((k.d.get("okuma_bekleyen") or {}).get("adaylar") or []) == 2:
        # İE-08 A4: "1 / 2 / Hiçbiri" — iki okuma tek görselde numaralı (görsel üretilemezse düğmeler metinle gider; akış durmaz).
        # "Görselde işaretledim" cümlesi yalnız görsel gerçekten giderse (kapanış incelemesi 13.10)
        g = okuma_gorseli(gelen, k.d["okuma_bekleyen"], proje_koku)
        ekle_satir(giden_etkilesim(gelen, metin + (" Görselde 1 ve 2 ile işaretledim." if g else ""), 0, butonlar=butonlar, gorsel=g,
                                   altbilgi="1, 2 ya da Hiçbiri"))
    elif cizim_ek.get("gorsel") and butonlar:                  # İE-20: okunan yerleşimin görseli + [Doğru] [Düzelt]
        ekle_satir(giden_etkilesim(gelen, metin, 0, butonlar=butonlar, gorsel=cizim_ek["gorsel"], altbilgi="Düğmeyle ya da yazarak cevaplayın"))
    elif cizim_ek.get("gorsel") and katman:                     # İE-20: soru ya da çizilemezlik: görsel + altyazı
        g = cizim_ek["gorsel"]
        ekle_satir(giden_gorsel(gelen, Path(g["file"]), g["filename"], metin, 0, g["sha256"]))
    elif butonlar:
        ekle_satir(giden_etkilesim(gelen, metin, 0, butonlar=butonlar))
    elif katman and (fs := form_sunusu(gelen, karar, k, bayi, settings, metin)) is not None:     # İE-20 PR-2: aynı metin + form düğmesi
        ekle_satir(giden_form(gelen, metin, 0, fs[0], settings, fs[1], fs[2], is_emri_no=fs[3], revizyon=fs[4]))
        sonuc["form_sunuldu"] = fs[0]
    else:
        ekle(metin)
    if cizim_ek.get("patrona"):
        patrona(cizim_ek["patrona"])
    if teknik:
        ekle(teknik.strip())
    if cizim and not cizim["passed"]:
        ekle("Ön onay planı otomatik doğrulamadan geçmedi; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
        patrona(f"Portman: {kim} için {sonuc['is_emri_no']} çizimi doğrulamadan geçmedi: {'; '.join(cizim['errors'])[:400]}")
    from beyin.karar import KURALA_UYMADI
    if KURALA_UYMADI in (karar.gerekce or "") and karar.eylem != "yonlendir":
        # Lokman 16.10 (canlı deneme G): kurallara uymayan istek konuşmayı kapatmaz; bayi planı onaylayabilir, Patron elle yardım için bilgilenir.
        # Kararın yoluna bağlı (geometri hakemi: LLM sonucuna bakmak, karar yeni plan dalına girmese de bilgi gönderiyordu; kısmi başarı kapsam dışı)
        patrona(f"Portman bilgi: {kim} — yeni plan revizyonunda kurallara uymayan istek otomatik uygulanmadı; konuşma açık, plan onaylanabilir. "
                f"Mesaj: \"{maske_numaralar(gelen.get('text') or '')[:300]}\"", sablon=True, is_emri_no=sonuc.get("is_emri_no"))
    if karar.eylem == "yonlendir":
        model = katalog.bul(talep.katalog_kodu) if talep.katalog_kodu else None
        model_notu = f" Katalog notu ({model['code']}): {model['not']}" if model and model.get("not") else ""   # D-07: yalnız Patron'a
        patrona(f"Portman yönlendirme: {kim} — {karar.gerekce}.{model_notu} Mesaj: \"{maske_numaralar(gelen.get('text') or '')[:300]}\"",
                sablon=True, is_emri_no=sonuc.get("is_emri_no"))
    return {"satirlar": satirlar, "sonuc": sonuc, **({"plan_uretimi": pu_kayit} if pu_kayit else {}),
            **({"okuma_kiyasi": okuma_k} if okuma_k else {})}


def _form_cevabi(gelen: dict, k, fc: dict, sonuc: dict, satirlar: list, ekle, patrona, kim: str) -> dict:
    """İE-20 PR-2: LLM'siz form cevabı (eski ya da tanınmayan form, boş ya da yalnız dosyalı revizyon formu). Plan değişmez."""
    k.not_dus("gelen", f"form: {(gelen.get('form') or {}).get('tur')}", {"niyet": "form", "guven": "yuksek"})
    if fc["durum"] in ("bos", "dosya"):
        k.d["son_soru_alani"] = "revizyon_ne"          # bayinin yazısı revizyon olarak okunur (bugünkü yol)
    k.not_dus("giden", fc["mesaj"], {"eylem": "sor" if fc["durum"] in ("bos", "dosya") else "cevapla", "gerekce": f"form: {fc['durum']}"})
    k.kaydet()
    ekle(fc["mesaj"])
    if fc["durum"] == "dosya":
        patrona(f"Portman: {kim} revizyon formuna dosya ekledi ({fc.get('no')} r{int(fc.get('rev') or 0):02d}); panelden bakabilirsiniz.")
    sonuc.update(eylem="sor" if fc["durum"] in ("bos", "dosya") else "cevapla", gerekce=f"form: {fc['durum']}", asama=k.d.get("asama"),
                 form={"tur": (gelen.get("form") or {}).get("tur"), "durum": fc["durum"], "dosya": len((gelen.get("form") or {}).get("dosyalar") or [])})
    return {"satirlar": satirlar, "sonuc": sonuc}


def _form_okumasi(fc: dict, cikarim: dict | None, gelen: dict, patrona, kim: str) -> tuple:
    """Talep formunun dosyası okunduysa: plan okunduysa çizim yolu (çizim esas; okumanın boş bıraktığı yapı tipi ve kat formdan, not
    otomatik işlenmez: ön not ayrı satır); okunamadıysa (plan değil, dosya inmedi, türü okunmuyor, okuma hatası) formun bilgileriyle
    devam. Dönen: (fc, medya, ön not, cikarim)."""
    g = (cikarim or {}).get("gorsel") or {"durum": "dosya_yok"}
    o = g.get("okuma") or {}
    if g.get("durum") == "tamam" and o.get("tur") == "plan":
        t = fc.get("talep") or {}
        o = {**o, **{a: t[a] for a in ("yapi_turu", "kat_sayisi") if t.get(a) and not o.get(a)}}
        return fc, True, FORM_NOTU_CIZIM if t.get("ozel_istekler") else "", {**(cikarim or {}), "gorsel": {**g, "okuma": o}}
    if g.get("durum") != "tamam":
        patrona(f"Portman: {kim} talep formuna dosya ekledi ama okunamadı ({g.get('durum')}); panelden bakabilirsiniz.")
    return fc, False, "Formdaki dosyadan plan çıkaramadım; formdaki bilgilerle devam ediyorum. ", cikarim


def _cizim_hatasi(k, d0: dict, karar, talep, meta: dict, cizim: dict, ie: dict, settings: dict, sonuc: dict, satirlar: list, ekle, patrona,
                  kim: str, patron_mu: bool) -> dict:
    """İE-08 A4 · "hak düşmez" (Lokman, 12.10.2026): çelik çizim üretilemezse (istisna ya da doğrulama) konuşma karar öncesine döner
    (revizyon sayacı, taslak, askıdaki soru, seçenek seti); `revizyonlar`'a satır yazılmaz (`eylem cizim_hatasi`; `depo._isi_bitir` yalnız
    `is_emri`de yazar), eski planın Onayla/Revize et düğmeleri geçerli kalır. Bayiye önceki planın geçerli olduğu söylenir, Patron'a metin +
    şablon. `isler.sonuc`'a zarfın yalnız yapısı yazılır (antet `bilgi` yok: D-09). Prefabrik (pano Motor'u) bugünkü davranışta kalır (A5)."""
    no, rev = ie.get("is_emri_no"), int(ie.get("revizyon") or 1)
    k.d = _geri_al(d0, k.d)
    if hasattr(k, "yeni_notlar"):                   # bu işin notları geri alınan değişikliğe aitti (soru kaydı onları okumasın)
        k.yeni_notlar = []; k.sifirlandi = False
    onceki = k.d.get("son_is_emri") or {}
    if onceki.get("is_emri_no") and k.d.get("asama") == "topluyor":
        # mesaj bir soruyu cevaplıyordu (aşama "topluyor"): bayiye "önceki planınız geçerli" denir, o planın düğmeleri de çalışmalı
        # (kapanış incelemesi 13.10: Onayla "onay beklenmiyor" diyordu). Askıdaki soru ve saklanan istek kapanır.
        k.d["asama"] = "onay_bekliyor"; k.d["son_soru_alani"] = None; k.d["bekleyen_onay"] = onceki["is_emri_no"]
        for a in ("okuma_bekleyen", "okuma_secilen", "celik_istek"):
            k.d.pop(a, None)
    k.not_dus("kural", f"çelik çizim üretilemedi ({no} r{rev:02d}); konuşma önceki duruma döndü, revizyon hakkı düşmedi")
    k.kaydet()
    if onceki.get("is_emri_no"):
        mesaj = (f"Çizimi şu an üretemedim; önceki planınız ({onceki['is_emri_no']} r{int(onceki.get('revizyon') or 1):02d}) geçerli: onaylayabilir "
                 "ya da değişikliği yeniden isteyebilirsiniz, revizyon hakkınız düşmedi. Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
    else:
        mesaj = "Çizimi şu an üretemedim; talebiniz duruyor, revizyon hakkınız düşmedi. Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak."
    if patron_mu:
        mesaj = mesaj.replace(" Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.", " (Patron modu: ayrıca bildirim gönderilmez.)")
    ekle(mesaj)
    if patron_mu and settings.get("patron_teknik_not", True):
        ekle(teknik_not(karar, talep, meta, cizim).strip())
    patrona(f"Portman: {kim} için {no} r{rev:02d} çelik çizimi üretilemedi; konuşma önceki planda, revizyon hakkı düşmedi: "
            f"{'; '.join(cizim.get('errors') or [])[:300]}", sablon=True, is_emri_no=no)
    y = ie.get("yapi") or {}
    sonuc.update(eylem="cizim_hatasi", gerekce="çelik çizim üretilemedi; hak düşmez (konuşma önceki duruma döndü)", asama=k.d.get("asama"),
                 denenen={"is_emri_no": no, "revizyon": rev, "yapi": {a: y.get(a) for a in ("kod", "tanim", "tanim_sha256", "degisiklikler", "bu_revizyon")}})
    return {"satirlar": satirlar, "sonuc": sonuc}


def _anlik(d: dict) -> dict:
    """Konuşmanın karar öncesi anlık görüntüsü ("hak düşmez" için). Geçmiş (en çok 40 not, `Konusma.not_dus`) yalnız sığ kopyalanır: notlar
    sonradan değişmez, yalnız eklenir (kod incelemesi 13.10: her mesajda bütün durumu JSON'la çoğaltmak gereksizdi). Sığ kopya geri almada
    geçmişi tam verir (KVKK ikinci tur: uzunlukla kesmek, 40'ta dolu geçmişte bu işin notlarını değil en eskileri düşürüyordu)."""
    return {"_gecmis": list(d.get("gecmis") or []), **json.loads(json.dumps({a: b for a, b in d.items() if a != "gecmis"}))}


def _geri_al(anlik: dict, simdiki: dict) -> dict:
    d = {a: b for a, b in anlik.items() if a != "_gecmis"}
    d["gecmis"] = list(anlik.get("_gecmis") or [])
    return d


def _cizim_tanimi(yol_veya_tanim, degisiklikler: list[dict] | None) -> dict:
    """Model tanımı (`modeller/<kod>.json` ya da İE-14'te gömülü sözlük) + sırayla uygulanmış değişiklikler (`beyin/varyant.tanim_uygula`)."""
    from beyin import varyant
    t = json.loads(json.dumps(yol_veya_tanim)) if isinstance(yol_veya_tanim, dict) else \
        json.loads((KOD.parent / str(yol_veya_tanim)).read_text(encoding="utf-8"))
    for d in degisiklikler or []:
        t = varyant.tanim_uygula(t, d)
    return t


def okuma_gorseli(gelen: dict, ob: dict, proje_koku: Path | None) -> dict | None:
    """İE-08 A4: iki okumalı "1 / 2 / Hiçbiri" sorusunun başlık görseli (`motor/genel/okuma_gorseli.okumalar`); üretilemezse None."""
    try:
        from motor.genel import okuma_gorseli as OG
        t = _cizim_tanimi(ob["tanim"], ob.get("degisiklikler"))
        kok = (Path(proje_koku) if proje_koku else KANAL / "projects") / f"OKUMA-{satir_id(gelen['id'], 0)[4:16]}" / "r01"
        from motor.genel.uret import kod_govde
        yol = OG.okumalar(t, ob["adaylar"], kok, kod_govde(t), olcu=ob.get("olcu"))
        return {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png"}
    except Exception as e:
        log("okuma görseli üretilemedi:", maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
        return None


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
        celik = any(a.get("motor") == "genel" for a in adaylar)      # İE-08: çelik kartı (plan + çatı planı + perspektif) daha geniş panelde okunur
        yol = BG.bilesik_gorsel([{**a, "gorsel_yolu": (KT_KOK() / a["gorsel"]) if a.get("gorsel") else None} for a in adaylar[:SC.EN_COK_GORSEL]],
                                kok / "secenekler.png", baslik=f"{gelen.get('text') or ''}"[:60], panel_px=600 if celik else 460)
        if yol:
            gorsel = {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png"}
    except Exception as e:      # görsel üretilemezse metinli buton mesajı gider; akış durmaz
        log("seçenek görseli üretilemedi:", maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
    rows = [giden_etkilesim(gelen, metin, 0, butonlar=butonlar, gorsel=gorsel, altbilgi="Butonla ya da yazarak seçin")]
    if len(adaylar) > len(butonlar):
        from beyin import secenek as SC
        liste = {"dugme": "Tüm seçenekler", "bolumler": [{"baslik": "Puana göre", "satirlar": [
            {"id": f"s:{st['id']}:{a['kod']}", "baslik": SC.kisa_ad(a), "aciklama": SC.aciklama(a)} for a in adaylar]}]}
        rows.append(giden_etkilesim(gelen, f"{len(adaylar)} seçeneğin tamamı, puanlarıyla listede.", 0, liste=liste))
    return rows


# ───────────────────────── İE-20 PR-2: talep formu ve revizyon formu (WhatsApp Flow) ─────────────────────────
FORM_SORULARI = ("oda_programi", "dis_olcu", "model_veya_olcu")      # eksik bilgi sorusu: aynı metin + [Talep formu]
FORM_CEVAPLARI = ("selam", "anlaşılmadı")                            # karşılık: "hangi model ya da ölçü?" metni + [Talep formu]
FORM_NOTU = "Formdaki notunuz plana özel istek olarak yazıldı; planı değiştirmesi gereken bir istekse planı gördükten sonra yazın."
FORM_NOTU_CIZIM = "Çiziminizi esas aldım; formdaki notunuz plana otomatik işlenmez, planı gördükten sonra değişiklik olarak yazabilirsiniz."
NASIL_TALEP = "Talebinizi bu sohbete yazabilirsiniz; örnek: \"Tek kat çelik, 2+1, 88 m² civarı, beşik çatı.\""


def form_kimligi(settings: dict, tur: str) -> str | None:
    """Sunulacak formun Meta kimliği (`talep_formu.<tur>_flow_id`); form kapalıysa, kimlik yoksa ya da mesaj katmanı kapalıysa None
    (bugünkü metin gider)."""
    import talep_formu as TF
    a = settings.get("talep_formu") or {}
    fid = str(a.get(f"{tur}_flow_id") or "")
    return fid if a.get("acik") is True and settings.get("mesaj_katmani") and TF.FLOW_ID.match(fid) else None


def giden_form(gelen: dict, metin: str, sira: int, tur: str, settings: dict, token: str, veri: dict, is_emri_no: str | None = None,
               revizyon: int | None = None) -> dict:
    """Formu açan düğmeli mesaj (Flow; gövde sorunun metni, satır sonları korunur). `form_kimligi` None değilken çağrılır; gövdeye
    (1024) sığmayan metin formla sunulmaz (`form_sunusu`)."""
    import talep_formu as TF
    govde = metin.strip()[:WA_GOVDE]
    r = giden_metin(gelen, govde, sira)
    i = TF.etkilesim(tur, govde, form_kimligi(settings, tur), token, veri, (settings.get("talep_formu") or {}).get("taslak", True) is not False)
    r.update(kind="interactive", interactive=i, is_emri_no=is_emri_no, revizyon=revizyon)
    return r


def _form_plani(d: dict | None) -> tuple[str, int]:
    """Revizyon formunun planı: (İş Emri no, revizyon); sunuş ve çözüm aynı yerden okur."""
    ie = (d or {}).get("son_is_emri") or {}
    return str(ie.get("is_emri_no") or ""), int(ie.get("revizyon") or 1)


def form_sunusu(gelen: dict, karar, k, bayi: dict | None, settings: dict, metin: str = "") -> tuple | None:
    """Bu cevap formla mı gitsin: (tur, token, veri, is_emri_no, rev) ya da None. Eksik bilgi sorusu, selam ve "anlayamadım" → talep formu
    (açık taslağın bilgileri ve kartın varsayılanları seçili); "Neyi değiştirelim?" → revizyon formu (planın numarası). Gövdeye sığmayan
    metin formla gitmez (bugünkü düz metin, kesilmez)."""
    import talep_formu as TF
    if len(metin.strip()) > WA_GOVDE:
        return None
    no, rev = _form_plani(k.d)
    if karar.soru_alani == "revizyon_ne" and karar.eylem == "sor" and no and form_kimligi(settings, "revizyon"):
        return ("revizyon", TF.revizyon_tokeni(no, rev), {"plan": f"{no} r{rev:02d} planı için değişikliğinizi yazın; isterseniz dosya da ekleyin."},
                no, rev)
    if ((karar.eylem == "sor" and karar.soru_alani in FORM_SORULARI) or (karar.eylem == "cevapla" and karar.gerekce in FORM_CEVAPLARI)) \
            and form_kimligi(settings, "talep"):
        taslak = (k.d.get("taslak") if k.d.get("asama") == "topluyor" else None) or None
        return "talep", TF.talep_tokeni(satir_id(gelen["id"], 0)[4:16], taslaktan=taslak is not None), TF.ekran_verisi(bayi, taslak), None, None
    return None


def form_cikarimi(gelen: dict, d: dict | None, giden_bul=None) -> dict | None:
    """Form cevabının LLM'siz çözümü (kalıcı akışta işten önce; iş satırına yazılır). None: revizyon formunun açıklaması bayinin yazısı
    gibi okunacak (bugünkü yol, LLM). Dönen `durum`: talep (talep formu → Talep) | eski | bilinmiyor | bos | dosya (LLM'siz cevap, `mesaj`)."""
    import talep_formu as TF
    oz = gelen.get("form") or {}
    d = d or {}
    ctx = gelen.get("context_id")
    satir = giden_bul(ctx) if ctx and giden_bul is not None else None
    if oz.get("tur") not in ("talep", "revizyon") or (satir is not None and TF.satir_tokeni(satir) != oz.get("token")):
        return {"durum": "bilinmiyor", "mesaj": "Bu formu tanıyamadım; isteğinizi yazarak iletirseniz devam ederim."}
    m = TF.TOKEN.match(oz.get("token") or "")
    if oz["tur"] == "talep":                       # `taslaga`: form açık taslağın bilgileriyle dolu sunulmuştu (token `:1`)
        return {"durum": "talep", "talep": TF.talep(oz), "dosya": bool(oz.get("dosyalar")), "taslaga": bool(m and m.group(3) == "1")}
    no, rev = m.group(2), int(m.group(3) or 0)
    guncel = _form_plani(d)
    if (no, rev) != guncel or d.get("asama") not in ("onay_bekliyor", "revizyon"):
        return {"durum": "eski", "no": no, "rev": rev,
                "mesaj": f"Bu form {no} r{rev:02d} planına ait; " + (f"güncel plan {guncel[0]} r{guncel[1]:02d}. " if guncel[0] else "şu an açık bir plan yok. ")
                         + "Değişikliği yazarak iletirseniz devam ederim."}
    if (oz.get("alanlar") or {}).get("aciklama"):
        return None
    if oz.get("dosyalar"):
        return {"durum": "dosya", "no": no, "rev": rev,
                "mesaj": "Dosyanızı Lokman Bey'e ilettim. Değişikliği kısaca yazarsanız (örn. \"mutfak penceresi 120x120\") planı hemen güncellerim."}
    return {"durum": "bos", "no": no, "rev": rev,
            "mesaj": "Neyi nasıl değiştirelim? Kısaca yazmanız yeterli; örneğin \"mutfak penceresi 120x120\" ya da \"veranda arkada olsun\"."}


def form_dosyasi_okunur(cikarim: dict | None, settings: dict) -> bool:
    """Talep formunun dosyası PR-1'in okumasından geçer mi (görsel okuma açıkken)."""
    fc = (cikarim or {}).get("form") or {}
    return fc.get("durum") == "talep" and bool(fc.get("dosya")) and gorsel_acik(settings)


# ───────────────────────── İE-20: görsel ve PDF ile talep ─────────────────────────
def gorsel_ayari(settings: dict) -> dict:
    """`gorsel_okuma` ayarı: {acik, backend, model, effort, timeout_s, max_tokens, bekle_sn, hazir_dosya (yalnız manuel), eşikler}."""
    return dict(settings.get("gorsel_okuma") or {})


def gorsel_acik(settings: dict) -> bool:
    return gorsel_ayari(settings).get("acik") is True


def _esik(settings: dict) -> dict:
    """Ayardaki denetim eşikleri (`gorsel_okuma.ESIK` anahtarları); yazmayan eşik varsayılanından."""
    from beyin import gorsel_okuma as GO
    return {a: v for a, v in gorsel_ayari(settings).items() if a in GO.ESIK}


def _llm_ayari(ayar: dict) -> dict:
    return {a: ayar[a] for a in ("backend", "model", "effort", "timeout_s", "max_tokens") if a in ayar}


def _dosya_bilgisi(dosya: dict) -> dict:
    return {"yol": str(dosya.get("yol")), "mime": (str(dosya.get("mime") or "").split(";")[0].strip().lower() or None),
            "boyut": dosya.get("boyut"), "sha256": dosya.get("sha256")}


def gorsel_oku(gelen: dict, settings: dict, dosya: dict | None) -> dict:
    """İE-20 (kalıcı akış, işten önce; `kalici.bir_is`): indirilen dosyayı okur (LLM, 1 çağrı; LLM yalnız okur). Sonuç iş satırına yazılır,
    yeniden denenen iş çağırmaz. `dosya`: gelen dosya kaydı ({yol, mime, boyut, sha256}) ya da None (indirilemedi). İstisna fırlatmaz.
    Dönen `durum`: tamam | hata | dosya_yok | desteklenmiyor."""
    from beyin import gorsel_okuma as GO
    if not dosya or not dosya.get("yol") or not Path(str(dosya["yol"])).is_file():
        return {"durum": "dosya_yok"}
    bilgi = _dosya_bilgisi(dosya)
    neden = GO.okunabilir_mi(bilgi["mime"], bilgi["boyut"])
    if neden:
        return {"durum": "desteklenmiyor", "neden": neden, "dosya": bilgi}
    ayar = gorsel_ayari(settings)
    try:
        h = _hazir(ayar)
        soz = gelen.get("text") or ""
        if isinstance(gelen.get("form"), dict):            # İE-20 PR-2: formun özeti bayinin sözü; not okumaya (LLM'e) gitmez
            import talep_formu as TF
            soz = TF.ozet(gelen["form"])
        s = GO.oku(Path(bilgi["yol"]), bilgi["mime"], soz, ayar=_llm_ayari(ayar),
                   hazir=(h.get("okuma", h) if isinstance(h, dict) else None))
    except Exception as e:
        s = {"durum": "hata", "okuma": None, "cagri": 0, "hata": maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")}
    log("çizim okuma:", s.get("durum"), "çağrı", s.get("cagri"))
    return {**s, "dosya": bilgi}


def gorsel_duzelt(co: dict, metin: str, settings: dict, revizyon: bool = False) -> dict:
    """İE-20: bayinin düzeltmesi ya da çizilmiş planın revizyonu (LLM, 1 çağrı): önceki okuma + bayinin sözü → yeni okuma. İstisna fırlatmaz."""
    from beyin import gorsel_okuma as GO, numara
    ayar = gorsel_ayari(settings)
    try:
        h = _hazir(ayar)
        d = co.get("dosya") or {}
        s = GO.duzelt(co["okuma"], numara.maskele(metin), sorulanlar=co.get("sorular"), yol=Path(d["yol"]) if d.get("yol") else None,
                      mime=d.get("mime"), ayar=_llm_ayari(ayar), hazir=(h.get("duzeltme", h) if isinstance(h, dict) else None), revizyon=revizyon)
    except Exception as e:
        s = {"durum": "hata", "niyet": None, "okuma": None, "degisenler": [], "cagri": 0,
             "hata": maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")}
    log("çizim düzeltme:", s.get("durum"), s.get("niyet"), "çağrı", s.get("cagri"))
    return s


def _cizim_gorseli(gelen: dict, okuma: dict, den: dict, proje_koku: Path | None) -> dict | None:
    """Okunan yerleşimin görseli (`beyin/gorsel_okuma.yerlesim_gorseli`); üretilemezse None (mesaj görselsiz gider, akış durmaz)."""
    try:
        from beyin import gorsel_okuma as GO
        kok = (Path(proje_koku) if proje_koku else KANAL / "projects") / f"CIZIM-{satir_id(gelen['id'], 0)[4:16]}" / "r01"
        yol = GO.yerlesim_gorseli(okuma, den, kok / "okunan_yerlesim.png")
        return {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png"}
    except Exception as e:
        log("okuma görseli üretilemedi:", maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
        return None


def _okuma_kaydi(g: dict) -> dict:
    """İş sonucuna (kayıt) giden okuma özeti: okumanın kendisi konuşmada; burada çağrı ve sayılar."""
    return {a: g.get(a) for a in ("durum", "niyet", "cagri", "girdi_token", "cikti_token", "model", "hata") if g.get(a) is not None}


def cizim_karari(gelen: dict, settings: dict, k, talep, etk, medya: bool, cikarim: dict | None, katalog, bayi: dict | None,
                 proje_koku: Path | None, ek_kaydet) -> tuple | None:
    """İE-20 · çizim okuma yolu. None: bugünkü yol (karar_ver). Yoksa (Karar, ek): ek = {gorsel (okuma görseli başlığı), patrona, kayit}.
    Durum konuşmada `cizim_okuma` = {iz, durum (teyit | soru | duzeltme | cizildi | devredildi), okuma, sorular, dosya, mesaj_id, revizyon}.
      - medya: okunan → kod denetimi → teyit [Doğru] [Düzelt] (`c:<iz>:d|z`), soru (emin olunamayanlar) ya da çizilemez (Patron'a)
      - [Doğru] (ya da teyit beklerken "doğru/onaylıyorum") → plan: prefabrikte İş Emri (`karar._is_emri_uret`), çelikte İE-14 yolu
      - [Düzelt] → "neyi düzelteyim?"; teyit ya da soru beklerken yazı → düzeltme (LLM okur, kod yeniden denetler)
      - okumadan çizilmiş prefabrik planın revizyonu (yazı) → okuma güncellenir, kod denetler, plan yeniden çizilir (değişen bayiye)."""
    from beyin import karar as KR, gorsel_okuma as GO
    co = k.d.get("cizim_okuma")
    if medya:
        return _cizim_medya(gelen, settings, k, (cikarim or {}).get("gorsel") or {"durum": "dosya_yok"}, bayi, proje_koku)
    if not gorsel_acik(settings):          # ayar kapandı: açık okuma kapanır, yazı bugünkü yoldan; LLM'le düzeltme ve çizim yok (G7)
        if co:
            k.d.pop("cizim_okuma", None)
            if k.d.get("son_soru_alani") == "cizim_okuma":
                k.d["son_soru_alani"] = None
        if etk is not None and etk.get("tur") == "cizim":
            k.not_dus("gelen", f"buton {etk.get('kimlik')}", {"niyet": "buton", "guven": "yuksek"})
            return KR._bitir(k, KR.Karar(eylem="cevapla", gerekce="çizim okuması kapalı",
                                         mesaj="Çizimden talep şu an kapalı. Talebinizi yazıyla iletirseniz (örn. \"7x4 m, 2+1, ön verandalı\") "
                                               "ön onay planını hazırlarım.")), {}
        return None
    if etk is not None and etk.get("tur") == "cizim":
        if etk.get("secim") == "d":
            return _cizim_plani(gelen, settings, k, katalog, bayi, proje_koku)
        co["durum"] = "duzeltme"
        k.d["son_soru_alani"] = "cizim_okuma"
        k.not_dus("gelen", "çizim okuması: düzelt", {"niyet": "buton", "guven": "yuksek"})
        return KR._bitir(k, KR.Karar(eylem="sor", soru_alani="cizim_okuma", gerekce="çizim okuması: düzeltme istendi",
                                     mesaj="Neyi düzelteyim? Yazmanız yeterli; örneğin \"salon 20 m²\", \"mutfak penceresi 120x120\" ya da "
                                           "\"veranda arkada değil, solda\".")), {}
    if etk is not None or not co or not (gelen.get("text") or "").strip():
        return None
    son = k.d.get("son_is_emri") or {}
    okumadan = (son.get("talep") or {}).get("kaynak") == GO.KAYNAK and (son.get("yapi") or {}).get("sistem") == "prefabrik"
    if co.get("durum") in ("teyit", "soru", "duzeltme"):
        if talep.niyet == "onay" and (co["durum"] == "teyit" or (co["durum"] == "duzeltme" and not co.get("sorular"))):
            return _cizim_plani(gelen, settings, k, katalog, bayi, proje_koku)     # [Düzelt]'den sonra "doğru": okuma yeniden denetlenir
        if talep.niyet in ("selam", "soru") or (talep.niyet == "yeni_talep" and talep.katalog_kodu):
            if talep.niyet == "yeni_talep":                    # başka bir talep: okuma kapanır, mesaj bugünkü yoldan
                k.d.pop("cizim_okuma", None); k.d["son_soru_alani"] = None
            return None
        return _cizim_duzeltme(gelen, settings, k, talep, cikarim, katalog, bayi, proje_koku, ek_kaydet, revizyon=bool(co.get("revizyon")))
    if co.get("durum") == "cizildi" and okumadan and k.d.get("asama") in ("onay_bekliyor", "revizyon") \
            and (talep.niyet == "revizyon" or (k.d.get("asama") == "revizyon" and talep.niyet in ("diger", "red", "yeni_talep")
                                               and not talep.katalog_kodu)):
        from beyin.konusma import MAX_REVIZYON
        if int(k.d.get("revizyon") or 0) + 1 > MAX_REVIZYON:
            return None                                         # hak doldu: bugünkü yol (karar) yönlendirir
        return _cizim_duzeltme(gelen, settings, k, talep, cikarim, katalog, bayi, proje_koku, ek_kaydet, revizyon=True)
    return None


def _cizim_sonucu(gelen: dict, settings: dict, k, okuma: dict, dosya: dict | None, bayi, proje_koku: Path | None, mesaj_id: str,
                  bas: str = "", revizyon: bool = False, kayit: dict | None = None) -> tuple:
    """Okuma → kod denetimi → bayiye teyit, soru ya da çizilemez (görseliyle). Konuşmaya `cizim_okuma` yazılır."""
    from beyin import karar as KR, gorsel_okuma as GO
    den = GO.denetle(okuma, ayar=_esik(settings))
    iz = hashlib.sha256(f"{mesaj_id}|{json.dumps(okuma, sort_keys=True)}".encode()).hexdigest()[:10]
    gorsel = _cizim_gorseli(gelen, okuma, den, proje_koku) if settings.get("mesaj_katmani") and den.get("kanonik") and (den["kanonik"] or {}).get("W") else None
    co = {"iz": iz, "okuma": okuma, "sorular": list(den["sorular"]), "dosya": dosya, "mesaj_id": mesaj_id, "revizyon": revizyon,
          "zaman": int(time.time())}
    k.d["cizim_okuma"] = co
    ek = {"gorsel": gorsel, "kayit": {**(kayit or {}), "iz": iz, "sorular": len(den["sorular"]), "cizilemez": list(den["cizilemez"])}}
    if den["cizilemez"]:
        co["durum"] = "devredildi"
        k.d["son_soru_alani"] = None
        mesaj, ek["on_metin"] = GO.cizilemez_metni(okuma, den, on=bas, ek=" " + KR.YONLENDIRME)
        return KR._bitir(k, KR.Karar(eylem="yonlendir", gerekce="çizim okundu, otomatik çizilemez: " + "; ".join(den["cizilemez"])[:200],
                                     mesaj=mesaj)), ek
    if den["sorular"]:
        co["durum"] = "soru"
        k.d["son_soru_alani"] = "cizim_okuma"
        mesaj, ek["on_metin"] = GO.soru_metni(okuma, den, gorsel_var=gorsel is not None, on=bas)
        return KR._bitir(k, KR.Karar(eylem="sor", soru_alani="cizim_okuma", gerekce=f"çizim okuması: {len(den['sorular'])} soru",
                                     mesaj=mesaj)), ek
    co["durum"] = "teyit"
    k.d["son_soru_alani"] = "cizim_okuma"
    butonlar = [{"id": f"c:{iz}:d", "baslik": "Doğru"}, {"id": f"c:{iz}:z", "baslik": "Düzelt"}]
    mesaj, ek["on_metin"] = GO.teyit_metni(okuma, den, gorsel_var=gorsel is not None, on=bas)
    return KR._bitir(k, KR.Karar(eylem="sor", soru_alani="cizim_okuma", gerekce="çizim okundu: teyit", butonlar=butonlar,
                                 mesaj=mesaj)), ek


def _cizim_medya(gelen: dict, settings: dict, k, g: dict, bayi, proje_koku: Path | None) -> tuple:
    from beyin import karar as KR
    k.not_dus("gelen", "çizim gönderdi (" + str(gelen.get("type")) + ")", {"niyet": "yeni_talep", "guven": "orta"})
    kayit = _okuma_kaydi(g)
    if bayi is None:
        return KR._bitir(k, KR.Karar(eylem="yonlendir", gerekce="kayıtsız numara",
                                     mesaj="Bu hat PortatifEv'in kayıtlı bayilerine hizmet verir. Kayıt ve bilgi için lütfen Lokman Bey ile iletişime geçin.")), {}
    if g.get("durum") == "dosya_yok":
        return KR._bitir(k, KR.Karar(eylem="cevapla", gerekce="çizim: dosya indirilemedi",
                                     mesaj="Gönderdiğiniz dosyayı alamadım; yeniden gönderebilir misiniz? Talebinizi yazıyla da iletebilirsiniz.")), \
            {"kayit": kayit, "patrona": f"Portman: {maske(gelen['sender'])} dosya gönderdi ama indirilemedi; panelden bakabilirsiniz."}
    if g.get("durum") == "desteklenmiyor":                    # bugünkü gibi dosya Patron'a da bildirilir (panelde)
        tur = (g.get("dosya") or {}).get("mime") or gelen.get("type")
        return KR._bitir(k, KR.Karar(eylem="cevapla", gerekce="çizim: dosya türü okunmuyor",
                                     mesaj=(g.get("neden") or "") + " Gönderdiğiniz dosyayı Lokman Bey'e ilettim.")), \
            {"kayit": kayit, "patrona": f"Portman: {maske(gelen['sender'])} okunamayan bir dosya gönderdi (tür: {tur}); panelden bakabilirsiniz."}
    okuma = g.get("okuma") or {}
    if okuma.get("tur") != "plan":
        return KR._bitir(k, KR.Karar(eylem="cevapla", gerekce=f"çizim: plan değil ({okuma.get('tur')})",
                                     mesaj="Gönderdiğiniz resimden plan çıkaramıyorum (ölçülü bir kat planı değil). Dış ölçüyü (örn. 8 × 9 m) ve oda "
                                           "sayısını (örn. 3+1) yazar mısınız? Elinizde ölçülü bir çizim varsa onu da gönderebilirsiniz.")), {"kayit": kayit}
    if k.d.get("asama") in ("onaylandi", "yonlendirildi"):      # kapanmış proje: yeni çizim yeni talep
        k.sifirla()
    return _cizim_sonucu(gelen, settings, k, okuma, g.get("dosya"), bayi, proje_koku, gelen["id"], kayit=kayit)


def _cizim_duzeltme(gelen: dict, settings: dict, k, talep, cikarim: dict | None, katalog, bayi, proje_koku: Path | None, ek_kaydet,
                    revizyon: bool) -> tuple:
    from beyin import karar as KR, gorsel_okuma as GO
    co = k.d["cizim_okuma"]
    dz = (cikarim or {}).get("gorsel_duzeltme")
    if dz is None:
        dz = gorsel_duzelt(co, gelen.get("text") or "", settings, revizyon=revizyon)
        if ek_kaydet is not None:
            ek_kaydet("gorsel_duzeltme", dz)
    if dz.get("durum") == "tamam" and dz.get("niyet") == "baska_talep":     # bu çizimle ilgisiz: mesaj bugünkü yoldan (not orada düşer)
        if not revizyon:
            k.d.pop("cizim_okuma", None); k.d["son_soru_alani"] = None
        return None
    k.not_dus("gelen", talep.ozet or "", {"niyet": talep.niyet, "guven": talep.guven})
    kayit = _okuma_kaydi(dz)
    if dz.get("durum") != "tamam":
        return KR._bitir(k, KR.Karar(eylem="cevapla", gerekce="çizim düzeltmesi okunamadı",
                                     mesaj="Yazdığınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")), \
            {"kayit": kayit, "patrona": f"Portman: {maske(gelen['sender'])} çizim düzeltmesi işlenemedi ({dz.get('hata')}); panelden bakabilirsiniz."}
    if dz.get("niyet") == "iptal":
        k.d.pop("cizim_okuma", None); k.d["son_soru_alani"] = None
        return KR._bitir(k, KR.Karar(eylem="cevapla", gerekce="çizim okuması: bayi vazgeçti",
                                     mesaj="Tamam, çizimden okumayı bıraktım. Yeni bir plan için yazabilir ya da çizim gönderebilirsiniz.")), {"kayit": kayit}
    yeni = dz["okuma"]
    ds = GO.degisenler(co["okuma"], yeni)
    fark = list(dict.fromkeys(list(dz.get("degisenler") or []) + ds))
    if not ds:
        msg = ("İstediğiniz değişikliği okumaya işleyemedim; neyi değiştirelim? Örneğin \"salon 20 m²\" ya da \"mutfak penceresi 120x120\"."
               if revizyon and co.get("durum") == "cizildi" else
               "Yazdığınızdan okumada değişecek bir şey çıkaramadım. Neyi düzelteyim? Örneğin \"salon 20 m²\" ya da \"veranda solda\".")
        k.d["son_soru_alani"] = "cizim_okuma"
        return KR._bitir(k, KR.Karar(eylem="sor", soru_alani="cizim_okuma", gerekce="çizim düzeltmesi: değişiklik yok", mesaj=msg)), {"kayit": kayit}
    bas = "Düzelttim: " + "; ".join(fark[:4]) + ".\n\n"
    if revizyon and co.get("durum") == "cizildi":
        # okumadan çizilmiş planın revizyonu: kod denetimi temizse plan doğrudan yeniden çizilir (planın kendisi teyittir)
        esik = _esik(settings)
        den = GO.denetle(yeni, ayar=esik)
        if den.get("cevrim") and not den["sorular"] and not den["cizilemez"]:
            # planın kendisi teyittir; ama bu değişiklikle gelen yeni varsayımlar (ızgara kayması, ölçüsüz pencere …) bayiye yazılır (K21)
            eski = GO.denetle(co["okuma"], ayar=esik)
            yeni_var = [n for n in den["notlar"] + den["tahminler"] if n not in eski["notlar"] + eski["tahminler"]]
            co.update(okuma=yeni, sorular=[], revizyon=True)
            var = "Varsaydığım: " + "; ".join(yeni_var) + ". " if yeni_var else ""
            uzun = len(var) > 300                                   # düğmeli mesajın gövdesine sığmayacaksa önden ayrı metin
            karar, ek = _cizim_plani(gelen, settings, k, katalog, bayi, proje_koku, den=den,
                                     on_not="Uygulanan: " + "; ".join(fark[:4]) + ". " + ("" if uzun else var), kayit=kayit)
            if uzun:
                ek["on_metin"] = ("Bu değişiklikte varsaydıklarım:\n" + "\n".join(f"• {x}" for x in yeni_var))[:GO.METIN_SINIRI]
            return karar, ek
    return _cizim_sonucu(gelen, settings, k, yeni, co.get("dosya"), bayi, proje_koku, gelen["id"], bas=bas, revizyon=revizyon, kayit=kayit)


def _oda_programi(okuma: dict) -> str | None:
    odalar = okuma.get("odalar") or []
    y = sum(1 for o in odalar if o.get("islev") == "yatak_odasi")
    s = sum(1 for o in odalar if o.get("islev") == "salon")
    return f"{y}+{s}" if y or s else None


def _cizim_plani(gelen: dict, settings: dict, k, katalog, bayi, proje_koku: Path | None, den: dict | None = None, on_not: str = "",
                 kayit: dict | None = None) -> tuple:
    """Teyit edilmiş okuma → plan. Prefabrik: İş Emri şablonu (`gorsel_okuma.is_emri_prefabrik`) → `karar._is_emri_uret` (numara, künye,
    revizyon; Motor worker'da çizer). Çelik: İE-14 denetçisinin tanımı → üretilen aday → `karar._celik_dali` (r01). Yeni çizim yeni
    projedir (konuşma sıfırlanır); okumadan çizilmiş planın revizyonu aynı projede sürer."""
    from beyin import karar as KR, gorsel_okuma as GO
    co = dict(k.d["cizim_okuma"])
    k.not_dus("gelen", "çizim okuması: doğru", {"niyet": "onay", "guven": "yuksek"})
    if den is None:
        den = GO.denetle(co["okuma"], ayar=_esik(settings))
    ek = {"kayit": {**(kayit or {}), "iz": co.get("iz"), "cizim": True}}
    if den["sorular"] or den["cizilemez"] or not den.get("cevrim"):       # teyitten sonra değişen durum (ör. Motor sürümü): yeniden sunulur
        return _cizim_sonucu(gelen, settings, k, co["okuma"], co.get("dosya"), bayi, proje_koku, co.get("mesaj_id") or gelen["id"],
                             revizyon=bool(co.get("revizyon")), kayit=kayit)
    revizyon = bool(co.get("revizyon")) and ((k.d.get("son_is_emri") or {}).get("talep") or {}).get("kaynak") == GO.KAYNAK
    if not revizyon:
        k.sifirla()
    co["durum"] = "cizildi"; co["sorular"] = []
    k.d["cizim_okuma"] = co
    k.d["son_soru_alani"] = None
    program = _oda_programi(co["okuma"])
    kan = den["kanonik"]
    ozet = f"Çiziminizdeki plan ({GO._m(kan['W'])} × {GO._m(kan['H'])} m" + (f", {program}" if program else "") + ")."
    ts = {"ozet": ozet, "varyantlar": [], "pencereler": [], "oda_programi": program, "yapi_turu": den["yapi_turu"]}
    if den["yapi_turu"] == "celik":
        c = den["cevrim"]
        aday = KR.uretilen_aday({"tanim": c["tanim"], "ozet": c.get("ozet"), "plan": c["plan"], "yol": "cizim"},
                                {"mesaj_id": co.get("mesaj_id"), "talep": {"oda_programi": program}}, None)
        aday.update(gosterim="Çiziminizdeki plan", sunum={**aday["sunum"], "ad": "Bayi çizimi (TASLAK)"})
        k.d["uretilen_plan"] = aday
        k.d["taslak"] = {**ts, "katalog_kodu": aday["kod"]}
        k.d["asama"] = "topluyor"
        return KR._celik_dali(k, bayi, katalog, aday, k.d["taslak"]), ek
    k.d["taslak"] = {"ozet": ozet, "oda_programi": program, "yapi_turu": "prefabrik"}
    return KR._is_emri_uret(k, bayi, katalog, den["cevrim"]["is_emri"], GO.KAYNAK, ts, on_bilgi=on_not), ek


def plan_uret(talep: dict, ayar: dict) -> dict:
    """İE-14 r3: üretici (`beyin/plan_uretici.uret`): program → bankadan uyarlama → çözücü → en son sınırlı LLM programı. LLM koordinat
    yazmaz; çoğu talepte hiç çağrılmaz. Sonuç kayda yazılabilir biçimde (istisna fırlatmaz)."""
    from beyin import plan_uretici as PU
    try:
        h = _hazir(ayar)
        s = PU.uret(talep, ayar={"acik": True, **{a: ayar[a] for a in ("model", "effort", "en_cok_cagri", "timeout_s", "max_tokens", "backend")
                                                  if a in ayar}}, hazir=(h.get("uretim", h) if isinstance(h, dict) else None))
    except Exception as e:                                       # beklenmeyen: kayda hata yazılır, yeniden denenen iş çağırmaz
        s = {"durum": "hata", "hata": maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}"), "adaylar": [], "denemeler": [], "cagri": 0,
             "girdi_token": 0, "cikti_token": 0}
    log("plan üretimi:", s.get("durum"), "yol", s.get("yol"), "aday", len(s.get("adaylar") or []), "çağrı", s.get("cagri"))
    return s


def plan_dogrulamasi(aday: dict, kart: str | None) -> dict | None:
    """İE-14 r3 (P1): üretilen planın çok durumlu doğrulama raporu; kartın klasörüne `dogrulama.json` (bayiye gitmez). İstisna fırlatmaz."""
    try:
        from beyin import plan_dogrulama as D
        cikti = Path(kart).parent if kart else None
        r = D.rapor(aday.get("denetim") or {}, aday.get("tanim"), cikti)
        if cikti:
            D.yaz(r, cikti / "dogrulama.json")
        return r
    except Exception as e:
        log("doğrulama raporu yazılamadı:", maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
        return None


def llm_once_revizyon(k, talep, gelen: dict, etk, cikarim: dict | None, settings: dict, katalog, ek_kaydet) -> tuple[dict | None, dict | None]:
    """İE-14 PR-3: çelik revizyon mesajı (yazılı, düğme değil) karardan önce LLM-önce okunur; karar sonucu kodla denetler. Yeni plan
    (`YENI-…`, `plan_uretimi.acik`) → `plan_duzenle` (en çok 3 çağrı); banka modeli (`llm_once_revizyon.acik`) → `degisiklik_oku` (1 çağrı).
    Sonuç iş satırına yazılır (`ek_kaydet`); yeniden denenen iş çağırmaz. Revizyon hakkı dolmuşsa ya da okuma sorusu askıdaysa çağrılmaz."""
    from beyin.konusma import MAX_REVIZYON
    from beyin import numara
    metin = numara.maskele((gelen.get("text") or "").strip())      # KVKK: LLM'e numara tam maskeli (son dört hane de gitmez)
    from beyin.karar import ESKI_TASLAK_SORUSU
    son_y = (k.d.get("son_is_emri") or {}).get("yapi") or {}
    # kapanış incelemesi: ücretli çağrı yalnız karar revizyon yoluna girecekse — plan bayide (onay bekliyor ya da "Revize et" denmiş),
    # askıda D-01 / seçenek / okuma sorusu yok, revizyon hakkı var
    if etk is not None or talep.niyet != "revizyon" or son_y.get("sistem") != "celik" or not metin \
            or k.d.get("asama") not in ("onay_bekliyor", "revizyon") or k.d.get("bekleyen_talep") \
            or int(k.d.get("revizyon") or 0) + 1 > MAX_REVIZYON \
            or k.d.get("son_soru_alani") in ("okuma", "okuma_olcu", "okuma_metin", "secenek", ESKI_TASLAK_SORUSU):
        return None, None
    temel = f"{(k.d.get('son_is_emri') or {}).get('is_emri_no')}:{(k.d.get('son_is_emri') or {}).get('revizyon')}"

    def onceki(anahtar):                               # yeniden denemede yalnız aynı plana karşı hesaplanmış sonuç kullanılır
        v = (cikarim or {}).get(anahtar)
        return v if v is not None and v.get("_temel") == temel else None
    yeni_mi = str(son_y.get("kod") or "").startswith("YENI-")
    u = k.d.get("uretilen_plan") or {}
    # kural yoluyla değişiklik almış yeni plan LLM'e yeniden yazdırılmaz (o değişiklikler plan şemasında yok, düşerdi): kural okuması sürer
    if yeni_mi and u.get("plan") and not son_y.get("degisiklikler") and (settings.get("plan_uretimi") or {}).get("acik"):
        pd = onceki("plan_duzenleme")
        if pd is None:
            pd = {**plan_duzenle(u["plan"], metin, {"oda_programi": u.get("oda_programi")}, settings.get("plan_uretimi") or {}), "_temel": temel}
            if ek_kaydet is not None:
                ek_kaydet("plan_duzenleme", pd)
        return pd, None
    lo_ayar = settings.get("llm_once_revizyon") or {}
    mod = okuma_modu(lo_ayar)
    if not yeni_mi and mod == "acik":
        lo = onceki("degisiklik")
        if lo is None:
            lo = {**degisiklik_oku(son_y, metin, katalog, lo_ayar), "_temel": temel}
            if ek_kaydet is not None:
                ek_kaydet("degisiklik", lo)
        return None, lo
    if not yeni_mi and mod == "golge":                    # r3 P4: kural karar verir; LLM okuması yalnız kayda ve kıyasa (bayiye gitmez)
        lg = onceki("degisiklik_golge")
        if lg is None:
            lg = {**degisiklik_oku(son_y, metin, katalog, lo_ayar), "_temel": temel}
            if ek_kaydet is not None:
                ek_kaydet("degisiklik_golge", lg)
        k.llm_golge = lg
    return None, None


def okuma_modu(lo_ayar: dict) -> str:
    """`llm_once_revizyon.mod`: kapali | golge | acik; `mod` yoksa geriye uyum (`acik: true` → acik)."""
    m = lo_ayar.get("mod")
    if m in ("kapali", "golge", "acik"):
        return m
    return "acik" if lo_ayar.get("acik") else "kapali"


def okuma_kiyasi(son_y: dict, metin: str, katalog, lg: dict) -> dict | None:
    """Gölge kipinde iki okumanın kıyası (`beyin/okuma_kiyas.py`): açık planın tablosuna karşı kural ve LLM okuması, sınıf. Metin satıra
    yazılmaz (mesajlar tablosunda). İstisna fırlatmaz."""
    from beyin import celik_okuma as CO, okuma_kiyas as OK, varyant
    try:
        t = _cizim_tanimi(son_y["tanim"], son_y.get("degisiklikler"))
        y = varyant._kur(t)
        aday = katalog.aday(son_y.get("kod")) or {}
        taban = katalog.aday(aday.get("referans_model")) if aday.get("referans_model") else None
        kat = taban if (taban and taban.get("varyantlar")) else aday
        kodlar = {kat["kod"], *(kat.get("varyantlar") or [])} if kat.get("varyantlar") else set()
        k = OK.kiyas(metin, t, kat if kat.get("varyantlar") else None, lg, CO.pencere_adaylari(t, y), kodlar, y)
        return {"model": son_y.get("kod"), "kural": OK.kayit_ozeti(k["kural"]), "llm": OK.kayit_ozeti(k["llm"]), "sinif": k["sinif"],
                **{a: lg.get(a) or 0 for a in ("cagri", "girdi_token", "cikti_token")}}
    except Exception as e:
        log("okuma kıyası yapılamadı:", maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
        return None


def _hazir(ayar: dict):
    """manuel arka uç (yerel test; LLM çağrısı yok): kayıtlı cevap `hazir_dosya`dan. İE-14 r3: üretim ve yeni plan düzenlemesi aynı dosyada
    `uretim` ({program, yeniden}) ve `duzenleme` (işlem listesi) anahtarlarıyla ayrılabilir."""
    return json.loads(Path(ayar["hazir_dosya"]).read_text(encoding="utf-8")) if ayar.get("backend") == "manuel" else None


def plan_duzenle(plan: dict, metin: str, talep: dict, ayar: dict) -> dict:
    """İE-14 r3: yeni planın revizyonu (`beyin/plan_islem.duzenle`): LLM isteği koordinatsız işlemlere çevirir (1 çağrı, ücretli), kod
    uygular, denetçi karar verir. İstisna fırlatmaz."""
    from beyin import plan_islem as PI
    try:
        h = _hazir(ayar)
        s = PI.duzenle(plan, metin, talep, ayar={a: ayar[a] for a in ("model", "effort", "timeout_s", "max_tokens", "backend") if a in ayar},
                       hazir=(h.get("duzenleme", h) if isinstance(h, dict) else None))
    except Exception as e:
        s = {"durum": "hata", "hata": maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}"), "denemeler": [], "cagri": 0, "girdi_token": 0, "cikti_token": 0}
    log("plan düzenleme:", s.get("durum"), "işlem", len(s.get("islemler") or []), "çağrı", s.get("cagri"))
    return s


def degisiklik_oku(son_y: dict, metin: str, katalog, ayar: dict) -> dict:
    """İE-14 PR-3: banka modelinin revizyonu LLM-önce (`degisiklik_okuyucu.oku`; 1 çağrı). Tablo: son planın pencereleri (değişikliklerle),
    modelin çatı seçenekleri, dış karkas. İstisna fırlatmaz."""
    from beyin import celik_okuma as CO, degisiklik_okuyucu as DO, varyant
    try:
        t = _cizim_tanimi(son_y["tanim"], son_y.get("degisiklikler"))
        pencereler = CO.pencere_adaylari(t, varyant._kur(t))
        aday = katalog.aday(son_y.get("kod")) or {}
        taban = katalog.aday(aday.get("referans_model")) if aday.get("referans_model") else None
        kat = taban if (taban and taban.get("varyantlar")) else aday
        catilar = [{"kod": x["kod"], "ad": (x.get("sunum") or {}).get("cati_adi") or ""} for x in
                   [kat] + [katalog.aday(v) for v in kat.get("varyantlar") or []] if x] if kat.get("varyantlar") else []
        dis140 = "140" in str((t.get("duvar_siniflari") or {}).get("dis", {}).get("profil", ""))
        return DO.oku(metin, pencereler, catilar, dis140, ayar={a: ayar[a] for a in ("model", "effort", "timeout_s", "backend") if a in ayar},
                      hazir=_hazir(ayar))
    except Exception as e:
        return {"durum": "hata", "islemler": [], "bilgi": [], "cagri": 0, "hata": maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")}


def kart_son_yeri(k, proje_koku: Path | None) -> None:
    """İE-14: yeni planların kartları hazırlık klasöründe çizilir; kalıcı akış `<ad>/r01`'i projects/'e taşır (`kalici._yerlestir`). Konuşmadaki
    yollar (sonraki set sunumları; r3: iki yeni plan) taşınan yere çevrilir."""
    if not proje_koku:
        return
    planlar = [k.d.get("uretilen_plan") or {}] + list(k.d.get("uretilen_planlar") or [])
    for u in planlar:
        g = u.get("gorsel")
        if not (g and str(g).startswith(str(proje_koku))):
            continue
        son = str(KANAL / "projects" / Path(g).relative_to(Path(proje_koku)))
        for x in planlar + list((k.d.get("secenek_seti") or {}).get("adaylar") or []):
            if x.get("gorsel") == g:
                x["gorsel"] = son


def plan_karti(tanim: dict | None, gelen: dict, proje_koku: Path | None, sira: int = 1) -> str | None:
    """İE-14: yeni planın seçenek kartı (`<kod>_bayi_gorsel.png`, perspektifsiz; genel motor). Üretilemezse None (set görselsiz gider).
    r3: ikinci yeni planın klasörü `-2` ekiyle."""
    if not tanim:
        return None
    try:
        from motor.genel import uret as U
        kok = (Path(proje_koku) if proje_koku else KANAL / "projects") / (f"YENI-{satir_id(gelen['id'], 0)[4:16]}" + ("" if sira == 1 else f"-{sira}"))
        kok.mkdir(parents=True, exist_ok=True)
        yol = kok / "tanim.json"
        yol.write_text(json.dumps(tanim, ensure_ascii=False), encoding="utf-8")
        U.uret(yol, kok / "r01", is_emri_no="YENI", revizyon=1, perspektif=False, bayi=True)     # r01: kalıcı akış projects/'e taşır
        kart = kok / "r01" / f"{U.kod_govde(tanim)}_bayi_gorsel.png"
        return str(kart) if kart.is_file() else None
    except Exception as e:
        log("yeni plan kartı üretilemedi:", maske_numaralar(f"{type(e).__name__}: {str(e)[:160]}"))
        return None


def KT_KOK() -> Path:
    from beyin import katalog as KT
    return KT.SABLON_DIR


def motor_sec(ie: dict):
    """İE-08 (D-08): zarfın `yapi.sistem`i motoru seçer: 'celik' → genel motor (`cizim_genel`), yoksa pano birimli Motor (`dxf_out.uret`).
    Çağrı anında bakılır: testler `dxf_out.uret`'i sahte üreticiyle değiştirir. Dönen: (ad, uret(ie, hedef) → manifest)."""
    if (ie.get("yapi") or {}).get("sistem") == "celik":
        return "genel", cizim_genel
    from motor import dxf_out
    return "pano", dxf_out.uret


def cizim_genel(ie: dict, hedef: Path) -> dict:
    """Çelik İş Emri → genel motor (İE-08 A3). Tanım zarfta gömülü değildir: `modeller/<kod>.json` yüklenir, sha256 doğrulanır,
    `yapi.degisiklikler` sırayla uygulanır (A4, PR-2b: `beyin/varyant.tanim_uygula`), tanım `hedef/tanim.json`'a yazılır ve
    `motor.genel.uret` (perspektifli; VTK yoksa görsel perspektifsiz, iş düşmez) güncel kural kitabıyla (sürümle gider) koşar.
    Antet bilgisi zarfın `bilgi`sinden (D-09). Manifest prefabrik Motor'unkiyle aynı anahtarları taşır (`pdf`, `pdf_sha256`, `warnings`)."""
    from motor.genel import uret as U
    from beyin import celik as C
    y = ie.get("yapi") or {}
    if C.tanim_gomulu(y):                                       # İE-14 (D-18): üretilen planın tanımı zarfta gömülü; kanonik sha
        if not C.tanim_dogrula(y):
            raise ValueError(f"gömülü tanım zarftaki sha ile uyuşmuyor: {y.get('kod')}")
    else:
        tanim_yolu = KOD.parent / str(y.get("tanim") or "")
        if not y.get("tanim") or not tanim_yolu.is_file():
            raise FileNotFoundError(f"model tanımı yok: {y.get('tanim')}")
        if y.get("tanim_sha256") and hashlib.sha256(tanim_yolu.read_bytes()).hexdigest() != y["tanim_sha256"]:
            raise ValueError(f"model tanımı zarftaki sha ile uyuşmuyor: {y.get('tanim')}")
    t = _cizim_tanimi(y["tanim"], y.get("degisiklikler"))
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    calisma = hedef / "tanim.json"
    calisma.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    no, rev = ie.get("is_emri_no"), int(ie.get("revizyon") or 1)
    return U.uret(calisma, hedef, is_emri_no=no, revizyon=rev, set_yolu=None, yontem=y.get("yontem") or "panel", perspektif=True, bayi=True,
                  kaynak=f"İş Emri {no} r{rev:02d} ({y.get('referans_model') or y.get('kod')})", bilgi=ie.get("bilgi"))


def ek_sozu(metin: str, gorsel_var: bool) -> str:
    """BK-08 madde 4: çelik plan mesajı "plan görseli ve PDF ektedir" der; görsel gitmiyorsa (mesaj katmanı kapalı ya da bayi görseli
    üretilemedi) yalnız PDF'in ekte olduğu söylenir. Prefabrik metni bu sözü taşımaz, dokunulmaz."""
    return metin if gorsel_var else metin.replace("plan görseli ve PDF ektedir", "PDF ektedir")


def maske_numaralar(metin: str) -> str:
    """Günlük, hata iletisi, Patron metni ve kayıt kopyası için: telefon numaraları "…" + son dört hane olur (K09, D-09). BK-08 madde 9:
    bitişik 10–15 hanenin yanında boşluklu, tireli, parantezli ve `+90`'lı biçimler de (`beyin/numara.py`, paftayla aynı desen)."""
    from beyin import numara
    return numara.maskele(metin, son_dort=True)


NASIL_CALISIR = KOD / "belgeler" / "nasil_calisir.html"      # İE-08 8b M4: bayi rehberi §1–3 tek sayfa (Görev 9 metni)
_NASIL_CSS = ("body{font-family:sans-serif;font-size:9.5pt} h1{font-size:16pt} h2{font-size:11.5pt;margin-top:8pt} "
              "table{border-collapse:collapse} td,th{border:0.5pt solid #999;padding:2pt;font-size:8.5pt}")


def nasil_calisir_pdf() -> tuple[Path, str]:
    """'Nasıl çalışır?' PDF'i: kaynak HTML'den tek sayfa A4 (PyMuPDF), `projects/bilgi/` altına kaynağın özetiyle adlanır (gönderici yalnız
    projects/ altından gönderir; metin değişmedikçe yeniden yazılmaz). Sayfaya sığmazsa hata: yarım sayfa gitmez."""
    import fitz
    html = NASIL_CALISIR.read_text(encoding="utf-8")
    hedef = KANAL / "projects" / "bilgi" / f"Portman_Nasil_calisir_{hashlib.sha256(html.encode()).hexdigest()[:12]}.pdf"
    if not hedef.is_file():
        d = fitz.open(); sayfa = d.new_page(width=595, height=842)
        bos, olcek = sayfa.insert_htmlbox(fitz.Rect(40, 40, 555, 802), html, css=_NASIL_CSS)
        if bos < 0 or olcek < 1:
            raise ValueError("nasıl çalışır metni tek sayfaya sığmadı")
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecici = hedef.with_suffix(".tmp"); gecici.write_bytes(d.tobytes(garbage=3, deflate=True)); os.replace(gecici, hedef)
    return hedef, _sha(hedef)


def liste_exceli(json_yolu: Path, hedef: Path, no: str, rev: int, set_yolu=None) -> dict:
    """İE-08 8b (D-17): yükleme listesinin Excel'i sunucuda, `motor/genel/excel_liste.xlsx_yaz` ile (kabul paketiyle aynı düzen);
    `uret`'in dışında: genel motorun altın çıktısı ve referans izleri değişmez. Ad `Portman_<no>_rNN_yukleme_listesi.xlsx`.
    Üretilemezse (openpyxl yok, liste bozuk) {"hata": …}; çizim ve bayi akışı durmaz, mühendise Excel'siz gider."""
    try:
        from motor.genel import excel_liste
        hedef_x = Path(hedef) / f"Portman_{no}_r{int(rev):02d}_yukleme_listesi.xlsx"
        excel_liste.xlsx_yaz(json.loads(Path(json_yolu).read_text(encoding="utf-8")), hedef_x, kaynak=Path(json_yolu).name,
                             set_adi=Path(str(set_yolu or "")).name or None)
        return {"dosya": str(hedef_x), "sha256": _sha(hedef_x), "bayiye_gider": False}
    except Exception as e:
        return {"hata": maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")}


def _ucb_eki(ifc: Path, hedef: Path, no: str, rev: int, settings: dict) -> dict:
    """İE-21: IFC'den tek dosyalık 3D sayfası (kayıtta `<rev>/3d/index.html`) ve yayın kopyası. Bağlantı yalnız `ucb_taban_url` doluysa ve
    yayın dizini varsa gelir (`kanal/ucb_yayin.py`; adres rastgele anahtarlı, İş Emri numarası taşımaz)."""
    from motor import ucb_sayfa as US
    import ucb_yayin as UY
    html = US.uret(ifc, hedef / "3d" / "index.html", baslik=f"{no} r{rev:02d}")
    return {"dosya": str(html), "sha256": _sha(html), **UY.yayinla(html, settings, KANAL / "yayin" / "3d")}


def ekler_uret(ie: dict, hedef: Path, v: dict, settings: dict, m: dict | None = None) -> dict:
    """Aynı İş Emri revizyonundan türetilen ekler: {"gorsel": {...}, "ifc": {...}, "ucb": {...}}. Her biri ayrı denenir; üretilemeyen
    ek akışı durdurmaz (satır metinle gider) ve 'hata' ile kaydedilir. Motor'un DXF/PDF'ine dokunulmaz.
    İE-08 çelik (manifest `m`, motor genel): görsel = `<kod>_bayi_gorsel.png` (plan + çatı planı + perspektifler; yoksa `plan_bayi.png`),
    IFC genel motorun IFC'si; 3D sayfası o IFC'den (İE-21). Yükleme listesi klasörde kalır, bayiye gitmez."""
    ekler: dict = {}
    no, rev = ie.get("is_emri_no", ""), int(ie.get("revizyon") or 1)
    if (ie.get("yapi") or {}).get("sistem") == "celik" and m is not None:
        for anahtar in ("bayi_gorsel", "plan_bayi"):
            yol = hedef / str(m.get(anahtar) or "")
            if m.get(anahtar) and yol.is_file():
                ekler["gorsel"] = {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png", "kaynak": anahtar}
                break
        else:
            ekler["gorsel_hata"] = "bayi görseli üretilmedi"
        if m.get("ifc") and (hedef / m["ifc"]).is_file():
            oz = (v.get("ifc") or {})
            ekler["ifc"] = {"dosya": str(hedef / m["ifc"]), "sha256": m.get("ifc_sha256") or _sha(hedef / m["ifc"]), "sema_hatasi": oz.get("sema_hatasi"),
                            **{k: (oz.get("urunler") or {}).get(x) for k, x in (("duvar", "IfcWall"), ("pencere", "IfcWindow"), ("kapi", "IfcDoor"), ("mahal", "IfcSpace"))}}
        else:
            ekler["ifc_hata"] = "IFC üretilmedi"
        if ekler.get("ifc"):
            try:
                ekler["ucb"] = _ucb_eki(Path(ekler["ifc"]["dosya"]), hedef, no, rev, settings)
            except Exception as e:
                ekler["ucb_hata"] = maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")
        if m.get("yukleme_json"):
            ekler["yukleme_listesi"] = {"dosya": str(hedef / m["yukleme_json"]), "bayiye_gider": False}
            excel = liste_exceli(hedef / m["yukleme_json"], hedef, no, rev, m.get("set"))   # İE-08 8b (D-17): mühendise gider, bayiye gitmez
            ekler.update({"excel": excel} if "dosya" in excel else {"excel_hata": excel["hata"]})
        if m.get("duzenlenebilir_dxf") and (hedef / m["duzenlenebilir_dxf"]).is_file():      # D-11: düzenlenebilir DXF (plan + görünüşler); kayıtta, bayiye gitmez
            ekler["dxf"] = {"dosya": str(hedef / m["duzenlenebilir_dxf"]), "sha256": _sha(hedef / m["duzenlenebilir_dxf"]), "bayiye_gider": False}
        y = ie.get("yapi") or {}
        if y.get("onceki") and rev >= 2 and (hedef / "tanim.json").is_file():
            # İE-08 A4: r02 ve sonrasında başlık görseli önce–sonra (önceki plan | bu plan; altta çatı planı ve iki perspektif, aynı görselde)
            try:
                from motor.genel import okuma_gorseli as OG, uret as U
                from beyin import celik as C
                o = y["onceki"]
                if not C.tanim_dogrula(o):                          # dosyada bayt sha'sı, gömülüde (İE-14) kanonik sha
                    raise ValueError("önceki planın tanımı değişmiş")
                t0 = _cizim_tanimi(o["tanim"], o.get("degisiklikler"))
                t1 = json.loads((hedef / "tanim.json").read_text(encoding="utf-8"))
                yol = OG.once_sonra(t0, t1, hedef, U.kod_govde(t1), y.get("bu_revizyon") or [],
                                    int(o.get("revizyon") or rev - 1), rev, yontem=y.get("yontem") or "panel",
                                    perspektif=((v or {}).get("perspektif") or {}).get("durum") == "TAMAM")
                if ekler.get("gorsel"):
                    ekler["kart"] = ekler["gorsel"]                 # bu planın bayi görseli (kart) kayıtta kalır
                ekler["gorsel"] = {"file": str(yol), "filename": yol.name, "sha256": _sha(yol), "mime": "image/png", "kaynak": "once_sonra"}
            except Exception as e:                                  # görsel üretilemezse kart başlık olur; akış durmaz
                ekler["once_sonra_hata"] = maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")
        return ekler
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
        ekler["ifc"] = {"dosya": str(hedef / ad), "sha256": _sha(hedef / ad), **{k: oz.get(k) for k in ("duvar", "pencere", "kapi", "mahal", "sema_hatasi")},
                        **({"cati_uyari": oz["cati"]["uyari"]} if (oz.get("cati") or {}).get("uyari") else {})}   # makas yeri uyarısı (BK-12 PR-R, K16)
        try:
            ekler["ucb"] = _ucb_eki(hedef / ad, hedef, no, rev, settings)
        except Exception as e:
            ekler["ucb_hata"] = maske_numaralar(f"{type(e).__name__}: {str(e)[:200]}")
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
    baglam = "; ".join(x for x in (bayi_tanimi(gelen.get("bayi")), baglam_ozeti(k)) if x)       # İE-08 8b M5: ad ve hitap (D-06), numara yok
    return llm.cikar_guvenli(gelen["text"], baglam, backend=backend, model=llm_ayar.get("model") or None,
                             hazir=gelen.get("test_cikarim") if backend == "manuel" else None,   # yalnız yerel test
                             ayarlar_json=settings.get("ayarlar_json"), timeout=int(llm_ayar.get("timeout_s", 60)))


