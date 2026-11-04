"""D-50 (İE-30; Lokman, 4 Kasım 2026 20:42 ve 21:14, kart "Paftadan, ev ev") · AP-26: pencere bölmeleri, cam PVC kapı, teras paneli (PC-32).

Lokman: "pencereler çizimi tam doğru değil ayrıca teras ayrı bir teknikler yapılıyor çatı saçağının 10 cm altında çatı paneli olarak
kullandığımız bir 8 cm genişliğinde C den oluşan panel yapıyoruz üzerine yine Trapez sac araya damlalık atıyoruz yani çatı gibi şekilli
değil AP26 montaj paftasını iyice incele". Paftadan İş Emri'ne:
- pencerenin bölmeleri açıklık başına (`acikliklar[i].bolmeler`, İE-29'un biçimi; D-50 ile sürgülü ve vasistas bölmesi),
- dış kapının türü (`kapi_turu: pvc_cam`: beyaz, komple cam PVC kapı),
- taşan verandanın üstü teras paneli (`verandalar[i].cati: {tip: teras_paneli, cikma_cm}`: düz, duvar üstünün 10 altında, 8 cm).
Anahtarları yazılmamış İş Emri'nde hiçbir şey değişmez (TK-01 r07, TK-02, P6001; referans ve M-02 testleri ayrıca).
"""
from __future__ import annotations
import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
KOR = KOK / "testler" / "kor" / "projeler"
ANAHTARSIZ = (VERI / "TK01_r07.json", VERI / "TK02.json", KOK / "is_emri" / "P6001_2plus1_6x6.json")


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _ap26() -> dict:
    return _oku(KOR / "AP26" / "is_emri.json")


def _ac(ie: dict, **k) -> int:
    return next(i for i, a in enumerate(ie["acikliklar"]) if all(a.get(x) == y for x, y in k.items()))


@pytest.fixture(scope="module")
def ap26_dxf():
    import ezdxf
    from motor import dxf_out
    with tempfile.TemporaryDirectory() as t:
        dxf_out.uret(_ap26(), Path(t), pdf_hatada=False)
        yield ezdxf.readfile(next(Path(t).glob("*.dxf")))


# --------------------------------------------------------------------------- İş Emri biçimi (K21: yanlış yazım açık hata)

def test_ap26_is_emri_paftadan():
    """AP-26'nın İş Emri paftanın pencere ve kapı detayıyla, teraslar teras paneli: duvardan panel 140; derinlik 110 (gerçek listenin yan
    kirişleri 100; paftanın planında 120 yazılı, Lokman'a soruldu)."""
    ie = _ap26()
    plan = G.kur(copy.deepcopy(ie))
    v = {x["ad"]: x for x in plan.dis_verandalar}
    assert sorted(v) == ["ARKA TERAS", "ÖN TERAS"]
    for x in v.values():
        assert x["derinlik"] == 110 and x["cati"]["tip"] == "teras_paneli" and x["cati"]["cikma_cm"] == 140
    ac = [a for p in plan.panolar for a in p.aciklar]
    b = {a.olcu: a.bolmeler for a in ac if a.tur == "pencere"}
    assert [x["tur"] for x in b["280x210"]] == ["sabit", "surgulu", "surgulu", "sabit"]
    assert [x.get("yon") for x in b["280x210"]] == [None, "sol", "sag", None]
    assert [(x["tur"], x["mentese"]) for x in b["120x120"]] == [("kanat", "sol"), ("kanat", "sag")]   # menteşe dış yanlarda
    assert [x["tur"] for x in b["50x50"]] == ["vasistas"]
    assert b["200x210"] is None                                                         # iki bölmeli sürgülü: eski sürgülü bloğu
    assert sorted((a.kapi_turu or "-") for a in ac if a.tur == "dis_kapi") == ["-", "pvc_cam"]


@pytest.mark.parametrize("bolmeler, mesaj", [
    ([{"tur": "sabit", "en_cm": 140}, {"tur": "surgulu", "en_cm": 140}], "bölme"),                       # sürgülüde yon yok
    ([{"tur": "sabit", "en_cm": 140, "yon": "sol"}, {"tur": "surgulu", "en_cm": 140, "yon": "sol"}], "bölme"),   # yon yalnız sürgülüde
    ([{"tur": "sabit", "en_cm": 140}, {"tur": "surgulu", "en_cm": 140, "yon": "ust"}], "bölme"),
    ([{"tur": "vasistas", "en_cm": 280, "mentese": "sol"}], "bölme"),                                     # vasistasta menteşe yazılmaz
    ([{"tur": "sabit", "en_cm": 140}, {"tur": "surgulu", "en_cm": 130, "yon": "sol"}], "toplamı"),
    ([{"tur": "sabit", "en_cm": True}, {"tur": "surgulu", "en_cm": 279, "yon": "sol"}], "bölme"),
])
def test_bolmeler_yanlis_yazim(bolmeler, mesaj):
    ie = _ap26()
    ie["acikliklar"][_ac(ie, olcu="280x210")]["bolmeler"] = bolmeler
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(ie)


