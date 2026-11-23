"""BK-72 (D-150; Lokman, kart 23 Kasım 2026 12:40:09 UTC "Dördü de, sırayla"): okuyucunun ölçü kuralları.
Kural 1: ızgaranın sonunda 20 cm'den kısa pano kalan dış ölçü sorulmaz, kısa uç kesilir (TK-04 kroki 9,00 → onaylı 8,885; TK-09 6,50 → 6,475).
Kural 4: zincir ile toplamın eşik içindeki farkı sorulmaz; tek parçalı toplamsız ölçü zincir sayılmaz; aynı soru bir kez gider."""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from beyin import gorsel_okuma as GO  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"


def _okuma(ad: str) -> dict:
    return json.loads((VERI / f"BK70_{ad}_okuma.json").read_text(encoding="utf-8"))


def test_kural1_onayli_planlarin_olcusu():
    W, H, notlar = GO.izgaraya_oturt(900, 1000, "y")
    assert (W, H) == (888.5, 1000)
    assert "9,00 m yerine 8,885 m" in notlar[0]
    W, H, _ = GO.izgaraya_oturt(650, 700, "x")
    assert W == 647.5


def test_kural1_oturan_olcu_degismez():
    assert GO.izgaraya_oturt(888.5, 898.5, "x") is None or GO._izgara(888.5, 898.5, "x")[4]
    for W, H, m in ((800, 1088, "x"), (950, 640, "y")):
        if not GO._izgara(W, H, m)[4]:
            assert GO.izgaraya_oturt(W, H, m) is None


def test_kural1_kisa_uc_sorusu_bayiye_gitmez():
    o = _okuma("TK09")
    den = GO.denetle({**o, "emin_olunamayanlar": []})
    assert not any("pano kalıyor" in s for s in den["sorular"])


def test_kural4_kucuk_zincir_farki_sorusu_dusur():
    o = _okuma("TK01")
    o = {**o, "zincirler": [{"kenar": "ust", "olculer_cm": [261, 126, 188, 324], "toplam_cm": 898, "kapsam": "govde"}],
         "emin_olunamayanlar": ["Üst ölçü zinciri 261+126+188+324=899 ediyor, toplam 898 yazıyor; hangi parça 1 cm eksik?",
                                "Salon penceresinin ölçüsü ne?"]}
    den = GO.denetle(o)
    assert not any("899" in s for s in den["sorular"])
    assert "Salon penceresinin ölçüsü ne?" in den["sorular"]
    assert any("küçük farkla" in n for n in den["notlar"])


def test_kural4_buyuk_zincir_farki_sorulur():
    o = _okuma("TK01")
    o = {**o, "zincirler": [{"kenar": "ust", "olculer_cm": [261, 126, 188, 330], "toplam_cm": 898, "kapsam": "govde"}],
         "emin_olunamayanlar": []}
    assert any("ölçü zinciri" in s for s in GO.denetle(o)["sorular"])


def test_kural4_tek_parcali_olcu_zincir_sayilmaz():
    o = _okuma("TK01")
    o = {**o, "zincirler": [{"kenar": "sol", "olculer_cm": [624.5], "kapsam": "govde"}], "emin_olunamayanlar": []}
    assert not any("ölçü zinciri" in s for s in GO.denetle(o)["sorular"])


def test_ayni_soru_bir_kez():
    o = _okuma("TK01")
    o = {**o, "emin_olunamayanlar": ["Banyo penceresi kaç cm?", "Banyo penceresi kaç cm?"]}
    den = GO.denetle(o)
    assert den["sorular"].count("Banyo penceresi kaç cm?") == 1
