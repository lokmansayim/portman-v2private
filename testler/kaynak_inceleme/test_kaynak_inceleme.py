"""kaynak_inceleme: IFC yazıcı, bağlayıcı denetim kapıları, kalıcı kimlikli seçim ve çatı/gövde denetimi.

Sentetik küçük veriyle koşar (ağ, LLM, canlı sunucu yok). Codex devrinin gerçek verisiyle bütünleşik test yalnız
PORTMAN_KAYNAK_VERI verilirse koşar (devir klasörünün düzeni; bkz. kaynak_inceleme/README.md).
"""
from __future__ import annotations

import copy
import os
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
import numpy as np
import pytest

from kaynak_inceleme import cati, secim
from kaynak_inceleme.geometri import dunya_koseleri, dunya_matrisi
from kaynak_inceleme.ifc_dogrula import dogrula, karsilastir
from kaynak_inceleme.ifc_yaz import cati_tanimi, ifc_yaz, model_tanimi

BIRIM = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
DONUK = [0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1, 0, 100.0, 50.0, 0, 1]  # z çevresinde 90°, öteleme inç


def _secili(sha: str = "a" * 64) -> dict:
    tetra = {"vertices": [[0, 0, 0], [1.25, 0, 0], [0, 0.8, 0], [0, 0, 2.5]],
             "triangles": [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], "uv": [[0, 0]] * 4,
             "materials": ["m1", "m1", "m2", None]}
    ucgen = {"vertices": [[0, 0, 3], [2, 0, 3], [0, 2, 3.5]], "triangles": [[0, 1, 2]], "uv": [[0, 0]] * 3, "materials": [None]}
    return {"code": "P0001", "revision": "SKP-inceleme-01", "source_sha256": sha, "focus": [0, 0, 0], "notes": [],
            "materials": {"m1": {"name": "Beyaz", "color": [1, 1, 1, 1], "texture": None},
                          "m2": {"name": "Kırmızı", "color": [1, 0, 0, .5], "texture": None}},
            "meshes": {"g1": tetra, "g2": ucgen},
            "nodes": [{"id": 1, "name": "Group#1", "source_id": 111, "world_transform": DONUK, "material": "m1",
                       "geometry": "g1", "root": 1, "roof": False, "stage": 1},
                      {"id": 2, "name": "Group#2", "source_id": 222, "world_transform": BIRIM, "material": "m2",
                       "geometry": "g2", "root": 2, "roof": True, "stage": 3}]}


def _secenek(kaynak: dict, harf: str) -> dict:
    s = copy.deepcopy(kaynak)
    s["revision"] = f"{kaynak['code']}-CATI-{harf}-01"
    if harf != "A":
        s["nodes"] = [n for n in s["nodes"] if not n["roof"]]
        s["meshes"][f"{harf}_01"] = {"vertices": [[0, 0, 3.2], [3, 0, 3.2], [0, 3, 3.2]], "triangles": [[0, 1, 2]],
                                     "uv": [[0, 0]] * 3, "materials": ["roof"]}
        s["materials"]["roof"] = {"name": "Öneri antrasit çatı", "color": [.22, .25, .27, 1], "texture": None}
        s["nodes"].append({"id": 1000, "name": "Öneri çatı", "source_id": None, "world_transform": BIRIM, "material": "roof",
                           "geometry": f"{harf}_01", "root": f"{harf}_01", "roof": True, "stage": 3, "proposal": True})
    return s


def _yaz(tmp_path: Path, secili: dict | None = None, zaman: int = 0, harf: str | None = None):
    secili = secili or _secili()
    tanim = cati_tanimi(secili, harf) if harf else model_tanimi(secili)
    sonuc = ifc_yaz(secili, tmp_path, tanim, zaman=zaman)
    return secili, tanim, Path(sonuc["ifc"])


# --- IFC yazıcı ve kapılar ---------------------------------------------------------------------------------------

def test_yazilan_ifc_butun_kapilardan_gecer(tmp_path):
    secili, tanim, yol = _yaz(tmp_path)
    r = dogrula(yol, secili, tanim)
    assert r["gecti"], r["kapilar"]
    assert r["kapilar"]["nesne"]["bulunan"] == 2
    assert r["kapilar"]["topoloji"]["saklanan_ucgen"] == 5
    assert r["kapilar"]["koordinat"]["en_buyuk_fark_m"] == 0.0


def test_tarih_damgasi_karsilastirmayi_etkilemez_icerik_farki_etkiler(tmp_path):
    _, _, a = _yaz(tmp_path / "a", zaman=0)
    _, _, b = _yaz(tmp_path / "b", zaman=1790000000)
    assert karsilastir(a, b)["ayni"]
    s = _secili()
    s["nodes"][0]["name"] = "Group#99"
    _, _, c = _yaz(tmp_path / "c", secili=s)
    assert not karsilastir(a, c)["ayni"]


