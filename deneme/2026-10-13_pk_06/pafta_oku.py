"""PK-06 montaj paftası setinin vektör okuması (13 Ekim 2026; İE-11 PR-2, kör test adım 1; pafta kipi).

Sevim Güler 82 + 10 m² (Çorlu; Mehmet Yıldırım bayisi; Loftev şablonu, onay paftası "PROJE ADI XXX"). Sekiz sayfa:
1 müşteri onay (özellik tablosu), 2 montaj planı, 3 tavan omega, 4–5 makas ve dere, 6 aşık, 7 çatı kaplaması, 8 elektrik.
Motor çizemiyor (L plan: salon soldan 188,25 taşıyor, önünde veranda; 160/180 pencereler iki modüllük 251'lik panoda; verandaya ana çatıya
paralel ikinci beşik). Pano geometrisi doğrudan paftanın vektörlerinden okunur (Lokman 13.10 11:45, "ikisi birden").
Çıktılar: `pafta_montaj.json` (ham okuma) ve `yapi_pafta.json` (liste üretecinin pafta kipi girdisi).
Çerçeve: cm; x salonun sol dış yüzünden (veranda dikmeleri x = −120,3), y ana bloğun ön dış yüzünden (y = 0 ön, arka duvar 762,9–773).
Renkler (sayfa 2): turuncu dörtgen = 125,5'lik ve kesik pano, zeytin = özel pano (62,75 / 60,75 / 49,75), siyah kapalı çizgi = 251'lik
iki modüllük pencere panosu, kırmızı = köşe (5 × 10 dış, 3 × 6 iç, 10 × 10 veranda dikmesi), lacivert 82 × 4 = kapı kanadı (açık).
Ölçek 568,2 pt = 1139,5 cm (ön–arka 9 pano 62,58 pt). Sayfa 270° döndürülmüş: x = (y_pdf − Y0) / S, y = (x_pdf − X0) / S.

Koşma: python3 -I deneme/2026-10-13_pk_06/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
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
S = 568.2 / 1139.5                  # pt / cm
X0_PDF, Y0_PDF = 274.4, 272.76      # x_pdf = ana bloğun ön yüzü, y_pdf = salonun sol dış yüzü
RENK = {(0.949, 0.404, 0.133): "STD", (0.784, 0.788, 0.176): "OZEL", (1.0, 0.0, 0.0): "KOSE", (0.047, 0.275, 0.592): "KANAT"}
_pk03 = importlib.util.spec_from_file_location("pk03_oku", BURASI.parent / "2026-10-13_pk_03" / "pafta_oku.py")
PK03 = importlib.util.module_from_spec(_pk03); _pk03.loader.exec_module(PK03)        # pencereler(), kapilar(), ekler() ve menteşe sözleşmesi ortak


def b(xp, yp):
    return (yp - Y0_PDF) / S, (xp - X0_PDF) / S


def _kutu(xa, ya, xb, yb):
    (p, q), (r, s) = b(xa, ya), b(xb, yb)
    x0, x1 = sorted((p, r)); y0, y1 = sorted((q, s))
    return round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)


def _boy(L: float, olculer: list[float]) -> float:
    """Pano boyu: paftadaki ölçü yazısına (± 0,35) ya da 125,5'e oturt; yoksa 0,25'e yuvarla. Çizimdeki 62,57 / 49,57 gibi sapmalar
    yazıdaki 62,75 / 49,75'e gider (yazı esastır)."""
    for o in olculer + [125.5]:
        if abs(L - o) <= 0.35:
            return o
    return round(L * 4) / 4


