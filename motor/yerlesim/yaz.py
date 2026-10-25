"""K2 ve K3 parçalarının kart modeline yazılması: her parça kartının türüne bağlı bir IFC örneği.

Parça dünya koordinatındadır (cm; yerleşimi birim matris, bugünkü IFC'nin parçaları gibi), kat kabına girer. GlobalId evin kimliğinden
(İş Emri numarası) ve parçanın adından türer: her üretimde aynı, iki evin modeli birlikte açılınca çakışmaz. `PortatifEv_Parca`: kart kodu, paftadaki anahtarı (`;`), uygulanan kural, kaynak ve kuralın parçaya yazdığı
bilgiler. Boyla alınan parçada `Qto_…BaseQuantities.Length` (m; yerleşim kapısı metreyi buradan toplar), levha ve kaplamada `GrossArea` (tam
levha, kaplamada şerit). Kablo (K3) kare kesitli çubuktur; boyu (`Qto_CableSegmentBaseQuantities.Length`) formülden, çizgisinin boyundan değil.
K3b'nin sacları ve profilleri birden çok kesitli gövdedir (`coklu`: sacın her yüzü bir prizma; tek temsilde). Renkler yalnız gösterimdir.
"""
from __future__ import annotations

import importlib
import uuid

import ifcopenshell.guid
import numpy as np
from ifcopenshell.util.shape_builder import ShapeBuilder

AD_ALANI = uuid.UUID("8c0f3b5e-2a71-4d4e-9f3c-6b1a0e2d7c94")     # K2 parçalarının GlobalId'si ev kimliği ve adından türer
QTO = {"IfcMember": "Qto_MemberBaseQuantities", "IfcPipeSegment": "Qto_PipeSegmentBaseQuantities", "IfcCovering": "Qto_CoveringBaseQuantities",
       "IfcPlate": "Qto_PlateBaseQuantities", "IfcCableSegment": "Qto_CableSegmentBaseQuantities"}
RENK = {"omega": (0.85, 0.55, 0.15), "asik": (0.20, 0.45, 0.80), "panel": (0.25, 0.27, 0.30), "levha": (0.80, 0.42, 0.20),
        "dere": (0.55, 0.58, 0.62), "inis": (0.40, 0.42, 0.46),
        "tavan_armaturu": (0.95, 0.20, 0.15), "glop": (0.95, 0.75, 0.20), "anahtar_tekli": (0.20, 0.60, 0.30), "anahtar_cift": (0.10, 0.45, 0.20),
        "priz_tekli": (0.20, 0.40, 0.85), "priz_cift": (0.10, 0.25, 0.65), "uydu_prizi": (0.55, 0.30, 0.75), "zil": (0.85, 0.45, 0.10),
        "sigorta_kutusu": (0.15, 0.15, 0.15), "kablo_priz": (0.20, 0.40, 0.85), "kablo_aydinlatma": (0.95, 0.55, 0.15),
        "alt_cerceve": (0.45, 0.47, 0.50), "sacak_omegasi": (0.70, 0.35, 0.15), "sacak_saci": (0.30, 0.32, 0.36), "alin_saci": (0.20, 0.22, 0.26),
        "bas_makas_z": (0.55, 0.20, 0.55), "c_kapama": (0.15, 0.50, 0.50), "mahya": (0.60, 0.15, 0.15)}


def _api(ad: str, *a, **k):
    modul, islev = ad.split(".")
    return getattr(importlib.import_module(f"ifcopenshell.api.{modul}"), islev)(*a, **k)


def _m(v: float) -> float:
    return v / 100.0


def _govdeler(sb: ShapeBuilder, geo: dict) -> list:
    if geo["tip"] == "coklu":                                          # K3b: sacın yüzleri, her biri bir prizma
        return [g for p in geo["parcalar"] for g in _govdeler(sb, p)]
    return [_govde(sb, geo)]


