"""BK-14 · Gövdeden taşan veranda (İş Emri `verandalar`).

Motor önceden yalnız pano ızgarasının içindeki verandayı çiziyordu; gövdenin dışına taşan veranda (TK-01: önde 386 × 181, arkada 261 × 130)
girdide yer bulamıyordu. Şimdi veranda gövdenin dış yüzüne dışarıdan eklenir: açık mahal, üç açık kenar (kiriş), iki dış köşede dikme ve
kendi çatısı. Plan, DXF ve doğrulama, bayi paftası (çatı planı, ön ve sağ yan görünüş), IFC ve yükleme listesi aynı geometriden. Liste
TK-01'in geçici yolundaki listeyle (gövde Motor'dan, verandalar elle; `Teklif_Calisma/TK-01/gecici_r01`) bütün satırlarda aynı adeti verir;
burada o değerler sabit. `verandalar` yoksa hiçbiri devreye girmez (referans gerilemesi bayt bayt aynı). Bu bir Motor kilididir, paftaya
uygunluk kanıtı değildir.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL, sunum, veranda as VR  # noqa: E402

TK01 = KOK / "testler" / "motor" / "veri" / "TK01.json"
PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _ie(verandalar=None) -> dict:
    ie = _oku(TK01)
    if verandalar is not None:
        ie["verandalar"] = verandalar
    return ie


@pytest.fixture(scope="module")
def plan():
    return G.kur(_ie())


def test_veranda_geometrisi(plan):
    on, arka = plan.dis_verandalar
    assert (on["ad"], on["cephe"], on["rect"]) == ("ÖN VERANDA", "on", (256.0, -181.0, 642.0, 0.0))
    assert (arka["ad"], arka["cephe"], arka["rect"]) == ("ARKA VERANDA", "arka", (0.0, 888.0, 261.0, 1018.0))
    assert plan.mahaller["ÖN VERANDA"].acik and plan.mahaller["ÖN VERANDA"].alan_m2 == pytest.approx(6.9866)
    assert plan.mahaller["ARKA VERANDA"].alan_m2 == pytest.approx(3.393)
    assert on["kolonlar"] == [(256.0, -181.0, 266.0, -171.0), (632.0, -181.0, 642.0, -171.0)]
    assert arka["kolonlar"] == [(0.0, 1008.0, 10.0, 1018.0), (251.0, 1008.0, 261.0, 1018.0)]
    assert len(plan.dikmeler) == 4 and all(k in plan.dikmeler for v in plan.dis_verandalar for k in v["kolonlar"])
    uz = lambda e: max(e[2] - e[0], e[3] - e[1])
    assert [uz(e) for v in plan.dis_verandalar for e in v["kenarlar"]] == [386.0, 181.0, 181.0, 261.0, 130.0, 130.0]
    assert all(e in plan.acik_kenarlar for v in plan.dis_verandalar for e in v["kenarlar"])
    assert G.govde_kutusu(plan) == (0.0, 0.0, 898.0, 888.0)              # ana çatı gövdeyi örter
    assert sunum.sinirlar(plan) == (0.0, -181.0, 898.0, 1018.0)
    assert sunum.oturum_m2(plan) == pytest.approx(90.12, abs=0.01)
    assert not [u for u in plan.uyarilar if u.startswith("Veranda")]     # iki çatı da İş Emri'nde, ikisi de ana çatının kalkan yüzünde


def test_veranda_catisi(plan):
    on, arka = (VR.cati(v, plan.is_emri) for v in plan.dis_verandalar)
    assert on["tip"] == "besik" and on["kutu"] == (226.0, -211.0, 672.0, 0.0)  # dış kenarda ve iki yanda 30 saçak, cephede yok
    assert on["sacak_kotu"] == 260.0 and on["mahya_kotu"] == pytest.approx(321.325)
    assert on["mahya"] == ((449.0, -211.0), (449.0, 0.0))                 # mahya cepheye dik
    assert arka["kutu"] == (-30.0, 888.0, 291.0, 1048.0) and arka["mahya_kotu"] == pytest.approx(304.1375)
    p = VR.gorunus_parcalari(plan, plan.is_emri, "on")
    say = {t: sum(x["tur"] == t for x in p) for t in ("kolon", "kiris", "alin", "cati")}
    assert say == {"kolon": 4, "kiris": 6, "alin": 2, "cati": 2}         # önden iki kalkan görünür
    yan = VR.gorunus_parcalari(plan, plan.is_emri, "sag")
    assert not [x for x in yan if x["tur"] == "alin"] and sum(x["tur"] == "cati" for x in yan) == 2


def test_veranda_dogrulamadan_gecer(tmp_path):
    m = dxf_out.uret(_ie(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("errors")
    v = _oku(tmp_path / "validation.json")
    assert v["rooms_m2"]["ÖN VERANDA"] == pytest.approx(6.9866) and v["rooms_m2"]["ARKA VERANDA"] == pytest.approx(3.393)
    dxf = next(tmp_path.glob("*.dxf")).read_text(encoding="utf-8", errors="ignore")
    for blok in ("_VERANDA_ON_", "_VERANDA_YAN_"):
        assert blok in dxf, blok


def test_veranda_profili_kiris_yerinde(plan):
    """DXF'in veranda profili blokları (BOM ve IFC kirişleri bunlardan): her verandada üç, kutusu Plan'ın kirişiyle aynı; gövde duvarının
    içine profil düşmez, iki yanın iç çizgisi verandanın içinde (geometri hakemi, 27 Ekim: eski döngü gövde çizgisini de profil sayıyordu,
    aynı adlı iki yan bloğu bir yanın kaymasıyla çiziliyordu)."""
    from motor import ifc_uret
    g = ifc_uret.hazirla(_ie())
    profil = sorted(tuple(b["rect"]) for b in g["baglantilar"] if b["tur"] == "veranda_profil")
    kiris = sorted(tuple(round(t, 2) for t in k) for v in plan.dis_verandalar for k in v["kirisler"])
    assert profil == kiris and len(profil) == 6
    assert sum(b["tur"] == "dikme" for b in g["baglantilar"]) == 4
    assert g["veranda"] is None and [v["net_m2"] for v in g["dis_verandalar"]] == [pytest.approx(6.9866), pytest.approx(3.393)]


def test_veranda_listesi():
    N = PL.model_motor(_ie())
    assert (N["W"], N["D"], N["brut_m2"]) == (898.0, 1199.0, 90.122)       # brüt gövde + veranda; dış kutunun boş köşeleri sayılmaz
    assert N["dis_cevre_m"] == pytest.approx(35.72) and N["ic_kalan_dis_duvar_m"] == pytest.approx(6.47) and N["dikmeler"] == 4
    assert N["veranda_kenarlari_cm"] == [386.0, 181.0, 181.0, 261.0, 130.0, 130.0]
    ana, on, arka = N["cati"]
    assert (ana["aciklik_cm"], ana["boy_cm"], ana["makas_kosu_cm"]) == (898.0, 888.0, 868.0)
    assert {k: on[k] for k in ("ad", "tip", "aciklik_cm", "boy_cm", "kalkan", "capraz", "acik", "mahya_boy_cm", "sacak_hatlari_m", "makas_kosu_cm")} == \
        {"ad": "ön veranda çatısı", "tip": "besik", "aciklik_cm": 386.0, "boy_cm": 181.0, "kalkan": 1, "capraz": False, "acik": True,
         "mahya_boy_cm": 211.0, "sacak_hatlari_m": [2.11, 2.11], "makas_kosu_cm": 161.0}
    assert (arka["aciklik_cm"], arka["boy_cm"], arka["mahya_boy_cm"]) == (261.0, 130.0, 160.0)
    N["ozellikler"] = {"Çatı Şekli": "Beşik", "Çatı Kaplaması": "Tek Kat Panel", "Çatı Kaplama Rengi": "Antrasit", "Tavan": "Asma"}
    L = PL.liste(N)
    sat = lambda kalem: [(s["olcu"], s["adet"]) for s in L["satirlar"] if s["kalem"] == kalem]
    assert sat("Özel kutu profil (kolon) 100 × 100") == [("L 2500", 4)]
    assert sat("Kutu profil (kiriş) 100 × 100") == [(f"L {x}", 1) for x in (3760, 1710, 1710, 2510, 1200, 1200)]
    assert sat("Yavru makas · ön veranda çatısı") == [("L 4460", 3)] and sat("Yavru makas · arka veranda çatısı") == [("L 3210", 2)]
    assert sat("Metal dere") == [("L 4000", 7)]
    assert L["ozet"]["satir"] == 131
    N["ozellikler"]["Tavan"] = "Ters"
    assert PL.liste(N)["ozet"]["satir"] == 129


def test_verandasiz_ayni():
    """`verandalar` yoksa yeni yol hiç çalışmaz: gövde kutusu dış ölçüyle aynı, listede tek çatı, brüt dış dikdörtgen."""
    ie = _oku(PK01)
    p = G.kur(json.loads(json.dumps(ie)))
    assert p.dis_verandalar == [] and G.govde_kutusu(p) == sunum.sinirlar(p)
    N = PL.model_motor(ie)
    assert len(N["cati"]) == 1 and N["brut_m2"] == round(N["W"] * N["D"] / 1e4, 3)
    assert "dis_verandalar" not in __import__("motor.ifc_uret", fromlist=["hazirla"]).hazirla(ie)


@pytest.mark.parametrize("v, hata", [
    ({"ad": "V", "cephe": "kuzey", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150}, "cephesi bilinmiyor"),
    ({"ad": "V", "cephe": "on", "bas_cm": 800, "bit_cm": 1000, "derinlik_cm": 150}, "tam oturmuyor"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 30, "derinlik_cm": 150}, "çok dar"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": "derin"}, "sayı olmalı"),
    ({"ad": "SALON", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150}, "aynı"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150, "tur": "salon"}, "açık mahal değil"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150, "cati": {"tip": "kirma"}}, "çatı tipi bilinmiyor"),
])
def test_veranda_hatali_girdi(v, hata):
    with pytest.raises(G.IsEmriHatasi, match=hata):
        G.kur(_ie([v]))


def test_veranda_ust_uste_hata():
    v = {"cephe": "on", "bas_cm": 0, "bit_cm": 300, "derinlik_cm": 150}
    with pytest.raises(G.IsEmriHatasi, match="çakışıyor"):
        G.kur(_ie([{"ad": "A", **v}, {"ad": "B", **v, "bas_cm": 200, "bit_cm": 500}]))


def test_veranda_saçak_yuzunde_uyarir_ve_capraz():
    """Ana çatının saçak yüzündeki veranda (sağ cephe; makaslar x'i geçer): çatısı yazılmamışsa beşik ve ana eğim, uyarı; mahyası saçağın
    üstünde kaldığı için dere çizilmez, uyarı; listede çapraz beşik (5.1 deresi), mahya ana çatının yüzüne kadar."""
    p = G.kur(_ie([{"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150}]))
    u = [x for x in p.uyarilar if x.startswith("Veranda")]
    assert len(u) == 2 and "%27,5" in u[0] and "dere" in u[1]
    N = PL.model_motor(_ie([{"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150}]))
    c = N["cati"][1]
    assert c["capraz"] is True and c["aciklik_cm"] == 300.0 and c["mahya_boy_cm"] == pytest.approx(150 + 180 * 0.275 / 0.275)
    assert N["veranda_kenarlari_cm"] == [300.0, 150.0, 150.0]
    tek = PL.model_motor(_ie([{"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150,
                                "cati": {"tip": "tek_yon", "egim_yuzde": 10}}]))["cati"][1]
    assert (tek["tip"], tek["aciklik_cm"], tek["boy_cm"], tek["kalkan"], tek["sacak_hatlari_m"]) == ("tek_yon", 150.0, 300.0, 0, [3.6])


def test_kalkan_yaninda_cati_tasmasi_uyarir(plan):
    """Kalkan yanındaki veranda çatısı ana çatının saçağının üstüne çıkarsa uyarı (K16). TK-01'in kendi çatıları altında: ön 70 cm aşağıda,
    arkanın sol yüzü ana çatının sol yüzüyle aynı düzlemde (0)."""
    assert [round(VR.ana_catiya_tasma(plan, plan.is_emri, v), 1) for v in plan.dis_verandalar] == [-70.4, 0.0]
    for cati, cm in (({"tip": "tek_yon", "egim_yuzde": 27.5}, "44"), ({"tip": "besik", "egim_yuzde": 40}, "20")):
        ie = _ie(); ie["verandalar"][1]["cati"] = cati
        u = [x for x in G.kur(ie).uyarilar if x.startswith("Veranda")]
        assert len(u) == 1 and "ARKA VERANDA" in u[0] and f"yüzünü {cm} cm aşıyor" in u[0], u


def test_capraz_besik_farkli_sacak():
    """Saçak yüzündeki beşikte saçak hattı dış kenardan ana çatının saçak hattına, mahya ana çatının yüzüne: veranda saçağı 50, ana 30."""
    v = {"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150, "cati": {"tip": "besik", "egim_yuzde": 27.5, "sacak_cm": 50}}
    c = PL.model_motor(_ie([v]))["cati"][1]
    assert c["capraz"] is True and c["sacak_hatlari_m"] == [1.7, 1.7] and c["mahya_boy_cm"] == pytest.approx(150 + 20 + 200)


def test_ayna_verandayi_cevirir():
    """Varyant aynası (`beyin.varyant.ayna`, pano birimli İş Emri) verandayı da çevirir: cephe ve cephe boyunca konum. P6001 (773 × 763)."""
    from beyin import varyant
    p6001 = _oku(KOK / "is_emri" / "P6001_2plus1_6x6.json")
    for v, x, y in (({"ad": "ARKA V", "cephe": "arka", "bas_cm": 50, "bit_cm": 350, "derinlik_cm": 150},
                     (423.0, 763.0, 723.0, 913.0), (50.0, -150.0, 350.0, 0.0)),
                    ({"ad": "SOL V", "cephe": "sol", "bas_cm": 300, "bit_cm": 500, "derinlik_cm": 120},
                     (773.0, 300.0, 893.0, 500.0), (-120.0, 263.0, 0.0, 463.0))):
        ie = json.loads(json.dumps(p6001)); ie["verandalar"] = [v]
        assert G.kur(varyant.ayna(ie, "x")).dis_verandalar[0]["rect"] == x
        assert G.kur(varyant.ayna(ie, "y")).dis_verandalar[0]["rect"] == y
    # ayak izi simetrik değil (ızgara içi veranda sağ kenarı boydan boya kaplar): konum planın ölçüsüne göre, ayak izine göre değil (hakem 2. tur)
    yan = _oku(KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json")
    for m in yan["mahaller"]:
        m["konum_pano"] = {"VERANDA": [[5, 0, 6, 8.5]], "SALON": [[2.5, 4, 5, 8.5]]}.get(m["ad"], m["konum_pano"])
    yan["verandalar"] = [{"ad": "ARKA V", "cephe": "arka", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150}]
    assert G.kur(varyant.ayna(yan, "x")).dis_verandalar[0]["rect"] == (373.0, 1076.75, 673.0, 1226.75)   # W 773: sağdan 100 içeride


def test_bayi_plan_gorseli_verandayi_kirpmaz(tmp_path):
    """Canlı yolun plan görseli (`bayi_gorseli.plan_gorseli`) çerçeveyi taşan verandayla genişletir (geometri hakemi: ön veranda
    kırpılıyordu); veranda yoksa çerçeve gövde ± 120, eskisi gibi."""
    from PIL import Image
    from motor import bayi_gorseli
    yol = bayi_gorseli.plan_gorseli(_ie(), tmp_path / "tk01.png")
    w, h = Image.open(yol).size
    assert w == 1400 and h == pytest.approx(1400 * (1199 + 2 * 120 + 90) / (898 + 2 * 120), abs=1)


def test_bayi_paftasi_verandali(tmp_path):
    import pymupdf
    ie = _ie()
    o = sunum.bayi_paftasi(ie, tmp_path, perspektif=False, bilgi={"tarih": "27.10.2026"})
    assert o["teslim"] is True
    with pymupdf.open(tmp_path / "TK01_bayi.pdf") as d:
        metin = " ".join(w[4] for w in d[0].get_text("words"))
    for s in ("ÖN VERANDA", "ARKA VERANDA", "ÖN GÖRÜNÜŞ", "SAĞ YAN GÖRÜNÜŞ", "ÇATI PLANI", "386", "181", "130", "1199"):
        assert s in metin, s
    oz = _oku(tmp_path / "TK01_bayi_ozet.json")
    assert oz["sayimlar"]["dikme"] == 4 and oz["sayimlar"]["oturum_m2"] == pytest.approx(90.12)


def test_ifc_veranda_catisi(tmp_path):
    from motor import ifc_uret
    g = ifc_uret.hazirla(_ie())
    assert [v["ad"] for v in g["dis_verandalar"]] == ["ÖN VERANDA", "ARKA VERANDA"]
    oz = ifc_uret.uret(_ie(), tmp_path / "tk01.ifc")
    assert oz["sema_hatasi"] == 0
    import ifcopenshell
    f = ifcopenshell.open(str(tmp_path / "tk01.ifc"))
    adlar = {e.Name for e in f.by_type("IfcRoof")} | {e.Name for e in f.by_type("IfcSlab")} | {e.Name for e in f.by_type("IfcPlate")}
    for ad in ("VERANDA_CATISI_1", "VERANDA_CATISI_2", "VERANDA_ZEMINI_1", "VERANDA_CATI_1_1", "VERANDA_CATI_1_2", "VERANDA_ALIN_1"):
        assert ad in adlar, ad
    mekan = {e.Name: e.LongName for e in f.by_type("IfcSpace")}
    assert mekan.get("M-VERANDA-1") == "ÖN VERANDA" and mekan.get("M-VERANDA-2") == "ARKA VERANDA" and "M-VERANDA" not in mekan
