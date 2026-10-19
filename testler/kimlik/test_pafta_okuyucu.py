"""İE-15 · KH-1 · Tek genel pafta okuyucusu (`testler/kimlik/hakem/pafta_oku.py`).

- **Sentetik pafta (her koşuda):** okuyucunun şablon kuralları PyMuPDF ile çizilen üç sayfalık bir paftada sınanır: sayfa başlıktan
  bulunur (sıra karışık), montaj ve makas sayfaları 270° döndürülmüş, ölçek 125,5'lik panodan ve dış ölçü yazısından, dış / iç
  ayrımı konumdan, H türleri lejantın renginden, makaslar MK etiketlerinin yanındaki çizgiden (turuncu tarama çizgisi oylamayı
  şaşırtmaz), kısa makaslar ayrı aile. Lejant eksikse H satırı katmana girmez, "teyit bekliyor" yazar.
- **PK-07 gerilemesi (paftayla):** `PORTMAN_PAFTA_DIZINI` altında `PK07.pdf` (SHA tutarsa) varsa okuyucu 13 Ekim betiğinin pano, H ve
  makas sayılarını ve makas konumlarını (±0,5 cm) yeniden üretir; yoksa atlanır. Pafta depoya girmez (antetinde ad var).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pymupdf as fitz
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "testler" / "kimlik" / "hakem"))
import pafta_oku as PO  # noqa: E402

FONT = str(KOK / "motor" / "genel" / "font" / "LiberationSans-Regular.ttf")
VERI = KOK / "testler" / "kimlik" / "veri"
PROJE = KOK / "testler" / "kimlik" / "hakem" / "projeler"
GENIS, YUKSEK = 842, 1191                     # A3 dikey; montaj ve makas sayfaları 270° döndürülür (mühürlü paftalardaki gibi)
S, X0, Y1 = 0.5, 300.0, 600.0                 # pt / cm; görünen sayfada binanın sol dış yüzü ve ön dış yüzü
R = PO.VARSAYILAN["montaj"]["renkler"]
DUVAR = PO.VARSAYILAN["duvar_rengi"]
H_RENK = {"dubelli_kulakli": (0.663, 0.325, 0.627), "dubelli": (0.075, 0.608, 0.282), "standart": (0.996, 0.8, 0.4),
          "uclu_dubelli_kulakli": (0.929, 0.122, 0.141), "uclu_dubelli": (0.369, 0.404, 0.686), "uclu_standart": (0.949, 0.404, 0.133)}
H_ETIKETI = {"dubelli_kulakli": "H (DÜBELLİ&KULAKLI)", "dubelli": "H (DÜBELLİ)", "standart": "H (STANDART)",
             "uclu_dubelli_kulakli": "3’LÜ H (DÜBELLİ & KULAKLI)", "uclu_dubelli": "3'LÜ H (DÜBELLİ)", "uclu_standart": "3'LÜ H (STANDART)"}


class Sayfa:
    """Görünen sayfanın koordinatıyla çizer (bina cm'si → görünen pt → döndürülmemiş pt)."""

    def __init__(self, doc, rot: int):
        self.pg, self.rot = doc.new_page(width=GENIS, height=YUKSEK), rot

    def ters(self, X, Y):
        return fitz.Point(GENIS - Y, X) if self.rot == 270 else fitz.Point(X, Y)

    @staticmethod
    def gor(x, y):
        return X0 + x * S, Y1 - y * S

    def dortgen(self, k, renk):
        a, b = self.ters(*self.gor(k[0], k[1])), self.ters(*self.gor(k[2], k[3]))
        self.pg.draw_rect(fitz.Rect(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)), color=renk, width=0.3)

    def cizgi(self, p, q, renk):
        self.pg.draw_line(self.ters(*self.gor(*p)), self.ters(*self.gor(*q)), color=renk, width=0.3)

    def daire(self, X, Y, renk, r=7):
        self.pg.draw_circle(self.ters(X, Y), r, color=renk, width=0.8)

    def yazi(self, X, Y, metin, boy=9):
        """Yazının ortası görünen (X, Y)'ye gelir."""
        w = fitz.Font(fontfile=FONT).text_length(metin, boy)
        o = self.ters(X, Y)
        self.pg.insert_text((o.x - w / 2, o.y + 0.35 * boy), metin, fontsize=boy, fontname="ls", fontfile=FONT)

    def bitir(self):
        if self.rot:
            self.pg.set_rotation(self.rot)


def _dis_cizgi(s: Sayfa):
    for p, q in (((0, 0), (600, 0)), ((600, 0), (600, 400)), ((600, 400), (0, 400)), ((0, 400), (0, 0)), ((295, 10), (295, 390))):
        s.cizgi(p, q, DUVAR)


