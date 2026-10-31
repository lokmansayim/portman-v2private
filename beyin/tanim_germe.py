"""İE-23 PR-2a · Banka modelinde oda büyütme / küçültme: Yapı Tanımı germe ve iç duvar kaydırma (LLM yok; belirlenimci).

İşlem `{op: oda_buyut | oda_kucult, mahal, yon: G|K|B|D, cm}` (`plan_islem.Islem` ile aynı dil; G ön, K arka, B sol, D sağ). Harita yapı
kimliğinden (`beyin/yapi_kimligi.tanimdan` › parametrik): mahalin o yanındaki kenarlar, ön bilgileri (oynar / düzey 2 / kilitli) ve
kesit bantları. Karar hakemindir: uygulayıcı önerir, hakem değişmez (Z-03).

- **Dış kenar → germe (düzey 1).** Kesit, mahalin içinden geçen ve verandayı kesmeyen düzey 1 bandına konur (öteki mahalleri en az
  kesen, en geniş, kenara en yakın bant). Kesitin ötesindeki her koordinat cm kadar kayar: duvarlar, açıklıklar, mahal noktaları,
  kirişler, çatı düzlemleri ve karkas izleri, saçak çizgileri, özel kenarlar, kalkanlar, makas dizileri. Kesiti kesen duvarlar ve
  kirişler uzar; kesitin kestiği çatı düzlemleri eğimlerine paralel uzar (kotlar değişmez). Kesitin ötesine taşan makas aralığı
  tanımdaki en büyük aralığı aşarsa araya eşit aralıkla makas eklenir. Küçültmede kesitte cm genişliğinde boş bir şerit çıkarılır;
  şeritte duvar ucu, kalkan ya da çatı köşesi varsa işlem yapılmaz.
- **İç kenar → duvar kayar.** Kenarın duvarları cm kadar kayar; uçları o duvarın kalınlığında biten dik duvarlar (T ve L birleşimi)
  uzar ya da kısalır, aynı hizadaki kiriş uçları da. Kayan duvarın yolundaki kapı ve pencere (dik duvarda, küçülen yanda) duvarla
  birlikte kayar; köşeye uzaklığı korunur, bayiye yazılır. Kayan duvarla aynı hizada duran kiriş ya da duvara bitişik devam eden duvar varsa yapılmaz.
- **Kilitli kenar** (veranda, ana çatının açıklığı = düzey 3, karşı komşunun başka hizada devam etmesi …) → `GermeHatasi`, gerekçe
  bayinin okuyacağı Türkçeyle (K21: sessiz düşme yok). Düzey 2 (ikincil çatı yeniden hesabı) bu PR'da yok: gerekçesiyle yapılmaz.

Hakem (`denetle`): `yapi.kur` + `aciklik_denetimi` (varyant), aynı duvarda açıklık örtüşmesi ve 15 cm parça (D-10; yalnız yeni çıkan),
`cati_genel.cati_kur`, metraj (kimlik), yükleme listesinin girdisi (`girdi_genel.girdi`, yöntem panel), açıklık–mahal ilişkisi değişmez
(her kapı aynı iki mahal arasında, her pencere aynı mahalde), değişen mahallerde oda en küçükleri (`kurallar/plan/oda_kurallari.json`:
net m², dar kenar, kol; yalnız kötüleşen ölçü). Karkas modeli (`celik_modeli`, SKP) gerilmiş eve uymaz: karkas kurala geçer
(`karkas: kural`; çıktı TASLAK, metraj kapısı taşınmaz). Etiket alanı (`etiket_m2`, çizimden okunmuş) değişen mahalde kalkar.
"""
from __future__ import annotations

import collections
import copy
import math
import re

from beyin import yapi_kimligi as YK
from beyin.varyant import VaryantHatasi, _kur, aciklik_denetimi

ISARET = {"G": -1, "K": 1, "B": -1, "D": 1}               # yanın eksendeki yönü (+y kuzey, +x doğu)
YON_SOZU = {"G": "öne", "K": "arkaya", "B": "sola", "D": "sağa"}
YAN_SOZU = {"G": "ön", "K": "arka", "B": "sol", "D": "sağ"}
CM_ARALIK = (5, 300)                                       # `plan_islem.Islem.cm` ile aynı
KISA_PARCA_CM = 15                                         # D-10: çelikte 15 cm (ve daha kısa) parça çıkmaz
TOL = 0.01
KESIT_DUVAR_SINIFLARI = ("dis", "ic", "ek")               # kesit yalnız bu sınıftaki duvarları uzatır (kolon, baca, korkuluk değil)
ISLEV_KURAL_SIRA = ("salon", "yatak_odasi", "mutfak", "banyo", "hol", "depo")   # karma mahalde kural (salonla birlikte mutfak: salon kuralı)


class GermeHatasi(VaryantHatasi):
    """Oda büyütme / küçültme uygulanamadı; ileti bayiye gider (gerekçe, kodun dilinde değil)."""


def _tr(v: float, n: int = 2) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def _sayi(yeni: float, eski) -> float | int:
    v = round(float(yeni), 2)
    if isinstance(eski, int) and not isinstance(eski, bool) and v.is_integer():
        return int(v)
    return 0.0 if v == 0 else v


