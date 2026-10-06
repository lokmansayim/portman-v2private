#!/usr/bin/env python3
"""Genel motorun sağlaması: Ç8201, Yapı Tanımı 0.5 ile (`C8201_05.json`) genel hattan geçirilir ve 0.4 hattının kayıtlı sonuçlarıyla
(`../2026-10-02_celik/sonuc`, `../2026-10-03_yukleme/sonuc`) karşılaştırılır. Ayrıca genel kaplama dizilimi, rastgele dikdörtgen kırma
çatılarda eski dizilimle (`cati_acilim.dizilim`) karşılaştırılır. Fark varsa çıkış kodu 1.

Karşılaştırılanlar: mahal alanı, çevresi, köşeleri ve boşlukları; dış çevre ve boşluklar; iç duvar boyu; çatı yüzeyi, saçak, mahya hattı,
aşık boyu, kaplama adedi ve boyu; yükleme listesinin bütün satırları (kalem, boyut, adet, kg). Bilinen fark: yok.

Kullanım:
    python saglama.py
"""
from __future__ import annotations

import itertools
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

BURADA = Path(__file__).resolve().parent
YUKLEME = BURADA.parent / "2026-10-03_yukleme"
sys.path.insert(0, str(YUKLEME))
import cati_acilim  # noqa: E402
import cati_genel  # noqa: E402
import girdi_genel  # noqa: E402
import yapi  # noqa: E402


def yakin(a, b, tol=0.006):
    return abs(a - b) <= tol


