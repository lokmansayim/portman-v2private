"""İE-20 PR-9 (D-93) · çelik talep formu, kalıcı akış (gerçek Postgres, sahte WhatsApp; LLM yok, hızlı sahte genel motor).

Selam → [Prefabrik] [Çelik] → çelik talep formu (çeliğin standartları seçili) → hazır çelik planlar m²'ye göre → plan → r01 (evin
kendi çatısıyla) → Onayla → çatı seti → evin çatısı r01'i onaylar, başka çatı aynı planı r02 çizer (D-94, İE-42; önceki akışta çatı
plandan hemen sonra soruluyordu, İE-25).
Formdaki dış duvar 140 mm karkas ilk planda çizime işlenir; öteki standart dışı seçimler özel isteğe, çatı rengi pafta tablosuna yazılır.
Çelik formunun kimliği ayarda yokken davranış bugünküyle aynıdır (`test_prefabrik_formu_akisi.py` › çelik düğmesi testleri).

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_celik_formu_akisi.py -q
"""
from __future__ import annotations

import time

from conftest import NUMARA_A, sorgu, tek

import talep_formu as TF
from test_celik_akisi import YEDI, hizli_genel, kabul  # noqa: F401  (hizli_genel: pytest fixture)
from test_gorsel_akisi import buton
from test_prefabrik_formu_akisi import dugmeli, gonder_ve_dis, pf_ayar, yapi_dugmeleri
from test_talep_formu_akisi import bayiye, form_cevabi, form_satiri, isle_hepsi, parametreler, son_sonuc

STD = {"kat": "1", "oda": "2+1", "oncelik": "butce", **TF.C_STANDART}


def cf_ayar(tmp_path) -> dict:
    s = pf_ayar(tmp_path)
    return {**s, "talep_formu": {**s["talep_formu"], "celik_flow_id": "5555555555"}}


def celik_formu(depo, wa, s) -> tuple[dict, str]:
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    [r] = isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "celik", r
    satir, dis_form = form_satiri(depo, wa)
    assert satir["body"] == "Çelik talep formunu doldurun. İsterseniz talebinizi yazın."
    p = parametreler(satir)
    assert p["flow_id"] == "5555555555" and p["flow_token"].startswith("cf:") and p["flow_action_payload"]["screen"] == "TALEP_C"
    veri = p["flow_action_payload"]["data"]
    assert set(veri) == set(TF.tanim("celik")["screens"][0]["data"]) and "yapi" not in veri and "veranda" not in veri
    return satir, dis_form


def sec(depo, wa, s, kod: str) -> dict:
    """Açık setten `kod` düğmesine basılır. Dönen: işin sonucu."""
    x = dugmeli(depo)
    dis = gonder_ve_dis(depo, wa, x)
    sid = tek(depo, "SELECT id FROM secenek_setleri WHERE durum = 'acik'")["id"]
    assert depo.mesaj_kaydet(buton(f"s:{sid}:{kod}", dis))
    [r] = isle_hepsi(depo, s)
    return r


def onayla(depo, wa, s) -> dict:
    """Son planın Onayla düğmesine basılır (D-94: çatı seçeneği olan evde çatı setini getirir). Dönen: işin sonucu."""
    x = dugmeli(depo)
    dis = gonder_ve_dis(depo, wa, x)
    rev = tek(depo, "SELECT is_emri_no, rev FROM revizyonlar ORDER BY id DESC LIMIT 1")
    time.sleep(1.1)                                           # onay, planın gönderildiği saniyeden sonra (plan ulaşmadan yazılan onay bağlanmaz)
    assert depo.mesaj_kaydet(buton(f"o:{rev['is_emri_no']}:{rev['rev']}", dis))
    [r] = isle_hepsi(depo, s)
    return r


