#!/usr/bin/env python3
"""Üretim dosyasından (rulo form makinesinin CSV'leri) panel panel profil boyu ve et kalınlığı: çelik ağırlığının girdisi.

`skp_profil.py`nin üretim dosyası karşılığıdır (KT-02, 9 Ekim 2026). Her CSV bir çerçevedir (panel, makas, kiriş, kolon):
    FRAMESET,<ad>,...
    COMPONENT,<üye>,<etiket>,<adet>,<boy mm>,C,<sırt>,<başlık>,<et mm>,<çelik sınıfı>,x1,y1,x2,y2,<işlemler...>
Çıktı, `skp_profil.py --json` ile aynı biçimdedir: {çerçeve: {uye, boy_m, et_mm, et_dagilimi}}. Bir çerçevede birden çok et varsa `et_mm`
yazılmaz (null); dağılım yine verilir.

Kullanım: python uretim_profil.py <üretim klasörü> --json boylar.json
Klasördeki dosya ve klasör adları okunmaz (yalnız CSV içeriği); çıktıda ad, telefon ya da fiyat yoktur.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def oku(kok: Path) -> dict[str, dict]:
    cik: dict[str, dict] = {}
    for yol in sorted(kok.rglob("*.csv")):
        satirlar = list(csv.reader(yol.read_text(encoding="utf-8", errors="replace").splitlines()))
        adlar = [r[1] for r in satirlar if r and r[0] == "FRAMESET"]
        if len(adlar) != 1:
            raise SystemExit(f"{yol.name}: FRAMESET satırı bir tane olmalı ({len(adlar)})")
        ad = adlar[0]
        if ad in cik:
            raise SystemExit(f"Aynı çerçeve iki dosyada: {ad}")
        uye, dagilim = 0, {}
        for r in satirlar:
            if not r or r[0] != "COMPONENT":
                continue
            adet, boy_mm, et = int(r[3]), float(r[4]), float(r[8])
            uye += adet
            dagilim[et] = dagilim.get(et, 0.0) + adet * boy_mm / 1000
        if not uye:
            raise SystemExit(f"{yol.name}: üye yok")
        etler = sorted(dagilim)
        cik[ad] = {"uye": uye, "boy_m": round(sum(dagilim.values()), 3), "et_mm": etler[0] if len(etler) == 1 else None,
                   "et_dagilimi": {f"{e:g}": round(v, 3) for e, v in sorted(dagilim.items())}}
    if not cik:
        raise SystemExit(f"{kok}: CSV yok")
    return dict(sorted(cik.items()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("klasor", type=Path)
    ap.add_argument("--json", type=Path, required=True)
    a = ap.parse_args()
    c = oku(a.klasor)
    a.json.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    top: dict[str, list] = {}
    for v in c.values():
        e = top.setdefault(f"{v['et_mm']:g}" if v["et_mm"] is not None else "karışık", [0, 0.0])
        e[0] += 1
        e[1] += v["boy_m"]
    print(f"yazıldı: {a.json.name} · {len(c)} çerçeve, {sum(v['uye'] for v in c.values())} üye, {sum(v['boy_m'] for v in c.values()):.2f} m")
    for et, (n, boy) in sorted(top.items()):
        print(f"   et {et} mm: {n} çerçeve, {boy:.2f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
