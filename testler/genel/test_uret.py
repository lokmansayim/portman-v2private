"""İE-08 · motor/genel/uret.py: perspektif süreci çökse de iş düşmez (perspektifsiz manifest, PDF var); yalnız liste kipi aynı listeyi verir;
Python sürümünden bağımsız toplama (toplam.py) yerleşik 3.11 davranışıyla aynı."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import toplam, uret  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
TANIM = KOK / "modeller" / "C8201.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_perspektif_sureci_cokunce_perspektifsiz_manifest(tmp_path, monkeypatch):
    asil = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda ad, *a, **k: object() if ad == "vtk" else asil(ad, *a, **k))   # VTK varmış gibi
    monkeypatch.setattr(uret.subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, -11, "", "Segmentation fault"))  # süreç çöker
    m = uret.uret(TANIM, tmp_path, is_emri_no="TEST", revizyon=1, set_yolu=SET, yontem="panel", perspektif=True, bayi=True)
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert m["passed"] and v["passed"] and v["errors"] == []
    assert v["perspektif"]["durum"] == "ÇİZİLEMEDİ" and "sinyal 11" in v["perspektif"]["neden"]
    assert any(w.startswith("perspektif: ÇİZİLEMEDİ") for w in m["warnings"])
    assert (tmp_path / "C8201_pafta.pdf").exists() and (tmp_path / "C8201_plan_bayi.png").exists() and m["pdf_sha256"]


def test_vtk_yoksa_perspektif_atlanir_is_gecer(tmp_path, monkeypatch):
    asil = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda ad, *a, **k: None if ad == "vtk" else asil(ad, *a, **k))
    m = uret.uret(TANIM, tmp_path, set_yolu=SET, yontem="panel", perspektif=True, bayi=False)
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert m["passed"] and v["perspektif"] == {"durum": "ÇİZİLEMEDİ", "neden": "VTK kurulu değil"}
    assert not (tmp_path / "C8201_pafta.pdf").exists() and m["pdf"] is None


def test_yalniz_liste_ayni_listeyi_verir(tmp_path):
    tam = tmp_path / "tam"; liste = tmp_path / "liste"
    m1 = uret.uret(TANIM, tam, set_yolu=SET, yontem="panel", perspektif=False, bayi=False)
    m2 = uret.uret(TANIM, liste, set_yolu=SET, yontem="panel", perspektif=False, bayi=False, yalniz_liste=True)
    assert m1["passed"] and m2["passed"]
    assert sha(tam / "C8201_yukleme.json") == sha(liste / "C8201_yukleme.json") and sha(tam / "C8201_girdi.json") == sha(liste / "C8201_girdi.json")
    v2 = json.loads((liste / "validation.json").read_text(encoding="utf-8"))
    assert v2["ciktilar"] == {"beklenen": 2, "var": 2, "eksik": [], "zorunlu_eksik": []} and v2["ifc"] == {} and v2["perspektif"]["durum"] == "ATLANDI"
    assert not (liste / "C8201_plan.png").exists() and not (liste / "C8201.ifc").exists()


def test_toplam_311_davranisi():
    # soldan sağa toplama: dengelenmiş toplamanın (3.12 sum) değiştirebileceği örnek; her sürümde aynı sonuç
    sayilar = [0.1] * 10 + [1e16, 1.0, -1e16]
    naif = 0.0
    for x in sayilar:
        naif = naif + x
    assert toplam.sum(sayilar) == naif and toplam.sum(sayilar, 0.0) == naif
    assert toplam.sum([1, 2, 3]) == 6 and toplam.sum([[1], [2]], []) == [1, 2] and toplam.sum([]) == 0
    assert uret.sum is toplam.sum
