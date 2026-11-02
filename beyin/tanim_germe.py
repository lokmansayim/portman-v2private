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
  bayinin okuyacağı Türkçeyle (K21: sessiz düşme yok).
- **Düzey 2 (PR-2b): kesit cumba ya da çıkma çatısından geçer.** Kesit küçük çatının saçak taşıyan duvarları arasında; olabiliyorsa ortanın
  iki yanında iki yarım kesit (pencere ortada kalır), olmuyorsa tek kesit (ortadaki açıklık yeni ortaya kayar). Sırt saçakların ortasına,
  tepe ana düzlemle kesişimden yeniden hesaplanır; tepe ana mahyayı aşarsa yapılmaz.

Hakem (`denetle`): `yapi.kur` + `aciklik_denetimi` (varyant), aynı duvarda açıklık örtüşmesi, açıklık kenarının birleşen duvara en az 10 cm
uzaklığı (`plan_derle` payı) ve 15 cm parça (D-10) (üçü de yalnız yeni çıkan),
`cati_genel.cati_kur`, metraj (kimlik), yükleme listesinin girdisi (`girdi_genel.girdi`, yöntem panel), açıklık–mahal ilişkisi değişmez
(her kapı aynı iki mahal arasında, her pencere aynı mahalde), değişen mahallerde oda en küçükleri (`kurallar/plan/oda_kurallari.json`:
net m², dar kenar, kol; yalnız kötüleşen ölçü), çatı (`_cati_hakemi`: yüzlerin birleşimi, saçak taşması, mahyanın ortasındaki açıklık, vadideki
makas ucu değişmez). Karkas modeli (`celik_modeli`, SKP) gerilmiş eve uymaz: karkas kurala geçer
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
KUCULT_SOZU = {"G": "önden", "K": "arkadan", "B": "soldan", "D": "sağdan"}   # küçültmede yan: "Mutfak arkadan 30 cm küçültüldü"
YAN_SOZU = {"G": "ön", "K": "arka", "B": "sol", "D": "sağ"}
CM_ARALIK = (5, 300)                                       # `plan_islem.Islem.cm` ile aynı
KISA_PARCA_CM = 15                                         # D-10: çelikte 15 cm (ve daha kısa) parça çıkmaz
AYAK_CM = 10                                               # açıklık kenarı birleşen duvarın karkas yüzünden (`plan_derle` PAY_KOSE, PAY_BIRLESIM)
KOSE_CM = 50                                               # köşeye bağlı açıklık: kayan duvarın yüzüne bu kadar yakın kenarlı açıklık duvarla
                                                           # birlikte kayar (Lokman 31.10: büyüyen odanın kapısı da kayar). Banka modellerinde köşe
                                                           # açıklıkları 5–44 cm, ortadakiler 60 cm'den başlar
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


class _Bilesik:
    """İki dönüşüm art arda (düzey 2'de sırtın iki yanındaki iki kesit)."""

    def __init__(self, f1, f2):
        self.f1, self.f2 = f1, f2
        self.eksen, self.i, self.buyut, self.c = f1.eksen, f1.i, f1.buyut, f1.c

    def __call__(self, v, ne: str = "öğe", serbest: bool = False):
        return self.f2(self.f1(v, ne, serbest), ne, serbest)

    def nokta(self, p: list, ne: str = "öğe", serbest: bool = False) -> list:
        return self.f2.nokta(self.f1.nokta(p, ne, serbest), ne, serbest)


def _makas_dizisi(aile: dict, f: _Donusum, ad: str, ikincil: bool = False) -> None:
    """Makas ailesi: `x` ve `y` listeleri (biri açıklık, öbürü makas yerleri; `eksen` varsa makasın uzandığı eksen). Kesit ekseninin
    listesi dönüşür. O liste makas yerleriyse ve bir aralık tanımdaki en büyük aralığı aştıysa araya eşit aralıkla makas eklenir;
    küçültmede şeritte kalan makas çıkar, kesitte tanımdaki en küçük aralıktan yakın kalan iki makastan kesite yakın olanı da çıkar.
    `ikincil` (düzey 2 kesiti): açıklığı kesiti kesen makas ikincil çatınındır (cumba, çıkma); açıklığı kesitle birlikte uzar."""
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
        if len(eski) >= 2 and min(eski) < f.c < max(eski) and f.buyut and not ikincil:
            raise GermeHatasi("kesit bir çatı makasını boyuna kesiyor (çatı eğimi kesit yönünde)")
        aile[k] = [f(v, "bir çatı makası") for v in aile[k]]
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


