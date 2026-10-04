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


# Altı kaplamanın çıktısı `sonuc/C8201_kaplama_<anahtar>.json`; baz paketin kaplaması (kurallar.json) tabloda başa alınır.
KAPLAMALAR = (("tek_kat_panel", "Tek kat panel"), ("sandvic_panel", "Sandviç panel"),
              ("osb_kiremit", "OSB + nem bariyeri + kiremit desen sac (motorda: OSB + membran + metal kiremit)"),
              ("osb_trapez", "OSB + nem bariyeri + trapez sac"), ("trapez_sac", "Trapez sac"), ("osb_shingle", "OSB + membran + shingle"))
ELEKTRIK = (("Tijli duy", "tijli_duy"), ("Yuvarlak glop", "glop"), ("Tekli anahtar", "tekli_anahtar"), ("Çiftli anahtar", "cift_anahtar"),
            ("Tekli priz", "tekli_priz"), ("Çiftli priz", "cift_priz"), ("Uydu prizi", "uydu_prizi"))
ISLEV_ADI = {"yatak_odasi": "yatak odası", "banyo": "banyo", "salon": "salon", "mutfak": "mutfak", "hol": "hol", "veranda": "veranda"}


def kaplama_tablosu() -> list[str]:
    cik = ["| Seçenek | Kalem | Boyut | Adet | Durum |", "|---|---|---|---|---|"]
    baz_kaplama = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))["baz_paket_cati_kaplamasi"]["deger"]
    assert oku("C8201_yukleme_taslak.json")["cati_kaplamasi_anahtar"] == baz_kaplama, "Ç8201 taslağı baz paketin kaplamasıyla hesaplanmalı"
    for anahtar, ad in sorted(KAPLAMALAR, key=lambda x: x[0] != baz_kaplama):
        v = oku(f"C8201_kaplama_{anahtar}.json")
        assert v["cati_kaplamasi_anahtar"] == anahtar, (anahtar, v["cati_kaplamasi_anahtar"])
        if anahtar == baz_kaplama:
            ad += " (baz paket)"
        satirlar = [s for s in v["satirlar"] if s["grup"] == "Çatı kaplamaları" or (s["grup"] == "Vida" and ("Trapez vida (5,5 × 60)" in s["kalem"] or "panel)" in s["kalem"] or "OSB ve yalıpan" in s["kalem"]))]
        for s in satirlar:
            cik.append(f"| {ad} | {s['kalem']} | {s['boyut']} | {adet(s['adet'])} | {s['durum']} |")
    return cik


