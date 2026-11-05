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


def teras_paneli(v: dict, ie: dict) -> dict:
    """D-52: teras paneli (`cati.tip: teras_paneli`): 8 cm kalın panel, üst yüzü duvarda duvar üstünün (ana çatının saçak altı çizgisi) 10 cm
    altında; D-52 ek (Lokman, 5 Kasım 2026 00:36: "teraslara biraz eğim vereceksin") duvardan dışarı `egim_yuzde` ile iner. Planda duvardan
    `cikma_cm` dışarı, cephe boyunca verandanın eni. `cati` ile aynı biçim (tek düzlem: saçak kotu dış kenarda, mahya kotu duvarda) +
    `kalinlik`, `dis_kiris_ustu` (dış kiriş düz, panelin altında: panelin altının dış kirişin dış yüzündeki kotu) ve `kolon_ustu` (dış kirişin
    altı). Yan kiriş panelin altında eğimle (`teras_kirisi`)."""
    x0, y0, x1, y1 = v["rect"]
    c = v["cati"]; k = c["cikma_cm"]; cephe = v["cephe"]; e = c["egim_yuzde"] / 100.0
    X0, Y0, X1, Y1 = (x0, y1 - k, x1, y1) if cephe == "on" else (x0, y0, x1, y0 + k) if cephe == "arka" else \
                     (x1 - k, y0, x1, y1) if cephe == "sol" else (x0, y0, x0 + k, y1)
    z_ic = duvar_ustu(ie) - G.TERAS_PANELI_SACAK_ALTI_CM
    z_dis = z_ic - e * k
    ux, uy = YON[cephe]
    t = G.TERAS_PANELI_KALINLIK_CM
    dz = {"ad": "panel", "plan": [[X0, Y0], [X1, Y0], [X1, Y1], [X0, Y1]], "yukari": [-ux, -uy], "egim": e, "sacak_kotu": z_dis}
    dis = v["kirisler"][0]                              # `geometry._dis_verandalar`: dış kenar, iki yan
    h = min(kot(dz, x, y) for x in (dis[0], dis[2]) for y in (dis[1], dis[3])) - t
    return {"tip": "teras_paneli", "kutu": (X0, Y0, X1, Y1), "duzlemler": [dz], "mahya": None, "sacak_kotu": z_dis, "mahya_kotu": z_ic,
            "egim": e, "sacak": 0.0, "kalinlik": t, "dis_kiris_ustu": h, "kolon_ustu": h - KIRIS_CM}


def teras_kirisi(T: dict, v: dict, rect) -> tuple[bool, float, float]:
    """D-52 ek: teras panelinin altındaki kiriş: (eğik mi, duvar ucunda üstü, dış ucunda üstü). Dış kenardaki (cepheye paralel) kiriş düz,
    üstü `dis_kiris_ustu`; yandaki kiriş panelin altında eğimle (üstü panelin altı), 10 cm."""
    x0, y0, x1, y1 = rect
    if ((x1 - x0) >= (y1 - y0)) == (v["cephe"] in ("on", "arka")):
        return False, T["dis_kiris_ustu"], T["dis_kiris_ustu"]
    dz = T["duzlemler"][0]
    kotlar = [kot(dz, x, y) - T["kalinlik"] for x in (x0, x1) for y in (y0, y1)]
    return True, max(kotlar), min(kotlar)


def cati(v: dict, ie: dict) -> dict:
    """Veranda çatısı: plan düzlemleri (genel motorun `duzlemler` biçimi: plan, yukarı yönü, eğim, saçak kotu), mahya ve kotlar (cm)."""
    if v["cati"]["tip"] == "teras_paneli":
        return teras_paneli(v, ie)
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
        if v["cati"]["tip"] == "teras_paneli":                          # D-52: düz panel ana çatının saçağının altında; birleşim yok
            continue
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


def izdusum(taraf: str):
    """`taraf` (on | arka | sol | sag) görünüşünün izdüşümü: plandaki kutu (x0, y0, x1, y1) → (u0, u1, derinlik). u görünüşün yatay ekseni
    (bakanın soldan sağa), derinlik bakana uzaklık sırası için (küçük = yakın). Bayi paftasının görünüşü de bunu kullanır."""
    u_of = {"on": lambda x, y: x, "arka": lambda x, y: -x, "sol": lambda x, y: -y, "sag": lambda x, y: y}[taraf]
    d_of = {"on": lambda x, y: y, "arka": lambda x, y: -y, "sol": lambda x, y: x, "sag": lambda x, y: -x}[taraf]

    def kutu_u(x0, y0, x1, y1):
        us = [u_of(x, y) for x in (x0, x1) for y in (y0, y1)]
        return min(us), max(us), min(d_of(x, y) for x in (x0, x1) for y in (y0, y1))
    kutu_u.u = u_of                                     # nokta izdüşümü (tek eğimin dış ucu)
    return kutu_u