def _donustur(t: dict, f: _Donusum, y: dict, ikincil: bool = False) -> dict:
    """Tanımdaki eksen koordinatlarını dönüştürür (kopya). Kesiti kesen duvar ve kiriş uzar (küçültmede kısalır)."""
    t2 = copy.deepcopy(t)
    i = f.i
    for d in t2["duvarlar"]:
        w = y["adli"][d["ad"]]
        a, b = d["kutu"][i], d["kutu"][i + 2]
        kesiyor = (a < f.c - TOL and b > f.c + TOL) if f.buyut else (a <= f.lo + TOL and b >= f.hi - TOL)
        if kesiyor:
            if w["sinif"] not in KESIT_DUVAR_SINIFLARI or w["yon"] != f.eksen:
                raise GermeHatasi("kesit bir duvarın içinden geçiyor")
            if isinstance(d.get("yukseklik"), dict):
                raise GermeHatasi("kesit üstü eğimli bir duvardan geçiyor; eğimli duvar otomatik uzatılamaz")
        d["kutu"][i], d["kutu"][i + 2] = f(a, "bir duvarın ucu"), f(b, "bir duvarın ucu")
    for ac in t2.get("acikliklar") or []:
        if y["adli"][ac["duvar"]]["yon"] != f.eksen:
            continue
        b0, b1 = f(ac["bas"], "bir kapı ya da pencere"), f(ac["bas"] + ac["en"], "bir kapı ya da pencere")
        if abs(float(b1) - float(b0) - ac["en"]) > TOL:
            raise GermeHatasi("kesit bir kapı ya da pencereden geçiyor")
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
        kr["kutu"][i], kr["kutu"][i + 2] = f(kr["kutu"][i], "bir kiriş"), f(kr["kutu"][i + 2], "bir kiriş")
        if uzun == f.eksen:
            kr["acik"] = [[f(a, "bir kiriş"), f(b, "bir kiriş")] for a, b in kr.get("acik") or []]
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
            _makas_dizisi(aile, f, ad, ikincil)
    el = (t2.get("elektrik") or {}).get("sigorta_kutusu")
    if isinstance(el, list) and len(el) == 2:
        t2["elektrik"]["sigorta_kutusu"] = f.nokta(el, "sigorta kutusu", serbest=True)
    return t2


# ── düzey 2: ikincil çatı (cumba, çıkma) yeniden hesaplanır ─────────────────────────────────────────────────────────────────
def _ikincil_cati(t0: dict, t2: dict, f: _Donusum, dik: list[str]) -> list[str]:
    """Kesitin dik kestiği ikincil çatı düzlemleri (sırtı kesit eksenine dik iki yüzlü cumba ya da çıkma) gerilmiş tanımda yeniden kurulur:
    iki yüzün saçakları dönüşümle yerini aldı; sırt iki saçağın ortasına gelir (yüzler aynı eğimde ve aynı saçak kotunda, sırt tanımda
    ortada olmalı). Sırtın ana çatıya oturan ucu (vadilerin buluştuğu tepe) düzlemlerin kesişiminden yeniden hesaplanır; ana çatının
    o köşesi de oraya taşınır. Dönen: yeniden kurulan parçaların düzlem adları. Uymayan biçimde `GermeHatasi`."""
    from shapely.geometry import Polygon
    i, ek = f.i, f.eksen
    j, ej = 1 - f.i, ("y" if f.eksen == "x" else "x")
    D0 = {d["ad"]: d for d in t0["cati"]["duzlemler"]}
    D2 = {d["ad"]: d for d in t2["cati"]["duzlemler"]}
    yon = {ad: float((d.get("yukari") or [0, 0])[i]) for ad, d in D0.items()}
    kalan, yapilan, sirtlar = list(dik), [], {}
    while kalan:
        a = kalan.pop(0)
        es = None
        for b in D0:                                           # eşi: zıt yöne yükselen, sırtı ortak yüz (kesit onu kesmeyebilir)
            if b == a or b in yapilan or yon[a] * yon[b] >= 0:
                continue
            ortak = Polygon(D0[a]["plan"]).boundary.intersection(Polygon(D0[b]["plan"]).boundary)
            if ortak.length > 1:
                es = b
                break
        if es is None:
            raise GermeHatasi("küçük çatının iki yüzü bulunamadı; otomatik hesaplanamıyor")
        if es in kalan:
            kalan.remove(es)
        art, aza = (a, es) if yon[a] > 0 else (es, a)          # art: eksen boyunca yükselen yüz (saçağı alt yanda)
        A0, B0 = D0[art], D0[aza]
        if A0.get("egim") != B0.get("egim") or A0.get("sacak_kotu") != B0.get("sacak_kotu") or \
                not all(isinstance(d.get("sacak"), dict) and ek in d["sacak"] for d in (A0, B0)):
            raise GermeHatasi("küçük çatının iki yüzü aynı eğimde değil; otomatik hesaplanamıyor")
        ortak = Polygon(A0["plan"]).boundary.intersection(Polygon(B0["plan"]).boundary)
        xb = ortak.bounds
        sirt0 = xb[i]
        sa0, sb0 = float(A0["sacak"][ek]), float(B0["sacak"][ek])
        if abs(xb[i + 2] - sirt0) > TOL or abs(sirt0 - (sa0 + sb0) / 2) > 1.0:
            raise GermeHatasi("küçük çatının sırtı ortada değil; otomatik hesaplanamıyor")
        sa2, sb2 = float(D2[art]["sacak"][ek]), float(D2[aza]["sacak"][ek])
        sirt_t = float(f(sirt0, "küçük çatının sırtı") if f.buyut else _sirt_donusumu(f, sirt0))
        sirt2 = round((sa2 + sb2) / 2, 2)
        sirtlar[(round(sirt0, 1), "")] = sirtlar.get((round(sirt0, 1), ""), []) + [sirt2]
        yapilan += [art, aza]
        if abs(sirt2 - sirt_t) < 0.005 and abs((sb2 - sa2) - (sb0 - sa0)) < 0.005:
            continue                                           # parça ne genişledi ne kaydı (yalnız ötelendi)
        egim, kot = float(A0["egim"]), float(A0["sacak_kotu"])
        tepe0, tepe2 = kot + egim * (sirt0 - sa0), kot + egim * (sirt2 - sa2)
        for uc in (xb[j], xb[j + 2]):                          # sırtın iki ucu; ana çatıya oturan uç (başka düzlemin köşesi) tepe olur
            yeni_uc = uc
            for d in t2["cati"]["duzlemler"]:
                if d["ad"] in (art, aza) or abs(yon[d["ad"]]) > 1e-9:  # tepe: eğimi kesit ekseninde olmayan (ana çatının) düzlemde
                    continue
                if not any(abs(p[i] - sirt_t) < TOL and abs(p[j] - uc) < TOL for p in d["plan"]):
                    continue
                M = D0[d["ad"]]
                sm = float((M.get("yukari") or [0, 0])[j])
                if not (isinstance(M.get("sacak"), dict) and ej in M["sacak"]) or abs(sm) < 1e-9 or not M.get("egim"):
                    raise GermeHatasi("küçük çatının ana çatıya oturduğu yer otomatik hesaplanamıyor")
                y_s, em, km = float(M["sacak"][ej]), float(M["egim"]), float(M["sacak_kotu"])
                if abs(y_s + (tepe0 - km) / (em * sm) - uc) > 1.5:
                    raise GermeHatasi("küçük çatının vadileri tanımla uyuşmuyor; otomatik hesaplanamıyor")
                yeni_uc = round(y_s + (tepe2 - km) / (em * sm), 2)
                ust = [p[j] for p in Polygon(d["plan"]).exterior.coords]
                if not (min(ust) + 1 < yeni_uc < max(ust) - 1):
                    raise GermeHatasi("küçük çatı büyüyünce ana çatının mahyasını aşıyor")
            for d in t2["cati"]["duzlemler"]:
                for k in ("plan", "karkas"):
                    for p in d.get(k) or []:
                        if abs(p[i] - sirt_t) < TOL and abs(p[j] - uc) < TOL and (d["ad"] in (art, aza) or yeni_uc != uc):
                            p[i], p[j] = _sayi(sirt2, p[i]), _sayi(yeni_uc, p[j])
        for d in (D2[art], D2[aza]):                           # sırt boyunca öteki köşeler
            for k in ("plan", "karkas"):
                for p in d.get(k) or []:
                    if abs(p[i] - sirt_t) < TOL:
                        p[i] = _sayi(sirt2, p[i])
    for v in sirtlar.values():                                 # aynı hizadaki sırtlar (cumba ve önündeki çıkma) hizada kalır
        if max(v) - min(v) > 0.5:
            raise GermeHatasi("kesit küçük çatıyla önündeki çıkma çatısını farklı geriyor")
    return yapilan


