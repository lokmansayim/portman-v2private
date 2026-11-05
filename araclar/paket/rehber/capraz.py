"""İE-15 K6 · Beşik + çıkıntısız çapraz cumbanın rehber çatısı (TK-04; AP-06, AP-13, AP-16 aynı kod yolu): `motor/cati_capraz.py`.

Şablonun (`sahne.js`, 62 m²) beşik + cumba çatısı aynen kullanılır: ana çatının makasları y boyunca (mahya x yönünde), cumbanın makasları
x boyunca; cumbanın ana çatının üstündeki makası 62 m²'deki "ara makas" (alt başlığı ana makasların üst başlığında, üstü cumba eğiminde);
ana çatının ön yüzü derelerde kırpılır (62 m²'nin MFL/MFR yüzleri), dere hatlarına ters mahya. Burada yalnız evin çatı verisi kurulur;
kaynaklar motorunkiler, rehber kendi çatısını kurmaz (D-28):

- **Parçalar, makas yerleri, kalkanlar** çatı tanımından (`cati_capraz.tanim`; liste, 3B model ve kart modeli aynı tanımı okur). Baş
  makas, 62 m²'deki gibi dış yüzü omeganın dış kanadıyla aynı hizada (duvarın dış yüzünden 3,7 cm). Cumbanın ana çatının üstündeki
  makası (yavru makas) çatı tanımının yerinde; uçları derelerde sıfır yüksekliğe indiği için şablonun ara makası gibi derenin 10 cm
  üstünde biter (gösterim, 62 m²'deki gibi).
- **Yüzler, kenarlar, dere hatları** `cati_genel.cati_kur`'dan (liste üreteci ve kart modeliyle aynı); ana çatının cumbalı yüzü derelerin
  birleştiği yerden ikiye bölünür (her parça dışbükey, tek dere hattı: şablonun aşık sırası ve ters mahyası tek aralık okur).
- **Aşık ve iniş yerleri** kart modelinden (`<kod>_model.ifc`: `ASIK_n` yüz ve sıra bilgisiyle, `INIS_n`). İniş borusu saçağın altındaki
  duvarın ucunda ya da veranda kolonunda iner (altında duvar olmayan saçakta en yakın duvarın köşesine döner).
- **Kaplama şeritleri** kart modelinin dizilimiyle (liste gibi parça parça, `serit.kaplama_capraz`): ana çatıda kalkan kenarından
  dizilimin başladığı uçtan, cumbada dış uçtaki kalkandan.

Cumba ön ya da arka cephede (makasları x boyunca) ve ana çatının mahyası x yönünde değilse `Desteklenmiyor`.
"""
from __future__ import annotations

import math
from collections import defaultdict

from shapely.geometry import LineString, Polygon, box

BAS = 3.7                   # baş makasın konumu: duvarın dış yüzünden (şablon: dış yüzü omeganın dış kanadıyla aynı hizada)
ARA_PAY = 10.0              # ara makasın ucu: cumbanın üst başlığı ana makasın üst başlığından bu kadar yüksekte (62 m²: ≈ 10 cm)
ARA_YUZ = 4.0               # ara makasın alt başlığı ana yüzün alçak kenarında (62 m²: konumdan 4 cm saçağa doğru)
ESIK = 1e-6


def _ote(P: list, pay: list[float]) -> list:
    from .girinti import _ote as ote
    return ote(P, pay)


