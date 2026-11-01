"""İE-24 · Girintili gövdenin çatı katmanları (TK-03'ün Z gövdesi): ana çatı + paralel cumba (`motor/cati_serit.py`).

Bugünkü IFC girintili gövdede çatıyı `cati_serit.tanim`'den kurar (`motor.ifc_uret.IfcUretici._cati_serit`): her parça (ana çatı, cumbalar)
bir beşik, aynı düzlemdeki ana çatı ve cumba yüzü tek yüz. Çatı katmanları liste üretecinin saydığı çatıdan kurulur (`motor/prefabrik_liste.py`
› `_serit_catilari`, kitabın çok düzlemli çatı kuralı `cok_duzlemli_cati`); sayılar listeyle aynı yoldan çıkar:

- **Aşık** çatının yüzlerinde (`cati_genel.cati_kur` › `asik`): sıralar saçak çizgisinden kitabın aralığıyla, sıranın boyu yüzün o
  yükseklikteki genişliği (aynı düzlemdeki ana çatı ve cumba yüzünde tek sıra; paftanın aşık planı 845,6 ve 753,2). Sıra dizilimin başladığı
  uçtan tam parçalara bölünür (K2'nin `parcala`'sı). Dikdörtgen gövdede K2'nin karar C'si (mahyadan) aynen; burada kitabın çok düzlemli kuralı.
- **Kaplama** (sandviç panel) kitabın çok düzlemli dizilimiyle (`girdi_genel._dizilim`): şeritler saçağın ucundan, panel başına bir parça
  (bir panelden kesilen iki parça tek parçadır). Tek kat panelin çok düzlemli dizilimi listede de yok: "kural yok".
- **Baş makas betopanı** her parçanın baş makaslarında, parçanın kendi çerçevesiyle (`cati.betopan`; sayı liste kuralı H5, baş makas başına).
- **Dere** her saçak hattında (`cati_kur` › `dere`), **iniş** hattın iki ucunda ve eşiği geçen hattın ortasında (K2'nin kuralı).
- **Çatı kenarları** (K3b): saçak omegası ve saçak sacı saçak hattı boyunca (omega baş makas betopanında kesilir; D-39), mahya her parçanın
  görünen mahyası boyunca, Z, alın sacı ve C kapama her görünen alın kenarında (başka bir çatının altında kalan kenar sayılmaz; ana çatının
  cumba üstündeki kısa kenarı sayılır). Kesitler K3b'ninkiler (`kenar.py`).

Parçaların çerçevesi (`cerceve`): K2'nin `cati.cerceve` anahtarları; `u` makas ekseni, `ou` yerel `u`'nun dünyadaki başı (parçanın dış yüzü),
`v` dünya koordinatı (`v0`..`v1` çatının saçaklı boyu, `w0`..`w1` parçanın duvar boyu). LLM yok; sayı burada yazılmaz.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon, box

from . import cati, kenar
from .tavan import parcala

ESIK = 1e-6


def _ref(dz: dict) -> tuple[float, float]:
    s = dz["sacak"]
    return (s["x"], 0.0) if "x" in s else (0.0, s["y"])


def _nokta(dz: dict, u: float, t: float) -> tuple[float, float]:
    """Yüzün açılım koordinatından (`u` sağa, `t` saçak çizgisinden eğik boy; `cati_genel.duzlem_kur` › `yuz`) plan noktası."""
    (yx, yy), (sx, sy), (rx, ry) = dz["yukari"], dz["sag"], _ref(dz)
    h = t / dz["kok"] + rx * yx + ry * yy
    return (u * sx + h * yx, u * sy + h * yy)


def _mahya_x(q: dict) -> bool:
    return abs(q["mahya"][0][1] - q["mahya"][1][1]) < ESIK


def _yuz_adi(dz: dict) -> str:
    """K2'nin yüz adı: makas ekseninde mahyadan küçük taraf "sol", büyük taraf "sag" (yukarı yön makas ekseninde artıyorsa sol yüz)."""
    yx, yy = dz["yukari"]
    return "sol" if (yy if abs(yy) > abs(yx) else yx) > 0 else "sag"


