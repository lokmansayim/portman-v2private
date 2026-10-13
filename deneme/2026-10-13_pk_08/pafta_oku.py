"""PK-08 pafta okuması (13 Ekim 2026; İE-11 PR-2, kör test adım 1; pafta kipi).

Eren Bey 60 m² (Muhammed Uysal bayisi; Uysallar Yapı mimari planı; Loftev listesi bekleniyor). Montaj paftası DWG (`EROL BEY MONTAJ PAFTASI.dwg`,
okunamıyor); PDF olarak yalnız `Duvar Yerleşim Planı.pdf` (pano yerleşimi), `Omega yerleşim planı.pdf` ve mimari `Kat planı.pdf` /
`Eray Bey 60 M2 Plan.pdf` var. Özellikler satış teklifinden (`Eren Bey 60 m2 Prefabrik Teklif.pdf`, 19 Ağustos 2025; Mac'te okundu, kopyalanmadı;
fiyat ve kişi bilgisi alınmadı): duvar 2500, dış 100 / iç 60, "Cumba Kubbeli Beşik Çatı - Trapez Sac", mineral yün 80 mm, çelik dış kapı,
Amerikan iç kapı, PVC pencere satıcıya ait (bizde), sıva altı elektrik, sıcak / soğuk su tesisatı, dış ve iç boya; vitrifiye alıcıya ait.
Paftada çatı kesiti yok: eğim %33 varsayıldı. Elektrik planı yok.
Çerçeve: cm; x sol dış yüzden (sağ dış yüz 769,8), y yatak 2'nin ön duvar ekseninden (y = 0; arka dış yüz 782,5); açılı cumba y < 0.
Duvar yerleşim planı: turuncu dörtgen = pano (10 dış, 6 iç), sarı = 240'lık pencere panosu (180), camgöbeği = 31'lik parça, kırmızı = köşe (10 × 5),
siyah 15 × 15 = veranda dikmesi; cumbanın açılı panoları (790'lık, 59/170) ve ön panosu (200,7, 105/170) çizgiyle. Ölçek 78,66 pt = 125,5 cm.
Kapılar duvar yerleşim planında yok: mimari kat planındaki kanat ve yaylardan (ölçek 0,5003 pt/cm, x0 220,68, ön yüz y 468,1 pt).

Koşma: python3 -I deneme/2026-10-13_pk_08/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz

BURASI = Path(__file__).resolve().parent
K = BURASI / "kaynak"
S = 78.66 / 125.5
X0_PDF, YB_PDF = 162.0, 541.24
RENK = {(0.949, 0.404, 0.133): "STD", (0.973, 0.843, 0.192): "PENCERE_240", (0.0, 1.0, 1.0): "OZEL", (1.0, 0.0, 0.0): "KOSE", (0.0, 0.0, 0.0): "SIYAH"}
_pk03 = importlib.util.spec_from_file_location("pk03_oku", BURASI.parent / "2026-10-13_pk_03" / "pafta_oku.py")
PK03 = importlib.util.module_from_spec(_pk03); _pk03.loader.exec_module(PK03)        # pencereler() ve ekler() ortak


def b(xp, yp):
    return (xp - X0_PDF) / S, (YB_PDF - yp) / S


def montaj() -> dict:
    pg = fitz.open(K / "PK08_DUVAR_YERLESIM.pdf")[0]
    olculer = sorted({float(w[4]) for w in pg.get_text("words") if re.fullmatch(r"\d+", w[4]) and 20 < float(w[4]) < 260} | {125.5, 240.0})   # 240 = 30 + 180 + 30
    panolar, koseler, dikmeler = [], [], []
    for d in pg.get_drawings():
        r = RENK.get(tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))))
        if not r:
            continue
        for it in d["items"]:
            if it[0] != "qu":
                continue
            q = it[1].rect
            (xa, ya), (xb, yb) = b(q.x0, q.y0), b(q.x1, q.y1)
            x0, x1 = sorted((round(xa, 2), round(xb, 2))); y0, y1 = sorted((round(ya, 2), round(yb, 2)))
            w, h = x1 - x0, y1 - y0
            t, L = min(w, h), max(w, h)
            if r in ("STD", "PENCERE_240", "OZEL") and L > 20 and (abs(t - 10) < 0.5 or abs(t - 6) < 0.5):
                yon = "x" if w > h else "y"
                yakin = min(olculer, key=lambda o: abs(o - L))
                panolar.append({"yon": yon, "c": round((y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2, 2), "a0": x0 if yon == "x" else y0,
                                "a1": x1 if yon == "x" else y1, "boy": yakin if abs(yakin - L) <= 0.6 else round(L * 4) / 4, "boy_cizim": round(L, 2),
                                "t": round(t, 1), "duvar": "dis" if t > 8 else "ic", "tur": r, "rect": [x0, y0, x1, y1]})
            elif r == "KOSE":
                koseler.append({"tur": "dis", "rect": [x0, y0, x1, y1]})
            elif r == "SIYAH" and abs(w - 14.9) < 0.5 and abs(h - 14.9) < 0.5:
                dikmeler.append([x0, y0, x1, y1])
    # cumba (çizgiyle çizilmiş): sol 31'lik parça, açılı 790'lık iki pano (59/170), ön pano 200,7 (105/170). Açılı panolar ekler()'e girmez.
    panolar.append({"yon": "x", "c": 0.0, "a0": 384.8, "a1": 415.7, "boy": 31.0, "boy_cizim": 30.9, "t": 10.0, "duvar": "dis", "tur": "OZEL",
                    "rect": [384.8, -5.2, 415.7, 5.0], "not": "cumbanın sol 31'lik parçası (çizgi)"})
    cumba = [{"yon": "a", "c": None, "a0": None, "a1": None, "boy": 79.0, "boy_cizim": 79.6, "t": 10.0, "duvar": "dis", "tur": "OZEL",
              "aciklik": {"tur": "pencere", "olcu": "59x170", "genislik": 59.0, "kaynak": "etiket 59/170 (açılı pano, 790)"}, "not": "cumba açılı pano (45°)"} for _ in range(2)]
    cumba.append({"yon": "x", "c": -52.35, "a0": 471.9, "a1": 672.6, "boy": 200.75, "boy_cizim": 200.7, "t": 10.0, "duvar": "dis", "tur": "OZEL",
                  "aciklik": {"tur": "pencere", "olcu": "105x170", "genislik": 105.0, "kaynak": "etiket 105/170"}, "not": "cumba ön panosu"})
    etiket = []
    for w in pg.get_text("words"):
        if re.fullmatch(r"\d+/\d+", w[4]):
            x, y = b((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            etiket.append({"metin": w[4], "x": round(x, 1), "y": round(y, 1)})
    return {"panolar": panolar, "cumba_panolari": cumba, "koseler": koseler, "dikmeler": dikmeler, "etiketler": etiket}


# Mimari plandan (kat planı) pencereler ve kapılar: P1 180/180 (240'lık sarı pano), P2 120/100 (sol duvar), P3 120/100 (yatak 1 sağ duvarı).
# Cumba pencereleri paftadan (59/170, 105/170; mimari planda 50/180, 180/180, 50/180). Kapılar mimari plandaki kanat ve yaylardan:
KAPILAR = [  # (tür, menteşe (x, y), açılma yönü, boşluk, kaynak)
    ("dis_kapi", (358.6, 162.4), (0, 1), (258.6, 358.6), "kat planı yay [349,8 334,8 400,1 385,1] (r 100); listede 90 × 200 (L4)"),
    ("ic_kapi", (404.6, 465.0), (0, 1), (404.6, 490.6), "yatak 1: kanat sol pervazdan yatak odasına"),
    ("ic_kapi", (514.95, 440.0), (1, 0), (358.0, 440.0), "WC: kanat üst pervazdan WC'ye"),
    ("ic_kapi", (404.6, 277.25), (0, -1), (404.6, 490.6), "yatak 2: kanat sol pervazdan yatak odasına"),
]
PENCERE_ETIKET = [  # mimari plandan, paftanın çerçevesine çevrilmiş (x, y)
    {"metin": "180/180", "x": 129.8, "y": 150.0},      # paftada "30 180 30": 240'lık sarı pano
    {"metin": "120/100", "x": -10.0, "y": 496.0},       # P2
    {"metin": "120/100", "x": 780.0, "y": 556.0},       # P3
]


def kapilar(M) -> None:
    for tur, (hx, hy), n, (lo, hi), kaynak in KAPILAR:
        dik_x = n[0] == 0
        p = next(p for p in M["panolar"] if p["yon"] == ("x" if dik_x else "y") and abs((hy if dik_x else hx) - p["c"]) <= p["t"] / 2 + 1.5
                 and p["a0"] - 1.5 <= lo and hi <= p["a1"] + 1.5 and not p.get("aciklik"))
        ek = hx if dik_x else hy
        sol = (-n[1], n[0]); orta = (lo + hi) / 2
        h = (ek - orta, 0) if dik_x else (0, ek - orta)
        p["aciklik"] = {"tur": tur, "olcu": "90" if tur == "dis_kapi" else "82", "genislik": 90.0 if tur == "dis_kapi" else 82.0,
                        "mentese": "sol" if h[0] * sol[0] + h[1] * sol[1] > 0 else "sag", "bosluk": [lo, hi], "kaynak": kaynak}


ODALAR = [  # (ad, tür, [x0, y0, x1, y1]); omega hatları x yönünde (mahyaya paralel) → en = x boyu, derin = y boyu
    ("YAŞAM ALANI", "salon", [10.0, 167.3, 383.5, 772.5]),
    ("HOL", "antre_hol", [389.4, 280.3, 512.0, 462.0]),
    ("YATAK ODASI 1", "yatak_odasi", [389.4, 467.9, 759.9, 772.5]),
    ("WC", "wc", [517.9, 280.3, 759.9, 462.0]),
    ("YATAK ODASI 2", "yatak_odasi", [384.8, 5.0, 759.7, 274.2]),
]
VERANDA = [14.9, 0.0, 374.9, 157.4]


def main() -> int:
    M = montaj()
    M["etiketler"] = PENCERE_ETIKET
    PK03.pencereler(M)
    kapilar(M)
    M["ekler"] = PK03.ekler(M)
    # cumbanın dört açılı eki (31 / 790 / 200,7 / 790 / 31): dış pano eki
    M["ekler"] += [{"duvar": "dis", "cins": "pano_eki", "sacak": False, "yer": [x, 0.0], "not": "cumba açılı ek"} for x in (415.7, 471.9, 672.6, 728.9)]
    # kulaklı H: makaslar y yönünde (mahya x'te; omega planı), arka duvarın pano eklerine denk (x 135,4 … 637,4); ön tarafta makas ayakları
    # veranda kirişine ve cumbanın lentosuna gelir, pano eki yok
    makas_x = [5.0, 135.4, 261.0, 386.4, 512.0, 637.4, 764.8]
    for e in M["ekler"]:
        x, y = e["yer"]
        e["sacak"] = bool(e["duvar"] == "dis" and y > 770 and any(abs(x - m) <= 2 for m in makas_x))
    kos = Counter(k_["tur"] for k_ in M["koseler"])
    tum = M["panolar"] + M["cumba_panolari"]
    (BURASI / "pafta_montaj.json").write_text(json.dumps({"kaynak": "Duvar Yerleşim Planı.pdf, Kat planı.pdf (Uysallar Yapı)", "cerceve": __doc__.split("Çerçeve: ")[1].split("\n")[0],
                                                          "montaj_plani": M}, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    kapali = [{"ad": a, "tur": t, "alan_m2": round((r[2] - r[0]) * (r[3] - r[1]) / 1e4, 3), "en_cm": round(r[2] - r[0], 2), "derin_cm": round(r[3] - r[1], 2)}
              for a, t, r in ODALAR]
    cumba_alan = (313.2 + 200.7) / 2 * 57.4 / 1e4
    ver = {"ad": "VERANDA", "tur": "veranda", "alan_m2": round((VERANDA[2] - VERANDA[0]) * (VERANDA[3] - VERANDA[1]) / 1e4, 3),
           "en_cm": VERANDA[2] - VERANDA[0], "derin_cm": VERANDA[3] - VERANDA[1]}
    cevre = 770.0 + (782.5 - 157.4) + 374.9 + 157.4 + (31 + 79.6 + 200.7 + 79.6 + 31) + 782.5
    yp = {"kod": "PK-08", "is_emri_no": "PK08-EREN-BEY-60M2 (pafta kipi)", "H0": 250.0, "W": 769.8, "D": 782.5 + 57.4,
          "brut_m2": round(769.8 * 782.5 / 1e4 + cumba_alan, 3), "dis_cevre_m": round(cevre / 100, 3), "t_dis": 10.0,
          "panolar": [{"duvar": p["duvar"], "kal_mm": 100 if p["duvar"] == "dis" else 60, "boy": p["boy"],
                       "aciklik": None if not p.get("aciklik") else {k_: v for k_, v in p["aciklik"].items() if k_ in ("tur", "olcu", "genislik", "mentese")}}
                      for p in tum],
          "ekler": [{k_: e[k_] for k_ in ("duvar", "cins", "sacak")} for e in M["ekler"]],
          "koseler": dict(kos), "dikmeler": len(M["dikmeler"]),
          "ic_kalan_dis_duvar_m": round((374.9 + 157.4) / 100, 3),         # salonun veranda duvarı ve yatak 2'nin veranda duvarı ana çatının altında
          "veranda_kirisleri_cm": [360.0, 148.2],                           # yeşil kesikli: ön (dikmeden yatak 2 duvarına) ve yan (dikmeden salon köşesine)
          "kapali": kapali, "acik": [ver],
          "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 782.5, "boy_cm": 769.8, "egim_yuzde": 33.0, "sacak_cm": 25.0, "kalkan": 2,
                    "not": "teklif: \"Cumba Kubbeli Beşik Çatı - Trapez Sac\"; mahya x yönünde (omega planı 13 hat × 769,8); kat planında saçak 25; "
                           "eğim paftada yok (%33 varsayıldı); veranda ana çatının altında"},
                   {"ad": "cumba kubbesi", "tip": "tek_yon", "aciklik_cm": 57.4, "boy_cm": 375.0, "egim_yuzde": 33.0, "sacak_cm": 10.0, "kalkan": 0,
                    "makas_yok": True, "dere_yok": True, "sacak_hatlari_m": [3.6],
                    "not": "açılı cumbanın küçük kubbe çatısı (teklif); ölçüsü paftada yok, ana saçağın 32 cm önüne taşan kısım"}],
          "ozellikler": {"Panel Türü": "Yonga levha EPS (dış 100 / iç 60)", "Çatı Şekli": "Cumba kubbeli beşik", "Çatı Kaplaması": "Trapez sac",
                         "Dış Kapı": "Çelik", "İç Kapılar": "Amerikan panel", "Pencere": "PVC çift cam (satıcıya ait)", "Dış Cephe Boya": "var",
                         "İç Cephe Boya": "var", "Tavan": "Ters tavan", "Saçak Çıkması": "25 cm", "Çatı İzolasyonu": "Mineral yün 80 mm",
                         "Elektrik": "Sıva altı", "Su Tesisatı": "Sıcak, soğuk"},
          "alici_ait": {"kalemler": ["vitrifiye", "nakliye", "fayans", "parke", "zemin betonu", "mutfak dolabı"], "kaynak": "satış teklifi, 19 Ağustos 2025"},
          "kaynak_notu": "deneme/2026-10-13_pk_08/pafta_oku.py; montaj paftası DWG, duvar yerleşim planı ve mimari plandan; tavan omega planı 60'ta bir → ters tavan varsayıldı"}
    (BURASI / "yapi_pafta.json").write_text(json.dumps(yp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet = {"pano": len(tum), "dis": sum(p["duvar"] == "dis" for p in tum), "ic": sum(p["duvar"] == "ic" for p in tum), "kose": dict(kos),
            "dikme": len(M["dikmeler"]), "ek": {f"{d}|{c}|" + ("kulaklı" if s else "-"): n for (d, c, s), n in Counter((e["duvar"], e["cins"], e["sacak"]) for e in M["ekler"]).items()}}
    print(json.dumps(ozet, ensure_ascii=False))
    for p in tum:
        if p.get("aciklik"):
            print("  ", p["yon"], p["c"], p["a0"], p["a1"], p["boy"], p["aciklik"]["tur"], p["aciklik"]["olcu"], p["aciklik"].get("mentese", ""))
    print("boylar", dict(Counter(f"{p['duvar']} {p['boy']}" for p in tum)))
    print("brüt", yp["brut_m2"], "çevre", yp["dis_cevre_m"], "odalar", [(o["ad"], o["alan_m2"]) for o in kapali], "veranda", ver["alan_m2"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
