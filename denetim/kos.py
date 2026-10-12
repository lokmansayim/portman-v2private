#!/usr/bin/env python3
"""Portman — bağımsız denetçi koşumu. Temiz açılmış kaynak paketinde, elle dosya taşımadan çalışır (denetim bulgusu F04).

    python3 denetim/kos.py            # hızlı: ortam, girdi hash'leri, Beyin harness, iki altın Motor testi (+BOM), P6001 çıkarıcı altın testi, sır taraması
    python3 denetim/kos.py --planlar  # ek: 16 katalog planının tamamı (çıkarıcı + Motor), plan başına özet

Çıktı: cikti/denetim/sonuc.json (her adım: durum, süre, sayılar, çıkış kodu) + ekrana özet. Ağ erişimi ve sır gerekmez; WhatsApp/LLM çağrısı yok.
Ortam: Python 3.11+, ezdxf==1.4.4 pymupdf shapely pydantic numpy pillow (sürümler sonuc.json'a yazılır).
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, re, subprocess, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
CIKTI = ROOT / "cikti" / "denetim"
PLANLAR = ["P6001", "P6501", "P6701", "P7001", "P7401", "P7601", "P8201", "P8501", "P9201", "P9401", "P9501", "P9901", "P1051", "P1081", "P1121", "P3701"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def adim(sonuc: dict, ad: str, fn):
    t0 = time.time()
    try:
        r = fn(); durum = "passed" if r.get("passed", True) else "failed"
    except Exception as e:
        r = {"hata": f"{type(e).__name__}: {str(e)[:300]}", "iz": traceback.format_exc()[-1200:]}; durum = "error"
    r.update(durum=durum, sure_s=round(time.time() - t0, 1)); sonuc["adimlar"][ad] = r
    print(f"[{durum:>6}] {ad} ({r['sure_s']} s) " + (json.dumps({k: v for k, v in r.items() if k in ('sayilar', 'hata')}, ensure_ascii=False)[:300]))
    return r


def ortam() -> dict:
    import ezdxf, shapely, pydantic, numpy, pymupdf
    return {"python": sys.version.split()[0], "platform": platform.platform(), "ezdxf": ezdxf.__version__, "shapely": shapely.__version__,
            "pydantic": pydantic.VERSION, "numpy": numpy.__version__, "pymupdf": pymupdf.__doc__.split()[-1] if pymupdf.__doc__ else getattr(pymupdf, "VersionBind", "?"),
            "cwd": str(ROOT), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def girdi_hashleri() -> dict:
    dosyalar = ["is_emri/ALTIN_2plus1_6x8.json", "is_emri/YAN_VERANDALI_2plus1_6x8p5.json", "is_emri/P6001_2plus1_6x6.json",
                "kanal/ref_source-6x8.dxf", "kanal/ref_h-connector.json", "ref_yan/yeni-2plus1-yan-verandali.dxf", "ref_yan/BOM_SAYIM_KAYDI.json",
                "ref_katalog/P6001.dxf", "ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf",
                "beyin/karar.py", "beyin/harness.py", "beyin/testler/mesajlar.json", "beyin/testler/cikarim_b.json",
                "motor/geometry.py", "motor/dxf_out.py", "motor/validate.py", "motor/cikarici.py", "kanal/worker.py", "kanal/api.php", "vps/agent.py"]
    return {d: (sha(ROOT / d)[:16] if (ROOT / d).exists() else "YOK") for d in dosyalar}


def harness() -> dict:
    from beyin import harness as H
    ok, toplam = H.main(durum_dir=CIKTI / "durum_harness", sessiz=True, rapor_yaz=False)
    return {"passed": ok == toplam, "sayilar": {"uyumlu": ok, "toplam": toplam}}


def motor_altin(is_emri_yolu: str, hedef: str, beklenen: dict, ref_bom: str | None = None) -> dict:
    import ezdxf
    from motor import dxf_out, validate as V
    ie = json.loads((ROOT / is_emri_yolu).read_text(encoding="utf-8"))
    out = CIKTI / hedef
    m = dxf_out.uret(ie, out)
    v = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    kinds = {}
    for o in v.get("openings", []): kinds[o.get("kind")] = kinds.get(o.get("kind"), 0) + 1
    sayilar = {"passed": v.get("passed"), "pdf": m.get("pdf"), "pano": v.get("panel_count"), "kose": v.get("corner_count"), "aciklik": kinds,
               "ucluH": (len(v["h_connectors"]) if isinstance(v.get("h_connectors"), list) else v.get("h_connectors")), "ayak_izi_fark_cm2": v.get("footprint_diff_cm2"), "altin": v.get("altin")}
    doc = ezdxf.readfile(out / m["dxf"])
    sayim = V.bom_sayim(doc)
    kontrol = {}
    if ref_bom:
        ref = json.loads((ROOT / ref_bom).read_text(encoding="utf-8")).get("counts", {})
        farklar = {k: (ref.get(k), sayim.get(k)) for k in sorted(set(ref) | set(sayim)) if ref.get(k) != sayim.get(k)}
        kontrol["bom_ref_ile_ayni"] = not farklar; kontrol["bom_fark"] = farklar; kontrol["bom_kod_sayisi"] = len(ref)
    dis = v.get("outer_cm")
    kontrol["dis_olcu"] = dis
    if "dis_olcu" in beklenen and dis is not None:
        kontrol["dis_olcu_beklenen"] = beklenen["dis_olcu"]; kontrol["dis_olcu_ok"] = [round(float(x), 2) for x in dis] == beklenen["dis_olcu"]
    kontrol["bom_sayim"] = sayim
    gecti = v.get("passed") is True and m.get("pdf") is not None and all(x is not False for x in (kontrol.get("bom_ref_ile_ayni"), kontrol.get("dis_olcu_ok")))
    return {"passed": gecti, "sayilar": {k: v_ for k, v_ in {**sayilar, **{k: kontrol[k] for k in ("bom_ref_ile_ayni", "bom_fark", "dis_olcu", "dis_olcu_ok") if k in kontrol}}.items()},
            "validation_keys": sorted(v.keys())[:40], "bom_sayim": sayim, "manifest": {k: m.get(k) for k in ("dxf_sha256", "pdf_sha256", "validation_passed", "duration_s")}}


def cikarici_p6001() -> dict:
    cmd = [sys.executable, "-m", "motor.cikarici", "ref_katalog/P6001.dxf", "--kod", "P6001", "--sablon", "is_emri/P6001_2plus1_6x6.json",
           "--cikti", str(CIKTI / "cikarici" / "P6001"), "--motor"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    rapor_p = CIKTI / "cikarici" / "P6001" / "cikarim_raporu.json"
    rapor = json.loads(rapor_p.read_text(encoding="utf-8")) if rapor_p.exists() else {}
    k = rapor.get("karsilastirma") or {}
    mah = k.get("mahaller") or []; ac = k.get("acikliklar") or []
    sayilar = {"grid_esit": (k.get("grid") or {}).get("esit"), "mahal_esit": f"{sum(1 for x in mah if x.get('durum') == 'eşit')}/{len(mah)}",
               "aciklik_esit": f"{sum(1 for x in ac if x.get('durum') == 'eşit')}/{len(ac)}", "aciklik_farklar": [x for x in ac if x.get("durum") != "eşit"][:5]}
    return {"passed": r.returncode == 0 and sayilar["mahal_esit"].startswith("5/"), "cikis_kodu": r.returncode, "sayilar": sayilar,
            "son_satirlar": r.stdout[-800:] + r.stderr[-400:], "not": "aciklik_farklar: menteşe yorumu farkları (insan kararı bekler)"}


def planlar_16() -> dict:
    ozet = {}; hepsi_ok = True
    for kod in PLANLAR:
        cmd = [sys.executable, "-m", "motor.cikarici", "ref_katalog/TEK_KAT_PREFABRIK_PLANLARI.dxf", "--secici", kod, "--cikti", str(CIKTI / "cikarici" / kod), "--motor"]
        t0 = time.time(); r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        vp = CIKTI / "cikarici" / kod / "motor" / "validation.json"; mp = CIKTI / "cikarici" / kod / "motor" / "manifest.json"
        v = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
        m = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
        iep = CIKTI / "cikarici" / kod / "is_emri.json"
        ie = json.loads(iep.read_text(encoding="utf-8")) if iep.exists() else {}
        ac = ie.get("acikliklar", [])
        ozet[kod] = {"cikis_kodu": r.returncode, "motor_passed": v.get("passed"), "pdf": m.get("pdf"), "pencere": sum(1 for a in ac if a.get("tur") == "pencere"),
                     "kapi": sum(1 for a in ac if str(a.get("tur", "")).endswith("kapi")), "mahal": len(ie.get("mahaller", [])), "sure_s": round(time.time() - t0, 1),
                     "hata": (r.stderr[-300:] if r.returncode != 0 else None)}
        hepsi_ok = hepsi_ok and r.returncode == 0
        print(f"   {kod}: rc={r.returncode} motor={v.get('passed')} pencere={ozet[kod]['pencere']} kapı={ozet[kod]['kapi']} mahal={ozet[kod]['mahal']} ({ozet[kod]['sure_s']} s)")
    return {"passed": True, "sayilar": {"motor_passed": sum(1 for o in ozet.values() if o["motor_passed"] is True), "toplam": len(PLANLAR),
                                        "kapisiz_plan": [k for k, o in ozet.items() if o["kapi"] == 0]}, "planlar": ozet,
            "not": "motor_passed = kural doğrulaması; mimari doğruluk/insan kabulü değildir. kapisiz_plan: kaynakta kapı olup çıkarımda düşenler (rapor: P1051)."}


# Sır desenleri. Telefon deseni (İE-08, 12.10.2026): önünde rakam, nokta ya da virgül olan ya da arkasında rakam ya da ondalık devamı
# (".5", ",5") gelen "905…" dizileri numara sayılmaz; IFC ve JSON'daki ondalıklar (ör. 6.9050000000000002, 19050000000.5) böyle elenir.
# Gerçek numara (tek başına, parantezli, cümle sonunda noktayla, "wa_id=…;" içinde) yakalanmaya devam eder (testler/test_sir_taramasi.py).
SIR_DESENLERI = [r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{10,}", r"EAA[A-Za-z0-9]{20,}", r"PORTMAN_API_TOKEN=[0-9a-f]{20,}", r"(?<![\d.,])905\d{9}(?!\d|[.,]\d)",
                 r"Bearer [A-Za-z0-9._-]{16,}", r"(?:[Pp]assword|[Pp]arola|[Ss]ifre|[Şş]ifre)\s*[:=]\s*['\"][^'\"]{4,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"]
SIR_RX = re.compile("|".join(f"(?:{d})" for d in SIR_DESENLERI))
TARANMAYAN_UZANTI = (".dxf", ".png", ".jpg", ".jpeg", ".ttf", ".pdf", ".zip", ".xlsx", ".pyc")


def beklenen_bulgu(b: dict) -> bool:
    """Bilinen, sır olmayan bulgular: kanal/tests içindeki sahte sabitler ('test-app-secret'), bu betiğin kendi metni ve
    vps/kapi_d_dogrula.sh'deki parola deseni yanlış pozitifi (rolün parolası olup olmadığını yazdıran SQL; dosya tarihli kayıttır,
    dokunulmaz — İE-08, 12.10.2026; önce 'bilinen tek fark' olarak dogrula.py'de taşınıyordu)."""
    d, o = b["dosya"], b["ornek"]
    return (d.startswith("kanal/tests/") and "test-app-sec" in o) or d == "denetim/kos.py" or (d == "vps/kapi_d_dogrula.sh" and b["satir"] == 25)


