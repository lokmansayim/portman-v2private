"""İE-13 · Fiyat defteri (`kurallar/fiyat/defter_2026-10.json`) ve liste × fiyat aracı (`araclar/fiyatla.py`).

Defterin biçimi, kişisel veri olmaması, onay kuralı (onaysız fiyat yalnız --oneri ile), pano eni bandı, kiriş boy önerisi, kg'lı kalem, özet
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
DURUMLAR = {"eşleşti", "bant", "öneri onaylı", "ikinci kaynak", "yedek öneri", "hesap", "kaynakta yok", "yakın", "TK-01 onaylı kalemle aynı",
            "eşdeğer"}
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
        for b in H.get("boy_onerileri") or []:                  # boy kuralı: onaylıysa Patron'un kuralı (D-36), dayanağında sözü
            assert b["kaynak"] in defter["kaynaklar"] and b["boy_mm"] > 0 and b["fiyat"] > 0 and isinstance(b["onay"], bool) and b["dayanak"]
            assert ("kalem" in b) != ("kalem_baslar" in b) and b.get("yuvarlama", 1) > 0
            if b["onay"]:
                assert defter["kaynaklar"][b["kaynak"]]["patron_verdi"] and "D-36" in b["dayanak"]
        if (m := H.get("makas_kurali")) is not None:           # makas kuralı (D-37): kg makas boyuyla orantılı × kg fiyatı
            assert m["kaynak"] in defter["kaynaklar"] and m["kg_m"] > 0 and m["kg_fiyat"] > 0 and m["sacak_mm"] >= 0
            assert m["kalem_baslar"] and all(b.endswith(" · ") for b in m["kalem_baslar"]) and isinstance(m["onay"], bool)
            if m["onay"]:
                assert defter["kaynaklar"][m["kaynak"]]["patron_verdi"] and "D-37" in m["dayanak"]
            assert not [k for k in H["kalemler"] if any(k.startswith(b) for b in m["kalem_baslar"])]   # kaydı olan anahtar kurala düşmez


def test_defterde_kisisel_veri_yok():
    """Kaynak dosyalarda kişi adı, telefon, IBAN, T.C. no var; deftere yalnız kalem ve fiyat girer."""
    txt = DEFTER.read_text(encoding="utf-8")
    assert not re.search(r"\b0?5\d{2}[ ]?\d{3}[ ]?\d{2}[ ]?\d{2}\b", txt)     # cep telefonu
    assert not re.search(r"\b0?[2-4]\d{2}[ ]?\d{3}[ ]?\d{2}[ ]?\d{2}\b", txt)  # sabit hat
    assert not re.search(r"\bTR\d{2}[ ]?\d{4}", txt)                         # IBAN
    assert not re.search(r"\b\d{11}\b", txt)                                 # T.C. kimlik no
    assert not re.search(r"[\w.]+@[\w.]+\.\w+", txt)                         # e-posta


def test_birebir_anahtar_ve_onay_kurali(defter):
    """Onaylı kalem toplama girer, onaysız öneri yalnız `--oneri` ile. Defter r04'te prefabrik hatta fiyatlı öneri kalmadı (Lokman 28 Ekim
    13:27 TK-01'in önerilerini onayladı); kural, defterin kopyasına konan bir öneri kalemiyle sınanır."""
    defter = copy.deepcopy(defter)
    pre = defter["hatlar"]["prefabrik"]["kalemler"]
    if not any(not g["onay"] and g["fiyat"] is not None for g in pre.values()):
        pre["Deneme önerisi | adet"] = {"fiyat": 150, "birim": "adet", "kaynak": "CTKB", "kaynak_satir": None, "kaynak_kalem": "Deneme",
                                       "durum": "yedek öneri", "onay": False, "not": "test kalemi"}
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