def montaj() -> dict:
    pg = fitz.open(K / "PK06_2.pdf")[0]
    olculer = sorted({float(w[4]) for w in pg.get_text("words") if re.fullmatch(r"\d+\.\d+|\d{2,3}", w[4]) and float(w[4]) < 260})
    panolar, koseler, dikmeler, kanatlar = [], [], [], []

    def pano(tur, x0, y0, x1, y1):
        w, h = x1 - x0, y1 - y0
        t, L = min(w, h), max(w, h)
        yon = "x" if w > h else "y"
        panolar.append({"yon": yon, "c": round((y0 + y1) / 2 if yon == "x" else (x0 + x1) / 2, 2), "a0": x0 if yon == "x" else y0,
                        "a1": x1 if yon == "x" else y1, "boy": _boy(L, olculer), "boy_cizim": round(L, 2), "t": round(t, 1),
                        "duvar": "dis" if t > 8 else "ic", "tur": tur, "rect": [x0, y0, x1, y1]})

    for d in pg.get_drawings():
        r = RENK.get(tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))))
        if r is None and tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))) == (0.0, 0.0, 0.0):
            # siyah kapalı çizgi: 251'lik pencere panosu (kesit profilleri plan dışında, x > 1300 ya da x < −200)
            noktalar = [b(it[1].x, it[1].y) for it in d["items"] if it[0] == "l"] + [b(it[2].x, it[2].y) for it in d["items"] if it[0] == "l"]
            xs, ys = [p[0] for p in noktalar], [p[1] for p in noktalar]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            if -5 < x0 and x1 < 1145 and abs(min(x1 - x0, y1 - y0) - 10) < 0.5 and max(x1 - x0, y1 - y0) > 200:
                pano("PENCERE_251", round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2))
            continue
        if not r:
            continue
        for it in d["items"]:
            if it[0] != "qu":
                continue
            q = it[1].rect
            x0, y0, x1, y1 = _kutu(q.x0, q.y0, q.x1, q.y1)
            w, h = x1 - x0, y1 - y0
            t, L = min(w, h), max(w, h)
            if r in ("STD", "OZEL") and L > 20 and (abs(t - 10) < 0.4 or abs(t - 6) < 0.4):
                pano(r, x0, y0, x1, y1)
            elif r == "KOSE" and abs(t - 9.9) < 0.3 and abs(L - 9.9) < 0.3:
                dikmeler.append([x0, y0, x1, y1])                       # 10 × 10: veranda dikmesi
            elif r == "KOSE" and L <= 11:
                koseler.append({"tur": "dis" if abs(t - 5) < 0.5 else "ic", "rect": [x0, y0, x1, y1]})
            elif r == "KANAT" and 80 < L < 84:
                kanatlar.append([x0, y0, x1, y1])
    etiket = []
    for w in pg.get_text("words"):
        if re.fullmatch(r"\d+/\d+", w[4]):
            x, y = b((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
            etiket.append({"metin": w[4], "x": round(x, 1), "y": round(y, 1)})
    return {"panolar": panolar, "koseler": koseler, "dikmeler": dikmeler, "kanatlar": kanatlar, "etiketler": etiket, "olcu_yazilari": olculer}


def tavan_omega() -> dict:
    """Sayfa 3: omega parçalarının ölçü yazıları eflatun (0xff00ff); plan ölçüleri siyah (ayıklanır)."""
    pg = fitz.open(K / "PK06_3.pdf")[0]
    parca = []
    for bl in pg.get_text("dict")["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln["spans"]:
                if sp["color"] == 0xFF00FF and re.fullmatch(r"\d+(\.\d+)?", sp["text"].strip()):
                    parca.append(float(sp["text"]))
    return {"parcalar_cm": parca, "parca": len(parca), "toplam_m": round(sum(parca) / 100, 2)}


def asik() -> dict:
    """Sayfa 6: ana çatının iki yüzü 8'er sıra × (410 + 410 + 379,5) = 1199,5 (1139,5 + 2 × 30 saçak); ön yüzün alt dört sırası verandanın
    üstüne 120,25 (bir sırada 127,75) uzar (veranda çatısının ön yüzü ana çatının ön yüzüyle aynı düzlemde); veranda çatısının arka yüzü
    ayrı: 4 sıra × 150,25."""
    pg = fitz.open(K / "PK06_6.pdf")[0]
    sayi = [float(w[4]) for w in pg.get_text("words") if re.fullmatch(r"\d+(\.\d+)?", w[4]) and w[4] != "60"]
    c = Counter(sayi)
    boy_420 = c[410.0] + c[379.5] + math.ceil((c[120.25] + c[127.75]) / 3) + math.ceil(c[150.25] / 2)    # kesim: 4200'lük boydan
    return {"parcalar": {str(k_): v for k_, v in sorted(c.items())}, "toplam_m": round(sum(sayi) / 100, 2), "boy_4200": boy_420}


def kaplama() -> dict:
    """Sayfa 7: tek kat panel şeritleri 43,32 pt (87 cm) × 221,52 pt (444,9 cm); arka yüz 14, ön yüz 16 (verandaya uzayan iki şerit dahil).
    Veranda çatısının arka yüzü (207 × 150) şeritsiz çizilmiş; ön yüzün iki uç şeridinden bir ok ona gidiyor (artan parça oraya)."""
    pg = fitz.open(K / "PK06_7.pdf")[0]
    serit = [it[1].rect for d in pg.get_drawings() if tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9))) == (1.0, 0.0, 1.0)
             for it in d["items"] if it[0] == "qu"]
    olcek = 597.24 / 1199.5                     # arka yüzün çatı boyu 597,24 pt = 1199,5 cm
    return {"serit": len(serit), "en_cm": round(serit[0].height / olcek, 1), "boy_cm": round(serit[0].width / olcek, 1)}


