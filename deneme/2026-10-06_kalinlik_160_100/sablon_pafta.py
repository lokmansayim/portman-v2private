"""6 Ekim 2026 denemesi: İş Emri → plan paftası, "Örnek Şablon" düzeninde (A4 yatay).

    python deneme/2026-10-06_kalinlik_160_100/sablon_pafta.py [is_emri.json]

Lokman, 6 Ekim 19:46: "bundan sonra planda bunun aynısını yapacağız". Şablon bir AutoCAD çıktısıdır (A4 yatay, 842 × 595 pt);
çerçeveler, tablolar, yazı boyları ve renkler o dosyadan ölçüldü (`docs/sartname/plan_paftasi_sablonu.md`). Şablonun kendisi
kişi adı taşıdığı için depoda değildir.

Paftada: plan (pano ekleri, pencere ve kapı etiketleri, mahal adı ve m², mavi ölçü zincirleri), altında ön görünüş, solunda
90° döndürülmüş sol yan görünüş; sağda BİNA ÖZELLİKLERİ ve ÖZEL İSTEKLER; altta antet. Geometri Motor'un deneme kopyasındaki
plandan gelir; burada yalnız çizilir. Yazı tipi: Comic Relief (şablondaki Comic Sans MS'in açık lisanslı eşi) ve Liberation Sans
(Arial'in eşi). Canlı Motor'a dokunmaz. Çıktı: `cikti/<iş emri no>/plan/`.
"""
from __future__ import annotations
import json, math, os, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.textpath import TextPath
from matplotlib.patches import Arc, Circle, Ellipse, FancyBboxPatch, Polygon as MplPolygon, Rectangle

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIKTI = BURASI / "cikti"
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(BURASI))
os.environ.setdefault("PORTMAN_REF_DIR", str(KOK / "kanal"))

EN, BOY = 842.0, 595.0                      # A4 yatay, pt (şablonla aynı)
# ---- şablondan ölçülen çerçeveler (pt; y yukarıdan aşağı) ----
DIS = (10.3, 2.4, 835.8, 590.8)
ANA = (22.9, 15.0, 686.8, 522.3)
OZELLIK = (691.9, 15.0, 824.9, 249.9); OZELLIK_BASLIK_ALT = 29.7; OZELLIK_BOLME = 761.4
ISTEK = (691.7, 255.6, 824.6, 521.0)
ANTET_SOL = (22.9, 528.6, 277.9, 578.3)
ANTET_ORTA = (282.4, 528.6, 686.8, 578.3); ANTET_ORTA_SATIR = (540.6, 553.2, 567.5); ANTET_ORTA_BOLME = 423.8
ANTET_SAG = (691.7, 527.2, 824.6, 578.3); ANTET_SAG_SATIR = (539.7, 552.2, 564.4); ANTET_SAG_BOLME = 760.1
KOSE_R = 4.2
# ---- şablondaki renkler ----
MAVI, GRI, GRI_YAZI, TURUNCU, KIRMIZI, KOYU_KIRMIZI, KAHVE = "#6EC2DD", "#636366", "#939598", "#DDA56E", "#FF0000", "#991B1E", "#4F290F"
CATI_RENGI = {"kırmızı": "#991B1E", "antrasit": "#4A4F57", "gri": "#7D8187", "yeşil": "#2F6B45", "mavi": "#2F5E8A", "kahverengi": "#5B3A21"}
OZELLIK_SIRASI = ["Bina Yüksekliği", "Dış Duvarlar", "İç Duvarlar", "Panel Türü", "Çatı Şekli", "Çatı Eğimi", "Çatı Kaplaması", "Çatı Kaplama Rengi",
                  "Dış Kapı", "İç Kapılar", "Pencereler", "Vasistaslar", "Dış Boya Rengi", "İç Boya Rengi", "Köşe ve Söveler"]
PENCERE_ESIK = {"120x120": 80.0, "120x180": 20.0, "60x40": 160.0}
KAPI_UST = 200.0; CATI_KALINLIK = 14.0; SUBASMAN = 15.0

for _f in (BURASI / "font" / "ComicRelief-Regular.ttf", BURASI / "font" / "ComicRelief-Bold.ttf"):
    fm.fontManager.addfont(str(_f))
COMIC = fm.FontProperties(fname=str(BURASI / "font" / "ComicRelief-Regular.ttf"))
_arial = next((f for f in ("Arial", "Liberation Sans", "Arimo", "DejaVu Sans") if any(x.name == f for x in fm.fontManager.ttflist)), "DejaVu Sans")
ARIAL = fm.FontProperties(family=_arial)


def tr(v: float, n: int = 0) -> str:
    return f"{v:.{n}f}".replace(".", ",") if n else f"{int(round(v))}"


def yazi_eni(metin: str, pt: float, font=None) -> float:
    """Yazının eni (pt)."""
    return TextPath((0, 0), metin, size=pt, prop=font or ARIAL).get_extents().width


