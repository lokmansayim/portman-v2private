"""PK-02 · Motor planı ↔ montaj paftası (kör test adım 2; gerçek liste açılmadan). Pano, köşe, açıklık ve kapı kanadı eşleşmesi.

    python3 deneme/2026-10-13_pk_02/pafta_kiyas.py      → stdout + pafta_kiyas.json

Pano eşleşmesi dış kutu üzerinden, 0,6 cm toleransla (PDF adımı ≈ 0,1 pt; ölçek 1,84 pt/cm). LLM yok, ağ yok.
"""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(KOK))

from motor import geometry as G  # noqa: E402

TOL = 0.6


def _ayni(a, b, tol=TOL):
    return all(abs(u - v) <= tol for u, v in zip(a, b))


def main() -> int:
    ie = json.loads((BURASI / "tanim" / "PK02.json").read_text(encoding="utf-8"))
    pafta = json.loads((BURASI / "pafta_montaj.json").read_text(encoding="utf-8"))["montaj_plani"]
    plan = G.kur(copy.deepcopy(ie))
    motor = [(d, p, [round(v, 2) for v in p.rect()]) for d in plan.duvarlar for p in d.panolar]
    kalan = list(motor)
    eslesen, yalniz_pafta = [], []
    for pp in pafta["panolar"]:
        bul = next((m for m in kalan if _ayni(m[2], pp["rect"])), None)
        if bul:
            kalan.remove(bul); eslesen.append(pp)
        else:
            yalniz_pafta.append(pp)
    yalniz_motor = [{"duvar": f"{d.tur} {d.yon}={d.c:g}", "rect": r, "boy": p.boy} for d, p, r in kalan]
    kose_m = [list(k.rect) for k in plan.koseler]
    kose_ok = sum(any(_ayni(k, q["rect"]) for q in pafta["koseler"]) for k in kose_m)
    siparis = lambda cm: int((cm * 10 - 2.5) // 5 * 5)                # PK-01 dersi 2; liste üreteci sürüm 2 ile aynı kural
    kal = lambda t: "100" if t > 8 else "60"
    tam = lambda cm: round(cm * 4) / 4                                 # PDF ölçüm gürültüsü (±0,1 cm): 0,25 cm'ye yuvarlanır (62,73 → 62,75)
    boy_p = Counter(f"{kal(p['kalinlik'])} × {siparis(tam(p['boy']))}" for p in pafta["panolar"])
    boy_m = Counter(f"{kal(2 * d.h)} × {siparis(p.boy)}" for d, p, _ in motor)
    sonuc = {"pano": {"pafta": len(pafta["panolar"]), "motor": len(motor), "eslesen": len(eslesen)},
             "yalniz_pafta": yalniz_pafta, "yalniz_motor": yalniz_motor,
             "kose": {"pafta": len(pafta["koseler"]), "motor": len(kose_m), "eslesen": kose_ok},
             "siparis_boylari": {"not": "açıklıklı panolar dahil; kalınlık mm × sipariş boyu mm", "pafta": dict(sorted(boy_p.items())),
                                 "motor": dict(sorted(boy_m.items()))}}
    (BURASI / "pafta_kiyas.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"pano: pafta {len(pafta['panolar'])}, Motor {len(motor)}, eşleşen {len(eslesen)}; köşe {kose_ok}/{len(kose_m)}")
    for p in yalniz_pafta:
        print("  yalnız paftada:", p["tur"], p["rect"], p["boy"])
    for p in yalniz_motor:
        print("  yalnız Motor'da:", p["duvar"], p["rect"], p["boy"])
    for anahtar in sorted(set(boy_p) | set(boy_m)):
        if boy_p[anahtar] != boy_m[anahtar]:
            print(f"  sipariş boyu {anahtar}: pafta {boy_p[anahtar]}, Motor {boy_m[anahtar]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
