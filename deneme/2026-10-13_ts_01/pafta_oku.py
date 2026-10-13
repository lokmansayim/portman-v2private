"""TS-01 montaj paftasının vektör okuması (13 Ekim 2026; AIPrefabrik test seti, kör test adım 1; pafta kipi).

Diamond 45 m² prefabrik konut (Ramazan Batmaz; Portatifev paftası, çizen Ubeydullah Özer, kontrol Lokman Sayım).
12 sayfa:
  1 teknik özellikler, mobilyalı plan, kesitler;
  2 montaj planı;
  3 H profil montaj planı (H türleri renkli dairelerle; özel C ve F);
  4–5 özel kutu profiller (A–F);
  6 tavan omega; 7 makas ve dere; 8 baş makas betopanı; 9 aşık; 10 OSB; 11 çatı kaplaması; 12 elektrik.
Plan: 750 × 690. Sol bölümde (x 0–300) yatak odasının önü 150 cm öne çıkar; üstünde ana çatıya dik küçük beşik ("cumba", MK11–MK12, iç uçta MK13).
Arkada dış kapının önünde 135,5 × 130 "sundurma", iki 10'luk kutu profil kolon (D) üstünde küçük beşik (MK09–MK10).
Sağ ön duvardaki 150/190 (D01, 251) ve cumbanın önündeki 150/190 (D02, 290) mavi özel pano.

Çerçeve: cm; x sol dış yüzden (sağ dış yüz 749,5); y cumbanın ön dış yüzünden (y = 0). Sağ bölümün ön duvarı y 150–160, arka duvar 679,7–689,6.
Sayfa 270° döndürülmüş: x = (y_pdf − Y0) / S, y = (x_pdf − X0) / S (PK-07 ile aynı dönüşüm; menteşe sözleşmesi aynı kalır).
Renkler (sayfa 2):
  - siyah dörtgen 125,5'lik pano; mavi kesik ya da özel pano;
  - kırmızı köşe (10 × 5), iç köşe (6 × 3) ve kolon (10 × 10, D);
  - lacivert 82 × 4 kapı kanadı.
İç duvarlar 6 cm.

Koşma: python3 -I deneme/2026-10-13_ts_01/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
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
PAFTA = K / "TS01_MONTAJ_PAFTASI.pdf"
S = 68.4 / 125.5                                  # pt / cm (sayfa 2)
X0_PDF, Y0_PDF = 291.8, 534.84
RENK = {(0.0, 0.0, 0.0): "STD", (0.0, 0.0, 1.0): "OZEL", (1.0, 0.0, 0.0): "KOSE", (0.047, 0.275, 0.592): "KANAT"}
_pk03 = importlib.util.spec_from_file_location("pk03_oku", BURASI.parent / "2026-10-13_pk_03" / "pafta_oku.py")
PK03 = importlib.util.module_from_spec(_pk03); _pk03.loader.exec_module(PK03)        # pencereler(), kapilar(), ekler() ortak


def b(xp, yp):
    return (yp - Y0_PDF) / S, (xp - X0_PDF) / S


def dis_mi(yon: str, c: float, a0: float, a1: float) -> bool:
    """Dış çizgi: sol (x ≈ 4,95), sağ (x ≈ 744,4), cumbanın sağı (x ≈ 294,7, y < 160); arka (y ≈ 684,6), sağ bölümün önü (y ≈ 155),
    cumbanın önü (y ≈ 5,1)."""
    if yon == "y":
        return abs(c - 4.955) < 1 or abs(c - 744.415) < 1 or (abs(c - 294.705) < 1 and a1 <= 161)
    return abs(c - 684.635) < 1 or (abs(c - 155.005) < 1 and a0 >= 289) or abs(c - 5.065) < 1


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
            if r in ("STD", "OZEL") and L > 20 and (abs(t - 10) < 0.5 or abs(t - 6) < 0.3):
                yon = "x" if w > h else "y"
                c = round((y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2, 3)
                a0, a1 = (x0, x1) if yon == "x" else (y0, y1)
                kal = 10.0 if abs(t - 10) < 0.5 else 6.0
                panolar.append({"yon": yon, "c": c, "a0": a0, "a1": a1, "boy": round(L * 4) / 4, "boy_cizim": round(L, 2), "t": kal,
                                "duvar": "dis" if dis_mi(yon, c, a0, a1) else "ic", "tur": r, "rect": [x0, y0, x1, y1]})
            elif r == "KOSE" and abs(t - 9.9) < 0.4 and abs(L - 9.9) < 0.4 and y0 > 700:
                kolonlar.append([x0, y0, x1, y1])                        # D: sundurmanın iki kolonu (sayfa 4, 10'luk kutu profil 3 mm)
            elif r == "KOSE":
                ozel = abs(x0 - 289.75) < 1 and abs(y0 - 149.94) < 1     # B: L'nin iç köşesi (sayfa 4, "dış köşe direği + profil vidalama aparatı")
                dis = x0 < 10 or x1 > 740 or y0 < 1 or y1 > 680
                koseler.append({"tur": "ozel" if ozel else ("dis" if dis else "ic"), "kal": 10 if t > 4.5 else 6, "rect": [x0, y0, x1, y1]})
            elif r == "KANAT" and 80 < L < 84:
                kanatlar.append([x0, y0, x1, y1])
    olculer = sorted({float(w[4]) for w in pg.get_text("words") if re.fullmatch(r"\d+(\.\d+)?", w[4]) and 20 < float(w[4]) < 260} | {125.5})
    for p in panolar:                                                   # çizimdeki 125,28 / 80,58 gibi sapmalar yazıdaki ölçüye (± 0,4)
        yakin = min(olculer, key=lambda o: abs(o - p["boy_cizim"]))
        p["boy"] = yakin if abs(yakin - p["boy_cizim"]) <= 0.4 else round(p["boy_cizim"] * 4) / 4
    etiket = []
    for w in pg.get_text("words"):
        if re.fullmatch(r"\d+/\d+", w[4]):
            x, y = b((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            etiket.append({"metin": w[4], "x": round(x, 1), "y": round(y, 1)})
    return {"panolar": panolar, "koseler": koseler, "kolonlar": kolonlar, "kanatlar": kanatlar, "etiketler": etiket}


def makaslar() -> dict:
    """Sayfa 7: makaslar camgöbeği çift çizgi (8 cm). Ölçek ve köken gri duvar çizgilerinden: sol dış yüz y_pdf 326,88 (x = 0),
    cumbanın ön dış yüzü x_pdf 268,04 (y = 0); 750 cm = 429,4 pt."""
    pg = fitz.open(PAFTA)[6]
    s7, X0, Y0 = (756.24 - 326.88) / 750, 268.04, 326.88
    yatay, dikey = defaultdict(lambda: [1e9, -1e9]), defaultdict(lambda: [1e9, -1e9])
    for d in pg.get_drawings():
        if tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))) != (0.0, 1.0, 1.0):
            continue
        for it in d["items"]:
            if it[0] != "l":
                continue
            p, q = it[1], it[2]
            if abs(p.y - q.y) < 0.3:                                    # pdf'te yatay → planda y yönünde (ana çatı makası)
                g = yatay[round(p.y, 1)]; g[0] = min(g[0], p.x, q.x); g[1] = max(g[1], p.x, q.x)
            elif abs(p.x - q.x) < 0.3:                                  # pdf'te dikey → planda x yönünde (cumba ve sundurma makası)
                g = dikey[round(p.x, 1)]; g[0] = min(g[0], p.y, q.y); g[1] = max(g[1], p.y, q.y)

    def eksenler(cizgiler, kok):
        ham = sorted((k_, a, b_) for k_, (a, b_) in cizgiler.items() if b_ - a > 60)
        grup = []
        for k_, a, b_ in ham:
            if grup and k_ - grup[-1]["k"][-1] < 6 and abs(b_ - grup[-1]["b"]) < 3:
                grup[-1]["k"].append(k_)
            else:
                grup.append({"k": [k_], "a": a, "b": b_})
        return [{"eksen": round(((g["k"][0] + g["k"][-1]) / 2 - kok) / s7, 1), "bas": round((g["a"] - (X0 if kok == Y0 else Y0)) / s7, 1),
                 "son": round((g["b"] - (X0 if kok == Y0 else Y0)) / s7, 1), "boy": round((g["b"] - g["a"]) / s7, 1)} for g in grup]
    # boyla ayrılır: ana makas 600 (540 + 2 × 30), cumba makası 360, sundurma makası 195,5, iç uçtaki yavru 143,6. Aynı boydaki tek
    # çizgiler (mahya 206 / 750, saçak kenarı 750) makas değil.
    ana = [e for e in eksenler(yatay, Y0) if abs(e["boy"] - 600) < 5]
    kx = eksenler(dikey, X0)
    return {"ana_x": [e["eksen"] for e in ana], "ana_y": [ana[0]["bas"], ana[0]["son"]] if ana else None,
            "cumba_y": [e["eksen"] for e in kx if abs(e["boy"] - 360) < 5], "sundurma_y": [e["eksen"] for e in kx if abs(e["boy"] - 195.5) < 5],
            "yavru": [e for e in kx if abs(e["boy"] - 143.6) < 5], "ham": {"ana": ana, "x_yonu": kx}}


def h_plani() -> dict:
    """Sayfa 3: H türleri renkli dairelerle (lejant sırası: dübelli & kulaklı, dübelli, standart, 3'lü dübelli & kulaklı, 3'lü dübelli,
    3'lü standart). Plandaki daireler türüne göre sayılır; siyah daireler özel profil etiketleri (A, C, F)."""
    pg = fitz.open(PAFTA)[2]
    daire = defaultdict(set)
    for d in pg.get_drawings():
        col = tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9)))
        if any(it[0] == "c" for it in d["items"]):
            r = d["rect"]
            if 8 < r.width < 30 and abs(r.width - r.height) < 1.5:
                daire[col].add((round(r.x0 + r.width / 2), round(r.y0 + r.height / 2)))
    sira = sorted((min(p[0] for p in v if p[1] < 160), col) for col, v in daire.items() if any(p[1] < 160 for p in v))
    adlar = ["kulakli", "dubelli", "standart", "uclu_kulakli", "uclu_dubelli", "uclu_standart"]
    return {ad: len([p for p in daire[col] if p[1] > 480]) for ad, (_x, col) in zip(adlar, sira)}


