#!/usr/bin/env python3
"""Çatı karkas kuralı (İE-16 PR-3b): makas dizilimi ve makasın üyeleri; çatı paneli, tavan paneli ve çatı üstü panel.

Yalnız tanım karkas kuralını isterse çalışır (`"karkas": "kural"`; `karkas.kur` çağırır); istemeyen tanımın çıktısı bayt bayt aynıdır.
Sayısal ayarlar `kurallar/karkas/celik_karkas.json`'da (`makas`, `makas_uyeleri`, `cati_paneli`, `tavan_paneli`), her biri durumu ve
kaynağıyla. Tanımdaki `cati.makaslar` (paftadan okunmuş makas yerleri) bu kuralda okunmaz: kör projede o bilgi yoktur.

1. **Aile.** Bir mahya ve iki düzlemi beşik ailedir; aileye girmeyen ve duvar dibine dayanan düzlem tek eğimli ailedir. Aileye girmeyen
   öteki makaslı düzlem kırma yüzüdür: tepe köşesi bir mahyanın ucundaysa o ailenin o ucuna bağlanır. Ana aile en büyük düzlemi
   taşıyandır. Kanat: ana aileye dik, mahyası ana ailenin saçak bandının dışına taşan beşik aile (güneydeki kanat, cumba, çıkma).
2. **Konum.** Makas mahyaya diktir; konumlar mahya boyunca iki uç arasında eşit aralıklı (en çok `aralik_cm`), değer makasın ortası.
   Beşik ailenin ucu: alın → kalkan duvarının iç yüzü; kırma → kırma yüzünün saçağı altındaki duvarın iç yüzü, o konum düşer (ana
   makaslar kırma bölgesinden, üstleri kırma yüzüyle kırpılarak geçer); birleşim → aynı eksenli komşu aile o yöndeyse mahyanın ucu,
   değilse ailenin düzlemlerinin o yöndeki ucu (orada duvar varsa iç yüzü). Kanadın ana çatıya bakan ucu ana ailenin saçağında biter.
   Tek eğimli ailenin ucu: düzlem orada tam derinlikteyse duvarın iç yüzü; değilse (kırma ya da vadi) tam derinliğin bittiği yer.
3. **Makas çizgisi.** Konumda makas yönünde: ailenin iki düzlemi (her biri mahyanın kendi yanında) ve kırma yüzleri içinde, mahyayı
   içeren bitişik parça. Ucunda tek eğimli bir düzlem ya da (ana ailede) kanadın düzlemi sürüyorsa, vadiyi geçip ailenin o yandaki
   saçak hizasına kadar uzanır. Üstü çatı yüzeyi, altı duvar üstü (`duvar_ustu`). Konumda mahyayı içeren parça yoksa (çizgi
   mahyaya varmıyor) en uzun parça alınır ve makas kısa sayılır. `en_kisa_cm`'den kısa çizgi makas olmaz, uyarı yazılır.
4. **Kısa makas ve çapraz.** Kırma ucunun şeridinde (uç duvardan ilk makasa) kırma yüzünün yönünde, tek eğimli düzlemin kırma
   üçgeninde ailenin yönünde; aralık yine en çok `aralik_cm`, uçlardaki konum düşer (köşede çapraz var). Her kırma çizgisinde (kırma
   yüzüyle ailesi ya da tek eğimli düzlemle komşusu arasında) bir çapraz makas.
5. **Üyeler.** Alt başlık (açıklık), üst başlık (çatı yüzeyi boyunca) ve örgü: açıklık en çok `panel_cm` boyunda eşit panellere
   bölünür; iç düğümlerde dikme (düğümdeki yükseklik), her panelde bir çapraz (panel boyu ve panelin ortalama yüksekliğiyle). Biçim ve
   `panel_cm`, KT-01'in (= ÇP-13) karkas modelindeki 16 makastan; biri dışarıda bırakılarak seçildi (`makas_uyeleri`).
6. **Paneller.** Çatı paneli (tanımda `ust_yapi: cati_paneli` düzlemler), yöntem A'nın çatı üstü paneli ve tavan paneli duvar
   paneli kuralıyla kurulur (`karkas.uyeler`; panelin uzun kenarı başlık, dikmeler `dikme_araligi_cm` arayla kısa kenar boyunca).
   Çatı paneli düzlemin açılımında saçak boyunca `cati_paneli_adedi` eşit panele bölünür; çatı üstü paneli saçak boyunca `bolme`
   hedefiyle; tavan paneli ana ailenin makas aralıklarında, mahallerin içinde (makas kalınlığından dar şerit ve parça panel olmaz).
   PR-3c (Lokman, 27 Ekim 2026; yeni anahtarlar, eski kural kopyasında eski davranış): çatı paneli ve çatı üstü panelinde çapraz yok;
   adedi tanımda yazmayan açık alan çatı paneli saçak boyunca `cati_paneli.en_cm_acik_alan` (180); çatı üstü paneli eğim boyunca en çok `ust_paneli.en_cm`, saçak
   boyunca en çok beş makas aralığı, eşit bölünür (`ust_paneli`); tavan panelinin uzun kenarı en çok `tavan_paneli.en_uzun_cm` (tırın 13,60 m'si); tek
   açıklığı `makas_eti.tek_aciklik_en_cok_cm`'yi (8 m) aşan makas kalın sacdan (`makas_eti`, `tek_aciklik`).
7. **Uyarılar.** Kuralın yedeğe düştüğü ya da bir şey koymadığı her yer `uyarilar`a yazılır (aileye bağlanmayan kırma yüzü, ailesiz
   çatı, ucunda duvar bulunamayan aile (ana saçağın ezdiği uç hariç: sonucu değiştirmez), saçağı bulunamayan kırma ucu, tek parça
   kesilmeyen kırma şeridi, kısa çizgi, kurulamayan tavan paneli, tavan panelinin ve çatı üstü panelinin küçük ve dar parçaları); girdi bunları "karkas kuralı:
   …" uyarısı olarak taşır (kurulamayan yöntem A panelinin satırı kitabın oranıyla), makas paftası basar.

Hesapta LLM yoktur: aynı tanım ve aynı kural aynı sonucu verir. Ölçüler cm; boylar m.
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import math

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import cati_genel

EPS = 0.5          # cm; düzlem sınırı ve nokta eşitliği toleransı
ADIM = 2.0         # cm; makasın üst çizgisi bu aralıkla örneklenir


def _d(k: dict, anahtar: str):
    return k[anahtar]["deger"]


def _esit(p, q, tol: float = 1.0) -> bool:
    return math.hypot(p[0] - q[0], p[1] - q[1]) < tol


def _eksen(dz: dict) -> str:
    """Düzlemin eğim yönü: makas bu eksen boyunca uzanır."""
    yx, yy = dz["yukari"]
    return "x" if abs(yx) > abs(yy) else "y"


def _i(e: str) -> int:
    return 0 if e == "x" else 1


def _oteki(e: str) -> str:
    return "y" if e == "x" else "x"


def _sacak(dz: dict, ex: str):
    return dz["sacak"].get(ex)


# ──────────────────────────────────────────────────────────────── aileler ──
def aileler(c: dict) -> tuple[dict, list[dict], list[dict], list[str]]:
    """(makaslı düzlemler adla, kenarlar, aileler, kırma yüzü olup bir aileye bağlanmayan düzlemler)."""
    dzs = [d for d in c["duzlemler"] if d.get("ust_yapi") != "cati_paneli"]
    if not dzs:                                   # bütün düzlemler çatı paneli: makaslı düzlem yok
        return {}, [], [], []
    adli = {d["ad"]: d for d in dzs}
    kn = [e for e in c["kenarlar"] if all(a in adli for a in e["duzlemler"])]
    aile: list[dict] = []
    mahyalar: dict[tuple, list[dict]] = {}        # aynı iki düzlemin mahya kenarları (ilk görülme sırasıyla)
    for e in kn:
        if e["tur"] == "mahya":
            mahyalar.setdefault(tuple(sorted(e["duzlemler"])), []).append(e)
    for es in mahyalar.values():
        a, b = es[0]["duzlemler"]
        ex = _eksen(adli[a])
        ie = _i(_oteki(ex))
        parca = sorted((tuple(sorted((tuple(e["p"]), tuple(e["q"])), key=lambda v: v[ie])) for e in es), key=lambda pq: pq[0][ie])
        uclar = [list(parca[0])]
        for p, q in parca[1:]:                    # uç uca kenarlar tek mahya (çokgende mahyanın üstünde fazladan köşe)
            if _esit(p, uclar[-1][1]):
                uclar[-1][1] = q
            else:
                uclar.append([p, q])
        for p, q in uclar:
            aile.append({"tur": "besik", "duzlemler": [a, b], "uc": (p, q), "eksen": ex})
    kolda = {x for k in aile for x in k["duzlemler"]}
    dibi = {e["duzlemler"][0] for e in kn if e["tur"] == "duvar_dibi"}
    for a in adli:
        if a not in kolda and a in dibi:
            aile.append({"tur": "tek", "duzlemler": [a], "eksen": _eksen(adli[a])})
    kolda = {x for k in aile for x in k["duzlemler"]}
    serbest = [a for a in adli if a not in kolda]
    for k in aile:
        k["kirma_yuzu"] = {}
        if k["tur"] == "besik":
            for i, u in enumerate(k["uc"]):
                for a in serbest:
                    if _eksen(adli[a]) != k["eksen"] and any(_esit(u, v) for v in adli[a]["plan"]):
                        k["kirma_yuzu"][i] = a
        k["takim"] = k["duzlemler"] + [k["kirma_yuzu"][i] for i in sorted(k["kirma_yuzu"])]
    buyuk = max(dzs, key=lambda d: d["cokgen"].area)["ad"]
    for k in aile:
        k["ana"] = buyuk in k["duzlemler"]
        k["kanatlari"], k["sinir"] = [], {}
    for a in aile:
        if not a["ana"] or a["tur"] != "besik":
            continue
        i = _i(a["eksen"])
        sac = [_sacak(adli[n], a["eksen"]) for n in a["duzlemler"]]
        if None in sac:
            continue
        lo, hi = min(sac), max(sac)
        for k in aile:
            if k["ana"] or k["tur"] != "besik" or k["eksen"] == a["eksen"]:
                continue
            us = [u[i] for u in k["uc"]]
            if min(us) < lo - 1 or max(us) > hi + 1:
                a["kanatlari"].append(k)
                if min(us) < lo - 1:
                    k["sinir"][+1] = min(k["sinir"].get(+1, math.inf), lo)
                else:
                    k["sinir"][-1] = max(k["sinir"].get(-1, -math.inf), hi)
    bagli = {x for k in aile for x in k["kirma_yuzu"].values()}
    return adli, kn, aile, [a for a in serbest if a not in bagli]


# ──────────────────────────────────────────────────────────────── konumlar ──
def _duvar(y: dict, cizgi: float, ee: str, ex: str, bant: tuple[float, float], en_cok: float):
    """`cizgi` konumundaki (ee ekseninde) uç çizgisine paralel, ona en çok `en_cok` uzak, ex'te `bant` ile örtüşen en yakın duvar:
    ee eksenindeki (baş, son) ya da None."""
    en_iyi = None
    for w in y["duvarlar"]:
        if w["sinif"] not in ("dis", "ic", "ek"):
            continue
        x0, y0, x1, y1 = w["kutu"]
        e0, e1 = (x0, x1) if ee == "x" else (y0, y1)
        d0, d1 = (x0, x1) if ex == "x" else (y0, y1)
        if (e1 - e0) > (d1 - d0) or min(d1, bant[1]) - max(d0, bant[0]) < 10:
            continue
        uzak = abs((e0 + e1) / 2 - cizgi)
        if uzak <= en_cok and (en_iyi is None or uzak < en_iyi[0]):
            en_iyi = (uzak, (e0, e1))
    return None if en_iyi is None else en_iyi[1]


def _ic_yuz(w, isaret: int, yedek: float) -> float:
    """Duvarın ailenin içine bakan yüzü (`isaret`: ucun dışarı yönü); duvar yoksa yedek."""
    if w is None:
        return yedek
    return w[1] if isaret < 0 else w[0]


def _esit_bol(a0: float, a1: float, dus0: bool, dus1: bool, S: float) -> list[float]:
    L = a1 - a0
    n = max(1, math.ceil(L / S - 1e-9))
    ks = [a0 + L * i / n for i in range(n + 1)]
    return ks[1 if dus0 else 0: len(ks) - (1 if dus1 else 0)]


def _besik_konumlar(y: dict, adli: dict, kn: list[dict], aile: list[dict], k: dict, sacak: float, S: float, kal: float,
                    uyari: list[str]):
    ex = k["eksen"]; ee = _oteki(ex)
    ie = _i(ee)
    bb = unary_union([adli[a]["cokgen"] for a in k["takim"]]).bounds
    bant = (bb[_i(ex)], bb[_i(ex) + 2])
    uclar = []
    duvarsiz = {}                                                     # ucunda duvar bulunamayan uçlar: {i: (neden, yedek)}
    for i, (u, isaret) in enumerate(((k["uc"][0], -1), (k["uc"][1], +1))):    # isaret: ucun dışarı yönü (ee ekseninde)
        turler = {e["tur"] for e in kn if (_esit(e["p"], u) or _esit(e["q"], u)) and any(a in k["duzlemler"] for a in e["duzlemler"])}
        if i in k["kirma_yuzu"]:
            H = k["kirma_yuzu"][i]
            sac = [e for e in kn if e["tur"] == "sacak" and e["duzlemler"] == [H] and abs(e["p"][ie] - e["q"][ie]) < 1]
            if sac:
                uc = max(sac, key=lambda e: e["plan_boy"])["p"][ie]
            else:
                uc = u[ie] + isaret * 10 * sacak
                uyari.append(f"makas: {'/'.join(k['duzlemler'])} ailesinin {H} kırma yüzünde saçak bulunamadı; uç mahyanın ucundan 10 × saçak")
            w = _duvar(y, uc, ee, ex, bant, sacak + 15)
            if w is None:
                duvarsiz[i] = ("kırma", "saçak − saçak payı")
            uclar.append((_ic_yuz(w, isaret, uc - isaret * sacak), True, "kırma"))
        elif "alin" in turler:
            w = _duvar(y, u[ie], ee, ex, bant, sacak + 15)
            if w is None:
                duvarsiz[i] = ("alın", "mahyanın ucu")
            uclar.append((_ic_yuz(w, isaret, u[ie]), False, "alın"))
        elif any(o is not k and o["tur"] == "besik" and o["eksen"] == ex and set(o["takim"]) & set(k["takim"])
                 and any((v[ie] - u[ie]) * isaret > 1 for v in o["uc"]) for o in aile):
            uclar.append((u[ie], False, "birleşim"))
        else:
            ks = [p[ie] for a in k["takim"] for p in adli[a]["plan"]]
            uc = min(ks) if isaret < 0 else max(ks)
            w = _duvar(y, uc, ee, ex, bant, sacak + 15)
            if w is None:
                duvarsiz[i] = ("uzanım", "düzlemlerin ucu")
            uclar.append((_ic_yuz(w, isaret, uc), False, "uzanım"))
    (a0, d0, n0), (a1, d1, n1) = uclar
    if -1 in k["sinir"] and k["sinir"][-1] + kal / 2 > a0:            # kanadın ana çatıya bakan ucu: makas ana saçağın hemen dışında
        a0, d0, n0 = k["sinir"][-1] + kal / 2, False, "ana saçak"
        duvarsiz.pop(0, None)
    if +1 in k["sinir"] and k["sinir"][+1] - kal / 2 < a1:
        a1, d1, n1 = k["sinir"][+1] - kal / 2, False, "ana saçak"
        duvarsiz.pop(1, None)
    ad = "/".join(k["duzlemler"])
    for i, (neden, yedek) in sorted(duvarsiz.items()):                # ana saçağın ezdiği uç sonucu değiştirmez, yazılmaz
        uyari.append(f"makas: {ad} ailesinin {neden} ucunda duvar bulunamadı; uç {(a0, a1)[i]:.1f} ({yedek})")
    if a1 - a0 <= EPS:                                                # ana saçağa kırpılan kanat uçları geçti: dizilim yok
        uyari.append(f"makas: {ad} ailesinin uçları {a0:.1f} ve {a1:.1f}: ters ya da çakışık, tam makas yok")
        return [], (n0, n1), (a0, a1)
    ks = _esit_bol(a0, a1, d0, d1, S)
    if not ks:
        uyari.append(f"makas: {ad} ailesinde iki uç arası {a1 - a0:.1f} cm (iki ucu da düşen konum, aralık en çok {S:g}): tam makas yok")
    return ks, (n0, n1), (a0, a1)


def _tek_konumlar(y: dict, adli: dict, kn: list[dict], k: dict, sacak: float, S: float, kal: float, uyari: list[str]):
    """Tek eğimli düzlem: konumlar ve kırma üçgenleri [(son tam makas, saçak köşesi)]."""
    dz = adli[k["duzlemler"][0]]
    ex = k["eksen"]; ee = _oteki(ex)
    ie, ix = _i(ee), _i(ex)
    pol = dz["cokgen"]
    bb = pol.bounds
    saclar = [e for e in kn if e["tur"] == "sacak" and e["duzlemler"] == [dz["ad"]]]
    if not saclar:
        uyari.append(f"makas: {dz['ad']} ailesinin (tek eğimli) saçağı yok: makas yok")
        return [], ("saçak yok", "saçak yok"), []
    sac = max(saclar, key=lambda e: e["plan_boy"])
    derinlik = bb[ix + 2] - bb[ix]

    def derin(e):
        ln = LineString([(e, bb[1] - 1), (e, bb[3] + 1)]) if ee == "x" else LineString([(bb[0] - 1, e), (bb[2] + 1, e)])
        return ln.intersection(pol).length

    def tam_sinir(c, yon):
        """Saçak köşesinden (c) içeri doğru, derinliğin tam olduğu ilk konum (0,5 cm duyarlıkla)."""
        lo, hi = 0.0, abs(sac["p"][ie] - sac["q"][ie])
        if derin(c - yon * 0.25) >= derinlik - 1.0:
            return c
        for _ in range(40):
            orta = (lo + hi) / 2
            if derin(c - yon * orta) >= derinlik - 1.0:
                hi = orta
            else:
                lo = orta
        return c - yon * hi
    c0, c1 = sorted([sac["p"][ie], sac["q"][ie]])
    uclar, ucgen = [], []
    for c, yon in ((c0, -1), (c1, +1)):
        kose = (c, sac["p"][ix]) if ee == "x" else (sac["p"][ix], c)
        turler = {e["tur"] for e in kn if (_esit(e["p"], kose) or _esit(e["q"], kose)) and dz["ad"] in e["duzlemler"]} - {"sacak"}
        if not turler & {"kirma", "vadi"}:
            w = _duvar(y, c, ee, ex, (bb[ix], bb[ix + 2]), sacak + 15)
            if w is None:
                uyari.append(f"makas: {dz['ad']} ailesinin alın ucunda duvar bulunamadı; uç {c - yon * sacak:.1f} (saçak − saçak payı)")
            uclar.append((_ic_yuz(w, yon, c - yon * sacak), "alın"))
            continue
        b = tam_sinir(c, yon) - yon * kal / 2
        uclar.append((b, "kırma" if "kirma" in turler else "vadi"))
        if "kirma" in turler:
            ucgen.append((b, c))
    (a0, n0), (a1, n1) = uclar
    return _esit_bol(a0, a1, False, False, S), (n0, n1), ucgen


# ──────────────────────────────────────────────────────────────── çizgiler ──
def _araliklar(dz: dict, ex: str, a: float, bb) -> list[tuple[float, float]]:
    """`a` konumunda ex yönündeki doğrunun düzlemin içinde kalan aralıkları (ex ekseninde)."""
    i = _i(ex)
    ln = LineString([(bb[0] - 10, a), (bb[2] + 10, a)]) if ex == "x" else LineString([(a, bb[1] - 10), (a, bb[3] + 10)])
    kes = ln.intersection(dz["cokgen"].buffer(EPS))
    parcalar = [kes] if kes.geom_type == "LineString" else [g for g in getattr(kes, "geoms", []) if g.geom_type == "LineString"]
    out = []
    for g in parcalar:
        if g.is_empty:
            continue
        cs = [p[i] for p in g.coords]
        out.append((min(cs), max(cs)))
    return sorted(out)


def _icinde(ar: list[tuple[float, float]], s: float) -> bool:
    return any(lo - 1e-9 <= s <= hi + 1e-9 for lo, hi in ar)


def _profil(adli: dict, ex: str, a: float, s0: float, s1: float, kapsam: dict[str, list]) -> dict:
    """[s0, s1] boyunca üst çizgi: her noktada kapsayan düzlemlerin en yükseği. Dönen: noktalar, yükseklikler, boylar."""
    n = max(2, int(math.ceil((s1 - s0) / ADIM)) + 1)
    ss = [s0 + (s1 - s0) * j / (n - 1) for j in range(n)]
    zz = []
    for s in ss:
        p = (s, a) if ex == "x" else (a, s)
        kot = [adli[ad]["kot"](p) for ad, ar in kapsam.items() if _icinde(ar, s)]
        zz.append(max(kot) if kot else (zz[-1] if zz else None))
    if zz[0] is None:
        ilk = next(z for z in zz if z is not None)
        zz = [ilk if z is None else z for z in zz]
    return {"ss": ss, "zz": zz}


def _birlesik(ar: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for lo, hi in sorted(ar):
        if out and lo <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


def _besik_cizgi(adli: dict, k: dict, a: float, bb, uzanan: list[str]):
    ex = k["eksen"]; i = _i(ex)
    A, B = k["duzlemler"]
    m = k["uc"][0][i]
    kapsam = {}
    for n in k["takim"]:
        ar = _araliklar(adli[n], ex, a, bb)
        if n in (A, B):                                        # aile düzlemi mahyanın kendi yanında
            up = adli[n]["yukari"][i]
            ar = [(lo, min(hi, m)) if up > 0 else (max(lo, m), hi) for lo, hi in ar]
            ar = [(lo, hi) for lo, hi in ar if hi - lo > 1e-6]
        if ar:
            kapsam[n] = ar
    parcalar = _birlesik([x for ar in kapsam.values() for x in ar])
    if not parcalar:
        return None
    icinde = [p for p in parcalar if p[0] - EPS <= m <= p[1] + EPS]
    s0, s1 = icinde[0] if icinde else max(parcalar, key=lambda p: p[1] - p[0])
    # vadi üçgeni: uçta tek eğimli düzlem ya da kanat düzlemi sürüyorsa ailenin o yandaki saçağına kadar
    for n in (A, B):
        hedef = _sacak(adli[n], ex)
        if hedef is None:
            continue
        yon = -1 if adli[n]["yukari"][i] > 0 else +1
        uc = s0 if yon < 0 else s1
        if (hedef - uc) * yon <= EPS:
            continue
        ek = _birlesik([x for o in uzanan for x in _araliklar(adli[o], ex, a, bb)])
        for lo, hi in ek:
            if lo - EPS <= uc <= hi + EPS:
                yeni = max(lo, hedef) if yon < 0 else min(hi, hedef)
                for o in uzanan:
                    ar = [(max(x0, min(uc, yeni)), min(x1, max(uc, yeni))) for x0, x1 in _araliklar(adli[o], ex, a, bb)]
                    ar = [(x0, x1) for x0, x1 in ar if x1 - x0 > 1e-6]
                    if ar:
                        kapsam[o] = kapsam.get(o, []) + ar
                if yon < 0:
                    s0 = yeni
                else:
                    s1 = yeni
                break
    return {"s0": s0, "s1": s1, "mahyali": bool(icinde), **_profil(adli, ex, a, s0, s1, kapsam)}


def _tek_cizgi(adli: dict, ad: str, ex: str, a: float, bb, sinir: tuple[float, float] | None = None):
    ar = _araliklar(adli[ad], ex, a, bb)
    if sinir:
        ar = [(max(lo, sinir[0]), min(hi, sinir[1])) for lo, hi in ar]
        ar = [(lo, hi) for lo, hi in ar if hi - lo > 1e-6]
    if not ar:
        return None
    s0, s1 = max(ar, key=lambda p: p[1] - p[0])
    return {"s0": s0, "s1": s1, **_profil(adli, ex, a, s0, s1, {ad: [(s0, s1)]})}


# ──────────────────────────────────────────────────────────────── üyeler ──
def _yukseklik(ss: list[float], hh: list[float], s: float) -> float:
    if s <= ss[0]:
        return hh[0]
    if s >= ss[-1]:
        return hh[-1]
    j = min(int((s - ss[0]) / (ss[-1] - ss[0]) * (len(ss) - 1)), len(ss) - 2)
    while ss[j + 1] < s:
        j += 1
    while ss[j] > s:
        j -= 1
    t = (s - ss[j]) / (ss[j + 1] - ss[j]) if ss[j + 1] > ss[j] else 0.0
    return hh[j] + t * (hh[j + 1] - hh[j])


def uyeler(ss: list[float], zz: list[float], duvar_ustu: float, panel: float) -> dict[str, float]:
    """Makasın üyeleri, tür tür boy (m): alt başlık, üst başlık, dikmeler, çaprazlar."""
    hh = [z - duvar_ustu for z in zz]
    acik = ss[-1] - ss[0]
    n = max(1, math.ceil(acik / panel - 1e-9))
    pe = acik / n
    hk = [_yukseklik(ss, hh, ss[0] + pe * j) for j in range(n + 1)]
    ust = sum(math.hypot(ss[j + 1] - ss[j], zz[j + 1] - zz[j]) for j in range(len(ss) - 1))
    return {"alt_baslik": acik / 100, "ust_baslik": ust / 100, "dikme": sum(hk[1:-1]) / 100,
            "capraz": sum(math.hypot(pe, (hk[j] + hk[j + 1]) / 2) for j in range(n)) / 100}


def _kayit(tur: str, aile: str, ex: str, a: float, cz: dict, duvar_ustu: float, panel: float) -> dict:
    u = uyeler(cz["ss"], cz["zz"], duvar_ustu, panel)
    return {"tur": tur, "aile": aile, "eksen": ex, "konum": round(a, 2), "s": [round(cz["s0"], 2), round(cz["s1"], 2)],
            "acik_cm": round(cz["s1"] - cz["s0"], 2), "h_en_cok_cm": round(max(cz["zz"]) - duvar_ustu, 2),
            "uyeler_m": {ad: round(v, 4) for ad, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)}


def makaslar(t: dict, c: dict, y: dict, k: dict) -> dict:
    """Makaslar (tam, kısa, çapraz), ailelerin kaydı ve uyarılar. Beşik ailede çizgisi mahyaya varmayan makas kısa sayılır;
    `en_kisa_cm`'den kısa çizgide makas konmaz ve uyarı yazılır (sessiz düşme yok)."""
    mk = _d(k, "makas")
    S, kal, en_kisa = mk["aralik_cm"], mk["kalinlik_cm"], mk["en_kisa_cm"]
    panel = _d(k, "makas_uyeleri")["panel_cm"]
    sacak = t["cati"].get("sacak", 30.0)
    duvar_ustu = t["cati"].get("duvar_ustu", 270.0)
    adli, kn, aile, serbest = aileler(c)
    uyari: list[str] = [f"makas: {H} kırma yüzü hiçbir aileye bağlanmadı; o yüzde kısa makas ve çapraz yok" for H in serbest]
    if not aile:
        uyari.append("makas: çatıda makas ailesi bulunamadı; makas yok")
        return {"makaslar": [], "aileler": [], "baglanmayan_kirma_yuzleri": serbest, "uyarilar": uyari}

    def koy(tur, aile_ad, eksen, a_, cz):
        if cz and cz["s1"] - cz["s0"] >= en_kisa:
            out.append(_kayit(tur, aile_ad, eksen, a_, cz, duvar_ustu, panel))
        elif not cz:
            uyari.append(f"makas: {aile_ad} ailesinde {a_:.1f} konumunda çatının içinde çizgi yok: makas yok")
        else:
            uyari.append(f"makas: {aile_ad} ailesinde {a_:.1f} konumunda {'kısa makas' if tur == 'kisa' else 'makas'} çizgisi "
                         f"{cz['s1'] - cz['s0']:.1f} cm (en kısa {en_kisa:g}): makas yok")
    bb = unary_union([d["cokgen"] for d in adli.values()]).bounds
    tekler = [x["duzlemler"][0] for x in aile if x["tur"] == "tek"]
    out, kayit = [], []
    for f in aile:
        ex = f["eksen"]; ee = _oteki(ex)
        ad = "/".join(f["duzlemler"])
        if f["tur"] == "besik":
            ks, nedenler, uclar = _besik_konumlar(y, adli, kn, aile, f, sacak, S, kal, uyari)
            uzanan = tekler + [x for kk in f["kanatlari"] for x in kk["takim"]]
            for a_ in ks:
                cz = _besik_cizgi(adli, f, a_, bb, uzanan)
                koy("makas" if cz and cz["mahyali"] else "kisa", ad, ex, a_, cz)
            for i, H in sorted(f["kirma_yuzu"].items()):     # kırma ucunun şeridi: kırma yüzünün yönünde kısa makaslar
                w = uclar[i]
                a1 = (ks[0] if i == 0 else ks[-1]) if ks else (uclar[0] + uclar[1]) / 2     # tam makas yoksa iki şerit ortada buluşur
                hb = adli[H]["cokgen"].bounds
                ln = LineString([(w, hb[1] - 1), (w, hb[3] + 1)]) if ee == "x" else LineString([(hb[0] - 1, w), (hb[2] + 1, w)])
                kes = ln.intersection(adli[H]["cokgen"])
                if kes.is_empty or kes.geom_type != "LineString":
                    uyari.append(f"makas: {ad} ailesinin {H} kırma yüzünde uç duvar çizgisi yüzü tek parça kesmiyor ({'boş' if kes.is_empty else kes.geom_type}); "
                                 "o şeritte kısa makas yok")
                    continue
                cc = [q[_i(ex)] for q in kes.coords]
                for pos in _esit_bol(min(cc), max(cc), True, True, S):
                    koy("kisa", H, ee, pos, _tek_cizgi(adli, H, ee, pos, bb, (-math.inf, a1) if i == 0 else (a1, math.inf)))
        else:
            ks, nedenler, ucgen = _tek_konumlar(y, adli, kn, f, sacak, S, kal, uyari)
            for a_ in ks:
                koy("makas", ad, ex, a_, _tek_cizgi(adli, f["duzlemler"][0], ex, a_, bb))
            for b, cpos in ucgen:                             # kırma üçgeni: ailenin yönünde kısa makaslar
                for pos in _esit_bol(min(b, cpos), max(b, cpos), True, True, S):
                    koy("kisa", ad, ex, pos, _tek_cizgi(adli, f["duzlemler"][0], ex, pos, bb))
        kayit.append({"aile": ad, "tur": f["tur"], "eksen": f["eksen"], "ana": f["ana"], "uclar": list(nedenler),
                      "konumlar": [round(v, 2) for v in ks], "kirma_yuzleri": [f["kirma_yuzu"][i] for i in sorted(f["kirma_yuzu"])],
                      "kanatlari": ["/".join(x["duzlemler"]) for x in f["kanatlari"]]})
    # çaprazlar: kırma çizgisi boyunca, saçak köşesinden tepeye
    for e in kn:
        if e["tur"] != "kirma":
            continue
        a_, b_ = e["duzlemler"]
        bagli = any((a_ in f["duzlemler"] and b_ in f["kirma_yuzu"].values()) or (b_ in f["duzlemler"] and a_ in f["kirma_yuzu"].values()) for f in aile)
        if not (bagli or a_ in tekler or b_ in tekler):              # iki ailenin arasındaki kırma (ÇP-07'nin kanat birleşimi gibi): kural sorusu
            uyari.append(f"makas: {a_}/{b_} kırma çizgisi ({e['plan_boy']:.1f} cm) iki ailenin arasında: çapraz yok (kural: çapraz yalnız "
                         "kırma yüzüyle ailesi ya da tek eğimli düzlemle komşusu arasında)")
            continue
        L = e["plan_boy"]
        z0, z1 = e["kot"]
        if z0 > z1:
            z0, z1 = z1, z0
        n = max(2, int(math.ceil(L / ADIM)) + 1)
        ss = [L * j / (n - 1) for j in range(n)]
        zz = [z0 + (z1 - z0) * s / L for s in ss]
        u = uyeler(ss, zz, duvar_ustu, panel)
        out.append({"tur": "capraz", "aile": "/".join(e["duzlemler"]), "eksen": None, "konum": None,
                    "s": [[round(v, 2) for v in e["p"]], [round(v, 2) for v in e["q"]]], "acik_cm": round(L, 2),
                    "h_en_cok_cm": round(z1 - duvar_ustu, 2), "uyeler_m": {ad: round(v, 4) for ad, v in u.items()},
                    "profil_boyu_m": round(sum(u.values()), 4)})
    return {"makaslar": out, "aileler": kayit, "baglanmayan_kirma_yuzleri": serbest, "uyarilar": uyari}


