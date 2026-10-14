"""İE-14 r2 · bankadan uyarlama: bankadaki bir planı işlemlerle talebe uydurur (LLM yok; koordinatı kod yazar).

Kaynak: bankadaki çelik modeller (`plan_uretici._banka` → `plan_sema.tanimdan`, 5 cm sapmalar `sapma_duzelt` ile giderilmiş) 14a'ya
getirilir (`hazirla`: ikinci veranda/sundurma atılır ve dış hat kırpılır, köşe veranda çatı altına alınır, çatı altındaki verandada çatı
kırma olur). Yalnız denetçiden geçen kaynak kullanılır.

İşlemler (saf fonksiyon; plan şeması → plan şeması; her dizinin sonunda denetçi):
- `ayna_x`, `ayna_y`, `devrik` (simetri; verandayı istenen cepheye çevirir, işlem sayısına girmez)
- `uzat(eksen, kesit, delta)`: kesit çizgisini kesen bütün dikdörtgenler uzar, ötesindekiler kayar; brüt alanı hedefe getirir
- `oda_ekle(yatak, eksen)`: bir yatak odasının ardına aynı derinlikte bir yatak odası şeridi (2+1 → 3+1)
- `veranda_kaldir`: şerit verandayı atar, dış hat kırpılır
- `bol(mahal, eksen, konum, ad, islev)`: büyük mahali ikiye böler (açık mutfaktan ayrı mutfak)
Arama: her kaynakta en çok 3 işlemlik diziler (simetri hariç); puan `plan_cozucu.puan` − kaynak topolojisi payı.
"""
from __future__ import annotations

import copy
import time
from functools import lru_cache

from beyin.plan_cozucu import IZ, acikliklar, cepheler, hazirla, puan, r5
from beyin.plan_denetim import denetle, kurallar

TOPOLOJI_PAYI = 3.0             # bankadaki gerçek yerleşimin korunması (puandan düşülür)
EN_COK_ISLEM = 3
CEPHE_X = {"B": "D", "D": "B"}
CEPHE_Y = {"G": "K", "K": "G"}
CEPHE_DEVRIK = {"G": "B", "B": "G", "K": "D", "D": "K"}


# ── simetri ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _cephe_cevir(p: dict, tablo: dict) -> None:
    for pc in p["pencereler"]:
        pc["cephe"] = tablo.get(pc["cephe"], pc["cephe"])
    for k in p["kapilar"]:
        if k.get("cephe"):
            k["cephe"] = tablo.get(k["cephe"], k["cephe"])


def ayna_x(p: dict) -> dict:
    q = copy.deepcopy(p)
    W = q["dis_olcu"]["en"]
    for m in q["mahaller"]:
        m["dikdortgenler"] = [[W - r[2], r[1], W - r[0], r[3]] for r in m["dikdortgenler"]]
    _cephe_cevir(q, CEPHE_X)
    return q


def ayna_y(p: dict) -> dict:
    q = copy.deepcopy(p)
    H = q["dis_olcu"]["boy"]
    for m in q["mahaller"]:
        m["dikdortgenler"] = [[r[0], H - r[3], r[2], H - r[1]] for r in m["dikdortgenler"]]
    _cephe_cevir(q, CEPHE_Y)
    return q


def devrik(p: dict) -> dict:
    """x ↔ y (köşegene göre yansıma): güney ↔ batı, kuzey ↔ doğu. Kırmada mahya yine uzun kenarda (verilmemişse)."""
    q = copy.deepcopy(p)
    q["dis_olcu"] = {"en": p["dis_olcu"]["boy"], "boy": p["dis_olcu"]["en"]}
    for m in q["mahaller"]:
        m["dikdortgenler"] = [[r[1], r[0], r[3], r[2]] for r in m["dikdortgenler"]]
    _cephe_cevir(q, CEPHE_DEVRIK)
    if (q.get("cati") or {}).get("mahya_yonu"):
        q["cati"]["mahya_yonu"] = {"x": "y", "y": "x"}[q["cati"]["mahya_yonu"]]
    return q


