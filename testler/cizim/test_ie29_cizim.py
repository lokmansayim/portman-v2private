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
