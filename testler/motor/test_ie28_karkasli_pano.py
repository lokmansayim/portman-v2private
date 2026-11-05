"""D-46 (İE-28; Lokman, 4 Kasım 2026 04:35, kart "Paftadan, ev ev") · Karkaslı kaplama duvar panosu ve odaya ortalı geniş pencere (PC-33).

Paftadaki tek parça karkaslı kaplama duvar panosunun yeri İş Emri'ne paftadan yazılır (`yapi.dizilim.karkasli_panolar`): dış duvar (yön ve
eksen, Motor çerçevesinde) ve aralık; aralığa düşen panolar tek panoya birleşir, içindeki pencere ve dış kapı yerinde (ya da paftadaki
ortasında, `aciklik_ortasi_cm`), içinde derz ve H yok. Panodan geniş pencereyi odanın ortasına koyan anahtar `genis_pencere: oda_ortasi`
(AP-11: 62,75 + 251 + 62,75). Anahtarı yazılmamış İş Emri'nde hiçbir şey değişmez (TK-01 r07, TK-02, P6001; referans ve M-02 testleri ayrıca).
Çizim, liste, IFC ve montaj rehberi aynı panoyu sayar.
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

VERI = KOK / "testler" / "motor" / "veri"
KOR = KOK / "testler" / "kor" / "projeler"
ANAHTARSIZ = (VERI / "TK01_r07.json", VERI / "TK02.json", KOK / "is_emri" / "P6001_2plus1_6x6.json")


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _ie(kod: str) -> dict:
    return _oku(KOR / kod / "is_emri.json")


def _karkaslilar(plan) -> list:
    """(duvar id, a0, a1, [(tür, ölçü, ortası)]) — karkaslı panolar, duvar sırasıyla."""
    return [(d.id, round(p.a0, 2), round(p.a1, 2), [(a.tur, a.olcu, round(sum(p.bosluk(a)) / 2, 2)) for a in p.aciklar])
            for d in plan.duvarlar for p in d.panolar if p.karkasli]


def _duvar(plan, i):
    return next(d for d in plan.duvarlar if d.id == i)


def test_sabitler():
    assert G.KARKAS_ARTIK_CM == 20.0 and G.KARKAS_ACIKLIK_TURLERI == ("pencere", "dis_kapi")
    assert {"karkasli_panolar", "genis_pencere"} <= G.DIZILIM_ANAHTARLARI


@pytest.mark.parametrize("yol", ANAHTARSIZ, ids=[p.stem for p in ANAHTARSIZ])
def test_anahtarsiz_is_emrinde_karkasli_pano_yok(yol):
    ie = _oku(yol)
    assert "karkasli_panolar" not in ie["yapi"].get("dizilim", {})
    plan = G.kur(ie)
    for p in plan.panolar:
        assert not p.karkasli and not p.ek_acilimlar
        assert p.aciklar == ([p.acilim] if p.acilim else []) and p.gaps() == ([p.gap()] if p.acilim else [])


def test_ap14_dort_karkasli_pano():
    """AP-14 paftası: yatak odası 1 arka duvarı tek 251 (120/120), yatak odası 2 arka duvarı 236,67 (120/120), salon ön duvarı 62,75 + 188,25
    (120/180, paftadaki ortası 158,9) + 56,5, veranda duvarı kapılı pano + 242,75 (180/200, ortası 559,5) + 62,92."""
    plan = G.kur(_ie("AP14"))
    assert _karkaslilar(plan) == [
        (0, 5.0, 256.0, [("pencere", "120x120", 130.5)]),
        (0, 507.0, 743.67, [("pencere", "120x120", 626.25)]),
        (3, 438.0, 680.75, [("pencere", "180x200", 559.5)]),
        (4, 67.75, 256.0, [("pencere", "120x180", 158.9)]),
    ]
    d3, d4 = _duvar(plan, 3), _duvar(plan, 4)
    assert [(round(p.a0, 2), round(p.a1, 2)) for p in d3.panolar] == [(312.5, 438.0), (438.0, 680.75), (680.75, 743.67)]   # 62,92 tek parça
    assert [(round(p.a0, 2), round(p.a1, 2)) for p in d4.panolar] == [(5.0, 67.75), (67.75, 256.0), (256.0, 312.5)]


def test_ap26_kapi_ve_pencere_tek_panoda():
    """AP-26: arka duvarda kapı + 200/210 tek 428,58'lik panoda (köşeye kadar); ön duvarda 280/210 tek 491,33'lük panoda. Arka panonun
    ortasından iç duvar T ile geçer (paftadaki gibi): o T listede pano ekinde değil, çektirme U'su (D-45 madde 13)."""
    plan = G.kur(_ie("AP26"))
    assert _karkaslilar(plan) == [
        (0, 256.0, 684.58, [("dis_kapi", "90", 318.75), ("pencere", "200x210", 525.3)]),
        (5, 193.25, 684.58, [("pencere", "280x210", 449.9)]),
    ]
    p = next(p for p in _duvar(plan, 0).panolar if p.karkasli)
    assert len(p.rects()) == 3 and len(p.gaps()) == 2                    # iki açıklığın arası ve iki yanı dolu
    assert abs(sum(r[2] - r[0] for r in p.rects()) + sum(g[2] - g[0] for g in p.gaps()) - p.boy) < 1e-6


