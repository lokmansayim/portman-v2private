"""İE-14 PR-2 / r3 · talepten plana, kanal (kalıcı akış, gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp). r3: üretici LLM'siz
koşar (program → bankadan uyarlama → çözücü); yeni plan revizyonu kayıtlı işlem listesiyle (`plan_islem`, manuel arka uç). LLM çağrısı yok.

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

from conftest import AYAR, NUMARA_A, mesaj, sorgu, talep, tek
from test_celik_akisi import BAYI_KART, YEDI, buton, hizli_genel, isle_hepsi, kabul, son_rev  # noqa: F401 (fikstür)

import worker as W
from psycopg.types.json import Jsonb

KOK = Path(__file__).resolve().parents[2]
ORNEK = KOK / "testler" / "plan" / "ornekler"
URETIM = {**AYAR, "mesaj_katmani": True, "plan_uretimi": {"acik": True}}
T95 = talep(ozet="95 m² 3+1 tek kat çelik, kırma çatı", alan_m2=95, oda_programi="3+1", yapi_turu="celik", kat_sayisi=1, cati={"tip": "kirma"})


def ornek(ad):
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


@pytest.fixture
def uretici(monkeypatch):
    """`worker.plan_uret` → gerçek üretici, LLM kapalı (r3: yapısal talepte LLM gerekmez); çağrı sayısı ve gelen talep tutulur.
    `durum["talep_ezme"]` verilirse üretim o taleple yapılır (ör. sığmayan program)."""
    from beyin import plan_uretici as PU
    durum = {"cagri": 0, "talep": None, "talep_ezme": None}

    def sahte(talep_, ayar):
        durum["cagri"] += 1
        durum["talep"] = talep_
        return PU.uret(durum["talep_ezme"] or talep_, ayar={"acik": False})
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
    assert kodlar[0].startswith("YENI-") and kodlar[1].startswith("YENI-") and kodlar[0] != kodlar[1]
    assert kodlar[2:] == ["KT03"]                                                    # r3: iki yeni plan + brüt alana en yakın banka modeli (94)
    assert st["adaylar"][0]["tanim"] is None                                         # set kaydı tanımı taşımaz; konuşmada
    satirlar = sorgu(depo, "SELECT kind, govde, satir FROM giden ORDER BY olusturuldu, sira")      # gönderim sırası
    assert satirlar[0]["kind"] == "text" and "yeni bir plan taslağı hazırlıyorum" in satirlar[0]["govde"]
    s = satirlar[1]["satir"]
    assert [b["reply"]["title"] for b in s["interactive"]["action"]["buttons"]][:2] == ["1. Yeni plan", "2. Yeni plan 2"]
    assert "2 yeni plan taslağı" in s["body"] and "1. Yeni plan · " in s["body"] and "TASLAK, programdan çözüldü" in s["body"]
    yeni_satirlar = [x for x in s["body"].splitlines() if x.startswith(("1.", "2."))]
    assert "(bankadan en yakın)" in s["body"] and len(yeni_satirlar) == 2
    assert not any(c in x for x in yeni_satirlar for c in ("KT", "Ç8", "C8"))           # uyarlama kaynağı bayiye adsız (P5)
    d, _ = depo.konusma_oku(NUMARA_A)
    u = d["uretilen_plan"]
    assert u["kod"] == kodlar[0] and isinstance(u["tanim"], dict) and u["durum"] == "uretilen" and "plan_istegi" not in d
    assert [x["kod"] for x in d["uretilen_planlar"]] == kodlar[:2]
    c = sorgu(depo, "SELECT cikarim FROM isler")[0]["cikarim"]
    pu = c["plan_uretimi"]
    assert pu["durum"] == "gecerli" and len(pu["adaylar"]) == 2 and pu["cagri"] == 0 and pu["denemeler"][0]["basamak"] == "uyarlama+cozucu"
    assert c["talep"]["oda_programi"] == "3+1"                                       # çıkarım kaydı korunur
    pr = sorgu(depo, "SELECT durum, plan_kodu, cagri, talep, denemeler, is_emri_no, yol, sure_ms, adaylar FROM plan_uretimleri")     # göç 007
    assert len(pr) == 1 and pr[0]["durum"] == "gecerli" and pr[0]["plan_kodu"] == kodlar[0] and pr[0]["cagri"] == 0
    assert pr[0]["yol"] in ("uyarlama", "cozucu") and pr[0]["sure_ms"] >= 0
    assert [x["kod"] for x in pr[0]["adaylar"]] == kodlar[:2]
    dg = pr[0]["adaylar"][0]["dogrulama"]["kalemler"]
    assert dg["geometri"]["durum"] == "GECTI" and dg["yapisal"]["durum"] == "YAPILMADI" and dg["muhendis_kabulu"]["durum"] == "YAPILMADI"
    assert dg["cizim"]["durum"] in ("GECTI", "KALDI")                               # sahte genel motor (hizli_genel); gerçeği e2e bölüm 12'de
    assert pr[0]["talep"]["oda_programi"] == "3+1" and pr[0]["is_emri_no"] is None and NUMARA_A not in json.dumps(pr[0]["talep"])
    assert Path(u["gorsel"]).with_name("dogrulama.json").is_file()                   # rapor kartın klasöründe (bayiye gitmez)


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
    assert uretici["cagri"] == 1                                                      # seçim üretimi yeniden çağırmaz
    belge = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'document' ORDER BY olusturuldu DESC")[0]["govde"]
    assert "ÖN ONAYA SUNULAN TASLAK" in belge
    govde = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC")[0]["govde"]
    assert govde.startswith("Yeni plan") and "3+1" in govde


def test_t2_ikinci_yeni_plan_secilir_ve_uretime_baglanir(depo, wa, hizli_genel, uretici):
    from beyin import celik as C
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    ikinci = st["adaylar"][1]["kod"]
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{ikinci}"))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri", r
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert y["kod"] == ikinci and y["gosterim"] == "Yeni plan 2" and C.tanim_dogrula(y)
    pr = sorgu(depo, "SELECT is_emri_no, plan_kodu FROM plan_uretimleri")[0]
    assert pr["is_emri_no"] == rev["is_emri_no"] and pr["plan_kodu"] == ikinci
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["uretilen_plan"]["kod"] == ikinci


def test_t2_numara_yazarak_secim(depo, wa, hizli_genel, uretici):
    t1(depo)
    assert depo.mesaj_kaydet(mesaj("1", talep("diger", "kısa cevap"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri" and son_rev(depo)["is_emri"]["yapi"]["kod"].startswith("YENI-")


def test_t4_uretim_gecmezse_uygulayamadim_ve_patron(depo, wa, hizli_genel, uretici):
    uretici["talep_ezme"] = {"alan_m2": 45, "oda_programi": "3+1"}              # 45 m²'ye 3+1 sığmaz (LLM kapalı: son basamak yok)
    r = t1(depo)
    assert r["eylem"] == "yonlendir" and "yeni plan üretilemedi" in r["gerekce"]
    govdeler = [x["govde"] for x in sorgu(depo, "SELECT govde FROM giden ORDER BY sira")]
    assert any("otomatik çizemedim" in g for g in govdeler)
    assert any(x["alici"] == "PATRON" for x in sorgu(depo, "SELECT alici FROM giden"))
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "uretilen_plan" not in d and "plan_istegi" not in d
    pr = sorgu(depo, "SELECT durum, plan_kodu, denemeler FROM plan_uretimleri")[0]
    assert pr["durum"] == "gecersiz" and pr["plan_kodu"] is None and pr["denemeler"][0]["aday"] == 0 and pr["denemeler"][0]["ihlaller"]


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
    """`worker.plan_duzenle` → `plan_islem.duzenle` manuel arka uçla (kayıtlı işlem listesi); çağrı ve gelen metin tutulur."""
    from beyin import plan_islem as PI
    durum = {"cevap": {"islemler": [], "uygulanamayan": []}, "cagri": 0, "metin": None, "plan": None}

    def sahte(plan, metin, talep_, ayar):
        durum["cagri"] += 1
        durum["metin"] = metin
        durum["plan"] = plan
        return PI.duzenle(plan, metin, talep_, hazir=durum["cevap"])
    monkeypatch.setattr(W, "plan_duzenle", sahte)
    return durum


def _dis_yon(plan: dict, ad: str) -> str:
    """Mahalin dış cepheye değen bir yanı (G/K/B/D): oda o yönde büyütülünce bina büyür."""
    W, H = plan["dis_olcu"]["en"], plan["dis_olcu"]["boy"]
    ver = [r for m in plan["mahaller"] if m["islev"] == "veranda" for r in m["dikdortgenler"]]
    r = max(next(m for m in plan["mahaller"] if m["ad"] == ad)["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
    for yon, ok in (("B", r[0] == 0), ("D", r[2] == W), ("G", r[1] == 0), ("K", r[3] == H)):
        if ok and not ver:
            return yon
    raise AssertionError("dış yan yok")


def test_t3_yeni_plan_revizyonu_islemlerle_dis_140_ve_salon(depo, wa, hizli_genel, uretici, duzenleyici):
    _secilmis_yeni_plan(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    plan = d["uretilen_plan"]["plan"]
    salon = next(m["ad"] for m in plan["mahaller"] if m["islev"] == "salon")
    duzenleyici["cevap"] = {"islemler": [{"op": "dis_karkas_140"}, {"op": "oda_buyut", "mahal": salon, "yon": _dis_yon(plan, salon), "cm": 50,
                                                                    "alinti": "salonu biraz büyütelim"}],
                            "uygulanamayan": ["çift kat olsun"]}
    assert depo.mesaj_kaydet(mesaj("dışlar 140'lık olsun, salonu biraz büyütelim, çift kat olsun", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri" and "LLM-önce" in r["gerekce"], r
    assert duzenleyici["cagri"] == 1 and "salonu biraz büyütelim" in duzenleyici["metin"]
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert rev["rev"] == 2 and y["degisiklikler"] == [] and isinstance(y["tanim"], dict) and isinstance(y["onceki"]["tanim"], dict)
    assert y["tanim"]["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2"
    assert any(f.startswith(f"{salon} ") and "→" in f for f in y["uygulanan"]) and "dış duvarlar 140'lık karkas" in y["uygulanan"]
    assert any(f.startswith("dış ölçü ") for f in y["uygulanan"])                      # salon dış cepheye doğru: bina büyüdü
    govde = sorgu(depo, "SELECT govde FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC")[0]["govde"]
    assert "Uygulanan:" in govde and "\"çift kat olsun\" isteğini otomatik uygulayamadım" in govde
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["uretilen_plan"]["plan"]["dis_karkas"] == 140 and d["uretilen_plan"]["tanim_sha256"] == y["tanim_sha256"]
    assert sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]["plan_duzenleme"]["durum"] == "gecerli"


def test_c1_ilk_mesajda_dis_140_secimde_yinelenmez(depo, wa, hizli_genel, uretici):
    # inceleme C1: "dış duvarlar 140 olsun" üretimde uygulanır; seçimde saklanan istek ikinci kez uygulanıp Patron'a düşürmez
    kabul(depo, YEDI)
    tl = talep(ozet="95 m² 3+1 tek kat çelik, dış duvarlar 140", alan_m2=95, oda_programi="3+1", yapi_turu="celik", kat_sayisi=1,
               ozel_istekler=["dış duvarlar 140 olsun"])
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik, dış duvarlar 140 olsun", tl, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "secenek", r
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{st['adaylar'][0]['kod']}"))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri", r
    y = son_rev(depo)["is_emri"]["yapi"]
    assert y["tanim"]["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2" and y["degisiklikler"] == []


def test_c2_islemsiz_revizyon_konusmayi_kapatmaz(depo, wa, hizli_genel, uretici, duzenleyici):
    # inceleme C2: işlem çıkmayan mesaj (değişiklik isteği yok) sorulur; taslak ve hak kalır, ardından onay çalışır
    _secilmis_yeni_plan(depo)
    duzenleyici["cevap"] = {"islemler": [], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("tamam bir bakalım", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "sor" and duzenleyici["cagri"] == 1, r
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] not in ("yonlendirildi", "is_emri_hazir") and d["uretilen_plan"] and d["revizyon"] == 0
    assert son_rev(depo)["rev"] == 1
    son = sorgu(depo, "SELECT govde FROM giden ORDER BY is_id DESC, sira")[0]["govde"]
    assert "Planda neyi değiştirelim?" in son and "Lokman" not in son


def test_c2_sorudan_sonra_cevap_llm_duzenleyicisine_gider(depo, wa, hizli_genel, uretici, duzenleyici):
    # ikinci tur bulgu 1: soru okuma alanı bırakmaz; bayinin cevabı ("salonu 50 cm büyüt") Patron'a değil düzenleyiciye gider
    _secilmis_yeni_plan(depo)
    duzenleyici["cevap"] = {"islemler": [], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("tamam bir bakalım", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "sor", r
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor" and d["son_soru_alani"] == "yeni_plan_degisiklik"
    plan = d["uretilen_plan"]["plan"]
    salon = next(m["ad"] for m in plan["mahaller"] if m["islev"] == "salon")
    duzenleyici["cevap"] = {"islemler": [{"op": "oda_buyut", "mahal": salon, "yon": _dis_yon(plan, salon), "cm": 50, "alinti": "salonu 50 cm büyüt"}],
                            "uygulanamayan": []}
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("salonu 50 cm büyüt", talep("revizyon", ozet="salon büyüt"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert duzenleyici["cagri"] == 2 and r["eylem"] == "is_emri" and "LLM-önce" in r["gerekce"], r


def test_c2_zaten_uygulanmis_islem_zaten_var_der(depo, wa, hizli_genel, uretici, duzenleyici):
    # ikinci tur bulgu 6: işlem okundu ama plan zaten öyle → "planda zaten var" (bayinin cümlesi örnek diye geri önerilmez)
    _secilmis_yeni_plan(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    tip = (d["uretilen_plan"]["plan"].get("cati") or {}).get("tip") or "besik"
    duzenleyici["cevap"] = {"islemler": [{"op": "cati_tipi", "tip": tip, "alinti": "çatı aynı olsun"}], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("çatı böyle olsun", talep("revizyon", ozet="çatı"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "sor", r
    son = sorgu(depo, "SELECT govde FROM giden ORDER BY is_id DESC, sira")[0]["govde"]
    assert "planda zaten var" in son and "Onayla" in son and "çatı kırma olsun" not in son          # aynı istek yeniden önerilmez


def test_c2_bilgiyle_gelen_okunamayan_istek_sessiz_dusmez(depo, wa, hizli_genel, uretici, duzenleyici):
    # ikinci tur bulgu 7: müşteri bilgisi + değişiklik isteği, LLM işlem çıkarmadı → plan bilgiyle yeniden çizilmez, yönlendirilir
    _secilmis_yeni_plan(depo)
    duzenleyici["cevap"] = {"islemler": [], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("müşteri Ahmet Bey, mutfak penceresi 120x120 olsun",
                                   talep("revizyon", ozet="revizyon", musteri={"ad": "Ahmet Bey"}), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "yonlendir" and "okunamadı" in r["gerekce"], r
    assert son_rev(depo)["rev"] == 1


def test_c1_hazir_140_modelde_dis_140_zaten_der(depo, wa, hizli_genel):
    # ikinci tur bulgu 5: KT-03 (dış zaten 140) revizyonunda "dışlar 140" → aynı öneriyle geri sorulmaz, "zaten 140" denir
    from test_celik_akisi import r01
    kabul(depo, YEDI)
    r01(depo, "KT03")
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("dış duvarlar 140'lık olsun", talep("revizyon", ozet="dış 140"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, {**AYAR, "mesaj_katmani": True})
    assert r["eylem"] == "sor", r
    assert "zaten 140'lık" in sorgu(depo, "SELECT govde FROM giden ORDER BY is_id DESC, sira")[0]["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor"                                            # mesajın söylediği Onayla çalışır (dördüncü tur)


@pytest.mark.parametrize("istek", ["salonu 50 cm büyüt", "yatak odasını küçült", "mutfağa kapı ekleyin", "çatı kırma olsun"])
def test_c2_bilgiyle_gelen_oda_istegi_de_dusmez(depo, wa, hizli_genel, uretici, duzenleyici, istek):
    # kod incelemesi üçüncü tur A: oda büyütme, kapı ve çatı istekleri de (yalnız pencere değil) bilgiyle gelince sessiz düşmez
    _secilmis_yeni_plan(depo)
    duzenleyici["cevap"] = {"islemler": [], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj(f"müşteri Ahmet Bey, {istek}", talep("revizyon", ozet="revizyon", musteri={"ad": "Ahmet Bey"}),
                                   bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "yonlendir" and "okunamadı" in r["gerekce"], r
    assert son_rev(depo)["rev"] == 1


def test_c2_yalniz_bilgi_plani_antetle_yeniden_cizer(depo, wa, hizli_genel, uretici, duzenleyici):
    # bilgi dışında cümle yoksa banka yoluyla aynı: plan antet bilgisiyle yeniden (yönlendirme yok)
    _secilmis_yeni_plan(depo)
    duzenleyici["cevap"] = {"islemler": [], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("müşteri Ahmet Bey", talep("revizyon", ozet="müşteri bilgisi", musteri={"ad": "Ahmet Bey"}), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "is_emri", r


def test_c2_sorudan_sonra_onay_soruyu_kapatir(depo, wa, hizli_genel, uretici, duzenleyici):
    # kod incelemesi üçüncü tur B: soru alanı onayla temizlenir
    _secilmis_yeni_plan(depo)
    duzenleyici["cevap"] = {"islemler": [], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("tamam bir bakalım", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    isle_hepsi(depo, URETIM)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["son_soru_alani"] == "yeni_plan_degisiklik"
    # karar katmanı (kalıcı akışın onay denetimi PDF'in teslim bildirimini ister; bu test onu kurmaz)
    import kalici
    from beyin.karar import karar_ver
    from beyin.sema import Talep
    k = kalici.BellekKonusma(NUMARA_A, d)
    kr = karar_ver(Talep.model_validate(talep("onay", ozet="onay")), k, BAYI_KART, W.katalog_nesnesi(URETIM, kabul_edilmis=depo.kabul_edilmis_adaylar()),
                   metin="onaylıyorum")
    assert kr.gerekce == "plan onaylandı" and k.d["asama"] == "onaylandi" and k.d["son_soru_alani"] is None


def test_t3_yeni_plan_revizyonu_gecmezse_plan_degismez(depo, wa, hizli_genel, uretici, duzenleyici):
    _secilmis_yeni_plan(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    plan = d["uretilen_plan"]["plan"]
    salon = next(m["ad"] for m in plan["mahaller"] if m["islev"] == "salon")
    duzenleyici["cevap"] = {"islemler": [{"op": "kapi_kaldir", "mahal": salon, "mahal_b": "Hol"}], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("salonla hol arasındaki kapıyı kaldırın", talep("revizyon", ozet="kapı kaldır"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "yonlendir" and "revizyonu üretilemedi" in r["gerekce"]
    assert son_rev(depo)["rev"] == 1
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["revizyon"] == 0 and d["asama"] != "is_emri_hazir"


def test_k1_olcu_notu_ve_yuvarlama_bayiye_yazilir(depo, wa, hizli_genel, uretici):
    # inceleme G1/G2 (15.10): döndürülmüş aday ve 5 cm yuvarlama bayiye yazılır; "Birini seçin" 1024 sınırında kesilmez
    kabul(depo, YEDI)
    tl = talep(ozet="12,02 × 8 m 3+1 tek kat çelik", oda_programi="3+1", yapi_turu="celik", kat_sayisi=1, dis_olcu={"en_m": 12.02, "boy_m": 8})
    assert depo.mesaj_kaydet(mesaj("12,02 x 8 m 3+1 tek kat çelik", tl, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "secenek", r
    body = sorgu(depo, "SELECT satir FROM giden ORDER BY olusturuldu, sira")[1]["satir"]["body"]
    assert "Not: dış ölçü 12,02 × 8 m, 5 cm ızgaraya 12 × 8 m olarak alındı" in body
    satir1, satir2 = (next(x for x in body.splitlines() if x.startswith(n)) for n in ("1.", "2."))
    # iki yön de ölçüyü tutar (talep şemasında en/boy kısa/uzun kenardır, ön cephe değil; ikinci tur): ikisi de notsuz
    assert "(" not in satir1.split("TASLAK")[1] and "(" not in satir2.split("TASLAK")[1]
    assert body.endswith("Birini seçin (düğme ya da numara).")


def test_c7_hazirliyorum_uretimden_once_kayitta(depo, wa, hizli_genel, monkeypatch):
    # inceleme C7: "hazırlıyorum" satırı üretim başlamadan giden tablosunda 'bekliyor' (gönderici hemen alır); iş bitince yinelenmez
    from beyin import plan_uretici as PU
    gorulen = {}

    def sahte(talep_, ayar):
        gorulen["satir"] = sorgu(depo, "SELECT durum FROM giden WHERE govde LIKE %s", "%hazırlıyorum%")
        return PU.uret(talep_, ayar={"acik": False})
    monkeypatch.setattr(W, "plan_uret", sahte)
    r = t1(depo)
    assert r["eylem"] == "secenek", r
    assert [x["durum"] for x in gorulen["satir"]] == ["bekliyor"]
    hepsi = sorgu(depo, "SELECT sira, govde FROM giden ORDER BY olusturuldu, sira")
    assert sum("hazırlıyorum" in x["govde"] for x in hepsi) == 1 and "hazırlıyorum" in hepsi[0]["govde"]
    assert hepsi[0]["sira"] == depo.ERKEN_SIRA and hepsi[1]["sira"] == 1          # ayrılmış sıra; ajan satırları 1'den


def test_c7_uretim_patlarsa_hata_mesaji_gider_dongu_yok(depo, wa, hizli_genel, monkeypatch):
    # erken "hazırlıyorum"dan sonra beklenmeyen hata: hata yolu sıra 1'le çakışıp işi sonsuz döngüye sokmaz; bayi hata mesajını alır
    import depo as D

    def patlar(talep_, ayar):
        raise RuntimeError("deneme")
    monkeypatch.setattr(W, "plan_uret", patlar)
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik, kırma çatı", T95, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["durum"] == "basarisiz" and r["eylem"] == "hata", r
    hepsi = {x["sira"]: x for x in sorgu(depo, "SELECT sira, alici, govde FROM giden")}
    assert "hazırlıyorum" in hepsi[depo.ERKEN_SIRA]["govde"] and hepsi[1]["govde"] == D.HATA_BAYIYE


def test_c7_basarisiz_is_hata_mesaji_hazirliyorumla_cakismaz(depo):
    # erken "hazırlıyorum" ayrılmış sırada (99); iş başarısız sayılırsa bayinin hata mesajı sıra 1'e yazılır (çakışmaz, düşmez)
    import depo as D
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik", T95, bayi=BAYI_KART))
    al = depo.is_al("deneme")
    g = al["gelen"]
    s = W.giden_metin(g, "Sizin için yeni bir plan taslağı hazırlıyorum", depo.ERKEN_SIRA)
    assert depo.ara_satir_yaz(al["is"]["id"], "deneme", g["id"], s) and depo.ara_satir_yaz(al["is"]["id"], "deneme", g["id"], s)
    assert not depo.ara_satir_yaz(al["is"]["id"], "baskasi", g["id"], {**s, "id": s["id"] + "x"})      # kira başkasında: yazılmaz
    with depo.baglan() as c, c.transaction():
        depo._basarisiz_yaz(c, al["is"], g, "deneme")
    satirlar = {x["sira"]: x for x in sorgu(depo, "SELECT sira, alici, govde FROM giden")}
    assert "hazırlıyorum" in satirlar[depo.ERKEN_SIRA]["govde"]
    assert satirlar[1]["alici"] == g["sender"] and satirlar[1]["govde"] == D.HATA_BAYIYE


def test_c7_yeniden_denenen_is_baska_karar_verse_de_dongu_yok(depo, wa, hizli_genel, uretici):
    # ikinci tur bulgu 2: erken satır kalıcı yazıldıktan sonra iş düşer, yeniden denemede karar değişir (ör. üretim kapatıldı) → sıra 1'e
    # başka satır gelir; erken satır ayrılmış sırada olduğu için kayıt çakışmaz, iş biter
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik, kırma çatı", T95, bayi=BAYI_KART))
    al = depo.is_al("eski-isleyici", kira_sn=1)
    g = al["gelen"]
    assert depo.ara_satir_yaz(al["is"]["id"], "eski-isleyici", g["id"], W.giden_metin(g, "… hazırlıyorum", depo.ERKEN_SIRA))
    time.sleep(1.2)                                                                   # kira doldu: iş yeniden alınır
    [r] = isle_hepsi(depo, {**AYAR, "mesaj_katmani": True})                          # üretim kapalı: başka karar (katalog sorusu)
    assert r["durum"] == "bitti" and r["eylem"] == "sor", r
    assert {x["sira"] for x in sorgu(depo, "SELECT sira FROM giden")} >= {1, depo.ERKEN_SIRA}


def test_yeniden_denenen_is_uretimi_tekrarlamaz(depo, uretici, monkeypatch):
    # iş satırında üretim sonucu varsa worker LLM'i çağırmaz (kalıcı akışın yeniden denemesi; ücret iki kez doğmaz)
    from beyin import plan_uretici as PU
    kabul(depo, YEDI)
    kayitli = PU.uret({"alan_m2": 95, "oda_programi": "3+1"}, ayar={"acik": False})
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
    g2 = d["uretilen_planlar"][1]["gorsel"]                                         # r3: ikinci yeni planın kartı da taşındı
    assert g2 and Path(g2).is_file() and ".hazirlik" not in g2 and d["secenek_seti"]["adaylar"][1]["gorsel"] == g2


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


# ───────────────────────── r3 · P4: LLM-önce okuma gölgede (kural karar verir, LLM kayda; göç 008) ─────────────────────────
def _golge(tmp_path, cevap: dict) -> dict:
    yol = tmp_path / "golge.json"
    yol.write_text(json.dumps(cevap, ensure_ascii=False), encoding="utf-8")
    return {**AYAR, "mesaj_katmani": True, "llm_once_revizyon": {"mod": "golge", "backend": "manuel", "hazir_dosya": str(yol)}}


def test_golge_ayni_okuma_kural_karar_verir_kiyas_kaydi(depo, wa, hizli_genel, tmp_path):
    ilk = _r01_c8801k(depo)
    ayar = _golge(tmp_path, {"islemler": [_islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120, alinti="mutfak penceresi 120x120")]})
    assert depo.mesaj_kaydet(mesaj("mutfak penceresi 120x120 olsun", talep("revizyon", ozet="mutfak penceresi"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri", r
    sn = sorgu(depo, "SELECT sonuc FROM isler ORDER BY id DESC")[0]["sonuc"]
    assert "llm_degisiklik" not in sn and sn["okuma_kiyasi"]["sinif"] == "aynı", sn
    y = son_rev(depo)["is_emri"]["yapi"]
    assert [(d["op"], d["aciklik"], d["en"], d["yuk"]) for d in y["degisiklikler"]] == [("pencere_olcu", "P5", 120, 120)]
    ok = sorgu(depo, "SELECT sinif, model, kural, llm, is_emri_no, rev FROM okuma_kiyaslari")
    # inceleme C8: kayıt okunan planın (r01) numarasını taşır, bu işin ürettiği r02'yi değil
    assert len(ok) == 1 and ok[0]["sinif"] == "aynı" and ok[0]["model"] == "Ç8801K" and ok[0]["rev"] == 1 and ok[0]["is_emri_no"] == ilk["is_emri_no"]
    assert ok[0]["kural"]["ogeler"] == [["pencere", "P5", 120, 120]] and "mutfak" not in json.dumps(ok[0])     # metin satırda yok
    assert sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]["degisiklik_golge"]["durum"] == "tamam"


def test_kv1_kiyas_kaydinda_cumle_parcasi_yok(depo, wa, hizli_genel, tmp_path):
    # inceleme KV1: okunamayan cümle kayda metin olarak değil sayı olarak girer (ad maskelenmez; göç 008 yalnız yapı ve sayı)
    _r01_c8801k(depo)
    ayar = _golge(tmp_path, {"islemler": [_islem(tur="pencere_olcu", aciklik="P5", en=120, yuk=120, alinti="mutfak penceresi 120x120"),
                                          _islem(tur="uygulanamaz", alinti="salona Zeynep Hanım için şömine")]})
    assert depo.mesaj_kaydet(mesaj("mutfak penceresi 120x120 olsun. salona Zeynep Hanım için şömine koyalım",
                                   talep("revizyon", ozet="mutfak penceresi"), bayi=BAYI_KART))
    isle_hepsi(depo, ayar)
    ok = sorgu(depo, "SELECT kural, llm FROM okuma_kiyaslari")
    assert len(ok) == 1
    ham = json.dumps(ok[0], ensure_ascii=False)
    assert "Zeynep" not in ham and "şömine" not in ham and "mutfak" not in ham, ham
    assert ok[0]["kural"]["okunamayan_n"] >= 1 and "okunamayan" not in ok[0]["kural"]


def test_golge_farkli_okumada_karar_yine_kuralin(depo, wa, hizli_genel, tmp_path):
    _r01_c8801k(depo)
    ayar = _golge(tmp_path, {"islemler": [_islem(tur="pencere_olcu", aciklik="P6", en=120, yuk=180, alinti="yanlış okuma")]})
    assert depo.mesaj_kaydet(mesaj("mutfak penceresi 120x120 olsun", talep("revizyon", ozet="mutfak penceresi"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri"
    assert sorgu(depo, "SELECT sonuc FROM isler ORDER BY id DESC")[0]["sonuc"]["okuma_kiyasi"]["sinif"] == "farklı"
    y = son_rev(depo)["is_emri"]["yapi"]
    assert [(d["aciklik"], d["en"], d["yuk"]) for d in y["degisiklikler"]] == [("P5", 120, 120)]    # kuralın okuması uygulandı
    assert sorgu(depo, "SELECT sinif FROM okuma_kiyaslari")[0]["sinif"] == "farklı"


def test_okuma_modu_geriye_uyum():
    assert W.okuma_modu({}) == "kapali" and W.okuma_modu({"acik": True}) == "acik"
    assert W.okuma_modu({"acik": True, "mod": "golge"}) == "golge" and W.okuma_modu({"mod": "kapali", "acik": True}) == "kapali"


def test_c5_ayar_dosyasindan_geriye_uyum(tmp_path):
    # inceleme C5: varsayılan `mod`'u birleştirmez; dosyada yalnız `acik: true` → acik (belgelenen geriye uyum)
    import ayarlar
    (tmp_path / ayarlar.DOSYA).write_text(json.dumps({"llm_once_revizyon": {"acik": True}}), encoding="utf-8")
    assert W.okuma_modu(ayarlar.oku(tmp_path)["llm_once_revizyon"]) == "acik"
    (tmp_path / ayarlar.DOSYA).write_text(json.dumps({"llm_once_revizyon": {"acik": True, "mod": "golge"}}), encoding="utf-8")
    assert W.okuma_modu(ayarlar.oku(tmp_path)["llm_once_revizyon"]) == "golge"
    assert W.okuma_modu(ayarlar.oku(tmp_path / "yok")["llm_once_revizyon"]) == "kapali"


# ───────────────────────── r3 · P6 (M6): kayıtlardan ölçüm raporu (yalnız okur; numara yazmaz) ─────────────────────────
def test_olcum_raporu_kayitlardan(depo, wa, hizli_genel, uretici):
    import sys as _s
    _s.path.insert(0, str(KOK / "araclar"))
    import plan_olcum as PO
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{st['adaylar'][0]['kod']}"))
    isle_hepsi(depo, URETIM)
    with depo.baglan() as c:
        o = PO.topla(c)
    assert o["uretim"] == 1 and o["durum"] == {"gecerli": 1} and o["secilen"] == 1 and o["cagri"] == 0
    assert o["yeni_plan_isi"] == 1 and o["revizyon_ortalama"] == 0 and o["sure_ms_medyan"] is not None
    metin = PO.rapor(o, 7)
    # inceleme C6: r02 ayrı iş sayılmaz (her revizyon yeni İş Emri numarası alır; iş = proje)
    with depo.baglan() as c:
        r1 = c.execute("SELECT * FROM revizyonlar ORDER BY id DESC LIMIT 1").fetchone()
        c.execute("INSERT INTO revizyonlar (proje_id, rev, is_emri_no, gonderen, bayi_kod, kaynak_mesaj_id, is_emri, dogrulandi, durum) "
                  "VALUES (%s, 2, %s, %s, %s, %s, %s, true, 'onay_bekliyor')",
                  (r1["proje_id"], r1["is_emri_no"] + "-r2", r1["gonderen"], r1["bayi_kod"], r1["kaynak_mesaj_id"], Jsonb(r1["is_emri"])))
        o2 = PO.topla(c)
    assert o2["yeni_plan_isi"] == 1 and o2["revizyon_ortalama"] == 1
    assert "Yeni plan üretimi | 1 (gecerli 1)" in metin and NUMARA_A not in metin and "Hedef yok" in metin


# ───────────────────────── Lokman 15.10 · kapanış soruları ─────────────────────────
def test_soru1_muhendis_mesajinda_yeni_plan_dogrulama_satiri(depo, wa, hizli_genel, uretici):
    # soru 1: yalnız yeni üretilen planda mühendisin dosya mesajına tek satır doğrulama özeti (mühendis kabulü satırda yok)
    import kalici
    from test_muhendis import muhendis_isle, muhendis_karti, muhendis_mesaji, satirlar
    muhendis_karti(depo)
    _secilmis_yeni_plan(depo)
    kalici.gonder(depo, wa)
    rev = tek(depo, "SELECT * FROM revizyonlar ORDER BY id DESC LIMIT 1")
    assert rev["is_emri"]["yapi"]["kod"].startswith("YENI-")
    time.sleep(1.1)
    assert depo.mesaj_kaydet(buton(f"o:{rev['is_emri_no']}:1"))
    [r] = isle_hepsi(depo, URETIM)
    assert r["gerekce"] == "plan onaylandı", r
    g = muhendis_mesaji(reply_id=f"muh:gonder:{rev['is_emri_no']}:1")
    muhendis_isle(depo, g)
    govdeler = [x.get("body") or "" for x in satirlar(depo, g["id"])]
    satir = [b for b in govdeler if "doğrulaması:" in b]
    assert len(satir) == 1 and "Yeni plan (otomatik üretildi) doğrulaması: Sözleşme: geçti" in satir[0]
    assert "Yapısal: yapılmadı" in satir[0] and "Mühendis kabulü" not in satir[0]


def test_soru1_banka_modelinde_dogrulama_satiri_yok():
    import muhendis as MH
    assert MH.dogrulama_satiri({"is_emri": {"yapi": {"kod": "Ç8801K", "tanim": "modeller/C8801K.json"}}}) is None
    assert MH.dogrulama_satiri({}) is None


def test_soru1_satir_onaylanan_revizyonun_taniminden():
    # r02+'da r01'in raporu bayatlar: satır revizyonun gömülü tanımından hesaplanır; çizim klasörü yoksa "doğrulanmadı"
    import muhendis as MH
    from beyin import plan_uretici as PU
    s = PU.uret({"alan_m2": 95, "oda_programi": "3+1"}, ayar={"acik": False})
    d = MH.dogrulama_satiri({"is_emri": {"yapi": {"kod": "YENI-ABC123", "tanim": s["tanim"]}}, "pdf_yolu": None})
    assert d.startswith("Yeni plan (otomatik üretildi) doğrulaması: Sözleşme: geçti · Geometri: geçti")
    assert "Çizim çıktıları: doğrulanmadı" in d and "Yükleme listesi: doğrulanmadı" in d
    assert MH.dogrulama_satiri({"is_emri": {"yapi": {"kod": "YENI-BOZUK", "tanim": {"bozuk": True}}}}).endswith("hesaplanamadı.")


@pytest.mark.parametrize("istek", ["L çatı olsun", "cumbalı çatı olsun"])
def test_soru3_l_ve_cumba_cati_uygulayamadim_ve_besik_kirma(depo, wa, hizli_genel, uretici, istek):
    # soru 3 (Lokman 15.10): L ve cumba derleyiciye bağlanmaz; istenirse "otomatik uygulayamadım", plan beşik ya da kırma
    kabul(depo, YEDI)
    tl = talep(ozet=f"95 m² 3+1 tek kat çelik, {istek}", alan_m2=95, oda_programi="3+1", yapi_turu="celik", kat_sayisi=1, ozel_istekler=[istek])
    assert depo.mesaj_kaydet(mesaj(f"95 m² 3+1 tek kat çelik, {istek}", tl, bayi=BAYI_KART))
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "secenek", r
    body = sorgu(depo, "SELECT satir FROM giden ORDER BY olusturuldu, sira")[1]["satir"]["body"]
    assert f'"{istek}" isteğini otomatik uygulayamadım' in body
    d, _ = depo.konusma_oku(NUMARA_A)
    assert all((u["tanim"]["cati"]["tip"] in ("besik", "kirma")) for u in d["uretilen_planlar"])