def _ortada_tut(t0: dict, t2: dict, f, eksen: str, parcalar, aralik: tuple[float, float]) -> list[list]:
    """Tek kesitli düzey 2: küçük çatı tek yandan genişler, sırtı yeni ortaya (cm/2) gider. Eski ortasında duran açıklık (cumbanın alnındaki
    pencere: kesit eksenindeki dış duvarda, ortası taşıyıcı duvarların ortasında, ±2 cm) yeni ortaya kayar (hakem ortada kaldığını ayrıca
    denetler). İç duvardaki açıklık çatıya bağlı değildir, kaymaz. Dönen: [[ad, kayma (cm, işaretli)]]."""
    i = 0 if eksen == "x" else 1
    j = 1 - i
    a0, a1 = aralik
    m0, m1 = (a0 + a1) / 2, (float(f(a0)) + float(f(a1))) / 2
    adli = {d["ad"]: d for d in t0["cati"]["duzlemler"]}
    noktalar = [p for ad in parcalar if ad in adli for p in adli[ad]["plan"]]
    if not noktalar or abs(m1 - m0) < TOL:
        return []
    lo, hi = min(p[j] for p in noktalar) - 60, max(p[j] for p in noktalar) + 60
    duvar0 = {d["ad"]: d["kutu"] for d in t0["duvarlar"] if d.get("sinif") == "dis"}
    out = []
    for a0_, a2 in zip(t0["acikliklar"], t2["acikliklar"]):
        k = duvar0.get(a0_["duvar"])
        if k is None or (k[i + 2] - k[i]) < (k[j + 2] - k[j]) or not (lo <= (k[j] + k[j + 2]) / 2 <= hi):
            continue
        if abs(float(a0_["bas"]) + float(a0_["en"]) / 2 - m0) > 2.0:
            continue
        kay = round(m1 - (float(a2["bas"]) + float(a2["en"]) / 2), 2)
        if abs(kay) >= TOL:
            a2["bas"] = _sayi(float(a2["bas"]) + kay, a2["bas"])
            out.append([a2["ad"], kay])
    return out