def main() -> int:
    sorun: list[str] = []
    kur = json.loads((YUKLEME / "kurallar.json").read_text(encoding="utf-8"))
    t = json.loads((BURADA / "C8201_05.json").read_text(encoding="utf-8"))
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    m = girdi_genel.metraj(y, c, kur)
    g = girdi_genel.girdi(y, c, m, kur, "C8201_05.json")
    eski = json.loads((YUKLEME / "sonuc" / "C8201_girdi.json").read_text(encoding="utf-8"))
    # 1) metraj
    for o in eski["odalar"]:
        n = next((x for x in g["odalar"] if x["ad"] == o["ad"]), None)
        if n is None:
            sorun.append(f"mahal yok: {o['ad']}")
            continue
        for k in ("cevre_m", "alan_m2"):
            if not yakin(o[k], n[k], 0.0011):
                sorun.append(f"{o['ad']} {k}: {o[k]} / {n[k]}")
        for k in ("ic_kose", "dis_kose", "tur", "islev"):
            if o[k] != n[k]:
                sorun.append(f"{o['ad']} {k}: {o[k]} / {n[k]}")
        if sorted(o["bosluk_m2"]) != sorted(round(x, 4) for x in n["bosluk_m2"]):
            sorun.append(f"{o['ad']} boşluklar: {sorted(o['bosluk_m2'])} / {sorted(n['bosluk_m2'])}")
        if not yakin(o["cevre_m"] * g["kat_yuksekligi_m"], n["duvar_brut_m2"], 0.006):
            sorun.append(f"{o['ad']} duvar brüt: {o['cevre_m'] * g['kat_yuksekligi_m']:.3f} / {n['duvar_brut_m2']}")
    cift = [("bina_m2", None), ("dis_olcu_m", None), ("kapali_olcu_m", None), ("oda_sayisi", None), ("ic_kapi_adedi", None), ("ic_duvar_boyu_m", None),
            ("veranda_tavan_cevresi_m", None), ("tavan_m2", None)]
    for k, _ in cift:
        if eski[k] != g[k]:
            sorun.append(f"{k}: {eski[k]} / {g[k]}")
    if not yakin(eski["dis"]["cevre_m"], g["dis"]["cevre_m"]) or not yakin(eski["dis"]["cevre_m"] * 2.7, g["dis"]["duvar_m2"]):
        sorun.append(f"dış çevre: {eski['dis']['cevre_m']} / {g['dis']['cevre_m']} · brüt {g['dis']['duvar_m2']}")
    for k in ("kolon_kiris", "alin_m2", "karkas_mm"):
        if eski["dis"][k] != g["dis"][k]:
            sorun.append(f"dis.{k}: {eski['dis'][k]} / {g['dis'][k]}")
    if sorted((b["ad"], b["adet"], b["en"], b["boy"]) for b in eski["dis"]["bosluklar"]) != sorted((b["ad"], b["adet"], b["en"], b["boy"]) for b in g["dis"]["bosluklar"]):
        sorun.append(f"dış boşluklar: {eski['dis']['bosluklar']} / {g['dis']['bosluklar']}")
    for k in ("dis", "ic", "dikme", "kiris"):
        e, n = eski["celik"][k], g["celik"][k]
        if any(e[a] != n.get(a) for a in e if a != "not"):
            sorun.append(f"celik.{k}: {e} / {n}")
    for k in ("tip", "profil", "plan_m2", "oturum_m2"):
        if eski["celik"]["cati"][k] != g["celik"]["cati"].get(k):
            sorun.append(f"celik.cati.{k}: {eski['celik']['cati'][k]} / {g['celik']['cati'].get(k)}")
    for k in ("tavan_paneli_m2", "cati_paneli_m2"):
        if eski["celik"][k] != g["celik"][k]:
            sorun.append(f"celik.{k}: {eski['celik'][k]} / {g['celik'][k]}")
    for k in ("tip", "yontem", "kaplama", "egim", "yuzey_m2", "sacak_boyu_toplam_m", "cephe_kenarlari_m", "kose_adedi", "mahya_hatti_m", "bina_eni_m", "cati_boyu_m",
              "sacak_alti", "sacak_alti_eni_m", "sacak_yuzu_m2"):
        if eski["cati"][k] != g["cati"].get(k):
            sorun.append(f"cati.{k}: {eski['cati'][k]} / {g['cati'].get(k)}")
    if sorted(eski["cati"]["sacak_kenarlari_m"]) != sorted(g["cati"]["sacak_kenarlari_m"]):
        sorun.append(f"cati.sacak_kenarlari_m: {eski['cati']['sacak_kenarlari_m']} / {g['cati']['sacak_kenarlari_m']}")
    eo, no = eski["osb_takviye"], g.get("osb_takviye")
    if not no or [(x["mahal"], x["boy_m"], x["bosluk_m2"]) for x in eo["duvarlar"]] != [(x["mahal"], x["boy_m"], x["bosluk_m2"]) for x in no["duvarlar"]] \
            or (eo["brut_m2"], eo["net_m2"]) != (no["brut_m2"], no["net_m2"]):
        sorun.append(f"osb_takviye: {eo} / {no}")
    # aşık boyu (yöntem B'de kullanılır): eski kural halkalarla, genel motor yüz yüz sıralarla
    eski_asik = sum(2 * ((11.54 - 2 * i * 0.6 / math.sqrt(1 + 0.33 ** 2)) + (8.10 - 2 * i * 0.6 / math.sqrt(1 + 0.33 ** 2))) for i in range(8)) + 2 * (11.54 - 8.10)
    if not yakin(eski_asik, m["cati"]["asik_boyu_m"], 0.02):
        sorun.append(f"aşık boyu: {eski_asik:.2f} / {m['cati']['asik_boyu_m']:.2f}")
    # 2) yükleme listesi: baz (yöntem A) ve öteki panel kaplaması; satır satır
    with tempfile.TemporaryDirectory() as td:
        gy = Path(td) / "girdi.json"
        gy.write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
        for kaplama, eski_ad in ((None, "C8201_yukleme_taslak.json"), ("sandvic_panel", "C8201_kaplama_sandvic_panel.json")):
            cy = Path(td) / "cikti.json"
            komut = [sys.executable, str(YUKLEME / "yukleme.py"), str(gy), "--cikti", str(cy)] + (["--kaplama", kaplama] if kaplama else [])
            r = subprocess.run(komut, capture_output=True, text=True)
            if r.returncode != 0:
                sorun.append(f"yukleme.py koşmadı ({kaplama}): {r.stderr[-300:]}")
                continue
            yeni = json.loads(cy.read_text(encoding="utf-8"))["satirlar"]
            esk = json.loads((YUKLEME / "sonuc" / eski_ad).read_text(encoding="utf-8"))["satirlar"]
            anahtar = lambda s: (s["grup"], s["kalem"], s["boyut"], s["adet"], None if s["kg"] is None else round(s["kg"]))
            if [anahtar(s) for s in esk] != [anahtar(s) for s in yeni]:
                a, b = [anahtar(s) for s in esk], [anahtar(s) for s in yeni]
                for x in a:
                    if x not in b:
                        sorun.append(f"liste ({eski_ad}) 0.4'te var, genelde yok ya da farklı: {x}")
                for x in b:
                    if x not in a:
                        sorun.append(f"liste ({eski_ad}) genelde var, 0.4'te yok ya da farklı: {x}")
                if sorted(map(str, a)) == sorted(map(str, b)):
                    sorun.append(f"liste ({eski_ad}): satırlar aynı, sıra farklı")
    # 3) genel dizilim ↔ eski kırma dizilimi
    def kirma(px, py, egim):
        y0 = py / 2
        f = lambda ad, plan, yuk, sac: {"ad": ad, "plan": plan, "yukari": yuk, "egim": egim, "sacak_kotu": 280.0, "sacak": sac}
        return [f("ön", [[0, 0], [px, 0], [px - y0, y0], [y0, y0]], [0, 1], {"y": 0}), f("sol", [[0, py], [0, 0], [y0, y0]], [1, 0], {"x": 0}),
                f("arka", [[px, py], [0, py], [y0, y0], [px - y0, y0]], [0, -1], {"y": py}), f("sağ", [[px, 0], [px, py], [px - y0, y0]], [-1, 0], {"x": px})]
    deneme = fark = 0
    for (px, py), egim, kap, ek in itertools.product([(1154, 810), (1000, 1000), (1260, 640), (900, 700), (1432, 868), (1154, 813), (2010, 915)], [0.33, 0.25, 0.4],
                                                     [100, 87, 80, 110], [0, 1, 2, 3, 10]):
        dz = [cati_genel.duzlem_kur(d) for d in kirma(px, py, egim)]
        kn = cati_genel.kenarlari_bul(dz)
        boy = math.ceil((py / 2 * math.sqrt(1 + egim ** 2) + 5) * 10 - 1e-9) / 10 + ek
        for paylas in (True, False):
            a = cati_genel.dizilim(dz, kn, kap, 5.0, 0.5, paylas, boylar=[boy])["adet"]
            b = cati_acilim.dizilim(px / 100, py / 100, egim, kap / 100, boy / 100, paylas, "sol", 0.005, 0.05)["adet"]
            deneme += 1
            if a != b:
                fark += 1
                if fark <= 5:
                    sorun.append(f"dizilim farkı: plan {px} × {py}, eğim {egim}, kapatma {kap}, boy {boy}, paylaş {paylas}: genel {a} / kırma {b}")
    print(f"Ç8201 (0.5) ↔ 0.4: metraj, iki yükleme listesi satır satır; genel dizilim ↔ kırma dizilimi {deneme} deneme")
    for s in sorun:
        print("  SORUN:", s)
    print("toplam sorun", len(sorun))
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main())
