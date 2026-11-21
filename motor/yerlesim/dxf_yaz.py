"""Montaj paftasının (kart modelinin yerleşim planları) düzenlenebilir DXF'i: PDF'i çizen sayfaların kendisinden (D-28 madde 1, tek kod).

`cizim.ciz(..., dxf_yolu=)` her sayfayı PDF'e kaydettikten hemen sonra aynı matplotlib figürünü buraya verir; burada yeni geometri
hesaplanmaz, figürde çizili olan her şekil, çizgi ve yazı DXF varlığına çevrilir. PDF'in baytları değişmez (sayfa PDF'e önce yazılır).

- **Birim cm, gerçek ölçek** ($INSUNITS 5, R2018): planın parçaları modeldeki dünya koordinatıyla (cm) yazılır, sayfanın ötelemesiyle.
  Bir sayfada birden çok çizim alanı varsa (3. sayfa betopan görünüşleri, 7. sayfa zemin ve çatı) her biri kendi gerçek ölçeğinde,
  PDF'teki kutusunun ortasında durur. Başlık, lejant, notlar ve alt satır sayfanın ölçeğiyle (en büyük çizim alanının ölçeği) yerleşir.
- **Sayfalar yan yana**: model alanında soldan sağa, PDF'teki sırayla; her sayfanın çevresinde ince bir sayfa sınırı (`SAYFA_SINIRI`).
- **Katmanlar** `S<n>_<rol>`: rol parçanın renginden (cizim.py'nin `RENK`, `ELEKTRIK_RENK`, `KENAR_RENK` sözlükleri; ör. `S2_MAKAS`,
  `S7_CK-01`), duvarlar `S<n>_DUVAR`, çizim içi yazılar `S<n>_YAZI`, başlık-lejant-not `S<n>_PAFTA`. Renk varlıkta gerçek renk (RGB),
  saydamlık PDF'teki alfa; dolgu HATCH (katı), kenar LWPOLYLINE, daire CIRCLE, yazı MTEXT (DejaVu Sans).
- **K23 gibi**: dosya yazıldıktan sonra yeniden açılır ve denetlenir (audit hatası 0; sayfa sayfa varlık sayısı yazılanla aynı; çizim
  alanlarının kapsamı yazılanla aynı). Geçmezse dosya `.HATALI.dxf` adıyla kalır ve teslim adıyla dosya yoktur.

DXF çıktıdır, kaynak değil: düzeltme koda, kural kitabına ya da İş Emri'ne işlenir, yeniden üretilir (D-11, D-28).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

YAZI_STILI, YAZI_STILI_KALIN = "PORTMAN_DEJAVU", "PORTMAN_DEJAVU_KALIN"
BUYUK_HARF = 0.72               # DejaVu Sans'ın büyük harf yüksekliği / punto (CAD yazı yüksekliği büyük harf yüksekliğidir)
SAYFA_ARASI = 0.08              # sayfalar arasındaki boşluk, sayfa eninin oranı
SAYFA_KATMANI = "SAYFA_SINIRI"
GECERLI_KALINLIK = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211)
EK = 1e-6


def _hex(c) -> str:
    from matplotlib.colors import to_hex
    return to_hex(c, keep_alpha=False).lower()


def roller(*sozlukler) -> dict[str, str]:
    """Renk → rol adı; önce gelen sözlük önceliklidir. İç içe sözlük (omega) ve demet (kaplama) düzleşir; aynı rengi paylaşan kodlar
    birleşir (ör. `EL-01_EL-02`)."""
    out: dict[str, list[str]] = {}
    sira: list[str] = []

    def ekle(ad, deger):
        if isinstance(deger, dict):
            for k, v in deger.items():
                ekle(f"{ad}_{k}" if ad else k, v)
        elif isinstance(deger, (tuple, list)):
            for v in deger:
                ekle(ad, v)
        else:
            h = _hex(deger)
            if h not in out:
                out[h] = []
                sira.append(h)
            if ad not in out[h]:
                out[h].append(ad)

    sonuc: dict[str, str] = {}
    for s in sozlukler:
        out.clear()
        ekle("", s)
        for h, adlar in out.items():
            sonuc.setdefault(h, "_".join(adlar).upper().replace("Ç", "C").replace("Ş", "S").replace("İ", "I").replace("Ğ", "G")
                             .replace("Ü", "U").replace("Ö", "O").replace(" ", "_"))
    return sonuc


def _kalinlik(pt: float) -> int:
    mm100 = pt * 25.4 / 72 * 100
    return min(GECERLI_KALINLIK[1:], key=lambda v: abs(v - mm100)) if pt > 0 else 0


KESIK = "PORTMAN_KESIK"          # matplotlib'in '--' deseni: çizgi 3,7 × kalınlık, boşluk 1,6 × kalınlık (ltscale = kalınlık, birimle)


def _ek(ent, renk, alfa: float, lw_pt: float | None = None, kesik: float | None = None) -> None:
    """`kesik`: kesik çizgide bir puntonun DXF birimindeki boyu (desen kalınlıkla ölçeklenir); düz çizgide None."""
    r, g, b = (int(round(255 * x)) for x in renk[:3])
    ent.rgb = (r, g, b)
    if alfa < 1 - EK:
        ent.transparency = 1 - alfa
    if lw_pt is not None:
        ent.dxf.lineweight = _kalinlik(lw_pt)
    if kesik:
        ent.dxf.linetype = KESIK
        ent.dxf.ltscale = max(lw_pt or 1.0, 0.1) * kesik


def _satir_araligi(t) -> float:
    """matplotlib'in satır aralığı (punto katı; varsayılan 1,2) → MTEXT çarpanı (1,0 = 5/3 × büyük harf ≈ 1,2 punto)."""
    a = t.get_linespacing()
    return float(a) / 1.2 if isinstance(a, (int, float)) else 1.0


