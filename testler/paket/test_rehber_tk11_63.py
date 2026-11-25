"""63 m² tek evin (TK-11) montaj rehberi main'deki koddan çıkar (BK-77; 24–25 Kasım 2026).

Lokman, 24 Kasım 2026 06:51:52 UTC "1-5 evet" (5: 63 m² montaj rehberi). Rehber üç yerde duruyordu: verandanın köşe kırması,
kubbe (D-54) ve makas sayısı (kart modeli 7, çatı 8). 07:35:17 UTC: "Montaj Rehberlerinde bundan sonra orjinal üretim çizimleri
dursun": kubbenin çelik karkası üretim dosyasından (`araclar/uretim/veri/kubbe.json`, BK-76).

Bu test hedef örnek değildir: rehber taslaktır, Lokman'ın onayı yoktur (D-28 madde 2). Denetlenen yalnız yapıdır: rehber kurulur,
köşe kırmasının 4 kısa + 1 çapraz makası, kubbenin 7 üretim çerçevesi (çubuk sayısı dosyadakiyle aynı) ve OSB adımı yerindedir.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

IE = KOK / "testler" / "teklif_formu" / "TK11" / "is_emri.json"
URETIM = KOK / "araclar" / "uretim" / "veri" / "kubbe.json"


@pytest.fixture(scope="module")
def d(tmp_path_factory):
    from motor import geometry as G
    from araclar.paket import uret
    from araclar.paket.rehber import veri
    ie = json.loads(IE.read_text(encoding="utf-8"))
    tmp = tmp_path_factory.mktemp("tk11_rehber")
    L = uret.listeler(copy.deepcopy(ie), ["ters"])["ters"]
    uret.kart_modeli(copy.deepcopy(ie), tmp, "TK-11")
    v = veri.kur(copy.deepcopy(ie), tmp / "kart", "TK-11", L["satirlar"], "TK-11")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    yield v
    G.lento_ayarla({})


def test_kose_kirmasinin_makaslari(d):
    """Verandanın köşe kırması: 4 kısa makas (MA-06) + 1 çapraz makas (MA-07), ana çatının makaslarıyla aynı adımda."""
    mk = [e for e in d["ek"] if e["mat"] == "truss" and e.get("kod")]
    assert sorted(e["kod"] for e in mk) == ["MA-06"] * 4 + ["MA-07"]
    assert len({e["adim"] for e in mk}) == 1
    assert d["adimlar"][mk[0]["adim"]]["ad"] == "Ana çatı makasları"


def test_kubbe_uretim_cercevelerinden(d):
    """Kubbenin 3 duvarı, üst bandı ve 3 makası üretim dosyasından; her çerçevenin çubuk sayısı dosyadaki parça sayısı."""
    fr = json.loads(URETIM.read_text(encoding="utf-8"))
    kb = [e for e in d["ek"] if e["ad"].startswith(("Kubbe duvarı", "Kubbe üst bandı", "Kubbe makası"))]
    assert len(kb) == 7
    assert sorted(len(e["cubuk"]) for e in kb) == sorted(len(f["parcalar"]) for f in fr)
    duvar = {e["adim"] for e in kb if not e["ad"].startswith("Kubbe makası")}
    assert len(duvar) == 1                                # kubbe duvarları ve bandı kubbenin odasının adımında


def test_osb_adimi(d):
    """İş Emri OSB yazar: OSB ve nem bariyeri adımı aşıklardan sonra, saçak sacından önce; mahal çatısı da OSB'li."""
    ad = [a.get("ad") for a in d["adimlar"]]
    i = ad.index("OSB ve nem bariyeri")
    assert ad[i - 1] == "Aşıklar" and ad[i + 1] == "Saçak sacı"
    assert d["kaplama"]["osb"] == {"kal": 1.1, "nem": 0.05}
    assert any(e.get("osb") for e in d["ek"] if e["mat"] == "roof")