SIMETRILER = {"": lambda p: p, "ayna_x": ayna_x, "ayna_y": ayna_y, "ayna_xy": lambda p: ayna_y(ayna_x(p)), "devrik": devrik,
              "devrik_ayna_x": lambda p: ayna_x(devrik(p)), "devrik_ayna_y": lambda p: ayna_y(devrik(p)),
              "devrik_ayna_xy": lambda p: ayna_y(ayna_x(devrik(p)))}


# ── ölçü işlemleri ───────────────────────────────────────────────────────────────────────────────────────────────────────
def uzat(p: dict, eksen: str, kesit: int, delta: int) -> dict | None:
    """`kesit`'ten büyük bütün koordinatlar `delta` kayar (kesiti kesen dikdörtgenler uzar). Negatif delta kısaltır; bir dikdörtgen
    çökerse ya da kesitin ötesindeki bir sınır kesite değerse None."""
    k = 0 if eksen == "x" else 1
    q = copy.deepcopy(p)
    ust = q["dis_olcu"]["en" if k == 0 else "boy"]
    if not 0 < kesit < ust or delta % IZ:
        return None
    for m in q["mahaller"]:
        for r in m["dikdortgenler"]:
            for i in (k, k + 2):
                if r[i] > kesit:
                    r[i] += delta
                    if r[i] <= kesit:
                        return None
            if r[k + 2] - r[k] <= 0:
                return None
    q["dis_olcu"]["en" if k == 0 else "boy"] = ust + delta
    return q


def veranda_kaldir(p: dict) -> dict | None:
    """Şerit verandayı atar ve dış hattı kırpar; köşe veranda atılamaz (boşluk kalır)."""
    q = copy.deepcopy(p)
    ver = [m for m in q["mahaller"] if m["islev"] == "veranda"]
    if not ver:
        return q
    ad = ver[0]["ad"]
    q["mahaller"] = [m for m in q["mahaller"] if m["islev"] != "veranda"]
    q = _kirp(q)
    if q is None:
        return None
    for kp in q["kapilar"]:
        kp["arasinda"] = ["dis" if x == ad else x for x in kp["arasinda"]]
    return q


def _kirp(q: dict) -> dict | None:
    """Mahallerin sınır kutusuna kırpar ve kökene kaydırır; kutu boşluksuz dolmuyorsa None."""
    rs = [r for m in q["mahaller"] for r in m["dikdortgenler"]]
    x0, y0 = min(r[0] for r in rs), min(r[1] for r in rs)
    x1, y1 = max(r[2] for r in rs), max(r[3] for r in rs)
    if sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) != (x1 - x0) * (y1 - y0):
        return None
    for m in q["mahaller"]:
        m["dikdortgenler"] = [[r[0] - x0, r[1] - y0, r[2] - x0, r[3] - y0] for r in m["dikdortgenler"]]
    q["dis_olcu"] = {"en": x1 - x0, "boy": y1 - y0}
    return q


def _yeniden_ac(q: dict) -> None:
    """Pencere ve kapıları yeni mahal listesine göre tamamlar: var olanlar kalır (mahali duruyorsa), penceresiz oda pencere alır,
    holü (ya da salonu) olan yeni oda kapı alır."""
    adlar = {m["ad"] for m in q["mahaller"]}
    q["pencereler"] = [pc for pc in q["pencereler"] if pc["mahal"] in adlar]
    q["kapilar"] = [k for k in q["kapilar"] if all(x == "dis" or x in adlar for x in k["arasinda"])]
    W, H = q["dis_olcu"]["en"], q["dis_olcu"]["boy"]
    ce = cepheler(q["mahaller"], W, H)
    for pc in list(q["pencereler"]):                           # cephesi kaybolan pencere en uzun cepheye
        if not ce.get(pc["mahal"], {}).get(pc["cephe"]):
            yeni = sorted(((L, c) for c, L in ce.get(pc["mahal"], {}).items() if c != "veranda"), key=lambda t: -t[0])
            if yeni:
                pc["cephe"] = yeni[0][1]
            else:
                q["pencereler"].remove(pc)
    _, pencereler = acikliklar(q["mahaller"], W, H, [])
    pencereli = {pc["mahal"] for pc in q["pencereler"]}
    q["pencereler"] += [pc for pc in pencereler if pc["mahal"] not in pencereli and not any(x["mahal"] == pc["mahal"] for x in q["pencereler"])]


