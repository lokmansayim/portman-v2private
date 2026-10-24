"""İE-15 · KH-3 · PK-01'in elektrik yerleşim planı (hakem değişikliği; Patron onayı gerekir).

KH-1, KH-2 ve K1–K2'nin testleri değişmez (tek istisna: `test_hakem_kh2.py`'de cevap dosyasının sürüm iğnesi 2 → 3; gerekçe iş emrinde);
bu dosya KH-3'ün eklediklerini sınar:
- **Okuyucu, sentetik pafta (her koşuda):** KH-1'in sentetik paftasına 270° döndürülmüş bir elektrik sayfası eklenir (PK-07'deki gibi;
  0°, 90° ve 180° de okunur). Bölüm proje ayarıyla açılır (`ek_bolumler`); kapalıyken çıktı önceki gibidir. İşaretlerin rengi, ölçüsü ve
  içi lejanttan okunur: tijli duy (dolgulu kare), glop (çaprazlı daire), buat (çaprazsız, içinde BUAT yazan daire; bilgi), anahtar
  (daire ve tırnak sayısı), priz (U; arka arkaya iki U çift), uydu prizi ("UYDU" yazısına en yakın tek U), sigorta kutusu (çerçeve
  ölçüsü), zil (lejantta yoksa 0). Aynı yerde iki kez çizilmiş işaret bir sayılır. Konumlar duvar çerçevesinde cm. Sessiz sayı yok:
  lejant renginde ya da ona yakın tonda hiçbir işarete uymayan öğe, içi lejanttakine uymayan duy, glop, BUAT, anahtar ya da sigorta
  ölçüsünde kutu, tırnağı bir ya da iki olmayan anahtar, iki daireye değen ya da ucunda fazla çizgi olan tırnak, ölçüsü tutmayan dolgu,
  çaprazsız ve BUAT yazısız daire, çaprazı eksik ya da içinde BUAT yazan glop, lejantta çaprazsız glop, sap boyundan yakın ya da
  birbirine binen iki U, Z biçimli U, işareti ya da etiketi olmayan lejant satırı, lejanttaki zil, lejant alanının hemen altında öğe ya da alanın dışında lejant
  etiketi, yanında priz olmayan ya da başka UYDU'yla aynı prize bağlanan UYDU, üçlü zincir priz, duvar çerçevesinin dışındaki lejant
  renginde öğe, dış ölçüye oturmayan duvar, lejantta tanınmayan sözcük ya da etiketsiz işaret, lejantta olup planda hiç bulunamayan tür
  ve montaj teyidi bölümü bekletir; okunamayan sayfa yalnız kendini bekletir.
- **PK-01 cevabı:** s. 10; duy 6, glop 2, anahtar 4 + 2, priz 15 + 4, uydu 1, zil 0, sigorta 1; buat 5 (bilgi); 40 konum; iki kez
  çizilmiş 2 öğe bir sayıldı. Paftayla yeniden üretimi `test_hakem_pk01.py`'deki test sınar.
- **PK-07 gerilemesi (paftayla):** s. 13 (270° döndürülmüş) BK-12 PR-3'ün göz sayımıyla aynı; KH-1 bölümleri elektrik açılınca değişmez.
- **Kıyas aracı (`kiyas.py` değişmedi):** `--adim K3` K2'nin kapısını aynen taşır, elektrik satırları bilgidir (kapıya girmez). Elektrik
  teyitteyse araç bölümü tanımadığı için bütün satırlar bekler (daha sıkı).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
from pathlib import Path

import pymupdf as fitz
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "testler" / "kimlik"))
sys.path.insert(0, str(KOK / "testler" / "kimlik" / "hakem"))
import kiyas as KY  # noqa: E402
import pafta_oku as PO  # noqa: E402
import test_hakem_kh2 as KH2  # noqa: E402  (K2 modelinin parçaları ve IFC yazıcısı; o dosya değişmez)
import test_pafta_okuyucu as T  # noqa: E402  (KH-1'in sentetik paftası; o dosya değişmez)

VERI = KOK / "testler" / "kimlik" / "veri"
PROJE = KOK / "testler" / "kimlik" / "hakem" / "projeler"
CEVAP = VERI / "PK01_pafta_katmani.json"
KIRMIZI, TURUNCU, SIYAH = (1.0, 0.0, 0.0), (1.0, 0.247, 0.0), (0.0, 0.0, 0.0)
EL = {"ayar": {"ek_bolumler": ["elektrik"]}}
BASLIK = "ELEKTRİK YERLEŞİM PLANI"


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- sentetik elektrik sayfası
class Donuk(T.Sayfa):
    """KH-1'in sayfası yalnız 0° ve 270° çevirir; 90° ve 180°'de görünen koordinat sayfanın kendi ters döndürme matrisiyle çevrilir."""

    def __init__(self, doc, rot: int):
        super().__init__(doc, rot)
        self.pg.set_rotation(rot)
        self.m = self.pg.derotation_matrix
        self.pg.set_rotation(0)

    def ters(self, X, Y):
        return fitz.Point(X, Y) * self.m


class Elektrik:
    """Elektrik sayfasına görünen koordinatta (pt) çizer; sayfa döndürülür, yazılar görünen sayfada düz durur."""

    def __init__(self, doc, rot: int = 270):
        self.s = T.Sayfa(doc, rot) if rot in (0, 270) else Donuk(doc, rot)

    def p(self, X, Y):
        return self.s.ters(X, Y)

    def cizgi(self, a, b, renk=KIRMIZI):
        self.s.pg.draw_line(self.p(*a), self.p(*b), color=renk, width=0.4)

    def daire(self, X, Y, r, renk=KIRMIZI):
        self.s.pg.draw_circle(self.p(X, Y), r, color=renk, width=0.4)

    def kutu(self, X, Y, w, h, renk, dolgu=None):
        a, b = self.p(X - w / 2, Y - h / 2), self.p(X + w / 2, Y + h / 2)
        self.s.pg.draw_rect(fitz.Rect(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)), color=renk, fill=dolgu, width=0.3)

    def yazi(self, X, Y, metin, boy=7):
        w = fitz.Font(fontfile=T.FONT).text_length(metin, boy)
        self.s.pg.insert_text(self.p(X - w / 2, Y + 0.35 * boy), metin, fontsize=boy, fontname="ls", fontfile=T.FONT, rotate=self.s.rot)

    # işaretler (ortası görünen X, Y)
    def duy(self, X, Y, a=12.0):
        self.kutu(X, Y, a, a, KIRMIZI, KIRMIZI)
        self.cizgi((X - 4, Y - 4), (X + 4, Y + 4))
        self.cizgi((X - 4, Y + 4), (X + 4, Y - 4))

    def glop(self, X, Y, capraz=2):
        self.daire(X, Y, 9.5)
        for a, b in (((X - 6.7, Y - 6.7), (X + 6.7, Y + 6.7)), ((X - 6.7, Y + 6.7), (X + 6.7, Y - 6.7)))[:capraz]:
            self.cizgi(a, b)

    def buat(self, X, Y, yazili=True):
        self.daire(X, Y, 9.5)
        if yazili:
            self.yazi(X, Y, "BUAT", 3)

    def anahtar(self, X, Y, tirnak=1):
        self.daire(X, Y, 4.5, TURUNCU)
        for aci in (-60, -120, -30)[:tirnak]:
            c, s = math.cos(math.radians(aci)), math.sin(math.radians(aci))
            b = (X + 4.5 * c, Y + 4.5 * s)
            e = (b[0] + 4.6 * c, b[1] + 4.6 * s)
            self.cizgi(b, e, TURUNCU)
            self.cizgi(e, (e[0] + 2.4, e[1]), TURUNCU)                # tırnağın ucundaki kısa çizgi

    def priz(self, X, Y, yon=(0, -1), kolsuz=False):
        """Taban (X, Y)'de, kollar `yon`a, sap öbür yana; sapın ucu döner."""
        ux, uy = yon
        nx, ny = -uy, ux
        a, b = (X - 4.25 * nx, Y - 4.25 * ny), (X + 4.25 * nx, Y + 4.25 * ny)
        self.cizgi(a, b)
        for i, u in enumerate((a, b)):
            if not (kolsuz and i):
                self.cizgi(u, (u[0] + 4.9 * ux, u[1] + 4.9 * uy))
        uc = (X - 7.8 * ux, Y - 7.8 * uy)
        self.cizgi((X, Y), uc)
        return uc

    def cift_priz(self, X, Y, yon=(0, -1), uclu=False):
        uc = self.priz(X, Y, yon)
        uc = self.priz(*uc, yon)
        if uclu:
            self.priz(*uc, yon)

    def sigorta(self, X, Y):
        self.kutu(X, Y, 14, 10, SIYAH)
        self.cizgi((X - 4, Y), (X + 4, Y), SIYAH)

    def bitir(self):
        self.s.bitir()


