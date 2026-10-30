"""İE-24 · Girintili gövde (TK-03; Lokman'ın 87,72 m² evinin 1. katı, 30 Ekim 2026: "var olan motor üzerine gideceğiz, yeni kurallar
ekleyeceğiz"). İş Emri'nin `girintiler`i ızgaranın bina dışında kalan dikdörtgenleridir: hücreleri hiçbir mahalin değildir, komşu oda
duvarı dış duvardır, girinti kenarında profil ve alan yoktur. Paftadan ölçülen değerler `veri/TK03_pafta.json`; kalan farklar orada."""
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
    """Net alanlar paftanın yazısından en çok 0,45 m² farklı (salon 33,41 / 33,82: paftanın salonu duvar ekseninden; merdiven 4,39 / 4,26)."""
    for ad, beklenen in pafta["oda_alanlari_m2"].items():
        assert abs(plan.mahaller[ad].alan_m2 - beklenen) < 0.45, (ad, plan.mahaller[ad].alan_m2, beklenen)
    assert "GİRİNTİ" not in " ".join(plan.mahaller)


def test_girinti_duvarlari_dis_ve_aksa_ortali(plan, pafta):
    """Girinti duvarı 10'luk dış duvar, aksa ortalı (dis_dusey_duvar: cevre_aks_disinda); yüzler paftadakiyle 0,3 cm içinde."""
    sol = _duvar(plan, "y", 548.5, 641.3)
    assert sol.tur == "dis" and sol.h == 5.0 and not sol.cevre
    pf = pafta["girinti_duvarlari"]["arka_sol_dusey"]
    assert abs(sol.c - sol.h - pf["yuzler_x"][0]) < 0.1 and abs(sol.c + sol.h - pf["yuzler_x"][1]) < 0.1
    on = _duvar(plan, "x", 175.0, 780.6)
    assert on.tur == "dis" and on.h == 5.0
    pf = pafta["girinti_duvarlari"]["on_sag_yatay"]
    assert abs(on.c - on.h - pf["yuzler_y"][0]) < 0.3 and abs(on.c + on.h - pf["yuzler_y"][1]) < 0.3
    banyo_sag = _duvar(plan, "y", 780.6, 10.0)                       # banyonun girintiye bakan duvarı dış, salona bakan ucu iç
    assert banyo_sag.tur == "dis" and abs(banyo_sag.p1 - 170.0) < 1e-6
    assert _duvar(plan, "y", 780.6, 180.0).tur == "ic"


def test_girintide_profil_ve_mahal_yok(plan):
    """Açık profil yalnız balkonun iki dış kenarında (sol ve ön); girinti kenarına profil çizilmez."""
    assert {(x0 == x1 == 0.0) or (y0 == y1 == 0.0) for (x0, y0, x1, y1) in plan.acik_kenarlar} == {True}
    assert all(max(y0, y1) <= 198.25 + 1e-6 and max(x0, x1) <= 318.75 + 1e-6 for (x0, y0, x1, y1) in plan.acik_kenarlar)


@pytest.mark.parametrize("ad", ["sol dış (salon)", "sağ dış", "ön-sağ girinti duvarı", "arka-sol girinti duvarı"])
def test_pano_kosulari_paftayla_ayni(plan, pafta, ad):
    """Tam ızgarada (hiza: tam_izgara) bu dört duvarın pano koşusu paftadakiyle 1,3 cm içinde aynı; öteki farklar `farklar`da."""
    duvar = {"sol dış (salon)": ("y", 5.0, 203.25), "sağ dış": ("y", 1231.7, 180.0), "ön-sağ girinti duvarı": ("x", 175.0, 780.6),
             "arka-sol girinti duvarı": ("x", 636.3, 5.0)}[ad]
    boylar = [p.boy for p in _duvar(plan, *duvar).panolar]
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
    """Merdiven ağzı kapısız geçiş: bayi görselinde kanat yayı yalnız dört oda kapısında (geçişe yay çizilmez)."""
    from motor import bayi_gorseli as BG
    yaylar = []
    gercek = BG.Arc
    monkeypatch.setattr(BG, "Arc", lambda *a, **k: (yaylar.append(a), gercek(*a, **k))[1])
    BG.plan_gorseli(_oku(TK03), tmp_path / "plan.png")
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