def _komsu_mu(a: dict, b: dict, en_az: int = 130) -> bool:
    for r in a["dikdortgenler"]:
        for s in b["dikdortgenler"]:
            if (r[2] == s[0] or s[2] == r[0]) and min(r[3], s[3]) - max(r[1], s[1]) >= en_az:
                return True
            if (r[3] == s[1] or s[3] == r[1]) and min(r[2], s[2]) - max(r[0], s[0]) >= en_az:
                return True
    return False


def serit_ac(p: dict, eksen: str, kesit: int, g: int) -> dict | None:
    """Sınır çizgisinde (`kesit`) `g` cm'lik şerit açar: kesiti kesen dikdörtgenler uzar, kesitte başlayanlar kayar, kesitte bitenler
    yerinde kalır. Açılan boşluk dönüşte `_bos` anahtarında (dikdörtgen listesi). Dış ölçü g kadar büyür."""
    k = 0 if eksen == "x" else 1
    q = copy.deepcopy(p)
    ust = q["dis_olcu"]["en" if k == 0 else "boy"]
    if not 0 < kesit < ust or g % IZ or g <= 0:
        return None
    for m in q["mahaller"]:
        for r in m["dikdortgenler"]:
            if r[k] >= kesit:
                r[k] += g
            if r[k + 2] > kesit:
                r[k + 2] += g
    q["dis_olcu"]["en" if k == 0 else "boy"] = ust + g
    # boşluk: şeritte hiçbir dikdörtgenin örtmediği aralıklar (dik eksende)
    dik = q["dis_olcu"]["boy" if k == 0 else "en"]
    ortulen = sorted((r[1 - k], r[3 - k]) for m in q["mahaller"] for r in m["dikdortgenler"] if r[k] <= kesit and r[k + 2] >= kesit + g)
    bos, imlec = [], 0
    for a0, a1 in ortulen:
        if a0 > imlec:
            bos.append((imlec, a0))
        imlec = max(imlec, a1)
    if imlec < dik:
        bos.append((imlec, dik))
    q["_bos"] = [([kesit, a0, kesit + g, a1] if k == 0 else [a0, kesit, a1, kesit + g]) for a0, a1 in bos]
    return q


