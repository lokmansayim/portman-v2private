"""İE-08 PR-2a (Lokman, 13 Ekim 2026): bayiye giden üç çıktıda — `<kod>_plan_bayi.png`, `<kod>_bayi_gorsel.png` (alt sıra) ve şablon
paftasının iki sayfası — yazı kutuları (ölçü sayısı, yön etiketi, pencere etiketi, mahal adı, antet) birbirine binmez; yön etiketleri
ölçü çizgisini kapatmaz. Yedi modelde koşar. Figürler kaydedilmeden önce `Figure.savefig` / `PdfPages.savefig` sarılarak denetlenir
(`motor/genel/yazi_cakisma.py`); çizim baytlarına dokunulmaz."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import uret, yazi_cakisma as YC  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
MODELLER = ["C8801", "C8801K", "C8801L", "C8201", "KT01", "KT02", "KT03"]
BILGI = {"bayi_adi": "Deneme Bayi", "bayi_telefonu": "900000000555", "sevk_adresi": "Deneme Mah. Deneme Sok. No 1 Deneme İlçesi / Deneme İli",
         "ozel_istekler": ["çatı antrasit", "dış cephe krem"], "ozellikler": {"Dış Boya Rengi": "krem"}}
_RAPOR: dict[str, dict[str, dict]] = {}


def raporlar(model: str) -> dict[str, dict]:
    """Model bir kez üretilir; kaydedilen her figürün yazı raporu {dosya adı | 'pafta_sayfa_N': rapor} (test dosyası boyunca önbellekte)."""
    if model in _RAPOR:
        return _RAPOR[model]
    import matplotlib.figure
    from matplotlib.backends.backend_pdf import PdfPages
    r: dict[str, dict] = {}
    asil_fig, asil_pdf = matplotlib.figure.Figure.savefig, PdfPages.savefig

    def fig_savefig(self, fname, *a, **k):
        ad = Path(str(fname)).name if not hasattr(fname, "write") else "akis"
        r[ad] = YC.denetle(self, ad)
        return asil_fig(self, fname, *a, **k)

    def pdf_savefig(self, figure=None, **k):
        n = sum(1 for x in r if x.startswith("pafta_sayfa_")) + 1
        r[f"pafta_sayfa_{n}"] = YC.denetle(figure, f"pafta_sayfa_{n}")
        return asil_pdf(self, figure, **k)

    matplotlib.figure.Figure.savefig, PdfPages.savefig = fig_savefig, pdf_savefig
    try:
        with tempfile.TemporaryDirectory() as tmp:
            m = uret.uret(KOK / "modeller" / f"{model}.json", Path(tmp), is_emri_no="PM-TEST-20261013-1", revizyon=1, set_yolu=SET,
                          yontem="panel", perspektif=False, bayi=True, bilgi=BILGI)
            assert m["passed"], m.get("warnings")
    finally:
        matplotlib.figure.Figure.savefig, PdfPages.savefig = asil_fig, asil_pdf
    _RAPOR[model] = r
    return r


def _hatalar(rap: dict[str, dict], dosyalar: list[str]) -> list:
    h = []
    for d in dosyalar:
        assert d in rap and rap[d]["yazi"] > 5, (d, sorted(rap))
        if rap[d]["cakisan"]:
            h.append((d, "çakışan", rap[d]["cakisan"]))
        if rap[d]["cizgi_kapatan"]:
            h.append((d, "çizgiyi kapatan", rap[d]["cizgi_kapatan"]))
    return h


@pytest.mark.parametrize("model", MODELLER)
def test_plan_bayi_ve_kart_yazi_cakismaz(model):
    # bayi plan görseli (yön etiketleri en dıştaki ölçünün dışında; 15 cm kuralı; mahal adı/m² ayrık) ve kartın alt sırası (çatı planı sade;
    # VTK yoksa görünüşler ölçüsüz)
    kod = uret.kod_govde(json.loads((KOK / "modeller" / f"{model}.json").read_text(encoding="utf-8")))
    h = _hatalar(raporlar(model), [f"{kod}_plan_bayi.png", f"{kod}_bayi_gorsel_alt.png"])
    assert h == [], json.dumps(h, ensure_ascii=False, indent=1)


@pytest.mark.parametrize("model", MODELLER)
def test_pafta_yazi_cakismaz(model):
    # şablon paftası iki sayfa (Lokman 13.10: şimdi, bu PR'da): özellik tablosunda sarılan satırlar mürekkep aralığıyla; dar parça sayıları
    # içeri sırada; 2. sayfada görünüş ölçü şeritleri ölçeğe göre, çatı planı kenar/eğim yazıları çakışmadan. "..." hücreleri, antetteki
    # "95"/"ÇELİK" ve ÖZEL İSTEKLER satırları yalnız yerleşim kutusuyla örtüşür (mürekkep ayrık): yanlış alarm, `yerlesim_cakisan`da bilgi
    h = _hatalar(raporlar(model), ["pafta_sayfa_1", "pafta_sayfa_2"])
    assert h == [], json.dumps(h, ensure_ascii=False, indent=1)


def test_denetim_cakismayi_gorur():
    # denetimin kendisi: üst üste iki yazı (mürekkep) yakalanır; yalnız yerleşim kutusu örtüşen bitişik satırlar yanlış alarm sayılır
    # (ayrı listede); ölçü okunu kapatan kutulu etiket ve ok ucuna binen sayı yakalanır; eğim oku (gid'siz annotate) ölçü değildir
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from motor.genel import ciz_genel
    fig, ax = plt.subplots(figsize=(4, 3), dpi=100)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.text(50, 50, "AAAA", ha="center", va="center"); ax.text(52, 50, "BBBB", ha="center", va="center")
    ax.text(10, 90, "uzak", ha="left", va="center")
    ax.text(10, 80, "satır 1", ha="left", va="center", fontsize=8); ax.text(10, 76.4, "satır 2", ha="left", va="center", fontsize=8)   # bitişik: mürekkep ayrık
    ciz_genel.olcu(ax, (20, 20), (80, 20), "600", 3)                                                   # ölçü oku + sayısı (gid olcu_ok)
    ax.text(72, 20, "ETİKET", ha="center", va="center", bbox=dict(boxstyle="round,pad=0.35", fc="#1f5f93", ec="none"), color="white")   # oku kapatır, sayıya değmez
    ciz_genel.olcu(ax, (20, 5), (26, 5), "22,4", 0.5)                                                  # dar parça: sayı ok uçlarına biner
    ax.annotate("", xy=(60, 90), xytext=(90, 90), arrowprops=dict(arrowstyle="->", color="white", lw=1.0))   # eğim oku: ölçü değil
    ax.text(75, 90, "%33,0", ha="center", va="center", fontsize=7.2)
    r = YC.denetle(fig, "deneme")
    plt.close(fig)
    assert r["yazi"] == 9 and [(a, b) for a, b, _ in r["cakisan"]] == [("AAAA", "BBBB")]
    assert [(a, b) for a, b, _ in r["yerlesim_cakisan"]] == [("satır 1", "satır 2")]
    assert sorted(a for a, _, _ in r["cizgi_kapatan"]) == ["22,4", "ETİKET"]
