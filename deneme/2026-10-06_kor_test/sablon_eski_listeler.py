#!/usr/bin/env python3
"""Eylül 2026 uygulaması (`yukleme.py --sablon 2026`) 2025 tarihli üç gerçek listede ne veriyor?

Kör test kıyasında Eylül 2026 listesinin şablonu ve paftaları, mevcut kurallardan birçok yerde farklı çıktı (`kurallar.json` → `sablon_2026`).
Bu betik aynı katmanı 2025 tarihli üç örnek listeye uygular: katman o listelerde de tutuyorsa değişiklik eskiden beri var demektir;
tutmuyorsa uygulama 2025 ile Eylül 2026 arasında değişmiştir ve hangisinin geçerli olacağı karardır.

Örnek girdilerde pafta ölçüsü yoktur (tavan omegası dizilimi, saçağın altındaki cephe boyları, duvar dibi kenarları): o kalemlerde katman
yalnız formülü değiştirir, ölçü bugünkü kuraldaki ölçüdür. Katmanda adı değişen kalem (çatı izolasyonu 100 mm; 2025 listelerinde çatı şiltesi
80 mm) listedeki adıyla karşılaştırılır: adet aynıdır, ad farkı ayrıca yazılır.

Kullanım: python sablon_eski_listeler.py [--md sonuc/sablon_2026_eski_listeler.md] [--ozet]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
YUKLEME = BURADA.parent / "2026-10-03_yukleme"
sys.path.insert(0, str(YUKLEME))
import kurallar_oku  # noqa: E402
import yukleme  # noqa: E402

ORNEKLER = [("90 m² (Eylül 2025; beşik)", "ornek_90m2"), ("62 m² (Eylül 2025; kırma)", "ornek_62m2"), ("105 m² (Kasım 2025; beşik + cumba)", "ornek_105m2")]
# katmanda adı değişen kalem → 2025 listelerindeki adı (adet formülü aynı)
ESKI_AD = [(re.compile(r"^Çatı izolasyonu \d+ mm$"), "Çatı şiltesi 80 mm")]
NOT = ("Okuma: Eylül 2026 uygulaması 2025 listelerinde bugünkü kurallardan daha çok satır tutmuyorsa o listeler başka bir uygulamayla hazırlanmış demektir "
       "(hangi kalemlerin tutmaya başladığı, hangilerinin bozulduğu aşağıdaki tablolarda). Tavan omegası ve aşıkta şablonun formülü paftadaki toplam boy üzerinedir; "
       "örnek girdilerde pafta toplamı olmadığı için burada kuralın kendi toplamı kullanıldı. Paftalardaki toplamlarla (62 · 90 · 105 m²) şablonun formülü tavan "
       "omegasında 28 · 41 · 45 (listeler 26 · 40 · 44), aşıkta 44 · 62 · 78 (listeler 41 · 57 · 71) veriyor (`kurallar.json` → `tavan_omegasi_aralik_m`, `asik.zayiat`).")


def hesap(girdi: dict, kurallar: dict, sablon: bool) -> tuple[dict[str, int], dict[str, str]]:
    """Dönen: ({2025 listesindeki adıyla kalem: adet}, {2025 adı: katmandaki adı} (adı değişenler))."""
    g = json.loads(json.dumps(girdi))
    if sablon:
        g["sablon"] = "2026"
    adet, yeni_ad = {}, {}
    for s in yukleme.hesapla(g, kurallar)["satirlar"]:
        if s["adet"] is None or s["durum"] == "liste":
            continue
        ad = next((eski for desen, eski in ESKI_AD if desen.match(s["kalem"])), s["kalem"])
        if ad != s["kalem"]:
            yeni_ad[ad] = s["kalem"]
        adet[ad] = s["adet"]
    return adet, yeni_ad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", type=Path)
    ap.add_argument("--ozet", action="store_true", help="satırları tek tek yazdırma")
    a = ap.parse_args()
    kurallar = kurallar_oku.oku()
    cik = ["# Eylül 2026 uygulaması, 2025 tarihli üç gerçek listede", "",
           "`sablon_eski_listeler.py` ile üretilir; elle düzeltilmez. Aynı satır / karşılaştırılan satır: gerçek listede adı aynı olan ve adedi hesaplanan kalemler.", "",
           NOT, "", "| Liste | Bugünkü kurallar | + Eylül 2026 uygulaması |", "|---|---|---|"]
    ayrinti: list[str] = []
    for ad, kok in ORNEKLER:
        girdi = json.loads((YUKLEME / f"{kok}_girdi.json").read_text(encoding="utf-8"))
        gercek = {k: v["adet"] for k, v in json.loads((YUKLEME / f"{kok}_gercek_liste.json").read_text(encoding="utf-8"))["kalemler"].items()
                  if isinstance(v, dict) and v.get("adet") is not None}
        (bugun, _), (sablon, yeni_ad) = hesap(girdi, kurallar, False), hesap(girdi, kurallar, True)
        ozet = []
        for h in (bugun, sablon):
            ortak = [k for k in h if k in gercek]
            ozet.append(f"{sum(1 for k in ortak if h[k] == gercek[k])} / {len(ortak)}")
        cik.append(f"| {ad} | {ozet[0]} | {ozet[1]} |")
        print(f"{ad}: bugünkü kurallar {ozet[0]} · + Eylül 2026 {ozet[1]}")
        ayrinti += ["", f"## {ad}", "", "| Kalem | Gerçek liste | Bugünkü kurallar | + Eylül 2026 | Sonuç |", "|---|---|---|---|---|"]
        for k in sorted(set(bugun) | set(sablon)):
            if k not in gercek or bugun.get(k) == sablon.get(k):
                continue
            b, s_, g_ = bugun.get(k), sablon.get(k), gercek[k]
            sonuc = ("yalnız birinde var" if s_ is None or b is None else "tutmaya başladı" if s_ == g_ and b != g_ else "tutuyordu, bozuldu" if b == g_ and s_ != g_ else
                     "yaklaştı" if abs(s_ - g_) < abs(b - g_) else "uzaklaştı" if abs(s_ - g_) > abs(b - g_) else "aynı uzaklıkta, öbür yanda")
            ayrinti.append(f"| {k} | {g_} | {'—' if b is None else b} | {'—' if s_ is None else s_} | {sonuc} |")
            if not a.ozet:
                print(f"   {k[:44]:44s} liste {g_!s:>6} | bugün {b!s:>6} | şablon {s_!s:>6} | {sonuc}")
        # katmanın eklediği ya da adını değiştirdiği, karşılaştırmada görünmeyen kalemler
        eklenen = sorted(k for k in sablon if k not in bugun and k not in gercek)
        if eklenen:
            ayrinti += ["", "Katmanın eklediği, bu listede olmayan kalemler: " + ", ".join(f"{k} ({sablon[k]})" for k in eklenen) + "."]
        if yeni_ad:
            ayrinti += ["", "Katmanda adı değişen kalemler (adet aynı; karşılaştırma listedeki adla): " + ", ".join(f"{e} → {y}" for e, y in sorted(yeni_ad.items())) + "."]
    cik += ayrinti
    if a.md:
        a.md.write_text("\n".join(cik) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
