"""İE-13 · Fiyat defteri (`kurallar/fiyat/defter_2026-10.json`) ve liste × fiyat aracı (`araclar/fiyatla.py`).

Defterin biçimi, kişisel veri olmaması, onay kuralı (onaysız fiyat yalnız --oneri ile), pano eni bandı, kg'lı kalem, özet
satırının atlanması, düzeltme ve basit yöntem kıyası. Kör test projelerinin Motor listeleri (`testler/kor/projeler/*/bizim_liste.json`)
defterle fiyatlanır: tutar = miktar × birim fiyat, toplam satırların toplamı.
"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import fiyatla as F  # noqa: E402

DEFTER = KOK / "kurallar" / "fiyat" / "defter_2026-10.json"
KOR = sorted((KOK / "testler" / "kor" / "projeler").glob("*/bizim_liste.json"))
DURUMLAR = {"eşleşti", "bant", "öneri onaylı", "ikinci kaynak", "yedek öneri", "hesap", "kaynakta yok", "yakın", "TK-01 onaylı kalemle aynı"}
BIRIMLER = {"adet", "metre", "m", "kg"}


@pytest.fixture(scope="module")
def defter():
    return json.loads(DEFTER.read_text(encoding="utf-8"))


def _pre(kalem, olcu, adet, grup="1001"):
    return {"grup": grup, "grup_adi": "Panel", "kalem": kalem, "olcu": olcu, "adet": adet, "birim": "adet"}


def test_defter_bicimi(defter):
    assert defter["sema"] == "portman.fiyat_defteri/1"
    assert set(defter["hatlar"]) == {"prefabrik", "celik"}
    for v in defter["kaynaklar"].values():                                      # kısa ad liste ve tarih: çıktının kaynak sütunu
        assert re.search(r"\d{2}\.\d{2}\.\d{4}$", v["kisa"]), v
    for hat, H in defter["hatlar"].items():
        assert H["kalemler"], hat
        for k, g in H["kalemler"].items():
            assert " | " in k, k
            assert g["durum"] in DURUMLAR, (k, g["durum"])
            assert g["birim"] in BIRIMLER, (k, g["birim"])
            assert isinstance(g["onay"], bool), k
            if g["fiyat"] is not None:
                assert g["fiyat"] > 0, k
                assert g["kaynak"] in defter["kaynaklar"], (k, g["kaynak"])
            if g["onay"]:                                       # onaylı fiyat Patron'un verdiği listeden ya da onayladığı öneriden
                assert g["fiyat"] is not None and defter["kaynaklar"][g["kaynak"]]["patron_verdi"], k
        for b in H.get("bantlar") or []:
            assert b["kaynak"] in defter["kaynaklar"]
            for a in b["araliklar"]:
                assert a["en_mm"][0] <= a["en_mm"][1] and a["fiyat"] > 0 and a["dayanak"]


def test_defterde_kisisel_veri_yok():
    """Kaynak dosyalarda kişi adı, telefon, IBAN, T.C. no var; deftere yalnız kalem ve fiyat girer."""
    txt = DEFTER.read_text(encoding="utf-8")
    assert not re.search(r"\b0?5\d{2}[ ]?\d{3}[ ]?\d{2}[ ]?\d{2}\b", txt)     # cep telefonu
    assert not re.search(r"\b0?[2-4]\d{2}[ ]?\d{3}[ ]?\d{2}[ ]?\d{2}\b", txt)  # sabit hat
    assert not re.search(r"\bTR\d{2}[ ]?\d{4}", txt)                         # IBAN
    assert not re.search(r"\b\d{11}\b", txt)                                 # T.C. kimlik no
    assert not re.search(r"[\w.]+@[\w.]+\.\w+", txt)                         # e-posta


def test_birebir_anahtar_ve_onay_kurali(defter):
    pre = defter["hatlar"]["prefabrik"]["kalemler"]
    onayli = next(k for k, g in pre.items() if g["onay"])
    onaysiz = next(k for k, g in pre.items() if not g["onay"] and g["fiyat"] is not None)
    L = {"satirlar": [_pre(*onayli.split(" | "), 3), _pre(*onaysiz.split(" | "), 2)]}
    R = F.fiyatla(L, defter)
    a, b = R["satirlar"]
    assert a["durum"] == "onaylı" and a["tutar"] == round(3 * pre[onayli]["fiyat"], 2)
    assert a["kaynak_adi"] == defter["kaynaklar"][pre[onayli]["kaynak"]]["kisa"]       # kaynak sütununda liste ve tarih
    assert b["tutar"] is None and b["durum"] == "öneri, onay bekliyor"            # fiyat uydurulmaz: onaysız öneri varsayılan olarak girmez
    assert [f["anahtar"] for f in R["ozet"]["fiyatsiz"]] == [onaysiz]
    R2 = F.fiyatla(L, defter, oneri=True)
    assert R2["satirlar"][1]["durum"] == "öneri" and R2["satirlar"][1]["tutar"] == round(2 * pre[onaysiz]["fiyat"], 2)
    assert R2["ozet"]["onerilerle"] == R2["satirlar"][1]["tutar"]


@pytest.mark.parametrize("olcu,fiyat", [
    ("100 × 700 × 2500", 2100),     # 627,5'ten geniş: tam
    ("100 × 627 × 2500", 1050),     # 627,5'e kadar: yarım (Patron 27 Ekim)
    ("100 × 400 × 2500", 1050),
    ("100 × 225 × 2500", 525),
    ("100 × 300 × 2500", None),     # Ekim listesinde 225 ile 340 arası yok: fiyat uydurulmaz
    ("100 × 700 × 2800", None),     # başka yükseklik
])
def test_pano_eni_bandi(defter, olcu, fiyat):
    L = {"satirlar": [_pre("100'lük yapıştırma dolu pano", olcu, 1)]}
    s = F.fiyatla(L, defter)["satirlar"][0]
    assert s["birim_fiyat"] == fiyat, s
    assert s["durum"] == ("onaylı bant" if fiyat else "defterde yok")


def test_bant_onayi_ve_kayitli_anahtar(defter):
    D = copy.deepcopy(defter)
    H = D["hatlar"]["prefabrik"]
    kalem = "100'lük yapıştırma dolu pano"
    H["bantlar"].insert(0, {"kalem": kalem, "kalinlik_mm": 100, "yukseklik_mm": 2800, "kaynak": "EKIM87", "araliklar": [
        {"en_mm": [627.5, 1250], "alt_haric": True, "fiyat": 2300, "onay": False, "dayanak": "deneme"}]})
    H["kalemler"][f"{kalem} | 100 × 1000 × 2500"] = {"fiyat": None, "birim": "adet", "kaynak": None, "kaynak_satir": None,
                                                     "kaynak_kalem": "", "durum": "kaynakta yok", "onay": False, "not": ""}
    L = {"satirlar": [_pre(kalem, "100 × 700 × 2500", 1),      # ilk bant başka yükseklikte: sonraki bant da denenir
                      _pre(kalem, "100 × 700 × 2800", 1),      # onaysız bant
                      _pre(kalem, "100 × 1000 × 2500", 1),     # kendi kaydı fiyatsız: banda düşmez
                      _pre(kalem, "100 × 627.5 × 2500", 1)]}   # noktalı ondalık
    a, b, c, d = F.fiyatla(L, D)["satirlar"]
    assert (a["birim_fiyat"], a["durum"]) == (2100, "onaylı bant")
    assert (b["birim_fiyat"], b["durum"]) == (None, "öneri bant, onay bekliyor")
    assert (c["birim_fiyat"], c["durum"]) == (None, "fiyat yok")
    assert (d["birim_fiyat"], d["durum"]) == (1050, "onaylı bant")
    b2 = F.fiyatla(L, D, oneri=True)["satirlar"][1]
    assert (b2["birim_fiyat"], b2["durum"]) == (2300, "öneri bant")


def test_miktari_olmayan_fiyatli_satir(defter):
    C = defter["hatlar"]["celik"]
    kg_k = next(k for k, g in C["kalemler"].items() if g["birim"] == "kg" and g["fiyat"])
    kalem, boyut = kg_k.split(" | ")
    R = F.fiyatla({"satirlar": [{"grup": "Çelik panel", "kalem": kalem, "boyut": boyut, "adet": 8, "kg": None}]}, defter, oneri=True)
    s, beklenen = R["satirlar"][0], ("onaylı" if C["kalemler"][kg_k]["onay"] else "öneri") + "; kg yok"
    assert s["tutar"] is None and s["durum"] == beklenen                          # onaylı görünmez, eksik olan kg yazılır
    assert [f["durum"] for f in R["ozet"]["fiyatsiz"]] == [beklenen]


def test_celik_kg_ve_toplam_satiri(defter):
    C = defter["hatlar"]["celik"]
    kg_k = next(k for k, g in C["kalemler"].items() if g["birim"] == "kg")
    kalem, boyut = kg_k.split(" | ")
    L = {"satirlar": [
        {"grup": "Çelik panel", "kalem": kalem, "boyut": boyut, "adet": 8, "kg": 650.56},
        {"grup": "Çelik panel", "kalem": C["atla"][0], "boyut": "", "adet": 69, "kg": 2555.07},
    ]}
    assert F.hat_bul(L) == "celik"
    R = F.fiyatla(L, defter, oneri=True)
    assert len(R["satirlar"]) == 1                                               # özet satırı fiyatlanmaz, iki kez sayılmaz
    assert R["satirlar"][0]["tutar"] == round(650.56 * C["kalemler"][kg_k]["fiyat"], 2)


def test_duzeltme_tek_satira(defter):
    L = {"satirlar": [_pre("A", "x", 1), _pre("A", "x", 1), _pre("B", "y", 1)]}
    assert F.duzelt(L, [{"anahtar": "B | y", "adet": 4}], "prefabrik")["satirlar"][2]["adet"] == 4
    assert L["satirlar"][2]["adet"] == 1                                         # liste değişmez
    with pytest.raises(SystemExit):
        F.duzelt(L, [{"anahtar": "A | x", "adet": 2}], "prefabrik")


def test_m2_kiyasi():
    m = F.m2_kiyasi(330000, 80, 5000, esik=15)
    assert m["basit_toplam"] == 400000 and m["fark_yuzde"] == -17.5 and m["uyari"]
    assert not F.m2_kiyasi(390000, 80, 5000, esik=15)["uyari"]
    assert not F.m2_kiyasi(100, 80, 5000)["uyari"]                                # eşik verilmezse uyarı yok


@pytest.mark.parametrize("yol", KOR, ids=[p.parent.name for p in KOR])
def test_kor_listeleri_fiyatlanir(defter, yol):
    L = json.loads(yol.read_text(encoding="utf-8"))
    for oneri in (False, True):
        R = F.fiyatla(L, defter, oneri=oneri)
        assert R["hat"] == "prefabrik"
        top = 0.0
        for s in R["satirlar"]:
            if s["tutar"] is not None:
                miktar = s["kg"] if s["birim"] == "kg" else s["adet"]
                assert s["tutar"] == round(miktar * s["birim_fiyat"], 2)
                assert oneri or s["durum"].startswith("onaylı")
                top += s["tutar"]
        assert R["ozet"]["toplam"] == round(top, 2)
        assert R["ozet"]["fiyatli"] + len(R["ozet"]["fiyatsiz"]) <= R["ozet"]["satir"]
        assert R["ozet"]["fiyatli"] > 0


def test_komut_satiri(tmp_path, capsys):
    yol = KOR[0]
    assert F.main([str(yol), "--oneri", "--alan", "60", "--m2-fiyat", "5000", "--esik", "15",
                   "--json", str(tmp_path / "f.json"), "--excel", str(tmp_path / "f.xlsx")]) == 0
    R = json.loads((tmp_path / "f.json").read_text(encoding="utf-8"))
    assert R["m2"]["basit_toplam"] == 300000 and R["oneri_dahil"]
    assert (tmp_path / "f.xlsx").stat().st_size > 0
    assert "basit yöntem: 60.0 m²" in capsys.readouterr().out
