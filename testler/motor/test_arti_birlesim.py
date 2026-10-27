"""BK-14 · Dört kollu (+) duvar birleşimi.

İki duvar aynı noktadan geçip orada hiçbir duvar bitmiyorsa Motor önceden ikisini de geçiriyordu: birleşim karesi iki kez doluyor, doğrulama
"Duvar çakışması" diyordu. Şimdi kısa olan (eşitse düşey; dış duvar her zaman geçer) o noktada ikiye bölünür, iki ucu geçen duvarın yüzünde
biter ve uyarı yazılır. Girdi `veri/TK01.json`: bayi çiziminden okunmuş 3+1 (iki banyonun alt duvarı holün sol duvarıyla + yapar).
Bu bir Motor kilididir, paftaya uygunluk kanıtı değildir; birleşimin profili kural kitabında yok (uyarı bunu söyler).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G  # noqa: E402

TK01 = KOK / "testler" / "motor" / "veri" / "TK01.json"


def _ie() -> dict:
    return json.loads(TK01.read_text(encoding="utf-8"))


def test_arti_birlesim_kisa_duvar_bolunur():
    plan = G.kur(_ie())
    arti = [u for u in plan.uyarilar if "dört kollu birleşim" in u]
    assert len(arti) == 1, plan.uyarilar
    y256 = [d for d in plan.duvarlar if d.yon == "x" and abs(d.c - (plan.H - 256.0)) < 1e-6]   # arka-sol: y arkadan, plan aynalı
    x386 = [d for d in plan.duvarlar if d.yon == "y" and abs(d.c - 386.5) < 1e-6]
    assert len(y256) == 2 and len(x386) == 1                     # kısa yatay duvar ikiye bölündü, uzun düşey geçer
    a, b = sorted(y256, key=lambda d: d.p0)
    assert abs(a.p1 - (386.5 - G.T_IC / 2)) < 1e-6 and abs(b.p0 - (386.5 + G.T_IC / 2)) < 1e-6   # uçlar geçen duvarın yüzünde


def test_arti_birlesim_dogrulamadan_gecer(tmp_path):
    m = dxf_out.uret(_ie(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("errors") or m.get("warnings")


def test_arti_birlesimsiz_plan_degismez():
    plan = G.kur(json.loads((KOK / "testler" / "motor" / "veri" / "PK01.json").read_text(encoding="utf-8")))
    assert not [u for u in plan.uyarilar if "dört kollu" in u]
