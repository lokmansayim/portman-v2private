"""Tek genel pafta okuyucusu (İE-15 · KH-1, KH-2 ve KH-3; hakem aracı, D-24).

Prefabrik montaj paftasının PDF'ini yazıdan ve vektörden okur; LLM yok, ağ yok, elle okuma yok. Her paftada üç sayfa okunur (KH-1):
montaj planı (pano, köşe, kolon, kapı kanadı), H profil planı (H türleri lejanttaki renkten) ve makas–dere planı (makaslar).
Çatı ve tavan bölümleri (KH-2) proje ayarındaki `ek_bolumler` ile açılır: tavan omega (`omega`), aşık (`asik`), çatı kaplaması
(`kaplama`), baş makas betopanı (`betopan`) ve makas–dere sayfasındaki dere ve iniş (`dere`). Elektrik yerleşim planı (KH-3) da öyle
açılır (`elektrik`): tijli duy, glop, anahtar (tekli, çift), priz (tekli, çift), uydu prizi, zil ve sigorta kutusu; işaretlerin rengi ve
ölçüsü sayfanın lejantından okunur, lejant renginde hiçbir işarete uymayan öğe bölümü teyide düşürür (ayrıntı `elektrik_oku`'da). Her
evin hakem PR'ı kendi bölümlerini açar.
Çıktı PR #28'in `pafta_katmani.json` biçimindedir (anahtar → {adet, not}; `motor/prefabrik_liste.py --pafta` değişmeden okur);
yerleşim kapısının istediği ayrıntı (H türleri ayrı, konumlar, makas boyları, parça boyları ve metre) `ayrinti` altında durur.

Sayfa başlığından bulunur, sayfa numarasından değil. Şablonun renkleri ve başlıkları aşağıdaki `VARSAYILAN`'dadır; projeye özgü
ayar (SHA, sayfa, renk, açılan bölümler) `projeler/<KOD>.json`'da görünür durur, koda gömülmez. Kodla okunamayan ya da uyarı veren
bölüm `teyit_bekliyor`'a nedeniyle yazılır; o bölümün satırları katmana ve kapıya girmez. Montaj teyitteyse ölçeğini ve duvar
çerçevesini montajdan alan bölümler (H, makas, omega, dere, elektrik) de teyide düşer. Çıktıya antetten yazı girmez; yalnız sayılar, konumlar ve MKnn etiketleri.

Çerçeve: cm; x binanın sol dış yüzünden, y ön dış yüzünden (önden bakışta paftanın altı). Döndürülmüş sayfalar `rotation_matrix`
ile görünen sayfaya çevrilir. Ölçek montaj sayfasında 125,5'lik standart panodan bulunur; dış ölçü yazısı bununla %3 içinde
tutuyorsa yazıdaki ölçü kullanılır. H, makas ve omega sayfalarında duvar çizgilerinin sınırı montajdaki dış ölçüye oturtulur.

Eflatun boy yazılı parçalar (omega, aşık): iki ok başı arasındaki çizgi ve yanındaki sayı bir parçadır; boy sayıdan alınır, çizimdeki
boy sayıyla %3 içinde tutmalıdır. Ok başı olmayan ölçü parça sayılmaz: `EN_KISA_PARCA_CM`'den kısası boşluk ölçüsüdür (bilgi), uzunu
parça mı boşluk mu bilinmediği için bölümü teyide düşürür; sayfada hiç ölçülü parça yoksa bölüm teyittedir. Lejantlı sayfalarda
(kaplama, betopan) lejanttaki dörtgenin rengi ve ölçüsüyle aynı dörtgenler sayılır ve lejanttaki "N adet" yazısıyla kıyaslanır.

Bina çerçevesi (KH-2): omega parçası duvar çerçevesinin içinde, dere hattı çerçevenin `dere.cerceve_payi_cm` yakınında (saçakta)
durur; dışındaki öğe sayılmaz (`atilan.cerceve_disinda`) ve bölümü teyide düşürür. İnişi olmayan dere hattı teyittir. Aşık sayfasında
duvar çizgisi yoktur; tek sıralı çatı yüzü (bina dışında bir ölçü olabilir) aşığı teyide düşürür.

Koşma:
    python3 -I testler/kimlik/hakem/pafta_oku.py <pafta.pdf> --proje testler/kimlik/hakem/projeler/PK01.json [--cikti <json>]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import pymupdf as fitz

SURUM = "3"
EN_KISA_PARCA_CM = 10.0                     # ok başı olmayan ölçünün parça sayılabileceği en kısa boy (CIO, 24 Ekim)
VARSAYILAN = {
    "basliklar": {                          # sayfa başlığı (boşluklar teke indirilir, büyük harf); ilk eşleşen sayfa
        "montaj": r"MONTAJ( VE ELEKTRİK)? PLANI",
        "h": r"H (PROFİL )?(MONTAJ|YERLEŞİM) PLANI",
        "makas": r"MAKAS VE DERE YERLEŞİM PLANI",
        "omega": r"TAVAN OMEGA YERLEŞİM PLANI",
        "asik": r"AŞIK YERLEŞİM PLANI",
        "kaplama": r"ÇATI KAPLAMASI YERLEŞİM PLANI",
        "betopan": r"BAŞ ?MAKAS BETOPAN YERLEŞİMİ",
        "elektrik": r"ELEKTRİK YERLEŞİM PLANI",
    },
    "ek_bolumler": [],                      # KH-2'nin bölümleri (omega, asik, kaplama, betopan, dere) ve KH-3'ün elektrik bölümü; proje ayarıyla açılır
    "cati": "besik",                        # baş makas kuralı (ana ailenin iki ucu) yalnız kalkanlı beşikte geçerli
    "montaj": {
        "renkler": {"STD": [0.0, 0.0, 0.0], "OZEL": [0.0, 0.0, 1.0], "KOSE": [1.0, 0.0, 0.0], "KANAT": [0.047, 0.275, 0.592]},
        "std_pano_cm": 125.5,
        "kanat_cm": [60.0, 100.0],
    },
    "duvar_rengi": [0.388, 0.392, 0.4],     # H ve makas sayfalarında gri duvar çizgileri
    "makas": {"renk": None, "en_kisa_cm": 50.0},   # renk None: MK etiketlerinin yanındaki çizgilerden oylanır
    "sayfalar": {},                         # zorunlu sayfa numarası (1'den), başlık bulunamazsa
    "olcu": {"renk": [1.0, 0.0, 1.0], "oran_payi": 0.03},   # eflatun boy yazıları ve okları; çizim / yazı oranı bu payın içinde
    "omega": {"anahtar": "tavan_omegasi", "duvar_payi_cm": 1.0,    # katman anahtarı (asma tavanda `duvar_omegasi_asma`)
              "cerceve_payi_cm": 10.0},  # parça duvar çerçevesinin bu payla içinde; dışındaki sayılmaz, bölüm teyitte
    "asik": {"yuz_sira_araligi_cm": 100.0},  # bu aralıktan yakın ve boyca örtüşen sıralar aynı çatı yüzüdür
    "dere": {"renk": [0.663, 0.325, 0.627], "inis_rengi": [0.0, 0.0, 0.0], "birlesme_cm": 20.0, "uc_payi_cm": 10.0,
             "cerceve_payi_cm": 60.0},  # dere saçakta: duvar çerçevesinden bu paydan uzak hat sayılmaz, bölüm teyitte
    "elektrik": {                           # KH-3; işaretlerin rengi ve ölçüsü lejanttan okunur
        "lejant_basligi": r"LEJANT",
        "lejant": {"anahtar": r"ANAHTAR", "priz": r"PR[İI]Z", "glop": r"GLOP", "duy": r"T[İI]JL[İI]", "sigorta": r"S[İI]GORTA",
                   "zil": r"Z[İI]L"},  # etiketin ilk sözcüğü; başlığın altında `lejant_boyu_pt`, iki yanında `lejant_payi_pt` içinde
        "lejant_ek_sozcuk": r"DUY|KUTUSU",  # iki satırlı etiketin ikinci sözcüğü; lejantta başka sözcük bölümü teyide düşürür
        "lejant_payi_pt": 50.0, "lejant_boyu_pt": 250.0,
        "isaret_genisligi_pt": 70.0,        # lejant işareti etiketin solunda bu genişlikte
        "satir_payi_pt": 18.0,              # işaretin ortası etiketin satırından bu kadar uzaksa o etiketin değil
        "duvar_rengi": None,                # None: genel `duvar_rengi` (PK-01'in elektrik sayfasında duvar daha açık; proje ayarında)
        "sigorta_rengi": [0.0, 0.0, 0.0],
        "uydu": r"UYDU", "buat": r"BUAT",
        "uydu_uzakligi_pt": 25.0,           # "UYDU" yazısı ile uydu prizinin tabanı arası en çok
        "lejant_alt_boslugu_pt": 40.0,      # lejant alanının hemen altındaki bu bant boş olmalı (lejant alandan uzunsa teyit)
        "yakin_renk_payi": 0.25,            # işaret rengine bu kadar yakın (kanal başına) başka tondaki öğe de denetlenir
        "aci_payi_derece": 10.0,            # açılar lejanttakiyle bu payla aynı: anahtarın tırnakları (yarıçapla, çiftte birbiriyle) ve
                                            # ucu, glopun çaprazları, U'nun kolları ve sapı, çift prizin iki U'sunun yönü
        "oran_payi": 0.03,                  # duvar sınırının oranı montajdaki dış ölçünün oranıyla bu payla aynı
        "cerceve_payi_cm": 30.0,            # işaret duvar çerçevesinin bu payla içinde; dışında lejant renginde öğe bölümü teyide düşürür
    },
}
EK_BOLUMLER = ("omega", "asik", "kaplama", "betopan", "dere")          # KH-2
KH3_BOLUMLERI = ("elektrik",)                                           # KH-3
ACILABILEN = EK_BOLUMLER + KH3_BOLUMLERI
EK_SAYFA = {"omega": "omega", "asik": "asik", "kaplama": "kaplama", "betopan": "betopan", "dere": "makas", "elektrik": "elektrik"}
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
    """Başlıktan sayfa (0'dan). Aynı başlık iki sayfada varsa hata; bulunamazsa `sayfalar` ayarı, o da yoksa yok. KH-1'in üç sayfası
    her zaman, ek bölümlerin sayfası yalnız bölüm açıksa aranır."""
    aranan = {"montaj", "h", "makas"} | {EK_SAYFA[b] for b in ayar["ek_bolumler"]}
    bulunan: dict[str, list[int]] = {k: [] for k in ayar["basliklar"] if k in aranan}
    for i, pg in enumerate(doc):
        metinler = {_norm(t) for t, _ in _satirlar(pg)}
        for k in bulunan:
            if any(re.fullmatch(ayar["basliklar"][k], m) for m in metinler):
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
    # dış ölçü yazıyla doğrulanmazsa ya da standart pano bu ölçekle 125,5 tutmazsa dış ölçüyü bina dışından bir öğe genişletmiş olabilir
    # (köşeye bitişik, dışarı taşan çizim; KH-1 › Bilinen sınırlama, KH-2'de hakem değişikliği)
    yazisiz = [e for e, v in (("x", W_y), ("y", D_y)) if not v]
    if yazisiz:
        uyarilar.append(f"dış ölçü yazısı bulunamadı ({', '.join(yazisiz)} ekseni); ölçek yalnız standart panodan")
    std_boy = [statistics.median(max(r.width, r.height) for r in std) / s for s in (sx, sy)]
    if any(abs(b / A["std_pano_cm"] - 1) > 0.01 for b in std_boy):
        uyarilar.append(f"standart pano bu ölçekle {std_boy[0]:.1f} / {std_boy[1]:.1f} cm ({A['std_pano_cm']} değil); dış ölçüyü bir öğe genişletmiş olabilir")

    def cm(r):
        return [round((r.x0 - X0) / sx, 2), round((Y1 - r.y1) / sy, 2), round((r.x1 - X0) / sx, 2), round((Y1 - r.y0) / sy, 2)]

    boy_yazilari = [v for v in olculer if 30 < v < 260] + [A["std_pano_cm"]]
    panolar, koseler, kanatlar, atilan = [], [], [], []
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
        else:
            atilan.append((ad, r, k))
    # sayılan renklerde biçimi tutmayan dörtgen: bina içindeyse sayılan bir öğe olabilir (teyit), dışındaysa lejant ya da tablo (bilgi)
    bina = fitz.Rect(X0, Y0, X1, Y1)
    icerde = [(ad, k) for ad, r, k in atilan if bina.intersects(r)]
    if icerde:
        uyarilar.append(f"bina içinde sayılmayan {len(icerde)} renkli dörtgen: "
                        + ", ".join(f"{ad} {k[2] - k[0]:.1f} × {k[3] - k[1]:.1f} cm" for ad, k in icerde[:5]))

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
        "atilan": {"bina_icinde": len(icerde), "bina_disinda": len(atilan) - len(icerde)},
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


def _egriler(pg) -> list[tuple[tuple, fitz.Rect]]:
    """Eğri içeren çizimler: (renk, görünen sayfadaki kutu)."""
    rm = pg.rotation_matrix
    return [(_renk(d.get("color") or d.get("fill")), d["rect"] * rm) for d in pg.get_drawings() if any(it[0] == "c" for it in d["items"])]


def _daire_mi(r: fitz.Rect) -> bool:
    return 4 <= r.width <= 40 and abs(r.width - r.height) < 0.15 * r.width


def _daireler(pg) -> list[tuple[tuple, float, float, float]]:
    rm, gorulen, out = pg.rotation_matrix, set(), []
    for d in pg.get_drawings():
        if not any(it[0] == "c" for it in d["items"]):
            continue
        r = d["rect"] * rm
        if not _daire_mi(r):
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
    # daire sayılmayan eğri: lejant renginde ve planın içindeyse sayılmamış bir H olabilir (teyit); duvar renginde kapı yayıdır (bilgi)
    disi = [(renk, r) for renk, r in _egriler(pg) if not _daire_mi(r) and plan.contains(fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))]
    lejant_renkli = [r for renk, r in disi if renk in renk_turu]
    if lejant_renkli:
        uyarilar.append(f"lejant renginde, daire sayılmayan {len(lejant_renkli)} eğri (boyu ya da biçimi H dairesine uymuyor)")
    duvar_renkli = taninmayan.get(tuple(ayar["duvar_rengi"]), 0) + sum(1 for renk, _ in disi if renk == tuple(ayar["duvar_rengi"]))
    sayim = {t: sum(1 for k in konumlar if k["tur"] == t) for t in H_TURLERI}
    return {"turler": sayim, "eksik_turler": eksik, "konumlar": konumlar, "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
            "lejant_dairesi": len(lejant), "atilan": {"duvar_renginde_egri": duvar_renkli}, "uyarilar": uyarilar}


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
    kisa = sum(1 for h in hatlar if (h[2] - h[1]) / s_boy < ayar["makas"]["en_kisa_cm"])     # tarama, ok, kesik çizgi (bilgi)
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
            "atilan": {"kisa_cizgi": kisa}, "uyarilar": uyarilar}


# ── eflatun boy yazılı parçalar (tavan omega, aşık; KH-2) ────────────────────────────────────────────────────────────────────

YAZI_UZAKLIGI_PT = 25.0                     # boy yazısı parçasının çizgisine bundan uzaksa o parçaya bağlanmaz


def _yazi_rengi(c: int) -> tuple:
    return (round(((c >> 16) & 255) / 255, 3), round(((c >> 8) & 255) / 255, 3), round((c & 255) / 255, 3))


def _sayi_yazilari(pg, renk: tuple | None = None) -> list[dict]:
    """Sayı olan yazılar (renk verilirse yalnız o renkte), görünen sayfada ortası ve kutusuyla."""
    rm, out = pg.rotation_matrix, []
    for b in pg.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for sp in ln["spans"]:
                s = sp["text"].strip()
                if SAYI.fullmatch(s) and (renk is None or _ayni_renk(_yazi_rengi(sp["color"]), renk)):
                    r = fitz.Rect(sp["bbox"]) * rm
                    out.append({"deger": float(s.replace(",", ".")), "x": (r.x0 + r.x1) / 2, "y": (r.y0 + r.y1) / 2, "rect": r})
    return out


def olculu_parcalar(pg, ayar: dict) -> dict:
    """Ölçü renginde iki ok başı arasındaki çizgi ve yanındaki sayı bir parçadır; boy sayıdan alınır. Ok başı ölçü renginde dolgulu
    çizimdir; aynı doğrultudaki ok başları sırayla ikişer eşlenir. Sayı kendisine en yakın parçaya bir kez bağlanır. Ok başı olmayan
    sayı parça değildir: `EN_KISA_PARCA_CM`'den kısası boşluk ölçüsü (bilgi), uzunu teyit."""
    O = ayar["olcu"]
    renk, rm = tuple(O["renk"]), pg.rotation_matrix
    oklar = [d["rect"] * rm for d in pg.get_drawings()
             if d.get("fill") is not None and _ayni_renk(_renk(d.get("color") or d.get("fill")), renk)]
    gruplar: dict[tuple, list] = {}
    for r in oklar:
        eksen = "y" if r.height > r.width else "x"
        c = (r.x0 + r.x1) / 2 if eksen == "y" else (r.y0 + r.y1) / 2
        anahtar = next((k for k in gruplar if k[0] == eksen and abs(k[1] - c) < 0.5), (eksen, c))
        gruplar.setdefault(anahtar, []).append(r)
    parcalar, tek = [], 0
    for (eksen, c), rs in sorted(gruplar.items()):
        rs.sort(key=lambda r: r.y0 if eksen == "y" else r.x0)
        tek += len(rs) % 2
        for a, b in zip(rs[0::2], rs[1::2]):
            parcalar.append({"eksen": eksen, "c": c, "u0": a.y0 if eksen == "y" else a.x0, "u1": b.y1 if eksen == "y" else b.x1})
    yazilar = _sayi_yazilari(pg, renk)

    def uzaklik(p, y):
        k, b = (y["x"], y["y"]) if p["eksen"] == "y" else (y["y"], y["x"])
        return abs(k - p["c"]) + max(p["u0"] - b, 0, b - p["u1"])
    bag: dict[int, int] = {}
    for d, i, j in sorted((uzaklik(p, y), i, j) for i, p in enumerate(parcalar) for j, y in enumerate(yazilar)):
        if d <= YAZI_UZAKLIGI_PT and i not in bag and j not in bag.values():
            bag[i] = j
    uyarilar = []
    if tek:
        uyarilar.append(f"eşi olmayan ok başı {tek} doğrultuda")
    yazisiz = [p for i, p in enumerate(parcalar) if i not in bag]
    if yazisiz:
        uyarilar.append(f"boy yazısı bulunamayan {len(yazisiz)} parça")
    okunan = []
    for i, j in bag.items():
        okunan.append(parcalar[i] | {"boy": yazilar[j]["deger"]})
    olcek = statistics.median((p["u1"] - p["u0"]) / p["boy"] for p in okunan) if okunan else None
    sapan = [p for p in okunan if abs((p["u1"] - p["u0"]) / p["boy"] / olcek - 1) > O["oran_payi"]]
    if sapan:
        uyarilar.append(f"çizimdeki boyu yazısından %{O['oran_payi'] * 100:g}'ten çok farklı {len(sapan)} parça: "
                        + ", ".join(f"{p['boy']:g}" for p in sapan[:5]))
    if not okunan:
        uyarilar.append("ölçülü parça yok (ölçü renginde iki ok başı ve boy yazısı); sayfayı ve `olcu.renk` ayarını denetleyin")
    oksuz = sorted(y["deger"] for j, y in enumerate(yazilar) if j not in bag.values())
    uzun = [v for v in oksuz if v >= EN_KISA_PARCA_CM]
    if uzun:
        uyarilar.append(f"ok başı olmayan {len(uzun)} ölçü ({', '.join(f'{v:g}' for v in uzun[:6])}{' …' if len(uzun) > 6 else ''} cm): "
                        f"parça mı boşluk mu belli değil (en kısa parça {EN_KISA_PARCA_CM:g} cm)")
    return {"parcalar": okunan, "olcek_pt_cm": olcek, "bosluk": [v for v in oksuz if v < EN_KISA_PARCA_CM], "oksuz_uzun": uzun,
            "uyarilar": uyarilar}


def _boylar(boylar: list[float]) -> dict[str, int]:
    return {f"{b:g}": n for b, n in sorted(Counter(boylar).items(), key=lambda kv: -kv[0])}


def _duvara_gore(yon: str, k: float, b: float, s: float, panolar: list[dict], pay: float) -> tuple[str, str | None]:
    """Hattın montajdaki duvarlara göre yeri: duvarın ekseninde, yüzünde, duvarın içinde ya da arada. Hattın beş noktasında bakılır,
    en az üçü aynı yeri gösteriyorsa o yer; değilse "ara"."""
    oy: Counter = Counter()
    for oran in (0.1, 0.3, 0.5, 0.7, 0.9):
        t, yer = b + (s - b) * oran, ("ara", None)
        for p in panolar:
            if p["yon"] != yon:
                continue
            x0, y0, x1, y1 = p["rect"]
            c0, c1, a0, a1 = (x0, x1, y0, y1) if yon == "y" else (y0, y1, x0, x1)
            if not a0 <= t <= a1:
                continue
            if abs(k - (c0 + c1) / 2) <= pay:
                yer = ("duvar_ekseni", p["duvar"])
            elif min(abs(k - c0), abs(k - c1)) <= pay:
                yer = ("duvar_yuzu", p["duvar"])
            elif c0 < k < c1:
                yer = ("duvar_ici", p["duvar"])
            else:
                continue
            break
        oy[yer] += 1
    yer, n = oy.most_common(1)[0]
    return yer if n >= 3 else ("ara", None)


def omega_oku(pg, ayar: dict, M: dict) -> dict:
    """Tavan omega planı: eflatun boy yazılı parçalar; her hattın montajın duvarlarına göre yeri (bilgi, karar B'nin kanıtı)."""
    P = olculu_parcalar(pg, ayar)
    uyarilar = list(P["uyarilar"])
    kutu = _duvar_kutusu(pg, tuple(ayar["duvar_rengi"]))
    if kutu is None:
        raise ValueError("omega sayfasında duvar çizgisi yok; `duvar_rengi` ayarını denetleyin")
    dis = M["dis_olcu_cm"]
    sx, sy = kutu.width / dis[0], kutu.height / dis[1]
    if abs(sx - sy) / sx > 0.01:
        uyarilar.append(f"duvar sınırı montajdaki dış ölçüye oturmuyor ({sx:.5f} / {sy:.5f} pt/cm)")
    if P["olcek_pt_cm"] and abs(P["olcek_pt_cm"] / ((sx + sy) / 2) - 1) > ayar["olcu"]["oran_payi"]:
        uyarilar.append(f"boy yazılarının ölçeği ({P['olcek_pt_cm']:.5f}) duvar çerçevesininkiyle tutmuyor ({sx:.5f} pt/cm)")
    parcalar, disarida, pay = [], [], ayar["omega"]["cerceve_payi_cm"]
    for p in P["parcalar"]:
        if p["eksen"] == "y":                         # görünen sayfada dikey: binanın y'si boyunca, konumu x
            yon, k, b, s = "y", (p["c"] - kutu.x0) / sx, (kutu.y1 - p["u1"]) / sy, (kutu.y1 - p["u0"]) / sy
        else:
            yon, k, b, s = "x", (kutu.y1 - p["c"]) / sy, (p["u0"] - kutu.x0) / sx, (p["u1"] - kutu.x0) / sx
        kg, bg = (dis[0], dis[1]) if yon == "y" else (dis[1], dis[0])
        if not (-pay <= k <= kg + pay and -pay <= b and s <= bg + pay):
            disarida.append(p["boy"])
            continue
        yer, duvar = _duvara_gore(yon, k, b, s, M["panolar"], ayar["omega"]["duvar_payi_cm"])
        parcalar.append({"yon": yon, "konum_cm": round(k, 1), "bas_cm": round(b, 1), "son_cm": round(s, 1), "boy_cm": p["boy"],
                         "yer": yer, **({"duvar": duvar} if duvar else {})})
    if disarida:
        uyarilar.append(f"duvar çerçevesinin dışında {len(disarida)} ölçülü parça ({', '.join(f'{v:g}' for v in disarida[:6])} cm): "
                        "sayılmadı (lejant örneği ya da başka bir çizim olabilir)")
    parcalar.sort(key=lambda p: (p["yon"], p["konum_cm"], p["bas_cm"]))
    yerler = Counter(p["yer"] for p in parcalar)
    return {"parca": len(parcalar), "toplam_m": round(sum(p["boy_cm"] for p in parcalar) / 100, 4),
            "boylar": _boylar([p["boy_cm"] for p in parcalar]),
            "konum": {y: yerler.get(y, 0) for y in ("duvar_ekseni", "duvar_yuzu", "duvar_ici", "ara")},
            "parcalar": parcalar, "bosluk_olculeri": P["bosluk"], "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
            "atilan": {"cerceve_disinda": len(disarida)}, "uyarilar": uyarilar}


def asik_oku(pg, ayar: dict) -> dict:
    """Aşık planı: eflatun boy yazılı parçalar. Aynı doğrultudaki parçalar bir sıradır; yakın ve boyca örtüşen sıralar bir çatı yüzüdür.
    Sıra konumları yüzün sayfadaki ilk sırasından ölçülür (mahya ya da saçak tarafı paftanın çatı şeklinden okunur, burada değil).
    Aşık sayfasında duvar çizgisi olmadığı için bina çerçevesi yoktur; tek sıralı yüz (bina dışında bir ölçü olabilir) teyittir."""
    P = olculu_parcalar(pg, ayar)
    uyarilar, s = list(P["uyarilar"]), P["olcek_pt_cm"]
    siralar: list[dict] = []
    for p in sorted(P["parcalar"], key=lambda p: (p["eksen"], p["c"], p["u0"])):
        r = next((r for r in siralar if r["eksen"] == p["eksen"] and abs(r["c"] - p["c"]) < 0.5), None)
        if r is None:
            r = {"eksen": p["eksen"], "c": p["c"], "u0": p["u0"], "u1": p["u1"], "boylar": []}
            siralar.append(r)
        r["u0"], r["u1"] = min(r["u0"], p["u0"]), max(r["u1"], p["u1"])
        r["boylar"].append(p["boy"])
    kok = list(range(len(siralar)))

    def bul(i):
        while kok[i] != i:
            kok[i] = kok[kok[i]]
            i = kok[i]
        return i
    for i, a in enumerate(siralar):
        for j in range(i + 1, len(siralar)):
            b = siralar[j]
            ortak = min(a["u1"], b["u1"]) - max(a["u0"], b["u0"])
            if a["eksen"] == b["eksen"] and abs(a["c"] - b["c"]) / s <= ayar["asik"]["yuz_sira_araligi_cm"] \
                    and ortak >= 0.5 * min(a["u1"] - a["u0"], b["u1"] - b["u0"]):
                kok[bul(i)] = bul(j)
    yuzler: dict[int, list] = {}
    for i, r in enumerate(siralar):
        yuzler.setdefault(bul(i), []).append(r)
    yuz = []
    for rs in sorted(yuzler.values(), key=lambda rs: (rs[0]["eksen"], min(r["c"] for r in rs), min(r["u0"] for r in rs))):
        rs.sort(key=lambda r: r["c"])
        yuz.append({"sira": len(rs), "sira_konumlari_cm": [round((r["c"] - rs[0]["c"]) / s, 1) for r in rs],
                    "sira_boylari_cm": [round(sum(r["boylar"]), 2) for r in rs], "parca": sum(len(r["boylar"]) for r in rs)})
    tek = [y for y in yuz if y["sira"] == 1]
    if tek:
        uyarilar.append(f"tek sıralı {len(tek)} çatı yüzü ({', '.join(str(y['parca']) + ' parça' for y in tek)}): bina dışında bir ölçü "
                        "ya da tek sıralı küçük bir çatı olabilir")
    boylar = [p["boy"] for p in P["parcalar"]]
    return {"parca": len(boylar), "toplam_m": round(sum(boylar) / 100, 4), "boylar": _boylar(boylar), "yuzler": yuz,
            "bosluk_olculeri": P["bosluk"], "teyitli_olculer": P["oksuz_uzun"], "olcek_pt_cm": round(s, 5) if s else None,
            "uyarilar": uyarilar}


# ── lejantlı sayfalar (çatı kaplaması, baş makas betopanı; KH-2) ─────────────────────────────────────────────────────────────

ADET = re.compile(r"(?:ADET ?:? ?(\d+)(?: ?ADET)?|(\d+) ?ADET)")


def lejantli_oku(pg, ayar: dict) -> dict:
    """Lejanttaki dörtgenin rengi ve ölçüsüyle (dönmüş de olabilir) aynı dörtgenler sayılır; lejanttaki "N adet" yazısıyla kıyaslanır.
    Lejant dörtgeni, adet yazısıyla aynı satırda ya da hemen üstünde duran, aynı türden en az bir eşi olan dörtgendir. Ölçü, lejant
    dörtgeninin yanındaki iki sayıdan dörtgenin oranına uyanıdır."""
    dortgen = []
    for renk, tur, nok, d in _cizimler(pg):
        if tur == "qu" and d.get("fill") is None:
            r, eksende = _dik_dortgen(nok)
            if eksende and min(r.width, r.height) > 1:
                dortgen.append((renk, r))
    turler: list[dict] = []
    for renk, r in dortgen:
        a, b = sorted((r.width, r.height))
        t = next((t for t in turler if t["renk"] == renk and abs(t["a"] - a) <= 0.02 * t["a"] and abs(t["b"] - b) <= 0.02 * t["b"]), None)
        if t is None:
            t = {"renk": renk, "a": a, "b": b, "uyeler": []}
            turler.append(t)
        t["uyeler"].append(r)
    adetler = [(int(m.group(1) or m.group(2)), r) for metin, r in _satirlar(pg) if (m := ADET.fullmatch(_norm(metin)))]
    uyarilar, okunan, kullanilan = [], [], set()
    if not adetler:
        uyarilar.append("lejantta adet yazısı yok; hangi dörtgenin sayılacağı belli değil")
    sayilar = _sayi_yazilari(pg)
    for n, yr in adetler:
        tx, ty, aday = (yr.x0 + yr.x1) / 2, (yr.y0 + yr.y1) / 2, []
        for ti, t in enumerate(turler):
            if len(t["uyeler"]) < 2:
                continue
            for ui, r in enumerate(t["uyeler"]):
                if r.y0 <= ty <= r.y1:                                # aynı satırda
                    aday.append((max(r.x0 - yr.x1, yr.x0 - r.x1, 0), ti, ui))
                elif yr.x0 < r.x1 and r.x0 < yr.x1 and 0 <= yr.y0 - r.y1 <= r.height:     # hemen altında
                    aday.append((yr.y0 - r.y1, ti, ui))
        aday = [a for a in sorted(aday) if (a[1], a[2]) not in kullanilan]
        if not aday:
            uyarilar.append(f"'{n} adet' yazısının lejant dörtgeni bulunamadı")
            continue
        _, ti, ui = aday[0]
        kullanilan.add((ti, ui))
        t, lr = turler[ti], turler[ti]["uyeler"][ui]

        def uz(y):
            return max(lr.x0 - y["x"], y["x"] - lr.x1, 0) + max(lr.y0 - y["y"], y["y"] - lr.y1, 0)
        yakin = sorted(sayilar, key=uz)[:2]
        olcu = None
        if len(yakin) == 2 and yakin[0]["deger"] and yakin[1]["deger"]:
            for w, h in ((yakin[0]["deger"], yakin[1]["deger"]), (yakin[1]["deger"], yakin[0]["deger"])):
                if abs((w / h) / (lr.width / lr.height) - 1) <= 0.03:
                    olcu = [w, h]
                    break
        cizim = len(t["uyeler"]) - 1
        if cizim != n:
            uyarilar.append(f"çizimde {cizim}, lejantta {n} adet ({olcu[0]:g} × {olcu[1]:g})" if olcu else f"çizimde {cizim}, lejantta {n} adet")
        okunan.append({"olcu_cm": olcu, "cizimde": cizim, "lejantta": n, "renk": list(t["renk"]),
                       "ornekler": [r for r in t["uyeler"] if r is not lr]})
    # lejant renginde, lejanttaki ölçüden başka ölçüde dörtgen: kesilmiş ya da başka bir ürün olabilir
    lejant_turu = {id(turler[ti]) for ti, _ in kullanilan}
    lejant_rengi = {turler[ti]["renk"] for ti, _ in kullanilan}
    baska = sum(len(t["uyeler"]) for t in turler if t["renk"] in lejant_rengi and id(t) not in lejant_turu)
    if baska:
        uyarilar.append(f"lejant renginde, ölçüsü lejanttakinden farklı {baska} dörtgen")
    ornek = [r for o in okunan for r in o.pop("ornekler")]
    return {"adet": sum(o["cizimde"] for o in okunan), "turler": okunan, "gruplar": _temas_gruplari(ornek), "uyarilar": uyarilar}


def _temas_gruplari(rs: list[fitz.Rect], pay: float = 1.0) -> list[int]:
    """Birbirine değen (pay pt) dörtgenlerin grupları, büyükten küçüğe."""
    kok = list(range(len(rs)))

    def bul(i):
        while kok[i] != i:
            kok[i] = kok[kok[i]]
            i = kok[i]
        return i
    for i, a in enumerate(rs):
        for j in range(i + 1, len(rs)):
            b = rs[j]
            if a.x0 - pay <= b.x1 and b.x0 - pay <= a.x1 and a.y0 - pay <= b.y1 and b.y0 - pay <= a.y1:
                kok[bul(i)] = bul(j)
    return sorted(Counter(bul(i) for i in range(len(rs))).values(), reverse=True)


# ── dere ve iniş (makas ve dere planı; KH-2) ─────────────────────────────────────────────────────────────────────────────────

def dere_oku(pg, ayar: dict, dis_olcu_cm: list[float]) -> dict:
    """Dere: dere renginde (kesikli) çizgiler doğrultu doğrultu birleştirilir, aradaki boşluk `birlesme_cm`'den kısaysa aynı hattır.
    İniş: iniş renginde daire (çift daire tek sayılır); hattın ucunda (`uc_payi_cm`) ya da arasında. Ölçek duvar çizgilerinin sınırının
    montajdaki dış ölçüye oturmasından. Duvar çerçevesinden `cerceve_payi_cm`'den uzak hat sayılmaz; inişi olmayan hat teyittir."""
    D = ayar["dere"]
    kutu = _duvar_kutusu(pg, tuple(ayar["duvar_rengi"]))
    if kutu is None:
        raise ValueError("makas ve dere sayfasında duvar çizgisi yok; `duvar_rengi` ayarını denetleyin")
    sx, sy = kutu.width / dis_olcu_cm[0], kutu.height / dis_olcu_cm[1]
    uyarilar = []
    if abs(sx - sy) / sx > 0.01:
        uyarilar.append(f"duvar sınırı montajdaki dış ölçüye oturmuyor ({sx:.5f} / {sy:.5f} pt/cm)")
    parca: dict[tuple, list] = {}
    egik = 0
    for renk, tur, nok, _d in _cizimler(pg):
        if tur != "l" or not _ayni_renk(renk, tuple(D["renk"])):
            continue
        p, q = nok
        if abs(p.x - q.x) < 0.3:
            e, c, a, b = "y", (p.x + q.x) / 2, min(p.y, q.y), max(p.y, q.y)
        elif abs(p.y - q.y) < 0.3:
            e, c, a, b = "x", (p.y + q.y) / 2, min(p.x, q.x), max(p.x, q.x)
        else:
            egik += 1
            continue
        anahtar = next((k for k in parca if k[0] == e and abs(k[1] - c) < 0.5), (e, c))
        parca.setdefault(anahtar, []).append((a, b))
    if egik:
        uyarilar.append(f"dere renginde eğik {egik} çizgi okunmadı")
    hatlar, disarida, pay = [], [], D["cerceve_payi_cm"]
    for (e, c), ps in sorted(parca.items()):
        s_boy = sy if e == "y" else sx
        ps.sort()
        a, b = ps[0]
        for a2, b2 in ps[1:] + [(math.inf, math.inf)]:
            if a2 - b <= D["birlesme_cm"] * s_boy:
                b = max(b, b2)
                continue
            if e == "y":
                h = {"yon": "y", "konum_cm": round((c - kutu.x0) / sx, 1), "bas_cm": round((kutu.y1 - b) / sy, 1),
                     "son_cm": round((kutu.y1 - a) / sy, 1)}
            else:
                h = {"yon": "x", "konum_cm": round((kutu.y1 - c) / sy, 1), "bas_cm": round((a - kutu.x0) / sx, 1),
                     "son_cm": round((b - kutu.x0) / sx, 1)}
            h["boy_cm"] = round(h["son_cm"] - h["bas_cm"], 1)
            kg, bg = (dis_olcu_cm[0], dis_olcu_cm[1]) if e == "y" else (dis_olcu_cm[1], dis_olcu_cm[0])
            (hatlar if -pay <= h["konum_cm"] <= kg + pay and -pay <= h["bas_cm"] and h["son_cm"] <= bg + pay else disarida).append(h)
            a, b = a2, b2
    if disarida:
        uyarilar.append(f"duvar çerçevesinden {pay:g} cm'den uzakta {len(disarida)} dere hattı "
                        f"({', '.join(format(h['boy_cm'], 'g') for h in disarida)} cm): sayılmadı")
    if not hatlar:
        uyarilar.append("dere çizgisi yok")
    inisler = []
    for renk, cx, cy, _w in _daireler(pg):
        if not _ayni_renk(renk, tuple(D["inis_rengi"])):
            continue
        x, y = (cx - kutu.x0) / sx, (kutu.y1 - cy) / sy
        if any(abs(x - i["xy"][0]) < 2 and abs(y - i["xy"][1]) < 2 for i in inisler):    # çift daire
            continue
        inisler.append({"xy": [round(x, 1), round(y, 1)]})
    for i in inisler:
        en, yer = math.inf, None
        for h in hatlar:
            d, uc = _hatta_uzaklik(h, *i["xy"], D["uc_payi_cm"])
            if d < en:
                en, yer = d, "uc" if uc else "ara"
        i["yer"] = yer if en <= D["birlesme_cm"] else None
    bagsiz = [i for i in inisler if i["yer"] is None]
    if bagsiz:
        uyarilar.append(f"dere hattına bağlı olmayan {len(bagsiz)} iniş")
    if hatlar and not inisler:
        uyarilar.append("iniş yok")
    inissiz = [h for h in hatlar if not any(_hatta_uzaklik(h, *i["xy"], D["uc_payi_cm"])[0] <= D["birlesme_cm"] for i in inisler)]
    if inisler and inissiz:
        uyarilar.append(f"inişi olmayan {len(inissiz)} dere hattı ({', '.join(format(h['boy_cm'], 'g') for h in inissiz)} cm)")
    inisler.sort(key=lambda i: i["xy"])
    return {"hat": len(hatlar), "toplam_m": round(sum(h["boy_cm"] for h in hatlar) / 100, 4), "hatlar": hatlar,
            "inis": len(inisler), "inisler": inisler, "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
            "atilan": {"cerceve_disinda": len(disarida)}, "uyarilar": uyarilar}


def _hatta_uzaklik(h: dict, x: float, y: float, uc_payi: float) -> tuple[float, bool]:
    """İnişin (x, y; cm) hatta uzaklığı (dik uzaklık + hattın ucundan taşma) ve hattın ucunda olup olmadığı."""
    k, t = (x, y) if h["yon"] == "y" else (y, x)
    return abs(k - h["konum_cm"]) + max(h["bas_cm"] - t, 0, t - h["son_cm"]), min(abs(t - h["bas_cm"]), abs(t - h["son_cm"])) <= uc_payi


# ── elektrik yerleşim planı (KH-3) ───────────────────────────────────────────────────────────────────────────────────────

ELEKTRIK = ("tavan_armaturu", "glop", "anahtar_tekli", "anahtar_cift", "priz_tekli", "priz_cift", "uydu_prizi", "zil", "sigorta_kutusu")
UC_PAYI_PT = 0.3                            # iki çizgi ucu bu kadar yakınsa değer; priz parçasının boyu lejanttakiyle bu payla aynı
DAIRE_PAYI_PT = 0.4                         # dairenin çapı lejanttakiyle bu payla aynı
ISARET_SIRASI = ("tavan_armaturu", "glop", "anahtar_tekli", "anahtar_cift", "priz_tekli", "priz_cift", "uydu_prizi", "sigorta_kutusu", "buat")


def _sozcukler(pg) -> list[tuple[str, fitz.Rect]]:
    """Sayfanın sözcükleri, görünen sayfa koordinatında (iki satırlı lejant etiketinin ilk sözcüğü aranır)."""
    rm = pg.rotation_matrix
    return [(_norm(w[4]), fitz.Rect(w[:4]) * rm) for w in pg.get_text("words")]


def _yapi(it: tuple) -> tuple:
    """Bir PDF yolu öğesinin türü ve ölçüsü (döndürmeyle değişmez): çizgi ve eğride iki ucunun arası, dörtgende kenarları."""
    if it[0] in ("l", "c"):
        return (it[0], round(_uzak(it[1], it[-1]), 3))
    q = it[1].quad if isinstance(it[1], fitz.Rect) else it[1]
    return (it[0], *sorted((round(_uzak(q.ul, q.ur), 3), round(_uzak(q.ur, q.lr), 3))))


def _ogeler(pg) -> list[dict]:
    """Çizimler görünen sayfada: renk (dolgulu çizimde dolgunun rengi), dolgu, öğe türleri, kutu, merkez, çizgi parçaları, eğrilerin dört
    noktası (`_cemberde`), yolun öğelerinin türü ve ölçüsü (`_yapi`) ve bütün noktalar (aynı yerde iki kez çizilmiş öğeyi tanımak için)."""
    rm, out = pg.rotation_matrix, []
    for d in pg.get_drawings():
        dolgu = d.get("fill") is not None
        r = d["rect"] * rm
        noktalar = []
        for it in d["items"]:
            for v in it[1:]:
                if isinstance(v, fitz.Point):
                    noktalar.append(v * rm)
                elif isinstance(v, (fitz.Rect, fitz.Quad)):
                    q = v.quad if isinstance(v, fitz.Rect) else v
                    noktalar += [q.ul * rm, q.ur * rm, q.lr * rm, q.ll * rm]
        out.append({"renk": _renk(d["fill"] if dolgu else d.get("color")), "dolgu": dolgu, "tur": {it[0] for it in d["items"]}, "r": r,
                    "m": fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2),
                    "cizgiler": [(it[1] * rm, it[2] * rm) for it in d["items"] if it[0] == "l"], "noktalar": noktalar,
                    "egriler": [tuple(v * rm for v in it[1:5]) for it in d["items"] if it[0] == "c"],
                    "yapi": sorted(_yapi(it) for it in d["items"])})
    return out


