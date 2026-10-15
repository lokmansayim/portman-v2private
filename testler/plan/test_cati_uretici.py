"""İE-14 r2 · çatı üreticisi ayrı parça (K7): bankadaki dikdörtgen çatılar ayak izinden yeniden üretilir, elle yazılmış çatıyla kıyaslanır.

Kıyas `cati_uretici.olc` ile: düzlem sayısı, plan alanı, saçak / mahya / kırma kenarlarının plan boyu toplamı ±1 cm (alan ±1 cm × çevre);
düzlem düzlem köşeler ±1 cm (yukarı yönüyle eşlenir), eğim ve saçak kotu aynı. LLM yok.
- Ç8201: kırma, 4 düzlem. Ayak izi dış yüzlerden: dış duvarlar (kaplama 1,25 dahil) ve veranda kolonları → 0..1094 × 0..750.
- KT-02 ana gövde: kırma, 4 düzlem, eğim 0,32878. Elle yazılmış çatının saçağı karkasın dış yüzünden 30 (kaplama 3 cm dahil değil;
  projenin DWG'si) → ayak izi dış duvar ve veranda korkuluğu kutularının dış kenarı 3..767 × 3..1167. Batı düzlemindeki sundurma çentiği (iki vadi) ana gövde
  kıyasında dışbükey zarfla kapatılır; sundurma düzlemleri kıyasa girmez.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_genel, cati_uretici as CU  # noqa: E402

MODEL = KOK / "modeller"


def _zarf(plan):
    """Dışbükey zarf (Andrew), saat yönünün tersine; çentiği kapatır."""
    p = sorted({(round(x, 4), round(y, 4)) for x, y in plan})

    def cap(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    alt, ust = [], []
    for q in p:
        while len(alt) >= 2 and cap(alt[-2], alt[-1], q) <= 0:
            alt.pop()
        alt.append(q)
    for q in reversed(p):
        while len(ust) >= 2 and cap(ust[-2], ust[-1], q) <= 0:
            ust.pop()
        ust.append(q)
    return [list(v) for v in alt[:-1] + ust[:-1]]


def _dis_kutu(t, siniflar):
    ks = [d["kutu"] for d in t["duvarlar"] if d.get("sinif") in siniflar]
    return min(k[0] for k in ks), min(k[1] for k in ks), max(k[2] for k in ks), max(k[3] for k in ks)


def _c8201():
    t = json.loads((MODEL / "C8201.json").read_text(encoding="utf-8"))
    k = t["yuz_kaplamalari"]["dis"]["kalinlik"]
    dx0, dy0, _, _ = _dis_kutu(t, {"dis"})
    _, _, kx1, ky1 = _dis_kutu(t, {"kolon", "dis"})
    R = (dx0 - k, dy0 - k, kx1, ky1)                  # dış duvarın dış yüzü; doğu ve kuzey veranda kolonunun dış kenarı
    assert R == (0, 0, 1094, 750)
    return t["cati"], R, "kirma", None


def _kt02():
    t = json.loads((MODEL / "KT02.json").read_text(encoding="utf-8"))
    R = _dis_kutu(t, {"dis", "korkuluk"})               # güneyde çatı altındaki veranda: korkuluk ve kolonlar 3..240
    assert R == (3, 3, 767, 1167)
    ana = {"batı", "doğu", "güney", "kuzey"}
    cati = dict(t["cati"])
    cati["duzlemler"] = [dict(d, plan=_zarf(d["plan"])) for d in t["cati"]["duzlemler"] if d["ad"] in ana]
    cati.pop("kenar_ozel", None)
    egim = t["cati"]["duzlemler"][0]["egim"]
    return cati, R, "kirma", egim * 100


VAKALAR = {"C8201": _c8201, "KT02_ana_govde": _kt02}


@pytest.mark.parametrize("ad", sorted(VAKALAR))
def test_banka_catisi_ayak_izinden_yeniden_uretilir(ad):
    elle, R, tip, egim = VAKALAR[ad]()
    uretilen = CU.uret(R, tip, None, egim, duvar_ustu=elle.get("duvar_ustu", 270))
    a, b = CU.olc(elle), CU.olc(uretilen)
    assert a["duzlem"] == b["duzlem"] == 4
    cevre = 2 * ((R[2] - R[0]) + (R[3] - R[1]) + 4 * 30)
    assert abs(a["plan_cm2"] - b["plan_cm2"]) <= cevre * 1.0, (a, b)
    for tur in ("sacak", "mahya", "kirma"):
        assert abs(a["kenar_plan_cm"].get(tur, 0) - b["kenar_plan_cm"].get(tur, 0)) <= 1.0, (tur, a, b)
    assert set(a["kenar_plan_cm"]) == set(b["kenar_plan_cm"]), (a, b)
    eller = {tuple(d["yukari"]): d for d in elle["duzlemler"]}
    for d in uretilen["duzlemler"]:
        e = eller[tuple(d["yukari"])]
        assert abs(d["egim"] - e["egim"]) < 1e-4 and abs(d["sacak_kotu"] - e["sacak_kotu"]) < 0.01
        assert len(d["plan"]) == len(e["plan"])
        for p in d["plan"]:
            assert min(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for q in e["plan"]) <= 1.0, (ad, d["ad"], p)


@pytest.mark.parametrize("tip,mahya,R,n_duz,n_kal", [("besik", "x", (0, 0, 1200, 800), 2, 2), ("besik", "y", (0, 0, 1200, 800), 2, 2),
                                                      ("kirma", "x", (0, 0, 1200, 800), 4, 0), ("kirma", "y", (0, 0, 800, 1200), 4, 0),
                                                      ("kirma", None, (0, 0, 900, 900), 4, 0)])
def test_dikdortgeni_tam_orter_ve_cati_kurdan_gecer(tip, mahya, R, n_duz, n_kal):
    from shapely.geometry import Polygon
    c = CU.uret(R, tip, mahya, None)
    assert len(c["duzlemler"]) == n_duz and len(c["kalkanlar"]) == n_kal
    assert all(Polygon(d["plan"]).is_valid for d in c["duzlemler"])
    toplam = sum(Polygon(d["plan"]).area for d in c["duzlemler"])
    assert abs(toplam - (R[2] + 60) * (R[3] + 60)) < 1
    cati_genel.cati_kur(c)
    assert all(d["egim"] == 0.33 and d["sacak_kotu"] == 280 for d in c["duzlemler"])


def test_kare_kirma_piramittir():
    o = CU.olc(CU.uret((0, 0, 900, 900), "kirma"))
    assert o["kenar_plan_cm"].get("mahya", 0) == 0 and all(len(d["plan"]) == 3 for d in CU.uret((0, 0, 900, 900), "kirma")["duzlemler"])


@pytest.mark.parametrize("girdi,parca", [(((0, 0, 1200, 800), "kirma", "y", None), "uzun kenar"),
                                         (((0, 0, 1200, 800), "mansard", None, None), "üretilmez"),
                                         (((0, 0, 1200, 800), "besik", None, 75), "aralık dışı"),
                                         (((0, 0, 0, 800), "besik", None, None), "boş")])
def test_gecersiz_girdi_reddedilir(girdi, parca):
    with pytest.raises(CU.CatiHatasi, match=parca):
        CU.uret(*girdi)


def test_sayilar_kural_tablosundan():
    k = CU.kurallar()
    assert (k["sacak_cm"], k["topuk_cm"], k["panel_kalinligi_cm"], k["egim_varsayim"]) == (30, 10, 8, 0.33)
    assert k["tipler"] == ["besik", "kirma", "cumba", "l"]
    k2 = dict(k, sacak_cm=50, egim_varsayim=0.25)
    c = CU.uret((0, 0, 1000, 600), "besik", kural=k2)
    assert c["duzlemler"][0]["plan"][0] == [-50, -50] and c["duzlemler"][0]["egim"] == 0.25


# ── r3 · P3: tipe göre üreticiler (cumba, L) — bankadaki elle yazılmış çatıyla birebir ─────────────────────────────────────
C8801_IZ = [[0, 220, 1024, 860], [624, 0, 1024, 220]]          # ana gövde + güneydoğudaki cumba (dış yüzler; batıdaki köşe pergola veranda)
C8801L_IZ = [[0, 220, 624, 860], [624, 0, 1024, 860]]         # aynı L ayak izi: batı blok + boydan boya doğu kanadı


def _eslesme(uretilen: dict, elle: dict) -> None:
    for d in uretilen["duzlemler"]:
        aday = [x for x in elle["duzlemler"] if x["yukari"] == d["yukari"]]
        e = min(aday, key=lambda x: sum(min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in x["plan"]) for p in d["plan"]))
        assert len(d["plan"]) == len(e["plan"]) and abs(d["egim"] - e["egim"]) < 1e-4, (d["ad"], e["ad"])
        for p in d["plan"]:
            assert min(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for q in e["plan"]) <= 1.0, (d["ad"], p)
    kb = sorted((k["eksen"], k["konum"], tuple(k["aralik"]), k["ic"]) for k in elle["kalkanlar"])
    ku = sorted((k["eksen"], k["konum"], tuple(k["aralik"]), k["ic"]) for k in uretilen["kalkanlar"])
    assert len(kb) == len(ku) and all(a[0] == b[0] and a[3] == b[3] and abs(a[1] - b[1]) <= 1 and abs(a[2][0] - b[2][0]) <= 1
                                      and abs(a[2][1] - b[2][1]) <= 1 for a, b in zip(kb, ku)), (kb, ku)


def test_ayak_izleri_bankadaki_dis_duvarlarla_ayni():
    for ad in ("C8801", "C8801L"):
        t = json.loads((MODEL / f"{ad}.json").read_text(encoding="utf-8"))
        k = t["yuz_kaplamalari"]["dis"]["kalinlik"]
        x0, y0, x1, y1 = _dis_kutu(t, {"dis"})
        assert (x0 - k, y0 - k, x1 + k, y1 + k) == (0, 0, 1024, 860), ad


@pytest.mark.parametrize("ad,iz,tip", [("C8801", C8801_IZ, "cumba"), ("C8801L", C8801L_IZ, "l")])
def test_cumba_ve_l_bankadaki_catiyla_ayni(ad, iz, tip):
    elle = json.loads((MODEL / f"{ad}.json").read_text(encoding="utf-8"))["cati"]
    u = CU.uret(iz, tip)
    assert CU.olc(u) == CU.olc(elle)                                     # düzlem, kalkan, plan alanı, saçak/mahya/vadi/alın toplamları
    _eslesme(u, elle)
    assert CU.denetle(u, iz) == []
    assert u["tip"] == "besik_cumba"


def test_l_kanat_egimi_mahyalar_esit_kotta():
    u = CU.uret(C8801L_IZ, "l")
    kanat = {d["egim"] for d in u["duzlemler"] if d["ad"].startswith("kanat")}
    assert kanat == {0.50217}                                            # 0,33 × 350 / 230


@pytest.mark.parametrize("tip,iz", [("cumba", C8801_IZ), ("l", C8801L_IZ)])
@pytest.mark.parametrize("donus", ["ayna_y", "ayna_x", "devrik", "devrik_ayna"])
def test_dort_yonde_ayni_olcu_ve_ortak_denetim(tip, iz, donus):
    f = {"ayna_y": lambda r: [r[0], 860 - r[3], r[2], 860 - r[1]], "ayna_x": lambda r: [1024 - r[2], r[1], 1024 - r[0], r[3]],
         "devrik": lambda r: [r[1], r[0], r[3], r[2]], "devrik_ayna": lambda r: [r[1], 1024 - r[2], r[3], 1024 - r[0]]}[donus]
    iz2 = [f(r) for r in iz]
    u = CU.uret(iz2, tip)
    assert CU.olc(u) == CU.olc(CU.uret(iz, tip)) and CU.denetle(u, iz2) == []


def test_cumbanin_ana_kuzey_yuzu_besikle_ayni():
    besik = CU.uret((0, 220, 1024, 860), "besik")
    cumba = CU.uret(C8801_IZ, "cumba")
    assert next(d["plan"] for d in cumba["duzlemler"] if d["ad"] == "ana kuzey") == next(d["plan"] for d in besik["duzlemler"] if d["ad"] == "kuzey")


@pytest.mark.parametrize("tip,iz,parca", [("cumba", [[0, 0, 400, 300], [20, 300, 390, 700]], "çok geniş"),
                                          ("cumba", [[0, 200, 1000, 800], [1100, 0, 1300, 200]], "bitişik"),
                                          ("l", [[0, 200, 600, 800], [600, 300, 1000, 800]], "bitişik"),
                                          ("cumba", [[0, 200, 1000, 800]], "iki dikdörtgen")])
def test_cumba_ve_l_gecersiz_ayak_izi(tip, iz, parca):
    with pytest.raises(CU.CatiHatasi, match=parca):
        CU.uret(iz, tip)
