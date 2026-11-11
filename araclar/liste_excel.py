"""İE-13 PR-2 · Fiyatlı listenin Excel sayfası: teklifin (`araclar/teklif.py`) ve `fiyatla.py --excel`'in tek yazıcısı.

Düzen Patron'un yükleme listesinin düzeni (28 Ekim 06:40–06:41): grup adı sütun değil, grubun üstünde başlık satırı ve altında ara toplam;
tek "Adet" sütunu; ölçüsü birim sözcüğü olan satırda (adet, metre, kova, paket, takım) ölçü boş, birim o. Genel toplam ve fiyatı olmayan
satır sayısı `fiyatla.fiyatla`'nın özetinden; sayfa saymaz, yazar. Motor'u yüklemez (yalnız openpyxl).

Adedi 0 olan satır (kalem bu evde yok: 60'lık köşe direği, 3'lü H …) sayfaya yazılmaz; adedi olmayan (Motor'da kuralı yok) satır gri
kalır. Lokman, 11 Kasım 2026 10:46 UTC (TK-07 teklifi): "hiç kullanılmayan malzemeyi listeden çıkar mesala 6'lık köşe direği 60 x 60
listeden kaldır". Teklif PDF'inin Ek-1'i de aynı satırları yazar (`teklif_pdf.ek_satirlari`; bayi formunda D-64'ten beri böyle).

KDV (D-76): özet `kdv` taşıyorsa (CRM defteri) Tutar'ın yanında "KDV %" ve "KDV" sütunları, ara toplamda grubun KDV'si, genel toplamın
altında KDV ve KDV DAHİL TOPLAM satırları (Lokman 10 Kasım 16:56, çelik fiyat sohbeti: "bir satır daha aç ve yanlarına yaz"). Oranı
olmayan satırın KDV hücreleri boş ve sarı. Özette `kdv` yoksa sayfa eskisi gibidir.

Formüllü sayfa (`formullu=True`, teklif Excel'i): Tutar = adet (kg'lı kalemde kg) × birim fiyat, KDV = tutar × KDV %, ara toplam, genel
toplam, KDV ve KDV dahil toplam Excel formülüdür; en altta kâr marjı yüzdesi (Lokman yazar, ilk değer %0), kâr ve kâr dahil toplamlar.
Kâr maliyetin üstüne eklenir: kâr = KDV hariç toplam × kâr %; KDV de aynı oranla büyür. Lokman, 11 Kasım 2026 10:54 UTC (TK-07 teklifi):
"excel'i tüm kalemleri formülleriyle ver birim fiyatı veya adeti değiştirdiğimde toplamda değişsin"; 10:55: "en sona kar marjı yüzdesi koy
ben belirleyeyim". Üretimde formüllerin sonucu JSON'un sayılarıyla aynıdır (sayfa yazılırken denetlenir). Kayıttan sonra
`onbellek_yaz` sonuçları hücreye önbellek değeri olarak da yazar: formül hesaplamayan görüntüleyici boş göstermez (Lokman 11:31).
"""
from __future__ import annotations

BIRIM = {"m": "metre"}
BIRIM_SOZCUK = {"adet", "metre", "kova", "paket", "takım", "m²"}    # Motor'un ölçü yerine yazdığı birimler
TL = "#,##0.00"
RENK = {"sari": "FFF2A8", "gri": "E7E7E7", "baslik": "D9E1F2", "cizgi": "8EA9DB",
        "öneri onaylı": "FCE4D6", "ikinci kaynak": "DDEBF7", "öneri": "FFF2A8"}
GENEL = "GENEL TOPLAM (fiyatı olan satırlar)"
KDV_SUTUN = ["KDV %", "KDV"]
KAR = "KÂR MARJI %"
FORMUL_ACIKLAMA = ("Tutar, toplamlar ve kâr formüldür: adedi ya da birim fiyatı değiştirin, toplamlar kendiliğinden değişir. Fiyatı boş "
                   "satıra fiyat yazarsanız KDV %'sini de yazın. Kâr marjı yüzdesini en alttaki sarı hücreye yazın.")


