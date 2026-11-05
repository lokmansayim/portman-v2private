"""İE-13 · Fiyat defteri r11 (`kurallar/fiyat/defter_2026-11.json`): 45. hafta malzeme listesi (D-62).

Lokman 5 Kasım 2026 23:00 UTC, TK-04 teklif thread'i, 45. hafta listesini (3 Kasım) gönderip: "fiyatları buradan al". 23:10'da karar kartında
yakın eşleşen 28 kalem için "Hepsini al". Yeni liste yeni dosyayla girer (kurallar/fiyat/README.md): araçların varsayılanı r11, eski defter
(r10) eski teklifi aynen verir. Biçim ve kişisel veri denetimi her defterde (`test_fiyat_defteri.py`, `DEFTERLER`).
"""
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import fiyatla as F  # noqa: E402
from araclar import teklif as TK  # noqa: E402

YENI = KOK / "kurallar" / "fiyat" / "defter_2026-11.json"
ESKI = KOK / "kurallar" / "fiyat" / "defter_2026-10.json"
TK04 = KOK / "testler" / "motor" / "veri" / "TK04_r08.json"


@pytest.fixture(scope="module")
def defter():
    return F.oku(YENI)


def _pre(kalem, olcu, adet, grup="1001", **ek):
    return {"grup": grup, "grup_adi": "Panel", "kalem": kalem, "olcu": olcu, "adet": adet, "birim": "adet", **ek}


def test_varsayilan_defter_r11(defter):
    """Araçların (fiyatla, teklif) varsayılanı 45. hafta defteri; eski defter yerinde ve r10."""
    assert F.DEFTER == YENI and defter["surum"] == "2026-11-05-r11" and defter["onceki_defter"].startswith("defter_2026-10.json")
    assert F.oku(ESKI)["surum"] == "2026-11-05-r10"
    k = defter["kaynaklar"]["L45"]
    assert k["patron_verdi"] and k["kisa"] == "45. hafta listesi, 03.11.2026"
    assert '"fiyatları buradan al"' in k["not"] and '"Hepsini al"' in k["not"] and "23:00" in k["not"] and "23:10" in k["not"]
    assert "önce L45" in defter["onay_kurali"]
    assert defter["hatlar"]["celik"] == F.oku(ESKI)["hatlar"]["celik"]                 # çelik hattı değişmedi


def test_tk04_r08_toplami(tmp_path):
    """TK-04 r08 (asma tavan): 45. hafta defteriyle 335.467,98 TL (Patron'a 23:10 kartında söylenen önizleme), r10 defteriyle 374.965,01 TL
    (22:49 kartı). 121 satır, fiyatsız yalnız çırpı ipi (bilerek boş), onay bekleyen öneri yok."""
    for ad, ek, toplam in (("yeni", [], 335467.98), ("eski", ["--defter", str(ESKI)], 374965.01)):
        assert TK.main([str(TK04), str(tmp_path / ad), "--tavan", "asma", "--tarih", "05.11.2026", *ek]) == 0
        T = json.loads((tmp_path / ad / "TK04_teklif.json").read_text(encoding="utf-8"))
        oz = T["secenekler"][0]["fiyat"]["ozet"]
        assert (oz["toplam"], oz["satir"], [f["anahtar"] for f in oz["fiyatsiz"]], oz["oneri_bekleyen"]["satir"]) == \
            (toplam, 121, ["Çırpı ipi | adet"], 0), ad


def test_yakin_eslesmeler_onayli(defter):
    """23:10 "Hepsini al": TK-04'ün yakın eşleşen 28 kalemi L45'ten, onaylı; notunda Patron'un sözü. Aynı kalemin öteki boyu (60'lık karkaslı
    1190) da aynı kayıtla."""
    P = defter["hatlar"]["prefabrik"]["kalemler"]
    yakin = {k for k, g in P.items() if g["durum"] == "yakın"}
    assert len(yakin) == 29 and "60'lık karkaslı + kasalı pano | 60 × 1190 × 2500" in yakin
    for k in yakin:
        assert P[k]["kaynak"] == "L45" and P[k]["onay"] and '"Hepsini al"' in P[k]["not"], k


