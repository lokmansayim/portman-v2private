"""İE-24 · Girintili gövde (TK-03; Lokman'ın 87,72 m² evinin 1. katı, 30 Ekim 2026: "var olan motor üzerine gideceğiz, yeni kurallar
ekleyeceğiz"). İş Emri'nin `girintiler`i ızgaranın bina dışında kalan dikdörtgenleridir: hücreleri hiçbir mahalin değildir, komşu oda
duvarı dış duvardır, girinti kenarında profil ve alan yoktur. Çatı: en derin şerit ana çatı, öteki şeritler ona paralel cumba (`cati_serit`;
Lokman 13:49). Ön ve arka Lokman'ın düzeltmesiyle (14:07; İş Emri r02 arka-sol). Paftadan ölçülen değerler `veri/TK03_pafta.json`;
kalan farklar orada."""
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
TK03 = VERI / "TK03.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plan():
    return G.kur(_oku(TK03))


@pytest.fixture(scope="module")
def pafta():
    return _oku(VERI / "TK03_pafta.json")


def _duvar(plan, yon, c, p0):
    return next(d for d in plan.duvarlar if d.yon == yon and abs(d.c - c) < 1e-6 and abs(d.p0 - p0) < 1e-6)


def test_dis_olcu_ve_toplam_alan(plan, pafta):
    """Dış ölçü kutusu girintiyle değişmez; bina çizgisinin (brüt) alanı + balkon paftanın "TOPLAM ALAN 87,72"si."""
    from motor import sunum
    assert (plan.W, plan.H) == (pafta["dis_olcu_cm"]["x"], pafta["dis_olcu_cm"]["y"])
    brut = sunum.bina_cizgisi(plan).area / 1e4
    assert abs(brut + plan.mahaller["BALKON"].alan_m2 - pafta["toplam_alan_m2"]) < 0.01
    assert abs(plan.mahaller["BALKON"].alan_m2 - pafta["oda_alanlari_m2"]["BALKON"]) < 0.01


def test_oda_alanlari_paftaya_yakin(plan, pafta):
    """Net alanlar paftanın yazısından en çok 0,45 m² farklı (salon 33,42 / 33,82: paftanın salonu duvar ekseninden; merdiven 4,39 / 4,26)."""
    for ad, beklenen in pafta["oda_alanlari_m2"].items():
        assert abs(plan.mahaller[ad].alan_m2 - beklenen) < 0.45, (ad, plan.mahaller[ad].alan_m2, beklenen)
    assert "GİRİNTİ" not in " ".join(plan.mahaller)


def test_girinti_duvarlari_dis_ve_aksa_ortali(plan, pafta):
    """Girinti duvarı 10'luk dış duvar, aksa ortalı (dis_dusey_duvar: cevre_aks_disinda); yüzler paftadakiyle 0,3 cm içinde."""
    sol = _duvar(plan, "y", 548.5, 10.0)
    assert sol.tur == "dis" and sol.h == 5.0 and not sol.cevre and abs(sol.p1 - 232.0) < 1e-6
    pf = pafta["girinti_duvarlari"]["on_sol_dusey"]
    assert abs(sol.c - sol.h - pf["yuzler_x"][0]) < 0.1 and abs(sol.c + sol.h - pf["yuzler_x"][1]) < 0.1
    arka = _duvar(plan, "x", 698.3, 780.6)
    assert arka.tur == "dis" and arka.h == 5.0
    pf = pafta["girinti_duvarlari"]["arka_sag_yatay"]
    assert abs(arka.c - arka.h - pf["yuzler_y"][0]) < 0.3 and abs(arka.c + arka.h - pf["yuzler_y"][1]) < 0.3
    banyo_sag = _duvar(plan, "y", 780.6, 703.3)                      # banyonun girintiye bakan duvarı dış, salona bakan ucu iç
    assert banyo_sag.tur == "dis"
    assert _duvar(plan, "y", 780.6, 675.05).tur == "ic"


def test_girintide_profil_ve_mahal_yok(plan):
    """Açık profil yalnız balkonun iki dış kenarında (sol ve arka); girinti kenarına profil çizilmez."""
    H = plan.H
    assert {(x0 == x1 == 0.0) or (y0 == y1 == H) for (x0, y0, x1, y1) in plan.acik_kenarlar} == {True}
    assert all(min(y0, y1) >= 675.05 - 1e-6 and max(x0, x1) <= 318.75 + 1e-6 for (x0, y0, x1, y1) in plan.acik_kenarlar)