def buyuk(s: str) -> str:
    """Türkçe büyük harf: "Elektrik" → "ELEKTRİK", "Sıhhi" → "SIHHİ" (str.upper i'yi I yapar)."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def gorunen(olcu: str | None, birim: str | None) -> tuple[str, str]:
    """(ölçü, birim): ölçü bir birim sözcüğüyse ölçü boş kalır, birim o olur; öteki ölçüler ("—", "roll form çelik") yerinde kalır."""
    olcu = olcu or ""
    if olcu in BIRIM_SOZCUK:
        return "", olcu
    return olcu, BIRIM.get(birim, birim or "")


def tl_yazi(x: float) -> str:
    """Türkçe tutar yazısı: 3217 → "3.217", 1045.5 → "1.045,50"."""
    y = f"{x:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return y[:-3] if y.endswith(",00") else y


def fiyat_notu(s: dict) -> str:
    """Fiyatı olmayan satırın Not'u: uygulanmayan öneri varsa birim fiyatıyla (toplama girmez)."""
    o = s.get("oneri_fiyat")
    return "fiyat yok" if o is None else f"fiyat yok; öneri {tl_yazi(o)} TL, onay bekliyor (toplama girmedi)"


def eksik(s: dict) -> str | None:
    """Satırın miktarı yoksa nedeni (Not sütunu, gri satır, Özet'in Neden'i hep buradan): adet ya da kg'lı kalemde kg."""
    if s.get("birim") == "kg":
        return "kg yok" if s.get("kg") is None else None
    return "Motor'da kuralı yok, adet yok" if s.get("adet") is None else None


def _stil():
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    dolgu = {k: PatternFill("solid", fgColor=v) for k, v in RENK.items()}
    return Alignment, Border, Font, dolgu, Side


def formul_degeri(ws, ref: str):
    """Bu modülün yazdığı formüllerin değeri (yazım denetimi ve testler için; genel bir Excel hesaplayıcısı değildir). Boş sonuç "".
    Yuvarlama Python'un `round`'u, JSON'un sayılarıyla aynı; Excel'in ROUND'u yarımda (0,005) bir kuruş farklı olabilir."""
    import re
    v = ws[ref].value
    if not (isinstance(v, str) and v.startswith("=")):
        return v
    f, wb = v[1:], ws.parent

    def hucre(x: str):
        m = re.fullmatch(r"(?:'((?:[^']|'')+)'!)?([A-Z]+\d+)", x)
        return formul_degeri(wb[m[1].replace("''", "'")] if m[1] else ws, m[2])

    def degerler(arg: str) -> list:
        out = []
        for a in arg.split(","):
            if ":" not in a:
                out.append(hucre(a)); continue
            m = re.fullmatch(r"(?:'((?:[^']|'')+)'!)?([A-Z]+)(\d+):[A-Z]+(\d+)", a)
            sayfa = wb[m[1].replace("''", "'")] if m[1] else ws
            out += [formul_degeri(sayfa, f"{m[2]}{r}") for r in range(int(m[3]), int(m[4]) + 1)]
        return out

    def sayi(x) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def n(x):                                               # Excel: boş hücre 0; yazı hata
        if x is None or sayi(x):
            return x or 0
        raise ValueError(f"{ws.title}!{ref}: sayı değil: {x!r}")
    R = r"([A-Z]+\d+)"
    if m := re.fullmatch(rf'IF\(AND\(ISNUMBER\({R}\),ISNUMBER\({R}\)\),ROUND\(\1\*\2,2\),""\)', f):
        a, b = hucre(m[1]), hucre(m[2])
        return round(a * b, 2) if sayi(a) and sayi(b) else ""
    if m := re.fullmatch(r"SUM\((.+)\)", f):
        return round(sum(x for x in degerler(m[1]) if sayi(x)), 2)
    if m := re.fullmatch(rf"ROUND\({R}\*{R},2\)", f):
        return round(n(hucre(m[1])) * n(hucre(m[2])), 2)
    if m := re.fullmatch(rf"ROUND\({R}\*\(1\+{R}\),2\)", f):
        return round(n(hucre(m[1])) * (1 + n(hucre(m[2]))), 2)
    if m := re.fullmatch(rf"{R}([+-]){R}", f):
        a, b = n(hucre(m[1])), n(hucre(m[3]))
        return round(a + b if m[2] == "+" else a - b, 2)
    if m := re.fullmatch(r'(?:"([^"]*)"&\()?(\d+)-COUNT\((.+?)\)\)?', f):
        k = int(m[2]) - sum(1 for x in degerler(m[3]) if sayi(x))
        return f"{m[1]}{k}" if m[1] is not None else k
    if re.fullmatch(r"(?:'(?:[^']|'')+'!)?[A-Z]+\d+", f):
        return hucre(f)
    raise ValueError(f"{ws.title}!{ref}: bilinmeyen formül {v}")


