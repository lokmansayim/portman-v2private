"""BK-12 PR-2 · Prefabrik yükleme listesi (`motor/prefabrik_liste.py`, kurallar `kurallar/liste/prefabrik.json`).

- PK-01 (AP-19) listesinin kilidi: satır başına grup, kalem, ölçü, adet ve aday (`veri/PK01_liste_kilidi.json`). Gerçek listeyle kıyas
  değildir; hesabın değişmediğini söyler.
- Kurallar dosyadan okunur: bir değer değişince adet değişir; her kuralın değeri, durumu ve kaynağı var; çelikle ortak değerler yinelenmez.
- Orta iniş (Lokman, 13 Ekim 15:10): uzunluğa bağlı kural ile 7.3'ün "her saçak hattına bir" kuralı yer değiştirir, öteki aday sütununda.
- Pafta kipi Motor kipiyle aynı geometriden aynı adetleri verir; komut satırı JSON ve tek sayfalık Excel yazar.
"""
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
PK01 = VERI / "PK01.json"
PAFTA_KATMANI = VERI / "PK01_pafta_katmani.json"
KILIT = VERI / "PK01_liste_kilidi.json"
DURUMLAR = {"lokman", "excel", "uydurma", "varsayim", "pafta", "cizim", "aday"}   # kural kitabının değerleri + prefabrikin üçü


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def N():
    return PL.model_motor(_oku(PK01))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


@pytest.fixture(scope="module")
def pk01(N, kurallar):
    return PL.liste(copy.deepcopy(N), kurallar, _oku(PAFTA_KATMANI))


def _satir(L: dict, kalem: str) -> dict:
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, len(s))
    return s[0]


def test_pk01_kilidi(pk01):
    k = _oku(KILIT)
    assert pk01["ozet"] == k["ozet"]
    assert pk01["girdi_ozeti"] == k["girdi_ozeti"]
    assert [[s["grup"], s["kalem"], s["olcu"], s["adet"], s["aday"]] for s in pk01["satirlar"]] == k["satirlar"]


def test_pk01_motor_sayimlari(pk01):
    """Montaj paftasıyla aynı olduğu PR-1'de sınanan sayımlar listeye aynen geçer (50 pano, 38 H)."""
    g = pk01["girdi_ozeti"]
    assert (g["pano_dis"], g["pano_ic"]) == (30, 20)
    h = sum(_satir(pk01, k)["adet"] for k in ("H 100 (dış pano eki)", "H standart 60 (iç pano eki)", "3'lü H 100 × 100 × 60 (dış duvar T'si)",
                                               "3'lü H standart 60 (iç T)"))
    assert h == 38
    assert _satir(pk01, "H 100 (dış pano eki)")["pafta"] == 19      # pafta katmanı yerinde okunuyor


def test_pk01_aliciya_ait(pk01):
    """PK-01'de pencere, dış kapı, boya ve tesisat alıcıya ait: satır kalır, adet 0."""
    assert _satir(pk01, "Pencere grubu")["adet"] == 0
    dis_kapi = [s for s in pk01["satirlar"] if s["kalem"].startswith("Prefabrik çelik kapı")]
    assert len(dis_kapi) == 1 and dis_kapi[0]["adet"] == 0
    assert _satir(pk01, "Boya grubu ve mastik")["adet"] == 0
    assert _satir(pk01, "Sıhhi tesisat grubu")["adet"] == 0
    assert _satir(pk01, "Elektrik grubu")["dayanak"] == "Kural yok"     # PK-01 paftasında elektrik planı yok


def test_kurallar_dosyadan_okunur(N, kurallar):
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["kosebent"]["deger"] = 9
    k["prefabrik"]["kurallar"]["alt_cerceve_bolen_m"]["deger"] = 2.5
    L = PL.liste(copy.deepcopy(N), k)
    assert _satir(L, "Köşebent")["adet"] == 9
    assert _satir(L, "100'lük alt çerçeve")["adet"] == 13           # dış çevre 32 m ÷ 2,5 (kuralla ÷ 3,75 → 9)