def test_ap18_iki_pencere_tek_panoda():
    plan = G.kur(_ie("AP18"))
    assert _karkaslilar(plan) == [
        (5, 5.0, 381.5, [("pencere", "120x180", 67.75), ("pencere", "120x180", 318.75)]),
        (7, 10.0, 261.0, [("pencere", "180x180", 135.5)]),
    ]


def test_ap25_arka_sol_y_duvari():
    """y duvarında satırın aralığı Motor çerçevesinde (arkadan): [507, 695,25] → gerçek 333,75–522; paftadaki ortası 606,15 → 422,85."""
    plan = G.kur(_ie("AP25"))
    assert _karkaslilar(plan) == [(8, 333.75, 522.0, [("pencere", "120x120", 422.85)])]


def test_ap11_oda_ortasi_genis_pencere():
    """`genis_pencere: oda_ortasi` (AP-11): 180/200'ün 251'lik panosu odanın duvar parçasına ortalı, iki yanı 62,75; komşu kuralıyla (BK-13)
    pencereli pano 5–256'daydı. Karkaslı satır aynı panoyu karkaslı kaplama panosu yapar."""
    ie = _ie("AP11")
    plan = G.kur(ie)
    sira = lambda pl: [(round(p.a0, 2), round(p.a1, 2), p.karkasli, [a.olcu for a in p.aciklar]) for p in _duvar(pl, 3).panolar]
    assert sira(plan)[:3] == [(5.0, 67.75, False, []), (67.75, 318.75, True, ["180x200"]), (318.75, 381.5, False, [])]
    ie["yapi"]["dizilim"].pop("karkasli_panolar")
    assert sira(G.kur(copy.deepcopy(ie)))[:3] == [(5.0, 67.75, False, []), (67.75, 318.75, False, ["180x200"]), (318.75, 381.5, False, [])]
    ie["yapi"]["dizilim"].pop("genis_pencere")
    assert sira(G.kur(ie))[:2] == [(5.0, 256.0, False, ["180x200"]), (256.0, 381.5, False, [])]
    assert (_duvar(plan, 7).panolar[0].karkasli, round(_duvar(plan, 7).panolar[0].boy, 2)) == (True, 194.0)


def test_oda_ortasi_parcada_kapi_varsa_hata():
    ie = _ie("AP14")
    ie["yapi"]["dizilim"].pop("karkasli_panolar")
    ie["yapi"]["dizilim"]["genis_pencere"] = "oda_ortasi"
    with pytest.raises(G.IsEmriHatasi, match="oda_ortasi: 2 panoluk pencereli pano odanın duvar parçasına ortalanamıyor"):
        G.kur(ie)
    ie["yapi"]["dizilim"]["genis_pencere"] = "orta"
    with pytest.raises(G.IsEmriHatasi, match="komsu \\| yarim_pano \\| oda_ortasi"):
        G.kur(ie)


def _tk01(satirlar) -> dict:
    ie = _oku(VERI / "TK01_r07.json")
    ie["yapi"]["dizilim"]["karkasli_panolar"] = satirlar
    return ie


