"""İE-13 PR-6 · Teklif PDF'i (T5): `araclar/teklif.py`'nin teklifinden, Patron'un teklif formunun düzeninde. D-28: yalnız teklif komutuyla.

Düzen ve sabit metinler `kurallar/teklif/form.json`'da (Patron'un boş teklif formu "PREFABRİK - TEKLİF PORTATİFEV - YENİ"; verilen
tekliflerin PDF'iyle aynı düzen): başlık, 01 Bayi / firma bilgileri, 02 Ürün detayı, 03 Ödeme, 04 Paket içeriği ve teknik özellikleri,
05 Kapsam dışı işler; arkasında Ek-1, Motor'un yükleme listesi birim fiyat ve tutarıyla. Her seçenek ayrı PDF (asma ve ters tavan iki
teklif). Sayılar teklifin JSON'undan: tutar fiyatlı satırların toplamı, alan Motor'un brüt alanı. Fiyatı olmayan satırın birim fiyatı ve
tutarı boş kalır, toplama girmez; toplam eksikse ilk sayfada yazar. KDV tutarı yazılmaz (kaynak listelerde KDV durumu yok). Bayi adı
yazılmaz, kodu yazılır; müşteri adı yazılır (D-33); telefon hiç yazılmaz. Teknik özellikler formdan, üstüne İş Emri'nin `ozellikler`'i ve
seçeneğin tavanı; kat yüksekliği ve panel kalınlıkları İş Emri'nin `yapi`'sından; alıcıya ait kalem teknik özelliklerden çıkar, kapsam
dışına girer. Motor'u yüklemez (yalnız PyMuPDF).
"""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
FORM = KOK / "kurallar" / "teklif" / "form.json"
A4 = (595.0, 842.0)
KENAR = 36.0
CSS = """
* { font-family: sans-serif; font-size: 8pt; line-height: 1.25; }
p { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 0.5px solid #8c96a3; padding: 2px 4px; vertical-align: top; text-align: left; }
th { background-color: #dfe6ee; font-weight: bold; }
.ust td, .bas td { border: none; padding: 0 2px; vertical-align: middle; }
.marka { font-size: 20pt; font-weight: bold; color: #1f2d4d; letter-spacing: 1px; }
.baslik { font-size: 11pt; font-weight: bold; text-align: center; }
h2 { font-size: 9pt; font-weight: bold; color: #ffffff; background-color: #1f2d4d; margin: 8px 0 3px 0; padding: 2px 4px; }
.sag { text-align: right; }
.orta { text-align: center; }
.nw { white-space: nowrap; }
.kalin { font-weight: bold; }
.grup td { font-weight: bold; background-color: #dfe6ee; }
.ara td { font-weight: bold; }
.bos { background-color: #ececec; }
.uyari { color: #b0161b; font-weight: bold; }
.soluk { color: #5d6670; font-size: 7pt; }
.alt { color: #5d6670; font-size: 7pt; text-align: center; }
"""


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def tl(x) -> str:
    """Tutar hücresi: 3217 → "3.217,00 TL"; boş fiyat boş kalır."""
    if x is None:
        return ""
    return f"{x:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".") + " TL"


def sayi(x, basamak: int = 2) -> str:
    s = f"{float(x):.{basamak}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def kucuk(s: str) -> str:
    return str(s).replace("I", "ı").replace("İ", "i").lower().strip()


def satir(ad, deger) -> str:
    """Etiketli iki sütunlu satır (01, 03, 04). Genişlik hücrenin stilinde, nokta olarak: MuPDF sınıftaki ve yüzdeli genişliği
    uygulamıyor, değeri boş sütunu daraltıyor; toplam sayfanın yazı alanını (523 nk) aşmaz."""
    return f"<tr><td style='width:130px' class='kalin'>{e(ad)}</td><td style='width:370px'>{e(deger)}</td></tr>"


def form_oku(yol: Path | str = FORM) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def dosya_adi(T: dict, sec: dict) -> str:
    """`<kod>_teklif.pdf`; birden çok seçenekte `<kod>_teklif_<tavan>.pdf` (asma, ters)."""
    kod = str(T["kod"]).replace("-", "")
    if len(T["secenekler"]) == 1:
        return f"{kod}_teklif.pdf"
    return f"{kod}_teklif_{kucuk(sec['ozellikler'].get('Tavan') or sec['ad'].split()[0])}.pdf"


