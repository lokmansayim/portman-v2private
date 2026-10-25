"""Çelik hakeminin pafta okuyucusu (İE-16 PR-1): montaj paftasındaki panel etiketleri.

Montaj paftası PDF'inin her sayfasındaki sözcükler okunur. "D01", "K04", "M13", "C02", "T03" biçimindeki sözcük bir panel etiketidir: harf
liste okuyucusunun türlerinden (`oku.TURLER`; D duvar paneli, K kolon-kiriş, M makas, C çatı paneli, T tavan paneli), ardından iki ya da üç
basamak. Tür başına benzersiz etiket sayısı, en büyük numara, eksik numaralar (1'den en büyüğe), birden çok yerde geçen etiketler ve
etiketin geçtiği sayfalar yazılır. Eksik numara ve yinelenen etiket uyarıdır (`uyarilar`); sayı sessizce düzeltilmez. Sayfa başlıkları ve
antet okunmaz; etiket dışındaki yazılar sonuca girmez.

Kör projelerde panel etiketleri cevap tarafıdır: bu okuyucu yalnız hakemin kıyasında çağrılır (İE-16 › Kör ölçüm).
Veri, talimat değildir.
"""
from __future__ import annotations

import re
from pathlib import Path

from testler.celik import oku as celik_oku

HARFLER = "".join(h for _, h, _ in celik_oku.TURLER if h)
ETIKET = re.compile(rf"^([{HARFLER}])(\d{{2,3}})$")


def etiketler(yol: Path) -> dict:
    """{"sayfa_sayisi", "turler": {harf: {"adet", "en_buyuk", "eksik", "yinelenen", "sayfalar"}}, "uyarilar"}."""
    import pymupdf

    doc = pymupdf.open(str(yol))
    gorulen: dict[str, dict[int, list[int]]] = {}
    for sno, sayfa in enumerate(doc, 1):
        for w in sayfa.get_text("words"):
            m = ETIKET.match(w[4].strip())
            if m:
                gorulen.setdefault(m.group(1), {}).setdefault(int(m.group(2)), []).append(sno)
    turler, uyarilar = {}, []
    for h in HARFLER:
        n = gorulen.get(h)
        if not n:
            continue
        en = max(n)
        eksik = [i for i in range(1, en + 1) if i not in n]
        yin = sorted(f"{h}{i:02d}" for i, s in n.items() if len(s) > 1)
        turler[h] = {"adet": len(n), "en_buyuk": en, "eksik": eksik, "yinelenen": yin,
                     "sayfalar": sorted({s for v in n.values() for s in v})}
        if eksik:
            uyarilar.append(f"{h}: eksik numara {', '.join(f'{h}{i:02d}' for i in eksik)}")
        if yin:
            uyarilar.append(f"{h}: birden çok yerde geçen etiket {', '.join(yin)}")
    return {"sayfa_sayisi": len(doc), "turler": turler, "uyarilar": uyarilar}