# ──────────────────────────────────────────────────────────────── paneller ──
def panel_uyeleri(pol: Polygon, k: dict, capraz: bool = True) -> dict[str, float]:
    """Düz (açılımdaki) bir panelin üyeleri, duvar paneli kuralıyla (m): çevre (başlıklar ve uç dikmeler), ara dikmeler
    (`dikme_araligi_cm` arayla, uzun kenara dik), kuşaklar (`kusak_kotlari_cm`, uzun kenara paralel) ve çapraz payı
    (kısa kenar × (a + b × uzun kenar); karkas kuralının `capraz_payi`). Dikdörtgende `karkas.uyeler` ile aynı."""
    x0, y0, x1, y1 = pol.bounds
    du, dv = x1 - x0, y1 - y0
    uzun_u = du >= dv
    L, H = (du, dv) if uzun_u else (dv, du)
    S = _d(k, "dikme_araligi_cm")

    def kesit(sabit, deger):
        ln = (LineString([(deger, y0 - 1), (deger, y1 + 1)]) if sabit == "u" else LineString([(x0 - 1, deger), (x1 + 1, deger)]))
        return ln.intersection(pol).length
    # ara dikmeler `karkas.uyeler`'deki gibi: son aralık 1 cm'den (karkas.TOL) kısaysa o dikme uç dikmesidir
    dikme = sum(kesit("u" if uzun_u else "v", (x0 if uzun_u else y0) + S * j) for j in range(1, int(math.ceil((L - 1.0) / S - 1e-9))))
    kusak = sum(kesit("v" if uzun_u else "u", (y0 if uzun_u else x0) + z) for z in _d(k, "kusak_kotlari_cm")
                if z < H - _d(k, "kusak_ust_payi_cm"))
    cp = _d(k, "capraz_payi")
    u = {"cevre": pol.length / 100, "dikme": dikme / 100, "kusak": kusak / 100}
    if capraz:
        u["capraz"] = H / 100 * (cp["a_m_m"] + cp["b_m_m2"] * L / 100)
    return u


