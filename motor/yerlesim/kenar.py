"""İE-15 · K3b · Alt çerçeve ve çatı kenarları: montaj rehberinin kartsız yedi parçası (alt çerçeve, saçak omegası, saçak sacı, alın sacı,
baş makas Z'si, C kapama, mahya).

Yer montaj rehberindendir (Lokman'ın 24 Ekim çizimleri; teyit bekleyen maddeler varsayım: Lokman, 25 Ekim 09:10), sayı liste üretecinin
sayma yolundandır: boy modelden ölçülür, sayı kesim planında listenin yöntemiyle çıkar (kuralın `yontem`'i: hatların toplamı, kenar başına
ya da metre; `kesim.py`). Kurallar `kurallar/yerlesim/prefabrik.json`'da (`KENAR`); sayılar `okunan` ile liste kurallarından ve kitaptan
gelir, burada sayı yazılmaz.

Alt çerçeve liste üretecinin okuduğu plandan (`motor.geometry.kur`): dış hat kapalı kısmın dış sınırının her düz kenarı (köşe dahil;
liste üretecinin `dis_cevre_m`'si), iç hat bir iç duvarın bitişik panoları (liste üretecinin iç duvar boyu). Parça hattın kesilen
boşluklar arasındaki kısmıdır; hattın tamamı `HatBoyu_cm`'de, sayı hatların toplamından (kesilen parça artık).

Çatı kenarları K2'nin çatısıyla aynı çerçevede (`cati.cerceve`) ve yalnız beşik çatıda; başka çatı tipinde "kural yok". Saçak omegası iki
saçak duvarının üstünde binanın boyunca, saçak sacı saçak kenarında saçak ucundan ucuna, mahya kaplamanın üstünde saçak ucundan ucuna;
her baş makasın iki eğik kenarında Z, alın sacı ve C kapama (boyu eğik boy). Parça hat ya da kenar başına birdir; stok boyları kesim
planındadır. Kesitler yalnız gösterimdir (`kenar_gosterim`); sayı, boy ve metre onlardan çıkmaz.

`katman(ie, g, D, kesit, K)` döner: {parcalar, kural_yok, uyarilar, hatlar}. Parçalar K2'ninkilerle aynı biçimdedir ({kural, parca, boy_cm, geo,
bilgi, aciklama}); kartı kart modelinde bulunur (`motor/kart_model.py`).
"""
from __future__ import annotations

import copy

from shapely.geometry import Point, Polygon

from . import cati, girdi

ALT_CERCEVE = "alt_cerceve_yerlesimi"
CATI_KENARLARI = (("sacak_omegasi_yerlesimi", "saçak omegası", "IfcMember"), ("sacak_saci_yerlesimi", "saçak sacı", "IfcCovering"),
                  ("alin_saci_yerlesimi", "alın sacı", "IfcCovering"), ("bas_makas_z_yerlesimi", "baş makas Z'si", "IfcMember"),
                  ("c_kapama_yerlesimi", "C kapama", "IfcCovering"), ("mahya_yerlesimi", "mahya", "IfcCovering"))
KENAR = (ALT_CERCEVE,) + tuple(ad for ad, _a, _s in CATI_KENARLARI)
GOSTERIM = "kenar_gosterim"
KATMAN = "alt çerçeve ve çatı kenarları"
ESIK = 1e-6
YAPISMA_CM = 0.5            # boşluk ve pano uçları Motor'da tam sayıya oturur; bu kadar yakın sayılır (`girdi.YAPISMA_CM` gibi)


def _r(v: float) -> float:
    return round(float(v), 4)


def _dikdortgen(a0: float, a1: float, b0: float, b1: float) -> list[list[float]]:
    return [[a0, b0], [a1, b0], [a1, b1], [a0, b1]]


def _u(c0: float, c1: float, z0: float, h: float, t: float, ters: bool = False) -> list[list[float]]:
    """U kesiti (kesit düzleminde c0..c1 genişlikte, z0'dan h yükseklikte, sac t); `ters` ise ağzı aşağı (ters U)."""
    if ters:
        return [[c0, z0], [c0 + t, z0], [c0 + t, z0 + h - t], [c1 - t, z0 + h - t], [c1 - t, z0], [c1, z0], [c1, z0 + h], [c0, z0 + h]]
    return [[c0, z0], [c1, z0], [c1, z0 + h], [c1 - t, z0 + h], [c1 - t, z0 + t], [c0 + t, z0 + t], [c0 + t, z0 + h], [c0, z0 + h]]


