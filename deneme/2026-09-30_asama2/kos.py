"""Aşama 2 · 90 m² civarı 3+1 adaylarının kaynak–geometri karşılaştırmasını yeniden üretir (30.09.2026).

Rapor: docs/raporlar/2026-09-30_Asama2_3arti1_Aday_Karsilastirmasi.md

Depo koduna dokunmaz. Her aday için:
  1. çıkarıcı → İş Emri → Motor v1.1 (plan DXF/PDF, BOM, validation.json), bugünkü zincir değiştirilmeden;
  2. kaynak görseli: katalog DXF'inde planın paftası, çıkarıcıyla aynı bölge (<kod>_kaynak.png)
     ve çıkarıcının tanı görseli (<kod>_tani.png);
  3. --ifc ile verilen adaylar için aynı İş Emri'nden IFC4. 23.09 deneme kodu (deneme/2026-09-23) geçici bir
     klasörde tek `cozumleyici` paketinde birleştirilir; Motor yamasızdır (serbest aks YOK).

Kaynaktaki kapı ve pencere sayıları görüntüden elle sayıldı (rapor §2); bu betik yalnız Motor tarafını özetler.
Motor'un "passed" sonucu kaynağa uygunluk DEĞİLDİR (rapor, K-A9).

Kullanım (depo kökünde):
    python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör>
    python3 deneme/2026-09-30_asama2/kos.py --cikti <klasör> --kodlar P9401 --ifc P9401

Gerekenler: Python 3.11, ezdxf 1.4.4, matplotlib, shapely, numpy, pillow, pymupdf; IFC için ifcopenshell 0.8.5.
Ağ, LLM, WhatsApp ya da canlı sunucu kullanılmaz.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
D23 = KOK / "deneme" / "2026-09-23"
DXF = KOK / "ref_katalog" / "TEK_KAT_PREFABRIK_PLANLARI.dxf"
PY = sys.executable
ADAYLAR = ["P9401", "P9201", "P9501", "P1051", "P1121"]


def kos(komut: list[str], cwd: Path, gunluk: Path | None = None) -> int:
    env = {**os.environ, "PYTHONPATH": str(cwd)}
    r = subprocess.run(komut, cwd=cwd, env=env, capture_output=True, text=True)
    if gunluk:
        gunluk.write_text(r.stdout + r.stderr, encoding="utf-8")
    if r.returncode:
        print(f"   HATA ({r.returncode}): {' '.join(komut[:4])} …\n{(r.stderr or r.stdout)[-1500:]}")
    return r.returncode


def kaynak_gorseli(kodlar: list[str], cikti: Path) -> None:
    """Katalog DXF'indeki paftayı (ham çizgi, kapı yayları, yazılar) ve çıkarıcının tanı görselini PNG'ye çizer."""
    sys.path.insert(0, str(KOK))
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy
    from motor.cikarici import Cikarici, tani_png
    for kod in kodlar:
        cik = Cikarici(str(DXF), plan_secici=kod)
        ie = cik.calistir(kod)
        tani_png(cik, ie, cikti / f"{kod}_tani.png")
        x0, y0, x1, y1 = cik._plan_bolgesi()
        fig = plt.figure(figsize=(12, 12 * (y1 - y0) / (x1 - x0)))
        ax = fig.add_axes([0, 0, 1, 1])
        # Beyaz zemin şart: renk 7 (beyaz/siyah) çizgiler aksi hâlde beyaz üstüne beyaz çıkar (P9201'de duvarlar görünmüyordu).
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE, min_lineweight=0.4)
        Frontend(RenderContext(cik.doc), MatplotlibBackend(ax), config=cfg).draw_layout(cik.msp, finalize=False)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")
        fig.savefig(cikti / f"{kod}_kaynak.png", dpi=110, facecolor="white"); plt.close(fig)


def ifc_paketi(t: Path) -> Path:
    """23.09 betiklerini depo kopyasında tek `cozumleyici` paketinde birleştirir (yeniden_kos.py ile aynı düzen, yamasız)."""
    W = t / "is"
    atla = {".git", "cikti", "deneme", "testler", "venv", "SHA256SUMS", "KARARLAR", "DURUM.md"}
    shutil.copytree(KOK, W, ignore=lambda d, a: [x for x in a if (Path(d).resolve() == KOK and x in atla) or x in {"__pycache__", ".git"}])
    pk = W / "cozumleyici"; pk.mkdir()
    for kaynak in ["10_Cozumleyici/kod/cozumleyici", "11_Blender/kod", "13_Kiyas/kod"]:
        for f in (D23 / kaynak).glob("*.py"):
            shutil.copy(f, pk / f.name)
    return W


def ozet(kod: str, klasor: Path) -> str:
    v = json.loads((klasor / "motor" / "validation.json").read_text(encoding="utf-8"))
    odalar = ", ".join(f"{k} {round(m, 2)}" for k, m in (v.get("rooms_m2") or {}).items())
    return (f"{kod}: Motor doğrulaması {'geçti' if v.get('passed') else 'GEÇMEDİ'} (kaynağa uygunluk değil) · dış {v.get('outer_cm')} cm · "
            f"pano {v.get('panel_count')} · pencere {v.get('windows')} · kapı {v.get('doors')} · odalar: {odalar}")


def ifc_ozet(kod: str, yol: Path) -> str:
    """IFC sınıf sayıları ve şema doğrulaması (şema doğrulaması üretim doğruluğu değildir)."""
    import ifcopenshell, ifcopenshell.validate
    m = ifcopenshell.open(str(yol))
    say = {s: len(m.by_type(s)) for s in ("IfcWall", "IfcWindow", "IfcDoor", "IfcSpace", "IfcOpeningElement")}
    kayit = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(m, kayit)
    hata = sum(1 for s in kayit.statements if str(s.get("level")).lower() == "error")   # 0.8.5: düzey "error"
    return f"{kod} IFC: " + " · ".join(f"{k} {v}" for k, v in say.items()) + f" · şema hatası {hata}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", required=True, type=Path)
    ap.add_argument("--kodlar", nargs="+", default=ADAYLAR)
    ap.add_argument("--ifc", nargs="*", default=["P9401", "P9201"], help="IFC üretilecek adaylar (boş: IFC yok)")
    a = ap.parse_args()
    c = a.cikti.resolve(); c.mkdir(parents=True, exist_ok=True)
    satirlar = []
    for kod in a.kodlar:
        k = c / "cikarici" / kod
        print(f"-- {kod}: çıkarıcı → İş Emri → Motor")
        if kos([PY, "-m", "motor.cikarici", str(DXF), "--secici", kod, "--kod", kod, "--cikti", str(k), "--motor"], KOK, c / f"{kod}.log"):
            return 1
        satirlar.append(ozet(kod, k))
    print("-- kaynak ve tanı görselleri")
    kaynak_gorseli(a.kodlar, c)
    if a.ifc:
        with tempfile.TemporaryDirectory() as t:
            W = ifc_paketi(Path(t))
            for kod in a.ifc:
                print(f"-- {kod}: aynı İş Emri'nden IFC4")
                ie = c / "cikarici" / kod / "is_emri.json"
                if kos([PY, "-m", "cozumleyici.motor_girdi", str(ie), str(c / f"{kod}.motor_girdi.json")], W):
                    return 1
                # Başlık verilmeli: ifc_uret.py'nin varsayılan başlığı 23.09 bayi planının adını taşır.
                if kos([PY, "-m", "cozumleyici.ifc_uret", str(c / f"{kod}.motor_girdi.json"), str(c / f"{kod}.ifc"),
                        f"Portman — KATALOG {kod} (Aşama 2 adayı)"], W, c / f"{kod}.ifc.log"):
                    return 1
                satirlar.append(ifc_ozet(kod, c / f"{kod}.ifc"))
    (c / "ozet.txt").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print("\n".join(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
