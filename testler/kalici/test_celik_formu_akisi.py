"""İE-20 PR-9 (D-93) · çelik talep formu, kalıcı akış (gerçek Postgres, sahte WhatsApp; LLM yok, hızlı sahte genel motor).

Selam → [Prefabrik] [Çelik] → çelik talep formu (çeliğin standartları seçili) → hazır çelik planlar m²'ye göre → plan → çatı → r01.
Formdaki dış duvar 140 mm karkas ilk planda çizime işlenir; öteki standart dışı seçimler özel isteğe, çatı rengi pafta tablosuna yazılır.
Çelik formunun kimliği ayarda yokken davranış bugünküyle aynıdır (`test_prefabrik_formu_akisi.py` › çelik düğmesi testleri).

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_celik_formu_akisi.py -q
"""
from __future__ import annotations

import pytest
from conftest import NUMARA_A, mesaj, sorgu, talep, tek

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
    assert d["taslak"]["form_kaplama"] == "sandvic_panel"                                                 # PR-11 (D-97): kitabın anahtarı
    assert "olcu_formdan" not in d["taslak"] and "pano" not in {k for k, v in d["taslak"].items() if v}
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Uzun kenarı m²'den hesapladım: 8 × 11 m. Standart dışı seçimlerinizi aldım: çatı kaplaması sandviç panel, "
                            "dış duvar 140 mm karkas, pencere rengi antrasit gri, çatıda çift kat yalıtım. "
                            "Çizime yalnız dış duvar 140 mm karkası ve çatı kaplamasını işlerim. İşleyemezsem plan mesajında yazarım.")
    assert "pano katına" not in govde                                                                     # çelikte ölçü yuvarlanmaz
    # plan seçilir → çatı seti (İE-25) → çatı seçilir → r01
    r = sec(depo, wa, s, "Ç8801")
    assert r["eylem"] == "secenek" and "3 aday" in r["gerekce"], r
    assert not sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"]
    r = sec(depo, wa, s, "Ç8801K")
    assert r["eylem"] == "is_emri" and "dis_karkas_140" in r["gerekce"], r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["revizyon"] == 1 and ie["yapi"]["kod"] == "Ç8801K"
    # formdaki iki seçim çizime işlendi; PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC): çatı kaplaması tanıma yazılır
    assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == [("dis_karkas_140", None), ("cati_kaplamasi", "sandvic_panel")]
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}                             # renk pafta tablosunda
    # kaplama pafta tablosunda ve listede: özel istekte ayrıca yazılmaz (aynı paftada iki kaplama okunmaz)
    assert sorted(ie["bilgi"]["ozel_istekler"]) == ["Ek İstekler: çatıda çift kat yalıtım", "Pencere Rengi: antrasit gri"]
    assert ie["bilgi"]["musteri_adi"] == "Ali Veli" and ie["bilgi"]["sevk_adresi"] == "Nilüfer, Bursa"
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm); çatı kaplaması sandviç panel." in onay["satir"]["body"]
    # PR-10 (15 Kasım 2026 canlı C5): PDF başlığında model adı ve m² düşmez
    belge = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'document' ORDER BY olusturuldu DESC, sira DESC")[0]["govde"]
    assert belge.endswith(" r01 · ÖN ONAYA SUNULAN TASLAK · Ç8801-K (Beşik + cumba, doğu ucu kırma) · 88 m², 2+1. "
                          "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm); çatı kaplaması sandviç panel."), belge


