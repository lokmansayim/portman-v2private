"""İE-14 kapanış incelemesi · K1 (15.10.2026): bayinin ölçüsü ve sözü sessizce değişmez.

G1 uyarlama ve seçim bayinin dış ölçüsünü tutar, tutmayan aday bayiye notla gider · G2 ölçü yönü korunur, 5 cm yuvarlama yazılır ·
C3 son basamakta değişen her alan yazılır · C4 "iç duvarlar 140" dış 140 değildir. LLM çağrısı yok.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_program as PP, plan_uretici as PU  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402


# ── G1 · bayinin dış ölçüsü ─────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("en,boy", [(10, 11), (8.8, 10), (9, 10.5)])
def test_g1_olcu_veren_bayiye_olcusu_tutan_plan(en, boy):
    # hakemin örnekleri: önceden uyarlama 765×1440, 1175×750, 1100×860 veriyordu ve notu yoktu
    s = PU.uret({"oda_programi": "2+1", "dis_olcu": {"en_m": en, "boy_m": boy}}, ayar={"acik": False})
    assert s["durum"] == "gecerli"
    hedef = {"en": round(en * 100), "boy": round(boy * 100)}
    assert s["adaylar"][0]["plan"]["dis_olcu"] == hedef
    for a in s["adaylar"]:
        tutuyor = PU.olcu_sapmasi(s["program"], a["plan"]) == (0, 0)
        assert tutuyor or a["degisen"], a["plan"]["dis_olcu"]                 # tutmayan aday notsuz gitmez


def test_g1_uyarlama_kaynagi_olcuye_getirilir():
    # Ç8201 (1095×750) bayinin ölçüsünü söylediği yönde tutar; uyarlama ölçüyü alana değil ölçüye göre ayarlar
    s = PU.uret({"oda_programi": "2+1", "dis_olcu": {"en_m": 10.94, "boy_m": 7.5}}, ayar={"acik": False})
    a = s["adaylar"][0]
    assert a["yol"] == "uyarlama" and a["plan"]["dis_olcu"] == {"en": 1095, "boy": 750} and a["degisen"] == []


def test_g1_donuk_aday_bayiye_yazilir():
    s = PU.uret({"oda_programi": "3+1", "dis_olcu": {"en_m": 12, "boy_m": 8}}, ayar={"acik": False})
    ilk, ikinci = s["adaylar"]
    assert ilk["plan"]["dis_olcu"] == {"en": 1200, "boy": 800} and ilk["degisen"] == []
    if ikinci["plan"]["dis_olcu"] != ilk["plan"]["dis_olcu"]:
        assert ikinci["degisen"] == ["dış ölçü 12 × 8 m döndürülmüş çizildi, ön cephe 8 m"]


def test_g1_secim_once_olcu_sonra_puan():
    pr = {"dis_olcu_cm": [1000, 1100]}
    tutan = {"plan": {"dis_olcu": {"en": 1000, "boy": 1100}}, "puan": 9.0, "yol": "cozucu"}
    donuk = {"plan": {"dis_olcu": {"en": 1100, "boy": 1000}}, "puan": 2.0, "yol": "cozucu"}
    uzak = {"plan": {"dis_olcu": {"en": 765, "boy": 1440}}, "puan": 1.0, "yol": "uyarlama"}
    assert PU._sec([[uzak, donuk], [tutan]], 3, pr) == [tutan, donuk, uzak]
    assert PU.olcu_notu(pr, uzak["plan"]) == "dış ölçü 10 × 11 m yerine 7,65 × 14,4 m"
    assert PU._sec([[uzak, tutan]], 2) == [uzak, tutan]                     # ölçü verilmediyse yalnız puan


# ── G2 · yön ve yuvarlama ───────────────────────────────────────────────────────────────────────────────────────────────
def test_g2_yon_korunur_yuvarlama_yazilir():
    p, _ = PP.talepten({"oda_programi": "2+1", "dis_olcu": {"en_m": 10.94, "boy_m": 7.5}})
    assert p["dis_olcu_cm"] == [1095, 750]                                  # sıralanmaz: en ön cephe
    assert p["varsayimlar"] == ["dış ölçü 10,94 × 7,5 m, 5 cm ızgaraya 10,95 × 7,5 m olarak alındı"]
    p, _ = PP.talepten({"oda_programi": "2+1", "dis_olcu": {"en_m": 7.52, "boy_m": 10.03}})
    assert p["dis_olcu_cm"] == [750, 1005] and "7,52 × 10,03 m" in p["varsayimlar"][0]
    p, _ = PP.talepten({"oda_programi": "2+1", "dis_olcu": {"en_m": 8, "boy_m": 12}})
    assert p["dis_olcu_cm"] == [800, 1200] and p["varsayimlar"] == []       # ızgaradaysa not yok


def test_g2_yuvarlama_notu_uretim_notlarinda():
    s = PU.uret({"oda_programi": "2+1", "dis_olcu": {"en_m": 7.52, "boy_m": 10.03}}, ayar={"acik": False})
    assert s["notlar"][0].startswith("dış ölçü 7,52 × 10,03 m")


def test_g2_llm_ne_olcuyu_ne_varsayimi_degistirir():
    kod = PP.talepten({"oda_programi": "2+1", "dis_olcu": {"en_m": 7.52, "boy_m": 10}, "ozel_istekler": ["şömine"]})[0]
    llm = {**kod, "dis_olcu_cm": [900, 900], "varsayimlar": ["uydurma"], "uygulanamayan": ["şömine"]}
    b = PP.birlestir(kod, llm, ["şömine"])
    assert b["dis_olcu_cm"] == [750, 1000] and b["varsayimlar"] == kod["varsayimlar"]


# ── C3 · son basamakta değişen her şey yazılır ──────────────────────────────────────────────────────────────────────────
def _prog(**k):
    return PP.PlanProgrami.model_validate({"yatak": 2, **k}).model_dump()


def test_c3_program_farki_dis_karkas_olcu_hedef_egim_veranda():
    eski = _prog(alan_m2=85, dis_olcu_cm=[800, 1000], dis_karkas=140, egim_yuzde=30, cati_tipi="kirma",
                 oda_hedefleri=[{"islev": "salon", "m2": 30}], veranda={"alan_m2": 12})
    yeni = _prog(alan_m2=85, dis_olcu_cm=[850, 1000], cati_tipi="kirma", veranda={"istiyor": True, "konum": "kose"})
    f = PP.program_farki(eski, yeni)
    assert "dış ölçü 8 × 10 m → 8,5 × 10 m" in f
    assert "dış duvarlar 80'lik (140 uygulanmadı)" in f
    assert "çatı eğimi %30 → varsayılan" in f
    assert "salon 30 m² isteği alınmadı" in f
    assert "veranda: belirtilmemiş → var" in f and "veranda yeri: belirtilmemiş → köşede" in f
    assert "veranda alanı 12 → belirtilmemiş" in f


def test_c3_hakemin_senaryosu_bos_kalmaz():
    eski = _prog(alan_m2=80, dis_olcu_cm=[800, 1000], dis_karkas=140)
    yeni = _prog(alan_m2=80, dis_olcu_cm=[850, 1000])
    assert PP.program_farki(eski, yeni)                                     # önceden []: plan 80'lik ve 8,5×10 çizilir, bayiye söylenmezdi


def test_c3_llm_eklenen_dis_140_yazilir():
    assert PP.program_farki(_prog(alan_m2=80), _prog(alan_m2=80, dis_karkas=140)) == ["dış duvarlar 140'lık"]
    assert PP.program_farki(_prog(alan_m2=80), _prog(alan_m2=80)) == []


# ── C4 · yalnız dış duvar 140 ───────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("istek,dis", [
    ("dış duvarlar 140 olsun", 140), ("140'lık dış duvar", 140), ("140 lık dış karkas", 140), ("karkas 140 olsun", 140),
    ("dış duvarları 140 yapın", 140),
    ("iç duvarlar 140 olsun", None), ("banyo duvarı 140 olsun", None), ("duvarlar 140 olsun", None), ("İç karkas 140", None)])
def test_c4_dis_140_deseni(istek, dis):
    p, kalan = PP.talepten({"oda_programi": "2+1", "alan_m2": 80, "ozel_istekler": [istek]})
    assert p["dis_karkas"] == dis
    assert (kalan == []) == (dis == 140)                                   # okunamayan "uygulayamadım"a düşer, sessiz kalmaz


def test_c4_ic_duvar_istegi_plan_dis_140_cizmez():
    s = PU.uret({"oda_programi": "2+1", "alan_m2": 80, "ozel_istekler": ["iç duvarlar 140 olsun"]}, ayar={"acik": False})
    assert s["program"]["dis_karkas"] is None and s["okunamayan"] == ["iç duvarlar 140 olsun"]
    assert all(a["plan"].get("dis_karkas") != 140 for a in s["adaylar"])
    assert denetle(s["adaylar"][0]["plan"], {"oda_programi": "2+1", "alan_m2": 80})["gecerli"]