def cerceveler(g: dict) -> dict[str, dict]:
    """Parça başına K2 çerçevesi. Ana çatının iki ucu saçaklı; cumbanın dış ucu saçaklı, iç ucu ana çatının duvar yüzünde biter."""
    T = g["cati_serit"]
    s, eg = float(T["sacak"]), float(g["cati"]["egim"])
    ana = next(q for q in T["parcalar"] if q["rol"] == "ana")
    out = {}
    for q in T["parcalar"]:
        mx = not _mahya_x(q)                                          # makaslar x boyunca (mahya y boyunca)
        (a0, a1), (b0, b1) = q["a"], q["b"]
        if q["rol"] == "ana":
            v0, v1 = a0 - s, a1 + s
        elif a1 < ana["a"][0] + 0.5:                                  # cumba ana çatının solunda (önünde): iç ucu a1 (bir yanda iki cumbada dıştaki de)
            v0, v1 = a0 - s, a1
        else:
            v0, v1 = a0, a1 + s
        A = b1 - b0
        out[q["ad"]] = {"mx": mx, "ou": b0, "aciklik": A, "boy": a1 - a0, "s": s, "eg": eg, "zs": g["duvar_h"] + T["topuk"], "um": A / 2,
                        "kos": 1 / math.sqrt(1 + eg * eg), "egik": (A / 2 + s) * math.sqrt(1 + eg * eg), "v0": v0, "v1": v1, "w0": a0, "w1": a1,
                        "v_bas": g["baslangic"]["y" if mx else "x"], "ad": q["ad"], "rol": q["rol"], "parca": q}
    return out


def _makas_adi(g: dict, konum: float) -> str:
    return min(g["makaslar"], key=lambda m: abs(m["konum"] - konum))["ad"]


# ----------------------------------------------------------------------------- K2: aşık, kaplama, betopan, dere
def asik(g: dict, ck: dict, K: dict) -> list[dict]:
    """Yüz başına kitabın sıraları (`ck["asik"]`); sıra yüzün o yükseklikteki genişliğinde, parçaları dizilimin başladığı uçtan."""
    a, w = K["kesit_asik"]
    out = []
    for dz in ck["duzlemler"]:
        ac = dz.get("acilim_karkas") or dz["acilim"]
        u0, t0, u1, t1 = ac.bounds
        ymax = max(dz["yatay"](p) for p in dz["plan"])
        ax = 0 if abs(dz["sag"][0]) > 0.5 else 1                         # sıranın koştuğu dünya ekseni
        sondan = g["baslangic"]["x" if ax == 0 else "y"] == "max"
        kose = list(ac.exterior.coords)[:-1]
        for i, sr in enumerate(sorted(ck["asik"][dz["ad"]], key=lambda r: r["t"])):
            t = min(max(sr["t"], t0 + 0.01), t1 - 0.01)
            if sr["tur"] == "ust_sira":                                  # üst yatay kenarın sırası: o kenarın boyunda (`asik_siralari`)
                kes = next(LineString([p, q]) for p, q in zip(kose, kose[1:] + kose[:1])
                           if abs(p[1] - sr["t"]) < 0.05 and abs(q[1] - sr["t"]) < 0.05 and abs(abs(q[0] - p[0]) - sr["boy"]) < 0.05)
            else:
                kes = ac.intersection(LineString([(u0 - 1, t), (u1 + 1, t)]))
            tg = min(max(sr["t"] / dz["kok"], w / 2), ymax - w / 2) * dz["kok"]       # gösterim: kesit yüzün içinde kalsın
            for seg in getattr(kes, "geoms", [kes]):
                if seg.is_empty or seg.length < 1.0:
                    continue
                (ua, _), (ub, _) = seg.coords[0], seg.coords[-1]
                pa, pb = _nokta(dz, ua, tg), _nokta(dz, ub, tg)
                r0, r1 = sorted((pa[ax], pb[ax]))
                c = pa[1 - ax]
                z = dz["kot"](pa) + 10                                    # makas üst başlığının üst yüzü (`ifc_uret`: başlık 10 cm)
                for v0, v1 in parcala(r0, r1, K["tam"], K["en_kisa"], sondan)[0]:
                    kutu = [v0, c - w / 2, z, v1, c + w / 2, z + a] if ax == 0 else [c - w / 2, v0, z, c + w / 2, v1, z + a]
                    out.append({"kural": "asik_sirasi", "parca": "asik", "boy_cm": round(v1 - v0, 4), "geo": {"tip": "kutu", "kutu": kutu},
                                "bilgi": {"Yuz": _yuz_adi(dz), "Sira": i + 1, "SacaktanEgik_cm": round(sr["t"], 2), "Cati": dz["ad"]},
                                "aciklama": f"{dz['ad']} yüzü, {i + 1}. sıra (saçaktan {sr['t']:.1f} cm)"})
    return out


