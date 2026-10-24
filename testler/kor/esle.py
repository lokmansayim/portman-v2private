"""Kör test aracının eşlemesi (BK-12 PR-3, M7): gerçek satır ↔ bizim satır ve otomatik sonuç.

Eşleme iki katmanlıdır:
1. **Sözlük** (`sozluk.json`): aynı kalemin iki listede farklı yazıldığı ya da farklı bölündüğü kalem grupları. Her grup bizim kalem
   adlarına ve gerçek malzeme adlarına uyan desenlerle tanımlanır (desenler düzgünleştirilmiş ada uygulanır; ilk uyan grup alır).
   Sözlük kalem adı taşır, gerçek listelerin adedini ya da ölçüsünü taşımaz.
2. **Aynı ad:** sözlüğe girmeyen satırlar düzgünleştirilmiş adları aynıysa bir gruptur.

Grup içinde satırlar anahtarlarla eşlenir (sözlükte `olcu`):
- `tam` (aynı ad gruplarının varsayılanı): anahtar düzgünleştirilmiş ölçüdür; yazısı farklı ama sayıları aynı olan ölçüler de eşlenir
  ("1200*1200" ↔ "1200 × 1200", "125*125" ↔ "125/125", "90*200" ↔ "900 × 2000"). `anahtar: en_buyuk` ise anahtar ölçünün en büyük
  sayısıdır (profil boyları: "100*100*3240" ↔ "L 3240"); `tolerans` (mm) içindeki anahtarlar da eşlenir (yuvarlama). `sira: true`
  ise eşi kalmayan anahtarlar iki yanda aynı sayıdaysa büyükten küçüğe eşlenir ve ölçüsü tutmadığı için "farklı" sayılır. Aynı ad
  grubunda iki yanda birer anahtar kalmışsa ikisi eşlenir: birinin ölçüsünde sayı yoksa ("ADET", "METRE") adet kıyaslanır, ikisinde
  de sayı varsa ölçü tutmadığı için "farklı" sayılır (uydurma: L 1150 ↔ L 950, "4,5 X 16" ↔ "3,5 X 25", "20 Amper" ↔ "25 Amper").
- `yok`: grubun bütün satırları tek anahtardır; toplam kıyaslanır, satırlar arasındaki dağılım kıyaslanmaz (ör. H'ların kulaklı /
  dübelli / özel bölünmesi; 13 Ekim tanımında "toplam aynı, ayrım farklı"). Ölçü kümesi ayrıca kıyaslanır: iki yanda da ölçüsünde
  sayı olan satır varsa her gerçek ölçünün bizde, her bizim ölçümüzün (adet > 0) gerçek listede eşi olmalı, yoksa satırlar "farklı"
  sayılır (ör. saçak sacı 300 × 2500 ↔ 500 × 3000). Gerçek yanın bütün satırları ve bizim yanın adedi dolu bütün satırları sayılı
  ölçülüyse ve bizde birden çok ölçü varsa ölçü başına toplam da tutmalı (ör. 300 × 2500 × 4 + 500 × 3000 × 6 ↔ 6 + 4 "farklı"). Eş: aynı ölçü ya da aynı sayılar; `anahtar:
  en_buyuk` ise en büyük sayı (`tolerans` içinde). `olcu_serbest: true` olan grupta ölçü kıyaslanmaz (iki listenin ölçüsü başka şeyi
  anlatıyor; gerekçe `not`'ta).
- `her_satir`: bizim satırlarımız gerçek listenin her satırıyla ayrı ayrı kıyaslanır (ör. vitrifiye takımı: dört satır, her biri 1);
  gerçek satırın ölçüsünde sayı varsa bizim sayılı ölçülerimizden birinin eşi olmalı.
Bir yanda ölçüsünde sayı olan satır yoksa (ör. bizde "ADET", gerçekte "L:3750") ölçü kıyaslanmaz, yalnız adet kıyaslanır.

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
KAPI_SONUC = {"aynı": ("aynı", "ayrım"), "ayrım": ("aynı", "ayrım"), "pafta": ("aynı", "ayrım", "pafta"), "aday": DOGRU}
GRUP_OLCULU = ("kalan", "esdeger", "tolerans")      # kapıda grubun bütün bizim ölçüleri de sabit
SATIR_BASINA = ("toplam", "her_satir")             # kapıda grubun bizim satır değerleri de sabit (gerekirse; `satir_degerleri`)


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
    """Ölçüdeki sayılar; "M2", "M³" gibi birim yazıları sayı değildir ("PKT / 60 M2" ↔ "paket / 60 m²")."""
    t = re.sub(r"\bM[23²³]\b", "", ust(t))
    return tuple(float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", t))


def ayni_sayilar(a, b) -> bool:
    """İki ölçünün sayıları aynı mı; birim farkı (cm ↔ mm) da aynı sayılır."""
    x, y = sayilar(a), sayilar(b)
    if not x or len(x) != len(y):
        return False
    return any(all(abs(p * k - q) < 1e-6 for p, q in zip(x, y)) for k in (1, 10, 0.1))


def boyutlu(t) -> bool:
    """Ölçü bir boyut mu (100 ve üstü bir sayı), yoksa birim yazısı mı ("ADET", "16 Amper", "Kova (17,5 KG)")."""
    return any(x >= 100 for x in sayilar(t))


def olculu(t) -> bool:
    """Ölçüde kıyaslanacak bir sayı var mı ("ADET", "METRE", "M2" yalnız birimdir)."""
    return bool(sayilar(t))


def esdeger(a, b, grup: dict | None = None) -> bool:
    """Eşlemede iki ölçü aynı mı: aynı yazı ya da aynı sayılar (cm ↔ mm dahil); `anahtar: en_buyuk` ise en büyük sayı, `tolerans` içinde."""
    if olcu(a) == olcu(b):
        return True
    if grup and grup.get("anahtar") == "en_buyuk":
        x, y = _en_buyuk(a), _en_buyuk(b)
        return x is not None and y is not None and abs(x - y) <= float(grup.get("tolerans", 0))
    return ayni_sayilar(a, b)


def kimlik(t) -> str:
    """Kapıda ölçünün kimliği: `olcu` yazısı; yazıya çevirmek sayıları değiştiriyorsa (boşlukla ayrılmış rakamlar "1 200 × 300" →
    "1200X300", birim yazısı "60 M2" → "60M2") yanına sayılar da yazılır. Eşleme hem yazıya (`esdeger`) hem sayılara (`ayni_sayilar`,
    `olculu`) baktığı için kapı ölçüyü her yerde kimlikle tanır ve ikisini birlikte sabitler; sekiz projenin bizim listelerinde kimlik
    `olcu` ile aynı."""
    o, s = olcu(t), sayilar(t)
    return o if sayilar(o) == s else o + " | " + " ".join(f"{x:g}" for x in s)


def ayni_olcu(a, b, grup: dict | None = None) -> bool:
    """Gerileme kapısında kayıttaki bizim ölçümüzle bugünkü aynı mı: aynı kimlik, her kipte (birim çevirisi ve tolerans yok;
    `anahtar: en_buyuk` grubunda da yalnız en büyük sayı yetmez: kapı o grupta satırları en büyük sayıyla seçer, `bizim_secimi`, ve
    kayıttakilerle kimlikle eşler; en büyük sayısı aynı, kimliği farklı satır "yeni satır" olur). Aynı yazıya inen ama sayıları farklı iki
    ölçü ("1 200 × 300" ↔ "1200 × 300") de, sayıları aynı ama yazısı farklı iki ölçü ("1200 × 300" ↔ "1200/300") de aynı değildir:
    `tam` kipinde anahtar yazıdır, eşdeğer adımı sayılara bakar. `grup` imza için durur."""
    return kimlik(a) == kimlik(b)


def belirsiz_olcu(satirlar: list[dict]) -> list[str]:
    """Aynı yazıya inen ama sayıları farklı bizim ölçülerimiz (ör. "1200 × 300" ile "1 200 × 300"): `tam` kipinde ikisi aynı
    anahtardadır ve anahtarın sayıları kimlik sırasıyla ilk satırdan gelir; aynı ölçünün iki yazımı üreteçte tutarsızlıktır. Kapı böyle
    bir grupta, tutan satır başka anahtarda olsa da durur (yanlış alarm yönünde katı; bugün sekiz projede yok)."""
    k: dict[str, set] = {}
    for s in satirlar:
        k.setdefault(olcu(s["olcu"]), set()).add(kimlik(s["olcu"]))
    return sorted(o for o, v in k.items() if len(v) > 1)


def _kume_tutar(g_olcu: list, b_olcu: list, grup: dict | None) -> bool:
    """`yok` kipinde ölçü kümesi: iki yanda da sayılı ölçü varsa her birinin öbür yanda eşi olmalı."""
    g, b = [t for t in g_olcu if olculu(t)], [t for t in b_olcu if olculu(t)]
    if not g or not b or (grup and grup.get("olcu_serbest")):
        return True
    return all(any(esdeger(x, y, grup) for y in b) for x in g) and all(any(esdeger(x, y, grup) for x in g) for y in b)


def _olcu_basina_tutar(g_satir: list[dict], b_satir: list[dict], grup: dict | None) -> bool:
    """`yok` kipinde gerçek yanın bütün satırları ve bizim yanın adedi dolu bütün satırları (`b_satir`) sayılı ölçülüyse ve bizde birden
    çok ölçü varsa her ölçünün toplamı da tutmalı (aynı kalemin iki ölçüsünde adetler ters dağılmışsa toplam ve ölçü kümesi tutar, ölçü
    başına toplam tutmaz)."""
    if grup and grup.get("olcu_serbest"):
        return True
    if not all(olculu(s["boyut"]) for s in g_satir) or not all(olculu(s["olcu"]) for s in b_satir):
        return True
    temsil = []
    for s in sorted(b_satir, key=lambda s: kimlik(s["olcu"])):        # satır sırasına bağlı kalmasın (`esdeger` geçişli değil)
        if not any(esdeger(s["olcu"], r, grup) for r in temsil):
            temsil.append(s["olcu"])
    if len(temsil) < 2:
        return True
    for r in temsil:
        G = sum(s["adet"] for s in g_satir if esdeger(s["boyut"], r, grup))
        if _karar(G, [s for s in b_satir if esdeger(s["olcu"], r, grup)], 1) not in DOGRU:
            return False
    return True


def satir_degerleri(satirlar: list[dict], grup: dict | None) -> list | None:
    """`yok` ve `her_satir` kipinde gerileme kapısı için grubun bizim satırlarımızın değerleri: [[kalem, ölçü, varsayılan, pafta, aday]].

    Ölçü kümesi, ölçü başına toplam ve `her_satir` ölçüsü satırların doluluğuna (adet > 0), ölçüsüne ve pafta / aday sütunlarına satır
    satır bakar: grupta iki ya da daha çok sayılı ölçü varsa ya da adedi dolu olmayan sayılı ölçülü bir satır varsa, toplamlar aynı
    kalsa da bir satırın adedi ya da sütunu değişince eşleme değişebilir (ör. adedin iki ölçü arasında kayması, sayılı ölçüsü olmayan
    satırın boşalması, aynı ölçüdeki iki satır arasında pafta dağılımı). Kapı bu yüzden satırların değerlerini ister (yanlış alarm yönünde
    katı). Öteki durumlarda None: grubun ölçüsü serbest, sayılı ölçü yok, ya da sayılı ölçü tek ve adedi dolu (eşleme o zaman yalnız
    toplama bakar, kapı toplamı zaten ister)."""
    if grup and grup.get("olcu_serbest"):
        return None
    sayili = [s for s in satirlar if olculu(s["olcu"])]
    olculer = {kimlik(s["olcu"]) for s in sayili}
    if not olculer or (len(olculer) == 1 and all(sayi_mi(s["adet"]) and s["adet"] > 0 for s in sayili)):
        return None
    d = [[ad(s["kalem"]), kimlik(s["olcu"]), s.get("adet"), s.get("pafta"), s.get("aday")] for s in satirlar]
    return sorted(d, key=lambda r: json.dumps(r, ensure_ascii=False))


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
        if g.get("olcu_serbest") and (kip == "tam" or not str(g.get("not") or "").strip()):
            raise ValueError(f"sözlük grubu {g.get('ad')!r}: olcu_serbest yalnız yok / her_satir kipinde ve gerekçesiyle (not)")
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
    """Grup içinde anahtarlar: [(gerçek satır indisleri, bizim satır indisleri, ölçü tuttu mu, bizim anahtar, eşleme türü)],
    eşsiz gerçek, eşsiz bizim. Eşleme türü: anahtar · esdeger (aynı sayılar) · tolerans · sira · kalan · toplam (`yok`) · her_satir."""
    kip = grup["olcu"] if grup else "tam"
    dolu = [b_satir[j] for j in b_satir if sayi_mi(b_satir[j]["adet"]) and b_satir[j]["adet"] > 0]
    dolu_b = [s["olcu"] for s in dolu]
    if kip == "yok":
        if g_satir and b_satir:
            tuttu = (_kume_tutar([s["boyut"] for s in g_satir.values()], dolu_b, grup)
                     and _olcu_basina_tutar(list(g_satir.values()), dolu, grup))
            return [(list(g_satir), list(b_satir), tuttu, None, "toplam")], [], []
        return [], list(g_satir), list(b_satir)
    if kip == "her_satir":
        if b_satir:
            return ([([i], list(b_satir), _her_satir_tutar(g_satir[i]["boyut"], dolu_b, grup), None, "her_satir") for i in g_satir],
                    [], ([] if g_satir else list(b_satir)))
        return [], list(g_satir), []
    en_buyuk = bool(grup and grup.get("anahtar") == "en_buyuk")
    tolerans = float(grup.get("tolerans", 0)) if grup else 0.0

    def anahtar(t):
        return olcu_anahtari(t, grup)

    gk, bk = {}, {}
    for i, s in g_satir.items():
        gk.setdefault(anahtar(s["boyut"]), []).append(i)
    for j, s in sorted(b_satir.items(), key=lambda js: kimlik(js[1]["olcu"])):   # bizim satır sırası eşlemeyi değiştirmesin
        bk.setdefault(anahtar(s["olcu"]), []).append(j)
    cift = [(gk[k], bk[k], True, k, "anahtar") for k in gk if k in bk]
    kalan_g = [k for k in gk if k not in bk]
    kalan_b = [k for k in bk if k not in gk]

    def eslestir(kosul, tur):
        for a in list(kalan_g):
            for b in kalan_b:
                if kosul(a, b):
                    cift.append((gk[a], bk[b], True, b, tur))
                    kalan_g.remove(a)
                    kalan_b.remove(b)
                    break

    if not en_buyuk:
        eslestir(lambda a, b: ayni_sayilar(g_satir[gk[a][0]]["boyut"], b_satir[bk[b][0]]["olcu"]), "esdeger")
    elif tolerans:
        eslestir(lambda a, b: a is not None and b is not None and abs(a - b) <= tolerans, "tolerans")
    if grup and grup.get("sira") and kalan_g and len(kalan_g) == len(kalan_b):
        def sira(k, satir, alan, idx):
            return ((k if en_buyuk else _en_buyuk(satir[idx[k][0]][alan])) or 0, sayilar(satir[idx[k][0]][alan]))
        sg = sorted(kalan_g, key=lambda k: sira(k, g_satir, "boyut", gk), reverse=True)
        sb = sorted(kalan_b, key=lambda k: sira(k, b_satir, "olcu", bk), reverse=True)
        cift += [(gk[a], bk[b], False, b, "sira") for a, b in zip(sg, sb)]
        kalan_g, kalan_b = [], []
    elif grup is None and len(kalan_g) == 1 and len(kalan_b) == 1:
        a, b = kalan_g[0], kalan_b[0]
        cift.append((gk[a], bk[b], not (olculu(g_satir[gk[a][0]]["boyut"]) and olculu(b_satir[bk[b][0]]["olcu"])), b, "kalan"))
        kalan_g, kalan_b = [], []
    return cift, [i for k in kalan_g for i in gk[k]], [j for k in kalan_b for j in bk[k]]


def _her_satir_tutar(g_olcu, b_olcu: list, grup: dict | None) -> bool:
    """`her_satir`: gerçek satırın ölçüsü sayılıysa bizim sayılı ölçülerimizden birinin eşi olmalı."""
    b = [y for y in b_olcu if olculu(y)]
    if not olculu(g_olcu) or not b or (grup and grup.get("olcu_serbest")):
        return True
    return any(esdeger(g_olcu, y, grup) for y in b)


def esle(bizim: list[dict], gercek: list[dict], gruplar: list[dict]) -> dict:
    """bizim: liste üretecinin satırları (kalem, olcu, adet, pafta, aday); gercek: okuyucunun satırları (malzeme, boyut, adet).

    Dönen: {"gercek": [her dolu gerçek satır için {i, sonuc, grup, ad, bizim: [j…], b_anahtar, G, n_g, olcu_tuttu, eslesme,
    anahtar_satirlari, grup_bizim, satir_degerleri}], "fazla": [j…], "sayilar": {…}}. `grup` sözlük grubunun adı, `ad` aynı ad grubunun düzgünleştirilmiş
    adı; `b_anahtar` bizim yanın ölçü anahtarı (`yok` ve `her_satir` kipinde None: grubun bütün satırları); `grup_bizim` grubun bütün
    bizim satırları (eşdeğer, tolerans ve kalan eşlemesinin kapısı için); `satir_degerleri` toplam ve her satır eşlemesinde
    grubun bizim satır değerleri (kapı için; gerekmiyorsa None, › `satir_degerleri`).
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
        for gi, bj, olcu_tuttu, b_anahtar, eslesme in cift:
            G = sum(dolu[i]["adet"] for i in gi)
            s = _karar(G, [bizim[j] for j in bj], len(gi)) if olcu_tuttu else "farklı"
            sd = satir_degerleri([bizim[j] for j in bj], grup) if eslesme in SATIR_BASINA else None
            for i in gi:
                satir[i] = {"i": i, "sonuc": s, **ortak, "bizim": list(bj), "b_anahtar": b_anahtar, "G": G, "n_g": len(gi),
                            "olcu_tuttu": olcu_tuttu, "eslesme": eslesme, "anahtar_satirlari": list(gi), "grup_bizim": list(b_satir),
                            "satir_degerleri": sd}
        for i in essiz_g:
            satir[i] = {"i": i, "sonuc": "bizde yok", **ortak, "bizim": [], "b_anahtar": None, "G": dolu[i]["adet"], "n_g": 1,
                        "olcu_tuttu": None, "eslesme": None, "anahtar_satirlari": [i], "grup_bizim": list(b_satir),
                        "satir_degerleri": None}
        fazla += [j for j in essiz_b if sayi_mi(bizim[j]["adet"]) and bizim[j]["adet"] > 0]
    sonuc = [satir[i] for i in sorted(satir)]
    say = {s: sum(1 for r in sonuc if r["sonuc"] == s) for s in SONUCLAR}
    say["bizde fazla"] = len(fazla)
    say["gercek_dolu"] = len(dolu)
    say["dogru"] = sum(say[s] for s in DOGRU)
    return {"gercek": sonuc, "fazla": sorted(fazla), "sayilar": say}


