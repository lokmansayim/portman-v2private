#!/usr/bin/env python3
"""PORTMAN · perspektif denemesi (BK-07 S1): VTK bu sunucuda EKRANSIZ çizebiliyor mu? Küçük bir küp çizilir, PNG'ye yazılır.
vps/guncelle.sh [3b] adımında sürümün venv python'uyla AYRI SÜREÇTE ve timeout ile çağrılır; sonucu ne olursa olsun sürüm etkinleşir
(Lokman 11.10: olmazsa pilot perspektifsiz). Ayrı süreç şart: OSMesa/EGL yoksa VTK uyarı değil segfault verir (bulut kabı, 12.10).
Perspektif kodu (ie-05 perspektif.py) bu işte alınmaz; burada yalnız "çizebilir mi" kanıtlanır.
Çıktı tek satır: "TAMAM (…)" ya da "ÇİZİLEMEDİ (<neden>)". Çıkış kodu: 0 TAMAM, 2 VTK yok, 3 çizilemedi; segfault 139 (guncelle.sh yorumlar).
    python vps/perspektif_dene.py [çıktı_dizini]
"""
from __future__ import annotations

import os
import sys
import tempfile


def main(argv: list[str]) -> int:
    hedef = argv[1] if len(argv) > 1 else tempfile.gettempdir()
    try:
        import vtk                                                           # noqa: F401
    except Exception as e:                                                   # paket yok ya da .so eksik
        print(f"ÇİZİLEMEDİ (VTK içe aktarılamadı: {type(e).__name__}: {str(e)[:120]})"); return 2
    surum = vtk.vtkVersion.GetVTKVersion()
    # Uyarılar stderr'e gider (guncelle.sh yalnız stdout'un son satırını okur); ekranı kirletmesin diye kısaltılır
    vtk.vtkObject.GlobalWarningDisplayOff()
    try:
        pencere = vtk.vtkRenderWindow(); pencere.SetOffScreenRendering(1); pencere.SetSize(320, 240)
        sinif = pencere.GetClassName()
        ren = vtk.vtkRenderer(); ren.SetBackground(1.0, 1.0, 1.0); pencere.AddRenderer(ren)
        kup = vtk.vtkCubeSource(); kup.SetXLength(6.0); kup.SetYLength(8.0); kup.SetZLength(2.8)
        m = vtk.vtkPolyDataMapper(); m.SetInputConnection(kup.GetOutputPort())
        a = vtk.vtkActor(); a.SetMapper(m); a.GetProperty().SetColor(0.85, 0.85, 0.80); a.GetProperty().EdgeVisibilityOn()
        ren.AddActor(a); ren.ResetCamera(); ren.GetActiveCamera().Elevation(25); ren.GetActiveCamera().Azimuth(35); ren.ResetCamera()
        pencere.Render()
        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(pencere); w2i.Update()
        yol = os.path.join(hedef, "portman_perspektif_dene.png")
        y = vtk.vtkPNGWriter(); y.SetFileName(yol); y.SetInputConnection(w2i.GetOutputPort()); y.Write()
        boyut = os.path.getsize(yol) if os.path.exists(yol) else 0
        if boyut < 200:
            print(f"ÇİZİLEMEDİ (VTK {surum}; PNG boş ya da çok küçük: {boyut} bayt; pencere {sinif})"); return 3
        print(f"TAMAM (VTK {surum} ekransız çizim; 320×240 PNG {boyut} bayt; pencere {sinif})"); return 0
    except Exception as e:
        print(f"ÇİZİLEMEDİ (VTK {surum}; {type(e).__name__}: {str(e)[:120]})"); return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