ODALAR = [  # duvar iç yüzlerinden (sayfa 2), adlar sayfa 8 (elektrik planı: eşyalar ve yazılar)
    ("SALON", "salon", [[9.9, 389.4, 503.9, 762.9], [9.9, 333.8, 192.0, 389.4]]),
    ("HOL", "antre_hol", [[509.9, 389.4, 880.3, 509.0]]),
    ("ÇAMAŞIR ODASI", "camasir", [[886.3, 389.4, 1129.4, 509.0]]),       # "k.m." "ç.m." prizleri, 60/40 pencere
    ("BANYO", "banyo", [[509.9, 515.0, 692.1, 762.9]]),
    ("YATAK ODASI 1", "yatak_odasi", [[698.1, 515.0, 1129.4, 762.9]]),
    ("MUTFAK", "mutfak", [[198.1, 9.9, 503.9, 383.4]]),
    ("YATAK ODASI 2", "yatak_odasi", [[509.9, 9.9, 754.9, 383.4]]),
    ("YATAK ODASI 3", "yatak_odasi", [[761.0, 9.9, 1129.4, 383.4]]),
]
VERANDA = [-110.5, 9.9, 188.2, 323.7]      # dikme iç yüzü → ana bloğun dış köşesi; ön dikmeden salon duvarına (298,5 × 313,75)


def oda_kayitlari():
    out = []
    for ad, tur, rects in ODALAR:
        for r in rects:
            out.append({"ad": ad, "tur": tur, "alan_m2": round((r[2] - r[0]) * (r[3] - r[1]) / 1e4, 3), "en_cm": round(r[2] - r[0], 2),
                        "derin_cm": round(r[3] - r[1], 2), "rect": r})
    return out


