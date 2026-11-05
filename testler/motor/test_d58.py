"""D-58 (Lokman, 5 Kasım 2026 11:00; TK-04 kampanyalı prefabrik, r07): veranda 30 cm saçak kalacak şekilde içeri, kirişin salon duvarına
geldiği yere 250 cm kolon.

"veranda da saçak oturmadığı için verandayı 30cm saçak olacak şekilde içeri almamız gerekiyor çatı kısmi naif bir L olacak ayrıca kiriş
profilin boşta kalmaması için köşe direğine vidalayamıyoruz o yüzden tam geldiği yerede bir tane 250cm kolon koyması gerekiyor".
r06'da ana makaslar cumba makasının arkasından başlar (D-53 madde 7): ana çatının açıklığı ön dış yüzden 37,5'ta başlar, saçağı 7,5'ta biter.
r07'de verandanın ön kirişi 37,5'a alınır (İş Emri: ek aks y 861, girinti, `dikmeler`); Motor kodu değişmez. Çizimde girintiye bakan açık
kenarın profili (verandada `girinti_kirisi: true`), dış parça ölçüsünün kirişte bölünmesi ve ölçü yazılarının binmemesi PC-33 (`dxf_out`);
anahtarsız İş Emri eski yoldan (aynı biçimli AP-15, AP-18, AP-22, AP-25 aynen).
"""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import ezdxf

from motor import dxf_out, geometry as G, prefabrik_liste as PL

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "motor" / "veri"


def _oku(ad: str) -> dict:
    return json.loads((VERI / ad).read_text(encoding="utf-8"))


def _duvarlar(plan) -> dict:
    return {(d.tur, d.yon, round(d.c, 3), round(d.p0, 3), round(d.p1, 3)): [(round(p.boy, 3), p.acilim.tur if p.acilim else "")
                                                                         for p in d.panolar] for d in plan.duvarlar}


def test_veranda_ice_alinir():
    """Ön kiriş ön dış yüzden 37,5 içeride, köşe kolonu ve salon duvarının dibinde kolon; duvarlar ve panolar r06 ile aynı; brüt verandayla
    77,95 (veranda 7,82 m²); listede iki 250'lik kolon, sağ kiriş 155,75 − 10."""
    r6, r7 = _oku("TK04_r06.json"), _oku("TK04_r07.json")
    a, b = G.kur(copy.deepcopy(r6)), G.kur(copy.deepcopy(r7))
    assert _duvarlar(a) == _duvarlar(b)
    assert b.mahaller["VERANDA"].poly.bounds == (386.5, 37.5, 888.5, 193.25)
    assert sorted(b.dikmeler) == [(386.5, 37.5, 396.5, 47.5), (878.5, 37.5, 888.5, 47.5)] and b.kose_kolonlari == [(878.5, 37.5, 888.5, 47.5)]
    on = sorted(k[:4] for k in b.acik_kenarlar if abs(k[1] - k[3]) < 1e-9)
    assert on[0][0] == 381.5 and on[-1][2] == 883.5 and {k[1] for k in on} == {37.5}
    assert dxf_out.alan_yazisi(b) == "77,95 m² brüt · 65,22 m² net"
    L = PL.is_emrinden(copy.deepcopy(r7))
    kolon = [s for s in L["satirlar"] if s["kalem"].startswith("Özel kutu profil (kolon)")]
    assert [(s["olcu"], s["adet"]) for s in kolon] == [("L 2500", 2)]
    assert ("Kutu profil (kiriş) 100 × 100", "L 1457,5") in [(s["kalem"], s["olcu"]) for s in L["satirlar"]]


def _dxf(ie: dict, td: str):
    m = dxf_out.uret(copy.deepcopy(ie), Path(td))
    assert m["validation_passed"], m
    return ezdxf.readfile(Path(td) / m["dxf"])


def test_girinti_kenarinda_profil():
    """Girintiye bakan ön kenar veranda profilidir (dış yüz 37,5, iç çizgi 47,5, uçta iki kolonun yüzünde biter); girintisiz r06'da ve
    `girinti_kirisi` anahtarı olmayan r07'de böyle profil yok (anahtarsız İş Emri eski yoldan)."""
    with tempfile.TemporaryDirectory() as td:
        doc = _dxf(_oku("TK04_r07.json"), td)
        ins = [e for e in doc.modelspace().query("INSERT") if e.dxf.layer == "VERANDA_PROFIL_100" and e.dxf.name.endswith("_GIRINTI")
               and e.dxf.insert.x < 888.5]                            # ana plan (öteki kopya W + 300 sağda)
        assert [(round(e.dxf.insert.x, 2), round(e.dxf.insert.y, 2)) for e in ins] == [(386.5, 37.5)], [e.dxf.insert for e in ins]
        blk = doc.blocks[ins[0].dxf.name]
        cizgiler = sorted((tuple(round(v, 2) for v in l.dxf.start)[:2], tuple(round(v, 2) for v in l.dxf.end)[:2]) for l in blk.query("LINE"))
        assert cizgiler == [((0.0, 0.0), (502.0, 0.0)), ((10.0, 10.0), (492.0, 10.0))], cizgiler
    anahtarsiz = _oku("TK04_r07.json")
    for m in anahtarsiz["mahaller"]:
        m.pop("girinti_kirisi", None)
    for ie in (_oku("TK04_r06.json"), anahtarsiz):
        with tempfile.TemporaryDirectory() as td:
            doc = _dxf(ie, td)
            assert not [e for e in doc.modelspace().query("INSERT") if e.dxf.name.endswith("_GIRINTI")]


def test_olcu_yazilari_binmez():
    """Salon duvarının dış parça ölçüsü kirişin dış yüzünde bölünür (193,25 → 37,5 geri çekilme + 155,75 veranda derinliği); özel pano
    ölçüleri (62,75, 120,5) bu yazılara binmez (PC-33 öncesi 120,5, 193,25'in üstündeydi)."""
    with tempfile.TemporaryDirectory() as td:
        doc = _dxf(_oku("TK04_r07.json"), td)
    kutular = []
    for e in doc.modelspace().query("DIMENSION"):
        if e.dxf.layer not in ("OZEL_PANEL_OLCU_CM", "DIS_PARCA_OLCU") or not e.dxf.hasattr("text_midpoint"):
            continue
        x, y = e.dxf.text_midpoint.x, e.dxf.text_midpoint.y
        if not (380 < x < 520 and 0 < y < 200):
            continue
        yari = dxf_out.Cizici.yazi_eni(dxf_out.fmt(e.get_measurement()), 14) / 2
        dusey = abs(e.dxf.get("angle", 0.0) - 90.0) < 1e-6
        kutular.append((e.dxf.layer, round(e.get_measurement(), 2), (x - 7, y - yari, x + 7, y + yari) if dusey else (x - yari, y - 7, x + yari, y + 7)))
    olculer = {(k[0], k[1]) for k in kutular}
    assert olculer >= {("DIS_PARCA_OLCU", 37.5), ("DIS_PARCA_OLCU", 155.75), ("OZEL_PANEL_OLCU_CM", 62.75), ("OZEL_PANEL_OLCU_CM", 120.5)}, kutular
    assert ("DIS_PARCA_OLCU", 193.25) not in olculer, kutular
    for i, (la, ma, a) in enumerate(kutular):
        for lb, mb, b in kutular[i + 1:]:
            assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]), ((la, ma, a), (lb, mb, b))