def _seritler(dz: dict, kose: list, tasma: float, z_ust: float, t_kap: float) -> list[dict]:
    """Bir kaplama parçasının (açılım çokgeni) gövdesi: köşelerinden geçen dik şeritlere bölünür, her şerit eğim boyunca bir prizma
    (saçaktaki ucu taşma kadar uzar). Çapraz kenarlı parça şeridinin en uzun boyuyla çizilir (gösterim)."""
    pg = Polygon(kose)
    ax = 0 if abs(dz["sag"][0]) > 0.5 else 1
    us = sorted({round(u, 4) for u, _t in kose})
    out = []
    for ua, ub in zip(us, us[1:]):
        dil = pg.intersection(box(ua, -1e6, ub, 1e6))
        for p in getattr(dil, "geoms", [dil]):
            if p.is_empty or p.geom_type != "Polygon" or p.area < 0.5:
                continue
            _a, ta, _b, tb = p.bounds
            ta -= tasma if abs(ta) < 0.05 else 0.0
            k = []
            for t in (ta, tb):
                q = _nokta(dz, ua, t)
                k.append((q[1 - ax], dz["kot"](q) + z_ust))
            kes = [list(k[0]), list(k[1]), [k[1][0], k[1][1] + t_kap], [k[0][0], k[0][1] + t_kap]]
            x0, x1 = sorted((_nokta(dz, ua, ta)[ax], _nokta(dz, ub, ta)[ax]))
            out.append({"tip": "prizma", "duzlem": "yz" if ax == 0 else "xz", "noktalar": kes, "a0": x0, "a1": x1})
    return out


def kaplama(g: dict, ck: dict, kitap: dict, K: dict, kaplama_adi: str) -> list[dict]:
    """Kitabın çok düzlemli dizilimi (liste üreteciyle aynı): panel başına bir parça; panelden kesilen parçalar tek gövdede."""
    from motor.genel.girdi_genel import _dizilim
    d = _dizilim(ck, kitap, kaplama_adi)
    adli = {dz["ad"]: dz for dz in ck["duzlemler"]}
    z_ust = 10 + K["kesit_asik"][0]                                       # aşığın üstü
    out = []
    for pn in d["paneller"]:
        parcalar = [p for dd in pn["dikdortgenler"] for p in dd["parcalar"]]
        govde = [s for p in parcalar for s in _seritler(adli[p.yuz], p.kose, p.tasma, z_ust, K["kalinlik_kaplama"])]
        ilk = adli[parcalar[0].yuz]
        out.append({"kural": "cati_kaplamasi", "parca": "panel", "alan_m2": round(d["kapatma_cm"] * pn["boy"] / 1e4, 4),
                    "geo": govde[0] if len(govde) == 1 else {"tip": "coklu", "parcalar": govde},
                    "bilgi": {"Yuz": _yuz_adi(ilk), "Serit": pn["no"], "PanelBoyu_cm": pn["boy"], "Genislik_cm": d["kapatma_cm"], "Cati": ilk["ad"],
                              "Parca": len(parcalar)},
                    "aciklama": f"{pn['no']}. panel ({d['kapatma_cm']:g} × {pn['boy']:g}; "
                                + ", ".join(f"{p.yuz} {p.konum or 'parça'}" for p in parcalar) + ")"})
    return out


def betopan(g: dict, K: dict, kalinlik: float) -> tuple[list[dict], list[str]]:
    """Her parçanın baş makaslarında, parçanın çerçevesiyle (`cati.betopan`): levha uç duvarın dış yüzünde."""
    out, nedenler = [], []
    for F in cerceveler(g).values():
        q = F["parca"]
        kalkanlar = []
        for m in (m for m in q["makaslar"] if m["rol"] == "bas"):
            alt = abs(m["konum"] - F["w0"]) < abs(m["konum"] - F["w1"])
            kalkanlar.append({"ad": _makas_adi(g, m["konum"]), "v0": F["w0"] - kalinlik if alt else F["w1"],
                              "v1": F["w0"] if alt else F["w1"] + kalinlik})
        levhalar, neden = cati.betopan(g, K, F, kalkanlar=kalkanlar)
        if neden:
            nedenler.append(f"{q['ad']}: {neden}")
        for p in levhalar:
            p["bilgi"]["Cati"] = q["ad"]
        out += levhalar
    return out, nedenler


