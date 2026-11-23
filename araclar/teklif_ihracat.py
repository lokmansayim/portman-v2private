"""İE-46 · İngilizce ihracat teklif ve satış onay formu (PDF). D-28: bu form yalnız bu komutla üretilir.

    python3 araclar/teklif_ihracat.py <girdi.json> [<girdi2.json> …] <çıktı klasörü> [--tarih GG.AA.YYYY] [--taslak]

Düzen standart çelik teklif formunun 01–05 düzenidir (Drive "ÇELİK - TEKLİF PORTATİFEV - YENİ.xlsx"), Türkçe prefabrik bayi formuyla
(`araclar/teklif_pdf.py`, M-14) aynı görünüşte; metinler İngilizce, sabitleri `kurallar/teklif/form_ihracat_en.json`'da. Malzeme listesi
(Ek-1) ve kat planı yoktur (Lokman, 23 Kasım 2026 17:56:49). 06 banka bilgisidir. Notlar ve imza bölümü isteğe bağlıdır; bölüm numaraları sırayla verilir. Tek sayfaya en çok %85 küçülerek sığmazsa bölüm sınırında ikinci sayfaya geçer.

Bütün proje değerleri girdiden gelir: müşteri, ürün, alan, fiyat ve para birimi, koşullar, 04'ün satırları, 05 (yoksa formun listesi),
satıcı, banka, logo. Girdi proje klasöründe durur, depoya girmez: IBAN ve telefon depoya yazılmaz. Birden çok girdi dosyası sırayla
birleşir (ör. içerik + banka); sonraki dosya üst düzey alanı ezer, sözlük alanları anahtar anahtar birleşir.

Değeri "acik" (ya da "acik …") olan ve boş zorunlu alan durur (ValueError): form uydurmaz. `--taslak` verilirse eksik değerler kırmızı
"TBD" yazılır, başlığa " · DRAFT" eklenir; bu çıktı müşteriye gitmez, yalnız önizlemedir.

Girdi alanları:
  kod            teklif kimliği (sağ üstte ve dosya adında)
  musteri        {"Customer", "Project", "Phone", "Address"} (form.json › musteri_satirlari)
  urun           02'deki ürün tanımı
  alan_m2        brüt alan, m² (02'de m² ve sq ft)
  miktar         adet (yoksa 1)
  fiyat          {"para_birimi": "USD", "tutar": birim fiyat, "kdv_orani": 0}
  kosullar       {"Delivery terms", "Delivery time", "Payment method"}; "Offer validity" isteğe bağlı (yoksa satır yok)
  teknik         [[satır adı, değer], …] (04, sırasıyla)
  kapsam_disi    [madde, …] (05; yoksa formun listesi)
  satici         satıcının unvanı (06'nın başında)
  banka          {"Bank", "Account holder", "Currency", "IBAN"}
  notlar         [[başlık, metin], …] isteğe bağlı; NOTES numaralı maddeler, başlık kalın; boşsa bölüm yok
  imza           true ise sonda APPROVAL: satıcı ve alıcı için ad, imza ve kaşe, tarih kutuları (isteğe bağlı)
  logo           logo dosyası (PNG/JPG); göreli yol girdi dosyasının klasörüne göre; yoksa firma adı yazı olarak
Not alanları (okunmaz): sema, aciklama, dil, *_kaynagi, teknik_acik, sorulacak.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from araclar.teklif_pdf import A4, CSS, KENAR, e  # noqa: E402  (aynı görünüş; teklif_pdf.py değişmez)

FORM = KOK / "kurallar" / "teklif" / "form_ihracat_en.json"
ALANLAR = {"kod", "musteri", "urun", "alan_m2", "miktar", "fiyat", "kosullar", "teknik", "kapsam_disi", "satici", "banka", "logo",
           "notlar", "imza"}
NOT_ALANLARI = {"sema", "aciklama", "dil", "teknik_acik", "sorulacak"}
FIYAT_ALANLARI = {"para_birimi", "tutar", "kdv_orani"}
SQFT = 10.763910416709722                      # 1 m² = 10,7639 sq ft (1 ft = 0,3048 m)
CSS_EK = """
.eksik { color: #b0161b; font-weight: bold; }
"""


def form_oku(yol: Path | str = FORM) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def acik_mi(v) -> bool:
    """Değer eksik mi: None, boş yazı, "acik" ya da "acik …" (içerik dosyasının bekleyen değeri)."""
    if v is None:
        return True
    if isinstance(v, str):
        s = v.strip().lower()
        return not s or s == "acik" or s.startswith(("acik ", "acik("))
    return False


def para(x: float, birim: str) -> str:
    """İngilizce tutar: 45000 → "USD 45,000.00"."""
    return f"{birim} {float(x):,.2f}"


def sayi_en(x: float, basamak: int = 2) -> str:
    s = f"{float(x):,.{basamak}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def girdi_birlestir(yollar: list[Path]) -> tuple[dict, Path]:
    """Girdi dosyalarını sırayla birleştirir; (girdi, ilk dosyanın klasörü). Logo yolu kendi dosyasının klasörüne göre çözülür."""
    G: dict = {}
    for yol in yollar:
        d = json.loads(Path(yol).read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError(f"ihracat formu: {yol} bir JSON nesnesi değil")
        if d.get("logo") and not acik_mi(d["logo"]):
            d["logo"] = str((Path(yol).parent / d["logo"]).resolve())
        for k, v in d.items():
            G[k] = {**G[k], **v} if isinstance(v, dict) and isinstance(G.get(k), dict) else v
    return G, Path(yollar[0]).parent


def hazirla(G: dict, form: dict | None = None, taslak: bool = False) -> dict:
    """Girdiyi denetler, formun değerlerini döndürür. Bilinmeyen alan ya da satır her zaman durur; eksik değer `taslak` değilse durur
    (hepsi tek iletide), taslakta "TBD" olur ve `eksik` listesine girer."""
    form = form or form_oku()
    bilinmeyen = sorted(k for k in G if k not in ALANLAR | NOT_ALANLARI and not k.endswith("_kaynagi"))
    musteri, kosul, banka, fiyat = (dict(G.get(k) or {}) for k in ("musteri", "kosullar", "banka", "fiyat"))
    bilinmeyen += [f"musteri.{k}" for k in musteri if k not in form["musteri_satirlari"]]
    bilinmeyen += [f"kosullar.{k}" for k in kosul if k not in form["kosul_satirlari"] + form["istege_bagli_kosullar"]]
    bilinmeyen += [f"banka.{k}" for k in banka if k not in form["banka_satirlari"]]
    bilinmeyen += [f"fiyat.{k}" for k in fiyat if k not in FIYAT_ALANLARI]
    if bilinmeyen:
        raise ValueError(f"ihracat formu: bilinmeyen alan {bilinmeyen}")
    eksik: list[str] = []

    def al(ad: str, v, zorunlu: bool = True):
        if acik_mi(v):
            if zorunlu:
                eksik.append(ad)
                return None
            return ""
        return v

    teknik = G.get("teknik")
    if not isinstance(teknik, list) or not teknik or any(not isinstance(r, list) or len(r) != 2 for r in teknik):
        raise ValueError("ihracat formu: teknik [[satır adı, değer], …] olmalı, boş olamaz")
    tutar = al("fiyat.tutar", fiyat.get("tutar"))
    if tutar is not None and not isinstance(tutar, (int, float)):
        raise ValueError(f"ihracat formu: fiyat.tutar sayı olmalı ({tutar!r})")
    kdv = fiyat.get("kdv_orani", 0)
    if not isinstance(kdv, (int, float)) or not 0 <= kdv < 1:
        raise ValueError(f"ihracat formu: fiyat.kdv_orani 0 ile 1 arasında sayı olmalı ({kdv!r})")
    alan = al("alan_m2", G.get("alan_m2"))
    if alan is not None and (not isinstance(alan, (int, float)) or alan <= 0):
        raise ValueError(f"ihracat formu: alan_m2 pozitif sayı olmalı ({alan!r})")
    miktar = G.get("miktar", 1)
    if not isinstance(miktar, int) or miktar < 1:
        raise ValueError(f"ihracat formu: miktar pozitif tam sayı olmalı ({miktar!r})")
    notlar = G.get("notlar") or []
    if not isinstance(notlar, list) or any(not isinstance(n, list) or len(n) != 2 or any(acik_mi(x) for x in n) for n in notlar):
        raise ValueError("ihracat formu: notlar [[başlık, metin], …] olmalı, boş başlık ya da metin olamaz")
    imza = G.get("imza", False)
    if not isinstance(imza, bool):
        raise ValueError(f"ihracat formu: imza true ya da false olmalı ({imza!r})")
    logo = None if acik_mi(G.get("logo")) else Path(G["logo"])
    if logo is not None and not logo.is_file():
        raise ValueError(f"ihracat formu: logo dosyası yok ({logo.name})")
    if form.get("telefon") == "maskeli":                    # D-151: ihracat formunda "acik" (Lokman 23.11.2026 19:29:29)
        from beyin import numara
        musteri = {k: numara.maskele(str(v), son_dort=True) if isinstance(v, str) else v for k, v in musteri.items()}
    D = {
        "kod": al("kod", G.get("kod")),
        "musteri": [(k, al(f"musteri.{k}", musteri.get(k), k in form["zorunlu_musteri"])) for k in form["musteri_satirlari"]],
        "urun": al("urun", G.get("urun")),
        "alan_m2": alan, "miktar": miktar,
        "para_birimi": al("fiyat.para_birimi", fiyat.get("para_birimi")), "tutar": tutar, "kdv_orani": kdv,
        "kosullar": [(k, al(f"kosullar.{k}", kosul.get(k))) for k in form["kosul_satirlari"]]
                    + [(k, str(kosul[k])) for k in form["istege_bagli_kosullar"] if not acik_mi(kosul.get(k))],
        "teknik": [(str(a), al(f"teknik.{a}", v)) for a, v in teknik],
        "kapsam_disi": list(G.get("kapsam_disi") or form["kapsam_disi"]),
        "satici": al("satici", G.get("satici")),
        "banka": [(k, al(f"banka.{k}", banka.get(k))) for k in form["banka_satirlari"]],
        "notlar": [(str(b), str(m)) for b, m in notlar], "imza": imza,
        "logo": logo,
    }
    if eksik and not taslak:
        raise ValueError(f"ihracat formu: eksik değer {eksik}; değer girdiden verilir, uydurulmaz (önizleme için --taslak)")
    D["eksik"] = eksik
    return D


def _deger(v, form: dict) -> str:
    return f"<span class='eksik'>{e(form['eksik_yazisi'])}</span>" if v is None else e(v)


def _satir(ad: str, v, form: dict) -> str:
    return f"<tr><td style='width:130px' class='kalin'>{e(ad)}</td><td style='width:370px'>{_deger(v, form)}</td></tr>"


def _urun_tablosu(D: dict, form: dict) -> str:
    T = form["urun_tablosu"]
    pb = D["para_birimi"]
    hesap = D["tutar"] is not None and pb is not None
    birim = para(D["tutar"], pb) if hesap else None
    tutar = round(D["tutar"] * D["miktar"], 2) if hesap else None
    kdv = round(tutar * D["kdv_orani"], 2) if hesap else None
    toplam = round(tutar + kdv, 2) if hesap else None
    if D["alan_m2"] is None:
        alan = None
    else:
        alan = f"{sayi_en(D['alan_m2'])} m²" + (f" ({sayi_en(D['alan_m2'] * SQFT, 1)} sq ft)" if form.get("alan_sqft") else "")
    sinif = ["", "", "sag", "orta", "sag", "sag", "orta", "sag"]
    bas = "".join(f"<th class='{c}'>{e(b)}</th>" for b, c in zip(T["basliklar"], sinif))
    f = lambda v: _deger(v, form)        # noqa: E731
    return (f"<table><tr>{bas}</tr><tr><td>1</td><td>{f(D['urun'])}</td><td class='sag nw'>{f(alan)}</td>"
            f"<td class='orta'>{D['miktar']}</td><td class='sag nw'>{f(birim)}</td>"
            f"<td class='sag nw'>{f(para(tutar, pb) if hesap else None)}</td><td class='orta'>{e(sayi_en(D['kdv_orani'] * 100))}%</td>"
            f"<td class='sag nw'>{f(para(toplam, pb) if hesap else None)}</td></tr>"
            f"<tr class='ara'><td colspan='7' class='sag'>{e(T['genel_toplam'])}</td>"
            f"<td class='sag nw'>{f(para(toplam, pb) if hesap else None)}</td></tr></table>")


def bas_html(D: dict, form: dict, tarih: str, logo_var: bool) -> str:
    ek = form["taslak_eki"] if D["eksik"] else ""
    marka = "" if logo_var else f"<td class='marka'>{e(form['firma'])}</td>"
    return (f"<table class='ust'><tr>{marka}<td class='sag soluk'>{e(form['web'])}</td></tr></table>"
            f"<table class='bas'><tr><td class='nw'>{e(form['tarih_etiketi'])}: <b>{e(tarih)}</b></td>"
            f"<td class='baslik'>{e(form['baslik'])}{e(ek)}</td><td class='sag nw'>{_deger(D['kod'], form)}</td></tr></table>")


def _imza(form: dict) -> str:
    I = form["imza"]
    bas = "".join(f"<th style='width:250px'>{e(t)}</th>" for t in I["taraflar"])
    sat = "".join(f"<tr><td style='width:250px; height:{I['satir_yuksekligi_nk']}px'>{e(a)}:</td>"
                  f"<td style='width:250px; height:{I['satir_yuksekligi_nk']}px'>{e(a)}:</td></tr>" for a in I["satirlar"])
    return f"<table><tr>{bas}</tr>{sat}</table>"


def bolumler(D: dict, form: dict) -> list[str]:
    """Bölümlerin HTML'i sırayla; numara sırayla verilir (01, 02, …): notlar ve imza yalnız girdide varsa."""
    B = form["bolumler"]
    parca = [("musteri", "<table>" + "".join(_satir(a, v, form) for a, v in D["musteri"]) + "</table>"),
             ("urun", _urun_tablosu(D, form) + f"<p class='soluk'>{e(form['fiyat_aciklamasi'])}</p>"),
             ("kosullar", "<table>" + "".join(_satir(a, v, form) for a, v in D["kosullar"]) + "</table>"),
             ("teknik", "<table>" + "".join(_satir(a, v, form) for a, v in D["teknik"]) + "</table>"),
             ("kapsam_disi", "<table>" + "".join(f"<tr><td>• {e(m)}</td></tr>" for m in D["kapsam_disi"]) + "</table>"),
             ("banka", "<table>" + _satir(form["satici_etiketi"], D["satici"], form)
              + "".join(_satir(a, v, form) for a, v in D["banka"]) + "</table>")]
    if D["notlar"]:
        parca.append(("notlar", "<table>" + "".join(f"<tr><td>{i}. <b>{e(b)}</b> {e(m)}</td></tr>"
                                                     for i, (b, m) in enumerate(D["notlar"], 1)) + "</table>"))
    if D.get("imza"):
        parca.append(("imza", _imza(form)))
    return [f"<h2>{n:02d} &nbsp; {e(B[k])}</h2>{h}" for n, (k, h) in enumerate(parca, 1)]


def sayfa_html(D: dict, form: dict, tarih: str, logo_var: bool) -> str:
    """Formun bütün metni tek parça (başlık + bölümler)."""
    return bas_html(D, form, tarih, logo_var) + "".join(bolumler(D, form))


def dosya_adi(D: dict, form: dict) -> str:
    kod = str(D["kod"] or "DRAFT").replace("-", "").replace(" ", "_")
    ad = form["dosya"].format(kod=kod)
    return ad.replace(".pdf", "_DRAFT.pdf") if D["eksik"] else ad


def logo_kirp(yol: Path, esik: int = 245, pay: int = 4) -> bytes:
    """Logonun beyaz kenarlarını kırpar (zemin beyaz, logo bant; Lokman'ın dosyası 591 × 591). Beyaza yakın (her kanal ≥ `esik`)
    olmayan piksellerin kutusu + `pay` piksel; kutu yoksa resim aynen. PNG baytı döndürür."""
    import io
    from PIL import Image
    with Image.open(yol) as r:
        im = r.convert("RGB")
    maske = im.point(lambda v: 255 if v < esik else 0).convert("L").point(lambda v: 255 if v else 0)
    kutu = maske.getbbox()
    if kutu:
        x0, y0, x1, y1 = kutu
        im = im.crop((max(0, x0 - pay), max(0, y0 - pay), min(im.width, x1 + pay), min(im.height, y1 + pay)))
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def sayfalara_bol(bas: str, parca: list[str], sigar) -> list[str]:
    """Bölümleri sayfalara böler: önce hepsi tek sayfada; sığmazsa her sayfaya sığdığı kadar bölüm, bölüm ortadan bölünmez. Başlık
    yalnız ilk sayfada. `sigar(html, ilk)` sayfaya en küçük ölçekle sığıyor mu. Tek bölüm boş sayfaya sığmazsa durur."""
    if sigar(bas + "".join(parca), True):
        return [bas + "".join(parca)]
    sayfalar, i = [], 0
    while i < len(parca):
        ilk = not sayfalar
        ust = bas if ilk else ""
        j = i + 1
        if not sigar(ust + parca[i], ilk):
            raise ValueError("ihracat formu: bir bölüm boş sayfaya en küçük ölçekte de sığmadı")
        while j < len(parca) and sigar(ust + "".join(parca[i:j + 1]), ilk):
            j += 1
        sayfalar.append(ust + "".join(parca[i:j]))
        i = j
    return sayfalar


def pdf_yaz(D: dict, yol: Path, form: dict | None = None, tarih: str | None = None) -> Path:
    """Formu A4 PDF olarak yazar: tek sayfaya `en_kucuk_olcek`le sığarsa tek sayfa, sığmazsa bölüm sınırında ikinci sayfa (form.json).
    Logo yalnız ilk sayfada; beyaz kenarları kırpılır, sol üstte (en çok 170 × 34 nk, oranı korunur), firma adı yazısı yerine."""
    import pymupdf
    form = form or form_oku()
    tarih = tarih or dt.date.today().strftime("%d.%m.%Y")
    logo = D.get("logo")
    olcek = form["en_kucuk_olcek"]
    css = CSS + CSS_EK
    ust_ilk = 28.0 + (38 if logo else 0)

    def alan(ilk: bool):
        return pymupdf.Rect(KENAR, ust_ilk if ilk else 28.0, A4[0] - KENAR, A4[1] - 34)

    with pymupdf.open() as deneme:
        def sigar(h: str, ilk: bool) -> bool:
            sayfa = deneme.new_page(width=A4[0], height=A4[1])
            sonuc = sayfa.insert_htmlbox(alan(ilk), h, css=css, scale_low=olcek)[0] >= 0
            deneme.delete_page(-1)
            return sonuc
        sayfalar = sayfalara_bol(bas_html(D, form, tarih, bool(logo)), bolumler(D, form), sigar)
    doc = pymupdf.open()
    for n, h in enumerate(sayfalar):
        s = doc.new_page(width=A4[0], height=A4[1])
        if n == 0 and logo:
            s.insert_image(pymupdf.Rect(KENAR, 28.0, KENAR + 170, 28.0 + 34), stream=logo_kirp(Path(logo)), keep_proportion=True)
        if s.insert_htmlbox(alan(n == 0), h, css=css, scale_low=olcek)[0] < 0:
            raise ValueError("ihracat formu: sayfa sığmadı")
    kimlik = str(D["kod"] or "DRAFT")
    for n, s in enumerate(doc, 1):
        s.insert_htmlbox(pymupdf.Rect(KENAR, A4[1] - 26, A4[0] - KENAR, A4[1] - 12),
                         f"<p class='alt'>{e(kimlik)} · {e(form['alt_yazi'])} · page {n} / {doc.page_count}</p>", css=CSS)
    doc.set_metadata({"title": f"{kimlik} {form['alt_yazi']}", "creator": "Portman · araclar/teklif_ihracat.py", "producer": "",
                      "creationDate": "", "modDate": ""})
    yol.parent.mkdir(parents=True, exist_ok=True)
    doc.save(yol, garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return yol


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="İngilizce ihracat teklif ve satış onay formu (İE-46)")
    ap.add_argument("yollar", nargs="+", help="girdi dosyaları (sırayla birleşir), en sonda çıktı klasörü")
    ap.add_argument("--tarih", help="GG.AA.YYYY (yoksa bugün)")
    ap.add_argument("--taslak", action="store_true", help="eksik değerleri TBD yaz, DRAFT işaretle (önizleme)")
    a = ap.parse_args(argv)
    if len(a.yollar) < 2:
        ap.error("en az bir girdi dosyası ve çıktı klasörü gerekir")
    *girdiler, cikti = a.yollar
    form = form_oku()
    G, _ = girdi_birlestir([Path(p) for p in girdiler])
    try:
        D = hazirla(G, form, taslak=a.taslak)
    except ValueError as h:
        print(h, file=sys.stderr)
        return 1
    yol = pdf_yaz(D, Path(cikti) / dosya_adi(D, form), form, a.tarih)
    print(yol)
    if D["eksik"]:
        print(f"TASLAK: eksik {D['eksik']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
