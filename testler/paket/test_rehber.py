"""İE-18 R1 · D-28 A1: montaj rehberi tek şablondan. Hedef örnek 62 m² rehberidir (Lokman'ın beğendiği, rehber.portatifev.com'daki sayfa):
şablon (`araclar/paket/rehber/sahne.js` + `kabuk.html`) ile 62'nin verisi (`rehber62/veri.json`) o sayfayı aynen verir.

- `test_62_verisi`: `rehber62/donustur.py` (62'nin girdisi + sahnesindeki sabitler → şablonun verisi) commit'li `veri.json`'u verir.
- `test_62_izi`: şablon + 62'nin verisi → sayfa → iz (`rehber/iz.js`: her parçanın adımı, sırası, kartı, yazısı ve dünya koordinatındaki
  köşeleri; adımların metni, satırları ve kamerası) → commit'li `rehber62/iz.json` ile aynı. İz onaylı 62 m² sayfasından alındı
  (6b899b4, `deneme/2026-10-25_rehber_62m2/rehber/`); tek düzeltme dübelin adı (karar verilmiş kalem). Şablon değişip 62'yi bozarsa
  bu test kırmızıdır. Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).

Evlerin rehberi (TK-01, AP-19) aynı şablondan; verileri `test_paket.py` sınar (kart modeliyle aynı adet, eski rehberle aynı adet,
sayfa hatasız açılır).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
B = Path(__file__).with_name("rehber62")
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(B))
from araclar.paket.rehber import iz  # noqa: E402


def test_62_verisi():
    import donustur
    assert donustur.veri() == json.loads((B / "veri.json").read_text(encoding="utf-8"))


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber izi: {iz.hazir()}")
def test_62_izi(tmp_path):
    from araclar.paket.rehber import sayfa
    html = sayfa.yaz(json.loads((B / "veri.json").read_text(encoding="utf-8")), tmp_path / "62.html")
    a = json.loads((B / "iz.json").read_text(encoding="utf-8"))
    b = iz.al(html, tmp_path / "iz.json")
    assert b["hatalar"] == []
    for k in ("N", "liste", "ilerleme", "parca"):
        assert a[k] == b[k], k
    fark = [(i, {k: (x[k], y.get(k)) for k in x if x[k] != y.get(k)}) for i, (x, y) in enumerate(zip(a["parts"], b["parts"])) if x != y]
    assert not fark, f"{len(fark)} parça farklı; ilk: {fark[:3]}"
    fark = [(x["i"], k) for x, y in zip(a["adimlar"], b["adimlar"]) for k in x if x[k] != y.get(k)]
    assert not fark, f"adımlarda fark: {fark[:10]}"