def g(x, y):
    """Bina cm'si → görünen pt (montajla aynı ölçek ve yer)."""
    return T.Sayfa.gor(x, y)


# beklenen işaretler (bina cm'si)
DUY = [(150, 200), (450, 200)]
GLOP = [(450, 330)]
BUAT = [(200, 330)]
ANAHTAR_TEKLI, ANAHTAR_CIFT = [(80, 30), (520, 30)], [(380, 30)]
PRIZ_TEKLI = [((20, 100), (1, 0)), ((580, 100), (-1, 0)), ((150, 380), (0, 1))]
PRIZ_CIFT = [((380, 380), (0, 1))]
UYDU = (450, 100)
SIGORTA = (330, 60)


def kh3_sentetik(yol: Path, *, taban: dict | None = None, rot: int = 270, tirnak: int | None = None, eksik_u: bool = False,
                 buyuk_dolgu: bool = False, bos_daire: bool = False, tek_capraz: bool = False, lejant_isaretsiz: str | None = None,
                 lejant_etiketsiz: str | None = None, zil: bool = False, uydu_uzak: bool = False, disarida: bool = False,
                 serbest_cizgi: bool = False, oran: bool = False, duvarsiz: bool = False, uclu_priz: bool = False,
                 yabanci_etiket: bool = False, bagsiz_isaret: bool = False, glopsuz_plan: bool = False, uydu_cift: bool = False,
                 caprazsiz_glop: bool = False, ek=None) -> Path:
    """KH-1'in sentetik paftası + elektrik sayfası. Bina 600 × 400 cm (montajın dış ölçüsü); lejant binanın sağında. `ek(e)`: sayfa
    döndürülmeden önce eklenen bozma."""
    gecici = yol.with_suffix(".kh1.pdf")
    T.sentetik(gecici, **(taban or {}))
    doc = fitz.open(gecici)
    e = Elektrik(doc, rot)
    if not duvarsiz:
        T._dis_cizgi(e.s)
    if oran:                                                       # duvar çizgisi 450 cm'ye uzar: sınır dış ölçüye oturmaz
        e.s.cizgi((0, 400), (0, 450), T.DUVAR)
    # lejant (binanın sağında; dik sayfaya da sığar)
    e.yazi(710, 300, "LEJANT", 12)
    satir = {"anahtar": (330, ["ANAHTAR"], lambda X, Y: e.anahtar(X, Y, 2)), "priz": (355, ["PRİZ"], lambda X, Y: e.priz(X, Y)),
             "glop": (385, ["GLOP"], lambda X, Y: e.glop(X, Y, 0 if caprazsiz_glop else 2)), "duy": (412, ["TİJLİ", "DUY"], lambda X, Y: e.duy(X, Y + 3)),
             "sigorta": (445, ["SİGORTA", "KUTUSU"], lambda X, Y: e.sigorta(X, Y + 3))}
    if zil:
        satir["zil"] = (475, ["ZİL"], lambda X, Y: e.daire(X, Y, 3, SIYAH))
    if yabanci_etiket:                                             # etiketi bilinmeyen bir tür (okuyucunun desenlerinde yok)
        satir["tv"] = (475, ["TV"], lambda X, Y: e.daire(X, Y, 3, SIYAH))
    if bagsiz_isaret:                                              # etiketsiz lejant işareti
        satir["bos"] = (475, [], lambda X, Y: e.daire(X, Y, 3, SIYAH))
    for tur, (Y, sozler, ciz) in satir.items():
        if tur != lejant_etiketsiz:
            for i, s in enumerate(sozler):
                w = fitz.Font(fontfile=T.FONT).text_length(s, 7)
                e.yazi(718 + w / 2, Y + 8 * i, s)
        if tur != lejant_isaretsiz:
            ciz(665, Y)
    # plan
    for x, y in DUY:
        e.duy(*g(x, y))
    for x, y in [] if glopsuz_plan else GLOP:
        e.glop(*g(x, y), 0 if caprazsiz_glop else 2)
    for x, y in BUAT:
        e.buat(*g(x, y))
    for x, y in ANAHTAR_TEKLI:
        e.anahtar(*g(x, y), 1)
    for x, y in ANAHTAR_CIFT:
        e.anahtar(*g(x, y), 2)
        e.daire(*g(x, y), 4.5, TURUNCU)                            # aynı daire iki kez çizilmiş (PK-01'deki gibi): bir sayılır
    for (x, y), yon in PRIZ_TEKLI:
        e.priz(*g(x, y), yon)
    for (x, y), yon in PRIZ_CIFT:
        e.cift_priz(*g(x, y), yon)
    X, Y = g(*UYDU)
    e.priz(X, Y)
    if uydu_cift:                                                  # yazıya en yakın U bir çift prizin parçası
        X, Y = g(*PRIZ_CIFT[0][0])
        Y += 2
    e.yazi(X, Y + (60 if uydu_uzak else 12), "UYDU")
    e.sigorta(*g(*SIGORTA))
    e.yazi(*g(300, 420), BASLIK, 14)
    # bozmalar
    if tirnak is not None:
        e.anahtar(*g(250, 120), tirnak)
    if eksik_u:
        e.priz(*g(250, 250), kolsuz=True)
    if buyuk_dolgu:
        e.duy(*g(250, 250), 20.0)
    if bos_daire:
        e.buat(*g(250, 250), yazili=False)
    if tek_capraz:
        e.glop(*g(250, 250), capraz=1)
    if disarida:
        e.cizgi(g(300, -150), g(330, -150))
    if serbest_cizgi:
        e.cizgi(g(250, 250), g(280, 250))
    if uclu_priz:
        e.cift_priz(*g(250, 250), uclu=True)
    if ek:
        ek(e)
    e.bitir()
    doc.save(yol)
    return yol


