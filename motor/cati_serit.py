"""İE-24 · Girintili gövdenin beşik çatısı: ana çatı ve ona paralel cumbalar (TK-03; Lokman, 30 Ekim 2026 13:49).

Lokman: "çatıda 3 tür makas var; en uzun makasları ana makas kabul et, diğer makasları cumba makası kabul et; Altan bey'in projesindeki
veranda makası mantığıyla aynı". Gövdenin dış çizgisi (`G.govde_cokgeni`) mahyaya dik şeritlere bölünür: bir şeritte makaslar aynı
açıklığı geçer. Açıklığı en büyük şerit ana çatıdır (ana makas), ötekiler cumbadır (cumba makası). Cumba, TK-01'in veranda çatısı gibi
(BK-14) komşu şeridin kalkan yüzüne dayanan, ona paralel küçük beşiktir: eğim, saçak ve saçak kotu ana çatınınki; dış ucunda kalkan ve
saçak; iç ucu komşunun kalkan saçağının altına girer, komşunun duvarının dış yüzünde biter (paftanın aşık planı: sol cumbanın arka yüzü
−30 → 543,5). Şeridin açıklığı ana çatıya doğru komşusununkinin içinde kalmalı (çatısı komşunun altında kalır); kalmıyorsa ya da gövde bir
şeritte iki parçaya bölünüyorsa (U gövde) çatı çizilmez, hata söylenir (yanlış çatı çizilmez).

Düzlemler genel motorun biçiminde (`cati_genel.cati_kur`; `cephe_gorunus` görünüşleri bundan çizer): her şeridin iki yüzü. Saçak çizgisi
aynı olan bitişik yüzler aynı düzlemdir ve birleşir (TK-03: sol cumbanın ön yüzü ana çatının ön yüzünün devamı, ön saçak −30 → 815,6 tek
hat; sağ cumbanın arka yüzü ana çatının arka yüzünün devamı). Kalkanlar: şeridin dış ucunda duvar üstünden; komşusu alçak olan uçta komşunun
çatısının üstünde kalan kısım (`alt`), komşusu olmayan kısım duvar üstünden. Cumbanın iç ucunda kalkan yoktur.

Makaslar (paftanın makas planı MKS01–12; sayfa 9: makaslar dış duvarın H'larına gelir): ana çatıda iki baş makas iki kalkan duvarının
ekseninde, cumbada tek baş makas dış uçtaki duvarın ekseninde; orta makaslar şeridin saçak duvarlarının pano eklerinde, en çok 125,5 arayla
(baştan başlayarak en uzaktaki ek). Cumbanın iç ucunda makas yoktur: son açıklık komşunun baş makasına kadardır. Sayı açıklıkların
125,5'i aşmamasından: ana ⌈eksenler arası ÷ 125,5⌉ + 1, cumba ⌈dış eksenden komşunun eksenine ÷ 125,5⌉. Ekler bu sayıyı vermiyorsa eşit
aralık ve uyarı (K16).

Açık mahalin kendi çatısı (İE-17 PR-2, AP-09 paftası, 1 Kasım 2026): `cati.mahal_catilari` [{`mahal` (ızgaradaki açık mahal: veranda),
`tip` tek_yon, `egim_yuzde` (paftadan; varsayılan yok), `yuksek_yan` on | arka | sol | sag (çatının dayandığı, kapalı gövdeye bitişik yan),
`sacak_cm` (açık yanlarda, 0)}]. Ana çatı o mahali örtmez: ayak izinden mahalin kutusu çıkar (`cati_izi`), kalan gövdenin şeritleri ana
çatı ve paralel cumbalardır (AP-09: verandanın arka duvarından arkaya ana çatı, sağ öndeki bölümde cumba). Mahalin çatısı tek eğimli panel
çatıdır (paftada P1, 381,5 × 245,48): yüksek kenarı dayandığı duvarın üstünde (duvar üstü), alçak kenarı eğimle dış yana iner; alçak kenarda
mahalin boyunca kiriş (10 × 10, üstü çatının alt kenarı; paftanın montaj planındaki V02 ön profili), serbest dikme kirişin altına, gövdenin
duvar ucundaki dikme (paftanın A profili, 250) duvar üstüne kadar. Ana çatının ve cumbanın
saçağının altında kalır; kalmıyorsa çatı çizilmez, hata söylenir (yanlış çatı çizilmez).
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import geometry as G
from .cati_prefabrik import PrefabrikCatiHatasi

MOD = G.MOD
TOL = 0.01


def _eksen(ie: dict):
    """Kanonik eksenler: a mahya boyunca, b makas boyunca. (a, b) → (x, y) ve geri."""
    if (ie.get("cati") or {}).get("makas_ekseni", "x") == "y":       # makaslar y'yi geçer, mahya x boyunca (TK-03)
        return (lambda a, b: (a, b)), (lambda x, y: (x, y)), "y"
    return (lambda a, b: (b, a)), (lambda x, y: (y, x)), "x"


def seritler(cokgen, ie: dict) -> list[list[float]]:
    """Gövdenin mahyaya dik şeritleri, mahya boyunca sırayla: [a0, a1, b0, b1] (kanonik, dış yüzler). Aynı açıklıktaki komşu dilimler tek şerit."""
    P, K, _ = _eksen(ie)
    noktalar = [K(x, y) for x, y in cokgen.exterior.coords]
    a_lar = sorted({round(a, 2) for a, _b in noktalar})
    b_min, b_max = min(b for _a, b in noktalar) - 1, max(b for _a, b in noktalar) + 1
    out: list[list[float]] = []
    for a0, a1 in zip(a_lar, a_lar[1:]):
        am = (a0 + a1) / 2
        k = cokgen.intersection(LineString([P(am, b_min), P(am, b_max)]))
        parca = [g for g in getattr(k, "geoms", [k]) if g.geom_type == "LineString" and g.length > TOL]
        if len(parca) != 1:
            raise PrefabrikCatiHatasi(f"girintili gövde: mahyaya dik kesitte gövde {len(parca)} parça (U gövde); çatısı bu sürümde çizilmez")
        bs = [K(x, y)[1] for x, y in parca[0].coords]
        b0, b1 = round(min(bs), 2), round(max(bs), 2)
        if out and abs(out[-1][2] - b0) < TOL and abs(out[-1][3] - b1) < TOL:
            out[-1][1] = a1
        else:
            out.append([a0, a1, b0, b1])
    return out


def cati_izi(plan: G.Plan, ie: dict | None = None):
    """Çatının ayak izi: gövdenin dış çizgisi (`G.govde_cokgeni`); açık mahalin (veranda) dikmeleriyle birlikte dış kutusu da içinde.
    İE-17 PR-2 (AP-15 paftası, 1 Kasım 2026): verandanın sağ kenarı köşe dikmesinden yatak odası 2'nin köşesine 17,75 açık; gövde çizgisi
    orada dikmenin dış yüzünden 5 cm içeri girer ve şeritleri böler. Paftada cumba 0–386,5, dikmenin dış yüzüne kadar. Dikmesiz açık mahal
    ve dikmesi kutusunu büyütmeyen mahal izi değiştirmez (TK-03). Kendi çatısı olan açık mahal (`cati.mahal_catilari`, AP-09) izden çıkar:
    ana çatı onu örtmez."""
    g = G.govde_cokgeni(plan)
    kendi = {m["mahal"]: m for m in (mahal_catilari(plan, ie) if ie else [])}
    ekler = []
    for m in plan.mahaller.values():
        if not m.acik or m.poly is None or m.poly.is_empty or m.ad in kendi:
            continue
        dk = [box(*d) for d in plan.dikmeler if box(*d).distance(m.poly) < 0.5]
        if dk:
            ekler.append(box(*unary_union([m.poly, *dk]).bounds))
    u = unary_union([g, *ekler]) if ekler else g
    if kendi:
        u = u.difference(unary_union([box(*m["kutu"]) for m in kendi.values()]))
    if not ekler and not kendi:
        return g
    en = max(getattr(u, "geoms", [u]), key=lambda p: p.area)
    return Polygon(en.exterior.coords).simplify(TOL)


MAHAL_CATI_ALANLARI = {"mahal", "tip", "egim_yuzde", "yuksek_yan", "sacak_cm"}
_YAN_YON = {"on": (0, -1), "arka": (0, 1), "sol": (-1, 0), "sag": (1, 0)}      # yanın dışarı yönü (gerçek çerçeve: ön y = 0)


def mahal_catilari_var(ie: dict) -> bool:
    return bool((ie.get("cati") or {}).get("mahal_catilari"))


def mahal_catilari(plan: G.Plan, ie: dict) -> list[dict]:
    """`cati.mahal_catilari` → [{"ad", "mahal", "kutu" (mahalin dış kutusu, cm), "yuksek_yan", "duzlem" (genel motorun düzlem biçimi), "egim",
    "ust_kot" (yüksek kenar: duvar üstü), "alt_kot" (alçak kenar), "kolonlar" [(x0, y0, x1, y1, üst kot)] (mahalin dikmeleri), "kirisler"
    [(x0, y0, x1, y1, z0, z1)]}].
    Denetim: mahal ızgarada açık mahal; yüksek yanı boyunca kapalı gövdeye bitişik, karşı yanı açık; tanınmayan alan yok sayılmaz."""
    lst = (ie.get("cati") or {}).get("mahal_catilari") or []
    if not lst:
        return []
    if not isinstance(lst, list):
        raise PrefabrikCatiHatasi("cati.mahal_catilari bir liste olur")
    H0 = float((ie.get("yapi") or {}).get("duvar_yuksekligi_cm", 250))
    kutu_g = box(*G.govde_kutusu(plan))
    acik = {m.ad: m for m in plan.mahaller.values() if m.acik and m.poly is not None and not m.poly.is_empty}
    dis_v = {v["ad"] for v in plan.dis_verandalar}
    kutular = []
    for g in lst:
        if not isinstance(g, dict):
            raise PrefabrikCatiHatasi("cati.mahal_catilari'nin her girişi bir sözlük olur")
        fazla = sorted(set(g) - MAHAL_CATI_ALANLARI)
        if fazla:
            raise PrefabrikCatiHatasi(f"mahal çatısında tanınmayan alan: {', '.join(fazla)} (yok sayılmaz; yanlış çatı çizilmez)")
        ad = g.get("mahal")
        if ad not in acik or ad in dis_v:
            raise PrefabrikCatiHatasi(f"mahal çatısı: '{ad}' ızgaradaki açık mahal değil (taşan veranda kendi çatısıyla `verandalar`'da)")
        kutular.append(acik[ad].poly.bounds)
    kapali = kutu_g.difference(unary_union([box(*k) for k in kutular]))
    out = []
    for g, (x0, y0, x1, y1) in zip(lst, kutular):
        ad = g["mahal"]
        if g.get("tip") != "tek_yon":
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): yalnız tek_yon (tek eğimli panel çatı) çizilir; '{g.get('tip')}' yok")
        if g.get("egim_yuzde") is None:
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): eğim paftadan yazılır (`egim_yuzde`; varsayılan yok)")
        eg = float(g["egim_yuzde"]) / 100.0
        if not 0 < eg < 1:
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): eğim %{g['egim_yuzde']} olmaz")
        s = float(g.get("sacak_cm", 0))
        if s < 0:
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): saçak {s:g} cm olmaz")
        yan = g.get("yuksek_yan")
        if yan not in _YAN_YON:
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): yuksek_yan on, arka, sol ya da sag olur: {yan}")

        def serit(y_, d=1.0):
            """Mahalin `y_` yanının hemen dışındaki d cm'lik şerit."""
            return {"on": box(x0, y0 - d, x1, y0), "arka": box(x0, y1, x1, y1 + d),
                    "sol": box(x0 - d, y0, x0, y1), "sag": box(x1, y0, x1 + d, y1)}[y_]

        def bitisik(y_):                                                   # yanı boyunca kapalı gövde var mı (1 cm şeridin dolu oranı)
            return kapali.intersection(serit(y_)).area / serit(y_).area
        karsi = {"on": "arka", "arka": "on", "sol": "sag", "sag": "sol"}[yan]
        if bitisik(yan) < 0.99:
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): yüksek yanı ({yan}) boyunca kapalı gövde yok; çatı dayanmaz")
        if bitisik(karsi) > 0.01:
            raise PrefabrikCatiHatasi(f"mahal çatısı ({ad}): alçak yanı ({karsi}) kapalı gövdeye bitişik; su duvara iner")
        ac = {y_: bitisik(y_) < 0.01 for y_ in _YAN_YON}                   # açık yan: saçak orada
        X0, Y0, X1, Y1 = x0 - s * ac["sol"], y0 - s * ac["on"], x1 + s * ac["sag"], y1 + s * ac["arka"]
        ux, uy = _YAN_YON[yan]                                             # yukarı yönü: yüksek yana doğru
        derin = (Y1 - Y0) if uy else (X1 - X0)
        alt = H0 - derin * eg
        sacak = {"on": {"y": Y1}, "arka": {"y": Y0}, "sol": {"x": X1}, "sag": {"x": X0}}[yan]     # alçak kenar
        dz = {"ad": f"{ad} çatısı", "plan": [[X0, Y0], [X1, Y0], [X1, Y1], [X0, Y1]], "yukari": [ux, uy], "egim": eg, "sacak_kotu": alt,
              "sacak": sacak, "ust_yapi": "cati_paneli"}
        K = 10.0                                                           # alçak kenarda kiriş (mahalin boyunca), üstü çatının alt kenarı
        kiris = [(x0, y0, x1, y0 + K) if uy > 0 else (x0, y1 - K, x1, y1) if uy < 0 else (x0, y0, x0 + K, y1) if ux > 0 else (x1 - K, y0, x1, y1)]
        kiris = [(*k, alt - K, alt) for k in kiris]
        kolon = []                                                         # dikme: gövdenin duvar ucundaki profil (AP-09 paftası A) duvar üstüne,
        for d in plan.dikmeler:                                            # serbest dikme kirişin altına
            if box(*d).distance(acik[ad].poly) < 0.5:
                kolon.append((*d, H0 if kapali.intersection(box(*d)).area > 1e-6 else alt - K))
        out.append({"ad": dz["ad"], "mahal": ad, "kutu": (x0, y0, x1, y1), "yuksek_yan": yan, "duzlem": dz, "egim": eg, "sacak": s,
                    "ust_kot": H0, "alt_kot": round(alt, 4), "kolonlar": kolon, "kirisler": kiris})
    return out