# TK-01 r07 (arka-sol, H 888,5): Motor eksen 5 → ön duvar (gerçek y 883,5; H 261, 386,5 ve 574,75'te; 120/180 72,75–198,25 panosunda);
# Motor eksen 883,5 → arka sol duvar (gerçek y 5; panolar 10–135,5, 135,5–261 (120/180), 261–381,5)
@pytest.mark.parametrize("satirlar, mesaj", [
    ([], "boş olmayan bir liste"),
    ({"yon": "x"}, "boş olmayan bir liste"),
    ([{"yon": "z", "eksen_cm": 5, "aralik_cm": [10, 200]}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [10, 200], "renk": "mavi"}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": "5", "aralik_cm": [10, 200]}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [10]}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [10, True]}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [10, 200], "aciklik_ortasi_cm": "100"}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [10, 200], "aciklik_ortasi_cm": []}], "yon \\(x \\| y\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [100, 100.5]}], "aralık boş"),
    ([{"yon": "x", "eksen_cm": 400, "aralik_cm": [10, 200]}], "aralığı içine alan dış duvar yok"),
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [5, 381.5]}], "aralığı içine alan dış duvar yok"),       # duvarın panolarından taşıyor
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [200, 300]}], "üçlü H birleşimi var \\(261, 883.5\\)"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [72.75, 196]}], "pencere 120x180 .* karkaslı panoya girmiyor"),
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [15, 381.5]}], "başında kalan 5 cm'lik parça komşu panoyla birleşemiyor"),
    ([{"yon": "x", "eksen_cm": 5, "aralik_cm": [72.75, 250]}], "sonunda kalan 11 cm'lik parça komşu panoyla birleşemiyor"),   # komşuda 60/40
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 261]}, {"yon": "x", "eksen_cm": 883.5, "aralik_cm": [135.5, 381.5]}],
     "başka bir karkaslı panoyla çakışıyor"),
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 261], "aciklik_ortasi_cm": [100, 200]}], "2 değer, aralıkta 1 açıklık"),
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 261], "aciklik_ortasi_cm": [70]}], "ortası 70 aralığın ucuna pano payından yakın"),
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [261, 381.5]}], "aralıkta pencere ya da dış kapı yok"),                # D-46: açıklıksız olmaz
    ([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [136, 381.5]}], "başında kalan 0.5 cm'lik parça komşu panoyla birleşemiyor"),  # 10–136 > 125,5
])
def test_satir_hatalari(satirlar, mesaj):
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(_tk01(satirlar))


def test_kisa_artik_komsuyla_tek_parca():
    """Aralığın dışında kalan 20 cm'den kısa parça açıklıksız komşu panoyla tek parça (birleşen pano en çok 125,5; AP-14 verandası 62,92);
    20 cm ve üstü kendi panosu. 10–136 (126 cm) olacaksa açık hata (`test_satir_hatalari`)."""
    sira = lambda ie: [(round(p.a0, 2), round(p.a1, 2), p.karkasli) for p in _duvar(G.kur(ie), 6).panolar]
    assert sira(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 260.5]}])) == \
        [(10.0, 260.5, True), (260.5, 381.5, False)]                                    # 0,5 cm'lik artık 261–381,5 ile: 121
    assert sira(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [131, 381.5]}])) == [(10.0, 131.0, False), (131.0, 381.5, True)]
    assert sira(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [30, 381.5]}])) == [(10.0, 30.0, False), (30.0, 381.5, True)]
    assert sira(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 261]}])) == [(10.0, 261.0, True), (261.0, 381.5, False)]


def test_ortasi_yazilmayan_aciklik_yerinde():
    """`aciklik_ortasi_cm` yoksa (ya da değeri null) açıklık Motor'un koyduğu yerde kalır; yazılırsa paftadaki ortasına gider."""
    yer = lambda ie: [(a.olcu, round(sum(p.bosluk(a)) / 2, 2)) for p in _duvar(G.kur(ie), 6).panolar if p.karkasli for a in p.aciklar]
    assert yer(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 381.5]}])) == [("120x180", 198.25)]
    assert yer(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 381.5], "aciklik_ortasi_cm": [None]}])) == [("120x180", 198.25)]
    assert yer(_tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 381.5], "aciklik_ortasi_cm": [250]}])) == [("120x180", 250.0)]


def _liste(ie):
    from motor import prefabrik_liste as PL
    return PL.liste(PL.model_motor(copy.deepcopy(ie)))["satirlar"]


def _adet(L, bas):
    return sum(s["adet"] for s in L if s["kalem"].startswith(bas))


