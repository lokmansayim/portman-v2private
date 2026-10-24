"""Çatı katmanları: aşık, kaplama, baş makas betopanı, dere ve iniş. Kurallar `kurallar/yerlesim/prefabrik.json`'da (karar C ve PK-01 paftası).

Çatı bugünkü IFC'deki gibidir (`motor.ifc_uret.IfcUretici.cati`): makas üst başlığının üst yüzü saçak ucunda `duvar yüksekliği + topuk +
10`, eğimle mahyaya çıkar. Yerel eksenler: `u` makasın açıklığı (makas ekseni), `v` mahya boyu. Mahya boyu bina boyu + iki saçaktır.
Katmanlar yalnız beşik çatıda kurulur; bugünkü IFC çatıyı her zaman beşik çizdiği için başka çatı tipinde çatı parçası "kural yok" yazar.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon, box

from .tavan import parcala

ESIK = 1e-6


def cerceve(g: dict) -> dict:
    c = g["cati"]
    mx = c["makas_ekseni"] == "x"
    aciklik, boy = (g["W"], g["H"]) if mx else (g["H"], g["W"])
    s, eg = c["sacak"], c["egim"]
    zs = g["duvar_h"] + c["topuk"]
    um = aciklik / 2
    return {"mx": mx, "aciklik": aciklik, "boy": boy, "s": s, "eg": eg, "zs": zs, "um": um, "kos": 1 / math.sqrt(1 + eg * eg),
            "egik": (um + s) * math.sqrt(1 + eg * eg), "v0": -s, "v1": boy + s,
            "v_bas": g["baslangic"]["y" if mx else "x"]}


def _ust(F: dict, u: float) -> float:
    """Makas üst başlığının üst yüzünün kotu (cm)."""
    return F["zs"] + 10 + (min(u, F["aciklik"] - u) + F["s"]) * F["eg"]


def _kutu(F: dict, u0, u1, v0, v1, z0, z1) -> dict:
    x0, x1, y0, y1 = (u0, u1, v0, v1) if F["mx"] else (v0, v1, u0, u1)
    return {"tip": "kutu", "kutu": [x0, y0, z0, x1, y1, z1]}


def _prizma(F: dict, uz: list, v0: float, v1: float) -> dict:
    """`u`–`z` düzlemindeki kesit, `v0`..`v1` boyunca."""
    return {"tip": "prizma", "duzlem": "xz" if F["mx"] else "yz", "noktalar": [list(p) for p in uz], "a0": v0, "a1": v1}


def asik(g: dict, K: dict) -> list[dict]:
    """Karar C: her yüzde ilk sıra mahyada, sonra kitabın aralığıyla (eğik boyca); saçağa aralıktan az kalınca saçakta bir sıra daha;
    saçak sırasına `en_kisa`'dan yakın kalan sıra konmaz. Sıra boyu mahya boyu; dizilimin başladığı uçtan tam parçalar (parça boyu − pay),
    kalan son parçada; `en_kisa`'dan kısa kalan parçasız boşluk (omegadaki gibi)."""
    F = cerceve(g)
    a, w = K["kesit_asik"]
    d = []
    k = 0
    while k * K["aralik"] < F["egik"] - ESIK:
        d.append(k * K["aralik"]); k += 1
    if len(d) > 1 and F["egik"] - d[-1] < K["en_kisa"] - ESIK:          # saçak sırası son sıranın yerini alır
        d.pop()
    d.append(F["egik"])
    out = []
    for yuz, isaret in (("sol", -1), ("sag", 1)):
        for i, di in enumerate(d):
            h = di * F["kos"]
            hg = min(max(h, w / 2), F["um"] + F["s"] - w / 2)                 # gösterim: kesit yüzün içinde kalsın
            u = F["um"] + isaret * hg
            z = _ust(F, u)
            for v0, v1 in parcala(F["v0"], F["v1"], K["tam"], K["en_kisa"], F["v_bas"] == "max")[0]:
                out.append({"kural": "asik_sirasi", "parca": "asik", "boy_cm": round(v1 - v0, 4),
                            "geo": _kutu(F, u - w / 2, u + w / 2, v0, v1, z, z + a),
                            "bilgi": {"Yuz": yuz, "Sira": i + 1, "MahyadanEgik_cm": round(di, 2)},
                            "aciklama": f"{yuz} yüz, {i + 1}. sıra (mahyadan {di:.1f} cm)"})
    return out


def kaplama(g: dict, K: dict) -> list[dict]:
    """Her yüz ⌈mahya boyu ÷ kapatma⌉ şerit (liste üretecinin sayısı): ilk şerit dizilimin başladığı uçtan, son şerit yüzün öteki ucundan
    taşar (kesilmez; PK-01 paftası). Şerit mahyadan saçağa, boyu eğik boy + taşma, `yuvarlama`'ya yukarı (liste üretecinin boyu)."""
    F = cerceve(g)
    a = K["kesit_asik"][0]
    t = K["kalinlik_kaplama"]
    L = math.ceil((F["egik"] / 100 + K["tasma_m"]) * 1000 / K["yuvarlama_mm"] - 1e-9) * K["yuvarlama_mm"] / 10
    out = []
    for yuz, isaret in (("sol", -1), ("sag", 1)):
        zr = _ust(F, F["um"]) + a
        du, dz = isaret * L * F["kos"], -L * F["kos"] * F["eg"]
        kesit = [(F["um"], zr), (F["um"] + du, zr + dz), (F["um"] + du, zr + dz + t), (F["um"], zr + t)]
        b = K["kapatma_cm"]
        n = math.ceil((F["v1"] - F["v0"]) / b - 1e-9)
        for i in range(n):
            v0, v1 = (F["v1"] - (i + 1) * b, F["v1"] - i * b) if F["v_bas"] == "max" else (F["v0"] + i * b, F["v0"] + (i + 1) * b)
            tasma = round(max(0.0, F["v0"] - v0, v1 - F["v1"]), 2)
            out.append({"kural": "cati_kaplamasi", "parca": "panel", "geo": _prizma(F, kesit, v0, v1), "alan_m2": round(b * L / 1e4, 4),
                        "bilgi": {"Yuz": yuz, "Serit": i + 1, "PanelBoyu_cm": L, "Genislik_cm": b, "Tasma_cm": tasma},
                        "aciklama": f"{yuz} yüz, {i + 1}. şerit ({b:g} × {L:g}" + (f"; {tasma:g} cm taşar)" if tasma else ")")})
    return out


