#!/usr/bin/env python3
"""IFC'den perspektif görüntüler. IFC, IfcOpenShell geometri motoruyla (boşluklar gerçekten kesilerek) üçgenlere çevrilir ve VTK ile
ekransız çizilir. Görüntüler IFC'nin içeriğidir; ayrı bir model kurulmaz.

Görüntüler: ön-sağ, ön-sol, arka-sol, arka-sağ (kuş bakışı perspektif), çatısız (duvarlar, doğramalar, mahal zeminleri), makaslı
(kaplama ve tavan kaldırılmış). Geometri denetimi: duvar gövdelerinin hacmi ve nesne sayıları `*_geometri.json` dosyasına yazılır.

Kullanım:
    python perspektif.py model.ifc cikti_klasoru [on_ek]
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import json
import math
import multiprocessing
import sys
from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np

MAHAL_RENGI = {"yatak_odasi": (0.89, 0.92, 0.97), "banyo": (0.86, 0.94, 0.93), "salon": (0.99, 0.95, 0.84), "mutfak": (0.99, 0.95, 0.84),
               "hol": (0.95, 0.92, 0.85), "depo": (0.93, 0.91, 0.88), "veranda": (0.85, 0.92, 0.80)}


def ucgenle(ifc_yol: Path):
    f = ifcopenshell.open(str(ifc_yol))
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    it = ifcopenshell.geom.iterator(s, f, max(1, multiprocessing.cpu_count()))
    cik = []
    if it.initialize():
        while True:
            sh = it.get()
            e = f.by_id(sh.id)
            g = sh.geometry
            v = np.array(g.verts, dtype=float).reshape(-1, 3)
            fc = np.array(g.faces, dtype=int).reshape(-1, 3)
            renk = []
            for m in g.materials:
                d = m.diffuse
                renk.append((d.r(), d.g(), d.b()))
            mid = np.array(g.material_ids, dtype=int)
            cik.append({"id": sh.id, "sinif": e.is_a(), "ad": e.Name or "", "tip": getattr(e, "PredefinedType", None), "v": v, "f": fc, "renk": renk, "mid": mid,
                        "uzun": getattr(e, "LongName", None)})
            if not it.next():
                break
    return f, cik


def hacim(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)


def denetim(f, sekiller) -> dict:
    import ifcopenshell.util.element as ue
    duvar = []
    for sh in sekiller:
        if sh["sinif"] != "IfcWall":
            continue
        e = f.by_id(sh["id"])
        q = ue.get_psets(e).get("Qto_WallBaseQuantities", {})
        duvar.append({"ad": sh["ad"], "geometri_m3": round(hacim(sh["v"], sh["f"]), 4), "net_yuz_m2": q.get("NetSideArea"), "kalinlik_m": q.get("Width")})
    for d in duvar:                      # kaba sağlama: gövde hacmi ≈ net yan alan × kalınlık (kaplama payları nedeniyle biraz büyük olabilir)
        d["beklenen_m3"] = None if d["net_yuz_m2"] is None else round(d["net_yuz_m2"] * d["kalinlik_m"], 4)
    return {"nesne": dict(Counter(s["sinif"] for s in sekiller)), "ucgen": int(sum(len(s["f"]) for s in sekiller)), "duvar": duvar}


def ciz(f, sekiller, cikti: Path, on_ek: str, genislik=1800, yukseklik=1150):
    import vtk
    from vtk.util import numpy_support as ns
    import ifcopenshell.util.element as ue

    tum = np.vstack([s["v"] for s in sekiller if s["sinif"] not in ("IfcSpace", "IfcOpeningElement")])
    lo, hi = tum.min(0), tum.max(0)
    merkez = (lo + hi) / 2
    cap = float(np.linalg.norm(hi - lo))
    islev = {}
    for sp in f.by_type("IfcSpace"):
        ps = ue.get_psets(sp).get("PortatifEv_Mahal", {})
        islev[sp.id()] = (ps.get("Islev") or "").split(", ")[0]

    def aktor(sh, renk_fn=None, kenar=True):
        v, fc = sh["v"], sh["f"]
        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.SetData(ns.numpy_to_vtk(v, deep=True))
        pd.SetPoints(pts)
        hucre = np.hstack([np.full((len(fc), 1), 3), fc]).astype(np.int64).ravel()
        ca = vtk.vtkCellArray()
        if hasattr(ca, "ImportLegacyFormat"):
            ca.ImportLegacyFormat(ns.numpy_to_vtkIdTypeArray(hucre, deep=True))
        else:
            ca.SetCells(len(fc), ns.numpy_to_vtkIdTypeArray(hucre, deep=True))
        pd.SetPolys(ca)
        renkler = np.zeros((len(fc), 3), dtype=np.uint8)
        for i in range(len(fc)):
            mi = sh["mid"][i] if i < len(sh["mid"]) else 0
            r = sh["renk"][mi] if 0 <= mi < len(sh["renk"]) else (0.7, 0.7, 0.7)
            if renk_fn:
                r = renk_fn(sh, r)
            renkler[i] = [int(255 * max(0.0, min(1.0, c))) for c in r]
        arr = ns.numpy_to_vtk(renkler, deep=True)
        arr.SetNumberOfComponents(3)
        arr.SetName("renk")
        pd.GetCellData().SetScalars(arr)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        m.SetScalarModeToUseCellData()
        m.SetResolveCoincidentTopologyToOff()         # yüzeyler geriye itilmez: birkaç cm arkadaki üyelerin çizgileri öne geçmesin
        a = vtk.vtkActor()
        a.SetMapper(m)
        p = a.GetProperty()
        p.SetInterpolationToFlat()
        p.SetAmbient(0.42)
        p.SetDiffuse(0.62)
        p.SetSpecular(0.0)
        cik = [a]
        if kenar:                                   # belirgin kenarlar (30°'den keskin) ve sınır kenarları ince çizgi
            fe = vtk.vtkFeatureEdges()
            fe.SetInputData(pd)
            fe.BoundaryEdgesOn(); fe.FeatureEdgesOn(); fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff()
            fe.SetFeatureAngle(25)
            fe.ColoringOff()
            em = vtk.vtkPolyDataMapper()
            em.SetInputConnection(fe.GetOutputPort())
            em.ScalarVisibilityOff()
            em.SetResolveCoincidentTopologyToPolygonOffset()
            em.SetRelativeCoincidentTopologyLineOffsetParameters(0.0, -0.8)      # çizgiler kendi yüzeyinin çok az önünde (20 m'de yaklaşık 5 mm)
            ea = vtk.vtkActor()
            ea.SetMapper(em)
            ea.GetProperty().SetColor(0.16, 0.17, 0.19)
            ea.GetProperty().SetLineWidth(1.6)
            ea.GetProperty().LightingOff()
            cik.append(ea)
        return cik

    def sahne(gizli_sinif=(), gizli_fn=None, mahal=False, etiket=False):
        r = vtk.vtkRenderer()
        r.etiketler = []
        r.SetBackground(1, 1, 1)
        r.SetBackground2(0.86, 0.91, 0.96)
        r.GradientBackgroundOn()
        for sh in sekiller:
            if sh["sinif"] == "IfcOpeningElement" or sh["sinif"] in gizli_sinif or (gizli_fn and gizli_fn(sh)):
                continue
            if sh["sinif"] == "IfcSpace":
                if not mahal:
                    continue
                # mahal hacmi yerine yalnız zemini: tabanındaki üçgenler, işleve göre renkli
                v, fc = sh["v"], sh["f"]
                alt = fc[np.all(np.abs(v[fc][:, :, 2]) < 1e-6, axis=1)]
                if not len(alt):
                    continue
                v2 = v.copy()
                v2[:, 2] += 0.004
                renk = MAHAL_RENGI.get(islev.get(sh["id"], ""), (0.93, 0.93, 0.93))
                for a in aktor({"v": v2, "f": alt, "mid": np.zeros(len(alt), dtype=int), "renk": [renk]}, kenar=False):
                    a.GetProperty().SetAmbient(0.75)
                    a.GetProperty().SetDiffuse(0.3)
                    r.AddActor(a)
                if etiket and sh.get("uzun"):
                    ucg = v[alt]                                  # zemin üçgenlerinin alan ağırlıklı ortası
                    k1, k2 = ucg[:, 1, :2] - ucg[:, 0, :2], ucg[:, 2, :2] - ucg[:, 0, :2]
                    al = 0.5 * np.abs(k1[:, 0] * k2[:, 1] - k1[:, 1] * k2[:, 0])
                    orta = (ucg.mean(axis=1) * al[:, None]).sum(0) / al.sum()
                    r.etiketler.append((sh["uzun"], (float(orta[0]), float(orta[1]), 0.05)))
                continue
            for a in aktor(sh):
                r.AddActor(a)
        # zemin
        zs = vtk.vtkPlaneSource()
        zs.SetOrigin(merkez[0] - cap * 3, merkez[1] - cap * 3, -0.155)
        zs.SetPoint1(merkez[0] + cap * 3, merkez[1] - cap * 3, -0.155)
        zs.SetPoint2(merkez[0] - cap * 3, merkez[1] + cap * 3, -0.155)
        zm = vtk.vtkPolyDataMapper()
        zm.SetInputConnection(zs.GetOutputPort())
        za = vtk.vtkActor()
        za.SetMapper(zm)
        za.GetProperty().SetColor(0.80, 0.84, 0.76)
        za.GetProperty().SetAmbient(0.8)
        za.GetProperty().SetDiffuse(0.25)
        r.AddActor(za)
        # ışık: güneybatıdan, yukarıdan
        r.RemoveAllLights()
        for yon, guc in (((-0.45, -0.75, 1.0), 0.95), ((0.8, 0.35, 0.6), 0.38), ((0.1, 0.9, 0.5), 0.22)):
            L = vtk.vtkLight()
            L.SetLightTypeToSceneLight()
            L.SetPositional(False)
            L.SetPosition(merkez[0] + yon[0] * 100, merkez[1] + yon[1] * 100, merkez[2] + yon[2] * 100)
            L.SetFocalPoint(*merkez)
            L.SetIntensity(guc)
            r.AddLight(L)
        return r

    def kaydet(r, ad, az, el, uzaklik=1.35, hedef_z=1.4, aci=30.0):
        w = vtk.vtkRenderWindow()
        w.SetOffScreenRendering(1)
        w.SetMultiSamples(0)
        w.AddRenderer(r)
        w.SetSize(genislik * 2, yukseklik * 2)             # iki kat çizilir, yarıya küçültülür (kenar yumuşatma)
        cam = r.GetActiveCamera()
        hedef = np.array([merkez[0], merkez[1], hedef_z])
        a, e = math.radians(az), math.radians(el)
        d = cap * uzaklik
        cam.SetFocalPoint(*hedef)
        cam.SetPosition(hedef[0] + d * math.cos(e) * math.cos(a), hedef[1] + d * math.cos(e) * math.sin(a), hedef[2] + d * math.sin(e))
        cam.SetViewUp(0, 0, 1)
        cam.SetViewAngle(aci)
        cam.SetClippingRange(max(0.5, d - cap * 0.9), d + cap * 4)      # yakın düzlem yapıya yakın: derinlik çözünürlüğü yeterli olsun
        try:
            r.UseFXAAOn()
        except Exception:
            pass
        w.Render()
        wf = vtk.vtkWindowToImageFilter()
        wf.SetInput(w)
        wf.Update()
        img = wf.GetOutput()
        dims = img.GetDimensions()
        arr = ns.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(dims[1], dims[0], -1)[::-1, :, :3]
        from PIL import Image, ImageDraw, ImageFont
        im = Image.fromarray(np.ascontiguousarray(arr)).resize((genislik, yukseklik), Image.LANCZOS)
        if getattr(r, "etiketler", None):               # mahal adları: dünya noktası ekrana izdüşürülür, yazı görüntünün üstüne yazılır
            from matplotlib import font_manager
            font = ImageFont.truetype(font_manager.findfont("DejaVu Sans:bold"), 19)
            dr = ImageDraw.Draw(im, "RGBA")
            co = vtk.vtkCoordinate()
            co.SetCoordinateSystemToWorld()
            for metin, nokta in r.etiketler:
                co.SetValue(*nokta)
                px, py = co.GetComputedDoubleDisplayValue(r)
                x, y = px / 2, yukseklik - py / 2
                kutu = dr.textbbox((x, y), metin, font=font, anchor="mm")
                dr.rectangle((kutu[0] - 5, kutu[1] - 3, kutu[2] + 5, kutu[3] + 3), fill=(255, 255, 255, 205))
                dr.text((x, y), metin, font=font, fill=(25, 25, 30, 255), anchor="mm")
        yol = cikti / f"{on_ek}_{ad}.png"
        im.save(yol)
        w.Finalize()
        return yol.name

    cikanlar = []
    r = sahne()
    # az: kameranın yapıya göre yeri (0° doğu, 90° kuzey, 180° batı, 270° güney); ön cephe güneydedir
    for ad, az in (("perspektif_on_sag", 300), ("perspektif_on_sol", 238), ("perspektif_arka_sol", 128), ("perspektif_arka_sag", 52)):
        cikanlar.append(kaydet(r, ad, az, 24))
    cati = lambda sh: sh["sinif"] in ("IfcRoof", "IfcCovering", "IfcElementAssembly", "IfcMember", "IfcPlate") or (sh["sinif"] == "IfcSlab" and sh["tip"] == "ROOF")
    cikanlar.append(kaydet(sahne(gizli_fn=cati, mahal=True, etiket=True), "catisiz", 262, 58, uzaklik=1.3, hedef_z=0.6))
    kaplama = lambda sh: sh["sinif"] == "IfcCovering" or (sh["sinif"] == "IfcSlab" and sh["tip"] == "ROOF") or (sh["sinif"] == "IfcPlate" and sh["ad"].startswith("ALIN"))
    cikanlar.append(kaydet(sahne(gizli_fn=kaplama, mahal=True), "makasli", 300, 38, uzaklik=1.4, hedef_z=1.4))
    return cikanlar


def main() -> int:
    ifc_yol, cikti = Path(sys.argv[1]), Path(sys.argv[2])
    on_ek = sys.argv[3] if len(sys.argv) > 3 else ifc_yol.stem
    cikti.mkdir(parents=True, exist_ok=True)
    f, sekiller = ucgenle(ifc_yol)
    d = denetim(f, sekiller)
    (cikti / f"{on_ek}_geometri.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("geometri:", d["nesne"], "üçgen", d["ucgen"])
    print("yazıldı:", ", ".join(ciz(f, sekiller, cikti, on_ek)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
