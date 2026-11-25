"""python -m araclar.uretim <dosya ya da klasör> … [--json <çıktı.json>]

Üretim dosyalarını okur, her dosyanın özgünüyle bayt bayt aynı geri yazıldığını denetler, özetini basar.
--json: okunan bütün çerçeveleri (parça, uç koordinatları, işlem yerleri) tek JSON'a yazar (rehber ve 3B görünüm okur).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bde, islem, mrd


def _dosyalar(yollar):
    for y in map(Path, yollar):
        if y.is_dir():
            yield from sorted(p for p in y.iterdir() if p.suffix.lower() in (".bde", ".csv"))
        else:
            yield y


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m araclar.uretim")
    ap.add_argument("yollar", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--islem", action="store_true", help="MRD dosyasında işlemleri geometriden üretip dosyadakilerle kıyasla")
    a = ap.parse_args(argv)
    cikti, hata = [], 0
    for y in _dosyalar(a.yollar):
        ham = y.read_bytes()
        if y.suffix.lower() == ".bde":
            v = bde.oku(y)
            ayni = bde.yaz(v) == ham
            tut, top = bde.vida_denetimi(v)
            print(f"{'AYNI ' if ayni else 'FARKLI'} {y.name}: {len(bde.panolar(v))} pano, {len(v['cubuklar'])} çubuk, vida {tut}/{top}")
            cikti.append({"dosya": y.name, "bicim": "bde", "cubuklar": v["cubuklar"]})
        else:
            v = mrd.oku(y)
            ayni = mrd.yaz(v) == ham
            o = mrd.ozet(v)
            print(f"{'AYNI ' if ayni else 'FARKLI'} {y.name}: {o['cerceve']}, {o['cubuk']} çubuk, {o['toplam_boy_m']} m, {o['islem']}")
            if a.islem:
                k = islem.kiyas(v["parcalar"], islem.uret(v["parcalar"]))
                print("       işlem (tutan/dosyadaki, fazla): " + ", ".join(f"{t} {x[0]}/{x[1]} +{x[2]}" for t, x in sorted(k.items())))
            cikti.append({"dosya": y.name, "bicim": "mrd", "cerceve": v["cerceve"], "ozet": o, "parcalar": v["parcalar"]})
        hata += not ayni
    if a.json:
        Path(a.json).write_text(json.dumps(cikti, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