def _tekille(ogeler: list[dict], pay: float = 0.05) -> tuple[list[dict], list[dict]]:
    """Aynı yerde ikinci kez çizilmiş öğe (renk, dolgu, öğe türleri aynı; noktaları `pay` pt içinde aynı) bir sayılır. Döner: (tekiller,
    atılan kopyalar). Göz iki kopyayı tek işaret görür; okuyucu da öyle sayar (iki kez çizilmiş tekli anahtar çift sayılmaz). PK-01 ve
    PK-07'de kopyalar birebir aynı koordinatta (pay 0,3 pt'de sigortanın iç desenindeki ayrı kısa çizgiler de birleşiyordu)."""
    def anahtar(p):
        return (round(p.x, 1), round(p.y, 1))

    def ayni(a, b):
        if (a["renk"], a["dolgu"], a["tur"], len(a["noktalar"])) != (b["renk"], b["dolgu"], b["tur"], len(b["noktalar"])):
            return False
        return all(_uzak(p, q) <= pay for p, q in zip(sorted(a["noktalar"], key=anahtar), sorted(b["noktalar"], key=anahtar)))
    kova: dict[tuple, list[dict]] = {}
    tek, kopya = [], []
    for o in ogeler:
        k = (round(o["m"].x), round(o["m"].y))
        if any(ayni(o, b) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for b in kova.get((k[0] + dx, k[1] + dy), ())):
            kopya.append(o)
        else:
            tek.append(o)
            kova.setdefault(k, []).append(o)
    return tek, kopya


