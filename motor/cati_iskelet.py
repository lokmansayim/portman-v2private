"""BK-64 (D-139, PC-50) · Girintili gövdede kırma çatı: düz iskelet (straight skeleton) ile çatı yüzleri.

Lokman, 20 Kasım 2026: kart 08:27:14 "Evet, önce girintili evde kırma" (yöntem C: eski türler aynen, yeni türler kenar kuralıyla);
91 m² 3+1 evin makas planı kart 08:45:03 "Doğru, eskizdeki gibi", aşık dizilimi ve 4 çatı paneli kart 08:57:26 "Doğru, eskizdeki gibi".
Çatı biçimi 16 Kasım 2026'daki iskelet eskizinin aynısı (Lokman 11:13:41 "91 m² ve 143 m² doğru").

Yöntem: çatının ayak izi (`cati_serit.cati_izi`: gövde + ana çatının örttüğü veranda) saçak kadar dışarı genişletilir; her saçak kenarı
aynı eğimle içeri yükselen bir yüz verir. Bir noktanın yüksekliği, saçak çizgisi 45° içe kaydırılınca o noktaya varış mesafesidir. Gövde dik
açılı olduğundan bu, noktanın saçak çizgisine eksenlere paralel kare ölçüsüyle (L∞) uzaklığıdır: her kenarın etkisi, kenarın iki ucundan 45°
açılan kamada kenara dik uzaklıktır; nokta, değeri en küçük olan kenarın yüzündedir. Yüzler bu kamaların kesişiminden tam (çokgen işlemiyle)
kurulur; ızgara ya da yaklaşık hesap yok. Dış kütüphane yok (LGPL ve GPL kod depoya girmez; 16 ve 20 Kasım denemeleri).

Kenarlar (mahya, kırma, vadi, saçak) ve aşık sıraları genel motorun düzlem çekirdeğinden (`genel.cati_genel.cati_kur`): bu modül yalnız
düzlemleri kurar. Denetim: yüzler saçaklı ayak izini boşluksuz ve örtüşmesiz örter, desteksiz üst kenar yok, her yerde 30 cm'den dar yüz yok
(28 cm'lik küçük girintide ince şerit: kural yok, çatı çizilmez; K21).
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

YON_ADI = {(0, 1): "güney", (0, -1): "kuzey", (1, 0): "batı", (-1, 0): "doğu"}   # yüzün yükseldiği yön → saçağın cephesi (`cati_uretici` gibi)
EN_DAR_YUZ_CM = 30.0     # her yerde bundan dar yüz ince şerittir (28 cm'lik küçük girinti; 20 Kasım denemesi: 60, 78, 143 m²)


class IskeletHatasi(ValueError):
    pass


def _kenarlar(R: Polygon) -> list[tuple]:
    c = list(orient(R, 1.0).exterior.coords)[:-1]
    out = []
    for i in range(len(c)):
        a, b = c[i], c[(i + 1) % len(c)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        if abs(dx) > 1e-6 and abs(dy) > 1e-6:
            raise IskeletHatasi(f"çatının ayak izi dik açılı değil ({a} → {b}); iskelet yalnız dik açılı gövdede")
        t = (round(dx / L), round(dy / L))
        n = (-t[1], t[0])                                         # saat yönü tersinde içe normal: sol
        out.append({"a": a, "b": b, "t": t, "n": n, "L": L})
    return out


def _yari_duzlem(d: tuple, c: float, H: float, merkez: tuple) -> Polygon:
    """{p : p·d + c < 0} kocaman bir kutuyla kesilmiş (Sutherland–Hodgman)."""
    mx, my = merkez
    pts = [(mx - H, my - H), (mx + H, my - H), (mx + H, my + H), (mx - H, my + H)]
    f = lambda p: p[0] * d[0] + p[1] * d[1] + c
    out = []
    for i in range(4):
        p, q = pts[i], pts[(i + 1) % 4]
        fp, fq = f(p), f(q)
        if fp < 0:
            out.append(p)
        if (fp < 0) != (fq < 0):
            s = fp / (fp - fq)
            out.append((p[0] + s * (q[0] - p[0]), p[1] + s * (q[1] - p[1])))
    return Polygon(out) if len(out) >= 3 else Polygon()


def yuzler(R: Polygon) -> list[dict]:
    """Saçak çizgisi R'den (dik açılı) iskelet yüzleri: [{kenar, n, cokgen}], aynı düzlemdeki yüzler birleşik."""
    kn = _kenarlar(R)
    x0, y0, x1, y1 = R.bounds
    H = 4 * max(x1 - x0, y1 - y0) + 100
    merkez = ((x0 + x1) / 2, (y0 + y1) / 2)
    kama = []
    for e in kn:
        a, b, t, n = e["a"], e["b"], e["t"], e["n"]
        kama.append(Polygon([a, b, (b[0] + (t[0] + n[0]) * H, b[1] + (t[1] + n[1]) * H),
                             (a[0] + (n[0] - t[0]) * H, a[1] + (n[1] - t[1]) * H)]))
    off = [e["a"][0] * e["n"][0] + e["a"][1] * e["n"][1] for e in kn]   # f_i(p) = p·n_i − off_i
    ham = []
    for i, e in enumerate(kn):
        F = R.intersection(kama[i])
        kes = []
        for j, f in enumerate(kn):
            if j == i:
                continue
            d = (f["n"][0] - e["n"][0], f["n"][1] - e["n"][1])        # f_j − f_i = p·d + (off_i − off_j) < 0 → j daha alçak
            c = off[i] - off[j]
            if d == (0, 0):
                if c < -1e-9:
                    kes.append(kama[j])
                continue
            kes.append(kama[j].intersection(_yari_duzlem(d, c, H, merkez)))
        if kes:
            F = F.difference(unary_union(kes))
        ham.append((e, F))
    # aynı düzlem (aynı yön, aynı saçak doğrusu): tek yüz
    gruplar: dict[tuple, list] = {}
    for e, F in ham:
        k = (e["n"], round(e["a"][0] * e["n"][0] + e["a"][1] * e["n"][1], 6))
        gruplar.setdefault(k, []).append((e, F))
    out = []
    for (n, _), ls in gruplar.items():
        F = unary_union([F for _, F in ls])
        for g in getattr(F, "geoms", [F]):                        # aynı doğrudaki iki saçak kenarı birbirine değmiyorsa iki ayrı yüz
            if g.area <= 1e-3:
                continue
            e = next((e for e, F_ in ls if F_.intersection(g).area > 1e-3), None)
            if e is None:
                raise IskeletHatasi(f"{YON_ADI[n]} yüzünün saçak kenarı bulunamadı; iskelet beklenmeyen biçimde")
            p = Polygon([(round(x, 4), round(y, 4)) for x, y in g.exterior.coords]).simplify(0.01)
            if not p.is_valid or list(g.interiors):
                raise IskeletHatasi(f"{YON_ADI[n]} yüzü geçerli bir çokgen değil; iskelet beklenmeyen biçimde")
            out.append({"kenar": e, "n": n, "cokgen": p})
    return out


