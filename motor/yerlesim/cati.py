"""Çatı katmanları: aşık, kaplama, baş makas betopanı, dere ve iniş. Kurallar `kurallar/yerlesim/prefabrik.json`'da (karar C ve PK-01 paftası).

Çatı bugünkü IFC'deki gibidir (`motor.ifc_uret.IfcUretici.cati`): makas üst başlığının üst yüzü saçak ucunda `duvar yüksekliği + topuk +
10`, eğimle mahyaya çıkar. Yerel eksenler: `u` makasın açıklığı (makas ekseni), `v` mahya boyu. Mahya boyu bina boyu + iki saçaktır.
Katmanlar yalnız beşik çatıda kurulur; bugünkü IFC çatıyı her zaman beşik çizdiği için başka çatı tipinde çatı parçası "kural yok" yazar.

Gövdeden taşan verandanın çatısı (K5b, `veranda.py`) aynı işlevlerle kendi çerçevesinde kurulur (`F`): `ou` yerel `u`'nun dünyadaki
başı, `v` dünya koordinatıdır (`v0`..`v1` çatının, `w0`..`w1` kirişlerin boyu). Verilmezse çerçeve ana çatınınkidir (`cerceve(g)`).
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

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
    if F.get("ou"):                                                     # taşan verandanın çerçevesi (K5b): yerel u dünyada ou'dan başlar
        u0, u1 = u0 + F["ou"], u1 + F["ou"]
    x0, x1, y0, y1 = (u0, u1, v0, v1) if F["mx"] else (v0, v1, u0, u1)
    return {"tip": "kutu", "kutu": [x0, y0, z0, x1, y1, z1]}


def _prizma(F: dict, uz: list, v0: float, v1: float) -> dict:
    """`u`–`z` düzlemindeki kesit, `v0`..`v1` boyunca."""
    o = F.get("ou") or 0.0
    return {"tip": "prizma", "duzlem": "xz" if F["mx"] else "yz", "noktalar": [[p[0] + o, p[1]] if o else list(p) for p in uz], "a0": v0, "a1": v1}


def asik(g: dict, K: dict, F: dict | None = None) -> list[dict]:
    """Karar C: her yüzde ilk sıra mahyada, sonra kitabın aralığıyla (eğik boyca); saçağa aralıktan az kalınca saçakta bir sıra daha;
    saçak sırasına `en_kisa`'dan yakın kalan sıra konmaz. Sıra boyu mahya boyu; dizilimin başladığı uçtan tam parçalar (parça boyu − pay),
    kalan son parçada; `en_kisa`'dan kısa kalan parçasız boşluk (omegadaki gibi)."""
    from motor.prefabrik_liste import asik_mesafeleri                   # sıralar liste üretecinin sayısıyla tek kaynaktan (D-28 madde 1)
    F = F or cerceve(g)
    a, w = K["kesit_asik"]
    d = asik_mesafeleri(F["egik"], K["aralik"], K["en_kisa"], ESIK)        # saçak sırası son sıranın yerini alabilir
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