def tam_bol(parcalar: list[float]) -> list[int]:
    """Ölçü zincirini tam sayıya yuvarlar; toplam, genel ölçünün yuvarlağıyla aynı kalır (en büyük kalan yöntemi)."""
    hedef = int(round(sum(parcalar))); taban = [math.floor(p) for p in parcalar]
    for i in sorted(range(len(parcalar)), key=lambda i: parcalar[i] - taban[i], reverse=True)[:hedef - sum(taban)]:
        taban[i] += 1
    return taban


class Sayfa:
    def __init__(self):
        self.fig = plt.figure(figsize=(EN / 72, BOY / 72))
        self.ax = self.fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, EN); self.ax.set_ylim(0, BOY); self.ax.axis("off")

    @staticmethod
    def y(yd):            # şablon koordinatı (aşağı) → çizim koordinatı (yukarı)
        return BOY - yd

    def cizgi(self, x0, y0, x1, y1, renk="black", lw=0.72, ls="-", z=3):
        self.ax.plot([x0, x1], [self.y(y0), self.y(y1)], color=renk, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")

    def kutu(self, x0, y0, x1, y1, fc="none", ec="black", lw=0.72, z=2, ls="-", hatch=None):
        self.ax.add_patch(Rectangle((x0, self.y(y1)), x1 - x0, y1 - y0, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z, linestyle=ls, hatch=hatch))

    def yuvarlak_kutu(self, k, lw=0.72):
        x0, y0, x1, y1 = k
        self.ax.add_patch(FancyBboxPatch((x0 + KOSE_R, self.y(y1) + KOSE_R), x1 - x0 - 2 * KOSE_R, y1 - y0 - 2 * KOSE_R,
                                         boxstyle=f"round,pad={KOSE_R},rounding_size={KOSE_R}", facecolor="none", edgecolor="black", linewidth=lw, zorder=4))

    def cokgen(self, pts, fc, ec="black", lw=0.72, z=2):
        self.ax.add_patch(MplPolygon([(x, self.y(y)) for x, y in pts], closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z, joinstyle="miter"))

    def yazi(self, x, yd, s, pt=7.3, font=None, renk="black", ha="left", va="center", rot=0, z=6, **kw):
        return self.ax.text(x, self.y(yd), s, fontsize=pt, fontproperties=font or COMIC, color=renk, ha=ha, va=va, rotation=rot, zorder=z, **kw)

    def olcu(self, x0, y0, x1, y1, metin, taraf):
        """Şablondaki ölçü: mavi çizgi, uçlarda kalın eğik çentik, siyah Arial yazı. taraf: yazının çizgiye göre yeri (ust | alt | sol | sag)."""
        self.cizgi(x0 - (4 if y0 == y1 else 0), y0 - (4 if x0 == x1 else 0), x1 + (4 if y0 == y1 else 0), y1 + (4 if x0 == x1 else 0), MAVI, 0.72, z=5)
        for (x, y_) in ((x0, y0), (x1, y1)):
            self.cizgi(x - 4.2, y_ + 4.2, x + 4.2, y_ - 4.2, MAVI, 1.56, z=5)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if y0 == y1:
            self.yazi(mx, my + (-7.2 if taraf == "ust" else 7.6), metin, 10.7, ARIAL, ha="center")
        else:
            self.yazi(mx + (-7.4 if taraf == "sol" else 7.4), my, metin, 10.7, ARIAL, ha="center", rot=90)


# ----------------------------------------------------------------------------- tablolar ve antet
def cerceveler(sf: Sayfa, ie: dict, plan, G, cati: dict):
    x0, y0, x1, y1 = DIS
    sf.kutu(x0, y0, x1, y1, lw=1.3, z=4)
    sf.yuvarlak_kutu(ANA)
    # BİNA ÖZELLİKLERİ
    sf.yuvarlak_kutu(OZELLIK)
    sf.yazi((OZELLIK[0] + OZELLIK[2]) / 2, 23.0, "BİNA ÖZELLİKLERİ", 10.9, renk=KOYU_KIRMIZI, ha="center")
    p = ie.get("pafta", {}); oz = dict(p.get("ozellikler", {}))
    H0 = float(ie["yapi"].get("duvar_yuksekligi_cm", 250))
    oz.setdefault("Bina Yüksekliği", f"{H0 * 10:g}mm"); oz.setdefault("Dış Duvarlar", f"{G.T_DIS * 10:g}mm"); oz.setdefault("İç Duvarlar", f"{G.T_IC * 10:g}mm")
    oz.setdefault("Çatı Şekli", {"besik": "Beşik", "kirma": "Kırma", "cumbali": "Cumbalı", "teras": "Teras"}.get(ie.get("cati", {}).get("tip", "besik"), "..."))
    oz.setdefault("Çatı Eğimi", f"%{cati['egim'] * 100:g}")
    adim = (OZELLIK[3] - OZELLIK_BASLIK_ALT) / len(OZELLIK_SIRASI)
    for i, ad in enumerate(OZELLIK_SIRASI):
        yt = OZELLIK_BASLIK_ALT + i * adim
        sf.cizgi(OZELLIK[0], yt, OZELLIK[2], yt)
        v = oz.get(ad, "...")
        sf.yazi(695.0, yt + adim / 2 + 0.6, ad, 7.3)
        sf.yazi(765.0, yt + adim / 2 + (0.6 if v != "..." else -1.2), v, 7.3 if v != "..." else 12.0)
    sf.cizgi(OZELLIK_BOLME, OZELLIK_BASLIK_ALT, OZELLIK_BOLME, OZELLIK[3])
    # ÖZEL İSTEKLER
    sf.yuvarlak_kutu(ISTEK)
    sf.yazi(696.0, 272.0, "ÖZEL İSTEKLER;", 7.6, renk=KOYU_KIRMIZI)
    yy = 282.0
    for i, m in enumerate(p.get("ozel_istekler", []), 1):
        satirlar = _sar(m, 29)
        for j, s_ in enumerate(satirlar):
            sf.yazi(699.0 if j == 0 else 711.0, yy, (f"{i}. " if j == 0 else "") + s_, 7.6, renk=KOYU_KIRMIZI)
            yy += 9.2
        yy += 2.0
    # antet
    sf.yuvarlak_kutu(ANTET_SOL)                            # şablonda boş (firma alanı)
    sf.yuvarlak_kutu(ANTET_ORTA)
    for ys in ANTET_ORTA_SATIR:
        sf.cizgi(ANTET_ORTA[0], ys, ANTET_ORTA[2], ys)
    sf.cizgi(ANTET_ORTA_BOLME, ANTET_ORTA[1], ANTET_ORTA_BOLME, ANTET_ORTA[3])
    sat = [ANTET_ORTA[1], *ANTET_ORTA_SATIR, ANTET_ORTA[3]]
    brut = plan.W * plan.H / 1e4
    orta = [("PROJE KODU", f"{ie.get('is_emri_no', '')} r{int(ie.get('revizyon', 1)):02d}"), ("İLGİLİ KİŞİ-TELEFON", p.get("ilgili_kisi", "...")),
            ("SEVK ADRESİ", p.get("sevk_adresi", "...")), ("PROJE ADI & M²", p.get("proje_adi") or f"{brut:.0f} M² PREFABRİK KONUT")]
    for (ad, v), ya, yb in zip(orta, sat, sat[1:]):
        sf.yazi(287.0, (ya + yb) / 2 + 0.4, ad, 7.3)
        sf.yazi(431.0, (ya + yb) / 2 + (0.4 if v != "..." else -1.4), v, 7.3 if v != "..." else 12.0)
    sf.yuvarlak_kutu(ANTET_SAG)
    for ys in ANTET_SAG_SATIR:
        sf.cizgi(ANTET_SAG[0], ys, ANTET_SAG[2], ys)
    sf.cizgi(ANTET_SAG_BOLME, ANTET_SAG[1], ANTET_SAG_BOLME, ANTET_SAG[3])
    sat = [ANTET_SAG[1], *ANTET_SAG_SATIR, ANTET_SAG[3]]
    for (ad, v), ya, yb in zip([("TARİH", p.get("tarih", "...")), ("ÇİZEN", p.get("cizen", "...")), ("KONTROL", p.get("kontrol", "...")), ("ONAY", p.get("onay", "..."))], sat, sat[1:]):
        sf.yazi(698.0, (ya + yb) / 2 + 0.4, ad, 7.3)
        sf.yazi(765.0, (ya + yb) / 2 + (0.4 if v != "..." else -1.4), v, 7.3 if v != "..." else 12.0)


def _sar(metin: str, genislik: int) -> list[str]:
    satir, out = "", []
    for k in metin.split():
        if satir and len(satir) + 1 + len(k) > genislik:
            out.append(satir); satir = k
        else:
            satir = (satir + " " + k).strip()
    return out + ([satir] if satir else [])


# ----------------------------------------------------------------------------- plan
def plan_ciz(sf: Sayfa, plan, G, ie: dict, px0: float, py0: float, s: float):
    """px0, py0: planın sol-ön dış köşesinin sayfadaki yeri (pt; y aşağı). s: pt/cm."""
    X = lambda x: px0 + s * x
    Y = lambda y: py0 - s * y
    W, H = plan.W, plan.H
    # duvarlar: her pano parçası siyah çerçeve (pano ekleri kendiliğinden görünür)
    for d in plan.duvarlar:
        for p in d.panolar:
            for (x0, y0, x1, y1) in p.rects():
                sf.kutu(X(x0), Y(y1), X(x1), Y(y0), fc="white", ec="black", lw=0.72, z=3)
    for k in plan.koseler:
        x0, y0, x1, y1 = k.rect
        sf.kutu(X(x0), Y(y1), X(x1), Y(y0), fc="white", ec=MAVI, lw=1.1, z=4)
    # açıklıklar
    for d in plan.duvarlar:
        for p in d.panolar:
            ac = p.acilim
            if ac is None:
                continue
            x0, y0, x1, y1 = p.gap()
            if ac.tur == "pencere":
                sf.kutu(X(x0), Y(y1), X(x1), Y(y0), fc="white", ec=MAVI, lw=1.0, z=4)
                en, yuk = ac.olcu.split("x")
                etiket = ("V." if ac.olcu == "60x40" else "") + ac.olcu
                if d.yon == "x":                      # yatay duvar: cam çizgileri yatay, etiket dışarıda
                    ym = (y0 + y1) / 2; n = 2 if int(en) >= 100 else 1; w = (x1 - x0) / n
                    for i in range(n):
                        sf.kutu(X(x0 + i * w) + 1.0, Y(ym) - 1.0, X(x0 + (i + 1) * w) - 1.0, Y(ym) + 1.0, fc="white", ec=TURUNCU, lw=0.72, z=5)
                    dis = ac.disari_normal == "-y"
                    sf.yazi(X((x0 + x1) / 2), Y(y0) + 5.0 if dis else Y(y1) - 5.0, etiket, 5.0, ha="center")
                else:
                    xm = (x0 + x1) / 2; n = 2 if int(en) >= 100 else 1; w = (y1 - y0) / n
                    for i in range(n):
                        sf.kutu(X(xm) - 1.0, Y(y0 + (i + 1) * w) + 1.0, X(xm) + 1.0, Y(y0 + i * w) - 1.0, fc="white", ec=TURUNCU, lw=0.72, z=5)
                    dis = ac.disari_normal == "-x"
                    sf.yazi(X(x0) - 5.0 if dis else X(x1) + 5.0, Y((y0 + y1) / 2), etiket, 5.0, ha="center", rot=90)
            elif ac.tur in ("ic_kapi", "dis_kapi"):
                n = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[ac.icine_normal]       # kapının açıldığı yön
                sag = (n[1], -n[0])                                                                    # içeri girene göre sağ
                yon = sag if (ac.mentese or "sag") == "sag" else (-sag[0], -sag[1])
                w = ac.genislik
                if d.yon == "x":
                    cy = y1 if n[1] > 0 else y0                    # menteşe, kapının açıldığı odanın yüzünde
                    hx = x1 if yon[0] > 0 else x0; ox_ = x0 if yon[0] > 0 else x1
                    mente, uc, karsi = (hx, cy), (hx, cy + n[1] * w), (ox_, cy)
                else:
                    cx = x1 if n[0] > 0 else x0
                    hy = y1 if yon[1] > 0 else y0; oy_ = y0 if yon[1] > 0 else y1
                    mente, uc, karsi = (cx, hy), (cx + n[0] * w, hy), (cx, oy_)
                sf.cizgi(X(mente[0]), Y(mente[1]), X(uc[0]), Y(uc[1]), MAVI, 1.4, z=5)                 # kanat
                a0 = math.degrees(math.atan2(-(uc[1] - mente[1]) * -1, uc[0] - mente[0]))
                a1 = math.degrees(math.atan2(-(karsi[1] - mente[1]) * -1, karsi[0] - mente[0]))
                t0, t1 = sorted((a0 % 360, a1 % 360))
                if t1 - t0 > 180:
                    t0, t1 = t1, t0 + 360
                sf.ax.add_patch(Arc((X(mente[0]), sf.y(Y(mente[1]))), 2 * w * s, 2 * w * s, theta1=t0, theta2=t1, color="black", lw=0.72, ls=(0, (4, 3)), zorder=5))
                if d.yon == "x":                                                                       # kasa: açıklığın iki ucunda mavi çentik
                    for jx in (x0, x1):
                        sf.cizgi(X(jx), Y(y0), X(jx), Y(y1), MAVI, 1.4, z=5)
                else:
                    for jy in (y0, y1):
                        sf.cizgi(X(x0), Y(jy), X(x1), Y(jy), MAVI, 1.4, z=5)
                ex, ey = (mente[0] + uc[0] + karsi[0]) / 3, (mente[1] + uc[1] + karsi[1]) / 3
                sf.yazi(X(ex), Y(ey), tr(w), 3.6, renk=GRI_YAZI, ha="center")
                if ac.tur == "dis_kapi":
                    sf.yazi(X(ex), Y(ey) + 4.4, "ÇELİK", 3.3, renk=GRI_YAZI, ha="center")
    # tefriş (şematik, turuncu)
    for t in ie.get("tefris", []):
        tefris_ciz(sf, t, X, Y, s)
    # mahal adları ve m²
    adlar = ie.get("pafta", {}).get("mahal_adi", {}); yerler = ie.get("pafta", {}).get("etiket_yeri_cm", {}); etiket = {}
    for ad, m in plan.mahaller.items():
        r_big = max(m.rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
        cx = (G.X(r_big[0]) + G.X(r_big[2])) / 2; cy = (G.Y(r_big[1]) + G.Y(r_big[3])) / 2
        if ad in yerler:                               # tefrişe ve kapı yayına değmeyen yer (cm), İş Emri'nden
            cx, cy = yerler[ad]
        metin = adlar.get(ad, ad)
        ic_en = (G.X(r_big[2]) - G.X(r_big[0]) - G.T_IC) * s - 7.0
        pt = min(8.4, 8.4 * ic_en / max(yazi_eni(metin, 8.4), 1e-6))
        sf.yazi(X(cx), Y(cy) - 4.6 * pt / 8.4, metin, pt, ARIAL, renk=GRI_YAZI, ha="center")
        sf.yazi(X(cx), Y(cy) + 5.4 * pt / 8.4, f"{m.alan_m2:.0f} m²", pt + 0.2, ARIAL, renk=GRI_YAZI, ha="center")
        etiket[ad] = round(pt, 2)
    # açık mahal (veranda) kenarı: kırmızı kesik çizgi
    for (x0, y0, x1, y1) in plan.acik_kenarlar:
        sf.cizgi(X(x0), Y(y0), X(x1), Y(y1), KIRMIZI, 0.9, ls=(0, (4, 3)), z=4)

    # ölçü zincirleri: genel ölçü dışta, iç duvar akslarının cepheye değdiği yerler içte
    def zincir(yon: str, hat_ucu: str) -> list[float]:
        """İç duvarların o cepheye değdiği akslar (cm), dış yüzden dış yüze."""
        noktalar = {0.0, W if yon == "x" else H}
        hedef = {"on": G.Y(0), "arka": G.Y(plan.ny), "sol": G.X(0), "sag": G.X(plan.nx)}[hat_ucu]
        for d in plan.duvarlar:
            if d.tur != "ic":
                continue
            if yon == "x" and d.yon == "y" and (abs(d.a0 - hedef) < 1e-6 or abs(d.a1 - hedef) < 1e-6):
                noktalar.add(d.c)
            if yon == "y" and d.yon == "x" and (abs(d.a0 - hedef) < 1e-6 or abs(d.a1 - hedef) < 1e-6):
                noktalar.add(d.c)
        return sorted(noktalar)

    ic_, dis_ = 16.0, 32.0                                 # şablondaki aralıklar (pt)
    ek = {"arka": 0.0, "sol": 0.0, "on": 8.0, "sag": 8.0}  # yazı duvarla çizgi arasında kalıyorsa pencere etiketine yer açılır
    kayit = {}
    for ad, yon in (("arka", "x"), ("on", "x"), ("sol", "y"), ("sag", "y")):
        nk = zincir(yon, ad); parca = tam_bol([b - a for a, b in zip(nk, nk[1:])]); kayit[ad] = parca
        if yon == "x":
            yy = Y(H) - ic_ if ad == "arka" else Y(0) + ic_ + ek[ad]
            yg = Y(H) - dis_ if ad == "arka" else Y(0) + dis_ + ek[ad]
            if len(nk) > 2:
                for (a, b), v in zip(zip(nk, nk[1:]), parca):
                    sf.olcu(X(a), yy, X(b), yy, str(v), "ust")
            else:
                yg = yy
            sf.olcu(X(0), yg, X(W), yg, tr(W), "ust" if ad == "arka" else "ust")
        else:
            xx = X(0) - ic_ if ad == "sol" else X(W) + ic_ + ek[ad]
            xg = X(0) - dis_ if ad == "sol" else X(W) + dis_ + ek[ad]
            if len(nk) > 2:
                for (a, b), v in zip(zip(nk, nk[1:]), parca):
                    sf.olcu(xx, Y(b), xx, Y(a), str(v), "sol")
            else:
                xg = xx
            sf.olcu(xg, Y(H), xg, Y(0), tr(H), "sol")
    return kayit, etiket


def tefris_ciz(sf: Sayfa, t: dict, X, Y, s: float):
    x0, y0, x1, y1 = t["rect"]; tur = t["tur"]
    a, b, c, d = X(x0), Y(y1), X(x1), Y(y0)            # sayfada sol, üst, sağ, alt
    k = dict(fc="white", ec=TURUNCU, lw=0.72, z=3)
    if tur == "tezgah":
        sf.kutu(a, b, c, d, **k)
    elif tur == "eviye":
        sf.kutu(a, b, c, d, **k); w = (c - a)
        sf.kutu(a + 1.2, b + 1.2, a + w * 0.5, d - 1.2, **k)
        for i in range(5):
            xx = a + w * 0.58 + i * w * 0.08
            sf.cizgi(xx, b + 1.8, xx, d - 1.8, TURUNCU, 0.5, z=4)
    elif tur == "ocak":
        sf.kutu(a, b, c, d, **k)
        for fx in (0.28, 0.72):
            for fy in (0.3, 0.72):
                sf.ax.add_patch(Circle((a + (c - a) * fx, sf.y(b + (d - b) * fy)), (c - a) * 0.13, facecolor="white", edgecolor=TURUNCU, linewidth=0.6, zorder=4))
    elif tur == "klozet":                               # rezervuar duvarda (sağ), oturak içeri doğru
        rez = (c - a) * 0.28
        sf.kutu(c - rez, b, c, d, **k)
        sf.ax.add_patch(Ellipse(((a + c - rez) / 2, sf.y((b + d) / 2)), (c - a - rez), (d - b) * 0.82, facecolor="white", edgecolor=TURUNCU, linewidth=0.72, zorder=4))
    elif tur == "lavabo":
        sf.kutu(a, b, c, d, **k)
        sf.ax.add_patch(Ellipse(((a + c) / 2, sf.y((b + d) / 2)), (c - a) * 0.66, (d - b) * 0.7, facecolor="white", edgecolor=TURUNCU, linewidth=0.6, zorder=4))
    elif tur == "dus":
        sf.kutu(a, b, c, d, **k); sf.kutu(a + 1.3, b + 1.3, c - 1.3, d - 1.3, **k)
        sf.cizgi(a + 1.3, b + 1.3, c - 1.3, d - 1.3, TURUNCU, 0.5, z=4); sf.cizgi(a + 1.3, d - 1.3, c - 1.3, b + 1.3, TURUNCU, 0.5, z=4)


# ----------------------------------------------------------------------------- görünüşler
def tas_serit(sf: Sayfa, pts_fn, u0: float, u1: float, s: float):
    """Subasman: gri şerit ve taş deseni. pts_fn(u, z) → sayfa noktası (z: 0 zemin, −SUBASMAN alt)."""
    sf.cokgen([pts_fn(u0, 0), pts_fn(u1, 0), pts_fn(u1, -SUBASMAN), pts_fn(u0, -SUBASMAN)], fc=GRI_YAZI, ec="black", lw=0.72, z=3)
    adim = SUBASMAN * 0.9; n = int((u1 - u0) / adim); i = 0
    while i < n:
        uc = u0 + (i + 0.5) * adim * (u1 - u0) / (n * adim)
        r = SUBASMAN * (0.34 if i % 2 else 0.42); zc = -SUBASMAN / 2 + (SUBASMAN * 0.08 if i % 3 == 0 else -SUBASMAN * 0.06)
        altigen = [pts_fn(uc + r * math.cos(math.radians(60 * k_ + 15 * (i % 4))), zc + r * math.sin(math.radians(60 * k_ + 15 * (i % 4)))) for k_ in range(6)]
        sf.cokgen(altigen, fc="none", ec=GRI, lw=0.5, z=4)
        i += 1


def dograma_gorunus(sf: Sayfa, P, u0: float, u1: float, ac):
    """Görünüşte pencere / dış kapı. P(u, z) → sayfa noktası."""
    def dort(ua, za, ub, zb, **kw):
        sf.cokgen([P(ua, za), P(ub, za), P(ub, zb), P(ua, zb)], **kw)
    if ac.tur == "pencere":
        en, yuk = (float(v) for v in ac.olcu.split("x")); z0 = PENCERE_ESIK[ac.olcu]; z1 = z0 + yuk
        dort(u0, z0, u1, z1, fc="white", ec="black", lw=1.2, z=5)
        dort(u0 + 3, z0 + 3, u1 - 3, z1 - 3, fc="white", ec="black", lw=0.6, z=5)
        n = 2 if en >= 100 else 1; w = (u1 - u0 - 6) / n
        for i in range(n):
            a, b = u0 + 3 + i * w + 2.5, u0 + 3 + (i + 1) * w - 2.5
            dort(a, z0 + 6, b, z1 - 6, fc="white", ec="black", lw=0.9, z=6)
            if i == 0:                                   # açılan kanat: kırmızı kesik üçgen
                for q in (((a, z0 + 6), ((a + b) / 2, z1 - 6)), (((a + b) / 2, z1 - 6), (b, z0 + 6)), ((a, (z0 + z1) / 2), (b, z0 + 6)), ((a, (z0 + z1) / 2), (b, z1 - 6))):
                    (xa, ya), (xb, yb) = P(*q[0]), P(*q[1])
                    sf.cizgi(xa, ya, xb, yb, KIRMIZI, 0.6, ls=(0, (2, 1.6)), z=7)
            else:                                        # sabit cam: üç eğik çizgi
                um, zm = (a + b) / 2, (z0 + z1) / 2
                for k_ in (-1, 0, 1):
                    (xa, ya), (xb, yb) = P(um - 6 + k_ * 3, zm - 8 + k_ * 3), P(um + 6 + k_ * 3, zm + 8 + k_ * 3)
                    sf.cizgi(xa, ya, xb, yb, "black", 0.5, z=7)
    elif ac.tur == "dis_kapi":
        dort(u0 - 3, 0, u1 + 3, KAPI_UST + 3, fc=GRI_YAZI, ec="black", lw=0.8, z=5)
        dort(u0, 0, u1, KAPI_UST, fc=KAHVE, ec="black", lw=0.6, z=6)
        for i in range(1, 16):
            (xa, ya), (xb, yb) = P(u0 + 2, KAPI_UST * i / 16), P(u1 - 2, KAPI_UST * i / 16)
            sf.cizgi(xa, ya, xb, yb, "black", 0.45, z=7)
        dort(u0 + (u1 - u0) * 0.28, 12, u0 + (u1 - u0) * 0.36, KAPI_UST - 6, fc=GRI_YAZI, ec="black", lw=0.5, z=8)


def cati_rengi(ie: dict) -> str:
    ad = str(ie.get("pafta", {}).get("ozellikler", {}).get("Çatı Kaplama Rengi", "")).strip().lower()
    return CATI_RENGI.get(ad, "#7D8187")


def gorunus_ciz(sf: Sayfa, P, c: dict, cati: dict, kalkan: bool, renk: str, G, ayna: bool):
    """Bir cepheyi çizer. P(u, z) → sayfa noktası; u cephe boyunca (cm), z yükseklik (cm)."""
    boy, H0, s_ = c["boy"], cati["H0"], cati["sacak"]
    for u0, u1, tur, p in c["parcalar"]:
        sf.cokgen([P(u0, 0), P(u1, 0), P(u1, H0), P(u0, H0)], fc=GRI_YAZI if tur == "kose" else "white", ec="black", lw=0.72, z=3)
        if tur == "pano" and p.acilim is not None:
            g = p.gap(); a0, a1 = (g[0], g[2]) if p.duvar.yon == "x" else (g[1], g[3])
            if ayna:
                a0, a1 = boy - a1, boy - a0
            dograma_gorunus(sf, P, a0, a1, p.acilim)
    zs, zm, ust = cati["zs"], cati["zm"], cati["ust"]
    if kalkan:
        sf.cokgen([P(0, H0), P(boy, H0), P(boy, zs + s_ * cati["egim"]), P(boy / 2, zm), P(0, zs + s_ * cati["egim"])], fc="white", ec="black", lw=0.72, z=3)
        sf.cokgen([P(-s_, zs), P(boy / 2, zm), P(boy + s_, zs), P(boy + s_, zs + CATI_KALINLIK), P(boy / 2, ust), P(-s_, zs + CATI_KALINLIK)], fc=GRI_YAZI, ec="black", lw=0.72, z=4)
    else:
        sf.cokgen([P(-s_, zs + CATI_KALINLIK), P(boy + s_, zs + CATI_KALINLIK), P(boy + s_, ust), P(-s_, ust)], fc=renk, ec="black", lw=0.72, z=4)
        n = int((boy + 2 * s_) / 20)
        for i in range(1, n):                                  # trapez sac: beyaz ince çizgiler
            u = -s_ + i * (boy + 2 * s_) / n
            (xa, ya), (xb, yb) = P(u, zs + CATI_KALINLIK + 2), P(u, ust - 2)
            sf.cizgi(xa, ya, xb, yb, "white", 0.55, z=5)
        sf.cokgen([P(-s_, H0), P(boy + s_, H0), P(boy + s_, zs + CATI_KALINLIK), P(-s_, zs + CATI_KALINLIK)], fc=GRI_YAZI, ec="black", lw=0.72, z=5)   # saçak yüzü
        for u in (-s_ + 4, boy + s_ - 4):                      # kalkan uçlarındaki kenar sacı
            sf.cokgen([P(u - 4, zs + CATI_KALINLIK), P(u + 4, zs + CATI_KALINLIK), P(u + 4, ust), P(u - 4, ust)], fc=GRI_YAZI, ec="black", lw=0.6, z=6)
    tas_serit(sf, P, -6.0, boy + 6.0, 1.0)


# ----------------------------------------------------------------------------- pafta
def uret(is_emri_yolu: Path) -> dict:
    import yama
    yama.uret(CIKTI)
    sys.path.insert(0, str(CIKTI))
    from motor_k import geometry as G
    import gorunus as GR

    ie = json.loads(Path(is_emri_yolu).read_text(encoding="utf-8"))
    plan = G.kur(json.loads(json.dumps(ie)))
    W, H = plan.W, plan.H
    cepheler = GR.cephe_verisi(plan, G)
    cati = GR.cati_olculeri(ie, W, H)
    sac = cati["sacak"]
    renk = cati_rengi(ie)
    sf = Sayfa()
    cerceveler(sf, ie, plan, G, cati)

    # yerleşim: [sol yan görünüş] [ölçü] [plan] [ölçü]; planın altında ön görünüş. Ölçek ana çerçeveye sığacak en büyük değer.
    yan_yuk = SUBASMAN + cati["ust"]                       # görünüşün yüksekliği (cm)
    olcu_pay = 46.0; bosluk = 12.0; baslik_pay = 18.0
    s_yatay = (ANA[2] - ANA[0] - 2 * 10 - baslik_pay - bosluk - 2 * olcu_pay) / (yan_yuk + W)
    s_dusey = (ANA[3] - ANA[1] - 8 - 2 * olcu_pay - bosluk - baslik_pay - 8) / (H + yan_yuk)
    s = min(s_yatay, s_dusey, 0.2975)                      # şablondaki ölçekten (0,2975 pt/cm) büyük olmaz
    toplam_en = baslik_pay + yan_yuk * s + bosluk + olcu_pay + W * s + olcu_pay
    xb = ANA[0] + (ANA[2] - ANA[0] - toplam_en) / 2
    yan_x0 = xb + baslik_pay + SUBASMAN * s                # sol yan görünüşte zemin çizgisinin x'i
    px0 = yan_x0 + cati["ust"] * s + bosluk + olcu_pay     # planın sol dış yüzü
    toplam_boy = olcu_pay + H * s + olcu_pay + bosluk + yan_yuk * s + baslik_pay
    yb = ANA[1] + (ANA[3] - ANA[1] - toplam_boy) / 2
    py_ust = yb + olcu_pay                                 # planın arka (üst) dış yüzü
    py0 = py_ust + H * s                                   # planın ön (alt) dış yüzü
    on_zemin = py0 + olcu_pay + bosluk + cati["ust"] * s   # ön görünüşte zemin çizgisinin y'si

    zincirler, etiket_pt = plan_ciz(sf, plan, G, ie, px0, py0, s)

    # ön görünüş: planla aynı x hizasında
    P_on = lambda u, z: (px0 + s * u, on_zemin - s * z)
    gorunus_ciz(sf, P_on, cepheler["on"], cati, kalkan=(cati["makas_ekseni"] != "y"), renk=renk, G=G, ayna=False)
    xo = px0 + s * (W + sac) + 9.0
    sf.olcu(xo, on_zemin - s * cati["H0"], xo, on_zemin, tr(cati["H0"]), "sol")
    t = sf.yazi(px0 + s * W, on_zemin + SUBASMAN * s + 9.5, "ÖN GÖRÜNÜŞ", 8.0, renk=GRI_YAZI, ha="right")
    sf.cizgi(px0 + s * W - 52.0, on_zemin + SUBASMAN * s + 15.0, px0 + s * W, on_zemin + SUBASMAN * s + 15.0, GRI_YAZI, 0.8)
    # sol yan görünüş: 90° döndürülmüş (zemin solda, çatı plana doğru); düşeyde planla aynı hizada
    c_sol = cepheler["sol"]                                 # u: arkadan öne (bakana göre soldan sağa); sayfada yukarıdan aşağı
    P_sol = lambda u, z: (yan_x0 + s * z, py_ust + s * u)
    gorunus_ciz(sf, P_sol, c_sol, cati, kalkan=(cati["makas_ekseni"] == "y"), renk=renk, G=G, ayna=True)
    sf.yazi(yan_x0 - SUBASMAN * s - 7.5, py0, "SOL YAN GÖRÜNÜŞ", 8.2, renk=GRI_YAZI, ha="center", va="bottom", rot=90)
    sf.cizgi(yan_x0 - SUBASMAN * s - 2.6, py0 - 76.0, yan_x0 - SUBASMAN * s - 2.6, py0, GRI_YAZI, 0.8)

    hedef = CIKTI / ie["is_emri_no"] / "plan"; hedef.mkdir(parents=True, exist_ok=True)
    govde = f"Portman_{ie['is_emri_no']}_r{int(ie.get('revizyon', 1)):02d}_plan"
    sf.fig.savefig(hedef / f"{govde}.pdf"); sf.fig.savefig(hedef / f"{govde}.png", dpi=200)
    plt.close(sf.fig)
    ozet = {"is_emri_no": ie["is_emri_no"], "sayfa_pt": [EN, BOY], "olcek_pt_cm": round(s, 4), "olcek_1e": round(1 / (s / 72 * 2.54)),
            "zincirler_cm": zincirler, "mahal_yazi_pt": etiket_pt, "dis_olcu_cm": [W, H], "mahal_m2": {ad: round(m.alan_m2) for ad, m in plan.mahaller.items()},
            "dosyalar": [f"{govde}.pdf", f"{govde}.png"]}
    (hedef / "plan_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    return ozet | {"hedef": str(hedef)}


if __name__ == "__main__":
    yol = Path(sys.argv[1]) if len(sys.argv) > 1 else BURASI / "is_emri_3arti1_1150x1050.json"
    if not yol.is_absolute() and not yol.exists():
        yol = BURASI / yol
    print(json.dumps(uret(yol), ensure_ascii=False, indent=1))