def duzlemler(iz: Polygon, sacak: float, egim: float, sacak_kotu: float) -> list[dict]:
    """Ayak izinden (gövde + veranda, dik açılı) `cati_genel` biçiminde düzlemler. Adlar yönden (`güney`, `kuzey`, …); aynı yönde
    birden çok yüz varsa büyükten küçüğe `güney`, `güney 2`."""
    R = orient(iz.buffer(sacak, join_style=2, mitre_limit=10), 1.0)
    try:
        yz = yuzler(R)
    except IskeletHatasi:
        raise
    except Exception as e:                                           # noqa: BLE001  (çokgen işleminin hatası: çatı çizilmez, K21)
        raise IskeletHatasi(f"iskelet kurulamadı ({type(e).__name__}: {e})") from None
    dar = [y for y in yz if y["cokgen"].buffer(-EN_DAR_YUZ_CM / 2, join_style=2).is_empty]
    if dar:
        raise IskeletHatasi("iskelet " + ", ".join(f"{YON_ADI[y['n']]} yönünde {y['cokgen'].area / 1e4:.2f} m²" for y in dar)
                            + f" ince şerit yüz kurdu (her yerde {EN_DAR_YUZ_CM:g} cm'den dar; küçük girinti); kural yok, çatı çizilmez")
    yz.sort(key=lambda y: (list(YON_ADI).index(y["n"]), -y["cokgen"].area))
    say: dict[tuple, int] = {}
    out = []
    for y in yz:
        say[y["n"]] = say.get(y["n"], 0) + 1
        ad = YON_ADI[y["n"]] + ("" if say[y["n"]] == 1 else f" {say[y['n']]}")
        e = y["kenar"]
        sac = {"x": float(e["a"][0])} if e["t"][0] == 0 else {"y": float(e["a"][1])}
        out.append({"ad": ad, "plan": [[float(x), float(v)] for x, v in list(y["cokgen"].exterior.coords)[:-1]],
                    "yukari": list(y["n"]), "egim": egim, "sacak_kotu": sacak_kotu, "sacak": sac,
                    "not": f"{ad} yüzü (düz iskelet, BK-64)"})
    return out


