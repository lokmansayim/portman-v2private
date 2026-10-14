"""Yazı çakışma denetimi (İE-08 PR-2a; Lokman, 13 Ekim 2026: bayiye giden üç çıktıda yazı kutuları birbirine binmesin, yazı ölçü okunu
kapatmasın).

Matplotlib figüründeki bütün yazıların (ölçü sayısı, yön etiketi, pencere etiketi, mahal adı, başlık, antet) **mürekkep kutuları**
toplanır (`metin_kutulari`): yazının gerçek glif sınırı (`TextPath` uzantıları + yazı tipinin alçalma payı). Yerleşim kutusu (yazı
tipinin satır yüksekliği: çıkma + alçalma boşluklarıyla) komşu satır ya da hücrede örtüşse de mürekkep örtüşmüyorsa çakışma sayılmaz —
Lokman 13.10: "gerçek çakışmayı yanlış alarmdan ayır" (ör. 12 pt "..." hücreleri, 3,6 pt "95" / "ÇELİK", üst üste satırlar). bbox yaması
olan yazılarda (yön etiketi, veranda adı) yamanın kutusu alınır. Döndürülmüş yazı: 0/90/270° için eksene paralel mürekkep kutusu,
`rotation_mode='anchor'` ile başka açılarda döndürülmüş dikdörtgen (çokgen), aksi hâlde yerleşim kutusu.

- `cakisanlar`: aynı eksende mürekkep kutuları örtüşen yazı çiftleri (örtüşme > PAY_PX² piksel).
- `olcu_cizgileri`: ölçü okları — `plan_eksen`'in `annotate` okları (gövde + uç; yol çokgeni) ve şablon paftasının `Sayfa.olcu` çizgileri
  (`gid` "olcu_cizgi" / "olcu_centik").
- `cizgi_kapatanlar`: ölçü okunu/çentiğini kapatan yazılar (mürekkep kutusu ok yoluna değiyor; KT-02 "25,1" ve "22,4" örneği).
- `kapi_yaylari` + `cizgi_kapatanlar`: kapı açılım yayını (`gid` "kapi_yay") kesen yazılar (BK-09: KT-02 paftasında "BANYO").
- `sayfa_disindakiler`: mürekkebi figürün dışına taşan yazılar (BK-09: Ç8801-L paftası 2. sayfada "TASLAK").

Testte (`testler/genel/test_yazi_cakismasi.py`) `Figure.savefig` ve `PdfPages.savefig` sarılarak `plan_bayi.png`, `bayi_gorsel` alt
sırası ve şablon paftasının iki sayfası kaydedilmeden önce denetlenir. Çizim baytlarına dokunmaz."""
from __future__ import annotations
import math

PAY_PX = 1.0          # bu kadar piksel kareden küçük örtüşme (kenar kenara yazılar, yuvarlama) çakışma sayılmaz
KIYMIK_PX = 0.8       # kesişim her iki yönde de bundan ince ise yuvarlama kıymığıdır (Agg metrikleri tam piksele yuvarlar), çakışma değil


def _gercek(inter, pay: float) -> float:
    """Kesişim alanı; kıymık (iki yönden biri KIYMIK_PX'ten ince) ya da pay altı ise 0."""
    if inter.is_empty or inter.area <= pay:
        return 0.0
    x0, y0, x1, y1 = inter.bounds
    return inter.area if (x1 - x0) >= KIYMIK_PX and (y1 - y0) >= KIYMIK_PX else 0.0


def _renderer(fig):
    try:
        fig.canvas.draw()
        return fig.canvas.get_renderer()
    except Exception:                                   # tuvalsiz figür (PdfPages): Agg tuvali tak
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig); fig.canvas.draw()
        return fig.canvas.get_renderer()


