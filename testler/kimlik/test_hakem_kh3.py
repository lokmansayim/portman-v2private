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
  çaprazsız ve BUAT yazısız daire, tam olmayan daire (eğrilerle çizilmiş elmas, yıldız; açık ya da yarısı iki kez), çaprazı eksik ya da
  içinde BUAT yazan glop, lejantta çaprazsız glop, sap boyundan yakın ya da
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
KIRMIZI, TURUNCU, SIYAH, MAVI = (1.0, 0.0, 0.0), (1.0, 0.247, 0.0), (0.0, 0.0, 0.0), (0.29, 0.365, 0.584)
KOYU_KIRMIZI = (0.804, 0.125, 0.153)                               # PK-01'in sayfasında da var; kırmızıya yakın ton
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

    def __init__(self, doc, rot: int = 270, glop_tek_yol: bool = False, anahtar_yonler=None):
        self.s = T.Sayfa(doc, rot) if rot in (0, 270) else Donuk(doc, rot)
        self.glop_tek_yol = glop_tek_yol                           # glopun çaprazları tek bir PDF yolunda
        self.anahtar_yonler = anahtar_yonler                       # bütün anahtarların (lejant dahil) tırnak yönleri

    def p(self, X, Y):
        return self.s.ters(X, Y)

    def cizgi(self, a, b, renk=KIRMIZI):
        self.s.pg.draw_line(self.p(*a), self.p(*b), color=renk, width=0.4)

    def daire(self, X, Y, r, renk=KIRMIZI, ic=None):
        """`ic` verilirse aynı PDF yolunda bu yarıçapta ikinci bir daire."""
        sh = self.s.pg.new_shape()
        for yc in (r, ic) if ic else (r,):
            sh.draw_circle(self.p(X, Y), yc)
        sh.finish(color=renk, width=0.4)
        sh.commit()

    def yol(self, parcalar, renk=KIRMIZI):
        """Birden çok çizgi tek bir PDF yolunda (path)."""
        sh = self.s.pg.new_shape()
        for a, b in parcalar:
            sh.draw_line(self.p(*a), self.p(*b))
        sh.finish(color=renk, width=0.4, closePath=False)
        sh.commit()

    def kutu(self, X, Y, w, h, renk, dolgu=None, ic=None):
        """`ic` (en, boy) verilirse aynı PDF yolunda ortası aynı ikinci bir dörtgen."""
        sh = self.s.pg.new_shape()
        for w2, h2 in ((w, h), ic) if ic else ((w, h),):
            a, b = self.p(X - w2 / 2, Y - h2 / 2), self.p(X + w2 / 2, Y + h2 / 2)
            sh.draw_rect(fitz.Rect(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)))
        sh.finish(color=renk, fill=dolgu, width=0.3)
        sh.commit()

    def yazi(self, X, Y, metin, boy=7):
        w = fitz.Font(fontfile=T.FONT).text_length(metin, boy)
        self.s.pg.insert_text(self.p(X - w / 2, Y + 0.35 * boy), metin, fontsize=boy, fontname="ls", fontfile=T.FONT, rotate=self.s.rot)

    # işaretler (ortası görünen X, Y)
    def duy(self, X, Y, a=12.0):
        self.kutu(X, Y, a, a, KIRMIZI, KIRMIZI)
        self.cizgi((X - 4, Y - 4), (X + 4, Y + 4))
        self.cizgi((X - 4, Y + 4), (X + 4, Y - 4))

    def glop(self, X, Y, capraz=2, ic=None):
        self.daire(X, Y, 9.5, ic=ic)
        cs = (((X - 6.7, Y - 6.7), (X + 6.7, Y + 6.7)), ((X - 6.7, Y + 6.7), (X + 6.7, Y - 6.7)))[:capraz]
        if self.glop_tek_yol and cs:
            self.yol(cs)
            return
        for a, b in cs:
            self.cizgi(a, b)

    def buat(self, X, Y, yazili=True, ic=None):
        self.daire(X, Y, 9.5, ic=ic)
        if yazili:
            self.yazi(X, Y, "BUAT", 3)

    def anahtar(self, X, Y, tirnak=1, boy=4.6, uc=2.4, acilar=(-60, -120, -30), yonler=None, don=0, ayna=False, uc_yonler=None, ic=None):
        """Tırnaklar dairenin `acilar`daki yerlerinden çıkar; çizgileri `yonler`e (verilmezse yarıçap boyunca); ucundaki kısa çizgi
        `uc_yonler`e (verilmezse yatay). Bütün işaret `ayna` ile yatay eksene göre aynalanır, sonra `don` derece döndürülür."""
        yonler = yonler or self.anahtar_yonler

        def d(x, y):
            y = -y if ayna else y
            c, s = math.cos(math.radians(don)), math.sin(math.radians(don))
            return X + x * c - y * s, Y + x * s + y * c
        self.daire(X, Y, 4.5, TURUNCU, ic=ic)
        for i, aci in enumerate(acilar[:tirnak]):
            c, s = math.cos(math.radians(aci)), math.sin(math.radians(aci))
            b = (4.5 * c, 4.5 * s)
            if yonler:
                c, s = math.cos(math.radians(yonler[i])), math.sin(math.radians(yonler[i]))
            e = (b[0] + boy * c, b[1] + boy * s)
            self.cizgi(d(*b), d(*e), TURUNCU)
            if uc:
                u = math.radians(uc_yonler[i]) if uc_yonler else 0.0
                self.cizgi(d(*e), d(e[0] + uc * math.cos(u), e[1] + uc * math.sin(u)), TURUNCU)   # tırnağın ucundaki kısa çizgi

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

    def sigorta(self, X, Y, desen=False, ic=None):
        self.kutu(X, Y, 14, 10, SIYAH, ic=ic)
        self.cizgi((X - 4, Y), (X + 4, Y), SIYAH)
        if desen:                                                  # iç desen başka renkte (PK-07'deki gri-mavi gibi)
            self.cizgi((X - 4, Y + 2.5), (X + 4, Y + 2.5), MAVI)

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
                 caprazsiz_glop: bool = False, lejant_tirnaksiz: bool = False, sigorta_deseni: bool = False,
                 lejant_tek_tirnak: bool = False, glop_tek_yol: bool = False, anahtar_yonler: tuple | None = None, ek=None) -> Path:
    """KH-1'in sentetik paftası + elektrik sayfası. Bina 600 × 400 cm (montajın dış ölçüsü); lejant binanın sağında. `ek(e)`: sayfa
    döndürülmeden önce eklenen bozma."""
    gecici = yol.with_suffix(".kh1.pdf")
    T.sentetik(gecici, **(taban or {}))
    doc = fitz.open(gecici)
    e = Elektrik(doc, rot, glop_tek_yol, anahtar_yonler)
    if not duvarsiz:
        T._dis_cizgi(e.s)
    if oran:                                                       # duvar çizgisi 450 cm'ye uzar: sınır dış ölçüye oturmaz
        e.s.cizgi((0, 400), (0, 450), T.DUVAR)
    # lejant (binanın sağında; dik sayfaya da sığar)
    e.yazi(710, 300, "LEJANT", 12)
    satir = {"anahtar": (330, ["ANAHTAR"], lambda X, Y: e.anahtar(X, Y, 0 if lejant_tirnaksiz else 1 if lejant_tek_tirnak else 2)), "priz": (355, ["PRİZ"], lambda X, Y: e.priz(X, Y)),
             "glop": (385, ["GLOP"], lambda X, Y: e.glop(X, Y, 0 if caprazsiz_glop else 2)), "duy": (412, ["TİJLİ", "DUY"], lambda X, Y: e.duy(X, Y + 3)),
             "sigorta": (445, ["SİGORTA", "KUTUSU"], lambda X, Y: e.sigorta(X, Y + 3, sigorta_deseni))}
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
    e.sigorta(*g(*SIGORTA), sigorta_deseni)
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
    assert (L["anahtar"]["tirnak"], L["anahtar"]["uc"], L["anahtar"]["aci"]) == (4.6, 2.4, 60.0)
    assert (L["anahtar"]["isin_aci"], L["anahtar"]["sapma"], L["anahtar"]["uc_aci"]) == (60.0, 0.0, 60.0)
    assert L["glop"]["capraz_aci"] == [90.0]
    assert L["priz"]["aci"] == {"kol_kol": 0.0, "kol_taban": 90.0, "sap_taban": 90.0}
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