def _acilim(dz: dict) -> Polygon:
    return dz["acilim"] if dz["acilim"].is_valid else dz["acilim"].buffer(0)


def _parcalar(p) -> list[Polygon]:
    """Kesişimin çokgen parçaları (1 cm²'den büyük)."""
    return [g for g in ([p] if p.geom_type == "Polygon" else list(getattr(p, "geoms", []))) if g.geom_type == "Polygon" and g.area > 1.0]


def _saciga_bol(pol: Polygon, n: int) -> list[Polygon]:
    """Açılımdaki çokgen saçak boyunca (u ekseni) n eşit şeride."""
    x0, y0, x1, y1 = pol.bounds
    out = []
    for j in range(n):
        out += _parcalar(pol.intersection(box(x0 + (x1 - x0) * j / n, y0 - 1, x0 + (x1 - x0) * (j + 1) / n, y1 + 1)))
    return out


def ek_yapi_mi(dz: dict, y: dict) -> bool:
    """Çatı panelli düzlem bir ek yapıyı (müştemilat) mı örtüyor; değilse açık alan (veranda, sundurma)."""
    return any(b["sinif"] == "ek" and dz["cokgen"].contains(b["net"].representative_point()) for b in y["bolgeler"].values())


def cati_paneli_adedi(dz: dict, k: dict, y: dict) -> int:
    """Çatı panelli düzlemin panel adedi: tanımda yazıyorsa (`cati_paneli_adedi`) o; yazmıyorsa açık alanın düzleminde kuralda
    `en_cm_acik_alan` varsa (İE-16 PR-3c; Lokman, 27 Ekim 2026: 60 cm arayla C profil, 180 cm genişlik) açılımın saçak boyu ÷ o, yukarı;
    yoksa (ek yapı ya da eski kural kopyası) 1. Liste (`cati_panelleri`) ve pafta (`makas_pafta.cati_paneli_planlari`) bunu okur."""
    en = _d(k, "cati_paneli").get("en_cm_acik_alan")
    if dz.get("cati_paneli_adedi") or not en or ek_yapi_mi(dz, y):
        return int(dz.get("cati_paneli_adedi", 1))
    pol = _acilim(dz)
    return max(1, math.ceil((pol.bounds[2] - pol.bounds[0]) / en - 1e-9))