def kaplama(g: dict, K: dict, F: dict | None = None, iki_yuz: bool = False) -> list[dict]:
    """Her yüz ⌈mahya boyu ÷ kapatma⌉ şerit (liste üretecinin sayısı): ilk şerit dizilimin başladığı uçtan, son şerit yüzün öteki ucundan
    taşar (kesilmez; PK-01 paftası). Şerit mahyadan saçağa, boyu eğik boy + taşma, `yuvarlama`'ya yukarı (liste üretecinin boyu).
    `iki_yuz` (taşan verandanın çatısı, K5b): iki yüz birlikte ⌈2 × mahya boyu ÷ kapatma⌉ (liste üretecinin ek çatı parçası sayısı): her yüzde
    tam şeritler, iki yüzün artan şeritleri bir panele sığıyorsa bir panelden (iki prizmalı parça), sığmıyorsa her yüzün son şeridi gövde
    duvarında kesilir (ötesi ana çatının kalkan saçağı)."""
    F = F or cerceve(g)
    a = K["kesit_asik"][0]
    t = K["kalinlik_kaplama"]
    L = math.ceil((F["egik"] / 100 + K["tasma_m"]) * 1000 / K["yuvarlama_mm"] - 1e-9) * K["yuvarlama_mm"] / 10
    b = K["kapatma_cm"]
    kesitler = {}
    for yuz, isaret in (("sol", -1), ("sag", 1)):
        zr = _ust(F, F["um"]) + a
        du, dz = isaret * L * F["kos"], -L * F["kos"] * F["eg"]
        kesitler[yuz] = [(F["um"], zr), (F["um"] + du, zr + dz), (F["um"] + du, zr + dz + t), (F["um"], zr + t)]

    def serit(i: int, gen: float = b) -> tuple[float, float]:
        return (F["v1"] - i * b - gen, F["v1"] - i * b) if F["v_bas"] == "max" else (F["v0"] + i * b, F["v0"] + i * b + gen)

    def parca(yuz, i, v0, v1, geo=None, **ek):
        tasma = round(max(0.0, F["v0"] - v0, v1 - F["v1"]), 2)
        return {"kural": "cati_kaplamasi", "parca": "panel", "geo": geo or _prizma(F, kesitler[yuz], v0, v1), "alan_m2": round(b * L / 1e4, 4),
                "bilgi": {"Yuz": yuz, "Serit": i + 1, "PanelBoyu_cm": L, "Genislik_cm": b, "Tasma_cm": tasma, **ek},
                "aciklama": f"{'iki' if yuz == 'iki' else yuz} yüz, {i + 1}. şerit ({b:g} × {L:g}" + (f"; {tasma:g} cm taşar)" if tasma else ")")}
    out = []
    m = F["v1"] - F["v0"]
    if not iki_yuz:
        n = math.ceil(m / b - 1e-9)
        for yuz in ("sol", "sag"):
            for i in range(n):
                out.append(parca(yuz, i, *serit(i)))
        return out
    n = math.floor(m / b + 1e-9)
    r = m - n * b
    for yuz in ("sol", "sag"):
        for i in range(n):
            out.append(parca(yuz, i, *serit(i)))
    if r > ESIK and 2 * r <= b + ESIK:                                  # iki yüzün artan şeritleri bir panelden
        v0, v1 = serit(n, r)
        p = parca("iki", n, v0, v1, {"tip": "coklu", "parcalar": [_prizma(F, kesitler[y], v0, v1) for y in ("sol", "sag")]}, Kesim_cm=round(r, 4))
        p["aciklama"] = f"iki yüz, {n + 1}. şerit: bir panelden iki yüzün {r:g} cm'lik şeritleri ({b:g} × {L:g})"
        out.append(p)
    elif r > ESIK:
        for yuz in ("sol", "sag"):
            p = parca(yuz, n, *serit(n, r), Kesim_cm=round(r, 4))
            p["aciklama"] = f"{yuz} yüz, {n + 1}. şerit: duvarda {r:g} cm'ye kesilir ({b:g} × {L:g})"
            out.append(p)
    return out


def _uz(k) -> list[tuple[float, float]]:
    return [(round(u, 4), round(z, 4)) for u, z in k.exterior.coords[:-1]]


