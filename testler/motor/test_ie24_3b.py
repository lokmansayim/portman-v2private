"""İE-24 · TK-03 3B model (A4): girintili gövdenin IFC'si. Döşeme gövdenin dış çizgisinden; çatı çizimdeki ve listedeki çatının aynısından
(`cati_serit.tanim`): dört eğik yüz (aynı düzlemdeki ana çatı ve cumba yüzü tek levha), kalkan dolguları, 12 makas paftadaki yerde. Ana
çatının makasları "Çatı makası (baş/orta)", cumbanınkiler "Cumba makası" (Lokman, 30 Ekim 2026 13:49). Girintisiz evde plan aynı."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    import ifcopenshell
    yol = tmp_path_factory.mktemp("tk03") / "TK03.ifc"
    ozet = ifc_uret.uret(_oku(VERI / "TK03.json"), yol)
    return ozet, ifcopenshell.open(str(yol))


def _kutu(e):
    import ifcopenshell.geom
    st = ifcopenshell.geom.settings()
    st.set("use-world-coords", True)
    v = np.array(ifcopenshell.geom.create_shape(st, e).geometry.verts).reshape(-1, 3) * 100
    return v.min(0), v.max(0)


def _ps(e):
    import ifcopenshell.util.element as ue
    return ue.get_psets(e).get("PortatifEv_Kapsam", {})


def test_sema_ve_doseme(ifc):
    """Şema hatası yok; döşeme gövdenin dış çizgisi (87,72 m², girinti gözleri dışarıda)."""
    from shapely.geometry import Polygon
    ozet, f = ifc
    assert ozet["sema_hatasi"] == 0
    h = ifc_uret.hazirla(_oku(VERI / "TK03.json"))
    assert abs(Polygon(h["govde"]).area / 1e4 - 87.72) < 0.01
    z = next(e for e in f.by_type("IfcSlab") if e.Name == "ZEMIN_BETONU")
    alt, ust = _kutu(z)
    assert np.allclose(alt[:2], [0, 0], atol=0.1) and np.allclose(ust[:2], [1236.7, 873.3], atol=0.1)


def test_makaslar_paftadaki_yerde(ifc):
    """12 makas: ana çatıda 2 baş + 1 orta, sol cumbada 5, sağ cumbada 4; yerleri paftanın makas planıyla 1,5 cm içinde (Motor'un çerçevesinde
    x aynı); her makas kendi parçasının dış yüzünden dış yüzüne."""
    ozet, f = ifc
    pafta = _oku(VERI / "TK03_pafta.json")["cati"]["makaslar_x"]
    m = sorted((e for e in f.by_type("IfcElementAssembly") if e.Name.startswith("MAKAS_")), key=lambda e: e.Name)
    assert len(m) == ozet["cati"]["makas"] == 12
    kalem = [_ps(e)["BOMKalem"] for e in m]
    assert kalem.count("Çatı makası (baş)") == 2 and kalem.count("Çatı makası (orta)") == 1
    assert kalem.count("Cumba makası · sol cumba") == 5 and kalem.count("Cumba makası · sağ cumba") == 4
    for parca, ad in (("ana çatı", "ana çatı"), ("sol cumba", "sol cumba"), ("sağ cumba", "sağ cumba")):
        x = sorted(y["konum_cm"] for y in ozet["cati"]["makaslar"] if y["parca"] == parca)
        assert len(x) == len(pafta[ad]) and all(abs(a - b) < 1.5 for a, b in zip(x, pafta[ad])), (parca, x, pafta[ad])
    alt_baslik = {e.Name: _kutu(e) for e in f.by_type("IfcMember") if e.Name.endswith("_ALT_BASLIK")}
    acik = {"ana çatı": (0.0, 873.3), "sol cumba": (232.0, 873.3), "sağ cumba": (0.0, 703.3)}
    for e in m:
        a, b = alt_baslik[f"{e.Name}_ALT_BASLIK"]
        y0, y1 = acik[_ps(e)["CatiParcasi"]]
        assert abs(a[1] - y0) < 0.1 and abs(b[1] - y1) < 0.1 and abs(a[2] - 250) < 0.1


def test_cati_yuzleri_ve_kalkanlar(ifc):
    """Dört yüz (önde ana + sağ cumba, arkada sol cumba + ana tek levha); levhanın altı saçakta duvar üstü + topuk + 10. Kalkan dolguları
    çatının altında kalır (ana çatınınki mahyasına, cumbanınki kendi mahyasına) ve duvar üstünden ya da alttaki cumbanın çatısından başlar."""
    ozet, f = ifc
    yuz = {_ps(e)["Duzlem"]: _kutu(e) for e in f.by_type("IfcSlab") if e.Name.startswith("CATI_")}
    assert set(yuz) == {"sol cumba ön", "sağ cumba arka", "ana çatı ön", "ana çatı arka"}
    assert all(abs(a[2] - 270) < 0.1 for a, _ in yuz.values())
    assert abs(ozet["cati"]["mahya_cm"] - 413.4) < 0.05
    alin = {_ps(e)["Kalkan"]: _kutu(e) for e in f.by_type("IfcPlate") if e.Name.startswith("ALIN_")}
    assert len(alin) == 6
    beklenen_tepe = {"sol cumba sol kalkanı": 375.29, "ana çatı sol kalkanı": 413.43, "ana çatı sağ kalkanı": 413.43,
                     "sağ cumba sağ kalkanı": 385.49}
    for ad, z in beklenen_tepe.items():
        assert abs(alin[ad][1][2] - z) < 0.1, (ad, alin[ad])
    assert abs(alin["ana çatı sol kalkanı"][0][2] - 260) < 0.1                 # alttaki sol cumbanın çatısından (saçak kotu)
    assert all(b[2] <= 413.43 + 0.1 and a[2] >= 250 - 0.1 for a, b in alin.values())


@pytest.mark.parametrize("dosya", ["is_emri/P6001_2plus1_6x6.json", "testler/motor/veri/TK02.json", "testler/motor/veri/TK01_r07.json"])
def test_girintisiz_evde_plan_ayni(dosya):
    """Girintisiz evde `hazirla` girintili gövdenin alanlarını yazmaz (IFC eskisi gibi kutudan)."""
    yol = KOK / dosya
    if not yol.exists():
        pytest.skip(f"{dosya} yok")
    h = ifc_uret.hazirla(copy.deepcopy(_oku(yol)))
    assert "govde" not in h and "cati_serit" not in h


@pytest.fixture(scope="module")
def kart(tmp_path_factory):
    """Kart modeli (K2 çatı katmanları ve K3b çatı kenarları dahil) TK-03'te."""
    from motor import kart_model
    yol = tmp_path_factory.mktemp("tk03_kart")
    kart_model.uret(_oku(VERI / "TK03.json"), yol, "TK03")
    return {k["kod"]: k for k in _oku(yol / "TK03_kart_sayim.json")["kartlar"]}


