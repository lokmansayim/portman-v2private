"""İE-13 PR-6 · Teklif PDF'i (T5): `araclar/teklif.py`'nin teklifinden, Patron'un teklif formunun düzeninde. D-28: yalnız teklif komutuyla.

Düzen ve sabit metinler `kurallar/teklif/form.json`'da (Patron'un boş teklif formu "PREFABRİK - TEKLİF PORTATİFEV - YENİ"; verilen
tekliflerin PDF'iyle aynı düzen): başlık, 01 Bayi / firma bilgileri, 02 Ürün detayı, 03 Ödeme, 04 Paket içeriği ve teknik özellikleri,
05 Kapsam dışı işler; arkasında Ek-1, Motor'un yükleme listesi birim fiyat ve tutarıyla. Her seçenek ayrı PDF (asma ve ters tavan iki
teklif). Sayılar teklifin JSON'undan: tutar fiyatlı satırların toplamı, alan Motor'un brüt alanı. Fiyatı olmayan satırın birim fiyatı ve
tutarı boş kalır, toplama girmez; toplam eksikse ilk sayfada yazar. KDV tutarı yazılmaz (kaynak listelerde KDV durumu yok). Bayi adı
yazılmaz, kodu yazılır; müşteri adı yazılır (D-33); telefon hiç yazılmaz. Teknik özellikler formdan, üstüne İş Emri'nin `ozellikler`'i ve
seçeneğin tavanı; kat yüksekliği ve panel kalınlıkları İş Emri'nin `yapi`'sından; alıcıya ait kalem teknik özelliklerden çıkar, kapsam
dışına girer. Motor'u yüklemez (yalnız PyMuPDF).

Standart dışı değer 04'te kalın (D-64): satırın yalnız standarttan ayrılan kısmı (kat yüksekliği, panel kalınlığı, çatı kaplaması); standartlar
`form.json › standart`'ta. İki formda da.

Bayi formu (D-64; `araclar/teklif.py --bayi <girdi>`): bayiye giden teklif ve satış onay formu, tek seçenek. TASLAK ve uyarı satırı yok;
01 bayinin bilgileri girdiden (telefon `form.json › bayi_formu.telefon`'a göre: açık, D-64; "maskeli" ise son dört hane); 02'de ürün tanımı tavansız ("Tek Kat
Prefabrik Yapı"), birim fiyat teklifin toplamından pazarın kuralıyla (`kurallar/teklif/fiyatlandirma.json`: taban × (1 + kâr + KDV ×
fiyata katılan pay)), KDV pazarın fatura oranıyla; 03 girdiden, boş satırla form üretilmez; Ek-1'de malzeme listesi, birim fiyat ve tutar
boş, ara ve genel toplam yok, "Motor" ve "fiyatsız satır" yazılmaz.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
FORM = KOK / "kurallar" / "teklif" / "form.json"
FIYATLANDIRMA = KOK / "kurallar" / "teklif" / "fiyatlandirma.json"
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


def satir(ad, deger, kalin: str | list[str] | tuple[str, ...] | None = None) -> str:
    """Etiketli iki sütunlu satır (01, 03, 04). Genişlik hücrenin stilinde, nokta olarak: MuPDF sınıftaki ve yüzdeli genişliği
    uygulamıyor, değeri boş sütunu daraltıyor; toplam sayfanın yazı alanını (523 nk) aşmaz. `kalin` değerin kalın yazılan kısmı (ilk
    geçtiği yer; D-64); bayi formunun ek kalınlarıyla (D-77) birden çok kısım olabilir, her biri ilk geçtiği yerde."""
    d = e(deger)
    for k in ([kalin] if isinstance(kalin, str) else list(kalin or [])):
        if k and e(k) in d and f"<b>{e(k)}</b>" not in d:
            d = d.replace(e(k), f"<b>{e(k)}</b>", 1)
    return f"<tr><td style='width:130px' class='kalin'>{e(ad)}</td><td style='width:370px'>{d}</td></tr>"


def form_oku(yol: Path | str = FORM) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def fiyatlandirma_oku(yol: Path | str = FIYATLANDIRMA) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def yapi_degerleri(ie: dict) -> dict[str, str]:
    """Formun yer tutucuları: kat yüksekliği ve panel kalınlıkları mm, İş Emri'nin `yapi`'sından (yoksa 250, 10, 6 cm)."""
    yapi = ie.get("yapi") or {}
    kal = yapi.get("duvar_kalinligi_cm") or {}
    mm = lambda cm: sayi(float(cm) * 10, 1)                 # noqa: E731
    return {"kat_mm": mm(yapi.get("duvar_yuksekligi_cm", 250)), "dis_mm": mm(kal.get("dis", 10)), "ic_mm": mm(kal.get("ic", 6))}


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
    deg = yapi_degerleri(ie)
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


def standart_disi(form: dict, ie: dict, teknik: list[list[str]]) -> dict[str, str]:
    """04'te kalın yazılacak kısımlar, {satır adı: kalın kısım} (D-64; Lokman 6 Kasım 2026 08:38, madde 6). `form.json › standart`:
    yerli satırda (kat yüksekliği, panel kalınlıkları) yerin yazısı standarttan ayrıysa o yazı ("160 mm"); sözcüklü satırda (çatı
    kaplaması) değer sözcüğü içermiyorsa değerin tamamı. Teknik özelliklerde olmayan satır kalın almaz."""
    deg = yapi_degerleri(ie)
    d = dict(teknik)
    sonuc: dict[str, str] = {}
    for ad, k in ((form.get("standart") or {}).get("satirlar") or {}).items():
        v = d.get(ad)
        if not v:
            continue
        if "deger" in k:
            yazi = k["deger"].format(**deg)
            if yazi != k["standart"] and yazi in v:
                sonuc[ad] = yazi
        elif kucuk(k["standart_sozcuk"]) not in kucuk(v):
            sonuc[ad] = v
    return sonuc


def _bas(form: dict, tarih: str, kimlik: str, ek: str = "") -> str:
    return (f"<table class='ust'><tr><td class='marka'>{e(form['firma'])}</td><td class='sag soluk'>{e(form['web'])}</td></tr></table>"
            f"<table class='bas'><tr><td class='nw'>Tarih: <b>{e(tarih)}</b></td><td class='baslik'>{e(form['baslik'])}{ek}</td>"
            f"<td class='sag nw'>{e(kimlik)}</td></tr></table>")


def _urun(ad: str, alan, birim: float, kdv: str, toplam: float, ek: list[str] | tuple[str, ...] = ()) -> str:
    """02'nin tablosu: tek satır (miktar 1, tutar = birim fiyat) ve genel toplam. `ek` bayi formunun ek ürün satırları (D-77): yalnız
    tanım, numara, alan, miktar ve fiyat hücreleri boş; genel toplam değişmez."""
    ek_satir = "".join(f"<tr><td></td><td>{e(x)}</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>" for x in ek)
    return ("<h2>02 &nbsp; ÜRÜN DETAYI</h2><table><tr><th>No</th><th>Ürün Tanımı</th><th class='sag'>Alan</th><th class='orta'>Mkt</th>"
            "<th class='sag'>Birim Fiyatı</th><th class='sag'>Tutar</th><th class='orta'>Kdv</th><th class='sag'>Toplam</th></tr>"
            f"<tr><td>1</td><td>{e(ad)}</td><td class='sag nw'>{e(sayi(alan) + ' m²' if alan else '')}</td>"
            f"<td class='orta'>1</td><td class='sag nw'>{tl(birim)}</td><td class='sag nw'>{tl(birim)}</td><td class='orta'>{e(kdv)}</td>"
            f"<td class='sag nw'>{tl(toplam)}</td></tr>{ek_satir}"
            f"<tr class='ara'><td colspan='7' class='sag'>Gen. Toplam</td><td class='sag nw'>{tl(toplam)}</td></tr></table>")


def teknik_ekleri(teknik: list[list[str]], kapsam: list[str], kalin: dict[str, str], ek: dict | None) -> tuple[list, list, dict]:
    """Bayi formunun 04 ve 05 ekleri (D-77; girdiden, `bayi_hazirla`): `ek_yazi` satırın değerinin sonuna " - <yazı>" ekler, yazı kalın;
    `kalin` satırın değerini bütünüyle kalın yapar; `kapsam_disina` satırı 04'ten çıkarır, 05'in başına "<ad>: <değer>" diye bütünüyle
    koyar. Satır adı 04'te yoksa durur (ValueError). Sonuç (04 satırları, 05 maddeleri, {satır: kalın kısımlar})."""
    k = {ad: [v] for ad, v in kalin.items()}
    if not ek:
        return teknik, kapsam, k
    teknik = [list(r) for r in teknik]
    adlar = lambda: [kucuk(a) for a, _ in teknik]                            # noqa: E731

    def bul(ad: str) -> list[str]:
        if kucuk(ad) not in adlar():
            raise ValueError(f"bayi formu: 04'te '{ad}' satırı yok; satırlar {[a for a, _ in teknik]}")
        return teknik[adlar().index(kucuk(ad))]
    for ad, yazi in (ek.get("ek_yazi") or {}).items():
        r = bul(ad)
        r[1] = f"{r[1]} - {yazi}"
        k.setdefault(r[0], []).append(str(yazi))
    for ad in ek.get("kalin") or []:
        r = bul(ad)
        k[r[0]] = [r[1]]
    cik = [bul(ad) for ad in ek.get("kapsam_disina") or []]
    teknik = [r for r in teknik if r not in cik]
    return teknik, [f"{a}: {v}" for a, v in cik] + list(kapsam), k