def test_liste_satiri_ve_ic_pencere():
    """Listede "Karkaslı kaplama duvar panosu" (kural kitabında `karkasli_kaplama_panosu`), 100 × gerçek boy × H (gerçek listeler gibi, AP-11
    2510; yapıştırma panonun sipariş boyu kuralı değil); içindeki 120'lik pencereye
    üst ve alt panel, özel pencere karkası yok; panodan geniş pencerenin karkaslı özel pencere panosu da yok (pano onun yerine). Pencere ve kapı
    kalemleri aynı (AP-14: dört karkaslı pano, gerçek listede de dört)."""
    from motor import prefabrik_liste as PL
    kk = PL.kurallari_oku()["prefabrik"]["kurallar"]["karkasli_kaplama_panosu"]
    assert kk["durum"] == "lokman" and "D-46" in kk["kaynak"] and kk["deger"]["kalem"] == "Karkaslı kaplama duvar panosu"
    ie = _ie("AP14")
    L = _liste(ie)
    k = sorted((s["olcu"], s["adet"], s["dayanak"]) for s in L if s["kalem"] == "Karkaslı kaplama duvar panosu")
    assert k == [("100 × 1882,5 × 2500", 1, "İş Emri (D-46)"), ("100 × 2366,7 × 2500", 1, "İş Emri (D-46)"),     # gerçek boy, sipariş boyu değil
                 ("100 × 2427,5 × 2500", 1, "İş Emri (D-46)"), ("100 × 2510 × 2500", 1, "İş Emri (D-46)")]
    ie0 = copy.deepcopy(ie)
    ie0["yapi"]["dizilim"].pop("karkasli_panolar")
    L0 = _liste(ie0)
    assert _adet(L0, "Pencere üst panel") - _adet(L, "Pencere üst panel") == 3          # 120/120 × 2 ve 120/180 karkaslı panoda
    assert _adet(L0, "Pencere alt panel") - _adet(L, "Pencere alt panel") == 3
    assert _adet(L0, "Özel pencere karkası") - _adet(L, "Özel pencere karkası") == 3
    assert _adet(L0, "Karkaslı özel pencere panosu (180/200)") == 1 and _adet(L, "Karkaslı özel pencere panosu") == 0
    for bas in ("PVC pencere", "Pencere", "Çelik kapı", "Kapı"):
        pen = lambda X: sorted((s["kalem"], s["olcu"], s["adet"]) for s in X if s["grup"] == "1003" and s["kalem"].startswith(bas))
        assert pen(L) == pen(L0), bas


def test_liste_karkasli_kural_kitabi_denetlenir():
    from motor import prefabrik_liste as PL
    for alan, deger in (("ic_pencereye_ust_alt_panel", True), ("ic_pencereye_ozel_karkas", True), ("boy", "siparis_boyu")):
        K = copy.deepcopy(PL.kurallari_oku())
        K["prefabrik"]["kurallar"]["karkasli_kaplama_panosu"]["deger"][alan] = deger
        with pytest.raises(ValueError, match="karkasli_kaplama_panosu"):
            PL.liste(PL.model_motor(_ie("AP14")), K)


def test_kapi_karkasli_panoda_giris_sayilir():
    """AP-26'nın giriş kapısı karkaslı panoda: kablo mesafesi (sigorta kutusu giriş kapısında) kapının ortasından ölçülür."""
    from motor import prefabrik_liste as PL
    N = PL.model_motor(_ie("AP26"))
    assert N["sigorta_en_uzak"]["nereden"] == "giriş kapısından kapalı kısmın en uzak köşesi"
    k = [p for p in N["panolar"] if p.get("karkasli")]
    assert [[a["tur"] for a in p["aciklar"]] for p in k] == [["dis_kapi", "pencere"], ["pencere"]]


@pytest.mark.parametrize("kod", ["AP14", "AP26"])
def test_cizim_dogrulamadan_gecer(kod, tmp_path):
    """Ön onay çizimi (`dxf_out.uret`): doğrulama geçer; her karkaslı pano tek blok (`…_KARKAS_…`), içinde derz yok; bloğun dolu parçaları ve
    açıklıkları panonun boyunu tam doldurur."""
    import ezdxf
    from motor import dxf_out
    ie = _ie(kod)
    m = dxf_out.uret(copy.deepcopy(ie), tmp_path)
    assert m["validation_passed"] and m["pdf"]
    doc = ezdxf.readfile(tmp_path / m["dxf"])
    plan = G.kur(ie)
    adlar = {b.name for b in doc.blocks if b.name.startswith("BOM_") and "_KARKAS_" in b.name}     # MNT_ kopyaları montaj planında
    assert len(adlar) == len(_karkaslilar(plan))
    yerlesen = [e for e in doc.modelspace().query("INSERT") if e.dxf.name in adlar]
    assert yerlesen and len(yerlesen) % len(adlar) == 0                   # her planda her karkaslı pano bir kez


def test_ifc_acikliklari():
    """IFC: karkaslı panonun bütün açıklıkları (AP-26 arka: kapı + 200/210) planın açıklık sayısıyla aynı."""
    import tempfile
    from motor import ifc_uret
    ie = _ie("AP26")
    plan = G.kur(copy.deepcopy(ie))
    with tempfile.TemporaryDirectory() as t:
        o = ifc_uret.uret(copy.deepcopy(ie), Path(t) / "AP26.ifc")
    assert o["sema_hatasi"] == 0
    assert o["pencere"] == sum(a.tur == "pencere" for p in plan.panolar for a in p.aciklar)
    assert o["kapi"] == sum(a.tur in ("ic_kapi", "dis_kapi") for p in plan.panolar for a in p.aciklar)


