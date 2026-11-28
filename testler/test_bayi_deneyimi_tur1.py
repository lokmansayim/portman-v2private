"""WhatsApp bayi deneyimi tur 1 (28 Kasım 2026; canlı v2026.11.25, 15 muhtemel bayi talebi, PF WhatsApp_Bayi_Deneyimi/).

S13: yalnız "teşekkürler" "Anlayamadım" alıyordu → nezaket cevabı, planı olana planın durumu.
S02: "8x10 prefabrik ev ne kadar" niyet "soru" okunuyor, ölçü düşüyordu → talep sayılır, sonuna fiyat cümlesi.
S07/S08: prefabrik planda yönlendirilen istekten sonra yazıyla yapılabilen iş söylenir.
S15: "ne yapabiliyorsun" fiyat cevabı alıyordu → "Nasıl çalışır?" yolu (kanal/worker.py).
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
from test_celik_revizyon_karar import Sohbet, var  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402
import worker  # noqa: E402


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


# ── S13: teşekkür ──────────────────────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin", ["teşekkürler", "Teşekkür ederim hocam", "sağolun", "eyvallah abi", "kolay gelsin, iyi çalışmalar",
                                   "Allah razı olsun", "tşk"])
def test_yalniz_tesekkur_nezaketle_cevaplanir(s, metin):
    k = s.yaz(metin, niyet="diger")
    assert (k.eylem, k.gerekce) == ("cevapla", "teşekkür")
    assert k.mesaj == "Rica ederim. Yeni plan için model kodu ya da ölçü yazmanız yeterli."


@pytest.mark.parametrize("metin", ["teşekkürler 1 olsun", "tamam teşekkürler", "teşekkürler, mutfak penceresi 120x120 olsun", "evet",
                                   "merhaba", "PA-04 teşekkürler"])
def test_baska_soz_varsa_tesekkur_degil(metin):
    assert not K._yalniz_tesekkur(metin)


def test_planli_bayiye_tesekkurde_plan_durumu(s):
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    k = s.yaz("teşekkürler", niyet="diger")
    assert k.mesaj.startswith(f"Rica ederim. Planınız ({no} r01) onayınızı bekliyor.")
    assert s.k.d["asama"] == "onay_bekliyor" and s.plan["revizyon"] == 1        # plan aynen, onay yok


# ── S02: fiyat sorusuyla gelen talep ─────────────────────────────────────────────────────────────────────────────────────

def test_olculu_fiyat_sorusu_talep_sayilir(s):
    k = s.yaz("8x10 prefabrik ev ne kadar", niyet="soru", yapi_turu="prefabrik", dis_olcu={"en_m": 8, "boy_m": 10})
    assert k.gerekce != "genel soru"
    assert k.mesaj.rstrip().endswith(K.FIYAT_SORUSU_CEVABI), k.mesaj
    assert (s.k.d.get("taslak") or {}).get("dis_olcu"), s.k.d.get("taslak")


def test_m2_ve_oda_programli_fiyat_sorusu(s):
    k = s.yaz("2+1 85 m2 prefabrik kaça olur", niyet="soru", yapi_turu="prefabrik", oda_programi="2+1", alan_m2=85)
    assert (k.eylem, k.soru_alani) == ("sor", "oncelik")
    assert k.mesaj.rstrip().endswith(K.FIYAT_SORUSU_CEVABI)


def test_olcusuz_fiyat_sorusu_bugunku_gibi(s):
    k = s.yaz("prefabrik ev ne kadar", niyet="soru", yapi_turu="prefabrik")
    assert k.gerekce == "genel soru"


def test_llm_yinelenen_olcu_talep_sayilmaz(s):
    """Ölçü mesajda yazılı değilse (LLM bağlamdan yineledi) bugünkü soru cevabı."""
    k = s.yaz("fiyatı ne kadar", niyet="soru", dis_olcu={"en_m": 8, "boy_m": 10})
    assert k.gerekce == "genel soru"


def test_acik_planda_fiyat_sorusu_plan_durumu(s):
    _plan(s, "PA04")
    k = s.yaz("8x10 olsa ne kadar", niyet="soru", dis_olcu={"en_m": 8, "boy_m": 10})
    assert k.gerekce == "genel soru: plan durumu"


# ── S07/S08: yönlendirilen istekte yapılabilen iş ──────────────────────────────────────────────────────────────────────

def test_yonlendirilen_istekte_yapilabilen_soylenir(s):
    _plan(s, "PA04")
    k = s.yaz("verandayı kaldır", varyantlar=[var("veranda_kaldir", "verandayı kaldır")])
    assert k.eylem == "yonlendir" and k.mesaj.startswith('"verandayı kaldır" değişikliği otomatik yapılamıyor.'), k.mesaj
    assert K.PREFABRIK_YAPILABILEN in k.mesaj
    assert s.plan["revizyon"] == 1


# ── S15: "ne yapabiliyorsun" ───────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin,beklenen", [("ne yapabiliyorsun", True), ("Neler yapabilirsiniz?", True), ("Portman nedir?", True),
                                             ("Nasıl çalışır?", True), ("neler yapabilirsin bu evde", False),
                                             ("bu pencere nasıl çalışır", False), ("ne kadar", False)])
def test_ne_yapabiliyorsun_nasil_calisir_yolu(metin, beklenen):
    assert worker.nasil_calisir_sozu(metin) is beklenen


# ── S10: yalnız "tamam" onay değildir (öneri; Lokman'ın kartı) ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin", ["tamam", "Tamam hocam", "ok", "peki", "olur abi", "tmm", "güzel olmuş"])
def test_tamam_onay_sayilmaz_dugmeyle_sorulur(s, metin):
    _plan(s, "PA04")
    no = s.plan["is_emri_no"]
    k = s.yaz(metin, niyet="onay")
    assert (k.eylem, k.gerekce) == ("cevapla", "onay soruldu")
    assert k.mesaj.startswith(f"Planı ({no} r01) onaylıyor musunuz?")
    assert [b["baslik"] for b in k.butonlar] == ["Onayla", "Revize et"]
    assert s.k.d["asama"] == "onay_bekliyor" and not s.k.d.get("onaylanan")
    k = s.dugme(f"o:{no}:1")
    assert k.gerekce == "plan onaylandı" and s.k.d["asama"] == "onaylandi"


@pytest.mark.parametrize("metin", ["onaylıyorum", "onay", "tamam onaylıyorum", "Onaylıyoruz hocam"])
def test_acik_onay_sozu_onaydir(s, metin):
    _plan(s, "PA04")
    k = s.yaz(metin, niyet="onay")
    assert k.gerekce == "plan onaylandı" and s.k.d["asama"] == "onaylandi"
