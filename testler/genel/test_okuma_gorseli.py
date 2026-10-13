"""İE-08 8a PR-2b (A4) · bayiye giden iki yeni görsel (`motor/genel/okuma_gorseli.py`): "1 / 2 / Hiçbiri" okuma görseli ve r0N başlık
görseli önce–sonra (alttaki çatı planı ve iki perspektif aynı görselde; altın koşuda perspektif yok, görünüşler çizilir).

Yedi modelde: yazıların mürekkep kutuları binmez, yazı ölçü okunu kapatmaz (`motor/genel/yazi_cakisma.denetle`; bayiye giden çizimlere
yazı eklenirken bu denetim koşulur — `.claude/rules/motor-cizim.md`); görseller ≤ 5 MB ve telefonda okunsun diye dikey (paneller alt
alta). Okuma görselinde iki numara rozeti var; önce–sonra çatı varyantı değişince üstte iki çatı planı çizer."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import celik_okuma as CO, varyant as V  # noqa: E402
from motor.genel import okuma_gorseli as OG, yazi_cakisma as YC  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
MODELLER = ["C8201", "C8801", "C8801K", "C8801L", "KT01", "KT02", "KT03"]


@pytest.fixture(scope="module", autouse=True)
def kural_seti():
    eski = os.environ.get("PORTMAN_KURALLAR")
    os.environ["PORTMAN_KURALLAR"] = str(SET)
    try:
        yield
    finally:
        if eski is None:
            os.environ.pop("PORTMAN_KURALLAR", None)
        else:
            os.environ["PORTMAN_KURALLAR"] = eski


@pytest.fixture
def denetim(monkeypatch):
    """Kaydedilen her figür önce denetlenir (test_yazi_cakismasi.py ile aynı yol)."""
    import matplotlib.figure as MF
    bulgular: list[tuple] = []
    eski = MF.Figure.savefig

    def yakala(self, *a, **k):
        r = YC.denetle(self, str(a[0]) if a else "")
        bulgular.append((Path(str(a[0])).name, r["cakisan"], r["cizgi_kapatan"]))
        return eski(self, *a, **k)
    monkeypatch.setattr(MF.Figure, "savefig", yakala)
    return bulgular


def tanim(kod: str) -> dict:
    return json.loads((KOK / "modeller" / f"{kod}.json").read_text(encoding="utf-8"))


def boyut(yol: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(yol) as im:
        return im.size


@pytest.mark.parametrize("kod", MODELLER)
def test_okuma_ve_once_sonra_yazi_cakismaz(kod, tmp_path, denetim):
    t = tanim(kod)
    iki = [a for a in CO.pencere_adaylari(t) if not a["vasistas"]][:2]
    yol = OG.okumalar(t, iki, tmp_path / "okuma", kod, olcu=(120, 120))
    a = iki[0]
    op = {"op": "pencere_olcu", "aciklik": a["aciklik"], "en": 120, "yuk": 120, "aciklama": a["aciklama"] + " → 120/120"}
    try:
        t2 = V.tanim_uygula(t, op)
    except V.VaryantHatasi:                                   # o pencere 120 genişliğe sığmıyorsa yalnız yükseklik değişir
        op = {**op, "en": a["en"], "yuk": 100}
        t2 = V.tanim_uygula(t, op)
    ys = OG.once_sonra(t, t2, tmp_path / "os", kod, [op], 1, 2, perspektif=False)
    for p in (yol, ys):
        assert p.is_file() and p.stat().st_size <= 5 * 1024 * 1024
        w, h = boyut(p)
        assert h > w, (p.name, w, h)                          # paneller alt alta
    bulgu = [(ad, c, k) for ad, c, k in denetim if c or k]
    assert bulgu == [], bulgu
    assert len(denetim) >= 3                                  # okuma + önce–sonra üst + alt sıra denetlendi


def test_dis_140_ve_cati_once_sonra(tmp_path, denetim):
    t = tanim("C8801")
    op = {"op": "dis_karkas_140", "aciklama": "dış duvarlar 140'lık karkas (16,5 cm)"}
    y1 = OG.once_sonra(t, V.tanim_uygula(t, op), tmp_path / "d", "C8801", [op], 1, 2, perspektif=False)
    op2 = {"op": "cati_varyanti", "kod": "Ç8801L", "aciklama": "çatı Ç8801-L"}
    y2 = OG.once_sonra(t, tanim("C8801L"), tmp_path / "c", "C8801L", [op2], 2, 3, perspektif=False)
    assert y1.is_file() and y2.is_file() and [(ad, c, k) for ad, c, k in denetim if c or k] == []


def test_okuma_rozeti_iki_numara(tmp_path, monkeypatch):
    """Okuma görselinde 1 ve 2 numaralı rozet (büyük yazı) ve iki daire var; başlıkta adayların tarifi."""
    import matplotlib.figure as MF
    yazilar: list[str] = []
    eski = MF.Figure.savefig

    def yakala(self, *a, **k):
        for ax in self.axes:
            yazilar.extend(t.get_text() for t in ax.texts if t.get_fontsize() >= 20)
            yazilar.append(ax.get_title(loc="left"))
        return eski(self, *a, **k)
    monkeypatch.setattr(MF.Figure, "savefig", yakala)
    t = tanim("C8801")
    r = CO.oku("salondaki sol taraftaki pencere 120x180 olsun", t, {"kod": "Ç8801", "varyantlar": ["Ç8801K", "Ç8801L"]})
    OG.okumalar(t, r["pencere"]["adaylar"], tmp_path, "C8801", olcu=r["pencere"]["olcu"])
    assert sorted(x for x in yazilar if x in ("1", "2")) == ["1", "2"]
    assert any("arkaya yakın" in x and x.startswith("1 ·") for x in yazilar) and any("öne yakın" in x and x.startswith("2 ·") for x in yazilar)