def makas_ekseni(duz: list[dict]) -> str:
    """Makasların geçtiği eksen ("x" ya da "y"; İş Emri'nin `makas_ekseni` anlamında): makaslar mahyaya diktir. Mahyalar tek yönde ve
    eksenlere paralel değilse IskeletHatasi (makas yönü kuralı yok)."""
    from .genel import cati_genel
    ck = cati_genel.cati_kur({"duzlemler": duz, "kalkanlar": [], "duvar_ustu": 250.0, "sacak": 0.0})
    yon = {"x" if abs(e["p"][1] - e["q"][1]) <= 1e-6 else "y" if abs(e["p"][0] - e["q"][0]) <= 1e-6 else "?"
           for e in ck["kenarlar"] if e["tur"] == "mahya"}
    if len(yon) != 1 or "?" in yon:
        raise IskeletHatasi("mahyalar tek yönde ve eksenlere paralel değil; makas yönü kuralı yok")
    return "y" if yon.pop() == "x" else "x"


def denetle(duz: list[dict], iz: Polygon, sacak: float) -> list[str]:
    from .genel import cati_genel
    bulgu = []
    R = iz.buffer(sacak, join_style=2, mitre_limit=10)
    poli = [Polygon(d["plan"]) for d in duz]
    bir = unary_union(poli)
    if abs(bir.area - R.area) > 1 or abs(sum(p.area for p in poli) - bir.area) > 1:
        bulgu.append(f"yüzler saçaklı ayak izini tam örtmüyor (hedef {R.area:.0f}, birleşim {bir.area:.0f}, toplam {sum(p.area for p in poli):.0f} cm²)")
    try:
        ck = cati_genel.cati_kur({"duzlemler": duz, "kalkanlar": [], "duvar_ustu": 250.0, "sacak": sacak})
    except (SystemExit, Exception) as e:                             # noqa: BLE001  (çekirdeğin hatası bulgudur)
        return bulgu + [f"cati_kur: {e}"]
    ust = [e for e in ck["kenarlar"] if e["tur"] not in ("sacak", "mahya", "kirma", "vadi")]
    if ust:
        bulgu.append("beklenmeyen kenar: " + ", ".join(f"{e['tur']} ({'/'.join(e['duzlemler'])})" for e in ust))
    return bulgu


__all__ = ["duzlemler", "denetle", "makas_ekseni", "yuzler", "IskeletHatasi", "box"]