# ── koordinat dönüşümü ─────────────────────────────────────────────────────────────────────────────────────────────────
class _Donusum:
    """Eksen boyunca tek boyutlu dönüşüm. Germe: kesit `c`'nin `s` yanı `+s·cm` kayar. Küçültme: [a, a + cm] şeridi çıkar; şeridin `s`
    yanı `−s·cm` kayar (s = +1: üst yan aşağı; s = −1: alt yan yukarı). Şeridin içindeki değer yalnız `serbest=True` ile (mahal noktası)
    şeridin kenarına iner; öteki öğeler için `GermeHatasi`."""

    def __init__(self, eksen: str, s: int, cm: float, buyut: bool, c: float):
        self.eksen, self.s, self.cm, self.buyut, self.c = eksen, s, float(cm), buyut, float(c)
        self.i = 0 if eksen == "x" else 1
        if not buyut:                                      # şerit [lo, hi]; s yanı kayar
            self.lo, self.hi = (c, c + cm) if s > 0 else (c - cm, c)

    def __call__(self, v, ne: str = "öğe", serbest: bool = False):
        x = float(v)
        if self.buyut:
            if (x - self.c) * self.s > TOL:
                return _sayi(x + self.s * self.cm, v)
            return v
        if self.lo + TOL < x < self.hi - TOL:
            if not serbest:
                raise GermeHatasi(f"küçülecek şeritte {ne} var")
            return _sayi(self.c, v)                           # şerit kapanınca iki kenarı kesitte birleşir
        if (self.s > 0 and x >= self.hi - TOL) or (self.s < 0 and x <= self.lo + TOL):
            return _sayi(x - self.s * self.cm, v)
        return v

    def nokta(self, p: list, ne: str = "öğe", serbest: bool = False) -> list:
        q = list(p)
        q[self.i] = self(p[self.i], ne, serbest)
        return q


def _makas_dizisi(aile: dict, f: _Donusum, ad: str) -> None:
    """Makas ailesi: `x` ve `y` listeleri (biri açıklık, öbürü makas yerleri; `eksen` varsa makasın uzandığı eksen). Kesit ekseninin
    listesi dönüşür. O liste makas yerleriyse ve bir aralık tanımdaki en büyük aralığı aştıysa araya eşit aralıkla makas eklenir;
    küçültmede şeritte kalan makas çıkar, kesitte tanımdaki en küçük aralıktan yakın kalan iki makastan kesite yakın olanı da çıkar."""
    k = f.eksen
    if not isinstance(aile.get(k), list):
        return
    eski = [float(v) for v in aile[k]]
    adet = aile.get("adet")
    if aile.get("eksen") in ("x", "y"):
        yerler = aile["eksen"] != k
    else:
        diger = "y" if k == "x" else "x"
        yerler = adet is not None and len(eski) == adet and not (isinstance(aile.get(diger), list) and len(aile[diger]) == adet)
    if not yerler:                                          # açıklık (uç noktaları): kesiti kesiyorsa makas eğim yönünde uzar (düzey ≥ 2)
        if len(eski) >= 2 and min(eski) < f.c < max(eski) and f.buyut:
            raise GermeHatasi(f"{ad} makaslarının açıklığı kesiti kesiyor (çatı eğimi kesit yönünde)")
        aile[k] = [f(v, f"{ad} makası") for v in aile[k]]
        return
    azalan = len(eski) >= 2 and eski[0] > eski[-1]
    yeni: list[float] = []
    for v in aile[k]:
        try:
            yeni.append(float(f(v, "makas")))
        except GermeHatasi:                                 # küçültmede şeritte kalan makas çıkar
            continue
    yeni = sorted(set(round(v, 2) for v in yeni))
    sirali = sorted(eski)
    en_buyuk = max((b - a for a, b in zip(sirali, sirali[1:])), default=0.0)
    en_kucuk = min((b - a for a, b in zip(sirali, sirali[1:])), default=0.0)
    while not f.buyut and en_kucuk > 0:                     # küçültmede kesitte yaklaşan iki makas: kesite yakın olan çıkar (uçlar kalır)
        dar = [(abs((a + b) / 2 - f.c), n) for n, (a, b) in enumerate(zip(yeni, yeni[1:])) if b - a < en_kucuk - 0.5]
        if not dar:
            break
        n = min(dar)[1]
        ic = [x for x in (n, n + 1) if 0 < x < len(yeni) - 1]
        if not ic:
            break
        del yeni[min(ic, key=lambda x: abs(yeni[x] - f.c))]
    if en_buyuk > 0:
        dolu = [yeni[0]] if yeni else []
        for a, b in zip(yeni, yeni[1:]):
            n = math.ceil((b - a) / en_buyuk - 1e-6)
            dolu += [round(a + (b - a) * j / n, 2) for j in range(1, n)] + [b]
        yeni = dolu
    aile[k] = [_sayi(v, 0.0) for v in (sorted(yeni, reverse=True) if azalan else yeni)]
    if adet is not None:
        aile["adet"] = len(aile[k])


