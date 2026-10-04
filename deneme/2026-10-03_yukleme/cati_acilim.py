#!/usr/bin/env python3
"""Kırma çatının açılımı ve kaplama dizilimi: kaplama adedi buradan çıkar.

Lokman, 4 Ekim 2026 01:42: kırma çatıda kaplama adedi AutoCAD'e bırakılmaz. Çatı eğimine göre çizilir, zarf açar gibi açılır
ve kaplama yüzeye dizilir. Çapraz kesimden artan parça karşı tarafta, aynı açılı yere kullanılır: sol üçgende kullanılan
panelin artanı sağ üçgene, ön yamuktan çıkan açılı kesilmiş parça arka yamuğun aynı biçimdeki açılı yerine.

Model (dikdörtgen planlı, dört yanı eşit eğimli kırma çatı):
  - Dört yüz gerçek boyutuyla açılır: uzun saçaklarda iki yamuk (ön, arka), kısa saçaklarda iki üçgen (sol, sağ).
    Yüzün yüksekliği eğimli boydur: (kısa kenar ÷ 2) × √(1 + eğim²). Kırma çizgisi açılımda bütün yüzlerde aynı açıdadır.
  - Her yüz, saçağa dik, `kapatma` genişliğinde şeritlere bölünür. Dizilim dışarıdan bakışla sol köşeden başlar (varsayım).
  - Şerit parçası: düz (tam boy dikdörtgen), L (boyu soldan sağa artan), R (azalan) ya da karma (içinde mahya ucu ya da tepe var).
  - Bir panel gönyesinde kesilerek kısa dikdörtgenlere, her dikdörtgen tek bir çapraz kesimle iki parçaya ayrılır:
    alt parça olduğu gibi kullanılır; üst parça, düz ucu saçağa gelecek biçimde karşı yüze taşınır. Üst parça alt parçayla
    aynı türdendir (L ise L). İki parçanın birlikte istediği boy: uzun kenarların toplamı − bir şeritlik boy farkı.
  - Eşleme: en uzun parçadan başlanır; karşı yüzde, onunla aynı panelden çıkabilen en uzun parça eş yapılır.
    Dikdörtgenler panellere büyükten küçüğe, ilk sığana yerleştirilir.
  - Boy bindirmesi yoktur; kesim payı sıfır alınır (`kesim_payi` ile denenebilir: kesilen her dikdörtgene eklenir).
    Panel tek boydur (eğimli boy, 10 cm'ye yukarı yuvarlanmış).
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
             "plan_yonu": {"ön": "sol", "arka": "sag", "sol": "sol", "sağ": "sag"}}


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


def yuz_parcalari(ad: str, sacak: float, y0: float, k: float, kapatma: float, baslangic: str) -> list[Parca]:
    """Bir yüzün şerit parçaları. Yüzün boyu x'te: k × min(x, y0, saçak − x)."""
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
        cik.append(Parca(ad, len(cik) + 1, a, b, tip, max(t for _, t in ust), min(ha, hb), [(a, 0.0), (b, 0.0)] + ust))
    return cik


def es_boyu(p: Parca, q: Parca, adim: float) -> float:
    """Aynı türden iki parçanın tek dikdörtgenden çıkması için gereken boy. `adim`: bir şerit genişliğinde boyun değişimi.
    Dar parça ötekinin ince ucuna yerleşir: en çok (uzun kenarların toplamı − adım), en az iki uzun kenarın büyüğü."""
    return max(p.uzun, q.uzun, p.uzun + q.uzun - adim)