def onbellek_yaz(yol) -> int:
    """Kayıtlı dosyadaki formüllerin sonucunu hücrenin önbellek değerine (<v>) yazar (`formul_degeri` ile). Formül hesaplamayan
    görüntüleyici (telefon, dosya önizlemesi) de sayıyı gösterir; Excel açılışta yine hesaplar (openpyxl'in `fullCalcOnLoad`'u).
    Lokman, 11 Kasım 2026 11:31 UTC (TK-07): "adet * birim fiyat = tutar sütünunu niye girmedin ve KDV". Döner: yazılan hücre sayısı."""
    import posixpath
    import re
    import xml.etree.ElementTree as ET
    import zipfile
    from xml.sax.saxutils import escape

    from openpyxl import load_workbook
    wb = load_workbook(yol)
    with zipfile.ZipFile(yol) as z:
        dosya = [(i, z.read(i.filename)) for i in z.infolist()]
    icerik = {i.filename: b for i, b in dosya}
    ns_r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    rel = {e.get("Id"): e.get("Target") for e in ET.fromstring(icerik["xl/_rels/workbook.xml.rels"])}
    sayfa = {}
    for e in ET.fromstring(icerik["xl/workbook.xml"]).iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
        t = rel[e.get(ns_r)]
        sayfa[t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join("xl", t))] = wb[e.get("name")]
    n = 0

    def yaz(ws, m) -> str:
        nonlocal n
        v = formul_degeri(ws, m["ref"])
        att = re.sub(r'\s+t="[^"]*"', "", m["att"])
        n += 1
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f'<c r="{m["ref"]}"{att}><f>{m["f"]}</f><v>{v!r}</v></c>'
        return f'<c r="{m["ref"]}"{att} t="str"><f>{m["f"]}</f><v>{escape(str(v))}</v></c>'
    for p, ws in sayfa.items():
        x = icerik[p].decode("utf-8")
        icerik[p] = re.sub(r'<c r="(?P<ref>[A-Z]+\d+)"(?P<att>[^>]*)><f>(?P<f>[^<]*)</f><v\s*/></c>', lambda m: yaz(ws, m), x).encode("utf-8")
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        for i, _ in dosya:
            z.writestr(i, icerik[i.filename])
    return n


def _hucre(sutun: int, satir: int) -> str:
    from openpyxl.utils import get_column_letter
    return f"{get_column_letter(sutun)}{satir}"


