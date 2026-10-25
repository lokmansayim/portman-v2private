"""İE-15 · KH-2 · PK-01'in çatı ve tavan sayfaları (hakem değişikliği; Patron onayı gerekir).

KH-1 ve K1'in testleri (`test_pafta_okuyucu.py`, `test_hakem_pk01.py`, `test_hakem_k1.py`, `test_kart_model.py`) değişmez; bu dosya
KH-2'nin eklediklerini sınar:
- **Okuyucu, sentetik pafta (her koşuda):** KH-1'in sentetik paftasına tavan omega, aşık, çatı kaplaması ve baş makas betopanı sayfaları,
  makas sayfasına dere ve iniş eklenir. Bölümler proje ayarıyla açılır (`ek_bolumler`); kapalıyken çıktı KH-1'deki gibidir. Eflatun
  ölçülü parça iki ok başı ve boy yazısıdır; ok başsız kısa ölçü boşluktur, 10 cm ve üstü teyit. Lejantlı sayfada sayı lejantın
  "N ADET" yazısıyla kıyaslanır. Montaj teyitteyken ölçeğini montajdan alan bölümler (H, makas, omega, dere) de teyide düşer; bina içinde
  sayılmayan renkli dörtgen ve yazıyla doğrulanmayan dış ölçü montajı bekletir; kırma çatıda makas teyitte; okunamayan ek bölüm
  yalnız kendini bekletir ve komutun özeti çökmez. Sessiz sayı yok (hakem 1. tur): ölçülü parçası olmayan omega ya da aşık sayfası,
  duvar çerçevesinin dışındaki omega parçası ya da dere hattı (sayılmaz), inişi olmayan dere hattı ve tek sıralı aşık yüzü teyittir.
- **PK-01 cevabı:** omega 24 parça 58,46 m (karar B: dokuz parça iç duvar ekseninde), aşık 42 parça 148,4 m (karar C: iki yüz, yedişer
  sıra), kaplama 22, betopan 4, dere 2 hat 21,2 m, iniş 6. Paftayla yeniden üretimi `test_hakem_pk01.py`'deki test sınar.
- **PK-07 gerilemesi (paftayla):** omega ve aşık 13 Ekim okumasıyla aynı (aşığın 20 cm'lik 12 ölçüsü teyitte), kaplama lejantla aynı,
  iniş 8, betopan teyitte (lejantta adet yok), yavru makas 3; KH-1 bölümleri ek bölümler açılınca değişmez.
- **Kıyas aracı:** adımsız koşu KH-1'deki gibi; `--adim K2` ile K2 satırları ve metre kapısı (±%3, `Qto_…BaseQuantities.Length`, birim
  çevrilir) kapıya girer; K1 modeli K2'den geçmez; yanlış bir K2 (bir omega eksik, aşık %5 kısa, kaplama bir fazla, boysuz parça) geçmez.
  Tutarsız adım ayarı (boş kapı, satırlarda olmayan kapı anahtarı, eksik metre satırı) koşmaz; omega anahtarı proje ayarından da
  tanınır; sayfası bulunamayan bölümün satırı "paftada yok" yazar ve kapıyı geçmez.
"""
from __future__ import annotations

import copy
import json
import os
import re
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
import test_pafta_okuyucu as T  # noqa: E402  (KH-1'in sentetik paftası; o dosya değişmez)

VERI = KOK / "testler" / "kimlik" / "veri"
PROJE = KOK / "testler" / "kimlik" / "hakem" / "projeler"
CEVAP = VERI / "PK01_pafta_katmani.json"
MOTOR_VERI = KOK / "testler" / "motor" / "veri"
MOR = tuple(PO.VARSAYILAN["olcu"]["renk"])
DERE = tuple(PO.VARSAYILAN["dere"]["renk"])
SARI, TURUNCU = (0.973, 0.843, 0.192), (0.949, 0.404, 0.133)
BASKA_MOR = (0.8, 0.0, 0.8)                                       # ölçü renginden farklı: bu renkte parça okunmaz
EK = {"ayar": {"ek_bolumler": list(PO.EK_BOLUMLER)}}


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- sentetik pafta
def _yazi(pg, X, Y, metin, renk=(0, 0, 0), boy=7):
    """Yazının ortası görünen (X, Y)'ye gelir (döndürülmemiş sayfa)."""
    w = fitz.Font(fontfile=T.FONT).text_length(metin, boy)
    pg.insert_text((X - w / 2, Y + 0.35 * boy), metin, fontsize=boy, fontname="ls", fontfile=T.FONT, color=renk)


def _ok(pg, noktalar, renk=MOR):
    pg.draw_polyline(noktalar + [noktalar[0]], color=renk, fill=renk, width=0.1, closePath=True)


def _parca(s: T.Sayfa, p, q, yazi: str | None, renk=MOR):
    """Bina cm'sinde p → q (eksene paralel) eflatun ölçülü parça: çizgi, iki dolgulu ok başı, boy yazısı (çizginin yanında)."""
    (x0, y0), (x1, y1) = s.gor(*p), s.gor(*q)
    s.pg.draw_line((x0, y0), (x1, y1), color=renk, width=0.3)
    L, w = 4, 0.8
    if abs(y0 - y1) < 1e-6:
        a, b = min(x0, x1), max(x0, x1)
        _ok(s.pg, [(a, y0), (a + L, y0 - w), (a + L, y0 + w)], renk)
        _ok(s.pg, [(b, y0), (b - L, y0 - w), (b - L, y0 + w)], renk)
        if yazi:
            _yazi(s.pg, (a + b) / 2, y0 - 6, yazi, renk)
    else:
        a, b = min(y0, y1), max(y0, y1)
        _ok(s.pg, [(x0, a), (x0 - w, a + L), (x0 + w, a + L)], renk)
        _ok(s.pg, [(x0, b), (x0 - w, b - L), (x0 + w, b - L)], renk)
        if yazi:
            _yazi(s.pg, x0 + 8, (a + b) / 2, yazi, renk)