def _donustur(t: dict, f: _Donusum, y: dict) -> dict:
    """Tanımdaki eksen koordinatlarını dönüştürür (kopya). Kesiti kesen duvar ve kiriş uzar (küçültmede kısalır)."""
    t2 = copy.deepcopy(t)
    i = f.i
    for d in t2["duvarlar"]:
        w = y["adli"][d["ad"]]
        a, b = d["kutu"][i], d["kutu"][i + 2]
        kesiyor = (a < f.c - TOL and b > f.c + TOL) if f.buyut else (a <= f.lo + TOL and b >= f.hi - TOL)
        if kesiyor:
            if w["sinif"] not in KESIT_DUVAR_SINIFLARI or w["yon"] != f.eksen:
                raise GermeHatasi(f"kesit {d['ad']} duvarından geçiyor")
            if isinstance(d.get("yukseklik"), dict):
                raise GermeHatasi(f"kesit üst kotu eğimli {d['ad']} duvarından geçiyor")
        d["kutu"][i], d["kutu"][i + 2] = f(a, f"{d['ad']} duvarının ucu"), f(b, f"{d['ad']} duvarının ucu")
    for ac in t2.get("acikliklar") or []:
        if y["adli"][ac["duvar"]]["yon"] != f.eksen:
            continue
        b0, b1 = f(ac["bas"], f"{ac.get('ad')} açıklığı"), f(ac["bas"] + ac["en"], f"{ac.get('ad')} açıklığı")
        if abs(float(b1) - float(b0) - ac["en"]) > TOL:
            raise GermeHatasi(f"kesit {ac.get('ad')} açıklığından geçiyor")
        ac["bas"] = b0
    for m in t2["mahaller"]:
        if m.get("nokta"):
            m["nokta"] = f.nokta(m["nokta"], "mahal noktası", serbest=True)
        if m.get("etiket_yeri"):
            m["etiket_yeri"] = f.nokta(m["etiket_yeri"], "etiket", serbest=True)
        if m.get("poligon"):
            m["poligon"] = [f.nokta(p, f"{m['ad']} köşesi") for p in m["poligon"]]
    for kr in t2.get("kirisler") or []:
        uzun = "x" if kr["kutu"][2] - kr["kutu"][0] >= kr["kutu"][3] - kr["kutu"][1] else "y"
        kr["kutu"][i], kr["kutu"][i + 2] = f(kr["kutu"][i], f"{kr['ad']} kirişi"), f(kr["kutu"][i + 2], f"{kr['ad']} kirişi")
        if uzun == f.eksen:
            kr["acik"] = [[f(a, f"{kr['ad']} kirişi"), f(b, f"{kr['ad']} kirişi")] for a, b in kr.get("acik") or []]
    c = t2["cati"]
    for dz in c.get("duzlemler") or []:
        dz["plan"] = [f.nokta(p, f"{dz['ad']} çatı köşesi") for p in dz["plan"]]
        if dz.get("karkas"):
            dz["karkas"] = [f.nokta(p, f"{dz['ad']} karkas köşesi") for p in dz["karkas"]]
        if isinstance(dz.get("sacak"), dict) and f.eksen in dz["sacak"]:
            dz["sacak"][f.eksen] = f(dz["sacak"][f.eksen], f"{dz['ad']} saçağı")
    for ko in c.get("kenar_ozel") or []:
        ko["p"], ko["q"] = f.nokta(ko["p"], "çatı özel kenarı"), f.nokta(ko["q"], "çatı özel kenarı")
    for k in c.get("kalkanlar") or []:
        if k.get("eksen") == f.eksen:
            k["konum"] = f(k["konum"], k.get("ad") or "kalkan")
        else:
            k["aralik"] = [f(v, k.get("ad") or "kalkan") for v in k["aralik"]]
    for ad, aile in (c.get("makaslar") or {}).items():
        if isinstance(aile, dict):
            _makas_dizisi(aile, f, ad)
    el = (t2.get("elektrik") or {}).get("sigorta_kutusu")
    if isinstance(el, list) and len(el) == 2:
        t2["elektrik"]["sigorta_kutusu"] = f.nokta(el, "sigorta kutusu", serbest=True)
    return t2


# ── dış kenar: germe ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _germe(t: dict, y: dict, kimlik: dict, mahal: str, yon: str, kenarlar: list[dict], cm: int, buyut: bool) -> tuple[dict, dict]:
    eksen, s = YK.YON_EKSEN[yon], ISARET[yon]
    if any(e["durum"] == "duzey2" for e in kenarlar):           # PR-2b: ikincil çatı parçası yeniden hesaplanır
        raise GermeHatasi(f"{YON_SOZU[yon]} büyümek yandaki küçük çatıyı (cumba ya da çıkma çatısı) yeniden hesaplamayı gerektiriyor; "
                          "bu henüz otomatik değil")
    konum = [e["konum_cm"] for e in kenarlar]
    sinir = min(konum) if s > 0 else max(konum)               # kesit, kenarın berisinde (mahalin içinde)
    serit = 0.0 if buyut else float(cm)
    sinif = {m["ad"]: m["sinif"] for m in kimlik["anlamsal"]["mahaller"]}
    adaylar = []
    for g in kimlik["parametrik"]["germe"][eksen]:
        if mahal not in g["mahaller"] or g["duzey"] != 1 or any(sinif.get(m) == "veranda" for m in g["mahaller"]):
            continue
        lo, hi = g["aralik"]
        hi = min(hi, sinir) if s > 0 else hi
        lo = max(lo, sinir) if s < 0 else lo
        if hi - lo < serit - TOL or hi - lo < 0:
            continue
        orta = (lo + hi) / 2
        adaylar.append((len(g["mahaller"]), -(hi - lo), abs(sinir - orta), lo, hi, g))
    if not adaylar:
        raise GermeHatasi("odanın içinden kesit geçecek boş yer yok" + (f" ({cm} cm genişliğinde)" if not buyut else ""))
    hatalar = []
    for _, _, _, lo, hi, g in sorted(adaylar, key=lambda a: a[:4]):
        orta = round((lo + hi) / 2, 1)
        c = orta if buyut else round(orta - s * cm / 2, 1)     # küçültmede şerit [c, c + s·cm] bandın ortasında
        try:
            t2 = _donustur(t, _Donusum(eksen, s, cm, buyut, c), y)
        except GermeHatasi as e:
            hatalar.append(str(e))
            continue
        return t2, {"tur": "germe", "eksen": eksen, "kesit_cm": c, "mahaller": list(g["mahaller"])}
    raise GermeHatasi(hatalar[0])


