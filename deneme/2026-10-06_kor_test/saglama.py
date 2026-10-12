#!/usr/bin/env python3
"""Genel motorun sağlaması: Ç8201, Yapı Tanımı 0.5 ile (`C8201_05.json`) genel hattan geçirilir ve 0.4 hattının kayıtlı sonuçlarıyla
(`../2026-10-02_celik/sonuc`, `../2026-10-03_yukleme/sonuc`) karşılaştırılır. Ayrıca genel kaplama dizilimi, rastgele dikdörtgen kırma
çatılarda eski dizilimle (`cati_acilim.dizilim`) karşılaştırılır. Panel boyu kuralı (yukarı yuvarlama, uzatma ve pay koşulu) iki motorda ayrı ayrı
kuruludur; rastgele kırma çatılarda genel motorun seçtiği boy, adet ve uzatmanın nedeni kırma motorununkiyle (`cati_acilim.kural_dizilimi`)
karşılaştırılır. Fark varsa çıkış kodu 1.

Eylül 2026 katmanının (`yukleme.py --sablon 2026`) değişmezleri de burada denetlenir (bütün örnek girdilerde, Ç8201'de ve kör test girdilerinde):
varsayılan hesapta `sablon` durumlu satır yoktur ve varsayılan hesap katman kurallardan silinse de aynı listeyi verir; katmanla hesaplanan listede
varsayılandan farklı olan her satır `sablon`dur, `sablon` olan her satır da gerçekten farklıdır. Geçici dosya yazılmaz; komutla koşulunca özet
`sonuc/saglama.json`a yazılır (şartname belgesi deneme sayılarını oradan okur).

Karşılaştırılanlar: mahal alanı, çevresi, köşeleri ve boşlukları; dış çevre ve boşluklar; iç duvar boyu; çatı yüzeyi, saçak, mahya hattı,
aşık sıraları, kaplama adedi ve boyu; yükleme listesinin bütün satırları (kalem, boyut, adet, kg). Bilinen fark: genel motor mahyanın iki yanına
ayrıca mahya aşığı eklemez (6 Ekim 2026 kıyası; aşık yalnız yöntem B'dedir, karşılaştırılan iki liste yöntem A).

Kullanım:
    python saglama.py
"""
from __future__ import annotations

import copy
import itertools
import json
import math
import random
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent
YUKLEME = BURADA.parent / "2026-10-03_yukleme"
sys.path.insert(0, str(YUKLEME))
import cati_acilim  # noqa: E402
import yukleme  # noqa: E402
import cati_genel  # noqa: E402
import girdi_genel  # noqa: E402
import kurallar_oku  # noqa: E402
import yapi  # noqa: E402


def yakin(a, b, tol=0.006):
    return abs(a - b) <= tol