def _u_parcalari(X, Y, k=1.0, z=False):
    """Kolları yukarı bakan U'nun dört parçası (taban, iki kol, sap): `k` ölçü çarpanı; `z` kollardan biri ters yana (Z biçimi)."""
    a, b = (X - 4.25 * k, Y), (X + 4.25 * k, Y)
    return [(a, b), (a, (a[0], a[1] - 4.9 * k)), (b, (b[0], b[1] + (4.9 if z else -4.9) * k)), ((X, Y), (X, Y + 7.8 * k))]


def _u(e, X, Y, renk=KIRMIZI, k=1.0, z=False):
    """Elle çizilmiş U, her parçası ayrı yolda."""
    for a, b in _u_parcalari(X, Y, k, z):
        e.cizgi(a, b, renk)


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


X_A, Y_A = g(250, 120)                                             # 2. turun anahtar bozmalarının yeri
X_U, Y_U = g(250, 250)


def _tirnak_yana_kaymis(e):
    """Tekli anahtarın tırnağı 0,7 pt yana kaydırılarak ikinci kez çizilmiş (koşut iki tırnak)."""
    e.anahtar(X_A, Y_A, 1)
    c, s = math.cos(math.radians(-60)), math.sin(math.radians(-60))
    b = (X_A + 4.5 * c - 0.7 * s, Y_A + 4.5 * s + 0.7 * c)
    e.cizgi(b, (b[0] + 4.6 * c, b[1] + 4.6 * s), TURUNCU)


