"""PK-05 montaj paftasının vektör okuması (13 Ekim 2026; İE-11 PR-2, kör test adım 1; pafta kipi).

Abdullah Yavuz 60 m² (Kapaklı; Mehmet Yıldırım bayisi; Loftev, çizen Ebru Balcı). Montaj setinden PDF olarak yalnız
"PANEL YERLEŞİMİ" (17 Eylül 2025, mimarın planı üstüne pano yerleşimi) ve müşteri onay paftası var; öteki montaj paftaları DWG (okunamıyor).
Çatı LyteCad DXF'inden (MK01–MK07 makas, ÇP01–ÇP02 ek bölüm çatı paneli) ve hafif çelik makine dosyasından (Alpha Mini `.bde`: makas alt
başlığı 6600, üst başlığı 6648, yükselme 900 → 100: eğim %12,1). Motor çizemiyor (L plan, tek yön çatı, 80/120 pencere).
Çerçeve: cm; x soldaki dış yüzden, y paftanın alt kenarındaki dış yüzden (WC ve çok amaçlı bölümün pencereleri bu kenarda).
Renkler: turuncu = 125,5'lik pano, siyah = kesik pano (ve 10 × 4 kapı kasası parçaları), kırmızı 10 × 5 = köşe, camgöbeği = pencere karkas işareti.
Ölçek 130,8 pt = 125,5 cm.

Koşma: python3 -I deneme/2026-10-13_pk_05/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
"""
from __future__ import annotations

import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz

BURASI = Path(__file__).resolve().parent
K = BURASI / "kaynak"
S = 130.8 / 125.5
RENK = {(0.949, 0.404, 0.133): "STD", (0.0, 0.0, 0.0): "OZEL", (1.0, 0.0, 0.0): "KOSE", (0.498, 0.875, 1.0): "KARKAS"}
_pk03 = importlib.util.spec_from_file_location("pk03_oku", BURASI.parent / "2026-10-13_pk_03" / "pafta_oku.py")
PK03 = importlib.util.module_from_spec(_pk03); _pk03.loader.exec_module(PK03)        # ekler() ve menteşe sözleşmesi ortak


