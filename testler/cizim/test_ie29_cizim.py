"""İE-29 PR-2 · Kör kalan evlerin çizimi: tek uçlu kırma (AP-27) ve dış kapının duvar ucu.

AP-27'nin İş Emri'si `testler/kor/projeler/AP27/is_emri.json` (montaj paftasından; kişi ve bayi adı yok). Sayılar paftadan: makas ve panel
yerleşim planında kırma çizgileri 45° ve tepe sağ duvardan ~500 (eşit eğim), çatı kaplaması planında üç yüzün eğik boyu aynı (562,91),
kırma yüzünün tabanı 1060; yan kesitte tepe 184,26 (10 topuk + 530 × 0,3288). Holün dış kapısı sağ duvarda iki T kavşağının arasındaki
125,5'lik panoda (paftada 430,1–555,7). LLM yok.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP  # noqa: E402
from motor import geometry as G  # noqa: E402

AP27 = KOK / "testler" / "kor" / "projeler" / "AP27" / "is_emri.json"


def _ie() -> dict:
    return json.loads(AP27.read_text(encoding="utf-8"))


def _cati(ie: dict) -> dict:
    return CP.cati(G.kur(copy.deepcopy(ie)), copy.deepcopy(ie))


def test_tek_uclu_kirma_ap27():
    t = _cati(_ie())
    assert t["tip"] == "kirma" and t["tip_adi"] == "kırma"
    d = {x["ad"]: x for x in t["duzlemler"]}
    assert sorted(d) == ["doğu", "güney", "kuzey"]
    assert d["güney"]["plan"] == [[-30.0, -30.0], [803.0, -30.0], [273.0, 500.0], [-30.0, 500.0]]     # mahya 273'e kadar (803 − 530)
    assert d["doğu"]["plan"] == [[803.0, -30.0], [803.0, 1030.0], [273.0, 500.0]]                      # kırma yüzü, taban 1060
    assert {x["egim"] for x in t["duzlemler"]} == {0.3288}                                             # eşit eğim
    assert [(k["ad"], k["konum"], k["aralik"]) for k in t["kalkanlar"]] == [("batı kalkanı", 0.0, [0.0, 1000.0])]
    g = d["güney"]
    assert round(t["topuk"] + (g["plan"][2][1] - g["plan"][0][1]) * g["egim"], 2) == 184.26          # paftanın yan kesitindeki tepe


def test_tek_uclu_kirma_ayna_ve_devrik():
    ie = _ie()
    ie["cati"]["kalkan_ucu"] = "sag"
    t = _cati(ie)
    assert [k["ad"] for k in t["kalkanlar"]] == ["doğu kalkanı"] and "batı" in {x["ad"] for x in t["duzlemler"]}
    ie = _ie()                                                       # mahya y boyunca: kalkan önde ya da arkada
    ie["cati"]["makas_ekseni"] = "x"
    ie["cati"]["kalkan_ucu"] = "on"
    t = _cati(ie)
    assert [k["eksen"] for k in t["kalkanlar"]] == ["y"] and t["kalkanlar"][0]["konum"] == 0.0
    assert len(t["duzlemler"]) == 3


@pytest.mark.parametrize("degis, mesaj", [
    (lambda c: c.update(kalkan_ucu="on"), "sol ya da sag"),
    (lambda c: c.update(kirma_egimleri={"sol": 30, "sag": 35}), "kirma_egimleri"),
    (lambda c: c.update(egim_yuzde=80), "aralık dışı"),
])
def test_tek_uclu_kirma_hatalari(degis, mesaj):
    ie = _ie()
    degis(ie["cati"])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        _cati(ie)


def test_dis_kapi_duvar_ucu():
    plan = G.kur(_ie())
    d = next(d for d in plan.duvarlar if d.yon == "y" and d.tur == "dis" and d.c > 700)
    kapi = [p for p in d.panolar if p.acilim and p.acilim.tur == "dis_kapi"]
    assert [(round(p.a0, 2), round(p.a1, 2)) for p in kapi] == [(430.25, 555.75)]                  # paftada 430,1–555,7
    assert [round(p.boy, 2) for p in d.panolar if 367 < p.a0 < 600] == [62.75, 125.5, 62.75]


def test_dis_kapi_duvar_ucu_cephesiz_hata():
    ie = _ie()
    k = next(a for a in ie["acikliklar"] if a["tur"] == "dis_kapi")
    k.pop("duvar")
    with pytest.raises(G.IsEmriHatasi, match="cephesi yazılmış dış kapıda"):
        G.kur(ie)


# ───────────────────────────── AP-12: yarım duvarlı veranda, beşik + yan yana iki cumba (İE-29 PR-2) ──
# AP-12'nin İş Emri'si `testler/kor/projeler/AP12/is_emri.json` (montaj paftasından). Paftanın montaj planında verandanın önü "Yarım Duvar
# h:80" (panolar 10–507, köşelerde K ve L kaynaklı profilleri), sol duvarı 1588,25; çatı: ana beşik salonun ön duvarında kalkanlı, önünde yan
# yana iki küçük beşik (aşık planı: ana yüzler kalkanın önüne uzar, sol cumbanın iç yüzü 228,5, sağınki 278 ve 80,2'lik basamak).

AP12 = KOK / "testler" / "kor" / "projeler" / "AP12" / "is_emri.json"


def _ie12() -> dict:
    return json.loads(AP12.read_text(encoding="utf-8"))


def test_ap12_yarim_duvar():
    plan = G.kur(_ie12())
    y = [d for d in plan.duvarlar if d.yukseklik is not None]
    assert len(y) == 1 and y[0].yon == "x" and y[0].tur == "dis" and y[0].yukseklik == 80.0
    assert sorted({round(v, 2) for p in y[0].panolar for v in (p.a0, p.a1)}) == [10.0, 135.5, 261.0, 386.5, 507.0]   # paftada 10–507
    assert (y[0].p0, y[0].p1) == (10.0, 507.0) and not any("uzun özel pano" in u for u in plan.uyarilar)
    kose = sorted(tuple(round(v, 2) for v in k.rect) for k in plan.koseler if abs(k.rect[1] - 53.25) < 1e-6)
    assert kose == [(0.0, 53.25, 10.0, 63.25), (507.0, 53.25, 517.0, 63.25)]                    # K ve L: tam kare
    sol = next(d for d in plan.duvarlar if d.yon == "y" and d.tur == "dis" and d.c < 10)
    assert sol.p0 == 63.25 and plan.H - 53.25 == 1588.25          # sol duvar yarım duvarın iç yüzünde biter; sol yan 1588,25 (paftadaki gibi)
    assert G.disari_yon(plan, y[0]) == "-y"


def test_ap12_yan_yana_cumbalar():
    from motor import cati_serit as CS
    from motor.genel import cati_genel
    ie = _ie12()
    t = CS.tanim(G.kur(copy.deepcopy(ie)), ie)
    d = {x["ad"]: x for x in t["duzlemler"]}
    assert sorted(d) == ["ana çatı sağ", "ana çatı sol", "ön sağ cumba sol", "ön sol cumba sağ"]
    assert d["ana çatı sol"]["birlesen"] == ["ana çatı sol", "ön sol cumba sol"]                  # dış yüzler ana çatının devamı
    assert d["ana çatı sağ"]["birlesen"] == ["ana çatı sağ", "ön sağ cumba sağ"]
    assert d["ön sol cumba sağ"]["plan"] == [[258.5, 251.0], [512.0, 251.0], [512.0, 23.25], [258.5, 23.25]]   # 228,5 (aşık planı)
    assert d["ön sağ cumba sol"]["plan"] == [[477.0, 53.25], [512.0, 53.25], [512.0, 251.0], [697.75, 251.0], [697.75, -30.0],
                                            [477.0, -30.0]]                                       # 278 ve 80,25'lik basamak
    assert [(q["ad"], q["b"]) for q in t["parcalar"]] == [("ön sol cumba", [0.0, 517.0]), ("ön sağ cumba", [507.0, 888.5]),
                                                          ("ana çatı", [0.0, 888.5])]           # ikisi de bölme duvarını örter
    k = {x["ad"]: x for x in t["kalkanlar"]}
    assert k["ana çatı ön kalkanı"]["konum"] == 251.0 and k["ana çatı ön kalkanı"]["alt"] == ["ön sağ cumba sol", "ön sol cumba sağ"]
    ck = cati_genel.cati_kur(t)
    vadi = sorted((round(e["p"][1], 2), round(e["q"][1], 2)) for e in ck["kenarlar"] if e["tur"] == "vadi")
    assert vadi == [(23.25, 53.25), (53.25, 251.0)] and all(e["p"][0] == 512.0 for e in ck["kenarlar"] if e["tur"] == "vadi")
    kk = {x["ad"]: x for x in ck["kalkanlar"]}
    assert round(kk["ön sol cumba ön kalkanı"]["tepe"]) == 385 and round(kk["ön sağ cumba ön kalkanı"]["tepe"], 1) == 362.6
    assert round(kk["ana çatı ön kalkanı"]["tepe"], 1) == 445.9 and kk["ana çatı ön kalkanı"]["alan_m2"] < 3.2   # yalnız iki cumbanın üstü


def test_ap12_makas_plani():
    """Paftanın makas planı (s. 5): ana çatıda 13 makas (MK01–12, MK14); pencere panolarının yanındaki 62,75'lik panoların ekinde de
    makas var: iki saçak duvarının ortak eki (820,75) her zaman makas alır (İE-29 PR-2). Cumbalarda paftada 3 + 3 (iç uçta MK13, MK18);
    bizde 2 + 2: cumbanın iç ucunda makas yok (D-44, Lokman 2 Kasım 16:50)."""
    from motor import cati_serit as CS
    ie = _ie12()
    t = CS.tanim(G.kur(copy.deepcopy(ie)), ie)
    mk = {p["ad"]: [m["konum"] for m in p["makaslar"]] for p in t["parcalar"]}
    assert mk["ana çatı"] == [256.0, 381.5, 507.0, 632.5, 758.0, 820.75, 883.5, 1009.0, 1134.5, 1260.0, 1385.5, 1511.0, 1636.5]
    assert mk["ön sol cumba"] == [58.25, 130.5] and mk["ön sağ cumba"] == [5.0, 130.5]
    assert all(p["makas_yeri"] == "pano ekleri" for p in t["parcalar"]) and not t["uyarilar"]


@pytest.mark.parametrize("ekler, ortak, beklenen", [
    ([30.0, 67.75, 130.5, 193.25, 256.0], (), [5.0, 130.5, 256.0, 381.5]),                 # ortak ek yok: en uzak ek
    ([30.0, 67.75, 130.5, 193.25, 256.0], (193.25,), [5.0, 130.5, 193.25, 256.0, 381.5]),  # ortak ek her zaman makas
    ([7.0, 135.5, 261.0], (7.0,), [5.0, 135.5, 261.0, 381.5]),     # ortak ekle sınır aşılıyor (7 → 135,5 > 125,5): yalnız en uzak ek
])
def test_makas_ortak_ek(ekler, ortak, beklenen):
    from motor import cati_serit as CS
    yer, duzenli = CS._makas_yerleri(5.0, 381.5, True, ekler, 5.0, list(ortak))
    assert duzenli and yer == beklenen


def test_ap12_gorunusler():
    from motor import cephe_gorunus as CGo
    plan = G.kur(_ie12())
    on = CGo.cephe(plan, "on")
    assert on["yarim"] == [{"u0": 10.0, "u1": 507.0, "z1": 80.0, "derz": [135.5, 261.0, 386.5]}]
    assert [(a["tur"], a.get("olcu")) for a in on["acikliklar"]] == [("pencere", "160x180"), ("dis_kapi", None), ("pencere", "160x180")]
    assert not any(10 < u < 507 and u in (135.5, 261.0) for u in on["derz"])                       # yarım duvarın derzi tam boy değil
    sag = CGo.cephe(plan, "sag")                                                                  # açık verandanın ardındaki duvar ve kapısı
    assert ("dis_kapi", 148.25) in [(a["tur"], round(a["u0"], 2)) for a in sag["acikliklar"]]
    assert 130.5 in sag["derz"] and 376.5 not in sag["derz"] and 386.5 not in sag["derz"]         # salonun ardında kalan kısım çizilmez


@pytest.mark.parametrize("degis, mesaj", [
    (lambda ie: ie["duvarli_sinirlar"][1].update(yukseklik_cm=280), "bina yüksekliğinden alçak"),
    (lambda ie: ie["duvarli_sinirlar"][1].pop("parca_cm"), "parca_cm ile yazılır"),
])
def test_ap12_yarim_duvar_hatalari(degis, mesaj):
    ie = _ie12()
    degis(ie)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(ie)


@pytest.mark.parametrize("degis, mesaj", [
    (lambda c: c["yan_yana_cumbalar"].update(cephe="sol"), "ana çatının bir ucunda"),
    (lambda c: c["yan_yana_cumbalar"].update(bolme_cm=600), "bölme ekseninde"),
    (lambda c: c["yan_yana_cumbalar"].update(kalkan_mahali="VERANDA"), "kapalı bir mahal"),
    (lambda c: c["yan_yana_cumbalar"].update(fazla=1), "yok sayılmaz"),
])
def test_ap12_yan_yana_hatalari(degis, mesaj):
    from motor import cati_serit as CS
    ie = _ie12()
    degis(ie["cati"])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        CS.tanim(G.kur(copy.deepcopy(ie)), ie)


# ───────────────────────────── AP-17: kubbe (İE-29 PR-2) ─────────────────────────────
# AP-17'nin İş Emri'si `testler/kor/projeler/AP17/is_emri.json` (montaj paftasından; kişi ve bayi adı yok). Paftanın montaj planında salonun
# ön duvarında kubbe: dış yüzde ölçü zinciri 58,61 · 133,78 · 58,61 (taban 251), iki yanında 94,13'lük pano; yan panolar 790 (59/170), ön
# pano 105/170; salonun iç ölçüsü 494,86 kubbenin ön panosunun iç yüzünden. Öteki duvarların pano hatları paftanın dörtgenlerinden.

AP17 = KOK / "testler" / "kor" / "projeler" / "AP17" / "is_emri.json"


def _ie17() -> dict:
    return json.loads(AP17.read_text(encoding="utf-8"))


def _hat(plan, yon: str, c: float) -> list:
    return sorted({round(v, 1) for d in plan.duvarlar if d.yon == yon and abs(d.c - c) < 6 for p in d.panolar for v in (p.a0, p.a1)})


def test_ap17_pano_hatlari():
    plan = G.kur(_ie17())
    assert _hat(plan, "x", 5) == [444.2, 538.4, 789.4, 883.5]                                    # 94,13 · kubbe · 94,13
    assert _hat(plan, "x", 193.25) == [5.0, 67.8, 318.8, 444.2]                                  # verandanın ardı: yarım, 180/200 (251), kapı
    assert _hat(plan, "x", 893.5) == [5.0, 130.5, 256.0, 381.5, 507.0, 632.5, 695.2, 820.8, 883.5]   # yatak odası 2'nin penceresi ortada
    assert _hat(plan, "y", 5) == [198.2, 261.0, 386.5, 449.2, 574.8, 637.5, 763.0, 888.5]         # 449,25 aksına dayalı (yarım panolar)
    assert _hat(plan, "y", 883.5) == [10.0, 135.5, 261.0, 386.5, 449.2, 574.8, 637.5, 763.0, 888.5]
    assert _hat(plan, "y", 318.75) == _hat(plan, "y", 507.0) == [449.2, 574.8, 637.5, 763.0, 888.5]   # holün ve banyonun iki duvarı
    assert not any("uzun özel pano" in u for u in plan.uyarilar)


def test_ap17_kubbe():
    plan = G.kur(_ie17())
    assert len(plan.kubbeler) == 1
    kb = plan.kubbeler[0]
    assert (kb["cephe"], kb["mahal"], kb["u0"], kb["u1"]) == ("on", "SALON", 538.375, 789.375)
    dis, ic = kb["dis"], kb["ic"]
    assert [round(b[0] - a[0], 2) for a, b in zip(dis, dis[1:])] == [58.61, 133.78, 58.61]         # paftanın zinciri
    assert round(dis[1][1], 2) == round(dis[2][1], 2) == -58.61                                   # çıkma
    assert [q["boy"] for q in kb["panolar"]] == [79.0, 125.5, 79.0]
    assert [q["pencere"] for q in kb["panolar"]] == ["59x170", "105x170", "59x170"]
    assert round(ic[2][0] - ic[1][0], 2) == 125.5                                                 # ön panonun iç yüzü
    assert round(446.25 - ic[1][1], 2) == 494.86                                                  # salonun paftadaki iç ölçüsü
    salon = plan.mahaller["SALON"]
    assert round(salon.alan_m2, 2) == 30.70 and round(salon.ek[0].area / 1e4, 3) == 1.079        # kubbenin içi salonda (paftada 30,6)
    p = next(p for d in plan.duvarlar for p in d.panolar if p.acilim and p.acilim.tur == "kubbe")
    assert p.rects() == [] and p.boy == 251.0                                                    # taban boşluk


def test_ap17_cizim(tmp_path):
    import ezdxf
    from motor import dxf_out
    r = dxf_out.uret(_ie17(), tmp_path)
    assert r["validation_passed"] and r["pdf"]
    doc = ezdxf.readfile(tmp_path / r["dxf"])
    msp = doc.modelspace()
    kub = [e for e in msp.query('LWPOLYLINE[layer=="KUBBE"]') if e.closed and max(p[0] for p in e.get_points("xy")) < 1100]
    assert len(kub) == 10                                                                         # 6 pano parçası, 2 köşe direği, 2 kama
    from shapely.geometry import Polygon
    salon = next(e for e in msp.query('LWPOLYLINE[layer=="NET_ALAN_GEOMETRISI"]') if e.get_xdata("PORTMAN_ROOM")[0].value == "SALON")
    assert round(Polygon(list(salon.get_points("xy"))).area / 1e4, 2) == 30.70


def test_ap17_kubbe_gorunusu():
    from motor import cephe_gorunus as CGo
    ie = _ie17()
    plan = G.kur(copy.deepcopy(ie))
    r = {t: CGo.cati_cizgileri(plan, ie, t)["kubbe"] for t in CGo.TARAFLAR}
    assert [a["olcu"] for a in r["on"]["pencereler"]] == ["59x170", "105x170", "59x170"]
    k30 = round(30 * 2 ** 0.5, 4)                                                                 # D-54: saçak 30, 45° yüzde gönye
    assert (r["on"]["u0"], r["on"]["u1"]) == (round(538.375 - k30, 4), round(789.375 + k30, 4))   # saçak düz duvarın yüzüne uzar
    assert max(z for k in r["on"]["dolgu"] for _u, z in k) == 200 + 35                            # tepe düz duvarda, kubbe duvarından 35
    assert min(z for k in r["on"]["dolgu"] for _u, z in k if _u < 538.375 - 1) == 200             # kubbe duvarı ana duvardan 50 alçak
    assert r["arka"]["dolgu"] == [] and r["arka"]["pencereler"] == []                             # gövdenin ardında
    for t, uc in (("sol", 898.5), ("sag", 0.0)):
        k = r[t]
        assert [a["olcu"] for a in k["pencereler"]] == ["59x170"]
        ust = [u for k2 in k["dolgu"] for u, z in k2 if z > 200.5]                                # topuk ve çatı
        assert round(min(abs(u - uc) for u in ust), 2) == 0.0                                     # ana çatının saçağının altında, örtülmez
        assert round(max(abs(u - uc) for u in ust), 2) == round(58.61 + 30, 2)                    # kubbenin saçağı çıkmadan 30 dışarıda
        assert max(z for k2 in k["dolgu"] for _u, z in k2) == 235
    assert "kubbe" not in CGo.cati_cizgileri(G.kur(_ie12()), _ie12(), "on")                       # kubbesiz evde anahtar yok


@pytest.mark.parametrize("degis, mesaj", [
    (lambda k: k.update(mahal="VERANDA"), "kapalı bir mahalin"),
    (lambda k: k.update(bas_cm=700), "sığmıyor"),
    (lambda k: k.update(cephe="arka"), "sığmıyor"),
    (lambda k: k.update(cephe="ust"), "cephesi bilinmiyor"),
    (lambda k: k.update(yan_pencere="76x170"), "penceresine dar"),
    (lambda k: k.update(renk="beyaz"), "kubbeler girişi"),
])
def test_ap17_kubbe_hatalari(degis, mesaj):
    ie = _ie17()
    degis(ie["kubbeler"][0])
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(ie)


def test_ap17_iki_kubbe_ust_uste():
    ie = _ie17()
    ie["kubbeler"].append({"cephe": "on", "mahal": "SALON", "bas_cm": 600})
    with pytest.raises(G.IsEmriHatasi, match="üst üste"):
        G.kur(ie)


# ───────────────────────────── AP-24: AP-03'ün kubbeli eşi (İE-29 PR-2) ─────────────────────────────
# AP-24'ün İş Emri'si `testler/kor/projeler/AP24/is_emri.json` (montaj paftasından; kişi ve bayi adı yok). Gövde AP-03'ünki (763 × 835,75,
# sağ arkada veranda), kubbe yaşama alanının sağ duvarında. Beklenen pano hatları paftanın montaj planındaki dörtgenlerden (gerçek çerçeve,
# y önden; 0,15 payla). Paftanın üç köşesi `dizilim.kose_uzayan`, verandanın iç duvarı (125,5 · 62,75 · 125,5 · 120,5) yardımcı akslara
# dayalı. Veranda çatısı paftanın makas planındaki gibi %20 (`yuz_egimi_yuzde`; MK09 planda 0,61 eğik), AP-03'te ana eğim (45°).

AP24 = KOK / "testler" / "kor" / "projeler" / "AP24" / "is_emri.json"
AP03 = KOK / "testler" / "cizim" / "evler" / "AP03.json"
PAFTA24 = {   # (yön, eksen): paftadaki pano uçları (montaj planının dörtgenleri)
    ("x", 5.0): [4.88, 67.71, 193.14, 318.79, 444.21, 569.64, 632.47, 757.89],
    ("x", 830.75): [4.88, 67.71, 193.14, 318.79, 444.21, 569.64, 632.47],
    ("x", 512.0): [9.99, 67.71, 193.14, 315.68],
    ("x", 389.5): [196.24, 318.79],
    ("x", 261.0): [9.99, 67.71, 193.14],
    ("y", 5.0): [9.99, 135.44, 260.89, 386.57, 512.02, 637.47, 762.92, 825.76],
    ("y", 193.25): [264.0, 389.45, 508.91],
    ("y", 318.75): [9.99, 135.44, 260.89, 386.57, 512.02, 637.47, 762.92, 825.76],
    ("y", 632.5): [391.45, 516.9, 579.74, 705.19, 825.76],
}


def _ie24() -> dict:
    return json.loads(AP24.read_text(encoding="utf-8"))


def _uclar(plan, yon: str, c: float) -> list:
    return sorted({v for d in plan.duvarlar if d.yon == yon and abs(d.c - c) < 0.5 for p in d.panolar for v in (p.a0, p.a1)})


def test_ap24_pano_hatlari():
    plan = G.kur(_ie24())
    for (yon, c), pafta in PAFTA24.items():
        bizim = _uclar(plan, yon, c)
        assert len(bizim) == len(pafta) and max(abs(a - b) for a, b in zip(bizim, pafta)) < 0.15, (yon, c, bizim, pafta)
    assert [round(v, 2) for v in _uclar(plan, "y", 758.0)] == [10.0, 72.61, 323.61, 386.5]   # paftada 9,99 · 72,61 · 323,73 · 386,57 (kubbe 251)
    assert [round(v, 2) for v in _uclar(plan, "x", 386.5)] == [632.5, 753.0]                   # paftada 632,47 · 752,79 (köşe parçası 10,21)
    assert not any("kısa pano" in u for u in plan.uyarilar)
    assert G.ana_akslar("y") == [10.0, 72.75, 198.25, 323.75, 389.5, 449.25, 574.75, 700.25, 825.75]   # yardımcı akslar çizilmez


def test_ap24_kubbe_ve_alanlar():
    plan = G.kur(_ie24())
    kb, = plan.kubbeler
    assert (kb["cephe"], kb["mahal"], round(kb["u0"], 2), round(kb["u1"], 2)) == ("sag", "YAŞAMA ALANI", 72.61, 323.61)
    assert [round(b[1] - a[1], 2) for a, b in zip(kb["dis"], kb["dis"][1:])] == [58.61, 133.78, 58.61]
    assert round(kb["dis"][1][0] - 763.0, 2) == 58.61
    # D-54: kubbe çatısının saçağı ana çatınınki gibi 30; ön yüzde çıkmadan 30 dışarıda, 45° yüzlerde dik 30 (gönye), düz duvarın yüzüne uzar
    assert G.kubbe_sacagi(kb, 30) == [(763.0, 30.1836), (851.61, 118.7936), (851.61, 277.4264), (763.0, 366.0364)]
    alan = {ad: round(m.alan_m2, 2) for ad, m in plan.mahaller.items()}
    assert alan == {"YATAK ODASI 1": 9.50, "BANYO": 4.42, "HOL": 1.46, "YATAK ODASI 2": 9.12, "YAŞAMA ALANI": 30.68, "VERANDA": 5.58}
    # paftada 9,45 · 4,34 · 1,61 · 9,13 · 30,73 · 5,61


def test_ap24_veranda_catisi():
    from motor import sunum
    ie = _ie24()
    t = sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie)
    d = {z["ad"]: z for z in t["duzlemler"]}
    v = d["VERANDA çatısı"]
    assert v["egim"] == pytest.approx(0.20)
    assert [[round(a, 1) for a in q] for q in v["plan"]] == [[637.5, 771.2], [793.0, 865.8], [793.0, 421.5], [637.5, 326.9]]
    assert 865.75 - v["plan"][0][1] == pytest.approx(155.5 * 20 / 32.88, abs=0.01)              # kırmanın duvardaki ucu (paftada 94–95)
    hat = {h["tur"]: (h["p"], h["q"]) for h in t["hatlar"]}
    assert hat["kirma"] == ([793.0, 865.75], [667.5, 789.41]) and hat["dere"] == ([667.5, 345.16], [793.0, 421.5])
    mk = t["mahal_catilari"][0]["makaslar"]
    assert [m["rol"] for m in mk] == ["kisa"] * 4 + ["capraz"]
    assert mk[-1]["plan_boy_cm"] == round(155.5 * (1 + (20 / 32.88) ** 2) ** 0.5, 2)        # kırmanın doğrultusunda


def test_yuz_egimi_ana_egimle_ayni_cati():
    """`yuz_egimi_yuzde` ana eğime eşitse çatı yazılmamış hâliyle aynı (AP-03, 45°); tek_yon'da yazılmaz."""
    from motor import sunum
    ie = json.loads(AP03.read_text(encoding="utf-8"))
    ie2 = copy.deepcopy(ie)
    ie2["cati"]["mahal_catilari"][0]["yuz_egimi_yuzde"] = ie["cati"]["egim_yuzde"]
    a, b = (sunum.cati_tanimi(G.kur(copy.deepcopy(x)), x) for x in (ie, ie2))
    assert a["duzlemler"] == b["duzlemler"] and a["hatlar"] == b["hatlar"] and a["kalkanlar"] == b["kalkanlar"]
    assert a["mahal_catilari"][0]["makaslar"] == b["mahal_catilari"][0]["makaslar"]
    ie3 = copy.deepcopy(ie)
    ie3["cati"]["mahal_catilari"][0].update(tip="tek_yon", egim_yuzde=10, yuz_egimi_yuzde=20)
    with pytest.raises(CP.PrefabrikCatiHatasi, match="yalnız köşe kırmasında"):
        sunum.cati_tanimi(G.kur(copy.deepcopy(ie3)), ie3)


