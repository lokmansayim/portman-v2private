#!/usr/bin/env python3
"""Çelik deneme: çatı hesabı, dört görünüş, çatı planı ve tek pafta.

Deneme kodudur; canlıda değildir. `ciz.py` ile aynı tanım dosyasını okur.

Çatı kuralları (Lokman, 2 Ekim 2026 20:40): kırma (dört omuz) çatı; eğim %33, yandan da önden de;
mahya ortada kalan kısımdır; saçak 30 cm, altı kaplamalı. Lento her zaman 70 cm.
Topuk 10 cm: makasın üst yüzü saçak ucunda duvar üst kotundan 10 cm yukarıdadır; saçak altı duvar üst kotundadır
(üç çelik SKP modelinden ölçüldü, `docs/sartname/skp_olcumleri.md`; Lokman 2 Ekim 22:05'te teyit etti).
Makasların üzerine 8 cm çatı paneli gelir; saçak yüzü (Lokman'ın deyişiyle "saçak genişliği"; kaplanır) = topuk + panelin eğimdeki düşey ölçüsü (Lokman, 22:05).
Not: kodda bu yüzün anahtarları `alin_*` diye geçer; PortatifEv listelerinde "alın" beşik çatının kalkan yüzüdür, o yüzden çıktılarda "saçak yüzü" denir.
Mahya malzemesi tepe mahyasına ve dört kırma hattına konur; aynı malzeme (Lokman, 3 Ekim 11:57).

3 Ekim 13:27 (Lokman):
- Makasların üzerine yine kendi malzemesinden çatı paneli konur; çatı kaplaması seçenektir. (Çıkarım: 22:05'teki 8 cm panel bu paneldir.)
- Mahya, saçak sacı ve alın sacında bindirme 30 cm kabul edilir (fire dahil): L 2800 parçada uzunluk ÷ 2,5.
- Dere inişi: her köşeye bir tane; 10 m ve daha uzun cephenin ortasına bir tane daha (cephe başına en çok bir orta iniş).
- Veranda çerçevesi: her projede sırt 80 mm, genişlik 30 cm; bu projede kirişler yanlarda ve karşıda, altlarında 240 cm dikmeler.
- İç kapı boşluğu 90 × 214 cm. (Çıkarım: lento 70 cm kuralı pencerelerde uygulanır.)

3 Ekim 2026 (inşaat mühendisi Ubeydullah'ın cevapları; Lokman 18:14'te iletti):
- Yöntem A'da saçak omegası gerekmez; saçak yüzü de Boardex'le kaplanır.
- Dere inişi plana bakarak yerleştirilir; düz bir saçakta ortalama 5 metrede bir yazılır. Tanımda `cati.inis_noktalari` verilirse o kullanılır, yoksa Lokman'ın kuralı.
- OSB takviyesi yalnız dolap ve TV ünitesi gelen duvarlara: planda turuncu çizgi.

Kullanım:
    python gorunus.py C8201.json
    python gorunus.py C8201.json --secenek secenekler/dis_karkas_140.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Polygon as MplPolygon, Rectangle

from ciz import BURADA, hesapla, olcu, osb_takviye_satiri, plan_eksen, secenek_uygula, tr, veranda_cercevesi

DUVAR = "#dcd7cb"
DUVAR_GERI = "#c9c4b8"
CATI = "#5d6470"
CAM = "#cfe6f7"
CERCEVE = "#2a78b8"
KAPI = "#b08a5a"
KOLON = "#8f8f8f"
KAPLAMA_ADI = {"sandvic_panel": "sandviç panel", "tek_kat_panel": "tek kat panel", "osb_kiremit": "OSB + nem bariyeri + kiremit desen sac (metal kiremit)",
               "osb_trapez": "OSB + nem bariyeri + trapez sac", "trapez_sac": "trapez sac", "osb_shingle": "OSB + membran + shingle"}
INIS_ORTA_ESIK_CM = 1000   # bu boydan kısa cepheye orta iniş konmaz (Lokman, 3 Ekim 13:27)


def inis_noktalari(L: float, H: float, s: float, esik: float = INIS_ORTA_ESIK_CM) -> list[tuple[float, float, str]]:
    """Kırma çatıda dere inişleri: saçak köşelerine birer tane; cephesi `esik` ve üzeri olan kenarın ortasına bir tane.
    Dönen: (x, y, 'kose' | 'orta'); başlangıç ayak izinin sol-alt köşesi."""
    n = [(-s, -s, "kose"), (L + s, -s, "kose"), (L + s, H + s, "kose"), (-s, H + s, "kose")]
    if L >= esik:
        n += [(L / 2, -s, "orta"), (L / 2, H + s, "orta")]
    if H >= esik:
        n += [(-s, H / 2, "orta"), (L + s, H / 2, "orta")]
    return n


def cati_hesapla(tanim: dict, inis_esik_cm: float = INIS_ORTA_ESIK_CM) -> dict:
    c = tanim["cati"]
    if c["tip"] != "kirma":
        raise SystemExit("Bu deneme yalnız kırma (dört omuz) çatıyı hesaplar.")
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    v = tanim.get("veranda")
    L = W + (v["en"] if v and "veranda" in c["kapsam"] else 0)   # çatının örttüğü ayak izi: L × H
    e, s = c["egim_yuzde"] / 100.0, c["sacak"]
    px, py = L + 2 * s, H + 2 * s                                 # saçak dahil plan
    kisa, uzun = min(px, py), max(px, py)
    h = tanim["duvar_yuksekligi"]
    kok = math.sqrt(1 + e * e)
    topuk, panel = c.get("topuk", 0), c.get("panel_kalinligi", 0)   # panel: makasların üzerine gelen çatı paneli, eğime dik kalınlık
    panel_dusey = panel * kok                                    # panelin düşey ölçüsü (ucu şakülünde kesilirse)
    z_makas_sacak = h + topuk                                    # makas üst yüzü, saçak ucunda; saçak altı h kotunda
    z_makas_mahya = z_makas_sacak + (kisa / 2) * e
    z_sacak = z_makas_sacak + panel_dusey                        # çatı üst yüzü, saçak ucunda
    z_mahya = z_makas_mahya + panel_dusey                        # çatı üst yüzü, mahyada
    alin = z_sacak - h                                           # saçak yüzü (saçak kaplaması) yüksekliği = topuk + panelin düşey ölçüsü
    cevre = 2 * (px + py)                                        # saçak ucu çevresi
    # Mahya malzemesi tepeye ve dört kırma hattına konur (Lokman, 3 Ekim 11:57). Kırma: saçak köşesinden mahya ucuna.
    kirma_plan = (kisa / 2) * math.sqrt(2)                       # plandaki boy (45°)
    kirma = math.hypot(kirma_plan, (kisa / 2) * e)               # eğimli gerçek boy
    mahya_hatti = (uzun - kisa) + 4 * kirma
    parca = c.get("mahya_parca_boyu")
    bindirme = c.get("mahya_bindirme", 0)
    plan_m2 = px * py / 1e4
    if c.get("inis_noktalari"):                                  # plana bakarak elle yerleştirilmiş inişler (Ubeydullah, 3 Ekim 2026)
        inis = [(float(x), float(y), "plan") for x, y in c["inis_noktalari"]]
    else:
        inis = inis_noktalari(L, H, s, inis_esik_cm)
    return {
        "ayak_izi": (L, H), "plan": (px, py), "mahya_uzunlugu": uzun - kisa, "mahya_yonu": "x" if px >= py else "y",
        "z_sacak": z_sacak, "z_mahya": z_mahya, "plan_m2": plan_m2, "yuzey_m2": plan_m2 * math.sqrt(1 + e * e),
        "sacak_alti_m2": (px * py - L * H) / 1e4, "veranda_tavani_m2": (v["en"] * v["boy"] / 1e4) if v else 0.0,
        "sacak": s, "egim": e, "z_sacak_alti": h,
        "z_makas_sacak": z_makas_sacak, "z_makas_mahya": z_makas_mahya, "panel_kalinligi": panel, "panel_dusey": panel_dusey,
        "alin_yuksekligi": alin, "alin_gonye_kesimde": topuk + panel / kok, "alin_cevre_m": cevre / 100, "alin_m2": cevre * alin / 1e4,
        "kirma_adedi": 4, "kirma_plan_boyu": kirma_plan, "kirma_boyu": kirma, "mahya_hatti_toplam": mahya_hatti,
        "mahya_parca_boyu": parca, "mahya_parca_adedi_bindirmesiz": math.ceil(mahya_hatti / parca - 1e-9) if parca else None,
        "mahya_bindirme": bindirme, "mahya_parca_adedi": math.ceil(mahya_hatti / (parca - bindirme) - 1e-9) if parca else None,
        "inis_noktalari": inis, "inis_adedi": len(inis), "inis_kaynagi": "plan" if c.get("inis_noktalari") else "kural", "cephe": (L, H),
        "oturum_m2": L * H / 1e4,
        "yontem": c.get("yontem"), "kaplama": c.get("kaplama"),
    }


def _cati_siluet(tanim: dict, c: dict, taraf: str):
    """Görünüşte çatı çokgeni (u, z). u, görünüşün yatay ekseni; 0, ayak izinin bakışa göre sol ucu."""
    L, H = c["ayak_izi"]
    s, yari = c["sacak"], min(c["plan"]) / 2
    uz = L if taraf in ("on", "arka") else H
    mahya_boyunca = (c["mahya_yonu"] == "x") == (taraf in ("on", "arka"))
    if mahya_boyunca:   # mahyaya dik bakış: yamuk
        return [(-s, c["z_sacak"]), (-s + yari, c["z_mahya"]), (uz + s - yari, c["z_mahya"]), (uz + s, c["z_sacak"])]
    return [(-s, c["z_sacak"]), (uz / 2, c["z_mahya"]), (uz + s, c["z_sacak"])]   # mahya boyunca bakış: üçgen


def gorunus_eksen(ax, tanim: dict, s: dict, c: dict, taraf: str):
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    L = c["ayak_izi"][0]
    h = tanim["duvar_yuksekligi"]
    v = tanim.get("veranda")
    vc = veranda_cercevesi(tanim)
    duvar_adi = {"on": "dis:alt", "arka": "dis:ust", "sol": "dis:sol", "sag": "dis:sag"}[taraf]
    uz = L if taraf in ("on", "arka") else H

    def u(deger: float, en: float = 0.0) -> float:
        """Plandaki konumu görünüşün yatay eksenine çevirir (bakışa göre soldan sağa)."""
        if taraf == "on":
            return deger
        if taraf == "arka":
            return L - deger - en
        if taraf == "sol":
            return H - deger - en
        return deger

    # duvar yüzü
    if taraf in ("on", "arka"):
        u0 = u(0, W)
        ax.add_patch(Rectangle((u0, 0), W, h, fc=DUVAR, ec="#555", lw=0.8, zorder=2))
        if v:   # veranda: açık; yandan bakışta köşe dikmesinin sırtı ve yan kiriş görünür
            vu = u(v["x"], v["en"])
            if vc:
                sr, g, db = vc["sirt"], vc["genislik"], vc["dikme_boyu"]
                ku = vu + v["en"] - sr if taraf == "on" else vu
                ax.add_patch(Rectangle((ku, 0), sr, db, fc=KOLON, ec="#555", lw=0.8, zorder=3))
                ax.add_patch(Rectangle((vu, db), v["en"], g, fc=KOLON, ec="#555", lw=0.8, zorder=3))   # yan kiriş
            ax.plot([vu, vu + v["en"]], [h, h], color="#555", lw=0.8, zorder=2)   # veranda tavanı
    elif taraf == "sol":
        ax.add_patch(Rectangle((0, 0), H, h, fc=DUVAR, ec="#555", lw=0.8, zorder=2))
    else:   # sağ: önde veranda kolonları, geride duvar
        ax.add_patch(Rectangle((0, 0), H, h, fc=DUVAR_GERI, ec="#555", lw=0.8, zorder=2))
    # açıklıklar
    for a in s["aciklik_kotlari"]:
        if a["duvar"] != duvar_adi:
            continue
        x0 = u(a["bas"], a["en"])
        if a["tur"] == "pencere":
            ax.add_patch(Rectangle((x0, a["alt"]), a["en"], a["ust"] - a["alt"], fc=CAM, ec=CERCEVE, lw=1.0, zorder=4))
            if a["en"] >= 100:
                ax.plot([x0 + a["en"] / 2] * 2, [a["alt"], a["ust"]], color=CERCEVE, lw=0.7, zorder=5)
        else:
            ax.add_patch(Rectangle((x0, 0), a["en"], a["ust"], fc=KAPI, ec="#5c4326", lw=1.0, zorder=4))
    if taraf == "sag" and vc:   # karşıdan bakış: dikmelerin geniş yüzü ve ön kiriş
        g, db = vc["genislik"], vc["dikme_boyu"]
        for dk in vc["dikmeler"]:
            ax.add_patch(Rectangle((dk.bounds[1], 0), g, db, fc=KOLON, ec="#555", lw=0.8, zorder=6))
        ax.add_patch(Rectangle((0, db), H, g, fc=KOLON, ec="#555", lw=0.8, zorder=6))
    # çatı
    sil = _cati_siluet(tanim, c, taraf)
    ax.add_patch(MplPolygon(sil, closed=True, fc=CATI, ec="#2f343c", lw=1.0, zorder=7))
    # saçak yüzü: saçak ucunda duvar üst kotu ile çatı üst yüzü arası (topuk + panelin düşey ölçüsü); kaplanır
    ax.add_patch(Rectangle((-c["sacak"], h), uz + 2 * c["sacak"], c["z_sacak"] - h, fc="#454b55", ec="#2f343c", lw=0.8, zorder=8))
    # zemin ve kotlar
    ax.plot([-70, uz + 70], [0, 0], color="#333", lw=1.2, zorder=1)
    olcu(ax, (uz + 52, 0), (uz + 52, h), str(h), 4, yatay=False)
    olcu(ax, (uz + 88, 0), (uz + 88, c["z_mahya"]), tr(c["z_mahya"], 0), 4, yatay=False)
    olcu(ax, (0, -34), (uz, -34), tr(uz).replace(",0", ""), -3)
    ad = {"on": "ÖN (GİRİŞ) GÖRÜNÜŞ", "arka": "ARKA GÖRÜNÜŞ", "sol": "SOL GÖRÜNÜŞ", "sag": "SAĞ (VERANDA) GÖRÜNÜŞ"}[taraf]
    ax.set_title(ad, fontsize=9.5, weight="bold")
    ax.set_xlim(-90, uz + 130)
    ax.set_ylim(-75, c["z_mahya"] + 25)
    ax.set_aspect("equal")
    ax.axis("off")


def cati_plani_eksen(ax, tanim: dict, c: dict):
    L, H = c["ayak_izi"]
    W = tanim["kapali"]["en"]
    s = c["sacak"]
    px, py = c["plan"]
    yari = min(px, py) / 2
    kose = [(-s, -s), (L + s, -s), (L + s, H + s), (-s, H + s)]
    ax.add_patch(MplPolygon(kose, closed=True, fc="#8a919c", ec="#2f343c", lw=1.2, zorder=1))
    if c["mahya_yonu"] == "x":
        m1, m2 = (-s + yari, H / 2), (L + s - yari, H / 2)
    else:
        m1, m2 = (L / 2, -s + yari), (L / 2, H + s - yari)
    ax.plot([m1[0], m2[0]], [m1[1], m2[1]], color="#1c1f24", lw=2.0, zorder=3)
    for kx, ky in kose:
        hedef = m1 if (kx < L / 2 if c["mahya_yonu"] == "x" else ky < H / 2) else m2
        ax.plot([kx, hedef[0]], [ky, hedef[1]], color="#1c1f24", lw=2.0, zorder=3)   # kırma: mahya ile aynı malzeme
        aci = math.degrees(math.atan2(hedef[1] - ky, hedef[0] - kx))
        if aci > 90 or aci < -90:
            aci += 180
        ox, oy = (kx + hedef[0]) / 2, (ky + hedef[1]) / 2
        nx, ny = -math.sin(math.radians(aci)), math.cos(math.radians(aci))
        ax.text(ox + nx * 15, oy + ny * 15, f"mahya {tr(c['kirma_boyu'], 0)}", ha="center", va="center", fontsize=7.5, color="white",
                rotation=aci, rotation_mode="anchor", zorder=4)
    ax.add_patch(Rectangle((0, 0), L, H, fill=False, ec="white", lw=0.9, ls=(0, (5, 3)), zorder=2))   # duvar dış yüzü
    ax.plot([W, W], [0, H], color="white", lw=0.8, ls=(0, (2, 3)), zorder=2)
    ax.text((m1[0] + m2[0]) / 2, m1[1] + 16, f"mahya {tr(c['mahya_uzunlugu']).replace(',0', '')}", ha="center", fontsize=8, color="white", zorder=4)
    yuzde = f"%{round(c['egim'] * 100)}"
    for (tx, ty), (dx, dy) in (((L / 2, H * 0.14), (0, -1)), ((L / 2, H * 0.86), (0, 1)), ((L * 0.07, H / 2), (-1, 0)), ((L * 0.93, H / 2), (1, 0))):
        ax.annotate("", xy=(tx + dx * 46, ty + dy * 46), xytext=(tx, ty), arrowprops=dict(arrowstyle="->", color="white", lw=1.0), zorder=4)
        ax.text(tx - dx * 20 + (0 if dx else 34), ty - dy * 20, yuzde, ha="center", va="center", fontsize=7.5, color="white", zorder=4)
    for ix, iy, _tur in c["inis_noktalari"]:   # dere inişleri
        ax.plot([ix], [iy], marker="o", ms=7, mfc="#f2c744", mec="#1c1f24", mew=1.0, zorder=6)
    olcu(ax, (-s, -s - 34), (L + s, -s - 34), tr(px).replace(",0", ""), -3)
    olcu(ax, (-s - 34, -s), (-s - 34, H + s), tr(py).replace(",0", ""), -4, yatay=False)
    ax.set_title(f"ÇATI PLANI · sarı nokta: dere inişi ({c['inis_adedi']} adet)", fontsize=9.5, weight="bold")
    ax.set_xlim(-s - 90, L + s + 40)
    ax.set_ylim(-s - 80, H + s + 30)
    ax.set_aspect("equal")
    ax.axis("off")


def pafta(tanim: dict, s: dict, c: dict, cikti: Path):
    fig = plt.figure(figsize=(18.5, 13.2), dpi=140)
    gs = GridSpec(3, 4, figure=fig, height_ratios=[1.9, 1.0, 0.48], hspace=0.10, wspace=0.06)
    plan_eksen(fig.add_subplot(gs[0, 0:2]), tanim, s, baslik=False, bilgi=False)
    fig.axes[0].set_title("PLAN", fontsize=9.5, weight="bold")
    cati_plani_eksen(fig.add_subplot(gs[0, 2:4]), tanim, c)
    for i, taraf in enumerate(("on", "arka", "sol", "sag")):
        gorunus_eksen(fig.add_subplot(gs[1, i]), tanim, s, c, taraf)
    ax = fig.add_subplot(gs[2, :])
    ax.axis("off")
    b = s["boardex"]
    ct = tanim["cati"]
    vc = veranda_cercevesi(tanim)
    kapilar = {a["tur"]: a for a in tanim["acikliklar"] if a["tur"] != "pencere"}
    ik, dk = kapilar.get("ic_kapi", {}), kapilar.get("dis_kapi", {})
    kap = KAPLAMA_ADI.get(ct.get("kaplama"), "—")
    sol = [
        f"Dış ölçü (veranda dahil): {tr(c['ayak_izi'][0]).replace(',0', '')} × {c['ayak_izi'][1]} cm = {tr(s['toplam_oturum_m2'])} m²",
        f"Kapalı kısım: {tanim['kapali']['en']} × {tanim['kapali']['boy']} cm · brüt {tr(s['kapali_brut_m2'], 2)} m² · net {tr(s['kapali_net_m2'])} m²",
        f"Duvar: dış {tr(s['td'])} cm ({tanim['dis_duvar_tipi']}) · iç {tr(s['ti'])} cm ({tanim['ic_duvar_tipi']}) · yükseklik {tanim['duvar_yuksekligi']} cm",
        f"Pencereler: lento {tanim['lento']} cm, üst kot {s['aciklik_ust_kotu']} cm · iç kapı boşluğu {ik.get('en', '—')} × {ik.get('yuk', '—')} "
        f"(kanat {' × '.join(str(x) for x in ik.get('kanat', []))}) · dış kapı {dk.get('en', '—')}/{dk.get('yuk', '—')}",
        f"Dış Boardex: {tr(b['cevre_m'])} m × {tr(b['yukseklik_m'], 2)} m − {tr(b['bosluk_m2'])} m² = {tr(b['net_m2'])} m² (fire hariç {b['levha_adedi_firesiz']} levha)",
    ]
    if s.get("osb_takviye"):
        sol.append(osb_takviye_satiri(s["osb_takviye"], kisa=True))
    sag = [
        f"Çatı: kırma (dört omuz) · eğim %{ct['egim_yuzde']} · saçak {ct['sacak']} cm, altı ve yüzü Boardex · çatı ve tavan panelli (çelik) · kaplama: {kap}",
        f"Çatı planı {tr(c['plan'][0]).replace(',0', '')} × {tr(c['plan'][1]).replace(',0', '')} cm · mahya kotu {tr(c['z_mahya'], 0)} cm (makas üstü {tr(c['z_makas_mahya'], 0)})",
        f"Mahya (tepe ve kırmalar, aynı malzeme): {tr(c['mahya_uzunlugu']).replace(',0', '')} + {c['kirma_adedi']} × {tr(c['kirma_boyu'], 0)} = {tr(c['mahya_hatti_toplam'], 0)} cm"
        + (f" · {tr(c['mahya_parca_boyu'] / 100)} m'lik parça, {c['mahya_bindirme']} cm bindirmeyle {c['mahya_parca_adedi']} adet" if c["mahya_parca_boyu"] else ""),
        f"Çatı yüzeyi {tr(c['yuzey_m2'])} m² (plan {tr(c['plan_m2'])} m²) · saçak altı {tr(c['sacak_alti_m2'])} m² · veranda tavanı {tr(c['veranda_tavani_m2'])} m²",
        f"Saçak yüzü {tr(c['alin_yuksekligi'])} cm = topuk {ct.get('topuk', 0)} + {ct.get('panel_kalinligi', 0)} cm çatı panelinin eğimdeki düşey ölçüsü {tr(c['panel_dusey'])} · kaplaması {tr(c['alin_cevre_m'])} m × {tr(c['alin_yuksekligi'])} cm = {tr(c['alin_m2'])} m²",
        (f"Veranda çerçevesi: sırt {vc['sirt']}, genişlik {vc['genislik']} cm · kiriş {tr(vc['kiris_boyu'] / 100, 2)} m (yanlar ve karşı) · dikme {vc['dikme_adedi']} × {vc['dikme_boyu']} cm "
         f"(yerleri katalog görsellerinden)" if vc else "Veranda yok"),
        f"Dere inişi {c['inis_adedi']} adet (" + ("plana yerleştirildi" if c["inis_kaynagi"] == "plan" else "köşeler; 10 m ve daha uzun cephelerin ortası")
        + ") · subasman, merdiven ve cephe kaplaması çizilmedi · ölçüler cm",
    ]
    ax.text(0.0, 0.95, "\n".join(sol), ha="left", va="top", fontsize=9.2, linespacing=1.55, transform=ax.transAxes)
    ax.text(0.52, 0.95, "\n".join(sag), ha="left", va="top", fontsize=9.2, linespacing=1.55, transform=ax.transAxes)
    fig.suptitle(f"{tanim['kod']} · {tanim['ad']} · paket: {tanim['paket']}   —   TASLAK · çizim kurallarından kuruldu · üretim projesi değildir",
                 fontsize=12.5, weight="bold", x=0.02, ha="left", y=0.965)
    fig.savefig(cikti, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--secenek", type=Path, action="append", default=[], help="seçenek dosyası (yinelenebilir)")
    ap.add_argument("--cikti", type=Path, default=BURADA / "cikti")
    a = ap.parse_args()
    tanim = json.loads(a.tanim.read_text(encoding="utf-8"))
    tanim, sek = secenek_uygula(tanim, a.secenek)
    tipler = json.loads((BURADA / "duvar_tipleri.json").read_text(encoding="utf-8"))
    s = hesapla(tanim, tipler, False)
    c = cati_hesapla(tanim)
    a.cikti.mkdir(parents=True, exist_ok=True)
    kod = tanim["kod"].replace("Ç", "C") + sek
    pafta(tanim, s, c, a.cikti / f"{kod}_pafta.png")
    rapor = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()}
    (a.cikti / f"{kod}_cati.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{tanim['kod']} çatı: plan {c['plan'][0]} × {c['plan'][1]} cm · mahya {c['mahya_uzunlugu']} cm ({c['mahya_yonu']} yönünde) · "
          f"saçak ucu {tr(c['z_sacak'])} (makas üstü {tr(c['z_makas_sacak'])}) · mahya kotu {tr(c['z_mahya'])} (makas üstü {tr(c['z_makas_mahya'])}) cm")
    print(f"  mahya hattı: tepe {tr(c['mahya_uzunlugu'], 1)} + {c['kirma_adedi']} kırma × {tr(c['kirma_boyu'], 2)} (planda {tr(c['kirma_plan_boyu'], 2)}) = {tr(c['mahya_hatti_toplam'], 1)} cm"
          + (f" · {c['mahya_parca_boyu']} cm'lik parça, {c['mahya_bindirme']} cm bindirmeyle {c['mahya_parca_adedi']} adet (bindirmesiz {c['mahya_parca_adedi_bindirmesiz']})" if c["mahya_parca_boyu"] else ""))
    print(f"  saçak yüzü {tr(c['alin_yuksekligi'], 2)} cm (panel ucu gönyesinde kesilirse {tr(c['alin_gonye_kesimde'], 2)}) · kaplaması {tr(c['alin_cevre_m'], 2)} m × {tr(c['alin_yuksekligi'], 2)} cm = {tr(c['alin_m2'], 2)} m²")
    print(f"  yüzey {tr(c['yuzey_m2'], 2)} m² (plan {tr(c['plan_m2'], 2)}) · saçak altı {tr(c['sacak_alti_m2'], 2)} m² · veranda tavanı {tr(c['veranda_tavani_m2'], 2)} m²")
    print(f"  dere inişi {c['inis_adedi']} adet: " + ", ".join(f"({x:.0f}, {y:.0f}) {t}" for x, y, t in c["inis_noktalari"]))
    print("  açıklık kotları:", sorted({(k["tur"], k["en"], k["alt"], k["ust"]) for k in s["aciklik_kotlari"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
