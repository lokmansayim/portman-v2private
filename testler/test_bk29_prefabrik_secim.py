"""BK-29 PR-3 (pano 208) · prefabrik seçenek setinde yazılı kod ve numara; boş sohbette yalnız model kodu.

13 Kasım 2026 WhatsApp denetimi (canlı v2026.11.13; kabul seti A5–A7): açık prefabrik sette "PA-04 olsun" ve "3" aynı listeyi yeniden
getiriyordu; boş sohbette "PA-04" "Anlayamadım" alıyordu. Canlı LLM bu kısa mesajlarda model kodunu vermiyordu; kural bayinin kendi sözünü
okur (K18). LLM yok, Postgres yok, çizim yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür (kod alanı boş: canlıdaki gibi).
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_celik_revizyon_karar import Sohbet  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


def _set(s: Sohbet) -> list[str]:
    """Tek kat prefabrik, 2+1, 85 m² → öncelik → bütçe: set PA-06, PA-04, PA-05 (canlının kabul kümesiyle)."""
    s.yaz("Tek kat prefabrik, 2+1, 85 m²", yapi_turu="prefabrik", kat_sayisi=1, oda_programi="2+1", alan_m2=85)
    k = s.dugme("q:oncelik:butce")
    assert k.eylem == "secenek"
    return [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]]


@pytest.mark.parametrize("niyet", ["yeni_talep", "diger"])
@pytest.mark.parametrize("metin", ["PA-04 olsun", "PA04", "pa 04 olsun lütfen"])
def test_a5_sette_yazili_kod(s, metin, niyet):
    """A5: LLM kodu vermese de bayinin yazdığı kod seçimdir; set "seçildi" kapanır."""
    assert _set(s) == ["PA06", "PA04", "PA05"]
    k = s.yaz(metin, niyet=niyet)
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == "PA04", k.mesaj
    assert s.k.d["secenek_seti"]["durum"] == "secildi" and s.k.d["secenek_seti"]["secilen_kod"] == "PA04"


@pytest.mark.parametrize("niyet", ["yeni_talep", "diger"])
@pytest.mark.parametrize("metin, kod", [("3", "PA05"), ("üçüncü", "PA05"), ("2 olsun", "PA04")])
def test_a6_prefabrik_sette_yazili_numara(s, metin, kod, niyet):
    """A6: "3" düğmeyle aynıdır (prefabrikte de); LLM'in bu kısa cevaba verdiği niyet yok sayılır."""
    _set(s)
    k = s.yaz(metin, niyet=niyet)
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == kod, k.mesaj


def test_a6_cati_seti_acan_evde_numara(s):
    """Setin 1. evi (PA-06) çatı seçenekli: "1" önce çatı setini getirir (düğmeyle seçimdeki gibi), sonra "1" evin çatısıyla plan."""
    _set(s)
    k = s.yaz("1", niyet="diger")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti"
    k = s.yaz("1", niyet="diger")
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == "PA06"


@pytest.mark.parametrize("metin", ["2+1 olsun", "PA-04 olmasın", "PA-04 ile PA-05 farkı ne?", "5"])
def test_sette_secim_olmayan_mesaj(s, metin):
    """Oda programı, olumsuz söz, iki kod ve setin dışındaki numara seçim değildir: plan çıkmaz."""
    _set(s)
    k = s.yaz(metin, niyet="yeni_talep")
    assert k.eylem != "is_emri", k.mesaj


@pytest.mark.parametrize("niyet", ["diger", "yeni_talep"])
def test_a7_bos_sohbette_yalniz_kod(s, niyet):
    """A7: boş sohbette "PA-04" planı getirir; "PA-06" önce çatı setini (evin çatısı, kırma, mahya önde)."""
    k = s.yaz("PA-04", niyet=niyet)
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == "PA04", k.mesaj
    s2 = Sohbet(s.k.path.parent / "b", kabul=KABUL)
    k = s2.yaz("PA-06", niyet=niyet)
    assert k.eylem == "secenek" and s2.k.d["secenek_seti"]["tur"] == "cati_varyanti"


def test_acik_planin_ustune_yazilan_kod_bugunku_yoldan(s):
    """Açık plan (PA-04 r01) varken LLM'siz "PA-05" yeni model seçimi sayılmaz (bugünkü yol; model değişikliği LLM okumasıyla)."""
    s.yaz("PA-04", niyet="diger")
    assert s.plan["revizyon"] == 1
    k = s.yaz("PA-05", niyet="diger")
    assert k.eylem == "cevapla" and k.gerekce == "anlaşılmadı"
    assert s.plan["talep"]["kaynak"] == "PA04"


def test_bilinmeyen_kod_secilmez(s):
    """Kayıtta olmayan kod ("PA-99") kod sayılmaz: bugünkü "Anlayamadım"."""
    k = s.yaz("PA-99", niyet="diger")
    assert k.eylem == "cevapla" and k.gerekce == "anlaşılmadı"