def oda_ekle(p: dict, yatak: str, eksen: str, yer: str = "son", genislik: int | None = None) -> dict | None:
    """`yatak` odasının önüne (`yer` 'bas') ya da ardına ('son') aynı derinlikte yeni bir yatak odası: odanın sınırında şerit açılır,
    şeridi kesen odalar uzar, odanın hizasında açılan boşluk yeni oda olur. Başka boşluk kalırsa, ya da yeni oda hole (yoksa salona) en az
    130 cm değmiyorsa None."""
    k = 0 if eksen == "x" else 1
    m = next((x for x in p["mahaller"] if x["ad"] == yatak), None)
    if m is None or m["islev"] != "yatak_odasi":
        return None
    ana = max(m["dikdortgenler"], key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    kesit = ana[k + 2] if yer == "son" else ana[k]
    g = genislik or r5(ana[k + 2] - ana[k])
    q = serit_ac(p, eksen, kesit, g)
    if q is None:
        return None
    bos = q.pop("_bos")
    if len(bos) != 1:
        return None
    n = sum(1 for x in q["mahaller"] if x["islev"] == "yatak_odasi") + 1
    ad = f"Yatak Odası {n}"
    while any(x["ad"] == ad for x in q["mahaller"]):
        n += 1
        ad = f"Yatak Odası {n}"
    yeni_m = {"ad": ad, "islev": "yatak_odasi", "dikdortgenler": bos}
    q["mahaller"].append(yeni_m)
    dagitan = [x for x in q["mahaller"] if x["islev"] == "hol"] + [x for x in q["mahaller"] if x["islev"] == "salon"]
    kapi = next((x for x in dagitan if _komsu_mu(x, yeni_m)), None)
    if kapi is None:
        return None
    q["kapilar"].append({"arasinda": [kapi["ad"], ad]})
    _yeniden_ac(q)
    return q


def bol(p: dict, mahal: str, eksen: str, konum: int, yeni_ad: str, yeni_islev: str, yeni_salon_adi: str | None = None) -> dict | None:
    """`mahal`'in ana dikdörtgenini `konum`'da böler; büyük koordinat yanı yeni mahal olur, ikisi arasına kapı."""
    k = 0 if eksen == "x" else 1
    q = copy.deepcopy(p)
    m = next((x for x in q["mahaller"] if x["ad"] == mahal), None)
    if m is None:
        return None
    ana = max(m["dikdortgenler"], key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    if not ana[k] < konum < ana[k + 2]:
        return None
    a, b = list(ana), list(ana)
    a[k + 2], b[k] = konum, konum
    m["dikdortgenler"] = [a if r is ana else r for r in m["dikdortgenler"]]
    q["mahaller"].append({"ad": yeni_ad, "islev": yeni_islev, "dikdortgenler": [b]})
    if yeni_salon_adi and yeni_salon_adi != mahal:
        for kp in q["kapilar"]:
            kp["arasinda"] = [yeni_salon_adi if x == mahal else x for x in kp["arasinda"]]
        for pc in q["pencereler"]:
            if pc["mahal"] == mahal:
                pc["mahal"] = yeni_salon_adi
        m["ad"] = yeni_salon_adi
    q["kapilar"].append({"arasinda": [m["ad"], yeni_ad]})
    _yeniden_ac(q)
    return q


# ── kaynaklar ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def hazirla_kaynak(p: dict) -> dict | None:
    """Banka çevirisini 14a'ya getirir: ikinci veranda (sundurma) atılır, dış hat kırpılır; köşe veranda çatı altına; çatı altındaki
    verandada çatı kırma. Olmazsa None."""
    q = copy.deepcopy(p)
    ver = sorted([m for m in q["mahaller"] if m["islev"] == "veranda"],
                 key=lambda m: -sum((r[2] - r[0]) * (r[3] - r[1]) for r in m["dikdortgenler"]))
    for m in ver[1:]:
        q["mahaller"].remove(m)
        for kp in q["kapilar"]:
            kp["arasinda"] = ["dis" if x == m["ad"] else x for x in kp["arasinda"]]
    if len(ver) > 1:
        q = _kirp(q)
        if q is None:
            return None
    if ver:
        v = next(m for m in q["mahaller"] if m["islev"] == "veranda")
        x0, y0, x1, y1 = v["dikdortgenler"][0]
        W, H = q["dis_olcu"]["en"], q["dis_olcu"]["boy"]
        serit = (x0 == 0 and x1 == W) or (y0 == 0 and y1 == H)
        if not serit:
            v["ortu"] = "cati"
        if (v.get("ortu") or "cati") == "cati":
            q["cati"] = {**(q.get("cati") or {}), "tip": "kirma"}
            q["cati"].pop("mahya_yonu", None)
    q["kapilar"] = [k for i, k in enumerate(q["kapilar"]) if k not in q["kapilar"][:i] and len(set(k["arasinda"])) == 2]
    return q


@lru_cache(maxsize=1)
def _kaynaklar() -> tuple[dict, ...]:
    from beyin.plan_uretici import _banka
    out = []
    for b in _banka():
        q = hazirla_kaynak(b["plan"])
        if q is None:
            continue
        d = denetle(q, {}, kod="KAYNAK")
        if d["gecerli"]:
            out.append({"kod": b["kod"], "plan": q, "katalog_m2": b["katalog_m2"], "oda_programi": b["oda_programi"]})
    return tuple(out)


def kaynaklar(haric: tuple[str, ...] = ()) -> list[dict]:
    """Uyarlama kaynakları (denetçiden geçen, 14a'ya getirilmiş banka planları). Kör üretimde model `haric`."""
    return [copy.deepcopy(k) for k in _kaynaklar() if not any(kod_esit(k["kod"], h) for h in haric)]


def kod_esit(kod: str, haric: str) -> bool:
    """'Ç8201' ~ 'C8201', 'KT02' ~ 'KT-02'; varyant da dışlanır (C8801 → C8801K)."""
    def n(s):
        return str(s).upper().replace("Ç", "C").replace("-", "").replace(" ", "")
    return n(kod).startswith(n(haric))


# ── arama ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _say(p: dict, islev: str) -> int:
    return sum(1 for m in p["mahaller"] if m["islev"] == islev)


def _veranda_cephesi(p: dict) -> str | None:
    v = next((m for m in p["mahaller"] if m["islev"] == "veranda"), None)
    if not v:
        return None
    x0, y0, x1, y1 = v["dikdortgenler"][0]
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    if x0 == 0 and x1 == W:
        return "G" if y0 == 0 else "K"
    if y0 == 0 and y1 == H:
        return "B" if x0 == 0 else "D"
    return "kose"


def _kesitler(p: dict, eksen: str, delta: int, n: int = 3) -> list[int]:
    """Uzatma/kısaltma kesiti adayları: iki komşu sınır çizgisinin ortası; kestiği odaların en sıkışığının payı en büyük olanlar önce.
    Pay: oda (eksen boyunca) ölçüsü + delta − en küçük ölçü (salon 315, yatak 315, mutfak 265, banyo 185, hol 145, veranda 150)."""
    k = 0 if eksen == "x" else 1
    en_az = {"salon": 315, "yatak_odasi": 315, "mutfak": 265, "banyo": 185, "hol": 145, "depo": 115, "veranda": 150}
    cz = sorted({v for m in p["mahaller"] for r in m["dikdortgenler"] for v in (r[k], r[k + 2])})
    out = []
    for a0, a1 in zip(cz, cz[1:]):
        if a1 - a0 + min(delta, 0) < 40:
            continue
        kes = r5((a0 + a1) / 2)
        if not a0 < kes < a1:
            continue
        kesilen = [(m, r) for m in p["mahaller"] for r in m["dikdortgenler"] if r[k] < kes < r[k + 2]]
        ust = p["dis_olcu"]["en" if k == 0 else "boy"]
        if any(m["islev"] == "veranda" and r[k + 2] - r[k] < ust for m, r in kesilen):
            continue                                           # veranda derinliği ölçü ayarıyla değişmez (yalnız boydan boya şerit uzar)
        pay = min((r[k + 2] - r[k] + delta - en_az.get(m["islev"], 100) for m, r in kesilen), default=-1)
        out.append((pay, -(a1 - a0), kes))
    out.sort(key=lambda t: (-t[0], t[1], t[2]))
    return [kes for pay, _, kes in out if pay >= 0][:n]


def _alan_ayarlari(p: dict, hedef_m2: float) -> list[tuple[list, dict]]:
    """Brüt alanı hedefe getiren uzatma seçenekleri: x'te, y'de ya da ikisinde yarı yarıya; kesit payı en büyük çizgilerde."""
    W, H = p["dis_olcu"]["en"], p["dis_olcu"]["boy"]
    A0, A = W * H, hedef_m2 * 1e4
    if abs(A0 - A) / A <= 0.02:
        return [([], p)]
    out = []
    dx, dy = r5((A - A0) / H), r5((A - A0) / W)
    for kx in _kesitler(p, "x", dx):
        q = uzat(p, "x", kx, dx) if dx else None
        if q:
            out.append(([f"uzat x {dx:+d}"], q))
    for ky in _kesitler(p, "y", dy):
        q = uzat(p, "y", ky, dy) if dy else None
        if q:
            out.append(([f"uzat y {dy:+d}"], q))
    f = math_sqrt(A / A0)
    dx2, dy2 = r5(W * (f - 1)), r5(H * (f - 1))
    if dx2 and dy2:
        for kx in _kesitler(p, "x", dx2, 2):
            for ky in _kesitler(p, "y", dy2, 2):
                q = uzat(p, "x", kx, dx2)
                q = uzat(q, "y", ky, dy2) if q else None
                if q:
                    out.append(([f"uzat x {dx2:+d}", f"uzat y {dy2:+d}"], q))
    return out


def math_sqrt(v: float) -> float:
    return v ** 0.5


def _yonlendir(p: dict, hedef: str | None) -> list[tuple[str, dict]]:
    """Verandayı istenen cepheye çeviren simetriler (en az değişiklikten başlayarak). Hedef yoksa yalnız kimlik."""
    if hedef is None:
        return [("", p)]
    out = []
    for ad, f in SIMETRILER.items():
        q = f(p)
        c = _veranda_cephesi(q)
        if c == hedef or (hedef == "yan" and c in ("B", "D")) or (hedef == "kose" and c == "kose"):
            out.append((ad, q))
    return out


def uyarla(program: dict, n: int = 2, haric: tuple[str, ...] = (), en_cok_denetim: int = 40, kod: str = "YENI") -> dict:
    """Program → bankadan uyarlanan en iyi n plan (denetçiden geçen). Dönüş: {adaylar: [{plan, tanim, ozet, puan, yol, kaynak, islemler}],
    denetim, sure_ms}. İstisna fırlatmaz."""
    t0 = time.time()
    kural = kurallar()
    hz = hazirla(program)
    talep = {"oda_programi": f"{program['yatak']}+{program.get('salon', 1)}", "alan_m2": program.get("alan_m2")}
    ver = hz["veranda"]
    hedef_cephe = None
    if ver:
        hedef_cephe = {"on": "G", "arka": "K", "yan": "yan", "kose": "kose"}[ver["konum"]]
    istenen_veranda = (program.get("veranda") or {}).get("istiyor")
    adaylar, denetim = [], 0
    for kay in kaynaklar(haric):
        p0 = kay["plan"]
        ny = _say(p0, "yatak_odasi")
        if not (ny <= program["yatak"] <= ny + 2) or _say(p0, "banyo") != int(program.get("banyo") or 1) or \
                (program.get("depo") and not _say(p0, "depo")):
            continue
        mutfak_var = _say(p0, "mutfak") > 0
        if program.get("mutfak") == "acik" and mutfak_var:
            continue
        islem0: list[str] = []
        vc = _veranda_cephesi(p0)
        if istenen_veranda is False and vc:
            if vc == "kose":
                continue
            p0 = veranda_kaldir(p0)
            if p0 is None:
                continue
            islem0.append("veranda kaldır")
        elif istenen_veranda and not vc:
            continue
        elif istenen_veranda and ((hedef_cephe == "kose") != (vc == "kose")):
            continue
        if istenen_veranda and ver and ver["ortu"] != "cati" and vc == "kose":
            continue
        for sim, p1 in _yonlendir(p0, hedef_cephe if istenen_veranda else None):
            if istenen_veranda and ver:
                v = next(m for m in p1["mahaller"] if m["islev"] == "veranda")
                v["ortu"] = ver["ortu"]
                p1["cati"] = {"tip": hz["cati"]}
            elif program.get("cati_tipi") and not any(m["islev"] == "veranda" and (m.get("ortu") or "cati") == "cati" for m in p1["mahaller"]):
                p1["cati"] = {"tip": program["cati_tipi"]}
            dizi: list[tuple[list[str], dict]] = [(islem0 + ([sim] if sim else []), p1)]
            # ayrı mutfak
            if program.get("mutfak") == "ayri" and not mutfak_var:
                yeni = []
                for isl, q in dizi:
                    s = next(m for m in q["mahaller"] if m["islev"] == "salon")
                    r = max(s["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
                    for eksen, k in (("x", 0), ("y", 1)):
                        L = r[k + 2] - r[k]
                        for konum in (r[k + 2] - 300, r[k] + 300):
                            if r[k] + 300 <= konum <= r[k + 2] - 300 or L >= 600:
                                q2 = bol(q, s["ad"], eksen, r5(konum), "Mutfak", "mutfak", "Salon")
                                if q2:
                                    yeni.append((isl + [f"böl {eksen}"], q2))
                dizi = yeni
            # yatak odası ekleme
            for _ in range(program["yatak"] - ny):
                yeni = []
                for isl, q in dizi:
                    for m in [m for m in q["mahaller"] if m["islev"] == "yatak_odasi"]:
                        for eksen in ("x", "y"):
                            for yer in ("son", "bas"):
                                dik = q["dis_olcu"]["boy" if eksen == "x" else "en"]
                                hedef_g = r5((program["alan_m2"] * 1e4 - q["dis_olcu"]["en"] * q["dis_olcu"]["boy"]) / dik) \
                                    if program.get("alan_m2") else 0
                                for g in sorted({None, 330, min(450, max(320, hedef_g)) if hedef_g else 330}, key=lambda v: v or 0):
                                    q2 = oda_ekle(q, m["ad"], eksen, yer, g)
                                    if q2:
                                        yeni.append((isl + [f"oda ekle ({m['ad']}, {eksen} {yer})"], q2))
                dizi = yeni
            # alan
            if program.get("alan_m2"):
                dizi = [(isl + i2, q2) for isl, q in dizi for i2, q2 in _alan_ayarlari(q, program["alan_m2"])]
            for isl, q in dizi:
                if len([i for i in isl if not i.startswith(("ayna", "devrik"))]) > EN_COK_ISLEM:
                    continue
                q["gerekce"] = f"uyarlama: bankadaki {kay['kod']}; " + (", ".join(isl) or "aynen")
                adaylar.append({"plan": q, "kaynak": kay["kod"], "islemler": isl, "on": puan(q, {"odalar_m2": _yaklasik(q)}, program)})
    adaylar.sort(key=lambda a: (a["on"], a["kaynak"], str(a["islemler"])))
    gecen = []
    gorulen = set()
    for a in adaylar:
        if denetim >= en_cok_denetim or len(gecen) >= n:
            break
        if a["kaynak"] in gorulen:                            # aynı kaynaktan iki seçenek gösterilmez
            continue
        denetim += 1
        d = denetle(a["plan"], talep, kural, kod=kod)
        if d["gecerli"]:
            gorulen.add(a["kaynak"])
            gecen.append({"plan": a["plan"], "tanim": d["tanim"], "ozet": d["ozet"], "yol": "uyarlama", "kaynak": a["kaynak"],
                          "islemler": a["islemler"], "puan": round(puan(a["plan"], d["ozet"], program) - TOPOLOJI_PAYI, 3)})
    gecen.sort(key=lambda g: g["puan"])
    return {"adaylar": gecen, "denetim": denetim, "sure_ms": int((time.time() - t0) * 1000)}


def _yaklasik(p: dict) -> dict:
    return {m["ad"]: sum((r[2] - r[0]) * (r[3] - r[1]) for r in m["dikdortgenler"]) / 1e4 * 0.93 for m in p["mahaller"] if m["islev"] != "veranda"}