def _ikincil_aralik(t: dict, y: dict, eksen: str, dik: list[str]) -> tuple[float, float, frozenset]:
    """Düzey 2 kesitinin konabileceği aralık: kestiği her ikincil çatı yüzünün saçağını taşıyan duvar kesitin saçakla aynı yanında kalır
    (saçak taşması değişmez). Yüzün altındaki, kesit eksenine dik duvarlardan saçağa en yakını taşıyıcıdır. Dönen: (alt, üst, yeniden
    kurulacak yüzlerin hepsi)."""
    from shapely.geometry import Polygon
    i = 0 if eksen == "x" else 1
    j = 1 - i
    D = {d["ad"]: d for d in t["cati"]["duzlemler"]}
    lo, hi = -math.inf, math.inf
    tum = set(dik)
    for ad in dik:                                             # kesitin kesmediği öbür yüz de (ikisi birlikte yeniden kurulur)
        yk = float((D[ad].get("yukari") or [0, 0])[i])
        for b, d in D.items():
            if b not in tum and yk * float((d.get("yukari") or [0, 0])[i]) < 0 and \
                    Polygon(D[ad]["plan"]).boundary.intersection(Polygon(d["plan"]).boundary).length > 1:
                tum.add(b)
    for ad in sorted(tum):
        d = D[ad]
        if not (isinstance(d.get("sacak"), dict) and eksen in d["sacak"]):
            raise GermeHatasi("küçük çatının saçağı tanımda yok; otomatik hesaplanamıyor")
        sac = float(d["sacak"][eksen])
        b = Polygon(d["plan"]).bounds
        p0, p1, q0, q1 = b[i], b[i + 2], b[j], b[j + 2]
        tasiyan = None
        for w in t["duvarlar"]:
            k = w["kutu"]
            if w.get("sinif") not in KESIT_DUVAR_SINIFLARI or y["adli"][w["ad"]]["yon"] == eksen:
                continue
            if k[j + 2] <= q0 + TOL or k[j] >= q1 - TOL or k[i + 2] <= p0 - TOL or k[i] >= p1 + TOL:
                continue
            uzak = abs((k[i] + k[i + 2]) / 2 - sac)
            if tasiyan is None or uzak < tasiyan[0]:
                tasiyan = (uzak, k)
        if tasiyan is None:
            raise GermeHatasi("küçük çatının saçağı altında duvar yok; otomatik hesaplanamıyor")
        k = tasiyan[1]
        if sac <= k[i]:                                        # saçak alt yanda: kesit taşıyıcının üst yüzünün ötesinde
            lo = max(lo, k[i + 2])
        else:
            hi = min(hi, k[i])
    return lo, hi, frozenset(tum)


def _sirt_donusumu(f: _Donusum, v: float) -> float:
    """Küçültmede sırt şeritte kalabilir: şeridin kayan yanındaysa kayar, şeritteyse kesite iner (yeniden hesaplanacak)."""
    return float(f(v, "küçük çatının sırtı", serbest=True))


# ── dış kenar: germe ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _germe(t: dict, y: dict, kimlik: dict, mahal: str, yon: str, kenarlar: list[dict], cm: int, buyut: bool) -> tuple[dict, dict]:
    eksen, s = YK.YON_EKSEN[yon], ISARET[yon]
    duzey = 2 if any(e["durum"] == "duzey2" for e in kenarlar) else 1   # düzey 2: ikincil çatı (cumba, çıkma) yeniden hesaplanır
    konum = [e["konum_cm"] for e in kenarlar]
    sinir = min(konum) if s > 0 else max(konum)               # kesit, kenarın berisinde (mahalin içinde)
    serit = 0.0 if buyut else float(cm)
    sinif = {m["ad"]: m["sinif"] for m in kimlik["anlamsal"]["mahaller"]}
    adaylar, on_hata, merkez, aralik = [], [], {}, {}
    for g in kimlik["parametrik"]["germe"][eksen]:
        if mahal not in g["mahaller"] or g["duzey"] != duzey or any(sinif.get(m) == "veranda" for m in g["mahaller"]):
            continue
        lo, hi = g["aralik"]
        if duzey == 2:                                         # saçak taşmaları değişmesin: kesit küçük çatıların taşıyıcı duvarları arasında
            try:
                a0, a1, parcalar = _ikincil_aralik(t, y, eksen, g["dik"])
            except GermeHatasi as e:
                on_hata.append(str(e))
                continue
            lo, hi = max(lo, a0 + YK.KESIT_PAYI), min(hi, a1 - YK.KESIT_PAYI)
            merkez[id(g)] = (parcalar, (a0 + a1) / 2)          # küçük çatının yüzleri ve ortası (sırt; iki yandaki taşıyıcı duvarların arası)
            aralik[id(g)] = (a0, a1)
        hi = min(hi, sinir) if s > 0 else hi
        lo = max(lo, sinir) if s < 0 else lo
        if hi - lo < serit - TOL or hi - lo < 0:
            continue
        orta = (lo + hi) / 2
        adaylar.append((len(g["mahaller"]), -(hi - lo), abs(sinir - orta), lo, hi, g))
    if not adaylar:
        if on_hata:
            raise GermeHatasi(on_hata[0])
        raise GermeHatasi("odanın içinden kesit geçecek boş yer yok" + (f" ({cm} cm genişliğinde)" if not buyut else ""))
    hatalar = []
    if duzey == 2:                                             # küçük çatı ortasından simetrik genişler: sırtın iki yanında birer kesit, cm/2
        for parcalar, m in sorted(set(merkez.values()), key=lambda v: (-len(v[0]), sorted(v[0]))):
            yan = [[a for a in adaylar if merkez[id(a[5])][0] == parcalar and (a[4] <= m + TOL if k == 0 else a[3] >= m - TOL)
                    and a[4] - a[3] >= (0.0 if buyut else cm / 2) - TOL] for k in (0, 1)]
            if not all(yan):
                continue
            secilen = [min(v, key=lambda a: (-(a[4] - a[3]), a[3])) for v in yan]
            try:
                t2, f, kesitler = t, None, []
                for _, _, _, lo, hi, g in secilen:
                    orta = (lo + hi) / 2
                    c = round(orta if buyut else orta - s * cm / 4, 2)
                    c = float(f(c)) if f is not None else c
                    fk = _Donusum(eksen, s, cm / 2, buyut, c)
                    t2 = _donustur(t2, fk, y, ikincil=True)
                    f = fk if f is None else _Bilesik(f, fk)
                    kesitler.append(c)
                ikincil = _ikincil_cati(t, t2, f, sorted({x for a in secilen for x in a[5]["dik"]}))
            except GermeHatasi as e:
                hatalar.append(str(e))
                continue
            return t2, {"tur": "germe", "eksen": eksen, "kesit_cm": kesitler, "mahaller": sorted({x for a in secilen for x in a[5]["mahaller"]}),
                        "ikincil_cati": ikincil}
    for _, _, _, lo, hi, g in sorted(adaylar, key=lambda a: a[:4]):
        orta = round((lo + hi) / 2, 1)
        c = orta if buyut else round(orta - s * cm / 2, 1)     # küçültmede şerit [c, c + s·cm] bandın ortasında
        try:
            f = _Donusum(eksen, s, cm, buyut, c)
            t2 = _donustur(t, f, y, ikincil=duzey == 2)
            ikincil = _ikincil_cati(t, t2, f, g["dik"]) if duzey == 2 else []
        except GermeHatasi as e:
            hatalar.append(str(e))
            continue
        r = {"tur": "germe", "eksen": eksen, "kesit_cm": c, "mahaller": list(g["mahaller"])}
        if ikincil:
            r["ikincil_cati"] = ikincil
            ortalanan = _ortada_tut(t, t2, f, eksen, merkez[id(g)][0], aralik[id(g)])
            if ortalanan:
                r["ortalanan_acikliklar"] = ortalanan
        return t2, r
    raise GermeHatasi(hatalar[0])


