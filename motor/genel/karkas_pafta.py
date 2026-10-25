#!/usr/bin/env python3
"""Duvar panelleri yerleşim planı (İE-16 PR-3a): karkas kuralının bölmesi pafta olarak.

Yalnız tanım karkas kuralını isterse çizilir (`"karkas": "kural"`; `uret` çağırır); istemeyen tanımın çizim seti değişmez. Açık
paftalardaki düzen: planın üstünde her duvar paneli adıyla (D01…) ve boyuyla, panel ekleri duvarı kesen çizgiyle; kolon ve kirişler
K01… (önce kolonlar, sonra kirişler; tanımdaki sırayla). Yanında panel tablosu: sınıf, profil, boy × yükseklik, açıklıklar, profil boyu.
Bölme ve adlar `karkas.kur`'dan gelir; bu modül hesap yapmaz, yalnız çizer.

    python -m motor.genel.karkas_pafta tanim.json <çıktı klasörü>
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402

from . import ciz_genel, karkas, yapi  # noqa: E402

PANEL_RENGI = {"dis": ("#c9d9ec", "#9fbbdc"), "ic": ("#e4ddc9", "#cfc3a1"), "ek": ("#c9d9ec", "#9fbbdc"), "korkuluk": ("#dcdcdc", "#c4c4c4")}
SINIF_ADI = {"dis": "dış", "ic": "iç", "ek": "ek yapı", "korkuluk": "korkuluk"}
KOLON_RENGI = "#e8b04a"


def dosya_adlari(kod: str) -> tuple[str, str]:
    return f"{kod}_duvar_panelleri.png", f"{kod}_duvar_panelleri.pdf"


def _kutu(ax, k, fc, ec="#333", lw=0.5, z=4, hatch=None):
    x0, y0, x1, y1 = k
    ax.add_patch(MplPolygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, fc=fc, ec=ec, lw=lw, zorder=z, hatch=hatch))


def kolon_kiris(y: dict, t: dict, kk: dict) -> list[dict]:
    """K01…: önce kolonlar, sonra kirişler (tanımdaki sırayla)."""
    out = []
    for x in kk["kolonlar"]:
        out.append({"tur": "kolon", "tanim_adi": x["ad"], "kutu": y["adli"][x["ad"]]["kutu"], "olcu": f"h {ciz_genel.sade(x['yukseklik_cm'])}",
                    "profil_boyu_m": x["profil_boyu_m"]})
    kutular = {kr["ad"]: kr["kutu"] for kr in t.get("kirisler", [])}
    for x in kk["kirisler"]:
        out.append({"tur": "kiriş", "tanim_adi": x["ad"], "kutu": kutular[x["ad"]], "olcu": f"L {ciz_genel.sade(x['boy_cm'])}", "profil_boyu_m": x["profil_boyu_m"]})
    for i, x in enumerate(out, 1):
        x["ad"] = f"K{i:02d}"
    return out


def plan(ax, y: dict, t: dict, kk: dict, ks: list[dict]) -> None:
    """Plan: mahaller soluk, duvar panelleri renkli (komşular iki tonla), adlar ve boylar; kolon ve kirişler K01…."""
    for b in y["bolgeler"].values():
        if b["sinif"] == "dis":
            continue
        for p in ciz_genel._cokgenler(b["net"]):
            ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc="#f6f6f2" if b["sinif"] != "veranda" else "#eef4e8", ec="none", zorder=1))
        c = b["net"].representative_point()
        cx, cy = b.get("etiket_yeri", (c.x, c.y))
        ax.text(cx, cy, b["ad"].upper(), ha="center", va="center", fontsize=7.0, color="#8a8a8a", zorder=2)
    for d in y["duvarlar"]:                                   # kuralın dışındaki duvarlar (baca): gri
        if d["sinif"] not in karkas.DUVAR_SINIFLARI and d["sinif"] != "kolon":
            _kutu(ax, d["kutu"], "#bdbdbd", ec="none", z=3)
    sira = {}
    for p in kk["paneller"]:
        ton = sira.get(tuple(p["kosu"]), 0)
        sira[tuple(p["kosu"])] = 1 - ton
        _kutu(ax, p["kutu"], PANEL_RENGI[p["sinif"]][ton], ec="#2b2b2b", lw=0.6, z=4)
    for a in y["acikliklar"]:                                 # açıklıklar: panelin üstünde beyaz boşluk
        k = ciz_genel.aciklik_kutusu(y, a, pay=0.0).bounds
        _kutu(ax, k, "white" if a["tur"] != "pencere" else "#e3f1fb", ec="#1f5f93" if a["tur"] == "pencere" else "#8a4b2a", lw=0.6, z=5)
    for x in ks:
        _kutu(ax, x["kutu"], KOLON_RENGI if x["tur"] == "kolon" else "none", ec="#8a5a00", lw=0.9 if x["tur"] == "kolon" else 0.8, z=6,
              hatch=None if x["tur"] == "kolon" else "////")
    hat = ciz_genel.dis_hat(y)
    bx0, by0 = min(q[0] for h in hat for q in h), min(q[1] for h in hat for q in h)
    bx1, by1 = max(q[0] for h in hat for q in h), max(q[1] for h in hat for q in h)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    konan: list[tuple[float, float]] = []                     # yazı yerleri: kısa panellerde (çıkma köşeleri) yazılar binmesin
    for p in kk["paneller"]:                                  # ad ve boy: dış panelde dışarıya, içte panelin yanına
        x0, y0, x1, y1 = p["kutu"]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        metin = f"{p['ad']}\n{ciz_genel.sade(p['boy_cm'])}"
        yatay = (x1 - x0) >= (y1 - y0)
        dis_taraf = (1 if my >= cy else -1) if yatay else (1 if mx >= cx else -1)
        aralik = 8.0
        while True:
            yer = (mx, (y1 + aralik) if dis_taraf > 0 else (y0 - aralik)) if yatay else (((x1 + aralik) if dis_taraf > 0 else (x0 - aralik)), my)
            if all(abs(yer[0] - a) > 45 or abs(yer[1] - b) > 30 for a, b in konan) or aralik > 100:
                break
            aralik += 28.0
        konan.append(yer)
        if yatay:
            ax.text(*yer, metin, ha="center", va="bottom" if dis_taraf > 0 else "top", fontsize=6.4, color="#14365e", zorder=8, linespacing=1.05)
        else:
            ax.text(*yer, metin, ha="left" if dis_taraf > 0 else "right", va="center", fontsize=6.4, color="#14365e", zorder=8, linespacing=1.05)
    for x in ks:
        x0, y0, x1, y1 = x["kutu"]
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, x["ad"], ha="center", va="center", fontsize=6.0, color="#5a3a00", weight="bold", zorder=9,
                bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))
    ax.set_xlim(bx0 - 90, bx1 + 90)
    ax.set_ylim(by0 - 90, by1 + 90)
    ax.set_aspect("equal")
    ax.axis("off")


def tablo(ax, kk: dict, ks: list[dict]) -> None:
    ax.axis("off")
    satirlar = [f"{'Ad':4s} {'Sınıf':8s} {'Profil':14s} {'Boy × yük.':>13s}  {'Profil boyu':>11s}  Açıklık"]
    for p in kk["paneller"]:
        satirlar.append(f"{p['ad']:4s} {SINIF_ADI[p['sinif']]:8s} {(p['profil'] or '').replace('x', ' × '):14s} "
                        f"{ciz_genel.sade(p['boy_cm']) + ' × ' + ciz_genel.sade(p['yukseklik_cm']):>13s}  {ciz_genel.tr(p['profil_boyu_m'], 2) + ' m':>11s}  "
                        f"{len(p['acikliklar']) or ''}")
    satirlar.append("")
    for x in ks:
        satirlar.append(f"{x['ad']:4s} {x['tur']:8s} {'':14s} {x['olcu']:>13s}  {ciz_genel.tr(x['profil_boyu_m'], 2) + ' m':>11s}")
    boy = sum(p["profil_boyu_m"] for p in kk["paneller"]) + sum(x["profil_boyu_m"] for x in ks)
    satirlar += ["", f"Toplam profil boyu {ciz_genel.tr(boy, 1)} m"]
    ax.text(0.0, 1.0, "\n".join(satirlar), ha="left", va="top", fontsize=6.6, family="DejaVu Sans Mono", linespacing=1.32, transform=ax.transAxes)


def ciz(t: dict, hedef: Path, kod: str, kural: dict | None = None) -> dict:
    """PNG ve tek sayfa PDF yazar; kaydı döner (yollar, panel sayıları, kuralın sha'sı)."""
    if t.get("karkas") != "kural":
        raise SystemExit("Duvar panelleri paftası yalnız karkas kuralını isteyen tanımda çizilir (`karkas: kural`).")
    k = kural or karkas.oku()
    y = yapi.kur(t)
    kk = karkas.kur(y, t, k)
    ks = kolon_kiris(y, t, kk)
    fig = plt.figure(figsize=(16.5, 11.7), dpi=140)                    # A3 yatay
    gs = GridSpec(1, 2, figure=fig, width_ratios=[2.35, 1.0], wspace=0.02)
    plan(fig.add_subplot(gs[0, 0]), y, t, kk, ks)
    tablo(fig.add_subplot(gs[0, 1]), kk, ks)
    sayi = {s: sum(1 for p in kk["paneller"] if p["sinif"] == s) for s in karkas.DUVAR_SINIFLARI}
    ozet = " · ".join(f"{SINIF_ADI[s]} {n}" for s, n in sayi.items() if n) + f" · kolon-kiriş {len(ks)}"
    fig.suptitle(f"{t['kod']} · DUVAR PANELLERİ YERLEŞİM PLANI   —   TASLAK · panel bölmesi karkas kuralından · üretim projesi değildir",
                 fontsize=12, weight="bold", x=0.02, ha="left", y=0.975)
    fig.text(0.02, 0.945, f"Duvar paneli {sum(sayi.values())} ({ozet}). Ölçüler cm; panelin yanındaki sayı boyu. "
             f"Kural: {kk['kural']['yol']} (sha {kk['kural']['sha256'][:12]}).", fontsize=8.4, ha="left")
    png_ad, pdf_ad = dosya_adlari(kod)
    hedef = Path(hedef)
    fig.savefig(hedef / png_ad, facecolor="white")
    with PdfPages(hedef / pdf_ad, metadata={"Title": f"{t['kod']} duvar panelleri", "Creator": "Portman", "Producer": "Portman",
                                           "CreationDate": None, "ModDate": None}) as pp:
        pp.savefig(fig, facecolor="white")
    plt.close(fig)
    return {"png": png_ad, "pdf": pdf_ad, "duvar_paneli": sayi, "kolon_kiris": len(ks), "kural": kk["kural"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path); ap.add_argument("cikti", type=Path)
    a = ap.parse_args()
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    a.cikti.mkdir(parents=True, exist_ok=True)
    print(json.dumps(ciz(t, a.cikti, t["kod"].replace("Ç", "C").replace("-", "")), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
