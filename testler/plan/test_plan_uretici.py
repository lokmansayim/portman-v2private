"""İE-14 PR-1: plan üreteci döngüsü (LLM'siz). Manuel arka uç elle yazılmış cevapları sırayla oynatır; Anthropic yolu sahte HTTP ile.

Elle yazılmış cevaplar LLM çıktısı değildir (`testler/plan/ornekler/`); gerçek LLM cevapları `testler/plan/kayitlar/`'a
`araclar/plan_dene.py` ile yazılır ve `test_plan_kayitlari.py` onları oynatır.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import llm, plan_uretici as PU  # noqa: E402

ORNEK = KOK / "testler" / "plan" / "ornekler"
TALEP = {"alan_m2": 95, "oda_programi": "3+1", "cati": {"tip": "kirma"}}


def ornek(ad):
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


def test_ilk_cevap_gecersiz_ikincisi_gecerli():
    s = PU.uret(TALEP, hazir=[ornek("gecersiz_3arti1_dar_odalar"), ornek("gecerli_3arti1_100")])
    assert s["durum"] == "gecerli" and len(s["denemeler"]) == 2
    assert not s["denemeler"][0]["gecerli"] and any("dar kenarı" in i for i in s["denemeler"][0]["ihlaller"])
    assert s["tanim"]["sema"] == "portman.yapi_tanimi/0.5-taslak" and s["ozet"]["brut_m2"] == 100.0
    assert s["cagri"] == 0                                    # manuel: ücretli çağrı yok


def test_uc_denemede_gecmezse_gecersiz_ve_dorduncu_cagri_yok():
    k = ornek("gecersiz_3arti1_dar_odalar")
    s = PU.uret(TALEP, hazir=[k, k, k, ornek("gecerli_3arti1_100")])
    assert s["durum"] == "gecersiz" and len(s["denemeler"]) == 3 and s["tanim"] is None


def test_ihlaller_ayni_konusmada_arac_sonucu_olarak_geri_gider(monkeypatch):
    goren = []
    asil = llm.arac_cagir

    def kayitci(sistem, mesajlar, *a, **k):
        goren.append(json.loads(json.dumps(mesajlar, ensure_ascii=False, default=str)))
        return asil(sistem, mesajlar, *a, **k)
    monkeypatch.setattr(llm, "arac_cagir", kayitci)
    PU.uret(TALEP, hazir=[ornek("gecersiz_3arti1_dar_odalar"), ornek("gecerli_3arti1_100")])
    assert len(goren) == 2 and len(goren[0]) == 1 and len(goren[1]) == 3
    assert goren[1][1]["role"] == "assistant" and goren[1][1]["content"][0]["type"] == "tool_use"
    sonuc = goren[1][2]["content"][0]
    assert sonuc["type"] == "tool_result" and sonuc["is_error"] and sonuc["tool_use_id"] == goren[1][1]["content"][0]["id"]
    assert "Banyo dar kenarı" in sonuc["content"]


def test_talep_metni_ornekler_ve_kurallar():
    m = PU.talep_metni(TALEP, PU.yakin_ornekler(95), PU.kurallar())
    assert "3+1 (3 yatak odası, 1 salon)" in m and "kırma" in m and "85.5–104.5" in m
    assert "### KT03 · 94 m²" in m and "yatak odası: en az 10.5 m², dar kenar en az 300 cm (eksenden eksene en az 315 cm)" in m


def test_kor_uretimde_model_kendisi_ornek_degil():
    assert [o["kod"] for o in PU.yakin_ornekler(88, 3, haric=("Ç8801",))] == ["KT02", "KT03", "Ç8201"]
    assert "Ç8801K" not in [o["kod"] for o in PU._banka()]          # çatı varyantı aynı plan: bir kez


def test_llm_hatasi_durum_hata(monkeypatch):
    def bozuk(*a, **k):
        raise llm.LLMHatasi("HTTP 529: overloaded")
    monkeypatch.setattr(llm, "arac_cagir", bozuk)
    s = PU.uret(TALEP, ayar={"backend": "anthropic"})
    assert s["durum"] == "hata" and "529" in s["hata"] and s["denemeler"] == []


def test_anthropic_istegi_arac_effort_ve_cevap(monkeypatch):
    giden = {}

    def sahte_post(url, headers, body, timeout=60):
        giden.update(body=body, headers=headers)
        return {"model": "claude-opus-5-5", "stop_reason": "tool_use", "usage": {"input_tokens": 9000, "output_tokens": 2500},
                "content": [{"type": "text", "text": "…"}, {"type": "tool_use", "id": "tu_1", "name": "plan_kaydet",
                                                              "input": ornek("gecerli_3arti1_100")}]}
    monkeypatch.setattr(llm, "_post", sahte_post)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "deneme-anahtari")
    s = PU.uret(TALEP, ayar={"backend": "anthropic"})
    b = giden["body"]
    assert b["model"] == "claude-opus-5-5" and b["output_config"] == {"effort": "medium"}
    assert b["tools"][0]["name"] == "plan_kaydet" and b["tool_choice"]["disable_parallel_tool_use"]
    assert "plan_kaydet aracını bir kez" in b["system"]
    assert s["durum"] == "gecerli" and s["cagri"] == 1 and s["girdi_token"] == 9000 and s["cikti_token"] == 2500


def test_anthropic_arac_cagrisi_yoksa_hata(monkeypatch):
    monkeypatch.setattr(llm, "_post", lambda *a, **k: {"stop_reason": "end_turn", "content": [{"type": "text", "text": "plan"}]})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "deneme-anahtari")
    with pytest.raises(llm.LLMHatasi, match="plan_kaydet çağrısı dönmedi"):
        llm.arac_cagir("s", [{"role": "user", "content": "x"}], "plan_kaydet", "a", {}, backend="anthropic")


def test_kayit_bicimi_ad_ve_numara_tasimaz():
    s = PU.uret(TALEP, hazir=[ornek("gecerli_3arti1_100")])
    k = PU.kayit(s, TALEP, "deneme")
    assert set(k) >= {"etiket", "talep", "durum", "denemeler", "cagri"} and k["denemeler"][0]["gecerli"]


def test_bozuk_taslak_ihlal_olur_ve_cagri_sayilir(monkeypatch):
    bozuk = ornek("gecerli_3arti1_100")
    bozuk["mahaller"][0]["dikdortgenler"] = []                       # şema reddeder (min_length 1): istisna değil ihlal
    s = PU.uret(TALEP, hazir=[bozuk, ornek("gecerli_3arti1_100")])
    assert s["durum"] == "gecerli" and len(s["denemeler"]) == 2 and any("şema" in i for i in s["denemeler"][0]["ihlaller"])
    from motor.genel import plan_derle
    monkeypatch.setattr(plan_derle, "derle", lambda *a, **k: (_ for _ in ()).throw(ZeroDivisionError("beklenmeyen")))
    s = PU.uret(TALEP, hazir=[ornek("gecerli_3arti1_100")])
    assert s["durum"] == "gecersiz" and "taslak derlenemedi: ZeroDivisionError" in s["denemeler"][0]["ihlaller"][0]


def test_llm_hatasi_cagri_olarak_sayilir(monkeypatch):
    monkeypatch.setattr(llm, "arac_cagir", lambda *a, **k: (_ for _ in ()).throw(llm.LLMHatasi("plan_kaydet çağrısı dönmedi")))
    s = PU.uret(TALEP, ayar={"backend": "anthropic"})
    assert s["durum"] == "hata" and s["cagri"] == 1