def _uzerine(doc, baslik: str) -> T.Sayfa:
    """Var olan (döndürülmüş) sayfaya çizmek için: döndürme kaldırılır, `bitir()` geri koyar."""
    pg = next(pg for pg in doc if baslik in [" ".join(t.split()) for t in pg.get_text().splitlines()])
    s = T.Sayfa.__new__(T.Sayfa)
    s.pg, s.rot = pg, pg.rotation
    pg.set_rotation(0)
    return s


OMEGA = [((300, 10), (300, 390), "380"),                        # iç duvarın ekseninde
         ((10, 10), (10, 390), "380"),                          # sol dış duvarın iç yüzünde
         ((150, 10), (150, 206.5), "196,5"), ((150, 210), (150, 390), "180"),     # oda içinde; arada 3,5 cm boşluk
         ((450, 10), (450, 390), "380")]
ASIK = [(y, x0, x1, b) for y in (0, 60, 120, 400, 460, 520) for x0, x1, b in ((0, 410, "410"), (410, 650, "240"))]
KAPLAMA = {"renk": SARI, "olcu": (100, 350), "lejant": (60, 120), "yazi": ("350", "100"),      # örnekler pt; yan yana değen iki grup
           "ornekler": [(100 + 20 * i, 400) for i in range(3)] + [(300 + 20 * i, 400) for i in range(3)]}
BETOPAN = {"renk": TURUNCU, "olcu": (125, 250), "lejant": (60, 150), "yazi": ("125", "250"),
           "ornekler": [(100, 400), (125, 400), (300, 400), (325, 400)]}


def _lejantli(doc, baslik, L, adet: int | None, kesik: bool = False):
    s = T.Sayfa(doc, 0)
    k = 0.2                                                       # pt / cm
    w, h = L["olcu"][0] * k, L["olcu"][1] * k
    for x, y in L["ornekler"]:
        s.pg.draw_rect(fitz.Rect(x, y, x + w, y + h), color=L["renk"], width=0.5)
    if kesik:                                                     # lejant renginde, lejanttakinden kısa bir dörtgen
        s.pg.draw_rect(fitz.Rect(100, 700, 100 + w, 700 + h / 2), color=L["renk"], width=0.5)
    lx, ly = L["lejant"]
    s.pg.draw_rect(fitz.Rect(lx, ly, lx + h, ly + w), color=L["renk"], width=0.5)      # lejant dörtgeni döndürülmüş
    _yazi(s.pg, lx + h / 2, ly - 6, L["yazi"][0])
    _yazi(s.pg, lx - 10, ly + w / 2, L["yazi"][1])
    if adet is not None:
        _yazi(s.pg, lx + h + 30, ly + w / 2, f"{adet} ADET")
    _yazi(s.pg, 420, 1100, baslik, boy=14)


def kh2_sentetik(yol: Path, *, oksuz_uzun: bool = False, omega_duvarsiz: bool = False, kaplama_adet: int = 6, kaplama_kesik: bool = False,
                 betopan_adet: int | None = 4, dis_yazisiz: bool = False, bina_icinde: bool = False, kose_tasan: bool = False,
                 h_buyuk_daire: bool = False, kaplamasiz: bool = False, omega_renksiz: bool = False, omega_disarida: bool = False,
                 asik_bos: bool = False, asik_tek_sira: bool = False, dere_disarida: bool = False, inissiz_hat: bool = False) -> Path:
    gecici = yol.with_suffix(".kh1.pdf")
    T.sentetik(gecici)
    doc = fitz.open(gecici)

    o = T.Sayfa(doc, 0)                                           # tavan omega planı
    if not omega_duvarsiz:
        T._dis_cizgi(o)
    for p, q, b in OMEGA:
        _parca(o, p, q, b, BASKA_MOR if omega_renksiz else MOR)
    if omega_disarida:                                            # binanın önünde, lejant örneği gibi ok başlı 100'lük ölçü
        _parca(o, (0, -150), (100, -150), "100")
    _yazi(o.pg, *o.gor(150 + 28, 208.25), "3,5", MOR)              # ok başsız boşluk ölçüsü (bilgi)
    if oksuz_uzun:
        _yazi(o.pg, *o.gor(530, 200), "20", MOR)                  # ok başsız 20 cm: parça mı boşluk mu belli değil
    _yazi(o.pg, 420, 1100, "TAVAN OMEGA YERLEŞİM PLANI", boy=14)

    a = T.Sayfa(doc, 0)                                           # aşık planı: iki yüz, üçer sıra
    for y, x0, x1, b in ([] if asik_bos else ASIK):
        _parca(a, (x0, y), (x1, y), b)
    if asik_tek_sira:                                             # yüzlerden uzakta ok başlı tek bir 410'luk ölçü
        _parca(a, (0, -300), (410, -300), "410")
    _yazi(a.pg, 420, 1100, "AŞIK YERLEŞİM PLANI", boy=14)

    if not kaplamasiz:
        _lejantli(doc, "ÇATI KAPLAMASI YERLEŞİM PLANI", KAPLAMA, kaplama_adet, kaplama_kesik)
    _lejantli(doc, "BAŞ MAKAS BETOPAN YERLEŞİMİ", BETOPAN, betopan_adet)

    k = _uzerine(doc, "MAKAS VE DERE YERLEŞİM PLANI")                            # dere: iki saçakta kesikli çizgi, beş iniş (çift daire)
    for x in (-35, 635):
        for i in range(11):
            k.cizgi((x, -20 + 40 * i), (x, min(-20 + 40 * i + 30, 410)), DERE)
    for x, y in ((-35, -20), (-35, 410), (635, -20), (635, 410), (635, 195)):
        for r in (5, 3):
            k.daire(*k.gor(x, y), (0.0, 0.0, 0.0), r)
    if dere_disarida:                                             # binanın önünde, lejant örneği gibi 60 cm'lik dere çizgisi
        k.cizgi((700, -150), (760, -150), DERE)
    if inissiz_hat:                                               # ön saçakta 400 cm'lik bir hat daha; yanında iniş yok
        for i in range(10):
            k.cizgi((100 + 40 * i, -35), (100 + 40 * i + 30 if i < 9 else 500, -35), DERE)
    k.bitir()

    if h_buyuk_daire:                                             # H lejant renginde, H dairesinden büyük bir daire (4–40 pt dışı)
        h = _uzerine(doc, "H PROFİL MONTAJ PLANI")
        h.daire(*h.gor(450, 300), T.H_RENK["standart"], 25)
        h.bitir()
    if dis_yazisiz or bina_icinde or kose_tasan:
        m = _uzerine(doc, "MONTAJ PLANI")
        if dis_yazisiz:                                           # 600'lük dış ölçü yazısı yok
            for r in m.pg.search_for("600"):
                m.pg.add_redact_annot(r)
            m.pg.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        if bina_icinde:                                           # odanın ortasında kanat renginde kısa dörtgen
            m.dortgen([100, 300, 130, 304], T.R["KANAT"])
        if kose_tasan:                                            # köşeye çaprazdan bitişik, dışarı taşan köşe renkli kare
            m.dortgen([-10, -10, 0, 0], T.R["KOSE"])
        m.bitir()
    doc.save(yol)
    return yol


