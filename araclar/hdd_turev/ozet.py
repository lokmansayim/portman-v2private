"""Disk arşivinin türev katmanından proje başına adsız özet (İE-43 PR-2).

  python3 ozet.py <kök>

Mac'te koşar. Manifestlerden (anahtar başına en iyi satır) ve türev JSON'larından proje kodu başına sayılar çıkarır:
DWG (pano bloğu olan çizim ve pano eklemesi sayısı), PDF (sayfa, taranmış, metinde m²), Excel (yükleme listesi),
görsel (konum bilgisi). Yazar: `<kök>/_portman_analiz/turev/ozet.json`; ekrana toplamları basar. Ad, metin ya da kişisel veri
yazmaz; yalnız kod ve sayı.
"""

from __future__ import annotations

import collections
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from turev import DURUM_SIRASI  # noqa: E402

M2 = re.compile(r"(\d{2,3}(?:[.,]\d{1,2})?)\s*m\s*(?:²|2)(?![0-9])", re.I)


def en_iyi_satirlar(hedef: str) -> dict:
    """(kod, sıra, tür) → en iyi manifest satırı (tamam > kismi > hata; eşitte sonraki)."""
    iyi = {}
    for ad in sorted(os.listdir(hedef)):
        if not (ad.startswith("manifest") and ad.endswith(".jsonl")):
            continue
        with open(os.path.join(hedef, ad), encoding="utf-8") as f:
            for s in f:
                try:
                    d = json.loads(s)
                except ValueError:
                    continue
                k = (d["kod"], int(d["sira"]), d["tur"])
                if k not in iyi or DURUM_SIRASI.get(d.get("durum"), 0) >= DURUM_SIRASI.get(iyi[k].get("durum"), 0):
                    iyi[k] = d
    return iyi


def _json(hedef: str, satir: dict):
    c = (satir.get("ciktilar") or {}).get("json_gz")
    if not c:
        return None
    try:
        with gzip.open(os.path.join(hedef, c["yol"]), "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _excel_liste_mi(oz: dict) -> bool:
    for sayfa in oz.get("sayfalar", []):
        for h in sayfa.get("hucreler", []):
            v = h[1] if len(h) > 1 else None
            if isinstance(v, str) and "YÜKLEME" in v.replace("i", "İ").upper():
                return True
    return False


def ozet(kok: str) -> dict:
    hedef = os.path.join(kok, "_portman_analiz", "turev")
    projeler = collections.defaultdict(lambda: collections.Counter())
    m2 = collections.defaultdict(collections.Counter)
    for (kod, _sira, tur), d in en_iyi_satirlar(hedef).items():
        p = projeler[kod]
        p[f"{tur}_{d.get('durum')}"] += 1
        if d.get("durum") == "hata":
            continue
        if tur in ("dwg", "dxf"):
            if d.get("pano_eklemesi"):
                p["dwg_panolu"] += 1
                p["pano_eklemesi"] += d["pano_eklemesi"]
        elif tur == "pdf":
            p["pdf_sayfa"] += d.get("sayfa") or 0
            p["pdf_taranmis"] += bool(d.get("taranmis_olabilir"))
            oz = _json(hedef, d)
            for s in (oz or {}).get("sayfalar", []):
                for x in M2.findall(s.get("metin", "")):
                    m2[kod][x.replace(",", ".")] += 1
        elif tur == "excel":
            oz = _json(hedef, d)
            if oz and _excel_liste_mi(oz):
                p["excel_liste"] += 1
        elif tur == "gorsel":
            p["gorsel_konumlu"] += bool(d.get("konum_var"))
    sonuc = {}
    for kod in sorted(projeler):
        p = dict(projeler[kod])
        if m2[kod]:
            p["pdf_m2_en_sik"] = [float(x) for x, _ in m2[kod].most_common(3)]
        sonuc[kod] = p
    t = collections.Counter()
    for p in sonuc.values():
        for k, v in p.items():
            if isinstance(v, int):
                t[k] += v
        t["proje_dwg_panolu"] += p.get("dwg_panolu", 0) > 0
        t["proje_excel_liste"] += p.get("excel_liste", 0) > 0
        t["proje_m2"] += "pdf_m2_en_sik" in p
        t["proje_panolu_ve_liste"] += p.get("dwg_panolu", 0) > 0 and p.get("excel_liste", 0) > 0
        t["proje_panolu_liste_m2"] += p.get("dwg_panolu", 0) > 0 and p.get("excel_liste", 0) > 0 and "pdf_m2_en_sik" in p
    return {"toplam": dict(sorted(t.items())), "projeler": sonuc}


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    kok = argv[0]
    o = ozet(kok)
    yol = os.path.join(kok, "_portman_analiz", "turev", "ozet.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
    print(json.dumps(o["toplam"], ensure_ascii=False))
    print(f"proje {len(o['projeler'])}; yazıldı {yol}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
