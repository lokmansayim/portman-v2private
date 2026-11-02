"""İE-15 · K5b · Gövdeden taşan verandanın çatısı (BK-14): yavru makas, aşık, kaplama, kalkan betopanı, dere ve iniş; çatı kenarları
(`kenar.py`) da aynı çerçeveyle. Kural `kurallar/yerlesim/prefabrik.json › veranda_catisi`.

Verandanın çatısı BK-14'ün düzlemlerinden (`motor/veranda.cati`; bugünkü IFC'deki `VERANDA_CATI_n_m` yüzleri) kendi çerçevesiyle kurulur:
`cati.cerceve`'nin anahtarları, `u` makas ekseni (verandanın cephe boyunca eni), `ou` yerel `u`'nun dünyadaki başı, `v` dünya koordinatı
(`v0`..`v1` çatının saçaklı boyu, `w0`..`w1` kirişlerin boyu, `dis` dış kalkanın kirişinin dış yüzü, `ic` gövde duvarının dış yüzü).
Ana çatının işlevleri (`cati.asik`, `cati.kaplama`, `cati.betopan`, `cati.dere`) bu çerçeveyle çağrılır; parçalar `Cati` bilgisini (verandanın
adı) ve adında `VERANDA_` önekini taşır (montaj rehberi ana çatının parçalarını adıyla okur).

Yalnız ana çatı beşikken ve veranda çatısı ana çatıya paralel beşikken (TK-01) kurulur; çapraz ya da tek yön veranda çatısı "kural yok"
yazar (İE-17 PR-1b'den sonra K6). Sayılar liste üretecinin ek çatı parçası satırlarındaki gibi (`motor/prefabrik_liste.py` ›
`_veranda_catilari`): yavru makas J8, kaplama iki yüz birlikte, iniş ek çatı parçası başına.
"""
from __future__ import annotations

import math

from . import cati

KURAL = "veranda_catisi"
ONEK = "VERANDA_"
ESIK = 1e-6


def _yok(ad: str, neden: str) -> dict:
    return {"parca": f"veranda çatısı ({ad})", "sinif": "—", "neden": neden}


def cerceveler(g: dict) -> tuple[list[dict], list[dict]]:
    """Her taşan verandanın çatı çerçevesi ve kurulamayanların kural yoku. Çerçeve `cati.cerceve`'ninkiler ve `ou`, `w0`, `w1`, `dis`,
    `ic`, `ad`, `kiris` (dış kirişin ekseni, `v`)."""
    out, yok = [], []
    mahya_y = g["cati"]["makas_ekseni"] == "x"                         # ana çatının mahyası y boyunca
    for v in g["dis_verandalar"]:
        c, ad = v["cati"], v["ad"]
        if c["tip"] != "besik":
            yok.append(_yok(ad, f"{KURAL}: veranda çatısı \"{c['tip']}\"; K5b yalnız ana çatıya paralel beşiği kurar (tek yön İE-15 K6'da)"))
            continue
        (ax, ay), (bx, by) = c["mahya"]
        if (abs(ax - bx) < ESIK) != mahya_y:
            yok.append(_yok(ad, f"{KURAL}: veranda çatısı ana çatının saçak yüzünde, mahyası ana çatınınkine dik (çapraz beşik: dere içi ve ters "
                                f"mahya); K5b yalnız ana çatıya paralel beşiği kurar (İE-15 K6)"))
            continue
        x0, y0, x1, y1 = v["rect"]
        X0, Y0, X1, Y1 = c["kutu"]
        u0, u1, w0, w1 = (x0, x1, y0, y1) if mahya_y else (y0, y1, x0, x1)
        V0, V1 = (Y0, Y1) if mahya_y else (X0, X1)
        aciklik, s, eg = u1 - u0, c["sacak"], c["egim"]
        um = (ax if mahya_y else ay) - u0
        if abs(um - aciklik / 2) > 0.5:
            yok.append(_yok(ad, f"{KURAL}: mahya verandanın ortasında değil ({um:g} / {aciklik:g} cm); kural ortadaki mahyayı kurar"))
            continue
        dis_min = v["cephe"] in ("on", "sol")
        dis = w0 if dis_min else w1
        kiris = next((((r[1] + r[3]) / 2 if mahya_y else (r[0] + r[2]) / 2) for r in g["veranda_kirisleri"]
                      if (r[2] - r[0] > r[3] - r[1]) == mahya_y and abs((r[1] if dis_min else r[3]) - dis if mahya_y
                                                                        else (r[0] if dis_min else r[2]) - dis) < 0.5), None)
        out.append({"mx": mahya_y, "ou": u0, "aciklik": aciklik, "boy": w1 - w0, "s": s, "eg": eg, "zs": c["sacak_kotu"], "um": aciklik / 2,
                    "kos": 1 / math.sqrt(1 + eg * eg), "egik": (aciklik / 2 + s) * math.sqrt(1 + eg * eg), "v0": V0, "v1": V1, "w0": w0, "w1": w1,
                    "v_bas": "min" if dis_min else "max", "dis": dis, "ic": w1 if dis_min else w0, "ad": ad, "kiris": kiris})
    return out, yok