# ── iç kenar: duvar kayar ────────────────────────────────────────────────────────────────────────────────────────────────
def _kayma(t: dict, y: dict, kimlik: dict, mahal: str, yon: str, kenarlar: list[dict], cm: int, buyut: bool) -> tuple[dict, dict]:
    eksen, s = YK.YON_EKSEN[yon], ISARET[yon]
    delta = s * cm * (1 if buyut else -1)
    i = 0 if eksen == "x" else 1
    j = 1 - i
    tasinan = sorted({d for e in kenarlar for d in e["duvarlar"]})
    ozgun = {d["ad"]: list(d["kutu"]) for d in t["duvarlar"]}
    for ad in tasinan:
        if y["adli"][ad]["yon"] == eksen or y["adli"][ad]["sinif"] != "ic":
            raise GermeHatasi(f"{ad} duvarı kaydırılamaz")
    for ad in tasinan:                                         # aynı hizada bitişik devam eden (kaymayan) duvar
        m = ozgun[ad]
        for d in t["duvarlar"]:
            o = ozgun[d["ad"]]
            if d["ad"] in tasinan or y["adli"][d["ad"]]["yon"] == eksen:
                continue
            ayni_hiza = abs(o[i] - m[i]) < TOL and abs(o[i + 2] - m[i + 2]) < TOL
            if ayni_hiza and (abs(o[j] - m[j + 2]) < TOL or abs(o[j + 2] - m[j]) < TOL):
                raise GermeHatasi("duvar aynı hizada başka bir duvarla devam ediyor; yalnız bir parçası kaydırılamaz")
        for kr in t.get("kirisler") or []:                     # kayan duvarın hizasında kiriş (açıklığın kirişi duvarla birlikte durur)
            k = kr["kutu"]
            if (k[i + 2] - k[i]) > (k[j + 2] - k[j]):
                continue                                       # dik kiriş: ucu aşağıda duvarla birlikte kayar
            if min(k[i + 2], m[i + 2]) - max(k[i], m[i]) > TOL and min(k[j + 2], m[j + 2]) - max(k[j], m[j]) > -TOL:
                raise GermeHatasi("duvarın hizasında kiriş var; duvar kayarsa kiriş de değişirdi")
    t2 = copy.deepcopy(t)
    adli = {d["ad"]: d for d in t2["duvarlar"]}
    for ad in tasinan:
        adli[ad]["kutu"][i] = _sayi(ozgun[ad][i] + delta, ozgun[ad][i])
        adli[ad]["kutu"][i + 2] = _sayi(ozgun[ad][i + 2] + delta, ozgun[ad][i + 2])
    for d in t2["duvarlar"]:                                   # uçları kayan duvarın kalınlığında biten dik duvarlar
        if d["ad"] in tasinan or y["adli"][d["ad"]]["yon"] != eksen:
            continue
        o = ozgun[d["ad"]]
        for ad in tasinan:
            m = ozgun[ad]
            if min(o[j + 2], m[j + 2]) - max(o[j], m[j]) < -TOL:
                continue
            for u in (i, i + 2):
                if m[i] - TOL <= o[u] <= m[i + 2] + TOL:
                    d["kutu"][u] = _sayi(o[u] + delta, o[u])
    for kr in t2.get("kirisler") or []:                        # dik kirişin kayan duvara oturan ucu ve açık aralığı
        k0 = list(kr["kutu"])
        if (k0[i + 2] - k0[i]) < (k0[j + 2] - k0[j]):
            continue
        for ad in tasinan:
            m = ozgun[ad]
            if min(k0[j + 2], m[j + 2]) - max(k0[j], m[j]) < -TOL:
                continue
            for u in (i, i + 2):
                if m[i] - TOL <= k0[u] <= m[i + 2] + TOL:
                    kr["kutu"][u] = _sayi(k0[u] + delta, k0[u])
            kr["acik"] = [[_sayi(v + delta, v) if m[i] - TOL <= v <= m[i + 2] + TOL else v for v in a] for a in kr.get("acik") or []]
    # kayan duvarın yolundaki açıklıklar (dik duvarda, küçülen yanda): duvarla birlikte kayar, köşeye uzaklık korunur; bayiye yazılır
    kayan = []
    for ac in t2.get("acikliklar") or []:
        if y["adli"][ac["duvar"]]["yon"] != eksen or ac["duvar"] in tasinan:
            continue
        w = ozgun[ac["duvar"]]
        for ad in tasinan:
            m = ozgun[ad]
            if min(w[j + 2], m[j + 2]) - max(w[j], m[j]) < -TOL:
                continue
            a0, a1 = ac["bas"], ac["bas"] + ac["en"]
            yolda = (delta > 0 and a0 >= m[i + 2] - TOL and a0 < m[i + 2] + delta + YK.KESIT_PAYI) or \
                    (delta < 0 and a1 <= m[i] + TOL and a1 > m[i] + delta - YK.KESIT_PAYI)
            if yolda:
                ac["bas"] = _sayi(ac["bas"] + delta, ac["bas"])
                kayan.append(ac["ad"])
                break
    # küçülen mahalin noktası süpürülen şeritteyse mahalin kalan net alanına
    from shapely.geometry import box
    serit = []
    for ad in tasinan:
        m = ozgun[ad]
        lo, hi = min(m[i], m[i] + delta), max(m[i + 2], m[i + 2] + delta)
        serit.append(box(lo, m[j], hi, m[j + 2]) if eksen == "x" else box(m[j], lo, m[j + 2], hi))
    from shapely.geometry import Point
    from shapely.ops import unary_union
    suru = unary_union(serit).buffer(YK.KESIT_PAYI + 15, join_style=2)
    for m in t2["mahaller"]:
        for alan in ("nokta", "etiket_yeri"):
            p = m.get(alan)
            b = y["bolgeler"].get(m["ad"])
            if not p or b is None or not suru.contains(Point(*p)):
                continue
            kalan = b["net"].difference(suru)
            if kalan.is_empty or kalan.area < 1e4:
                raise GermeHatasi(f"{m['ad']} neredeyse kalmıyor")
            rp = kalan.representative_point()
            m[alan] = [_sayi(rp.x, 0.0), _sayi(rp.y, 0.0)]
    return t2, {"tur": "kayma", "eksen": eksen, "duvarlar": tasinan, "kayma_cm": delta, "kayan_acikliklar": kayan}