@pytest.fixture(scope="module")
def pdf(tmp_path_factory):
    return kh3_sentetik(tmp_path_factory.mktemp("kh3") / "s.pdf")


@pytest.fixture(scope="module")
def okuma(pdf):
    return PO.oku(pdf, EL)


def _teyit(o) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for t in o["teyit_bekliyor"]:
        out.setdefault(t["bolum"], []).append(t["neden"])
    return out


BEKLENEN = {"tavan_armaturu": 2, "glop": 1, "anahtar_tekli": 2, "anahtar_cift": 1, "priz_tekli": 3, "priz_cift": 1, "uydu_prizi": 1, "zil": 0,
            "sigorta_kutusu": 1}


def test_elektrik_kapaliyken_cikti_onceki_gibi(pdf, okuma):
    o = PO.oku(pdf)
    assert "elektrik" not in o and "elektrik" not in o["ayrinti"] and o["teyit_bekliyor"] == []
    assert {k: v for k, v in okuma.items() if k not in ("elektrik", "ayrinti")} == {k: v for k, v in o.items() if k != "ayrinti"}
    assert {k: v for k, v in okuma["ayrinti"].items() if k != "elektrik"} == o["ayrinti"]


def test_bilinmeyen_bolum_ve_surum(pdf):
    assert PO.SURUM == "3" and PO.ACILABILEN == (*PO.EK_BOLUMLER, "elektrik")
    with pytest.raises(ValueError, match=r"bilinmeyen ek bölüm: \['zil'\]"):
        PO.oku(pdf, {"ayar": {"ek_bolumler": ["zil"]}})


