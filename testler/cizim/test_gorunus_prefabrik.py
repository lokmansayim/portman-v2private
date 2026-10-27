"""İE-17 · Dört görünüşün yüzeyleri planla aynı: Örnek Şablon köprüsünün Yapı Tanımı (`sablon_kopru.tanim`) → genel motorun sahnesi
(`sahne.sahne_kur`), görünüşleri çizim setinin `gorunus_ciz` / `gorunus_eksen`'i çizer.

Her cephede pencere ve kapı sayısı pano Motor'unun planıyla aynı, yerleri panonun ortasında (D-15: yer Motor'un), kotları BK-13'le
(üst 200, eşik 200 − boy); görünüşün duvar genişliği dış ölçü; çatının tepesi düzlemlerden. Bu bir çizim kilididir; paftaya uygunluk
yan yana kıyasla (İE-17 › Kanıt).
"""
from __future__ import annotations
import collections
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G, sablon_kopru as K  # noqa: E402
from motor.genel import cati_genel, sahne as SH, yapi as Y  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
VERI = KOK / "testler" / "motor" / "veri"
CEPHE = {"-y": "on", "+y": "arka", "-x": "sol", "+x": "sag"}
NORMAL = {"on": (0.0, -1.0), "arka": (0.0, 1.0), "sol": (-1.0, 0.0), "sag": (1.0, 0.0)}


def _ie(ad: str) -> dict:
    return json.loads(((VERI if ad == "PK01" else EVLER) / f"{ad}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=["PK01", "AP13", "AP16", "AP01"])
def ev(request):
    ie = _ie(request.param)
    plan = G.kur(copy.deepcopy(ie))
    t = K.tanim(copy.deepcopy(ie))
    return request.param, ie, plan, t, SH.sahne_kur(Y.kur(t), cati_genel.cati_kur(t["cati"]))


def _kapi_cephesi(plan: G.Plan, d, a) -> str:
    """Dış kapının cephesi: duvarın açık mahal (veranda) ya da dışarı tarafı."""
    dis = plan.mahaller.get(a.arasi[0])
    m = dis.poly.centroid if dis is not None else None
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    if d.yon == "x":
        alt = (m.y < d.c) if m is not None else abs(d.c - y0) < abs(d.c - y1)
        return "on" if alt else "arka"
    sol = (m.x < d.c) if m is not None else abs(d.c - x0) < abs(d.c - x1)
    return "sol" if sol else "sag"


def _plan_acikliklari(plan: G.Plan) -> dict:
    """Dış duvarlardaki pencere ve dış kapılar, cephe başına: (tür, panonun ortası)."""
    out = collections.defaultdict(list)
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if d.tur == "dis" and a and a.tur in ("pencere", "dis_kapi"):
                cephe = CEPHE[a.disari_normal] if a.tur == "pencere" else _kapi_cephesi(plan, d, a)
                out[cephe].append(("pencere" if a.tur == "pencere" else "kapi", round((p.a0 + p.a1) / 2, 2)))
    return {k: sorted(v) for k, v in out.items()}


def _sahne_acikliklari(S: list) -> dict:
    out = collections.defaultdict(list)
    for s in S:
        if s["tur"] not in ("pencere", "kapi"):
            continue
        taraf = next(k for k, n in NORMAL.items() if abs(s["normal"][0] - n[0]) < 1e-6 and abs(s["normal"][1] - n[1]) < 1e-6)
        eks = 0 if taraf in ("on", "arka") else 1
        vs = [p[eks] for p in s["kose"]]
        out[taraf].append((s["tur"], round((min(vs) + max(vs)) / 2, 2)))
    return {k: sorted(v) for k, v in out.items()}


def test_cephe_basina_aciklik_planla_ayni(ev):
    ad, ie, plan, t, S = ev
    assert _sahne_acikliklari(S) == _plan_acikliklari(plan), ad


def test_aciklik_kotlari(ev):
    # BK-13: pencere ve kapının üst kotu 200, eşik 200 − boy (250'lik duvarda lento 50)
    ad, ie, plan, t, S = ev
    for s in S:
        if s["tur"] in ("pencere", "kapi"):
            assert max(p[2] for p in s["kose"]) == pytest.approx(200.0), (ad, s["ad"])


def test_gorunus_genisligi_dis_olcu(ev):
    ad, ie, plan, t, S = ev
    x0, y0, x1, y1 = G.govde_kutusu(plan)
    for taraf, boy in (("on", x1 - x0), ("arka", x1 - x0), ("sol", y1 - y0), ("sag", y1 - y0)):
        us = [p[0] for s in SH.izdusum(S, taraf) if s["tur"] in ("duvar", "kolon") for p in s["k2"]]
        assert max(us) - min(us) == pytest.approx(boy), (ad, taraf)


def test_cati_tepesi_duzlemlerden(ev):
    # görünüşteki en yüksek nokta çatının mahyası (kaplama payı `ust_pay` dahil); mahya kotu düzlemlerden (`cati_kur`)
    ad, ie, plan, t, S = ev
    ck = cati_genel.cati_kur(t["cati"])
    mahya = max(max(k["kot"]) for k in ck["kenarlar"] if k["tur"] == "mahya")
    for taraf in NORMAL:
        z = max(p[1] for s in SH.izdusum(S, taraf) if s["tur"] in ("cati", "alin", "kalkan") for p in s["k2"])
        assert z == pytest.approx(mahya + t["cati"]["ust_pay"], abs=0.05), (ad, taraf)
