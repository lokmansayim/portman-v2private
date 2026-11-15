"""Plan görselinde mahal yazısı odaya sığar (`bayi_gorseli._mahal_yazilarini_sigdir`; 15.11.2026, PA-33 canlı görseli).

Sunucunun yazı tipi DejaVu Sans'tır (CI de öyle). 140 m² evin (PA-08) ve büyüyen hâlinin (PA-33) 95 cm'lik iki EBV banyosunda
10 pt kalın ad komşu odaya taşıyordu ("EBV BANYO 2EBV BANYO 3"); 2,8 m²'lik EBV banyonun adı duvara ve pencere ölçüsü yazısına
biniyordu. Sığmayan yazı önce küçülür (en az 7 pt), yine sığmazsa iki satır olur. Sığan yazıya dokunulmaz: o görsel bayt bayt
eskisi gibidir. Anahtarsız İş Emri'nde (P6001, 6×8, Yan) adım hiç koşmaz. Testler DejaVu Sans'ı açıkça seçer; makinenin yazı tipi ayarı (yerel ortamda Inter) sonucu değiştirmez.
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import matplotlib
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import bayi_gorseli as BG  # noqa: E402
from shapely.geometry import box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

SUNUCU_YAZI_TIPI = {"font.family": ["sans-serif"], "font.sans-serif": ["DejaVu Sans"], "text.hinting": "default"}
TASAN_EVLER = ["is_emri/adaylar/PA08.json", "is_emri/adaylar/PA33.json"]
ANAHTARSIZ = ["is_emri/P6001_2plus1_6x6.json", "is_emri/ALTIN_2plus1_6x8.json", "is_emri/YAN_VERANDALI_2plus1_6x8p5.json"]
SIGAN_EVLER = ["testler/motor/veri/TK01_r07.json", "testler/motor/veri/TK02.json", "is_emri/adaylar/PA30.json", "is_emri/adaylar/PA34.json"]


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _ciz(ie: dict, yol: Path, monkeypatch, sigdir: bool = True) -> list:
    """Plan görselini sunucunun yazı tipiyle çizer; sığdırmadan önce ve sonra oda dışına taşan yazıları döndürür."""
    asil = BG._mahal_yazilarini_sigdir
    olcum = []

    def sar(fig, ax, etiketler, engel):
        rnd = fig.canvas.get_renderer(); ters = ax.transData.inverted()

        def kutu(t):
            bb = t.get_window_extent(rnd)
            (x0, y0), (x1, y1) = ters.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
            return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

        eng = unary_union([engel] + [kutu(t) for t in ax.texts if t.get_color() == BG.PENCERE])

        def tasanlar():
            out = []
            for poly, t_ad, t_alan, _y in etiketler:
                ic = poly.difference(eng)
                out += [(t.get_text(), t.get_fontsize(), kutu(t)) for t in (t_ad, t_alan) if kutu(t).difference(ic).area > 0.01]
            return out, [(t_ad.get_text(), kutu(t_ad)) for _p, t_ad, _a, _y in etiketler]

        olcum.append(tasanlar())
        if sigdir:
            asil(fig, ax, etiketler, engel)
        olcum.append(tasanlar())

    monkeypatch.setattr(BG, "_mahal_yazilarini_sigdir", sar)
    with matplotlib.rc_context(SUNUCU_YAZI_TIPI):
        BG.plan_gorseli(copy.deepcopy(ie), yol)
    return olcum


@pytest.mark.parametrize("ev", TASAN_EVLER)
def test_ebv_banyo_adlari_sigar(ev, tmp_path, monkeypatch):
    (once, _), (sonra, adlar) = _ciz(_ie(ev), tmp_path / "plan.png", monkeypatch)
    assert {a for a, _fs, _k in once} == {"EBV BANYO 1", "EBV BANYO 2", "EBV BANYO 3"}   # sorun gerçekti: üç ad taşıyordu
    assert sonra == []
    k = dict(adlar)
    assert not k["EBV BANYO 2"].intersects(k["EBV BANYO 3"])                            # iki ad birbirine değmez
    assert k["EBV BANYO 2"].bounds[3] - k["EBV BANYO 2"].bounds[1] < 25                  # tek satır kaldı, küçüldü


@pytest.mark.parametrize("ev", SIGAN_EVLER)
def test_sigan_yaziya_dokunulmaz(ev, tmp_path, monkeypatch):
    """Yazısı sığan evin görseli, sığdırma adımı hiç yokmuş gibi (eski kod) bayt bayt aynıdır; ölçmek de görseli değiştirmez."""
    olcum = _ciz(_ie(ev), tmp_path / "olculu.png", monkeypatch)
    assert olcum[0][0] == [] and olcum[1][0] == []
    monkeypatch.undo()
    with matplotlib.rc_context(SUNUCU_YAZI_TIPI):
        BG.plan_gorseli(copy.deepcopy(_ie(ev)), tmp_path / "yeni.png")
    monkeypatch.setattr(BG, "_mahal_yazilarini_sigdir", lambda *a: None)       # eski kodun yolu: ölçme de yok
    with matplotlib.rc_context(SUNUCU_YAZI_TIPI):
        BG.plan_gorseli(copy.deepcopy(_ie(ev)), tmp_path / "eski.png")
    assert (tmp_path / "yeni.png").read_bytes() == (tmp_path / "eski.png").read_bytes()


@pytest.mark.parametrize("ev", ANAHTARSIZ)
def test_anahtarsiz_is_emri_eski_yoldan(ev, tmp_path, monkeypatch):
    """Anahtarsız İş Emri'nde sığdırma adımı hiç çağrılmaz (İE-11: bayt bayt eski yol)."""
    cagri = []
    monkeypatch.setattr(BG, "_mahal_yazilarini_sigdir", lambda *a: cagri.append(1))
    with matplotlib.rc_context(SUNUCU_YAZI_TIPI):
        BG.plan_gorseli(copy.deepcopy(_ie(ev)), tmp_path / "plan.png")
    assert cagri == []


def test_iki_satir_ve_en_kucuk_boy(tmp_path, monkeypatch):
    """2,8 m²'lik EBV banyonun adı 7 pt'de de tek satıra sığmaz: iki satır olur ve odaya sığar."""
    (_, _), (sonra, adlar) = _ciz(_ie("is_emri/adaylar/PA33.json"), tmp_path / "plan.png", monkeypatch)
    assert sonra == []
    ad = [(m, k) for m, k in adlar if m.replace("\n", " ") == "EBV BANYO 1"]
    assert len(ad) == 1 and "\n" in ad[0][0]