def test_sayim(okuma):
    assert okuma["teyit_bekliyor"] == []
    a = okuma["ayrinti"]["elektrik"]
    assert a["sayfa"] == 5 and a["sayim"] == BEKLENEN and (a["buat"], a["buat_yazisi"]) == (1, 1)
    assert a["atilan"] == {"cerceve_disinda": 0, "ayni_yerde_iki_kez": 1, "isaretten_buyuk": 0}     # çift anahtarın ikinci dairesi
    assert {k: v["adet"] for k, v in okuma["elektrik"].items()} == BEKLENEN
    assert all(v["not"].startswith("elektrik planı: ") for v in okuma["elektrik"].values())
    assert okuma["elektrik"]["zil"]["not"] == "elektrik planı: lejantta zil yok"


def test_lejanttan_okunan_olculer(okuma):
    L = okuma["ayrinti"]["elektrik"]["lejant"]
    assert (L["glop"]["cap"], L["glop"]["cizgi"], L["anahtar"]["cap"], L["anahtar"]["cizgi"]) == (19.0, 2, 9.0, 2)
    assert (L["priz"]["kol"], L["priz"]["taban"], L["priz"]["sap"]) == (4.9, 8.5, 7.8)
    assert L["duy"]["renk"] == list(KIRMIZI) and L["anahtar"]["renk"] == list(TURUNCU) and L["sigorta"]["renk"] == list(SIYAH)
    assert okuma["ayrinti"]["elektrik"]["uydu_uzakligi_pt"] == [12.0]


def test_konumlar_bina_cercevesinde_cm(okuma):
    a = okuma["ayrinti"]["elektrik"]
    assert a["olcek_pt_cm"] == [0.5, 0.5]
    beklenen = {"tavan_armaturu": DUY, "glop": GLOP, "buat": BUAT, "anahtar_tekli": ANAHTAR_TEKLI, "anahtar_cift": ANAHTAR_CIFT,
                "priz_tekli": [p for p, _ in PRIZ_TEKLI], "uydu_prizi": [UYDU], "sigorta_kutusu": [SIGORTA]}
    k = a["konumlar"]
    assert len(k) == sum(len(v) for v in beklenen.values()) + len(PRIZ_CIFT)
    for tur, yerler in beklenen.items():
        bulunan = [x["xy"] for x in k if x["tur"] == tur]
        assert len(bulunan) == len(yerler), tur
        for x, y in yerler:                                       # işaretin kutusunun ortası; U'da taban ile sapın ortası
            assert min(abs(b[0] - x) + abs(b[1] - y) for b in bulunan) <= 10, (tur, x, y, bulunan)
    assert [x["tur"] for x in k] == sorted((x["tur"] for x in k), key=PO.ISARET_SIRASI.index)


def test_katman_anahtarlari_liste_ureteciyle_ayni(okuma):
    from motor import prefabrik_liste as PL
    assert set(okuma["elektrik"]) == set(PO.ELEKTRIK) == set(PL.ELEKTRIK_NOKTALARI.values()) | {"zil", "sigorta_kutusu"}


@pytest.mark.parametrize("rot", [0, 90, 180])
def test_dik_ve_donuk_sayfa_da_okunur(tmp_path, rot):
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", rot=rot), EL)
    assert o["teyit_bekliyor"] == [] and o["ayrinti"]["elektrik"]["sayim"] == BEKLENEN