@pytest.mark.parametrize("anahtar,fiyat,satir", [
    ("100'lük yapıştırma dolu pano | 100 × 1250 × 2500", 2371.09, ["1-A"]),
    ("100'lük yapıştırma dolu pano | 100 × 640 × 2500", 2371.09, ["1-A"]),          # aynı kalemin öteki eni
    ("100'lük yapıştırma dolu pano | 100 × 610 × 2500", 1185.55, ["1-A"]),          # yarım
    ("60'lık karkaslı + kasalı pano | 60 × 1250 × 2500", 2530.50, ["1-E", "8-3"]),
    ("H 100 (dış pano eki) | 100 × 100 × 2500", 299.55, ["3-22", "3-13"]),
    ("H standart 100 (iç pano eki) | 100 × 100 × 2500", 299.55, ["3-22", "3-13"]),  # D-36: iç 100 dıştakiyle aynı
    ("3'lü H standart 100 (iç T) | L 2500", 298.07, ["3-43"]),                         # D-36: 60'lık karşılığı
    ("Özel kutu profil (kolon) 100 × 100 | L 2500", 1205, ["16-3"]),
    ("Kutu profil (kiriş) 100 × 100 | L 3860", 1861, ["16-3"]),                       # 2.892,25 × 3860 / 6000
    ("Prefabrik çelik kapı (SAĞ) | 900 × 2000", 9108, ["18-A"]),
    ("Prefabrik çelik kapı (SOL) | 900 × 2000", 9108, ["18-A"]),
    ("Trapez sac mahyası | L 1000", 167.54, ["12-9"]),
    ("Vitrifiye ve batarya (duş teknesi, klozet, lavabo, batarya grubu) | takım", 8886.05,
     ["22-1", "22-3", "22-4", "22-5", "22-6", "22-7", "22-10", "22-12", "22-24"]),
])
def test_kalem_fiyatlari(defter, anahtar, fiyat, satir):
    g = defter["hatlar"]["prefabrik"]["kalemler"][anahtar]
    assert (g["fiyat"], g["kaynak"], g["kaynak_satir"], g["onay"]) == (fiyat, "L45", satir, True)


def test_eski_kaynakta_kalanlar(defter):
    """45. hafta listesinde karşılığı olmayan ya da henüz eşlenmeyen kalem önceki kaynağında ve fiyatında: makas kuralı, pencere karkası,
    metal tahta, tek kat panel, metal kiremit mahyası."""
    P, E = defter["hatlar"]["prefabrik"], F.oku(ESKI)["hatlar"]["prefabrik"]
    for k in ("Özel pencere karkası (120×180) (100'lük çektirme U'su + 100'lük H geçen) | 1200 × 1800", "Ters mahya kenar kutusu | L 21 × 40 × 21 × 2800",
              "Tek kat çatı paneli · ana çatı | L 5100", "Metal kiremit mahyası | L 2800", "Mahya bandı | rulo 10 m", "Çırpı ipi | adet"):
        assert P["kalemler"][k] == E["kalemler"][k], k
    assert P["makas_kurali"] == E["makas_kurali"]
    tk = [b for b in P["boy_onerileri"] if b.get("kalem_baslar") == "Tek kat çatı paneli · "]
    assert tk == [b for b in E["boy_onerileri"] if b.get("kalem_baslar") == "Tek kat çatı paneli · "]