# ── hakem ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _kural_islevi(m: dict) -> str | None:
    if m["sinif"] == "veranda":
        return None
    if m["sinif"] == "ek":
        return "depo"
    for i in ISLEV_KURAL_SIRA:
        if i in (m.get("islev") or []):
            return i
    return None


def _aciklik_iliskisi(k: dict) -> dict:
    """Açıklık adı → (tür, iki yanı). Kapı: kenarın iki mahali; pencere: mahali (dış yanı bilgi)."""
    out = {}
    for e in k["topolojik"]["kenarlar"]:
        for kp in e["kapilar"]:
            out[kp] = ("kapı", tuple(sorted((e["a"], e["b"]))))
    for m in k["anlamsal"]["mahaller"]:
        for p in m["pencereler"]:
            out[p["ad"]] = ("pencere", (m["ad"],))
    return out


def _kisa_parcalar(t: dict) -> collections.Counter:
    """İki eksende birbirine 15 cm ya da daha yakın duran paralel duvar eksenleri (D-10: "çelikte 15 cm parça çıkmaz"; İE-14 denetçisiyle
    aynı ölçüt). Sayaç: (eksen, ara cm)."""
    out: collections.Counter = collections.Counter()
    for i, eks in ((0, "x"), (1, "y")):
        cizgi = sorted({round((d["kutu"][i] + d["kutu"][i + 2]) / 2, 1) for d in t["duvarlar"]
                        if d.get("sinif") in KESIT_DUVAR_SINIFLARI and d["kutu"][i + 2] - d["kutu"][i] < d["kutu"][3 - i] - d["kutu"][1 - i]})
        for a, b in zip(cizgi, cizgi[1:]):
            if 0 < b - a <= KISA_PARCA_CM + TOL:
                out[(eks, round(b - a, 1))] += 1
    return out


def _ortusen_acikliklar(t: dict) -> set[tuple[str, str]]:
    """Aynı duvarda üst üste binen açıklık çiftleri (adlarıyla)."""
    duvar: dict[str, list] = {}
    for a in t.get("acikliklar") or []:
        duvar.setdefault(a["duvar"], []).append((float(a["bas"]), float(a["bas"]) + float(a["en"]), a.get("ad") or ""))
    out = set()
    for liste in duvar.values():
        liste.sort()
        for n, x in enumerate(liste):
            for z in liste[n + 1:]:
                if z[0] < x[1] - TOL:
                    out.add(tuple(sorted((x[2], z[2]))))
    return out


def _aciklik_sozu(t: dict, ad: str) -> str:
    ac = next((a for a in t.get("acikliklar") or [] if a.get("ad") == ad), {})
    mahaller = {m["ad"] for m in t.get("mahaller") or []}
    sahibi = ac.get("mahal") if ac.get("mahal") in mahaller else ac.get("not") if ac.get("not") in mahaller else ""
    if ac.get("giris"):
        return "giriş kapısı"
    ne = "penceresi" if ac.get("tur") == "pencere" else "kapısı"
    return f"{sahibi} {ne}" if sahibi else ("bir pencere" if ac.get("tur") == "pencere" else "bir kapı")


