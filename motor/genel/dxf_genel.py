#!/usr/bin/env python3
"""Genel motorun düzenlenebilir DXF'i (İE-08; D-11, Lokman 13 Ekim 2026): plan ve dört görünüş tek dosyada, AutoCAD'de açılır.

Çizimler `ciz_genel` ile aynı geometriden (`yapi.kur`, `cati_genel.cati_kur`, `sahne.sahne_kur`):
  plan       duvar kesitleri kaplamalarıyla tek gövde (açıklıklarda kesik), pencere simgesi, kapı kanadı ve açılım yayı, veranda kirişi izi,
             mahal adı ve alanı, pencere etiketi (en/yük), giriş, dört yanda tam ölçü zinciri (dış yüzler ve iç duvar aksları; bayi
             paftasındaki 15 cm birleştirmesi yok, mühendis planı gibi)
  görünüşler ön, arka, sol, sağ; yüzeyler yakından uzağa örtülerek çizilir (gizli çizgi yok; aynı düzlemdeki duvar yüzleri tek gövde,
             `ciz_genel.gorunus_eksen` ile aynı kural), zemin çizgisi, genişlik, duvar ve tepe yüksekliği
ezdxf, R2018, birim cm ($INSUNITS 5); ölçüler DIMENSION varlığı (düzenlenebilir). Katmanlar `kurallar/cizim/duzenlenebilir.json › dxf`
(DUVAR, ACIKLIK, OLCU, YAZI) ve `dxf_cati_katmani` (CATI; varsayım). Kural dosyası ya da `dxf` anahtarı yoksa `uret` DXF üretmez (eski
davranış). Dosya yazıldıktan sonra yeniden açılır ve denetlenir (`audit`); denetim hatası varsa çıkış kodu 1 (uret uyarı yazar, iş düşmez:
DXF bayiye gitmez). İçerik izi `testler/referans/parmak_izi.dxf_ozet` (tutamaç, zaman ve rastgele kimlik dışarıda).

DXF çıktıdır, kaynak değil (D-11): dosyadaki düzeltme tanıma (`modeller/*.json`, D-07) ya da kural kitabına işlenir, DXF yeniden üretilir.

    python -m motor.genel.dxf_genel modeller/C8801.json --cikti <klasör> [--yontem panel|omega_asik]
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import argparse
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import linemerge, unary_union

KOK = Path(__file__).resolve().parents[2]
KURAL_DOSYASI = KOK / "kurallar" / "cizim" / "duzenlenebilir.json"
KATMAN_VARSAYILAN = {"duvar": "DUVAR", "aciklik": "ACIKLIK", "olcu": "OLCU", "yazi": "YAZI"}
KATMAN_BICIM = {"duvar": (7, 35), "aciklik": (4, 18), "olcu": (3, 13), "yazi": (2, 18), "cati": (1, 25)}   # ACI rengi, çizgi kalınlığı (1/100 mm)
YAZI_STILI, YAZI_TIPI = "PORTMAN", "arial.ttf"           # AutoCAD'de Türkçe harfler (ğ, ş, ı, İ); yoksa AutoCAD benzeriyle değiştirir
DUVAR_GIBI = ("duvar", "korkuluk", "kalkan")
GORUNUS_KATMANI = {"duvar": "duvar", "korkuluk": "duvar", "kalkan": "duvar", "kolon": "duvar", "kiris": "duvar", "baca": "duvar",
                   "pencere": "aciklik", "kapi": "aciklik", "cati": "cati", "alin": "cati"}
H_MAHAL, H_ALAN, H_ETIKET, H_BASLIK, H_NOT = 15.0, 12.0, 10.0, 25.0, 11.0      # yazı yükseklikleri (cm; 1/50 çıktıda 3 / 2,4 / 2 / 5 / 2,2 mm)
EN_KISA_CIZGI = 0.5                                                            # örtmeden artan bundan kısa parça çizilmez (cm)


def kurallar() -> dict:
    """`kurallar/cizim/duzenlenebilir.json`; yoksa boş (DXF üretilmez, eski davranış)."""
    try:
        return json.loads(KURAL_DOSYASI.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def katmanlar(kd: dict) -> dict:
    """Katman anahtarı → katman adı (duvar, aciklik, olcu, yazi, cati)."""
    d = (kd.get("dxf") or {}).get("deger") or {}
    k = {**KATMAN_VARSAYILAN, **(d.get("katmanlar") or {})}
    k["cati"] = (kd.get("dxf_cati_katmani") or {}).get("deger") or k["duvar"]
    return k


def dosya_adi(kd: dict, kod: str) -> str:
    return str(((kd.get("dxf") or {}).get("deger") or {}).get("dosya") or "{kod}_cizim.dxf").format(kod=kod)


def _belge(K: dict):
    import ezdxf
    from ezdxf import units
    doc = ezdxf.new("R2018", setup=True)
    doc.units = units.CM                                        # $INSUNITS 5
    doc.header["$MEASUREMENT"] = 1                              # metrik
    doc.styles.add(YAZI_STILI, font=YAZI_TIPI)
    for anahtar in ("duvar", "aciklik", "olcu", "yazi", "cati"):
        ad = K[anahtar]
        if ad not in doc.layers:
            renk, kalinlik = KATMAN_BICIM[anahtar]
            doc.layers.add(ad, color=renk, lineweight=kalinlik)
    ds = doc.dimstyles.duplicate_entry("EZDXF", "PORTMAN")
    ds.dxf.dimtxt = 12; ds.dxf.dimasz = 8; ds.dxf.dimexe = 5; ds.dxf.dimexo = 4; ds.dxf.dimtad = 1; ds.dxf.dimgap = 3
    ds.dxf.dimdec = 1; ds.dxf.dimzin = 8; ds.dxf.dimdsep = ord(","); ds.dxf.dimtxsty = YAZI_STILI; ds.dxf.dimblk = "ARCHTICK"
    ds.dxf.dimlfac = 1.0; ds.dxf.dimtih = 0; ds.dxf.dimtoh = 0
    return doc


class _Cizer:
    """Model alanına katman anahtarıyla yazar; (dx, dy) ötelemesi görünüşleri planın altına yerleştirir."""

    def __init__(self, msp, K: dict):
        self.msp, self.K = msp, K

    @staticmethod
    def _n(p, dx, dy):
        return (round(p[0] + dx, 3), round(p[1] + dy, 3))

    def cizgi(self, pts, katman: str, kapali: bool = False, dx: float = 0.0, dy: float = 0.0, **ek):
        pts = [self._n(p, dx, dy) for p in pts]
        if len(pts) >= 2:
            self.msp.add_lwpolyline(pts, close=kapali, dxfattribs={"layer": self.K[katman], **ek})

    def geo(self, g, katman: str, dx: float = 0.0, dy: float = 0.0, **ek):
        """Shapely geometrisi: çokgen → kapalı çizgiler (dış ve delikler); çizgi → birleştirilmiş açık çizgiler; noktalar atlanır."""
        if g is None or g.is_empty:
            return
        t = g.geom_type
        if t == "Polygon":
            self.cizgi(list(g.exterior.coords)[:-1], katman, True, dx, dy, **ek)
            for h in g.interiors:
                self.cizgi(list(h.coords)[:-1], katman, True, dx, dy, **ek)
        elif t in ("LineString", "LinearRing"):
            if g.length >= EN_KISA_CIZGI:
                self.cizgi(list(g.coords), katman, False, dx, dy, **ek)
        elif t == "MultiLineString":
            m = linemerge(g)
            for p in (m.geoms if m.geom_type == "MultiLineString" else [m]):
                self.geo(p, katman, dx, dy, **ek)
        elif hasattr(g, "geoms"):
            for p in g.geoms:
                self.geo(p, katman, dx, dy, **ek)

    def yazi(self, s: str, xy, h: float, katman: str = "yazi", hiza: str = "MIDDLE_CENTER", aci: float = 0.0, dx: float = 0.0, dy: float = 0.0):
        from ezdxf.enums import TextEntityAlignment
        self.msp.add_text(s, dxfattribs={"height": h, "layer": self.K[katman], "style": YAZI_STILI, "rotation": aci}).set_placement(
            self._n(xy, dx, dy), align=getattr(TextEntityAlignment, hiza))

    def olcu(self, p1, p2, taban, dikey: bool = False, dx: float = 0.0, dy: float = 0.0, ondalik: int | None = None):
        """Doğrusal ölçü (DIMENSION). `ondalik`: yalnız bu ölçüde ondalık hane (görünüşte tepe yüksekliği çizim setindeki gibi tam sayı)."""
        p1, p2, taban = self._n(p1, dx, dy), self._n(p2, dx, dy), self._n(taban, dx, dy)
        if (abs(p2[1] - p1[1]) if dikey else abs(p2[0] - p1[0])) < 0.05:
            return
        d = self.msp.add_linear_dim(base=taban, p1=p1, p2=p2, angle=90 if dikey else 0, dimstyle="PORTMAN", dxfattribs={"layer": self.K["olcu"]},
                                    override={"dimdec": ondalik} if ondalik is not None else None)
        d.render()

    def yay(self, merkez, r: float, a0: float, a1: float, katman: str = "aciklik"):
        self.msp.add_arc(self._n(merkez, 0, 0), r, a0, a1, dxfattribs={"layer": self.K[katman]})


# ───────────────────────── plan ─────────────────────────
def plan_ciz(C: _Cizer, y: dict, baslik: list[str]) -> tuple[float, float, float, float]:
    from .ciz_genel import aciklik_kutusu, dis_hat, sade, tr, zincirler
    t = y["tanim"]
    kap = t.get("yuz_kaplamalari") or {}
    pay = max((kap.get(k) or {}).get("kalinlik", 0.0) for k in ("dis", "ic")) + 0.05
    kutular = {a["ad"]: aciklik_kutusu(y, a, pay=pay) for a in y["acikliklar"]}
    delik = unary_union(list(kutular.values())) if kutular else None
    kesit = lambda siniflar: unary_union([unary_union([d["geo"]] + d.get("_serit", [])) for d in y["duvarlar"] if d["sinif"] in siniflar])
    govde = kesit(("dis", "ic", "ek"))                         # dış, iç ve ek duvarlar kaplamalarıyla tek gövde: birleşimde iç çizgi yok
    if delik is not None:
        govde = govde.difference(delik)
    C.geo(govde, "duvar")
    for sinif in ("korkuluk", "kolon", "baca"):
        g = kesit((sinif,))
        if g.is_empty:
            continue
        C.geo(g.difference(delik) if (sinif == "korkuluk" and delik is not None) else g, "duvar")
        if sinif == "baca":
            for d in y["duvarlar"]:
                if d["sinif"] == "baca":
                    x0, y0, x1, y1 = d["kutu"]
                    C.cizgi([(x0, y0), (x1, y1)], "duvar"); C.cizgi([(x0, y1), (x1, y0)], "duvar")
    for b in y["bolgeler"].values():                            # veranda ve sundurma döşeme kenarı (duvara değen kısmı çizilmez)
        if b["sinif"] == "veranda":
            for p in (b["net"].geoms if b["net"].geom_type == "MultiPolygon" else [b["net"]]):
                C.geo(LineString(list(p.exterior.coords)).difference(govde.buffer(0.05)), "duvar", lineweight=13)
    for kr in t.get("kirisler", []):                            # veranda kirişleri: eksende kesik çizgi
        x0, y0, x1, y1 = kr["kutu"]
        yatay = (x1 - x0) >= (y1 - y0)
        for lo, hi in kr["acik"]:
            C.cizgi([(lo, (y0 + y1) / 2), (hi, (y0 + y1) / 2)] if yatay else [((x0 + x1) / 2, lo), ((x0 + x1) / 2, hi)], "duvar", linetype="DASHED")
    # açıklıklar
    for a in y["acikliklar"]:
        d = y["adli"][a["duvar"]]
        x1, y1, x2, y2 = kutular[a["ad"]].bounds
        if a["tur"] == "pencere":
            C.cizgi([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], "aciklik", True)
            if d["yon"] == "x":                                 # cam: duvar ekseninde iki çizgi
                m = (d["kutu"][1] + d["kutu"][3]) / 2
                for e in (-1.5, 1.5):
                    C.cizgi([(x1, m + e), (x2, m + e)], "aciklik")
            else:
                m = (d["kutu"][0] + d["kutu"][2]) / 2
                for e in (-1.5, 1.5):
                    C.cizgi([(m + e, y1), (m + e, y2)], "aciklik")
            et = a.get("etiket") or f"{a['en']}/{a['yuk']}"
            yuz = next((f for f in y["yuzler"] if f["duvar"] == d["ad"] and f["uzun"] and f["bolge_sinifi"] in ("dis", "veranda")), None)
            kn = yuz["kenar"] if yuz else ("alt" if d["yon"] == "x" else "sol")
            if kn == "alt":
                C.yazi(et, ((x1 + x2) / 2, y1 - 9), H_ETIKET, hiza="TOP_CENTER")
            elif kn == "ust":
                C.yazi(et, ((x1 + x2) / 2, y2 + 9), H_ETIKET, hiza="BOTTOM_CENTER")
            elif kn == "sag":                                   # 90° döndürülmüş yazının "üstü" −x'e bakar: sağda üst kenar duvara, gövde dışarı
                C.yazi(et, (x2 + 9, (y1 + y2) / 2), H_ETIKET, hiza="TOP_CENTER", aci=90.0)
            else:                                               # solda alt kenar (taban çizgisi) duvara, gövde dışarı
                C.yazi(et, (x1 - 9, (y1 + y2) / 2), H_ETIKET, hiza="BOTTOM_CENTER", aci=90.0)
        elif a["tur"] in ("ic_kapi", "dis_kapi"):               # kanat (açık konumda) ve açılım yayı (`ciz_genel.kapi_ciz` ile aynı)
            kx0, ky0, kx1, ky1 = d["kutu"]
            r = a["en"]
            mh = a["a0"] if a.get("mentese", "bas") == "bas" else a["a1"]
            yon = 1 if a.get("acilim", "ust") in ("ust", "sag") else -1
            if d["yon"] == "x":
                hx, hy = mh, (ky1 if yon == 1 else ky0)
                C.cizgi([(hx, hy), (hx, hy + yon * r)], "aciklik")
                kapali, acik = (0 if mh == a["a0"] else 180), (90 if yon == 1 else 270)
            else:
                hx, hy = (kx1 if yon == 1 else kx0), mh
                C.cizgi([(hx, hy), (hx + yon * r, hy)], "aciklik")
                kapali, acik = (90 if mh == a["a0"] else 270), (0 if yon == 1 else 180)
            t1, t2 = sorted([kapali % 360, acik % 360])
            if t2 - t1 > 180:
                t1, t2 = t2, t1 + 360
            C.yay((hx, hy), r, float(t1), float(t2 % 360 if t2 != 360 else 360))
    # mahal adı ve alanı
    for b in y["bolgeler"].values():
        if b["sinif"] == "dis":
            continue
        c = b["net"].representative_point()
        cx, cy = b.get("etiket_yeri", (c.x, c.y))
        C.yazi(b["ad"].upper(), (cx, cy + 14), H_MAHAL)
        C.yazi(f"{tr(b['alan_m2'])} m²", (cx, cy - 14), H_ALAN)
    hat = dis_hat(y)
    bx0, by0 = min(p[0] for h in hat for p in h), min(p[1] for h in hat for p in h)
    bx1, by1 = max(p[0] for h in hat for p in h), max(p[1] for h in hat for p in h)
    for a in y["acikliklar"]:                                    # giriş oku
        if a["tur"] in ("dis_kapi", "gecit") and a.get("giris"):
            d = y["adli"][a["duvar"]]
            if d["yon"] == "x":
                mx, ky0 = (a["a0"] + a["a1"]) / 2, d["kutu"][1]
                C.cizgi([(mx, ky0 - 36), (mx, ky0 - 6)], "yazi"); C.cizgi([(mx - 4, ky0 - 14), (mx, ky0 - 6), (mx + 4, ky0 - 14)], "yazi")
                C.yazi("GİRİŞ", (mx, ky0 - 40), H_ETIKET, hiza="TOP_CENTER")
    # ölçü zincirleri: dış yüzler ve iç duvar aksları (tam zincir)
    z = zincirler(y)
    for xa, xb in zip(z["alt"], z["alt"][1:]):
        C.olcu((xa, by0), (xb, by0), (xa, by0 - 66))
    C.olcu((bx0, by0), (bx1, by0), (bx0, by0 - 102))
    for xa, xb in zip(z["ust"], z["ust"][1:]):
        C.olcu((xa, by1), (xb, by1), (xa, by1 + 50))
    for ya, yb in zip(z["sol"], z["sol"][1:]):
        C.olcu((bx0, ya), (bx0, yb), (bx0 - 50, ya), dikey=True)
    C.olcu((bx0, by0), (bx0, by1), (bx0 - 86, by0), dikey=True)
    for ya, yb in zip(z["sag"], z["sag"][1:]):
        C.olcu((bx1, ya), (bx1, yb), (bx1 + 50, ya), dikey=True)
    ust = by0 - 150.0                                            # başlık ve not satırları: her satır kendi yüksekliği + 10 cm aralıkla
    for i, s in enumerate(baslik):
        h = H_BASLIK if i == 0 else H_NOT
        C.yazi(s, (bx0, ust), h, hiza="TOP_LEFT")
        ust -= h + 10.0
    _ = sade                                                     # (ölçü yazısını DIMENSION biçimler: dimdec 1, dimzin 8, virgül)
    return bx0 - 120, ust - 10.0, bx1 + 90, by1 + 90


# ───────────────────────── görünüşler ─────────────────────────
def _ogeler(yz: list[dict]) -> list[tuple[str, object, dict]]:
    """Uzaktan yakına çizim öğeleri: aynı düzlemdeki duvar yüzleri (duvar, korkuluk, kalkan) birleşir, geçitler delik olur
    (`ciz_genel.gorunus_eksen` ile aynı kural); öteki yüzeyler tek tek."""
    gecitler = [s for s in yz if s["tur"] == "gecit"]
    cik, i = [], 0
    while i < len(yz):
        s = yz[i]
        if s["tur"] == "gecit":
            i += 1
            continue
        if s["tur"] in DUVAR_GIBI:
            grup, j = [s], i + 1
            while j < len(yz) and (yz[j]["tur"] in DUVAR_GIBI or yz[j]["tur"] == "gecit") and abs(yz[j]["derinlik"] - s["derinlik"]) < 0.6:
                if yz[j]["tur"] != "gecit":
                    grup.append(yz[j])
                j += 1
            g = unary_union([Polygon(x["k2"]).buffer(0.01, join_style=2) for x in grup]).buffer(-0.01, join_style=2)
            delik = [Polygon(x["k2"]) for x in gecitler if abs(x["derinlik"] - s["derinlik"]) < 1.0]
            if delik:
                g = g.difference(unary_union(delik))
            cik.append(("duvar", g, s))
            i = j
            continue
        cik.append((s["tur"], Polygon(s["k2"]).buffer(0), s))
        i += 1
    return cik


def gorunus_olcusu(S: list[dict], taraf: str) -> dict:
    from .sahne import izdusum
    yz = izdusum(S, taraf)
    us = [p[0] for s in yz for p in s["k2"]]; zs = [p[1] for s in yz for p in s["k2"]]
    return {"yz": yz, "u0": min(us), "u1": max(us), "z1": max(zs)}


def gorunus_ciz(C: _Cizer, S: list[dict], taraf: str, duvar_h: float, ox: float, oy: float, g: dict | None = None) -> None:
    """Görünüş: yakından uzağa; her öğenin kenarlarından, kendinden yakın öğelerin örttüğü kısım atılır (gizli çizgi yok)."""
    from .ciz_genel import TARAF_ADI
    g = g or gorunus_olcusu(S, taraf)
    yz, umin = g["yz"], g["u0"]
    dx, dy = ox - umin, oy
    ortu = Polygon()
    for tur, geo, s in reversed(_ogeler(yz)):
        if geo.is_empty or geo.area < 0.5:
            continue
        katman = GORUNUS_KATMANI.get(tur, "duvar")
        kenar = geo.boundary
        C.geo(kenar if ortu.is_empty else kenar.difference(ortu.buffer(0.05)), katman, dx, dy)
        if tur == "pencere" and s.get("en", 0) >= 100:             # kayıt (orta kayıt) çizgisi, görünüşteki gibi
            u_ = [p[0] for p in s["k2"]]; z_ = [p[1] for p in s["k2"]]
            orta = LineString([((min(u_) + max(u_)) / 2, min(z_)), ((min(u_) + max(u_)) / 2, max(z_))])
            C.geo(orta if ortu.is_empty else orta.difference(ortu.buffer(0.05)), "aciklik", dx, dy)
        ortu = unary_union([ortu, geo])
    us = [p[0] for s in yz for p in s["k2"]]
    C.cizgi([(min(us) - 40, 0.0), (max(us) + 40, 0.0)], "duvar", dx=dx, dy=dy)               # zemin
    duvar_us = [p[0] for s in yz if s["tur"] in ("duvar", "korkuluk", "kolon") for p in s["k2"]]
    u0, u1 = min(duvar_us), max(duvar_us)
    tepe_s = max((p for s in yz if s["tur"] in ("cati", "alin", "kalkan") for p in s["k2"]), key=lambda p: p[1])
    sag = max(us)
    C.olcu((u1, 0.0), (u1, duvar_h), (sag + 30, 0.0), dikey=True, dx=dx, dy=dy)
    C.olcu((u1, 0.0), (tepe_s[0], tepe_s[1]), (sag + 66, 0.0), dikey=True, dx=dx, dy=dy, ondalik=0)         # çizim setinde tepe tam sayı (444)
    C.olcu((u0, 0.0), (u1, 0.0), (u0, -34.0), dx=dx, dy=dy)
    C.yazi(TARAF_ADI[taraf], ((min(us) + max(us)) / 2, -60.0), 20.0, hiza="TOP_CENTER", dx=dx, dy=dy)


# ───────────────────────── belge ─────────────────────────
def ciz(t: dict, kur: dict, cikti: Path, K: dict | None = None) -> dict:
    """Plan + dört görünüş → `cikti` (DXF). Dönen: {dosya, denetim_hatasi, katmanlar: {ad: varlık sayısı}, olcu}."""
    import ezdxf
    from . import cati_genel, sahne as sahne_m, yapi
    from .bayi_gorseli import musteri_projesi
    K = K or katmanlar(kurallar())
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    S = sahne_m.sahne_kur(y, c)
    doc = _belge(K)
    C = _Cizer(doc.modelspace(), K)
    ad = "" if musteri_projesi(t) else f" · {t.get('ad', '')}"            # müşteri projesi adsız (D-08)
    px0, py0, px1, _ = plan_ciz(C, y, [f"PLAN · {t['kod']}{ad}",
                                       "Ölçüler cm · TASLAK, üretim projesi değildir · DXF çıktıdır, kaynak değil: düzeltme tanıma ya da kural kitabına işlenir, yeniden üretilir (D-11)"])
    # görünüşler planın altında 2 × 2: üstte ön ve arka, altta sol ve sağ
    olc = {taraf: gorunus_olcusu(S, taraf) for taraf in ("on", "arka", "sol", "sag")}
    ara, sag_pay = 250.0, 110.0
    y_ust = py0 - 120.0
    for sira in (("on", "arka"), ("sol", "sag")):
        h = max(olc[x]["z1"] for x in sira)
        oy = y_ust - h
        ox = px0 + 120.0
        for taraf in sira:
            gorunus_ciz(C, S, taraf, t["kat_yuksekligi"], ox, oy, olc[taraf])
            ox += (olc[taraf]["u1"] - olc[taraf]["u0"]) + sag_pay + ara
        y_ust = oy - 60.0 - 22.0 - ara
    cikti = Path(cikti); cikti.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(cikti)
    d2 = ezdxf.readfile(cikti)                                   # yeniden aç ve denetle (AutoCAD'de açılabilirlik)
    a = d2.audit()
    say: dict[str, int] = {}
    for e in d2.modelspace():
        say[e.dxf.layer] = say.get(e.dxf.layer, 0) + 1
    return {"dosya": cikti.name, "denetim_hatasi": len(a.errors), "katmanlar": dict(sorted(say.items())),
            "olcu": sum(1 for e in d2.modelspace() if e.dxftype() == "DIMENSION")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--cikti", type=Path, required=True)
    ap.add_argument("--yontem", choices=("panel", "omega_asik"))
    a = ap.parse_args()
    from . import kural
    kd = kurallar()
    if not kd.get("dxf"):
        print("DXF kuralı yok (kurallar/cizim/duzenlenebilir.json › dxf): DXF üretilmedi")
        return 0
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    if a.yontem:
        t["cati"]["yontem"] = a.yontem
    kod = t["kod"].replace("Ç", "C").replace("-", "")
    oz = ciz(t, kural.oku(), a.cikti / dosya_adi(kd, kod), katmanlar(kd))
    print("yazıldı:", oz["dosya"], f"(denetim hatası {oz['denetim_hatasi']}, ölçü {oz['olcu']}, katmanlar {oz['katmanlar']})")
    return 0 if oz["denetim_hatasi"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
