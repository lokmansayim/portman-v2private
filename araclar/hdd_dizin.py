"""Disk arşivinin (Portman_HDD_Projeler) mührü ve kodlu dizini (İE-43, D-99).

Ham dosyalar Drive'da ve Mac'te durur; depoya yalnız adsız mühür ve dizin girer (Lokman, 15 Kasım 2026 05:37:53 UTC,
karar kartı "Drive'da, depoya dizin ve kart"). Araç yalnız standart kütüphaneyle çalışır: Mac'te, arşiv klasörünün
yanında koşar. Arşivin dosyalarına yazmaz, taşımaz, silmez; yazdığı yerler `--depo` ve `<kök>/_portman_analiz/`.

  python3 hdd_dizin.py kur <kök> --depo <depo kökü> [--sure 150]
      Her alınan dosyanın SHA-256'sını hesaplar, kopyalayanın listesiyle (`_kaynak_listesi.csv`) kıyaslar. Hepsi aynıysa
      depoya `testler/hdd/muhur.csv` ve `testler/hdd/dizin.json`, Mac'e `<kök>/_portman_analiz/kod_esleme.csv` yazar.
      Süre biterse kaldığı yeri önbelleğe yazar ve 2 ile çıkar; yeniden koşulunca devam eder. Fark varsa 1, hiçbir şey yazmaz.

  python3 hdd_dizin.py dogrula <kök> --depo <depo kökü> --esleme <kod_esleme.csv> --onbellek <dosya> [--sure 150]
      Bir kopyayı (ör. Drive'daki) mühürle kıyaslar. Önbellek kopyanın dışında tutulur ki kopyayla taşınan önbellek
      sayılmasın. 0 hepsi aynı, 1 fark ya da eksik, 2 süre bitti.

Kodlar: proje klasörleri adlarının düz sıralamasıyla (NFC, Python `sorted`) HD-001…; proje içinde dosyalar göreli yolun
düz sıralamasıyla 1, 2, … Depodaki dosyalarda klasör adı, dosya adı, kişi ya da bayi adı yoktur.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import sys
import time
import unicodedata

LISTE = "_kaynak_listesi.csv"
PROJELER = "_projeler.csv"
ANALIZ = "_portman_analiz"
MUHUR = os.path.join("testler", "hdd", "muhur.csv")
DIZIN = os.path.join("testler", "hdd", "dizin.json")
MUHUR_BASLIK = ["kod", "sira", "uzanti", "bayt", "tarih", "sha256"]

# Kaynak bölümü: Elements diskindeki ana kaynak klasörün üst klasörlerinden, sabit sözcüklerle (ilk eşleşen kazanır).
# Ad yazılmaz; yalnız bölüm türü.
BOLUMLER = [
    ("celik", ("ÇELIK", "CELIK")),
    ("prefabrik", ("PREFABR",)),
    ("kampanyali", ("KAMPANYALI",)),
    ("sevk", ("SEVK",)),
    ("revize", ("REVIZE",)),
    ("sozlesme", ("SÖZLEŞME", "SOZLESME")),
    ("teklif", ("TEKLIF",)),
    ("cizim", ("ÇIZIM", "CIZIM")),
    ("sunum", ("SUNUM", "KAT PLAN")),
]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def buyuk(s: str) -> str:
    """Türkçe büyük harf: İ ve I aynı sayılır."""
    return nfc(s).upper().replace("İ", "I")


def kaynak_bolumu(ana_kaynak: str) -> str:
    ust = buyuk("/".join(nfc(ana_kaynak).split("/")[:-1]))
    for ad, sozler in BOLUMLER:
        if any(s in ust for s in sozler):
            return ad
    return "diger"


def iso_tarih(s: str) -> str:
    g, a, y = s.strip().split(".")
    return f"{int(y):04d}-{int(a):02d}-{int(g):02d}"


def uzanti(yol: str) -> str:
    ad = yol.rsplit("/", 1)[-1]
    return ad.rsplit(".", 1)[-1].lower() if "." in ad.strip(".") else ""


def oku_liste(kok: str) -> list[dict]:
    with open(os.path.join(kok, LISTE), encoding="utf-8-sig", newline="") as f:
        satirlar = list(csv.reader(f, delimiter=";"))[1:]
    return [
        {"klasor": s[0], "dosya": s[1], "tarih": s[4], "durum": s[5], "sha256": s[6].strip().lower()}
        for s in satirlar if s
    ]


def oku_projeler(kok: str) -> dict[str, str]:
    yol = os.path.join(kok, PROJELER)
    if not os.path.exists(yol):
        return {}
    with open(yol, encoding="utf-8-sig", newline="") as f:
        satirlar = list(csv.reader(f, delimiter=";"))[1:]
    return {nfc(s[0]): s[9] for s in satirlar if s and len(s) > 9}


def kodla(alinan: list[dict]) -> list[dict]:
    """Alınan dosyalara kod ve sıra verir (adların düz sıralaması)."""
    klasorler = sorted({nfc(d["klasor"]) for d in alinan})
    kod = {k: f"HD-{i:03d}" for i, k in enumerate(klasorler, 1)}
    gruplar: dict[str, list[dict]] = collections.defaultdict(list)
    for d in alinan:
        gruplar[nfc(d["klasor"])].append(d)
    sonuc = []
    for k in klasorler:
        for i, d in enumerate(sorted(gruplar[k], key=lambda x: nfc(x["dosya"])), 1):
            sonuc.append(dict(d, kod=kod[k], sira=i))
    return sonuc


def oku_onbellek(yol: str) -> dict[str, tuple[int, int, str]]:
    if not os.path.exists(yol):
        return {}
    kayit = {}
    with open(yol, encoding="utf-8") as f:
        for satir in f.read().split("\n"):
            p = satir.split("\t")
            if len(p) == 4 and len(p[3]) == 64:
                kayit[p[0]] = (int(p[1]), int(p[2]), p[3])
    return kayit


def ozetle(kok: str, gorelikler: list[str], onbellek_yolu: str, sure: float) -> tuple[dict[str, tuple[int, str]], bool]:
    """Dosyaların bayt ve SHA-256'sı; önbellekle kaldığı yerden devam eder. (sonuç, bitti mi)"""
    onbellek = oku_onbellek(onbellek_yolu)
    os.makedirs(os.path.dirname(os.path.abspath(onbellek_yolu)), exist_ok=True)
    # yarım kalmış son satırı at
    with open(onbellek_yolu, "w", encoding="utf-8") as f:
        for g, (b, m, h) in onbellek.items():
            f.write(f"{g}\t{b}\t{m}\t{h}\n")
    sonuc: dict[str, tuple[int, str]] = {}
    bas = time.time()
    with open(onbellek_yolu, "a", encoding="utf-8") as f:
        for g in gorelikler:
            p = os.path.join(kok, g)
            if not os.path.exists(p):
                continue
            st = os.stat(p)
            eski = onbellek.get(g)
            if eski and eski[0] == st.st_size and eski[1] == st.st_mtime_ns:
                sonuc[g] = (st.st_size, eski[2])
                continue
            if time.time() - bas > sure:
                return sonuc, False
            h = hashlib.sha256()
            with open(p, "rb") as d:
                for parca in iter(lambda: d.read(1 << 20), b""):
                    h.update(parca)
            sonuc[g] = (st.st_size, h.hexdigest())
            f.write(f"{g}\t{st.st_size}\t{st.st_mtime_ns}\t{sonuc[g][1]}\n")
            f.flush()
    return sonuc, True


