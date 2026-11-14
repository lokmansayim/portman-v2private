"""İE-38 (D-87) · Aday havuzu hakemi: prefabrik evin İş Emri'si gerçek projesinin proje kartıyla aynı mı.

Lokman, 13 Kasım 2026 21:41 UTC: AIPrefabrik ve AICelik'teki bütün tek katlı projeler bayiye giden aday havuzuna. Bayinin göreceği yanlış
ölçü gerçek hatadır: bir ev havuza ancak Motor'un kurduğu plan, montaj paftasından okunan proje kartıyla (`testler/havuz/proje_kartlari.json`)
aşağıdaki kalemlerde aynıysa girer. Hakem yalnız okur ve bulgu yazar; düzeltme yapmaz (öneren değişir, hakem değişmez).

Kalemler (her biri paftanın 1. sayfasındaki değerle):
- dış ölçü: gövde (W × H) ya da açık mahallerle birlikte (taşan teras ve veranda) en çok 5 cm fark (pafta okuması ve 125,5 köşe kuralı);
- brüt oturum: Motor'un brüt alanı (D-49, `prefabrik_liste.bina_brut_cm2`) + kubbelerin dış yüzden çıkıntısı, en çok 0,5 m² fark;
- oda programı: kartın oda sayısı (yoksa kartın yatak odası sayısı + 1) Motor'un yatak odası sayısıyla;
- pencereler: ölçü ölçü aynı adet (kubbenin pencereleri kubbe panolarından);
- dış kapı, iç kapı ve veranda (açık mahal) sayısı aynı; kat 1.

    python3 araclar/havuz_hakemi.py testler/kor/projeler/AP14/is_emri.json --kart AP-14

Çelik (AICelik): proje kartı yok. Hedef değerler İE-16'da müşteri onay paftasından okunan tanımın adından (`testler/havuz/
celik_kartlari.json`: antet m², oda programı, veranda): genel motor çizer ve doğrular, brüt oturum antet m²'sinden en çok 0,5 m² sapar,
oda programı antette yazılı ve aynı, antet verandalıysa Motor'da da veranda var, tek kat; aynı proje havuzda başka kodla varsa
(ÇP-14 = KT-04) girmez. Veranda bir oda gibi sayılır; verandasız proje de girer (Lokman, 14 Kasım 2026 07:34 UTC; D-87 › Veranda).

    python3 araclar/havuz_hakemi.py testler/celik/projeler/CP18/CP18.json --kart ÇP-18
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
KARTLAR = KOK / "testler" / "havuz" / "proje_kartlari.json"
CELIK_KARTLARI = KOK / "testler" / "havuz" / "celik_kartlari.json"
TOL_OLCU_CM = 5.0
TOL_BRUT_M2 = 0.5


def kartlar() -> dict:
    return json.loads(KARTLAR.read_text(encoding="utf-8"))["evler"]


def _olcu(s) -> str:
    n = re.findall(r"\d+(?:[.,]\d+)?", str(s))
    return f"{int(float(n[0].replace(',', '.')))}x{int(float(n[1].replace(',', '.')))}" if len(n) >= 2 else str(s)


def _alan(poly) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2


def olcum(ie: dict) -> dict:
    """İş Emri → Motor'un planından hakemin okuduğu sayılar (LLM yok; Motor `geometry.kur`)."""
    from motor import geometry as G, prefabrik_liste as PL
    from shapely.geometry import box
    from shapely.ops import unary_union
    plan = G.kur(json.loads(json.dumps(ie)))
    kubbe = sum(_alan(list(k["dis"])) for k in plan.kubbeler) / 1e4
    acik = [m.poly for m in plan.mahaller.values() if m.acik]
    u = unary_union([box(0, 0, plan.W, plan.H)] + acik)
    x0, y0, x1, y1 = u.bounds
    pen = Counter(_olcu(a["olcu"]) for a in ie.get("acikliklar") or [] if a.get("tur") == "pencere")
    for k in plan.kubbeler:
        pen.update(_olcu(p["pencere"]) for p in k.get("panolar") or [] if p.get("pencere"))
    return {"dis_olcu_cm": [round(plan.W, 2), round(plan.H, 2)], "acikla_olcu_cm": [round(x1 - x0, 2), round(y1 - y0, 2)],
            "brut_m2": round(PL.bina_brut_cm2(plan) / 1e4, 2), "kubbe_m2": round(kubbe, 2),
            "yatak_odasi": sum(1 for m in ie.get("mahaller") or [] if m.get("tur") == "yatak_odasi"),
            "pencereler": dict(sorted(pen.items())),
            "dis_kapi": sum(1 for a in ie.get("acikliklar") or [] if a.get("tur") == "dis_kapi"),
            "ic_kapi": sum(1 for a in ie.get("acikliklar") or [] if a.get("tur") == "ic_kapi"),
            "veranda": len(acik), "kat": int((ie.get("yapi") or {}).get("kat_sayisi") or 1)}


