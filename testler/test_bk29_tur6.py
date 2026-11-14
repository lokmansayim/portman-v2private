"""BK-29 tur 6 (pano 206, 212, 213) · 13 Kasım 2026 WhatsApp kabul setinin kalan satırları: A12, C7, C8, D3.

A12: iki katlı prefabrik talebinde bot dış ölçü soruyordu; plan çizilmiyor, ilk cevapta söylenir ve talep PortatifEv'e iletilir.
C7: onaydan sonra "Teklif ne zaman gelir?" genel fiyat cevabı alıyordu; cevap bayinin planını bilir.
C8: onaylı planın üstüne revizyon gelince r02 gidiyor, onaydan söz edilmiyordu; r01 onayının düştüğü ve r02'nin onay istediği yazılır.
D3: yazıyla "Nasıl çalışır?" fiyat cevabı alıyordu; düğmeyle aynı yoldan gider (kanal/worker.py, LLM'siz).
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kanal"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402

IKI_KAT = "İki katlı ev planını henüz çizemiyorum. Talebinizi PortatifEv'e iletiyorum; size dönüş yapılacak."


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


# ── A12 (pano 213): iki katlı prefabrik ──────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("alan", [
    dict(yapi_turu="prefabrik", kat_sayisi=2, oda_programi="4+1", alan_m2=150),
    dict(yapi_turu="prefabrik", kat_sayisi=2),
    dict(yapi_turu="prefabrik", kat_sayisi=2, oda_programi="3+1", dis_olcu={"en_m": 7.0, "boy_m": 9.0}),
])
def test_iki_katli_prefabrik_ilk_cevapta_iletilir(s, alan):
    k = s.yaz("İki katlı prefabrik, 4+1, 150 m²", **alan)
    assert (k.eylem, k.mesaj) == ("yonlendir", IKI_KAT)
    assert s.k.d["asama"] == "yonlendirildi" and not s.k.d["taslak"]


def test_iki_kat_dis_olcuyle_tek_katli_sablona_dusmez(s):
    """7x10 pano ve 2+1 için tek katlı ızgara şablonu var; iki kat denince o plan çizilmez."""
    k = s.yaz("iki katlı prefabrik 2+1, 7x10 pano", yapi_turu="prefabrik", kat_sayisi=2, oda_programi="2+1", pano={"nx": 6, "ny": 8})
    assert k.eylem == "yonlendir" and k.is_emri is None


def test_tek_kat_ve_celik_bugunku_gibi(s):
    k = s.yaz("Tek kat prefabrik, 2+1, 85 m²", yapi_turu="prefabrik", kat_sayisi=1, oda_programi="2+1", alan_m2=85)
    assert (k.eylem, k.soru_alani) == ("sor", "oncelik")
    c = Sohbet(s.k.kok / "celik", kabul=KABUL) if hasattr(s.k, "kok") else s
    k = c.yaz("İki katlı çelik, 4+1, 150 m²", yapi_turu="celik", kat_sayisi=2, oda_programi="4+1", alan_m2=150)
    assert k.eylem == "sor" and "çelik çift kat" in k.mesaj               # çelikte katalog önerisi bugünkü gibi


def test_yapi_tipi_yazilmamis_iki_kat_bugunku_gibi(s):
    k = s.yaz("iki katlı ev", kat_sayisi=2)
    assert (k.eylem, k.soru_alani) == ("sor", "oda_programi")


# ── C7 (pano 212): plan durumu soruya cevapta ───────────────────────────────────────────────────────────────────────────────

def test_onaydan_sonra_teklif_sorusu_plani_bilir(s):
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    k = s.yaz("Teklif ne zaman gelir?", niyet="soru")
    assert k.mesaj.startswith(f"Planınız ({no} r01) onayınızı bekliyor. Teklifi PortatifEv, planı onayladıktan sonra hazırlar.")
    assert s.k.d["asama"] == "onay_bekliyor"
    assert s.dugme(f"o:{no}:1").gerekce == "plan onaylandı"
    k = s.yaz("Teklif ne zaman gelir?", niyet="soru")
    assert (k.eylem, k.gerekce) == ("cevapla", "genel soru: plan durumu")
    assert k.mesaj.startswith(f"Onayladığınız plan ({no} r01) için teklifi PortatifEv hazırlıyor.")
    assert s.k.d["asama"] == "onaylandi" and s.k.d["onaylanan"] == [no, 1]


def test_celik_onayindan_sonra_teknik_kontrol(s):
    k = s.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik")
    assert k.eylem == "is_emri"
    no = s.plan["is_emri_no"]
    s.dugme(f"o:{no}:1")
    k = s.yaz("Fiyat ne kadar?", niyet="soru")
    assert k.mesaj.startswith(f"Onayladığınız plan ({no} r01) teknik kontrolde.")


def test_plansiz_soru_bugunku_gibi(s):
    k = s.yaz("Bu evin fiyatı ne kadar?", niyet="soru")
    assert (k.eylem, k.gerekce) == ("cevapla", "genel soru")
    assert k.mesaj.startswith("Fiyat, süre ve teslim bilgisi ön onaylı planın ardından teklifle gelir.")


# ── C8 (pano 212): onaylı planın üstüne revizyon ────────────────────────────────────────────────────────────────────────────

DUSTU = "Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir."


def test_onayli_planda_revizyon_onayi_dusurur_ve_soyler(s):
    _plan(s, "PA04")
    s.dugme(f"o:{s.plan['is_emri_no']}:1")
    k = s.yaz("Onayladığım planda yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 2
    assert k.mesaj.endswith(DUSTU), k.mesaj
    assert s.k.d["asama"] == "onay_bekliyor" and "onaylanan" not in s.k.d
    k = s.yaz("yatak odası 1 penceresi 120x120 olsun", pencereler=[pen("yatak odası 1", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 3 and "onayınızı geçersiz" not in k.mesaj      # yalnız onayı düşüren revizyonda


def test_onaysiz_revizyonda_onay_cumlesi_yok(s):
    _plan(s, "PA04")
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and "onayınızı geçersiz" not in k.mesaj


def test_onayli_planda_geri_cevrilen_istek_onayi_korur(s):
    """BK-29 PR-1: geri çevrilen istek onayı düşürmez (plan aynı); C8 cümlesi gitmez."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    s.dugme(f"o:{no}:1")
    k = s.yaz("veranda arkada olsun", varyantlar=[{"tur": "veranda_degistir", "aciklama": "veranda arkada", "parametreler": {}}])
    assert k.eylem != "is_emri" and "onayınızı geçersiz" not in k.mesaj
    assert s.k.d["asama"] == "onaylandi" and s.k.d["onaylanan"] == [no, 1]


