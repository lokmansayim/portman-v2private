"""İE-20 PR-6 (D-88) · prefabrik talep formu, kalıcı akış (gerçek Postgres, sahte WhatsApp, kayıtlı okuma; LLM yok, hızlı Motor).

Selam → [Prefabrik] [Çelik] → prefabrik form (standartlar seçili) → ölçü kodda hesaplanır → hazır planlar m²'ye göre → seçim → plan.
Standart dışı seçim plana işlenir; çelik düğmesi bugünkü formu açar; açık plan eski düğmeyle kapanmaz; prefabrik formun kimliği ayarda
yokken davranış bugünküyle aynıdır.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_prefabrik_formu_akisi.py -q
"""
from __future__ import annotations

from conftest import BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import kalici
import meta_api as M
import talep_formu as TF
import worker as W
from test_gorsel_akisi import buton
from test_talep_formu_akisi import BAYI_KART, FORM_AYARI, ayar, bayiye, form_cevabi, form_satiri, isle_hepsi, parametreler, patrona, son_sonuc

HAVUZ = ("PA01", "PA02", "PA03", "PA04", "PA05", "PA06", "PA07", "PA08")
STD = {"kat": "1", "oda": "2+1", "oncelik": "butce", **TF.STANDART}


def pf_ayar(tmp_path) -> dict:
    s = ayar(tmp_path)
    return {**s, "talep_formu": {**FORM_AYARI, "prefabrik_flow_id": "3333333333"}}


def kabul(depo, kodlar=HAVUZ) -> None:
    for kod in kodlar:
        depo.aday_yaz(kod, "gecerli", referans_model=kod, muhendis_kabulu={"kim": "test", "tarih": "2026-11-13", "not": ""})


def dugmeli(depo) -> dict:
    [x] = [x for x in bayiye(depo) if x["kind"] == "interactive" and x["satir"]["interactive"]["type"] == "button"]
    return x


def gonder_ve_dis(depo, wa, satir: dict) -> str:
    if "header" not in satir["satir"]["interactive"]:                           # başlık görselli mesaj medya kimliğiyle denetlenir (gönderici)
        M.mesaj_yuku(satir["satir"], NUMARA_A)
    kalici.gonder(depo, wa)
    return tek(depo, "SELECT dis_id FROM giden WHERE id = %s", satir["satir"]["id"])["dis_id"]


def yapi_dugmeleri(depo, wa, s) -> tuple[list[str], str]:
    """Selam yazılır; cevap [Prefabrik] [Çelik] düğmeli gelir. Dönen: (düğme kimlikleri, mesajın dış kimliği)."""
    assert depo.mesaj_kaydet(mesaj("merhaba", talep("selam", "selam"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "yapi_sor", r
    x = dugmeli(depo)
    assert x["satir"]["body"].startswith("Merhaba") and x["satir"]["body"].endswith(W.YAPI_SORUSU)
    b = x["satir"]["interactive"]["action"]["buttons"]
    assert [y["reply"]["title"] for y in b] == ["Prefabrik", "Çelik"]
    return [y["reply"]["id"] for y in b], gonder_ve_dis(depo, wa, x)


def prefabrik_formu(depo, wa, s) -> tuple[dict, str]:
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[0], dis))
    [r] = isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "prefabrik", r
    satir, dis_form = form_satiri(depo, wa)
    assert satir["body"] == "Prefabrik talep formunu doldurun. İsterseniz talebinizi yazın."
    p = parametreler(satir)
    assert p["flow_id"] == "3333333333" and p["flow_token"].startswith("pf:") and p["flow_action_payload"]["screen"] == "TALEP_P"
    return satir, dis_form


def set_al(depo, wa, tmp_path, s, **alanlar) -> tuple[dict, str, dict]:
    """Prefabrik form gönderilir; hazır planlar gelir. Dönen: (düğmeli satır, dış kimliği, işin sonucu)."""
    satir, dis = prefabrik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, **alanlar}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    x = dugmeli(depo)
    return x, gonder_ve_dis(depo, wa, x), r


