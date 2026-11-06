"""D-46 (İE-28; Lokman, 4 Kasım 2026 04:35, kart "Paftadan, ev ev") · Beş evin karkaslı kaplama duvar panoları paftadaki gibi.

Hedef örnek `testler/kor/pafta_panolar.json`: montaj paftasından okunan duvar parçaları (yalnız sayılar; paftanın SHA-256'sı kör test
mührünün `montaj paftası` kaydıyla aynı). AP-14, AP-25 ve AP-26'da karkaslı panonun bulunduğu her dış duvar pano pano kıyaslanır (uçlar 3 cm
içinde, karkaslı olup olmadığı aynı); kalan fark yalnız `bilinen_farklar`'daki aralıkta ve iki yanı da orada yazılı boylarla (Motor değişirse
test düşer, fark yeniden yazılır). AP-11 ve AP-18'de paftanın bu sayfası kısmen okunuyor: karkaslı panoların boyu ve AP-11'in oda ortası dizisi.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

KOR = KOK / "testler" / "kor"
HEDEF = json.loads((KOR / "pafta_panolar.json").read_text(encoding="utf-8"))
TOL = HEDEF["tolerans_cm"]
EVLER = sorted(HEDEF["evler"])


def _plan(kod: str):
    return G.kur(json.loads((KOR / "projeler" / kod / "is_emri.json").read_text(encoding="utf-8")))


def _motor_duvari(plan, yon: str, eksen: float, a0: float, a1: float):
    ds = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == yon and abs(d.c - eksen) <= TOL and d.panolar
          and d.panolar[0].a0 - TOL <= a0 and a1 <= d.panolar[-1].a1 + TOL]
    assert len(ds) == 1, (yon, eksen, a0, a1, [d.id for d in ds])
    return ds[0]


def test_hedef_karar_ve_muhur():
    assert HEDEF["karar"] == "D-46" and (KOK / "KARARLAR" / "D-46.md").is_file() and TOL == 3.0
    muhur = json.loads((KOR / "muhur.json").read_text(encoding="utf-8"))
    for kod, ev in HEDEF["evler"].items():
        r = [x for x in muhur["dosyalar"] if x["sha256"] == ev["pafta_sha256"]]
        ap = f"{kod[:2]}-{kod[2:]}"
        assert len(r) == 1 and r[0]["tur"] == "montaj paftası" and ap in r[0]["kod"], kod
        assert json.loads((KOR / "projeler" / kod / "proje.json").read_text(encoding="utf-8"))["ap"] == ap


@pytest.mark.parametrize("kod", [k for k in EVLER if "duvarlar" in HEDEF["evler"][k]])
def test_duvar_duvar_paftadaki_gibi(kod):
    ev, plan = HEDEF["evler"][kod], _plan(kod)
    karkasli_pafta = 0
    for dv in ev["duvarlar"]:
        pp = dv["panolar"]
        d = _motor_duvari(plan, dv["yon"], dv["eksen_cm"], pp[0][0], pp[-1][1])
        mp = [(p.a0, p.a1, p.karkasli) for p in d.panolar]
        farklar = [f for f in ev["bilinen_farklar"] if f["yon"] == dv["yon"] and abs(f["eksen_cm"] - dv["eksen_cm"]) <= TOL]
        icinde = lambda a0, a1: any(f["aralik_cm"][0] - TOL <= a0 and a1 <= f["aralik_cm"][1] + TOL for f in farklar)
        for f in farklar:                                                  # bilinen fark: iki yanı da yazılı boylarla
            lo, hi = f["aralik_cm"]
            pb = [b - a for a, b, *_ in pp if lo - TOL <= a and b <= hi + TOL]
            assert len(pb) == len(f["pafta"]) and all(abs(x - y) <= 0.5 for x, y in zip(pb, f["pafta"])), (kod, f, pb)   # okuma ± 0,5
            assert [round(b - a, 2) for a, b, _k in mp if lo - TOL <= a and b <= hi + TOL] == f["motor"], (kod, f)
        pp_ = [x for x in pp if not icinde(x[0], x[1])]
        mp_ = [x for x in mp if not icinde(x[0], x[1])]
        assert len(pp_) == len(mp_), (kod, dv["not"], pp_, mp_)
        for x, (a0, a1, k) in zip(pp_, mp_):
            assert abs(x[0] - a0) <= TOL and abs(x[1] - a1) <= TOL and (len(x) > 2) == k, (kod, dv["not"], x, (a0, a1, k))
        karkasli_pafta += sum(len(x) > 2 for x in pp)
    assert sum(p.karkasli for p in plan.panolar) == karkasli_pafta, kod      # paftada olmayan karkaslı pano yok


@pytest.mark.parametrize("kod", [k for k in EVLER if "karkasli_boylari_cm" in HEDEF["evler"][k]])
def test_karkasli_boylari(kod):
    ev, plan = HEDEF["evler"][kod], _plan(kod)
    boy = sorted(p.boy for p in plan.panolar if p.karkasli)
    assert len(boy) == len(ev["karkasli_boylari_cm"]) and all(abs(a - b) <= TOL for a, b in zip(boy, ev["karkasli_boylari_cm"])), (kod, boy)
    for dz in ev.get("dizi", []):
        ds = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == dz["yon"] and abs(d.c - dz["eksen_cm"]) <= TOL]
        n = len(dz["boylar"])
        bul = [(d.id, i) for d in ds for i in range(len(d.panolar) - n + 1)
               if all(abs(d.panolar[i + j].boy - b) <= TOL for j, b in enumerate(dz["boylar"]))
               and [j for j in range(n) if d.panolar[i + j].karkasli] == [dz["karkasli"]]]
        assert len(bul) == 1, (kod, dz["not"], bul)