def test_surgulu_bolme_acilisla():
    """Sürgülü bölmesi olan pencere `acilis: surgulu` ile yazılır; sürgülüsüz bölmeli pencerede acilis yazılmaz (İE-29)."""
    ie = _ap26()
    del ie["acikliklar"][_ac(ie, olcu="280x210")]["acilis"]
    with pytest.raises(G.IsEmriHatasi, match="acilis: surgulu"):
        G.kur(ie)
    ie = _ap26()
    ie["acikliklar"][_ac(ie, olcu="120x120", mahal="MUTFAK")]["acilis"] = "surgulu"
    with pytest.raises(G.IsEmriHatasi, match="acilis'siz"):
        G.kur(ie)


@pytest.mark.parametrize("yer, deger", [("arka_kapi", "pvc"), ("arka_kapi", "celik"), ("pencere", "pvc_cam")])
def test_kapi_turu_yanlis_yazim(yer, deger):
    ie = _ap26()
    i = _ac(ie, tur="dis_kapi", duvar="arka") if yer == "arka_kapi" else _ac(ie, olcu="50x50")
    ie["acikliklar"][i]["kapi_turu"] = deger
    with pytest.raises(G.IsEmriHatasi, match="kapi_turu"):
        G.kur(ie)


@pytest.mark.parametrize("cati", [
    {"tip": "teras_paneli"},                                            # çıkma yok
    {"tip": "teras_paneli", "cikma_cm": 100},                           # derinlikten (110) kısa
    {"tip": "teras_paneli", "cikma_cm": 175},                           # derinlikten 60'tan fazla
    {"tip": "teras_paneli", "cikma_cm": 140, "egim_yuzde": 5},          # eğim yazılmaz (düz)
    {"tip": "teras_paneli", "cikma_cm": "140"},
])
def test_teras_paneli_yanlis_yazim(cati):
    ie = _ap26()
    ie["verandalar"][0]["cati"] = cati
    with pytest.raises(G.IsEmriHatasi, match="teras_paneli"):
        G.kur(ie)


# --------------------------------------------------------------------------- teras panelinin geometrisi

def test_teras_paneli_kotlari_ve_gorunusu():
    """Panelin üst yüzü duvar üstünün (ana çatının saçak altı çizgisi) 10 cm altında, 8 cm kalın; planda duvardan 140, cephe boyunca
    verandanın eni. Görünüşte kolon kirişin altına, kiriş panelin altında, panel düz bant; topuk, kalkan ve eğik çatı çizgisi yok."""
    from motor import veranda as VR
    ie = _ap26()
    plan = G.kur(copy.deepcopy(ie))
    on = next(v for v in plan.dis_verandalar if v["cephe"] == "on")
    T = VR.cati(on, ie)
    assert T["tip"] == "teras_paneli" and T["mahya"] is None and T["egim"] == 0
    assert (T["sacak_kotu"], T["alt_kotu"]) == (240.0, 232.0)
    x0, _, x1, y1 = on["rect"]
    assert T["kutu"] == (x0, y1 - 140, x1, y1)
    assert VR.uyarilar(plan, ie) == []
    for taraf in ("on", "sol"):
        p = [q for q in VR.gorunus_parcalari(plan, ie, taraf) if q["veranda"] == on["ad"]]
        assert {q["tur"] for q in p} == {"kolon", "kiris", "cati"}
        assert not any(q.get("kalkan") or q.get("acik") for q in p)
        assert {max(z for _, z in q["u"]) for q in p if q["tur"] == "kolon"} == {222.0}
        assert {(min(z for _, z in q["u"]), max(z for _, z in q["u"])) for q in p if q["tur"] == "kiris"} == {(222.0, 232.0)}
        (panel,) = [q for q in p if q["tur"] == "cati"]
        assert panel["panel"] and {z for _, z in panel["u"]} == {232.0, 240.0}
        if taraf == "sol":                                              # yandan: duvardan panelin dış kenarına 140
            us = [u for u, _ in panel["u"]]
            assert round(max(us) - min(us), 6) == 140.0


# --------------------------------------------------------------------------- çizim (ön onay PDF'inin DXF'i)