def _yakin(a, b) -> float:
    return min(max(abs(a[0] - b[0]), abs(a[1] - b[1])), max(abs(a[0] - b[1]), abs(a[1] - b[0])))


def denetle(ie: dict, kart: dict) -> tuple[list[str], dict]:
    """(bulgular, ölçüm). Bulgu yoksa ev havuza girebilir."""
    o = olcum(ie)
    b: list[str] = []
    ko = kart["dis_olcu_cm"]
    fark = min(_yakin(o["dis_olcu_cm"], ko), _yakin(o["acikla_olcu_cm"], ko))
    if fark > TOL_OLCU_CM:
        b.append(f"dış ölçü: Motor {o['dis_olcu_cm'][0]:g} × {o['dis_olcu_cm'][1]:g} cm (açık mahallerle {o['acikla_olcu_cm'][0]:g} × "
                 f"{o['acikla_olcu_cm'][1]:g}), pafta {ko[0]:g} × {ko[1]:g} cm; fark {fark:.2f} cm > {TOL_OLCU_CM:g}")
    brut = o["brut_m2"] + o["kubbe_m2"]
    if kart.get("brut_oturum_m2") is not None and abs(brut - kart["brut_oturum_m2"]) > TOL_BRUT_M2:
        b.append(f"brüt oturum: Motor {brut:.2f} m² (kubbe {o['kubbe_m2']:.2f} dahil), pafta {kart['brut_oturum_m2']:g} m²; "
                 f"fark {brut - kart['brut_oturum_m2']:+.2f} > {TOL_BRUT_M2:g}")
    oda = str(kart.get("oda_sayisi") or "").strip()
    m = re.fullmatch(r"(\d+)\+1", oda)
    beklenen_yatak = int(m.group(1)) if m else (kart.get("yatak_odasi") if not oda else None)
    if beklenen_yatak is None or beklenen_yatak != o["yatak_odasi"]:
        b.append(f"oda programı: Motor {o['yatak_odasi']}+1, pafta \"{oda or '?'}\" (yatak odası {kart.get('yatak_odasi')})")
    kp = Counter()
    for s, n in (kart.get("acikliklar") or {}).items():
        kp[_olcu(s)] += int(n)
    if Counter(o["pencereler"]) != kp:
        eksik, fazla = kp - Counter(o["pencereler"]), Counter(o["pencereler"]) - kp
        b.append(f"pencereler: Motor'da eksik {dict(eksik) or '-'}, fazla {dict(fazla) or '-'}")
    for alan, ka in (("dis_kapi", "dis_kapi_adedi"), ("ic_kapi", "ic_kapi_adedi"), ("veranda", "veranda_adedi")):
        if kart.get(ka) is not None and int(kart[ka]) != o[alan]:
            b.append(f"{alan.replace('_', ' ')}: Motor {o[alan]}, pafta {kart[ka]}")
    if int(kart.get("kat_adedi") or 1) != 1 or o["kat"] != 1:
        b.append("kat: havuz yalnız tek kat")
    return b, o


def celik_kartlari() -> dict:
    return json.loads(CELIK_KARTLARI.read_text(encoding="utf-8"))["evler"]


