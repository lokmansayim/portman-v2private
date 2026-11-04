"""İE-29 PR-2 · Kör kalan evlerin çizimi: tek uçlu kırma (AP-27) ve dış kapının duvar ucu.

AP-27'nin İş Emri'si `testler/kor/projeler/AP27/is_emri.json` (montaj paftasından; kişi ve bayi adı yok). Sayılar paftadan: makas ve panel
yerleşim planında kırma çizgileri 45° ve tepe sağ duvardan ~500 (eşit eğim), çatı kaplaması planında üç yüzün eğik boyu aynı (562,91),
kırma yüzünün tabanı 1060; yan kesitte tepe 184,26 (10 topuk + 530 × 0,3288). Holün dış kapısı sağ duvarda iki T kavşağının arasındaki
125,5'lik panoda (paftada 430,1–555,7). LLM yok.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP  # noqa: E402
from motor import geometry as G  # noqa: E402

AP27 = KOK / "testler" / "kor" / "projeler" / "AP27" / "is_emri.json"


def _ie() -> dict:
    return json.loads(AP27.read_text(encoding="utf-8"))


def _cati(ie: dict) -> dict:
    return CP.cati(G.kur(copy.deepcopy(ie)), copy.deepcopy(ie))


def test_tek_uclu_kirma_ap27():
    t = _cati(_ie())
    assert t["tip"] == "kirma" and t["tip_adi"] == "kırma"
    d = {x["ad"]: x for x in t["duzlemler"]}
    assert sorted(d) == ["doğu", "güney", "kuzey"]
    assert d["güney"]["plan"] == [[-30.0, -30.0], [803.0, -30.0], [273.0, 500.0], [-30.0, 500.0]]     # mahya 273'e kadar (803 − 530)
    assert d["doğu"]["plan"] == [[803.0, -30.0], [803.0, 1030.0], [273.0, 500.0]]                      # kırma yüzü, taban 1060
    assert {x["egim"] for x in t["duzlemler"]} == {0.3288}                                             # eşit eğim
    assert [(k["ad"], k["konum"], k["aralik"]) for k in t["kalkanlar"]] == [("batı kalkanı", 0.0, [0.0, 1000.0])]
    g = d["güney"]
    assert round(t["topuk"] + (g["plan"][2][1] - g["plan"][0][1]) * g["egim"], 2) == 184.26          # paftanın yan kesitindeki tepe


def test_tek_uclu_kirma_ayna_ve_devrik():
    ie = _ie()
    ie["cati"]["kalkan_ucu"] = "sag"
    t = _cati(ie)
    assert [k["ad"] for k in t["kalkanlar"]] == ["doğu kalkanı"] and "batı" in {x["ad"] for x in t["duzlemler"]}
    ie = _ie()                                                       # mahya y boyunca: kalkan önde ya da arkada
    ie["cati"]["makas_ekseni"] = "x"
    ie["cati"]["kalkan_ucu"] = "on"
    t = _cati(ie)
    assert [k["eksen"] for k in t["kalkanlar"]] == ["y"] and t["kalkanlar"][0]["konum"] == 0.0
    assert len(t["duzlemler"]) == 3


@pytest.mark.parametrize("degis, mesaj", [
    (lambda c: c.update(kalkan_ucu="on"), "sol ya da sag"),
    (lambda c: c.update(kirma_egimleri={"sol": 30, "sag": 35}), "kirma_egimleri"),
    (lambda c: c.update(egim_yuzde=80), "aralık dışı"),
])
def test_tek_uclu_kirma_hatalari(degis, mesaj):
    ie = _ie()
    degis(ie["cati"])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        _cati(ie)


def test_dis_kapi_duvar_ucu():
    plan = G.kur(_ie())
    d = next(d for d in plan.duvarlar if d.yon == "y" and d.tur == "dis" and d.c > 700)
    kapi = [p for p in d.panolar if p.acilim and p.acilim.tur == "dis_kapi"]
    assert [(round(p.a0, 2), round(p.a1, 2)) for p in kapi] == [(430.25, 555.75)]                  # paftada 430,1–555,7
    assert [round(p.boy, 2) for p in d.panolar if 367 < p.a0 < 600] == [62.75, 125.5, 62.75]


def test_dis_kapi_duvar_ucu_cephesiz_hata():
    ie = _ie()
    k = next(a for a in ie["acikliklar"] if a["tur"] == "dis_kapi")
    k.pop("duvar")
    with pytest.raises(G.IsEmriHatasi, match="cephesi yazılmış dış kapıda"):
        G.kur(ie)


# ───────────────────────────── AP-12: yarım duvarlı veranda, beşik + yan yana iki cumba (İE-29 PR-2) ──
# AP-12'nin İş Emri'si `testler/kor/projeler/AP12/is_emri.json` (montaj paftasından). Paftanın montaj planında verandanın önü "Yarım Duvar
# h:80" (panolar 10–507, köşelerde K ve L kaynaklı profilleri), sol duvarı 1588,25; çatı: ana beşik salonun ön duvarında kalkanlı, önünde yan
# yana iki küçük beşik (aşık planı: ana yüzler kalkanın önüne uzar, sol cumbanın iç yüzü 228,5, sağınki 278 ve 80,2'lik basamak).

AP12 = KOK / "testler" / "kor" / "projeler" / "AP12" / "is_emri.json"


def _ie12() -> dict:
    return json.loads(AP12.read_text(encoding="utf-8"))


def test_ap12_yarim_duvar():
    plan = G.kur(_ie12())
    y = [d for d in plan.duvarlar if d.yukseklik is not None]
    assert len(y) == 1 and y[0].yon == "x" and y[0].tur == "dis" and y[0].yukseklik == 80.0
    assert sorted({round(v, 2) for p in y[0].panolar for v in (p.a0, p.a1)}) == [10.0, 135.5, 261.0, 386.5, 507.0]   # paftada 10–507
    assert (y[0].p0, y[0].p1) == (10.0, 507.0) and not any("uzun özel pano" in u for u in plan.uyarilar)
    kose = sorted(tuple(round(v, 2) for v in k.rect) for k in plan.koseler if abs(k.rect[1] - 53.25) < 1e-6)
    assert kose == [(0.0, 53.25, 10.0, 63.25), (507.0, 53.25, 517.0, 63.25)]                    # K ve L: tam kare
    sol = next(d for d in plan.duvarlar if d.yon == "y" and d.tur == "dis" and d.c < 10)
    assert sol.p0 == 63.25 and plan.H - 53.25 == 1588.25          # sol duvar yarım duvarın iç yüzünde biter; sol yan 1588,25 (paftadaki gibi)
    assert G.disari_yon(plan, y[0]) == "-y"


def test_ap12_yan_yana_cumbalar():
    from motor import cati_serit as CS
    from motor.genel import cati_genel
    ie = _ie12()
    t = CS.tanim(G.kur(copy.deepcopy(ie)), ie)
    d = {x["ad"]: x for x in t["duzlemler"]}
    assert sorted(d) == ["ana çatı sağ", "ana çatı sol", "ön sağ cumba sol", "ön sol cumba sağ"]
    assert d["ana çatı sol"]["birlesen"] == ["ana çatı sol", "ön sol cumba sol"]                  # dış yüzler ana çatının devamı
    assert d["ana çatı sağ"]["birlesen"] == ["ana çatı sağ", "ön sağ cumba sağ"]
    assert d["ön sol cumba sağ"]["plan"] == [[258.5, 251.0], [512.0, 251.0], [512.0, 23.25], [258.5, 23.25]]   # 228,5 (aşık planı)
    assert d["ön sağ cumba sol"]["plan"] == [[477.0, 53.25], [512.0, 53.25], [512.0, 251.0], [697.75, 251.0], [697.75, -30.0],
                                            [477.0, -30.0]]                                       # 278 ve 80,25'lik basamak
    assert [(q["ad"], q["b"]) for q in t["parcalar"]] == [("ön sol cumba", [0.0, 517.0]), ("ön sağ cumba", [507.0, 888.5]),
                                                          ("ana çatı", [0.0, 888.5])]           # ikisi de bölme duvarını örter
    k = {x["ad"]: x for x in t["kalkanlar"]}
    assert k["ana çatı ön kalkanı"]["konum"] == 251.0 and k["ana çatı ön kalkanı"]["alt"] == ["ön sağ cumba sol", "ön sol cumba sağ"]
    ck = cati_genel.cati_kur(t)
    vadi = sorted((round(e["p"][1], 2), round(e["q"][1], 2)) for e in ck["kenarlar"] if e["tur"] == "vadi")
    assert vadi == [(23.25, 53.25), (53.25, 251.0)] and all(e["p"][0] == 512.0 for e in ck["kenarlar"] if e["tur"] == "vadi")
    kk = {x["ad"]: x for x in ck["kalkanlar"]}
    assert round(kk["ön sol cumba ön kalkanı"]["tepe"]) == 385 and round(kk["ön sağ cumba ön kalkanı"]["tepe"], 1) == 362.6
    assert round(kk["ana çatı ön kalkanı"]["tepe"], 1) == 445.9 and kk["ana çatı ön kalkanı"]["alan_m2"] < 3.2   # yalnız iki cumbanın üstü


def test_ap12_gorunusler():
    from motor import cephe_gorunus as CGo
    plan = G.kur(_ie12())
    on = CGo.cephe(plan, "on")
    assert on["yarim"] == [{"u0": 10.0, "u1": 507.0, "z1": 80.0, "derz": [135.5, 261.0, 386.5]}]
    assert [(a["tur"], a.get("olcu")) for a in on["acikliklar"]] == [("pencere", "160x180"), ("dis_kapi", None), ("pencere", "160x180")]
    assert not any(10 < u < 507 and u in (135.5, 261.0) for u in on["derz"])                       # yarım duvarın derzi tam boy değil
    sag = CGo.cephe(plan, "sag")                                                                  # açık verandanın ardındaki duvar ve kapısı
    assert ("dis_kapi", 148.25) in [(a["tur"], round(a["u0"], 2)) for a in sag["acikliklar"]]
    assert 130.5 in sag["derz"] and 376.5 not in sag["derz"] and 386.5 not in sag["derz"]         # salonun ardında kalan kısım çizilmez


@pytest.mark.parametrize("degis, mesaj", [
    (lambda ie: ie["duvarli_sinirlar"][1].update(yukseklik_cm=280), "bina yüksekliğinden alçak"),
    (lambda ie: ie["duvarli_sinirlar"][1].pop("parca_cm"), "parca_cm ile yazılır"),
])
def test_ap12_yarim_duvar_hatalari(degis, mesaj):
    ie = _ie12()
    degis(ie)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(ie)


@pytest.mark.parametrize("degis, mesaj", [
    (lambda c: c["yan_yana_cumbalar"].update(cephe="sol"), "ana çatının bir ucunda"),
    (lambda c: c["yan_yana_cumbalar"].update(bolme_cm=600), "bölme ekseninde"),
    (lambda c: c["yan_yana_cumbalar"].update(kalkan_mahali="VERANDA"), "kapalı bir mahal"),
    (lambda c: c["yan_yana_cumbalar"].update(fazla=1), "yok sayılmaz"),
])
def test_ap12_yan_yana_hatalari(degis, mesaj):
    from motor import cati_serit as CS
    ie = _ie12()
    degis(ie["cati"])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        CS.tanim(G.kur(copy.deepcopy(ie)), ie)
