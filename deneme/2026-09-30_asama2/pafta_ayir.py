"""Katalog DXF'inden tek bir planın paftasını ayrı bir DXF'e çıkarır (katmanlar, bloklar ve yazılar korunur).

Amaç: bir adayın kaynak çizimini tek başına vermek (ör. Astra'ya çizim işi, Ubeydullah kabulü) ve dış çizim yolunu
(kos.py --dxf) sınamak. Bölge, çıkarıcının kullandığı pafta bölgesidir (Cikarici._plan_bolgesi); merkezi bölgenin
içinde kalan her varlık alınır. Geometri değişmez; koordinatlar kaynaktaki gibidir.

    python3 deneme/2026-09-30_asama2/pafta_ayir.py --cikti <klasör> P9401 P9201

Gerekenler: ezdxf 1.4.4. Girdi yalnız katalog DXF'i; kişisel veri içermez.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

import ezdxf
from ezdxf import bbox, xref

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.cikarici import Cikarici  # noqa: E402

DXF = KOK / "ref_katalog" / "TEK_KAT_PREFABRIK_PLANLARI.dxf"


def ayir(kod: str, hedef: Path) -> tuple[int, tuple]:
    cik = Cikarici(str(DXF), plan_secici=kod)
    x0, y0, x1, y1 = cik._plan_bolgesi()
    kaynak = cik.doc
    secilen = set()
    for e in kaynak.modelspace():
        kutu = bbox.extents([e], fast=False)      # fast=False: ölçü (DIMENSION) kutuları da hesaplanır
        if not kutu.has_data:
            continue
        # Varlığın tamamı bölgede olmalı: paftayı çevreleyen çerçeve gibi taşan çizgiler alınmaz.
        if kutu.extmin.x >= x0 and kutu.extmax.x <= x1 and kutu.extmin.y >= y0 and kutu.extmax.y <= y1:
            secilen.add(e.dxf.handle)
    yeni = ezdxf.new(dxfversion=kaynak.dxfversion, units=kaynak.units)
    # xref, katmanları, blokları ve ölçülerin anonim bloklarını birlikte taşır.
    xref.load_modelspace(kaynak, yeni, filter_fn=lambda e: e.dxf.handle in secilen)
    yeni.saveas(hedef)
    return len(secilen), (round(x0), round(y0), round(x1), round(y1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kodlar", nargs="+")
    ap.add_argument("--cikti", required=True, type=Path)
    a = ap.parse_args()
    a.cikti.mkdir(parents=True, exist_ok=True)
    for kod in a.kodlar:
        n, bolge = ayir(kod, a.cikti / f"{kod}_kaynak.dxf")
        print(f"{kod}: {n} varlık · bölge {bolge} → {a.cikti / f'{kod}_kaynak.dxf'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
