"""Katalog erişimi: 37 model (kod, aile, m², oda programı) + motor için hazır İş Emri şablonları."""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KATALOG_JSON = Path(__file__).resolve().parent / "veri" / "katalog_37_proje.json"
SABLON_DIR = ROOT / "is_emri"
SABLONLAR = {"P6001": "P6001_2plus1_6x6.json"}          # kodlanmış katalog modelleri (büyüyecek)


def _m2(s) -> float | None:
    try:
        return float(str(s).replace(",", "."))
    except Exception:
        return None


class Katalog:
    def __init__(self, path: Path = KATALOG_JSON):
        self.modeller = {m["code"].upper(): m for m in json.loads(path.read_text(encoding="utf-8"))}

    @staticmethod
    def kod_normalize(s: str | None) -> str | None:
        if not s:
            return None
        t = s.strip().upper().replace("-", "").replace(" ", "")
        t = t.replace("C", "Ç") if re.fullmatch(r"C\d{4}", t) else t
        if re.fullmatch(r"\d{4}", t):
            t = "P" + t
        return t if re.fullmatch(r"[PÇ]\d{4}", t) else s.strip().upper()

    def bul(self, kod: str | None) -> dict | None:
        k = self.kod_normalize(kod)
        return self.modeller.get(k) if k else None

    def sablon_yolu(self, kod: str) -> Path | None:
        f = SABLONLAR.get(self.kod_normalize(kod) or "")
        return (SABLON_DIR / f) if f and (SABLON_DIR / f).exists() else None

    def yakin_modeller(self, alan_m2: float, oda: str | None = None, yapi: str | None = None, n: int = 3) -> list[dict]:
        adaylar = []
        for m in self.modeller.values():
            if yapi == "celik" and not m["code"].startswith("Ç"): continue
            if yapi in (None, "prefabrik") and yapi is not None and not m["code"].startswith("P"): continue
            if oda and m["type"] != oda: continue
            a = _m2(m["total_m2"])
            if a is None: continue
            adaylar.append((abs(a - alan_m2), m))
        adaylar.sort(key=lambda t: t[0])
        return [m for _, m in adaylar[:n]]

    @staticmethod
    def kisa(m: dict) -> str:
        return f"{m['code']} ({m['total_m2']} m², {m['type']}, {m['family'].lower()})"