@pytest.fixture(scope="module")
def pdf(tmp_path_factory):
    return kh2_sentetik(tmp_path_factory.mktemp("kh2") / "kh2.pdf")


@pytest.fixture(scope="module")
def okuma(pdf):
    return PO.oku(pdf, EK)


def _teyit(o) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for t in o["teyit_bekliyor"]:
        out.setdefault(t["bolum"], []).append(t["neden"])
    return out


def test_ek_bolumler_kapaliyken_kh1_ayni(pdf, tmp_path):
    """Ek bölümler açılmadan okuma KH-1'in sentetik paftasındakiyle aynıdır (yalnız SHA ve sayfa sayısı farklı)."""
    kh1 = PO.oku(T.sentetik(tmp_path / "kh1.pdf"))
    o = PO.oku(pdf)
    for x in (kh1, o):
        x.pop("pafta_sha256")
        x["okuyucu"].pop("sayfa_sayisi")
    assert o == kh1                                               # dere çizgileri makas sayfasında; makası ve atılanı değiştirmez
    assert not set(PO.EK_BOLUMLER) & set(o["ayrinti"]) and "tavan_omegasi" not in o


def test_bilinmeyen_ek_bolum_okunmaz(pdf):
    with pytest.raises(ValueError, match="bilinmeyen ek bölüm"):
        PO.oku(pdf, {"ayar": {"ek_bolumler": ["tavan_omega"]}})


def test_kh2_bolumleri_teyitsiz(okuma):
    assert okuma["teyit_bekliyor"] == []
    assert {k: okuma["ayrinti"][k]["sayfa"] for k in PO.EK_BOLUMLER} == {"omega": 5, "asik": 6, "kaplama": 7, "betopan": 8, "dere": 4}


def test_omega(okuma):
    O = okuma["ayrinti"]["omega"]
    assert (O["parca"], O["toplam_m"], O["boylar"]) == (5, 15.165, {"380": 3, "196.5": 1, "180": 1})
    assert O["konum"] == {"duvar_ekseni": 1, "duvar_yuzu": 1, "duvar_ici": 0, "ara": 3}
    assert {(p["konum_cm"], p["yer"]) for p in O["parcalar"]} == {(300.0, "duvar_ekseni"), (10.0, "duvar_yuzu"), (150.0, "ara"), (450.0, "ara")}
    assert O["bosluk_olculeri"] == [3.5]
    assert okuma["tavan_omegasi"]["adet"] == 5 and "duvar ekseninde 1, duvar yüzünde 1, arada 3" in okuma["tavan_omegasi"]["not"]


def test_omega_anahtari_proje_ayarindan(pdf):
    o = PO.oku(pdf, {"ayar": {"ek_bolumler": ["omega"], "omega": {"anahtar": "duvar_omegasi_asma"}}})
    assert o["duvar_omegasi_asma"]["adet"] == 5 and "tavan_omegasi" not in o


def test_oksuz_uzun_olcu_omegayi_bekletir(tmp_path):
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", oksuz_uzun=True), EK)
    assert _teyit(o) == {"omega": ["ok başı olmayan 1 ölçü (20 cm): parça mı boşluk mu belli değil (en kısa parça 10 cm)"]}
    assert "tavan_omegasi" not in o and o["asik"]["adet"] == 12


def test_asik(okuma):
    A = okuma["ayrinti"]["asik"]
    assert (A["parca"], A["toplam_m"], A["boylar"]) == (12, 39.0, {"410": 6, "240": 6})
    assert [(y["sira"], y["sira_konumlari_cm"], y["sira_boylari_cm"]) for y in A["yuzler"]] == [(3, [0.0, 60.0, 120.0], [650.0] * 3)] * 2
    assert A["teyitli_olculer"] == [] and okuma["asik"]["adet"] == 12


def test_kaplama_ve_betopan(okuma):
    K, B = okuma["ayrinti"]["kaplama"], okuma["ayrinti"]["betopan"]
    assert (K["adet"], [(t["olcu_cm"], t["cizimde"], t["lejantta"]) for t in K["turler"]], K["gruplar"]) == (6, [([350.0, 100.0], 6, 6)], [3, 3])
    assert (B["adet"], [(t["olcu_cm"], t["cizimde"], t["lejantta"]) for t in B["turler"]], B["gruplar"]) == (4, [([250.0, 125.0], 4, 4)], [2, 2])
    # ölçü lejant dörtgeninin çizildiği yöndedir (burada örneklere göre dönmüş); sayım dönmeden bağımsız
    assert (okuma["sandvic_panel"]["adet"], okuma["bas_makas_betopan"]["adet"]) == (6, 4)


@pytest.mark.parametrize("kw, bolum, neden", [
    ({"kaplama_adet": 7}, "kaplama", "çizimde 6, lejantta 7 adet (350 × 100)"),
    ({"kaplama_kesik": True}, "kaplama", "lejant renginde, ölçüsü lejanttakinden farklı 1 dörtgen"),
    ({"betopan_adet": None}, "betopan", "lejantta adet yazısı yok; hangi dörtgenin sayılacağı belli değil"),
    ({"omega_duvarsiz": True}, "omega", "okunamadı: omega sayfasında duvar çizgisi yok; `duvar_rengi` ayarını denetleyin"),
])
def test_tutmayan_ek_bolum_yalniz_kendini_bekletir(tmp_path, kw, bolum, neden):
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", **kw), EK)
    assert _teyit(o) == {bolum: [neden]}
    anahtar = {"kaplama": "sandvic_panel", "betopan": "bas_makas_betopan", "omega": "tavan_omegasi"}[bolum]
    assert anahtar not in o and o["h_plani"]["dis"]["adet"] == 5 and o["asik"]["adet"] == 12