def test_kiris_boy_onerisi(defter):
    """Kaydı olmayan kiriş boyu 6 m tam boyun fiyatından boyla orantılı fiyat alır (tam TL'ye yarım yukarı). Yöntem defterdeki onaylı kiriş
    boylarını aynen verir (Patron 27 Ekim 22:08; 28 Ekim 13:27'de onaylanan 3860, 2610, 1255 dahil). Defter r05'ten beri kural onaylı, her boy
    için (Lokman 31 Ekim 15:25, D-36): yeni boy toplama girer. Onaysız boy kuralının gösterimi (CIO, 28 Ekim: öneri satırda ve özette durur,
    varsayılan toplama girmez) defterin kuralı onaysız kopyasıyla sınanır (r03–r04 hâli)."""
    K = "Kutu profil (kiriş) 100 × 100"
    pre = defter["hatlar"]["prefabrik"]
    onayli = {k.split(" | ")[1]: g["fiyat"] for k, g in pre["kalemler"].items() if k.startswith(K + " | ")}
    assert onayli == {"L 3760": 3133, "L 1710": 1425, "L 2510": 2092, "L 1200": 1000, "L 3860": 3217, "L 2610": 2175, "L 1255": 1046}
    for olcu, fiyat in onayli.items():
        assert F.boy_onerisi_bul(_pre(K, olcu, 1), pre["boy_onerileri"])[1] == fiyat, olcu
    L = {"satirlar": [_pre(K, "L 3960", 1), _pre(K, "L 1355", 2), _pre(K, "L 3760", 1), _pre(K, "100 × 100", 1)]}
    a, b, c, d = F.fiyatla(L, defter)["satirlar"]                # r05: kural onaylı
    assert (a["birim_fiyat"], a["tutar"], a["durum"], b["tutar"], c["durum"], d["durum"]) == (3300.0, 3300.0, "onaylı boy", 2258.0, "onaylı", "defterde yok")
    defter = copy.deepcopy(defter)                              # r03–r04 hâli: kural öneri
    for k in defter["hatlar"]["prefabrik"]["boy_onerileri"]:
        k["onay"] = False
    R = F.fiyatla(L, defter)
    a, b, c, d = R["satirlar"]
    assert (a["birim_fiyat"], a["tutar"], a["durum"], a["oneri_fiyat"]) == (None, None, "öneri boy, onay bekliyor", 3300.0)
    assert (b["oneri_fiyat"], c["durum"], c["tutar"], d["durum"]) == (1129.0, "onaylı", 3133, "defterde yok")   # kaydı olan kendi kaydıyla
    assert "oneri_fiyat" not in c and "oneri_fiyat" not in d
    assert R["ozet"]["toplam"] == 3133 and R["ozet"]["oneri_bekleyen"] == {"satir": 2, "tutar": 3300 + 2 * 1129}
    R2 = F.fiyatla(L, defter, oneri=True)
    assert [x["durum"] for x in R2["satirlar"][:2]] == ["öneri boy"] * 2 and R2["ozet"]["onerilerle"] == 3300 + 2 * 1129
    assert R2["ozet"]["oneri_bekleyen"] == {"satir": 0, "tutar": 0}



@pytest.mark.parametrize("kalem,olcu,fiyat,durum", [
    # iç 100'lük eleman dıştaki 100'lük ile birebir aynı (Lokman 31 Ekim 15:25)
    ("H standart 100 (iç pano eki)", "100 × 100 × 2500", 342.0, "onaylı"),
    ("Çektirme U'su 100 (iç duvar)", "100 × 2440", 148, "onaylı"),
    ("100'lük karkaslı + kasalı pano", "100 × 1250 × 2500", 2200, "onaylı bant"),
    ("100'lük karkaslı + kasalı pano", "100 × 1200 × 2500", 2200, "onaylı bant"),
    ("Karkaslı çelik kapı panosu", "100 × 1150 × 2500", 2200, "onaylı bant"),
    ("Karkaslı çelik kapı panosu", "100 × 1000 × 2500", None, "defterde yok"),        # bandın dışı: fiyat uydurulmaz
    # 100'lük 3'lü H, 60'lık karşılığının fiyatı (15:25)
    ("3'lü H 100 × 100 × 100 (dış duvar T'si)", "L 2500", 427.25, "onaylı"),
    ("3'lü H standart 100 (iç T)", "L 2500", 389, "onaylı"),
    # kutu profil ve tek kat çatı paneli boyla orantılı (15:25, 15:26; panel kuruşa)
    ("Kutu profil (kiriş) 100 × 100", "L 2660", 2217.0, "onaylı boy"),
    ("Özel kutu profil (kolon) 100 × 100", "L 3000", 2500.0, "onaylı boy"),
    ("Tek kat çatı paneli · arka veranda çatısı", "L 1770", 535.87, "onaylı boy"),
    ("Tek kat çatı paneli · yan veranda çatısı", "L 2000", 605.5, "onaylı boy"),
    ("Tek kat çatı paneli · ana çatı", "L 5100", 1544.04, "onaylı"),                   # kaydı olan kendi kaydıyla, yöntem aynı
    # besleme kablo borusu 3 × 2,5 kablonun iki katı, kenar boyası iç cephe boyasının kg fiyatıyla, çırpı ipi boş (15:27)
    ("Besleme kablo borusu", "metre", 140, "onaylı"),
    ("Kenarlar için boya", "10 kg", 2000.0, "onaylı"),
    ("Çırpı ipi", "adet", None, "fiyat yok"),
])
def test_d36_fiyat_kurallari(defter, kalem, olcu, fiyat, durum):
    """D-36 (Lokman 31 Ekim 2026 15:25–15:27): TK-02'nin (iç 100) fiyatsız satırları. Yöntem defterdeki eski fiyatları aynen verir: tek kat
    panel 5100, 2400, 1750; kolon L 2500."""
    s = F.fiyatla({"satirlar": [_pre(kalem, olcu, 1)]}, defter)["satirlar"][0]
    assert (s["birim_fiyat"], s["durum"]) == (fiyat, durum), s
    pre = defter["hatlar"]["prefabrik"]
    for k in ("Tek kat çatı paneli · ön veranda çatısı | L 2400", "Tek kat çatı paneli · arka veranda çatısı | L 1750",
              "Özel kutu profil (kolon) 100 × 100 | L 2500"):
        assert F.boy_onerisi_bul(_pre(*k.split(" | "), 1), pre["boy_onerileri"])[1] == pre["kalemler"][k]["fiyat"], k

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


