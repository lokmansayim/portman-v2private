#!/usr/bin/env python3
"""Çatı açılımı diziliminin geometrik sağlaması (`cati_acilim.dizilim`).

Çokgenlerle (shapely) şunlara bakar:
  1. Her yüzün şerit parçaları yüzü tam örtüyor ve üst üste binmiyor mu?
  2. Her paneldeki parçalar panelin (kapatma × boy) içinde mi; birbirinin üstüne biniyor mu?
  3. Her parça, atandığı yüz parçasıyla eş mi? Alt parça yalnız ötelenir; üst parça 180° çevrilir (ters yüz edilmez).
  4. Eşleme kuralı: iki parça veren kesimde parçalar karşılıklı yüzlerde ve aynı türden mi?
  5. Adet, alan olarak en az gereken panelden az olamaz.

Ç8201'in dört kaplaması, 62 m² gerçek liste örneği ve rastgele kırma çatılar denenir. Sorun varsa çıkış kodu 1.

Kullanım:
    python cati_acilim_saglama.py
"""
from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from cati_acilim import BASLANGIC, dizilim

BURADA = Path(__file__).resolve().parent
TOL = 1e-6


def panel_sekilleri(d: dict):
    """Kesim planındaki yerleşim (cati_acilim.kesim_ciz ile aynı): (panel no, parça, çokgen [panel koordinatı; m], alt mı üst mü)."""
    w = d["kapatma_m"]
    for pn in d["paneller"]:
        taban = 0.0
        for dk in pn["dikdortgenler"]:
            l, ps = dk["boy"], dk["parcalar"]
            if len(ps) == 1 and ps[0].konum == "tam":
                p = ps[0]
                yield pn["no"], p, Polygon([(x - p.x0, t + taban) for x, t in p.kose]), "alt"
            else:
                alt = ps[0]
                a, b, en = alt.uzun, alt.kisa, alt.en
                kose = [(w - en, 0), (w, 0), (w, a), (w - en, b)] if alt.tip == "L" else [(0, 0), (en, 0), (en, b), (0, a)]
                yield pn["no"], alt, Polygon([(x, y + taban) for x, y in kose]), "alt"
                if len(ps) == 2:
                    ust = ps[1]
                    a, b, en = ust.uzun, ust.kisa, ust.en
                    kose = [(0, l), (en, l), (en, l - b), (0, l - a)] if ust.tip == "L" else [(w, l), (w - en, l), (w - en, l - b), (w, l - a)]
                    yield pn["no"], ust, Polygon([(x, y + taban) for x, y in kose]), "ust"
            taban += l


def es_mi(s1: Polygon, s2: Polygon) -> bool:
    """İki çokgen öteleme ile aynı mı (alt-sol köşeler hizalanarak)."""
    a = translate(s1, -s1.bounds[0], -s1.bounds[1])
    b = translate(s2, -s2.bounds[0], -s2.bounds[1])
    return a.symmetric_difference(b).area < TOL