H_KONUM = {"dubelli_kulakli": [(5, 130), (5, 255), (595, 130)], "dubelli": [(130, 5), (255, 5)],
           "standart": [(300, 130), (300, 255), (130, 395), (255, 395)], "uclu_dubelli_kulakli": [(300, 5)],
           "uclu_dubelli": [(595, 255)], "uclu_standart": [(5, 395), (595, 395)]}
MAKAS = {"MK01": (390, 660), "MK02": (260, 660), "MK03": (140, 660), "MK04": (10, 660), "MK05": (200, 260), "MK06": (75, 260)}


def sentetik(yol: Path, lejant_eksik: str | None = None) -> Path:
    doc = fitz.open()
    # 1. sayfa kapak (başlıksız), sonra H, makas ve montaj: sayfa başlıktan bulunur
    Sayfa(doc, 0).yazi(400, 500, "TEKNİK ÖZELLİKLER")

    h = Sayfa(doc, 0)
    _dis_cizgi(h)
    for i, (tur, renk) in enumerate(H_RENK.items()):
        h.daire(260 + 40 * i, 120, renk)                          # lejantın başlık satırı (yazısı iki satırlık, eşlenmez)
        if tur != lejant_eksik:
            h.daire(100, 200 + 30 * i, renk)
            h.yazi(180, 200 + 30 * i, H_ETIKETI[tur])
        for x, y in H_KONUM[tur]:
            h.daire(*h.gor(x, y), renk)
    h.yazi(420, 1100, "H PROFİL MONTAJ PLANI", 16)
    h.bitir()

    m = Sayfa(doc, 270)
    for k in ([0, 0, 10, 10], [590, 0, 600, 10], [0, 390, 10, 400], [590, 390, 600, 400]):
        m.dortgen(k, R["KOSE"])
    m.dortgen([-200, 0, -150, 30], R["KOSE"])                       # lejant tablosunun hücresi: köşe değil
    for y0, y1 in ((0, 10), (390, 400)):
        for x0, x1, tur in ((10, 135.5, "STD"), (135.5, 261, "STD"), (261, 386.5, "STD"), (386.5, 512, "STD"), (512, 590, "OZEL")):
            m.dortgen([x0, y0, x1, y1], R[tur])
    for x0, x1 in ((0, 10), (590, 600), (295, 305)):
        for y0, y1, tur in ((10, 135.5, "STD"), (135.5, 261, "STD"), (261, 390, "OZEL")):
            m.dortgen([x0, y0, x1, y1], R[tur])
    m.dortgen([150, 200, 232, 204], R["KANAT"])
    for metin, (X, Y) in (("600", (450, 640)), ("400", (130, 500)), ("78", (580, 620)), ("129", (250, 450))):
        m.yazi(X, Y, metin)
    m.yazi(500, 700, "MONTAJ PLANI", 12)
    m.bitir()

    k = Sayfa(doc, 270)
    _dis_cizgi(k)
    for ad, (y, boy) in MAKAS.items():
        for dy in (-4, 4):
            k.cizgi((-30, y + dy), (-30 + boy, y + dy), (0.0, 1.0, 1.0))
        k.yazi(X0 - 40, k.gor(0, y)[1], ad)
        k.cizgi((300, y), (580, y), (0.949, 0.404, 0.133))           # veranda taraması gibi uzun turuncu çizgi, etiketten uzakta
    k.yazi(500, 700, "MAKAS VE DERE YERLEŞİM  PLANI", 12)
    k.bitir()
    doc.save(yol)
    return yol


@pytest.fixture(scope="module")
def okuma(tmp_path_factory):
    return PO.oku(sentetik(tmp_path_factory.mktemp("pafta") / "sentetik.pdf"))


def test_sayfalar_basliktan(okuma):
    assert okuma["okuyucu"]["sayfalar"] == {"h": 2, "makas": 4, "montaj": 3}


def test_montaj(okuma):
    m = okuma["ayrinti"]["montaj"]
    assert m["pano"] == {"adet": 19, "std": 14, "ozel": 5, "dis": 16, "ic": 3}
    assert (m["kose"], m["kose_kare"], m["kanat"]) == (4, 4, 1)
    assert m["dis_olcu_cm"] == [600.0, 400.0] and m["olcek_kaynagi"] == ["ölçü yazısı", "ölçü yazısı"]
    assert sorted(p["boy"] for p in m["panolar"] if p["tur"] == "OZEL") == [78.0, 78.0, 129.0, 129.0, 129.0]
    ic = [p for p in m["panolar"] if p["duvar"] == "ic"]
    assert all(abs(p["rect"][0] - 295) < 0.3 and abs(p["rect"][2] - 305) < 0.3 for p in ic)


