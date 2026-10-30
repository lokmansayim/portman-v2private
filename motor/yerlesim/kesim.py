"""Kesim planı (kural `kurallar/yerlesim/prefabrik.json › kesim_plani`): boyla alınan kartın parçaları stok boylarına.

Omega ve aşıkta modelin parçaları stok boylara en uzun önce, ilk sığan boya yerleşir; bir boyun kullanılır uzunluğu parça boyu − pay
(yerleşim kuralındaki tam parça). Dere hattı bindirmeyle bölünür: hat başına ⌈(hat − bindirme) ÷ (parça boyu − bindirme)⌉ parça, son
parça kalan boy; parçalar stok boylarına aynı yolla yerleşir (K5b: bir hattın artanı başka hatta kullanılır, taşan verandanın kısa
hatları gibi). Yedek parça eklenmez (karar D açık); sayı modelin yerleşimidir, yükleme listesinin metrajı değildir.

K3b'nin kartlarında (alt çerçeve, saçak ve kalkan kenarları, mahya) sayı liste üretecinin sayma yoludur, boy modelden: hatların toplamı
(`toplam_karti`: ⌈Σ hat ÷ (parça boyu − bindirme)⌉, bir kez yukarı) ya da kenar başına (`kenar_karti`: ⌈kenar ÷ parça boyu⌉). Yukarı
yuvarlamanın payı liste üretecininki (`motor.prefabrik_liste.TAVAN`, 1e-9); K2'nin kartları kendi payıyla (`ESIK`).
"""
from __future__ import annotations

import math

ESIK = 1e-6
LISTE_ESIK = 1e-9          # liste üretecinin yukarı yuvarlaması (`TAVAN`); K3b sayıyı onun yoluyla verir


def _tavan(x: float) -> int:
    return int(math.ceil(x - LISTE_ESIK))


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
    """Hat başına ⌈(hat − bindirme) ÷ (parça boyu − bindirme)⌉ parça (tam boylar bindirmeyle, son parça kalan boy); parçalar stok
    boylarına en uzun önce, ilk sığan boy (`yerlestir`)."""
    n = [max(1, math.ceil((h - bindirme_cm) / (parca_boyu_cm - bindirme_cm) - ESIK)) for h in hatlar_cm]
    parcalar = [b for h, k in zip(hatlar_cm, n) for b in [parca_boyu_cm] * (k - 1) + [min(parca_boyu_cm, h - (k - 1) * (parca_boyu_cm - bindirme_cm))]]
    dizilim = yerlestir(parcalar, parca_boyu_cm)
    return {"yontem": "hat başına ⌈(hat − bindirme) ÷ (parça boyu − bindirme)⌉ parça; parçalar stok boylarına en uzun önce, ilk sığan boy",
            "parca_boyu_cm": parca_boyu_cm, "bindirme_cm": bindirme_cm, "parca": len(hatlar_cm), "toplam_m": round(sum(hatlar_cm) / 100, 4),
            "stok": len(dizilim), "hat_basina": n, "dizilim": [[round(b, 4) for b in d] for d in dizilim]}


def toplam_karti(hatlar_cm: list[float], parca_boyu_cm: float, bindirme_cm: float = 0.0, parca: int | None = None) -> dict:
    """Hatların toplamı bir kez yukarı bölünür (liste üretecinin yolu); `parca` modeldeki parça sayısı (kesik hatta hattan çok)."""
    n = _tavan(sum(hatlar_cm) / (parca_boyu_cm - bindirme_cm))
    return {"yontem": "⌈hatların toplamı ÷ (parça boyu − bindirme)⌉, bir kez yukarı", "parca_boyu_cm": parca_boyu_cm, "bindirme_cm": bindirme_cm,
            "parca": len(hatlar_cm) if parca is None else parca, "hat": len(hatlar_cm), "toplam_m": round(sum(hatlar_cm) / 100, 4), "stok": n,
            "hatlar_cm": [round(h, 4) for h in hatlar_cm]}


def kenar_karti(kenarlar_cm: list[float], parca_boyu_cm: float) -> dict:
    """Kenar başına ⌈kenar ÷ parça boyu⌉ (kitap: kenar kenar; bindirme yok)."""
    n = [_tavan(h / parca_boyu_cm) for h in kenarlar_cm]
    return {"yontem": "kenar başına ⌈kenar ÷ parça boyu⌉", "parca_boyu_cm": parca_boyu_cm, "parca": len(kenarlar_cm),
            "toplam_m": round(sum(kenarlar_cm) / 100, 4), "stok": sum(n), "hat_basina": n}