def liste_sayfasi(ws, R: dict, baslik: str, aciklama: str, renk=None, kaynak_sutunu: bool = False, formullu: bool = False) -> dict:
    """`fiyatla.fiyatla`'nın sonucu (R) bir sayfaya: grup başlık satırı + satırlar + ara toplam; en altta genel toplam ve fiyatı olmayan
    satır sayısı (R'nin özetinden). `renk(satır)` birim fiyat hücresinin dolgusunu (RENK anahtarı) verir. `kaynak_sutunu`: fiyatla.py'nin
    defter görünümü için Durum ve Kaynak sütunları. `formullu`: tutar ve toplamlar formül, en altta kâr marjı (modül notu). Ara toplamların
    toplamı özetin toplamını tutmazsa durur. Döner: toplam hücrelerinin adresi (genel, kdv, dahil; formüllüde kar, kar_tutari, kar_haric,
    kar_kdv, kar_dahil; fiyatsız sayımı için tutar_araliklari ve kalem_sayisi), Özet sayfası bunlara bağlanır."""
    Alignment, Border, Font, dolgu, Side = _stil()
    from openpyxl.utils import get_column_letter
    satirlar, ozet = R["satirlar"], R["ozet"]
    kg = any(s.get("kg") is not None for s in satirlar)
    K = ozet.get("kdv")                                     # D-76: CRM defteriyle KDV sütunları
    sutun = (["Ölçü", "Birim", "Adet"] + (["kg"] if kg else []) + ["Birim fiyat", "Tutar"] + (KDV_SUTUN if K else []) + ["Not"]
             + (["Durum", "Kaynak"] if kaynak_sutunu else []))
    n = 1 + len(sutun)
    i_bf, i_tut, i_not = (sutun.index(x) + 2 for x in ("Birim fiyat", "Tutar", "Not"))    # sayfadaki sütun (1'den; A Kalem)
    ws.append([baslik]); ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"{aciklama} {FORMUL_ACIKLAMA}" if formullu else aciklama]); ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n); ws.row_dimensions[2].height = 48 if formullu else 32
    gruplar: dict[str, list[dict]] = {}                     # grup ilk göründüğü sırada, grup içinde Motor'un sırası
    for s in satirlar:
        gruplar.setdefault(s.get("grup_adi") or str(s.get("grup") or ""), []).append(s)
    H = lambda sutun: _hucre(sutun, ws.max_row + 1)          # noqa: E731 (yazılacak satırın hücresi)
    i_adet, i_kg = 4, (5 if kg else None)
    ara_t, ara_k, araliklar, kalem_sayisi = [], [], [], 0     # formüllü: ara toplam hücreleri, kalem satırı aralıkları
    toplam = 0.0
    for ad, ss in gruplar.items():
        ss = [s for s in ss if s.get("adet") != 0]          # adedi 0 olan satır (pakette yok) yazılmaz (Lokman, 11 Kasım 2026 10:46 UTC)
        if not ss:
            continue
        ws.append([]); ws.append([buyuk(ad), *sutun])
        for c in ws[ws.max_row]:
            c.font = Font(bold=True); c.fill = dolgu["baslik"]
        ara = round(sum(s["tutar"] or 0 for s in ss), 2)
        ilk = ws.max_row + 1
        for s in ss:
            olcu, birim = gorunen(s.get("teklif_olcu") or s.get("olcu"), s.get("birim"))
            neden = eksik(s)
            notu = neden or (fiyat_notu(s) if s["birim_fiyat"] is None else "")
            if K and s["tutar"] and s.get("kdv_orani") is None:
                notu = "; ".join(x for x in (notu, "KDV oranı yok") if x)
            tutar, kdv = s["tutar"], s.get("kdv_tutari")
            if formullu:                                    # adet (kg'lı kalemde kg) × birim fiyat; KDV = tutar × KDV %
                m = H(i_adet) if s.get("birim") != "kg" else (H(i_kg) if i_kg else None)
                bf, t = H(i_bf), H(i_tut)
                tutar = f'=IF(AND(ISNUMBER({m}),ISNUMBER({bf})),ROUND({m}*{bf},2),"")' if m else None
                kdv = f'=IF(AND(ISNUMBER({t}),ISNUMBER({H(i_tut + 1)})),ROUND({t}*{H(i_tut + 1)},2),"")'
            ws.append([s.get("teklif_adi") or s["kalem"], olcu, birim, s.get("adet")] + ([s.get("kg")] if kg else []) + [s["birim_fiyat"], tutar]
                      + ([s.get("kdv_orani"), kdv] if K else []) + [notu]
                      + ([s["durum"], s.get("kaynak_adi") or s.get("kaynak")] if kaynak_sutunu else []))
            r = ws[ws.max_row]
            r[i_bf - 1].number_format = r[i_tut - 1].number_format = TL
            if K:
                r[i_tut].number_format, r[i_tut + 1].number_format = "0%", TL
                if s["tutar"] and s.get("kdv_orani") is None:
                    r[i_tut].fill = r[i_tut + 1].fill = dolgu["sari"]
            k = renk(s) if renk else None
            if neden:
                for c in r: c.fill = dolgu["gri"]
            elif k:
                r[i_bf - 1].fill = dolgu[k]
        toplam += ara
        son = ws.max_row
        araliklar.append((ilk, son)); kalem_sayisi += son - ilk + 1
        ara_kdv = round(sum(s.get("kdv_tutari") or 0 for s in ss), 2)
        if formullu:
            ara, ara_kdv = f"=SUM({_hucre(i_tut, ilk)}:{_hucre(i_tut, son)})", f"=SUM({_hucre(i_tut + 2, ilk)}:{_hucre(i_tut + 2, son)})"
        ara_t.append(H(i_tut)); ara_k.append(H(i_tut + 2))
        ws.append([f"{ad} toplamı"] + [""] * (i_tut - 2) + [ara] + (["", ara_kdv] if K else []))
        r = ws[ws.max_row]; r[0].font = r[i_tut - 1].font = Font(bold=True); r[i_tut - 1].number_format = TL
        if K:
            r[i_tut + 1].font = Font(bold=True); r[i_tut + 1].number_format = TL
        for c in r[:n]: c.border = Border(top=Side(style="thin", color=RENK["cizgi"]))
    if abs(toplam - ozet["toplam"]) > 0.005:
        raise ValueError(f"liste sayfası: ara toplamların toplamı {toplam:.2f}, özetin toplamı {ozet['toplam']:.2f}")
    if formullu and len(ozet["fiyatsiz"]) != kalem_sayisi - sum(1 for s in satirlar if s.get("adet") != 0 and s["tutar"] is not None):
        raise ValueError("liste sayfası: fiyatı olmayan satır sayısı yazılan satırlarla tutmuyor")
    ws.append([None])                                       # boş satır; [None] ws.max_row'u da ilerletir (H'nin adresi doğru kalır)
    adres = {"genel": H(i_tut)}
    genel, fiyatsiz = ozet["toplam"], f"fiyatı olmayan satır: {len(ozet['fiyatsiz'])}"
    if formullu:
        genel = f"=SUM({','.join(ara_t)})"
        adres["tutar_araliklari"] = [f"{_hucre(i_tut, a)}:{_hucre(i_tut, b)}" for a, b in araliklar]
        adres["kalem_sayisi"] = kalem_sayisi
        fiyatsiz = f'="fiyatı olmayan satır: "&({kalem_sayisi}-COUNT({",".join(adres["tutar_araliklari"])}))'
    ws.append([GENEL] + [""] * (i_tut - 2) + [genel] + (["", ""] if K else []) + [fiyatsiz])
    r = ws[ws.max_row]; r[0].font = r[i_tut - 1].font = Font(bold=True, size=12); r[i_tut - 1].number_format = TL
    if K:                                                   # D-76: KDV ve KDV dahil, genel toplamın altında
        from araclar.fiyatla import kdv_yazi
        adres["kdv"], adres["dahil"] = H(i_tut), _hucre(i_tut, ws.max_row + 2)
        kdv, dahil, notu = K["kdv"], K["dahil"], kdv_yazi(K)
        if formullu:
            kdv, dahil, notu = f"=SUM({','.join(ara_k)})", f"={adres['genel']}+{adres['kdv']}", f"satırların KDV'si; üretimde {notu}"
        for ad, x, notu in (("KDV (kalem grubunun oranıyla)", kdv, notu), ("KDV DAHİL TOPLAM", dahil,
                            "eksik: oranı olmayan satırların KDV'si yok" if K["eksik"] else "")):
            ws.append([ad] + [""] * (i_tut - 2) + [x, "", "", notu])
            r = ws[ws.max_row]; r[0].font = r[i_tut - 1].font = Font(bold=True, size=12); r[i_tut - 1].number_format = TL
            if K["eksik"]:
                r[i_tut - 1].fill = dolgu["sari"]
    if formullu:                                            # kâr marjı en sonda; Lokman yazar (11 Kasım 2026 10:55 UTC)
        ws.append([None])
        g, k = adres["genel"], H(i_tut)
        adres["kar"] = k
        satir = [(KAR, 0, "Kâr marjını bu sarı hücreye yazın (ör. %25). Kâr maliyetin üstüne eklenir."),
                 ("Kâr (KDV hariç toplam × kâr marjı)", f"=ROUND({g}*{k},2)", ""),
                 ("TEKLİF TOPLAMI · kâr dahil, KDV hariç", f"={g}+{_hucre(i_tut, ws.max_row + 2)}", "")]
        if K:
            satir += [("KDV · kâr dahil", f"=ROUND({adres['kdv']}*(1+{k}),2)", "KDV aynı oranla büyür"),
                      ("TEKLİF TOPLAMI · kâr dahil, KDV dahil", f"={_hucre(i_tut, ws.max_row + 3)}+{_hucre(i_tut, ws.max_row + 4)}", "")]
        for j, (ad, x, notu) in enumerate(satir):
            adres[("kar", "kar_tutari", "kar_haric", "kar_kdv", "kar_dahil")[j]] = H(i_tut)
            ws.append([ad] + [""] * (i_tut - 2) + [x] + (["", ""] if K else []) + [notu])
            r = ws[ws.max_row]; r[0].font = r[i_tut - 1].font = Font(bold=True, size=12)
            r[i_tut - 1].number_format = "0%" if j == 0 else TL
        ws[adres["kar"]].fill = dolgu["sari"]
        bekle = {"genel": GENEL, "kdv": "KDV (kalem grubunun oranıyla)", "dahil": "KDV DAHİL TOPLAM", "kar": KAR,
                 "kar_dahil": "TEKLİF TOPLAMI · kâr dahil, KDV dahil"}
        for a, ad in bekle.items():                         # formüllerin gösterdiği hücre doğru satırda mı
            if a in adres and ws.cell(ws[adres[a]].row, 1).value != ad:
                raise ValueError(f"liste sayfası: {a} hücresi {adres[a]} '{ad}' satırında değil")
        hesap = {"genel": ozet["toplam"], "kar_haric": ozet["toplam"]} | ({"kdv": K["kdv"], "dahil": K["dahil"], "kar_dahil": K["dahil"]} if K else {})
        for a, x in hesap.items():                          # formüllerin sonucu JSON'un sayısı (kâr %0)
            if abs(formul_degeri(ws, adres[a]) - x) > 0.005:
                raise ValueError(f"liste sayfası: {a} formülü {formul_degeri(ws, adres[a])}, JSON {x}")
    genislik = [62, 20, 9, 8] + ([9] if kg else []) + [13, 14] + ([8, 13] if K else []) + [30] + ([16, 30] if kaynak_sutunu else [])
    for i, w in enumerate(genislik, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=3):
        for c in row:
            if c.column in (3, 4): c.alignment = Alignment(horizontal="center")
            elif c.column >= i_not: c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A3"
    ws.page_setup.orientation = "landscape"; ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    return adres
