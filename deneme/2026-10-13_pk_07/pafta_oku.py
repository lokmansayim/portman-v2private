"""PK-07 montaj paftasının vektör okuması (13 Ekim 2026; İE-11 PR-2, kör test adım 1; pafta kipi).

Diamond 70,65 m² prefabrik konut (Aziz Bey, Manisa; Halil Bey; Portatifev paftası, çizen Ubeydullah Özer, kontrol Lokman Sayım).
13 sayfa: 1 teknik özellikler ve görünüşler, 2 montaj planı, 3 H profil montaj planı (H türleri renkli dairelerle), 4–5 özel kutu profiller
(A–E), 6 betopan fuga detayı, 7 özel büküm saçlar, 8 tavan omega, 9 makas ve dere, 10 baş makas betopanı, 11 aşık, 12 çatı kaplaması,
13 elektrik. Üretim dosyası (`PK07_URETIM_DOSYASI.zip`, LyteCad / makine CSV'leri): makas MKS01–07 alt başlık 8450, MKS08–10 4515;
veranda paneli 3925 × 1189; D01 (100/120 pencereli 1470'lik çelik duvar paneli); KAPI-01…05 (1250'lik çelik kapı panoları).
Motor çizemiyor: iç duvar 100 mm, önde 120 cm çıkıntılı salon (L plan) ve önüne paralel küçük beşik ("cumba"), 100/120 pencere, veranda saçağı.
Çerçeve: cm; x salonun sol dış yüzünden (sağ dış yüz 785), y ön yüzden (salonun ön yüzü y = 0; sağ bölümün ön duvarı y 120–129,9;
arka duvar 890–900). Sayfa 270° döndürülmüş: x = (y_pdf − Y0) / S, y = (x_pdf − X0) / S.
Renkler (sayfa 2): siyah dörtgen = 125,5'lik pano, mavi = kesik / özel pano, kırmızı = köşe (10 × 5) ve kutu profil (10 × 10, A ve B),
lacivert 82 × 4 = kapı kanadı. İç duvarlar da 10 cm: dış / iç ayrımı konumdan (dış çizgi) yapılır.

Koşma: python3 -I deneme/2026-10-13_pk_07/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf as fitz

BURASI = Path(__file__).resolve().parent
K = BURASI / "kaynak"
PAFTA = K / "PK07_MONTAJ_PAFTASI.pdf"
S = (413.88 / 900 + 361.08 / 785) / 2          # pt / cm (sayfa 2)
X0_PDF, Y0_PDF = 254.84, 402.0
RENK = {(0.0, 0.0, 0.0): "STD", (0.0, 0.0, 1.0): "OZEL", (1.0, 0.0, 0.0): "KOSE", (0.047, 0.275, 0.592): "KANAT"}
_pk03 = importlib.util.spec_from_file_location("pk03_oku", BURASI.parent / "2026-10-13_pk_03" / "pafta_oku.py")
PK03 = importlib.util.module_from_spec(_pk03); _pk03.loader.exec_module(PK03)        # pencereler(), kapilar(), ekler() ortak


def b(xp, yp):
    return (yp - Y0_PDF) / S, (xp - X0_PDF) / S


def dis_mi(yon: str, c: float, a0: float, a1: float) -> bool:
    """Dış çizgi: sol (x ≈ 5), sağ (x ≈ 780), salonun önü (y ≈ 5, x < 391,5), sağ bölümün önü (y ≈ 125, x > 381), arka (y ≈ 895),
    salon–veranda duvarı (x ≈ 386,5, y < 120)."""
    if yon == "y":
        return abs(c - 4.95) < 1 or abs(c - 780.0) < 1 or (abs(c - 386.45) < 1 and a1 <= 121)
    return (abs(c - 4.95) < 1 and a1 <= 392) or (abs(c - 124.95) < 1 and a0 >= 381) or abs(c - 894.95) < 1


def montaj() -> dict:
    pg = fitz.open(PAFTA)[1]
    panolar, koseler, kolonlar, kanatlar = [], [], [], []
    for d in pg.get_drawings():
        r = RENK.get(tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))))
        if not r:
            continue
        for it in d["items"]:
            if it[0] != "qu":
                continue
            q = it[1].rect
            if r == "KOSE" and q.width > 10 and q.height > 10:          # sol tablonun hücreleri
                continue
            (xa, ya), (xb, yb) = b(q.x0, q.y0), b(q.x1, q.y1)
            x0, x1 = sorted((round(xa, 2), round(xb, 2))); y0, y1 = sorted((round(ya, 2), round(yb, 2)))
            w, h = x1 - x0, y1 - y0
            t, L = min(w, h), max(w, h)
            if r in ("STD", "OZEL") and L > 20 and abs(t - 10) < 0.5:
                yon = "x" if w > h else "y"
                c = round((y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2, 2)
                a0, a1 = (x0, x1) if yon == "x" else (y0, y1)
                panolar.append({"yon": yon, "c": c, "a0": a0, "a1": a1, "boy": round(L * 4) / 4, "boy_cizim": round(L, 2), "t": 10.0,
                                "duvar": "dis" if dis_mi(yon, c, a0, a1) else "ic", "tur": r, "rect": [x0, y0, x1, y1]})
            elif r == "KOSE" and abs(t - 9.9) < 0.4 and abs(L - 9.9) < 0.4:
                kolonlar.append([x0, y0, x1, y1])                        # A (salonun ön sağ köşesi) ve B (veranda dikmesi)
            elif r == "KOSE":
                koseler.append({"tur": "dis" if (x0 < 10 or x1 > 775 or y0 < 10 or y1 > 890 or (380 < x0 < 390 and 115 < y0 < 125)) else "ic",
                                "rect": [x0, y0, x1, y1]})
            elif r == "KANAT" and 80 < L < 84:
                kanatlar.append([x0, y0, x1, y1])
    olculer = sorted({float(w[4]) for w in pg.get_text("words") if re.fullmatch(r"\d+(\.\d+)?", w[4]) and 30 < float(w[4]) < 260} | {125.5})
    for p in panolar:                                                   # çizimdeki 62,88 / 79,58 / 74,62 gibi sapmalar yazıdaki ölçüye (± 0,4)
        yakin = min(olculer, key=lambda o: abs(o - p["boy_cizim"]))
        p["boy"] = yakin if abs(yakin - p["boy_cizim"]) <= 0.4 else round(p["boy_cizim"] * 4) / 4
    etiket = []
    for w in pg.get_text("words"):
        if re.fullmatch(r"\d+/\d+", w[4]):
            x, y = b((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            etiket.append({"metin": w[4], "x": round(x, 1), "y": round(y, 1)})
    return {"panolar": panolar, "koseler": koseler, "kolonlar": kolonlar, "kanatlar": kanatlar, "etiketler": etiket}


def makaslar() -> dict:
    """Sayfa 9: makaslar x yönünde (camgöbeği çift çizgi, 8 cm); eksenin y'si. Ana çatı makası x −30 … 815, cumba makası −30 … 421,5."""
    pg = fitz.open(PAFTA)[8]
    wx, wy, cizgi = [], [], defaultdict(lambda: [1e9, -1e9])
    for d in pg.get_drawings():
        col = tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9)))
        for it in d["items"]:
            if it[0] != "l":
                continue
            p, q = it[1], it[2]
            if col == (0.388, 0.392, 0.4):
                wx += [p.x, q.x]; wy += [p.y, q.y]
            if col == (0.0, 1.0, 1.0) and abs(p.x - q.x) < 0.3:
                g = cizgi[round(p.x, 1)]; g[0] = min(g[0], p.y, q.y); g[1] = max(g[1], p.y, q.y)
    X0, Y0, s9 = min(wx), min(wy), (max(wx) - min(wx)) / 900
    ham = sorted(((k - X0) / s9, (a - Y0) / s9, (b_ - Y0) / s9) for k, (a, b_) in cizgi.items() if b_ - a > 50)
    eksen = []
    for y, xa, xb in ham:
        if eksen and y - eksen[-1]["y"][-1] < 10 and abs(xb - eksen[-1]["x1"]) < 5:
            eksen[-1]["y"].append(y)
        else:
            eksen.append({"y": [y], "x1": xb})
    ana = [round((e["y"][0] + e["y"][-1]) / 2, 1) for e in eksen if e["x1"] > 800]
    cumba = [round((e["y"][0] + e["y"][-1]) / 2, 1) for e in eksen if e["x1"] < 500]
    return {"ana": ana, "cumba": cumba}


