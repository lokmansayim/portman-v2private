"""BK-14 · Dört kollu (+) duvar birleşimi.

İki duvar aynı noktadan geçip orada hiçbir duvar bitmiyorsa Motor önceden ikisini de geçiriyordu: birleşim karesi iki kez doluyor, doğrulama
"Duvar çakışması" diyordu. Şimdi, yalnız yeni anahtarlı İş Emri'nde ve iki iç duvar arasında, kısa olan (cm, bölünmeden önceki boyuyla;
eşitse düşey) o noktada bölünür, iki ucu geçen duvarın yüzünde biter ve uyarı yazılır; yükleme listesi o eki sayar ve uyarır. Kararlar tarama
sırasına ve ek akslara bağlı değil (geometri hakemi, 27 Ekim). Girdi `veri/TK01.json`: bayi çiziminden okunmuş 3+1 (iki banyonun alt duvarı
holün sol duvarıyla + yapar). Bu bir Motor kilididir, paftaya uygunluk kanıtı değildir; birleşimin profili kural kitabında yok.
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


# sentetik 6 × 6: yatay iç duvar (y = 3, x 1 … 5,5) iki düşey iç duvarı (x = 2 boydan boya, x = 4 y 1 … 5) keser
_ODALAR = {"L": [[0, 0, 1, 6]], "P": [[1, 0, 2, 3]], "Q": [[1, 3, 2, 6]], "S": [[2, 0, 4, 3], [4, 0, 5.5, 1]], "T": [[2, 3, 4, 6], [4, 5, 5.5, 6]],
           "U": [[4, 1, 5.5, 3]], "V": [[4, 3, 5.5, 5]], "Z": [[5.5, 0, 6, 6]]}


def _sentetik(odalar: dict, yapi_ek: dict | None = None) -> dict:
    y = {"sistem": "prefabrik", "kat_sayisi": 1, "duvar_yuksekligi_cm": 250, "grid": {"x_pano": 6, "y_pano": 6}, "kisa_kenar": "x"}
    y.update(yapi_ek or {})
    return {"is_emri_no": "S", "revizyon": 1, "yapi": y, "acikliklar": [],
            "mahaller": [{"ad": a, "tur": "yatak_odasi", "konum_pano": r} for a, r in odalar.items()]}


def _ic_duvarlar(plan, ayna_x: bool = False):
    W = plan.W
    out = []
    for d in plan.duvarlar:
        if d.tur != "ic":
            continue
        if d.yon == "x":
            p0, p1 = (W - d.p1, W - d.p0) if ayna_x else (d.p0, d.p1)
            out.append(("x", round(d.c, 2), round(p0, 2), round(p1, 2)))
        else:
            out.append(("y", round(W - d.c if ayna_x else d.c, 2), round(d.p0, 2), round(d.p1, 2)))
    return sorted(out)


def test_arti_birlesim_anahtarsiz_eski_yol():
    plan = G.kur(_sentetik(_ODALAR))
    assert not [u for u in plan.uyarilar if "dört kollu" in u] and not plan.arti_birlesimler


def test_arti_birlesim_aynada_ayni_karar():
    anahtar = {"dizilim": {"baslangic": "on-sol"}}
    ayna = {a: [[6 - r[2], r[1], 6 - r[0], r[3]] for r in rs] for a, rs in _ODALAR.items()}
    p1, p2 = G.kur(_sentetik(_ODALAR, anahtar)), G.kur(_sentetik(ayna, anahtar))
    assert len(p1.arti_birlesimler) == 2 == len(p2.arti_birlesimler)
    # x = 2 (6 pano) ve x = 4 (4 pano) yatayı (4,5 pano) keser: x = 2'de yatay kısa, x = 4'te düşey kısa
    assert _ic_duvarlar(p1) == _ic_duvarlar(p2, ayna_x=True)


def test_arti_birlesim_ek_aks_karari_degistirmez():
    temel = {"dizilim": {"baslangic": "on-sol"}}
    ekli = {"dizilim": {"baslangic": "on-sol"}, "ek_akslar_cm": {"x": [220, 240, 280, 300, 320]}}
    assert _ic_duvarlar(G.kur(_sentetik(_ODALAR, temel))) == _ic_duvarlar(G.kur(_sentetik(_ODALAR, ekli)))


def test_arti_birlesim_listede_uyari():
    from motor import prefabrik_liste as PL
    N = PL.model_motor(_ie())
    assert sum(1 for e in N["ekler"] if e.get("arti")) == 1
