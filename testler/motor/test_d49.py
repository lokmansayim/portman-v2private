"""D-49 (Lokman, 4 Kasım 2026; TK-04 kampanyalı prefabrik): ortalanan pencerenin köşeye bakan yanı tek pano.

14:25: "küçük bir hata mutfaktaki 120x180 pencereyi güzel ortalamışsın ama pencerenin sağındaki panel duvarı yanlış ölçeklendirmişsin 2 parça
gibi ölçeklendirmişsin". TK-04'ün mutfağı verandaya bakan duvarında 507–820,75 (2,5 pano); oda ortası ızgara panosundan ¼ panodan çok
kaçtığı için pencereli pano odaya ortalanır (D-15), sağında duvarın ucuna (verandanın açık köşesi) 95,125 kalır: 32,375 + 62,75 değil, tek
pano (`geometry._pencere_yani_tek_pano`). Yan bir T'de bitiyorsa ekler aynen (kör PK-02'nin gerçek listesi: 42,25 + 39; D-29 madde 2).
"""
from __future__ import annotations

import json
from pathlib import Path

from motor import geometry as G

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _boylar(d):
    return [(round(p.boy, 3), p.acilim.tur if p.acilim else "") for p in d.panolar]


def test_pencere_yani_koseye_tek_pano():
    """TK-04 mutfağının verandaya bakan duvarı: hol kapısı, 93,125, pencereli pano, köşeye 95,125 (tek pano)."""
    plan = G.kur(_oku(VERI / "TK04.json"))
    d = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 198.25) < 1e-6)
    assert _boylar(d) == [(125.5, "dis_kapi"), (93.125, ""), (125.5, "pencere"), (95.125, "")], _boylar(d)


def test_t_yanindaki_ekler_aynen():
    """Pencereyle T (oda sınırı) arasındaki ekler değişmez: kör PK-02'nin yatak odası penceresinin yanı 42,25 + 39 (gerçek liste)."""
    plan = G.kur(_oku(KOK / "testler" / "kor" / "projeler" / "PK02" / "is_emri.json"))
    b = _boylar(next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "y" and abs(d.c - 768.0) < 1e-6))
    i = [k for k, x in enumerate(b) if x[1] == "pencere"][1]
    assert b[i - 2:i + 2] == [(39.0, ""), (42.25, ""), (125.5, "pencere"), (83.25, "")], b


def test_tk04_planinda_kisa_pano_yok():
    """TK-04'ün bütün duvarlarında 60 cm'den kısa pano yok (pencere yanındaki 32,375'lik parça gitti)."""
    plan = G.kur(_oku(VERI / "TK04.json"))
    kisa = [(d.id, round(p.boy, 3)) for d in plan.duvarlar for p in d.panolar if p.boy < 57.75 - 1e-6]
    assert not kisa, kisa