def test_ap24_cizim(tmp_path):
    import ezdxf
    from motor import dxf_out
    r = dxf_out.uret(_ie24(), tmp_path)
    assert r["validation_passed"] and r["pdf"] and not r["warnings"]
    msp = ezdxf.readfile(tmp_path / r["dxf"]).modelspace()
    kub = [e for e in msp.query('LWPOLYLINE[layer=="KUBBE"]') if e.closed and max(p[0] for p in e.get_points("xy")) < 1100]
    assert len(kub) == 10


@pytest.mark.parametrize("giris, mesaj", [
    ({"x": 318.75, "y": 446.25}, "kose_uzayan girişi"),
    ({"x": 318.75, "y": 446.25, "uzayan": "z"}, "kose_uzayan girişi"),
    ({"x": 444.25, "y": 446.25, "uzayan": "x"}, "L köşesine düşmüyor"),
])
def test_kose_uzayan_hatalari(giris, mesaj):
    ie = _ie24()
    ie["yapi"]["dizilim"]["kose_uzayan"].append(giris)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(ie)


# ---------------- AP-23 (ikiz ev: iki AP-03 dairesi aynalı, ortada 10'luk ortak duvar, iki kubbe, iki %20 veranda)
AP23 = KOK / "testler" / "kor" / "projeler" / "AP23" / "is_emri.json"
PAFTA23 = {   # (yön, eksen): paftadaki pano uçları (montaj planının dörtgenleri; paftanın çiziminde ~0,2 kayma: 10 → 10,21)
    ("x", 5.0): [4.87, 130.41, 255.95, 381.49, 507.04, 569.69, 695.23, 757.88, 820.77, 946.08, 1008.96, 1134.51, 1259.81, 1385.35, 1510.89],
    ("x", 261.0): [321.63, 381.49, 504.02, 1011.98, 1134.51, 1194.14],
    ("x", 386.5): [9.98, 130.41, 135.52, 255.95, 318.61, 444.15, 507.04, 632.34, 753.01, 762.99, 883.42, 1008.96, 1071.62, 1197.16, 1259.81,
                   1380.48, 1385.35, 1505.79],
    ("x", 830.75): [130.41, 255.95, 381.49, 507.04, 632.34, 757.88, 883.42, 1008.96, 1134.51, 1259.81, 1385.35],
    ("y", 5.0): [10.21, 72.88, 323.76, 386.66],
    ("y", 130.5): [391.53, 512.22, 574.88, 700.44, 825.77],
    ("y", 318.75): [10.21, 135.54, 261.1, 383.64],
    ("y", 507.0): [10.21, 135.54, 261.1, 383.64],
    ("y", 758.0): [10.21, 135.54, 261.1, 386.66, 512.22, 574.88, 700.44, 825.77],
    ("y", 1009.0): [10.21, 135.54, 261.1, 383.64],
    ("y", 1197.25): [10.21, 135.54, 261.1, 383.64],
    ("y", 1385.5): [391.53, 512.22, 574.88, 700.44, 825.77],
    ("y", 1511.0): [10.21, 72.88, 323.76, 386.66],
}


