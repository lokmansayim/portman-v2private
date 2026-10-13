"""Bayiye giden plan paftası: "Örnek Şablon" düzeni (A4 yatay), geometri genel motordan (İE-08 A3; Lokman 6 Ekim 2026 19:46).

Düzen, tablolar, yazı ve renk kuralları `docs/sartname/plan_paftasi_sablonu.md`'den; çizim kodu `deneme/2026-10-06_kalinlik_160_100/
sablon_pafta.py`'nin (pano birimli Motor için yazılmıştı) Yapı Tanımı 0.5 geometrisine bağlanmış halidir: duvarlar `yapi.kur`'dan,
görünüşler `sahne.izdusum`'dan (çok düzlemli çatı dahil), çatı ölçüleri `cati_genel`'den. Çelikte pano eki çizilmez (kural yok; İE-08
Soru 19). Sayfa 1 şablonun aynısı: plan ortada, solunda 90° döndürülmüş sol yan görünüş, altında ön görünüş; sağda BİNA ÖZELLİKLERİ
ve ÖZEL İSTEKLER; altta antet. Sayfa 2: dört görünüş ve çatı planı (genel motorun kendi çizimleri; İE-08 Soru 18).

Bilinmeyen değerler "..." yazılır (şablonda da öyle). Antette İLGİLİ KİŞİ-TELEFON: yalnız bayinin adı ve bayi kartındaki telefonu
(`bilgi["bayi_adi"]`, `bilgi["bayi_telefonu"]`; D-09); zarf vermezse "...". 8b mühendis kabulüne kadar 1. sayfada antetin üstünde de
küçük "TASLAK" yazar (`pafta_sablonu.json › taslak_ibaresi`; Lokman, Soru 25, 12 Ekim 2026). Ölçü zincirinde 15 cm ve daha kısa
parçalar komşusuna katılır ve `pafta_ozet.json › kontrol_notlari`'na mühendis için not düşülür (Lokman, 12 Ekim 2026: "Çelikte 15 cm
parça çıkmaz"). Çıktı: `<kod>_pafta.pdf` (2 sayfa), `<kod>_pafta_sablon.png` (1. sayfanın önizlemesi; antetle birlikte bayinin
numarasını taşır: yalnız bayiye gider, kanıta ve referansa girmez) ve `<kod>_pafta_ozet.json`. Üretim tarihi `time.gmtime()`den gelir
(testte TEST_SABIT_ZAMAN ile sabit; D-02). PDF üst verisinde zaman yoktur.

    python -m motor.genel.sablon_pafta modeller/C8801.json <çıktı klasörü> [--yontem panel|omega_asik] [--set <kural seti>]
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)
import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import matplotlib
from matplotlib import font_manager as fm
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Arc, FancyBboxPatch, PathPatch, Polygon as MplPolygon, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from shapely.geometry import Polygon as SPolygon
from shapely.ops import unary_union

BURADA = Path(__file__).resolve().parent
KOK = BURADA.parents[1]
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
SUBASMAN = 15.0
TOL = 0.5
_FONT_HAZIR = False
COMIC = ARIAL = None


def fontlari_hazirla() -> None:
    """Comic Relief (şablondaki Comic Sans MS'in açık lisanslı eşi; `font/`, OFL) ve Arial'in eşi (Liberation Sans; yoksa DejaVu Sans)."""
    global _FONT_HAZIR, COMIC, ARIAL
    if _FONT_HAZIR:
        return
    for f in ("ComicRelief-Regular.ttf", "ComicRelief-Bold.ttf", "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf"):
        fm.fontManager.addfont(str(BURADA / "font" / f))
    COMIC = fm.FontProperties(fname=str(BURADA / "font" / "ComicRelief-Regular.ttf"))
    # Arial'in ölçüdeş açık eşi Liberation Sans (OFL) depodan okunur: çıktı makinedeki yazı tiplerine bağlı değil (kod incelemesi, 12.10)
    ARIAL = fm.FontProperties(fname=str(BURADA / "font" / "LiberationSans-Regular.ttf"))
    _FONT_HAZIR = True


_SABLON_KURAL: dict | None = None


def sablon_kurallari() -> dict:
    """`kurallar/cizim/pafta_sablonu.json` (vasistas eşiği, çatı tipi adları, özellik yazı boyu); anahtar yoksa koddaki varsayılan sürer."""
    global _SABLON_KURAL
    if _SABLON_KURAL is None:
        yol = BURADA.parents[1] / "kurallar" / "cizim" / "pafta_sablonu.json"
        _SABLON_KURAL = json.loads(yol.read_text(encoding="utf-8")) if yol.is_file() else {}
    return _SABLON_KURAL


def tr(v: float, n: int = 0) -> str:
    return f"{v:.{n}f}".replace(".", ",") if n else f"{int(round(v))}"


def yazi_eni(metin: str, pt: float, font=None) -> float:
    if not metin:
        return 0.0
    return TextPath((0, 0), metin, size=pt, prop=font or ARIAL).get_extents().width


def yarim_yukari(v: float) -> int:
    """Ölçü yuvarlaması: yarım yukarı (970,5 → 971; Python'un round'u çifte yuvarlar). Genel ölçü ve zincir parçaları aynı kuralla."""
    return int(math.floor(v + 0.5))


def tam_bol(parcalar: list[float], hedef: int | None = None) -> list[int]:
    """Ölçü zincirini tam sayıya yuvarlar; toplam, genel ölçünün yuvarlağıyla (`hedef`) aynı kalır (en büyük kalan yöntemi)."""
    hedef = yarim_yukari(sum(parcalar)) if hedef is None else hedef; taban = [math.floor(p) for p in parcalar]
    for i in sorted(range(len(parcalar)), key=lambda i: parcalar[i] - taban[i], reverse=True)[:hedef - sum(taban)]:
        taban[i] += 1
    return taban


class Sayfa:
    def __init__(self, fig):
        self.fig = fig
        self.ax = fig.add_axes([0, 0, 1, 1]); self.ax.set_xlim(0, EN); self.ax.set_ylim(0, BOY); self.ax.axis("off")

    @staticmethod
    def y(yd):            # şablon koordinatı (aşağı) → çizim koordinatı (yukarı)
        return BOY - yd

    def cizgi(self, x0, y0, x1, y1, renk="black", lw=0.72, ls="-", z=3, clip=None, gid=None):
        (ln,) = self.ax.plot([x0, x1], [self.y(y0), self.y(y1)], color=renk, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")
        if clip is not None:
            ln.set_clip_path(clip)
        if gid:                                       # yalnız denetim etiketi (yazi_cakisma); PDF/PNG çıktısını değiştirmez
            ln.set_gid(gid)
        return ln

    def kutu(self, x0, y0, x1, y1, fc="none", ec="black", lw=0.72, z=2, ls="-"):
        self.ax.add_patch(Rectangle((x0, self.y(y1)), x1 - x0, y1 - y0, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z, linestyle=ls))

    def yuvarlak_kutu(self, k, lw=0.72):
        x0, y0, x1, y1 = k
        self.ax.add_patch(FancyBboxPatch((x0 + KOSE_R, self.y(y1) + KOSE_R), x1 - x0 - 2 * KOSE_R, y1 - y0 - 2 * KOSE_R,
                                         boxstyle=f"round,pad={KOSE_R},rounding_size={KOSE_R}", facecolor="none", edgecolor="black", linewidth=lw, zorder=4))

    def cokgen(self, pts, fc, ec="black", lw=0.72, z=2, ls="-"):
        p = MplPolygon([(x, self.y(y)) for x, y in pts], closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z, joinstyle="miter", linestyle=ls)
        self.ax.add_patch(p)
        return p

    def yazi(self, x, yd, s, pt=7.3, font=None, renk="black", ha="left", va="center", rot=0, z=6, **kw):
        return self.ax.text(x, self.y(yd), s, fontsize=pt, fontproperties=font or COMIC, color=renk, ha=ha, va=va, rotation=rot, zorder=z, **kw)

    def olcu(self, x0, y0, x1, y1, metin, taraf, kaydir: float = 0.0):
        """Şablondaki ölçü: mavi çizgi, uçlarda kalın eğik çentik, siyah Arial yazı. taraf: yazının çizgiye göre yeri (ust | alt | sol | sag);
        kaydir: yazıyı çizgiden ek uzaklaştırma (pt; dar parçalarda yazılar binmesin)."""
        self.cizgi(x0 - (4 if y0 == y1 else 0), y0 - (4 if x0 == x1 else 0), x1 + (4 if y0 == y1 else 0), y1 + (4 if x0 == x1 else 0), MAVI, 0.72, z=5,
                   gid="olcu_cizgi")
        for (x, y_) in ((x0, y0), (x1, y1)):
            self.cizgi(x - 4.2, y_ + 4.2, x + 4.2, y_ - 4.2, MAVI, 1.56, z=5, gid="olcu_centik")
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        if y0 == y1:
            self.yazi(mx, my + (-7.2 if taraf == "ust" else 7.6) + kaydir, metin, 10.7, ARIAL, ha="center")
        else:
            self.yazi(mx + (-7.4 if taraf == "sol" else 7.4) + kaydir, my, metin, 10.7, ARIAL, ha="center", rot=90)


def _satirlara(v: str, pt: float, gen: float) -> list[str]:
    """Değeri virgül (yoksa boşluk) sınırından, her satır `gen`'e sığacak biçimde açgözlü sarar; boş parça üretmez. Virgülle sarılan
    satırların sonunda virgül kalır (liste sürüyor); sığma ölçümü o virgülü de sayar."""
    ayrac = ", " if ", " in v else " "
    kuyruk = "," if ayrac == ", " else ""
    parcalar = [p.strip() for p in v.split(ayrac) if p.strip()]
    satirlar: list[str] = []
    for i, p in enumerate(parcalar):
        ek = "" if i == len(parcalar) - 1 else kuyruk
        if satirlar and yazi_eni(satirlar[-1] + ayrac + p + ek, pt, COMIC) <= gen:
            satirlar[-1] = satirlar[-1] + ayrac + p
        else:
            satirlar.append(p)
    if not satirlar:
        return [v]
    return [s + kuyruk for s in satirlar[:-1]] + satirlar[-1:]


SATIR_BOSLUK_PT = 0.6            # sarılan satırlar arasında mürekkep boşluğu (pt; Agg metriklerinin piksel yuvarlamasından büyük)


def _murekkep(s: str, pt: float, font=None) -> tuple[float, float]:
    """Yazının taban çizgisine göre mürekkep çıkması ve alçalması (pt; TextPath): satır aralığı buna göre (yazı kutuları binmesin)."""
    if not s:
        return 0.0, 0.0
    e = TextPath((0, 0), s, size=pt, prop=font or COMIC).get_extents()
    return max(e.y1, 0.0), max(-e.y0, 0.0)


def _blok(satirlar: list[str], pt: float) -> tuple[list[float], float]:
    """Sarılı satırların taban çizgisi aralıkları (pt) ve bloğun toplam mürekkep yüksekliği: ardışık satırların mürekkebi örtüşmez
    (alçalma + çıkma + SATIR_BOSLUK_PT). Dönen: (aralıklar, toplam)."""
    olc = [_murekkep(s_, pt) for s_ in satirlar]
    ara = [olc[i][1] + olc[i + 1][0] + SATIR_BOSLUK_PT for i in range(len(satirlar) - 1)]
    return ara, (olc[0][0] + sum(ara) + olc[-1][1]) if satirlar else 0.0


def _sadelestir(v: str, bir_carpani: bool, adet_sozcugu: bool) -> list[str]:
    """Sığmayan değerin daha kısa yazımları (bilgi aynı): önce "1×" önekleri kalkar ("1×80/180" → "80/180"; "N adet (…)" içinde tek
    adet zaten bellidir — Lokman 13.10.2026), o da yetmezse "adet" sözcüğü kalkar ("5 (120/100, …)"; kural anahtarı
    `ozellik_adet_sozcugu_kalkar`, varsayım). Dönen: denenecek yazımlar, en sade sonda; değişmeyenler atlanır."""
    out = []
    v1 = re.sub(r"(?<![\d×])1×(?=\d)", "", v) if bir_carpani else v
    if v1 != v:
        out.append(v1)
    v2 = re.sub(r"^(\d+) adet \(", r"\1 (", v1) if adet_sozcugu else v1
    if v2 != v1:
        out.append(v2)
    return out


def _sigdir(v: str, pt_bas: float, en_az: float, gen: float, yuk: float | None = None, en_az_mutlak: float | None = None,
            sade: list[str] | None = None) -> tuple[float, list[str]]:
    """Bina özellikleri değeri (Lokman 12–13.10.2026; bilgi kesilmez, uydurulmaz): önce yazı küçülür (en_az'a kadar); sığmazsa önce
    daha sade yazım (`sade`: "1×" önekleri kalkmış, sonra "adet"siz) tek satırda denenir; o da sığmazsa sade yazım **iki** satıra sarılır
    (en büyük boyda), o da olmazsa üç satır. Satır aralığı mürekkep ölçüsüyledir (`_blok`): blok `yuk`'a sığmalı. en_az'da sığmazsa yazı
    `en_az_mutlak`'a kadar küçülür (kural anahtarı `ozellik_yazi_pt_mutlak`; 5 pt'nin altına inmez). Az satır çok satırdan önce,
    büyük yazı küçük yazıdan önce gelir. Dönen: (pt, satırlar)."""
    if yazi_eni(v, pt_bas, COMIC) <= gen:
        return pt_bas, [v]
    sade = list(sade or [])
    bir = [s_ for s_ in sade if s_.startswith(v.split(" ")[0] + " adet") or " adet" not in v]   # "1×" kalkmış yazım (adet sözcüğü duruyor)
    adetsiz = [s_ for s_ in sade if s_ not in bir]                                               # son çare (varsayım): "adet" de kalkmış

    def tek_satir(metin: str, taban: float) -> tuple[float, list[str]] | None:
        pt = max(taban, pt_bas * (gen - 2.0) / yazi_eni(metin, pt_bas, COMIC))
        return (pt, [metin]) if yazi_eni(metin, pt, COMIC) <= gen else None

    def sarili(metin: str, n: int, taban: float) -> tuple[float, list[str]] | None:
        for pt2 in [pt_bas - 0.1 * i for i in range(int((pt_bas - taban) / 0.1) + 1)] + [taban]:
            if pt2 < taban - 1e-9:
                break
            satirlar = _satirlara(metin, pt2, gen)
            if len(satirlar) <= n and all(yazi_eni(s_, pt2, COMIC) <= gen for s_ in satirlar) and (yuk is None or _blok(satirlar, pt2)[1] <= yuk):
                return pt2, satirlar
        return None

    tabanlar = [en_az] + ([en_az_mutlak] if en_az_mutlak is not None and en_az_mutlak < en_az else [])

    def asama(yazimlar: list[str]) -> tuple[float, list[str]] | None:
        """Verilen yazımlarla: önce tek satır (en_az'a kadar), sonra iki ve üç satır; en_az'da olmazsa en_az_mutlak'a kadar."""
        for taban in tabanlar:
            for metin in yazimlar:
                r = tek_satir(metin, taban)
                if r:
                    return r
            for n in (2, 3):
                for metin in (yazimlar[1:] or yazimlar):        # sarma en sade yazımla (Lokman: önce 1× kalkar, sonra iki satır)
                    r = sarili(metin, n, taban)
                    if r:
                        return r
        return None

    r = asama([v] + bir)
    if r is None and adetsiz:                                   # son çare (varsayım, kural anahtarı): "adet" sözcüğü de kalkar
        r = asama(adetsiz)
    if r:
        return r
    son = tabanlar[-1]
    return son, _satirlara((adetsiz or bir or [v])[-1], son, gen)


def _sar(metin: str, genislik: int) -> list[str]:
    satir, out = "", []
    for k in metin.split():
        if satir and len(satir) + 1 + len(k) > genislik:
            out.append(satir); satir = k
        else:
            satir = (satir + " " + k).strip()
    return out + ([satir] if satir else [])


# ----------------------------------------------------------------------------- tanımdan bilgi
def ozellikler(t: dict, y: dict, c: dict, kur: dict, bilgi: dict) -> dict:
    """BİNA ÖZELLİKLERİ satırları: tanım ve kural kitabından; bayinin söyledikleri `bilgi['ozellikler']` ile üstüne yazılır; gerisi '...'."""
    oz = {}
    sinif = t.get("duvar_siniflari", {})
    oz["Bina Yüksekliği"] = f"{t['kat_yuksekligi'] * 10:g}mm"
    for ad, k in (("Dış Duvarlar", "dis"), ("İç Duvarlar", "ic")):
        s = sinif.get(k, {})
        oz[ad] = (s.get("profil", "...") + " çelik profil") if s.get("profil") else "..."
    oz["Panel Türü"] = "Çelik karkas (LGF)" if t.get("aile", "").endswith("celik") else "..."
    ks = sablon_kurallari(); ct = t.get("cati") or {}
    tip_adi = (ct.get("tip_adi") or "").split(":")[0].strip()
    oz["Çatı Şekli"] = tip_adi.capitalize() if tip_adi else ((ks.get("cati_tipi_adi") or {}).get("deger") or {}).get(ct.get("tip"), "...")   # iç anahtar basılmaz
    egimler = sorted({round(d["egim"] * 100) for d in c.get("duzlemler", [])})
    oz["Çatı Eğimi"] = " / ".join(f"%{e:g}" for e in egimler) if egimler else "..."
    kaplama = t.get("cati", {}).get("kaplama") or (kur.get("baz_paket_cati_kaplamasi") or {}).get("deger")
    oz["Çatı Kaplaması"] = ((kur.get("cati_kaplama") or {}).get("deger") or {}).get(kaplama, kaplama or "...") if kaplama else "..."
    acl = y["acikliklar"]
    dis = [a for a in acl if a["tur"] == "dis_kapi"]; ic = [a for a in acl if a["tur"] == "ic_kapi"]
    esik = ((ks.get("vasistas_en_cok_yukseklik_cm") or {}).get("deger") or 60)       # kural anahtarı (pafta_sablonu.json); yoksa 60 cm
    pen = [a for a in acl if a["tur"] == "pencere" and a["yuk"] > esik]; vas = [a for a in acl if a["tur"] == "pencere" and a["yuk"] <= esik]
    olcu = lambda L: ", ".join(f"{n}×{k}" for k, n in sorted(__import__('collections').Counter(f"{int(a['en'])}/{int(a['yuk'])}" for a in L).items()))
    oz["Dış Kapı"] = (f"{len(dis)} adet ({olcu(dis)})" if dis else "...")
    oz["İç Kapılar"] = (f"{len(ic)} adet ({olcu(ic)})" if ic else "...")
    oz["Pencereler"] = (f"{len(pen)} adet ({olcu(pen)})" if pen else "...")
    oz["Vasistaslar"] = (f"{len(vas)} adet ({olcu(vas)})" if vas else "yok")
    for ad in ("Çatı Kaplama Rengi", "Dış Boya Rengi", "İç Boya Rengi", "Köşe ve Söveler"):
        oz[ad] = "..."
    oz.update({k: v for k, v in (bilgi.get("ozellikler") or {}).items() if v})
    return oz


def cerceveler(sf: Sayfa, t: dict, oz: dict, bilgi: dict, oturum_m2: float):
    x0, y0, x1, y1 = DIS
    sf.kutu(x0, y0, x1, y1, lw=1.3, z=4)
    sf.yuvarlak_kutu(ANA)
    sf.yuvarlak_kutu(OZELLIK)
    sf.yazi((OZELLIK[0] + OZELLIK[2]) / 2, 23.0, "BİNA ÖZELLİKLERİ", 10.9, renk=KOYU_KIRMIZI, ha="center")
    adim = (OZELLIK[3] - OZELLIK_BASLIK_ALT) / len(OZELLIK_SIRASI)
    yp = (sablon_kurallari().get("ozellik_yazi_pt") or {}).get("deger") or {}
    en_cok, en_az = float(yp.get("en_cok", 7.3)), float(yp.get("en_az", 5.2))
    _m = (sablon_kurallari().get("ozellik_yazi_pt_mutlak") or {}).get("deger")
    en_az_mutlak = float(_m) if _m is not None else None             # anahtar yoksa en_az'ın altına inilmez
    bir_carpani = bool((sablon_kurallari().get("ozellik_bir_carpani_kalkar") or {}).get("deger", False))
    adet_sozcugu = bool((sablon_kurallari().get("ozellik_adet_sozcugu_kalkar") or {}).get("deger", False))
    gen = OZELLIK[2] - 765.0 - 2
    yuk = adim - 1.0                                                   # sarılı bloğun mürekkebi satır çizgilerinden ≥ 0,5 pt uzak
    for i, ad in enumerate(OZELLIK_SIRASI):
        yt = OZELLIK_BASLIK_ALT + i * adim
        sf.cizgi(OZELLIK[0], yt, OZELLIK[2], yt)
        v = str(oz.get(ad, "..."))
        pt, satirlar = (en_cok, [v]) if v == "..." else _sigdir(v, en_cok, en_az, gen, yuk, en_az_mutlak, _sadelestir(v, bir_carpani, adet_sozcugu))
        v = satirlar[0] if len(satirlar) == 1 else v                   # sığmazsa sade yazım, küçülür, sonra sarılır; bilgi kesilmez (pafta_ozet tam değeri taşır)
        sf.yazi(695.0, yt + adim / 2 + 0.6, ad, 7.3)
        if len(satirlar) == 1:
            sf.yazi(765.0, yt + adim / 2 + (0.6 if v != "..." else -1.2), v, pt if v != "..." else 12.0)
        else:                                                          # sarılı satırlar: mürekkep aralığıyla, satırda ortalı (13.10.2026)
            ara, toplam = _blok(satirlar, pt)
            yd = yt + adim / 2 - toplam / 2 + _murekkep(satirlar[0], pt)[0]        # ilk satırın taban çizgisi (şablon koordinatı, aşağı)
            for k_, s_ in enumerate(satirlar):
                sf.yazi(765.0, yd, s_, pt, va="baseline")
                if k_ < len(ara):
                    yd += ara[k_]
    sf.cizgi(OZELLIK_BOLME, OZELLIK_BASLIK_ALT, OZELLIK_BOLME, OZELLIK[3])
    sf.yuvarlak_kutu(ISTEK)
    sf.yazi(696.0, 272.0, "ÖZEL İSTEKLER;", 7.6, renk=KOYU_KIRMIZI)
    yy = 282.0
    for i, m in enumerate(bilgi.get("ozel_istekler") or [], 1):
        for j, s_ in enumerate(_sar(str(m), 29)):
            if yy > ISTEK[3] - 8:
                break
            sf.yazi(699.0 if j == 0 else 711.0, yy, (f"{i}. " if j == 0 else "") + s_, 7.6, renk=KOYU_KIRMIZI)
            yy += 9.2
        yy += 2.0
    # TASLAK ibaresi: 8b mühendis kabulüne kadar 1. sayfada da, antetin üstünde küçük (Lokman, Soru 25, 12.10.2026; kural anahtarı
    # `taslak_ibaresi`; anahtar yoksa ya da sayfa1 false ise yazılmaz). Ana çerçeve ile antet arasındaki boşluğa, antetin orta kutusu hizasında.
    ti = (sablon_kurallari().get("taslak_ibaresi") or {}).get("deger") or {}
    if ti.get("sayfa1") and ti.get("metin"):
        sf.yazi(ANTET_ORTA[0], (ANA[3] + ANTET_ORTA[1]) / 2 + 0.3, str(ti["metin"]), 5.4, renk=KOYU_KIRMIZI)
    sf.yuvarlak_kutu(ANTET_SOL)                            # şablonda boş (firma alanı / logo; Soru 20a)
    sf.yuvarlak_kutu(ANTET_ORTA)
    for ys in ANTET_ORTA_SATIR:
        sf.cizgi(ANTET_ORTA[0], ys, ANTET_ORTA[2], ys)
    sf.cizgi(ANTET_ORTA_BOLME, ANTET_ORTA[1], ANTET_ORTA_BOLME, ANTET_ORTA[3])
    sat = [ANTET_ORTA[1], *ANTET_ORTA_SATIR, ANTET_ORTA[3]]
    no = bilgi.get("is_emri_no") or t["kod"]; rev = int(bilgi.get("revizyon") or 1)
    tur = "ÇELİK" if t.get("aile", "").endswith("celik") else "PREFABRİK"
    # İLGİLİ KİŞİ-TELEFON: yalnız bayinin adı ve bayi kartındaki kayıtlı telefonu (D-09, Lokman 12.10.2026 14:53); zarf vermezse "..."
    # (katalog ve altın üretimde böyle). Serbest metin anahtarı yok: başka hiç kimsenin numarası bu satıra giremez; PR-2'de zarf
    # `bayi_adi` ve `bayi_telefonu`yu bayi kartından doldurur, başka rakam dizisi reddedilir.
    ilgili = " · ".join(str(x).strip() for x in (bilgi.get("bayi_adi"), bilgi.get("bayi_telefonu")) if x) or "..."
    orta = [("PROJE KODU", f"{no} r{rev:02d}"), ("İLGİLİ KİŞİ-TELEFON", ilgili),
            ("SEVK ADRESİ", bilgi.get("sevk_adresi") or "..."), ("PROJE ADI & M²", bilgi.get("proje_adi") or f"{t['kod']} · {oturum_m2:.0f} M² {tur} KONUT")]
    for (ad, v), ya, yb in zip(orta, sat, sat[1:]):
        sf.yazi(287.0, (ya + yb) / 2 + 0.4, ad, 7.3)
        sf.yazi(431.0, (ya + yb) / 2 + (0.4 if v != "..." else -1.4), v, 7.3 if v != "..." else 12.0)
    sf.yuvarlak_kutu(ANTET_SAG)
    for ys in ANTET_SAG_SATIR:
        sf.cizgi(ANTET_SAG[0], ys, ANTET_SAG[2], ys)
    sf.cizgi(ANTET_SAG_BOLME, ANTET_SAG[1], ANTET_SAG_BOLME, ANTET_SAG[3])
    sat = [ANTET_SAG[1], *ANTET_SAG_SATIR, ANTET_SAG[3]]
    tarih = bilgi.get("tarih") or time.strftime("%d.%m.%Y", time.gmtime())
    # Çizen, Kontrol ve Onay: "Portman" (Lokman, 12.10.2026 14:53: "Portman her yerde geçsin"); zarf başka ad verirse o yazılır
    for (ad, v), ya, yb in zip([("TARİH", tarih), ("ÇİZEN", bilgi.get("cizen") or "Portman"), ("KONTROL", bilgi.get("kontrol") or "Portman"), ("ONAY", bilgi.get("onay") or "Portman")], sat, sat[1:]):
        sf.yazi(698.0, (ya + yb) / 2 + 0.4, ad, 7.3)
        sf.yazi(765.0, (ya + yb) / 2 + (0.4 if v != "..." else -1.4), v, 7.3 if v != "..." else 12.0)


# ----------------------------------------------------------------------------- plan
def _dis_taraf(y: dict, d: dict) -> tuple[float, float]:
    """Dış duvarın dışarı bakan yönü (plan merkezine göre)."""
    bx0, by0, bx1, by1 = y["kutle"].bounds
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    x0, y0, x1, y1 = d["kutu"]
    if d["yon"] == "x":
        return (0.0, -1.0) if (y0 + y1) / 2 < cy else (0.0, 1.0)
    return (-1.0, 0.0) if (x0 + x1) / 2 < cx else (1.0, 0.0)


def _mahal_tarafi(y: dict, d: dict, mahal: str | None) -> tuple[float, float] | None:
    """Kapının açıldığı mahal duvarın hangi yanında (kapının açıldığı yön)."""
    b = y["bolgeler"].get(mahal or "")
    if not b or b.get("sinif") == "dis":
        return None
    p = b["net"].representative_point()
    x0, y0, x1, y1 = d["kutu"]
    if d["yon"] == "x":
        return (0.0, 1.0) if p.y > (y0 + y1) / 2 else (0.0, -1.0)
    return (1.0, 0.0) if p.x > (x0 + x1) / 2 else (-1.0, 0.0)


def dis_yuz_sinirlari(y: dict) -> tuple[float, float, float, float]:
    """Yapının kaplanmış dış yüzlerinin sınır kutusu (cm). Onaylı çizim seti kuralı: ölçüler dış yüzden (`ciz_genel.dis_hat`, mühendis
    planı ve görünüşlerle aynı; `y["kutle"]` karkas kutusudur, dış kaplama kadar küçüktür — Lokman/rehber, 12 Ekim 2026)."""
    from . import ciz_genel
    pts = [p for h in ciz_genel.dis_hat(y) for p in h]
    if not pts:
        return y["kutle"].bounds
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _birlestir(noktalar, uclar: tuple[float, float], tol: float) -> tuple[list[float], list[dict]]:
    """Sıralı zincir noktaları; birbirine `tol` cm'den yakın olanlar tek nokta sayılır (kısa parça komşusuna katılır), uçlar (genel ölçü)
    her zaman korunur. Bayi paftasında 15 cm ve daha kısa parçalar (veranda dikmesi, korkuluk, kaplama sıçraması, tanımda 1–2 cm kayma)
    okunmaz (Lokman, 12.10.2026: "Çelikte 15 cm parça çıkmaz"); mühendis planı tam zinciri taşır (`pafta_sablonu.json` ›
    zincir_en_kisa_parca_cm). Dönen: (noktalar, katılan parçalar [{konum_cm: zincir başından, parca_cm}]) — katılanlar mühendise
    kontrol notu olur (`pafta_ozet.json › kontrol_notlari`). Tek kaynak `ciz_genel.zincir_birlestir` (bayi plan görseli de kullanır)."""
    from . import ciz_genel
    return ciz_genel.zincir_birlestir(noktalar, uclar, tol)


def plan_ciz(sf: Sayfa, y: dict, t: dict, px0: float, py0: float, s: float) -> tuple[dict, dict, list[dict], dict]:
    """px0, py0: planın sol-ön dış köşesinin (dış yüz) sayfadaki yeri (pt; y aşağı). s: pt/cm.
    Dönen: ölçü zincirleri, mahal yazı boyları, kontrol notları (komşusuna katılan kısa parçalar), mahal etiket yerleri (cm)."""
    bx0, by0, bx1, by1 = dis_yuz_sinirlari(y)
    W, H = bx1 - bx0, by1 - by0
    X = lambda x: px0 + s * (x - bx0)
    Y = lambda yy: py0 - s * (yy - by0)
    # duvarlar: çift çizgi (beyaz dolgu, siyah kenar); kolon ve korkuluk mavi kenarla (şablondaki köşe parçası rengi)
    for d in y["duvarlar"]:
        x0, y0, x1, y1 = d["kutu"]
        ec, lw = ("black", 0.72) if d["sinif"] not in ("kolon", "korkuluk") else (MAVI, 1.0)
        sf.kutu(X(x0), Y(y1), X(x1), Y(y0), fc="white", ec=ec, lw=lw, z=3)
    # açıklıklar
    for ac in y["acikliklar"]:
        d = y["adli"][ac["duvar"]]
        x0, y0, x1, y1 = d["kutu"]
        if d["yon"] == "x":
            g = (ac["a0"], y0, ac["a1"], y1)
        else:
            g = (x0, ac["a0"], x1, ac["a1"])
        gx0, gy0, gx1, gy1 = g
        if ac["tur"] == "pencere":
            sf.kutu(X(gx0), Y(gy1), X(gx1), Y(gy0), fc="white", ec=MAVI, lw=1.0, z=4)
            etiket = ac.get("etiket") or f"{int(ac['en'])}/{int(ac['yuk'])}"
            if ac["yuk"] <= ((sablon_kurallari().get("vasistas_en_cok_yukseklik_cm") or {}).get("deger") or 60):   # tabloyla aynı anahtar
                etiket = "V." + etiket
            n = 2 if ac["en"] >= 100 else 1
            dis = _dis_taraf(y, d)
            if d["yon"] == "x":
                ym = (gy0 + gy1) / 2; w = (gx1 - gx0) / n
                for i in range(n):
                    sf.kutu(X(gx0 + i * w) + 1.0, Y(ym) - 1.0, X(gx0 + (i + 1) * w) - 1.0, Y(ym) + 1.0, fc="white", ec=TURUNCU, lw=0.72, z=5)
                sf.yazi(X((gx0 + gx1) / 2), Y(gy0) + 5.0 if dis[1] < 0 else Y(gy1) - 5.0, etiket, 5.0, ha="center")
            else:
                xm = (gx0 + gx1) / 2; w = (gy1 - gy0) / n
                for i in range(n):
                    sf.kutu(X(xm) - 1.0, Y(gy0 + (i + 1) * w) + 1.0, X(xm) + 1.0, Y(gy0 + i * w) - 1.0, fc="white", ec=TURUNCU, lw=0.72, z=5)
                sf.yazi(X(gx0) - 5.0 if dis[0] < 0 else X(gx1) + 5.0, Y((gy0 + gy1) / 2), etiket, 5.0, ha="center", rot=90)
        elif ac["tur"] in ("ic_kapi", "dis_kapi"):
            n = _mahal_tarafi(y, d, ac.get("mahal") or ac.get("not"))
            if n is None:                                    # mahal bilinmiyorsa: dış kapı içeri açılır
                dx, dy = _dis_taraf(y, d); n = (-dx, -dy)
            w = ac["en"]
            mentese_son = ac.get("mentese", "bas") == "son"
            if d["yon"] == "x":
                cy = gy1 if n[1] > 0 else gy0
                hx = gx1 if mentese_son else gx0; ox_ = gx0 if mentese_son else gx1
                mente, uc, karsi = (hx, cy), (hx, cy + n[1] * w), (ox_, cy)
            else:
                cx = gx1 if n[0] > 0 else gx0
                hy = gy1 if mentese_son else gy0; oy_ = gy0 if mentese_son else gy1
                mente, uc, karsi = (cx, hy), (cx + n[0] * w, hy), (cx, oy_)
            sf.cizgi(X(mente[0]), Y(mente[1]), X(uc[0]), Y(uc[1]), MAVI, 1.4, z=5)                 # kanat
            a0 = math.degrees(math.atan2(uc[1] - mente[1], uc[0] - mente[0]))
            a1 = math.degrees(math.atan2(karsi[1] - mente[1], karsi[0] - mente[0]))
            t0, t1 = sorted((a0 % 360, a1 % 360))
            if t1 - t0 > 180:
                t0, t1 = t1, t0 + 360
            sf.ax.add_patch(Arc((X(mente[0]), sf.y(Y(mente[1]))), 2 * w * s, 2 * w * s, theta1=t0, theta2=t1, color="black", lw=0.72, ls=(0, (4, 3)), zorder=5))
            if d["yon"] == "x":
                for jx in (gx0, gx1):
                    sf.cizgi(X(jx), Y(gy0), X(jx), Y(gy1), MAVI, 1.4, z=5)
            else:
                for jy in (gy0, gy1):
                    sf.cizgi(X(gx0), Y(jy), X(gx1), Y(jy), MAVI, 1.4, z=5)
            ex, ey = (mente[0] + uc[0] + karsi[0]) / 3, (mente[1] + uc[1] + karsi[1]) / 3
            sf.yazi(X(ex), Y(ey), tr(w), 3.6, renk=GRI_YAZI, ha="center")
            if ac["tur"] == "dis_kapi":
                sf.yazi(X(ex), Y(ey) + 4.4, "ÇELİK", 3.3, renk=GRI_YAZI, ha="center")
    # mahal adları ve m²: tanım `etiket_yeri` veriyorsa oraya (mühendis planı `ciz_genel.plan_eksen` gibi; KT-01 "Salon - Mutfak" yazısı
    # kapı simgesine biniyordu — rehberin göz denetimi, 12.10.2026), yoksa mahalin temsil noktasına
    etiket = {}; etiket_yeri = {}
    for ad, b in y["bolgeler"].items():
        if b.get("sinif") == "dis":
            continue
        p = b["net"].representative_point(); mx0, my0, mx1, my1 = b["net"].bounds
        ex, ey = (float(b["etiket_yeri"][0]), float(b["etiket_yeri"][1])) if b.get("etiket_yeri") else (p.x, p.y)
        metin = ad.upper()
        ic_en = (mx1 - mx0) * s - 7.0
        pt = max(3.5, min(8.4, 8.4 * ic_en / max(yazi_eni(metin, 8.4), 1e-6)))
        sf.yazi(X(ex), Y(ey) - 4.6 * pt / 8.4, metin, pt, ARIAL, renk=GRI_YAZI, ha="center")
        sf.yazi(X(ex), Y(ey) + 5.4 * pt / 8.4, f"{b['alan_m2']:.0f} m²", pt + 0.2, ARIAL, renk=GRI_YAZI, ha="center")
        etiket[ad] = round(pt, 2); etiket_yeri[ad] = [round(ex, 1), round(ey, 1)]
        for eks, sabit, lo, hi in b.get("_acik", []):      # açık mahal (veranda) kenarı: kırmızı kesik çizgi
            if eks == "x":
                sf.cizgi(X(lo), Y(sabit), X(hi), Y(sabit), KIRMIZI, 0.9, ls=(0, (4, 3)), z=4)
            else:
                sf.cizgi(X(sabit), Y(lo), X(sabit), Y(hi), KIRMIZI, 0.9, ls=(0, (4, 3)), z=4)
    # ölçü zincirleri: genel ölçü dışta (dış yüzden dış yüze); o cepheye ulaşan duvarlar içte (dış duvarda dış yüz, iç duvarda aks).
    # Noktalar mühendis planıyla aynı (`ciz_genel.zincirler`); parçalar tam sayıya yuvarlanır, toplam genel ölçüyle aynı kalır (tam_bol).
    from . import ciz_genel
    zin = ciz_genel.zincirler(y)
    esle = {"arka": "ust", "on": "alt", "sol": "sol", "sag": "sag"}
    ic_, dis_ = 16.0, 32.0
    ek = {"arka": 0.0, "sol": 0.0, "on": 8.0, "sag": 8.0}
    kayit = {}; notlar: list[dict] = []
    _deger = (sablon_kurallari().get("zincir_en_kisa_parca_cm") or {}).get("deger")
    en_kisa = 15.0 if _deger is None else float(_deger)       # anahtar yoksa 15; 0 verilirse birleştirme kapanır
    for ad, yon in (("arka", "x"), ("on", "x"), ("sol", "y"), ("sag", "y")):
        uclar = (bx0, bx1) if yon == "x" else (by0, by1)
        nk, katilan = _birlestir(list(zin.get(esle[ad], [])) + list(uclar), uclar, en_kisa)
        for k in katilan:                                        # mühendise: komşusuna katılan kısa parça, zincir başından konumu (cm)
            notlar.append({"zincir": ad, **k, "not": f"{en_kisa:g} cm ve daha kısa parça komşusuna katıldı; ölçüyü kontrol edin (mühendis planında tam zincir)"})
        genel = yarim_yukari(W if yon == "x" else H)             # genel ölçü ve parçaların toplamı aynı sayı (şablon kuralı)
        parca = tam_bol([b - a for a, b in zip(nk, nk[1:])], genel); kayit[ad] = parca
        # dar parçanın yazısı komşusuna binmesin: sığmayan yazı bir sıra **içeri** (plana doğru) alınır, dönüşümlü. Dışarı alınınca genel
        # ölçünün sayısına ve çizgisine biniyordu (KT-02 "22 ⟂ 1170", Ç8201 "30 ⟂ 750"; Lokman 13.10.2026). İçeri sıra: yazı zincir
        # çizgisinin plan tarafında, dış yüzden ≈ 7–9 pt uzakta; o şeritte başka yazı yok.
        dar = [yazi_eni(str(v), 10.7, ARIAL) > s * (b - a) - 2 for (a, b), v in zip(zip(nk, nk[1:]), parca)]
        kaydir = []; son = 0
        for i, d in enumerate(dar):
            son = (son + 1) if (d and i and dar[i - 1]) else (1 if d else 0)
            kaydir.append((son % 2) if d else 0)
        # şablon koordinatında (y aşağı) sayı normalde: on → çizginin üstünde (içeri), arka → üstünde (dışarı), sol → solunda (dışarı),
        # sag → solunda (içeri). İçeri sıra: on −9.5, sag −9.5 (aynı yönde bir sıra daha), arka +14.4, sol +14.8 (çizginin öbür yanına)
        ic_kaydir = {"on": -9.5, "sag": -9.5, "arka": 14.4, "sol": 14.8}[ad]
        kaydir = [ic_kaydir * k for k in kaydir]
        if yon == "x":
            yy = Y(by1) - ic_ if ad == "arka" else Y(by0) + ic_ + ek[ad]
            yg = Y(by1) - dis_ if ad == "arka" else Y(by0) + dis_ + ek[ad]
            if len(nk) > 2:
                for (a, b), v, k_ in zip(zip(nk, nk[1:]), parca, kaydir):
                    sf.olcu(X(a), yy, X(b), yy, str(v), "ust", kaydir=k_)
            else:
                yg = yy
            sf.olcu(X(bx0), yg, X(bx1), yg, str(genel), "ust")
        else:
            xx = X(bx0) - ic_ if ad == "sol" else X(bx1) + ic_ + ek[ad]
            xg = X(bx0) - dis_ if ad == "sol" else X(bx1) + dis_ + ek[ad]
            if len(nk) > 2:
                for (a, b), v, k_ in zip(zip(nk, nk[1:]), parca, kaydir):
                    sf.olcu(xx, Y(b), xx, Y(a), str(v), "sol", kaydir=k_)
            else:
                xg = xx
            sf.olcu(xg, Y(by1), xg, Y(by0), str(genel), "sol")
    return kayit, etiket, notlar, etiket_yeri


# ----------------------------------------------------------------------------- görünüşler (sahne izdüşümünden)
DUVAR_GIBI = ("duvar", "korkuluk", "kalkan", "kolon")


def tas_serit(sf: Sayfa, P, u0: float, u1: float):
    """Subasman: gri şerit ve taş deseni. P(u, z) → sayfa noktası (z: 0 zemin, −SUBASMAN alt)."""
    sf.cokgen([P(u0, 0), P(u1, 0), P(u1, -SUBASMAN), P(u0, -SUBASMAN)], fc=GRI_YAZI, ec="black", lw=0.72, z=3)
    adim = SUBASMAN * 0.9; n = max(1, int((u1 - u0) / adim))
    for i in range(n):
        uc = u0 + (i + 0.5) * (u1 - u0) / n
        r = SUBASMAN * (0.34 if i % 2 else 0.42); zc = -SUBASMAN / 2 + (SUBASMAN * 0.08 if i % 3 == 0 else -SUBASMAN * 0.06)
        altigen = [P(uc + r * math.cos(math.radians(60 * k_ + 15 * (i % 4))), zc + r * math.sin(math.radians(60 * k_ + 15 * (i % 4)))) for k_ in range(6)]
        sf.cokgen(altigen, fc="none", ec=GRI, lw=0.5, z=4)


def pencere_gorunus(sf: Sayfa, P, u0, u1, z0, z1, en):
    def dort(ua, za, ub, zb, **kw):
        return sf.cokgen([P(ua, za), P(ub, za), P(ub, zb), P(ua, zb)], **kw)
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


def kapi_gorunus(sf: Sayfa, P, u0, u1, z0, z1):
    def dort(ua, za, ub, zb, **kw):
        return sf.cokgen([P(ua, za), P(ub, za), P(ub, zb), P(ua, zb)], **kw)
    dort(u0 - 3, z0, u1 + 3, z1 + 3, fc=GRI_YAZI, ec="black", lw=0.8, z=5)
    dort(u0, z0, u1, z1, fc=KAHVE, ec="black", lw=0.6, z=6)
    for i in range(1, 16):
        (xa, ya), (xb, yb) = P(u0 + 2, z0 + (z1 - z0) * i / 16), P(u1 - 2, z0 + (z1 - z0) * i / 16)
        sf.cizgi(xa, ya, xb, yb, "black", 0.45, z=7)
    dort(u0 + (u1 - u0) * 0.28, z0 + 12, u0 + (u1 - u0) * 0.36, z1 - 6, fc=GRI_YAZI, ec="black", lw=0.5, z=8)


def gorunus_ciz(sf: Sayfa, P, S: list[dict], taraf: str, renk: str, u_kaydir: float = 0.0) -> tuple[float, float, float]:
    """Bir cepheyi sahne izdüşümünden çizer. P(u, z) → sayfa noktası (u: cephe boyunca cm, u_kaydir çıkarılmış; z: kot cm).
    Dönen: (u_min, u_max, tepe) cm."""
    from . import sahne as sahne_m
    yz = sahne_m.izdusum(S, taraf)
    if not yz:
        return 0.0, 0.0, 0.0
    k2 = lambda s: [(u - u_kaydir, z) for u, z in s["k2"]]
    i = 0
    while i < len(yz):
        s = yz[i]
        if s["tur"] == "gecit":
            i += 1
            continue
        if s["tur"] in DUVAR_GIBI:
            grup = [s]; j = i + 1
            while j < len(yz) and (yz[j]["tur"] in DUVAR_GIBI or yz[j]["tur"] == "gecit") and abs(yz[j]["derinlik"] - s["derinlik"]) < 0.6:
                if yz[j]["tur"] != "gecit":
                    grup.append(yz[j])
                j += 1
            g = unary_union([SPolygon(k2(x)).buffer(0.01, join_style=2) for x in grup]).buffer(-0.01, join_style=2)
            delik = [SPolygon(k2(x)) for x in yz if x["tur"] == "gecit" and abs(x["derinlik"] - s["derinlik"]) < 1.0]
            if delik:
                g = g.difference(unary_union(delik))
            for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
                if p.geom_type != "Polygon" or p.area <= 1:
                    continue
                nok, kod = [], []
                for halka in [p.exterior] + list(p.interiors):
                    pts = [P(u, z) for u, z in halka.coords]
                    nok += [(x, sf.y(yy)) for x, yy in pts]
                    kod += [MplPath.MOVETO] + [MplPath.LINETO] * (len(pts) - 2) + [MplPath.CLOSEPOLY]
                sf.ax.add_patch(PathPatch(MplPath(nok, kod), fc="white", ec="black", lw=0.72, zorder=3, joinstyle="miter"))
            i = j
            continue
        pts = k2(s)
        if s["tur"] == "pencere":
            us = [u for u, _ in pts]; zs = [z for _, z in pts]
            pencere_gorunus(sf, P, min(us), max(us), min(zs), max(zs), s.get("en", 0))
        elif s["tur"] == "kapi":
            us = [u for u, _ in pts]; zs = [z for _, z in pts]
            kapi_gorunus(sf, P, min(us), max(us), min(zs), max(zs))
        elif s["tur"] == "cati":
            yama = sf.cokgen([P(u, z) for u, z in pts], fc=renk, ec="black", lw=0.72, z=4)
            us = [u for u, _ in pts]; zs = [z for _, z in pts]
            n = int((max(us) - min(us)) / 20)
            for k_ in range(1, n):                                 # trapez sac: beyaz ince çizgiler (yüzeye kırpılı)
                u = min(us) + k_ * (max(us) - min(us)) / n
                (xa, ya), (xb, yb) = P(u, min(zs)), P(u, max(zs))
                sf.cizgi(xa, ya, xb, yb, "white", 0.55, z=5, clip=yama)
        elif s["tur"] in ("alin", "kiris"):
            sf.cokgen([P(u, z) for u, z in pts], fc=GRI_YAZI, ec="black", lw=0.72, z=4 if s["tur"] == "alin" else 3)
        elif s["tur"] == "baca":
            # Baca, önündeki (daha yakın: `derinlik` küçük) bir çatı düzleminin arkasında kalıyorsa çatının altına çizilir; eğimin
            # üstünde, düzlemin önündeyse (KT-01 sol yan: baca batı eğiminde, çizim setindeki SOL GÖRÜNÜŞ ile aynı) üstte kalır.
            # Sol yan görünüş gözden geçirildi (rehber, 12.10.2026): KT-01'de çizim setiyle tutarlı; bu sıralama yalnız arkada kalan baca için.
            bp = SPolygon(pts)
            onde_cati = any(x["tur"] == "cati" and x["derinlik"] < s["derinlik"] and SPolygon(k2(x)).intersects(bp) for x in yz)
            sf.cokgen([P(u, z) for u, z in pts], fc="white", ec="black", lw=0.6, z=3.5 if onde_cati else 5)
        else:
            sf.cokgen([P(u, z) for u, z in pts], fc="white", ec="black", lw=0.6, z=3)
        i += 1
    us = [u for s in yz for u, _ in k2(s)]; zs = [z for s in yz for _, z in k2(s)]
    duvar_us = [u for s in yz if s["tur"] in ("duvar", "korkuluk", "kolon") for u, _ in k2(s)] or us
    tas_serit(sf, P, min(duvar_us) - 6.0, max(duvar_us) + 6.0)
    return min(us), max(us), max(zs)


# ----------------------------------------------------------------------------- pafta
def pafta_pdf(t: dict, hedef: Path, kod: str, is_emri_no: str | None = None, revizyon: int = 1, set_yolu: Path | None = None,
              yontem: str | None = None, bilgi: dict | None = None) -> dict:
    """Şablon paftası: `<kod>_pafta.pdf` (2 sayfa) ve `<kod>_pafta_sablon.png`. `bilgi`: antet, özellik ve özel istek alanları (zarftan)."""
    from . import cati_genel, ciz_genel, girdi_genel, kural, sahne as sahne_m, yapi
    from .bayi_gorseli import musteri_projesi
    import matplotlib.pyplot as plt
    fontlari_hazirla()
    bilgi = dict(bilgi or {}); bilgi.setdefault("is_emri_no", is_emri_no); bilgi.setdefault("revizyon", revizyon)
    t = json.loads(json.dumps(t))
    if yontem:
        t["cati"]["yontem"] = yontem
    with kural.secili(set_yolu):
        kur = kural.oku()
    y = yapi.kur(t); c = cati_genel.cati_kur(t["cati"], kur); S = sahne_m.sahne_kur(y, c)
    oturum_m2 = girdi_genel.metraj(y, c, kur)["oturum_m2"]    # brüt oturum (dış duvar dış yüzleri; veranda ve sundurma dahil) = listedeki bina_m2 (D-08 K-A1); sınır kutusu değil
    bx0, by0, bx1, by1 = dis_yuz_sinirlari(y)                 # dış ölçüler dış yüzden (mühendis planı ve görünüşlerle aynı: Ç8801 1024 × 860)
    W, H = bx1 - bx0, by1 - by0
    H0 = float(t["kat_yuksekligi"]); sac = float(t["cati"].get("sacak", 30))
    tepe = max((z for s in S if s["tur"] in ("cati", "alin", "kalkan", "baca") for _, _, z in s["kose"]), default=H0)
    oz = ozellikler(t, y, c, kur, bilgi)
    renk = CATI_RENGI.get(str(oz.get("Çatı Kaplama Rengi", "")).strip().lower(), "#7D8187")
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    pdf = hedef / f"{kod}_pafta.pdf"; png = hedef / f"{kod}_pafta_sablon.png"

    fig1 = plt.figure(figsize=(EN / 72, BOY / 72))
    sf = Sayfa(fig1)
    cerceveler(sf, t, oz, bilgi, oturum_m2)
    # yerleşim: [sol yan görünüş] [ölçü] [plan] [ölçü]; planın altında ön görünüş. Ölçek ana çerçeveye sığacak en büyük değer.
    yan_yuk = SUBASMAN + tepe
    olcu_pay = 46.0; bosluk = 12.0; baslik_pay = 18.0
    s_yatay = (ANA[2] - ANA[0] - 2 * 10 - baslik_pay - bosluk - 2 * olcu_pay) / (yan_yuk + W + 2 * sac)
    s_dusey = (ANA[3] - ANA[1] - 8 - 2 * olcu_pay - bosluk - baslik_pay - 8) / (H + yan_yuk)
    s = min(s_yatay, s_dusey, 0.2975)                      # şablondaki ölçekten (0,2975 pt/cm) büyük olmaz
    toplam_en = baslik_pay + yan_yuk * s + bosluk + olcu_pay + W * s + olcu_pay
    xb = ANA[0] + (ANA[2] - ANA[0] - toplam_en) / 2
    yan_x0 = xb + baslik_pay + SUBASMAN * s                # sol yan görünüşte zemin çizgisinin x'i
    px0 = yan_x0 + tepe * s + bosluk + olcu_pay            # planın sol dış yüzü
    toplam_boy = olcu_pay + H * s + olcu_pay + bosluk + yan_yuk * s + baslik_pay
    yb = ANA[1] + (ANA[3] - ANA[1] - toplam_boy) / 2
    py_ust = yb + olcu_pay                                 # planın arka (üst) dış yüzü
    py0 = py_ust + H * s                                   # planın ön (alt) dış yüzü
    on_zemin = py0 + olcu_pay + bosluk + tepe * s          # ön görünüşte zemin çizgisinin y'si
    zincirler, etiket_pt, kontrol_notlari, etiket_yeri = plan_ciz(sf, y, t, px0, py0, s)
    # ön görünüş: planla aynı x hizasında (izdüşümde u = x)
    P_on = lambda u, z: (px0 + s * u, on_zemin - s * z)
    u0, u1, _ = gorunus_ciz(sf, P_on, S, "on", renk, u_kaydir=bx0)
    xo = px0 + s * (u1 + 9 / s)
    sf.olcu(xo + 9.0, on_zemin - s * H0, xo + 9.0, on_zemin, tr(H0), "sol")
    sf.yazi(px0 + s * W, on_zemin + SUBASMAN * s + 9.5, "ÖN GÖRÜNÜŞ", 8.0, renk=GRI_YAZI, ha="right")
    sf.cizgi(px0 + s * W - 52.0, on_zemin + SUBASMAN * s + 15.0, px0 + s * W, on_zemin + SUBASMAN * s + 15.0, GRI_YAZI, 0.8)
    # sol yan görünüş: 90° döndürülmüş (zemin solda, çatı plana doğru); düşeyde planla aynı hizada (izdüşümde u = −y: arkadan öne)
    P_sol = lambda u, z: (yan_x0 + s * z, py_ust + s * u)
    gorunus_ciz(sf, P_sol, S, "sol", renk, u_kaydir=-by1)
    sf.yazi(yan_x0 - SUBASMAN * s - 7.5, py0, "SOL YAN GÖRÜNÜŞ", 8.2, renk=GRI_YAZI, ha="center", va="bottom", rot=90)
    sf.cizgi(yan_x0 - SUBASMAN * s - 2.6, py0 - 76.0, yan_x0 - SUBASMAN * s - 2.6, py0, GRI_YAZI, 0.8)

    # sayfa 2: dört görünüş ve çatı planı (genel motorun kendi çizimleri)
    fig2 = plt.figure(figsize=(EN / 72, BOY / 72))
    from matplotlib.gridspec import GridSpec
    gs = GridSpec(2, 3, figure=fig2, left=0.03, right=0.985, top=0.9, bottom=0.04, hspace=0.18, wspace=0.08)
    inis, _ = ciz_genel.inis_kurali(c, kur, t["cati"].get("sacak", 30))
    # başlık kısa (uzun başlık dar sütundan sayfa dışına taşıyordu), açıklama sayfanın altında; üst üste binen eğim yazıları ayrılır (Lokman, 12.10)
    ciz_genel.cati_plani_eksen(fig2.add_subplot(gs[:, 0]), y, c, inis, baslik="ÇATI PLANI", yazi_ayir=True)
    fig2.text(0.03, 0.012, "Çatı planı: eğim okları ve yüzdeleri · sarı nokta: dere inişi" + (f" ({len(inis)} adet)" if inis else "") +
              " · turuncu: duvara dayanan kenar · beyaz kesik çizgi: duvar dış yüzü · ölçüler cm", fontsize=7.2, ha="left", va="bottom", color="#333")
    for ax, taraf in zip((fig2.add_subplot(gs[0, 1]), fig2.add_subplot(gs[0, 2]), fig2.add_subplot(gs[1, 1]), fig2.add_subplot(gs[1, 2])), ("on", "arka", "sol", "sag")):
        ciz_genel.gorunus_eksen(ax, S, taraf, t["kat_yuksekligi"], sigdir=True)      # küçük panelde iki düşey ölçü şeridi ölçeğe göre açılır (13.10)
    no = bilgi.get("is_emri_no") or t["kod"]
    ad = f"{t['kod']} · {oturum_m2:.0f} m²" if musteri_projesi(t) else f"{t['kod']} · {t['ad']}"     # müşteri projeleri bayiye adsız (D-08)
    fig2.suptitle(f"{ad}   —   {no} r{int(bilgi.get('revizyon') or 1):02d} · görünüşler ve çatı planı · TASLAK", fontsize=10.5, weight="bold", x=0.03, ha="left", y=0.965)
    with PdfPages(pdf, metadata={"Title": f"{t['kod']} plan paftası", "Creator": "Portman", "Producer": "Portman", "CreationDate": None, "ModDate": None}) as pp:
        pp.savefig(fig1); pp.savefig(fig2)
    fig1.savefig(png, dpi=200)
    plt.close(fig1); plt.close(fig2)
    ozet = {"kod": t["kod"], "sayfa_pt": [EN, BOY], "olcek_pt_cm": round(s, 4), "olcek_1e": round(1 / (s / 72 * 2.54)), "zincirler_cm": zincirler,
            "mahal_yazi_pt": etiket_pt, "mahal_etiket_cm": etiket_yeri, "dis_olcu_cm": [round(W, 1), round(H, 1)], "oturum_m2": round(oturum_m2, 2),
            "tepe_cm": round(tepe, 1), "ozellikler": oz,
            "kontrol_notlari": kontrol_notlari,                 # mühendise: komşusuna katılan kısa parçalar (Lokman 12.10.2026; 8b'de gösterilir)
            "dosyalar": [pdf.name, png.name]}
    (hedef / f"{kod}_pafta_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return ozet


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path); ap.add_argument("cikti", type=Path)
    ap.add_argument("--yontem", choices=("panel", "omega_asik")); ap.add_argument("--set", type=Path, default=None)
    ap.add_argument("--is-emri-no", default=None); ap.add_argument("--revizyon", type=int, default=1)
    a = ap.parse_args()
    from .uret import matplotlib_sabitle, kod_govde
    matplotlib_sabitle()
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    o = pafta_pdf(t, a.cikti, kod_govde(t), is_emri_no=a.is_emri_no, revizyon=a.revizyon, set_yolu=a.set, yontem=a.yontem)
    print("yazıldı:", ", ".join(o["dosyalar"]), f"· ölçek 1:{o['olcek_1e']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
