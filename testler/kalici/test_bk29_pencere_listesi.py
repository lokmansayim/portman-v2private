"""BK-29 PR-2 (pano 201, 210) · kalıcı akışta: oda sorusu liste olarak, pencere sorusu düğmeyle gider ve cevabı planı günceller.

Kabul seti B2, B5 (13 Kasım 2026 denetimi): odası yazılmamış pencere isteğinde bot odaları sorar; dört oda üç düğmeye sığmaz, WhatsApp
listesi gider ve listedeki seçim r02'yi üretir. İki pencereli odada bot "Hangisini?" diye iki düğmeyle sorar; düğme r03'ü üretir.
Gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp, hızlı Motor.
"""
from __future__ import annotations

from conftest import AYAR, mesaj, sorgu, talep, tek

import etkilesim as ET
import kalici

KATMAN = {**AYAR, "mesaj_katmani": True}


def isle_hepsi(depo, ayar=KATMAN) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def bayiye_son(depo, mesaj_id: str) -> dict:
    satirlar = [x for x in sorgu(depo, "SELECT alici, kind, satir, dis_id FROM giden WHERE mesaj_id = %s ORDER BY sira", mesaj_id)
                if x["alici"] != "PATRON"]
    assert len(satirlar) == 1, satirlar
    return satirlar[0]


def cevap(metin: str, kimlik: str, dis_id: str, tur: str) -> dict:
    g = mesaj(metin, talep("diger", "kısa cevap"), context_id=dis_id, tur="interactive")
    g["reply_id"] = kimlik; g["reply_kind"] = tur
    return g


def test_oda_listesi_ve_pencere_dugmesi_kalici(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001", talep(ozet="P6001", katalog_kodu="P6001")))
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "is_emri"
    kalici.gonder(depo, wa)

    # odası yazılmamış pencere: dört oda → liste
    t = talep("revizyon", "pencere 120x180 olsun",
              varyantlar=[{"tur": "pencere_degistir", "aciklama": "pencere 120x180 olsun", "parametreler": {"yeni": "120x180"}}])
    depo.mesaj_kaydet(mesaj("pencere 120x180 olsun", t))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "sor", r2
    kalici.gonder(depo, wa)
    soru = bayiye_son(depo, r2["mesaj_id"])
    assert soru["kind"] == "interactive" and soru["satir"]["interactive"]["type"] == "list"
    satirlar = soru["satir"]["interactive"]["action"]["sections"][0]["rows"]
    assert [(x["id"], x["title"]) for x in satirlar] == [("q:pencere_mahal:1", "YASAM ALANI"), ("q:pencere_mahal:2", "YATAK ODASI 1"),
                                                         ("q:pencere_mahal:3", "BANYO"), ("q:pencere_mahal:4", "YATAK ODASI 2")]
    assert ET.mesaj_kimlikleri(soru["satir"]) == {f"q:pencere_mahal:{i}" for i in range(1, 5)}
    assert "veranda" not in soru["satir"]["body"].lower()

    # listeden YATAK ODASI 1 → r02
    depo.mesaj_kaydet(cevap("YATAK ODASI 1", "q:pencere_mahal:2", soru["dis_id"], "list_reply"))
    [r3] = isle_hepsi(depo)
    assert r3["eylem"] == "is_emri", r3
    kalici.gonder(depo, wa)
    assert [x["rev"] for x in sorgu(depo, "SELECT rev FROM revizyonlar ORDER BY rev")] == [1, 2]
    ie = tek(depo, "SELECT is_emri FROM revizyonlar WHERE rev = 2")["is_emri"]
    assert [a["olcu"] for a in ie["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == "YATAK ODASI 1"] == ["120x180"]

    # iki pencereli yaşam alanı: iki düğme, düğme → r03
    t = talep("revizyon", "yaşam alanı penceresi 120x120 olsun",
              pencereler=[{"mahal": "yaşam alanı", "olcu": "120x120", "islem": None, "aciklama": "yaşam alanı penceresi 120x120 olsun"}])
    depo.mesaj_kaydet(mesaj("yaşam alanı penceresi 120x120 olsun", t))
    [r4] = isle_hepsi(depo)
    assert r4["eylem"] == "sor", r4
    kalici.gonder(depo, wa)
    soru = bayiye_son(depo, r4["mesaj_id"])
    assert soru["satir"]["interactive"]["type"] == "button"
    assert ET.mesaj_kimlikleri(soru["satir"]) == {"q:pencere_secim:1", "q:pencere_secim:2"}
    # D-86 (BK-29 tur 5): 1. düğme zaten 120x120 olan sol pencere (plan değişmez, yeni revizyon gitmez); 2. düğme 120x180 ön pencere
    depo.mesaj_kaydet(cevap("2", "q:pencere_secim:2", soru["dis_id"], "button_reply"))
    [r5] = isle_hepsi(depo)
    assert r5["eylem"] == "is_emri", r5
    assert [x["rev"] for x in sorgu(depo, "SELECT rev FROM revizyonlar ORDER BY rev")] == [1, 2, 3]
    ie = tek(depo, "SELECT is_emri FROM revizyonlar WHERE rev = 3")["is_emri"]
    olculer = sorted(a["olcu"] for a in ie["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == "YASAM ALANI")
    assert "120x120" in olculer and len(olculer) == 2
    assert [a["olcu"] for a in ie["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == "YATAK ODASI 1"] == ["120x180"]
