"""PK-01 montaj paftasının vektör okuması (13 Ekim 2026; İE-11).

`kaynak/HUMA_60M2_MONTAJ_PAFTASI.pdf` sayfa 2 (montaj planı) ve sayfa 3 (H profil montaj planı) çizgilerinden panoları, köşe
parçalarını, kapı kanatlarını, pencere uç işaretlerini ve H profil işaretlerini Motor'un gerçek çerçevesine (cm; x soldaki dış
yüzden, y ön dış yüzden) çevirir ve `pafta_montaj.json`'a yazar. Elle okuma yok; renkler paftanın kendi düzeninden:
siyah dörtgen = standart pano, mavi = özel pano, kırmızı = köşe parçası, lacivert = kapı kanadı (sayfa 2); H planında
lejanttaki altı renk (sayfa 3). PDF koordinatları ~0,12 pt (≈ 0,25 cm) adımlıdır; karşılaştırma toleransı buna göre seçilir.

Koşma: python3 deneme/2026-10-13_pk_01/pafta_oku.py   (PyMuPDF; LLM yok, ağ yok)
"""
from __future__ import annotations
import json
from pathlib import Path

import fitz  # PyMuPDF

BURASI = Path(__file__).resolve().parent
KAYNAK = BURASI / "kaynak" / "HUMA_60M2_MONTAJ_PAFTASI.pdf"
CIKTI = BURASI / "pafta_montaj.json"

RENK_S2 = {(0.0, 0.0, 0.0): "STD", (0.0, 0.0, 1.0): "OZEL", (1.0, 0.0, 0.0): "KOSE", (0.047, 0.275, 0.592): "KANAT"}
RENK_S3 = {(0.663, 0.325, 0.627): ("dis", "pano_eki", "dübelli & kulaklı"), (0.075, 0.608, 0.282): ("dis", "pano_eki", "dübelli"),
           (0.996, 0.8, 0.4): ("ic", "pano_eki", "standart"), (0.929, 0.122, 0.141): ("dis", "uclu", "dübelli & kulaklı"),
           (0.369, 0.404, 0.686): ("dis", "uclu", "dübelli"), (0.949, 0.404, 0.133): ("ic", "uclu", "standart")}


def _renk(d):
    return tuple(round(v, 3) for v in (d.get("color") or (9, 9, 9)))


def montaj_plani(pg) -> dict:
    """Sayfa 2. Sayfa 270° döndürülmüş; çizim koordinatları döndürülmemiş sayfada: bina x ↔ y_pdf, bina y (önden) ↔ x_pdf."""
    dortgen, kanat_yay, kirmizi_dolu = [], [], []
    for d in pg.get_drawings():
        r = _renk(d)
        for it in d["items"]:
            if it[0] == "qu":
                q = it[1].rect; dortgen.append((RENK_S2.get(r), q.x0, q.y0, q.x1, q.y1))
            elif it[0] == "c":
                kanat_yay.append((it[1].x, it[1].y, it[4].x, it[4].y))
        if r == (1.0, 0.0, 0.0) and d.get("fill"):
            kirmizi_dolu.append(d["rect"])
    # bina kutusu: köşe parçaları ve panoların dış sınırı
    duvar = [o for o in dortgen if o[0] in ("STD", "OZEL", "KOSE")]
    xu0, xu1 = min(o[1] for o in duvar), max(o[3] for o in duvar)       # ön … arka (x_pdf)
    yu0, yu1 = min(o[2] for o in duvar), max(o[4] for o in duvar)       # sol … sağ (y_pdf)
    sx, sy = (yu1 - yu0) / 600.0, (xu1 - xu0) / 1000.0                  # pt / cm (600 × 1000 paftadaki dış ölçü)
    bx = lambda yu: (yu - yu0) / sx
    by = lambda xu: (xu - xu0) / sy

    def kutu(o):
        x0, x1 = sorted((bx(o[2]), bx(o[4]))); y0, y1 = sorted((by(o[1]), by(o[3])))
        return [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]

    panolar = [{"tur": o[0], "rect": kutu(o)} for o in dortgen if o[0] in ("STD", "OZEL")]
    koseler = [{"rect": kutu(o)} for o in dortgen if o[0] == "KOSE"]
    kanatlar = [{"rect": kutu(o)} for o in dortgen if o[0] == "KANAT"]
    yaylar = [[round(bx(a[1]), 2), round(by(a[0]), 2), round(bx(a[3]), 2), round(by(a[2]), 2)] for a in kanat_yay]
    # pencere uç işaretleri (kırmızı dolu küçük kareler): çiftler bir pencerenin iki ucu
    isaret = [kutu(("", r.x0, r.y0, r.x1, r.y1)) for r in kirmizi_dolu]
    return {"olcek_pt_cm": [round(sx, 5), round(sy, 5)], "panolar": panolar, "koseler": koseler, "kanatlar": kanatlar,
            "kanat_yaylari": yaylar, "pencere_uc_isaretleri": isaret}


def h_plani(pg) -> list:
    """Sayfa 3 (döndürülmemiş). Lejant daireleri y < 140 pt; plan daireleri y > 400 pt."""
    daire, xs, ys = [], [], []
    for d in pg.get_drawings():
        r = d["rect"]
        if any(it[0] == "c" for it in d["items"]) and 6 < r.width < 40 and abs(r.width - r.height) < 1.0 and (r.y0 + r.y1) / 2 > 400:
            daire.append((_renk(d), (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
        if 400 < r.y0 and r.y1 < 1000:
            for it in d["items"]:
                if it[0] == "l":
                    xs += [it[1].x, it[2].x]; ys += [it[1].y, it[2].y]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = (x1 - x0) / 600.0
    out = []
    for renk, cx, cy in daire:
        tur, cins, ad = RENK_S3[renk]
        out.append({"duvar": tur, "cins": cins, "ad": ad, "xy": [round((cx - x0) / s, 1), round((y1 - cy) / s, 1)]})
    return sorted(out, key=lambda h: (h["cins"], h["duvar"], h["xy"]))


def main():
    doc = fitz.open(KAYNAK)
    veri = {"kaynak": KAYNAK.name, "cerceve": "Motor gerçek çerçevesi; cm; x sol dış yüzden, y ön dış yüzden",
            "montaj_plani_s2": montaj_plani(doc[1]), "h_plani_s3": h_plani(doc[2])}
    CIKTI.write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    m = veri["montaj_plani_s2"]
    print(f"pano {len(m['panolar'])} (std {sum(p['tur'] == 'STD' for p in m['panolar'])}), köşe {len(m['koseler'])}, kanat {len(m['kanatlar'])}, "
          f"H {len(veri['h_plani_s3'])} → {CIKTI.name}")


if __name__ == "__main__":
    main()