def eflatun_sayilar(sayfa: int) -> list[float]:
    pg = fitz.open(PAFTA)[sayfa]
    out = []
    for bl in pg.get_text("dict")["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if sp["color"] == 0xFF00FF and re.fullmatch(r"\d+(\.\d+)?", t):
                    out.append(float(t))
    return out


def tavan_omega() -> dict:
    """Sayfa 6 (ters tavan): yatay eflatun ölçüler hat parçaları; dikey 248 / 268,569 / 120 duvar ve sundurma ölçüsü sayılmaz."""
    say = eflatun_sayilar(5)
    parca = [v for v in say if v > 20 and v not in (248.0, 268.569, 120.0)]
    return {"parcalar_cm": parca, "parca": len(parca), "toplam_m": round(sum(parca) / 100, 2), "sayilmayan": [v for v in say if v not in parca]}


def asik() -> dict:
    """Sayfa 9: aşık parçaları (eflatun). Ana çatı iki yüz × 6 sıra (410 + 400; arka yüzde sundurmanın, ön yüzde cumbanın oluğu kesik);
    cumba iki yüz × 4 sıra (155,9 … 326,9), sundurma iki yüz × 2 sıra (167,6 / 224,6)."""
    say = eflatun_sayilar(8)
    c = Counter(say)
    return {"parcalar": {str(k_): v for k_, v in sorted(c.items())}, "toplam_m": round(sum(say) / 100, 2), "parca": len(say)}


ODALAR = [  # (ad, tür, [x0, y0, x1, y1]); ters tavan omegası mahyaya (x) paralel → en = x boyu, derin = y boyu (sayfa 1 alanlarıyla)
    ("BANYO", "banyo", [9.91, 431.76, 190.01, 679.68]),                    # 180,25 × 248 = 4,47 ✓
    ("GİRİŞ", "antre_hol", [195.96, 431.76, 378.26, 679.68]),              # 182,25 × 248 = 4,52 (paftada 4,51)
    ("SALON & MUTFAK", "salon", [384.21, 160.07, 739.35, 679.68]),          # 355,5 × 520 (+ aşağıdaki şerit = 20,15 ✓)
    ("SALON & MUTFAK", "salon", [321.46, 160.07, 384.21, 425.82]),          # 62,75 × 266
    ("YATAK ODASI", "yatak_odasi", [9.91, 160.07, 315.51, 425.82]),         # 305,6 × 265,75
    ("YATAK ODASI", "yatak_odasi", [9.91, 10.13, 289.75, 160.07]),          # cumba 280 × 150 (toplam 12,32; paftada 12,33)
]
SUNDURMA = [188.0, 689.6, 323.5, 819.5]                                    # 135,5 × 130 = 1,76 ✓ (kolonlar D)


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
    # kulaklı H: makasın denk geldiği dış ek (sayfa 3 lejantı). Ana makaslar y yönünde → ayakları x yönündeki dış duvarlarda (arka, sağ
    # bölümün önü); cumba makasları x yönünde → ayakları sol duvar ve cumbanın sağ duvarında (y < 160)
    for e in M["ekler"]:
        x, y = e["yer"]
        if e["duvar"] != "dis":
            e["sacak"] = False
            continue
        yan = abs(x - 4.955) < 1 or abs(x - 744.415) < 1 or (abs(x - 294.705) < 1 and y < 160)   # y yönündeki dış duvar
        arka_on = not yan and (abs(y - 684.635) < 1 or (abs(y - 155.005) < 1 and x >= 289))       # sol duvarın y 155 eki (A) değil
        yan_cumba = yan and y < 160
        e["sacak"] = bool((arka_on and any(abs(x - m) <= 2.0 for m in mk["ana_x"])) or (yan_cumba and any(abs(y - m) <= 2.0 for m in mk["cumba_y"])))
    kos = Counter(k_["tur"] if k_["tur"] != "ic" else f"ic{k_['kal']}" for k_ in M["koseler"])
    hp, to, as_ = h_plani(), tavan_omega(), asik()
    (BURASI / "pafta_montaj.json").write_text(json.dumps({"kaynak": "DIAMOND 45 M2 MONTAJ PAFTASI.pdf (12 sayfa)", "cerceve": __doc__.split("Çerçeve: ")[1].split("\n")[0],
                                                          "montaj_plani": M, "makaslar": mk, "h_plani": hp, "tavan_omega": to, "asik": as_},
                                                         ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    kapali = [{"ad": a, "tur": t, "alan_m2": round((r[2] - r[0]) * (r[3] - r[1]) / 1e4, 3), "en_cm": round(r[2] - r[0], 2), "derin_cm": round(r[3] - r[1], 2)}
              for a, t, r in ODALAR]
    sund = {"ad": "SUNDURMA", "tur": "veranda", "alan_m2": round((SUNDURMA[2] - SUNDURMA[0]) * (SUNDURMA[3] - SUNDURMA[1]) / 1e4, 3),
            "en_cm": round(SUNDURMA[2] - SUNDURMA[0], 2), "derin_cm": round(SUNDURMA[3] - SUNDURMA[1], 2)}
    eg = round(math.tan(math.radians(18.2)) * 100, 1)
    # kapalı bina: 750 × 540 (y 150–690) + cumba 300 × 150; dış çevre sol 690 + arka 750 + sağ 540 + sağ ön 450 + basamak 150 + cumba önü 300
    yp = {"kod": "TS-01", "is_emri_no": "TS01-DIAMOND-45M2 (pafta kipi)", "H0": 250.0, "W": 749.48, "D": 689.59,
          "brut_m2": round((749.48 * (689.59 - 149.94) + 299.66 * 149.94) / 1e4, 3),
          "dis_cevre_m": round((689.59 + 749.48 + (689.59 - 149.94) + (749.48 - 289.75) + 149.94 + 299.66) / 100, 3), "t_dis": 10.0,
          "panolar": [{"duvar": p["duvar"], "kal_mm": round(p["t"] * 10), "boy": p["boy"],
                       "aciklik": None if not p.get("aciklik") else {k_: v for k_, v in p["aciklik"].items() if k_ in ("tur", "olcu", "genislik", "mentese")}}
                      for p in M["panolar"]],
          "ekler": [{k_: e[k_] for k_ in ("duvar", "cins", "sacak")} for e in M["ekler"]],
          "koseler": {"dis": kos.get("dis", 0), "ic": kos.get("ic6", 0), "ozel": kos.get("ozel", 0)}, "dikmeler": len(M["kolonlar"]),
          "kolon_boylari_cm": [250.0, 250.0],                             # sayfa 4: D, 10'luk kutu profil 3 mm, 250, 2 adet
          "ic_kalan_dis_duvar_m": 0.0,                                     # bütün dış duvarlar saçak ya da kalkan altında
          "veranda_kirisleri_cm": [],                                      # sundurmada kiriş özel profil listesinde yok (yalnız D kolonları)
          "kapali": kapali, "acik": [sund],
          "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 540.0, "boy_cm": 750.0, "egim_yuzde": eg, "sacak_cm": 30.0, "kalkan": 2,
                    "kalkan_duvar_cm": 540.0 + 540.0, "sacak_hatlari_m": [8.1, 4.5],
                    "not": "sayfa 1 / 7 / 9: 600 açıklık (540 + 2 × 30), 18,2°, eğik 315,8, mahya x yönünde 810; MK01–MK08 (x 4 … 746); "
                           "ön saçak yalnız sağ bölümün önünde (x 330–780, 4,5 m), solda cumba çatısı; sol ve sağ kalkan duvarı 540"},
                   {"ad": "cumba", "tip": "besik", "aciklik_cm": 300.0, "boy_cm": 150.0, "egim_yuzde": eg, "sacak_cm": 30.0, "kalkan": 1,
                    "mahya_boy_cm": 236.0, "kalkan_duvar_cm": 300.0, "sacak_hatlari_m": [1.5, 1.5],
                    "not": "yatak odasının öne çıkıntısı üstünde ana çatıya dik (çapraz) beşik: 360 açıklık, 18,2°, eğik 189,48, yükseklik 69,18; "
                           "MK11 (ön kalkan, y 4) ve MK12 (y 72,9), iç uçta MK13 (y 201,7); mahya x 150'de y −30 … 206"},
                   {"ad": "sundurma", "tip": "besik", "aciklik_cm": 135.5, "boy_cm": 130.0, "egim_yuzde": round(42.14 / 97.75 * 100, 1), "sacak_cm": 30.0,
                    "kalkan": 1, "acik": True, "mahya_boy_cm": 160.0, "sacak_hatlari_m": [1.6, 1.6],
                    "not": "arka dış kapının önünde iki kolonlu (D) küçük çapraz beşik: 195,5 açıklık, yükseklik 42,14; MK09, MK10; altı açık"}],
          "ozellikler": {"Panel Türü": "Pres Panel", "Çatı Şekli": "Beşik + Cumba", "Çatı Kaplaması": "OSB + Nem Bariyeri + Metal Kiremit",
                         "Çatı Kaplama Rengi": "Bordo", "Dış Kapı": "Çelik Standart", "İç Kapılar": "Standart Amerikan",
                         "Dış Cephe Boya": "Polisan", "İç Cephe Boya": "Polisan", "Pencere Rengi": "Alıcıya ait", "Tavan": "Ters",
                         "Saçak ve Alın Rengi": "Bordo", "Yağmur İniş Borusu": "Metal",
                         "Açıklama": "1- İç cephe alçıpan kaplama olacak. 2- Çatı izolasyon mineral yün 3- Yağmur inişleri metal (antrasit gri) olacak. "
                                     "4- Dış cephede mastik olacak. 5- Çatı müdahale kapağı gidecek."},
          "alici_ait": {"kalemler": ["pencere"], "kaynak": "özellik tablosu \"Pencere Rengi: ALICIYA AİT\""},
          "kaynak_notu": "deneme/2026-10-13_ts_01/pafta_oku.py; Motor çizemiyor (L plan, çapraz cumba, sundurma, 251 / 290'lık pencereli özel pano)"}
    (BURASI / "yapi_pafta.json").write_text(json.dumps(yp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet = {"pano": len(M["panolar"]), "dis": sum(p["duvar"] == "dis" for p in M["panolar"]), "ic": sum(p["duvar"] == "ic" for p in M["panolar"]),
            "kose": dict(kos), "kolon": len(M["kolonlar"]),
            "kapi": dict(Counter((p.get("aciklik") or {}).get("tur") for p in M["panolar"] if (p.get("aciklik") or {}).get("tur", "").endswith("kapi"))),
            "ek": {f"{d}|{c}|" + ("kulaklı" if s else "-"): n for (d, c, s), n in Counter((e["duvar"], e["cins"], e["sacak"]) for e in M["ekler"]).items()},
            "h_plani_pafta": hp}
    print(json.dumps(ozet, ensure_ascii=False))
    print("makas", {k_: v for k_, v in mk.items() if k_ != "ham"}, "\ntavan omega", to["parca"], "parça", to["toplam_m"], "m; aşık", as_)
    for p in M["panolar"]:
        if p.get("aciklik"):
            print("  ", p["yon"], p["c"], (round(p["a0"], 1), round(p["a1"], 1)), p["boy"], p["duvar"], p["aciklik"]["tur"], p["aciklik"].get("olcu"), p["aciklik"].get("mentese", ""))
    print("boylar", dict(Counter(f"{p['duvar']} {p['t']:g} {p['boy']}" for p in M["panolar"])))
    print("brüt", yp["brut_m2"], "çevre", yp["dis_cevre_m"], "odalar", [(o["ad"], o["alan_m2"]) for o in kapali], "sundurma", sund["alan_m2"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
