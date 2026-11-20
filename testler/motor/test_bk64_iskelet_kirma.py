"""BK-64 (D-139, PC-50): girintili gövdede kenar yöntemli kırma çatı (düz iskelet).

Hedef örnek `testler/motor/veri/BK64_PA17_beklenen.json` (91 m² 3+1; yüzler 16 Kasım onaylı eskiz, makas planı kart 20 Kasım 08:45:03,
aşık ve çatı paneli kart 08:57:26). Anahtarsız İş Emri eski yoldan gider: aynı evin bugünkü çatısı ve listesi değişmez.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_iskelet as CI  # noqa: E402
from motor import cati_prefabrik as CP  # noqa: E402
from motor import geometry as G  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor import tavan_kirisi as TK  # noqa: E402
VERI = KOK / "testler" / "motor" / "veri"
IE = json.loads((VERI / "BK64_PA17_kirma.json").read_text(encoding="utf-8"))
HEDEF = json.loads((VERI / "BK64_PA17_beklenen.json").read_text(encoding="utf-8"))
ESKI = json.loads((KOK / "is_emri" / "adaylar" / "PA17.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan():
    return G.kur(IE)


@pytest.fixture(scope="module")
def cati(plan):
    return CP.cati(plan, IE)


def test_yuzler_eskizdeki_gibi(cati):
    assert cati["yontem"] == "kenar" and cati["kalkanlar"] == []
    assert {d["ad"]: round(Polygon(d["plan"]).area / 1e4, 2) for d in cati["duzlemler"]} == HEDEF["yuzler"]


def test_yuzler_sacakli_izi_tam_orter(plan, cati):
    from motor.cati_serit import cati_izi
    assert CI.denetle(cati["duzlemler"], cati_izi(plan, IE), float(cati["sacak"])) == []


def test_iskelet_yuksekligi_mitre_varisiyla_ayni():
    """Yüzdeki her noktanın yüksekliği (kendi düzleminde) saçak çizgisinin 45° içe kayarak o noktaya varış mesafesi."""
    R = box(0, 0, 900, 600).union(box(0, 600, 400, 900))
    yz = CI.yuzler(R)
    for y in yz:
        e, n = y["kenar"], y["n"]
        p = y["cokgen"].representative_point()
        h = (p.x - e["a"][0]) * n[0] + (p.y - e["a"][1]) * n[1]
        lo, hi = 0.0, 1000.0
        for _ in range(40):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if R.buffer(-m, join_style=2, mitre_limit=10).contains(p) else (lo, m)
        assert abs(h - lo) < 0.01


def test_makas_plani_onayli_eskizdeki_gibi(plan):
    c = PL._iskelet_kirma_catilari(plan, IE)[0][0]
    km, H = c["kirma_makas"], HEDEF["makas"]
    assert (km["ana"], km["cumba"], km["kisa"], km["capraz"]) == (H["ana"], H["cumba"], H["kisa"], H["capraz"]) == (6, 2, 12, 5)
    assert [[m["a"], m["b"], m["rol"], m["vadide"]] for m in km["makaslar"]] == H["hatlar"]
    assert [[k["uc_cm"], k["b"], k["boy_cm"]] for k in km["kisa_makaslar"]] == H["kisa_makaslar"]
    assert [[k["uc_cm"], k["boy_cm"]] for k in km["capraz_makaslar"]] == H["capraz_makaslar"]
    assert {k: c[k] for k in HEDEF["cati"]} == HEDEF["cati"]
    assert c["cati_paneli"] == 4


def test_liste_satirlari_hedefle_ayni():
    L = PL.is_emrinden(IE)
    rows = [{"grup": s["grup_adi"], "kalem": s["kalem"], "olcu": s["olcu"], "adet": s["adet"]} for s in L["satirlar"]
            if s["grup_adi"] in ("Makas", "Çatı", "Dere", "Metal aksam")]
    assert rows == HEDEF["liste_satirlari"]
    asik = [s for s in L["satirlar"] if s["kalem"] == "Aşık"]
    assert [(s["olcu"], s["adet"]) for s in asik] == [("L 4200", 52)]


def test_tavan_kirisi_makas_yonu_catidan(plan):
    """Kenar yönteminde makaslar mahyaya dik (mahya y → makas x'i geçer); salonun x'teki açıklığı 7 m'yi aşmaz, kiriş yok."""
    assert CI.makas_ekseni(CP.cati(plan, IE)["duzlemler"]) == "x"
    assert TK.bul(plan, IE)["kirisler"] == []


def test_anahtarsiz_is_emri_eski_yoldan():
    p = G.kur(ESKI)
    assert CP.cati(p, ESKI).get("yontem") is None
    with pytest.raises(PL.ListeYazilmaz):
        PL._iskelet_kirma_catilari(p, ESKI)


def test_bilinmeyen_yontem_reddedilir():
    ie = copy.deepcopy(IE)
    ie["cati"]["yontem"] = "serbest"
    with pytest.raises(CP.PrefabrikCatiHatasi):
        CP.cati(G.kur(ie), ie)


def test_ince_serit_cizilmez():
    """28 cm'lik küçük girinti: iskelet her yerde 30 cm'den dar yüz kurar; kural yok, çatı çizilmez (K21)."""
    iz = box(0, 0, 800, 600).difference(box(300, 0, 500, 28))
    with pytest.raises(CI.IskeletHatasi, match="ince şerit"):
        CI.duzlemler(iz, 30.0, 0.3288, 260.0)


def test_dik_acili_olmayan_iz_reddedilir():
    with pytest.raises(CI.IskeletHatasi, match="dik açılı"):
        CI.yuzler(Polygon([(0, 0), (500, 0), (400, 300), (0, 300)]))


def test_liste_makas_yonu_catidan():
    """Geometri hakemi (20 Kasım): listenin açıklığı ve oda ölçüleri çatının makas yönünden (x), İş Emri'nin plan değerinden (y) değil."""
    L, plan = PL.model_motor(IE), G.kur(IE)
    for o in L["kapali"] + L["acik"]:                               # makas x'i geçer: oda eni y'de, derinliği x'te
        x0, y0, x1, y1 = plan.mahaller[o["ad"]].poly.bounds
        assert (o["en_cm"], o["derin_cm"]) == (y1 - y0, x1 - x0), o["ad"]


def test_besikte_yontem_reddedilir():
    from motor import sunum
    ie = copy.deepcopy(ESKI)
    ie["cati"] = {**ie["cati"], "tip": "besik", "yontem": "kenar"}
    with pytest.raises(G.IsEmriHatasi, match="yalnız kırma"):
        sunum.cati_tanimi(G.kur(ie), ie)


def test_u_govde_liste_yazilmaz(monkeypatch):
    """İki iç köşeli gövde (U) onaylı eskizle kıyaslanmadı: liste yazılmaz (K21)."""
    import motor.cati_serit as CS
    plan = G.kur(IE)
    u = box(0, 0, 888.5, 1149.5).difference(box(300, 0, 600, 220))
    monkeypatch.setattr(CS, "cati_izi", lambda p, ie: u)
    with pytest.raises(PL.ListeYazilmaz, match="iç köşe"):
        PL._iskelet_kirma_catilari(plan, IE)