def test_ap26_gorunus_bloklari(ap26_dxf):
    """Görünüşte 280/210 dört bölmeli (sabit, sürgülü, sürgülü, sabit), 120/120 iki kanat, 50/50 vasistas, arka kapı cam PVC; 200/210
    eski sürgülü bloğu, ön kapı çelik kapı bloğu."""
    adlar = sorted(e.dxf.name for e in ap26_dxf.modelspace().query("INSERT") if e.dxf.layer == "ON_DOGRAMA")
    assert adlar == sorted(["kaynak-on-kapi", "on-pvc-kapi-sol", "on-surgulu", "on-pencere-280x210-s70-su70so-su70sa-s70",
                            "on-pencere-50x50-v50"] + ["on-pencere-120x120-k60so-k60sa"] * 3)


def _kirmizi(doc, ad):
    return [((float(e.dxf.start.x), float(e.dxf.start.y)), (float(e.dxf.end.x), float(e.dxf.end.y)))
            for e in doc.blocks.get(ad).query("LINE") if e.dxf.color == 1]


def test_kanat_kollari_kol_yaninda_bulusur(ap26_dxf):
    """D-50: açılımın kolları menteşe yanının iki köşesinden kol yanının ortasına (AP-26 paftası: 120/120'de ortada; kapı detayında kol
    üçgenin tepesinde). 120/120: menteşe dış yanlarda, kollar ortadaki kayıtta buluşur."""
    k = _kirmizi(ap26_dxf, "on-pencere-120x120-k60so-k60sa")
    xs = [x for (a, b) in k for x in (a[0], b[0])]
    sol = [x for x in xs if x < 60]
    sag = [x for x in xs if x > 60]
    assert len(sol) + len(sag) == len(xs)
    assert (round(min(sol), 2), round(max(sol), 2)) == (12.5, 52.5)       # sol kanat: menteşe solda (12,5), kollar sağda (52,5)
    assert (round(min(sag), 2), round(max(sag), 2)) == (67.5, 107.5)
    tepe = [b for (a, b) in k if abs(b[0] - 52.5) < 0.6]                  # kolların ucu kol yanının ortasında
    assert tepe and all(abs(y - 60.0) < 6 for _, y in tepe)


def test_surgulu_ve_vasistas_bolmesi(ap26_dxf):
    """280/210: iki orta kanatta kırmızı yön oku dışa (sol kanat sola, sağ kanat sağa); sabitlerde ok yok. 50/50: kollar alt köşelerden
    üst ortaya (vasistas bloğundaki gibi)."""
    k = _kirmizi(ap26_dxf, "on-pencere-280x210-s70-su70so-su70sa-s70")
    yatay = [(a, b) for a, b in k if abs(a[1] - b[1]) < 1e-6 and abs(a[0] - b[0]) > 20]
    assert len(yatay) == 2
    (s0, s1), (t0, t1) = sorted(yatay, key=lambda q: q[0][0])
    assert 70 < min(s0[0], s1[0]) and max(s0[0], s1[0]) < 140 and s1[0] < s0[0]        # ikinci bölme: uç solda
    assert 140 < min(t0[0], t1[0]) and max(t0[0], t1[0]) < 210 and t1[0] > t0[0]       # üçüncü bölme: uç sağda
    assert not any(x < 70 or x > 210 for (a, b) in k for x in (a[0], b[0]))
    v = _kirmizi(ap26_dxf, "on-pencere-50x50-v50")
    ust = max(y for (a, b) in v for y in (a[1], b[1]))
    assert any(abs(b[0] - 25.0) < 0.6 and abs(b[1] - ust) < 1e-6 for _, b in v)       # tepe üst ortada


def test_pvc_kapi_menteseye_gore(ap26_dxf):
    """Cam PVC kapı: menteşe planın kapı sembolüyle aynı yanda (arka görünüşte bakanın solunda; paftanın planında kapı yatak odası 1'e
    iç duvar yanındaki menteşeden açılır), kol karşı yanda ortada, kollar kol yanında buluşur."""
    k = _kirmizi(ap26_dxf, "on-pvc-kapi-sol")
    bas = {round(a[0], 2) for a, _ in k}
    uc = [b for _, b in k]
    assert min(bas) == 8.0                                                  # menteşe yanı (sol) köşeleri
    assert max(x for x, _ in uc) == pytest.approx(82.0)                      # kol yanı (sağ), kol yüksekliğinde
    from motor import cephe_gorunus as CG
    plan = G.kur(_ap26())
    (a,) = [a for a in CG.cephe(plan, "arka")["acikliklar"] if a["tur"] == "dis_kapi"]
    assert (a["kapi_turu"], a["mentese"]) == ("pvc_cam", "sol")


def test_teras_paneli_planda(ap26_dxf):
    """Planda panelin dış çizgisi duvardan 140 (paftanın planındaki gibi). Katman yalnız teras panelli planda."""
    pl = [e for e in ap26_dxf.modelspace().query("LWPOLYLINE") if e.dxf.layer == "VERANDA_PANEL"]
    assert pl and len(pl) % 2 == 0                                          # iki teras, planın her kopyasında
    for e in pl:
        xs = [p[0] for p in e.get_points()]; ys = [p[1] for p in e.get_points()]
        assert round(max(ys) - min(ys), 4) == 140.0