@pytest.mark.parametrize("ek, kw, neden", [
    # kaydırılarak iki kez çizilmiş işaret iki sayılmaz
    (lambda e: [e.anahtar(X_A, Y_A + d, 1) for d in (0, 1.0)], {},
     "kutusu aynı türden bir başkasıyla kesişen 1 işaret çifti (aynı işaret kaydırılarak iki kez çizilmiş olabilir)"),
    (lambda e: [e.anahtar(X_A + d, Y_A, 1) for d in (0, 6.0)], {},
     "kutusu aynı türden bir başkasıyla kesişen 1 işaret çifti (aynı işaret kaydırılarak iki kez çizilmiş olabilir)"),
    (lambda e: [e.glop(X_U + d, Y_U) for d in (0, 4.0)], {},
     "kutusu aynı türden bir başkasıyla kesişen 1 işaret çifti (aynı işaret kaydırılarak iki kez çizilmiş olabilir)"),
    (_tirnak_yana_kaymis, {},
     "iki tırnağının dizilişi lejanttakine (60° / 60°) uymayan 1 anahtar dairesi (9° / 0°; değdikleri yerlerin ve çizgilerin açı farkı)"),
    # tırnağın ve ucunun boyu
    (lambda e: e.anahtar(X_A, Y_A, 1, boy=25.0), {}, "anahtar dairesine değen, boyu lejanttaki tırnaktan farklı 1 eğik çizgi"),
    (lambda e: e.anahtar(X_A, Y_A, 1, uc=40.0), {}, "tırnağın ucunda boyu lejanttakinden farklı 1 çizgi"),
    (lambda e: e.anahtar(X_A, Y_A, 1, uc=0), {}, "ucunda lejanttaki kısa çizgi olmayan 1 tırnak"),
    (None, {"lejant_tirnaksiz": True}, "lejantta anahtar dairesinde tırnak yok: tekli ve çift ayrılamaz"),
    # aynı PDF yolunda U ile fazla çizgi
    (lambda e: e.yol(_u_parcalari(X_U, Y_U) + [((X_U + 40, Y_U), (X_U + 55, Y_U))]), {},
     "bir parçası işarete giren ama başka parçası hiçbir işarete girmeyen 1 çizim"),
    (lambda e: e.yol(_u_parcalari(X_U, Y_U) + [p for i, p in enumerate(_u_parcalari(X_U + 40, Y_U)) if i != 2]), {},
     "bir parçası işarete giren ama başka parçası hiçbir işarete girmeyen 1 çizim"),
    (lambda e: e.yol(_u_parcalari(X_U, Y_U) + _u_parcalari(X_U + 40, Y_U, z=True)), {},
     "bir parçası işarete giren ama başka parçası hiçbir işarete girmeyen 1 çizim"),
    # glop çaprazının boyu, çift prizin yönü
    (lambda e: (e.daire(X_U, Y_U, 9.5), e.cizgi((X_U - 1, Y_U - 1), (X_U + 0.06, Y_U + 0.06)), e.cizgi((X_U - 1, Y_U + 1), (X_U + 0.06, Y_U - 0.06))),
     {}, "glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    (lambda e: (lambda uc: e.priz(uc[0], uc[1], (1, 0)))(e.priz(X_U, Y_U)), {}, "sapı öbürünün tabanına değen ama yönü farklı 1 U çifti"),
    # renk ve ayıklama payı
    (lambda e: e.cizgi((X_U, Y_U), (X_U + 8, Y_U), MAVI), {"sigorta_deseni": True},
     "sigortanın iç desenindeki ya da lejant rengine yakın tonda, hiçbir işarete uymayan 1 öğe (çizgi 8.0 pt × 1)"),
    (lambda e: e.cizgi(g(300, -150), g(330, -150), KOYU_KIRMIZI), {}, "duvar çerçevesinin 30 cm dışında lejant renginde 1 öğe: sayılmadı"),
    (lambda e: (lambda X, Y: e.cizgi((X - 4.05, Y), (X - 4.05, Y - 4.9)))(*g(*UYDU)), {},
     "lejant renginde, hiçbir işarete uymayan 5 öğe (çizgi 4.9 pt × 3, çizgi 7.8 pt × 1, çizgi 8.5 pt × 1)"),
], ids=["anahtar_dikey_1", "anahtar_yatay_6", "glop_4", "tirnak_kaymis", "uzun_tirnak", "uzun_uc", "ucsuz_tirnak", "lejant_tirnaksiz",
        "yol_serbest_cizgi", "yol_eksik_u", "yol_z_u", "glop_centik", "dik_cift_priz", "sigorta_deseni_basibos", "disarida_yakin_ton",
        "kolun_yaninda_cizgi"])
def test_kaymis_kopya_tirnak_ve_yol_bekletir(tmp_path, ek, kw, neden):
    """KH-3 hakeminin 2. turu: kaydırılarak iki kez çizilmiş anahtar, glop ve tırnak; boyu tutmayan tırnak ve uç; aynı PDF yolunda U'nun
    yanındaki fazla çizgi; kısa glop çaprazı; yönü farklı çift priz; sigortanın iç desen renginde ve çerçeve dışında yakın tonda öğe; kolun
    0,2 pt yanındaki ikinci çizgi (kopya sayılmaz: ayıklama payı 0,05 pt) de elektriği bekletir."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


EGIK = (-40, -140)                                                 # yarıçapla 20° açılı, birbirinden uzaklaşan iki tırnak


def _ikinci_u_donuk(e, derece):
    """Çift prizin ikinci U'su `derece` döndürülmüş (sapı birincinin tabanına değer)."""
    uc = e.priz(X_U, Y_U)
    r = math.radians(derece)
    e.priz(uc[0], uc[1], (math.sin(r), -math.cos(r)))


@pytest.mark.parametrize("ek, kw, neden", [
    # tırnakların dizilişi
    (lambda e: e.anahtar(X_A, Y_A, 2, acilar=(-60, 66)), {},
     "iki tırnağının dizilişi lejanttakine (60° / 60°) uymayan 1 anahtar dairesi (126° / 54°; değdikleri yerlerin ve çizgilerin açı farkı)"),
    (lambda e: e.anahtar(X_A, Y_A, 2, acilar=(-60, -40)), {},
     "iki tırnağının dizilişi lejanttakine (60° / 60°) uymayan 1 anahtar dairesi (20° / 20°; değdikleri yerlerin ve çizgilerin açı farkı)"),
    # yarıçapla açıları ve uçları lejanttaki gibi, yalnız çizgilerin açı farkı başka (-5°: iki tırnak da eğik kalsın)
    (lambda e: e.anahtar(X_A, Y_A, 2, yonler=(-40, -100), uc_yonler=(0, -140), don=-5), {"anahtar_yonler": EGIK},
     "iki tırnağının dizilişi lejanttakine (60° / 80°) uymayan 1 anahtar dairesi (60° / 60°; değdikleri yerlerin ve çizgilerin açı farkı)"),
    (lambda e: e.anahtar(X_A, Y_A, 1, acilar=(-60,), yonler=(-30,)), {}, "yarıçapla açısı lejanttakinden (0°) farklı 1 tırnak (30°)"),
    (lambda e: e.anahtar(X_A, Y_A, 2, acilar=(-60, -120), yonler=(-30, 210)), {}, "yarıçapla açısı lejanttakinden (0°) farklı 2 tırnak (30°, 30°)"),
    (lambda e: e.anahtar(X_A, Y_A, 1, uc=0) or (lambda c, s: e.cizgi((X_A + 9.1 * c, Y_A + 9.1 * s), (X_A + 11.5 * c, Y_A + 11.5 * s), TURUNCU))(
        math.cos(math.radians(-60)), math.sin(math.radians(-60))), {}, "tırnağın ucunda tırnakla açısı lejanttakinden (60°) farklı 1 çizgi"),
    (None, {"lejant_tek_tirnak": True}, "lejantta iki tırnaklı anahtar yok: 1 iki tırnaklı anahtarın dizilişi denetlenemez"),
    # glop: tek çapraz iki kez; tek yoldaki çaprazlara eklenen çizgi
    (lambda e: (e.glop(X_U, Y_U, 1), e.cizgi((X_U - 6.7, Y_U - 6.4), (X_U + 6.7, Y_U + 7.0))), {},
     "çaprazlarının arasındaki açı lejanttakine uymayan 1 glop (bir çapraz iki kez çizilmiş olabilir)"),
    (lambda e: (e.daire(X_U, Y_U, 9.5), [e.cizgi((X_U - 9.45 * math.cos(math.radians(a)), Y_U - 9.45 * math.sin(math.radians(a))),
                                                   (X_U + 9.45 * math.cos(math.radians(a)), Y_U + 9.45 * math.sin(math.radians(a)))) for a in (45, 105)]),
     {}, "çaprazlarının arasındaki açı lejanttakine uymayan 1 glop (bir çapraz iki kez çizilmiş olabilir)"),
    (lambda e: (e.daire(X_U, Y_U, 9.5), e.yol([((X_U - 6.7, Y_U - 6.7), (X_U + 6.7, Y_U + 6.7)), ((X_U - 6.7, Y_U + 6.7), (X_U + 6.7, Y_U - 6.7)),
                                              ((X_U - 5, Y_U), (X_U + 5, Y_U))])),
     {"glop_tek_yol": True}, "glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    # başka türden işaretin içine çizilmiş U
    (lambda e: e.priz(*g(*BUAT[0])), {}, "kutusunun ortası başka türden bir işaretin kutusunda olan 2 işaret (biri öbürünün içine çizilmiş olabilir)"),
    (lambda e: e.priz(*g(*DUY[0])), {}, "kutusunun ortası başka türden bir işaretin kutusunda olan 2 işaret (biri öbürünün içine çizilmiş olabilir)"),
    (lambda e: e.priz(*g(*GLOP[0])), {}, "kutusunun ortası başka türden bir işaretin kutusunda olan 2 işaret (biri öbürünün içine çizilmiş olabilir)"),
    # kaydırılarak iki kez çizilmiş duy ve sigorta (tek kümeye girer)
    (lambda e: (lambda X, Y: e.duy(X + 3, Y))(*g(*DUY[0])), {}, "duy renginde, ölçüsü lejanttakinden (12.0 × 12.0 pt) farklı 1 dolgu (15.0 × 12.0 pt)"),
    (lambda e: (lambda X, Y: e.sigorta(X + 3, Y, True))(*g(*SIGORTA)), {"sigorta_deseni": True},
     "sigortanın iç desenindeki ya da lejant rengine yakın tonda, hiçbir işarete uymayan 2 öğe (çizgi 8.0 pt × 2)"),
    # çift prizin ikinci U'su 12° dönük
    (lambda e: _ikinci_u_donuk(e, 12), {}, "sapı öbürünün tabanına değen ama yönü farklı 1 U çifti"),
], ids=["aynali_tirnak", "yirmi_derece", "ayni_yana_egik", "sapik_tekli", "ters_egik_cift", "uc_tirnagin_uzantisi", "lejant_tek_tirnak", "glop_capraz_iki_kez", "glop_capraz_60",
        "glop_yolunda_fazla_cizgi", "buat_icinde_u", "duy_icinde_u", "glop_icinde_u", "duy_kaymis", "sigorta_kaymis", "cift_priz_12"])
def test_dizilis_desen_ve_ic_ice_bekletir(tmp_path, ek, kw, neden):
    """KH-3 hakeminin 3. turu: aynalanmış, yarıçapa göre eğik ya da başka açıda tırnak; yalnız çizgilerinin açı farkı lejanttakinden başka
    çift; tırnağın uzantısı olan uç; lejantta iki tırnaklı anahtar yokken iki tırnaklı anahtar; tek çaprazı iki kez çizilmiş glop; tek
    yoldaki çaprazlara eklenen çizgi; başka türden işaretin içine çizilmiş U; kaydırılarak iki kez çizilmiş duy ve sigorta; ikinci U'su 12°
    dönük çift priz de elektriği bekletir."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


GLOP_BICIMSIZ = "glop renginde ve çapında, tam daire olmayan 1 eğri yolu (eğrileri çemberin dışında, açık ya da iki kez geçilmiş)"
ANAHTAR_BICIMSIZ = ("anahtar dairesinin renginde ve çapında, tam daire olmayan 1 eğri yolu (eğrileri çemberin dışında, açık ya da iki kez "
                    "geçilmiş)")


def _u_acili(e, X, Y, kollar=(0, 0), sap=0, don=0):
    """Taban ortası (X, Y), kollar yukarı, sap aşağı bir U; kolların ve sapın tabana dik yönden sapması `kollar` ve `sap` (derece), bütün
    U'nun (X, Y) çevresinde dönüşü `don`. Sapın ucu döner."""
    def d(x, y):
        c, s = math.cos(math.radians(don)), math.sin(math.radians(don))
        return X + x * c - y * s, Y + x * s + y * c

    def yon(aci, boy, taban):
        return taban[0] + boy * math.sin(math.radians(aci)), taban[1] + boy * math.cos(math.radians(aci))
    a, b = (-4.25, 0), (4.25, 0)
    e.cizgi(d(*a), d(*b))
    for u, aci in zip((a, b), kollar):
        e.cizgi(d(*u), d(*yon(180 + aci, 4.9, u)))
    uc = d(*yon(sap, 7.8, (0, 0)))
    e.cizgi((X, Y), uc)
    return uc


@pytest.mark.parametrize("ek, kw, neden", [
    # PDF yolunda işaretin dairesine ya da kutusuna eklenmiş ikinci daire ya da dörtgen; tek yoldaki çaprazın biri kısa. 5. turdan beri
    # içteki dairenin eğrileri çemberin üstünde olmadığından yol daire sayılmaz (önceden yolun yapısı tutmuyordu; ikisi de bekletir)
    (lambda e: e.glop(X_U, Y_U, ic=3), {}, GLOP_BICIMSIZ),
    (lambda e: e.buat(X_U, Y_U, ic=3), {}, GLOP_BICIMSIZ),
    (lambda e: e.anahtar(X_A, Y_A, 1, ic=2), {}, ANAHTAR_BICIMSIZ),
    (lambda e: e.sigorta(X_U, Y_U, ic=(8, 5)), {}, "sigorta kutusu ölçüsünde, içi lejanttaki işarete uymayan 1 kutu"),
    (lambda e: (e.daire(X_U, Y_U, 9.5), e.yol([((X_U - 6.7, Y_U - 6.7), (X_U + 6.7, Y_U + 6.7)), ((X_U - 2, Y_U + 2), (X_U + 2, Y_U - 2))])),
     {"glop_tek_yol": True}, "glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe (1 daire)"),
    # U'nun açıları: kolu açık, kolları eğik (paralelkenar), sapı eğik; ikinci U'su dönük ama sapı birincininkiyle aynı yönde çift
    (lambda e: _u_acili(e, X_U, Y_U, kollar=(0, 20)), {}, "açıları lejanttakine (kollar 0°, kol–taban 90°, sap–taban 90°) uymayan 1 U"),
    (lambda e: _u_acili(e, X_U, Y_U, kollar=(8, -8)), {}, "açıları lejanttakine (kollar 0°, kol–taban 90°, sap–taban 90°) uymayan 1 U"),
    (lambda e: _u_acili(e, X_U, Y_U, kollar=(45, 45)), {}, "açıları lejanttakine (kollar 0°, kol–taban 90°, sap–taban 90°) uymayan 1 U"),
    (lambda e: _u_acili(e, X_U, Y_U, sap=45), {}, "açıları lejanttakine (kollar 0°, kol–taban 90°, sap–taban 90°) uymayan 1 U"),
    (lambda e: _u_acili(e, *e.priz(X_U, Y_U), don=12, sap=12), {}, "açıları lejanttakine (kollar 0°, kol–taban 90°, sap–taban 90°) uymayan 1 U"),
    # çift prizin ikinci U'su payın hemen dışında
    (lambda e: _ikinci_u_donuk(e, 10.5), {}, "sapı öbürünün tabanına değen ama yönü farklı 1 U çifti"),
], ids=["glop_yolunda_daire", "buat_yolunda_daire", "anahtar_yolunda_daire", "sigorta_yolunda_dortgen", "tek_yolda_kisa_capraz",
        "u_kolu_acik", "u_kollari_8_derece", "u_paralelkenar", "u_sapi_egik", "ikinci_u_sapi_duz", "cift_priz_10_5"])
def test_yol_ve_u_acisi_bekletir(tmp_path, ek, kw, neden):
    """KH-3 hakeminin 4. turu: işaretin PDF yoluna eklenmiş daire ya da dörtgen, tek yoldaki kısa çapraz; açıları lejanttakine uymayan U
    (kolu açık; kolları tabanla payın içinde ama birbirine 16° açılı; paralelkenar; sapı eğik; 12° dönük ikinci U'nun sapı birincinin
    sapıyla aynı yönde); ikinci U'su 10,5° dönük çift priz de elektriği bekletir."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


def _egri_yol(e, X, Y, r, renk, bicim, ters=False, k=0.5523, d=0.0, yaylar=None):
    """Kübik eğrilerle (c) çizilmiş yol; kutusu dairenin kutusu. Çeyrek dairenin kontrol noktası yarıçapın `k` katı (0,5523 çember;
    küçüğü basık); `d` pt ile iki kontrol noktası ters yönde kayar (eğrinin ortası çemberde kalır, çeyrekleri dalgalanır). `daire`: dört
    çeyrek (`ters` ile öbür yöne); `elmas`: eğriler düz; `yildiz`: dördü içe bükük; `girintili`: bir çeyreği içe bükük; `c`: dördüncü
    çeyrek yerine üçüncüsü geri geçilir (açık); `yarim`: karşı iki çeyrek ikişer kez (gidip dönerek); `karisik`: dört çeyrek karışık
    sırayla, ikisi öbür yöne (ayrı alt yollar; tam daire). `yaylar` verilirse `bicim` yok sayılır: her (baş, son) açı çifti (derece, baştan
    sona) çemberin üstünde bir kübik yaydır (boşluklu, örtüşen ya da iki kez çizilmiş daire için)."""
    uc = [(X + r, Y), (X, Y + r), (X - r, Y), (X, Y - r), (X + r, Y)]
    egriler = []
    for i in range(4):
        a, b = uc[i], uc[i + 1]
        if bicim in ("daire", "c", "yarim", "karisik"):
            t0, t1, tm = math.radians(90 * i), math.radians(90 * (i + 1)), math.radians(90 * i + 45)
            c1 = (a[0] - k * r * math.sin(t0) - d * math.sin(tm), a[1] + k * r * math.cos(t0) + d * math.cos(tm))
            c2 = (b[0] + k * r * math.sin(t1) + d * math.sin(tm), b[1] - k * r * math.cos(t1) - d * math.cos(tm))
        elif bicim == "yildiz":
            c1, c2 = (X + (a[0] - X) * 0.2, Y + (a[1] - Y) * 0.2), (X + (b[0] - X) * 0.2, Y + (b[1] - Y) * 0.2)
        else:
            c1, c2 = (a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3), (a[0] + 2 * (b[0] - a[0]) / 3, a[1] + 2 * (b[1] - a[1]) / 3)
            if bicim == "girintili" and i == 0:
                c1, c2 = (X + (c1[0] - X) * 0.3, Y + (c1[1] - Y) * 0.3), (X + (c2[0] - X) * 0.3, Y + (c2[1] - Y) * 0.3)
        egriler.append((a, c1, c2, b))
    geri = [tuple(reversed(x)) for x in egriler]
    if bicim == "c":
        egriler = egriler[:3] + [geri[2]]
    elif bicim == "yarim":
        egriler = [egriler[0], geri[0], egriler[2], geri[2]]
    elif bicim == "karisik":
        egriler = [egriler[2], geri[0], egriler[3], geri[1]]
    if yaylar:
        egriler = []
        for a0, a1 in yaylar:
            t0, t1 = math.radians(a0), math.radians(a1)
            h = 4 / 3 * math.tan((t1 - t0) / 4) * r
            p0, p3 = (X + r * math.cos(t0), Y + r * math.sin(t0)), (X + r * math.cos(t1), Y + r * math.sin(t1))
            egriler.append((p0, (p0[0] - h * math.sin(t0), p0[1] + h * math.cos(t0)), (p3[0] + h * math.sin(t1), p3[1] - h * math.cos(t1)), p3))
    sh = e.s.pg.new_shape()
    for eg in ([tuple(reversed(x)) for x in reversed(egriler)] if ters else egriler):
        sh.draw_bezier(*(e.p(*q) for q in eg))
    sh.finish(color=renk, width=0.4, closePath=False)
    sh.commit()


def _glop_bicimli(e, X, Y, bicim, ters=False, **kw):
    _egri_yol(e, X, Y, 9.5, KIRMIZI, bicim, ters, **kw)
    for a, b in (((X - 6.7, Y - 6.7), (X + 6.7, Y + 6.7)), ((X - 6.7, Y + 6.7), (X + 6.7, Y - 6.7))):
        e.cizgi(a, b)


def _anahtar_bicimli(e, X, Y, bicim, ters=False, **kw):
    """Tekli anahtar (`Elektrik.anahtar` ile aynı tırnak ve uç), dairesi `_egri_yol` ile."""
    _egri_yol(e, X, Y, 4.5, TURUNCU, bicim, ters, **kw)
    c, s = math.cos(math.radians(-60)), math.sin(math.radians(-60))
    b = (X + 4.5 * c, Y + 4.5 * s)
    t = (b[0] + 4.6 * c, b[1] + 4.6 * s)
    e.cizgi(b, t, TURUNCU)
    e.cizgi(t, (t[0] + 2.4, t[1]), TURUNCU)


@pytest.mark.parametrize("ek, kw, neden", [
    # eğrilerle çizilmiş daire olmayan yol: uçları ve kutusu dairenin, eğrileri çemberin üstünde değil
    (lambda e: _glop_bicimli(e, X_U, Y_U, "elmas"), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "yildiz"), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "girintili"), {}, GLOP_BICIMSIZ),
    (lambda e: (_egri_yol(e, X_U, Y_U, 9.5, KIRMIZI, "elmas"), e.yazi(X_U, Y_U, "BUAT", 3)), {},
     GLOP_BICIMSIZ),
    (lambda e: _anahtar_bicimli(e, X_A, Y_A, "elmas"), {},
     ANAHTAR_BICIMSIZ),
    (lambda e: _glop_bicimli(e, 665, 385, "elmas"), {"lejant_isaretsiz": "glop"}, "lejantta 'glop' etiketinin işareti okunamadı"),
    # çift prizin ikinci U'su: tabanı 15° dönük, sapı kendi tabanına 9°, birincinin sapına 6° (yön sapın yönünden okunsa çift sayılırdı)
    (lambda e: _u_acili(e, *e.priz(X_U, Y_U), don=15, sap=9), {}, "sapı öbürünün tabanına değen ama yönü farklı 1 U çifti"),
    # U'nun iki kolu da tabanla denetlenir: kolların arası 9° (pay içinde), ikinci kol tabana 73°
    (lambda e: _u_acili(e, X_U, Y_U, kollar=(8, 17)), {}, "açıları lejanttakine (kollar 0°, kol–taban 90°, sap–taban 90°) uymayan 1 U"),
], ids=["glop_elmas", "glop_yildiz", "glop_ceyregi_ice_bukuk", "buat_elmas", "anahtar_elmas", "lejantta_elmas_glop", "ikinci_u_tabani_15",
        "u_kollari_8_17"])
def test_daire_bicimi_ve_u_yonu_bekletir(tmp_path, ek, kw, neden):
    """KH-3 hakeminin 5. turu: glop, BUAT ya da anahtar dairesinin renginde ve çapında, eğrileri çemberin üstünde olmayan yol (eğrilerle
    çizilmiş elmas, yıldız, bir çeyreği içe bükük daire; lejanttaki de); tabanı payın dışında dönük, sapı birincinin sapıyla payın içinde
    ikinci U; iki kolu birbirine payın içinde, biri tabana payın dışında açılı U da elektriği bekletir."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


@pytest.mark.parametrize("ek, kw, neden", [
    # çeyrekleri çemberin üstünde, kutusu ve eğri sayısı dairenin; ama açık ya da yarısı iki kez geçilmiş
    (lambda e: _glop_bicimli(e, X_U, Y_U, "c"), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "yarim"), {}, GLOP_BICIMSIZ),
    (lambda e: (_egri_yol(e, X_U, Y_U, 9.5, KIRMIZI, "c"), e.yazi(X_U, Y_U, "BUAT", 3)), {}, GLOP_BICIMSIZ),
    (lambda e: _anahtar_bicimli(e, X_A, Y_A, "c"), {}, ANAHTAR_BICIMSIZ),                  # tırnak eksik çeyreğe değer
    (lambda e: _anahtar_bicimli(e, X_A, Y_A, "yarim"), {}, ANAHTAR_BICIMSIZ),
    # çembere uzaklığın payı (0,2 pt) ve dokuz nokta: 0,3 pt basık daire; ortası çemberde, çeyrekleri 0,5 pt dalgalı daire
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", k=0.4928), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", d=4.0), {}, GLOP_BICIMSIZ),
    # yayların uç uca değmesi (pay 0,2 pt) ve kapanması: kapanış yerinde 4° açık glop (0,66 pt boşluk); dört yerinden 3° kesik glop ya da
    # bir yerinden 3° örtüşen glop (0,5 pt; dört yerinden örtüşünce kutusu büyür, daire sayılmaz); bir çeyreği iki kez çizilmiş glop (beş
    # eğri); kapanış yerinde 8° açık anahtar dairesi (0,63 pt)
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", yaylar=((0, 90), (90, 180), (180, 270), (270, 356))), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", yaylar=((0, 87), (90, 177), (180, 267), (270, 357))), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", yaylar=((0, 90), (90, 180), (180, 270), (267, 360))), {}, GLOP_BICIMSIZ),
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", yaylar=((0, 90), (90, 180), (180, 270), (270, 360), (90, 0))), {}, GLOP_BICIMSIZ),
    (lambda e: _anahtar_bicimli(e, X_A, Y_A, "daire", yaylar=((0, 90), (90, 180), (180, 270), (270, 352))), {}, ANAHTAR_BICIMSIZ),
], ids=["glop_acik", "glop_yarisi_iki_kez", "buat_acik", "anahtar_acik", "anahtar_yarisi_iki_kez", "glop_0_3_basik", "glop_dalgali",
        "glop_kapanisi_4_acik", "glop_dort_yerden_kesik", "glop_bir_yerden_ortusen", "glop_bir_ceyregi_iki_kez", "anahtar_kapanisi_8_acik"])
