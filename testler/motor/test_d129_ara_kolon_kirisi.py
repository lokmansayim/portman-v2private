"""D-129 (BK-59; Lokman, kart 19 Kasım 2026 21:39:45 "Eskizdeki gibi, yüzden yüze"): gövdedeki açık mahalin (ana çatının örttüğü
veranda) açık kenarında ara kolon varsa kiriş ara kolonlarda bölünür, her parça kolonun yüzünden yüzüne.

Hedef örnek: 110 m² 3+1 disk arşivi evi (HD-380), veranda gövdeye alınmış (`testler/motor/veri/D129_veranda_110m2.json`); eskiz PF
`Disk_Arsivi/parti2/motor_bakim/eskiz/110m2_on_kiris_once_sonra.png`. Ara kolonsuz kenar bugünkü yoldan (tek parça) gider."""
import copy
import json
from collections import Counter
from pathlib import Path

from motor import prefabrik_liste as PL

VERI = Path(__file__).parent / "veri"
KIRIS = "Kutu profil (kiriş) 100 × 100"


def _ie(ad):
    return json.loads((VERI / ad).read_text(encoding="utf-8"))


def _kirisler(ie):
    N = PL.model_motor(copy.deepcopy(ie))
    L = PL.liste(N, PL.kurallari_oku(), None)
    return N, Counter(x["olcu"] for x in L["satirlar"] if x["kalem"] == KIRIS), L


def test_kenar_parcalari_yuzden_yuze():
    kolonlar = [(0, 0, 10, 10), (333, 0, 343, 10), (671, 0, 681, 10), (1004, 0, 1014, 10)]
    assert PL._kenar_parcalari(kolonlar, "x", 0.0, 0.0, 1014.0) == [323.0, 328.0, 323.0]
    # köşede kolon yoksa parça kenarın ucundan (tek kolonlu kenar gibi)
    assert PL._kenar_parcalari(kolonlar[1:3], "x", 0.0, 0.0, 1014.0) == [333.0, 328.0, 333.0]
    # ara kolon yoksa boş: kenar bugünkü yoldan
    assert PL._kenar_parcalari([kolonlar[0], kolonlar[3]], "x", 0.0, 0.0, 1014.0) == []
    # y yönündeki kenar
    assert PL._kenar_parcalari([(0, 240, 10, 250)], "y", 5.0, 0.0, 500.0) == [240.0, 250.0]


def test_110m2_on_kiris_ara_kolonda_bolunur():
    N, k, L = _kirisler(_ie("D129_veranda_110m2.json"))
    assert N["veranda_ara_kolon_parca_sira"] == [0, 1, 2]
    assert k["L 3230"] == 2 and k["L 3280"] == 1 and "L 9940" not in k
    satir = next(x for x in L["satirlar"] if x["kalem"] == KIRIS and x["olcu"] == "L 3280")
    assert "D-129" in json.dumps(satir, ensure_ascii=False)


def test_ara_kolonsuz_veranda_aynen():
    ie = _ie("D129_veranda_110m2.json")
    ie["dikmeler"] = []
    N, k, _ = _kirisler(ie)
    assert "veranda_ara_kolon_parca_sira" not in N
    assert k["L 9940"] == 1