def sec(depo, wa, s, x: dict, dis: str, kod: str) -> dict:
    [kimlik] = [b["reply"]["id"] for b in x["satir"]["interactive"]["action"]["buttons"] if b["reply"]["id"].endswith(":" + kod)]
    assert depo.mesaj_kaydet(buton(kimlik, dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    return tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]


def test_selam_iki_dugme_prefabrik_form_set_plan(depo, wa, tmp_path, hizli_motor):
    kabul(depo)
    s = pf_ayar(tmp_path)
    x, dis, r = set_al(depo, wa, tmp_path, s, alan="70", en="7")                # Lokman'ın örneği: 7 m kısa kenar, 70 m²
    j = tek(depo, "SELECT cikarim, sonuc FROM isler ORDER BY id DESC LIMIT 1")
    assert j["cikarim"]["form"]["durum"] == "talep" and "talep" not in j["cikarim"] and j["sonuc"]["llm"]["backend"] == "form"   # LLM yok
    govde = x["satir"]["body"]
    assert govde.startswith("Ölçüyü pano katına yuvarladım: 7,10 × 10,14 m (5,5 × 8 pano), 72 m². Uzun kenarı m²'den hesapladım.")
    assert "Öncelik: bütçe." in govde                                            # öncelik formda soruldu; sohbette yeniden sorulmaz
    kodlar = [b["reply"]["id"].rsplit(":", 1)[1] for b in x["satir"]["interactive"]["action"]["buttons"]]
    assert "PA03" in kodlar and len(kodlar) <= 3 and set(kodlar) <= set(HAVUZ)   # 72 m² ± %10: 70 m² plan sette
    d = tek(depo, "SELECT durum FROM konusmalar WHERE gonderen = %s", NUMARA_A)["durum"]
    assert d["taslak"]["oncelik"] == "butce" and d["taslak"]["pano"] == {"nx": 5.5, "ny": 8.0} and d["taslak"]["alan_m2"] == 72.0
    ie = sec(depo, wa, s, x, dis, "PA03")
    assert ie["yapi"]["sistem"] == "prefabrik" and ie["yapi"]["duvar_yuksekligi_cm"] == 250         # standart seçim planı değiştirmez
    assert ie["yapi"]["duvar_kalinligi_cm"] == {"dis": 10, "ic": 6}
    assert ie["bina_ozellikleri"]["Çatı Kaplama Rengi"] == "antrasit gri" and ie["bina_ozellikleri"]["Pencere Rengi"] == "beyaz"
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert [b["reply"]["title"] for b in onay["satir"]["interactive"]["action"]["buttons"]] == ["Onayla", "Revize et"]


def test_standart_disi_secim_plana_islenir(depo, wa, tmp_path, hizli_motor):
    kabul(depo)
    s = pf_ayar(tmp_path)
    x, dis, _r = set_al(depo, wa, tmp_path, s, alan="80", yukseklik="280", ic_duvar="100", dis_duvar="160", kaplama="kiremit", tavan="ters",
                        ek=["alcipan"], musteri="Ahmet Yılmaz", il="Bursa", ilce="Nilüfer")
    govde = x["satir"]["body"]
    assert "Standart dışı seçimleriniz talebe yazıldı: çatı kaplaması kiremit desen sac + OSB + nem bariyeri, pano yüksekliği 280 cm" in govde
    assert "Dış duvar 160 mm çizimde gösterilmez; çizim 100 mm duvarla hazırlanır." in govde
    kod = x["satir"]["interactive"]["action"]["buttons"][0]["reply"]["id"].rsplit(":", 1)[1]
    ie = sec(depo, wa, s, x, dis, kod)
    assert ie["yapi"]["duvar_yuksekligi_cm"] == 280 and ie["yapi"]["duvar_kalinligi_cm"]["ic"] == 10
    assert ie["yapi"]["duvar_kalinligi_cm"].get("dis", 10) == 10                                   # dış 160 çizime girmez
    assert ie["ozellikler"]["Çatı Kaplaması"] == "Kiremit Desen Sac + OSB + Nem Bariyeri" and ie["ozellikler"]["Tavan"] == "Ters"
    assert ie["ozellikler"]["İç Cephe Kaplaması"] == "Alçıpan" and ie["bina_ozellikleri"]["Dış Duvar"] == "160 mm"
    assert ie["talep"]["musteri_adi"] == "Ahmet Yılmaz" and ie["kunye"]["sevk_adresi"] == "Nilüfer, Bursa"   # teklif bilgisi baştan
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert "pano yüksekliği 280 cm" in onay["satir"]["body"] and "iç duvar 100 mm" in onay["satir"]["body"]


def test_hazir_plan_yoksa_olcuyle_yonlendirilir(depo, wa, tmp_path):
    kabul(depo)
    s = pf_ayar(tmp_path)
    satir, dis = prefabrik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "oda": "1+1", "alan": "45", "en": "5"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "yonlendir", r
    assert any(y["kind"] == "text" for y in bayiye(depo)) and patrona(depo)      # bayiye dürüst cevap, Lokman'a bildirim


def test_katalog_onerisi_tasiyan_soru_davetle_ezilmez(depo, wa, tmp_path):
    """Bayi prefabrik formla 2+1, 70 m² yazdı; sonra [Çelik] düğmesine bastı. Soru çelik katalog önerisini taşır: davet metni onu ezmez."""
    kabul(depo)
    s = pf_ayar(tmp_path)
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[0], dis))
    isle_hepsi(depo, s)
    satir, dis_form = form_satiri(depo, wa)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "oncelik": "yok", "alan": "70"}, dis_form)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and son_sonuc(depo)["form_sunuldu"] == "talep", r
    govde = [x["satir"]["body"] for x in bayiye(depo) if x["kind"] == "interactive" and x["satir"]["interactive"]["type"] == "flow"][-1]
    assert "katalog önerilerim" in govde and "talep formunu doldurun" not in govde


