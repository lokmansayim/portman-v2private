#!/usr/bin/env python3
"""Yapı Tanımı taslağından (deneme/2026-10-02_celik) yükleme listesi girdisi üretir.

Geometriden gelenler: dış çevre, oda iç çevreleri, oda oda boşluklar, tavan alanları, çatı planı ve uzunlukları.
Varsayımlar girdinin içinde `varsayimlar` altında yazılıdır.

Kullanım:
    python girdi_uret.py ../2026-10-02_celik/C8201.json
    python girdi_uret.py ../2026-10-02_celik/C8201.json --secenek ../2026-10-02_celik/secenekler/dis_karkas_140.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
CELIK = BURADA.parent / "2026-10-02_celik"
sys.path.insert(0, str(CELIK))
from ciz import aciklik_kutusu, hesapla, karkas_mm, secenek_uygula  # noqa: E402
from gorunus import cati_hesapla  # noqa: E402

ISLAK = ("banyo", "wc", "duş")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--secenek", type=Path, action="append", default=[])
    ap.add_argument("--cikti", type=Path, default=BURADA / "sonuc")
    a = ap.parse_args()
    tanim = json.loads(a.tanim.read_text(encoding="utf-8"))
    tanim, sek = secenek_uygula(tanim, a.secenek)
    tipler = json.loads((CELIK / "duvar_tipleri.json").read_text(encoding="utf-8"))
    kur = json.loads((BURADA / "kurallar.json").read_text(encoding="utf-8"))
    s = hesapla(tanim, tipler, False)
    c = cati_hesapla(tanim)
    td, ti = s["td"], s["ti"]
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    dk = kur["kapi_boslugu_m"]["dis"]["deger"]
    ik = kur["kapi_boslugu_m"]["ic"]["deger"]

    def alan(ac):          # boşluk alanı, m²
        if ac["tur"] == "pencere":
            return ac["en"] * ac["yuk"] / 1e4
        if ac["tur"] == "dis_kapi":
            return dk[0] * dk[1]
        return ac["en"] / 100 * ik[1]

    # dış boşluklar (adlarına göre gruplanır)
    dis = {}
    for ac in tanim["acikliklar"]:
        if not ac["duvar"].startswith("dis:"):
            continue
        if ac["tur"] == "pencere":
            ad, en, boy = f"{ac['en']}/{ac['yuk']}", ac["en"] / 100, ac["yuk"] / 100
        else:
            ad, en, boy = "dış kapı", dk[0], dk[1]
        dis.setdefault(ad, {"ad": ad, "adet": 0, "en": en, "boy": boy})["adet"] += 1
    # odalar: iç çevre ve o odaya bakan boşluklar
    odalar = []
    for m in s["mahaller"]:
        bos = []
        for ac in tanim["acikliklar"]:
            if aciklik_kutusu(ac, tanim, td, ti).buffer(0.5).intersects(m["poligon"]):
                bos.append(round(alan(ac), 4))
        odalar.append({"ad": m["ad"], "tur": "yesil" if any(x in m["ad"].lower() for x in ISLAK) else "beyaz",
                       "cevre_m": round(m["poligon"].length / 100, 3), "alan_m2": round(m["alan_m2"], 3), "bosluk_m2": bos})
    v = tanim.get("veranda")
    kolon = v.get("kolon", {}) if v else {}
    veranda_m2 = v["en"] * v["boy"] / 1e4 if v else 0.0
    px, py = c["plan"][0] / 100, c["plan"][1] / 100
    kok = math.sqrt(1 + c["egim"] ** 2)
    girdi = {
        "sema": "portman.yukleme_girdisi/0.1-taslak",
        "ad": f"{tanim['kod']} · {tanim['ad']} · paket: {tanim['paket']}",
        "kaynak": f"deneme/2026-10-02_celik/{a.tanim.name}" + ("" if not a.secenek else " + " + ", ".join(x.name for x in a.secenek)),
        "bina_m2": round(s["toplam_oturum_m2"]),
        "kat_yuksekligi_m": tanim["duvar_yuksekligi"] / 100,
        "dis": {
            "cevre_m": 2 * (W + H) / 100, "duvar_kalinligi_m": td / 100, "karkas_mm": int(karkas_mm(tipler, tanim["dis_duvar_tipi"])),
            "kolon_kiris": ([{"ad": "veranda kolonu", "adet": kolon.get("adet", 0), "cevre_m": 0.76, "boy_m": 2.4},
                             {"ad": "veranda kirişi", "adet": 1, "cevre_m": 0.68, "boy_m": round((v["boy"] + 2 * v["en"]) / 100, 2)}] if v else []),
            "kolon_kiris_varsayim": bool(v),
            "alin_m2": [],
            "bosluklar": list(dis.values()),
        },
        "odalar": odalar,
        "ic_kapi_adedi": sum(1 for ac in tanim["acikliklar"] if ac["tur"] == "ic_kapi"),
        "tavan_m2": {"beyaz": round(sum(o["alan_m2"] for o in odalar if o["tur"] == "beyaz"), 2),
                     "yesil": round(sum(o["alan_m2"] for o in odalar if o["tur"] == "yesil") + veranda_m2, 2)},
        "cati": {
            "tip": "kirma", "ortu": "sandvic_panel", "egim": c["egim"], "plan_m": [px, py],
            "yuzey_m2": round(c["yuzey_m2"], 2), "sacak_kenarlari_m": [px, py, px, py], "sacak_boyu_toplam_m": round(2 * (px + py), 2),
            "mahya_hatti_m": round(c["mahya_hatti_toplam"] / 100, 2),
            "panel_boyu_m": math.ceil(min(px, py) / 2 * kok * 10 - 1e-9) / 10,
            "bina_eni_m": min(c["ayak_izi"]) / 100, "cati_boyu_m": max(px, py),
            "sacak_alti": "boardex", "sacak_omegasi": "Geniş saçak omegası (180 × 2500)",
        },
        "kapi_pencere": (
            [{"kalem": "Melamin kapı (80'lik kanat)", "boyut": "90 × 214", "adet": sum(1 for ac in tanim["acikliklar"] if ac["tur"] == "ic_kapi" and ac["en"] >= 90), "durum": "model"}]
            + ([{"kalem": "Melamin kapı (çizimde 80 cm; listelerde bütün iç kapılar 90 × 214)", "boyut": "soru", "adet": n80, "durum": "soru"}]
               if (n80 := sum(1 for ac in tanim["acikliklar"] if ac["tur"] == "ic_kapi" and ac["en"] < 90)) else [])
            + [{"kalem": "Kompozit çelik kapı", "boyut": "90 × 210", "adet": sum(1 for ac in tanim["acikliklar"] if ac["tur"] == "dis_kapi"), "durum": "model"}]
            + [{"kalem": ("PVC vasistas" if x["ad"] == "60/40" else "PVC pencere"), "boyut": x["ad"], "adet": x["adet"], "durum": "model"} for x in dis.values() if x["ad"] != "dış kapı"]
        ),
        "varsayimlar": [
            "Çatı örtüsü sandviç panel alındı (Lokman, 2 Ekim 22:05: makasların üzerine 8 cm çatı paneli gelir); panel boyu eğimli boydan, 10 cm'ye yuvarlandı.",
            "Veranda kolonu ve kirişi Boardex'le kaplanır sayıldı; kolon çevresi 0,76 m × 2,40 m ve kiriş çevresi 0,68 m gerçek listelerdeki değerlerdir; kiriş boyu verandanın üç kenarı.",
            "Yeşil tavan = ıslak hacim + veranda tavanı (iki gerçek listeden çıkarım).",
            "Saçak altı Boardex ve geniş saçak omegası alındı (62 m² kırma çatılı listedeki gibi).",
            "İç kapı boşluğu çizimdeki genişlik × 2,14 m; dış kapı 0,95 × 2,10 m (çalışma kitabındaki değerler).",
            "İniş sayısı 7 alındı (iki gerçek listede de 7).",
        ],
    }
    a.cikti.mkdir(parents=True, exist_ok=True)
    yol = a.cikti / f"{tanim['kod'].replace('Ç', 'C')}{sek}_girdi.json"
    yol.write_text(json.dumps(girdi, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı:", yol.name)
    for o in odalar:
        print(f"  {o['ad']:15s} {o['tur']:6s} çevre {o['cevre_m']:6.2f} m  alan {o['alan_m2']:6.2f} m²  boşluk {sum(o['bosluk_m2']):5.2f} m² ({len(o['bosluk_m2'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
