"""İE-12 · Prefabrik bayi paftası: antetli A4 sayfanın ortasında TASLAK bayi görseli (Lokman, 13 Ekim 2026 09:34 / 09:38 / 09:39).

Geometri pano Motor'undandır (`geometry.kur`; D-12, D-15): panolar, pano ekleri (H profili), köşeler, kapı ve pencere yerleri. Plan
doğrudan Motor'un `Plan`'ından çizilir; çeviri ya da ikinci bir geometri yoktur. Genel motordan yalnız çizim yardımcıları kullanılır:
"Örnek Şablon" çerçevesi ve antet (`genel.sablon_pafta`), ölçü oku ve renkler (`genel.ciz_genel`) ve perspektif (`genel.perspektif`,
Motor'un IFC'sinden; VTK). Beşik çatı planı burada çizilir; düzlemleri İş Emri'nin `cati` alanından (Motor'un IFC çatısıyla aynı kurallar).

Sayfa: A4 yatay; sağda BİNA ÖZELLİKLERİ ve ÖZEL İSTEKLER; altta antet (proje adı, m², TASLAK ve İş Emri no antette). Ana çerçevede
renkli plan (ARKA / SOL / SAĞ / ÖN (GİRİŞ) etiketleri, dış yüzden ölçü zincirleri, pencere ölçüleri, D-15 kapı yayları, her pano ekinde
H profili), çatı planı ve iki perspektif. Aynı bileşik görsel tek başına PNG olarak da yazılır (WhatsApp önizlemesi, ≤ 5 MB).

K23: Motor'un DXF doğrulaması geçmezse teslim PDF'i yazılmaz; yalnız tanı için `<kod>_bayi.HATALI.pdf`. Perspektif VTK ister; çizilemezse
sayfa yine çıkar, yerinde "perspektif çizilemedi" yazar. Çıktılar matplotlib'in kendi varsayılanlarıyla çizilir (`rc_context` içinde;
çağıranın ayarları değişmez).

    python -m motor.sunum <is_emri.json> <çıktı klasörü> [--perspektifsiz]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from . import geometry as G

KOK = Path(__file__).resolve().parents[1]
ETIKET = {"on": "ÖN (GİRİŞ)", "arka": "ARKA", "sol": "SOL", "sag": "SAĞ"}
GORUNUMLER = (("perspektif_on_sag", "ÖN-SAĞ PERSPEKTİF"), ("perspektif_arka_sag", "ARKA-SAĞ PERSPEKTİF"))
PERSPEKTIF_UZAKLIK = 1.55            # kamera uzaklığı (yapı köşegeninin katı); genel motorun 1,35'i bu planlarda saçağı kesiyordu
PERSPEKTIF_ZAMAN_ASIMI_S = 240
PNG_SINIRI = 5 * 1024 * 1024         # WhatsApp görsel sınırı
MAHAL_ISLEVI = {"antre_hol": "hol", "hol": "hol", "koridor": "hol", "salon": "salon", "mutfak": "mutfak", "yatak_odasi": "yatak_odasi",
                "calisma": "yatak_odasi", "giyinme": "yatak_odasi", "banyo": "banyo", "wc": "banyo", "depo": "depo", "teknik": "depo"}
DUVAR_RENGI = {"dis": "#3a3a3a", "ic": "#6b6b6b"}
KOSE_RENGI = "#151515"
H_RENGI, H_KENAR = "#e4e8ec", "#8a949d"        # galvaniz H profili
CAM, CERCEVE, KAPI_RENGI, ACIK_RENGI = "#cfe6f7", "#2a78b8", "#8a4b2a", "#e9f2e0"
ETIKET_MAVI = "#1f5f93"
VASISTAS_ESIGI_CM = 60.0             # şablonun kuralı (`kurallar/cizim/pafta_sablonu.json` › vasistas_en_cok_yukseklik_cm); yoksa 60


# ───────────────────────────────────────────────────────────────── yardımcılar ──
def _f(v: float) -> str:
    """Ölçü yazısı: en çok iki ondalık, sondaki sıfırlar atılır, ondalık virgül (201,25 · 213,5 · 600)."""
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def kod_adi(ie: dict) -> str:
    return str(ie.get("yapi", {}).get("referans_model") or ie.get("is_emri_no") or "PLAN")


def dosya_govdesi(ie: dict) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", kod_adi(ie).replace("Ç", "C")) or "PLAN"


def _cokgenler(g):
    if g is None or g.is_empty:
        return []
    return list(g.geoms) if g.geom_type in ("MultiPolygon", "GeometryCollection") else [g]


def bina_cizgisi(plan: G.Plan):
    """Kapalı yapının dış çizgisi (duvar, köşe ve boşluk kutularının birleşiminin dış halkası); veranda ve dikme dışarıda."""
    from shapely.geometry import Polygon
    from shapely.geometry.polygon import orient
    en_buyuk = max(_cokgenler(plan.footprint()), key=lambda p: p.area)
    return orient(Polygon(en_buyuk.exterior.coords).simplify(0.01), 1.0)      # saat yönü tersi: kenarın dış normali (ey, −ex)


def sinirlar(plan: G.Plan) -> tuple[float, float, float, float]:
    """Dış ölçü kutusu: bina, açık mahaller (veranda) ve dikmeler dahil."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    g = unary_union([plan.footprint()] + [m.poly for m in plan.mahaller.values() if m.poly is not None] + [box(*r) for r in plan.dikmeler])
    return g.bounds