def test_dere_ve_inis(okuma):
    D = okuma["ayrinti"]["dere"]
    assert (D["hat"], D["toplam_m"], [h["boy_cm"] for h in D["hatlar"]]) == (2, 8.6, [430.0, 430.0])
    assert (D["inis"], sorted(i["yer"] for i in D["inisler"])) == (5, ["ara", "uc", "uc", "uc", "uc"])
    assert (okuma["dere"]["adet"], okuma["inis"]["adet"]) == (2, 5)
    assert okuma["makas_bas"]["adet"] == 2 and okuma["makas_orta"]["adet"] == 2     # dere çizgileri makası değiştirmez


def test_yavru_makas(okuma):
    assert okuma["makas_yavru"] == {"adet": 2, "not": "makas planı MK05 ve MK06; ana çatıdan ayrı kısa makas, boy 260.0 cm"}


def test_sayfasi_olmayan_ek_bolum_katmana_girmez(tmp_path):
    """Açılan bölümün sayfası yoksa katmanda satırı olmaz, teyit yazmaz; kıyasta "paftada yok" kapıyı geçmez."""
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", kaplamasiz=True), EK)
    assert o["ayrinti"]["kaplama"] is None and "sandvic_panel" not in o and o["teyit_bekliyor"] == []


@pytest.mark.parametrize("kw, neden", [
    ({"dis_yazisiz": True}, "dış ölçü yazısı bulunamadı (x ekseni); ölçek yalnız standart panodan"),
    ({"bina_icinde": True}, "bina içinde sayılmayan 1 renkli dörtgen: KANAT 30.0 × 4.0 cm"),
    # KH-1 › Bilinen sınırlama: köşeye bitişik taşan öğe dış ölçüyü iki eksende birlikte genişletir, x/y denetimi yakalamaz (%0,8)
    ({"kose_tasan": True}, "standart pano bu ölçekle 123.4 / 122.4 cm (125.5 değil); dış ölçüyü bir öğe genişletmiş olabilir"),
])
def test_montaj_teyidi_bagli_bolumlere_iner(tmp_path, kw, neden):
    """Montaj teyitteyse ölçeğini ve duvar çerçevesini montajın dış ölçüsünden alan H, makas, omega ve dere de bekler; aşık, kaplama ve
    betopan kendi ölçeğiyle okunur."""
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", **kw), EK)
    t = _teyit(o)
    assert t["montaj"] == [neden]
    bagli = "montaj teyitte; bu bölümün ölçeği ve duvar çerçevesi montajın dış ölçüsünden"
    assert {b: v for b, v in t.items() if b != "montaj"} == {b: [bagli] for b in ("h_plani", "makas", "omega", "dere")}
    assert not {"h_plani", "makas_bas", "tavan_omegasi", "dere", "inis"} & set(o)
    assert (o["asik"]["adet"], o["sandvic_panel"]["adet"], o["bas_makas_betopan"]["adet"]) == (12, 6, 4)
    if kw.get("bina_icinde"):
        assert o["ayrinti"]["montaj"]["atilan"] == {"bina_icinde": 1, "bina_disinda": 1}


def test_h_lejant_renginde_sayilmayan_egri_h_bolumunu_bekletir(tmp_path):
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", h_buyuk_daire=True), EK)
    assert _teyit(o) == {"h_plani": ["lejant renginde, daire sayılmayan 1 eğri (boyu ya da biçimi H dairesine uymuyor)"]}
    assert "h_plani" not in o and o["makas_bas"]["adet"] == 2


def test_kirma_catida_makas_bekler(pdf):
    o = PO.oku(pdf, {"ayar": {"ek_bolumler": list(PO.EK_BOLUMLER), "cati": "kirma"}})
    assert _teyit(o) == {"makas": ["çatı \"kirma\"; baş makas kuralı (ana ailenin iki ucu) yalnız kalkanlı beşikte"]}
    assert "makas_bas" not in o and o["tavan_omegasi"]["adet"] == 5


# hakem 1. tur: sessiz sayı yok (bulgu 2, 3, 4)
YOK = "ölçülü parça yok (ölçü renginde iki ok başı ve boy yazısı); sayfayı ve `olcu.renk` ayarını denetleyin"


@pytest.mark.parametrize("kw, bolum, anahtar", [({"omega_renksiz": True}, "omega", "tavan_omegasi"), ({"asik_bos": True}, "asik", "asik")])
def test_olculu_parcasi_olmayan_sayfa_bekler(tmp_path, kw, bolum, anahtar):
    """Sayfası bulunan bölümde hiç ölçülü parça okunmazsa bölüm sessizce 0 yazmaz, teyittir."""
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", **kw), EK)
    assert _teyit(o) == {bolum: [YOK]}
    assert anahtar not in o and o["ayrinti"][bolum]["parca"] == 0


@pytest.mark.parametrize("kw, bolum, neden, alan, sayi", [
    ({"omega_disarida": True}, "omega", "duvar çerçevesinin dışında 1 ölçülü parça (100 cm): sayılmadı (lejant örneği ya da başka bir "
                                        "çizim olabilir)", "parca", 5),
    ({"dere_disarida": True}, "dere", "duvar çerçevesinden 60 cm'den uzakta 1 dere hattı (60 cm): sayılmadı", "hat", 2),
])
def test_bina_cercevesi_disindaki_oge_sayilmaz_ve_bekletir(tmp_path, kw, bolum, neden, alan, sayi):
    """Omega parçası duvar çerçevesinin içinde, dere hattı saçakta (çerçeveden 60 cm içinde) durur; dışındaki öğe sayılmaz, bölüm bekler."""
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", **kw), EK)
    assert _teyit(o) == {bolum: [neden]}
    a = o["ayrinti"][bolum]
    assert (a[alan], a["atilan"]) == (sayi, {"cerceve_disinda": 1})
    assert o["ayrinti"]["omega"]["toplam_m"] == 15.165 and o["ayrinti"]["dere"]["toplam_m"] == 8.6