# ── iç kenar: duvar kayar ────────────────────────────────────────────────────────────────────────────────────────────────
def _ayak_obur(t: dict, ac: dict, w: list, i: int, j: int, haric: set[str]) -> float:
    """Açıklığın, bulunduğu duvara (kutusu `w`, `i` ekseni boyunca uzanır) değen öteki duvarların (`haric` dışındakiler) karkas yüzüne en
    yakın uzaklığı (cm, iki yanda da). `_ayaklar` ile aynı ölçü."""
    a0, a1 = float(ac["bas"]), float(ac["bas"]) + float(ac["en"])
    en_az = math.inf
    for d in t["duvarlar"]:
        q = d["kutu"]
        if d["ad"] == ac["duvar"] or d["ad"] in haric or d.get("sinif") not in KESIT_DUVAR_SINIFLARI or q[j + 2] < w[j] - TOL or q[j] > w[j + 2] + TOL:
            continue
        g = a0 - q[i + 2] if q[i + 2] <= a0 + TOL else q[i] - a1 if q[i] >= a1 - TOL else 0.0
        en_az = min(en_az, max(g, 0.0))
    return en_az


def _kayma(t: dict, y: dict, kimlik: dict, mahal: str, yon: str, kenarlar: list[dict], cm: int, buyut: bool) -> tuple[dict, dict]:
    eksen, s = YK.YON_EKSEN[yon], ISARET[yon]
    delta = s * cm * (1 if buyut else -1)
    i = 0 if eksen == "x" else 1
    j = 1 - i
    tasinan = sorted({d for e in kenarlar for d in e["duvarlar"]})
    ozgun = {d["ad"]: list(d["kutu"]) for d in t["duvarlar"]}
    for ad in tasinan:
        if y["adli"][ad]["yon"] == eksen or y["adli"][ad]["sinif"] != "ic":
            raise GermeHatasi("o yandaki duvar kaydırılamaz")
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
    # dik duvardaki açıklıklar duvarla birlikte kayar, köşeye uzaklıkları korunur; bayiye yazılır:
    # - yolundakiler (küçülen yanda, duvarın süpürdüğü şeritte);
    # - köşeye bağlı olanlar (iki yanda da: kenarı kayan duvarın yüzüne KOSE_CM'den yakın ve en yakın duvar o; Lokman 31.10: Ç8201'de
    #   yatak odası 2 öne büyüyünce kendi kapısı da kayar). Öbür ucundaki duvara daha yakın açıklık o köşeye bağlıdır, yerinde kalır;
    #   kayınca kendi duvarının dışına taşacak köşe açıklığı da yerinde kalır (yolundakinin taşması hakemde gerekçe olur)
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
            ayak = a0 - m[i + 2] if a0 >= m[i + 2] - TOL else m[i] - a1 if a1 <= m[i] + TOL else math.inf
            koseye_bagli = ayak <= KOSE_CM + TOL and ayak <= _ayak_obur(t, ac, w, i, j, set(tasinan)) + TOL
            if koseye_bagli and not yolda:                     # köşe kuralı açıklığı kendi duvarının dışına taşıyorsa açıklık yerinde kalır
                k2 = adli[ac["duvar"]]["kutu"]
                koseye_bagli = k2[i] - TOL <= a0 + delta and a1 + delta <= k2[i + 2] + TOL
            if yolda or koseye_bagli:
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