def dizilim(px: float, py: float, egim: float, kapatma: float, boy: float, paylas: bool = True, baslangic: str = "sol", kesim_payi: float = 0.0) -> dict:
    """Kırma çatının açılımı ve kaplama dizilimi. `paylas`: çapraz kesimden artan parça karşı yüzde kullanılır.
    `kesim_payi` (m): kesilerek çıkan her dikdörtgenin boyuna eklenir (tam boy paneller hariç); sağlama içindir."""
    uzun_k, kisa_k = max(px, py), min(px, py)
    y0, k = kisa_k / 2, math.sqrt(1 + egim * egim)
    H = y0 * k
    if boy + EPS < H:
        raise ValueError(f"Panel boyu ({boy} m) eğimli boydan ({H:.3f} m) kısa; boy bindirmeli dizilim bu modelde yok")
    adim = k * kapatma
    bas = BASLANGIC[baslangic]
    yuzler = {"ön": yuz_parcalari("ön", uzun_k, y0, k, kapatma, bas["ön"]), "arka": yuz_parcalari("arka", uzun_k, y0, k, kapatma, bas["arka"]),
              "sol": yuz_parcalari("sol", kisa_k, y0, k, kapatma, bas["sol"]), "sağ": yuz_parcalari("sağ", kisa_k, y0, k, kapatma, bas["sağ"])}
    hepsi = [p for ad in NUMARA_SIRASI for p in yuzler[ad]]
    sira = {id(p): i for i, p in enumerate(hepsi)}

    # 1) dikdörtgenler: tam boy ve karma parçalar tek başına; L ve R parçalar karşı yüzdeki eşleriyle
    dikdortgenler: list[dict] = []
    for p in hepsi:
        if p.tip in ("duz", "karma"):
            p.konum = "tam"
            dikdortgenler.append({"boy": p.uzun, "parcalar": [p]})
    for cift in (("ön", "arka"), ("sol", "sağ")):
        for tip in ("L", "R"):
            grup = sorted((p for p in hepsi if p.yuz in cift and p.tip == tip), key=lambda p: (-p.uzun, sira[id(p)]))
            bitti: set[int] = set()
            for p in grup:
                if id(p) in bitti:
                    continue
                bitti.add(id(p))
                es = next((q for q in grup if id(q) not in bitti and q.yuz == KARSI[p.yuz] and es_boyu(p, q, adim) + kesim_payi <= boy + EPS), None) if paylas else None
                if es is None:
                    p.konum = "tek"
                    dikdortgenler.append({"boy": min(p.uzun + kesim_payi, boy), "parcalar": [p]})
                    continue
                bitti.add(id(es))
                alt, ust = (p, es) if p.yuz in ALT_YUZ else (es, p)
                alt.konum, ust.konum = "alt", "üst"
                dikdortgenler.append({"boy": es_boyu(p, es, adim) + kesim_payi, "parcalar": [alt, ust]})

    # 2) dikdörtgenler panellere: büyükten küçüğe, ilk sığana
    dikdortgenler.sort(key=lambda d: (-d["boy"], sira[id(d["parcalar"][0])]))
    paneller: list[dict] = []
    for d in dikdortgenler:
        for pn in paneller:
            if d["boy"] <= pn["kalan"] + EPS:
                pn["kalan"] -= d["boy"]
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
    return {"plan_m": [uzun_k, kisa_k], "egim": egim, "kapatma_m": kapatma, "boy_m": boy, "paylas": paylas, "baslangic": baslangic,
            "egimli_boy_m": H, "mahya_m": uzun_k - kisa_k, "adim_m": adim, "yuzey_m2": yuzey,
            "yuzler": yuzler, "paneller": paneller, "adet": len(paneller),
            "alan_alt_siniri": tavan(yuzey / (kapatma * boy)),
            "tam_boy_adedi": sum(1 for p in hepsi if p.konum == "tam"),
            "cift_adedi": sum(1 for p in hepsi if p.konum == "alt"),
            "tek_adedi": sum(1 for p in hepsi if p.konum == "tek"),
            "parca_adedi": len(hepsi), "kesim_payi_m": kesim_payi,
            # en dar pay: kesilen panellerde artan boyun en küçüğü (tam boy paneller hariç)
            "en_dar_pay_m": min((pn["kalan"] for pn in paneller if any(p.konum != "tam" for x in pn["dikdortgenler"] for p in x["parcalar"])), default=None)}


def adet_denemeleri(px: float, py: float, egim: float, kapatma: float, boy: float, paylas: bool = True) -> dict:
    """Dizilimin başladığı köşe değişince adet: sağlama için."""
    return {b: dizilim(px, py, egim, kapatma, boy, paylas, b)["adet"] for b in BASLANGIC}