def _hedef(gruplar: list[dict], tutan: dict):
    if tutan["grup"]:
        k = next((i for i, g in enumerate(gruplar) if g["ad"] == tutan["grup"]), None)
        if k is None:
            return None, None
        return ("s", k), gruplar[k]
    return ("a", tutan["ad"]), None


def bizim_secimi(bizim: list[dict], gruplar: list[dict], tutan: dict) -> list[dict]:
    """Gerileme kapısı: tutan bir anahtarın bugünkü listedeki satırları (aynı grup ya da ad; `tam` kipinde eşlemenin anahtarı,
    `olcu_anahtari`, kayıttaki bizim satırlarımızınkiyle aynı olanlar: `anahtar: en_buyuk` grubunda en büyük sayısı aynı ama yazısı
    farklı yeni bir satır da seçilir ve çift denetiminde "yeni satır" olur)."""
    hedef, grup = _hedef(gruplar, tutan)
    if hedef is None:
        return []
    grubun = [s for s in bizim if grup_anahtari(s["kalem"], gruplar, "_b") == hedef]
    if tutan["b_anahtar"] is None:
        return grubun
    anahtarlar = {olcu_anahtari(k["olcu"], grup) for k in tutan["bizim"]}
    return [s for s in grubun if olcu_anahtari(s["olcu"], grup) in anahtarlar]