def teknik_ve_kapsam(form: dict, ie: dict, ozellikler: dict | None = None) -> tuple[list[list[str]], list[str]]:
    """(04'ün satırları, 05'in maddeleri). Formun satırı İş Emri'nin özelliğiyle aynı adı taşıyorsa değer İş Emri'nden (formun
    `deger_yazisi` karşılığıyla); formda olmayan özellik, adının ilk sözcüğünü taşıyan son satırın arkasına, yoksa sona eklenir. Alıcıya
    ait kalem adıyla başlayan satır çıkar, kapsam dışına "(alıcıya ait)" diye girer; satırı olmayan kalem de girer."""
    yapi = ie.get("yapi") or {}
    kal = yapi.get("duvar_kalinligi_cm") or {}
    mm = lambda cm: sayi(float(cm) * 10, 1)                 # noqa: E731
    deg = {"kat_mm": mm(yapi.get("duvar_yuksekligi_cm", 250)), "dis_mm": mm(kal.get("dis", 10)), "ic_mm": mm(kal.get("ic", 6))}
    satir = [[ad, metin.format(**deg)] for ad, metin in form["teknik"]]
    for k, v in {**(ie.get("ozellikler") or {}), **(ozellikler or {})}.items():
        v = str((form.get("deger_yazisi") or {}).get(k, {}).get(v, v))
        adlar = [kucuk(a) for a, _ in satir]
        if kucuk(k) in adlar:
            satir[adlar.index(kucuk(k))][1] = v
            continue
        ilk = kucuk(k).split()[0]
        yer = max((i for i, a in enumerate(adlar) if a.split()[0] == ilk), default=len(satir) - 1)
        satir.insert(yer + 1, [str(k), v])
    kapsam = list(form["kapsam_disi"])
    for k in (ie.get("alici_ait") or {}).get("kalemler") or []:
        cik = [r for r in satir if kucuk(r[0]).startswith(kucuk(k))]
        satir = [r for r in satir if r not in cik]
        kapsam += [f"{r[0]} (alıcıya ait)" for r in cik] or [f"{str(k)[:1].upper()}{str(k)[1:]} (alıcıya ait)"]
    return satir, kapsam


def ilk_sayfa(T: dict, ie: dict, sec: dict, form: dict, tarih: str) -> str:
    from araclar.teklif import uyari
    o = sec["fiyat"]["ozet"]
    talep = ie.get("talep") or {}
    kimlik = f"{T['is_emri_no']} r{T['revizyon']:02d}" if isinstance(T.get("revizyon"), int) else str(T.get("is_emri_no"))
    alan = (sec["liste"].get("girdi_ozeti") or {}).get("brut_m2")
    teknik, kapsam = teknik_ve_kapsam(form, ie, sec["ozellikler"])
    bos_kosul = [ad for ad, v in T["kosullar"].items() if not v]
    uy = "; ".join(x for x in (uyari(o), "onaysız öneriler dahil" if T["oneri_dahil"] else "",
                               f"{', '.join(bos_kosul)} boş (Patron'dan)" if bos_kosul else "") if x)
    k = []
    k.append(f"<table class='ust'><tr><td class='marka'>{e(form['firma'])}</td><td class='sag soluk'>{e(form['web'])}</td></tr></table>")
    k.append(f"<table class='bas'><tr><td class='nw'>Tarih: <b>{e(tarih)}</b></td><td class='baslik'>{e(form['baslik'])}"
             f"{' · TASLAK' if uy else ''}</td><td class='sag nw'>{e(kimlik)}</td></tr></table>")
    if uy:
        k.append(f"<p class='uyari'>{e(uy[:1].upper() + uy[1:])}." + (" Fiyatı olmayan satırlar Ek-1'de boş." if o["fiyatsiz"] else "") + "</p>")
    k.append("<h2>01 &nbsp; BAYİ / FİRMA BİLGİLERİ</h2><table>")
    k += [satir("Bayi", (talep.get("bayi") or {}).get("kod")), satir("Müşteri / proje", talep.get("musteri_adi")),
          satir("İletişim (GSM)", ""), satir("Adres", ""), "</table>"]
    k.append("<h2>02 &nbsp; ÜRÜN DETAYI</h2><table><tr><th>No</th><th>Ürün Tanımı</th><th class='sag'>Alan</th><th class='orta'>Mkt</th>"
             "<th class='sag'>Birim Fiyatı</th><th class='sag'>Tutar</th><th class='orta'>Kdv</th><th class='sag'>Toplam</th></tr>")
    k.append(f"<tr><td>1</td><td>{e(form['urun'])} · {e(sec['ad'])}</td><td class='sag nw'>{e(sayi(alan) + ' m²' if alan else '')}</td>"
             f"<td class='orta'>1</td><td class='sag nw'>{tl(o['toplam'])}</td><td class='sag nw'>{tl(o['toplam'])}</td><td class='orta'>—</td>"
             f"<td class='sag nw'>{tl(o['toplam'])}</td></tr>")
    k.append(f"<tr class='ara'><td colspan='7' class='sag'>Gen. Toplam</td><td class='sag nw'>{tl(o['toplam'])}</td></tr></table>")
    k.append(f"<p class='soluk'>Tutar, Motor'un yükleme listesinde fiyatı olan {o['fiyatli']} satırın toplamıdır ({o['satir']} satır; Ek-1); "
             f"fiyatlar fiyat defterinden ({e(T['defter_surumu'])}). Alan Motor'un brüt alanı (verandalar dahil). KDV tutarı yazılmadı: "
             "fiyat listelerinde KDV durumu belirtilmiyor.</p>")
    k.append("<h2>03 &nbsp; ÖDEME</h2><table>")
    for ad, v in T["kosullar"].items():
        k.append(satir(ad, v))
    k.append("</table><h2>04 &nbsp; PAKET İÇERİĞİ VE TEKNİK ÖZELLİKLERİ</h2><table>")
    for ad, v in teknik:
        k.append(satir(ad, v))
    k.append("</table><h2>05 &nbsp; KAPSAM DIŞI İŞLER (BAYİ/SAHA SORUMLULUKLARI)</h2><table>")
    for m in kapsam:
        k.append(f"<tr><td>• {e(m)}</td></tr>")
    k.append("</table>")
    return "".join(k)


