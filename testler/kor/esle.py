"""Kör test aracının eşlemesi (BK-12 PR-3, M7): gerçek satır ↔ bizim satır ve otomatik sonuç.

Eşleme iki katmanlıdır:
1. **Sözlük** (`sozluk.json`): aynı kalemin iki listede farklı yazıldığı ya da farklı bölündüğü kalem grupları. Her grup bizim kalem
   adlarına ve gerçek malzeme adlarına uyan desenlerle tanımlanır (desenler düzgünleştirilmiş ada uygulanır; ilk uyan grup alır).
   Sözlük kalem adı taşır, gerçek listelerin adedini ya da ölçüsünü taşımaz.
2. **Aynı ad:** sözlüğe girmeyen satırlar düzgünleştirilmiş adları aynıysa bir gruptur.

Grup içinde satırlar anahtarlarla eşlenir (sözlükte `olcu`):
- `tam` (aynı ad gruplarının varsayılanı): anahtar düzgünleştirilmiş ölçüdür; yazısı farklı ama sayıları aynı olan ölçüler de eşlenir
  ("1200*1200" ↔ "1200 × 1200", "120*120" ↔ "120/120", "90*200" ↔ "900 × 2000"). `anahtar: en_buyuk` ise anahtar ölçünün en büyük
  sayısıdır (profil boyları: "100*100*3240" ↔ "L 3240"); `tolerans` (mm) içindeki anahtarlar da eşlenir (yuvarlama). `sira: true`
  ise eşi kalmayan anahtarlar iki yanda aynı sayıdaysa büyükten küçüğe eşlenir ve ölçüsü tutmadığı için "farklı" sayılır. Aynı ad
  grubunda iki yanda birer anahtar kalmışsa ikisi eşlenir: birinin ölçüsü boyut değilse ("ADET", "METRE", "16 Amper") adet
  kıyaslanır, ikisi de boyutsa ölçü tutmadığı için "farklı" sayılır (ör. mahya L 1000 ↔ L 800).
- `yok`: grubun bütün satırları tek anahtardır (toplam kıyaslanır; ör. H'ların kulaklı / dübelli / özel bölünmesi).
- `her_satir`: bizim satırlarımız gerçek listenin her satırıyla ayrı ayrı kıyaslanır (ör. vitrifiye takımı: dört satır, her biri 1).

Bir anahtarda gerçek toplam G ise sonuç (13 Ekim raporlarının tanımı):
- **aynı:** bizim varsayılan adet toplamı G, iki yanda birer satır (varsayılan adetle aynı);
- **ayrım:** varsayılan toplam G, satır sayıları farklı (toplam aynı, ayrım farklı);
- **pafta:** varsayılan tutmaz, pafta sütunu (boşsa varsayılan) toplamı G;
- **aday:** varsayılan ve pafta tutmaz, aday sütunu (sayı değilse varsayılan) toplamı G;
- **farklı:** adet ya da (sıra eşlemesinde) ölçü tutmaz;
- **bizde yok:** gerçek satırın grubu ya da ölçüsü bizde yok;
- **bizde fazla:** bizim satırın (adet > 0) gerçek listede eşi yok. Gerçek satır sayısına girmez.
Doğru = aynı + ayrım + pafta + aday. Gerçek listenin adedi boş ya da 0 olan satırı kıyasa girmez.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

SONUCLAR = ("aynı", "ayrım", "pafta", "aday", "farklı", "bizde yok")
DOGRU = ("aynı", "ayrım", "pafta", "aday")
ADLAR = {"aynı": "varsayılan adetle aynı", "ayrım": "toplam aynı, ayrım farklı", "pafta": "pafta sütunu tuttu",
         "aday": "aday sütunu tuttu", "farklı": "adet ya da ölçü farklı", "bizde yok": "bizde yok", "bizde fazla": "bizde fazla"}
KIPLER = ("tam", "yok", "her_satir")


def ust(t) -> str:
    return unicodedata.normalize("NFC", str(t if t is not None else "")).replace("i", "İ").replace("ı", "I").upper()


def ad(t) -> str:
    t = ust(t).replace("’", "'").replace("´", "'").replace("`", "'")
    t = re.sub(r"^\s*(\([^)]*\)\s*)+", "", t)          # baştaki renk / tür parantezi: "(BORDO)", "( ASMA / TERS )"
    t = re.sub(r"\s*'\s*", "", t).replace("&", " VE ").replace("×", "X")   # "100'LÜK" → "100LÜK", "H' I" → "HI"
    t = re.sub(r"\bU SU\b", "USU", t)                  # "ÇEKTİRME U SU" → "ÇEKTİRME USU"
    t = re.sub(r"(\d)\.(\d)", r"\1,\2", t)            # "3.9 X 32" → "3,9 X 32"
    t = re.sub(r"(\d)\s+(L[UÜIİ]K?|MM|CM)\b", r"\1\2", t)   # "230 LUK", "3 LÜ H", "20 MM"
    t = re.sub(r"\s*([()+/,:\-·])\s*", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def olcu(t) -> str:
    t = ust(t).replace("×", "X").replace("*", "X").replace(":", "")
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"MM$", "", t)
    return re.sub(r"^L(?=\d)", "", t)                  # "L 2800" ↔ "2800"


def sayilar(t) -> tuple:
    return tuple(float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", str(t or "")))


def ayni_sayilar(a, b) -> bool:
    """İki ölçünün sayıları aynı mı; birim farkı (cm ↔ mm) da aynı sayılır."""
    x, y = sayilar(a), sayilar(b)
    if not x or len(x) != len(y):
        return False
    return any(all(abs(p * k - q) < 1e-6 for p, q in zip(x, y)) for k in (1, 10, 0.1))


def boyutlu(t) -> bool:
    """Ölçü bir boyut mu (100 ve üstü bir sayı), yoksa birim yazısı mı ("ADET", "16 Amper", "Kova (17,5 KG)")."""
    return any(x >= 100 for x in sayilar(t))


def sayi_mi(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def esit(a, b) -> bool:
    return abs(float(a) - float(b)) < 1e-6


def sozluk_oku(yol: Path) -> list[dict]:
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    gruplar = []
    for g in d["gruplar"]:
        kip = g.get("olcu", "yok")
        if kip not in KIPLER:
            raise ValueError(f"sözlük grubu {g.get('ad')!r}: bilinmeyen olcu {kip!r}")
        gruplar.append({**g, "olcu": kip, "_b": [re.compile(p) for p in g.get("bizim", [])],
                        "_g": [re.compile(p) for p in g.get("gercek", [])]})
    return gruplar


def _grup_bul(gruplar, adi: str, yan: str):
    for i, g in enumerate(gruplar):
        if any(p.search(adi) for p in g[yan]):
            return i
    return None


def _karar(G: float, bizim: list[dict], n_g: int) -> str:
    n_b = len(bizim)
    if any(sayi_mi(b["adet"]) for b in bizim) and esit(sum(b["adet"] for b in bizim if sayi_mi(b["adet"])), G):
        return "aynı" if n_g == 1 and n_b == 1 else "ayrım"
    if any(sayi_mi(b.get("pafta")) for b in bizim):
        p = sum(b["pafta"] if sayi_mi(b.get("pafta")) else (b["adet"] if sayi_mi(b["adet"]) else 0) for b in bizim)
        if esit(p, G):
            return "pafta"
    if any(sayi_mi(b.get("aday")) for b in bizim):
        a = sum(b["aday"] if sayi_mi(b.get("aday")) else (b["adet"] if sayi_mi(b["adet"]) else 0) for b in bizim)
        if esit(a, G):
            return "aday"
    return "farklı"


def _en_buyuk(t):
    s = sayilar(t)
    return max(s) if s else None


def olcu_anahtari(t, grup: dict | None):
    """Bizim ya da gerçek satırın grup içindeki ölçü anahtarı (`tam` kipinde)."""
    return _en_buyuk(t) if grup and grup.get("anahtar") == "en_buyuk" else olcu(t)


def grup_anahtari(adi: str, gruplar: list[dict], yan: str = "_b"):
    """Satırın grubu: ("s", sözlük sırası) ya da ("a", düzgünleştirilmiş ad)."""
    n = ad(adi)
    k = _grup_bul(gruplar, n, yan)
    return ("s", k) if k is not None else ("a", n)


def _anahtarla(g_satir: dict, b_satir: dict, grup: dict | None):
    """Grup içinde anahtarlar: [(gerçek satır indisleri, bizim satır indisleri, ölçü tuttu mu)], eşsiz gerçek, eşsiz bizim."""
    kip = grup["olcu"] if grup else "tam"
    if kip == "yok":
        if g_satir and b_satir:
            return [(list(g_satir), list(b_satir), True, None)], [], []
        return [], list(g_satir), list(b_satir)
    if kip == "her_satir":
        if b_satir:
            return [([i], list(b_satir), True, None) for i in g_satir], [], ([] if g_satir else list(b_satir))
        return [], list(g_satir), []
    en_buyuk = bool(grup and grup.get("anahtar") == "en_buyuk")
    tolerans = float(grup.get("tolerans", 0)) if grup else 0.0

    def anahtar(t):
        return olcu_anahtari(t, grup)

    gk, bk = {}, {}
    for i, s in g_satir.items():
        gk.setdefault(anahtar(s["boyut"]), []).append(i)
    for j, s in b_satir.items():
        bk.setdefault(anahtar(s["olcu"]), []).append(j)
    cift = [(gk[k], bk[k], True, k) for k in gk if k in bk]
    kalan_g = [k for k in gk if k not in bk]
    kalan_b = [k for k in bk if k not in gk]

    def eslestir(kosul):
        for a in list(kalan_g):
            for b in kalan_b:
                if kosul(a, b):
                    cift.append((gk[a], bk[b], True, b))
                    kalan_g.remove(a)
                    kalan_b.remove(b)
                    break

    if not en_buyuk:
        eslestir(lambda a, b: ayni_sayilar(g_satir[gk[a][0]]["boyut"], b_satir[bk[b][0]]["olcu"]))
    elif tolerans:
        eslestir(lambda a, b: a is not None and b is not None and abs(a - b) <= tolerans)
    if grup and grup.get("sira") and kalan_g and len(kalan_g) == len(kalan_b):
        def sira(k, satir, alan, idx):
            return ((k if en_buyuk else _en_buyuk(satir[idx[k][0]][alan])) or 0, sayilar(satir[idx[k][0]][alan]))
        sg = sorted(kalan_g, key=lambda k: sira(k, g_satir, "boyut", gk), reverse=True)
        sb = sorted(kalan_b, key=lambda k: sira(k, b_satir, "olcu", bk), reverse=True)
        cift += [(gk[a], bk[b], False, b) for a, b in zip(sg, sb)]
        kalan_g, kalan_b = [], []
    elif grup is None and len(kalan_g) == 1 and len(kalan_b) == 1:
        a, b = kalan_g[0], kalan_b[0]
        cift.append((gk[a], bk[b], not (boyutlu(g_satir[gk[a][0]]["boyut"]) and boyutlu(b_satir[bk[b][0]]["olcu"])), b))
        kalan_g, kalan_b = [], []
    return cift, [i for k in kalan_g for i in gk[k]], [j for k in kalan_b for j in bk[k]]


def esle(bizim: list[dict], gercek: list[dict], gruplar: list[dict]) -> dict:
    """bizim: liste üretecinin satırları (kalem, olcu, adet, pafta, aday); gercek: okuyucunun satırları (malzeme, boyut, adet).

    Dönen: {"gercek": [her dolu gerçek satır için {i, sonuc, grup, ad, bizim: [j…], b_anahtar, G, n_g, olcu_tuttu}],
    "fazla": [j…], "sayilar": {…}}. `grup` sözlük grubunun adı, `ad` aynı ad grubunun düzgünleştirilmiş adı; `b_anahtar` bizim yanın ölçü
    anahtarı (`yok` ve `her_satir` kipinde None: grubun bütün satırları).
    """
    dolu = {i: s for i, s in enumerate(gercek) if sayi_mi(s.get("adet")) and s["adet"] > 0}
    gg, bg = {}, {}
    for i, s in dolu.items():
        gg.setdefault(grup_anahtari(s["malzeme"], gruplar, "_g"), {})[i] = s
    for j, s in enumerate(bizim):
        bg.setdefault(grup_anahtari(s["kalem"], gruplar, "_b"), {})[j] = s
    satir, fazla = {}, []
    for anahtar in list(gg) + [k for k in bg if k not in gg]:
        g_satir, b_satir = gg.get(anahtar, {}), bg.get(anahtar, {})
        tur, k = anahtar
        grup = gruplar[k] if tur == "s" else None
        cift, essiz_g, essiz_b = _anahtarla(g_satir, b_satir, grup)
        ortak = {"grup": grup["ad"] if grup else None, "ad": None if grup else k}
        for gi, bj, olcu_tuttu, b_anahtar in cift:
            G = sum(dolu[i]["adet"] for i in gi)
            s = _karar(G, [bizim[j] for j in bj], len(gi)) if olcu_tuttu else "farklı"
            for i in gi:
                satir[i] = {"i": i, "sonuc": s, **ortak, "bizim": list(bj), "b_anahtar": b_anahtar, "G": G, "n_g": len(gi),
                            "olcu_tuttu": olcu_tuttu, "anahtar_satirlari": list(gi)}
        for i in essiz_g:
            satir[i] = {"i": i, "sonuc": "bizde yok", **ortak, "bizim": [], "b_anahtar": None, "G": dolu[i]["adet"], "n_g": 1,
                        "olcu_tuttu": None, "anahtar_satirlari": [i]}
        fazla += [j for j in essiz_b if sayi_mi(bizim[j]["adet"]) and bizim[j]["adet"] > 0]
    sonuc = [satir[i] for i in sorted(satir)]
    say = {s: sum(1 for r in sonuc if r["sonuc"] == s) for s in SONUCLAR}
    say["bizde fazla"] = len(fazla)
    say["gercek_dolu"] = len(dolu)
    say["dogru"] = sum(say[s] for s in DOGRU)
    return {"gercek": sonuc, "fazla": sorted(fazla), "sayilar": say}


def bizim_secimi(bizim: list[dict], gruplar: list[dict], tutan: dict) -> list[dict]:
    """Gerileme kapısı: tutan bir anahtarın bugünkü listedeki satırları (aynı grup ya da ad, aynı ölçü anahtarı)."""
    hedef = ("s", next(i for i, g in enumerate(gruplar) if g["ad"] == tutan["grup"])) if tutan["grup"] else ("a", tutan["ad"])
    grup = gruplar[hedef[1]] if hedef[0] == "s" else None
    secilen = []
    for s in bizim:
        if grup_anahtari(s["kalem"], gruplar, "_b") != hedef:
            continue
        if tutan["b_anahtar"] is not None and olcu_anahtari(s["olcu"], grup) != tutan["b_anahtar"]:
            continue
        secilen.append(s)
    return secilen


def tutuyor_mu(bizim: list[dict], gruplar: list[dict], tutan: dict) -> str | None:
    """Tutan anahtar bugünkü listede hâlâ doğru mu: doğruysa sonucu, değilse None."""
    secilen = bizim_secimi(bizim, gruplar, tutan)
    if not secilen:
        return None
    s = _karar(tutan["deger"], secilen, tutan["gercek_satir"])
    return s if s in DOGRU else None
