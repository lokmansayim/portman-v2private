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
    assert d["taslak"]["form_kaplama"] == "sandvic_panel"                                                 # PR-11 (D-97): kitabın anahtarı
    assert "olcu_formdan" not in d["taslak"] and "pano" not in {k for k, v in d["taslak"].items() if v}
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Uzun kenarı m²'den hesapladım: 8 × 11 m. Standart dışı seçimlerinizi aldım: çatı kaplaması sandviç panel, "
                            "dış duvar 140 mm karkas, pencere rengi antrasit gri, çatıda çift kat yalıtım. "
                            "Çizime yalnız dış duvar 140 mm karkası ve çatı kaplamasını işlerim. İşleyemezsem plan mesajında yazarım.")
    assert "pano katına" not in govde                                                                     # çelikte ölçü yuvarlanmaz
    # plan seçilir → r01 evin kendi çatısıyla (D-94) → Onayla → çatı seti → başka çatı → aynı plan r02
    r = sec(depo, wa, s, "Ç8801")
    assert r["eylem"] == "is_emri" and "dis_karkas_140" in r["gerekce"], r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["revizyon"] == 1 and ie["yapi"]["kod"] == "Ç8801"
    # formdaki iki seçim çizime işlendi; PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC): çatı kaplaması tanıma yazılır
    assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == [("dis_karkas_140", None), ("cati_kaplamasi", "sandvic_panel")]
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}                             # renk pafta tablosunda
    # kaplama pafta tablosunda ve listede: özel istekte ayrıca yazılmaz (aynı paftada iki kaplama okunmaz)
    assert sorted(ie["bilgi"]["ozel_istekler"]) == ["Ek İstekler: çatıda çift kat yalıtım", "Pencere Rengi: antrasit gri"]
    assert ie["bilgi"]["musteri_adi"] == "Ali Veli" and ie["bilgi"]["sevk_adresi"] == "Nilüfer, Bursa"
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm); çatı kaplaması sandviç panel." in onay["satir"]["body"]
    # PR-10 (15 Kasım 2026 canlı C5): PDF başlığında model adı ve m² düşmez (D-94: r01 evin kendi çatısıyla)
    belge = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'document' ORDER BY olusturuldu DESC, sira DESC")[0]["govde"]
    assert belge.endswith(" r01 · ÖN ONAYA SUNULAN TASLAK · Ç8801 (Beşik + cumba) · 88 m², 2+1. "
                          "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm); çatı kaplaması sandviç panel."), belge
    r = onayla(depo, wa, s)
    assert r["eylem"] == "secenek" and "3 aday" in r["gerekce"], r
    r = sec(depo, wa, s, "Ç8801K")
    assert r["eylem"] == "is_emri" and "Ç8801K" in r["gerekce"], r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["revizyon"] == 2 and ie["yapi"]["kod"] == "Ç8801K"
    # dış 140 ve formun çatı kaplaması r02'de de çizimde (çatısı seçilen plan r01'in değişikliklerini taşır)
    assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == [("dis_karkas_140", None), ("cati_kaplamasi", "sandvic_panel"),
                                                                                   ("cati_varyanti", None)]
    assert ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}
    assert sorted(ie["bilgi"]["ozel_istekler"]) == ["Ek İstekler: çatıda çift kat yalıtım", "Pencere Rengi: antrasit gri"]
    assert ie["bilgi"]["musteri_adi"] == "Ali Veli" and ie["bilgi"]["sevk_adresi"] == "Nilüfer, Bursa"
    belge = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'document' ORDER BY olusturuldu DESC, sira DESC")[0]["govde"]
    assert belge.endswith(" r02 · ÖN ONAYA SUNULAN TASLAK · Ç8801-K (Beşik + cumba, doğu ucu kırma) · 88 m², 2+1. "
                          "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm); çatı kaplaması sandviç panel."), belge   # çatısı seçilen plan: eski r01 başlığı