def _govde(sb: ShapeBuilder, geo: dict):
    if geo["tip"] == "cubuk":                                          # K3 kablosu: kare kesitli çubuk, p0'dan p1'e
        p0, p1 = np.array(geo["p0"], dtype=float), np.array(geo["p1"], dtype=float)
        v = p1 - p0
        L = float(np.linalg.norm(v))
        z = v / L
        x = np.cross(z, [0.0, 0.0, 1.0])
        x = x / np.linalg.norm(x) if np.linalg.norm(x) > 1e-9 else np.array([1.0, 0.0, 0.0])
        k = _m(geo["kesit"])
        prof = sb.profile(sb.rectangle(size=np.array([k, k]), position=np.array([-k / 2, -k / 2])))
        return sb.extrude(prof, magnitude=_m(L), position=p0 / 100.0, position_z_axis=z, position_x_axis=x)
    if geo["tip"] == "kutu":
        x0, y0, z0, x1, y1, z1 = geo["kutu"]
        prof = sb.profile(sb.rectangle(size=np.array([_m(x1 - x0), _m(y1 - y0)])))
        return sb.extrude(prof, magnitude=_m(z1 - z0), position=np.array([_m(x0), _m(y0), _m(z0)]))
    prof = sb.profile(sb.polyline([np.array([_m(u), _m(z)]) for u, z in geo["noktalar"]], closed=True))
    a0, a1 = geo["a0"], geo["a1"]
    if geo["duzlem"] == "xz":                                          # kesit x–z, y boyunca a0..a1
        return sb.extrude(prof, magnitude=_m(a1 - a0), position=np.array([0.0, _m(a1), 0.0]),
                          position_z_axis=np.array([0.0, -1.0, 0.0]), position_x_axis=np.array([1.0, 0.0, 0.0]))
    return sb.extrude(prof, magnitude=_m(a1 - a0), position=np.array([_m(a0), 0.0, 0.0]),     # kesit y–z, x boyunca a0..a1
                      position_z_axis=np.array([1.0, 0.0, 0.0]), position_x_axis=np.array([0.0, 1.0, 0.0]))


def yaz(f, parcalar: list[dict], turler: dict, kaynak: str, parca_seti: str, kimlik: str) -> list:
    """`parcalar`: kart modelinin eşlediği K2 parçaları ({ad, kart, sinif, pafta, kural, geo, bilgi, boy_cm?}); `turler`: kart kodu → tür;
    `kimlik`: evin kimliği (İş Emri numarası)."""
    kat = f.by_type("IfcBuildingStorey")[0]
    govde = next(c for c in f.by_type("IfcGeometricRepresentationSubContext") if c.ContextIdentifier == "Body")
    sb = ShapeBuilder(f)
    stiller = {}
    out = []
    for p in parcalar:
        e = _api("root.create_entity", f, ifc_class=p["sinif"], name=p["ad"])
        e.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(AD_ALANI, f"{kimlik}/{p['ad']}").hex)
        e.Description = p["aciklama"]
        _api("geometry.edit_object_placement", f, product=e)
        temsil = sb.get_representation(govde, _govdeler(sb, p["geo"]))
        _api("geometry.assign_representation", f, product=e, representation=temsil)
        if p["parca"] not in stiller:
            stiller[p["parca"]] = s = _api("style.add_style", f, name=f"K2 {p['parca']}")
            r, g_, b = RENK[p["parca"]]
            _api("style.add_surface_style", f, style=s, ifc_class="IfcSurfaceStyleShading",
                 attributes={"SurfaceColour": {"Name": None, "Red": r, "Green": g_, "Blue": b}, "Transparency": 0.0})
        _api("style.assign_representation_styles", f, shape_representation=temsil, styles=[stiller[p["parca"]]])
        _api("spatial.assign_container", f, relating_structure=kat, products=[e])
        _api("type.assign_type", f, related_objects=[e], relating_type=turler[p["kart"]["kod"]], should_map_representations=False)
        ozellik = {"KartKodu": p["kart"]["kod"], "PaftaAnahtari": ";".join(p["pafta"]), "KatalogKodu": "", "Kural": p["kural"], "Kaynak": kaynak}
        ozellik |= {k: v for k, v in p["bilgi"].items()}
        if "boy_cm" in p:
            ozellik["Boy_cm"] = p["boy_cm"]
        ps = _api("pset.add_pset", f, product=e, name=parca_seti)
        _api("pset.edit_pset", f, pset=ps, properties=ozellik)
        q = None
        if "boy_cm" in p:
            q = {"Length": _m(p["boy_cm"])}
        elif "alan_m2" in p:
            q = {"GrossArea": p["alan_m2"]}
        if q:
            qto = _api("pset.add_qto", f, product=e, name=QTO[p["sinif"]])
            _api("pset.edit_qto", f, qto=qto, properties=q)
        out.append(e)
    return out
