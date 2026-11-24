"""D-148 · Çizim gelince standart formu (Lokman, 23 Kasım 2026 11:55:43 UTC; 24 Kasım 2026 06:55:41 UTC "tamam sıralama önemli değil
sana elle çizim geldiği anda formu gönder").

Bayi çizimi formsuz gönderince okumanın cevabıyla tek ekranlı standart formu gider (`kanal/formlar/standart.json`, prefabrik talep
formunun "Standart özellikler" ekranı). Cevap plandan önce gelirse plan bu seçimlerle çizilir; plandan sonra gelirse standart dışı seçim
aynı planı yeni revizyonla çizer, seçim değişmediyse plan aynı kalır. Form kimliği ayarda yoksa davranış bugünküyle aynıdır.
"""
from __future__ import annotations

import json
from pathlib import Path

from conftest import AYAR, NUMARA_A, mesaj, sorgu

import kalici
import talep_formu as TF
from test_gorsel_akisi import BASIT, BAYI_KART, bayiye, buton, cizim_gonder, isle_hepsi

FORM_AYARI = {"acik": True, "talep_flow_id": "1111111111", "revizyon_flow_id": "2222222222", "taslak": False,
              "standart_flow_id": "4444444444"}
STD = {"kaplama": "trapez", "cati_rengi": "antrasit", "yukseklik": "250", "dis_duvar": "100", "ic_duvar": "60", "tavan": "asma",
       "pencere_rengi": "beyaz"}


def ayar(tmp_path: Path, standart: bool = True) -> dict:
    h = tmp_path / "hazir_gorsel.json"
    h.write_text(json.dumps({"okuma": BASIT, "duzeltme": None}, ensure_ascii=False), encoding="utf-8")
    tf = dict(FORM_AYARI) if standart else {a: v for a, v in FORM_AYARI.items() if a != "standart_flow_id"}
    return {**AYAR, "mesaj_katmani": True, "talep_formu": tf,
            "gorsel_okuma": {"acik": True, "backend": "manuel", "hazir_dosya": str(h), "bekle_sn": 0}}


def form_satiri(depo) -> dict | None:
    return next((x for x in bayiye(depo) if x["kind"] == "interactive"
                 and (x["satir"]["interactive"] or {}).get("type") == "flow"), None)


def standart_gonder(depo, token: str, **alan) -> None:
    oz = TF.cevap_ozeti(json.dumps({"flow_token": token, **STD, **alan}, ensure_ascii=False))
    g = mesaj(TF.metin(oz), None, bayi=BAYI_KART, tur="interactive")
    g["form"] = oz
    assert depo.mesaj_kaydet(g)


def cizim_ve_form(depo, tmp_path, s) -> tuple[str, str]:
    cizim_gonder(depo, tmp_path)
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "çizim okundu: teyit", r
    f = form_satiri(depo)
    assert f is not None
    p = f["satir"]["interactive"]["action"]["parameters"]
    d, _ = depo.konusma_oku(NUMARA_A)
    return p["flow_token"], d["cizim_okuma"]["iz"]


def test_form_tanimi_prefabrik_formun_standart_ekrani():
    st, pf = TF.tanim("standart"), TF.tanim("prefabrik")
    assert st["version"] == pf["version"] and [x["id"] for x in st["screens"]] == ["STANDART_P"]
    e = st["screens"][0]
    assert e["terminal"] is True and TF.EKRAN["standart"] == "STANDART_P" and len(TF.DUGME["standart"]) <= 20
    ozp = next(x for x in pf["screens"] if x["id"] == "OZELLIK_P")
    alan = {c["name"]: c for c in e["layout"]["children"] if c.get("name")}
    eski = {c["name"]: c for c in ozp["layout"]["children"] if c.get("name")}
    assert set(alan) == set(eski) - {"not", "dosya"}
    for ad, c in alan.items():
        assert c == eski[ad]                                   # seçenekler ve seçili standartlar prefabrik formla aynı
    for ad, deger in STD.items():
        assert alan[ad]["init-value"] == deger == TF.STANDART[ad]
    footer = next(c for c in e["layout"]["children"] if c["type"] == "Footer")
    assert footer["on-click-action"]["name"] == "complete"
    assert footer["on-click-action"]["payload"] == {a: "${form.%s}" % a for a in alan}       # öteki ekrana bağlı alan yok


