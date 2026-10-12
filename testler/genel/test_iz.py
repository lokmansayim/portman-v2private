"""İE-08 GM3 · motor/genel/iz.py: IFC içerik izi başlık zamanına, GlobalId'ye, kayıt numarasına, küme sırasına ve ondalık gürültüsüne
duyarsız; geometri ve nitelik değişimine duyarlı. JSON izi anahtar sırasına ve boşluğa duyarsız."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import iz  # noqa: E402

IFC = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('','2026-10-10T14:53:33',(''),(''),'IfcOpenShell 0.8.5-1c5b825','IfcOpenShell 0.8.5-1c5b825','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCCARTESIANPOINT((0.,0.,0.));
#2=IFCCARTESIANPOINT((1024.0000000000002,0.,0.));
#3=IFCPOLYLINE((#1,#2));
#4=IFCWALL('2Zk3abcdefghijklmnopqr',$,'DK',$,$,#3,$,$,.SOLIDWALL.);
#5=IFCWALL('3Zk3abcdefghijklmnopqr',$,'DG',$,$,#3,$,$,.SOLIDWALL.);
#6=IFCRELCONTAINEDINSPATIALSTRUCTURE('1Ab3abcdefghijklmnopqr',$,$,$,(#4,#5),#7);
#7=IFCBUILDINGSTOREY('0Ab3abcdefghijklmnopqr',$,'zemin',$,$,$,$,$,.ELEMENT.,0.);
ENDSEC;
END-ISO-10303-21;
"""


def _iz(metin: str) -> str:
    return hashlib.sha256("\n".join(iz.ifc_kanonik(metin)).encode("utf-8")).hexdigest()


def test_baslik_guid_ve_ondalik_gurultusu_izi_degistirmez():
    a = _iz(IFC)
    b = _iz(IFC.replace("2026-10-10T14:53:33", "2026-10-12T07:58:19").replace("0.8.5-1c5b825", "0.9.0-abc1234")
                  .replace("2Zk3abcdefghijklmnopqr", "9Qx3zzzzzzzzzzzzzzzzzz").replace("1024.0000000000002", "1024.00000000001"))
    assert a == b


def test_kayit_numarasi_ve_kume_sirasi_izi_degistirmez():
    # #4 ↔ #5 numaraları yer değiştirsin, ilişkinin listesi ters yazılsın: içerik aynı
    yeni = (IFC.replace("#4=IFCWALL('2Zk3abcdefghijklmnopqr',$,'DK'", "#4=IFCWALL('2Zk3abcdefghijklmnopqr',$,'DG'")
               .replace("#5=IFCWALL('3Zk3abcdefghijklmnopqr',$,'DG'", "#5=IFCWALL('3Zk3abcdefghijklmnopqr',$,'DK'")
               .replace("(#4,#5)", "(#5,#4)"))
    assert _iz(IFC) == _iz(yeni)


def test_geometri_ve_nitelik_degisimi_izi_degistirir():
    assert _iz(IFC) != _iz(IFC.replace("1024.0000000000002", "1023.5"))                   # ölçü
    assert _iz(IFC) != _iz(IFC.replace("'DK'", "'DKX'"))                                  # ad
    assert _iz(IFC) != _iz(IFC.replace("(#4,#5)", "(#4)"))                                # ilişkiden eleman düşmesi
    assert _iz(IFC) != _iz(IFC.replace(".SOLIDWALL.", ".PARTITIONING."))                   # tür


def test_polyline_nokta_sirasi_korunur():
    # geometri listeleri küme değildir: nokta sırası değişince iz değişir
    assert _iz(IFC) != _iz(IFC.replace("(#1,#2)", "(#2,#1)"))


def test_json_izi_anahtar_sirasi_ve_bosluga_duyarsiz(tmp_path: Path):
    a = tmp_path / "a.json"; b = tmp_path / "b.json"; c = tmp_path / "c.json"
    a.write_text(json.dumps({"x": 1, "y": [1, 2]}, indent=2), encoding="utf-8")
    b.write_text(json.dumps({"y": [1, 2], "x": 1}), encoding="utf-8")
    c.write_text(json.dumps({"y": [2, 1], "x": 1}), encoding="utf-8")
    assert iz.json_izi(a) == iz.json_izi(b) != iz.json_izi(c)
    assert iz.dosya_izi(a) == iz.json_izi(a)


def test_depodaki_ifcnin_izi_kararli():
    # Ç8801 katalog IFC'si: ie-05 seti, ana set ve sunucu seti aynı izi verir (İE-08 Adım 2 kanıtı); bu iz referansta dondurulur.
    yol = KOK / "deneme" / "2026-10-10_c8801" / "cizimler" / "C8801_A" / "C8801.ifc"
    if not yol.exists():
        import pytest
        pytest.skip("deneme/ ağacı yok (sürüm ağacı)")
    assert iz.ifc_izi(yol) == iz.ifc_izi(yol) and len(iz.ifc_kanonik(yol.read_text())) > 2000
