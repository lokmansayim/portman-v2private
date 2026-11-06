"""İE-13 PR-6 · Teklif PDF'i (`araclar/teklif_pdf.py`, `araclar/teklif.py` yazar): Patron'un teklif formunun düzeni, fiyatı olmayan satır boş.

TK-01 (İş Emri r05): her tavan seçeneğine bir PDF; ilk sayfada formun beş bölümü ve teklifin JSON'undaki toplam; Ek-1'de Motor'un listesi
satır satır, birim fiyat ve tutar JSON'dakiyle aynı, fiyatı olmayan satırda ikisi de boş; tavan satırı seçeneğe göre; alıcıya ait kalem
teknik özelliklerden kapsam dışına geçer; bayi adı ve telefon yazılmaz; aynı girdi aynı PDF. PDF'in kendisi henüz hedef örnek değildir
(D-28 madde 2: Patron'un onayı bekleniyor); bu test toplamları ve satırları teklifin JSON'una karşı sınar.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf
import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from araclar import teklif as TK  # noqa: E402
from araclar import teklif_pdf as TP  # noqa: E402

IE = KOK / "testler" / "teklif" / "TK01_is_emri_r05.json"
ESKI_DEFTER = ["--defter", str(KOK / "kurallar" / "fiyat" / "defter_2026-10.json")]   # toplamlar r10 defteriyle (D-62)
BOLUMLER = ["01 BAYİ / FİRMA BİLGİLERİ", "02 ÜRÜN DETAYI", "03 ÖDEME", "04 PAKET İÇERİĞİ VE TEKNİK ÖZELLİKLERİ",
            "05 KAPSAM DIŞI İŞLER (BAYİ/SAHA SORUMLULUKLARI)"]
BAYRAK = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES       # "fi" bitişik harf olarak değil, iki harf
TELEFON = re.compile(r"(?:\+?90[\s-]?)?0?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")


def _oku(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cikti(tmp_path_factory):
    d = tmp_path_factory.mktemp("teklif_pdf")
    assert TK.main([str(IE), str(d), "--tavan", "asma,ters", "--tarih", "03.11.2026", *ESKI_DEFTER]) == 0
    return d


@pytest.fixture(scope="module")
def T(cikti):
    return _oku(cikti / "TK01_teklif.json")


def _metin(yol):
    """Sayfaların metni, boşluklar tek boşluğa indirilmiş."""
    with pymupdf.open(yol) as d:
        return [" ".join(s.get_text(flags=BAYRAK).split()) for s in d]


def _ek_satirlari(yol):
    """Ek-1 sayfalarındaki kalem satırları: (kalem, ölçü, birim, adet, birim fiyat, tutar); başlık, grup ve toplam satırları atlanır."""
    satir = []
    with pymupdf.open(yol) as d:
        for s in list(d)[1:]:
            for t in s.find_tables().tables:
                for r in t.extract():
                    if len(r) != 6 or r[0] in (None, "", "Kalem") or r[2] in (None, ""):
                        continue
                    satir.append(tuple(" ".join((x or "").split()) for x in r))
    return satir


def test_her_secenege_bir_pdf(cikti, T):
    adlar = sorted(p.name for p in cikti.glob("*.pdf"))
    assert adlar == ["TK01_teklif_asma.pdf", "TK01_teklif_ters.pdf"]
    assert [TP.dosya_adi(T, s) for s in T["secenekler"]] == ["TK01_teklif_asma.pdf", "TK01_teklif_ters.pdf"]
    tek = dict(T, secenekler=T["secenekler"][:1])
    assert TP.dosya_adi(tek, tek["secenekler"][0]) == "TK01_teklif.pdf"


def test_ilk_sayfa_formun_duzeni(cikti, T):
    """Başlık, tarih, beş bölüm; 02'de seçeneğin toplamı (Tutar, Toplam, Gen. Toplam) JSON'un toplamı; alan Motor'un brüt alanı; 03'te
    koşullar boşsa boş ve uyarıda; fiyatsız satır varken TASLAK."""
    for sec in T["secenekler"]:
        s1 = _metin(cikti / TP.dosya_adi(T, sec))[0]
        for x in ["PORTATİF EV", "Tarih: 03.11.2026", "TEKLİF VE SATIŞ ONAY FORMU · TASLAK", *BOLUMLER, "Gen. Toplam",
                  f"PREFABRİK YAPI · {sec['ad']}", "Teslim süresi", "Ödeme şekli"]:
            assert x in s1, (sec["ad"], x)
        toplam = TP.tl(sec["fiyat"]["ozet"]["toplam"])
        assert s1.count(toplam) == 4, (sec["ad"], toplam)                     # birim fiyat, tutar, toplam, genel toplam
        assert f"{TP.sayi(sec['liste']['girdi_ozeti']['brut_m2'])} m²" in s1
        assert "1 satır fiyatsız, toplam eksik; Teslim süresi, Ödeme şekli boş (Patron'dan)" in s1      # r09: 120 × 180 karkas fiyatlı
        assert "sayfa 1 / " in s1


def test_ek_satirlari_json_ile_ayni_fiyatsiz_bos(cikti, T):
    """Ek-1'in her kalem satırı Motor'un listesindeki sırayla; birim fiyat ve tutar JSON'dakinin yazısı; fiyatı olmayan satırda ikisi de
    boş (fiyat uydurulmaz). Sonda genel toplam ve fiyatı olmayan satır sayısı."""
    for sec in T["secenekler"]:
        yol = cikti / TP.dosya_adi(T, sec)
        pdf = _ek_satirlari(yol)
        js = sec["fiyat"]["satirlar"]
        assert len(pdf) == len(js) == sec["fiyat"]["ozet"]["satir"]
        for p, s in zip(pdf, js):
            assert p[0] == " ".join(s["kalem"].split()), (p, s["kalem"])
            assert p[3] == ("" if s.get("adet") is None else str(s["adet"])), (p, s)
            assert (p[4], p[5]) == (TP.tl(s["birim_fiyat"]), TP.tl(s["tutar"])), (p, s)
        bos = [p[0] for p in pdf if p[4] == "" and p[5] == ""]
        assert len(bos) == len(sec["fiyat"]["ozet"]["fiyatsiz"]) == 1                  # r09 (Lokman 4 Kasım 23:20): 120 × 180 karkas 700 TL
        assert bos[0].startswith("Çırpı ipi")
        son = _metin(yol)[-1]
        assert TP.tl(sec["fiyat"]["ozet"]["toplam"]) in son and "Fiyatı olmayan satır: 1" in son


def test_tavan_satiri_secenege_gore(cikti, T):
    asma, ters = (_metin(cikti / TP.dosya_adi(T, s))[0] for s in T["secenekler"])
    assert "Alçıpan Dizme (Asma)" in asma and "Ters Tavan" not in asma
    assert "Ters Tavan" in ters and "Alçıpan Dizme (Asma)" not in ters


def test_teknik_ozellikler_is_emrinden():
    """Kat yüksekliği ve panel kalınlıkları İş Emri'nin yapısından; İş Emri'nin özelliği aynı adlı form satırının yerine geçer, formda
    olmayan özellik ilk sözcüğünü taşıyan son satırın arkasına girer; alıcıya ait kalem teknik özelliklerden çıkar, kapsam dışına girer."""
    form, ie = TP.form_oku(), _oku(IE)
    teknik, kapsam = TP.teknik_ve_kapsam(form, ie, {"Tavan": "Ters"})
    d = dict(teknik)
    assert (d["Kat Yüksekliği"], d["Dış Cephe Panelleri"][:15], d["İç Cephe Panelleri"][:14]) == ("2500 mm", "Kalınlık 100 mm", "Kalınlık 60 mm")
    assert (d["Çatı Şekli"], d["Çatı Kaplaması"], d["Çatı Kaplama Rengi"], d["Tavan"]) == ("Beşik", "Tek Kat Panel", "Antrasit", "Ters Tavan")
    adlar = [a for a, _ in teknik]
    assert adlar.index("Çatı Kaplaması") == adlar.index("Çatı Tavan Arası İzolasyonu") + 1
    assert kapsam == form["kapsam_disi"]
    al = dict(ie, alici_ait={"kalemler": ["vitrifiye", "klima"]})
    teknik2, kapsam2 = TP.teknik_ve_kapsam(form, al)
    assert "Vitrifiye ve Armatür Grubu" not in dict(teknik2)
    assert kapsam2[-2:] == ["Vitrifiye ve Armatür Grubu (alıcıya ait)", "Klima (alıcıya ait)"]
    kalin = dict(ie, yapi=dict(ie["yapi"], duvar_yuksekligi_cm=260, duvar_kalinligi_cm={"dis": 10, "ic": 10}))
    d3 = dict(TP.teknik_ve_kapsam(form, kalin)[0])
    assert (d3["Kat Yüksekliği"], d3["İç Cephe Panelleri"][:15]) == ("2600 mm", "Kalınlık 100 mm")


def test_bayi_adi_ve_telefon_yazilmaz(cikti, T):
    """Bayinin yalnız kodu yazılır, adı yazılmaz; müşteri adı yazılır (D-33); telefon hiçbir sayfada yok."""
    ie = _oku(IE)
    for sec in T["secenekler"]:
        metin = "\n".join(_metin(cikti / TP.dosya_adi(T, sec)))
        assert ie["talep"]["bayi"]["ad"] not in metin and ie["talep"]["bayi"]["kod"] in metin
        assert ie["talep"]["musteri_adi"] in metin
        assert not TELEFON.search(metin)


def test_kosullar_dolu_ve_fiyatsiz_yoksa_taslak_yok(T):
    """Koşullar dolu ve fiyatsız satır yoksa başlıkta TASLAK ve uyarı yok; koşulların değeri 03'te."""
    sec = json.loads(json.dumps(T["secenekler"][0]))
    sec["fiyat"]["ozet"]["fiyatsiz"] = []
    T2 = dict(T, kosullar={"Teslim süresi": "30 gün", "Ödeme şekli": "Peşin"}, secenekler=[sec])
    h = TP.ilk_sayfa(T2, _oku(IE), sec, TP.form_oku(), "03.11.2026")
    assert "TASLAK" not in h and "class='uyari'" not in h
    assert ">30 gün<" in h and ">Peşin<" in h
    T3 = dict(T2, oneri_dahil=True)
    assert "Onaysız öneriler dahil" in TP.ilk_sayfa(T3, _oku(IE), sec, TP.form_oku(), "03.11.2026")


