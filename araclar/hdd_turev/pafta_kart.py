"""Arşiv DWG'sindeki montaj planından proje kartı taslağı (İE-43 sonrası, havuz yolu adım 1).

  python3 pafta_kart.py <DXF ya da DXF.gz> [--json <çıktı>]

Okuma (LLM yok; ezdxf):
1. Montaj planı: "MONTAJ VE ELEKTRİK PLANI" yazısı. Bir dosyada birçok pafta ve birçok proje olabilir; her montaj yazısı ayrı
   plan. Sayfa: yazıyı içine alan kapalı çerçeve (İkranur 2016–2018 şablonu); çerçeve yoksa yazıdan başlayıp birbirine
   `BOSLUK_CM`'den yakın öğelerin bölgesi (2019–2020 şablonu; yazı ile başlık arasındaki bantta).
   Plan kutusu: çerçeveli sayfada çerçevedeki uzun ölçülerin kapsamı (+ `PAY_CM`; teknik tablo ve antet dışarıda);
   çerçevesizde alt yazının ortasından geçen en uzun
   yatay ölçü ve onun hizasındaki en uzun dikey ölçü (+ `PAY_CM`): bölge komşu çizime taşsa da plan kutusu taşmaz.
2. Başlık: "<ad> <sayı> M2" ya da "<sayı> m² PREFABRİK BİNA" → başlık m²'si. Ad karta yazılmaz (kişisel veri; ad yalnız
   Mac'teki eşlemede). Teknik bilgiler tablosu ("Dış Duvarlar:", "Çatı Şekli:" …) varsa değerleriyle. Birçok projenin
   bir arada çizildiği dosyada planın hangi projeye ait olduğu başlıktaki ya da antetteki adla bulunur
   (`--klasor-adi`, `--dosya-adi`: yalnız eşleşir/eşleşmez yazılır).
3. Dış ölçü: plan kutusundaki en uzun yatay ve dikey ölçü (DIMENSION'ın ölçtüğü değer).
4. Mahaller: "<ad> <sayı> m²" yazıları (ör. "Y.ODASI 9.14 m²"); oda programı yatak odası sayısından.
5. Açıklıklar: "120/120 ÇİFT AÇILIM", "60/40", "120/100 SÜRGÜ", "P.40x170", "ÇELİK" gibi yazılar ("100*100" dikme
   ölçüsüdür, açıklık değil; 30 cm'den küçük "17/3" açıklık değil). Kapı: plandaki kapı yayları (yarıçap 55–110 cm,
   80–100°; çoklu çizgide tek yay 60–100°; blok içindekiler dahil).
6. Pano blokları: adında "PANO" geçen eklemeler; konum blok tanımının kendi kutusundan (taban noktası çoğu blokta
   uzakta durur, ekleme noktası panonun yeri değildir).
Kart düzeltilmez: paftada ne yazıyorsa o (Lokman, 15 Kasım; asıl proje olduğu gibi kalır).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import io
import json
import math
import re
import sys

BOSLUK_CM = 150.0
EN_BUYUK_OGE_CM = 4000.0
PAY_CM = 250.0                      # plan kutusunun genel ölçünün dışındaki payı (kubbe, ölçü ve açıklık yazıları)
CERCEVE_CM = (600.0, 6000.0)        # sayfa çerçevesinin kenar sınırları
MONTAJ = re.compile(r"MONTAJ\s*(VE|&)?\s*ELEKTR", re.I)
TASLAK = re.compile(r"TASLAK\s+PLAN", re.I)
ALT_YAZI = re.compile(MONTAJ.pattern + "|" + TASLAK.pattern, re.I)
ANTET = re.compile(r"\d{2,3}(?:[.,]\d{1,2})?\s*M\s*[²2]\s*PREFABR", re.I)       # "74 m² PREFABRİK KONUT"
M2_YAZI = re.compile(r"^\s*(\d{1,3}(?:[.,]\d{1,2})?)\s*m\s*(?:²|2|\\U\+00B2)\s*$", re.I)   # oda yazısının m² satırı
OLCU_YAZI = re.compile(r"^\s*(\d{2,4}[.,]\d{2})\s*$")    # patlatılmış ölçünün yazısı ("1014.00")
PAY_YAZI_CM = 120.0                 # ölçü yazılarından kurulan plan kutusunun payı
BASLIK_M2 = re.compile(r"(\d{2,3}(?:[.,]\d{1,2})?)\s*M\s*(?:2|²)(?![0-9])", re.I)
MAHAL = re.compile(r"^(?P<ad>.+?)\s*(?:\\P|\n|\s)\s*(?P<m2>\d{1,3}[.,]\d{1,2})\s*m\s*(?:²|2|\\U\+00B2)", re.I | re.S)
OLCU = re.compile(r"(?<![\d*])(\d{2,3})\s*[/xX]\s*(\d{2,3})(?![\d.*])")
TEKNIK = ["Bina Yüksekliği", "Dış Duvarlar", "İç Duvarlar", "Panel Türü", "Çatı Şekli", "Çatı Kaplaması",
          "Çatı Kaplama Rengi", "Dış Kapı", "İç Kapılar", "Tavan", "Saçak ve Alın Rengi"]
KAPI_YARICAP = (55.0, 110.0)
KAPI_ACI = (80.0, 100.0)
KAPI_ACI_CIZGI = (60.0, 100.0)      # çoklu çizgideki kapı yayı (İkranur bloklarında 75°)


def _sade(t: str) -> str:
    """MTEXT biçim kodlarını atar: {\\fArial|b0;...}, \\P → satır sonu."""
    t = re.sub(r"\\S([^;^/#]*)[\^/#]([^;]*);", r"\1/\2", t)   # yığılmış kesir: \S120^180; → 120/180
    t = re.sub(r"\\[A-Za-z][^;\\{}]*;", "", t)
    t = t.replace("\\P", "\n").replace("{", "").replace("}", "")
    t = re.sub(r"\\[A-Za-z]", "", t)
    return t.replace("%%c", "Ø").replace("%%d", "°").strip()


def _ust(t: str) -> str:
    return t.replace("i", "İ").replace("ı", "I").upper()


def _sayi(t: str) -> float:
    return float(t.strip().replace(",", "."))


ACIKLIK_SOZU = re.compile(r"ÇELİK|CELIK|SÜRGÜ|SURGU|AÇILIM|ACILIM|^P[. ]")


def yukle(yol: str):
    """DXF'i okur; ikili veri satırlarını (310, 1004) atar (bozuk proxy/OLE verisi ezdxf'i durdurur), katmanları açar."""
    from ezdxf import recover
    ac = gzip.open if yol.endswith(".gz") else open
    cikti = io.BytesIO()
    with ac(yol, "rb") as g:
        while True:
            k = g.readline()
            if not k:
                break
            v = g.readline()
            if k.strip() in (b"310", b"1004"):
                continue
            cikti.write(k)
            cikti.write(v)
    cikti.seek(0)
    d, _ = recover.read(cikti)
    for l in d.layers:
        l.on()
        l.thaw()
    return d


def _kutu(e):
    from ezdxf import bbox
    if e.dxftype() == "DIMENSION":
        # ölçünün kutusu tanım noktalarından (ölçü bloğunun kutusu ezdxf sürümüne göre değişir, bazen bloksuzdur)
        nok = [e.dxf.get(a) for a in ("defpoint", "defpoint2", "defpoint3", "text_midpoint")]
        nok = [n for n in nok if n is not None]
        if nok:
            return (min(n[0] for n in nok), min(n[1] for n in nok), max(n[0] for n in nok), max(n[1] for n in nok))
    try:
        b = bbox.extents([e], fast=True)
    except Exception:
        return None
    if not b.has_data:
        return None
    return (b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)


def oge_kutulari(msp) -> list:
    """(öğe, kutu) çiftleri; kutusu olmayan öğe atlanır."""
    L = []
    for e in msp:
        k = _kutu(e)
        if k is None:
            continue
        L.append((e, k))
    return L


def bolge(kutular: list, cekirdek: tuple, bosluk: float = BOSLUK_CM) -> tuple:
    """Çekirdek kutudan başlayıp `bosluk`tan yakın öğeleri ekleyerek bölgeyi büyütür (ızgara). Çok büyük öğeler
    (çerçeve, yardımcı çizgi) köprü olmasın diye atlanır. Bölgenin kutusu ve öğe sırası."""
    hucre = 500.0
    izgara = collections.defaultdict(list)
    for i, (_, k) in enumerate(kutular):
        if k[2] - k[0] > EN_BUYUK_OGE_CM or k[3] - k[1] > EN_BUYUK_OGE_CM:
            continue
        for gx in range(int(k[0] // hucre), int(k[2] // hucre) + 1):
            for gy in range(int(k[1] // hucre), int(k[3] // hucre) + 1):
                izgara[(gx, gy)].append(i)
    secili, kuyruk = set(), [cekirdek]
    B = list(cekirdek)
    while kuyruk:
        k = kuyruk.pop()
        x0, y0, x1, y1 = k[0] - bosluk, k[1] - bosluk, k[2] + bosluk, k[3] + bosluk
        for gx in range(int(x0 // hucre), int(x1 // hucre) + 1):
            for gy in range(int(y0 // hucre), int(y1 // hucre) + 1):
                for i in izgara.get((gx, gy), ()):
                    if i in secili:
                        continue
                    a = kutular[i][1]
                    if a[2] >= x0 and a[0] <= x1 and a[3] >= y0 and a[1] <= y1:
                        secili.add(i)
                        kuyruk.append(a)
                        B = [min(B[0], a[0]), min(B[1], a[1]), max(B[2], a[2]), max(B[3], a[3])]
    return tuple(B), sorted(secili)


def _metin(e) -> str:
    if e.dxftype() == "MTEXT":
        return _sade(e.text)
    if e.dxftype() == "TEXT":
        return _sade(e.dxf.text)
    return ""


def pano_turu(ad: str) -> dict:
    a = _ust(ad)
    m = re.match(r"\s*(\d{2,3})", a)
    kalinlik = int(m.group(1)) if m else None
    if "KAPI" in a:
        acik = "kapi"
    elif "VASİSTAS" in a or "VASISTAS" in a:
        acik = "vasistas"
    elif "PENCERE" in a or "PEN." in a:
        acik = "pencere"
    elif "DOLU" in a:
        acik = "dolu"
    else:
        acik = "diger"
    return {"kalinlik_mm": kalinlik, "acik": acik}


GENEL_SOZ = {"BEY", "HANIM", "ABI", "USTA", "LOKMAN", "PREFABRIK", "PREF", "IKRANUR", "PLANI", "PLAN", "TASLAK", "REVIZE",
             "GENEL", "SABLON", "PAFTA", "PAFTALAR", "MONTAJ", "ELEKTRIK", "DUZELTME", "PROJE", "PROJESI", "BINA", "KONUT",
             "ICIN", "YENI", "ESKI", "SON", "TEK", "KAT", "CIFT", "CIFTKAT"}
_KATLA = str.maketrans("ÇĞİÖŞÜÂÎÛ", "CGIOSUAIU")


def _soz_listesi(t: str) -> list:
    import unicodedata
    t = _ust(unicodedata.normalize("NFC", t)).translate(_KATLA)
    return [w for w in re.sub(r"[^A-Z ]", " ", t).split() if len(w) >= 3 and w not in GENEL_SOZ]


def _sozler(t: str) -> set:
    return set(_soz_listesi(t))


def ad_eslesir(metinler: list, ad: str) -> bool:
    """Planın başlığı ya da antetindeki ad, projenin adıyla aynı kişi mi. Ad karta yazılmaz; yalnız sonuç.
    1. Ortak ad sözcüğü: adda iki ya da daha çok sözcük varsa en az iki, tek sözcükse bir.
    2. Başlıkta yalnız ilk ad ("ENSAR BEY" ↔ "Ensar Aksoy"): başlığın ad sözcükleri adın içinde ve ilk ad aralarında
       (yalnız soyadı yetmez: "ÇELİK EV" ↔ "Ahmet Çelik" eşleşmez).
    3. Bitişik yazılmış ad ("FARUKCAN" ↔ "Faruk Can")."""
    F = _soz_listesi(ad)
    if not F:
        return False
    Fs = set(F)
    bitisik = {a + b for a, b in zip(F, F[1:])}
    T = set()
    for m in metinler or ():
        Tm = _sozler(m)
        if Tm and Tm <= Fs and F[0] in Tm:
            return True
        if Tm & bitisik:
            return True
        T |= Tm
    return len(Fs & T) >= min(2, len(Fs))


def _icinde(k, B, tol=1.0) -> bool:
    return k[0] >= B[0] - tol and k[1] >= B[1] - tol and k[2] <= B[2] + tol and k[3] <= B[3] + tol


def _baslik_mi(s: str) -> float | None:
    """Başlık m²'si: "<ad> 72 M2", "66 m² PREFABRİK BİNA" ya da antetin "74 m² PREFABRİK KONUT" satırı; mahal yazısı
    ("Y.ODASI\\n9.14 m²") değil."""
    if ALT_YAZI.search(_ust(s)):
        return None
    if "\n" in s:                   # antet: "<ad>\n74 m² PREFABRİK KONUT"
        for satir in s.split("\n"):
            m = BASLIK_M2.search(satir) if "PREFABR" in _ust(satir) else None
            if m:
                return float(m.group(1).replace(",", "."))
        return None
    if MAHAL.match(s):
        return None
    m = BASLIK_M2.search(s)
    if not m:
        return None
    if "m²" in s and "PREFABR" not in _ust(s):
        return None
    return float(m.group(1).replace(",", "."))


def cerceve_bul(kutular: list, cekirdek: tuple, antetler: tuple = ()):
    """Alt yazıyı taşıyan en küçük kapalı çerçeve (kenarları `CERCEVE_CM` içinde): yazı çerçevenin sol alt köşesinde
    (İkranur 2016–2018) ya da alt dörtte birinde ve çerçevenin alt kısmında "<n> m² PREFABRİK …" anteti var (İkranur A4)."""
    en = None
    for e, k in kutular:
        if e.dxftype() not in ("LWPOLYLINE", "POLYLINE"):
            continue
        try:
            kapali = e.closed if e.dxftype() == "LWPOLYLINE" else e.is_closed
        except Exception:
            kapali = False
        w, h = k[2] - k[0], k[3] - k[1]
        if not kapali or not (CERCEVE_CM[0] <= w <= CERCEVE_CM[1] and CERCEVE_CM[0] <= h <= CERCEVE_CM[1]):
            continue
        if not _icinde(cekirdek, k):
            continue
        if cekirdek[0] - k[0] > 150 or cekirdek[1] - k[1] > 150:   # alt yazı sol alt köşede değil (İkranur 2016–2018)
            if cekirdek[1] - k[1] > 0.25 * h or not any(k[0] <= (a[0] + a[2]) / 2 <= k[2] and 0 <= (a[1] + a[3]) / 2 - k[1] < 0.3 * h
                                                        for a in antetler):
                continue
        if en is None or w * h < (en[2] - en[0]) * (en[3] - en[1]):
            en = k
    return en


def _baslik_ust(kutular: list, cekirdek: tuple):
    """Alt yazının üstündeki en yakın başlık yazısının kutusu (2019–2020 şablonunda planın üst sınırı)."""
    cx = (cekirdek[0] + cekirdek[2]) / 2
    en = None
    for e, k in kutular:
        if e.dxftype() not in ("TEXT", "MTEXT"):
            continue
        if _baslik_mi(_metin(e)) is None:
            continue
        if k[1] > cekirdek[3] and k[1] - cekirdek[3] < 4000 and abs((k[0] + k[2]) / 2 - cx) < 1500:
            if en is None or k[1] < en[1]:
                en = k
    return en


def _olcu(e):
    """DIMENSION → {deger, yon, a, b}: a–b ölçülen aralık (yatayda x, dikeyde y), defpoint2/3'ten."""
    p1, p2 = e.dxf.get("defpoint2"), e.dxf.get("defpoint3")
    tip = e.dxf.get("dimtype", 0) & 7
    if tip in (0, 1) and p1 is not None and p2 is not None:
        # doğrusal (0) ve hizalı (1) ölçü tanım noktalarından (ezdxf 1.4.4 hizalı dikey ölçüye 0 döndürür)
        if tip == 1:
            deger = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        else:
            a = math.radians(e.dxf.get("angle", 0.0))
            deger = abs((p2[0] - p1[0]) * math.cos(a) + (p2[1] - p1[1]) * math.sin(a))
    else:
        try:
            deger = e.get_measurement()
        except Exception:
            return None
    if not isinstance(deger, (int, float)):
        return None
    yon, a, b = None, None, None
    if p1 is not None and p2 is not None:
        dx, dy = abs(p1[0] - p2[0]), abs(p1[1] - p2[1])
        if abs(deger - dx) < 0.6 and dx >= dy * 0.2:
            yon, a, b = "yatay", min(p1[0], p2[0]), max(p1[0], p2[0])
        elif abs(deger - dy) < 0.6:
            yon, a, b = "dikey", min(p1[1], p2[1]), max(p1[1], p2[1])
        else:
            yon = "egik"
        konum = (p1[1] + p2[1]) / 2 if yon == "yatay" else (p1[0] + p2[0]) / 2
    else:
        konum = None
    return {"deger": round(float(deger), 2), "yon": yon, "a": a, "b": b, "konum": konum}


