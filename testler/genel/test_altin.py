"""İE-08 GM1/GM3 · altın test: Ç8801 (katalog) ana koddaki paketle, kural seti 0.19 pimiyle çizilir; plan PNG, liste JSON ve IFC izi
`modeller/altin.json` ile aynı; çizim seti tam (perspektifsiz 7/14), IFC şema hatası 0, liste 93 satır; bayi görseli ≤ 5 MB; şablon
paftası 2 sayfa A4 yatay. Asıl referans `testler/referans/` zinciridir (D-02, D-08); bu test paketin kendi başına çalıştığını söyler."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import iz, uret  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
PERSPEKTIF = ["C8801_perspektif_on_sag.png", "C8801_perspektif_on_sol.png", "C8801_perspektif_arka_sol.png", "C8801_perspektif_arka_sag.png",
              "C8801_catisiz.png", "C8801_makasli.png", "C8801_geometri.json"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def c8801(tmp_path_factory):
    hedef = tmp_path_factory.mktemp("c8801")
    m = uret.uret(KOK / "modeller" / "C8801.json", hedef, is_emri_no="TEST-ALTIN", revizyon=1, set_yolu=SET, yontem="panel", perspektif=False, bayi=True)
    return hedef, m, json.loads((hedef / "validation.json").read_text(encoding="utf-8"))


def test_c8801_altin_degerlerle_ayni(c8801):
    hedef, m, v = c8801
    altin = json.loads((KOK / "modeller" / "altin.json").read_text(encoding="utf-8"))["C8801"]
    assert m["passed"] and v["passed"] and v["errors"] == [], v["errors"]
    assert v["ifc"]["sema_hatasi"] == 0 and v["liste_satir"] == 93
    assert sha(hedef / "C8801_plan.png") == altin["plan_png_sha256"]
    assert sha(hedef / "C8801_yukleme.json") == altin["yukleme_json_sha256"]
    assert iz.ifc_izi(hedef / "C8801.ifc") == altin["ifc_izi"]
    assert v["set"].endswith("setler/0.19.json")


def test_c8801_cizim_seti_tam_perspektif_haric(c8801):
    hedef, m, v = c8801
    assert v["ciktilar"]["beklenen"] == 15 and v["ciktilar"]["var"] == 8 and v["ciktilar"]["zorunlu_eksik"] == []     # 15: bayi görseli (PR-2a)
    assert sorted(v["ciktilar"]["eksik"]) == sorted(PERSPEKTIF)
    assert v["perspektif"]["durum"] == "ATLANDI"
    for ad in ("C8801_plan.png", "C8801_gorunusler.png", "C8801_pafta.png", "C8801.ifc", "C8801.ozet.json", "C8801_yukleme.json", "C8801_yukleme.md"):
        assert (hedef / ad).stat().st_size > 0, ad


def test_c8801_bayi_ciktilari(c8801):
    hedef, m, v = c8801
    bayi = hedef / "C8801_plan_bayi.png"; pdf = hedef / "C8801_pafta.pdf"
    assert bayi.exists() and bayi.stat().st_size <= 5 * 1024 * 1024 and Path(m["plan_bayi"]).name == bayi.name
    assert pdf.exists() and Path(m["pdf"]).name == pdf.name and m["pdf_sha256"] == sha(pdf)
    import fitz
    with fitz.open(pdf) as d:
        assert len(d) == 2 and (round(d[0].rect.width), round(d[0].rect.height)) == (842, 595)
        sozcukler = [w[4] for p in d for w in p.get_text("words")]
    assert sozcukler.count("Portman") == 3                       # Çizen, Kontrol, Onay (Lokman 12.10.2026 14:53)
    assert "..." in sozcukler and "ÇATI" in sozcukler            # ilgili kişi-telefon katalogda "..."; 2. sayfa çatı planı
    assert sozcukler.count("TASLAK") == 2                        # 1. sayfa antet üstü (D-10, Soru 25) + 2. sayfa başlığı
    with fitz.open(pdf) as d:
        assert "TASLAK" in [w[4] for w in d[0].get_text("words")] and "TASLAK" in [w[4] for w in d[1].get_text("words")]
    assert (hedef / "C8801_pafta_sablon.png").exists() and (hedef / "C8801_pafta_ozet.json").exists()
    # bayi görseli: plan + çatı planı + iki görünüş (altın koşuda perspektif yok) tek PNG, ≤ 5 MB, plan görselinden uzun
    kart = hedef / "C8801_bayi_gorsel.png"
    assert kart.exists() and kart.stat().st_size <= 5 * 1024 * 1024 and m["bayi_gorsel"] == kart.name and m["bilgi_var"] is False
    from PIL import Image
    with Image.open(kart) as k, Image.open(bayi) as p:
        assert k.width == p.width and k.height > p.height * 1.2
    o = json.loads((hedef / "C8801_pafta_ozet.json").read_text(encoding="utf-8"))
    assert o["kontrol_notlari"] == [] and o["mahal_etiket_cm"]["Yaşam Alanı"][0] > 0     # Ç8801'de 15 cm altı parça yok (rehber, 12.10)


def test_c8801_pafta_olculeri_dis_yuzden_ve_zincir_toplami(c8801):
    # Lokman/rehber 12.10: ölçüler dış yüzden (mühendis planıyla aynı: 1024 × 860, karkas kutusu 1022 × 858 değil); parçaların toplamı genel ölçü
    hedef, m, v = c8801
    o = json.loads((hedef / "C8801_pafta_ozet.json").read_text(encoding="utf-8"))
    assert o["dis_olcu_cm"] == [1024.0, 860.0] and o["oturum_m2"] == 88.06
    for ad, toplam in (("arka", 1024), ("on", 1024), ("sol", 860), ("sag", 860)):
        assert sum(o["zincirler_cm"][ad]) == toplam, (ad, o["zincirler_cm"][ad])
        assert all(p >= 15 for p in o["zincirler_cm"][ad]), (ad, o["zincirler_cm"][ad])   # kısa parçalar komşusuna katılır


def test_kt03_pafta_yuvarlama_iki_yanda_ayni(tmp_path):
    # KT-03 dış ölçü 970,5: yarım yukarı → 971, sol ve sağ zincir aynı toplamı verir; m² brüt oturum (93,81 → 94), ad basılmaz (müşteri projesi)
    from motor.genel import sablon_pafta
    t = json.loads((KOK / "modeller" / "KT03.json").read_text(encoding="utf-8"))
    o = sablon_pafta.pafta_pdf(t, tmp_path, "KT03", is_emri_no="TEST", revizyon=1, set_yolu=SET, yontem="panel")
    assert o["dis_olcu_cm"] == [1045.1, 970.5] and o["oturum_m2"] == 93.81
    assert sum(o["zincirler_cm"]["sol"]) == sum(o["zincirler_cm"]["sag"]) == 971 and sum(o["zincirler_cm"]["on"]) == sum(o["zincirler_cm"]["arka"]) == 1045
    import fitz
    with fitz.open(tmp_path / "KT03_pafta.pdf") as d:
        metin = " ".join(w[4] for p in d for w in p.get_text("words"))
    assert "94" in metin and "kör" not in metin.lower() and "üçüncü" not in metin.lower()


def test_kisa_parcalar_komsusuna_katilir_ve_muhendise_not_duser(tmp_path):
    # D-10 (Lokman 12.10.2026 20:01: "Çelikte 15 cm parça çıkmaz"): Ç8201'in 8 cm (arka/ön, 1094'te) ve 15 cm (sol, 375'te) parçaları
    # zincirde görünmez, kontrol_notlari'na yazılır (rehberin denetimiyle aynı: Ç8201 8 ve 15+15); zincir toplamları genel ölçü
    from motor.genel import sablon_pafta
    t = json.loads((KOK / "modeller" / "C8201.json").read_text(encoding="utf-8"))
    o = sablon_pafta.pafta_pdf(t, tmp_path, "C8201", is_emri_no="TEST", revizyon=1, set_yolu=SET, yontem="panel")
    notlar = {(n["zincir"], n["konum_cm"], n["parca_cm"]) for n in o["kontrol_notlari"]}
    assert notlar == {("arka", 1094.0, 8.0), ("on", 1094.0, 8.0), ("sol", 375.0, 15.0)}, notlar
    assert all("kontrol" in n["not"] for n in o["kontrol_notlari"])
    assert o["zincirler_cm"]["sol"] == [30, 330, 30, 330, 30] and all(p >= 15 for ad in o["zincirler_cm"] for p in o["zincirler_cm"][ad])


def test_kt01_mahal_etiketi_tanimdaki_yerde(tmp_path):
    # Rehberin göz denetimi (12.10): "SALON - MUTFAK" yazısı kapı simgesine biniyordu; tanımdaki etiket_yeri [980, 420] kullanılır
    from motor.genel import sablon_pafta
    t = json.loads((KOK / "modeller" / "KT01.json").read_text(encoding="utf-8"))
    o = sablon_pafta.pafta_pdf(t, tmp_path, "KT01", is_emri_no="TEST", revizyon=1, set_yolu=SET, yontem="panel")
    assert o["mahal_etiket_cm"]["Salon - Mutfak"] == [980.0, 420.0] and o["kontrol_notlari"] == []


def test_ozellik_degeri_once_kuculur_sonra_iki_satir_en_son_uc():
    # Lokman 12.10 14:53: değer kesilmez. Az satır çok satırdan önce: Ç8801'in pencere satırı iki satıra sarılır (ilk satır virgülle biter),
    # üç satır yalnız en küçük boyda da iki satıra sığmayan değerde (KT-02); satırlar hücreye sığar, iki satır satır yüksekliğine sığar
    from motor.genel import sablon_pafta as sp
    gen = sp.OZELLIK[2] - 765.0 - 2
    yuk = (sp.OZELLIK[3] - sp.OZELLIK_BASLIK_ALT) / len(sp.OZELLIK_SIRASI) - 1.6
    pt, sat = sp._sigdir("8 adet (4×120/120, 3×120/180, 1×80/180)", 7.3, 5.2, gen, yuk)
    assert len(sat) == 2 and sat[0].endswith(",") and 5.2 <= pt <= 7.3 and sp._blok(sat, pt)[1] <= yuk, (pt, sat)
    assert sp._sigdir("1 adet (1×60/40)", 7.3, 5.2, gen, yuk) == (7.3, ["1 adet (1×60/40)"])
    # Lokman 13.10: sığmayan satırda önce "1×" önekleri kalkar, sonra iki satıra sarılır; yazı 5 pt'nin altına inmez (ozellik_yazi_pt_mutlak)
    v8 = "8 adet (4×120/120, 3×120/180, 1×80/180)"
    assert sp._sadelestir(v8, True, False) == ["8 adet (4×120/120, 3×120/180, 80/180)"] and sp._sadelestir("11×100/120", True, True) == []
    pt8, sat8 = sp._sigdir(v8, 7.3, 5.2, gen, yuk, 5.0, sp._sadelestir(v8, True, True))
    assert sat8 == ["8 adet (4×120/120,", "3×120/180, 80/180)"] and pt8 >= 5.2, (pt8, sat8)
    v3 = "3 adet (1×80/214, 2×90/214)"                                                          # "1×" kalkınca da tek satıra sığmaz: iki satır, büyük boy
    pt3, sat3 = sp._sigdir(v3, 7.3, 5.2, gen, yuk, 5.0, sp._sadelestir(v3, True, True))
    assert sat3 == ["3 adet (80/214,", "2×90/214)"] and pt3 > 6.0, (pt3, sat3)
    # KT-02: "1×" kalkmış hâliyle 5 pt'de iki/üç satır 14,7 pt'lik satıra sığmaz → son çare (varsayım anahtarı) "adet" sözcüğü kalkar; sayı ve liste aynen
    v5 = "5 adet (1×120/100, 1×120/120, 2×120/180, 1×300/200)"
    pt5, sat5 = sp._sigdir(v5, 7.3, 5.2, gen, yuk, 5.0, sp._sadelestir(v5, True, True))
    assert sat5 == ["5 (120/100, 120/120,", "2×120/180, 300/200)"] and pt5 >= 5.2 and sp._blok(sat5, pt5)[1] <= yuk, (pt5, sat5)
    pt5b, sat5b = sp._sigdir(v5, 7.3, 5.2, gen, yuk, 5.0, sp._sadelestir(v5, True, False))   # adet anahtarı kapalı: 5 pt'de üç satır, kesilmez
    assert pt5b == 5.0 and len(sat5b) == 3 and "".join(sat5b).startswith("5 adet (120/100,"), (pt5b, sat5b)
    for p_, s_ in ((pt, sat), (pt8, sat8), (pt3, sat3), (pt5, sat5)):
        assert all(sp.yazi_eni(x, p_, sp.COMIC) <= gen for x in s_)