def test_inisi_olmayan_dere_hatti_bekletir(tmp_path):
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", inissiz_hat=True), EK)
    assert _teyit(o) == {"dere": ["inişi olmayan 1 dere hattı (400 cm)"]}
    D = o["ayrinti"]["dere"]
    assert (D["hat"], D["toplam_m"], D["inis"]) == (3, 12.6, 5) and "dere" not in o and "inis" not in o


def test_tek_sirali_asik_yuzu_bekletir(tmp_path):
    """Aşık sayfasında duvar çizgisi yok; yüzlerden uzak tek bir ölçü tek sıralı yüz olur ve aşığı bekletir."""
    o = PO.oku(kh2_sentetik(tmp_path / "s.pdf", asik_tek_sira=True), EK)
    assert _teyit(o) == {"asik": ["tek sıralı 1 çatı yüzü (1 parça): bina dışında bir ölçü ya da tek sıralı küçük bir çatı olabilir"]}
    assert "asik" not in o and sorted(y["sira"] for y in o["ayrinti"]["asik"]["yuzler"]) == [1, 3, 3]


def test_komut_ozeti_okunamayan_ve_sayfasiz_bolumde_cokmez(tmp_path, capsys):
    """Okunamayan ek bölüm (duvar çizgisi yok) ve sayfası bulunamayan bölüm belgelenen komutun özetini çökertmez."""
    pdf = kh2_sentetik(tmp_path / "s.pdf", omega_duvarsiz=True, kaplamasiz=True)
    proje = tmp_path / "p.json"
    proje.write_text(json.dumps(EK), encoding="utf-8")
    assert PO.main([str(pdf), "--proje", str(proje), "--cikti", str(tmp_path / "o.json")]) == 0
    cikti = capsys.readouterr().out.splitlines()
    assert {"omega (s. 5): okunamadı (nedeni TEYİT satırında)", "kaplama: sayfası bulunamadı (katmana girmedi)",
            "TEYİT (omega): okunamadı: omega sayfasında duvar çizgisi yok; `duvar_rengi` ayarını denetleyin"} <= set(cikti)
    assert _oku(tmp_path / "o.json")["ayrinti"]["omega"] == {"sayfa": 5}


# ----------------------------------------------------------------------------- PK-01 cevabı (karar B ve C'nin kanıtı)
@pytest.fixture(scope="module")
def cevap():
    return _oku(CEVAP)


def test_pk01_kh2_cevabi(cevap):
    a = cevap["ayrinti"]
    assert cevap["okuyucu"]["surum"] == PO.SURUM == "3" and cevap["teyit_bekliyor"] == []
    assert {k: cevap[k]["adet"] for k in ("duvar_omegasi_asma", "asik", "sandvic_panel", "bas_makas_betopan", "dere", "inis", "makas_yavru")} == \
        {"duvar_omegasi_asma": 24, "asik": 42, "sandvic_panel": 22, "bas_makas_betopan": 4, "dere": 2, "inis": 6, "makas_yavru": 0}
    assert {k: a[k]["sayfa"] for k in PO.EK_BOLUMLER} == {"omega": 6, "asik": 8, "kaplama": 9, "betopan": 5, "dere": 7}
    # omega: 24 parça; karar B (asma tavan): dokuz parça iç duvarların ekseninde, biri dış duvarın yüzünde (verandanın ilk hattı)
    assert (a["omega"]["toplam_m"], a["omega"]["konum"]) == (58.4575, {"duvar_ekseni": 9, "duvar_yuzu": 1, "duvar_ici": 0, "ara": 14})
    assert a["omega"]["boylar"] == {"365": 8, "249": 1, "248": 1, "243": 1, "240.5": 1, "200.5": 1, "190": 6, "182.25": 1, "166": 2,
                                    "50": 1, "40.5": 1}
    # aşık: karar C, iki yüz yedişer sıra; sıra aralığı 60, saçaktaki son aralık 47
    assert (a["asik"]["toplam_m"], a["asik"]["boylar"]) == (148.4, {"410": 28, "240": 14})
    assert [y["sira_konumlari_cm"] for y in a["asik"]["yuzler"]] == [[0.0, 47.2, 107.3, 167.2, 227.3, 287.2, 347.3],
                                                                     [0.0, 59.9, 119.9, 179.9, 239.9, 299.9, 347.3]]
    assert [(t["olcu_cm"], t["cizimde"], t["lejantta"]) for t in a["kaplama"]["turler"]] == [([350.0, 100.0], 22, 22)]
    assert [(t["olcu_cm"], t["cizimde"], t["lejantta"]) for t in a["betopan"]["turler"]] == [([125.0, 250.0], 4, 4)]
    assert (a["dere"]["toplam_m"], [h["boy_cm"] for h in a["dere"]["hatlar"]]) == (21.196, [1059.8, 1059.8])
    assert sorted(i["yer"] for i in a["dere"]["inisler"]) == ["ara", "ara", "uc", "uc", "uc", "uc"]


def _pafta(kod: str) -> Path | None:
    d = os.environ.get("PORTMAN_PAFTA_DIZINI")
    p = Path(d) / f"{kod}.pdf" if d else None
    return p if p and p.exists() and PO.sha256(p) == _oku(PROJE / f"{kod}.json")["pafta_sha256"] else None


