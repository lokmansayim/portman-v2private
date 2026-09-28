"""29.09 Opus 5.5 geçişi (Codex'in yazdığı, canlıda koşan beyin/llm.py): sahte cevaplarla, API çağrısı yok.
Opus 5.5 zorunlu tool_choice'ı reddettiği için auto + tek araç + effort low; beklenen tek talep_kaydet çağrısı ve
stop_reason=tool_use denetlenir. Öteki modellerin yolu (zorunlu araç) değişmedi. Bot adaptörü (PHP) de koşulur."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from beyin import llm

KOK = Path(__file__).resolve().parents[2]
ORNEK = json.loads((KOK / "kanal" / "self-test-request.json").read_text())["hazir_cikarim"]


def _cevap(stop, bloklar):
    return {"stop_reason": stop, "model": "claude-opus-5-5", "content": bloklar, "usage": {"input_tokens": 100, "output_tokens": 20}}


def test_opus_istegi_ve_basari(monkeypatch):
    istekler = []
    monkeypatch.setattr(llm, "_post", lambda url, h, govde, t=60: istekler.append(govde) or _cevap("tool_use", [
        {"type": "thinking", "thinking": "", "signature": "x"}, {"type": "tool_use", "name": "talep_kaydet", "input": ORNEK}]))
    talep, meta = llm.cikar_detayli("test", backend="anthropic", model="claude-opus-5-5", anahtar="sahte")
    g = istekler[0]
    assert g["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True} and g["output_config"] == {"effort": "low"}
    assert "temperature" not in g and g["max_tokens"] == 4096 and talep.katalog_kodu == "P6001" and meta["girdi_token"] == 100


@pytest.mark.parametrize("stop, bloklar", [
    ("max_tokens", [{"type": "tool_use", "name": "talep_kaydet", "input": ORNEK}]),
    ("end_turn", [{"type": "text", "text": "merhaba"}]),
    ("refusal", []),
    ("tool_use", [{"type": "tool_use", "name": "baska", "input": ORNEK}]),
    ("tool_use", [{"type": "tool_use", "name": "talep_kaydet", "input": ORNEK}] * 2),
])
def test_opus_eksik_ya_da_yanlis_cevap_hata(monkeypatch, stop, bloklar):
    monkeypatch.setattr(llm, "_post", lambda *a, **k: _cevap(stop, bloklar))
    with pytest.raises(llm.LLMHatasi):
        llm.cikar_detayli("test", backend="anthropic", model="claude-opus-5-5", anahtar="sahte")


def test_haiku_yolu_degismedi(monkeypatch):
    istekler = []
    monkeypatch.setattr(llm, "_post", lambda url, h, govde, t=60: istekler.append(govde) or _cevap("tool_use", [
        {"type": "tool_use", "name": "talep_kaydet", "input": ORNEK}]))
    llm.cikar_detayli("test", backend="anthropic", model="claude-haiku-4-5-20251001", anahtar="sahte")
    assert istekler[0]["tool_choice"] == {"type": "tool", "name": "talep_kaydet"} and "output_config" not in istekler[0]


@pytest.mark.parametrize("php", [p for p in ("/opt/php82/bin/php", shutil.which("php")) if p and Path(p).exists()])
def test_bot_adaptoru_php(php):
    r = subprocess.run([php, "claude_api_test.php"], cwd=KOK / "hosting" / "tests", capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "PASSED" in r.stdout, r.stdout + r.stderr