def _kesikler(a0: float, a1: float, bosluklar: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Hattın (a0, a1) boşluklar dışında kalan kısımları."""
    out, u = [], a0
    for b0, b1 in sorted(bosluklar):
        if b1 <= u + ESIK or b0 >= a1 - ESIK:
            continue
        if b0 > u + ESIK:
            out.append((u, b0))
        u = max(u, b1)
    if a1 > u + ESIK:
        out.append((u, a1))
    return out


# ----------------------------------------------------------------------------- alt çerçeve
def alt_cerceve(ie: dict, D: dict, G_: dict) -> tuple[list[dict], list[dict]]:
    """Alt çerçevenin parçaları ve hatları. `D`: kuralın değerleri; `G_`: `kenar_gosterim` kesitleri."""
    from motor import geometry as G

    P = G.kur(copy.deepcopy(ie))
    turler = set(D["kesilen_bosluklar"])
    pay, kanat, t = G_["alt_cerceve"]["pay"], G_["alt_cerceve"]["kanat"], G_["sac"]
    bosluklar = [(d.yon, p.gap()) for d in P.duvarlar for p in d.panolar if p.acilim and p.acilim.tur in turler]
    T = max(2 * d.h for d in P.duvarlar if d.tur == "dis")
    hatlar = []
    fp = P.footprint()
    for g_ in getattr(fp, "geoms", [fp]):
        halka = Polygon(g_.exterior).simplify(0.0)
        cs = list(halka.exterior.coords)
        for (x0, y0), (x1, y1) in zip(cs, cs[1:]):
            if abs(y1 - y0) < ESIK:
                yon, e, a0, a1 = "x", y0, min(x0, x1), max(x0, x1)
            elif abs(x1 - x0) < ESIK:
                yon, e, a0, a1 = "y", x0, min(y0, y1), max(y0, y1)
            else:
                raise ValueError(f"alt çerçeve: dış sınırın kenarı eksene paralel değil ({x0:g}, {y0:g})–({x1:g}, {y1:g})")
            orta = (a0 + a1) / 2
            n = 1 if halka.contains(Point((orta, e + 1) if yon == "x" else (e + 1, orta))) else -1     # içeri
            kes = []
            for byon, (gx0, gy0, gx1, gy1) in bosluklar:
                b0, b1, c0, c1 = (gx0, gx1, gy0, gy1) if yon == "x" else (gy0, gy1, gx0, gx1)
                if byon == yon and min(abs(c0 - e), abs(c1 - e)) <= YAPISMA_CM:
                    kes.append((b0, b1))
            c_a, c_b = e - n * (pay + t), e + n * (T + pay + t)
            hatlar.append({"duvar": "dış", "cerceve": "100'lük", "yon": yon, "c0": min(c_a, c_b), "c1": max(c_a, c_b), "eksen": e,
                           "a0": a0, "a1": a1, "boy": a1 - a0, "kesikler": kes, "kalinlik_cm": T})
    for d in P.duvarlar:
        if d.tur != "ic" or not d.panolar:
            continue
        ps = sorted(d.panolar, key=lambda p: p.a0)
        kosular, k = [], [ps[0]]
        for p in ps[1:]:
            if p.a0 - k[-1].a1 <= YAPISMA_CM:
                k.append(p)
            else:
                kosular.append(k); k = [p]
        kosular.append(k)
        cerceve = "100'lük" if round(2 * d.h * 10) >= D["ic_100_esigi_mm"] else "60'lık"
        for k in kosular:
            kes = [((g[0], g[2]) if d.yon == "x" else (g[1], g[3])) for g in (p.gap() for p in k if p.acilim and p.acilim.tur in turler)]
            hatlar.append({"duvar": "iç", "cerceve": cerceve, "yon": d.yon, "c0": d.c - d.h - pay - t, "c1": d.c + d.h + pay + t, "eksen": d.c,
                           "a0": k[0].a0, "a1": k[-1].a1, "boy": sum(p.boy for p in k), "kesikler": kes, "kalinlik_cm": 2 * d.h})
    hatlar.sort(key=lambda h: (h["duvar"] != "dış", h["yon"], h["eksen"], h["a0"]))
    parcalar = []
    for i, h in enumerate(hatlar, 1):
        h["no"] = i
        kesit = _u(h["c0"], h["c1"], -t, kanat, t)
        h["parcalar"] = _kesikler(h["a0"], h["a1"], h["kesikler"])
        for j, (s0, s1) in enumerate(h["parcalar"], 1):
            parcalar.append({"kural": ALT_CERCEVE, "parca": "alt_cerceve", "boy_cm": _r(s1 - s0),
                             "geo": {"tip": "prizma", "duzlem": "yz" if h["yon"] == "x" else "xz", "noktalar": kesit, "a0": s0, "a1": s1},
                             "bilgi": {"Cerceve": h["cerceve"], "Duvar": h["duvar"], "Hat": i, "HatBoyu_cm": _r(h["boy"]), "Parca": j},
                             "aciklama": f"{h['duvar']} hat {i} ({'y' if h['yon'] == 'x' else 'x'} = {h['eksen']:g}, {h['a0']:g}–{h['a1']:g}), "
                                         f"{s0:g}–{s1:g}"})
    return parcalar, [{"no": h["no"], "duvar": h["duvar"], "cerceve": h["cerceve"], "yon": h["yon"], "eksen_cm": _r(h["eksen"]),
                       "a0_cm": _r(h["a0"]), "a1_cm": _r(h["a1"]), "boy_cm": _r(h["boy"]),
                       "kesikler_cm": [[_r(a), _r(b)] for a, b in sorted(h["kesikler"])], "parcalar_cm": [_r(b - a) for a, b in h["parcalar"]]}
                      for h in hatlar]


# ----------------------------------------------------------------------------- çatı kenarları
def _coklu(F: dict, kesitler: list[tuple[list, float, float]]) -> dict:
    return {"tip": "coklu", "parcalar": [cati._prizma(F, uz, v0, v1) for uz, v0, v1 in kesitler]}


def _bant(F: dict, u0: float, u1: float, dz0: float, dz1: float) -> list[list[float]]:
    """Makas üst başlığının üst yüzünü izleyen şerit (u–z kesiti): u0'dan u1'e, üst yüzün dz0 ile dz1 üstünde."""
    return [[u0, cati._ust(F, u0) + dz0], [u1, cati._ust(F, u1) + dz0], [u1, cati._ust(F, u1) + dz1], [u0, cati._ust(F, u0) + dz1]]


def sacak_omegasi(g: dict, G_: dict) -> list[dict]:
    F = cati.cerceve(g)
    w, h = G_["sacak_omegasi"]
    out = []
    for yuz, u0 in (("sol", 0.0), ("sag", F["aciklik"] - w)):
        out.append({"kural": "sacak_omegasi_yerlesimi", "parca": "sacak_omegasi", "boy_cm": _r(F["boy"]),
                    "geo": cati._prizma(F, _u(u0, u0 + w, g["duvar_h"], h, G_["sac"], ters=True), 0.0, F["boy"]),
                    "bilgi": {"Yuz": yuz}, "aciklama": f"{yuz} saçak duvarının üstü, {F['boy']:g} cm"})
    return out


def sacak_saci(g: dict, G_: dict) -> list[dict]:
    """Tırnak saçak omegasının üstünde, saçak altı omeganın üstü kotunda saçak ucuna, alın saçak ucunda yukarı, kıvrım alnın üstünden dışarı
    (dereye)."""
    F = cati.cerceve(g)
    S, t = G_["sacak_saci"], G_["sac"]
    zo = g["duvar_h"] + G_["sacak_omegasi"][1]
    out = []
    for yuz, ue, i in (("sol", -F["s"], 1), ("sag", F["aciklik"] + F["s"], -1)):
        ic = 0.0 if yuz == "sol" else F["aciklik"]
        kesitler = [(_dikdortgen(*sorted((ue, ic + i * S["tirnak"])), zo, zo + t), F["v0"], F["v1"]),
                    (_dikdortgen(*sorted((ue, ue + i * t)), zo, zo + S["alin"]), F["v0"], F["v1"]),
                    (_dikdortgen(*sorted((ue, ue - i * S["kivrim"])), zo + S["alin"] - t, zo + S["alin"]), F["v0"], F["v1"])]
        out.append({"kural": "sacak_saci_yerlesimi", "parca": "sacak_saci", "boy_cm": _r(F["v1"] - F["v0"]), "geo": _coklu(F, kesitler),
                    "bilgi": {"Yuz": yuz}, "aciklama": f"{yuz} saçak kenarı, {F['v1'] - F['v0']:g} cm (saçak ucundan ucuna)"})
    return out


def mahya(g: dict, G_: dict, kesit: dict) -> list[dict]:
    F = cati.cerceve(g)
    t, w = G_["sac"], G_["mahya"]["kanat"] * F["kos"]
    dz = kesit["asik"][0] + kesit["kaplama"]
    L, M, R = ([u, cati._ust(F, u) + dz] for u in (F["um"] - w, F["um"], F["um"] + w))
    kesit_ = [L, M, R, [R[0], R[1] + t], [M[0], M[1] + t], [L[0], L[1] + t]]
    return [{"kural": "mahya_yerlesimi", "parca": "mahya", "boy_cm": _r(F["v1"] - F["v0"]), "geo": cati._prizma(F, kesit_, F["v0"], F["v1"]),
             "bilgi": {}, "aciklama": f"mahya, {F['v1'] - F['v0']:g} cm (saçak ucundan ucuna)"}]


def kalkan_kenarlari(g: dict, G_: dict, kesit: dict, kurallar: set[str]) -> list[dict]:
    """Her baş makasın iki eğik kenarında (saçak ucundan mahyaya) Z, alın sacı ve C kapama. Kalkanın dışı uç duvarın dış yüzündeki
    betopanın dışıdır; kalkan saçağı oradan saçak ucuna (aşık uçlarına). Z makasın üstünden betopanın dışına iner; alın sacının saçak altı
    makas üstünün `makas_ustunden` altında, tırnağı Z'de; C kapama aşık uçlarında aşığın üstünden alın sacının saçak altına; alın sacının
    alnı en önde, kıvrımı kaplamanın kenarını kavrar."""
    F = cati.cerceve(g)
    t = G_["sac"]
    Z, A, C = G_["bas_makas_z"], G_["alin_saci"], G_["c_kapama"]
    a = kesit["asik"][0]
    out = []
    for m in sorted((m for m in g["makaslar"] if m["rol"] == "bas"), key=lambda m: m["konum"]):
        on = m["konum"] < F["boy"] / 2
        s = -1 if on else 1                                                   # kalkanın dışarı yönü (v)
        v_dis = -kesit["betopan"] if on else F["boy"] + kesit["betopan"]       # betopanın dış yüzü
        v_uc = F["v0"] if on else F["v1"]                                     # kalkan saçağının ucu (aşık uçları)

        def v(a_, b_):                                                        # dışarı yönde a_..b_ (v_dis'ten ölçü değil, mutlak)
            return min(a_, b_), max(a_, b_)
        for yuz, u0, u1 in (("sol", -F["s"], F["um"]), ("sag", F["um"], F["aciklik"] + F["s"])):
            bilgi = {"Makas": m["ad"], "Yuz": yuz}
            ortak = {"boy_cm": _r(F["egik"]), "bilgi": bilgi}
            if "bas_makas_z_yerlesimi" in kurallar:
                kes = [(_bant(F, u0, u1, 0.0, t), *v(v_dis, v_dis - s * 5)),
                       (_bant(F, u0, u1, -Z["centik"], t), *v(v_dis, v_dis + s * t)),
                       (_bant(F, u0, u1, -Z["centik"], -Z["centik"] + t), *v(v_dis, v_dis + s * Z["dis_kanat"]))]
                out.append({"kural": "bas_makas_z_yerlesimi", "parca": "bas_makas_z", "geo": _coklu(F, kes), **ortak,
                            "aciklama": f"{m['ad']}, {yuz} eğik kenar, {F['egik']:.1f} cm"})
            if "c_kapama_yerlesimi" in kurallar:
                z0 = a - C["govde"]
                kes = [(_bant(F, u0, u1, z0, a), *v(v_uc, v_uc + s * t)),
                       (_bant(F, u0, u1, a - t, a), *v(v_uc + s * t, v_uc - s * C["kanat"])),
                       (_bant(F, u0, u1, z0, z0 + t), *v(v_uc + s * t, v_uc - s * C["kanat"]))]
                out.append({"kural": "c_kapama_yerlesimi", "parca": "c_kapama", "geo": _coklu(F, kes), **ortak,
                            "aciklama": f"{m['ad']}, {yuz} eğik kenar, aşık uçlarında, {F['egik']:.1f} cm"})
            if "alin_saci_yerlesimi" in kurallar:
                z0 = -A["makas_ustunden"]
                on_yuz = v_uc + s * t                                         # C kapamanın önü
                kes = [(_bant(F, u0, u1, z0 - t, z0), *v(v_dis + s * Z["dis_kanat"], on_yuz)),
                       (_bant(F, u0, u1, z0, z0 + A["alin"]), *v(on_yuz, on_yuz + s * t)),
                       (_bant(F, u0, u1, z0 + A["alin"] - t, z0 + A["alin"]), *v(on_yuz + s * t, on_yuz + s * t - s * A["kivrim"]))]
                out.append({"kural": "alin_saci_yerlesimi", "parca": "alin_saci", "geo": _coklu(F, kes), **ortak,
                            "aciklama": f"{m['ad']}, {yuz} eğik kenar, {F['egik']:.1f} cm"})
    return out


def katman(ie: dict, g: dict, D: dict, kesit: dict, K: dict) -> dict:
    """K3b'nin parçaları. `g`: yerleşimin girdisi (`girdi.kur`; makaslar kart modelinden); `D`: bütün kuralların değerleri
    (`motor.yerlesim.degerler`); `kesit`: K2'nin gösterim kesitleri (aşığın yüksekliği, kaplama ve betopan kalınlığı); `K`: yerleşim
    kuralları (`cati_tipleri` kuralın kendisinden okunur, K2'deki gibi: yazılı değilse her çatı)."""
    G_ = D[GOSTERIM]["kesit_cm"]
    parcalar, kural_yok, uyarilar = [], [], []
    ac, hatlar = alt_cerceve(ie, D[ALT_CERCEVE], G_)
    parcalar += ac
    kurulan = set()
    for ad, adi, sinif in CATI_KENARLARI:
        izin = K[ad].get("cati_tipleri")
        if izin and g["cati_tipi"] not in izin:
            kural_yok.append({"parca": adi, "sinif": sinif, "neden": f"İş Emri'nin çatısı \"{g['cati_tipi']}\"; {ad} yalnız "
                                                                      f"{', '.join(izin)} çatıda (bugünkü IFC çatıyı hep beşik çizer)"})
            continue
        if ad == "mahya_yerlesimi":
            yazili = girdi.kucuk(next((v for k, v in g["ozellikler"].items() if girdi.kucuk(k) == "çatı kaplaması"), ""))
            if D[ad]["trapez_yazisi"] in yazili:
                kural_yok.append({"parca": adi, "sinif": sinif, "neden": f"İş Emri'nin çatı kaplaması \"{yazili}\": mahya trapez sac mahyasıdır "
                                                                          "(ayrı ürün, kartı yok)"})
                continue
        if ad in ("alin_saci_yerlesimi", "bas_makas_z_yerlesimi", "c_kapama_yerlesimi") and not any(m["rol"] == "bas" for m in g["makaslar"]):
            kural_yok.append({"parca": adi, "sinif": sinif, "neden": f"{ad}: bugünkü IFC'de baş makas yok (kalkan kenarı kurulamaz)"})
            continue
        kurulan.add(ad)
    if "sacak_omegasi_yerlesimi" in kurulan:
        parcalar += sacak_omegasi(g, G_)
    if "sacak_saci_yerlesimi" in kurulan:
        parcalar += sacak_saci(g, G_)
    parcalar += kalkan_kenarlari(g, G_, kesit, kurulan)
    if "mahya_yerlesimi" in kurulan:
        parcalar += mahya(g, G_, kesit)
    return {"parcalar": parcalar, "kural_yok": kural_yok, "uyarilar": uyarilar, "hatlar": hatlar}