def sozluk(d: dict) -> dict:
    """JSON'a yazılacak biçim (ölçüler m, üç hane)."""
    def r(x: float) -> float:
        return round(x, 3)
    return {"plan_m": [r(x) for x in d["plan_m"]], "egim": d["egim"], "kapatma_m": d["kapatma_m"], "panel_boyu_m": d["boy_m"],
            "artan_parca_karsi_yuzde": d["paylas"], "baslangic": d["baslangic"], "egimli_boy_m": r(d["egimli_boy_m"]), "mahya_m": r(d["mahya_m"]),
            "yuzey_m2": round(d["yuzey_m2"], 2), "adet": d["adet"], "alan_alt_siniri": d["alan_alt_siniri"],
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
    ax.text(0.0, 0.022, f"Sayı: panel numarası. Aynı numara iki yüzde görünüyorsa iki parça aynı panelden çıkar. Eğimli boy {_tr(H, 1)} cm; her yüz gerçek boyutunda.",
            fontsize=9.6, color="#3a4350", ha="left", va="center", transform=ax.transAxes)
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
                sekiller.append((p, [((x - p.x0) * 100, t * 100) for x, t in p.kose]))
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
KAPATMA_KURALI = {"sandvic_panel": "sandvic_panel_kapatma_m", "tek_kat_panel": "tek_kat_panel_kapatma_m", "osb_kiremit": "kiremit_kapatma_m",
                  "osb_trapez": "trapez_sac_kapatma_m", "trapez_sac": "trapez_sac_kapatma_m"}


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
    if kaplama not in KAPATMA_KURALI:
        raise SystemExit(f"Bu kaplama şerit olarak dizilmiyor: {kaplama}")
    kapatma = kr[KAPATMA_KURALI[kaplama]]["deger"]
    paylas = kaplama not in kr["kirma_cati_dizilim"]["deger"]["artan_parca_kullanilmayan_kaplamalar"]
    d = dizilim(c["plan_m"][0], c["plan_m"][1], c["egim"], kapatma, c["panel_boyu_m"], paylas)
    den = adet_denemeleri(c["plan_m"][0], c["plan_m"][1], c["egim"], kapatma, c["panel_boyu_m"], paylas)
    print(f"{g['ad']}: {KAPLAMA_ADI[kaplama]}, {_tr(kapatma * 100)} cm kapatır, L {round(c['panel_boyu_m'] * 1000)}")
    print(f"  yüzey {_tr(d['yuzey_m2'], 2)} m² · eğimli boy {_tr(d['egimli_boy_m'] * 100, 1)} cm · parça {d['parca_adedi']}")
    print(f"  panel {d['adet']} (tam boy {d['tam_boy_adedi']}, iki parça veren kesim {d['cift_adedi']}, artığı kullanılmayan parça {d['tek_adedi']}) · alan olarak en az {d['alan_alt_siniri']}")
    pay1 = dizilim(c["plan_m"][0], c["plan_m"][1], c["egim"], kapatma, c["panel_boyu_m"], paylas, kesim_payi=0.01)["adet"]
    print("  başlangıç köşesine göre:", den, "· en dar pay", "—" if d["en_dar_pay_m"] is None else f"{_tr(d['en_dar_pay_m'] * 100, 1)} cm", f"· 1 cm kesim payıyla {pay1}")
    for pn in d["paneller"]:
        print(f"  {pn['no']:>3}: " + " + ".join(" ve ".join(f"{p.yuz} {p.serit}" for p in x["parcalar"]) + f" [{_tr(x['boy'] * 100, 1)}]" for x in pn["dikdortgenler"])
              + f"  · artan {_tr(pn['kalan'] * 100, 1)} cm")
    ad = g["ad"].split(" ")[0]
    alt = f"{KAPLAMA_ADI[kaplama]} · {_tr(kapatma * 100)} cm kapatır · L {round(c['panel_boyu_m'] * 1000)} · {d['adet']} adet"
    if a.cikti:
        s = sozluk(d)
        s.update({"ad": g["ad"], "kaplama": kaplama, "baslangic_kosesine_gore_adet": den, "bir_cm_kesim_payiyla_adet": pay1})
        a.cikti.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.acilim_png:
        acilim_ciz(d, a.acilim_png, f"{ad} · çatı açılımı ve kaplama dizilimi · {alt}")
    if a.kesim_png:
        kesim_ciz(d, a.kesim_png, f"{ad} · kesim planı · {alt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
