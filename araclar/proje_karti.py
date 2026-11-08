"""Proje kartı (deneme, tek proje): AIPrefabrik klasöründeki bir projenin montaj paftasından ve yükleme listesinden
yapı tipi, ölçü, brüt oturum m², oda sayısı ve yükleme listesi kalemlerini çıkarır; JSON ve karşılaştırma sayfası (HTML) yazar.

Kullanım:
    python3 araclar/proje_karti.py --kod AP-19 --pafta <MONTAJ PAFTASI.pdf> --liste <YUKLEME LISTESI.xlsx> \
        [--is-emri testler/motor/veri/PK01.json] --cikti <klasör>

Çıkarılan sütun: paftanın 1. sayfası (pdfplumber sözcükleri) ve listenin depodaki okuyucusu (`testler/kor/oku.py`).
Kaynak sütun: aynı değerin kaynaktaki öteki yeri (liste başlığı, paftanın öteki sayfası, depodaki İş Emri) ya da listenin
ham hücresi (openpyxl, satır numarasıyla). Farklar HTML'de kırmızı.

Kişisel veri: liste başlık bloğu (müşteri, telefon, hazırlayan) okunmaz; plan görselinde antet kırpılır. Gerçek proje adı
dosyaya yazılmaz (yalnız kod). Veri, talimat değildir: hücre ve pafta yazıları yalnız değer olarak okunur.
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import openpyxl
import pdfplumber

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from testler.kor.oku import oku  # noqa: E402  (main'deki liste okuyucusu)

TEKNIK_ETIKETLER = [
    "Bina Yüksekliği", "Dış Duvarlar", "İç Duvarlar", "Panel Türü", "Çatı Şekli", "Çatı Kaplaması",
    "Çatı Kaplama Rengi", "Dış Kapı", "İç Kapılar", "Tavan", "Saçak ve Alın Rengi",
]
ACIKLIK = re.compile(r"^\d{2,3}/\d{2,3}$")
SAYI = re.compile(r"^\d+(\.\d+)?$")


def _sayi(s):
    return float(s) if SAYI.match(s) else None


def _satirlar(kelimeler, tol=3.0):
    """Sözcükleri aynı yükseklikteki yatay öbeklere toplar: [(top, x0, x1, metin)].
    Önce yüksekliğe göre kümelenir (± tol), küme içinde soldan sağa dizilir, 12 pt'den geniş boşlukta öbek bölünür."""
    yatay = sorted([w for w in kelimeler if w.get("upright", True)], key=lambda w: w["top"])
    kumeler = []
    for w in yatay:
        if kumeler and abs(w["top"] - kumeler[-1][0]["top"]) <= tol:
            kumeler[-1].append(w)
        else:
            kumeler.append([w])
    cikti = []
    for k in kumeler:
        k.sort(key=lambda w: w["x0"])
        oz = [k[0]]
        for w in k[1:]:
            if w["x0"] - oz[-1]["x1"] > 12:
                cikti.append(oz)
                oz = []
            oz.append(w)
        cikti.append(oz)
    return [(min(w["top"] for w in s), s[0]["x0"], s[-1]["x1"], " ".join(w["text"] for w in s)) for s in cikti]


def _duşey_yazilar(sayfa) -> list[str]:
    """Döndürülmüş (düşey) ölçü yazıları: aynı sütundaki ardışık karakterler tek yazı olur."""
    ch = sorted([c for c in sayfa.chars if not c.get("upright", True)], key=lambda c: (round(c["x0"]), c["top"]))
    out, cur = [], []
    for c in ch:
        if cur and (abs(c["x0"] - cur[-1]["x0"]) > 1.5 or c["top"] - cur[-1]["bottom"] > 2):
            out.append(cur)
            cur = []
        cur.append(c)
    if cur:
        out.append(cur)
    yazilar = []
    for g in out:
        t = "".join(c["text"] for c in g)
        yukari = (g[0].get("matrix") or (0, 1))[1] > 0  # aşağıdan yukarı okunan yazı
        yazilar.append(t[::-1] if yukari else t)
    return yazilar


