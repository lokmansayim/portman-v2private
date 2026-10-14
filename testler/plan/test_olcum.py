"""İE-14 r3 · P6 (M1–M5): kör üretim ölçümü LLM'siz; program modelin kendisinden, model kaynaktan ve örnekten dışlanır."""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))
import plan_dene as PD  # noqa: E402


def test_kor_programi_modelden():
    p, t = PD.kor_programi("Ç8801", "C8801")
    assert (p["yatak"], p["alan_m2"], p["mutfak"], p["banyo"], p["cati_tipi"]) == (2, 88.0, "ayri", 1, "besik")
    assert p["veranda"]["istiyor"] and p["veranda"]["konum"] == "kose" and t["kod"] == "Ç8801"


def test_kor_olcum_model_dislanir_ve_olcer():
    s = PD.kor_olc("Ç8201", "C8201")
    assert s["gecti"] and s.get("kaynak") != "Ç8201"                       # kendi planı kaynak olamaz
    assert abs(s["brut_fark_yuzde"]) <= 10 and s["duvar_m"][0] > 0 and len(s["pencere_kapi"]) == 2
    assert "Geometri: geçti" in s["dogrulama"]


def test_rapor_hedef_koymaz():
    s = PD.kor_olc("Ç8201", "C8201")
    r = PD.rapor([s], [])
    assert "Hedef yok" in r and "| Ç8201 | evet |" in r
