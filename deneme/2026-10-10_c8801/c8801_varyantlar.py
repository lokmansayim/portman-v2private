#!/usr/bin/env python3
"""Ç8801'in üç çatısının listeleri yan yana: yalnız farklı olan satırlar (plan, duvar ve iç kaplama aynı; fark çatıdan).

Lokman, 10 Ekim 2026 14:46: "3 modelin de gayet güzel hatta çatı olarak 3'üde olur ... ben 1. versiyonu beğendim ama asıl katalogdaki
model 2. versiyon neden böyle bir sonuç var maliyet açısından". Tablo, çatı seçiminin listeye etkisini (adet ve ölçü; fiyat yok) gösterir.
Satırlar listenin iç kalem adıyla (`kalem`) eşlenir; aynı kalemin birden çok boyutu (ör. iki panel boyu) aynı hücrede. Hesap yapmaz, yalnız okur.

Kullanım: python c8801_varyantlar.py <liste.json> <liste.json> [...] --md <çıktı.md>
"""
import argparse
import json
from pathlib import Path

from c8801_yan_yana import hucre


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("listeler", type=Path, nargs="+")
    ap.add_argument("--md", type=Path, required=True)
    a = ap.parse_args()
    L = [json.loads(p.read_text(encoding="utf-8")) for p in a.listeler]
    kisa = [x["ad"].split(" · ")[0] for x in L]
    sira = []
    for x in L:
        for s in x["satirlar"]:
            if (s["grup"], s["kalem"]) not in sira:
                sira.append((s["grup"], s["kalem"]))
    farkli, ayni = [], 0
    for grup, kalem in sira:
        hucreler = [hucre([s for s in x["satirlar"] if (s["grup"], s["kalem"]) == (grup, kalem)]) for x in L]
        if len(set(hucreler)) == 1:
            ayni += 1
            continue
        ad = next(s.get("liste_adi") or kalem for x in L for s in x["satirlar"] if (s["grup"], s["kalem"]) == (grup, kalem))
        farkli.append(f"| {grup} | {ad} | " + " | ".join(hucreler) + " |")
    out = [f"# {kisa[0]}: çatı varyantlarının listeleri", ""]
    out += [f"- {x['ad']}: {x['yontem_adi']}; çatı kaplaması {x['cati_kaplamasi']}." for x in L]
    out += ["- Aynı plan, aynı kurallar; yalnız çatı farklı. Fiyat yok; adet ve ölçü. Çatıların biçimi README'de.",
            f"- Kalem sayısı {len(sira)}: {len(L)} listede aynı olan {ayni}, farklı olan {len(farkli)} (aşağıda yalnız bunlar).", "",
            "| Grup | Kalem | " + " | ".join(kisa) + " |", "|---|---|" + "---|" * len(L)]
    a.md.write_text("\n".join(out + farkli) + "\n", encoding="utf-8")
    print("yazıldı:", a.md.name, "|", len(sira), "kalem,", len(farkli), "farklı")


if __name__ == "__main__":
    main()