def denetle(t_once: dict, t_sonra: dict, k_once: dict | None = None, set_yolu=None) -> dict:
    """Hakem: geometri (yapı, açıklık, aynı duvarda açıklık örtüşmesi, 15 cm parça), çatı, metraj, yükleme listesi girdisi, açıklık–mahal
    ilişkisi, oda en küçükleri. Geçerse sonra kimliği döner; geçmezse `GermeHatasi`."""
    from beyin.plan_denetim import ISLEV_ADI, kurallar as oda_kurallari
    try:
        y2 = _kur(t_sonra)
        aciklik_denetimi(t_sonra, y2)
    except VaryantHatasi as e:
        raise GermeHatasi(_yapi_nedeni(str(e), t_sonra)) from None
    from motor.genel import cati_genel, girdi_genel, kural as MK, yapi
    try:
        cati_genel.cati_kur(t_sonra["cati"], MK.oku())
        k2 = YK.tanimdan(t_sonra, set_yolu)
    except (SystemExit, ValueError, KeyError) as e:
        raise GermeHatasi(f"çatı ya da metraj kurulamadı ({str(e)[:120]})") from None
    k1 = k_once or YK.tanimdan(t_once, set_yolu)
    if set(k2["topolojik"]["ulasilamayan"]) - set(k1["topolojik"]["ulasilamayan"]) or \
            set(k2["topolojik"]["eslesmeyen_acikliklar"]) - set(k1["topolojik"]["eslesmeyen_acikliklar"]):
        raise GermeHatasi("odaların kapı bağlantıları değişiyor")
    a1, a2 = _aciklik_iliskisi(k1), _aciklik_iliskisi(k2)
    for ad, (tur, yan) in sorted(a1.items()):
        if a2.get(ad) != (tur, yan):
            ne = f"{yan[0]} penceresi" if tur == "pencere" else f"{' ile '.join(yan)} arasındaki kapı"
            raise GermeHatasi(f"{ne} ({ad}) yerinde kalmıyor")
    kural = oda_kurallari()
    once = {m["ad"]: m for m in k1["anlamsal"]["mahaller"]}
    for m in k2["anlamsal"]["mahaller"]:
        m0 = once.get(m["ad"])
        isl = _kural_islevi(m)
        if m0 is None or isl is None:
            continue
        r = kural["odalar"].get(isl) or {}
        ad_ = ISLEV_ADI.get(isl, isl)
        if m["alan_m2"] < m0["alan_m2"] - 1e-6 and m["alan_m2"] + 1e-6 < float(r.get("en_az_m2", 0)):
            raise GermeHatasi(f"{m['ad']} {_tr(m['alan_m2'])} m²'ye iner ({ad_} için en az {_tr(float(r['en_az_m2']), 1)} m²)")
        dar0, dar = min(m0["olcu_cm"]), min(m["olcu_cm"])
        if dar < dar0 - 1e-6 and dar + 1e-6 < float(r.get("dar_kenar_cm", 0)):
            raise GermeHatasi(f"{m['ad']} dar kenarda {dar:.0f} cm kalır ({ad_} için en az {r['dar_kenar_cm']} cm)")
    kol = float((kural.get("kol_en_az_cm") or {}).get("deger", 0) or 0)
    if kol:
        y1 = _kur(t_once)
        for ad, b2 in y2["bolgeler"].items():
            b1 = y1["bolgeler"].get(ad)
            if b1 is None or b2["sinif"] in ("dis", "veranda"):
                continue
            dar2 = b2["net"].difference(b2["net"].buffer(-kol / 2, join_style=2).buffer(kol / 2, join_style=2)).area
            dar1 = b1["net"].difference(b1["net"].buffer(-kol / 2, join_style=2).buffer(kol / 2, join_style=2)).area
            if dar2 > 500 and dar2 > dar1 + 100:
                raise GermeHatasi(f"{ad} içinde {kol:g} cm'den dar bir kol kalıyor")
    # yapım ayrıntıları (oda kurallarından sonra: bayinin önce oda gerekçesini okuması için)
    yeni_ortusme = sorted(_ortusen_acikliklar(t_sonra) - _ortusen_acikliklar(t_once))
    if yeni_ortusme:
        a, b = yeni_ortusme[0]
        raise GermeHatasi(f"{_aciklik_sozu(t_sonra, a)} ile {_aciklik_sozu(t_sonra, b)} aynı duvarda üst üste biniyor")
    yeni_kisa = sorted(_kisa_parcalar(t_sonra) - _kisa_parcalar(t_once))
    if yeni_kisa:
        raise GermeHatasi(f"duvarlar arasında {yeni_kisa[0][1]:g} cm'lik bir kırık çıkıyor (çelikte {KISA_PARCA_CM} cm ve daha kısa parça yapılmaz)")
    try:                                                       # en son: yükleme listesinin girdisi, kanalın ürettiği gibi (`worker`: yöntem panel)
        with MK.secili(set_yolu):
            kur = MK.oku()
            tl = copy.deepcopy(t_sonra)
            tl["cati"]["yontem"] = "panel"
            yl = yapi.kur(tl)
            cl = cati_genel.cati_kur(tl["cati"], kur)
            girdi_genel.girdi(yl, cl, girdi_genel.metraj(yl, cl, kur), kur, "germe hakemi")
    except (SystemExit, ValueError, KeyError):
        raise GermeHatasi("bu modelin çelik listesi değişen ölçülere otomatik uyarlanamıyor") from None
    return k2


def _yapi_nedeni(e: str, t: dict) -> str:
    """`yapi.kur` / `aciklik_denetimi` hatası → bayinin okuyacağı gerekçe."""
    ac = {a.get("ad"): a for a in t.get("acikliklar") or []}
    m = re.search(r"Açıklık duvarın dışına taşıyor: (\S+)", e) or re.search(r"\((\w+), [\d.,]+ cm\)", e)
    if m and m.group(1) in ac:
        a = ac[m.group(1)]
        mahaller = {x["ad"] for x in t.get("mahaller") or []}
        sahibi = a.get("mahal") if a.get("mahal") in mahaller else a.get("not") if a.get("not") in mahaller else ""
        if a.get("tur") == "pencere":
            return f"{(sahibi + ' ') if sahibi else ''}penceresi yeni duvar düzenine sığmıyor"
        return f"{(sahibi + ' ') if sahibi else ''}{'kapısı' if sahibi else 'bir kapı'} yeni duvar düzenine sığmıyor"
    if "çevrili değil" in e or "Adı verilmemiş" in e or "aynı bölgeyi" in e:
        return "odaların duvarları kapanmıyor"
    return re.sub(r"^tanım geçersiz: ", "", e)[:160]