def main() -> int:
    M = montaj()
    PK03.pencereler(M)
    PK03.kapilar(M)
    for p in M["panolar"]:
        a = p.get("aciklik")
        if a and a["tur"] == "kapi?":
            a["tur"] = "dis_kapi" if p["duvar"] == "dis" else "ic_kapi"
            if a["tur"] == "dis_kapi":
                a["genislik"] = 90.0; a["olcu"] = "90"; a["not"] = "kanat 82 çizilmiş; çelik dış kapı listede 900 × 2000 (L4)"
        if a and a["tur"] == "pencere" and p["tur"] == "PENCERE_251" and abs(p["c"] - 193.1) < 1:
            a["not"] = "paftada \"Sürgülü Pencere\" (verandaya bakan)"
    M["ekler"] = PK03.ekler(M)
    # kulaklı H = makas ayağının geldiği ek (PK-01, -02, -03, -05'te tuttu): makaslar y yönünde, ayaklar ön (y = 0) ve arka (y = 773)
    # dış duvarda; salon–veranda duvarı (y 323,7–333,8) çatının ortasında kalır, makas ayağı almaz
    for e in M["ekler"]:
        e["sacak"] = bool(e["sacak"] and (e["yer"][1] < 15 or e["yer"][1] > 760))
    kos = Counter(k_["tur"] for k_ in M["koseler"])
    to, asik_, kap = tavan_omega(), asik(), kaplama()
    (BURASI / "pafta_montaj.json").write_text(json.dumps({"kaynak": "PK06_1–8.pdf (Sevim Güler 82 + 10 m², Loftev)", "cerceve": __doc__.split("Çerçeve: ")[1].split("\n")[0],
                                                          "montaj_plani": M, "tavan_omega": to, "asik": asik_, "kaplama": kap},
                                                         ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    kapali = oda_kayitlari()
    ver = {"ad": "VERANDA", "tur": "veranda", "alan_m2": round((VERANDA[2] - VERANDA[0]) * (VERANDA[3] - VERANDA[1]) / 1e4, 3),
           "en_cm": round(VERANDA[2] - VERANDA[0], 2), "derin_cm": round(VERANDA[3] - VERANDA[1], 2)}
    kapali_brut = 951.25 * 773.0 + 188.25 * (773.0 - 323.7)                   # ana blok + salonun soldaki çıkıntısı = 81,99 ("82")
    veranda_brut = (188.2 + 120.3) * 323.7                                     # dikme dış yüzünden ana bloğa = 9,99 ("+ 10")
    yp = {"kod": "PK-06", "is_emri_no": "PK06-SEVIM-GULER-82+10M2 (pafta kipi)", "H0": 250.0, "W": 1259.8, "D": 773.0,
          "brut_m2": round((kapali_brut + veranda_brut) / 1e4, 3), "dis_cevre_m": round(2 * (1139.5 + 773.0) / 100, 3), "t_dis": 10.0,
          "panolar": [{"duvar": p["duvar"], "kal_mm": 100 if p["duvar"] == "dis" else 60, "boy": p["boy"],
                       "aciklik": None if not p.get("aciklik") else {k_: v for k_, v in p["aciklik"].items() if k_ in ("tur", "olcu", "genislik", "mentese")}}
                      for p in M["panolar"]],
          "ekler": [{k_: e[k_] for k_ in ("duvar", "cins", "sacak")} for e in M["ekler"]],
          "koseler": dict(kos), "dikmeler": len(M["dikmeler"]),
          # çatı kenarına gelmeyen dış duvarlar (ana çatının altında kalan): salon–veranda duvarı 198,1 + verandaya bakan mutfak duvarı 333,8
          "ic_kalan_dis_duvar_m": round((198.1 + 333.8) / 100, 3),
          "veranda_kirisleri_cm": [298.5, 313.75, 110.25],                   # paftadaki ölçüler: ön, sol (dikmeler arası), arka (dikmeden salona)
          "kapali": [{k_: v for k_, v in o.items() if k_ != "rect"} for o in kapali], "acik": [ver],
          "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 773.0, "boy_cm": 1139.5, "egim_yuzde": 34.0, "sacak_cm": 30.0, "kalkan": 2,
                    "sacak_hatlari_m": [round(11.995 + 1.2025, 4), 11.995],
                    "not": "sayfa 4–5: MK01–MK10 (125,5'te bir, x 4 … 1135); sayfa 2 kesiti: yükselme 140,06 / yatay 411,51 → %34,0, eğik 434,69. "
                           "Ön saçak verandanın önünden de geçer (veranda çatısının ön yüzü aynı düzlemde): 11,995 + 1,2025"},
                   {"ad": "veranda çatısı", "tip": "besik", "aciklik_cm": 333.8, "boy_cm": 120.3, "egim_yuzde": 32.8, "sacak_cm": 30.0, "kalkan": 1,
                    "capraz": False, "mahya_boy_cm": 150.25, "sacak_hatlari_m": [1.5025],
                    "not": "ana çatıya paralel ikinci beşik (MK11 x −4, MK12 x −116); sol kesit: taban 373,75, yükselme 61,37 / 186,87 → %32,8; "
                           "ön yüzü ana çatının ön yüzüyle aynı düzlemde (aşık planında ön yüzün alt dört sırası 120,25 uzuyor), arka yüzü 4 × 150,25"}],
          "ozellikler": {"Panel Türü": "Press Panel", "Çatı Şekli": "Beşik", "Çatı Kaplaması": "Tek kat panel", "Çatı Kaplama Rengi": "Antrasit",
                         "Dış Kapı": "Çelik", "İç Kapılar": "Amerikan Panel", "Dış Cephe Boya": "Sandeco", "İç Cephe Boya": "Sandeco",
                         "Tavan": "Ters tavan", "Saçak Rengi": "Antrasit", "Saçak Çıkması": "30 cm", "Yağmur Oluğu": "Metal",
                         "Yağmur Oluğu Rengi": "Antrasit", "Yağmur İniş Borusu": ""},
          "alici_ait": {"kalemler": [], "kaynak": "onay paftasının özellik tablosu: alıcıya ait kalem yazılmamış; açıklama boş; iniş borusu boş"},
          "kaynak_notu": "deneme/2026-10-13_pk_06/pafta_oku.py; Motor çizemiyor (L plan, 160/180 iki modüllük pano, paralel veranda beşiği)"}
    (BURASI / "yapi_pafta.json").write_text(json.dumps(yp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ozet = {"pano": len(M["panolar"]), "dis": sum(p["duvar"] == "dis" for p in M["panolar"]), "ic": sum(p["duvar"] == "ic" for p in M["panolar"]),
            "kose": dict(kos), "dikme": len(M["dikmeler"]),
            "pencere": sum(1 for p in M["panolar"] if (p.get("aciklik") or {}).get("tur") == "pencere"),
            "kapi": dict(Counter((p.get("aciklik") or {}).get("tur") for p in M["panolar"] if (p.get("aciklik") or {}).get("tur", "").endswith("kapi"))),
            "ek": {f"{d}|{c}|" + ("saçak" if s else "kalkan"): n for (d, c, s), n in Counter((e["duvar"], e["cins"], e["sacak"]) for e in M["ekler"]).items()},
            "boy": dict(Counter(f"{p['duvar']} {p['boy']}" for p in M["panolar"]))}
    print(json.dumps(ozet, ensure_ascii=False, default=str))
    print("brüt", yp["brut_m2"], "m²; kapalı", round(kapali_brut / 1e4, 2), "+ veranda", round(veranda_brut / 1e4, 2), "; dış çevre", yp["dis_cevre_m"],
          "m; odalar", round(sum(o["alan_m2"] for o in kapali), 2), "m²")
    print("tavan omega", to["parca"], "parça", to["toplam_m"], "m; aşık", asik_, "; kaplama", kap)
    for p in M["panolar"]:
        if p.get("aciklik"):
            print("  ", p["yon"], p["c"], (round(p["a0"], 1), round(p["a1"], 1)), p["boy"], p["aciklik"]["tur"], p["aciklik"].get("olcu"), p["aciklik"].get("mentese", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
