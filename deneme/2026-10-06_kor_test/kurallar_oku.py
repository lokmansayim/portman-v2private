"""Kural setini okur: güncel set ya da `PORTMAN_KURALLAR` ile seçilen eski set (bkz. `../2026-10-03_yukleme/kural.py`)."""
from __future__ import annotations

import sys
from pathlib import Path

YUKLEME = Path(__file__).resolve().parent.parent / "2026-10-03_yukleme"
if str(YUKLEME) not in sys.path:
    sys.path.append(str(YUKLEME))
import kural  # noqa: E402

oku = kural.oku
yol = kural.yol
