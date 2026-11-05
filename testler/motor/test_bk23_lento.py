"""BK-23 (D-55): İş Emri'nde `yapi.lento_cm`. Lokman, 5 Kasım 2026 10:47 (TK-05, dış 160 / iç 100 duvarlı 20 m²): "yükseklik 280cm lento 70".

Lento yalnız İş Emri'nin seçeneğidir: yazılırsa pencere ve kapı üst kotu = duvar yüksekliği − lento (280 − 70 = 210), eşik = üst kot − boy;
yazılmazsa D-14'ün varsayılanı (üst kot 200, 280'de lento 80) aynen ve anahtarsız İş Emri bayt bayt eski yoldan gider. Plan (pano,
ölçü, alan) lentoyla değişmez; değişen yalnız görünüş, IFC'deki açıklık kotları ve listedeki pencere üst/alt panel boyları."""
import json
from pathlib import Path

import pytest

from motor import geometry as G

KOK = Path(__file__).resolve().parents[2]
TK02 = KOK / "testler" / "motor" / "veri" / "TK02.json"
P6001 = KOK / "is_emri" / "P6001_2plus1_6x6.json"


def _oku(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _ie(lento=None, h=280, yol=TK02) -> dict:
    ie = _oku(yol)
    ie["yapi"]["duvar_yuksekligi_cm"] = h
    if lento is not None:
        ie["yapi"]["lento_cm"] = lento
    return ie


@pytest.fixture(autouse=True)
def _durum_temiz():
    """Lento modül durumudur (kalınlık gibi): her testten sonra varsayılana döner, öteki testlere sızmaz."""
    yield
    G.lento_ayarla({})


def test_anahtarsiz_ust_kot_200():
    G.kur(_ie())
    assert G.ust_kot() == G.PENCERE_UST_KOTU_CM == 200.0
    k = G.pencere_kurali("120x120")
    assert (k.esik, k.ust) == (80.0, 200.0)


def test_lento_70_ust_kot_210_esik_90():
    G.kur(_ie(70))
    assert G.ust_kot() == 210.0
    assert [(k.esik, k.ust) for k in map(G.pencere_kurali, ("120x120", "120x180", "60x40"))] == [(90.0, 210.0), (30.0, 210.0), (170.0, 210.0)]
    G.kur(_ie())                                              # anahtarsız kurulum durumu geri alır
    assert G.ust_kot() == 200.0 and G.pencere_kurali("120x120").esik == 80.0


def test_plan_lentoyla_degismez():
    """Lento planın geometrisini değiştirmez: pano, ölçü, mahal alanı aynı."""
    a, b = G.kur(_ie()), G.kur(_ie(70))
    iz = lambda p: (p.W, p.H, sorted((round(q.a0, 3), round(q.a1, 3)) for d in p.duvarlar for q in d.panolar),
                    {k: round(m.poly.area, 3) for k, m in p.mahaller.items() if m.poly is not None})
    assert iz(a) == iz(b)


@pytest.mark.parametrize("lento", [0, -10, 81, "70", True, None])
def test_gecersiz_lento_hata_ve_durum_sifirlanir(lento):
    ie = _ie()
    ie["yapi"]["lento_cm"] = lento
    with pytest.raises(G.IsEmriHatasi, match="lento_cm"):
        G.kur(ie)
    assert G.ust_kot() == 200.0


def test_250de_lento_50_eski_yolla_ayni(tmp_path):
    """250'de lento 50 = varsayılan: DXF'in yazıları ve katman katman öğe sayıları aynı (bayt kıyası `dogrula.py`'de, anahtarsız İş Emri'yle)."""
    import ezdxf
    from collections import Counter
    from motor import dxf_out
    izler = []
    for k, ie in enumerate((_ie(h=250, yol=P6001), _ie(50, h=250, yol=P6001))):
        m = dxf_out.uret(ie, tmp_path / str(k), pdf_hatada=False)
        assert m["validation_passed"]
        msp = ezdxf.readfile(tmp_path / str(k) / Path(m["dxf"]).name).modelspace()
        izler.append((sorted(t.dxf.text for t in msp.query("TEXT") if "Üretim" not in t.dxf.text),
                      Counter((e.dxftype(), e.dxf.layer) for e in msp)))
    assert izler[0] == izler[1]


def test_gorunus_yazisi_ve_kapi(tmp_path):
    import ezdxf
    from motor import dxf_out
    m = dxf_out.uret(_ie(70), tmp_path, pdf_hatada=False)
    assert m["validation_passed"]
    yazilar = [t.dxf.text for t in ezdxf.readfile(tmp_path / Path(m["dxf"]).name).modelspace().query("TEXT")]
    assert any("Pencere üst kotu 210 cm" in t and "Lento 70 cm" in t and "Bina yüksekliği 280 cm" in t for t in yazilar), \
        [t for t in yazilar if "Lento" in t or "lento" in t]
    assert any("(lento): 70 cm" in t for t in yazilar)


def test_ifc_aciklik_kotlari():
    """IFC: kapılar ve pencereler aynı üst kotta (210); 120x120'nin eşiği 90; `bina.lento` 70."""
    from motor import ifc_uret
    v = ifc_uret.hazirla(_ie(70))
    assert v["bina"]["lento"] == 70.0
    ac = v["acikliklar"]
    assert {a["tur"] for a in ac} >= {"pencere", "kapi"} and all(a["z1"] == 210.0 for a in ac), {(a["tur"], a["z0"], a["z1"]) for a in ac}
    assert {(a["olcu"], a["z0"]) for a in ac if a["tur"] == "pencere"} >= {("120x180", 30.0), ("60x40", 170.0)}
    eski = ifc_uret.hazirla(_ie())
    assert eski["bina"]["lento"] == 80.0 and all(a["z1"] == 200.0 for a in eski["acikliklar"])


def test_liste_pencere_panolari():
    from motor import prefabrik_liste as PL
    sat = PL.is_emrinden(_ie(70))["satirlar"]
    ust = {s["olcu"].split(" × ")[2] for s in sat if s["kalem"].startswith("Pencere üst panel")}
    alt = {s["kalem"]: s["olcu"].split(" × ")[2] for s in sat if s["kalem"].startswith("Pencere alt panel")}
    assert ust == {"700"}, ust
    assert alt.get("Pencere alt panel (120/120)") == "900", alt
    eski = PL.is_emrinden(_ie())["satirlar"]
    assert {s["olcu"].split(" × ")[2] for s in eski if s["kalem"].startswith("Pencere üst panel")} == {"800"}
    adet = lambda S: sorted((s["kalem"], s["adet"]) for s in S if s["grup"] == "1001")
    assert adet(sat) == adet(eski)                            # adetler aynı, yalnız üst/alt panel boyu değişir


def test_liste_lentoyu_modelden_okur():
    """Hakem bulgusu 1: liste üst kotu modül durumundan değil modelden okur. Lentolu bir kurulumdan sonra pafta kipindeki liste 200'le kalır;
    lentolu evin modeli de sonradan kurulan lentosuz evden etkilenmez."""
    from motor import prefabrik_liste as PL
    yp = _oku(KOK / "testler" / "kor" / "projeler" / "PK07" / "yapi_pafta.json")
    pencere = lambda L: sorted((s["kalem"], s["olcu"]) for s in L["satirlar"] if s["kalem"].startswith("Pencere "))
    temiz = pencere(PL.liste(PL.model_pafta(json.loads(json.dumps(yp)))))
    G.kur(_ie(70))
    assert pencere(PL.liste(PL.model_pafta(json.loads(json.dumps(yp))))) == temiz
    N = PL.model_motor(_ie(70))
    G.kur(_ie())                                              # modül durumu 200'e döndü
    ust = {s["olcu"].split(" × ")[2] for s in PL.liste(N)["satirlar"] if s["kalem"].startswith("Pencere üst panel")}
    assert ust == {"700"}, ust
    assert "ust_kot_cm" not in PL.model_motor(_ie())         # lentosuz modelde anahtar yok (eski çıktı aynen)


def test_gorunus_kapi_ve_pencere_kotlari():
    """Hakem bulgusu 4: görünüşte kapının üstü ve pencere kotları (yalnız yazıya değil, açıklıklara bakar)."""
    from motor import cephe_gorunus as CG
    plan = G.kur(_ie(70))
    ac = [a for t in CG.TARAFLAR for a in CG.cephe(plan, t)["acikliklar"]]
    assert {a["tur"] for a in ac} == {"pencere", "dis_kapi"}
    assert all(a["z1"] == 210.0 for a in ac) and all(a["z0"] == 0.0 for a in ac if a["tur"] == "dis_kapi")
    assert {(a["olcu"], a["z0"]) for a in ac if a["tur"] == "pencere"} >= {("120x180", 30.0), ("60x40", 170.0)}


def test_kur_hatasinda_lento_sifirlanir():
    """Hakem bulgusu 4: lento geçerli, kurulum başka bir hatayla düşerse üst kot 200'e döner."""
    ie = _ie(70)
    ie["yapi"]["kat_sayisi"] = 2
    with pytest.raises(G.IsEmriHatasi):
        G.kur(ie)
    assert G.ust_kot() == 200.0


# ── madde 2: dış pano dayanağı yalnız yazılan cephede (TK-05 r06, müşterinin beğendiği plan; Lokman 5 Kasım 2026 11:10–11:51) ──────────
TK05 = KOK / "testler" / "motor" / "veri" / "TK05_r06.json"


def _x_duvarlari(ie: dict) -> dict:
    """Gerçek çerçevede x boyunca uzanan dış duvarlar: eksen y → (pano uçları, açıklık türleri)."""
    p = G.kur(ie)
    return {round(d.c, 2): ([round(q.a0, 2) for q in d.panolar] + [round(d.panolar[-1].a1, 2)],
                            [q.acilim.tur if q.acilim else "-" for q in d.panolar])
            for d in p.duvarlar if d.tur == "dis" and d.yon == "x"}


def test_tk05_on_pencere_ortada_arka_duvar_tam_pano():
    """TK-05 r06 (dış 160 / iç 100, 280, lento 70; 3 × 4 pano): öndeki 120x180 A–C duvarında tam ortada, iki yanı 62,75 (`cephe: on`);
    arka duvar ızgarada (üç tam pano, 60x40 C–D panosunda); çelik kapı önde C–D'de; banyo C–D, aks 2,5–5."""
    ie = _oku(TK05)
    assert ie["yapi"]["dizilim"]["dis_pano_dayanagi"] == [{"x": 204.25, "aralik_cm": [16, 267], "cephe": "on"}]
    d = _x_duvarlari(ie)
    assert d[8.0] == ([16.0, 78.75, 204.25, 267.0, 392.5], ["-", "pencere", "-", "dis_kapi"])      # ön
    assert d[510.0] == ([16.0, 141.5, 267.0, 392.5], ["-", "-", "pencere"])                        # arka
    p = G.kur(ie)
    assert (p.W, p.H, len(p.panolar)) == (408.5, 518.0, 21)
    assert {k: round(m.poly.area / 1e4, 2) for k, m in p.mahaller.items()} == {"YATAK ODASI": 14.24, "BANYO": 3.62}
    assert G.ust_kot() == 210.0


def test_on_sol_baslangicta_ayni_duvar():
    """Hakem bulgusu 7: başlangıç on-sol (y önden) ve mahaller aynalanınca `cephe: on` yine gerçek ön duvarı seçer."""
    ie = _oku(TK05)
    ie["yapi"]["dizilim"]["baslangic"] = "on-sol"
    H = ie["yapi"]["dis_olcu_cm"]["y"]
    for m in ie["mahaller"]:
        m["konum_cm"] = [[x0, round(H - y1, 2), x1, round(H - y0, 2)] for x0, y0, x1, y1 in m["konum_cm"]]
    assert _x_duvarlari(ie) == _x_duvarlari(_oku(TK05))


def test_cephesiz_dayanak_eskisi_gibi_iki_duvarda():
    """`cephe` yazılmamış dayanak D-34'teki gibi aralıktaki bütün dış duvarlara (TK-03 aynen)."""
    ie = _oku(TK05)
    del ie["yapi"]["dizilim"]["dis_pano_dayanagi"][0]["cephe"]
    d = _x_duvarlari(ie)
    assert d[8.0][0] == d[510.0][0] == [16.0, 78.75, 204.25, 267.0, 392.5]


def test_cephe_arka_yalniz_arka_duvar():
    ie = _oku(TK05)
    ie["yapi"]["dizilim"]["dis_pano_dayanagi"][0]["cephe"] = "arka"
    d = _x_duvarlari(ie)
    assert d[510.0][0] == [16.0, 78.75, 204.25, 267.0, 392.5] and 78.75 not in d[8.0][0]          # ön duvar dayanaksız (pencere oda ortasında)


@pytest.mark.parametrize("cephe", ["sol", "sag", "ön", 1])
def test_gecersiz_cephe_hata(cephe):
    ie = _oku(TK05)
    ie["yapi"]["dizilim"]["dis_pano_dayanagi"][0]["cephe"] = cephe
    with pytest.raises(G.IsEmriHatasi, match="dis_pano_dayanagi"):
        G.kur(ie)


def test_cephe_ile_ic_duvarlar_hata():
    """Hakem bulgusu 6 (K21): cephe yalnız dış duvarı seçer; `ic_duvarlar: true` ile birlikte sessizce düşmez, hata."""
    ie = _oku(TK05)
    ie["yapi"]["dizilim"]["dis_pano_dayanagi"][0]["ic_duvarlar"] = True
    with pytest.raises(G.IsEmriHatasi, match="ic_duvarlar birlikte"):
        G.kur(ie)


def _y_duvarlari(ie: dict) -> dict:
    p = G.kur(ie)
    return {d.id: [round(q.a0, 2) for q in d.panolar] + [round(d.panolar[-1].a1, 2)] for d in p.duvarlar if d.tur == "dis" and d.yon == "y"}


@pytest.mark.parametrize("cephe, dayanakli", [(None, {6, 9}), ("sol", {6}), ("sag", {9})])
def test_cephe_acik_mahale_bakan_duvar(cephe, dayanakli):
    """Hakem bulgusu 5 (K21): verandaya bakan dış duvar (P6001 duvar 6, dışı veranda) cephesini görünüşlerdeki gibi alır (`disari_yon`);
    `cephe: sol` onu seçer, sağdaki dış duvarı (9) seçmez. y aksında ve on-sol başlangıçta (hakem bulgusu 7)."""
    ie = _oku(P6001)
    ie["yapi"]["ek_akslar_cm"] = {"x": [], "y": [67.75]}
    ie["yapi"].setdefault("dizilim", {})["dis_pano_dayanagi"] = [{"y": 67.75, "aralik_cm": [5, 256], **({"cephe": cephe} if cephe else {})}]
    d = _y_duvarlari(ie)
    assert {k for k, v in d.items() if 67.75 in v} == dayanakli, d


def test_dis_normal_gorunusle_ayni():
    """Dayanağın cephesi görünüşlerin cephesiyle aynı kuraldan: açık mahalli planlarda her dış duvarda `_dis_normal` = `disari_yon`."""
    for yol in (P6001, TK02, KOK / "testler" / "motor" / "veri" / "TK03.json", KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json"):
        p = G.kur(_oku(yol))
        assert all(G._dis_normal(d, p.mahaller) == G.disari_yon(p, d) for d in p.duvarlar if d.tur == "dis"), yol.name


def test_tk05_cizim_dogrulamasi(tmp_path):
    from motor import dxf_out
    m = dxf_out.uret(_oku(TK05), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] and not m["warnings"]


# ── madde 3: planda yalnız en ve boy (TK-05; Lokman 5 Kasım 2026 11:37: "içteki pano ölçülerini kaldır bu genel kural değil şimdilik") ──
def _plan_olculeri(ie: dict, yol: Path) -> tuple:
    import ezdxf
    from motor import dxf_out
    m = dxf_out.uret(ie, yol, pdf_hatada=False)
    assert m["validation_passed"]
    msp = ezdxf.readfile(yol / Path(m["dxf"]).name).modelspace()
    return msp, sorted(round(d.get_measurement(), 2) for d in msp.query("DIMENSION") if d.dxf.layer == "OZEL_PANEL_OLCU_CM")


def test_plan_olcusu_en_boy(tmp_path):
    """`cikti.plan_olcusu: en_boy` → kat planında özel pano ve açık mahal ölçüsü yok; montaj kopyasındaki özel pano ölçüleri aynen."""
    ie = _oku(TK05)
    msp0, ozel0 = _plan_olculeri(ie, tmp_path / "a")
    assert ozel0 and 62.75 in ozel0                           # anahtarsız: özel pano ölçüleri planda (PC-06)
    ie["cikti"]["plan_olcusu"] = "en_boy"
    msp1, ozel1 = _plan_olculeri(ie, tmp_path / "b")
    assert ozel1 == []
    montaj = lambda msp: sorted(round(d.get_measurement(), 2) for d in msp.query("DIMENSION") if d.dxf.layer == "MONTAJ_OZEL_OLCU")
    assert montaj(msp1) == montaj(msp0)
    olc = lambda msp: {round(d.get_measurement(), 2) for d in msp.query("DIMENSION") if d.dxf.layer not in ("OZEL_PANEL_OLCU_CM", "MONTAJ_OZEL_OLCU")}
    assert {408.5, 518.0} <= olc(msp1) and len(list(msp1.query("DIMENSION"))) < len(list(msp0.query("DIMENSION")))


def test_plan_olcusu_gecersiz_hata():
    ie = _oku(TK05)
    ie["cikti"]["plan_olcusu"] = "net"
    with pytest.raises(G.IsEmriHatasi, match="plan_olcusu"):
        G.kur(ie)