def _ayaklar(t: dict) -> dict[str, float]:
    """Açıklık adı → kenarından, bulunduğu duvara değen (birleşen ya da devam eden) en yakın duvarın karkas yüzüne uzaklık (cm, duvar
    boyunca). Açıklığın karşısına düşen duvar 0 verir."""
    duvar = {d["ad"]: d for d in t["duvarlar"]}
    out: dict[str, float] = {}
    for ac in t.get("acikliklar") or []:
        w = duvar.get(ac.get("duvar"))
        if w is None:
            continue
        k = w["kutu"]
        i = 0 if k[2] - k[0] >= k[3] - k[1] else 1
        j = 1 - i
        a0, a1 = float(ac["bas"]), float(ac["bas"]) + float(ac["en"])
        en_az = math.inf
        for d in t["duvarlar"]:
            q = d["kutu"]
            if d["ad"] == w["ad"] or d.get("sinif") not in KESIT_DUVAR_SINIFLARI or q[j + 2] < k[j] - TOL or q[j] > k[j + 2] + TOL:
                continue
            g = a0 - q[i + 2] if q[i + 2] <= a0 + TOL else q[i] - a1 if q[i] >= a1 - TOL else 0.0
            en_az = min(en_az, max(g, 0.0))
        out[ac["ad"]] = en_az
    return out


def _aciklik_sozu(t: dict, ad: str) -> str:
    ac = next((a for a in t.get("acikliklar") or [] if a.get("ad") == ad), {})
    mahaller = {m["ad"] for m in t.get("mahaller") or []}
    sahibi = ac.get("mahal") if ac.get("mahal") in mahaller else ac.get("not") if ac.get("not") in mahaller else ""
    if ac.get("giris"):
        return "giriş kapısı"
    ne = "penceresi" if ac.get("tur") == "pencere" else "kapısı"
    return f"{sahibi} {ne}" if sahibi else ("bir pencere" if ac.get("tur") == "pencere" else "bir kapı")


def _sacak_taskilari(t: dict) -> dict[str, tuple[str, float]]:
    """Her çatı yüzünün saçağının altındaki dış duvar ve taşma (cm): saçak çizgisine paralel, saçak boyunca yüzle örtüşen, taşması 0–100 cm
    olan en yakın dış duvar yüzü."""
    out = {}
    for d in t["cati"]["duzlemler"]:
        s, (yx, yy) = d.get("sacak") or {}, d["yukari"]
        if "x" in s and yx and not yy:
            i, v, yon = 0, float(s["x"]), 1 if yx > 0 else -1
        elif "y" in s and yy and not yx:
            i, v, yon = 1, float(s["y"]), 1 if yy > 0 else -1
        else:
            continue
        j = 1 - i
        lo, hi = min(p[j] for p in d["plan"]), max(p[j] for p in d["plan"])
        en_iyi = None
        for w in t["duvarlar"]:
            k = w["kutu"]
            if w.get("sinif") != "dis" or min(hi, k[j + 2]) - max(lo, k[j]) < 1:
                continue
            pay = ((k[i] if yon > 0 else k[i + 2]) - v) * yon
            if -TOL <= pay <= 100 and (en_iyi is None or pay < en_iyi[1]):
                en_iyi = (w["ad"], round(pay, 2))
        if en_iyi:
            out[d["ad"]] = en_iyi
    return out


def _sacak_payi(t: dict, duzlem: str, duvar: str) -> float | None:
    d = next((x for x in t["cati"]["duzlemler"] if x["ad"] == duzlem), None)
    w = next((x for x in t["duvarlar"] if x["ad"] == duvar), None)
    if d is None or w is None:
        return None
    s, (yx, yy) = d.get("sacak") or {}, d["yukari"]
    i, v, yon = (0, float(s["x"]), 1 if yx > 0 else -1) if "x" in s else (1, float(s["y"]), 1 if yy > 0 else -1)
    return ((w["kutu"][i] if yon > 0 else w["kutu"][i + 2]) - v) * yon


def _mahya_anahtari(e: dict) -> tuple:
    return tuple(sorted((round(float(e["p"][0]), 1), round(float(e["p"][1]), 1), round(float(e["q"][0]), 1), round(float(e["q"][1]), 1))))


def _mahya_altindakiler(t: dict, c: dict) -> dict[str, set]:
    """Bir mahyanın tam altında (ortasında, ±2 cm) duran açıklıklar ve altında durdukları mahyalar: dış duvarda, duvarı mahyaya dik,
    ortası mahyanın hizasında, duvarı mahyanın ucundan en çok 150 cm ötede (alın ya da cumba alnı)."""
    duvar = {w["ad"]: w["kutu"] for w in t["duvarlar"] if w.get("sinif") == "dis"}
    mahyalar = [e for e in c["kenarlar"] if e["tur"] == "mahya"]
    out: dict[str, set] = {}
    for a in t.get("acikliklar") or []:
        k = duvar.get(a.get("duvar"))
        if k is None:
            continue
        i = 0 if (k[2] - k[0]) >= (k[3] - k[1]) else 1          # duvarın uzandığı eksen
        orta, yer = float(a["bas"]) + float(a["en"]) / 2, (k[1 - i] + k[3 - i]) / 2
        for e in mahyalar:
            p, q = e["p"], e["q"]
            if abs(p[1 - i] - q[1 - i]) < 0.5:                  # mahya duvara paralel: alın değil
                continue
            if abs(p[i] - q[i]) < 0.5 and abs(orta - p[i]) <= 2.0 and min(p[1 - i], q[1 - i]) - 150 <= yer <= max(p[1 - i], q[1 - i]) + 150:
                out.setdefault(a["ad"], set()).add(_mahya_anahtari(e))
    return out


