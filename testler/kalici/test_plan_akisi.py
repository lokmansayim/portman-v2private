"""İE-14 PR-2 · talepten plana, kanal (kalıcı akış, gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp; üretici elle yazılmış
cevaplarla — `worker.plan_uret` manuel arka uca bağlanır, LLM çağrısı yok).

T1: "95 m² 3+1 tek kat çelik" (bankada 3+1 yok) → önce "hazırlıyorum", sonra seçenek görseli: 1. Yeni plan + bankadan en yakın iki
model; üretim sonucu iş satırına (`isler.cikarim.plan_uretimi`) yazılır. T2: "Yeni plan" düğmesi → r01, zarfta tanım gömülü (kanonik
sha), genel motor. T4: üretim kurallara uymazsa "otomatik çizemedim" + Patron. T5: Onayla → 8b mühendis kontrol kaydı. Ayar kapalıyken
bugünkü davranış (`test_celik_akisi.test_kat_suzgeci_ve_uyan_yoksa_bugunku_davranis`). Revizyon (dış 140) gömülü tanım üstünde r02.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_plan_akisi.py -q
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import AYAR, NUMARA_A, mesaj, sorgu, talep
from test_celik_akisi import BAYI_KART, YEDI, buton, hizli_genel, isle_hepsi, kabul, son_rev  # noqa: F401 (fikstür)

import worker as W

KOK = Path(__file__).resolve().parents[2]
ORNEK = KOK / "testler" / "plan" / "ornekler"
URETIM = {**AYAR, "mesaj_katmani": True, "plan_uretimi": {"acik": True}}
T95 = talep(ozet="95 m² 3+1 tek kat çelik, kırma çatı", alan_m2=95, oda_programi="3+1", yapi_turu="celik", kat_sayisi=1, cati={"tip": "kirma"})


def ornek(ad):
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


@pytest.fixture
def uretici(monkeypatch):
    """`worker.plan_uret` → manuel arka uç (elle yazılmış cevaplar sırayla); çağrı sayısı ve gelen talep tutulur."""
    from beyin import plan_uretici as PU
    durum = {"cevaplar": [ornek("gecersiz_3arti1_dar_odalar"), ornek("gecerli_3arti1_100")], "cagri": 0, "talep": None}

    def sahte(talep_, ayar):
        durum["cagri"] += 1
        durum["talep"] = talep_
        return PU.uret(talep_, hazir=durum["cevaplar"])
    monkeypatch.setattr(W, "plan_uret", sahte)
    return durum


def t1(depo):
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik, kırma çatı", T95, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    return r


def test_t1_uyan_yoksa_yeni_plan_ve_bankadan_en_yakinlar(depo, wa, hizli_genel, uretici):
    r = t1(depo)
    assert r["eylem"] == "secenek" and "yeni plan YENI-" in r["gerekce"], r
    assert uretici["cagri"] == 1
    tl = uretici["talep"]
    assert tl["oda_programi"] == "3+1" and tl["alan_m2"] == 95 and tl["cati"]["tip"] == "kirma"
    assert "telefon" not in json.dumps(tl) and "musteri" not in tl                    # LLM'e yalnız yapısal talep
    st = sorgu(depo, "SELECT id, durum, adaylar FROM secenek_setleri")[0]
    kodlar = [a["kod"] for a in st["adaylar"]]
    assert kodlar[0].startswith("YENI-") and kodlar[1:] == ["KT03", "KT02"]           # brüt alana en yakın iki banka modeli (94, 92)
    assert st["adaylar"][0]["tanim"] is None                                         # set kaydı tanımı taşımaz; konuşmada
    satirlar = sorgu(depo, "SELECT kind, govde, satir FROM giden ORDER BY sira")
    assert satirlar[0]["kind"] == "text" and "yeni bir plan taslağı hazırlıyorum" in satirlar[0]["govde"]
    s = satirlar[1]["satir"]
    assert [b["reply"]["title"] for b in s["interactive"]["action"]["buttons"]][0] == "1. Yeni plan"
    assert "1. Yeni plan · 100 m² · 3+1 · TASLAK" in s["body"] and "(bankadan en yakın)" in s["body"]
    d, _ = depo.konusma_oku(NUMARA_A)
    u = d["uretilen_plan"]
    assert u["kod"] == kodlar[0] and isinstance(u["tanim"], dict) and u["durum"] == "uretilen" and "plan_istegi" not in d
    c = sorgu(depo, "SELECT cikarim FROM isler")[0]["cikarim"]
    pu = c["plan_uretimi"]
    assert pu["durum"] == "gecerli" and len(pu["denemeler"]) == 2 and not pu["denemeler"][0]["gecerli"]
    assert c["talep"]["oda_programi"] == "3+1"                                       # çıkarım kaydı korunur
    pr = sorgu(depo, "SELECT durum, plan_kodu, cagri, talep, denemeler, is_emri_no FROM plan_uretimleri")     # göç 007
    assert len(pr) == 1 and pr[0]["durum"] == "gecerli" and pr[0]["plan_kodu"] == kodlar[0] and len(pr[0]["denemeler"]) == 2
    assert pr[0]["talep"]["oda_programi"] == "3+1" and pr[0]["is_emri_no"] is None and NUMARA_A not in json.dumps(pr[0]["talep"])


def test_t2_yeni_plan_secimi_r01_gomulu_tanim(depo, wa, hizli_genel, uretici):
    from beyin import celik as C
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    yeni = st["adaylar"][0]["kod"]
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{yeni}"))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri", r
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert y["kod"] == yeni and y["sistem"] == "celik" and isinstance(y["tanim"], dict) and C.tanim_dogrula(y)
    assert y["gosterim"] == "Yeni plan" and rev["rev"] == 1
    assert sorgu(depo, "SELECT is_emri_no FROM plan_uretimleri")[0]["is_emri_no"] == rev["is_emri_no"]      # r01 üretime bağlandı
    assert uretici["cagri"] == 1                                                      # seçim LLM'i yeniden çağırmaz
    belge = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'document' ORDER BY olusturuldu DESC")[0]["govde"]
    assert "ÖN ONAYA SUNULAN TASLAK" in belge
    govde = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC")[0]["govde"]
    assert govde.startswith("Yeni plan") and "100 m², 3+1" in govde


def test_t2_numara_yazarak_secim(depo, wa, hizli_genel, uretici):
    t1(depo)
    assert depo.mesaj_kaydet(mesaj("1", talep("diger", "kısa cevap"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri" and son_rev(depo)["is_emri"]["yapi"]["kod"].startswith("YENI-")


def test_t4_uretim_gecmezse_uygulayamadim_ve_patron(depo, wa, hizli_genel, uretici):
    k = ornek("gecersiz_3arti1_dar_odalar")
    uretici["cevaplar"] = [k, k, k]
    r = t1(depo)
    assert r["eylem"] == "yonlendir" and "yeni plan üretilemedi" in r["gerekce"]
    govdeler = [x["govde"] for x in sorgu(depo, "SELECT govde FROM giden ORDER BY sira")]
    assert any("otomatik çizemedim" in g for g in govdeler)
    assert any(x["alici"] == "PATRON" for x in sorgu(depo, "SELECT alici FROM giden"))
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "uretilen_plan" not in d and "plan_istegi" not in d
    pr = sorgu(depo, "SELECT durum, plan_kodu, denemeler FROM plan_uretimleri")[0]
    assert pr["durum"] == "gecersiz" and pr["plan_kodu"] is None and len(pr["denemeler"]) == 3


def test_t5_onay_muhendis_kontrolune_gider(depo, wa, hizli_genel, uretici):
    import kalici
    depo.bayi_yaz("900000000303", ad="Deneme Mühendis", rol="muhendis")
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{st['adaylar'][0]['kod']}"))
    isle_hepsi(depo, URETIM)
    kalici.gonder(depo, wa)
    rev = son_rev(depo)
    time.sleep(1.1)
    assert depo.mesaj_kaydet(buton(f"o:{rev['is_emri_no']}:1"))
    [r] = isle_hepsi(depo, URETIM)
    assert r["gerekce"] == "plan onaylandı", r
    assert any("teknik kontrole gönderildi" in x["govde"] for x in sorgu(depo, "SELECT govde FROM giden WHERE kind = 'text'"))
    k = sorgu(depo, "SELECT durum, is_emri_no, rev FROM muhendis_kontrolleri")
    assert len(k) == 1 and k[0]["is_emri_no"] == rev["is_emri_no"] and k[0]["rev"] == 1


def _secilmis_yeni_plan(depo):
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{st['adaylar'][0]['kod']}"))
    isle_hepsi(depo, URETIM)
    time.sleep(1.1)


@pytest.fixture
def duzenleyici(monkeypatch):
    """`worker.plan_duzenle` → manuel arka uç (elle yazılmış düzeltilmiş plan); çağrı ve gelen metin tutulur."""
    from beyin import plan_uretici as PU
    durum = {"cevaplar": [], "cagri": 0, "metin": None}

    def sahte(plan, metin, talep_, ayar):
        durum["cagri"] += 1
        durum["metin"] = metin
        return PU.duzenle(plan, metin, talep_, hazir=durum["cevaplar"])
    monkeypatch.setattr(W, "plan_duzenle", sahte)
    return durum


def test_t3_yeni_plan_revizyonu_llm_once_dis_140_ve_salon(depo, wa, hizli_genel, uretici, duzenleyici):
    _secilmis_yeni_plan(depo)
    yeni = ornek("gecerli_3arti1_100")
    yeni["dis_karkas"] = 140
    yeni["dis_olcu"]["en"] = 1300                                                          # salon doğuya 50 cm büyür, ötekiler kayar
    for ad, r in (("Salon", [0, 0, 610, 450]), ("Yatak Odası 3", [0, 450, 350, 800]), ("Banyo", [350, 450, 610, 800]), ("Hol", [610, 0, 755, 800]),
                  ("Yatak Odası 1", [755, 0, 1300, 400]), ("Yatak Odası 2", [755, 400, 1300, 800])):
        next(m for m in yeni["mahaller"] if m["ad"] == ad)["dikdortgenler"] = [r]
    yeni["uygulanamayan"] = ["çift kat olsun"]
    duzenleyici["cevaplar"] = [yeni]
    assert depo.mesaj_kaydet(mesaj("dışlar 140'lık olsun, salonu biraz büyütelim, çift kat olsun", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri" and "LLM-önce" in r["gerekce"], r
    assert duzenleyici["cagri"] == 1 and "salonu biraz büyütelim" in duzenleyici["metin"]
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert rev["rev"] == 2 and y["degisiklikler"] == [] and isinstance(y["tanim"], dict) and isinstance(y["onceki"]["tanim"], dict)
    assert y["tanim"]["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2"
    assert any(f.startswith("Salon 25,2 → 27,") for f in y["uygulanan"]) and "dış duvarlar 140'lık karkas" in y["uygulanan"]
    assert "dış ölçü 1250×800 → 1300×800 cm" in y["uygulanan"]
    govde = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC")[0]["govde"]
    assert "Uygulanan:" in govde and "\"çift kat olsun\" isteğini otomatik uygulayamadım" in govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["uretilen_plan"]["plan"]["dis_karkas"] == 140 and d["uretilen_plan"]["tanim_sha256"] == y["tanim_sha256"]
    assert sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]["plan_duzenleme"]["durum"] == "gecerli"


def test_t3_yeni_plan_revizyonu_gecmezse_plan_degismez(depo, wa, hizli_genel, uretici, duzenleyici):
    _secilmis_yeni_plan(depo)
    k = ornek("gecersiz_3arti1_dar_odalar")
    duzenleyici["cevaplar"] = [k, k, k]
    assert depo.mesaj_kaydet(mesaj("salonu küçültelim", talep("revizyon", ozet="salonu küçült"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "yonlendir" and "revizyonu üretilemedi" in r["gerekce"]
    assert son_rev(depo)["rev"] == 1
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["revizyon"] == 0 and d["asama"] != "is_emri_hazir"


def test_yeniden_denenen_is_uretimi_tekrarlamaz(depo, uretici, monkeypatch):
    # iş satırında üretim sonucu varsa worker LLM'i çağırmaz (kalıcı akışın yeniden denemesi; ücret iki kez doğmaz)
    from beyin import plan_uretici as PU
    kabul(depo, YEDI)
    kayitli = PU.uret({"alan_m2": 95, "oda_programi": "3+1"}, hazir=[ornek("gecerli_3arti1_100")])
    import kalici
    k = kalici.BellekKonusma(NUMARA_A, None)
    g = mesaj("95 m² 3+1 tek kat çelik", T95, bayi=BAYI_KART)
    katalog = W.katalog_nesnesi(URETIM, kabul_edilmis=depo.kabul_edilmis_adaylar())
    cikti = W.isle(g, URETIM, k=k, cikarim={"talep": T95, "meta": {}, "plan_uretimi": kayitli}, katalog=katalog)
    assert cikti["sonuc"]["eylem"] == "secenek" and uretici["cagri"] == 0


def test_ayar_kapaliyken_bugunku_davranis(depo, wa, hizli_genel, uretici):
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik", T95, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, {**AYAR, "mesaj_katmani": True})
    assert r["eylem"] == "sor" and "model_veya_olcu" in r["gerekce"] and uretici["cagri"] == 0


# ───────────────────────── PR-3 · banka modelinde LLM-önce revizyon (llm_once_revizyon; elle yazılmış LLM cevapları) ─────────────────────────
def _islem(**k):
    return {"tur": k.pop("tur"), "aciklik": None, "adaylar": [], "en": None, "yuk": None, "cati_kodu": None, "alinti": "", **k}


def _llm_once(tmp_path, cevap: dict) -> dict:
    yol = tmp_path / "degisiklik.json"
    yol.write_text(json.dumps(cevap, ensure_ascii=False), encoding="utf-8")
    return {**AYAR, "mesaj_katmani": True, "llm_once_revizyon": {"acik": True, "backend": "manuel", "hazir_dosya": str(yol)}}


def _r01_c8801k(depo):
    from test_celik_akisi import r01
    kabul(depo)
    ilk = r01(depo, "Ç8801K")
    time.sleep(1.1)
    return ilk


def test_llm_once_pencere_olcusu_r02(depo, wa, hizli_genel, tmp_path):
    ilk = _r01_c8801k(depo)
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120, alinti="mutfak penceresi 120x120")]})
    assert depo.mesaj_kaydet(mesaj("mutfaktaki pencereyi 120ye 120 yapalım", talep("revizyon", ozet="mutfak penceresi"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri", r
    y = son_rev(depo)["is_emri"]["yapi"]
    assert [(d["op"], d["aciklik"], d["en"], d["yuk"]) for d in y["degisiklikler"]] == [("pencere_olcu", "P5", 120, 120)]
    c = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]
    assert c["degisiklik"]["durum"] == "tamam" and son_rev(depo)["proje_id"] == ilk["proje_id"]


def test_llm_once_cati_l(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="cati", cati_kodu="Ç8801L", alinti="çatıyı L yapalım")]})
    assert depo.mesaj_kaydet(mesaj("çatıyı diğer modeldeki gibi L yapalım", talep("revizyon", ozet="çatı"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri" and son_rev(depo)["is_emri"]["yapi"]["kod"] == "Ç8801L", r


def test_llm_once_iki_aday_bir_iki_hicbiri(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    from beyin import celik_okuma as CO, varyant
    t = json.loads((KOK / "modeller" / "C8801K.json").read_text(encoding="utf-8"))
    yasam = [p["aciklik"] for p in CO.pencere_adaylari(t, varyant._kur(t)) if p["mahal"] == "Yaşam Alanı"][:2]
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="belirsiz_pencere", adaylar=yasam, en=120, yuk=180, alinti="salonun penceresi")]})
    assert depo.mesaj_kaydet(mesaj("salonun penceresi 120x180 olsun", talep("revizyon", ozet="salon penceresi"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "sor" and r["gerekce"] == "eksik: okuma", r
    d, _ = depo.konusma_oku(NUMARA_A)
    assert [a["aciklik"] for a in d["okuma_bekleyen"]["adaylar"]] == yasam
    time.sleep(1.1)
    assert depo.mesaj_kaydet(buton("q:okuma:2"))
    [r2] = isle_hepsi(depo, ayar)
    assert r2["eylem"] == "is_emri" and son_rev(depo)["is_emri"]["yapi"]["degisiklikler"][0]["aciklik"] == yasam[1], r2


def test_llm_once_s2_ikinci_istek_sessiz_dusmez(depo, wa, hizli_genel, tmp_path):
    # S2 (İE-08 › Bilinen sınırlama): "salonu büyütüp mutfak penceresini 120x120 yapalım" — kural okumasında salon isteği sessiz düşüyordu
    _r01_c8801k(depo)
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="uygulanamaz", alinti="salonu büyütüp"),
                                             _islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120, alinti="mutfak penceresini 120x120")]})
    assert depo.mesaj_kaydet(mesaj("salonu büyütüp mutfak penceresini 120x120 yapalım", talep("revizyon", ozet="salon ve mutfak"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "yonlendir" and "otomatik uygulanamıyor" in r["gerekce"], r
    govde = sorgu(depo, "SELECT govde FROM giden WHERE alici <> 'PATRON' ORDER BY olusturuldu DESC, sira")[0]["govde"]
    assert "\"salonu büyütüp\" isteğini otomatik uygulayamadım" in govde
    assert son_rev(depo)["rev"] == 1                                                    # plan değişmedi; hak düşmez


def test_llm_once_s7_ondalikli_olcu_yuvarlanmaz(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="pencere_olcu", aciklik="P5", en=125, yuk=182.5, alinti="125x182,5")]})
    assert depo.mesaj_kaydet(mesaj("mutfak penceresi 125x182,5 olsun", talep("revizyon", ozet="mutfak penceresi"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "yonlendir" and son_rev(depo)["rev"] == 1
    assert "ondalıklı ölçü" in sorgu(depo, "SELECT govde FROM giden WHERE alici <> 'PATRON' ORDER BY olusturuldu DESC, sira")[0]["govde"]


def test_llm_once_kapaliyken_kural_okumasi(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    assert depo.mesaj_kaydet(mesaj("mutfak penceresi 120x120 olsun", talep("revizyon", ozet="mutfak penceresi 120x120",
                                                                           pencereler=[{"mahal": "mutfak", "olcu": "120x120", "islem": "degistir"}]), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, {**AYAR, "mesaj_katmani": True})
    assert r["eylem"] == "is_emri" and "llm_degisiklik" not in r and sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"].get("degisiklik") is None


# ───────────────────────── kapanış incelemesi düzeltmeleri (14.10) ─────────────────────────
def test_kart_tasinan_yerde_ve_konusmada_guncel(depo, wa, hizli_genel, uretici):
    t1(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    g = d["uretilen_plan"]["gorsel"]
    assert g and Path(g).is_file() and str(W.KANAL / "projects") in g and ".hazirlik" not in g
    assert d["secenek_seti"]["adaylar"][0]["gorsel"] == g


def test_llm_okumasi_hata_donerse_kural_okumasi_cati_L(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    yol = tmp_path / "bozuk.json"
    yol.write_text(json.dumps({"islemler": [{"tur": "bilinmeyen"}]}), encoding="utf-8")     # şema dışı → okuma 'hata'
    ayar = {**AYAR, "mesaj_katmani": True, "llm_once_revizyon": {"acik": True, "backend": "manuel", "hazir_dosya": str(yol)}}
    assert depo.mesaj_kaydet(mesaj("çatı L olsun", talep("revizyon", ozet="çatı L"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri" and son_rev(depo)["is_emri"]["yapi"]["kod"] == "Ç8801L", r
    assert sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]["degisiklik"]["durum"] == "hata"


def test_llm_okumasi_dis_140_yinelenmez(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="dis_karkas_140", alinti="dışlar 140")]})
    assert depo.mesaj_kaydet(mesaj("dışlar 140'lık olsun", talep("revizyon", ozet="dış 140"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri"
    time.sleep(1.1)
    ayar = _llm_once(tmp_path, {"islemler": [_islem(tur="dis_karkas_140", alinti="dışlar 140 kalsın"),
                                             _islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120, alinti="mutfak 120x120")]})
    assert depo.mesaj_kaydet(mesaj("dışlar 140 kalsın, mutfak penceresi 120x120", talep("revizyon", ozet="mutfak"), bayi=BAYI_KART))
    [r2] = isle_hepsi(depo, ayar)
    assert r2["eylem"] == "is_emri", r2
    assert [d["op"] for d in son_rev(depo)["is_emri"]["yapi"]["degisiklikler"]] == ["dis_karkas_140", "pencere_olcu"]


def test_yeniden_denemede_eski_plana_karsi_okuma_kullanilmaz(monkeypatch):
    from beyin.sema import Talep
    sayac = {"n": 0}

    def sahte(son_y, metin, katalog, ayar):
        sayac["n"] += 1
        return {"durum": "tamam", "islemler": [], "bilgi": []}
    monkeypatch.setattr(W, "degisiklik_oku", sahte)
    k = type("K", (), {"d": {"asama": "onay_bekliyor", "revizyon": 0, "son_is_emri": {"is_emri_no": "PM-X-1", "revizyon": 2,
                                                                                      "yapi": {"sistem": "celik", "kod": "Ç8801K"}}}})()
    t = Talep(niyet="revizyon", guven="yuksek", ozet="x")
    ayar = {"llm_once_revizyon": {"acik": True}}
    g = {"text": "mutfak 120x120 olsun"}
    _, lo = W.llm_once_revizyon(k, t, g, None, {"degisiklik": {"durum": "tamam", "islemler": [], "_temel": "PM-X-1:1"}}, ayar, None, None)
    assert sayac["n"] == 1 and lo["_temel"] == "PM-X-1:2"                               # r01'e karşı hesaplanmış eski okuma kullanılmadı
    _, lo = W.llm_once_revizyon(k, t, g, None, {"degisiklik": lo}, ayar, None, None)
    assert sayac["n"] == 1                                                               # aynı plana karşı olan yeniden kullanıldı
    k.d["son_soru_alani"] = "secenek"
    assert W.llm_once_revizyon(k, t, g, None, None, ayar, None, None) == (None, None) and sayac["n"] == 1   # set açıkken ücretli çağrı yok
