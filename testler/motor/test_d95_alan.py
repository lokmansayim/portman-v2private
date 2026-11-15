"""D-95 · Brüt ve net m²'nin tanımı (mühür M-18).

Lokman, 14 Kasım 2026 (UTC): 21:01:02 "net ve bürütte hata var biz verandayıda net alana alır sayarız bu kadar fark çıkmaz prefabrikte";
21:01:25 "biz çatı ile kapattığımız her yeri bürütten sayarız"; 21:07:29 "biz her zaman brüt m² ile hesaplarız ben izin veriyorum varsa
mühür bunu gir ve mühürle".

- Brüt: çatının örttüğü her yer; yükleme listesinin `bina_m2`'si (tek kaynak `prefabrik_liste.bina_brut_cm2`, D-49 madde 2).
- Net: bütün mahallerin net alanı; veranda, giriş nişi ve balkon dahil.
- Ön onay antedi (`dxf_out.alan_yazisi`) ve montaj rehberinin başlığı (`araclar/paket/rehber/veri.baslik_alani`) aynı yazıyı basar.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from motor import dxf_out, geometry as G, prefabrik_liste as PL

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "motor" / "veri"

# İş Emri → (brüt, net, kapalı odalar). Sayılar 14 Kasım 2026'da Motor'dan; net − kapalı = veranda, giriş nişi ve balkon.
BEKLENEN = {
    "TK01_r08": ("90,28", "84,60", "72,70"),     # 80 m² 3+1 (D-104, 15 Kasım 2026: nişte köşe direği, hol 5,91 → 5,90; 72,71 → 72,70)
    "TK02_r04": ("90,28", "83,35", "71,45"),     # 80 m² 3+1, 100'lük iç duvar
    "TK03": ("87,72", "82,07", "76,01"),         # 88 m² 3+1
    "TK04_r08": ("77,95", "73,04", "65,22"),     # kampanyalı ev
    "TK05_r07": ("21,16", "17,87", "17,03"),     # yatak odası + banyo
    "PK01": ("60,00", "55,53", "48,85"),         # 60 m²
}


def _f2(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


@pytest.fixture
def lento_sifirla():
    yield
    G.lento_ayarla({})                       # lento modül durumudur (BK-23): öteki testlere sızmaz


@pytest.mark.parametrize("ad", sorted(BEKLENEN))
def test_brut_cati_net_verandali(ad, lento_sifirla):
    brut, net, kapali = BEKLENEN[ad]
    ie = json.loads((VERI / f"{ad}.json").read_text(encoding="utf-8"))
    plan = G.kur(copy.deepcopy(ie))
    assert dxf_out.alan_yazisi(plan) == f"{brut} m² brüt · {net} m² net"
    assert _f2(PL.bina_brut_cm2(plan) / 1e4) == brut == _f2(PL.model_motor(copy.deepcopy(ie))["brut_m2"])
    assert _f2(sum(m.alan_m2 for m in plan.mahaller.values())) == net
    assert _f2(sum(m.alan_m2 for m in plan.mahaller.values() if not m.acik)) == kapali


def test_rehber_basligi_antedin_yazisi(lento_sifirla):
    from araclar.paket.rehber import veri
    plan = G.kur(json.loads((VERI / "TK01_r08.json").read_text(encoding="utf-8")))
    assert veri.baslik_alani(plan) == dxf_out.alan_yazisi(plan) == "90,28 m² brüt · 84,60 m² net"