# ── kilitli kenarın bayiye gerekçesi ─────────────────────────────────────────────────────────────────────────────────────
def _kilit_nedeni(e: dict, mahal: str, yon: str) -> str:
    n = e.get("neden") or ""
    if n.startswith("verandaya bakan"):
        return f"{mahal} {YAN_SOZU[yon]} yanında verandaya bakıyor; veranda ve çatısı otomatik değişmiyor"
    if n.startswith("verandanın kenarı"):
        return "veranda ve çatısı otomatik değişmiyor"
    if "verandayı da keser" in n:
        return f"{YON_SOZU[yon]} büyürken veranda da değişirdi; veranda ve çatısı otomatik değişmiyor"
    if n.startswith("ana çatının"):
        return f"{YON_SOZU[yon]} büyümek ana çatının genişliğini ve mahya yüksekliğini değiştirir; bu otomatik yapılmıyor"
    m = re.match(r"karşıdaki (.+?) bu kenarın ötesinde (.+?) yanında devam ediyor", n)
    if m:
        oteki = ", ".join({"dis": "dış cephe"}.get(x, x) for x in m.group(2).split(", "))       # iç kod bayiye gitmez
        return f"duvarın öbür yanındaki {m.group(1)} aynı hizada {oteki} yanında da devam ediyor; duvar kayarsa o da değişirdi"
    if n.startswith("kenarın arkasında birden çok"):
        return f"odanın {YAN_SOZU[yon]} yanında hem dış duvar hem başka oda var"
    if n.startswith("kenarın arkası yok"):
        return f"odanın {YAN_SOZU[yon]} yanında duvar yerine baca ya da kolon var"
    if n.startswith("mahalin içinden kesit"):
        return "odanın içinden kesit geçecek boş yer yok (kapı, pencere ya da duvar var)"
    return re.sub(r"\s*\(İE-[^)]*\)", "", n)


# ── işlem ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def oda_degistir(t: dict, mahal: str | None, yon: str | None, cm, buyut: bool = True, set_yolu=None) -> tuple[dict, dict]:
    """Mahalin `yon` yanını cm kadar dışarı (büyüt) ya da içeri (küçült) alır. Dönen: (yeni tanım, rapor). Hata: `GermeHatasi`.
    `set_yolu`: kimliğin alan ölçüsünün kural seti (rapordaki m²; geometri ondan bağımsız); verilmezse güncel kitap."""
    try:
        cm = int(cm) if cm is not None and float(cm) == int(float(cm)) else None
    except (TypeError, ValueError):
        cm = None
    if cm is None or not (CM_ARALIK[0] <= cm <= CM_ARALIK[1]):
        raise GermeHatasi(f"ölçü {CM_ARALIK[0]}–{CM_ARALIK[1]} cm arasında tam sayı olmalı")
    if yon not in ISARET:
        raise GermeHatasi("yön ön, arka, sol ya da sağ olmalı")
    tm = {m["ad"]: m for m in t["mahaller"]}
    if mahal not in tm:
        raise GermeHatasi(f"planda {mahal} adlı oda yok")
    if tm[mahal].get("sinif") == "veranda":
        raise GermeHatasi("veranda ve çatısı otomatik değişmiyor")
    y = _kur(t)
    k1 = YK.tanimdan(t, set_yolu)
    kenarlar = [e for e in k1["parametrik"]["kenarlar"] if e["mahal"] == mahal and e["yon"] == yon]
    if not kenarlar:
        raise GermeHatasi(f"{mahal} odasının {YAN_SOZU[yon]} yanı bulunamadı")
    # Yanın en dıştaki kenarları karar verir. Dışa bakıyorsa ev o yöne uzar: kesit mahalin içinden geçer, beride kalan iç girinti
    # (L odanın öbür kolu, verandaya bakan geri çekik yüz) kesitin berisinde kalır ya da bütünüyle kayar, biçimi değişmez. İç kenarda
    # yanın bütün duvarları birlikte kayar (L odada iki duvar).
    uc = [e for e in kenarlar if e["en_dis"]]
    if {e["tur"] for e in uc} == {YK.DIS}:
        kullanilan, islem = uc, _germe
    elif {e["tur"] for e in kenarlar} == {"ic"}:
        kullanilan, islem = kenarlar, _kayma
    else:
        kilitli = [e for e in uc if e["durum"] == "kilitli"]
        if kilitli:
            raise GermeHatasi(_kilit_nedeni(kilitli[0], mahal, yon))
        raise GermeHatasi(f"odanın {YAN_SOZU[yon]} yanında hem dış duvar hem başka oda var")
    kilitli = [e for e in kullanilan if e["durum"] == "kilitli"]
    if kilitli:
        raise GermeHatasi(_kilit_nedeni(kilitli[0], mahal, yon))
    t2, rapor = islem(t, y, k1, mahal, yon, kullanilan, cm, buyut)
    if t2.get("celik_modeli"):                                 # SKP karkas modeli gerilmiş eve uymaz: karkas kuraldan (TASLAK)
        t2.pop("celik_modeli")
        t2["karkas"] = "kural"
        rapor["karkas_kurala"] = True
    k2 = denetle(t, t2, k1, set_yolu)
    once = {m["ad"]: m for m in k1["anlamsal"]["mahaller"]}
    yeni = next(m for m in k2["anlamsal"]["mahaller"] if m["ad"] == mahal)
    if (yeni["alan_m2"] - once[mahal]["alan_m2"]) * (1 if buyut else -1) <= 0:
        raise GermeHatasi(f"{mahal} {'büyümüyor' if buyut else 'küçülmüyor'}")
    degisen = {}
    for m in k2["anlamsal"]["mahaller"]:
        m0 = once.get(m["ad"])
        if m0 and abs(m["alan_m2"] - m0["alan_m2"]) >= 0.005:
            degisen[m["ad"]] = [m0["alan_m2"], m["alan_m2"]]
    for m in t2["mahaller"]:
        if m["ad"] in degisen:
            m.pop("etiket_m2", None)
    if rapor.get("kayan_acikliklar"):                         # kayan kapı ve pencere bayiye yazılır (K21): ad, kaç cm, hangi yöne
        iliski = _aciklik_iliskisi(k2)
        kyon = {("x", True): "D", ("x", False): "B", ("y", True): "K", ("y", False): "G"}[(rapor["eksen"], rapor["kayma_cm"] > 0)]
        rapor["kayan_acikliklar"] = [{"ad": a, "tur": iliski.get(a, ("açıklık", ()))[0],
                                      "mahaller": [x for x in iliski.get(a, ("", ()))[1] if x != YK.DIS],
                                      "cm": abs(rapor["kayma_cm"]), "yon": kyon} for a in rapor["kayan_acikliklar"]]
    rapor.update(mahal=mahal, yon=yon, cm=cm, buyut=buyut, degisen=degisen,
                 dis_olcu=[k1["anlamsal"]["dis_olcu_cm"], k2["anlamsal"]["dis_olcu_cm"]],
                 kapali_m2=[k1["anlamsal"]["kapali_m2"], k2["anlamsal"]["kapali_m2"]])
    return t2, rapor