def cati(HZ: dict, plan, kitap: dict, IFC: dict, ASIK: dict, SC: float, TAN: float, COS: float, baslangic: dict, ls, PI: float,
         Desteklenmiyor, _r, fmt, fmtc, kucuk, ASMA: bool, W: float, DY: float) -> dict:
    """Rehberin çatı verisi (`girinti.cati` ile aynı anahtarlar: `RF`, `makas`, `omega_duvar`, `sacak`, `kalkan`, `yuz`, `asik`, kaplama
    mahyası, `izo`, dere ve iniş) ve adım yazılarının sayıları. `IFC`: kart modelinin kutuları (makas alt başlığı, aşık, iniş); `ASIK`:
    aşıkların yüz ve sıra bilgisi."""
    from motor.cati_capraz import yavru_acikligi
    from motor.genel import cati_genel
    from motor.yerlesim.serit import _ortulu

    T = HZ["cati_serit"]
    if abs(float(T["sacak"]) - SC) > 0.01:
        raise Desteklenmiyor(f"çatı tanımının saçağı {T['sacak']}, İş Emri'nin {SC}")
    ana = next(q for q in T["parcalar"] if q["rol"] == "ana")
    cu = next(q for q in T["parcalar"] if q["rol"] == "cumba")
    if abs(ana["mahya"][0][1] - ana["mahya"][1][1]) > ESIK or cu["cephe"] not in ("on", "arka"):
        raise Desteklenmiyor("çapraz cumba: rehber şimdilik mahyası x yönündeki ana çatıyı ve ön ya da arka cephedeki cumbayı kurar")
    ck = cati_genel.cati_kur(T, kitap)
    on = cu["cephe"] == "on"
    ic = 1.0 if on else -1.0                                       # cumbanın dış ucundan içeri (y)
    dis = cu["dis_uc"]
    (a0, a1), (b0, b1) = ana["a"], ana["b"]                         # ana çatı: a mahya boyunca (x), b makas boyunca (y)
    (c0, c1) = cu["b"]                                              # cumba: makas boyunca (x)
    M_an, M_cu = (b0 + b1) / 2, (c0 + c1) / 2
    RF = {"AN": {"L": _r(b0 - SC), "R": _r(b1 + SC), "M": _r(M_an), "tan": TAN},
          "CU": {"L": _r(c0 - SC), "R": _r(c1 + SC), "M": _r(M_cu), "tan": TAN}}
    EGIM_D = math.degrees(math.atan(TAN))
    birlesim = (cu["mahya"][0][1] if abs(cu["mahya"][0][1] - dis) > abs(cu["mahya"][1][1] - dis) else cu["mahya"][1][1])   # derelerin birleştiği y

    def nb(span):
        return max(2, round((span - 77.8) / 64))

    # ---------- makaslar: ana çatı soldan sağa, sonra cumba (dış uçtan içeri) ----------
    makas, MAD = [], defaultdict(list)
    cati_an = f"ana çatı beşiği · eğim %{fmt(TAN * 100)} ({fmt(EGIM_D, 1)}°) · açıklık {fmtc(b1 - b0 + 2 * SC)} cm"
    cati_cu = (f"çapraz cumba · eğim %{fmt(TAN * 100)} · açıklık {fmtc(c1 - c0 + 2 * SC)} cm; mahyası ana çatının yüzüne iner "
               f"(derelerin birleştiği yer, dış yüzden {fmtc(abs(birlesim - dis))} cm)")
    for m in ana["makaslar"]:
        k = m["konum"]
        if m["rol"] == "bas":
            k = a0 + BAS if abs(k - a0) < abs(k - a1) else a1 - BAS
        ad = f"MKS{len(makas) + 1:02d}"
        MAD[ana["ad"]].append(ad)
        makas.append({"ad": ad, "aile": "ana", "rol": m["rol"], "konum": _r(k), "bas": _r(b0 - SC), "son": _r(b1 + SC), "R": "AN", "yon": "y",
                      "wl": [_r(b0 + 2.7), _r(b1 - 2.7)], "NB": nb(b1 - b0 + 2 * SC), "T0": 38.9, "cati": cati_an})
    kaynak_cu = f"yer çatı tanımından (D-47: dış uçtaki kalkan duvarının ekseninden 125,5 arayla, derelerin birleştiği yere kadar); {ls('Yavru makas · ' + cu['ad'])}"
    for m in cu["makaslar"]:
        ad = f"MKS{len(makas) + 1:02d}"
        MAD[cu["ad"]].append(ad)
        if not m.get("ana_ustunde"):                               # cumbanın baş makası: dış uçtaki kalkan duvarının üstünde
            makas.append({"ad": ad, "aile": "cumba", "rol": "bas", "konum": _r(dis + ic * BAS), "bas": _r(c0 - SC), "son": _r(c1 + SC), "R": "CU",
                          "yon": "x", "wl": [_r(c0 + 2.7), _r(c1 - 2.7)], "NB": nb(c1 - c0 + 2 * SC), "T0": 38.9, "cati": cati_cu, "kod": "MA-05",
                          "kaynak": kaynak_cu})
            continue
        u0, u1 = yavru_acikligi(T, cu, m["konum"])                 # dereler arası
        if m.get("uclar"):                                         # AP-06 paftasındaki gibi iki ana makasa oturur (`cumba_yavru_makasi`)
            b_, s_ = m["uclar"]
            yer = (f"; AP-06 paftasındaki gibi baş makasın arkasında, iki ana makasa ({' ve '.join(fmtc(v) for v in m['oturdugu'])}) oturur, "
                   f"boyu {fmtc(s_ - b_)} cm (Lokman, 5 Kasım 2026; kart modeliyle aynı)")
        else:                                                      # D-47: uçları derenin 10 cm üstünde (gösterim, 62 m² rehberindeki ara makas gibi)
            d = ARA_PAY / TAN - ARA_YUZ
            if u1 - u0 < 2 * d + 20:
                raise Desteklenmiyor(f"cumbanın yavru makası ({m['konum']:g}): dereler arası {fmtc(u1 - u0)} cm, rehberin ara makası kurulamaz")
            b_, s_ = u0 + d, u1 - d
            yer = f"; dereler arası {fmtc(u1 - u0)} cm; uçları derenin 10 cm üstünde biter (gösterim, 62 m² rehberindeki ara makas gibi)"
        makas.append({"ad": ad, "aile": "ara", "rol": "ara", "konum": _r(m["konum"]), "bas": _r(b_), "son": _r(s_),
                      "yuz": _r(m["konum"] - ic * ARA_YUZ), "R": "CU", "zR": "AN", "yon": "x", "nps": 1 if s_ - b_ < 200 else 2,
                      "cati": cati_cu, "kod": "MA-05", "kart_ad": None, "dereler_arasi": [_r(u0), _r(u1)], "kaynak": kaynak_cu + yer})
    n_ifc = sum(1 for n in IFC if n.startswith("MAKAS"))
    if n_ifc != len(makas):
        raise Desteklenmiyor(f"kart modelinde {n_ifc} makas, çatı tanımında {len(makas)}")

    def mks(R, x):
        return min((m for m in makas if m["R"] == R and m["aile"] != "ara"), key=lambda m: abs(m["konum"] - x))["ad"]

    # ---------- saçak hatları (ana çatının saçak kenarları: saçak sacı, dere, saçak omegası) ----------
    adli = {dz["ad"]: dz for dz in ck["duzlemler"]}
    alin_uclari = [p for e in ck["kenarlar"] if e["tur"] == "alin" for p in (e["p"], e["q"])]
    sac_uclari = [p for e in ck["kenarlar"] if e["tur"] == "sacak" for p in (e["p"], e["q"])]
    govde = box(0, 0, W, DY)
    hatlar = []
    for e in (e for e in ck["kenarlar"] if e["tur"] == "sacak"):
        dz = adli[e["duzlemler"][0]]
        if abs(e["p"][1] - e["q"][1]) > ESIK:
            raise Desteklenmiyor(f"{dz['ad']}: saçak kenarı x yönünde değil")
        ic_ = 1 if dz["yukari"][1] > 0 else -1                          # içeri yön (y): ön yüzde +1
        ys = e["p"][1]
        yd = ys + ic_ * SC
        r0, r1 = sorted((e["p"][0], e["q"][0]))
        kes = govde.intersection(LineString([(r0, yd + ic_ * 0.5), (r1, yd + ic_ * 0.5)]))
        w0, w1 = kes.bounds[0], kes.bounds[2]
        bos0, bos1 = r0 < w0 - 1, r1 > w1 + 1                           # saçaklı uç (duvarın dışında); öbürü cumbanın alnında biter
        yer = "ön" if ic_ > 0 else "arka"
        ad = f"ana çatı {yer}" + (f" (cumbanın {'sağı' if r0 > M_cu else 'solu'})" if (ic_ > 0) == on and (not bos0 or not bos1) else "")
        hatlar.append({"ad": ad, "dz": dz["ad"], "ic": ic_, "ys": ys, "yd": yd, "r0": r0, "r1": r1,
                       "a0": r0 - 0.2 if bos0 else r0 + 0.2, "a1": r1 + 0.2 if bos1 else r1 - 0.2,
                       "t0": w0 - 1.1 if bos0 else r0 + 0.2, "t1": w1 + 1.1 if bos1 else r1 - 0.2})
    hatlar.sort(key=lambda h: (h["ic"] < 0, h["ys"]))
    sacak = [{"ad": f"{h['ad']} saçağı", "o": "h", "face": _r(h["yd"]), "out": -h["ic"], "a0": _r(h["a0"]), "a1": _r(h["a1"]), "f0": _r(h["a0"]),
              "f1": _r(h["a1"]), "t0": _r(h["t0"]), "t1": _r(h["t1"]), "R": "AN"} for h in hatlar]
    dere_hat = [{"ad": h["ad"], "yon": "x", "a0": h["a0"], "a1": h["a1"], "kenar": _r(h["ys"] - h["ic"] * 0.2), "out": -h["ic"]} for h in hatlar]

    # ---------- baş makas omegaları (D-32: baş makasın boyunca saçak ucundan saçak ucuna) ve kalkanlar ----------
    def alt_uc(p) -> bool:
        """Alın kenarının alt ucunda dere biter mi (alın sacı köşede dereyi de içine alacak kadar uzar; şablonun `altUc`'u)."""
        return any(math.hypot(p[0] - s[0], p[1] - s[1]) < 0.5 for s in sac_uclari)

    omega_duvar, kalkan = [], []
    for m in (m for m in makas if m["aile"] == "ana" and m["rol"] == "bas"):
        sol = m["konum"] < (a0 + a1) / 2
        w = a0 if sol else a1
        xa = w - SC if sol else w + SC
        omega_duvar.append({"tur": "bas", "o": "v", "perp": _r(w + (5 if sol else -5)), "a0": _r(b0 - SC), "a1": _r(b1 + SC), "out": -1 if sol else 1,
                            "yer": f"{'sol' if sol else 'sağ'} duvar ({m['ad']} altı)"})
        gor = [e for e in ck["kenarlar"] if e["tur"] == "alin" and abs(e["p"][0] - xa) < 0.5 and abs(e["q"][0] - xa) < 0.5 and not _ortulu(ck, e)]
        ys_ = sorted(y for e in gor for y in (e["p"][1], e["q"][1]))
        if not ys_ or abs(ys_[0] - (b0 - SC)) > 0.5 or abs(ys_[-1] - (b1 + SC)) > 0.5:
            raise Desteklenmiyor(f"ana çatının {'sol' if sol else 'sağ'} kalkanı saçaktan saçağa görünmüyor")
        p = -1 if sol else 1
        kalkan.append({"ad": f"ana çatı {'sol' if sol else 'sağ'} kalkanı ({m['ad']})", "r": -PI / 2 if sol else PI / 2, "O": [_r(w), 0], "R": "AN", "p": p,
                       "uc": {"A": _r(p * (b0 - SC)), "B": _r(p * (b1 + SC))}, "sm": _r(p * M_an), "duvar": {"A": _r(p * b0), "B": _r(p * b1)},
                       "altUc": {"A": alt_uc((xa, b0 - SC)), "B": alt_uc((xa, b1 + SC))}})
    mb = next(m for m in makas if m["aile"] == "cumba")
    omega_duvar.append({"tur": "bas", "o": "h", "perp": _r(dis + ic * 5), "a0": _r(c0 - SC), "a1": _r(c1 + SC), "out": -1 if on else 1,
                        "yer": f"{'ön' if on else 'arka'} duvar, cumbanın altı ({mb['ad']} altı)"})
    ya = dis - ic * SC                                               # cumbanın alın hattı (y)
    p = 1 if on else -1
    kalkan.append({"ad": f"cumba kalkanı ({mb['ad']})", "r": 0 if on else PI, "O": [0, _r(dis)], "R": "CU", "p": p,
                   "uc": {"A": _r(p * (c0 - SC)), "B": _r(p * (c1 + SC))}, "sm": _r(p * M_cu), "duvar": {"A": _r(p * c0), "B": _r(p * c1)},
                   "altUc": {"A": alt_uc((c0 - SC, ya)), "B": alt_uc((c1 + SC, ya))}})
    if not any(alin_uclari):
        raise Desteklenmiyor("çatının alın kenarı yok")

    # ---------- yüzler: ana çatının cumbalı yüzü derelerin birleştiği yerden ikiye; cumbanın iki yüzü ----------
    kenar_tur = [(e, e["tur"] == "alin" and not _ortulu(ck, e)) for e in ck["kenarlar"]]

    def pay(a, b):
        for e, gorunur in kenar_tur:
            if {tuple(round(v, 2) for v in e["p"]), tuple(round(v, 2) for v in e["q"])} == {tuple(round(v, 2) for v in a), tuple(round(v, 2) for v in b)}:
                return 1.3 if e["tur"] == "sacak" else 0.2 if gorunur else 0.0
        return 0.0

    vadi = [e for e in ck["kenarlar"] if e["tur"] == "vadi"]
    if len(vadi) != 2:
        raise Desteklenmiyor(f"çapraz cumbada {len(vadi)} dere (vadi) kenarı; iki beklenir")
    tepe_ = (M_cu, birlesim)
    vadi_sol = next(e for e in vadi if min(e["p"][0], e["q"][0]) < M_cu - 0.5)
    vadi_sag = next(e for e in vadi if e is not vadi_sol)
    dere_ = {"sol": [list(p_) for p_ in sorted((vadi_sol["p"], vadi_sol["q"]), key=lambda t: abs(t[1] - birlesim), reverse=True)],
             "sağ": [list(p_) for p_ in sorted((vadi_sag["p"], vadi_sag["q"]), key=lambda t: abs(t[1] - birlesim), reverse=True)]}
    dizilim_x = baslangic.get("x", "min")
    dizilim_y = baslangic.get("y", "min")
    yuz, hadve_ar, YK = {}, {}, defaultdict(list)                   # YK: kart modelinin düzlemi → [(anahtar, x sınırı)]
    for dz in ck["duzlemler"]:
        P = [tuple(p_) for p_ in dz["plan"]]
        anam = dz["ad"].startswith("ana ")
        on_yuz = dz["yukari"][1] * ic > 0 if anam else None          # ana çatının cumbalı yüzü
        if anam and on_yuz:
            pg = Polygon(P)
            bx = pg.bounds
            parcalar = [("MFL", "solu", pg.intersection(box(bx[0] - 1, bx[1] - 1, M_cu, bx[3] + 1)), dere_["sol"], "sol", (-1e9, M_cu)),
                        ("MFR", "sağı", pg.intersection(box(M_cu, bx[1] - 1, bx[2] + 1, bx[3] + 1)), dere_["sağ"], "sağ", (M_cu, 1e9))]
        elif anam:
            parcalar = [("MB" if ic > 0 else "MF", None, Polygon(P), None, None, (-1e9, 1e9))]
        else:
            sol_ = dz["yukari"][0] > 0                               # batı yüzü (yukarı +x)
            parcalar = [("CL" if sol_ else "CR", None, Polygon(P), dere_["sol" if sol_ else "sağ"], "sol" if sol_ else "sağ", None)]
        for k, yan, pg, dere, dyan, xs in parcalar:
            Q0 = [tuple(round(v, 4) for v in c) for c in pg.exterior.coords[:-1]]
            Q0 = [q for i_, q in enumerate(Q0) if math.hypot(q[0] - Q0[i_ - 1][0], q[1] - Q0[i_ - 1][1]) > 0.01]
            Q = _ote(Q0, [pay(Q0[j], Q0[(j + 1) % len(Q0)]) for j in range(len(Q0))])
            if anam:
                yy = dz["sacak"]["y"] if "y" in dz["sacak"] else None
                E, d_, eksen, R = [0, _r(yy)], [0, 1 if dz["yukari"][1] > 0 else -1], "x", "AN"
                lo, hi = min(q[0] for q in Q), max(q[0] for q in Q)
                bas_v = a0 - SC - 0.2 if dizilim_x == "min" else a1 + SC + 0.2
                son_v = hi if dizilim_x == "min" else lo
                ad = (f"ana çatı {'ön' if dz['yukari'][1] > 0 else 'arka'} yüz" + (f" (cumbanın {yan})" if yan else ""))
                parca_ad = [ana["ad"]]
            else:
                xx = c0 - SC if dz["yukari"][0] > 0 else c1 + SC
                E, d_, eksen, R = [_r(xx), 0], [1 if dz["yukari"][0] > 0 else -1, 0], "y", "CU"
                lo, hi = min(q[1] for q in Q), max(q[1] for q in Q)
                bas_v = dis - ic * (SC + 0.2)                        # cumbada şeritler dış uçtaki kalkandan (kart modeli gibi)
                son_v = birlesim
                ad = f"cumba {'sol' if dz['yukari'][0] > 0 else 'sağ'} yüz"
                parca_ad = [cu["ad"]]
            hadve_ar[f"H{k}"] = (lo, hi)
            Y = {"ad": ad, "E": E, "d": d_, "R": R, "poly": [[_r(x), _r(y)] for x, y in Q], "eksen": eksen, "hadve": f"H{k}",
                 "_bas": bas_v, "_son": son_v, "_parcalar": parca_ad}
            if dere:
                Y["dere"], Y["dere_yan"] = dere, dyan
            yuz[k] = Y
            YK[dz["ad"]].append((k, xs))

    # ---------- aşıklar (kart modelinden: yüz ve sıra; ana çatının bölünen yüzünde parçalar bölme çizgisinde kırpılır) ----------
    # Bölme çizgisini geçen parça (derelerin birleştiği yerin arkasında sıra ana çatının iki ucu arasında kesintisiz) iki yüzde de gerçek boyuyla
    # yazılır ve yüzün sırasının son parçası olur: şablon son parçayı sıranın kalanıyla keser (iki yarısı birlikte paftadaki tek parça)
    sira = defaultdict(lambda: defaultdict(list))                    # anahtar → sıra → [(a, b, merkez, gerçek boy, bölünen uç)]
    for n, kt in IFC.items():
        if not n.startswith("ASIK"):
            continue
        ps = ASIK.get(n) or {}
        if ps.get("Cati") not in YK:
            raise Desteklenmiyor(f"kart modelinin aşığı {n} çatının yüzlerinden birinde değil ({ps.get('Cati')})")
        x0, y0, _z0, x1, y1, _z1 = kt
        for k, xs in YK[ps["Cati"]]:
            if k.startswith("C"):                                    # cumba yüzü: sıra y boyunca
                sira[k][int(ps["Sira"])].append((y0, y1, (x0 + x1) / 2, y1 - y0, None))
                continue
            a, b = max(x0, xs[0]), min(x1, xs[1])
            if b - a > 0.5:
                uc = "min" if a > x0 + 0.5 else "max" if b < x1 - 0.5 else None
                sira[k][int(ps["Sira"])].append((a, b, (y0 + y1) / 2, x1 - x0, uc))
    asik = {}
    for k, Y in yuz.items():
        dx, dy = Y["d"]
        ax = 1 if k.startswith("C") else 0                            # sıranın koştuğu eksen
        bolunen = {t[4] for parcalar in sira[k].values() for t in parcalar} - {None}
        if len(bolunen) > 1:
            raise Desteklenmiyor(f"{Y['ad']}: aşık sırası bölme çizgisinde iki uçtan kesik")
        sondan = (bolunen.pop() == "min") if bolunen else (dizilim_y if ax else dizilim_x) == "max"
        artan = (dy if ax == 0 else -dx) > 0                         # yerel t bu eksende artıyor mu (`sahne.js` › Y.yerel)
        sr_, pf = [], []
        for _s, parcalar in sorted(sira[k].items()):
            c = parcalar[0][2]
            sr_.append(round(abs(c - Y["E"][1 - ax]) / COS, 2))
            pf.append([round(L_, 2) for _a, _b, _c, L_, _u in sorted(parcalar, key=lambda t: t[0], reverse=sondan)])
        asik[k] = {"sira": sr_, "pafta": pf, "bas": ("max" if sondan else "min") if artan else ("min" if sondan else "max")}

    # ---------- mahya ----------
    mahya = [{"R": "AN", "topR": "AN", "r": PI / 2, "O": [0, 0], "s0": _r(M_an), "z": [_r(a0 - SC - 0.2), _r(a1 + SC + 0.2)], "ad": "ana çatı mahyası"}]
    z_ = sorted((dis - ic * (SC + 0.2), birlesim))
    mahya.append({"R": "CU", "topR": "CU", "r": PI, "O": [_r(M_cu), 0], "s0": 0, "z": [_r(z_[0]), _r(z_[1])], "ad": "cumba mahyası"})

    # ---------- izolasyon: ana çatının her makas aralığına bir şerit, ön duvardan arka duvara (cumba ana çatının üstünde) ----------
    serme = f"çatı kapanmadan önce, aşıkların arasından; rulo ön duvardan arka duvara açılır, {'asma ' if ASMA else 'ters '}tavanın üstüne serilir"
    izo = {"ana": {"yon": "y", "bas": _r(b0 + 10), "L": _r(b1 - b0 - 20), "ad": "Çatı izolasyonu · 10 cm rulo cam yünü", "serme": serme}, "ek": []}

    # ---------- inişler (kart modelinden): saçağın altındaki duvarın ucunda ya da veranda kolonunda iner ----------
    dis_duvar = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x"]
    kolonlar = [b["rect"] for b in HZ.get("baglantilar", []) if b["tur"] == "dikme"]
    inisler = []
    for n, kt in sorted(IFC.items()):
        if not n.startswith("INIS"):
            continue
        xc, yc = (kt[0] + kt[3]) / 2, (kt[1] + kt[4]) / 2
        h = min(hatlar, key=lambda h: abs(yc - h["ys"]) + (0 if h["r0"] - 10 <= xc <= h["r1"] + 10 else 1e4))
        duvar = sorted((d.a0 - d.h, d.a1 + d.h) for d in dis_duvar if abs((d.c - h["ic"] * d.h) - h["yd"]) < 0.6)
        kol = [((r[0] + r[2]) / 2, r) for r in kolonlar if abs((r[1] if h["ic"] > 0 else r[3]) - h["yd"]) < 0.6]
        icinde = next(((w0, w1) for w0, w1 in duvar if w0 <= xc <= w1), None)
        if icinde:
            s = min(max(xc, icinde[0] + 17), icinde[1] - 17)
            inisler.append({"hat": h["ad"], "s": _r(s), "yuz": _r(h["yd"]), "duvar": f"{h['ad']} saçağının altındaki duvar", "dis": 0,
                            "kose": bool(abs(s - xc) > 0.5 or s < icinde[0] + 17.5 or s > icinde[1] - 17.5)})
            continue
        uclar = [(abs(xc - w0), w0 + 17, "duvar") for w0, _w1 in duvar] + [(abs(xc - w1), w1 - 17, "duvar") for _w0, w1 in duvar] + \
                [(abs(xc - kx), kx, "kolon") for kx, _r_ in kol]
        if not uclar:
            raise Desteklenmiyor(f"kart modelinin inişi {n}: {h['ad']} saçağının altında duvar ya da kolon yok")
        _d, s, tur = min(uclar)
        if tur == "kolon":
            inisler.append({"hat": h["ad"], "s": _r(h["a1"] if xc > s else h["a0"]), "yuz": _r(h["yd"]), "duvar": "veranda kolonu", "sw": _r(s)})
        else:
            inisler.append({"hat": h["ad"], "s": _r(s), "yuz": _r(h["yd"]), "duvar": f"{h['ad']} saçağının ucundaki duvar köşesi", "dis": 0, "kose": True})

    tepe = (b1 - b0) / 2 * TAN + SC * TAN
    aralik = sorted({round(q - p_, 1) for p_, q in zip([m["konum"] for m in ana["makaslar"]], [m["konum"] for m in ana["makaslar"]][1:])})
    return {"RF": RF, "makas": makas, "MAD": dict(MAD), "omega_duvar": omega_duvar, "sacak": sacak, "kalkan": kalkan, "yuz": yuz,
            "hadve_ar": hadve_ar, "asik": asik, "mahya": mahya, "izo": izo, "dere_hat": dere_hat, "inisler": inisler, "tepe": tepe,
            "aralik": aralik, "ucu": [], "hatlar": [h["ad"] for h in hatlar], "parcalar": T["parcalar"], "anahtar": {ana["ad"]: "AN", cu["ad"]: "CU"},
            "sacak_hatlari": [{"ad": h["ad"], "perp": _r(h["yd"] + h["ic"] * 5), "a0": _r(h["a0"] - 0.4), "a1": _r(h["a1"] + 0.4)} for h in hatlar],
            "birlesim": birlesim, "cumba": cu, "ana": ana, "tepe_cu": (c1 - c0) / 2 * TAN + SC * TAN, "tepe_nokta": tepe_}
