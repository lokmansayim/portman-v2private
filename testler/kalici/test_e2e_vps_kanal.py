"""İE-06 · kanal/tests/e2e_vps_kanal.py sarmalayıcısı: uçtan uca senaryo (sahte Meta → webhook → ajan → gönderici → panel; gerçek
Postgres ve Motor) `ortam_kur.sh --dogrula` koşusunda da sınansın. LLM, WhatsApp ve canlı yok; ~1–2 dakika sürer."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from conftest import ADMIN, KOK


@pytest.mark.skipif(not ADMIN, reason="PORTMAN_TEST_PG yok")
def test_e2e_vps_kanal():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI", "ANTHROPIC"))}
    r = subprocess.run([sys.executable, str(KOK / "kanal" / "tests" / "e2e_vps_kanal.py")], env=env, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-5000:] + r.stderr[-2000:]
    assert "✗" not in r.stdout and " geçti" in r.stdout