def h_plani() -> dict:
    """Sayfa 3: H türleri renkli dairelerle (lejantta sırayla dübelli & kulaklı, dübelli, standart, 3'lü dübelli & kulaklı, 3'lü dübelli,
    3'lü standart). Plandaki daireler türüne göre sayılır."""
    pg = fitz.open(PAFTA)[2]
    daire = defaultdict(set)
    for d in pg.get_drawings():
        col = tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9)))
        if any(it[0] == "c" for it in d["items"]):
            r = d["rect"]
            if 8 < r.width < 30 and abs(r.width - r.height) < 1.5:
                daire[col].add((round(r.x0 + r.width / 2), round(r.y0 + r.height / 2)))
    sira = sorted((min(p[0] for p in v if p[1] < 140), col) for col, v in daire.items() if any(p[1] < 140 for p in v))
    adlar = ["kulakli", "dubelli", "standart", "uclu_kulakli", "uclu_dubelli", "uclu_standart"]
    return {ad: len([p for p in daire[col] if p[1] > 420]) for ad, (_x, col) in zip(adlar, sira)}


def tavan_omega() -> dict:
    pg = fitz.open(PAFTA)[7]
    parca = []
    for bl in pg.get_text("dict")["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if sp["color"] == 0xFF00FF and re.fullmatch(r"\d+(\.\d+)?", t) and float(t) > 20:
                    parca.append(float(t))
    return {"parcalar_cm": parca, "parca": len(parca), "toplam_m": round(sum(parca) / 100, 2)}


def asik() -> dict:
    """Sayfa 11: aşık parçaları (eflatun yazı): 410'luk tam boylar, yüz sonundaki 20 / 140'lık parçalar, cumbanın iç yüzünde 150'lik 5 sıra."""
    pg = fitz.open(PAFTA)[10]
    say = []
    for bl in pg.get_text("dict")["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if sp["color"] == 0xFF00FF and re.fullmatch(r"\d+(\.\d+)?", t):
                    say.append(float(t))
    c = Counter(say)
    boy = c[410.0] + math.ceil(c[140.0] / 3) + math.ceil(c[150.0] / 2)     # 4200'lük boydan: 410 tek, 140 üçlü, 150 ikili; 20'ler artandan
    return {"parcalar": {str(k_): v for k_, v in sorted(c.items())}, "toplam_m": round(sum(say) / 100, 2), "boy_4200": boy}


ODALAR = [  # (ad, tür, [x0, y0, x1, y1]); ters tavan omegası mahyaya (y) paralel → en = y boyu, derin = x boyu
    ("SALON", "salon", [9.9, 9.9, 381.5, 513.5]),
    ("OTURMA ODASI", "oturma", [9.9, 523.4, 381.5, 890.0]),
    ("HOL", "antre_hol", [391.4, 129.9, 507.0, 639.0]),
    ("MUTFAK", "mutfak", [391.4, 689.6, 774.9, 890.0]),
    ("MUTFAK", "mutfak", [391.4, 648.9, 507.0, 689.6]),
    ("WC & BANYO", "banyo", [516.9, 460.8, 774.9, 679.7]),
    ("YATAK ODASI", "yatak_odasi", [516.9, 129.9, 774.9, 450.6]),
]
VERANDA = [391.5, 0.0, 785.0, 120.0]


def main() -> int:
    M = montaj()
    PK03.pencereler(M)
    PK03.kapilar(M)
    for p in M["panolar"]:
        a = p.get("aciklik")
        if a and a["tur"] == "kapi?":
            a["tur"] = "dis_kapi" if p["duvar"] == "dis" else "ic_kapi"
            if a["tur"] == "dis_kapi":
                a["genislik"] = 90.0; a["olcu"] = "90"; a["not"] = "çelik standart; listede 900 × 2000 (L4)"
    M["ekler"] = PK03.ekler(M)
    mk = makaslar()
    # kulaklı H: makasın denk geldiği dış ek (sayfa 3'ün lejantı da böyle tanımlıyor). Makaslar x yönünde → ayaklar y yönündeki dış duvarlarda
    # (sol, sağ; cumba makası sol duvar ve salon–veranda duvarı)
    for e in M["ekler"]:
        x, y = e["yer"]
        yon_y = abs(x - 4.95) < 1 or abs(x - 780.0) < 1 or (abs(x - 386.45) < 1 and y < 121)   # arka duvarın x 386,4 T'si x yönünde
        e["sacak"] = bool(e["duvar"] == "dis" and yon_y and any(abs(y - m) <= 2.0 for m in mk["ana"] + mk["cumba"]))
    kos = Counter(k_["tur"] for k_ in M["koseler"])
    hp, to, as_ = h_plani(), tavan_omega(), asik()
    (BURASI / "pafta_montaj.json").write_text(json.dumps({"kaynak": "DIAMOND 70 M2 MONTAJ PAFTASI.pdf (13 sayfa)", "cerceve": __doc__.split("Çerçeve: ")[1].split("\n")[0],
                                                          "montaj_plani": M, "makaslar": mk, "h_plani": hp, "tavan_omega": to, "asik": as_},
                                                         ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    kapali = [{"ad": a, "tur": t, "alan_m2": round((r[2] - r[0]) * (r[3] - r[1]) / 1e4, 3), "en_cm": round(r[3] - r[1], 2), "derin_cm": round(r[2] - r[0], 2)}
              for a, t, r in ODALAR]
    ver = {"ad": "VERANDA", "tur": "veranda", "alan_m2": round((VERANDA[2] - VERANDA[0]) * (VERANDA[3] - VERANDA[1]) / 1e4, 3),
           "en_cm": VERANDA[3] - VERANDA[1], "derin_cm": VERANDA[2] - VERANDA[0]}
    yp = {"kod": "PK-07", "is_emri_no": "PK07-DIAMOND-70M2 (pafta kipi)", "H0": 250.0, "W": 785.0, "D": 900.0,
          "brut_m2": round(785.0 * 900.0 / 1e4, 3), "dis_cevre_m": round(2 * (785.0 + 900.0) / 100, 3), "t_dis": 10.0,
          "panolar": [{"duvar": p["duvar"], "kal_mm": 100, "boy": p["boy"],
                       "aciklik": None if not p.get("aciklik") else {k_: v for k_, v in p["aciklik"].items() if k_ in ("tur", "olcu", "genislik", "mentese")}}
                      for p in M["panolar"]],
          "ekler": [{k_: e[k_] for k_ in ("duvar", "cins", "sacak")} for e in M["ekler"]],
          "koseler": dict(kos), "dikmeler": len(M["kolonlar"]),
          "ic_kalan_dis_duvar_m": 0.0,                                   # bütün dış duvarlar saçak ya da kalkan altında (salon–veranda duvarı cumbanın saçağında)
          "veranda_kirisleri_cm": [393.5],                               # E: 10'luk kutu profil 393,5 (sayfa 4); yan kenarda kiriş yok
          "kapali": kapali, "acik": [ver],
          "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 785.0, "boy_cm": 780.0, "egim_yuzde": round(math.tan(math.radians(18.2)) * 100, 1),
                    "sacak_cm": 30.0, "kalkan": 2, "kalkan_duvar_cm": 785.0 + 393.5, "sacak_hatlari_m": [9.6, 8.4],
                    "not": "sayfa 1 / 10: 845 açıklık, 18,2°, eğik 444,75; makas MK01–MK07 (y 125 … 894,9; ilk aralık 142,6); sol yüz cumbanın sol "
                           "yüzüyle aynı düzlemde ve öne 120 uzar (aşık planı 960 / 840); ön kalkanın altında yalnız sağ bölümün ön duvarı (393,5) var"},
                   {"ad": "cumba", "tip": "besik", "aciklik_cm": 391.5, "boy_cm": 120.0, "egim_yuzde": round(math.tan(math.radians(18.2)) * 100, 1),
                    "sacak_cm": 30.0, "kalkan": 1, "capraz": False, "mahya_boy_cm": 150.0, "kalkan_duvar_cm": 391.5, "sacak_hatlari_m": [1.5],
                    "not": "salonun öne çıkıntısı üstünde ana çatıya paralel küçük beşik (451,5 açıklık, 18,2°, eğik 237,64); MK08–MK10; iç yüzü 5 × 150 aşık"},
                   {"ad": "veranda saçağı", "tip": "tek_yon", "aciklik_cm": 120.0, "boy_cm": 393.5, "egim_yuzde": 5.0, "sacak_cm": 0.0, "kalkan": 0,
                    "makas_yok": True, "acik": True, "sacak_hatlari_m": [3.935],
                    "not": "hafif çelik veranda paneli (üretim PANEL.csv 3925 × 1189) üstüne 4 × 125'lik sandviç panel (sayfa 12); eğim paftada yok, %5"}],
          "ozellikler": {"Panel Türü": "Pres Panel", "Çatı Şekli": "Beşik + Cumba", "Çatı Kaplaması": "Sandviç Panel", "Çatı Kaplama Rengi": "Bordo",
                         "Dış Kapı": "Çelik Standart", "İç Kapılar": "Standart Amerikan", "Dış Cephe Boya": "?", "İç Cephe Boya": "?",
                         "Pencere Rengi": "Alıcıya ait", "Tavan": "Ters", "Saçak ve Alın Rengi": "Bordo",
                         "Açıklama": "1- Dış cephe fugalı düz betopan 2- Çatı izolasyon mineral yün"},
          "alici_ait": {"kalemler": ["pencere"], "kaynak": "özellik tablosu \"Pencere Rengi: ALICIYA AİT\", \"PENCERE DETAY: ALICIYA AİT\""},
          "kaynak_notu": "deneme/2026-10-13_pk_07/pafta_oku.py; Motor çizemiyor (iç duvar 100, L plan, paralel cumba, veranda saçağı)"}
    (BURASI / "yapi_pafta.json").write_text(json.dumps(yp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet = {"pano": len(M["panolar"]), "dis": sum(p["duvar"] == "dis" for p in M["panolar"]), "ic": sum(p["duvar"] == "ic" for p in M["panolar"]),
            "kose": dict(kos), "kolon": len(M["kolonlar"]),
            "kapi": dict(Counter((p.get("aciklik") or {}).get("tur") for p in M["panolar"] if (p.get("aciklik") or {}).get("tur", "").endswith("kapi"))),
            "ek": {f"{d}|{c}|" + ("kulaklı" if s else "-"): n for (d, c, s), n in Counter((e["duvar"], e["cins"], e["sacak"]) for e in M["ekler"]).items()},
            "h_plani_pafta": hp}
    print(json.dumps(ozet, ensure_ascii=False))
    print("makas", mk, "\ntavan omega", to["parca"], "parça", to["toplam_m"], "m; aşık", as_)
    for p in M["panolar"]:
        if p.get("aciklik"):
            print("  ", p["yon"], p["c"], (round(p["a0"], 1), round(p["a1"], 1)), p["boy"], p["duvar"], p["aciklik"]["tur"], p["aciklik"].get("olcu"), p["aciklik"].get("mentese", ""))
    print("boylar", dict(Counter(f"{p['duvar']} {p['boy']}" for p in M["panolar"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
