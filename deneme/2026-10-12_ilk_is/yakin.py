#!/usr/bin/env python3
"""Yakın plan denetim görüntüsü: IFC'yi perspektif.py ile aynı biçimde üçgenler, verilen kamera konumu ve hedefiyle çizer.
Kullanım: python yakin.py model.ifc cikti.png kx ky kz hx hy hz [aci] [gizle]
  k: kamera (m), h: hedef (m), aci: görüş açısı (derece), gizle: virgülle sınıf adları (ör. IfcCovering) — denetimde arkayı görmek için.
Teslim edilmez; yalnız denetim içindir.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "2026-10-06_kor_test"))   # perspektif.py yamada değişmedi
from perspektif import ucgenle  # noqa: E402


def main():
    ifc, cikti = Path(sys.argv[1]), Path(sys.argv[2])
    k = [float(v) for v in sys.argv[3:6]]
    h = [float(v) for v in sys.argv[6:9]]
    aci = float(sys.argv[9]) if len(sys.argv) > 9 else 30.0
    gizle = set(sys.argv[10].split(",")) if len(sys.argv) > 10 and sys.argv[10] else set()
    import vtk
    from vtk.util import numpy_support as ns
    from PIL import Image
    f, sekiller = ucgenle(ifc)
    r = vtk.vtkRenderer()
    r.SetBackground(1.0, 0.3, 0.9)          # boşluk varsa arka plan pembe görünür
    for sh in sekiller:
        if sh["sinif"] in ("IfcSpace", "IfcOpeningElement") or sh["sinif"] in gizle:
            continue
        v, fc = sh["v"], sh["f"]
        pd = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.SetData(ns.numpy_to_vtk(v, deep=True))
        pd.SetPoints(pts)
        hucre = np.hstack([np.full((len(fc), 1), 3), fc]).astype(np.int64).ravel()
        ca = vtk.vtkCellArray()
        ca.ImportLegacyFormat(ns.numpy_to_vtkIdTypeArray(hucre, deep=True))
        pd.SetPolys(ca)
        renk = np.zeros((len(fc), 3), dtype=np.uint8)
        for i in range(len(fc)):
            mi = sh["mid"][i] if i < len(sh["mid"]) else 0
            c = sh["renk"][mi] if 0 <= mi < len(sh["renk"]) else (0.7, 0.7, 0.7)
            renk[i] = [int(255 * max(0.0, min(1.0, x))) for x in c]
        arr = ns.numpy_to_vtk(renk, deep=True)
        arr.SetNumberOfComponents(3)
        pd.GetCellData().SetScalars(arr)
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        m.SetScalarModeToUseCellData()
        a = vtk.vtkActor()
        a.SetMapper(m)
        p = a.GetProperty()
        p.SetInterpolationToFlat()
        p.SetAmbient(0.42)
        p.SetDiffuse(0.62)
        r.AddActor(a)
        fe = vtk.vtkFeatureEdges()
        fe.SetInputData(pd)
        fe.BoundaryEdgesOn(); fe.FeatureEdgesOn(); fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff()
        fe.SetFeatureAngle(25)
        fe.ColoringOff()
        em = vtk.vtkPolyDataMapper()
        em.SetInputConnection(fe.GetOutputPort())
        em.ScalarVisibilityOff()
        ea = vtk.vtkActor()
        ea.SetMapper(em)
        ea.GetProperty().SetColor(0.16, 0.17, 0.19)
        ea.GetProperty().LightingOff()
        r.AddActor(ea)
    w = vtk.vtkRenderWindow()
    w.SetOffScreenRendering(1)
    w.AddRenderer(r)
    w.SetSize(1600, 1100)
    cam = r.GetActiveCamera()
    cam.SetFocalPoint(*h)
    cam.SetPosition(*k)
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(aci)
    r.ResetCameraClippingRange()
    w.Render()
    wf = vtk.vtkWindowToImageFilter()
    wf.SetInput(w)
    wf.Update()
    img = wf.GetOutput()
    d = img.GetDimensions()
    arr = ns.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(d[1], d[0], -1)[::-1, :, :3]
    im = Image.fromarray(np.ascontiguousarray(arr)).resize((800, 550), Image.LANCZOS)
    im.save(cikti)
    pembe = ((arr[:, :, 0] > 230) & (arr[:, :, 1] < 110) & (arr[:, :, 2] > 200)).sum()
    print(cikti.name, "pembe piksel:", int(pembe))
    w.Finalize()


if __name__ == "__main__":
    main()