def plan_kutusu(olculer: list, cekirdek: tuple, sinir: tuple):
    """Alt yazının ortasından geçen en uzun yatay ölçü ile onun hizasındaki en uzun dikey ölçünün kutusu (+ PAY_CM)."""
    cx = (cekirdek[0] + cekirdek[2]) / 2
    yat = [o for o in olculer if o["yon"] == "yatay" and o["deger"] >= 300 and o["a"] - 100 <= cx <= o["b"] + 100]
    if not yat:
        return None
    y = max(yat, key=lambda o: o["deger"])
    dik = [o for o in olculer if o["yon"] == "dikey" and o["deger"] >= 300 and y["a"] - PAY_CM <= o["konum"] <= y["b"] + PAY_CM]
    if not dik:
        return None
    d = max(dik, key=lambda o: o["deger"])
    B = (y["a"] - PAY_CM, d["a"] - PAY_CM, y["b"] + PAY_CM, d["b"] + PAY_CM)
    return (max(B[0], sinir[0]), max(B[1], sinir[1]), min(B[2], sinir[2]), min(B[3], sinir[3]))


def _yaylar(e, derinlik: int = 0):
    """Öğedeki kapı yayları (ARC; blok içindekiler bir kat derinliğe kadar)."""
    t = e.dxftype()
    if t == "ARC":
        r = e.dxf.radius
        aci = (e.dxf.end_angle - e.dxf.start_angle) % 360
        if KAPI_YARICAP[0] <= r <= KAPI_YARICAP[1] and KAPI_ACI[0] <= aci <= KAPI_ACI[1]:
            c = e.dxf.center
            yield (round(c[0], 0), round(c[1], 0), round(r, 0))
    elif t == "LWPOLYLINE":
        # İkranur kapı bloğu: tek yaylı çoklu çizgi (kapı kanadı + yay); dört yaylı daire (armatür) kapı değil
        from ezdxf.math import bulge_to_arc
        nok = list(e.get_points("xyb"))
        if e.closed and nok:
            nok.append(nok[0])
        yayli = [(a, b) for a, b in zip(nok, nok[1:]) if abs(a[2]) > 0.1]
        if len(yayli) == 1:
            a, b = yayli[0]
            c, sa, ea, r = bulge_to_arc((a[0], a[1]), (b[0], b[1]), a[2])
            aci = math.degrees((ea - sa) % (2 * math.pi))
            if KAPI_YARICAP[0] <= r <= KAPI_YARICAP[1] and KAPI_ACI_CIZGI[0] <= aci <= KAPI_ACI_CIZGI[1]:
                yield (round(c[0], 0), round(c[1], 0), round(r, 0))
    elif t == "INSERT" and derinlik < 2:
        try:
            for v in e.virtual_entities():
                yield from _yaylar(v, derinlik + 1)
        except Exception:
            return


