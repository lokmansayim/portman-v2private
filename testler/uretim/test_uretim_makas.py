"""BK-78 Parça 2: plandan makas çerçevesi (araclar/uretim/makas.py).

1. Kalıbı yeniden kurmak: 90 m² çelik evin makas üretim dosyasındaki ana (M01), kısa (M09) ve çapraz (M13)
   makas, kendi ölçüleriyle kurulunca çubuk uçları dosyadakine en çok 9 / 16 / 16 mm, boylar 4 / 6 / 8 mm yakın.
   Dosyadaki çubuğun gerçek uçları .bde'nin vida yerlerinden çıkar; o uçlarla islem.uret() vidaları
   dosyayla bire bir verir (138/138, 44/44, 52/52).
2. 63 m² makasları (Motor'un yerleşimi, Lokman 26 Kasım 05:50:56 "sen motora uy"; cumbada 2 makas, 05:52:33): depodaki CSV'ler girdiden yeniden üretilince bayt bayt aynı. Hedef örnek: Lokman 26 Kasım 2026 05:53:56 UTC
   kartı "A: Evet, böyle üretilsin" (r03 çizimi, 14 makas, 328 çubuk).
"""
import math
from pathlib import Path

import pytest

from araclar.uretim import bde, islem, makas, mrd

KOK = Path(__file__).resolve().parents[2]
KALIP = KOK / "testler/uretim/veri/celik_90m2/80X0,8_MAKAS_PANELLERI.bde"
M63 = KOK / "araclar/uretim/veri/makas_63m2"


def _gercek_uclar(cubuklar):
    """.bde çubuklarının eksen üstündeki gerçek uçları (kesim başı vida yerlerinden)."""
    hatlar = [bde.vida_hatti(c) for c in cubuklar]
    sonuc = []
    for i, (c, hat) in enumerate(zip(cubuklar, hatlar)):
        yerler = []
        for j, h2 in enumerate(hatlar):
            k = bde._kesis(hat, h2) if i != j else None
            if k and -300 < k[0] < hat[4] + 300 and -300 < k[1] < h2[4] + 300:
                yerler.append(k[0])
        en = (0, 0.0)
        for t in yerler:
            for h in c["h"]:
                say = sum(1 for hh in c["h"] if any(abs(t - h + hh - y) < 1.0 for y in yerler))
                if say > en[0]:
                    en = (say, t - h)
        x, y, ux, uy, _ = hat
        ax, ay = bde.YONLER[c["tip"][1]]
        k = en[1]
        sonuc.append({"ad": c["tip"], "yon": "LABEL_NRM" if (-uy * ax + ux * ay) > 0 else "LABEL_INV", "boy": c["boy"],
                      "x1": x + ux * k, "y1": y + uy * k, "x2": x + ux * (k + c["boy"]), "y2": y + uy * (k + c["boy"]),
                      "h": c["h"], "islemler": []})
    return sonuc


@pytest.fixture(scope="module")
def kalip():
    return bde.panolar(bde.oku(KALIP))


@pytest.mark.parametrize("pano", ["M01", "M09", "M13"])
def test_kalip_vidalari_islem_kurallariyla(kalip, pano):
    P = _gercek_uclar(kalip[pano])
    for p, u in zip(P, islem.uret(P)):
        d = sorted(v for k, v in u if k == "DIMPLE")
        assert len(d) == len(p["h"]) and all(abs(a - b) < 1.0 for a, b in zip(d, sorted(p["h"])))


@pytest.mark.parametrize("pano, kur, uc_mm, boy_mm", [
    ("M01", lambda: makas.besik(9790, 0.33), 9.0, 4.0),
    ("M09", lambda: makas.tek(2160, 495 / 2160), 16.0, 6.0),
    ("M13", lambda: makas.capraz(2583, 586, 417.5), 16.0, 8.0),
])
def test_kalibi_yeniden_kurar(kalip, pano, kur, uc_mm, boy_mm):
    P = _gercek_uclar(kalip[pano])
    cub, _ = kur()
    assert [c["ad"] for c in cub] == [p["ad"] for p in P]
    assert [c["yon"] for c in cub] == [p["yon"] for p in P]
    for p, c in zip(P, cub):
        uc = max(math.hypot(p["x1"] - c["x1"], p["y1"] - c["y1"]), math.hypot(p["x2"] - c["x2"], p["y2"] - c["y2"]))
        assert uc <= uc_mm, (p["ad"], uc)
        assert abs(math.hypot(c["x2"] - c["x1"], c["y2"] - c["y1"]) - p["boy"]) <= boy_mm


def test_63m2_makaslari_girdiden_ayni(tmp_path):
    assert makas.main([str(M63 / "girdi.json"), str(tmp_path)]) == 0
    uretilen = sorted(p.name for p in tmp_path.glob("*.csv"))
    assert len(uretilen) == 14
    for ad in uretilen:
        assert (tmp_path / ad).read_bytes() == (M63 / ad).read_bytes(), ad


def test_63m2_sayilar():
    ozet = {y.stem: mrd.ozet(mrd.oku(y)) for y in M63.glob("*.csv")}
    assert sum(o["cubuk"] for o in ozet.values()) == 7 * 33 + 2 * 21 + 4 * 11 + 11
    assert ozet["MK01"]["cubuk"] == 33 and ozet["MK07"]["cubuk"] == 21
    assert ozet["MK12"]["cubuk"] == 11 and ozet["MK09"]["cubuk"] == 11


def test_63m2_girdisi_motorun_catisiyla_ayni():
    """Makas sayısı ve boyları Motor'un çatı tanımından (D-28: sayı tek kaynaktan)."""
    import json

    from motor import geometry as G
    from motor import ifc_uret, sunum

    ie = json.loads((KOK / "testler/teklif_formu/TK11/is_emri.json").read_text(encoding="utf-8"))
    ie = ie.get("is_emri", ie)
    T = sunum.cati_tanimi(G.kur(ie), ie)
    s = float(T["sacak"])
    girdi = json.loads((M63 / "girdi.json").read_text(encoding="utf-8"))
    tur = {}
    for m in girdi["makaslar"]:
        tur.setdefault(m["tur"], []).append(m)
    for parca in T["parcalar"]:
        ad = "ana" if parca["rol"] == "ana" else "cumba"
        # cumbada Motor'un 1 makasına paftadaki MK13 eklenir (Lokman 26 Kasım 05:52:33 UTC "cumbada 2 makas")
        assert len(tur[ad]) == len(parca["makaslar"]) + (1 if ad == "cumba" else 0)
        assert all(abs(m["alt_baslik_mm"] - (parca["aciklik_cm"] + 2 * s) * 10) < 0.1 for m in tur[ad])
    kirma = [m for m in T["mahal_catilari"] if m["tip"] == "kirma"][0]
    mk = ifc_uret._kirma_mahal_makaslari(kirma, T)
    kisa = [q for q in mk if q["rol"] == "kisa"]
    assert len(tur["kisa"]) == len(kisa)
    for q in kisa:
        assert all(abs(m["alt_baslik_mm"] - math.dist(*q["ust"]) * 10) < 0.1 for m in tur["kisa"])
    (q,) = [q for q in mk if q["rol"] == "capraz"]
    (c,) = tur["capraz"]
    assert abs(c["alt_baslik_mm"] - math.dist(*q["ust"]) * 10) < 0.1
    assert abs(c["sacak_mm"] - math.dist(q["ust"][0], q["alt"][0]) * 10) < 0.1
