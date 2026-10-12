"""6 Ekim 2026 denemesi: aynı gövdenin üzerine çatı seçenekleri (3D sunum sayfası için).

İstek (Lokman, 6 Ekim 21:26): videolardaki çatı şekilleri, bizim kurallarımıza göre, Astra'nın P9401'de yaptığı gibi
(dört çatı seçeneği, kartlarla). Dayanak: `docs/sartname/cati.md` — "Çatılar bütün kategorilerde aynıdır: beşik, cumba,
dört omuz/kırma"; "Eğim değişmez" (%33); saçak 30 cm; topuk 10 cm.

Videodaki 44 seçenek çatı değil, ev biçimidir (T, L, H, avlulu, iki katlı…). Dikdörtgen tek katlı bu plana düşen çatı
aileleri burada üretilir. Kurala uyanlar "kurallı", kuralın dışına çıkanlar (eğim, parapet, iç dere) "öneri" diye işaretlenir.

Geometri kuraldan hesaplanır, sayfada çizilmez: örtü düzlemleri, kalkan (alın) kapamaları, pano akslarındaki makaslar.
Ölçüler cm, plan eksenleri (x sağa, y arkaya, z yukarı). Çıktı sayfanın beklediği biçimdedir (metre; x, z, −y).
Makas biçimleri şematiktir; statik hesap değildir.
"""
from __future__ import annotations
import math

KAPLAMA = 14.0      # örtü kalınlığı (görünüş paftası ve IFC ile aynı)
KUSAK = 8.0         # makas başlığı yüksekliği (şematik)
UYE_EN = 5.0        # makas üyesinin eni (şematik)
MOD = 125.5


def _v(p):
    """Plan (cm) → sayfa (m): x, z, −y."""
    return [round(p[0] / 100.0, 4), round(p[2] / 100.0, 4), round(-p[1] / 100.0, 4)]


def prizma(ust: list[tuple], ofset: tuple) -> tuple[list, list]:
    """Düzlemsel dışbükey çokgen `ust`, `ofset` vektörü kadar ötelenerek kapalı prizma olur."""
    n = len(ust); alt = [(p[0] + ofset[0], p[1] + ofset[1], p[2] + ofset[2]) for p in ust]
    v = [c for p in ust + alt for c in _v(p)]; i = []
    for k in range(1, n - 1):
        i += [0, k, k + 1, n, n + k + 1, n + k]
    for k in range(n):
        j = (k + 1) % n
        i += [k, j, n + j, k, n + j, n + k]
    return v, i


def parca(g: str, ad: str, bilgi: str, ust: list[tuple], ofset: tuple, **ek) -> dict:
    v, i = prizma(ust, ofset)
    return {"g": g, "ad": ad, "b": bilgi, "t": "", "r": [0.7, 0.7, 0.7], "o": 1.0, "v": v, "i": i, **ek}


def ortu(ad: str, bilgi: str, ust: list[tuple], hadve: str, **ek) -> dict:
    """Çatı örtüsü: üst yüzü `ust` olan, aşağı doğru KAPLAMA kalınlığında levha. hadve: dokunun tekrar ettiği sayfa ekseni."""
    return parca("cati", ad, bilgi, ust, (0.0, 0.0, -KAPLAMA), h=hadve, **ek)