class DxfPafta:
    """Sayfa sayfa doldurulur (`sayfa`), sonra yazılır ve denetlenir (`kaydet`)."""

    def __init__(self, kod: str):
        import ezdxf
        from ezdxf import units
        self.kod = kod
        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = units.CM
        self.doc.header["$MEASUREMENT"] = 1
        self.doc.header["$LWDISPLAY"] = 1
        self.doc.styles.add(YAZI_STILI, font="DejaVuSans.ttf")
        self.doc.styles.add(YAZI_STILI_KALIN, font="DejaVuSans-Bold.ttf")
        self.doc.layers.add(SAYFA_KATMANI, color=8, lineweight=13)
        self.doc.linetypes.add(KESIK, pattern=[5.3, 3.7, -1.6], description="matplotlib -- (3,7 / 1,6 × kalınlık)")
        self.msp = self.doc.modelspace()
        self.x = 0.0
        self.sayfalar: list[dict] = []

    # ------------------------------------------------------------------ katman
    def _katman(self, ad: str) -> str:
        if ad not in self.doc.layers:
            self.doc.layers.add(ad, color=7)
        return ad

    # ------------------------------------------------------------------ sayfa
    def sayfa(self, fig, ad: str, renk_rolleri: dict[str, str]) -> dict:
        """Kaydedilmiş bir PDF sayfasının figürünü DXF'e çevirir. Dönen: sayfanın özeti (katman başına varlık sayısı, çizim alanlarının
        kapsamı)."""
        from matplotlib.axes import Axes
        from matplotlib.axis import Axis
        from matplotlib.spines import Spine
        from matplotlib.text import Text
        from matplotlib.patches import Patch, Circle
        from matplotlib.lines import Line2D

        fig.canvas.draw()                                       # yerleşim (eşit en-boy, lejant) son hâlinde
        n = len(self.sayfalar) + 1
        W, H = fig.bbox.width, fig.bbox.height
        alanlar = []
        for ax in fig.axes:
            inv = ax.transData.inverted()
            (x0, y0), (x1, _y1) = inv.transform([[0, 0], [1, 0]])
            k = abs(x1 - x0)                                    # cm / piksel
            if np.isfinite(k) and k > 0:
                alanlar.append((ax, k))
        s = max((k for _, k in alanlar), default=1.0)
        nokta = fig.dpi / 72                                   # bir punto, piksel
        ox, oy = self.x, 0.0

        def sayfa_nok(p):
            p = np.atleast_2d(np.asarray(p, dtype=float))
            return np.column_stack([ox + p[:, 0] * s, oy + p[:, 1] * s])

        oteleme = {}
        for ax, k in alanlar:                                   # çizim alanı kutusunda PDF'teki dayanağıyla (`set_anchor`; N: üst orta)
            a = ax.get_anchor()
            a = a if isinstance(a, tuple) else {"C": (.5, .5), "N": (.5, 1), "S": (.5, 0), "E": (1, .5), "W": (0, .5), "NE": (1, 1),
                                                 "NW": (0, 1), "SE": (1, 0), "SW": (0, 0)}[a]
            b = ax.bbox
            c = np.array([[b.x0 + a[0] * b.width, b.y0 + a[1] * b.height]])
            oteleme[id(ax)] = (sayfa_nok(c)[0] - ax.transData.inverted().transform(c)[0], k)

        ozet = {"ad": ad, "katmanlar": {}, "kapsam": {}}

        def say(katman):
            ozet["katmanlar"][katman] = ozet["katmanlar"].get(katman, 0) + 1

        def donustur(artist):
            """(nokta dönüştürücü, ölçek cm/piksel, veri mi). Yamada yamanın kendi dönüşümü (`get_patch_transform`) hariç: yol önce onunla
            açılır (`yama`)."""
            from matplotlib.artist import Artist
            ax = getattr(artist, "axes", None)
            tr = Artist.get_transform(artist) if isinstance(artist, Patch) else artist.get_transform()
            if ax is not None and id(ax) in oteleme and tr.contains_branch(ax.transData):
                d, k = oteleme[id(ax)]
                ic = tr - ax.transData
                return (lambda p: ic.transform(np.atleast_2d(np.asarray(p, dtype=float))) + d), k, True
            return (lambda p: sayfa_nok(tr.transform(np.atleast_2d(np.asarray(p, dtype=float))))), s, False

        def rol(renk, veri: bool, varsayilan: str) -> str:
            h = _hex(renk)
            if h in ("#c9c9c9", "#8a8a8a"):
                return f"S{n}_DUVAR"
            if not veri:
                return f"S{n}_PAFTA"
            return f"S{n}_{renk_rolleri.get(h, varsayilan)}"

        def kapsam(katman, pts):
            if not katman.endswith(("_PAFTA",)) and len(pts):
                k = ozet["kapsam"].setdefault("cizim", [math.inf, math.inf, -math.inf, -math.inf])
                k[0] = min(k[0], float(pts[:, 0].min())); k[1] = min(k[1], float(pts[:, 1].min()))
                k[2] = max(k[2], float(pts[:, 0].max())); k[3] = max(k[3], float(pts[:, 1].max()))

        def yama(p, ozel=None):
            """`ozel`: (dönüştürücü, ölçek, veri mi) yazı kutusu için, yazının kendi eşlemesiyle (kutu yazıyla birlikte durur)."""
            if not p.get_visible():
                return
            f, k, veri = ozel or donustur(p)
            fc, ec = p.get_facecolor(), p.get_edgecolor()
            dolu = p.get_fill() and fc[3] > EK
            kenar = p.get_linewidth() > 0 and ec[3] > EK
            if not (dolu or kenar or p.get_hatch()):
                return
            beyaz = dolu and _hex(fc) == "#ffffff" and kenar
            katman = self._katman(rol(ec if (beyaz or not dolu) else fc, veri, "SEKIL"))
            if isinstance(p, Circle):
                m = f([p.center])[0]
                r = float(np.hypot(*(f([(p.center[0] + p.radius, p.center[1])])[0] - m)))
                if dolu:
                    h = self.msp.add_hatch(dxfattribs={"layer": katman})
                    h.paths.add_edge_path().add_arc(tuple(m), r, 0, 360)
                    _ek(h, fc, fc[3]); say(katman)
                if kenar:
                    c = self.msp.add_circle(tuple(m), r, dxfattribs={"layer": katman})
                    _ek(c, ec, ec[3], p.get_linewidth(), None if p.get_linestyle() in ("solid", "-") else nokta * k); say(katman)
                kapsam(katman, np.array([[m[0] - r, m[1] - r], [m[0] + r, m[1] + r]]))
                return
            yol = p.get_path()
            tr_p = p.get_patch_transform()
            cokgenler = [f(tr_p.transform(c)) for c in yol.to_polygons(closed_only=False) if len(c) >= 2]
            cokgenler = [c[:-1] if len(c) > 2 and np.allclose(c[0], c[-1]) else c for c in cokgenler]
            for c in cokgenler:
                if len(c) < 2:
                    continue
                kapsam(katman, c)
                if dolu and len(c) >= 3:
                    h = self.msp.add_hatch(dxfattribs={"layer": katman})
                    h.paths.add_polyline_path([tuple(q) for q in c], is_closed=True)
                    _ek(h, fc, fc[3]); say(katman)
                if p.get_hatch() and len(c) >= 3:
                    h = self.msp.add_hatch(dxfattribs={"layer": katman})
                    h.set_pattern_fill("ANSI31", scale=max(0.2, 8 * k / 2.54 * 0.4))
                    h.paths.add_polyline_path([tuple(q) for q in c], is_closed=True)
                    _ek(h, ec, ec[3]); say(katman)
                if kenar:
                    pl = self.msp.add_lwpolyline([tuple(q) for q in c], close=len(c) >= 3, dxfattribs={"layer": katman})
                    _ek(pl, ec, ec[3], p.get_linewidth(), None if p.get_linestyle() in ("solid", "-") else nokta * k); say(katman)

        def cizgi(l):
            if not l.get_visible() or l.get_linewidth() <= 0 or l.get_linestyle() in ("None", "none", " ", ""):
                return
            from matplotlib.colors import to_rgba
            f, k, veri = donustur(l)
            renk = to_rgba(l.get_color(), l.get_alpha())
            pts = f(l.get_xydata())
            pts = pts[np.all(np.isfinite(pts), axis=1)]
            if len(pts) < 2:
                return
            katman = self._katman(rol(renk, veri, "CIZGI"))
            pl = self.msp.add_lwpolyline([tuple(q) for q in pts], dxfattribs={"layer": katman})
            _ek(pl, renk, renk[3], l.get_linewidth(), None if l.get_linestyle() in ("-", "solid") else nokta * k)
            say(katman); kapsam(katman, pts)

        def yazi(t):
            metin = t.get_text()
            if not t.get_visible() or not metin.strip():
                return
            from matplotlib.artist import Artist
            from matplotlib.colors import to_rgba
            f, k, veri = donustur(t)
            m = f([t.get_unitless_position()])[0]
            bp = t.get_bbox_patch()
            if bp is not None:                                  # kutu ekranda yazının çapasına göre; DXF'te yazının ölçeğiyle aynı yere
                capa = t.get_transform().transform(np.atleast_2d(t.get_unitless_position()))[0]
                btr = Artist.get_transform(bp)
                yama(bp, (lambda P: m + (btr.transform(np.atleast_2d(np.asarray(P, dtype=float))) - capa) * k, k, veri))
            renk = to_rgba(t.get_color(), t.get_alpha())
            boy = t.get_fontsize() * fig.dpi / 72 * k * BUYUK_HARF
            rot = t.get_rotation() % 360
            ha, va = t.get_horizontalalignment(), t.get_verticalalignment()
            yv = {"top": "TOP", "center": "MIDDLE", "center_baseline": "MIDDLE", "bottom": "BOTTOM", "baseline": "BOTTOM"}[va]
            yh = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}[ha]
            if abs(rot - 90) < 1e-6:                            # 90°: ekranın yatayı yazının dikeyi (bkz. modül notu)
                yv, yh = ({"left": "TOP", "center": "MIDDLE", "right": "BOTTOM"}[ha],
                          {"bottom": "LEFT", "baseline": "LEFT", "center": "CENTER", "center_baseline": "CENTER", "top": "RIGHT"}[va])
            ek = {("TOP", "LEFT"): 1, ("TOP", "CENTER"): 2, ("TOP", "RIGHT"): 3, ("MIDDLE", "LEFT"): 4, ("MIDDLE", "CENTER"): 5,
                  ("MIDDLE", "RIGHT"): 6, ("BOTTOM", "LEFT"): 7, ("BOTTOM", "CENTER"): 8, ("BOTTOM", "RIGHT"): 9}[(yv, yh)]
            kalin = str(t.get_fontweight()) in ("bold", "heavy", "700", "800", "900") or (isinstance(t.get_fontweight(), (int, float))
                                                                                          and t.get_fontweight() >= 600)
            katman = self._katman(f"S{n}_YAZI" if veri else f"S{n}_PAFTA")
            satirlar = [("\u00a0" * (len(x) - len(x.lstrip(" "))) + x.lstrip(" ")) for x in metin.split("\n")]   # baştaki boşluk kalsın
            mt = self.msp.add_mtext("\\P".join(satirlar), dxfattribs={
                "layer": katman, "insert": (float(m[0]), float(m[1])), "char_height": boy, "attachment_point": ek,
                "rotation": float(rot), "style": YAZI_STILI_KALIN if kalin else YAZI_STILI,
                "line_spacing_factor": _satir_araligi(t)})
            _ek(mt, renk, renk[3])
            say(katman)

        def cocuklar(a):
            """matplotlib'in çizim sırası: figürde ve çizim alanında zorder'a göre (eşitte ekleniş sırası); lejantta önce çerçeve."""
            from matplotlib.legend import Legend
            if isinstance(a, Legend):
                return [a.get_frame(), *[c for c in a.get_children() if c is not a.get_frame()]]
            cs = a.get_children()
            return sorted(cs, key=lambda c: c.get_zorder()) if isinstance(a, (Axes, type(fig))) else cs

        def gez(a):
            for c in cocuklar(a):
                if c is fig.patch or (isinstance(a, Axes) and c is a.patch):
                    continue
                if isinstance(c, (Spine, Axis)) and not getattr(getattr(c, "axes", None), "axison", True):
                    continue
                if not c.get_visible():
                    continue
                if isinstance(c, Text):
                    yazi(c)
                elif isinstance(c, Patch):
                    yama(c)
                elif isinstance(c, Line2D):
                    cizgi(c)
                gez(c)

        gez(fig)
        sinir = [(ox, oy), (ox + W * s, oy), (ox + W * s, oy + H * s), (ox, oy + H * s)]
        self.msp.add_lwpolyline(sinir, close=True, dxfattribs={"layer": SAYFA_KATMANI})
        ozet["katmanlar"][SAYFA_KATMANI] = 1
        ozet["sayfa_cm"] = [round(ox, 3), round(oy, 3), round(ox + W * s, 3), round(oy + H * s, 3)]
        ozet["olcek_cm_piksel"] = s
        self.sayfalar.append(ozet)
        self.x = ox + W * s * (1 + SAYFA_ARASI)
        return ozet

    # ------------------------------------------------------------------ kaydet ve denetle
    def kaydet(self, yol: Path) -> dict:
        """Yazar, yeniden açar, denetler. Geçerse `yol`, geçmezse `<ad>.HATALI.dxf` (teslim adıyla dosya kalmaz)."""
        import ezdxf
        from ezdxf import bbox as ebbox
        yol = Path(yol)
        yol.parent.mkdir(parents=True, exist_ok=True)
        hatali = yol.with_suffix(".HATALI.dxf")
        for eski in (yol, hatali):                              # önceki koşunun dosyası teslim adıyla kalmasın
            eski.unlink(missing_ok=True)
        self.doc.saveas(hatali)                                 # denetimden geçene kadar HATALI adıyla
        try:
            d2 = ezdxf.readfile(hatali)
            a = d2.audit()
        except Exception as e:                                  # noqa: BLE001 — okunamayan dosya teslim edilmez
            return {"dosya": None, "hatali": hatali.name, "hatalar": [f"yeniden açılamadı ({type(e).__name__}: {str(e)[:160]})"],
                    "sayfalar": self.sayfalar}
        sayim: dict[str, int] = {}
        for e in d2.modelspace():
            sayim[e.dxf.layer] = sayim.get(e.dxf.layer, 0) + 1
        beklenen: dict[str, int] = {}
        for sf in self.sayfalar:
            for kt, nn in sf["katmanlar"].items():
                beklenen[kt] = beklenen.get(kt, 0) + nn
        hatalar = []
        if a.errors:
            hatalar.append(f"denetim hatası {len(a.errors)}")
        if sayim != beklenen:
            fark = {k: (beklenen.get(k, 0), sayim.get(k, 0)) for k in set(sayim) | set(beklenen) if beklenen.get(k, 0) != sayim.get(k, 0)}
            hatalar.append(f"katman sayısı farklı (yazılan, okunan): {fark}")
        for i, sf in enumerate(self.sayfalar, 1):
            k = sf["kapsam"].get("cizim")
            if not k:
                continue
            varl = [e for e in d2.modelspace() if e.dxf.layer.startswith(f"S{i}_") and not e.dxf.layer.endswith("_PAFTA")
                    and e.dxftype() in ("LWPOLYLINE", "CIRCLE", "HATCH")]
            if varl:
                b = ebbox.extents(varl, fast=True)
                okunan = [b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y]
                if any(abs(x - y) > 0.01 for x, y in zip(okunan, k)):
                    hatalar.append(f"sayfa {i} kapsamı farklı")
                sf["kapsam_okunan"] = [round(x, 2) for x in okunan]
            for e in (e for e in varl if e.dxftype() != "HATCH"):
                pts = list(e.get_points("xy")) if e.dxftype() == "LWPOLYLINE" else [tuple(e.dxf.center)[:2]]
                if not all(math.isfinite(c) for q in pts for c in q):
                    hatalar.append(f"sayfa {i}: sonlu olmayan koordinat")
                    break
        if hatalar:
            return {"dosya": None, "hatali": hatali.name, "hatalar": hatalar, "sayfalar": self.sayfalar}
        hatali.replace(yol)
        return {"dosya": yol.name, "denetim_hatasi": 0, "katmanlar": dict(sorted(sayim.items())), "sayfa": len(self.sayfalar),
                "sayfalar": [{"ad": sf["ad"], "sayfa_cm": sf["sayfa_cm"]} for sf in self.sayfalar]}