@pytest.mark.parametrize("ad", ["sol dış (salon)", "sağ dış", "arka-sağ girinti duvarı", "ön-sol girinti duvarı"])
def test_pano_kosulari_paftayla_ayni(plan, pafta, ad):
    """Tam ızgarada (hiza: tam_izgara) bu dört duvarın pano koşusu paftadakiyle 1,3 cm içinde aynı; öteki farklar `farklar`da."""
    duvar = {"sol dış (salon)": ("y", 5.0, 242.0), "sağ dış": ("y", 1231.7, 10.0), "arka-sağ girinti duvarı": ("x", 698.3, 780.6),
             "ön-sol girinti duvarı": ("x", 237.0, 5.0)}[ad]
    boylar = [p.boy for p in sorted(_duvar(plan, *duvar).panolar, key=lambda p: p.a0)]
    beklenen = pafta["pano_kosulari"][ad]
    assert len(boylar) == len(beklenen) and all(abs(a - b) < 1.3 for a, b in zip(boylar, beklenen)), (boylar, beklenen)


def test_kapilar_paftadaki_yerde(plan, pafta):
    """Dört oda kapısı paftadaki boşluğun 10 cm içinde ve menteşesi paftadaki uçta."""
    kapilar = {tuple(p.acilim.arasi): (d, p) for d in plan.duvarlar for p in d.panolar if p.acilim and p.acilim.tur == "ic_kapi"}
    for k in pafta["kapilar"]:
        d, p = kapilar[tuple(k["arasi"])]
        g = p.gap(); lo, hi = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
        assert abs(lo - k["aralik_cm"][0]) < 10 and abs(hi - k["aralik_cm"][1]) < 10, (k["arasi"], lo, hi)
        mentese = float(k["mentese"].split()[1].replace(",", "."))
        assert abs((lo, hi)[G.mentese_ucu(p.acilim)] - mentese) < 10, (k["arasi"], lo, hi, mentese)


def test_gecis_kapisiz_cizilir(monkeypatch, tmp_path):
    """Kapısız geçiş: bayi görselinde kanat yayı yalnız dört oda kapısında (geçişe yay çizilmez). TK-03 r03'te merdiven ağzı duvarsız
    (D-34); geçiş r02'deki yerinde, ağzın açık parçası kaldırılarak sınanır."""
    from motor import bayi_gorseli as BG
    ie = _oku(TK03)
    ie["acik_sinirlar"] = [s for s in ie["acik_sinirlar"] if "parca_cm" not in s]
    ie["acikliklar"].append({"tur": "gecis", "olcu": 77, "arasi": ["SALON", "MERDİVEN KOVASI"], "pano": 2})
    yaylar = []
    gercek = BG.Arc
    monkeypatch.setattr(BG, "Arc", lambda *a, **k: (yaylar.append(a), gercek(*a, **k))[1])
    BG.plan_gorseli(ie, tmp_path / "plan.png")
    assert len(yaylar) == 4


def test_girinti_hatalari():
    ie = _oku(TK03)
    aks_disi = copy.deepcopy(ie); aks_disi["girintiler"][0] = [780.0, 10, 1231.7, 175]
    with pytest.raises(G.IsEmriHatasi, match="aks üstünde değil"):
        G.kur(aks_disi)
    cakisan = copy.deepcopy(ie); cakisan["girintiler"].append([548.5, 10, 780.6, 175])
    with pytest.raises(G.IsEmriHatasi, match="BANYO ile çakışıyor"):
        G.kur(cakisan)
    ust_uste = copy.deepcopy(ie); ust_uste["girintiler"].append([1009, 10, 1231.7, 175])
    with pytest.raises(G.IsEmriHatasi, match="başka bir girinti ile çakışıyor"):
        G.kur(ust_uste)
    eksik = copy.deepcopy(ie); eksik["girintiler"].pop()
    with pytest.raises(G.IsEmriHatasi, match="boş hücreler"):
        G.kur(eksik)
    bicim = copy.deepcopy(ie); bicim["girintiler"][0] = [780.6, 10, 1231.7]
    with pytest.raises(G.IsEmriHatasi, match=r"\[x0, y0, x1, y1\]"):
        G.kur(bicim)


def test_girintisiz_is_emri_anahtar_sayilmaz():
    """`girintiler` geometri anahtarıdır; anahtarsız İş Emri eski yoldan gider (boş liste de anahtar değil)."""
    ie = _oku(TK03)
    assert G.geometri_anahtari_var({"yapi": {}, "mahaller": [], "acikliklar": [], "girintiler": [[0, 0, 1, 1]]})
    assert not G.geometri_anahtari_var({"yapi": {}, "mahaller": [], "acikliklar": [], "girintiler": []})
    assert ie["girintiler"]