def test_h_plani(okuma):
    assert okuma["ayrinti"]["h_plani"]["turler"] == {t: len(v) for t, v in H_KONUM.items()}
    assert okuma["h_plani"] == {
        "dis": {"adet": 5, "not": "H planı: 3 dübelli & kulaklı + 2 dübelli"},
        "h_standart": {"adet": 4, "not": "H planı: H standart"},
        "uclu_dis": {"adet": 2, "not": "H planı: 3'lü 1 dübelli & kulaklı + 1 dübelli"},
        "uclu_standart": {"adet": 2, "not": "H planı: 3'lü H standart"},
    }
    konum = {(k["tur"], round(k["xy"][0]), round(k["xy"][1])) for k in okuma["ayrinti"]["h_plani"]["konumlar"]}
    assert konum == {(t, x, y) for t, v in H_KONUM.items() for x, y in v}


def test_makas(okuma):
    ms = {m["ad"]: m for m in okuma["ayrinti"]["makas"]["makaslar"]}
    assert set(ms) == set(MAKAS)
    for ad, (y, boy) in MAKAS.items():
        assert abs(ms[ad]["konum_cm"] - y) < 0.3 and abs(ms[ad]["boy_cm"] - boy) < 0.3 and ms[ad]["cizgi"] == 2
    assert [ms[a]["rol"] for a in ("MK01", "MK02", "MK03", "MK04", "MK05", "MK06")] == ["bas", "orta", "orta", "bas", "yavru", "yavru"]
    assert okuma["ayrinti"]["makas"]["renk"] == [0.0, 1.0, 1.0]
    assert okuma["makas_bas"] == {"adet": 2, "not": "makas planı MK01 ve MK04 (ana çatının iki ucu)"}
    assert okuma["makas_orta"]["adet"] == 2 and okuma["makas_orta"]["not"].startswith("makas planı MK02 ve MK03; boy 660.0 cm; ana çatıdan ayrı 2")
    assert okuma["teyit_bekliyor"] == [] and okuma["ayrinti"]["uyarilar"] == []


def test_lejant_eksikse_teyit(tmp_path):
    o = PO.oku(sentetik(tmp_path / "eksik.pdf", lejant_eksik="dubelli"))
    assert "h_plani" not in o
    assert any(t.startswith("h_plani:") and "dubelli" in t for t in o["teyit_bekliyor"])
    assert o["makas_bas"]["adet"] == 2                       # öteki satırlar yine okunur


def test_sha_tutmazsa_okunmaz(tmp_path):
    p = sentetik(tmp_path / "s.pdf")
    with pytest.raises(ValueError, match="SHA"):
        PO.oku(p, {"pafta_sha256": "0" * 64})


def test_proje_ayari_varsayilani_ezer(tmp_path):
    p = sentetik(tmp_path / "s.pdf")
    with pytest.raises(ValueError, match="montaj planı sayfası bulunamadı"):
        PO.oku(p, {"ayar": {"basliklar": {"montaj": "BAŞKA BAŞLIK"}}})
    o = PO.oku(p, {"ayar": {"basliklar": {"montaj": "BAŞKA BAŞLIK"}, "sayfalar": {"montaj": 3}}})
    assert o["ayrinti"]["montaj"]["pano"]["adet"] == 19


def _pafta(kod: str) -> Path | None:
    d = os.environ.get("PORTMAN_PAFTA_DIZINI")
    p = Path(d) / f"{kod}.pdf" if d else None
    if not p or not p.exists():
        return None
    proje = json.loads((PROJE / f"{kod}.json").read_text(encoding="utf-8"))
    return p if PO.sha256(p) == proje["pafta_sha256"] else None


@pytest.mark.skipif(_pafta("PK07") is None, reason="PK-07 paftası yok (PORTMAN_PAFTA_DIZINI/PK07.pdf, SHA'sı proje ayarındaki)")
def test_pk07_13_ekim_gerilemesi():
    g = json.loads((VERI / "PK07_gerileme_13ekim.json").read_text(encoding="utf-8"))
    o = PO.oku(_pafta("PK07"), json.loads((PROJE / "PK07.json").read_text(encoding="utf-8")))
    m = o["ayrinti"]["montaj"]
    assert o["pafta_sha256"] == g["pafta_sha256"]
    assert m["pano"] == g["pano"]
    assert (m["kose"], m["kose_kare"], m["kanat"]) == (g["kose"], g["kose_kare"], g["kanat"])
    assert o["ayrinti"]["h_plani"]["turler"] == g["h_turleri"]
    ms = o["ayrinti"]["makas"]["makaslar"]
    ana = [x["konum_cm"] for x in ms if x["aile"] == "ana"]
    cumba = [x["konum_cm"] for x in ms if x["aile"] != "ana"]
    assert len(ana) == len(g["makas"]["ana_cm"]) and all(abs(a - b) <= 0.5 for a, b in zip(ana, g["makas"]["ana_cm"]))
    assert len(cumba) == len(g["makas"]["cumba_cm"]) and all(abs(a - b) <= 0.5 for a, b in zip(cumba, g["makas"]["cumba_cm"]))
    assert (o["makas_bas"]["adet"], o["makas_orta"]["adet"]) == (g["makas"]["makas_bas"], g["makas"]["makas_orta"])
    assert o["teyit_bekliyor"] == []
