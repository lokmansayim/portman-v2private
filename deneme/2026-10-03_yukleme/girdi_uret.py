#!/usr/bin/env python3
"""Yapı Tanımı taslağından (deneme/2026-10-02_celik) yükleme listesi girdisi üretir.

Geometriden gelenler: dış çevre, iç duvar boyu, oda iç çevreleri, oda oda boşluklar, tavan alanları, çatı planı ve uzunlukları,
veranda çerçevesi (dikme ve kiriş), dere inişlerinin yeri. Varsayımlar girdinin içinde `varsayimlar` altında yazılıdır.

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
from ciz import aciklik_kutusu, bosluk_m2, hesapla, karkas_mm, secenek_uygula, veranda_cercevesi  # noqa: E402
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
    c = cati_hesapla(tanim, kur["inis"]["deger"]["orta_inis_esigi_m"] * 100)
    td, ti = s["td"], s["ti"]
    W, H = tanim["kapali"]["en"], tanim["kapali"]["boy"]
    dk = kur["kapi_boslugu_m"]["dis"]["deger"]
    ik = kur["kapi_boslugu_m"]["ic"]["deger"]
    ct = tanim["cati"]

    def alan(ac):          # boşluk alanı, m²
        if ac["tur"] == "ic_kapi" and [ac["en"] / 100, ac["yuk"] / 100] != ik:
            raise SystemExit(f"İç kapı boşluğu kuraldan farklı ({ik}): {ac}")
        if ac["tur"] == "dis_kapi" and [x / 100 for x in ac.get("bosluk", [])] != dk:
            raise SystemExit(f"Dış kapı boşluğu çalışma kitabındaki değerden farklı ({dk}): {ac}")
        return bosluk_m2(ac)

    # dış boşluklar (adlarına göre gruplanır)
    dis = {}
    for ac in tanim["acikliklar"]:
        if not ac["duvar"].startswith("dis:"):
            continue
        alan(ac)
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
    h = tanim["duvar_yuksekligi"] / 100
    v = tanim.get("veranda")
    vc = veranda_cercevesi(tanim)
    vk = kur["veranda_cercevesi"]["deger"]
    if vc and (vc["sirt"] * 10 != vk["sirt_mm"] or vc["genislik"] != vk["genislik_cm"] or vc["dikme_boyu"] != vk["dikme_boyu_cm"]):
        raise SystemExit("Veranda çerçevesi kuraldaki ölçülerden farklı.")
    veranda_m2 = v["en"] * v["boy"] / 1e4 if v else 0.0
    px, py = c["plan"][0] / 100, c["plan"][1] / 100
    L, Hc = c["cephe"][0] / 100, c["cephe"][1] / 100
    kok = math.sqrt(1 + c["egim"] ** 2)
    karkas = int(karkas_mm(tipler, tanim["dis_duvar_tipi"]))
    # iç duvar boyu: iç duvarların birleşimi (kesişmeler bir kez), dış duvarların iç yüzü arasında
    ic_boy = s["ic_duvarlar"].area / ti / 100
    # çelik: profil ve panel adedi
    ev = kur["celik"]["et_kalinligi_varsayilan"]["deger"]
    en_cok = kur["celik"]["panel_boyu_en_cok_m"]["deger"]
    dis_profil = f"{karkas}x45x{ev['dis_80' if karkas == 80 else 'dis_140']}"
    ic_profil = f"80x45x{ev['ic_dis80' if karkas == 80 else 'ic_dis140']}"
    dis_panel = sum(math.ceil(x / 100 / en_cok - 1e-9) for x in (W, H, W, H))
    ic_panel = sum(math.ceil((d["son"] - d["bas"]) / 100 / en_cok - 1e-9) for d in tanim["ic_duvarlar"])
    et_notu = "et kalınlığı ve panel adedi tahmin; teyit bekliyor"
    # OSB takviyesi: salon ve mutfağın bulunduğu mahal(ler)in bütün duvar yüzeyi
    anahtarlar = kur["osb_takviye"]["deger"]["oda_anahtarlari"]
    takviye = [o for o in odalar if any(x in o["ad"].lower() for x in anahtarlar)]
    ic_kapi = [ac for ac in tanim["acikliklar"] if ac["tur"] == "ic_kapi"]
    kanat = ic_kapi[0]["kanat"] if ic_kapi else [80, 200]
    yontem = ct.get("yontem", "omega_asik")
    girdi = {
        "sema": "portman.yukleme_girdisi/0.2-taslak",
        "ad": f"{tanim['kod']} · {tanim['ad']} · paket: {tanim['paket']}",
        "kaynak": f"deneme/2026-10-02_celik/{a.tanim.name}" + ("" if not a.secenek else " + " + ", ".join(x.name for x in a.secenek)),
        "bina_m2": round(s["toplam_oturum_m2"]),
        "dis_olcu_m": [L, Hc],
        "kat_adedi": 1,
        "oda_sayisi": len(odalar),
        "kat_yuksekligi_m": h,
        "celik": {
            "dis": {"profil": dis_profil, "boy_m": round(2 * (W + H) / 100, 2), "panel_adedi": dis_panel, "not": et_notu},
            "ic": {"profil": ic_profil, "boy_m": round(ic_boy, 2), "panel_adedi": ic_panel, "not": et_notu},
            "dikme": ({"profil": f"80x45x{ev['dikme']}", "adet": vc["dikme_adedi"], "boy_m": vc["dikme_boyu"] / 100,
                       "not": "dikme sayısı ve yeri katalog görsellerinden"} if vc else None),
            "kiris": ({"profil": f"80x45x{ev['kiris']}", "boy_m": round(vc["kiris_boyu"] / 100, 2)} if vc else None),
            "cati": {"tip": ct["tip"], "profil": f"80x45x{ev['cati']}", "plan_m2": round(c["plan_m2"], 2)},
            "tavan_paneli_m2": round(s["kapali_net_m2"] + veranda_m2, 2) if yontem == "panel" else None,
            "cati_paneli_m2": round(c["yuzey_m2"], 2) if yontem == "panel" else None,
        },
        "dis": {
            "cevre_m": 2 * (W + H) / 100, "duvar_kalinligi_m": td / 100, "karkas_mm": karkas,
            "kolon_kiris": ([{"ad": "veranda dikmesi", "adet": vc["dikme_adedi"], "cevre_m": vk["dikme_kaplama_cevresi_m"], "boy_m": vc["dikme_boyu"] / 100},
                             {"ad": "veranda kirişi", "adet": 1, "cevre_m": vk["kiris_kaplama_cevresi_m"], "boy_m": round(vc["kiris_boyu"] / 100, 2)}] if vc else []),
            "kolon_kiris_varsayim": False,
            "alin_m2": [],
            "bosluklar": list(dis.values()),
        },
        "odalar": odalar,
        "ic_kapi_adedi": len(ic_kapi),
        "ic_duvar_boyu_m": round(ic_boy, 2),
        "osb_takviye": ({"odalar": [o["ad"] for o in takviye],
                         "net_m2": round(sum(o["cevre_m"] * h - sum(o["bosluk_m2"]) for o in takviye), 2)} if takviye else None),
        "tavan_m2": {"beyaz": round(sum(o["alan_m2"] for o in odalar if o["tur"] == "beyaz"), 2),
                     "yesil": round(sum(o["alan_m2"] for o in odalar if o["tur"] == "yesil") + veranda_m2, 2)},
        "cati": {
            "tip": ct["tip"], "yontem": yontem, "kaplama": ct.get("kaplama", "sandvic_panel"), "egim": c["egim"], "plan_m": [px, py],
            "yuzey_m2": round(c["yuzey_m2"], 2), "sacak_kenarlari_m": [px, py, px, py], "sacak_boyu_toplam_m": round(2 * (px + py), 2),
            "cephe_kenarlari_m": [L, Hc, L, Hc], "kose_adedi": 4,
            "mahya_hatti_m": round(c["mahya_hatti_toplam"] / 100, 2),
            "panel_boyu_m": math.ceil(min(px, py) / 2 * kok * 10 - 1e-9) / 10,
            "bina_eni_m": min(c["ayak_izi"]) / 100, "cati_boyu_m": max(px, py),
            "sacak_alti": ct.get("sacak_alti", "boardex"), "sacak_alti_eni_m": ct["sacak"] / 100,
            "sacak_yuzu_m2": round(c["alin_m2"], 2) if yontem == "panel" else None,
        },
        "kapi_pencere": (
            [{"kalem": f"Melamin kapı ({kanat[0]}'lik kanat)", "boyut": f"{round(ik[0] * 100)} × {round(ik[1] * 100)}", "adet": len(ic_kapi),
              "durum": "lokman", "formul": "iç kapı sayısı; boşluk 90 × 214, kanat 200 cm: Lokman, 3 Ekim 13:27; kalemin adı ve 80'lik kanat listelerden"}]
            + [{"kalem": "Kompozit çelik kapı", "boyut": "90 × 210", "adet": sum(1 for ac in tanim["acikliklar"] if ac["tur"] == "dis_kapi"), "durum": "model",
                "formul": "dış kapı sayısı; ölçü gerçek listelerden"}]
            + [{"kalem": ("PVC vasistas" if x["ad"] == "60/40" else "PVC pencere"), "boyut": x["ad"], "adet": x["adet"], "durum": "model"} for x in dis.values() if x["ad"] != "dış kapı"]
        ),
        "varsayimlar": [
            "Çatı kaplaması seçenektir; baz paketin kaplaması söylenmedi. Örnek olarak sandviç panel alındı; `--kaplama` ile öteki seçenekler hesaplanır. Panel boyu eğimli boydan, 10 cm'ye yuvarlandı.",
            "Çelik et kalınlığı gerçek listelerden çıkarıldı: 80 mm dış karkasta duvarlar 1,2 mm; 140 mm dış karkasta dış ve iç duvarlar 0,8 mm. Teyit bekliyor.",
            f"Duvar paneli adedi tahmin: her duvar hattı bir panel, {str(en_cok).replace('.', ',')} m'yi aşarsa bölünür. Gerçek adet karkas yerleşiminden gelir.",
            "Veranda dikmelerinin sayısı ve yeri katalog görsellerinden: dış kenarda iki köşe ve bir orta.",
            "Saçak yüzü (saçak ucunda topuk + panel, 18,4 cm) Boardex'le kaplanır sayıldı; kaplandığını Lokman söyledi, malzemesini söylemedi.",
            "OSB takviyesi: salon ve mutfak aynı mahalde (Yaşam Alanı) olduğu için o mahalin bütün duvar yüzeyi alındı.",
            "Dış kapı boşluğu 0,95 × 2,10 m (çalışma kitaplarındaki değer); katalog çiziminde kapı 100 cm.",
            "Elektrik paftası yok: duy, glop, anahtar, priz ve sigorta sayıları hesaplanmadı.",
        ],
    }
    a.cikti.mkdir(parents=True, exist_ok=True)
    yol = a.cikti / f"{tanim['kod'].replace('Ç', 'C')}{sek}_girdi.json"
    yol.write_text(json.dumps(girdi, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı:", yol.name)
    for o in odalar:
        print(f"  {o['ad']:15s} {o['tur']:6s} çevre {o['cevre_m']:6.2f} m  alan {o['alan_m2']:6.2f} m²  boşluk {sum(o['bosluk_m2']):5.2f} m² ({len(o['bosluk_m2'])})")
    print(f"  dış çevre {girdi['dis']['cevre_m']:.2f} m · iç duvar boyu {ic_boy:.2f} m · profil dış {dis_profil} / iç {ic_profil} · panel (tahmin) dış {dis_panel} / iç {ic_panel}")
    if girdi["osb_takviye"]:
        print(f"  OSB takviyesi: {', '.join(girdi['osb_takviye']['odalar'])} net {girdi['osb_takviye']['net_m2']:.2f} m²")
    return 0


if __name__ == "__main__":
    sys.exit(main())