def betopan(g: dict, K: dict) -> tuple[list[dict], str | None]:
    """Her baş makasın dış yüzünde levhalar yatık, makasın alt başlığından başlayarak mahyaya ortalı, tek sıra yan yana; sayı liste
    kuralından (H5: ⌈katsayı × saçaklı üçgen ÷ levha⌉). Levha binanın dış yüzünde (uç duvarın dış yüzüyle aynı düzlem); gösterimde
    makasın üst başlığının altında kalan kısmı çizilir (levha yerinde kesilir), sayı ve ölçü tam levhadır. Üçgenin yüksekliği (alt
    başlıktan mahyada üst başlığın alt yüzüne) levhanın kısa kenarını geçerse tek sıra örtmez: parça yok, neden döner ("kural yok")."""
    F = cerceve(g)
    yuks = (F["aciklik"] / 200 + F["s"] / 100) * F["eg"]
    n = math.ceil(K["katsayi"] * 0.5 * (F["aciklik"] / 100 + 2 * F["s"] / 100) * yuks / K["levha_m2"] - 1e-9)
    lu, lz = K["levha_cm"]
    t = K["kalinlik_betopan"]
    z0 = g["duvar_h"]
    h = _ust(F, F["um"]) - 10 - z0                                      # üst başlığın alt yüzü (`ifc_uret`: başlık 10 cm)
    if h > lz + ESIK:
        return [], f"üçgen {h:.1f} cm yüksek, levha {lz:g} cm: tek sıra örtmez"
    ucgen = Polygon([(-F["s"], z0), (F["aciklik"] + F["s"], z0), (F["aciklik"] + F["s"], _ust(F, F["aciklik"] + F["s"])),
                     (F["um"], _ust(F, F["um"])), (-F["s"], _ust(F, -F["s"]))])
    out = []
    for m in sorted((m for m in g["makaslar"] if m["rol"] == "bas"), key=lambda m: m["konum"]):
        v0, v1 = (-t, 0.0) if m["konum"] < F["boy"] / 2 else (F["boy"], F["boy"] + t)
        for i in range(n):
            u0 = F["um"] - n * lu / 2 + i * lu
            kesik = box(u0, z0, u0 + lu, z0 + lz).intersection(ucgen)
            if kesik.is_empty or kesik.geom_type != "Polygon":
                return [], f"{m['ad']}: {i + 1}. levha üçgenin dışında kalıyor (tek sıra {n} levha)"
            out.append({"kural": "bas_makas_betopani_yerlesimi", "parca": "levha", "alan_m2": round(lu * lz / 1e4, 4),
                        "geo": _prizma(F, [(round(u, 4), round(z, 4)) for u, z in kesik.exterior.coords[:-1]], v0, v1),
                        "bilgi": {"Makas": m["ad"], "Levha": i + 1, "LevhaAdedi": n, "Levha_cm": f"{lu:g} × {lz:g}"},
                        "aciklama": f"{m['ad']}, {i + 1}. levha ({lu:g} × {lz:g})"})
    return out, None


def dere(g: dict, K: dict) -> list[dict]:
    """Beşikte her saçak kenarı boyunca bir dere hattı, boyu mahya boyu. İniş her hattın iki ucunda (köşe başına `kose_basina`); eşiği
    geçen hattın ortasında bir iniş daha."""
    F = cerceve(g)
    dw, dh = K["kesit_dere"]
    iw = K["kesit_inis"]
    ze = F["zs"] + 10
    out = []
    for yuz, ue in (("sol", -F["s"]), ("sag", F["aciklik"] + F["s"])):
        u0, u1 = (ue - dw, ue) if yuz == "sol" else (ue, ue + dw)
        boy = F["v1"] - F["v0"]
        out.append({"kural": "dere_hatti", "parca": "dere", "boy_cm": round(boy, 4),
                    "geo": _kutu(F, u0, u1, F["v0"], F["v1"], ze - dh, ze), "bilgi": {"Yuz": yuz},
                    "aciklama": f"{yuz} saçak, {boy:g} cm"})
        n = int(K["kose_basina"])
        konumlar = ([("uç", F["v0"] + iw / 2 + k * 2 * iw) for k in range(n)] + [("uç", F["v1"] - iw / 2 - k * 2 * iw) for k in range(n)])
        if boy > K["orta_esik_cm"] + ESIK:
            konumlar.insert(n, ("orta", (F["v0"] + F["v1"]) / 2))
        uc = (u0 + u1) / 2
        for yer, v in konumlar:
            out.append({"kural": "dere_hatti", "parca": "inis",
                        "geo": _kutu(F, uc - iw / 2, uc + iw / 2, v - iw / 2, v + iw / 2, ze - dh - 15, ze - dh),
                        "bilgi": {"Yuz": yuz, "Yer": yer}, "aciklama": f"{yuz} saçak, {yer}"})
    return out
