#!/usr/bin/env python3
"""Genel yapı çizimi: plan, çatı planı, dört görünüş ve tek pafta (Yapı Tanımı 0.5).

`../2026-10-02_celik/ciz.py` ve `gorunus.py` ile aynı görünüm; fark, dikdörtgen olmayan planı ve çok düzlemli çatıyı çizebilmesidir.
Plan `yapi.kur()` sonucundan, çatı planı `cati_genel.cati_kur()` sonucundan, görünüşler `sahne.sahne_kur()` yüzeylerinden çizilir.

Kullanım:
    python ciz_genel.py tanim.json --cikti klasor
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Arc
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from . import cati_genel, yapi
from . import sahne as sahne_m
from . import kural as kurallar_oku

BURADA = Path(__file__).resolve().parent
KOK = BURADA.parents[1]                                  # depo kökü (BURADA = motor/genel; parents[0] = motor, parents[1] = kök)
DUVAR, DUVAR_GERI, CATI, CAM, CERCEVE, KAPI, KOLON = "#dcd7cb", "#c9c4b8", "#5d6470", "#cfe6f7", "#2a78b8", "#b08a5a", "#8f8f8f"
MAHAL_RENGI = {"yatak_odasi": "#e3ebf7", "banyo": "#dcefee", "salon": "#fdf1d6", "mutfak": "#fdf1d6", "hol": "#f3ead9", "depo": "#ece8e1"}
DUVAR_RENGI = {"dis": "#3a3a3a", "ek": "#3a3a3a", "ic": "#6b6b6b", "korkuluk": "#9a9a9a", "kolon": "#1f1f1f", "baca": "#555555"}
KAPLAMA_ADI = {"sandvic_panel": "sandviç panel", "tek_kat_panel": "tek kat panel", "osb_kiremit": "OSB + nem bariyeri + kiremit desen sac",
               "osb_trapez": "OSB + nem bariyeri + trapez sac", "trapez_sac": "trapez sac", "osb_shingle": "OSB + membran + shingle"}
TARAF_ADI = {"on": "ÖN (GİRİŞ) GÖRÜNÜŞ", "arka": "ARKA GÖRÜNÜŞ", "sol": "SOL GÖRÜNÜŞ", "sag": "SAĞ GÖRÜNÜŞ"}


def tr(v: float, n: int = 1) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def sade(v: float) -> str:
    return tr(v).replace(",0", "")


def olcu(ax, p1, p2, metin, kaydir=0.0, yatay=True, fs=7.5):
    (x1, y1), (x2, y2) = p1, p2
    ok = ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="<->", color="#444", lw=0.7, shrinkA=0, shrinkB=0))
    ok.set_gid("olcu_ok")                                 # yalnız denetim etiketi (yazi_cakisma: ölçü oku ≠ eğim oku); çıktıyı değiştirmez
    if yatay:
        ax.text((x1 + x2) / 2, y1 + kaydir, metin, ha="center", va="bottom" if kaydir >= 0 else "top", fontsize=fs, color="#222")
    else:
        ax.text(x1 + kaydir, (y1 + y2) / 2, metin, ha="right" if kaydir <= 0 else "left", va="center", fontsize=fs, color="#222", rotation=90)


def zincir_birlestir(noktalar, uclar: tuple[float, float], tol: float) -> tuple[list[float], list[dict]]:
    """Sıralı zincir noktaları; birbirine `tol` cm'den yakın olanlar tek nokta sayılır (kısa parça komşusuna katılır), uçlar (genel ölçü)
    her zaman korunur. Bayiye giden çizimlerde 15 cm ve daha kısa parçalar (veranda dikmesi, korkuluk, kaplama sıçraması, tanımda 1–2 cm
    kayma) okunmaz (Lokman, 12.10.2026: "Çelikte 15 cm parça çıkmaz"); mühendis planı tam zinciri taşır (`pafta_sablonu.json` ›
    zincir_en_kisa_parca_cm). Dönen: (noktalar, katılan parçalar [{konum_cm: zincir başından, parca_cm}]) — katılanlar mühendise
    kontrol notu olur (`pafta_ozet.json › kontrol_notlari`). Şablon paftası (`sablon_pafta._birlestir`) ve bayi plan görseli
    (`bayi_gorseli.plan_bayi`, 13.10.2026) aynı kuralı kullanır."""
    cik: list[float] = []; katilan: list[dict] = []; son: float | None = None
    for v in sorted(set(noktalar)):                    # aynı nokta bir kez (uçlar zincirde de var)
        if not cik or v - cik[-1] > tol:               # `tol` ve daha kısa parçalar komşusuna katılır (iki yanda simetri için); tol 0 → birleştirme yok
            cik.append(v)
        elif v - cik[-1] > 0.05:                       # aynı nokta parça değildir; not düşülmez. Parça boyu bir önceki (tutulan ya da katılan) noktadan
            katilan.append({"konum_cm": round(v - uclar[0], 1), "parca_cm": round(v - (son if son is not None else cik[-1]), 1)})
        son = v
    cik[0], cik[-1] = uclar
    return (cik if cik[-1] > cik[0] else list(uclar)), katilan


def _cokgenler(g):
    if g.is_empty:
        return []
    return list(g.geoms) if g.geom_type in ("MultiPolygon", "GeometryCollection") else [g]


def dis_hat(y: dict):
    """Yapının dış çizgisi (kaplanmış dış yüzler): dış bölgenin iç halkası."""
    return [list(h.coords) for h in y["bolgeler"]["(dış)"]["net"].interiors]


def zincir_esigi(y: dict) -> float:
    """İç duvarın cepheye "ulaştığı" sayılan en büyük uzaklık (cm): en az 12,5; dış kaplama + en kalın dış duvar + 1 cm (BK-09 G1).
    80'lik karkasta iç duvar ucu dış çizgiden 9,2 cm (eşik 12,5 kalır), 140'lıkta 15,2 cm (1,25 kaplamayla eşik 16,25; KT-03'te 3 cm
    kaplamayla 18). Eşik yapı için tektir (en kalın dış duvar): 80 ve 140 karışık modelde yeniden ölçülür (D-16 › Yeniden açılır)."""
    kd = y["tanim"]["yuz_kaplamalari"]["dis"]["kalinlik"]
    dis = max((d["kalinlik"] for d in y["duvarlar"] if d["sinif"] == "dis"), default=0.0)
    return max(12.5, kd + dis + 1.0)


def zincirler(y: dict) -> dict:
    """Dört yan için ölçü zinciri noktaları: o yana bakan dış köşeler ve o yandaki cepheye ulaşan duvarlar
    (dış duvarda dış yüz, iç duvarda aks). Dönen: {'alt': [x...], 'ust': [x...], 'sol': [y...], 'sag': [y...]}"""
    t = y["tanim"]
    kd = t["yuz_kaplamalari"]["dis"]["kalinlik"]
    kenar = {"alt": [], "ust": [], "sol": [], "sag": []}          # (sabit, lo, hi)
    for h in dis_hat(y):
        pts = yapi._sade(h)
        alan2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
        for a, b in zip(pts, pts[1:] + pts[:1]):
            ex, ey = b[0] - a[0], b[1] - a[1]
            nx, ny = (ey, -ex) if alan2 > 0 else (-ey, ex)         # yapıdan dışarı
            if abs(ey) < 1e-6:
                kenar["alt" if ny < 0 else "ust"].append((a[1], min(a[0], b[0]), max(a[0], b[0])))
            else:
                kenar["sol" if nx < 0 else "sag"].append((a[0], min(a[1], b[1]), max(a[1], b[1])))
    cik = {}
    esik = zincir_esigi(y)
    for yan in kenar:
        nok = {round(v, 2) for _, lo, hi in kenar[yan] for v in (lo, hi)}
        for d in y["duvarlar"]:
            if d["sinif"] in ("kolon", "baca", "korkuluk"):
                continue
            dik = (d["yon"] == "y") if yan in ("alt", "ust") else (d["yon"] == "x")
            if not dik:
                continue
            x0, y0, x1, y1 = d["kutu"]
            uc = {"alt": y0, "ust": y1, "sol": x0, "sag": x1}[yan]
            orta = ((x0 + x1) / 2) if yan in ("alt", "ust") else ((y0 + y1) / 2)
            ulasir = any(abs(uc - sabit) <= esik and lo - 1 <= orta <= hi + 1 for sabit, lo, hi in kenar[yan])
            if not ulasir:
                continue
            if d["sinif"] == "ic":
                nok.add(round(orta, 2))
            else:                                               # dış duvar: dışa bakan uzun yüzü
                yuz = [f for f in y["yuzler"] if f["duvar"] == d["ad"] and f["uzun"] and f["kaplama"].startswith("dis")]
                for f in yuz:
                    c = {"sol": x0 - kd, "sag": x1 + kd, "alt": y0 - kd, "ust": y1 + kd}[f["kenar"]]
                    nok.add(round(c, 2))
        cik[yan] = sorted(nok)
    return cik


def etiket_yaydan_kacir(fig, ax, gruplar: list[tuple[list, object]], adim: float, en_cok: int = 12, bosluk_pt: float = 2.0) -> dict[int, tuple[float, float]]:
    """BK-09 M5: kapı açılım yayını (`gid` "kapi_yay") kesen mahal etiketi (ad + m² yazıları birlikte) oda içinde kaydırılır.
    gruplar: [(yazılar, odanın veri koordinatındaki çokgeni)]. Yalnız yayı kesen grup taşınır; aday kaydırmalar `adim` aralıklı ızgarada,
    uzaklık sırasıyla (eşitlikte sabit sıra): yazıların mürekkebi yaya değmez, odadan taşmaz, eksendeki öteki yazılara binmez. Uygun yer
    yoksa grup yerinde kalır (yazı çakışma testi `yay_kapatan` görür). Dönen: {grup sırası: (dx, dy)} veri biriminde. Eksen sınırları
    son hâlinde olmalı (çizim baytları yalnız taşınan yazıda değişir)."""
    from shapely import affinity
    from shapely.ops import unary_union as _birlesim
    from . import yazi_cakisma as YC
    r = fig.canvas.get_renderer()
    eksen = fig.axes.index(ax)
    yaylar = [k["poligon"] for k in YC.kapi_yaylari(fig) if k["eksen"] == eksen]
    if not yaylar:
        return {}
    yay = _birlesim(yaylar)
    yay_pay = yay.buffer(bosluk_pt * fig.dpi / 72.0)          # yeni yer yaydan en az bu kadar uzak (harf yaya yapışmasın)
    tasinan = {}
    for gi, (yazilar, oda) in enumerate(gruplar):
        def murekkep():
            return [YC._murekkep(t, r, fig.dpi)[0] for t in yazilar]
        if not any(YC._gercek(m.intersection(yay), YC.PAY_PX) > 0 for m in murekkep()):
            continue
        M = ax.transData.get_affine().get_matrix()
        oda_px = affinity.affine_transform(oda, [M[0, 0], M[0, 1], M[1, 0], M[1, 1], M[0, 2], M[1, 2]])
        obur = _birlesim([YC._murekkep(t, r, fig.dpi)[0] for t in ax.texts if t not in yazilar and t.get_text().strip() and t.get_visible()]
                         or [box(0, 0, 0, 0)])
        bas = [t.get_position() for t in yazilar]
        adaylar = sorted(((i * adim, j * adim) for i in range(-en_cok, en_cok + 1) for j in range(-en_cok, en_cok + 1) if (i, j) != (0, 0)),
                         key=lambda d: (round(d[0] ** 2 + d[1] ** 2, 6), -d[1], d[0]))
        for dx, dy in adaylar:
            for t, (x, y_) in zip(yazilar, bas):
                t.set_position((x + dx, y_ + dy))
            mm = murekkep()
            if all(oda_px.contains(m) and YC._gercek(m.intersection(yay_pay), YC.PAY_PX) == 0 and YC._gercek(m.intersection(obur), YC.PAY_PX) == 0
                   for m in mm):
                tasinan[gi] = (dx, dy)
                break
        else:
            for t, p in zip(yazilar, bas):
                t.set_position(p)
    return tasinan


def kapi_ciz(ax, y: dict, ac: dict):
    """Kapı kanadı (açık konumda) ve açılım yayı."""
    d = y["adli"][ac["duvar"]]
    x0, y0, x1, y1 = d["kutu"]
    r = ac["en"]
    mh = ac["a0"] if ac.get("mentese", "bas") == "bas" else ac["a1"]
    yon = 1 if ac.get("acilim", "ust") in ("ust", "sag") else -1
    if d["yon"] == "x":
        hx, hy = mh, (y1 if yon == 1 else y0)
        ax.plot([hx, hx], [hy, hy + yon * r], color="#8a4b2a", lw=1.2, zorder=6)
        kapali, acik = (0 if mh == ac["a0"] else 180), (90 if yon == 1 else 270)
    else:
        hx, hy = (x1 if yon == 1 else x0), mh
        ax.plot([hx, hx + yon * r], [hy, hy], color="#8a4b2a", lw=1.2, zorder=6)
        kapali, acik = (90 if mh == ac["a0"] else 270), (0 if yon == 1 else 180)
    t1, t2 = sorted([kapali % 360, acik % 360])
    if t2 - t1 > 180:
        t1, t2 = t2, t1 + 360
    ax.add_patch(Arc((hx, hy), 2 * r, 2 * r, theta1=t1, theta2=t2, color="#8a4b2a", lw=0.8, ls=(0, (3, 2)), zorder=6, gid="kapi_yay"))


def aciklik_kutusu(y: dict, ac: dict, pay: float = 3.5):
    d = y["adli"][ac["duvar"]]
    x0, y0, x1, y1 = d["kutu"]
    return box(ac["a0"], y0 - pay, ac["a1"], y1 + pay) if d["yon"] == "x" else box(x0 - pay, ac["a0"], x1 + pay, ac["a1"])


def plan_eksen(ax, y: dict, baslik: str | None = None, bilgi: list[str] | None = None, olcu_zinciri: bool = True,
               en_kisa_parca: float = 0.0, mahal_aralik: float = 14.0, giris_yazi_dy: float = 44.0):
    """Plan. Varsayılanlar çizim setinin (mühendis planı) baytlarını değiştirmez. Bayi plan görseli (İE-08, 13.10.2026) `en_kisa_parca`
    ile 15 cm ve daha kısa zincir parçalarını komşusuna katar (`zincir_birlestir`; şablon paftasıyla aynı kural) ve küçük mahallerde ad
    ile m² yazıları binmesin diye `mahal_aralik`ı (cm; ad cy+aralık, m² cy−aralık) ölçeğe göre büyütür."""
    t = y["tanim"]
    # mahaller
    for b in y["bolgeler"].values():
        if b["sinif"] == "dis":
            continue
        veranda = b["sinif"] == "veranda"
        renk = "#e9f2e0" if veranda else next((MAHAL_RENGI[i] for i in b.get("islev", []) if i in MAHAL_RENGI), "#f2f2f2")
        for p in _cokgenler(b["net"]):
            ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc=renk, ec="#7aa35c" if veranda else "none", hatch="///" if veranda else None,
                                    lw=0.6 if veranda else 0, zorder=1))
        c = b["net"].representative_point()
        cx, cy = b.get("etiket_yeri", (c.x, c.y))
        kutu = dict(fc="white", ec="none", pad=1.5) if veranda else None
        ax.text(cx, cy + mahal_aralik, b["ad"].upper(), ha="center", va="center", fontsize=8.6, weight="bold", zorder=8, bbox=kutu,
                gid=f"mahal:{b['ad']}")                                     # gid çizime girmez; bayi görselinde yay denetimi bulur (BK-09)
        ax.text(cx, cy - mahal_aralik, f"{tr(b['alan_m2'])} m²", ha="center", va="center", fontsize=8.6, zorder=8, bbox=kutu,
                gid=f"mahal:{b['ad']}")
    # duvarlar (kapı ve geçitlerde kesilir; pencerede duvar sürer)
    delik = unary_union([aciklik_kutusu(y, a) for a in y["acikliklar"] if a["tur"] != "pencere"] or [box(0, 0, 0, 0)])
    for sinif in ("korkuluk", "ic", "ek", "dis", "baca", "kolon"):
        for d in y["duvarlar"]:
            if d["sinif"] != sinif:
                continue
            g = unary_union([d["geo"]] + d.get("_serit", [])).difference(delik)
            for p in _cokgenler(g):
                if p.geom_type != "Polygon":
                    continue
                ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc=DUVAR_RENGI[sinif], ec="none", zorder=3 if sinif != "kolon" else 5))
            if sinif == "baca":
                x0, y0, x1, y1 = d["kutu"]
                ax.plot([x0, x1], [y0, y1], color="white", lw=0.8, zorder=6)
                ax.plot([x0, x1], [y1, y0], color="white", lw=0.8, zorder=6)
    # kirişler (üstte; kesik çizgi)
    for kr in t.get("kirisler", []):
        x0, y0, x1, y1 = kr["kutu"]
        yatay = (x1 - x0) >= (y1 - y0)
        for lo, hi in kr["acik"]:
            if yatay:
                ax.plot([lo, hi], [(y0 + y1) / 2] * 2, color="#4d4d4d", lw=2.0, ls=(0, (4, 2)), zorder=4)
            else:
                ax.plot([(x0 + x1) / 2] * 2, [lo, hi], color="#4d4d4d", lw=2.0, ls=(0, (4, 2)), zorder=4)
    # açıklıklar
    hat = dis_hat(y)
    bx0, by0 = min(p[0] for h in hat for p in h), min(p[1] for h in hat for p in h)
    bx1, by1 = max(p[0] for h in hat for p in h), max(p[1] for h in hat for p in h)
    for a in y["acikliklar"]:
        k = aciklik_kutusu(y, a)
        x1, y1, x2, y2 = k.bounds
        d = y["adli"][a["duvar"]]
        if a["tur"] == "pencere":
            ax.add_patch(MplPolygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], closed=True, fc=CAM, ec=CERCEVE, lw=1.0, zorder=4))
            et = a.get("etiket") or f"{a['en']}/{a['yuk']}"
            # etiket: duvarın dışa bakan yanına
            yuz = next((f for f in y["yuzler"] if f["duvar"] == d["ad"] and f["uzun"] and f["bolge_sinifi"] in ("dis", "veranda")), None)
            kn = yuz["kenar"] if yuz else ("alt" if d["yon"] == "x" else "sol")
            if kn == "alt":
                ax.text((x1 + x2) / 2, y1 - 9, et, ha="center", va="top", fontsize=7.2, color="#1f5f93", zorder=8)
            elif kn == "ust":
                ax.text((x1 + x2) / 2, y2 + 9, et, ha="center", va="bottom", fontsize=7.2, color="#1f5f93", zorder=8)
            elif kn == "sag":
                ax.text(x2 + 9, (y1 + y2) / 2, et, ha="left", va="center", fontsize=7.2, color="#1f5f93", rotation=90, zorder=8)
            else:
                ax.text(x1 - 9, (y1 + y2) / 2, et, ha="right", va="center", fontsize=7.2, color="#1f5f93", rotation=90, zorder=8)
        elif a["tur"] in ("ic_kapi", "dis_kapi"):
            kapi_ciz(ax, y, a)
    # ölçü zincirleri
    if olcu_zinciri:
        z = zincirler(y)
        if en_kisa_parca > 0:                                                                 # bayi çizimi: kısa parçalar komşusuna (D-10)
            z = {ad: zincir_birlestir(list(z[ad]) + list(uc), uc, en_kisa_parca)[0]
                 for ad, uc in (("alt", (bx0, bx1)), ("ust", (bx0, bx1)), ("sol", (by0, by1)), ("sag", (by0, by1)))}
        for i in range(len(z["alt"]) - 1):
            olcu(ax, (z["alt"][i], by0 - 66), (z["alt"][i + 1], by0 - 66), sade(z["alt"][i + 1] - z["alt"][i]), 3)
        olcu(ax, (bx0, by0 - 102), (bx1, by0 - 102), sade(bx1 - bx0), 3)
        for i in range(len(z["ust"]) - 1):
            olcu(ax, (z["ust"][i], by1 + 50), (z["ust"][i + 1], by1 + 50), sade(z["ust"][i + 1] - z["ust"][i]), 3)
        for i in range(len(z["sol"]) - 1):
            olcu(ax, (bx0 - 50, z["sol"][i]), (bx0 - 50, z["sol"][i + 1]), sade(z["sol"][i + 1] - z["sol"][i]), -4, yatay=False)
        olcu(ax, (bx0 - 86, by0), (bx0 - 86, by1), sade(by1 - by0), -4, yatay=False)
        for i in range(len(z["sag"]) - 1):
            olcu(ax, (bx1 + 50, z["sag"][i]), (bx1 + 50, z["sag"][i + 1]), sade(z["sag"][i + 1] - z["sag"][i]), 4, yatay=False)
    # giriş oku: dış kapılar
    for a in y["acikliklar"]:
        if a["tur"] in ("dis_kapi", "gecit") and a.get("giris"):
            d = y["adli"][a["duvar"]]
            x0, y0, x1, y1 = d["kutu"]
            if d["yon"] == "x":
                ax.annotate("GİRİŞ", xy=((a["a0"] + a["a1"]) / 2, y0 - 6), xytext=((a["a0"] + a["a1"]) / 2, y0 - giris_yazi_dy), ha="center", fontsize=7.5,
                            color="#b03030", arrowprops=dict(arrowstyle="->", color="#b03030", lw=1.0), zorder=9)
    if baslik:
        ax.set_title(baslik, fontsize=11, weight="bold", loc="left")
    alt_sinir = by0 - 126
    if bilgi:
        ax.text(bx0, by0 - 134, "\n".join(bilgi), ha="left", va="top", fontsize=8.3, linespacing=1.5)
        alt_sinir = by0 - 134 - 30 * len(bilgi) - 10
    ax.set_xlim(bx0 - 120, bx1 + 90)
    ax.set_ylim(alt_sinir, by1 + 90)
    ax.set_aspect("equal")
    ax.axis("off")


def inis_noktalari(c: dict, esik_cm: float = 1000.0, sacak_cm: float = 30.0, olcu: str = "cephe", alcak_kose: bool | str = True,
                   kisa_dere_m: float | None = None, sayim: dict | None = None) -> list[tuple[float, float, str]]:
    """Dere inişleri (Lokman, 3 Ekim 13:27): dere hattının her ucuna (köşe) bir; 10 m ve daha uzun cephenin ortasına bir.
    `olcu` "dere" ise (Lokman, 7 Ekim 2026 07:45: "çok uzun dere boylarında ortaya 1 tane daha") orta iniş, boyu eşiği geçen dere hattına konur.
    Dere hattı dereli saçak kenarlarıdır (`cati_genel.dere_hatlari`; çatı panelli ek yapıda dere yok); iki hattın buluştuğu köşe tek iniş sayılır.
    Cephe boyu: saçak kenarı − çatının dış köşesinde biten uçlardaki saçak payı.
    `kisa_dere_m` verilmişse (kural `inis.kisa_dere_tek_inis_m`; Lokman, 10 Ekim 2026 11:39) boyu onu geçmeyen dere hattında tek iniş (`kisa_dere_tek_inis`).
    `alcak_kose` (kural `inis.alcak_cati_ustundeki_kose`): True ise her uca iniş; False ise (0.18; Lokman, 10 Ekim 2026 10:18: "İniş olmasın") alçak bir
    çatının üstüne düşen uca iniş konmaz; "kucuk_catida_yok" ise (0.19; Lokman, 11:39: "veranda çatısının üstüne iniş oluyor") yalnız alçak çatı küçükse,
    yani kendi deresinde tek iniş varsa (giriş sundurması gibi) konmaz (`alcak_koseleri_dusur`). `sayim` verilirse düşen uçların sayısı ona yazılır."""
    uc: list[tuple[float, float]] = []
    orta = []
    orta_hat: set[int] = set()
    hatlar = (c.get("dere") or {}).get("hatlar")
    if hatlar is None:
        hatlar = [dict(e, cephe=e["boy"] - 2 * sacak_cm) for e in c["kenarlar"] if e["tur"] == "sacak"]
    for i, e in enumerate(hatlar):
        for p in (e["p"], e["q"]):
            if not any(math.hypot(p[0] - u[0], p[1] - u[1]) < 1.0 for u in uc):
                uc.append(p)
        if (e["boy"] > esik_cm + 1e-6) if olcu == "dere" else (e["cephe"] >= esik_cm - 1e-6):
            orta.append(((e["p"][0] + e["q"][0]) / 2, (e["p"][1] + e["q"][1]) / 2))
            orta_hat.add(i)
    if kisa_dere_m:
        n0 = len(uc)
        uc = kisa_dere_tek_inis(hatlar, uc, orta, orta_hat, kisa_dere_m * 100)
        if sayim is not None:
            sayim["kisa_dere"] = n0 - len(uc)
    if alcak_kose is not True:
        n0 = len(uc)
        uc = alcak_koseleri_dusur(c, hatlar, uc, orta_hat, yalniz_kucuk=(alcak_kose == "kucuk_catida_yok"))
        if sayim is not None:
            sayim["alcak"] = n0 - len(uc)
    return [(p[0], p[1], "kose") for p in uc] + [(p[0], p[1], "orta") for p in orta]


def kisa_dere_tek_inis(hatlar: list[dict], uc: list, orta: list, orta_hat: set, esik_cm: float) -> list:
    """Kısa derede tek iniş (Lokman, 10 Ekim 2026 11:39: "olsun önerine uyalım"; öneri: boyu bir dere parçasını, 4 m, geçmeyen hatta tek iniş).
    Kısa hattın iki ucu da başka bir dere hattına bağlıysa iki köşe de kalır: köşedeki iniş öteki hattın da inişidir (KT-03'te ana çatının verandanın
    üstündeki 2,6 m'lik saçağı: paftada iki uçta da iniş). Bir ucu bağlı, öteki serbestse serbest uç düşer (su bağlı köşedeki inişe gider). İki ucu da
    serbestse (tek başına duran dere: KT-03'te sundurmanınki, 1,62 m) başka bir inişe en yakın uç kalır, eşitlikte hattın ilk ucu (inişler bir köşede
    toplanır; Claude'un seçimi, yalnız çizimdeki yeri etkiler)."""
    def yakin(a, b) -> bool:
        return math.hypot(a[0] - b[0], a[1] - b[1]) < 1.0

    def bagli(p, i) -> bool:
        return any(yakin(p, e["p"]) or yakin(p, e["q"]) for k, e in enumerate(hatlar) if k != i)

    dusen = []
    for i, e in enumerate(hatlar):
        if i in orta_hat or e["boy"] > esik_cm + 1e-6:
            continue
        bp, bq = bagli(e["p"], i), bagli(e["q"], i)
        if bp and bq:
            continue
        if bp != bq:
            dusen.append(e["q"] if bp else e["p"])
            continue
        oteki = [u for u in uc if not yakin(u, e["p"]) and not yakin(u, e["q"]) and not any(yakin(u, g) for g in dusen)] + list(orta)
        mesafe = lambda p: min((math.hypot(p[0] - u[0], p[1] - u[1]) for u in oteki), default=math.inf)
        dusen.append(e["q"] if mesafe(e["p"]) <= mesafe(e["q"]) else e["p"])
    return [u for u in uc if not any(yakin(u, g) for g in dusen)]


def alcak_koseleri_dusur(c: dict, hatlar: list[dict], uc: list, orta_hat: set, yalniz_kucuk: bool = False) -> list:
    """Alçak bir çatının üstüne düşen dere ucuna iniş konmaz (Lokman, 10 Ekim 2026: "İniş olmasın"; KT-03'ün dere paftasında ana çatının sundurmanın
    üstüne düşen iç köşesinde iniş yok). Aday: uç, ucun bağlı olduğu dere hatlarının düzlemlerinden başka, o noktada daha alçak bir düzlemin planı
    içinde kalıyor. En derindeki aday önce düşer; ama her dere hattının en az bir ucunda (ya da ortasında) iniş kalır (Claude'un uygulaması: suyun bir
    çıkışı olmalı). Bir hattın iki ucu da alçak çatının üstündeyse alçak çatının kenarına en yakın uç kalır.
    `yalniz_kucuk` (0.19): Lokman, 10 Ekim 2026 11:39: "veranda çatısının üstüne iniş oluyor ama dere veranda çatısının hemen üstünde 15 cm içerde bitiyor
    akan su dereden verandaya iniyor". Aday yalnız alçak çatı küçükse sayılır: kendi dere hatlarında en çok bir iniş var (KT-03'ün sundurması: tek
    inişli 1,62 m'lik dere). Verandanın deresinde iki iniş var: verandanın üstüne düşen köşeler kalır (paftadaki gibi). Okuma Claude'un; Lokman'a yazıldı."""
    from shapely.geometry import Point
    adli = {d["ad"]: d for d in c["duzlemler"]}

    def yakin(a, b) -> bool:
        return math.hypot(a[0] - b[0], a[1] - b[1]) < 1.0

    hat_uclari = [[j for j, u in enumerate(uc) if yakin(u, e["p"]) or yakin(u, e["q"])] for e in hatlar]
    hat_duzlemi = [e.get("duzlem") or e["duzlemler"][0] for e in hatlar]

    def kucuk(d) -> bool:          # alçak çatının kendi dere hatlarındaki iniş sayısı (uç ve orta) en çok bir
        return len({j for i, ue in enumerate(hat_uclari) if hat_duzlemi[i] == d["ad"] for j in ue}) + sum(1 for i in orta_hat if hat_duzlemi[i] == d["ad"]) <= 1

    aday = []
    for j, u in enumerate(uc):
        dz_adlari = {hat_duzlemi[i] for i, ue in enumerate(hat_uclari) if j in ue}
        ust = max(adli[a]["kot"](u) for a in dz_adlari)
        nokta = Point(u)
        for d in c["duzlemler"]:
            if d["ad"] in dz_adlari or not d["cokgen"].contains(nokta) or d["kot"](u) > ust - 1.0:
                continue
            if not yalniz_kucuk or kucuk(d):
                aday.append((d["cokgen"].exterior.distance(nokta), j))
            break
    dusen: set[int] = set()
    for _, j in sorted(aday, key=lambda x: (-x[0], x[1])):
        if all(i in orta_hat or any(u2 != j and u2 not in dusen for u2 in ue) for i, ue in enumerate(hat_uclari) if j in ue):
            dusen.add(j)
    return [u for j, u in enumerate(uc) if j not in dusen]


def inis_kurali(c: dict, kur: dict, sacak_cm: float) -> tuple[list[tuple[float, float, str]], dict]:
    """Kural setindeki iniş kuralıyla iniş noktaları ve kurala göre düşen uçların sayısı (`kisa_dere`, `alcak`). Eski setlerde anahtar yoksa eski davranış."""
    ii = kur["inis"]["deger"]
    sayim: dict = {}
    nok = inis_noktalari(c, ii["orta_inis_esigi_m"] * 100, sacak_cm, ii.get("olcu", "cephe"), ii.get("alcak_cati_ustundeki_kose", True),
                         ii.get("kisa_dere_tek_inis_m"), sayim)
    return nok, sayim


def cati_plani_eksen(ax, y: dict, c: dict, inisler=None, baslik: str | None = None, yazi_ayir: bool = False, yalin: bool = False,
                     yazi_kutusu: tuple[float, float] = (55.0, 12.0)):
    """Çatı planı. `baslik` verilmezse uzun başlık (çizim setindeki pafta); `yazi_ayir` ile üst üste binen eğim yazıları kaydırılır
    (İE-08 şablon paftası 2. sayfa; varsayılanlar çizim setinin baytlarını değiştirmez). `yalin` (bayi kartının küçük paneli, 13.10.2026):
    mahya/kırma/vadi boy yazıları basılmaz (çizgiler kalır), eğim yazıları `yazi_kutusu` (yarı en, yarı boy; cm) ile sığdığı yere konur."""
    for dz in sorted(c["duzlemler"], key=lambda d: max(k[2] for k in d["ucboyut"])):          # alçak düzlem önce
        ax.add_patch(MplPolygon(dz["plan"], closed=True, fc="#8a919c", ec="#2f343c", lw=1.0, zorder=1 + max(k[2] for k in dz["ucboyut"]) / 1000))
    for h in dis_hat(y):                                                                      # duvarların dış yüzü
        ax.plot([p[0] for p in h], [p[1] for p in h], color="white", lw=0.8, ls=(0, (5, 3)), zorder=3)
    yazi = {"mahya": "mahya", "kirma": "kırma", "vadi": "vadi"}
    yerler: list[tuple[float, float, float, float]] = []                                       # yazı kutuları (x, y, yarı en, yarı boy; yazi_ayir)
    # eğim oklarının yerleri (yazi_ayir: yazı okun üstüne konmaz; 13.10.2026)
    oklar = [(m.x + ux * 20, m.y + uy * 20, m.x - ux * 40, m.y - uy * 40)
             for dz in c["duzlemler"] for m in [dz["cokgen"].representative_point()] for (ux, uy) in [dz["yukari"]]] if yazi_ayir else []
    ok_keser = lambda x, y_, kx, ky: any(box(x - kx, y_ - ky, x + kx, y_ + ky).intersects(LineString([(a, b), (c_, d)]).buffer(6)) for a, b, c_, d in oklar)
    cati_ici = unary_union([dz["cokgen"] for dz in c["duzlemler"]]).buffer(-8) if yazi_ayir else None   # kenar yazısı çatının içinde kalır (ölçülere binmez)
    for e in c["kenarlar"]:
        (px, py), (qx, qy) = e["p"], e["q"]
        if e["tur"] in ("mahya", "kirma"):
            ax.plot([px, qx], [py, qy], color="#1c1f24", lw=2.0, zorder=4)
        elif e["tur"] == "vadi":
            ax.plot([px, qx], [py, qy], color="#e8e8e8", lw=1.6, ls=(0, (4, 2)), zorder=4)
        elif e["tur"] == "duvar_dibi":
            ax.plot([px, qx], [py, qy], color="#f0b35a", lw=1.8, zorder=4)
        if e["tur"] in yazi and e["boy"] > 150 and not yalin:
            aci = math.degrees(math.atan2(qy - py, qx - px))
            if aci > 90 or aci <= -90:
                aci += 180
            nx, ny = -math.sin(math.radians(aci)), math.cos(math.radians(aci))
            ca, sa = abs(math.cos(math.radians(aci))), abs(math.sin(math.radians(aci)))      # yazı kutusu ≈ 110 × 22 cm, döndürülmüş
            rx, ry = 55 * ca + 11 * sa, 55 * sa + 11 * ca
            mx, my = (px + qx) / 2, (py + qy) / 2
            tx, ty = mx + nx * 14, my + ny * 14
            if yazi_ayir:                                                                      # kenar yazısı başka yazıya ve eğim okuna binmesin:
                ex_, ey_ = (qx - px) / max(e["boy"], 1e-9), (qy - py) / max(e["boy"], 1e-9)   # kenar boyunca kayar, sığmazsa öbür yana, o da olmazsa atlanır
                bos = lambda x, y_: (not any(abs(x - a) < r1 + rx and abs(y_ - b) < r2 + ry for a, b, r1, r2 in yerler) and not ok_keser(x, y_, rx, ry)
                                     and cati_ici.contains(box(x - rx, y_ - ry, x + rx, y_ + ry)))
                denemeler = [(mx + nx * 14 + ex_ * d, my + ny * 14 + ey_ * d) for d in (0, 40, -40, 80, -80, 120, -120)] + \
                            [(mx - nx * 14 + ex_ * d, my - ny * 14 + ey_ * d) for d in (0, 40, -40, 80, -80)]
                yer = next(((x, y_) for x, y_ in denemeler if bos(x, y_)), None)
                if yer is None:
                    continue
                tx, ty = yer
            ax.text(tx, ty, f"{yazi[e['tur']]} {tr(e['boy'], 0)}", ha="center", va="center", fontsize=7.2, color="white",
                    rotation=aci, rotation_mode="anchor", zorder=6)
            yerler.append((tx, ty, rx, ry))
    for dz in c["duzlemler"]:                                                                  # eğim okları
        m = dz["cokgen"].representative_point()
        ux, uy = dz["yukari"]
        ax.annotate("", xy=(m.x - ux * 40, m.y - uy * 40), xytext=(m.x + ux * 20, m.y + uy * 20), arrowprops=dict(arrowstyle="->", color="white", lw=1.0), zorder=6)
        tx, ty = m.x + ux * 42 + abs(uy) * 36, m.y + uy * 42
        if yazi_ayir:                                                                          # yazı kutusu (≈110 × 24 cm) düzlemin içinde ve başka yazıya binmeden
            kx, ky = yazi_kutusu
            cakisir = lambda x, y_: any(abs(x - a) < rx + kx and abs(y_ - b) < ry + ky for a, b, rx, ry in yerler) or ok_keser(x, y_, kx, ky)
            ic = dz["cokgen"].buffer(-18)                                                      # sığmıyorsa yazı atlanır (ok kalır; eğim Bina Özellikleri'nde de yazar)
            uygun = lambda x, y_: not cakisir(x, y_) and ic.contains(box(x - kx, y_ - ky, x + kx, y_ + ky))
            cx, cy = dz["cokgen"].centroid.x, dz["cokgen"].centroid.y
            denemeler = [(tx, ty), (m.x, m.y + uy * 42 + abs(ux) * 30), (cx, cy)] + [(tx - uy * d, ty + ux * d) for d in (32, -32, 64, -64, 96, -96)] \
                + [(tx + ux * d, ty + uy * d) for d in (40, -40, 80, -80)] + [(cx - uy * d, cy + ux * d) for d in (40, -40)]
            yer = next(((x, y_) for x, y_ in denemeler if uygun(x, y_)), None)
            if yer is None:
                continue
            tx, ty = yer
            yerler.append((tx, ty, kx, ky))
        ax.text(tx, ty, f"%{tr(dz['egim'] * 100)}", ha="center", va="center", fontsize=7.2, color="white", zorder=6)
    for ix, iy, _tur in (inisler or []):
        ax.plot([ix], [iy], marker="o", ms=6.5, mfc="#f2c744", mec="#1c1f24", mew=1.0, zorder=8)
    xs = [p[0] for dz in c["duzlemler"] for p in dz["plan"]]
    ys = [p[1] for dz in c["duzlemler"] for p in dz["plan"]]
    ky, kx = -3.0, -4.0                                                                       # sayının çizgiden uzaklığı (cm)
    if yazi_ayir or yalin:                                                                    # küçük panelde ölçeğe göre (sayı çizgiye değmesin; 13.10)
        cm_pt = cm_pt_tahmini(ax, (max(xs) - min(xs)) + 130)
        ky, kx = -max(3.0, 2.5 * cm_pt), -max(4.0, 3.0 * cm_pt)
    olcu(ax, (min(xs), min(ys) - 34), (max(xs), min(ys) - 34), sade(max(xs) - min(xs)), ky)
    olcu(ax, (min(xs) - 34, min(ys)), (min(xs) - 34, max(ys)), sade(max(ys) - min(ys)), kx, yatay=False)
    ek = f" · sarı nokta: dere inişi ({len(inisler)} adet)" if inisler else ""
    ax.set_title(baslik if baslik is not None else "ÇATI PLANI" + ek + " · turuncu: duvara dayanan kenar", fontsize=9.5, weight="bold")
    ax.set_xlim(min(xs) - 90, max(xs) + 40)
    ax.set_ylim(min(ys) - 80, max(ys) + 30)
    ax.set_aspect("equal")
    ax.axis("off")


RENK = {"duvar": (DUVAR, "#555"), "korkuluk": (DUVAR, "#555"), "kalkan": (DUVAR, "#555"), "kolon": (KOLON, "#555"), "kiris": (KOLON, "#555"),
        "cati": (CATI, "#2f343c"), "alin": ("#454b55", "#2f343c"), "baca": (DUVAR_GERI, "#555"), "pencere": (CAM, CERCEVE), "kapi": (KAPI, "#5c4326"),
        "gecit": ("#f4f1ea", "#555")}


def _yama(g, fc, ec, lw=0.8, zorder=2):
    """Shapely çokgeninden (delikli olabilir) matplotlib yaması."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath
    nok, kod = [], []
    for halka in [g.exterior] + list(g.interiors):
        pts = list(halka.coords)
        nok += pts
        kod += [MplPath.MOVETO] + [MplPath.LINETO] * (len(pts) - 2) + [MplPath.CLOSEPOLY]
    return PathPatch(MplPath(nok, kod), fc=fc, ec=ec, lw=lw, zorder=zorder, joinstyle="round")


DUVAR_GIBI = ("duvar", "korkuluk", "kalkan")


def cm_pt_tahmini(ax, span_cm: float) -> float:
    """Eksenin yatay ölçeği (cm / pt): veri aralığı `span_cm` eksenin genişliğine yayılınca bir punto kaç cm eder (yazı boyu → cm)."""
    fig = ax.figure
    w_pt = max(ax.get_position().width * fig.get_figwidth() * 72.0, 1.0)
    return span_cm / w_pt


def surgulu_oku(k2) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Sürgülü pencerenin görünüşteki yön oku (sağ kanadın ortasında, sağa): gövde, kuyruk çentiği, iki uç; (u, z) cm çizgileri."""
    us = [p[0] for p in k2]; zs = [p[1] for p in k2]
    o, zm = (min(us) + max(us)) / 2, (min(zs) + max(zs)) / 2
    ua, ub = o + (max(us) - o) * 0.25, o + (max(us) - o) * 0.75
    return [((ua, zm), (ub, zm)), ((ua, zm - 4), (ua, zm + 4)), ((ub, zm), (ub - 6, zm + 4)), ((ub, zm), (ub - 6, zm - 4))]


def gorunus_eksen(ax, S: list[dict], taraf: str, duvar_h: float, olculu: bool = True, sigdir: bool = False):
    """Görünüş: yüzeyler uzaktan yakına çizilir. Aynı düzlemdeki duvar yüzleri (duvar, korkuluk, kalkan) birleştirilir, böylece panel
    ekleri çizgi olarak görünmez; kapısız geçitler duvarda delik olur (arkası görünür). `olculu=False`: ölçü zincirleri basılmaz
    (bayi kartının küçük görünüş paneli, VTK yoksa; 13.10.2026 — sayılar o ölçekte birbirine biniyordu). `sigdir=True` (şablon paftası
    2. sayfa): iki düşey ölçü şeridinin arası sayının mürekkebine göre açılır (küçük panelde kat yüksekliği sayısı tepe ölçüsünün
    okuna biniyordu); varsayılan çizim setinin baytlarını değiştirmez."""
    from shapely.geometry import Polygon as SPolygon
    yz = sahne_m.izdusum(S, taraf)
    gecitler = [s for s in yz if s["tur"] == "gecit"]
    en_yakin = min(s["derinlik"] for s in yz if s["tur"] in ("duvar", "korkuluk"))       # en öndeki duvar düzlemi; 60 cm'den geridekiler koyu
    i = 0
    while i < len(yz):
        s = yz[i]
        if s["tur"] == "gecit":
            i += 1
            continue
        if s["tur"] in DUVAR_GIBI:
            grup = [s]
            j = i + 1
            while j < len(yz) and (yz[j]["tur"] in DUVAR_GIBI or yz[j]["tur"] == "gecit") and abs(yz[j]["derinlik"] - s["derinlik"]) < 0.6:
                if yz[j]["tur"] != "gecit":
                    grup.append(yz[j])
                j += 1
            g = unary_union([SPolygon(x["k2"]).buffer(0.01, join_style=2) for x in grup]).buffer(-0.01, join_style=2)
            delik = [SPolygon(x["k2"]) for x in gecitler if abs(x["derinlik"] - s["derinlik"]) < 1.0]
            if delik:
                g = g.difference(unary_union(delik))
            for p in _cokgenler(g):
                if p.geom_type == "Polygon" and p.area > 1:
                    ax.add_patch(_yama(p, DUVAR_GERI if s["derinlik"] > en_yakin + 60 else DUVAR, "#555"))
            i = j
            continue
        fc, ec = RENK[s["tur"]]
        ax.add_patch(MplPolygon(s["k2"], closed=True, fc=fc, ec=ec, lw=0.8 if s["tur"] not in ("pencere", "kapi") else 1.0, zorder=2, joinstyle="round"))
        if s["tur"] == "pencere" and s.get("en", 0) >= 100:
            us = [p[0] for p in s["k2"]]
            zs = [p[1] for p in s["k2"]]
            ax.plot([(min(us) + max(us)) / 2] * 2, [min(zs), max(zs)], color=CERCEVE, lw=0.7, zorder=2)
        if s["tur"] == "pencere" and s.get("acilis") == "surgulu":        # sürgülü (Lokman, 30 Ekim 2026): sağ kanatta kırmızı yön oku
            for (ua, za), (ub, zb) in surgulu_oku(s["k2"]):
                ax.plot([ua, ub], [za, zb], color="#d62728", lw=0.8, zorder=2)
        i += 1
    us = [p[0] for s in yz for p in s["k2"]]
    zs = [p[1] for s in yz for p in s["k2"]]
    duvar_us = [p[0] for s in yz if s["tur"] in ("duvar", "korkuluk", "kolon") for p in s["k2"]]
    u0, u1 = min(duvar_us), max(duvar_us)
    ax.plot([min(us) - 40, max(us) + 40], [0, 0], color="#333", lw=1.2, zorder=1)
    tepe = max(z for s in yz if s["tur"] in ("cati", "alin", "kalkan") for _, z in s["k2"])
    serit2 = 66.0; sag_pay = 110.0
    if olculu and sigdir:                                 # sayı (7,5 pt döndürülmüş yerleşim kutusu 1,2 em) + ok ucu (≈2,7 pt) + 2 pt boşluk + 4 cm; en az bugünkü 36 cm
        cm_pt = cm_pt_tahmini(ax, (max(us) - min(us)) + 60 + sag_pay)
        kalin = (1.2 * 7.5 + 2.7 + 2.0) * cm_pt
        serit2 = 30.0 + max(36.0, 4.0 + kalin)
        sag_pay = max(110.0, serit2 + 4.0 + kalin + 10.0)
    if olculu:
        olcu(ax, (max(us) + 30, 0), (max(us) + 30, duvar_h), sade(duvar_h), 4, yatay=False)
        olcu(ax, (max(us) + serit2, 0), (max(us) + serit2, tepe), tr(tepe, 0), 4, yatay=False)
        olcu(ax, (u0, -34), (u1, -34), sade(u1 - u0), -3)
    ax.set_title(TARAF_ADI[taraf], fontsize=9.5, weight="bold")
    ax.set_xlim(min(us) - 60, max(us) + sag_pay)
    ax.set_ylim(-75, max(zs) + 25)
    ax.set_aspect("equal")
    ax.axis("off")


def pafta(y: dict, c: dict, S: list[dict], cikti: Path, sol: list[str], sag: list[str], inisler=None, alt_baslik: str = "TASLAK · modelden okunan ölçülerle kuruldu · üretim projesi değildir",
          ad: str | None = None):
    t = y["tanim"]
    ad = ad or f"{t['kod']} · {t['ad']}"
    fig = plt.figure(figsize=(18.5, 13.6), dpi=140)
    gs = GridSpec(3, 4, figure=fig, height_ratios=[1.9, 1.0, 0.52], hspace=0.10, wspace=0.06)
    ax = fig.add_subplot(gs[0, 0:2])
    plan_eksen(ax, y)
    ax.set_title("PLAN", fontsize=9.5, weight="bold")
    cati_plani_eksen(fig.add_subplot(gs[0, 2:4]), y, c, inisler)
    for i, taraf in enumerate(("on", "arka", "sol", "sag")):
        gorunus_eksen(fig.add_subplot(gs[1, i]), S, taraf, t["kat_yuksekligi"])
    ax = fig.add_subplot(gs[2, :])
    ax.axis("off")
    import textwrap
    sar = lambda satirlar: "\n".join("\n    ".join(textwrap.wrap(x, 118)) for x in satirlar)
    ax.text(0.0, 0.98, sar(sol), ha="left", va="top", fontsize=8.8, linespacing=1.5, transform=ax.transAxes)
    ax.text(0.51, 0.98, sar(sag), ha="left", va="top", fontsize=8.8, linespacing=1.5, transform=ax.transAxes)
    fig.suptitle(f"{ad}   —   {alt_baslik}", fontsize=12.5, weight="bold", x=0.02, ha="left", y=0.965)
    fig.savefig(cikti, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gorunusler(S: list[dict], cikti: Path, duvar_h: float, baslik: str):
    fig, axs = plt.subplots(2, 2, figsize=(17, 9.5), dpi=140)
    for ax, taraf in zip(axs.ravel(), ("on", "arka", "sol", "sag")):
        gorunus_eksen(ax, S, taraf, duvar_h)
    fig.suptitle(baslik, fontsize=12, weight="bold", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(cikti, facecolor="white")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--cikti", type=Path, default=KOK / "cikti" / "genel")
    ap.add_argument("--yontem", choices=("panel", "omega_asik"), help="tanımdaki çatı yöntemi yerine: panel (A; çelik standardı) ya da omega_asik (B; prefabrik yöntemi)")
    a = ap.parse_args()
    from . import girdi_genel
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    if a.yontem:
        t["cati"]["yontem"] = a.yontem
    kur = kurallar_oku.oku()
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    S = sahne_m.sahne_kur(y, c)
    m = girdi_genel.metraj(y, c, kur)
    sol, sag = girdi_genel.bilgi_satirlari(y, c, m, kur)
    a.cikti.mkdir(parents=True, exist_ok=True)
    kod = t["kod"].replace("Ç", "C").replace("-", "")
    inis, _ = inis_kurali(c, kur, t["cati"].get("sacak", 30))
    fig, ax = plt.subplots(figsize=(13.5, 11.5), dpi=140)
    ad = girdi_genel.baslik_adi(t, m["oturum_m2"])               # BK-09 M7: KT'de m² koddan
    plan_eksen(ax, y, baslik=f"{ad}\nTASLAK · modelden okunan ölçülerle kuruldu · üretim projesi değildir", bilgi=sol + ["Ölçü zinciri: dış yüzler ve iç duvar aksları · ölçüler cm"])
    fig.savefig(a.cikti / f"{kod}_plan.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    pafta(y, c, S, a.cikti / f"{kod}_pafta.png", sol, sag, inis, ad=ad)
    gorunusler(S, a.cikti / f"{kod}_gorunusler.png", t["kat_yuksekligi"], f"{ad} · görünüşler")
    print("yazıldı:", ", ".join(f"{kod}_{x}.png" for x in ("plan", "pafta", "gorunusler")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
