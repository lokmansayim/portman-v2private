"""D-166 (BK-90): dörtomuzda (iki uçlu kırma) uç bandı 1,5 panodan geniş kalır ve uçta duvar yoksa uç duvarın dış yüzünden 125,5 içeride
bir ana makas daha.

Dayanak: Lokman kartı 28 Kasım 2026 10:46:26 UTC "Eskizdeki gibi, aynı durumdaki her evde"; eskiz PF
`Portman_Proje_Dosyalari/Disk_Arsivi/kalan_evler/dortomuz_liste/67m2_dortomuz_makas_once_sonra.png`. Hedef örnek disk arşivi 67 m² 2+1
(verandayı da örten dörtomuz; önce "arka uçta bant ya da kısa makas arası 193,25 cm, 1,5 panodan geniş; liste yazılmaz"); aynı durumdaki
üç havuz evinin kırma seçeneği (60, 84, 62 m²) de yazılır. Beklenen `testler/motor/veri/D166_beklenen.json`.
"""
import copy
import json
from pathlib import Path

import pytest

from motor import geometry as G
from motor import prefabrik_liste as PL

KOK = Path(__file__).resolve().parents[2]
H = json.loads((KOK / "testler" / "motor" / "veri" / "D166_beklenen.json").read_text(encoding="utf-8"))


def _ozet(ie: dict) -> dict:
    m = PL.model_motor(ie)
    L = PL.liste(m)
    k = next(c["kirma_makas"] for c in m["cati"] if c.get("kirma_makas"))
    return {"ana_x_cm": k["ana_x_cm"],
            "uclar": [{x: u[x] for x in ("uc", "bant_cm", "kisa_y_cm", "kisa_boy_cm", "capraz_boy_cm")} for u in k["uclar"]],
            "satirlar": [[r["kalem"], r["olcu"], r["adet"]] for r in L["satirlar"]
                         if r["grup"] == "1005" and r["kalem"].startswith(("Makas", "Çatı paneli"))]}


def test_67m2_dortomuz():
    """Arka uçta yeni ana makas 814,75 (940,25 − 125,5); ana 7, kısa 3 + 5, çapraz 2 + 2, panel 4. Ön uç D-131 aynen (gövde duvarı 245)."""
    ie = json.loads((KOK / "testler" / "motor" / "veri" / "D166_dortomuz_67m2.json").read_text(encoding="utf-8"))
    o = _ozet(ie)
    assert o == H["67m2_2+1"]
    assert o["ana_x_cm"][0] == 245.0 and o["ana_x_cm"][-1] == 814.75 and len(o["ana_x_cm"]) == 7
    assert [u["bant_cm"] for u in o["uclar"]] == [245.0, 125.5]


@pytest.mark.parametrize("kod", sorted(H["havuz_kirma_secenekleri"]))
def test_havuz_kirma_secenegi(kod):
    """Aynı durumdaki havuz evlerinin kırma seçeneği (İE-44 aracının kurduğu çatı) artık yazılır; uç bandı 125,5."""
    from araclar import cati_secenekleri_toplu as T
    h = H["havuz_kirma_secenekleri"][kod]
    ie = json.loads((KOK / h["sablon"]).read_text(encoding="utf-8"))
    s = next(s for s in T.secenekler(ie, G.kur(copy.deepcopy(ie))) if s["harf"] == "K")
    v = copy.deepcopy(ie)
    v["cati"] = s["cati"]
    o = _ozet(v)
    assert o == {k: h[k] for k in ("ana_x_cm", "uclar", "satirlar")}
    assert 125.5 in [u["bant_cm"] for u in o["uclar"]]
