"""Yazı çakışma denetimi (İE-08 PR-2a; Lokman, 13 Ekim 2026: bayiye giden üç çıktıda yazı kutuları birbirine binmesin).

Matplotlib figüründeki bütün yazıların (ölçü sayısı, yön etiketi, pencere etiketi, mahal adı, başlık, antet) ekran kutuları toplanır
(`metin_kutulari`); aynı eksende üst üste binen çiftler `cakisanlar` ile bulunur. Yön etiketlerinin ölçü çizgilerini (plan_eksen'in
`annotate` okları) kapatıp kapatmadığı `cizgi_kapatanlar` ile bakılır. Testte (`testler/genel/test_yazi_cakismasi.py`) `Figure.savefig`
ve `PdfPages.savefig` sarılarak `plan_bayi.png`, `bayi_gorsel` alt sırası ve şablon paftasının iki sayfası kaydedilmeden önce denetlenir.
Çizim baytlarına dokunmaz."""
from __future__ import annotations

PAY_PX = 0.5          # iki kutu arasında bu kadar (piksel) örtüşme çakışma sayılmaz (kenar kenara yazılar)


def _renderer(fig):
    try:
        fig.canvas.draw()
        return fig.canvas.get_renderer()
    except Exception:                                   # tuvalsiz figür (PdfPages): Agg tuvali tak
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig); fig.canvas.draw()
        return fig.canvas.get_renderer()


def metin_kutulari(fig) -> list[dict]:
    """Figürdeki görünür, boş olmayan yazılar: {metin, kutu (x0, y0, x1, y1; piksel), eksen, tur}. tur: 'yazi' | 'kutulu' (bbox yaması olan)."""
    r = _renderer(fig)
    out = []
    for i, ax in enumerate(fig.axes):
        yazilar = list(ax.texts) + [ax.title, ax.xaxis.label, ax.yaxis.label]
        for t in yazilar:
            s = t.get_text()
            if not s or not s.strip() or not t.get_visible():
                continue
            p = t.get_bbox_patch()
            bb = p.get_window_extent(r) if p is not None else t.get_window_extent(r)
            out.append({"metin": s.replace("\n", " / "), "kutu": (float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1)), "eksen": i,
                        "tur": "kutulu" if p is not None else "yazi"})
    for t in fig.texts:
        s = t.get_text()
        if s and s.strip() and t.get_visible():
            bb = t.get_window_extent(r)
            out.append({"metin": s.replace("\n", " / "), "kutu": (float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1)), "eksen": -1, "tur": "yazi"})
    return out


def olcu_cizgileri(fig) -> list[dict]:
    """plan_eksen'in ölçü okları (`annotate` ile çizilen): {kutu, eksen}."""
    from matplotlib.text import Annotation
    r = _renderer(fig)
    out = []
    for i, ax in enumerate(fig.axes):
        for t in ax.texts:
            if isinstance(t, Annotation) and getattr(t, "arrow_patch", None) is not None and not t.get_text():
                bb = t.arrow_patch.get_window_extent(r)
                out.append({"kutu": (float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1)), "eksen": i})
    return out


def _ortusme(a, b, pay: float = PAY_PX) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0]) - pay
    h = min(a[3], b[3]) - max(a[1], b[1]) - pay
    return w * h if (w > 0 and h > 0) else 0.0


def cakisanlar(kutular: list[dict], pay: float = PAY_PX) -> list[tuple[str, str, float]]:
    """Aynı eksende üst üste binen yazı çiftleri (metin, metin, örtüşme px²)."""
    out = []
    for i in range(len(kutular)):
        for j in range(i + 1, len(kutular)):
            a, b = kutular[i], kutular[j]
            if a["eksen"] != b["eksen"]:
                continue
            o = _ortusme(a["kutu"], b["kutu"], pay)
            if o > 0:
                out.append((a["metin"], b["metin"], round(o, 1)))
    return out


def cizgi_kapatanlar(kutular: list[dict], cizgiler: list[dict], secici=None, pay: float = PAY_PX) -> list[tuple[str, float]]:
    """Ölçü çizgisini kapatan yazılar (varsayılan: bbox yamalı yazılar = yön etiketleri ve mahal kutuları)."""
    sec = secici or (lambda k: k["tur"] == "kutulu")
    out = []
    for k in kutular:
        if not sec(k):
            continue
        for c in cizgiler:
            if c["eksen"] == k["eksen"] and _ortusme(k["kutu"], c["kutu"], pay) > 0:
                out.append((k["metin"], round(_ortusme(k["kutu"], c["kutu"], pay), 1)))
                break
    return out


def denetle(fig, ad: str = "") -> dict:
    """Tek figür için rapor: {ad, yazi: n, cakisan: [...], cizgi_kapatan: [...]}."""
    k = metin_kutulari(fig)
    return {"ad": ad, "yazi": len(k), "cakisan": cakisanlar(k), "cizgi_kapatan": cizgi_kapatanlar(k, olcu_cizgileri(fig))}