def _vadi_uclari(t: dict, c: dict) -> collections.Counter:
    """Makas ailelerinin vadiye oturan uç sayısı (aile başına; uç: açıklık listesinin iki ucu × makas yerleri)."""
    from shapely.geometry import LineString, Point
    vadiler = [LineString([e["p"], e["q"]]) for e in c["kenarlar"] if e["tur"] == "vadi"]
    out = collections.Counter()
    for ad, aile in ((t["cati"].get("makaslar") or {}).items()):
        e = aile.get("eksen") if isinstance(aile, dict) else None
        if e not in ("x", "y") or not isinstance(aile.get(e), list) or not isinstance(aile.get("y" if e == "x" else "x"), list):
            continue
        for u in (aile[e][0], aile[e][-1]):
            for v in aile["y" if e == "x" else "x"]:
                nokta = Point((u, v) if e == "x" else (v, u))
                if any(L.distance(nokta) < 1.0 for L in vadiler):
                    out[ad] += 1
    return out


def _cati_hakemi(t1: dict, c1: dict, t2: dict, c2: dict) -> None:
    """Çatı, öneren koddan bağımsız (Z-03; İE-23 PR-2b: düzey 2 küçük çatıyı yeniden kurar, hakem `cati_kur`un kurabildiği her çatıyı kabul
    ediyordu). Germe yüzleri eğimlerine paralel uzatır; şunlar değişmez:
    - yüzlerin birleşimi: kenar türleri (mahya, kırma, vadi, saçak, alın …) ve her birinin hangi yüzler arasında olduğu (kotu tutmayan iki
      yüz ortak kenar sayılmaz: tepe ya da sırt yanlış yerdeyse birleşim değişir);
    - her yüzün saçağının altındaki dış duvara taşması;
    - mahyanın ortasında duran açıklık (cumba alnındaki pencere) yine bir mahyanın ortasında; çatı hiç değişmediyse (iç duvar kayması)
      açıklığı kaydıran çatı değil plan kuralıdır (köşe kuralı, Lokman 31.10; KT-01 banyo penceresi), hakem karışmaz;
    - vadiye oturan makas uçları vadide."""
    imza = lambda c: collections.Counter((e["tur"], tuple(sorted(e["duzlemler"]))) for e in c["kenarlar"])
    if imza(c1) != imza(c2):
        raise GermeHatasi("küçük çatı yeni ölçüye göre kurulamıyor (çatı yüzleri birbirine oturmuyor)")
    for dz, (duvar, pay) in sorted(_sacak_taskilari(t1).items()):
        p2 = _sacak_payi(t2, dz, duvar)
        if p2 is None or abs(p2 - pay) > 0.5:
            raise GermeHatasi("çatının saçak taşması değişiyor")
    kenarlar = lambda c: sorted((e["tur"], _mahya_anahtari(e)) for e in c["kenarlar"])
    if kenarlar(c1) != kenarlar(c2):
        for ad in sorted(set(_mahya_altindakiler(t1, c1)) - set(_mahya_altindakiler(t2, c2))):
            raise GermeHatasi(f"{_aciklik_sozu(t2, ad)} çatının ortasında kalmıyor")
    v1, v2 = _vadi_uclari(t1, c1), _vadi_uclari(t2, c2)
    if any(v2[a] < n for a, n in v1.items()):
        raise GermeHatasi("küçük çatının makası vadiye oturmuyor")


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
        c2 = cati_genel.cati_kur(t_sonra["cati"], MK.oku())
        k2 = YK.tanimdan(t_sonra, set_yolu)
    except (SystemExit, ValueError, KeyError) as e:
        raise GermeHatasi("çatı yeni ölçüye otomatik kurulamıyor") from None
    _cati_hakemi(t_once, cati_genel.cati_kur(t_once["cati"], MK.oku()), t_sonra, c2)
    k1 = k_once or YK.tanimdan(t_once, set_yolu)
    if set(k2["topolojik"]["ulasilamayan"]) - set(k1["topolojik"]["ulasilamayan"]) or \
            set(k2["topolojik"]["eslesmeyen_acikliklar"]) - set(k1["topolojik"]["eslesmeyen_acikliklar"]):
        raise GermeHatasi("odaların kapı bağlantıları değişiyor")
    a1, a2 = _aciklik_iliskisi(k1), _aciklik_iliskisi(k2)
    for ad, (tur, yan) in sorted(a1.items()):
        if a2.get(ad) != (tur, yan):
            ne = f"{yan[0]} penceresi" if tur == "pencere" else f"{' ile '.join(yan)} arasındaki kapı"
            raise GermeHatasi(f"{ne} yerinde kalmıyor")
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
    ayak0, ayak1 = _ayaklar(t_once), _ayaklar(t_sonra)
    for ad, g in sorted(ayak1.items()):
        if g < AYAK_CM - TOL and g < ayak0.get(ad, math.inf) - TOL:
            raise GermeHatasi(f"{_aciklik_sozu(t_sonra, ad)} duvar köşesine {_tr(g, 1)} cm kalıyor (en az {AYAK_CM} cm olmalı)")
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
def _degisim(yon: str, buyut: bool) -> str:
    """Bayi gerekçesinde isteğin anılışı: "arkaya büyümek" ya da "arkadan küçülmek"."""
    return f"{YON_SOZU[yon]} büyümek" if buyut else f"{KUCULT_SOZU[yon]} küçülmek"


