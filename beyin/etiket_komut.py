"""Etiketli plan komutları (çizim okuma ikinci döngüsü; Lokman, kart 28 Kasım 2026 05:55:38 UTC "Doğru, böyle kodla"; 05:59:11 UTC
"oda ismi versin büyüt veya küçült desin").

Bayi etiketli plana bakarak yazar; kural bayinin kendi cümlesini okur (K18), LLM yok. Kapalı komutlar:

1. Oda sınırı aksa: "O2'yi C aksına kadar büyüt", "O3'ü 4 aksına kadar küçült". Odanın aksa en yakın duvarı aksa taşınır; aynı
   sınırı paylaşan komşu bölüm de taşınır (komşu küçülür ya da büyür). Kaybolan bölüm olursa komut durur.
2. Pencere ölçüsü: "P1 120/180 olsun", "P2'yi 100x140 yap".

3. Aks vermeden oda: "O2'yi büyüt", "O2'yi sağa büyüt" (Lokman, kart 28 Kasım 2026 06:00:14 UTC "Yarım pano, duvarı sorsun":
   "Oda yarım pano (62,75 cm) büyür. Birden çok duvar kayabiliyorsa bayiye düğmeyle sorulur: Hangi duvar? Sol / Sağ / Ön / Arka").
   Kayabilen duvar iç duvardır (dış duvar kaymaz; dış duvar komutu İE-39'un). Duvar sözü yazılıysa o duvar.

Komut İş Emri'ni değiştirir; planı Motor kurar (D-28). Kod çözemediğini sessizce değiştirmez, gerekçeyle döner (K21).

Çerçeve: aks `cm` değerleri ve İş Emri'nin `konum_cm`'si arka-sol çerçevede (y arkadan; aks 1 arka duvar).
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

_ODA = re.compile(r"\bO\s?(\d{1,2})\b", re.I)
_PENCERE = re.compile(r"\bP\s?(\d{1,2})\b", re.I)
_AKS_HARF = re.compile(r"\b([A-Z]{1,2})\s*aks", re.I)
_AKS_RAKAM = re.compile(r"\b(\d{1,2})\s*(?:\.|nolu|numaral[ıi])?\s*aks", re.I)
_BUYUT = re.compile(r"b[üu]y[üu]t|geni[şs]let|uzat", re.I)
_KUCULT = re.compile(r"k[üu][çc][üu]lt|daralt|k[ıi]salt", re.I)
_OLCU = re.compile(r"\b(\d{2,3})\s*[x×*/]\s*(\d{2,3})\b")
_OLUMSUZ = re.compile(r"\b\w+(ma|me)(y[ıi]n|s[ıi]n|d[ıi]k)\b|istemiyor|olmas[ıi]n", re.I)
_DUVAR = {"sol": re.compile(r"\bsol", re.I), "sag": re.compile(r"\bsa[ğg]", re.I),
          "on": re.compile(r"\b[öo]n(e|[üu]|de|den)?\b", re.I), "arka": re.compile(r"\barka", re.I)}
DUVAR_ADI = {"sol": "Sol", "sag": "Sağ", "on": "Ön", "arka": "Arka"}
YARIM_PANO = 62.75
_SORU = re.compile(r"\bm[ıiuü](?:s[ıi]n[ıi]z)?\?|\?$")


class KomutDurdu(Exception):
    def __init__(self, neden: str):
        super().__init__(neden)
        self.neden = neden


@dataclass
class Komut:
    tur: str                           # "oda_aksa" | "oda_yonsuz" | "pencere_olcu"
    etiket: str
    aks: dict | None = None            # {"ad", "cm", "eksen": "x" | "y"}
    yon: str | None = None             # "buyut" | "kucult"
    olcu: str | None = None
    cumle: str = ""
    notlar: list[str] = field(default_factory=list)


def _cumleler(metin: str) -> list[str]:
    return [c.strip() for c in re.split(r"[.\n;]+|,\s*(?=[OPK]\s?\d)", metin or "") if c.strip()]


def oku(metin: str, et: dict) -> tuple[list[Komut], list[str]]:
    """Bayinin mesajı → (komutlar, sorular). Etiketi olmayan cümle komut değildir (bugünkü yol okur)."""
    komutlar, sorular = [], []
    odalar = {o["etiket"].upper(): o for o in et["odalar"]}
    pencereler = {a["etiket"].upper(): a for a in et["acikliklar"] if a["etiket"].startswith("P")}
    aks_x = {a["ad"].upper(): a for a in et["aks_x"]}
    aks_y = {a["ad"]: a for a in et["aks_y"]}
    for c in _cumleler(metin):
        if _OLUMSUZ.search(c) or _SORU.search(c):
            if _ODA.search(c) or _PENCERE.search(c):
                sorular.append(f"\"{c}\" cümlesini komut olarak okuyamadım (olumsuz ya da soru); ne yapalım?")
            continue
        mo, mp = _ODA.search(c), _PENCERE.search(c)
        if mp and _OLCU.search(c) and not mo:
            et_ = f"P{int(mp.group(1))}"
            if et_ not in pencereler:
                sorular.append(f"Planda {et_} yok; hangi pencere?")
                continue
            m = _OLCU.search(c)
            komutlar.append(Komut("pencere_olcu", et_, olcu=f"{int(m.group(1))}x{int(m.group(2))}", cumle=c))
            continue
        if not mo:
            continue
        et_ = f"O{int(mo.group(1))}"
        if et_ not in odalar:
            sorular.append(f"Planda {et_} yok; hangi oda?")
            continue
        yon = "buyut" if _BUYUT.search(c) else "kucult" if _KUCULT.search(c) else None
        ah = [a for a in _AKS_HARF.findall(c) if a.upper() in aks_x]
        ar = [a for a in _AKS_RAKAM.findall(c) if a in aks_y]
        akslar = [dict(aks_x[a.upper()], eksen="x") for a in ah] + [dict(aks_y[a], eksen="y") for a in ar]
        if yon is None:
            sorular.append(f"{et_} için ne yapalım: büyütelim mi, küçültelim mi?")
            continue
        if len(akslar) > 1:
            sorular.append(f"{et_} için iki aks yazdınız; önce hangisi? Her aks için ayrı cümle yazın.")
            continue
        if not akslar:
            duvarlar = [d for d, r in _DUVAR.items() if r.search(c)]
            komutlar.append(Komut("oda_yonsuz", et_, yon=yon, cumle=c, notlar=duvarlar))
            continue
        komutlar.append(Komut("oda_aksa", et_, aks=akslar[0], yon=yon, cumle=c))
    return komutlar, sorular


def _mahal_kutulari(ie: dict, ad: str) -> list[list[float]]:
    return next(m["konum_cm"] for m in ie["mahaller"] if m["ad"] == ad)


def _alan(rects) -> float:
    from shapely.geometry import box
    from shapely.ops import unary_union
    return unary_union([box(*r) for r in rects if r[2] > r[0] and r[3] > r[1]]).area / 1e4 if rects else 0.0


def _kutular(poly) -> list[list[float]]:
    from beyin.gorsel_okuma import _dikdortgenlere
    parcalar = getattr(poly, "geoms", [poly])
    return [list(map(lambda v: round(float(v), 2), r)) for pg in parcalar if pg.area > 1 for r in _dikdortgenlere(pg)]


def _tr(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def sinir_tasi(ie0: dict, ad: str, eksen: str, eski: float, hedef: float, adi: str) -> tuple[dict, list[tuple[str, float, float]]]:
    """Odanın `eski` koordinattaki duvarını (yalnız odanın boyunca) `hedef`e taşır. Büyürken aradaki şerit komşulardan alınır;
    küçülürken şerit o duvara değen komşuya verilir (birden çok komşu varsa her biri kendi boyunca alır). Dönüş: (İş Emri, değişenler)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    ie = copy.deepcopy(ie0)
    W, H = float(ie["yapi"]["dis_olcu_cm"]["x"]) + 50, float(ie["yapi"]["dis_olcu_cm"]["y"]) + 50
    poly = {m["ad"]: unary_union([box(*r) for r in m["konum_cm"]]) for m in ie["mahaller"]}
    oda = poly[ad]
    a, b = sorted((eski, hedef))
    bant = box(a, -50, b, H) if eksen == "x" else box(-50, a, W, b)
    # odanın o duvar boyunca uzandığı aralık: duvar çizgisinin odaya değen parçası
    cizgi = box(eski - 0.5, -50, eski + 0.5, H) if eksen == "x" else box(-50, eski - 0.5, W, eski + 0.5)
    temas = oda.intersection(cizgi).bounds
    if not temas or oda.intersection(cizgi).area <= 0:
        raise KomutDurdu(f"{ad} duvarı bulunamadı.")
    aralik = (temas[1], temas[3]) if eksen == "x" else (temas[0], temas[2])
    serit = bant.intersection(box(a, aralik[0], b, aralik[1]) if eksen == "x" else box(aralik[0], a, aralik[1], b))
    once = {k: v.area / 1e4 for k, v in poly.items()}
    buyur = oda.intersection(serit).area < serit.area / 2
    if buyur:
        poly[ad] = unary_union([oda, serit])
        for k in poly:
            if k != ad:
                poly[k] = poly[k].difference(serit)
    else:
        verilecek = oda.intersection(serit)
        poly[ad] = oda.difference(serit)
        kalan = verilecek
        for k, v in poly.items():
            if k == ad:
                continue
            komsu_cizgi = v.intersection(cizgi.buffer(1.0))
            if komsu_cizgi.area <= 0:
                continue
            kb = komsu_cizgi.bounds
            parca = verilecek.intersection(box(a, kb[1], b, kb[3]) if eksen == "x" else box(kb[0], a, kb[2], b))
            if parca.area > 1:
                poly[k] = unary_union([v, parca])
                kalan = kalan.difference(parca)
        if kalan.area > 100:
            raise KomutDurdu(f"{ad} küçülünce boşalan yerin hangi bölüme katılacağını bulamadım.")
    degisen = []
    for m in ie["mahaller"]:
        p = poly[m["ad"]]
        if p.area < 1e3:
            raise KomutDurdu(f"{adi}: {m['ad']} kayboluyor; başka bir aks yazın.")
        if abs(p.area / 1e4 - once[m["ad"]]) > 0.01:
            m["konum_cm"] = _kutular(p)
            degisen.append((m["ad"], once[m["ad"]], p.area / 1e4))
    return ie, degisen


