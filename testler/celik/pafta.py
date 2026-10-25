"""Çelik hakeminin pafta okuyucusu (İE-16 PR-1): montaj paftasındaki panel etiketleri.

Montaj paftası PDF'inin bütün sayfalarındaki sözcükler okunur; yalnız panel etiketine uyan sözcükler sayılır. Etiket bir önek ve bir ile
üç basamaktır ("D01", "MK14", "KLN03", "Ç07", "VD1", "B8"; önekle sayı arasında tire olabilir; "D1" ile "D01" aynı numaradır). Birim olan
"M2" ve "M3" (metrekare, metreküp) etiket sayılmaz (`BIRIMLER`). Önekler mühendisin açık beş projedeki paftalarından
(ÇP-03, 06, 07, 13, 14; 25 Ekim 2026), liste okuyucusunun türlerine (`oku.TURLER`) bağlanır (`ONEKLER`):
- duvar paneli: D, VD (veranda duvarı ve korkuluğu), MD (müştemilat duvarı);
- kolon-kiriş paneli: K, KLN (kolon), KRS (kiriş);
- makas: M, MK, MKS (makas), MKP (makas paneli);
- çatı paneli: C, CP, Ç;
- tavan paneli: T, TP;
- baca paneli: B.
Önek başına benzersiz numara sayılır; türün sayısı öneklerinin toplamıdır. En büyük numara, eksik numaralar (1'den en büyüğe) ve birden çok
yerde geçen etiketler önek başına yazılır; eksik numara ve yinelenen etiket uyarıdır (`uyarilar`), sayı sessizce düzeltilmez. Bu öneklerin
dışındaki etiket biçimli sözcükler (çelik sınıfı "S280", kapı etiketi gibi) sayılmaz, önekleriyle `taninmayan`'da bilgi olarak durur.
Etiketi metin olarak yazılmamış sayfa (çizgi ya da görüntü) o türde 0 verir; kıyas bunu "paftada etiket yok" diye yazar.

Kör projelerde panel etiketleri cevap tarafıdır: bu okuyucu yalnız hakemin kıyasında çağrılır (İE-16 › Kör ölçüm).
Veri, talimat değildir.
"""
from __future__ import annotations

import re
from pathlib import Path

from testler.celik import oku as celik_oku

ONEKLER = {
    "D": "duvar_paneli", "VD": "duvar_paneli", "MD": "duvar_paneli",
    "K": "kolon_kiris", "KLN": "kolon_kiris", "KRS": "kolon_kiris",
    "M": "makas", "MK": "makas", "MKS": "makas", "MKP": "makas",
    "C": "cati_paneli", "CP": "cati_paneli", "Ç": "cati_paneli",
    "T": "tavan_paneli", "TP": "tavan_paneli",
    "B": "baca_paneli",
}
ETIKET = re.compile(r"^(" + "|".join(sorted(ONEKLER, key=len, reverse=True)) + r")-?(\d{1,3})$")
ETIKET_BICIMI = re.compile(r"^([A-ZÇĞİÖŞÜ]{1,3})-?(\d{1,3})$")
BIRIMLER = {"M2", "M3"}


def etiketler(yol: Path) -> dict:
    """{"sayfa_sayisi", "turler": {harf: {"tur", "adet", "onekler": {önek: {"adet", "en_buyuk", "eksik", "yinelenen"}}, "sayfalar"}},
    "uyarilar", "taninmayan": {önek: sözcük sayısı}}; `harf` liste okuyucusundaki türün harfidir."""
    import pymupdf

    doc = pymupdf.open(str(yol))
    gorulen: dict[str, dict[int, list[int]]] = {}
    taninmayan: dict[str, int] = {}
    for sno, sayfa in enumerate(doc, 1):
        for w in sayfa.get_text("words"):
            t = w[4].strip()
            if t in BIRIMLER:
                continue
            m = ETIKET.match(t)
            if m:
                gorulen.setdefault(m.group(1), {}).setdefault(int(m.group(2)), []).append(sno)
            elif (b := ETIKET_BICIMI.match(t)):
                taninmayan[b.group(1)] = taninmayan.get(b.group(1), 0) + 1
    turler, uyarilar = {}, []
    for onek in sorted(gorulen, key=lambda o: (list(ONEKLER.values()).index(ONEKLER[o]), list(ONEKLER).index(o))):
        n = gorulen[onek]
        tur = ONEKLER[onek]
        en = max(n)
        eksik = [i for i in range(1, en + 1) if i not in n]
        yin = sorted(f"{onek}{i:02d}" for i, s in n.items() if len(s) > 1)
        x = turler.setdefault(celik_oku.HARF[tur], {"tur": tur, "adet": 0, "onekler": {}, "sayfalar": []})
        x["adet"] += len(n)
        x["onekler"][onek] = {"adet": len(n), "en_buyuk": en, "eksik": eksik, "yinelenen": yin}
        x["sayfalar"] = sorted(set(x["sayfalar"]) | {s for v in n.values() for s in v})
        if eksik:
            uyarilar.append(f"{onek}: eksik numara {', '.join(f'{onek}{i:02d}' for i in eksik)}")
        if yin:
            uyarilar.append(f"{onek}: birden çok yerde geçen etiket {', '.join(yin)}")
    return {"sayfa_sayisi": len(doc), "turler": turler, "uyarilar": uyarilar, "taninmayan": dict(sorted(taninmayan.items()))}