def _teknik_kapsam(form: dict, ie: dict, sec: dict, ek: dict | None = None) -> str:
    """04 (standart dışı kalın) ve 05; `ek` bayi formunun ekleri (D-77, `teknik_ekleri`)."""
    teknik, kapsam = teknik_ve_kapsam(form, ie, sec["ozellikler"])
    teknik, kapsam, kalin = teknik_ekleri(teknik, kapsam, standart_disi(form, ie, teknik), ek)
    k = ["<h2>04 &nbsp; PAKET İÇERİĞİ VE TEKNİK ÖZELLİKLERİ</h2><table>"]
    k += [satir(ad, v, kalin.get(ad)) for ad, v in teknik]
    k.append("</table><h2>05 &nbsp; KAPSAM DIŞI İŞLER (BAYİ/SAHA SORUMLULUKLARI)</h2><table>")
    k += [f"<tr><td>• {e(m)}</td></tr>" for m in kapsam]
    k.append("</table>")
    return "".join(k)


def _kimlik(T: dict) -> str:
    return f"{T['is_emri_no']} r{T['revizyon']:02d}" if isinstance(T.get("revizyon"), int) else str(T.get("is_emri_no"))


def kdv_cumlesi(k: dict) -> str:
    """D-76: iç teklifin ilk sayfasında KDV cümlesi (CRM defteri). Tutar KDV hariçtir; KDV kalem grubunun oranıyla."""
    from araclar.fiyatla import kdv_yazi
    return e(f"Tutar KDV hariçtir. Kalem grubunun oranıyla KDV {tl(k['kdv'])}, KDV dahil {tl(k['dahil'])} ({kdv_yazi(k)}; D-76).")


