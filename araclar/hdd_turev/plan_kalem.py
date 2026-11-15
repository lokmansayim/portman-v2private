"""İE-43 PR-3 · Plandan çıkan liste kalemleri: arşivin gerçek listesi (2019–2020 TEKLİF sayfası) ↔ Motor'un yükleme listesi.

Kalemler pano dizilimiyle doğrudan bağlıdır: dolu pano (100'lük, 60'lık), vasistaslı pano, pencere üst ve alt paneli, kapılı pano, köşe
direği, H (dış ve iç pano eki), 3'lü H, 60'lık çektirme U'su, iç ve dış kapı, pencere (ölçü ölçü). Kalem başına toplam adet yazılır.
Eski listeler dolu panoyu çoğunlukla tam boy (125 cm) yazar, kesimi sahada yapar; Motor kesilmiş parçayı sayar. Bu yüzden dolu panoda
iki tarafın toplam eni de yazılır ve tam boy eşdeğeri (toplam en ÷ 125, yukarı yuvarlanır) iki tarafta aynıysa kalem aynı sayılır. Bu bir
gözlemdir, kural değildir. Listede pencere ölçüsü yazılmamışsa pencereler yalnız toplam adetle kıyaslanır.
Gerçek listenin eski adları kör testin sözlüğünde yok; eşleme burada kalem kalem düzenli ifadeyle yapılır. Karar vermez, farkı yazar.

    python3 araclar/hdd_turev/plan_kalem.py <listeler.json> <KOD>=<İş Emri.json> [...] [--json <çıktı>]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))


def buyuk(s) -> str:
    return (s or "").upper().replace("İ", "I").replace("Ü", "U").replace("Ö", "O").replace("Ç", "C").replace("Ş", "S").replace("Ğ", "G")


def sade(s) -> str:
    return re.sub(r"\s", "", str(s or "")).replace("×", "*").replace("X", "*").replace("x", "*")


def _en_mm(olcu) -> float | None:
    """'100 × 1250 × 2500' ya da '100*1250*2500' → 1250 (pano eni, mm)."""
    n = re.findall(r"\d+(?:[.,]\d+)?", str(olcu or ""))
    return float(n[1].replace(",", ".")) if len(n) >= 3 else None


# (kalem, gerçek(ad, boyut) → bool, Motor(kalem, ölçü) → bool); adlar `buyuk` ile
KALEMLER = [
    ("100'lük dolu pano", lambda a, o: re.search(r"100.?LUK YAPISTIRMA DOLU PANO", a), lambda a, o: re.search(r"100.?LUK YAPISTIRMA DOLU PANO$", a)),
    ("60'lık dolu pano", lambda a, o: re.search(r"60.?LIK YAPISTIRMA DOLU PANO", a), lambda a, o: re.search(r"60.?LIK YAPISTIRMA DOLU PANO$", a)),
    ("Vasistaslı pano", lambda a, o: "VASISTAS" in a and ("PANEL" in a or "PANO" in a), lambda a, o: "VASISTASLI PANO" in a),
    ("Pencere üst panel", lambda a, o: "PENCERE UST PANEL" in a, lambda a, o: "PENCERE UST PANEL" in a),
    ("Pencere alt panel", lambda a, o: "PENCERE ALT PANEL" in a, lambda a, o: "PENCERE ALT PANEL" in a),
    ("Kapılı pano (iç)", lambda a, o: re.search(r"60.?LIK KARKASLI KAPILI", a), lambda a, o: re.search(r"60.?LIK KARKASLI \+ KASALI", a)),
    ("Kapılı pano (dış)", lambda a, o: "DIS KAPILI" in a, lambda a, o: "KARKASLI CELIK KAPI PANOSU" in a),
    ("Köşe direği 100", lambda a, o: "KOSE DIREG" in a and sade(o).startswith("100"), lambda a, o: "KOSE DIREG" in a and sade(o).startswith("100")),
    ("Köşe direği 60", lambda a, o: "KOSE DIREG" in a and sade(o).startswith("60"), lambda a, o: "KOSE DIREG" in a and sade(o).startswith("60")),
    ("H 100 (dış pano eki)", lambda a, o: re.match(r"H\s*\(", a) and sade(o).startswith("100"), lambda a, o: a.startswith("H 100")),
    ("H 60 (iç pano eki)", lambda a, o: re.match(r"H\s*\(", a) and sade(o).startswith("60"), lambda a, o: a.startswith("H STANDART 60")),
    ("3'lü H 100", lambda a, o: re.match(r"3\s*.?LU\s*H", a) and sade(o).startswith("100"), lambda a, o: a.startswith("3'LU H 100")),
    ("3'lü H 60", lambda a, o: re.match(r"3\s*.?LU\s*H", a) and sade(o).startswith("60"), lambda a, o: a.startswith("3'LU H STANDART 60")),
    ("Çektirme U'su 60", lambda a, o: re.match(r"CEKTIRME U", a) and sade(o).startswith("60"), lambda a, o: a.startswith("CEKTIRME U'SU 60")),
    ("İç kapı", lambda a, o: "AMERIKAN KAPI" in a, lambda a, o: a.startswith("AMERIKAN KAPI")),
    ("Dış kapı", lambda a, o: re.match(r"CELIK KAPI", a), lambda a, o: "PREFABRIK CELIK KAPI" in a),
]
PENCERE_GERCEK = re.compile(r"PVC (PENCERE|VASISTAS|SURGU)(?!.*KOL)|SURGULU")
PENCERE_MOTOR = re.compile(r"PVC (PENCERE|VASISTAS)|SURGULU")


def _pencere_olcusu(o) -> str:
    m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", str(o or ""))
    return f"{m.group(1)}/{m.group(2)}" if m else "ölçüsüz"


def motor_listesi(ie: dict) -> list[dict]:
    from motor import prefabrik_liste as PL
    t = {k: v for k, v in ie.items() if not k.startswith("_")}
    t["acikliklar"] = [{k: v for k, v in a.items() if not k.startswith("_")} for a in ie.get("acikliklar") or []]
    return PL.liste(PL.model_motor(t), PL.kurallari_oku(), None)["satirlar"]


def kiyasla(gercek: list[dict], motor: list[dict]) -> list[dict]:
    """Kalem kalem toplam adet; dolu panoda Motor'un tam boy eşdeğeri."""
    satir = []
    for ad, fg, fm in KALEMLER:
        g = [(x["boyut"], x["adet"]) for x in gercek if isinstance(x.get("adet"), (int, float)) and x["adet"] > 0
             and fg(buyuk(x["malzeme"]), x["boyut"])]
        m = [(x["olcu"], x["adet"]) for x in motor if fm(buyuk(x["kalem"]), x["olcu"])]
        s = {"kalem": ad, "gercek": sum(n for _, n in g), "motor": sum(n for _, n in m), "gercek_satir": g, "motor_satir": m}
        if "dolu pano" in ad:
            for taraf, liste in (("gercek", g), ("motor", m)):
                # 1250 mm'den geniş dolu pano yazımı (ör. "100*6325*2500") toplam ene girmez; liste düzeltilmez, ayrıca yazılır
                gecersiz = [(o, n) for o, n in liste if (_en_mm(o) or 0) > 1260]
                if gecersiz:
                    s[f"{taraf}_gecersiz_en"] = gecersiz
                toplam = sum((_en_mm(o) or 0) * n for o, n in liste if (o, n) not in gecersiz)
                s[f"{taraf}_en_m"] = round(toplam / 1000, 2)
                s[f"{taraf}_tam_boy"] = math.ceil(toplam / 1250 - 1e-6) if toplam else 0
        satir.append(s)
    gp, mp = {}, {}
    for x in gercek:
        if isinstance(x.get("adet"), (int, float)) and x["adet"] > 0 and PENCERE_GERCEK.search(buyuk(x["malzeme"])):
            gp[_pencere_olcusu(x["boyut"])] = gp.get(_pencere_olcusu(x["boyut"]), 0) + x["adet"]
    for x in motor:
        if PENCERE_MOTOR.match(buyuk(x["kalem"])):
            mp[_pencere_olcusu(x["olcu"])] = mp.get(_pencere_olcusu(x["olcu"]), 0) + x["adet"]
    if "ölçüsüz" in gp:                             # listede pencere ölçüsü yazılmamış: yalnız toplam
        satir.append({"kalem": "Pencere (listede ölçü yok, toplam)", "gercek": sum(gp.values()), "motor": sum(mp.values())})
    else:
        for o in sorted(set(gp) | set(mp)):
            satir.append({"kalem": f"Pencere {o}", "gercek": gp.get(o, 0), "motor": mp.get(o, 0)})
    return satir


def ayni_mi(s: dict) -> bool:
    return s["gercek"] == s["motor"] or ("gercek_tam_boy" in s and s["gercek_tam_boy"] == s["motor_tam_boy"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("listeler"); ap.add_argument("evler", nargs="+"); ap.add_argument("--json")
    a = ap.parse_args(argv)
    L = json.loads(Path(a.listeler).read_text(encoding="utf-8"))
    cikti = {}
    for e in a.evler:
        kod, yol = e.split("=", 1)
        satir = kiyasla(L[kod]["satirlar"], motor_listesi(json.loads(Path(yol).read_text(encoding="utf-8"))))
        cikti[kod] = satir
        print(f"== {kod}: {sum(ayni_mi(s) for s in satir)}/{len(satir)} kalem aynı")
        for s in satir:
            if not ayni_mi(s):
                print(f"   {s['kalem']}: gerçek {s['gercek']} | Motor {s['motor']}"
                      + (f" (toplam en {s['gercek_en_m']:g} m | {s['motor_en_m']:g} m)" if "gercek_en_m" in s else ""))
    if a.json:
        Path(a.json).write_text(json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
