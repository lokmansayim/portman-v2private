"""BK-29 tur 5 (pano 216) · 13 Kasım 2026 canlı denetimi tur 3 (v2026.11.13d), gözlem 1.

Onay bekleyen planda "iptal" ilk yazışta iptal sayılmıyordu: LLM "red" niyeti veriyor, kural onu "Anladım. Neyi değiştirelim?" sorusuna
çeviriyordu (revizyon formu); talep ikinci "iptal"le kapanıyordu. Bayinin açık iptal sözü (K18) talebi ilk yazışta kapatır.
"beğenmedim", "olmadı", "hayır" ve olumsuz biçim ("iptal etmeyin") bugünkü gibi revizyon sorusu alır.
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür (LLM'in canlıda verdiği biçimde).
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from test_celik_revizyon_karar import Sohbet  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402

KAPANDI = "Talep kapatıldı. Yeni bir plan istediğinizde yazmanız yeterli."


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


@pytest.mark.parametrize("soz", ["iptal", "İptal", "iptal edin", "Talebi iptal edin lütfen", "iptal ediyoruz", "vazgeçtik"])
def test_onay_bekleyen_planda_iptal_ilk_yazista_kapatir(s, soz):
    _plan(s, "PA04")
    k = s.yaz(soz, niyet="red", ozet="Bayi talebi iptal etmek istiyor.")
    assert (k.eylem, k.gerekce, k.mesaj) == ("cevapla", "iptal", KAPANDI)
    assert not s.k.d.get("taslak") and not s.k.d.get("son_is_emri")


def test_iptalden_sonra_yalniz_kod_yeni_plan(s):
    """Denetim A7: "iptal" → "Talep kapatıldı." → "PA-04" → PA-04 planı r01 (tur 3'te iki "iptal" gerekiyordu)."""
    _plan(s, "PA04")
    assert s.yaz("iptal", niyet="red").mesaj == KAPANDI
    k = s.yaz("PA-04", niyet="diger", ozet='"PA-04" yazdınız, ne istediğinizi anlayamadık.')
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1, k.mesaj
    assert k.mesaj.startswith("PA-04 seçildi. ")


@pytest.mark.parametrize("soz", ["beğenmedim", "olmadı", "hayır", "iptal etmeyin", "iptal mi?"])
def test_ret_sozu_revizyon_sorusu_alir(s, soz):
    """Açık iptal sözü olmayan ret bugünkü gibi: plan açık kalır, "Neyi değiştirelim?" sorulur."""
    _plan(s, "PA04")
    k = s.yaz(soz, niyet="red")
    assert (k.eylem, k.soru_alani) == ("sor", "revizyon_ne"), k.mesaj
    assert k.mesaj.startswith("Anladım. Neyi değiştirelim?")
    assert s.plan["revizyon"] == 1


def test_revizyon_sorusundan_sonra_iptal_bugunku_gibi(s):
    """"Neyi değiştirelim?" açıkken "iptal" talebi kapatır (tur 3'teki ikinci "iptal"; değişmedi)."""
    _plan(s, "PA04")
    s.yaz("beğenmedim", niyet="red")
    assert s.yaz("iptal", niyet="red").mesaj == KAPANDI


@pytest.mark.parametrize("soz,beklenen", [
    ("iptal", True), ("iptal et", True), ("iptal edelim", True), ("iptal olsun", True), ("iptal edilsin", True),
    ("bu talebi iptal ediyorum", True), ("vazgeçtim", True), ("iptal lütfen", True),
    ("iptal etmeyin", False), ("iptal etme", False), ("iptal edilmesin", False), ("vazgeçmedim", False), ("iptal etmedik", False),
    ("iptal mi", False), ("pencereyi iptal et", False), ("beğenmedim", False), ("hayır", False), ("", False),
])
def test_iptal_sozu(soz, beklenen):
    assert K._iptal_sozu(soz) is beklenen
