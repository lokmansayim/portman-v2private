#!/usr/bin/env python3
"""KT-03 (üçüncü kör test) kıyası: gerçek yükleme listesi ile dondurulan iki listemiz, satır satır.

Gerçek liste `sonuc/KT03_gercek_liste.json` (adsız, fiyatsız; 10 Ekim 2026'da, kendi listemiz dondurulduktan sonra açıldı). Listelerimiz:
    b   kural seti 0.17, projenin yapıldığı yöntemle (B: tavan omegası ve aşık); elektrik sayıları projenin paftasından
    a   aynı, çelik standardıyla (A: çatı ve tavan paneli): bu proje bugün sipariş edilse çıkacak liste
Gerçek liste yöntem B ile hazırlandığı için "aynı" B listesinde sayılır; A bilgi içindir. Üretim dosyası yoktu: çelik satırlarında adet
karşılaştırılır, kg motorun ortalamasıdır (bilgi).

Birim: gerçek listenin bir ya da birkaç satırı ile bizim listenin onlara denk satırları (`BIRIMLER`); adetler toplanarak karşılaştırılır. Her farkın
sınıfı (asıl nedeni) elle yazılmıştır (`kt03_farklar.json`) ve sayımla denetlenir: B'de farklı her birimin `sinif` ve `neden`i olmalı, aynı birimde
olmamalı. Sınıflar (KT-01 ve KT-02'deki gibi):
    girdi   girdi hatası: projenin belgesinde ya da modelinde vardı, yanlış ya da eksik okuduk
    kural   kural hatası: kuralımız yoktu, varsayımımız tutmadı ya da motor yanlış hesapladı
    karar   karar farkı: mevcut kural (Lokman'ın kararı ya da Excel motoru) o listedeki uygulamadan farklı
    elle    listenin elle yuvarlaması ya da kaba hesabı
    pafta   paftadan sayılan kalem (kör testte paftalardaki adetler girdi değildi)
Yalnız ilk ikisi bizim hatamızdır. Ayrıca: bizim listede olup gerçek listede olmayan satırlar (`fazla`), gerçek listede adedi yazılmayan satırlar.

"Ne olur" (`--ne-olur-b`, yalnız bilgi): düzeltilmiş B girdisinde kural soruları gerçek listedeki gibi cevaplanmış sayılır (`kt03_ne_olur.py`);
tutan hiçbir satırın bozulmadığı ve tutmaya başlayan her satırın kural satırı olduğu denetlenir.

Kullanım: python kt03_kiyas.py --kor-b sonuc/KT03_B_yukleme.json --kor-a sonuc/KT03_A_yukleme.json --duz-b sonuc/KT03_duzeltilmis_B_yukleme.json \\
              --duz-a sonuc/KT03_duzeltilmis_A_yukleme.json --sablon-b sonuc/KT03_duzeltilmis_B_2026.json --ne-olur-b sonuc/KT03_ne_olur_B_yukleme.json \\
              --md sonuc/KT03_kiyas.md --json sonuc/KT03_kiyas.json
(hepsi birden: bash kt03_kiyas_kos.sh <KT03_duzeltilmis.json> [python])
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

GRUP = {**GRUP_ADI, "DEPO GRUBU": "Depo", "MEKANİK TESİSAT GRUBU": "Mekanik tesisat"}

# (ad, gerçek liste satırları, bizim satırlar: kalem deseni ya da (kalem deseni, boyut deseni))
BIRIMLER: list[tuple[str, list[int], list]] = [
    ("Dış cephe duvar panelleri", [12], [r"^Dış cephe duvar panelleri$"]),
    ("İç cephe duvar panelleri", [13], [r"^İç cephe duvar panelleri$"]),
    ("Çatı makas panelleri (1,2 ve 0,8)", [14, 16], [r"^Çatı makas panelleri$"]),
    ("Çatı panelleri (1,2 ve 0,8)", [15, 17], [r"^Çatı paneli \(veranda", r"^Çatı panelleri"]),
    ("Baca panelleri", [18], [r"^Baca karkası$"]),
    ("Kolon ve kiriş panelleri", [19], [r"^Veranda dikmeleri", r"^Kirişler \(kiriş paneli\)$"]),
    ("Parça C profil 1,2", [20], [(r"^Boy C profil$", r"1,2")]),
    ("Parça C profil 0,8", [21], [(r"^Boy C profil$", r"0,8")]),
    ("Tavan omegası", [24], [r"^Tavan omegası"]),
    ("Köşebent", [25], [r"^Köşebent$"]),
    ("Aşık", [26], [r"^Aşık$"]),
    ("Alın sacı (veranda ve sundurma)", [27], [r"^Alın sacı"]),
    ("Saçak sacı", [28], [r"^Saçak sacı"]),
    ("Özel büküm saçak sacı", [29], [r"^Özel büküm saçak sacı"]),
    ("Saçak omegası (geniş, 140'lık duvar)", [30], [r"^Saçak omegası$"]),
    ("Dış cephe Boardex", [32], [r"^Dış cephe Boardex$"]),
    ("Veranda ve sundurma tavanı (Boardex)", [33], [r"^Veranda tavanı \(Boardex\)$"]),
    ("Tavan alçıpan beyaz", [35], [r"^Tavan alçıpan beyaz$"]),
    ("Tavan alçıpan yeşil", [36], [r"^Tavan alçıpan yeşil$"]),
    ("Duvar alçıpan beyaz", [37], [r"^Duvar alçıpan beyaz$"]),
    ("Duvar alçıpan yeşil", [38], [r"^Duvar alçıpan yeşil$"]),
    ("İç duvar OSB", [39], [r"^İç duvar OSB \d+ mm$"]),
    ("Duvar izolasyonu", [40], [r"^Duvar izolasyonu$"]),
    ("Sandviç panel (altı boy, toplam)", [42, 43, 44, 45, 46, 47], [r"^Sandviç panel$"]),
    ("Mahya sacı", [48], [r"^Metal kiremit mahyası$"]),
    ("Sandviç panel kapaması", [49], [r"^Sandviç panel kapaması$"]),
    ("Ters mahya (vadi sacı)", [50], [r"^Ters mahya$"]),
    ("Damlalık (duvar dibi ve baca; bizde özel mahya)", [51], [r"^Özel mahya", r"^Damlalık"]),
    ("Çatı çıkış kapağı", [52], [r"^Çatı çıkış kapağı"]),
    ("İzolasyon bandı (mahya, baca)", [53], [r"^Mahya bandı$"]),
    ("Çatı izolasyonu", [54], [r"^Çatı şiltesi|^Çatı izolasyonu"]),
    ("Metal dere", [56], [r"^Metal dere$"]),
    ("Dere kapağı", [57], [r"^Dere kapağı$"]),
    ("Dere iniş aparatı", [58], [r"^Dere iniş aparatı$"]),
    ("Dere iniş borusu", [59], [r"^Dere iniş borusu$"]),
    ("Açık dirsek", [60], [r"^Açık dirsek$"]),
    ("Kapalı dirsek", [61], [r"^Kapalı dirsek$"]),
    ("İniş kelepçesi", [62], [r"^İniş kelepçesi$"]),
    ("Dere kelepçesi", [63], [r"^Dere kelepçesi$"]),
    ("PVC pencere 150/130", [65], [(r"^PVC pencere$", r"^150/130$")]),
    ("PVC pencere 200/220 (sürgülü)", [66], [(r"^PVC pencere$", r"^200/220$")]),
    ("PVC pencere 100/70", [67], [(r"^PVC pencere$", r"^100/70$")]),
    ("PVC vasistas 50/50", [68], [(r"^PVC (pencere|vasistas)$", r"^50/50$")]),
    ("Kompozit çelik kapı", [70], [r"^Kompozit çelik kapı"]),
    ("Duylu armatür (tijli duy)", [72], [r"^Tijli duy$"]),
    ("Yuvarlak glop", [73], [r"^Yuvarlak glop$"]),
    ("Ampul", [74], [r"^Ampul$"]),
    ("NYM kablo (3 × 2,5)", [75], [r"^NYM kablo \(3"]),
    ("NYM kablo (2 × 1,5)", [76], [r"^NYM kablo \(2"]),
    ("Uydu kablo", [77], [r"^Uydu kablo$"]),
    ("Besleme kablosu", [78], [r"^Besleme kablosu"]),
    ("Tekli anahtar", [79], [r"^Tekli anahtar$"]),
    ("Çiftli anahtar", [80], [r"^Çiftli anahtar$"]),
    ("Tekli priz", [81], [r"^Tekli priz$"]),
    ("Çiftli priz", [82], [r"^Çiftli priz$"]),
    ("Uydu prizi", [83], [r"^Uydu prizi$"]),
    ("Buat kasa", [84], [r"^Buat kasa$"]),
    ("Sigorta kutusu", [85], [r"^Sigorta kutusu"]),
    ("W otomat (sigorta)", [86], [r"^W otomat"]),
    ("Kaçak akım rölesi", [87], [r"^Kaçak akım rölesi$"]),
    ("İzole bant", [88], [r"^İzole bant$"]),
    ("Zil", [89], [r"^Zil$"]),
    ("RYSB pul başlı", [91], [r"^RYSB"]),
    ("Alçıpan vidası", [92], [r"^Alçıpan vidası"]),
    ("OSB ve yalıpan vidası", [93], [r"^OSB ve yalıpan vidası"]),
    ("Pencere vidası (4,8 × 70)", [94], [r"^Pencere vidası"]),
    ("Trapez vida (5,5 × 25)", [95], [r"^Trapez vida \(5,5 × 25\)"]),
    ("Trapez vida (5,5 × 60)", [96], [r"^Trapez vida \(5,5 × 60\)"]),
    ("Trapez vida (5,5 × 110)", [97], [r"^Trapez vida \(5,5 × 110"]),
    ("Çelik dübel", [99], [r"^Çelik dübel"]),
    ("8'lik trapez uç", [100], [r"^8'lik trapez uç$"]),
    ("PH2 uç", [101], [r"^PH2 uç$"]),
    ("230'luk kesme taşı", [102], [r"^230'luk kesme taşı$"]),
    ("İnox taş", [103], [r"^İnox taş$"]),
    ("Acil müdahale kapağı", [104], [r"^Acil müdahale kapağı$"]),
    ("Poliüretan köpük", [105], [r"^Poliüretan köpük$"]),
    ("Dayson", [106], [r"^Dayson$"]),
    ("Mastik", [107], [r"^Silikonize mastik$"]),
    ("Baca borusu", [108], [r"^Baca borusu"]),
    ("Baca T'si", [109], [r"^Baca T"]),
    ("Baca kör tapa", [110], [r"^Baca kör tapa"]),
    ("Baca maşonu", [111], [r"^Baca maşon"]),
    ("Baca şapkası", [112], [r"^Baca şapka"]),
    ("Temiz su borusu", [114], [r"^Temiz su borusu$"]),
    ("Normal dirsek 20 mm", [115], [r"^Normal dirsek"]),
    ("Kulaklı dirsek 20 mm", [116], [r"^Kulaklı dirsek"]),
    ("Düz T 20 mm", [117], [r"^Düz T"]),
    ("Maşon 20 mm", [118], [r"^Maşon"]),
    ("Taharet musluğu 20 mm", [119], [r"^Taharet musluğu"]),
    ("İç dişli T 20 mm", [120], [r"^İç dişli T"]),
    ("Atlama parçası", [121], [r"^Atlama parçası"]),
    ("Dış cephe boyası", [123], [r"^Dış cephe boyası$"]),
    ("İç cephe boyası", [124], [r"^İç cephe boyası$"]),
    ("Tavan boyası", [125], [r"^Tavan boyası$"]),
    ("Astar", [126], [r"^Astar$"]),
]
ADETSIZ = {69: "Melamin kapı (alıcıya ait)"}
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
    ap.add_argument("--ne-olur-b", type=Path, help="düzeltilmiş B, kural soruları listedeki gibi cevaplanırsa (kt03_ne_olur.py; yalnız bilgi)")
    ap.add_argument("--gercek", type=Path, default=BURADA / "sonuc" / "KT03_gercek_liste.json")
    ap.add_argument("--farklar", type=Path, default=BURADA / "kt03_farklar.json")
    ap.add_argument("--ek-notlar", type=Path, help="cevaplardan sonraki notlar: birim alanları, giriş, başlık, etiketler ve adet dışı farklar `--farklar`ın "
                                                    "üstüne yazılır; kör listenin sınıfları değişmez")
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
    E = oku(a.ek_notlar) if a.ek_notlar else None
    if E:
        for ad, alanlar in E.get("birimler", {}).items():
            if "sinif" in alanlar or "neden" in alanlar:
                sorun.append(f"ek notlar kör listenin sınıfını ya da nedenini değiştiremez: {ad}")
            F["birimler"].setdefault(ad, {}).update(alanlar)
        F.update({x: E[x] for x in ("giris", "adet_disi") if x in E})
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
        b = {"ad": ad, "grup": GRUP[gg[0]["grup"]], "gercek_satirlar": satirlar, "gercek_kalemler": [s["kalem"] for s in gg], "gercek_boyut": [s["boyut"] for s in gg],
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
            if b["pay"] and b["kor_b"] == b["duz_b"] and not b["pay"].startswith(("kural", "karar")):
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
    yeni_fazla = sorted({s["ic_ad"] for s in Z.get("duz_b", [])} - {s["ic_ad"] for s in Z["kor_b"]})
    if yeni_fazla:
        sorun.append("düzeltilmiş B listesinde, kör listede olmayan fazla satır var: " + ", ".join(yeni_fazla))
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    ozet = {x: {"gercek_satir": satir(B), "ayni": satir([b for b in B if b[x + "_ayni"]])} for x in L}
    sinif_say = {k: satir([b for b in B if b["sinif"] == k]) for k in SINIF}
    kalan_say = {k: satir([b for b in B if b["kalan"] and b["kalan"].split(":")[0] == k]) for k in SINIF} if "duz_b" in L else None
    ne_olur = None
    if "ne_olur_b" in L and "duz_b" in L:
        # yalnız kural sorularının etkisi: adedi tutmaya başlayan satır kural satırı ya da payı kural olan satır olmalı; tutan hiçbir satır bozulmamalı
        ne_olur = [{"ad": b["ad"], "gercek": b["gercek"], "duz_b": b["duz_b"], "ne_olur_b": b["ne_olur_b"], "ayni": b["ne_olur_b_ayni"]}
                   for b in B if b["ne_olur_b"] != b["duz_b"]]
        kural_payli = {b["ad"] for b in B if b["sinif"] == "kural" or (b.get("pay") or "").startswith("kural") or (b.get("kalan") or "").startswith("kural")}
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
    if E:
        sonuc.update({"baslik": E.get("baslik"), "etiketler": E.get("etiketler", {})})
    print(f"gerçek listenin adetli satırı: {satir(B)} | birim: {len(B)} | " + " · ".join(f"{x} {ozet[x]['ayni']}" for x in L))
    print(f"  kör B'de farklı {satir(B) - ozet['kor_b']['ayni']} satır: {sinif_say} · bizim hatamız {sonuc['bizim_hatamiz']}")
    if kalan_say:
        print(f"  düzeltilmiş B'de farklı {satir(B) - ozet['duz_b']['ayni']} satır: {kalan_say}")
    if ne_olur is not None:
        print("  ne olur (kural soruları listedeki gibi): " + "; ".join(f"{x['ad']} {x['duz_b']} → {x['ne_olur_b']}{' (aynı)' if x['ayni'] else ''}" for x in ne_olur))
    print(f"  çelik: gerçek {toplam_g['adet']} adet {toplam_g['kg']} kg · " + " · ".join(f"{x} {sonuc['celik'][x]}" for x in L))
    print(f"  kör B'de olup gerçek listede olmayan: {[(s['kalem'], s['adet']) for s in Z['kor_b']]}")
    for s in sorun:
        print("  SORUN:", s)
    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.md:
        a.md.write_text(md(sonuc, L), encoding="utf-8")
    return 1 if sorun else 0


ETIKET_VARSAYILAN = {"duz_b": "Düzeltilmiş (B)", "duz_b_aciklama": "yalnız girdi hatalarımız düzeltildi (makas adedi, veranda ve sundurma çatısının saçağı); kurallar aynı",
                     "duz_a": "Düzeltilmiş (A)", "duz_a_aciklama": "bilgi", "duz_kisa": "düzeltilmiş", "duz_sutun": "Düzeltilmiş B",
                     "kalan_basligi": "Düzeltilmiş listede (B) farklı kalan", "kalan_sutun": "Düzeltilmiş listede kalan",
                     "kaynak_notu": "Sınıflar ve nedenler `kt03_farklar.json`dan."}


def md(s: dict, L: dict) -> str:
    B, o = s["birimler"], s["ozet"]
    toplam = o["kor_b"]["gercek_satir"]
    et = {**ETIKET_VARSAYILAN, **(s.get("etiketler") or {})}
    cik = [f"# {s.get('baslik') or 'KT-03 · kıyas'}", "", s["giris"], "", f"Tablo `kt03_kiyas.py` ile üretilir; elle düzeltilmez. {et['kaynak_notu']}", "",
           "| Liste | Aynı satır | Ne demek |", "|---|---|---|",
           f"| Kör liste, yapıldığı yöntemle (B) | {o['kor_b']['ayni']} / {toplam} | dondurulan liste (commit 1f7ba6c); kural seti 0.17; elektrik sayıları paftadan |"]
    if "duz_b" in o:
        cik.append(f"| {et['duz_b']} | {o['duz_b']['ayni']} / {toplam} | {et['duz_b_aciklama']} |")
    if "sablon_b" in o:
        cik.append(f"| Düzeltilmiş + Eylül 2026 uygulaması (B) | {o['sablon_b']['ayni']} / {toplam} | yalnız bilgi: `--sablon 2026` katmanı (KT-01'in Eylül 2026 listesinin uygulaması; Lokman 7 Ekim'de cevapladı, varsayılan hesapta değil) |")
    if "ne_olur_b" in o:
        cik.append(f"| Kural soruları listedeki gibi cevaplanırsa (B) | {o['ne_olur_b']['ayni']} / {toplam} | yalnız bilgi (`kt03_ne_olur.py`): çatı panelli veranda ve sundurmanın "
                   "kenarları listedeki gibi (dere, iniş ve alın sacı var, Boardex şeridi yok, tavanı saçağıyla; özel büküm saçak sacı motorda yok); kırma uçlarının çatı panelleri paftadaki adetle |")
    cik.append(f"| Kör liste, çelik standardıyla (A) | {o['kor_a']['ayni']} / {toplam} | çatı ve tavan paneli: bu proje bugün sipariş edilse çıkacak liste (bilgi) |")
    if "duz_a" in o:
        cik.append(f"| {et['duz_a']} | {o['duz_a']['ayni']} / {toplam} | {et['duz_a_aciklama']} |")
    cik += ["", f"Kör listede (B) farklı {toplam - o['kor_b']['ayni']} satırın asıl nedeni:", "", "| Sınıf | Satır | Anlamı |", "|---|---|---|"]
    cik += [f"| {k} | {v} | {SINIF[k]} |" for k, v in s["siniflar"].items()]
    cik += ["", f"Bizim hatamız (girdi + kural): {s['bizim_hatamiz']} satır; ayrıca kör listede gerçek listede olmayan {len(s['fazla']['kor_b'])} satır (aşağıda)."]
    if s["kalan_siniflar"]:
        cik += ["", f"{et['kalan_basligi']} {toplam - o['duz_b']['ayni']} satır:", "", "| Tür | Satır |", "|---|---|"]
        cik += [f"| {k} | {v} |" for k, v in s["kalan_siniflar"].items() if v]
    if s.get("ne_olur"):
        cik += ["", "Kural soruları listedeki gibi cevaplanırsa (yalnız bilgi) değişen satırlar: "
                + "; ".join(f"{x['ad']} {n(x['duz_b'])} → {n(x['ne_olur_b'])}" + (" (aynı)" if x["ayni"] else f" (gerçek {n(x['gercek'])})") for x in s["ne_olur"])
                + ". Tutan hiçbir satır bozulmadı (denetlenir)."]
    c = s["celik"]
    ETIKET = {"kor_b": "kör B", "kor_a": "kör A", "duz_b": f"{et['duz_kisa']} B", "duz_a": f"{et['duz_kisa']} A", "sablon_b": "+ Eylül 2026 (B)", "ne_olur_b": "ne olur (B)"}
    cik += ["", "Çelik (adet, kg): gerçek liste " + f"{c['gercek']['adet']} · {n(round(c['gercek']['kg'], 1))}"
            + "".join(f" — {ETIKET[x]} {c[x]['adet']} · {n(round(c[x]['kg'], 1))}" for x in L if x in c)
            + ". Üretim dosyası olmadığı için bizim kg motorun proje ortalamalarıdır; A'da tavan ve çatı panelleri eklenir.", "",
            "Gerçek listede adedi yazılmayan satırlar (bizim listede de yok): " + ", ".join(s["adetsiz_gercek_satirlar"]) + ".", "",
            "## Kör listede (B) olup gerçek listede olmayan satırlar", "", "| Kalem | Boyut | Adet | Sınıf | Neden |", "|---|---|---|---|---|"]
    cik += [f"| {z['kalem']} | {z['boyut']} | {n(z['adet'])} | {z.get('sinif') or ''} | {z.get('neden') or ''} |" for z in s["fazla"]["kor_b"]]
    if s["fazla"].get("duz_a") is not None or s["fazla"].get("kor_a"):
        cik += ["", "Çelik standardıyla (A) gelen, gerçek listede olmayan satırlar: "
                + ", ".join(f"{z['kalem']} ({n(z['adet'])})" for z in s["fazla"].get("duz_a", s["fazla"]["kor_a"])) + "."]
    if s["adet_disi"]:
        cik += ["", "## Adet dışı farklar (sayıma girmez)", ""] + [f"- {x}" for x in s["adet_disi"]]
    cik += ["", "## Satır satır", "", f"| Kalem (gerçek liste) | Gerçek | Kör B | {et['duz_sutun']} | Kör A | Sınıf | Neden | {et['kalan_sutun']} |",
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
