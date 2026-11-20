"""80 m² (PA-48, HD-420) montaj rehberi: dikdörtgen gövdede mahya uzun kenar boyunca (makas ekseni y) ve sundurma paneli (teras panelli
veranda; D-52, D-133). Lokman, 20 Kasım 2026 14:50:44 kart "Evin tam 3B montaj rehberi". Ana çatı girintili gövdenin yolundan, tek şeritli
çatı tanımıyla (`cati_serit.tanim`; çizim, liste ve kart modeliyle aynı makas yerleri); sundurmanın kolon, kiriş ve kotları Motor'un planından,
sac, damlalık, saçak sacı ve kapama adetleri listeden. Öteki evlerin rehberi değişmez (`test_rehber.py`, `test_ie24_rehber.py`, ...)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
IE = KOK / "testler" / "havuz" / "is_emirleri" / "HD420.json"


@pytest.fixture(scope="module")
def pa48(tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = json.loads(IE.read_text(encoding="utf-8"))
    kart = tmp_path_factory.mktemp("pa48_rehber")
    kart_model.uret(copy.deepcopy(ie), kart, "PA48")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return veri.kur(copy.deepcopy(ie), kart, "PA48", L, "PA-48"), L


def _adet(L, on):
    return sum(s["adet"] or 0 for s in L if s["kalem"].startswith(on))


def test_adimlar(pa48):
    d, _ = pa48
    ad = [a.get("ad") for a in d["adimlar"]]
    assert d["N"] == 20 and len(ad) == 21
    assert ad[ad.index("Alın sacları") + 1] == "Sundurma paneli" and ad[-1] == "Kapı ve pencereler"
    assert "Veranda" in ad and "Ana çatı makasları" in ad
    assert d["kabuk"]["spec"][0] == "1014 × 647,5 cm" and d["kabuk"]["spec"][3].startswith("beşik %33") and d["kabuk"]["spec"][5] == "veranda · sundurma paneli"
    assert d["S"]["sundurma"] in d["cati_adim"]
    metin = " ".join(a.get("p", "") for a in d["adimlar"])
    assert "girintili" not in metin and "cumba" not in metin


def test_ana_cati_makaslari(pa48):
    """9 makas (2 baş, 7 orta), mahya uzun kenar boyunca: makaslar x hatlarında, açıklık kısa kenar + 2 saçak."""
    d, L = pa48
    m = d["makas"]
    assert len(m) == 9 == _adet(L, "Makas (")
    assert sum(x["rol"] == "bas" for x in m) == 2 and all(x["aile"] == "ana" for x in m)
    assert d["R"]["AN"]["R"] - d["R"]["AN"]["L"] == pytest.approx(647.5 + 60, abs=0.6)


def test_sundurma_motorun_kotlarinda(pa48):
    d, L = pa48
    (su,) = d["sundurma"]
    assert (su["x0"], su["x1"], su["yw"], su["yo"], su["out"]) == (0, 641, 0, -224, -1)
    assert (su["ust"], su["alt_uc"], su["kal"], su["egim"]) == (230, 218.8, 8, 0.05)
    v = d["verandalar"][-1]
    assert len(v["kolon"]) == 3 == _adet(L, "Özel kutu profil (kolon)") and all(k["h1"] == 200.8 for k in v["kolon"])
    assert len(v["kiris"]) == 2 == _adet(L, "Kutu profil (kiriş)")
    assert [k["rect"][2] - k["rect"][0] for k in v["kiris"]] == [320.5, 320.5] and all((k["h0"], k["h1"]) == (200.8, 210.8) for k in v["kiris"])


def test_sundurma_adetleri_listeden(pa48):
    d, L = pa48
    (su,) = d["sundurma"]
    assert len(su["sac"]) == _adet(L, "Trapez sac · veranda çatısı") == 7 and su["sac"][-1] == [600, 641]
    assert len(su["damla"]) == _adet(L, "Damlalık") == 3 and su["damla"][-1][1] == 641
    assert len(su["sacak"]) == _adet(L, "Özel büküm saçak sacı") == 3 and su["sacak"][-1][1] == 641
    assert "Silikonize mastik" in su["liste"]["mastik"]
