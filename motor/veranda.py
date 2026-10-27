"""BK-14 · Gövdeden taşan verandanın çatısı ve görünüşü (Pano Motor).

Veranda geometrisi `geometry._dis_verandalar`'da kurulur (`Plan.dis_verandalar`: dikdörtgen, cephe, kolonlar, açık kenarlar, çatı). Bu modül
yalnız ondan türeyen çizim geometrisini verir; DXF'in ön görünüşü (`dxf_out`), bayi paftasının çatı planı ve görünüşleri (`sunum`) ve IFC
(`ifc_uret`) aynı sayıları buradan alır. Taşan veranda yoksa hiçbiri çağrılmaz (çıktılar bayt bayt aynı).

Çatı: beşiğin mahyası cepheye diktir, kalkanı verandanın dış kenarındadır; tek eğim duvardan dışarı iner. Saçak dış kenarda ve iki yanda
`sacak_cm`; çatı cephenin hizasında biter (ana çatının saçağının altında kalır). Saçak kotu ana çatıyla aynı (duvar üstü + topuk), eğim
verandanın kendi eğimi. Mahyası ana çatının saçak kotunu aşan ve ana çatının saçak yanına (kalkan değil) dayanan veranda çatısında
iki çatının birleşimi (dere) çizilmez; kalkan yanında ana çatının saçağının üstüne çıkan veranda çatısında da birleşim çizilmez. İkisinde
de uyarı düşer (`uyarilar`).
"""
from __future__ import annotations

from . import geometry as G

KIRIS_CM = 10.0                     # veranda kirişi ve dikmesi 10 × 10 (DXF blokları, liste "kutu profil 100 × 100")
YON = {"on": (0.0, -1.0), "arka": (0.0, 1.0), "sol": (-1.0, 0.0), "sag": (1.0, 0.0)}   # cepheden dışarı birim yön


def duvar_ustu(ie: dict) -> float:
    return float((ie.get("yapi") or {}).get("duvar_yuksekligi_cm", 250))


def ana_mahya_yonu(ie: dict) -> str:
    """Ana çatının mahya yönü: makaslar x'i geçiyorsa (varsayılan) mahya y boyunca."""
    return "y" if (ie.get("cati") or {}).get("makas_ekseni", "x") == "x" else "x"


def cati(v: dict, ie: dict) -> dict:
    """Veranda çatısı: plan düzlemleri (genel motorun `duzlemler` biçimi: plan, yukarı yönü, eğim, saçak kotu), mahya ve kotlar (cm)."""
    x0, y0, x1, y1 = v["rect"]
    c = v["cati"]; s = c["sacak_cm"]; eg = c["egim_yuzde"] / 100.0
    zs = duvar_ustu(ie) + c["topuk_cm"]
    cephe = v["cephe"]
    # saçaklı kutu: dış kenarda ve iki yanda saçak, cephede yok
    X0, Y0, X1, Y1 = (x0 - s, y0 - s, x1 + s, y1) if cephe == "on" else (x0 - s, y0, x1 + s, y1 + s) if cephe == "arka" else \
                     (x0 - s, y0 - s, x1, y1 + s) if cephe == "sol" else (x0, y0 - s, x1 + s, y1 + s)
    dikey = cephe in ("on", "arka")                     # mahya y boyunca (cepheye dik)
    if c["tip"] == "besik":
        if dikey:
            xm = (x0 + x1) / 2
            zm = zs + (xm - X0) * eg
            dz = [{"ad": "sol", "plan": [[X0, Y0], [xm, Y0], [xm, Y1], [X0, Y1]], "yukari": [1, 0], "egim": eg, "sacak_kotu": zs},
                  {"ad": "sağ", "plan": [[xm, Y0], [X1, Y0], [X1, Y1], [xm, Y1]], "yukari": [-1, 0], "egim": eg, "sacak_kotu": zs}]
            mahya = ((xm, Y0), (xm, Y1))
        else:
            ym = (y0 + y1) / 2
            zm = zs + (ym - Y0) * eg
            dz = [{"ad": "ön", "plan": [[X0, Y0], [X1, Y0], [X1, ym], [X0, ym]], "yukari": [0, 1], "egim": eg, "sacak_kotu": zs},
                  {"ad": "arka", "plan": [[X0, ym], [X1, ym], [X1, Y1], [X0, Y1]], "yukari": [0, -1], "egim": eg, "sacak_kotu": zs}]
            mahya = ((X0, ym), (X1, ym))
    else:                                               # tek eğim: dış kenarda alçak, cephede yüksek
        ux, uy = YON[cephe]
        derin = (Y1 - Y0) if dikey else (X1 - X0)
        zm = zs + derin * eg
        dz = [{"ad": "tek", "plan": [[X0, Y0], [X1, Y0], [X1, Y1], [X0, Y1]], "yukari": [-ux, -uy], "egim": eg, "sacak_kotu": zs}]
        mahya = None
    return {"tip": c["tip"], "kutu": (X0, Y0, X1, Y1), "duzlemler": dz, "mahya": mahya, "sacak_kotu": zs, "mahya_kotu": zm,
            "egim": eg, "sacak": s}


