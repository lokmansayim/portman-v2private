"""İE-08 8a PR-2b (A4) · `beyin/celik_okuma`: bayinin kendi sözünden pencere/çatı/dış 140 okuması (K18, K21). Motor ve Postgres yok."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import celik_okuma as CO  # noqa: E402

C8801 = json.loads((KOK / "modeller" / "C8801.json").read_text(encoding="utf-8"))
C8201 = json.loads((KOK / "modeller" / "C8201.json").read_text(encoding="utf-8"))
KATALOG = {"kod": "Ç8801", "varyantlar": ["Ç8801K", "Ç8801L"]}


def adlar(r):
    return [a["aciklik"] for a in (r["pencere"] or {}).get("adaylar", [])]


@pytest.mark.parametrize("metin, aciklik, olcu", [
    ("mutfak penceresi 120x120 olsun", ["P5"], (120, 120)),
    ("Mutfağın penceresini 120 x 180 yapalım", ["P5"], (120, 180)),
    ("banyo vasistası 60/60 olsun", ["P7"], (60, 60)),
    ("holdeki pencere 120x180", ["P2"], (120, 180)),
    ("yaşam alanı penceresi 160x120", ["P1", "P3", "P4"], (160, 120)),              # 3 aday → numaralı soru
    ("salondaki sol taraftaki pencere 120x180 olsun", ["P3", "P4"], (120, 180)),   # oda + cephe: 2 aday → görselli soru
    ("salon ön cephedeki pencere 160x180", ["P1"], (160, 180)),
    ("yatak odası 2 penceresi 120x180", ["P8", "P9"], (120, 180)),
    ("ikinci yatak odasının sağ cephedeki penceresi 120x180", ["P8"], (120, 180)),
    ("1. yatak odası penceresi 120x180", ["P6"], (120, 180)),
    ("yatak odası penceresi 120x180", ["P6", "P8", "P9"], (120, 180)),            # iki yatak odası: 3 aday
    ("salon 120x120 olan pencere 120x180 olsun", ["P3", "P4"], (120, 180)),       # eski ölçü süzgeci
    ("salonda 120x180 yerine 160x180", ["P1"], (160, 180)),
    ("arka cephedeki pencere 120x120 olsun", ["P5"], (120, 120)),
])
def test_pencere_okumasi(metin, aciklik, olcu):
    r = CO.oku(metin, C8801, KATALOG)
    assert r["istek"] and r["pencere"] and not r["pencere"]["olumsuz"], r
    assert adlar(r) == aciklik and r["pencere"]["olcu"] == olcu, (adlar(r), r["pencere"]["olcu"])
    assert r["cati"] is None and r["dis140"] is False


def test_pencere_olcu_yok_ve_oda_yok():
    r = CO.oku("mutfak penceresini büyütelim", C8801, KATALOG)
    assert r["pencere"]["olcu"] is None and adlar(r) == ["P5"]
    r = CO.oku("kiler penceresi 120x120", C8801, KATALOG)                   # odası yok: aday 0, süzgeç yok → bütün pencereler (soru)
    assert r["pencere"]["olcu"] == (120, 120) and r["pencere"]["mahaller"] == [] and len(adlar(r)) == 9
    r = CO.oku("mutfak 60x40 olsun", C8801, KATALOG)                           # "pencere" sözü yok ama ölçü ve oda var
    assert adlar(r) == ["P5"] and r["pencere"]["olcu"] == (60, 40)
    assert CO.oku("sevk adresi Deneme İlçesi olsun", C8801, KATALOG)["istek"] is False


def test_olumsuz_ve_soru_belirsiz():
    assert CO.oku("mutfak penceresi 120x120 olmasın", C8801, KATALOG)["pencere"]["olumsuz"] is True
    assert CO.oku("mutfak penceresi 120x120 olur mu?", C8801, KATALOG)["pencere"]["olumsuz"] is True
    assert CO.oku("mutfak penceresi 120x120 olsun", C8801, KATALOG)["pencere"]["olumsuz"] is False
    r = CO.oku("mutfağa bir pencere daha ekleyin 120x120", C8801, KATALOG)
    assert r["pencere"]["ekle_kaldir"] is False and r["pencere"]["olcu"] == (120, 120)     # ölçü varken ekleme sözü kural katmanına kalır (B1 gibi sorulmaz; tek pencere değişir)
    assert CO.oku("mutfağa bir pencere daha ekleyin", C8801, KATALOG)["pencere"]["ekle_kaldir"] is True


def test_cati_ve_dis140():
    assert CO.oku("çatı L olsun", C8801, KATALOG)["cati"] == "Ç8801L"
    assert CO.oku("Ç8801K", C8801, KATALOG)["cati"] == "Ç8801K"
    assert CO.oku("katalog çatısı kalsın", C8801, KATALOG)["cati"] == "Ç8801"
    for s in ("dışlar 140'lık olsun", "dış duvarlar 140 olsun", "dış karkas 140'lık", "dışlar 14'lük olsun", "140'lık dış duvar istiyoruz"):
        assert CO.oku(s, C8801, KATALOG)["dis140"] is True, s
    assert CO.oku("dışlar 140 olmasın", C8801, KATALOG)["dis140"] is False
    assert CO.oku("iç duvarlar 140 olsun", C8801, KATALOG)["dis140"] is False
    r = CO.oku("çatı K olsun, dışlar 140'lık, mutfak penceresi 120x120", C8801, KATALOG)
    assert r["cati"] == "Ç8801K" and r["dis140"] and adlar(r) == ["P5"]


def test_cephe_yuzlerden_ve_c8201():
    from motor.genel import yapi
    y = yapi.kur(C8801)
    ad = {a["aciklik"]: a["cephe"] for a in CO.pencere_adaylari(C8801, y)}
    assert ad == {"P1": "on", "P2": "on", "P3": "sol", "P4": "sol", "P5": "arka", "P6": "sag", "P7": "sag", "P8": "sag", "P9": "on"}
    assert {a["aciklik"]: a["cephe"] for a in CO.pencere_adaylari(C8801)} == ad                    # ortaya göre tahmin aynı (motor yokken)
    r = CO.oku("yaşam alanının sağdaki penceresi 180x120", C8201, {"kod": "Ç8201", "varyantlar": []})
    assert adlar(r) == ["P6", "P7", "P8"]


@pytest.mark.parametrize("metin, bekleyen, cevap", [
    ("1", {"tur": "secim", "adaylar": [1, 2]}, {"secim": 0}), ("2", {"tur": "secim", "adaylar": [1, 2]}, {"secim": 1}),
    ("ikinci", {"tur": "secim", "adaylar": [1, 2]}, {"secim": 1}), ("1 olsun", {"tur": "secim", "adaylar": [1, 2]}, {"secim": 0}),
    ("3", {"tur": "secim", "adaylar": [1, 2]}, None), ("hiçbiri", {"tur": "secim", "adaylar": [1, 2]}, {"hicbiri": True}),
    ("ikisi de değil", {"tur": "secim", "adaylar": [1, 2]}, {"hicbiri": True}), ("mutfak penceresi 120x120 olsun", {"tur": "secim", "adaylar": [1, 2]}, None),
    ("120x120", {"tur": "olcu", "adaylar": [1]}, {"olcu": (120, 120)}), ("vazgeçtim, yok", {"tur": "olcu", "adaylar": [1]}, {"hicbiri": True}),
    ("3. pencere", {"tur": "secim", "adaylar": [1, 2, 3]}, {"secim": 2}),
])
def test_okuma_cevabi(metin, bekleyen, cevap):
    assert CO.okuma_cevabi(metin, bekleyen) == cevap


def test_vasistas_esigi_kuralla_ayni():
    from motor.genel.sablon_pafta import sablon_kurallari
    assert CO.VASISTAS_ESIK == ((sablon_kurallari().get("vasistas_en_cok_yukseklik_cm") or {}).get("deger") or 60)
