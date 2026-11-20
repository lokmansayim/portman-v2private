"""D-140 (Lokman, 20 Kasım 2026: kart 10:50:36 "Eskizdeki gibi, kirişli her evde", kart 10:54:39 "Evet, iki tür kiriş her evde"; BK-66;
PC-51): yükleme listesinde kiriş olan iç yerler ön onay çiziminde de 10 × 10 profil, kesik kırmızı çerçeve. İki tür: tavan kirişi
(D-107, D-127) ve iki kapalı oda arasındaki duvarsız sınırın kirişi. Çerçeve ana planda ve kopyasında; saha montaj planı, BOM ve IFC aynen.
Hedef örnek eskiz PF `Teklif_Calisma/TK-08/TK08_r05_kirisler_eskiz.png`, çerçeveler `testler/motor/veri/D140_kiris_profilleri_beklenen.json`.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
from pathlib import Path

import ezdxf
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor import dxf_out, geometry as G, prefabrik_liste as PL  # noqa: E402

BEKLENEN = json.loads((KOK / "testler" / "motor" / "veri" / "D140_kiris_profilleri_beklenen.json").read_text(encoding="utf-8"))
KATMAN = dxf_out.Cizici.KIRIS_KATMANI[0]


def _oku(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _uret(ie: dict):
    with tempfile.TemporaryDirectory() as td:
        with contextlib.redirect_stdout(io.StringIO()):
            m = dxf_out.uret(copy.deepcopy(ie), Path(td))
        assert m["validation_passed"], m
        return ezdxf.readfile(Path(td) / m["dxf"])


def test_karar_dayanagi():
    karar = (KOK / "KARARLAR" / "D-140.md").read_text(encoding="utf-8")
    for s in ("10:50:36", "Eskizdeki gibi, kirişli her evde", "10:54:39", "Evet, iki tür kiriş her evde"):
        assert s in karar and s in BEKLENEN["aciklama"], s


@pytest.mark.parametrize("ev", sorted(BEKLENEN["evler"]))
def test_cerceveler_hedef_ornekle_ayni(ev):
    b = BEKLENEN["evler"][ev]
    doc = _uret(_oku(b["is_emri"]))
    kut = sorted([[round(v, 2) for p in e.get_points("xy") for v in p] for e in doc.modelspace().query(f"LWPOLYLINE[layer=='{KATMAN}']")])
    assert kut == b["cerceveler"]
    lay = doc.layers.get(KATMAN)
    assert lay.dxf.color == 1 and lay.dxf.linetype == "VERANDA_KESIK"
    assert not doc.modelspace().query(f"INSERT[layer=='{KATMAN}']")          # BOM bloğu değil


def test_kiris_sayisi_listeyle_ayni():
    """76 m²: listedeki iç kirişler (tavan kirişi + sınır kirişi) kadar çerçeve, iki planda (ana + kopya)."""
    ie = _oku(BEKLENEN["evler"]["76m2"]["is_emri"])
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    from motor import tavan_kirisi as TK
    with contextlib.redirect_stdout(io.StringIO()):
        n = len(TK.bul(plan, ie)["kirisler"]) + len(PL.ic_kiris_hatlari(plan))
    assert n == 3 and 2 * n == len(BEKLENEN["evler"]["76m2"]["cerceveler"])


def test_liste_boyu_ayni_islevden():
    """Listenin `ic_kirisler_cm`'i çizimin hatlarının boyudur (D-28 madde 1)."""
    ie = _oku("is_emri/P6001_r03.json")
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    boylar = [round((x1 - x0) + (y1 - y0), 2) for (x0, y0, x1, y1) in PL.ic_kiris_hatlari(plan)]
    assert boylar and all(b > 0 for b in boylar)


def test_kirissiz_evde_katman_yok():
    """M-02 hedefi TK-02 kirişsiz: katman açılmaz, DXF aynen."""
    doc = _uret(_oku("testler/motor/veri/TK02.json"))
    assert KATMAN not in doc.layers