def test_koordinat_bozulursa_kalir(tmp_path):
    secili, tanim, yol = _yaz(tmp_path)
    f = ifcopenshell.open(str(yol))
    pl = f.by_type("IfcCartesianPointList3D")[0]
    koord = [list(p) for p in pl.CoordList]
    koord[0][0] += 1e-4
    pl.CoordList = [tuple(p) for p in koord]
    f.write(str(yol))
    r = dogrula(yol, secili, tanim, geometri=False)
    assert not r["gecti"] and not r["kapilar"]["koordinat"]["gecti"]


def test_nesne_eksikse_kalir(tmp_path):
    secili, tanim, yol = _yaz(tmp_path)
    f = ifcopenshell.open(str(yol))
    f.remove(f.by_type("IfcBuildingElementProxy")[0])
    f.write(str(yol))
    r = dogrula(yol, secili, tanim, geometri=False)
    assert not r["gecti"] and not r["kapilar"]["nesne"]["gecti"]
    assert r["kapilar"]["nesne"]["eksik_dugum"]


def test_topoloji_bozulursa_kalir(tmp_path):
    secili, tanim, yol = _yaz(tmp_path)
    f = ifcopenshell.open(str(yol))
    fs = f.by_type("IfcTriangulatedFaceSet")[0]
    idx = [list(t) for t in fs.CoordIndex]
    idx[0] = [idx[0][0], idx[0][0], idx[0][2]]
    fs.CoordIndex = [tuple(t) for t in idx]
    f.write(str(yol))
    r = dogrula(yol, secili, tanim, geometri=False)
    assert not r["gecti"] and not r["kapilar"]["topoloji"]["gecti"]


def test_kaynak_sha_ozelligi_bozulursa_kalir(tmp_path):
    secili, tanim, yol = _yaz(tmp_path)
    f = ifcopenshell.open(str(yol))
    for p in f.by_type("IfcPropertySingleValue"):
        if p.Name == "KaynakSHA256":
            p.NominalValue = f.create_entity("IfcLabel", "b" * 64)
            break
    f.write(str(yol))
    r = dogrula(yol, secili, tanim, geometri=False)
    assert not r["gecti"] and not r["kapilar"]["ozellik"]["gecti"]


def test_baska_kaynagin_ifcsi_kabul_edilmez(tmp_path):
    secili, tanim, yol = _yaz(tmp_path)
    baska = _secili(sha="c" * 64)
    r = dogrula(yol, baska, model_tanimi(baska), geometri=False)
    assert not r["gecti"] and not r["kapilar"]["nesne"]["gecti"]


def test_cati_secenegi_ozellikleri_ve_parca_durumu(tmp_path):
    secenek = _secenek(_secili(), "B")
    secili, tanim, yol = _yaz(tmp_path, secili=secenek, harf="B")
    r = dogrula(yol, secili, tanim)
    assert r["gecti"], r["kapilar"]
    f = ifcopenshell.open(str(yol))
    durum = {ifcopenshell.util.element.get_psets(o)["Portman_Kaynak"]["ParcaDurumu"] for o in f.by_type("IfcBuildingElementProxy")}
    assert durum == {"Yeni tasarım önerisi", "Kaynak SKP geometrisi"}
    assert f.by_type("IfcProject")[0].Name == "P0001-CATI-B-01"


def test_cati_tanimi_revizyonla_uyusmali():
    with pytest.raises(ValueError):
        cati_tanimi(_secenek(_secili(), "B"), "C")


# --- geometri -----------------------------------------------------------------------------------------------------

def test_blender32_ile_float64_farki_mikronun_altinda_ve_float32_yuvarli():
    v = [[0.123456789, 4.98765, 2.5], [10.24, 8.885, 3.1017]]
    a = dunya_koseleri(DONUK, v, "blender32")
    b = dunya_koseleri(DONUK, v, "float64")
    assert np.abs(a - b).max() < 1e-6
    assert np.array_equal(a, a.astype(np.float32).astype(np.float64))
    assert np.allclose(b[1], [-8.885 + 100 * .0254, 10.24 + 50 * .0254, 3.1017])


def test_normalize_olmayan_donusum_reddedilir():
    t = list(BIRIM)
    t[15] = .5035167782
    with pytest.raises(ValueError):
        dunya_matrisi(t)


# --- seçim --------------------------------------------------------------------------------------------------------