def ilk_sayfa(T: dict, ie: dict, sec: dict, form: dict, tarih: str) -> str:
    from araclar.teklif import uyari
    o = sec["fiyat"]["ozet"]
    talep = ie.get("talep") or {}
    alan = (sec["liste"].get("girdi_ozeti") or {}).get("brut_m2")
    bos_kosul = [ad for ad, v in T["kosullar"].items() if not v]
    uy = "; ".join(x for x in (uyari(o), "onaysız öneriler dahil" if T["oneri_dahil"] else "",
                               f"{', '.join(bos_kosul)} boş (Patron'dan)" if bos_kosul else "") if x)
    k = [_bas(form, tarih, _kimlik(T), " · TASLAK" if uy else "")]
    if uy:
        k.append(f"<p class='uyari'>{e(uy[:1].upper() + uy[1:])}." + (" Fiyatı olmayan satırlar Ek-1'de boş." if o["fiyatsiz"] else "") + "</p>")
    k.append("<h2>01 &nbsp; BAYİ / FİRMA BİLGİLERİ</h2><table>")
    k += [satir("Bayi", (talep.get("bayi") or {}).get("kod")), satir("Müşteri / proje", talep.get("musteri_adi")),
          satir("İletişim (GSM)", ""), satir("Adres", ""), "</table>"]
    k.append(_urun(f"{form['urun']} · {sec['ad']}", alan, o["toplam"], "—", o["toplam"]))
    k.append(f"<p class='soluk'>Tutar, Motor'un yükleme listesinde fiyatı olan {o['fiyatli']} satırın toplamıdır ({o['satir']} satır; Ek-1); "
             f"fiyatlar fiyat defterinden ({e(T['defter_surumu'])}). Alan Motor'un brüt alanı (verandalar dahil). "
             + (kdv_cumlesi(o["kdv"]) if o.get("kdv") else "KDV tutarı yazılmadı: fiyat listelerinde KDV durumu belirtilmiyor.") + "</p>")
    k.append("<h2>03 &nbsp; ÖDEME</h2><table>")
    for ad, v in T["kosullar"].items():
        k.append(satir(ad, v))
    k.append("</table>")
    k.append(_teknik_kapsam(form, ie, sec))
    return "".join(k)