def dizilim_tablosu() -> list[str]:
    """Kırma çatıda kaplama adedi: çatı açılımı ve dizilim (Lokman, 4 Ekim 2026 01:42; taşma: mühendis, 12:14;
    her yüzde köşeden başlama, kesim payı ve kapatma genişlikleri: Lokman, 15:18).
    Ç8201'de şerit dizilen kaplamalar (güncel ürün genişlikleriyle ve Lokman'ın andığı öteki ürünlerle), 62 m² gerçek liste
    ve mühendisin 10 × 10 m dört omuz metrajı."""
    from cati_acilim import BASLANGIC_ADI, dizilim, kural_dizilimi
    kr = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))
    kd = kr["kirma_cati_dizilim"]["deger"]
    baz_kaplama = kr["baz_paket_cati_kaplamasi"]["deger"]
    c = oku("C8201_girdi.json")["cati"]
    assert kd["baslangic"] != "en_az", "tablo başlıkları dizilimin kuralda yazılı yerden başladığını söylüyor"
    cik = [f"| Çatı | Kaplama | Kapatır | Adet ({BASLANGIC_ADI[kd['baslangic']]}) | En az paneli veren dizilimle | Altı başlangıçla | Artan parça kullanılmazsa | Alan olarak en az | Kesim payı sıfır / 1 cm | Taşma |",
           "|---|---|---|---|---|---|---|---|---|---|"]

    def satir(cati_adi: str, ad: str, cati: dict, kaplama: str, kapatma: float | None = None) -> str:
        if kapatma is not None:      # başka bir ürünün genişliğiyle (kuraldaki güncel değerin yerine)
            cati = {**cati, "kapatma_m": kapatma}
        d = kural_dizilimi(kr, cati, kaplama)
        den = d["denemeler"]
        px, py = cati["plan_m"]
        kullanmadan = dizilim(px, py, cati["egim"], d["kapatma_m"], cati["panel_boyu_m"], False, d["baslangic"], kd["kesim_payi_m"], d["tasma_m"])["adet"]
        aralik = str(min(den.values())) if len(set(den.values())) == 1 else f"{min(den.values())}–{max(den.values())}"
        return (f"| {cati_adi} | {ad} | {round(d['kapatma_m'] * 100)} cm | {d['adet']} ({d['tam_boy_adedi']} tam boy + {d['adet'] - d['tam_boy_adedi']} kesilen) | "
                f"{d['en_az_adet']} | {aralik} | {kullanmadan}{'' if d['paylas'] else ' (listeye giren)'} | {d['alan_alt_siniri']} | "
                f"{d['paysiz_adet']} / {d['bir_cm_payla_adet']} | {tr(d['tasma_m'] * 100, 1)} cm |")

    boy = f"Ç8201 (L {round(c['panel_boyu_m'] * 1000)})"
    sirali = sorted((("tek_kat_panel", "Tek kat panel"), ("sandvic_panel", "Sandviç panel"), ("trapez_sac", "Trapez sac"), ("osb_kiremit", "Kiremit desen sac")),
                    key=lambda x: x[0] != baz_kaplama)
    for anahtar, ad in sirali:
        cik.append(satir(boy, ad + (" (baz paket)" if anahtar == baz_kaplama else ""), c, anahtar))
    # öteki ürünler: Lokman'ın andığı 80 cm kapatan sandviç panel; 2025 listelerindeki 87 cm tek kat panel ve 110 cm kiremit desen sac
    for w in kr["sandvic_panel_kapatma_m"].get("diger_urunler_m", []):
        cik.append(satir(boy, f"Sandviç panel, {round(w * 100)} cm kapatan ürün", c, "sandvic_panel", w))
    cik.append(satir(boy, "Tek kat panel, 87 cm kapatan ürün (2025 listeleri)", c, "tek_kat_panel", 0.87))
    cik.append(satir(boy, "Kiremit desen sac, 110 cm kapatan ürün (2025 listeleri)", c, "osb_kiremit", 1.10))
    g62 = json.loads((BURADA / "ornek_62m2_girdi.json").read_text(encoding="utf-8"))["cati"]
    liste = json.loads((BURADA / "ornek_62m2_gercek_liste.json").read_text(encoding="utf-8"))["kalemler"]["Sandviç panel"]["adet"]
    cik.append(satir(f"62 m² gerçek liste (L {round(g62['panel_boyu_m'] * 1000)}; listede {liste})", "Sandviç panel", g62, "sandvic_panel"))
    # Mühendisin 10 × 10 m dört omuz metrajı (Çatı Hesapları çalışma kitabı): 118 m² yüzey, trapez sac L 5900, 36 adet.
    # Plan saçak dahil 10,6 × 10,6 m ve eğim %33 alındı: yüzey 10,6² × 1,053 = 118,3 m² (metrajdaki yüzeyi veriyor).
    cik.append(satir("Mühendisin 10 × 10 m dört omuz metrajı (L 5900; metrajda 36)", "Trapez sac", {"plan_m": [10.6, 10.6], "egim": 0.33, "panel_boyu_m": 5.9}, "trapez_sac"))
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
    veranda = kb.get("veranda_tavan_cevresi_m") or 0.0     # veranda tavanının çevresi de sayılır (mühendis, 4 Ekim 12:14)
    assert abs(kb["tavan_cevresi_m"] + veranda + kb["ic_kose"] * k["kose_boyu_m"] - kb["boy_m"]) < 0.01, kb
    cik += ["", f"Ç8201 (planından): oda çevreleri {tr(kb['tavan_cevresi_m'], 2)} m, veranda tavanının çevresi {tr(veranda, 2)} m, iç köşe {kb['ic_kose']}; "
                f"({tr(kb['tavan_cevresi_m'], 2)} + {tr(veranda, 2)} + {kb['ic_kose']} × 2,7) ÷ 2,5 = {tr(kb['boy_m'] / k['parca_boyu_m'], 1)} → {kose['adet']} adet."]
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
    cik += ["", "## Kırma çatıda kaplama dizilimi", ""] + dizilim_tablosu()
    cik += ["", "## Köşebent: mühendisin formülü", ""] + kosebent_tablosu()
    cik += ["", "## Elektrik kuralının sınaması (105 m² liste)", ""] + elektrik_sinama_tablosu()
    cik += ["", "## Ç8201: elektrik, oda oda", ""] + elektrik_oda_tablosu()
    (S / "tablolar.md").write_text("\n".join(cik) + "\n", encoding="utf-8")
    print("yazıldı: sonuc/tablolar.md,", len(cik), "satır")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