def sagla(px: float, py: float, egim: float, w: float, boy: float, paylas: bool = True, baslangic: str = "sol") -> tuple[int, list[str]]:
    d = dizilim(px, py, egim, w, boy, paylas, baslangic)
    hata: list[str] = []
    y0, H = min(px, py) / 2, d["egimli_boy_m"]
    for ad, ps in d["yuzler"].items():                       # 1) yüz parçaları yüzü tam örtüyor
        E = max(px, py) if ad in ("ön", "arka") else min(px, py)
        yuz = Polygon([(0, 0), (E, 0), (E - y0, H), (y0, H)]) if E - 2 * y0 > 1e-9 else Polygon([(0, 0), (E, 0), (y0, H)])
        parcalar = [Polygon(p.kose) for p in ps]
        parcalar = [s for s in parcalar if s.area > 1e-12]
        if abs(sum(s.area for s in parcalar) - yuz.area) > TOL or abs(unary_union(parcalar).area - yuz.area) > TOL:
            hata.append(f"{ad}: parçalar yüzü tam örtmüyor")
    panel = box(0, 0, w, boy)
    gorulen: set[int] = set()
    icerik: dict[int, list] = defaultdict(list)
    for no, p, s, konum in panel_sekilleri(d):               # 2) ve 3)
        gorulen.add(id(p))
        if not panel.buffer(1e-7).contains(s):
            hata.append(f"panel {no}: {p.yuz} {p.serit} panelin dışına taşıyor")
        if not es_mi(rotate(s, 180, origin=(0, 0)) if konum == "ust" else s, Polygon(p.kose)):
            hata.append(f"panel {no}: {p.yuz} {p.serit} yüzdeki yeriyle eş değil")
        if (konum == "ust") != (p.konum == "üst"):
            hata.append(f"panel {no}: {p.yuz} {p.serit} konumu uyuşmuyor")
        icerik[no].append((p, s))
    for no, liste in icerik.items():
        for i in range(len(liste)):
            for j in range(i + 1, len(liste)):
                if liste[i][1].buffer(-1e-6).intersection(liste[j][1].buffer(-1e-6)).area > TOL:
                    hata.append(f"panel {no}: {liste[i][0].yuz} {liste[i][0].serit} ile {liste[j][0].yuz} {liste[j][0].serit} üst üste")
        if sum(s.area for _, s in liste) > w * boy + TOL:
            hata.append(f"panel {no}: alan aşıldı")
    if {id(p) for ps in d["yuzler"].values() for p in ps} != gorulen:
        hata.append("bazı parçalar hiçbir panelden çıkmıyor")
    for pn in d["paneller"]:                                  # 4) eşleme kuralı
        for dk in pn["dikdortgenler"]:
            if len(dk["parcalar"]) == 2:
                a, u = dk["parcalar"]
                if {a.yuz, u.yuz} not in ({"ön", "arka"}, {"sol", "sağ"}) or a.tip != u.tip or not paylas:
                    hata.append(f"panel {pn['no']}: eşleme kuralı bozuk")
    if d["adet"] < d["alan_alt_siniri"]:                      # 5)
        hata.append("adet, alan olarak en az gerekenden az")
    return d["adet"], hata


def main() -> int:
    kr = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))
    c = json.loads((BURADA / "sonuc" / "C8201_girdi.json").read_text(encoding="utf-8"))["cati"]
    g62 = json.loads((BURADA / "ornek_62m2_girdi.json").read_text(encoding="utf-8"))["cati"]
    yok = kr["kirma_cati_dizilim"]["deger"]["artan_parca_kullanilmayan_kaplamalar"]
    denemeler = [(f"Ç8201 {ad}", (c["plan_m"][0], c["plan_m"][1], c["egim"], kr[kural]["deger"], c["panel_boyu_m"], anahtar not in yok))
                 for anahtar, ad, kural in (("tek_kat_panel", "tek kat panel", "tek_kat_panel_kapatma_m"), ("sandvic_panel", "sandviç panel", "sandvic_panel_kapatma_m"),
                                            ("trapez_sac", "trapez sac", "trapez_sac_kapatma_m"), ("osb_kiremit", "kiremit desen sac", "kiremit_kapatma_m"))]
    denemeler.append(("62 m² sandviç panel", (g62["plan_m"][0], g62["plan_m"][1], g62["egim"], kr["sandvic_panel_kapatma_m"]["deger"], g62["panel_boyu_m"], True)))
    sorun = 0
    for ad, olcu in denemeler:
        sonuc = {b: sagla(*olcu, baslangic=b) for b in BASLANGIC}
        hatalar = [h for _, hs in sonuc.values() for h in hs]
        sorun += len(hatalar)
        print(f"{ad:28s} " + " · ".join(f"{b} {n}" for b, (n, _) in sonuc.items()) + ("  geometri TAMAM" if not hatalar else "  HATA: " + "; ".join(hatalar[:3])))
    random.seed(8201)
    n = 0
    for _ in range(200):
        px = round(random.uniform(5, 16), random.choice((1, 2, 3)))
        py = round(random.uniform(4, px), random.choice((1, 2, 3)))
        egim, w = random.choice((0.25, 0.30, 0.33, 0.40)), random.choice((0.80, 0.87, 1.00, 1.10))
        boy = math.ceil(min(px, py) / 2 * math.sqrt(1 + egim ** 2) * 10 - 1e-9) / 10
        for paylas in (True, False):
            for b in BASLANGIC:
                n += 1
                _, hata = sagla(px, py, egim, w, boy, paylas, b)
                if hata:
                    sorun += 1
                    print("SORUN", px, py, egim, w, boy, paylas, b, hata[:3])
    print(f"rastgele kırma çatılar: {n} dizilim denendi; toplam sorun {sorun}")
    return 1 if sorun else 0


if __name__ == "__main__":
    raise SystemExit(main())