# ── Bayi formu (D-64) ──────────────────────────────────────────────────────────────────────────────────────────────────────────────

def bayi_fiyati(taban: float, pazar: dict) -> dict:
    """Bayi formunun fiyatı (`fiyatlandirma.json`): birim = taban × (1 + kâr + KDV × fiyata katılan pay), kuruşa yuvarlı; formdaki KDV =
    birim × fatura oranı; toplam = birim + KDV."""
    artis = pazar["kar_orani"] + pazar["kdv_orani"] * pazar["fiyata_katilan_kdv_payi"]
    birim = round(taban * (1 + artis), 2)
    kdv = round(birim * pazar["faturada_kdv_orani"], 2)
    return {"taban": round(taban, 2), "artis_orani": round(artis, 6), "birim": birim, "kdv_orani": pazar["faturada_kdv_orani"],
            "kdv": kdv, "toplam": round(birim + kdv, 2)}


EKLER = ("urun_ek_satirlari", "ek_yazi", "kalin", "kapsam_disina", "on_onay_paftasi", "sabit_fiyat")


def ekleri_denetle(girdi: dict) -> dict:
    """Bayi formunun isteğe bağlı ekleri (D-77; Lokman, 11 Kasım 2026 09:02, TK-06): `urun_ek_satirlari` 02'ye fiyatsız ürün satırları
    ["İç Cephe Alçıpan Kaplama"]; `ek_yazi` {"Çatı Kaplaması": "Antrasit Gri"} 04'teki satırın sonuna " - Antrasit Gri", kalın; `kalin`
    ["Tavan"] 04'teki satırın değeri bütünüyle kalın; `kapsam_disina` ["Pencereler"] 04'teki satır bütünüyle 05'e; `on_onay_paftasi`
    true ise 2. sayfa Motor'un ön onay paftası (`motor/dxf_out.uret`'in A4 PDF'i, `araclar/teklif.py` üretir; Lokman 09:17:35 "2. sayfaya
    png yi değil ön onay paftasını koy"); `sabit_fiyat` {"birim": 550000, "kdv_orani": 0} 02'nin fiyatı Lokman'ın verdiği tutar, pazarın
    hesabı JSON'da kalır, açıklamada KDV cümlesi yazmaz (Lokman 09:17:35 "birim fiyatı 550.000 TL yap KDV yi 0 Yap … ürün detayı
    açıklama kısmına yazdığın KDV detayını sil"). Ek yoksa form eskisiyle aynı. Biçimi bozuk ek durur (ValueError)."""
    ek = {k: girdi[k] for k in EKLER if k in girdi}
    liste = lambda v: isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)    # noqa: E731
    for k in ("urun_ek_satirlari", "kalin", "kapsam_disina"):
        if k in ek and not liste(ek[k]):
            raise ValueError(f"bayi formu: {k} boş olmayan yazılardan bir liste olmalı: {ek[k]!r}")
    if "ek_yazi" in ek and not (isinstance(ek["ek_yazi"], dict) and all(isinstance(v, str) and v.strip() for v in ek["ek_yazi"].values())):
        raise ValueError(f"bayi formu: ek_yazi {{satır: yazı}} olmalı: {ek['ek_yazi']!r}")
    if "on_onay_paftasi" in ek and not isinstance(ek["on_onay_paftasi"], bool):
        raise ValueError(f"bayi formu: on_onay_paftasi true ya da false olmalı: {ek['on_onay_paftasi']!r}")
    if "sabit_fiyat" in ek:
        sf = ek["sabit_fiyat"]
        sayi_mi = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)          # noqa: E731
        if not (isinstance(sf, dict) and set(sf) == {"birim", "kdv_orani"} and sayi_mi(sf["birim"]) and sf["birim"] > 0
                and sayi_mi(sf["kdv_orani"]) and 0 <= sf["kdv_orani"] <= 1):
            raise ValueError(f"bayi formu: sabit_fiyat {{\"birim\": > 0, \"kdv_orani\": 0–1}} olmalı: {sf!r}")
    return ek


