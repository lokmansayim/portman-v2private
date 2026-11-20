"""D-136 · CRM fiyatı KDV dahil (Lokman 20 Kasım 2026 07:58:30 UTC: "artık fiyatlara ekli yani yeniden KDV hesabı yapmayacağız ...
120 TL lik %20 KDV li bir ürünü artık listede KDV dahil 144 bin değil, KDV dahil 120 bin TL (100+20(kdv)"; kart 08:03:19 UTC
"CRM ve sizin fiyatlarınız"). 20 Kasım 2026'dan sonraki CRM görüntüsünde CRM fiyatı ve Lokman'ın fiyatları (ayın istisnası dahil) KDV
dahildir: fiyatla satırın fiyatını kaydın oranıyla KDV hariçe çevirir, KDV'yi ekler, KDV dahil toplam listedeki fiyatların toplamıdır.
Önceki görüntülerin defteri ve fiyatlı listesi aynen (D-128 hedef örneği, onaylı teklifler)."""
from __future__ import annotations

import copy
import datetime
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "testler"))

from araclar import crm_fiyat as C  # noqa: E402
from araclar import fiyatla as F  # noqa: E402
from test_crm_fiyat import IE_TK04, kategorili, sahte_anlik  # noqa: E402

ISTISNA = KOK / "kurallar" / "fiyat" / "istisna" / "2026-11_bayi_listesi.json"
KARKASLI = "Karkaslı özel pencere panosu (180/180) | 100 × 2500 × 2500"


@pytest.fixture(scope="module")
def E():
    return C.oku(C.ESLEME)


def _tarihli(A: dict, zaman: str) -> dict:
    B = copy.deepcopy(A)
    B["generated_at"] = zaman
    return C.denetle(B)


@pytest.fixture(scope="module")
def A_eski(E):
    return _tarihli(kategorili(sahte_anlik(E)), "2026-11-19T06:19:53+03:00")


@pytest.fixture(scope="module")
def A_yeni(E):
    return _tarihli(kategorili(sahte_anlik(E)), "2026-11-20T06:19:18+03:00")


@pytest.fixture(scope="module")
def L():
    from motor import prefabrik_liste as PL
    return PL.is_emrinden(json.loads(IE_TK04.read_text(encoding="utf-8")))


def test_esleme_karari(E):
    f = E["kdv"]["fiyata_dahil"]
    assert (f["baslangic"], f["karar"]) == ("2026-11-20", "D-136")
    assert "KDV dahil 120 bin TL (100+20(kdv)" in f["dayanak"] and "CRM ve sizin fiyatlarınız" in f["dayanak"]


def test_baslangictan_onceki_goruntu_aynen(E, A_eski, L):
    D = C.defter_uret(A_eski, E)
    assert "fiyata_dahil" not in D["kdv"] and D["kdv"]["not"].startswith("CRM fiyatı KDV hariç")
    R = F.fiyatla(L, D, "prefabrik")
    assert "fiyata_dahil" not in R["ozet"]["kdv"] and not any("kdv_dahil_birim_fiyat" in s for s in R["satirlar"])
    k = R["ozet"]["kdv"]
    assert k["haric"] == R["ozet"]["toplam"] and k["dahil"] == round(k["haric"] + k["kdv"], 2)


