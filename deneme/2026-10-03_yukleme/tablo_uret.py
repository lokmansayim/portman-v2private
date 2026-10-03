#!/usr/bin/env python3
"""`sonuc/` altındaki hesap çıktılarından şartname belgesinin tablolarını üretir (`sonuc/tablolar.md`).

Tablolar elle yazılmaz: belge ile hesap aynı sayıları göstersin diye buradan kopyalanır.

Kullanım:
    python tablo_uret.py
"""
from __future__ import annotations

import json
from pathlib import Path

BURADA = Path(__file__).resolve().parent
S = BURADA / "sonuc"
ORNEKLER = (("90 m²", "ornek_90m2"), ("62 m²", "ornek_62m2"), ("105 m²", "ornek_105m2"))


def oku(ad: str) -> dict:
    return json.loads((S / ad).read_text(encoding="utf-8"))


def tr(x, n=0) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def adet(x) -> str:
    return "" if x is None else str(x)


def karsilastirma_tablosu() -> list[str]:
    veri = {ad: oku(f"{dosya}_karsilastirma.json") for ad, dosya in ORNEKLER}
    sira, kural = [], {}
    for v in veri.values():
        for s in v["satirlar"]:
            if s["kalem"] in v.get("karsilastirma", {}) and s["kalem"] not in kural:
                sira.append((s["grup"], s["kalem"]))
                kural[s["kalem"]] = (s["formul"], s["durum"])
    gruplar = []
    for g, _ in sira:
        if g not in gruplar:
            gruplar.append(g)
    cik = ["| Grup | Kalem | Kural | Durum | " + " | ".join(f"{ad}: hesap / liste" for ad, _ in ORNEKLER) + " |", "|---|---|---|---|" + "---|" * len(ORNEKLER)]
    for g in gruplar:
        for gg, kalem in sira:
            if gg != g:
                continue
            huc = []
            for ad, _ in ORNEKLER:
                k = veri[ad].get("karsilastirma", {}).get(kalem)
                huc.append("—" if k is None else f"{k['hesap']} / {k['liste']}" + ("" if k["hesap"] == k["liste"] else " ✗"))
            cik.append(f"| {g} | {kalem} | {kural[kalem][0]} | {kural[kalem][1]} | " + " | ".join(huc) + " |")
    cik.append("")
    ozet = []
    for ad, _ in ORNEKLER:
        o = veri[ad]["karsilastirma_ozeti"]
        ozet.append(f"{ad}: {o['karsilastirilan']} kalemin {o['ayni']} tanesinde adet aynı")
    top = sum(veri[ad]["karsilastirma_ozeti"]["karsilastirilan"] for ad, _ in ORNEKLER)
    ayni = sum(veri[ad]["karsilastirma_ozeti"]["ayni"] for ad, _ in ORNEKLER)
    cik.append("Özet: " + "; ".join(ozet) + f". Toplam {top} karşılaştırmanın {ayni} tanesi aynı.")
    cik += ["", "| Çelik (kg) | " + " | ".join(f"{ad}: hesap / liste / fark" for ad, _ in ORNEKLER) + " |", "|---|" + "---|" * len(ORNEKLER)]
    for anahtar, baslik in (("dis", "Dış duvar"), ("ic", "İç duvar"), ("duvar", "Duvar toplamı"), ("kiris_kolon", "Kiriş ve kolon"), ("cati", "Çatı"), ("toplam", "Toplam")):
        huc = []
        for ad, _ in ORNEKLER:
            k = veri[ad].get("celik_kg_karsilastirma", {}).get(anahtar)
            huc.append("—" if k is None else f"{k['hesap']} / {k['liste']} / {'+' if k['fark_yuzde'] > 0 else '−'}%{tr(abs(k['fark_yuzde']), 1)}")
        cik.append(f"| {baslik} | " + " | ".join(huc) + " |")
    return cik


