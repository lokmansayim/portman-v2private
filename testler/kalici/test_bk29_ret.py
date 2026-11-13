"""BK-29 PR-1 (pano 200) · kalıcı akışta: geri çevrilen revizyon isteğinden sonra plan açık kalır.

Kabul seti C1 (13 Kasım 2026 denetimi): ret cevabı Onayla / Revize et düğmeleriyle gider, Patron'a yönlendirme bildirimi bugünkü gibi
gider, revizyon kaydı onay bekler; bayi ret mesajındaki Onayla düğmesine basınca onay aynı revizyona yazılır. Gerçek Postgres, kayıtlı
LLM çıkarımı, sahte WhatsApp, hızlı Motor.
"""
from __future__ import annotations

import time

from conftest import AYAR, mesaj, sorgu, talep, tek

import etkilesim as ET
import kalici

KATMAN = {**AYAR, "mesaj_katmani": True}


def isle_hepsi(depo, ayar=KATMAN) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def test_ret_sonrasi_onayla_dugmesi_kalici(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001", talep(ozet="P6001", katalog_kodu="P6001")))
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "is_emri"
    kalici.gonder(depo, wa)
    no = tek(depo, "SELECT is_emri_no FROM revizyonlar")["is_emri_no"]

    t_ret = talep("revizyon", "veranda arkada olsun",
                  varyantlar=[{"tur": "veranda_degistir", "aciklama": "veranda arkada olsun", "parametreler": {}}])
    depo.mesaj_kaydet(mesaj("veranda arkada olsun", t_ret))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "yonlendir", r2
    kalici.gonder(depo, wa)
    satirlar = sorgu(depo, "SELECT alici, kind, satir, dis_id FROM giden WHERE mesaj_id = %s ORDER BY sira", r2["mesaj_id"])
    bayiye = [x for x in satirlar if x["alici"] != "PATRON"]
    assert [x["kind"] for x in bayiye] == ["interactive"]
    ret = bayiye[0]
    assert sorted(ET.mesaj_kimlikleri(ret["satir"])) == sorted([f"o:{no}:1", f"r:{no}:1"])
    assert f"Planınız ({no} r01) değişmedi." in ret["satir"]["body"]
    assert any(x["alici"] == "PATRON" and "yönlendirme" in str(x["satir"].get("body") or x["satir"].get("text") or "") for x in satirlar)
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE rev = 1")["durum"] == "onay_bekliyor"
    assert tek(depo, "SELECT durum FROM konusmalar")["durum"]["asama"] == "onay_bekliyor"

    time.sleep(1.1)                                          # onay planın teslim anından sonra yazılmış olmalı
    g = mesaj("Onayla", talep("diger", "kısa cevap"), context_id=ret["dis_id"], tur="interactive")
    g["reply_id"] = f"o:{no}:1"; g["reply_kind"] = "button_reply"
    depo.mesaj_kaydet(g)
    [r3] = isle_hepsi(depo)
    assert r3["gerekce"] == "plan onaylandı", r3
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE rev = 1")["durum"] == "onaylandi"
