"""BK-65 · Montaj paftasının tavan omega planında yan yana iki omeganın boy yazıları birbirine binmez.

D-137'den (PR #283) sonra 80 m² 3+1'in (PA-21) verandasında duvar omegası (133,25) ile duvar yüzündeki tavan omegası (138,25) yan yana;
iki yazı aynı yere düşüyordu. Lokman kart 20 Kasım 2026 08:57:12 "Kalsın, kirişe göre"; seçeneğin metni: "Üst üste binen yazıyı ayrı küçük
işte düzeltirim." Düzeltme `motor/yerlesim/cizim._omega_yazilari_ayir`: binen iki yazıdan soldaki (yatayda alttaki) omeganın yazısı
omeganın öteki yanına geçer; yalnız yazının yeri değişir, çakışma yoksa sayfa aynen.
"""
from __future__ import annotations

import copy
import io
import contextlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor.genel import yazi_cakisma as YC  # noqa: E402
from motor.yerlesim import cizim  # noqa: E402


def _iki_cubuk(aralik: float, dik: bool = True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16.54, 11.69), dpi=100)    # öteki testlerin rcParams'ı (dpi) ölçeği değiştirmesin
    ax.set_xlim(0, 1500); ax.set_ylim(0, 1100); ax.set_aspect("equal")
    yazilar = []
    for i, boy in enumerate(("133,25", "138,25")):
        if dik:
            k = (700 + i * aralik, 300, 705 + i * aralik, 433)
            t = ax.text((k[0] + k[2]) / 2 + 6, 366, boy, rotation=90, fontsize=7.5, ha="left", va="center")
        else:
            k = (300, 700 + i * aralik, 433, 705 + i * aralik)
            t = ax.text(366, (k[1] + k[3]) / 2 + 6, boy, fontsize=7.5, ha="center", va="bottom")
        yazilar.append((t, k, dik))
    return fig, yazilar


@pytest.mark.parametrize("dik", [True, False])
def test_binen_yazilar_ayrilir(dik):
    fig, yazilar = _iki_cubuk(4, dik)
    assert YC.cakisanlar(YC.metin_kutulari(fig)), "deney kurulumu: iki yazı başta binmeli"
    cizim._omega_yazilari_ayir(fig, yazilar)
    assert YC.cakisanlar(YC.metin_kutulari(fig)) == []
    alt, ust = yazilar
    if dik:
        assert (alt[0].get_ha(), ust[0].get_ha()) == ("right", "left")
        assert alt[0].get_position()[0] == pytest.approx(702.5 - 6)
    else:
        assert (alt[0].get_va(), ust[0].get_va()) == ("top", "bottom")
        assert alt[0].get_position()[1] == pytest.approx(702.5 - 6)


def test_binmeyen_yazi_yerinde_kalir():
    fig, yazilar = _iki_cubuk(200)
    once = [(t.get_position(), t.get_ha()) for t, _, _ in yazilar]
    cizim._omega_yazilari_ayir(fig, yazilar)
    assert [(t.get_position(), t.get_ha()) for t, _, _ in yazilar] == once


def test_pa21_tavan_omega_sayfasi(tmp_path, monkeypatch):
    """80 m² 3+1: tavan omega sayfasında yazı çakışması 0; 133,25 omeganın solunda, 138,25 sağında."""
    from matplotlib.backends.backend_pdf import PdfPages
    from motor import kart_model
    sayfalar = []
    esk = PdfPages.savefig

    def kaydet(self, fig=None, **kw):
        if not sayfalar:
            sayfalar.append({t.get_text(): t for a in fig.axes for t in a.texts} | {"_cakisma": YC.cakisanlar(YC.metin_kutulari(fig))})
        return esk(self, fig, **kw)
    monkeypatch.setattr(PdfPages, "savefig", kaydet)
    ie = json.loads((KOK / "is_emri/adaylar/PA21.json").read_text(encoding="utf-8"))
    with contextlib.redirect_stdout(io.StringIO()):
        kart_model.uret(copy.deepcopy(ie), tmp_path, "PA21")
    s = sayfalar[0]
    assert s["_cakisma"] == []
    assert s["133,25"].get_ha() == "right" and s["138,25"].get_ha() == "left"
    assert s["133,25"].get_position()[0] < s["138,25"].get_position()[0]