SACAK_FARKI_CM = 50.0   # 2020 montaj paftası: saçağın ölçüsü gövdeninkinden 2 × 25 cm büyük (makas planı gövde + 50; listede saçak sacı 250)


def _sacak_ayir(degerler: list) -> tuple[list, float | None]:
    """Bir yöndeki ölçüler (büyükten küçüğe) → (gövde ölçüsüyle başlayan liste, saçak ölçüsü ya da None). En büyük ölçü ikinci ölçüden
    tam 50 cm (± 0,5) büyükse saçağın ölçüsüdür, gövde ölçüsü ikincisidir (İE-43 PR-4: 63 m² 823 ↔ 773, 58 m² 650 ↔ 600; gözlem, kural
    değil). Taşan veranda ölçüsü (67 m² 940,25 ↔ 700,25) bu farkla karışmaz."""
    if len(degerler) >= 2 and abs(degerler[0] - degerler[1] - SACAK_FARKI_CM) <= 0.5:
        return degerler[1:], degerler[0]
    return degerler, None


def teknik_oku(yazilar: list, degerler: list | None = None) -> dict:
    """"Dış Duvarlar:" gibi etiketin aynı satırında sağdaki ilk yazı; sağda yoksa hemen altındaki yazı (teknik tablo). `degerler`
    verilirse değer olarak alınan yazılar oraya eklenir (plan okuması onları açıklık yazısı saymaz: "Dış Kapı: Çelik Kapı")."""
    T = {}
    etiket = {_ust(et): et for et in TEKNIK}
    for y in yazilar:
        et = etiket.get(_ust(y["t"].strip().rstrip(":").strip()))
        if not et:
            continue
        # yazının kutusu hızlı ölçümde geniş çıkar: değer etiketin içine taşabilir; satır kayıklığı en çok 16 cm
        yan = [z for z in yazilar if abs(z["y"] - y["y"]) < 16 and y["x0"] + 30 < z["x0"] < y["x1"] + 260
               and z.get("aci", 0) == 0 and not OLCU_YAZI.match(z["t"])
               and _ust(z["t"].strip().rstrip(":").strip()) not in etiket and not z["t"].strip().endswith(":")]
        if yan:
            z = min(yan, key=lambda z: (abs(z["y"] - y["y"]), z["x0"]))
            if et not in T and degerler is not None:
                degerler.append(z)
            T.setdefault(et, z["t"].strip())
            continue
        # İkranur A4: değer etiketin altındaki satırda, aynı sol hizada
        alt = [z for z in yazilar if abs(z["x0"] - y["x0"]) < 20 and 0 < y["y"] - z["y"] <= 80
               and _ust(z["t"].strip().rstrip(":").strip()) not in etiket and z["t"].strip()]
        if alt:
            z = min(alt, key=lambda z: y["y"] - z["y"])
            if et not in T and degerler is not None:
                degerler.append(z)
            T.setdefault(et, z["t"].strip())
    return T


