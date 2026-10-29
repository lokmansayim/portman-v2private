"""D-31 · Prefabrik ön onay çiziminin görünüş kuralları (Lokman, 29 Ekim 2026 11:07–11:23; CIO 11:07), Motor kuralı olarak.

1. Beşik çatı da dört görünüşle (ön, arka, sol, sağ); "ÇATI PROFİLİ - TOPUK VE SAÇAK" ve altındaki yazılar yok ("çatı profili topuk ve saçak
   tamamen kaldır bunlar GPT Astra'dan kalma").
2. Taşan verandanın çatısı ana çatının küçüğü ("tıpa tıp aynısı sadece daha küçüğü eğim olarak aynı topuk aynı"): saçak altı çizgisi, iki uçta
   topuk, iki eğim, her eğimde % yazısı. Karşı cephedeki veranda çizilmez; yandan bakışta ana çatının ardında kalan parça kırpılır.
3. Kalkanın alın çerçevesi yok: `test_veranda.py::test_gorunuste_alin_yok_kalkan_cati_cizgisinde`.
4. Aks çizgisi soluk gri ve veranda kirişi gibi kesik ("tireleri veranda kirişi çizdiğimiz gibi olsun lakin rengi belli belirsiz olsun").
5. 60×40 pencere görünüşte vasistas, tek kanat, üstten açılır ("yukarıdan aşağıya doğru açılır yani yana doğru değil tek kanat").
6. Derz yalnız görünen ve cepheye değen duvardan ("2 WC'nin arasında sadece H var 2 ek çizgi var").
7. Veranda kolonu görünüşte soluk dolgulu (11:55: "arka görünüşte ... sağ taraftaki direk mi eksik").
8. % eğim yalnız ana çatıda, görünüşte bir kez (11:55: "%33 eğimi sadece ana çatıda tek tarafta belirtsen yeter"); veranda eğimi yalnız
   farklıysa.
9. İş Emri'nde `acilis: "surgulu"` yazan pencere görünüşte sürgülü (11:57: "arka verandadaki pencere aslında sürgülü kapı gibi kullanılıyor").
10. PDF tek sayfa, dikey A4: üstte ön ve arka, altta sol ve sağ görünüş, sayfa enine sığar; kat planı aradaki yerin ortasında (12:01–12:21:
    "önce görünüşleri tam sığdır sonra ortaya kat planını al", "ikinci sayfayı artık tamamen kaldır").
11. A4'teki kat planında 125,5'lik aks ölçü zinciri yok (12:20: "kat planının 125,5 pano ölçülerini tamamen kaldır"); DXF'te durur.

Kural listesi `kurallar/prefabrik/cizim_kurallari.json` (PC-09 … PC-20) bu testleri gösterir (`test_prefabrik_cizim_kurallari.py`).
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import ezdxf
import pytest
from shapely.geometry import LineString, MultiPoint, Point

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cephe_gorunus as CG, dxf_out, geometry as G  # noqa: E402
from motor.katalog import Katalog  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
GIRDI = {"TK02": VERI / "TK02.json", "P6001": KOK / "is_emri" / "P6001_2plus1_6x6.json"}
BASLIK = [f"{CG.AD[t]} GÖRÜNÜŞ - ÇALIŞMA" for t in CG.TARAFLAR]


def _ie(ad: str) -> dict:
    return json.loads(GIRDI[ad].read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=sorted(GIRDI))
def cizim(request, tmp_path_factory):
    ad = request.param
    cikti = tmp_path_factory.mktemp(ad)
    m = dxf_out.uret(_ie(ad), cikti, pdf_hatada=False)
    return ad, m, ezdxf.readfile(cikti / m["dxf"])


@pytest.fixture(scope="module")
def tk02():
    ie = _ie("TK02")
    plan = G.kur(copy.deepcopy(ie))
    return ie, plan, dxf_out.Cizici(plan, Katalog())


def test_besik_dort_gorunus_profil_yok(cizim):
    ad, m, doc = cizim
    msp = doc.modelspace()
    assert m["validation_passed"] is True, m.get("errors")
    yazi = sorted(((e.dxf.insert.x, e.dxf.text) for e in msp.query("TEXT") if "GÖRÜNÜŞ" in e.dxf.text))
    assert [t for _x, t in yazi] == BASLIK                                   # dördü bir kez, soldan sağa ön, arka, sol, sağ
    assert not [e for e in msp.query("TEXT") if "PROFİLİ" in e.dxf.text or "cm'yi geçer" in e.dxf.text]
    assert not [e for e in msp if e.dxf.layer.startswith("CATI_")]          # katmanlar tanımlı, boş


def test_veranda_catisi_ana_catinin_kucugu(tk02):
    ie, plan, c = tk02
    egim = float(ie["cati"]["egim_yuzde"]) / 100; topuk = float(ie["cati"]["topuk_cm"]); hy = float(ie["yapi"]["duvar_yuksekligi_cm"])
    for taraf, ad in (("on", "ÖN VERANDA"), ("arka", "ARKA VERANDA")):
        vp = c._veranda_gorunusu(taraf, CG.cati_cizgileri(plan, ie, taraf))
        kal = [p["u"] for p in vp if p.get("kalkan")]
        assert len(kal) == 1 and [p["veranda"] for p in vp if p.get("kalkan")] == [ad]
        (a, za), (um, zm), (b, zb) = kal[0]
        assert za == zb == hy + topuk                                       # iki uç topuğun üstünde, ana çatınınki gibi
        assert (zm - za) / (um - a) == pytest.approx(egim) and (zm - zb) / (b - um) == pytest.approx(egim)
        assert [p["u"] for p in vp if p["tur"] == "topuk" and p["veranda"] == ad] == [[(a, hy), (a, hy + topuk)], [(b, hy), (b, hy + topuk)]]
        assert [p["u"] for p in vp if p["tur"] == "sacak" and p["veranda"] == ad] == [[(a, hy), (b, hy)]]
        assert not [p for p in vp if p["tur"] in ("yazi", "alin")]          # eğim ana çatınınkiyle aynı: yazılmaz (madde 10); alın yok


def test_karsi_veranda_cizilmez_yanda_kirpilir(tk02):
    ie, plan, c = tk02
    for taraf, gizli in (("on", "ARKA VERANDA"), ("arka", "ÖN VERANDA")):
        assert not [p for p in c._veranda_gorunusu(taraf, CG.cati_cizgileri(plan, ie, taraf)) if p.get("veranda") == gizli]
    for taraf in ("sol", "sag"):
        r = CG.cati_cizgileri(plan, ie, taraf)
        ortu = MultiPoint([q for k in r["cizgiler"] for q in k]).convex_hull.buffer(-0.05)
        vp = [p for p in c._veranda_gorunusu(taraf, r) if p["tur"] != "yazi"]
        assert {p["veranda"] for p in vp} == {"ÖN VERANDA", "ARKA VERANDA"}
        assert all(LineString(p["u"]).intersection(ortu).length < 1e-6 for p in vp if len(p["u"]) > 1)


def test_aks_soluk_ve_kesik(cizim):
    ad, m, doc = cizim
    aks, veranda = doc.layers.get("AKS"), doc.layers.get("VERANDA_PROFIL_100")
    assert (aks.color, aks.dxf.linetype) == (9, "VERANDA_KESIK") == (dxf_out.AKS_KATMANI[1], veranda.dxf.linetype)
    cizgi = [e for e in doc.modelspace() if e.dxf.layer == "AKS" and e.dxftype() == "LINE"]
    assert cizgi and all(e.dxf.get("color", 256) == 256 and e.dxf.get("linetype", "BYLAYER") == "BYLAYER" for e in cizgi)


def test_vasistas_60x40(cizim):
    ad, m, doc = cizim
    plan = G.kur(_ie(ad))
    ac = [a for t in CG.TARAFLAR for a in CG.cephe(plan, t)["acikliklar"] if a["tur"] == "pencere"]
    ad_v, en, boy, k = dxf_out.VASISTAS_BLOK
    v = [e for e in doc.modelspace().query("INSERT") if e.dxf.name == ad_v]
    assert len(v) == sum(a["olcu"] == "60x40" for a in ac) == {"TK02": 2, "P6001": 1}[ad]
    assert all((e.dxf.xscale, e.dxf.yscale) == (pytest.approx(1.0), pytest.approx(1.0)) for e in v)       # 60 × 40 açıklıkta 1:1
    kaynak = [e for e in doc.modelspace().query("INSERT") if e.dxf.name == "kaynak-on-pencere"]
    assert len(kaynak) == len(ac) - len(v) - sum(a.get("acilis") == "surgulu" for a in ac)              # sürgülü kendi bloğuyla (madde 9)
    assert not [e for e in kaynak if round(e.dxf.xscale * 77.101) == 60 and round(e.dxf.yscale * 116.017) == 40]
    blok = list(doc.blocks.get(ad_v))
    assert [e.closed for e in blok if e.dxftype() == "LWPOLYLINE"] == [True, True]                     # kasa ve tek kanat
    acilim = [e for e in blok if e.dxftype() == "LINE" and e.dxf.color == 1]
    tepe, alt = (en / 2, boy - k), [(k, k), (en - k, k)]
    hat = [LineString([a, tepe]) for a in alt]                                                         # alt köşelerden üst ortaya
    uclar = lambda e: [Point(e.dxf.start.x, e.dxf.start.y), Point(e.dxf.end.x, e.dxf.end.y)]
    assert len(acilim) == 12 and all(any(all(h.distance(q) < 1e-6 for q in uclar(e)) for h in hat) for e in acilim)
    assert sum(1 for e in blok if e.dxftype() == "LINE" and e.dxf.color == 7) == 4                     # köşe gönyeleri


def test_derz_yalniz_gorunen_duvardan():
    tk = G.kur(_ie("TK02"))
    on, arka, sol, sag = (CG.cephe(tk, t)["derz"] for t in CG.TARAFLAR)
    assert [381.5, 391.5, 507.0, 517.0] == [u for u in on if 380 < u < 520]           # nişin yan duvarları önden görünür
    assert arka == [10.0, 72.75, 198.25, 323.75, 386.5, 512.0, 637.5, 700.25, 825.75, 888.5]   # WC'lerin arasında yalnız H'nin derzi (512)
    assert [u for u in sol if 750 < u < 770] == [758.0] and [u for u in sag if 120 < u < 140] == [130.5]
    assert len([d for d in tk.duvarlar if d.tur == "dis" and not CG.gorunur(tk, d, G.disari_yon(tk, d))]) == 2     # nişin iki yan duvarı
    p = G.kur(_ie("P6001"))                                                            # köşe verandasının duvarları görünür kalır
    assert [CG.cephe(p, t)["derz"] for t in CG.TARAFLAR] == [
        [10.0, 135.5, 261.0, 386.5, 439.25, 444.25, 449.25, 574.75, 700.25, 763.0], [10.0, 135.5, 261.0, 386.5, 512.0, 637.5, 763.0],
        [5.0, 10.0, 130.5, 256.0, 381.5, 502.0, 507.0, 512.0, 632.5, 753.0, 758.0], [5.0, 10.0, 130.5, 256.0, 381.5, 507.0, 632.5, 753.0, 758.0]]


@pytest.mark.parametrize("ev, arka, sol, dusen", [
    ("AP01", [5.0, 10.0, 77.25, 140.0, 265.5, 328.25, 453.75, 579.25, 642.0, 767.5, 893.0, 1018.5, 1144.0, 1269.5, 1390.0, 1395.0],
     [10.0, 135.5, 261.0, 386.5, 512.0, 637.5, 763.0, 888.5, 990.0], ((762.5, 772.5), (695.25, 705.25))),
    ("AP13", [5.0, 10.0, 130.5, 256.0, 381.5, 507.0, 632.5, 753.0, 758.0],
     [10.0, 135.5, 261.0, 386.5, 512.0, 637.5, 700.25, 778.0], ((376.5, 386.5), (507.0, 517.0))),
    ("AP16", [5.0, 10.0, 130.5, 256.0, 381.5, 507.0, 632.5, 753.0, 758.0],
     [10.0, 72.75, 198.25, 261.0, 386.5, 512.0, 637.5, 763.0, 825.75, 908.5], ((376.5, 386.5), (695.25, 705.25))),
])
def test_derz_cepheye_degmeyen_dik_duvar_ap(ev, arka, sol, dusen):
    """Madde 7'nin kapsamı (geometri hakemi, 29 Ekim): kırma ve beşik + cumba AP evlerinde de cepheye değmeyen dik dış duvarın iki yüzü arka
    ve sol görünüşte derz vermez (D-31'den önce veriyordu); ön ve sağ aynı. Düşen çizgiler o yandan görülmeyen duvarındır."""
    p = G.kur(json.loads((KOK / "testler" / "cizim" / "evler" / f"{ev}.json").read_text(encoding="utf-8")))
    d = {t: CG.cephe(p, t)["derz"] for t in CG.TARAFLAR}
    assert (d["arka"], d["sol"]) == (arka, sol)
    assert not set(dusen[0]) & set(d["arka"]) and not set(dusen[1]) & set(d["sol"])


def _gorunus_cizici(ie):
    c = dxf_out.Cizici(G.kur(copy.deepcopy(ie)), Katalog())
    c.ciz_gorunusler(-600.0)
    return c


def _bolge(c, taraf):
    return [c.doc.entitydb[h] for h in c.bolgeler[taraf]]


def test_veranda_kolonu_dolgulu(tk02):
    ie, plan, _ = tk02
    c = _gorunus_cizici(ie)
    for taraf in CG.TARAFLAR:
        kolon = [p["u"] for p in c._veranda_gorunusu(taraf, CG.cati_cizgileri(plan, ie, taraf)) if p["tur"] == "kolon" and not p.get("acik")]
        dolgu = [e for e in _bolge(c, taraf) if e.dxftype() == "HATCH"]
        assert len(dolgu) == len(kolon) and all(e.dxf.color == dxf_out.VERANDA_KOLON_DOLGU == 9 for e in dolgu), taraf
    arka = sorted(round(min(v[0] for v in e.paths[0].vertices)) for e in _bolge(c, "arka") if e.dxftype() == "HATCH")
    ox = min(e.dxf.start.x for e in _bolge(c, "arka") if e.dxftype() == "LINE" and e.dxf.layer == "ON_DERZ") - 10.0   # ilk derz duvar köşesinden 10
    assert [round(u - ox, 1) for u in arka] == [632.5, 888.5]        # sağdaki kolon gövdenin köşesiyle aynı hizada, dolgusuyla görünür


def test_egim_yalniz_ana_catida_bir_kez(tk02):
    ie = tk02[0]
    yazi = lambda c, t: [e.dxf.text for e in _bolge(c, t) if e.dxftype() == "TEXT" and e.dxf.text.startswith("%")]
    c = _gorunus_cizici(ie)
    assert {t: yazi(c, t) for t in CG.TARAFLAR} == {"on": ["%33"], "arka": ["%33"], "sol": [], "sag": []}
    farkli = copy.deepcopy(ie)
    for v in farkli["verandalar"]:
        v["cati"]["egim_yuzde"] = 25
    c = _gorunus_cizici(farkli)                                       # veranda eğimi farklıysa kendi çatısında bir kez
    assert {t: sorted(yazi(c, t)) for t in ("on", "arka")} == {"on": ["%25", "%33"], "arka": ["%25", "%33"]}


def test_surgulu_pencere(cizim):
    ad, m, doc = cizim
    ad_s, en, boy, k = dxf_out.SURGULU_BLOK
    s = [e for e in doc.modelspace().query("INSERT") if e.dxf.name == ad_s]
    assert len(s) == {"TK02": 1, "P6001": 0}[ad]
    if not s:
        return
    assert (s[0].dxf.xscale, s[0].dxf.yscale) == (pytest.approx(1.0), pytest.approx(1.0))     # 120 × 180 açıklıkta 1:1
    blok = list(doc.blocks.get(ad_s))
    assert [e.closed for e in blok if e.dxftype() == "LWPOLYLINE"] == [True] * 6              # çift kasa, iki kanat (her biri çift)
    assert len([e for e in blok if e.dxftype() == "LINE" and e.dxf.color == 1]) == 4          # yön oku (gövde, başlangıç, iki uç)
    assert len([e for e in blok if e.dxftype() == "LINE" and e.dxf.color == 7]) == 2          # sabit kanatta cam işareti


def test_surgulu_is_emrinde_ve_yalniz_gorunuste(tk02):
    ie, plan, _ = tk02
    [a] = [a for t in CG.TARAFLAR for a in CG.cephe(plan, t)["acikliklar"] if a.get("acilis")]
    assert (a["acilis"], a["olcu"], a["z0"], a["z1"]) == ("surgulu", "120x180", 20.0, 200.0)   # ölçü, eşik ve üst kot pencereninki
    duz = copy.deepcopy(ie)
    for x in duz["acikliklar"]:
        x.pop("acilis", None)
    p2 = G.kur(duz)
    panolar = lambda p: [(pn.duvar.id, pn.a0, pn.a1, pn.acilim and (pn.acilim.tur, pn.acilim.olcu)) for pn in p.panolar]
    assert panolar(p2) == panolar(plan) and plan.W == p2.W and plan.H == p2.H                  # plan ve panolar aynı
    for kotu in ({"acilis": "kanatli"}, {"tur": "dis_kapi", "olcu": 90, "arasi": ["GİRİŞ", "HOL"], "acilis": "surgulu"}):
        ie2 = copy.deepcopy(ie)
        hedef = next(x for x in ie2["acikliklar"] if x.get("acilis")) if "tur" not in kotu else next(x for x in ie2["acikliklar"] if x["tur"] == "dis_kapi")
        hedef.update(kotu)
        with pytest.raises(G.IsEmriHatasi, match="acilis"):
            G.kur(ie2)


def test_a4_bayi_sayfasi(cizim):
    import pymupdf
    ad, m, doc = cizim
    pdf = Path(doc.filename).with_name(m["pdf"])
    with pymupdf.open(pdf) as d:
        assert [(round(s.rect.width / 72 * 25.4), round(s.rect.height / 72 * 25.4)) for s in d] == [(210, 297)]   # tek sayfa, dikey A4
        kutu = pymupdf.Rect()
        for x in d[0].get_drawings():
            kutu |= x["rect"]
    mm = 72 / 25.4
    k = dxf_out.A4_KENAR_MM - 0.5
    assert kutu.x0 >= k * mm and kutu.y0 >= k * mm and kutu.x1 <= (210 - k) * mm and kutu.y1 <= (297 - k) * mm   # kenar boşluğu içinde


def test_a4_planda_aks_zinciri_yok():
    c = dxf_out.Cizici(G.kur(_ie("TK02")), Katalog())
    c.ciz_plan(0.0, 0.0, "ANA", "KAT PLANI — AKSLI", "")
    zincir, plan = set(c.bolgeler["aks_zinciri"]), set(c.bolgeler["plan"])
    olcu = lambda e: round(e.get_measurement(), 2)
    assert zincir and not zincir & plan
    assert sorted(olcu(c.doc.entitydb[h]) for h in zincir) == [125.5] * 14         # TK-02: 7 + 7 aks aralığı
    assert all(c.doc.entitydb[h].dxftype() == "DIMENSION" for h in zincir)
    assert any(c.doc.entitydb[h].dxftype() == "DIMENSION" for h in plan)         # öteki ölçüler (dış ölçü, veranda, özel pano) planda kalır


def test_a4_yerlesim():
    # TK-02'nin bölge kutuları (cm, payla): görünüşler sayfa enine sığar, plan aradaki yerin ortasında, sığan en büyük ölçekte
    kut = {"plan": (1185, 1340), "antet": (1071, 92), "on": (1036, 713), "arka": (1066, 713), "sol": (1362, 713), "sag": (1362, 713)}
    y = dxf_out.a4_yerlesim(kut)
    W, H = dxf_out.A4_DIKEY_MM; k, g = dxf_out.A4_KENAR_MM, dxf_out.A4_ARA_MM
    sv = y["olcek"]["gorunus"]
    assert y["sol"][0] == pytest.approx(k) and y["sag"][0] + y["sag"][2] == pytest.approx(W - k)    # geniş satır kenardan kenara
    assert sv == pytest.approx((W - 2 * k - g) / (1362 * 2)) and sv <= dxf_out.A4_GORUNUS_EN_BUYUK
    for t in ("on", "arka", "sol", "sag"):
        assert (y[t][2], y[t][3]) == (pytest.approx(kut[t][0] * sv), pytest.approx(kut[t][1] * sv))  # dördü aynı ölçekte
    assert y["antet"][1] == pytest.approx(k) and y["antet"][1] + y["antet"][3] + g == pytest.approx(y["on"][1])
    assert y["on"][0] + y["on"][2] <= y["arka"][0] and y["sol"][0] + y["sol"][2] <= y["sag"][0]       # soldan sağa ön, arka; sol, sağ
    assert y["sol"][1] + y["sol"][3] == pytest.approx(H - k)
    x, yy, w, h = y["plan"]
    ust, alt = y["on"][1] + y["on"][3] + g, y["sol"][1] - g
    assert x + w / 2 == pytest.approx(W / 2) and yy + h / 2 == pytest.approx((ust + alt) / 2)        # aradaki yerin ortasında
    assert h == pytest.approx(alt - ust) or w == pytest.approx(W - 2 * k)                             # sığan en büyük
    assert all(k - 1e-9 <= r[0] and r[0] + r[2] <= W - k + 1e-9 and k - 1e-9 <= r[1] and r[1] + r[3] <= H - k + 1e-9
               for a, r in y.items() if a != "olcek")


def test_a4_bolgesi_eksikse_pdf_yok(tk02):
    """Kat planı bölgesi yoksa ya da bir bölgeye yer kalmazsa A4 sayfası sessizce eksik basılmaz (geometri hakemi, 29 Ekim; K16)."""
    from ezdxf.addons.drawing import config
    ie, _, _ = tk02
    c = _gorunus_cizici(ie)                                             # yalnız dört görünüş: plan bölgesi yok
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
    with pytest.raises(RuntimeError, match="kat planı bölgesi yok"):
        dxf_out.a4_bayi_sayfasi(c.doc, c.bolgeler, cfg)


def test_kot_yalniz_on_ve_sag_gorunuste(tk02):
    """Madde 14 (Lokman 13:14): düşey kot ölçüleri (duvar, tepe, pencere eşiği ve lentosu) yalnız ön ve sağ görünüşte; yatay ölçüler dördünde."""
    ie, _, _ = tk02
    c = _gorunus_cizici(ie)
    kot = {t: [e for e in _bolge(c, t) if e.dxftype() == "DIMENSION" and abs(e.dxf.get("angle", 0) - 90) < 1e-6] for t in CG.TARAFLAR}
    yatay = {t: [e for e in _bolge(c, t) if e.dxftype() == "DIMENSION" and abs(e.dxf.get("angle", 0)) < 1e-6] for t in CG.TARAFLAR}
    assert {t: len(v) for t, v in kot.items()} == {"on": 4, "arka": 0, "sol": 0, "sag": 4}
    assert all(len(v) == 2 for v in yatay.values())
    assert dxf_out.KOT_GORUNUSLERI == ("on", "sag")


def test_antette_kime_ait_ve_m2(tmp_path):
    """Madde 14 (Lokman 13:13): antette kime ait (bayi / müşteri; boşu yazılmaz) ve m² (brüt: nişsiz gövdenin dış yüzü, net: kapalı odalar)."""
    ie = _ie("TK02")
    assert dxf_out.alan_yazisi(G.kur(copy.deepcopy(ie))) == "78,38 m² brüt · 71,45 m² net"
    ie["talep"]["bayi"]["ad"], ie["talep"]["musteri_adi"] = "", "Müşteri A"
    m = dxf_out.uret(ie, tmp_path)
    doc = ezdxf.readfile(tmp_path / m["dxf"])
    antet = [e.dxf.text for e in doc.modelspace().query("TEXT") if e.dxf.text.startswith("PORTMAN |")]
    assert antet == ["PORTMAN | Müşteri A | 78,38 m² brüt · 71,45 m² net | İş Emri PM-TK02-80M2 r03"]


ODA_M2_EVLER = {"TK02": VERI / "TK02.json", "TK01_r06": KOK / "araclar" / "paket" / "girdi" / "TK01_r06.json", "PK01": VERI / "PK01.json",
                "P6001": KOK / "is_emri" / "P6001_2plus1_6x6.json", "YAN_VERANDALI": KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json",
                "ALTIN": KOK / "is_emri" / "ALTIN_2plus1_6x8.json"}


def _kutu(s, x, y, h, rot):
    w = dxf_out.Cizici.yazi_eni(s, h) / 2
    return (x - h / 2, y - w, x + h / 2, y + w) if abs(rot % 180 - 90) < 1e-6 else (x - w, y - h / 2, x + w, y + h / 2)


def _biner(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.parametrize("rol", ["ANA", "KOPYA"])
@pytest.mark.parametrize("ev", sorted(ODA_M2_EVLER))
def test_her_bolmenin_adinin_altinda_net_m2(ev, rol):
    """Madde 15 (Lokman 13:21): kat planında (A4'teki akslı plan) ve net alan planında her bölmenin (oda, hol, giriş, veranda) adının
    altında net m²'si; 90°'lik yazıda okuma yönünde altta (+x). Ad ve m² mahalin içinde; A4 planında ölçü çizgisine, ölçü yazısına ve
    öteki yazılara (pencere ölçü yazısı dahil) binmez (aks ölçü zinciri A4'te yok, sayılmaz); net alan planında yazılara, pencere yazısına ve özel
    pano ölçülerine binmez. Nişin "aks modülü" yazısı A4 planında yok, net alan planında var."""
    ie = json.loads(ODA_M2_EVLER[ev].read_text(encoding="utf-8"))
    plan = G.kur(copy.deepcopy(ie))
    c = dxf_out.Cizici(plan, Katalog())
    c.ciz_plan(0.0, 0.0, rol, "KAT PLANI", "")
    varlik = [c.doc.entitydb[h] for h in c.bolgeler["plan"]] if rol == "ANA" else list(c.msp)
    yazilar = [e for e in varlik if e.dxftype() == "TEXT"]
    adlar = set()
    for ad, m in plan.mahaller.items():
        a = [t for t in yazilar if t.dxf.text == ad]
        alan = f"{m.alan_m2:.2f}".replace(".", ",") + " m²"
        b = [t for t in yazilar if t.dxf.text == alan and t.dxf.rotation == a[0].dxf.rotation] if len(a) == 1 else []
        assert len(a) == 1 and b, (ev, rol, ad, alan)
        (ax, ay), rot = (a[0].dxf.align_point[0], a[0].dxf.align_point[1]), a[0].dxf.rotation
        altta = [t for t in b if (abs(t.dxf.align_point[0] - ax - 32) < 1e-6 and abs(t.dxf.align_point[1] - ay) < 1e-6 if rot
                                  else abs(t.dxf.align_point[0] - ax) < 1e-6 and abs(ay - t.dxf.align_point[1] - 32) < 1e-6)]
        assert len(altta) == 1, (ev, rol, ad)
        for t in (a[0], altta[0]):
            k = _kutu(t.dxf.text, t.dxf.align_point[0], t.dxf.align_point[1], t.dxf.height, t.dxf.rotation)
            assert m.poly.contains(Point(k[0], k[1])) and m.poly.contains(Point(k[2], k[3])), (ev, rol, ad, t.dxf.text)
            adlar.add(t.dxf.handle)
    nis = [t for t in yazilar if t.dxf.text.endswith("aks modülü")]
    acik_nis = [ad for ad, mm in plan.mahaller.items() if mm.acik and mm.cells]
    assert len(nis) == (0 if rol == "ANA" else len(acik_nis)), (ev, rol)
    etiket = [_kutu(t.dxf.text, t.dxf.align_point[0], t.dxf.align_point[1], t.dxf.height, t.dxf.rotation) for t in yazilar if t.dxf.handle in adlar]
    engel = [_kutu(t.dxf.text, t.dxf.align_point[0], t.dxf.align_point[1], t.dxf.height, t.dxf.rotation) for t in yazilar
             if t.dxf.handle not in adlar and t not in nis]
    def pencere_yazilari(e):                             # pano bloğu → pencere bloğu → kaynak pencere bloğu → yazı (hakem, 29 Ekim)
        for g in e.virtual_entities():
            if g.dxftype() == "INSERT" and (g.dxf.layer == "PENCERE" or e.dxf.layer == "PENCERE"):
                yield from pencere_yazilari(g)
            elif g.dxftype() == "TEXT" and e.dxf.layer == "PENCERE":
                yield g
    pencere = [y for e in varlik if e.dxftype() == "INSERT" for y in pencere_yazilari(e)]
    assert pencere or ev == "ALTIN", ev
    pencere = [(lambda bb: (bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y))(ezdxf.bbox.extents([y])) for y in pencere]
    engel.extend(pencere)
    nis_k = [_kutu(t.dxf.text, t.dxf.align_point[0], t.dxf.align_point[1], t.dxf.height, t.dxf.rotation) for t in nis]
    assert not [(k, o) for k in nis_k for o in pencere if _biner(k, o)], ev     # Yan 6×8,5'te "1 x 4 aks modülü" mutfak penceresinin yazısına biniyordu
    if rol != "ANA":                                     # net alan planı DXF'te: aks zinciri ayrılamadığından yalnız yazılara ve özel pano ölçülerine karşı
        varlik = [e for e in varlik if e.dxftype() == "DIMENSION" and e.dxf.layer == "OZEL_PANEL_OLCU_CM"]
    for e in varlik:
        if e.dxftype() != "DIMENSION": continue
        for g in e.get_geometry_block():
            if g.dxftype() == "LINE":
                x0, y0, x1, y1 = g.dxf.start[0], g.dxf.start[1], g.dxf.end[0], g.dxf.end[1]
                engel.append((min(x0, x1) - 1, min(y0, y1) - 1, max(x0, x1) + 1, max(y0, y1) + 1))
            elif g.dxftype() == "MTEXT":
                engel.append(_kutu(g.text, g.dxf.insert[0], g.dxf.insert[1], g.dxf.char_height, g.dxf.get("rotation", 0.0)))
    binen = [(k, o) for k in etiket for o in engel if _biner(k, o)]
    assert not binen, (ev, binen[:3])