def oturum_m2(plan: G.Plan) -> float:
    """Brüt oturum: dış duvarların dış yüzleri, veranda ve dikmeler dahil (genel motordaki `oturum_m2` gibi; sınır kutusu değil)."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    g = unary_union([bina_cizgisi(plan)] + [m.poly for m in plan.mahaller.values() if m.poly is not None] + [box(*r) for r in plan.dikmeler])
    return sum(Polygon(p.exterior.coords).area for p in _cokgenler(g.buffer(0.05, join_style=2).buffer(-0.05, join_style=2))) / 1e4


def sayimlar(plan: G.Plan) -> dict:
    acl = [p.acilim for p in plan.panolar if p.acilim]
    ek = G.pano_ekleri(plan)
    pen = [a for a in acl if a.tur == "pencere" and (a.yukseklik or 0) > VASISTAS_ESIGI_CM]
    vas = [a for a in acl if a.tur == "pencere" and (a.yukseklik or 0) <= VASISTAS_ESIGI_CM]
    yatak = sum(1 for m in plan.mahaller.values() if m.tur == "yatak_odasi")
    salon = 1 if any(m.tur == "salon" for m in plan.mahaller.values()) else 0
    return {"pano_dis": sum(len(d.panolar) for d in plan.duvarlar if d.tur == "dis"), "pano_ic": sum(len(d.panolar) for d in plan.duvarlar if d.tur == "ic"),
            "h_pano_eki": sum(k["cins"] == "pano_eki" for k in ek), "h_uclu": sum(k["cins"] == "uclu" for k in ek), "kose": len(plan.koseler),
            "dikme": len(plan.dikmeler), "pencere": [G.pencere_yazisi(a.olcu) for a in pen],
            "vasistas": [G.pencere_yazisi(a.olcu) for a in vas], "ic_kapi": sum(a.tur == "ic_kapi" for a in acl),
            "dis_kapi": [_f(a.genislik) for a in acl if a.tur == "dis_kapi"], "oda_programi": f"{yatak}+{salon}", "oturum_m2": round(oturum_m2(plan), 2)}


def _olculer(liste: list[str]) -> str:
    return ", ".join(f"{n} × {k}" for k, n in sorted(Counter(liste).items()))


def ozellikler(ie: dict, say: dict) -> tuple[dict, list[str]]:
    """BİNA ÖZELLİKLERİ (şablonun 15 satırı) ve tabloya girmeyen İş Emri özellikleri (ÖZEL İSTEKLER kutusuna). Bilinmeyen "..." (K21)."""
    y = ie.get("yapi", {}); c = ie.get("cati", {}); oz_ie = dict(ie.get("ozellikler") or {})
    kal = y.get("duvar_kalinligi_cm") or {}
    panel = oz_ie.get("Panel Türü")
    duvar = lambda cm: f"{float(cm) * 10:.0f} mm" + (f" {panel}" if panel else "")
    oz = {"Bina Yüksekliği": f"{float(y.get('duvar_yuksekligi_cm', 250)) * 10:.0f} mm",
          "Dış Duvarlar": duvar(kal.get("dis", 10)), "İç Duvarlar": duvar(kal.get("ic", 6)), "Panel Türü": panel or "...",
          "Çatı Şekli": oz_ie.pop("Çatı Şekli", None) or {"besik": "Beşik"}.get(c.get("tip"), "..."),
          "Çatı Eğimi": f"%{float(c['egim_yuzde']):g}" if "egim_yuzde" in c else "...",
          "Çatı Kaplaması": oz_ie.pop("Çatı Kaplaması", None) or "...", "Çatı Kaplama Rengi": oz_ie.pop("Çatı Kaplama Rengi", None) or "...",
          "Dış Kapı": oz_ie.pop("Dış Kapı", None) or (f"{len(say['dis_kapi'])} adet ({_olculer(say['dis_kapi'])})" if say["dis_kapi"] else "..."),
          "İç Kapılar": (f"{say['ic_kapi']} adet" + (f" ({oz_ie.pop('İç Kapılar')})" if oz_ie.get("İç Kapılar") else "")) if say["ic_kapi"] else (oz_ie.pop("İç Kapılar", None) or "..."),
          "Pencereler": f"{len(say['pencere'])} adet ({_olculer(say['pencere'])})" if say["pencere"] else "...",
          "Vasistaslar": f"{len(say['vasistas'])} adet ({_olculer(say['vasistas'])})" if say["vasistas"] else "yok",
          "Dış Boya Rengi": oz_ie.pop("Dış Cephe Boya", None) or oz_ie.pop("Dış Boya Rengi", None) or "...",
          "İç Boya Rengi": oz_ie.pop("İç Cephe Boya", None) or oz_ie.pop("İç Boya Rengi", None) or "...",
          "Köşe ve Söveler": oz_ie.pop("Köşe ve Söveler", None) or "..."}
    oz_ie.pop("Panel Türü", None); oz_ie.pop("İç Kapılar", None)
    diger = [f"{k}: {v}" for k, v in oz_ie.items() if v]
    return oz, diger


# ─────────────────────────────────────────────────────────────── ölçü zincirleri ──
def zincirler(plan: G.Plan) -> dict:
    """Dört yan için ölçü noktaları (cm). Uçlar dış ölçü kutusudur (veranda ve dikme dahil); ara noktalar o yana bakan dış çizgi köşeleri ve
    o yandaki dış duvara ulaşan duvarlar: iç duvarda aks, çevrede olmayan dış duvarda dışa (açık alana) bakan yüz (genel motorun
    `zincirler` kuralı). Parçaların toplamı her yanda dış ölçüye eşittir."""
    from shapely.geometry import Point
    bx0, by0, bx1, by1 = sinirlar(plan)
    cizgi = bina_cizgisi(plan)
    pts = list(cizgi.exterior.coords)[:-1]
    kenar = {"alt": [], "ust": [], "sol": [], "sag": []}
    for a, b in zip(pts, pts[1:] + pts[:1]):
        ex, ey = b[0] - a[0], b[1] - a[1]
        nx, ny = ey, -ex
        if abs(ey) < 1e-6:
            kenar["alt" if ny < 0 else "ust"].append((a[1], min(a[0], b[0]), max(a[0], b[0])))
        elif abs(ex) < 1e-6:
            kenar["sol" if nx < 0 else "sag"].append((a[0], min(a[1], b[1]), max(a[1], b[1])))
    tol = G.T_DIS + 3.0
    cik = {}
    for yan, ks in kenar.items():
        uclar = (bx0, bx1) if yan in ("alt", "ust") else (by0, by1)
        nok = {round(v, 2) for v in uclar} | {round(v, 2) for _, lo, hi in ks for v in (lo, hi)}
        for d in plan.duvarlar:
            if (d.yon == "y") != (yan in ("alt", "ust")) or not d.panolar:
                continue
            lo, hi = min(p.a0 for p in d.panolar), max(p.a1 for p in d.panolar)
            uc = lo if yan in ("alt", "sol") else hi
            if not any(abs(uc - sabit) <= tol and k_lo - 1 <= d.c <= k_hi + 1 for sabit, k_lo, k_hi in ks):
                continue
            if d.tur == "ic":
                nok.add(round(d.c, 2)); continue
            orta = (lo + hi) / 2
            disa = [f for f in (d.c - d.h, d.c + d.h)
                    if not cizgi.contains(Point((f + (1 if f > d.c else -1), orta) if d.yon == "y" else (orta, f + (1 if f > d.c else -1))))]
            nok.add(round(disa[0] if len(disa) == 1 else d.c, 2))
        cik[yan] = sorted(v for v in nok if uclar[0] - 1e-6 <= v <= uclar[1] + 1e-6)
    return cik


# ───────────────────────────────────────────────────────────────────────── plan ──
def plan_ciz(ax, plan: G.Plan, yazi: float = 1.0) -> dict:
    """Motor planını (cm) eksene çizer: mahaller, pano panoları, köşe ve dikmeler, her pano ekinde H profili, pencereler, D-15 kapı yayları,
    giriş oku, ölçü zincirleri, dört yan etiketi. `yazi`: yazı boyu çarpanı (pt). Dönen: ölçü zincirleri ve dış ölçü."""
    from matplotlib.patches import Arc, Polygon as MplPolygon, Rectangle
    from shapely.ops import polylabel
    from .genel import ciz_genel as CG

    bx0, by0, bx1, by1 = sinirlar(plan)
    fs = lambda pt: pt * yazi
    kapi_mantik = ((plan.is_emri.get("yapi") or {}).get("dizilim") or {}).get("kapi") == "mantik"
    # mahaller
    for ad, m in plan.mahaller.items():
        if m.poly is None or m.poly.is_empty:
            continue
        acik = m.acik or m.tur in G.ACIK_MAHAL_TURLERI
        renk = ACIK_RENGI if acik else CG.MAHAL_RENGI.get(MAHAL_ISLEVI.get(m.tur, m.tur), "#f2f2f2")
        for pg in _cokgenler(m.poly):
            ax.add_patch(MplPolygon(list(pg.exterior.coords), closed=True, fc=renk, ec="#7aa35c" if acik else "none", hatch="///" if acik else None,
                                    lw=0.4 if acik else 0, zorder=1))
        ana = max(_cokgenler(m.poly), key=lambda p: p.area)
        c = polylabel(ana, tolerance=1.0)
        kutu = dict(fc="white", ec="none", pad=1.2) if acik else None
        ax.text(c.x, c.y + 15, ad.upper(), ha="center", va="center", fontsize=fs(6.0), weight="bold", zorder=9, bbox=kutu)
        ax.text(c.x, c.y - 15, f"{m.alan_m2:.1f} m²".replace(".", ","), ha="center", va="center", fontsize=fs(5.8), zorder=9, bbox=kutu)
    # açık kenarlar (veranda)
    for (x0, y0, x1, y1, *_r) in plan.acik_kenarlar:
        ax.plot([x0, x1], [y0, y1], color="#7aa35c", lw=0.6, ls=(0, (4, 2)), zorder=2)
    # panolar, köşeler, dikmeler
    for d in plan.duvarlar:
        for p in d.panolar:
            for (x0, y0, x1, y1) in p.rects():
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=DUVAR_RENGI.get(d.tur, "#3a3a3a"), ec="none", zorder=3))
    for k in plan.koseler:
        x0, y0, x1, y1 = k.rect
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=KOSE_RENGI, ec="none", zorder=4))
    for (x0, y0, x1, y1) in plan.dikmeler:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=KOSE_RENGI, ec="none", zorder=5))
    # H birleştirme profili: her pano ekinde, dışarıdan 5 cm, eke tam ortalı (Lokman 13.10.2026 09:39); duvarı her yüzde 1 cm taşar
    w = G.H_PROFIL_GORUNEN_CM / 2.0
    for k in G.pano_ekleri(plan):
        t = k["h"] + 1.0
        x0, y0, x1, y1 = (k["e"] - w, k["c"] - t, k["e"] + w, k["c"] + t) if k["yon"] == "x" else (k["c"] - t, k["e"] - w, k["c"] + t, k["e"] + w)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=H_RENGI, ec=H_KENAR, lw=0.2, zorder=4.5))
    # açıklıklar
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if a is None:
                continue
            g = p.gap()
            if a.tur == "pencere":
                pay = 2.0
                x0, y0, x1, y1 = (g[0], g[1] - pay, g[2], g[3] + pay) if d.yon == "x" else (g[0] - pay, g[1], g[2] + pay, g[3])
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=CAM, ec=CERCEVE, lw=0.5, zorder=6))
                if d.yon == "x":
                    ax.plot([g[0], g[2]], [d.c, d.c], color=CERCEVE, lw=0.35, zorder=6.5)
                else:
                    ax.plot([d.c, d.c], [g[1], g[3]], color=CERCEVE, lw=0.35, zorder=6.5)
                n = a.disari_normal or ("-y" if d.yon == "x" else "-x")
                s = 1 if n[0] == "+" else -1
                et = G.pencere_yazisi(a.olcu)
                bb = dict(fc="white", ec="none", pad=0.6, alpha=0.85)
                if d.yon == "x":
                    ax.text((g[0] + g[2]) / 2, d.c + s * (d.h + 8), et, ha="center", va="bottom" if s > 0 else "top", fontsize=fs(5.0), color=ETIKET_MAVI,
                            zorder=9, bbox=bb)
                else:
                    ax.text(d.c + s * (d.h + 8), (g[1] + g[3]) / 2, et, ha="left" if s > 0 else "right", va="center", rotation=90, fontsize=fs(5.0),
                            color=ETIKET_MAVI, zorder=9, bbox=bb)
            elif a.tur in ("ic_kapi", "dis_kapi") and a.icine_normal:
                _kapi_ciz(ax, d, g, a, kapi_mantik)
                if a.tur == "dis_kapi":
                    s = -1 if a.icine_normal[0] == "+" else 1                 # dışarı
                    if d.yon == "x":
                        cx, yuz = (g[0] + g[2]) / 2, d.c + s * d.h
                        ax.annotate("GİRİŞ", xy=(cx, yuz + s * 3), xytext=(cx, yuz + s * 46), ha="center", va="top" if s < 0 else "bottom",
                                    fontsize=fs(5.4), color="#b03030", weight="bold", arrowprops=dict(arrowstyle="->", color="#b03030", lw=0.8), zorder=10)
                    else:
                        cy, yuz = (g[1] + g[3]) / 2, d.c + s * d.h
                        ax.annotate("GİRİŞ", xy=(yuz + s * 3, cy), xytext=(yuz + s * 46, cy), ha="right" if s < 0 else "left", va="center",
                                    fontsize=fs(5.4), color="#b03030", weight="bold", arrowprops=dict(arrowstyle="->", color="#b03030", lw=0.8), zorder=10)
    # ölçü zincirleri (dış yüzden) ve dış ölçüler
    z = zincirler(plan)
    olc = lambda p1, p2, v, kay, yatay=True: CG.olcu(ax, p1, p2, _f(v), kay, yatay=yatay, fs=fs(5.2))
    for a_, b_ in zip(z["alt"], z["alt"][1:]):
        olc((a_, by0 - 52), (b_, by0 - 52), b_ - a_, 3)
    olc((bx0, by0 - 92), (bx1, by0 - 92), bx1 - bx0, 3)
    for a_, b_ in zip(z["ust"], z["ust"][1:]):
        olc((a_, by1 + 44), (b_, by1 + 44), b_ - a_, 3)
    for a_, b_ in zip(z["sol"], z["sol"][1:]):
        olc((bx0 - 44, a_), (bx0 - 44, b_), b_ - a_, -4, yatay=False)
    olc((bx0 - 84, by0), (bx0 - 84, by1), by1 - by0, -4, yatay=False)
    for a_, b_ in zip(z["sag"], z["sag"][1:]):
        olc((bx1 + 44, a_), (bx1 + 44, b_), b_ - a_, 4, yatay=False)
    # dört yan
    kutu = dict(boxstyle="round,pad=0.35", fc=ETIKET_MAVI, ec="none")
    ek = dict(fontsize=fs(6.4), weight="bold", color="white", bbox=kutu, zorder=20)
    ax.text((bx0 + bx1) / 2, by0 - 138, ETIKET["on"], ha="center", va="center", **ek)
    ax.text((bx0 + bx1) / 2, by1 + 100, ETIKET["arka"], ha="center", va="center", **ek)
    ax.text(bx0 - 138, (by0 + by1) / 2, ETIKET["sol"], ha="center", va="center", rotation=90, **ek)
    ax.text(bx1 + 100, (by0 + by1) / 2, ETIKET["sag"], ha="center", va="center", rotation=-90, **ek)
    ax.set_xlim(bx0 - 168, bx1 + 128)
    ax.set_ylim(by0 - 168, by1 + 128)
    ax.set_aspect("equal")
    ax.axis("off")
    return {"zincirler_cm": z, "dis_olcu_cm": [round(bx1 - bx0, 2), round(by1 - by0, 2)]}


def _kapi_ciz(ax, d, g, a, kapi_mantik: bool = False) -> None:
    """Kapı kanadı (açık konumda) ve açılım yayı: menteşe `mentese_ucu` ucunda, kanat `icine_normal` yönünde (D-15), boy = boşluk eni.
    Menteşe ucu bayi görseliyle aynı kuraldan (`bayi_gorseli._mentese_a0_ucunda`): dış kapıda DXF sembolü yalnız `dizilim.kapi: mantik`
    varken menteşeye göre aynalanır, yoksa "sol" = a0 (BK-12 geometri hakemi 3. tur)."""
    from matplotlib.patches import Arc
    from . import bayi_gorseli as BG
    a0, a1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
    L = a1 - a0
    uc = 0 if BG._mentese_a0_ucunda(a, kapi_mantik) else 1
    hm = a0 if uc == 0 else a1
    s = 1 if a.icine_normal[0] == "+" else -1
    if d.yon == "x":
        hx, hy = hm, d.c + s * d.h
        ucx, ucy = hx, hy + s * L
        kapali, acik = (0.0 if uc == 0 else 180.0), (90.0 if s > 0 else 270.0)
    else:
        hx, hy = d.c + s * d.h, hm
        ucx, ucy = hx + s * L, hy
        kapali, acik = (90.0 if uc == 0 else 270.0), (0.0 if s > 0 else 180.0)
    ax.plot([hx, ucx], [hy, ucy], color=KAPI_RENGI, lw=0.9, zorder=7, solid_capstyle="butt")
    t1, t2 = sorted([kapali % 360, acik % 360])
    if t2 - t1 > 180:
        t1, t2 = t2, t1 + 360
    ax.add_patch(Arc((hx, hy), 2 * L, 2 * L, theta1=t1, theta2=t2, color=KAPI_RENGI, lw=0.5, ls=(0, (3, 2)), zorder=7))


# ─────────────────────────────────────────────────────────────────── çatı planı ──
def cati_tanimi(plan: G.Plan, ie: dict) -> dict | None:
    """İş Emri'nin `cati` alanından genel motorun çatı düzlemleri (yalnız beşik; Motor'un IFC'si de beşik kurar). Mahya, makas ekseni "x"
    ise (kısa kenar, varsayılan) y boyunca ortada; "y" ise x boyunca. Saçak her yanda `sacak_cm`. Beşik dışı tip: None (çatı planı yok)."""
    c = ie.get("cati") or {}
    if c.get("tip", "besik") != "besik":
        return None
    s = float(c.get("sacak_cm", 30)); eg = float(c.get("egim_yuzde", 33)) / 100.0; top = float(c.get("topuk_cm", 10))
    H0 = float(ie.get("yapi", {}).get("duvar_yuksekligi_cm", 250))
    zs = H0 + top
    x0, y0, x1, y1 = sinirlar(plan)
    if c.get("makas_ekseni", "x") == "x":
        xm = (x0 + x1) / 2
        dz = [{"ad": "sol", "plan": [[x0 - s, y0 - s], [xm, y0 - s], [xm, y1 + s], [x0 - s, y1 + s]], "yukari": [1, 0], "egim": eg, "sacak_kotu": zs, "sacak": {"x": x0 - s}},
              {"ad": "sağ", "plan": [[xm, y0 - s], [x1 + s, y0 - s], [x1 + s, y1 + s], [xm, y1 + s]], "yukari": [-1, 0], "egim": eg, "sacak_kotu": zs, "sacak": {"x": x1 + s}}]
    else:
        ym = (y0 + y1) / 2
        dz = [{"ad": "ön", "plan": [[x0 - s, y0 - s], [x1 + s, y0 - s], [x1 + s, ym], [x0 - s, ym]], "yukari": [0, 1], "egim": eg, "sacak_kotu": zs, "sacak": {"y": y0 - s}},
              {"ad": "arka", "plan": [[x0 - s, ym], [x1 + s, ym], [x1 + s, y1 + s], [x0 - s, y1 + s]], "yukari": [0, -1], "egim": eg, "sacak_kotu": zs, "sacak": {"y": y1 + s}}]
    return {"tip": "besik", "sacak": s, "topuk": top, "duvar_ustu": H0, "duzlemler": dz}


def cati_plani_ciz(ax, plan: G.Plan, ie: dict, yazi: float = 1.0) -> bool:
    """Beşik çatı planı: iki düzlem, mahya, duvarların dış çizgisi (beyaz kesik), eğim okları ve yüzdesi, dış ölçüler. Renkler genel motorun
    çatı planıyla aynı (`ciz_genel.cati_plani_eksen`); yazılar bu küçük kutuya göre. Geometri yalnız İş Emri'nin `cati` alanından."""
    from matplotlib.patches import Polygon as MplPolygon
    from .genel import ciz_genel as CG
    tanim = cati_tanimi(plan, ie)
    if tanim is None:
        ax.text(0.5, 0.5, "çatı planı yalnız beşikte çiziliyor", ha="center", va="center", fontsize=6.5 * yazi, color="#8a8a8a", transform=ax.transAxes)
        ax.axis("off")
        return False
    dz = tanim["duzlemler"]
    xs = [p[0] for d in dz for p in d["plan"]]; ys = [p[1] for d in dz for p in d["plan"]]
    X0, X1, Y0, Y1 = min(xs), max(xs), min(ys), max(ys)
    for d in dz:
        ax.add_patch(MplPolygon(d["plan"], closed=True, fc="#8a919c", ec="#2f343c", lw=0.7, zorder=1))
    hat = list(bina_cizgisi(plan).exterior.coords)
    ax.plot([p[0] for p in hat], [p[1] for p in hat], color="white", lw=0.6, ls=(0, (4, 2.5)), zorder=3)
    ortak = sorted({tuple(p) for p in dz[0]["plan"]} & {tuple(p) for p in dz[1]["plan"]})       # mahya: iki düzlemin ortak kenarı
    (mx0, my0), (mx1, my1) = ortak[0], ortak[-1]
    ax.plot([mx0, mx1], [my0, my1], color="#1c1f24", lw=1.4, zorder=4)
    boy = math.hypot(mx1 - mx0, my1 - my0)
    for d in dz:
        ux, uy = d["yukari"]
        xs_, ys_ = [p[0] for p in d["plan"]], [p[1] for p in d["plan"]]
        cx, cy = (min(xs_) + max(xs_)) / 2, (min(ys_) + max(ys_)) / 2
        ax.annotate("", xy=(cx - ux * 45, cy - uy * 45), xytext=(cx + ux * 45, cy + uy * 45), arrowprops=dict(arrowstyle="->", color="white", lw=0.9), zorder=6)
        tx, ty = (cx, cy + 60) if ux != 0 else (cx + 70, cy)          # yüzde okun yanında, oka binmeden (okun dik yönünde)
        ax.text(tx, ty, f"%{d['egim'] * 100:g}", ha="center", va="center", fontsize=5.8 * yazi, color="white", zorder=6)
    CG.olcu(ax, (X0, Y0 - 34), (X1, Y0 - 34), _f(X1 - X0), -3, fs=5.6 * yazi)
    CG.olcu(ax, (X0 - 34, Y0), (X0 - 34, Y1), _f(Y1 - Y0), -4, yatay=False, fs=5.6 * yazi)
    ax.text((X0 + X1) / 2, Y0 - 110, f"mahya {_f(boy)} · saçak {_f(tanim['sacak'])}", ha="center", va="center", fontsize=5.4 * yazi, color="#333")
    ax.set_xlim(X0 - 80, X1 + 20)
    ax.set_ylim(Y0 - 140, Y1 + 20)
    ax.set_aspect("equal")
    ax.set_anchor("N")
    ax.axis("off")
    return True


