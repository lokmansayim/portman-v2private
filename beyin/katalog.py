"""Katalog erişimi: 37 model (kod, aile, m², oda programı) + motor için hazır İş Emri şablonları."""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KATALOG_JSON = Path(__file__).resolve().parent / "veri" / "katalog_37_proje.json"
ADAYLAR_JSON = Path(__file__).resolve().parent / "veri" / "adaylar.json"      # İE-04 aday kaydı (şablonlar is_emri/adaylar/)
ADAYLAR_TEST_JSON = Path(__file__).resolve().parent / "veri" / "adaylar_test.json"   # yalnız test_adaylari=True iken yüklenir
SABLON_DIR = ROOT / "is_emri"
ADAY_SABLON_DIR = SABLON_DIR / "adaylar"
SABLONLAR = {"P6001": "P6001_2plus1_6x6.json"}          # kodlanmış katalog modelleri (büyüyecek)


def _m2(s) -> float | None:
    try:
        return float(str(s).replace(",", "."))
    except Exception:
        return None


class Katalog:
    """37 katalog modeli + kodlanmış şablonlar + İE-04 aday kaydı.

    Aday kaydı (veri/adaylar.json): [{"kod", "durum": test|kosullu|gecerli, "sablon": "adaylar/<kod>.json", "referans_model",
    "oda_programi", "katalog_m2", "kapali_m2", "veranda_m2", "ozet": {...}, "kaynak": {...}, "gorsel": "adaylar/<kod>.png"}].
    Görünürlük: 'test' yalnız test_adaylari=True iken (yerel); 'gecerli' ancak kabul_edilmis verilmişse o kümede olanlar
    (kalıcı mod: mühendis kabulü kayıtlı olanlar, K-A10), verilmemişse hepsi; 'kosullu' hiçbir zaman sunulmaz."""

    def __init__(self, path: Path = KATALOG_JSON, adaylar_path: Path = ADAYLAR_JSON, test_adaylari: bool = False,
                 kabul_edilmis: set | None = None):
        self.modeller = {m["code"].upper(): m for m in json.loads(path.read_text(encoding="utf-8"))}
        self.test_adaylari = bool(test_adaylari)
        self.kabul_edilmis = set(kabul_edilmis) if kabul_edilmis is not None else None
        ham = json.loads(adaylar_path.read_text(encoding="utf-8")) if adaylar_path.exists() else []
        if self.test_adaylari and ADAYLAR_TEST_JSON.exists():          # test verisi ayrı dosyada; canlı pakette yüklenmez
            ham = list(ham) + [dict(a, durum="test") for a in json.loads(ADAYLAR_TEST_JSON.read_text(encoding="utf-8"))]
        self.adaylar = {str(a["kod"]).upper(): a for a in ham if isinstance(a, dict) and a.get("kod")}

    def aday_gorunur(self, a: dict) -> bool:
        d = a.get("durum")
        if d == "test":
            return self.test_adaylari
        if d == "gecerli":
            return self.kabul_edilmis is None or str(a["kod"]).upper() in self.kabul_edilmis
        return False

    def aday(self, kod: str | None) -> dict | None:
        k = self.kod_normalize(kod)
        a = self.adaylar.get(k) if k else None
        return a if a and self.aday_gorunur(a) else None

    def gorunur_adaylar(self) -> list[dict]:
        return [a for a in self.adaylar.values() if self.aday_gorunur(a)]

    def aday_sablon_yolu(self, kod: str) -> Path | None:
        a = self.aday(kod)
        if not a or not a.get("sablon"):
            return None
        yol = SABLON_DIR / a["sablon"]
        return yol if yol.exists() else None

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
        """Kodlanmış katalog şablonu; yoksa görünür aday şablonu (İE-04). Test adayı yalnız test_adaylari=True iken bulunur."""
        f = SABLONLAR.get(self.kod_normalize(kod) or "")
        if f and (SABLON_DIR / f).exists():
            return SABLON_DIR / f
        return self.aday_sablon_yolu(kod)

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
