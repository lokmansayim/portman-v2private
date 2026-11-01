"""D-40 (Lokman, 1 Kasım 2026 10:23): "şayet çatı sandviç panel ise çatı kaplaması kalınlaşır ve doğal olarak alın sacı alnı da genişler
başka hiç bir yerde değişiklik olmaz". Kaplama profili kural kitabında (`cati_kaplamasi.profil`); kalınlaşma tek kat panele göre
(yalıtım + hadve) farkı, sandviç panelde 4,8 cm. Aynı ev (PK-01) sandviç ve tek kat panelle: kart modelinin IFC'sinde yalnız kaplama,
alın sacı ve mahya değişir, o da 4,8 cm; öteki bütün parçaların kutusu aynı."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import yerlesim  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"


def _kurallar() -> dict:
    return json.loads((KOK / "kurallar" / "yerlesim" / "prefabrik.json").read_text(encoding="utf-8"))


def test_profil_ve_kalinlasma():
    """Profil Lokman'ın verdiği panelden (100 cm kapatır, 5 hadve, hadve 35 mm; yalıtım 40 mm stok standart); tek kat panel 62 m²
    rehberinin 27/200 trapezi. Kalınlaşma (yalıtım + hadve) farkı: sandviç 4,8, tek kat 0, kurulmayan kaplama 0."""
    C = _kurallar()["kurallar"]["cati_kaplamasi"]
    assert C["profil"]["durum"] == "lokman" and "10:23" in C["profil"]["kaynak"]
    P = C["profil"]["deger"]
    assert P["sandvi"] == {"hadve_sayisi": 5, "hadve": 3.5, "tepe": 4.2, "taban": 7.4, "kenar": 4.5, "yalitim": 4}
    assert P["tek kat"] == {"hadve_sayisi": 5, "hadve": 2.7, "tepe": 4.2, "taban": 7.4, "kenar": 4.5, "yalitim": 0}
    D = {"profil": P, "varsayilan": C["varsayilan"]["deger"]}
    assert yerlesim.kaplama_kalinlasma(D, "sandvi") == 4.8
    assert yerlesim.kaplama_kalinlasma(D, "tek kat") == 0 and yerlesim.kaplama_kalinlasma(D, None) == 0


@pytest.fixture(scope="module")
def iki_kaplama(tmp_path_factory):
    from araclar.paket.rehber.veri import ifc_kutulari
    from motor import kart_model
    ie = json.loads((VERI / "PK01.json").read_text(encoding="utf-8"))
    out = {}
    for tur, yazi in (("sandvi", None), ("tek kat", "Tek Kat Panel")):
        ie_ = copy.deepcopy(ie)
        if yazi:
            ie_["ozellikler"]["Çatı Kaplaması"] = yazi
        d = tmp_path_factory.mktemp(f"pk01_{tur.replace(' ', '_')}")
        kart_model.uret(ie_, d, "PK01")
        say = json.loads((d / "PK01_kart_sayim.json").read_text(encoding="utf-8"))
        out[tur] = (say, ifc_kutulari(d / "PK01_model.ifc", r"^[A-Z_0-9]+$"))
    return out


def test_baska_hicbir_parca_degismez(iki_kaplama):
    """PK-01 (sandviç panel) ve aynı ev tek kat panelle: parça adları ve sayıları aynı; kaplamanın üstü ve alın sacının üstü 4,8 cm yukarıda,
    mahya 4,8 cm yukarıda; öteki bütün parçaların (makas, aşık, betopan, Z, C kapama, saçak sacı, dere, omega, duvar …) kutusu aynı."""
    (say_s, a), (say_t, b) = iki_kaplama["sandvi"], iki_kaplama["tek kat"]
    assert {p["bilgi"].get("Kaplama") for p in say_s["yerlesim"]["parcalar"] if "Kaplama" in p["bilgi"]} == {"sandvi"}
    assert {p["bilgi"].get("Kaplama") for p in say_t["yerlesim"]["parcalar"] if "Kaplama" in p["bilgi"]} == {"tek kat"}
    assert set(a) == set(b) and len(a) > 400
    degisen = {}
    for n in a:
        d = [round(x - y, 3) for x, y in zip(a[n], b[n])]
        if any(abs(x) > 1e-3 for x in d):
            degisen[n] = d
    on = {n.rstrip("0123456789").rstrip("_") for n in degisen}
    assert on == {"KAPLAMA", "ALIN_SACI", "MAHYA"}, on
    assert all(d == [0, 0, 0, 0, 0, 4.8] for n, d in degisen.items() if not n.startswith("MAHYA"))
    assert all(d == [0, 0, 4.8, 0, 0, 4.8] for n, d in degisen.items() if n.startswith("MAHYA"))
    assert sum(n.startswith("ALIN_SACI") for n in degisen) == sum(n.startswith("ALIN_SACI") for n in a)
    assert sum(n.startswith("KAPLAMA") for n in degisen) == sum(n.startswith("KAPLAMA") for n in a)