def ek_satirlari(T: dict, sec: dict) -> tuple[str, str, list[tuple[str, str, str]], str]:
    """Ek-1'in parçaları: (başlık, tablo başı, satırlar, son). Satır (tür, grup, html); tür "grup", "kalem", "ara" ya da "genel". Motor'un
    listesi grup grup, birim fiyat ve tutarla (Excel'in seçenek sayfasıyla aynı satırlar ve toplamlar); ara toplamların toplamı özetin
    toplamını tutmazsa durur."""
    from araclar.liste_excel import GENEL, buyuk, eksik, gorunen
    R = sec["fiyat"]; o = R["ozet"]
    kg = any(s.get("kg") is not None for s in R["satirlar"])
    gen = [200 - 40 * kg, 72, 32, 28] + ([40] if kg else []) + [66, 70]     # nokta, iç dolgusuz; dolguyla yazı alanını (523) aşmaz
    n = len(gen)
    w = lambda i: f" style='width:{gen[i]}px'"            # noqa: E731
    baslik = (f"<p class='kalin'>EK-1 · MALZEME LİSTESİ VE BİRİM FİYATLAR · {e(sec['ad'])}</p>"
              f"<p class='soluk'>Liste Motor'dan ({e(sec['liste'].get('uretici_surum', '').split(' (')[0])}), fiyat defterden "
              f"({e(T['defter_surumu'])}). Fiyatı olmayan satırın birim fiyatı ve tutarı boş bırakıldı; toplama girmez.</p>")
    adlar = [("Kalem", ""), ("Ölçü", ""), ("Birim", "orta"), ("Adet", "sag")] + ([("kg", "sag")] if kg else []) \
        + [("Birim fiyat", "sag"), ("Tutar", "sag")]
    bas = "<tr>" + "".join(f"<th{w(i)} class='{c}'>{a}</th>" for i, (a, c) in enumerate(adlar)) + "</tr>"
    gruplar: dict[str, list[dict]] = {}
    for s in R["satirlar"]:
        gruplar.setdefault(s.get("grup_adi") or str(s.get("grup") or ""), []).append(s)
    satir: list[tuple[str, str, str]] = []
    toplam = 0.0
    for ad, ss in gruplar.items():
        satir.append(("grup", ad, f"<tr class='grup'><td colspan='{n}'>{e(buyuk(ad))}</td></tr>"))
        for s in ss:
            olcu, birim = gorunen(s.get("teklif_olcu") or s.get("olcu"), s.get("birim"))
            bos = " class='sag nw bos'" if s["birim_fiyat"] is None or eksik(s) else " class='sag nw'"
            hucre = [f"<td{w(0)}>{e(s.get('teklif_adi') or s['kalem'])}</td>", f"<td{w(1)} class='nw'>{e(olcu)}</td>", f"<td{w(2)} class='orta'>{e(birim)}</td>",
                     f"<td{w(3)} class='sag'>{e(s.get('adet') if s.get('adet') is not None else '')}</td>"]
            if kg:
                hucre.append(f"<td{w(4)} class='sag'>{e(sayi(s['kg']) if s.get('kg') is not None else '')}</td>")
            hucre += [f"<td{w(n - 2)}{bos}>{tl(s['birim_fiyat'])}</td>", f"<td{w(n - 1)}{bos}>{tl(s['tutar'])}</td>"]
            satir.append(("kalem", ad, "<tr>" + "".join(hucre) + "</tr>"))
        ara = round(sum(s["tutar"] or 0 for s in ss), 2)
        toplam += ara
        satir.append(("ara", ad, (f"<tr class='ara'><td colspan='{n - 1}' class='sag'>{e(ad)} toplamı</td><td{w(n - 1)} class='sag nw'>"
                                  f"{tl(ara)}</td></tr>")))
    if abs(toplam - o["toplam"]) > 0.005:
        raise ValueError(f"teklif PDF'i: ara toplamların toplamı {toplam:.2f}, özetin toplamı {o['toplam']:.2f}")
    satir.append(("genel", "", (f"<tr class='ara'><td colspan='{n - 1}' class='sag'>{e(GENEL)}</td><td{w(n - 1)} class='sag nw'>"
                                f"{tl(o['toplam'])}</td></tr>")))
    return baslik, bas, satir, f"<p class='kalin'>Fiyatı olmayan satır: {len(o['fiyatsiz'])}</p>"