@pytest.mark.skipif(_pafta("PK07") is None, reason="PK-07 paftası yok (PORTMAN_PAFTA_DIZINI/PK07.pdf, SHA'sı proje ayarındaki)")
def test_pk07_kh2_gerilemesi():
    g = _oku(VERI / "PK07_gerileme_13ekim.json")
    proje = _oku(PROJE / "PK07.json")
    kh1, o = PO.oku(_pafta("PK07"), proje), PO.oku(_pafta("PK07"), proje | EK)
    assert {k: o[k] for k in ("h_plani", "makas_bas", "makas_orta", "makas_yavru")} == {k: kh1[k] for k in ("h_plani", "makas_bas", "makas_orta", "makas_yavru")}
    assert {k: o["ayrinti"][k] for k in ("montaj", "h_plani", "makas")} == {k: kh1["ayrinti"][k] for k in ("montaj", "h_plani", "makas")}
    a = o["ayrinti"]
    # omega (ters tavan): 13 Ekim'le aynı; karar B: parçalar duvar yüzünde ve arada, eksende değil
    assert (a["omega"]["parca"], round(a["omega"]["toplam_m"], 1), a["omega"]["boylar"]) == \
        (g["tavan_omega"]["parca"], g["tavan_omega"]["toplam_m"], g["tavan_omega"]["boylar"])
    assert a["omega"]["konum"] == {"duvar_ekseni": 0, "duvar_yuzu": 8, "duvar_ici": 0, "ara": 34} and o["tavan_omegasi"]["adet"] == 42
    # aşık: ok başlı 41 parça + ok başsız 12 × 20 (teyitte) = 13 Ekim'in 53 parçası ve 146,7 m'si
    asik = dict(a["asik"]["boylar"])
    for v in a["asik"]["teyitli_olculer"]:
        asik[f"{v:g}"] = asik.get(f"{v:g}", 0) + 1
    assert (a["asik"]["parca"], a["asik"]["teyitli_olculer"]) == (41, [20.0] * 12)
    assert (asik, round(a["asik"]["toplam_m"] + sum(a["asik"]["teyitli_olculer"]) / 100, 1)) == (g["asik"]["boylar"], g["asik"]["toplam_m"])
    assert [(t["olcu_cm"], t["cizimde"], t["lejantta"]) for t in a["kaplama"]["turler"]] == \
        [([450.0, 100.0], 18, 18), ([240.0, 100.0], 3, 3), ([125.0, 100.0], 4, 4)]
    assert (o["sandvic_panel"]["adet"], o["dere"]["adet"], o["inis"]["adet"], o["makas_yavru"]["adet"]) == (25, 3, 8, 3)
    assert _teyit(o) == {"asik": ["ok başı olmayan 12 ölçü (20, 20, 20, 20, 20, 20 … cm): parça mı boşluk mu belli değil (en kısa parça 10 cm)"],
                         "betopan": ["lejantta adet yazısı yok; hangi dörtgenin sayılacağı belli değil"]}


# ----------------------------------------------------------------------------- kıyas aracı (adım ve metre kapısı)
def _ifc(yol: Path, parcalar: list[tuple], birim: str = "MILLIMETERS") -> Path:
    """(sınıf, ad, PaftaAnahtari | None, boy cm | None) parçalarıyla IFC4; boy `Qto_MemberBaseQuantities.Length`'e modelin biriminde."""
    import ifcopenshell
    import ifcopenshell.api
    f = ifcopenshell.file(schema="IFC4")
    ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="sınama")
    ifcopenshell.api.run("unit.assign_unit", f, length={"is_metric": True, "raw": birim})
    carpan = {"MILLIMETERS": 10, "METERS": 0.01}[birim]
    for sinif, ad, anahtar, boy in parcalar:
        e = ifcopenshell.api.run("root.create_entity", f, ifc_class=sinif, name=ad)
        if anahtar:
            ps = ifcopenshell.api.run("pset.add_pset", f, product=e, name="PortatifEv_Parca")
            ifcopenshell.api.run("pset.edit_pset", f, pset=ps, properties={"PaftaAnahtari": anahtar})
        if boy is not None:
            q = ifcopenshell.api.run("pset.add_qto", f, product=e, name="Qto_MemberBaseQuantities")
            ifcopenshell.api.run("pset.edit_qto", f, qto=q, properties={"Length": boy * carpan})
    f.write(str(yol))
    return yol


def _k2_parcalari(cevap: dict, asik_carpani: float = 1.0) -> list[tuple]:
    """PK-01'in bütün satırlarını kart sözleşmesiyle taşıyan doğru bir K2 modeli (KH-1 satırları ve K2 satırları)."""
    a = cevap["ayrinti"]
    t = a["h_plani"]["turler"]
    tur_satiri = {"dubelli_kulakli": "h_plani.dis", "dubelli": "h_plani.dis", "standart": "h_plani.h_standart",
                  "uclu_dubelli_kulakli": "h_plani.uclu_dis", "uclu_dubelli": "h_plani.uclu_dis", "uclu_standart": "h_plani.uclu_standart"}
    p = [("IfcWall", f"PANO_D_{i:03d}", "ayrinti.montaj.pano.adet;ayrinti.montaj.pano.dis", None) for i in range(30)]
    p += [("IfcWall", f"PANO_I_{i:03d}", "ayrinti.montaj.pano.adet;ayrinti.montaj.pano.ic", None) for i in range(20)]
    for tur, satir in tur_satiri.items():
        ek = "" if tur in ("standart", "uclu_standart") else f";ayrinti.h_plani.turler.{tur}"
        p += [("IfcMember", f"H_{tur}_{i:03d}", satir + ek, None) for i in range(t[tur])]
    p += [("IfcElementAssembly", f"MAKAS_{i:02d}", "makas_bas" if i in (1, 9) else "makas_orta", None) for i in range(1, 10)]
    konum = {"duvar_ekseni": ";ayrinti.omega.konum.duvar_ekseni", "duvar_yuzu": ";ayrinti.omega.konum.duvar_yuzu", "ara": ";ayrinti.omega.konum.ara"}
    p += [("IfcMember", f"OMEGA_{i:02d}", "duvar_omegasi_asma" + konum[o["yer"]], o["boy_cm"]) for i, o in enumerate(a["omega"]["parcalar"])]
    p += [("IfcMember", f"ASIK_{i:02d}", "asik", float(b) * asik_carpani) for i, (b, n) in enumerate(
        (b, n) for b, n in a["asik"]["boylar"].items() for _ in range(n))]
    p += [("IfcPlate", f"PANEL_{i:02d}", "sandvic_panel", None) for i in range(22)]
    p += [("IfcPlate", f"BETOPAN_{i}", "bas_makas_betopan", None) for i in range(4)]
    p += [("IfcPipeSegment", f"DERE_{i}", "dere", h["boy_cm"]) for i, h in enumerate(a["dere"]["hatlar"])]
    p += [("IfcPipeSegment", f"INIS_{i}", "inis", None) for i in range(6)]
    return p


