"""İE-17 PR-2 · Dört evin (AP-15, AP-09, AP-03, AP-22) kat planı için Motor'a eklenenler — Motor kilidi.

Paftaya uygunluk `testler/cizim/test_pafta_kiyasi.py`'de (paftadan ölçülen değerler, kalan farklar gerekçeli). Hepsi yalnız yeni durumda
çalışır; anahtarsız ve var olan İş Emri'lerinin planı değişmez (`testler/referans/dogrula.py`, PR-1 evleri, PK-01, TK-03).

- `yapi.kose_kaynagi: pafta` (AP-15): `kisa_kenar: y` makas x ile de çizilir, uyarıyla; yazılmamışsa K21 hatası aynen.
- Panodan geniş pencerenin yanında tam pano yoksa (AP-09 ön duvar, 170/180): odanın duvar parçası 62,75 + pencereli pano + 62,75.
- `dizilim.dis_pano_dayanagi[].ic_duvarlar: true` (AP-03): aralıktaki iç duvarlar da aynı akslara dayanır.
- İş Emri dikmesinin tamamen örttüğü köşe parçası çizilmez (AP-09: verandanın açık kenarı gövde köşesinde biter; paftada orada kolon).
- Çatı: girintili gövdenin beşiğinin izi verandayı dikmeleriyle içine alır (`cati_serit.cati_izi`, AP-15); çıkıntılı çapraz cumba
  (`cati_prefabrik`, AP-22) gövdenin girintisiyle denetlenir. Ön onay PDF'inde yakın aksların adları kademeli (`dxf_out._kademe`).
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
YENI = ("AP15", "AP09", "AP03", "AP22")
# Net alanlar paftanın oda etiketinden (m²; AP-15 ve AP-03 paftasında alan yazılı değil)
PAFTA_ALAN = {
    "AP09": {"ODA 1": 9.13, "BANYO": 3.28, "ODA 2": 11.37, "SALON+MUTFAK": 32.51, "VERANDA": 9.29},
    "AP22": {"YATAK ODASI": 14.51, "BANYO": 6.07, "ÇOCUK ODASI": 13.76, "HOL": 7.95, "SALON": 16.09, "MUTFAK": 11.45, "VERANDA": 7.15},
}


def _ie(ad: str) -> dict:
    return json.loads((EVLER / f"{ad}.json").read_text(encoding="utf-8"))


def _kur(ie: dict) -> G.Plan:
    return G.kur(copy.deepcopy(ie))


def _duvar(plan, yon, c):
    return next(d for d in plan.duvarlar if d.yon == yon and abs(d.c - c) < 1e-6)


@pytest.mark.parametrize("ad", YENI)
def test_dort_ev_kuruluyor(ad):
    # yalnız AP-15'te köşe istisnasının uyarısı; başka uyarı yok
    plan = _kur(_ie(ad))
    beklenen = ["Köşe paftadan"] if ad == "AP15" else []
    assert [u.split(" (")[0] for u in plan.uyarilar] == beklenen, plan.uyarilar


@pytest.mark.parametrize("ad", sorted(PAFTA_ALAN))
def test_net_alanlar_paftanin_etiketiyle(ad):
    plan = _kur(_ie(ad))
    alan = {m: round(v.alan_m2, 2) for m, v in plan.mahaller.items()}
    assert alan.keys() == PAFTA_ALAN[ad].keys()
    assert all(abs(alan[m] - v) <= 0.05 for m, v in PAFTA_ALAN[ad].items()), alan


# ---------------- köşe paftadan (AP-15)

def test_kose_kaynagi_pafta():
    ie = _ie("AP15")
    assert ie["yapi"]["kisa_kenar"] == "y" and ie["cati"]["makas_ekseni"] == "x" and ie["yapi"]["kose_kaynagi"] == "pafta"
    plan = _kur(ie)
    assert any(u.startswith("Köşe paftadan (yapi.kose_kaynagi: pafta): makas x'i geçiyor") for u in plan.uyarilar)
    assert G.KISA_KENAR == "y"
    x = copy.deepcopy(ie); x["yapi"].pop("kose_kaynagi")
    with pytest.raises(G.IsEmriHatasi, match="kisa_kenar: y yalnız makas y'yi geçerken .*kose_kaynagi: pafta"):
        G.kur(x)
    x = copy.deepcopy(ie); x["yapi"]["kose_kaynagi"] = "olcu"
    with pytest.raises(G.IsEmriHatasi, match="kose_kaynagi bilinmiyor"):
        G.kur(x)
    assert G.KISA_KENAR == "x"                                      # hatadan sonra varsayılana döner


def test_kose_kaynagi_makas_y_de_uyarisiz():
    # makas y'yi geçiyorsa kural zaten sağlanır: anahtar yazılsa da uyarı yok (AP-03 makas y)
    ie = _ie("AP03"); ie["yapi"]["kose_kaynagi"] = "pafta"
    assert not any("Köşe paftadan" in u for u in _kur(ie).uyarilar)


# ---------------- geniş pencere, yanında tam pano yok (AP-09)

def test_genis_pencere_yarim_panolarla():
    # ön duvar (salon, 391,5–730): pencere yokken 120,5 + 125,5 + 92,5 (yanında tam pano yok); 170/180 gelince paftadaki gibi 62,75 + 213 + 62,75
    ie = _ie("AP09")
    plan = _kur(ie)
    on = _duvar(plan, "x", 5.0)
    assert [(p.a0, p.a1) for p in on.panolar] == [(391.5, 454.25), (454.25, 667.25), (667.25, 730.0)]
    assert [p.acilim.olcu if p.acilim else None for p in on.panolar] == [None, "170x180", None]
    yok = copy.deepcopy(ie); yok["acikliklar"] = [a for a in ie["acikliklar"] if a.get("olcu") != "170x180"]
    assert [(p.a0, p.a1) for p in _duvar(_kur(yok), "x", 5.0).panolar] == [(391.5, 512.0), (512.0, 637.5), (637.5, 730.0)]


def test_genis_pencere_parcada_dolu_pano_varsa_hata():
    # parçadaki başka pano açıklıklıysa eskisi gibi hata
    ie = _ie("AP09")
    ie["acikliklar"].append({"tur": "pencere", "olcu": "60x40", "mahal": "SALON+MUTFAK", "duvar": "on", "pano": 3})
    with pytest.raises(G.IsEmriHatasi, match="yanında tam pano yok"):
        G.kur(ie)


# ---------------- iç duvarlar dış aksa dayanır (AP-03)

def test_ic_duvarlar_dayanagi():
    # holün iki yan duvarı (iç, 6'lık) ön bölümde salonun ön duvarının aksından 125,5 arayla (Motor çerçevesinde arkadan 449,25)
    ie = _ie("AP03")
    plan = _kur(ie)
    H = plan.H
    aks = H - 449.25                                                 # gerçek çerçevede (önden)
    for c in (256.0, 444.25):
        d = _duvar(plan, "y", c)
        assert d.tur == "ic"
        for p in d.panolar[:-1]:
            assert abs(((p.a1 - aks) / G.MOD) - round((p.a1 - aks) / G.MOD)) < 1e-6, (c, p.a1)
    x = copy.deepcopy(ie)
    x["yapi"]["dizilim"]["dis_pano_dayanagi"][0].pop("ic_duvarlar")
    with pytest.raises(G.IsEmriHatasi):                              # iç duvarlar ızgarada kalınca hol kapılarına pano yok
        G.kur(x)


@pytest.mark.parametrize("deger", ["evet", 1, None])
def test_ic_duvarlar_yalniz_dogru_yanlis(deger):
    ie = _ie("AP03"); ie["yapi"]["dizilim"]["dis_pano_dayanagi"][0]["ic_duvarlar"] = deger
    with pytest.raises(G.IsEmriHatasi, match="ic_duvarlar"):
        G.kur(ie)


# ---------------- dikmenin örttüğü köşe parçası (AP-09)

def test_dikmenin_ortugu_kose_cizilmez():
    ie = _ie("AP09")
    plan = _kur(ie)
    kolon = (381.5, 0.0, 391.5, 10.0)
    assert kolon in plan.dikmeler
    ic = lambda k, d: d[0] - 0.5 <= k.rect[0] and k.rect[2] <= d[2] + 0.5 and d[1] - 0.5 <= k.rect[1] and k.rect[3] <= d[3] + 0.5  # noqa: E731
    assert not any(ic(k, d) for k in plan.koseler for d in plan.dikmeler)
    x = copy.deepcopy(ie); x["dikmeler"] = [v for v in ie["dikmeler"] if v != [381.5, 0]]
    yok = _kur(x)
    assert [tuple(k.rect) for k in yok.koseler if ic(k, kolon)] == [(381.5, 0.0, 391.5, 5.0)]
    assert len(yok.koseler) == len(plan.koseler) + 1
    assert {m: v.alan_m2 for m, v in yok.mahaller.items()} == {m: v.alan_m2 for m, v in plan.mahaller.items()}   # net alan değişmez


# ---------------- çatı (PR-2'nin ikinci aşaması)

def test_cati_izi_veranda_dikmesiyle():
    # AP-15: verandanın sağ kenarı dikmeden yatak odası 2'nin köşesine açık; gövde çizgisi orada 5 cm içeri girer. Çatının izi veranda ve
    # dikmeleriyle: iki şerit, öndeki cumba 0–386,5 (paftanın cumba kesiti), ana çatı 0–763. TK-03'ün izi değişmez
    from motor import cati_serit as CS
    ie = _ie("AP15")
    plan = _kur(ie)
    assert CS.seritler(G.govde_cokgeni(plan), ie) == [[0.0, 10.0, 0.0, 386.5], [10.0, 27.75, 0.0, 381.5], [27.75, 800.75, 0.0, 763.0]]
    assert CS.seritler(CS.cati_izi(plan), ie) == [[0.0, 27.75, 0.0, 386.5], [27.75, 800.75, 0.0, 763.0]]
    t = CS.tanim(plan, ie)
    assert [(p["ad"], p["aciklik_cm"], round(p["mahya_kotu"] - 250, 2)) for p in t["parcalar"]] == [("ön cumba", 386.5, 83.4),
                                                                                                    ("ana çatı", 763.0, 145.3)]
    tk03 = json.loads((KOK / "testler" / "motor" / "veri" / "TK03.json").read_text(encoding="utf-8"))
    p3 = _kur(tk03)
    assert CS.seritler(CS.cati_izi(p3), tk03) == CS.seritler(G.govde_cokgeni(p3), tk03)


def test_cikintili_cumba():
    # AP-22: ana çatı gövdenin 62,75 gerisinden (0–1014 × 62,75–835,75), cumba 439,25–1014 ve öne kadar; mahyalar ana 1074, cumba 380,12
    from motor import cati_prefabrik as CP, cephe_gorunus as CG
    ie = _ie("AP22")
    plan = _kur(ie)
    c = CP.cati(plan, ie)
    ana = next(d for d in c["duzlemler"] if d["ad"] == "ana kuzey")
    assert [min(p[1] for p in ana["plan"]), max(p[1] for p in ana["plan"])] == pytest.approx([449.25, 865.75])
    cumba = [d for d in c["duzlemler"] if d["ad"].startswith("cumba")]
    assert min(p[1] for d in cumba for p in d["plan"]) == pytest.approx(-30.0)
    assert {round(p[0], 2) for d in cumba for p in d["plan"]} >= {409.25, 1044.0}
    assert CG.mahya_boylari(plan, ie) == [1074.0, 380.12]


@pytest.mark.parametrize("degis, mesaj", [
    (lambda ie: ie["cati"]["cumbalar"][0].update(cikinti_cm=0), "girintili gövde"),       # girinti var, cumba taşmıyor
    (lambda ie: ie["cati"]["cumbalar"][0].update(bas_cm=200), "çıkıntılı cumba: gövdenin dış çizgisi"),
    (lambda ie: ie["cati"]["cumbalar"][0].update(cikinti_cm=40), "çıkıntılı cumba: gövdenin dış çizgisi"),
    (lambda ie: ie["cati"]["cumbalar"][0].update(cikinti_cm=500), "gövdenin derinliğinin yarısından az"),
])
def test_cikintili_cumba_govdeyle_denetlenir(degis, mesaj):
    from motor import cati_prefabrik as CP
    ie = _ie("AP22"); degis(ie)
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        CP.cati(_kur(ie), ie)


def test_aks_adlari_kademeli():
    # yazı boyundan yakın iki aksın ikincisinin adı dışarıda (AP-22: 1′ 67,75, 2 72,75); yakın aks yoksa hepsi aynı hizada
    from motor import dxf_out
    assert dxf_out._kademe([10.0, 67.75, 72.75, 130.5]) == [0, 0, 1, 0]
    assert dxf_out._kademe([0.0, 1.2, 10.0, 200.0]) == [0, 1, 0, 0]
    assert dxf_out._kademe([5.0, 130.5, 256.0]) == [0, 0, 0]
