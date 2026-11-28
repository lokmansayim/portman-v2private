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
    # her yarım pano aksı (iç duvarın oturabildiği her yer), Motor'un aks tablosundan
    assert [(a["ad"], a["cm"]) for a in et["aks_x"]] == list(zip("ABCDEFGHI", [5, 67.75, 130.5, 193.25, 256, 318.75, 381.5, 444.25, 495]))
    assert [a["cm"] for a in et["aks_y"]] == [10, 72.75, 135.5, 198.25, 261, 323.75, 386.5]
    assert [(o["etiket"], o["ad"]) for o in et["odalar"]] == [("O1", "SALON+MUTFAK"), ("O2", "WC")]
    assert [(a["etiket"], a["tur"]) for a in et["acikliklar"]] == [("P1", "pencere"), ("K1", "ic_kapi"), ("P2", "pencere")]
    _, et2 = E.ciz(ie, tmp_path / "f.png")
    assert et2 == et


def test_pencere_olcusu_yazilir_kapi_yazilmaz():
    """Lokman kart 28 Kasım 2026 06:25:25 UTC "Etiketin yanında ölçü"; 06:25:31 "kapıyı yazma"."""
    ie = g.denetle(OKUMA)["cevrim"]["is_emri"]
    et = E.etiketler(__import__("motor.geometry", fromlist=["kur"]).kur(ie))
    p = {a["etiket"]: a["olcu_yazi"] for a in et["acikliklar"]}
    assert p["P1"] == "60/40" and p["P2"] == "300/200"
