#!/usr/bin/env python3
"""PORTMAN · genel motor denemesi (İE-08 GM2): sürümün venv'i Ç8801'in planını ana koddaki paketle (`motor.genel`) çizebiliyor mu ve
çıktı altın değerle aynı mı? `vps/guncelle.sh [3c]` adımında AYRI SÜREÇTE ve timeout ile çağrılır; sonucu ne olursa olsun sürüm
etkinleşir (bilgi amaçlı; Lokman karar verir — İE-08 Soru 17). Perspektif burada denenmez (`[3b]` perspektif_dene.py).

Çıktı tek satır: "AYNI (…)", "FARKLI (…)" ya da "ÇİZİLEMEDİ (<neden>)". Çıkış kodu: 0 AYNI, 1 FARKLI, 2 içe aktarılamadı, 3 çizilemedi.
Altın değerler `modeller/altin.json` (sürümle gider; `testler/referans/` sunucuya gitmez): {"C8801": {"plan_png_sha256": …,
"yukleme_json_sha256": …, "ifc_izi": …}}.
    python vps/genel_dene.py [çıktı_dizini]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    hedef = Path(argv[1]) if len(argv) > 1 else Path(tempfile.mkdtemp(prefix="portman_genel_"))
    sys.path.insert(0, str(KOK))
    t0 = time.time()
    try:
        from motor.genel import uret as U, iz as IZ
    except Exception as e:
        print(f"ÇİZİLEMEDİ (motor.genel içe aktarılamadı: {type(e).__name__}: {str(e)[:120]})"); return 2
    tanim = KOK / "modeller" / "C8801.json"; altin_yolu = KOK / "modeller" / "altin.json"
    if not tanim.exists():
        print("ÇİZİLEMEDİ (modeller/C8801.json yok)"); return 3
    try:
        m = U.uret(tanim, hedef, is_emri_no="DENEME", revizyon=1, yontem="panel", perspektif=False, bayi=True)
    except BaseException as e:   # SystemExit dahil (kural dosyası yok vb.)
        print(f"ÇİZİLEMEDİ ({type(e).__name__}: {str(e)[:140]})"); return 3
    v = json.loads((hedef / "validation.json").read_text(encoding="utf-8"))
    if not m["passed"]:
        print(f"ÇİZİLEMEDİ (doğrulama geçmedi: {'; '.join(v['errors'])[:160]})"); return 3
    plan = hedef / "C8801_plan.png"; liste = hedef / "C8801_yukleme.json"; ifc = hedef / "C8801.ifc"
    sure = round(time.time() - t0, 1)
    if not altin_yolu.exists():
        print(f"AYNI (altın değer yok; çizildi: plan {plan.stat().st_size} bayt, liste {v['liste_satir']} satır, IFC şema hatası {v['ifc'].get('sema_hatasi')}, pdf {'var' if m['pdf'] else 'yok'}; {sure} s)"); return 0
    altin = json.loads(altin_yolu.read_text(encoding="utf-8")).get("C8801", {})
    sonuc = {"plan_png_sha256": sha256(plan), "yukleme_json_sha256": sha256(liste), "ifc_izi": IZ.ifc_izi(ifc)}
    farkli = [k for k, vdeger in altin.items() if k in sonuc and sonuc[k] != vdeger]
    if farkli:
        print(f"FARKLI ({', '.join(farkli)} altın değerden farklı; liste {v['liste_satir']} satır, IFC şema hatası {v['ifc'].get('sema_hatasi')}; {sure} s)"); return 1
    print(f"AYNI (plan PNG, liste JSON ve IFC izi altınla aynı; liste {v['liste_satir']} satır, pdf {'var' if m['pdf'] else 'yok'}; {sure} s)"); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