def uygula(t: dict, d: dict) -> dict:
    """`varyant.tanim_uygula`'nın `oda_buyut` / `oda_kucult` kolu."""
    t2, _ = oda_degistir(t, d.get("mahal"), d.get("yon"), d.get("cm"), buyut=d.get("op") == "oda_buyut")
    return t2


def kisa_anlatim(rapor: dict) -> str:
    """Uygulanan işlem (bayi mesajındaki "Uygulanan", önce–sonra görselinin başlığı, PDF açıklaması): "Yatak Odası 1 arkaya 50 cm büyütüldü"."""
    return f"{rapor['mahal']} {YON_SOZU[rapor['yon']]} {rapor['cm']} cm {'büyütüldü' if rapor['buyut'] else 'küçültüldü'}"


def anlatim(rapor: dict) -> str:
    """Kodun hesapladığı fark (bayi mesajı): germede "ev arkaya 50 cm uzadı (uzayan öteki odalar: …); kapalı alan 87,27 → 93,37 m²",
    kaymada "Mutfak 10,05 → 10,82 m²; Yatak Odası 1 12,74 → 11,97 m²" ve kayan kapı ya da pencere ("… arasındaki kapı 30 cm öne kaydı")."""
    mahal, yon, cm, buyut = rapor["mahal"], rapor["yon"], rapor["cm"], rapor["buyut"]
    deg = rapor.get("degisen") or {}
    if rapor["tur"] == "germe":
        obur = [m for m in sorted(deg) if m != mahal]
        ev = f"ev {YON_SOZU[yon]} {cm} cm {'uzadı' if buyut else 'kısaldı'}"
        if obur:
            ev += f" ({'uzayan' if buyut else 'kısalan'} öteki odalar: {', '.join(obur)})"
        k0, k1 = rapor["kapali_m2"]
        return f"{ev}; kapalı alan {_tr(k0)} → {_tr(k1)} m²"
    sira = [mahal] + [m for m in sorted(deg) if m != mahal]
    parca = [f"{m} {_tr(deg[m][0])} → {_tr(deg[m][1])} m²" for m in sira if m in deg]
    for a in rapor.get("kayan_acikliklar") or []:
        parca.append(f"{_aciklik_adi(a)} {a['cm']:g} cm {YON_SOZU[a['yon']]} kaydı")
    return "; ".join(parca)


def _aciklik_adi(a: dict) -> str:
    """Kayan açıklığın bayiye adı: "Hol ile Yatak Odası 1 arasındaki kapı", "Banyo penceresi", "Hol dış kapısı"."""
    m = a.get("mahaller") or []
    if a.get("tur") == "pencere":
        return f"{m[0]} penceresi" if m else "bir pencere"
    if a.get("tur") == "kapı":
        return f"{m[0]} ile {m[1]} arasındaki kapı" if len(m) == 2 else f"{m[0]} dış kapısı" if m else "bir kapı"
    return "bir açıklık"


def istek_sozu(d: dict) -> str:
    """Uygulanamayan isteğin bayiye anılışı: "Salon - Mutfak sağa 50 cm büyütme"."""
    return f"{d.get('mahal')} {YON_SOZU.get(d.get('yon'), '')} {d.get('cm')} cm {'büyütme' if d.get('op') == 'oda_buyut' else 'küçültme'}".replace("  ", " ")