def _kilit_nedeni(e: dict, mahal: str, yon: str, buyut: bool = True) -> str:
    n = e.get("neden") or ""
    if n.startswith("verandaya bakan"):
        return f"{mahal} {YAN_SOZU[yon]} yanında verandaya bakıyor; veranda ve çatısı otomatik değişmiyor"
    if n.startswith("verandanın kenarı"):
        return "veranda ve çatısı otomatik değişmiyor"
    if "verandayı da keser" in n:
        return (f"{YON_SOZU[yon]} büyürken" if buyut else f"{KUCULT_SOZU[yon]} küçülürken") + " veranda da değişirdi; veranda ve çatısı otomatik değişmiyor"
    if n.startswith("ana çatının"):
        return f"{_degisim(yon, buyut)} ana çatının genişliğini ve mahya yüksekliğini değiştirir; bu otomatik yapılmıyor"
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
            raise GermeHatasi(_kilit_nedeni(kilitli[0], mahal, yon, buyut))
        raise GermeHatasi(f"odanın {YAN_SOZU[yon]} yanında hem dış duvar hem başka oda var")
    kilitli = [e for e in kullanilan if e["durum"] == "kilitli"]
    if kilitli:
        raise GermeHatasi(_kilit_nedeni(kilitli[0], mahal, yon, buyut))
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
    if rapor.get("ortalanan_acikliklar"):                      # tek kesitli düzey 2: küçük çatının ortasındaki açıklık ortada kalır (bayiye yazılır)
        iliski = _aciklik_iliskisi(k2)
        rapor["kayan_acikliklar"] = [{"ad": a, "tur": iliski.get(a, ("açıklık", ()))[0],
                                      "mahaller": [x for x in iliski.get(a, ("", ()))[1] if x != YK.DIS], "cm": abs(kay),
                                      "yon": {("x", True): "D", ("x", False): "B", ("y", True): "K", ("y", False): "G"}[(rapor["eksen"], kay > 0)]}
                                     for a, kay in rapor.pop("ortalanan_acikliklar")]
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
    yon = (YON_SOZU if rapor["buyut"] else KUCULT_SOZU)[rapor["yon"]]
    return f"{rapor['mahal']} {yon} {rapor['cm']} cm {'büyütüldü' if rapor['buyut'] else 'küçültüldü'}"


def anlatim(rapor: dict) -> str:
    """Kodun hesapladığı fark (bayi mesajı): germede "ev arkaya 50 cm uzadı (uzayan öteki odalar: …); kapalı alan 87,27 → 93,37 m²",
    kaymada "Mutfak 10,05 → 10,82 m²; Yatak Odası 1 12,74 → 11,97 m²" ve kayan kapı ya da pencere ("… arasındaki kapı 30 cm öne kaydı")."""
    mahal, yon, cm, buyut = rapor["mahal"], rapor["yon"], rapor["cm"], rapor["buyut"]
    deg = rapor.get("degisen") or {}
    if rapor["tur"] == "germe":
        obur = [m for m in sorted(deg) if m != mahal]
        ev = f"ev {(YON_SOZU if buyut else KUCULT_SOZU)[yon]} {cm} cm {'uzadı' if buyut else 'kısaldı'}"
        if obur:
            ev += f" ({'uzayan' if buyut else 'kısalan'} öteki odalar: {', '.join(obur)})"
        k0, k1 = rapor["kapali_m2"]
        ek = ""
        if rapor.get("ikincil_cati"):                          # düzey 2 (PR-2b): düzlem adı değil, sabit sözcük (bayiye iç ad gitmez)
            tur = [w for w in ("cumba", "çıkma") if any(w in ad for ad in rapor["ikincil_cati"])]
            ek = f"; {' ve '.join(tur) if tur else 'küçük çatı'} {'ortadan ' if isinstance(rapor.get('kesit_cm'), list) else ''}" \
                 f"{'genişledi' if buyut else 'daraldı'}, {'çatıları' if len(tur) > 1 else 'çatısı'} yeni ölçüye göre kuruldu"
        for a in rapor.get("kayan_acikliklar") or []:          # tek kesitli düzey 2: ortada tutulan pencere
            ek += f"; {_aciklik_adi(a)} {_cm_sozu(a['cm'])} cm {YON_SOZU[a['yon']]} kaydı (ortada kaldı)"
        return f"{ev}; kapalı alan {_tr(k0)} → {_tr(k1)} m²{ek}"
    sira = [mahal] + [m for m in sorted(deg) if m != mahal]
    parca = [f"{m} {_tr(deg[m][0])} → {_tr(deg[m][1])} m²" for m in sira if m in deg]
    for a in rapor.get("kayan_acikliklar") or []:
        parca.append(f"{_aciklik_adi(a)} {a['cm']:g} cm {YON_SOZU[a['yon']]} kaydı")
    return "; ".join(parca)


def _cm_sozu(v: float) -> str:
    return f"{float(v):g}".replace(".", ",")


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
    buyut = d.get("op") == "oda_buyut"
    yon = (YON_SOZU if buyut else KUCULT_SOZU).get(d.get("yon"), "")
    return f"{d.get('mahal')} {yon} {d.get('cm')} cm {'büyütme' if buyut else 'küçültme'}".replace("  ", " ")
