"""İE-44 · Havuz evlerine toplu çatı seçenekleri: Motor kuralla çizer, havuz denetimi süzer, Lokman tek sayfada onaylar.

Dayanak: Lokman, 16 Kasım 2026 08:10:32 ve 08:17:09 UTC mesajları (çatı seçeneği yalnız 88 m²'de; çatılar kuralla çizilsin), 08:21:45 kartı
"Toplu çizilsin, ben onaylayayım" ("Motor havuzdaki evlerin çatılarını çizer ve denetler; tek sayfada onaylarsınız"). Kural ailesi D-83'ten
(PA-06'da Lokman'ın seçtiği üç çatı: evin çatısı, kırma, mahya önde + salonun üstünde cumba).

Bu araç YALNIZ OKUR: hiçbir kayda yazmaz. Her ev için seçenekleri kurar, Motor'la çizer, denetler, görselleri ve sonucu verilen klasöre yazar.
Kayıt Lokman'ın kararından sonra `araclar/cati_varyanti_kaydet.py` ile olur (ev başına bir komut; `--kaydet-komutlari` yazdırır).

Seçenekler (harf, ad; evin kendi çatısıyla aynı olan kurulmaz):
  K  Kırma               dört düzlem, kalkan yok, mahya uzun kenar boyunca (`cati_prefabrik`, eşit eğim); eğim, saçak, topuk evin çatısından.
                         Girintili gövdede ve açık mahal çatısı (`mahal_catilari`) olan evde Motor kırma kurmaz: "çizilemedi" yazılır.
  C  Beşik + salonda     mahya ön cepheye paralel beşik; salonun ön duvarı boyunca çıkıntısız cumba, ana makaslar cumba makasından
     cumba               (`ana_makas: cumba_makasindan`; PA-04 ve PA-06-C gibi). Cumbanın ucu: köşede gövdenin dış yüzü, açık komşuda
                         (veranda) komşunun yüzü, kapalı komşuda aradaki duvarın ekseni. Salon ön cepheye değmiyorsa ya da ön cephenin
                         %80'inden genişse kurulmaz.
  B  Beşik               evin kırmasız ya da cumbasız hâli, aynı mahya yönüyle.

Her seçenek için denetim: (1) Motor kurar ve çizim doğrulaması geçer (K23); (2) plan evinkiyle aynı (Motor'un brüt alanı ve pano sayısı);
(3) havuz denetimi (D-112, BK-47: `araclar/havuz_denetimi.py`; hata sınıfı HD-01, 03, 04, 05, 08, 10 seçeneği düşürür, uyarı yazılır).
Mühürlü evin (kaynağı `KARARLAR/muhurlu.json`'da kilitli) seçenekleri çizilir ama "mühürlü" işaretlenir: eklemek için Lokman'a ayrıca sorulur
(D-83 › Kapsam dışı). Zaten çatı seçeneği olan ev (`beyin/veri/cati_varyantlari/`) atlanır.

    python -m araclar.cati_secenekleri_toplu --cikti <klasör> [--ev PA-09 PA-12 …] [--is 4]
    python -m araclar.cati_secenekleri_toplu --cikti <klasör> --kaydet-komutlari --karar D-NN [--ev …]   # onaydan sonra

LLM, ağ ve sunucu yok.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
import re
import shlex
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
VERI = KOK / "beyin" / "veri"

ADLAR = {"K": "Kırma", "C": "Beşik + salonda cumba", "B": "Beşik"}
SIRA = ("K", "C", "B")
CATI_ALANLARI = ("egim_yuzde", "sacak_cm", "topuk_cm")          # evin çatısından aynen
CUMBA_EN_COK = 0.8                                              # salon ön cephenin bu oranından genişse cumba anlamsız (bütün cephe)


# ---------------------------------------------------------------- evler

def muhurlu_yerler(kok: Path = KOK) -> dict[str, str]:
    """Mühür kilitlerinin dosya yolları → mühür kodu (`KARARLAR/muhurlu.json`; `yol#alan` ve `yol::ad` dosyaya indirgenir)."""
    d = json.loads((kok / "KARARLAR" / "muhurlu.json").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for m in d.get("muhurler") or []:
        for k in m.get("kilitler") or []:
            yer = re.split(r"#|::", str(k.get("yer") or ""))[0]
            if yer:
                out.setdefault(yer, m.get("kod"))
    return out


def evler(kok: Path = KOK) -> list[dict]:
    """Havuzdaki geçerli prefabrik evler: {kod, gosterim, sablon (yol), kayit, muhur, secenekli}. Sıra: adaylar_prefabrik.json, havuz/PA*.json."""
    veri = kok / "beyin" / "veri"
    kayitlar = list(json.loads((veri / "adaylar_prefabrik.json").read_text(encoding="utf-8")))
    kayitlar += [json.loads(f.read_text(encoding="utf-8")) for f in sorted((veri / "havuz").glob("PA*.json"))]
    secenekli = {f.stem.upper() for f in (veri / "cati_varyantlari").glob("*.json")}
    muhur = muhurlu_yerler(kok)
    out = []
    for k in kayitlar:
        if k.get("durum", "gecerli") != "gecerli" or not k.get("sablon"):
            continue
        dosya = str((k.get("kaynak") or {}).get("dosya") or "")
        out.append({"kod": str(k["kod"]).upper(), "gosterim": k.get("gosterim") or k["kod"], "sablon": str(kok / "is_emri" / k["sablon"]),
                    "m2": k.get("katalog_m2"), "oda": k.get("oda_programi"), "muhur": muhur.get(dosya),
                    "secenekli": str(k["kod"]).upper() in secenekli})
    return out


# ---------------------------------------------------------------- çatı adları ve seçenekler

def cati_adi(c: dict, plan=None) -> str:
    """Evin kendi çatısının bayiye giden adı (kart): "Beşik, kalkan önde", "Kırma", "Beşik + cumba" …"""
    tip = c.get("tip", "besik")
    ek = []
    if c.get("mahal_catilari"):
        ek.append("verandada tek eğim" if all(m.get("tip") == "tek_yon" for m in c["mahal_catilari"]) else "verandada kırma")
    if tip == "kirma":
        ad = "Kırma, bir ucu kalkan" if c.get("kalkan_ucu") else "Kırma"
    elif tip == "besik_cumba":
        ad = "Beşik + iki cumba" if len(c.get("cumbalar") or []) > 1 else "Beşik + cumba"
    else:
        ad = "Beşik, kalkan önde" if c.get("makas_ekseni", "x") == "x" else "Beşik, kalkan yanda"
    return ad + (f" ({', '.join(ek)})" if ek else "")


def _taban(c: dict) -> dict:
    return {k: c[k] for k in CATI_ALANLARI if k in c}


def _salon_cumbasi(plan) -> tuple[list[float] | None, str]:
    """Salonun ön duvarı boyunca cumba aralığı [bas, bit] (ön cephede, gövdenin sol dış yüzünden cm) ya da (None, neden)."""
    from motor import geometry as G
    from shapely.geometry import box
    x0, y0, x1, y1 = (float(v) for v in G.govde_kutusu(plan))
    t_dis = max((2 * d.h for d in plan.duvarlar if d.tur == "dis"), default=10.0)
    salonlar = [m for m in plan.mahaller.values() if m.tur == "salon" and not m.acik]
    if not salonlar:
        return None, "evde salon yok"
    serit = box(x0, y0, x1, y0 + t_dis + 2.0)                    # ön duvarın içi: salon buraya değiyorsa ön cephededir
    adaylar = []
    for s in salonlar:
        kes = s.poly.intersection(serit)
        if kes.area > 1.0:
            adaylar.append((kes.bounds[0], kes.bounds[2], s))
    if not adaylar:
        return None, "salon ön cepheye değmiyor (önünde veranda ya da başka oda var)"
    xa, xb, s = max(adaylar, key=lambda t: t[1] - t[0])

    def uc(x: float, yon: int) -> float:
        kenar = x0 if yon < 0 else x1
        if abs(x - kenar) <= t_dis + 2.0:
            return kenar                                         # köşe: gövdenin dış yüzü
        komsular = []
        for m in plan.mahaller.values():
            if m is s:
                continue
            kes = m.poly.intersection(box(x0, y0, x1, y0 + t_dis + 40.0))
            if kes.area <= 1.0:
                continue
            bx0, _, bx1, _ = kes.bounds
            if yon < 0 and bx1 <= x + 1.0 and x - bx1 <= t_dis + 4.0:
                komsular.append((m, bx1))
            if yon > 0 and bx0 >= x - 1.0 and bx0 - x <= t_dis + 4.0:
                komsular.append((m, bx0))
        if not komsular:
            return x - yon * t_dis / 2                            # komşu bulunamadı: duvarın ekseni (yarım dış duvar)
        m, yuz = komsular[0]
        return yuz if m.acik else (x + yuz) / 2                  # açık komşu: onun yüzü; kapalı komşu: aradaki duvarın ekseni

    bas, bit = uc(xa, -1) - x0, uc(xb, +1) - x0
    if bit - bas > CUMBA_EN_COK * (x1 - x0):
        return None, f"salon ön cephenin %{round(100 * (bit - bas) / (x1 - x0))}'ini kaplıyor; cumba bütün cephe olur"
    return [round(bas, 2), round(bit, 2)], ""


def secenekler(ie: dict, plan) -> list[dict]:
    """Evin çatı seçenekleri: [{harf, ad, cati (dict) | None, neden}] (evin kendi türü olan kurulmaz; kurulamayan nedeniyle)."""
    from motor import geometry as G
    c = ie.get("cati") or {}
    tip = c.get("tip", "besik")
    x0, y0, x1, y1 = (float(v) for v in G.govde_kutusu(plan))
    uzun_x = (x1 - x0) >= (y1 - y0)
    out = []
    # K · kırma
    if tip != "kirma":
        if plan.girintili:
            out.append({"harf": "K", "ad": ADLAR["K"], "cati": None, "neden": "gövde girintili: Motor kırmayı yalnız dikdörtgen gövdede kurar"})
        elif c.get("mahal_catilari"):
            out.append({"harf": "K", "ad": ADLAR["K"], "cati": None,
                        "neden": "verandanın kendi çatısı var (tek eğim ya da köşe kırması): Motor kırmayı bununla birlikte kurmaz"})
        else:
            out.append({"harf": "K", "ad": ADLAR["K"], "neden": "",
                        "cati": {"tip": "kirma", **_taban(c), "makas_yonu": "kisa_kenar", "makas_ekseni": "y" if uzun_x else "x"}})
    # C · beşik + salonda cumba
    if tip != "besik_cumba":
        if plan.girintili:
            out.append({"harf": "C", "ad": ADLAR["C"], "cati": None, "neden": "gövde girintili: çıkıntısız cumba girintisiz gövdede kurulur"})
        elif c.get("mahal_catilari"):
            out.append({"harf": "C", "ad": ADLAR["C"], "cati": None,
                        "neden": "verandanın kendi çatısı var: Motor cumbayı bununla birlikte kurmaz"})
        else:
            ara, neden = _salon_cumbasi(plan)
            if ara is None:
                out.append({"harf": "C", "ad": ADLAR["C"], "cati": None, "neden": neden})
            else:
                out.append({"harf": "C", "ad": ADLAR["C"], "neden": "",
                            "cati": {"tip": "besik_cumba", **_taban(c), "makas_yonu": "kisa_kenar" if uzun_x else "uzun_kenar",
                                     "makas_ekseni": "y",
                                     "cumbalar": [{"cephe": "on", "bas_cm": ara[0], "bit_cm": ara[1], "cikinti_cm": 0,
                                                   "ana_makas": "cumba_makasindan"}]}})
    # B · beşik
    if tip != "besik":
        b = {"tip": "besik", **_taban(c), "makas_yonu": c.get("makas_yonu", "kisa_kenar"), "makas_ekseni": c.get("makas_ekseni", "x")}
        if c.get("mahal_catilari"):
            b["mahal_catilari"] = copy.deepcopy(c["mahal_catilari"])
        if plan.girintili:
            out.append({"harf": "B", "ad": ADLAR["B"], "cati": None,
                        "neden": "gövde girintili: cumbasız beşik girintiyi örtmez (çatı gövdenin dış çizgisinden taşar)"})
        else:
            out.append({"harf": "B", "ad": ADLAR["B"], "cati": b, "neden": ""})
    return sorted(out, key=lambda s: SIRA.index(s["harf"]))


# ---------------------------------------------------------------- çizim ve denetim

def ciz(ie: dict, png: Path) -> dict:
    """Motor'u geçici klasörde koşar; doğrulama geçerse çatı görselini (ön ve sol görünüş) yazar. Dönen: {gecti, brut_cm2, pano, uyarilar,
    hata}. `cati_varyanti_kaydet.ciz` ile aynı çıktı (aynı Motor çağrısı, aynı kırpma); fark: durmaz, sonucu döner."""
    from motor import dxf_out, bayi_gorseli as BG, geometry as G, prefabrik_liste as PL
    try:
        plan = G.kur(copy.deepcopy(ie))
        oz = {"brut_cm2": round(PL.bina_brut_cm2(plan)), "pano": len(plan.panolar), "uyarilar": list(plan.uyarilar)}
    except Exception as e:                                       # IsEmriHatasi dahil
        return {"gecti": False, "hata": f"Motor kuramadı: {e}"}
    with tempfile.TemporaryDirectory() as tmp:
        yerler: dict = {}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                m = dxf_out.uret(copy.deepcopy(ie), Path(tmp), bolge_yerleri=yerler)
        except Exception as e:
            return {"gecti": False, "hata": f"çizim üretilemedi: {e}", **oz}
        if not m.get("validation_passed") or not m.get("pdf"):
            return {"gecti": False, "hata": f"çizim doğrulaması geçmedi (K23): {'; '.join(map(str, m.get('warnings') or []))[:300]}", **oz}
        BG.cati_gorseli(Path(tmp) / m["pdf"], yerler, png)
        oz["uyarilar"] = list(dict.fromkeys(oz["uyarilar"] + list(m.get("warnings") or [])))
    return {"gecti": True, "hata": "", **oz}


def denetle(ie: dict) -> dict:
    """Havuz denetimi (D-112): {dur: [hata], uyari: [uyarı]}. Araç yoksa (BK-47 henüz main'de değilse) dur'a yazılır: denetimsiz seçenek yok."""
    try:
        from araclar import havuz_denetimi as HD
    except ImportError:
        return {"dur": ["havuz denetimi aracı yok (araclar/havuz_denetimi.py, BK-47); denetimsiz seçenek havuza girmez"], "uyari": []}
    with contextlib.redirect_stdout(io.StringIO()):
        dur, uyari = HD.kayit_kapisi(HD.denetle_prefabrik(copy.deepcopy(ie)))
    return {"dur": dur, "uyari": uyari}


def ev_isle(ev: dict, cikti: Path) -> dict:
    """Bir ev: evin çatısı görseli, seçenekler, her seçeneğin çizimi ve denetimi. Süreç havuzunda da koşar."""
    from motor import geometry as G
    ie = json.loads(Path(ev["sablon"]).read_text(encoding="utf-8"))
    sonuc = {**{k: ev[k] for k in ("kod", "gosterim", "m2", "oda", "muhur")}, "cati": ie.get("cati"), "secenekler": []}
    sonuc["cati_adi"] = cati_adi(ie.get("cati") or {})
    evin = ciz(ie, cikti / f"{ev['kod']}_cati.png")
    sonuc["evin_cizimi"] = evin
    if not evin["gecti"]:
        sonuc["neden"] = f"evin kendi çizimi geçmedi: {evin.get('hata')}"
        return sonuc
    plan = G.kur(copy.deepcopy(ie))
    for s in secenekler(ie, plan):
        kod = f"{ev['kod']}{s['harf']}"
        r = {"harf": s["harf"], "kod": kod, "gosterim": f"{ev['gosterim']}-{s['harf']}", "ad": s["ad"], "cati": s["cati"]}
        if s["cati"] is None:
            r.update(durum="cizilemedi", neden=s["neden"])
            sonuc["secenekler"].append(r)
            continue
        v = copy.deepcopy(ie)
        v["cati"] = s["cati"]
        v["is_emri_no"] = f"PM-ADAY-{kod}"
        v.setdefault("yapi", {})["referans_model"] = r["gosterim"]
        oz = ciz(v, cikti / f"{kod}.png")
        r["cizim"] = oz
        if not oz["gecti"]:
            r.update(durum="cizilemedi", neden=oz["hata"])
        elif (oz["brut_cm2"], oz["pano"]) != (evin["brut_cm2"], evin["pano"]):
            r.update(durum="cizilemedi", neden=f"plan değişti (brüt {oz['brut_cm2']} ↔ {evin['brut_cm2']} cm², pano {oz['pano']} ↔ {evin['pano']})")
        else:
            d = denetle(v)
            r["denetim"] = d
            r["yeni_uyarilar"] = [u for u in oz["uyarilar"] if u not in evin["uyarilar"]]
            r.update(durum="denetimden_gecmedi" if d["dur"] else "gecti", neden="; ".join(d["dur"]))
        sonuc["secenekler"].append(r)
    return sonuc


def _isci(is_: tuple[dict, str]) -> dict:
    ev, cikti = is_
    try:
        return ev_isle(ev, Path(cikti))
    except Exception as e:                                       # bir ev bütün koşuyu düşürmez; hata sayfada görünür
        return {**{k: ev[k] for k in ("kod", "gosterim", "m2", "oda", "muhur")}, "secenekler": [],
                "neden": f"araç hatası: {type(e).__name__}: {e}"}


# ---------------------------------------------------------------- onay sayfası

NEDEN_KALIBI = (                                                  # denetim bulgusu → Lokman'a giden sade cümle (kod adı yok)
    (r"HD-10", "3D modelde kırma çatı beşik çıkıyor; 3D bakım işi bitince yeniden denetlenir."),
    (r"HD-08", "3D modeldeki makas sayısı yükleme listesinden farklı; 3D bakım işi bitince yeniden denetlenir."),
    (r"HD-03", "Yükleme listesi bu çatıda yazılamıyor; liste bakım işi bitince yeniden denetlenir."),
    (r"HD-04", "Yükleme listesinde adedi olmayan satır var."),
    (r"HD-05", "3D model kurulamıyor."),
    (r"HD-01", "Motor çizimi doğrulamadı."),
)


def neden_yazisi(s: dict) -> str:
    """Seçeneğin neden geçmediği, Lokman'ın okuyacağı tek cümleyle (ayrıntı sonuc.json'da)."""
    if s.get("durum") == "denetimden_gecmedi":
        cumleler = [c for k, c in NEDEN_KALIBI if re.search(k, s.get("neden") or "")]
        return " ".join(dict.fromkeys(cumleler)) or (s.get("neden") or "")[:200]
    n = s.get("neden") or ""
    if "kisa_kenar" in n and "makas" in n:
        return "Evin köşe yönü bu makas yönüne izin vermiyor (Motor kurmadı)."
    if "kırma mahyası" in n:
        return "Ev kareye çok yakın: kırmanın mahyası 15 cm'den kısa kalıyor (Motor kurmadı)."
    if "taşan veranda görünüşte çizilmez" in n:
        return "Taşan verandası var: Motor beşik dışı çatıyı taşan verandayla birlikte çizmiyor."
    if n.startswith("Motor kuramadı") or n.startswith("çizim"):
        return "Motor bu çatıyı kurmadı: " + re.sub(r"^(Motor kuramadı|çizim üretilemedi): ", "", n)[:160]
    return n[:1].upper() + n[1:]


def uyari_yazisi(s: dict) -> list[str]:
    """Geçen seçeneğin mühendis notları (sade): makas uzun kenarı geçer, makas yeri düzensiz."""
    out = []
    metin = " ".join((s.get("denetim") or {}).get("uyari") or []) + " " + " ".join(s.get("yeni_uyarilar") or [])
    if "kisa_kenar x" in metin or "Makas y'yi geçiyor" in metin:
        out.append("Makas evin uzun kenarını geçiyor; mühendis bakar (87 m²'nin cumbalı çatısındaki gibi).")
    if "pano ekleri düzensiz" in metin:
        out.append("3D modelde makaslar eşit aralıkla yerleşti (saçak duvarının pano ekleri düzensiz).")
    return out


def sayfa(sonuc: dict, cikti: Path) -> Path:
    """Tek onay sayfası (HTML; görseller aynı klasörde, göreli yolla). Bölümler: hazır, denetimden geçmedi, çizilemedi, mühürlü evler."""
    import html
    h = html.escape
    evler_ = sorted(sonuc["evler"], key=lambda e: (float(e.get("m2") or 0), e["gosterim"]))
    hazir, bekleyen, cizilemeyen, muhurlu = [], [], [], []
    for e in evler_:
        (muhurlu if e.get("muhur") else hazir).append(e)
    say = {"gecti": 0, "denetimden_gecmedi": 0, "cizilemedi": 0}
    for e in evler_:
        for s in e.get("secenekler") or []:
            if not e.get("muhur") or s["durum"] == "cizilemedi":
                say[s["durum"]] += 1
            if s["durum"] == "denetimden_gecmedi" and not e.get("muhur"):
                bekleyen.append((e, s))
            if s["durum"] == "cizilemedi":
                cizilemeyen.append((e, s))

    def baslik(e: dict) -> str:
        m2 = f"{float(e['m2']):g}".replace(".", ",") if e.get("m2") is not None else "?"
        return f"{m2} m² · {h(str(e.get('oda') or ''))} <span class='kod'>{h(e['gosterim'])}</span>"

    def kart(png: str, ad: str, alt: str = "", notlar: list[str] | None = None, sinif: str = "") -> str:
        n = "".join(f"<li>{h(x)}</li>" for x in notlar or [])
        return (f"<figure class='kart {sinif}'><img src='{h(png)}' alt='{h(ad)}' loading='lazy'><figcaption><b>{h(ad)}</b>"
                f"{f'<span class=alt>{h(alt)}</span>' if alt else ''}{f'<ul>{n}</ul>' if n else ''}</figcaption></figure>")

    def ev_satiri(e: dict, durumlar: tuple) -> str:
        secs = [s for s in e.get("secenekler") or [] if s["durum"] in durumlar]
        if not secs:
            return ""
        kartlar = [kart(f"{e['kod']}_cati.png", "Evin çatısı", e.get("cati_adi") or "", sinif="ev")]
        for s in secs:
            if s["durum"] == "gecti":
                kartlar.append(kart(f"{s['kod']}.png", s["ad"], s["gosterim"], uyari_yazisi(s), "hazir"))
            else:
                kartlar.append(kart(f"{s['kod']}.png", s["ad"], s["gosterim"], [neden_yazisi(s)], "bekler"))
        return f"<section class='ev'><h3>{baslik(e)}</h3><div class='kartlar'>{''.join(kartlar)}</div></section>"

    hazir_html = "".join(ev_satiri(e, ("gecti",)) for e in hazir) or "<p>Hazır seçenek yok.</p>"
    bekleyen_evler = [e for e in hazir if any(s["durum"] == "denetimden_gecmedi" for s in e.get("secenekler") or [])]
    bekleyen_html = "".join(ev_satiri(e, ("denetimden_gecmedi",)) for e in bekleyen_evler) or "<p>Yok.</p>"
    satirlar = "".join(f"<tr><td>{baslik(e)}{' <span class=kod>mühürlü ev</span>' if e.get('muhur') else ''}</td><td>{h(s['ad'])}</td>"
                       f"<td>{h(neden_yazisi(s))}</td></tr>" for e, s in cizilemeyen)
    muhur_html = "".join(ev_satiri(e, ("gecti", "denetimden_gecmedi")) for e in muhurlu)
    muhur_bolum = (f"<section class='bolum muhur'><h2>4. Mühürlü evler: ayrıca sorulur</h2><p class='not'>Bu evlerin çatısı mühürlü. "
                   f"Seçenek eklemek için ayrıca \"evet\" demeniz gerekir.</p>{muhur_html}</section>") if muhur_html else ""
    atlanan = ", ".join(sonuc.get("atlanan") or []) or "yok"
    ev_sayisi = len(evler_)
    govde = f"""<title>Havuz Çatı Seçenekleri</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
