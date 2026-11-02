"""62 m² rehberinin hedef örnek verisi (İE-18 R1, D-28 A1): onaylı 62 m² sayfasının girdisi (`kaynak.json`, 6b899b4'teki
`deneme/2026-10-25_rehber_62m2/rehber/data.json` aynen) ve o sayfanın `sahne.js` içinde sabit duran eve ait sayılar ve yazılar
(`metin.json` ve aşağıdaki sabitler) → tek şablonun (`araclar/paket/rehber/sahne.js`) verisi (`veri.json`).

Sabitler 62'nin sahne.js'inden aynen alındı; işlemler aynı sırayla yazıldı ki sayılar JS'tekiyle bit bit aynı çıksın
(şablon + bu veri = 62 m² sayfası, `testler/paket/test_rehber.py`). Tek bilinçli fark: dübelin adı "Çelik dübel" (karar
verilmiş kalem; `iz.json` aynı düzeltmeyle).

  python testler/paket/rehber62/donustur.py   → testler/paket/rehber62/veri.json
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

B = Path(__file__).resolve().parent


def R(k, ad, v, src):
    return [k, ad, v, src]


def I(ad, v):
    return ["-", ad, v]


def veri() -> dict:
    k = json.loads((B / "kaynak.json").read_text(encoding="utf-8"))
    mt = json.loads((B / "metin.json").read_text(encoding="utf-8"))
    d = copy.deepcopy(k)
    W, D = d["dis"]
    d["kod"] = "62m2"
    S = dict(alt=1, veranda=7, omega=8, makas=9, kalkan=10, tomega=11, alcipan=12, izo=13, asik=14, sacak=15, dere=16,
             tersmahya=17, kaplama=18, alin=19, dograma=20)
    d["N"], d["S"] = 20, S
    d["zemin"] = [-12, W + 12, -162, D + 12]
    d["fuga"] = {"bant": [38, 78, 118, 158, 198, 238],
                 "metin": "fugalı: alttan 6 × 38 cm + 2 cm fuga, üstte 10 cm bant (pafta: fugalı duvar detayı)"}
    d["renk"] = {}
    # Çatılar: ana beşik (y boyunca −30…630, mahya 300), cumba (x boyunca −30…604,75, mahya 287,375); iki mahya aynı yükseklikte
    d["R"] = {"AN": {"L": -30, "R": 630, "M": 300, "tan": 108.5 / 330},
              "CU": {"L": -30, "R": 604.75, "M": 287.375, "tan": 108.5 / 317.375}}
    d["sacak"] = [
        {"ad": "arka saçak", "o": "h", "face": 600, "out": 1, "a0": -30.2, "a1": 930.2, "f0": -30.2, "f1": 930.2, "t0": -1.1, "t1": 901.1, "R": "AN"},
        {"ad": "ön saçak (cumbanın sağı)", "o": "h", "face": 0, "out": -1, "a0": 604.95, "a1": 930.2, "f0": 604.95, "f1": 930.2, "t0": 604.95, "t1": 901.1, "R": "AN"},
        {"ad": "cumba sol saçağı", "o": "v", "face": 0, "out": -1, "a0": -180.2, "a1": -30.2, "f0": -180.2, "f1": -30.2, "t0": -151.1, "t1": -30.2, "R": "CU"},
        {"ad": "cumba sağ saçağı", "o": "v", "face": 574.75, "out": 1, "a0": -180.2, "a1": 0, "f0": -180.2, "f1": -30.2, "t0": -151.1, "t1": 0, "R": "CU"},
    ]
    d["kalkan"] = [
        {"ad": "sol kalkan (MKS01)", "r": -math.pi / 2, "O": [0, 0], "R": "AN", "p": -1, "uc": {"A": 30, "B": -630}, "sm": -300,
         "duvar": {"A": 0, "B": -600}, "altUc": {"A": False, "B": True}, "parca": [[-50, -300], [-300, -550]], "dolgu": [[0, -50], [-550, -600]]},
        {"ad": "sağ kalkan (MKS08)", "r": math.pi / 2, "O": [900, 0], "R": "AN", "p": 1, "uc": {"A": -30, "B": 630}, "sm": 300,
         "duvar": {"A": 0, "B": 600}, "altUc": {"A": True, "B": True}, "parca": [[50, 300], [300, 550]], "dolgu": [[0, 50], [550, 600]]},
        {"ad": "cumba kalkanı (MKS09)", "r": 0, "O": [0, -150], "R": "CU", "p": 1, "uc": {"A": -30, "B": 604.75}, "sm": 287.375,
         "duvar": {"A": 0, "B": 574.75}, "altUc": {"A": True, "B": True}, "parca": [[37.375, 287.375], [287.375, 537.375]],
         "dolgu": [[0, 37.375], [537.375, 574.75]]},
    ]

    def VSL(x):   # sol dere (vadi) hattı: (−30, −30) → (287,375; 300)
        return -30 + (x + 30) * (330 / 317.375)

    def VSR(x):   # sağ dere hattı: (604,75; −30) → (287,375; 300)
        return -30 + (604.75 - x) * (330 / 317.375)

    d["yuz"] = {
        "MB": {"ad": "ana çatı arka yüz", "E": [0, 630], "d": [0, -1], "R": "AN",
               "poly": [[-30.2, 300], [930.2, 300], [930.2, 631.3], [-30.2, 631.3]],
               "eksen": "x", "hadve": "RX", "serit": {"ad": 350, "bas": -30.2, "son": 930.2, "yon": 1}},
        "MFR": {"ad": "ana çatı ön yüz (cumbanın sağı)", "E": [0, -30], "d": [0, 1], "R": "AN",
                "poly": [[604.75 + 1.3 * 317.375 / 330, -31.3], [930.2, -31.3], [930.2, 300], [287.375, 300]],
                "dere": [[604.75, -30], [287.375, 300]], "dere_yan": "sağ",
                "eksen": "x", "hadve": "RX", "serit": {"ad": 350, "bas": 930.2, "son": 287.375, "yon": -1}},
        "MFL": {"ad": "ana çatı ön yüz (cumbanın solu)", "E": [0, -30], "d": [0, 1], "R": "AN",
                "poly": [[-30.2, VSL(-30.2)], [-30.2, 300], [287.375, 300]], "dere": [[-30, -30], [287.375, 300]], "dere_yan": "sol",
                "eksen": "x", "hadve": "RX", "serit": {"ad": 350, "bas": -30.2, "son": 287.375, "yon": 1}},
        "CL": {"ad": "cumba sol yüz", "E": [-30, 0], "d": [1, 0], "R": "CU",
               "poly": [[-31.3, -180.2], [287.375, -180.2], [287.375, 300], [-31.3, VSL(-31.3)]], "dere": [[-30, -30], [287.375, 300]],
               "dere_yan": "sol", "eksen": "y", "hadve": "RY", "serit": {"ad": 340, "bas": -180.2, "son": 300, "yon": 1}},
        "CR": {"ad": "cumba sağ yüz", "E": [604.75, 0], "d": [-1, 0], "R": "CU",
               "poly": [[287.375, -180.2], [606.05, -180.2], [606.05, VSR(606.05)], [287.375, 300]], "dere": [[604.75, -30], [287.375, 300]],
               "dere_yan": "sağ", "eksen": "y", "hadve": "RY", "serit": {"ad": 340, "bas": -180.2, "son": 300, "yon": 1}},
    }
    A = k["asik"]
    d["asik"] = {"yuzler": {
        "MB": {"sira": A["ana_sira"], "pafta": A["pafta"]["arka"], "bas": "max"},
        "MFR": {"sira": A["ana_sira"], "pafta": A["pafta"]["on_sag"], "bas": "max"},
        "MFL": {"sira": A["ana_sira"], "pafta": A["pafta"]["on_sol"], "bas": "min"},
        "CL": {"sira": A["cumba_sira"], "pafta": A["pafta"]["cumba"], "bas": "max"},
        "CR": {"sira": A["cumba_sira"], "pafta": A["pafta"]["cumba"], "bas": "min"},
    }}
    d["kaplama"] = {
        "profil": {"hadve": 2.7, "tepe": 4.2, "taban": 7.4, "kenar": 4.5, "kapatir": 100},   # trapez 27/200-6, 100 cm kapatır, 0,5 mm
        "hadve": {"RX": [-30.2 + 4.5 + i * (960.4 - 9) / 48 for i in range(49)],
                  "RY": [y for y in (-180.2 + 4.5 + i * 20 for i in range(25)) if y < 300]},
        "mahya": [{"R": "AN", "topR": "AN", "r": math.pi / 2, "O": [0, 0], "s0": 300, "z": [-30.2, 930.2], "ad": "ana mahya"},
                  {"R": "CU", "topR": "AN", "r": math.pi, "O": [287.375, 0], "s0": 0, "z": [-180.2, 300], "ad": "cumba mahyası"}],
        "metin": {"ad": "Trapez sac {ad} × 100", "kesim": "Trapez sac · kesim parçası", "say_onek": "Trapez sac",
                  "profil": "27/200-6: hadve 27 mm, adım 200 mm, tepe 42 / taban 74 mm; 6 hadve, 100 cm kapatır; 0,5 mm (Lokman)",
                  "dizilim": "modelde 100’lük levhayla; paftadaki dizilim 80’lik levhaya göre çizilmiş", "renk": "antrasit",
                  "liste": "TRAPEZ SAC 3500 · 21 adet, 3400 · 8 adet", "mahya_ad": "Trapez sac mahyası",
                  "mahya_liste": "TRAPEZ SAC MAHYASI L 800 · 25 adet; mahya bandı 4 rulo"},
    }
    CB = sorted(m["konum"] for m in k["makas"] if m["aile"] == "cumba")
    d["izo"] = {
        "ana": {"yon": "y", "bas": 10, "L": 580, "ad": "Çatı izolasyonu · 10 cm rulo cam yünü",
                "serme": "çatı kapanmadan önce, aşıkların arasından; rulo ön duvardan arka duvara açılır, tavanın (alçıpanın) üstüne serilir"},
        "ek": [{"x": 10, "y0": y0, "y1": y1, "L": 564.75 - 10, "ad": "Çatı izolasyonu · 10 cm rulo cam yünü (cumba)",
                "bu": f"cumba (veranda) · {yer} · {{w}} × {{L}} cm",
                "serme": "makas yönünde (yatay); rulo sol yan kirişten sağa açılır, veranda tavanının (boardex) üstüne serilir"}
               for y0, y1, yer in [(-140, CB[1] - 4.2, "MKS09–MKS10 arası"), (CB[1] + 4.2, 0, "MKS10 ile ön duvar arası")]],
    }
    d["tavan"] = {"tip": "ters", "boardex": [[10, 313.75, -140, 0], [323.75, 564.75, -140, 0]]}
    del d["veranda"], d["betopan"]
    v = k["veranda"]
    d["verandalar"] = [{
        "kolon": [{"rect": r, "order": i, "bu": f"veranda kolonu {['sol', 'orta', 'sağ'][i]} · 100 × 100 × 2400, 3 mm, flanşlı",
                   "liste": "KUTU PROFİL (KOLON) (FLANŞLI) (3 MM) · 3 adet"} for i, r in enumerate(v["kolon"])],
        "kiris": [{"rect": v["kiris_on"], "order": 3, "bu": "ön kiriş · L 574,75 · 4 mm (paftada B)", "liste": "ÖZEL KUTU PROFİL (KİRİŞ) (4 MM) - B · 1 adet"}]
        + [{"rect": r, "order": 4 + i, "bu": f"kiriş L 140 · {['sol: köşe direği A’ya', 'orta: özel H (C)’ya', 'sağ: özel H (C)’ya'][i]} bağlanır",
            "liste": "KUTU PROFİL (KİRİŞ) (4 MM) 100 × 100 × 1400 · 3 adet"} for i, r in enumerate(v["kiris"])],
    }]
    for p in d["posts"]:
        if p.get("id") == "FL":
            p["baglanti"] = {"gorev": "veranda sol kirişi buna bağlanır (kaynaklı detaylar paftasında A)", "liste": "ÖZEL KÖŞE DİREĞİ - A · 100 × 100 × 2500"}
    CATI_AN, CATI_CU = "ana beşik · eğim 18,2° · tepe 118,5 cm", "cumba · eğim 18,9° · mahya ana mahyayla aynı yükseklikte"
    for m in d["makas"]:
        if m["aile"] == "ana":
            m.update(R="AN", yon="y", wl=[2.7, 597.3], NB=9, T0=38.9, cati=CATI_AN)
        elif m["aile"] == "cumba":
            m.update(R="CU", yon="x", wl=[2.7, 572.05], NB=9, T0=38.86, cati=CATI_CU)
        else:
            m.update(R="CU", zR="AN", yon="x", nps=2 if m["ad"] == "MKS11" else 1, cati=CATI_CU)
    oda = mt["oda"]
    KAM = {"salon": 12.5, "yatak2": 9, "hol": 8, "banyo": 8, "yatak1": 8.5}
    for r in d["rooms"]:
        r.update(metin=oda[r["id"]], kamera=KAM[r["id"]])
        if r["id"] == "banyo":
            r["yesil"] = True
    for p in d["dere"]["inisler"]:
        if p["duvar"] == "veranda kolonu":
            p["sw"] = -145
        else:
            p["dis"] = 0
    d["pencere"] = {
        "120/120": {"kod": "P-01", "ad": None, "liste": "PVC DOĞRAMA … ÇİFT AÇILIM 120 × 120 · 2 adet", "tip": "acilir", "karkas": True},
        "120/80": {"kod": None, "ad": "PVC pencere 120/80 (sürgülü)", "liste": "PVC DOĞRAMA … SÜRGÜLÜ 120 × 80 · 1 adet", "tip": "surgulu", "karkas": True},
        "180/180": {"kod": None, "ad": "PVC pencere 180/180 (çift açılım)", "liste": "PVC DOĞRAMA … ÇİFT AÇILIM 180 × 180 · 2 adet", "tip": "b180", "karkas": True},
        "60/60": {"kod": None, "ad": "PVC vasistas 60/60", "liste": "PVC DOĞRAMA … VASİSTAS 60 × 60 · 1 adet", "tip": "vasistas", "karkas": False},
    }
    d["metin"] = {
        "alt_liste": {"dis": "100 × 3750 · 8 adet", "ic": "60 × 2500 · 7 adet"},
        "dis_kapi": "çelik kapı 90 × 200 (sağ)", "ic_kapi_boslugu": "Kapı boşluğu 82 × 200 (kasalı) · iç kapı alıcıya ait",
        "dvr_kaynak": "dış duvar görünüşü ve SketchUp modeli (DVR1/DVR2)",
        "ozel_h_liste": "ÖZEL H (DÜBELLİ) - C · 100 × 100 × 2500 · 2 adet",
        "dubel_ad": "Çelik dübel", "dubel_liste": "ÇELİK DÜBEL · 21 adet (dübelli H adedi kadar) + şase pul 21",
        "ceku_liste": "ÇEKTİRME U'SU (60 LIK) 60 × 2440 · 4 adet (2 yer + 2 yedek)",
        "omega_liste": {"sacak": "100 × 2500 · 7 adet (makas saçaklarının altı: 1525 cm)",
                        "duvar": "100 × 2500 · 4 adet (saçak ve baş makas omegası gelmeyen yerler)",
                        "bas": "L 2500 · 8 adet · fabrikada hazırlanır",
                        "ic": "60'LIK DUVAR OMEGASI 60 × 3750 · 36 adet (iç duvar üstleri ve ters tavan; listede toplam 127,64 m)"},
        "sacak_liste": "(ANTRASİT) SAÇAK SACI (30'LUK) 300 × 2500 · 8 adet (3 adedi menfezli)",
        "ara_ad": "Cumba ara makası", "ara_gorev": "cumba yüzlerinin dere (vadi) hattına kadar uzanan kısmını taşır",
        "makas_profil": 'C80 (listede "80X0.8") · 12 makas 314,9 kg', "makas_kaynak": "SketchUp modeli (yer, boy, yükseklik)",
        "betopan": {"dolgu": "makas ucu (iki betopanın dışında kalan üçgen)", "levha": "125 × 250 × 8 mm",
                    "pafta": "Baş makas betopan yerleşimi: 3 kalkan × 2 = 6 adet"},
        "z_liste": "BAŞ MAKAS Z'Sİ L 2800 · 8 adet · fabrikada hazırlanır",
        "tomega": {"ad": "60'lık duvar omegası (ters tavan)", "pafta": "Tavan omega yerleşim planı: 45 parça, 111,8 m",
                   "liste": "60'LIK DUVAR OMEGASI 60 × 3750 · 36 adet (iç duvar üstleriyle birlikte)"},
        "alcipan_liste": {"yesil": "( ASMA / TERS ) TAVAN YEŞİL ALÇIPAN 12,5 × 1200 × 2500 · 2 adet",
                          "beyaz": "( ASMA / TERS ) TAVAN BEYAZ ALÇIPAN 12,5 × 1200 × 2500 · 17 adet"},
        "boardex_liste": "VERANDA-SUNDURMA-BALKON TAVAN BOARDEX 12,5 × 1200 × 2400 · 4 adet",
        "tavan_h_liste": "",
        "asik_liste": "AŞIK L 4200 · 43 adet (10 cm bindirme)",
        "izo_liste": "ÇATI İZOLASYONU (IZOCAM-KNAUF) 100 mm · 9,6 m² / paket · 7 paket",
        "tersmahya": {"ad": "Ters mahya (dere hattı)", "gorev": "iki yüzün kesiştiği iç köşede suyu saçağa indirir; trapez sac bunun üstünde kesilir",
                      "liste": "(ANTRASİT) TERS MAHYA L 2800 · 4 adet + kenar kutusu 8"},
        "alin": {"ad": "Alın sacı",
                 "alin": "~{h} cm: trapezin kenar hadvesinden saçak altının 6 cm altına; dereyi de içine alır, ayrı alt uç parçası yok (Lokman, 26.10.2026)",
                 "kaynak": "Lokman çizimleri (24.10.2026)",
                 "profil": "tırnak 3 (baş makas Z'sine) → saçak altı 30 → alın → hadve üstünden kıvrım → hadveyi kavrayan kıvrım",
                 "uc": "saçak altı kolu makasın topuğuna dayanır, orada kesilir; alın yüzü ve üst kıvrım derenin ucunu kapatmak için devam eder (Lokman, 26.10.2026)",
                 "proje": "alın ~{h} cm: kenar hadvesinden dereyi de içine alacak kadar aşağı (Lokman, 26.10.2026; PK-01’de sandviç panelle 13 cm); kesin ölçü teyit bekler",
                 "liste": "( ANTRASİT) ALIN SACI (30'LUK) 300 × 2500 · 10 adet"},
        "dere": {"ad": "Galvaniz eksiz oluk (dere)", "kesit": "K profil, 15 × 11,4 cm (38’lik açınım), boyalı antrasit",
                 "pafta": "Makas ve dere planı: 4 hat, 16,4 m",
                 "liste": "( ANTRASİT ) METAL DERE L 4000 · 5 adet; dere kapağı 8, dere kelepçesi 40"},
        "inis": {"ad": "İniş borusu (dikdörtgen, oluklu)", "agiz_kolon": "kolonun hizasında; kaz boynu kolona dik döner",
                 "agiz_kose": "derenin köşe ucunda, borunun hizasında; kaz boynu duvara dik döner, boru köşe direğinin yanından iner (Lokman’ın fotoğrafları)",
                 "agiz": "borunun hizasında; kaz boynu duvara dik döner", "kesit": "yaklaşık 8 × 6 cm, boyalı antrasit; bina ile birlikte iner",
                 "takim": "iniş aparatı · 2 açık dirsek (kaz boynu) · boru L 3000 · 2 kelepçe · kapalı dirsek", "pafta": "7 iniş",
                 "liste": "iniş borusu 7, açık dirsek 14, kapalı dirsek 7, kelepçe 14"},
        "ic_kapi": {"kod": "K-01", "not": "iç kapılar alıcıya ait; yer ve açılış yönü paftadan"},
        "pvc_renk": "antrasit gri, iç ve dış", "pvc_renk_kisa": "antrasit gri",
        "dis_kapi_kanat": {"kod": "K-02", "kanat": "kanat 90 × 200, sağ", "liste": "PREFABRİK ÇELİK KAPI ( SAĞ ) 90 × 200 · 1 adet"},
        "bolum_cati": "Veranda ve çatı",
    }
    a = mt["adim"]

    def K(t, az, el, dd, plan=False):
        return {"t": t, "az": az, "el": el, "d": dd, **({"plan": True} if plan else {})}

    adim = [
        {"ad": "Genel bakış", "t": a[0]["t"], "p": a[0]["p"], "head": "Kimlik kartına göre adetler", "kamera": K([0, 1.4, 0.7], 0.62, 0.34, 16.5)},
        {"ad": "Alt çerçeve", "t": a[1]["t"], "p": a[1]["p"], "kamera": K([0, 0, 0.6], 0.45, 1.05, 13.5),
         "rows": [R(None, "100’lük alt çerçeve 100 × 3750", "8 adet", "liste"), R(None, "60’lık alt çerçeve 60 × 2500", "7 adet", "liste"),
                  I("Dış duvar hattı", "{alt_dis} m"), I("İç duvar hattı", "{alt_ic} m")]},
        *({"oda": r["id"]} for r in d["rooms"]),
        {"ad": "Veranda", "t": a[2]["t"], "p": a[2]["p"], "kamera": K([300, 1.2, -60], 0.55, 0.42, 8.5, True)},
        {"ad": "Saçak, duvar ve baş makas omegası", "t": a[3]["t"], "p": a[3]["p"], "kamera": K([0, 2.3, 0.6], 0.62, 0.55, 13.5),
         "rows": [R(None, "100’lük saçak omegası 100 × 2500", "7 adet", "liste"), R(None, "100’lük duvar omegası 100 × 2500", "4 adet", "liste"),
                  R(None, "Baş makas omegası L 2500", "8 adet", "liste"),
                  R(None, "60’lık duvar omegası (iç duvar üstü)", "{omega_ic_n} parça · {omega_ic_m} m", "model"), I("Sac", "1 mm")]},
        {"ad": "Ana çatı ve cumba makasları", "t": a[4]["t"], "p": a[4]["p"], "kamera": K([0, 2.4, 0.2], 0.95, 0.55, 14.5),
         "extra": [I("Ana çatı", "açıklık 660 cm · eğim 18,2° · tepe 118,5 cm"), I("Makas aralığı", "125,5 cm (son göz 137)"),
                   I("İç çubuk", "Warren · 9 göz"), I("Cumba", "açıklık 634,75 cm · eğim 18,9°"), I("Cumba aralığı", "104 · 117 · 92 cm (pafta)")]},
        {"ad": "Baş makas betopanı ve Z", "t": a[5]["t"], "p": a[5]["p"], "kamera": K([250, 2.9, 150], -0.55, 0.24, 11.5, True),
         "rows": [R(None, "Baş makas betopanı 125 × 250 × 8 mm", "6 adet", "pafta"), R(None, "Baş makas Z’si L 2800", "8 adet", "liste"),
                  I("Makas uçları", "artan betopandan (6 parça)")]},
        {"ad": "Tavan omegaları", "t": a[6]["t"], "p": a[6]["p"], "kamera": K([0, 2.3, 0.6], 0.55, 1.28, 12.5),
         "rows": [R(None, "Tavan omegası", "45 parça · 111,8 m", "pafta"), R(None, "60’lık duvar omegası 60 × 3750", "36 adet (iç duvar üstleriyle)", "liste"),
                  I("Veranda", "10 × 140 cm")]},
        {"ad": "Ters tavan alçıpanı", "t": a[7]["t"], "p": a[7]["p"], "kamera": K([0, 2.3, 0.6], 0.55, 1.28, 12.5),
         "extra": [R(None, "Tavan alçıpanı beyaz 12,5 × 1200 × 2500", "17 adet", "liste"), R(None, "Tavan alçıpanı yeşil (ıslak hacim)", "2 adet", "liste"),
                   R(None, "Veranda tavanı boardex 12,5 × 1200 × 2400", "4 adet", "liste"), R(None, "Alçıpan vidası 3,5 × 35", "1250 adet", "liste")]},
        {"ad": "Çatı izolasyonu", "t": a[8]["t"], "p": a[8]["p"], "kamera": K([450, 2.5, 300], 2.5, 0.95, 12.5, True),
         "extra": [R(None, "Çatı izolasyonu (Izocam-Knauf) 100 mm · 9,6 m² / paket", "7 paket", "liste"), I("Modelde", "{izo_n} şerit · ≈ {izo_m2} m²")]},
        {"ad": "Aşıklar", "t": a[9]["t"], "p": a[9]["p"], "kamera": K([0, 3.0, 0.6], 0.95, 0.6, 14),
         "rows": [R(None, "Aşık (omega) L 4200", "43 adet", "liste"), I("Paftada", "57 parça · 154 m"), I("Kesit", "87 × 30 mm, sac 1 mm"),
                  R(None, "C kapama", "6 kalkan kenarı", "model")]},
        {"ad": "Saçak sacı", "t": a[10]["t"], "p": a[10]["p"], "kamera": K([740, 2.45, -20], 0.7, 0.16, 5.2, True),
         "rows": [R(None, "Saçak sacı (antrasit, 30’luk) 300 × 2500", "8 adet", "liste"), I("Menfezli", "3 adet"), I("Profil", "3 + 30 + 13 + 10 cm"), I("Sac", "1 mm")]},
        {"ad": "Dere ve inişler", "t": a[11]["t"], "p": a[11]["p"], "kamera": K([0, 2.0, 0.6], -0.62, 0.28, 14.5),
         "rows": [R(None, "Metal dere L 4000", "5 adet", "liste"), I("Dere (pafta)", "4 hat · 16,4 m"), R(None, "İniş takımı", "7 adet", "pafta"),
                  R(None, "Dere kapağı", "8 adet", "liste")]},
        {"ad": "Ters mahya", "t": a[12]["t"], "p": a[12]["p"], "kamera": K([287, 3.2, 40], 0.55, 0.75, 10.5, True),
         "rows": [R(None, "Ters mahya L 2800", "4 adet", "liste"), R(None, "Ters mahya kenar kutusu", "8 adet", "liste")]},
        {"ad": "Trapez sac ve mahya", "t": a[13]["t"], "p": a[13]["p"], "kamera": K([0, 2.6, 0.6], 0.62, 0.5, 15.5),
         "rows": [R(None, "Trapez sac L 3500 (ana çatı)", "21 adet", "liste"), R(None, "Trapez sac L 3400 (cumba)", "8 adet", "liste"),
                  I("Modelde", "{kaplama_n} levha · 100 cm kapatır, 0,5 mm"), R(None, "Trapez sac mahyası L 800", "25 adet", "liste")]},
        {"ad": "Alın sacları", "t": a[14]["t"], "p": a[14]["p"], "kamera": K([0, 2.6, 0.6], -0.62, 0.34, 14.5),
         "rows": [R(None, "Alın sacı 300 × 2500", "10 adet", "liste")]},
        {"ad": "Kapı ve pencereler", "t": a[15]["t"], "p": a[15]["p"], "kamera": K([0, 0.8, 0.6], 0.5, 1.0, 13),
         "extra": [I("İç kapılar", "alıcıya ait")]},
    ]
    drop = [0, 0.3, 1.4, 1.4, 1.4, 1.4, 1.4, 1.2, 0.6, 1.4, 0.8, 0.5, -0.5, 0, 0.7, 0.6, 0.6, 0.9, 0.9, 0.6, 0]
    for x, dr in zip(adim, drop):
        x["drop"] = dr
    assert len(adim) == d["N"] + 1
    d["adimlar"] = adim
    d["genel"] = [
        {"grp": "Duvar panoları"}, {"pre": ["D-", "I-"], "adlar": ["100'lük yapıştırma", "100'lük pencereli", "Betopan kaplı"]},
        {"grp": "Ekler, köşeler ve veranda"}, {"pre": ["H-", "B-", "V-"], "adlar": ["Özel H", "Özel köşe", "Çektirme"]},
        {"grp": "Çatı"}, {"pre": ["MA-"], "adlar": ["Cumba ara"]},
        R(None, "Saçak omegası · duvar omegası · baş makas omegası", "7 · 4 · 8", "liste"), R(None, "Saçak sacı", "8 adet", "liste"),
        R(None, "Baş makas betopanı", "6 adet", "pafta"), R(None, "Tavan omegası", "45 · 111,8 m", "pafta"),
        R(None, "60’lık duvar omegası (tavan + iç duvar)", "36 adet", "liste"),
        R(None, "Tavan alçıpanı beyaz · yeşil · veranda boardex", "17 · 2 · 4", "liste"), R(None, "Aşık L 4200", "43 adet", "liste"),
        R(None, "Çatı izolasyonu 100 mm (rulo)", "7 paket", "liste"),
        R(None, "Trapez sac 3500 / 3400 (100 cm kapatır, 0,5 mm)", "21 / 8 adet", "liste"), R(None, "Mahya · ters mahya", "25 · 4", "liste"),
        R(None, "Alın sacı", "10 adet", "liste"), R(None, "Dere ve iniş", "4 hat · 7 iniş", "pafta"), R(None, "Çelik dübel", "21 adet", "liste"),
        {"grp": "Kapı ve pencere"}, {"pre": ["K-", "P-"], "adlar": ["PVC"]},
    ]
    d["cati_adim"] = list(range(9, 20))
    d["rozet"] = "900 × 600 · 62,62 m²"
    d["kabuk"] = {
        "proje": "62 m² prefabrik", "chip": "62,62 m² · paftadan",
        "spec": ["900 × 600 cm", "tek kat prefabrik", "duvar 250 cm", "beşik + cumba · 18,2° / 18,9°", "trapez sac", "fugalı cephe"],
        "note": ("Kaynak: __PROJE__ montaj paftası (DWG, 19 pafta: duvar montaj planı, dış duvar görünüşleri, H profil, kaynaklı detaylar, tavan omega, "
                 "makas ve dere, baş makas betopanı, aşık, çatı kaplama) ve yükleme listesi; kodla okundu. Pano, H, köşe direği, veranda, makas, tavan "
                 "omegası, aşık, trapez ve dere yerleri paftadan; makasların yeri, boyu ve yüksekliği SketchUp modelinden. Adetler yükleme listesinden. "
                 "Köşe direği, Z, C kapama, saçak ve alın sacı kesitleri PK-01 için Lokman’ın çizimleri ve fotoğraflarından; bu projede aynı sistem "
                 "varsayıldı. Trapezde paftada çizili olmayan kesim parçaları varsayımdır. Paftadaki “OSB + nem bariyeri” notu bu projede geçerli değil: "
                 "trapez doğrudan aşıkların üstünde (Lokman). Cephe fugası dış duvar görünüşlerindeki fugalı duvar detayından."),
    }
    return d


if __name__ == "__main__":
    (B / "veri.json").write_text(json.dumps(veri(), ensure_ascii=False, indent=None, separators=(",", ":")), encoding="utf-8")
    print(B / "veri.json")