def plan_oku(d, kutular: list, cekirdek_i: int, antetler: tuple = ()) -> dict:
    cekirdek = kutular[cekirdek_i][1]
    cerceve = cerceve_bul(kutular, cekirdek, antetler)
    if cerceve:
        # yazının hızlı kutusu geniş çıkar (antet çerçeveden taşar): yazı için ortası çerçevede yeter
        sec = [i for i, (e, k) in enumerate(kutular) if _icinde(k, cerceve)
               or (e.dxftype() in ("TEXT", "MTEXT") and _icinde(((k[0] + k[2]) / 2, (k[1] + k[3]) / 2) * 2, cerceve))]
        B = cerceve
        sinir = cerceve
    else:
        ust = _baslik_ust(kutular, cekirdek)
        alt_y, ust_y = cekirdek[1] - 20, (ust[3] + 20 if ust else cekirdek[3] + 4000)
        bant = [(e, k) if (k[1] >= alt_y and k[3] <= ust_y) else (e, (1e12, 1e12, 1e12, 1e12)) for e, k in kutular]
        (B, sec) = bolge(bant, cekirdek)
        sinir = B
    sayfa_yazilari, olculer = [], []
    for i in sec:
        e, k = kutular[i]
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            s = _metin(e)
            if s:
                try:
                    aci = round(float(e.dxf.get("rotation", 0.0) or 0.0)) % 360
                except Exception:
                    aci = 0
                sayfa_yazilari.append({"t": s, "x": (k[0] + k[2]) / 2, "y": (k[1] + k[3]) / 2, "x0": k[0], "x1": k[2],
                                       "h": k[3] - k[1], "aci": aci})
        elif t == "DIMENSION":
            o = _olcu(e)
            if o:
                olculer.append({**o, "kutu": k})
    baslik = None
    for y in sorted(sayfa_yazilari, key=lambda y: -y["y"]):
        baslik = _baslik_mi(y["t"])
        if baslik is not None:
            break
    teknik_degerleri: list = []
    teknik = teknik_oku(sayfa_yazilari, teknik_degerleri)
    ad_metinleri = [y["t"] for y in sayfa_yazilari if _baslik_mi(y["t"]) is not None or "PREF" in _ust(y["t"])]
    if cerceve:
        uzun = [o for o in olculer if o["yon"] in ("yatay", "dikey") and o["deger"] >= 300]
        yx = [o for o in uzun if o["yon"] == "yatay"]
        dy = [o for o in uzun if o["yon"] == "dikey"]
        P = None
        if yx and dy:   # sayfada yalnız plan var; ölçülerin kapsamı teknik tabloyu ve anteti dışarıda bırakır
            P = (max(min(o["a"] for o in yx) - PAY_CM, sinir[0]), max(min(o["a"] for o in dy) - PAY_CM, sinir[1]),
                 min(max(o["b"] for o in yx) + PAY_CM, sinir[2]), min(max(o["b"] for o in dy) + PAY_CM, sinir[3]))
    else:
        P = plan_kutusu(olculer, cekirdek, sinir)
    kutu_kaynagi = "olcu"
    olcu_yazilari = [y for y in sayfa_yazilari if OLCU_YAZI.match(y["t"]) and y["aci"] in (0, 90, 270)]
    if P is None:
        # ölçüler patlatılmış (çizgi + yazı): plan kutusu ölçü yazılarının kapsamından
        Y = [y for y in olcu_yazilari if _icinde((y["x"], y["y"], y["x"], y["y"]), sinir)]
        uzun_y = [y for y in Y if y["aci"] == 0 and _sayi(y["t"]) >= 300]
        uzun_d = [y for y in Y if y["aci"] in (90, 270) and _sayi(y["t"]) >= 300]
        if uzun_y and uzun_d:
            P = (max(min(y["x0"] for y in Y) - PAY_YAZI_CM, sinir[0]), max(min(y["y"] for y in Y) - PAY_YAZI_CM, sinir[1]),
                 min(max(y["x1"] for y in Y) + PAY_YAZI_CM, sinir[2]), min(max(y["y"] for y in Y) + PAY_YAZI_CM, sinir[3]))
            kutu_kaynagi = "olcu_yazisi"
    if P is None:
        P, kutu_kaynagi = sinir, ("cerceve" if cerceve else "bolge")
    plan_sec = [i for i in sec if _icinde(kutular[i][1], P, tol=0)
                or (P[0] <= (kutular[i][1][0] + kutular[i][1][2]) / 2 <= P[2]
                    and P[1] <= (kutular[i][1][1] + kutular[i][1][3]) / 2 <= P[3])]
    yazilar = [y for y in sayfa_yazilari if P[0] <= y["x"] <= P[2] and P[1] <= y["y"] <= P[3]]
    olculer = [o for o in olculer if _icinde(o["kutu"], P, tol=50)]
    panolar, yaylar = [], set()
    for i in plan_sec:
        e, k = kutular[i]
        if e.dxftype() == "INSERT" and "PANO" in _ust(e.dxf.name):
            panolar.append({"blok": e.dxf.name, "kutu": [round(v, 2) for v in k], **pano_turu(e.dxf.name)})
        elif e.dxftype() in ("ARC", "INSERT", "LWPOLYLINE"):
            yaylar.update(_yaylar(e))
    mahaller = []
    for y in yazilar:
        m = MAHAL.match(y["t"])
        if m:
            ad = re.sub(r"\s+", " ", m.group("ad")).strip(" :")
            mahaller.append({"ad": _ust(ad), "m2": float(m.group("m2").replace(",", ".")),
                             "x": round(y["x"] - P[0], 1), "y": round(y["y"] - P[1], 1)})
    for y in yazilar:
        m = M2_YAZI.match(y["t"])           # oda adı ve m²'si ayrı yazı: ad hemen üstte, aynı hizada
        if not m:
            continue
        ad = [z for z in yazilar if z is not y and 0 < z["y"] - y["y"] <= 2.5 * max(y["h"], 1) + 10
              and abs(z["x"] - y["x"]) <= 80 and not any(c.isdigit() for c in z["t"]) and len(z["t"]) <= 30
              and re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]{2}", z["t"]) and not ACIKLIK_SOZU.search(_ust(z["t"]))]
        if ad:
            z = min(ad, key=lambda z: (z["y"] - y["y"], abs(z["x"] - y["x"])))
            mahaller.append({"ad": _ust(re.sub(r"\s+", " ", z["t"]).strip(" :")), "m2": _sayi(m.group(1)),
                             "x": round(y["x"] - P[0], 1), "y": round(z["y"] - P[1], 1)})
    aciklik = []
    for y in yazilar:
        u = _ust(y["t"])
        if MAHAL.match(y["t"]) or ALT_YAZI.search(u) or _baslik_mi(y["t"]) is not None:
            continue
        if any(y is z for z in teknik_degerleri):      # teknik tablonun değeri ("Dış Kapı: Çelik Kapı") planın kapısı değil
            continue
        olcu = OLCU.search(u.replace(" ", ""))
        if olcu and min(int(olcu.group(1)), int(olcu.group(2))) < 30:
            olcu = None                     # "17/3", "8/9": açıklık değil (en küçük açıklık 40 cm)
        tur = None
        if "ÇELİK" in u or "CELIK" in u:
            tur = "celik_kapi"
        elif "SÜRGÜ" in u or "SURGU" in u:
            tur = "surgulu"
        elif "AÇILIM" in u or "ACILIM" in u:
            tur = "cift_acilim" if "ÇİFT" in u or "CIFT" in u else "acilim"
        elif u.startswith("P.") or u.startswith("P "):
            tur = "pencere"
        elif olcu:
            tur = "olcu"
        if tur:
            aciklik.append({"tur": tur, "olcu": [int(olcu.group(1)), int(olcu.group(2))] if olcu else None,
                            "metin": u[:40] if not any(c.isdigit() for c in u) or olcu else None,
                            "x": round(y["x"] - P[0], 1), "y": round(y["y"] - P[1], 1)})
    yat = sorted((o["deger"] for o in olculer if o["yon"] == "yatay"), reverse=True)
    dik = sorted((o["deger"] for o in olculer if o["yon"] == "dikey"), reverse=True)
    yat_k = dik_k = "olcu"            # ölçü yoksa o yöndeki en uzun ölçü yazısı (patlatılmış ölçü)
    Y = [y for y in olcu_yazilari if P[0] <= y["x"] <= P[2] and P[1] <= y["y"] <= P[3]]
    if not yat:
        yat, yat_k = sorted((_sayi(y["t"]) for y in Y if y["aci"] == 0), reverse=True), "yazi"
    if not dik:
        dik, dik_k = sorted((_sayi(y["t"]) for y in Y if y["aci"] in (90, 270)), reverse=True), "yazi"
    (yat, sacak_yat), (dik, sacak_dik) = _sacak_ayir(yat), _sacak_ayir(dik)
    olcu_kaynagi = (yat_k if yat_k == dik_k else "karma") if (yat or dik) else None
    return {"sablon": "cerceveli" if cerceve else "bantli",
            "alt_yazi": "taslak" if TASLAK.search(_ust(_metin(kutular[cekirdek_i][0]))) else "montaj",
            "kutu_cm": [round(P[2] - P[0], 1), round(P[3] - P[1], 1)],
            "kutu_kaynagi": kutu_kaynagi,
            "kutu_dunya": [round(v, 1) for v in P],
            "baslik_m2": baslik,
            "teknik": teknik,
            "dis_olcu_cm": [yat[0] if yat else None, dik[0] if dik else None],
            "sacak_olcusu_cm": [sacak_yat, sacak_dik],
            "olcu_kaynagi": olcu_kaynagi,
            "mahaller": sorted(mahaller, key=lambda m: (-m["y"], m["x"])),
            "acikliklar": aciklik,
            "kapi_yayi": len(yaylar),
            "pano_bloklari": dict(sorted(collections.Counter(f"{p['kalinlik_mm']}_{p['acik']}" for p in panolar).items())),
            "pano_sayisi": len(panolar),
            "olcu_sayisi": len(olculer),
            "_ad_metinleri": ad_metinleri}