def yaz_json(yol: str, veri: dict) -> None:
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
        f.write("\n")


def kur(kok: str, depo: str, sure: float, onbellek: str | None = None) -> int:
    liste = oku_liste(kok)
    alinan = [d for d in liste if d["durum"].startswith("alındı")]
    kayitlar = kodla(alinan)
    gorelikler = [d["klasor"] + "/" + d["dosya"] for d in kayitlar]
    onbellek = onbellek or os.path.join(kok, ANALIZ, "sha_onbellek.tsv")
    ozet, bitti = ozetle(kok, gorelikler, onbellek, sure)
    if not bitti:
        print(f"süre bitti: {len(ozet)} / {len(kayitlar)} dosya; yeniden koşun, kaldığı yerden devam eder")
        return 2
    eksik = [g for g in gorelikler if g not in ozet]
    farkli = [g for d, g in zip(kayitlar, gorelikler) if g in ozet and ozet[g][1] != d["sha256"]]
    if eksik or farkli:
        print(f"MÜHÜR TUTMADI: {len(eksik)} dosya yok, {len(farkli)} dosyanın SHA-256'sı listeden farklı; hiçbir şey yazılmadı")
        return 1

    projeler_kaynak = oku_projeler(kok)
    muhur_yolu = os.path.join(depo, MUHUR)
    os.makedirs(os.path.dirname(muhur_yolu), exist_ok=True)
    with open(muhur_yolu, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(MUHUR_BASLIK)
        for d, g in zip(kayitlar, gorelikler):
            w.writerow([d["kod"], d["sira"], uzanti(d["dosya"]), ozet[g][0], iso_tarih(d["tarih"]), d["sha256"]])

    projeler: dict[str, dict] = {}
    for d, g in zip(kayitlar, gorelikler):
        p = projeler.setdefault(d["kod"], {
            "dosya": 0, "bayt": 0, "uzantilar": collections.Counter(), "tarih_ilk": None, "tarih_son": None,
            "kaynak_bolumu": kaynak_bolumu(projeler_kaynak.get(nfc(d["klasor"]), "")),
            "revize": "REVIZE" in buyuk(d["klasor"]),
        })
        t = iso_tarih(d["tarih"])
        p["dosya"] += 1
        p["bayt"] += ozet[g][0]
        p["uzantilar"][uzanti(d["dosya"])] += 1
        p["tarih_ilk"] = min(filter(None, [p["tarih_ilk"], t]))
        p["tarih_son"] = max(filter(None, [p["tarih_son"], t]))
    for p in projeler.values():
        p["uzantilar"] = dict(sorted(p["uzantilar"].items(), key=lambda x: (-x[1], x[0])))

    durumlar = collections.Counter(d["durum"] for d in liste)
    uzantilar = collections.Counter(uzanti(d["dosya"]) for d in kayitlar)
    yillar = collections.Counter(iso_tarih(d["tarih"])[:4] for d in kayitlar)
    dizin = {
        "aciklama": (
            "Disk arşivinin (Elements diskinin Mac kopyası Portman_HDD_Projeler) adsız mührü ve dizini (İE-43, D-99). "
            "Ham dosyalar Mac'te ve Drive'da durur; depoya dosya girmez. Kodlar klasör adlarının düz sıralamasıyla "
            "(NFC, Python sorted) HD-001…; proje içinde dosyalar göreli yolun düz sıralamasıyla. Adlı eşleme yalnız "
            "Mac'te ve Drive'da (`_portman_analiz/kod_esleme.csv`). Dosya başına kayıt `muhur.csv`: kod, sıra, uzantı, "
            "bayt, kaynak listesindeki değişiklik tarihi, SHA-256. Kaynak bölümü Elements diskindeki üst klasörün "
            "türüdür (araclar/hdd_dizin.py › BOLUMLER); projenin türü değildir, tahmin değildir. Üreten komut: "
            "python3 araclar/hdd_dizin.py kur <kök> --depo <depo>."
        ),
        "sayilar": {
            "proje": len(projeler),
            "dosya": len(kayitlar),
            "bayt": sum(p["bayt"] for p in projeler.values()),
            "sha256_tekil": len({d["sha256"] for d in kayitlar}),
            "uzantilar": dict(sorted(uzantilar.items(), key=lambda x: (-x[1], x[0]))),
            "yillar": dict(sorted(yillar.items())),
            "kaynak_bolumleri": dict(sorted(collections.Counter(p["kaynak_bolumu"] for p in projeler.values()).items())),
            "revize_klasor": sum(p["revize"] for p in projeler.values()),
            "kaynak_listesi_durumlari": dict(sorted(durumlar.items())),
        },
        "projeler": projeler,
    }
    yaz_json(os.path.join(depo, DIZIN), dizin)

    esleme = os.path.join(kok, ANALIZ, "kod_esleme.csv")
    os.makedirs(os.path.dirname(esleme), exist_ok=True)
    with open(esleme, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(["kod", "sira", "proje_klasoru", "dosya", "sha256"])
        for d in kayitlar:
            w.writerow([d["kod"], d["sira"], d["klasor"], d["dosya"], d["sha256"]])
    print(f"mühür tuttu: {len(projeler)} proje, {len(kayitlar)} dosya, {dizin['sayilar']['bayt']} bayt; "
          f"yazıldı: {MUHUR}, {DIZIN}, {esleme}")
    return 0


def dogrula(kok: str, depo: str, esleme: str, onbellek: str, sure: float) -> int:
    with open(os.path.join(depo, MUHUR), encoding="utf-8", newline="") as f:
        muhur = {(s["kod"], s["sira"]): s for s in csv.DictReader(f, delimiter=";")}
    with open(esleme, encoding="utf-8-sig", newline="") as f:
        adlar = {(s["kod"], s["sira"]): s["proje_klasoru"] + "/" + s["dosya"] for s in csv.DictReader(f, delimiter=";")}
    if set(adlar) != set(muhur):
        print("eşleme mühürle aynı kayıtları taşımıyor")
        return 1
    sirali = sorted(muhur)
    ozet, bitti = ozetle(kok, [adlar[a] for a in sirali], onbellek, sure)
    if not bitti:
        print(f"süre bitti: {len(ozet)} / {len(sirali)} dosya; yeniden koşun")
        return 2
    eksik = [a for a in sirali if adlar[a] not in ozet]
    farkli = [a for a in sirali if adlar[a] in ozet
              and (ozet[adlar[a]][1] != muhur[a]["sha256"] or ozet[adlar[a]][0] != int(muhur[a]["bayt"]))]
    print(f"kopya: {len(sirali) - len(eksik) - len(farkli)} aynı, {len(eksik)} yok, {len(farkli)} farklı")
    return 1 if eksik or farkli else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    k = alt.add_parser("kur")
    k.add_argument("kok")
    k.add_argument("--depo", required=True)
    k.add_argument("--sure", type=float, default=150.0)
    k.add_argument("--onbellek")
    d = alt.add_parser("dogrula")
    d.add_argument("kok")
    d.add_argument("--depo", required=True)
    d.add_argument("--esleme", required=True)
    d.add_argument("--onbellek", required=True)
    d.add_argument("--sure", type=float, default=150.0)
    a = ap.parse_args(argv)
    if a.komut == "kur":
        return kur(a.kok, a.depo, a.sure, a.onbellek)
    return dogrula(a.kok, a.depo, a.esleme, a.onbellek, a.sure)


if __name__ == "__main__":
    sys.exit(main())