def kot(dz: dict, x: float, y: float) -> float:
    """Çatı düzleminin (genel motorun `duzlemler` biçimi) plandaki (x, y) noktasındaki kotu: saçak kenarında saçak kotu, yukarı yönde eğimle."""
    ux, uy = dz["yukari"]
    alt = min(px * ux + py * uy for px, py in dz["plan"])
    return dz["sacak_kotu"] + dz["egim"] * (x * ux + y * uy - alt)


def ana_catiya_tasma(plan: G.Plan, ie: dict, v: dict) -> float | None:
    """Veranda çatısının, planda ana çatıyla üst üste geldiği yerde (ana çatının saçak bandı) ana çatının yüzünün en çok kaç cm üstüne
    çıktığı. Negatif ya da sıfır: altında ya da aynı düzlemde (TK-01 arka verandasının sol yüzü ana çatının sol yüzünün devamı). Üst üste
    gelmiyorsa ya da ana çatı beşik değilse None. İki düzlem farkı her kesişim çokgeninde doğrusal: en büyüğü köşelerde."""
    from shapely.geometry import Polygon
    from . import sunum                                 # burada: sunum bu modülü içe aktarır
    ana = sunum.cati_tanimi(plan, ie)
    if ana is None:
        return None
    en = None
    for dv in cati(v, ie)["duzlemler"]:
        pv = Polygon(dv["plan"])
        for dm in ana["duzlemler"]:
            k = pv.intersection(Polygon(dm["plan"]))
            for g in getattr(k, "geoms", [k]):
                if g.is_empty or g.geom_type != "Polygon" or g.area < 1e-6:
                    continue
                for x, y in g.exterior.coords:
                    f = kot(dv, x, y) - kot(dm, x, y)
                    en = f if en is None else max(en, f)
    return en


def uyarilar(plan: G.Plan, ie: dict) -> list[str]:
    """Çizimde sadeleştirilen birleşimler (K16: Motor kendi uyarısını düşürmez). Veranda çatısı ana çatının saçak yanına dayanıp mahyası
    saçağın üstüne çıkıyorsa iki çatının birleşimi (dere) çizilmez. Kalkan yanındaki veranda çatısı da ana çatının kalkan saçağının üstüne
    çıkabilir (dik eğim, tek eğimin yüksek ucu): planda üst üste geldikleri bantta ana çatının yüzünü 0,5 cm'den çok aşarsa uyarı (geometri
    hakemi, 27 Ekim)."""
    out = []
    ana = ie.get("cati") or {}
    zs_ana = duvar_ustu(ie) + float(ana.get("topuk_cm", 10))
    mahya_y = ana_mahya_yonu(ie) == "y"
    for v in plan.dis_verandalar:
        kalkan_yuzu = (v["cephe"] in ("on", "arka")) == mahya_y      # ana çatının kalkanına dayanıyor (TK-01)
        if not kalkan_yuzu and cati(v, ie)["mahya_kotu"] > zs_ana + 1e-6:
            out.append(f"Veranda {v['ad']}: çatısı ana çatının saçak yanına dayanıyor, " +
                       ("mahyası saçağın üstünde; iki çatının birleşimi (dere) çizimde yok, listede çapraz beşiğin deresi sayılır (5.1)"
                        if v["cati"]["tip"] == "besik" else
                        "yüksek ucu saçağın üstünde; iki çatının birleşimi çizimde yok, kural kitabında yok"))
            continue
        t = ana_catiya_tasma(plan, ie, v)
        if t is not None and t > 0.5:
            out.append(f"Veranda {v['ad']}: çatısı ana çatının kalkan saçağının altında kalmıyor, yüzünü {t:.0f} cm aşıyor; iki çatının "
                       f"birleşimi çizimde yok, kural kitabında yok")
    return out


