#!/usr/bin/env python3
"""Çatı açılımı diziliminin geometrik sağlaması (`cati_acilim.dizilim`).

Çokgenlerle (shapely) şunlara bakar:
  1. Her yüzün şerit parçaları yüzü (saçaktan taşan şeritle birlikte) tam örtüyor ve üst üste binmiyor mu?
  2. Her paneldeki parçalar panelin (kapatma × boy) içinde mi; birbirinin üstüne biniyor mu?
  3. Her parça, atandığı yüz parçasıyla eş mi? Alt parça yalnız ötelenir; üst parça 180° çevrilir (ters yüz edilmez).
  4. Eşleme kuralı: iki parça veren kesimde parçalar karşılıklı yüzlerde ve aynı türden mi?
  5. Adet, alan olarak en az gereken panelden az olamaz.
  6. Panel boyu uzatma kuralı (Lokman, 4 Ekim 2026 16:18): adet ve toplam boy artmıyor; uzatma kuraldaki sınırı aşmıyor;
     uzatılan boyda adet, kesim payı 1 cm olsa da aynı; uzatılmayan çatıda koşulu sağlayan aday yok.

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

import kural

from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from cati_acilim import BASLANGIC, dizilim, kural_dizilimi, panel_yerlesimi

BURADA = Path(__file__).resolve().parent
TOL = 1e-6


def panel_sekilleri(d: dict):
    """Kesim planındaki yerleşim (`cati_acilim.panel_yerlesimi`; çizim ve ölçü tablosuyla aynı çokgenler):
    (panel no, parça, çokgen [panel koordinatı; m], alt mı üst mü)."""
    for no, p, kose, konum in panel_yerlesimi(d):
        yield no, p, Polygon(kose), konum


def es_mi(s1: Polygon, s2: Polygon) -> bool:
    """İki çokgen öteleme ile aynı mı (alt-sol köşeler hizalanarak)."""
    a = translate(s1, -s1.bounds[0], -s1.bounds[1])
    b = translate(s2, -s2.bounds[0], -s2.bounds[1])
    return a.symmetric_difference(b).area < TOL


def sagla(px: float, py: float, egim: float, w: float, boy: float, paylas: bool = True, baslangic: str = "sol", tasma: float = 0.0,
          kesim_payi: float = 0.0) -> tuple[int, list[str]]:
    d = dizilim(px, py, egim, w, boy, paylas, baslangic, kesim_payi, tasma)
    return d["adet"], dizilim_hatalari(d)


def dizilim_hatalari(d: dict) -> list[str]:
    """Bir dizilimin geometrik sağlaması; sorun yoksa boş liste."""
    (uzun_k, kisa_k), w, boy, paylas, ts = d["plan_m"], d["kapatma_m"], d["boy_m"], d["paylas"], d["tasma_m"]
    px, py = uzun_k, kisa_k
    hata: list[str] = []
    y0, H = min(px, py) / 2, d["egimli_boy_m"]
    for ad, ps in d["yuzler"].items():                       # 1) yüz parçaları yüzü (taşma şeridiyle) tam örtüyor
        E = max(px, py) if ad in ("ön", "arka") else min(px, py)
        yuz = Polygon([(0, -ts), (E, -ts), (E, 0), (E - y0, H), (y0, H), (0, 0)]) if E - 2 * y0 > 1e-9 else Polygon([(0, -ts), (E, -ts), (E, 0), (y0, H), (0, 0)])
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
    return hata


def main() -> int:
    kr = kural.oku()
    c = json.loads((BURADA / "sonuc" / "C8201_girdi.json").read_text(encoding="utf-8"))["cati"]
    g62 = json.loads((BURADA / "ornek_62m2_girdi.json").read_text(encoding="utf-8"))["cati"]
    sorun = 0
    # 1) kurallardaki ayarlarla listeye giren dizilimler
    for ad, cati, kaplama in ([(f"Ç8201 {x}", c, x) for x in ("tek_kat_panel", "sandvic_panel", "trapez_sac", "osb_kiremit")] + [("62 m² sandvic_panel", g62, "sandvic_panel")]):
        d = kural_dizilimi(kr, cati, kaplama)
        hatalar = dizilim_hatalari(d)
        sorun += len(hatalar)
        print(f"{ad:24s} {d['adet']:3d} adet · başlangıç {d['baslangic']:10s} · taşma {d['tasma_m'] * 100:.1f} cm · denemeler {d['denemeler']}"
              + ("  geometri TAMAM" if not hatalar else "  HATA: " + "; ".join(hatalar[:3])))
    # 2) rastgele kırma çatılar: bütün başlangıçlar, artan parça kullanılarak ve kullanılmadan, taşmalı ve taşmasız
    random.seed(8201)
    n = 0
    for _ in range(120):
        px = round(random.uniform(5, 16), random.choice((1, 2, 3)))
        py = round(random.uniform(4, px), random.choice((1, 2, 3)))
        egim, w = random.choice((0.25, 0.30, 0.33, 0.40)), random.choice((0.80, 0.87, 1.00, 1.10))
        tasma = random.choice((0.0, 0.05))
        pay = random.choice((0.0, 0.005))
        boy = math.ceil((min(px, py) / 2 * math.sqrt(1 + egim ** 2) + tasma) * 1000 - 1e-9) / 1000
        for paylas in (True, False):
            for b in BASLANGIC:
                n += 1
                _, hata = sagla(px, py, egim, w, boy, paylas, b, tasma, pay)
                if hata:
                    sorun += 1
                    print("SORUN", px, py, egim, w, boy, paylas, b, tasma, pay, hata[:3])
    # 3) panel boyu uzatma kuralı (Lokman, 4 Ekim 2026 16:18) rastgele kırma çatılarda: geometri; adet ve toplam boy artmıyor;
    #    uzatma en çok kuraldaki kadar; uzatılan boyda adet kesim payı 1 cm olsa da aynı; uzatılmadıysa hiçbir aday koşulu sağlamıyor
    uz, kd = kr["panel_boyu_uzatma"]["deger"], kr["kirma_cati_dizilim"]["deger"]
    tasma_k, m, uzatilan, payli, tam_saglam = kr["cati_kaplama_tasma_m"]["deger"], 0, 0, 0, 0
    yv_mm = (kr.get("panel_boyu_yuvarlama_mm") or {}).get("deger") or 1
    random.seed(4325)
    for _ in range(150):
        px = round(random.uniform(5, 16), random.choice((1, 2, 3)))
        py = round(random.uniform(4, px), random.choice((1, 2, 3)))
        egim = random.choice((0.25, 0.30, 0.33, 0.40))
        taban = math.ceil((min(px, py) / 2 * math.sqrt(1 + egim ** 2) + tasma_k) * 1000 / yv_mm - 1e-9) * yv_mm / 1000     # kuraldaki adıma yukarı
        for kaplama in ("tek_kat_panel", "trapez_sac", "osb_kiremit"):
            m += 1
            cati = {"plan_m": [max(px, py), min(px, py)], "egim": egim, "panel_boyu_m": taban, "panel_boyu_kaynak": "kural"}
            d = kural_dizilimi(kr, cati, kaplama)
            hata = dizilim_hatalari(d)

            def adet(b: float, pay: float) -> int:
                return dizilim(d["plan_m"][0], d["plan_m"][1], egim, d["kapatma_m"], b, d["paylas"], kd["baslangic"], pay, d["tasma_m"])["adet"]

            # Kuralın seçimi burada ayrıca kurulur (kuralın sözüyle; `kural_dizilimi`nin içine bakmadan) ve onun seçimiyle karşılaştırılır:
            # adet düşüren ve 1 cm kesim payıyla da aynı kalan boy; pay koşulu taban boy için de aranıyorsa (`taban_icin_de`) ve taban boyda pay inceyse
            # adedi aynı bırakıp 1 cm kesim payıyla gereken adedi düşüren boy. En az adet, sonra 1 cm payla en az adet, sonra en kısa boy.
            pay, sp = kd["kesim_payi_m"], uz["saglamlik_kesim_payi_m"]
            n0, n0_sp = adet(taban, pay), adet(taban, sp)
            ince = bool(uz.get("taban_icin_de")) and n0_sp > n0
            secenekler = []
            for i in range(1, round(uz["en_cok_m"] / uz["adim_m"]) + 1):
                b = round(taban + i * uz["adim_m"], 6)
                nb, nb_sp = adet(b, pay), adet(b, sp)
                if (nb < n0 and nb_sp == nb) or (ince and nb == n0 and nb_sp < n0_sp):
                    secenekler.append((nb, nb_sp, b))
            beklenen = min(secenekler) if secenekler else None
            if d["taban_adet"] != n0 or d["adet"] > n0 or d["boy_m"] - taban > uz["en_cok_m"] + 1e-9:
                hata.append("taban adedi tutmuyor, adet arttı ya da uzatma sınırı aşıldı")
            if d["uzatma"]:
                uzatilan += 1
                paydan = d["uzatma"].get("neden") == "pay"
                payli += paydan
                tam_saglam += d["bir_cm_payla_adet"] == d["adet"]
                if beklenen is None or (d["adet"], d["bir_cm_payla_adet"]) != beklenen[:2] or abs(d["boy_m"] - beklenen[2]) > 1e-9 \
                        or (uz.get("taban_icin_de") and paydan != (d["adet"] == n0)) or (not paydan and d["adet"] * d["boy_m"] >= n0 * taban):
                    hata.append("uzatma kuralı koşulları sağlanmıyor")
            elif beklenen or d["adet"] != d["taban_adet"] or abs(d["boy_m"] - taban) > 1e-9:
                hata.append("uzatma uygulanmalıydı ya da taban boy değişmiş")
            if hata:
                sorun += 1
                print("SORUN (uzatma)", px, py, egim, kaplama, taban, d["boy_m"], hata[:3])
    print(f"rastgele kırma çatılar: {n} dizilim denendi; panel boyu uzatma kuralı {m} çatı ve kaplamada denendi ({uzatilan} tanesinde boy uzadı" + (f", {payli} tanesinde pay koşulundan" if uz.get("taban_icin_de") else "") + f"); toplam sorun {sorun}")
    # özet (belge bu dosyadan okur; elle yazılmasın diye): hangi kural setiyle, kaç deneme, kaç uzatma
    ozet = {"kural_seti": kr.get("sema"), "dizilim": n, "kural_denemesi": m, "uzatilan": uzatilan, "pay_kosulundan": payli if uz.get("taban_icin_de") else None,
            "uzatilanlarda_tam_saglam": tam_saglam, "sorun": sorun}
    (BURADA / "sonuc" / "cati_acilim_saglama.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if sorun else 0


if __name__ == "__main__":
    raise SystemExit(main())