def sabit_fiyatla(hesap: dict, sabit: dict) -> dict:
    """Lokman'ın verdiği fiyat (D-77): birim ve KDV oranı girdiden; taban ve pazarın hesabı (`hesaplanan`) kayıtta kalır."""
    birim = round(float(sabit["birim"]), 2)
    kdv = round(birim * sabit["kdv_orani"], 2)
    return {"taban": hesap["taban"], "artis_orani": round(birim / hesap["taban"] - 1, 6) if hesap["taban"] else None, "birim": birim,
            "kdv_orani": sabit["kdv_orani"], "kdv": kdv, "toplam": round(birim + kdv, 2), "sabit": True,
            "hesaplanan": {k: hesap[k] for k in ("artis_orani", "birim", "kdv_orani", "kdv", "toplam")}}


def bayi_hazirla(girdi: dict, ie: dict, taban: float, form: dict | None = None, kural: dict | None = None) -> dict:
    """Bayi formunun girdisini denetler ve formun değerlerini hazırlar. Girdi (proje klasöründe; depoya girmez):
    `{"pazar": "yurt_disi", "bilgi": {"Bayi": …, "İletişim (GSM)": …, "Adres": …}, "kosullar": {"Teslim süresi": …, …}}`.
    Bilinmeyen alan, tanımsız pazar, boş zorunlu bilgi ya da boş ödeme satırı durur (ValueError): form uydurmaz, TASLAK yazmaz.
    "Müşteri / proje" girdide yoksa İş Emri'nin müşteri adı. Telefon `bayi_formu.telefon` "acik" ise olduğu gibi (D-64; Lokman 6 Kasım
    09:01), "maskeli" ise son dört hane (D-33 madde 3)."""
    from beyin import numara
    form = form or form_oku()
    kural = kural or fiyatlandirma_oku()
    B = form["bayi_formu"]
    if bilinmeyen := sorted(set(girdi) - {"sema", "aciklama", "pazar", "bilgi", "kosullar"} - set(EKLER)):
        raise ValueError(f"bayi formu: bilinmeyen alan {bilinmeyen}")
    pazar = kural["pazarlar"].get(girdi.get("pazar"))
    if pazar is None:
        raise ValueError(f"bayi formu: pazar {girdi.get('pazar')!r} tanımlı değil; tanımlılar {sorted(kural['pazarlar'])} "
                         "(kurallar/teklif/fiyatlandirma.json)")
    bilgi = dict(girdi.get("bilgi") or {})
    kosul = dict(girdi.get("kosullar") or {})
    if bilinmeyen := sorted(set(bilgi) - set(B["bilgi_satirlari"])) + sorted(set(kosul) - set(B["odeme_satirlari"])):
        raise ValueError(f"bayi formu: bilinmeyen satır {bilinmeyen}; bilinenler {B['bilgi_satirlari'] + B['odeme_satirlari']}")
    if not str(bilgi.get("Müşteri / proje") or "").strip():
        bilgi["Müşteri / proje"] = (ie.get("talep") or {}).get("musteri_adi") or ""
    if eksik := [k for k in B["zorunlu_bilgi"] + B["odeme_satirlari"] if not str({**bilgi, **kosul}.get(k) or "").strip()]:
        raise ValueError(f"bayi formu: boş satır {eksik}; değer girdiden verilir, uydurulmaz")
    if B.get("telefon") == "maskeli":
        bilgi = {k: numara.maskele(str(v), son_dort=True) for k, v in bilgi.items()}
    ekler = ekleri_denetle(girdi)
    kat = B["kat_adi"].get(str((ie.get("yapi") or {}).get("kat_sayisi", 1)))
    if kat is None:
        raise ValueError(f"bayi formu: {(ie.get('yapi') or {}).get('kat_sayisi')} katın ürün adı yok (form.json › bayi_formu.kat_adi)")
    return {"pazar": girdi["pazar"], "pazar_kurali": pazar, "urun": B["urun"].format(kat=kat),
            "bilgi": [(k, str(bilgi.get(k) or "")) for k in B["bilgi_satirlari"]],
            "kosullar": [(k, str(kosul[k])) for k in B["odeme_satirlari"]],
            "fiyat": sabit_fiyatla(bayi_fiyati(taban, pazar), ekler["sabit_fiyat"]) if "sabit_fiyat" in ekler else bayi_fiyati(taban, pazar),
            "ekler": ekler}