def test_ayni_girdi_ayni_pdf(cikti, T, tmp_path):
    assert TK.main([str(IE), str(tmp_path), "--tavan", "asma,ters", "--tarih", "03.11.2026", *ESKI_DEFTER]) == 0
    for sec in T["secenekler"]:
        ad = TP.dosya_adi(T, sec)
        assert (tmp_path / ad).read_bytes() == (cikti / ad).read_bytes(), ad


def test_teklifte_yazilan_ad_ve_olcu(T):
    """r09 (Lokman 4 Kasım 23:24, TK-04 teklif PDF'i: "'METAL TAHTA L:2800 (GALVANİZ)' Yaz fiyat:100 TL"): defter kaydı `teklif_adi` ve
    `teklif_olcu` taşıyorsa Ek-1'de satır o adla ve ölçüyle yazılır; iç ad (`kalem`) ve ölçü tabloya girmez."""
    sec = json.loads(json.dumps(T["secenekler"][0]))
    s = sec["fiyat"]["satirlar"][0]
    s.update({"kalem": "Ters mahya kenar kutusu", "olcu": "L 21 × 40 × 21 × 2800", "teklif_adi": "Metal tahta (galvaniz)", "teklif_olcu": "L 2800"})
    _b, _bas, satir, _son = TP.ek_satirlari(T, sec)
    h = "".join(x[2] for x in satir if x[0] == "kalem")
    assert ">Metal tahta (galvaniz)<" in h and ">L 2800<" in h
    assert "Ters mahya kenar kutusu" not in h and "21 × 40 × 21" not in h