def test_baslangictan_sonra_kdv_icinden_ayrilir(E, A_eski, A_yeni, L):
    """Aynı fiyatlar: eski görüntüde KDV üstüne eklenir, yenide fiyatın içinden ayrılır. Defterin fiyatı değişmez."""
    De, Dy = C.defter_uret(A_eski, E), C.defter_uret(A_yeni, E)
    assert Dy["kdv"]["fiyata_dahil"]["karar"] == "D-136"
    assert Dy["hatlar"] == De["hatlar"]
    Re, Ry = F.fiyatla(L, De, "prefabrik"), F.fiyatla(L, Dy, "prefabrik")
    ky = Ry["ozet"]["kdv"]
    assert ky["fiyata_dahil"] == "D-136" and (ky["oransiz"]["satir"], ky["eksik"]) == (0, False)
    n = 0
    for e, y in zip(Re["satirlar"], Ry["satirlar"]):
        assert (e["kalem"], e["adet"]) == (y["kalem"], y["adet"])
        if y["tutar"] is None:
            assert e["tutar"] is None
            continue
        n += 1
        assert y["kdv_dahil_birim_fiyat"] == e["birim_fiyat"]
        assert y["birim_fiyat"] == round(e["birim_fiyat"] / (1 + y["kdv_orani"]), 6)
        assert y["kdv_tutari"] == round(y["tutar"] * y["kdv_orani"], 2)
        assert abs(y["tutar"] + y["kdv_tutari"] - e["tutar"]) <= 0.011, y["kalem"]   # satırın KDV dahili listedeki tutar (kuruş)
    assert n > 50
    assert ky["haric"] == Ry["ozet"]["toplam"] and ky["dahil"] == round(ky["haric"] + ky["kdv"], 2)
    assert abs(ky["dahil"] - Re["ozet"]["toplam"]) <= 0.01 * n                 # KDV dahil toplam = listedeki fiyatların toplamı
    assert ky["dahil"] < Re["ozet"]["kdv"]["dahil"]


def test_lokmanin_ornegi_120_tl(E, A_yeni):
    """120 TL'lik %20 KDV'li ürün: 100 TL + 20 TL KDV = 120 TL (144 değil)."""
    D = C.defter_uret(A_yeni, E)
    g = D["hatlar"]["prefabrik"]["kalemler"]["100'lük duvar omegası | 100 × 2500"]
    assert g["kdv"] == 0.2
    g["fiyat"] = 120
    L1 = {"satirlar": [{"grup": "1002", "grup_adi": "Metal aksam", "kalem": "100'lük duvar omegası", "olcu": "100 × 2500",
                        "birim": "adet", "adet": 1}]}
    R = F.fiyatla(L1, D, "prefabrik")
    s = R["satirlar"][0]
    assert (s["birim_fiyat"], s["tutar"], s["kdv_tutari"], s["kdv_dahil_birim_fiyat"]) == (100.0, 100.0, 20.0, 120)
    assert (R["ozet"]["kdv"]["haric"], R["ozet"]["kdv"]["kdv"], R["ozet"]["kdv"]["dahil"]) == (100.0, 20.0, 120.0)


def test_lokmanin_fiyatlari_da_kdv_dahil(E, A_yeni):
    """Kart "CRM ve sizin fiyatlarınız": ayın istisnasındaki fiyat da KDV dahil (karkaslı pencere panosu 4.000 TL = 3.333,33 + 666,67)."""
    I = C.istisna_oku(ISTISNA, datetime.date(2026, 11, 20))
    D = C.istisnali_defter(A_yeni, I, E)
    g = D["hatlar"]["prefabrik"]["kalemler"][KARKASLI]
    assert (g["fiyat"], g["kaynak"], g["kdv"]) == (4000.0, C.ISTISNA_KAYNAK, 0.2)
    L1 = {"satirlar": [{"grup": "1001", "grup_adi": "Panel", "kalem": KARKASLI.split(" | ")[0], "olcu": KARKASLI.split(" | ")[1],
                        "birim": "adet", "adet": 1}]}
    s = F.fiyatla(L1, D, "prefabrik")["satirlar"][0]
    assert (s["tutar"], s["kdv_tutari"], s["kdv_dahil_birim_fiyat"]) == (3333.33, 666.67, 4000.0)


def test_teklif_pdf_cumlesi():
    from araclar import teklif_pdf as TP
    k = {"kdv": 20.0, "dahil": 120.0, "oranlar": {"%20": {"oran": 0.2, "matrah": 100.0, "kdv": 20.0, "satir": 1}},
         "oransiz": {"satir": 0, "tutar": 0, "satirlar": []}, "eksik": False}
    assert "Liste fiyatı KDV dahildir" not in TP.kdv_cumlesi(k)
    assert "Liste fiyatı KDV dahildir" in TP.kdv_cumlesi(k | {"fiyata_dahil": "D-136"})
