"""İE-18 · Montaj rehberinin verisi (D-28): motorun planı, kart modeli ve yükleme listesi → tek şablonun (`sahne.js`) verisi.

    python -m araclar.paket.rehber.veri <İş Emri.json> <kart klasörü> <kart kodu> <liste.json> <çıktı.json> [--kod TK-01]

Şablon 62 m² rehberidir (hedef örnek, `testler/paket/rehber62/`); yapım ayrıntıları (pano katmanları, H, köşe direği, omegalar,
makas, betopan, Z, C kapama, saçak ve alın sacı, dere, iniş, doğrama) şablonda yazılı. Burada yalnız evin yerleri, ölçüleri, adetleri ve
yazıları kurulur; şema 62'nin verisiyle aynı (`testler/paket/rehber62/donustur.py`). Kaynaklar:

- **Plan** (`motor.geometry.kur`, `motor.ifc_uret.hazirla`): pano, açıklık, köşe direği, H (pano ekleri), oda poligonları, veranda
  kolon ve kirişleri, veranda çatıları. Pafta çerçevesi: x sol dış yüzden sağa, y ön dış yüzden arkaya (cm).
- **Kart modeli** (`python -m motor.kart_model`): kartlar ve katalog kodları, H türleri (kulaklı / kulaksız), makas, aşık ve iniş yerleri
  (`<kod>_model.ifc`), tavan omegası parçaları (`<kod>_kart_sayim.json`).
- **Yükleme listesi**: adetler ve listedeki satırlar (adım satırları, kimlik kartlarındaki "Liste" satırı).
- **Kural** (motorun modelinde olmayanlar): yavru makasın yeri (derinlik boyunca eşit aralık), veranda çatısında aşık sırası (motorun
  ana çatıdaki kuralı: mahyadan 60 cm), asma tavanın H'ı ve gözü (`tavan_h_aralik_m`), kalkan betopanının dizilimi (125 cm'ye sığan
  kalkanda 62 m²'deki gibi mahyadan iki yana 250'lik yatay levhalar, yüksek kalkanda 125'lik dik şeritler). Kartlarında kaynağı yazar.
- **Kartlar**: pano, H, köşe direği, makas, kapı, pencere, veranda kolon ve kirişi kart modelinden; aşık, omegalar, saçak ve alın sacı,
  Z, C kapama, mahya, dere, iniş, betopan ve sandviç panel `kart_bag` ile kartına bağlanır (62 m²'nin verisinde yok, orada "kart yok").
- **İç duvar kalınlığı** (İE-18 R1 ek 4): 60'lık ya da 100'lük (BK-18), liste üretecinin kuralıyla plandan; iç pano, alt çerçeve, çektirme
  U'su ve iç köşe yazıları onunla, iç H'ların kartı kart modelinden (`metin.ic_kal`; 62 m²'nin verisinde yok, şablon 60'lık alır).

Verandalar: gövdeden taşan (önde ya da arkada, ana çatıya paralel küçük beşik; TK-01) ve gövdenin içindeki (ana çatının altında, kolon
ve kiriş; AP-19; kolonsuzsa giriş nişi: önü açık, kirişi iki yandaki duvarı bağlar; TK-01 r06). Rehberin kuramadığı ev `Desteklenmiyor` atar; paket üreteci bunu "Yok: neden" diye yazar: beşik dışı çatı, mahyası
x yönünde (makaslar y'ye paralel), dizilimi arka-sol dışında, yan cephede ya da ana çatıya dik veranda çatısı.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]


class Desteklenmiyor(Exception):
    """Rehber üreteci bu evi kuramıyor; neden mesajda."""


def fmt(n, d=0) -> str:
    """Türkçe sayı: binlik nokta, ondalık virgül."""
    return f"{n:,.{d}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def fmtc(n) -> str:
    """Şablonun `fmtc`'si: iki haneye yuvarlar, gereksiz sıfır yazmaz (125,5; 100)."""
    v = round(n * 100) / 100
    s = repr(v)
    return (s[:-2] if s.endswith(".0") else s).replace(".", ",")


def kucuk(s: str) -> str:
    return (s or "").replace("I", "ı").replace("İ", "i").lower()


def oda_adi(ad: str, birlesen: list[str]) -> str:
    """Paftadaki mahal adından rehberdeki ad: "YATAK ODASI 1" → "Yatak odası 1", "E. BANYO" → "Ebeveyn banyosu"."""
    if ad == "E. BANYO":
        return "Ebeveyn banyosu"
    t = kucuk(ad)
    t = {"i": "İ", "ı": "I"}.get(t[:1], t[:1].upper()) + t[1:]
    if birlesen:
        t += " ve " + " ve ".join(kucuk(b) for b in birlesen)
    return t


