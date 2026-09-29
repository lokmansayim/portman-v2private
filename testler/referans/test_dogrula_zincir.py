"""D-02: yeniden dondurma bir karara dayanır. dogrula.py'nin zincir denetimi geçici bir referans klasöründe sınanır
(depodaki referanslara dokunulmaz; Motor koşulmaz).

Koşum: python -m pytest testler/referans/test_dogrula_zincir.py -q
"""
import hashlib
import shutil
import sys
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parent
sys.path.insert(0, str(REF))
import dogrula  # noqa: E402


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def ref(tmp_path, monkeypatch):
    """Depodaki iki referansın kopyası (2026-09-28 ve 2026-09-28b) geçici bir klasörde."""
    for ad in ("2026-09-28", "2026-09-28b"):
        shutil.copytree(REF / ad, tmp_path / ad)
    monkeypatch.setattr(dogrula, "REF", tmp_path)
    return tmp_path


def _yeni_referans(ref: Path, karar_satiri: str | None, gerekce: str = "Deneme: bir PDF izi değişti.") -> Path:
    """2026-09-28b'den türeyen 2026-09-28c: bir PDF izi değişir, GEREKCE.md özeti tutarlı tutulur (elle bozulmuş değil)."""
    yeni = ref / "2026-09-28c"
    shutil.copytree(ref / "2026-09-28b", yeni)
    p = yeni / "pdf_parmak_izleri.txt"
    satirlar = p.read_text(encoding="utf-8").splitlines()
    satirlar[0] = "0" * 64 + satirlar[0][64:]
    eski_sha = _sha(p)
    p.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    g = (yeni / "GEREKCE.md").read_text(encoding="utf-8").replace(eski_sha, _sha(p))
    g = "\n".join(l for l in g.splitlines() if not l.startswith("Karar:"))
    g = g.replace(next(l for l in g.splitlines() if l.startswith("Gerekçe:")), f"Gerekçe: {gerekce}")
    if karar_satiri:
        g = g.replace("\n## Önceki referansa", f"\n{karar_satiri}\n\n## Önceki referansa")
    (yeni / "GEREKCE.md").write_text(g, encoding="utf-8")
    return yeni


def test_depodaki_zincir_saglam(ref):
    son, bilgi = dogrula.referans_zinciri(ref / "2026-09-28b")
    assert son["karar"] == "D-02"
    assert any("değişen 18" in b for b in bilgi)


def test_kararsiz_degisiklik_reddedilir(ref):
    with pytest.raises(dogrula.ReferansHatasi, match="karar"):
        dogrula.referans_zinciri(_yeni_referans(ref, None))


def test_olmayan_karar_reddedilir(ref):
    with pytest.raises(dogrula.ReferansHatasi, match="karar"):
        dogrula.referans_zinciri(_yeni_referans(ref, "Karar: D-99"))


def test_var_olan_kararla_kabul(ref):
    son, bilgi = dogrula.referans_zinciri(_yeni_referans(ref, "Karar: D-02"))
    assert son["ad"] == "2026-09-28c" and any("değişen 1" in b for b in bilgi)


def test_ayni_gerekce_reddedilir(ref):
    g = next(l for l in (ref / "2026-09-28b" / "GEREKCE.md").read_text(encoding="utf-8").splitlines() if l.startswith("Gerekçe:"))
    with pytest.raises(dogrula.ReferansHatasi, match="gerekçe"):
        dogrula.referans_zinciri(_yeni_referans(ref, "Karar: D-02", gerekce=g[len("Gerekçe:"):].strip()))


def test_elle_degisen_dosya_reddedilir(ref):
    yeni = _yeni_referans(ref, "Karar: D-02")
    p = yeni / "dxf_parmak_izleri.txt"
    p.write_text(p.read_text(encoding="utf-8").replace("a", "b", 1), encoding="utf-8")
    with pytest.raises(dogrula.ReferansHatasi, match="elle"):
        dogrula.referans_zinciri(yeni)