# ─────────────────────────────────────────────────────────────────── perspektif ──
def perspektif_uret(ie: dict, hedef: Path, govde: str) -> dict:
    """Motor'un IFC'si (pano ekleri dahil) → iki perspektif PNG. Ayrı süreçte: VTK çökmesi ya da zaman aşımı sayfayı düşürmez. Ekran yoksa
    ve `xvfb-run` varsa onunla (yerel); sunucuda OSMesa'lı VTK doğrudan çizer."""
    from importlib.util import find_spec
    try:
        if find_spec("vtk") is None:
            return {"durum": "ÇİZİLEMEDİ", "neden": "VTK kurulu değil"}
    except Exception as e:  # pragma: no cover
        return {"durum": "ÇİZİLEMEDİ", "neden": f"VTK denetlenemedi: {e}"}
    from . import ifc_uret
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    ifc = hedef / f"{govde}_sunum.ifc"
    ifc_ozet = ifc_uret.uret(ie, ifc)
    komut = [sys.executable, "-m", "motor.sunum", "perspektif", str(ifc), str(hedef), govde]
    if not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        komut = ["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24"] + komut
    t0 = time.time()
    try:
        r = subprocess.run(komut, cwd=str(KOK), capture_output=True, text=True, timeout=PERSPEKTIF_ZAMAN_ASIMI_S)
    except subprocess.TimeoutExpired:
        return {"durum": "ÇİZİLEMEDİ", "neden": f"zaman aşımı ({PERSPEKTIF_ZAMAN_ASIMI_S} s)", "ifc": ifc.name, "ifc_ozet": ifc_ozet}
    dosyalar = {ad: hedef / f"{govde}_{ad}.png" for ad, _ in GORUNUMLER}
    if r.returncode == 0 and all(p.is_file() for p in dosyalar.values()):
        return {"durum": "TAMAM", "sure_s": round(time.time() - t0, 1), "ifc": ifc.name, "ifc_ozet": ifc_ozet,
                "dosyalar": {ad: str(p) for ad, p in dosyalar.items()}}
    neden = f"süreç çöktü, sinyal {-r.returncode}" if r.returncode < 0 else f"çıkış {r.returncode}"
    return {"durum": "ÇİZİLEMEDİ", "neden": f"{neden}: {(r.stderr or '').strip()[-300:]}", "ifc": ifc.name, "ifc_ozet": ifc_ozet}