def test_cevap_ozeti_ve_ozellikler():
    oz = TF.cevap_ozeti(json.dumps({"flow_token": "sf:abc123", **STD, "yukseklik": "280", "kaplama": "sandvic", "musteri": "Ayşe Kaya",
                                    "il": "Edirne"}, ensure_ascii=False))
    assert oz["tur"] == "standart" and oz["form"] == "standart" and oz["token"] == "sf:abc123"
    bo, mus = TF.standart_ozellikleri(oz)
    assert bo["Pano Yüksekliği"] == "280 cm" and bo["Çatı Kaplaması"] == "sandviç panel" and bo["Tavan"] == "alçıpan asma tavan"
    assert mus == {"ad": "Ayşe Kaya", "sevk_adresi": "Edirne"}
    assert TF.metin(oz) == "Standart formu: çatı kaplaması sandviç panel, pano yüksekliği 280 cm."
    assert TF.metin(TF.cevap_ozeti(json.dumps({"flow_token": "sf:abc123", **STD}))) == "Standart formu: standartlar aynen."


def test_cizim_gelince_form_gider(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    token, _ = cizim_ve_form(depo, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert token == f"sf:{d['cizim_okuma']['standart_iz']}"
    f = form_satiri(depo)
    p = f["satir"]["interactive"]["action"]["parameters"]
    assert p["flow_id"] == "4444444444" and p["flow_action_payload"]["screen"] == "STANDART_P" and "mode" not in p
    assert f["govde"].startswith("Çiziminizi aldım. Standart özellikler formda seçili: 2,50 m pano")
    kinds = [x["kind"] for x in bayiye(depo)]
    assert kinds[-1] == "interactive" and len(kinds) == 2           # teyit + form


def test_form_kimligi_yoksa_bugunku_yol(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, standart=False)
    cizim_gonder(depo, tmp_path)
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "çizim okundu: teyit" and form_satiri(depo) is None and len(bayiye(depo)) == 1


def test_plandan_once_cevap_plan_bu_secimle(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    token, iz = cizim_ve_form(depo, tmp_path, s)
    standart_gonder(depo, token, yukseklik="280", kaplama="sandvic")
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "cevapla" and r["gerekce"] == "standart formu: plan öncesi kaydedildi", r
    assert bayiye(depo)[0]["govde"] == ("Standart dışı seçimleriniz: çatı kaplaması sandviç panel, pano yüksekliği 280 cm. "
                                        "Plan bu seçimlerle çizilecek.")
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["durum"] == "teyit"                    # teyit sorusu açık kalır
    assert depo.mesaj_kaydet(buton(f"c:{iz}:d"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie = sorgu(depo, "SELECT is_emri FROM revizyonlar")[0]["is_emri"]
    assert ie["yapi"]["duvar_yuksekligi_cm"] == 280 and ie["bina_ozellikleri"]["Çatı Kaplaması"] == "sandviç panel"


def test_plandan_sonra_standart_disi_r02_standart_ayni_kalir(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    token, iz = cizim_ve_form(depo, tmp_path, s)
    assert depo.mesaj_kaydet(buton(f"c:{iz}:d"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri"
    standart_gonder(depo, token)                                   # standartlar aynen: plan değişmez
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "standart formu: plan değişmedi", r
    no = sorgu(depo, "SELECT is_emri_no FROM revizyonlar")[0]["is_emri_no"]
    assert bayiye(depo)[0]["govde"] == f"Standart özellikler aynen kaldı. Planınız ({no} r01) değişmedi."
    standart_gonder(depo, token, yukseklik="280")
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    revs = sorgu(depo, "SELECT is_emri_no, rev, is_emri FROM revizyonlar ORDER BY rev")
    assert [x["rev"] for x in revs] == [1, 2] and revs[1]["is_emri_no"] == no
    assert revs[1]["is_emri"]["yapi"]["duvar_yuksekligi_cm"] == 280 and revs[1]["is_emri"]["mahaller"] == revs[0]["is_emri"]["mahaller"]
    m = next(x for x in bayiye(depo) if x["kind"] == "interactive")
    assert "Standart dışı seçimleriniz: pano yüksekliği 280 cm." in m["govde"]


def test_eski_form_tanınmaz(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    cizim_ve_form(depo, tmp_path, s)
    standart_gonder(depo, "sf:baskaiz12345", yukseklik="280")
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "standart formu: eski ya da tanınmayan", r
    assert sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 0
