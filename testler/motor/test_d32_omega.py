"""D-32 · Lokman, 29 Ekim 2026 13:12 (TK-02 montaj rehberi, 11. adım): baş makas omegası ve 100'lük iç duvarın üstü (İE-18 R1 ek 4).

- Baş makas omegası saçak ucundan saçak ucuna, baş makasın boyunca: her baş makasta açıklık + 2 × saçak. Taşan verandanın (BK-14) baş makası
  dış kirişe oturur (`kalkan_kirisli`), omegası veranda saçağından saçağına; kirişsiz açık çatı parçası sayılmaz (N1). Önceki kural (baş
  makasın altındaki duvar) aday sütununda.
- Taşan verandaya bakan gövde duvarı ana çatının kenarındadır: "100'lük duvar omegası"nın çatı kenarına gelmeyen dış duvar terimine girmez.
- Asma dizme tavanda 100'lük iç duvarın üstü ayrı satır: "60'lık iç duvar üstü omegası (sırt 10,5)", 60'lık omeganın böleniyle; ne 60'lık
  duvar omegasında ne 100'lük duvar omegasında sayılır (GB-017'nin çift sayımı kapanır). Sırt kural dosyasından (`ic_duvar_ustu_omegasi`).
  Ters tavanda 100'lük iç duvarın üstü bugünkü gibi 100'lük duvar omegasında (O5, PK-07); 60'lık iç duvarlı evde değişiklik yok.
- Yerleşim katmanı 100'lük iç duvarın eksenindeki omega parçasına sırtı yazar (`Sirt_cm`); kart OM-02 o parçayı, OM-01 ötekileri alır.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import kart_model as KM  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor.yerlesim import tavan  # noqa: E402
from motor.yerlesim.girdi import Duvar  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
YENI_SATIR = "60'lık iç duvar üstü omegası (sırt 10,5)"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


def _liste(N: dict, kurallar: dict) -> dict:
    return {s["kalem"]: s for s in PL.liste(copy.deepcopy(N), kurallar)["satirlar"]}


def _ic100(N: dict, **oz) -> dict:
    n = copy.deepcopy(N)
    n["panolar"] = [dict(p, kal_mm=100) if p["duvar"] == "ic" else p for p in n["panolar"]]
    n["ozellikler"] = {**n["ozellikler"], **oz}
    return n


@pytest.fixture(scope="module")
def pk01():
    return PL.model_motor(_oku(VERI / "PK01.json"))


@pytest.fixture(scope="module")
def tk01():
    return PL.model_motor(_oku(VERI / "TK01.json"))


def test_bas_makas_omegasi_sacaktan_sacaga(pk01, kurallar):
    """PK-01: iki baş makas, her biri açıklık + 2 × 30 cm saçak; önceki kural (duvar) aday sütununda."""
    L = _liste(pk01, kurallar)["Baş makas omegası"]
    ana = pk01["cati"][0]
    boy = 2 * (ana["aciklik_cm"] + 2 * ana["sacak_cm"]) / 100
    assert L["adet"] == math.ceil(boy / 2.5 - 1e-9) == 6
    assert L["aday"] == math.ceil(2 * ana["aciklik_cm"] / 100 / 2.5 - 1e-9) == 5
    assert "saçak ucundan saçak ucuna" in L["formul"] and "D-32" in L["dayanak"]
    assert all("kalkan" not in L[a] for a in ("formul", "kaynak", "aday_notu"))


def test_tasan_veranda_bas_makasi_kiriste(tk01, kurallar):
    """TK-01: iki taşan veranda; baş makasları dış kirişte, omegası veranda saçağından saçağına. Verandaya bakan gövde duvarı 100'lük duvar
    omegası almaz (ana çatının baş makas omegasının altında)."""
    ver = [c for c in tk01["cati"] if c.get("acik")]
    assert len(ver) == 2 and all(c["kalkan_kirisli"] and c["kalkan"] == 1 for c in ver)
    assert tk01["ic_kalan_dis_duvar_m"] == 0.0
    L = _liste(tk01, kurallar)
    ana = tk01["cati"][0]
    boy = 2 * (ana["aciklik_cm"] + 2 * ana["sacak_cm"]) + sum(c["aciklik_cm"] + 2 * c["sacak_cm"] for c in ver)
    assert L["Baş makas omegası"]["adet"] == math.ceil(boy / 100 / 2.5 - 1e-9)
    assert "taşan verandanın dış kirişindeki dahil" in L["Baş makas omegası"]["formul"]
    assert L["100'lük duvar omegası"]["adet"] == 0
    assert L["Baş makas betopanı"]["formul"].endswith("(açık çatı parçası sayılmaz, N1)")      # betopan bu işte değişmedi


def test_kirissiz_acik_parca_sayilmaz(pk01, kurallar):
    """N1: kirişsiz açık çatı parçasının (PK-06 verandası gibi) baş makası yok; omegası sayılmaz."""
    ana = pk01["cati"][0]
    acik = dict(ana, ad="veranda", acik=True, aciklik_cm=300.0, boy_cm=200.0, kalkan=1)
    a = _liste(pk01, kurallar)["Baş makas omegası"]
    b = _liste(dict(pk01, cati=pk01["cati"] + [acik]), kurallar)["Baş makas omegası"]
    c = _liste(dict(pk01, cati=pk01["cati"] + [dict(acik, kalkan_kirisli=True)]), kurallar)["Baş makas omegası"]
    assert b["adet"] == a["adet"] and "kirişsiz açık çatı parçası sayılmaz" in b["formul"]
    assert c["adet"] == math.ceil((2 * (ana["aciklik_cm"] + 60) + 360) / 100 / 2.5 - 1e-9)


def test_ic_duvar_ustu_100_asma(pk01, kurallar):
    """Asma tavan, iç duvar 100'lük: iç duvar üstleri ayrı satırda; 60'lık ve 100'lük duvar omegasından çıkar."""
    L60, L100 = _liste(pk01, kurallar), _liste(_ic100(pk01), kurallar)
    L_duvar = sum(p["boy"] for p in pk01["panolar"] if p["duvar"] == "ic") / 100
    L_hat, _n = PL.omega_hatlari(pk01["kapali"], 1.255)
    assert YENI_SATIR not in L60
    y = L100[YENI_SATIR]
    assert (y["grup"], y["olcu"], y["adet"]) == ("1002", "60 × 3750", math.ceil(L_duvar / 3.65 - 1e-9))
    assert L100["60'lık duvar omegası (asma dizme tavan)"]["adet"] == math.ceil(L_hat / 3.65 + 5 - 1e-9)
    assert "iç duvar üstleri ayrı satırda" in L100["60'lık duvar omegası (asma dizme tavan)"]["formul"]
    assert L100["100'lük duvar omegası"]["adet"] == L60["100'lük duvar omegası"]["adet"]
    assert "100'lük iç duvarlar" not in L100["100'lük duvar omegası"]["formul"]