def _egim(sayfa):
    """Çatı kesitindeki eğim yazısı ("18.2°"): ° karakteriyle aynı doğrultudaki (aynı matris dönüşü) yakın karakterler."""
    der = [c for c in sayfa.chars if c["text"] == "°"]
    if not der:
        return None
    d = der[0]
    m = d.get("matrix")
    yakin = [c for c in sayfa.chars if c is not d and c.get("matrix") and m and
             all(abs(c["matrix"][i] - m[i]) < 1e-3 for i in range(4)) and
             abs(c["x0"] - d["x0"]) < 12 and abs(c["top"] - d["top"]) < 30 and re.match(r"[\d.]", c["text"])]
    # yazı yönünde sırala: matrisin x bileşeni (a, b) yönünde izdüşüm
    yon = (m[0], m[1]) if m else (1, 0)
    yakin.sort(key=lambda c: c["matrix"][4] * yon[0] + c["matrix"][5] * yon[1])
    t = "".join(c["text"] for c in yakin)
    return float(t) if SAYI.match(t) else None


def pafta_oku(yol: Path) -> dict:
    with pdfplumber.open(yol) as pdf:
        s1 = pdf.pages[0]
        kel = s1.extract_words(keep_blank_chars=False, use_text_flow=False, extra_attrs=["upright"])
        satirlar = _satirlar(kel)
        metin_tum = " ".join(t for *_, t in satirlar)

        # Teknik özellikler tablosu (sol sütun): etiket ve aynı satırdaki değer
        teknik = {}
        for top, x0, x1, t in satirlar:
            for e in sorted(TEKNIK_ETIKETLER, key=len, reverse=True):
                if t.startswith(e):
                    deger = t[len(e):].strip()
                    if not deger:  # değer ayrı sözcük öbeğinde
                        yan = [u for (tp, a, b, u) in satirlar if abs(tp - top) < 4 and a > x1 and a < x1 + 120]
                        deger = yan[0] if yan else ""
                    teknik.setdefault(e, deger)
                    break
        # "Sandviç Panel" yazısı tabloda iki satır arasında kayık durur
        if not teknik.get("Çatı Kaplaması"):
            m = re.search(r"(Sandviç Panel|Trapez[^0-9]*|Metal Kiremit)", metin_tum)
            teknik["Çatı Kaplaması"] = m.group(1).strip() if m else ""

        # Mahaller: "<ad>" satırının hemen altındaki "<n> m2" satırı
        mahaller = []
        tablo_sag = max((x1 for (_, x0, x1, t) in satirlar if t.startswith("TEKNİK")), default=0)
        for top, x0, x1, t in satirlar:
            m = re.fullmatch(r"(\d+(?:\.\d+)?) m2", t)
            if not m:
                continue
            ust = [(tp, a, u) for (tp, a, b, u) in satirlar
                   if 0 < top - tp < 16 and abs(a - x0) < 25 and a > tablo_sag and not re.search(r"\d", u)]
            ad = max(ust)[2] if ust else "?"
            mahaller.append({"ad": ad, "net_m2": float(m.group(1))})

        # Dış ölçü: en sık yinelenen yatay ve düşey ölçü yazısı (≥ 300 cm)
        yatay = Counter(_sayi(w["text"]) for w in kel if w.get("upright", True) and _sayi(w["text"]) and _sayi(w["text"]) >= 300)
        duşey = Counter(v for v in (_sayi(t) for t in _duşey_yazilar(s1)) if v and v >= 300)
        genislik = yatay.most_common(1)[0][0] if yatay else None
        derinlik = duşey.most_common(1)[0][0] if duşey else None

        # Açıklıklar: plan üstündeki "120/120" gibi yazılar
        acikliklar = Counter([w["text"] for w in kel if w.get("upright", True) and ACIKLIK.match(w["text"])]
                             + [t for t in _duşey_yazilar(s1) if ACIKLIK.match(t)])

        # Çatı kesiti: eğim (°) ve mahya yüksekliği (eğimin solundaki düşey sayı)
        egim = _egim(s1)

        sayfa_metin = [p.extract_text() or "" for p in pdf.pages]

    # Öteki sayfalar (kaynak sütunu için)
    makas = sorted({m for t in sayfa_metin for m in re.findall(r"\bMK\d{2}\b", t)})
    betopan = None
    for t in sayfa_metin:
        if "BETOPAN YERLEŞİMİ" in t.upper():
            m = re.search(r"ADET:\s*(\d+)", t)
            if m:
                betopan = int(m.group(1))
    acik_s3 = Counter(re.findall(r"\b(\d{2,3}/\d{2,3})\b", sayfa_metin[2])) if len(sayfa_metin) > 2 else Counter()

    return {
        "teknik": teknik, "mahaller": mahaller, "genislik_cm": genislik, "derinlik_cm": derinlik,
        "acikliklar": dict(acikliklar), "egim_derece": egim, "makas_etiketleri": makas,
        "bas_makas_betopani": betopan, "acikliklar_sayfa3": dict(acik_s3),
        "baslik_tek_kat": bool(re.search(r"PREFABRİK KONUT", metin_tum)),
    }