@pytest.mark.parametrize("kod, secim, beklenen", [("Ç8801", "sandvic", [("cati_kaplamasi", "sandvic_panel")]), ("KT02", "sandvic", []),
                                                  ("Ç8801", "kiremit", [("cati_kaplamasi", "osb_kiremit")]),
                                                  ("KT02", "kiremit", [("cati_kaplamasi", "osb_kiremit")])])
def test_celik_formu_cati_kaplamasi_plana_islenir(depo, wa, tmp_path, hizli_genel, kod, secim, beklenen):  # noqa: F811
    """PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC "Plana ve listeye işlensin"). Formda yalnız çatı kaplaması sandviç panel:
    ön not söyler; seçilen planda (Ç8801, kendi kaplaması tek kat panel) işlem tanıma yazılır, özel istekte kaplama yok. Aynı formla
    kendi paftası sandviç panel olan plan (KT-02) seçilirse işlem eklenmez (tablo zaten sandviç panel), özel istek yine boş.
    Kiremit desen sac + OSB (BK-33, D-98; Motor 15 Kasım 2026'dan beri hesaplar) aynı yoldan: iki planda da işlem tanıma yazılır."""
    ad = TF.C_KAPLAMA[secim]
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "kaplama": secim}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith(f"Çatı kaplaması {ad} seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım. "), govde
    r = sec(depo, wa, s, kod)                                                                             # D-94: Ç8801'de de r01 doğrudan (evin çatısı)
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["kod"] == kod and [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == beklenen
    assert ie["bilgi"]["ozel_istekler"] == [] and ie["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}
    [onay] = [y for y in bayiye(depo) if y["kind"] == "interactive"]
    assert (f"Uygulanan: çatı kaplaması {ad}." in onay["satir"]["body"]) is bool(beklenen), onay["satir"]["body"]
    assert "işleyemedim" not in onay["satir"]["body"]


def test_celik_formu_hesaplanmayan_kaplama_ozel_istekte_kalir(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """PR-11: genel motorun hesaplamadığı kaplamalar (burada yayımlı formun trapez sac + OSB cevabı) bugünkü gibi özel isteğe yazılır; plan modelin kendi
    kaplamasıyla çizilir, ön not "çizimi değiştirmez" der (Motor bu kaplamaları öğrenene kadar; BK-33). Örnek 15 Kasım 2026'da kiremit
    desen sac + OSB'den trapez sac + OSB'ye alındı: Motor kiremit desen sacı o gün öğrendi (D-98), o seçim artık plana işlenir."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "kaplama": "osb_trapez"}, dis)
    [r] = isle_hepsi(depo, s)
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Standart dışı seçimlerinizi aldım: çatı kaplaması trapez sac + OSB. Bu seçimler çizimi değiştirmez. "), govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "form_kaplama" not in d["taslak"]
    r = sec(depo, wa, s, "Ç8801")                                                                        # D-94: r01 evin çatısıyla, çatı onaydan sonra
    assert r["eylem"] == "is_emri", r
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    assert ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == ["Çatı Kaplaması: trapez sac + OSB"]


# İE-20 PR-11 eki (canlı deneme K7 ve K8, 15 Kasım 2026, v2026.11.15d). Kural bayinin kendi cümlesini okur (K18): LLM aynı cümleyi çatı
# değişikliği (`cati_degistir`) diye de okuyabilir, hiçbir alana yazmayabilir, `cati.kaplama`'ya, özellik satırına ya da özel isteğe
# yazabilir. Sonuç dokuz okuma biçiminde aynıdır. Canlıda görülen biçimler: K8'de `cati_degistir` (istek geri çevrildi), K7'de boş okuma
# (söz plana da talebe de yazılmadı). Önceki testler yalnız özellik satırı ve özel istek biçimini deniyordu.
def _cati_v(soz: str) -> list[dict]:
    return [{"tur": "cati_degistir", "aciklama": soz, "parametreler": {}}]


OKUMA = {
    "cati_degistir": lambda soz: {"varyantlar": _cati_v(soz)},
    "cati_degistir+cati": lambda soz: {"varyantlar": _cati_v(soz), "cati": {"kaplama": "kiremit"}},
    "cati_degistir+satir": lambda soz: {"varyantlar": _cati_v(soz), "bina_ozellikleri": {"Çatı Kaplaması": "kiremit"}},
    "cati_degistir+ozel": lambda soz: {"varyantlar": _cati_v(soz), "ozel_istekler": [soz]},
    "diger": lambda soz: {"varyantlar": [{"tur": "diger", "aciklama": soz, "parametreler": {}}]},
    "bos": lambda soz: {},
    "cati": lambda soz: {"cati": {"kaplama": "kiremit"}},
    "satir": lambda soz: {"bina_ozellikleri": {"Çatı Kaplaması": "kiremit"}},
    "ozel": lambda soz: {"ozel_istekler": [soz]},
}


def _sandvic_formu(depo, wa, tmp_path, kaplama: str = "sandvic") -> dict:
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "kaplama": kaplama}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    return s


def _c8801(depo, wa, s) -> dict:
    r = sec(depo, wa, s, "Ç8801")
    return sec(depo, wa, s, "Ç8801") if r["eylem"] == "secenek" else r                                    # çatı seti (İE-25): evin kendi çatısı


def _son_plan(depo) -> tuple[dict, str]:
    ie = tek(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri"]
    return ie, [y["satir"]["body"] for y in bayiye(depo) if y["kind"] == "interactive"][-1]


@pytest.mark.parametrize("okuma", sorted(OKUMA))
def test_formdan_sonra_yazilan_baska_kaplama_bayinin_cumlesinden(depo, wa, tmp_path, hizli_genel, okuma):  # noqa: F811
    """Canlı deneme K7: formda sandviç panel seçildi, ön nottan sonra bayi "çatı kiremit olsun" yazdı, sonra planı seçti. Form seçimi
    çizime işlenmez, bayinin sözü talebe yazılır ve bayiye söylenir; plan geri çevrilmez. LLM okuması ne olursa olsun."""
    s = _sandvic_formu(depo, wa, tmp_path)
    soz = "çatı kiremit olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep(ozet=soz, **OKUMA[okuma](soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r                                                                     # set yeniden sunulur; plan sonra
    r = _c8801(depo, wa, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 1 and ie["yapi"]["kod"] == "Ç8801" and ie["yapi"]["degisiklikler"] == []
    assert ie["bilgi"]["ozel_istekler"] == (["Çatı Kaplaması: kiremit"] if "satir" in okuma else [soz])
    assert ("Formda çatı kaplaması sandviç panel seçtiniz. Mesajınızda başka bir kaplama yazdınız. Planı modelin kendi çatı kaplamasıyla "
            "çizdim. Yazdığınız kaplamayı talebe yazdım.") in govde and "Uygulanan" not in govde, govde


@pytest.mark.parametrize("okuma", sorted(OKUMA))
def test_revizyonda_yazilan_baska_kaplama_bayinin_cumlesinden(depo, wa, tmp_path, hizli_genel, okuma):  # noqa: F811
    """Canlı deneme K8: r01 formdan sandviç panelle çizildi; bayi "çatı kaplaması kiremit olsun" yazdı. Zarftaki kaplama işlemi çıkar,
    r02 modelin kendi kaplamasıyla gelir, söz talebe yazılır ve bayiye söylenir. İstek geri çevrilmez. LLM okuması ne olursa olsun."""
    s = _sandvic_formu(depo, wa, tmp_path)
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    ie, govde = _son_plan(depo)
    assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == [("cati_kaplamasi", "sandvic_panel")]
    assert "Uygulanan: çatı kaplaması sandviç panel." in govde
    soz = "çatı kaplaması kiremit olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="Ç8801", **OKUMA[okuma](soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 2 and ie["yapi"]["degisiklikler"] == [] and ie["yapi"]["uygulanan"] == []
    assert ie["bilgi"]["ozel_istekler"] == (["Çatı Kaplaması: kiremit"] if "satir" in okuma else [soz])
    assert ("Mesajınızda başka bir çatı kaplaması yazdınız. Sandviç panel seçiminizi plandan çıkardım. Planı modelin kendi çatı "
            "kaplamasıyla çizdim. Yazdığınız kaplamayı talebe yazdım. Ön onay planınız hazır") in govde, govde


@pytest.mark.parametrize("soz,beklenen", [
    ("çatı kaplaması kiremit olabilir mi?", "yonlendir"),          # soru biçimi seçimi çıkarmaz (K21); bugünkü yol
    ("çatı kaplaması kiremit olmasın", "yonlendir"),               # olumsuz cümle seçimi çıkarmaz; bugünkü yol
    ("çatı eğimi dik olsun kaplaması kiremit olsun", "yonlendir"),  # çatı şekli isteği taşıyan cümle kaplama cümlesi değildir
    ("çatıyı kırma yap", "yonlendir"),                             # çatı şekli isteği: bugünkü yol
    ("çatı L olsun", "is_emri"),                                   # çatı seçimi: kaplama zarfta kalır
    ("çatı kaplaması sandviç panel 5 cm olsun", "yonlendir"),      # aynı kaplamanın ek bilgisi: seçim kalır; bugünkü yol
])
def test_revizyonda_kaplama_cumlesi_olmayan_cati_istegi_bugunku_yoldan(depo, wa, tmp_path, hizli_genel, soz, beklenen):  # noqa: F811
    """K8 düzeltmesinin sınırı: yalnız yalın "başka kaplama" cümlesi form seçimini plandan çıkarır. Soru, olumsuz, çatı şekli ve çatı
    seçimi cümleleri bugünkü yoldan gider; geri çevrilen istekte plan r01 ve sandviç panel seçimi aynen kalır (BK-29)."""
    s = _sandvic_formu(depo, wa, tmp_path)
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="Ç8801", varyantlar=_cati_v(soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == beklenen, r
    ie, _ = _son_plan(depo)
    if beklenen == "yonlendir":
        assert ie["revizyon"] == 1 and [x["op"] for x in ie["yapi"]["degisiklikler"]] == ["cati_kaplamasi"]
        assert "değişmedi" in [y["satir"].get("body") or "" for y in bayiye(depo)][-1]
    else:
        assert ie["revizyon"] == 2 and ie["yapi"]["kod"] == "Ç8801L"
        assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == [("cati_kaplamasi", "sandvic_panel"), ("cati_varyanti", None)]


@pytest.mark.parametrize("soz,soru", [("çatı kaplaması kiremit olsun, mutfak penceresi 120x120 olsun", False),
                                      ("çatı kaplaması kiremit olsun. salon penceresi 120x120 olsun", True)])
def test_revizyonda_kaplama_cumlesi_pencere_istegiyle_birlikte(depo, wa, tmp_path, hizli_genel, soz, soru):  # noqa: F811
    """K8 düzeltmesi, karma mesaj: kaplama cümlesi pencere isteğiyle aynı mesajda. İkisi de işlenir. Pencere sorusu araya girerse
    (salonda üç pencere) kaplama sözü taslakta bekler; cevapta seçim plandan çıkar ve bayiye söylenir (söz soruyla düşmez)."""
    s = _sandvic_formu(depo, wa, tmp_path)
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    oda = "salon" if soru else "mutfak"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="Ç8801", varyantlar=_cati_v("çatı kaplaması kiremit olsun"),
                                              pencereler=[{"mahal": oda, "olcu": "120x120", "islem": "degistir"}])))
    [r] = isle_hepsi(depo, s)
    if soru:
        assert r["eylem"] == "sor", r
        assert depo.mesaj_kaydet(mesaj("1", talep("diger", ozet="1")))
        [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 2 and [x["op"] for x in ie["yapi"]["degisiklikler"]] == ["pencere_olcu"]
    assert ie["bilgi"]["ozel_istekler"] == ["çatı kaplaması kiremit olsun"]
    assert "Sandviç panel seçiminizi plandan çıkardım." in govde and "→ 120/120" in govde, govde


# İE-20 PR-13 (D-106; Lokman, kart 15 Kasım 2026 10:06:51 UTC "Evet, talebe yazılsın"; cümle kartı 10:08:33 UTC "Üç cümle"). Formda çatı
# kaplaması standart kaldı; bayi formdan sonra mesajla bir çatı kaplaması yazdı. Kaplama çizime işlenmez; söz talebe (özel istek) yazılır
# ve bayiye üç cümle söylenir. İlk planda da revizyonda da; LLM okuması ne olursa olsun (K18). Önceki beklenti (PR-11 eki,
# `test_formda_kaplama_secilmediyse_kaplama_cumlesi_bugunku_yoldan`: revizyonda istek geri çevrilir) Lokman'ın bu kararıyla değişti.
UC_CUMLE = "Mesajınızda çatı kaplaması yazdınız. Planı modelin kendi çatı kaplamasıyla çizdim. Yazdığınız kaplamayı talebe yazdım."


@pytest.mark.parametrize("okuma", sorted(OKUMA))
def test_standart_formdan_sonra_yazilan_kaplama_talebe_yazilir(depo, wa, tmp_path, hizli_genel, okuma):  # noqa: F811
    """D-106, ilk plan: formda kaplama standart; ön nottan sonra bayi "çatı kiremit olsun" yazdı, sonra planı seçti. Plan modelin kendi
    kaplamasıyla çizilir, söz talebe yazılır, bayiye üç cümle gider; plan geri çevrilmez."""
    s = _sandvic_formu(depo, wa, tmp_path, kaplama="tek_kat")
    soz = "çatı kiremit olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep(ozet=soz, **OKUMA[okuma](soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    r = _c8801(depo, wa, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 1 and ie["yapi"]["kod"] == "Ç8801" and ie["yapi"]["degisiklikler"] == []
    assert ie["bilgi"]["ozel_istekler"] == (["Çatı Kaplaması: kiremit"] if "satir" in okuma else [soz])
    assert f"{UC_CUMLE} Ön onay planınız hazır" in govde and "Uygulanan" not in govde and "Formda çatı kaplaması" not in govde, govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "yazilan_kaplama" not in d["taslak"]


@pytest.mark.parametrize("okuma", sorted(OKUMA))
def test_standart_formda_revizyonda_yazilan_kaplama_talebe_yazilir(depo, wa, tmp_path, hizli_genel, okuma):  # noqa: F811
    """D-106, revizyon: r01 standart formla çizildi (zarfta kaplama işlemi yok); bayi "çatı kaplaması kiremit olsun" yazdı. İstek geri
    çevrilmez: r02 aynı çizimle gelir, söz talebe yazılır, bayiye üç cümle gider."""
    s = _sandvic_formu(depo, wa, tmp_path, kaplama="tek_kat")
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    ie, govde = _son_plan(depo)
    assert ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == [] and "çatı kaplaması" not in govde
    soz = "çatı kaplaması kiremit olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="Ç8801", **OKUMA[okuma](soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 2 and ie["yapi"]["kod"] == "Ç8801" and ie["yapi"]["degisiklikler"] == [] and ie["yapi"]["uygulanan"] == []
    assert ie["bilgi"]["ozel_istekler"] == (["Çatı Kaplaması: kiremit"] if "satir" in okuma else [soz])
    assert f"{UC_CUMLE} Ön onay planınız hazır" in govde and "plandan çıkardım" not in govde and "Uygulanan" not in govde, govde
    assert not [y for y in sorgu(depo, "SELECT alici FROM giden") if y["alici"] == "PATRON"]               # Patron'a yönlendirme yok


@pytest.mark.parametrize("soz,beklenen", [
    ("çatı kaplaması kiremit olabilir mi?", "yonlendir"),          # soru biçimi talebe yazılmaz (K21); bugünkü yol
    ("çatı kaplaması kiremit olmasın", "yonlendir"),               # olumsuz cümle; bugünkü yol
    ("çatı eğimi dik olsun kaplaması kiremit olsun", "yonlendir"),  # çatı şekli isteği taşıyan cümle kaplama cümlesi değildir
    ("çatı kaplaması tek kat panel olsun", "yonlendir"),           # modelin kendi kaplaması: başka kaplama değil; bugünkü yol
    ("çatı L olsun", "is_emri"),                                   # çatı seçimi: kaplama notu yok
])
def test_standart_formda_revizyonda_kaplama_cumlesi_olmayan_istek_bugunku_yoldan(depo, wa, tmp_path, hizli_genel, soz, beklenen):  # noqa: F811
    """D-106'nın sınırı: yalnız yalın "başka kaplama" cümlesi talebe yazılır ve üç cümleyi getirir. Soru, olumsuz, çatı şekli, modelin
    kendi kaplaması ve çatı seçimi cümleleri bugünkü yoldan gider."""
    s = _sandvic_formu(depo, wa, tmp_path, kaplama="tek_kat")
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="Ç8801", varyantlar=_cati_v(soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == beklenen, r
    ie, govde = _son_plan(depo)
    assert "Mesajınızda çatı kaplaması yazdınız" not in "".join(y["satir"].get("body") or "" for y in bayiye(depo))
    assert ie["bilgi"]["ozel_istekler"] == []
    assert ie["revizyon"] == (1 if beklenen == "yonlendir" else 2)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "yazilan_kaplama" not in d["taslak"] and not d["taslak"].get("ozel_istekler")


@pytest.mark.parametrize("soz,soru", [("çatı kaplaması kiremit olsun, mutfak penceresi 120x120 olsun", False),
                                      ("çatı kaplaması kiremit olsun. salon penceresi 120x120 olsun", True)])
def test_standart_formda_revizyonda_kaplama_cumlesi_pencere_istegiyle_birlikte(depo, wa, tmp_path, hizli_genel, soz, soru):  # noqa: F811
    """D-106, karma mesaj: kaplama cümlesi pencere isteğiyle aynı mesajda. Pencere işlenir, söz talebe yazılır, üç cümle gider. Pencere
    sorusu araya girerse söz taslakta bekler; cevapta bayiye söylenir (söz soruyla düşmez)."""
    s = _sandvic_formu(depo, wa, tmp_path, kaplama="tek_kat")
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    oda = "salon" if soru else "mutfak"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="Ç8801", varyantlar=_cati_v("çatı kaplaması kiremit olsun"),
                                              pencereler=[{"mahal": oda, "olcu": "120x120", "islem": "degistir"}])))
    [r] = isle_hepsi(depo, s)
    if soru:
        assert r["eylem"] == "sor", r
        assert depo.mesaj_kaydet(mesaj("1", talep("diger", ozet="1")))
        [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 2 and [x["op"] for x in ie["yapi"]["degisiklikler"]] == ["pencere_olcu"]
    assert ie["bilgi"]["ozel_istekler"] == ["çatı kaplaması kiremit olsun"]
    assert f"{UC_CUMLE} Ön onay planınız hazır" in govde and "→ 120/120" in govde, govde


@pytest.mark.parametrize("soz", ["çatı kaplaması kiremit olabilir mi?", "çatı kiremit olsun mu", "çatı kaplaması kiremit olmasın",
                                 "çatı rengi kiremit kırmızısı olsun", "dış cephe kaplaması trapez sac olsun"])
def test_standart_formdan_sonra_kaplama_istegi_olmayan_cumle_talebe_yazilmaz(depo, wa, tmp_path, hizli_genel, soz):  # noqa: F811
    """D-106'nın sınırı, ilk plan: soru, olumsuz, renk ve cephe cümlesi çatı kaplaması isteği değildir. Kural bu cümleyi talebe yazmaz,
    üç cümle gitmez (LLM okuması bugünkü yoldan işlenir; burada LLM alan doldurmadı)."""
    s = _sandvic_formu(depo, wa, tmp_path, kaplama="tek_kat")
    assert depo.mesaj_kaydet(mesaj(soz, talep(ozet=soz)))
    [r] = isle_hepsi(depo, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "yazilan_kaplama" not in d["taslak"] and not d["taslak"].get("ozel_istekler"), d["taslak"]
    if r["eylem"] == "secenek":
        assert _c8801(depo, wa, s)["eylem"] == "is_emri"
        ie, govde = _son_plan(depo)
        assert ie["bilgi"]["ozel_istekler"] == [] and "Mesajınızda çatı kaplaması yazdınız" not in govde, govde


def test_modelin_kendi_kaplamasi_form_secimiyse_revizyonda_yazilan_kaplama_talebe_yazilir(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """D-106, revizyon: formda sandviç panel seçildi, model zaten sandviç panel (KT-02): zarfta kaplama işlemi yok. Bayi revizyonda
    başka bir kaplama yazarsa söz talebe yazılır, üç cümle gider; plan geri çevrilmez."""
    s = _sandvic_formu(depo, wa, tmp_path)
    r = sec(depo, wa, s, "KT02")
    assert r["eylem"] == "is_emri", r
    ie, _ = _son_plan(depo)
    assert ie["yapi"]["kod"] == "KT02" and ie["yapi"]["degisiklikler"] == []
    soz = "çatı kaplaması kiremit olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep("revizyon", ozet=soz, katalog_kodu="KT02", varyantlar=_cati_v(soz))))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["revizyon"] == 2 and ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == [soz]
    assert f"{UC_CUMLE} Ön onay planınız hazır" in govde and "plandan çıkardım" not in govde, govde


def test_standart_formdan_sonra_modelin_kendi_kaplamasi_yazilirsa_not_yok(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """D-106'nın sınırı, ilk plan: bayi modelin kendi kaplamasını yazdı ("çatı tek kat panel olsun"; Ç8801 tek kat panel). Plan zaten o
    kaplamayla çizilir: üç cümle gitmez. Söz talepte durur (sessiz düşmez)."""
    s = _sandvic_formu(depo, wa, tmp_path, kaplama="tek_kat")
    soz = "çatı tek kat panel olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep(ozet=soz)))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    ie, govde = _son_plan(depo)
    assert ie["yapi"]["degisiklikler"] == [] and ie["bilgi"]["ozel_istekler"] == [soz]
    assert "Mesajınızda çatı kaplaması yazdınız" not in govde, govde


def test_standart_formdan_sonra_yazilan_kaplama_form_yenilenince_son_soz_form(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """D-106'nın sınırı: bayi kaplamayı yazdıktan sonra formu yeniden gönderip sandviç panel seçti. Son söz formdur: sandviç panel çizime
    işlenir, üç cümle gitmez; önce yazılan söz talepte kalır (D-97'nin "formdan önce yazılan söz" kuralı)."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    satir, dis = celik_formu(depo, wa, s)
    jeton = parametreler(satir)["flow_token"]
    form_cevabi(depo, tmp_path, jeton, {**STD, "alan": 88, "oncelik": "yok", "kaplama": "tek_kat"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    soz = "çatı kiremit olsun"
    assert depo.mesaj_kaydet(mesaj(soz, talep(ozet=soz)))
    [r] = isle_hepsi(depo, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["taslak"]["yazilan_kaplama"] == [soz]
    form_cevabi(depo, tmp_path, jeton, {**STD, "alan": 88, "oncelik": "yok", "kaplama": "sandvic"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "yazilan_kaplama" not in d["taslak"] and d["taslak"]["form_kaplama"] == "sandvic_panel"
    assert _c8801(depo, wa, s)["eylem"] == "is_emri"
    ie, govde = _son_plan(depo)
    assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == [("cati_kaplamasi", "sandvic_panel")]
    assert ie["bilgi"]["ozel_istekler"] == [soz]
    assert "Uygulanan: çatı kaplaması sandviç panel." in govde and "Mesajınızda" not in govde, govde


@pytest.mark.parametrize("soz,kod,islem", [("çatı L olsun", "Ç8801L", [("cati_kaplamasi", "sandvic_panel")]),
                                           ("mutfak penceresi 120x120 olsun", "Ç8801", None)])
def test_formdan_sonra_kaplama_disi_istek_bugunku_yoldan(depo, wa, tmp_path, hizli_genel, soz, kod, islem):  # noqa: F811
    """K7 düzeltmesinin sınırı: formdan sonra yazılan çatı seçimi ya da pencere isteği kaplama cümlesi değildir; LLM varyantı düşmez,
    form seçimi çizime işlenir."""
    s = _sandvic_formu(depo, wa, tmp_path)
    ek = {"varyantlar": _cati_v(soz)} if "çatı" in soz else {"pencereler": [{"mahal": "mutfak", "olcu": "120x120", "islem": "degistir"}]}
    assert depo.mesaj_kaydet(mesaj(soz, talep(ozet=soz, **ek)))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "secenek", r
    r = sec(depo, wa, s, "Ç8801")
    if r["eylem"] == "secenek":
        r = sec(depo, wa, s, kod)
    assert r["eylem"] == "is_emri", r
    ie, govde = _son_plan(depo)
    assert ie["yapi"]["kod"] == kod and ("cati_kaplamasi", "sandvic_panel") in [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]]
    assert "çatı kaplaması sandviç panel" in govde and "başka bir kaplama" not in govde, govde
    if islem is not None:
        assert [(x["op"], x.get("kaplama")) for x in ie["yapi"]["degisiklikler"]] == islem


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


def test_celik2_kimligi_varsa_yeni_form_sunulur_cevabi_ayni_yoldan(depo, wa, tmp_path, hizli_genel):  # noqa: F811
    """İE-20 PR-12 (D-102): `celik2_flow_id` ayarda varsa [Çelik] düğmesi yeni formu açar (trapez saclı seçenek yok). Cevabı çelik formun
    yolundan işlenir: shingle seçimi "OSB + membran + shingle" diye okunur. BK-33'ten (D-100) beri Motor bu kaplamayı hesaplar: seçim taslağa
    `form_kaplama` diye girer, ön not "Çizime işlerim" der (önceden özel istekte kalırdı)."""
    kabul(depo, YEDI)
    s = cf_ayar(tmp_path)
    s = {**s, "talep_formu": {**s["talep_formu"], "celik2_flow_id": "6666666666"}}
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    [r] = isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "celik2", r
    satir, dis_form = form_satiri(depo, wa)
    assert satir["body"] == "Çelik talep formunu doldurun. İsterseniz talebinizi yazın."
    p = parametreler(satir)
    assert p["flow_id"] == "6666666666" and p["flow_token"].startswith("cf:") and p["flow_action_payload"]["screen"] == "TALEP_C"
    form_cevabi(depo, tmp_path, p["flow_token"], {**STD, "alan": 88, "oncelik": "yok", "kaplama": "shingle"}, dis_form)
    [r] = isle_hepsi(depo, s)
    j = tek(depo, "SELECT cikarim, sonuc FROM isler ORDER BY id DESC LIMIT 1")
    assert j["cikarim"]["form"]["durum"] == "talep" and j["sonuc"]["llm"]["backend"] == "form", r        # LLM'siz
    assert j["cikarim"]["form"]["talep"]["bina_ozellikleri"]["Çatı Kaplaması"] == "OSB + membran + shingle"
    assert r["eylem"] == "secenek", r
    govde = dugmeli(depo)["satir"]["body"]
    assert govde.startswith("Çatı kaplaması OSB + membran + shingle seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım. "), govde
    assert "Standart dışı seçimlerinizi aldım" not in govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["taslak"]["form"] == "celik" and d["taslak"]["form_kaplama"] == "osb_shingle"
    assert d["taslak"]["form_kaplama_yazi"] == "OSB + membran + shingle"


def test_celik_formu_kimligi_yokken_bugunku_form(depo, wa, tmp_path):
    """`celik_flow_id` ayarda yok: [Çelik] düğmesi bugünkü formu açar (kurulum davranışı değiştirmez)."""
    s = pf_ayar(tmp_path)
    ids, dis = yapi_dugmeleri(depo, wa, s)
    assert depo.mesaj_kaydet(buton(ids[1], dis))
    isle_hepsi(depo, s)
    assert son_sonuc(depo)["form_sunuldu"] == "talep"