def main(ozet_yolu: Path | None = None) -> int:
    sorun: list[str] = []
    kur = kurallar_oku.oku()
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
    # aşık boyu (yöntem B'de kullanılır): eski kural halkalarla, genel motor yüz yüz sıralarla. Sıralar aynıdır (8 halka = her yüzde 8 sıra).
    # Bilinen fark: eski kural mahyanın iki yanına ayrıca birer mahya aşığı ekler (2 × 3,44 m); genel motor, kör test projesinin aşık paftasındaki
    # gibi, son sıra ile mahya arasında 30 cm'den fazla boşluk yoksa eklemez (Ç8201'de boşluk 6,5 cm).
    halkalar = sum(2 * ((11.54 - 2 * i * 0.6 / math.sqrt(1 + 0.33 ** 2)) + (8.10 - 2 * i * 0.6 / math.sqrt(1 + 0.33 ** 2))) for i in range(8))
    if not yakin(halkalar, m["cati"]["asik_boyu_m"], 0.02):
        sorun.append(f"aşık boyu (halkalar): {halkalar:.2f} / {m['cati']['asik_boyu_m']:.2f}")
    # 2) yükleme listesi: baz (yöntem A) ve öteki panel kaplaması; satır satır
    for kaplama, eski_ad in ((None, "C8201_yukleme_taslak.json"), ("sandvic_panel", "C8201_kaplama_sandvic_panel.json")):
        gk = copy.deepcopy(g)
        if kaplama:
            gk["cati"]["kaplama"] = kaplama
        try:
            yeni = yukleme.hesapla(gk, kur)["satirlar"]
        except SystemExit as e:
            sorun.append(f"yükleme listesi hesaplanamadı ({kaplama}): {e}")
            continue
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
    # 3b) panel boyu kuralı iki motorda aynı mı: yukarı yuvarlama, uzatma (Lokman, 4 Ekim 2026 16:18) ve pay koşulu. Rastgele kırma çatılarda
    #     genel motorun (`girdi_genel._dizilim`) seçtiği boy, adet ve uzatmanın nedeni ↔ kırma motorununki (`cati_acilim.kural_dizilimi`).
    #     Kırma motoru dizilime kuraldaki yerden başlar; genel motor soldan. Kural `sol` değilse karşılaştırma yapılmaz (o gün yeniden kurulur).
    kural_deneme = kural_uzayan = kural_paydan = kural_fark = 0
    if kur["kirma_cati_dizilim"]["deger"]["baslangic"] == "sol":
        rnd = random.Random(20261007)
        yv_mm = (kur.get("panel_boyu_yuvarlama_mm") or {}).get("deger") or 1
        tasma_m = kur["cati_kaplama_tasma_m"]["deger"]
        for _ in range(50):
            px = round(rnd.uniform(6, 16), rnd.choice((1, 2)))
            py = round(rnd.uniform(4, px), rnd.choice((1, 2)))
            egim = rnd.choice((0.25, 0.30, 0.33, 0.40))
            dz = [cati_genel.duzlem_kur(d) for d in kirma(round(px * 100), round(py * 100), egim)]
            kn = cati_genel.kenarlari_bul(dz)
            taban = math.ceil((py / 2 * math.sqrt(1 + egim ** 2) + tasma_m) * 1000 / yv_mm - 1e-9) * yv_mm / 1000
            for kaplama in ("tek_kat_panel", "trapez_sac", "osb_kiremit"):
                kural_deneme += 1
                gn = girdi_genel._dizilim({"duzlemler": dz, "kenarlar": kn}, kur, kaplama)
                kr_ = cati_acilim.kural_dizilimi(kur, {"plan_m": [px, py], "egim": egim, "panel_boyu_m": taban, "panel_boyu_kaynak": "kural"}, kaplama)
                genel = (gn["adet"], [round(x * 10) for x in gn["boylar_cm"]], [u.get("neden", "var") for u in gn["uzatma"]],
                         gn["taban"]["adet"], [round(x * 10) for x in gn["taban"]["boylar"]])
                kirma_ = (kr_["adet"], [round(kr_["boy_m"] * 1000)], [kr_["uzatma"].get("neden", "var")] if kr_["uzatma"] else [],
                          kr_["taban_adet"], [round(kr_["taban_boy_m"] * 1000)])
                kural_uzayan += bool(kr_["uzatma"])
                kural_paydan += bool(kr_["uzatma"]) and kr_["uzatma"].get("neden") == "pay"
                if genel != kirma_:
                    kural_fark += 1
                    if kural_fark <= 5:
                        sorun.append(f"panel boyu kuralı iki motorda farklı: plan {px} × {py} m, eğim {egim}, {kaplama}: "
                                     f"genel (adet, boy mm, neden, taban adet, taban boy) {genel} / kırma {kirma_}")
    # 4) Eylül 2026 katmanının değişmezleri
    katmansiz = {a: v for a, v in kur.items() if a != "sablon_2026"}
    girdiler = [("genel Ç8201", g)]
    for yol in [YUKLEME / f"ornek_{n}m2_girdi.json" for n in (90, 62, 105)] + [YUKLEME / "sonuc" / "C8201_girdi.json", BURADA / "sonuc" / "KT01_girdi.json",
                                                                              BURADA / "sonuc" / "KT01_duzeltilmis_girdi.json"]:
        if yol.exists():
            girdiler.append((yol.name, json.loads(yol.read_text(encoding="utf-8"))))
    oz = lambda x: (x["grup"], x["kalem"], x["boyut"], x["adet"], x["olcu"], x["brut"], x["birim"], x["kg"], x["formul"])
    for ad, gi in girdiler:
        v = yukleme.hesapla(copy.deepcopy(gi), kur)
        if any(x["durum"] == yukleme.SABLON for x in v["satirlar"]):
            sorun.append(f"katman ({ad}): varsayılan hesapta `sablon` durumlu satır var")
        try:
            v0 = yukleme.hesapla(copy.deepcopy(gi), katmansiz)
            fark = [(x["kalem"], y_["kalem"]) for x, y_ in zip(v["satirlar"], v0["satirlar"]) if (oz(x), x["durum"]) != (oz(y_), y_["durum"])]
            if fark or len(v["satirlar"]) != len(v0["satirlar"]):
                sorun.append(f"katman ({ad}): varsayılan hesap, katman kurallardan silinince değişiyor: {fark[:3]}")
        except (KeyError, SystemExit) as e:
            sorun.append(f"katman ({ad}): varsayılan hesap katman olmadan çalışmıyor: {e!r}")
        gs = copy.deepcopy(gi)
        gs["sablon"] = "2026"
        k_ = yukleme.hesapla(gs, kur)
        taban = [oz(x) for x in v["satirlar"]]
        for x in k_["satirlar"]:
            farkli = oz(x) not in taban
            if farkli != (x["durum"] == yukleme.SABLON):
                sorun.append(f"katman ({ad}): {x['kalem']} {'farklı ama `sablon` değil' if farkli else '`sablon` ama varsayılandakiyle aynı'}")
    print(f"Ç8201 (0.5) ↔ 0.4: metraj, iki yükleme listesi satır satır; genel dizilim ↔ kırma dizilimi {deneme} deneme; "
          f"panel boyu kuralı iki motorda {kural_deneme} çatı ve kaplamada ({kural_uzayan} tanesinde boy uzadı); "
          f"Eylül 2026 katmanının değişmezleri {len(girdiler)} girdide")
    for s in sorun:
        print("  SORUN:", s)
    print("toplam sorun", len(sorun))
    if ozet_yolu:       # belge bu dosyadan okur (elle yazılmasın diye): hangi kural setiyle, kaç deneme, kaç uzatma
        ozet = {"kural_seti": kur.get("sema"), "dizilim_denemesi": deneme, "kural_denemesi": kural_deneme, "kural_uzayan": kural_uzayan,
                "kural_pay_kosulundan": kural_paydan, "katman_girdisi": len(girdiler), "sorun": len(sorun)}
        ozet_yolu.write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if sorun else 0


if __name__ == "__main__":
    sys.exit(main(BURADA / "sonuc" / "saglama.json"))