def _sahne(sha: str = "d" * 64) -> dict:
    kutu = lambda x0, z1: [[x0 / .0254, 0, 0], [(x0 + 1) / .0254, 1 / .0254, z1 / .0254]]  # noqa: E731
    ag = {"vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "triangles": [[0, 1, 2]], "uv": [[0, 0]] * 3, "materials": [None]}
    bos = {"vertices": [], "triangles": [], "uv": [], "materials": []}
    dugum = lambda i, ust, sid, g, x0=0.0, z1=3.0, gizli=False: {  # noqa: E731
        "id": i, "parent": ust, "name": f"Group#{i}", "source_id": sid, "hidden": gizli, "world_transform": BIRIM,
        "material": None, "geometry": g, "face_count": 80, "bbox_parent_inches": kutu(x0, z1)}
    kok = {"id": 0, "parent": None, "name": "model", "hidden": False, "world_transform": BIRIM, "material": None,
           "geometry": "bos", "face_count": 0}
    return {"sha256": sha, "units": "meters", "source_units": "inches", "conversion": .0254,
            "materials": {}, "meshes": {"a": ag, "bos": bos},
            "nodes": [kok, dugum(1, 0, 500, "a"), dugum(2, 1, 501, "a"), dugum(3, 0, 600, "a", z1=4.5),
                      dugum(4, 0, 700, "a"), dugum(5, 0, 800, "a", gizli=True), dugum(6, 0, 900, "a", x0=15.0)]}


def test_secim_kalici_kimlikle_kurulur_sira_numarasina_guvenmez():
    sahne = _sahne()
    k = secim.secim_kaydi_uret(sahne, "P0001", {3}, {4}, kopya_x_min_esigi_m=12.0)
    s = secim.sec(sahne, k)
    assert [n["id"] for n in s["nodes"]] == [1, 2, 3]  # 4 dışlandı, 5 gizli, 6 ikinci kopya
    assert [n["roof"] for n in s["nodes"]] == [False, False, True]
    k2 = copy.deepcopy(k)
    for e in k2["cati_kokleri"] + k2["dislanan_kokler"]:
        e["sira"] = 99  # sıra numarası bozulsa da kalıcı kimlik aynı parçayı bulur
    assert secim.sec(sahne, k2)["nodes"] == s["nodes"]


def test_secim_sha_farkinda_ve_belirsiz_kimlikte_durur():
    sahne = _sahne()
    k = secim.secim_kaydi_uret(sahne, "P0001", {3}, {4})
    with pytest.raises(secim.SecimHatasi):
        secim.sec({**sahne, "sha256": "e" * 64}, k)
    ikiz = copy.deepcopy(sahne)
    ikiz["nodes"][4]["source_id"] = 600  # iki kök grupta aynı kalıcı kimlik
    with pytest.raises(secim.SecimHatasi):
        secim.sec(ikiz, k)


# --- çatı / gövde -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("harf", ["A", "B"])
def test_govde_korunumu_gecer(harf):
    r = cati.govde_korunumu(_secili(), _secenek(_secili(), harf), harf)
    assert r["gecti"], r["hatalar"]


def test_govde_degisirse_kalir():
    s = _secenek(_secili(), "B")
    s["meshes"]["g1"]["vertices"][0] = [0, 0, 0.001]
    r = cati.govde_korunumu(_secili(), s, "B")
    assert not r["gecti"] and any("gövde ağı" in h for h in r["hatalar"])


def test_oneri_kaynak_catiyla_karismaz():
    b = _secenek(_secili(), "B")
    b["nodes"].append(copy.deepcopy(_secili()["nodes"][1]))  # kaynak çatı B'de kalmış
    assert not cati.govde_korunumu(_secili(), b, "B")["gecti"]
    a = _secenek(_secili(), "A")
    a["nodes"].append(dict(_secenek(_secili(), "B")["nodes"][-1]))  # A'da öneri parçası
    assert not cati.govde_korunumu(_secili(), a, "A")["gecti"]
    c = _secenek(_secili(), "C")
    c["nodes"][-1]["source_id"] = 111  # öneri parçası kaynak kimliği taşıyor
    assert not cati.govde_korunumu(_secili(), c, "C")["gecti"]


# --- gerçek devir verisiyle (isteğe bağlı) --------------------------------------------------------------------------

@pytest.mark.skipif(not os.environ.get("PORTMAN_KAYNAK_VERI"), reason="PORTMAN_KAYNAK_VERI verilmedi (Codex devir verisi)")
def test_codex_devri_yeniden_uretilir_ve_denetlenir(tmp_path):
    from kaynak_inceleme.dogrula_devir import calistir

    r = calistir(Path(os.environ["PORTMAN_KAYNAK_VERI"]), tmp_path, geometri=False)
    assert r["gecti"], r["adimlar"]
