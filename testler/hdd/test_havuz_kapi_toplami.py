"""Havuz hakemi, kartta dış ve iç kapı ayrılamadığında kapı toplamını denetler (İE-43 PR-4, 15 Kasım 2026).

Disk arşivinin 2020 montaj paftasında dış kapının "Çelik" yazısı yok: paftadan okunan kart (`araclar/hdd_turev/pafta_kart.py`) dış ve iç
kapıyı ayıramaz, yalnız kapı kanadı sayısını (`kapi_adedi`) yazar. Hakem o zaman Motor'un dış + iç kapı toplamını onunla kıyaslar.
AIPrefabrik proje kartlarında bu alan yok; onların denetimi aynen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar import havuz_hakemi as HH  # noqa: E402

IE = KOK / "testler" / "kor" / "projeler" / "AP04" / "is_emri.json"


def test_kapi_toplami_kartta_ayrim_yoksa():
    ie = json.loads(IE.read_text(encoding="utf-8"))
    kart = dict(HH.kartlar()["AP-04"])
    b, o = HH.denetle(ie, kart)
    assert b == []
    toplam = o["dis_kapi"] + o["ic_kapi"]
    ayrimsiz = {**kart, "dis_kapi_adedi": None, "ic_kapi_adedi": None, "kapi_adedi": toplam}
    assert HH.denetle(ie, ayrimsiz)[0] == []
    eksik = HH.denetle(ie, {**ayrimsiz, "kapi_adedi": toplam + 1})[0]
    assert len(eksik) == 1 and eksik[0].startswith("kapı: ") and "ayrılamadı" in eksik[0]


def test_ayrim_varsa_toplam_denetlenmez():
    """Kart dış ve iç kapıyı ayrı yazıyorsa onlar denetlenir; toplam alanı yanlış olsa da ikinci bulgu çıkmaz."""
    ie = json.loads(IE.read_text(encoding="utf-8"))
    kart = dict(HH.kartlar()["AP-04"])
    assert HH.denetle(ie, {**kart, "kapi_adedi": 99})[0] == []


def test_proje_kartlarinda_kapi_toplami_yok():
    """AIPrefabrik'in kartları dış ve iç kapıyı ayırır; toplam yalnız disk arşivinin kartlarında (HD-NNN)."""
    k = HH.kartlar()
    assert all("kapi_adedi" not in v for a, v in k.items() if a.startswith("AP-"))
    assert all(v.get("kapi_adedi") is not None for a, v in k.items() if a.startswith("HD-"))
