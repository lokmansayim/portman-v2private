#!/usr/bin/env python3
"""İE-08 GM1/GM2 kanıtı: `motor.genel.uret` (ana koddaki paket) ile yedi modelin çizim seti ve listesi üretilir, depodaki ie-05 çıktılarıyla
karşılaştırılır: plan / görünüşler / pafta PNG ve liste JSON bayt bayt (sha256), IFC içerikçe (motor/genel/iz.py), IFC şema hatası 0.
Ç8201'in 0.5 seti depoda olmadığı için `--taban <klasör>` ile Adım 2'de üretilen taban çıktısına karşılaştırılır.

    <python> testler/genel/paket_kiyas.py --cikti <klasör> [--taban <taban kıyas klasörü>/cizim/C8201_05] [--etiket main]

Hangi Python ile koşulursa o paket setini sınar (ie-05 seti, ana set 3.11, sunucu seti 3.12). Perspektif üretilmez (VTK gerekmez).
Çıkış: 0 hepsi aynı, 1 fark var. Rapor: <cikti>/paket_kiyas.md ve .json.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

# model → (tanım, depodaki çizim klasörü, depodaki liste JSON'u ya da adayları, yöntem, elektrik sayımı)
# KT listeleri: deneme klasöründe aynı tanımın birden çok listesi var (kör, kıyas 0.12/0.15/0.17, cevaplar/kararlar = güncel set 0.19);
# kör testlerde liste pafta elektrik sayımıyla (`sonuc/KT0x_pafta_sayimi.json`) üretildi → aynı girdi verilir, güncel setin listesi
# (cevaplar/kararlar A ve B) aday; adaylardan biriyle bayt bayt aynıysa AYNI ve hangisiyle aynı olduğu yazılır.
KT = {"KT01": "deneme/2026-10-06_kor_test", "KT02": "deneme/2026-10-09_kor_test_2", "KT03": "deneme/2026-10-09_kor_test_3"}
MODELLER = {
    "C8801":  ("modeller/C8801.json",  "deneme/2026-10-10_c8801/cizimler/C8801_A",  "deneme/2026-10-10_c8801/sonuc/C8801_yukleme.json",  "panel", None),
    "C8801K": ("modeller/C8801K.json", "deneme/2026-10-10_c8801/cizimler/C8801K_A", "deneme/2026-10-10_c8801/sonuc/C8801K_yukleme.json", "panel", None),
    "C8801L": ("modeller/C8801L.json", "deneme/2026-10-10_c8801/cizimler/C8801L_A", "deneme/2026-10-10_c8801/sonuc/C8801L_yukleme.json", "panel", None),
    "KT01_A": ("modeller/KT01.json", f"{KT['KT01']}/cizimler/KT01_A", (f"{KT['KT01']}/sonuc/KT01_kararlar_A_yukleme.json",), "panel", f"{KT['KT01']}/sonuc/KT01_pafta_sayimi.json"),
    "KT01_B": ("modeller/KT01.json", f"{KT['KT01']}/cizimler/KT01_B", (f"{KT['KT01']}/sonuc/KT01_kararlar_B_yukleme.json",), None, f"{KT['KT01']}/sonuc/KT01_pafta_sayimi.json"),
    "KT02_A": ("modeller/KT02.json", f"{KT['KT02']}/cizimler/KT02_A", (f"{KT['KT02']}/sonuc/KT02_cevaplar_A_yukleme.json",), "panel", f"{KT['KT02']}/sonuc/KT02_pafta_sayimi.json"),
    "KT02_B": ("modeller/KT02.json", f"{KT['KT02']}/cizimler/KT02_B", (f"{KT['KT02']}/sonuc/KT02_cevaplar_B_yukleme.json",), None, f"{KT['KT02']}/sonuc/KT02_pafta_sayimi.json"),
    "KT03_A": ("modeller/KT03.json", f"{KT['KT03']}/cizimler/KT03_A", (f"{KT['KT03']}/sonuc/KT03_cevaplar_A_yukleme.json",), "panel", f"{KT['KT03']}/sonuc/KT03_pafta_sayimi.json"),
    "KT03_B": ("modeller/KT03.json", f"{KT['KT03']}/cizimler/KT03_B", (f"{KT['KT03']}/sonuc/KT03_cevaplar_B_yukleme.json",), "omega_asik", f"{KT['KT03']}/sonuc/KT03_pafta_sayimi.json"),
    "C8201":  ("modeller/C8201.json", None, None, "panel", None),                   # taban: --taban klasörü (Adım 2)
}
PNGLER = ("{kod}_plan.png", "{kod}_gorunusler.png", "{kod}_pafta.png")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cikti", required=True, type=Path); ap.add_argument("--taban", type=Path, default=None); ap.add_argument("--etiket", default="")
    a = ap.parse_args()
    from motor.genel import iz as IZ, uret as U
    import matplotlib, shapely, ifcopenshell, numpy
    surum = f"{sys.version.split()[0]} shapely {shapely.__version__} ifcopenshell {ifcopenshell.version} matplotlib {matplotlib.__version__} numpy {numpy.__version__}"
    a.cikti.mkdir(parents=True, exist_ok=True)
    satirlar, fark = [], 0
    t0 = time.time()
    for ad, (tanim, ciz_dir, liste_yolu, yontem, sayim) in MODELLER.items():
        hedef = a.cikti / ad
        m = U.uret(KOK / tanim, hedef, is_emri_no=None, revizyon=1, yontem=yontem, perspektif=False, bayi=True,
                   elektrik_sayimi=(KOK / sayim) if sayim else None)
        v = json.loads((hedef / "validation.json").read_text(encoding="utf-8"))
        kod = U.kod_govde(json.loads((KOK / tanim).read_text(encoding="utf-8")))
        ref = (KOK / ciz_dir) if ciz_dir else (a.taban if a.taban else None)
        for d in PNGLER:
            d = d.format(kod=kod)
            if ref is None or not (ref / d).exists():
                satirlar.append((ad, d, "referans yok")); continue
            ayni = sha(hedef / d) == sha(ref / d); fark += 0 if ayni else 1
            satirlar.append((ad, d, "AYNI" if ayni else "FARKLI"))
        if ref is not None and (ref / f"{kod}.ifc").exists():
            ayni = IZ.ifc_izi(hedef / f"{kod}.ifc") == IZ.ifc_izi(ref / f"{kod}.ifc"); fark += 0 if ayni else 1
            satirlar.append((ad, f"{kod}.ifc", "İÇERİK AYNI" if ayni else "FARKLI"))
        if liste_yolu:
            adaylar = (liste_yolu,) if isinstance(liste_yolu, str) else liste_yolu
            uretilen = sha(hedef / f"{kod}_yukleme.json")
            esi = next((y for y in adaylar if (KOK / y).exists() and sha(KOK / y) == uretilen), None)
            fark += 0 if esi else 1
            sonuc = "FARKLI" if not esi else ("AYNI" if isinstance(liste_yolu, str) else f"AYNI (= {esi.rsplit('/', 1)[-1]})")
            satirlar.append((ad, f"{kod}_yukleme.json", sonuc))
        sema = v["ifc"].get("sema_hatasi")
        satirlar.append((ad, "validation", f"passed={m['passed']} şema hatası {sema} liste {v['liste_satir']} satır pdf={'var' if m['pdf'] else 'yok'} bayi={'var' if m['plan_bayi'] else 'yok'}"))
        if not m["passed"] or sema:
            fark += 1
    say = {}
    for _, _, d in satirlar:
        say[d.split(" ")[0]] = say.get(d.split(" ")[0], 0) + 1
    md = [f"# Paket kıyası · {a.etiket} · {surum} · {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} · {round(time.time() - t0)} s", "",
          "Özet: " + ", ".join(f"{k} {n}" for k, n in sorted(say.items())), "", "| model | dosya | sonuç |", "|---|---|---|"]
    md += [f"| {m} | {d} | {s} |" for m, d, s in satirlar]
    (a.cikti / "paket_kiyas.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (a.cikti / "paket_kiyas.json").write_text(json.dumps({"etiket": a.etiket, "surum": surum, "satirlar": satirlar, "fark": fark}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md))
    return 1 if fark else 0


if __name__ == "__main__":
    sys.exit(main())
