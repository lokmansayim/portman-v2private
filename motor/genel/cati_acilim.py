#!/usr/bin/env python3
"""Kırma çatının açılımı ve kaplama dizilimi: kaplama adedi buradan çıkar.

Lokman, 4 Ekim 2026 01:42: kırma çatıda kaplama adedi AutoCAD'e bırakılmaz. Çatı eğimine göre çizilir, zarf açar gibi açılır
ve kaplama yüzeye dizilir. Çapraz kesimden artan parça karşı tarafta, aynı açılı yere kullanılır: sol üçgende kullanılan
panelin artanı sağ üçgene, ön yamuktan çıkan açılı kesilmiş parça arka yamuğun aynı biçimdeki açılı yerine.

Model (dikdörtgen planlı, dört yanı eşit eğimli kırma çatı):
  - Dört yüz gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ).
    Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Kırma çizgisi açılımda bütün yüzlerde aynı açıdadır.
  - Her yüz, saçağa dik, `kapatma` genişliğinde şeritlere bölünür. Kapatma genişliği ürüne göre değişir (Lokman, 4 Ekim 2026 15:18).
    Dizilim her yüzde, dışarıdan bakışla sol köşeden başlar (Lokman, 15:18: "her köşeden başlayacak gibi hesapla"); öteki
    başlangıçlar (sağ köşe, orta, karışık) yalnız bilgi için denenir.
  - Kaplama saçak çizgisinden `tasma` kadar dışarı uzar (mühendis, 4 Ekim 2026 12:14: 5 cm): her parçanın boyu o kadar artar.
  - Şerit parçası: düz (tam boy dikdörtgen), L (boyu soldan sağa artan), R (azalan) ya da karma (içinde mahya ucu ya da tepe var).
  - Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır:
    alt parça olduğu gibi kullanılır; üst parça, düz ucu saçağa gelecek biçimde karşı yüze taşınır. Üst parça alt parçayla
    aynı türdendir (L ise L). İki parçanın birlikte istediği boy: uzun kenarların toplamı − bir şeritlik boy farkı.
  - Eşleme: en uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır.
    Dikdörtgenler panellere büyükten küçüğe, ilk sığana yerleştirilir.
  - Boy bindirmesi yoktur. Kesim payı (`kesim_payi`): çapraz kesimde iki parçanın arasına ve aynı panelden çıkan
    dikdörtgenlerin arasına eklenir; kurallarda 5 mm (Lokman onayladı, 15:18). Yedek panel eklenmez: kesim planı montajcıya verilir.
    Panel tek boydur. Taban boy eğimli boy + taşmadır (Excel motorundaki gibi; mm'ye yukarı). Boy 1'er cm uzatılınca (en çok 3 cm)
    adet düşüyorsa uzun boy alınır (Lokman, 4 Ekim 2026 16:18; `panel_boyu_uzatma`): taşma değişmez, tam boy giden panellerde
    fazlalık mahya ucunda kalır.
  - Kesim planının ölçüleri (`--olcu-md`): her parçanın çatıdaki kenar boyları ve paneldeki yeri; çizim, ölçü tablosu ve
    geometrik sağlama aynı yerleşimi (`panel_yerlesimi`) kullanır.
Hesapta LLM yok: aynı girdi aynı dizilimi verir.

Kullanım:
    python cati_acilim.py sonuc/C8201_girdi.json --cikti sonuc/C8201_cati_acilim.json \\
        --acilim-png sonuc/C8201_cati_acilim.png --kesim-png sonuc/C8201_cati_kesim.png --olcu-md sonuc/C8201_cati_kesim_olculeri.md
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import kural

BURADA = Path(__file__).resolve().parent
EPS = 1e-6
KARSI = {"ön": "arka", "arka": "ön", "sol": "sağ", "sağ": "sol"}
ALT_YUZ = ("ön", "sol")                    # eşlemede alt (olduğu gibi kullanılan) parçanın yüzü; üst parça karşı yüze gider
NUMARA_SIRASI = ("ön", "sol", "arka", "sağ")
# Dizilimin başladığı köşe, dışarıdan bakışla. "plan_yonu": karşılıklı yüzler planda aynı uçtan başlar.
BASLANGIC = {"sol": {"ön": "sol", "arka": "sol", "sol": "sol", "sağ": "sol"},
             "sag": {"ön": "sag", "arka": "sag", "sol": "sag", "sağ": "sag"},
             "orta": {"ön": "orta", "arka": "orta", "sol": "orta", "sağ": "orta"},
             "plan_yonu": {"ön": "sol", "arka": "sag", "sol": "sol", "sağ": "sag"},
             # uzun yüzler (yamuk) köşeden, kısa yüzler (üçgen) ortadan ve tersi
             "kose_orta": {"ön": "sol", "arka": "sol", "sol": "orta", "sağ": "orta"},
             "orta_kose": {"ön": "orta", "arka": "orta", "sol": "sol", "sağ": "sol"}}


BASLANGIC_ADI = {"sol": "her yüzde sol köşeden", "sag": "her yüzde sağ köşeden", "orta": "her yüzde ortadan",
                 "plan_yonu": "karşılıklı yüzlerde planda aynı uçtan", "kose_orta": "uzun yüzlerde sol köşeden, kısa yüzlerde ortadan",
                 "orta_kose": "uzun yüzlerde ortadan, kısa yüzlerde sol köşeden"}
KAPATMA_KURALI = {"sandvic_panel": "sandvic_panel_kapatma_m", "tek_kat_panel": "tek_kat_panel_kapatma_m", "osb_kiremit": "kiremit_kapatma_m",
                  "osb_trapez": "trapez_sac_kapatma_m", "trapez_sac": "trapez_sac_kapatma_m"}


def tavan(x: float) -> int:
    return int(math.ceil(x - 1e-9))


@dataclass
class Parca:
    yuz: str
    serit: int                 # 1'den; dışarıdan bakışla soldan sağa
    x0: float                  # saçak boyunca, sol köşeden (m)
    x1: float
    tip: str                   # duz | L | R | karma
    uzun: float                # en uzun yerindeki boy (m)
    kisa: float                # en kısa yerindeki boy (m)
    kose: list = field(default_factory=list)   # yüz koordinatında köşeler: (x, t); t saçaktan yukarı, eğimli boy
    panel: int = 0
    konum: str = ""            # tam | alt | üst | tek

    @property
    def en(self) -> float:
        return self.x1 - self.x0


def yuz_parcalari(ad: str, sacak: float, y0: float, k: float, kapatma: float, baslangic: str, tasma: float = 0.0) -> list[Parca]:
    """Bir yüzün şerit parçaları. Yüzün boyu x'te: k × min(x, y0, saçak − x). Kaplama saçak çizgisinden `tasma` kadar dışarı uzar:
    her parçanın boyu o kadar artar (köşelerde t = −tasma)."""
    def h(x: float) -> float:
        return k * max(0.0, min(x, y0, sacak - x))

    n = tavan(sacak / kapatma)
    if baslangic == "sol":
        sinir = [min(i * kapatma, sacak) for i in range(n + 1)]
    elif baslangic == "sag":
        sinir = sorted(max(sacak - i * kapatma, 0.0) for i in range(n + 1))
    elif baslangic == "orta":   # ek yeri yüzün ortasında
        yari = sacak / 2
        m = tavan(yari / kapatma)
        sinir = sorted([max(yari - i * kapatma, 0.0) for i in range(m + 1)] + [min(yari + i * kapatma, sacak) for i in range(1, m + 1)])
    else:
        raise ValueError(f"Bilinmeyen başlangıç: {baslangic}")
    kirik = sorted({round(y0, 9), round(sacak - y0, 9)})
    cik: list[Parca] = []
    for a, b in zip(sinir, sinir[1:]):
        if b - a < EPS:
            continue
        ic = [x for x in kirik if a + EPS < x < b - EPS]
        ust = [(b, h(b))] + [(x, h(x)) for x in reversed(ic)] + [(a, h(a))]
        ha, hb = h(a), h(b)
        tip = "karma" if ic else ("duz" if abs(ha - hb) < EPS else ("L" if hb > ha else "R"))
        cik.append(Parca(ad, len(cik) + 1, a, b, tip, max(t for _, t in ust) + tasma, min(ha, hb) + tasma, [(a, -tasma), (b, -tasma)] + ust))
    return cik


def es_boyu(p: Parca, q: Parca, adim: float, pay: float = 0.0) -> float:
    """Aynı türden iki parçanın tek dikdörtgenden çıkması için gereken boy. `adim`: bir şerit genişliğinde boyun değişimi.
    Dar parça ötekinin ince ucuna yerleşir: en çok (uzun kenarların toplamı − adım), en az iki uzun kenarın büyüğü.
    `pay`: iki parçanın arasındaki çapraz kesimin payı; yalnız parçalar birbirine değiyorsa (toplam terimi belirleyiciyse) boyu uzatır."""
    return max(p.uzun, q.uzun, p.uzun + q.uzun - adim + pay)


def dizilim(px: float, py: float, egim: float, kapatma: float, boy: float, paylas: bool = True, baslangic: str = "sol", kesim_payi: float = 0.0,
            tasma: float = 0.0) -> dict:
    """Kırma çatının açılımı ve kaplama dizilimi. `paylas`: çapraz kesimden artan parça karşı yüzde kullanılır.
    `kesim_payi` (m): sağlama içindir; çapraz kesimde iki parçanın arasına ve bir panelden çıkan dikdörtgenlerin arasına eklenir.
    `tasma` (m): kaplama saçak çizgisinden bu kadar dışarı uzar (mühendis, 4 Ekim 2026 12:14: 5 cm); her parçanın boyuna eklenir."""
    uzun_k, kisa_k = max(px, py), min(px, py)
    y0, k = kisa_k / 2, math.sqrt(1 + egim * egim)
    H = y0 * k
    if boy + EPS < H + tasma:
        raise ValueError(f"Panel boyu ({boy} m) eğimli boy + taşmadan ({H + tasma:.3f} m) kısa; boy bindirmeli dizilim bu modelde yok")
    adim = k * kapatma
    bas = BASLANGIC[baslangic]
    yuzler = {"ön": yuz_parcalari("ön", uzun_k, y0, k, kapatma, bas["ön"], tasma), "arka": yuz_parcalari("arka", uzun_k, y0, k, kapatma, bas["arka"], tasma),
              "sol": yuz_parcalari("sol", kisa_k, y0, k, kapatma, bas["sol"], tasma), "sağ": yuz_parcalari("sağ", kisa_k, y0, k, kapatma, bas["sağ"], tasma)}
    hepsi = [p for ad in NUMARA_SIRASI for p in yuzler[ad]]
    sira = {id(p): i for i, p in enumerate(hepsi)}

    # 1) dikdörtgenler: tam boy ve karma parçalar tek başına; L ve R parçalar karşı yüzdeki eşleriyle
    dikdortgenler: list[dict] = []
    for p in hepsi:
        if p.tip in ("duz", "karma"):
            p.konum = "tam"
            dikdortgenler.append({"boy": p.uzun, "parcalar": [p], "bosluk": 0.0})
    for cift in (("ön", "arka"), ("sol", "sağ")):
        for tip in ("L", "R"):
            grup = sorted((p for p in hepsi if p.yuz in cift and p.tip == tip), key=lambda p: (-p.uzun, sira[id(p)]))
            bitti: set[int] = set()
            for p in grup:
                if id(p) in bitti:
                    continue
                bitti.add(id(p))
                es = next((q for q in grup if id(q) not in bitti and q.yuz == KARSI[p.yuz] and es_boyu(p, q, adim, kesim_payi) <= boy + EPS), None) if paylas else None
                if es is None:
                    p.konum = "tek"
                    dikdortgenler.append({"boy": p.uzun, "parcalar": [p], "bosluk": 0.0})
                    continue
                bitti.add(id(es))
                alt, ust = (p, es) if p.yuz in ALT_YUZ else (es, p)
                alt.konum, ust.konum = "alt", "üst"
                gereken = es_boyu(p, es, adim, kesim_payi)
                # bosluk: iki parçanın arasında kalan boşluk (boyu büyük parça belirliyorsa sıfırdan büyüktür)
                dikdortgenler.append({"boy": gereken, "parcalar": [alt, ust], "bosluk": gereken - (p.uzun + es.uzun - adim + kesim_payi)})

    # 2) dikdörtgenler panellere: büyükten küçüğe, ilk sığana
    dikdortgenler.sort(key=lambda d: (-d["boy"], sira[id(d["parcalar"][0])]))
    paneller: list[dict] = []
    for d in dikdortgenler:
        for pn in paneller:
            if d["boy"] + kesim_payi <= pn["kalan"] + EPS:      # aynı panelden bir dikdörtgen daha: araya bir gönye kesimi
                pn["kalan"] -= d["boy"] + kesim_payi
                pn["dikdortgenler"].append(d)
                break
        else:
            paneller.append({"kalan": boy - d["boy"], "dikdortgenler": [d]})

    # 3) numara: yüzler ön, sol, arka, sağ sırasıyla dolaşılır; panel, ilk görülen parçasının sırasıyla numaralanır
    paneller.sort(key=lambda pn: min(sira[id(p)] for d in pn["dikdortgenler"] for p in d["parcalar"]))
    for no, pn in enumerate(paneller, start=1):
        pn["no"] = no
        for d in pn["dikdortgenler"]:
            for p in d["parcalar"]:
                p.panel = no

    yuzey = 2 * (uzun_k + (uzun_k - kisa_k)) / 2 * H + 2 * kisa_k * H / 2
    kaplanan = yuzey + tasma * 2 * (uzun_k + kisa_k)          # taşma şeridi dahil
    return {"plan_m": [uzun_k, kisa_k], "egim": egim, "kapatma_m": kapatma, "boy_m": boy, "paylas": paylas, "baslangic": baslangic,
            "egimli_boy_m": H, "mahya_m": uzun_k - kisa_k, "adim_m": adim, "yuzey_m2": yuzey, "tasma_m": tasma, "kaplanan_m2": kaplanan,
            "yuzler": yuzler, "paneller": paneller, "adet": len(paneller),
            "alan_alt_siniri": tavan(kaplanan / (kapatma * boy)),
            "tam_boy_adedi": sum(1 for p in hepsi if p.konum == "tam"),
            "cift_adedi": sum(1 for p in hepsi if p.konum == "alt"),
            "tek_adedi": sum(1 for p in hepsi if p.konum == "tek"),
            "parca_adedi": len(hepsi), "kesim_payi_m": kesim_payi,
            # en dar pay: iki parça veren kesimlerde, parçaların arasında ve panelin sonunda kalan boşluğun en küçüğü
            "en_dar_pay_m": min((pn["kalan"] + x["bosluk"] for pn in paneller for x in pn["dikdortgenler"] if len(x["parcalar"]) == 2), default=None)}


def adet_denemeleri(px: float, py: float, egim: float, kapatma: float, boy: float, paylas: bool = True, tasma: float = 0.0, kesim_payi: float = 0.0) -> dict:
    """Dizilimin başladığı yer değişince adet."""
    return {b: dizilim(px, py, egim, kapatma, boy, paylas, b, kesim_payi, tasma)["adet"] for b in BASLANGIC}


def kapatma_genisligi(kr: dict, cati: dict, kaplama: str) -> float:
    """Kaplamanın kapattığı genişlik (m). Ürüne göre değişir (Lokman, 4 Ekim 2026 15:18): girdide `cati.kapatma_m` yazıyorsa o
    (gerçek liste örnekleri kendi ürünleriyle hesaplanır), yoksa kurallardaki güncel değer."""
    return cati.get("kapatma_m") or kr[KAPATMA_KURALI[kaplama]]["deger"]


def panel_yerlesimi(d: dict):
    """Kesim planındaki yerleşim: her parça için (panel no, parça, çokgen [panel koordinatı; m; saçak ucu altta], 'alt' | 'ust').
    Dikdörtgenler panelde saçak ucundan yukarı dizilir; aralarında kesim payı bırakılır. Alt parça olduğu gibi kullanılır;
    üst parça çatıya 180° çevrilerek (ters yüz edilmeden) konur. Çizim, ölçü tablosu ve geometrik sağlama bu çokgenleri kullanır."""
    w, pay, ts = d["kapatma_m"], d["kesim_payi_m"], d["tasma_m"]
    for pn in d["paneller"]:
        taban = 0.0
        for dk in pn["dikdortgenler"]:
            l, ps = dk["boy"], dk["parcalar"]
            if len(ps) == 1 and ps[0].konum == "tam":
                q = ps[0]
                yield pn["no"], q, [(x - q.x0, t + ts + taban) for x, t in q.kose], "alt"
            else:
                alt = ps[0]
                a, b, en = alt.uzun, alt.kisa, alt.en
                # boyu sağa doğru artan (L) dar parça sağa, azalan (R) sola yaslanır
                kose = [(w - en, 0), (w, 0), (w, a), (w - en, b)] if alt.tip == "L" else [(0, 0), (en, 0), (en, b), (0, a)]
                yield pn["no"], alt, [(x, y + taban) for x, y in kose], "alt"
                if len(ps) == 2:
                    ust = ps[1]
                    a, b, en = ust.uzun, ust.kisa, ust.en
                    # üst parça çevrilmeden önce: kalın ucu alt parçanın ince ucunun üstünde, dikdörtgenin üst kenarından asılı
                    kose = [(0, l), (en, l), (en, l - b), (0, l - a)] if ust.tip == "L" else [(w, l), (w - en, l), (w - en, l - b), (w, l - a)]
                    yield pn["no"], ust, [(x, y + taban) for x, y in kose], "ust"
            taban += l + pay


def kural_dizilimi(kr: dict, cati: dict, kaplama: str) -> dict | None:
    """Kurallardaki ayarlarla kırma çatının dizilimi: kapatma genişliği, taşma, kesim payı, artan parçanın kullanılıp
    kullanılmayacağı ve dizilimin başladığı yer. Başlangıç kuralda adıyla yazılıdır (Lokman, 4 Ekim 2026 15:18: her yüzde köşeden,
    `sol`); `en_az` yazıyorsa kurallardaki sırayla denenir ve en az paneli veren ilk başlangıç alınır. Sıradaki öteki başlangıçlar
    her durumda bilgi için denenir (`denemeler`, `en_az_adet`).
    Panel boyu listeden geliyorsa ve eğimli boy + taşmadan kısaysa taşma panelin yettiği kadardır.
    Panel boyu kuraldan geliyorsa (`cati.panel_boyu_kaynak: kural`) uzatma kuralı uygulanır: `boy_m` seçilen boydur, `taban_boy_m` ve
    `taban_adet` uzatmadan önceki değerler, `uzatma` kuralın uyguladığı değişiklik (yoksa None).
    Dönen: dizilim sözlüğü ve ek olarak denemeler, paysız ve 1 cm paylı adet. Çatı planı yoksa ya da panel eğimli boydan kısaysa None."""
    if not (cati.get("plan_m") and cati.get("panel_boyu_m") and cati.get("egim")) or kaplama not in KAPATMA_KURALI:
        return None
    kd = kr["kirma_cati_dizilim"]["deger"]
    px, py, egim, taban_boy = cati["plan_m"][0], cati["plan_m"][1], cati["egim"], cati["panel_boyu_m"]
    H = min(px, py) / 2 * math.sqrt(1 + egim * egim)
    if taban_boy + EPS < H:
        return None
    kapatma = kapatma_genisligi(kr, cati, kaplama)
    paylas = kaplama not in kd["artan_parca_kullanilmayan_kaplamalar"]
    tasma = max(0.0, min(kr["cati_kaplama_tasma_m"]["deger"], taban_boy - H))
    pay = kd["kesim_payi_m"]
    sira = list(kd["baslangic_sirasi"]) + ([kd["baslangic"]] if kd["baslangic"] not in ("en_az", *kd["baslangic_sirasi"]) else [])

    def sec(b: float) -> tuple[str, dict]:
        """Verilen panel boyunda dizilimin başladığı yer ve altı başlangıcın adetleri."""
        den_ = {s: dizilim(px, py, egim, kapatma, b, paylas, s, pay, tasma)["adet"] for s in sira}
        return (next(s for s in sira if den_[s] == min(den_.values())) if kd["baslangic"] == "en_az" else kd["baslangic"]), den_

    def adet(b: float, kesim_payi: float) -> int:
        return dizilim(px, py, egim, kapatma, b, paylas, sec(b)[0], kesim_payi, tasma)["adet"]

    taban_adet = adet(taban_boy, pay)
    # Panel biraz uzun olursa adet düşüyor mu? Panel boyu = eğimli boy + taşma tam boy parçaya ancak yeter; en uzun kesik parça ile
    # köşe parçasının aynı panelden çıkması için kesim payı kadar yer kalmayabilir. Eşik: 3 cm'ye kadar mm mm denenir (bilgi).
    uzun_panelle = None
    for ek_mm in range(1, 31):
        n = adet(taban_boy + ek_mm / 1000, pay)
        if n < taban_adet:
            uzun_panelle = {"boy_mm": round(taban_boy * 1000) + ek_mm, "adet": n}
            break
    # Panel boyu uzatma kuralı (Lokman, 4 Ekim 2026 16:18): boy 1'er cm uzatılarak denenir (en çok 3 cm); adet düşüyorsa liste o boyu
    # yazar. Aday boyda adet, kesim payı 1 cm'ye çıksa da aynı kalmalı (pay kalsın diye). En az adedi veren, eşitlikte en kısa boy alınır.
    # Yalnız panel boyu kuraldan geldiğinde uygulanır; boyu gerçek listeden gelen örneklerde uygulanmaz.
    # Pay koşulu taban boy için de aranır (kuralda `taban_icin_de`; 7 Ekim 2026): taban boyda adet, kesim payı 1 cm'ye çıkınca artıyorsa
    # (pay ince) adedi artırmayan ve 1 cm kesim payıyla gereken adedi en çok düşüren boy alınır (tam sağlam boy varsa odur); eşitlikte en kısası.
    # Anahtar kuralda yoksa eski davranış: yalnız adet düşüyorsa uzatılır. Genel motor aynı ölçütü kullanır (`girdi_genel._dizilim`).
    uz = (kr.get("panel_boyu_uzatma") or {}).get("deger") or {}
    boy, uzatma = taban_boy, None
    if uz.get("uygula") and cati.get("panel_boyu_kaynak") == "kural":
        taban_icin_de = bool(uz.get("taban_icin_de"))
        sp = uz["saglamlik_kesim_payi_m"]
        taban_saglamlik_adet = adet(taban_boy, sp) if taban_icin_de else taban_adet
        ince = taban_saglamlik_adet > taban_adet
        adaylar = []
        for i in range(1, round(uz["en_cok_m"] / uz["adim_m"]) + 1):
            b = round(taban_boy + i * uz["adim_m"], 6)
            n, n_sp = adet(b, pay), adet(b, sp)
            if (n < taban_adet and n_sp == n) or (ince and n == taban_adet and n_sp < taban_saglamlik_adet):
                adaylar.append((n, n_sp, b))
        if adaylar:
            n, n_sp, boy = min(adaylar)
            uzatma = {"taban_boy_mm": round(taban_boy * 1000), "taban_adet": taban_adet, "boy_mm": round(boy * 1000), "adet": n,
                      "esik_boy_mm": uzun_panelle["boy_mm"] if uzun_panelle else None}
            if taban_icin_de:      # neden: adet düştü ("adet") ya da adet aynı, taban boyda pay inceydi ("pay")
                uzatma["neden"] = "adet" if n < taban_adet else "pay"
                if n == taban_adet:
                    # taban boyda adedin aynı kaldığı en büyük kesim payı (0,1 mm adımla; bilgi)
                    sinir_mm = max((p10 / 10 for p10 in range(round(pay * 10000), round(sp * 10000) + 1) if adet(taban_boy, p10 / 10000) == taban_adet), default=round(pay * 1000, 1))
                    uzatma.update(taban_saglamlik_adet=taban_saglamlik_adet, saglamlik_adet=n_sp, taban_pay_siniri_mm=sinir_mm)
    secilen, den = sec(boy)
    d = dizilim(px, py, egim, kapatma, boy, paylas, secilen, pay, tasma)
    d.update(denemeler=den, en_az_adet=min(den.values()), baslangic_kurali=kd["baslangic"], kaplama=kaplama, tasma_kural_m=kr["cati_kaplama_tasma_m"]["deger"],
             paysiz_adet=dizilim(px, py, egim, kapatma, boy, paylas, secilen, 0.0, tasma)["adet"],
             bir_cm_payla_adet=dizilim(px, py, egim, kapatma, boy, paylas, secilen, 0.01, tasma)["adet"],
             taban_boy_m=taban_boy, taban_adet=taban_adet, uzatma=uzatma,
             # uzatma uygulanmadıysa: taban boydan biraz uzun panelle adet düşüyor mu (yalnız bilgi)
             uzun_panelle=None if uzatma else uzun_panelle)
    return d


def kenarlar(p: Parca, tasma: float) -> dict:
    """Parçanın çatıdaki yerinde, dışarıdan bakışla sol ve sağ kenar boyu (saçak ucundan, taşma dahil) ve varsa aradaki
    kırık noktaları: (sol kenardan uzaklık, o noktadaki boy). Hepsi m. Kesim için ölçü buradan okunur."""
    ust = p.kose[2:]                        # (x1, boy), aradaki kırıklar sağdan sola, (x0, boy)
    return {"sol": ust[-1][1] + tasma, "sag": ust[0][1] + tasma, "ara": [(x - p.x0, t + tasma) for x, t in reversed(ust[1:-1])]}


KONUM_ADI = {"tam": "tam boy panel", "alt": "çapraz kesimin alt parçası", "üst": "aynı panelin artan parçası (çevrilerek)", "tek": "tek parça; artığı kullanılmıyor"}


def parca_tablosu(d: dict) -> list[str]:
    """Yüz yüz, şerit şerit parça ölçüleri (markdown): montajcı için. Ölçüler cm; boylar saçak ucundan, taşma dahil."""
    cik = ["| Yüz | Şerit | Saçaktaki yeri (soldan) | En | Sol kenar | Sağ kenar | Arada | Panel | Nasıl çıkar |", "|---|---|---|---|---|---|---|---|---|"]
    for ad in NUMARA_SIRASI:
        for q in d["yuzler"][ad]:
            kn = kenarlar(q, d["tasma_m"])
            ara = "; ".join(f"soldan {_tr(u * 100, 1)} cm'de {_tr(b * 100, 1)}" for u, b in kn["ara"])
            cik.append(f"| {ad} | {q.serit} | {_tr(q.x0 * 100, 1)}–{_tr(q.x1 * 100, 1)} | {_tr(q.en * 100, 1)} | {_tr(kn['sol'] * 100, 1)} | {_tr(kn['sag'] * 100, 1)} | {ara} | {q.panel} | {KONUM_ADI[q.konum]} |")
    return cik


def panel_tablosu(d: dict) -> list[str]:
    """Panel panel kesim ölçüleri (markdown): her parçanın paneldeki yeri. Ölçüler cm; boy saçak ucundan (panelin alt ucundan) yukarı,
    en panelin sol kenarından. Parça, sol ve sağ kenardaki iki aralığın arasında kalan dörtgendir; köşesi kesilen tam boy panelde
    aradaki kırık noktası ayrıca yazılır."""
    def cm(x: float) -> str:
        return _tr(x * 100 + 0.0, 1)        # −0,0 yazılmasın

    cik = ["| Panel | Parça | Enine (soldan) | Sol kenarda (alttan) | Sağ kenarda (alttan) | Arada | Çatıya |", "|---|---|---|---|---|---|---|"]
    for no, q, kose, konum in panel_yerlesimi(d):
        xs = [x for x, _ in kose]
        x0, x1 = min(xs), max(xs)
        sol = [y for x, y in kose if abs(x - x0) < EPS]
        sag = [y for x, y in kose if abs(x - x1) < EPS]
        ara = "; ".join(f"soldan {cm(x)}'de {cm(y)}" for x, y in sorted((x, y) for x, y in kose if x0 + EPS < x < x1 - EPS))
        cik.append(f"| {no} | {q.yuz} {q.serit} | {cm(x0)}–{cm(x1)} | {cm(min(sol))}–{cm(max(sol))} | {cm(min(sag))}–{cm(max(sag))} | {ara} | "
                   f"{'180° çevrilerek' if konum == 'ust' else 'olduğu gibi'} |")
    return cik


def panel_ozeti(d: dict) -> list[str]:
    """Panel başına özet (markdown): içinden çıkan parçalar ve kullanılmayan boy (cm)."""
    cik = ["| Panel | Parçalar | Kullanılmayan boy |", "|---|---|---|"]
    for pn in d["paneller"]:
        parcalar = " · ".join(" + ".join(f"{q.yuz} {q.serit}" for q in x["parcalar"]) for x in pn["dikdortgenler"])
        cik.append(f"| {pn['no']} | {parcalar} | {_tr(max(pn['kalan'], 0.0) * 100, 1)} |")
    return cik


def sozluk(d: dict) -> dict:
    """JSON'a yazılacak biçim (ölçüler m, üç hane)."""
    def r(x: float) -> float:
        return round(x, 3)

    def kn(q: Parca) -> dict:
        k = kenarlar(q, d["tasma_m"])
        return {"sol_kenar_m": r(k["sol"]), "sag_kenar_m": r(k["sag"]), "arada": [[r(u), r(b)] for u, b in k["ara"]]}
    return {"plan_m": [r(x) for x in d["plan_m"]], "egim": d["egim"], "kapatma_m": d["kapatma_m"], "panel_boyu_m": d["boy_m"],
            "artan_parca_karsi_yuzde": d["paylas"], "baslangic": d["baslangic"], "baslangic_adi": BASLANGIC_ADI[d["baslangic"]],
            "egimli_boy_m": r(d["egimli_boy_m"]), "mahya_m": r(d["mahya_m"]), "tasma_m": r(d["tasma_m"]),
            "yuzey_m2": round(d["yuzey_m2"], 2), "kaplanan_m2": round(d["kaplanan_m2"], 2), "adet": d["adet"], "alan_alt_siniri": d["alan_alt_siniri"],
            "tam_boy_panel": d["tam_boy_adedi"], "iki_parca_veren_kesim": d["cift_adedi"], "artigi_kullanilmayan_parca": d["tek_adedi"], "parca_adedi": d["parca_adedi"],
            "kesim_payi_m": d["kesim_payi_m"], "en_dar_pay_m": None if d["en_dar_pay_m"] is None else r(d["en_dar_pay_m"]),
            "yuzler": {ad: [{"serit": p.serit, "x0_m": r(p.x0), "x1_m": r(p.x1), "en_m": r(p.en), "tip": p.tip, "uzun_m": r(p.uzun), "kisa_m": r(p.kisa), **kn(p),
                             "panel": p.panel, "konum": p.konum} for p in ps] for ad, ps in d["yuzler"].items()},
            "paneller": [{"no": pn["no"], "artan_boy_m": r(pn["kalan"]),
                          "kesimler": [{"boy_m": r(x["boy"]), "parcalar": [f"{p.yuz} {p.serit} ({p.konum})" for p in x["parcalar"]]} for x in pn["dikdortgenler"]]}
                         for pn in d["paneller"]]}


