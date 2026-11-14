"""PC-38 · İki cumba: taşan verandanın çatısı ana çatının cumbası (45 m² ev, AP-07 sundurması; D-87).

Lokman, 14 Kasım 2026 08:41 UTC (sundurma eskizine yorum): "cumba çatısı gibi birleştireceksin vadi dere oluşacak böyle eğrelti olmayacak";
08:41:58: "çapraz cumba çatısını nasıl çiziyorsan öyle çiz". Sundurma arkada taşan veranda (`verandalar`, `cati.tip` cumba); ana çatı beşik +
önde yatak odasının çapraz cumbası; `cati.cumbalar`'ın ikinci öğesi `veranda` ile sundurmanın cumbası (`cati_prefabrik.cumba_dikdortgenleri`,
`_iki_cumba`). Tek cumbalı evlerin çatısı eski yoldan, bayt bayt aynı (öteki testler).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from motor import cati_prefabrik as CP
from motor import cephe_gorunus as CG
from motor import geometry as G
from motor import veranda as VR
from motor.genel import cati_genel

KOK = Path(__file__).resolve().parents[2]
AP07 = KOK / "testler" / "havuz" / "is_emirleri" / "AP07.json"


def _ie() -> dict:
    return json.loads(AP07.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ap07():
    ie = _ie()
    plan = G.kur(ie)
    return ie, plan, CP.cati(plan, ie)


def test_iki_cumba_duzlemleri(ap07):
    """Ana çatının iki yüzü de bir cumbaya oyulur; iki cumba ikişer yüz, eğim ana çatınınki."""
    ie, plan, t = ap07
    adlar = sorted(d["ad"] for d in t["duzlemler"])
    assert adlar == ["ana güney", "ana kuzey", "cumba 2 batı", "cumba 2 doğu", "cumba batı", "cumba doğu"]
    assert {round(d["egim"], 4) for d in t["duzlemler"]} == {0.329}
    yuz = {d["ad"]: d["plan"] for d in t["duzlemler"]}
    # sundurmanın cumbası: verandanın dikdörtgeni 188,25–323,75 × 690–820, saçak 30; mahyası ana çatıya 97,75 girer (45° vadi)
    assert [158.25, 720.0] in yuz["ana kuzey"] and [353.75, 720.0] in yuz["ana kuzey"] and [256.0, 622.25] in yuz["ana kuzey"]
    assert sorted(map(tuple, yuz["cumba 2 doğu"])) == [(256.0, 622.25), (256.0, 850.0), (353.75, 720.0), (353.75, 850.0)]
    # öndeki cumba (yatak odası, 0–300, çıkıntı 150) eski yoldaki gibi
    assert [150.0, 300.0] in yuz["ana güney"]


def test_vadiler_ve_mahyalar(ap07):
    """Dört vadi (her cumbada iki), üç mahya; sundurma cumbasının mahyası ana çatının saçak kotundan 32,2 yukarıda."""
    ie, plan, t = ap07
    ck = cati_genel.cati_kur(t)
    turler = [k["tur"] for k in ck["kenarlar"]]
    assert turler.count("vadi") == 4
    assert turler.count("mahya") == 3
    assert not [k for k in ck["kenarlar"] if k["tur"] == "ust"]
    z = {d["ad"]: [p[2] for p in d["ucboyut"]] for d in ck["duzlemler"]}
    assert min(z["cumba 2 doğu"]) == pytest.approx(260.0)
    assert max(z["cumba 2 doğu"]) == pytest.approx(260.0 + 97.75 * 0.329, abs=0.05)


def test_kapi_sundurmanin_altinda(ap07):
    """Çelik kapının panosu sundurmanın altında, ortada; iki yanında birer 62,75 pano (Lokman, 14 Kasım 2026 10:12:22 UTC
    "çelik kapı sundurmanın olduğu pano ile yer değiştirmeli"; 10:34:26 kartı "Evet, doğru"; `dis_pano_dayanagi` x 193,25)."""
    ie, plan, t = ap07
    arka = sorted((round(p.a0, 2), round(p.a1, 2), p.acilim.tur if p.acilim else None)
                  for d in plan.duvarlar if d.yon == "x" and d.c > 600 for p in d.panolar)
    assert arka == [(5.0, 130.5, "pencere"), (130.5, 193.25, None), (193.25, 318.75, "dis_kapi"), (318.75, 381.5, None),
                    (381.5, 507.0, None), (507.0, 632.5, None), (632.5, 745.0, None)]
    x0, _, x1, _ = plan.dis_verandalar[0]["rect"]
    assert (x0 + x1) / 2 == pytest.approx((193.25 + 318.75) / 2)


def test_kalkanlar(ap07):
    """Ana çatının uç kalkanları iki kurulumun birleşimi; sundurmanın alnı verandanın dış kenarında, kolonların arasında."""
    ie, plan, t = ap07
    k = {kk["ad"]: kk for kk in t["kalkanlar"]}
    assert k["batı kalkanı"]["aralik"] == [0.0, 690.0]          # yatak odasının cumbası batı uçla aynı hizada
    assert k["doğu kalkanı"]["aralik"] == [150.0, 690.0]
    assert k["cumba 2'nin kuzey kalkanı"]["konum"] == 820.0
    assert k["cumba 2'nin kuzey kalkanı"]["aralik"] == [188.25, 323.75]
    assert k["cumba 2'nin kuzey kalkanı"]["ust"] == ["cumba 2 batı", "cumba 2 doğu"]


def test_arka_gorunus(ap07):
    """Arka görünüşte sundurmanın alnı ana saçağı keser; öndeki cumbanın vadisi ve topuğu sundurmanın alnının ardında kalır."""
    ie, plan, t = ap07
    r = CG.cati_cizgileri(plan, ie, "arka")
    assert r["topuklar"] == [396.25, 591.75]
    dis = r["cizgiler"][0]
    assert dis[4][0] == pytest.approx(494.0) and dis[4][1] == pytest.approx(292.16, abs=0.05)   # sundurma alnının tepesi
    assert len(r["cizgiler"]) == 3                               # çatı çevresi + sundurma alnının iki eğimi


def test_yan_gorunus_cumba_bandi(ap07):
    """Sol görünüşte sundurmanın cumbası ana çatının eğimine girip biter (dikey kesik yok)."""
    ie, plan, t = ap07
    r = CG.cati_cizgileri(plan, ie, "sol")
    bant = [c for c in r["cizgiler"] if min(p[0] for p in c) < -100]
    assert len(bant) == 1
    assert sorted({round(p[1], 1) for p in bant[0]}) == [260.0, 292.2]


def test_veranda_kolon_ve_kiris(ap07):
    """Cumbalı verandada görünüşe yalnız kolon ve kiriş girer; çatı, saçak ve topuk ana çatının çizgilerinde."""
    ie, plan, t = ap07
    for taraf in ("on", "arka", "sol", "sag"):
        assert {p["tur"] for p in VR.gorunus_parcalari(plan, ie, taraf)} == {"kolon", "kiris"}
    v = plan.dis_verandalar[0]
    assert v["cati"] == {"tip": "cumba", "egim_yuzde": 32.9, "sacak_cm": 30.0, "topuk_cm": 10.0}
    assert len(v["kirisler"]) == 3 and len(v["kolonlar"]) == 2
    with pytest.raises(G.IsEmriHatasi):
        VR.cati(v, ie)
    assert not [u for u in plan.uyarilar if "SUNDURMA" in u]


def test_cizim_dogrulamasi(tmp_path):
    """Ön onay çizimi kurulur, doğrulama geçer."""
    from motor import dxf_out
    r = dxf_out.uret(_ie(), tmp_path)
    assert r["validation_passed"] is True
    assert r["pdf"] and r["tani_pdf"] is None


def test_liste_yazilmaz():
    """Liste iki cumbayı saymaz (tek çapraz cumba kuralı); yanlış liste yazılmaz."""
    from motor import prefabrik_liste as PL
    with pytest.raises(PL.ListeYazilmaz):
        PL.model_motor(_ie())


@pytest.mark.parametrize("bozma, hata", [
    (lambda ie: ie["verandalar"][0].update(cati={"tip": "cumba", "egim_yuzde": 43}), G.IsEmriHatasi),
    (lambda ie: ie["cati"]["cumbalar"].pop(), G.IsEmriHatasi),
    (lambda ie: ie["cati"]["cumbalar"][1].update(cephe="on"), CP.PrefabrikCatiHatasi),
    (lambda ie: ie["cati"]["cumbalar"][1].update(bas_cm=188.25), CP.PrefabrikCatiHatasi),
    (lambda ie: ie["cati"]["cumbalar"][1].update(veranda="YOK"), G.IsEmriHatasi),
    (lambda ie: ie["cati"]["cumbalar"][0].update(ana_makas="cumba_makasindan"), CP.PrefabrikCatiHatasi),
    (lambda ie: ie["cati"]["cumbalar"].pop(0), CP.PrefabrikCatiHatasi),                       # gövde cumbası olmadan veranda cumbası
    (lambda ie: ie["cati"]["cumbalar"][0].update(cikinti_cm=0), CP.PrefabrikCatiHatasi),       # çıkıntısız gövde cumbası (Lokman görmedi)
    (lambda ie: ie["cati"]["cumbalar"][0].update(veranda="SUNDURMA"), CP.PrefabrikCatiHatasi), # iki veranda cumbası
])
def test_yanlis_tanim_hata(bozma, hata):
    """Yanlış yazılmış ikinci cumba sessizce çizilmez (K21)."""
    ie = copy.deepcopy(_ie())
    bozma(ie)
    with pytest.raises(hata):
        plan = G.kur(ie)
        CP.cati(plan, ie)


def test_tek_cumba_eski_yol():
    """Tek cumbada `cumba_dikdortgenleri` eski `_cumba`'nın sonucunu verir."""
    ie = _ie()
    ie["cati"]["cumbalar"] = ie["cati"]["cumbalar"][:1]
    ie.pop("verandalar")
    plan = G.kur(ie)
    kutu = tuple(float(v) for v in G.govde_kutusu(plan))
    ana, rs = CP.cumba_dikdortgenleri(ie["cati"], kutu, plan)
    assert (ana, rs[0]) == CP._cumba(ie["cati"], kutu, plan)
    assert len(rs) == 1