def _kutu_poligon(x0, y0, x1, y1):
    from shapely.geometry import box
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _murekkep(t, r, dpi: float):
    """Yazının mürekkep çokgeni (piksel) ve yerleşim kutusu. bbox yaması varsa ikisi de yamanın kutusu."""
    from matplotlib.textpath import TextPath
    from shapely.geometry import Polygon
    from shapely import affinity
    s = t.get_text()
    yama = t.get_bbox_patch()
    L = (yama.get_window_extent(r) if yama is not None else t.get_window_extent(r))
    yer = _kutu_poligon(L.x0, L.y0, L.x1, L.y1)
    if yama is not None or "\n" in s:
        return yer, yer
    prop = t.get_fontproperties()
    try:
        ex = TextPath((0, 0), s, size=t.get_fontsize(), prop=prop).get_extents()      # pt; taban çizgisine göre (y0 < 0: alçalma)
        _w, _h, d = r.get_text_width_height_descent(s, prop, ismath=False)             # piksel; d: yazı tipinin alçalma payı
    except Exception:
        return yer, yer
    sc = dpi / 72.0
    rot = t.get_rotation() % 360
    if abs(rot) < 0.5:
        taban = L.y0 + d
        ink = _kutu_poligon(L.x0 + ex.x0 * sc, taban + ex.y0 * sc, L.x0 + ex.x1 * sc, taban + ex.y1 * sc)
    elif abs(rot - 90) < 0.5:                        # saat yönünün tersine: alçalma sağa (+x), yazı yukarı akar
        taban = L.x1 - d
        ink = _kutu_poligon(taban - ex.y1 * sc, L.y0 + ex.x0 * sc, taban - ex.y0 * sc, L.y0 + ex.x1 * sc)
    elif abs(rot - 270) < 0.5:                       # saat yönünde: alçalma sola (−x), yazı aşağı akar
        taban = L.x0 + d
        ink = _kutu_poligon(taban + ex.y0 * sc, L.y1 - ex.x1 * sc, taban + ex.y1 * sc, L.y1 - ex.x0 * sc)
    elif t.get_rotation_mode() == "anchor":          # çatı kenar yazıları: ha/va çapaya göre, sonra döndürme
        ax_, ay_ = t.get_transform().transform(t.get_position())
        w = (ex.x1 - ex.x0) * sc; h = (ex.y1 - ex.y0) * sc
        ha, va = t.get_ha(), t.get_va()
        x0 = {"left": 0.0, "center": -w / 2, "right": -w}.get(ha, -w / 2)
        y0 = {"bottom": 0.0, "center": -h / 2, "top": -h, "baseline": ex.y0 * sc, "center_baseline": -h / 2}.get(va, -h / 2)
        dik = Polygon([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])
        ink = affinity.translate(affinity.rotate(dik, rot, origin=(0, 0)), ax_, ay_)
    else:
        ink = yer
    return ink, yer


def metin_kutulari(fig) -> list[dict]:
    """Figürdeki görünür, boş olmayan yazılar: {metin, murekkep (çokgen), yerlesim (çokgen), kutu (x0, y0, x1, y1; mürekkep sınırı),
    eksen, tur}. tur: 'yazi' | 'kutulu' (bbox yaması olan)."""
    r = _renderer(fig)
    out = []
    for i, ax in enumerate(fig.axes):
        for t in list(ax.texts) + [ax.title, ax.xaxis.label, ax.yaxis.label]:
            s = t.get_text()
            if not s or not s.strip() or not t.get_visible():
                continue
            ink, yer = _murekkep(t, r, fig.dpi)
            out.append({"metin": s.replace("\n", " / "), "murekkep": ink, "yerlesim": yer, "kutu": tuple(round(v, 1) for v in ink.bounds),
                        "eksen": i, "tur": "kutulu" if t.get_bbox_patch() is not None else "yazi"})
    for t in fig.texts:
        s = t.get_text()
        if s and s.strip() and t.get_visible():
            ink, yer = _murekkep(t, r, fig.dpi)
            out.append({"metin": s.replace("\n", " / "), "murekkep": ink, "yerlesim": yer, "kutu": tuple(round(v, 1) for v in ink.bounds),
                        "eksen": -1, "tur": "yazi"})
    return out


def _yol_cokgeni(verts, codes, lw_px: float):
    """Çizgi yolu (MOVETO ile bölünmüş parçalar) → kalınlığı kadar şişirilmiş çokgen."""
    from matplotlib.path import Path as MplPath
    from shapely.geometry import LineString, MultiLineString
    parcalar, cur = [], []
    for v, c in zip(verts, codes if codes is not None else [MplPath.LINETO] * len(verts)):
        if c == MplPath.MOVETO:
            if len(cur) > 1:
                parcalar.append(cur)
            cur = [tuple(v)]
        elif c in (MplPath.LINETO, MplPath.CURVE3, MplPath.CURVE4):
            cur.append(tuple(v))
    if len(cur) > 1:
        parcalar.append(cur)
    if not parcalar:
        return None
    g = MultiLineString([LineString(p) for p in parcalar if len(p) > 1]) if len(parcalar) > 1 else LineString(parcalar[0])
    return g.buffer(max(lw_px / 2, 0.4))


def olcu_cizgileri(fig) -> list[dict]:
    """Ölçü okları: `plan_eksen`'in `annotate` okları (gövde + uç) ve `Sayfa.olcu` çizgileri (gid olcu_cizgi / olcu_centik). {ad, poligon, eksen}."""
    from matplotlib.text import Annotation
    r = _renderer(fig)
    sc = fig.dpi / 72.0
    out = []
    for i, ax in enumerate(fig.axes):
        for t in ax.texts:
            ap = getattr(t, "arrow_patch", None)
            if isinstance(t, Annotation) and ap is not None and not t.get_text() and t.get_gid() == "olcu_ok":   # eğim okları (çatı planı) ölçü değildir
                try:
                    yol = ap.get_transform().transform_path(ap.get_path())
                    g = _yol_cokgeni(yol.vertices, yol.codes, ap.get_linewidth() * sc)
                except Exception:
                    bb = ap.get_window_extent(r); g = _kutu_poligon(bb.x0, bb.y0, bb.x1, bb.y1)
                if g is not None:
                    out.append({"ad": "ok", "poligon": g, "eksen": i})
        for ln in ax.lines:
            if (ln.get_gid() or "").startswith("olcu_"):
                xy = ln.get_transform().transform(list(zip(ln.get_xdata(), ln.get_ydata())))
                g = _yol_cokgeni(xy, None, ln.get_linewidth() * sc)
                if g is not None:
                    out.append({"ad": ln.get_gid(), "poligon": g, "eksen": i})
    return out