def _kutu(ogeler: list[dict]) -> fitz.Rect:
    return fitz.Rect(min(o["r"].x0 for o in ogeler), min(o["r"].y0 for o in ogeler), max(o["r"].x1 for o in ogeler), max(o["r"].y1 for o in ogeler))


def _icinde(r: fitz.Rect, k: fitz.Rect, pay: float = 0.0) -> bool:
    """r, k'nin (pay pt genişletilmiş) içinde mi; sıfır alanlı kutularda da (çizgi) doğru sonuç verir."""
    return k.x0 - pay <= r.x0 and r.x1 <= k.x1 + pay and k.y0 - pay <= r.y0 and r.y1 <= k.y1 + pay


def _degiyor(r: fitz.Rect, k: fitz.Rect) -> bool:
    """r ile k'nin ortak noktası var mı; sıfır alanlı kutularda da (çizgi)."""
    return not (r.x1 < k.x0 or k.x1 < r.x0 or r.y1 < k.y0 or k.y1 < r.y0)


def _imza(o: dict) -> tuple:
    return (o["renk"], o["dolgu"], tuple(sorted(o["tur"])))


def _bilesim(ogeler: list[dict], kutu: fitz.Rect, renkler: set, pay: float) -> tuple[Counter, list[dict]]:
    """Kutunun (pay pt genişletilmiş) içindeki, verilen renklerdeki öğeler ve imzalarının (renk, dolgu, öğe türleri) sayımı. Plandaki bir
    işaretin bileşimi lejanttakiyle aynı olmalı: işaretin içine düşen fazla ya da eksik öğe sessizce yutulmaz."""
    ic = [o for o in ogeler if o["renk"] in renkler and _icinde(o["r"], kutu, pay)]
    return Counter(_imza(o) for o in ic), ic


