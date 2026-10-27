"""İE-17 · Dört cephe görünüşünün geometrisi (`motor/cephe_gorunus.py`); çizimi canlı ön onay PDF'inin görünüşü (`dxf_out.ciz_gorunusler`).

Her cephede pencere ve kapı sayısı pano Motor'unun planıyla aynı, yerleri panonun ortasında (D-15: yer Motor'un), kotları BK-13'le
(üst 200, eşik 200 − boy, kapı 0'dan); cephenin eni dış ölçü. Çatı çizgileri `cati_prefabrik`'in düzlemlerinden: saçak uçları arası dış ölçü
+ iki saçak, saçak kotu duvar üstü + topuk, tepe canlı çatı profilinin kuralıyla (topuk + (makasın geçtiği boy / 2 + saçak) × eğim; profil
de aynı sayıyı yazar), cumbanın alnı ve kırmanın uç yüzleri yerinde. Bu bir çizim kilididir; paftaya uygunluk yan yana kıyasla
(İE-17 › Kanıt).
"""
from __future__ import annotations
import collections
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP, cephe_gorunus as CG, geometry as G  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
VERI = KOK / "testler" / "motor" / "veri"
CEPHE = {"-y": "on", "+y": "arka", "-x": "sol", "+x": "sag"}


def _ie(ad: str) -> dict:
    return json.loads(((VERI if ad in ("PK01", "TK01") else EVLER) / f"{ad}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=["PK01", "AP13", "AP16", "AP01"])
def ev(request):
    ie = _ie(request.param)
    return request.param, ie, G.kur(copy.deepcopy(ie))


@pytest.fixture(scope="module", params=["AP13", "AP16", "AP01"])
def cati_ev(request):
    ie = _ie(request.param)
    plan = G.kur(copy.deepcopy(ie))
    return request.param, ie, plan, {t: CG.cati_cizgileri(plan, ie, t) for t in CG.TARAFLAR}


def _kapi_cephesi(plan: G.Plan, d, a) -> str:
    """Dış kapının cephesi: duvarın açık mahal (veranda) ya da dışarı tarafı."""
    dis = plan.mahaller.get(a.arasi[0])
    m = dis.poly.centroid if dis is not None else None
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    if d.yon == "x":
        alt = (m.y < d.c) if m is not None else abs(d.c - y0) < abs(d.c - y1)
        return "on" if alt else "arka"
    sol = (m.x < d.c) if m is not None else abs(d.c - x0) < abs(d.c - x1)
    return "sol" if sol else "sag"


def _plan_acikliklari(plan: G.Plan) -> dict:
    """Dış duvarlardaki pencere ve dış kapılar, cephe başına: (tür, boşluğun ortası görünüşün yatayında, en, pencerenin boyu)."""
    out = collections.defaultdict(list)
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if d.tur == "dis" and a and a.tur in ("pencere", "dis_kapi"):
                cephe = CEPHE[a.disari_normal] if a.tur == "pencere" else _kapi_cephesi(plan, d, a)
                u, _, _ = CG.eksen(plan, cephe)
                m = (p.a0 + p.a1) / 2 + a.kayma
                out[cephe].append((a.tur, round(u(m, 0.0) if d.yon == "x" else u(0.0, m), 2), round(a.genislik, 2),
                                   round(a.yukseklik, 2) if a.tur == "pencere" else None))
    return {k: sorted(v, key=lambda t: t[1]) for k, v in out.items()}


def test_cephe_basina_aciklik_planla_ayni(ev):
    # sayı, yer (D-15), en ve pencerenin boyu planın açıklığıyla aynı; cephe dışarı yönden (pencere `disari_normal`, kapı açık mahalden)
    ad, ie, plan = ev
    gorunus = {t: [(a["tur"], round((a["u0"] + a["u1"]) / 2, 2), round(a["u1"] - a["u0"], 2),
                    round(a["z1"] - a["z0"], 2) if a["tur"] == "pencere" else None) for a in CG.cephe(plan, t)["acikliklar"]]
               for t in CG.TARAFLAR}
    assert {k: v for k, v in gorunus.items() if v} == _plan_acikliklari(plan), ad


def test_aciklik_kotlari(ev):
    # BK-13: pencere ve kapının üst kotu 200, eşik 200 − boy (250'lik duvarda lento 50); kapı zeminden
    ad, ie, plan = ev
    for t in CG.TARAFLAR:
        for a in CG.cephe(plan, t)["acikliklar"]:
            assert a["z1"] == pytest.approx(200.0), (ad, t, a)
            if a["tur"] == "dis_kapi":
                assert a["z0"] == 0.0, (ad, t, a)


def test_cephe_eni_dis_olcu(ev):
    ad, ie, plan = ev
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    for t, boy in (("on", x1 - x0), ("arka", x1 - x0), ("sol", y1 - y0), ("sag", y1 - y0)):
        g = CG.cephe(plan, t)
        assert g["en"] == pytest.approx(boy), (ad, t)
        assert all(0 < u < boy for u in g["derz"]) and g["derz"] == sorted(set(g["derz"])), (ad, t)
        assert all(0 <= a["u0"] < a["u1"] <= boy for a in g["acikliklar"]), (ad, t)


def test_cati_sacak_ve_tepe(cati_ev):
    # saçak uçları arası dış ölçü + iki saçak; saçak kotu duvar üstü + topuk; tepe canlı profilin kuralıyla, dört görünüşte aynı
    ad, ie, plan, r = cati_ev
    c = ie["cati"]
    hy, sacak, topuk, e = 250.0, float(c["sacak_cm"]), float(c["topuk_cm"]), float(c["egim_yuzde"]) / 100
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    makas = (x1 - x0) if c.get("makas_ekseni", "x") == "x" else (y1 - y0)
    tepe = hy + topuk + (makas / 2 + sacak) * e
    for t in CG.TARAFLAR:
        en = CG.cephe(plan, t)["en"]
        assert (r[t]["u0"], r[t]["u1"]) == (pytest.approx(-sacak), pytest.approx(en + sacak)), (ad, t)
        assert r[t]["sacak_kotu"] == pytest.approx(hy + topuk), (ad, t)
        assert r[t]["tepe"][1] == pytest.approx(tepe, abs=0.01), (ad, t)


def test_besik_cumba_on_gorunusu(cati_ev):
    # AP-13 ve AP-16: ön cephede 0–391,5 cumba; alnın tepesi cumbanın ortasında, topuk + (391,5 / 2 + saçak) × eğim; iki kenarı ana eğimle
    # yandan; arka görünüşte yalnız ana çatının arka yüzü (eğim yazısı yok); yan görünüşlerde ana kalkanın üçgeni, eğim iki yanda
    ad, ie, plan, r = cati_ev
    if ie["cati"]["tip"] != "besik_cumba":
        pytest.skip("kırma")
    e = float(ie["cati"]["egim_yuzde"]) / 100
    apex = (195.75, 260.0 + (391.5 / 2 + 30.0) * e)
    noktalar = {p for c in r["on"]["cizgiler"] for p in c}
    assert any(abs(u - apex[0]) < 0.01 and abs(z - apex[1]) < 0.01 for u, z in noktalar), ad
    assert [round(x[2], 4) for x in r["on"]["egimler"]] == [round(e, 4)] * 2 and all(x[0] < 391.5 for x in r["on"]["egimler"])
    assert r["arka"]["egimler"] == [] and len(r["arka"]["cizgiler"]) == 1
    for t in ("sol", "sag"):
        assert [round(x[2], 4) for x in r[t]["egimler"]] == [round(e, 4)] * 2, (ad, t)
        assert r[t]["tepe"][0] == pytest.approx(CG.cephe(plan, t)["en"] / 2), (ad, t)


def test_kirma_uc_yuzleri(cati_ev):
    # AP-01: mahya x boyunca 508,15–946,85 (uç yüzler farklı eğimli: sol %32,5, sağ %36,2); önden ve arkadan yamuk, uç yüzlerin eğimi
    # yandan görülür ve yazılır (arkadan sağ uç solda); yanlardan üçgen, eğim ana %33
    ad, ie, plan, r = cati_ev
    if ie["cati"]["tip"] != "kirma":
        pytest.skip("beşik + cumba")
    yamuk = r["on"]["cizgiler"][0]
    ust = sorted(u for u, z in yamuk if abs(z - 434.9) < 0.01)
    assert ust == [pytest.approx(508.15, abs=0.01), pytest.approx(946.85, abs=0.01)]
    assert [x[2] for x in r["on"]["egimler"]] == [pytest.approx(0.325), pytest.approx(0.362)]
    assert [x[2] for x in r["arka"]["egimler"]] == [pytest.approx(0.362), pytest.approx(0.325)]
    for t in ("sol", "sag"):
        assert [x[2] for x in r[t]["egimler"]] == [pytest.approx(0.33)] * 2, t
        assert r[t]["tepe"] == (pytest.approx(500.0), pytest.approx(434.9, abs=0.01)), t


def test_mahya_boylari(cati_ev):
    # profilin alt yazısı bunu yazar: beşik + cumbada ana mahya gövde boyu + iki alın saçağı, cumbanınki saçağından ana çatının yüzüne
    # (genişliğin yarısı + saçak); kırmada kırma uçları arası (gövde boyu değil)
    ad, ie, plan, r = cati_ev
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    if ie["cati"]["tip"] == "kirma":
        assert CG.mahya_boylari(plan, ie) == [pytest.approx(946.85 - 508.15, abs=0.01)]
    else:
        assert CG.mahya_boylari(plan, ie) == [pytest.approx(x1 - x0 + 60), pytest.approx(391.5 / 2 + 30)]


def test_besik_ve_tasan_veranda_burada_cizilmez():
    # beşik bugünkü ön görünüşüyle çizilir (`dxf_out.ciz_on_gorunus`, bayt bayt aynı); beşik dışı çatıyla taşan veranda PR-2'de
    ie = _ie("PK01")
    with pytest.raises(CP.PrefabrikCatiHatasi, match="besik"):
        CG.cati_cizgileri(G.kur(copy.deepcopy(ie)), ie, "on")
    ie = _ie("TK01")
    plan = G.kur(copy.deepcopy(ie))
    assert plan.dis_verandalar
    ie["cati"] = copy.deepcopy(_ie("AP01")["cati"])
    with pytest.raises(CP.PrefabrikCatiHatasi, match="taşan veranda"):
        CG.cati_cizgileri(plan, ie, "on")
