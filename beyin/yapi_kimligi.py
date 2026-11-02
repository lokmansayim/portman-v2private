"""İE-23 PR-1 · Yapı kimliği (`portman.yapi_kimligi/0.1`): bir yapının makinenin okuyacağı kimliği, koddan.

Dört katman:
- anlamsal: ne (oda programı, ölçüler, çatı; her mahalin işlevi, alanı, cepheleri, pencereleri ve kapıları)
- topolojik: nasıl bağlı (mahal ve dış düğümleri; ortak duvar, kapı ve açık sınır kenarları; girişten derinlik; işlev etiketli imza)
- parametrik: ne oynar (her mahalin dört yanındaki kenarlar ve arkalarında ne olduğu; germe bantları ve çatı düzeyi; ön bilgi olarak
  oynar / düzey 2 / kilitli ve gerekçesi)
- sayısal: benzerlik ve istatistik için oranlar

Kimlik karar vermez: LLM'e giden tablonun ve uygulayıcının haritasıdır; kararı denetçi verir (İE-23 › Amaç; D-28 m.4). LLM yok, aynı
girdi aynı kimliği verir. İki kaynak:
- `tanimdan`: çelik Yapı Tanımı 0.5 (banka modeli). Kesin: mahaller `yapi.kur` bölgeleri, komşuluk duvar yüzlerinden, kapı ve pencere
  açıklığın duvarının iki yanındaki bölgelerden; koordinatlar tanımın kendi ekseninde (cm, +x doğu, +y kuzey).
- `plandan`: ortak plan sözleşmesi `portman.plan/0.1` (İE-14 planı; eski biçim prefabrik İş Emri `plan_adaptor.prefabrik_oku` ile).
  Dikdörtgenlerden, yaklaşık: alan dış yüzden ya da pano aksından, net değil; germe bandı yok (uygulayıcı `plan_islem` ya da yok).

Germe (İE-23 PR-2'nin işlemi): bir eksene dik kesit çizgisinin ötesi cm kadar kayar. Kesit bir duvarın kalınlığından, kolondan, dik
kirişten ve kestiği duvardaki açıklıktan geçemez (`KESIT_PAYI`). Kesitin kestiği çatı düzlemlerine göre düzey:
1 · bütün düzlemlerin eğim yönü kesite paralel (düzlem uzar, kotlar değişmez);
2 · eğimi kesit eksenindeki düzlemler yalnız ikincil çatı parçalarında; o parça yeniden hesaplanır;
3 · ana çatının eğimi kesit ekseninde: açıklık ve mahya kotu değişir. Başta kilitli (İE-23 › 4.2 C).
Çatı parçası: sırt ya da kırma çizgisiyle (iki düzlem de çizgiye doğru yükselir) ya da aynı düzlem olarak birleşen düzlemler; vadi
parçaları ayırır. Tepesi en yüksek tepeye eşit (1 cm) parçalar ana çatıdır; öbürleri ikincil (cumba, çıkma, sundurma, veranda çatısı).
Veranda bu işte değişmez: veranda mahalinin kenarları, verandaya bakan kenar ve verandayı da kesen kesit kilitlidir.

Kullanım: python -m beyin.yapi_kimligi modeller/C8801.json [--cikti kimlik.json] [--gorsel kimlik.png] [--set kurallar/liste/setler/0.19.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

from beyin.celik import tanim_sha_icerik

SEMA = "portman.yapi_kimligi/0.1"
DIS = "dis"
YONLER = ("G", "K", "B", "D")
YON_ADI = {"G": "ön (güney)", "K": "arka (kuzey)", "B": "sol (batı)", "D": "sağ (doğu)"}
YON_EKSEN = {"G": "y", "K": "y", "B": "x", "D": "x"}
# mahal duvarın bu yanındaysa (yüzün `kenar`ı) duvar mahalin şu yanındadır: mahal duvarın üstündeyse (ust) duvar mahalin güneyinde
KENAR_YON = {"ust": "G", "alt": "K", "sag": "B", "sol": "D"}
KARSI = {"ust": "alt", "alt": "ust", "sol": "sag", "sag": "sol"}
KESIT_PAYI = 5.0            # cm; kesit duvar yüzüne, kolona, dik kirişe ve açıklık kenarına bundan yakın geçmez
ANA_TEPE_PAYI = 1.0         # cm; çatı parçasının tepesi en yüksek tepeden bundan az alçaksa ana çatıdır
HIZA_PAYI = 10.0            # cm; komşunun bu kadar kaçık duvar yüzü aynı hizada sayılır (iç kenarın kilidi)
WL_TUR = 3                  # imza: Weisfeiler–Lehman yineleme sayısı
ISLEV_SIRA = ("salon", "mutfak", "yatak_odasi", "banyo", "hol", "depo", "veranda")
DIKDORTGEN_ORANI = 0.97     # net alan çevreleyen dikdörtgenin bu oranındaysa mahal dikdörtgen sayılır (kaplama ve kolon çentikleri sayılmaz)


def _r(v: float, n: int = 1) -> float:
    x = round(float(v), n)
    return 0.0 if x == 0 else x


def _islak_mi(m: dict) -> bool:
    """Islak hacim: tanımdaki `islak` işareti ya da banyo işlevi (kimlikte ve ıslak oranında aynı ölçü)."""
    return bool(m.get("islak")) or "banyo" in (m.get("islev") or [])


def _ortusme(a: list, b: list) -> float:
    return sum(max(0.0, min(a1, b1) - max(a0, b0)) for a0, a1 in a for b0, b1 in b)


def _etiket(islev: list | None, sinif: str | None) -> str:
    if sinif == DIS:
        return DIS
    for i in ISLEV_SIRA:
        if i in (islev or []):
            return i
    return (islev or [sinif or "depo"])[0]


# ── topoloji (iki kaynakta ortak) ───────────────────────────────────────────────────────────────────────────────────────
def _topoloji(dugumler: dict[str, str], kenarlar: list[dict]) -> dict:
    """dugumler: ad → işlev etiketi (DIS dahil). kenarlar: {a, b, ortak_duvar_cm, kapilar, acik}. Geçiş kenarı: kapı ya da açık sınır."""
    gecis: dict[str, set[str]] = {a: set() for a in dugumler}
    for k in kenarlar:
        if k["kapilar"] or k["acik"]:
            gecis[k["a"]].add(k["b"])
            gecis[k["b"]].add(k["a"])
    derinlik = {DIS: 0}
    sira = [DIS]
    while sira:
        u = sira.pop(0)
        for v in sorted(gecis[u]):
            if v not in derinlik:
                derinlik[v] = derinlik[u] + 1
                sira.append(v)
    # düzen: girişten sonraki en çok kapılı iç mahal (dış ve veranda hariç); en az üç odaya açılıyorsa "<işlev>_merkezli"
    ic = [a for a, e in dugumler.items() if e not in (DIS, "veranda")]
    kapi_derece = {a: sum(1 for k in kenarlar if k["kapilar"] and a in (k["a"], k["b"]) and dugumler[k["b"] if k["a"] == a else k["a"]] not in (DIS, "veranda"))
                   for a in ic}
    merkez = max(sorted(ic), key=lambda a: (kapi_derece[a], -ISLEV_SIRA.index(dugumler[a]) if dugumler[a] in ISLEV_SIRA else -99)) if ic else None
    duzen = f"{dugumler[merkez]}_merkezli" if merkez and kapi_derece[merkez] >= 3 else "zincir"
    return {"derinlik": {a: derinlik.get(a) for a in sorted(dugumler) if a != DIS}, "ulasilamayan": sorted(a for a in dugumler if a not in derinlik),
            "merkez": merkez, "duzen": duzen, "imza": imza(dugumler, kenarlar)}


def imza(dugumler: dict[str, str], kenarlar: list[dict]) -> str:
    """Ad bağımsız topolojik imza: işlev etiketli grafiğin Weisfeiler–Lehman özeti (kenar türü: kapı, açık, duvar). Adları farklı iki
    model aynı bağlantıdaysa imzaları aynıdır; uzunluklar imzaya girmez."""
    komsu: dict[str, list[tuple[str, str]]] = {a: [] for a in dugumler}
    for k in kenarlar:
        tur = "kapi" if k["kapilar"] else "acik" if k["acik"] else "duvar"
        komsu[k["a"]].append((tur, k["b"]))
        komsu[k["b"]].append((tur, k["a"]))
    et = dict(dugumler)
    ozet = [sorted(et.values())]
    for _ in range(WL_TUR):
        et = {a: hashlib.sha256((et[a] + "|" + ",".join(sorted(f"{t}:{et[b]}" for t, b in komsu[a]))).encode()).hexdigest()[:12] for a in sorted(et)}
        ozet.append(sorted(et.values()))
    return hashlib.sha256(json.dumps(ozet).encode()).hexdigest()[:16]


# ── çelik Yapı Tanımı ───────────────────────────────────────────────────────────────────────────────────────────────────
def _yuz_cizgisi(kutu, kenar: str) -> float:
    return {"alt": kutu[1], "ust": kutu[3], "sol": kutu[0], "sag": kutu[2]}[kenar]


def _tepe(d: dict) -> float | None:
    """Düzlemin en yüksek noktasının kotu (cm): saçak kotu + eğim × saçak çizgisinden yukarı en uzak köşe."""
    u = d.get("yukari") or [0, 0]
    ax = 0 if abs(u[0]) > 0.5 else 1 if abs(u[1]) > 0.5 else None
    s = (d.get("sacak") or {}).get("xy"[ax]) if ax is not None else None
    if s is None or d.get("sacak_kotu") is None:
        return None
    return float(d["sacak_kotu"]) + float(d["egim"]) * (max(v[ax] * u[ax] for v in d["plan"]) - s * u[ax])


def cati_parcalari(duzlemler: list[dict]) -> list[dict]:
    """Çatı düzlemlerini parçalara ayırır: ortak kenarında iki düzlem de kenara doğru yükseliyorsa (sırt, kırma) ya da ikisi aynı
    düzlemse aynı parça; vadi ayırır. Tepesi en yüksek tepeye eşit parça ana çatıdır. Tepesi bilinmeyen düzlemin parçası ana sayılır
    (temkinli: yanlış "ikincil" PR-2'de ana çatıyı değiştirirdi)."""
    from shapely.geometry import Point, Polygon
    P = [Polygon(d["plan"]) for d in duzlemler]
    ata = list(range(len(duzlemler)))

    def kok(i: int) -> int:
        while ata[i] != i:
            i = ata[i]
        return i

    def iceri_yukari(p, parca, u) -> float:              # kenardan düzlemin içine doğru adımın yukarı bileşeni (< 0: kenar tepede)
        (x0, y0), (x1, y1) = parca.coords[0], parca.coords[-1]
        L = math.hypot(x1 - x0, y1 - y0)
        n = (-(y1 - y0) / L, (x1 - x0) / L)
        m = parca.interpolate(0.5, normalized=True)
        if not p.contains(Point(m.x + 2 * n[0], m.y + 2 * n[1])):
            n = (-n[0], -n[1])
        return n[0] * u[0] + n[1] * u[1]
    for i, a in enumerate(duzlemler):
        for j in range(i + 1, len(duzlemler)):
            b = duzlemler[j]
            ayni = (a.get("yukari") == b.get("yukari") and a.get("egim") == b.get("egim") and a.get("sacak_kotu") == b.get("sacak_kotu")
                    and a.get("sacak") == b.get("sacak"))
            sirt = False
            ortak = P[i].boundary.intersection(P[j].boundary)
            if ortak.length > KESIT_PAYI and a.get("yukari") and b.get("yukari"):
                parca = max((g for g in getattr(ortak, "geoms", [ortak]) if g.length > 0), key=lambda g: g.length)
                sirt = iceri_yukari(P[i], parca, a["yukari"]) < -1e-6 and iceri_yukari(P[j], parca, b["yukari"]) < -1e-6
            if ayni or sirt:
                ata[kok(i)] = kok(j)
    gruplar: dict[int, list[int]] = {}
    for i in range(len(duzlemler)):
        gruplar.setdefault(kok(i), []).append(i)
    tepeler = [_tepe(d) for d in duzlemler]
    en_yuksek = max((v for v in tepeler if v is not None), default=None)
    out = []
    for g in sorted(gruplar.values()):
        tp = [tepeler[i] for i in g]
        tepe = None if any(v is None for v in tp) else max(tp)
        out.append({"duzlemler": [duzlemler[i]["ad"] for i in g], "tepe_cm": _r(tepe) if tepe is not None else None,
                    "ana": tepe is None or en_yuksek is None or tepe >= en_yuksek - ANA_TEPE_PAYI})
    return out


def _germe(y: dict, t: dict, eksen: str) -> list[dict]:
    """Eksene dik kesitin konabileceği bantlar; her bandın kestiği mahaller, çatı düzlemleri ve düzeyi. Komşu ve özdeş bantlar birleşir."""
    from shapely.geometry import LineString, Polygon
    i0, i1 = (0, 2) if eksen == "x" else (1, 3)
    j0, j1 = (1, 3) if eksen == "x" else (0, 2)
    govde = [d["kutu"] for d in y["duvarlar"] if d["sinif"] in ("dis", "ic", "ek")]
    lo, hi = min(k[i0] for k in govde), max(k[i1] for k in govde)
    yasak = []
    for d in y["duvarlar"]:                                   # kesit duvarın kalınlığından ya da kolondan geçemez
        if d["sinif"] == "kolon" or d["yon"] != eksen:
            yasak.append((d["kutu"][i0] - KESIT_PAYI, d["kutu"][i1] + KESIT_PAYI))
    for kr in t.get("kirisler") or []:
        k = kr["kutu"]
        if ("x" if k[2] - k[0] >= k[3] - k[1] else "y") != eksen:
            yasak.append((k[i0] - KESIT_PAYI, k[i1] + KESIT_PAYI))
    for ac in y["acikliklar"]:                                # kestiği duvardaki açıklıktan geçemez
        if y["adli"][ac["duvar"]]["yon"] == eksen:
            yasak.append((ac["a0"] - KESIT_PAYI, ac["a1"] + KESIT_PAYI))
    duzlemler = [(d["ad"], Polygon(d["plan"]), d.get("yukari") or [0, 0]) for d in t["cati"].get("duzlemler") or []]
    ana = {ad for p in cati_parcalari(t["cati"].get("duzlemler") or []) if p["ana"] for ad in p["duzlemler"]}
    bolgeler = [(ad, b["net"]) for ad, b in y["bolgeler"].items() if b["sinif"] != DIS]
    olay = {lo, hi} | {v for a, b in yasak for v in (a, b) if lo < v < hi}
    for _, p, _ in duzlemler:
        olay |= {v for v in (p.bounds[i0], p.bounds[i1]) if lo < v < hi}
    for _, g in bolgeler:
        olay |= {v for v in (g.bounds[i0], g.bounds[i1]) if lo < v < hi}
    olay = sorted(olay)
    uz0 = min(k[j0] for k in govde) - 1000
    uz1 = max(k[j1] for k in govde) + 1000
    out: list[dict] = []
    for s0, s1 in zip(olay, olay[1:]):
        if s1 - s0 < 0.5:
            continue
        m = (s0 + s1) / 2
        if any(a < m < b for a, b in yasak):
            continue
        cizgi = LineString([(m, uz0), (m, uz1)] if eksen == "x" else [(uz0, m), (uz1, m)])
        mah = sorted(ad for ad, g in bolgeler if g.intersection(cizgi).length > 1)
        paralel, dik, ana_dik = [], [], False
        for ad, p, yk in duzlemler:
            if p.intersection(cizgi).length <= 1:
                continue
            bilesen = yk[0] if eksen == "x" else yk[1]
            if abs(bilesen) < 1e-6:
                paralel.append(ad)
            else:
                dik.append(ad)
                ana_dik = ana_dik or ad in ana
        e = {"aralik": [_r(s0), _r(s1)], "mahaller": mah, "paralel": sorted(paralel), "dik": sorted(dik), "duzey": 3 if ana_dik else 2 if dik else 1}
        o = out[-1] if out else None
        if o and o["aralik"][1] == e["aralik"][0] and all(o[k] == e[k] for k in ("mahaller", "paralel", "dik", "duzey")):
            o["aralik"][1] = e["aralik"][1]
        else:
            out.append(e)
    return out


def tanimdan(t: dict, set_yolu: str | Path | None = None) -> dict:
    """Çelik Yapı Tanımı 0.5 → yapı kimliği. `set_yolu`: alan ölçümlerinin (metraj) kural seti; verilmezse güncel kitap."""
    from motor.genel import cati_genel, girdi_genel, kural, yapi
    from motor.genel.bayi_gorseli import oda_programi
    with kural.secili(set_yolu):
        kur = kural.oku()
        y = yapi.kur(t)
        c = cati_genel.cati_kur(t["cati"], kur)
        m = girdi_genel.metraj(y, c, kur)
        set_adi = kural.yol().name
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    ad_ = lambda b: DIS if b == "(dış)" else b                          # noqa: E731
    bol = {ad: b for ad, b in y["bolgeler"].items() if b["sinif"] != "dis"}
    sinif = {ad: b["sinif"] for ad, b in bol.items()}

    # yüzler ve karşı yanları (aynı duvarın öbür kenarındaki bölgeler, örtüşme boyuyla)
    yuzler = [f for f in y["yuzler"] if f["uzun"] and f["sinif"] != "kolon"]
    duvar_yuz: dict[tuple[str, str], list[dict]] = {}
    for f in yuzler:
        duvar_yuz.setdefault((f["duvar"], f["kenar"]), []).append(f)
    for f in yuzler:
        f["_cizgi"] = _yuz_cizgisi(y["adli"][f["duvar"]]["kutu"], f["kenar"])
        f["_karsi"] = {}
        for g in duvar_yuz.get((f["duvar"], KARSI[f["kenar"]]), []):
            L = _ortusme(f["araliklar"], g["araliklar"])
            if L > 1 and g["bolge"] != f["bolge"]:
                f["_karsi"][ad_(g["bolge"])] = f["_karsi"].get(ad_(g["bolge"]), 0.0) + L

    # komşuluk (her çift bir kez: alt/sol yüzden)
    ciftler: dict[tuple[str, str], dict] = {}

    def cift(a: str, b: str) -> dict:
        k = tuple(sorted((a, b)))
        return ciftler.setdefault(k, {"a": k[0], "b": k[1], "ortak_duvar_cm": 0.0, "duvarlar": set(), "kapilar": [], "pencereler": [], "acik": False})
    for f in yuzler:
        if f["kenar"] not in ("alt", "sol"):
            continue
        for b, L in f["_karsi"].items():
            e = cift(ad_(f["bolge"]), b)
            e["ortak_duvar_cm"] += L
            e["duvarlar"].add(f["duvar"])

    # açıklıklar: duvarın iki yanında, açıklık aralığıyla en çok örtüşen bölgeler
    mahal_kapi: dict[str, list[str]] = {a: [] for a in bol}
    mahal_pencere: dict[str, list[dict]] = {a: [] for a in bol}
    eslesmeyen: list[str] = []
    for ac in y["acikliklar"]:
        yan = {}
        for f in yuzler:
            if f["duvar"] != ac["duvar"]:
                continue
            L = _ortusme(f["araliklar"], [(ac["a0"], ac["a1"])])
            if L > 1 and L > yan.get(f["kenar"], ("", 0.0))[1]:
                yan[f["kenar"]] = (ad_(f["bolge"]), L)
        iki = sorted(((k, v[0]) for k, v in yan.items()), key=lambda kv: kv[0])
        if len(iki) != 2 or iki[0][1] == iki[1][1]:
            eslesmeyen.append(str(ac.get("ad")))
            continue
        (k1, b1), (k2, b2) = iki
        if ac["tur"] == "pencere":
            oda_k, oda, dis = (k1, b1, b2) if b1 in bol and sinif.get(b1) != "veranda" else (k2, b2, b1)
            if oda not in bol:
                eslesmeyen.append(str(ac.get("ad")))
                continue
            p = {"ad": ac.get("ad"), "cephe": KENAR_YON[oda_k], "olcu": f"{_r(ac['en'], 0):g}x{_r(ac['yuk'], 0):g}",
                 "disi": DIS if dis == DIS else "veranda" if sinif.get(dis) == "veranda" else "ic"}
            if ac.get("acilis"):
                p["acilis"] = ac["acilis"]
            mahal_pencere[oda].append(p)
            cift(b1, b2)["pencereler"].append(ac.get("ad"))
        else:
            cift(b1, b2)["kapilar"].append(ac.get("ad"))
            for b in (b1, b2):
                if b in mahal_kapi:
                    mahal_kapi[b].append(ac.get("ad"))
    for ad, b in bol.items():                                 # duvarsız (açık) sınır: dışa açık veranda
        if b.get("acik_kenar_cm", 0) > 1 or b.get("poligon"):
            cift(ad, DIS)["acik"] = True
    kenarlar = []
    for k in sorted(ciftler):
        e = ciftler[k]
        e["ortak_duvar_cm"] = _r(e["ortak_duvar_cm"])
        e["duvarlar"] = sorted(e["duvarlar"])
        e["kapilar"] = sorted(e["kapilar"])
        e["pencereler"] = sorted(e["pencereler"])
        kenarlar.append(e)

    dugum = {ad: _etiket(b.get("islev"), b["sinif"]) for ad, b in bol.items()}
    dugum[DIS] = DIS
    topo = _topoloji(dugum, kenarlar)

    # parametrik: her mahalin dört yanındaki kenarlar
    germe = {e: _germe(y, t, e) for e in ("x", "y")}
    p_kenarlar = []
    for ad, b in bol.items():
        gruplar: dict[tuple[str, float], list[dict]] = {}
        for f in yuzler:
            if f["bolge"] == ad:
                gruplar.setdefault((KENAR_YON[f["kenar"]], _r(f["_cizgi"])), []).append(f)
        uc = {}
        for yon, konum in gruplar:
            uc[yon] = (min if yon in ("G", "B") else max)(konum, uc.get(yon, konum))
        for (yon, konum) in sorted(gruplar, key=lambda k: (YONLER.index(k[0]), k[1])):
            fs = gruplar[(yon, konum)]
            arkasi: dict[str, float] = {}
            for f in fs:
                for bb, L in f["_karsi"].items():
                    arkasi[bb] = arkasi.get(bb, 0.0) + L
            araliklar = [r for f in fs for r in f["araliklar"]]
            a0, a1 = min(r[0] for r in araliklar), max(r[1] for r in araliklar)
            turler = {DIS if bb == DIS else "veranda" if sinif.get(bb) == "veranda" else "ic" for bb in arkasi}
            tur = turler.pop() if len(turler) == 1 else "karisik" if turler else "yok"
            duvarlar = sorted({f["duvar"] for f in fs})
            e = {"mahal": ad, "yon": yon, "konum_cm": konum, "aralik": [_r(a0), _r(a1)], "uzunluk_cm": _r(sum(r[1] - r[0] for r in araliklar)),
                 "en_dis": konum == uc[yon], "tur": tur, "duvarlar": duvarlar, "arkasi": {k: _r(v) for k, v in sorted(arkasi.items())}}
            e.update(_kenar_durumu(e, ad, b, fs, yuzler, germe, sinif))
            p_kenarlar.append(e)

    # anlamsal
    mahaller = []
    for ad, b in bol.items():
        x0, y0, x1, y1 = b["net"].bounds
        cep = {p["yon"] for p in p_kenarlar if p["mahal"] == ad and DIS in p["arkasi"]}
        for eks, sabit, g0, g1 in b.get("_acik") or []:          # duvarsız (açık) kenar dışa bakar: veranda
            if g1 - g0 > 1:
                cep.add(("G" if abs(sabit - y0) <= abs(sabit - y1) else "K") if eks == "x" else ("B" if abs(sabit - x0) <= abs(sabit - x1) else "D"))
        cep = sorted(cep, key=YONLER.index)
        ver = sorted({p["yon"] for p in p_kenarlar if p["mahal"] == ad and any(sinif.get(k) == "veranda" for k in p["arkasi"])}, key=YONLER.index)
        rp = b["net"].representative_point()
        mahaller.append({"ad": ad, "sinif": b["sinif"], "islev": list(b.get("islev") or []), "islak": _islak_mi(b),
                         "alan_m2": _r(b["alan_m2"], 2), "olcu_cm": [_r(x1 - x0), _r(y1 - y0)],
                         "bicim": "dikdortgen" if b["net"].area >= DIKDORTGEN_ORANI * (x1 - x0) * (y1 - y0) else "girintili",
                         "cepheler": cep, "verandaya": ver, "pencereler": sorted(mahal_pencere[ad], key=lambda p: (YONLER.index(p["cephe"]), str(p["ad"]))),
                         "kapilar": sorted(mahal_kapi[ad]), "nokta": [_r(rp.x), _r(rp.y)]})
    duz = t["cati"].get("duzlemler") or []
    ana = max(duz, key=lambda d: Polygon(d["plan"]).area) if duz else None
    mahya = None
    if ana and ana.get("yukari"):
        mahya = "x" if abs(ana["yukari"][0]) < 1e-6 else "y" if abs(ana["yukari"][1]) < 1e-6 else None
    veranda = float(m.get("veranda_m2") or 0)
    oturum = float(m["oturum_m2"])
    anlamsal = {"oda_programi": oda_programi(t), "dis_olcu_cm": [_r(v) for v in m["dis_olcu_cm"]], "oturum_m2": _r(oturum, 2),
                "kapali_m2": _r(oturum - veranda, 2), "veranda_m2": _r(veranda, 2),
                "cati": {"tip": t["cati"].get("tip"), "duzlem": len(duz), "yuzey_m2": _r(c["yuzey_m2"], 2), "mahya": mahya,
                         "egim": _r(ana["egim"], 4) if ana and ana.get("egim") is not None else None, "parcalar": cati_parcalari(duz)},
                "mahaller": mahaller}

    # sayısal
    hat = unary_union([Polygon(h.coords) for h in y["bolgeler"]["(dış)"]["net"].interiors])
    ic_net = sum(b["alan_m2"] for b in bol.values() if b["sinif"] != "veranda")
    islak = sum(b["alan_m2"] for b in bol.values() if _islak_mi(b))
    pencere_m2 = sum(a["en"] * a["yuk"] / 1e4 for a in y["acikliklar"] if a["tur"] == "pencere")
    sayisal = _sayisal(anlamsal, topo, kenarlar, hat.area / 1e4, hat.length / 100, ic_net, islak, pencere_m2,
                       dis_duvar_m=float(m.get("bina_cevre_m") or 0))
    return {"sema": SEMA, "kod": t.get("kod"), "ad": t.get("ad"), "aile": "tek_kat_celik",
            "kaynak": {"tur": "yapi_tanimi", "tanim_sha256": tanim_sha_icerik(t), "kural_seti": set_adi, "alan_olcusu": "net",
                       "koordinat": "tanımın ekseni, cm; +x doğu, +y kuzey"},
            "anlamsal": anlamsal,
            "topolojik": {"dugumler": [{"ad": a, "islev": dugum[a], "derinlik": topo["derinlik"].get(a, 0 if a == DIS else None)} for a in [DIS] + sorted(bol)],
                          "kenarlar": kenarlar, **{k: topo[k] for k in ("ulasilamayan", "merkez", "duzen", "imza")},
                          "eslesmeyen_acikliklar": sorted(eslesmeyen)},
            "parametrik": {"izgara_cm": 5, "uygulayici": "tanim_germe (İE-23 PR-2)", "kesit_payi_cm": KESIT_PAYI, "kenarlar": p_kenarlar,
                           "germe": germe, "sinirlar": "kurallar/plan/oda_kurallari.json"},
            "sayisal": sayisal}


def _kenar_durumu(e: dict, ad: str, b: dict, fs: list[dict], yuzler: list[dict], germe: dict, sinif: dict[str, str]) -> dict:
    """Kenarın ön bilgisi (kararı uygulayıcıdan sonra denetçi verir). Veranda bu işte değişmez. İç kenar: karşıdaki komşu aynı hizada
    (`HIZA_PAYI`) bu mahalden başka bir şeye de bakıyorsa duvar kaymaz (İE-14 `plan_islem` kuralı: komşu başka hizada devam ediyor);
    yalnız bu mahale bakıyorsa duvar kayar, komşu küçülür ya da büyür. Dış kenar: mahalin aralığında verandayı kesmeyen kesit bantlarının
    en iyi çatı düzeyi."""
    if sinif.get(ad) == "veranda":
        return {"durum": "kilitli", "neden": "verandanın kenarı: veranda ve çatısı değişir (İE-23 PR-2'de yok)"}
    if e["tur"] == "ic":
        bizim = {f["kenar"] for f in fs}
        tasan = {}
        for k in e["arkasi"]:
            hiza = [g["_cizgi"] for g in yuzler if g["bolge"] == k and g["duvar"] in e["duvarlar"] and KARSI[g["kenar"]] in bizim]
            for g in yuzler:
                if g["bolge"] != k or KARSI[g["kenar"]] not in bizim or not any(abs(g["_cizgi"] - h) <= HIZA_PAYI for h in hiza):
                    continue
                for bb, L in g["_karsi"].items():
                    if bb != ad and L > KESIT_PAYI:
                        tasan.setdefault(k, set()).add(bb)
        if tasan:
            return {"durum": "kilitli", "neden": "karşıdaki " + "; ".join(f"{k} bu kenarın ötesinde {', '.join(sorted(v))} yanında devam ediyor"
                                                                       for k, v in sorted(tasan.items()))}
        return {"durum": "oynar", "neden": "iç duvar kayar; karşıdaki " + ", ".join(sorted(e["arkasi"])) + " küçülür ya da büyür"}
    if e["tur"] == "veranda":
        return {"durum": "kilitli", "neden": "verandaya bakan kenar: veranda ve çatısı değişir (İE-23 PR-2'de yok)"}
    if e["tur"] != DIS:
        return {"durum": "kilitli", "neden": "kenarın arkasında birden çok tür var (" + ", ".join(sorted(e["arkasi"])) + ")" if e["tur"] == "karisik"
                else "kenarın arkası yok"}
    eksen = YON_EKSEN[e["yon"]]
    i0, i1 = (0, 2) if eksen == "x" else (1, 3)
    lo, hi = b["net"].bounds[i0], b["net"].bounds[i1]
    bant = [g for g in germe[eksen] if ad in g["mahaller"] and g["aralik"][1] > lo and g["aralik"][0] < hi]
    if not bant:
        return {"durum": "kilitli", "neden": "mahalin içinden kesit geçecek yer yok (açıklık, duvar ya da kolon)"}
    bant = [g for g in bant if not any(sinif.get(m) == "veranda" for m in g["mahaller"])]
    if not bant:
        return {"durum": "kilitli", "neden": "mahalin içinden geçen her kesit verandayı da keser: veranda ve çatısı değişir (İE-23 PR-2'de yok)"}
    d = min(g["duzey"] for g in bant)
    kesit: list[list[float]] = []                                       # uygulayıcı kesiti bu aralıklardan birine koyar (PR-2)
    for g in bant:
        if g["duzey"] != d:
            continue
        if kesit and kesit[-1][1] == g["aralik"][0]:
            kesit[-1] = [kesit[-1][0], g["aralik"][1]]
        else:
            kesit.append(list(g["aralik"]))
    if d == 1:
        return {"durum": "oynar", "neden": "ev bu yöne büyür; kesitin kestiği çatı düzlemleri mahyaya paralel", "kesit_bantlari": kesit}
    if d == 2:
        dik = sorted({x for g in bant if g["duzey"] == 2 for x in g["dik"]})
        return {"durum": "duzey2", "neden": "ev bu yöne büyür; ikincil çatı yeniden hesaplanır: " + ", ".join(dik), "kesit_bantlari": kesit}
    return {"durum": "kilitli", "neden": "ana çatının açıklığı ve mahya kotu değişir (düzey 3)", "kesit_bantlari": kesit}


def _sayisal(an: dict, topo: dict, kenarlar: list[dict], alan_m2: float, cevre_m: float, ic_net: float, islak: float, pencere_m2: float,
             dis_duvar_m: float) -> dict:
    W, H = an["dis_olcu_cm"]
    mah = an["mahaller"]
    der = [v for v in topo["derinlik"].values() if v is not None]
    return {"oturum_m2": an["oturum_m2"], "kapali_m2": an["kapali_m2"], "veranda_orani": _r(an["veranda_m2"] / an["oturum_m2"], 3) if an["oturum_m2"] else 0.0,
            "en_boy": _r(max(W, H) / min(W, H), 3), "kompaktlik": _r(4 * math.sqrt(alan_m2) / cevre_m, 3) if cevre_m else 0.0,
            "yatak": sum(1 for x in mah if "yatak_odasi" in x["islev"]), "banyo": sum(1 for x in mah if "banyo" in x["islev"]),
            "mahal": len(mah), "kapi": len({k for e in kenarlar for k in e["kapilar"]}), "pencere": sum(len(x["pencereler"]) for x in mah),
            "islak_orani": _r(islak / ic_net, 3) if ic_net else 0.0, "pencere_taban_orani": _r(pencere_m2 / ic_net, 3) if ic_net else 0.0,
            "dis_duvar_m_m2": _r(dis_duvar_m / an["oturum_m2"], 3) if an["oturum_m2"] and dis_duvar_m else None,
            "cati_yuzey_orani": _r(an["cati"]["yuzey_m2"] / an["oturum_m2"], 3) if an["oturum_m2"] and an["cati"].get("yuzey_m2") else None,
            "derinlik_en_cok": max(der) if der else 0, "derinlik_ortalama": _r(sum(der) / len(der), 2) if der else 0.0}


# ── ortak plan sözleşmesi (İE-14 planı, eski biçim prefabrik İş Emri) ─────────────────────────────────────────────────────
def plandan(soz: dict) -> dict:
    """Plan sözleşmesi → yapı kimliği (dikdörtgenlerden; alan dış yüzden ya da pano aksından). Germe bandı yok: çelik sözleşmede
    uygulayıcı `plan_islem`, prefabrikte yok (pano motorunda germe İE-23 dışında)."""
    from beyin.plan_sema import PlanSozlesmesi
    from motor.genel.bayi_gorseli import oda_programi
    s = PlanSozlesmesi.model_validate(soz).model_dump()
    W, H = float(s["dis_olcu"]["en"]), float(s["dis_olcu"]["boy"])
    mah = {m["ad"]: m for m in s["mahaller"]}
    rect = [(m["ad"], [float(v) for v in r]) for m in s["mahaller"] for r in m["dikdortgenler"]]
    ciftler: dict[tuple[str, str], dict] = {}

    def cift(a: str, b: str) -> dict:
        k = tuple(sorted((a, b)))
        return ciftler.setdefault(k, {"a": k[0], "b": k[1], "ortak_duvar_cm": 0.0, "duvarlar": [], "kapilar": [], "pencereler": [], "acik": False})
    # her dikdörtgenin dört kenarı: (yön, sabit, lo, hi); karşısındaki dikdörtgenler ya da dış
    kenar_par: dict[str, list[tuple[str, float, float, float, dict[str, float]]]] = {a: [] for a in mah}
    for ad, r in rect:
        for yon, sabit, lo, hi in (("G", r[1], r[0], r[2]), ("K", r[3], r[0], r[2]), ("B", r[0], r[1], r[3]), ("D", r[2], r[1], r[3])):
            arka: dict[str, float] = {}
            for ad2, q in rect:
                if q is r:
                    continue
                if yon in ("G", "K"):
                    dokun = abs((q[3] if yon == "G" else q[1]) - sabit) < 1e-6
                    L = max(0.0, min(hi, q[2]) - max(lo, q[0]))
                else:
                    dokun = abs((q[2] if yon == "B" else q[0]) - sabit) < 1e-6
                    L = max(0.0, min(hi, q[3]) - max(lo, q[1]))
                if dokun and L > 1e-6:
                    arka[ad2] = arka.get(ad2, 0.0) + L
            bos = (hi - lo) - sum(arka.values())             # hiçbir dikdörtgenin değmediği kalan dışarıdır (girinti ve çıkıntı dahil)
            if bos > 1e-6:
                arka[DIS] = arka.get(DIS, 0.0) + bos
            arka.pop(ad, None)                                  # aynı mahalin iki dikdörtgeni arasındaki sınır kenar değildir
            kenar_par[ad].append((yon, sabit, lo, hi, arka))
            for b, L in arka.items():
                if b == DIS or ad < b:
                    cift(ad, b)["ortak_duvar_cm"] += L
    acik = {tuple(sorted(x)) for x in s.get("acik_sinirlar") or []}
    for k in acik:
        if k in ciftler:
            ciftler[k]["acik"] = True
    mahal_kapi = {a: [] for a in mah}
    for i, kp in enumerate(s["kapilar"], 1):
        a, b = (list(kp["arasinda"]) + [DIS, DIS])[:2]
        if a not in mah and a != DIS or b not in mah and b != DIS:
            continue
        cift(a, b)["kapilar"].append(f"K{i}")
        for x in (a, b):
            if x in mahal_kapi:
                mahal_kapi[x].append(f"K{i}")
    for a, m in mah.items():                                  # verandaya dışarıdan kapısı yoksa açık kenarından girilir (sözleşmede korkuluk yok)
        if m["islev"] == "veranda" and not cift(a, DIS)["kapilar"]:
            cift(a, DIS)["acik"] = True
    p_kenarlar = []
    for a in mah:
        gr: dict[tuple[str, float], list] = {}
        for yon, sabit, lo, hi, arka in kenar_par[a]:
            if not arka:
                continue
            gr.setdefault((yon, _r(sabit)), []).append((lo, hi, arka))
        uc = {}
        for yon, konum in gr:
            uc[yon] = (min if yon in ("G", "B") else max)(konum, uc.get(yon, konum))
        for (yon, konum) in sorted(gr, key=lambda k: (YONLER.index(k[0]), k[1])):
            parca = gr[(yon, konum)]
            arka: dict[str, float] = {}
            for _, _, ak in parca:
                for b, L in ak.items():
                    arka[b] = arka.get(b, 0.0) + L
            turler = {DIS if b == DIS else "veranda" if mah[b]["islev"] == "veranda" else "ic" for b in arka}
            p_kenarlar.append({"mahal": a, "yon": yon, "konum_cm": konum, "aralik": [_r(min(x[0] for x in parca)), _r(max(x[1] for x in parca))],
                               "uzunluk_cm": _r(sum(x[1] - x[0] for x in parca)), "en_dis": konum == uc[yon],
                               "tur": turler.pop() if len(turler) == 1 else "karisik", "arkasi": {k: _r(v) for k, v in sorted(arka.items())}})
    # pencere: sözleşmede yalnız mahal ve cephe var (yeri yok). O cephenin arkası yalnız dışsa dışa, yalnız verandaysa verandaya bakar;
    # ikisi birdense belirsizdir ve topolojik kenara yazılmaz
    mahal_pencere = {a: [] for a in mah}
    eslesmeyen: list[str] = []
    for i, p in enumerate(s["pencereler"], 1):
        adet = int(p.get("adet") or 1)
        if p["mahal"] not in mah:
            eslesmeyen += [f"P{i}"]
            continue
        karsi = sorted({b for e in p_kenarlar if e["mahal"] == p["mahal"] and e["yon"] == p["cephe"] for b in e["arkasi"]
                        if b == DIS or mah[b]["islev"] == "veranda"})
        disi = None if not karsi else "belirsiz" if len(karsi) > 1 else DIS if karsi[0] == DIS else "veranda"
        for j in range(adet):
            ad = f"P{i}" + (f".{j + 1}" if adet > 1 else "")
            if disi is None:
                eslesmeyen.append(ad)
                continue
            mahal_pencere[p["mahal"]].append({"ad": ad, "cephe": p["cephe"], "olcu": p["olcu"], "disi": disi})
            if disi != "belirsiz":
                cift(p["mahal"], karsi[0])["pencereler"].append(ad)
    kenarlar = []
    for k in sorted(ciftler):
        e = ciftler[k]
        e["ortak_duvar_cm"] = _r(e["ortak_duvar_cm"])
        e["kapilar"] = sorted(e["kapilar"])
        e["pencereler"] = sorted(e["pencereler"])
        kenarlar.append(e)
    dugum = {a: _etiket([m["islev"]], "veranda" if m["islev"] == "veranda" else "ic") for a, m in mah.items()}
    dugum[DIS] = DIS
    topo = _topoloji(dugum, kenarlar)
    mahaller = []
    for a, m in mah.items():
        rs = m["dikdortgenler"]
        x0, y0 = min(r[0] for r in rs), min(r[1] for r in rs)
        x1, y1 = max(r[2] for r in rs), max(r[3] for r in rs)
        alan = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) / 1e4
        cep = sorted({p["yon"] for p in p_kenarlar if p["mahal"] == a and DIS in p["arkasi"]}, key=YONLER.index)
        ver = sorted({p["yon"] for p in p_kenarlar if p["mahal"] == a and any(k != DIS and mah[k]["islev"] == "veranda" for k in p["arkasi"])}, key=YONLER.index)
        en_buyuk = max(rs, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        mahaller.append({"ad": a, "sinif": "veranda" if m["islev"] == "veranda" else "ic", "islev": [m["islev"]], "islak": _islak_mi({"islev": [m["islev"]]}),
                         "alan_m2": _r(alan, 2), "olcu_cm": [_r(x1 - x0), _r(y1 - y0)], "bicim": "dikdortgen" if len(rs) == 1 else f"{len(rs)} dikdörtgen",
                         "cepheler": cep, "verandaya": ver, "pencereler": sorted(mahal_pencere[a], key=lambda p: (YONLER.index(p["cephe"]), p["ad"])),
                         "kapilar": sorted(mahal_kapi[a]), "nokta": [_r((en_buyuk[0] + en_buyuk[2]) / 2), _r((en_buyuk[1] + en_buyuk[3]) / 2)]})
    veranda = sum(x["alan_m2"] for x in mahaller if x["sinif"] == "veranda")
    from shapely.geometry import box
    from shapely.ops import unary_union
    hat = unary_union([box(*r) for _, r in rect])               # girintili cephede oturum dış kutu değil, mahallerin birleşimi
    oturum = hat.area / 1e4
    ct = s.get("cati") or {}
    anlamsal = {"oda_programi": oda_programi({"mahaller": [{"ad": x["ad"], "islev": x["islev"]} for x in mahaller]}),
                "dis_olcu_cm": [_r(W), _r(H)], "oturum_m2": _r(oturum, 2), "kapali_m2": _r(oturum - veranda, 2), "veranda_m2": _r(veranda, 2),
                "cati": {"tip": ct.get("tip"), "duzlem": None, "yuzey_m2": None, "mahya": ct.get("mahya_yonu"),
                         "egim": _r(ct["egim_yuzde"] / 100, 4) if ct.get("egim_yuzde") else None},
                "mahaller": mahaller}
    ic = sum(x["alan_m2"] for x in mahaller if x["sinif"] != "veranda")
    islak = sum(x["alan_m2"] for x in mahaller if x["islak"])
    pen = sum(int(o.split("x")[0]) * int(o.split("x")[1]) / 1e4 for x in mahaller for o in (p["olcu"] for p in x["pencereler"]))
    sayisal = _sayisal(anlamsal, topo, kenarlar, oturum, hat.length / 100, ic, islak, pen, dis_duvar_m=0.0)
    celik = s["aile"] == "tek_kat_celik"
    return {"sema": SEMA, "kod": (s.get("kaynak") or {}).get("kod"), "ad": None, "aile": s["aile"],
            "kaynak": {"tur": "plan_sozlesmesi", "tanim_sha256": tanim_sha_icerik(soz), "kural_seti": s.get("kural_seti"),
                       "alan_olcusu": "dikdortgen" if s["olcu_kaynagi"] == "dis_yuz" else "pano_aksi",
                       "koordinat": "dış yüzden, cm" if s["olcu_kaynagi"] == "dis_yuz" else "pano aksından, cm"},
            "anlamsal": anlamsal,
            "topolojik": {"dugumler": [{"ad": a, "islev": dugum[a], "derinlik": topo["derinlik"].get(a, 0 if a == DIS else None)} for a in [DIS] + sorted(mah)],
                          "kenarlar": kenarlar, **{k: topo[k] for k in ("ulasilamayan", "merkez", "duzen", "imza")},
                          "eslesmeyen_acikliklar": sorted(eslesmeyen)},
            "parametrik": {"izgara_cm": s["izgara_cm"], "uygulayici": "plan_islem (İE-14)" if celik else "yok (pano motorunda germe İE-23 dışında)",
                           "kenarlar": p_kenarlar, "germe": None, "sinirlar": "kurallar/plan/oda_kurallari.json"},
            "sayisal": sayisal}


# ── görsel (Patron'un ve CIO'nun baktığı çıktı; altın değil) ─────────────────────────────────────────────────────────────
RENK_ISLEV = {"salon": "#f4e3c1", "mutfak": "#f6d8b8", "yatak_odasi": "#d9e7f5", "banyo": "#d4efe9", "hol": "#ececec", "depo": "#e6dff0",
              "veranda": "#e3efd3"}
RENK_DURUM = {"oynar": "#2e8b57", "duzey2": "#e08a1e", "kilitli": "#c0392b"}


def gorsel(kaynak: dict, yol: str | Path, kimlik: dict | None = None, set_yolu: str | Path | None = None) -> Path:
    """İki panel: topoloji (oda grafiği; düz çizgi kapı, kesikli çizgi kapısız ortak duvar, dış düğüm planın altında) ve parametrik
    (kenarlar ön bilgi rengiyle; plan kenarında germe bantları düzey rengiyle)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly, Rectangle
    tanim_mi = "duvarlar" in kaynak
    k = kimlik or (tanimdan(kaynak, set_yolu) if tanim_mi else plandan(kaynak))
    sekiller: dict[str, list] = {}
    duvar_kutulari = []
    if tanim_mi:
        from motor.genel import kural, yapi
        with kural.secili(set_yolu):
            y = yapi.kur(kaynak)
        for ad, b in y["bolgeler"].items():
            if b["sinif"] == "dis":
                continue
            g = b["net"]
            sekiller[ad] = [list(p.exterior.coords) for p in (g.geoms if g.geom_type == "MultiPolygon" else [g])]
        duvar_kutulari = [d["kutu"] for d in kaynak["duvarlar"]]
    else:
        for m in kaynak["mahaller"]:
            sekiller[m["ad"]] = [[(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])] for r in m["dikdortgenler"]]
    xs = [p[0] for v in sekiller.values() for s in v for p in s] + [q for b in duvar_kutulari for q in (b[0], b[2])]
    ys = [p[1] for v in sekiller.values() for s in v for p in s] + [q for b in duvar_kutulari for q in (b[1], b[3])]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    islev = {m["ad"]: _etiket(m["islev"], m["sinif"]) for m in k["anlamsal"]["mahaller"]}
    nokta = {m["ad"]: m["nokta"] for m in k["anlamsal"]["mahaller"]}
    derin = {d["ad"]: d["derinlik"] for d in k["topolojik"]["dugumler"]}
    dis_n = [(x0 + x1) / 2, y0 - 0.28 * (y1 - y0)]
    genis = (x1 - x0) >= (y1 - y0)
    fig, axs = plt.subplots(2 if genis else 1, 1 if genis else 2, figsize=(13, 13) if genis else (16, 10))

    def zemin(ax):
        for ad, ss in sekiller.items():
            for s in ss:
                ax.add_patch(MPoly(s, closed=True, facecolor=RENK_ISLEV.get(islev.get(ad), "#eeeeee"), edgecolor="#999999", lw=0.6))
        for b in duvar_kutulari:
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], facecolor="#555555", edgecolor="none"))
        ax.set_aspect("equal")
        ax.axis("off")
    ax = axs[0]
    zemin(ax)
    for e in k["topolojik"]["kenarlar"]:
        a = dis_n if e["a"] == DIS else nokta.get(e["a"])
        b = dis_n if e["b"] == DIS else nokta.get(e["b"])
        if a is None or b is None:
            continue
        if e["kapilar"] or e["acik"]:
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#1f5f93", lw=2.4, zorder=5, solid_capstyle="round")
        elif e["a"] != DIS and e["b"] != DIS:
            ax.plot([a[0], b[0]], [a[1], b[1]], color="#888888", lw=1.0, ls=(0, (3, 3)), zorder=4)
    for ad, p in list(nokta.items()) + [(DIS, dis_n)]:
        ax.plot(*p, "o", ms=9, color="#1f5f93" if ad != DIS else "#333333", zorder=6)
        ax.text(p[0], p[1] - 0.035 * (y1 - y0), f"{ad if ad != DIS else 'DIŞ'}\n{'derinlik ' + str(derin.get(ad)) if ad != DIS else 'giriş 0'}",
                ha="center", va="top", fontsize=8, zorder=7, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1})
    ax.set_xlim(x0 - 60, x1 + 60)
    ax.set_ylim(dis_n[1] - 0.12 * (y1 - y0), y1 + 60)
    ax.set_title(f"Topoloji · düzen {k['topolojik']['duzen']} · imza {k['topolojik']['imza'][:8]}\n"
                 "düz çizgi: kapı ya da açık geçiş · kesikli: kapısız ortak duvar", fontsize=10)
    ax = axs[1]
    zemin(ax)
    for e in k["parametrik"]["kenarlar"]:
        if not e.get("durum"):
            continue
        c = RENK_DURUM[e["durum"]]
        a0, a1 = e["aralik"]
        pts = [(a0, e["konum_cm"]), (a1, e["konum_cm"])] if e["yon"] in ("G", "K") else [(e["konum_cm"], a0), (e["konum_cm"], a1)]
        ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], color=c, lw=3.2 if e["en_dis"] else 1.6, zorder=5, solid_capstyle="butt")
    pay = 0.05 * max(x1 - x0, y1 - y0)
    veranda = {m["ad"] for m in k["anlamsal"]["mahaller"] if m["sinif"] == "veranda"}
    for eksen, bantlar in (k["parametrik"].get("germe") or {}).items():
        for g in bantlar:
            c = "#b0b0b0" if set(g["mahaller"]) & veranda else {1: RENK_DURUM["oynar"], 2: RENK_DURUM["duzey2"], 3: RENK_DURUM["kilitli"]}[g["duzey"]]
            a0, a1 = g["aralik"]
            if eksen == "x":
                ax.add_patch(Rectangle((a0, y0 - 1.6 * pay), a1 - a0, pay, facecolor=c, alpha=0.75, edgecolor="none"))
            else:
                ax.add_patch(Rectangle((x0 - 1.6 * pay, a0), pay, a1 - a0, facecolor=c, alpha=0.75, edgecolor="none"))
    for ad, p in nokta.items():
        ax.text(*p, ad, ha="center", va="center", fontsize=8, zorder=7)
    ax.set_xlim(x0 - 2 * pay, x1 + 60)
    ax.set_ylim(y0 - 2 * pay, y1 + 60)
    ax.set_title("Parametrik (ön bilgi; kararı denetçi verir) · yeşil oynar · turuncu düzey 2 (ikincil çatı yeniden) · kırmızı kilitli\n"
                 "kalın çizgi mahalin en dış kenarı · kenar şeritleri: germe bantları (alt: sağa–sola, sol: öne–arkaya; gri: verandayı da keser)",
                 fontsize=10)
    an = k["anlamsal"]
    fig.suptitle(f"{k.get('kod') or ''} · yapı kimliği · {an['oda_programi']} · {str(an['oturum_m2']).replace('.', ',')} m² · çatı {an['cati']['tip']}",
                 fontsize=13, weight="bold")
    fig.tight_layout()
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(yol, dpi=110, facecolor="white", metadata={"Software": None})
    plt.close(fig)
    return yol


# ── komut ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
def kaynak(girdi: dict) -> dict:
    """Kimliğin okuduğu biçim: Yapı Tanımı (`duvarlar`) ve plan sözleşmesi (`sema` portman.plan/0.1) olduğu gibi; eski biçim prefabrik
    İş Emri `plan_adaptor.prefabrik_oku` ile sözleşmeye çevrilir."""
    if "duvarlar" in girdi or girdi.get("sema") == "portman.plan/0.1":
        return girdi
    if "yapi" in girdi and "mahaller" in girdi:
        from beyin.plan_adaptor import prefabrik_oku
        return prefabrik_oku(girdi)
    raise ValueError("girdi tanınmadı: Yapı Tanımı, plan sözleşmesi ya da prefabrik İş Emri bekleniyordu")


def oku(girdi: dict, set_yolu: str | Path | None = None) -> dict:
    """Girdi (Yapı Tanımı, plan sözleşmesi ya da eski biçim prefabrik İş Emri) → yapı kimliği."""
    k = kaynak(girdi)
    return tanimdan(k, set_yolu) if "duvarlar" in k else plandan(k)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Yapı kimliği (İE-23): Yapı Tanımı, plan sözleşmesi ya da prefabrik İş Emri → kimlik JSON")
    ap.add_argument("girdi", type=Path)
    ap.add_argument("--cikti", type=Path)
    ap.add_argument("--gorsel", type=Path)
    ap.add_argument("--set", dest="set_yolu", type=Path, help="alan ölçümünün kural seti (yalnız Yapı Tanımı)")
    a = ap.parse_args(argv)
    girdi = kaynak(json.loads(a.girdi.read_text(encoding="utf-8")))
    k = oku(girdi, a.set_yolu)
    metin = json.dumps(k, ensure_ascii=False, indent=1) + "\n"
    if a.cikti:
        a.cikti.parent.mkdir(parents=True, exist_ok=True)
        a.cikti.write_text(metin, encoding="utf-8")
    else:
        sys.stdout.write(metin)
    if a.gorsel:
        gorsel(girdi, a.gorsel, k, a.set_yolu)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