def oda_aksa(ie: dict, et: dict, k: Komut, H: float | None = None) -> tuple[dict, str]:
    """Odanın aksa en yakın duvarını aksa taşır (aks `cm` İş Emri çerçevesinde)."""
    ad = next(o for o in et["odalar"] if o["etiket"] == k.etiket)["ad"]
    kutular = _mahal_kutulari(ie, ad)
    hedef = float(k.aks["cm"])
    i0, i1 = (0, 2) if k.aks["eksen"] == "x" else (1, 3)
    lo, hi = min(r[i0] for r in kutular), max(r[i1] for r in kutular)
    if k.yon == "buyut":
        if hedef < lo - 0.01:
            eski = lo
        elif hedef > hi + 0.01:
            eski = hi
        else:
            raise KomutDurdu(f"{k.aks['ad']} aksı {k.etiket}'in ({ad}) içinden geçiyor; büyütmek için odanın dışındaki bir aks yazın.")
    else:
        if not lo + 0.01 < hedef < hi - 0.01:
            raise KomutDurdu(f"{k.aks['ad']} aksı {k.etiket}'in ({ad}) dışında; küçültmek için odanın içinden geçen bir aks yazın.")
        eski = lo if hedef - lo < hi - hedef else hi
    yeni, degisen = sinir_tasi(ie, ad, k.aks["eksen"], eski, hedef, f"{k.etiket}'i {k.aks['ad']} aksına taşıyınca")
    return yeni, f"{k.etiket} ({ad}) duvarı {k.aks['ad']} aksına taşındı", [a for a, _, _ in degisen]