def _ie23() -> dict:
    return json.loads(AP23.read_text(encoding="utf-8"))


def test_ap23_pano_hatlari():
    plan = G.kur(_ie23())
    hatlar = {(d.yon, round(d.c, 2)) for d in plan.duvarlar}
    assert hatlar == set(PAFTA23)
    for (yon, c), pafta in PAFTA23.items():
        bizim = _uclar(plan, yon, c)
        assert len(bizim) == len(pafta) and max(abs(a - b) for a, b in zip(bizim, pafta)) < 0.25, (yon, c, bizim, pafta)
    assert not plan.uyarilar


def test_ap23_ortak_duvar():
    """İki dairenin arasındaki duvar dış duvar (10'luk, dış pano); görünüşte yok; salonların ön duvarı onun iki yüzünde biter (iki T)."""
    plan = G.kur(_ie23())
    od, = [d for d in plan.duvarlar if d.yon == "y" and abs(d.c - 758.0) < 1e-6]
    assert (od.tur, 2 * od.h, od.p0, od.p1) == ("dis", 10.0, 10.0, 825.75)
    assert G.disari_yonleri(plan, od) == []
    on = sorted((d.p0, d.p1) for d in plan.duvarlar if d.yon == "x" and d.tur == "ic" and abs(d.c - 386.5) < 1e-6)
    assert on == [(135.5, 753.0), (763.0, 1380.5)]
    assert not plan.arti_birlesimler
    ic = G.kur(_ie23() | {"ortak_duvarlar": []})                     # yazılmazsa iç duvar (6), ön duvar geçer
    ws = [d for d in ic.duvarlar if d.yon == "y" and abs(d.c - 758.0) < 1e-6]
    assert ws and all(d.tur == "ic" and 2 * d.h == 6.0 for d in ws)


