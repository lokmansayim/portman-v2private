"""D-136 · CRM fiyatı KDV dahil (Lokman 20 Kasım 2026 07:58:30 UTC: "artık fiyatlara ekli yani yeniden KDV hesabı yapmayacağız ...
120 TL lik %20 KDV li bir ürünü artık listede KDV dahil 144 bin değil, KDV dahil 120 bin TL (100+20(kdv)"; kart 08:03:19 UTC
"CRM ve sizin fiyatlarınız"). 20 Kasım 2026'dan sonraki CRM görüntüsünde CRM fiyatı ve Lokman'ın fiyatları (ayın istisnası dahil) KDV
dahildir. 09:10:13 "sen KDV olayını karıştırma CRM'den ne çektiysen onu gir", kart 09:10:41 "KDV hiç yazılmasın": fiyat CRM'deki gibi,
KDV ayrılmaz, eklenmez, yazılmaz; toplam CRM fiyatlarının toplamı.
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
    assert "KDV olayını karıştırma" in f["dayanak"] and "KDV hiç yazılmasın" in f["dayanak"]


def test_baslangictan_onceki_goruntu_aynen(E, A_eski, L):
    D = C.defter_uret(A_eski, E)
    assert "fiyata_dahil" not in D["kdv"] and D["kdv"]["not"].startswith("CRM fiyatı KDV hariç")
    R = F.fiyatla(L, D, "prefabrik")
    assert "fiyat_kdv_dahil" not in R["ozet"] and all("kdv_orani" in s for s in R["satirlar"])
    k = R["ozet"]["kdv"]
    assert k["haric"] == R["ozet"]["toplam"] and k["dahil"] == round(k["haric"] + k["kdv"], 2) and k["kdv"] > 0


def test_baslangictan_sonra_crm_fiyati_aynen_kdv_yok(E, A_eski, A_yeni, L):
    """Aynı fiyatlar: eski görüntüde KDV üstüne eklenir; yenide fiyat ve tutar aynı, KDV hiç yazılmaz. Defterin fiyatı değişmez."""
    De, Dy = C.defter_uret(A_eski, E), C.defter_uret(A_yeni, E)
    # D-147: paketli ürünün (HM44, HM45) CRM fiyatı 20 Kasım'dan beri paket fiyatıdır; aynı sayı yeni görüntüde paketin fiyatı sayılır
    paket = {(h, k) for h, H in E["hatlar"].items() for k, g in H["kalemler"].items() if "paket_fiyati_baslangic" in g}
    ayikla = lambda D: {h: {**H, "kalemler": {k: v for k, v in H["kalemler"].items() if (h, k) not in paket}}   # noqa: E731
                        for h, H in D["hatlar"].items()}
    assert paket and Dy["kdv"]["fiyata_dahil"]["karar"] == "D-136" and ayikla(Dy) == ayikla(De)
    Re, Ry = F.fiyatla(L, De, "prefabrik"), F.fiyatla(L, Dy, "prefabrik")
    assert "kdv" not in Ry["ozet"] and Ry["ozet"]["fiyat_kdv_dahil"] == "D-136"
    assert not any(k in s for s in Ry["satirlar"] for k in ("kdv_orani", "kdv_grubu", "kdv_tutari"))
    for e, y in zip(Re["satirlar"], Ry["satirlar"]):
        if ("prefabrik", f"{e['kalem']} | {e['olcu']}") in paket:
            continue
        assert (e["kalem"], e["adet"], e["birim_fiyat"], e["tutar"]) == (y["kalem"], y["adet"], y["birim_fiyat"], y["tutar"])
    assert Ry["ozet"]["toplam"] == Re["ozet"]["toplam"] == Re["ozet"]["kdv"]["haric"]


def test_lokmanin_ornegi_120_tl(E, A_yeni):
    """120 TL'lik %20 KDV'li ürün listede 120 TL; KDV dahil 120 (144 değil), KDV ayrıca yazılmaz."""
    D = C.defter_uret(A_yeni, E)
    g = D["hatlar"]["prefabrik"]["kalemler"]["100'lük duvar omegası | 100 × 2500"]
    assert g["kdv"] == 0.2
    g["fiyat"] = 120
    L1 = {"satirlar": [{"grup": "1002", "grup_adi": "Metal aksam", "kalem": "100'lük duvar omegası", "olcu": "100 × 2500",
                        "birim": "adet", "adet": 1}]}
    R = F.fiyatla(L1, D, "prefabrik")
    assert (R["satirlar"][0]["birim_fiyat"], R["satirlar"][0]["tutar"], R["ozet"]["toplam"]) == (120, 120.0, 120.0)
    assert "kdv" not in R["ozet"]


def test_lokmanin_fiyatlari_da_aynen(E, A_yeni):
    """Kart "CRM ve sizin fiyatlarınız": ayın istisnasındaki fiyat da KDV dahil, aynen yazılır (karkaslı pencere panosu 4.000 TL)."""
    I = C.istisna_oku(ISTISNA, datetime.date(2026, 11, 20))
    D = C.istisnali_defter(A_yeni, I, E)
    g = D["hatlar"]["prefabrik"]["kalemler"][KARKASLI]
    assert (g["fiyat"], g["kaynak"]) == (4000.0, C.ISTISNA_KAYNAK)
    L1 = {"satirlar": [{"grup": "1001", "grup_adi": "Panel", "kalem": KARKASLI.split(" | ")[0], "olcu": KARKASLI.split(" | ")[1],
                        "birim": "adet", "adet": 1}]}
    s = F.fiyatla(L1, D, "prefabrik")["satirlar"][0]
    assert (s["birim_fiyat"], s["tutar"]) == (4000.0, 4000.0) and "kdv_tutari" not in s


def test_teklif_kdv_yazmaz(E, A_yeni, tmp_path):
    """Teklifin PDF'inde ve Excel'inde KDV yok; toplam CRM fiyatlarının toplamı."""
    import pymupdf
    from openpyxl import load_workbook

    from araclar import teklif as TK
    p = tmp_path / "anlik.json"
    p.write_text(json.dumps(A_yeni, ensure_ascii=False), encoding="utf-8")
    assert TK.main([str(IE_TK04), str(tmp_path / "t"), "--tavan", "asma", "--crm", str(p)]) == 0
    pdf = next((tmp_path / "t").glob("*.pdf"))
    metin = "".join(s.get_text() for s in pymupdf.open(pdf))
    assert "KDV tutarı" not in metin and "KDV dahil" not in metin and "Tutar KDV" not in metin
    hucre = [c for ws in load_workbook(next((tmp_path / "t").glob("*.xlsx"))).worksheets
             for r in ws.iter_rows(values_only=True) for c in r if isinstance(c, str)]
    assert not [c for c in hucre if "KDV" in c]
