"""D-120 · ayın istisnası (Lokman 16 Kasım 2026 21:13:11 UTC kartı "Bu ay istisna"): CRM'in fiyat vermediği yere Lokman'ın listesinden
fiyat. CRM fiyatı ezilmez; dosya kendi ayının dışında kullanılmaz; `fiyatla.defter_sec` (M-15) değişmez. D-119 çeyrek boy kuralı kutu
profilde istisna fiyatıyla da işler."""
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
from test_crm_fiyat import sahte_anlik  # noqa: E402

ISTISNA = KOK / "kurallar" / "fiyat" / "istisna" / "2026-11_bayi_listesi.json"
GUN = datetime.date(2026, 11, 16)
PENCERE = "PVC pencere | 120/120"
VASISTASLI = "100'lük yapıştırma dolu vasistaslı pano (60/40) | 100 × 1250 × 2500"


@pytest.fixture(scope="module")
def E():
    return C.oku(C.ESLEME)


@pytest.fixture(scope="module")
def A0(E):
    """Sahte anlık görüntü; kutu profil kodları (MA11, MA12) bugünkü CRM gibi 0 TL."""
    A = sahte_anlik(E)
    for x in A["data"]:
        if x["urunkodu"] in ("MA11", "MA12"):
            x["fiyat"] = 0
    return C.denetle(A)


@pytest.fixture(scope="module")
def I():
    return C.istisna_oku(ISTISNA, GUN)


def test_dosya_kendi_ayinda(I):
    assert I["karar"] == "D-120" and I["gecerli"] == {"bas": "2026-11-01", "bit": "2026-11-30"}
    for gun in (datetime.date(2026, 10, 31), datetime.date(2026, 12, 1)):
        with pytest.raises(C.CrmHatasi, match="yalnız CRM"):
            C.istisna_oku(ISTISNA, gun)


def test_istisna_yalniz_crm_fiyati_olmayan_yerde(A0, E, I):
    D0 = C.defter_uret(A0, E)
    D = C.istisnali_defter(A0, I, E)
    P0, P = D0["hatlar"]["prefabrik"]["kalemler"], D["hatlar"]["prefabrik"]["kalemler"]
    for k in (PENCERE, VASISTASLI, "Kutu profil (kiriş) 100 × 100 | L 3760"):
        assert P0[k]["fiyat"] is None, k
    g = P["Kutu profil (kiriş) 100 × 100 | L 3760"]                 # 2.892,25 × 3/4 (D-119), tam TL
    assert (g["fiyat"], g["kaynak"], g["onay"], g["durum"], g["istisna"]) == (2169.0, "ISTISNA", True, "Lokman istisnası", "D-120")
    assert P["Özel kutu profil (kolon) 100 × 100 | L 2500"]["fiyat"] == 1446.0
    assert (P[PENCERE]["fiyat"], P[PENCERE]["kaynak"], P[PENCERE]["kdv"]) == (6500.0, "ISTISNA", 0.2)
    assert (P[VASISTASLI]["fiyat"], P[VASISTASLI]["kdv"], P[VASISTASLI]["kdv_grubu"]) == (2483.81, 0.2, "Yapıştırma pano")
    for k, g in P.items():                                         # CRM'in verdiği her fiyat aynen
        if P0[k]["fiyat"] is not None:
            assert (g["fiyat"], g["kaynak"]) == (P0[k]["fiyat"], P0[k]["kaynak"]), k
    g = P["Özel pencere karkası (120×120) (100'lük çektirme U'su + 100'lük H geçen) | 1200 × 1200"]   # Lokman 21:34:47: gerçek adı
    assert (g["fiyat"], g["teklif_adi"], g["teklif_olcu"], g["kdv"]) == (237.08, "PENCERE KÖR KASASI", "120/120", 0.2)
    assert D["istisna"]["kod"] == ["MA11", "MA12"] and D["istisna"]["crm_fiyatli_kod"] == []
    assert "ISTISNA" in D["kaynaklar"] and D["surum"].endswith("+ istisna D-120")
    assert "Şase pul" in D["hatlar"]["prefabrik"]["atla"] and "Şase pul" in D["hatlar"]["celik"]["atla"]   # Lokman 21:35:12
    assert "Şase pul" not in D0["hatlar"]["prefabrik"]["atla"]


def test_crm_fiyati_varsa_istisna_uygulanmaz(E, I):
    A = C.denetle(sahte_anlik(E))                                  # MA11, MA12 fiyatlı
    J = copy.deepcopy(I)
    D0, D = C.defter_uret(A, E), C.istisnali_defter(A, J, E)
    k = "Kutu profil (kiriş) 100 × 100 | L 3760"
    assert D["hatlar"]["prefabrik"]["kalemler"][k] == D0["hatlar"]["prefabrik"]["kalemler"][k]
    assert D["istisna"]["kod"] == [] and D["istisna"]["crm_fiyatli_kod"] == ["MA11", "MA12"]
    D0p = copy.deepcopy(D0)                                        # kalem CRM'de fiyatlıysa da ezilmez
    J["kalemler"]["prefabrik"]["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"] = {"fiyat": 1.0, "birim": "adet", "dayanak": "deneme"}
    D = C.istisnali_defter(A, J, E)
    assert D["hatlar"]["prefabrik"]["kalemler"]["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"] == \
        D0p["hatlar"]["prefabrik"]["kalemler"]["100'lük yapıştırma dolu pano | 100 × 1250 × 2500"]
    assert D["istisna"]["crm_fiyatli_kalem"] == ["prefabrik › 100'lük yapıştırma dolu pano | 100 × 1250 × 2500"]


