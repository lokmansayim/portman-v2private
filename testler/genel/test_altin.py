"""İE-08 GM1/GM3 · altın test: Ç8801 (katalog) ana koddaki paketle, kural seti 0.19 pimiyle çizilir; plan PNG, liste JSON ve IFC izi
`modeller/altin.json` ile aynı; çizim seti tam (perspektifsiz 7/14), IFC şema hatası 0, liste 93 satır; bayi görseli ≤ 5 MB; şablon
paftası 2 sayfa A4 yatay. Asıl referans `testler/referans/` zinciridir (D-02, D-08); bu test paketin kendi başına çalıştığını söyler."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import iz, uret  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
PERSPEKTIF = ["C8801_perspektif_on_sag.png", "C8801_perspektif_on_sol.png", "C8801_perspektif_arka_sol.png", "C8801_perspektif_arka_sag.png",
              "C8801_catisiz.png", "C8801_makasli.png", "C8801_geometri.json"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def c8801(tmp_path_factory):
    hedef = tmp_path_factory.mktemp("c8801")
    m = uret.uret(KOK / "modeller" / "C8801.json", hedef, is_emri_no="TEST-ALTIN", revizyon=1, set_yolu=SET, yontem="panel", perspektif=False, bayi=True)
    return hedef, m, json.loads((hedef / "validation.json").read_text(encoding="utf-8"))


def test_c8801_altin_degerlerle_ayni(c8801):
    hedef, m, v = c8801
    altin = json.loads((KOK / "modeller" / "altin.json").read_text(encoding="utf-8"))["C8801"]
    assert m["passed"] and v["passed"] and v["errors"] == [], v["errors"]
    assert v["ifc"]["sema_hatasi"] == 0 and v["liste_satir"] == 93
    assert sha(hedef / "C8801_plan.png") == altin["plan_png_sha256"]
    assert sha(hedef / "C8801_yukleme.json") == altin["yukleme_json_sha256"]
    assert iz.ifc_izi(hedef / "C8801.ifc") == altin["ifc_izi"]
    assert v["set"].endswith("setler/0.19.json")


def test_c8801_cizim_seti_tam_perspektif_haric(c8801):
    hedef, m, v = c8801
    assert v["ciktilar"]["beklenen"] == 14 and v["ciktilar"]["var"] == 7 and v["ciktilar"]["zorunlu_eksik"] == []
    assert sorted(v["ciktilar"]["eksik"]) == sorted(PERSPEKTIF)
    assert v["perspektif"]["durum"] == "ATLANDI"
    for ad in ("C8801_plan.png", "C8801_gorunusler.png", "C8801_pafta.png", "C8801.ifc", "C8801.ozet.json", "C8801_yukleme.json", "C8801_yukleme.md"):
        assert (hedef / ad).stat().st_size > 0, ad


def test_c8801_bayi_ciktilari(c8801):
    hedef, m, v = c8801
    bayi = hedef / "C8801_plan_bayi.png"; pdf = hedef / "C8801_pafta.pdf"
    assert bayi.exists() and bayi.stat().st_size <= 5 * 1024 * 1024 and Path(m["plan_bayi"]).name == bayi.name
    assert pdf.exists() and Path(m["pdf"]).name == pdf.name and m["pdf_sha256"] == sha(pdf)
    import fitz
    with fitz.open(pdf) as d:
        assert len(d) == 2 and (round(d[0].rect.width), round(d[0].rect.height)) == (842, 595)
    assert (hedef / "C8801_pafta_sablon.png").exists() and (hedef / "C8801_pafta_ozet.json").exists()
