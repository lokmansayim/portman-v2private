"""D-49 (Lokman, 4 Kasım 2026; TK-04 kampanyalı prefabrik): ortalanan pencerenin köşeye bakan yanı tek pano.

14:25: "küçük bir hata mutfaktaki 120x180 pencereyi güzel ortalamışsın ama pencerenin sağındaki panel duvarı yanlış ölçeklendirmişsin 2 parça
gibi ölçeklendirmişsin". TK-04'ün mutfağı verandaya bakan duvarında 507–820,75 (2,5 pano); oda ortası ızgara panosundan ¼ panodan çok
kaçtığı için pencereli pano odaya ortalanır (D-15), sağında duvarın ucuna (verandanın açık köşesi) 95,125 kalır: 32,375 + 62,75 değil, tek
pano (`geometry._pencere_yani_tek_pano`). Yan bir T'de bitiyorsa ekler aynen (kör PK-02'nin gerçek listesi: 42,25 + 39; D-29 madde 2).
Madde 3 (19:59, r04): İş Emri tek birleşimi yazar (`yapi.birlesimler`, `geometry._birlesimleri_oku`): 5/D iç köşesinin yönü, C–D panosunun
ortasına gelen T'de 3'lü H yerine çektirme U'su (`veri/TK04_r04.json`).
"""
from __future__ import annotations

import json
import re
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


BRUT_EVLER = {"TK01_r07": VERI / "TK01_r07.json", "TK02": VERI / "TK02.json", "TK03": VERI / "TK03.json", "PK01": VERI / "PK01.json",
              "TK04": VERI / "TK04.json"}


def test_antet_brut_verandali_ve_listeyle_ayni():
    """Madde 2 (Lokman 14:24, "bizde m² bürüt üzerinden verilir ve buna veranda dahildir çünkü çatı kapattığı için"): antetteki brüt çatının
    örttüğü oturum ve yükleme listesindeki `bina_m2` ile aynı sayı (D-28 madde 1). TK-03 87,72: Lokman'ın evinin m²'si."""
    from motor import dxf_out, prefabrik_liste as PL
    beklenen = {"TK01_r07": "90,28", "TK02": "90,28", "TK03": "87,72", "PK01": "60,00", "TK04": "74,19"}
    for ad, yol in BRUT_EVLER.items():
        ie = _oku(yol)
        yazi = dxf_out.alan_yazisi(G.kur(json.loads(json.dumps(ie))))
        assert yazi.startswith(f"{beklenen[ad]} m² brüt · "), (ad, yazi)
        assert f"{PL.model_motor(ie)['brut_m2']:.2f}".replace(".", ",") == beklenen[ad], ad


def _r04():
    return _oku(VERI / "TK04_r04.json")


def test_bes_d_kosesi_ve_cektirme_u():
    """Madde 3 (Lokman 19:59): TK-04 r04'te 5. aks ile D aksının iç köşesinde 5. akstaki duvar geçer: C–D panosu tam pano (62,75 + 59,75 değil),
    ortasına yatak odası 1 – hol duvarı T ile gelir, 3'lü H yerine çektirme U'su; salon kapısının panosu 122,5. Öteki duvarlar r03'le aynı."""
    from motor import prefabrik_liste as PL
    r03 = _r04(); del r03["yapi"]["birlesimler"]
    a, b = G.kur(json.loads(json.dumps(r03))), G.kur(_r04())
    pa = {(d.tur, d.yon, round(d.c, 3), round(d.p0, 3), round(d.p1, 3)): _boylar(d) for d in a.duvarlar}
    pb = {(d.tur, d.yon, round(d.c, 3), round(d.p0, 3), round(d.p1, 3)): _boylar(d) for d in b.duvarlar}
    fark = {k: (pa.get(k), pb.get(k)) for k in set(pa) | set(pb) if pa.get(k) != pb.get(k)}
    assert fark == {("ic", "x", 512.0, 10.0, 378.5): ([(120.5, ""), (125.5, ""), (62.75, ""), (59.75, "")], None),
                    ("ic", "x", 512.0, 10.0, 381.5): (None, [(120.5, ""), (125.5, ""), (125.5, "")]),
                    ("ic", "y", 381.5, 203.25, 512.0): ([(57.75, ""), (125.5, ""), (125.5, "ic_kapi")], None),
                    ("ic", "y", 381.5, 203.25, 509.0): (None, [(57.75, ""), (125.5, ""), (122.5, "ic_kapi")])}, fark
    assert len(b.h_baglantilar) == len(a.h_baglantilar) - 1 and not any(abs(h.x - 318.75) < 1e-6 and abs(h.y - 512.0) < 1e-6
                                                                        for h in b.h_baglantilar)
    Na, Nb = PL.model_motor(json.loads(json.dumps(r03))), PL.model_motor(_r04())
    assert (Na["cektirme_yerleri"]["t_orta"], Nb["cektirme_yerleri"]["t_orta"]) == (0, 1)
    uclu = lambda N: sum(1 for e in N["ekler"] if e["duvar"] == "ic" and e["cins"] == "uclu")
    assert uclu(Nb) == uclu(Na) - 1


def test_birlesim_yanlis_noktada_hata():
    """Yazılan nokta iki iç duvarın L köşesi ya da panonun ortasına gelen T değilse, T geçen duvarın ekindeyse, anahtar yanlışsa sessiz geçilmez
    (K21)."""
    import pytest
    for b, beklenen in (({"nokta_cm": [318.75, 386.5], "kose": "x"}, "L köşesi değil"),
                        ({"nokta_cm": [381.5, 386.5], "t": "cektirme_u"}, "T ile geldiği yer değil"),
                        ({"nokta_cm": [381.5, 386.5], "kose": "z"}, "kose (x | y)"),
                        ({"nokta_cm": [381.5, 386.5]}, "kose (x | y)"),
                        ({"nokta_cm": [380.0, 386.5], "kose": "x"}, "aks üstünde değil"),
                        ({"nokta_cm": ["381.5", 386.5], "kose": "x"}, "kose (x | y)"),
                        # geometri hakemi: T ızgara aksında, geçen duvarın ekinde (orada 3'lü H): yazılsa 3'lü H sessizce kalkardı
                        ({"nokta_cm": [318.75, 261], "t": "cektirme_u"}, "pano ekine denk geliyor"),
                        ({"nokta_cm": [5, 386.5], "t": "cektirme_u"}, "pano ekine denk geliyor")):
        ie = _r04(); ie["yapi"]["birlesimler"] = [b]
        with pytest.raises(G.IsEmriHatasi, match=re.escape(beklenen)):
            G.kur(ie)
