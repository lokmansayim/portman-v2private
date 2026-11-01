"""İE-24 · TK-03 yükleme listesi (A4): girintili gövdenin brütü ve çatısı. Liste çizimdeki çatıdan (`cati_serit`) sayılır: ana çatı + iki
paralel cumba (Lokman, 30 Ekim 2026 13:49: "en uzun makasları ana makas kabul et ve diğer makasları cumba makası kabul et"); saçak ve alın
kenarları çatının kendi kenarlarından, aşık ve kaplama kitabın çok düzlemli çatı kuralıyla (`cok_duzlemli_cati`) yüz yüz. Paftadan sayılanlar
`veri/TK03_pafta.json` › `cati` › `liste`; bilinen farklar orada."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ie():
    return _oku(VERI / "TK03.json")


@pytest.fixture(scope="module")
def pafta():
    return _oku(VERI / "TK03_pafta.json")


@pytest.fixture(scope="module")
def L(ie):
    return PL.is_emrinden(copy.deepcopy(ie))


def _satir(L, kalem):
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, [x["kalem"] for x in L["satirlar"] if x["grup"] in ("1005", "1006")])
    return s[0]


def test_brut_ve_cati_parcalari(ie, pafta):
    """Brüt gövdenin dış çizgisinin alanı (paftanın toplamı 87,72; dış kutu 108 değil). Çatı: ana çatı ilk, sonra iki cumba; makas adedi ve
    baş makas sayısı çizimdeki çatının makas yerlerinden; mahya boyları çatı planındakiler."""
    N = PL.model_motor(copy.deepcopy(ie))
    assert abs(N["brut_m2"] - pafta["toplam_alan_m2"]) < 0.01
    assert [(c["ad"], c["kalkan"], c["makas_adet"], c["cumba"], c["mahya_boy_cm"]) for c in N["cati"]] == [
        ("ana çatı", 2, 3, False, 302.1), ("sol cumba", 1, 5, True, 543.5), ("sağ cumba", 1, 4, True, 451.1)]
    assert [round(c["aciklik_cm"] + 2 * c["sacak_cm"], 1) for c in N["cati"]] == [pafta["cati"]["makas_profilleri"][c["ad"]]["taban"] for c in N["cati"]]
    assert all(not c["capraz"] for c in N["cati"])                                     # cumba ana çatıya paralel: dere içi yok


def test_makaslar_paftayla_ayni(L, pafta):
    """12 makas: ana çatıda 2 baş + 1 orta, sol cumbada 5, sağ cumbada 4 cumba makası (paftanın MKS01–MKS12'si); boyları saçaklı açıklık."""
    pf = pafta["cati"]["makaslar_x"]
    assert _satir(L, "Makas (baş) · ana çatı")["adet"] == 2 and _satir(L, "Makas (orta) · ana çatı")["adet"] == 1
    for ad in ("sol cumba", "sağ cumba"):
        s = _satir(L, f"Cumba makası · {ad}")
        assert s["adet"] == len(pf[ad]) and s["olcu"] == f"L {round(pafta['cati']['makas_profilleri'][ad]['taban'] * 10)}"
    assert sum(len(v) for v in pf.values()) == 12 and L["girdi_ozeti"]["makas"] == 12
    assert not any(x["kalem"].startswith(("Yavru makas", "Ters mahya")) for x in L["satirlar"])


def test_sacak_ve_alin_cizimdeki_catidan(ie, L, pafta):
    """Saçak: paftanın aşık planındaki dört saçak hattı (aynı düzlemdeki ana çatı + cumba tek hat). Alın: sekiz görünen kenar; cumbanın iç ucu
    ana çatının kalkan saçağının altında sayılmaz, ana çatının cumba üstündeki kısa alın kenarı sayılır. Z kenar başına."""
    N = PL.model_motor(copy.deepcopy(ie))
    sacak = sorted(h for c in N["cati"] for h in c["sacak_hatlari_m"])
    assert sacak == sorted(round((b - a) / 100, 3) for a, b in pafta["cati"]["sacak_hatlari"].values())
    alin = {c["ad"]: sorted(c["alin_kenarlari_m"]) for c in N["cati"]}
    assert alin == {"ana çatı": [0.895, 1.221, 4.912, 4.912], "sol cumba": [3.691, 3.691], "sağ cumba": [4.018, 4.018]}
    assert "26,53 m" in _satir(L, "100'lük saçak omegası")["formul"] and "27,36 m" in _satir(L, "Alın sacı (30'luk)")["formul"]
    assert _satir(L, "Baş makas Z'si")["adet"] == 14                                    # 2 × 2 + 1 + 1 (ana) + 4 × 2 (cumba)


def test_kaplama_ve_asik_yuz_yuz(L, pafta):
    """Kaplama ve aşık kitabın çok düzlemli çatı kuralıyla (aynı düzlemdeki ana çatı ve cumba tek yüz). Sol cumba paftayla aynı (11 × 375);
    toplam 28 / 27, aşık 207,1 / 213,2 m: farklar `TK03_pafta.json` › `cati` › `liste` › `fark`."""
    pf = pafta["cati"]["liste"]
    pan = {x["kalem"].split(" · ")[1]: (x["olcu"], x["adet"]) for x in L["satirlar"] if x["kalem"].startswith("Sandviç panel (")}
    assert pan == {"ana çatı": ("L 4970", 8), "sağ cumba": ("L 4070", 9), "sol cumba": ("L 3750", 11)}
    assert pan["sol cumba"][1] == pf["sandvic_panel"]["375"] and sum(n for _o, n in pan.values()) == sum(pf["sandvic_panel"].values()) + 1
    a = _satir(L, "Aşık")
    assert "207,1 m" in a["formul"] and "34 sıra" in a["formul"] and a["adet"] == 52
    assert abs(207.1 - pf["asik_m"]) / pf["asik_m"] < 0.03


def test_girintisiz_evde_cati_tanimi_yok():
    """Dikdörtgen gövdede liste eski yoldan: çatı tanımı yok, tek ana çatı dış ölçüden (TK-01 ve P6001'in listeleri `test_prefabrik_liste`
    kilitleriyle aynı)."""
    for yol in (KOK / "is_emri" / "P6001_2plus1_6x6.json", VERI / "TK02.json"):
        N = PL.model_motor(_oku(yol))
        assert "cati_tanimi" not in N and N["cati"][0]["ad"] == "ana çatı" and "makas_adet" not in N["cati"][0]