def test_celik_dugmesi_bugunku_formu_acar(depo, wa, tmp_path):
    s = pf_ayar(tmp_path)
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    [r] = isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "talep", r
    satir, _ = form_satiri(depo, wa)
    assert satir["body"] == "Çelik için talep formunu doldurun. İsterseniz talebinizi yazın."
    p = parametreler(satir)
    assert p["flow_id"] == "1111111111" and p["flow_token"].startswith("tf:") and p["flow_action_payload"]["screen"] == "TALEP"
    assert p["flow_action_payload"]["data"]["yapi"] == "celik"
    # bayi formu açmadan yazarsa soru bugünkü yoldan sürer
    assert depo.mesaj_kaydet(mesaj("2+1", talep(ozet="2+1", oda_programi="2+1"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "eksik: dis_olcu", r


def test_kartta_prefabrik_dugmesiz_form(depo, wa, tmp_path):
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"])
    depo.bayi_varsayilanlari_yaz(NUMARA_A, yapi_turu="prefabrik")
    bayi = depo.gelen_bayisi(NUMARA_A)
    s = pf_ayar(tmp_path)
    assert depo.mesaj_kaydet(mesaj("2+1 istiyorum", talep(ozet="2+1", oda_programi="2+1"), bayi=bayi))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and son_sonuc(depo)["form_sunuldu"] == "prefabrik"
    satir, _ = form_satiri(depo, wa)
    p = parametreler(satir)
    assert p["flow_id"] == "3333333333" and p["flow_token"].startswith("pf:") and p["flow_action_payload"]["data"]["oda"] == "2+1"


def test_acik_plan_eski_yapi_dugmesiyle_kapanmaz(depo, wa, tmp_path, hizli_motor):
    kabul(depo)
    s = pf_ayar(tmp_path)
    ids, dis0 = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[0], dis0))
    isle_hepsi(depo, s)
    satir, dis = form_satiri(depo, wa)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": "70"}, dis)
    isle_hepsi(depo, s)
    x = dugmeli(depo)
    sec(depo, wa, s, x, gonder_ve_dis(depo, wa, x), "PA03")
    kalici.gonder(depo, wa)
    no = tek(depo, "SELECT is_emri_no FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri_no"]
    assert depo.mesaj_kaydet(buton(ids[0], dis0))                               # eski [Prefabrik] düğmesi
    isle_hepsi(depo, s)
    [y] = bayiye(depo)
    assert y["kind"] == "text" and f"güncel plan {no} r01" in y["govde"]
    d = tek(depo, "SELECT durum FROM konusmalar WHERE gonderen = %s", NUMARA_A)["durum"]
    assert d["asama"] == "onay_bekliyor" and d["son_is_emri"]["is_emri_no"] == no
    assert len(sorgu(depo, "SELECT 1 FROM revizyonlar")) == 1


def test_prefabrik_kimligi_yokken_bugunku_davranis(depo, wa, tmp_path):
    s = ayar(tmp_path)                                                          # `prefabrik_flow_id` yok (kurulumdan sonra, açmadan önce)
    assert depo.mesaj_kaydet(mesaj("merhaba", talep("selam", "selam"), bayi=BAYI_KART))
    isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "talep"
    satir, _ = form_satiri(depo, wa)
    p = parametreler(satir)
    assert p["flow_id"] == "1111111111" and p["flow_token"].startswith("tf:")
    assert not [x for x in bayiye(depo) if x["kind"] == "interactive" and x["satir"]["interactive"]["type"] == "button"]


def test_hazir_olcu_dogrudan_plan(depo, wa, tmp_path, hizli_motor):
    """Ölçü kodlanmış bir plana birebir uyuyorsa (6 × 8 pano, 2+1) set sunulmaz: plan doğrudan gelir (bugünkü yol)."""
    kabul(depo)
    s = pf_ayar(tmp_path)
    satir, dis = prefabrik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "en": "7,73", "boy": "10,14", "yukseklik": "280"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert (ie["yapi"]["grid"]["x_pano"], ie["yapi"]["grid"]["y_pano"]) == (6, 8) and ie["yapi"]["duvar_yuksekligi_cm"] == 280
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    govde = onay["satir"]["body"]
    assert "pano yüksekliği 280 cm" in govde and "Ölçüyü pano katına yuvarladım" not in govde      # ölçü planın kendi metninde