def test_ap27_kayitlarinin_blogu_degismedi():
    """İE-29'un AP-27 pencereleri (veri tabanı 180x210, 140x150): D-50'de menteşe adı kanadın sabit yanına çevrildi, çizgiler aynı (AP-27
    paftasında kollar dış yanda buluşur; İE-29'un görünüş testindeki 12,5–38,5 ve 141,5–167,5)."""
    import ezdxf
    from motor import dxf_out
    c = dxf_out.Cizici.__new__(dxf_out.Cizici)
    c.doc = ezdxf.new()
    ad = c._bolmeli_blok("180x210")
    xs = [x for (a, b) in _kirmizi(c.doc, ad) for x in (a[0], b[0])]
    sol, sag = [x for x in xs if x < 46], [x for x in xs if x > 134]
    assert len(sol) + len(sag) == len(xs)
    assert (round(min(sol), 2), round(max(sol), 2)) == (12.5, 38.5)
    assert (round(min(sag), 2), round(max(sag), 2)) == (141.5, 167.5)
    tepe = {round(b[0], 2) for _, b in _kirmizi(c.doc, ad)}
    assert {12.5, 167.5} <= tepe                                            # kollar dış yanda buluşur (görünüş eskisi gibi)


@pytest.mark.parametrize("yol", ANAHTARSIZ, ids=lambda p: p.stem)
def test_anahtarsiz_is_emrinde_yeni_blok_yok(yol):
    """Bölmesi, kapı türü ve teras paneli yazılmamış İş Emri'nde yeni blok ve katman yok (TK-01 r07, TK-02, P6001)."""
    import ezdxf
    from motor import dxf_out
    with tempfile.TemporaryDirectory() as t:
        dxf_out.uret(_oku(yol), Path(t), pdf_hatada=False)
        doc = ezdxf.readfile(next(Path(t).glob("*.dxf")))
    assert "VERANDA_PANEL" not in doc.layers
    assert not [b.name for b in doc.blocks if b.name.startswith(("on-pencere-", "on-pvc-kapi"))]


# --------------------------------------------------------------------------- liste ve 3B

def test_liste_teras_paneli_panel_cati():
    """Teras paneli listede makassız panel çatı parçası (AP-09'un açık mahal panel çatısı gibi; Lokman: "çatı paneli olarak kullandığımız
    ... C den oluşan panel", "çatı gibi şekilli değil"): yavru makas ve aşık yok, "Çatı paneli (hafif çelik)" satırı "Kural yok"; trapez
    duvardan panelin dış kenarına (140 + bindirme payı; paftada trapez 150 × 6 + 6). Panel, damlalık ve tavan satırları çizim onayından sonra."""
    from motor import prefabrik_liste as PL
    L = PL.is_emrinden(_ap26())
    k = {(s["kalem"], s["olcu"]): s for s in L["satirlar"]}
    for ad in ("ön teras çatısı", "arka teras çatısı"):
        assert k[(f"Çatı paneli (hafif çelik) · {ad}", "—")]["dayanak"] == "Kural yok"
        assert not any(x["kalem"] == f"Yavru makas · {ad}" for x in L["satirlar"])
        assert k[(f"Trapez sac · {ad}", "L 1450")]["adet"] == 6


def test_ifc_teras_paneli_duz():
    """3B modelde teras paneli düz levha (232–240), kiriş panelin altında (222–232), dikme kirişin altına (0–222)."""
    import ifcopenshell
    from motor import ifc_uret
    with tempfile.TemporaryDirectory() as t:
        yol = Path(t) / "ap26.ifc"
        oz = ifc_uret.uret(_ap26(), yol)
        f = ifcopenshell.open(str(yol))
        catilar = [e for e in f.by_type("IfcRoof") if e.Name.startswith("VERANDA_CATISI_")]
        assert {e.PredefinedType for e in catilar} == {"FLAT_ROOF"}

        def kot(e):
            for r in e.IsDefinedBy:
                ps = getattr(r, "RelatingPropertyDefinition", None)
                if ps and ps.is_a("IfcPropertySet") and ps.Name == "PortatifEv_Kapsam":
                    return next((p.NominalValue.wrappedValue for p in ps.HasProperties if p.Name == "Kot_cm"), None)
        dikme = {kot(e) for e in f.by_type("IfcColumn") if e.Name.startswith("DIKME_")}
        profil = {kot(e) for e in f.by_type("IfcBeam") if e.Name.startswith("VERANDA_PROFIL_")}
    assert dikme == {"0–222"} and profil == {"222–232"}
    assert oz.get("hata", oz.get("hatalar", 0)) in (0, [], None)
