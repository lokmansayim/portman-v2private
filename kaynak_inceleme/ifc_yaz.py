"""Kaynak inceleme modelinden geometrik IFC4 yazar (IfcBuildingElementProxy + Portman_Kaynak özellik kümesi).

Codex devrindeki iki betiğin yerine geçen tek, açık parametreli işlev:
  - export_ifc.py (üç model; Blender Python'u, sabit `work/`, `outputs/` yolları);
  - export_variants.py (P9401 çatıları; export_ifc.py'nin METNİNİ değiştirip exec eden sarmalayıcı).
Varlık oluşturma sırası ve yazılan değerler Codex'in betiğiyle aynıdır; aynı girdiden, tarih damgaları dışında aynı IFC
çıkar (kanıt: kaynak_inceleme/dogrula_devir.py). Blender gerekmez; IfcOpenShell 0.8.5 ve numpy yeter.

Kapsam: SKP kaynak geometrisinin referans IFC'si. Semantik duvar/pano BIM'i, BOM ve üretim kabulü DEĞİLDİR.
Üretim IFC'si İş Emri'nden gelir (deneme/2026-09-23/13_Kiyas/kod/ifc_uret.py; İE-04 adım 5'te Motor hattına alınacak).

Kullanım (depo kökünde):
    python -m kaynak_inceleme.ifc_yaz --secili <selected.json> --cikti <klasör>            # üç modelden biri
    python -m kaynak_inceleme.ifc_yaz --secili <B_selected.json> --cikti <klasör> --cati B  # P9401 çatı seçeneği
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import ifcopenshell

from .geometri import dugum_guid, dunya_koseleri, secili_oku

ACIKLAMA = "Kaynak SKP geometrisi; teknik ve üretim kabulü bekliyor."
IFC_KAPSAMI = "Geometrik referans; BIM/BOM sınıflandırması bekliyor"
UYGULAMA_SURUMU = "SKP-inceleme-01"  # Codex'teki değer; çatı seçeneklerinde de aynı kalmıştı


@dataclass(frozen=True)
class Tanim:
    """Ne yazılacağı. GUID tohumu: kaynak SHA256 / kimlik_anahtari / düğüm kimliği."""

    model: str
    kimlik_anahtari: str
    proje_adi: str
    dosya_adi: str
    kapsam: str
    secenek: str | None = None


def model_tanimi(secili: dict) -> Tanim:
    kod = secili["code"]
    return Tanim(kod, kod, f"{kod} kaynak inceleme", f"{kod}_referans.ifc",
                 "SKP geometrik referans; üretim veya semantik BIM kabulü değildir")


def cati_tanimi(secili: dict, harf: str) -> Tanim:
    kod, rev = secili["code"], secili["revision"]
    if f"-CATI-{harf}-" not in rev:
        raise ValueError(f"seçenek {harf} ile revizyon uyuşmuyor: {rev}")
    return Tanim(kod, rev, rev, f"{kod}_Cati_{harf}.ifc",
                 f"{kod} çatı karşılaştırması; kaynak gövde + işaretli tasarım önerisi; üretim kabulü değil", harf)


def ozellikler(n: dict, secili: dict, tanim: Tanim) -> dict[str, str]:
    p = {"Model": tanim.model, "Revizyon": secili["revision"], "KaynakSHA256": secili["source_sha256"],
         "SKP_Nesne": str(n.get("source_id", "")), "SKP_Grup": str(n["root"]), "Kabul": "Bekliyor"}
    if tanim.secenek:
        p["Secenek"] = tanim.secenek
        p["ParcaDurumu"] = "Yeni tasarım önerisi" if n.get("proposal") else "Kaynak SKP geometrisi"
    p["IFC_Kapsami"] = IFC_KAPSAMI
    p["Sunum_Cati"] = "Evet" if n["roof"] else "Hayır"
    return p


def ifc_yaz(secili: dict, cikti: Path, tanim: Tanim, *, kip: str = "blender32", zaman: int | None = None) -> dict:
    """IFC'yi `cikti/tanim.dosya_adi`'na yazar; beklenen değerleri (düğüm başına sınır kutusu, üçgen) döndürür."""
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    sha, kod = secili["source_sha256"], tanim.model
    guid = lambda anahtar: dugum_guid(sha, tanim.kimlik_anahtari, anahtar)  # noqa: E731
    f = ifcopenshell.file(schema="IFC4")
    ce = f.create_entity
    org = ce("IfcOrganization", Name="Portman")
    person = ce("IfcPerson", FamilyName="Kaynak inceleme")
    user = ce("IfcPersonAndOrganization", ThePerson=person, TheOrganization=org)
    app = ce("IfcApplication", ApplicationDeveloper=org, Version=UYGULAMA_SURUMU,
             ApplicationFullName="Portman kaynak geometri aktarımı", ApplicationIdentifier="PORTMAN-SKP-REVIEW")
    owner = ce("IfcOwnerHistory", OwningUser=user, OwningApplication=app, ChangeAction="ADDED",
               CreationDate=int(time.time()) if zaman is None else int(zaman))
    axis = ce("IfcAxis2Placement3D", Location=ce("IfcCartesianPoint", Coordinates=(0., 0., 0.)))
    ctx = ce("IfcGeometricRepresentationContext", ContextType="Model", CoordinateSpaceDimension=3, Precision=1e-7,
             WorldCoordinateSystem=axis)
    body = ce("IfcGeometricRepresentationSubContext", ContextIdentifier="Body", ContextType="Model", ParentContext=ctx,
              TargetView="MODEL_VIEW")
    units = ce("IfcUnitAssignment", Units=[ce("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE"),
                                           ce("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE"),
                                           ce("IfcSIUnit", UnitType="VOLUMEUNIT", Name="CUBIC_METRE")])
    project = ce("IfcProject", GlobalId=guid("project"), OwnerHistory=owner, Name=tanim.proje_adi,
                 RepresentationContexts=[ctx], UnitsInContext=units)

    def yerel(ust=None):
        return ce("IfcLocalPlacement", PlacementRelTo=ust, RelativePlacement=axis)

    site = ce("IfcSite", GlobalId=guid("site"), OwnerHistory=owner, Name="Kaynak konumu", ObjectPlacement=yerel(),
              CompositionType="ELEMENT")
    building = ce("IfcBuilding", GlobalId=guid("building"), OwnerHistory=owner, Name=kod,
                  ObjectPlacement=yerel(site.ObjectPlacement), CompositionType="ELEMENT")
    storey = ce("IfcBuildingStorey", GlobalId=guid("storey"), OwnerHistory=owner, Name="Zemin Kat",
                ObjectPlacement=yerel(building.ObjectPlacement), CompositionType="ELEMENT", Elevation=0.)
    for i, (ust, alt) in enumerate([(project, site), (site, building), (building, storey)]):
        ce("IfcRelAggregates", GlobalId=guid("rel" + str(i)), OwnerHistory=owner, RelatingObject=ust, RelatedObjects=[alt])
    stiller = {}
    for k, m in secili["materials"].items():
        renk = ce("IfcColourRgb", Red=m["color"][0], Green=m["color"][1], Blue=m["color"][2])
        golge = ce("IfcSurfaceStyleShading", SurfaceColour=renk, Transparency=1 - m["color"][3])
        stiller[k] = ce("IfcSurfaceStyle", Name=m["name"], Side="BOTH", Styles=[golge])
    urunler, beklenen, kaynak_ucgen = [], {}, 0
    for n in secili["nodes"]:
        mesh = secili["meshes"][n["geometry"]]
        koseler = dunya_koseleri(n["world_transform"], mesh["vertices"], kip)
        verts = [tuple(float(x) for x in v) for v in koseler]
        yuzler = mesh["triangles"]
        kaynak_ucgen += len(yuzler)
        coord = ce("IfcCartesianPointList3D", CoordList=verts)
        kutular: dict = {}
        for tri, mk in zip(yuzler, mesh["materials"]):
            kutular.setdefault(mk or n["material"], []).append(tuple(int(i) + 1 for i in tri))
        ogeler = []
        for mk, tris in kutular.items():
            oge = ce("IfcTriangulatedFaceSet", Coordinates=coord, Closed=False, CoordIndex=tris)
            ogeler.append(oge)
            if mk in stiller:
                ce("IfcStyledItem", Item=oge, Styles=[stiller[mk]])
        rep = ce("IfcShapeRepresentation", ContextOfItems=body, RepresentationIdentifier="Body",
                 RepresentationType="Tessellation", Items=ogeler)
        shape = ce("IfcProductDefinitionShape", Representations=[rep])
        ob = ce("IfcBuildingElementProxy", GlobalId=guid(n["id"]), OwnerHistory=owner,
                Name=f"{kod}_{n['id']:03}_{n['name']}", Description=ACIKLAMA, ObjectType="SKP kaynak parçası",
                ObjectPlacement=yerel(storey.ObjectPlacement), Representation=shape, Tag=str(n.get("source_id", "")),
                PredefinedType="NOTDEFINED")
        urunler.append(ob)
        plist = [ce("IfcPropertySingleValue", Name=k, NominalValue=ce("IfcLabel", v))
                 for k, v in ozellikler(n, secili, tanim).items()]
        ps = ce("IfcPropertySet", GlobalId=guid("ps" + str(n["id"])), OwnerHistory=owner, Name="Portman_Kaynak",
                HasProperties=plist)
        ce("IfcRelDefinesByProperties", GlobalId=guid("psrel" + str(n["id"])), OwnerHistory=owner, RelatedObjects=[ob],
           RelatingPropertyDefinition=ps)
        beklenen[ob.GlobalId] = {"dugum": n["id"], "ucgen": len(yuzler),
                                 "sinir": [[min(v[i] for v in verts) for i in range(3)],
                                           [max(v[i] for v in verts) for i in range(3)]] if verts else None}
    ce("IfcRelContainedInSpatialStructure", GlobalId=guid("contains"), OwnerHistory=owner, RelatedElements=urunler,
       RelatingStructure=storey)
    yol = cikti / tanim.dosya_adi
    f.header.file_description.description = ("ViewDefinition [ReferenceView_V1.2]",
                                             "Geometrik kaynak incelemesi; teknik kabul bekliyor.")
    f.write(str(yol))
    return {"ifc": str(yol), "model": kod, "revizyon": secili["revision"], "secenek": tanim.secenek,
            "kapsam": tanim.kapsam, "kip": kip, "nesne": len(urunler), "kaynak_ucgen": kaynak_ucgen,
            "kaynak_sha256": sha, "beklenen": beklenen}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--secili", required=True, type=Path)
    ap.add_argument("--cikti", required=True, type=Path)
    ap.add_argument("--cati", help="P9401 çatı seçeneği harfi (A–D); verilmezse model IFC'si yazılır")
    ap.add_argument("--kip", default="blender32", choices=["blender32", "float64"])
    ap.add_argument("--zaman", type=int, help="IfcOwnerHistory.CreationDate (tekrar üretilebilirlik için sabit verilebilir)")
    ap.add_argument("--dogrula", action="store_true", help="yazdıktan sonra bağlayıcı denetimi koş; geçmezse çıkış 1")
    a = ap.parse_args(argv)
    secili = secili_oku(a.secili)
    tanim = cati_tanimi(secili, a.cati) if a.cati else model_tanimi(secili)
    sonuc = ifc_yaz(secili, a.cikti, tanim, kip=a.kip, zaman=a.zaman)
    ozet = {k: v for k, v in sonuc.items() if k != "beklenen"}
    print(json.dumps(ozet, ensure_ascii=False))
    if a.dogrula:
        from .ifc_dogrula import dogrula

        rapor = dogrula(Path(sonuc["ifc"]), secili, tanim, kip=a.kip)
        print(json.dumps({k: rapor[k] for k in ("gecti", "kapilar")}, ensure_ascii=False))
        return 0 if rapor["gecti"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
