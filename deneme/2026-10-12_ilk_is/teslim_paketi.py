#!/usr/bin/env python3
"""Bayi talebi (12 Ekim 2026): seçilen çizimin bayi ve mühendis paketleri. Lokman, 13:17: "seçenek 2 olacak ayırabilir misin?"; 13:49: çift cumba, 1 m veranda.

Bayiye: teslim/T1012C_bayi.pdf
  1. sunum sayfası (plan, iki ön perspektif, ön görünüş)
  2. çizim paftası
  3. dört perspektif
Mühendise: teslim/T1012C_muhendis.zip
  IFC, yükleme listesi (PDF ve md), pafta, makaslı ve çatısız görünüş
Yükleme listesi bayiye gitmez (CIO kararı). Görseller genel motorun çizim setinden; burada yalnız dizilir. Ad, telefon, fiyat içermez.
Antet yok: sayfalarda başlık ve TASLAK satırı yok (Lokman, 12 Ekim 2026 15:30: "anteti kaldıralım"; Portman'ın ilk gerçek işi).
Kullanım: python teslim_paketi.py <KOD> "<sunum alt notu>"   (KOD: T1012C, T1012CV)
"""
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

K = Path(__file__).resolve().parent
KOD = sys.argv[1]
ALT_NOT = sys.argv[2]
C = K / f"cizimler/{KOD}_A"
T = K / "teslim"
T.mkdir(exist_ok=True)
A4Y = (16.54, 11.69)   # A3 yatay (inç); PDF'te sayfa oranı korunur
PLAN_ALT = 0.85        # plan görselinde planın bittiği yer: antetsiz görselde plan 0,841'de biter, açıklamalar 0,862'de başlar


def ac(ad):
    return Image.open(C / ad).convert("RGB")


def kirp_beyaz(im, esik=245, pay=12):
    b = im.convert("L").point(lambda v: 0 if v > esik else 255).getbbox()
    return im.crop((max(0, b[0] - pay), max(0, b[1] - pay), min(im.width, b[2] + pay), min(im.height, b[3] + pay))) if b else im


def kirp_zemin(im, pay=30):
    """Perspektifte zemin ve gökyüzü dışında kalan (bina) kutusu."""
    a = np.asarray(im).astype(int)
    zemin = a[-5, 5]
    gok = a[5, -5] if abs(a[5, -5] - zemin).sum() > 30 else zemin
    fark = np.minimum(np.abs(a - zemin).sum(axis=2), np.abs(a - gok).sum(axis=2))
    ys, xs = np.where(fark > 45)
    return im.crop((max(0, xs.min() - pay), max(0, ys.min() - pay), min(im.width, xs.max() + pay), min(im.height, ys.max() + pay)))


