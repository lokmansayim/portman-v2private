"""İE-15 · K1 · Hakem değişikliği (CIO'nun KH-1 incelemesi, 20 Ekim; Patron onayı gerekir).

KH-1'in testleri (`test_hakem_pk01.py`) değişmez; bu dosya iki sıkılaştırmayı sınar:
- Kıyas aracı bölümünü tanımadığı bir teyit görürse (okuyucunun ileride eklediği bir bölüm) hangi satırı etkilediğini bilemez: bütün
  satırlar "teyit bekliyor" yazar, kapı geçmez, rapor bölümün tanınmadığını söyler. Önceden bu teyit sessizce yok sayılıyordu.
- Bir parçada aynı anahtar iki kez yazılmışsa (`a;a`) bir kez sayılır. Önceden iki sayılıyordu.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "testler" / "kimlik" / "hakem"))
import kiyas as KY  # noqa: E402

CEVAP = KOK / "testler" / "kimlik" / "veri" / "PK01_pafta_katmani.json"
PROJE = KOK / "testler" / "kimlik" / "hakem" / "projeler" / "PK01.json"
MOTOR_VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pk01_ifc(tmp_path_factory):
    from motor import ifc_uret
    yol = tmp_path_factory.mktemp("ifc") / "PK01.ifc"
    assert ifc_uret.uret(_oku(MOTOR_VERI / "PK01.json"), yol)["sema_hatasi"] == 0
    return yol


def test_taninmayan_teyit_bolumu_kapiyi_durdurur(pk01_ifc):
    cevap, proje = _oku(CEVAP), _oku(PROJE)
    assert KY.kiyasla(pk01_ifc, cevap, proje)["kapi_1"] == "geçer"
    teyitli = copy.deepcopy(cevap)
    teyitli["teyit_bekliyor"] = [{"bolum": "tavan_omega", "neden": "ölçek iki eksende farklı"}]
    k = KY.kiyasla(pk01_ifc, teyitli, proje)
    assert {s["sonuc"] for s in k["satirlar"]} == {"teyit bekliyor"} and k["kapi_1"] == "geçmez"
    assert "- tavan_omega: ölçek iki eksende farklı (bölüm tanınmıyor; bütün satırlar teyit bekliyor)" in KY.md(k).splitlines()


def test_ayni_anahtar_parca_basina_bir_kez(tmp_path):
    import ifcopenshell
    import ifcopenshell.api
    f = ifcopenshell.file(schema="IFC4")
    ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="sınama")
    for i, anahtar in enumerate(["makas_bas;makas_bas", "makas_bas; makas_bas;makas_orta"]):
        e = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcElementAssembly", name=f"MAKAS_{i:02d}")
        ps = ifcopenshell.api.run("pset.add_pset", f, product=e, name="PortatifEv_Parca")
        ifcopenshell.api.run("pset.edit_pset", f, pset=ps, properties={"PaftaAnahtari": anahtar})
    f.write(str(tmp_path / "m.ifc"))
    sayim, kartli = KY.say(ifcopenshell.open(str(tmp_path / "m.ifc")), ["makas_bas", "makas_orta"], [])
    assert (sayim["makas_bas"]["adet"], sayim["makas_orta"]["adet"], kartli) == (2, 1, 2)
