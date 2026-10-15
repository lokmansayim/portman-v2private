"""İE-14 r2 · R2: koordinatsız program, deterministik yerleşim çözücü ve bankadan uyarlama (LLM'siz).

Çözücünün ve uyarlamanın her çıktısı denetçiden (`plan_denetim.denetle`) geçmiş plandır; aynı program aynı planı verir; iki seçenek birbirinin
aynası ya da dönüğü değildir. Uyarlama kaynakları 14a'ya getirilmiş banka planlarıdır; kör üretimde model kaynaktan dışlanır.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_cozucu as PC, plan_program as PP, plan_uyarlama as PUY  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402
from beyin.plan_sema import tanimdan  # noqa: E402

PROGRAMLAR = {
    "3arti1_95": {"yatak": 3, "alan_m2": 95},
    "2arti1_82_yan_veranda": {"yatak": 2, "alan_m2": 82, "veranda": {"istiyor": True, "konum": "yan"}},
    "2arti1_88_kose_ayri_mutfak": {"yatak": 2, "alan_m2": 88, "mutfak": "ayri", "veranda": {"istiyor": True, "konum": "kose"}},
    "3arti1_120_iki_banyo_depo": {"yatak": 3, "alan_m2": 120, "banyo": 2, "depo": 1},
    "1arti1_50": {"yatak": 1, "alan_m2": 50},
}


# ── program ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_program_talepten_llmsiz():
    p, kalan = PP.talepten({"oda_programi": "3+1", "alan_m2": 95, "cati": {"tip": "kirma"}, "veranda": {"istiyor": True, "konum": "on"},
                            "ozel_istekler": ["iki banyo olsun", "mutfak ayrı olsun", "kiler", "dış duvarlar 140 olsun", "şömine"]})
    assert (p["yatak"], p["banyo"], p["mutfak"], p["depo"], p["dis_karkas"], p["cati_tipi"]) == (3, 2, "ayri", 1, 140, "kirma")
    assert kalan == ["şömine"]


@pytest.mark.parametrize("istek", ["depo olmasın", "iki banyo mu olsa?", "mutfak ayrı mı olur"])
def test_program_olumsuz_ve_soru_tanınmaz(istek):
    p, kalan = PP.talepten({"oda_programi": "2+1", "alan_m2": 80, "ozel_istekler": [istek]})
    assert (p["banyo"], p["depo"], p["mutfak"]) == (1, 0, None) and kalan == [istek]


def test_program_ayar_kapaliyken_llm_cagrilmaz_okunamayan_yazilir():
    s = PP.oku({"oda_programi": "2+1", "alan_m2": 80, "ozel_istekler": ["şömine olsun"]}, ayar={"acik": False})
    assert s["cagri"] == 0 and s["okunamayan"] == ["şömine olsun"] and s["program"]["yatak"] == 2


def test_program_llm_oda_sayisini_degistiremez():
    hazir = {"yatak": 4, "salon": 1, "banyo": 2, "mutfak": "ayri", "uygulanamayan": ["şömine"]}
    s = PP.oku({"oda_programi": "2+1", "alan_m2": 80, "ozel_istekler": ["ebeveyn için ayrı ıslak hacim", "şömine"]}, hazir=hazir)
    assert s["kaynak"] == "llm" and s["program"]["yatak"] == 2 and s["program"]["banyo"] == 2 and s["program"]["uygulanamayan"] == ["şömine"]


def test_program_yoksa_hata():
    assert PP.oku({"alan_m2": 80})["hata"]


# ── çözücü ────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ad", sorted(PROGRAMLAR))
def test_cozucu_denetciden_gecen_iki_farkli_plan(ad):
    prog = PROGRAMLAR[ad]
    r = PC.coz(prog)
    assert len(r["adaylar"]) == 2, r["ihlaller"]
    assert r["sure_ms"] < 30000
    t = {"oda_programi": f"{prog['yatak']}+1", "alan_m2": prog["alan_m2"]}
    for a in r["adaylar"]:
        assert denetle(a["plan"], t)["gecerli"]
        assert a["yol"] == "cozucu"
    assert PC.topoloji(r["adaylar"][0]["kalip"]) != PC.topoloji(r["adaylar"][1]["kalip"])


def test_cozucu_belirlenimci():
    a, b = PC.coz(PROGRAMLAR["3arti1_95"]), PC.coz(PROGRAMLAR["3arti1_95"])
    assert [x["plan"] for x in a["adaylar"]] == [x["plan"] for x in b["adaylar"]]


def test_cozucu_cati_alti_veranda_besik_istenirse_kirma_ve_not():
    hz = PC.hazirla({"yatak": 2, "alan_m2": 80, "cati_tipi": "besik", "veranda": {"istiyor": True, "ortu": "cati"}})
    assert hz["cati"] == "kirma" and hz["notlar"]
    hz = PC.hazirla({"yatak": 2, "alan_m2": 80, "cati_tipi": "besik", "veranda": {"istiyor": True}})
    assert hz["cati"] == "besik" and hz["veranda"]["ortu"] == "pergola" and not hz["notlar"]


def test_cozucu_ozel_istek_planin_icinde():
    r = PC.coz(PROGRAMLAR["3arti1_120_iki_banyo_depo"])
    for a in r["adaylar"]:
        islev = [m["islev"] for m in a["plan"]["mahaller"]]
        assert islev.count("banyo") == 2 and islev.count("depo") == 1


# ── uyarlama ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_sapma_duzeltmesi_c8801():
    p = tanimdan(json.loads((KOK / "modeller" / "C8801.json").read_text(encoding="utf-8")))
    xs = {v for m in p["mahaller"] for r in m["dikdortgenler"] for v in (r[0], r[2])}
    assert 630 in xs and 635 not in xs


def test_uyarlama_kaynaklari_14a_ya_getirilir():
    kodlar = {k["kod"] for k in PUY.kaynaklar()}
    assert {"Ç8201", "Ç8801", "KT02"} <= kodlar
    for k in PUY.kaynaklar():
        assert denetle(k["plan"], {})["gecerli"]
        assert sum(1 for m in k["plan"]["mahaller"] if m["islev"] == "veranda") <= 1


def test_kor_uretimde_model_kaynaktan_dislanir():
    assert all(not PUY.kod_esit(k["kod"], "C8201") for k in PUY.kaynaklar(("C8201",)))
    assert PUY.kod_esit("KT02", "KT-02") and PUY.kod_esit("Ç8801K", "C8801")


def test_simetriler_geri_doner():
    p = PUY.kaynaklar()[0]["plan"]
    assert PUY.ayna_x(PUY.ayna_x(p)) == p and PUY.ayna_y(PUY.ayna_y(p)) == p and PUY.devrik(PUY.devrik(p)) == p


def test_uzat_kesiti_kesen_uzar_otesindeki_kayar():
    p = {"dis_olcu": {"en": 1000, "boy": 800}, "mahaller": [{"ad": "A", "islev": "salon", "dikdortgenler": [[0, 0, 600, 800]]},
                                                          {"ad": "B", "islev": "yatak_odasi", "dikdortgenler": [[600, 0, 1000, 800]]}],
         "kapilar": [], "pencereler": [], "cati": {"tip": "besik"}}
    q = PUY.uzat(p, "x", 300, 100)
    assert q["dis_olcu"]["en"] == 1100 and q["mahaller"][0]["dikdortgenler"] == [[0, 0, 700, 800]]
    assert q["mahaller"][1]["dikdortgenler"] == [[700, 0, 1100, 800]]
    assert PUY.uzat(p, "x", 300, -400) is None


def test_uyarlama_c8201_82_yan_verandadan_denetciden_gecer():
    r = PUY.uyarla(PROGRAMLAR["2arti1_82_yan_veranda"])
    assert r["adaylar"] and r["adaylar"][0]["kaynak"] == "Ç8201" and r["adaylar"][0]["yol"] == "uyarlama"
    assert denetle(r["adaylar"][0]["plan"], {"oda_programi": "2+1", "alan_m2": 82})["gecerli"]


def test_uyarlama_alan_ayarinda_veranda_derinligi_degismez():
    r = PUY.uyarla({"yatak": 2, "alan_m2": 99, "veranda": {"istiyor": True, "konum": "on"}})
    assert r["adaylar"]
    for a in r["adaylar"]:
        v = next(m for m in a["plan"]["mahaller"] if m["islev"] == "veranda")["dikdortgenler"][0]
        assert v[3] - v[1] <= 250