def gorunus(im, sira):
    """Görünüşler görselinden biri (0 ön, 1 arka, 2 sol, 3 sağ). Satırlar, ortadaki en uzun boş bantın ortasından ayrılır (antetsiz
    görselde sabit oranlar alttaki satırın başlığını kesiyordu); sütunlar görselin ortasından."""
    w, h = im.size
    bos = ~(np.asarray(im.convert("L")) < 245).any(axis=1)
    en, bant, bas = (0, h // 2), 0, None
    for i in range(int(0.3 * h), int(0.7 * h) + 1):
        if i < int(0.7 * h) and bos[i]:
            bas = i if bas is None else bas
        elif bas is not None:
            if i - bas > bant:
                bant, en = i - bas, (bas, i)
            bas = None
    bol = (en[0] + en[1]) // 2 if bant else h // 2
    x0 = (sira % 2) * (w // 2)
    return kirp_beyaz(im.crop((x0, 0 if sira < 2 else bol, x0 + w // 2, bol if sira < 2 else h)))


def yerlestir(fig, im, kutu, baslik=None, bs=12):
    ax = fig.add_axes(kutu)
    ax.imshow(im)
    ax.set_axis_off()
    if baslik:
        ax.set_title(baslik, fontsize=bs, fontweight="bold", loc="left")


_p = ac(f"{KOD}_plan.png")
plan = kirp_beyaz(_p.crop((0, 0, int(0.66 * _p.width), int(PLAN_ALT * _p.height))))   # alttaki açıklama satırları dışarıda
g = ac(f"{KOD}_gorunusler.png")
on, sol = gorunus(g, 0), gorunus(g, 2)
ps = {ad: kirp_zemin(ac(f"{KOD}_perspektif_{ad}.png")) for ad in ("on_sol", "on_sag", "arka_sol", "arka_sag")}

# 1. sunum sayfası
f1 = plt.figure(figsize=A4Y, dpi=150)          # antet yok: başlık ve TASLAK satırı kaldırıldı, yer çizimlere verildi
yerlestir(f1, plan, [0.02, 0.04, 0.36, 0.91], "PLAN", 13)
yerlestir(f1, ps["on_sol"], [0.40, 0.53, 0.285, 0.42], "ön sol")
yerlestir(f1, ps["on_sag"], [0.695, 0.53, 0.285, 0.42], "ön sağ")
yerlestir(f1, on, [0.40, 0.11, 0.30, 0.35], "ön görünüş")
yerlestir(f1, sol, [0.72, 0.14, 0.26, 0.29], "sol görünüş")
f1.text(0.40, 0.075, "\n".join(textwrap.wrap(ALT_NOT, 118)), fontsize=10, va="top", linespacing=1.35)
s1 = T / f"{KOD}_sunum.png"
f1.savefig(s1, dpi=150)
plt.close(f1)

# 3. dört perspektif
f3 = plt.figure(figsize=A4Y, dpi=150)
for i, (ad, baslik) in enumerate((("on_sol", "ön sol"), ("on_sag", "ön sağ"), ("arka_sol", "arka sol"), ("arka_sag", "arka sağ"))):
    yerlestir(f3, ps[ad], [0.03 + (i % 2) * 0.49, 0.52 - (i // 2) * 0.48, 0.45, 0.43], baslik)
s3 = T / f"{KOD}_perspektifler.png"
f3.savefig(s3, dpi=150)
plt.close(f3)

with PdfPages(T / f"{KOD}_bayi.pdf") as pdf:
    for yol in (s1, C / f"{KOD}_pafta.png", s3):
        im = Image.open(yol).convert("RGB")
        w, h = im.size
        f = plt.figure(figsize=(16.54, 16.54 * h / w), dpi=150)
        a = f.add_axes([0, 0, 1, 1])
        a.imshow(im)
        a.set_axis_off()
        pdf.savefig(f, dpi=150)
        plt.close(f)

# mühendis paketi: yükleme listesi PDF'i (pandoc → HTML, Chromium ile yatay A4)
md = K / f"sonuc/{KOD}_yukleme.md"
ARA = K / "ara"
ARA.mkdir(exist_ok=True)
html = ARA / f"{KOD}_yukleme.html"   # ara dosya; silinmez
css = ("<style>body{font-family:'DejaVu Sans',sans-serif;font-size:8.5pt;margin:0}h1{font-size:13pt}table{border-collapse:collapse;width:100%}"
       "th,td{border:1px solid #999;padding:2px 4px;vertical-align:top}th{background:#eee}tr:nth-child(even) td{background:#fafafa}</style>")
govde = subprocess.run(["pandoc", str(md), "-f", "gfm", "-t", "html"], check=True, capture_output=True, text=True).stdout
html.write_text(f"<!doctype html><html lang='tr'><head><meta charset='utf-8'>{css}</head><body>{govde}</body></html>", encoding="utf-8")   # antet yok
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    s = b.new_page()
    s.goto(html.as_uri())
    s.pdf(path=str(T / f"{KOD}_yukleme.pdf"), format="A4", landscape=True, margin={"top": "10mm", "bottom": "10mm", "left": "8mm", "right": "8mm"})
    b.close()

with zipfile.ZipFile(T / f"{KOD}_muhendis.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for yol, ad in ((C / f"{KOD}.ifc", f"{KOD}.ifc"), (T / f"{KOD}_yukleme.pdf", f"{KOD}_yukleme_listesi.pdf"), (md, f"{KOD}_yukleme_listesi.md"),
                    (C / f"{KOD}_pafta.png", f"{KOD}_pafta.png"), (C / f"{KOD}_makasli.png", f"{KOD}_makasli.png"),
                    (C / f"{KOD}_catisiz.png", f"{KOD}_catisiz.png"), (C / f"{KOD}.dxf", f"{KOD}.dxf")):
        if yol.suffix == ".dxf" and not yol.is_file():               # DXF (dxf_genel.py) varsa pakete girer (Lokman, 12 Ekim 15:52)
            continue
        z.write(yol, ad)
print("yazıldı:", ", ".join(p.name for p in sorted(T.iterdir())))