def cati_panelleri(c: dict, y: dict, k: dict) -> list[dict]:
    """Tanımda çatı paneli yazan düzlemler (`ust_yapi: cati_paneli`): açılım saçak boyunca eşit panellere. Adet tanımda yazıyorsa
    (`cati_paneli_adedi`; açık projede paftadan) o; yazmıyorsa kuraldan (`cati_paneli_adedi`). Kuralda `capraz: false` ise çapraz yok
    (İE-16 PR-3c)."""
    cp = _d(k, "cati_paneli")
    out = []
    for dz in c["duzlemler"]:
        if dz.get("ust_yapi") != "cati_paneli":
            continue
        ek_yapi = ek_yapi_mi(dz, y)
        et = cp["et_ek_yapi"] if ek_yapi else cp["et_acik_alan"]
        for j, p in enumerate(_saciga_bol(_acilim(dz), cati_paneli_adedi(dz, k, y)), 1):
            u = panel_uyeleri(p, k, capraz=cp.get("capraz", True))
            out.append({"duzlem": dz["ad"], "sira": j, "ortu": "ek yapı" if ek_yapi else "açık alan", "profil": f"80x45x{et}",
                        "olcu_cm": [round(p.bounds[2] - p.bounds[0], 2), round(p.bounds[3] - p.bounds[1], 2)],
                        "uyeler_m": {a: round(v, 4) for a, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    return out


def _izgaraya_bol(pol: Polygon, nu: int, nv: int) -> list[Polygon]:
    """Açılımdaki çokgen saçak boyunca (u) nu, eğim boyunca (v) nv eşit parçaya; sıra saçaktan yukarı, soldan sağa."""
    x0, y0, x1, y1 = pol.bounds
    out = []
    for i in range(nv):
        for j in range(nu):
            out += _parcalar(pol.intersection(box(x0 + (x1 - x0) * j / nu, y0 + (y1 - y0) * i / nv, x0 + (x1 - x0) * (j + 1) / nu,
                                                  y0 + (y1 - y0) * (i + 1) / nv)))
    return out


def ust_panelleri(c: dict, k: dict, uyari: list[str] | None = None) -> list[dict]:
    """Yöntem A'nın çatı üstü panelleri, makaslı her düzlemin açılımında. Kuralda `ust_paneli` varsa (İE-16 PR-3c; Lokman, 27 Ekim
    2026): panel makaslara dik bağlanır, aşık görevi görür; eğim boyunca en çok `en_cm` (60 cm arayla üç C profil: 180), saçak boyunca
    en çok `boy_makas_araligi` makas aralığı (`makas.aralik_cm` ile), ikisinde de eşit bölünür; kırma yüzü ayrı düzlemdir (kırıldığı
    yerden kesilir); `capraz: false` ise çapraz yok. Kısa kenarı makas kalınlığından dar ya da 100 cm²'den küçük parça (kırma yüzünün
    köşesinde ızgaranın kestiği uç) panel olmaz, uyarı yazar (tavan panelindeki gibi). Yoksa (PR-3b'nin kural kopyası) açılım saçak
    boyunca `bolme` hedefiyle eşit panellere."""
    up = k.get("ust_paneli", {}).get("deger")
    kal = _d(k, "makas")["kalinlik_cm"]
    out = []
    for dz in c["duzlemler"]:
        if dz.get("ust_yapi") == "cati_paneli":
            continue
        pol = _acilim(dz)
        if up:
            boy = up["boy_makas_araligi"] * _d(k, "makas")["aralik_cm"]
            nu = max(1, math.ceil((pol.bounds[2] - pol.bounds[0]) / boy - 1e-9))
            nv = max(1, math.ceil((pol.bounds[3] - pol.bounds[1]) / up["en_cm"] - 1e-9))
            parcalar = []
            for p in _izgaraya_bol(pol, nu, nv):
                en = min(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1])
                if p.area < 100.0 or en <= kal + EPS:
                    if uyari is not None:
                        uyari.append(f"çatı üstü paneli: {dz['ad']} düzleminde {p.area:.0f} cm² parça, kısa kenarı {en:.1f} cm "
                                     f"(makas kalınlığı {kal:g} cm, en küçük parça 100 cm²): panel yok")
                    continue
                parcalar.append(p)
        else:
            hedef = _d(k, "bolme")["hedef_cm"]
            parcalar = _saciga_bol(pol, max(1, math.ceil((pol.bounds[2] - pol.bounds[0]) / hedef - 1e-9)))
        for j, p in enumerate(parcalar, 1):
            u = panel_uyeleri(p, k, capraz=up.get("capraz", True) if up else True)
            out.append({"duzlem": dz["ad"], "sira": j, "olcu_cm": [round(p.bounds[2] - p.bounds[0], 2), round(p.bounds[3] - p.bounds[1], 2)],
                        "uyeler_m": {a: round(v, 4) for a, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    return out


def _uzunu_bol(g: Polygon, en_uzun: float | None) -> list[Polygon]:
    """Uzun kenarı `en_uzun`'u aşan parça o kenar boyunca eşit parçalara (tavan paneli; tırın boyu, İE-16 PR-3c); sınır yoksa kendisi."""
    x0, y0, x1, y1 = g.bounds
    L = max(x1 - x0, y1 - y0)
    if not en_uzun or L <= en_uzun + EPS:
        return [g]
    n = math.ceil(L / en_uzun - 1e-9)
    kutular = ([box(x0 + (x1 - x0) * j / n, y0 - 1, x0 + (x1 - x0) * (j + 1) / n, y1 + 1) for j in range(n)] if x1 - x0 >= y1 - y0 else
               [box(x0 - 1, y0 + (y1 - y0) * j / n, x1 + 1, y0 + (y1 - y0) * (j + 1) / n) for j in range(n)])
    out = []
    for kb in kutular:
        out += _parcalar(g.intersection(kb))
    return out


def tavan_panelleri(c: dict, y: dict, k: dict, mk: dict, uyari: list[str]) -> list[dict]:
    """Yöntem A'nın tavan panelleri: ana ailenin makas aralıkları (uç duvarlara kadar) şerit; şerit her mahalle (ve verandayla)
    kesilir, her parça bir panel. Çatı paneli altındaki mahal ve çatısız veranda hariç. Ana aile birden çok olabilir (en büyük
    düzlem birden çok mahyaya katılırsa, ör. cumba): hepsinin konumları şerit sınırıdır. Makas kalınlığından (`kalinlik_cm`) dar şerit
    iki makasın arasında ya da makasın altında kalır, panel olmaz; kısa kenarı makas kalınlığından dar parça da (makasın altında) ve
    100 cm²'den küçük parça da panel olmaz. Kısa kenarı `dikme_araligi_cm`'den kısa parça panel olur. Panel olmayan parça ve dar panel
    uyarı yazar."""
    tp = _d(k, "tavan_paneli")
    kal = _d(k, "makas")["kalinlik_cm"]
    S = _d(k, "dikme_araligi_cm")
    makasli = unary_union([d["cokgen"] for d in c["duzlemler"] if d.get("ust_yapi") != "cati_paneli"])
    panelli = [d["cokgen"] for d in c["duzlemler"] if d.get("ust_yapi") == "cati_paneli"]
    bolgeler = [b for b in y["bolgeler"].values() if b["sinif"] in ("ic", "ek", "veranda")
                and makasli.contains(b["net"].representative_point()) and not any(p.contains(b["net"].representative_point()) for p in panelli)]
    ana = [f for f in mk["aileler"] if f["ana"] and f["tur"] == "besik"]
    if not ana or not bolgeler:
        uyari.append("tavan paneli: " + ("ana beşik aile yok" if not ana else "makaslı çatının altında mahal yok") + "; tavan paneli kurulmadı")
        return []
    ex = ana[0]["eksen"]; ee = _oteki(ex)
    ana = [f for f in ana if f["eksen"] == ex]
    ie = _i(ee)
    tavan_geo = unary_union([b["net"] for b in bolgeler])
    lo, hi = tavan_geo.bounds[ie], tavan_geo.bounds[ie + 2]
    sinirlar = sorted({v for f in ana for v in f["konumlar"]} | {lo, hi})
    adlar = {f["aile"] for f in ana}
    cizgiler = []                                         # şerit sınırı olmayan makasların alt başlıkları (başka aile, kısa, çapraz)
    for x in mk["makaslar"]:
        if x["tur"] == "capraz":
            cizgiler.append(LineString(x["s"]))
        elif not (x["aile"] in adlar and x["tur"] == "makas"):
            s0, s1 = x["s"]
            cizgiler.append(LineString([(s0, x["konum"]), (s1, x["konum"])] if x["eksen"] == "x" else [(x["konum"], s0), (x["konum"], s1)]))
    sinirlar = [v for v in sinirlar if lo - EPS <= v <= hi + EPS]
    out = []
    for a0, a1 in zip(sinirlar, sinirlar[1:]):
        if a1 - a0 <= kal + EPS:
            continue
        bb = tavan_geo.bounds
        serit = box(a0, bb[1] - 1, a1, bb[3] + 1) if ee == "x" else box(bb[0] - 1, a0, bb[2] + 1, a1)
        for b in bolgeler:
            p = serit.intersection(b["net"])
            for g in ([p] if p.geom_type == "Polygon" else list(getattr(p, "geoms", []))):
                if g.geom_type != "Polygon" or g.area <= 0:
                    continue
                en = min(g.bounds[2] - g.bounds[0], g.bounds[3] - g.bounds[1])
                if g.area < 100.0 or en <= kal + EPS:
                    uyari.append(f"tavan paneli: {b['ad']} mahalinde {a0:.1f}–{a1:.1f} şeridinde {g.area:.0f} cm² parça, kısa kenarı {en:.1f} cm "
                                 f"(makas kalınlığı {kal:g} cm, en küçük parça 100 cm²): panel yok")
                    continue
                if en < S:
                    uyari.append(f"tavan paneli: {b['ad']} mahalinde {a0:.1f}–{a1:.1f} şeridinde parçanın kısa kenarı {en:.1f} cm "
                                 f"(dikme aralığı {S:g}): panel kuruldu")
                for g in _uzunu_bol(g, tp.get("en_uzun_cm")):
                    ic = g.buffer(-EPS)
                    kesilen = sum(1 for ln in cizgiler if ln.intersection(ic).length > EPS)
                    u = panel_uyeleri(g, k, capraz=tp["capraz"])
                    out.append({"mahal": b["ad"], "serit": [round(a0, 2), round(a1, 2)], "kesilen_makas": kesilen,
                                "olcu_cm": [round(g.bounds[2] - g.bounds[0], 2), round(g.bounds[3] - g.bounds[1], 2)],
                                "uyeler_m": {a: round(v, 4) for a, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    kesen = [p for p in out if p["kesilen_makas"]]
    if kesen:                                             # şeritler yalnız ana ailenin makaslarıyla: dik ailenin altındaki panel makası keser
        uyari.append(f"tavan paneli: {len(kesen)} panel başka makasların alt başlığını kesiyor (toplam {sum(p['kesilen_makas'] for p in kesen)} "
                     "kesişme): şeritler yalnız ana ailenin makaslarıyla (kural sorusu)")
    return out


def tek_aciklik(x: dict, y: dict, t: dict) -> float | None:
    """Makasın altında desteksiz en uzun aralık (cm): makas çizgisini kesen oda duvarları (dış, iç, ek), kolonlar ve kirişler destektir;
    destekler arasındaki en büyük aralık. Uçlardaki saçak (son destekten öte) aralık değildir. Kırma çaprazı (eksensiz) ya da ikiden az
    desteği olan makas için yok."""
    if x["eksen"] is None or x["konum"] is None:
        return None
    ex, a = x["eksen"], x["konum"]
    s0, s1 = x["s"]
    ie = _i(_oteki(ex))                              # makasın konumunun ekseni (makasa dik)
    destek = []
    for w in y["duvarlar"]:
        if w["sinif"] not in ("dis", "ic", "ek", "kolon"):
            continue
        kt = w["kutu"]
        if w["sinif"] != "kolon" and w["yon"] == ex:  # makasa paralel duvar taşımaz
            continue
        if kt[ie] - EPS <= a <= kt[ie + 2] + EPS:
            destek.append((kt[_i(ex)] + kt[_i(ex) + 2]) / 2)
    for kr in t.get("kirisler", []):
        kt = kr["kutu"]
        if (kt[ie + 2] - kt[ie]) > (kt[_i(ex) + 2] - kt[_i(ex)]) and kt[ie] - EPS <= a <= kt[ie + 2] + EPS:
            destek.append((kt[_i(ex)] + kt[_i(ex) + 2]) / 2)
    destek = sorted(v for v in set(round(v, 1) for v in destek) if s0 - EPS <= v <= s1 + EPS)
    return max((q - p for p, q in zip(destek, destek[1:])), default=None) if len(destek) > 1 else None


def kur(t: dict, y: dict, k: dict, yontem: str | None = None) -> dict:
    """Çatının karkas kaydı: makaslar, çatı panelleri ve (yöntem A: `yontem == "panel"`) çatı üstü ve tavan panelleri. Kuralda `makas_eti`
    varsa (İE-16 PR-3c) her makasın desteksiz en uzun aralığı (`tek_aciklik_cm`) ve et kalınlığı (`et`) yazılır."""
    c = cati_genel.cati_kur(t["cati"])
    mk = makaslar(t, c, y, k)
    uyari = list(mk["uyarilar"])
    me = k.get("makas_eti", {}).get("deger")
    if me:
        for x in mk["makaslar"]:
            ta = tek_aciklik(x, y, t)
            x["tek_aciklik_cm"] = None if ta is None else round(ta, 1)
            x["et"] = me["kalin"] if ta is not None and ta > me["tek_aciklik_en_cok_cm"] + EPS else me["ince"]
    out = {"makaslar": mk["makaslar"], "aileler": mk["aileler"], "baglanmayan_kirma_yuzleri": mk["baglanmayan_kirma_yuzleri"],
           "cati_panelleri": cati_panelleri(c, y, k)}
    if yontem == "panel":
        out["ust_panelleri"] = ust_panelleri(c, k, uyari)
        out["tavan_panelleri"] = tavan_panelleri(c, y, k, mk, uyari)
    out["uyarilar"] = uyari
    return out