def dere(g: dict, ck: dict, K: dict) -> list[dict]:
    """Her saçak hattında dere (saçak çizgisinin dışında, saçak kotunda); iniş hattın iki ucunda (köşe başına) ve eşiği geçen hattın ortasında."""
    dw, dh = K["kesit_dere"]
    iw, iu = (K["kesit_inis"], K["kesit_inis"]) if isinstance(K["kesit_inis"], (int, float)) else K["kesit_inis"]
    adli = {dz["ad"]: dz for dz in ck["duzlemler"]}
    out = []
    for h in ck["dere"]["hatlar"]:
        dz = adli[h["duzlem"]]
        (yx, yy) = dz["yukari"]
        ax = 0 if abs(dz["sag"][0]) > 0.5 else 1
        r0, r1 = sorted((h["p"][ax], h["q"][ax]))
        c = h["p"][1 - ax]
        dis = -(yy if ax == 0 else yx)                                   # dışarı yön (yukarı yönün tersi)
        c0, c1 = sorted((c, c + dis * dw))
        ze = dz["sacak_kotu"] + 10
        kutu = (lambda a0, a1, b0, b1, z0, z1: [a0, b0, z0, a1, b1, z1]) if ax == 0 else (lambda a0, a1, b0, b1, z0, z1: [b0, a0, z0, b1, a1, z1])
        boy = r1 - r0
        yuz = _yuz_adi(dz)
        out.append({"kural": "dere_hatti", "parca": "dere", "boy_cm": round(boy, 4), "geo": {"tip": "kutu", "kutu": kutu(r0, r1, c0, c1, ze - dh, ze)},
                    "bilgi": {"Yuz": yuz, "Cati": dz["ad"]}, "aciklama": f"{dz['ad']} saçağı, {boy:g} cm"})
        n = int(K["kose_basina"])
        konumlar = [("uç", r0 + iw / 2 + k * 2 * iw) for k in range(n)] + [("uç", r1 - iw / 2 - k * 2 * iw) for k in range(n)]
        if boy > K["orta_esik_cm"] + ESIK:
            konumlar.insert(n, ("orta", (r0 + r1) / 2))
        uc = (c0 + c1) / 2
        for yer, v in konumlar:
            out.append({"kural": "dere_hatti", "parca": "inis", "geo": {"tip": "kutu", "kutu": kutu(v - iw / 2, v + iw / 2, uc - iu / 2, uc + iu / 2,
                                                                                                       ze - dh - 15, ze - dh)},
                        "bilgi": {"Yuz": yuz, "Yer": yer, "Cati": dz["ad"]}, "aciklama": f"{dz['ad']} saçağı, {yer}"})
    return out


# ----------------------------------------------------------------------------- K3b: çatı kenarları
def _ortulu(ck: dict, e: dict) -> bool:
    """Kenarın ortası başka bir düzlemin planında ve o düzlem orada kenardan yüksek: kenar o çatının altında (liste üreteciyle aynı)."""
    m = Point((e["p"][0] + e["q"][0]) / 2, (e["p"][1] + e["q"][1]) / 2)
    z = sum(e["kot"]) / 2
    return any(d["cokgen"].buffer(-0.5).contains(m) and d["kot"]((m.x, m.y)) > z + 0.5 for d in ck["duzlemler"] if d["ad"] not in e["duzlemler"])


def _sacak_cercevesi(Fs: dict, e: dict) -> tuple[dict, str]:
    """Saçak kenarının parçası (saçağı o kenarda ve boyu kenarla en çok örtüşen) ve yüzü."""
    ax = 0 if abs(e["p"][1] - e["q"][1]) < ESIK else 1
    c = e["p"][1 - ax]
    r0, r1 = sorted((e["p"][ax], e["q"][ax]))
    aday = []
    for F in Fs.values():
        if F["mx"] == (ax == 0):                                         # saçak mahyaya paralel: mahya x boyuncaysa kenar x boyunca
            continue
        for yuz, u in (("sol", F["ou"] - F["s"]), ("sag", F["ou"] + F["aciklik"] + F["s"])):
            if abs(c - u) < 0.5:
                aday.append((min(r1, F["v1"]) - max(r0, F["v0"]), F, yuz))
    if not aday:
        raise ValueError(f"saçak kenarı {e['p']}–{e['q']} hiçbir çatı parçasının saçağında değil")
    _o, F, yuz = max(aday, key=lambda x: x[0])
    return F, yuz