def kapi_yaylari(fig) -> list[dict]:
    """Kapı açılım yayları (`Arc`, gid "kapi_yay"): yay çizgisi kalınlığı kadar şişirilmiş çokgen (piksel). {ad, poligon, eksen}."""
    sc = fig.dpi / 72.0
    out = []
    for i, ax in enumerate(fig.axes):
        for p in ax.patches:
            if p.get_gid() != "kapi_yay":
                continue
            (cx, cy), rx, ry = p.center, p.width / 2, p.height / 2
            t0, t1 = p.theta1, p.theta2 if p.theta2 > p.theta1 else p.theta2 + 360
            n = max(8, int((t1 - t0) / 3))
            pts = [(cx + rx * math.cos(math.radians(t0 + (t1 - t0) * k / n)), cy + ry * math.sin(math.radians(t0 + (t1 - t0) * k / n)))
                   for k in range(n + 1)]
            g = _yol_cokgeni(ax.transData.transform(pts), None, p.get_linewidth() * sc)
            if g is not None:
                out.append({"ad": "kapi_yay", "poligon": g, "eksen": i})
    return out


def sayfa_disindakiler(kutular: list[dict], fig, pay: float = PAY_PX) -> list[tuple[str, float]]:
    """Mürekkebi figür sınırının dışına taşan yazılar (metin, dışarıda kalan alan px²)."""
    sayfa = _kutu_poligon(0, 0, fig.bbox.width, fig.bbox.height)
    out = []
    for k in kutular:
        dis = k["murekkep"].difference(sayfa)
        if not dis.is_empty and dis.area > pay:
            out.append((k["metin"], round(dis.area, 1)))
    return out


def cakisanlar(kutular: list[dict], pay: float = PAY_PX, anahtar: str = "murekkep") -> list[tuple[str, str, float]]:
    """Aynı eksende örtüşen yazı çiftleri (metin, metin, örtüşme px²). anahtar: 'murekkep' (varsayılan) ya da 'yerlesim'."""
    out = []
    for i in range(len(kutular)):
        for j in range(i + 1, len(kutular)):
            a, b = kutular[i], kutular[j]
            if a["eksen"] != b["eksen"]:
                continue
            o = _gercek(a[anahtar].intersection(b[anahtar]), pay)
            if o > 0:
                out.append((a["metin"], b["metin"], round(o, 1)))
    return out


def cizgi_kapatanlar(kutular: list[dict], cizgiler: list[dict], secici=None, pay: float = PAY_PX) -> list[tuple[str, str, float]]:
    """Ölçü okunu/çentiğini kapatan yazılar (metin, ok adı, örtüşme px²). Varsayılan: bütün yazılar (mürekkep kutusu)."""
    sec = secici or (lambda k: True)
    out = []
    for k in kutular:
        if not sec(k):
            continue
        for c in cizgiler:
            if c["eksen"] != k["eksen"]:
                continue
            o = _gercek(k["murekkep"].intersection(c["poligon"]), pay)
            if o > 0:
                out.append((k["metin"], c["ad"], round(o, 1)))
                break
    return out


def denetle(fig, ad: str = "") -> dict:
    """Tek figür için rapor: {ad, yazi: n, cakisan: mürekkep çakışmaları, yerlesim_cakisan: yalnız yerleşim kutusu örtüşmeleri (bilgi;
    yanlış alarm sayılır), cizgi_kapatan: ölçü okunu kapatan yazılar, yay_kapatan: kapı yayını kesen yazılar, sayfa_disi: sayfadan taşan
    yazılar (BK-09)}."""
    k = metin_kutulari(fig)
    ink = cakisanlar(k)
    yer = [x for x in cakisanlar(k, anahtar="yerlesim") if (x[0], x[1]) not in {(a, b) for a, b, _ in ink}]
    return {"ad": ad, "yazi": len(k), "cakisan": ink, "yerlesim_cakisan": yer, "cizgi_kapatan": cizgi_kapatanlar(k, olcu_cizgileri(fig)),
            "yay_kapatan": cizgi_kapatanlar(k, kapi_yaylari(fig)), "sayfa_disi": sayfa_disindakiler(k, fig)}
