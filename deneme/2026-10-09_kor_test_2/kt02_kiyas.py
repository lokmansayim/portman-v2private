#!/usr/bin/env python3
"""KT-02 (ikinci kör test) kıyası: gerçek yükleme listesi ile dondurulan iki listemiz, satır satır.

Gerçek liste `sonuc/KT02_gercek_liste.json` (adsız, fiyatsız; 9 Ekim 2026'da, kendi listemiz dondurulduktan sonra açıldı). Listelerimiz:
    b   güncel kural seti (0.15), projenin yapıldığı yöntemle (B: tavan omegası ve aşık); elektrik sayıları projenin paftasından
    a   aynı, çelik standardıyla (A: çatı ve tavan paneli): bu proje bugün sipariş edilse çıkacak liste
Gerçek liste yöntem B ile hazırlandığı için "aynı" B listesinde sayılır; A bilgi içindir.

Birim: gerçek listenin bir ya da birkaç satırı ile bizim listenin onlara denk satırları (`BIRIMLER`); adetler toplanarak karşılaştırılır. Her farkın
sınıfı (asıl nedeni) elle yazılmıştır (`kt02_farklar.json`) ve sayımla denetlenir: B'de farklı her birimin `sinif` ve `neden`i olmalı, aynı birimde
olmamalı. Sınıflar (KT-01'deki gibi):
    girdi   girdi hatası: projenin belgesinde ya da modelinde vardı, yanlış ya da eksik okuduk
    kural   kural hatası: kuralımız yoktu, varsayımımız tutmadı ya da motor yanlış hesapladı
    karar   karar farkı: mevcut kural (Lokman'ın kararı ya da Excel motoru) o listedeki uygulamadan farklı
    elle    listenin elle yuvarlaması ya da kaba hesabı
    pafta   paftadan sayılan kalem (kör testte paftalardaki adetler girdi değildi)
Yalnız ilk ikisi bizim hatamızdır. Ayrıca: bizim listede olup gerçek listede olmayan satırlar (`fazla`), gerçek listede adedi yazılmayan satırlar.

"Ne olur" (`--ne-olur-b`, yalnız bilgi): düzeltilmiş B girdisinde iki kural sorusu gerçek listedeki gibi cevaplanmış sayılır (`kt02_ne_olur.py`);
tutan hiçbir satırın bozulmadığı ve tutmaya başlayan her satırın kural satırı olduğu denetlenir.

Kullanım: python kt02_kiyas.py --kor-b sonuc/KT02_B_yukleme.json --kor-a sonuc/KT02_A_yukleme.json --duz-b sonuc/KT02_duzeltilmis_B_yukleme.json \\
              --duz-a sonuc/KT02_duzeltilmis_A_yukleme.json --sablon-b sonuc/KT02_duzeltilmis_B_2026.json --ne-olur-b sonuc/KT02_ne_olur_B_yukleme.json \\
              --md sonuc/KT02_kiyas.md --json sonuc/KT02_kiyas.json
(hepsi birden: bash kt02_kiyas_kos.sh <KT02_duzeltilmis.json> [python])
Çıkış kodu: denetim sorunu varsa 1.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURADA.parent / "2026-10-06_kor_test"))
from kiyas import bizim_adet, GRUP_ADI          # noqa: E402

# (ad, gerçek liste satırları, bizim satırlar: kalem deseni ya da (kalem deseni, boyut deseni))
BIRIMLER: list[tuple[str, list[int], list]] = [
    ("Dış cephe duvar panelleri", [11], [r"^Dış cephe duvar panelleri$"]),
    ("İç cephe duvar panelleri", [12], [r"^İç cephe duvar panelleri$"]),
    ("Kolon", [13], [r"^Veranda dikmeleri"]),
    ("Kiriş (1,2)", [14], [r"^Kirişler \(kiriş paneli\)$"]),
    ("Kiriş (1,5)", [15], [r"^Kirişler \(kiriş paneli, 1,5 mm\)$"]),
    ("Çatı makas panelleri", [16], [r"^Çatı makas panelleri$"]),
    ("Çatı panelleri", [17], [r"^Çatı panelleri \(kırma"]),
    ("Veranda duvarı (korkuluk)", [18], [r"^Veranda korkuluğu|^Veranda duvarı"]),
    ("Veranda destekleri", [19], [r"^Veranda destekleri$"]),
    ("Parça C profil 1,2", [20], [(r"^Boy C profil$", r"1,2")]),
    ("Parça C profil 0,8", [21], [(r"^Boy C profil$", r"0,8")]),
    ("Tavan omegası", [24], [r"^Tavan omegası"]),
    ("Köşebent", [25], [r"^Köşebent$"]),
    ("Aşık", [26], [r"^Aşık$"]),
    ("Saçak sacı", [27], [r"^Saçak sacı"]),
    ("Saçak omegası", [28], [r"^Saçak omegası$"]),
    ("Dış cephe Boardex (veranda tavanı dahil)", [30], [r"^Dış cephe Boardex$", r"^Veranda tavanı \(Boardex\)$"]),
    ("Tavan alçıpan beyaz", [32], [r"^Tavan alçıpan beyaz$"]),
    ("Tavan alçıpan yeşil", [33], [r"^Tavan alçıpan yeşil$"]),
    ("Duvar alçıpan beyaz", [34], [r"^Duvar alçıpan beyaz$"]),
    ("Duvar alçıpan yeşil", [35], [r"^Duvar alçıpan yeşil$"]),
    ("İç duvar OSB", [36], [r"^İç duvar OSB \d+ mm$"]),
    ("Betopan (veranda korkuluk kaplaması)", [37], [r"^Betopan"]),
    ("Duvar izolasyonu", [38], [r"^Duvar izolasyonu$"]),
    ("Sandviç panel (uzun)", [40], [(r"^Sandviç panel$", r"^L 4")]),
    ("Sandviç panel (kısa)", [41], [(r"^Sandviç panel$", r"^L 1")]),
    ("Metal kiremit mahyası", [42], [r"^Metal kiremit mahyası$"]),
    ("Sandviç panel kapaması", [43], [r"^Sandviç panel kapaması$"]),
    ("Ters mahya", [44], [r"^Ters mahya$"]),
    ("Ters mahya kenar kutuları", [45], [r"^Ters mahya kenar kutusu$"]),
    ("Mahya bandı", [46], [r"^Mahya bandı$"]),
    ("Çatı izolasyonu", [47], [r"^Çatı şiltesi|^Çatı izolasyonu"]),
    ("Metal dere", [49], [r"^Metal dere$"]),
    ("Dere iniş borusu", [50], [r"^Dere iniş borusu$"]),
    ("Dere iniş aparatı", [51], [r"^Dere iniş aparatı$"]),
    ("Açık dirsek", [52], [r"^Açık dirsek$"]),
    ("Kapalı dirsek", [53], [r"^Kapalı dirsek$"]),
    ("İniş kelepçesi", [54], [r"^İniş kelepçesi$"]),
    ("Dere kelepçesi", [55], [r"^Dere kelepçesi$"]),
    ("Melamin kapı (80'lik kanat; sağ ve sol)", [57, 58], [r"^Melamin kapı \(80"]),
    ("Kompozit çelik kapı", [59], [r"^Kompozit çelik kapı"]),
    ("Tijli duy", [62], [r"^Tijli duy$"]),
    ("Yuvarlak glop", [63], [r"^Yuvarlak glop$"]),
    ("Ampul", [64], [r"^Ampul$"]),
    ("NYM kablo (3 × 2,5)", [65], [r"^NYM kablo \(3"]),
    ("NYM kablo (2 × 1,5)", [66], [r"^NYM kablo \(2"]),
    ("Uydu kablo", [67], [r"^Uydu kablo$"]),
    ("Besleme kablosu", [68], [r"^Besleme kablosu"]),
    ("Besleme kablo borusu", [69], [r"^Besleme kablo borusu$"]),
    ("Tekli anahtar", [70], [r"^Tekli anahtar$"]),
    ("Çiftli anahtar", [71], [r"^Çiftli anahtar$"]),
    ("Tekli priz (kapaklı dahil)", [72, 73], [r"^Tekli priz$"]),
    ("Çiftli priz", [74], [r"^Çiftli priz$"]),
    ("Uydu prizi", [75], [r"^Uydu prizi$"]),
    ("Zil", [76], [r"^Zil$"]),
    ("Buat kasa", [77], [r"^Buat kasa$"]),
    ("W otomat (sigorta)", [78], [r"^W otomat"]),
    ("Sigorta kutusu", [79], [r"^Sigorta kutusu"]),
    ("İzole bant", [80], [r"^İzole bant$"]),
    ("Kaçak akım rölesi", [81], [r"^Kaçak akım rölesi$"]),
    ("RYSB pul başlı", [83], [r"^RYSB"]),
    ("Alçıpan vidası", [84], [r"^Alçıpan vidası"]),
    ("OSB ve yalıpan vidası", [85], [r"^OSB ve yalıpan vidası"]),
    ("Trapez vida (5,5 × 25)", [86], [r"^Trapez vida \(5,5 × 25\)"]),
    ("Trapez vida (5,5 × 60)", [87], [r"^Trapez vida \(5,5 × 60\)"]),
    ("Trapez vida (5,5 × 110)", [88], [r"^Trapez vida \(5,5 × 110"]),
    ("Çelik dübel", [89], [r"^Çelik dübel"]),
    ("Şase pul", [90], [r"^Şase pul$"]),
    ("8'lik trapez uç", [91], [r"^8'lik trapez uç$"]),
    ("PH2 uç", [92], [r"^PH2 uç$"]),
    ("230'luk kesme taşı", [93], [r"^230'luk kesme taşı$"]),
    ("İnox taş", [94], [r"^İnox taş$"]),
    ("Çırpı ipi", [95], [r"^Çırpı ipi$"]),
    ("Acil müdahale kapağı", [96], [r"^Acil müdahale kapağı$|^Çatı müdahale kapağı$"]),
    ("Temiz su borusu", [98], [r"^Temiz su borusu$"]),
    ("Normal dirsek 20 mm", [99], [r"^Normal dirsek"]),
    ("Kulaklı dirsek 20 mm", [100], [r"^Kulaklı dirsek"]),
    ("Düz T 20 mm", [101], [r"^Düz T"]),
    ("Maşon 20 mm", [102], [r"^Maşon"]),
    ("İç dişli T 20 mm", [103], [r"^İç dişli T"]),
    ("Atlama parçası", [104], [r"^Atlama parçası"]),
    ("Dayson", [108], [r"^Dayson$"]),
    ("Poliüretan köpük", [109], [r"^Poliüretan köpük$"]),
]
ADETSIZ = {60: "Pencereler (alıcıya ait)", 106: "Boya grubu (alıcıya ait)", 107: "Silikonize mastik (alıcıya ait)"}
TOPLAM_SATIRI = 22
SINIF = {"girdi": "girdi hatası", "kural": "kural hatası", "karar": "karar farkı", "elle": "listenin elle hesabı ya da yuvarlaması", "pafta": "paftadan sayılır"}
BIZIM = ("girdi", "kural")


def n(v) -> str:
    return "—" if v is None else (f"{v:,}".replace(",", " ") if isinstance(v, int) else f"{v:g}".replace(".", ","))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kor-b", type=Path, required=True, help="dondurulan liste, yöntem B")
    ap.add_argument("--kor-a", type=Path, required=True, help="dondurulan liste, yöntem A")
    ap.add_argument("--duz-b", type=Path, help="düzeltilmiş tanımla liste, yöntem B (girdi hataları düzeltildi)")
    ap.add_argument("--duz-a", type=Path, help="düzeltilmiş tanımla liste, yöntem A")
    ap.add_argument("--sablon-b", type=Path, help="düzeltilmiş B + Eylül 2026 uygulaması (yalnız bilgi)")
    ap.add_argument("--ne-olur-b", type=Path, help="düzeltilmiş B, iki kural sorusu listedeki gibi cevaplanırsa (kt02_ne_olur.py; yalnız bilgi)")
    ap.add_argument("--gercek", type=Path, default=BURADA / "sonuc" / "KT02_gercek_liste.json")
    ap.add_argument("--farklar", type=Path, default=BURADA / "kt02_farklar.json")
    ap.add_argument("--md", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    oku = lambda p: json.loads(p.read_text(encoding="utf-8"))
    G = oku(a.gercek)
    L = {"kor_b": oku(a.kor_b), "kor_a": oku(a.kor_a)}
    for x, yol in (("duz_b", a.duz_b), ("duz_a", a.duz_a), ("sablon_b", a.sablon_b), ("ne_olur_b", a.ne_olur_b)):
        if yol:
            L[x] = oku(yol)
    F = oku(a.farklar) if a.farklar.exists() else {"birimler": {}, "fazla": {}, "adet_disi": []}
    sorun = []
    if "ne_olur_b" in L and "duz_b" not in L:
        sorun.append("--ne-olur-b düzeltilmiş B ile birlikte verilir")
    for x, beklenen in (("kor_b", "omega_asik"), ("kor_a", "panel"), ("duz_b", "omega_asik"), ("duz_a", "panel"), ("sablon_b", "omega_asik"), ("ne_olur_b", "omega_asik")):
        if x in L and L[x]["yontem"] != beklenen:
            sorun.append(f"{x} listesi yanlış yuvada (yöntem {L[x]['yontem']})")
        if x in L and (L[x].get("ara") or {}).get("elektrik_kaynagi") != "pafta":
            sorun.append(f"{x} listesinde elektrik sayıları paftadan değil")
    if "sablon_b" in L and L["sablon_b"].get("sablon") != "2026":
        sorun.append("--sablon-b Eylül 2026 katmanıyla üretilmeli")
    for x in ("kor_b", "kor_a", "duz_b", "duz_a", "ne_olur_b"):
        if x in L and L[x].get("sablon"):
            sorun.append(f"{x} listesi şablon katmanıyla üretilmiş; katmansız olmalı")
    gs = {s["satir"]: s for s in G["satirlar"]}
    kapsanan = {n_ for _, satirlar, _ in BIRIMLER for n_ in satirlar} | set(ADETSIZ) | {TOPLAM_SATIRI}
    if kapsanan != set(gs):
        sorun.append(f"gerçek listenin satırları birimlere eksiksiz dağılmadı: eksik {sorted(set(gs) - kapsanan)}, fazla {sorted(kapsanan - set(gs))}")
    for no, ad in ADETSIZ.items():
        if gs[no]["adet"] is not None:
            sorun.append(f"adetsiz sayılan satırda adet var: {ad}")
    B = []
    for ad, satirlar, desenler in BIRIMLER:
        gg = [gs[x] for x in satirlar]
        if any(s["adet"] is None for s in gg):
            sorun.append(f"{ad}: gerçek satırda adet yok")
        b = {"ad": ad, "grup": GRUP_ADI[gg[0]["grup"]], "gercek_satirlar": satirlar, "gercek_kalemler": [s["kalem"] for s in gg], "gercek_boyut": [s["boyut"] for s in gg],
             "gercek": sum(s["adet"] or 0 for s in gg), "gercek_kg": (round(sum(s["kg"] for s in gg if s["kg"] is not None), 2) if any(s["kg"] is not None for s in gg) else None),
             "gercek_kaba": [s["kaba_hesap"] for s in gg if s.get("kaba_hesap") is not None]}
        for x in L:
            adet, kg = bizim_adet(L[x]["satirlar"], desenler)
            b[x], b[x + "_kg"] = adet, (None if kg is None else round(kg, 2))
            b[x + "_ayni"] = adet is not None and adet == b["gercek"]
        nt = F["birimler"].get(ad, {})
        b.update({k: nt.get(k) for k in ("sinif", "neden", "pay", "kalan", "not")})
        if (not b["kor_b_ayni"]) != bool(b["sinif"]):
            sorun.append(f"{ad}: gerçek {b['gercek']}, kör B {b['kor_b']}; `sinif` " + ("yazılmamış" if not b["sinif"] else "yazılmış ama adet aynı"))
        if b["sinif"] and (b["sinif"] not in SINIF or not b["neden"]):
            sorun.append(f"{ad}: sınıf bilinmiyor ya da neden yazılmamış")
        if "duz_b" in L:
            if (not b["duz_b_ayni"]) != bool(b["kalan"]):
                sorun.append(f"{ad}: gerçek {b['gercek']}, düzeltilmiş B {b['duz_b']}; `kalan` " + ("yazılmamış" if not b["kalan"] else "yazılmış ama adet aynı"))
            if b["kalan"] and b["kalan"].split(":")[0] not in SINIF:
                sorun.append(f"{ad}: `kalan` türüyle başlamıyor ({', '.join(SINIF)})")
            # düzeltme yalnız girdi hatalarıdır: adedi değişen birimin sınıfı girdi olmalı ya da `pay`ı yazılmalı
            if b["kor_b"] != b["duz_b"] and b["sinif"] != "girdi" and not b["pay"]:
                sorun.append(f"{ad}: düzeltmeyle adet değişti ({b['kor_b']} → {b['duz_b']}) ama sınıfı girdi değil ve `pay` yazılmamış")
            if b["pay"] and b["kor_b"] == b["duz_b"] and not b["pay"].startswith("kural"):
                sorun.append(f"{ad}: `pay` yazılmış ama düzeltmeyle adet değişmemiş")
        B.append(b)
    for ad in set(F["birimler"]) - {b["ad"] for b in B}:
        sorun.append(f"notlarda bilinmeyen birim: {ad}")

    def fazla(liste):
        return [s for s in liste["satirlar"] if not s["kalem"].startswith("Toplam (")
                and not any(re.search(d if isinstance(d, str) else d[0], s["kalem"]) and (isinstance(d, str) or re.search(d[1], s["boyut"]))
                            for _, _, ds in BIRIMLER for d in ds)]
    Z = {x: [{"kalem": s.get("liste_adi") or s["kalem"], "ic_ad": s["kalem"], "boyut": s["boyut"], "adet": s["adet"], "kg": s["kg"], "durum": s["durum"],
              **({"sinif": F["fazla"].get(s["kalem"], {}).get("sinif"), "neden": F["fazla"].get(s["kalem"], {}).get("neden")} if x == "kor_b" else {})}
             for s in fazla(L[x])] for x in L}
    for s in Z["kor_b"]:
        if not s.get("sinif") or s["sinif"] not in SINIF:
            sorun.append(f"dondurulan B listesinde gerçek listede olmayan satırın sınıfı yazılmamış: {s['kalem']}")
    if Z.get("duz_b"):
        sorun.append("düzeltilmiş B listesinde gerçek listede olmayan satır var: " + ", ".join(s["kalem"] for s in Z["duz_b"]))
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    ozet = {x: {"gercek_satir": satir(B), "ayni": satir([b for b in B if b[x + "_ayni"]])} for x in L}
    sinif_say = {k: satir([b for b in B if b["sinif"] == k]) for k in SINIF}
    kalan_say = {k: satir([b for b in B if b["kalan"] and b["kalan"].split(":")[0] == k]) for k in SINIF} if "duz_b" in L else None
    ne_olur = None
    if "ne_olur_b" in L and "duz_b" in L:
        # yalnız iki sorunun etkisi: adedi tutmaya başlayan satır kural satırı ya da payı kural olan satır olmalı; tutan hiçbir satır bozulmamalı
        ne_olur = [{"ad": b["ad"], "gercek": b["gercek"], "duz_b": b["duz_b"], "ne_olur_b": b["ne_olur_b"], "ayni": b["ne_olur_b_ayni"]}
                   for b in B if b["ne_olur_b"] != b["duz_b"]]
        kural_payli = {b["ad"] for b in B if b["sinif"] == "kural" or (b.get("pay") or "").startswith("kural")}
        for b in B:
            if b["duz_b_ayni"] and not b["ne_olur_b_ayni"]:
                sorun.append(f"ne olur listesinde tutan satır bozuldu: {b['ad']} ({b['duz_b']} → {b['ne_olur_b']})")
            if b["ne_olur_b_ayni"] and not b["duz_b_ayni"] and b["ad"] not in kural_payli:
                sorun.append(f"ne olur listesinde tutmaya başlayan satırın sınıfı kural değil: {b['ad']}")
    toplam_g = gs[TOPLAM_SATIRI]
    kg = lambda liste: next((s["kg"] for s in liste["satirlar"] if s["kalem"].startswith("Toplam (")), None)
    adet = lambda liste: next((s["adet"] for s in liste["satirlar"] if s["kalem"].startswith("Toplam (")), None)
    sonuc = {"ozet": ozet, "siniflar": sinif_say, "kalan_siniflar": kalan_say, "bizim_hatamiz": sum(sinif_say[k] for k in BIZIM), "ne_olur": ne_olur,
             "celik": {"gercek": {"adet": toplam_g["adet"], "kg": toplam_g["kg"]}, **{x: {"adet": adet(L[x]), "kg": round(kg(L[x]), 2)} for x in L}},
             "adetsiz_gercek_satirlar": list(ADETSIZ.values()), "fazla": Z, "adet_disi": F.get("adet_disi", []), "giris": F.get("giris", ""),
             "denetim_sorunlari": sorun, "birimler": B}
    print(f"gerçek listenin adetli satırı: {satir(B)} | birim: {len(B)} | " + " · ".join(f"{x} {ozet[x]['ayni']}" for x in L))
    print(f"  kör B'de farklı {satir(B) - ozet['kor_b']['ayni']} satır: {sinif_say} · bizim hatamız {sonuc['bizim_hatamiz']}")
    if kalan_say:
        print(f"  düzeltilmiş B'de farklı {satir(B) - ozet['duz_b']['ayni']} satır: {kalan_say}")
    if ne_olur is not None:
        print("  ne olur (iki kural sorusu listedeki gibi): " + "; ".join(f"{x['ad']} {x['duz_b']} → {x['ne_olur_b']}{' (aynı)' if x['ayni'] else ''}" for x in ne_olur))
    print(f"  çelik: gerçek {toplam_g['adet']} adet {toplam_g['kg']} kg · " + " · ".join(f"{x} {sonuc['celik'][x]}" for x in L))
    print(f"  kör B'de olup gerçek listede olmayan: {[(s['kalem'], s['adet']) for s in Z['kor_b']]}")
    for s in sorun:
        print("  SORUN:", s)
    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.md:
        a.md.write_text(md(sonuc, L), encoding="utf-8")
    return 1 if sorun else 0


def md(s: dict, L: dict) -> str:
    B, o = s["birimler"], s["ozet"]
    toplam = o["kor_b"]["gercek_satir"]
    cik = ["# KT-02 · kıyas", "", s["giris"], "", "Tablo `kt02_kiyas.py` ile üretilir; elle düzeltilmez. Sınıflar ve nedenler `kt02_farklar.json`dan.", "",
           "| Liste | Aynı satır | Ne demek |", "|---|---|---|",
           f"| Kör liste, yapıldığı yöntemle (B) | {o['kor_b']['ayni']} / {toplam} | dondurulan liste (commit 59602ef); kural seti 0.15; elektrik sayıları paftadan |"]
    if "duz_b" in o:
        cik.append(f"| Düzeltilmiş (B) | {o['duz_b']['ayni']} / {toplam} | yalnız girdi hatamız düzeltildi (sundurmanın çatısı); kurallar aynı |")
    if "sablon_b" in o:
        cik.append(f"| Düzeltilmiş + Eylül 2026 uygulaması (B) | {o['sablon_b']['ayni']} / {toplam} | yalnız bilgi: `--sablon 2026` katmanı (KT-01'in Eylül 2026 listesinin uygulaması; Lokman 7 Ekim'de cevapladı, varsayılan hesapta değil) |")
    if "ne_olur_b" in o:
        cik.append(f"| İki kural sorusu listedeki gibi cevaplanırsa (B) | {o['ne_olur_b']['ayni']} / {toplam} | yalnız bilgi (`kt02_ne_olur.py`): bina alanı 90 m² (açık sundurma hariç), "
                   "korkuluk dış cephe Boardex'ine girmez; Betopan satırı motorda yok (listede 3 levha) |")
    cik.append(f"| Kör liste, çelik standardıyla (A) | {o['kor_a']['ayni']} / {toplam} | çatı ve tavan paneli: bu proje bugün sipariş edilse çıkacak liste (bilgi) |")
    if "duz_a" in o:
        cik.append(f"| Düzeltilmiş (A) | {o['duz_a']['ayni']} / {toplam} | bilgi |")
    cik += ["", f"Kör listede (B) farklı {toplam - o['kor_b']['ayni']} satırın asıl nedeni:", "", "| Sınıf | Satır | Anlamı |", "|---|---|---|"]
    cik += [f"| {k} | {v} | {SINIF[k]} |" for k, v in s["siniflar"].items()]
    cik += ["", f"Bizim hatamız (girdi + kural): {s['bizim_hatamiz']} satır; ayrıca kör listede gerçek listede olmayan {len(s['fazla']['kor_b'])} satır (aşağıda)."]
    if s["kalan_siniflar"]:
        cik += ["", f"Düzeltilmiş listede (B) farklı kalan {toplam - o['duz_b']['ayni']} satır:", "", "| Tür | Satır |", "|---|---|"]
        cik += [f"| {k} | {v} |" for k, v in s["kalan_siniflar"].items() if v]
    if s.get("ne_olur"):
        cik += ["", "İki kural sorusu listedeki gibi cevaplanırsa (yalnız bilgi) değişen satırlar: "
                + "; ".join(f"{x['ad']} {n(x['duz_b'])} → {n(x['ne_olur_b'])}" + (" (aynı)" if x["ayni"] else f" (gerçek {n(x['gercek'])})") for x in s["ne_olur"])
                + ". Tutan hiçbir satır bozulmadı (denetlenir)."]
    c = s["celik"]
    ETIKET = {"kor_b": "kör B", "kor_a": "kör A", "duz_b": "düzeltilmiş B", "duz_a": "düzeltilmiş A", "sablon_b": "+ Eylül 2026 (B)", "ne_olur_b": "ne olur (B)"}
    cik += ["", "Çelik (adet, kg): gerçek liste " + f"{c['gercek']['adet']} · {n(round(c['gercek']['kg'], 1))}"
            + "".join(f" — {ETIKET[x]} {c[x]['adet']} · {n(round(c[x]['kg'], 1))}" for x in L if x in c)
            + ". Bizim listelerde 1,5 mm kiriş kg'sız (birim ağırlığı kuralda yoktu); A'da tavan ve çatı panelleri eklenir.", "",
            "Gerçek listede adedi yazılmayan satırlar (bizim listede de yok): " + ", ".join(s["adetsiz_gercek_satirlar"]) + ".", "",
            "## Kör listede (B) olup gerçek listede olmayan satırlar", "", "| Kalem | Boyut | Adet | Sınıf | Neden |", "|---|---|---|---|---|"]
    cik += [f"| {z['kalem']} | {z['boyut']} | {n(z['adet'])} | {z.get('sinif') or ''} | {z.get('neden') or ''} |" for z in s["fazla"]["kor_b"]]
    if s["fazla"].get("duz_a") is not None or s["fazla"].get("kor_a"):
        cik += ["", "Çelik standardıyla (A) gelen, gerçek listede olmayan satırlar: "
                + ", ".join(f"{z['kalem']} ({n(z['adet'])})" for z in s["fazla"].get("duz_a", s["fazla"]["kor_a"])) + "."]
    if s["adet_disi"]:
        cik += ["", "## Adet dışı farklar (sayıma girmez)", ""] + [f"- {x}" for x in s["adet_disi"]]
    cik += ["", "## Satır satır", "", "| Kalem (gerçek liste) | Gerçek | Kör B | Düzeltilmiş B | Kör A | Sınıf | Neden | Düzeltilmiş listede kalan |",
            "|---|---|---|---|---|---|---|---|"]
    grup = None
    for b in B:
        if b["grup"] != grup:
            grup = b["grup"]
            cik.append(f"| **{grup}** | | | | | | | |")
        isaret = lambda x: "" if b.get(x + "_ayni") or b.get(x) is None and x == "kor_a" else " ✗"
        cik.append(f"| {b['ad']} | {n(b['gercek'])} | {n(b['kor_b'])}{isaret('kor_b')} | {n(b.get('duz_b'))}{isaret('duz_b') if 'duz_b' in b else ''} | {n(b['kor_a'])}{isaret('kor_a')} "
                   f"| {b['sinif'] or ''} | {(b['neden'] or '') + (' Payı: ' + b['pay'] if b.get('pay') else '') + (' ' + b['not'] if b.get('not') else '')} | {b.get('kalan') or ''} |")
    return "\n".join(cik) + "\n"


if __name__ == "__main__":
    sys.exit(main())
