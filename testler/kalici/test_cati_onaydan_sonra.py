"""İE-42 (D-94) · çatı plan onayından sonra, kalıcı akış (gerçek Postgres, sahte WhatsApp, kayıtlı okuma; LLM yok, hızlı Motor).

Lokman, 14 Kasım 2026 20:33:41 UTC karar kartı "Çatı, eskizdeki gibi plan onayından sonra mı sorulsun?" → "Onaydan sonra, eskizdeki gibi".
Kanal katmanında denetlenen: "Onayla" düğmesi çatı setini getirir ama onayı KAYDETMEZ (revizyon onay bekler, mühendis kontrolü açılmaz,
Patron'a prefabrik onay bildirimi gitmez); setten evin çatısı seçilince r01 onaylanır (çelikte mühendis kontrolü, prefabrikte Patron
bildirimi); başka çatı seçilince aynı projede aynı plan r02 olur (r01 "yerini_aldi"; numara her çizimde yeni, bugünkü kural), onay r02'ye bağlanır; r01'in eski Onayla düğmesi geçmez.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_cati_onaydan_sonra.py -q
"""
from __future__ import annotations

import time

from conftest import BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import kalici
from test_celik_akisi import BAYI_KART, UC, buton, hizli_genel, isle_hepsi, kabul, set_satiri  # noqa: F401  (hizli_genel: fixture)
from test_muhendis import muhendis_karti, satirlar

PA = ("PA06", "PA06K", "PA06C")
PLAN_ONAYI = "plan onaylandı"


def _pf_kabul(depo, kodlar=PA) -> None:
    for kod in kodlar:
        depo.aday_yaz(kod, "gecerli", referans_model=kod, muhendis_kabulu={"kim": "test", "tarih": "2026-11-14", "not": ""})


def _son_rev(depo) -> dict:
    return tek(depo, "SELECT * FROM revizyonlar ORDER BY id DESC LIMIT 1")


def _cati_setleri(depo) -> list[dict]:
    """Çatı seti: adaylarında çatı varyantı kodu (PA06K, Ç8801K …) olan set (tabloda set türü sütunu yok)."""
    return [st for st in sorgu(depo, "SELECT id, durum, adaylar FROM secenek_setleri")
            if any(a.get("kod") in ("PA06K", "PA06C", "Ç8801K", "Ç8801L") for a in st["adaylar"])]


def _bas(depo, reply_id: str) -> tuple[dict, dict]:
    time.sleep(1.1)                                           # İş Emri numarası saniyeye bağlı (bugünkü kural)
    g = buton(reply_id)
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    return r, g