def sir_taramasi(root: Path | None = None) -> dict:
    kok = root or ROOT
    bulgular = []
    for p in kok.rglob("*"):
        if not p.is_file() or p.suffix.lower() in TARANMAYAN_UZANTI or "cikti" in p.parts or ".git" in p.parts:
            continue
        try:
            metin = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, satir in enumerate(metin.splitlines(), 1):
            if SIR_RX.search(satir):
                bulgular.append({"dosya": str(p.relative_to(kok)), "satir": i, "ornek": re.sub(r"[0-9A-Za-z]{6,}", lambda m_: m_.group(0)[:3] + "…", satir.strip())[:120]})
    beklenen = [b for b in bulgular if beklenen_bulgu(b)]
    return {"passed": len(bulgular) == len(beklenen), "sayilar": {"bulgu": len(bulgular), "beklenen_sahte": len(beklenen)}, "bulgular": bulgular[:50],
            "not": "Beklenen: kanal/tests içindeki sahte numara/sır sabitleri, bu betik ve vps/kapi_d_dogrula.sh:25 (parola deseni yanlış pozitifi). Başka her bulgu incelenmeli."}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--planlar", action="store_true", help="16 katalog planını da koş (dakikalar sürer)")
    a = ap.parse_args()
    CIKTI.mkdir(parents=True, exist_ok=True)
    sonuc = {"basladi": time.strftime("%Y-%m-%d %H:%M:%S"), "adimlar": {}}
    adim(sonuc, "ortam", ortam)
    adim(sonuc, "girdi_hashleri", lambda: {"hashler": girdi_hashleri()})
    adim(sonuc, "beyin_harness", harness)
    adim(sonuc, "motor_altin_6x8", lambda: motor_altin("is_emri/ALTIN_2plus1_6x8.json", "altin_6x8", {"dis_olcu": [773.0, 1014.0]}))
    adim(sonuc, "motor_altin_yan_6x8p5_bom", lambda: motor_altin("is_emri/YAN_VERANDALI_2plus1_6x8p5.json", "altin_yan", {"dis_olcu": [773.0, 1076.75]}, "ref_yan/BOM_SAYIM_KAYDI.json"))
    adim(sonuc, "motor_p6001", lambda: motor_altin("is_emri/P6001_2plus1_6x6.json", "p6001", {"dis_olcu": [773.0, 763.0]}))
    adim(sonuc, "cikarici_p6001_altin", cikarici_p6001)
    if a.planlar:
        adim(sonuc, "cikarici_16_plan", planlar_16)
    adim(sonuc, "sir_taramasi", sir_taramasi)
    sonuc["bitti"] = time.strftime("%Y-%m-%d %H:%M:%S")
    sonuc["ozet"] = {k: v["durum"] for k, v in sonuc["adimlar"].items()}
    (CIKTI / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nÖZET:", json.dumps(sonuc["ozet"], ensure_ascii=False)); print("→", CIKTI / "sonuc.json")
    return 0 if all(v == "passed" for v in sonuc["ozet"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
