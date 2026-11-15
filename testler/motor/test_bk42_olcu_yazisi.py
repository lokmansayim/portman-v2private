"""BK-42 · Bayi plan görselinde dış ölçü DXF ve PDF'teki gibi yazılır (Lokman, 15.11.2026 21:50 kartı "Evet, iş açılsın").

Görsel dış ölçüyü tek ondalıkla yazıyordu: 60 m² 2+1'in yeni hâlinde (PA-36) 951,25 cm başlıkta ve ölçüde "951,2 cm" çıkıyordu; DXF ve
PDF "951,25" yazar. Görselin ölçü yazısı artık DXF'in biçimlendiricisinden (`dxf_out.fmt`: en çok iki ondalık, sondaki sıfırlar atılır).
Ölçüsü tam sayı ya da tek ondalık olan evin görseli bayt bayt aynıdır (`araclar/aday_gorseli_yenile.py --kuru` "aynı" der).
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import matplotlib
import matplotlib.figure
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import bayi_gorseli as BG, dxf_out, geometry as G  # noqa: E402

SUNUCU_YAZI_TIPI = {"font.family": ["sans-serif"], "font.sans-serif": ["DejaVu Sans"], "text.hinting": "default"}


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _yazilar(ie: dict, yol: Path, monkeypatch) -> list[str]:
    """Plan görselini çizer, kaydedilen figürdeki bütün yazıları döndürür."""
    asil = matplotlib.figure.Figure.savefig
    toplanan: list[str] = []

    def kaydet(fig, *a, **k):
        toplanan.extend(t.get_text() for ax in fig.axes for t in ax.texts)
        return asil(fig, *a, **k)

    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", kaydet)
    with matplotlib.rc_context(SUNUCU_YAZI_TIPI):
        BG.plan_gorseli(copy.deepcopy(ie), yol)
    return toplanan


@pytest.mark.parametrize("cm, beklenen", [(951.25, "951,25"), (835.75, "835,75"), (800.75, "800,75"), (1076.75, "1076,75"),
                                          (647.5, "647,5"), (763.0, "763"), (689.583, "689,58"), (1319.017, "1319,02")])
def test_olcu_yazisi_dxf_ile_ayni(cm, beklenen):
    assert BG._fmt(cm) == dxf_out.fmt(cm) == beklenen


@pytest.mark.parametrize("ev, en, boy", [
    ("is_emri/adaylar/PA36.json", "647,5", "951,25"),           # 60 m² 2+1 yeni hâl: kartın konusu
    ("is_emri/adaylar/PA22.json", "689,58", "1319,02"),          # iki ondalıklı iki ölçü
    ("is_emri/YAN_VERANDALI_2plus1_6x8p5.json", "773", "1076,75"),   # anahtarsız İş Emri de (D-29 madde 6: Lokman'ın yorumundan düzeltme)
])
def test_gorselde_dis_olcu_ve_baslik(ev, en, boy, tmp_path, monkeypatch):
    ie = _ie(ev)
    plan = G.kur(copy.deepcopy(ie))
    assert (dxf_out.fmt(plan.W), dxf_out.fmt(plan.H)) == (en, boy)
    yazilar = _yazilar(ie, tmp_path / "plan.png", monkeypatch)
    assert f"{en} cm" in yazilar and f"{boy} cm" in yazilar
    assert any(t.endswith(f"({en}×{boy} cm)") for t in yazilar)
    assert not any("951,2 cm" in t or "1076,8" in t or "689,6" in t for t in yazilar)


def test_pa36_dxf_basligiyla_ayni(tmp_path, monkeypatch):
    """Görseldeki ölçü, aynı İş Emri'nin DXF'indeki pano grid satırının ölçüsüyle harfi harfine aynı."""
    import ezdxf
    ie = _ie("is_emri/adaylar/PA36.json")
    m = dxf_out.uret(copy.deepcopy(ie), tmp_path / "dxf")
    doc = ezdxf.readfile(tmp_path / "dxf" / m["dxf"])
    dxf_yazilari = [e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text for e in doc.modelspace().query("TEXT MTEXT")]
    assert any("647,5 × 951,25 cm" in t for t in dxf_yazilari)
    yazilar = _yazilar(ie, tmp_path / "plan.png", monkeypatch)
    assert "951,25 cm" in yazilar and "647,5 cm" in yazilar
