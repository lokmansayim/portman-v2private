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
    """İE-08 8b M5 (D-06): LLM bağlamında bayinin adı ve hitabı; telefon numarası asla (ad alanı numaraya düşmüşse ad yazılmaz, numara
    biçimli her şey maskelenir). Kayıtsız ya da boşsa ''."""
    b = bayi or {}
    numara = str(b.get("numara") or "")
    ad = str(b.get("ad") or "").strip()
    ad = "" if (not ad or ad == numara or ad.isdigit()) else maske_numaralar(ad)[:80]
    hitap = maske_numaralar(str(b.get("hitap") or "").strip())[:40]
    parca = ([f"bayi: {ad}"] if ad else []) + ([f"hitap: {hitap}"] if hitap else [])
    return ", ".join(parca)


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
         katalog=None) -> dict:
    """Bir gelen mesajı işler; giden satırlarını ve sonucu döndürür (kayda yazmaz — çağıran yazar: kanal/kalici.py).
    k verilirse konuşma o nesneden okunur (Postgres); verilmezse Beyin'in dosya tabanlı Konusma'sı (yalnız yerel koşum ve
    testler). cikarim verilirse ({"talep": …, "meta": …} ya da {"hata": …}) LLM çağrılmaz; proje_koku verilirse Motor çıktısı
    projects/ yerine oraya yazılır (kalıcı akış önce hazırlık klasörüne yazar, kayıtla birlikte yerine taşır).
    İE-04: gelen satırda reply_id varsa (buton ya da liste cevabı) LLM çağrılmaz; kimlik kanal/etkilesim.py ile çözülür
    (cikarim["etkilesim"] verilmişse o kullanılır). giden_bul(context_id) cevaplanan giden satırı verir (doğrulama için);
    None ise bu doğrulama yapılmaz."""
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
                ekle("Talebinizi bu sohbete yazabilirsiniz; örnek: \"Tek kat çelik, 2+1, 88 m² civarı, beşik çatı.\"")
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
        elif cikarim is not None:
            if cikarim.get("hata"):
                raise CikarimHatasi(cikarim["hata"])
            from beyin.sema import Talep
            talep, meta = Talep.model_validate(cikarim["talep"]), dict(cikarim.get("meta") or {})
        else:
            talep, meta = cikar(gelen, settings, k)
    except Exception as e:
        hata = maske_numaralar(str(e))[:320] if isinstance(e, CikarimHatasi) else maske_numaralar(f"{type(e).__name__}: {str(e)}")[:300]
        ekle("Mesajınızı şu an işleyemedim; Lokman Bey'e iletiyorum, en kısa sürede dönüş yapılacak.")
        patrona(f"Portman: {kim} mesajı işlenemedi (çıkarım hatası). Mesaj: \"{maske_numaralar(gelen['text'])[:300]}\"", sablon=True)
        sonuc.update(eylem="hata", gerekce="çıkarım hatası", hata=hata)
        return {"satirlar": satirlar, "sonuc": sonuc, "hata": hata}

    d0 = _anlik(k.d)                               # İE-08 A4 "hak düşmez": çelik çizim düşerse konuşma bu duruma döner
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
    metin = karar.mesaj
    # PDF başlığındaki özet: soru düğmesinin cevabıysa ("kısa cevap: 2") talebin özeti (kapanış incelemesi 13.10)
    ozet_baslik = ((k.d.get("taslak") or {}).get("ozet") or "") if meta.get("tur") == "soru" else (talep.ozet or "")
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
        if ucb and ucb.get("url"):
            ekle_satir(giden_etkilesim(gelen, f"{no} r{rev:02d} planının basit 3D modeli. Tarayıcıda açılır; odalara dokunarak gezebilirsiniz.", 0,
                                       baglanti={"metin": "3D'de gez", "url": ucb["url"]}, tur="cevap", is_emri_no=no, revizyon=rev))
        # ucb_taban_url yoksa 3D sayfası yalnız kayıtta (revizyonlar.ekler) durur; bayiye söz veren bir mesaj gönderilmez (barınak kararı ayrı)
    elif butonlar and karar.soru_alani == "okuma" and len((k.d.get("okuma_bekleyen") or {}).get("adaylar") or []) == 2:
        # İE-08 A4: "1 / 2 / Hiçbiri" — iki okuma tek görselde numaralı (görsel üretilemezse düğmeler metinle gider; akış durmaz).
        # "Görselde işaretledim" cümlesi yalnız görsel gerçekten giderse (kapanış incelemesi 13.10)
        g = okuma_gorseli(gelen, k.d["okuma_bekleyen"], proje_koku)
        ekle_satir(giden_etkilesim(gelen, metin + (" Görselde 1 ve 2 ile işaretledim." if g else ""), 0, butonlar=butonlar, gorsel=g,
                                   altbilgi="1, 2 ya da Hiçbiri"))
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
        model = katalog.bul(talep.katalog_kodu) if talep.katalog_kodu else None
        model_notu = f" Katalog notu ({model['code']}): {model['not']}" if model and model.get("not") else ""   # D-07: yalnız Patron'a
        patrona(f"Portman yönlendirme: {kim} — {karar.gerekce}.{model_notu} Mesaj: \"{maske_numaralar(gelen.get('text') or '')[:300]}\"",
                sablon=True, is_emri_no=sonuc.get("is_emri_no"))
    return {"satirlar": satirlar, "sonuc": sonuc}


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


def _cizim_tanimi(yol_veya_tanim: str, degisiklikler: list[dict] | None) -> dict:
    """Model tanımı (`modeller/<kod>.json`) + sırayla uygulanmış değişiklikler (`beyin/varyant.tanim_uygula`)."""
    from beyin import varyant
    t = json.loads((KOD.parent / str(yol_veya_tanim)).read_text(encoding="utf-8"))
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
    y = ie.get("yapi") or {}
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


def ekler_uret(ie: dict, hedef: Path, v: dict, settings: dict, m: dict | None = None) -> dict:
    """Aynı İş Emri revizyonundan türetilen ekler: {"gorsel": {...}, "ifc": {...}, "ucb": {...}}. Her biri ayrı denenir; üretilemeyen
    ek akışı durdurmaz (satır metinle gider) ve 'hata' ile kaydedilir. Motor'un DXF/PDF'ine dokunulmaz.
    İE-08 çelik (manifest `m`, motor genel): görsel = `<kod>_bayi_gorsel.png` (plan + çatı planı + perspektifler; yoksa `plan_bayi.png`),
    IFC genel motorun IFC'si; 3D sayfası yok (kapsam dışı). Yükleme listesi klasörde kalır, bayiye gitmez."""
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
                o = y["onceki"]
                yol_o = KOD.parent / str(o.get("tanim") or "")
                if o.get("tanim_sha256") and hashlib.sha256(yol_o.read_bytes()).hexdigest() != o["tanim_sha256"]:
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
    baglam = "; ".join(x for x in (bayi_tanimi(gelen.get("bayi")), baglam_ozeti(k)) if x)       # İE-08 8b M5: ad ve hitap (D-06), numara yok
    return llm.cikar_guvenli(gelen["text"], baglam, backend=backend, model=llm_ayar.get("model") or None,
                             hazir=gelen.get("test_cikarim") if backend == "manuel" else None,   # yalnız yerel test
                             ayarlar_json=settings.get("ayarlar_json"), timeout=int(llm_ayar.get("timeout_s", 60)))


