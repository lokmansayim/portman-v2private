"""İE-06 · Servis nabzı: her servis (ajan, gönderici, webhook) kendi JSON dosyasını düzenli yazar; /saglik ve nabiz.sh yaşına bakar.
Dosyada sır, numara ve mesaj metni olmaz."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path


def yaz(dizin: Path | str, ad: str, **alanlar) -> Path:
    d = Path(dizin) / "nabiz"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{ad}.json"
    gecici = p.with_suffix(".json.tmp")
    gecici.write_text(json.dumps({"zaman": int(time.time()), "ad": ad, **alanlar}, ensure_ascii=False), encoding="utf-8")
    os.replace(gecici, p)
    return p


def oku(dizin: Path | str, ad: str) -> dict | None:
    p = Path(dizin) / "nabiz" / f"{ad}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def yas(dizin: Path | str, ad: str) -> float | None:
    """Son nabızdan bu yana geçen saniye; dosya yoksa None."""
    v = oku(dizin, ad)
    if not v or not isinstance(v.get("zaman"), (int, float)):
        return None
    return max(0.0, time.time() - float(v["zaman"]))
