"""İE-14 PR-3: LLM-önce çelik revizyon okumasının kod denetimi (LLM'siz). LLM'in işlemleri tabloya karşı ayıklanır: tabloda olmayan açıklık,
aralık dışı ya da ondalıklı ölçü (S7), seçenek dışı çatı → uygulanamaz (sessiz düşme ve sessiz yuvarlama yok); iki aday → soru."""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import celik_okuma as CO, degisiklik_okuyucu as DO, varyant  # noqa: E402

T = json.loads((KOK / "modeller" / "C8801K.json").read_text(encoding="utf-8"))
P = CO.pencere_adaylari(T, varyant._kur(T))
CATI = {"Ç8801", "Ç8801K", "Ç8801L"}


def islem(**k):
    return {"tur": k.pop("tur"), "aciklik": None, "adaylar": [], "en": None, "yuk": None, "cati_kodu": None, "alinti": "", **k}


def test_tablo_ve_manuel_cagri():
    m = DO.tablo_metni(P, [{"kod": "Ç8801K", "ad": "x"}], False)
    assert "P5:" in m and "Mutfak" in m and "Dış karkas: 80'lik" in m
    s = DO.oku("mutfak penceresi 120x120 olsun", P, [], False, hazir={"islemler": [islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120)]})
    assert s["durum"] == "tamam" and s["cagri"] == 0 and s["islemler"][0]["aciklik"] == "P5"


def test_gecerli_islemler():
    d = DO.denetle({"islemler": [islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120), islem(tur="dis_karkas_140"),
                                 islem(tur="cati", cati_kodu="Ç8801-L")], "bilgi": ["çatı gri"]}, P, CATI)
    assert [o["op"] for o in d["ops"]] == ["pencere_olcu", "dis_karkas_140", "cati_varyanti"] and d["ops"][2]["kod"] == "Ç8801L"
    assert d["uygulanamaz"] == [] and d["sor"] is None and d["bilgi"] == ["çatı gri"]


def test_tabloda_olmayan_araligi_asan_ondalikli_ve_secenek_disi_uygulanamaz():
    d = DO.denetle({"islemler": [islem(tur="pencere_olcu", aciklik="P99", en=120, yuk=120, alinti="garaj penceresi"),
                                 islem(tur="pencere_olcu", aciklik="P5", en=500, yuk=120, alinti="mutfak 500"),
                                 islem(tur="pencere_olcu", aciklik="P5", en=125, yuk=182.5, alinti="125x182,5"),
                                 islem(tur="cati", cati_kodu="Ç9999", alinti="çatı düz olsun"),
                                 islem(tur="uygulanamaz", alinti="salonu büyütelim")]}, P, CATI)
    assert d["ops"] == [] and len(d["uygulanamaz"]) == 5
    assert any("ondalıklı" in u for u in d["uygulanamaz"]) and "salonu büyütelim" in d["uygulanamaz"]


def test_iki_aday_soru_tek_aday_islem():
    yasam = [p["aciklik"] for p in P if p["mahal"] == "Yaşam Alanı"][:2]
    d = DO.denetle({"islemler": [islem(tur="belirsiz_pencere", adaylar=yasam, en=120, yuk=180)]}, P, CATI)
    assert d["sor"] and [a["aciklik"] for a in d["sor"]["adaylar"]] == yasam and d["sor"]["olcu"] == [120, 180]
    d = DO.denetle({"islemler": [islem(tur="belirsiz_pencere", adaylar=yasam[:1], en=120, yuk=180)]}, P, CATI)
    assert d["sor"] is None and d["ops"][0]["aciklik"] == yasam[0]
