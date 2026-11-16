"""D-121 (BK-52, PC-46): makas aksı kaymaz, makasa dik duvarda pencere tam ortada.

Lokman, 16 Kasım 2026 20:56:44: "makas yönündeki akslar çok önemli makasları o akslara oturtuyoruz ama makas yönüne dik olan akslar
kayabilir ama yine kurallı kaysın". Kartlar 21:14:20 "Okuma 1: aks kaymaz, yarım pano olur", 21:15:33 "Her zaman tam ortada",
21:36:53 "B) 125,5 pencere yanında, kalan uçta", 21:38:12 "Yalnız yeni çizilen evlere". Hedef örnek 60 m² (P6001 r03, Lokman'ın onayı
20:57): `testler/motor/veri/D121_beklenen.json`.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from motor import geometry as G

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "motor" / "veri"


def _oku(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _anahtarli(ie: dict) -> dict:
    ie = copy.deepcopy(ie)
    ie["yapi"].setdefault("dizilim", {})["dik_duvar_pencere"] = "tam_orta"
    return ie


def _dizilim(plan) -> dict:
    return {f"{d.tur} {d.yon} {d.c:g}": [[round(q.a0, 3), round(q.boy, 3), q.acilim.tur if q.acilim else ""] for q in d.panolar]
            for d in plan.duvarlar}


def test_hedef_ornek_60m2():
    """Kuralla kurulan 60 m², Lokman'ın onayladığı r03 dizilimiyle pano pano aynı (A′ ek aksı ve dayanağı olmadan)."""
    hedef = json.loads((VERI / "D121_beklenen.json").read_text(encoding="utf-8"))
    plan = G.kur(_oku("testler/motor/veri/D121_60m2_is_emri.json"))
    assert _dizilim(plan) == {d["duvar"]: d["panolar"] for d in hedef["duvarlar"]}
    assert plan.dik_duvar_pencere == [{"duvar": "dis x 5", "once": [125.5, 125.5, 62.75], "sonra": [94.125, 125.5, 94.125]}]
    assert G.makas_aksi_denetimi(plan, "x") == []


def test_anahtarsiz_eski_yol():
    ie = _oku("testler/motor/veri/D121_60m2_is_emri.json")
    del ie["yapi"]["dizilim"]["dik_duvar_pencere"]
    plan = G.kur(ie)
    assert plan.dik_duvar_pencere == []
    d = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 5) < 1e-6)
    assert [round(q.boy, 3) for q in d.panolar] == [125.5, 125.5, 62.75]


def test_uzun_yan_125_pencere_yaninda_kalan_ucta():
    """Kart 21:36:53 "B": 87 m²'nin yatak odası 2 arka duvarı (466,25): 44,875 + 125,5 + pencere + 125,5 + 44,875."""
    plan = G.kur(_anahtarli(_oku("is_emri/adaylar/PA06.json")))
    assert {"duvar": "dis x 1083", "once": [125.5, 125.5, 125.5, 89.75], "sonra": [44.875, 125.5, 125.5, 125.5, 44.875]} \
        in plan.dik_duvar_pencere
    d = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 1083) < 1e-6)
    p = next(q for q in d.panolar if abs(q.a0 - 494.125) < 1e-6)
    assert p.acilim is not None and p.acilim.tur == "pencere" and abs(p.boy - 125.5) < 1e-9


def test_kisa_yan_her_zaman_ortada():
    """Kart 21:15:33 "Her zaman tam ortada": 90 m²'nin 188,25'lik oda parçasında 31,375 + pencere + 31,375."""
    plan = G.kur(_anahtarli(_oku("testler/motor/veri/TK01_r08.json")))
    assert {"duvar": "dis x 883.5", "once": [125.5, 62.75], "sonra": [31.375, 125.5, 31.375]} in plan.dik_duvar_pencere


@pytest.mark.parametrize("yol", ["is_emri/adaylar/PA06.json", "testler/motor/veri/TK01_r08.json", "is_emri/adaylar/PA39.json",
                                 "testler/motor/veri/D121_60m2_is_emri.json", "is_emri/YAN_VERANDALI_2plus1_6x8p5.json"])
def test_sacak_duvari_ve_ic_duvar_degismez(yol):
    """Kart 21:14:20 (Okuma 1): makasın oturduğu saçak duvarı ve iç duvarlar kuraldan etkilenmez; yalnız makasa dik dış duvar değişir."""
    ie = _oku(yol)
    (ie["yapi"].get("dizilim") or {}).pop("dik_duvar_pencere", None)
    me = (ie.get("cati") or {}).get("makas_ekseni", "x")
    once, sonra = _dizilim(G.kur(copy.deepcopy(ie))), _dizilim(G.kur(_anahtarli(ie)))
    for k in once:
        tur, yon, _ = k.split(" ")
        if tur != "dis" or yon != me:
            assert once[k] == sonra[k], k


def test_pencere_dis_olcu_ve_pano_sayisi():
    """Pencere odanın duvar parçasının tam ortasında; dış ölçü değişmez; açıklıksız pano 125,5'i aşmaz (D-69 denetimi geçer)."""
    for yol in ("is_emri/adaylar/PA06.json", "testler/motor/veri/TK01_r08.json", "testler/motor/veri/D121_60m2_is_emri.json"):
        ie = _oku(yol)
        p0, p1 = G.kur(copy.deepcopy(ie)), G.kur(_anahtarli(ie))
        assert (p0.W, p0.H) == (p1.W, p1.H)
        for c in p1.dik_duvar_pencere:
            s = c["sonra"]
            assert abs(sum(s) - sum(c["once"])) < 1e-6
            i = s.index(125.5) if len(s) == 3 else len(s) // 2
            assert abs(sum(s[:i]) - sum(s[i + 1:])) < 1e-6, c   # iki yan eşit


def test_bilinmeyen_deger_hata():
    ie = _anahtarli(_oku("testler/motor/veri/D121_60m2_is_emri.json"))
    ie["yapi"]["dizilim"]["dik_duvar_pencere"] = "oda_ortasi"
    with pytest.raises(G.IsEmriHatasi, match="dik_duvar_pencere bilinmiyor"):
        G.kur(ie)


def test_anahtarla_havuzun_her_evi_kurulur():
    """Yeni çizilen ev havuz evleri gibi olacak: havuzdaki her prefabrik İş Emri anahtarla da kurulur, D-69 denetimi geçer."""
    for f in sorted((KOK / "is_emri" / "adaylar").glob("*.json")):
        ie = json.loads(f.read_text(encoding="utf-8"))
        if not (isinstance(ie.get("yapi"), dict) and "grid" in ie["yapi"] and "mahaller" in ie):
            continue
        G.kur(_anahtarli(ie))


def test_makas_aksi_denetimi():
    """Hakem (kart 21:14:20): saçak duvarında ek tam ya da yarım aksta. 90 m² (yarım panolu) temiz; 37 m² paftasında 94,12'lik iki ek
    ızgara dışında (asıl proje havuzda aynen, D-103; hakem bulguyu söyler)."""
    assert G.makas_aksi_denetimi(G.kur(_oku("testler/motor/veri/TK01_r08.json")), "x") == []
    b = G.makas_aksi_denetimi(G.kur(_oku("is_emri/adaylar/PA39.json")), "y")
    assert len(b) == 2 and all("makas aksı kaymaz" in x for x in b)