def oda_kimligi(ad: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return re.sub(r"[^a-z0-9]", "", ad.translate(tr).lower()) or "oda"


def icinde(pt, poly) -> bool:
    x, y = pt
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def oda_sirasi(odalar: list[dict], baslangic: dict) -> tuple[list[str], dict[str, str]]:
    """Kapalı odaların dizilim sırası (arka-sol köşeden) ve birleşen mahaller (ANTRE → HOL). Dönen: (sıralı ana adlar, {birleşen: ana}).

    Önce arka duvara değen odalar soldan sağa, sonra sağ duvara değenler arkadan öne, ön duvara değenler sağdan sola, sol duvara değenler
    önden arkaya, en son hiçbir dış kenara değmeyenler. Bir oda bir yana değer: o yanda, kenarına dik izdüşümü örtüşen başka oda yoksa."""
    if baslangic != {"x": "min", "y": "max"}:
        raise Desteklenmiyor(f"dizilim başlangıcı {baslangic}; rehber yalnız arka-sol köşeden dizer")
    kapali = [o for o in odalar if not o.get("acik")]
    adlar = {o["ad"] for o in kapali}
    birles = {"ANTRE": "HOL"} if {"ANTRE", "HOL"} <= adlar else {}
    ana = [o["ad"] for o in kapali if o["ad"] not in birles]

    def kutu(ad):
        ps = [q for o in kapali if o["ad"] in [ad] + [b for b, h in birles.items() if h == ad] for q in o["poligon"]]
        return min(q[0] for q in ps), max(q[0] for q in ps), min(q[1] for q in ps), max(q[1] for q in ps)

    K = {a: kutu(a) for a in ana}
    ortus = lambda a0, a1, b0, b1: min(a1, b1) - max(a0, b0) > 1

    def deger(a, yan):
        x0, x1, y0, y1 = K[a]
        for b, (u0, u1, v0, v1) in K.items():
            if b == a:
                continue
            if yan == "arka" and v0 >= y1 - 1 and ortus(x0, x1, u0, u1):
                return False
            if yan == "on" and v1 <= y0 + 1 and ortus(x0, x1, u0, u1):
                return False
            if yan == "sag" and u0 >= x1 - 1 and ortus(y0, y1, v0, v1):
                return False
            if yan == "sol" and u1 <= x0 + 1 and ortus(y0, y1, v0, v1):
                return False
        return True

    sira = []
    for yan, anahtar in (("arka", lambda a: K[a][0]), ("sag", lambda a: -K[a][3]), ("on", lambda a: -K[a][1]), ("sol", lambda a: K[a][2])):
        sira += sorted((a for a in ana if a not in sira and deger(a, yan)), key=anahtar)
    sira += sorted((a for a in ana if a not in sira), key=lambda a: math.hypot(K[a][0], K[a][3]))
    return sira, birles


def dikdortgenler(pol: list) -> list[list[float]]:
    """Dik açılı poligon → x dilimlerine bölünmüş dikdörtgenler [x0, y0, x1, y1]."""
    xs = sorted(set(q[0] for q in pol))
    kenar = [(a, b) for a, b in zip(pol, pol[1:] + pol[:1]) if a[1] == b[1]]
    out = []
    for xa, xb in zip(xs, xs[1:]):
        xm = (xa + xb) / 2
        kes = sorted(a[1] for a, b in kenar if min(a[0], b[0]) <= xm <= max(a[0], b[0]))
        for ya, yb in zip(kes[::2], kes[1::2]):
            out.append([xa, ya, xb, yb])
    return out


def birlestir(araliklar: list[list[float]], tol: float = 0.6) -> list[list[float]]:
    out = []
    for a0, a1 in sorted(araliklar):
        if out and a0 <= out[-1][1] + tol:
            out[-1][1] = max(out[-1][1], a1)
        else:
            out.append([a0, a1])
    return out


def cikar(araliklar: list[list[float]], kes: list[list[float]]) -> list[list[float]]:
    out = [list(a) for a in araliklar]
    for k0, k1 in kes:
        yeni = []
        for a0, a1 in out:
            if k1 <= a0 or k0 >= a1:
                yeni.append([a0, a1])
                continue
            if k0 > a0:
                yeni.append([a0, k0])
            if k1 < a1:
                yeni.append([k1, a1])
        out = yeni
    return [a for a in out if a[1] - a[0] > 1]


def _r(v, n=2):
    v = round(float(v), n)
    return int(v) if v == int(v) else v


def ifc_kutulari(ifc_yolu: Path, desen: str) -> dict[str, tuple]:
    """Kart modelinde adı desene uyan parçaların kutusu (cm): {ad: (x0, y0, z0, x1, y1, z1)}."""
    import ifcopenshell
    import ifcopenshell.geom
    import numpy as np

    f = ifcopenshell.open(str(ifc_yolu))
    st = ifcopenshell.geom.settings()
    st.set(st.USE_WORLD_COORDS, True)
    out = {}
    for p in f.by_type("IfcProduct"):
        n = p.Name or ""
        if not re.match(desen, n):
            continue
        try:
            s = ifcopenshell.geom.create_shape(st, p)
        except Exception:                                     # montaj grubu (makas): üyeleri ayrı
            continue
        v = np.array(s.geometry.verts).reshape(-1, 3) * 100
        if len(v):
            lo, hi = v.min(0), v.max(0)
            out[n] = tuple(round(float(t), 2) for t in (*lo, *hi))
    return out


def ifc_kart_kodlari(ifc_yolu: Path, desen: str) -> dict[str, str]:
    """Kart modelinde adı desene uyan parçaların kart kodu (`PortatifEv_Parca.KartKodu`): {ad: kod}; kartı olmayan parça yok."""
    import ifcopenshell
    import ifcopenshell.util.element as ue
    from motor.kart_model import PARCA_SETI

    f = ifcopenshell.open(str(ifc_yolu))
    return {p.Name: k for p in f.by_type("IfcProduct") if re.match(desen, p.Name or "") and (k := ue.get_psets(p).get(PARCA_SETI, {}).get("KartKodu"))}


PI = 3.141592654     # dönüş açısı veride dokuz ondalıkla: 15 haneli π numara maskesine (`beyin/numara.py`) takılır; fark 4e-10 rad


def kur(ie: dict, kart: Path, kart_kodu: str, L: list[dict], kod: str) -> dict:
    """Rehberin verisi. `kart`: kart modeli klasörü (`<kart_kodu>_model.ifc`, `<kart_kodu>_kart_sayim.json`); `L`: liste satırları;
    `kod`: rehberde görünen kod (TK-01, AP-19)."""
    from motor import geometry as G
    from motor import ifc_uret
    from motor.prefabrik_liste import _pr, kurallari_oku

    kart = Path(kart)
    SAYIM = json.loads((kart / f"{kart_kodu}_kart_sayim.json").read_text(encoding="utf-8"))
    KARTLAR = {k["kod"]: k for k in json.loads((KOK / "kurallar" / "urun" / "kartlar.json").read_text(encoding="utf-8"))["kartlar"]}
    cati = ie.get("cati") or {}
    if cati.get("tip", "besik") != "besik":
        raise Desteklenmiyor(f"çatı {cati.get('tip')}; rehber yalnız beşik çatıyı kurar")
    if cati.get("makas_ekseni", "x") != "x":
        raise Desteklenmiyor("mahya x yönünde (makaslar y'ye paralel); rehber şimdilik mahyası y yönündeki beşiği kurar")
    plan = G.kur(ie)
    HZ = ifc_uret.hazirla(ie)
    GV = HZ.get("veranda")                      # gömme veranda: gövdenin içinde, ana çatının altında (AP-19)
    if GV and GV.get("tip") != "bina_ici":
        raise Desteklenmiyor(f"veranda {GV.get('tip')}; rehber gövdenin içindeki ve gövdeden taşan verandayı kurar")
    W, DY, H = HZ["bina"]["W"], HZ["bina"]["H"], HZ["bina"]["duvar_h"]
    TAN, SC = float(cati.get("egim_yuzde", 33)) / 100, float(cati.get("sacak_cm", 30))
    EGIM_D = math.degrees(math.atan(TAN))
    COS = 1 / math.sqrt(1 + TAN * TAN)
    OZ = {kucuk(k): v for k, v in (ie.get("ozellikler") or {}).items()}
    ASMA = "ters" not in kucuk(OZ.get("tavan", OZ.get("tavan şekli", "asma")))      # liste üretecinin okuyuşu: ters değilse asma dizme
    VER = HZ.get("dis_verandalar") or []
    for v in VER:
        c = v["cati"]
        if v["cephe"] not in ("on", "arka") or c.get("tip") != "besik" or c["mahya"][0][0] != c["mahya"][1][0]:
            raise Desteklenmiyor(f"{v['ad']}: cephe {v['cephe']}, çatı {c.get('tip')}; rehber ön ve arka cephede ana çatıya paralel beşiği kurar")
    IFC = ifc_kutulari(kart / f"{kart_kodu}_model.ifc", r"^(MAKAS_\d+_ALT_BASLIK|ASIK_\d+|INIS_\d+)$")
    KART_IFC = ifc_kart_kodlari(kart / f"{kart_kodu}_model.ifc", r"^(H_PANO_EKI_IC_\d+|BAGLANTI_B\d+_\d+)$")   # iç H'ların kartı modelden

    # ---------- liste ----------
    def satirlar(on, olcu=None):
        return [s for s in L if s["kalem"].startswith(on) and (olcu is None or s["olcu"] == olcu)]

    def adet(on, olcu=None):
        return sum(s["adet"] or 0 for s in satirlar(on, olcu))

    def ls(on, olcu=None, ad=None):
        """Kimlik kartındaki "Liste" satırı: kalem ölçü · adet."""
        ss = satirlar(on, olcu)
        if not ss:
            return "listede satırı yok"
        b = ss[0]["birim"]
        olc = ss[0]["olcu"] if len({s["olcu"] for s in ss}) == 1 and ss[0]["olcu"] not in ("adet", "metre", "paket", "kova") else ""
        return f"{ad or ss[0]['kalem']}{' ' + olc if olc else ''} · {fmt(sum(s['adet'] or 0 for s in ss))} {'m' if b == 'metre' else 'adet'}"

    def R(k, ad, v, src):
        return [k, ad, v, src]

    def I(ad, v):
        return ["-", ad, v]

    def LR(on, olcu=None, ad=None):
        ss = satirlar(on, olcu)
        if not ss:
            return None
        b = ss[0]["birim"]
        olc = ss[0]["olcu"] if len({s["olcu"] for s in ss}) == 1 and ss[0]["olcu"] not in ("adet", "metre", "paket", "kova") else ""
        return R(None, ad or f"{ss[0]['kalem']}{' ' + olc if olc else ''}", f"{fmt(sum(s['adet'] or 0 for s in ss))} {'m' if b == 'metre' else 'adet'}", "liste")

    # ---------- kartlar ----------
    KK = {kat: k["kod"] for k in SAYIM["kartlar"] for kat in (k.get("katalog_kodlari") or {})}
    HT = {h["parca"]: h for h in SAYIM["h_turu"]}
    GOR = {g["parca"]: g["asil"] for g in SAYIM["gorunum"]}
    cards = {k: {"ad": v["ad"], "olcu": v.get("olcu"), "ifc": v.get("ifc"), "birim": v.get("birim")} for k, v in KARTLAR.items()}

    # ---------- odalar ----------
    odalar = [dict(o, acik=False) for o in HZ["odalar"]]
    SIRA, BIRLES = oda_sirasi(odalar, SAYIM["yerlesim"]["baslangic"])
    POLY = {o["ad"]: o for o in odalar}
    ODA = []                                   # (ana ad, kimlik, rehberdeki ad, adım)
    for i, ad in enumerate(SIRA):
        ODA.append((ad, oda_kimligi(ad), oda_adi(ad, [b for b, h in BIRLES.items() if h == ad]), 2 + i))
    ADIM_ODA = {ad: s for ad, _, _, s in ODA}
    KIM = {ad: k for ad, k, _, _ in ODA}
    N_ODA = len(ODA)

    def oda_bul(pt):
        for ad, o in POLY.items():
            if icinde(pt, o["poligon"]):
                return BIRLES.get(ad, ad)
        return None

    def oda_sec(probes):
        bul = [o for o in (oda_bul(q) for q in probes) if o]
        return min(bul, key=lambda o: ADIM_ODA[o]) if bul else SIRA[-1]

    # ---------- adımlar ----------
    S = {"alt": 1}
    sira = (["veranda"] if VER or GV else []) + ["omega", "makas", "kalkan", "tomega", "alcipan", "izo", "asik", "sacak", "dere", "kaplama", "alin", "dograma"]
    for i, k in enumerate(sira):
        S[k] = 2 + N_ODA + i
    N = S["dograma"]

    # ---------- panolar, H'lar, köşe direkleri ----------
    PL = [(d, p) for d in plan.duvarlar for p in d.panolar]
    assert len(PL) == len(HZ["panolar"])
    oge = defaultdict(list)                    # oda → [(merkez, tür, kayıt)]
    panels = []
    for pr, (d, pp) in zip(HZ["panolar"], PL):
        x0, y0, x1, y1 = pr["rect"]
        o = "h" if pr["yon"] == "x" else "v"
        op = None
        for a in pr["acikliklar"]:
            A = HZ["acikliklar"][a["aciklik"]]
            if A["tur"] == "pencere":
                op = {"kind": "win", "size": A["olcu"].replace("x", "/"), "a0": A["a0"], "a1": A["a1"], "s": A["z0"], "top": A["z1"]}
            elif A["alt_tur"] == "dis_kapi":
                op = {"kind": "door_ext", "a0": A["a0"], "a1": A["a1"], "s": 0, "top": A["z1"],
                      "mentese": "sol" if G.mentese_ucu(pp.acilim) == 0 else "sag"}
            else:
                op = {"kind": "door", "a0": A["a0"], "a1": A["a1"], "s": 0, "top": A["z1"]}
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        probes = [(cx, y0 - 25), (cx, y1 + 25)] if o == "h" else [(x0 - 25, cy), (x1 + 25, cy)]
        oda = oda_sec(probes)
        k = {"id": f"P{pr['id']}", "rect": [_r(v) for v in pr["rect"]], "o": o, "t": _r(pr["kalinlik"]), "duvar": pr["tur"],
             "tur": "STD" if abs(pr["boy"] - 125.5) < 0.01 else "OZEL", "boy": _r(pr["boy"]), "card": KK.get(pr["kod"]),
             "ad": None if KK.get(pr["kod"]) else pr["kalem"], "op": op, "room": KIM[oda], "step": ADIM_ODA[oda]}
        panels.append(k)
        oge[oda].append(((cx, cy), 1, k))

    ic_panolar = [p for p in HZ["panolar"] if p["tur"] == "ic"]
    # İç duvar kalınlığı (İş Emri `yapi.duvar_kalinligi_cm.ic`; BK-18'den beri 100'lük de olabilir). Satır adları liste üretecinin kuralıyla
    # (`prefabrik_liste`: en sık iç pano kalınlığı, 100 mm ve üstü "100'lük"); iç duvarsız evde 60'lık.
    IC_MM = Counter(round(p["kalinlik"] * 10) for p in ic_panolar).most_common(1)[0][0] if ic_panolar else 60
    IC_100 = IC_MM >= 100
    IC_KAL = "100'lük" if IC_100 else "60'lık"

    def stub_bul(o, a, perp, t):
        for p in ic_panolar:
            px0, py0, px1, py1 = p["rect"]
            if o == "h" and p["yon"] == "y" and abs((px0 + px1) / 2 - a) < 0.6:
                if abs(py0 - (perp + t / 2)) < 0.6:
                    return [0, 1], _r(px1 - px0)
                if abs(py1 - (perp - t / 2)) < 0.6:
                    return [0, -1], _r(px1 - px0)
            if o == "v" and p["yon"] == "x" and abs((py0 + py1) / 2 - a) < 0.6:
                if abs(px0 - (perp + t / 2)) < 0.6:
                    return [1, 0], _r(py1 - py0)
                if abs(px1 - (perp - t / 2)) < 0.6:
                    return [-1, 0], _r(py1 - py0)
        return None, None

    hs = []
    for i, e in enumerate(HZ.get("pano_ekleri") or []):
        x0, y0, x1, y1 = e["rect"]
        o = "h" if (y1 - y0) > (x1 - x0) else "v"
        t = _r((y1 - y0 if o == "h" else x1 - x0) - 2 * ifc_uret.H_PROFIL_TASMA_CM)
        a, perp = ((x0 + x1) / 2, (y0 + y1) / 2) if o == "h" else ((y0 + y1) / 2, (x0 + x1) / 2)
        dis, uclu = e["duvar"] == "dis", e["cins"] == "uclu"
        ad_ifc = f"H_{'UCLU' if uclu else 'PANO_EKI'}_{'DIS' if dis else 'IC'}_{i:03d}"
        h = HT.get(GOR.get(ad_ifc, ad_ifc))
        if dis and h:
            card, tur = h["kart"], ("uclu_" if uclu else "") + h["tur"]
        else:                                               # iç H: kartı modelden (60'lıkta H-03 / H-06, 100'lükte H-07 / H-10)
            card, tur = KART_IFC.get(GOR.get(ad_ifc, ad_ifc)), "uclu_standart" if uclu else "standart"
        stub, stub_t = stub_bul(o, a, perp, t) if uclu else (None, None)
        xy = [_r(a), _r(perp)] if o == "h" else [_r(perp), _r(a)]
        k = {"xy": xy, "o": o, "t": t, "tur": tur, "card": card, "ad": None, "stub": stub, "stub_t": stub_t}
        probes = [(xy[0] + u, xy[1] + w) for u in (-t / 2 - 15, t / 2 + 15) for w in (-t / 2 - 15, t / 2 + 15)]
        oda = oda_sec(probes)
        k.update(room=KIM[oda], step=ADIM_ODA[oda])
        hs.append(k)
        oge[oda].append(((xy[0], xy[1]), 2, k))

    def devam(yon, kutu, uc, isaret):
        """Köşe kutusunun `uc` kenarından `yon` ekseninde (isaret yönünde) pano devam ediyor mu."""
        x0, y0, x1, y1 = kutu
        for p in HZ["panolar"]:
            px0, py0, px1, py1 = p["rect"]
            if p["yon"] != yon:
                continue
            if yon == "y" and min(px1, x1) - max(px0, x0) > 0.5 and abs((py0 if isaret > 0 else py1) - uc) < 0.6:
                return p
            if yon == "x" and min(py1, y1) - max(py0, y0) > 0.5 and abs((px0 if isaret > 0 else px1) - uc) < 0.6:
                return p
        return None

    posts = []
    for b in HZ["baglantilar"]:
        if b["kod"] not in ("B01", "B02"):                  # B03 / B05 üçlü H: H olarak (pano ekleri) çizilir
            continue
        x0, y0, x1, y1 = b["rect"]
        dx, dy = x1 - x0, y1 - y0
        if dy < dx:                                         # içeri giren duvar y boyunca, köşe kutusuna e kadar girer
            g = devam("y", b["rect"], y1, 1)
            dt = [0, 1] if g else [0, -1]
            g = g or devam("y", b["rect"], y0, -1)
            bt = devam("x", b["rect"], x1, 1)
            db = [1, 0] if bt else [-1, 0]
            bt = bt or devam("x", b["rect"], x0, -1)
            e = dy
            O = [x0 if db[0] > 0 else x1, y0 if dt[1] > 0 else y1]
            w, dep = g["kalinlik"], bt["kalinlik"]
            rect = [min(O[0], O[0] + db[0] * w), min(O[1], O[1] + dt[1] * dep), max(O[0], O[0] + db[0] * w), max(O[1], O[1] + dt[1] * dep)]
        else:                                               # içeri giren duvar x boyunca
            g = devam("x", b["rect"], x1, 1)
            dt = [1, 0] if g else [-1, 0]
            g = g or devam("x", b["rect"], x0, -1)
            bt = devam("y", b["rect"], y1, 1)
            db = [0, 1] if bt else [0, -1]
            bt = bt or devam("y", b["rect"], y0, -1)
            e = dx
            O = [x0 if dt[0] > 0 else x1, y0 if db[1] > 0 else y1]
            w, dep = g["kalinlik"], bt["kalinlik"]
            rect = [min(O[0], O[0] + dt[0] * dep), min(O[1], O[1] + db[1] * w), max(O[0], O[0] + dt[0] * dep), max(O[1], O[1] + db[1] * w)]
        k = {"rect": [_r(v) for v in rect], "O": [_r(v) for v in O], "db": db, "dt": dt, "e": _r(e), **({"ic": True} if b["kod"] == "B01" else {"ic_yer": True} if "_IC_KOSE_" in b["blok"] else {}),
             "card": KK.get(b["kod"]), "id": f"K{len(posts) + 1}"}
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        oda = oda_sec([(cx + u, cy + v) for u in (-20, 20) for v in (-20, 20)])
        k.update(room=KIM[oda], step=ADIM_ODA[oda])
        posts.append(k)
        oge[oda].append(((cx, cy), 0, k))

    # Oda içinde sıra: dizilimin başladığı köşeden (odanın arka-sol köşesi) uzaklık; köşe direği aynı yerdeki panodan önce
    for ad, lst in oge.items():
        pol = [q for a in [ad] + [b for b, h in BIRLES.items() if h == ad] for q in POLY[a]["poligon"]]
        bx, by = min(q[0] for q in pol), max(q[1] for q in pol)
        lst.sort(key=lambda t: (round(math.hypot(t[0][0] - bx, t[0][1] - by), 1), t[1]))
        for j, (_, tur, k) in enumerate(lst):
            k["order"] = j + 0.4 if tur == 0 else j

    # Çektirme U'su: iç duvarın dış duvara pano ortasında (H olmayan yerde) girdiği yer
    ceku = []
    eki_yer = [(h["xy"], h["o"]) for h in hs if h["stub"]]
    for p in ic_panolar:
        x0, y0, x1, y1 = p["rect"]
        for uc, yon in ((([x0, (y0 + y1) / 2], [1, 0]), ([x1, (y0 + y1) / 2], [-1, 0])) if p["yon"] == "x" else
                        (([(x0 + x1) / 2, y0], [0, 1]), ([(x0 + x1) / 2, y1], [0, -1]))):
            dis_yuz = (abs(uc[0] - 10) < 0.6 or abs(uc[0] - (W - 10)) < 0.6) if p["yon"] == "x" else \
                (abs(uc[1] - 10) < 0.6 or abs(uc[1] - (DY - 10)) < 0.6)
            if not dis_yuz or any(math.hypot(xy[0] - uc[0], xy[1] - uc[1]) < 12 for xy, _ in eki_yer):
                continue
            oda = oda_sec([(uc[0] + yon[0] * 25 + yon[1] * 25, uc[1] + yon[1] * 25 + yon[0] * 25),
                           (uc[0] + yon[0] * 25 - yon[1] * 25, uc[1] + yon[1] * 25 - yon[0] * 25)])
            ceku.append({"xy": [_r(uc[0]), _r(uc[1])], "yon": yon, "t": _r(p["kalinlik"]), "step": ADIM_ODA[oda], "order": 99, "room": KIM[oda],
                         "id": f"U{len(ceku) + 1}"})

    # ---------- alt çerçeve: duvar hatları, kapı boşluklarında kesik ----------
    hat = defaultdict(list)
    for pr, (d, pp) in zip(HZ["panolar"], PL):
        x0, y0, x1, y1 = pr["rect"]
        hat[(pr["yon"], d.c, pr["kalinlik"], pr["tur"])].append([x0, x1] if pr["yon"] == "x" else [y0, y1])
    alt, alt_m = [], {"dis": 0.0, "ic": 0.0}
    for (yon, c, t, tur), ar in sorted(hat.items(), key=lambda kv: (kv[0][3] != "dis", kv[0][0], kv[0][1])):
        kes = [[A["a0"], A["a1"]] for A in HZ["acikliklar"] if A["tur"] == "kapi" and A["yon"] == yon and abs(A["c"] - c) < 0.6]
        for a0, a1 in cikar(birlestir(ar), kes):
            alt.append({"o": "h" if yon == "x" else "v", "perp": _r(c), "t": _r(t), "a0": _r(a0), "a1": _r(a1), "duvar": tur})
            alt_m[tur] += (a1 - a0) / 100
    alt_m = {k: round(v, 2) for k, v in alt_m.items()}

    # ---------- verandalar ----------
    BAG = HZ["baglantilar"]

    def icinde_kutu(r, k):
        return r[0] >= k[0] - 0.5 and r[2] <= k[2] + 0.5 and r[1] >= k[1] - 0.5 and r[3] <= k[3] + 0.5

    # Kirişin kesim boyu listeden (D-28 madde 1: aynı parçanın boyunu iki kod ayrı üretmez): kart listede çizimdeki boyun satırını, yoksa kural
    # kitabının "açık kenar dış ölçüsü − 10" satırını (`veranda_kirisi_eksik_cm`, PK-01'de tuttu) okur; nişin kirişi aks arası. Patron 28 Ekim
    # (karar kartı A): taşan verandanın dış kirişi kolonların dış yüzünden dış yüzüne (TK-01 386, 261); çizim ve liste (İE-13 PR-2,
    # `tasan_veranda_dis_kirisi_eksik_cm` = 0) böyle. Listede çizimdeki boy yoksa kart listedeki boyu ve çizimle farkını gösterir (AP-19).
    EKSIK = _pr(kurallari_oku()["prefabrik"], "veranda_kirisi_eksik_cm")

    def kiris_boyu(acik, cizim):
        """(kartta yazan boy, Liste satırı, ek not). `acik`: açık kenarın dış ölçüsü (None: nişin kirişi, aks arası); `cizim`: çizimdeki boy (cm).
        Önce çizimdeki boyun satırı, yoksa açık kenar − kitabın eksiği."""
        for L_ in [cizim] + ([] if acik is None else [acik - EKSIK]):
            olcu = f"L {round(L_ * 10)}"
            if satirlar("Kutu profil (kiriş)", olcu):
                fark = "" if abs(L_ - cizim) < 0.6 else f"; boy listeden (kural kitabı: açık kenar dış ölçüsü − {fmtc(EKSIK)} cm), çizimde {fmtc(cizim)} cm"
                return L_, ls("Kutu profil (kiriş)", olcu), fark
        return cizim, f"listede kiriş L {round(cizim * 10)} satırı yok", ""

    verandalar, VR, GVK = [], [], None          # VR: çatı ve yerleşim için taşan veranda kaydı; GVK: gömme veranda
    for vi, v in enumerate(VER):
        vk = v["rect"]
        kol = [b for b in BAG if b["tur"] == "dikme" and icinde_kutu(b["rect"], vk)]
        kir = [b for b in BAG if b["tur"] == "veranda_profil" and icinde_kutu(b["rect"], vk)]
        on = v["cephe"] == "on"
        dis_y = vk[1] if on else vk[3]          # verandanın dış kenarı (kiriş dış yüzü)
        bas_k = [b for b in kir if (b["rect"][2] - b["rect"][0]) > (b["rect"][3] - b["rect"][1])]
        yan_k = [b for b in kir if b not in bas_k]
        ad = oda_adi(v["ad"], [])
        kc = v["cati"]["kutu"]
        rk = f"V{vi + 1}"
        kirisler = []
        for b in bas_k:
            r = b["rect"]
            Lk, lst, fark = kiris_boyu(r[2] - r[0], r[2] - r[0])
            kirisler.append({"rect": [_r(t) for t in r], "bu": f"{kucuk(ad)} · dış kiriş · L {fmtc(Lk)} cm (kolonların üstünde){fark}", "liste": lst})
        for b in sorted(yan_k, key=lambda b: b["rect"][0]):
            r = list(b["rect"])
            acik = r[3] - r[1]
            for q in bas_k:                      # yan kiriş dış kirişin iç yüzünde başlar (kesişmesin)
                if on:
                    r[1] = max(r[1], q["rect"][3])
                else:
                    r[3] = min(r[3], q["rect"][1])
            yer = "sol" if r[0] < (vk[0] + vk[2]) / 2 else "sağ"
            Lk, lst, fark = kiris_boyu(acik, r[3] - r[1])
            kirisler.append({"rect": [_r(t) for t in r], "bu": f"{kucuk(ad)} · {yer} yan kiriş · L {fmtc(Lk)} cm: dış kirişi gövdeye bağlar{fark}", "liste": lst})
        verandalar.append({
            "kolon": [{"rect": [_r(t) for t in b["rect"]], "order": len(verandalar) * 10 + i,
                       "bu": f"{kucuk(ad)} · {'sol' if b['rect'][0] < (vk[0] + vk[2]) / 2 else 'sağ'} kolon · 100 × 100 × {fmt(H * 10)}",
                       "liste": ls("Özel kutu profil (kolon)")} for i, b in enumerate(sorted(kol, key=lambda b: b["rect"][0]))],
            "kiris": [dict(k, order=len(verandalar) * 10 + len(kol) + i) for i, k in enumerate(kirisler)],
        })
        VR.append({"ad": ad, "on": on, "rect": vk, "dis_y": dis_y, "kutu": kc, "M": v["cati"]["mahya"][0][0], "R": rk,
                   "kolon": [b["rect"] for b in kol], "bas_k": [b["rect"] for b in bas_k], "yan_k": [r for r in (k["rect"] for k in kirisler[len(bas_k):])],
                   "egim": v["cati"]["egim"]})

    if GV:                                      # gömme veranda: kolon dış köşede, kirişler açık kenarlarda; çatısı ana çatı
        vk = [min(q[0] for q in GV["poligon"]), min(q[1] for q in GV["poligon"]), max(q[0] for q in GV["poligon"]), max(q[1] for q in GV["poligon"])]
        kol = [b for b in BAG if b["tur"] == "dikme" and icinde_kutu(b["rect"], vk)]
        kir = [b for b in BAG if b["tur"] == "veranda_profil" and icinde_kutu(b["rect"], vk)]
        if not kir:
            raise Desteklenmiyor("gömme verandanın kirişi planda yok")
        # Kolonsuz gömme veranda giriş nişidir (TK-01 r06): iki yanı ve arkası gövde duvarı, açık kenarındaki kiriş iki yandaki duvarı bağlar
        nis = not kol
        gad = "giriş nişi" if nis else "veranda"
        if nis:                                 # nişin ağzındaki kiriş aks arası (liste üreteci, BK-14 ek: duvarsız açıklığa kiriş, aks arası)
            uz = []
            for b in kir:
                r = list(b["rect"])
                yat = r[2] - r[0] > r[3] - r[1]
                for (yon, c, t, tur) in hat:            # kirişin ucuna yüzüyle değen duvarın aksına kadar
                    if tur == "dis" and yon == ("y" if yat else "x"):
                        i0, i1 = (0, 2) if yat else (1, 3)
                        if abs(c + t / 2 - r[i0]) < 0.6:
                            r[i0] = c
                        elif abs(c - t / 2 - r[i1]) < 0.6:
                            r[i1] = c
                uz.append(dict(b, rect=r))
            kir = uz

        def kenar(r):
            if r[2] - r[0] > r[3] - r[1]:
                return "ön kiriş" if r[1] < DY / 2 else "arka kiriş"
            return "sol yan kiriş" if r[0] < W / 2 else "sağ yan kiriş"

        def kose(r):
            return f"{'ön' if r[1] < DY / 2 else 'arka'} {'sol' if r[0] < W / 2 else 'sağ'} köşe"
        o0 = len(verandalar) * 10

        def gv_kiris(i, b):
            r = b["rect"]
            Lc = max(r[2] - r[0], r[3] - r[1])
            Lk, lst, fark = kiris_boyu(None if nis else Lc, Lc)
            return {"rect": [_r(t) for t in r], "order": o0 + len(kol) + i, "liste": lst,
                    "bu": f"{gad} · {kenar(r)} · L {fmtc(Lk)} cm: {'iki yandaki duvarı bağlar' if nis else 'kolonu gövdeye bağlar'}, duvar üstü kotunda; "
                          f"üstüne omega ve ana çatının makasları gelir{fark}"}
        verandalar.append({
            "kolon": [{"rect": [_r(t) for t in b["rect"]], "order": o0 + i, "bu": f"veranda · {kose(b['rect'])} kolonu · 100 × 100 × {fmt(H * 10)}",
                       "liste": ls("Özel kutu profil (kolon)")} for i, b in enumerate(sorted(kol, key=lambda b: (b["rect"][1], b["rect"][0])))],
            "kiris": [gv_kiris(i, b) for i, b in enumerate(sorted(kir, key=lambda b: (b["rect"][1], b["rect"][0])))],
        })
        GVK = {"vk": vk, "kol": len(kol), "kir": [kenar(b["rect"]) for b in kir], "m2": GV.get("net_m2"), "nis": nis}

    # ---------- çatılar ----------
    RF = {"AN": {"L": -SC, "R": W + SC, "M": W / 2, "tan": TAN}}
    for v in VR:
        RF[v["R"]] = {"L": v["kutu"][0], "R": v["kutu"][2], "M": v["M"], "tan": v["egim"]}
    # Arka/ön verandanın çatısı ana çatının saçağıyla aynı hizadaysa o yüz ana yüzün devamıdır (aynı düzlem): ana kalkanın o ucu kapalı
    for v in VR:
        v["sol_devam"] = abs(v["kutu"][0] - (-SC)) < 0.5 and abs(v["egim"] - TAN) < 1e-6
        v["sag_devam"] = abs(v["kutu"][2] - (W + SC)) < 0.5 and abs(v["egim"] - TAN) < 1e-6
    tepe = (W / 2 + SC) * TAN
    CATI_AN = f"ana beşik · eğim %{fmt(TAN * 100)} ({fmt(EGIM_D, 1)}°) · açıklık {fmtc(W + 2 * SC)} cm"

    # ---------- makaslar ----------
    alt_bas = sorted((k[1] + k[4]) / 2 for n, k in IFC.items() if n.startswith("MAKAS"))
    if len(alt_bas) < 2:
        raise Desteklenmiyor("kart modelinde makas yok")
    konum = [3.7] + [_r(y) for y in alt_bas[1:-1]] + [_r(DY - 3.7)]   # baş makas: dış yüzü omeganın dış kanadıyla aynı hizada (şablon)

    def nb(span):
        return max(2, round((span - 77.8) / 64))

    makas = [{"ad": f"MKS{i + 1:02d}", "aile": "ana", "rol": "bas" if i in (0, len(konum) - 1) else "orta", "konum": k, "bas": -SC, "son": W + SC,
              "R": "AN", "yon": "x", "wl": [2.7, _r(W - 2.7)], "NB": nb(W + 2 * SC), "T0": 38.9, "cati": CATI_AN} for i, k in enumerate(konum)]
    for v in VR:
        n = adet(f"Yavru makas · {kucuk(v['ad'])} çatısı")
        if not n:
            raise Desteklenmiyor(f"listede \"Yavru makas · {kucuk(v['ad'])} çatısı\" satırı yok")
        y_dis = v["dis_y"] + (3.7 if v["on"] else -3.7)
        y_duv = -4.2 if v["on"] else DY + 4.2
        ks = sorted(y_dis + (y_duv - y_dis) * j / (n - 1) for j in range(n)) if n > 1 else [y_dis]
        kx0, kx1 = v["kutu"][0], v["kutu"][2]
        for j, y in enumerate(ks):
            makas.append({"ad": f"MKS{len(makas) + 1:02d}", "aile": "veranda", "rol": "bas" if abs(y - y_dis) < 0.01 else "orta", "konum": _r(y),
                          "bas": _r(kx0), "son": _r(kx1), "R": v["R"], "yon": "x", "wl": [_r(v["rect"][0] + 2.7), _r(v["rect"][2] - 2.7)],
                          "NB": nb(kx1 - kx0), "T0": 38.9, "kod": None, "kart_ad": "Yavru makas (veranda)",
                          "cati": f"{kucuk(v['ad'])} beşiği · eğim %{fmt(v['egim'] * 100)} · açıklık {fmtc(kx1 - kx0)} cm",
                          "kaynak": f"adet ve boy listeden ({ls('Yavru makas · ' + kucuk(v['ad']) + ' çatısı')}); yer: derinlik boyunca eşit aralık (varsayım, motorun modelinde yok)"})

    # ---------- duvar üstü omegaları ----------
    omega_duvar = [
        {"tur": "sacak", "o": "v", "perp": 5, "a0": 0, "a1": DY, "out": -1, "yer": "sol duvar"},
        {"tur": "sacak", "o": "v", "perp": _r(W - 5), "a0": 0, "a1": DY, "out": 1, "yer": "sağ duvar"},
    ]
    for v in VR:
        for r in v["yan_k"]:
            sol = r[0] < (v["rect"][0] + v["rect"][2]) / 2
            omega_duvar.append({"tur": "sacak", "o": "v", "perp": _r((r[0] + r[2]) / 2), "a0": _r(min(r[1], r[3])), "a1": _r(max(r[1], r[3])),
                                "out": -1 if sol else 1, "yer": f"{kucuk(v['ad'])} {'sol' if sol else 'sağ'} yan kirişi"})
    for v in VR:                                  # listede verandanın dış kirişi duvar omegasıyla sayılır
        for r in v["bas_k"]:
            omega_duvar.append({"tur": "duvar", "o": "h", "perp": _r((r[1] + r[3]) / 2), "a0": _r(r[0]), "a1": _r(r[2]), "out": -1 if v["on"] else 1,
                                "yer": f"{kucuk(v['ad'])} dış kirişi"})
    omega_duvar += [{"tur": "bas", "o": "h", "perp": 5, "a0": 0, "a1": W, "out": -1, "yer": "ön duvar (ön baş makasın altı)"},
                    {"tur": "bas", "o": "h", "perp": _r(DY - 5), "a0": 0, "a1": W, "out": 1, "yer": "arka duvar (arka baş makasın altı)"}]
    if GVK:                                       # gömme veranda: verandaya bakan gövde duvarları 100'lük duvar omegası (kapı üstünden geçer)
        vx, vy = (GVK["vk"][0] + GVK["vk"][2]) / 2, (GVK["vk"][1] + GVK["vk"][3]) / 2
        for (yon, c, t, tur), ar in sorted(hat.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            if tur != "dis" or (yon == "y" and min(abs(c - 5), abs(c - (W - 5))) < 1) or (yon == "x" and min(abs(c - 5), abs(c - (DY - 5))) < 1):
                continue
            for a0, a1 in birlestir(ar, tol=12):
                omega_duvar.append({"tur": "duvar", "o": "h" if yon == "x" else "v", "perp": _r(c), "a0": _r(a0), "a1": _r(a1),
                                    "out": (1 if vy > c else -1) if yon == "x" else (1 if vx > c else -1),
                                    "yer": f"{'nişe' if GVK['nis'] else 'verandaya'} bakan gövde duvarı"})
        # dış hattın bir kısmı kiriş: omega kirişin üstünden geçer
        for o in omega_duvar:
            for r in (k["rect"] for k in verandalar[-1]["kiris"]):
                yat = r[2] - r[0] > r[3] - r[1]
                if (o["o"] == "h") == yat and abs(o["perp"] - ((r[1] + r[3]) / 2 if yat else (r[0] + r[2]) / 2)) < 0.6:
                    o["yer"] = o["yer"].replace(" duvar", " duvar ve veranda kirişi", 1)
    OMP = []                                       # kart modelinin tavan omegası parçaları
    for p in SAYIM["yerlesim"]["parcalar"]:
        if not p["parca"].startswith("OMEGA"):
            continue
        m = re.match(r"^(x|y) = ([\d.]+), ([\d.]+)–([\d.]+)", p["aciklama"])
        OMP.append({"eksen": m.group(1), "s": float(m.group(2)), "a0": float(m.group(3)), "a1": float(m.group(4)), "yer": p["bilgi"]["Yer"],
                    "mahal": p["bilgi"].get("Mahal") or "", "boy": p["boy_cm"], "tavan": p["bilgi"].get("Tavan")})
    for q in OMP:
        if q["yer"] == "duvar_ekseni":
            omega_duvar.append({"tur": "ic", "o": "h" if q["eksen"] == "y" else "v", "perp": _r(q["s"]), "a0": _r(q["a0"]), "a1": _r(q["a1"]), "out": 1,
                                "yer": f"iç duvar ({q['eksen']} = {fmtc(q['s'])})"})
    omega = [{"yon": "y" if q["eksen"] == "x" else "x", "konum": _r(q["s"]), "bas": _r(q["a0"]), "son": _r(q["a1"]),
              "oda": KIM.get(BIRLES.get(q["mahal"], q["mahal"]), "veranda"), "boy": _r(q["boy"])} for q in OMP if q["yer"] != "duvar_ekseni"]

    # ---------- tavan ----------
    if ASMA:
        TH = _pr(kurallari_oku()["prefabrik"], "tavan_h_aralik_m") * 100
        xhat = [(q["s"], q["a0"], q["a1"]) for q in OMP if q["eksen"] == "x"]
        if any(q["eksen"] == "y" and q["yer"] != "duvar_ekseni" for q in OMP):
            raise Desteklenmiyor("asma tavanın oda içi omegaları x yönünde; rehber y yönündekileri (mahyaya paralel) dizer")
        th, goz = [], []
        for ad, kim, _, _ in ODA:
            yesil = any(w in ad for w in ("BANYO", "WC"))
            for a in [ad] + [b for b, h in BIRLES.items() if h == ad]:
                for x0, y0, x1, y1 in dikdortgenler(POLY[a]["poligon"]):
                    cut = sorted({x0, x1} | {s for s, r0, r1 in xhat if x0 + 1 < s < x1 - 1 and r0 < (y0 + y1) / 2 < r1})
                    yc = [y1]
                    while yc[-1] - TH > y0 + 5:
                        yc.append(yc[-1] - TH)
                    yc.append(y0)
                    for xa, xb in zip(cut, cut[1:]):
                        ga, gb = xa + (0 if xa == x0 else 3.25), xb - (0 if xb == x1 else 3.25)
                        for ya, yb in zip(yc[1:], yc):
                            goz.append([_r(ga), _r(ya), _r(gb), _r(yb), yesil, kim])
                        for yh in yc[1:-1]:
                            th.append({"o": "h", "perp": _r(yh), "a0": _r(ga), "a1": _r(gb), "oda": kim})
        tavan = {"tip": "asma", "h": th, "goz": goz, "h_aralik": f"{fmtc(TH)} cm (kural: tavan_h_aralik_m); omega hatlarına dik"}
    else:
        tavan = {"tip": "ters", "boardex": []}

    # ---------- saçak sacı, kalkan, çatı yüzleri ----------
    E0, E1 = -SC - 0.2, DY + SC + 0.2              # ana çatının kalkan kenarları (alın sacı yüzü)
    sacak = [{"ad": "sol saçak", "o": "v", "face": 0, "out": -1, "a0": E0, "a1": E1, "f0": E0, "f1": E1, "t0": -1.1, "t1": _r(DY + 1.1), "R": "AN"},
             {"ad": "sağ saçak", "o": "v", "face": W, "out": 1, "a0": E0, "a1": E1, "f0": E0, "f1": E1, "t0": -1.1, "t1": _r(DY + 1.1), "R": "AN"}]
    kalkan = [{"ad": "ön kalkan (MKS01)", "r": 0, "O": [0, 0], "R": "AN", "p": 1, "uc": {"A": -SC, "B": W + SC}, "sm": W / 2, "duvar": {"A": 0, "B": W},
               "altUc": {"A": True, "B": True}},
              {"ad": f"arka kalkan (MKS{len(konum):02d})", "r": PI, "O": [0, DY], "R": "AN", "p": -1, "uc": {"A": SC, "B": -(W + SC)}, "sm": -W / 2,
               "duvar": {"A": 0, "B": -W}, "altUc": {"A": True, "B": True}}]
    yuz = {
        "ML": {"ad": "ana çatı sol yüz", "E": [-SC, 0], "d": [1, 0], "R": "AN", "poly": [[-SC - 1.3, E0], [W / 2, E0], [W / 2, E1], [-SC - 1.3, E1]],
               "eksen": "y", "hadve": "HA"},
        "MR": {"ad": "ana çatı sağ yüz", "E": [W + SC, 0], "d": [-1, 0], "R": "AN", "poly": [[W / 2, E0], [W + SC + 1.3, E0], [W + SC + 1.3, E1], [W / 2, E1]],
               "eksen": "y", "hadve": "HA"},
    }
    dere_hat = [{"ad": "sol", "yon": "y", "a0": E0, "a1": E1, "kenar": -SC - 0.2, "out": -1}, {"ad": "sağ", "yon": "y", "a0": E0, "a1": E1, "kenar": W + SC + 0.2, "out": 1}]
    hadve_ar = {"HA": (E0, E1)}
    for v in VR:
        kx0, ky0, kx1, ky1 = v["kutu"]
        M_ = v["M"]
        on = v["on"]
        # verandanın çatısı gövdeye ana kalkanın dış yüzünde biter; ana yüzün devamı olan yüz ana saçağın bittiği yerden başlar
        if on:
            y_ic, y_dis = -1.2, ky0 - 0.2
            y_ic_dev = E0
        else:
            y_ic, y_dis = DY + 1.2, ky1 + 0.2
            y_ic_dev = E1
        vk = v["rect"]
        vad = kucuk(v["ad"])
        for sol in (True, False):
            dev = v["sol_devam"] if sol else v["sag_devam"]
            face_x = vk[0] if sol else vk[2]
            # saçak: devam eden yüzde ana saçağın ucundan, öbüründe gövdenin dış yüzünden
            s0, s1 = sorted((y_dis, y_ic_dev if dev else y_ic))
            tdis = v["dis_y"] + (-1.1 if on else 1.1)
            t0, t1 = sorted((tdis, (y_ic_dev if dev else y_ic)))
            sacak.append({"ad": f"{vad} {'sol' if sol else 'sağ'} saçağı", "o": "v", "face": _r(face_x), "out": -1 if sol else 1, "a0": _r(s0), "a1": _r(s1),
                          "f0": _r(s0), "f1": _r(s1), "t0": _r(t0), "t1": _r(t1), "R": v["R"]})
            dere_hat.append({"ad": f"{vad} {'sol' if sol else 'sağ'}", "yon": "y", "a0": _r(s0), "a1": _r(s1),
                             "kenar": _r((kx0 - 0.2) if sol else (kx1 + 0.2)), "out": -1 if sol else 1, "veranda": v["ad"]})
        kalkan.append({"ad": f"{vad} kalkanı", "r": 0 if on else PI, "O": [0, _r(v["dis_y"])], "R": v["R"], "p": 1 if on else -1,
                       "uc": {"A": kx0 if on else -kx0, "B": kx1 if on else -kx1}, "sm": M_ if on else -M_,
                       "duvar": {"A": vk[0] if on else -vk[0], "B": vk[2] if on else -vk[2]}, "altUc": {"A": True, "B": True}})
        # yüz: ana yüzün devamıysa ana saçağın kenarına kadar, değilse ana kalkanın altından gövdeye (ana saçağın altında kalır)
        for yan, dev, x0_, x1_, E_, d_ in (("L", v["sol_devam"], kx0 - 1.3, M_, kx0, 1), ("R", v["sag_devam"], M_, kx1 + 1.3, kx1, -1)):
            lo, hi = sorted((y_dis, y_ic_dev if dev else y_ic))
            hk = f"H{v['R']}{yan}"
            hadve_ar[hk] = (lo, hi)
            yuz[f"{v['R']}{yan}"] = {"ad": f"{vad} çatısı {'sol' if yan == 'L' else 'sağ'} yüz", "E": [E_, 0], "d": [d_, 0], "R": v["R"],
                                     "poly": [[x0_, lo], [x1_, lo], [x1_, hi], [x0_, hi]], "eksen": "y", "hadve": hk}
        # ana kalkanın bu verandanın yanındaki ucu: veranda çatısı ana yüzün devamıysa alın ve Z veranda mahyasından başlar
        KA = kalkan[0] if on else kalkan[1]
        for sol, uc in ((True, "A"), (False, "B")):
            if v["sol_devam" if sol else "sag_devam"]:
                KA["uc"][uc] = (M_ if on else -M_)
                KA.setdefault("ucKapali", {})[uc] = True
                KA["altUc"][uc] = False
    # betopan (125 × 250): kalkan 125 cm'ye sığıyorsa 62 m²'deki gibi yatay levhalar, mahyadan iki yana 250'lik; sığmıyorsa 125'lik dik
    # şeritler. Levhanın yarısından kısa kalan uç "makas ucu" dolgusu (artandan), uzunu kesilmiş levha.
    KA_dik = []
    for KA in kalkan:
        a, b, sm = KA["duvar"]["A"], KA["duvar"]["B"], KA["sm"]
        tan_k = RF[KA["R"]]["tan"]
        KA_yuk = max(abs(sm - a), abs(sm - b)) * tan_k + 13
        en = 250 if KA_yuk <= 125 else 125
        KA_dik.append(en == 125)
        parca, dolgu = [], []
        for u, w in ((a, sm), (b, sm)):
            yon = 1 if u > w else -1
            s = w
            while abs(u - s) > en + 0.01:
                parca.append([_r(s), _r(s + yon * en)])
                s += yon * en
            if abs(u - s) > en / 2:
                parca.append([_r(s), _r(u)])
            elif abs(u - s) > 0.5:
                dolgu.append([_r(s), _r(u)])
        KA["parca"], KA["dolgu"] = parca, dolgu
        KA["uc"] = {k: _r(t) for k, t in KA["uc"].items()}
        KA["sm"] = _r(sm)

    # ---------- aşıklar ----------
    def sira_ana(sol):
        """Kart modelinin aşık sıraları (yüz, saçaktan eğim boyunca) ve sıra başına parça boyları (arka uçtan)."""
        rows = defaultdict(list)
        for n, k in IFC.items():
            if not n.startswith("ASIK"):
                continue
            xc = (k[0] + k[3]) / 2
            if (xc < W / 2) != sol:
                continue
            rows[round(xc, 2)].append((k[1], k[4]))
        out = []
        for xc in sorted(rows, reverse=not sol):
            s = ((xc + SC) if sol else (W + SC - xc)) / COS
            ps = sorted(rows[xc], key=lambda p: -p[1])     # arka uçtan öne
            out.append((round(s, 2), [round(p[1] - p[0], 2) for p in ps]))
        return out

    def sira_kural(Lp):
        """Kural (kart modelinin ana çatıdaki düzeni): mahya sırası, mahyadan 60 cm arayla sıralar, saçakta bir sıra."""
        sm = Lp / COS
        out = [round(4.35 / COS, 2)]
        k = 1
        while sm - 60 * k > out[0] + 10:
            out.append(round(sm - 60 * k, 2))
            k += 1
        out.append(round((Lp - 4.35) / COS, 2))
        return sorted(out)

    AL, AR = sira_ana(True), sira_ana(False)
    # pafta: sıradaki parça boyları baştan; şablon son parçayı sıranın kalanıyla keser
    asik = {"ML": {"sira": [s for s, _ in sorted(AL)], "pafta": [p for _, p in sorted(AL)], "bas": "min"},
            "MR": {"sira": [s for s, _ in sorted(AR)], "pafta": [p for _, p in sorted(AR)], "bas": "max"}}
    for v in VR:
        for yan in ("L", "R"):
            Lp = v["M"] - v["kutu"][0] if yan == "L" else v["kutu"][2] - v["M"]     # yüzün yatay açıklığı (mahyadan saçağa)
            dev = v["sol_devam"] if yan == "L" else v["sag_devam"]
            if dev:                                     # ana yüzün devamı: ana sıraların veranda mahyasının altında kalanları + mahya sırası
                ana = AL if yan == "L" else AR
                sr = sorted({s for s, _ in ana if s < (Lp - 4.35 - 8.7) / COS} | {round((Lp - 4.35) / COS, 2)})
            else:
                sr = sira_kural(Lp)
            lo_, hi_ = hadve_ar[f"H{v['R']}{yan}"]
            asik[f"{v['R']}{yan}"] = {"sira": sr, "pafta": [[410] * math.ceil((hi_ - lo_) / 410)] * len(sr), "bas": "min" if (yan == "L") == v["on"] else "max"}

    # ---------- kaplama ----------
    TP = satirlar("Tek kat çatı paneli")
    SP = satirlar("Sandviç panel")
    TR_ = satirlar("Trapez sac") if not TP and not SP else []
    if TP:
        kap_ad = "Tek kat panel"
        boy = {kucuk(s["kalem"].split(" · ")[1]): s["olcu"] for s in TP}
    elif SP:
        kap_ad = "Sandviç panel"
        boy = {"ana çatı": SP[0]["olcu"]}
    else:
        raise Desteklenmiyor("listede çatı kaplaması (tek kat panel ya da sandviç panel) satırı yok")
    renk = kucuk(OZ.get("çatı kaplama rengi", "") or "")
    hadve = {}
    for k, (lo_, hi_) in hadve_ar.items():
        n = max(1, round((hi_ - lo_ - 9) / 20))
        hadve[k] = [_r(lo_ + 4.5 + i * (hi_ - lo_ - 9) / n, 3) for i in range(n + 1)]
    for k, Y in yuz.items():
        lo_, hi_ = hadve_ar[Y["hadve"]]
        yer = "ana çatı" if k in ("ML", "MR") else next(f"{kucuk(v['ad'])} çatısı" for v in VR if k.startswith(v["R"]))
        bas_on = k in ("ML", "MR") or next(v["on"] for v in VR if k.startswith(v["R"]))
        # levhalar kalkan kenarından dizilir: ana çatıda ön kalkandan, verandada dış kalkanından
        if k in ("ML", "MR"):
            Y["serit"] = {"ad": f"{boy.get(yer, '')} ({yer})", "bas": lo_, "son": hi_, "yon": 1}
        else:
            Y["serit"] = {"ad": f"{boy.get(yer, '')} ({yer})", "bas": lo_ if bas_on else hi_, "son": hi_ if bas_on else lo_, "yon": 1 if bas_on else -1}
    mahya = [{"R": "AN", "topR": "AN", "r": 0, "O": [0, 0], "s0": W / 2, "z": [_r(-E1), _r(-E0)], "ad": "ana mahya"}]
    for v in VR:
        # mahya ana yüzün devamı olan yüzle biter (ötesi ana çatının yüzü); devam yoksa gövdeye kadar
        lo_, hi_ = hadve_ar[f"H{v['R']}{'R' if v['sag_devam'] and not v['sol_devam'] else 'L'}"]
        mahya.append({"R": v["R"], "topR": v["R"], "r": 0, "O": [0, 0], "s0": v["M"], "z": [_r(-hi_), _r(-lo_)], "ad": f"{kucuk(v['ad'])} mahyası"})
    kaplama = {
        "profil": {"hadve": 2.7, "tepe": 4.2, "taban": 7.4, "kenar": 4.5, "kapatir": 100},
        "hadve": hadve, "mahya": mahya,
        "metin": {"ad": f"{kap_ad} {{ad}}", "kesim": f"{kap_ad} · kesim parçası", "say_onek": kap_ad,
                  "profil": "100 cm kapatır; kesit kartta yazılı değil, çizimde 62 m²’deki 27/200 trapez profili gösterildi (varsayım)",
                  "dizilim": "kalkan kenarından başlayarak, her levha 100 cm kapatır; boy eğim boyunca (liste kuralı)",
                  "renk": renk or "—",
                  "liste": "; ".join(f"{s['kalem']} {s['olcu']} · {s['adet']} adet" for s in (TP or SP)),
                  "mahya_ad": "Metal kiremit mahyası", "mahya_liste": f"{ls('Metal kiremit mahyası')}; {ls('Mahya bandı')}"},
    }

    # ---------- izolasyon ----------
    izo = {"ana": {"yon": "x", "bas": 10, "L": _r(W - 20), "ad": "Çatı izolasyonu · 10 cm rulo cam yünü",
                   "serme": f"çatı kapanmadan önce, aşıkların arasından; rulo sol duvardan sağ duvara açılır, {'asma ' if ASMA else 'ters '}tavanın üstüne serilir"}}

    # ---------- dere ve iniş ----------
    for h in dere_hat:
        h["a0"], h["a1"], h["pafta"] = _r(h["a0"]), _r(h["a1"]), _r(h["a1"] - h["a0"])
    inisler = []
    for n, k in sorted(IFC.items()):
        if not n.startswith("INIS"):
            continue
        xc, yc = (k[0] + k[3]) / 2, (k[1] + k[4]) / 2
        sol = xc < W / 2
        inisler.append({"hat": "sol" if sol else "sağ", "s": _r(yc), "yuz": 0 if sol else W, "duvar": "sol duvar" if sol else "sağ duvar", "dis": 1})
    for v in VR:
        for sol in (True, False):
            kol = min(v["kolon"], key=lambda r: r[0] if sol else -r[2])
            yc = (kol[1] + kol[3]) / 2
            hat_ad = f"{kucuk(v['ad'])} {'sol' if sol else 'sağ'}"
            h = next(x for x in dere_hat if x["ad"] == hat_ad)
            inisler.append({"hat": hat_ad, "s": h["a0"] if v["on"] else h["a1"], "yuz": _r(kol[0] if sol else kol[2]), "duvar": "veranda kolonu", "sw": _r(yc)})
    for h in dere_hat:
        h.pop("veranda", None)

    # ---------- iç kapılar ----------
    doors = []
    for pr, (d, pp) in zip(HZ["panolar"], PL):
        ac = pp.acilim
        if ac is None or ac.tur != "ic_kapi":
            continue
        A = HZ["acikliklar"][pr["acikliklar"][0]["aciklik"]]
        u = G.mentese_ucu(ac)
        n = {"+x": [1, 0], "-x": [-1, 0], "+y": [0, 1], "-y": [0, -1]}[ac.icine_normal]
        a_h, a_o = (A["a0"], A["a1"]) if u == 0 else (A["a1"], A["a0"])
        hinge = [d.c, a_h] if d.yon == "y" else [a_h, d.c]
        kapali = [0, 1 if a_o > a_h else -1] if d.yon == "y" else [1 if a_o > a_h else -1, 0]
        mid = [hinge[0] + kapali[0] * 41 + n[0] * 30, hinge[1] + kapali[1] * 41 + n[1] * 30]
        oda = oda_bul(mid) or SIRA[-1]
        doors.append({"room": KIM[oda], "hinge": [_r(t) for t in hinge], "closed": kapali, "open": n})

    # ---------- pencere ve kapı ----------
    pencere = {}
    for A in HZ["acikliklar"]:
        if A["tur"] != "pencere" or A["olcu"].replace("x", "/") in pencere:
            continue
        en, by = (int(float(t)) for t in A["olcu"].split("x"))
        key = f"{en}/{by}"
        kod_ = KK.get(A["kod"])
        vas = en <= 60 and by <= 60
        karkas = bool(satirlar(f"Özel pencere karkası ({en}×{by})"))
        pencere[key] = {"kod": kod_, "ad": None if kod_ else f"PVC {'vasistas' if vas else 'pencere'} {key}",
                        "liste": ls("PVC vasistas" if vas else "PVC pencere", key, ad=f"PVC {'vasistas' if vas else 'pencere'}"),
                        "tip": "vasistas" if vas else "acilir", "karkas": karkas}
    pr_renk = kucuk(OZ.get("pencere rengi", "") or "")
    pvc_beyaz = not pr_renk or "beyaz" in pr_renk or "alıcı" in pr_renk
    # dış kapı alıcıya aitse liste satırı 0 adetle yazılır: rehber kapıyı "alıcıya ait" gösterir
    dk = [] if "alıcı" in kucuk(OZ.get("dış kapı", "")) else [s for s in satirlar("Prefabrik çelik kapı") if s.get("adet")]
    dk_m = re.search(r"\((SAĞ|SOL)\)", dk[0]["kalem"]) if dk else None
    dk_yon = dk_m.group(1).lower() if dk_m else "yönü planda"

    # ---------- yazılar ----------
    SAYI = {"n_ic": adet("Amerikan kapı"), "n_pen": adet("PVC pencere"), "n_vas": adet("PVC vasistas")}
    yatak = sum(1 for ad, _, _, _ in ODA if ad.startswith("YATAK ODASI"))
    m2 = round(sum(o["net_m2"] for o in odalar), 2)
    kaplama_txt = f"{kucuk(kap_ad)}{' (' + renk + ')' if renk else ''}"
    ver_ozet = ", ".join([f"{'önde' if v['on'] else 'arkada'} {fmtc(v['rect'][2] - v['rect'][0])} × {fmtc(v['rect'][3] - v['rect'][1])} cm" for v in VR] +
                         ([f"gövdenin içinde {fmtc(GVK['vk'][2] - GVK['vk'][0])} × {fmtc(GVK['vk'][3] - GVK['vk'][1])} cm (ana çatının altında)"]
                          if GVK and not GVK["nis"] else []))
    nis_ozet = (f"; gövdenin içinde {fmtc(GVK['vk'][2] - GVK['vk'][0])} × {fmtc(GVK['vk'][3] - GVK['vk'][1])} cm giriş nişi (ana çatının altında)"
                if GVK and GVK["nis"] else "")
    oda_listesi = ", ".join(kucuk(t) for _, _, t, _ in ODA)
    h_oda = defaultdict(lambda: defaultdict(int))
    for p in panels:
        h_oda[p["room"]]["pdis" if p["duvar"] == "dis" else "pic"] += 1
        if p["op"] and p["op"]["kind"] == "win":
            h_oda[p["room"]]["pen"] += 1
        if p["op"] and p["op"]["kind"] in ("door", "door_ext"):
            h_oda[p["room"]]["kap"] += 1
    for h in hs:
        h_oda[h["room"]]["h"] += 1
        if h["stub"]:
            h_oda[h["room"]]["t"] += 1
    for p in posts:
        h_oda[p["room"]]["kose"] += 1

    def oda_metni(kim, ilk, son):
        c = h_oda[kim]
        t = []
        if c["pdis"]:
            t.append(f"{c['pdis']} dış pano (100'lük{', ' + str(c['pen']) + ' pencereli' if c['pen'] else ''})")
        if c["pic"]:
            t.append(f"{c['pic']} iç pano ({IC_KAL})")
        s = ("Dizilim bu odanın arka sol köşesinden başlar. " if ilk else "") + \
            ("Bu odayla " + ", ".join(t) + " kurulur" if t else "Bu odanın duvarları önceki odalarla kuruldu")
        if c["kap"]:
            s += f"; {c['kap']} pano kapılı"
        if c["h"]:
            s += f". Aralarına {c['h']} H girer" + (f" ({c['t']} tanesi T birleşiminde 3’lü H)" if c["t"] else "")
        if c["kose"]:
            s += f", köşelerde {c['kose']} köşe direği"
        s += ". Panolar sırayla alt çerçeveye oturtulur ve H’lara geçirilir; önceki odalarla ortak duvarlar o odalarla kuruldu."
        if son:
            s += " Dizilim bu odada kapanır."
        return s

    rooms = []
    for i, (ad, kim, tad, st) in enumerate(ODA):
        adlar = [ad] + [b for b, h in BIRLES.items() if h == ad]
        r = {"id": kim, "ad": tad, "m2": round(sum(POLY[a]["net_m2"] for a in adlar), 2),
             "rects": [[_r(t) for t in q] for a in adlar for q in dikdortgenler(POLY[a]["poligon"])], "step": st,
             "metin": oda_metni(kim, i == 0, i == len(ODA) - 1)}
        r["kamera"] = round(min(12.5, max(8, 5 + 1.6 * math.sqrt(r["m2"]))), 1)
        if any(w in ad for w in ("BANYO", "WC")):
            r["yesil"] = True
        rooms.append(r)

    n_ana = len(konum)
    aralik = sorted({round(b - a, 1) for a, b in zip(alt_bas, alt_bas[1:])})
    vmetin = []
    for v in VR:
        vmetin.append(f"{kucuk(v['ad'])} ({fmtc(v['rect'][2] - v['rect'][0])} × {fmtc(v['rect'][3] - v['rect'][1])} cm): "
                      f"{len(v['kolon'])} kolon, dış kiriş ve iki yan kiriş")
    yavru = ", ".join(f"{kucuk(v['ad'])} {adet('Yavru makas · ' + kucuk(v['ad']) + ' çatısı')}" for v in VR)
    alcipan = {"yesil": ls("Tavan yeşil alçıpan"), "beyaz": ls("Tavan beyaz alçıpan")}
    metin = {
        "ic_kal": IC_KAL,
        "alt_liste": {"dis": ls("100'lük alt çerçeve"), "ic": ls(f"{IC_KAL} alt çerçeve")},
        "dis_kapi": f"çelik kapı 90 × 200 ({dk_yon})" if dk else "dış kapı",
        "ic_kapi_boslugu": "Kapı boşluğu 82 × 200 (kasalı)",
        "dvr_kaynak": "—",
        "ozel_h_liste": "—",
        "dubel_ad": "Çelik dübel", "dubel_liste": f"{ls('Çelik dübel')} (dübelli H adedi kadar) + {ls('Şase pul', ad='şase pul')}",
        "ceku_liste": ls("Çektirme U'su 100 (iç duvar)") if IC_100 else ls("Çektirme U'su 60"),
        "omega_liste": {"sacak": ls("100'lük saçak omegası"), "duvar": ls("100'lük duvar omegası"), "bas": ls("Baş makas omegası"),
                        "ic": ls("60'lık duvar omegası") if satirlar("60'lık duvar omegası") else ls("60'lık tavan omegası")},
        "sacak_liste": ls("Saçak sacı"),
        "ara_ad": "Ara makas", "ara_gorev": "—",
        "makas_profil": "kesit kartta yazılı değil (MA-01, MA-02); iç çubuklar 62 m² rehberindeki düzende (Warren) gösterildi",
        "makas_kaynak": "motorun kart modeli (yer, açıklık); kesit 62 m² rehberinden",
        "betopan": {"dolgu": "duvar ucunda kalan üçgen (levhaların artanından)",
                    "levha": "125 × 250 × 8 mm" + (", yüksek kalkanda dik şerit, alçak kalkanda yatay" if any(KA_dik) and not all(KA_dik) else
                                                   ", dik şerit" if any(KA_dik) else ", yatay"),
                    "pafta": ("dizilim: 125 cm'ye sığan kalkanda 62 m²'deki gibi mahyadan iki yana 250'lik yatay levhalar"
                              + (f"; daha yüksek kalkanda (ana kalkan {fmt(tepe + 13)} cm) 125'lik dik şeritler (paftası yok, varsayım)" if any(KA_dik) else "")
                              + f"; {ls('Baş makas betopanı')}")},
        "z_liste": ls("Baş makas Z'si"),
        "tomega": {"ad": "60'lık tavan omegası (asma dizme tavan)" if ASMA else "60'lık tavan omegası (ters tavan)",
                   "pafta": f"motorun kart modeli: {len(OMP)} parça, {fmt(sum(q['boy'] for q in OMP) / 100, 1)} m (iç duvar üstleriyle)",
                   "liste": ls("60'lık duvar omegası") if satirlar("60'lık duvar omegası") else ls("60'lık tavan omegası")},
        "alcipan_liste": alcipan,
        "boardex_liste": "—",
        "tavan_h_liste": ls("Tavan H'ı"),
        "asik_liste": ls("Aşık"),
        "izo_liste": ls("Çatı şiltesi"),
        "tersmahya": {"ad": "—", "gorev": "—", "liste": "—"},
        "alin": {"ad": "Alın sacı",
                 "alin": "~{h} cm: kaplamanın kenar hadvesinden saçak altının 6 cm altına; dereyi de içine alır, ayrı alt uç parçası yok (Lokman, 26.10.2026)",
                 "kaynak": "Lokman çizimleri (24.10.2026)",
                 "profil": "tırnak 3 (baş makas Z'sine) → saçak altı 30 → alın → hadve üstünden kıvrım → hadveyi kavrayan kıvrım",
                 "uc": "saçak altı kolu makasın topuğuna dayanır, orada kesilir; alın yüzü ve üst kıvrım derenin ucunu kapatmak için devam eder (Lokman, 26.10.2026)",
                 "proje": "alın ~{h} cm: 62 m² rehberindeki gibi; kesin ölçü teyit bekler",
                 "liste": ls("Alın sacı")},
        "dere": {"ad": "Metal dere", "kesit": "K profil, 15 × 11,4 cm (38’lik açınım), çatı renginde",
                 "pafta": f"motorun kart modeli: ana çatıda 2 hat; verandalarda {2 * len(VR)} hat (kural)",
                 "liste": f"{ls('Metal dere')}; {ls('Dere kapağı', ad='dere kapağı')}, {ls('Dere kelepçesi', ad='dere kelepçesi')}"},
        "inis": {"ad": "İniş borusu (70 mm PVC)", "agiz_kolon": "kolonun hizasında; kaz boynu kolona dik döner",
                 "agiz_kose": "derenin köşe ucunda, borunun hizasında; kaz boynu duvara dik döner, boru köşe direğinin yanından iner (Lokman’ın fotoğrafları)",
                 "agiz": "borunun hizasında; kaz boynu duvara dik döner", "kesit": "70 mm PVC boru; bina ile birlikte iner",
                 "takim": "iniş aparatı · 2 açık dirsek (kaz boynu) · boru L 2000 + L 500 · 2 kelepçe · kapalı dirsek",
                 "pafta": f"{len(inisler)} iniş (ana çatıda motorun kart modelinden, verandada kolonlarda)",
                 "liste": f"{ls('Metal dere inişi aparatı')}; {ls('70 mm PVC dere iniş borusu', 'L 2000', ad='iniş borusu')}"},
        "ic_kapi": {"kod": "K-01", "not": f"{ls('Amerikan kapı')}; yer ve açılış yönü motorun planından"},
        "pvc_renk": "beyaz, iç ve dış" if pvc_beyaz else pr_renk, "pvc_renk_kisa": "beyaz" if pvc_beyaz else pr_renk,
        "dis_kapi_kanat": {"kod": "K-02", "kanat": f"kanat 90 × 200, {dk_yon}" if dk else "alıcıya ait", "liste": ls("Prefabrik çelik kapı")},
        "bolum_cati": "Veranda ve çatı" if VR or GVK else "Çatı",
    }

    def K(t, az, el, dd, plan_=False):
        return {"t": t, "az": az, "el": el, "d": dd, **({"plan": True} if plan_ else {})}

    pen_ozet = ", ".join(f"{adet('PVC pencere', o)} × {o}" for o in sorted({s["olcu"] for s in satirlar("PVC pencere")}))
    vas = adet("PVC vasistas")
    ic_say = adet("Amerikan kapı")
    th_n = len(tavan.get("h", []))
    adim = [
        {"ad": "Genel bakış", "t": "Bitmiş bina ve malzeme listesi",
         "p": f"__PROJE__: gövde {fmtc(W)} × {fmtc(DY)} cm, {oda_listesi}" + (f"; {ver_ozet} veranda" if ver_ozet else "") + nis_ozet +
              f". Beşik çatı %{fmt(TAN * 100)}, {kaplama_txt}; {'asma dizme tavan' if ASMA else 'ters tavan'}. Model motorun planından ve kimlik kartlı "
              "modelinden kuruldu; her parça kimlik kartına bağlı (kartı olmayanlarda yükleme listesindeki adı yazar). Bir parçaya dokunun, kartı açılır. "
              "Oynat’a basınca montaj oda oda, {N} adımda gösterilir.",
         "head": "Kimlik kartına göre adetler", "kamera": K([0, 1.4, 0.3], 0.62, 0.36, 19.5)},
        {"ad": "Alt çerçeve", "t": "Alt çerçeve",
         "p": ("Zemin hazır olduktan sonra 100’lük alt çerçeve dış ve iç duvar hatlarına" if IC_100 else
               "Zemin hazır olduktan sonra 100’lük alt çerçeve dış duvar hattına, 60’lık alt çerçeve iç duvar hattına") +
              " serilip sabitlenir. Kapı boşluklarında çerçeve kesilir. Panolar bu çerçeveye oturur.",
         "kamera": K([0, 0, 0.3], 0.45, 1.05, 15.5),
         "rows": [x for x in (LR("100'lük alt çerçeve"), LR("60'lık alt çerçeve"), I("Dış duvar hattı", "{alt_dis} m"), I("İç duvar hattı", "{alt_ic} m")) if x]},
        *({"oda": r["id"]} for r in rooms),
    ]
    gv_olcu = f"{fmtc(GVK['vk'][2] - GVK['vk'][0])} × {fmtc(GVK['vk'][3] - GVK['vk'][1])} cm" if GVK else ""
    nis_metin = (f"Giriş nişi gövdenin içinde ({gv_olcu}), önü açık; iki yanı ve arkası gövde duvarı, dış kapı arkadaki duvarda. Açık kenarına "
                 f"{len(GVK['kir'])} kiriş ({', '.join(GVK['kir'])}) duvar üstü kotunda iki yandaki duvarı bağlar ve duvarın yerini tutar: üstüne baş makas "
                 "omegası, sonra ana çatının makasları gelir.") if GVK and GVK["nis"] else ""
    if GVK and VR and not GVK["nis"]:
        raise Desteklenmiyor("hem gövdeden taşan hem gövdenin içinde kolonlu veranda; rehber ikisini bir adımda kurmuyor")
    if GVK and not VR:
        adim.append({"ad": "Giriş nişi" if GVK["nis"] else "Veranda", "t": "Giriş nişinin kirişi" if GVK["nis"] else "Veranda kolon ve kirişleri",
                     "p": nis_metin or (f"Veranda gövdenin içinde ({gv_olcu}), ana çatının altında: "
                          f"{GVK['kol']} kolon ve {len(GVK['kir'])} kiriş ({', '.join(GVK['kir'])}). Kolon (100 × 100) dış köşeye dikilir; kirişler duvar "
                          "üstü kotunda kolonu gövdeye bağlar ve duvarın yerini tutar: üstlerine saçak ve baş makas omegası, sonra ana çatının makasları gelir."),
                     "kamera": K([0, 1.2, 0], 0.9, 0.45, 15)})
    if VR:
        adim.append({"ad": "Verandalar" if len(VR) > 1 else "Veranda", "t": "Veranda kolon ve kirişleri",
                     "p": "Verandalar gövdeden taşar: " + "; ".join(vmetin) + f". Kolonlar (100 × 100) dış köşelere dikilir; üstlerine duvar üstü kotunda "
                          "dış kiriş bağlanır, yan kirişler dış kirişi gövdeye bağlar. Yavru makaslar bu kirişlere oturur." + (" " + nis_metin if nis_metin else ""),
                     "kamera": K([0, 1.2, 0], 0.9, 0.45, 18)})
    adim += [
        {"ad": "Saçak, duvar ve baş makas omegası", "t": "Saçak, duvar ve baş makas omegası",
         "p": "Makasların oturacağı hatlara omega geçirilir. 100’lük omegalar 10,5 cm’dir (100 mm pano + iki yanda 2 mm H kanadı): dış kanat dışarıda tam yaslanır, "
              "içte kalan aralıklara silikonize mastik sıkılır. Sol ve sağ duvarın (saçak duvarları)" + (" ve veranda yan kirişlerinin" if VR or (GVK and not GVK["nis"]) else "") +
              " üstüne 100’lük saçak omegası; "
              "ön ve arka duvarın üstüne baş makas omegası (fabrikada hazırlanır: dışta baş makas betopanının gireceği 1 cm U yanak)" +
              ("; verandaların dış kirişlerine 100’lük duvar omegası (listede böyle sayılır)" if VR else "") +
              (f"; {'nişe' if GVK['nis'] else 'verandaya'} bakan gövde duvarlarına 100’lük duvar omegası" if GVK else "") +
              ". İç duvarların üstüne 60’lık omega geçirilir; kapı üstlerinden kesintisiz geçer.",
         "kamera": K([0, 2.3, 0.3], 0.62, 0.55, 15.5),
         "rows": [x for x in (LR("100'lük saçak omegası"), LR("100'lük duvar omegası"), LR("Baş makas omegası"),
                              R(None, "60’lık omega (iç duvar üstü)", "{omega_ic_n} parça · {omega_ic_m} m", "model"), I("Sac", "1 mm")) if x]},
        {"ad": "Ana çatı" + (" ve veranda makasları" if VR else " makasları"), "t": "Ana çatı" + (" ve veranda makasları" if VR else " makasları"),
         "p": f"Ana çatı: {n_ana} makas (MKS01–{n_ana:02d}) {fmtc(SAYIM['makas_aralik_cm'])} cm aralıkla; iki uçta baş makas, arada {n_ana - 2} orta makas. "
              f"Açıklık {fmtc(W + 2 * SC)} cm (iki yanda {fmtc(SC)} cm saçak), eğim %{fmt(TAN * 100)} ({fmt(EGIM_D, 1)}°), tepe yaklaşık {fmt(tepe)} cm. "
              "Makaslar sol ve sağ duvardaki kulaklı H’ların hizasına oturur; 10 cm topuk, duvar hizasında dikme, Warren zikzak." +
              (f" Verandaların çatısı ana çatıyla aynı yönde küçük birer beşiktir; yavru makaslar ({yavru}) dış kirişe ve yan kirişlere oturur. "
               "Yavru makaslar motorun modelinde yok: adet ve boy listeden, yerleri derinlik boyunca eşit aralıkla gösterildi." if VR else ""),
         "kamera": K([0, 2.6, 0], 0.95, 0.5, 18),
         "extra": [I("Ana çatı", f"açıklık {fmtc(W + 2 * SC)} cm · %{fmt(TAN * 100)} · tepe ≈ {fmt(tepe)} cm"),
                   I("Makas aralığı", " · ".join(fmtc(a) for a in aralik) + " cm")] +
                  [x for x in (LR("Makas (baş)"), LR("Makas (orta)"), *(LR(f"Yavru makas · {kucuk(v['ad'])} çatısı") for v in VR)) if x]},
        {"ad": "Baş makas betopanı ve Z", "t": "Baş makas betopanı ve Z",
         "p": f"{'Dört' if len(VR) == 2 else 'Üç' if len(VR) == 1 else 'İki'} kalkan var: ana çatının önü ve arkası" + (" ve verandaların dış kalkanları" if VR else "") +
              ". Kalkanın dış yüzü betopanla kapatılır: betopan (8 mm) makasa dayanır, alt ucu baş makas omegasının dış U yanağına girer; aralıklara silikon mastik "
              "sıkılır. " + ("Ana kalkan 125 cm’lik levhadan yüksek olduğu için levhaları mahyadan iki yana dik şerit olarak gösterildi (paftası yok, varsayım); "
                             "125’e sığan kalkanda levhalar 62 m²’deki gibi yatay. " if any(KA_dik) else
                             "Levhalar 62 m²’deki gibi mahyadan iki yana yatay dizilir; uçta artandan makas ucu dolgusu. ") +
              "Üstüne baş makas Z’si gelir; alın sacının tırnağı buna girer." +
              "".join(f" {kucuk(v['ad']).capitalize()} çatısının {'sol' if v['sol_devam'] else 'sağ'} yüzü ana çatının {'sol' if v['sol_devam'] else 'sağ'} "
                      "yüzünün devamıdır; ana kalkanın o ucu veranda mahyasından başlar." for v in VR if v["sol_devam"] or v["sag_devam"]),
         "kamera": K([W / 2, 3.0, 0], 0.4, 0.2, 15, True),
         "rows": [x for x in (LR("Baş makas betopanı"), LR("Baş makas Z'si")) if x]},
        {"ad": "Tavan omegaları ve H’lar" if ASMA else "Tavan omegaları", "t": "Asma tavan omegaları ve tavan H’ları" if ASMA else "Tavan omegaları",
         "p": (f"Asma dizme tavan: odalarda 60’lık omegalar mahyaya paralel uzanır (iç duvarların üstündekiler bir önceki adımda). Omegaların arasına "
               f"{fmtc(_pr(kurallari_oku()['prefabrik'], 'tavan_h_aralik_m') * 100)} cm’de bir tavan H’ı takılır; alçıpan levhalar bu gözlere dizilecek. "
               "Omegalar motorun kart modelinden; H’lar kuralın aralığıyla yerleştirildi.") if ASMA else "Tavan omegaları motorun kart modelinden.",
         "kamera": K([0, 2.3, 0.3], 0.55, 1.28, 15),
         "rows": [x for x in (R("OM-01", "Tavan omegası (oda içi)", f"{len(omega)} parça", "model"), LR("60'lık duvar omegası"), LR("60'lık tavan omegası"),
                              LR("Tavan H'ı"), I("Modelde H", f"{th_n} parça") if ASMA else None, LR("PVC omega kapak")) if x]},
        {"ad": "Asma tavan alçıpanı" if ASMA else "Ters tavan alçıpanı", "t": "Asma tavan alçıpanı" if ASMA else "Ters tavan alçıpanı",
         "p": "12,5 mm alçıpan levhalar (120 × 250) kesilip omega ve H gözlerine dizilir; banyolarda yeşil (ıslak hacim) alçıpan. Omegaların altı PVC omega kapakla kapatılır." +
              (" Verandalarda tavan yok." if VR else ""),
         "kamera": K([0, 2.3, 0.3], 0.55, 1.28, 15),
         "extra": [x for x in (LR("Tavan beyaz alçıpan"), LR("Tavan yeşil alçıpan"), LR("Alçıpan vidası"), I("Modelde göz", f"{len(tavan.get('goz', []))} adet") if ASMA else None) if x]},
        {"ad": "Çatı izolasyonu", "t": "Çatı izolasyonu (10 cm rulo cam yünü)",
         "p": "Aşıklardan önce tavanın üstüne 10 cm rulo cam yünü serilir. Her makas aralığına bir şerit gelir: rulo sol duvarın üstünden başlar, açılarak sağ duvara kadar serilir." +
              (" Verandaların üstü açık (tavan yok), izolasyon yalnız gövdede." if VR else ""),
         "kamera": K([W / 2, 2.6, DY / 2], 2.5, 0.95, 15, True),
         "extra": [x for x in (LR("Çatı şiltesi"), I("Modelde", "{izo_n} şerit · ≈ {izo_m2} m²")) if x]},
        {"ad": "Aşıklar", "t": "Omega aşıklar",
         "p": f"Aşıklar mahyadan 60 cm arayla makasların üst başlıklarına vidalanır; saçakta bir sıra. Ana çatının her yüzünde {len(AL)} sıra "
              f"({' + '.join(fmtc(p) for p in (AL[0][1] if AL else []))} + kalan); arka kalkandan başlar. "
              + ("Veranda çatılarında sıralar aynı kuralla (motorun modelinde yok). " if VR else "") +
              "Kalkan saçaklarında aşık uçları C kapamayla kapatılır.",
         "kamera": K([0, 3.2, 0], 0.95, 0.6, 17.5),
         "rows": [x for x in (LR("Aşık"), R("AS-01", "Aşık (ana çatı, kart modeli)", f"{sum(1 for n in IFC if n.startswith('ASIK'))} parça", "model"),
                              I("Kesit", "87 × 30 mm, sac 1 mm"), R(None, "C kapama", f"{2 * len(kalkan)} kalkan kenarı", "model")) if x]},
        {"ad": "Saçak sacı", "t": "Saçak sacı",
         "p": f"Aşıklardan sonra takılır. 3 cm tırnağı saçak omegasının üstüne, makasın altına girer; {fmtc(SC)} cm saçak altı, 13 cm alın ve makasa doğru 10 cm kıvrım. "
              "Saçaklar: ana çatının sol ve sağı" + (" ve verandaların iki yanı" if VR else "") + ". Saçak altı baş makasın hizasında kesilir; alın ve kıvrım köşeye, alın sacına kadar devam eder.",
         "kamera": K([W, 2.5, 0], 0.7, 0.18, 7, True),
         "rows": [x for x in (LR("Saçak sacı"), I("Profil", "3 + 30 + 13 + 10 cm"), I("Sac", "1 mm")) if x]},
        {"ad": "Dere ve inişler", "t": "Dere ve inişler",
         "p": f"Her saçağa metal dere asılır: sırtı saçak sacının alnına. {len(inisler)} iniş: ana çatıda köşelerde ve ortada (motorun kart modeli), "
              "verandalarda kolonun hizasında. Ağız borunun hizasında, kaz boynu duvara (verandada kolona) dik döner; boru köşe direği kaplamasının yanından kelepçeyle iner.",
         "kamera": K([0, 2.0, 0.3], -0.62, 0.28, 17),
         "rows": [x for x in (LR("Metal dere", "L 4000"), I("Dere hattı", f"{len(dere_hat)} hat · {fmt(sum(h['pafta'] for h in dere_hat) / 100, 1)} m"),
                              LR("Metal dere inişi aparatı"), LR("Dere kapağı")) if x]},
        {"ad": f"{kap_ad} ve mahya", "t": f"{kap_ad} ve mahya",
         "p": f"{kap_ad} ({renk or 'çatı rengi'}) doğrudan aşıkların üstüne serilip vidalanır (OSB ve nem bariyeri yok). Levhalar kalkan kenarından başlayarak dizilir, her levha "
              "100 cm kapatır; boy eğim boyunca: " + ", ".join(f"{y} {b}" for y, b in boy.items()) + ". Mahya metal kiremit mahyasıyla, altı mahya bandıyla kapatılır. "
              "Levhalar motorun modelinde yok; liste kuralının boyuyla dizildi.",
         "kamera": K([0, 2.8, 0.3], 0.62, 0.5, 19),
         "rows": [x for x in ([LR(s["kalem"], s["olcu"]) for s in (TP or SP)] + [I("Modelde", "{kaplama_n} levha · 100 cm kapatır"), LR("Metal kiremit mahyası"), LR("Mahya bandı")]) if x]},
        {"ad": "Alın sacları", "t": "Alın sacları",
         "p": "Alın sacı kalkanların eğik kenarlarına, kaplamadan sonra takılır: tırnağı baş makas Z’sine girer, saçak altı kolu aşıkların altını kapatır ve makasın "
              "topuğunda kesilir; üstte kaplamanın kenar hadvesini kavrar. Alın yüzü dereyi de içine alacak kadar geniştir: köşede saçak sacının alnıyla birleşir ve derenin ucunu kapatır.",
         "kamera": K([0, 2.8, 0.3], -0.62, 0.34, 18),
         "rows": [x for x in (LR("Alın sacı"),) if x]},
        {"ad": "Kapı ve pencereler", "t": "Kapı ve pencereler",
         "p": f"{'Beyaz' if pvc_beyaz else pr_renk.capitalize()} PVC pencereler ({pen_ozet}{', ' + str(vas) + ' × 60/40 vasistas' if vas else ''}) ve "
              f"{'prefabrik çelik dış kapı (90 × 200, ' + dk_yon + ')' if dk else 'dış kapı'} yerine konur. İç kapılar ({ic_say}) Amerikan kapı; yer ve açılış yönü motorun planından. "
              "Bu adımda çatı, tavan ve izolasyon gizlenir; düğmeyle geri açılır. Kanatlar ve kapılar sırayla açılıp kapanır.",
         "kamera": K([0, 0.8, 0.3], 0.5, 1.0, 15.5),
         "extra": [x for x in (LR("Özel pencere karkası"), LR("Prefabrik pencere vidası")) if x]},
    ]
    drop = [0, 0.3] + [1.4] * N_ODA + ([1.2] if VR or GVK else []) + [0.6, 1.4, 0.8, 0.5, -0.5, 0, 0.7, 0.6, 0.6, 0.9, 0.6, 0]
    for x, dr in zip(adim, drop):
        x["drop"] = dr
    assert len(adim) == N + 1 == len(drop), (len(adim), N, len(drop))
    genel = [
        {"grp": "Duvar panoları"}, {"pre": ["D-", "I-"], "adlar": []},
        {"grp": "Ekler, köşeler ve veranda"}, {"pre": ["H-", "B-", "V-"], "adlar": ["Çektirme"]},
        {"grp": "Çatı"}, {"pre": ["MA-"], "adlar": ["Yavru makas"]},
        *[x for x in (LR("100'lük saçak omegası"), LR("100'lük duvar omegası"), LR("Baş makas omegası"), LR("Saçak sacı"), LR("Baş makas betopanı"),
                      LR("Baş makas Z'si"), LR("60'lık duvar omegası"), LR("60'lık tavan omegası"), LR("Tavan H'ı"), LR("Tavan beyaz alçıpan"),
                      LR("Tavan yeşil alçıpan"), LR("Aşık"), LR("Çatı şiltesi")) if x],
        *[LR(s["kalem"], s["olcu"]) for s in (TP or SP)],
        *[x for x in (LR("Metal kiremit mahyası"), LR("Alın sacı"), LR("Metal dere", "L 4000"), LR("Metal dere inişi aparatı"), LR("Çelik dübel")) if x],
        {"grp": "Kapı ve pencere"}, {"pre": ["K-", "P-"], "adlar": ["PVC"]},
    ]
    # kartı olan ama modelde tek tek yerleşmeyen parçalar (şablon rolü → kart; 62 m²'nin verisinde yok, orada "kart yok")
    kart_bag = {"alt_dis": "AC-01", "alt_ic": "AC-01" if IC_100 else "AC-02", "omega_sacak": "CK-01", "omega_ic": "OM-01", "sacak": "CK-02", "betopan": "BT-01",
                "z": "CK-04", "tomega": "OM-01", "asik": "AS-01", "ckapama": "CK-05", "mahya": "CK-06", "alin": "CK-03", "dere": "DR-01",
                "inis": "DR-02", **({"kaplama": "KP-01"} if SP else {})}
    kabuk = {
        "proje": f"{kod} prefabrik", "kisa": kod, "chip": f"{fmt(m2, 2)} m² · motordan",
        "spec": [f"{fmtc(W)} × {fmtc(DY)} cm", "tek kat prefabrik", f"duvar {fmtc(H)} cm", f"beşik %{fmt(TAN * 100)} · {fmt(EGIM_D, 1)}°", kaplama_txt,
                 (f"{len(VR)} veranda" if VR else "gömme veranda" if GVK and not GVK["nis"] else "verandasız") + (" · giriş nişi" if GVK and GVK["nis"] else "")],
        "note": (f"Kaynak: İş Emri {ie.get('is_emri_no')} r{int(ie.get('revizyon', 1)):02d} → motorun planı (pano, açıklık, köşe direği, H, oda, veranda kolon ve "
                 "kirişleri) ve kimlik kartlı modeli (kartlar, H türleri, makas, aşık, iniş ve tavan omegası yerleri); adetler yükleme listesinden. "
                 "Yapım ayrıntıları (pano katmanları, köşe direği, omegalar, saçak ve alın sacı, Z, C kapama, dere, iniş) 62 m² rehberindeki Lokman çizimlerinden; "
                 "bu projede aynı sistem varsayıldı. Motorun modelinde olmayanlar kuraldan yerleştirildi ve kartlarında yazar: yavru makasların yeri, veranda "
                 "çatılarının aşıkları, " + ("asma tavanın H’ı ve gözleri, " if ASMA else "") + "kalkan betopanının dizilimi, çatı kaplamasının levhaları."),
    }
    return {
        "kod": kod, "dis": [W, DY], "h": H, "N": N, "S": S, "zemin": [-12, W + 12, min([0] + [v["rect"][1] for v in VR]) - 12, max([DY] + [v["rect"][3] for v in VR]) + 12],
        "renk": {"pvc": 0xF1F1EE} if pvc_beyaz else {}, "R": RF, "sacak": sacak, "kalkan": kalkan, "yuz": yuz, "asik": {"yuzler": asik}, "kaplama": kaplama,
        "izo": izo, "tavan": tavan, "verandalar": verandalar, "rooms": rooms, "panels": panels, "posts": posts, "ceku": ceku, "hs": hs, "alt": alt, "alt_m": alt_m,
        "omega_duvar": omega_duvar, "makas": makas, "omega": omega, "dere": {"hatlar": dere_hat, "inisler": inisler}, "doors": doors, "cards": cards,
        "pencere": pencere, "metin": metin, "adimlar": adim, "kart_bag": kart_bag, "genel": genel, "cati_adim": list(range(S["makas"], S["alin"] + 1)),
        "rozet": f"{fmtc(W)} × {fmtc(DY)} · {fmt(m2, 2)} m²", "kabuk": kabuk,
    }


def kiyas(kart: Path, kart_kodu: str, L: list[dict]) -> list[dict]:
    """Kart başına adet: kimlik kartlı model ve yükleme listesi. Kartın listedeki adı `liste.satirlar`'ın ilkidir (listedeki ek yazı,
    ör. "(SAĞ)" ya da " · ana çatı", eşlemeyi bozmaz; pencereli panonun üst paneli gibi ikinci satırlar sayılmaz). Aynı liste satırına
    giden kartlar (H türleri, pencere ölçüleri) birlikte kıyaslanır: listedeki adet grubun ilk kartında, notta grup yazar. Yalnız
    yerleşen adetle sayılan kartlarda fark işaretlenir; boyla, alanla ya da türevle alınanlarda listedeki adet stok ya da paket sayısıdır."""
    SAYIM = json.loads((kart / f"{kart_kodu}_kart_sayim.json").read_text(encoding="utf-8"))
    KT = {k["kod"]: k for k in json.loads((KOK / "kurallar" / "urun" / "kartlar.json").read_text(encoding="utf-8"))["kartlar"]}

    def tutar(x, ad):
        return x["kalem"] == ad or x["kalem"].startswith(ad + " (") or x["kalem"].startswith(ad + " ·")
    grup = defaultdict(list)
    for k in SAYIM["kartlar"]:
        grup[((KT.get(k["kod"], {}).get("liste") or {}).get("satirlar") or [None])[0] or k["kod"]].append(k)
    out = []
    for ad, g in grup.items():
        satir = [x for x in L if tutar(x, ad)]
        liste = sum(x["adet"] or 0 for x in satir) if satir else None
        model = sum(k.get("sabit", k["adet"]) for k in g)
        for i, k in enumerate(g):
            yol = KT.get(k["kod"], {}).get("sayim")
            m = k.get("sabit", k["adet"])
            if not satir:
                notu = "listede satırı yok"
            elif yol in ("boy_kesim", "metre"):
                notu = f"boyla alınır: modelde {m} parça" + (f", {fmt(k['metre'], 2)} m" if k.get("metre") else "") + "; listede stok boyu adedi"
            elif yol == "alan":
                notu = "alanla alınır (levha modelde yerleşmez); listede levha adedi"
            elif yol == "turev":
                notu = "başka kartın adedinden; listede metre"
            elif len(g) > 1:
                notu = f"{' + '.join(x['kod'] for x in g)} birlikte: modelde {model}, listede {liste}" if i == 0 else f"listedeki adet {g[0]['kod']} satırında"
            else:
                notu = ""
            out.append({"kod": k["kod"], "ad": k["ad"], "model": m, "liste": liste if i == 0 else None, "not": notu,
                        "fark": i == 0 and liste is not None and yol in ("yerlesen_adet", "sabit_paket") and liste != model})
    return sorted(out, key=lambda r: r["kod"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("is_emri", type=Path)
    ap.add_argument("kart", type=Path)
    ap.add_argument("kart_kodu")
    ap.add_argument("liste", type=Path)
    ap.add_argument("cikti", type=Path)
    ap.add_argument("--kod", default=None, help="rehberde görünen kod (varsayılan: kart kodu)")
    a = ap.parse_args(argv)
    d = kur(json.loads(a.is_emri.read_text(encoding="utf-8")), a.kart, a.kart_kodu,
            json.loads(a.liste.read_text(encoding="utf-8"))["satirlar"], a.kod or a.kart_kodu)
    a.cikti.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(a.cikti, "adım", d["N"], "oda", len(d["rooms"]), "pano", len(d["panels"]), "H", len(d["hs"]), "makas", len(d["makas"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