def kayabilen_duvarlar(ie: dict, ad: str, yon: str = "") -> dict[str, float]:
    """Odanın başka bir bölüme değen (iç) duvarları: {sol|sag|arka|on: koordinat} (arka-sol çerçeve). Bir yönde birden çok
    iç duvar varsa en uzun ortak kenarlı olan. Dış duvar bu komutla kaymaz (dış duvar yarım pano komutu ayrıdır)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    poly = {m["ad"]: unary_union([box(*r) for r in m["konum_cm"]]) for m in ie["mahaller"]}
    oda = poly[ad]
    uzun: dict[str, tuple[float, float]] = {}
    for k, v in poly.items():
        if k == ad:
            continue
        from shapely.geometry import LineString
        kenarlar = []
        for halka in [pg.exterior for pg in getattr(oda, "geoms", [oda])]:
            cs = list(halka.coords)
            for p0, p1 in zip(cs, cs[1:]):
                o = LineString([p0, p1]).intersection(v.buffer(0.6))
                kenarlar += [x for x in getattr(o, "geoms", [o]) if x.geom_type == "LineString"]
        for g in kenarlar:
            if g.is_empty or g.length < 20:
                continue
            x0, y0, x1, y1 = g.bounds
            if x1 - x0 < 1:                       # dikey kenar
                x, cy = (x0 + x1) / 2, (y0 + y1) / 2
                d = "sag" if oda.contains(box(x - 2, cy - 0.5, x - 1, cy + 0.5)) else "sol"
                c, L = x, y1 - y0
            elif y1 - y0 < 1:
                y, cx = (y0 + y1) / 2, (x0 + x1) / 2
                d = "on" if oda.contains(box(cx - 0.5, y - 2, cx + 0.5, y - 1)) else "arka"
                c, L = y, x1 - x0
            else:
                continue
            if d not in uzun or L > uzun[d][1]:
                uzun[d] = (round(c, 2), L)
    return {d: uzun[d][0] for d in ("sol", "sag", "arka", "on") if d in uzun}


def oda_yonsuz(ie: dict, et: dict, k: Komut) -> tuple[dict, str]:
    oda = next(o for o in et["odalar"] if o["etiket"] == k.etiket)
    ad = oda["ad"]
    kayan = kayabilen_duvarlar(ie, ad)
    secilen = [d for d in k.notlar if d in kayan]
    if k.notlar and not secilen:
        raise KomutDurdu(f"{k.etiket} ({ad}) için {', '.join(DUVAR_ADI[d].lower() for d in k.notlar)} duvar dış duvar; dış duvar bu "
                         "komutla kaymıyor. Hangi duvar?" + _secenek(kayan))
    if len(secilen) > 1 or (not secilen and len(kayan) != 1):
        if not kayan:
            raise KomutDurdu(f"{k.etiket} ({ad}) dört yandan dış duvara değiyor; iç duvarı yok.")
        raise KomutDurdu(f"{k.etiket} ({ad}) hangi duvardan {'büyüsün' if k.yon == 'buyut' else 'küçülsün'}?" + _secenek(kayan))
    d = (secilen or kayan)[0]
    eksen = "x" if d in ("sol", "sag") else "y"
    v = kayan[d]
    disa = -1 if d in ("sol", "arka") else 1
    hedef = v + disa * YARIM_PANO * (1 if k.yon == "buyut" else -1)
    ie2, degisen = sinir_tasi(ie, ad, eksen, v, hedef, f"{k.etiket}'i yarım pano {'büyütünce' if k.yon == 'buyut' else 'küçültünce'}")
    return ie2, f"{k.etiket} ({ad}) {DUVAR_ADI[d].lower()} duvarı yarım pano {'büyüdü' if k.yon == 'buyut' else 'küçüldü'}", \
        [a for a, _, _ in degisen]


def _secenek(kayan: list[str]) -> str:
    return " [" + " / ".join(DUVAR_ADI[d] for d in kayan) + "]" if kayan else ""


def pencere_olcu(ie0: dict, et: dict, k: Komut) -> tuple[dict, str]:
    ie = copy.deepcopy(ie0)
    p = next(a for a in et["acikliklar"] if a["etiket"] == k.etiket)
    sira = [a for a in et["acikliklar"] if a["tur"] == "pencere" and a["mahal"] == p["mahal"]].index(p)
    adaylar = [a for a in ie["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == p["mahal"]]
    if len(adaylar) <= sira:
        raise KomutDurdu(f"{k.etiket} İş Emri'nde bulunamadı.")
    a = adaylar[sira] if len(adaylar) == len([x for x in et["acikliklar"] if x["tur"] == "pencere" and x["mahal"] == p["mahal"]]) \
        else next((x for x in adaylar if x["olcu"] == p["olcu"]), None)
    if a is None:
        raise KomutDurdu(f"{k.etiket}'in hangi pencere olduğunu bulamadım.")
    eski = a["olcu"]
    a["olcu"] = k.olcu
    a.pop("bolmeler", None)
    return ie, f"{k.etiket} ({p['mahal']} penceresi) {eski} → {k.olcu}", []


def _motor_m2(ie: dict) -> dict:
    from motor import geometry as G
    return {m.ad: round(m.alan_m2, 2) for m in G.kur(copy.deepcopy(ie)).mahaller.values()}


def _motor_nedeni(e: Exception) -> str:
    import re
    t = str(e)
    m = re.search(r"Açıklık için uygun pano yok.*?'arasi': \[([^\]]*)\]", t)
    if m:
        return " ile ".join(x.strip(" '") for x in m.group(1).split(",")) + " arasındaki kapıya yer kalmıyor"
    if "Açıklık için uygun pano yok" in t:
        return "bir pencere ya da kapıya yer kalmıyor"
    return t[:120]


def uygula(ie: dict, et: dict, komutlar: list[Komut], H: float | None = None) -> tuple[dict, list[str], list[str]]:
    """Komutları sırayla uygular; her birinden sonra Motor kurar. Dönüş: (İş Emri, "Anladığım" satırları, uygulanamayanlar)."""
    from motor import geometry as G
    anladim, olmayan = [], []
    m2 = _motor_m2(ie)
    for k in komutlar:
        try:
            if k.tur == "oda_aksa":
                yeni, metin, adlar = oda_aksa(ie, et, k)
            elif k.tur == "pencere_olcu":
                yeni, metin, adlar = pencere_olcu(ie, et, k)
            else:
                yeni, metin, adlar = oda_yonsuz(ie, et, k)
            try:
                m2_yeni = _motor_m2(yeni)
            except Exception as e:  # noqa: BLE001
                raise KomutDurdu(f"\"{k.cumle}\": plan bu değişiklikle kurulamadı ({_motor_nedeni(e)}).")
            if adlar:
                metin += ": " + ", ".join(f"{a} {_tr(m2[a])} → {_tr(m2_yeni[a])} m²" for a in adlar if a in m2 and a in m2_yeni)
            ie, m2 = yeni, m2_yeni
            anladim.append(metin)
        except KomutDurdu as d:
            olmayan.append(d.neden)
    return ie, anladim, olmayan