def test_ic_duvar_ustu_100_ters_degismez(pk01, kurallar):
    """Ters tavan, iç duvar 100'lük (O5, PK-07): iç duvar üstleri 100'lük duvar omegasında; yeni satır yok."""
    L = _liste(_ic100(pk01, Tavan="Ters tavan"), kurallar)
    L_duvar = sum(p["boy"] for p in pk01["panolar"] if p["duvar"] == "ic") / 100
    assert YENI_SATIR not in L
    assert f"100'lük iç duvarlar {PL.od(L_duvar)} m" in L["100'lük duvar omegası"]["formul"]


def test_sirt_kural_dosyasindan(pk01, kurallar):
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["ic_duvar_ustu_omegasi"]["deger"]["sirt_cm"] = 11.0
    assert "60'lık iç duvar üstü omegası (sırt 11)" in _liste(_ic100(pk01), k)


def _g(tavan_turu: str, h_ic: float) -> dict:
    duvarlar = [Duvar("dis", "x", 5, 5, 0, 600), Duvar("dis", "x", 395, 5, 0, 600), Duvar("dis", "y", 5, 5, 0, 400),
                Duvar("dis", "y", 595, 5, 0, 400), Duvar("ic", "y", 300, h_ic, 10, 390)]
    return {"cati": {"makas_ekseni": "x"}, "duvarlar": duvarlar, "baslangic": {"x": "min", "y": "min"}, "tavan": tavan_turu,
            "odalar": [], "acik": [], "engeller": []}


@pytest.mark.parametrize("tavan_turu, h_ic, beklenen", [("asma", 5, [10.5]), ("asma", 3, [None]), ("ters", 5, []), ("ters", 3, [None])])
def test_yerlesim_sirti(tavan_turu, h_ic, beklenen):
    """Duvar eksenindeki hat: 100'lük iç duvarda sırt yazılır; ters tavanda 100'lük iç duvarın üstünde hat yok (O5)."""
    K = {"aralik_asma": 125.5, "aralik_ters": 60.0, "en_kisa": 10, "sirt_100": 10.5}
    h = [x for x in tavan.hatlar(_g(tavan_turu, h_ic), K) if x["yer"] == "duvar_ekseni"]
    assert [x.get("sirt") for x in h] == beklenen


def test_om02_karti():
    """Sırtı yazılı duvar ekseni parçası OM-02'ye, ötekiler OM-01'e; OM-02'nin satırı liste üretecinin yazdığı ad."""
    kartlar = KM._oku(KM.KARTLAR)
    p = lambda **b: {"kural": "tavan_omegasi_yerlesimi", "parca": "omega", "bilgi": {"Tavan": "asma", "Hat": 1, "Mahal": "", **b}}  # noqa: E731
    assert [k["kod"] for k in KM.yerlesim_kartlari(p(Yer="duvar_ekseni", Sirt_cm=10.5), kartlar)] == ["OM-02"]
    assert [k["kod"] for k in KM.yerlesim_kartlari(p(Yer="duvar_ekseni"), kartlar)] == ["OM-01"]
    assert [k["kod"] for k in KM.yerlesim_kartlari(p(Yer="ara"), kartlar)] == ["OM-01"]
    om02 = next(k for k in kartlar["kartlar"] if k["kod"] == "OM-02")
    assert om02["liste"]["satirlar"] == [YENI_SATIR] and om02["ad"].startswith(YENI_SATIR)
    assert om02["yerlesim"]["bilgi"]["Sirt_cm"] == PL.kurallari_oku()["prefabrik"]["kurallar"]["ic_duvar_ustu_omegasi"]["deger"]["sirt_cm"]