/* Düzen: tek sütun; her ev bir satır, evin çatısı solda, seçenekleri yanında (telefonda alt alta) */
:root {{ --bg:#f6f7f5; --yuzey:#ffffff; --fg:#1d2420; --ince:#5d6862; --cizgi:#d9ddd8; --hazir:#1f7a4d; --hazir-zemin:#e6f3ec;
  --bekler:#9a5b00; --bekler-zemin:#fbf1e1; --muhur:#5b4a8a; --font:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
  --baslik:"Space Grotesk","Inter",system-ui,sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#141816; --yuzey:#1c211f; --fg:#e8ece9; --ince:#a3ada7;
  --cizgi:#313834; --hazir:#5cc493; --hazir-zemin:#173126; --bekler:#e2a24a; --bekler-zemin:#33280f; --muhur:#b4a3e6; color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#141816; --yuzey:#1c211f; --fg:#e8ece9; --ince:#a3ada7; --cizgi:#313834; --hazir:#5cc493;
  --hazir-zemin:#173126; --bekler:#e2a24a; --bekler-zemin:#33280f; --muhur:#b4a3e6; color-scheme:dark }}
body {{ background:var(--bg); color:var(--fg); font-family:var(--font); font-size:15px; line-height:1.5;
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); padding-block:24px 48px }}
main {{ max-width:1180px; margin:0 auto; display:grid; gap:28px }}
h1,h2,h3 {{ font-family:var(--baslik); text-wrap:balance; margin:0 }}
h1 {{ font-size:1.7rem }} h2 {{ font-size:1.25rem; padding-bottom:6px; border-bottom:1px solid var(--cizgi) }} h3 {{ font-size:1.02rem }}
p {{ margin:0; max-width:70ch }}
.ozet {{ display:flex; flex-wrap:wrap; gap:12px }}
.sayi {{ background:var(--yuzey); border:1px solid var(--cizgi); border-radius:8px; padding:10px 14px; min-width:150px; flex:1 1 150px }}
.sayi b {{ display:block; font-size:1.6rem; font-variant-numeric:tabular-nums; font-family:var(--baslik) }}
.sayi.h b {{ color:var(--hazir) }} .sayi.b b {{ color:var(--bekler) }}
.bolum {{ display:grid; gap:14px }}
.ev {{ background:var(--yuzey); border:1px solid var(--cizgi); border-radius:8px; padding:12px; display:grid; gap:10px; min-width:0 }}
.kod {{ color:var(--ince); font-weight:400; font-size:.85rem; margin-left:6px }}
.kartlar {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:10px }}
.kart {{ margin:0; border:1px solid var(--cizgi); border-radius:6px; overflow:hidden; display:flex; flex-direction:column; min-width:0 }}
.kart img {{ background:#fff; width:100%; height:auto; display:block }}
.kart figcaption {{ padding:8px 10px; display:grid; gap:2px; font-size:.9rem }}
.kart .alt {{ color:var(--ince); font-size:.82rem }}
.kart ul {{ margin:4px 0 0; padding-left:18px; color:var(--ince); font-size:.84rem }}
.kart.hazir {{ border-color:var(--hazir) }} .kart.hazir figcaption {{ background:var(--hazir-zemin) }}
.kart.bekler {{ border-color:var(--bekler) }} .kart.bekler figcaption {{ background:var(--bekler-zemin) }}
.tablo {{ overflow-x:auto }} table {{ border-collapse:collapse; width:100%; font-size:.9rem }}
td,th {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--cizgi); vertical-align:top }}
.muhur h2 {{ color:var(--muhur) }}
.not {{ color:var(--ince); font-size:.88rem }}
</style>
<main>
<header class="bolum"><h1>Havuz evlerinin çatı seçenekleri</h1>
<p>Motor havuzdaki {ev_sayisi} prefabrik evin çatı seçeneklerini kuralla çizdi ve her birini havuz denetiminden geçirdi. Her seçenekte plan
evinkiyle aynıdır; yalnız çatı değişir. Görselde ön ve sol görünüş vardır; bayi de bunu görür.</p>
<p class="not">Kural: kırma (dört yüz, mahya uzun kenar boyunca), beşik + salonun üstünde cumba (mahya önde, 87 m²'deki gibi), beşik (cumbasız ya
da kırmasız). Eğim, saçak ve topuk evin kendi çatısından. Zaten çatı seçeneği olan ev: {h(atlanan)}.</p></header>
<div class="ozet">
<div class="sayi h"><b>{say['gecti']}</b>seçenek hazır</div>
<div class="sayi b"><b>{say['denetimden_gecmedi']}</b>seçenek çizildi, denetimi bekliyor</div>
<div class="sayi"><b>{say['cizilemedi']}</b>seçenek Motor'da çizilemedi</div>
</div>
<section class="bolum"><h2>1. Hazır: denetimden geçti</h2><p class="not">Onaylarsanız bu seçenekler havuza girer. Bayinin WhatsApp'ta görmesi için mühendis kabulü ve canlıya geçiş ayrıca sorulur.</p>{hazir_html}</section>
<section class="bolum"><h2>2. Çizildi, denetimi bekliyor</h2><p class="not">Çizim doğru görünüyorsa söyleyin. Bakım işi bitince Motor bunları yeniden denetler; geçen girer.</p>{bekleyen_html}</section>
<section class="bolum"><h2>3. Motor'da çizilemedi</h2><div class="tablo"><table><thead><tr><th>Ev</th><th>Seçenek</th><th>Neden</th></tr></thead><tbody>{satirlar}</tbody></table></div></section>
{muhur_bolum}
</main>"""
    yol = cikti / "onay_sayfasi.html"
    yol.write_text(govde, encoding="utf-8")
    return yol


# ---------------------------------------------------------------- kayıt komutları (onaydan sonra)

def kaydet_komutlari(sonuc: list[dict], karar: str, onaylanan: set[str] | None = None) -> list[str]:
    """Geçen seçeneklerden ev başına `cati_varyanti_kaydet.py` komutu (onaylanan verilirse yalnız o kodlar; mühürlü ev yalnız açıkça onaylanırsa)."""
    out = []
    for ev in sonuc:
        sec = [s for s in ev.get("secenekler") or [] if s.get("durum") == "gecti"
               and (onaylanan is None and not ev.get("muhur") or onaylanan is not None and s["gosterim"].upper() in onaylanan)]
        if not sec:
            continue
        p = ["python3", "araclar/cati_varyanti_kaydet.py", "--taban", ev["gosterim"], "--karar", karar, "--cati-adi", ev["cati_adi"]]
        for s in sec:
            p += ["--varyant", s["harf"], s["ad"], json.dumps(s["cati"], ensure_ascii=False)]
        p += ["--kaynak", f"İE-44 toplu çatı seçenekleri ({karar})"]
        out.append(" ".join(shlex.quote(x) for x in p))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cikti", required=True, help="görseller ve sonuc.json bu klasöre")
    ap.add_argument("--ev", nargs="*", default=[], help="yalnız bu evler (PA-09 …); verilmezse havuzdaki bütün prefabrik evler")
    ap.add_argument("--is", dest="isci", type=int, default=1, help="paralel süreç sayısı")
    ap.add_argument("--kaydet-komutlari", action="store_true", help="sonuc.json'dan kayıt komutlarını yazdır (çizmez)")
    ap.add_argument("--sayfa", action="store_true", help="yalnız sonuc.json'dan onay sayfasını yeniden yaz (çizmez)")
    ap.add_argument("--karar", default="", help="--kaydet-komutlari ile: Lokman'ın kararı (D-NN)")
    ap.add_argument("--onaylanan", nargs="*", default=None, help="--kaydet-komutlari ile: yalnız bu kodlar (PA-09-K …)")
    a = ap.parse_args(argv)
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    if a.kaydet_komutlari:
        if not re.fullmatch(r"D-\d{2,3}", a.karar):
            print("DUR: --karar D-NN gerekir (seçenek yalnız Lokman'ın kararıyla)"); return 2
        sonuc = json.loads((cikti / "sonuc.json").read_text(encoding="utf-8"))["evler"]
        onay = {x.upper() for x in a.onaylanan} if a.onaylanan is not None else None
        print("\n".join(kaydet_komutlari(sonuc, a.karar, onay)))
        return 0
    if a.sayfa:
        print(sayfa(json.loads((cikti / "sonuc.json").read_text(encoding="utf-8")), cikti))
        return 0
    from beyin.katalog import Katalog
    istenen = {Katalog.kod_normalize(k) for k in a.ev}
    secilen = [e for e in evler() if not istenen or e["kod"] in istenen]
    atlanan = [e["gosterim"] for e in secilen if e["secenekli"]]
    isler = [(e, str(cikti)) for e in secilen if not e["secenekli"]]
    if a.isci > 1:
        from multiprocessing import get_context
        with get_context("spawn").Pool(a.isci) as p:
            sonuc = p.map(_isci, isler, chunksize=1)
    else:
        sonuc = [_isci(i) for i in isler]
    ozet = {"gecti": 0, "denetimden_gecmedi": 0, "cizilemedi": 0}
    for ev in sonuc:
        for s in ev.get("secenekler") or []:
            ozet[s["durum"]] = ozet.get(s["durum"], 0) + 1
        print(f"{ev['gosterim']}: " + ("; ".join(f"{s['harf']} {s['durum']}" + (f" ({s['neden'][:120]})" if s.get('neden') else "")
                                                for s in ev.get("secenekler") or []) or ev.get("neden", "seçenek yok")))
    kayit = {"ozet": ozet, "atlanan": atlanan, "evler": sonuc}
    (cikti / "sonuc.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sayfa(kayit, cikti)
    print(f"özet: {ozet}; zaten seçenekli (atlandı): {', '.join(atlanan) or 'yok'} → {cikti / 'sonuc.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