def gorunus_parcalari(plan: G.Plan, ie: dict, taraf: str) -> list[dict]:
    """`taraf` (on | arka | sol | sag) görünüşündeki veranda parçaları: [{"tur": kolon | kiris | cati | sacak | topuk, "u": [(u, z), ...],
    "derinlik": d}]. u görünüşün yatay ekseni (bakanın soldan sağa), z kot; `derinlik` bakana uzaklık sırası için (büyük = uzak). Kolon 0 … duvar
    üstü − 10, kiriş duvar üstü − 10 … duvar üstü (IFC ile aynı). `sacak` ve `topuk` açık çizgidir (`acik`): ana çatının görünüşündeki gibi
    saçak altı çizgisi duvar üstünde saçak ucundan saçak ucuna, iki uçta topuk duvar üstünden saçak kotuna (BK-18 ek; Lokman, 29 Ekim 2026).
    Kalkanın alın dolgusu (kolon yüzlerinden çatıya dikey kenarlı çerçeve) görünüşte çizilmez: veranda çatısı ana çatı gibi saçak, topuk ve iki
    eğimle görünür (D-31; Lokman, 29 Ekim 2026 11:07–11:09: "saçaklardan yukarı doğru çıkan çizgiler var olmamalı", "veranda çatısının
    makaslarını ayrı çizmiştin onu da çizim kuralından kaldır"); IFC'nin alın dolgusu aynen."""
    H0 = duvar_ustu(ie)
    kutu_u = izdusum(taraf)
    u_of = kutu_u.u

    out = []
    for v in plan.dis_verandalar:
        if v["cati"]["tip"] == "teras_paneli":                          # D-52: kolon ve kiriş panelin altında, panel düz bant
            out += _teras_paneli_parcalari(v, ie, kutu_u)
            continue
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
        out.append({"tur": "sacak", "u": [(u0, H0), (u1, H0)], "acik": True, "derinlik": dd - 0.1, "veranda": v["ad"]})
        if zs > H0 + 1e-6:
            out += [{"tur": "topuk", "u": [(u, H0), (u, zs)], "acik": True, "derinlik": dd - 0.1, "veranda": v["ad"]} for u in (u0, u1)]
        if C["tip"] == "besik":
            if boyuna:
                um = (u0 + u1) / 2
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


def _teras_paneli_parcalari(v: dict, ie: dict, kutu_u) -> list[dict]:
    """D-52: teras panelinin görünüşü (`teras_paneli`). Kolon zeminden dış kirişin altına, dış kiriş (10 × 10) panelin altında; panel 8 cm.
    D-52 ek (eğim): önden ve arkadan bakınca (bakış cepheye dik) panel cephe boyunca bant, dış kenarın alt çizgisinden duvardaki üst kotuna,
    dış kenarın üstü açık çizgi; yan kiriş panelin ve dış kirişin ardında kalır, çizilmez. Yandan bakınca panel ve yan kiriş duvardan dışarı
    inen eğik dörtgen, bir kez eğim yazısı. Saçak ve topuk çizgisi yok (çatı gibi şekilli değil)."""
    T = teras_paneli(v, ie)
    t, z_ic, z_dis, h = T["kalinlik"], T["mahya_kotu"], T["sacak_kotu"], T["kolon_ustu"]
    u_of = kutu_u.u
    ux, uy = YON[v["cephe"]]
    X0, Y0, X1, Y1 = T["kutu"]
    u0, u1, dd = kutu_u(X0, Y0, X1, Y1)
    yandan = abs(u_of(ux, uy) - u_of(0.0, 0.0)) > 1e-6          # bakışın yatayı verandanın derinliği boyunca
    out = []
    for (x0, y0, x1, y1) in v["kolonlar"]:
        a0, a1, d_ = kutu_u(x0, y0, x1, y1)
        out.append({"tur": "kolon", "u": [(a0, 0.0), (a1, 0.0), (a1, h), (a0, h)], "derinlik": d_, "veranda": v["ad"]})
    for r in v["kirisler"]:
        egik, z_w, z_o = teras_kirisi(T, v, r)
        a0, a1, d_ = kutu_u(*r)
        if not egik:
            out.append({"tur": "kiris", "u": [(a0, z_o - KIRIS_CM), (a1, z_o - KIRIS_CM), (a1, z_o), (a0, z_o)], "derinlik": d_, "veranda": v["ad"]})
        elif yandan:
            uw, uo = (a0, a1) if abs(u_of(ux, uy) - u_of(0.0, 0.0) - 1.0) < 1e-6 else (a1, a0)   # duvar ucu, dış uç
            out.append({"tur": "kiris", "u": [(uw, z_w - KIRIS_CM), (uo, z_o - KIRIS_CM), (uo, z_o), (uw, z_w)], "derinlik": d_, "veranda": v["ad"]})
    if yandan:
        uw, uo = (u0, u1) if abs(u_of(ux, uy) - u_of(0.0, 0.0) - 1.0) < 1e-6 else (u1, u0)
        out.append({"tur": "cati", "u": [(uw, z_ic - t), (uo, z_dis - t), (uo, z_dis), (uw, z_ic)], "derinlik": dd - 0.1, "veranda": v["ad"],
                    "panel": True})
        out.append({"tur": "yazi", "metin": "%" + f"{v['cati']['egim_yuzde']:g}".replace(".", ","),
                    "u": [((uw + uo) / 2, (z_ic + z_dis) / 2 + 14)], "veranda": v["ad"]})
    else:
        out.append({"tur": "cati", "u": [(u0, z_dis - t), (u1, z_dis - t), (u1, z_ic), (u0, z_ic)], "derinlik": dd - 0.1, "veranda": v["ad"],
                    "panel": True})
        out.append({"tur": "cati", "u": [(u0, z_dis), (u1, z_dis)], "acik": True, "derinlik": dd - 0.1, "veranda": v["ad"]})
    return out
