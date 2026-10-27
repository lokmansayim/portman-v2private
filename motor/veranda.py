"""BK-14 · Gövdeden taşan verandanın çatısı ve görünüşü (Pano Motor).

Veranda geometrisi `geometry._dis_verandalar`'da kurulur (`Plan.dis_verandalar`: dikdörtgen, cephe, kolonlar, açık kenarlar, çatı). Bu modül
yalnız ondan türeyen çizim geometrisini verir; DXF'in ön görünüşü (`dxf_out`), bayi paftasının çatı planı ve görünüşleri (`sunum`) ve IFC
(`ifc_uret`) aynı sayıları buradan alır. Taşan veranda yoksa hiçbiri çağrılmaz (çıktılar bayt bayt aynı).

Çatı: beşiğin mahyası cepheye diktir, kalkanı verandanın dış kenarındadır; tek eğim duvardan dışarı iner. Saçak dış kenarda ve iki yanda
`sacak_cm`; çatı cephenin hizasında biter (ana çatının saçağının altında kalır). Saçak kotu ana çatıyla aynı (duvar üstü + topuk), eğim
verandanın kendi eğimi. Mahyası ana çatının saçak kotunu aşan ve ana çatının saçak yanına (kalkan değil) dayanan veranda çatısında
iki çatının birleşimi (dere) çizilmez, uyarı düşer (`uyarilar`).
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


def uyarilar(plan: G.Plan, ie: dict) -> list[str]:
    """Çizimde sadeleştirilen birleşimler (K16: Motor kendi uyarısını düşürmez)."""
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