# ── çizim ──────────────────────────────────────────────────────────────────────
RENK = {"tam": "#c9d6e2", "alt": "#bfe3c6", "üst": "#f6cf9a", "tek": "#eadf9c"}
RENK_ADI = (("tam", "tam boy panel"), ("alt", "çapraz kesimin alt parçası"), ("üst", "aynı panelin artan parçası (karşı yüzde)"), ("tek", "artığı kullanılmayan parça"))
CIZGI = "#2f343c"
KISA_AD = {"ön": "ön", "arka": "arka", "sol": "sol", "sağ": "sağ"}


def _tr(x: float, n: int = 0) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def _lejant(d: dict, bos: bool = False) -> list:
    from matplotlib.patches import Patch
    var = {p.konum for ps in d["yuzler"].values() for p in ps}
    cik = [Patch(fc=RENK[a], ec=CIZGI, lw=0.7, label=ad) for a, ad in RENK_ADI if a in var]
    if bos:
        cik.append(Patch(fc="white", ec=CIZGI, lw=0.7, hatch="////", label="kullanılmayan"))
    return cik


def acilim_ciz(d: dict, cikti: Path, baslik: str) -> None:
    """Açılım: çatı mahyadan dışarı doğru açılır; her yüz gerçek boyutunda ve üstten görünür. Her parçada panel numarası."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon

    A, B = (x * 100 for x in d["plan_m"])
    H, r = d["egimli_boy_m"] * 100, (d["plan_m"][0] - d["plan_m"][1]) * 50
    # yüz koordinatı (x: saçak boyunca soldan, t: saçaktan yukarı; cm) → sayfa
    don = {"ön": lambda x, t: (-A / 2 + x, -H + t), "arka": lambda x, t: (A / 2 - x, H - t),
           "sol": lambda x, t: (-r - H + t, B / 2 - x), "sağ": lambda x, t: (r + H - t, -B / 2 + x)}
    gen, yuk = 2 * (r + H) + 140, 2 * H + 245
    fig, ax = plt.subplots(figsize=(13.2, 13.2 * 0.96 * yuk / gen / 0.935 + 0.1), dpi=140)
    for ad, ps in d["yuzler"].items():
        f = don[ad]
        for p in ps:
            kose = [f(x * 100, t * 100) for x, t in p.kose]
            ax.add_patch(MplPolygon(kose, closed=True, fc=RENK[p.konum], ec=CIZGI, lw=0.7, zorder=2))
            alan = abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1]))) / 2
            if alan < 1200:       # çok küçük köşe parçası: numara sığmaz
                continue
            # numara: parçanın ağırlık merkezine
            cx = sum((x0 + x1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1]))
            cy = sum((y0 + y1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1]))
            a2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1]))
            ax.text(cx / (3 * a2), cy / (3 * a2), str(p.panel), ha="center", va="center", fontsize=11.5 if alan > 9000 else 8.6, color="#12161b", zorder=4)
        # yüzün dış çizgisi
        E = (A if ad in ("ön", "arka") else B) / 100
        y0 = d["plan_m"][1] / 2
        cevre = [(0, 0), (E, 0)] + ([(E - y0, d["egimli_boy_m"]), (y0, d["egimli_boy_m"])] if E - 2 * y0 > EPS else [(y0, d["egimli_boy_m"])])
        ax.add_patch(MplPolygon([f(x * 100, t * 100) for x, t in cevre], closed=True, fc="none", ec="#12161b", lw=1.8, zorder=3))
    ax.plot([-r, r], [0, 0], color="#12161b", lw=3.2, zorder=5, solid_capstyle="round")
    # ölçüler ve yüz adları
    kucuk = dict(fontsize=10.5, color="#3a4350", ha="center", va="center")
    ax.text(0, -H - 38, f"ÖN YÜZ · saçak {_tr(A)} cm", **kucuk)
    ax.text(0, H + 38, f"ARKA YÜZ · saçak {_tr(A)} cm", **kucuk)
    ax.text(-r - H - 38, 0, f"SOL YÜZ · saçak {_tr(B)} cm", rotation=90, **kucuk)
    ax.text(r + H + 38, 0, f"SAĞ YÜZ · saçak {_tr(B)} cm", rotation=90, **kucuk)
    if r > 60:
        ax.text(0, 24, f"mahya {_tr(2 * r)} cm", fontsize=10, color="#12161b", ha="center", va="center", zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85))
    ax.set_xlim(-r - H - 70, r + H + 70)
    ax.set_ylim(-H - 175, H + 70)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=_lejant(d), loc="upper left", bbox_to_anchor=(0.0, 0.09), ncol=4, frameon=False, fontsize=10.5, handlelength=1.6, columnspacing=1.6, borderaxespad=0.0)
    tasma_yazi = f" Kaplama saçaktan {_tr(d['tasma_m'] * 100, 1).replace(',0', '')} cm taşar (kalın çizginin dışı)." if d["tasma_m"] > EPS else ""
    ax.text(0.0, 0.022, f"Sayı: panel numarası. Aynı numara iki yüzde görünüyorsa iki parça aynı panelden çıkar. Eğimli boy {_tr(H, 1)} cm; her yüz gerçek boyutunda."
            + tasma_yazi, fontsize=9.6, color="#3a4350", ha="left", va="center", transform=ax.transAxes)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.945, bottom=0.01)
    fig.suptitle(baslik, fontsize=13.5, weight="bold", x=0.03, ha="left", y=0.985)
    fig.savefig(cikti, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def kesim_ciz(d: dict, cikti: Path, baslik: str) -> None:
    """Kesim planı: her panel bir dikdörtgen; içinde gönye kesimleri (yatay), çapraz kesimler ve parçaların gideceği yer."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon

    w, boy, k = d["kapatma_m"] * 100, d["boy_m"] * 100, d["adim_m"] / d["kapatma_m"]
    n = len(d["paneller"])
    satir_n = 2 if n > 16 else 1
    sutun = tavan(n / satir_n)
    ara, satir_ara = w * 0.42, 95
    gen = sutun * (w + ara) - ara
    ust_y, alt_y = boy + 60, -(satir_n - 1) * (boy + satir_ara) - 150
    fig, ax = plt.subplots(figsize=(13.2, 13.2 * 0.96 * (ust_y - alt_y) / (gen + 60) / 0.94 + 0.1), dpi=140)
    yer: dict[int, list] = {}
    for no, q, kose, _ in panel_yerlesimi(d):
        yer.setdefault(no, []).append((q, [(x * 100, y * 100) for x, y in kose]))
    for i, pn in enumerate(d["paneller"]):
        sx = (i % sutun) * (w + ara)
        sy = -(i // sutun) * (boy + satir_ara)
        ax.add_patch(MplPolygon([(sx, sy), (sx + w, sy), (sx + w, sy + boy), (sx, sy + boy)], closed=True, fc="white", ec=CIZGI, lw=0.6, hatch="////", zorder=1))
        for q, kose in yer.get(pn["no"], []):
            kose = [(sx + x, sy + y) for x, y in kose]
            ax.add_patch(MplPolygon(kose, closed=True, fc=RENK[q.konum], ec=CIZGI, lw=0.7, zorder=2))
            ys = [y for _, y in kose]
            if max(ys) - min(ys) > 70:
                a2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1]))
                cx = sum((x0 + x1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1])) / (3 * a2)
                cy = sum((y0 + y1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1])) / (3 * a2)
                ax.text(cx, cy, f"{KISA_AD[q.yuz]} {q.serit}", rotation=90, ha="center", va="center", fontsize=9.6, color="#12161b", zorder=4)
        ax.add_patch(MplPolygon([(sx, sy), (sx + w, sy), (sx + w, sy + boy), (sx, sy + boy)], closed=True, fc="none", ec="#12161b", lw=1.3, zorder=3))
        ax.text(sx + w / 2, sy + boy + 16, str(pn["no"]), ha="center", va="bottom", fontsize=11.5, weight="bold", color="#12161b")
    ax.set_xlim(-30, gen + 30)
    ax.set_ylim(alt_y, ust_y)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=_lejant(d, bos=True), loc="upper left", bbox_to_anchor=(0.0, 0.105), ncol=5, frameon=False, fontsize=10.5, handlelength=1.6, columnspacing=1.6, borderaxespad=0.0)
    ax.text(0.0, 0.025, f"Her dikdörtgen bir panel ({_tr(w)} × {_tr(boy, 1).replace(',0', '')} cm; saçak ucu altta). İçindeki yazı parçanın gideceği yer: yüz ve şerit numarası (soldan). "
            "Kesim ölçüleri ayrı tabloda.",
            fontsize=9.6, color="#3a4350", ha="left", va="center", transform=ax.transAxes)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.01)
    fig.suptitle(baslik, fontsize=13.5, weight="bold", x=0.03, ha="left", y=0.99)
    fig.savefig(cikti, bbox_inches="tight", facecolor="white")
    plt.close(fig)