def test_dogrulama_gecer(tmp_path):
    """Ön onay çizimi (DXF → doğrulama → PDF) girintili gövdede geçer."""
    from motor import dxf_out
    m = dxf_out.uret(_oku(TK03), tmp_path)
    assert m["validation_passed"] and m["pdf"]


# ── çatı: ana çatı + paralel cumba (Lokman, 30 Ekim 13:49; paftanın makas planı MKS01–12) ──────────────────────────────────────────
@pytest.fixture(scope="module")
def cati(plan):
    from motor import sunum
    return sunum.cati_tanimi(plan, _oku(TK03))


def test_cati_seritleri_ana_ve_cumba(cati):
    """En uzun makaslı şerit ana çatı, iki yanı cumba; açıklık ve boy gövdenin dış yüzlerinden."""
    p = {q["ad"]: q for q in cati["parcalar"]}
    assert [q["ad"] for q in cati["parcalar"]] == ["sol cumba", "ana çatı", "sağ cumba"]
    assert [q["rol"] for q in cati["parcalar"]] == ["cumba", "ana", "cumba"]
    assert (p["ana çatı"]["aciklik_cm"], p["ana çatı"]["boy_cm"]) == (873.3, 242.1)
    assert (p["sol cumba"]["aciklik_cm"], p["sol cumba"]["boy_cm"]) == (641.3, 543.5)
    assert (p["sağ cumba"]["aciklik_cm"], p["sağ cumba"]["boy_cm"]) == (703.3, 451.1)
    assert p["sol cumba"]["komsu"] == p["sağ cumba"]["komsu"] == "ana çatı"


def test_makaslar_paftadaki_yerde(cati, pafta):
    """12 makas: sol cumba 5 (baş dış uçta), ana 3 (iki baş), sağ cumba 4; cumbalarda iç uçta makas yok. Cumba makasları saçak duvarının
    pano eklerinde, paftadakiyle 1,5 cm içinde; ana çatının baş makasları da. Ana çatının orta makası paftada ön duvarın 655,1'deki ekinde;
    Motor'un ön duvarında orada ek yok (`farklar` › ön dış), eşit aralık ve uyarı."""
    pf = pafta["cati"]["makaslar_x"]
    p = {q["ad"]: q for q in cati["parcalar"]}
    assert sum(len(q["makaslar"]) for q in cati["parcalar"]) == 12
    for ad in ("sol cumba", "sağ cumba"):
        yer = [m["konum"] for m in p[ad]["makaslar"]]
        assert len(yer) == len(pf[ad]) and all(abs(a - b) < 1.5 for a, b in zip(yer, pf[ad])), (ad, yer)
        assert p[ad]["makas_yeri"] == "pano ekleri"
    assert [m["rol"] for m in p["sol cumba"]["makaslar"]] == ["bas", "orta", "orta", "orta", "orta"]
    assert [m["rol"] for m in p["sağ cumba"]["makaslar"]] == ["orta", "orta", "orta", "bas"]
    ana = [m["konum"] for m in p["ana çatı"]["makaslar"]]
    assert [m["rol"] for m in p["ana çatı"]["makaslar"]] == ["bas", "orta", "bas"]
    assert abs(ana[0] - pf["ana çatı"][0]) < 1.5 and abs(ana[2] - pf["ana çatı"][2]) < 1.5
    assert ana[1] == 664.55 and p["ana çatı"]["makas_yeri"] == "eşit aralık"
    assert any("ana çatı" in u and "eşit aralıklı 3 makas" in u for u in cati["uyarilar"])


def test_makas_profilleri_paftayla_ayni(cati, pafta):
    """Makasın üst başlık boyu (saçak ucundan mahyaya) ve yüksekliği (topuk dahil) paftanın üç profiliyle 0,05 cm içinde."""
    for q in cati["parcalar"]:
        pf = pafta["cati"]["makas_profilleri"][q["ad"]]
        assert abs(q["aciklik_cm"] + 2 * cati["sacak"] - pf["taban"]) < 0.05
        assert abs(q["makas_ust_boy_cm"] - pf["ust_boy"]) < 0.05, q["ad"]
        assert abs(q["makas_yuksekligi_cm"] - pf["yukseklik"]) < 0.05, q["ad"]


