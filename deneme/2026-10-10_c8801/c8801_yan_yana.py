#!/usr/bin/env python3
"""Ç8801'in listesi ile Ç8201'in listesi yan yana (iki katalog modeli; ikisi de çelik standardı, yöntem A, tek kat panel).

Gerçek bir Ç8801 listesi yok; bu tablo bir sağlamadır: aynı kural kitabı iki modelde ne kadar farklı sonuç veriyor ve farkın nedeni modelde mi.
Satırlar listenin iç kalem adıyla (`kalem`) eşlenir; aynı kalemin birden çok boyutu (ör. iki panel boyu) ayrı satırdır. Hesap yapmaz, yalnız okur.

Kullanım: python c8801_yan_yana.py <Ç8201 listesi.json> <Ç8801 listesi.json> --md <çıktı.md>
"""
import argparse
import json
from pathlib import Path


def tr(x, n=2):
    if x is None:
        return ""
    s = f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.rstrip("0").rstrip(",") if "," in s else s


def hucre(rows):
    return "<br>".join(f"{r['adet'] if r['adet'] is not None else '—'}" + (f" × {r['boyut']}" if r["boyut"] else "")
                       + (f" ({tr(r['olcu'])} {r['birim']})" if r.get("olcu") is not None else "") + (f", {tr(r['kg'], 0)} kg" if r.get("kg") else "")
                       for r in rows) or "—"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("c8201", type=Path)
    ap.add_argument("c8801", type=Path)
    ap.add_argument("--md", type=Path, required=True)
    a = ap.parse_args()
    A = json.loads(a.c8201.read_text(encoding="utf-8"))
    B = json.loads(a.c8801.read_text(encoding="utf-8"))
    sira = []
    for s in A["satirlar"] + B["satirlar"]:
        k = (s["grup"], s["kalem"])
        if k not in sira:
            sira.append(k)
    out = [f"# {B['ad'].split(' · ')[0]} ile {A['ad'].split(' · ')[0]} yan yana", "",
           f"- {A['ad']}: {A['yontem_adi']}; çatı kaplaması {A['cati_kaplamasi']}.",
           f"- {B['ad']}: {B['yontem_adi']}; çatı kaplaması {B['cati_kaplamasi']}.",
           "- Gerçek bir Ç8801 listesi yok. Tablo bir sağlamadır: aynı kural kitabı iki modelde ne veriyor. Farkların nedeni README'de.",
           "", f"| Grup | Kalem | {A['ad'].split(' · ')[0]} | {B['ad'].split(' · ')[0]} |", "|---|---|---|---|"]
    for grup, kalem in sira:
        ra = [s for s in A["satirlar"] if (s["grup"], s["kalem"]) == (grup, kalem)]
        rb = [s for s in B["satirlar"] if (s["grup"], s["kalem"]) == (grup, kalem)]
        ad = (rb or ra)[0].get("liste_adi") or kalem
        out.append(f"| {grup} | {ad} | {hucre(ra)} | {hucre(rb)} |")
    a.md.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("yazıldı:", a.md.name, "|", len(sira), "kalem")


if __name__ == "__main__":
    main()
