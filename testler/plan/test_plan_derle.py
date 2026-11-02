"""İE-14 PR-1: plan şeması → Yapı Tanımı derleyicisi, çatı üreteci ve denetçi (LLM'siz).

Örnek planlar `testler/plan/ornekler/` (elle yazılmış; biri Ç8801 yerleşiminin `tanimdan` çevirisi, köşe veranda çatı altında).
Üretilen tanım genel motordan `passed` geçer ve bayiye giden çıktılarda yazı çakışması yoktur (İE-08 `test_yazi_cakismasi` düzeneği).
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin.plan_denetim import denetle, program_coz  # noqa: E402
from beyin.plan_sema import tanimdan  # noqa: E402
from motor.genel import yapi as Y  # noqa: E402
from motor.genel.plan_derle import PlanHatasi, derle  # noqa: E402

ORNEK = KOK / "testler" / "plan" / "ornekler"
SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"


def ornek(ad: str) -> dict:
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


GECERLI = "gecerli_3arti1_100"
KOSE = "kose_veranda_2arti1_88"


def test_gecerli_plan_denetimden_gecer_ve_belirlenimci():
    p = ornek(GECERLI)
    r = denetle(p, {"alan_m2": 95, "oda_programi": "3+1"})
    assert r["gecerli"], r["ihlaller"]
    assert r["ozet"]["brut_m2"] == 100.0 and r["ozet"]["yatak"] == 3
    assert derle(copy.deepcopy(p)) == derle(copy.deepcopy(p))
    t = r["tanim"]
    assert sum(a["tur"] == "pencere" for a in t["acikliklar"]) == 7
    assert sum(a["tur"] == "ic_kapi" for a in t["acikliklar"]) == 5
    assert [a for a in t["acikliklar"] if a.get("giris")][0]["tur"] == "dis_kapi"


@pytest.mark.parametrize("ad", [GECERLI, KOSE])
def test_duvarlar_ust_uste_binmez_ve_mahaller_kapali(ad):
    from shapely.geometry import box
    t = derle(ornek(ad))
    kutular = [(d["ad"], box(*d["kutu"])) for d in t["duvarlar"]]
    for i in range(len(kutular)):
        for j in range(i + 1, len(kutular)):
            assert kutular[i][1].intersection(kutular[j][1]).area < 1e-6, (kutular[i][0], kutular[j][0])
    g = Y.kur(t)
    assert {m["ad"] for m in t["mahaller"]} <= set(g["bolgeler"])


def test_kose_veranda_cati_altinda_kolonlu_ve_catisi_dikdortgenin_tamami():
    p = ornek(KOSE)
    r = denetle(p, {"alan_m2": 88, "oda_programi": "2+1"})
    assert r["gecerli"], r["ihlaller"]
    t = r["tanim"]
    kolon = [d for d in t["duvarlar"] if d["sinif"] == "kolon"]
    assert kolon and kolon[0]["kutu"][:2] == [1.25, 1.25]
    xs = [x for d in t["cati"]["duzlemler"] for x, _ in d["plan"]]
    assert min(xs) == -30 and max(xs) == p["dis_olcu"]["en"] + 30
    # Ç8801'in dış duvar düzeni: girintide yatay duvar düşeyin dış yüzünde biter, düşey duvar köşeyi örter
    dis = {d["ad"]: d["kutu"] for d in t["duvarlar"] if d["sinif"] == "dis"}
    assert dis["DG2"] == [1.25, 226.25, 631.25, 234.25] and dis["DB2"] == [631.25, 9.25, 639.25, 234.25]


def test_kapi_yaylari_cakismaz():
    from beyin.plan_denetim import kapi_yaylari
    for ad in (GECERLI, KOSE):
        y = kapi_yaylari(derle(ornek(ad)))
        assert all(y[i][1].intersection(y[j][1]).area <= 25 for i in range(len(y)) for j in range(i + 1, len(y)))


def _bozuk(ad, degis):
    p = ornek(ad)
    degis(p)
    return denetle(p, {"alan_m2": 95, "oda_programi": "3+1"})


def _mahal(p, ad):
    return next(m for m in p["mahaller"] if m["ad"] == ad)


@pytest.mark.parametrize("degis,beklenen", [
    (lambda p: _mahal(p, "Salon")["dikdortgenler"].__setitem__(0, [0, 0, 560, 440]), "boşluk"),
    (lambda p: _mahal(p, "Salon")["dikdortgenler"].__setitem__(0, [0, 0, 560, 460]), "örtüşüyor"),
    (lambda p: _mahal(p, "Salon")["dikdortgenler"].__setitem__(0, [0, 0, 562, 450]), "ızgarada"),
    (lambda p: p["mahaller"].remove(_mahal(p, "Yatak Odası 3")) or _mahal(p, "Banyo")["dikdortgenler"].__setitem__(0, [0, 450, 560, 800]),
     "yatak odası 3 olmalı"),
    (lambda p: p["dis_olcu"].__setitem__("en", 1450) or _mahal(p, "Yatak Odası 1")["dikdortgenler"].__setitem__(0, [705, 0, 1450, 400])
     or _mahal(p, "Yatak Odası 2")["dikdortgenler"].__setitem__(0, [705, 400, 1450, 800]), "brüt alan"),
    (lambda p: p["kapilar"].remove({"arasinda": ["Hol", "Banyo"]}), "Banyo: giriş kapısından"),
    (lambda p: p["pencereler"].pop(), "penceresi yok"),
    (lambda p: _mahal(p, "Hol")["dikdortgenler"].__setitem__(0, [560, 0, 680, 800]) or
     _mahal(p, "Yatak Odası 1")["dikdortgenler"].__setitem__(0, [680, 0, 1250, 400]) or
     _mahal(p, "Yatak Odası 2")["dikdortgenler"].__setitem__(0, [680, 400, 1250, 800]), "Hol dar kenarı"),
    (lambda p: p["pencereler"].append({"mahal": "Hol", "cephe": "B", "olcu": "120x120"}), "Hol batı cephesine değmiyor"),
    (lambda p: p["kapilar"].append({"arasinda": ["Yatak Odası 1", "Salon"]}), "komşu değil"),
])
def test_ihlaller_somut_gerekceyle(degis, beklenen):
    r = _bozuk(GECERLI, degis)
    assert not r["gecerli"]
    assert any(beklenen in i for i in r["ihlaller"]), r["ihlaller"]


def test_banyo_yalniz_yatak_odasindan_ulasilirsa_ihlal():
    def degis(p):
        p["kapilar"].remove({"arasinda": ["Hol", "Banyo"]})
        p["kapilar"].append({"arasinda": ["Yatak Odası 3", "Banyo"]})
    r = _bozuk(GECERLI, degis)
    assert any("yatak odasından geçmeden" in i for i in r["ihlaller"]), r["ihlaller"]


def test_pergolali_kose_veranda_14a_disi():
    p = ornek(KOSE)
    _mahal(p, "Veranda")["ortu"] = "pergola"
    with pytest.raises(PlanHatasi, match="köşe veranda çatının altında"):
        derle(p)


def test_sema_hatasi_istisna_degil_ihlal():
    r = denetle({"dis_olcu": {"en": 1000}, "mahaller": []})
    assert not r["gecerli"] and any(i.startswith("şema:") for i in r["ihlaller"])


def test_program_coz():
    assert program_coz("3+1") == (3, 1) and program_coz(" 1 + 0 ") == (1, 0) and program_coz("üç artı bir") is None


def test_bankadaki_c8201_plan_semasina_cevrilir_ve_denetimden_gecer():
    p = tanimdan(json.loads((KOK / "modeller" / "C8201.json").read_text(encoding="utf-8")))
    assert p["dis_olcu"] == {"en": 1095, "boy": 750}
    assert {m["islev"] for m in p["mahaller"]} >= {"yatak_odasi", "banyo", "hol", "salon", "veranda"}
    r = denetle(p, {"oda_programi": "2+1", "alan_m2": 82})
    assert r["gecerli"], r["ihlaller"]


@pytest.mark.parametrize("ad", [GECERLI, KOSE])
def test_genel_motor_cizer_ve_bayi_ciktilarinda_yazi_cakismaz(ad):
    import matplotlib.figure
    from matplotlib.backends.backend_pdf import PdfPages
    from motor.genel import uret, yazi_cakisma as YC
    t = derle(ornek(ad), kod="YENI")
    rap: dict[str, dict] = {}
    asil_fig, asil_pdf = matplotlib.figure.Figure.savefig, PdfPages.savefig

    def fig_savefig(self, fname, *a, **k):
        rap[Path(str(fname)).name if not hasattr(fname, "write") else "akis"] = YC.denetle(self, "x")
        return asil_fig(self, fname, *a, **k)

    def pdf_savefig(self, figure=None, **k):
        dosya = Path(str(getattr(self, "_filename", "") or "")).name      # yalnız şablon paftası "pafta_sayfa_N" (İE-23 PR-2b)
        on = "pafta_sayfa_" if not dosya or dosya.endswith("_pafta.pdf") else f"{dosya}#"
        n = sum(1 for x in rap if x.startswith(on)) + 1
        rap[f"{on}{n}"] = YC.denetle(figure, "x")
        return asil_pdf(self, figure, **k)

    matplotlib.figure.Figure.savefig, PdfPages.savefig = fig_savefig, pdf_savefig
    try:
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "tanim.json"
            yol.write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
            m = uret.uret(yol, Path(tmp) / "c", is_emri_no="PM-TEST-20261014-1", revizyon=1, set_yolu=SET, yontem="panel",
                          perspektif=False, bayi=True)
            assert m["passed"], m.get("warnings")
    finally:
        matplotlib.figure.Figure.savefig, PdfPages.savefig = asil_fig, asil_pdf
    bulgular = []
    for d in ("YENI_plan_bayi.png", "YENI_bayi_gorsel_alt.png", "pafta_sayfa_1", "pafta_sayfa_2"):
        assert d in rap, sorted(rap)
        for tur in ("cakisan", "cizgi_kapatan", "yay_kapatan", "sayfa_disi"):
            if rap[d][tur]:
                bulgular.append((d, tur, rap[d][tur]))
    assert bulgular == [], json.dumps(bulgular, ensure_ascii=False, default=str)


# ───────────────────────── geometri hakemi (14.10) bulguları ─────────────────────────
def test_yakin_paralel_sinir_ust_uste_duvar_ve_kisa_parca_reddedilir():
    # geometri hakeminin örneği (14.10): 5 cm'lik mahal kolu çift duvar üretiyordu; denetim ve genel motor "geçti" diyordu
    r = denetle(ornek("hakem_ust_uste_duvar"))
    assert not r["gecerli"] and any("üst üste biniyor" in i for i in r["ihlaller"]) and any("15 cm ve daha kısa" in i for i in r["ihlaller"])


def test_kirmada_mahya_kisa_kenarda_reddedilir():
    p = ornek(GECERLI)
    p["cati"] = {"tip": "kirma", "mahya_yonu": "y"}
    r = denetle(p)
    assert not r["gecerli"] and any("mahya uzun kenar" in i for i in r["ihlaller"])


def test_cati_altinda_verandada_besik_reddedilir_ve_kirisler_var():
    p = ornek(KOSE)
    p["cati"] = {"tip": "besik"}
    assert any("yalnız kırma" in i for i in denetle(p)["ihlaller"])
    t = derle(ornek(KOSE))
    assert [k["ad"] for k in t["kirisler"]] == ["KRS1", "KRS2"] and all(k["alt"] == 240 and k["ust"] == 270 for k in t["kirisler"])
    assert t["kirisler"][0]["acik"] == [[1.25, 631.25]]                       # binaya değen uçta açık aralık dış duvarın karkasında biter


def test_kapi_yayi_duvara_carpan_dar_depo_reddedilir():
    p = ornek(GECERLI)
    _mahal(p, "Yatak Odası 3")["dikdortgenler"] = [[0, 450, 340, 740]]
    p["mahaller"].append({"ad": "Depo", "islev": "depo", "dikdortgenler": [[0, 740, 340, 800]]})
    p["kapilar"].append({"arasinda": ["Yatak Odası 3", "Depo"]})
    r = denetle(p)
    assert not r["gecerli"] and any("Depo" in i and ("dar kenarı" in i or "çarpıyor" in i or "yetmiyor" in i) for i in r["ihlaller"]), r["ihlaller"]


def test_l_odanin_dar_kolu_reddedilir():
    p = ornek(GECERLI)
    _mahal(p, "Salon")["dikdortgenler"] = [[0, 0, 560, 450], [0, 450, 50, 800]]   # 50 cm'lik kol (net ≈ 40)
    _mahal(p, "Yatak Odası 3")["dikdortgenler"] = [[50, 450, 340, 800]]
    next(x for x in p["pencereler"] if x["mahal"] == "Yatak Odası 3")["cephe"] = "K"
    r = denetle(p)
    assert not r["gecerli"] and any("dar kolu" in i for i in r["ihlaller"]), r["ihlaller"]


def test_egim_sinirli_ve_sessiz_degismez():
    p = ornek(GECERLI)
    p["cati"] = {"tip": "kirma", "egim_yuzde": 0}
    assert any(i.startswith("şema: cati.egim_yuzde") for i in denetle(p)["ihlaller"])
    p["cati"] = {"tip": "kirma", "egim_yuzde": 25}
    assert {d["egim"] for d in derle(p)["cati"]["duzlemler"]} == {0.25}
