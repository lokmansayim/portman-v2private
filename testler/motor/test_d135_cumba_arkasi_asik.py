"""D-135 (BK-62): çapraz cumbada ana çatının aşıkları cumbanın arkasında kesilmez, baştan sona sürer.

Lokman, 20 Kasım 2026 07:12:04 UTC: "ana makasdaki aşıklar cumbanın arkasına gelince kesilmez devam eder çapraz cumbalı yapılarda
örneğin P8501 cumbanın arkasında kalan aşıklar baştan sona kadar devam eder yarım bırakılmaz"; kart 07:20:08 "Eskizdeki gibi, çapraz
cumbalı her eve". Kod `motor/cati_prefabrik.ana_karkasi`; hedef örnek `testler/motor/veri/D135_cumba_arkasi_asik_beklenen.json`
(depodaki her `besik_cumba` İş Emri'nin aşık adedi, önce ve sonra).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from motor import cati_prefabrik as CP
from motor import geometry as G
from motor import prefabrik_liste as PL
from motor.genel import cati_genel

KOK = Path(__file__).resolve().parents[2]
HEDEF = json.loads((KOK / "testler/motor/veri/D135_cumba_arkasi_asik_beklenen.json").read_text(encoding="utf-8"))


def _ie(yol: str) -> dict:
    d = json.loads((KOK / yol).read_text(encoding="utf-8"))
    return d.get("is_emri", d) if isinstance(d.get("is_emri"), dict) else d


def test_p8501_ana_cati_siralari_bastan_sona():
    """85 m² (P8501 r05): ana güney yüzünün her aşık sırası tek parça, yüzün iki saçak ucu arasında (885,75 cm)."""
    ie = _ie("is_emri/P8501_r05.json")
    t = CP.cati(G.kur(ie), ie)
    ana = next(d for d in t["duzlemler"] if d["ad"] == "ana güney")
    yuz = Polygon(ana["plan"])
    assert Polygon(ana["karkas"]).area == pytest.approx(yuz.convex_hull.area)
    ck = cati_genel.cati_kur(t, PL.kurallari_oku()["ortak"])
    siralar = [s for s in ck["asik"]["ana güney"] if s["tur"] == "sira"]
    assert len(siralar) == HEDEF["P8501_r05"]["ana_guney_sira"]
    x0, _, x1, _ = yuz.bounds
    for s in siralar:
        assert s["boy"] == pytest.approx(x1 - x0, abs=0.05), s


def test_gorunen_yuz_ve_kenarlar_aynen():
    """Karkas yalnız aşık sıralarını değiştirir: düzlemin görünen planı, kenarlar ve kalkanlar aynı."""
    ie = _ie("is_emri/P8501_r05.json")
    t = CP.cati(G.kur(ie), ie)
    yalin = dict(t, duzlemler=[{k: v for k, v in d.items() if k != "karkas"} for d in t["duzlemler"]])
    a, b = cati_genel.cati_kur(t), cati_genel.cati_kur(yalin)
    assert [(e["tur"], round(e["boy"], 2)) for e in a["kenarlar"]] == [(e["tur"], round(e["boy"], 2)) for e in b["kenarlar"]]
    assert a["yuzey_m2"] == pytest.approx(b["yuzey_m2"])


def test_cumbasiz_ve_kirma_catida_karkas_yok():
    for d in CP.ana_karkasi([{"ad": "ana güney", "plan": [[0, 0], [10, 0], [10, 10], [0, 10]]}]):
        assert "karkas" not in d


@pytest.mark.parametrize("yol", sorted(HEDEF["asik_adedi"]))
def test_asik_adedi_hedef_ornekle(yol):
    ie = _ie(yol)
    L = PL.liste(PL.model_motor(ie))
    adet = next(s["adet"] for s in L["satirlar"] if s["kalem"] == "Aşık")
    assert adet == HEDEF["asik_adedi"][yol]["sonra"], (yol, adet, HEDEF["asik_adedi"][yol])