def makas(eksen: str, a: float, S: float, H0: float, zfun, kirik: list[float], sacak: float, ad: str, bilgi: str) -> list[dict]:
    """Bir makas: alt başlık, örtünün altını izleyen üst başlık, dikmeler ve çaprazlar (şematik).
    eksen 'x': makas x = a düzleminde, açıklık y boyunca. eksen 'y': makas y = a düzleminde, açıklık x boyunca.
    zfun(u): örtünün alt yüzünün kotu. kirik: üst başlığın yön değiştirdiği yerler."""
    def uye(k: int, pts: list[tuple]) -> dict:
        if eksen == "x":
            ust = [(a - UYE_EN / 2, u, z) for u, z in pts]; of = (UYE_EN, 0.0, 0.0)
        else:
            ust = [(u, a - UYE_EN / 2, z) for u, z in pts]; of = (0.0, UYE_EN, 0.0)
        return parca("makas", f"{ad}_{k}", bilgi, ust, of)
    out = []; zt = H0 + KUSAK
    out.append(uye(0, [(0, H0), (S, H0), (S, zt), (0, zt)]))                                   # alt başlık
    dugum = sorted({-sacak, S + sacak, *kirik})
    for k, (u0, u1) in enumerate(zip(dugum, dugum[1:]), 1):                                  # üst başlık parçaları
        out.append(uye(k, [(u0, zfun(u0)), (u1, zfun(u1)), (u1, zfun(u1) - KUSAK), (u0, zfun(u0) - KUSAK)]))
    dik = sorted({*[u for u in kirik if 0 < u < S], S / 4, S / 2, 3 * S / 4})
    dik = [u for u in dik if zfun(u) - KUSAK - zt > 12]
    for k, u in enumerate(dik, 20):                                                          # dikmeler
        out.append(uye(k, [(u - 2.5, zt), (u + 2.5, zt), (u + 2.5, zfun(u) - KUSAK), (u - 2.5, zfun(u) - KUSAK)]))
    for k, (u0, u1) in enumerate(zip(dik, dik[1:]), 40):                                     # çaprazlar: alçak dikmenin tepesinden yüksek dikmenin dibine
        h0, h1 = zfun(u0), zfun(u1)
        (ua, ub) = (u0, u1) if h0 <= h1 else (u1, u0)
        za = zfun(ua) - KUSAK
        yon = 1 if ub > ua else -1
        out.append(uye(k, [(ua, za), (ua + yon * 6, za), (ub, zt), (ub - yon * 6, zt)]))
    return out


def akslar(boy: float, t_dis: float, ilk: float) -> list[float]:
    """Makas aksları: iki baş makas kalkan duvarların ekseninde, orta makaslar pano eklerinde."""
    orta = []; k = 1
    while ilk + MOD * k < boy - t_dis - 1e-6:
        orta.append(round(ilk + MOD * k, 2)); k += 1
    return [t_dis / 2, *orta, boy - t_dis / 2]


