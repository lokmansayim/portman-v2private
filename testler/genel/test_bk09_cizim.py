"""BK-09 PR-2 · M8 (G1): dış 140'ta iç duvarlar ölçü zincirinden düşmez (`ciz_genel.zincirler` eşiği dış kaplama + dış duvar kalınlığına göre); M7: KT başlığında m² koddan.

80'lik karkasta iç duvarın ucu dış çizgiden 9,2 cm, 140'lıkta 15,2 cm uzakta; sabit 12,5 cm eşik 140'lık duvarda iç noktaları düşürüyordu
(İE-08 › Son geometri turu › G1; şablon "ölçü zinciri dört yanda, içte oda bölmeleri", `plan_paftasi_sablonu.md`)."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from beyin import varyant as V  # noqa: E402
from motor.genel import ciz_genel, yapi  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def kural_seti():
    eski = os.environ.get("PORTMAN_KURALLAR")
    os.environ["PORTMAN_KURALLAR"] = str(KOK / "kurallar" / "liste" / "setler" / "0.19.json")
    yield
    if eski is None:
        os.environ.pop("PORTMAN_KURALLAR", None)
    else:
        os.environ["PORTMAN_KURALLAR"] = eski


def tanim(kod: str) -> dict:
    return json.loads((KOK / "modeller" / f"{kod}.json").read_text(encoding="utf-8"))


def ic_noktalar(y: dict) -> dict:
    """Zincirdeki iç duvar aksı noktaları, yan yan."""
    aks = {round((d["kutu"][0] + d["kutu"][2]) / 2 if d["yon"] == "y" else (d["kutu"][1] + d["kutu"][3]) / 2, 2)
           for d in y["duvarlar"] if d["sinif"] == "ic"}
    return {yan: sorted(v for v in z if v in aks) for yan, z in ciz_genel.zincirler(y).items()}


@pytest.mark.parametrize("kod", ["C8201", "C8801", "C8801K", "C8801L"])
def test_dis_140_ic_duvarlar_zincirde_kalir(kod):
    once = ic_noktalar(yapi.kur(tanim(kod)))
    sonra = ic_noktalar(yapi.kur(V.tanim_uygula(tanim(kod), {"op": "dis_karkas_140"})))
    assert any(once.values()) and sonra == once


def test_c8201_dis_140_sartnamedeki_on_zincir():
    """Şartnamedeki referans paftayla (`deneme/2026-10-02_celik/sonuc/C8201_dis_karkas_140_pafta.png`) aynı iç noktalar."""
    y = yapi.kur(V.tanim_uygula(tanim("C8201"), {"op": "dis_karkas_140"}))
    assert ic_noktalar(y) == {"alt": [347.5, 498.5], "ust": [347.5, 538.5], "sol": [375.0], "sag": []}


def test_kt03_zaten_140_ic_duvarlar_zincirde():
    """KT-03'ün dış karkası tanımda 140'lık; altın çıktısında iç noktalar yoktu (D-16 ile yeniden donduruldu)."""
    z = ic_noktalar(yapi.kur(tanim("KT03")))
    assert z["alt"] and z["ust"] and z["sag"], z


@pytest.mark.parametrize("kod", ["C8201", "C8801", "C8801K", "C8801L", "KT01", "KT02"])
def test_80_karkasta_zincir_degismez(kod):
    """80'lik karkasta eşik 12,5 cm kalır: bugünkü zincirler aynen."""
    y = yapi.kur(tanim(kod))
    assert ciz_genel.zincir_esigi(y) == 12.5


# ───────────────────────── BK-09 M7: KT başlığında m² koddan ─────────────────────────
@pytest.mark.parametrize("kod, m2", [("KT02", "92 m²"), ("KT03", "94 m²")])
def test_kt_basliginda_m2_koddan(kod, m2):
    from motor.genel import cati_genel, girdi_genel, kural
    t = tanim(kod); kur = kural.oku()
    y = yapi.kur(t); m = girdi_genel.metraj(y, cati_genel.cati_kur(t["cati"], kur), kur)
    ad = girdi_genel.baslik_adi(t, m["oturum_m2"])
    assert m2 in ad and ad.count("m²") == 1 and ad.startswith(t["kod"] + " · "), ad
    assert tanim(kod)["ad"] == t["ad"], "model dosyası değişmez (D-07)"


@pytest.mark.parametrize("kod", ["C8201", "C8801", "C8801K", "C8801L"])
def test_katalog_basligi_aynen(kod):
    from motor.genel import girdi_genel
    t = tanim(kod)
    assert girdi_genel.baslik_adi(t, 123.4) == f"{t['kod']} · {t['ad']}"
