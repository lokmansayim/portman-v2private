"""Panelli Yapı Tanımı'ndan bölmesiz yazım (İE-16 PR-3a): karkas kuralının girdisi.

Paftadan panel panel yazılmış tanımda (PR-2'nin ÇP-06'sı; bankadaki KT-01 = ÇP-13, KT-03 = ÇP-07) aynı hattaki uç uca paneller tek duvar
olur (karkas kuralının koşusu: `motor/genel/karkas.py` › `kosular`); duvarlar W01… adını alır. Açıklıklar yeni duvarına yazılır; metinlerdeki
panel adları (D01…) duvarın adına çevrilir. Karkas modeli (`celik_modeli`) çıkarılır, `karkas: "kural"` yazılır: panel bölmesi tanımda
yoktur, kuraldan gelir. Kaynağın `okunmayanlar` notuna, onun kaynak tanımı anlattığı eklenir. Geometri (kutuların birleşimi), mahaller,
açıklıklar ve çatı aynı kalır.

    python3 -m testler.celik.projeler.bolmesiz <kaynak tanım> <çıktı> --kod ÇP-07 --ad "…" --cizim "…"

Çıktı elle düzeltilmez: `test_karkas_projeleri.py` aracı yeniden koşar ve dosyayla bayt bayt aynı ister.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
from motor.genel import karkas, yapi  # noqa: E402

AD = re.compile(r"\b[A-ZÇ]{1,4}\d{1,2}\b")          # panel ve duvar adları (D01, MD1, VD3…); tanımda olmayan ad olduğu gibi kalır
ALANLAR = ("ad", "sinif", "kutu", "yukseklik", "profil", "ust_kot", "kaplama_yuksekligi")


def _cevir(x, harita: dict):
    if isinstance(x, str):
        return AD.sub(lambda m: harita.get(m.group(0), m.group(0)), x)
    if isinstance(x, list):
        return [_cevir(v, harita) for v in x]
    if isinstance(x, dict):
        return {k: _cevir(v, harita) for k, v in x.items()}
    return x


def bolmesiz(t: dict, kaynak_yolu: str, kod: str, ad: str, cizim: str) -> dict:
    y = yapi.kur(t)
    kos = karkas.kosular(y, t)
    harita, yeni_duvarlar, adli = {}, [], {w["ad"]: w for w in t["duvarlar"]}
    for i, ks in enumerate(kos, 1):
        wad = f"W{i:02d}"
        ws = [adli[a] for a in ks["duvarlar"]]
        x0 = min(w["kutu"][0] for w in ws); y0 = min(w["kutu"][1] for w in ws)
        x1 = max(w["kutu"][2] for w in ws); y1 = max(w["kutu"][3] for w in ws)
        e = {k: ws[0][k] for k in ALANLAR if k in ws[0]}
        e.update(ad=wad, kutu=[x0, y0, x1, y1])
        yeni_duvarlar.append(e)
        for a in ks["duvarlar"]:
            harita[a] = wad
    kalan = [w for w in t["duvarlar"] if w["ad"] not in harita]          # kolon ve baca olduğu gibi
    out = copy.deepcopy({k: v for k, v in t.items() if k not in ("celik_modeli",)})
    out = {k: (_cevir(v, harita) if k not in ("duvarlar", "kaynak") else v) for k, v in out.items()}
    out["kod"], out["ad"] = kod, ad
    out["kaynak"] = {**{k: _cevir(v, harita) for k, v in t.get("kaynak", {}).items() if k != "cizim"}, "cizim": cizim,
                     "bolmesiz": f"{kaynak_yolu} tanımının bölmesiz yazımı (testler/celik/projeler/bolmesiz.py): aynı hattaki uç uca paneller tek duvar "
                                 "(W01…); panel bölmesi tanımda yok, karkas kuralından (`karkas: kural`). Karkas modeli (`celik_modeli`) çıkarıldı."}
    if "okunmayanlar" in out["kaynak"]:              # kaynağın notu kendi okunuşunu anlatır (ör. "çelik ağırlığı ortalamadan"); bu yazımda ağırlık kuraldan
        out["kaynak"]["okunmayanlar"] += (" [Bölmesiz yazım: bu not kaynak tanımın okunuşunu anlatır; bu yazımda duvar, kolon ve kiriş panellerinin "
                                          "bölmesi ve ağırlığı karkas kuralından gelir.]")
    out["duvarlar"] = yeni_duvarlar + kalan
    for a in out.get("acikliklar", []):
        a["duvar"] = harita.get(a["duvar"], a["duvar"])
    out["karkas"] = "kural"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kaynak", type=Path); ap.add_argument("cikti", type=Path)
    ap.add_argument("--kod", required=True); ap.add_argument("--ad", required=True); ap.add_argument("--cizim", required=True)
    a = ap.parse_args(argv)
    t = json.loads(a.kaynak.read_text(encoding="utf-8"))
    yol = a.kaynak.resolve().relative_to(KOK).as_posix()
    out = bolmesiz(t, yol, a.kod, a.ad, a.cizim)
    a.cikti.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{a.cikti}: {len(t['duvarlar'])} duvar → {len(out['duvarlar'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