def bayi_dosya_adi(T: dict, form: dict | None = None) -> str:
    return (form or form_oku())["bayi_formu"]["dosya"].format(kod=str(T["kod"]).replace("-", ""))


def bayi_ilk_sayfa(T: dict, ie: dict, sec: dict, form: dict, tarih: str, bayi: dict) -> str:
    """Bayi formunun ilk sayfası: TASLAK ve uyarı yok; 01 girdiden, 02 pazarın fiyatıyla, açıklama bayinin anlayacağı dille (Motor, defter,
    fiyatsız satır yazılmaz), 03 girdiden, 04 ve 05 iç teklifteki gibi."""
    P, Fy = bayi["pazar_kurali"], bayi["fiyat"]
    alan = (sec["liste"].get("girdi_ozeti") or {}).get("brut_m2")
    k = [_bas(form, tarih, _kimlik(T)), "<h2>01 &nbsp; BAYİ / FİRMA BİLGİLERİ</h2><table>"]
    k += [satir(ad, v) for ad, v in bayi["bilgi"]] + ["</table>"]
    ek = bayi.get("ekler") or {}
    k.append(_urun(bayi["urun"], alan, Fy["birim"], f"%{sayi(Fy['kdv_orani'] * 100)}", Fy["toplam"], ek.get("urun_ek_satirlari") or ()))
    kdv_notu = "" if Fy.get("sabit") else (P.get("kdv_notu") or "")          # D-77: sabit fiyatta KDV cümlesi yok
    k.append(f"<p class='soluk'>{e(' '.join(form['bayi_formu']['fiyat_aciklamasi'].format(kdv_notu=kdv_notu).split()))}</p>")
    k.append("<h2>03 &nbsp; ÖDEME</h2><table>")
    k += [satir(ad, v) for ad, v in bayi["kosullar"]] + ["</table>"]
    k.append(_teknik_kapsam(form, ie, sec, ek))
    return "".join(k)


