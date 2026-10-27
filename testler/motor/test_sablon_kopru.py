"""BK-14 · Pano Motor'unun planı canlıdaki Örnek Şablon paftasıyla (`motor/sablon_kopru.py`).

Lokman, 27 Ekim 2026 16:43: TK-01 r03'ün görünüşleri sıfırdan çizilmişti, eğim (%27,5) ve pencereler hatalıydı. Görünüş ve pafta biçimi canlıdaki
onaylı çizimden gelir (çizim seti, Lokman 7 Ekim; Örnek Şablon, 6 Ekim); geometri pano Motor'undan, değerler İş Emri'nden (duvar 250, açıklık
üst kotu 200, eğim kitaptan %33). Burada köprünün yazdığı Yapı Tanımı ve paftanın ölçü zincirleri TK-01'de sabit (bayi çizimiyle aynı
zincirler). Genel motorun çıktıları değişmez: zincir sarmalayıcısı çizimden sonra geri alınır. Bu bir çizim kilididir, kaynağa uygunluk kanıtı
değildir.
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
from motor import sablon_kopru as K  # noqa: E402

TK01 = KOK / "testler" / "motor" / "veri" / "TK01.json"


def _ie(egim: float = 33.0) -> dict:
    """TK-01 r03 (test verisi) eğim kitaptaki %33 ile (r04): ana çatı ve iki veranda çatısı."""
    ie = json.loads(TK01.read_text(encoding="utf-8"))
    ie["cati"]["egim_yuzde"] = egim
    for v in ie["verandalar"]:
        v["cati"]["egim_yuzde"] = egim
    return ie


@pytest.fixture(scope="module")
def tanim():
    return K.tanim(_ie())


@pytest.fixture(scope="module")
def pafta(tmp_path_factory):
    hedef = tmp_path_factory.mktemp("tk01_sablon")
    return hedef, K.pafta(_ie(), hedef, bilgi={"tarih": "27.10.2026"})


def test_degerler_is_emrinden(tanim):
    assert tanim["kat_yuksekligi"] == 250.0 and tanim["lento"] == 50.0
    assert {d["egim"] for d in tanim["cati"]["duzlemler"]} == {0.33}
    t2 = K.tanim(_ie(30.0))
    assert {d["egim"] for d in t2["cati"]["duzlemler"]} == {0.30}


def test_aciklik_sayilari_ve_ust_kot(tanim):
    say = collections.Counter((a["tur"], a.get("etiket")) for a in tanim["acikliklar"])
    assert say == {("pencere", "120/180"): 4, ("pencere", "120/120"): 2, ("pencere", "60/40"): 2, ("ic_kapi", None): 8, ("dis_kapi", None): 1}
    assert {a["alt"] + a["yuk"] for a in tanim["acikliklar"]} == {200.0}            # BK-13: pencere ve kapı üst kotu 200, eşik 200 − boy
    assert sorted(a["alt"] for a in tanim["acikliklar"] if a["tur"] == "pencere") == [20.0] * 4 + [80.0] * 2 + [160.0] * 2


def test_cati_ve_verandalar(tanim):
    c = tanim["cati"]
    assert [d["ad"] for d in c["duzlemler"]] == ["sol", "sağ", "ön veranda sol", "ön veranda sağ", "arka veranda sol", "arka veranda sağ"]
    assert [k["ad"] for k in c["kalkanlar"]] == ["ön kalkan", "arka kalkan", "ön veranda alnı", "arka veranda alnı"]
    assert collections.Counter(d["sinif"] for d in tanim["duvarlar"]) == {"ic": 10, "dis": 4, "kolon": 4}
    assert len(tanim["kirisler"]) == 6
    # alınlar duvarlar (verandada kolonların dış yüzleri) arasında, saçak payı alına girmez (genel motordaki gibi; geometri hakemi)
    assert [k["aralik"] for k in c["kalkanlar"]] == [[0.0, 898.0], [0.0, 898.0], [256.0, 642.0], [0.0, 261.0]]
    assert c["ust_pay"] == 14.0                                                 # ifc_uret: düzlemin 10 cm üstünde 4 cm sac
    ver = {m["ad"]: m["poligon"] for m in tanim["mahaller"] if m["sinif"] == "veranda"}
    assert ver == {"ÖN VERANDA": [[256.0, -181.0], [642.0, -181.0], [642.0, 0.0], [256.0, 0.0]],
                   "ARKA VERANDA": [[0.0, 888.0], [261.0, 888.0], [261.0, 1018.0], [0.0, 1018.0]]}


def test_pafta_iki_sayfa_ve_zincirler(pafta):
    import pymupdf
    hedef, o = pafta
    assert o["olcek_1e"] == 126 and o["dis_olcu_cm"] == [898.0, 1199.0] and o["oturum_m2"] == pytest.approx(90.12)
    # bayi çizimiyle aynı noktalar; şablonun kuralı (parçalar tam sayı, toplamları dış ölçü) üç parçada 1 cm fark verir: arka 323 ↔ 324 (aks
    # 574,75), sol ve sağ 381 ↔ 382 (bayinin zincirleri 899 ve 1200 tutuyor). Önde verandanın köşeleri ve hol duvarları (bayi 392 | 116 | 392)
    assert o["zincirler_cm"] == {"arka": [261, 126, 188, 323], "on": [256, 131, 125, 130, 256], "sol": [181, 507, 381, 130],
                                 "sag": [181, 256, 251, 381, 130]}
    assert [n for n in o["kontrol_notlari"] if n.get("kaynak") != "motor"] == []    # kolon halkasının 10 cm'lik kırıntısı yok
    assert [n["not"] for n in o["kontrol_notlari"] if n.get("kaynak") == "motor"] == K.G.kur(_ie()).uyarilar   # K16: Motor'un uyarısı düşmez
    assert o["teslim"] is True and o["dogrulama"]["passed"] is True and o["tepe_cm"] == pytest.approx(432.07, abs=0.05)
    assert o["ozellikler"]["Çatı Eğimi"] == "%33" and o["ozellikler"]["Çatı Şekli"] == "Beşik"
    with pymupdf.open(hedef / "TK01_pafta.pdf") as d:
        assert d.page_count == 2
        s1 = " ".join(w[4] for w in d[0].get_text("words")); s2 = " ".join(w[4] for w in d[1].get_text("words"))
    for s in ("SOL YAN GÖRÜNÜŞ", "ÖN GÖRÜNÜŞ", "ÖN VERANDA", "ARKA VERANDA", "YATAK ODASI 1", "898", "1199", "120/180"):
        assert s in s1, s
    for s in ("ÇATI PLANI", "ARKA GÖRÜNÜŞ", "SOL GÖRÜNÜŞ", "SAĞ GÖRÜNÜŞ", "%33,0"):
        assert s in s2, s
    assert json.loads((hedef / "TK01_yapi_tanimi.json").read_text(encoding="utf-8"))["kod"] == "TK-01"


def test_l_oda_yazisi_kolda(tanim, pafta):
    # yatak odası 1 L biçimli (E. banyonun altındaki parça); yazı geniş kolda, kapı yayının dışında (ilk çizimde iki duvara biniyordu)
    from shapely.geometry import Point
    from motor.genel import yapi
    _, o = pafta
    net = yapi.kur(tanim)["bolgeler"]["YATAK ODASI 1"]["net"]
    assert net.envelope.area - net.area > 1e4
    assert o["mahal_etiket_cm"]["YATAK ODASI 1"] == [157.5, 579.5] and net.contains(Point(157.5, 579.5))


def test_yazi_cakismasi(tmp_path):
    """Paftanın iki sayfasında yazı çakışması yok. Bilinen tek bulgu: 1 m²'lik antrede yazı kapı yayını keser (oda yazıdan dar; şablon yazı
    boyunu odanın eninden seçer)."""
    import matplotlib.figure  # noqa: F401
    from matplotlib.backends.backend_pdf import PdfPages
    from motor.genel import yazi_cakisma as YC
    r = []
    asil = PdfPages.savefig

    def kaydet(self, figure=None, **k):
        r.append(YC.denetle(figure, f"sayfa_{len(r) + 1}"))
        return asil(self, figure, **k)

    PdfPages.savefig = kaydet
    try:
        K.pafta(_ie(), tmp_path)
    finally:
        PdfPages.savefig = asil
    son = r[-2:]                                                              # ikinci çizim (oda yazıları yerinde)
    assert [x["cakisan"] for x in son] == [[], []] and [x["cizgi_kapatan"] for x in son] == [[], []]
    assert [x["sayfa_disi"] for x in son] == [[], []]
    assert {a for a, _, _ in son[0]["yay_kapatan"]} <= {"ANTRE", "1 m²"} and son[1]["yay_kapatan"] == []


def test_zincir_sarmalayici_geri_alinir(pafta):
    from motor.genel import ciz_genel
    asil = ciz_genel.zincirler
    with K._zincir_siluetten():
        assert ciz_genel.zincirler is not asil
    assert ciz_genel.zincirler is asil


def test_dogrulanmayan_plan_hatali_adla(tmp_path):
    # K23: Motor'un doğrulaması geçmezse teslim adı yok
    o = K.pafta(_ie(), tmp_path, dogrulama={"passed": False, "errors": ["deneme"]})
    assert o["teslim"] is False and o["dosyalar"] == ["TK01_pafta.HATALI.pdf", "TK01_pafta_sablon.HATALI.png"]
    assert not (tmp_path / "TK01_pafta.pdf").exists() and (tmp_path / "TK01_pafta.HATALI.pdf").exists()


def test_ana_catiyi_asan_veranda_catisi_hata():
    # K16: ön veranda %80'de ana çatının (%33) yüzünü 20 cm aşar (Motor uyarır); kırpılıp "saçak altında" sayılmaz, köprü durur
    ie = _ie()
    ie["verandalar"][0]["cati"]["egim_yuzde"] = 80
    with pytest.raises(K.KopruHatasi, match="aşıyor"):
        K.tanim(ie)


def test_besik_disi_cati_hata():
    ie = _ie()
    ie["cati"]["tip"] = "kirma"
    with pytest.raises(K.KopruHatasi):
        K.tanim(copy.deepcopy(ie))


def test_izgara_ici_veranda_pk01(tmp_path):
    # İE-17: PK-01'in verandası ızgaranın içinde (ana çatının altında). Mahal poligonla, kirişler açık kenarlarda (kolona kadar, dışarıdan
    # içeri 10 cm, duvar üstünden 10 cm aşağı), kolon Motor'un dikmesi; pafta iki sayfa ve teslim adıyla.
    ie = json.loads((KOK / "testler" / "motor" / "veri" / "PK01.json").read_text(encoding="utf-8"))
    t = K.tanim(copy.deepcopy(ie))
    v = [m for m in t["mahaller"] if m["sinif"] == "veranda"]
    assert [(m["ad"], m["etiket_m2"]) for m in v] == [("VERANDA", 6.68)]
    assert [(k["kutu"], k["alt"], k["ust"]) for k in t["kirisler"]] == [([261.0, 0.0, 590.0, 10.0], 240.0, 250.0),
                                                                        ([590.0, 5.0, 600.0, 205.0], 240.0, 250.0)]
    assert [d["kutu"] for d in t["duvarlar"] if d["sinif"] == "kolon"] == [[590.0, 0.0, 600.0, 10.0]]
    import pymupdf
    o = K.pafta(ie, tmp_path, bilgi={"tarih": "27.10.2026"})
    assert o["teslim"] is True
    with pymupdf.open(tmp_path / "PK01_pafta.pdf") as d:
        assert d.page_count == 2
        s1 = " ".join(w[4] for w in d[0].get_text("words")); s2 = " ".join(w[4] for w in d[1].get_text("words"))
    assert "VERANDA" in s1 and "ÇATI PLANI" in s2
