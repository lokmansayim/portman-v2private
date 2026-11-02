"""İE-24 · Girintili gövdenin (TK-03'ün Z gövdesi) rehber çatısı: ana çatı + paralel cumbalar (`motor/cati_serit.py`).

Şablonun (`sahne.js`, 62 m²) mahyası x yönündeki çatısı aynen kullanılır: makaslar y boyunca, saçaklar önde ve arkada, kalkanlar solda ve
sağda. Burada yalnız evin çatı verisi kurulur; kaynaklar motorunkiler, rehber kendi çatısını kurmaz (D-28):

- **Parçalar, makas yerleri, kalkanlar** çatı tanımından (`cati_serit.tanim`; çizim, liste, 3B model ve kart modeli aynı tanımı okur).
  Baş makas, 62 m²'deki gibi dış yüzü omeganın dış kanadıyla aynı hizada (duvarın dış yüzünden 3,7 cm). Cumbanın iç ucunda makas yok.
- **Yüzler, kenarlar, dere hatları** `cati_genel.cati_kur`'dan (liste üreteci ve kart modeliyle aynı). Aynı düzlemdeki ana çatı ve cumba yüzü
  tek yüzdür (içbükey çokgen: şablon şeridi yüzle kırpar). Başka bir çatının altında kalan kenar görünmez (`motor/yerlesim/serit._ortulu`):
  ana çatının kalkanı cumbanın çatısıyla aynı düzleme indiği yerde biter (62 m²'nin veranda devamı gibi, `ucKapali`).
- **Aşık ve iniş yerleri** kart modelinden (`<kod>_model.ifc`: `ASIK_n` yüz ve sıra bilgisiyle, `INIS_n`). İniş borusu saçağın altındaki
  duvarın ucunda (köşe direğinin yanında) iner.
- **Kaplama şeritleri** kitabın çok düzlemli diziliminden (`girdi_genel._dizilim`; liste ve kart modeli aynı): her yüzde ilk şeridin başı.

Mahyası y yönündeki girintili gövde henüz yok: `Desteklenmiyor`.
"""
from __future__ import annotations

import math
from collections import defaultdict

from shapely.geometry import LineString, Polygon

BAS = 3.7                   # baş makasın konumu: duvarın dış yüzünden (şablon: dış yüzü omeganın dış kanadıyla aynı hizada)
ESIK = 1e-6


def _cizgi_kesisimi(p1, d1, p2, d2):
    """İki doğrunun (nokta + yön) kesişimi; paralelse ilk noktası."""
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(det) < ESIK:
        return p1
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / det
    return (p1[0] + t * d1[0], p1[1] + t * d1[1])


def _ote(P: list, pay: list[float]) -> list:
    """Çokgenin her kenarını dışarı `pay[i]` kadar kaydır (saçak 1,3, görünen alın 0,2; şablonun yüz çokgeni gibi)."""
    n = len(P)
    alan = sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n)) / 2
    ks = []
    for i in range(n):
        (ax, ay), (bx, by) = P[i], P[(i + 1) % n]
        L = math.hypot(bx - ax, by - ay)
        dx, dy = (bx - ax) / L, (by - ay) / L
        nx, ny = (dy, -dx) if alan > 0 else (-dy, dx)
        ks.append(((ax + nx * pay[i], ay + ny * pay[i]), (dx, dy)))
    return [_cizgi_kesisimi(*ks[i - 1], *ks[i]) for i in range(n)]


def _disbukey(P: list) -> bool:
    pg = Polygon(P)
    return abs(pg.convex_hull.area - pg.area) < 1.0


