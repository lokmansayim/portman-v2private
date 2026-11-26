"""D-154 · Mehmet Kapaklı Tek 63 m² (TK-11) teklif formu r02: 14 makas, 454.607,96 TL (hedef örnek; D-28 madde 2 ve 3).

Lokman, 26 Kasım 2026 05:52:33 UTC: "cumbada 2 makas gördüm ana makasın tam önünde 1 tane daha makas var"; 05:56:53 UTC kart
"B: Listeye 1 cumba makası ekle"; 06:14:46 UTC kart "Soru 5: 63 m2 evin 14 makaslı yeni teklif formunu onaylıyor musunuz?" →
"Onaylıyorum, 454.607,96 TL" ("Form kuralın hesabıyla kurulur (363.686,37 × 1,25). Taslaktaki tutar 1 kuruş düşer.").
Girdi depoda: r02 İş Emri (r01 + `cati.cumba_ic_makasi`), 23 Kasım 06:19 CRM anlık görüntüsü, Kasım istisnası, bu eve özel fiyatlar,
form girdisi (tutar yazmaz; kâr %25). Mühürlü r01 formunun hedefi (`test_teklif_formu_iki_sayfa_tk11.py`, 452.301,89 TL) aynen durur.
Kod, eşleme ya da Motor bu formu değiştirirse test kırmızıdır; hedef yalnız Lokman'ın onayıyla yeniden dondurulur (D-02)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pymupdf
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import teklif as TK  # noqa: E402
from araclar import teklif_pdf as TP  # noqa: E402
from motor import dxf_out  # noqa: E402

HEDEF = KOK / "testler" / "teklif_formu" / "TK11_r02" / "TK11_r02_beklenen.json"
R01 = KOK / "testler" / "teklif_formu" / "TK11" / "TK11_beklenen.json"
BAYRAK = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES


@pytest.fixture(scope="module")
def H():
    return json.loads(HEDEF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def C(H, tmp_path_factory):
    g = H["girdi"]
    d = tmp_path_factory.mktemp("tk11_r02") / "c"
    arg = [str(KOK / g["is_emri"]), str(d), "--tavan", g["tavan"], "--crm", str(KOK / g["crm"]), "--istisna", str(KOK / g["istisna"]),
           "--proje-fiyat", str(KOK / g["proje_fiyat"]), "--bayi", str(KOK / g["bayi"]), "--tarih", g["tarih"]]
    assert TK.main(arg + (["--oneri"] if g["oneri"] else [])) == 0
    return d


def test_sayilar(H, C):
    """Malzeme 363.686,37 TL, 136/136 satır fiyatlı; form 454.607,96 TL = malzeme × 1,25, girdide tutar yazmaz; KDV %0."""
    T = json.loads(next(C.glob("*_teklif.json")).read_text(encoding="utf-8"))
    o, b, B = T["secenekler"][0]["fiyat"]["ozet"], T["bayi_formu"], H["beklenen"]
    assert (o["toplam"], o["fiyatli"], o["satir"]) == (B["taban"], B["fiyatli_satir"], B["satir"]) == (363686.37, 136, 136)
    assert (b["birim"], b["toplam"], b["kdv_orani"], b["ekler"]["malzeme_listesi"]) == (B["birim"], B["toplam"], 0, False)
    assert b["ekler"]["sabit_fiyat"] == {"kar_orani": B["kar_orani"], "kdv_orani": 0}
    assert b["birim"] == round(o["toplam"] * (1 + B["kar_orani"]), 2) == 454607.96


def test_tek_fark_bir_cumba_makasi(H, C):
    """Fiyatlı listede cumba makası 2 adet (1.844,86 TL × 2); r01'e göre malzeme farkı tam bir cumba makası."""
    T = json.loads(next(C.glob("*_teklif.json")).read_text(encoding="utf-8"))
    s = [x for x in T["secenekler"][0]["fiyat"]["satirlar"] if x["kalem"].startswith("Cumba makası")]
    assert len(s) == 1 and (s[0]["adet"], s[0]["olcu"], s[0]["birim_fiyat"]) == (H["beklenen"]["cumba_makasi"], "L 4515", 1844.86)
    r01 = json.loads(R01.read_text(encoding="utf-8"))["beklenen"]
    assert round(H["beklenen"]["taban"] - r01["taban"], 2) == s[0]["birim_fiyat"]


def test_iki_sayfa_hedefle_ayni(H, C):
    """Form 2 sayfa; her sayfanın metni hedefle aynı; 2. sayfa Motor'un ön onay paftası; Ek-1 yok. r01'e göre 1. sayfada yalnız
    tarih, revizyon ve tutar değişir."""
    B = H["beklenen"]
    with pymupdf.open(next(C.glob("*_teklif_formu.pdf"))) as d:
        assert d.page_count == B["sayfa"] == 2
        metin = [" ".join(p.get_text(flags=BAYRAK).split()) for p in d]
        ciz2 = len(d[1].get_drawings())
    assert metin == B["sayfa_metni"]
    r01 = json.loads(R01.read_text(encoding="utf-8"))["beklenen"]["sayfa_metni"]
    assert metin[0] == r01[0].replace("23.11.2026", "26.11.2026").replace("PM-TK11-63M2 r01", "PM-TK11-63M2 r02").replace("452.301,89", "454.607,96")
    assert metin[1] == r01[1]
    with tempfile.TemporaryDirectory() as t:
        ie = json.loads((KOK / H["girdi"]["is_emri"]).read_text(encoding="utf-8"))
        with pymupdf.open(Path(t) / dxf_out.uret(ie, t)["pdf"]) as m:
            pafta = len(m[0].get_drawings())
    assert pafta > 1000 and ciz2 == pafta == B["sayfa2_cizim"]


def test_kar_oraniyla_fiyat():
    """`sabit_fiyat` tutar yerine kâr oranı alabilir: birim = taban × (1 + kâr), kuruşa yuvarlı; mühürlü r01'in tutarı da aynı kuraldan.
    İkisi birden, oran 0–1 dışı ya da sayı olmayan değer durur."""
    pazar = TP.fiyatlandirma_oku()["pazarlar"]["yurt_ici"]
    f = TP.sabit_fiyatla(TP.bayi_fiyati(361841.51, pazar), {"kar_orani": 0.25, "kdv_orani": 0})
    assert (f["birim"], f["toplam"], f["kdv"], f["sabit"]) == (452301.89, 452301.89, 0.0, True)
    assert TP.sabit_fiyatla(TP.bayi_fiyati(100, pazar), {"birim": 550000, "kdv_orani": 0})["birim"] == 550000.0      # tutarlı biçim aynen
    for bozuk in ({"kar_orani": 0.25, "birim": 1, "kdv_orani": 0}, {"kar_orani": 25, "kdv_orani": 0}, {"kar_orani": -0.1, "kdv_orani": 0},
                  {"kar_orani": "0.25", "kdv_orani": 0}, {"kar_orani": 0.25}, {"kar_orani": True, "kdv_orani": 0}):
        with pytest.raises(ValueError, match="sabit_fiyat"):
            TP.ekleri_denetle({"sabit_fiyat": bozuk})
    assert TP.ekleri_denetle({"sabit_fiyat": {"kar_orani": 0.25, "kdv_orani": 0}})["sabit_fiyat"]["kar_orani"] == 0.25