def kapi_denetle(bizim: list[dict], gruplar: list[dict], tutan: dict) -> tuple[str | None, str]:
    """Tutan anahtar bugünkü listede hâlâ doğru mu: (sonuç, "") ya da (None, neden).

    Grubun bizim satırlarında aynı yazıya inen ama sayıları farklı ölçü varsa (`belirsiz_olcu`) kapı durur. Kayıttaki bizim
    satırlarımızın (kalem, ölçü) çiftleri bugün de aynı olmalı (eksik ya da yeni satır yok; ölçü `ayni_olcu`: kimlik), adetleri
    kayıttaki değeri kayıttaki sonucun sütununda vermeli: aynı ya da ayrım tutmuşsa varsayılan adet, pafta tutmuşsa pafta ya da
    varsayılan, aday tutmuşsa üçünden biri (`KAPI_SONUC`). Kalan, eşdeğer ya da tolerans eşlemesiyle tutmuş satırda grubun bütün
    ölçüleri de (`kimlik`) kayıttaki gibi olmalı (`GRUP_OLCULU`): gruba eklenen ya da ölçüsü değişen bir satır eşlemeyi değiştirebilir.
    Toplam ya da her satır eşlemesiyle tutmuş satırda kayıtta `satir_degerleri` varsa (iki ya da daha çok sayılı ölçü, ya da adedi boş ya
    da 0 olan sayılı ölçülü satır) grubun satırlarının değerleri de kayıttaki gibi olmalı: satırlar arasında kayan bir adet ya da sütun
    değeri ölçü kümesini, ölçü başına toplamı ya da `her_satir` ölçüsünü bozabilir."""
    hedef, grup = _hedef(gruplar, tutan)
    if hedef is None:
        return None, "sözlükte grup yok"
    belirsiz = belirsiz_olcu([s for s in bizim if grup_anahtari(s["kalem"], gruplar, "_b") == hedef])
    if belirsiz:
        return None, "belirsiz ölçü (aynı yazı, farklı sayılar): " + ", ".join(belirsiz)
    secilen = bizim_secimi(bizim, gruplar, tutan)
    kalan = list(secilen)
    for k in tutan["bizim"]:
        e = next((s for s in kalan if ad(s["kalem"]) == ad(k["kalem"]) and ayni_olcu(s["olcu"], k["olcu"], grup)), None)
        if e is None:
            return None, f"satır yok: {k['kalem']} · {k['olcu']}"
        kalan.remove(e)
    if kalan:
        return None, "yeni satır: " + " + ".join(f"{s['kalem']} · {s['olcu']}" for s in kalan)
    if tutan.get("eslesme") in GRUP_OLCULU:
        bugun = sorted(kimlik(s["olcu"]) for s in bizim if grup_anahtari(s["kalem"], gruplar, "_b") == hedef)
        if bugun != tutan["grup_olculeri"]:
            return None, f"grubun ölçüleri değişti ({tutan['eslesme']} eşleme): kayıtta {tutan['grup_olculeri']}, bugün {bugun}"
    if "satir_degerleri" in tutan:
        bugun = satir_degerleri(secilen, grup)
        if bugun != tutan["satir_degerleri"]:
            return None, f"satır değerleri değişti ({tutan['eslesme']} eşleme): kayıtta {tutan['satir_degerleri']}, bugün {bugun}"
    s = _karar(tutan["deger"], secilen, 1)
    if s not in KAPI_SONUC[tutan["sonuc"]]:
        return None, (f"adet: kayıtta {tutan['deger']} ({tutan['sonuc']}), bugün " + " + ".join(_adet_yazisi(x) for x in secilen)
                      + f" → {s if s in DOGRU else 'tutmuyor'}")
    return s, ""


def _adet_yazisi(s: dict) -> str:
    ek = [f"{k} {s[k]}" for k in ("pafta", "aday") if s.get(k) is not None]
    return str(s["adet"]) + (f" ({', '.join(ek)})" if ek else "")


def tutuyor_mu(bizim: list[dict], gruplar: list[dict], tutan: dict) -> str | None:
    """Tutan anahtar bugünkü listede hâlâ doğru mu: doğruysa sonucu, değilse None (`kapi_denetle`)."""
    return kapi_denetle(bizim, gruplar, tutan)[0]