def test_kart_modelinin_catisi_listeyle_ayni(kart):
    """Girintili gövdenin çatı katmanları liste üretecinin saydığı çatıdan (`motor/yerlesim/serit.py`): aşık boyu, sandviç panel, baş makas
    betopanı, dere ve iniş, saçak sacı, alın kenarları (Z, alın sacı, C kapama) ve mahya listeyle aynı; dış ölçü kutusuyla kurulmaz."""
    from motor import prefabrik_liste as PL
    L = PL.is_emrinden(_oku(VERI / "TK03.json"))["satirlar"]
    say = lambda on: sum(s["adet"] or 0 for s in L if s["kalem"].startswith(on))
    formul = lambda on: next(s["formul"] for s in L if s["kalem"].startswith(on))
    assert "207,1 m" in formul("Aşık") and abs(kart["AS-01"]["metre"] - 207.14) < 0.05
    assert kart["KP-01"]["adet"] == say("Sandviç panel (") == 28
    assert kart["BT-01"]["adet"] == say("Baş makas betopanı") == 13
    assert "26,53 m" in formul("Metal dere") and abs(kart["DR-01"]["metre"] - 26.53) < 0.01
    assert kart["DR-02"]["adet"] == say("Metal dere inişi") == 8
    assert "26,53 m" in formul("Saçak sacı") and abs(kart["CK-02"]["metre"] - 26.53) < 0.01
    assert "27,36 m" in formul("Alın sacı")
    for kk in ("CK-03", "CK-04", "CK-05"):
        assert abs(kart[kk]["metre"] - 27.36) < 0.01 and kart[kk]["adet"] == 8, kk          # sekiz görünen alın kenarı
    assert abs(kart["CK-06"]["metre"] - 12.97) < 0.01 and kart["CK-06"]["adet"] == 3       # üç parçanın görünen mahyası
    assert abs(kart["CK-01"]["metre"] - 24.73) < 0.01                                       # saçak hatlarının altındaki duvarlar
