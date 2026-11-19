"""D-126 (BK-57; Lokman 19 Kasım 2026 19:00:47, TK-08 kartı "Evet, çatı şiltesi çıksın"): İş Emri çatı izolasyonunu alıcıya ait
yazarsa (izocam, şilte, çatı izolasyonu) çatı şiltesi satırı adet 0 ve "alıcıya ait"; yazmayan İş Emri'nin listesi aynen."""
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402
IE = KOK / "testler/teklif/TK01_is_emri_r05.json"


def _silte(L):
    s = [x for x in L["satirlar"] if x["kalem"].startswith("Çatı şiltesi")]
    assert len(s) == 1
    return s[0]


@pytest.fixture(scope="module")
def ie():
    return json.loads(IE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def once(ie):
    return PL.is_emrinden(copy.deepcopy(ie))


@pytest.mark.parametrize("kalem", ["Çatı arası izocam", "ÇATI ŞİLTESİ", "Çatı izolasyonu", "çatı yalıtımı"])
def test_alici_ait_silte_sifir(ie, once, kalem):
    d = copy.deepcopy(ie)
    d["alici_ait"] = {"kalemler": [kalem], "kaynak": "test"}
    sonra = PL.is_emrinden(d)
    s = _silte(sonra)
    assert s["adet"] == 0 and s["formul"] == "alıcıya ait" and s["dayanak"] == "İş Emri"
    assert _silte(once)["adet"] > 0
    # yalnız şilte satırı değişir: satır sayısı, sıra ve öteki satırlar aynı
    assert [x["kalem"] for x in sonra["satirlar"]] == [x["kalem"] for x in once["satirlar"]]
    fark = [a["kalem"] for a, b in zip(once["satirlar"], sonra["satirlar"]) if (a["adet"], a["formul"]) != (b["adet"], b["formul"])]
    assert fark == [s["kalem"]]


@pytest.mark.parametrize("kalemler", [[], ["boya", "vitrifiye", "Su tesisatı grubu"], ["ses izolasyonu"]])
def test_anahtarsiz_aynen(ie, once, kalemler):
    d = copy.deepcopy(ie)
    d["alici_ait"] = {"kalemler": kalemler, "kaynak": "test"}
    assert _silte(PL.is_emrinden(d)) == _silte(once)


def test_silte_alici():
    assert PL.silte_alici(["çatı arası izocam"]) and PL.silte_alici(["şilte"])
    assert not PL.silte_alici(["ses izolasyonu"]) and not PL.silte_alici([])