@pytest.mark.parametrize("degis, mesaj", [
    ({"ortak_duvarlar": [["SALON + MUTFAK 1"]]}, "iki ayrı mahal"),
    ({"ortak_duvarlar": [["SALON + MUTFAK 1", "SALON + MUTFAK 1"]]}, "iki ayrı mahal"),
    ({"ortak_duvarlar": [["SALON + MUTFAK 1", "YOK"]]}, "bilinmeyen mahal"),
    ({"ortak_duvarlar": [["SALON + MUTFAK 1", "VERANDA 1"]]}, "açık mahal"),
    ({"ortak_duvarlar": [["SALON + MUTFAK 1", "BANYO 2"]]}, "komşu değil"),
])
def test_ortak_duvar_hatalari(degis, mesaj):
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(_ie23() | degis)


def test_ap23_kubbe_ve_alanlar():
    plan = G.kur(_ie23())
    k1, k2 = sorted(plan.kubbeler, key=lambda k: k["mahal"])
    assert (k1["cephe"], k1["mahal"], k2["cephe"], k2["mahal"]) == ("sol", "YATAK ODASI 1", "sag", "YATAK ODASI 2")
    for kb in (k1, k2):
        assert (round(kb["u0"], 2), round(kb["u1"], 2)) == (72.75, 323.75)          # paftada 72,88 · 323,76 (onay paftası 72,75 · 251)
    assert round(-k1["dis"][1][0], 2) == round(k2["dis"][1][0] - 1516.0, 2) == 58.61
    s1, s2 = G.kubbe_sacagi(k1, 30), G.kubbe_sacagi(k2, 30)                     # D-54: iki kubbenin saçağı birbirinin aynası
    assert [(round(-x, 4), y) for x, y in s1] == [(round(x - 1516.0, 4), y) for x, y in s2] and s2[1] == (1604.61, 118.9336)
    alan = {ad: round(m.alan_m2, 2) for ad, m in plan.mahaller.items()}
    for n in (1, 2):
        assert {k[:-2]: v for k, v in alan.items() if k.endswith(str(n))} == {
            "SALON + MUTFAK": 26.94, "VERANDA": 5.58, "ÇOCUK ODASI": 9.08, "HOL": 2.18, "BANYO": 4.52, "YATAK ODASI": 12.47}
    # paftada 26,75 · 5,51 · 9,14 · 2,23 · 4,52 · 12,60


