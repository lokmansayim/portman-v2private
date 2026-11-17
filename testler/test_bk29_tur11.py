"""BK-29 tur 11 · D-101 çelik eki (Lokman, kart 15 Kasım 2026 21:51:26 UTC, "Çelikte de sabit kalsın"): çelik planda da revizyon
talebin numarasını taşır.

Kartın sonuç satırı: "Çelik planda r02 ve r03 de r01'in numarasıyla gelir." Numarayı prefabrikte ve çelikte aynı kural verir
(`karar._talep_numarasi`; çelik zarfı `celik.zarf(is_emri_no=…)`). Yeni numara: konuşma sıfırlandıysa (iptal, yeni talep) ve kanalın
sıradaki revizyon klasörünü dolu bulduğu işte (`k.yeni_numara`). Revizyon sayısı sürüyorsa numara sürer: çelik planın üstüne
prefabrik ev (ya da tersi) revizyon olarak gelirse plan aynı numarayla sıradaki revizyondur (varsayım; D-101).
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür; saat testte ileri alınır (numara saatten kurulur).
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kanal"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
import etkilesim as ET  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen, r01_k, var  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402


@pytest.fixture
def c(tmp_path) -> Sohbet:
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


def _mutfak(c: Sohbet, olcu: str):
    k = c.yaz(f"mutfak penceresi {olcu} olsun", pencereler=[pen("mutfak", olcu)])
    assert k.eylem == "is_emri", k.mesaj
    return k


def test_celik_revizyon_talebin_numarasini_tasir(c, saat):
    r01_k(c)
    no = c.plan["is_emri_no"]
    assert no.startswith("PM-")
    saat(1000)
    k2 = _mutfak(c, "120x120")
    assert (k2.is_emri["is_emri_no"], k2.is_emri["revizyon"]) == (no, 2)
    assert k2.is_emri["yapi"]["sistem"] == "celik" and k2.is_emri["yapi"]["onceki"]["revizyon"] == 1
    saat(1000)
    k3 = _mutfak(c, "120x180")
    assert (k3.is_emri["is_emri_no"], k3.is_emri["revizyon"]) == (no, 3)


def test_celik_cati_degisince_numara_ayni(c, saat):
    """Çatı varyantı değişince zarfın tanım dosyası değişir (Ç8801K → Ç8801L); talep aynı talep, numara aynı numara."""
    r01_k(c)
    no = c.plan["is_emri_no"]
    saat(1000)
    k = c.yaz("çatı L olsun", varyantlar=[var("cati_degistir", "çatı L olsun")])
    assert k.eylem == "is_emri" and k.is_emri["yapi"]["kod"] == "Ç8801L", k.mesaj
    assert (k.is_emri["is_emri_no"], k.is_emri["revizyon"]) == (no, 2)


def test_celik_dugmeler_numara_ve_revizyon_ciftiyle(c, saat):
    """Numara aynı kalınca eski planın düğmesi yeni planı onaylamaz: düğme (numara, revizyon) çiftiyle denetlenir."""
    r01_k(c)
    no = c.plan["is_emri_no"]
    saat(1000)
    _mutfak(c, "120x120")
    assert ET.coz({"reply_id": f"o:{no}:1", "type": "interactive"}, c.k.d).get("gecerli") is False
    assert ET.coz({"reply_id": f"o:{no}:2", "type": "interactive"}, c.k.d).get("gecerli") is True
    assert c.k.d["bekleyen_onay"] == no and c.k.d["asama"] == "onay_bekliyor"


def test_celik_iptalden_sonraki_plan_yeni_numara_alir(c, saat):
    r01_k(c)
    no = c.plan["is_emri_no"]
    k = c.yaz("iptal", niyet="red")
    assert (k.eylem, k.gerekce) == ("cevapla", "iptal") and not c.k.d.get("son_is_emri")
    saat(1000)
    k = c.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik", niyet="yeni_talep")
    assert k.eylem == "is_emri" and k.is_emri["revizyon"] == 1 and k.is_emri["is_emri_no"] != no


def test_celik_klasor_doluysa_yeni_numara(c, saat):
    """Kanal sıradaki revizyon klasörünü dolu bulduysa (`worker.isle` → `k.yeni_numara`) çelik revizyon da yeni numara alır."""
    r01_k(c)
    no = c.plan["is_emri_no"]
    c.k.yeni_numara = True
    k = _mutfak(c, "120x120")                                              # saat ilerlemedi: aynı saniyede de numara eskisiyle aynı çıkmaz
    assert k.is_emri["revizyon"] == 2 and k.is_emri["is_emri_no"] != no and k.is_emri["is_emri_no"].startswith("PM-")
    c.k.yeni_numara = False
    yeni = k.is_emri["is_emri_no"]
    saat(1000)
    k = _mutfak(c, "120x180")
    assert (k.is_emri["is_emri_no"], k.is_emri["revizyon"]) == (yeni, 3)   # sonraki revizyon son planın numarasını taşır


def test_yeni_talep_baska_sistemde_yeni_numara(c, saat):
    """Yeni talep konuşmayı sıfırlar: çelik plandan sonra prefabrik ev (ve tersi) r01 olur, yeni numara alır."""
    r01_k(c)
    no = c.plan["is_emri_no"]
    saat(1000)
    k = c.yaz("PA-04", katalog_kodu="PA04", niyet="yeni_talep")
    assert k.eylem == "is_emri" and (k.is_emri.get("yapi") or {}).get("sistem") != "celik", k.mesaj
    assert k.is_emri["revizyon"] == 1 and k.is_emri["is_emri_no"] != no
    no2 = k.is_emri["is_emri_no"]
    saat(1000)
    k = c.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik", niyet="yeni_talep")
    assert k.eylem == "is_emri" and k.is_emri["yapi"]["sistem"] == "celik"
    assert k.is_emri["revizyon"] == 1 and k.is_emri["is_emri_no"] not in (no, no2)


def test_revizyon_sayisi_suruyorsa_numara_surer_sistem_degisse_de(c, saat):
    """Varsayım (D-101): açık planın üstüne öteki sistemden bir ev revizyon olarak gelirse konuşma sıfırlanmaz, plan sıradaki
    revizyondur (r02) ve r01'in numarasını taşır. r02 hiçbir yolda r01'inkinden başka numarayla gelmez."""
    r01_k(c)
    no = c.plan["is_emri_no"]
    saat(1000)
    k = c.yaz("PA-04 olsun", katalog_kodu="PA04", niyet="revizyon")
    assert k.eylem == "is_emri" and (k.is_emri.get("yapi") or {}).get("sistem") != "celik", k.mesaj
    assert (k.is_emri["is_emri_no"], k.is_emri["revizyon"]) == (no, 2) and k.is_emri["kunye"]["proje_kodu"] == no
    saat(1000)
    k = c.yaz("Ç8801K olsun", katalog_kodu="Ç8801K", niyet="revizyon")
    assert k.eylem == "is_emri" and k.is_emri["yapi"]["sistem"] == "celik", k.mesaj
    assert (k.is_emri["is_emri_no"], k.is_emri["revizyon"]) == (no, 3)


def test_prefabrik_planin_ustune_celik_revizyon(tmp_path, saat):
    s = Sohbet(tmp_path, kabul=KABUL)
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    saat(1000)
    k = s.yaz("Ç8801K olsun", katalog_kodu="Ç8801K", niyet="revizyon")
    assert k.eylem == "is_emri" and k.is_emri["yapi"]["sistem"] == "celik", k.mesaj
    assert (k.is_emri["is_emri_no"], k.is_emri["revizyon"]) == (no, 2)