@pytest.mark.parametrize("kod, beklenen", [("Ç8801", [("cati_kaplamasi", "sandvic_panel")]), ("KT02", [])])
def test_celik_formu_cati_kaplamasi_plana_islenir(depo, wa, tmp_path, hizli_genel, kod, beklenen):  # noqa: F811
    """PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC "Plana ve listeye işlensin"). Formda yalnız çatı kaplaması sandviç panel:
    ön not söyler; seçilen planda (Ç8801, kendi kaplaması tek kat panel) işlem tanıma yazılır, özel istekte kaplama yok. Aynı formla
    kendi paftası sandviç panel olan plan (KT-02) seçilirse işlem eklenmez (tablo zaten sandviç panel), özel istek yine boş."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "kaplama": "sandvic"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Çatı kaplaması sandviç panel seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım. "), govde
    r = sec(depo, wa, s, kod)
    if kod == "Ç8801":                                                                                    # çatı seti (İE-25): evin kendi çatısı
        assert r["eylem"] == "secenek", r
        r = sec(depo, wa, s, kod)
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["kod"] == kod and [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == beklenen
    assert ie["bilgi"]["ozel_istekler"] == [] and ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert ("Uygulanan: çatı kaplaması sandviç panel." in onay["satir"]["body"]) is bool(beklenen), onay["satir"]["body"]
    assert "işleyemedim" not in onay["satir"]["body"]


def test_celik_formu_hesaplanmayan_kaplama_ozel_istekte_kalir(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """PR-11: genel motorun hesaplamadığı dört kaplama (burada kiremit desen sac + OSB) bugünkü gibi özel isteğe yazılır; plan modelin
    kendi kaplamasıyla çizilir, ön not "çizimi değiştirmez" der (Motor bu kaplamaları öğrenene kadar; ayrı bakım işi)."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "kaplama": "kiremit"}, dis)
    [r] = isle_hepsi(depo, s)
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Standart dışı seçimlerinizi aldım: çatı kaplaması kiremit desen sac + OSB. Bu seçimler çizimi değiştirmez. "), govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "form_kaplama" not in d["taslak"]
    assert sec(depo, wa, s, "Ç8801")["eylem"] == "secenek"                                               # çatı seti (İE-25)
    r = sec(depo, wa, s, "Ç8801")
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == ["Çatı Kaplaması: kiremit desen sac + OSB"]


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
    assert sec(depo, wa, s, "Ç8801")["eylem"] == "secenek"
    r = sec(depo, wa, s, "Ç8801")
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == []
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}


def test_celik_formu_yaziyla_secim_islenemeyen_140(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """PR-10 · 15 Kasım 2026 canlı denemesi C6 (gözlem 1 ve 5). Formda dış duvar 140 mm karkas; bayi planı yazıyla seçer ("KT-02 olsun";
    LLM cümleyi özel istek diye de yazar). Hedef: ön not kesin söz vermez; plan düşmez ve "işleyemedim" der; paftanın özel isteklerinde
    seçim cümlesi yok, yalnız işlenemeyen seçimin kaydı."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "dis_duvar": "140"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Dış duvar 140 mm karkas seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım. ")
    assert "çizime işlenir" not in govde
    assert depo.mesaj_kaydet(mesaj("KT-02 olsun", talep(ozet="KT-02 seçildi", katalog_kodu="KT02", ozel_istekler=["KT-02 olsun"])))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri" and "dis_karkas_140" not in r["gerekce"], r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["kod"] == "KT02" and ie["yapi"]["degisiklikler"] == []
    assert ie["bilgi"]["ozel_istekler"] == ["Dış duvar: 140 mm karkas (formdan; çizime işlenemedi)"]       # "KT-02 olsun" yok
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert onay["satir"]["body"].startswith("KT-02 · 92 m², 2+1. Dış duvar 140 mm karkası bu plana otomatik işleyemedim. "
                                            "Planı modelin kendi dış duvarıyla çizdim. İsteğinizi talebe yazdım. Ön onay planınız hazır")
    belge = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'document' ORDER BY olusturuldu DESC, sira DESC")[0]["govde"]
    assert belge.endswith(" r01 · ÖN ONAYA SUNULAN TASLAK · KT-02 · 92 m², 2+1"), belge
    assert not [y for y in sorgu(depo, "SELECT alici FROM giden") if y["alici"] == "PATRON"]               # Patron'a yönlendirme yok


def test_celik_formu_kimligi_yokken_bugunku_form(depo, wa, tmp_path):
    """`celik_flow_id` ayarda yok: [Çelik] düğmesi bugünkü formu açar (kurulum davranışı değiştirmez)."""
    s = pf_ayar(tmp_path)
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "talep"
