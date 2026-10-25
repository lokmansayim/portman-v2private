"""İE-15 · K3 · Elektrik noktaları oda oda: kural (kart modeli) ile pafta yan yana. Hakem değildir; kapıya girmez, yalnız bilgi.

Kart modelinin sayımı (`python -m motor.kart_model … --kod PK01` → `<kod>_kart_sayim.json`) odaların çokgenini (`elektrik.odalar`) ve her
noktanın odasını (`elektrik.noktalar[].bilgi.Mahal`) taşır. Paftanın noktaları hakemin cevabındadır (`ayrinti.elektrik.konumlar`: tür ve yer,
Motor'un plan çerçevesinde, cm). Pafta noktası içinde durduğu odaya, odaların dışındaysa (duvarın üstü) `tolerans` içindeki en yakın odaya
yazılır; o da yoksa "oda dışı". Buat paftada sayılır, kart modelinde yoktur (liste üretecinde kalır).

Kullanım:
    python3 -I testler/kimlik/k3_oda_tablosu.py <kart_sayim.json> <cevap.json> [--md <tablo.md>]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from shapely.geometry import Point, Polygon

NOKTALAR = (("tavan_armaturu", "Duy"), ("glop", "Glop"), ("anahtar_tekli", "Anahtar"), ("anahtar_cift", "Çift anahtar"),
            ("priz_tekli", "Priz"), ("priz_cift", "Çift priz"), ("uydu_prizi", "Uydu"), ("zil", "Zil"), ("sigorta_kutusu", "Sigorta"),
            ("buat", "Buat"))
ODA_DISI = "oda dışı"


def tablo(say: dict, cevap: dict, tolerans: float = 20.0) -> dict:
    """{odalar: [ad], model: {ad: Counter}, pafta: {ad: Counter}, kaynak: {ad: yazı}}; noktanın türü paftadaki adıdır (`elektrik.<ad>`)."""
    E = say["elektrik"]
    odalar = [(o["ad"], Polygon(o["poligon"])) for o in E["odalar"] if o["poligon"]]
    model = {o["ad"]: Counter() for o in E["odalar"]}
    for p in E["noktalar"]:
        if not p["pafta"]:                                              # kablo
            continue
        tur = p["pafta"][0].split(".", 1)[1]
        model.setdefault(p["bilgi"]["Mahal"], Counter())[tur] += 1
    pafta = {ad: Counter() for ad in model}
    for k in cevap["ayrinti"]["elektrik"]["konumlar"]:
        q = Point(k["xy"])
        icinde = next((ad for ad, poly in odalar if poly.covers(q)), None)
        if icinde is None:
            uzak, ad = min(((poly.distance(q), ad) for ad, poly in odalar), default=(None, None))
            icinde = ad if uzak is not None and uzak <= tolerans else ODA_DISI
        pafta.setdefault(icinde, Counter())[k["tur"]] += 1
    sira = list(model) + [ad for ad in pafta if ad not in model]
    return {"odalar": sira, "model": model, "pafta": pafta, "kaynak": {o["ad"]: o["kaynak"] for o in E["odalar"]}}


def md(t: dict) -> str:
    satir = ["| Oda | " + " | ".join(b for _, b in NOKTALAR) + " |", "|---|" + "---|" * len(NOKTALAR)]
    toplam_m, toplam_p = Counter(), Counter()
    for ad in t["odalar"]:
        m, p = t["model"].get(ad, Counter()), t["pafta"].get(ad, Counter())
        toplam_m.update(m)
        toplam_p.update(p)
        hucre = []
        for tur, _ in NOKTALAR:
            a, b = ("—" if tur == "buat" else m[tur]), p[tur]
            hucre.append(" " if a in (0, "—") and not b else f"{a} / {b}" if a != b else f"{a}")
        satir.append(f"| {ad} | " + " | ".join(hucre) + " |")
    satir.append("| **Toplam** | " + " | ".join(f"**{'—' if tur == 'buat' else toplam_m[tur]} / {toplam_p[tur]}**" for tur, _ in NOKTALAR) + " |")
    return ("Hücre: kural / pafta (tek sayı: ikisi aynı; boş: ikisinde de yok). Kural kart modelinin noktaları (liste üretecinin oda kuralı), "
            "pafta hakemin okuduğu noktalar.\n\n" + "\n".join(satir) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sayim", type=Path)
    ap.add_argument("cevap", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    metin = md(tablo(json.loads(a.sayim.read_text(encoding="utf-8")), json.loads(a.cevap.read_text(encoding="utf-8"))))
    if a.md:
        a.md.write_text(metin, encoding="utf-8")
    print(metin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