def taslak_tablosu() -> list[str]:
    baz, d140 = oku("C8201_yukleme_taslak.json"), oku("C8201_dis_karkas_140_yukleme_taslak.json")
    d = {(s["grup"], s["kalem"], s["boyut"]): s for s in d140["satirlar"]}
    cik = ["| Grup | Kalem | Boyut | Baz | Dış 140 | Ölçü (baz) | kg (baz) | Durum |", "|---|---|---|---|---|---|---|---|"]
    gorulen = set()
    for s in baz["satirlar"]:
        anahtar = (s["grup"], s["kalem"], s["boyut"])
        o = d.get(anahtar)
        if o is None:   # profil değiştiği için boyutu farklı olan çelik satırları
            o = next((x for x in d140["satirlar"] if x["grup"] == s["grup"] and x["kalem"] == s["kalem"] and (x["grup"], x["kalem"], x["boyut"]) not in gorulen and x["boyut"] != s["boyut"]), None)
        if o is not None:
            gorulen.add((o["grup"], o["kalem"], o["boyut"]))
        if o is None:
            oteki = "yok"
        elif s["grup"] == "Çelik panel" and (o["kg"] != s["kg"] or o["boyut"] != s["boyut"]):
            oteki = (f"{o['boyut']}: " if o["boyut"] != s["boyut"] else "") + ("" if o["kg"] is None else f"{tr(o['kg'])} kg")
        elif o["adet"] is None and s["adet"] is None and o["olcu"] != s["olcu"]:
            oteki = f"{tr(o['olcu'], 1)} {o['birim']}"
        elif o["adet"] == s["adet"]:
            oteki = "aynı"
        else:
            oteki = adet(o["adet"])
        olcu = "" if s["olcu"] is None else f"{tr(s['olcu'], 1)} {s['birim']}"
        cik.append(f"| {s['grup']} | {s['kalem']} | {s['boyut']} | {adet(s['adet'])} | {oteki} | {olcu} | {'' if s['kg'] is None else tr(s['kg'])} | {s['durum']} |")
    return cik


KAPLAMALAR = (("Sandviç panel", "C8201_yukleme_taslak.json"), ("Tek kat panel", "C8201_kaplama_tek_kat_panel.json"),
              ("OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit)", "C8201_kaplama_osb_kiremit.json"),
              ("OSB + nem bariyeri + trapez sac", "C8201_kaplama_osb_trapez.json"), ("Trapez sac", "C8201_kaplama_trapez_sac.json"),
              ("OSB + membran + shingle", "C8201_kaplama_osb_shingle.json"))
ELEKTRIK = (("Tijli duy", "tijli_duy"), ("Yuvarlak glop", "glop"), ("Tekli anahtar", "tekli_anahtar"), ("Çiftli anahtar", "cift_anahtar"),
            ("Tekli priz", "tekli_priz"), ("Çiftli priz", "cift_priz"), ("Uydu prizi", "uydu_prizi"))
ISLEV_ADI = {"yatak_odasi": "yatak odası", "banyo": "banyo", "salon": "salon", "mutfak": "mutfak", "hol": "hol", "veranda": "veranda"}


def kaplama_tablosu() -> list[str]:
    cik = ["| Seçenek | Kalem | Boyut | Adet | Durum |", "|---|---|---|---|---|"]
    for ad, dosya in KAPLAMALAR:
        v = oku(dosya)
        satirlar = [s for s in v["satirlar"] if s["grup"] == "Çatı kaplamaları" or (s["grup"] == "Vida" and ("Trapez vida (5,5 × 60)" in s["kalem"] or "panel)" in s["kalem"] or "OSB ve yalıpan" in s["kalem"]))]
        for s in satirlar:
            cik.append(f"| {ad} | {s['kalem']} | {s['boyut']} | {adet(s['adet'])} | {s['durum']} |")
    return cik