def test_bicim_denetimi(tmp_path, I):
    for bozuk in ({"karar": None}, {"gecerli": {"bas": "2026-11-01"}}, {"kod_fiyatlari": {"MA11": {"fiyat": 0, "dayanak": "x"}}},
                  {"kalemler": {"prefabrik": {PENCERE: {"fiyat": 1, "birim": "adet"}}}},
                  {"kalemler": {"prefabrik": {PENCERE: {"fiyat": 1, "birim": "adet", "dayanak": "x", "kdv_grubu": "yok"}}}}):
        p = tmp_path / "b.json"
        p.write_text(json.dumps(dict(I, **bozuk), ensure_ascii=False), encoding="utf-8")
        with pytest.raises(C.CrmHatasi):
            C.istisna_oku(p, GUN)


def test_istisna_defterle_verilmez_ve_crm_ister(tmp_path):
    with pytest.raises(SystemExit, match="--crm"):
        F.istisnali_defter_sec(None, ISTISNA, GUN)
    with pytest.raises(SystemExit):
        F.main([str(tmp_path / "liste.json"), "--defter", "x.json", "--istisna", str(ISTISNA)])


def test_180_pencere_istisnasi(A0, E, I):
    """85 m² katalog evi (P8501): 180/180 pencereli pano ve PVC pencere CRM'de yok; Kasım fiyatı 45. hafta listesinden (Lokman 17 Kasım 2026
    05:49:59 UTC kartı "Girsin, kenar kutusu boş"). Ters mahya kenar kutusu fiyatsız kalır."""
    D0, D = C.defter_uret(A0, E), C.istisnali_defter(A0, I, E)
    P0, P = D0["hatlar"]["prefabrik"]["kalemler"], D["hatlar"]["prefabrik"]["kalemler"]
    pano, pencere = "Karkaslı özel pencere panosu (180/180) | 100 × 2500 × 2500", "PVC pencere | 180/180"
    assert P0[pano]["fiyat"] is None and P0[pencere]["fiyat"] is None
    assert (P[pano]["fiyat"], P[pano]["kaynak"], P[pano]["kdv"]) == (4000.0, "ISTISNA", 0.2)       # 19 Kasım 19:04:33: karkaslı pano tek fiyat
    assert (P[pencere]["fiyat"], P[pencere]["kaynak"], P[pencere]["kdv"]) == (8993.0, "ISTISNA", 0.2)
    assert P["Ters mahya kenar kutusu | L 21 × 40 × 21 × 2800"]["fiyat"] is None


def test_120_150_kor_kasa_istisnasi(A0, E, I):
    """76 m² Nimet Doğan teklifi: 120/150 kör kasası CRM'de yok; Kasım fiyatı 120/180 kör kasasınınki (Lokman 17 Kasım 2026 09:39:41 UTC:
    "pencere kör kasasına 120/180 ne kadar aynı fiyatı ver sonucu çok etkilemiyor")."""
    D0, D = C.defter_uret(A0, E), C.istisnali_defter(A0, I, E)
    P0, P = D0["hatlar"]["prefabrik"]["kalemler"], D["hatlar"]["prefabrik"]["kalemler"]
    k150 = "Özel pencere karkası (120×150) (100'lük çektirme U'su + 100'lük H geçen) | 1200 × 1500"
    k180 = "Özel pencere karkası (120×180) (100'lük çektirme U'su + 100'lük H geçen) | 1200 × 1800"
    assert P0[k150]["fiyat"] is None
    assert (P[k150]["fiyat"], P[k150]["kaynak"]) == (P[k180]["fiyat"], "ISTISNA") == (297.72, "ISTISNA")


def test_karkasli_pencere_panosu_tek_fiyat(A0, E, I):
    """Karkaslı özel pencere panosu (251 × 250 cm) pencere ölçüsünden bağımsız tek fiyat, şimdilik 4.000 TL (Lokman 19 Kasım 2026 19:04:33
    UTC: "ister 140/150 olsun ister 180/180 olsun aynı fiyat olacak fiyatı şimdilik 4000 TL gir"). 2800 ve 3000 boyu ile fugalı aynen."""
    D0, D = C.defter_uret(A0, E), C.istisnali_defter(A0, I, E)
    P0, P = D0["hatlar"]["prefabrik"]["kalemler"], D["hatlar"]["prefabrik"]["kalemler"]
    for olcu in ("150/140", "160/180", "180/150", "180/180"):
        k = f"Karkaslı özel pencere panosu ({olcu}) | 100 × 2500 × 2500"
        assert P0[k]["fiyat"] is None and (P[k]["fiyat"], P[k]["kaynak"], P[k]["kdv"]) == (4000.0, "ISTISNA", 0.2), k
    assert P["Karkaslı özel pencere panosu (150/180) | 100 × 2500 × 2800"]["fiyat"] is None
