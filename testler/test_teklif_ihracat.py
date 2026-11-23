"""İE-46 · İngilizce ihracat teklif ve satış onay formu (`araclar/teklif_ihracat.py`, `kurallar/teklif/form_ihracat_en.json`).

Girdi uydurmadır (`testler/teklif_ihracat/ornek_girdi.json`; gerçek müşteri, telefon, IBAN yok). Türkçe bayi formu (M-14) bu işten
etkilenmez: o formun dosyaları burada okunmaz ve değişmez."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")

from araclar import teklif_ihracat as T  # noqa: E402

KOK = Path(__file__).resolve().parents[1]
ORNEK = KOK / "testler" / "teklif_ihracat" / "ornek_girdi.json"


def girdi() -> dict:
    return json.loads(ORNEK.read_text(encoding="utf-8"))


def metin(pdf: Path) -> tuple[int, str]:
    with pymupdf.open(pdf) as d:
        return d.page_count, " ".join(" ".join(s.get_text().split()) for s in d).replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff")   # bağlı harf


def test_tam_form_tek_sayfa_ve_bolumler(tmp_path):
    form = T.form_oku()
    D = T.hazirla(girdi(), form)
    assert D["eksik"] == []
    pdf = T.pdf_yaz(D, tmp_path / T.dosya_adi(D, form), form, "23.11.2026")
    assert pdf.name == "EXTEST01_quotation_en.pdf"
    n, s = metin(pdf)
    assert n == 1
    bolumler = [f"{n:02d} {form['bolumler'][k]}" for n, k in
                enumerate(["musteri", "urun", "kosullar", "teknik", "kapsam_disi", "banka"], 1)]
    for b in bolumler:                                       # 01–06 sırasıyla; notsuz, imzasız girdide 07 yok
        assert b in s
    assert "07 " not in s and "NOTES" not in s and "APPROVAL" not in s and "Offer validity" not in s
    sira = [s.index(b) for b in bolumler]
    assert sira == sorted(sira)
    assert "QUOTATION AND SALES CONFIRMATION FORM" in s and "DRAFT" not in s and "TBD" not in s
    assert "USD 26,500.00" in s and "108 m² (1,162.5 sq ft)" in s and "0%" in s
    assert "Grand Total USD 26,500.00" in s
    for a, v in girdi()["teknik"]:                           # 04 girdinin sırasıyla
        assert f"{a} {v}" in s
    assert s.index("Structural Frame") < s.index("Roof") < s.index("Fasteners")
    for m in form["kapsam_disi"]:                            # 05 girdide yoksa formun listesi
        assert m in s
    assert "YER-TUTUCU" in s and "TEST SELLER LTD" in s
    assert "Malzeme" not in s and "EK-1" not in s             # Ek-1 yok (Lokman 23.11 17:56:49)


def test_miktar_ve_kdv_carpar():
    G = girdi()
    G["miktar"], G["fiyat"]["kdv_orani"] = 2, 0.1
    html = T.sayfa_html(T.hazirla(G), T.form_oku(), "01.01.2027", False)
    assert "USD 53,000.00" in html and "USD 58,300.00" in html and "10%" in html


@pytest.mark.parametrize("yol,deger", [(("kosullar", "Delivery time"), "acik"), (("fiyat", "tutar"), None),
                                       (("banka", "IBAN"), ""), (("kod",), "acik (sonra)")])
def test_eksik_deger_durur_taslakta_tbd(yol, deger):
    G = girdi()
    hedef = G
    for k in yol[:-1]:
        hedef = hedef[k]
    hedef[yol[-1]] = deger
    with pytest.raises(ValueError, match="eksik değer"):
        T.hazirla(copy.deepcopy(G))
    D = T.hazirla(G, taslak=True)
    assert D["eksik"]
    html = T.sayfa_html(D, T.form_oku(), "01.01.2027", False)
    assert "TBD" in html and "· DRAFT" in html
    assert T.dosya_adi(D, T.form_oku()).endswith("_DRAFT.pdf")


def test_zorunlu_olmayan_bos_satir_bos_kalir():
    D = T.hazirla(girdi())
    assert dict(D["musteri"])["Phone"] == ""


@pytest.mark.parametrize("bozuk", [{"fazla": 1}, {"musteri": {"Email": "x"}}, {"banka": {"SWIFT": "x"}},
                                   {"fiyat": {"para_birimi": "USD", "tutar": 1, "kur": 1}}, {"teknik": []},
                                   {"fiyat": {"para_birimi": "USD", "tutar": "26.500"}}, {"alan_m2": 0}])
def test_bilinmeyen_ya_da_bozuk_alan_durur(bozuk):
    G = {**girdi(), **bozuk}
    with pytest.raises(ValueError):
        T.hazirla(G, taslak=True)


def test_not_alanlari_okunmaz():
    G = {**girdi(), "sema": "x", "alan_kaynagi": "plan", "sorulacak": ["a"], "teknik_acik": "b", "dil": "en"}
    assert T.hazirla(G)["eksik"] == []


def test_girdiler_birlesir_ve_logo_kirpilir(tmp_path):
    from PIL import Image
    Image.new("RGB", (200, 200), "white").save(tmp_path / "logo.png")
    with Image.open(tmp_path / "logo.png") as im:
        im.paste((20, 40, 90), (50, 90, 150, 110))
        im.save(tmp_path / "logo.png")
    G = girdi()
    banka = {"banka": G.pop("banka"), "logo": "logo.png"}
    (tmp_path / "a.json").write_text(json.dumps(G), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(banka), encoding="utf-8")
    B, _ = T.girdi_birlestir([tmp_path / "a.json", tmp_path / "b.json"])
    assert B["banka"]["IBAN"] == "YER-TUTUCU" and Path(B["logo"]).is_file()
    import io
    with Image.open(io.BytesIO(T.logo_kirp(Path(B["logo"])))) as k:
        assert k.size == (108, 28)                           # 100 × 20 + 4 piksel pay
    D = T.hazirla(B)
    pdf = T.pdf_yaz(D, tmp_path / "f.pdf", tarih="23.11.2026")
    with pymupdf.open(pdf) as d:
        assert len(d[0].get_images()) == 1
        assert "PORTATİF EV" not in d[0].get_text()           # logo varken firma adı yazı olarak yok


def test_komut(tmp_path):
    assert T.main([str(ORNEK), str(tmp_path), "--tarih", "23.11.2026"]) == 0
    assert (tmp_path / "EXTEST01_quotation_en.pdf").is_file()
    G = {**girdi(), "kod": "acik"}
    (tmp_path / "g.json").write_text(json.dumps(G), encoding="utf-8")
    assert T.main([str(tmp_path / "g.json"), str(tmp_path)]) == 1


def test_belirlenimci(tmp_path):
    D = T.hazirla(girdi())
    a = T.pdf_yaz(D, tmp_path / "a.pdf", tarih="23.11.2026").read_bytes()
    b = T.pdf_yaz(D, tmp_path / "b.pdf", tarih="23.11.2026").read_bytes()
    assert a == b


def test_telefon_maskeli():
    G = girdi()
    G["musteri"]["Phone"] = "+1 315 555 0123"                # uydurma numara
    D = T.hazirla(G)
    assert dict(D["musteri"])["Phone"] == "…0123"
    assert "555" not in T.sayfa_html(D, T.form_oku(), "01.01.2027", False)


def test_notlar_07_numarali(tmp_path):
    G = {**girdi(), "notlar": [["Quality.", "Licensed products."], ["Scope.", "Second order complete."]]}
    D = T.hazirla(G)
    n, s = metin(T.pdf_yaz(D, tmp_path / "n.pdf", tarih="23.11.2026"))
    assert n == 1 and "07 NOTES" in s
    assert s.index("06 BANK DETAILS") < s.index("07 NOTES") < s.index("1. Quality. Licensed products.") < s.index("2. Scope.")
    for bozuk in ([["Başlık"]], [["Başlık", ""]], "metin"):
        with pytest.raises(ValueError, match="notlar"):
            T.hazirla({**girdi(), "notlar": bozuk})


def test_imza_gecerlilik_ve_numara_sirasi(tmp_path):
    G = {**girdi(), "imza": True}
    G["kosullar"]["Offer validity"] = "30 days from the date of this form."
    n, s = metin(T.pdf_yaz(T.hazirla(G), tmp_path / "i.pdf", tarih="23.11.2026"))
    assert n == 1
    assert "Offer validity 30 days from the date of this form." in s
    assert "07 APPROVAL SELLER BUYER Name: Name: Signature and stamp: Signature and stamp: Date: Date:" in s   # notsuz: imza 07
    with pytest.raises(ValueError, match="imza"):
        T.hazirla({**girdi(), "imza": "evet"})


def test_sigmayan_form_bolum_sinirinda_ikinci_sayfa(tmp_path):
    G = {**girdi(), "imza": True, "notlar": [[f"Note {i}.", "Long text " * 40] for i in range(6)]}
    G["teknik"] = [[f"Row {i}", "Value " * 30] for i in range(14)]
    D = T.hazirla(G)
    n, s = metin(T.pdf_yaz(D, tmp_path / "u.pdf", tarih="23.11.2026"))
    assert n == 2 and "page 1 / 2" in s and "page 2 / 2" in s
    with pymupdf.open(tmp_path / "u.pdf") as d:
        ikinci = " ".join(d[1].get_text().split())
    assert ikinci.startswith(tuple(f"{k:02d} " for k in range(2, 9)))  # ikinci sayfa bir bölüm başlığıyla başlar
    assert "QUOTATION AND SALES CONFIRMATION FORM" not in ikinci
    assert "08 APPROVAL" in ikinci
