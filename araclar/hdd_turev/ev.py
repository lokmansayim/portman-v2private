"""İE-43 PR-3 · Arşiv evinin montaj paftasından İş Emri, Motor çizimi ve yan yana kıyas görseli (tek komut).

Adımlar (her biri ayrı araç, sırayla):
1. `plan_geometri.py`: paftanın çizgilerinden plan geometrisi ve İş Emri taslağı (pafta düzeltilmez; uyarılar ve varsayımlar yazılır);
2. `uydur.py`: Motor'un pano dizilimini paftanınkine yaklaştıran dayanaklar (`dizilim.dis_pano_dayanagi`); kalan farklar kıyasta;
3. Motor (`motor.geometry.kur` + `motor.dxf_out.uret`): main'deki kodla ön onay çizimi (DXF, PDF) ve doğrulama;
4. `yan_yana.py`: solda paftanın kendisi, sağda Motor'un pano dizilimi; aynı, kaymış ve paftada başka yerde olan panolar renkli.

Çıktılar `<çıktı>/` altında: `ie.json` (okunan), `ie_uydu.json` (dayanaklı İş Emri), `geo.json`, `okuma.txt`, `uydurma.txt`, `motor/`,
`yan_yana.png`. Pafta ve onlardan üretilenler depoya girmez (İE-43); çıktı klasörü depo dışında seçilir.

    python3 araclar/hdd_turev/ev.py <dxf|dxf.gz> <kart.json> <plan sırası> <HD kodu> <çıktı> [--baslik "37 m²"]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BURA = Path(__file__).resolve().parent
KOK = BURA.parents[1]
sys.path.insert(0, str(KOK))


def temiz(ie: dict) -> dict:
    """İş Emri'nden okuyucunun iz anahtarlarını (`_` ile başlayan) atar: Motor'a giden İş Emri."""
    t = {k: v for k, v in ie.items() if not k.startswith("_")}
    t["acikliklar"] = [{k: v for k, v in a.items() if not k.startswith("_")} for a in ie.get("acikliklar") or []]
    return t


def motor_kos(ie: dict, cikti: Path) -> dict:
    """main'deki Motor: plan kurulur, ön onay çizimi (DXF, PDF) yazılır. Dönüş: ölçü, uyarılar ve doğrulama."""
    from motor import dxf_out, geometry as G
    cikti.mkdir(parents=True, exist_ok=True)
    t = temiz(ie)
    (cikti / "is_emri.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    plan = G.kur(json.loads(json.dumps(t)))
    m = dxf_out.uret(t, cikti, pdf_hatada=True)
    return {"W": plan.W, "H": plan.H, "uyarilar": list(plan.uyarilar), "dogrulama": m.get("validation_passed"), "pdf": m.get("pdf")}


def _kos(arglar: list, log: Path) -> int:
    with open(log, "w", encoding="utf-8") as f:
        return subprocess.run([sys.executable, *map(str, arglar)], stdout=f, stderr=subprocess.STDOUT, cwd=KOK).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dxf"); ap.add_argument("kart"); ap.add_argument("plan", type=int); ap.add_argument("kod"); ap.add_argument("cikti")
    ap.add_argument("--baslik", default="")
    a = ap.parse_args(argv)
    c = Path(a.cikti); c.mkdir(parents=True, exist_ok=True)
    if _kos([BURA / "plan_geometri.py", a.dxf, a.kart, a.plan, c / "ie.json", "--kod", a.kod, "--geo", c / "geo.json"], c / "okuma.txt"):
        print("okuma hatası:", (c / "okuma.txt").read_text(encoding="utf-8")[-600:]); return 1
    if _kos([BURA / "uydur.py", c / "geo.json", c / "ie.json", c / "ie_uydu.json"], c / "uydurma.txt"):
        print("uydurma hatası:", (c / "uydurma.txt").read_text(encoding="utf-8")[-600:]); return 1
    ie = json.loads((c / "ie_uydu.json").read_text(encoding="utf-8"))
    m = motor_kos(ie, c / "motor")
    print(f"Motor {m['W']:g} × {m['H']:g} cm, doğrulama {'geçti' if m['dogrulama'] else 'KALDI'}")
    for u in m["uyarilar"]:
        print("  uyarı:", u)
    if _kos([BURA / "yan_yana.py", a.dxf, a.kart, a.plan, c / "geo.json", c / "ie_uydu.json", c / "yan_yana.png", a.baslik], c / "yan_yana.txt"):
        print("görsel hatası:", (c / "yan_yana.txt").read_text(encoding="utf-8")[-600:]); return 1
    print((c / "yan_yana.txt").read_text(encoding="utf-8").strip().splitlines()[-1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