def _alin_cercevesi(Fs: dict, e: dict) -> tuple[dict, bool]:
    """Alın kenarının parçası: kenarın mahya eksenindeki yeri parçanın saçaklı ucu. Dönen: çerçeve, kalkan önde mi (`v` küçük uçta)."""
    for F in Fs.values():
        v = e["p"][1] if F["mx"] else e["p"][0]
        if abs(v - F["v0"]) < 0.5 and abs(F["v0"] - (F["w0"] - F["s"])) < 0.5:
            return F, True
        if abs(v - F["v1"]) < 0.5 and abs(F["v1"] - (F["w1"] + F["s"])) < 0.5:
            return F, False
    raise ValueError(f"alın kenarı {e['p']}–{e['q']} hiçbir çatı parçasının ucunda değil")


def kenarlar(g: dict, ck: dict, G_: dict, kesit: dict, kurulan: set[str], engeller: list[dict] | None = None) -> list[dict]:
    """K3b'nin çatı kenarları girintili gövdede (kurallar `kurulan`): saçak omegası, saçak sacı, mahya, Z, alın sacı, C kapama. Saçak omegası
    saçak kenarının ucundan ucuna, dikdörtgen gövdedeki gibi (D-39; liste de saçak kenarlarının boyunu sayar); kesitine baş makas betopanı
    (`engeller`, `betopan`) iniyorsa orada kesilir. Hat, kenarın düzleminin parçasına yazılır (`Cati`; aynı düzlemdeki ana çatı ve cumba yüzü
    tek hat, liste üreteci gibi)."""
    Fs = cerceveler(g)
    out = []
    gorunen = [e for e in ck["kenarlar"] if e["tur"] in ("sacak", "alin") and not _ortulu(ck, e)]
    for e in (e for e in ck["kenarlar"] if e["tur"] == "sacak"):          # dere hattı gibi: saçak kenarının tamamı (altta kalan uç dahil)
        F, yuz = _sacak_cercevesi(Fs, e)
        ax = 0 if not F["mx"] else 1
        r0, r1 = sorted((e["p"][ax], e["q"][ax]))
        if "sacak_omegasi_yerlesimi" in kurulan:
            cati_ = e["duzlemler"][0].rsplit(" ", 1)[0]
            for p in kenar.sacak_omegasi(g, G_, dict(F, v0=r0, v1=r1), engeller):
                if p["bilgi"]["Yuz"] == yuz:
                    p["bilgi"] = {"Cati": cati_, **p["bilgi"]}
                    out.append(p)
        if "sacak_saci_yerlesimi" in kurulan:
            out += [p for p in kenar.sacak_saci(g, G_, dict(F, v0=r0, v1=r1)) if p["bilgi"]["Yuz"] == yuz]
    if "mahya_yerlesimi" in kurulan:
        for F in Fs.values():
            (mx0, my0), (mx1, my1) = F["parca"]["mahya"]
            v0, v1 = sorted((my0, my1) if F["mx"] else (mx0, mx1))
            out += kenar.mahya(g, G_, kesit, dict(F, v0=v0, v1=v1))
    kk = kurulan & {"bas_makas_z_yerlesimi", "alin_saci_yerlesimi", "c_kapama_yerlesimi"}
    if kk:
        for e in (e for e in gorunen if e["tur"] == "alin"):
            F, on = _alin_cercevesi(Fs, e)
            u0, u1 = sorted(((p[0] if F["mx"] else p[1]) - F["ou"]) for p in (e["p"], e["q"]))
            yuz = "sol" if (u0 + u1) / 2 < F["um"] else "sag"
            q = F["parca"]
            bas = min((m for m in q["makaslar"] if m["rol"] == "bas"), key=lambda m: abs(m["konum"] - (F["w0"] if on else F["w1"])))
            ka = {"ad": _makas_adi(g, bas["konum"]), "on": on, "v_dis": F["w0"] - kesit["betopan"] if on else F["w1"] + kesit["betopan"],
                  "v_uc": F["v0"] if on else F["v1"]}
            out += kenar.kalkan_kenarlari(g, G_, kesit, kk, F, [ka], yuzler=[(yuz, u0, u1)])
    return out
