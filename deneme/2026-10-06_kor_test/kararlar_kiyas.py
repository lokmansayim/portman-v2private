#!/usr/bin/env python3
"""KT-01: Lokman'ın 7 Ekim 2026 kararlarından sonra durum. Gerçek liste ile güncel kural setinin verdiği iki liste, satır satır.

    onceki  7 Ekim 03:46 kıyasındaki listeler (`sonuc/KT01_kiyas.json`: düzeltilmiş ve + pafta sütunları; kural seti 0.12)
    b       güncel kural seti, projenin yapıldığı yöntemle (B: tavan omegası ve aşık); elektrik sayıları projenin paftasından
    a       güncel kural seti, çelik standardıyla (A: çatı ve tavan paneli): bu proje bugün sipariş edilse çıkacak liste

Gerçek liste yöntem B ile hazırlandığı için "aynı" yalnız b listesinde sayılır. Birimler `kiyas.py`deki eşlemedir (`BIRIMLER`).
Açıklamalar elle yazılmıştır (`kararlar_notlari.json`) ve sayımla denetlenir: adedi 03:46'daki düzeltilmiş listeden farklı olan her birimin `karar`ı,
gerçek listeden farklı kalan her birimin `fark`ı olmalı; değişmeyen birimde `karar`, tutan birimde `fark` olmamalı. `fark` türüyle başlar:
karar · yöntem · elle · ölçü · soru. Çıkış kodu: denetim sorunu varsa 1.

Kullanım:
    python kararlar_kiyas.py --b sonuc/KT01_kararlar_B_yukleme.json --a sonuc/KT01_kararlar_A_yukleme.json --md sonuc/KT01_kararlar_kiyas.md --json sonuc/KT01_kararlar_kiyas.json
    (hepsi birden: bash kararlar_kos.sh <tanım.json> [python])
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import kiyas
import kurallar_oku

BURADA = Path(__file__).resolve().parent
PAFTADAN = "Karar değil:"       # `karar` notu böyle başlıyorsa adet bir karardan değil, elektrik sayılarının paftadan alınmasından değişmiştir
INIS_BIRIMLERI = ("Dere iniş borusu", "Dere iniş aparatı", "Açık dirsek", "Kapalı dirsek", "İniş kelepçesi")      # iniş sayısına bağlı birimler (eşik 7 Ekim'de öneriydi; 8 Ekim'de onaylandı)
FARK_TURU = {"karar": "Lokman'ın kararı o listeden farklı", "yöntem": "liste omega ve aşıklı yöntemle hazırlanmış; çelikte artık yok",
             "elle": "listenin elle hesabı, yuvarlaması ya da elle dizilimi", "ölçü": "ölçünün alındığı yüz (karar: bizdeki)", "soru": "kural bekliyor"}


def n(v) -> str:
    return "—" if v is None else (f"{v:,}".replace(",", " ") if isinstance(v, int) else str(v).replace(".", ","))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--a", type=Path, required=True)
    ap.add_argument("--gercek", type=Path, default=BURADA / "sonuc" / "KT01_gercek_liste.json")
    ap.add_argument("--onceki", type=Path, default=BURADA / "sonuc" / "KT01_kiyas.json")
    ap.add_argument("--notlar", type=Path, default=BURADA / "kararlar_notlari.json")
    ap.add_argument("--md", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    oku = lambda p: json.loads(p.read_text(encoding="utf-8"))
    L = {"b": oku(a.b), "a": oku(a.a)}
    sorun = []
    if L["b"]["yontem"] != "omega_asik" or L["a"]["yontem"] != "panel":
        sorun.append("listeler yanlış yuvada: --b yöntem B (omega_asik), --a yöntem A (panel) olmalı")
    for x in ("a", "b"):
        if L[x].get("sablon"):
            sorun.append(f"{x} listesi şablon katmanıyla üretilmiş; güncel kural setiyle, katmansız olmalı")
        if (L[x].get("ara") or {}).get("elektrik_kaynagi") != "pafta":
            sorun.append(f"{x} listesinde elektrik sayıları paftadan değil")
    B = kiyas.karsilastir(oku(a.gercek), L)
    onceki = {b["ad"]: b for b in oku(a.onceki)["birimler"]}
    notlar_dosyasi = oku(a.notlar)
    notlar = notlar_dosyasi["birimler"]
    satir = lambda bb: sum(len(b["gercek_satirlar"]) for b in bb)
    for b in B:
        o, nt = onceki[b["ad"]], notlar.get(b["ad"], {})
        b["duzeltilmis"], b["duzeltilmis_ayni"], b["onceki_pafta"] = o["duzeltilmis"], o["duzeltilmis_ayni"], o["pafta"]
        b["karar"], b["fark"] = nt.get("karar"), nt.get("fark")
        b["fark_turu"] = b["fark"].split(":")[0] if b["fark"] else None
        b["karar_turu"] = None if not b["karar"] else ("pafta" if b["karar"].startswith(PAFTADAN) else "karar")
        if (b["b"] != b["duzeltilmis"]) != bool(b["karar"]):
            sorun.append(f"{b['ad']}: düzeltilmiş {b['duzeltilmis']} → b {b['b']}; `karar` " + ("yazılmamış" if not b["karar"] else "yazılmış ama adet değişmemiş"))
        if (not b["b_ayni"]) != bool(b["fark"]):
            sorun.append(f"{b['ad']}: gerçek {b['gercek']}, b {b['b']}; `fark` " + ("yazılmamış" if not b["fark"] else "yazılmış ama adet aynı"))
        if b["fark"] and b["fark_turu"] not in FARK_TURU:
            sorun.append(f"{b['ad']}: `fark` türüyle başlamıyor ({', '.join(FARK_TURU)})")
    for ad in set(notlar) - {b["ad"] for b in B}:
        sorun.append(f"notlarda bilinmeyen birim: {ad}")
    # birimlere girmeyen satırlar: A listesinde yöntemin kendi satırları olur; B listesinde olmamalı
    def disarida(liste):
        cik = []
        for s in liste["satirlar"]:
            if s["kalem"].startswith("Toplam ("):
                continue
            if not any(re.search(d if isinstance(d, str) else d[0], s["kalem"]) and (isinstance(d, str) or re.search(d[1], s["boyut"])) for _, _, ds in kiyas.BIRIMLER for d in ds):
                cik.append(s)
        return cik
    # Lokman'ın yeni bir kararıyla gelen, gerçek listede olmayan satırlar (0.18: müştemilatın panel çatısının kenarları; Lokman, 10 Ekim 2026):
    # notlarda `listede_olmayan` altında nedeniyle yazılı olmalı; yazılı değilse sorun
    listede_olmayan = notlar_dosyasi.get("listede_olmayan") or {}
    b_ek = []
    for s in disarida(L["b"]):
        if s["kalem"] in listede_olmayan:
            b_ek.append(s)
        else:
            sorun.append(f"b listesinde hiçbir birime girmeyen satır: {s['kalem']} ({s['adet']})")
    for ad in sorted(set(listede_olmayan) - {s["kalem"] for s in b_ek}):
        sorun.append(f"notlarda gerçek listede olmayan satır olarak yazılı ama b listesinde yok: {ad}")
    for s in b_ek:
        if listede_olmayan[s["kalem"]].split(":")[0] not in FARK_TURU:
            sorun.append(f"{s['kalem']}: `listede_olmayan` nedeni türüyle başlamıyor ({', '.join(FARK_TURU)})")
    a_ek = disarida(L["a"])
    ozet = {x: {"gercek_satir": satir(B), "ayni": satir([b for b in B if b[x + "_ayni"]])} for x in ("b", "a")}
    onceki_ozet = oku(a.onceki)["ozet"]
    fark_sayimi = {t: satir([b for b in B if b["fark_turu"] == t]) for t in FARK_TURU}
    degisen = satir([b for b in B if b["karar"]])
    # 03:46'da tutmayıp şimdi tutan satırlar: kararlardan (ayrıca iniş kuralından) ve pafta sayımından; önce tutup şimdi tutmayanlar
    yeni_tutan = [b for b in B if not b["duzeltilmis_ayni"] and b["b_ayni"]]
    kazanc = {"toplam": satir(yeni_tutan), "pafta": satir([b for b in yeni_tutan if b["karar_turu"] == "pafta"]),
              "inis": satir([b for b in yeni_tutan if b["ad"] in INIS_BIRIMLERI]), "bozulan": satir([b for b in B if b["duzeltilmis_ayni"] and not b["b_ayni"]])}
    for ad in INIS_BIRIMLERI:
        if not any(b["ad"] == ad for b in B):
            sorun.append(f"iniş birimi kıyasta yok: {ad}")
    kg = lambda liste: next((s["kg"] for s in liste["satirlar"] if s["kalem"].startswith("Toplam (")), None)
    inis_kurali = kurallar_oku.oku().get("inis") or {}
    inis_onayli = inis_kurali.get("durum") == "lokman" and (inis_kurali.get("deger") or {}).get("olcu") == "dere"
    # "Damlalık" birimi özel mahya satırını da alır (8 Ekim 2026: çatının duvara dayandığı kenara özel mahya). Satırda birleşim boyu da varsa
    # (ana bina ile veranda çıkıntısı; bu projede yok) adet o kenarın adedi değildir: karşılaştırma yanıltır.
    for x in ("a", "b"):
        if any(s["kalem"] == "Özel mahya (geniş)" and "birleşim" in (s.get("formul") or "") for s in L[x]["satirlar"]):
            sorun.append(f"{x} listesinde özel mahya satırında birleşim boyu da var; 'Damlalık (bina ve müştemilat)' birimiyle karşılaştırılamaz")
    sonuc = {"ozet": ozet, "onceki": {x: onceki_ozet[x]["ayni"] for x in ("kor", "duzeltilmis", "sablon", "pafta")}, "fark_turleri": fark_sayimi,
             "karardan_degisen_satir": degisen, "degisen": {"karar": satir([b for b in B if b["karar_turu"] == "karar"]), "pafta": satir([b for b in B if b["karar_turu"] == "pafta"])},
             "yeni_tutan": kazanc, "celik_kg": {"gercek": oku(a.onceki)["celik_kg"]["gercek"], "b": kg(L["b"]), "a": kg(L["a"])},
             "a_listesinde_gercek_listede_olmayan": [{"kalem": s["kalem"], **({"liste_adi": s["liste_adi"]} if s.get("liste_adi") else {}), "boyut": s["boyut"], "adet": s["adet"],
                                                      **({"olcu": s["olcu"], "birim": s["birim"]} if s["adet"] is None and s["olcu"] is not None and s["durum"] == "soru" else {}),
                                                      "kg": s["kg"], "durum": s["durum"]} for s in a_ek],
             "denetim_sorunlari": sorun, "birimler": B}
    if b_ek:
        sonuc["b_listesinde_gercek_listede_olmayan"] = [{"kalem": s["kalem"], "boyut": s["boyut"], "adet": s["adet"], "durum": s["durum"],
                                                         "neden": listede_olmayan[s["kalem"]]} for s in b_ek]
    if inis_onayli:      # 8 Ekim 2026: iniş eşiği onaylandı; sayfa "eşiği öneri" demesin
        sonuc["inis_onayli"] = True
    print(f"gerçek listenin adetli satırı: {satir(B)} | birim: {len(B)}")
    print(f"  önceki (7 Ekim 03:46): kör {sonuc['onceki']['kor']} · düzeltilmiş {sonuc['onceki']['duzeltilmis']} · + Eylül 2026 {sonuc['onceki']['sablon']} · + pafta {sonuc['onceki']['pafta']}")
    print(f"  kararlardan sonra, aynı yöntemle (B): aynı {ozet['b']['ayni']} / {ozet['b']['gercek_satir']} | çelik standardıyla (A): {ozet['a']['ayni']}")
    print(f"  farklı kalan {satir(B) - ozet['b']['ayni']} satırın türü: {fark_sayimi} | toplam {sum(fark_sayimi.values())}")
    print(f"  kararlarla ya da pafta sayımıyla adedi değişen satır: {degisen} | yeni tutan {kazanc['toplam']} (pafta {kazanc['pafta']}, iniş {kazanc['inis']}); bozulan {kazanc['bozulan']}")
    for s in sorun:
        print("  SORUN:", s)
    if a.json:
        a.json.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.md:
        cik = ["# KT-01 · kararlardan sonra durum", "",
               (notlar_dosyasi.get("giris") or "Lokman'ın 7 Ekim 2026 07:45 cevapları ve 08:02 düzeltmeleri işlendikten sonra, gerçek listenin adetli her satırı güncel kural setinin verdiği iki listeyle.") + " "
               "Tablo `kararlar_kiyas.py` ile üretilir; elle düzeltilmez. Açıklamalar `kararlar_notlari.json`dan.", "",
               "| Liste | Aynı satır | Ne demek |", "|---|---|---|",
               f"| Düzeltilmiş (7 Ekim 03:46) | {sonuc['onceki']['duzeltilmis']} / {satir(B)} | kararlardan önce: yalnız bizim hatalarımız düzeltilmişti |",
               f"| Kararlardan sonra, aynı yöntemle (B) | {ozet['b']['ayni']} / {satir(B)} | güncel kurallar; proje yapıldığı gibi tavan omegası ve aşıkla; elektrik sayıları paftadan |",
               f"| Kararlardan sonra, çelik standardıyla (A) | {ozet['a']['ayni']} / {satir(B)} | güncel kurallar; çatı ve tavan paneliyle: bu proje bugün sipariş edilse çıkacak liste |", "",
               f"Aynı yöntemle farklı kalan {satir(B) - ozet['b']['ayni']} satır:", "", "| Tür | Satır | Anlamı |", "|---|---|---|"]
        cik += [f"| {t} | {fark_sayimi[t]} | {FARK_TURU[t]} |" for t in FARK_TURU]
        cik += ["", f"Çelik ağırlığı (kg): gerçek liste {n(round(sonuc['celik_kg']['gercek']))} · B {n(round(sonuc['celik_kg']['b']))} · "
                f"A {n(round(sonuc['celik_kg']['a']))} (A'da tavan ve çatı panelleri eklenir).", "",
                "## Çelik standardıyla (A) gelen, gerçek listede olmayan satırlar", "", "| Kalem | Boyut | Adet | kg | Durum |", "|---|---|---|---|---|"]
        cik += [f"| {s.get('liste_adi') or s['kalem']} | {s['boyut']} | "
                + (n(s['adet']) if s['adet'] is not None or s['olcu'] is None or s['durum'] != "soru" else f"— ({n(s['olcu'])} {s['birim']})")
                + f" | {'' if s['kg'] is None else n(round(s['kg']))} | {s['durum']} |" for s in a_ek]
        if b_ek:
            cik += ["", "## Kararlardan sonra (B) gelen, gerçek listede olmayan satırlar", "", "| Kalem | Boyut | Adet | Durum | Neden |", "|---|---|---|---|---|"]
            cik += [f"| {s['kalem']} | {s['boyut']} | {n(s['adet'])} | {s['durum']} | {listede_olmayan[s['kalem']]} |" for s in b_ek]
        cik += ["", "## Satır satır", "",
                "| Kalem (gerçek liste) | Gerçek | Düzeltilmiş (03:46) | Kararlardan sonra (B) | Çelik standardı (A) | Değişikliği doğuran karar | Hâlâ farklıysa nedeni |",
                "|---|---|---|---|---|---|---|"]
        grup = None
        for b in B:
            if b["grup"] != grup:
                grup = b["grup"]
                cik.append(f"| **{grup}** | | | | | | |")
            isaret = lambda x: "" if b[x + "_ayni"] else " ✗"
            cik.append(f"| {b['ad']} | {n(b['gercek'])} | {n(b['duzeltilmis'])} | {n(b['b'])}{isaret('b')} | {n(b['a'])}{isaret('a') if b['a'] is not None else ''} "
                       f"| {b['karar'] or ''} | {b['fark'] or ''} |")
        a.md.write_text("\n".join(cik) + "\n", encoding="utf-8")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