def kart_ozeti(p: dict) -> dict:
    """Plan okumasından proje kartı alanları (`testler/havuz/proje_kartlari.json` biçiminde; yalnız paftada yazanlar)."""
    yatak = sum(1 for m in p["mahaller"] if re.search(r"Y\.?\s*ODA|YATAK", m["ad"]))
    salon = sum(1 for m in p["mahaller"] if "SALON" in m["ad"])
    veranda = sum(1 for m in p["mahaller"] if "VERANDA" in m["ad"] or "TERAS" in m["ad"])
    olcu = collections.Counter(f"{a['olcu'][0]}/{a['olcu'][1]}" for a in p["acikliklar"]
                               if a["olcu"] and a["tur"] in ("olcu", "acilim", "cift_acilim", "surgulu"))
    kubbe = collections.Counter(f"{a['olcu'][0]}/{a['olcu'][1]}" for a in p["acikliklar"] if a["olcu"] and a["tur"] == "pencere")
    dis_kapi = sum(1 for a in p["acikliklar"] if a["tur"] == "celik_kapi")
    ayrik = dis_kapi > 0          # 2020 şablonunda dış kapının "Çelik" yazısı yok: dış ve iç ayrılamaz, yalnız toplam (kapı yayı)
    W, H = p["dis_olcu_cm"]
    return {"dis_olcu_cm": [W, H],
            "baslik_m2": p["baslik_m2"],
            "kutu_m2": round(W * H / 10000, 2) if W and H else None,
            "net_m2": round(sum(m["m2"] for m in p["mahaller"]), 2) if p["mahaller"] else None,
            "oda_sayisi": f"{yatak}+{salon}" if p["mahaller"] else None,
            "yatak_odasi": yatak if p["mahaller"] else None,
            "acikliklar": dict(sorted(olcu.items())),
            "kubbe_pencereleri": dict(sorted(kubbe.items())),
            "dis_kapi_adedi": dis_kapi if ayrik else None,
            "ic_kapi_adedi": (max(p["kapi_yayi"] - dis_kapi, 0) if p["kapi_yayi"] else None) if ayrik else None,
            "kapi_adedi": p["kapi_yayi"] or None,
            "veranda_adedi": veranda if p["mahaller"] else None,
            "cati_sekli": p["teknik"].get("Çatı Şekli"),
            "dis_duvar": p["teknik"].get("Dış Duvarlar"),
            "ic_duvar": p["teknik"].get("İç Duvarlar")}


