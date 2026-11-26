"""Plandan çelik makas çerçevesi (BK-78 Parça 2, taslak): beşik, tek eğim (kısa) ve çapraz makas.

Kalıp 90 m² çelik evin onaylı makas üretim dosyasıdır (`testler/uretim/veri/celik_90m2/80X0,8_MAKAS_PANELLERI.bde`;
Lokman 25 Kasım 2026 21:14:35 UTC "sadece çatı üretim dosyasın alacaksın 63 m² uyduracaksın"):
beşik M01–M05, kısa M09–M12, çapraz M13. Kalıbın W örgüsü yeni açıklığa eşit panellerle uyarlanır.
Makine işlemlerini `islem.uret()` verir; çıktı MRD (FrameBuilder CSV) çerçevesidir.

Eksen: çerçeve düzleminde mm. x alt başlık boyunca, y yukarı; alt başlığın alt yüzü y=0, x=0 dış uç.
Koordinatlar parçanın eksenidir (kanat ortası, sırttan 27 mm). x=0: beşikte saçak ucu, tek eğimde yüksek uç,
çaprazda alçak uç (saçak köşesi).

Kalıptan ölçülen sabitler (90 m², `testler/uretim/test_makas.py` kalıbı bu kodla yeniden kurar):
- üst başlık ekseni dış uçta topuk − 27 / cos(eğim açısı) yükseklikte;
- örgü çubuğunun ucu başlık ekseninden öteye geçer: üst başlıkta (21 − 27·cos θ) / sin θ, alt başlıkta 5 + 0,15·θ°;
  düşey çubukta altta 21 mm;
- bir düğümde iki örgü çubuğu ayrık biter: üst başlıkta eksenler arası 51 mm, altta her çubuk için
  28,35 / sin θ + 18,35 · cot θ;
- panel aralığı: beşik 606,6 mm, kısa 413,5 mm, çapraz 414,5 mm (en yakın tam sayıda eşit panel).
"""
from __future__ import annotations

import math

from . import islem

YARIM = 27.0
UST_ARA = 51.0             # üst başlıkta iki örgü ekseninin arası
TOPUK_UCU = 20.5           # üst başlığın alçak ucu düşey ekseninden öteye (başlık boyunca)
YUKSEK_UCU = 33.5          # tek eğimde üst başlığın yüksek ucu
TEPE_UCU = 8.8             # beşikte üst başlık tepeden öteye
DUSEY_ALT = 21.0           # düşey çubuk alt başlık ekseninden aşağı
DUSEY_ALT_Y = 6.0          # düşeyin alt ucu (y)
YUKSEK_PAY = 0.415         # tek eğimde uç panel: yüksek uçta 0,415, saçak ucunda 0,365 panel
SACAK_PAY = 0.365
PROFIL = {"kesit": "C", "sirt": 80.0, "kanat": 54.0, "kalinlik": 0.8, "kod": "550"}


def _ust_gec(teta):
    return max(2.0, (21.0 - YARIM * math.cos(teta)) / math.sin(teta))


def _alt_gec(teta):
    return 5.0 + 0.15 * math.degrees(teta)


def _alt_yari(teta):
    return 28.35 / math.sin(teta) + 18.35 / math.tan(teta)