@pytest.fixture(scope="module")
def proje():
    return _oku(PROJE / "PK01.json")


@pytest.fixture(scope="module")
def k2_ifc(tmp_path_factory, cevap):
    return _ifc(tmp_path_factory.mktemp("k2") / "k2.ifc", _k2_parcalari(cevap))


def test_bolumler():
    assert {a: KY.bolum(a) for a in ("duvar_omegasi_asma", "tavan_omegasi", "asik", "sandvic_panel", "bas_makas_betopan", "dere", "inis",
                                      "ayrinti.omega.konum.ara", "ayrinti.asik.toplam_m", "makas_yavru", "tavan_omega")} == \
        {"duvar_omegasi_asma": "omega", "tavan_omegasi": "omega", "asik": "asik", "sandvic_panel": "kaplama", "bas_makas_betopan": "betopan",
         "dere": "dere", "inis": "dere", "ayrinti.omega.konum.ara": "omega", "ayrinti.asik.toplam_m": "asik", "makas_yavru": "makas",
         "tavan_omega": None}


def test_adimsiz_kosu_kh1_gibi(k2_ifc, cevap, proje):
    k = KY.kiyasla(k2_ifc, cevap, proje)
    assert (len(k["satirlar"]), k["kapi_1"]) == (13, "geçer") and "metre" not in k and "adim" not in k
    rapor = KY.md(k).splitlines()
    assert "Kapı 1 (adet, PK-01): **geçer**." in rapor and not any(r.startswith("Metre") for r in rapor)
    assert rapor[0] == "| Anahtar | Paftadan | Modelden | Fark | Sonuç | Kapıda | Sayım yolu |"
    assert "| `makas_bas` | 2 | 2 | 0 | geçer | evet | PortatifEv_Parca.PaftaAnahtari |" in rapor


def test_k2_modeli_adet_ve_metreden_gecer(k2_ifc, cevap, proje):
    k = KY.kiyasla(k2_ifc, cevap, proje, "K2")
    s = {x["anahtar"]: x for x in k["satirlar"]}
    assert len(k["satirlar"]) == 22 and k["kapi_1"] == "geçer" and k["adim"] == "K2"
    assert {a: (s[a]["modelden"], s[a]["sonuc"], s[a]["kapida"]) for a in proje["kiyas"]["adimlar"]["K2"]["anahtarlar"]} == {
        "duvar_omegasi_asma": (24, "geçer", True), "asik": (42, "geçer", True), "sandvic_panel": (22, "geçer", True),
        "bas_makas_betopan": (4, "geçer", True), "dere": (2, "geçer", True), "inis": (6, "geçer", True),
        "ayrinti.omega.konum.duvar_ekseni": (9, "geçer", False), "ayrinti.omega.konum.duvar_yuzu": (1, "geçer", False),
        "ayrinti.omega.konum.ara": (14, "geçer", False)}
    assert [(m["anahtar"], m["paftadan_m"], m["modelden_m"], m["sonuc"]) for m in k["metre"]] == [
        ("duvar_omegasi_asma", 58.4575, 58.4575, "geçer"), ("asik", 148.4, 148.4, "geçer"), ("dere", 21.196, 21.196, "geçer")]
    rapor = KY.md(k).splitlines()
    assert "Kapı 1 (adet ve metre, PK-01, K2): **geçer**." in rapor
    assert "| `asik` | 148.4 | 148.4 | 0 | 42 | geçer |" in rapor


def test_metre_birim_cevrilir(tmp_path, cevap, proje):
    yol = _ifc(tmp_path / "m.ifc", _k2_parcalari(cevap), birim="METERS")
    k = KY.kiyasla(yol, cevap, proje, "K2")
    assert [m["modelden_m"] for m in k["metre"]] == [58.4575, 148.4, 21.196] and k["kapi_1"] == "geçer"


@pytest.mark.parametrize("carpan, sonuc", [(0.971, "geçer"), (1.03, "geçer"), (0.969, "geçmez"), (1.031, "geçmez"), (0.95, "geçmez")])
def test_metre_payi_yuzde_uc(tmp_path, cevap, proje, carpan, sonuc):
    k = KY.kiyasla(_ifc(tmp_path / "a.ifc", _k2_parcalari(cevap, asik_carpani=carpan)), cevap, proje, "K2")
    asik = next(m for m in k["metre"] if m["anahtar"] == "asik")
    assert asik["sonuc"] == sonuc and k["kapi_1"] == sonuc
    assert next(s for s in k["satirlar"] if s["anahtar"] == "asik")["sonuc"] == "geçer"          # adet yine tutar


@pytest.mark.parametrize("bozma, anahtar, adet, metre", [
    ("omega_eksik", "duvar_omegasi_asma", "geçmez", "geçmez"),
    ("kaplama_fazla", "sandvic_panel", "geçmez", None),
    ("dere_boysuz", "dere", "geçer", "modelde boy yok"),
])
def test_hakem_yanlis_k2yi_yakalar(tmp_path, cevap, proje, bozma, anahtar, adet, metre):
    p = _k2_parcalari(cevap)
    if bozma == "omega_eksik":
        p.remove(next(x for x in p if x[1].startswith("OMEGA_") and x[3] == 365))
    elif bozma == "kaplama_fazla":
        p.append(("IfcPlate", "PANEL_99", "sandvic_panel", None))
    else:
        i = next(i for i, x in enumerate(p) if x[1] == "DERE_0")
        p[i] = p[i][:3] + (None,)
    k = KY.kiyasla(_ifc(tmp_path / "y.ifc", p), cevap, proje, "K2")
    assert k["kapi_1"] == "geçmez"
    assert next(s for s in k["satirlar"] if s["anahtar"] == anahtar)["sonuc"] == adet
    if metre:
        assert next(m for m in k["metre"] if m["anahtar"] == anahtar)["sonuc"] == metre
    assert KY.kiyasla(_ifc(tmp_path / "y.ifc", p), cevap, proje)["kapi_1"] == "geçer"          # adımsız koşu KH-1 satırlarına bakar


