#!/usr/bin/env python3
"""Makas yerleşim planı (İE-16 PR-3b): karkas kuralının çatısı pafta olarak.

Yalnız tanım karkas kuralını isterse çizilir (`"karkas": "kural"`; `uret` çağırır); istemeyen tanımın çizim seti değişmez. Planın
üstünde çatı düzlemleri soluk, mahya, kırma ve vadi çizgileri; her makas adıyla (M01…; tam makas kalın, kısa makas ince, kırma çaprazı
kesik çizgi), çatı paneli olan düzlemler taralı ve saçak boyunca panellerine bölünmüş (Ç01…), bacalar (B01…). Yanında tablo: makasın
türü, ailesi, açıklığı, en büyük yüksekliği ve profil boyu; çatı panelleri, bacalar ve (yöntem A) çatı üstü ve tavan panellerinin özeti.
Dizilim ve adlar `karkas.kur`'dan (`makas.py`) gelir; bu modül hesap yapmaz, yalnız çizer (çatı panelinin plandaki bölmesi, açılımdaki
eşit bölmenin plandaki karşılığıdır).

    python -m motor.genel.makas_pafta tanim.json <çıktı klasörü>
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
from shapely.geometry import box  # noqa: E402

from . import cati_genel, ciz_genel, girdi_genel, karkas, kural, makas, yapi  # noqa: E402

TUR_ADI = {"makas": "tam", "kisa": "kısa", "capraz": "kırma çaprazı"}
TUR_CIZGI = {"makas": dict(color="#14365e", lw=2.0, ls="-"), "kisa": dict(color="#2f7bbf", lw=1.2, ls="-"),
             "capraz": dict(color="#a33a00", lw=1.4, ls="--")}
KENAR_CIZGI = {"mahya": dict(color="#555", lw=0.9, ls="-"), "kirma": dict(color="#777", lw=0.7, ls="-"), "vadi": dict(color="#777", lw=0.7, ls=":")}
CATI_PANELI_RENGI = ("#f3dcc4", "#e8c29c")
BACA_RENGI = "#bdbdbd"


def dosya_adlari(kod: str) -> tuple[str, str]:
    return f"{kod}_makaslar.png", f"{kod}_makaslar.pdf"


def adlar(ck: dict) -> list[dict]:
    """Makaslar kuralın sırasıyla M01…; çizgi uçları planda."""
    out = []
    for j, x in enumerate(ck["makaslar"], 1):
        if x["tur"] == "capraz":
            p, q = x["s"]
        elif x["eksen"] == "x":
            p, q = (x["s"][0], x["konum"]), (x["s"][1], x["konum"])
        else:
            p, q = (x["konum"], x["s"][0]), (x["konum"], x["s"][1])
        out.append({**x, "ad": f"M{j:02d}", "p": tuple(p), "q": tuple(q)})
    return out


def cati_paneli_planlari(c: dict) -> list[dict]:
    """Çatı panelli düzlemin planı saçak boyunca `cati_paneli_adedi` eşit şeride (açılımdaki eşit bölmenin plandaki karşılığı)."""
    out, j = [], 0
    for dz in c["duzlemler"]:
        if dz.get("ust_yapi") != "cati_paneli":
            continue
        n = int(dz.get("cati_paneli_adedi", 1))
        x0, y0, x1, y1 = dz["cokgen"].bounds
        sacak_x = makas._eksen(dz) == "y"                  # eğim y yönündeyse saçak x boyunca
        for i in range(n):
            serit = (box(x0 + (x1 - x0) * i / n, y0 - 1, x0 + (x1 - x0) * (i + 1) / n, y1 + 1) if sacak_x else
                     box(x0 - 1, y0 + (y1 - y0) * i / n, x1 + 1, y0 + (y1 - y0) * (i + 1) / n))
            p = dz["cokgen"].intersection(serit)
            for g in ciz_genel._cokgenler(p):
                j += 1
                out.append({"ad": f"Ç{j:02d}", "duzlem": dz["ad"], "cokgen": g})
    return out


def plan(ax, y: dict, c: dict, ms: list[dict], cps: list[dict], kk: dict) -> None:
    for b in y["bolgeler"].values():                          # mahaller soluk
        if b["sinif"] == "dis":
            continue
        for p in ciz_genel._cokgenler(b["net"]):
            ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc="#f6f6f2" if b["sinif"] != "veranda" else "#eef4e8", ec="none", zorder=1))
    for d in y["duvarlar"]:                                   # duvarlar gri
        x0, y0, x1, y1 = d["kutu"]
        ax.add_patch(MplPolygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, fc="#d6d6d6", ec="none", zorder=2))
    for dz in c["duzlemler"]:                                 # çatı düzlemleri: çizgi ve ad
        for p in ciz_genel._cokgenler(dz["cokgen"]):
            ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, fc="none", ec="#999", lw=0.5, zorder=3))
    for i, x in enumerate(cps):
        ax.add_patch(MplPolygon(list(x["cokgen"].exterior.coords), closed=True, fc=CATI_PANELI_RENGI[i % 2], ec="#8a5a2a", lw=0.6,
                                hatch="///", zorder=3.5))
        r = x["cokgen"].representative_point()
        ax.text(r.x, r.y, x["ad"], ha="center", va="center", fontsize=6.4, color="#6a3a00", weight="bold", zorder=9,
                bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.85))
    for e in c["kenarlar"]:
        if e["tur"] in KENAR_CIZGI and e.get("p") and e.get("q"):
            ax.plot([e["p"][0], e["q"][0]], [e["p"][1], e["q"][1]], zorder=4, **KENAR_CIZGI[e["tur"]])
    for j, b in enumerate(kk["bacalar"], 1):
        x0, y0, x1, y1 = y["adli"][b["ad"]]["kutu"]
        ax.add_patch(MplPolygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, fc=BACA_RENGI, ec="#333", lw=0.8, zorder=6))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"B{j:02d}", ha="center", va="center", fontsize=6.0, weight="bold", zorder=9)
    konan: list[tuple[float, float]] = []
    for x in ms:
        (px, py), (qx, qy) = x["p"], x["q"]
        ax.plot([px, qx], [py, qy], zorder=5, solid_capstyle="butt", **TUR_CIZGI[x["tur"]])
        aralik = 0.0                                          # ad: çizginin bir ucunda; yazılar binmesin diye çizgi boyunca kaydırılır
        while True:
            t_ = 0.12 + aralik
            yer = (px + (qx - px) * t_, py + (qy - py) * t_)
            if all(abs(yer[0] - a) > 26 or abs(yer[1] - b) > 16 for a, b in konan) or aralik > 0.7:
                break
            aralik += 0.12
        konan.append(yer)
        ax.text(*yer, x["ad"], ha="center", va="center", fontsize=5.8, color=TUR_CIZGI[x["tur"]]["color"], zorder=9,
                rotation=90 if abs(qx - px) < abs(qy - py) else 0, bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.9))
    hat = [h for h in ciz_genel.dis_hat(y)]
    xs = [q[0] for h in hat for q in h] + [v for dz in c["duzlemler"] for v in (dz["cokgen"].bounds[0], dz["cokgen"].bounds[2])]
    ys = [q[1] for h in hat for q in h] + [v for dz in c["duzlemler"] for v in (dz["cokgen"].bounds[1], dz["cokgen"].bounds[3])]
    ax.set_xlim(min(xs) - 60, max(xs) + 60)
    ax.set_ylim(min(ys) - 60, max(ys) + 60)
    ax.set_aspect("equal")
    ax.axis("off")


def tablo(ax, ms: list[dict], cps: list[dict], ck: dict, kk: dict, profil: str) -> None:
    ax.axis("off")
    tr = ciz_genel.tr
    sat = [f"{'Ad':4s} {'Tür':14s} {'Aile':24s} {'Açıklık':>8s} {'h':>6s} {'Profil boyu':>11s}"]
    for x in ms:
        sat.append(f"{x['ad']:4s} {TUR_ADI[x['tur']]:14s} {x['aile'][:24]:24s} {ciz_genel.sade(x['acik_cm']):>8s} {ciz_genel.sade(x['h_en_cok_cm']):>6s} "
                   f"{tr(x['profil_boyu_m'], 2) + ' m':>11s}")
    sat += ["", f"Makas {len(ms)} · profil {profil.replace('x', ' × ')} · toplam {tr(sum(x['profil_boyu_m'] for x in ms), 1)} m"]
    if ck["cati_panelleri"]:
        sat += ["", f"{'Ad':4s} {'Düzlem':14s} {'Profil':14s} {'Ölçü (açılım)':>15s} {'Profil boyu':>11s}"]
        for x, r in zip(cps, ck["cati_panelleri"]):
            sat.append(f"{x['ad']:4s} {r['duzlem'][:14]:14s} {r['profil'].replace('x', ' × '):14s} "
                       f"{ciz_genel.sade(r['olcu_cm'][0]) + ' × ' + ciz_genel.sade(r['olcu_cm'][1]):>15s} {tr(r['profil_boyu_m'], 2) + ' m':>11s}")
    if kk["bacalar"]:
        sat.append("")
        for j, b in enumerate(kk["bacalar"], 1):
            sat.append(f"B{j:02d}  baca, {len(b['paneller'])} panel {(b['profil'] or '').replace('x', ' × '):14s} {tr(b['profil_boyu_m'], 2) + ' m':>11s}")
    for anahtar, ad in (("ust_panelleri", "Çatı üstü paneli (yöntem A)"), ("tavan_panelleri", "Tavan paneli (yöntem A)")):
        if ck.get(anahtar):
            sat += ["", f"{ad}: {len(ck[anahtar])} panel, toplam {tr(sum(x['profil_boyu_m'] for x in ck[anahtar]), 1)} m"]
    ax.text(0.0, 1.0, "\n".join(sat), ha="left", va="top", fontsize=5.9 if len(sat) > 60 else 6.5, family="DejaVu Sans Mono", linespacing=1.3,
            transform=ax.transAxes)


def ciz(t: dict, hedef: Path, kod: str, kural_k: dict | None = None, yontem: str | None = None) -> dict:
    """PNG ve tek sayfa PDF yazar; kaydı döner (yollar, makas sayıları, kuralın sha'sı). `yontem`: çatı yöntemi (`uret --yontem`);
    verilmezse tanımdaki ya da kuraldaki (`girdi_genel.cati_yontemi`)."""
    if t.get("karkas") != "kural":
        raise SystemExit("Makas yerleşim planı yalnız karkas kuralını isteyen tanımda çizilir (`karkas: kural`).")
    if not t.get("cati"):
        raise SystemExit("Makas yerleşim planı: tanımda çatı yok.")
    k = kural_k or karkas.oku()
    y = yapi.kur(t)
    kur = kural.oku()
    yontem = yontem or girdi_genel.cati_yontemi(t["cati"], kur)
    kk = karkas.kur(y, t, k, yontem)
    ck = kk["cati"]
    c = cati_genel.cati_kur(t["cati"])
    ms = adlar(ck)
    cps = cati_paneli_planlari(c)
    if len(cps) != len(ck["cati_panelleri"]):
        raise SystemExit(f"Makas yerleşim planı: çatı panelinin plandaki bölmesi ({len(cps)}) kuralınkiyle ({len(ck['cati_panelleri'])}) aynı değil")
    profil = f"80x45x{kur['celik']['et_kalinligi_varsayilan']['deger']['cati']}"     # makasın profili tanımda yazmaz (`girdi_genel`)
    fig = plt.figure(figsize=(16.5, 11.7), dpi=140)                    # A3 yatay
    gs = GridSpec(1, 2, figure=fig, width_ratios=[2.2, 1.0], wspace=0.02)
    plan(fig.add_subplot(gs[0, 0]), y, c, ms, cps, kk)
    tablo(fig.add_subplot(gs[0, 1]), ms, cps, ck, kk, profil)
    say = {tur: sum(1 for x in ms if x["tur"] == tur) for tur in TUR_ADI}
    ozet = " · ".join(f"{TUR_ADI[tur]} {n}" for tur, n in say.items() if n)
    fig.suptitle(f"{t['kod']} · MAKAS YERLEŞİM PLANI   —   TASLAK · makas dizilimi karkas kuralından · üretim projesi değildir",
                 fontsize=12, weight="bold", x=0.02, ha="left", y=0.975)
    fig.text(0.02, 0.945, f"Makas {len(ms)} ({ozet}); çatı paneli {len(cps)}; baca {len(kk['bacalar'])}. Ölçüler cm; makasın konumu ortası. "
             f"Kural: {kk['kural']['yol']} (sha {kk['kural']['sha256'][:12]}).", fontsize=8.4, ha="left")
    png_ad, pdf_ad = dosya_adlari(kod)
    hedef = Path(hedef)
    fig.savefig(hedef / png_ad, facecolor="white")
    with PdfPages(hedef / pdf_ad, metadata={"Title": f"{t['kod']} makaslar", "Creator": "Portman", "Producer": "Portman",
                                           "CreationDate": None, "ModDate": None}) as pp:
        pp.savefig(fig, facecolor="white")
    plt.close(fig)
    return {"png": png_ad, "pdf": pdf_ad, "makas": say, "cati_paneli": len(cps), "baca": len(kk["bacalar"]), "kural": kk["kural"]}


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