class _Kur:
    def __init__(self, L, ust_y, egim):
        self.L, self.ust_y, self.egim = L, ust_y, egim   # ust_y(x): üst başlık ekseninin y'si
        self.cubuklar = []

    def ekle(self, ad, yon, x1, y1, x2, y2):
        self.cubuklar.append({"ad": ad, "yon": yon, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    def dusey(self, ad, yon, x, ust_egim):
        teta = math.atan(1 / abs(ust_egim)) if ust_egim else math.pi / 2
        self.ekle(ad, yon, x, DUSEY_ALT_Y, x, self.ust_y(x) + _ust_gec(teta))

    def orgu(self, ad, alt_x, ust_x, egim_ust, asagi):
        """Alt düğüm alt_x ile üst düğüm ust_x arasındaki örgü çubuğu; asagi: üstten alta çizilir."""
        ux, uy = ust_x - alt_x, self.ust_y(ust_x) - YARIM
        u = math.hypot(ux, uy)
        ux, uy = ux / u, uy / u
        teta_alt = math.atan2(abs(uy), abs(ux))
        bx, by = ux, egim_ust * ux
        teta_ust = math.asin(min(1.0, abs(ux * by - uy * bx) / math.hypot(bx, by)))
        ga, gu = _alt_gec(teta_alt), _ust_gec(teta_ust)
        a = (alt_x - ux * ga, YARIM - uy * ga)
        b = (ust_x + ux * gu, self.ust_y(ust_x) + uy * gu)
        if asagi:
            self.ekle(ad, "LABEL_INV", b[0], b[1], a[0], a[1])
        else:
            self.ekle(ad, "LABEL_INV", a[0], a[1], b[0], b[1])
        return teta_alt


def _alt_dugum(alt_x, ust_x, ust_y):
    return math.atan2(ust_y(ust_x) - YARIM, abs(ust_x - alt_x))


def _ust_ekseni(topuk, egim):
    return topuk - YARIM / math.cos(math.atan(egim))


def besik(L, egim, topuk=100.0, sacak=300.0, panel=606.6):
    """Simetrik beşik makas. L: alt başlık boyu (saçak ucundan saçak ucuna), mm."""
    y0 = _ust_ekseni(topuk, egim)
    a = L / 2
    ust_y = lambda x: y0 + egim * (x if x <= a else L - x)   # noqa: E731
    k = _Kur(L, ust_y, egim)
    sl = sacak - YARIM
    bd_ust, b0, b0_yari = sl + 93.8, sl + 366.6, 63.4
    b1 = b0 + 616.0                 # kalıpta ilk panel öbürlerinden 9 mm uzun
    n = max(1, round((a - b1) / panel))
    p = (a - b1) / n
    B = [b0] + [b1 + j * p for j in range(n + 1)]
    T = [(B[j] + B[j + 1]) / 2 for j in range(n + 1)]
    n += 1

    sol = []
    alt_ilk = lambda bx, tx: bx + _alt_yari(_alt_dugum(bx, tx, ust_y))   # noqa: E731
    alt_son = lambda bx, tx: bx - _alt_yari(_alt_dugum(bx, tx, ust_y))   # noqa: E731
    for j in range(n):
        bx = B[j] + b0_yari if j == 0 else alt_ilk(B[j], T[j])
        sol.append(("BR", bx, T[j] - UST_ARA / 2, False))
        sol.append(("BL", alt_son(B[j + 1], T[j]), T[j] + UST_ARA / 2, True))

    k.ekle("PR", "LABEL_INV", YARIM, DUSEY_ALT_Y, YARIM, ust_y(YARIM) + _ust_gec(math.pi / 2 - math.atan(egim)))
    c = math.cos(math.atan(egim))
    k.ekle("PD", "LABEL_INV", YARIM - TOPUK_UCU * c, ust_y(YARIM - TOPUK_UCU * c), a + TEPE_UCU * c, ust_y(a) + TEPE_UCU * c * egim)
    k.ekle("PU", "LABEL_NRM", 0.0, YARIM, L, YARIM)
    k.dusey("SL", "LABEL_NRM", sl, egim)
    k.orgu("BD", b0 - b0_yari, bd_ust, egim, True)
    for ad, bx, tx, asagi in sol:
        k.orgu(ad, bx, tx, egim, asagi)
    sag = []
    for ad, bx, tx, asagi in reversed(sol):
        sag.append(("BL" if ad == "BR" else "BR", L - bx, L - tx, not asagi))
    for i, (ad, bx, tx, asagi) in enumerate(sag):
        k.orgu(ad, bx, tx, -egim, asagi)
        if i == 0:                   # kalıptaki sıra: tepedeki ilk sağ örgüden sonra sağ üst başlık
            k.ekle("PD", "LABEL_INV", a - TEPE_UCU * c, ust_y(a) + TEPE_UCU * c * egim,
                   L - YARIM + TOPUK_UCU * c, ust_y(YARIM - TOPUK_UCU * c))
    k.orgu("BD", L - b0 + b0_yari, L - bd_ust, -egim, False)
    k.dusey("SR", "LABEL_INV", L - sl, -egim)
    k.ekle("PL", "LABEL_NRM", L - YARIM, DUSEY_ALT_Y, L - YARIM, ust_y(YARIM) + _ust_gec(math.pi / 2 - math.atan(egim)))
    return k.cubuklar, {"tur": "beşik", "panel": n, "aralik": p}


def _tek_egim(L, H, topuk, egim_isaret, bas_ilk, bas_son, panel, e_bas, e_son, sacak_x=None, sacak_basta=False):
    """Ortak tek eğim kurucu. egim_isaret −1: yüksek uç x=0'da (kısa); +1: alçak uç x=0'da (çapraz)."""
    egim = (H - topuk) / L
    dis = _ust_ekseni(topuk, egim)
    if egim_isaret < 0:
        ust_y = lambda x: dis + egim * (L - x)   # noqa: E731
    else:
        ust_y = lambda x: dis + egim * x         # noqa: E731
    s = egim_isaret * egim
    k = _Kur(L, ust_y, s)
    ara = bas_son - bas_ilk
    n = max(1, round(ara / panel - e_bas - e_son + 1))
    p = ara / (n - 1 + e_bas + e_son)
    T = [bas_ilk + e_bas * p + j * p for j in range(n)]
    B = [bas_ilk] + [t + p / 2 for t in T[:-1]] + [bas_son]
    c = math.cos(math.atan(egim))
    yuksek, alcak = (YUKSEK_UCU, TOPUK_UCU) if egim_isaret < 0 else (TOPUK_UCU, YUKSEK_UCU)
    k.ekle("PR", "LABEL_INV", YARIM, DUSEY_ALT_Y, YARIM, ust_y(YARIM) + _ust_gec(math.pi / 2 - math.atan(egim)))
    k.ekle("PU", "LABEL_NRM", 0.0, YARIM, L, YARIM)
    x1, x2 = YARIM - yuksek * c, L - YARIM + alcak * c
    k.ekle("PD", "LABEL_INV", x1, ust_y(x1), x2, ust_y(x2))
    if sacak_basta:
        k.dusey("SL", "LABEL_NRM", sacak_x, s)
    for j in range(n):
        bx = B[j] if j == 0 else B[j] + _alt_yari(_alt_dugum(B[j], T[j], ust_y))
        k.orgu("BR", bx, T[j] - UST_ARA / 2, s, False)
        son = B[j + 1] if j == n - 1 else B[j + 1] - _alt_yari(_alt_dugum(B[j + 1], T[j], ust_y))
        k.orgu("BL", son, T[j] + UST_ARA / 2, s, True)
    if sacak_x is not None and not sacak_basta:
        k.dusey("SR", "LABEL_INV", sacak_x, s)
    k.ekle("PL", "LABEL_NRM", L - YARIM, DUSEY_ALT_Y, L - YARIM, ust_y(L - YARIM) + _ust_gec(math.pi / 2 - math.atan(egim)))
    return k.cubuklar, {"panel": n, "aralik": p, "egim": egim}


def tek(L, egim, topuk=100.0, sacak=300.0, panel=413.5):
    """Kısa makas (tek eğim): yüksek uç x=0'da duvarda, alçak uç x=L'de saçakta."""
    H = topuk + egim * L
    sr = L - sacak + YARIM
    cub, bilgi = _tek_egim(L, H, topuk, -1, YARIM + 57.3, sr - 238.1, panel, YUKSEK_PAY, SACAK_PAY, sacak_x=sr)
    bilgi.update(tur="tek eğim", yukseklik=H)
    return cub, bilgi


def capraz(L, H, sacak, topuk=100.0, panel=414.5):
    """Çapraz makas: alçak uç x=0'da saçak köşesinde, yüksek uç x=L'de (H: dış yükseklik).
    sacak: alt başlık boyunca saçak ucundan duvar çizgisine mm."""
    sl = sacak - YARIM
    cub, bilgi = _tek_egim(L, H, topuk, +1, sl + 126.0, L - YARIM - 57.4, panel, SACAK_PAY, YUKSEK_PAY, sacak_x=sl, sacak_basta=True)
    bilgi.update(tur="çapraz", yukseklik=H)
    return cub, bilgi


def mrd_cercevesi(ad, cubuklar):
    """Çubuklardan MRD çerçevesi; işlemler islem.uret()'ten. Boy uçlar arası, 0,01 mm'ye yuvarlı."""
    parcalar = []
    for i, c in enumerate(cubuklar, 1):
        x1, y1, x2, y2 = (round(c[k], 2) for k in ("x1", "y1", "x2", "y2"))
        parcalar.append({"ad": f"{ad}-{i}", "yon": c["yon"], "adet": 1, "boy": round(math.hypot(x2 - x1, y2 - y1), 2),
                         **PROFIL, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "islemler": []})
    for p, isl in zip(parcalar, islem.uret(parcalar)):
        sira = {k: i for i, k in enumerate(islem.SIRA)}
        p["islemler"] = sorted(((k, round(v, 2)) for k, v in isl), key=lambda kv: (sira[kv[0]], kv[1]))
    baslik = [["UNIT", "MILLIMETRE"], ["VERSION", "2"], ["PROFILE", "54.00x80.00", "Standard Profile"], ["FRAMESET", ad, "TASLAK"]]
    return {"baslik": baslik, "cerceve": ad, "parcalar": parcalar, "bom": False, "son_satir_bos": True}


def girdiden(girdi: dict) -> list[dict]:
    """Girdi: {"cati": {egim, topuk_mm, sacak_mm}, "makaslar": [{ad, tur, alt_baslik_mm, …}]}. Çıktı MRD çerçeveleri."""
    cati = girdi["cati"]
    topuk, sacak = cati["topuk_mm"], cati["sacak_mm"]
    sonuc = []
    for m in girdi["makaslar"]:
        L = m["alt_baslik_mm"]
        if m["tur"] in ("ana", "cumba"):
            cub, bilgi = besik(L, m.get("egim", cati["egim"]), topuk, sacak)
        elif m["tur"] == "kisa":
            cub, bilgi = tek(L, m["egim"], topuk, sacak)
        elif m["tur"] == "capraz":
            cub, bilgi = capraz(L, m["yuksek_uc_mm"], m["sacak_mm"], topuk)
        else:
            raise ValueError(f"bilinmeyen makas türü: {m['tur']}")
        v = mrd_cercevesi(m["ad"], cub)
        v["bilgi"] = bilgi
        sonuc.append(v)
    return sonuc


def main(argv=None) -> int:
    import argparse
    import json
    from pathlib import Path

    from . import mrd

    ap = argparse.ArgumentParser(prog="python -m araclar.uretim.makas",
                                 description="Makas girdisinden MRD CSV çerçeveleri yazar (taslak).")
    ap.add_argument("girdi")
    ap.add_argument("klasor")
    a = ap.parse_args(argv)
    girdi = json.loads(Path(a.girdi).read_text(encoding="utf-8"))
    hedef = Path(a.klasor)
    hedef.mkdir(parents=True, exist_ok=True)
    for v in girdiden(girdi):
        (hedef / f"{v['cerceve']}.csv").write_bytes(mrd.yaz(v))
        o = mrd.ozet(v)
        print(f"{v['cerceve']}: {v['bilgi']['tur']}, {o['cubuk']} çubuk, {o['toplam_boy_m']} m, dış {o['dis_olcu_mm']} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
