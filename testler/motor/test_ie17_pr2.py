"""İE-17 PR-2 · Dört evin (AP-15, AP-09, AP-03, AP-22) kat planı için Motor'a eklenenler — Motor kilidi.

Paftaya uygunluk `testler/cizim/test_pafta_kiyasi.py`'de (paftadan ölçülen değerler, kalan farklar gerekçeli). Hepsi yalnız yeni durumda
çalışır; anahtarsız ve var olan İş Emri'lerinin planı değişmez (`testler/referans/dogrula.py`, PR-1 evleri, PK-01, TK-03).

- `yapi.kose_kaynagi: pafta` (AP-15): `kisa_kenar: y` makas x ile de çizilir, uyarıyla; yazılmamışsa K21 hatası aynen.
- Panodan geniş pencerenin yanında tam pano yoksa (AP-09 ön duvar, 170/180) ve `dizilim.genis_pencere: yarim_pano` yazılıysa: odanın
  duvar parçası 62,75 + pencereli pano + 62,75; anahtarsız eskisi gibi hata (BK-13).
- `dizilim.dis_pano_dayanagi[].ic_duvarlar: true` (AP-03): aralıktaki iç duvarlar da aynı akslara dayanır.
- Açık kenardaki köşe parçasını İş Emri dikmesi tamamen örtüyorsa köşe çizilmez (AP-09: verandanın açık kenarı gövde köşesinde biter;
  paftada orada kolon); o köşede biten duvar dikmenin yüzünden başlar. Kapalı odanın köşesindeki dikme köşeyi ve duvarı değiştirmez.
- Çatı: girintili gövdenin beşiğinin izi verandayı dikmeleriyle içine alır (`cati_serit.cati_izi`, AP-15); çıkıntılı çapraz cumba
  (`cati_prefabrik`, AP-22) gövdenin girintisiyle denetlenir. Ön onay PDF'inde yakın aksların adları kademeli (`dxf_out._kademe`).
- Açık mahalin kendi çatısı (`cati.mahal_catilari`, AP-09): ana çatı verandayı örtmez (kalan gövdenin ana çatısı ve paralel cumbası paftanın
  ölçüsüyle), veranda tek eğimli panel çatı, ana çatının ve cumbanın saçağının altında; alçak kenarda kiriş, açık yanda eğik kiriş;
  görünüşte çatı, dikme ve kirişler, IFC'de panel ve eğik profil. Denetim kapalı gövdeyle (girinti ve açık mahal kapalı sayılmaz).
- Köşe kırması (`tip` kirma, AP-03; Lokman, 1 Kasım 2026 10:17): veranda yüzü ana çatının eğimi ve saçak kotuyla sağa iner, arkada ana
  çatının arka yüzüyle 45° kırma, önde cumbanın arka yüzüyle dere; ölçüler paftanın aşık planıyla. Kalkan veranda yüzünün üstünde, kiriş ve
  dikme taşan verandadaki gibi; IFC'de sac levha; liste yazılmaz (PR-1b/K7).
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
    # kırpılan uç panoda açıklık olmaz (boyu ve kayması yeniden kurulmaz; geometri hakemi, 2. tur)
    x = copy.deepcopy(ie)
    x["acikliklar"].append({"tur": "pencere", "olcu": "50x50", "mahal": "SALON+MUTFAK", "duvar": "sol", "pano": 5})
    with pytest.raises(G.IsEmriHatasi, match="uç panosunda açıklık var"):
        G.kur(x)


def test_kapali_odanin_kosesindeki_dikme_degistirmez():
    # yalnız açık kenardaki köşe düşer (geometri hakemi, 2. tur): TK-02'nin sağ ön köşesindeki dikme (kapalı mutfağın köşesi) köşe parçasını
    # örtse de köşe ve duvarlar dikmesiz planla aynı (main'de dikme köşeye ve duvara hiç dokunmuyordu)
    tk = json.loads((KOK / "testler" / "motor" / "veri" / "TK02.json").read_text(encoding="utf-8"))
    x = copy.deepcopy(tk); x["dikmeler"] = [[888, 0], [256, 0]]
    ozet = lambda p: ([tuple(k.rect) for k in p.koseler], [(w.id, w.p0, w.p1, [(q.a0, q.a1) for q in w.panolar]) for w in p.duvarlar])  # noqa: E731
    p = G.kur(x)
    assert p.dikmeler[:2] == [(888.5, 0.0, 898.5, 10.0), (256.0, 0.0, 266.0, 10.0)]
    assert (888.5, 0.0, 898.5, 5.0) in ozet(p)[0] and ozet(p) == ozet(G.kur(copy.deepcopy(tk)))


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
    (lambda g: g.update(tip="besik"), "tek_yon .*ya da kirma.*'besik' yok"),
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


def test_verandanin_catisi_acik_yani_dis_olcude(monkeypatch):
    # açık yanın kirişi planın ve IFC'nin veranda profilidir; profil yalnız dış ölçüdeki kenarda (`dxf_out`): girintiye bakan açık yan hata
    # (geometri hakemi, 2. tur, N4). Girinti yapay: veranda 20 cm sağa daraltılır, solundaki şerit gövdeden çıkarılır
    from motor import cati_prefabrik as CP, cati_serit as CS
    ie = _ie("AP09")
    plan = _kur(ie)
    plan.mahaller["VERANDA"].poly = box(20, 0, 381.5, 244.25)
    govde = G.govde_cokgeni(plan).difference(box(0, 0, 20, 244.25))
    monkeypatch.setattr(G, "govde_cokgeni", lambda _p: govde)
    with pytest.raises(CP.PrefabrikCatiHatasi, match="açık sol yanı dış ölçüde değil"):
        CS.mahal_catilari(plan, ie)


def test_verandanin_catisi_dikdortgen_mahale():
    from motor import cati_prefabrik as CP, cati_serit as CS
    ie = _ie("AP09")
    plan = _kur(ie)
    m = plan.mahaller["VERANDA"]
    m.poly = m.poly.difference(box(300, 200, 381.5, 244.25))                     # L biçimli mahal: kutusu aynı, çatı kutuya çizilmez
    with pytest.raises(CP.PrefabrikCatiHatasi, match="dikdörtgen değil"):
        CS.mahal_catilari(plan, ie)


# ─────────────────────────────────────────── AP-03: verandanın köşe kırması (Lokman, 1 Kasım 2026 10:17, "Paftadaki gibi köşe kırma")
def test_kose_kirmasi_paftanin_asik_planiyla():
    # AP-03 paftası s. 7 (makas planı: MK9–12 kısa makaslar sağa, MK13 arka köşeden 45° çapraz) ve s. 9 (aşık planı, eğik boylar): veranda yüzü
    # kırma ile dere arasında paralelkenar, sağ saçakta 865,75 − 421,5 = 444,25 (paftada aşık 410 + 34,25); ana çatının arka yüzü saçakta
    # −30 → 793: 823 (paftada 823), salon duvarının saçağında 697,5 (paftada 695,5; duvar yüzü 2 cm farkı), kırma oradan saçağa 125,5
    # (paftada 127,5); cumbanın arka yüzünde aşık 155,5 (paftada 155,5). Eğim ve saçak kotu ana çatınınki: kırmanın salon duvarındaki ucunda
    # iki yüz aynı kotta (311,13 = 260 + 155,5 × 0,3288)
    from shapely.geometry import Polygon
    from motor import cati_serit as CS, sunum
    from motor.genel import cati_genel
    ie = _ie("AP03")
    plan = _kur(ie)
    t = sunum.cati_tanimi(plan, ie)
    D = {d["ad"]: d for d in t["duzlemler"]}
    assert list(D) == ["VERANDA çatısı", "sağ cumba arka", "ana çatı ön", "ana çatı arka"]       # veranda yüzü altta çizilir
    v = D["VERANDA çatısı"]
    assert Polygon(v["plan"]).equals(Polygon([(637.5, 266.0), (793.0, 421.5), (793.0, 865.75), (637.5, 710.25)]))
    assert (v["yukari"], v["sacak"], v["sacak_kotu"], v["egim"]) == ([-1, 0], {"x": 793.0}, 260.0, pytest.approx(0.3288))
    assert Polygon(D["sağ cumba arka"]["plan"]).equals(Polygon([(637.5, 195.75), (793.0, 195.75), (793.0, 421.5), (637.5, 266.0)]))
    arka = Polygon(D["ana çatı arka"]["plan"])
    assert arka.equals(Polygon([(-30.0, 417.875), (667.5, 417.875), (667.5, 740.25), (793.0, 865.75), (-30.0, 865.75)]))
    assert [h["tur"] for h in t["hatlar"]] == ["dere", "kirma"]
    dere, kirma = t["hatlar"]
    assert (dere["p"], dere["q"]) == ([667.5, 296.0], [793.0, 421.5])          # ana çatının saçağının altında kalan kısım görünmez
    assert (kirma["p"], kirma["q"]) == ([793.0, 865.75], [667.5, 740.25])
    from motor.veranda import kot
    assert kot(v, 637.5, 710.25) == pytest.approx(kot(D["ana çatı arka"], 637.5, 710.25)) == pytest.approx(260 + 155.5 * 0.3288)
    assert kot(v, 637.5, 266.0) == pytest.approx(kot(D["sağ cumba arka"], 637.5, 266.0))
    k = {(e["tur"], tuple(sorted(e["duzlemler"]))) for e in cati_genel.cati_kur(t)["kenarlar"] if e["tur"] in ("kirma", "vadi")}
    assert k == {("kirma", ("VERANDA çatısı", "ana çatı arka")), ("vadi", ("VERANDA çatısı", "sağ cumba arka"))}
    # salonun sağ kalkanı: cumbanın üstünde dereye kadar, sonra veranda yüzünün üstünde (kırmanın ötesinde ana çatı yüzü geçer: kalkan yok)
    sag = [(k_["ad"], k_["aralik"], k_.get("alt")) for k_ in t["kalkanlar"] if k_["konum"] == 637.5]
    assert sag == [("ana çatı sağ kalkanı (0–266)", [0.0, 266.0], ["sağ cumba arka"]),
                   ("ana çatı sağ kalkanı (266–835.75, VERANDA çatısı üstü)", [266.0, 835.75], ["VERANDA çatısı"])]
    (m,) = t["mahal_catilari"]
    assert (m["tip"], m["yuksek_yan"], m["yanlar"], m["egik_kirisler"]) == ("kirma", "sol", {"on": "kapali", "arka": "acik"}, [])
    # kiriş ve dikme taşan verandadaki gibi (BK-14): açık iki yanda yatay kiriş duvar üstünün 10 altından duvar üstüne, dikme kirişin altına
    assert m["kirisler"] == [(753.0, 391.5, 763.0, 835.75, 240.0, 250.0), (637.5, 825.75, 763.0, 835.75, 240.0, 250.0)]
    assert m["kolonlar"] == [(753.0, 825.75, 763.0, 835.75, 240.0)]
    # paftanın parçaları: ana çatı ve cumba aynen (kırma onlara dokunmaz)
    assert [(q["ad"], q["aciklik_cm"], round(q["mahya_kotu"] - 250, 2)) for q in t["parcalar"]] == [
        ("ana çatı", 835.75, 157.26), ("sağ cumba", 391.5, 84.23)]
    assert CS.seritler(CS.cati_izi(plan, ie), ie) == [[0.0, 637.5, 0.0, 835.75], [637.5, 763.0, 0.0, 391.5]]


def test_kose_kirmasi_gorunuste():
    # sağdan veranda yüzü dönük (üst kenarı salon duvarında 311,13, kırmadan dereye); arkadan kırma ana çatının arka yüzünün kenarı, üstünde
    # cumbanın arka yüzü mahyasına kadar görünür; dikme ve kirişler arkadan ve sağdan, önden ve soldan gövdenin ardında
    from motor import cephe_gorunus as CG
    ie = _ie("AP03")
    plan = _kur(ie)
    sag = CG.cati_cizgileri(plan, ie, "sag")
    assert [(266.0, 311.1284), (421.5, 260.0), (865.75, 260.0), (710.25, 311.1284), (266.0, 311.1284)] in sag["cizgiler"]
    arka = CG.cati_cizgileri(plan, ie, "arka")
    assert [(95.5, 301.2644), (-30.0, 260.0), (793.0, 260.0), (793.0, 407.2613), (95.5, 407.2613), (95.5, 301.2644)] in arka["cizgiler"]
    assert [(95.45, 334.2266), (-30.0, 334.2266), (-30.0, 260.0526)] in arka["cizgiler"]
    assert CG.cati_cizgileri(plan, ie, "on")["cizgiler"] == [
        [(793.0, 334.2266), (667.5, 334.2266), (667.5, 407.2613), (-30.0, 407.2613), (-30.0, 260.0), (793.0, 260.0), (793.0, 334.2266)]]
    assert [(p["tur"], p["u"]) for p in CG.mahal_cati_parcalari(plan, ie, "sag")] == [
        ("kolon", [(825.75, 0.0), (835.75, 0.0), (835.75, 240.0), (825.75, 240.0)]),
        ("kiris", [(391.5, 240.0), (391.5, 250.0), (835.75, 250.0), (835.75, 240.0)])]
    assert [p["tur"] for p in CG.mahal_cati_parcalari(plan, ie, "arka")] == ["kolon", "kiris"]
    assert CG.mahal_cati_parcalari(plan, ie, "on") == [] and CG.mahal_cati_parcalari(plan, ie, "sol") == []


def test_kose_kirmasi_ifc_ve_liste(tmp_path):
    # IFC: veranda yüzü ana çatının sac levhalarından biri (panel değil); profiller duvar üstünün 10 altından duvar üstüne, dikme kirişin
    # altına; salonun sağ kalkanı iki dolgu. Veranda makasları (MK9–13) ve liste PR-1b/K7'de: liste yazılmaz
    import ifcopenshell
    from motor import ifc_uret, prefabrik_liste as PL
    ie = _ie("AP03")
    o = ifc_uret.uret(copy.deepcopy(ie), tmp_path / "AP03.ifc")
    assert o["sema_hatasi"] == 0 and o["cati"]["mahya_cm"] == pytest.approx(407.3)
    f = ifcopenshell.open(str(tmp_path / "AP03.ifc"))

    def ps(e, ad):
        return next((q.NominalValue.wrappedValue for r in e.IsDefinedBy if r.is_a("IfcRelDefinesByProperties")
                     for q in r.RelatingPropertyDefinition.HasProperties if q.Name == ad), None)
    assert [ps(e, "Duzlem") for e in f.by_type("IfcSlab") if e.Name.startswith("CATI_")] == [
        "VERANDA çatısı", "sağ cumba arka", "ana çatı ön", "ana çatı arka"]
    assert not [e for e in f.by_type("IfcSlab") if e.Name.startswith("MAHAL_CATI")]
    assert [ps(e, "Kot_cm") for e in f.by_type("IfcColumn")] == ["0–240"]
    assert sorted(ps(e, "Kot_cm") for e in f.by_type("IfcBeam")) == ["240–250", "240–250"]
    assert [ps(e, "Kalkan") for e in f.by_type("IfcPlate") if e.Name.startswith("ALIN")] == [
        "ana çatı sol kalkanı", "ana çatı sağ kalkanı (0–266)", "ana çatı sağ kalkanı (266–835.75, VERANDA çatısı üstü)", "sağ cumba sağ kalkanı"]
    with pytest.raises(PL.ListeYazilmaz, match="köşe kırması"):
        PL.model_motor(copy.deepcopy(ie))


@pytest.mark.parametrize("degis, mesaj", [
    (lambda g: g.update(egim_yuzde=20), "egim_yuzde yazılmaz"),
    (lambda g: g.update(sacak_cm=20), "sacak_cm yazılmaz"),
    (lambda g: g.update(yuksek_yan="on"), "kalkan yüzüne dayanır"),             # mahyaya paralel yan: kırma kurulmaz
    (lambda g: g.update(yuksek_yan="sag"), "yüksek yanı \\(sag\\) boyunca kapalı gövde yok"),
])
def test_kose_kirmasi_denetlenir(degis, mesaj):
    from motor import cati_prefabrik as CP, sunum
    ie = _ie("AP03"); degis(ie["cati"]["mahal_catilari"][0])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        sunum.cati_tanimi(_kur(ie), ie)


@pytest.mark.parametrize("dus, mesaj", [
    ("ana çatı arka", "arka yanında o yöne inen ve saçağı mahalin saçağında biten ana çatı yüzü yok; kırma kurulmaz"),
    ("sağ cumba arka", "on yanında mahala inen çatı yüzü yok .*dere kurulamaz"),
])
def test_kose_kirmasi_komsu_yuz_ister(dus, mesaj):
    # kırmanın açık yanında o yöne inen ana çatı yüzü, kapalı yanında mahala inen yüz yoksa çatı çizilmez (yanlış çatı çizilmez)
    from motor import cati_prefabrik as CP, cati_serit as CS, sunum
    ie2 = _ie("AP03")
    plan = _kur(ie2)
    (m,) = CS.mahal_catilari(plan, ie2)
    ie2_t = {**ie2, "cati": {**ie2["cati"], "mahal_catilari": [{**ie2["cati"]["mahal_catilari"][0], "tip": "tek_yon", "egim_yuzde": 10}]}}
    t = sunum.cati_tanimi(plan, ie2_t)                                       # aynı şeritler, kırmasız düzlemler
    duz = [copy.deepcopy(d) for d in t["duzlemler"] if d["ad"] != dus]
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        CS._kirma(m, duz, copy.deepcopy(t["kalkanlar"]), box(-30, -30, 667.5, 865.75))


def test_kose_kirmasi_mahyayi_asmaz():
    # geometri hakemi (1 Kasım, `848f32b`): AP-09'un verandası makas x'ken kırma yazılırsa veranda yüzü duvarda (350,17) cumbanın
    # mahyasından (328,8) yüksek; dere mahyayı geçer, eskiden kırpılıp 21 cm basamaklı çatı hatasız PDF'e gidiyordu → hata
    from motor import cati_prefabrik as CP, sunum
    ie = _ie("AP09")
    ie["cati"]["mahal_catilari"] = [{"mahal": "VERANDA", "tip": "kirma", "yuksek_yan": "arka"}]
    with pytest.raises(CP.PrefabrikCatiHatasi, match=r"duvarda 350\.17 kotunda, ön cumba sol yüzünün mahyası 328\.80; dere mahyayı aşar"):
        sunum.cati_tanimi(_kur(ie), ie)


def _sentetik_kirma(X1: float, yanlar: dict, engel: list | None = None, y0: float = 0.0, cumba_x1: float | None = None):
    """AP-03'ün ana çatısı ölçüsünde elle kurulmuş yüzler; veranda x 637,5–X1, y y0–835,75; y0 > 0 ise önünde cumba (arka yüzü x 637,5–
    `cumba_x1`, verilmezse veranda saçağına kadar) (geometri hakeminin denemesi, 1 Kasım)."""
    from motor import cati_serit as CS
    e = 0.3288

    def dz(ad, plan, yuk, sac):
        return {"ad": ad, "plan": plan, "yukari": yuk, "egim": e, "sacak_kotu": 260.0, "sacak": sac}
    duz = [dz("ana çatı ön", [[-30, -30], [667.5, -30], [667.5, 417.875], [-30, 417.875]], [0, 1], {"y": -30.0}),
           dz("ana çatı arka", [[-30, 417.875], [667.5, 417.875], [667.5, 865.75], [-30, 865.75]], [0, -1], {"y": 865.75})]
    if y0 > 0:
        cx1 = X1 + 30 if cumba_x1 is None else cumba_x1
        duz.insert(0, dz("cumba arka", [[637.5, y0 / 2], [cx1, y0 / 2], [cx1, y0 + 30], [637.5, y0 + 30]], [0, -1], {"y": y0 + 30.0}))
    if engel:
        duz.append(dz("engel", engel, [0, -1], {"y": 865.75}))
    Y0 = y0 - (30 if yanlar["on"] == "acik" else 0)
    P = dz("VERANDA çatısı", [[637.5, Y0], [X1 + 30, Y0], [X1 + 30, 865.75], [637.5, 865.75]], [-1, 0], {"x": X1 + 30.0})
    m = {"mahal": "VERANDA", "kutu": (637.5, y0, X1, 835.75), "sacak": 30.0, "yuksek_yan": "sol", "duzlem": P, "yanlar": yanlar}
    kal = [{"ad": "ana çatı sağ kalkanı", "eksen": "x", "konum": 637.5, "ic": "bati", "ust": ["ana çatı ön", "ana çatı arka"],
            "aralik": [0.0, 835.75]}]
    return CS._kirma(m, duz, kal, box(-30, -30, 667.5, 865.75)), duz, kal


def test_kose_kirmasi_uzayan_yuz_sinirli():
    # geometri hakemi (1 Kasım): kırma yanında uzatılan ana çatı yüzü kendi mahyasını geçmez, başka yüze binmez
    from shapely.geometry import Polygon
    from motor import cati_prefabrik as CP
    hatlar, duz, kal = _sentetik_kirma(763.0, {"on": "acik", "arka": "acik"})          # iki açık yan: iki kırma, mahyada buluşmaz
    on, arka = (Polygon(d["plan"]) for d in duz if d["ad"] in ("ana çatı ön", "ana çatı arka"))
    assert on.intersection(arka).area < 1.0
    assert sorted(h["tur"] for h in hatlar) == ["kirma", "kirma"]
    assert [k["ad"] for k in kal] == ["ana çatı sağ kalkanı (0–835.75, VERANDA çatısı üstü)"]
    with pytest.raises(CP.PrefabrikCatiHatasi, match=r"duvarda 487\.69 kotunda, ana çatı ön yüzünün mahyası 407\.26; kırma mahyayı aşar"):
        _sentetik_kirma(1300.0, {"on": "acik", "arka": "acik"})                    # eskiden ön ve arka yüz 5,98 m² üst üste
    with pytest.raises(CP.PrefabrikCatiHatasi, match="ana çatı arka yüzü kırmaya uzarken engel yüzüne biniyor"):
        _sentetik_kirma(763.0, {"on": "acik", "arka": "acik"}, engel=[[700, 800], [793, 800], [793, 865.75], [700, 865.75]])


def test_kose_kirmasi_dar_komsu_yuz_ve_duvar():
    # geometri hakemi 2. tur (N2): kapalı yandaki yüz verandanın eğim aralığını örtmüyorsa ve iki kırma duvardan önce kesişiyorsa hata
    from motor import cati_prefabrik as CP
    AC = {"on": "kapali", "arka": "acik"}
    hatlar, _d, _k = _sentetik_kirma(763.0, AC, y0=391.5)                         # AP-03 ölçüsü: çizilir
    assert sorted(h["tur"] for h in hatlar) == ["dere", "kirma"]
    with pytest.raises(CP.PrefabrikCatiHatasi, match="dere yanında cumba arka yüzünün dışına taşıyor"):
        _sentetik_kirma(763.0, AC, y0=391.5, cumba_x1=720.0)                    # cumbanın arka yüzü 720'de bitiyor, veranda 793'e
    _sentetik_kirma(637.5 + 417.875, {"on": "acik", "arka": "acik"})               # veranda eni = ana çatının yarı açıklığı: mahyada buluşur
    with pytest.raises(CP.PrefabrikCatiHatasi, match="duvara değmiyor"):
        _sentetik_kirma(637.5 + 419.0, {"on": "acik", "arka": "acik"})             # mahyayı 0,37 aşar (payın içi): kırmalar duvardan önce kesişir


def _genis_veranda(ayna: bool) -> dict:
    """AP-03'ten: veranda 251 × 130,5 (eğim yönünde derinliğinden geniş), yanında ODA 3; `ayna` ön ↔ arka (geometri hakemi 2. tur)."""
    ie = _ie("AP03")
    for m in ie["mahaller"]:
        if m["ad"] == "VERANDA":
            m["konum_cm"] = [[507, 10, 758, 135.5]]
        if m["ad"] == "SALON+MUTFAK":
            m["konum_cm"] = [[5, 10, 507, 449.25]]
    ie["mahaller"].append({"ad": "ODA 3", "tur": "yatak_odasi", "konum_cm": [[507, 135.5, 758, 449.25]]})
    ie["acikliklar"] = [a for a in ie["acikliklar"] if a["tur"] == "dis_kapi"]
    if ayna:
        H = 835.75
        for m in ie["mahaller"]:
            m["konum_cm"] = [[r[0], round(H - r[3], 4), r[2], round(H - r[1], 4)] for r in m["konum_cm"]]
        ie["dikmeler"] = [[d[0], round(H - 10 - d[1], 4)] for d in ie["dikmeler"]]
        for a in ie["acikliklar"]:
            if "duvar_ucu" in a:
                a["duvar_ucu"] = {"on": "arka", "arka": "on"}.get(a["duvar_ucu"], a["duvar_ucu"])
        for d in ie["yapi"]["dizilim"].get("dis_pano_dayanagi", []):
            if "y" in d:
                d["y"] = round(H - d["y"], 4)
                d["aralik_cm"] = sorted(round(H - v, 4) for v in d["aralik_cm"])
    return ie


def test_kose_kirmasi_ayna_ayni_cati():
    # geometri hakemi 2. tur (B1): binme denetimi yanların sırasına bağlıydı; açık yan önde (ayna) iken uzayan ana çatı yüzü cumbanın
    # dereyle kesilmemiş planıyla kıyaslanıp "biniyor" hatası alıyordu. Şimdi denetim bütün yüzlerin son planına: ayna aynı çatıyı verir
    from motor import sunum
    hat = {}
    for ayna in (False, True):
        ie = _genis_veranda(ayna)
        t = sunum.cati_tanimi(_kur(ie), ie)
        hat[ayna] = {(h["tur"], *sorted([tuple(h["p"]), tuple(h["q"])])) for h in t["hatlar"]}
    assert hat[False] == {("dere", (542.0, 484.25), (793.0, 735.25)), ("kirma", (542.0, 614.75), (793.0, 865.75))}
    aynala = lambda q: (q[0], round(835.75 - q[1], 2))                         # noqa: E731
    assert hat[True] == {(tur, *sorted([aynala(p), aynala(q)])) for tur, p, q in hat[False]}