def test_onayli_planda_ayni_istek_onayi_korur(s):
    """D-86: plan değişmezse onay da düşmez."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    olcu = next(a["olcu"] for a in s.plan["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == "YATAK ODASI 1")
    s.dugme(f"o:{no}:1")
    k = s.yaz(f"yatak odası 1 penceresi {olcu} olsun", pencereler=[pen("yatak odası 1", olcu)])
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI)
    assert k.mesaj.startswith(f"Onaylı planınız ({no} r01) değişmedi")
    assert s.k.d["asama"] == "onaylandi" and s.k.d["onaylanan"] == [no, 1]


# ── tur 5 canlı madde 10: açık planda "iptal etmeyin" ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("niyet", ["diger", "soru", "red"])
@pytest.mark.parametrize("soz", ["iptal etmeyin", "İptal etmeyin lütfen", "iptal etme", "iptal edilmesin", "vazgeçmedim"])
def test_acik_planda_iptal_etmeyin_talebi_kapatmaz_degisikligi_sorar(s, soz, niyet):
    """Canlıda (v2026.11.13f) LLM "iptal etmeyin"i "diğer" okudu; "Anlayamadım" ve yeni talep önerisi gitti. Cevap niyetten bağımsız."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    k = s.yaz(soz, niyet=niyet)
    assert (k.eylem, k.soru_alani) == ("sor", "revizyon_ne"), k.mesaj
    assert k.mesaj.startswith("Anladım. Neyi değiştirelim?") and "Anlayamadım" not in k.mesaj
    assert s.plan["is_emri_no"] == no and s.plan["revizyon"] == 1 and s.k.d["asama"] == "revizyon"