def test_bant_ve_boy_kurallari(defter):
    """Pano eni bandı listenin pano fiyatıyla (tam, yarım); çeyrek pano listede yok, öneri. Kiriş ve kolon SHS100x4 L 6000 2.892,25'ten,
    trapez sac metresi 299,56 (100 cm kapatır) boy ve kapatmayla orantılı, mahya 167,54 boyla."""
    sac = lambda olcu, kap: _pre("Trapez sac · ana çatı", olcu, 1, "1006", kapatma_m=kap)   # noqa: E731
    L = {"satirlar": [_pre("100'lük yapıştırma dolu pano", "100 × 700 × 2500", 1), _pre("100'lük yapıştırma dolu pano", "100 × 400 × 2500", 1),
                      _pre("100'lük yapıştırma dolu pano", "100 × 225 × 2500", 1), _pre("60'lık yapıştırma dolu pano", "60 × 900 × 2500", 1),
                      _pre("Karkaslı çelik kapı panosu", "100 × 1200 × 2500", 1), _pre("100'lük karkaslı + kasalı pano", "100 × 1170 × 2500", 1),
                      _pre("Kutu profil (kiriş) 100 × 100", "L 5000", 1), sac("L 4900", 1.0), sac("L 2550", 0.8),
                      _pre("Trapez sac mahyası", "L 800", 1, "1006")]}
    R = F.fiyatla(L, defter)
    assert [(s["birim_fiyat"], s["durum"]) for s in R["satirlar"]] == [
        (2371.09, "onaylı bant"), (1185.55, "onaylı bant"), (None, "öneri bant, onay bekliyor"), (1976.32, "onaylı bant"),
        (2856.79, "onaylı bant"), (2856.79, "onaylı bant"), (2410, "onaylı boy"), (1467.84, "onaylı boy"), (611.1, "onaylı boy"),
        (134.03, "onaylı boy")]
    assert F.fiyatla(L, defter, oneri=True)["satirlar"][2]["birim_fiyat"] == 592.77


def test_tk05_hesaplari_yeni_tabandan(defter):
    """TK-05'in r10'da 250'lik tabandan hesaplanan 280 / 160 kalemleri (BK-25): yöntem aynı (280 = 250 × 1,12; 160 = 100'lük + strafor farkı),
    taban 45. hafta fiyatı; Patron onayı bekleyen öneri kalır. Listede birebir olan 160 / 280 profilleri değişmez."""
    P, E = defter["hatlar"]["prefabrik"]["kalemler"], F.oku(ESKI)["hatlar"]["prefabrik"]["kalemler"]
    eps = (1265.73 - 723.28) / 3.5
    hesap = {"100'lük yapıştırma dolu pano | 100 × 1250 × 2800": 2371.09 * 1.12, "100'lük yapıştırma dolu pano | 100 × 625 × 2800": 1185.55 * 1.12,
             "100'lük karkaslı + kasalı pano | 100 × 1170 × 2800": 2856.79 * 1.12,
             "160'lık yapıştırma dolu pano | 160 × 1250 × 2800": 2371.09 * 1.12 + eps * 3.5,
             "160'lık yapıştırma dolu vasistaslı pano (60/40) | 160 × 1250 × 2800": 2483.81 * 1.12 + eps * 3.26,
             "Karkaslı çelik kapı panosu | 160 × 1250 × 2800": 2856.79 * 1.12 + eps * (3.5 - 0.95 * 2.05),
             "Pencere alt panel (120/120) | 160 × 1250 × 900": 1069.74 * 1.125 + eps * 1.125,
             "Pencere alt panel (120/180) | 160 × 1250 × 300": 267.43 * 1.5 + eps * 0.375,
             "Pencere üst panel | 160 × 1250 × 700": 668.58 * 1.4 + eps * 0.875}
    for a, f in hesap.items():
        assert P[a]["fiyat"] == pytest.approx(f, abs=0.006) and P[a]["onay"] is False and P[a]["durum"] == "hesap" and P[a]["kaynak"] == "L45", a
    for a in ("16'lık köşe direği 160 × 160 | 160 × 160 × 2800", "Çektirme U'su 160 | 160 × 2740", "H 160 (dış pano eki) | 160 × 160 × 2800",
              "160'lık alt çerçeve | 160 × 3750", "Özel pencere karkası (120×120) (160'lık çektirme U'su + 160'lık H geçen) | 1200 × 1200"):
        assert P[a] == E[a], a
