"""Tek genel pafta okuyucusu (İE-15 · KH-1; hakem aracı, D-24).

Prefabrik montaj paftasının PDF'ini yazıdan ve vektörden okur; LLM yok, ağ yok, elle okuma yok. Bugün üç sayfa okunur:
montaj planı (pano, köşe, kolon, kapı kanadı), H profil planı (H türleri lejanttaki renkten) ve makas–dere planı (makaslar).
Çıktı PR #28'in `pafta_katmani.json` biçimindedir (anahtar → {adet, not}; `motor/prefabrik_liste.py --pafta` değişmeden okur);
yerleşim kapısının istediği ayrıntı (H türleri ayrı, konumlar, makas boyları) `ayrinti` altında durur.

Sayfa başlığından bulunur, sayfa numarasından değil. Şablonun renkleri ve başlıkları aşağıdaki `VARSAYILAN`'dadır; projeye özgü
ayar (SHA, sayfa, renk) `projeler/<KOD>.json`'da görünür durur, koda gömülmez. Kodla okunamayan ya da uyarı veren bölüm (montaj,
h_plani, makas) `teyit_bekliyor`'a nedeniyle yazılır; o bölümün satırları katmana ve kapıya girmez. Çıktıya antetten yazı girmez; yalnız sayılar, konumlar ve MKnn etiketleri.

Çerçeve: cm; x binanın sol dış yüzünden, y ön dış yüzünden (önden bakışta paftanın altı). Döndürülmüş sayfalar `rotation_matrix`
ile görünen sayfaya çevrilir. Ölçek montaj sayfasında 125,5'lik standart panodan bulunur; dış ölçü yazısı bununla %3 içinde
tutuyorsa yazıdaki ölçü kullanılır. H ve makas sayfalarında duvar çizgilerinin sınırı montajdaki dış ölçüye oturtulur.

Koşma:
    python3 -I testler/kimlik/hakem/pafta_oku.py <pafta.pdf> --proje testler/kimlik/hakem/projeler/PK01.json [--cikti <json>]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import pymupdf as fitz

SURUM = "1"
VARSAYILAN = {
    "basliklar": {                          # sayfa başlığı (boşluklar teke indirilir, büyük harf); ilk eşleşen sayfa
        "montaj": r"MONTAJ( VE ELEKTRİK)? PLANI",
        "h": r"H (PROFİL )?(MONTAJ|YERLEŞİM) PLANI",
        "makas": r"MAKAS VE DERE YERLEŞİM PLANI",
    },
    "montaj": {
        "renkler": {"STD": [0.0, 0.0, 0.0], "OZEL": [0.0, 0.0, 1.0], "KOSE": [1.0, 0.0, 0.0], "KANAT": [0.047, 0.275, 0.592]},
        "std_pano_cm": 125.5,
        "kanat_cm": [60.0, 100.0],
    },
    "duvar_rengi": [0.388, 0.392, 0.4],     # H ve makas sayfalarında gri duvar çizgileri
    "makas": {"renk": None, "en_kisa_cm": 50.0},   # renk None: MK etiketlerinin yanındaki çizgilerden oylanır
    "sayfalar": {},                         # zorunlu sayfa numarası (1'den), başlık bulunamazsa
}
H_ETIKET = re.compile(r"(3'LÜ)?H\((DÜBELLİ&KULAKLI|DÜBELLİ|STANDART)\)")
H_TURU = {"DÜBELLİ&KULAKLI": "dubelli_kulakli", "DÜBELLİ": "dubelli", "STANDART": "standart"}
H_TURLERI = ["dubelli_kulakli", "dubelli", "standart", "uclu_dubelli_kulakli", "uclu_dubelli", "uclu_standart"]
H_ADI = {"dubelli_kulakli": "dübelli & kulaklı", "dubelli": "dübelli", "standart": "standart"}
SAYI = re.compile(r"\d+(?:[.,]\d+)?")
MK = re.compile(r"MK\s*(\d+)")


def _ayar(proje: dict | None) -> dict:
    a = copy.deepcopy(VARSAYILAN)

    def birlestir(h, k):
        for anahtar, d in k.items():
            if isinstance(d, dict) and isinstance(h.get(anahtar), dict):
                birlestir(h[anahtar], d)
            else:
                h[anahtar] = d
    birlestir(a, (proje or {}).get("ayar", {}))
    return a


def _renk(r) -> tuple:
    return tuple(round(v, 3) for v in (r or (9, 9, 9)))


def _ayni_renk(a, b, tol=0.01) -> bool:
    return a is not None and b is not None and len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t.replace("’", "'").replace("`", "'").replace("´", "'")).strip().upper()


def _satirlar(pg) -> list[tuple[str, fitz.Rect]]:
    """Sayfanın yazı satırları, görünen sayfa koordinatında."""
    rm, out = pg.rotation_matrix, []
    for b in pg.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).strip()
            if t:
                out.append((t, fitz.Rect(ln["bbox"]) * rm))
    return out


def _cizimler(pg):
    """(renk, öğe türü, görünen sayfadaki noktalar) üçlüleri; dörtgen için dört köşe, çizgi için iki uç, eğri için kutu."""
    rm = pg.rotation_matrix
    for d in pg.get_drawings():
        renk = _renk(d.get("color"))
        for it in d["items"]:
            if it[0] == "l":
                yield renk, "l", [it[1] * rm, it[2] * rm], d
            elif it[0] == "qu":
                q = it[1]
                yield renk, "qu", [q.ul * rm, q.ur * rm, q.lr * rm, q.ll * rm], d
            elif it[0] == "re":
                r = it[1]
                yield renk, "qu", [r.tl * rm, r.tr * rm, r.br * rm, r.bl * rm], d


def sayfalari_bul(doc, ayar: dict) -> dict[str, int]:
    """Başlıktan sayfa (0'dan). Aynı başlık iki sayfada varsa hata; bulunamazsa `sayfalar` ayarı, o da yoksa yok."""
    bulunan: dict[str, list[int]] = {k: [] for k in ayar["basliklar"]}
    for i, pg in enumerate(doc):
        metinler = {_norm(t) for t, _ in _satirlar(pg)}
        for k, kalip in ayar["basliklar"].items():
            if any(re.fullmatch(kalip, m) for m in metinler):
                bulunan[k].append(i)
    out = {}
    for k, v in bulunan.items():
        if k in ayar["sayfalar"]:
            out[k] = int(ayar["sayfalar"][k]) - 1
        elif len(v) == 1:
            out[k] = v[0]
        elif len(v) > 1:
            raise ValueError(f"'{k}' başlığı birden çok sayfada: {[i + 1 for i in v]}; proje ayarında `sayfalar` ile seçin")
    return out


# ── montaj planı ───────────────────────────────────────────────────────────────────────────────────────────────────────────

def _dik_dortgen(noktalar) -> tuple[fitz.Rect, bool]:
    xs, ys = [p.x for p in noktalar], [p.y for p in noktalar]
    r = fitz.Rect(min(xs), min(ys), max(xs), max(ys))
    eksende = all(min(abs(p.x - r.x0), abs(p.x - r.x1)) < 0.3 and min(abs(p.y - r.y0), abs(p.y - r.y1)) < 0.3 for p in noktalar)
    return r, eksende


def _olcu_yazilari(satirlar) -> list[float]:
    return sorted({float(t.replace(",", ".")) for t, _ in satirlar if SAYI.fullmatch(t.strip())})


def _isin_acik(p: dict, yon: str, isaret: int, oran: float, engeller: list[dict]) -> bool:
    """Panonun `oran`'daki noktasından, yüzüne dik ve `isaret` yönünde giden ışın başka bir duvar öğesine çarpmıyor mu."""
    x0, y0, x1, y1 = p["rect"]
    e = 0.01
    if yon == "x":                                    # yatay pano: ışın y boyunca
        xs = x0 + (x1 - x0) * oran
        for o in engeller:
            if o is p:
                continue
            a0, b0, a1, b1 = o["rect"]
            if a0 + e < xs < a1 - e and ((isaret > 0 and b1 > y1 + e) or (isaret < 0 and b0 < y0 - e)):
                if (isaret > 0 and b0 >= y1 - e) or (isaret < 0 and b1 <= y0 + e):
                    return False
        return True
    ys = y0 + (y1 - y0) * oran
    for o in engeller:
        if o is p:
            continue
        a0, b0, a1, b1 = o["rect"]
        if b0 + e < ys < b1 - e and ((isaret > 0 and a1 > x1 + e) or (isaret < 0 and a0 < x0 - e)):
            if (isaret > 0 and a0 >= x1 - e) or (isaret < 0 and a1 <= x0 + e):
                return False
    return True


def _paralel_kacis(p: dict, engeller: list[dict], d: float = 1.0) -> bool:
    """Panonun bir yüzünün `d` cm önünden, panoya paralel giden ışın üç noktada da hiçbir duvar öğesine çarpmıyor mu (önde girinti:
    nişin yan duvarı, yüzüne dik ışında iç görünür ama dışarıya açılır)."""
    x0, y0, x1, y1 = p["rect"]
    e = 0.01
    for yan in (-1, 1):
        for yon in (-1, 1):
            acik = True
            for oran in (0.25, 0.5, 0.75):
                if p["yon"] == "x":                   # yatay pano: paralel ışın x boyunca, yüzün önünde sabit y
                    c, s = (y0 - d) if yan < 0 else (y1 + d), x0 + (x1 - x0) * oran
                    ara = [(o["rect"][1], o["rect"][3], o["rect"][0], o["rect"][2]) for o in engeller if o is not p]
                else:
                    c, s = (x0 - d) if yan < 0 else (x1 + d), y0 + (y1 - y0) * oran
                    ara = [(o["rect"][0], o["rect"][2], o["rect"][1], o["rect"][3]) for o in engeller if o is not p]
                if any(c0 + e < c < c1 - e and (b1 > s + e if yon > 0 else b0 < s - e) for c0, c1, b0, b1 in ara):
                    acik = False
                    break
            if acik:
                return True
    return False


def _bilesenler(ogeler: list[dict], pay: float = 2.0) -> list[list[int]]:
    """Birbirine `pay` cm'den yakın duvar öğeleri (pano, köşe) bir zincirdir; zincirler büyükten küçüğe."""
    kok = list(range(len(ogeler)))

    def bul(i):
        while kok[i] != i:
            kok[i] = kok[kok[i]]
            i = kok[i]
        return i
    for i, a in enumerate(ogeler):
        for j in range(i + 1, len(ogeler)):
            b = ogeler[j]["rect"]
            if a["rect"][0] - pay <= b[2] and b[0] - pay <= a["rect"][2] and a["rect"][1] - pay <= b[3] and b[1] - pay <= a["rect"][3]:
                kok[bul(i)] = bul(j)
    gruplar: dict[int, list[int]] = {}
    for i in range(len(ogeler)):
        gruplar.setdefault(bul(i), []).append(i)
    return sorted(gruplar.values(), key=len, reverse=True)


def montaj_oku(pg, ayar: dict) -> dict:
    A = ayar["montaj"]
    renkler = {ad: tuple(v) for ad, v in A["renkler"].items()}
    satirlar = _satirlar(pg)
    ham, egik = [], 0
    for renk, tur, nok, _d in _cizimler(pg):
        if tur != "qu":
            continue
        ad = next((a for a, r in renkler.items() if _ayni_renk(renk, r)), None)
        if not ad:
            continue
        r, eksende = _dik_dortgen(nok)
        if not eksende:
            egik += 1
            continue
        ham.append((ad, r))
    yay = 0                                           # kapı kanadının açılım yayı: kanat renginde eğri
    for d in pg.get_drawings():
        if _ayni_renk(_renk(d.get("color")), renkler["KANAT"]):
            yay += sum(1 for it in d["items"] if it[0] == "c")

    # ölçek: standart panonun uzun kenarı (pt) ÷ 125,5 cm
    std = [r for ad, r in ham if ad == "STD" and max(r.width, r.height) > 3 * min(r.width, r.height)]
    if not std:
        raise ValueError("montaj sayfasında standart pano dörtgeni yok; renk ayarını denetleyin")
    s_std = statistics.median(max(r.width, r.height) for r in std) / A["std_pano_cm"]
    kal_pt = statistics.median(min(r.width, r.height) for r in std)

    def pano_mu(ad, r):
        L, t = max(r.width, r.height) / s_std, min(r.width, r.height) / s_std
        return ad in ("STD", "OZEL") and L >= 20 and 3 <= t <= 25 and L >= 2 * t
    duvar = [(ad, r) for ad, r in ham if pano_mu(ad, r) or (ad == "KOSE" and max(r.width, r.height) <= 1.3 * kal_pt)]
    X0, X1 = min(r.x0 for _, r in duvar), max(r.x1 for _, r in duvar)
    Y0, Y1 = min(r.y0 for _, r in duvar), max(r.y1 for _, r in duvar)
    W_pt, D_pt = X1 - X0, Y1 - Y0

    olculer = _olcu_yazilari(satirlar)

    def yazidan(uzunluk_pt):
        aday = [v for v in olculer if v > 0 and abs(uzunluk_pt / v - s_std) / s_std < 0.03]
        return min(aday, key=lambda v: abs(uzunluk_pt / v - s_std)) if aday else None
    W_y, D_y = yazidan(W_pt), yazidan(D_pt)
    sx = W_pt / W_y if W_y else s_std
    sy = D_pt / D_y if D_y else s_std
    uyarilar = []
    if egik:
        uyarilar.append(f"eksene oturmayan {egik} renkli dörtgen okunmadı")
    if abs(sx - sy) / sx > 0.01:
        uyarilar.append(f"x ve y ölçeği %1'den çok farklı ({sx:.5f} / {sy:.5f} pt/cm)")

    def cm(r):
        return [round((r.x0 - X0) / sx, 2), round((Y1 - r.y1) / sy, 2), round((r.x1 - X0) / sx, 2), round((Y1 - r.y0) / sy, 2)]

    boy_yazilari = [v for v in olculer if 30 < v < 260] + [A["std_pano_cm"]]
    panolar, koseler, kanatlar = [], [], []
    for ad, r in ham:
        k = cm(r)
        w, h = k[2] - k[0], k[3] - k[1]
        L, t = max(w, h), min(w, h)
        if pano_mu(ad, r):
            yakin = min(boy_yazilari, key=lambda o: abs(o - L))
            panolar.append({"tur": ad, "yon": "x" if w > h else "y", "rect": k, "boy_cizim": round(L, 2),
                            "boy": yakin if abs(yakin - L) <= 0.4 else round(L * 4) / 4, "kalinlik": round(t, 2)})
        elif ad == "KOSE" and max(r.width, r.height) <= 1.3 * kal_pt:
            koseler.append({"rect": k, "kare": t > 0.85 * L})       # kare: duvar kalınlığında kutu profil ya da kolon olabilir
        elif ad == "KANAT" and A["kanat_cm"][0] <= L <= A["kanat_cm"][1]:
            kanatlar.append({"rect": k})

    engeller = panolar + koseler
    for p in panolar:
        dis = any(all(_isin_acik(p, p["yon"], isaret, o, engeller) for o in (0.25, 0.5, 0.75)) for isaret in (-1, 1))
        p["duvar"] = "dis" if dis else "ic"
    # okuyucunun bilmediği biçimler sayıyı sessizce bozmasın: teyide düşer
    belirsiz = [p for p in panolar if p["duvar"] == "ic" and _paralel_kacis(p, engeller)]
    if belirsiz:
        uyarilar.append(f"dış / iç belirsiz {len(belirsiz)} pano (iç sayıldı, yüzünün önü dışarıya açılıyor; önde girinti olabilir)")
    zincir = _bilesenler(engeller)
    ana = [engeller[i] for i in zincir[0]]
    ax0, ay0 = min(o["rect"][0] for o in ana), min(o["rect"][1] for o in ana)
    ax1, ay1 = max(o["rect"][2] for o in ana), max(o["rect"][3] for o in ana)
    kopuk = [engeller[i] for g in zincir[1:] for i in g]
    kopuk_pano = sum(1 for o in kopuk if any(o is p for p in panolar))
    if kopuk_pano:
        uyarilar.append(f"duvar zincirine bağlı olmayan {kopuk_pano} pano (bina dışında bir çizim olabilir)")
    disarida = [o for o in kopuk if o["rect"][0] < ax0 - 1 or o["rect"][1] < ay0 - 1 or o["rect"][2] > ax1 + 1 or o["rect"][3] > ay1 + 1]
    if disarida:
        uyarilar.append(f"duvar zincirinin dışında {len(disarida)} öğe dış ölçüyü genişletiyor")
    panolar.sort(key=lambda p: (p["duvar"], p["yon"], p["rect"]))
    return {
        "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
        "olcek_kaynagi": ["ölçü yazısı" if W_y else "standart pano", "ölçü yazısı" if D_y else "standart pano"],
        "dis_olcu_cm": [round(W_pt / sx, 1), round(D_pt / sy, 1)],
        "panolar": panolar, "koseler": koseler, "kanatlar": kanatlar, "kanat_yaylari": yay,
        "uyarilar": uyarilar,
    }


# ── H profil planı ─────────────────────────────────────────────────────────────────────────────────────────────────────────

def _duvar_kutusu(pg, renk) -> fitz.Rect | None:
    xs, ys = [], []
    for r, tur, nok, _d in _cizimler(pg):
        if _ayni_renk(r, renk):
            xs += [p.x for p in nok]
            ys += [p.y for p in nok]
    return fitz.Rect(min(xs), min(ys), max(xs), max(ys)) if xs else None


def _daireler(pg) -> list[tuple[tuple, float, float, float]]:
    rm, gorulen, out = pg.rotation_matrix, set(), []
    for d in pg.get_drawings():
        if not any(it[0] == "c" for it in d["items"]):
            continue
        r = d["rect"] * rm
        if not (4 <= r.width <= 40 and abs(r.width - r.height) < 0.15 * r.width):
            continue
        renk = _renk(d.get("color") or d.get("fill"))
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        anahtar = (renk, round(cx * 2), round(cy * 2))
        if anahtar not in gorulen:
            gorulen.add(anahtar)
            out.append((renk, cx, cy, r.width))
    return out


def h_oku(pg, ayar: dict, dis_olcu_cm: list[float]) -> dict:
    kutu = _duvar_kutusu(pg, tuple(ayar["duvar_rengi"]))
    if kutu is None:
        raise ValueError("H sayfasında duvar çizgisi yok; `duvar_rengi` ayarını denetleyin")
    daireler = _daireler(pg)
    pay = max((c[3] for c in daireler), default=0)
    plan = fitz.Rect(kutu.x0 - pay, kutu.y0 - pay, kutu.x1 + pay, kutu.y1 + pay)
    plandaki = [c for c in daireler if plan.contains(fitz.Point(c[1], c[2]))]
    lejant = [c for c in daireler if not plan.contains(fitz.Point(c[1], c[2]))]

    renk_turu: dict[tuple, str] = {}
    cakisma = []
    for t, r in _satirlar(pg):
        m = H_ETIKET.fullmatch(_norm(t).replace(" ", ""))
        if not m:
            continue
        tur = ("uclu_" if m.group(1) else "") + H_TURU[m.group(2)]
        cy, yuk = (r.y0 + r.y1) / 2, r.height
        sol = [c for c in lejant if abs(c[2] - cy) < yuk and c[1] < r.x0]
        if not sol:
            cakisma.append(f"H lejantı: '{tur}' satırının solunda daire yok")
            continue
        c = min(sol, key=lambda c: r.x0 - c[1])
        if renk_turu.get(c[0], tur) != tur:
            cakisma.append(f"H lejantı: bir renk iki türe bağlanıyor ({renk_turu[c[0]]}, {tur})")
        renk_turu[c[0]] = tur
    eksik = [t for t in H_TURLERI if t not in renk_turu.values()]

    sx, sy = kutu.width / dis_olcu_cm[0], kutu.height / dis_olcu_cm[1]
    uyarilar = list(cakisma)
    if abs(sx - sy) / sx > 0.01:
        uyarilar.append(f"duvar sınırı montajdaki dış ölçüye oturmuyor ({sx:.5f} / {sy:.5f} pt/cm)")
    konumlar, taninmayan = [], Counter()
    for renk, cx, cy, _w in plandaki:
        tur = renk_turu.get(renk)
        if tur is None:
            taninmayan[renk] += 1
            continue
        konumlar.append({"tur": tur, "xy": [round((cx - kutu.x0) / sx, 1), round((kutu.y1 - cy) / sy, 1)]})
    konumlar.sort(key=lambda k: (H_TURLERI.index(k["tur"]), k["xy"]))
    for renk, n in taninmayan.items():
        if renk != tuple(ayar["duvar_rengi"]):
            uyarilar.append(f"lejantta olmayan renkte {n} daire ({renk})")
    sayim = {t: sum(1 for k in konumlar if k["tur"] == t) for t in H_TURLERI}
    return {"turler": sayim, "eksik_turler": eksik, "konumlar": konumlar, "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
            "lejant_dairesi": len(lejant), "uyarilar": uyarilar}


# ── makas ve dere planı ────────────────────────────────────────────────────────────────────────────────────────────────────

def makas_oku(pg, ayar: dict, dis_olcu_cm: list[float]) -> dict:
    kutu = _duvar_kutusu(pg, tuple(ayar["duvar_rengi"]))
    if kutu is None:
        raise ValueError("makas sayfasında duvar çizgisi yok; `duvar_rengi` ayarını denetleyin")
    sx, sy = kutu.width / dis_olcu_cm[0], kutu.height / dis_olcu_cm[1]
    uyarilar = []
    if abs(sx - sy) / sx > 0.01:
        uyarilar.append(f"duvar sınırı montajdaki dış ölçüye oturmuyor ({sx:.5f} / {sy:.5f} pt/cm)")
    etiketler = []
    for t, r in _satirlar(pg):
        m = MK.fullmatch(_norm(t))
        if m:
            etiketler.append((f"MK{int(m.group(1)):02d}", (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    if len(etiketler) < 2:
        return {"makaslar": [], "uyarilar": ["MK etiketi yok ya da tek; okunmadı"]}
    # etiketler hangi eksen boyunca diziliyorsa makaslar ona diktir
    yatay = statistics.pvariance([e[2] for e in etiketler]) > statistics.pvariance([e[1] for e in etiketler])
    s_boy, s_konum = (sx, sy) if yatay else (sy, sx)
    duvar = tuple(ayar["duvar_rengi"])

    paralel = []                                      # (renk, konum pt, baş pt, son pt)
    for renk, tur, nok, _d in _cizimler(pg):
        if tur != "l" or _ayni_renk(renk, duvar):
            continue
        p, q = nok
        if yatay and abs(p.y - q.y) < 0.3:
            paralel.append((renk, (p.y + q.y) / 2, min(p.x, q.x), max(p.x, q.x)))
        elif not yatay and abs(p.x - q.x) < 0.3:
            paralel.append((renk, (p.x + q.x) / 2, min(p.y, q.y), max(p.y, q.y)))
    renk = tuple(ayar["makas"]["renk"]) if ayar["makas"]["renk"] else None
    if renk is None:                                  # her etiket kendisine en yakın uzun paralel çizginin rengine bir oy verir
        uzun = [c for c in paralel if (c[3] - c[2]) / s_boy >= ayar["makas"]["en_kisa_cm"]]

        def uzaklik(c, e):
            k, b = (e[2], e[1]) if yatay else (e[1], e[2])
            return abs(c[1] - k) + max(c[2] - b, 0, b - c[3])
        oy = Counter(min(uzun, key=lambda c: uzaklik(c, e))[0] for e in etiketler) if uzun else Counter()
        if not oy:
            return {"makaslar": [], "uyarilar": ["etiketlerin yanında makas çizgisi yok"]}
        renk = oy.most_common(1)[0][0]

    # aynı doğrultudaki parçaları birleştir (araları 1 pt'den az), kısa olanları at
    hatlar = []
    for anahtar in sorted({round(c[1], 1) for c in paralel if c[0] == renk}):
        parca = sorted((c[2], c[3]) for c in paralel if c[0] == renk and round(c[1], 1) == anahtar)
        a, b = parca[0]
        for a2, b2 in parca[1:]:
            if a2 <= b + 1:
                b = max(b, b2)
            else:
                hatlar.append((anahtar, a, b))
                a, b = a2, b2
        hatlar.append((anahtar, a, b))
    hatlar = [h for h in hatlar if (h[2] - h[1]) / s_boy >= ayar["makas"]["en_kisa_cm"]]

    # çift çizgi bir makastır: konumu 12 cm'den yakın, iki ucu 5 cm içinde aynı
    gruplar: list[list] = []
    for h in sorted(hatlar):
        g = next((g for g in gruplar if abs(h[0] - g[-1][0]) / s_konum < 12 and abs(h[1] - g[0][1]) / s_boy < 5
                  and abs(h[2] - g[0][2]) / s_boy < 5), None)
        (g.append(h) if g else gruplar.append([h]))
    # tek çizgili makasın eşi, daha uzun bir makasla ortak çizilmiş olabilir (PK-07: MK07'nin ön çizgisi MK08'in arka çizgisidir)
    ortak = set()
    for i, g in enumerate(gruplar):
        if len(g) == 1:
            k, a, b = g[0]
            es = [h for h in hatlar if h is not g[0] and abs(h[0] - k) / s_konum < 12 and h[1] <= a + 5 * s_boy and h[2] >= b - 5 * s_boy]
            if es:
                g.append((min(es, key=lambda h: abs(h[0] - k))[0], a, b))
                ortak.add(i)
    makaslar = []
    for i, g in enumerate(gruplar):
        konum = statistics.mean(h[0] for h in g)
        bas, son = min(h[1] for h in g), max(h[2] for h in g)
        if yatay:
            k_cm, b_cm, s_cm = (kutu.y1 - konum) / sy, (bas - kutu.x0) / sx, (son - kutu.x0) / sx
        else:
            k_cm, b_cm, s_cm = (konum - kutu.x0) / sx, (kutu.y1 - son) / sy, (kutu.y1 - bas) / sy
        makaslar.append({"konum_pt": konum, "konum_cm": round(k_cm, 1), "bas_cm": round(b_cm, 1), "son_cm": round(s_cm, 1),
                         "boy_cm": round(s_cm - b_cm, 1), "cizgi": len(g), **({"ortak_cizgi": True} if i in ortak else {})})
    makaslar.sort(key=lambda m: m["konum_cm"])
    if any(m["cizgi"] != 2 for m in makaslar):
        uyarilar.append("çift çizgi olmayan makas var: " + ", ".join(f"{m['konum_cm']} cm ({m['cizgi']} çizgi)"
                                                                          for m in makaslar if m["cizgi"] != 2))

    # etiketler sırayla eşlenir (makasın yanına yazılır); sayı ya da sıra tutmazsa ad yazılmaz
    sirali = sorted(etiketler, key=lambda e: e[2] if yatay else e[1])
    sirali_m = sorted(makaslar, key=lambda m: m["konum_pt"])
    if len(sirali) == len(sirali_m) and all(abs((e[2] if yatay else e[1]) - m["konum_pt"]) < 15 for e, m in zip(sirali, sirali_m)):
        for e, m in zip(sirali, sirali_m):
            m["ad"] = e[0]
    else:
        uyarilar.append(f"{len(etiketler)} MK etiketi, {len(makaslar)} makas; adlar eşlenmedi")

    # aileler: boyu %5 içinde aynı; ana çatı en uzun makasın ailesi; baş = ana ailenin iki ucu (kalkanlı beşik)
    aileler: list[list[dict]] = []
    for m in sorted(makaslar, key=lambda m: -m["boy_cm"]):
        a = next((a for a in aileler if abs(m["boy_cm"] - a[0]["boy_cm"]) / a[0]["boy_cm"] <= 0.05), None)
        (a.append(m) if a else aileler.append([m]))
    for i, a in enumerate(aileler):
        a.sort(key=lambda m: m["konum_cm"])
        for j, m in enumerate(a):
            m["aile"] = "ana" if i == 0 else f"ek_{i}"
            m["rol"] = ("bas" if j in (0, len(a) - 1) else "orta") if i == 0 else "yavru"
    for m in makaslar:
        del m["konum_pt"]
    return {"yon": "x" if yatay else "y", "renk": list(renk), "makaslar": makaslar, "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
            "uyarilar": uyarilar}


# ── katman ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _adlar(ms: list[dict]) -> str:
    adlar = [m.get("ad") for m in ms]
    if not adlar or None in adlar:
        return ""
    adlar.sort(key=lambda a: int(a[2:]))
    if len(adlar) > 2 and all(int(b[2:]) == int(a[2:]) + 1 for a, b in zip(adlar, adlar[1:])):
        return f"{adlar[0]}–{adlar[-1]}"
    return " ve ".join(adlar) if len(adlar) == 2 else ", ".join(adlar)


def katman(M: dict, H: dict | None, K: dict | None) -> tuple[dict, list[dict]]:
    """Okumayı PR #28 biçimine çevirir. Bir bölümde (montaj, h_plani, makas) uyarı varsa o bölümün satırları katmana girmez; her uyarı
    bölümüyle `teyit_bekliyor`'a yazılır ve kıyas aracı o bölümün satırlarını kapıya almaz."""
    teyit = [{"bolum": "montaj", "neden": u} for u in M["uyarilar"]]
    if H is None:
        teyit.append({"bolum": "h_plani", "neden": "H sayfası bulunamadı"})
    else:
        teyit += [{"bolum": "h_plani", "neden": u} for u in H["uyarilar"]]
        if H["eksik_turler"]:
            teyit.append({"bolum": "h_plani", "neden": "lejantta rengi bulunamayan tür: " + ", ".join(H["eksik_turler"])})
    if K is None:
        teyit.append({"bolum": "makas", "neden": "makas sayfası bulunamadı"})
    else:
        teyit += [{"bolum": "makas", "neden": u} for u in K["uyarilar"]]
        if not K["makaslar"] and not K["uyarilar"]:
            teyit.append({"bolum": "makas", "neden": "makas bulunamadı"})
    kapali = {t["bolum"] for t in teyit}
    out = {}
    if "h_plani" not in kapali:
        t = H["turler"]
        out["h_plani"] = {
            "dis": {"adet": t["dubelli_kulakli"] + t["dubelli"],
                    "not": f"H planı: {t['dubelli_kulakli']} dübelli & kulaklı + {t['dubelli']} dübelli"},
            "h_standart": {"adet": t["standart"], "not": "H planı: H standart"},
            "uclu_dis": {"adet": t["uclu_dubelli_kulakli"] + t["uclu_dubelli"],
                         "not": f"H planı: 3'lü {t['uclu_dubelli_kulakli']} dübelli & kulaklı + {t['uclu_dubelli']} dübelli"},
            "uclu_standart": {"adet": t["uclu_standart"], "not": "H planı: 3'lü H standart"},
        }
    if "makas" not in kapali:
        ana = [m for m in K["makaslar"] if m["aile"] == "ana"]
        bas, orta = [m for m in ana if m["rol"] == "bas"], [m for m in ana if m["rol"] == "orta"]
        yavru = [m for m in K["makaslar"] if m["aile"] != "ana"]
        ek = f"; ana çatıdan ayrı {len(yavru)} kısa makas ({_adlar(yavru)}, boy {', '.join(sorted({str(m['boy_cm']) for m in yavru}))} cm)" if yavru else ""
        out["makas_bas"] = {"adet": len(bas), "not": f"makas planı {_adlar(bas)} (ana çatının iki ucu)"}
        out["makas_orta"] = {"adet": len(orta), "not": f"makas planı {_adlar(orta)}; boy {ana[0]['boy_cm']} cm{ek}"}
    return out, teyit


def sha256(yol: Path) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def oku(pdf: Path | str, proje: dict | None = None) -> dict:
    """Paftayı okur; `proje` ayarındaki SHA tutmazsa hata."""
    pdf = Path(pdf)
    proje = proje or {}
    sha = sha256(pdf)
    if proje.get("pafta_sha256") and proje["pafta_sha256"] != sha:
        raise ValueError(f"pafta SHA'sı proje ayarındakiyle aynı değil ({sha[:12]}… ≠ {proje['pafta_sha256'][:12]}…)")
    ayar = _ayar(proje)
    doc = fitz.open(pdf)
    sayfa = sayfalari_bul(doc, ayar)
    if "montaj" not in sayfa:
        raise ValueError("montaj planı sayfası bulunamadı")
    M = montaj_oku(doc[sayfa["montaj"]], ayar)
    H = h_oku(doc[sayfa["h"]], ayar, M["dis_olcu_cm"]) if "h" in sayfa else None
    K = makas_oku(doc[sayfa["makas"]], ayar, M["dis_olcu_cm"]) if "makas" in sayfa else None
    kat, teyit = katman(M, H, K)
    pano = Counter((p["tur"], p["duvar"]) for p in M["panolar"])
    ad = proje.get("kod", "?") + (f" ({proje['ap']})" if proje.get("ap") else "")
    return {
        "kaynak": f"{ad} montaj paftası; tek genel pafta okuyucusu (İE-15 KH-1, sürüm {SURUM}); kodla okundu, elle okuma yok",
        "pafta_sha256": sha,
        "okuyucu": {"surum": SURUM, "sayfa_sayisi": len(doc), "sayfalar": {k: v + 1 for k, v in sorted(sayfa.items())}},
        **kat,
        "teyit_bekliyor": teyit,
        "ayrinti": {
            "montaj": {
                "pano": {"adet": len(M["panolar"]), "std": pano[("STD", "dis")] + pano[("STD", "ic")],
                         "ozel": pano[("OZEL", "dis")] + pano[("OZEL", "ic")],
                         "dis": pano[("STD", "dis")] + pano[("OZEL", "dis")], "ic": pano[("STD", "ic")] + pano[("OZEL", "ic")]},
                "kose": len(M["koseler"]), "kose_kare": sum(k["kare"] for k in M["koseler"]), "kanat": len(M["kanatlar"]), "kanat_yayi": M["kanat_yaylari"],
                "olcek_pt_cm": M["olcek_pt_cm"], "olcek_kaynagi": M["olcek_kaynagi"], "dis_olcu_cm": M["dis_olcu_cm"],
                "panolar": [{k: p[k] for k in ("tur", "duvar", "boy", "rect")} for p in M["panolar"]],
            },
            "h_plani": None if H is None else {k: H[k] for k in ("turler", "konumlar", "olcek_pt_cm", "lejant_dairesi")},
            "makas": None if K is None else {k: K[k] for k in ("yon", "renk", "makaslar", "olcek_pt_cm") if k in K},
        },
    }


def ozet(o: dict) -> str:
    m = o["ayrinti"]["montaj"]
    satir = [f"sayfalar {o['okuyucu']['sayfalar']}",
             f"pano {m['pano']['adet']} (std {m['pano']['std']}, özel {m['pano']['ozel']}; dış {m['pano']['dis']}, iç {m['pano']['ic']}), "
             f"köşe {m['kose']} (kare {m['kose_kare']}), kanat {m['kanat']}; ölçek {m['olcek_kaynagi']}, dış ölçü {m['dis_olcu_cm']}"]
    if o["ayrinti"]["h_plani"]:
        satir.append("H " + ", ".join(f"{k} {v}" for k, v in o["ayrinti"]["h_plani"]["turler"].items()))
    if o["ayrinti"]["makas"]:
        satir.append("makas " + ", ".join(f"{x.get('ad', '?')} {x['rol']} {x['boy_cm']}" for x in o["ayrinti"]["makas"]["makaslar"]))
    for k in ("h_plani", "makas_bas", "makas_orta"):
        if k in o:
            satir.append(f"{k}: " + json.dumps(o[k], ensure_ascii=False))
    satir += [f"TEYİT ({t['bolum']}): {t['neden']}" for t in o["teyit_bekliyor"]]
    return "\n".join(satir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--proje", type=Path, help="projeler/<KOD>.json (SHA ve ayar)")
    ap.add_argument("--cikti", type=Path, help="pafta_katmani.json biçiminde çıktı")
    a = ap.parse_args(argv)
    proje = json.loads(a.proje.read_text(encoding="utf-8")) if a.proje else {}
    o = oku(a.pdf, proje)
    if a.cikti:
        a.cikti.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(ozet(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