def kosebent_tablosu() -> list[str]:
    """Köşebent kuralı (Ubeydullah): üç gerçek listede oda çevreleri bilinir, iç köşe sayısı bilinmez."""
    k = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))["kosebent"]["deger"]
    cik = ["| Liste | Oda çevreleri (m) | Oda sayısı | Hesap (oda başına 4 iç köşe) | Listede | Listedeki adedin denk geldiği iç köşe |", "|---|---|---|---|---|---|"]
    for ad, dosya in ORNEKLER:
        v = oku(f"{dosya}_karsilastirma.json")
        kb, liste = v["ara"]["kosebent"], v["karsilastirma"]["Köşebent"]["liste"]
        denk = (liste * k["parca_boyu_m"] - kb["tavan_cevresi_m"]) / k["kose_boyu_m"]
        cik.append(f"| {ad} | {tr(kb['tavan_cevresi_m'], 2)} | {kb['ic_kose'] // k['plan_yoksa_oda_basina_ic_kose']} | {v['karsilastirma']['Köşebent']['hesap']} | {liste} | {tr(denk, 1)} |")
    c = oku("C8201_yukleme_taslak.json")
    kb = c["ara"]["kosebent"]
    kose = next(s for s in c["satirlar"] if s["kalem"] == "Köşebent")
    cik += ["", f"Ç8201 (planından): oda çevreleri {tr(kb['tavan_cevresi_m'], 2)} m, iç köşe {kb['ic_kose']}; ({tr(kb['tavan_cevresi_m'], 2)} + {kb['ic_kose']} × 2,7) ÷ 2,5 = {tr(kb['boy_m'] / k['parca_boyu_m'], 1)} → {kose['adet']} adet."]
    return cik


def elektrik_sinama_tablosu() -> list[str]:
    """Oda başına elektrik kuralı (Ubeydullah) ile 105 m² listenin pafta sayımı."""
    v = oku("ornek_105m2_karsilastirma.json")
    kural = v["ara"]["elektrik_kural"]
    sayim = {s["kalem"]: s["adet"] for s in v["satirlar"] if s["grup"] == "Elektrik"}
    cik = ["| Kalem | Kural | Pafta sayımı (liste) |", "|---|---|---|"]
    tk = ts = 0
    for ad, anahtar in ELEKTRIK:
        cik.append(f"| {ad} | {kural[anahtar]} | {sayim[ad]} |")
        tk, ts = tk + kural[anahtar], ts + sayim[ad]
    cik.append(f"| Toplam | {tk} | {ts} |")
    cik.append(f"| W otomat (sigorta) | {kural['sigorta']} | {sayim['W otomat (sigorta)']} |")
    return cik


def elektrik_oda_tablosu() -> list[str]:
    """Ç8201: elektrik kuralının oda oda dökümü."""
    k = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))["elektrik_oda"]["deger"]["odalar"]
    g = oku("C8201_girdi.json")
    cik = ["| Mahal | Kural | " + " | ".join(ad for ad, _ in ELEKTRIK) + " |", "|---|---|" + "---|" * len(ELEKTRIK)]
    top = {a: 0 for _, a in ELEKTRIK}
    for o in g["elektrik_odalar"]:
        say = {a: sum(k[i].get(a, 0) for i in o["islev"]) for _, a in ELEKTRIK}
        for a, n in say.items():
            top[a] += n
        cik.append(f"| {o['ad']} | {' + '.join(ISLEV_ADI[i] for i in o['islev'])} | " + " | ".join(str(say[a]) if say[a] else "" for _, a in ELEKTRIK) + " |")
    cik.append("| Toplam | | " + " | ".join(str(top[a]) for _, a in ELEKTRIK) + " |")
    return cik


def main() -> int:
    kt = karsilastirma_tablosu()
    cik = ["# Tablolar (hesap çıktılarından üretildi; elle düzeltilmez)", "", "## Üç gerçek listeyle karşılaştırma", ""] + kt
    cik += ["", "## Adedi tutmayan kalemler", ""] + kt[:2] + [x for x in kt[2:] if "✗" in x]
    cik += ["", "## Ç8201 taslak: baz ve dış 140", ""] + taslak_tablosu()
    cik += ["", "## Ç8201: çatı kaplaması seçenekleri", ""] + kaplama_tablosu()
    cik += ["", "## Köşebent: mühendisin formülü", ""] + kosebent_tablosu()
    cik += ["", "## Elektrik kuralının sınaması (105 m² liste)", ""] + elektrik_sinama_tablosu()
    cik += ["", "## Ç8201: elektrik, oda oda", ""] + elektrik_oda_tablosu()
    (S / "tablolar.md").write_text("\n".join(cik) + "\n", encoding="utf-8")
    print("yazıldı: sonuc/tablolar.md,", len(cik), "satır")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