def _dolu(p: dict) -> int:
    return sum([bool(p["dis_olcu_cm"][0]), bool(p["dis_olcu_cm"][1]), len(p["mahaller"]), len(p["acikliklar"]),
                bool(p["baslik_m2"]), p["kapi_yayi"] > 0])


def oku(yol: str, adlar: dict | None = None, ek_adlar: list[dict] = ()) -> list[dict]:
    """Dosyadaki her montaj planı; aynı plan birden çok kez çizildiyse (aynı başlık m²'si, aynı mahaller) en dolu okuma
    asıl, ötekiler `kopya`. `adlar` ({"klasor": …, "dosya": …}) verilirse her plana `<anahtar>_eslesir` yazılır (ad yazılmaz).
    Aynı dosya başka proje klasörlerinde de duruyorsa `ek_adlar` o klasörlerin adlarıdır; sonuç sırasıyla `ek_eslesme`'de."""
    d = yukle(yol)
    kutular = oge_kutulari(d.modelspace())
    yazi = {i: _metin(e) for i, (e, k) in enumerate(kutular) if e.dxftype() in ("TEXT", "MTEXT")}
    antetler = tuple(kutular[i][1] for i, t in yazi.items() if ANTET.search(_ust(t)))
    planlar = []
    for i, t in yazi.items():
        if ALT_YAZI.search(_ust(t)):
            p = plan_oku(d, kutular, i, antetler)
            k = kutular[i][1]
            p["konum"] = [round(k[0], 0), round(k[1], 0)]
            planlar.append(p)
    gruplar = collections.defaultdict(list)
    for j, p in enumerate(planlar):
        # aynı plan: aynı alt yazı türü, başlık yazıları, başlık m²'si ve mahaller (başlığı başka olan plan kopya değil)
        imza = (p["alt_yazi"], p["baslik_m2"], tuple(sorted(set(p["_ad_metinleri"]))),
                tuple((m["ad"], m["m2"]) for m in sorted(p["mahaller"], key=lambda m: (m["ad"], m["m2"]))))
        gruplar[imza].append(j)
    for js in gruplar.values():
        asil = max(js, key=lambda j: (planlar[j]["kutu_kaynagi"] == "olcu", _dolu(planlar[j]), -j))
        for j in js:
            planlar[j]["kopya"] = j != asil
            planlar[j]["kopya_sayisi"] = len(js) - 1
    for p in planlar:
        p["kart"] = kart_ozeti(p)
        metinler = p.pop("_ad_metinleri")
        for anahtar, ad in (adlar or {}).items():
            if ad:
                p[f"{anahtar}_eslesir"] = ad_eslesir(metinler, ad)
        if ek_adlar:
            p["ek_eslesme"] = [{f"{anahtar}_eslesir": ad_eslesir(metinler, ad) for anahtar, ad in ek.items() if ad}
                               for ek in ek_adlar]
    return planlar


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dxf")
    ap.add_argument("--json")
    ap.add_argument("--klasor-adi", action="append", default=[],
                    help="projenin klasör adı (yalnız eşleşme için; çıktıya yazılmaz); aynı dosya başka klasörlerde de "
                         "duruyorsa her biri için bir kez daha, sırası `ek_eslesme`'nin sırası")
    ap.add_argument("--dosya-adi", action="append", default=[],
                    help="çizim dosyasının adı (yalnız eşleşme için; çıktıya yazılmaz); klasörlerle aynı sırada")
    a = ap.parse_args(argv)
    adlar = [{"klasor": k, "dosya": a.dosya_adi[i] if i < len(a.dosya_adi) else None}
             for i, k in enumerate(a.klasor_adi)] or [{"klasor": None, "dosya": a.dosya_adi[0] if a.dosya_adi else None}]
    P = oku(a.dxf, adlar[0], adlar[1:])
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(P, f, ensure_ascii=False, indent=1)
    for p in P:
        print(("KOPYA " if p["kopya"] else "") + json.dumps(p["kart"], ensure_ascii=False))
        print("  mahaller:", [(m["ad"], m["m2"]) for m in p["mahaller"]], "| şablon", p["sablon"], "| kutu", p["kutu_cm"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