def test_daire_tam_ve_kapali_bekletir(tmp_path, ek, kw, neden):
    """KH-3 hakeminin 6. turu: eğrileri çemberin üstünde ama bir çeyreği eksik (yerine komşusu geri geçilmiş) ya da karşı iki çeyreği
    ikişer kez geçilmiş glop, BUAT ve anahtar dairesi; çembere uzaklığı payın dışında (0,3 pt basık; uçları ve ortası çemberde, çeyrekleri
    0,5 pt dalgalı) daire de elektriği bekletir. 7. tur: yayları uç uca değmeyen (kapanış yerinde ya da dört yerinden payın dışında boşluklu
    ya da bir yerinden örtüşen) ya da bir yayı iki kez çizilmiş daire de."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    t = _teyit(o)
    assert set(t) == {"elektrik"} and neden in t["elektrik"], t
    assert "elektrik" not in o and "makas_bas" in o and "h_plani" in o


def test_yolun_yapisi_tur_ve_olcu():
    """`_yapi` her öğenin türünü ve ölçüsünü verir (çizgide ve eğride iki ucunun arası, dörtgende iki kenarı); `_ayni_yapi` öğelerin
    sayısını, türünü ve ölçüsünü karşılaştırır: aynı boyda çizgi ile eğri, başka kenarlı dörtgen, başka boyda eğri, bir ve iki çizgi aynı
    yapı değildir (KH-3 hakeminin 5. turu: sentetik işaretlerde tür ve dörtgenin kenarları imzayla ve kutuyla örtülüyordu)."""
    pg = fitz.open().new_page()
    P = fitz.Point

    def yol(*ogeler):
        sh = pg.new_shape()
        for tur, *v in ogeler:
            {"l": sh.draw_line, "c": sh.draw_bezier, "re": sh.draw_rect}[tur](*v)
        sh.finish(color=KIRMIZI, width=0.4, closePath=False)
        sh.commit()
    yol(("l", P(10, 10), P(15, 10)), ("l", P(10, 20), P(15, 20)))
    yol(("l", P(10, 30), P(15, 30)), ("c", P(10, 40), P(11, 42), P(14, 42), P(15, 40)))
    yol(("re", fitz.Rect(10, 50, 18, 55)))
    yol(("re", fitz.Rect(10, 60, 17, 66)))
    yol(("c", P(10, 70), P(11, 72), P(14, 72), P(15, 70)))
    yol(("c", P(10, 80), P(11, 82), P(15, 82), P(16, 80)))
    yol(("l", P(10, 90), P(15, 90)))
    o = PO._ogeler(pg)
    assert [x["yapi"] for x in o] == [[("l", 5.0), ("l", 5.0)], [("c", 5.0), ("l", 5.0)], [("re", 5.0, 8.0)], [("re", 6.0, 7.0)], [("c", 5.0)],
                                      [("c", 6.0)], [("l", 5.0)]]
    assert all(PO._ayni_yapi(x, x, 0.3) for x in o)
    assert not any(PO._ayni_yapi(o[i], o[j], 0.3) or PO._ayni_yapi(o[j], o[i], 0.3) for i, j in ((0, 1), (2, 3), (4, 5), (0, 6)))


@pytest.mark.parametrize("ek, kw, sayim, atilan", [
    (lambda e: e.yol(_u_parcalari(X_U, Y_U) + _u_parcalari(X_U + 40, Y_U)), {}, {"priz_tekli": 5}, {}),     # tek yolda iki tam U: iki priz
    (None, {"sigorta_deseni": True}, {}, {}),                                                               # iç desenli sigorta
    (lambda e: e.kutu(*g(300, 420), 120, 20, KOYU_KIRMIZI), {}, {}, {"isaretten_buyuk": 1}),              # başlığın yakın tonda çerçevesi
    (lambda e: e.anahtar(X_A, Y_A, 2, don=90), {}, {"anahtar_cift": 2}, {}),                               # 90° döndürülmüş çift anahtar
    (lambda e: e.anahtar(X_A, Y_A, 2, ayna=True, don=-15), {}, {"anahtar_cift": 2}, {}),                   # aynalanmış çift anahtar
    (None, {"glop_tek_yol": True}, {}, {}),                                                                 # çaprazları tek yolda glop
    (None, {"anahtar_yonler": EGIK}, {}, {}),                                                               # tırnakları eğik anahtarlar
    (lambda e: (lambda X, Y: e.duy(X + 20, Y))(*g(*DUY[0])), {}, {"tavan_armaturu": 3}, {}),                # yan yana iki duy
    (lambda e: _ikinci_u_donuk(e, 8), {}, {"priz_cift": 2}, {}),                                           # 8° dönük ikinci U: pay içinde
    (lambda e: _ikinci_u_donuk(e, 9.5), {}, {"priz_cift": 2}, {}),                                         # 9,5°: payın hemen içinde
    (lambda e: _u_acili(e, X_U, Y_U, don=30), {}, {"priz_tekli": 4}, {}),                                        # 30° dönük tekli U
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire"), {}, {"glop": 2}, {}),                                   # dairesi eğrilerle çizilmiş glop
    (lambda e: _anahtar_bicimli(e, X_A, Y_A, "daire", ters=True), {}, {"anahtar_tekli": 3}, {}),            # dairesi öbür yöne çizilmiş
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", k=0.5365), {}, {"glop": 2}, {}),                         # 0,08 pt basık: pay içinde
    (lambda e: _anahtar_bicimli(e, X_A, Y_A, "karisik"), {}, {"anahtar_tekli": 3}, {}),                     # çeyrekler karışık sırayla
    (lambda e: _glop_bicimli(e, X_U, Y_U, "daire", yaylar=((180, 90), (270, 360), (90, 0), (180, 270))), {}, {"glop": 2}, {}),  # yaylarla
], ids=["tek_yolda_iki_u", "desenli_sigorta", "baslik_cercevesi", "donuk_cift_anahtar", "aynali_cift_anahtar", "glop_tek_yol", "egik_tirnakli_anahtarlar",
        "yan_yana_duy", "cift_priz_8", "cift_priz_9_5", "donuk_tekli_u", "egrili_daire_glop", "ters_yonde_daire_anahtar", "az_basik_glop",
        "karisik_ceyrekli_anahtar", "karisik_yayli_glop"])
def test_dogru_cizim_teyitsiz(tmp_path, ek, kw, sayim, atilan):
    """Sessiz sayı denetimleri doğru çizimi bekletmez: aynı yoldaki iki tam U iki priz; iç deseni başka renkte sigorta; işaretten büyük
    yakın tonda çerçeve denetlenmez, sayılır; döndürülmüş ya da aynalanmış çift anahtar, çaprazları tek yolda glop, tırnakları yarıçapla
    açılı (lejanttaki gibi eğik) anahtarlar, yan yana iki duy; ikinci U'su `aci_payi_derece` içinde dönük çift priz; dönük tekli U;
    dairesi tek tek eğrilerle (çeyrek daireler) ya da öbür yöne çizilmiş glop ve anahtar; 0,08 pt basık (payın içinde) glop; dairesinin
    çeyrekleri karışık sırayla ve yönle çizilmiş anahtar ve glop (glopta `_egri_yol`'un `yaylar`'ıyla; bozuk yay senaryolarının denetimi)."""
    o = PO.oku(kh3_sentetik(tmp_path / "s.pdf", ek=ek, **kw), EL)
    a = o["ayrinti"]["elektrik"]
    assert o["teyit_bekliyor"] == [] and a["sayim"] == BEKLENEN | sayim
    assert a["atilan"] == {"cerceve_disinda": 0, "ayni_yerde_iki_kez": 1, "isaretten_buyuk": 0} | atilan


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
    assert (a["lejant"]["anahtar"]["tirnak"], a["lejant"]["anahtar"]["uc"], a["lejant"]["anahtar"]["aci"]) == (4.72, 2.46, 29.49)
    # çift anahtarın dizilişi: tırnakların değdiği yerler merkezden 78,25° ayrık, her tırnak yarıçapla 24,38°, uç tırnakla 75,26°
    assert (a["lejant"]["anahtar"]["isin_aci"], a["lejant"]["anahtar"]["sapma"], a["lejant"]["anahtar"]["uc_aci"]) == (78.25, 24.38, 75.26)
    assert a["lejant"]["glop"]["capraz_aci"] == [90.0]
    assert a["lejant"]["priz"]["aci"] == {"kol_kol": 0.0, "kol_taban": 90.0, "sap_taban": 90.0}
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
