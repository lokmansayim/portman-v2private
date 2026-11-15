"""BK-29 tur 9 · canlı bulgu (v2026.11.15b, 15 Kasım 2026, adım 5): kod ile müşteri adı aynı mesajda yazılınca plan gelmiyordu.

"PA-04, müşteri Ayşe Kaya" → "Anlayamadım. …" (LLM niyeti "diğer" okudu); "PA-04 olsun, müşteri Ayşe Kaya" → "Onaylanacak açık bir
plan görünmüyor. …" (LLM niyeti "onay" okudu). Önce kod, sonra "müşteri adı Ayşe Kaya" yazınca çalışıyordu. Kural bayinin kendi
mesajını okur (K18): mesaj yalnız bir model kodu, seçim sözcükleri ve "müşteri <ad>" parçasıysa o modelin seçimidir, ad müşteri adıdır.
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür; adlar uydurmadır.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from test_bk29_tur7 import Sohbet, BAYI  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402

AD = {"ad": "Ayşe Kaya"}
HAZIR = "PA-04 seçildi. Ön onay planınız hazır; plan görseli ve PDF ektedir."


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path)


def _plan(k, ad="Ayşe Kaya"):
    assert k.eylem == "is_emri" and k.revizyon == 1, k.mesaj
    assert k.is_emri["talep"]["musteri_adi"] == ad
    return k


# ── canlıdaki iki cümle, LLM'in olası okumalarıyla ──────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("alan", [
    dict(niyet="diger"),                                              # canlı: "Anlayamadım"
    dict(niyet="diger", musteri=AD),
    dict(niyet="diger", katalog_kodu="PA04", musteri=AD),
    dict(niyet="yeni_talep", musteri=AD),                             # kod okunmadı
    dict(niyet="yeni_talep", katalog_kodu="PA04"),                    # ad okunmadı
    dict(niyet="soru"),
])
def test_kod_ve_musteri_adi_tek_mesajda_plan_gelir(s, alan):
    k = _plan(s.yaz("PA-04, müşteri Ayşe Kaya", **alan))
    assert k.mesaj.startswith(HAZIR)


@pytest.mark.parametrize("alan", [
    dict(niyet="onay"),                                               # canlı: "Onaylanacak açık bir plan görünmüyor"
    dict(niyet="onay", katalog_kodu="PA04", musteri=AD),
])
def test_olsun_onay_okunsa_da_secimdir(s, alan):
    k = _plan(s.yaz("PA-04 olsun, müşteri Ayşe Kaya", **alan))
    assert k.mesaj.startswith(HAZIR)


@pytest.mark.parametrize("metin, llm_adi, beklenen", [
    ("PA-04 müşteri adı Ayşe Kaya", None, "Ayşe Kaya"),
    ("PA-04, müşterimiz: Ayşe Kaya", None, "Ayşe Kaya"),
    ("Müşteri Ayşe Kaya, PA-04 olsun", None, "Ayşe Kaya"),
    ("PA-04 lütfen, müşteri Ali Rıza Öztürk", None, "Ali Rıza Öztürk"),
    ("PA-04, müşteri Fatma Güzel", None, "Fatma Güzel"),             # "güzel" seçim sözcüğüdür; büyük harfle soyadıdır
    ("pa-04 müşteri adı ayşe kaya", "Ayşe Kaya", "ayşe kaya"),        # küçük harf: LLM'in okuduğu adla aynıysa ad
])
def test_musteri_sozunun_bicimleri(s, metin, llm_adi, beklenen):
    _plan(s.yaz(metin, niyet="diger", **({"musteri": {"ad": llm_adi}} if llm_adi else {})), beklenen)


def test_llm_dogru_okuduysa_bugunku_yol(s):
    k = _plan(s.yaz("PA-04, müşteri Ayşe Kaya", niyet="yeni_talep", katalog_kodu="PA04", musteri=AD))
    assert not any("müşteri adı" in g["metin"] for g in s.k.d["gecmis"] if g["yon"] == "kural")


def test_celik_kodla_da_ayni(s):
    k = s.yaz("Ç8801K, müşteri Ayşe Kaya", niyet="diger")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["musteri_adi"] == "Ayşe Kaya" and k.is_emri["bilgi"]["musteri_adi"] == "Ayşe Kaya"


def test_bayi_kendi_adini_musteri_diye_yazarsa_kalir(s):
    """Tur 7 ile birlikte: ad bayinin kartındaki adla aynı ama bu mesajda yazıyor; müşteri adıdır."""
    _plan(s.yaz("PA-04, müşteri Deniz Örnek", niyet="diger"), "Deniz Örnek")


def test_acik_sette_kod_ve_musteri_adi_secimdir(s):
    k = s.yaz("Tek kat prefabrik, 2+1, 85 m²", yapi_turu="prefabrik", kat_sayisi=1, oda_programi="2+1", alan_m2=85)
    k = s.yaz("bütçe", niyet="yeni_talep", oncelik="butce")
    assert k.eylem == "secenek" and "PA04" in [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]], k.mesaj
    _plan(s.yaz("PA-04 olsun, müşteri Ayşe Kaya", niyet="onay"))


# ── kurala girmeyen mesajlar bugünkü gibi ───────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin", [
    "PA-04, müşteri salonu büyük istiyor",                            # ad değil, istek
    "PA-04, müşteri Ayşe Kaya, mutfak penceresi 120x120 olsun",       # başka istek de var: LLM'in okumasıyla gider
    "PA-04 müşteri onayladı",
    "PA-04 mü PA-05 mi, müşteri Ayşe Kaya",                           # iki kod
    "müşteri Ayşe Kaya",                                              # kod yok
    "PA-04 olmasın, müşteri Ayşe Kaya",                               # olumsuz söz
    "PA-04, müşteri adı ayşe kaya",                                   # küçük harf ve LLM adı okumadı
])
def test_baska_soz_tasiyan_mesaj_kurala_girmez(s, metin):
    assert K._kod_ve_musteri(metin, s.kat) == (None, None)
    k = s.yaz(metin, niyet="diger")
    assert k.eylem == "cevapla" and k.mesaj.startswith("Anlayamadım.")


def test_llm_baska_kod_okuduysa_karismaz(s):
    k = s.yaz("PA-04, müşteri Ayşe Kaya", niyet="onay", katalog_kodu="PA05", musteri=AD)
    assert k.eylem == "cevapla" and k.mesaj.startswith("Onaylanacak açık bir plan görünmüyor.")


def test_acik_planin_ustune_yazilan_mesaj_bugunku_yol(s):
    """Açık plan varken kural çalışmaz; "müşteri adı …" bugün olduğu gibi revizyon yolundan gider."""
    no = _plan(s.yaz("PA-04", katalog_kodu="PA04"), "").is_emri["is_emri_no"]
    k = s.yaz("PA-04, müşteri Ayşe Kaya", niyet="diger")
    assert k.eylem == "cevapla" and k.mesaj.startswith("Anlayamadım.")
    son = s.k.d["son_is_emri"]
    assert s.k.d["asama"] == "onay_bekliyor" and (son["is_emri_no"], son["revizyon"]) == (no, 1)
    k = s.yaz("müşteri adı Ayşe Kaya", niyet="revizyon", musteri=AD)          # canlıda çalışan iki adımlı yol aynen
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["musteri_adi"] == "Ayşe Kaya"


def test_kod_ve_musteri_okumasi():
    kat = Katalog(kabul_edilmis=KABUL)
    assert K._kod_ve_musteri("PA-04, müşteri Ayşe Kaya", kat) == ("PA04", "Ayşe Kaya")
    assert K._kod_ve_musteri("PA-04 olsun, müşteri Ayşe Kaya", kat) == ("PA04", "Ayşe Kaya")
    assert K._kod_ve_musteri("PA-04, müşteri Ayşe Kaya olsun", kat) == ("PA04", "Ayşe Kaya")
    assert K._kod_ve_musteri("PA-04", kat) == (None, None)             # müşteri sözü yok: `_yalniz_kod`'un işi
    assert K._kod_ve_musteri(None, kat) == (None, None)
    assert BAYI["ad"] == "Deniz Örnek"