def test_revizyon_sorusu_acikken_iptal_etmeyin_talebi_kapatmaz(s):
    """"Neyi değiştirelim?" açıkken ikinci "iptal etmeyin" (niyet "red") talebi kapatıyordu; olumsuz söz iptal değildir."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    assert s.yaz("iptal etmeyin", niyet="diger").soru_alani == "revizyon_ne"
    k = s.yaz("iptal etmeyin", niyet="red")
    assert (k.eylem, k.soru_alani) == ("sor", "revizyon_ne") and s.plan["is_emri_no"] == no
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 2                       # plan yaşıyor: değişiklik r02 olur
    assert s.plan["is_emri_no"] == no


def test_revizyon_sorusu_acikken_iptal_yine_kapatir(s):
    _plan(s, "PA04")
    s.yaz("iptal etmeyin", niyet="diger")
    k = s.yaz("iptal", niyet="red")
    assert (k.eylem, k.gerekce) == ("cevapla", "iptal") and not s.k.d.get("son_is_emri")


def test_plansiz_iptal_etmeyin_bugunku_gibi(s):
    k = s.yaz("iptal etmeyin", niyet="diger")
    assert k.eylem == "cevapla" and k.mesaj.startswith("Anlayamadım.")


def test_acik_planda_iptal_sozu_olmayan_diger_bugunku_gibi(s):
    """Yalnız iptal sözünün olumsuzu yakalanır; başka "diğer" mesajı bugünkü cevabı alır."""
    _plan(s, "PA04")
    k = s.yaz("etmeyin", niyet="diger")
    assert k.mesaj.startswith("Anlayamadım.")
    k = s.yaz("iptal etmeyin ama pencereyi büyütün", niyet="diger")
    assert k.mesaj.startswith("Anlayamadım.")


# ── D3 (pano 206): yazıyla "Nasıl çalışır?" ─────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("soz,beklenen", [
    ("Nasıl çalışır?", True), ("nasil calisir", True), ("NASIL ÇALIŞIR", True), ("Portman nasıl çalışıyor?", True),
    ("Bu sistem nasıl çalışır", True), ("Nasıl kullanılır?", True),
    ("bu pencere nasıl çalışır", False), ("nasıl çalışır, fiyat ne", False), ("Nasıl?", False), ("", False), (None, False),
    ("P6001 nasıl çalışır", False),
])
def test_nasil_calisir_sozu(soz, beklenen):
    import worker as W
    assert W.nasil_calisir_sozu(soz) is beklenen


@pytest.mark.parametrize("gelen,beklenen", [
    ({"type": "text", "text": "Nasıl çalışır?", "bayi": {"kod": "TST"}}, True),
    ({"type": "text", "text": "Nasıl çalışır?", "bayi": {"kod": "TST"}, "role": "patron"}, True),      # deneme Patron numarasından yapılır
    ({"type": "text", "text": "Nasıl çalışır?", "bayi": None}, False),                                   # kayıtsız gönderen
    ({"type": "text", "text": "Nasıl çalışır?", "bayi": {"kod": "TST"}, "role": "muhendis"}, False),
    ({"type": "button", "text": "Nasıl çalışır?", "bayi": {"kod": "TST"}, "reply_id": "bilgi:nasil"}, False),   # düğme kendi yolundan
    ({"type": "image", "text": "Nasıl çalışır?", "bayi": {"kod": "TST"}}, False),
    ({"type": "text", "text": "fiyat nedir", "bayi": {"kod": "TST"}}, False),
])
def test_nasil_calisir_mesaji(gelen, beklenen):
    import worker as W
    assert W.nasil_calisir_mesaji(gelen) is beklenen
