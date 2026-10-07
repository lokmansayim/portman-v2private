#!/usr/bin/env python3
"""Kör test kıyası: gerçek yükleme listesi ile kendi listelerimiz, satır satır.

Gerçek liste `sonuc/KT01_gercek_liste.json` (adsız; 6 Ekim 2026'da, kendi listemiz dondurulduktan sonra açıldı). Karşılaştırılan listeler:
    kor          dondurulan liste (`sonuc/KT01_yukleme.json`; commit 0658a1d)
    duzeltilmis  yalnız bizim hatalarımız düzeltildikten sonra, bugünkü kurallarla
    sablon       + Eylül 2026 uygulaması: o listenin şablonunun ve paftalarının, mevcut kurallardan farklı yaptığı her şey
                 (`yukleme.py --sablon 2026`; karar bekliyor)
    pafta        + elektrik ve iniş sayısı projenin paftalarından sayılınca

Birim: gerçek listenin bir ya da birkaç satırı ile bizim listenin onlara denk satırları (`BIRIMLER`). Adetler toplanarak karşılaştırılır;
gerçek listenin bir satırı, birimi aynıysa "aynı" sayılır. Her farkın sınıfı (asıl nedeni) elle yazılmıştır (`kiyas_farklar.json`) ve koddaki sayımla
denetlenir:
    girdi   girdi hatası: projenin belgesinde ya da modelinde vardı, yanlış ya da eksik okuduk
    kural   kural hatası: o projede ilk kez karşılaşılan bir durumda kuralımız yoktu ya da varsayımımız tutmadı; motor yanlış hesapladı
    karar   karar farkı: mevcut kural (Lokman'ın ya da mühendisin söylediği, Excel motorundan ya da 2025 listelerinden gelen) o listedeki
            uygulamadan farklı; hangisinin geçerli olacağına Lokman karar verir
    elle    listenin elle yuvarlaması, elle çizimi ya da kaba hesabı
    pafta   paftadan sayılan kalem: kör testte paftalardaki adetler girdi değildi
Yalnız ilk ikisi bizim hatamızdır. Bir satırda birden çok neden varsa sınıf asıl nedendir; nedenler eşit ağırlıktaysa ve biri bizim hatamızsa satır
bizim hatamız sayılır. Asıl nedeni başka olan ama bizim hatamızın da payı bulunan satırın `pay` alanı vardır. Bu denetim mekaniktir: düzeltilmiş
liste, dondurulan listenin yalnız bizim hatalarımız düzeltilmiş hali olduğu için, sınıfı bizim hatamız olmayan bir satırın adedi iki listede farklıysa
`pay` yazılmış olmalıdır (aynıysa yazılmamalıdır).
"Aynı" yalnız adedin aynı olmasıdır: profil, kalınlık, renk ve kalem adı farkları ayrıca yazılır (`bilgi`, `adet_disi`); çelikte ağırlık ayrı tablodadır.
Kör listede aynı çıkan ama tesadüfen ya da eşikte tutan birimlerin (birbirini götüren iki fark) `not` alanı vardır.
Son listede hâlâ farklı olan birimin `kalan` açıklaması türüyle başlar: `elle:`, `ölçü:` ya da `soru:`.
`bilgi`: adedi etkilemeyen ek bilgi (ağırlık, kalem adı); sayıma girmez. Dosyanın `adet_disi` listesi, gerçek listede yazan ama adet
karşılaştırmasına girmeyen farklardır (renk, kalem adı, özellik); raporda ayrı bölümdür.

Kullanım:
    python kiyas.py --kor sonuc/KT01_yukleme.json --duzeltilmis sonuc/KT01_duzeltilmis_yukleme.json \\
        --sablon sonuc/KT01_duzeltilmis_2026.json --pafta sonuc/KT01_duzeltilmis_2026_pafta.json --md sonuc/KT01_kiyas.md --json sonuc/KT01_kiyas.json
    (hepsi birden: bash kiyas_kos.sh <tanım.json> [python])
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent

# (ad, gerçek liste satırları, bizim satırlar: kalem deseni ya da (kalem deseni, boyut deseni))
BIRIMLER: list[tuple[str, list[int], list]] = [
    ("Dış cephe duvar panelleri", [11], [r"^Dış cephe duvar panelleri$"]),
    ("İç cephe duvar panelleri", [12], [r"^İç cephe duvar panelleri$"]),
    ("Kolon", [13], [r"^Veranda dikmeleri"]),
    ("Kiriş", [14], [r"^Kirişler|^Veranda kirişleri"]),
    ("Veranda duvarı ve korkuluğu", [15, 16], [r"^Veranda korkuluğu|^Veranda duvarı"]),
    ("Çatı makas panelleri", [17], [r"^Çatı makas panelleri$"]),
    ("Baca karkası", [18], [r"^Baca karkası$"]),
    ("Müştemilat duvar panelleri", [19], [r"^Müştemilat duvar panelleri$"]),
    ("Müştemilat çatı paneli", [20], [r"^Çatı paneli \(ek yapının çatısı\)$"]),
    ("Parça C profil 1,2", [21], [(r"^Boy C profil$", r"1,2")]),
    ("Parça C profil 0,8", [22], [(r"^Boy C profil$", r"0,8")]),
    ("Tavan omegası", [25], [r"^Tavan omegası"]),
    ("Köşebent", [26], [r"^Köşebent$"]),
    ("Aşık", [27], [r"^Aşık$"]),
    ("Alın sacı", [28], [r"^Alın sacı"]),
    ("Baş makas Z'si", [29], [r"^Baş makas Z"]),
    ("Saçak sacı", [30], [r"^Saçak sacı"]),
    ("Saçak omegası", [31], [r"^Saçak omegası$"]),
    ("Dış cephe Boardex: bina (duvarlar, veranda içi, makas alnı, baca)", [33, 38, 39, 40], [r"^Dış cephe Boardex$"]),
    ("Dış cephe Boardex: müştemilat (duvarlar, çatı panelinin saçağı)", [34, 41], [r"^Dış cephe Boardex \(müştemilat\)$"]),
    ("Veranda tavanı (Boardex)", [37], [r"^Veranda tavanı \(Boardex\)$"]),
    ("Nem bariyeri: bina", [35], [r"^Nem bariyeri \(bina|^Nem bariyeri \(dış cephe\)$"]),
    ("Nem bariyeri: müştemilat", [36], [r"^Nem bariyeri \(müştemilat"]),
    ("Tavan alçıpan beyaz", [43], [r"^Tavan alçıpan beyaz$"]),
    ("Tavan alçıpan yeşil", [44], [r"^Tavan alçıpan yeşil$"]),
    ("Tavan alçıpan yeşil: müştemilat", [45], [r"^Tavan alçıpan yeşil \(müştemilat\)$"]),
    ("Duvar alçıpan beyaz", [46], [r"^Duvar alçıpan beyaz$"]),
    ("Duvar alçıpan yeşil", [47], [r"^Duvar alçıpan yeşil$"]),
    ("Duvar alçıpan yeşil: müştemilat", [48], [r"^Duvar alçıpan yeşil \(müştemilat\)$"]),
    ("İç duvar OSB", [49], [r"^İç duvar OSB \d+ mm$"]),
    ("İç duvar OSB: müştemilat", [50], [r"^İç duvar OSB \d+ mm \(müştemilat\)$"]),
    ("Duvar izolasyonu", [51], [r"^Duvar izolasyonu$"]),
    ("Sandviç panel L 5070", [53], [(r"^Sandviç panel$", r"^L 50")]),
    ("Sandviç panel L 3420", [54], [(r"^Sandviç panel$", r"^L 34")]),
    ("Sandviç panel L 2870", [55], [(r"^Sandviç panel$", r"^L 28")]),
    ("Sandviç panel L 2340", [56], [(r"^Sandviç panel$", r"^L 23")]),
    ("Metal kiremit mahyası", [57], [r"^Metal kiremit mahyası$"]),
    ("Sandviç panel kapaması (bina ve müştemilat)", [58, 59], [r"^Sandviç panel kapaması$"]),
    ("Ters mahya", [60], [r"^Ters mahya$"]),
    ("Ters mahya kenar kutuları", [61], [r"^Ters mahya kenar kutusu$"]),
    ("Damlalık (bina ve müştemilat)", [62, 63], [r"^Damlalık|^Duvar dibi sacı"]),
    ("Mahya bandı", [64], [r"^Mahya bandı$"]),
    ("Çatı izolasyonu", [65], [r"^Çatı şiltesi|^Çatı izolasyonu"]),
    ("Metal dere", [67], [r"^Metal dere$"]),
    ("Dere iniş borusu", [68], [r"^Dere iniş borusu$"]),
    ("Dere iniş aparatı", [69], [r"^Dere iniş aparatı$"]),
    ("Dere kapağı", [70], [r"^Dere kapağı$"]),
    ("Açık dirsek", [71], [r"^Açık dirsek$"]),
    ("Kapalı dirsek", [72], [r"^Kapalı dirsek$"]),
    ("İniş kelepçesi", [73], [r"^İniş kelepçesi$"]),
    ("Dere kelepçesi", [74], [r"^Dere kelepçesi$"]),
    ("Melamin kapı (80'lik kanat)", [76], [r"^Melamin kapı \(80"]),
    ("Melamin kapı (70'lik kanat)", [77], [r"^Melamin kapı \(70"]),
    ("Tijli duy", [82], [r"^Tijli duy$"]),
    ("Yuvarlak glop", [83], [r"^Yuvarlak glop$"]),
    ("Ampul", [84], [r"^Ampul$"]),
    ("NYM kablo (3 × 2,5)", [85], [r"^NYM kablo \(3"]),
    ("NYM kablo (2 × 1,5)", [86], [r"^NYM kablo \(2"]),
    ("Uydu kablo", [87], [r"^Uydu kablo$"]),
    ("Besleme kablosu", [88], [r"^Besleme kablosu"]),
    ("Besleme kablo borusu", [89], [r"^Besleme kablo borusu$"]),
    ("Tekli anahtar", [90], [r"^Tekli anahtar$"]),
    ("Çiftli anahtar", [91], [r"^Çiftli anahtar$"]),
    ("Tekli priz", [92], [r"^Tekli priz$"]),
    ("Çiftli priz", [93], [r"^Çiftli priz$"]),
    ("Uydu prizi", [94], [r"^Uydu prizi$"]),
    ("Zil", [95], [r"^Zil$"]),
    ("Buat kasa", [96], [r"^Buat kasa$"]),
    ("W otomat (sigorta)", [97], [r"^W otomat"]),
    ("Sigorta kutusu", [98], [r"^Sigorta kutusu"]),
    ("İzole bant", [99], [r"^İzole bant$"]),
    ("Kaçak akım rölesi", [100], [r"^Kaçak akım rölesi$"]),
    ("RYSB pul başlı", [102], [r"^RYSB"]),
    ("Alçıpan vidası", [103], [r"^Alçıpan vidası"]),
    ("OSB ve yalıpan vidası", [104], [r"^OSB ve yalıpan vidası"]),
    ("Trapez vida (5,5 × 25)", [105], [r"^Trapez vida \(5,5 × 25\)"]),
    ("Trapez vida (5,5 × 60)", [106], [r"^Trapez vida \(5,5 × 60\)"]),
    ("Trapez vida (5,5 × 110)", [107], [r"^Trapez vida \(5,5 × 110"]),
    ("Çelik dübel", [108], [r"^Çelik dübel"]),
    ("Şase pul", [109], [r"^Şase pul$"]),
    ("8'lik trapez uç", [110], [r"^8'lik trapez uç$"]),
    ("PH2 uç", [111], [r"^PH2 uç$"]),
    ("230'luk kesme taşı", [112], [r"^230'luk kesme taşı$"]),
    ("İnox taş", [113], [r"^İnox taş$"]),
    ("Çırpı ipi", [114], [r"^Çırpı ipi$"]),
    ("Acil müdahale kapağı", [115], [r"^Çatı müdahale kapağı$"]),
    ("Tavan boyası", [121], [r"^Tavan boyası$"]),
    ("Astar", [122], [r"^Astar$"]),
    ("Silikonize mastik", [123], [r"^Silikonize mastik$"]),
    ("Dayson", [124], [r"^Dayson$"]),
    ("Poliüretan köpük", [125], [r"^Poliüretan köpük$"]),
]
GRUP_ADI = {"ÇELİK PANEL GRUBU": "Çelik panel", "METAL AKSAM GRUBU": "Metal aksam", "DIŞ CEPHE KAPLAMA GRUBU": "Dış cephe kaplama",
            "İÇ CEPHE KAPLAMA GRUBU": "İç cephe kaplama", "ÇATI KAPLAMALARI GRUBU": "Çatı kaplamaları", "DERE GRUBU": "Dere",
            "KAPI VE PENCERE GRUBU": "Kapı ve pencere", "ELEKTRİK GRUBU": "Elektrik", "VİDA GRUBU": "Vida", "BOYA GRUBU": "Boya",
            "SIHHİ TESİSAT GRUBU": "Sıhhi tesisat"}
SINIF_ADI = {"girdi": "girdi hatası", "kural": "kural hatası", "karar": "karar farkı", "elle": "elle (liste)", "pafta": "paftadan sayılır"}
BIZIM = ("girdi", "kural")
KALAN_ADI = {"elle": "listenin elle yuvarlaması, kaba hesabı ya da elle çizimi", "ölçü": "ölçünün nereden alındığı", "soru": "kural bilinmiyor ya da teyit gerekiyor"}
LISTELER = ("kor", "duzeltilmis", "sablon", "pafta")
LISTE_ADI = {"kor": "Kör liste", "duzeltilmis": "Düzeltilmiş", "sablon": "+ Eylül 2026", "pafta": "+ pafta"}


def bizim_adet(satirlar: list[dict], desenler: list) -> tuple[int | None, float | None]:
    """Desenlere uyan satırların adet ve kg toplamı; hiç satır yoksa (None, None)."""
    bulunan = []
    for d in desenler:
        kd, bd = (d, None) if isinstance(d, str) else d
        bulunan += [s for s in satirlar if re.search(kd, s["kalem"]) and (bd is None or re.search(bd, s["boyut"])) and s not in bulunan]
    if not bulunan:
        return None, None
    kg = [s["kg"] for s in bulunan if s.get("kg") is not None]
    return sum(s["adet"] or 0 for s in bulunan), (sum(kg) if kg else None)


def karsilastir(gercek: dict, listeler: dict[str, dict]) -> list[dict]:
    g_satir = {s["satir"]: s for s in gercek["satirlar"]}
    cik = []
    for ad, satir_no, desenler in BIRIMLER:
        gs = [g_satir[n] for n in satir_no]
        kg = [s["kg"] for s in gs if s.get("kg") is not None]
        b = {"ad": ad, "grup": GRUP_ADI[gs[0]["grup"]], "gercek_satirlar": satir_no, "gercek_kalemler": [s["kalem"] for s in gs], "gercek_boyut": [s["boyut"] for s in gs],
             "gercek": sum(s["adet"] for s in gs), "gercek_kg": round(sum(kg), 2) if kg else None, "gercek_kaba": [s["kaba_hesap"] for s in gs if s.get("kaba_hesap") is not None]}
        for anahtar, liste in listeler.items():
            n, bkg = bizim_adet(liste["satirlar"], desenler)
            b[anahtar] = n
            b[anahtar + "_kg"] = None if bkg is None else round(bkg, 2)
            b[anahtar + "_ayni"] = n is not None and n == b["gercek"]
        cik.append(b)
    return cik


def ozet(birimler: list[dict], anahtar: str) -> dict:
    satir = sum(len(b["gercek_satirlar"]) for b in birimler)
    ayni = sum(len(b["gercek_satirlar"]) for b in birimler if b[anahtar + "_ayni"])
    return {"gercek_satir": satir, "ayni": ayni, "farkli": satir - ayni}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gercek", type=Path, default=BURADA / "sonuc" / "KT01_gercek_liste.json")
    for x in LISTELER:
        ap.add_argument(f"--{x}", type=Path)
    ap.add_argument("--farklar", type=Path, default=BURADA / "kiyas_farklar.json", help="her farkın elle yazılmış sınıfı ve nedeni")
    ap.add_argument("--md", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--ozet", action="store_true", help="birimleri tek tek yazdırma; yalnız özet ve sorunlar")
    a = ap.parse_args()
    gercek = json.loads(a.gercek.read_text(encoding="utf-8"))
    listeler = {x: json.loads(getattr(a, x).read_text(encoding="utf-8")) for x in LISTELER if getattr(a, x)}
    # her liste kendi yuvasında mı: kör ve düzeltilmiş listeler varsayılan hesap, öteki ikisi Eylül 2026 katmanıyla; pafta listesi pafta sayımıyla
    yuva = [f"--{x}: bu liste {'Eylül 2026 katmanıyla hesaplanmış' if 'sablon' in listeler[x] else 'varsayılan hesap'}; bu yuvaya "
            f"{'varsayılan hesap' if x in ('kor', 'duzeltilmis') else 'katmanlı liste'} verilmeli"
            for x in listeler if ("sablon" in listeler[x]) != (x in ("sablon", "pafta"))]
    if "pafta" in listeler and listeler["pafta"]["ara"].get("elektrik_kaynagi") != "pafta":
        yuva.append("--pafta: bu listede elektrik sayıları paftadan değil")
    if "sablon" in listeler and listeler["sablon"]["ara"].get("elektrik_kaynagi") == "pafta":
        yuva.append("--sablon: bu listede elektrik sayıları paftadan; pafta sayımı yalnız --pafta listesinde olmalı")
    if yuva:
        raise SystemExit("Listeler yanlış yuvada:\n  " + "\n  ".join(yuva))
    birimler = karsilastir(gercek, listeler)
    kapsanan = sorted(n for b in birimler for n in b["gercek_satirlar"])
    adetli = sorted(s["satir"] for s in gercek["satirlar"] if s["adet"] is not None and "TOPLAM" not in s["kalem"])
    if kapsanan != adetli:
        raise SystemExit(f"Birimler gerçek listenin adetli satırlarını tam kapsamıyor: eksik {sorted(set(adetli) - set(kapsanan))}, fazla {sorted(set(kapsanan) - set(adetli))}")
    farklar = json.loads(a.farklar.read_text(encoding="utf-8")) if a.farklar.exists() else {}
    OZEL = ("aciklama", "adet_disi")
    sorun = [f"{ad}: `kiyas_farklar.json` içinde var ama birim listesinde yok" for ad in farklar if ad not in OZEL and ad not in {b["ad"] for b in birimler}]
    adet_disi = farklar.get("adet_disi", [])
    sorun += [f"adet_disi[{i}]: konu, gercek, biz ve yapilan alanları olmalı" for i, x in enumerate(adet_disi) if set(x) != {"konu", "gercek", "biz", "yapilan"}]
    # bizim listelerimizde hiçbir birime girmeyen satır (gerçek listede karşılığı yok): sessizce düşmesin
    for x, liste in listeler.items():
        for st in liste["satirlar"]:
            if st["kalem"].startswith("Toplam (") or st["adet"] is None:
                continue
            if not any(re.search(d if isinstance(d, str) else d[0], st["kalem"]) and (isinstance(d, str) or re.search(d[1], st["boyut"])) for _, _, ds in BIRIMLER for d in ds):
                sorun.append(f"{LISTE_ADI[x]}: '{st['kalem']}' ({st['adet']}) hiçbir birime girmiyor; gerçek listede karşılığı yoksa `adet_disi`nde yazılmalı ve birim tablosuna eklenmeli")
    for b in birimler:
        f = farklar.get(b["ad"], {})
        bilinmeyen = set(f) - {"sinif", "neden", "yapilan", "kalan", "not", "bilgi", "pay"}
        if bilinmeyen:
            sorun.append(f"{b['ad']}: bilinmeyen alan ({', '.join(sorted(bilinmeyen))})")
        b["sinif"], b["neden"], b["yapilan"], b["kalan"], b["not"] = f.get("sinif"), f.get("neden"), f.get("yapilan"), f.get("kalan"), f.get("not")
        b["bilgi"], b["pay"] = f.get("bilgi"), f.get("pay")
        if "kor" in listeler and "duzeltilmis" in listeler and not b["kor_ayni"]:
            degisti = b["kor"] != b["duzeltilmis"]
            if b["sinif"] in BIZIM and b["pay"]:
                sorun.append(f"{b['ad']}: sınıfı zaten bizim hatamız; 'pay' yazılmaz")
            if b["sinif"] not in BIZIM and degisti and not b["pay"]:
                sorun.append(f"{b['ad']}: sınıfı {b['sinif']} ama adet düzeltmelerimizle değişti ({b['kor']} → {b['duzeltilmis']}): bizim payımız ('pay') yazılmamış")
            if b["sinif"] not in BIZIM and not degisti and b["pay"]:
                sorun.append(f"{b['ad']}: adet düzeltmelerimizle değişmedi ama 'pay' yazılmış")
            if b["sinif"] in BIZIM and not degisti and b["duzeltilmis"] is not None:
                sorun.append(f"{b['ad']}: sınıfı bizim hatamız ama düzeltilmiş listede adet değişmedi ({b['kor']})")
        if b["sinif"] and b["sinif"] not in SINIF_ADI:
            sorun.append(f"{b['ad']}: bilinmeyen sınıf ({b['sinif']})")
        if "kor" in listeler:
            if b["kor_ayni"] and b["sinif"]:
                sorun.append(f"{b['ad']}: kör listede aynı ama sınıf yazılmış ({b['sinif']})")
            if not b["kor_ayni"] and not b["sinif"]:
                sorun.append(f"{b['ad']}: kör listede farklı ({b['kor']} / {b['gercek']}) ama sınıf yazılmamış")
            if not b["kor_ayni"] and b["not"]:
                sorun.append(f"{b['ad']}: kör listede farklı; 'not' yalnız kör listede aynı çıkan birimler içindir")
            sonra_farkli = [x for x in listeler if x != "kor" and not b[x + "_ayni"]]
            if b["kor_ayni"] and sonra_farkli and not b["not"]:
                sorun.append(f"{b['ad']}: kör listede aynı, sonraki listede farklı ({', '.join(sonra_farkli)}) ama not yazılmamış")
        son = next((x for x in reversed(LISTELER) if x in listeler), None)
        b["kalan_turu"] = b["kalan"].split(":")[0] if b["kalan"] else None
        if son and son != "kor":
            if not b[son + "_ayni"] and not b["kalan"]:
                sorun.append(f"{b['ad']}: son listede hâlâ farklı ({b[son]} / {b['gercek']}) ama kalan farkın nedeni yazılmamış")
            if b[son + "_ayni"] and b["kalan"]:
                sorun.append(f"{b['ad']}: son listede aynı ama 'kalan' yazılmış")
            if b["kalan"] and b["kalan_turu"] not in KALAN_ADI:
                sorun.append(f"{b['ad']}: 'kalan' açıklaması türüyle başlamıyor (elle: | ölçü: | soru:)")
    ozetler = {x: ozet(birimler, x) for x in listeler}
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    son = next((x for x in reversed(LISTELER) if x in listeler), None)
    sinif_sayimi, bizim_ozet, kalan_sayimi, tesaduf = {}, {}, {}, []
    if "kor" in listeler:
        farkli = [b for b in birimler if not b["kor_ayni"]]
        sinif_sayimi = {sn: satir([b for b in farkli if b["sinif"] == sn]) for sn in SINIF_ADI}
        bizim = [b for b in farkli if b["sinif"] in BIZIM]
        # bizim hatamız olan satırlar: hangi listede tutmaya başlıyor
        bizim_ozet = {"satir": satir(bizim)}
        gorulen: list = []
        for x in [x for x in LISTELER if x in listeler and x != "kor"]:
            yeni_tutan = [b for b in bizim if b[x + "_ayni"] and b not in gorulen]
            bizim_ozet[x] = satir(yeni_tutan)
            gorulen += yeni_tutan
        son_liste = [x for x in LISTELER if x in listeler][-1]
        kalanlar_b = [b for b in bizim if b not in gorulen]
        # hiçbir listemizde satırı olmayan birim: hata düzeltilemedi (kural bilinmiyor)
        bizim_ozet["duzeltilemedi"] = satir([b for b in kalanlar_b if b[son_liste] is None])
        bizim_ozet["kalan"] = satir(kalanlar_b) - bizim_ozet["duzeltilemedi"]
        tesaduf = [b for b in birimler if b["kor_ayni"] and b.get("not")]
        bizim_ozet["payimiz_olan"] = satir([b for b in farkli if b["sinif"] not in BIZIM and b.get("pay")])
    if son and son != "kor":
        kalanlar = [b for b in birimler if not b[son + "_ayni"]]
        kalan_sayimi = {tur: satir([b for b in kalanlar if b["kalan_turu"] == tur]) for tur in KALAN_ADI}
    print("gerçek listenin adetli satırı:", len(adetli), "| birim:", len(birimler))
    for x in listeler:
        print(f"  {LISTE_ADI[x]:14s} aynı {ozetler[x]['ayni']:3d} / {ozetler[x]['gercek_satir']}")
    if sinif_sayimi:
        print("  kör listedeki farkların sınıfı (gerçek satır):", sinif_sayimi, "| toplam", sum(sinif_sayimi.values()))
        print("  bizim hatamız olan satırlar:", bizim_ozet, "| kör listede tesadüfen tutan satır:", satir(tesaduf))
    if kalan_sayimi:
        print(f"  son listede ({LISTE_ADI[son]}) kalan farkların türü (gerçek satır):", kalan_sayimi, "| toplam", sum(kalan_sayimi.values()))
    for b in ([] if a.ozet else birimler):
        print(f"  {b['ad'][:58]:58s} gerçek {b['gercek']:>6} | " + " | ".join(f"{LISTE_ADI[x]} {('—' if b[x] is None else b[x]):>6}{'  ' if b[x + '_ayni'] else ' ✗'}" for x in listeler)
              + (f" | {b['sinif']}" if b.get("sinif") else "") + (f" | kalan: {b['kalan_turu']}" if b.get("kalan_turu") else ""))
    if sorun:
        print("\nSINIFLAMA SORUNLARI:")
        for s_ in sorun:
            print("  -", s_)
    celik = [b for b in birimler if b["grup"] == "Çelik panel"]
    kg = {x: round(sum(b[x + "_kg"] or 0 for b in celik), 1) for x in listeler}
    kg_gercek = round(sum(b["gercek_kg"] or 0 for b in celik), 2)
    print("çelik kg: gerçek", kg_gercek, "|", kg)
    sonuc = {"gercek": {"ad": gercek["ad"], "sha256": gercek["kaynak"]["sha256"], "adetli_satir": len(adetli)}, "ozet": ozetler, "celik_kg": {"gercek": kg_gercek, **kg},
             "kor_farklarinin_sinifi": sinif_sayimi, "bizim_hatamiz": bizim_ozet, "kor_listede_tesadufen_tutan_satir": satir(tesaduf),
             "son_listede_kalan": kalan_sayimi, "birimler": birimler, "adet_disi": adet_disi, "siniflama_sorunlari": sorun}
    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.md:
        a.md.write_text(md_yaz(sonuc, listeler), encoding="utf-8")
    return 1 if sorun else 0


def md_yaz(sonuc: dict, listeler: dict) -> str:
    def n(v):
        return "—" if v is None else (f"{v:,}".replace(",", " ") if isinstance(v, int) else str(v).replace(".", ","))

    B = sonuc["birimler"]
    son = next((x for x in reversed(LISTELER) if x in listeler), None)
    cik = ["# KT-01 · kör test kıyası", "",
           "Gerçek yükleme listesinin adetli her satırı, kendi listelerimizle. Tablo `kiyas.py` ile üretilir; elle düzeltilmez. "
           "Farkların sınıfı ve açıklaması `kiyas_farklar.json` dosyasındadır; sayımlar koddan.", "",
           "\"Aynı\" yalnız adedin aynı olmasıdır. Profil, kalınlık, renk ve kalem adı farkları tablolarda \"Bilgi\" olarak ve sondaki \"Adet dışındaki "
           "farklar\" bölümünde yazılır; çelikte ağırlık ayrı tablodadır.", "",
           "## Özet", "",
           "| Liste | Aynı satır | Açıklama |", "|---|---|---|"]
    aciklama = {"kor": "6 Ekim 22:47'de dondurulan liste; gerçek liste açılmadan önce",
                "duzeltilmis": "yalnız bizim hatalarımız düzeltildikten sonra, bugünkü kurallarla",
                "sablon": "Eylül 2026 listesinin şablonu ve paftalarındaki dizilim de kural olursa (`--sablon 2026`; karar bekliyor)",
                "pafta": "elektrik ve iniş sayısı da projenin paftalarından sayılırsa"}
    for x in listeler:
        o = sonuc["ozet"][x]
        cik.append(f"| {LISTE_ADI[x]} | {o['ayni']} / {o['gercek_satir']} | {aciklama[x]} |")
    ck = sonuc["celik_kg"]
    cik += ["", "Çelik ağırlığı (kg): gerçek " + n(round(ck["gercek"])) + " · " + " · ".join(f"{LISTE_ADI[x].lower()} {n(round(ck[x]))}" for x in listeler) + "."]
    ss = sonuc.get("kor_farklarinin_sinifi")
    if ss:
        toplam = sum(ss.values())
        bz = sonuc["bizim_hatamiz"]
        nerede = {"duzeltilmis": "düzeltilmiş listede", "sablon": "Eylül 2026 uygulamasıyla", "pafta": "pafta sayımıyla"}
        cik += ["", f"Kör listede gerçek listenin {toplam} satırı farklıydı. Farkın asıl nedenine göre:", "",
                "| Sınıf | Satır | Anlamı |", "|---|---|---|",
                f"| girdi hatası | {ss['girdi']} | projenin belgesinde vardı, yanlış ya da eksik okuduk |",
                f"| kural hatası | {ss['kural']} | o projede ilk kez karşılaşılan durumda kuralımız yoktu ya da varsayımımız tutmadı |",
                f"| karar farkı | {ss['karar']} | mevcut kural o listedeki uygulamadan farklı; karar Lokman'ın |",
                f"| elle (liste) | {ss['elle']} | listenin elle yuvarlaması, elle çizimi ya da kaba hesabı |",
                f"| paftadan sayılır | {ss['pafta']} | kör testte paftalardaki adetler girdi değildi |", "",
                "Bir satırda birden çok neden varsa sınıf asıl nedendir; nedenler eşit ağırlıktaysa ve biri bizim hatamızsa satır bizim hatamız sayılır.", "",
                f"Bizim hatamız olan {bz['satir']} satırın " + ", ".join(f"{bz[x]} tanesi {nerede[x]}" for x in listeler if x != "kor" and bz.get(x))
                + f" tutuyor; {bz['kalan']} tanesinde hatamız düzeldi ama başka bir nedenle fark sürüyor (tablolarda \"kalan fark\")"
                + (f"; {bz['duzeltilemedi']} tanesi düzeltilemedi (kuralı bilinmiyor)." if bz.get("duzeltilemedi") else ".")
                + (f" Asıl nedeni başka olan {bz['payimiz_olan']} satırda da bizim hatamızın payı vardı (tablolarda \"Bizim payımız\")." if bz.get("payimiz_olan") else "")]
        if sonuc.get("kor_listede_tesadufen_tutan_satir"):
            cik.append(f"Kör listede tutan {sonuc['ozet']['kor']['ayni']} satırın {sonuc['kor_listede_tesadufen_tutan_satir']} tanesi tesadüfen ya da eşikte "
                       "tutuyordu (birbirini götüren iki fark; tabloda \"Not\").")
    ks = sonuc.get("son_listede_kalan")
    if ks and son:
        cik += ["", f"Son listede ({LISTE_ADI[son]}) farklı kalan {sum(ks.values())} satır:", "", "| Tür | Satır | Anlamı |", "|---|---|---|"]
        cik += [f"| {tur} | {ks[tur]} | {KALAN_ADI[tur]} |" for tur in KALAN_ADI]
    celik = [b for b in B if b["grup"] == "Çelik panel"]
    kgl = [x for x in listeler if x in ("kor", "duzeltilmis")]
    TOL = 0.5       # %: bu kadar farka kadar ağırlık "tutuyor" sayılır

    def fark(b, x):
        return None if b[x + "_kg"] is None or not b["gercek_kg"] else (b[x + "_kg"] - b["gercek_kg"]) / b["gercek_kg"] * 100

    def yuzde(v):
        return "—" if v is None else ("0,0" if abs(v) < 0.05 else f"{v:+.1f}".replace(".", ","))

    cik += ["", "## Çelik ağırlığı (kg)", "", "| Kalem | Gerçek | " + " | ".join(f"{LISTE_ADI[x]} | fark %" for x in kgl) + " |", "|---|---|" + "---|---|" * len(kgl)]
    for b in celik:
        cik.append(f"| {b['ad']} | {n(b['gercek_kg'])} | " + " | ".join(n(b[x + "_kg"]) + " | " + yuzde(fark(b, x)) for x in kgl) + " |")
    cik.append(f"| Toplam | {n(ck['gercek'])} | " + " | ".join(n(ck[x]) + " | " + yuzde((ck[x] - ck["gercek"]) / ck["gercek"] * 100) for x in kgl) + " |")
    tutan = {x: sum(1 for b in celik if fark(b, x) is not None and abs(fark(b, x)) <= TOL) for x in kgl}
    cik += ["", f"Ağırlığı %{str(TOL).replace('.', ',')} içinde tutan satır ({len(celik)} satırda): " + " · ".join(f"{LISTE_ADI[x].lower()} {tutan[x]}" for x in kgl) + ". "
            "Kör listede ağırlık motorun proje ortalamalarından (duvar boyu × kg/m) hesaplanmıştı; korkuluk ve baca da 1,2 mm varsayılmıştı. "
            "Düzeltilmiş listede modeldeki profil boyundan ve modelde okunan et kalınlığından: boy × profilin birim ağırlığı (`kurallar.json` → `celik.profil_kg_m`)."]
    baslik = "| Kalem (gerçek liste) | Gerçek | " + " | ".join(LISTE_ADI[x] for x in listeler) + " | Kör listedeki farkın sınıfı | Neden | Yapılan | Kalan fark |"
    grup = None
    for b in B:
        if b["grup"] != grup:
            grup = b["grup"]
            cik += ["", f"## {grup}", "", baslik, "|---|---|" + "---|" * len(listeler) + "---|---|---|---|"]
        hucre = [(n(b[x]) + ("" if b[x + "_ayni"] else " ✗")) for x in listeler]
        neden = " ".join(x for x in (b["neden"], ("Bizim payımız: " + b["pay"]) if b.get("pay") else None, ("Not: " + b["not"]) if b.get("not") else None,
                                     ("Bilgi: " + b["bilgi"]) if b.get("bilgi") else None) if x)
        cik.append(f"| {b['ad']} | {n(b['gercek'])} | " + " | ".join(hucre) + f" | {SINIF_ADI.get(b['sinif'], '')} | {neden} | {b['yapilan'] or ''} | {b['kalan'] or ''} |")
    if sonuc.get("adet_disi"):
        cik += ["", "## Adet dışındaki farklar", "",
                "Gerçek listede yazan ama adet karşılaştırmasına girmeyenler: renk, kalem adı, özellik.", "",
                "| Konu | Gerçek liste | Bizim liste | Yapılan |", "|---|---|---|---|"]
        cik += [f"| {x['konu']} | {x['gercek']} | {x['biz']} | {x['yapilan']} |" for x in sonuc["adet_disi"]]
    return "\n".join(cik) + "\n"


if __name__ == "__main__":
    sys.exit(main())
