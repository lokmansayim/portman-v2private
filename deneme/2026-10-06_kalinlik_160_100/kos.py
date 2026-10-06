"""6 Ekim 2026 denemesi: duvar kalınlığı seçeneğiyle İş Emri → DXF/PDF.

    python deneme/2026-10-06_kalinlik_160_100/kos.py            # sağlama (P6001) + 3+1 el çizimi
    python deneme/2026-10-06_kalinlik_160_100/kos.py --sonuc    # ayrıca kanıtları sonuc/ altına kopyalar

Canlı Motor'a, sunucuya, LLM'e ve WhatsApp'a dokunmaz. Çıktılar `cikti/` altındadır (depoya girmez).
"""
from __future__ import annotations
import json, os, shutil, sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIKTI = BURASI / "cikti"
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(BURASI))
os.environ.setdefault("PORTMAN_REF_DIR", str(KOK / "kanal"))

import yama                                   # noqa: E402

yama.uret(CIKTI)
sys.path.insert(0, str(CIKTI))
from motor import dxf_out as CANLI            # noqa: E402
from motor import geometry as G0              # noqa: E402
from motor_k import dxf_out as DENEME         # noqa: E402
from motor_k import geometry as G             # noqa: E402


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _geometri(mod, is_emri: dict) -> dict:
    plan = mod.kur(json.loads(json.dumps(is_emri)))
    return {"dis": [plan.W, plan.H],
            "panolar": sorted((d.tur, tuple(round(v, 6) for v in p.rect()), p.acilim.tur if p.acilim else "") for d in plan.duvarlar for p in d.panolar),
            "koseler": sorted((k.tur, tuple(round(v, 6) for v in k.rect)) for k in plan.koseler),
            "h": sorted((round(h.x, 6), round(h.y, 6), h.rot) for h in plan.h_baglantilar),
            "alanlar": {ad: round(m.alan_m2, 9) for ad, m in plan.mahaller.items()}}


def saglama() -> bool:
    """Kalınlık alanı verilmeyince deneme kopyası canlı Motor'la aynı sonucu vermeli (P6001 ve iki altın İş Emri)."""
    tamam = True
    for ad in ("P6001_2plus1_6x6.json", "ALTIN_2plus1_6x8.json", "YAN_VERANDALI_2plus1_6x8p5.json"):
        ie = _oku(KOK / "is_emri" / ad)
        a, b = _geometri(G0, ie), _geometri(G, ie)
        m0 = CANLI.uret(json.loads(json.dumps(ie)), CIKTI / "saglama" / "canli" / ad[:-5])
        m1 = DENEME.uret(json.loads(json.dumps(ie)), CIKTI / "saglama" / "deneme" / ad[:-5])
        v0, v1 = _oku(CIKTI / "saglama" / "canli" / ad[:-5] / "validation.json"), _oku(CIKTI / "saglama" / "deneme" / ad[:-5] / "validation.json")
        b0, b1 = _oku(CIKTI / "saglama" / "canli" / ad[:-5] / "bom.json"), _oku(CIKTI / "saglama" / "deneme" / ad[:-5] / "bom.json")
        ayni = (a == b) and (v0 == v1) and (b0 == b1) and m0["validation_passed"] and m1["validation_passed"]
        tamam &= ayni
        print(f"sağlama {ad}: geometri {'AYNI' if a == b else 'FARKLI'} · doğrulama {'AYNI' if v0 == v1 else 'FARKLI'} · BOM {'AYNI' if b0 == b1 else 'FARKLI'}"
              f" · pano {v1['panel_count']} · {v1['outer_cm'][0]:g} × {v1['outer_cm'][1]:g} cm")
    return tamam


def ciz(is_emri_yolu: Path) -> dict:
    ie = _oku(is_emri_yolu)
    hedef = CIKTI / ie["is_emri_no"]
    if hedef.exists():
        shutil.rmtree(hedef)
    m = DENEME.uret(ie, hedef, pdf_hatada=True)
    v = _oku(hedef / "validation.json")
    print(f"\n{ie['is_emri_no']} r{ie['revizyon']:02d}: doğrulama {'GEÇTİ' if m['validation_passed'] else 'GEÇMEDİ'}"
          f" · {v['outer_cm'][0]:g} × {v['outer_cm'][1]:g} cm · pano {v['panel_count']} · köşe {v['corner_count']} · üçlü H {v['h_connectors']}"
          f" · pencere {v['windows']} · kapı {v['doors']}")
    for h in v["errors"]:
        print("  HATA:", h)
    for u in m["warnings"]:
        print("  uyarı:", u)
    kapali = 0.0
    plan = G.kur(_oku(is_emri_yolu))
    for ad, a in v["rooms_m2"].items():
        x0, y0, x1, y1 = plan.mahaller[ad].poly.bounds
        print(f"  {ad:18s} {a:6.2f} m²   net {x1 - x0:7.2f} × {y1 - y0:7.2f} cm")
        kapali += 0.0 if ad == "VERANDA" else a
    print(f"  {'kapalı net toplam':18s} {kapali:6.2f} m²")
    print("  yeni malzeme kodları:", ", ".join(m["yeni_kodlar"]) or "yok")
    return {"manifest": m, "dogrulama": v, "hedef": hedef}


if __name__ == "__main__":
    ok = saglama()
    print("SAĞLAMA:", "GEÇTİ" if ok else "GEÇMEDİ")
    s = ciz(BURASI / "is_emri_3arti1_9x10.json")
    if "--sonuc" in sys.argv and ok and s["manifest"]["validation_passed"]:
        son = BURASI / "sonuc"; son.mkdir(exist_ok=True)
        for f in sorted(s["hedef"].iterdir()):
            if f.name != "is_emri.json":
                shutil.copy2(f, son / f.name)
        shutil.copy2(CIKTI / "motor_k.diff", son / "motor_k.diff")
        print("kanıtlar:", son)
    sys.exit(0 if ok and s["manifest"]["validation_passed"] else 1)