def _mahal_cati_denetle(mc: list[dict], duzlemler: list[dict]) -> None:
    """Mahal çatısı, planda üst üste geldiği ana çatı ve cumba düzlemlerinin altında kalır (saçak bandı; 0,5 cm pay)."""
    from .veranda import kot
    for m in mc:
        pv = Polygon(m["duzlem"]["plan"])
        for dm in duzlemler:
            k = pv.intersection(Polygon(dm["plan"]))
            for gg in getattr(k, "geoms", [k]):
                if gg.is_empty or gg.geom_type != "Polygon" or gg.area < 1e-6:
                    continue
                for x, y in gg.exterior.coords:
                    f = kot(m["duzlem"], x, y) - kot(dm, x, y)
                    if f > 0.5:
                        raise PrefabrikCatiHatasi(f"{m['ad']}: {dm['ad']} düzleminin {f:.0f} cm üstüne çıkıyor (saçağının altında kalmalı); "
                                                  "yanlış çatı çizilmez")


def _ekler(plan: G.Plan, serit, eksen: str, h: float) -> list[float]:
    """Şeridin saçak duvarlarının (b0 ve b1 yüzündeki dış duvarlar) pano ekleri, mahya boyunca (a)."""
    a0, a1, b0, b1 = serit
    yon = "x" if eksen == "y" else "y"                                  # saçak duvarı mahyaya paralel
    out = set()
    for d in plan.duvarlar:
        if d.tur != "dis" or d.yon != yon:
            continue
        if not (abs(d.c - d.h - b0) < TOL or abs(d.c + d.h - b1) < TOL):
            continue
        ps = sorted(d.panolar, key=lambda p: p.a0)
        for p, q in zip(ps, ps[1:]):
            if abs(p.a1 - q.a0) < 1e-6 and a0 + h - TOL < p.a1 < a1 + h + TOL:
                out.add(round(p.a1, 2))
    return sorted(out)


