"""BK-25 (D-60): 160'lık dış duvarda profiller de 160'lık; 280 yükseklikte çektirme U'su ve iniş borusu boyla birlikte.

Lokman, 5 Kasım 2026 12:42 (TK-05, karar kartı "160'lık dış duvarda profiller de 160'lık sayılsın mı?"): "Evet, hepsi 160'lık" (köşe
direği, H, üçlü H, alt çerçeve, pencere U'su ve saçak omegası dış duvarda 160'lık; yeri ve adedi aynı). 12:44: "hem 160'lık hemde 280
gözden kaçmasın teyit edeceğim çatı sacı makaslar pencereler falan aynı standartta".

Seçenek yalnız İş Emri'nin `yapi.duvar_kalinligi_cm` {dis 16} anahtarıyla (D-12) açılır; anahtarsız 250'lik İş Emri bayt bayt eski
yoldan gider (TK-02 burada, PK-01 ve öteki altınlar kendi testlerinde). 280'lik her evde çektirme U'su ve iniş borusu boyla (AP-28 dahil).
160'lık dış duvarlı verandalı ya da çok parçalı çatı kapsam dışıdır: Motor saçak omegasını kirişin üstündekinden ayıramadığı için o satır
eski adıyla (100'lük) sayılır ve satırda uyarı yazar (Lokman'a sorulur); öteki profiller 160'lık."""
import json
from collections import Counter
from pathlib import Path

import pytest

from motor import geometry as G
from motor import prefabrik_liste as PL

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "motor" / "veri"
OZ = {"Çatı Şekli": "Beşik", "Çatı Kaplaması": "Sandviç Panel", "Çatı Kaplama Rengi": "Antrasit Gri", "Tavan": "Asma"}


def _oku(ad: str) -> dict:
    return json.loads((VERI / ad).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _durum_temiz():
    """Lento ve kalınlık modül durumudur: her testten sonra varsayılana döner (BK-23 testi gibi)."""
    yield
    G.lento_ayarla({})


@pytest.fixture(scope="module")
def tk05():
    ie = _oku("TK05_r06.json")
    ie["ozellikler"] = dict(OZ)
    L = PL.is_emrinden(ie)
    G.lento_ayarla({})
    return {(s["kalem"], s["olcu"]): s["adet"] for s in L["satirlar"]}


def test_dis_duvar_profilleri_160lik(tk05):
    """TK-05 r06 (müşterinin seçtiği plan, Lokman 11:51): dış duvarın her profili 160'lık adla ve ölçüyle; iç duvarınki 100'lük."""
    beklenen = {("16'lık köşe direği 160 × 160", "160 × 160 × 2800"): 4, ("10'luk köşe direği 100 × 100", "100 × 100 × 2800"): 1,
                ("H 160 (dış pano eki)", "160 × 160 × 2800"): 11, ("H standart 100 (iç pano eki)", "100 × 100 × 2800"): 2,
                ("3'lü H 160 × 160 × 100 (dış duvar T'si)", "L 2800"): 2, ("Çektirme U'su 160", "160 × 2740"): 2,
                ("160'lık pencere U'su H geçen", "L 2500"): 1, ("160'lık saçak omegası", "160 × 2500"): 5,
                ("160'lık alt çerçeve", "160 × 3750"): 5, ("100'lük alt çerçeve", "100 × 3750"): 2}
    assert {k: tk05.get(k) for k in beklenen} == beklenen
    adlar = " ".join(k for k, _ in tk05)
    assert "H 100 (dış pano eki)" not in adlar and "100'lük saçak omegası" not in adlar and "Çektirme U'su 100 |" not in adlar
    assert ("Özel pencere karkası (120×120) (160'lık çektirme U'su + 160'lık H geçen)", "1200 × 1200") in tk05


def test_280_boylari(tk05):
    """280'de çektirme U'su 2740 (kitabın 244'ü standart 250'de; 45. hafta listesi 2440 / 2740 / 2940) ve iniş borusu 2000 + 2 × 500 ≥ 2800."""
    assert tk05[("Çektirme U'su 160", "160 × 2740")] == 2 and tk05[("Çektirme U'su 100 (iç duvar)", "100 × 2740")] == 0
    assert not [k for k in tk05 if "2440" in k[1]]
    assert tk05[("70 mm PVC dere iniş borusu", "L 500")] == 2 * tk05[("70 mm PVC dere iniş borusu", "L 2000")]


def test_anahtarsiz_ve_250_eski_adlar():
    """Anahtarsız İş Emri (TK-02, 250): adlar ve ölçüler eskisi gibi; 160 hiçbir satırda yok, iniş borusunda tek L 500."""
    L = PL.is_emrinden(_oku("TK02.json"))
    k = Counter((s["kalem"], s["olcu"]) for s in L["satirlar"])
    assert k[("H 100 (dış pano eki)", "100 × 100 × 2500")] and k[("Çektirme U'su 100", "100 × 2440")] and k[("100'lük saçak omegası", "100 × 2500")]
    assert not [s for s in L["satirlar"] if "160" in s["kalem"] or "160 ×" in s["olcu"]]
    a = {(s["kalem"], s["olcu"]): s["adet"] for s in L["satirlar"]}
    assert a[("70 mm PVC dere iniş borusu", "L 500")] == a[("70 mm PVC dere iniş borusu", "L 2000")]


def test_160_verandali_saçak_omegasi_uyarili():
    """TK-05 r07 (giriş nişi, veranda türü): saçak omegası satırı 100'lük ve uyarılı; dış duvarın öteki profilleri 160'lık; TK-05 r06'da uyarı yok."""
    ie = _oku("TK05_r07.json")
    ie["ozellikler"] = dict(OZ)
    L = PL.is_emrinden(ie)
    so = [s for s in L["satirlar"] if "saçak omegası" in s["kalem"]]
    assert [(s["kalem"], s["olcu"]) for s in so] == [("100'lük saçak omegası", "100 × 2500")] and so[0]["formul"].startswith("UYARI (BK-25)")
    adlar = {s["kalem"] for s in L["satirlar"]}
    assert {"16'lık köşe direği 160 × 160", "H 160 (dış pano eki)", "160'lık alt çerçeve"} <= adlar


def test_160_tek_govde_uyarisiz(tk05):
    assert ("160'lık saçak omegası", "160 × 2500") in tk05 and ("100'lük saçak omegası", "100 × 2500") not in tk05


def test_280_ust_100luk_ev_ap28():
    """AP-28 (dış 100, iç 60, 280; kör proje): çektirme U'su 60 × 2740, iniş borusu iki L 500 (BK-25 öncesi 2440 ve bir L 500: 280'lik
    duvarda kısa kalıyordu). Öteki satırların adı ve ölçüsü 100'lük."""
    L = PL.is_emrinden(json.loads((KOK / "testler" / "kor" / "projeler" / "AP28" / "is_emri.json").read_text(encoding="utf-8")))
    a = {(s["kalem"], s["olcu"]): s["adet"] for s in L["satirlar"]}
    assert [k for k in a if k[0].startswith("Çektirme U'su 60")] == [("Çektirme U'su 60", "60 × 2740")]
    assert a[("70 mm PVC dere iniş borusu", "L 500")] == 2 * a[("70 mm PVC dere iniş borusu", "L 2000")]
    assert not [k for k in a if "160'lık" in k[0] or "16'lık" in k[0] or k[1].startswith("160 ×")]