def betopan(g: dict, K: dict, F: dict | None = None, kalkanlar: list[dict] | None = None) -> tuple[list[dict], str | None]:
    """Her baş makasın dış yüzünde levhalar, makasın alt başlığından başlayarak; sayı liste kuralından (H5: ⌈katsayı × saçaklı üçgen ÷
    levha⌉). Levha binanın dış yüzünde (uç duvarın dış yüzüyle aynı düzlem); gösterimde makasın üst başlığının altında kalan kısmı çizilir
    (levha yerinde kesilir), sayı ve ölçü tam levhadır. Üçgenin yüksekliği (alt başlıktan mahyada üst başlığın alt yüzüne) levhanın kısa
    kenarını geçmezse levhalar yatık, mahyaya ortalı, tek sıra yan yana (PK-01). Geçip uzun kenarını geçmezse levhalar dikey (K5b, PK-07
    s. 10): mahyadan dışa, iki yana sırayla (önce `u`'nun arttığı yan); iki uçta kalan üçgen çatı çizgisinde kesilen parçalarla (artan
    betopan) kapanır, o yandaki en dıştaki levhanın parçasıdır (iki prizmalı parça), sayıya eklenmez. Uzun kenarı da geçerse, levha
    üçgenin dışında kalırsa ya da artanın alanı uçları örtmezse parça yok, neden döner ("kural yok").
    `kalkanlar` ({ad, v0, v1}: levhanın `v` aralığı) verilmezse ana çatının baş makasları (uç duvarların dış yüzü)."""
    F = F or cerceve(g)
    yuks = (F["aciklik"] / 200 + F["s"] / 100) * F["eg"]
    n = math.ceil(K["katsayi"] * 0.5 * (F["aciklik"] / 100 + 2 * F["s"] / 100) * yuks / K["levha_m2"] - 1e-9)
    lu, lz = K["levha_cm"]
    t = K["kalinlik_betopan"]
    z0 = g["duvar_h"]
    h = _ust(F, F["um"]) - 10 - z0                                      # üst başlığın alt yüzü (`ifc_uret`: başlık 10 cm)
    if h > lu + ESIK:
        return [], f"üçgen {h:.1f} cm yüksek, levha {lu:g} × {lz:g} cm: dikey levha da örtmez"
    dikey = h > lz + ESIK
    ucgen = Polygon([(-F["s"], z0), (F["aciklik"] + F["s"], z0), (F["aciklik"] + F["s"], _ust(F, F["aciklik"] + F["s"])),
                     (F["um"], _ust(F, F["um"])), (-F["s"], _ust(F, -F["s"]))])
    if kalkanlar is None:
        kalkanlar = [{"ad": m["ad"], **dict(zip(("v0", "v1"), (-t, 0.0) if m["konum"] < F["boy"] / 2 else (F["boy"], F["boy"] + t)))}
                     for m in sorted((m for m in g["makaslar"] if m["rol"] == "bas"), key=lambda m: m["konum"])]
    out = []
    for kk in kalkanlar:
        ad, v0, v1 = kk["ad"], kk["v0"], kk["v1"]
        if not dikey:
            for i in range(n):
                u0 = F["um"] - n * lu / 2 + i * lu
                kesik = box(u0, z0, u0 + lu, z0 + lz).intersection(ucgen)
                if kesik.is_empty or kesik.geom_type != "Polygon":
                    return [], f"{ad}: {i + 1}. levha üçgenin dışında kalıyor (tek sıra {n} levha)"
                out.append({"kural": "bas_makas_betopani_yerlesimi", "parca": "levha", "alan_m2": round(lu * lz / 1e4, 4),
                            "geo": _prizma(F, _uz(kesik), v0, v1),
                            "bilgi": {"Makas": ad, "Levha": i + 1, "LevhaAdedi": n, "Levha_cm": f"{lu:g} × {lz:g}"},
                            "aciklama": f"{ad}, {i + 1}. levha ({lu:g} × {lz:g})"})
            continue
        dizi = []
        for i in range(n):                                              # mahyadan dışa, iki yana sırayla
            u0 = F["um"] + (i // 2) * lz if i % 2 == 0 else F["um"] - (i // 2 + 1) * lz
            kesik = box(u0, z0, u0 + lz, z0 + lu).intersection(ucgen)
            if kesik.is_empty or kesik.geom_type != "Polygon":
                return [], f"{ad}: {i + 1}. levha üçgenin dışında kalıyor (dikey {n} levha)"
            dizi.append((u0, kesik))
        uclar = ucgen.difference(unary_union([box(u0, z0, u0 + lz, z0 + lu) for u0, _k in dizi]))
        uclar = [q for q in getattr(uclar, "geoms", [uclar]) if q.geom_type == "Polygon" and q.area > ESIK]
        artan = sum(lz * lu - k.area for _u, k in dizi)
        if sum(q.area for q in uclar) > artan + ESIK:
            return [], f"{ad}: uçlar {sum(q.area for q in uclar) / 1e4:.2f} m², artan betopan {artan / 1e4:.2f} m²: örtmez"
        ek: dict[int, list] = {i: [] for i in range(n)}
        for q in uclar:                                                 # uç o yandaki en dıştaki levhanın parçası
            sag = q.centroid.x > F["um"]
            yan = [i for i, (u0, _k) in enumerate(dizi) if (u0 + lz / 2 > F["um"]) == sag] or list(range(n))
            ek[max(yan, key=lambda i: abs(dizi[i][0] + lz / 2 - F["um"]))].append(q)
        o = F.get("ou") or 0.0
        for i, (u0, kesik) in enumerate(dizi):
            govde = [_prizma(F, _uz(kesik), v0, v1)] + [_prizma(F, _uz(q), v0, v1) for q in ek[i]]
            artan_uc = round(sum(q.area for q in ek[i]) / 1e4, 4)
            out.append({"kural": "bas_makas_betopani_yerlesimi", "parca": "levha", "alan_m2": round(lu * lz / 1e4, 4),
                        "geo": govde[0] if len(govde) == 1 else {"tip": "coklu", "parcalar": govde},
                        "bilgi": {"Makas": ad, "Levha": i + 1, "LevhaAdedi": n, "Levha_cm": f"{lz:g} × {lu:g}", "Dizilim": "dikey",
                                  "LevhaU0_cm": round(u0 + o, 4), "LevhaU1_cm": round(u0 + lz + o, 4), **({"ArtanUc_m2": artan_uc} if ek[i] else {})},
                        "aciklama": f"{ad}, {i + 1}. levha ({lz:g} × {lu:g}, dikey)" + (f"; uçta artan betopan {artan_uc:g} m²" if ek[i] else "")})
    return out, None


def dere(g: dict, K: dict, F: dict | None = None, dis_uc: int | None = None) -> list[dict]:
    """Beşikte her saçak kenarı boyunca bir dere hattı, boyu mahya boyu. İniş her hattın iki ucunda (köşe başına `kose_basina`); eşiği
    geçen hattın ortasında bir iniş daha. İnişin gösterim kesiti [dere boyunca, dereye dik] ya da tek sayı (kare). `dis_uc` (taşan
    verandanın çatısı, K5b): her hatta bu kadar iniş, yalnız dış uçta (dizilimin başladığı uç), orta iniş yok."""
    F = F or cerceve(g)
    dw, dh = K["kesit_dere"]
    iw, iu = (K["kesit_inis"], K["kesit_inis"]) if isinstance(K["kesit_inis"], (int, float)) else K["kesit_inis"]
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
        if dis_uc is not None:
            konumlar = ([("dış uç", F["v0"] + iw / 2 + k * 2 * iw) for k in range(dis_uc)] if F["v_bas"] == "min"
                        else [("dış uç", F["v1"] - iw / 2 - k * 2 * iw) for k in range(dis_uc)])
        elif boy > K["orta_esik_cm"] + ESIK:
            konumlar.insert(n, ("orta", (F["v0"] + F["v1"]) / 2))
        uc = (u0 + u1) / 2
        for yer, v in konumlar:
            out.append({"kural": "dere_hatti", "parca": "inis",
                        "geo": _kutu(F, uc - iu / 2, uc + iu / 2, v - iw / 2, v + iw / 2, ze - dh - 15, ze - dh),
                        "bilgi": {"Yuz": yuz, "Yer": yer}, "aciklama": f"{yuz} saçak, {yer}"})
    return out
