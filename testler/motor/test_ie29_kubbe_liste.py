"""İE-29 PR-2 · Kubbenin yükleme listesi (D-54 madde 2; AP-17, AP-24, AP-23).

Kubbe başına kitabın kubbe takımı (`kurallar/liste/prefabrik.json` › `kubbe_takimi`; Lokman 13 Ekim 2026 14:42, R6: AP-02 kubbeli −
AP-03 kubbesiz): özel pano 100 × 2500 × 500 (kubbenin üstündeki 50'lik parça), üstü H, açılı köşe direği, kubbe saçak sacı, üç kubbe
makası, OSB, membran, shingle. Lokman 5 Kasım 2026 10:41: "üzerine standart çatı aşığı geliyor ... yine aynı normal çatı gibi saçak omegası
ve saçak sacı geliyor bunu tüm kubbeli binalar için uygula": aşık kubbenin üç yüzünde saçaktan 60 arayla, saçak omegası kubbe duvarlarının
üstünde duvar boyunca. Kubbenin panoları (yan 79, ön 125,5; 203 boyunda, Lokman 12:05) kendi pencereleriyle karkaslı özel pencere
panosu (L1); kubbenin tabanı pano değil, iki ucunda H yok (açılı köşe direği). Çizimler Lokman'ın 5 Kasım 12:34 onayıyla (r03). LLM yok.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402

PROJE = KOK / "testler" / "kor" / "projeler"


def _ie(kod: str) -> dict:
    return json.loads((PROJE / kod / "is_emri.json").read_text(encoding="utf-8"))


def _satir(L: dict) -> dict:
    return {(s["kalem"], s["olcu"]): s["adet"] for s in L["satirlar"]}


TAKIM = {("Kubbe özel pano", "100 × 2500 × 500"): 1, ("Kubbe üstü H", "100 × 100 × 500"): 2,
         ("Özel açılı köşe direği + kapaması", "100 × 100 × 2330"): 4, ("Kubbe saçak sacı (antrasit)", "170 × 1500"): 3,
         ("Kubbe makası", "80 × 0,8"): 3, ("Kubbe OSB 11 mm", "1220 × 2440"): 1, ("Kubbe üstü membran", "paket"): 1,
         ("Kubbe antrasit shingle", "paket"): 1}


@pytest.mark.parametrize("kod, n", [("AP17", 1), ("AP24", 1), ("AP23", 2)])
def test_kubbe_takimi_ve_panolari(kod, n):
    L = _satir(PL.is_emrinden(_ie(kod)))
    for anahtar, adet in TAKIM.items():
        assert L[anahtar] == adet * n, (kod, anahtar)
    assert L[("Karkaslı özel pencere panosu (59/170)", "100 × 785 × 2030")] == 2 * n
    assert L[("Karkaslı özel pencere panosu (105/170)", "100 × 1250 × 2030")] == n
    assert L[("PVC pencere", "59/170")] == 2 * n and L[("PVC pencere", "105/170")] == n


def _kubbesiz(ie: dict) -> dict:
    """Aynı ev kubbesiz: kubbenin tabanı (251) düz duvar."""
    ie = copy.deepcopy(ie)
    ie.pop("kubbeler")
    return ie


def test_ap17_kubbe_tabani_pano_degil_ucunda_h_yok():
    ie = _ie("AP17")
    N, N0 = PL.model_motor(ie), PL.model_motor(_kubbesiz(ie))
    assert not any(p["aciklik"] and p["aciklik"]["tur"] == "kubbe" for p in N["panolar"])
    assert sum(1 for p in N["panolar"] if p.get("kubbe")) == 3
    # kubbesiz evde aynı yerde iki pano ve aralarında bir ek; kubbeli evde tabanın iki ucundaki ek de yok
    assert len(N["ekler"]) == len(N0["ekler"]) - 3


def test_ap17_kubbe_asigi_ve_sacak_omegasi():
    ie = _ie("AP17")
    c, = [c for c in PL.model_motor(ie)["cati"] if c.get("kubbe")]
    assert c["duvar_m"] == round((2 * 58.61 * 2 ** 0.5 + 133.78) / 100, 4)                     # kubbe duvarlarının dış çizgisi
    yan, on, yan2 = c["yuzler"]
    assert yan == yan2 and round(on["taban_cm"], 2) == 149.11 and round(yan["taban_cm"], 2) == 109.05   # saçak 18,5, gönye
    assert round(on["egik_cm"], 2) == round(((58.61 + 18.5) ** 2 + 25 ** 2) ** 0.5, 2)           # tepe 35 − topuk 10
    # aşık: her yüzde saçakta ve saçaktan 60'ta (tepeye 60'tan az kalınca son)
    beklenen = sum(y["taban_cm"] * (1 + (1 - 60 / y["egik_cm"])) for y in c["yuzler"])
    assert abs(PL.kubbe_asigi_cm(c, 60) - beklenen) < 1e-6
    L = {s["kalem"]: s for s in PL.is_emrinden(ie)["satirlar"]}
    assert "kubbe duvarları 3,00 m (D-54)" in L["100'lük saçak omegası"]["formul"]
    assert "kubbe 1 × üç yüz 5,1 m" in L["Aşık"]["formul"]


def test_kubbesiz_evin_listesi_aynen():
    """Kubbe yalnız `kubbeler` anahtarlı İş Emri'nde: kubbesiz çatı girişi ve satırları değişmez."""
    ie = _kubbesiz(_ie("AP17"))
    N = PL.model_motor(ie)
    assert not any(c.get("kubbe") for c in N["cati"])
    assert not any("ubbe" in s["kalem"] for s in PL.liste(N)["satirlar"])
    assert G.KUBBE["duvar_cm"] == 203.0 and G.KUBBE["sacak_cm"] == 18.5