def test_ortak_degerler_kural_kitabindan(N, kurallar):
    """Saçak sacı ve dere çelikle ortak `kurallar.json`'dan okunur; prefabrik dosyası onları yinelemez."""
    yinelenmez = {"parca_boyu_m", "bindirme_m", "asik", "silte_adet_m2", "sandvic_panel_kapatma_m", "trapez_sac_kapatma_m",
                  "dere_kelepcesi_dere_basina", "inis", "inis_basina"}
    assert not yinelenmez & set(kurallar["prefabrik"]["kurallar"])
    k = copy.deepcopy(kurallar)
    k["ortak"]["parca_boyu_m"]["sacak_saci"]["deger"] = 2.8
    L0, L1 = PL.liste(copy.deepcopy(N), kurallar), PL.liste(copy.deepcopy(N), k)
    assert _satir(L1, "Saçak sacı (30'luk, 3'ü menfezli)")["adet"] < _satir(L0, "Saçak sacı (30'luk, 3'ü menfezli)")["adet"]


def test_kural_dosyasi_bicimi(kurallar):
    R = kurallar["prefabrik"]
    assert R["sema"].startswith("portman.prefabrik_liste/")
    for ad, v in R["kurallar"].items():
        assert set(v) == {"deger", "durum", "kaynak"}, ad
        assert v["durum"] in DURUMLAR, (ad, v["durum"])
        assert v["kaynak"].strip(), ad
    assert R["kurallar"]["inis_orta"]["deger"] in ("esik", "her_sacak")


def test_orta_inis_uzunluga_bagli(kurallar):
    """Beşik ana çatı, saçak hatları 8 ve 10 m: eşik (9 m) yalnız 10 m'lik hatta orta iniş koyar; 7.3'ün kuralı ikisine de."""
    N = {"kaynak": "pafta", "H0": 250.0, "W": 600.0, "D": 900.0, "t_dis": 10.0, "panolar": [], "ekler": [], "koseler": {"dis": 4},
         "dikmeler": 0, "veranda_kirisleri_cm": [], "kapali": [], "acik": [], "ozellikler": {}, "alici_ait": {},
         "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 600.0, "boy_cm": 900.0, "egim_yuzde": 33.0, "sacak_cm": 30.0,
                   "sacak_hatlari_m": [8.0, 10.0]}]}
    esik = _satir(PL.liste(PL.model_pafta(copy.deepcopy(N)), kurallar), "Metal dere inişi aparatı")
    assert (esik["adet"], esik["aday"]) == (5, 6)
    assert esik["dayanak"] == "Kural (Lokman 13.10 15:10)"
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["inis_orta"]["deger"] = "her_sacak"
    her = _satir(PL.liste(PL.model_pafta(copy.deepcopy(N)), k), "Metal dere inişi aparatı")
    assert (her["adet"], her["aday"]) == (6, 5)
    L = PL.liste(PL.model_pafta(copy.deepcopy(N)), kurallar)
    assert _satir(L, "Açık dirsek")["adet"] == 2 * esik["adet"]          # iniş başına parçalar varsayılan inişe göre


def test_pafta_kipi_motor_kipiyle_ayni(N, kurallar):
    """Motor'un geometrisi `yapi_pafta` biçiminde verilince aynı adetler çıkar; değişen yalnız kaynak yazısı."""
    yp = {k: v for k, v in copy.deepcopy(N).items() if k not in ("kaynak", "veranda_kenarlari_cm")}
    yp["veranda_kirisleri_cm"] = [x - 10 for x in N["veranda_kenarlari_cm"]]
    Lm = PL.liste(copy.deepcopy(N), kurallar)
    Lp = PL.liste(PL.model_pafta(yp), kurallar)
    assert [(s["kalem"], s["olcu"], s["adet"], s["aday"]) for s in Lm["satirlar"]] == [(s["kalem"], s["olcu"], s["adet"], s["aday"]) for s in Lp["satirlar"]]
    assert Lp["girdi_ozeti"]["geometri"] == "pafta"


def test_komut_satiri(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    assert PL.main([str(PK01), str(tmp_path), "--pafta", str(PAFTA_KATMANI)]) == 0
    L = _oku(tmp_path / "PK01_liste.json")
    assert L["kod"] == "PK-01" and L["ozet"]["satir"] == len(L["satirlar"]) == 93
    assert L["kural_seti"]["prefabrik"] == "portman.prefabrik_liste/1.0"
    wb = openpyxl.load_workbook(tmp_path / "PK01_liste.xlsx")
    assert wb.sheetnames == ["Liste"] and wb["Liste"].max_row == 93 + 2
    with pytest.raises(SystemExit):
        PL.main([str(tmp_path)])                                     # ne İş Emri ne --yapi