def tr(v: float, n: int = 2) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def uret(W: float, H: float, H0: float, t_dis: float, egim: float, sacak: float, topuk: float, ana: list[dict], ana_mahya: str) -> list[dict]:
    """Çatı seçenekleri. `ana`: IFC'den gelen bugünkü çatının parçaları (A seçeneği); ana_mahya: 'x' ya da 'y' (plan ekseni)."""
    e, s = egim, sacak
    zs = H0 + topuk                                          # örtü alt yüzünün saçak ucundaki kotu
    xs = akslar(W, t_dis, t_dis); ys = akslar(H, t_dis, t_dis / 2)
    egik = math.sqrt(1 + e * e)
    alan_tam = (W + 2 * s) * (H + 2 * s) * egik / 1e4        # eğim sabitken örtü alanı biçimden bağımsız
    U = KAPLAMA
    out = []

    def besik(kod: str, mahya: str) -> dict:
        S, L, ax = (H, W, xs) if mahya == "x" else (W, H, ys)   # açıklık, mahya boyu, makas aksları
        zm = zs + (S / 2 + s) * e
        zf = lambda u: zs + (min(u, S - u) + s) * e
        kalkan = S * ((zf(0) - H0) + (zm - H0)) / 2 / 1e4
        olcu = [("Mahya kotu", f"{tr(zm / 100)} m (örtü üstü {tr((zm + U) / 100)})"), ("Eğim", f"%{e * 100:g}"), ("Saçak / topuk", f"{s:g} / {topuk:g} cm"),
                ("Makas", f"{len(ax)} adet · açıklık {tr(S / 100)} m"), ("Mahya boyu", f"{tr((L + 2 * s) / 100)} m"),
                ("Örtü alanı", f"{tr(alan_tam, 1)} m²"), ("Kalkan duvar", f"2 × {tr(kalkan, 1)} m²")]
        el = None
        if mahya != ana_mahya or not ana:
            el = []
            if mahya == "x":
                el.append(ortu(f"CATI_{kod}_ON", "Çatı örtüsü · ön yüz", [(-s, -s, zs + U), (W + s, -s, zs + U), (W + s, H / 2, zm + U), (-s, H / 2, zm + U)], "x"))
                el.append(ortu(f"CATI_{kod}_ARKA", "Çatı örtüsü · arka yüz", [(-s, H + s, zs + U), (W + s, H + s, zs + U), (W + s, H / 2, zm + U), (-s, H / 2, zm + U)], "x"))
                for ad, x0 in (("SOL", 0.0), ("SAG", W - t_dis)):
                    el.append(parca("alin", f"ALIN_{kod}_{ad}", "Kalkan duvar kapaması", [(x0, 0, H0), (x0, H, H0), (x0, H, zf(H)), (x0, H / 2, zm), (x0, 0, zf(0))], (t_dis, 0, 0)))
            else:
                el.append(ortu(f"CATI_{kod}_SOL", "Çatı örtüsü · sol yüz", [(-s, -s, zs + U), (-s, H + s, zs + U), (W / 2, H + s, zm + U), (W / 2, -s, zm + U)], "z"))
                el.append(ortu(f"CATI_{kod}_SAG", "Çatı örtüsü · sağ yüz", [(W + s, -s, zs + U), (W + s, H + s, zs + U), (W / 2, H + s, zm + U), (W / 2, -s, zm + U)], "z"))
                for ad, y0 in (("ON", 0.0), ("ARKA", H - t_dis)):
                    el.append(parca("alin", f"ALIN_{kod}_{ad}", "Kalkan duvar kapaması", [(0, y0, H0), (W, y0, H0), (W, y0, zf(W)), (W / 2, y0, zm), (0, y0, zf(0))], (0, t_dis, 0)))
            for k, a in enumerate(ax):
                el += makas("x" if mahya == "x" else "y", a, S, H0, zf, [S / 2], s, f"MAKAS_{kod}_{k:02d}", f"Makas {k + 1} · açıklık {tr(S / 100)} m")
        return {"olcu": olcu, "el": el if el is not None else ana, "zm": zm}

    # A, B · beşik (kurallı)
    for kod, mahya, ad, alt in (("A", "x", "Beşik · mahya önde", "Mahya ön cepheye paralel; kalkanlar yanlarda"),
                                ("B", "y", "Beşik · kalkan önde", "Mahya yan cepheye paralel; kalkan ön cephede")):
        b = besik(kod, mahya)
        S = H if mahya == "x" else W
        out.append({"kod": kod, "ad": ad, "alt": alt, "kurali": True, "durum": "Kurallı",
                    "aciklama": f"Beşik çatı; makaslar {tr(S / 100)} m'lik kenarı geçer." + (" Bu yapının bugünkü çatısı." if mahya == ana_mahya else ""),
                    "not": "Eğim, saçak ve topuk şartnamedeki değerlerdir. Makaslar pano akslarındadır (çıkarım; P6001 gerçek listesinden)."
                           + ("" if mahya == "x" else " Arkadaki 30 cm'lik kesilmiş pano yüzünden son iki makas 30 cm arayla düşer; teyit ister."),
                    "olcu": b["olcu"], "el": b["el"]})

    # C · kırma / dört omuz (biçim kurallı; makas dizilimi çıkarım)
    yari = H / 2 + s; zm = zs + yari * e
    x1, x2 = -s + yari, W + s - yari                           # mahyanın uçları
    zf_yan = lambda x: zs + (min(x, W - x) + s) * e
    kirma_boy = math.sqrt(2 * yari * yari + (yari * e) ** 2)
    el = [ortu("CATI_C_ON", "Çatı örtüsü · ön yüz (yamuk)", [(-s, -s, zs + U), (W + s, -s, zs + U), (x2, H / 2, zm + U), (x1, H / 2, zm + U)], "x"),
          ortu("CATI_C_ARKA", "Çatı örtüsü · arka yüz (yamuk)", [(-s, H + s, zs + U), (W + s, H + s, zs + U), (x2, H / 2, zm + U), (x1, H / 2, zm + U)], "x"),
          ortu("CATI_C_SOL", "Çatı örtüsü · sol yüz (üçgen)", [(-s, -s, zs + U), (-s, H + s, zs + U), (x1, H / 2, zm + U)], "z"),
          ortu("CATI_C_SAG", "Çatı örtüsü · sağ yüz (üçgen)", [(W + s, -s, zs + U), (W + s, H + s, zs + U), (x2, H / 2, zm + U)], "z")]
    for k, a in enumerate(xs):
        tavan = min(zf_yan(a), zm)                              # bu akstaki makasın üst kotu: yan yüzün o noktadaki kotu
        u1 = (tavan - zs) / e - s
        zf = lambda u, tavan=tavan: min(zs + (min(u, H - u) + s) * e, tavan)
        kirik = [H / 2] if u1 >= H / 2 - 1e-6 else [u1, H - u1]
        el += makas("x", a, H, H0, zf, kirik, s, f"MAKAS_C_{k:02d}", f"Kırma makası {k + 1} · üst kot {tr(tavan / 100)} m")
    out.append({"kod": "C", "ad": "Kırma · dört omuz", "alt": "Dört yöne eğimli; kalkan duvar yok", "kurali": True, "durum": "Kurallı biçim · makas dizilimi çıkarım",
                "aciklama": "Dört omuz (kırma) çatı: yandan %33, önden de kırılır; mahya ortada kalan kısımdır.",
                "not": "Biçim şartnamedeki tanımdır. Kademeli kırma makası dizilimi çıkarımdır; prefabrikte kırma çatının makas kuralı henüz yazılmadı.",
                "olcu": [("Mahya kotu", f"{tr(zm / 100)} m (örtü üstü {tr((zm + U) / 100)})"), ("Eğim", f"%{e * 100:g}, dört yüzde"), ("Saçak / topuk", f"{s:g} / {topuk:g} cm"),
                         ("Makas", f"{len(xs)} adet · açıklık {tr(H / 100)} m · kademeli"), ("Mahya boyu", f"{tr((x2 - x1) / 100)} m"),
                         ("Kırma hattı", f"4 × {tr(kirma_boy / 100)} m"), ("Örtü alanı", f"{tr(alan_tam, 1)} m²"), ("Kalkan duvar", "yok")],
                "el": el})

    # D · tek eğimli (öneri; eğim kuralın dışında)
    p = 0.10
    zf = lambda u: zs + (u + s) * p
    z_on, z_arka = zs, zs + (H + 2 * s) * p
    el = [ortu("CATI_D", "Çatı örtüsü · tek yüz", [(-s, -s, z_on + U), (W + s, -s, z_on + U), (W + s, H + s, z_arka + U), (-s, H + s, z_arka + U)], "x")]
    el.append(parca("alin", "ALIN_D_ARKA", "Arka duvar üst kapaması", [(0, H - t_dis, H0), (W, H - t_dis, H0), (W, H - t_dis, zf(H)), (0, H - t_dis, zf(H))], (0, t_dis, 0)))
    el.append(parca("alin", "ALIN_D_ON", "Ön duvar üst kapaması", [(0, 0, H0), (W, 0, H0), (W, 0, zf(0)), (0, 0, zf(0))], (0, t_dis, 0)))
    for ad, x0 in (("SOL", 0.0), ("SAG", W - t_dis)):
        el.append(parca("alin", f"ALIN_D_{ad}", "Yan duvar üst kapaması", [(x0, 0, H0), (x0, H, H0), (x0, H, zf(H)), (x0, 0, zf(0))], (t_dis, 0, 0)))
    for k, a in enumerate(xs):
        el += makas("x", a, H, H0, zf, [], s, f"MAKAS_D_{k:02d}", f"Tek eğimli makas {k + 1} · açıklık {tr(H / 100)} m")
    kapama = (W * (zf(H) - H0) + W * (zf(0) - H0) + 2 * H * ((zf(0) - H0) + (zf(H) - H0)) / 2) / 1e4
    out.append({"kod": "D", "ad": "Tek eğimli", "alt": "Önden arkaya yükselen tek yüz", "kurali": False, "durum": "Öneri · kural dışı (eğim)",
                "aciklama": "Tek yüzeyli çatı; önde alçak, arkada yüksek.",
                "not": f"Eğim %{p * 100:g} alındı. Şartnamede eğim değişmez (%33); %33 ile arka duvar {tr((zs + (H + 2 * s) * e) / 100)} m'ye çıkar. Arka ve yan duvarlara üst kapama gerekir.",
                "olcu": [("Üst kot", f"önde {tr(z_on / 100)} m · arkada {tr(z_arka / 100)} m"), ("Eğim", f"%{p * 100:g} · öneri"), ("Saçak / topuk", f"{s:g} / {topuk:g} cm"),
                         ("Makas", f"{len(xs)} adet · açıklık {tr(H / 100)} m · tek eğimli"), ("Örtü alanı", f"{tr((W + 2 * s) * (H + 2 * s) * math.sqrt(1 + p * p) / 1e4, 1)} m²"),
                         ("Üst kapama", f"{tr(kapama, 1)} m² (arka, ön ve yanlar)")],
                "el": el})

    # E · parapetli düz görünüş (öneri)
    par, q = 45.0, 0.02
    ic0, ic1 = t_dis, t_dis                                   # döşeme parapetin iç yüzünden başlar
    zd = lambda y: H0 + 30.0 - (y - ic0) * q                  # döşeme üstü: önde yüksek, arkaya %2 düşer
    el = [parca("cati", "CATI_E_DOSEME", "Çatı döşemesi · gizli eğim %2", [(ic0, ic0, zd(ic0)), (W - ic0, ic0, zd(ic0)), (W - ic0, H - ic1, zd(H - ic1)), (ic0, H - ic1, zd(H - ic1))],
                (0.0, 0.0, -10.0), duz=True)]
    for ad, (xa, ya, xb, yb) in (("ON", (0, 0, W, t_dis)), ("ARKA", (0, H - t_dis, W, H)), ("SOL", (0, t_dis, t_dis, H - t_dis)), ("SAG", (W - t_dis, t_dis, W, H - t_dis))):
        el.append(parca("alin", f"PARAPET_E_{ad}", f"Parapet · {par:g} cm", [(xa, ya, H0 + par), (xb, ya, H0 + par), (xb, yb, H0 + par), (xa, yb, H0 + par)], (0.0, 0.0, -par)))
    el.append(parca("alin", "PARAPET_E_HARPUSTA_ON", "Parapet kapağı", [(-2, -2, H0 + par + 3.5), (W + 2, -2, H0 + par + 3.5), (W + 2, t_dis + 2, H0 + par + 3.5), (-2, t_dis + 2, H0 + par + 3.5)], (0, 0, -3.5), kapak=True))
    el.append(parca("alin", "PARAPET_E_HARPUSTA_ARKA", "Parapet kapağı", [(-2, H - t_dis - 2, H0 + par + 3.5), (W + 2, H - t_dis - 2, H0 + par + 3.5), (W + 2, H + 2, H0 + par + 3.5), (-2, H + 2, H0 + par + 3.5)], (0, 0, -3.5), kapak=True))
    el.append(parca("alin", "PARAPET_E_HARPUSTA_SOL", "Parapet kapağı", [(-2, t_dis + 2, H0 + par + 3.5), (t_dis + 2, t_dis + 2, H0 + par + 3.5), (t_dis + 2, H - t_dis - 2, H0 + par + 3.5), (-2, H - t_dis - 2, H0 + par + 3.5)], (0, 0, -3.5), kapak=True))
    el.append(parca("alin", "PARAPET_E_HARPUSTA_SAG", "Parapet kapağı", [(W - t_dis - 2, t_dis + 2, H0 + par + 3.5), (W + 2, t_dis + 2, H0 + par + 3.5), (W + 2, H - t_dis - 2, H0 + par + 3.5), (W - t_dis - 2, H - t_dis - 2, H0 + par + 3.5)], (0, 0, -3.5), kapak=True))
    zf = lambda u: zd(min(max(u, ic0), H - ic1)) - 10.0
    for k, a in enumerate(xs[1:-1], 1):
        el += makas("x", a, H, H0, zf, [], 0.0, f"KIRIS_E_{k:02d}", f"Düz çatı kirişi {k} · açıklık {tr(H / 100)} m")
    out.append({"kod": "E", "ad": "Parapetli düz", "alt": "Çatı parapetin arkasında; yatay siluet", "kurali": False, "durum": "Öneri · kural dışı",
                "aciklama": "Düz görünüşlü çatı: örtü parapetin arkasında kalır, saçak yoktur.",
                "not": "Parapet yüksekliği ve gizli eğim tasarım önerisidir. Su tahliyesi, yalıtım ve taşıyıcı çözülmedi; şartnamede bu çatının kuralı yok.",
                "olcu": [("Parapet üstü", f"{tr((H0 + par) / 100)} m ({par:g} cm parapet)"), ("Gizli eğim", f"%{q * 100:g} · arkaya"), ("Saçak", "yok"),
                         ("Kiriş", f"{len(xs) - 2} adet · açıklık {tr(H / 100)} m"), ("Döşeme alanı", f"{tr((W - 2 * ic0) * (H - ic0 - ic1) / 1e4, 1)} m²"),
                         ("Parapet", f"{tr(2 * (W + H) / 100, 1)} m çevre")],
                "el": el})

    # F · üç mahyalı (öneri; eğim kurala uygun, iç dere kuralı yok)
    n = 3; g = W / n; yari = g / 2
    zr = zs + (yari + s) * e                                   # dış yüzlerde saçak var; mahyalar aynı kotta
    zf = lambda x: zr - abs(((x % g) if 0 <= x <= W else (x if x < 0 else x - (n - 1) * g)) - yari) * e
    zdere = zr - yari * e
    el = []
    for k in range(n):
        c = g * k + yari; xa = -s if k == 0 else g * k; xb = W + s if k == n - 1 else g * (k + 1)
        za, zb = zr - (c - xa) * e, zr - (xb - c) * e
        el.append(ortu(f"CATI_F_{k + 1}_SOL", f"Çatı örtüsü · {k + 1}. beşik, sol yüz", [(xa, -s, za + U), (xa, H + s, za + U), (c, H + s, zr + U), (c, -s, zr + U)], "z"))
        el.append(ortu(f"CATI_F_{k + 1}_SAG", f"Çatı örtüsü · {k + 1}. beşik, sağ yüz", [(xb, -s, zb + U), (xb, H + s, zb + U), (c, H + s, zr + U), (c, -s, zr + U)], "z"))
        for ad, y0 in (("ON", 0.0), ("ARKA", H - t_dis)):
            el.append(parca("alin", f"ALIN_F_{k + 1}_{ad}", "Kalkan duvar kapaması", [(g * k, y0, H0), (g * (k + 1), y0, H0), (g * (k + 1), y0, zf(g * (k + 1) - 1e-6)), (c, y0, zr), (g * k, y0, zf(g * k + 1e-6))], (0, t_dis, 0)))
    kirik = [g * k + yari for k in range(n)] + [g * k for k in range(1, n)]
    for k, a in enumerate(ys):
        el += makas("y", a, W, H0, zf, kirik, s, f"MAKAS_F_{k:02d}", f"Üç gözlü makas {k + 1} · açıklık {tr(W / 100)} m")
    kalkan = n * g * ((zf(1e-6) - H0) + (zr - H0)) / 2 / 1e4
    out.append({"kod": "F", "ad": "Üç mahyalı", "alt": "Yan yana üç beşik; önde üç kalkan", "kurali": False, "durum": "Öneri · iç dere kuralı yok",
                "aciklama": "Yan yana üç küçük beşik çatı; ön cephede üç kalkan görünür.",
                "not": "Eğim %33 ile kurala uygundur, çatı alçalır. Beşikler arasında iki iç dere oluşur; iç derenin ve bu makasın kuralı şartnamede yok.",
                "olcu": [("Mahya kotu", f"{tr(zr / 100)} m (örtü üstü {tr((zr + U) / 100)})"), ("Eğim", f"%{e * 100:g}"), ("Saçak / topuk", f"{s:g} / {topuk:g} cm"),
                         ("Makas", f"{len(ys)} adet · açıklık {tr(W / 100)} m · üç gözlü"), ("Mahya boyu", f"3 × {tr((H + 2 * s) / 100)} m"),
                         ("İç dere", f"2 × {tr((H + 2 * s) / 100)} m · kot {tr(zdere / 100)} m"), ("Örtü alanı", f"{tr(alan_tam, 1)} m²"), ("Kalkan duvar", f"2 × {tr(kalkan, 1)} m²")],
                "el": el})
    return out