def _r01_ve_cati_seti(depo, wa, metin: str, t: dict) -> tuple[dict, dict]:
    """r01 (evin çatısıyla) → gönderim → Onayla → çatı seti. Dönen: (r01 revizyonu, açık çatı seti)."""
    assert depo.mesaj_kaydet(mesaj(metin, t, bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    rev = _son_rev(depo)
    assert (rev["rev"], rev["durum"]) == (1, "onay_bekliyor")
    r, g = _bas(depo, f"o:{rev['is_emri_no']}:1")
    assert r["eylem"] == "secenek" and r["gerekce"] != PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onay_bekliyor"      # onay kaydedilmedi
    assert tek(depo, "SELECT count(*) n FROM muhendis_kontrolleri")["n"] == 0
    assert not sorgu(depo, "SELECT 1 FROM giden WHERE alici IN ('PATRON', 'MUHENDIS')")
    [st] = sorgu(depo, "SELECT id, durum, adaylar FROM secenek_setleri WHERE durum = 'acik'")
    satir = set_satiri(depo)
    assert satir["body"].startswith(f"Planınız onaylandı (r01). Şimdi çatıyı seçin. Bu eve 3 çatı uygulanır. Plan aynı kalır; yalnız çatı "
                                    f"değişir."), satir["body"]
    assert [b["reply"]["id"] for b in satir["interactive"]["action"]["buttons"]] == [f"s:{st['id']}:{a['kod']}" for a in st["adaylar"]]
    assert satir.get("file") and satir["file"].endswith("secenekler.png")
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor" and d["cati_adimi"]["rev"] == 1
    kalici.gonder(depo, wa)
    return rev, st


# ───────────────────────── çelik (Ç8801) ─────────────────────────
def test_celik_katalog_catisi_onaylar_muhendise_gider(depo, wa, hizli_genel):
    kabul(depo)
    muhendis_karti(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "Ç8801 olsun", talep(ozet="Ç8801 istiyor", katalog_kodu="Ç8801", yapi_turu="celik"))
    assert [a["kod"] for a in st["adaylar"]] == ["Ç8801", "Ç8801K", "Ç8801L"]
    r, g = _bas(depo, f"s:{st['id']}:Ç8801")
    assert r["gerekce"] == PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onaylandi"
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1                                # yeni çizim yok
    no = rev["is_emri_no"]
    ss = satirlar(depo, g["id"])
    assert ss[0]["body"] == (f"Çatı: Beşik + cumba (Ç8801). Plan r01 aynen kalır. Onayınız kaydedildi ({no}, revizyon 1). Plan teknik "
                             "kontrole gönderildi; sonucu size bildireceğiz.")
    assert [s for s in ss if s["_alici"] == "MUHENDIS"]
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "bekliyor" and k["onay_mesaj_id"] == g["id"]


def test_celik_baska_cati_r02_onay_r02ye_baglanir(depo, wa, hizli_genel):
    kabul(depo)
    muhendis_karti(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "Ç8801 olsun", talep(ozet="Ç8801 istiyor", katalog_kodu="Ç8801", yapi_turu="celik"))
    r, g = _bas(depo, f"s:{st['id']}:Ç8801K")
    assert r["eylem"] == "is_emri" and "Ç8801K" in r["gerekce"], r
    revs = sorgu(depo, "SELECT rev, durum, is_emri_no, proje_id, is_emri FROM revizyonlar ORDER BY rev")
    assert [(x["rev"], x["durum"]) for x in revs] == [(1, "yerini_aldi"), (2, "onay_bekliyor")]
    assert revs[1]["is_emri"]["yapi"]["kod"] == "Ç8801K" and revs[1]["proje_id"] == revs[0]["proje_id"]   # aynı proje, r02
    no2 = revs[1]["is_emri_no"]
    assert satirlar(depo, g["id"])[0]["body"] == "Çatı: Beşik + cumba, doğu ucu kırma (Ç8801-K). Plan aynı. Ön onay planınız hazır (r02)."
    assert tek(depo, "SELECT count(*) n FROM muhendis_kontrolleri")["n"] == 0
    kalici.gonder(depo, wa)
    r, _ = _bas(depo, f"o:{rev['is_emri_no']}:1")                    # r01'in eski Onayla düğmesi r02'yi onaylamaz
    assert r["gerekce"] != PLAN_ONAYI and tek(depo, "SELECT count(*) n FROM muhendis_kontrolleri")["n"] == 0, r
    r, g = _bas(depo, f"o:{no2}:2")
    assert r["gerekce"] == PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE rev = 2")["durum"] == "onaylandi"
    assert depo.muhendis_kontrolu(no2, 2)["durum"] == "bekliyor"
    assert len(_cati_setleri(depo)) == 1                                                              # çatı yeniden sorulmadı


def test_celik_cati_seti_acikken_pencere_plani_degistirir(depo, wa, hizli_genel):
    """Set açıkken pencere isteği planın değişikliği: set kapanır, r02 katalog çatısıyla; onay r02'de yeniden çatı setini getirir."""
    kabul(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "Ç8801 olsun", talep(ozet="Ç8801 istiyor", katalog_kodu="Ç8801", yapi_turu="celik"))
    time.sleep(1.1)
    g = mesaj("mutfak penceresi 120x120 olsun", talep("revizyon", "mutfak penceresi", pencereler=[{"mahal": "mutfak", "islem": "degistir",
                                                                                                    "olcu": "120x120"}]), bayi=BAYI_KART)
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    assert [(x["rev"], x["durum"]) for x in sorgu(depo, "SELECT rev, durum FROM revizyonlar ORDER BY rev")] == [(1, "yerini_aldi"), (2, "onay_bekliyor")]
    assert satirlar(depo, g["id"])[0]["body"].endswith("Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir.")
    assert tek(depo, "SELECT durum FROM secenek_setleri WHERE id = %s", st["id"])["durum"] in ("eskidi", "dustu")
    kalici.gonder(depo, wa)
    r, _ = _bas(depo, f"o:{_son_rev(depo)['is_emri_no']}:2")
    assert r["eylem"] == "secenek" and r["gerekce"] != PLAN_ONAYI, r
    assert set_satiri(depo)["body"].startswith("Planınız onaylandı (r02). Şimdi çatıyı seçin.")


# ───────────────────────── prefabrik (PA-06) ─────────────────────────
def test_prefabrik_evin_catisi_onaylar_patrona_bildirim(depo, wa, hizli_motor):
    _pf_kabul(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "PA-06 olsun", talep(ozet="PA-06", katalog_kodu="PA-06", yapi_turu="prefabrik"))
    assert [a["kod"] for a in st["adaylar"]] == list(PA)
    r, g = _bas(depo, f"s:{st['id']}:PA06")
    assert r["gerekce"] == PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onaylandi"
    ss = satirlar(depo, g["id"])
    assert ss[0]["body"] == (f"Çatı: Beşik, kalkan önde (PA-06). Plan r01 aynen kalır. Onayınız kaydedildi ({rev['is_emri_no']}, revizyon 1). "
                             "Teklif aşamasına geçiliyor.")
    p, sab = [s for s in ss if s["_alici"] == "PATRON"]
    assert f"{BAYI_A['kod']} kodlu bayi {rev['is_emri_no']} r01 prefabrik planını onayladı" in p["body"] and NUMARA_A not in p["body"]
    assert sab["kind"] == "template"
    assert tek(depo, "SELECT count(*) n FROM muhendis_kontrolleri")["n"] == 0


def test_prefabrik_baska_cati_r02_sonra_onay(depo, wa, hizli_motor):
    _pf_kabul(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "PA-06 olsun", talep(ozet="PA-06", katalog_kodu="PA-06", yapi_turu="prefabrik"))
    r, g = _bas(depo, f"s:{st['id']}:PA06C")
    assert r["eylem"] == "is_emri", r
    revs = sorgu(depo, "SELECT rev, durum, is_emri_no, proje_id, is_emri FROM revizyonlar ORDER BY rev")
    assert [(x["rev"], x["durum"]) for x in revs] == [(1, "yerini_aldi"), (2, "onay_bekliyor")]
    assert revs[1]["is_emri"]["talep"]["kaynak"] == "PA06C" and revs[1]["is_emri"]["mahaller"] == revs[0]["is_emri"]["mahaller"]
    assert revs[1]["proje_id"] == revs[0]["proje_id"]
    assert satirlar(depo, g["id"])[0]["body"] == ("Çatı: Beşik + salonda cumba (PA-06-C). Plan aynı. Ön onay planınız hazır (r02); PDF'teki "
                                                  "4 görünüş beşik + salonda cumba çatıyı gösterir.")
    assert not sorgu(depo, "SELECT 1 FROM giden WHERE alici = 'PATRON'")
    kalici.gonder(depo, wa)
    r, g = _bas(depo, f"o:{revs[1]['is_emri_no']}:2")
    assert r["gerekce"] == PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE rev = 2")["durum"] == "onaylandi"
    assert [s for s in satirlar(depo, g["id"]) if s["_alici"] == "PATRON"]


def test_prefabrik_cati_secenegi_kabulsuz_bugunku_onay(depo, wa, hizli_motor):
    """Çatı seçenekleri kabul edilmemiş ev (öteki 28 ev gibi): Onayla bugünkü gibi onaylar, çatı sorulmaz."""
    _pf_kabul(depo, ("PA06",))
    assert depo.mesaj_kaydet(mesaj("PA-06 olsun", talep(ozet="PA-06", katalog_kodu="PA-06", yapi_turu="prefabrik"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    rev = _son_rev(depo)
    r, _ = _bas(depo, f"o:{rev['is_emri_no']}:1")
    assert r["gerekce"] == PLAN_ONAYI and not _cati_setleri(depo), r


# ───────────────────────── onay denetimi (hakem tur 1, bulgu 1) ─────────────────────────
def _r02_pencereyle(depo, wa, gonder: bool) -> tuple[str, dict]:
    """PA-06 r01 (evin çatısı) gönderilir; pencere isteği r02'yi çizer (çatı yine evin çatısı). Dönen: (r01 mesajının dış kimliği, r02)."""
    _pf_kabul(depo)
    assert depo.mesaj_kaydet(mesaj("PA-06 olsun", talep(ozet="PA-06", katalog_kodu="PA-06", yapi_turu="prefabrik"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    r01_dis = sorgu(depo, "SELECT dis_id FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu, sira")[0]["dis_id"]
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("yatak odası 1 penceresi 120x180 olsun", talep(
        "revizyon", "pencere", pencereler=[{"mahal": "yatak odası 1", "islem": "degistir", "olcu": "120x180"}]), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    if gonder:
        kalici.gonder(depo, wa)
    rev = _son_rev(depo)
    assert (rev["rev"], rev["durum"]) == (2, "onay_bekliyor")
    time.sleep(1.1)
    return r01_dis, rev


def _onay_reddedildi(depo, g: dict, r: dict, rev: dict, metin: str) -> None:
    """Onay revizyona bağlanmadı: çatı seti açılmadı, onay ve çatı adımı yazılmadı, bayiye neden yazıldı."""
    assert r["gerekce"].startswith("onay bağlanmadı"), r
    assert not _cati_setleri(depo), "onay bağlanmadan çatı seti açıldı"
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onay_bekliyor"
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor" and not d.get("cati_adimi") and not d.get("onaylanan")
    govde = [s["govde"] for s in sorgu(depo, "SELECT govde FROM giden WHERE mesaj_id = %s ORDER BY sira", g["id"])]
    assert govde and metin in govde[0] and "Planınız onaylandı" not in " ".join(govde), govde


def test_alintilanan_eski_revizyonun_onayi_cati_setini_acmaz(depo, wa, hizli_motor):
    """Bayi r01'in mesajını alıntılayıp "onaylıyorum" yazar, güncel plan r02: "Planınız onaylandı (r02)" ve çatı seti gitmez (onay denetimi
    çatı setinde de koşar); bayi güncel planı yeniden onaylayınca set gelir."""
    r01_dis, rev = _r02_pencereyle(depo, wa, gonder=True)
    g = mesaj("onaylıyorum", talep("onay", "onay"), bayi=BAYI_KART, context_id=r01_dis)
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    _onay_reddedildi(depo, g, r, rev, "r01 planına ait; güncel plan")
    kalici.gonder(depo, wa)
    r, _ = _bas(depo, f"o:{rev['is_emri_no']}:2")
    assert r["eylem"] == "secenek" and set_satiri(depo)["body"].startswith("Planınız onaylandı (r02). Şimdi çatıyı seçin."), r


def test_plan_ulasmadan_yazilan_onay_cati_setini_acmaz(depo, wa, hizli_motor):
    """r02 bayiye gönderilmeden yazılan "onaylıyorum" çatı setini açmaz; sonra evin çatısı seçilip r02'nin onayı kaydedilemez."""
    _, rev = _r02_pencereyle(depo, wa, gonder=False)
    g = mesaj("onaylıyorum", talep("onay", "onay"), bayi=BAYI_KART)
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    _onay_reddedildi(depo, g, r, rev, "size ulaşmadan yazılmış")


# ───────────────────────── hakem tur 2 ─────────────────────────
def _yaz(depo, metin: str, t: dict) -> tuple[dict, dict]:
    time.sleep(1.1)
    g = mesaj(metin, t, bayi=BAYI_KART)
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    return r, g


def test_prefabrik_evin_catisi_ve_uygulanmayan_istek_onay_kaydetmez(depo, wa, hizli_motor):
    """Y1: evin çatısı + yükseklik (Motor plana işlemez): onay kaydedilmez, Patron'a bildirim gitmez, set açık kalır; bayiye isteğin
    uygulanmadığı ve çatı seçiminin kaydedilmediği yazılır. Sonra düğmeyle evin çatısı r01'i onaylar."""
    _pf_kabul(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "PA-06 olsun", talep(ozet="PA-06", katalog_kodu="PA-06", yapi_turu="prefabrik"))
    r, g = _yaz(depo, "1 olsun, yükseklik 260 olsun", talep("revizyon", "çatı 1, yükseklik 260", yukseklik_cm=260))
    assert r["gerekce"] != PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onay_bekliyor"
    assert tek(depo, "SELECT durum FROM secenek_setleri WHERE id = %s", st["id"])["durum"] == "acik"
    assert not sorgu(depo, "SELECT 1 FROM giden WHERE alici = 'PATRON'")
    assert satirlar(depo, g["id"])[0]["body"].endswith("değişmedi; isteğinizi plana uygulayamadım. Çatı seçiminizi (PA-06) kaydetmedim; "
                                                       "çatıyı yeniden seçin.")
    kalici.gonder(depo, wa)
    r, _ = _bas(depo, f"s:{st['id']}:PA06")
    assert r["gerekce"] == PLAN_ONAYI, r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onaylandi"


def test_prefabrik_cati_ve_m2_degisikligi_yeni_talep(depo, wa, hizli_motor):
    """O1: çatı + yeni m² aynı mesajda: talep değişikliği önce gelir; onay kaydedilmez, set kapanır, bayiye çatı seçiminin kaydedilmediği
    yazılır."""
    _pf_kabul(depo)
    rev, st = _r01_ve_cati_seti(depo, wa, "PA-06 olsun", talep(ozet="PA-06", katalog_kodu="PA-06", yapi_turu="prefabrik"))
    r, g = _yaz(depo, "2 olsun, 100 m2 olsun", talep("revizyon", "çatı 2, 100 m2", alan_m2=100))
    assert r["gerekce"] != PLAN_ONAYI and r["eylem"] != "is_emri", r
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] != "onaylandi"
    assert tek(depo, "SELECT durum FROM secenek_setleri WHERE id = %s", st["id"])["durum"] != "acik"
    assert not sorgu(depo, "SELECT 1 FROM giden WHERE alici = 'PATRON'")
    assert satirlar(depo, g["id"])[0]["body"].startswith("Çatı seçiminizi (PA-06-K) kaydetmedim. Talebiniz değişti; önce plan seçilir.")
