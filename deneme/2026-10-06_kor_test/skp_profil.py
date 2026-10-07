#!/usr/bin/env python3
"""Karkas modelindeki (SKP) profil boyları ve et kalınlıkları: panel panel üye sayısı, toplam profil boyu, et.

Çelik ağırlığı kuralının girdisidir (`kurallar.json` → `celik.profil_kg_m`): model verilmişse bir grubun ağırlığı, o gruptaki panellerin profil boyu
toplamı × profilin birim ağırlığıdır (80 × 45 × 1,2 için 1,66 kg/m; 0,8 için 1,11 kg/m). Kör test projesinde on grubun onunda gerçek listedeki ağırlığı
verdi (6 Ekim 2026).

Girdi: `../2026-10-02_skp/kaydet.py` ile yazılan ara dosya (çözülmüş model; yüzler dünya uzayında, cm). Üst düzey her bileşen bir paneldir
(D1, MKS3, KRS1…); panelin en derin düğümleri üyelerdir (dikme, başlık, kuşak, çapraz). Ara dosya kendi ürettiğimiz bir pickle'dır; başka kaynaktan
gelen pickle açılmaz.

- Üye: katı çizilmiş profil. Ekseni yan yüzlerinin normallerinden bulunur (bütün yan yüzlere dik doğrultu: alan ağırlıklı normal kovaryansının en
  küçük öz değerli doğrultusu); böylece gövdesinden kısa bir parçada da eksen doğru çıkar. Eksene dik iki uzanımından büyüğü en çok 16 cm (80 ve
  140 mm gövdeli profiller), küçüğü 2 cm'den büyük olmalı. Levha ya da panel çerçevesi gibi düğümler ve düz şeritler üye sayılmaz; kaç düğümün
  sayılmadığı dökümde yazar.
- Aynı yolu paylaşan (adsız kopyalar) üyeler ortak kenarı olmayan parçalara ayrılır; her parça ayrı üyedir. Yüz yüze değen iki profil tek parça
  okunur: böyle bir parça açılımından anlaşılır (yan yüz alanı ÷ boy ÷ 2; tek profilde yaklaşık 20 cm) ve `şüpheli` olarak sayılır; şüpheli üye varsa
  çıkış kodu 1'dir.
- Üye boyu: köşe noktalarının eksen boyunca uzanımı; eğik üyelerde de gerçek boy.
- Et kalınlığı: üyenin yan yüzlerinde (normali eksene dik) birbirine paralel düzlem çiftleri arasındaki küçük aralık (0,2–5 mm); alanı en büyük olan
  aralık üyenin etidir. Kör test projesinin modelinde 1223 üyenin hepsi 1,2 ya da 0,8 mm okunuyor; bir panelin üyeleri aynı ette.
  Düz yüzlerle (kabuk olarak) çizilmiş modellerde üye bulunmaz: o modeller bu betikle okunamaz (hiç panel bulunamazsa çıkış kodu 1).

Panellerin hangi gruba girdiği (dış duvar, iç duvar, makas…) tanımda yazılır: `celik_modeli.gruplar.<grup>.paneller = {panel adı: profil boyu (m)}`.

Kullanım:
    python skp_profil.py ara/model.pkl                      # panel panel döküm
    python skp_profil.py ara/model.pkl --json boylar.json   # {panel: {uye, boy_m, et_mm, et_dagilimi}}
    python skp_profil.py ara/model.pkl --disarida           # üye sayılmayan düğümleri de göster
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np

GENIS_CM = 16.0         # üyenin eksene dik büyük uzanımı en çok bu kadar (140 mm gövdeli profil dahil)
DAR_CM = 2.0            # küçük uzanımı bundan büyük olmalı (düz şerit ve levha üye değildir)
ET_ARALIGI_CM = (0.02, 0.5)
ACILIM_EN_COK_CM = 32.0  # tek profilin açılımı (yan yüz alanı ÷ boy ÷ 2) bundan küçüktür; büyükse yüz yüze değen iki profil tek parça okunmuş olabilir


def _parcalar(yuzler: list[dict]) -> list[list[dict]]:
    """Yüzleri ortak kenar üzerinden bağlı parçalara ayırır (aynı yolu paylaşan ayrı üyeler birleşmesin; yalnız bir köşede değen iki üye ayrı kalır)."""
    ust = list(range(len(yuzler)))

    def bul(i: int) -> int:
        while ust[i] != i:
            ust[i] = ust[ust[i]]
            i = ust[i]
        return i

    ilk: dict[tuple, int] = {}
    for i, y in enumerate(yuzler):
        for h in y["halkalar"]:
            n = [(round(v[0] * 100), round(v[1] * 100), round(v[2] * 100)) for v in np.asarray(h, float)]
            for p, q in zip(n, n[1:] + n[:1]):
                if p == q:
                    continue
                k = (p, q) if p < q else (q, p)
                if k in ilk:
                    a, b = bul(i), bul(ilk[k])
                    if a != b:
                        ust[a] = b
                else:
                    ilk[k] = i
    grup = collections.defaultdict(list)
    for i, y in enumerate(yuzler):
        grup[bul(i)].append(y)
    return list(grup.values())


def _alan_normal(halka) -> tuple[float, np.ndarray]:
    h = np.asarray(halka, float)
    n = np.zeros(3)
    for i in range(len(h)):
        n += np.cross(h[i], h[(i + 1) % len(h)])
    alan = float(np.linalg.norm(n)) / 2.0
    return alan, (n / (2.0 * alan) if alan > 1e-12 else np.array([0.0, 0.0, 1.0]))


def _et_mm(yuzler: list[dict], eksen: np.ndarray) -> float | None:
    """Üyenin et kalınlığı (mm): yan yüzlerde paralel düzlem çiftleri arasındaki, alanı en büyük küçük aralık."""
    aileler: list[dict] = []
    for y in yuzler:
        alan, n = _alan_normal(y["halkalar"][0])
        for h in y["halkalar"][1:]:
            alan -= _alan_normal(h)[0]
        if alan < 1e-6 or abs(float(n @ eksen)) > 0.3:
            continue
        d = float(n @ np.asarray(y["halkalar"][0], float).mean(0))
        for a in aileler:
            s = float(n @ a["n"])
            if abs(s) > 0.999:
                a["oteleme"][round((d if s > 0 else -d) / 0.005) * 0.005] += alan
                break
        else:
            aileler.append({"n": n, "oteleme": collections.defaultdict(float, {round(d / 0.005) * 0.005: alan})})
    aday: dict[float, float] = collections.defaultdict(float)
    for a in aileler:
        ot = sorted(a["oteleme"].items())
        for (d0, a0), (d1, a1) in zip(ot, ot[1:]):
            if ET_ARALIGI_CM[0] < d1 - d0 < ET_ARALIGI_CM[1]:
                aday[round(d1 - d0, 2)] += min(a0, a1)
    return round(max(aday.items(), key=lambda kv: kv[1])[0] * 10, 2) if aday else None


def _eksen(yuzler: list[dict]) -> tuple[np.ndarray, float]:
    """Üyenin ekseni ve yüz alanı toplamı: yan yüzlerin hepsine dik doğrultu (alan ağırlıklı normal kovaryansının en küçük öz değerli doğrultusu)."""
    M, toplam = np.zeros((3, 3)), 0.0
    for y in yuzler:
        alan, n = _alan_normal(y["halkalar"][0])
        for h in y["halkalar"][1:]:
            alan -= _alan_normal(h)[0]
        if alan > 1e-9:
            M += alan * np.outer(n, n)
            toplam += alan
    w, v = np.linalg.eigh(M)
    return v[:, 0], toplam


def profil_boylari(model: dict) -> tuple[dict, dict, dict]:
    """Dönen: ({panel: {"uye", "boy_m", "et_mm", "et_dagilimi"}}, {panel: üye sayılmayan düğümler},
    {"ust_duzey_yuz": panel sayılmayan üst düzey yüz sayısı, "supheli": [(panel, düğüm, açılım cm)]})."""
    dugum = collections.defaultdict(list)
    ust_duzey = 0
    for y in model["yuzler"]:
        yol = y["yol"].strip("/")
        if "/" in yol:               # üst düzeydeki çıplak yüzler (zemin, yardımcı çizgi) panel değildir; sayısı dökümde yazar
            dugum[yol].append(y)
        else:
            ust_duzey += 1
    supheli: list[tuple] = []
    boy = collections.defaultdict(float)
    say = collections.Counter()
    et = collections.defaultdict(lambda: collections.defaultdict(float))       # panel → et (mm) → boy (cm)
    disarida = collections.defaultdict(list)
    for yol, yuzler in dugum.items():
        panel = yol.split("/")[0]
        for parca in _parcalar(yuzler):
            p = np.unique(np.round(np.vstack([np.asarray(h, float) for y in parca for h in y["halkalar"]]), 3), axis=0)
            if len(p) < 8:
                disarida[panel].append((yol.split("/", 1)[1], f"{len(p)} köşe"))
                continue
            eksen, alan = _eksen(parca)
            c = p - p.mean(0)
            L = float((c @ eksen).max() - (c @ eksen).min())            # eksen boyunca uzanım: üye boyu
            dik = c - np.outer(c @ eksen, eksen)                          # eksene dik düzlemdeki kesit
            _, v2 = np.linalg.eigh(dik.T @ dik)
            kesit = np.sort((dik @ v2).max(0) - (dik @ v2).min(0))[::-1]  # kesitin iki uzanımı, büyükten küçüğe (üçüncüsü sıfır)
            if kesit[0] > GENIS_CM or kesit[1] <= DAR_CM or L < 1.0:
                disarida[panel].append((yol.split("/", 1)[1], [round(L, 1)] + [round(float(x), 1) for x in kesit[:2]]))
                continue
            boy[panel] += L
            say[panel] += 1
            et[panel][_et_mm(parca, eksen)] += L
            acilim = alan / L / 2                                       # sacın açılımı: tek profilde yaklaşık 20 cm
            if acilim > ACILIM_EN_COK_CM:
                supheli.append((panel, yol.split("/", 1)[1], round(acilim, 1)))

    def sira(ad: str):
        m = re.match(r"([^\d#]+)\s*#?(\d+)?", ad)
        return (m.group(1), int(m.group(2) or 0)) if m else (ad, 0)

    cik = {}
    for ad in sorted(boy, key=sira):
        dagilim = {("okunamadı" if k is None else f"{k:g}"): round(b / 100, 3) for k, b in sorted(et[ad].items(), key=lambda kv: -kv[1])}
        baskin = max(et[ad].items(), key=lambda kv: kv[1])[0]
        cik[ad] = {"uye": say[ad], "boy_m": round(boy[ad] / 100, 3), "et_mm": baskin, "et_dagilimi": dagilim}
    return cik, dict(disarida), {"ust_duzey_yuz": ust_duzey, "supheli": supheli}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ara", type=Path, help="kaydet.py ile yazılan ara dosya (.pkl)")
    ap.add_argument("--json", type=Path, help="panel panel sonucu JSON olarak yaz")
    ap.add_argument("--disarida", action="store_true", help="üye sayılmayan düğümleri de göster")
    a = ap.parse_args()
    with a.ara.open("rb") as f:
        model = pickle.load(f)
    if not isinstance(model, dict) or not isinstance(model.get("yuzler"), list):
        raise SystemExit("Beklenen ara dosya değil: ../2026-10-02_skp/kaydet.py'nin yazdığı model ('yuzler' listesiyle) bekleniyor.")
    boylar, disarida, ek = profil_boylari(model)
    for ad, v in boylar.items():
        karisik = "  (iki et birden: " + ", ".join(f"{k} mm {b} m" for k, b in v["et_dagilimi"].items()) + ")" if len(v["et_dagilimi"]) > 1 else ""
        dis_ = f" · üye sayılmayan {len(disarida[ad])}: {disarida[ad][:3]}" if a.disarida and disarida.get(ad) else ""
        et = "okunamadı" if v["et_mm"] is None else f"{v['et_mm']:g} mm"
        print(f"{ad:12s} üye {v['uye']:3d} · profil boyu {v['boy_m']:7.2f} m · et {et}{karisik}{dis_}")
    toplam_et = collections.defaultdict(float)
    for v in boylar.values():
        for k, b in v["et_dagilimi"].items():
            toplam_et[k] += b
    print(f"toplam {len(boylar)} panel · {sum(v['uye'] for v in boylar.values())} üye · {sum(v['boy_m'] for v in boylar.values()):.2f} m · "
          + " · ".join(f"et {k} mm {b:.2f} m" for k, b in sorted(toplam_et.items())) + f" · üye sayılmayan düğüm {sum(len(x) for x in disarida.values())}"
          + f" · panel sayılmayan üst düzey yüz {ek['ust_duzey_yuz']}")
    for panel, dugum_adi, acilim in ek["supheli"]:
        print(f"ŞÜPHELİ: {panel} · {dugum_adi}: açılım {acilim} cm (tek profilde yaklaşık 20 cm); yüz yüze değen iki profil tek üye okunmuş olabilir")
    if not boylar:
        print("Hiç panel bulunamadı: model katı çizilmiş, bileşenlere ayrılmış profillerden oluşmuyor olabilir; bu betikle okunamaz.")
        return 1
    if a.json:
        a.json.write_text(json.dumps(boylar, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if ek["supheli"] else 0


if __name__ == "__main__":
    sys.exit(main())