def _boyut(o: dict) -> tuple[float, ...]:
    """Öğenin ölçüsü: tek çizgide boyu; öbürlerinde kutusunun kısa ve uzun kenarı (90° dönük işarette de aynı)."""
    if o["tur"] == {"l"} and len(o["cizgiler"]) == 1:
        return (_uzak(*o["cizgiler"][0]),)
    return tuple(sorted((o["r"].width, o["r"].height)))


def _ayni_yapi(a: dict, b: dict, pay: float) -> bool:
    """İki PDF yolunun öğeleri bire bir aynı: türleri (çizgi, eğri, dörtgen) ve sayıları aynı, her birinin ölçüsü `pay` pt içinde."""
    return len(a["yapi"]) == len(b["yapi"]) and all(x[0] == y[0] and len(x) == len(y) and all(abs(p - q) <= pay for p, q in zip(x[1:], y[1:]))
                                                    for x, y in zip(a["yapi"], b["yapi"]))


def _ayni_icerik(ic: list[dict], lejant: list[dict], pay: float) -> bool:
    """Plandaki işaretin kutusundaki öğeler lejant işaretindekilerle bire bir eşleşir: imzası (renk, dolgu, tür) aynı; dolgusuz öğenin
    ölçüsü `pay` pt içinde ve yolunun öğeleri de (`_ayni_yapi`) aynı (ör. glopun çaprazı kısa bir çentik olamaz; bir PDF yoluna kutunun
    içinde çizgi, daire ya da dörtgen eklenemez). Dolgunun parçalarına ölçü bakılmaz: tarama deseni sayfanın başlangıcına göre kesilir,
    her işarette parçaları başka boydadır (PK-07'nin duyları); dolgunun kendi kutusu ayrıca denetlenir."""
    if len(ic) != len(lejant):
        return False
    kalan = list(ic)
    for a in sorted(lejant, key=_boyut, reverse=True):
        es = next((b for b in kalan if _imza(b) == _imza(a) and (a["dolgu"] or (len(_boyut(b)) == len(_boyut(a))
                   and _ayni_yapi(a, b, pay) and all(abs(x - y) <= pay for x, y in zip(_boyut(a), _boyut(b)))))), None)
        if es is None:
            return False
        kalan.remove(es)
    return True


def _kesisiyor(a: fitz.Rect, b: fitz.Rect, pay: float) -> bool:
    """İki kutu iki yönde de `pay` pt'den çok örtüşüyor mu (yalnız değmek değil)."""
    return min(a.x1, b.x1) - max(a.x0, b.x0) > pay and min(a.y1, b.y1) - max(a.y0, b.y0) > pay


def _aci(s: tuple) -> float:
    """Çizgi parçasının yönü, derece (0–180; yönsüz)."""
    return math.degrees(math.atan2(s[2].y - s[1].y, s[2].x - s[1].x)) % 180


def _aci_farki(a: float, b: float) -> float:
    d = abs(a - b) % 180
    return min(d, 180 - d)


def _sapma(s: tuple, m: fitz.Point) -> float:
    """Tırnağın çizgisi ile daireye değdiği yerden geçen yarıçap arasındaki açı (0–90)."""
    p = s[1] if _uzak(s[1], m) < _uzak(s[2], m) else s[2]
    return _aci_farki(_aci(s), math.degrees(math.atan2(p.y - m.y, p.x - m.x)) % 180)


def _tirnak_cifti(t: list, m: fitz.Point) -> tuple[float, float]:
    """İki tırnağın dizilişi: daireye değen uçlarının merkezden açı farkı (0–180) ve çizgilerinin açı farkı (0–90). Her tırnağın
    yarıçapla açısı (`_sapma`) da lejanttakiyle aynıysa ikisi birlikte çifti aynalanmasına kadar belirler; tekli anahtarın tırnağı
    aynalanarak ya da yana kaydırılarak ikinci kez çizilirse biri tutmaz."""
    ic = [s[1] if _uzak(s[1], m) < _uzak(s[2], m) else s[2] for s in t]
    i0, i1 = (math.degrees(math.atan2(p.y - m.y, p.x - m.x)) for p in ic)
    return abs((i1 - i0 + 180) % 360 - 180), _aci_farki(_aci(t[0]), _aci(t[1]))


def _capraz_acilari(cs: list) -> list[float]:
    """Glop çaprazlarının ikişer ikişer açı farkları (küçükten büyüğe). Tek çaprazı iki kez çizilmiş glopta koşut iki çizgi olur,
    lejanttakine uymaz."""
    return sorted(round(_aci_farki(_aci(a), _aci(b)), 2) for i, a in enumerate(cs) for b in cs[i + 1:])


def _kumeler(ogeler: list[dict], pay: float = 0.6) -> list[list[dict]]:
    """Kutuları birbirine değen (pay pt) öğelerin kümeleri."""
    sira = sorted(range(len(ogeler)), key=lambda i: ogeler[i]["r"].x0)
    kok = list(range(len(ogeler)))

    def bul(i):
        while kok[i] != i:
            kok[i] = kok[kok[i]]
            i = kok[i]
        return i
    for n, i in enumerate(sira):
        a = ogeler[i]["r"]
        for j in sira[n + 1:]:
            b = ogeler[j]["r"]
            if b.x0 > a.x1 + pay:
                break
            if b.y0 <= a.y1 + pay and a.y0 <= b.y1 + pay:
                kok[bul(i)] = bul(j)
    gruplar: dict[int, list[dict]] = {}
    for i, o in enumerate(ogeler):
        gruplar.setdefault(bul(i), []).append(o)
    return list(gruplar.values())


