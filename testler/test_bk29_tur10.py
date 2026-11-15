"""BK-29 tur 10 · D-101 (Lokman, kart 15 Kasım 2026 07:26:12 UTC, "Sabit kalsın"): prefabrik planda revizyon talebin numarasını taşır.

Kabul seti D5 (pano 207): canlıda her revizyon yeni numara alıyordu (…4303 r03 → …4342 r04); bayi aynı evin iki planını iki ayrı
iş sanıyordu. Numara artık ilk planda kurulur, revizyonu rNN ayırır (…8813 r01, …8813 r02). Yeni numara: konuşma sıfırlandıysa (iptal,
yeni talep) ve kanalın sıradaki revizyon klasörünü dolu bulduğu işte (`k.yeni_numara`). Çelikte bugünkü yol (kartın kapsamı prefabrik).
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür; saat testte ileri alınır (numara saatten kurulur).
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen, r01_k  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


@pytest.fixture
def saat(monkeypatch):
    """Saati ileri alır: `saat(1000)` sonraki numaranın saatten kurulan parçasını değiştirir (aynı saniyeye güvenilmez)."""
    kayma = [0.0]
    gercek = time.time
    monkeypatch.setattr(K.time, "time", lambda: gercek() + kayma[0])

    def ileri(sn: float):
        kayma[0] += sn
    return ileri


def _pencere(s: Sohbet, olcu: str):
    k = s.yaz(f"yatak odası 1 penceresi {olcu} olsun", pencereler=[pen("yatak odası 1", olcu)])
    assert k.eylem == "is_emri", k.mesaj
    return k


def test_revizyon_talebin_numarasini_tasir(s, saat):
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    assert no.startswith("PM-")
    saat(1000)
    k2 = _pencere(s, "120x180")
    assert (k2.is_emri["is_emri_no"], k2.is_emri["revizyon"]) == (no, 2)
    saat(1000)
    k3 = _pencere(s, "120x160")
    assert (k3.is_emri["is_emri_no"], k3.is_emri["revizyon"]) == (no, 3)
    assert k3.is_emri["kunye"]["proje_kodu"] == no                       # PDF antedindeki proje kodu da aynı numara


def test_onay_ve_revizyon_ayni_numarada_rev_ile_ayrilir(s, saat):
    """Onaylı r01'in üstüne gelen revizyon aynı numarayla r02 olur; onay (numara, revizyon) çiftiyle tutulur, r01 onayı r02'ye geçmez."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    s.dugme(f"o:{no}:1")
    assert s.k.d["onaylanan"] == [no, 1]
    saat(1000)
    k = _pencere(s, "120x180")
    assert (k.is_emri["is_emri_no"], k.revizyon) == (no, 2)
    assert "r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir." in k.mesaj
    assert "onaylanan" not in s.k.d and s.k.d["asama"] == "onay_bekliyor"


def test_iptalden_sonraki_plan_yeni_numara_alir(s, saat):
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    k = s.yaz("iptal", niyet="red")
    assert (k.eylem, k.gerekce) == ("cevapla", "iptal") and not s.k.d.get("son_is_emri")
    saat(1000)
    k = s.yaz("PA-04", katalog_kodu="PA04", niyet="yeni_talep")
    assert k.eylem == "is_emri" and k.is_emri["revizyon"] == 1 and k.is_emri["is_emri_no"] != no


def test_klasor_doluysa_yeni_numara(s, saat):
    """Kanal sıradaki revizyon klasörünü dolu bulduysa (`worker.isle` → `k.yeni_numara`) revizyon yeni numara alır; revizyon sayısı sürer."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    s.k.yeni_numara = True
    k = _pencere(s, "120x180")                                             # saat ilerlemedi: aynı saniyede de numara eskisiyle aynı çıkmaz
    assert k.is_emri["revizyon"] == 2 and k.is_emri["is_emri_no"] != no and k.is_emri["is_emri_no"].startswith("PM-")
    s.k.yeni_numara = False
    yeni = k.is_emri["is_emri_no"]
    saat(1000)
    k = _pencere(s, "120x160")
    assert (k.is_emri["is_emri_no"], k.is_emri["revizyon"]) == (yeni, 3)   # sonraki revizyon son planın numarasını taşır


def test_degismeyen_plan_numarayi_ve_revizyonu_tuketmez(s, saat):
    """D-86: aynı değişiklik yeniden istenince plan yeniden çizilmez; numara ve revizyon aynı kalır."""
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    saat(1000)
    _pencere(s, "120x180")
    saat(1000)
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "cevapla" and f"Planınız ({no} r02) değişmedi" in k.mesaj
    assert (s.plan["is_emri_no"], s.plan["revizyon"]) == (no, 2)


def test_celikte_bugunku_yol(tmp_path, saat):
    """Kartın kapsamı prefabrik: çelik revizyonun numarası bugünkü gibi her planda yeniden kurulur (çelik sorusu Lokman'da, D-101 › Açık)."""
    c = Sohbet(tmp_path)
    r01_k(c)
    no = c.plan["is_emri_no"]
    saat(1000)
    k = c.yaz("salondaki sol taraftaki pencere 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="sol")])
    if k.eylem == "sor":
        k = c.dugme("q:okuma:2")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["is_emri_no"] != no


def test_celik_planin_numarasi_prefabrik_plana_gecmez(tmp_path, saat):
    """Çelik plandan sonra aynı konuşmada prefabrik ev seçilirse prefabrik plan çelik planın numarasını almaz."""
    c = Sohbet(tmp_path, kabul=KABUL)
    r01_k(c)
    no = c.plan["is_emri_no"]
    saat(1000)
    k = c.yaz("PA-04", katalog_kodu="PA04", niyet="yeni_talep")
    assert k.eylem == "is_emri" and (k.is_emri.get("yapi") or {}).get("sistem") != "celik", k.mesaj
    assert k.is_emri["is_emri_no"] != no
