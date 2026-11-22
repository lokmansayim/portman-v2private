"""D-144 (BK-69): açık mahalin tek eğimli panel çatısında veranda başına 1 hafif çelik çatı paneli (Lokman, 22 Kasım 2026 05:08:57
UTC: "evet 1 adet sayılsın"). Önce satır adetsiz "Kural yok"tu (havuz denetimi HD-04, üç ev). Hedef örnek
`testler/motor/veri/D144_mahal_paneli_beklenen.json`. Teras paneli (D-52) ve pafta kipi aynen."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from motor import prefabrik_liste as PL

KOK = Path(__file__).resolve().parents[2]
BEKLENEN = json.loads((KOK / "testler/motor/veri/D144_mahal_paneli_beklenen.json").read_text(encoding="utf-8"))


def _liste(yol: Path) -> list[dict]:
    return PL.is_emrinden(copy.deepcopy(json.loads(yol.read_text(encoding="utf-8"))))["satirlar"]


@pytest.mark.parametrize("kod", sorted(BEKLENEN["evler"]))
def test_veranda_basina_bir_panel(kod):
    L = _liste(KOK / "is_emri/adaylar" / f"{kod}.json")
    b = BEKLENEN["satir"]
    panel = [{a: s[a] for a in b} for s in L if s["kalem"].startswith("Çatı paneli (hafif çelik)")]
    assert panel == [b]
    assert not [s["kalem"] for s in L if s["adet"] is None or s["dayanak"] == "Kural yok"]


def test_teras_paneli_aynen():
    """Teras paneli (D-52, AP-26) kendi satırıyla kalır; D-144 satırı yazılmaz."""
    L = _liste(KOK / "testler/kor/projeler/AP26/is_emri.json")
    assert [s["adet"] for s in L if s["kalem"].startswith("Teras paneli (hafif çelik C 80)")] == [1, 1]
    assert not any(s["dayanak"] == "Kural (D-144)" for s in L)


def test_pafta_kipi_aynen():
    """Pafta kipindeki makassız parça (PK-07'nin veranda saçağı) eskisi gibi adetsiz: kural yalnız Motor'un açık mahal paneli için."""
    from testler.kor import kiyas as K
    L = K.bizim_liste_uret(KOK / "testler/kor/projeler/PK07")["satirlar"]
    s = next(s for s in L if s["kalem"] == "Çatı paneli (hafif çelik) · veranda saçağı")
    assert (s["adet"], s["dayanak"]) == (None, "Kural yok")