def _uzak(a: fitz.Point, b: fitz.Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _parcalar(ogeler: list[dict], renk: tuple) -> list[tuple]:
    """Bir renkteki çizgi parçaları: (öğe, uç, uç, boy)."""
    return [(o, p, q, _uzak(p, q)) for o in ogeler if not o["dolgu"] and o["renk"] == renk for p, q in o["cizgiler"]]


def _u_isaretleri(parcalar: list[tuple], olcu: dict | None = None) -> list[dict]:
    """Priz işareti (U): taban, tabanın iki ucunda aynı yana giden birer kol ve tabanın ortasından kolların öbür yanına giden sap. `olcu`
    (kol, sap, taban; pt) verilirse parçanın boyu bu ölçüyle `UC_PAYI_PT` içinde aynı olmalı. Bir parça tek bir U'ya girer. Her U'nun
    açıları (`aci`: iki kolun arası, kolların ve sapın tabanla açısı; 0–90) ve yönü (`yon`: tabana dik, sap yanına birim vektör) de
    döner; açıların lejanttakiyle aynılığı çağıranda denetlenir."""
    def uyar(s, ad):
        return olcu is None or abs(s[3] - olcu[ad]) <= UC_PAYI_PT

    def degen(s, uc):                      # s'nin uca değen ucu ve öbür ucu
        if _uzak(s[1], uc) <= UC_PAYI_PT:
            return s[2]
        if _uzak(s[2], uc) <= UC_PAYI_PT:
            return s[1]
        return None
    out, kullanilan = [], set()
    for t in parcalar:
        if id(t) in kullanilan or not uyar(t, "taban"):
            continue
        kollar = []
        for uc in (t[1], t[2]):
            k = [(s, degen(s, uc)) for s in parcalar if s is not t and id(s) not in kullanilan and uyar(s, "kol") and degen(s, uc) is not None]
            kollar.append(k[0] if len(k) == 1 else None)
        if None in kollar or kollar[0][0] is kollar[1][0]:
            continue
        o = fitz.Point((t[1].x + t[2].x) / 2, (t[1].y + t[2].y) / 2)
        yon, yon2 = kollar[0][1] - t[1], kollar[1][1] - t[2]
        if yon.x * yon2.x + yon.y * yon2.y <= 0:
            continue                       # kollar aynı yana gitmiyor (Z biçimi): U değil; parçaları sahipsiz kalır
        saplar = [(s, degen(s, o)) for s in parcalar if s is not t and id(s) not in kullanilan and uyar(s, "sap") and degen(s, o) is not None]
        saplar = [(s, uc) for s, uc in saplar if (uc.x - o.x) * yon.x + (uc.y - o.y) * yon.y < 0]
        if len(saplar) != 1:
            continue
        sap, uc = saplar[0]
        parca = [t, kollar[0][0], kollar[1][0], sap]
        kullanilan |= {id(s) for s in parca}
        n = fitz.Point(-(t[2].y - t[1].y), t[2].x - t[1].x) / t[3]                   # tabana dik birim vektör, sap yanına
        n = n if (uc.x - o.x) * n.x + (uc.y - o.y) * n.y > 0 else -n
        aci = {"kol_kol": round(_aci_farki(_aci(kollar[0][0]), _aci(kollar[1][0])), 2),
               "kol_taban": [round(_aci_farki(_aci(k[0]), _aci(t)), 2) for k in kollar], "sap_taban": round(_aci_farki(_aci(sap), _aci(t)), 2)}
        out.append({"o": o, "uc": uc, "yon": n, "aci": aci, "parcalar": parca, "olcu": {"kol": round((kollar[0][0][3] + kollar[1][0][3]) / 2, 2),
                                                                   "sap": round(sap[3], 2), "taban": round(t[3], 2)},
                    "r": fitz.Rect(min(p.x for s in parca for p in s[1:3]), min(p.y for s in parca for p in s[1:3]),
                                   max(p.x for s in parca for p in s[1:3]), max(p.y for s in parca for p in s[1:3]))})
    return out


def _lejant(E: dict, sozcukler: list, ogeler: list[dict], duvar: tuple) -> tuple[dict[str, dict], fitz.Rect, list[str]]:
    """Lejant etiketleri (`lejant` desenleri; başlığın altında) ve işaretleri. Etiketlerin solundaki (`isaret_genisligi_pt`) çizimler
    birbirine değenler bir küme olacak biçimde toplanır; her küme, sağında duran ve satırı en yakın olan etiketin işaretidir. Üçüncü
    değer uyarılardır: lejantta tanınmayan sözcük (bilinmeyen bir tür olabilir), hiçbir etikete bağlanmayan işaret, lejant alanının hemen
    altında öğe (lejant alandan uzun olabilir) ve alanın dışında lejant etiketine benzeyen sözcük."""
    baslik = [r for t, r in sozcukler if re.fullmatch(E["lejant_basligi"], t)]
    if len(baslik) != 1:
        raise ValueError(f"elektrik sayfasında lejant başlığı {len(baslik)} kez var" if baslik else "elektrik sayfasında lejant başlığı yok")
    B = baslik[0]
    alan = fitz.Rect(B.x0 - E["lejant_payi_pt"], B.y1, B.x1 + E["lejant_payi_pt"], B.y1 + E["lejant_boyu_pt"])
    etiket = {}
    for tur, desen in E["lejant"].items():
        aday = [r for t, r in sozcukler if re.fullmatch(desen, t) and _icinde(r, alan)]
        if len(aday) > 1:
            raise ValueError(f"lejantta '{tur}' etiketi {len(aday)} kez var")
        if aday:
            etiket[tur] = aday[0]
    if not etiket:
        raise ValueError("lejantta tanınan etiket yok")
    uyarilar = []
    tanimsiz = [t for t, r in sozcukler if _icinde(r, alan) and r is not B and not any(r is e for e in etiket.values())
                and not re.fullmatch(E["lejant_ek_sozcuk"], t)]
    if tanimsiz:                                    # sözcükler yazılmaz (antet ya da kişi adı çıktıya girmesin)
        uyarilar.append(f"lejantta tanınmayan {len(tanimsiz)} sözcük (etiketi bilinmeyen bir tür olabilir)")
    alt = fitz.Rect(alan.x0, alan.y1, alan.x1, alan.y1 + E["lejant_alt_boslugu_pt"])
    altta = sum(1 for _, r in sozcukler if _degiyor(r, alt)) + sum(1 for o in ogeler if not _ayni_renk(o["renk"], duvar) and _degiyor(o["r"], alt))
    if altta:
        uyarilar.append(f"lejant alanının (başlığın {E['lejant_boyu_pt']:g} pt altına kadar) hemen altında {altta} öğe: lejant alandan uzun olabilir")
    benzer = sum(1 for t, r in sozcukler if not _icinde(r, alan) and any(re.fullmatch(d, t) for d in E["lejant"].values()))
    if benzer:
        uyarilar.append(f"lejant alanının dışında lejant etiketine benzeyen {benzer} sözcük")
    isaret_alani = fitz.Rect(min(r.x0 for r in etiket.values()) - E["isaret_genisligi_pt"], B.y1, max(r.x0 for r in etiket.values()), alan.y1)
    isaret: dict[str, list[dict]] = {t: [] for t in etiket}
    lejant_ogeleri = [o for o in ogeler if not _ayni_renk(o["renk"], duvar) and _icinde(o["r"], isaret_alani)]
    bagsiz = 0
    for k in _kumeler(lejant_ogeleri):
        kr = _kutu(k)
        sagdaki = [t for t, r in etiket.items() if kr.x1 <= r.x0 + 0.5]
        t = min(sagdaki, key=lambda t: abs((etiket[t].y0 + etiket[t].y1) / 2 - (kr.y0 + kr.y1) / 2)) if sagdaki else None
        if t and abs((etiket[t].y0 + etiket[t].y1) / 2 - (kr.y0 + kr.y1) / 2) <= E["satir_payi_pt"]:
            isaret[t] += k
        else:
            bagsiz += 1
    if bagsiz:
        uyarilar.append(f"lejantta hiçbir etikete bağlanmayan {bagsiz} işaret")
    lk = fitz.Rect(B)
    for r in [*etiket.values(), *(o["r"] for o in lejant_ogeleri)]:
        lk = fitz.Rect(min(lk.x0, r.x0), min(lk.y0, r.y0), max(lk.x1, r.x1), max(lk.y1, r.y1))
    return {t: {"etiket": etiket[t], "ogeler": isaret[t]} for t in etiket}, lk, uyarilar


def _bezier(e: tuple, t: float) -> fitz.Point:
    """Kübik eğrinin (dört noktası `e`) t'deki noktası."""
    u = 1 - t
    k = (u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3)
    return fitz.Point(sum(a * p.x for a, p in zip(k, e)), sum(a * p.y for a, p in zip(k, e)))


def _cemberde(o: dict) -> bool:
    """Yolun her eğrisi çemberin üstünde: eğrinin dokuz noktası (iki ucu, aradaki yedi nokta) kutunun ortasından kutunun yarı eni kadar
    uzakta (`DAIRE_PAYI_PT`'nin yarısı içinde). Eğrilerle çizilmiş elmas, yıldız ya da bir çeyreği içe bükük yol daire sayılmaz; yalnız
    uçlarına ve kutusuna bakılsa daire sanılırdı. PK-01 ve PK-07'nin glop ve anahtar daireleri en çok 0,0025 pt uzakta."""
    yc = (o["r"].width + o["r"].height) / 4
    return all(abs(_uzak(_bezier(e, i / 8), o["m"]) - yc) <= DAIRE_PAYI_PT / 2 for e in o["egriler"] for i in range(9))


def _lejant_dairesi(g: list[dict]) -> dict | None:
    d = [o for o in g if o["tur"] == {"c"} and _daire_mi(o["r"]) and _cemberde(o)]
    return {"renk": d[0]["renk"], "cap": d[0]["r"].width, "m": d[0]["m"], "r": d[0]["r"]} \
        if d and len({(o["renk"], round(o["r"].width, 1)) for o in d}) == 1 else None


def _daireler_renkte(ogeler: list[dict], renk: tuple, cap: float) -> tuple[list[dict], int]:
    """Bir renkte, lejanttaki çapta daireler; aynı merkezde iki kez çizilmiş daire bir sayılır (öğeleri birlikte döner). Döner: (daireler,
    bu renkte ve çapta olup eğrileri çemberin üstünde olmayan yolların sayısı; `_cemberde`)."""
    out, bicimsiz = [], 0
    for o in ogeler:
        if o["tur"] == {"c"} and o["renk"] == renk and abs(o["r"].width - cap) <= DAIRE_PAYI_PT and abs(o["r"].height - cap) <= DAIRE_PAYI_PT:
            if not _cemberde(o):
                bicimsiz += 1                                   # sahipsiz kalır
                continue
            es = next((d for d in out if _uzak(d["m"], o["m"]) <= 0.5), None)
            if es:
                es["ogeler"].append(o)
            else:
                out.append({"m": o["m"], "r": o["r"], "ogeler": [o]})
    return out, bicimsiz


def _capraz(s: tuple) -> bool:
    return abs(s[1].x - s[2].x) > 0.2 * s[3] and abs(s[1].y - s[2].y) > 0.2 * s[3]


def _renk_farki(a: tuple, b: tuple) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def elektrik_oku(pg, ayar: dict, dis_olcu_cm: list[float]) -> dict:
    """Elektrik yerleşim planı (KH-3). İşaretlerin rengi, ölçüsü ve bileşimi (işaretin kutusundaki öğelerin rengi, dolgusu, türü;
    dolgusuz öğede ölçüsü ve PDF yolunun öğeleri) lejanttan okunur, koda gömülmez. Aynı yerde (0,05 pt içinde) ikinci kez çizilmiş öğe
    bir sayılır (`ayrinti.elektrik.atilan.ayni_yerde_iki_kez`):
    - tijli duy: lejanttaki dolgunun renginde, birbirine değen dolgular; kutusu lejanttakinin ölçüsünde (±1 pt), içi lejanttakiyle aynı;
    - glop: lejanttaki daire (renk, çap; eğrileri çemberin üstünde), içinde lejanttaki kadar çapraz (aralarındaki açılar
      `aci_payi_derece` içinde) ve lejanttaki işaretle aynı bileşim; çaprazsız, içinde yalnız dairesi olan ve "BUAT" yazan daire buat
      (bilgi);
    - anahtar: lejanttaki daire (eğrileri çemberin üstünde, içi lejanttakiyle aynı) ve ona değen, lejanttaki boyda eğik tırnaklar; her
      tırnağın dıştaki ucunda lejanttaki boyda ve tırnakla lejanttaki açıda tek kısa çizgi; her tırnağın yarıçapla açısı lejanttakiyle
      aynı; bir tırnak tekli, iki tırnak çift (dizilişi lejanttaki çiftinki: değdikleri yerlerin merkezden ve çizgilerinin açı farkı;
      aynalanmış çift de olur). Açılar `aci_payi_derece` içinde;
    - priz: lejanttaki U (kol, sap ve taban boyu; kollar aynı yana; kolların arası, kolların ve sapın tabanla açısı `aci_payi_derece`
      içinde); birinin sapının ucu öbürünün tabanının ortasına değen, tabanı aynı yöne (`aci_payi_derece` içinde) bakan iki U çift
      prizdir; "UYDU" yazısına en yakın (`uydu_uzakligi_pt` içinde) tek U uydu prizidir, tekli prizden düşülür;
    - sigorta kutusu: `sigorta_rengi`nde, birbirine değen çizgilerin kutusu lejanttaki çerçevenin ölçüsünde (±%10), içi lejanttakiyle aynı;
    - zil: lejantta yoksa 0.
    Sessiz sayı yok; şunların her biri bölümü teyide düşürür:
    - lejant renginde hiçbir işarete girmeyen öğe; sigortanın iç desenindeki ya da lejant rengine yakın (`yakin_renk_payi`) tonda, işaret
      boyunda hiçbir işarete girmeyen öğe; duvar çerçevesinin dışında bu renklerde öğe; bir parçası (çizgisi) işarete giren ama başka
      parçası hiçbir işarete girmeyen çizim (PDF yolu);
    - içi lejanttakine uymayan duy, glop, BUAT, anahtar dairesi ya da sigorta ölçüsünde kutu; ölçüsü tutmayan duy dolgusu; glop ya da
      anahtar dairesinin renginde ve çapında, eğrileri çemberin üstünde olmayan yol (eğrilerle çizilmiş elmas, yıldız);
    - tırnak sayısı bir ya da iki olmayan anahtar, iki anahtar dairesine birden değen tırnak, daireye değen ama tırnak boyunda olmayan eğik
      çizgi, yarıçapla açısı lejanttakinden farklı tırnak, iki tırnağının dizilişi lejanttakine uymayan anahtar (tırnak kaydırılarak ya
      da aynalanarak ikinci kez çizilmiş), tırnağın ucunda birden çok, lejanttakinden başka boyda ya da açıda ya da hiç çizgi; çaprazı
      lejanttakinden başka sayıda ya da başka açıda glop (tek çapraz iki kez çizilmiş), çaprazsız ve BUAT yazısız daire, içinde BUAT yazan
      glop; lejantta çaprazsız glop, tırnaksız anahtar ya da iki tırnaklı anahtar yokken planda iki tırnaklı anahtar;
    - açıları lejanttakine uymayan U (kolu açık, paralelkenar, sapı eğik); iki çift prize giren U; sapı öbürünün tabanına değmeyen ama
      sap boyundan yakın iki U (çift priz olabilir); sapı öbürünün tabanına değen ama başka yöne bakan iki U; kutusu bir başkasıyla kesişen ve çift olmayan iki U ya da kutusu aynı türden bir başkasıyla
      kesişen iki duy, glop/BUAT, anahtar ya da sigorta (aynı işaret kaydırılarak iki kez çizilmiş olabilir; kaymış duy kopyası
      öbürüyle tek kümeye girer ve ölçüsü tutmaz, kaymış sigorta kopyası da tek büyük kutu olur ve iç deseni sahipsiz kalır); kutusunun
      ortası başka türden bir işaretin kutusunda olan işaret (ör. BUAT dairesinin içine çizilmiş U);
    - lejantta: etiketi ya da işareti bulunamayan tür, tanınmayan sözcük, hiçbir etikete bağlanmayan işaret, zil (okunmuyor), alanın
      hemen altında öğe, alanın dışında lejant etiketine benzeyen sözcük;
    - planda hiç işareti bulunamayan lejant türü; yanında priz olmayan, en yakın prizi çift olan ya da başka bir UYDU yazısıyla aynı prize
      bağlanan UYDU yazısı.
    Konumlar duvar çizgilerinin sınırının montajdaki dış ölçüye oturmasından (cm; `oran_payi` içinde); oda ataması burada değil."""
    E = ayar["elektrik"]
    duvar = tuple(E["duvar_rengi"] or ayar["duvar_rengi"])
    kutu = _duvar_kutusu(pg, duvar)
    if kutu is None:
        raise ValueError("elektrik sayfasında duvar çizgisi yok; `elektrik.duvar_rengi` ayarını denetleyin")
    soz = _sozcukler(pg)
    ogeler, kopyalar = _tekille(_ogeler(pg))
    lejant, lk, uyarilar = _lejant(E, soz, ogeler, duvar)
    sx, sy = kutu.width / dis_olcu_cm[0], kutu.height / dis_olcu_cm[1]
    if abs(sx - sy) / sx > E["oran_payi"]:
        uyarilar.append(f"duvar sınırı montajdaki dış ölçüye oturmuyor ({sx:.5f} / {sy:.5f} pt/cm)")
    pay = E["cerceve_payi_cm"] * sx
    cerceve = fitz.Rect(kutu.x0 - pay, kutu.y0 - pay, kutu.x1 + pay, kutu.y1 + pay)
    plan = [o for o in ogeler if not lk.contains(o["m"]) and cerceve.contains(o["m"])]
    disari = [o for o in ogeler if not lk.contains(o["m"]) and not cerceve.contains(o["m"])]

    # lejant: her türün rengi, ölçüsü ve bileşimi (G: tür → (imza sayımı, renkler); plandaki işaretin kutusu aynısını taşımalı)
    L: dict[str, dict] = {}
    G: dict[str, tuple[list, set]] = {}

    def bilesim(g, r, pay_):
        renkler = {o["renk"] for o in g}
        return _bilesim(g, r, renkler, pay_)[1], renkler

    def degen_tirnaklar(parca, d, cap):
        return [s for s in parca if _capraz(s) and min(abs(_uzak(s[1], d) - cap / 2), abs(_uzak(s[2], d) - cap / 2)) <= 0.6]

    def uctaki(parca, s, d):                            # tırnağın dıştaki ucuna değen öbür çizgiler
        dis = s[1] if _uzak(s[1], d) > _uzak(s[2], d) else s[2]
        return [s2 for s2 in parca if s2 is not s and min(_uzak(dis, s2[1]), _uzak(dis, s2[2])) <= 0.6]
    for tur in ("duy", "glop", "anahtar", "priz", "sigorta"):
        if tur not in lejant:
            uyarilar.append(f"lejantta {tur} etiketi yok; sayısı bilinmiyor")
            continue
        g = lejant[tur]["ogeler"]
        if tur in ("glop", "anahtar"):
            d = _lejant_dairesi(g)
            if d:
                parca = _parcalar(g, d["renk"])
                if tur == "glop":                       # çaprazların sayısı ve ikişer ikişer açı farkları
                    cs = [s for s in parca if _capraz(s)]
                    L[tur] = {"renk": d["renk"], "cap": d["cap"], "cizgi": len(cs), "capraz_aci": _capraz_acilari(cs)}
                else:                                   # tırnak: boyu, ucundaki kısa çizginin boyu; iki tırnağın dizilişi
                    t = degen_tirnaklar(parca, d["m"], d["cap"])
                    uclar = [(s, s2) for s in t for s2 in uctaki(parca, s, d["m"])]
                    uc = [s2[3] for _, s2 in uclar]
                    uc_aci = [_aci_farki(_aci(s), _aci(s2)) for s, s2 in uclar]
                    isin, aci = _tirnak_cifti(t, d["m"]) if len(t) == 2 else (None, None)
                    L[tur] = {"renk": d["renk"], "cap": d["cap"], "cizgi": len(t), "tirnak": sum(s[3] for s in t) / len(t) if t else None,
                              "uc": sum(uc) / len(uc) if uc else None, "uc_aci": sum(uc_aci) / len(uc_aci) if uc_aci else None,
                              "sapma": sum(_sapma(s, d["m"]) for s in t) / len(t) if t else None, "aci": aci, "isin_aci": isin}
                G[tur] = bilesim(g, d["r"], 0.5)
        elif tur == "duy":
            dolgu = [o for o in g if o["dolgu"]]
            if dolgu:
                renk = Counter(o["renk"] for o in dolgu).most_common(1)[0][0]
                r = _kutu([o for o in dolgu if o["renk"] == renk])
                L[tur] = {"renk": renk, "olcu": sorted((r.width, r.height))}
                G[tur] = bilesim(g, r, 1.0)
        elif tur == "priz":
            renkler = Counter(o["renk"] for o in g if not o["dolgu"] and o["cizgiler"])
            U = _u_isaretleri(_parcalar(g, renkler.most_common(1)[0][0])) if renkler else []
            if len(U) == 1 and abs(U[0]["parcalar"][1][3] - U[0]["parcalar"][2][3]) <= UC_PAYI_PT:
                a = U[0]["aci"]                         # açılar: iki kolun arası, kolların (ortalama) ve sapın tabanla açısı
                L[tur] = {"renk": renkler.most_common(1)[0][0], **U[0]["olcu"],
                          "aci": {"kol_kol": a["kol_kol"], "kol_taban": round(sum(a["kol_taban"]) / 2, 2), "sap_taban": a["sap_taban"]}}
        else:
            siyah = [o for o in g if _ayni_renk(o["renk"], tuple(E["sigorta_rengi"]))]
            if siyah:
                r = _kutu(siyah)
                L[tur] = {"renk": siyah[0]["renk"], "olcu": sorted((r.width, r.height))}
                G[tur] = bilesim(g, r, 1.0)
        if tur not in L:
            uyarilar.append(f"lejantta '{tur}' etiketinin işareti okunamadı")
    if "zil" in lejant:
        uyarilar.append("lejantta zil var; bu okuyucu zil işaretini okumuyor")
    if L.get("glop", {}).get("cizgi") == 0:
        uyarilar.append("lejantta glop işaretinde çapraz yok: glop BUAT'tan ayrılamaz")
    if "anahtar" in L and L["anahtar"]["tirnak"] is None:
        uyarilar.append("lejantta anahtar dairesinde tırnak yok: tekli ve çift ayrılamaz")

    sahipli: set[int] = set()
    isaretler: list[tuple[str, fitz.Rect]] = []          # (tür, kutu)

    parcali: dict[int, set] = {}                       # parçasıyla (çizgi çizgi) bir işarete giren çizim → kullanılan parçaları

    def al(oo):
        sahipli.update(id(o) for o in oo)

    def parca_al(ss):
        for s in ss:
            sahipli.add(id(s[0]))
            parcali.setdefault(id(s[0]), set()).add((round(s[1].x, 3), round(s[1].y, 3), round(s[2].x, 3), round(s[2].y, 3)))

    def serbest():                                      # henüz bir işarete girmemiş plan öğeleri
        return [o for o in plan if id(o) not in sahipli]
    # priz, çift priz ve uydu (önce: U'nun parçası başka işaretin kutusuna düşebilir; bileşime girmez)
    uydu_uzaklik = []
    if "priz" in L:
        P = L["priz"]
        U = _u_isaretleri(_parcalar(plan, P["renk"]), P)
        pa = E["aci_payi_derece"]                       # U'nun açıları lejanttakiyle aynı; uymayanın parçaları sahipsiz kalır
        aci_disi = [u for u in U if abs(u["aci"]["kol_kol"] - P["aci"]["kol_kol"]) > pa or abs(u["aci"]["sap_taban"] - P["aci"]["sap_taban"]) > pa
                    or any(abs(a - P["aci"]["kol_taban"]) > pa for a in u["aci"]["kol_taban"])]
        if aci_disi:
            uyarilar.append(f"açıları lejanttakine (kollar {P['aci']['kol_kol']:g}°, kol–taban {P['aci']['kol_taban']:g}°, sap–taban "
                            f"{P['aci']['sap_taban']:g}°) uymayan {len(aci_disi)} U")
        U = [u for u in U if u not in aci_disi]
        for u in U:
            parca_al(u["parcalar"])

        def ayni_yon(a, b):                             # iki U'nun tabanı aynı yöne bakar (`aci_payi_derece` içinde)
            return a["yon"].x * b["yon"].x + a["yon"].y * b["yon"].y >= math.cos(math.radians(pa))
        degen_ = [(i, j) for i, a in enumerate(U) for j, b in enumerate(U) if i != j and _uzak(a["uc"], b["o"]) <= UC_PAYI_PT]
        cift = [(i, j) for i, j in degen_ if ayni_yon(U[i], U[j])]
        if len(cift) != len(degen_):
            uyarilar.append(f"sapı öbürünün tabanına değen ama yönü farklı {len(degen_) - len(cift)} U çifti")
        yakin = sum(1 for i, a in enumerate(U) for j, b in enumerate(U) if i != j and UC_PAYI_PT < _uzak(a["uc"], b["o"]) <= P["sap"])
        if yakin:
            uyarilar.append(f"sapı öbürünün tabanına değmeyen ama sap boyundan yakın {yakin} U çifti (çift priz olabilir)")
        cakisan = sum(1 for i, a in enumerate(U) for j, b in enumerate(U) if i < j and (i, j) not in cift and (j, i) not in cift
                      and _kesisiyor(a["r"], b["r"], UC_PAYI_PT))
        if cakisan:                                     # iki ayrı priz üst üste binmez; kaymış bir kopya iki tekli sayılmasın
            uyarilar.append(f"kutusu bir başkasıyla kesişen ve çift olmayan {cakisan} U çifti (aynı priz iki kez çizilmiş olabilir)")
        ciftte = [i for e in cift for i in e]
        if len(ciftte) != len(set(ciftte)):
            uyarilar.append("bir U iki çift prize giriyor (üçlü priz?)")
        tek = [i for i in range(len(U)) if i not in ciftte]
        uydu = []
        for metin, yr in soz:
            if not re.fullmatch(E["uydu"], metin) or lk.contains(yr):
                continue
            m = fitz.Point((yr.x0 + yr.x1) / 2, (yr.y0 + yr.y1) / 2)
            en = min(range(len(U)), key=lambda i: _uzak(U[i]["o"], m), default=None)
            if en is None or _uzak(U[en]["o"], m) > E["uydu_uzakligi_pt"]:
                uyarilar.append("\"UYDU\" yazısının yanında priz yok")
            elif en in ciftte:
                uyarilar.append("\"UYDU\" yazısına en yakın priz çift; uydu prizi belli değil")
            elif en in uydu:
                uyarilar.append("iki \"UYDU\" yazısı aynı prize bağlanıyor")
            else:
                uydu.append(en)
                uydu_uzaklik.append(round(_uzak(U[en]["o"], m), 1))
        for i in tek:
            isaretler.append(("uydu_prizi" if i in uydu else "priz_tekli", U[i]["r"]))
        for i, j in cift:
            isaretler.append(("priz_cift", fitz.Rect(min(U[i]["r"].x0, U[j]["r"].x0), min(U[i]["r"].y0, U[j]["r"].y0),
                                                     max(U[i]["r"].x1, U[j]["r"].x1), max(U[i]["r"].y1, U[j]["r"].y1))))
    # tijli duy
    if "duy" in L:
        Gd, rd = G["duy"]
        dolgu = [o for o in plan if o["dolgu"] and o["renk"] == L["duy"]["renk"]]
        olmayan, icsiz = [], 0
        for k in _kumeler(dolgu, 1.0):
            r = _kutu(k)
            if not all(abs(a - b) <= 1.0 for a, b in zip(sorted((r.width, r.height)), L["duy"]["olcu"])):
                olmayan.append(f"{r.width:.1f} × {r.height:.1f}")
                al(k)                                       # ölçüsü tutmayan dolgu kendi uyarısıyla yazılır
                continue
            _, ic = _bilesim(serbest(), r, rd, 1.0)
            if _ayni_icerik(ic, Gd, 1.0):
                isaretler.append(("tavan_armaturu", r))
                al(ic)
            else:
                icsiz += 1
        if olmayan:
            uyarilar.append(f"duy renginde, ölçüsü lejanttakinden ({L['duy']['olcu'][0]:.1f} × {L['duy']['olcu'][1]:.1f} pt) farklı "
                            f"{len(olmayan)} dolgu ({', '.join(olmayan)} pt)")
        if icsiz:
            uyarilar.append(f"duy ölçüsünde, içi lejanttaki işarete uymayan {icsiz} dolgu")
    # glop ve buat
    buat = [r for t, r in soz if re.fullmatch(E["buat"], t)]
    if "glop" in L:
        Gg, rg = G["glop"]
        Gb = [o for o in Gg if o["tur"] != {"l"}]                         # buat: glopun çaprazsız kısmı (daire)
        capraz_yok, tutmayan, icsiz, yazili_glop, desensiz = 0, [], 0, 0, 0
        parca = _parcalar(plan, L["glop"]["renk"])
        daireler, bicimsiz = _daireler_renkte(plan, L["glop"]["renk"], L["glop"]["cap"])
        if bicimsiz:
            uyarilar.append(f"glop renginde ve çapında, eğrileri çemberin üstünde olmayan {bicimsiz} yol (daire değil)")
        for d in daireler:
            _, ic = _bilesim(serbest(), d["r"], rg, 0.5)
            cs = [s for s in parca if _capraz(s) and _icinde(s[0]["r"], d["r"], 0.5)]
            n = len(cs)
            yazili = any(d["r"].contains(fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)) for r in buat)
            if n == L["glop"]["cizgi"] and _ayni_icerik(ic, Gg, 0.5):
                aci = _capraz_acilari(cs)               # tek çapraz iki kez çizilmişse koşut iki çizgi: açı tutmaz
                if any(abs(a - b) > E["aci_payi_derece"] for a, b in zip(aci, L["glop"]["capraz_aci"])):
                    desensiz += 1
                    al(ic)
                    continue
                isaretler.append(("glop", d["r"]))
                yazili_glop += yazili
                al(ic)
            elif n == 0 and _ayni_icerik(ic, Gb, 0.5):
                if yazili:
                    isaretler.append(("buat", d["r"]))
                else:
                    capraz_yok += 1
                al(ic)
            elif n not in (0, L["glop"]["cizgi"]):
                tutmayan.append(n)
                al(ic)
            else:
                icsiz += 1
        if capraz_yok:
            uyarilar.append(f"glop renginde ve çapında, çaprazsız ve içinde \"BUAT\" yazmayan {capraz_yok} daire")
        if tutmayan:
            uyarilar.append(f"glop dairesinde lejanttakinden ({L['glop']['cizgi']}) başka sayıda çapraz: {tutmayan}")
        if desensiz:
            uyarilar.append(f"çaprazlarının arasındaki açı lejanttakine uymayan {desensiz} glop (bir çapraz iki kez çizilmiş olabilir)")
        if icsiz:
            uyarilar.append(f"glop ya da BUAT dairesinin içinde lejanttakine uymayan öğe ({icsiz} daire)")
        if yazili_glop:
            uyarilar.append(f"içinde \"BUAT\" yazan {yazili_glop} glop: glop mu buat mı belli değil")
    # anahtar
    if "anahtar" in L:
        A = L["anahtar"]
        Ga, ra = G["anahtar"]
        parca = _parcalar(plan, A["renk"])
        daireler, bicimsiz = _daireler_renkte(plan, A["renk"], A["cap"])
        if bicimsiz:
            uyarilar.append(f"anahtar dairesinin renginde ve çapında, eğrileri çemberin üstünde olmayan {bicimsiz} yol (daire değil)")
        degenler = [degen_tirnaklar(parca, d["m"], A["cap"]) for d in daireler]
        ortak = sum(1 for v in Counter(id(s) for t in degenler for s in t).values() if v > 1)
        if ortak:
            uyarilar.append(f"iki anahtar dairesine birden değen {ortak} tırnak")
        tirnak_disi, icsiz, uc_fazla, boy_disi, uc_disi, uc_acisi, uc_eksik, acisi, lejantsiz_cift, sapmasi = [], 0, 0, 0, 0, 0, 0, [], 0, []
        aci_payi = E["aci_payi_derece"]
        for d, degen in zip(daireler, degenler):
            _, ic = _bilesim(serbest(), d["r"], ra, 0.5)
            if not _ayni_icerik(ic, Ga, 0.5):
                icsiz += 1
                continue
            # tırnak: daireye değen eğik çizgi, boyu lejanttakiyle aynı; öbürleri sahipsiz kalır
            tirnak = [s for s in degen if A["tirnak"] is not None and abs(s[3] - A["tirnak"]) <= UC_PAYI_PT]
            boy_disi += len(degen) - len(tirnak)
            sapik = [s for s in tirnak if abs(_sapma(s, d["m"]) - A["sapma"]) > aci_payi]   # yarıçapla açısı lejanttakinden başka
            if sapik:
                sapmasi.extend(round(_sapma(s, d["m"])) for s in sapik)
                continue
            n = len(tirnak)
            if n == 2:                                      # iki tırnağın dizilişi lejanttaki çiftinki (aynalanmışı da olur)
                if A["aci"] is None:
                    lejantsiz_cift += 1
                    continue
                isin, aci = _tirnak_cifti(tirnak, d["m"])
                if abs(isin - A["isin_aci"]) > aci_payi or abs(aci - A["aci"]) > aci_payi:
                    acisi.append(f"{round(isin)}° / {round(aci)}°")
                    continue
            if n in (1, 2):
                isaretler.append(("anahtar_tekli" if n == 1 else "anahtar_cift", d["r"]))
            else:
                tirnak_disi.append(n)
            al(ic)
            for s in tirnak:                                # tırnak ve dıştaki ucunda lejanttaki boyda tek kısa çizgi
                ucta = uctaki(parca, s, d["m"])
                boyda = [s2 for s2 in ucta if A["uc"] is not None and abs(s2[3] - A["uc"]) <= UC_PAYI_PT]
                uygun = [s2 for s2 in boyda if abs(_aci_farki(_aci(s), _aci(s2)) - A["uc_aci"]) <= aci_payi]   # tırnakla açısı da
                uc_fazla += len(ucta) > 1
                uc_disi += len(ucta) - len(boyda)
                uc_acisi += len(boyda) - len(uygun)
                uc_eksik += A["uc"] is not None and not uygun
                parca_al([s, *uygun[:1]])
        if tirnak_disi:
            uyarilar.append(f"anahtar dairesinde bir ya da iki olmayan tırnak: {tirnak_disi}")
        if icsiz:
            uyarilar.append(f"anahtar dairesinin içinde lejanttakine uymayan öğe ({icsiz} daire)")
        if boy_disi:
            uyarilar.append(f"anahtar dairesine değen, boyu lejanttaki tırnaktan farklı {boy_disi} eğik çizgi")
        if acisi:
            uyarilar.append(f"iki tırnağının dizilişi lejanttakine ({round(A['isin_aci'])}° / {round(A['aci'])}°) uymayan {len(acisi)} anahtar "
                            f"dairesi ({', '.join(acisi)}; değdikleri yerlerin ve çizgilerin açı farkı)")
        if sapmasi:
            uyarilar.append(f"yarıçapla açısı lejanttakinden ({round(A['sapma'])}°) farklı {len(sapmasi)} tırnak "
                            f"({', '.join(f'{a}°' for a in sapmasi)})")
        if lejantsiz_cift:
            uyarilar.append(f"lejantta iki tırnaklı anahtar yok: {lejantsiz_cift} iki tırnaklı anahtarın dizilişi denetlenemez")
        if uc_fazla:
            uyarilar.append(f"ucunda birden çok çizgi olan {uc_fazla} tırnak")
        if uc_disi:
            uyarilar.append(f"tırnağın ucunda boyu lejanttakinden farklı {uc_disi} çizgi")
        if uc_acisi:
            uyarilar.append(f"tırnağın ucunda tırnakla açısı lejanttakinden ({round(A['uc_aci'])}°) farklı {uc_acisi} çizgi")
        if uc_eksik:
            uyarilar.append(f"ucunda lejanttaki kısa çizgi olmayan {uc_eksik} tırnak")
    # sigorta kutusu
    if "sigorta" in L:
        Gs, rs = G["sigorta"]
        lw, lh = L["sigorta"]["olcu"]
        siyah = [o for o in plan if _ayni_renk(o["renk"], tuple(E["sigorta_rengi"])) and o["r"].width <= 2 * lh and o["r"].height <= 2 * lh]
        icsiz = 0
        for k in _kumeler(siyah):
            r = _kutu(k)
            a, b = sorted((r.width, r.height))
            if abs(a - lw) <= 0.1 * lw and abs(b - lh) <= 0.1 * lh:
                _, ic = _bilesim(serbest(), r, rs, 1.0)
                if _ayni_icerik(ic, Gs, 1.0):
                    isaretler.append(("sigorta_kutusu", r))
                    al(ic)
                else:
                    icsiz += 1
        if icsiz:
            uyarilar.append(f"sigorta kutusu ölçüsünde, içi lejanttaki işarete uymayan {icsiz} kutu")

    # kaydırılarak iki kez çizilmiş işaret: aynı türden iki işaretin kutusu kesişmez (prizde U'ların kutusu yukarıda)
    aile = {"tavan_armaturu": "duy", "glop": "glop", "buat": "glop", "anahtar_tekli": "anahtar", "anahtar_cift": "anahtar",
            "sigorta_kutusu": "sigorta"}
    ust_uste = sum(1 for i, (t1, r1) in enumerate(isaretler) for t2, r2 in isaretler[i + 1:]
                   if t1 in aile and aile.get(t2) == aile[t1] and _kesisiyor(r1, r2, UC_PAYI_PT))
    if ust_uste:
        uyarilar.append(f"kutusu aynı türden bir başkasıyla kesişen {ust_uste} işaret çifti (aynı işaret kaydırılarak iki kez çizilmiş olabilir)")
    # bir işaret başka türden bir işaretin içine çizilmez (ör. BUAT ya da glop dairesinin içinde tam bir U); kolu düşebilir, ortası düşmez
    tur_ailesi = aile | {"priz_tekli": "priz", "priz_cift": "priz", "uydu_prizi": "priz"}
    icte = sum(1 for t1, r1 in isaretler for t2, r2 in isaretler if tur_ailesi[t1] != tur_ailesi[t2]
               and r2.contains(fitz.Point((r1.x0 + r1.x1) / 2, (r1.y0 + r1.y1) / 2)))
    if icte:
        uyarilar.append(f"kutusunun ortası başka türden bir işaretin kutusunda olan {icte} işaret (biri öbürünün içine çizilmiş olabilir)")
    # parçasıyla işarete giren çizimin (PDF yolu) öbür parçaları da bir işarete girmeli: aynı yolda U'nun yanına çizilmiş fazla çizgi yutulmaz
    yarim = sum(1 for o in plan if id(o) in parcali and (o["tur"] != {"l"} or len(parcali[id(o)]) < len(o["cizgiler"])))
    if yarim:
        uyarilar.append(f"bir parçası işarete giren ama başka parçası hiçbir işarete girmeyen {yarim} çizim")

    # sessiz sayı yok: işaret renklerinde (her boyda) ya da sigortanın iç desenindeki ve işaret renklerine yakın tonlarda (işaret boyunda),
    # hiçbir işarete girmeyen öğe; aynı renklerde duvar çerçevesinin dışındaki öğe
    siyah_ = tuple(E["sigorta_rengi"])
    tam = {o["renk"] for t, d in lejant.items() if t not in ("sigorta", "zil") for o in d["ogeler"]}
    ek = (G["sigorta"][1] if "sigorta" in G else set()) - tam - {siyah_}
    ek |= {o["renk"] for o in ogeler if o["renk"] not in tam | ek and o["renk"] != siyah_ and not _ayni_renk(o["renk"], duvar)
           and any(_renk_farki(o["renk"], c) <= E["yakin_renk_payi"] for c in tam)}
    isaret_boyu = max((max(_kutu(d["ogeler"]).width, _kutu(d["ogeler"]).height) for d in lejant.values() if d["ogeler"]), default=0.0)

    def aday(o):
        return o["renk"] in tam or (o["renk"] in ek and max(o["r"].width, o["r"].height) <= 2 * isaret_boyu)
    sahipsiz = [o for o in plan if aday(o) and id(o) not in sahipli]
    for ad, oo in (("lejant renginde", [o for o in sahipsiz if o["renk"] in tam]),
                   ("sigortanın iç desenindeki ya da lejant rengine yakın tonda", [o for o in sahipsiz if o["renk"] not in tam])):
        if oo:
            tur = Counter(("dolgu" if o["dolgu"] else "çizgi" if o["tur"] == {"l"} else "eğri") + f" {max(o['r'].width, o['r'].height):.1f}"
                          for o in oo)
            uyarilar.append(f"{ad}, hiçbir işarete uymayan {len(oo)} öğe ({', '.join(f'{k} pt × {n}' for k, n in sorted(tur.items()))})")
    disarida = [o for o in disari if aday(o)]
    if disarida:
        uyarilar.append(f"duvar çerçevesinin {E['cerceve_payi_cm']:g} cm dışında lejant renginde {len(disarida)} öğe: sayılmadı")

    sayim = {k: sum(1 for t, _ in isaretler if t == k) for k in ELEKTRIK}
    sayim["zil"] = 0 if "zil" not in lejant else None
    plandaki = {"duy": ("tavan_armaturu",), "glop": ("glop",), "anahtar": ("anahtar_tekli", "anahtar_cift"),
                "priz": ("priz_tekli", "priz_cift", "uydu_prizi"), "sigorta": ("sigorta_kutusu",)}
    yok = [t for t in L if not sum(sayim[k] for k in plandaki[t])]
    if yok:                                         # sessiz sıfır yok: lejanttaki türün planda hiç işareti yoksa ölçüsü tutmamış olabilir
        uyarilar.append(f"lejantta olup planda hiç bulunamayan tür: {', '.join(yok)}")
    konumlar = sorted(({"tur": t, "xy": [round(((r.x0 + r.x1) / 2 - kutu.x0) / sx, 1), round((kutu.y1 - (r.y0 + r.y1) / 2) / sy, 1)]}
                       for t, r in isaretler), key=lambda k: (ISARET_SIRASI.index(k["tur"]), k["xy"]))
    return {"sayim": sayim, "buat": sum(1 for t, _ in isaretler if t == "buat"), "buat_yazisi": len(buat), "konumlar": konumlar,
            "lejant": {t: {k: (list(v) if isinstance(v, tuple) else round(v, 2) if isinstance(v, float) else
                               [round(x, 2) for x in v] if isinstance(v, list) else v) for k, v in d.items()} for t, d in L.items()},
            "uydu_uzakligi_pt": uydu_uzaklik, "olcek_pt_cm": [round(sx, 5), round(sy, 5)],
            "atilan": {"cerceve_disinda": len(disarida), "ayni_yerde_iki_kez": sum(1 for o in kopyalar if o["renk"] in tam | ek and not lk.contains(o["m"])),
                       "isaretten_buyuk": sum(1 for o in plan + disari if o["renk"] in ek and not aday(o))},
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


def katman(M: dict, H: dict | None, K: dict | None, ek: dict | None = None, ayar: dict | None = None) -> tuple[dict, list[dict]]:
    """Okumayı PR #28 biçimine çevirir. Bir bölümde uyarı varsa o bölümün satırları katmana girmez; her uyarı bölümüyle
    `teyit_bekliyor`'a yazılır ve kıyas aracı o bölümün satırlarını kapıya almaz. Montaj teyitteyse ölçeğini ve duvar çerçevesini
    montajın dış ölçüsünden alan bölümler (H, makas, omega, dere; KH-3'te elektrik) de teyide düşer (KH-2, hakem değişikliği). `ek`: açılan
    KH-2 ve KH-3 bölümleri (bölüm → okuma; sayfası bulunamayan bölüm None, katmana girmez ve teyit yazmaz; kıyasta "paftada yok" kapıyı
    geçmez)."""
    ek, ayar = ek or {}, ayar or VARSAYILAN
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
        if ayar["cati"] != "besik":
            teyit.append({"bolum": "makas", "neden": f"çatı \"{ayar['cati']}\"; baş makas kuralı (ana ailenin iki ucu) yalnız kalkanlı beşikte"})
    for b, o in ek.items():
        if o is not None:
            teyit += [{"bolum": b, "neden": u} for u in o["uyarilar"]]
    if M["uyarilar"]:
        bagli = [b for b, var in (("h_plani", H), ("makas", K), ("omega", ek.get("omega")), ("dere", ek.get("dere")), ("elektrik", ek.get("elektrik")))
                 if var is not None]
        teyit += [{"bolum": b, "neden": "montaj teyitte; bu bölümün ölçeği ve duvar çerçevesi montajın dış ölçüsünden"} for b in bagli]
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
        boy = ', '.join(sorted({str(m['boy_cm']) for m in yavru}))
        ek_not = f"; ana çatıdan ayrı {len(yavru)} kısa makas ({_adlar(yavru)}, boy {boy} cm)" if yavru else ""
        out["makas_bas"] = {"adet": len(bas), "not": f"makas planı {_adlar(bas)} (ana çatının iki ucu)"}
        out["makas_orta"] = {"adet": len(orta), "not": f"makas planı {_adlar(orta)}; boy {ana[0]['boy_cm']} cm{ek_not}"}
        out["makas_yavru"] = {"adet": len(yavru), "not": f"makas planı {_adlar(yavru)}; ana çatıdan ayrı kısa makas, boy {boy} cm" if yavru
                              else "makas planı: ana çatıdan ayrı makas yok"}
    O = ek.get("omega")
    if O is not None and "omega" not in kapali:
        ky = O["konum"]
        out[ayar["omega"]["anahtar"]] = {
            "adet": O["parca"],
            "not": f"tavan omega planı: {O['parca']} parça, {O['toplam_m']:g} m ({_carpim(O['boylar'])}); duvar ekseninde {ky['duvar_ekseni']}, "
                   f"duvar yüzünde {ky['duvar_yuzu']}, arada {ky['ara'] + ky['duvar_ici']}"}
    A = ek.get("asik")
    if A is not None and "asik" not in kapali:
        yuz = ", ".join(f"{y['sira']} sıra" for y in A["yuzler"])
        out["asik"] = {"adet": A["parca"], "not": f"aşık planı: {_carpim(A['boylar'], ' + ')} = {A['toplam_m']:g} m; {len(A['yuzler'])} yüz ({yuz})"}
    for b, anahtar, ad in (("kaplama", "sandvic_panel", "çatı kaplaması planı"), ("betopan", "bas_makas_betopan", "baş makas betopan yerleşimi")):
        L = ek.get(b)
        if L is not None and b not in kapali:
            tur = " + ".join(f"{o['cizimde']} × ({o['olcu_cm'][0]:g} × {o['olcu_cm'][1]:g})" if o["olcu_cm"] else f"{o['cizimde']}" for o in L["turler"])
            out[anahtar] = {"adet": L["adet"], "not": f"{ad}: {tur}; lejantta {' + '.join(str(o['lejantta']) for o in L['turler'])}; "
                                                      f"{len(L['gruplar'])} grup ({' + '.join(map(str, L['gruplar']))})"}
    D = ek.get("dere")
    if D is not None and "dere" not in kapali:
        boylar = " + ".join(f"{h['boy_cm']:g}" for h in D["hatlar"])
        out["dere"] = {"adet": D["hat"], "not": f"makas ve dere planı: {D['hat']} hat, {boylar} cm = {D['toplam_m']:g} m"}
        uc = sum(1 for i in D["inisler"] if i["yer"] == "uc")
        out["inis"] = {"adet": D["inis"], "not": f"makas ve dere planı: {D['inis']} iniş (hat ucunda {uc}, arada {D['inis'] - uc})"}
    El = ek.get("elektrik")
    if El is not None and "elektrik" not in kapali:
        out["elektrik"] = {k: {"adet": El["sayim"][k], "not": "elektrik planı: " + _elektrik_notu(k, El)} for k in ELEKTRIK}
    return out, teyit


def _elektrik_notu(k: str, El: dict) -> str:
    L, s = El["lejant"], El["sayim"]
    olcu = lambda v: " × ".join(f"{x:.1f}".replace(".", ",") for x in v)
    return {
        "tavan_armaturu": f"tijli duy, lejanttaki dolgulu karenin ölçüsünde ({olcu(L['duy']['olcu'])} pt)",
        "glop": f"lejanttaki daire ({olcu([L['glop']['cap']])} pt) ve içinde {L['glop']['cizgi']} çapraz; çaprazsız, içinde BUAT yazan "
                f"{El['buat']} daire buat (sayılmadı)",
        "anahtar_tekli": f"lejanttaki daire ({olcu([L['anahtar']['cap']])} pt) ve ona değen tek tırnak",
        "anahtar_cift": "aynı daire, iki tırnak",
        "priz_tekli": f"lejanttaki U (kol {olcu([L['priz']['kol']])}, taban {olcu([L['priz']['taban']])}, sap {olcu([L['priz']['sap']])} pt); "
                      f"UYDU yanındaki {s['uydu_prizi']} U düşüldü",
        "priz_cift": "iki U arka arkaya: birinin sapı öbürünün tabanının ortasına değer",
        "uydu_prizi": "\"UYDU\" yazısına en yakın tek U (" + ", ".join(f"{u:g}".replace(".", ",") for u in El["uydu_uzakligi_pt"]) + " pt)"
                      if El["uydu_uzakligi_pt"] else "\"UYDU\" yazısı yok",
        "zil": "lejantta zil yok",
        "sigorta_kutusu": f"lejanttaki çerçevenin ölçüsünde ({olcu(L['sigorta']['olcu'])} pt)",
    }[k]


def _carpim(boylar: dict[str, int], ayirac: str = ", ") -> str:
    return ayirac.join(f"{n} × {b}" if n > 1 else b for b, n in boylar.items())


def _guvenli(okuyan, pg) -> dict:
    """Ek bölüm okunamazsa (ör. sayfada duvar çizgisi yok) okuma durmaz; bölüm nedeniyle teyide düşer, KH-1 bölümleri okunur."""
    try:
        return okuyan(pg)
    except ValueError as e:
        return {"uyarilar": [f"okunamadı: {e}"]}


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
    bilinmeyen = [b for b in ayar["ek_bolumler"] if b not in ACILABILEN]
    if bilinmeyen:
        raise ValueError(f"bilinmeyen ek bölüm: {bilinmeyen}; okunabilenler {list(ACILABILEN)}")
    doc = fitz.open(pdf)
    sayfa = sayfalari_bul(doc, ayar)
    if "montaj" not in sayfa:
        raise ValueError("montaj planı sayfası bulunamadı")
    M = montaj_oku(doc[sayfa["montaj"]], ayar)
    H = h_oku(doc[sayfa["h"]], ayar, M["dis_olcu_cm"]) if "h" in sayfa else None
    K = makas_oku(doc[sayfa["makas"]], ayar, M["dis_olcu_cm"]) if "makas" in sayfa else None
    okuyan = {"omega": lambda pg: omega_oku(pg, ayar, M), "asik": lambda pg: asik_oku(pg, ayar), "kaplama": lambda pg: lejantli_oku(pg, ayar),
              "betopan": lambda pg: lejantli_oku(pg, ayar), "dere": lambda pg: dere_oku(pg, ayar, M["dis_olcu_cm"]),
              "elektrik": lambda pg: elektrik_oku(pg, ayar, M["dis_olcu_cm"])}
    ek = {b: _guvenli(okuyan[b], doc[sayfa[EK_SAYFA[b]]]) if EK_SAYFA[b] in sayfa else None for b in ACILABILEN if b in ayar["ek_bolumler"]}
    kat, teyit = katman(M, H, K, ek, ayar)
    pano = Counter((p["tur"], p["duvar"]) for p in M["panolar"])
    ad = proje.get("kod", "?") + (f" ({proje['ap']})" if proje.get("ap") else "")
    return {
        "kaynak": f"{ad} montaj paftası; tek genel pafta okuyucusu (İE-15 KH-1, KH-2 ve KH-3, sürüm {SURUM}); kodla okundu, elle okuma yok",
        "pafta_sha256": sha,
        # KH-1'in üç sayfası burada; ek bölümlerin sayfası kendi ayrıntısında (`ayrinti.<bölüm>.sayfa`)
        "okuyucu": {"surum": SURUM, "sayfa_sayisi": len(doc),
                    "sayfalar": {k: v + 1 for k, v in sorted(sayfa.items()) if k in ("montaj", "h", "makas")}},
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
                "atilan": M["atilan"],
            },
            "h_plani": None if H is None else {k: H[k] for k in ("turler", "konumlar", "olcek_pt_cm", "lejant_dairesi", "atilan")},
            "makas": None if K is None else {k: K[k] for k in ("yon", "renk", "makaslar", "olcek_pt_cm", "atilan") if k in K},
            **{b: None if o is None else {"sayfa": sayfa[EK_SAYFA[b]] + 1, **{k: v for k, v in o.items() if k != "uyarilar"}}
               for b, o in ek.items()},
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
    for b in ACILABILEN:
        if b not in o["ayrinti"]:
            continue
        a = o["ayrinti"][b]
        ozet_alani = {"omega": ("parca", "toplam_m", "boylar", "konum"), "asik": ("parca", "toplam_m", "boylar", "yuzler"),
                      "kaplama": ("adet", "turler", "gruplar"), "betopan": ("adet", "turler", "gruplar"),
                      "dere": ("hat", "toplam_m", "inis"), "elektrik": ("sayim", "buat")}[b]
        if a is None:
            satir.append(f"{b}: sayfası bulunamadı (katmana girmedi)")
        elif not all(k in a for k in ozet_alani):
            satir.append(f"{b} (s. {a['sayfa']}): okunamadı (nedeni TEYİT satırında)")
        else:
            satir.append(f"{b} (s. {a['sayfa']}) " + json.dumps({k: a[k] for k in ozet_alani}, ensure_ascii=False))
    for k in o:
        if isinstance(o[k], dict) and "adet" in o[k] or k in ("h_plani", "elektrik"):
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