def isaretle(parcalar: list[dict], F: dict) -> list[dict]:
    """Veranda parçası: `Cati` bilgisi ve adın öneki."""
    for p in parcalar:
        p["bilgi"] = {"Cati": F["ad"], **p["bilgi"]}
        p["onek"] = ONEK
        p["aciklama"] = f"{F['ad']}: {p['aciklama']}"
    return parcalar


def kalkan(F: dict, t: float) -> dict:
    """Dış kalkan: betopanın `v` aralığı (dış kirişin dış yüzünde), dışarı yön ve kalkan saçağının ucu (`kenar.kalkan_kenarlari`)."""
    on = F["v_bas"] == "min"
    return {"ad": f"{F['ad']} kalkanı", "v0": F["dis"] - t if on else F["dis"], "v1": F["dis"] if on else F["dis"] + t, "on": on,
            "v_dis": F["dis"] - t if on else F["dis"] + t, "v_uc": F["v0"] if on else F["v1"]}


def yavru_makaslar(g: dict, F: dict, D: dict) -> list[dict]:
    """Sayı liste kuralından (J8): ⌈(derinlik − 2 × dış duvar) ÷ makas aralığı⌉ + 1. İlki dış kirişin ekseninde (kiriş yoksa dış kenardan
    yarım makas içeride), sonuncusu gövde duvarının dış yüzünden yarım makas dışarıda, aralarında eşit aralık. Gösterim: alt başlık
    kirişlerin üstünde açıklık boyunca, üst başlıklar saçak ucundan mahyaya (ana makasınki gibi), orta dikme."""
    t_dis = 2 * max(d.h for d in g["duvarlar"] if d.tur == "dis")
    n = math.ceil((F["boy"] - 2 * t_dis) / D["makas_aralik"] - 1e-6) + 1
    yarim = D["makas_yarim_cm"]
    sgn = 1 if F["v_bas"] == "min" else -1                              # dıştan içeri
    v_ilk = F["kiris"] if F["kiris"] is not None else F["dis"] + sgn * yarim
    v_son = F["ic"] - sgn * yarim
    kal, b, d = D["kesit_cm"]["kalinlik"], D["kesit_cm"]["baslik"], D["kesit_cm"]["dikme"]
    H0, A, s, um = g["duvar_h"], F["aciklik"], F["s"], F["um"]
    zs, zm = F["zs"], F["zs"] + (um + s) * F["eg"]
    uz = [[(0, H0), (A, H0), (A, H0 + b), (0, H0 + b)],
          [(-s, zs), (um, zm), (um, zm + b), (-s, zs + b)],
          [(um, zm), (A + s, zs), (A + s, zs + b), (um, zm + b)],
          [(um - d / 2, H0 + b), (um + d / 2, H0 + b), (um + d / 2, zm), (um - d / 2, zm)]]
    out = []
    for i in range(n):
        v = v_ilk + (v_son - v_ilk) * i / (n - 1) if n > 1 else v_ilk
        yer = "dış kiriş" if i == 0 else "duvar dibi" if i == n - 1 else "ara"
        out.append({"kural": KURAL, "parca": "yavru_makas",
                    "geo": {"tip": "coklu", "parcalar": [cati._prizma(F, k, v - kal / 2, v + kal / 2) for k in uz]},
                    "bilgi": {"Sira": i + 1, "Yer": yer, "MakasAdedi": n, "Aciklik_cm": round(A + 2 * s, 4)},
                    "aciklama": f"{i + 1}. yavru makas ({yer}), açıklık {A + 2 * s:g} cm"})
    return out