def _katla(s) -> str:
    return re.sub(r"\s+", " ", str(s if s is not None else "")).strip()


def liste_ham(yol: Path) -> tuple[dict, list[dict]]:
    """Listenin ham hücreleri (kaynak sütunu): başlıktaki m²/kat/yükseklik ve malzeme satırları (satır no ile).
    Başlık bloğundan yalnız 'BİNA M2 / KAT ADEDİ / KAT YÜKSEKLİĞİ' satırı alınır; ad ve telefon satırları okunmaz."""
    wb = openpyxl.load_workbook(yol, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    bas, satirlar, grup, basladi = {}, [], None, False
    for i, r in enumerate(ws.iter_rows(max_row=2000, max_col=8, values_only=True), 1):
        a, b, c = (r + (None,) * 3)[:3]
        g = r[6] if len(r) > 6 else None
        if isinstance(a, str) and a.upper().startswith("BİNA M2"):
            bas = {"satir": i, "m2": b, "kat": c, "yukseklik_m": r[3]}
            continue
        if _katla(b).upper() == "BOYUT" and _katla(c).upper() == "ADET":
            grup, basladi = _katla(a), True
            continue
        if not basladi or a in (None, ""):
            continue
        satirlar.append({"satir": i, "grup": grup, "malzeme": _katla(a), "boyut": _katla(b), "adet": c,
                         "kesin_hesap": g})
    return bas, satirlar


def kart_cikar(kod: str, pafta: Path, liste_yolu: Path, is_emri: Path | None) -> dict:
    p = pafta_oku(pafta)
    okunan = oku(liste_yolu, liste_yolu.suffix.lower())
    bas, ham = liste_ham(liste_yolu)
    ie = json.loads(is_emri.read_text(encoding="utf-8")) if is_emri else None

    W, D = p["genislik_cm"], p["derinlik_cm"]
    brut = round(W * D / 10000, 2) if W and D else None
    yatak = sum(1 for m in p["mahaller"] if "yatak" in m["ad"].lower())
    salon = sum(1 for m in p["mahaller"] if "salon" in m["ad"].lower())
    t = p["teknik"]
    yuk_mm = int(re.search(r"\d+", t.get("Bina Yüksekliği", "")).group()) if re.search(r"\d+", t.get("Bina Yüksekliği", "")) else None

    def ham_ara(desen, boyut=None):
        for r in ham:
            if re.search(desen, r["malzeme"], re.I) and (boyut is None or boyut in r["boyut"]):
                return r
        return None

    def ham_deger(desen, boyut=None):
        r = ham_ara(desen, boyut)
        return (r["adet"], f"liste satır {r['satir']}") if r else (None, "listede yok")

    ie_yatak = sum(1 for m in (ie or {}).get("mahaller", []) if m.get("tur") == "yatak_odasi")
    ie_salon = sum(1 for m in (ie or {}).get("mahaller", []) if m.get("tur") == "salon")
    ie_olcu = ((ie or {}).get("yapi", {}).get("dis_olcu_cm") or {})
    ie_kal = ((ie or {}).get("yapi", {}).get("duvar_kalinligi_cm") or {})

    def k(alan, cik, cik_yer, kay, kay_yer, birim=""):
        esit = (cik == kay) if not isinstance(cik, (int, float)) or not isinstance(kay, (int, float)) \
            else abs(float(cik) - float(kay)) < 1e-6
        return {"alan": alan, "cikarilan": cik, "cikarilan_yer": cik_yer, "kaynak": kay, "kaynak_yer": kay_yer,
                "birim": birim, "ayni": bool(esit)}

    acik = p["acikliklar"]
    yapi = [
        k("Yapı tipi", "Tek kat prefabrik" if p["baslik_tek_kat"] else "?", "pafta s.1 antet",
          "Tek kat prefabrik" if bas.get("kat") == 1 else f"kat {bas.get('kat')}", f"liste satır {bas.get('satir')} (kat adedi)"),
        k("Panel türü", t.get("Panel Türü"), "pafta s.1 teknik tablo", "Pres Panel" if ham_ara(r"YAPIŞTIRMA DOLU PANO") else None,
          "liste: yapıştırma dolu pano satırları"),
        k("Dış ölçü (genişlik × derinlik)", f"{W:g} × {D:g}", "pafta s.1 genel ölçü",
          f"{ie_olcu.get('x', 0):g} × {ie_olcu.get('y', 0):g}" if ie_olcu else None, "depo: PK-01 İş Emri", "cm"),
        k("Brüt oturum (veranda dahil)", brut, "pafta s.1: genişlik × derinlik", bas.get("m2"), f"liste satır {bas.get('satir')}", "m²"),
        k("Duvar yüksekliği", yuk_mm, "pafta s.1 teknik tablo",
          round(bas["yukseklik_m"] * 1000) if bas.get("yukseklik_m") else None, f"liste satır {bas.get('satir')}", "mm"),
        k("Dış duvar kalınlığı", int(re.search(r"\d+", t.get("Dış Duvarlar", "0")).group()), "pafta s.1 teknik tablo",
          ie_kal.get("dis", 0) * 10 if ie_kal else None, "depo: PK-01 İş Emri", "mm"),
        k("İç duvar kalınlığı", int(re.search(r"\d+", t.get("İç Duvarlar", "0")).group()), "pafta s.1 teknik tablo",
          ie_kal.get("ic", 0) * 10 if ie_kal else None, "depo: PK-01 İş Emri", "mm"),
        k("Oda sayısı (yatak + salon)", f"{yatak}+{salon}", "pafta s.1 mahal yazıları",
          f"{ie_yatak}+{ie_salon}" if ie else None, "depo: PK-01 İş Emri"),
        k("Çatı şekli", t.get("Çatı Şekli"), "pafta s.1 teknik tablo", {"besik": "Beşik", "kirma": "Kırma"}.get((ie or {}).get("cati", {}).get("tip"), (ie or {}).get("cati", {}).get("tip")),
          "depo: PK-01 İş Emri"),
        k("Çatı kaplaması", t.get("Çatı Kaplaması"), "pafta s.1 teknik tablo",
          "Sandviç Panel" if ham_ara(r"SANDVİÇ PANEL \(") else "?", "liste: çatı kaplamaları grubu"),
        k("Makas adedi", len(p["makas_etiketleri"]), "pafta s.7 MK etiketleri", *ham_deger(r"^MAKAS$")),
        k("Baş makas betopanı", p["bas_makas_betopani"], "pafta s.5", *ham_deger(r"BAŞ MAKAS BETOPANI")),
        k("Pencere 120/120", acik.get("120/120", 0), "pafta s.1 plan yazıları", *ham_deger(r"PENCERE ALT PANEL \(120/120\)")),
        k("Pencere 120/180", acik.get("120/180", 0), "pafta s.1 plan yazıları", *ham_deger(r"PENCERE ALT PANEL \(120/180\)")),
        k("Vasistas 60/40", acik.get("60/40", 0), "pafta s.1 plan yazıları", *ham_deger(r"VASİSTASLI PANO \(60/40\)")),
        k("Pencere üst paneli (120'lik pencereler)", acik.get("120/120", 0) + acik.get("120/180", 0), "pafta s.1: 120/120 + 120/180",
          *ham_deger(r"PENCERE ÜST PANEL")),
        k("Dış kapı panosu", 1 if "Dış Kapı" in t else 0, "pafta s.1 teknik tablo", *ham_deger(r"KARKASLI ÇELİK KAPI PANOSU")),
    ]
    a_sag, _ = ham_deger(r"AMERİKAN KAPI.*\(SAĞ\)")
    a_sol, _ = ham_deger(r"AMERİKAN KAPI.*\(SOL\)")
    ie_kapi = sum(1 for a in (ie or {}).get("acikliklar", []) if a.get("tur") == "ic_kapi")
    yapi.append(k("İç kapı (Amerikan)", (a_sag or 0) + (a_sol or 0), "liste: sağ + sol", ie_kapi if ie else None,
                  "depo: PK-01 İş Emri (iç kapılar)"))

    # Liste: okuyucunun satırları ↔ ham hücreler (sırayla)
    liste = []
    hi = 0
    for o in okunan:
        while hi < len(ham) and _katla(ham[hi]["malzeme"]).upper() != _katla(o["malzeme"]).upper():
            liste.append({"durum": "okuyucuda yok", **{f"k_{x}": ham[hi][x] for x in ("satir", "grup", "malzeme", "boyut", "adet")}})
            hi += 1
        h = ham[hi] if hi < len(ham) else None
        hi += 1
        fark = [] if h else ["kaynakta yok"]
        if h:
            if _katla(o["boyut"]) != h["boyut"]:
                fark.append("boyut")
            if o["adet"] != h["adet"]:
                fark.append("adet")
            if (o["grup"] or "") != (h["grup"] or ""):
                fark.append("grup")
        ic = None
        if h and isinstance(h.get("kesin_hesap"), (int, float)) and isinstance(h["adet"], (int, float)) \
                and round(h["kesin_hesap"]) != h["adet"]:
            ic = h["kesin_hesap"]
        liste.append({"durum": "aynı" if not fark else "fark: " + ", ".join(fark),
                      "grup": o["grup"], "malzeme": o["malzeme"], "boyut": o["boyut"], "adet": o["adet"],
                      "k_satir": h and h["satir"], "k_boyut": h and h["boyut"], "k_adet": h and h["adet"],
                      "kesin_hesap_farkli": ic})
    while hi < len(ham):
        liste.append({"durum": "okuyucuda yok", **{f"k_{x}": ham[hi][x] for x in ("satir", "grup", "malzeme", "boyut", "adet")}})
        hi += 1

    kart_liste = [{"grup": r["grup"], "kalem": r["malzeme"], "boyut": r["boyut"], "adet": r["adet"]}
                  for r in liste if r.get("malzeme") and r.get("adet") not in (0,)]
    sifir = sum(1 for r in liste if r.get("adet") == 0)
    kart = {
        "kod": kod,
        "surum": 1,
        "kaynak_dosyalar": {"pafta": liste_ad(pafta),
                            "liste": liste_ad(liste_yolu)},
        "yapi_tipi": yapi[0]["cikarilan"],
        "panel_turu": t.get("Panel Türü"),
        "dis_olcu_cm": {"genislik": W, "derinlik": D},
        "brut_oturum_m2": brut,
        "duvar_yuksekligi_mm": yuk_mm,
        "duvar_kalinligi_mm": {"dis": yapi[5]["cikarilan"], "ic": yapi[6]["cikarilan"]},
        "oda_sayisi": f"{yatak}+{salon}",
        "mahaller": p["mahaller"],
        "net_alan_toplami_m2": round(sum(m["net_m2"] for m in p["mahaller"]), 2),
        "cati": {"sekil": t.get("Çatı Şekli"), "kaplama": t.get("Çatı Kaplaması"), "renk": t.get("Çatı Kaplama Rengi"),
                 "egim_derece": p["egim_derece"], "makas_adedi": len(p["makas_etiketleri"])},
        "acikliklar": p["acikliklar"],
        "tavan": t.get("Tavan"),
        "alici_ait": [x for x in ("Dış Kapı",) if "Alıcıya" in t.get(x, "")],
        "yukleme_listesi": {"kalem_sayisi": len(kart_liste), "adedi_0_satir": sifir, "kalemler": kart_liste},
    }
    return {"kart": kart, "yapi_kiyas": yapi, "liste_kiyas": liste}


def liste_ad(p: Path) -> str:
    return re.sub(r"^\S+", "<ad>", p.name)


def plan_gorseli(pafta: Path) -> str:
    """Paftanın 1. sayfasından kat planı (antet ve teknik tablo kırpılır) → base64 PNG."""
    with pdfplumber.open(pafta) as pdf:
        s = pdf.pages[0]
        w, h = s.width, s.height
        kutu = (w * 0.24, h * 0.07, w * 0.74, h * 0.94) if w > h else (w * 0.07, h * 0.24, w * 0.94, h * 0.74)
        img = s.crop(kutu).to_image(resolution=200).original
    b = io.BytesIO()
    img.save(b, format="PNG", optimize=True)
    return base64.b64encode(b.getvalue()).decode()


def _h(x):
    if x is None:
        return "<span class='bos'>—</span>"
    if isinstance(x, float):
        x = f"{x:g}".replace(".", ",")
    return html.escape(str(x))


def html_yaz(sonuc: dict, gorsel_b64: str, yol: Path, kod: str):
    kart, yk, lk = sonuc["kart"], sonuc["yapi_kiyas"], sonuc["liste_kiyas"]
    yfark = sum(1 for r in yk if not r["ayni"])
    lfark = sum(1 for r in lk if r["durum"] != "aynı")
    ic = [r for r in lk if r.get("kesin_hesap_farkli") is not None]
    satir_y = "".join(
        f"<tr class='{'' if r['ayni'] else 'fark'}'><td>{_h(r['alan'])}</td><td class='d'>{_h(r['cikarilan'])} {_h(r['birim']) if r['cikarilan'] is not None else ''}</td>"
        f"<td class='yer'>{_h(r['cikarilan_yer'])}</td><td class='d'>{_h(r['kaynak'])} {_h(r['birim']) if r['kaynak'] is not None else ''}</td>"
        f"<td class='yer'>{_h(r['kaynak_yer'])}</td><td>{'aynı' if r['ayni'] else 'FARK'}</td></tr>" for r in yk)
    satir_l, grup = [], None
    for r in lk:
        g = r.get("grup") or r.get("k_grup")
        if g != grup:
            satir_l.append(f"<tr class='grup'><td colspan='7'>{_h(g)}</td></tr>")
            grup = g
        cls = "fark" if r["durum"] != "aynı" else ("sifir" if r.get("adet") == 0 else "")
        not_ = f"kesin hesap sütunu {_h(round(r['kesin_hesap_farkli'], 2))}" if r.get("kesin_hesap_farkli") is not None else ""
        satir_l.append(
            f"<tr class='{cls}'><td>{_h(r.get('malzeme') or r.get('k_malzeme'))}</td><td>{_h(r.get('boyut'))}</td><td class='d'>{_h(r.get('adet'))}</td>"
            f"<td class='yer'>{_h(r.get('k_satir'))}</td><td>{_h(r.get('k_boyut'))}</td><td class='d'>{_h(r.get('k_adet'))}</td>"
            f"<td class='yer'>{'aynı' if r['durum'] == 'aynı' else _h(r['durum'])}{(' · ' + not_) if not_ else ''}</td></tr>")
    mah = "".join(f"<li>{_h(m['ad'])}: {_h(m['net_m2'])} m²</li>" for m in kart["mahaller"])
    sayfa = f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Proje kartı {html.escape(kod)}</title>
<style>
:root{{--bg:#fff;--fg:#1d1d1f;--ince:#6b6b70;--cizgi:#ddd;--kirmizi:#c62828;--kirmizi-bg:#fdecea;--grup:#f3f3f5;--sari:#8a6d00}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#17171a;--fg:#ececf0;--ince:#a0a0a8;--cizgi:#333;--kirmizi:#ff6b6b;--kirmizi-bg:#3a1d1d;--grup:#222226;--sari:#e0c060}}}}
:root[data-theme="dark"]{{--bg:#17171a;--fg:#ececf0;--ince:#a0a0a8;--cizgi:#333;--kirmizi:#ff6b6b;--kirmizi-bg:#3a1d1d;--grup:#222226;--sari:#e0c060}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:16px;max-width:1200px;margin:auto}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:16px;margin:24px 0 8px}}
.ust{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr);gap:20px}} @media(max-width:800px){{.ust{{grid-template-columns:1fr}}}}
img{{width:100%;height:auto;border:1px solid var(--cizgi);background:#fff}}
.tw{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid var(--cizgi);padding:4px 6px;text-align:left;vertical-align:top}} th{{font-weight:600}}
td.d{{text-align:right;white-space:nowrap}} .yer{{color:var(--ince);font-size:12px}}
tr.fark td{{color:var(--kirmizi);background:var(--kirmizi-bg);font-weight:600}} tr.grup td{{background:var(--grup);font-weight:600}}
tr.sifir td{{color:var(--ince)}} .bos{{color:var(--ince)}} .ozet{{color:var(--ince)}} ul{{margin:4px 0;padding-left:18px}}
</style></head><body>
<h1>Proje kartı · {html.escape(kod)} · deneme (tek proje)</h1>
<div class="ozet">Kırmızı satır: çıkarılan değer kaynaktakinden farklı. Yapı tablosunda {yfark} fark, liste tablosunda {lfark} fark.
Çıkarılan sütun: montaj paftası 1. sayfa ve listenin depodaki okuyucusu. Kaynak sütun: aynı değerin öteki kaynaktaki yeri.</div>
<div class="ust"><div><h2>Kat planı (montaj paftası, sayfa 1)</h2><img alt="Kat planı" src="data:image/png;base64,{gorsel_b64}">
<h2>Mahaller (paftadaki net alanlar)</h2><ul>{mah}</ul><div class="ozet">Net alan toplamı {_h(kart['net_alan_toplami_m2'])} m² (veranda dahil).</div></div>
<div><h2>Yapı değerleri</h2><div class="tw"><table><tr><th>Alan</th><th>Çıkarılan</th><th>Nereden</th><th>Kaynak</th><th>Nereden</th><th></th></tr>{satir_y}</table></div></div></div>
<h2>Yükleme listesi ({kart['yukleme_listesi']['kalem_sayisi']} kalem karta girdi; adedi 0 olan {kart['yukleme_listesi']['adedi_0_satir']} satır girmedi, gri)</h2>
<div class="ozet">Kaynak: listenin ADET sütunu. Not sütunu: listenin "kesin hesap" sütunu ADET'ten farklıysa yazılır ({len(ic)} satır); karta ADET girer.</div>
<div class="tw"><table><tr><th>Kalem</th><th>Boyut</th><th>Adet (çıkarılan)</th><th>Liste satırı</th><th>Boyut (kaynak)</th><th>Adet (kaynak)</th><th>Durum · not</th></tr>{''.join(satir_l)}</table></div>
</body></html>"""
    yol.write_text(sayfa, encoding="utf-8")


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--kod", required=True)
    a.add_argument("--pafta", type=Path, required=True)
    a.add_argument("--liste", type=Path, required=True)
    a.add_argument("--is-emri", type=Path)
    a.add_argument("--cikti", type=Path, required=True)
    o = a.parse_args(argv)
    sonuc = kart_cikar(o.kod, o.pafta, o.liste, o.is_emri)
    o.cikti.mkdir(parents=True, exist_ok=True)
    (o.cikti / "kart.json").write_text(json.dumps(sonuc["kart"], ensure_ascii=False, indent=1), encoding="utf-8")
    (o.cikti / "kiyas.json").write_text(json.dumps({k: v for k, v in sonuc.items() if k != "kart"}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    html_yaz(sonuc, plan_gorseli(o.pafta), o.cikti / "karsilastirma.html", o.kod)
    yf = sum(1 for r in sonuc["yapi_kiyas"] if not r["ayni"])
    lf = sum(1 for r in sonuc["liste_kiyas"] if r["durum"] != "aynı")
    print(f"{o.kod}: yapı {len(sonuc['yapi_kiyas'])} alan, {yf} fark · liste {len(sonuc['liste_kiyas'])} satır, {lf} fark")


if __name__ == "__main__":
    main()
