"""Montaj rehberi ön-sol köşeden dizilen evi de kurar (17 Kasım 2026; 85 m² katalog evi, İş Emri `is_emri/P8501_r04.json`).

Hata: rehber üreteci (`rehber/veri.py` › `oda_sirasi`) yalnız arka-sol köşeden dizilen evi kuruyordu (`dizilim.baslangic: arka-sol`;
TK-01…TK-05). Motor'un varsayılanı ön-sol (`baslangic` yazılmazsa); katalog evlerinin İş Emri'si bunu yazmaz, rehber "Yok: dizilim
başlangıcı {'x': 'min', 'y': 'min'}" diyordu. Lokman, 17 Kasım 2026 07:41 UTC: "bana başka bir sohbette montaj paftasını oluşturur musun?"

Düzeltme: ön-sol başlangıçta oda sırası aynı kuralla, planın y'si aynalanarak (ön duvara değen odalar soldan sağa, sağ duvara değenler
önden arkaya, arka duvara değenler sağdan sola, sol duvara değenler arkadan öne); oda içinde sıra odanın ön-sol köşesinden; ilk odanın
yazısı "ön sol köşesinden". Arka-sol evlerin rehberi değişmez (`test_rehber.py`, `test_paket.py`, `test_tk05_rehber.py`).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import veri  # noqa: E402

IE = KOK / "is_emri" / "P8501_r04.json"


def _kutu(ad, x0, y0, x1, y1):
    return {"ad": ad, "poligon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


ODALAR = [_kutu("ON SOL", 0, 0, 100, 100), _kutu("ON SAG", 100, 0, 200, 100),
          _kutu("ARKA SOL", 0, 100, 100, 200), _kutu("ARKA SAG", 100, 100, 200, 200)]


def test_oda_sirasi_arka_sol_aynen():
    assert veri.oda_sirasi(copy.deepcopy(ODALAR), {"x": "min", "y": "max"})[0] == ["ARKA SOL", "ARKA SAG", "ON SAG", "ON SOL"]


def test_oda_sirasi_on_sol_aynali():
    assert veri.oda_sirasi(copy.deepcopy(ODALAR), {"x": "min", "y": "min"})[0] == ["ON SOL", "ON SAG", "ARKA SAG", "ARKA SOL"]


@pytest.mark.parametrize("bas", [{"x": "max", "y": "max"}, {"x": "max", "y": "min"}])
def test_sag_kose_desteklenmiyor(bas):
    with pytest.raises(veri.Desteklenmiyor):
        veri.oda_sirasi(copy.deepcopy(ODALAR), bas)


@pytest.fixture(scope="module")
def p8501(tmp_path_factory):
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    ie = json.loads(IE.read_text(encoding="utf-8"))
    assert "baslangic" not in ie["yapi"]["dizilim"]                     # Motor'un varsayılanı: ön-sol
    kart = tmp_path_factory.mktemp("p8501_rehber")
    kart_model.uret(copy.deepcopy(ie), kart, "P8501")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), kart, "P8501", L, "KP-85")
    G.lento_ayarla({})
    yield d
    G.lento_ayarla({})


def test_p8501_rehber_kurulur(p8501):
    d = p8501
    assert d["N"] == 21 and len(d["panels"]) == 49 and len(d["rooms"]) == 6
    oda = [a for a in d["adimlar"] if a.get("oda")]
    assert oda[0]["oda"] == "yasamalani"                                # ön-sol köşedeki oda ilk
    assert [x for x in d["panels"] + d["hs"] + d["posts"] if not (x.get("card") or x.get("ad"))] == []


def test_p8501_ilk_oda_yazisi_on_sol(p8501):
    assert "ön sol köşesinden" in json.dumps(p8501, ensure_ascii=False)
    assert "arka sol köşesinden" not in json.dumps(p8501, ensure_ascii=False)
