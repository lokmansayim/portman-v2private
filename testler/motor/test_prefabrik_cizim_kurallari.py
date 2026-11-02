"""D-31 madde 8 · Prefabrik ön onay çiziminin kural listesi (`kurallar/prefabrik/cizim_kurallari.json`) depoyla aynı.

Lokman, 29 Ekim 2026 11:12–11:15: "var olan çizim kurallarını güncelliyoruz aman bir daha başa dönmeyelim", "repoya, kural dosyasına json
veriye nereye kaydediyorsan kaydet ama bağlam kopmasın". Her satırın kararı `KARARLAR/`'da, kod yeri (dosya ve ad; `Sınıf.üye` de olur)
depoda, testi (dosya ve test işlevi) depoda; sabiti kodla aynı. Kod adı değişir ya da test silinirse bu test düşer: liste kodla birlikte
güncellenir. Kuralın kendisi kendi testinde sınanır; bu test yalnız listenin doğru yeri gösterdiğini denetler.
"""
from __future__ import annotations
import ast
import importlib
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
LISTE = KOK / "kurallar" / "prefabrik" / "cizim_kurallari.json"


def _adlar(yol: Path) -> set[str]:
    """Dosyanın üst düzey adları (işlev, sınıf, atama) ve `Sınıf.üye` adları."""
    agac = ast.parse(yol.read_text(encoding="utf-8"))
    out = set()
    for d in agac.body:
        if isinstance(d, (ast.FunctionDef, ast.ClassDef)):
            out.add(d.name)
        if isinstance(d, ast.ClassDef):
            out |= {f"{d.name}.{u.name}" for u in d.body if isinstance(u, ast.FunctionDef)}
            out |= {f"{d.name}.{h.id}" for u in d.body if isinstance(u, ast.Assign) for h in u.targets if isinstance(h, ast.Name)}
        if isinstance(d, ast.Assign):
            out |= {h.id for h in d.targets if isinstance(h, ast.Name)}
    return out


def _deger(yer: str):
    dosya, ad = yer.split("::")
    nesne = importlib.import_module(dosya[:-3].replace("/", "."))
    for parca in ad.split("."):
        nesne = getattr(nesne, parca)
    return json.loads(json.dumps(nesne))


def test_kural_listesi_depoyla_ayni():
    L = json.loads(LISTE.read_text(encoding="utf-8"))
    assert L["sema"] == "portman.prefabrik_cizim_kurallari/1"
    kodlar = [k["kod"] for k in L["kurallar"]]
    assert kodlar == [f"PC-{i:02d}" for i in range(1, len(kodlar) + 1)]           # sırayla, boşluksuz, tekrarsız
    adlar = {}
    for k in L["kurallar"]:
        assert k["baslik"] and k["kural"] and k["test"] and k["kod_yeri"], k["kod"]
        assert (KOK / "KARARLAR" / f"{k['karar']}.md").is_file(), k["kod"]
        assert re.fullmatch(r"2026-\d\d-\d\d", k["lokman"]["tarih"]) and re.fullmatch(r"\d\d:\d\d", k["lokman"]["saat"]) and k["lokman"]["soz"]
        for yer in k["kod_yeri"] + k["test"]:
            dosya, ad = yer.split("::")
            yol = KOK / dosya
            assert yol.is_file(), (k["kod"], yer)
            adlar.setdefault(dosya, _adlar(yol))
            assert ad in adlar[dosya], (k["kod"], yer)
        assert all(t.startswith("testler/") and t.split("::")[1].startswith("test_") for t in k["test"]), k["kod"]
        for s in k.get("sabitler", []):
            assert _deger(s["yer"]) == s["deger"], (k["kod"], s)
    # karar dosyaları listeyi anar (karar ↔ liste iki yönlü)
    for karar in sorted({k["karar"] for k in L["kurallar"] if k["karar"] == "D-31"}):
        assert "kurallar/prefabrik/cizim_kurallari.json" in (KOK / "KARARLAR" / f"{karar}.md").read_text(encoding="utf-8")
