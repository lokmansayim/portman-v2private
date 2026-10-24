"""Kesim planı (kural `kurallar/yerlesim/prefabrik.json › kesim_plani`): boyla alınan kartın parçaları stok boylarına.

Omega ve aşıkta modelin parçaları stok boylara en uzun önce, ilk sığan boya yerleşir; bir boyun kullanılır uzunluğu parça boyu − pay
(yerleşim kuralındaki tam parça). Dere hattı bindirmeyle bölünür: hat başına ⌈(hat − bindirme) ÷ (parça boyu − bindirme)⌉. Yedek parça
eklenmez (karar D açık); sayı modelin yerleşimidir, yükleme listesinin metrajı değildir.
"""
from __future__ import annotations

import math

ESIK = 1e-6


def yerlestir(boylar_cm: list[float], kullanilir_cm: float) -> list[list[float]]:
    """En uzun önce, ilk sığan boya. Döner: her stok boyuna yerleşen parça boyları."""
    stok: list[list] = []
    for b in sorted(boylar_cm, reverse=True):
        if b > kullanilir_cm + ESIK:
            raise ValueError(f"{b:g} cm'lik parça {kullanilir_cm:g} cm'lik boya sığmaz")
        for s in stok:
            if s[0] >= b - ESIK:
                s[0] -= b
                s[1].append(b)
                break
        else:
            stok.append([kullanilir_cm - b, [b]])
    return [s[1] for s in stok]


def boy_karti(boylar_cm: list[float], parca_boyu_cm: float, pay_cm: float) -> dict:
    kullanilir = parca_boyu_cm - pay_cm
    dizilim = yerlestir(boylar_cm, kullanilir)
    return {"yontem": "en uzun önce, ilk sığan boy", "parca_boyu_cm": parca_boyu_cm, "kullanilir_cm": round(kullanilir, 4),
            "parca": len(boylar_cm), "toplam_m": round(sum(boylar_cm) / 100, 4), "stok": len(dizilim),
            "artik_m": round(sum(kullanilir - sum(d) for d in dizilim) / 100, 4), "dizilim": [[round(b, 4) for b in d] for d in dizilim]}


def dere_karti(hatlar_cm: list[float], parca_boyu_cm: float, bindirme_cm: float) -> dict:
    n = [math.ceil((h - bindirme_cm) / (parca_boyu_cm - bindirme_cm) - ESIK) for h in hatlar_cm]
    return {"yontem": "hat başına ⌈(hat − bindirme) ÷ (parça boyu − bindirme)⌉", "parca_boyu_cm": parca_boyu_cm, "bindirme_cm": bindirme_cm,
            "parca": len(hatlar_cm), "toplam_m": round(sum(hatlar_cm) / 100, 4), "stok": sum(n), "hat_basina": n}