def _perspektif_cocuk(ifc: Path, hedef: Path, govde: str) -> int:
    from .genel import perspektif as P
    f, sekiller = P.ucgenle(ifc)
    print("yazıldı:", ", ".join(P.ciz(f, sekiller, hedef, govde, uzaklik=PERSPEKTIF_UZAKLIK, yalniz=tuple(ad for ad, _ in GORUNUMLER))))
    return 0


def kirp(yol: Path):
    """Perspektif görüntüsünü yapıya kırpar: gök (açık mavi-beyaz) ve zemin (sol alt köşenin rengi) dışındaki piksellerin kutusu + %3 pay."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(yol).convert("RGB")).astype(int)
    zemin = a[-1, 0]
    gok = (a[..., 0] > 200) & (a[..., 1] > 210) & (a[..., 2] > 220) & (a[..., 2] >= a[..., 0])
    yapi = (np.abs(a - zemin).sum(-1) > 24) & ~gok
    if not yapi.any():
        return a.astype("uint8")
    sat, sut = np.where(yapi.any(1))[0], np.where(yapi.any(0))[0]
    py, px = int(0.03 * a.shape[0]), int(0.03 * a.shape[1])
    return a[max(0, sat[0] - py):min(a.shape[0], sat[-1] + py + 1), max(0, sut[0] - px):min(a.shape[1], sut[-1] + px + 1)].astype("uint8")


# ─────────────────────────────────────────────────────────────── bileşik görsel ──
def bilesik_ciz(fig, kutu: tuple, plan: G.Plan, ie: dict, persp: dict, say: dict, en: float, boy: float, yazi: float = 1.0) -> dict:
    """Bayi görselini figürde `kutu` (pt; x0, y0, x1, y1; y yukarıdan, şablon koordinatı) içine yerleştirir. Plan dikeyse (derinlik > en):
    solda çatı planı ve pano dizilimi notu, ortada plan, sağda iki perspektif; yataysa üstte plan, altta çatı planı ve iki perspektif."""
    x0, y0, x1, y1 = kutu
    W, H = x1 - x0, y1 - y0

    def eksen(a0, b0, a1, b1):
        return fig.add_axes([a0 / en, (boy - b1) / boy, (a1 - a0) / en, (b1 - b0) / boy])

    def yazi_pt(x, y, s, pt, **kw):
        fig.text(x / en, (boy - y) / boy, s, fontsize=pt * yazi, **kw)

    def resim(a0, b0, a1, b1, ad, baslik):
        yazi_pt((a0 + a1) / 2, b0 + 5, baslik, 7.0, ha="center", va="center", weight="bold", color="#222")
        ax = eksen(a0, b0 + 12, a1, b1)
        ax.axis("off")
        yol = (persp.get("dosyalar") or {}).get(ad)
        if persp.get("durum") == "TAMAM" and yol and Path(yol).is_file():
            ax.imshow(kirp(Path(yol)), interpolation="lanczos")
            ax.set_anchor("N")
        else:
            ax.add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle((0.02, 0.1), 0.96, 0.8, transform=ax.transAxes, fc="#f4f4f4",
                                                                                         ec="#bbbbbb", lw=0.6, ls=(0, (3, 2))))
            ax.text(0.5, 0.5, "perspektif çizilemedi", ha="center", va="center", fontsize=7 * yazi, color="#8a8a8a", transform=ax.transAxes)

    not_satirlari = ["Pano dizilimi (125,5 cm aks):", f"   {say['pano_dis']} dış + {say['pano_ic']} iç pano", "H birleştirme profili:",
                     f"   {say['h_pano_eki']} pano eki + {say['h_uclu']} üçlü", f"Köşe {say['kose']}" + (f" · dikme {say['dikme']}" if say["dikme"] else ""),
                     "Açık renkli çentik: H profili", "   (dışarıdan 5 cm, eke ortalı)", "Ölçüler cm, dış yüzden;", "   iç duvarda aks.",
                     "TASLAK: bayi onayı içindir,", "   üretim projesi değildir."]
    bx0, by0, bx1, by1 = sinirlar(plan)
    gap = 10.0
    if (by1 - by0) > (bx1 - bx0):                                      # dikey plan
        w_cati, w_plan = 0.17 * W, 0.48 * W
        w_p = W - w_cati - w_plan - 2 * gap
        ax_plan = eksen(x0 + w_cati + gap, y0, x0 + w_cati + gap + w_plan, y1)
        yazi_pt(x0 + w_cati / 2, y0 + 5, "ÇATI PLANI", 7.0, ha="center", va="center", weight="bold", color="#222")
        cati_alt = y0 + 12 + 0.52 * H
        cati_plani_ciz(eksen(x0, y0 + 12, x0 + w_cati, cati_alt), plan, ie, yazi=yazi)
        for i, s in enumerate(not_satirlari):
            yazi_pt(x0 + 2, cati_alt + 12 + i * 9.6, s, 5.6, ha="left", va="center", color="#333")
        h_slot = (H - gap) / 2
        for i, (ad, baslik) in enumerate(GORUNUMLER):
            b0 = y0 + i * (h_slot + gap)
            resim(x1 - w_p, b0, x1, b0 + h_slot, ad, baslik)
    else:                                                              # yatay plan
        h_plan = 0.6 * H
        ax_plan = eksen(x0, y0, x1 - 0.2 * W, y0 + h_plan)
        for i, s in enumerate(not_satirlari):
            yazi_pt(x1 - 0.2 * W + 6, y0 + 20 + i * 9.6, s, 5.6, ha="left", va="center", color="#333")
        b0 = y0 + h_plan + gap
        w_cati = 0.22 * W; w_p = (W - w_cati - 2 * gap) / 2
        yazi_pt(x0 + w_cati / 2, b0 + 5, "ÇATI PLANI", 7.0, ha="center", va="center", weight="bold", color="#222")
        cati_plani_ciz(eksen(x0, b0 + 12, x0 + w_cati, y1), plan, ie, yazi=yazi)
        for i, (ad, baslik) in enumerate(GORUNUMLER):
            a0 = x0 + w_cati + gap + i * (w_p + gap)
            resim(a0, b0, a0 + w_p, y1, ad, baslik)
    return plan_ciz(ax_plan, plan, yazi=yazi)


# ──────────────────────────────────────────────────────────────── bayi paftası ──
def motor_dogrulamasi(ie: dict) -> dict:
    """K23: Motor'un DXF'i kaydedilip yeniden açılarak doğrulanır (`dxf_out.uret`, geçici klasörde). Dönen: geçti mi ve ilk hatalar."""
    from . import dxf_out
    with tempfile.TemporaryDirectory(prefix="portman_sunum_") as td:
        m = dxf_out.uret(ie, Path(td), ad_govde="dogrulama")
        v = json.loads((Path(td) / "validation.json").read_text(encoding="utf-8"))
    return {"passed": m.get("validation_passed") is True, "errors": list(v.get("errors") or [])[:10]}


def bayi_paftasi(ie: dict, hedef: Path, perspektif: bool = True, bilgi: dict | None = None, dogrulama: dict | None = None) -> dict:
    """İş Emri → `<kod>_bayi.pdf` (A4 yatay, 1 sayfa, antetli) ve `<kod>_plan_bayi.png` (bileşik görsel, başlıklı). `bilgi`: antet alanları
    (tarih, sevk adresi, bayi telefonu …; yoksa İş Emri'nden ya da "..."). `dogrulama`: Motor'un doğrulaması (verilmezse burada koşulur)."""
    import matplotlib
    from .genel import sablon_pafta as SP
    from .genel.uret import matplotlib_sabitle

    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    govde = dosya_govdesi(ie); kod = kod_adi(ie)
    dogrulama = dogrulama if dogrulama is not None else motor_dogrulamasi(ie)
    gecti = dogrulama.get("passed") is True
    plan = G.kur(ie)
    say = sayimlar(plan)
    oz, diger = ozellikler(ie, say)
    no = ie.get("is_emri_no") or kod; rev = int(ie.get("revizyon") or 1)
    bayi = (ie.get("talep") or {}).get("bayi") or {}
    bilgi = dict(bilgi or {})
    bilgi.setdefault("is_emri_no", no); bilgi.setdefault("revizyon", rev)
    bilgi.setdefault("proje_adi", f"{kod} · {say['oturum_m2']:.0f} M² · {say['oda_programi']} PREFABRİK KONUT")
    bilgi.setdefault("bayi_adi", bayi.get("ad"))
    bilgi.setdefault("ozel_istekler", list(ie.get("ozel_istekler") or []) + diger)
    persp = perspektif_uret(ie, hedef, govde) if perspektif else {"durum": "ÇİZİLMEDİ", "neden": "perspektifsiz istendi"}
    taslak = f"TASLAK · r{rev:02d} · {no}"
    pdf = hedef / (f"{govde}_bayi.pdf" if gecti else f"{govde}_bayi.HATALI.pdf")
    png = hedef / f"{govde}_plan_bayi.png"
    with matplotlib.rc_context():
        matplotlib_sabitle()
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        SP.fontlari_hazirla()
        # 1) antetli sayfa
        fig = plt.figure(figsize=(SP.EN / 72, SP.BOY / 72))
        sf = SP.Sayfa(fig)
        SP.cerceveler(sf, {"kod": kod, "aile": "tek_kat_prefabrik"}, oz, bilgi, say["oturum_m2"])
        a0, b0, a1, b1 = SP.ANTET_SOL                                  # şablonda boş; başlık ve TASLAK buraya (Lokman 09:38)
        sf.yazi(a0 + 9, b0 + 15, "TASLAK", 15.0, renk=SP.KOYU_KIRMIZI, va="center", weight="bold")
        sf.yazi(a0 + 86, b0 + 11, f"r{rev:02d} · {no}", 7.3, va="center")
        sf.yazi(a0 + 86, b0 + 22, f"{kod} · {say['oturum_m2']:.0f} m² · {say['oda_programi']}", 7.3, va="center")
        sf.yazi(a0 + 9, b0 + 38, "Bayi onayı içindir; üretim projesi değildir." + ("" if gecti else "  DOĞRULAMA GEÇMEDİ"), 6.6,
                renk=SP.GRI if gecti else SP.KIRMIZI, va="center")
        ozet_plan = bilesik_ciz(fig, (SP.ANA[0] + 8, SP.ANA[1] + 8, SP.ANA[2] - 8, SP.ANA[3] - 6), plan, ie, persp, say, SP.EN, SP.BOY)
        with PdfPages(pdf, metadata={"Title": f"{kod} bayi paftası", "Creator": "Portman", "Producer": "Portman", "CreationDate": None, "ModDate": None}) as pp:
            pp.savefig(fig)
        plt.close(fig)
        # 2) tek başına bileşik görsel (başlık görselin üstünde)
        fig2 = plt.figure(figsize=(SP.EN / 72, SP.BOY / 72))
        fig2.text(16 / SP.EN, 1 - 16 / SP.BOY, f"{kod} · {say['oturum_m2']:.0f} m² · {say['oda_programi']}", fontsize=12.5, weight="bold", ha="left", va="center")
        fig2.text(16 / SP.EN, 1 - 31 / SP.BOY, taslak + ("" if gecti else " · DOĞRULAMA GEÇMEDİ"), fontsize=8.5, ha="left", va="center",
                  color="#b03030" if not gecti else "#555")
        bilesik_ciz(fig2, (14, 42, SP.EN - 14, SP.BOY - 10), plan, ie, persp, say, SP.EN, SP.BOY)
        for dpi in (200, 150, 110):
            fig2.savefig(png, dpi=dpi, facecolor="white")
            if png.stat().st_size <= PNG_SINIRI:
                break
        plt.close(fig2)
    ozet = {"kod": kod, "is_emri_no": no, "revizyon": rev, "dogrulama": dogrulama, "teslim": gecti, "sayfa_pt": [SP.EN, SP.BOY],
            "sayimlar": say, "ozellikler": oz, "ozel_istekler": bilgi["ozel_istekler"], **ozet_plan,
            "perspektif": {k: v for k, v in persp.items() if k != "dosyalar"}, "dosyalar": [pdf.name, png.name]}
    (hedef / f"{govde}_bayi_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return ozet


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["perspektif"]:                                    # iç kullanım: ayrı süreçte VTK çizimi
        return _perspektif_cocuk(Path(argv[1]), Path(argv[2]), argv[3])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", type=Path); ap.add_argument("cikti", type=Path)
    ap.add_argument("--perspektifsiz", action="store_true")
    a = ap.parse_args(argv)
    ie = json.loads(a.is_emri.read_text(encoding="utf-8"))
    o = bayi_paftasi(ie, a.cikti, perspektif=not a.perspektifsiz)
    print(("yazıldı: " if o["teslim"] else "DOĞRULAMA GEÇMEDİ, tanı: ") + ", ".join(o["dosyalar"]), f"· perspektif {o['perspektif']['durum']}")
    return 0 if o["teslim"] else 2


if __name__ == "__main__":
    sys.exit(main())