def test_ap23_catisi():
    """Sağ veranda AP-24'ünkiyle aynı (x + 753), sol veranda onun aynası; her verandanın deresi kendi yanındaki cumbayla (iki uçta cumba)."""
    from motor import sunum
    ie, ie24 = _ie23(), _ie24()
    d = {z["ad"]: z for z in sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie)["duzlemler"]}
    d24 = {z["ad"]: z for z in sunum.cati_tanimi(G.kur(copy.deepcopy(ie24)), ie24)["duzlemler"]}
    sag = [[round(x, 2), round(y, 2)] for x, y in d["VERANDA 2 çatısı"]["plan"]]
    assert sag == [[round(x + 753, 2), round(y, 2)] for x, y in d24["VERANDA çatısı"]["plan"]]
    sol = [[round(x, 2), round(y, 2)] for x, y in d["VERANDA 1 çatısı"]["plan"]]
    assert sorted(sol) == sorted([[round(1516 - x, 2), y] for x, y in sag])
    assert d["VERANDA 1 çatısı"]["egim"] == d["VERANDA 2 çatısı"]["egim"] == pytest.approx(0.20)
    t = sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie)
    dere = {tuple(h["duzlemler"]) for h in t["hatlar"] if h["tur"] == "dere"}
    assert dere == {("VERANDA 1 çatısı", "sol cumba arka"), ("VERANDA 2 çatısı", "sağ cumba arka")}


def test_ap23_cizim(tmp_path):
    import ezdxf
    from motor import dxf_out
    r = dxf_out.uret(_ie23(), tmp_path)
    assert r["validation_passed"] and r["pdf"] and not r["warnings"]
    msp = ezdxf.readfile(tmp_path / r["dxf"]).modelspace()
    od = sorted((round(e.dxf.insert[1], 2), e.dxf.name) for e in msp.query('INSERT[layer=="DIS_DUVAR_100"]')
                if abs(e.dxf.insert[0] - 753.0) < 1e-6 and abs(e.dxf.rotation) < 1e-6)     # ortak duvarın panoları dış pano (10'luk)
    assert [y for y, _ in od] == [10.0, 135.5, 261.0, 386.5, 512.0, 574.75, 700.25]
    assert sum("627p5" in n for _, n in od) == 1 and sum("1255p0" in n for _, n in od) == 6
    kub = [e for e in msp.query('LWPOLYLINE[layer=="KUBBE"]') if e.closed and max(p[0] for p in e.get_points("xy")) < 1700]
    assert len(kub) == 20