def celik_olcum(tanim_yolu: Path) -> dict:
    """Yapı Tanımı → genel motorun çizdiği ve doğruladığı plandan sayılar (perspektifsiz; LLM yok)."""
    import tempfile
    from motor.genel import uret as U
    from motor.genel.bayi_gorseli import oda_programi
    t = json.loads(Path(tanim_yolu).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        m = U.uret(Path(tanim_yolu), Path(tmp), is_emri_no=None, revizyon=None, set_yolu=None, yontem="panel", perspektif=False, bayi=True,
                   kaynak="havuz hakemi")
        v = json.loads((Path(tmp) / "validation.json").read_text(encoding="utf-8"))
        g = json.loads((Path(tmp) / f"{U.kod_govde(t)}_girdi.json").read_text(encoding="utf-8"))
    vm = g.get("veranda_m2") or 0
    veranda = float(vm.get("net") or vm.get("brut") or 0) if isinstance(vm, dict) else float(vm)
    return {"gecti": bool(m.get("passed")), "hatalar": v.get("errors") or [], "bayi_gorseli": bool(m.get("bayi_gorsel")),
            "oturum_m2": round(float(g.get("oturum_m2") or g["bina_m2"]), 2), "veranda_m2": round(veranda, 2), "oda_programi": oda_programi(t),
            "kat": 1 if str(t.get("kat", "zemin")) in ("zemin", "1") else 2}


def celik_denetle(tanim_yolu: Path, kart: dict) -> tuple[list[str], dict]:
    """(bulgular, ölçüm). Bulgu yoksa çelik proje havuza girebilir."""
    o = celik_olcum(tanim_yolu)
    b: list[str] = []
    if kart.get("havuzda"):
        b.append(f"havuzda: aynı proje {kart['havuzda']} koduyla havuzda")
    if not o["gecti"] or not o["bayi_gorseli"]:
        b.append(f"motor: genel motor doğrulaması geçmedi ya da bayi görseli yok ({o['hatalar']})")
    if kart.get("antet_m2") is None or abs(o["oturum_m2"] - kart["antet_m2"]) > TOL_BRUT_M2:
        b.append(f"brüt oturum: Motor {o['oturum_m2']:.2f} m², antet {kart.get('antet_m2')} m²; en çok {TOL_BRUT_M2:g}")
    if not kart.get("oda_programi"):
        b.append(f"oda programı: antette yok (Motor {o['oda_programi']}); doğrulanamadı")
    elif kart["oda_programi"] != o["oda_programi"]:
        b.append(f"oda programı: Motor {o['oda_programi']}, antet {kart['oda_programi']}")
    if kart.get("veranda") and o["veranda_m2"] <= 0:                           # veranda bir oda gibi: antette varsa Motor'da da olmalı;
        b.append("veranda: antet verandalı, Motor'da veranda yok")               # verandasız proje de girer (Lokman, 14 Kasım 2026; D-87)
    if int(kart.get("kat_adedi") or 1) != 1 or o["kat"] != 1:
        b.append("kat: havuz yalnız tek kat")
    return b, o


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("is_emri", help="prefabrik İş Emri ya da çelik Yapı Tanımı"); ap.add_argument("--kart", required=True, help="proje kodu (AP-14 ya da ÇP-18)")
    a = ap.parse_args(argv)
    if a.kart.upper().startswith(("ÇP", "CP")):
        kod = "ÇP-" + re.sub(r"\D", "", a.kart)[-2:].zfill(2)
        kart = celik_kartlari().get(kod)
        if kart is None:
            print(f"DUR: {kod} için çelik hedef değeri yok ({CELIK_KARTLARI.relative_to(KOK)})"); return 2
        bulgular, o = celik_denetle(Path(a.is_emri), kart)
        print(json.dumps(o, ensure_ascii=False))
        print("GEÇTİ: antetle aynı" if not bulgular else "KALDI:\n- " + "\n- ".join(bulgular))
        return 0 if not bulgular else 1
    kart = kartlar().get(a.kart.upper())
    if kart is None:
        print(f"DUR: {a.kart} için proje kartı yok ({KARTLAR.relative_to(KOK)})"); return 2
    bulgular, o = denetle(json.loads(Path(a.is_emri).read_text(encoding="utf-8")), kart)
    print(json.dumps(o, ensure_ascii=False))
    print("GEÇTİ: proje kartıyla aynı" if not bulgular else "KALDI:\n- " + "\n- ".join(bulgular))
    return 0 if not bulgular else 1


if __name__ == "__main__":
    sys.exit(main())
