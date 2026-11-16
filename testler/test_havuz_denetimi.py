"""Havuz denetimi (`araclar/havuz_denetimi.py`): havuz listesi, makas sayımı ve bir evde uçtan uca koşu. Araç yalnız okur."""
import json
from pathlib import Path

from araclar import havuz_denetimi as HD

KOK = Path(__file__).resolve().parent.parent


def test_havuz_evleri_tam_ve_tekil():
    evler = HD.havuz_evleri()
    kodlar = [e["kod"] for e in evler]
    assert len(kodlar) == len(set(kodlar))
    assert all(Path(e["yol"]).exists() for e in evler)
    assert {"prefabrik", "genel"} == {e["motor"] for e in evler}
    assert "PA06K" in kodlar and "KT04" in kodlar               # çatı varyantı ve bankanın kabul modeli de havuzda


def test_kart_kodu_kayittan():
    assert HD._kart_kodu({"kaynak": {"kart_kiyasi": {"kart": "AP-05"}}}) == "AP-05"
    assert HD._kart_kodu({"kaynak": {"dosya": "testler/cizim/evler/AP15.json"}}) == "AP-15"
    assert HD._kart_kodu({"kaynak": {}}) is None


def test_makas_sayimi_parca_parca():
    sat = [{"grup": "1005", "kalem": "Makas (baş) · ana çatı", "adet": 2},
           {"grup": "1005", "kalem": "Makas (orta) · ana çatı", "adet": 5},
           {"grup": "1005", "kalem": "Cumba makası · sağ cumba", "adet": 1},
           {"grup": "1005", "kalem": "Çatı paneli (makas arası) · VERANDA çatısı", "adet": 4},
           {"grup": "1002", "kalem": "Baş makas omegası", "adet": 9}]
    assert HD.makas_sayisi(sat) == 8
    assert HD.parca_makaslari(sat) == {"ana çatı": 7, "sağ cumba": 1}


def test_bir_ev_uctan_uca():
    ie = json.loads((KOK / "is_emri" / "adaylar" / "PA11.json").read_text(encoding="utf-8"))
    r = HD.denetle_prefabrik(ie)
    assert not [b for b in r["bulgular"] if b["sinif"] == "hata"], r["bulgular"]
    assert r["makas"] == r["makas_3d"] and r["makas"]
    assert "| PA11 |" in HD.markdown({"PA11": r})
