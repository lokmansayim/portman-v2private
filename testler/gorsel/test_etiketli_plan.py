"""Etiketli plan (Lokman, kart 28 Kasım 2026 05:55:38 UTC "Doğru, böyle kodla"): adlar plandan, her seferinde aynı."""
import json
from pathlib import Path

from beyin import etiketli_plan as E
from beyin import gorsel_okuma as g

OKUMA = json.loads((Path(__file__).parent / "veri" / "DONGU2_kroki_4x5_okuma.json").read_text(encoding="utf-8"))


def test_4x5_etiketleri(tmp_path):
    ie = g.denetle(OKUMA)["cevrim"]["is_emri"]
    yol, et = E.ciz(ie, tmp_path / "e.png")
    assert yol.is_file() and yol.stat().st_size > 10_000
    assert [a["ad"] for a in et["aks_x"]] == list("ABCDEFG")
    assert [a["ad"] for a in et["aks_y"]] == ["1", "2", "3", "4"]
    assert [(o["etiket"], o["ad"]) for o in et["odalar"]] == [("O1", "SALON+MUTFAK"), ("O2", "WC")]
    assert [(a["etiket"], a["tur"]) for a in et["acikliklar"]] == [("P1", "pencere"), ("K1", "ic_kapi"), ("P2", "pencere")]
    _, et2 = E.ciz(ie, tmp_path / "f.png")
    assert et2 == et
