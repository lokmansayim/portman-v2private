"""PK-02 montaj paftası setinin vektör okuması (13 Ekim 2026; İE-11 PR-2, kör test adım 1).

`kaynak/` altındaki Loftev paftalarından (Büşra Nur Gürgün çizimi; sayfa 270° döndürülmüş) Motor'un gerçek çerçevesine (cm; x soldaki
dış yüzden, y ön dış yüzden) çevirip `pafta_montaj.json`'a yazar. Elle okuma yok; renkler paftanın kendi düzeni:
  - montaj ve elektrik planı: turuncu dörtgen = 125,5'lik pano, siyah / zeytin / beyaz = ölçüye kesilmiş pano, kırmızı 10 × 5 = köşe,
    camgöbeği 5 × 10 + 5 × 5 = pencere karkası uç işareti, lacivert çeyrek yay = kapı kanadı;
  - makas ve dere planı: camgöbeği düşey hatlar = makas, köşedeki daireler = iniş;
  - aşık planı: "410 410 13" yazıları = aşık sırası (sıra başına iki 4200'lük boy + 13 cm);
  - çatı kaplaması planı: "430 100 17 ADET" = sandviç panel;
  - tavan omega planı: magenta ölçü çizgileri = asma tavan omegaları (125'te bir) ve duvar üstü omegalar.
Ölçek tek (pt/cm), genişlik 773 cm'den; derinlik ölçekten çıkar (739,25; paftadaki "745" yazısı panolarla uyuşmaz).

Koşma: python3 -I deneme/2026-10-13_pk_02/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import pymupdf as fitz

BURASI = Path(__file__).resolve().parent
K = BURASI / "kaynak"
CIKTI = BURASI / "pafta_montaj.json"
GENISLIK_CM = 773.0

RENK = {(0.949, 0.404, 0.133): "STD", (0.0, 0.0, 0.0): "OZEL", (0.784, 0.788, 0.176): "OZEL", (1.0, 1.0, 1.0): "OZEL",
        (1.0, 0.0, 0.0): "KOSE", (0.498, 0.875, 1.0): "KARKAS"}
KANAT = (0.047, 0.275, 0.592)


def _renk(d, anahtar="color"):
    return tuple(round(v, 3) for v in (d.get(anahtar) or (9, 9, 9)))


def montaj(pg) -> dict:
    dort = []
    for d in pg.get_drawings():
        r = _renk(d)
        if r not in RENK:
            continue
        for it in d["items"]:
            if it[0] == "qu":
                q = it[1].rect
                dort.append((RENK[r], q.x0, q.y0, q.x1, q.y1))
    govde = [o for o in dort if o[0] in ("STD", "OZEL") and min(o[3] - o[1], o[4] - o[2]) > 5]
    x0 = min(o[1] for o in govde); x1 = max(o[3] for o in govde)            # ön … arka (x_pdf)
    y0 = min(o[2] for o in govde); y1 = max(o[4] for o in govde)            # sol … sağ (y_pdf)
    s = (y1 - y0) / GENISLIK_CM
    bx = lambda v: (v - y0) / s
    by = lambda v: (v - x0) / s

    def kutu(o):
        a, b = sorted((bx(o[2]), bx(o[4]))); c, e = sorted((by(o[1]), by(o[3])))
        return [round(a, 2), round(c, 2), round(b, 2), round(e, 2)]

    panolar, koseler, karkas = [], [], []
    for o in dort:
        k = kutu(o); w, h = k[2] - k[0], k[3] - k[1]
        if o[0] in ("STD", "OZEL") and min(w, h) > 5 and max(w, h) > 20:
            panolar.append({"tur": o[0], "rect": k, "boy": round(max(w, h), 2), "kalinlik": round(min(w, h), 2)})
        elif o[0] == "KOSE" and 4 < min(w, h) < 6 and 9 < max(w, h) < 11:
            koseler.append({"rect": k})
        elif o[0] == "KARKAS":
            karkas.append({"rect": k})
    kanatlar = []
    for d in pg.get_drawings():
        if _renk(d) != KANAT:
            continue
        for it in d["items"]:
            if it[0] == "c":
                a = (bx(it[1].y), by(it[1].x)); b = (bx(it[4].y), by(it[4].x))
                r = math.dist(a, b) / math.sqrt(2)
                if r > 40:
                    kanatlar.append({"uc_a": [round(v, 1) for v in a], "uc_b": [round(v, 1) for v in b], "yaricap": round(r, 1)})
    derinlik = (x1 - x0) / s
    return {"olcek_pt_cm": round(s, 5), "dis_olcu_cm": [GENISLIK_CM, round(derinlik, 2)], "panolar": panolar, "koseler": koseler,
            "pencere_karkas_isaretleri": karkas, "kanatlar": kanatlar}


def makas_dere(pg) -> dict:
    """Makaslar planda düşey camgöbeği hatlardır (döndürülmemiş sayfada yatay: y_pdf sabit). Her makas hattının parçalarının toplam boyu
    aynıdır; yan profil çizimindeki hat bundan uzundur ve dışarıda kalır. İnişler: kenarlardaki dört daire (göz sayımı, aşağıda)."""
    hat = Counter()
    for d in pg.get_drawings():
        if _renk(d) == (0.0, 1.0, 1.0):
            for it in d["items"]:
                if it[0] == "l" and abs(it[1].y - it[2].y) < 0.5:
                    hat[round(it[1].y)] += abs(it[1].x - it[2].x)
    orta = sorted(hat.values())[len(hat) // 2]
    makas = sorted(y for y, L in hat.items() if abs(L - orta) < 0.1 * orta)
    yazi = [w[4] for w in pg.get_text("words") if re.fullmatch(r"\d+", w[4])]
    return {"makas_hatti_sayisi": len(makas), "makas_y_pdf": makas, "olculer": yazi,
            "inis": 4, "inis_notu": "köşelerdeki dört iniş dairesi (göz sayımı, MAKAS_VE_DERE görüntüsü)",
            "cati_olculeri_cm": {"mahya_boyu": 833, "makas_acikligi_sacakla": 805, "egik_boy": 424, "yukselme": 143}}


def asik(pg) -> dict:
    w = [x[4] for x in pg.get_text("words")]
    return {"sira": w.count("13"), "parca_410": w.count("410"), "sira_boyu_cm": 410 + 410 + 13}


def kaplama(pg) -> dict:
    metin = " ".join(x[4] for x in pg.get_text("words"))
    m = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+ADET", metin)
    return {"sandvic_boy_cm": int(m.group(1)), "sandvic_en_cm": int(m.group(2)), "sandvic_adet": int(m.group(3)), "metin": m.group(0)}


def tavan(pg) -> dict:
    w = [x[4] for x in pg.get_text("words")]
    sayi = [float(v) for i, v in enumerate(w) if re.fullmatch(r"\d+(\.\d+)?", v) and (i + 1 >= len(w) or w[i + 1] != "cm")]
    parcalar = [v for v in sayi if v > 20]                       # 8.5'ler pencere boşluğu ölçüsü; notlardaki "60 cm", "125 cm" dışarıda
    return {"omega_parcalari_cm": parcalar, "parca": len(parcalar), "toplam_m": round(sum(parcalar) / 100, 2),
            "not": "Paftanın notu: asma tavan omegaları 125 cm'de bir; veranda ters tavanı 60 cm'de bir (bu projede veranda yok)."}


def main() -> int:
    ac = lambda ad: fitz.open(K / f"PK02_{ad}.pdf")[0]
    sonuc = {"kaynak": "PK-02 Mehmet Balaban 58 m² (Loftev), montaj paftası seti", "cerceve": "Motor gerçek çerçevesi; cm; x sol dış yüzden, y ön dış yüzden",
             "montaj_plani": montaj(ac("MONTAJ_VE_ELEKTRİK_PLANI")), "makas_dere": makas_dere(ac("MAKAS_VE_DERE_YERLEŞİM_PLANI")),
             "asik": asik(ac("AŞIK_YERLEŞİM_PLANI")), "cati_kaplamasi": kaplama(ac("ÇATI_KAPLAMASI_YERLEŞİM_PLANI")),
             "tavan_omega": tavan(ac("TAVAN_OMEHA_YERLEŞİM_PLANI"))}
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    m = sonuc["montaj_plani"]
    print(f"pano {len(m['panolar'])} (STD {sum(p['tur'] == 'STD' for p in m['panolar'])}), köşe {len(m['koseler'])}, kanat {len(m['kanatlar'])}, "
          f"dış ölçü {m['dis_olcu_cm']}; makas {sonuc['makas_dere']['makas_hatti_sayisi']}; aşık sırası {sonuc['asik']['sira']}; "
          f"sandviç {sonuc['cati_kaplamasi']['sandvic_adet']}; tavan omega {sonuc['tavan_omega']['parca']} parça {sonuc['tavan_omega']['toplam_m']} m → {CIKTI.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
