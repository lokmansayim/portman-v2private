"""İE-14 r3 · P4: LLM-önce okuma ↔ celik_okuma kıyası (LLM'siz; kayıtlı cevaplar). Kural okuması karar verir; kıyas yalnız farkı gösterir."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))
from beyin import okuma_kiyas as OK  # noqa: E402
import okuma_kiyas as ARAC  # noqa: E402


def _llm(*islemler, bilgi=()):
    return {"durum": "tamam", "islemler": [{"tur": i[0], "aciklik": i[1] if len(i) > 1 else None, "adaylar": [], "en": i[2] if len(i) > 2 else None,
                                            "yuk": i[3] if len(i) > 3 else None, "cati_kodu": None, "alinti": ""} for i in islemler],
            "bilgi": list(bilgi)}


@pytest.fixture(scope="module")
def b():
    return ARAC._baglam("Ç8801")


@pytest.mark.parametrize("metin,ogeler,okunamayan", [
    ("mutfak penceresi 120x120 olsun", [("pencere", "P5", 120, 120)], 0),
    ("dış duvarlar 140'lık olsun", [("dis140",)], 0),
    ("L olsun", [("cati", "Ç8801L")], 0),
    ("dışlar 140 olmasın", [], 0),                                       # olumsuz: doğru okuma, okunamama değil
    ("mutfak kapısı 90x200 olsun", [], 1),
    ("mutfak penceresi 125x182,5 olsun", [("pencere", "P5", 125, 182)], 0),    # S7 bugünkü davranış (sessiz yuvarlama) ölçülür
])
def test_kural_okumasi_ortak_bicim(b, metin, ogeler, okunamayan):
    k = OK.kural_okumasi(metin, b["t"], b["katalog"], b["y"])
    assert [tuple(x) for x in k["ogeler"]] == ogeler and len(k["okunamayan"]) == okunamayan


def test_sinifla():
    bos, oku = {"ogeler": [], "okunamayan": []}, {"ogeler": [("pencere", "P5", 120, 120)], "okunamayan": []}
    yonl = {"ogeler": [], "okunamayan": ["x"]}
    assert OK.sinifla(oku, oku) == "aynı" and OK.sinifla(bos, bos) == "ikisi_de_bos" and OK.sinifla(yonl, yonl) == "ikisi_de_okuyamadi"
    assert OK.sinifla(bos, oku) == "yalnız_llm" and OK.sinifla(oku, bos) == "yalnız_kural"
    assert OK.sinifla(yonl, bos) == "yalnız_kural" and OK.sinifla(bos, yonl) == "yalnız_llm"
    assert OK.sinifla(oku, {"ogeler": [("pencere", "P6", 120, 120)], "okunamayan": []}) == "farklı"
    assert OK.sinifla(oku, {"ogeler": [], "okunamayan": [], "hata": "ağ"}) == "farklı"


def test_llm_okumasi_kodla_ayiklanir(b):
    l_ = OK.llm_okumasi(_llm(("pencere_olcu", "P5", 120.5, 180)), b["pencereler"], {"Ç8801", "Ç8801K", "Ç8801L"})
    assert l_["ogeler"] == [] and l_["okunamayan"]                       # ondalıklı ölçü sessizce yuvarlanmaz (S7)


def test_cevrimdisi_arac_kayitli_cevaplarla(tmp_path):
    d = tmp_path / "kayit"
    d.mkdir()
    (d / "a.json").write_text(json.dumps({"islemler": [{"tur": "pencere_olcu", "aciklik": "P5", "en": 120, "yuk": 120, "alinti": ""}], "bilgi": []}))
    (d / "b.json").write_text(json.dumps({"islemler": [{"tur": "uygulanamaz", "alinti": "çatı olmasa iyi"}], "bilgi": []}))
    cumleler = [{"id": "a", "model": "Ç8801", "metin": "mutfak penceresi 120x120 olsun"},
                {"id": "b", "model": "Ç8801", "metin": "Ç8801L olmasa iyi olur"},
                {"id": "c", "model": "Ç8801", "metin": "L olsun"}]
    s = ARAC.kos(cumleler, d)
    assert [x["sinif"] for x in s] == ["aynı", "ikisi_de_okuyamadi", "llm_yok"]
    rap = ARAC.rapor(s)
    assert "| aynı | 1 |" in rap and "Hedef yok" in rap


def test_cumle_seti_gecerli_ve_gercek_olmadigi_yazili():
    doc = json.loads((KOK / "testler" / "okuma" / "cumleler.json").read_text(encoding="utf-8"))
    assert "GERÇEK BAYİ CÜMLESİ DEĞİLDİR" in doc["aciklama"] and len(doc["cumleler"]) >= 40
    assert len({c["id"] for c in doc["cumleler"]}) == len(doc["cumleler"])
    s = ARAC.kos(doc["cumleler"])
    assert all(x["sinif"] == "llm_yok" for x in s)                       # LLM'siz: kural okuması baz çizgisi