def test_sacak_hatlari_asik_planiyla_ayni(cati, pafta):
    """Aynı düzlemdeki yüzler birleşir: arkada sol cumba + ana çatı, önde ana çatı + sağ cumba tek saçak hattı; cumbanın öteki yüzü ana
    çatının duvar yüzüne kadar (kalkan saçağının altında). Saçak hatları paftanın aşık planındaki genişliklerle aynı."""
    from motor.genel import cati_genel
    ck = cati_genel.cati_kur(cati)
    hatlar = sorted(tuple(sorted((round(e["p"][0], 2), round(e["q"][0], 2)))) for e in ck["kenarlar"] if e["tur"] == "sacak")
    assert hatlar == sorted(tuple(v) for v in pafta["cati"]["sacak_hatlari"].values())
    mahya = sorted(round(e["plan_boy"], 2) for e in ck["kenarlar"] if e["tur"] == "mahya")
    assert mahya == [302.1, 451.1, 543.5]                                # ana (iki alın saçağıyla), cumbalar ana çatının saçağına kadar
    assert {d["ad"]: d.get("birlesen") for d in cati["duzlemler"]} == {
        "sol cumba ön": None, "sağ cumba arka": None,
        "ana çatı ön": ["ana çatı ön", "sağ cumba ön"], "ana çatı arka": ["ana çatı arka", "sol cumba arka"]}


def test_gorunusler_cati(plan):
    """Ön görünüşte üç mahya kotu (sol cumba, ana, sağ cumba), tepe ana çatının mahyası (paftada 163,43 duvar üstünden); yandan bakışta öteki
    yandaki cumba ana çatının kalkanının ardında kalır (sol görünüşte sağ cumbanın çizgisi yok)."""
    from motor import cephe_gorunus as CG
    ie = _oku(TK03)
    H0, zs, eg = 250.0, 260.0, 0.3288
    on = CG.cati_cizgileri(plan, ie, "on")
    yatay = {round(a[1], 2) for c in on["cizgiler"] for a, b in zip(c, c[1:]) if abs(a[1] - b[1]) < 1e-6 and a[1] > zs + 1}
    assert yatay == {round(zs + eg * v, 2) for v in (350.65, 466.65, 381.65)}
    assert (on["u0"], on["u1"]) == (-30.0, 1266.7) and abs(on["tepe"][1] - H0 - 163.43) < 0.05
    sol = CG.cati_cizgileri(plan, ie, "sol")
    zr = zs + eg * 381.65                                               # sağ cumbanın mahyası
    assert not any(abs(z - zr) < 0.05 for c in sol["cizgiler"] for _u, z in c)
    assert len(sol["cizgiler"]) == 3                                    # ana çatının iki yüzü ve sol cumbanın ön yüzü


def test_girinti_duvari_gorunuste(plan):
    """Girintideki duvar görünür (gövde kutu değil, gövdenin dış çizgisi): ön görünüşte salonun girinti duvarındaki pencere de var."""
    from motor import cephe_gorunus as CG
    pen = [a for a in CG.cephe(plan, "on")["acikliklar"] if a["tur"] == "pencere"]
    assert len(pen) == 3 and abs(pen[0]["u0"] - 133.2) < 0.1


def test_cati_hatalari(plan, monkeypatch):
    """U gövde (bir şeritte iki parça) ve ana çatıya doğru komşusunun açıklığına sığmayan şerit (kademeli çatı) çizilmez, hata söylenir;
    IFC girintili gövdenin çatısını kurmaz (dış ölçü kutusunu örterdi)."""
    from shapely.geometry import Polygon
    from motor import cati_serit, ifc_uret
    from motor.cati_prefabrik import PrefabrikCatiHatasi
    ie = _oku(TK03)
    u = Polygon([(0, 0), (900, 0), (900, 300), (300, 300), (300, 500), (900, 500), (900, 800), (0, 800)])     # mahyaya dik kesitte iki parça
    with pytest.raises(PrefabrikCatiHatasi, match="U gövde"):
        cati_serit.seritler(u, ie)
    kademe = Polygon([(0, 0), (500, 0), (500, 100), (1000, 100), (1000, 900), (500, 900), (500, 600), (0, 600)])
    monkeypatch.setattr(cati_serit.G, "govde_cokgeni", lambda _p: kademe)
    with pytest.raises(PrefabrikCatiHatasi, match="kademeli çatı"):
        cati_serit.tanim(plan, ie)
    monkeypatch.undo()
    with pytest.raises(G.IsEmriHatasi, match="IFC'nin çatısı"):
        ifc_uret.hazirla(ie)


def test_girintisiz_govde_kutu():
    """Girintisiz planda gövde çizgisi dış ölçü kutusu (bugünkü görünüşler aynen) ve beşik iki düzlem."""
    from shapely.geometry import box
    from motor import sunum
    ie = _oku(KOK / "is_emri" / "P6001_2plus1_6x6.json")
    p = G.kur(ie)
    assert not p.girintili and G.govde_cokgeni(p).equals(box(*G.govde_kutusu(p)))
    t = sunum.cati_tanimi(p, ie)
    assert "parcalar" not in t and len(t["duzlemler"]) == 2
