"""İE-17 PR-2 · Dört evin (AP-15, AP-09, AP-03, AP-22) kat planı için Motor'a eklenenler — Motor kilidi.

Paftaya uygunluk `testler/cizim/test_pafta_kiyasi.py`'de (paftadan ölçülen değerler, kalan farklar gerekçeli). Hepsi yalnız yeni durumda
çalışır; anahtarsız ve var olan İş Emri'lerinin planı değişmez (`testler/referans/dogrula.py`, PR-1 evleri, PK-01, TK-03).

- `yapi.kose_kaynagi: pafta` (AP-15): `kisa_kenar: y` makas x ile de çizilir, uyarıyla; yazılmamışsa K21 hatası aynen.
- Panodan geniş pencerenin yanında tam pano yoksa (AP-09 ön duvar, 170/180) ve `dizilim.genis_pencere: yarim_pano` yazılıysa: odanın
  duvar parçası 62,75 + pencereli pano + 62,75; anahtarsız eskisi gibi hata (BK-13).
- `dizilim.dis_pano_dayanagi[].ic_duvarlar: true` (AP-03): aralıktaki iç duvarlar da aynı akslara dayanır.
- İş Emri dikmesinin tamamen örttüğü köşe parçası çizilmez (AP-09: verandanın açık kenarı gövde köşesinde biter; paftada orada kolon);
  o köşede biten duvar dikmenin yüzünden başlar.
- Çatı: girintili gövdenin beşiğinin izi verandayı dikmeleriyle içine alır (`cati_serit.cati_izi`, AP-15); çıkıntılı çapraz cumba
  (`cati_prefabrik`, AP-22) gövdenin girintisiyle denetlenir. Ön onay PDF'inde yakın aksların adları kademeli (`dxf_out._kademe`).
- Açık mahalin kendi çatısı (`cati.mahal_catilari`, AP-09): ana çatı verandayı örtmez (kalan gövdenin ana çatısı ve paralel cumbası paftanın
  ölçüsüyle), veranda tek eğimli panel çatı, ana çatının ve cumbanın saçağının altında; alçak kenarda kiriş, açık yanda eğik kiriş;
  görünüşte çatı, dikme ve kirişler, IFC'de panel ve eğik profil. Denetim kapalı gövdeyle (girinti ve açık mahal kapalı sayılmaz).
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest
from shapely.geometry import box

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
    # yarım panolar yalnız anahtarla (geometri hakemi, 1 Kasım: sessiz geri dönüş olmaz); anahtarsız BK-13'ün hatası aynen
    x = copy.deepcopy(ie); x["yapi"]["dizilim"].pop("genis_pencere")
    with pytest.raises(G.IsEmriHatasi, match="yanında tam pano yok"):
        G.kur(x)
    x["yapi"]["dizilim"]["genis_pencere"] = "yarim"
    with pytest.raises(G.IsEmriHatasi, match="dizilim.genis_pencere bilinmiyor"):
        G.kur(x)


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
    # o köşede biten salon–veranda duvarı dikmenin yüzünden başlar (paftada ilk pano 10,1–60,6); köşe parçası varken köşeden
    d, d_yok = _duvar(plan, "y", 386.5), _duvar(yok, "y", 386.5)
    assert (d.p0, [(p.a0, p.a1) for p in d.panolar][:2]) == (10.0, [(10.0, 61.0), (61.0, 186.5)])
    assert (d_yok.p0, d_yok.panolar[0].a0) == (5.0, 5.0)
    assert not [(q.rect(), dk) for w in plan.duvarlar for q in w.panolar for dk in plan.dikmeler
                if box(*q.rect()).intersection(box(*dk)).area > 1e-6]                 # hiçbir pano dikmeyle çakışmaz


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


def test_verandanin_kendi_catisi():
    # AP-09 (paftanın çatı kaplama sayfası): ana çatı yarısı 421,07 × 760,26 (verandanın arka duvarından arkaya), sağ öndeki cumba 220,27 ×
    # 273,75 (açıklık 358,5), verandada P1 381,5 × 245,48 (eğim %10: 244,25 × √1,01 = 245,47). Veranda çatısı arka duvar üstünden (250) öne
    # 24,4 iner; kiriş alçak kenarda, serbest dikme kirişin altına, cumbanın duvar ucundaki dikme (paftanın A profili) duvar üstüne
    from motor import cati_serit as CS, sunum
    ie = _ie("AP09")
    plan = _kur(ie)
    assert CS.seritler(CS.cati_izi(plan, ie), ie) == [[0.0, 244.25, 381.5, 740.0], [244.25, 944.5, 0.0, 740.0]]
    t = sunum.cati_tanimi(plan, ie)
    assert [(q["ad"], q["aciklik_cm"], q["makas_ust_boy_cm"], round(q["mahya_kotu"] - 250, 2)) for q in t["parcalar"]] == [
        ("ön cumba", 358.5, 220.27, 78.8), ("ana çatı", 740.0, 421.07, 141.52)]
    ana = [d for d in t["duzlemler"] if d["ad"].startswith("ana çatı")]
    assert min(p[1] for d in ana for p in d["plan"] if p[0] < 351.5) == pytest.approx(214.25)    # ana çatı 214,25–974,5: 760,25
    (m,) = t["mahal_catilari"]
    assert m["kutu"] == (0.0, 0.0, 381.5, 244.25) and m["yuksek_yan"] == "arka" and m["egim"] == pytest.approx(0.1)
    assert (m["ust_kot"], m["alt_kot"]) == (250.0, pytest.approx(225.575))
    assert round(244.25 * (1 + 0.1 ** 2) ** 0.5, 2) == pytest.approx(245.47)
    assert m["kirisler"] == [(0.0, 0.0, 381.5, 10.0, pytest.approx(215.575), pytest.approx(225.575))]
    assert m["kolonlar"] == [(0.0, 0.0, 10.0, 10.0, pytest.approx(215.575)), (381.5, 0.0, 391.5, 10.0, 250.0)]
    assert m["egik_kirisler"] == [(0.0, 0.0, 10.0, 244.25)]                       # sol açık yan: eğim boyunca (paftada V05)
    assert CS.kiris_kotu(m, 0, 244.25) == (pytest.approx(240.0), pytest.approx(250.0))
    assert "mahal_catilari" not in sunum.cati_tanimi(_kur(_ie("AP15")), _ie("AP15"))   # anahtarsız evde çatı tanımı aynen


def test_verandanin_catisi_gorunuste():
    # önden: veranda çatısı bant (225,6–250), iki dikme ve kiriş; soldan: eğik çizgi ve %10; arkadan ve sağdan gövdenin ardında
    from motor import cephe_gorunus as CG
    ie = _ie("AP09")
    plan = _kur(ie)
    on = CG.cati_cizgileri(plan, ie, "on")
    assert any({round(z, 3) for _u, z in c} == {225.575, 250.0} for c in on["cizgiler"])
    on_p = CG.mahal_cati_parcalari(plan, ie, "on")
    assert [q["tur"] for q in on_p] == ["kolon", "kolon", "kiris"]
    # önden eğik kirişin yalnız ucu görünür, alçak kenardaki kirişin yüzünün içinde: tek dikdörtgen
    assert {(round(u, 3), round(z, 3)) for u, z in on_p[2]["u"]} == {(0, 215.575), (381.5, 215.575), (381.5, 225.575), (0, 225.575)}
    # soldan eğik kiriş paralelkenar, alçak kenardaki kirişin ucuyla birleşik tek çizgi
    sol_k = [q for q in CG.mahal_cati_parcalari(plan, ie, "sol") if q["tur"] == "kiris"]
    assert [{(round(u, 3), round(z, 3)) for u, z in q["u"]} for q in sol_k] == [
        {(934.5, 215.575), (934.5, 216.575), (700.25, 240.0), (700.25, 250.0), (944.5, 225.575), (944.5, 215.575)}]
    sol = CG.cati_cizgileri(plan, ie, "sol")
    assert [round(e, 3) for _u, _z, e in sol["egimler"]] == [0.1]                  # ana çatı soldan dönük: eğimi önde yazılı
    assert [(pytest.approx(944.5), pytest.approx(225.575)), (pytest.approx(700.25), pytest.approx(250.0))] in sol["cizgiler"]
    for t in ("arka", "sag"):
        assert CG.mahal_cati_parcalari(plan, ie, t) == []
        assert all(min(z for _u, z in c) >= 260 - 1e-6 for c in CG.cati_cizgileri(plan, ie, t)["cizgiler"])
    assert on["tepe"] == (370.0, pytest.approx(391.52)) and on["u0"] == -30.0 and on["u1"] == 770.0      # saçak uçları ana çatıdan


def test_verandanin_catisi_ifc_ve_liste(tmp_path):
    # IFC'de panel levhası ve dikme ile profiller veranda çatısının altında; yükleme listesi bu çatıyı bilmiyor: yazılmaz (PR-1b/K7)
    import ifcopenshell
    from motor import ifc_uret, prefabrik_liste as PL
    ie = _ie("AP09")
    o = ifc_uret.uret(copy.deepcopy(ie), tmp_path / "AP09.ifc")
    assert o["sema_hatasi"] == 0 and o["cati"]["mahya_cm"] == pytest.approx(391.5)
    f = ifcopenshell.open(str(tmp_path / "AP09.ifc"))
    assert [e.Name for e in f.by_type("IfcSlab") if e.Name.startswith("MAHAL_CATI")] == ["MAHAL_CATI_1"]

    def kot(e):
        return next(q.NominalValue.wrappedValue for r in e.IsDefinedBy if r.is_a("IfcRelDefinesByProperties")
                    for q in r.RelatingPropertyDefinition.HasProperties if q.Name == "Kot_cm")
    assert sorted(kot(e) for e in f.by_type("IfcColumn")) == ["0–216", "0–250"]
    assert sorted(kot(e) for e in f.by_type("IfcBeam")) == ["216–226", "216–250"]   # alçak kenarda yatay, sol yanda çatının eğimiyle
    import ifcopenshell.geom
    import numpy as np
    ayar = ifcopenshell.geom.settings(); ayar.set(ayar.USE_WORLD_COORDS, True)
    (v05,) = [e for e in f.by_type("IfcBeam") if "V05" in e.Name]
    v = np.array(ifcopenshell.geom.create_shape(ayar, v05).geometry.verts).reshape(-1, 3) * 100
    for y, z0 in ((0.0, 215.575), (244.25, 240.0)):                                   # altı çatının 10 altında, iki ucunda
        assert v[np.abs(v[:, 1] - y) < 0.5][:, 2].min() == pytest.approx(z0, abs=0.01)
    with pytest.raises(PL.ListeYazilmaz, match="açık mahalin kendi çatısı"):
        PL.model_motor(copy.deepcopy(ie))


@pytest.mark.parametrize("degis, mesaj", [
    (lambda g: g.update(tip="besik"), "yalnız tek_yon"),
    (lambda g: g.pop("egim_yuzde"), "eğim paftadan yazılır"),
    (lambda g: g.update(yuksek_yan="on"), "yüksek yanı \\(on\\) boyunca kapalı gövde yok"),
    (lambda g: g.update(yuksek_yan="sol"), "yüksek yanı \\(sol\\) boyunca kapalı gövde yok"),
    (lambda g: g.update(mahal="SALON+MUTFAK"), "açık mahal değil"),
    (lambda g: g.update(renk="antrasit"), "tanınmayan alan: renk"),
    (lambda g: g.update(sacak_cm=-5), "saçak -5 cm olmaz"),
])
def test_verandanin_catisi_denetlenir(degis, mesaj):
    from motor import cati_prefabrik as CP, sunum
    ie = _ie("AP09"); degis(ie["cati"]["mahal_catilari"][0])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        sunum.cati_tanimi(_kur(ie), ie)


def test_verandanin_catisi_ana_catinin_altinda_kalir():
    # saçak kotu duvar üstünün altındaysa (topuk −15: ana çatının ve cumbanın saçağı 245) veranda çatısının arka ucu (250) üstüne çıkar: çizilmez.
    # Yüksek yanı sağ (cumbanın duvarı) da kurulur: eğim x boyunca, alçak kenar solda
    from motor import cati_prefabrik as CP, sunum
    ie = _ie("AP09"); ie["cati"]["topuk_cm"] = -15
    with pytest.raises(CP.PrefabrikCatiHatasi, match="saçağının altında kalmalı"):
        sunum.cati_tanimi(_kur(ie), ie)
    ie = _ie("AP09"); ie["cati"]["mahal_catilari"][0]["yuksek_yan"] = "sag"
    (m,) = sunum.cati_tanimi(_kur(ie), ie)["mahal_catilari"]
    assert m["duzlem"]["yukari"] == [1, 0] and m["alt_kot"] == pytest.approx(250 - 38.15)
    assert m["kirisler"] == [(0.0, 0.0, 10.0, 244.25, pytest.approx(201.85), pytest.approx(211.85))]
    assert m["egik_kirisler"] == [(0.0, 0.0, 381.5, 10.0)]                         # eğim x boyunca: açık ön yanda


def test_verandanin_catisi_sacakli_kiris_kotu():
    # saçak 20 (sol ve ön açık): düzlem saçak ucuna uzar, alt kotu saçak ucunda; kiriş mahalin kenarında, üstü çatının orada kotu
    # (geometri hakemi, 1 Kasım: saçak ucunun kotu değil), serbest dikme kirişin altına
    from motor import sunum
    ie = _ie("AP09"); ie["cati"]["mahal_catilari"][0]["sacak_cm"] = 20
    (m,) = sunum.cati_tanimi(_kur(ie), ie)["mahal_catilari"]
    assert m["duzlem"]["plan"] == [[-20.0, -20.0], [381.5, -20.0], [381.5, 244.25], [-20.0, 244.25]]
    assert m["alt_kot"] == pytest.approx(250 - 264.25 * 0.1)
    assert m["kirisler"] == [(0.0, 0.0, 381.5, 10.0, pytest.approx(215.575), pytest.approx(225.575))]
    assert m["kolonlar"][0] == (0.0, 0.0, 10.0, 10.0, pytest.approx(215.575))


@pytest.mark.parametrize("ad, yan, mesaj", [
    ("AP15", "sag", "yüksek yanı \\(sag\\) boyunca kapalı gövde yok"),     # sağının %92'si kapalı gövde (dış kutuyla tam dolu sayılıyordu)
    ("AP22", "sol", "yüksek yanı \\(sol\\) boyunca kapalı gövde yok"),     # solunun %58'i kapalı gövde, kalanı girinti
    ("AP15", "arka", "sag yanı kısmen kapalı"),
])
def test_verandanin_catisi_kapali_govdeyle_denetlenir(ad, yan, mesaj):
    # kapalı gövde gövdenin çokgeninden bütün açık mahaller düşülerek: girintiye ya da başka açık mahale bakan yan açık sayılır (geometri
    # hakemi, 1 Kasım: dış kutuyla denetim AP-15'in sağını tam dolu sayıyordu). AP-22'nin çatısı beşik + cumba: denetim için beşik yazılır
    from motor import cati_prefabrik as CP, cati_serit as CS
    ie = _ie(ad)
    ie["cati"]["tip"] = "besik"; ie["cati"].pop("cumbalar", None)
    ie["cati"]["mahal_catilari"] = [{"mahal": "VERANDA", "tip": "tek_yon", "egim_yuzde": 10, "yuksek_yan": yan}]
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        CS.mahal_catilari(_kur(ie), ie)


def test_verandanin_catisi_yalniz_besikle():
    # beşik + cumba ve kırmada mahal çatısı yok: her yolda hata (çizim `cati_prefabrik`'te tanınmayan alan, IFC ve görünüş `cati_serit`'te)
    from motor import cati_prefabrik as CP, cati_serit as CS
    ie = _ie("AP22")
    ie["cati"]["mahal_catilari"] = [{"mahal": "VERANDA", "tip": "tek_yon", "egim_yuzde": 10, "yuksek_yan": "arka"}]
    with pytest.raises(CP.PrefabrikCatiHatasi, match="yalnız beşik ana çatıyla"):
        CS.mahal_catilari(_kur(ie), ie)
    with pytest.raises(CP.PrefabrikCatiHatasi, match="tanınmayan alan: mahal_catilari"):
        CP.cati(_kur(ie), ie)


def test_verandanin_catisi_dikdortgen_mahale():
    from motor import cati_prefabrik as CP, cati_serit as CS
    ie = _ie("AP09")
    plan = _kur(ie)
    m = plan.mahaller["VERANDA"]
    m.poly = m.poly.difference(box(300, 200, 381.5, 244.25))                     # L biçimli mahal: kutusu aynı, çatı kutuya çizilmez
    with pytest.raises(CP.PrefabrikCatiHatasi, match="dikdörtgen değil"):
        CS.mahal_catilari(plan, ie)