@pytest.mark.parametrize("kw, neden", [
    ({"tirnak": 0}, "anahtar dairesinde bir ya da iki olmayan tırnak: [0]"),
    ({"tirnak": 3}, "anahtar dairesinde bir ya da iki olmayan tırnak: [3]"),
    ({"eksik_u": True}, "lejant renginde, hiçbir işarete uymayan 3 öğe (çizgi 4.9 pt × 1, çizgi 7.8 pt × 1, çizgi 8.5 pt × 1)"),
    ({"serbest_cizgi": True}, "lejant renginde, hiçbir işarete uymayan 1 öğe (çizgi 15.0 pt × 1)"),
    ({"buyuk_dolgu": True}, "duy renginde, ölçüsü lejanttakinden (12.0 × 12.0 pt) farklı 1 dolgu (20.0 × 20.0 pt)"),
    ({"bos_daire": True}, "glop renginde ve çapında, çaprazsız ve içinde \"BUAT\" yazmayan 1 daire"),
    ({"tek_capraz": True}, "glop dairesinde lejanttakinden (2) başka sayıda çapraz: [1]"),
    ({"lejant_isaretsiz": "glop"}, "lejantta 'glop' etiketinin işareti okunamadı"),
    ({"lejant_etiketsiz": "priz"}, "lejantta priz etiketi yok; sayısı bilinmiyor"),
    ({"zil": True}, "lejantta zil var; bu okuyucu zil işaretini okumuyor"),
    ({"uydu_uzak": True}, "\"UYDU\" yazısının yanında priz yok"),
    ({"uclu_priz": True}, "bir U iki çift prize giriyor (üçlü priz?)"),
    ({"uydu_cift": True}, "\"UYDU\" yazısına en yakın priz çift; uydu prizi belli değil"),
    ({"disarida": True}, "duvar çerçevesinin 30 cm dışında lejant renginde 1 öğe: sayılmadı"),
    ({"oran": True}, "duvar sınırı montajdaki dış ölçüye oturmuyor (0.50000 / 0.56250 pt/cm)"),
    ({"duvarsiz": True}, "okunamadı: elektrik sayfasında duvar çizgisi yok; `elektrik.duvar_rengi` ayarını denetleyin"),
    ({"yabanci_etiket": True}, "lejantta tanınmayan 1 sözcük (etiketi bilinmeyen bir tür olabilir)"),
    ({"bagsiz_isaret": True}, "lejantta hiçbir etikete bağlanmayan 1 işaret"),
    ({"glopsuz_plan": True}, "lejantta olup planda hiç bulunamayan tür: glop"),
])
def test_uymayan_oge_elektrigi_bekletir(tmp_path, kw, neden):
    """Sessiz sayı yok: her bozma elektriği teyide düşürür, katmana elektrik satırı girmez; öteki bölümler okunur."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


def _tirnak_ucu(X, Y, aci=-60):
    c, s = math.cos(math.radians(aci)), math.sin(math.radians(aci))
    return X + 9.1 * c, Y + 9.1 * s


def _u(e, X, Y, renk=KIRMIZI, k=1.0, z=False):
    """Elle çizilmiş U: `k` ölçü çarpanı; `z` kollardan biri ters yana (Z biçimi)."""
    a, b = (X - 4.25 * k, Y), (X + 4.25 * k, Y)
    e.cizgi(a, b, renk)
    e.cizgi(a, (a[0], a[1] - 4.9 * k), renk)
    e.cizgi(b, (b[0], b[1] + (4.9 if z else -4.9) * k), renk)
    e.cizgi((X, Y), (X, Y + 7.8 * k), renk)


def _komsu_anahtar(e):
    """Tekli anahtarın tırnağının ucu, yanındaki (kendi tırnağı olan) anahtar dairesine değer."""
    X, Y = g(250, 120)
    e.anahtar(X, Y, 1)
    u = _tirnak_ucu(X, Y)
    cx, cy = u[0] + 4.5, u[1]
    e.daire(cx, cy, 4.5, TURUNCU)
    b = (cx + 4.5 * math.cos(math.radians(-30)), cy + 4.5 * math.sin(math.radians(-30)))
    e.cizgi(b, (b[0] + 4.6 * math.cos(math.radians(-30)), b[1] + 4.6 * math.sin(math.radians(-30))), TURUNCU)


def _zil_alanin_altinda(e):
    """Lejantta ZİL satırı alanın altında (başlığın 250 pt'sinden uzakta); planda siyah küçük daire."""
    w = fitz.Font(fontfile=T.FONT).text_length("ZİL", 7)
    e.yazi(718 + w / 2, 580, "ZİL")
    e.daire(665, 580, 3, SIYAH)
    e.daire(*g(560, 30), 3, SIYAH)


def _yakin_cift(e):
    uc = e.priz(*g(250, 250))
    e.priz(uc[0], uc[1] + 0.5)                                    # sapın ucu öbürünün tabanına 0,5 pt kala biter


@pytest.mark.parametrize("ek, kw, neden", [
    # tanınan işaretin kutusundaki uymayan öğe yutulmaz (işaretin içi lejanttakiyle aynı olmalı)
    (lambda e: e.daire(*g(*DUY[0]), 2.5), {}, "duy ölçüsünde, içi lejanttaki işarete uymayan 1 dolgu"),
    (lambda e: e.daire(*g(*GLOP[0]), 3), {}, "glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    (lambda e: _u(e, *g(*BUAT[0]), k=0.7), {}, "glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    (lambda e: e.priz(*g(*BUAT[0]), kolsuz=True), {}, "glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    (lambda e: (lambda X, Y: e.cizgi((X - 2, Y), (X + 2, Y), TURUNCU))(*g(*ANAHTAR_TEKLI[0])), {},
     "anahtar dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    (lambda e: (lambda X, Y: e.cizgi((X - 4, Y + 2), (X + 4, Y + 2), SIYAH))(*g(*SIGORTA)), {},
     "sigorta kutusu ölçüsünde, içi lejanttaki işarete uymayan 1 kutu"),
    (lambda e: e.kutu(*g(100, 300), 14, 10, SIYAH), {}, "sigorta kutusu ölçüsünde, içi lejanttaki işarete uymayan 1 kutu"),
    # U'nun biçimi ve rengi, çift priz payı
    (_yakin_cift, {}, "sapı öbürünün tabanına değmeyen ama sap boyundan yakın 1 U çifti (çift priz olabilir)"),
    (lambda e: [e.priz(X + d, Y) for X, Y in [g(250, 250)] for d in (0, 0.5)], {},
     "kutusu bir başkasıyla kesişen ve çift olmayan 1 U çifti (aynı priz iki kez çizilmiş olabilir)"),
    (lambda e: _u(e, *g(250, 250), z=True), {},
     "lejant renginde, hiçbir işarete uymayan 4 öğe (çizgi 4.9 pt × 2, çizgi 7.8 pt × 1, çizgi 8.5 pt × 1)"),
    (lambda e: _u(e, *g(250, 250), renk=(0.804, 0.125, 0.153)), {},
     "sigortanın iç desenindeki ya da lejant rengine yakın tonda, hiçbir işarete uymayan 4 öğe (çizgi 4.9 pt × 2, çizgi 7.8 pt × 1, "
     "çizgi 8.5 pt × 1)"),
    # anahtar tırnakları
    (_komsu_anahtar, {}, "iki anahtar dairesine birden değen 1 tırnak"),
    (lambda e: (lambda u: e.cizgi(u, (u[0], u[1] - 2.4), TURUNCU))(_tirnak_ucu(*g(*ANAHTAR_TEKLI[0]))), {},
     "ucunda birden çok çizgi olan 1 tırnak"),
    # glop ve BUAT
    (None, {"caprazsiz_glop": True}, "lejantta glop işaretinde çapraz yok: glop BUAT'tan ayrılamaz"),
    (lambda e: e.yazi(*g(*GLOP[0]), "BUAT", 3), {}, "içinde \"BUAT\" yazan 1 glop: glop mu buat mı belli değil"),
    # lejant alanı ve UYDU
    (_zil_alanin_altinda, {}, "lejant alanının (başlığın 250 pt altına kadar) hemen altında 2 öğe: lejant alandan uzun olabilir"),
    (_zil_alanin_altinda, {}, "lejant alanının dışında lejant etiketine benzeyen 1 sözcük"),
    (lambda e: e.daire(665, 575, 3, SIYAH), {}, "lejant alanının (başlığın 250 pt altına kadar) hemen altında 1 öğe: lejant alandan uzun olabilir"),
    (lambda e: (lambda X, Y: e.yazi(X, Y - 12, "UYDU"))(*g(*UYDU)), {}, "iki \"UYDU\" yazısı aynı prize bağlanıyor"),
], ids=["duy_ici", "glop_ici", "buat_ici_u", "buat_ici_eksik_u", "anahtar_ici", "sigorta_ici", "ici_bos_sigorta", "yakin_cift", "kaymis_priz", "z_u", "yakin_ton_u",
        "komsu_tirnak", "tirnak_ucu", "caprazsiz_glop", "buat_yazili_glop", "zil_alt_bant", "zil_alan_disi", "bantta_daire", "iki_uydu"])
def test_isaretin_ici_ve_bicimi_bekletir(tmp_path, ek, kw, neden):
    """KH-3 hakeminin 1. turu: tanınan işaretin kutusundaki uymayan öğe, biçimi ya da tonu tutmayan U, komşu daireye değen tırnak,
    lejant alanından taşan satır ve aynı prize bağlanan ikinci UYDU yazısı da elektriği bekletir (sessiz sayı yok)."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


def _tekli_anahtar_tirnagi_iki_kez(e):
    X, Y = g(250, 120)
    e.anahtar(X, Y, 1)
    c, s = math.cos(math.radians(-60)), math.sin(math.radians(-60))
    e.cizgi((X + 4.5 * c, Y + 4.5 * s), _tirnak_ucu(X, Y), TURUNCU)


@pytest.mark.parametrize("ek, tur, kopya", [
    (lambda e: [e.anahtar(*g(250, 120), 1) for _ in range(2)], "anahtar_tekli", 3),
    (_tekli_anahtar_tirnagi_iki_kez, "anahtar_tekli", 1),              # iki tırnak sayılıp çift olmaz
    (lambda e: [e.duy(*g(250, 250)) for _ in range(2)], "tavan_armaturu", 3),
    (lambda e: [e.glop(*g(250, 250)) for _ in range(2)], "glop", 3),
    (lambda e: [e.priz(*g(250, 250)) for _ in range(2)], "priz_tekli", 4),
    (lambda e: [e.sigorta(*g(100, 300)) for _ in range(2)], "sigorta_kutusu", 0),   # siyah öğe sayaca girmez
], ids=["anahtar", "tirnak", "duy", "glop", "priz", "sigorta"])
def test_ayni_yerde_iki_kez_cizilen_isaret_bir_sayilir(tmp_path, ek, tur, kopya):
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek), EL)
    a = o["ayrinti"]["elektrik"]
    assert o["teyit_bekliyor"] == [] and a["sayim"] == BEKLENEN | {tur: BEKLENEN[tur] + 1}
    assert a["atilan"] == {"cerceve_disinda": 0, "ayni_yerde_iki_kez": 1 + kopya, "isaretten_buyuk": 0}


def test_montaj_teyidi_elektrige_iner(tmp_path):
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", taban={"disari": "kolon"}), EL)
    t = _teyit(o)
    assert "montaj teyitte; bu bölümün ölçeği ve duvar çerçevesi montajın dış ölçüsünden" in t["elektrik"] and "elektrik" not in o


def test_sayfasi_olmayan_elektrik_katmana_girmez(tmp_path):
    o = PO.oku(T.sentetik(tmp_path / "s.pdf"), EL)
    assert o["ayrinti"]["elektrik"] is None and "elektrik" not in o and o["teyit_bekliyor"] == []


def test_komut_ozeti(pdf, tmp_path, capsys):
    proje = tmp_path / "p.json"
    proje.write_text(json.dumps(EL), encoding="utf-8")
    assert PO.main([str(pdf), "--proje", str(proje), "--cikti", str(tmp_path / "o.json")]) == 0
    cikti = capsys.readouterr().out.splitlines()
    assert any(s.startswith("elektrik (s. 5) {\"sayim\": {\"tavan_armaturu\": 2,") for s in cikti)
    assert any(s.startswith("elektrik: {\"tavan_armaturu\": {\"adet\": 2,") for s in cikti)
    assert _oku(tmp_path / "o.json")["ayrinti"]["elektrik"]["sayim"] == BEKLENEN


# ----------------------------------------------------------------------------- PK-01 cevabı
@pytest.fixture(scope="module")
def cevap():
    return _oku(CEVAP)


def test_pk01_elektrik_cevabi(cevap):
    a = cevap["ayrinti"]["elektrik"]
    assert cevap["okuyucu"]["surum"] == "3" and cevap["teyit_bekliyor"] == [] and a["sayfa"] == 10
    assert {k: v["adet"] for k, v in cevap["elektrik"].items()} == a["sayim"] == \
        {"tavan_armaturu": 6, "glop": 2, "anahtar_tekli": 4, "anahtar_cift": 2, "priz_tekli": 15, "priz_cift": 4, "uydu_prizi": 1, "zil": 0,
         "sigorta_kutusu": 1}
    assert (a["buat"], a["buat_yazisi"], a["uydu_uzakligi_pt"]) == (5, 5, [12.4])
    # iki çift anahtar dairesi ikişer kez çizilmiş (bir sayıldı); sayfa başlığının koyu kırmızı çerçevesi işaretten büyük, denetlenmedi
    assert a["atilan"] == {"cerceve_disinda": 0, "ayni_yerde_iki_kez": 2, "isaretten_buyuk": 1}
    # ölçek: duvar çizgisinin sınırı 600 × 1000 cm'ye oturur; bu sayfada duvar öteki sayfalardan açık (proje ayarı)
    assert abs(a["olcek_pt_cm"][0] - a["olcek_pt_cm"][1]) / a["olcek_pt_cm"][0] < 0.001
    assert _oku(PROJE / "PK01.json")["ayar"]["elektrik"] == {"duvar_rengi": [0.576, 0.584, 0.596]}
    k = a["konumlar"]
    assert len(k) == 40 and all(0 <= x["xy"][0] <= 600 and 0 <= x["xy"][1] <= 1000 for x in k)
    # sigorta kutusu holde, giriş kapısının iç yanında (karar E'nin varsayımıyla aynı; oda ataması K3'te)
    assert [x["xy"] for x in k if x["tur"] == "sigorta_kutusu"] == [[321.9, 209.0]]
    assert len([x for x in k if x["tur"] == "priz_cift" and x["xy"][0] < 40]) == 3          # mutfak tezgahı (sol dış duvar)


@pytest.mark.skipif(KH2._pafta("PK07") is None, reason="PK-07 paftası yok (PORTMAN_PAFTA_DIZINI/PK07.pdf, SHA'sı proje ayarındaki)")
def test_pk07_elektrik_gerilemesi():
    g_ = _oku(VERI / "PK07_gerileme_13ekim.json")
    proje = _oku(PROJE / "PK07.json")
    kh1, o = PO.oku(KH2._pafta("PK07"), proje), PO.oku(KH2._pafta("PK07"), proje | EL)
    assert {k: v["adet"] for k, v in o["elektrik"].items()} == o["ayrinti"]["elektrik"]["sayim"] == g_["elektrik"]
    assert o["teyit_bekliyor"] == kh1["teyit_bekliyor"] == [] and o["ayrinti"]["elektrik"]["sayfa"] == 13
    assert o["ayrinti"]["elektrik"]["atilan"] == {"cerceve_disinda": 0, "ayni_yerde_iki_kez": 1, "isaretten_buyuk": 1}
    assert {k: v for k, v in o.items() if k not in ("elektrik", "ayrinti")} == {k: v for k, v in kh1.items() if k != "ayrinti"}
    assert {k: v for k, v in o["ayrinti"].items() if k != "elektrik"} == kh1["ayrinti"]


# ----------------------------------------------------------------------------- kıyas aracı (K3 adımı)
@pytest.fixture(scope="module")
def proje():
    return _oku(PROJE / "PK01.json")


@pytest.fixture(scope="module")
def k2_ifc(tmp_path_factory, cevap):
    return KH2._ifc(tmp_path_factory.mktemp("k3") / "k2.ifc", KH2._k2_parcalari(cevap))


def test_k3_adimi_k2nin_kapisini_tasir(proje):
    A = proje["kiyas"]["adimlar"]
    assert A["K3"]["kapi"] == A["K2"]["kapi"] and A["K3"]["metre"] == A["K2"]["metre"]
    assert A["K3"]["anahtarlar"] == A["K2"]["kapi"] + [f"elektrik.{k}" for k in PO.ELEKTRIK]
    assert proje["ayar"]["ek_bolumler"] == [*PO.EK_BOLUMLER, "elektrik"]


def test_k3_elektrik_satirlari_bilgi(k2_ifc, cevap, proje):
    """Elektrik parçası olmayan doğru bir K2 modeli K3'ün kapısından geçer; elektrik satırları "modelde yok" yazar, kapıda değildir."""
    k = KY.kiyasla(k2_ifc, cevap, proje, "K3")
    s = {x["anahtar"]: x for x in k["satirlar"]}
    assert k["kapi_1"] == "geçer" and {m["sonuc"] for m in k["metre"]} == {"geçer"}
    el = {a: x for a, x in s.items() if a.startswith("elektrik.")}
    assert len(el) == 9 and {x["sonuc"] for x in el.values()} == {"modelde yok"} and not any(x["kapida"] for x in el.values())
    assert el["elektrik.priz_tekli"]["paftadan"] == 15 and el["elektrik.zil"]["paftadan"] == 0
    rapor = KY.md(k).splitlines()
    assert "| `elektrik.glop` | 2 | — | — | modelde yok | bilgi | modelde yok |" in rapor
    assert "Kapı 1 (adet ve metre, PK-01, K3): **geçer**." in rapor


def test_k3_elektrik_farki_kapiyi_degistirmez(tmp_path, cevap, proje):
    """Kart sözleşmesiyle sayılan elektrik satırı (K3 modeli böyle sayılır) paftadan farklıysa "geçmez" yazar ama kapıyı durdurmaz:
    elektrikte ölçüt Patron'un kuralıdır (plan §5)."""
    p = KH2._k2_parcalari(cevap) + [("IfcLightFixture", f"DUY_{i}", "elektrik.tavan_armaturu", None) for i in range(5)]
    k = KY.kiyasla(KH2._ifc(tmp_path / "k3.ifc", p), cevap, proje, "K3")
    s = {x["anahtar"]: x for x in k["satirlar"]}
    assert (s["elektrik.tavan_armaturu"]["modelden"], s["elektrik.tavan_armaturu"]["sonuc"]) == (5, "geçmez") and k["kapi_1"] == "geçer"


def test_k3_elektrik_teyidi_butun_satirlari_bekletir(k2_ifc, cevap, proje):
    """Kıyas aracı `elektrik` bölümünü tanımaz (KH-3'te değişmedi): elektrik teyitteyse hangi satırı etkilediğini bilemez, bütün satırlar
    bekler ve kapı geçmez (daha sıkı)."""
    c = copy.deepcopy(cevap)
    del c["elektrik"]
    c["teyit_bekliyor"] = [{"bolum": "elektrik", "neden": "anahtar dairesinde bir ya da iki olmayan tırnak: [0]"}]
    k = KY.kiyasla(k2_ifc, c, proje, "K3")
    assert {x["sonuc"] for x in k["satirlar"]} == {"teyit bekliyor"} and {m["sonuc"] for m in k["metre"]} == {"teyit bekliyor"}
    assert k["kapi_1"] == "geçmez"
    assert "- elektrik: anahtar dairesinde bir ya da iki olmayan tırnak: [0] (bölüm tanınmıyor; bütün satırlar teyit bekliyor)" in KY.md(k).splitlines()


def test_k2_adimi_degismedi(k2_ifc, cevap, proje):
    k = KY.kiyasla(k2_ifc, cevap, proje, "K2")
    assert k["kapi_1"] == "geçer" and not any(x["anahtar"].startswith("elektrik.") for x in k["satirlar"])
