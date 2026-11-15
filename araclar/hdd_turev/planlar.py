"""Disk arşivinin çizimlerinde pano bloklarından plan adayları (İE-43 PR-2).

  python3 planlar.py <kök> [--esik 400] [--en-az 12]

Mac'te koşar. Her DWG türevinin JSON'undaki pano eklemelerini (blok adında "PANO", model alanı) yakınlığa göre öbekler:
iki pano `--esik` cm'den yakınsa aynı plandadır (tek bağlantılı öbekleme, ızgarayla). En az `--en-az` panolu öbek bir plan
adayıdır. Bir dosyada birçok proje ve aynı planın kopyaları olabilir; aynı imzalı (pano sayısı, kutu ölçüsü, pano türleri)
adaylar "tekil" diye ayrıca sayılır.

Yazar: `<kök>/_portman_analiz/turev/planlar.json` (kod, sıra, aday başına sayılar; her tekil imzanın bir örneğinin pano
noktaları, göreli cm, tür); ekrana toplamları basar. Ad ve yazı yazmaz.
Ölçü birimi: çizimler santimetre (pano aralığı 125,5); $INSUNITS çoğu dosyada 4 (mm) yazsa da aralık cm'dir (15 Kasım).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ozet  # noqa: E402


def pano_turu(ad: str) -> str:
    """Blok adından kaba tür: duvar kalınlığı (100/60) ve açıklık (kapı, pencere, vasistas, dolu)."""
    a = ad.upper().replace("İ", "I")
    kalinlik = "60" if a.startswith("60") or " 60" in a[:6] else "100"
    if "KAPI" in a:
        acik = "kapi"
    elif "VASISTAS" in a:
        acik = "vasistas"
    elif "PENCERE" in a:
        acik = "pencere"
    else:
        acik = "dolu"
    return f"{kalinlik}_{acik}"


def obekle(noktalar: list[tuple[float, float]], esik: float) -> list[list[int]]:
    """Tek bağlantılı öbekleme: aralarındaki uzaklık `esik`ten küçük noktalar aynı öbekte (ızgara + birleşim-bul)."""
    ata = list(range(len(noktalar)))

    def bul(i):
        while ata[i] != i:
            ata[i] = ata[ata[i]]
            i = ata[i]
        return i

    izgara = collections.defaultdict(list)
    for i, (x, y) in enumerate(noktalar):
        izgara[(int(x // esik), int(y // esik))].append(i)
    e2 = esik * esik
    for (gx, gy), L in izgara.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in izgara.get((gx + dx, gy + dy), ()):
                    for i in L:
                        if i < j:
                            xi, yi = noktalar[i]
                            xj, yj = noktalar[j]
                            if (xi - xj) ** 2 + (yi - yj) ** 2 <= e2:
                                ri, rj = bul(i), bul(j)
                                if ri != rj:
                                    ata[ri] = rj
    obek = collections.defaultdict(list)
    for i in range(len(noktalar)):
        obek[bul(i)].append(i)
    return list(obek.values())


def adaylar(eklemeler: list[dict], esik: float, en_az: int) -> list[dict]:
    P = [e for e in eklemeler if "PANO" in str(e.get("blok", "")).upper() and not e.get("kagit")
         and e.get("x") is not None and e.get("y") is not None]
    sonuc = []
    for ob in obekle([(e["x"], e["y"]) for e in P], esik):
        if len(ob) < en_az:
            continue
        xs = [P[i]["x"] for i in ob]
        ys = [P[i]["y"] for i in ob]
        turler = collections.Counter(pano_turu(P[i]["blok"]) for i in ob)
        en, boy = round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)
        imza_metni = json.dumps([len(ob), sorted([round(en), round(boy)]), sorted(turler.items())])
        x0, y0 = min(xs), min(ys)
        sonuc.append({"pano": len(ob), "kutu_cm": [en, boy], "turler": dict(sorted(turler.items())),
                      "imza": hashlib.sha256(imza_metni.encode()).hexdigest()[:12],
                      "noktalar": [[round(P[i]["x"] - x0, 1), round(P[i]["y"] - y0, 1), round(P[i].get("aci") or 0),
                                    pano_turu(P[i]["blok"])] for i in ob]})
    sonuc.sort(key=lambda a: -a["pano"])
    return sonuc


def calistir(kok: str, esik: float, en_az: int) -> dict:
    hedef = os.path.join(kok, "_portman_analiz", "turev")
    dosyalar, imzalar, projeler, ornekler = [], collections.Counter(), collections.defaultdict(set), {}
    for (kod, sira, tur), d in sorted(ozet.en_iyi_satirlar(hedef).items()):
        if tur != "dwg" or not d.get("pano_eklemesi"):
            continue
        oz = ozet._json(hedef, d)
        if not oz:
            continue
        A = adaylar(oz.get("eklemeler", []), esik, en_az)
        if not A:
            continue
        for a in A:
            imzalar[a["imza"]] += 1
            projeler[kod].add(a["imza"])
            ornekler.setdefault(a["imza"], {"kod": kod, "sira": sira, **a})
            del a["noktalar"]
        dosyalar.append({"kod": kod, "sira": sira, "aday": A})
    toplam = {"dosya": len(dosyalar), "proje": len(projeler), "aday": sum(imzalar.values()), "tekil_aday": len(imzalar),
              "esik_cm": esik, "en_az_pano": en_az}
    for imza, o in ornekler.items():
        o["kopya"] = imzalar[imza]
    return {"toplam": toplam, "dosyalar": dosyalar, "ornekler": sorted(ornekler.values(), key=lambda o: -o["pano"])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kok")
    ap.add_argument("--esik", type=float, default=400.0)
    ap.add_argument("--en-az", type=int, default=12)
    a = ap.parse_args(argv)
    o = calistir(a.kok, a.esik, a.en_az)
    yol = os.path.join(a.kok, "_portman_analiz", "turev", "planlar.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
    print(json.dumps(o["toplam"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