def montaj() -> dict:
    pg = fitz.open(K / "PK05_PANEL_YERLESIMI.pdf")[0]
    ham = []
    for d in pg.get_drawings():
        r = RENK.get(tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))))
        if r:
            for it in d["items"]:
                if it[0] == "qu":
                    q = it[1].rect; ham.append((r, q.x0, q.y0, q.x1, q.y1))
    duvar = [o for o in ham if o[0] in ("STD", "OZEL", "KOSE")]
    X0 = min(min(o[1], o[3]) for o in duvar); Y0 = min(min(o[2], o[4]) for o in duvar)
    b = lambda xp, yp: ((yp - Y0) / S, (xp - X0) / S)
    panolar, koseler, karkas = [], [], []
    for r, a, c, e, f in ham:
        (xa, ya), (xb, yb) = b(a, c), b(e, f)
        x0, x1 = sorted((xa, xb)); y0, y1 = sorted((ya, yb))
        w, h = x1 - x0, y1 - y0; t, L = min(w, h), max(w, h)
        if r in ("STD", "OZEL") and L > 20 and (abs(t - 10) < 0.4 or abs(t - 6) < 0.4):
            yon = "x" if w > h else "y"
            panolar.append({"yon": yon, "c": round((y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2, 2), "a0": round(x0 if yon == "x" else y0, 2),
                            "a1": round(x1 if yon == "x" else y1, 2), "boy": round(L, 2), "t": round(t, 1), "duvar": "dis" if t > 8 else "ic",
                            "tur": r, "rect": [round(v, 2) for v in (x0, y0, x1, y1)]})
        elif r == "KOSE" and 4 < t < 6 and 9 < L < 11:
            koseler.append({"tur": "dis", "rect": [round(v, 2) for v in (x0, y0, x1, y1)]})
        elif r == "KARKAS":
            karkas.append([round(v, 2) for v in (x0, y0, x1, y1)])
    etiket = []
    for w in pg.get_text("words"):
        m = re.fullmatch(r"P?(\d+)/(\d+)", w[4])
        if m:
            x, y = b((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            etiket.append({"metin": f"{m.group(1)}/{m.group(2)}", "x": round(x, 1), "y": round(y, 1)})
    return {"panolar": panolar, "koseler": koseler, "karkas_isaretleri": karkas, "etiketler": etiket}


# Kapılar: kanatlar bu paftada dörtgen değil; kasa parçaları (siyah 10 × 4) ve dış kapı kanadı (1 pt çizgi) ile işaretli. Menteşe noktası,
# açılma yönü ve boşluk yazıdan (ÇK:100/220, K:90/210, K:80/210). Menteşe adı PK-03 ile aynı sözleşme.
KAPILAR = [  # (tür, genişlik, menteşe noktası (x, y), açılma yönü, kaynak)
    ("dis_kapi", 100, (363.5, 753.0), (0, -1), "kanat çizgisi x 363,5, y 670,6–750,6; ÇK:100/220"),
    ("ic_kapi", 90, (306.9, 315.8), (0, -1), "kasa parçaları x 304,9–308,9; K:90/210 (yatak odası)"),
    ("ic_kapi", 90, (605.5, 315.8), (0, -1), "kasa parçaları x 603,4–607,5; K:90/210 (mutfak)"),
    ("ic_kapi", 80, (626.0, 24.6), (1, 0), "kasa parçaları y 22,6–26,6; K:80/210 (çok amaçlı)"),
    ("ic_kapi", 80, (877.0, 26.1), (1, 0), "kasa parçaları y 24,1–28,1; K:80/210 (WC)"),
]


def acikliklar(M) -> None:
    for e in M["etiketler"]:
        olcu = e["metin"].replace("/", "x")
        aday = []
        for p in M["panolar"]:
            if p["duvar"] != "dis":
                continue
            boy_eks = e["x"] if p["yon"] == "x" else e["y"]
            if p["a0"] - 5 <= boy_eks <= p["a1"] + 5:
                aday.append((abs((e["y"] if p["yon"] == "x" else e["x"]) - p["c"]), p))
        _d, p = min(aday, key=lambda t: t[0])
        p["aciklik"] = {"tur": "pencere", "olcu": olcu, "genislik": float(olcu.split("x")[0]), "kaynak": f"etiket {e['metin']} ({e['x']}, {e['y']})"}
    for tur, gen, (hx, hy), n, kaynak in KAPILAR:
        dik_x = n[0] == 0                                  # açılma ±y → kapı x yönündeki duvarda
        bul = None
        for p in M["panolar"]:
            if p["yon"] != ("x" if dik_x else "y") or abs((hy if dik_x else hx) - p["c"]) > p["t"] / 2 + 1.5:
                continue
            ek = hx if dik_x else hy
            for lo, hi in ((ek - gen, ek), (ek, ek + gen)):
                if p["a0"] - 1.5 <= lo and hi <= p["a1"] + 1.5 and not p.get("aciklik"):
                    bul = (p, lo, hi, ek); break
            if bul:
                break
        p, lo, hi, ek = bul
        sol = (-n[1], n[0]); orta = (lo + hi) / 2
        h = (ek - orta, 0) if dik_x else (0, ek - orta)
        p["aciklik"] = {"tur": tur, "olcu": str(gen), "genislik": float(gen), "mentese": "sol" if h[0] * sol[0] + h[1] * sol[1] > 0 else "sag",
                        "bosluk": [round(lo, 1), round(hi, 1)], "kaynak": kaynak}


ODALAR = [  # duvar iç yüzlerinden; paftadaki alanlarla aynı (salon 26,30 · yatak 9,50 · mutfak 8,97 · çok amaçlı 4,61 · WC 4,18)
    ("SALON", "salon", [10.0, 321.8, 620.0, 753.0]),
    ("YATAK ODASI", "yatak_odasi", [10.0, 10.0, 320.7, 315.8]),
    ("MUTFAK", "mutfak", [326.8, 10.0, 620.0, 315.8]),
    ("ÇOK AMAÇLI BÖLÜM", "diger", [626.0, 10.0, 871.0, 198.0]),
    ("WC", "wc", [877.0, 10.0, 1099.5, 198.0]),
]


def main() -> int:
    M = montaj()
    acikliklar(M)
    M["ekler"] = PK03.ekler(M)
    # saçak (makas ayağı) duvarları: ana bölümde makaslar x'i geçer → ayaklar sol ve sağ (y yönündeki) duvarlarda; ek bölümde çatı panelleri
    # y'yi geçer → ön ve arka (x yönündeki) duvarlar
    for e in M["ekler"]:
        x, y = e["yer"]
        ana_yan = e["duvar"] == "dis" and (x < 10.5 or (619 < x < 631 and y > 200))        # ana bölümün sol ve sağ dış duvarı
        ek_on_arka = e["duvar"] == "dis" and x > 630 and (y < 10.5 or 197 < y < 209)       # ek bölümün ön ve arka dış duvarı
        e["sacak"] = ana_yan or ek_on_arka
    kos = Counter(k_["tur"] for k_ in M["koseler"])
    (BURASI / "pafta_montaj.json").write_text(json.dumps({"kaynak": "PK05_PANEL_YERLESIMI.pdf (17 Eylül 2025)", "montaj_plani": M}, ensure_ascii=False, indent=1) + "\n",
                                              encoding="utf-8")
    kapali = [{"ad": a, "tur": t, "alan_m2": round((r[2] - r[0]) * (r[3] - r[1]) / 1e4, 3), "en_cm": round(r[3] - r[1], 2) if a in ("SALON", "YATAK ODASI", "MUTFAK") else round(r[2] - r[0], 2),
               "derin_cm": round(r[2] - r[0], 2) if a in ("SALON", "YATAK ODASI", "MUTFAK") else round(r[3] - r[1], 2)} for a, t, r in ODALAR]
    W, D = 1109.5, 763.0
    kapali_brut = 630.0 * 763.0 + (1109.5 - 630.0) * 208.0
    cevre = 2 * (1109.5 + 763.0)                                             # L planın dış çevresi dikdörtgen zarfınkiyle aynı
    yp = {"kod": "PK-05", "is_emri_no": "PK05-ABDULLAH-YAVUZ-60M2 (pafta kipi)", "H0": 250.0, "W": W, "D": D, "brut_m2": round(kapali_brut / 1e4, 3),
          "dis_cevre_m": round(cevre / 100, 3), "t_dis": 10.0, "ic_kalan_dis_duvar_m": 0.0,
          "panolar": [{"duvar": p["duvar"], "kal_mm": 100 if p["duvar"] == "dis" else 60, "boy": round(round(p["boy"] * 4) / 4, 2),
                       "aciklik": None if not p.get("aciklik") else {k_: v for k_, v in p["aciklik"].items() if k_ in ("tur", "olcu", "genislik", "mentese")}}
                      for p in M["panolar"]],
          "ekler": [{k_: e[k_] for k_ in ("duvar", "cins", "sacak")} for e in M["ekler"]],
          "koseler": dict(kos), "dikmeler": 0, "veranda_kirisleri_cm": [], "kapali": kapali, "acik": [],
          "cati": [{"ad": "ana çatı", "tip": "tek_yon", "aciklik_cm": 630.0, "boy_cm": 763.0, "egim_yuzde": 12.1, "sacak_cm": 30.0, "kalkan": 2,
                    "not": "LyteCad makas DXF'i: MK01–MK07 (aralık 125); Alpha Mini makas dosyası: alt başlık 6600, üst başlık 6648, 900 → 100"},
                   {"ad": "ek bölüm çatısı", "tip": "tek_yon", "aciklik_cm": 208.0, "boy_cm": 479.5, "egim_yuzde": 5.0, "sacak_cm": 30.0, "kalkan": 0,
                    "makas_yok": True, "not": "makas yok, iki hafif çelik çatı paneli (ÇP01, ÇP02: 2398 × 2082); eğim paftada yok, %5 varsayıldı"}],
          "ozellikler": {"Panel Türü": "Press Panel", "Çatı Şekli": "Tek yön çatı", "Çatı Kaplaması": "Tek kat panel", "Çatı Kaplama Rengi": "Antrasit",
                         "Dış Kapı": "Çelik", "İç Kapılar": "Amerikan Panel", "Dış Cephe Boya": "...", "İç Cephe Boya": "...", "Tavan": "Asma tavan",
                         "Saçak Rengi": "Antrasit", "Saçak Çıkması": "30 cm", "Yağmur Oluğu": "Metal", "Yağmur İniş Borusu": "Metal"},
          "alici_ait": {"kalemler": [], "kaynak": "müşteri onay paftası: alıcıya ait kalem yazılmamış; boya alanları boş"},
          "kaynak_notu": "deneme/2026-10-13_pk_05/pafta_oku.py; Motor çizemiyor (L plan, tek yön çatı, 80/120 pencere)"}
    (BURASI / "yapi_pafta.json").write_text(json.dumps(yp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"pano": len(M["panolar"]), "dis": sum(p["duvar"] == "dis" for p in M["panolar"]), "ic": sum(p["duvar"] == "ic" for p in M["panolar"]),
                      "kose": dict(kos), "ek": {f"{d}|{c}|" + ("saçak" if s_ else "kalkan"): n for (d, c, s_), n in Counter((e["duvar"], e["cins"], e["sacak"]) for e in M["ekler"]).items()}},
                     ensure_ascii=False))
    for p in M["panolar"]:
        if p.get("aciklik"):
            print("  ", p["yon"], p["c"], (p["a0"], p["a1"]), p["boy"], p["aciklik"]["tur"], p["aciklik"]["olcu"], p["aciklik"].get("mentese", ""))
    print("brüt", yp["brut_m2"], "çevre", yp["dis_cevre_m"], "odalar", [(o["ad"], o["alan_m2"]) for o in kapali])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