def cati(HZ: dict, kitap: dict, IFC: dict, ASIK: dict, H: float, SC: float, TAN: float, COS: float, baslangic: dict, ls, PI: float,
         Desteklenmiyor, _r, fmt, fmtc, kucuk, ASMA: bool) -> dict:
    """Rehberin çatı verisi (şablonun anahtarları: `R`, `makas`, `sacak`, `kalkan`, `yuz`, `asik`, kaplama şeridi ve mahya, `izo`, dere ve
    iniş) ve adım yazılarının sayıları. `IFC`: kart modelinin kutuları (makas alt başlığı, aşık, iniş); `ASIK`: aşıkların yüz ve sıra bilgisi."""
    from motor.genel import cati_genel
    from motor.genel.girdi_genel import _dizilim
    from motor.yerlesim.serit import _nokta, _ortulu

    T = HZ["cati_serit"]
    if abs(float(T["sacak"]) - SC) > 0.01:
        raise Desteklenmiyor(f"çatı tanımının saçağı {T['sacak']}, İş Emri'nin {SC}")
    for q in T["parcalar"]:
        if abs(q["mahya"][0][1] - q["mahya"][1][1]) > ESIK:
            raise Desteklenmiyor("girintili gövdede mahya y yönünde; rehber şimdilik mahyası x yönündeki ana çatı + cumba çatısını kurar")
    govde = Polygon(HZ["govde"])
    ck = cati_genel.cati_kur(T, kitap)
    adli = {dz["ad"]: dz for dz in ck["duzlemler"]}

    # ---------- parçalar ve çerçeveler (şablonun R'si: makas boyunca s = y) ----------
    anahtar, ci = {}, 0
    for q in T["parcalar"]:
        if q["rol"] == "ana":
            anahtar[q["ad"]] = "AN"
        else:
            ci += 1
            anahtar[q["ad"]] = f"C{ci}"
    PAR = {q["ad"]: q for q in T["parcalar"]}
    RF = {anahtar[q["ad"]]: {"L": _r(q["b"][0] - SC), "R": _r(q["b"][1] + SC), "M": _r((q["b"][0] + q["b"][1]) / 2), "tan": TAN}
          for q in T["parcalar"]}
    EGIM_D = math.degrees(math.atan(TAN))

    def parca_of(dz_ad: str) -> dict:
        return next(q for q in T["parcalar"] if dz_ad.startswith(q["ad"] + " "))

    def cati_yazi(q):
        (b0, b1) = q["b"]
        return f"{kucuk(q['ad'])} beşiği · eğim %{fmt(TAN * 100)} ({fmt(EGIM_D, 1)}°) · açıklık {fmtc(b1 - b0 + 2 * SC)} cm"

    # ---------- makaslar: soldan sağa ----------
    yer = []
    for q in T["parcalar"]:
        a0, a1 = q["a"]
        for m in q["makaslar"]:
            k = m["konum"]
            if m["rol"] == "bas":
                k = a0 + BAS if abs(k - a0) < abs(k - a1) else a1 - BAS
            yer.append((k, q, m["rol"]))
    yer.sort(key=lambda t: t[0])
    n_ifc = sum(1 for n in IFC if n.startswith("MAKAS"))
    if n_ifc != len(yer):
        raise Desteklenmiyor(f"kart modelinde {n_ifc} makas, çatı tanımında {len(yer)}")

    def nb(span):
        return max(2, round((span - 77.8) / 64))

    makas, MAD = [], defaultdict(list)            # MAD: parça → makas adları
    for i, (k, q, rol) in enumerate(yer):
        (b0, b1), ad = q["b"], f"MKS{i + 1:02d}"
        MAD[q["ad"]].append(ad)
        mk = {"ad": ad, "aile": "ana" if q["rol"] == "ana" else "cumba", "rol": rol, "konum": _r(k), "bas": _r(b0 - SC), "son": _r(b1 + SC),
              "R": anahtar[q["ad"]], "yon": "y", "wl": [_r(b0 + 2.7), _r(b1 - 2.7)], "NB": nb(b1 - b0 + 2 * SC), "T0": 38.9, "cati": cati_yazi(q)}
        if q["rol"] != "ana":
            mk.update(kod=None, kart_ad="Cumba makası",
                      kaynak=f"yer ve açıklık çatı tanımından (çizim, liste ve 3B modelle aynı); {ls('Cumba makası · ' + q['ad'])}; "
                             "kartı henüz yok (İE-15)")
        makas.append(mk)

    def mks(q, x):
        """Parçanın x'e en yakın makasının adı."""
        return min((m for m in makas if m["R"] == anahtar[q["ad"]]), key=lambda m: abs(m["konum"] - x))["ad"]

    # ---------- saçak hatları (her saçak kenarı: saçak sacı, dere, saçak omegası) ----------
    hatlar = []
    for e in (e for e in ck["kenarlar"] if e["tur"] == "sacak"):
        dz = adli[e["duzlemler"][0]]
        ic = 1 if dz["yukari"][1] > 0 else -1                           # içeri yön (y): ön yüzde +1
        ys = e["p"][1]                                                  # saçak çizgisi
        yd = ys + ic * SC                                               # duvarın dış yüzü
        r0, r1 = sorted((e["p"][0], e["q"][0]))
        kes = govde.intersection(LineString([(r0, yd + ic * 0.5), (r1, yd + ic * 0.5)]))
        duvar = sorted([round(min(p[0] for p in s.coords), 2), round(max(p[0] for p in s.coords), 2)]
                       for s in getattr(kes, "geoms", [kes]) if not s.is_empty and s.length > 1.0)
        if not duvar:
            raise Desteklenmiyor(f"{dz['ad']} saçağının altında duvar yok")
        w0, w1 = duvar[0][0], duvar[-1][1]
        bos0, bos1 = r0 < w0 - 1, r1 > w1 + 1                           # saçaklı uç (duvarın dışında); öbürü başka çatının duvarında biter
        q = parca_of(dz["ad"])
        bir = [b for b in (dz.get("birlesen") or []) if not b.startswith(q["ad"] + " ")]
        ad = f"{q['ad']}{' ve ' + ', '.join(b.rsplit(' ', 1)[0] for b in bir) if bir else ''} {dz['ad'].rsplit(' ', 1)[1]}"
        hatlar.append({"ad": ad, "dz": dz["ad"], "q": q, "ic": ic, "ys": ys, "yd": yd, "duvar": duvar,
                       "a0": r0 - 0.2 if bos0 else r0, "a1": r1 + 0.2 if bos1 else r1,
                       "t0": w0 - 1.1 if bos0 else r0, "t1": w1 + 1.1 if bos1 else r1})
    hatlar.sort(key=lambda h: (h["ic"] < 0, h["ys"]))

    sacak = [{"ad": f"{h['ad']} saçağı", "o": "h", "face": _r(h["yd"]), "out": -h["ic"], "a0": _r(h["a0"]), "a1": _r(h["a1"]), "f0": _r(h["a0"]),
              "f1": _r(h["a1"]), "t0": _r(h["t0"]), "t1": _r(h["t1"]), "R": anahtar[h["q"]["ad"]]} for h in hatlar]
    dere_hat = [{"ad": h["ad"], "yon": "x", "a0": h["a0"], "a1": h["a1"], "kenar": _r(h["ys"] - h["ic"] * 0.2), "out": -h["ic"]} for h in hatlar]

    # ---------- duvar üstü omegaları: baş makas omegası baş makasın boyunca saçaktan saçağa (D-32); saçak omegası kart modelinden (`veri.py`, D-39) ----------
    omega_duvar = []
    kalkan, ucu = [], []
    for k, q, rol in yer:
        if rol != "bas":
            continue
        a0, a1 = q["a"]
        sol = abs(k - a0) < abs(k - a1)
        w = a0 if sol else a1
        (b0, b1), M = q["b"], (q["b"][0] + q["b"][1]) / 2
        omega_duvar.append({"tur": "bas", "o": "v", "perp": _r(w + (5 if sol else -5)), "a0": _r(b0 - SC), "a1": _r(b1 + SC), "out": -1 if sol else 1,
                            "yer": f"{kucuk(q['ad'])} {'sol' if sol else 'sağ'} kalkan hattı ({mks(q, k)} altı)"})
        # kalkanın görünen alın kenarları (alın hattı saçak kadar dışarıda): görünmeyen uç başka çatının yüzüyle aynı düzlemde biter
        xa = w - SC if sol else w + SC
        gor = [e for e in ck["kenarlar"] if e["tur"] == "alin" and abs(e["p"][0] - xa) < 0.5 and abs(e["q"][0] - xa) < 0.5 and not _ortulu(ck, e)]
        uc = {"A": b0 - SC, "B": b1 + SC}
        kapali = {}
        for u, yan in (("A", lambda y: y < M - 0.5), ("B", lambda y: y > M + 0.5)):
            ys = [y for e in gor for y in (e["p"][1], e["q"][1]) if yan(y)]
            if not ys:
                raise Desteklenmiyor(f"{q['ad']} {'sol' if sol else 'sağ'} kalkanının {'ön' if u == 'A' else 'arka'} alın kenarı görünmüyor")
            uc_y = min(ys) if u == "A" else max(ys)
            if abs(uc_y - uc[u]) > 0.5:
                uc[u] = uc_y
                kapali[u] = True
        p = -1 if sol else 1
        KA = {"ad": f"{kucuk(q['ad'])} {'sol' if sol else 'sağ'} kalkanı ({mks(q, k)})", "r": -PI / 2 if sol else PI / 2, "O": [_r(w), 0],
              "R": anahtar[q["ad"]], "p": p, "uc": {u: _r(p * y) for u, y in uc.items()}, "sm": _r(p * M), "duvar": {"A": _r(p * b0), "B": _r(p * b1)},
              "altUc": {"A": "A" not in kapali, "B": "B" not in kapali}}
        if kapali:
            KA["ucKapali"] = kapali
            ucu.append((q, sol, kapali))
        kalkan.append(KA)

    # ---------- yüzler (kaplama ve aşık) ----------
    kenar_tur = []
    for e in ck["kenarlar"]:
        kenar_tur.append((e, e["tur"] == "alin" and not _ortulu(ck, e)))

    def pay(a, b):
        for e, gorunur in kenar_tur:
            if {tuple(round(v, 2) for v in e["p"]), tuple(round(v, 2) for v in e["q"])} == {tuple(round(v, 2) for v in a), tuple(round(v, 2) for v in b)}:
                return 1.3 if e["tur"] == "sacak" else 0.2 if gorunur else 0.0
        return 0.0
    ilk = {}                                                            # yüz → dizilimin ilk şeridinin başı (x)
    d = _dizilim(ck, kitap, "sandvic_panel")
    for pn in d["paneller"]:
        for dd in pn["dikdortgenler"]:
            for pc in dd["parcalar"]:
                ilk.setdefault(pc.yuz, _nokta(adli[pc.yuz], pc.u0, 0)[0])
    yuz, hadve_ar, YK = {}, {}, {}
    for i, dz in enumerate(ck["duzlemler"]):
        P = [tuple(p) for p in dz["plan"]]
        Q = _ote(P, [pay(P[j], P[(j + 1) % len(P)]) for j in range(len(P))])
        q = parca_of(dz["ad"])
        k = f"Y{i + 1}"
        YK[dz["ad"]] = k
        lo, hi = min(p[0] for p in Q), max(p[0] for p in Q)
        hadve_ar[f"H{k}"] = (lo, hi)
        h = next(h for h in hatlar if h["dz"] == dz["ad"])
        bas_x = ilk.get(dz["ad"], lo)
        son_x = hi if abs(bas_x - lo) < abs(bas_x - hi) else lo
        yuz[k] = {"ad": f"{h['ad']} yüzü", "E": [0, _r(h["ys"])], "d": [0, h["ic"]], "R": anahtar[q["ad"]], "poly": [[_r(x), _r(y)] for x, y in Q],
                  "eksen": "x", "hadve": f"H{k}", "_bas": bas_x, "_son": son_x, "_parcalar": [q["ad"]] + [b.rsplit(" ", 1)[0] for b in (dz.get("birlesen") or [])
                                                                                                  if not b.startswith(q["ad"] + " ")]}
        if not _disbukey(Q):
            yuz[k]["icbukey"] = True

    # ---------- aşıklar (kart modelinden: yüz ve sıra) ----------
    sira = defaultdict(list)
    for n, kt in IFC.items():
        if n.startswith("ASIK"):
            ps = ASIK.get(n) or {}
            if ps.get("Cati") not in YK:
                raise Desteklenmiyor(f"kart modelinin aşığı {n} çatının yüzlerinden birinde değil ({ps.get('Cati')})")
            sira[(YK[ps["Cati"]], int(ps["Sira"]))].append(kt)
    sondan = baslangic.get("x") == "max"
    asik = {}
    for k, Y in yuz.items():
        rows = sorted((s, kts) for (kk, s), kts in sira.items() if kk == k)
        sr, pf = [], []
        for _s, kts in rows:
            yc = (kts[0][1] + kts[0][4]) / 2
            sr.append(round(abs(yc - Y["E"][1]) / COS, 2))
            ps = sorted(kts, key=lambda b: b[0], reverse=sondan)
            pf.append([round(b[3] - b[0], 2) for b in ps])
        artan = (Y["d"][1] > 0) != sondan                               # yerel t x ile artıyor (ön yüz) ve dizilim küçük x'ten
        asik[k] = {"sira": sr, "pafta": pf, "bas": "min" if artan else "max"}

    # ---------- mahya ----------
    mahya = []
    for e in (e for e in ck["kenarlar"] if e["tur"] == "mahya"):
        y = e["p"][1]
        x0, x1 = sorted((e["p"][0], e["q"][0]))
        q = next(q for q in T["parcalar"] if abs(q["mahya"][0][1] - y) < 0.5 and min(x1, q["a"][1] + SC) - max(x0, q["a"][0] - SC) > 1)
        mahya.append({"R": anahtar[q["ad"]], "topR": anahtar[q["ad"]], "r": PI / 2, "O": [0, 0], "s0": _r(y), "z": [_r(x0 - 0.2), _r(x1 + 0.2)],
                      "ad": f"{kucuk(q['ad'])} mahyası"})
    mahya.sort(key=lambda m: m["z"][0])

    # ---------- izolasyon: her makas aralığına bir şerit, ön duvardan arka duvara ----------
    ana = next(q for q in T["parcalar"] if q["rol"] == "ana")
    serme = f"çatı kapanmadan önce, aşıkların arasından; rulo ön duvardan arka duvara açılır, {'asma ' if ASMA else 'ters '}tavanın üstüne serilir"
    izo = {"ana": {"yon": "y", "bas": _r(ana["b"][0] + 10), "L": _r(ana["b"][1] - ana["b"][0] - 20), "ad": "Çatı izolasyonu · 10 cm rulo cam yünü",
                   "serme": serme}, "ek": []}
    for q in (q for q in T["parcalar"] if q["rol"] != "ana"):
        a0, a1 = q["a"]
        ic_uc = a1 if a1 < ana["a"][0] + 0.5 else a0                   # cumbanın iç ucu ana çatıya (ya da iç komşu cumbaya) bakan uç
        ks = sorted((m["konum"], m["ad"]) for m in makas if m["R"] == anahtar[q["ad"]])
        uclar = sorted(ks + [(ic_uc, None)])
        for (u, ua), (v, va) in zip(uclar, uclar[1:]):
            x0, x1 = (u + 4.2 if ua else u + 1), (v - 4.2 if va else v - 1)
            arasi = f"{ua}–{va} arası" if ua and va else f"{ua or va} ile ana çatının duvarı arası"
            izo["ek"].append({"yon": "y", "y": _r(q["b"][0] + 10), "x0": _r(x0), "x1": _r(x1), "L": _r(q["b"][1] - q["b"][0] - 20),
                              "ad": f"Çatı izolasyonu · 10 cm rulo cam yünü ({kucuk(q['ad'])})", "bu": f"{kucuk(q['ad'])} · {arasi} · {{w}} × {{L}} cm",
                              "serme": serme})

    # ---------- inişler (kart modelinden): saçağın altındaki duvarın ucunda iner ----------
    inisler = []
    for n, kt in sorted(IFC.items()):
        if not n.startswith("INIS"):
            continue
        xc, yc = (kt[0] + kt[3]) / 2, (kt[1] + kt[4]) / 2
        h = min(hatlar, key=lambda h: abs(yc - h["ys"]) + (0 if h["a0"] - 10 <= xc <= h["a1"] + 10 else 1e4))
        w0, w1 = min(h["duvar"], key=lambda w: 0 if w[0] <= xc <= w[1] else min(abs(xc - w[0]), abs(xc - w[1])))
        s = min(max(xc, w0 + 17), w1 - 17)
        inisler.append({"hat": h["ad"], "s": _r(s), "yuz": _r(h["yd"]), "duvar": f"{h['ad']} saçağının altındaki duvar", "dis": 0,
                        "kose": bool(abs(s - xc) > 0.5 or s < w0 + 17.5 or s > w1 - 17.5)})

    # ---------- adım yazıları için ----------
    tepe = (ana["b"][1] - ana["b"][0]) / 2 * TAN + SC * TAN
    aralik = sorted({round(b["konum"] - a["konum"], 1) for a, b in zip(makas, makas[1:]) if a["R"] == b["R"]})
    return {"RF": RF, "makas": makas, "MAD": dict(MAD), "omega_duvar": omega_duvar, "sacak": sacak, "kalkan": kalkan, "yuz": yuz,
            "hadve_ar": hadve_ar, "asik": asik, "mahya": mahya, "izo": izo, "dere_hat": dere_hat, "inisler": inisler, "tepe": tepe,
            "aralik": aralik, "ucu": ucu, "hatlar": [h["ad"] for h in hatlar], "parcalar": T["parcalar"], "anahtar": anahtar,
            "sacak_hatlari": [{"ad": h["ad"], "perp": _r(h["yd"] + h["ic"] * 5), "a0": _r(h["a0"]), "a1": _r(h["a1"])} for h in hatlar]}
