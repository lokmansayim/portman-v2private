"""PK-03 montaj paftası setinin vektör okuması (13 Ekim 2026; İE-11 PR-2, kör test adım 1; pafta kipi).

Doğan Prefabrik 80 m² (Nimet Bey; Loftev şablonu, çizen Ebru Balcı / Batuhan Tınmaz, 17 Eylül 2025). Motor bu planı çizemiyor
(160/180 pencere iki modüllük 251'lik panoda; L plan; mutfak önde çıkıntılı; verandaya çapraz beşik), bu yüzden geometri doğrudan
paftadan okunur (Lokman 13.10 11:45, "ikisi birden"). Çıktılar:
  - `pafta_montaj.json`: ham okuma (panolar, köşe parçaları, kapı kanatları, pencere etiketleri, ekler);
  - `yapi_pafta.json`: liste üretecinin (sürüm 3) pafta kipi girdisi;
Çerçeve: cm; x soldaki dış yüzden, y verandanın ön yüzünden (y = 0 veranda önü, arka duvar 888,7–898,7).
Renkler: siyah dörtgen = pano (125,5 ve kesik), kırmızı = 62,75'lik özel pano ve köşe parçası (5 × 10 dış, 3 × 6 iç), mavi = pencere
karkas işareti, lacivert 82 × 4 = kapı kanadı (açık konumda). Ölçek 180,8 pt = 125,5 cm.

Koşma: python3 -I deneme/2026-10-13_pk_03/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz

BURASI = Path(__file__).resolve().parent
K = BURASI / "kaynak"
S = 180.8 / 125.5                   # pt / cm
X0_PDF, Y0_PDF = 653.6, 864.8       # x_pdf = veranda önü, y_pdf = sol dış yüz (sayfa 270° döndürülmüş)
W_CM = 951.5
RENK = {(0.0, 0.0, 0.0): "SIYAH", (1.0, 0.0, 0.0): "KIRMIZI", (0.0, 0.0, 1.0): "MAVI", (0.047, 0.275, 0.592): "KANAT"}
TOL = 1.2


def b(xp, yp):
    return (yp - Y0_PDF) / S, (xp - X0_PDF) / S


def dortgenler(pg):
    out = []
    for d in pg.get_drawings():
        r = RENK.get(tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))))
        if not r:
            continue
        for it in d["items"]:
            if it[0] == "qu":
                q = it[1].rect
                (xa, ya), (xb, yb) = b(q.x0, q.y0), b(q.x1, q.y1)
                x0, x1 = sorted((xa, xb)); y0, y1 = sorted((ya, yb))
                if x1 <= W_CM + 1:
                    out.append((r, round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)))
    return out


def montaj() -> dict:
    pg = fitz.open(K / "PK03_MONTAJ_VE_ELEKTRIK_PLANI.pdf")[0]
    D = dortgenler(pg)
    panolar, koseler, karkas, kanatlar = [], [], [], []
    for r, x0, y0, x1, y1 in D:
        w, h = x1 - x0, y1 - y0
        t, L = min(w, h), max(w, h)
        if r in ("SIYAH", "KIRMIZI") and L > 20 and (abs(t - 10) < 0.4 or abs(t - 6) < 0.4):
            yon = "x" if w > h else "y"
            panolar.append({"yon": yon, "c": round((y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2, 2), "a0": x0 if yon == "x" else y0,
                            "a1": x1 if yon == "x" else y1, "boy": round(L, 2), "t": round(t, 1), "duvar": "dis" if t > 8 else "ic",
                            "tur": "OZEL" if r == "KIRMIZI" else "STD", "rect": [x0, y0, x1, y1]})
        elif r == "KIRMIZI" and L <= 11 and t < 9:          # 10 × 10 kırmızı = veranda dikmesi (köşe değil)
            koseler.append({"tur": "dis" if abs(t - 5) < 0.5 else "ic", "rect": [x0, y0, x1, y1]})
        elif r == "MAVI":
            karkas.append([x0, y0, x1, y1])
        elif r == "KANAT" and 80 < L < 84:
            kanatlar.append([x0, y0, x1, y1])
    etiket = []
    for w in pg.get_text("words"):
        if re.fullmatch(r"\d+/\d+", w[4]):
            x, y = b((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            etiket.append({"metin": w[4], "x": round(x, 1), "y": round(y, 1)})
    return {"panolar": panolar, "koseler": koseler, "karkas_isaretleri": karkas, "kanatlar": kanatlar, "etiketler": etiket}


def pencereler(M) -> None:
    """Etiket → en yakın dış duvardaki, etiketin boyuna göre izdüşümünü içeren pano. Ölçü pencere görünüşlerinden: 60/60 yazısı
    görünüşte "60/40, 1 adet" (yazım farkı; 60/40 alındı)."""
    for e in M["etiketler"]:
        olcu = {"60/60": "60x40"}.get(e["metin"], e["metin"].replace("/", "x"))
        aday = []
        for p in M["panolar"]:
            if p["duvar"] != "dis":
                continue
            boy_eks = e["x"] if p["yon"] == "x" else e["y"]
            dik = abs((e["y"] if p["yon"] == "x" else e["x"]) - p["c"])
            if p["a0"] - 5 <= boy_eks <= p["a1"] + 5:
                aday.append((dik, p))
        dik, p = min(aday, key=lambda t: t[0])
        p["aciklik"] = {"tur": "pencere", "olcu": olcu, "genislik": float(olcu.split("x")[0]), "kaynak": f"etiket {e['metin']} ({e['x']}, {e['y']})"}


def kapilar(M) -> None:
    """Kanat (açık, 82 × 4) → menteşe ucunun değdiği duvar ve boşluğun tümüyle içinde kaldığı pano. Menteşe adı Motor'la aynı sözleşme:
    açılma yönünde yürürken menteşe solda mı sağda mı (PK-02'de banyo kapısıyla sınandı: "sag")."""
    for k_ in M["kanatlar"]:
        x0, y0, x1, y1 = k_
        dikey = (y1 - y0) > (x1 - x0)
        xl, yl = (x0 + x1) / 2, (y0 + y1) / 2
        uclar = [(xl, y0), (xl, y1)] if dikey else [(x0, yl), (x1, yl)]
        bulundu = None
        for hx, hy in uclar:
            for p in M["panolar"]:
                if p["yon"] == ("x" if dikey else "y") and abs((hy if dikey else hx) - p["c"]) <= p["t"] / 2 + TOL:
                    ek = hx if dikey else hy
                    for lo, hi in ((ek - 82, ek), (ek, ek + 82)):
                        if p["a0"] - TOL <= lo and hi <= p["a1"] + TOL and p.get("aciklik") is None:
                            bulundu = (p, lo, hi, ek, (hx, hy))
                            break
                if bulundu:
                    break
            if bulundu:
                break
        p, lo, hi, ek, (hx, hy) = bulundu
        diger = (xl, y1 if hy == y0 else y0) if dikey else (x1 if hx == x0 else x0, yl)
        n = (0, 1 if diger[1] > hy else -1) if dikey else (1 if diger[0] > hx else -1, 0)    # açılma yönü
        sol = (-n[1], n[0])                                                                  # yürüme yönünün solu
        orta = (lo + hi) / 2
        h = (ek - orta, 0) if dikey else (0, ek - orta)
        mentese = "sol" if h[0] * sol[0] + h[1] * sol[1] > 0 else "sag"
        p["aciklik"] = {"tur": "kapi?", "olcu": "82", "genislik": 82.0, "mentese": mentese, "bosluk": [round(lo, 1), round(hi, 1)],
                        "acilma": n, "kaynak": f"kanat {[round(v, 1) for v in k_]}"}


def ekler(M) -> list:
    """Aynı hattaki ardışık iki pano arasındaki her ek; o noktaya dik bir duvar değiyorsa üçlü H (T), değmiyorsa pano eki. Saçak
    duvarı = mahyaya (x) paralel dış duvar."""
    hat = {}
    for p in M["panolar"]:
        hat.setdefault((p["yon"], round(p["c"] * 2) / 2), []).append(p)
    cik = []
    for (yon, c), ps in hat.items():
        ps.sort(key=lambda p: p["a0"])
        for a, b_ in zip(ps, ps[1:]):
            if abs(a["a1"] - b_["a0"]) > TOL:
                continue
            j = a["a1"]
            t = a["t"]
            T = any(q["yon"] != yon and abs(q["c"] - j) <= q["t"] / 2 + TOL and
                    (abs(q["a0"] - (c + t / 2)) <= TOL + 0.5 or abs(q["a1"] - (c - t / 2)) <= TOL + 0.5) for q in M["panolar"])
            cik.append({"duvar": a["duvar"], "cins": "uclu" if T else "pano_eki", "sacak": yon == "x" and a["duvar"] == "dis",
                        "yer": [round(j, 1) if yon == "x" else c, c if yon == "x" else round(j, 1)]})
    return cik


ODALAR = [  # paftadaki duvar iç yüzlerinden (montaj planı; tavan omega planındaki ölçülerle aynı: 242,96 / 307,79 / 368,5 / 310,75 / 240 / 182,25)
    ("SALON", "salon", [[10, 261.1, 253.0, 888.7], [259.0, 261.1, 378.6, 506.1]]),
    ("YATAK ODASI 1", "yatak_odasi", [[259.0, 512.1, 566.9, 888.7]]),
    ("YATAK ODASI 2", "yatak_odasi", [[572.9, 577.9, 941.5, 888.7], [572.9, 512.1, 695.5, 577.9]]),
    ("HOL", "antre_hol", [[384.6, 389.6, 695.5, 506.1], [384.6, 261.1, 506.1, 389.6]]),
    ("BANYO", "banyo", [[701.5, 389.6, 941.5, 571.9]]),
    ("MUTFAK", "mutfak", [[512.1, 135.5, 941.5, 383.6]]),
]
VERANDA = [10.0, 10.0, 502.1, 251.1]


def oda_kayitlari():
    out = []
    for ad, tur, rects in ODALAR:
        for r in rects:            # her dikdörtgen ayrı kayıt (omega hatları dikdörtgen başına); alan toplamı odanın alanı
            out.append({"ad": ad, "tur": tur, "alan_m2": round((r[2] - r[0]) * (r[3] - r[1]) / 1e4, 3), "en_cm": round(r[2] - r[0], 2),
                        "derin_cm": round(r[3] - r[1], 2), "rect": r})
    return out


def tavan_omega() -> dict:
    pg = fitz.open(K / "PK03_TAVAN_OMEGA_YERLESIM_PLANI.pdf")[0]
    w = [x[4] for x in pg.get_text("words")]
    sayi = [float(v) for i, v in enumerate(w) if re.fullmatch(r"\d+(\.\d+)?", v) and (i + 1 >= len(w) or w[i + 1] not in ("cm", "mm"))]
    parca = [v for v in sayi if v > 20 and v not in (60.0, 100.0, 2500.0)]
    return {"parcalar_cm": parca, "parca": len(parca), "toplam_m": round(sum(parca) / 100, 2)}


def main() -> int:
    M = montaj()
    pencereler(M)
    kapilar(M)
    # dış kapı: veranda / dışarı ile hol arasındaki duvarda (salon-hol ön duvarı, y 251–261) — öteki beşi iç kapı
    for p in M["panolar"]:
        a = p.get("aciklik")
        if a and a["tur"] == "kapi?":
            a["tur"] = "dis_kapi" if p["duvar"] == "dis" else "ic_kapi"
            if a["tur"] == "dis_kapi":
                a["genislik"] = 90.0; a["olcu"] = "90"; a["not"] = "kanat 82 çizilmiş; ölçü yaydan okunmaz (PK-02 dersi), K04: 90"
    M["ekler"] = ekler(M)
    kos = Counter(k_["tur"] for k_ in M["koseler"])
    ozet = {"pano": len(M["panolar"]), "dis": sum(p["duvar"] == "dis" for p in M["panolar"]), "ic": sum(p["duvar"] == "ic" for p in M["panolar"]),
            "kose": dict(kos), "pencere": sum(1 for p in M["panolar"] if (p.get("aciklik") or {}).get("tur") == "pencere"),
            "kapi": Counter((p.get("aciklik") or {}).get("tur") for p in M["panolar"] if (p.get("aciklik") or {}).get("tur", "").endswith("kapi")),
            "ek": {f"{d}|{c}|" + ("saçak" if s else "kalkan"): n for (d, c, s), n in Counter((e["duvar"], e["cins"], e["sacak"]) for e in M["ekler"]).items()}}
    (BURASI / "pafta_montaj.json").write_text(json.dumps({"kaynak": "PK03_MONTAJ_VE_ELEKTRIK_PLANI.pdf (17 Eylül 2025)", "cerceve": __doc__.split("Çerçeve: ")[1].split("\n")[0],
                                                          "montaj_plani": M, "tavan_omega": tavan_omega()}, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    kapali = oda_kayitlari()
    ver = {"ad": "VERANDA", "tur": "veranda", "alan_m2": round((VERANDA[2] - VERANDA[0]) * (VERANDA[3] - VERANDA[1]) / 1e4, 3),
           "en_cm": round(VERANDA[2] - VERANDA[0], 2), "derin_cm": round(VERANDA[3] - VERANDA[1], 2)}
    # kapalı bina dış çevresi: sol 647,6 + arka 951,5 + sağ 773,2 + mutfak önü 449,4 + basamak 125,6 + salon önü 502,1
    cevre = (898.7 - 251.1) + 951.5 + (898.7 - 125.5) + (951.5 - 502.1) + (251.1 - 125.5) + 502.1
    kapali_brut = 951.5 * (898.7 - 125.5) - 502.1 * (251.1 - 125.5)
    yp = {"kod": "PK-03", "is_emri_no": "PK03-DOGAN-80M2 (pafta kipi)", "H0": 250.0, "W": W_CM, "D": 898.7,
          "brut_m2": round((kapali_brut + 502.1 * (251.1 - 0)) / 1e4, 3), "dis_cevre_m": round(cevre / 100, 3), "t_dis": 10.0,
          "panolar": [{"duvar": p["duvar"], "kal_mm": round(p["t"] * 10), "boy": round(round(p["boy"] * 4) / 4, 2),
                       "aciklik": None if not p.get("aciklik") else {k_: v for k_, v in p["aciklik"].items() if k_ in ("tur", "olcu", "genislik", "mentese")}}
                      for p in M["panolar"]],
          "ekler": [{k_: e[k_] for k_ in ("duvar", "cins", "sacak")} for e in M["ekler"]],
          "koseler": dict(kos), "dikmeler": 2, "veranda_kirisleri_cm": [502.1 - 10, 251.1 - 10, 125.5 - 10],
          "kapali": [{k_: v for k_, v in o.items() if k_ != "rect"} for o in kapali], "acik": [ver],
          "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 773.2, "boy_cm": 951.5, "egim_yuzde": 30.0, "sacak_cm": 30.0, "kalkan": 2,
                    "sacak_hatlari_m": [10.115, 4.46], "not": "makas ve dere planı: 1011 × 833, 9 makas (MK01–MK09); eğim paftada yok, trapez boyundan (440 − 5 taşma) %30"},
                   {"ad": "veranda çatısı", "tip": "besik", "aciklik_cm": 505.0, "boy_cm": 96.0, "egim_yuzde": 44.0, "sacak_cm": 30.0, "kalkan": 1,
                    "mahya_boy_cm": 156.0, "sacak_hatlari_m": [1.56, 1.56],
                    "not": "çapraz beşik (MK10, MK11; 565 × 156); mahya ana çatının mahyasıyla aynı yükseklikte varsayıldı (aşık planı: yüz başına 6 sıra)"}],
          "ozellikler": {"Panel Türü": "Poliüretan Panel", "Çatı Şekli": "Beşik", "Çatı Kaplaması": "Trapez", "Çatı Kaplama Rengi": "Kırmızı",
                         "Dış Kapı": "Çelik", "İç Kapılar": "Amerikan Panel", "Dış Cephe Boya": "Sandeco", "İç Cephe Boya": "Sandeco",
                         "Tavan": "Ters tavan", "Saçak Rengi": "Antrasit", "Saçak Çıkması": "30 cm", "Yağmur Oluğu": "Metal",
                         "Yağmur İniş Borusu": "Metal", "Açıklama": "İç cephede alçıpan kaplama yapılacaktır."},
          "alici_ait": {"kalemler": [], "kaynak": "paftanın özellik tablosu ve açıklaması: alıcıya ait kalem yazılmamış"},
          "kaynak_notu": "deneme/2026-10-13_pk_03/pafta_oku.py; Motor çizemiyor (160/180 iki modüllük pano, L plan, çapraz beşik)"}
    (BURASI / "yapi_pafta.json").write_text(json.dumps(yp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(ozet, ensure_ascii=False, default=str))
    print("brüt", yp["brut_m2"], "m²; kapalı", round(kapali_brut / 1e4, 2), "m²; dış çevre", yp["dis_cevre_m"], "m; tavan omega", tavan_omega()["toplam_m"], "m")
    for p in M["panolar"]:
        if p.get("aciklik"):
            print("  ", p["yon"], p["c"], (round(p["a0"], 1), round(p["a1"], 1)), p["boy"], p["aciklik"]["tur"], p["aciklik"].get("olcu"), p["aciklik"].get("mentese", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