KAPLAMA_ADI = {"sandvic_panel": "sandviç panel", "tek_kat_panel": "tek kat panel", "osb_kiremit": "kiremit desen sac", "osb_trapez": "trapez sac", "trapez_sac": "trapez sac"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("girdi", type=Path, help="yükleme girdisi (girdi_uret.py çıktısı)")
    ap.add_argument("--kaplama", choices=list(KAPATMA_KURALI), help="girdidekinin yerine bu kaplama")
    ap.add_argument("--cikti", type=Path, help="dizilimi JSON olarak yaz")
    ap.add_argument("--acilim-png", type=Path)
    ap.add_argument("--kesim-png", type=Path)
    ap.add_argument("--olcu-md", type=Path, help="parça ölçüleri ve panel kesimleri (markdown; montajcıya verilecek kesim planının ölçüleri)")
    a = ap.parse_args()
    g = json.loads(a.girdi.read_text(encoding="utf-8"))
    kr = kural.oku()
    c = g["cati"]
    if c["tip"] != "kirma":
        raise SystemExit("Açılım dizilimi yalnız kırma çatı için")
    kaplama = a.kaplama or c["kaplama"]
    d = kural_dizilimi(kr, c, kaplama)
    if d is None:
        raise SystemExit(f"Dizilim kurulamadı (kaplama şerit olarak dizilmiyor, çatı planı yok ya da panel kısa): {kaplama}")
    kapatma, boy_mm = d["kapatma_m"], round(d["boy_m"] * 1000)
    print(f"{g['ad']}: {KAPLAMA_ADI[kaplama]}, {_tr(kapatma * 100)} cm kapatır, L {boy_mm}")
    if d["uzatma"]:
        u = d["uzatma"]
        if u.get("neden") == "pay":
            print(f"  panel boyu uzatıldı (pay koşulu): taban L {u['taban_boy_mm']} ile de {u['taban_adet']}, ama kesim payı {_tr(u['taban_pay_siniri_mm'], 1)} mm'yi geçerse "
                  f"{u['taban_saglamlik_adet']}; L {u['boy_mm']} ile 1 cm payla {u['saglamlik_adet']}")
        else:
            print(f"  panel boyu uzatıldı: taban L {u['taban_boy_mm']} ile {u['taban_adet']}, L {u['boy_mm']} ile {u['adet']} (adedin düştüğü en kısa boy L {u['esik_boy_mm']})")
    print(f"  yüzey {_tr(d['yuzey_m2'], 2)} m² · eğimli boy {_tr(d['egimli_boy_m'] * 100, 1)} cm · taşma {_tr(d['tasma_m'] * 100, 1)} cm · parça {d['parca_adedi']}")
    print(f"  panel {d['adet']} (tam boy {d['tam_boy_adedi']}, iki parça veren kesim {d['cift_adedi']}, artığı kullanılmayan parça {d['tek_adedi']}) · alan olarak en az {d['alan_alt_siniri']}")
    print(f"  başlangıç: {BASLANGIC_ADI[d['baslangic']]} · denemeler {d['denemeler']} · en dar pay",
          "—" if d["en_dar_pay_m"] is None else f"{_tr(d['en_dar_pay_m'] * 100, 1)} cm", f"· kesim payı {_tr(d['kesim_payi_m'] * 1000)} mm; paysız {d['paysiz_adet']}, 1 cm payla {d['bir_cm_payla_adet']}")
    for pn in d["paneller"]:
        print(f"  {pn['no']:>3}: " + " + ".join(" ve ".join(f"{p.yuz} {p.serit}" for p in x["parcalar"]) + f" [{_tr(x['boy'] * 100, 1)}]" for x in pn["dikdortgenler"])
              + f"  · artan {_tr(pn['kalan'] * 100, 1)} cm")
    ad = g["ad"].split(" ")[0]
    alt = f"{KAPLAMA_ADI[kaplama]} · {_tr(kapatma * 100)} cm kapatır · L {boy_mm} · {d['adet']} adet"
    if a.cikti:
        s = sozluk(d)
        s.update({"ad": g["ad"], "kaplama": kaplama, "baslangica_gore_adet": d["denemeler"], "kesim_payisiz_adet": d["paysiz_adet"], "bir_cm_kesim_payiyla_adet": d["bir_cm_payla_adet"],
                  "taban_boy_m": d["taban_boy_m"], "taban_adet": d["taban_adet"], "uzatma": d["uzatma"], "uzun_panelle": d["uzun_panelle"]})
        a.cikti.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.acilim_png:
        acilim_ciz(d, a.acilim_png, f"{ad} · çatı açılımı ve kaplama dizilimi · {alt}")
    if a.kesim_png:
        kesim_ciz(d, a.kesim_png, f"{ad} · kesim planı · {alt}")
    if a.olcu_md:
        # Tam boy giden panelde mahya ucunda kalan fazlalık: panel boyu − (eğimli boy + taşma). Boy 10 mm'ye yuvarlanıyorsa (kural; 7 Ekim 2026) yuvarlama payı da
        # bunun içindedir; kural yokken taban boy mm'ye yuvarlıydı ve fazlalık uzatma kadardı (eski metin).
        yuvarlamali = ((kr.get("panel_boyu_yuvarlama_mm") or {}).get("deger") or 1) > 1
        fazla_cm = _tr((d["boy_m"] - (d["egimli_boy_m"] + d["tasma_m"] if yuvarlamali else d["taban_boy_m"])) * 100, 1)
        a.olcu_md.write_text("\n".join(
            [f"# {ad} · kesim planının ölçüleri · {alt}", "",
             f"Hesap çıktısıdır; elle düzeltilmez (`cati_acilim.py --olcu-md`). Dizilim {BASLANGIC_ADI[d['baslangic']]} başlar; kaplama saçaktan {_tr(d['tasma_m'] * 100, 1)} cm taşar; "
             f"kesim payı {_tr(d['kesim_payi_m'] * 1000)} mm. Ölçüler cm. Boylar saçak ucundan (taşma dahil) ölçülür; sol ve sağ, çatıya dışarıdan bakışla.", ""]
            + ([f"Panel boyu pay kalsın diye uzatıldı (4 Ekim 16:18 kuralındaki pay koşulu, taban boya da uygulandı; 7 Ekim 2026): taban boy L {d['uzatma']['taban_boy_mm']} "
                f"(eğimli boy + taşma, yukarı yuvarlanmış) ile de {d['uzatma']['taban_adet']} panel çıkıyor, ama pay ince: "
                f"kesim payı {_tr(d['uzatma']['taban_pay_siniri_mm'], 1)} mm'yi geçerse {d['uzatma']['taban_saglamlik_adet']} panel gerekir. L {d['uzatma']['boy_mm']} ile kesim payı 1 cm olsa "
                + (f"da {d['uzatma']['adet']} panel yetiyor. " if d['uzatma']['saglamlik_adet'] == d['uzatma']['adet'] else f"{d['uzatma']['saglamlik_adet']} panel gerekir. ")
                + f"Taşma değişmez: tam boy giden panellerde fazla {fazla_cm} cm panelin üst ucunda (mahya ucunda) kalır.", ""]
               if d["uzatma"] and d["uzatma"].get("neden") == "pay" else
               [f"Panel boyu kuralla uzatıldı (Lokman, 4 Ekim 16:18): taban boy L {d['uzatma']['taban_boy_mm']} (eğimli boy + taşma) ile {d['uzatma']['taban_adet']} panel gerekiyordu; "
                f"L {d['uzatma']['boy_mm']} ile {d['uzatma']['adet']} panel yetiyor. Taşma değişmez: tam boy giden panellerde fazla "
                f"{fazla_cm} cm panelin üst ucunda (mahya ucunda) kalır.", ""] if d["uzatma"] else [])
            + ["## Parçalar (yüz yüz, soldan sağa)", ""] + parca_tablosu(d)
            + ["", "## Kesim ölçüleri (panel panel)", "",
               "Her satır bir parçanın paneldeki yeridir: panelin sol ve sağ kenarında, alt uçtan (saçak ucu) kaç cm ile kaç cm arası. "
               "Parça bu iki aralığın arasında kalan dörtgendir. \"180° çevrilerek\" yazan parça, düz ucu saçağa gelecek biçimde çevrilip karşı yüze konur; ters yüz edilmez.", ""]
            + panel_tablosu(d) + ["", "## Paneller (özet)", ""] + panel_ozeti(d)) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