def ek_satirlari(T: dict, sec: dict, bayi_basligi: str | None = None) -> tuple[str, str, list[tuple[str, str, str]], str]:
    """Ek-1'in parçaları: (başlık, tablo başı, satırlar, son). Satır (tür, grup, html); tür "grup", "kalem", "ara" ya da "genel". Motor'un
    listesi grup grup, birim fiyat ve tutarla (Excel'in seçenek sayfasıyla aynı satırlar ve toplamlar); ara toplamların toplamı özetin
    toplamını tutmazsa durur. `bayi_basligi` verilirse bayi formunun eki (D-64): o başlık, aynı satırlar, birim fiyat ve tutar boş, ara
    ve genel toplam yok, son yok; adedi 0 olan satır (pakette yok) yazılmaz."""
    bayi = bayi_basligi is not None
    from araclar.liste_excel import GENEL, buyuk, eksik, gorunen
    R = sec["fiyat"]; o = R["ozet"]
    kg = any(s.get("kg") is not None for s in R["satirlar"])
    gen = [200 - 40 * kg, 72, 32, 28] + ([40] if kg else []) + [66, 70]     # nokta, iç dolgusuz; dolguyla yazı alanını (523) aşmaz
    n = len(gen)
    w = lambda i: f" style='width:{gen[i]}px'"            # noqa: E731
    baslik = f"<p class='kalin'>{e(bayi_basligi)}</p>" if bayi else (
              f"<p class='kalin'>EK-1 · MALZEME LİSTESİ VE BİRİM FİYATLAR · {e(sec['ad'])}</p>"
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
        gorunur = [s for s in ss if not (bayi and s.get("adet") == 0)]      # bayi formunda adedi 0 olan satır yazılmaz
        if gorunur:
            satir.append(("grup", ad, f"<tr class='grup'><td colspan='{n}'>{e(buyuk(ad))}</td></tr>"))
        for s in gorunur:
            olcu, birim = gorunen(s.get("teklif_olcu") or s.get("olcu"), s.get("birim"))
            bos = " class='sag nw bos'" if s["birim_fiyat"] is None or eksik(s) else " class='sag nw'"
            hucre = [f"<td{w(0)}>{e(s.get('teklif_adi') or s['kalem'])}</td>", f"<td{w(1)} class='nw'>{e(olcu)}</td>", f"<td{w(2)} class='orta'>{e(birim)}</td>",
                     f"<td{w(3)} class='sag'>{e(s.get('adet') if s.get('adet') is not None else '')}</td>"]
            if kg:
                hucre.append(f"<td{w(4)} class='sag'>{e(sayi(s['kg']) if s.get('kg') is not None else '')}</td>")
            if bayi:
                hucre += [f"<td{w(n - 2)} class='sag nw'></td>", f"<td{w(n - 1)} class='sag nw'></td>"]
            else:
                hucre += [f"<td{w(n - 2)}{bos}>{tl(s['birim_fiyat'])}</td>", f"<td{w(n - 1)}{bos}>{tl(s['tutar'])}</td>"]
            satir.append(("kalem", ad, "<tr>" + "".join(hucre) + "</tr>"))
        ara = round(sum(s["tutar"] or 0 for s in ss), 2)
        toplam += ara
        if not bayi:
            satir.append(("ara", ad, (f"<tr class='ara'><td colspan='{n - 1}' class='sag'>{e(ad)} toplamı</td><td{w(n - 1)} class='sag nw'>"
                                      f"{tl(ara)}</td></tr>")))
    if abs(toplam - o["toplam"]) > 0.005:
        raise ValueError(f"teklif PDF'i: ara toplamların toplamı {toplam:.2f}, özetin toplamı {o['toplam']:.2f}")
    if bayi:
        return baslik, bas, satir, ""
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


def pdf_yaz(T: dict, ie: dict, sec: dict, yol: Path, form: dict | None = None, tarih: str | None = None,
            bayi: dict | None = None) -> Path:
    """Bir seçeneğin teklif PDF'i: ilk sayfa form (sığmazsa küçülür, yarıdan küçükse durur), arkasında Ek-1 (gerektiği kadar sayfa).
    `bayi` (`bayi_hazirla`'nın sonucu) verilirse bayi formu (D-64)."""
    import pymupdf
    form = form or form_oku()
    tarih = tarih or dt.date.today().strftime("%d.%m.%Y")
    kimlik = str(T["kod"]) if bayi else f"{T['kod']} · {sec['ad']}"
    alt_yazi = form["bayi_formu"]["alt_yazi"] if bayi else "teklif"
    ilk = bayi_ilk_sayfa(T, ie, sec, form, tarih, bayi) if bayi else ilk_sayfa(T, ie, sec, form, tarih)
    ek = ek_satirlari(T, sec, form["bayi_formu"]["ek_basligi"]) if bayi else ek_satirlari(T, sec)
    alan = pymupdf.Rect(KENAR, 28, A4[0] - KENAR, A4[1] - 34)
    doc = pymupdf.open()
    s1 = doc.new_page(width=A4[0], height=A4[1])
    bos, _ = s1.insert_htmlbox(alan, ilk, css=CSS, scale_low=0.5)
    if bos < 0:
        raise ValueError(f"teklif PDF'i: ilk sayfa yarı ölçekte de sığmadı ({kimlik})")
    if bayi and bayi.get("on_onay_pdf"):                    # D-77: 2. sayfa Motor'un ön onay paftası; alt yazıya yer bırakır
        with pymupdf.open(bayi["on_onay_pdf"]) as pafta:
            doc.new_page(width=A4[0], height=A4[1]).show_pdf_page(pymupdf.Rect(0, 0, A4[0], A4[1] - 30), pafta, 0, keep_proportion=True)
    with pymupdf.open() as deneme:
        def sigar(h: str) -> bool:
            sayfa = deneme.new_page(width=A4[0], height=A4[1])
            sonuc = sayfa.insert_htmlbox(alan, h, css=CSS, scale_low=1)[0] >= 0
            deneme.delete_page(-1)
            return sonuc
        for h in ek_sayfalari(*ek, sigar):
            if doc.new_page(width=A4[0], height=A4[1]).insert_htmlbox(alan, h, css=CSS, scale_low=1)[0] < 0:
                raise ValueError(f"teklif PDF'i: Ek-1 sayfası sığmadı ({kimlik})")
    for i, sayfa in enumerate(doc):
        sayfa.insert_htmlbox(pymupdf.Rect(KENAR, A4[1] - 26, A4[0] - KENAR, A4[1] - 12),
                             f"<p class='alt'>{e(kimlik)} · {e(alt_yazi)} · sayfa {i + 1} / {doc.page_count}</p>", css=CSS)
    doc.set_metadata({"title": f"{T['kod']} {alt_yazi}" if bayi else f"{T['kod']} teklif · {sec['ad']}",
                      "creator": "Portman · araclar/teklif.py", "producer": "",
                      "creationDate": "", "modDate": ""})
    yol.parent.mkdir(parents=True, exist_ok=True)
    doc.save(yol, garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return yol