def ek_sayfalari(baslik: str, bas: str, satir: list[tuple[str, str, str]], son: str, sigar) -> list[str]:
    """Ek-1'i sayfalara böler: her sayfa kendi tablosu, sütun başlığı her sayfada; grup başlığı sayfanın son satırı olmaz, sayfaya bölünen
    grubun başlığı yeni sayfada "(devam)" ile yinelenir. `sigar(html)` sayfaya sığıyor mu (ölçek 1)."""
    from araclar.liste_excel import buyuk
    n = bas.count("<th")
    sayfalar, i = [], 0
    while i < len(satir):
        ust = baslik if not sayfalar else ""
        if satir[i][0] in ("kalem", "ara"):                 # bölünen grubun başlığı yinelenir
            ust_satir = [f"<tr class='grup'><td colspan='{n}'>{e(buyuk(satir[i][1]))} (devam)</td></tr>"]
        else:
            ust_satir = []
        j = i + 1
        while j < len(satir) and sigar(ust + "<table>" + bas + "".join(ust_satir + [h for _, _, h in satir[i:j + 1]]) + "</table>"
                                       + (son if j + 1 == len(satir) else "")):
            j += 1
        if j < len(satir) and satir[j - 1][0] == "grup" and j - 1 > i:
            j -= 1
        sayfalar.append(ust + "<table>" + bas + "".join(ust_satir + [h for _, _, h in satir[i:j]]) + "</table>")
        i = j
    if not sigar(sayfalar[-1] + son):
        sayfalar.append(son)
    else:
        sayfalar[-1] += son
    return sayfalar


def pdf_yaz(T: dict, ie: dict, sec: dict, yol: Path, form: dict | None = None, tarih: str | None = None) -> Path:
    """Bir seçeneğin teklif PDF'i: ilk sayfa form (sığmazsa küçülür, yarıdan küçükse durur), arkasında Ek-1 (gerektiği kadar sayfa)."""
    import pymupdf
    form = form or form_oku()
    tarih = tarih or dt.date.today().strftime("%d.%m.%Y")
    kimlik = f"{T['kod']} · {sec['ad']}"
    alan = pymupdf.Rect(KENAR, 28, A4[0] - KENAR, A4[1] - 34)
    doc = pymupdf.open()
    s1 = doc.new_page(width=A4[0], height=A4[1])
    bos, _ = s1.insert_htmlbox(alan, ilk_sayfa(T, ie, sec, form, tarih), css=CSS, scale_low=0.5)
    if bos < 0:
        raise ValueError(f"teklif PDF'i: ilk sayfa yarı ölçekte de sığmadı ({kimlik})")
    with pymupdf.open() as deneme:
        def sigar(h: str) -> bool:
            sayfa = deneme.new_page(width=A4[0], height=A4[1])
            sonuc = sayfa.insert_htmlbox(alan, h, css=CSS, scale_low=1)[0] >= 0
            deneme.delete_page(-1)
            return sonuc
        for h in ek_sayfalari(*ek_satirlari(T, sec), sigar):
            if doc.new_page(width=A4[0], height=A4[1]).insert_htmlbox(alan, h, css=CSS, scale_low=1)[0] < 0:
                raise ValueError(f"teklif PDF'i: Ek-1 sayfası sığmadı ({kimlik})")
    for i, sayfa in enumerate(doc):
        sayfa.insert_htmlbox(pymupdf.Rect(KENAR, A4[1] - 26, A4[0] - KENAR, A4[1] - 12),
                             f"<p class='alt'>{e(kimlik)} · teklif · sayfa {i + 1} / {doc.page_count}</p>", css=CSS)
    doc.set_metadata({"title": f"{T['kod']} teklif · {sec['ad']}", "creator": "Portman · araclar/teklif.py", "producer": "",
                      "creationDate": "", "modDate": ""})
    yol.parent.mkdir(parents=True, exist_ok=True)
    doc.save(yol, garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return yol