def test_ek_bolum_teyidi_yalniz_kendi_satirlarini_durdurur(k2_ifc, cevap, proje):
    teyitli = copy.deepcopy(cevap)
    del teyitli["asik"]
    teyitli["teyit_bekliyor"] = [{"bolum": "asik", "neden": "ok başı olmayan 1 ölçü (20 cm)"}]
    k = KY.kiyasla(k2_ifc, teyitli, proje, "K2")
    s = {x["anahtar"]: x["sonuc"] for x in k["satirlar"]}
    assert s["asik"] == "teyit bekliyor" and next(m for m in k["metre"] if m["anahtar"] == "asik")["sonuc"] == "teyit bekliyor"
    assert {a for a, v in s.items() if v != "geçer"} == {"asik"} and k["kapi_1"] == "geçmez"
    assert "- asik: ok başı olmayan 1 ölçü (20 cm)" in KY.md(k).splitlines()


def test_bilinmeyen_adim(k2_ifc, cevap, proje):
    with pytest.raises(ValueError, match="adım yok: K9"):
        KY.kiyasla(k2_ifc, cevap, proje, "K9")


@pytest.mark.parametrize("bozma, hata", [
    (lambda A: A.update(kapi=[]), "adım K2: kapı listesi boş"),
    (lambda A: A["kapi"].append("cati_mahyasi"), "adım K2: kapıdaki anahtar satırlarda yok: ['cati_mahyasi']"),
    (lambda A: A["metre"].append({"anahtar": "inis"}), "adım K2: metre satırında `anahtar` ya da `cevap` yok"),
])
def test_tutarsiz_adim_ayari_kosmaz(k2_ifc, cevap, proje, bozma, hata):
    """Boş bir adım "geçer" yazmaz; satırı olmayan kapı anahtarı sessizce düşmez (hakem 1. tur, bilgi notu)."""
    p = copy.deepcopy(proje)
    bozma(p["kiyas"]["adimlar"]["K2"])
    with pytest.raises(ValueError, match=re.escape(hata)):
        KY.kiyasla(k2_ifc, cevap, p, "K2")


def test_omega_anahtari_proje_ayarindan_taninir(tmp_path, cevap, proje):
    """Okuyucu omega anahtarını proje ayarından alır, kıyas da öyle tanır: omega teyitteyken başka adla açılan omeganın metre satırı da
    bekler (eskiden teyitli okumanın metresiyle kıyaslanırdı)."""
    yeni = "tavan_omegasi_ters"
    c = copy.deepcopy(cevap)
    del c["duvar_omegasi_asma"]
    c["teyit_bekliyor"] = [{"bolum": "omega", "neden": "ok başı olmayan 1 ölçü (20 cm)"}]
    p = json.loads(json.dumps(proje).replace("duvar_omegasi_asma", yeni))
    parcalar = [(s, a, k.replace("duvar_omegasi_asma", yeni) if k else k, b) for s, a, k, b in _k2_parcalari(cevap)]
    k = KY.kiyasla(_ifc(tmp_path / "o.ifc", parcalar), c, p, "K2")
    assert next(s for s in k["satirlar"] if s["anahtar"] == yeni)["sonuc"] == "teyit bekliyor"
    assert next(m for m in k["metre"] if m["anahtar"] == yeni)["sonuc"] == "teyit bekliyor" and k["kapi_1"] == "geçmez"
    assert KY.bolum(yeni) is None and KY.bolum(yeni, yeni) == "omega"


def test_sayfasi_olmayan_bolum_kiyasta_paftada_yok(k2_ifc, cevap):
    """Okuyucu sayfası bulunamayan bölümü katmana yazmaz (`test_sayfasi_olmayan_ek_bolum_katmana_girmez`); kıyasta satırı "paftada yok"
    yazar ve kapıyı geçmez."""
    c = copy.deepcopy(cevap)
    del c["sandvic_panel"]
    c["ayrinti"]["kaplama"] = None
    k = KY.kiyasla(k2_ifc, c, _oku(PROJE / "PK01.json"), "K2")
    s = {x["anahtar"]: x["sonuc"] for x in k["satirlar"]}
    assert s["sandvic_panel"] == "paftada yok" and {a for a, v in s.items() if v != "geçer"} == {"sandvic_panel"} and k["kapi_1"] == "geçmez"


@pytest.fixture(scope="module")
def k1_modeli(tmp_path_factory):
    from motor import ifc_uret
    from motor import kart_model as KM
    d = tmp_path_factory.mktemp("k1")
    assert ifc_uret.uret(_oku(MOTOR_VERI / "PK01.json"), d / "PK01.ifc")["sema_hatasi"] == 0
    KM.kart_modeli(d / "PK01.ifc", d / "PK01_model.ifc", "besik")
    return d / "PK01_model.ifc"


def test_k1_modeli_k2den_gecmez(k1_modeli, cevap, proje):
    """Bugünkü kart modeli (K1) KH-1'in kapısından geçer, K2'nin kapısından geçmez: omega, aşık, kaplama, betopan, dere ve iniş yok."""
    assert KY.kiyasla(k1_modeli, cevap, proje)["kapi_1"] == "geçer"
    k = KY.kiyasla(k1_modeli, cevap, proje, "K2")
    s = {x["anahtar"]: x["sonuc"] for x in k["satirlar"]}
    assert {a for a, v in s.items() if v != "geçer"} == set(proje["kiyas"]["adimlar"]["K2"]["anahtarlar"])
    assert {v for a, v in s.items() if a in proje["kiyas"]["adimlar"]["K2"]["anahtarlar"]} == {"modelde yok"}
    assert {m["sonuc"] for m in k["metre"]} == {"modelde yok"} and k["kapi_1"] == "geçmez"


def test_komut_cikis_kodu(k1_modeli, k2_ifc, tmp_path):
    arg = [str(CEVAP), "--proje", str(PROJE / "PK01.json")]
    assert KY.main([str(k1_modeli), *arg]) == 0
    assert KY.main([str(k1_modeli), *arg, "--adim", "K2"]) == 1
    assert KY.main([str(k2_ifc), *arg, "--adim", "K2", "--md", str(tmp_path / "r.md")]) == 0
    assert "Kapı 1 (adet ve metre, PK-01, K2): **geçer**." in (tmp_path / "r.md").read_text(encoding="utf-8").splitlines()
