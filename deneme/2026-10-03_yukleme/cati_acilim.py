#!/usr/bin/env python3
"""Kırma çatının açılımı ve kaplama dizilimi: kaplama adedi buradan çıkar.

Lokman, 4 Ekim 2026 01:42: kırma çatıda kaplama adedi AutoCAD'e bırakılmaz. Çatı eğimine göre çizilir, zarf açar gibi açılır
ve kaplama yüzeye dizilir. Çapraz kesimden artan parça karşı tarafta, aynı açılı yere kullanılır: sol üçgende kullanılan
panelin artanı sağ üçgene, ön yamuktan çıkan açılı kesilmiş parça arka yamuğun aynı biçimdeki açılı yerine.

Model (dikdörtgen planlı, dört yanı eşit eğimli kırma çatı):
  - Dört yüz gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ).
    Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Kırma çizgisi açılımda bütün yüzlerde aynı açıdadır.
  - Her yüz, saçağa dik, `kapatma` genişliğinde şeritlere bölünür. Dizilimin başladığı yer seçilebilir (köşe ya da orta);
    kurallardaki sırayla denenir ve en az paneli veren başlangıç alınır.
  - Kaplama saçak çizgisinden `tasma` kadar dışarı uzar (mühendis, 4 Ekim 2026 12:14: 5 cm): her parçanın boyu o kadar artar.
  - Şerit parçası: düz (tam boy dikdörtgen), L (boyu soldan sağa artan), R (azalan) ya da karma (içinde mahya ucu ya da tepe var).
  - Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır:
    alt parça olduğu gibi kullanılır; üst parça, düz ucu saçağa gelecek biçimde karşı yüze taşınır. Üst parça alt parçayla
    aynı türdendir (L ise L). İki parçanın birlikte istediği boy: uzun kenarların toplamı − bir şeritlik boy farkı.
  - Eşleme: en uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır.
    Dikdörtgenler panellere büyükten küçüğe, ilk sığana yerleştirilir.
  - Boy bindirmesi yoktur. Kesim payı (`kesim_payi`): çapraz kesimde iki parçanın arasına ve aynı panelden çıkan
    dikdörtgenlerin arasına eklenir; birkaç milimetrelik paya güvenilmesin diye kurallarda 5 mm (varsayım).
    Panel tek boydur: eğimli boy + taşma (Excel motorundaki gibi; mm'ye yukarı).
Hesapta LLM yok: aynı girdi aynı dizilimi verir.

Kullanım:
    python cati_acilim.py sonuc/C8201_girdi.json --cikti sonuc/C8201_cati_acilim.json \\
        --acilim-png sonuc/C8201_cati_acilim.png --kesim-png sonuc/C8201_cati_kesim.png
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

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


def kural_dizilimi(kr: dict, cati: dict, kaplama: str) -> dict | None:
    """Kurallardaki ayarlarla kırma çatının dizilimi: taşma, kesim payı, artan parçanın kullanılıp kullanılmayacağı ve
    başlangıç seçimi (kurallardaki sırayla denenir; en az paneli veren ilk başlangıç alınır).
    Panel boyu listeden geliyorsa ve eğimli boy + taşmadan kısaysa taşma panelin yettiği kadardır.
    Dönen: dizilim sözlüğü ve ek olarak denemeler, paysız ve 1 cm paylı adet. Çatı planı yoksa ya da panel eğimli boydan kısaysa None."""
    if not (cati.get("plan_m") and cati.get("panel_boyu_m") and cati.get("egim")) or kaplama not in KAPATMA_KURALI:
        return None
    kd = kr["kirma_cati_dizilim"]["deger"]
    px, py, egim, boy = cati["plan_m"][0], cati["plan_m"][1], cati["egim"], cati["panel_boyu_m"]
    H = min(px, py) / 2 * math.sqrt(1 + egim * egim)
    if boy + EPS < H:
        return None
    kapatma = kr[KAPATMA_KURALI[kaplama]]["deger"]
    paylas = kaplama not in kd["artan_parca_kullanilmayan_kaplamalar"]
    tasma = max(0.0, min(kr["cati_kaplama_tasma_m"]["deger"], boy - H))
    pay = kd["kesim_payi_m"]
    den = {b: dizilim(px, py, egim, kapatma, boy, paylas, b, pay, tasma)["adet"] for b in kd["baslangic_sirasi"]}
    secilen = next(b for b in kd["baslangic_sirasi"] if den[b] == min(den.values()))
    d = dizilim(px, py, egim, kapatma, boy, paylas, secilen, pay, tasma)
    d.update(denemeler=den, kaplama=kaplama, tasma_kural_m=kr["cati_kaplama_tasma_m"]["deger"],
             paysiz_adet=dizilim(px, py, egim, kapatma, boy, paylas, secilen, 0.0, tasma)["adet"],
             bir_cm_payla_adet=dizilim(px, py, egim, kapatma, boy, paylas, secilen, 0.01, tasma)["adet"])
    return d


def sozluk(d: dict) -> dict:
    """JSON'a yazılacak biçim (ölçüler m, üç hane)."""
    def r(x: float) -> float:
        return round(x, 3)
    return {"plan_m": [r(x) for x in d["plan_m"]], "egim": d["egim"], "kapatma_m": d["kapatma_m"], "panel_boyu_m": d["boy_m"],
            "artan_parca_karsi_yuzde": d["paylas"], "baslangic": d["baslangic"], "baslangic_adi": BASLANGIC_ADI[d["baslangic"]],
            "egimli_boy_m": r(d["egimli_boy_m"]), "mahya_m": r(d["mahya_m"]), "tasma_m": r(d["tasma_m"]),
            "yuzey_m2": round(d["yuzey_m2"], 2), "kaplanan_m2": round(d["kaplanan_m2"], 2), "adet": d["adet"], "alan_alt_siniri": d["alan_alt_siniri"],
            "tam_boy_panel": d["tam_boy_adedi"], "iki_parca_veren_kesim": d["cift_adedi"], "artigi_kullanilmayan_parca": d["tek_adedi"], "parca_adedi": d["parca_adedi"],
            "kesim_payi_m": d["kesim_payi_m"], "en_dar_pay_m": None if d["en_dar_pay_m"] is None else r(d["en_dar_pay_m"]),
            "yuzler": {ad: [{"serit": p.serit, "x0_m": r(p.x0), "x1_m": r(p.x1), "tip": p.tip, "uzun_m": r(p.uzun), "kisa_m": r(p.kisa), "panel": p.panel, "konum": p.konum}
                            for p in ps] for ad, ps in d["yuzler"].items()},
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
    for i, pn in enumerate(d["paneller"]):
        sx = (i % sutun) * (w + ara)
        sy = -(i // sutun) * (boy + satir_ara)
        taban = 0.0
        ax.add_patch(MplPolygon([(sx, sy), (sx + w, sy), (sx + w, sy + boy), (sx, sy + boy)], closed=True, fc="white", ec=CIZGI, lw=0.6, hatch="////", zorder=1))
        for dk in pn["dikdortgenler"]:
            l = dk["boy"] * 100
            ps = dk["parcalar"]
            sekiller = []
            if len(ps) == 1 and ps[0].konum == "tam":
                p = ps[0]
                sekiller.append((p, [((x - p.x0) * 100, (t + d["tasma_m"]) * 100) for x, t in p.kose]))
            else:
                alt = ps[0]
                a, b, en = alt.uzun * 100, alt.kisa * 100, alt.en * 100
                if alt.tip == "L":     # boyu sağa doğru artar; dar parça sağa yaslanır
                    sekiller.append((alt, [(w - en, 0), (w, 0), (w, a), (w - en, b)]))
                else:
                    sekiller.append((alt, [(0, 0), (en, 0), (en, b), (0, a)]))
                if len(ps) == 2:
                    ust = ps[1]
                    a, b, en = ust.uzun * 100, ust.kisa * 100, ust.en * 100
                    if ust.tip == "L":   # üst parça çevrilmeden önce: kalın ucu solda, yukarıdan asılı
                        sekiller.append((ust, [(0, l), (en, l), (en, l - b), (0, l - a)]))
                    else:
                        sekiller.append((ust, [(w, l), (w - en, l), (w - en, l - b), (w, l - a)]))
            for p, kose in sekiller:
                kose = [(sx + x, sy + taban + y) for x, y in kose]
                ax.add_patch(MplPolygon(kose, closed=True, fc=RENK[p.konum], ec=CIZGI, lw=0.7, zorder=2))
                ys = [y for _, y in kose]
                if max(ys) - min(ys) > 70:
                    a2 = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1]))
                    cx = sum((x0 + x1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1])) / (3 * a2)
                    cy = sum((y0 + y1) * (x0 * y1 - x1 * y0) for (x0, y0), (x1, y1) in zip(kose, kose[1:] + kose[:1])) / (3 * a2)
                    ax.text(cx, cy, f"{KISA_AD[p.yuz]} {p.serit}", rotation=90, ha="center", va="center", fontsize=9.6, color="#12161b", zorder=4)
            taban += l
        ax.add_patch(MplPolygon([(sx, sy), (sx + w, sy), (sx + w, sy + boy), (sx, sy + boy)], closed=True, fc="none", ec="#12161b", lw=1.3, zorder=3))
        ax.text(sx + w / 2, sy + boy + 16, str(pn["no"]), ha="center", va="bottom", fontsize=11.5, weight="bold", color="#12161b")
    ax.set_xlim(-30, gen + 30)
    ax.set_ylim(alt_y, ust_y)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=_lejant(d, bos=True), loc="upper left", bbox_to_anchor=(0.0, 0.105), ncol=5, frameon=False, fontsize=10.5, handlelength=1.6, columnspacing=1.6, borderaxespad=0.0)
    ax.text(0.0, 0.025, f"Her dikdörtgen bir panel ({_tr(w)} × {_tr(boy)} cm; saçak ucu altta). İçindeki yazı parçanın gideceği yer: yüz ve şerit numarası (soldan).",
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
    a = ap.parse_args()
    g = json.loads(a.girdi.read_text(encoding="utf-8"))
    kr = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))
    c = g["cati"]
    if c["tip"] != "kirma":
        raise SystemExit("Açılım dizilimi yalnız kırma çatı için")
    kaplama = a.kaplama or c["kaplama"]
    d = kural_dizilimi(kr, c, kaplama)
    if d is None:
        raise SystemExit(f"Dizilim kurulamadı (kaplama şerit olarak dizilmiyor, çatı planı yok ya da panel kısa): {kaplama}")
    kapatma, boy_mm = d["kapatma_m"], round(c["panel_boyu_m"] * 1000)
    print(f"{g['ad']}: {KAPLAMA_ADI[kaplama]}, {_tr(kapatma * 100)} cm kapatır, L {boy_mm}")
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
        s.update({"ad": g["ad"], "kaplama": kaplama, "baslangica_gore_adet": d["denemeler"], "kesim_payisiz_adet": d["paysiz_adet"], "bir_cm_kesim_payiyla_adet": d["bir_cm_payla_adet"]})
        a.cikti.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.acilim_png:
        acilim_ciz(d, a.acilim_png, f"{ad} · çatı açılımı ve kaplama dizilimi · {alt}")
    if a.kesim_png:
        kesim_ciz(d, a.kesim_png, f"{ad} · kesim planı · {alt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