def gorunus_parcalari(plan: G.Plan, ie: dict, taraf: str) -> list[dict]:
    """`taraf` (on | arka | sol | sag) görünüşündeki veranda parçaları: [{"tur": kolon | kiris | cati | alin, "u": [(u, z), ...], "derinlik": d}].
    u görünüşün yatay ekseni (bakanın soldan sağa), z kot; `derinlik` bakana uzaklık sırası için (büyük = uzak). Kolon 0 … duvar üstü − 10,
    kiriş duvar üstü − 10 … duvar üstü (IFC ile aynı)."""
    H0 = duvar_ustu(ie)
    u_of = {"on": lambda x, y: x, "arka": lambda x, y: -x, "sol": lambda x, y: -y, "sag": lambda x, y: y}[taraf]
    d_of = {"on": lambda x, y: y, "arka": lambda x, y: -y, "sol": lambda x, y: x, "sag": lambda x, y: -x}[taraf]

    def kutu_u(x0, y0, x1, y1):
        us = [u_of(x, y) for x in (x0, x1) for y in (y0, y1)]
        ds = [d_of(x, y) for x in (x0, x1) for y in (y0, y1)]
        return min(us), max(us), min(ds)

    out = []
    for v in plan.dis_verandalar:
        for (x0, y0, x1, y1) in v["kolonlar"]:
            u0, u1, dd = kutu_u(x0, y0, x1, y1)
            out.append({"tur": "kolon", "u": [(u0, 0.0), (u1, 0.0), (u1, H0 - KIRIS_CM), (u0, H0 - KIRIS_CM)], "derinlik": dd, "veranda": v["ad"]})
        for (x0, y0, x1, y1) in v["kirisler"]:
            u0, u1, dd = kutu_u(x0, y0, x1, y1)
            out.append({"tur": "kiris", "u": [(u0, H0 - KIRIS_CM), (u1, H0 - KIRIS_CM), (u1, H0), (u0, H0)], "derinlik": dd, "veranda": v["ad"]})
        C = cati(v, ie)
        X0, Y0, X1, Y1 = C["kutu"]
        u0, u1, dd = kutu_u(X0, Y0, X1, Y1)
        zs, zm = C["sacak_kotu"], C["mahya_kotu"]
        boyuna = (v["cephe"] in ("on", "arka")) == (taraf in ("on", "arka"))   # bakış mahyaya paralel: kalkan görünür
        if C["tip"] == "besik":
            if boyuna:
                um = (u0 + u1) / 2
                out.append({"tur": "alin", "u": [(u0 + C["sacak"], H0), (u1 - C["sacak"], H0), (u1 - C["sacak"], zs), (um, zm), (u0 + C["sacak"], zs)],
                            "derinlik": dd, "veranda": v["ad"]})
                out.append({"tur": "cati", "u": [(u0, zs), (um, zm), (u1, zs)], "kalkan": True, "derinlik": dd - 0.1, "veranda": v["ad"]})
            else:
                out.append({"tur": "cati", "u": [(u0, zs), (u1, zs), (u1, zm), (u0, zm)], "derinlik": dd, "veranda": v["ad"]})
        else:
            ux, uy = YON[v["cephe"]]
            if boyuna:                                  # bakan verandanın önünde ya da arkasında: eğim bakana doğru, bant
                out.append({"tur": "cati", "u": [(u0, zs), (u1, zs), (u1, zm), (u0, zm)], "derinlik": dd, "veranda": v["ad"]})
            else:                                       # yandan: dik üçgen, cephede yüksek
                dis_u = u_of(X0 if ux < 0 else X1, Y0 if uy < 0 else Y1) if (ux or uy) else u0
                ic_u = u1 if abs(dis_u - u0) < 1e-6 else u0
                out.append({"tur": "cati", "u": [(dis_u, zs), (ic_u, zm), (ic_u, zs)], "derinlik": dd, "veranda": v["ad"]})
    return out