@pytest.mark.parametrize("kalem,olcu,kg,fiyat", [
    ("Makas (baş) · ana çatı", "açıklık 8985", 52.72, 3110.0),        # TK-01 r07 ve TK-02: 8985 + 2 × 300 = 9585 mm
    ("Makas (orta) · ana çatı", "açıklık 8985", 52.72, 3110.0),
    ("Makas (orta) · ana çatı", "açıklık 8980", 52.69, 3109.0),       # TK-01 İş Emri r05
    ("Yavru makas · ön veranda çatısı", "L 4460", 24.53, 1447.0),     # L saçaktan saçağa, Motor yazar
    ("Yavru makas · arka veranda çatısı", "L 3260", 17.93, 1058.0),
    ("Yavru makas · arka veranda çatısı", "L 3210", 17.66, 1042.0),
    ("Cumba makası · sol cumba", "L 7013", 38.57, 2276.0),            # TK-03'ün cumba makası (İE-24)
    ("Makas (baş) · ana çatı", "açıklık 7392,5", 43.96, 2594.0),      # PK-02: virgüllü ölçü
])
def test_d37_makas_kurali(defter, kalem, olcu, kg, fiyat):
    """D-37 (Lokman 31 Ekim 2026 15:40, kart 16:00 "TK-03 oranı, bütün makaslar"): makasın kg'ı saçaktan saçağa boyuyla orantılı, 87 m²
    listesinin (TK-03) 12 makasından 5,50 kg/m × 59 TL/kg. Satır "onaylı makas kuralı"; teklifin kaynak sütunu da kuralı gösterir."""
    kural = defter["hatlar"]["prefabrik"]["makas_kurali"]
    _, f, k = F.makas_bul(_pre(kalem, olcu, 1, "1005"), kural)
    assert (k, f) == (kg, fiyat)
    s = F.fiyatla({"satirlar": [_pre(kalem, olcu, 2, "1005")]}, defter)["satirlar"][0]
    assert (s["birim_fiyat"], s["tutar"], s["durum"], s["kaynak"]) == (fiyat, 2 * fiyat, "onaylı makas kuralı", "EKIM87"), s


def test_d37_makas_kurali_tk03_ve_sinirlar(defter):
    """Kural kaynağını geri verir: TK-03'ün 12 makası (ana 3 × açıklık 8733, cumba 5 × L 7013 ve 4 × L 7633) 514,76 kg ≈ listedeki
    514,72. Kurala girmeyenler: kubbe makası, makas omegası/Z'si/betopanı, ölçüsü L ya da açıklık olmayan satır. Onaysız kural yalnız --oneri ile."""
    kural = defter["hatlar"]["prefabrik"]["makas_kurali"]
    kg = sum(n * F.makas_bul(_pre(k, o, 1), kural)[2] for k, o, n in [("Makas (baş) · ana çatı", "açıklık 8733", 3),
             ("Cumba makası · sol cumba", "L 7013", 5), ("Cumba makası · sağ cumba", "L 7633", 4)])
    assert round(kg, 2) == 514.76 and abs(kg - 514.72) < 0.1
    for k, o in [("Kubbe makası", "80 × 0,8"), ("Baş makas omegası", "L 2500"), ("Baş makas Z'si", "L 2800"),
                 ("Baş makas betopanı", "1250 × 2500"), ("Makas (baş) · ana çatı", "adet")]:
        assert F.makas_bul(_pre(k, o, 1), kural) is None, (k, o)
    d = copy.deepcopy(defter)
    d["hatlar"]["prefabrik"]["makas_kurali"]["onay"] = False
    s = F.fiyatla({"satirlar": [_pre("Yavru makas · ön veranda çatısı", "L 4460", 3, "1005")]}, d)["satirlar"][0]
    assert (s["birim_fiyat"], s["oneri_fiyat"], s["durum"]) == (None, 1447.0, "öneri makas kuralı, onay bekliyor")
    s = F.fiyatla({"satirlar": [_pre("Yavru makas · ön veranda çatısı", "L 4460", 3, "1005")]}, d, oneri=True)["satirlar"][0]
    assert (s["birim_fiyat"], s["durum"]) == (1447.0, "öneri makas kuralı")


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