def test_celik_formu_dis_140_plana_islenir(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"],
                {**STD, "en": 8, "alan": 88, "dis_duvar": "140", "kaplama": "sandvic", "pencere_rengi": "antrasit", "ek": ["cift_yalitim"],
                 "musteri": "Ali Veli", "il": "Bursa", "ilce": "Nilüfer"}, dis)
    [r] = isle_hepsi(depo, s)
    j = tek(depo, "SELECT cikarim, sonuc FROM isler ORDER BY id DESC LIMIT 1")
    assert j["cikarim"]["form"]["durum"] == "talep" and j["sonuc"]["llm"]["backend"] == "form", r        # LLM'siz
    t = j["cikarim"]["form"]["talep"]
    assert t["yapi_turu"] == "celik" and t["alan_m2"] == 88 and t["dis_olcu"] == {"en_m": 8.0, "boy_m": 11.0} and "veranda" not in t
    # hazır çelik planlar m²'ye göre; soru yok (öncelik formda seçildi, çatı plandan sonra)
    assert r["eylem"] == "secenek" and "4 aday" in r["gerekce"], r
    st = tek(depo, "SELECT adaylar FROM secenek_setleri WHERE durum = 'acik'")
    assert {a["kod"] for a in st["adaylar"]} == {"Ç8801", "KT02", "KT03", "Ç8201"}
    assert any("bütçe önceliği" in (a.get("hesap") or "") for a in st["adaylar"])                         # formdaki öncelik seti sıraladı
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["taslak"]["form"] == "celik" and d["taslak"]["form_dis140"] is True and d["taslak"]["oncelik"] == "butce"
    assert "olcu_formdan" not in d["taslak"] and "pano" not in {k for k, v in d["taslak"].items() if v}
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Uzun kenarı m²'den hesapladım: 8 × 11 m. Standart dışı seçimlerinizi aldım: çatı kaplaması sandviç panel, "
                            "dış duvar 140 mm karkas, pencere rengi antrasit gri, çatıda çift kat yalıtım. "
                            "Çizime yalnız dış duvar 140 mm karkas işlenir.")
    assert "pano katına" not in govde                                                                     # çelikte ölçü yuvarlanmaz
    # plan seçilir → r01 evin kendi çatısıyla (D-94) → Onayla → çatı seti → başka çatı → aynı plan r02
    r = sec(depo, wa, s, "Ç8801")
    assert r["eylem"] == "is_emri" and "dis_karkas_140" in r["gerekce"], r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["revizyon"] == 1 and ie["yapi"]["kod"] == "Ç8801"
    assert [x["op"] for x in ie["yapi"]["degisiklikler"]] == ["dis_karkas_140"]                           # formdaki seçim çizime işlendi
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}                             # renk pafta tablosunda
    assert sorted(ie["bilgi"]["ozel_istekler"]) == ["Ek İstekler: çatıda çift kat yalıtım", "Pencere Rengi: antrasit gri",
                                                    "Çatı Kaplaması: sandviç panel"]            # sıra taslağın (jsonb) anahtar sırası
    assert ie["bilgi"]["musteri_adi"] == "Ali Veli" and ie["bilgi"]["sevk_adresi"] == "Nilüfer, Bursa"
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm)." in onay["satir"]["body"]
    r = onayla(depo, wa, s)
    assert r["eylem"] == "secenek" and "3 aday" in r["gerekce"], r
    r = sec(depo, wa, s, "Ç8801K")
    assert r["eylem"] == "is_emri" and "Ç8801K" in r["gerekce"], r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["revizyon"] == 2 and ie["yapi"]["kod"] == "Ç8801K"
    assert [x["op"] for x in ie["yapi"]["degisiklikler"]] == ["dis_karkas_140", "cati_varyanti"]          # dış 140 r02'de de çizimde
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}
    assert ie["bilgi"]["musteri_adi"] == "Ali Veli" and ie["bilgi"]["sevk_adresi"] == "Nilüfer, Bursa"


def test_celik_formu_standart_secimle_bugunku_plan(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """Standartlar değişmeden gönderilen form: plan bugünkü çelik planla aynı (işlem yok, özel istek yok); çatı rengi tabloda."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek" and "4 aday" in r["gerekce"], r
    govde = dugmeli(depo)["satir"]["body"]
    assert "Standart dışı" not in govde and "hesapladım" not in govde                                      # söylenecek şey yok: ön not yok
    st = tek(depo, "SELECT adaylar FROM secenek_setleri WHERE durum = 'acik'")
    assert [a["kod"] for a in st["adaylar"]] == ["Ç8801", "KT02", "KT03", "Ç8201"]                         # sohbetteki "88 m² 2+1 çelik" ile aynı sıra
    r = sec(depo, wa, s, "Ç8801")                                                                         # D-94: plan seçimi r01 çizer
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == []
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}
    assert onayla(depo, wa, s)["eylem"] == "secenek"                                                       # Onayla → çatı seti
    r = sec(depo, wa, s, "Ç8801")                                                                         # evin çatısı r01'i onaylar
    assert r["gerekce"] == "plan onaylandı", r
    assert tek(depo, "SELECT count(*) AS n FROM revizyonlar")["n"] == 1                                   # yeni çizim yok


def test_celik_formu_kimligi_yokken_bugunku_form(depo, wa, tmp_path):
    """`celik_flow_id` ayarda yok: [Çelik] düğmesi bugünkü formu açar (kurulum davranışı değiştirmez)."""
    s = pf_ayar(tmp_path)
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "talep"