def _makas_yerleri(bas: float, son: float, son_makas: bool, ekler: list[float]) -> tuple[list[float], bool]:
    """`bas` (baş makas) → `son` (öteki baş makas ya da komşunun ekseni) arasında makaslar. Döner: (yerler, eklerde mi)."""
    yon = 1.0 if son > bas else -1.0
    L = abs(son - bas)
    n = math.ceil(L / MOD - 1e-6)
    beklenen = n + (1 if son_makas else 0)
    aday = [e for e in ekler if TOL < (e - bas) * yon < L - TOL]
    xs, cur = [bas], bas
    while abs(son - cur) > MOD + 1e-6:
        uygun = [e for e in aday if 1e-6 < (e - cur) * yon <= MOD + 1e-6]
        if not uygun:
            break
        cur = max(uygun, key=lambda e: (e - cur) * yon)
        xs.append(cur)
    if abs(son - cur) <= MOD + 1e-6 and len(xs) + (1 if son_makas else 0) == beklenen:
        return xs + ([son] if son_makas else []), True
    esit = [bas + yon * L * i / n for i in range(n + 1)]
    return (esit if son_makas else esit[:-1]), False


def tanim(plan: G.Plan, ie: dict) -> dict:
    """Girintili gövdenin çatısı → `sunum.cati_tanimi`'nin beşik biçimi (`tip`, `sacak`, `topuk`, `duvar_ustu`, `duzlemler`) ve ek olarak
    `kalkanlar` (`cati_genel.cati_kur`, görünüşte örtü), `parcalar` (şerit başına ana ya da cumba: açıklık, boy, mahya, makaslar) ve
    `uyarilar`; açık mahalin kendi çatısı varsa `mahal_catilari` (`mahal_catilari`; düzlemi `duzlemler`'de değil: makası, topuğu ve kalkanı
    yok, sacı değil paneli var)."""
    c = ie.get("cati") or {}
    if c.get("tip", "besik") != "besik":
        raise PrefabrikCatiHatasi(f"girintili gövdede yalnız beşik çatı çizilir (ana çatı ve paralel cumbalar); '{c.get('tip')}' yok")
    if plan.dis_verandalar:
        raise PrefabrikCatiHatasi("girintili gövdede taşan veranda bu sürümde çizilmez (iki çatı kuralının birleşimi)")
    mc = mahal_catilari(plan, ie)
    s = float(c.get("sacak_cm", 30)); eg = float(c.get("egim_yuzde", 33)) / 100.0; top = float(c.get("topuk_cm", 10))
    H0 = float((ie.get("yapi") or {}).get("duvar_yuksekligi_cm", 250))
    zs = H0 + top
    P, _K, eksen = _eksen(ie)
    h = next(d.h for d in plan.duvarlar if d.tur == "dis")
    sr = seritler(cati_izi(plan, ie), ie)
    k = max(range(len(sr)), key=lambda i: (round(sr[i][3] - sr[i][2], 2), round(sr[i][1] - sr[i][0], 2), -i))
    for i in range(len(sr)):                                            # cumba ana çatıya doğru komşusunun açıklığı içinde
        if i == k:
            continue
        j = i + 1 if i < k else i - 1
        if not (sr[j][2] - TOL <= sr[i][2] and sr[i][3] <= sr[j][3] + TOL):
            raise PrefabrikCatiHatasi(f"girintili gövde: {i + 1}. şeridin açıklığı ({sr[i][2]:g}–{sr[i][3]:g}) ana çatıya doğru komşusununkinin "
                                      f"({sr[j][2]:g}–{sr[j][3]:g}) içinde değil; çatısı komşunun altında kalmaz (kademeli çatı bu sürümde yok)")
    yan_adi = ("sol", "sağ") if eksen == "y" else ("ön", "arka")
    yuz_adi = ("ön", "arka") if eksen == "y" else ("sol", "sağ")
    adlar = []
    for i in range(len(sr)):
        if i == k:
            adlar.append("ana çatı")
        else:
            taraf = yan_adi[0] if i < k else yan_adi[1]
            ayni = [j for j in range(len(sr)) if j != k and (j < k) == (i < k)]
            sira = sorted(ayni, key=lambda j: abs(j - k)).index(i)
            adlar.append(f"{taraf} cumba" + (f" {sira + 1}" if len(ayni) > 1 else ""))

    def yukari(b_yon):
        return [0, b_yon] if eksen == "y" else [b_yon, 0]

    def sacak(b):
        return {"y": b} if eksen == "y" else {"x": b}

    ham, parcalar, uyarilar = [], [], []
    for i, (a0, a1, b0, b1) in enumerate(sr):
        bm = (b0 + b1) / 2
        A0 = a0 - s if i <= k else a0                                    # cumbanın iç ucu komşunun duvar yüzünde
        A1 = a1 + s if i >= k else a1
        for yuz, (c0, c1, by, sb) in zip(yuz_adi, ((b0 - s, bm, 1, b0 - s), (bm, b1 + s, -1, b1 + s))):
            ham.append({"ad": f"{adlar[i]} {yuz}", "serit": i, "plan": [list(P(A0, c0)), list(P(A1, c0)), list(P(A1, c1)), list(P(A0, c1))],
                        "yukari": yukari(by), "egim": eg, "sacak_kotu": zs, "sacak": sacak(sb)})
        # makaslar
        ekler = _ekler(plan, sr[i], eksen, h)
        if i == k:
            yer, duzenli = _makas_yerleri(a0 + h, a1 - h, True, ekler)
            roller = ["bas"] + ["orta"] * (len(yer) - 2) + ["bas"]
        elif i < k:
            yer, duzenli = _makas_yerleri(a0 + h, a1 + h, False, ekler)
            roller = ["bas"] + ["orta"] * (len(yer) - 1)
        else:
            yer, duzenli = _makas_yerleri(a1 - h, a0 - h, False, ekler)
            roller = ["bas"] + ["orta"] * (len(yer) - 1)
        if not duzenli:
            uyarilar.append(f"makas yeri ({adlar[i]}): saçak duvarlarının pano ekleri makasları 125,5 arayla vermiyor; eşit aralıklı {len(yer)} makas")
        gorunen = (A0, A1) if i == k else (A0, a1 - s) if i < k else (a0 + s, A1)      # cumbanın mahyası komşunun saçağına kadar görünür
        egik = (bm - b0 + s) * math.sqrt(1 + eg * eg)
        parcalar.append({"ad": adlar[i], "rol": "ana" if i == k else "cumba", "a": [a0, a1], "b": [b0, b1],
                         "aciklik_cm": round(b1 - b0, 2), "boy_cm": round(a1 - a0, 2),
                         "mahya": [list(P(gorunen[0], bm)), list(P(gorunen[1], bm))], "mahya_kotu": round(zs + eg * (bm - b0 + s), 2),
                         "makas_ust_boy_cm": round(egik, 2), "makas_yuksekligi_cm": round(top + eg * (bm - b0 + s), 2),
                         "makaslar": [{"konum": round(x, 2), "rol": r} for x, r in sorted(zip(yer, roller))],
                         "makas_yeri": "pano ekleri" if duzenli else "eşit aralık",
                         "komsu": None if i == k else adlar[i + 1 if i < k else i - 1]})

    # aynı düzlemdeki bitişik yüzler birleşir (ön saçak tek hat)
    gruplar: list[dict] = []
    for d in sorted(ham, key=lambda d: d["serit"] != k):                 # ana çatının yüzleri önce: birleşen düzlem onun adını alır
        anahtar = (tuple(d["yukari"]), tuple(d["sacak"].items()))
        for g in gruplar:
            if g["anahtar"] == anahtar:
                u = unary_union([g["cokgen"], Polygon(d["plan"])])
                if u.geom_type == "Polygon":
                    g["cokgen"] = u
                    g["uyeler"].append(d["ad"])
                    break
        else:
            gruplar.append({"anahtar": anahtar, "cokgen": Polygon(d["plan"]), "uyeler": [d["ad"]], "d": d})
    ad_of, duzlemler = {}, []
    for g in sorted(gruplar, key=lambda g: g["d"]["serit"] == k):        # çizim sırası: cumba yüzleri önce, ana çatınınkiler üstte
        d = g["d"]
        pl = [[round(x, 4), round(y, 4)] for x, y in g["cokgen"].simplify(TOL).exterior.coords[:-1]]
        duzlemler.append({"ad": d["ad"], "plan": pl, "yukari": d["yukari"], "egim": eg, "sacak_kotu": zs, "sacak": d["sacak"],
                          **({"birlesen": g["uyeler"]} if len(g["uyeler"]) > 1 else {})})
        for u in g["uyeler"]:
            ad_of[u] = d["ad"]

    def yuzleri(i):
        return sorted({ad_of[f"{adlar[i]} {y}"] for y in yuz_adi})

    def birlesmemis(j, i):
        """j şeridinin, i şeridinin yüzüyle birleşmemiş yüzleri (birleşende iki çatı aynı düzlemde: arada kalkan yok)."""
        return sorted({ad_of[f"{adlar[j]} {y}"] for y in yuz_adi} - set(yuzleri(i)))

    kalkanlar = []
    ic_adi = {("y", 1): "dogu", ("y", -1): "bati", ("x", 1): "kuzey", ("x", -1): "guney"}
    for i, (a0, a1, b0, b1) in enumerate(sr):
        for uc, konum, ic, j in ((0, a0, 1, i - 1), (1, a1, -1, i + 1)):
            komsu = sr[j] if 0 <= j < len(sr) else None
            if komsu is not None and abs(j - k) < abs(i - k):
                continue                                                  # cumbanın iç ucu: komşu yüksek, kalkan yok
            ad = f"{adlar[i]} {('sol', 'sağ')[uc] if eksen == 'y' else ('ön', 'arka')[uc]} kalkanı"
            temel = {"eksen": "x" if eksen == "y" else "y", "konum": konum, "ic": ic_adi[(eksen, ic)], "ust": yuzleri(i)}
            if komsu is None:
                kalkanlar.append({"ad": ad, **temel, "aralik": [b0, b1]})
                continue
            lo, hi = max(b0, komsu[2] - s), min(b1, komsu[3] + s)       # komşunun saçaklı açıklığı: kalkan onun çatısının üstünde
            kalkanlar.append({"ad": ad, **temel, "aralik": [lo, hi], "alt": birlesmemis(j, i)})
            for r0, r1 in ((b0, lo), (hi, b1)):
                if r1 - r0 > TOL:
                    kalkanlar.append({"ad": f"{ad} ({r0:g}–{r1:g})", **temel, "aralik": [r0, r1]})
    if mc:
        _mahal_cati_denetle(mc, duzlemler)
    return {"tip": "besik", "tip_adi": "beşik: ana çatı + paralel cumba", "sacak": s, "topuk": top, "duvar_ustu": H0, "duzlemler": duzlemler,
            "kalkanlar": kalkanlar, "parcalar": parcalar, "uyarilar": uyarilar, **({"mahal_catilari": mc} if mc else {})}