def test_montaj_rehberi_karkasli_duvar(tmp_path):
    """Montaj rehberi: karkaslı pano sahnede çelik karkaslı duvar (`karkas`), bütün açıklıklarıyla (`ops`). Beş evin çatısını rehber henüz
    kurmuyor (mahya yönü, cumba); TK-01 r07'nin arka sol duvarına yazılmış bir satırla denenir (hedef örnek değişmez, yalnız girdi kopyası)."""
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = _tk01([{"yon": "x", "eksen_cm": 883.5, "aralik_cm": [10, 381.5]}, {"yon": "x", "eksen_cm": 5, "aralik_cm": [10, 261]}])
    kart_model.uret(copy.deepcopy(ie), tmp_path, "TK01")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), tmp_path, "TK01", L, "TK-01")
    k = [p for p in d["panels"] if p.get("karkas")]
    assert sorted((p["boy"], [o["kind"] for o in p["ops"]]) for p in k) == [(251.0, ["win"]), (371.5, ["win"])]
    assert all(p["op"] == p["ops"][0] and p["tur"] == "OZEL" for p in k)


def test_kisa_artik_birlesimi_yutmaz():
    """Kısa artık komşusuyla birleşirken aradaki pano ekinde birleşim varsa (AP-14 arka duvarı, 256'daki iç duvar T'si; orada 3'lü H) açık hata;
    T sessizce panonun ortasına düşmez."""
    ie = _ie("AP14")
    st = next(s for s in ie["yapi"]["dizilim"]["karkasli_panolar"] if s["eksen_cm"] == 5 and s["aralik_cm"] == [5, 256])
    st["aralik_cm"] = [5, 240]
    with pytest.raises(G.IsEmriHatasi, match="sonunda kalan 16 cm'lik parça komşu panoyla birleşemiyor"):
        G.kur(ie)


@pytest.mark.parametrize("orta, acik", [([None, 470], "pencere 200x210"), ([430, 580], "dis_kapi 90")])
def test_aciklik_ic_duvar_tsine_binmez(orta, acik):
    """AP-26 arka duvarı: 381,5'teki iç duvar T'si karkaslı panonun içinde (paftadaki gibi); paftadan yazılan açıklık ortası pencereyi T'nin
    üstüne (470: 370–570) ya da kapıyı T'nin öteki yanına (430: yatak odası 1'den yatak odası 2'ye) götüremez."""
    ie = _ie("AP26")
    st = next(s for s in ie["yapi"]["dizilim"]["karkasli_panolar"] if s.get("aciklik_ortasi_cm") == [None, 525.3])
    st["aciklik_ortasi_cm"] = orta
    with pytest.raises(G.IsEmriHatasi, match=f"{acik} .* iç duvarın T'sine \\(duvar 8, eksen 381.5\\) biniyor ya da onun öteki yanına"):
        G.kur(ie)


@pytest.mark.parametrize("hi, olur", [(271.0, False), (291.0, True), (251.0, True)])
def test_oda_ortasi_yan_parcasi_cok_kisa_olmaz(hi, olur):
    """`genis_pencere: oda_ortasi`: iki yanda kalan parça ya hiç yok ya da en az 20 cm (çok kısa pano sınırı); 10 cm'lik iki pano kurulmaz."""
    d = G.Duvar(id=1, yon="x", hat=0, c=5.0, h=5.0, tur="dis", cevre=False, govde_yonu=0, n0=0, n1=4, p0=0.0, p1=400.0)
    ac = G.Acilim(tur="pencere", olcu="180x200", genislik=180.0, yukseklik=200.0, mahal="SALON")
    pts = sorted({0.0, G.MOD, 2 * G.MOD, hi, 400.0})
    d.panolar = [G.Pano(d, a, b) for a, b in zip(pts, pts[1:])]
    d.panolar[1].acilim = ac
    if olur:
        G._genis_pencere_oda_ortasi(d, d.panolar[1], 1, 2, (0.0, hi), {"olcu": "180x200"})
        yan = (hi - 2 * G.MOD) / 2
        assert [round(p.boy, 2) for p in d.panolar if p.a1 <= hi + 1e-6] == ([yan, 2 * G.MOD, yan] if yan else [2 * G.MOD])
    else:
        with pytest.raises(G.IsEmriHatasi, match="20 ile 125,5 arası"):
            G._genis_pencere_oda_ortasi(d, d.panolar[1], 1, 2, (0.0, hi), {"olcu": "180x200"})
