#!/usr/bin/env python3
"""Yapı Tanımı 0.5'ten yükleme listesi girdisi (metraj).

`../2026-10-03_yukleme/girdi_uret.py`'nin genel hali: dikdörtgen olmayan plan, farklı yükseklikte duvarlar (ek yapı, korkuluk),
çok düzlemli çatı. Geometriden gelenler: dış kaplama yüzleri, oda iç yüzleri ve boşlukları, tavan alanları, köşeler, duvar boyları,
çatı kenarları (saçak, mahya, kırma, vadi, alın, duvar dibi), kalkanlar, aşık sıraları, kaplama dizilimi. Tanımdan gelenler:
odaların işlevi, kapsam (alıcıya ait olanlar), çatı yöntemi ve kaplaması. Hesap `../2026-10-03_yukleme/yukleme.py`'dedir.

Kullanım:
    python girdi_genel.py tanim.json --cikti klasor
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

import cati_genel
import yapi

BURADA = Path(__file__).resolve().parent
YUKLEME = BURADA.parent / "2026-10-03_yukleme"
KAPLAMA_ADI = {"sandvic_panel": "sandviç panel", "tek_kat_panel": "tek kat panel", "osb_kiremit": "OSB + nem bariyeri + kiremit desen sac",
               "osb_trapez": "OSB + nem bariyeri + trapez sac", "trapez_sac": "trapez sac", "osb_shingle": "OSB + membran + shingle"}


def tr(v: float, n: int = 1) -> str:
    return f"{v:.{n}f}".replace(".", ",")


def sade(v: float) -> str:
    return tr(v).replace(",0", "")


def _dizilim(c: dict, kur: dict, kaplama: str, uzat: bool = True) -> dict:
    """Kurallardaki ayarlarla kaplama dizilimi. Panel boyu uzatma kuralı (Lokman, 4 Ekim 2026 16:18): bir boy 1'er cm uzatılınca
    (en çok 3 cm) adet düşüyorsa ve kesim payı 1 cm olsa da aynı kalıyorsa uzun boy alınır; en uzun boydan başlanır."""
    kd = kur["kirma_cati_dizilim"]["deger"]
    anahtar = {"sandvic_panel": "sandvic_panel_kapatma_m", "tek_kat_panel": "tek_kat_panel_kapatma_m", "osb_kiremit": "kiremit_kapatma_m",
               "osb_trapez": "trapez_sac_kapatma_m", "trapez_sac": "trapez_sac_kapatma_m"}[kaplama]
    kapatma = kur[anahtar]["deger"] * 100
    tasma = kur["cati_kaplama_tasma_m"]["deger"] * 100
    pay = kd["kesim_payi_m"] * 100
    paylas = kaplama not in kd["artan_parca_kullanilmayan_kaplamalar"]
    # çatı paneli üstüne sandviç panel de aynı dizilime girer; düzlemlerin hepsi
    dz, kn = c["duzlemler"], c["kenarlar"]

    def kos(boylar=None, p=pay):
        return cati_genel.dizilim(dz, kn, kapatma, tasma, p, paylas, boylar)

    d = kos()
    taban = dict(boylar=list(d["boylar_cm"]), adet=d["adet"], boy_adet=dict(d["boy_adet"]))
    uzatma = []
    uz = (kur.get("panel_boyu_uzatma") or {}).get("deger") or {}
    if uzat and uz.get("uygula"):
        boylar = list(d["boylar_cm"])
        for i in sorted(range(len(boylar)), key=lambda j: -boylar[j]):
            adaylar = []
            for s in range(1, round(uz["en_cok_m"] / uz["adim_m"]) + 1):
                b2 = list(boylar)
                b2[i] = round(boylar[i] + s * uz["adim_m"] * 100, 4)
                n = kos(b2)["adet"]
                if n < d["adet"] and kos(b2, uz["saglamlik_kesim_payi_m"] * 100)["adet"] == n:
                    adaylar.append((n, b2[i]))
            if adaylar:
                n, yeni = min(adaylar)
                uzatma.append({"taban_boy_cm": boylar[i], "boy_cm": yeni, "taban_adet": d["adet"], "adet": n})
                boylar[i] = yeni
                d = kos(boylar)
    d["taban"] = taban
    d["uzatma"] = uzatma
    d["kaplama"] = kaplama
    return d


def metraj(y: dict, c: dict, kur: dict) -> dict:
    t = y["tanim"]
    F = y["yuzler"]
    sinif = t["duvar_siniflari"]
    kat_h = t["kat_yuksekligi"] / 100
    ct = t["cati"]
    vk = kur["veranda_cercevesi"]["deger"]
    m: dict = {}
    # dış çizgi ve oturum
    hat = y["bolgeler"]["(dış)"]["net"].interiors
    cevre = unary_union([Polygon(h.coords) for h in hat])
    x0, y0, x1, y1 = cevre.bounds
    m["dis_olcu_cm"] = [x1 - x0, y1 - y0]
    m["oturum_m2"] = cevre.area / 1e4
    kapali = [d for d in y["duvarlar"] if d["sinif"] in ("dis", "ic", "ek")]
    kd = t["yuz_kaplamalari"]["dis"]["kalinlik"]
    kx0, ky0 = min(d["kutu"][0] for d in kapali) - kd, min(d["kutu"][1] for d in kapali) - kd
    kx1, ky1 = max(d["kutu"][2] for d in kapali) + kd, max(d["kutu"][3] for d in kapali) + kd
    m["kapali_olcu_cm"] = [kx1 - kx0, ky1 - ky0]
    # dış kaplama yüzleri (Boardex): dikme hariç (dikme ve kiriş kaplaması kuraldaki çevreyle)
    dis_yuz = [f for f in F if f["kaplama"].startswith("dis") and f["sinif"] != "kolon"]
    m["dis_yuzler"] = [{"duvar": f["duvar"], "sinif": f["sinif"], "bolge": f["bolge"], "boy_m": round(f["boy"] / 100, 4), "brut_m2": round(f["brut_m2"], 4),
                        "net_m2": round(f["net_m2"], 4), "bosluklar": [b["ad"] for b in f["bosluklar"]]} for f in dis_yuz]
    m["dis_brut_m2"] = sum(f["brut_m2"] for f in dis_yuz)
    m["dis_net_m2"] = sum(f["net_m2"] for f in dis_yuz)
    # dış boşluklar: yüz başına bir kez (iki yüzü de dışa bakan duvardaki geçit iki kez)
    bos: dict[str, dict] = {}
    for f in dis_yuz:
        for b in f["bosluklar"]:
            ac = next(a for a in y["acikliklar"] if a["ad"] == b["ad"])
            ad = {"pencere": ac.get("etiket") or f"{ac['en']}/{ac['yuk']}", "dis_kapi": "dış kapı", "ic_kapi": "iç kapı", "gecit": "geçit (kapısız)"}[ac["tur"]]
            e = bos.setdefault(ad + f"|{ac['en']}x{ac['yuk']}", {"ad": ad, "adet": 0, "en": ac["en"] / 100, "boy": ac["yuk"] / 100, "tur": ac["tur"]})
            e["adet"] += 1
    m["dis_bosluklar"] = list(bos.values())
    # bina dış duvarının çevresi: dışa (dış, veranda, ek) bakan yüzlerinin toplamı
    m["bina_cevre_m"] = sum(f["boy"] for f in dis_yuz if f["sinif"] == "dis") / 100
    # dikme ve kiriş kaplaması (kuraldaki çevrelerle), kalkanlar, bacanın çatı üstü
    dikmeler = [d for d in y["duvarlar"] if d["sinif"] == "kolon"]
    kiris_v = [k for k in t.get("kirisler", []) if k.get("bolge") == "veranda"]
    m["kolon_kiris"] = []
    if dikmeler:
        m["kolon_kiris"].append({"ad": "veranda dikmesi", "adet": len(dikmeler), "cevre_m": vk["dikme_kaplama_cevresi_m"], "boy_m": dikmeler[0]["yukseklik"] / 100})
    if kiris_v:
        m["kolon_kiris"].append({"ad": "veranda kirişi", "adet": 1, "cevre_m": vk["kiris_kaplama_cevresi_m"],
                                 "boy_m": round(sum(hi - lo for k in kiris_v for lo, hi in k["acik"]) / 100, 3)})
    m["kalkanlar"] = [{"ad": k["ad"], "alan_m2": round(k["alan_m2"], 3)} for k in c["kalkanlar"]]
    baca = []
    for d in y["duvarlar"]:
        if d["sinif"] == "baca" and d.get("ust_kot"):
            bx0, by0, bx1, by1 = d["kutu"]
            orta = ((bx0 + bx1) / 2, (by0 + by1) / 2)
            dz = next((p for p in c["duzlemler"] if p["cokgen"].contains(Point(orta))), None)
            cati_kotu = dz["kot"](orta) if dz else t["kat_yuksekligi"]
            cev = 2 * ((bx1 - bx0) + (by1 - by0)) / 100
            baca.append({"ad": d["ad"], "cevre_m": cev, "ust_kot_cm": d["ust_kot"], "cati_kotu_cm": round(cati_kotu, 1), "cati_ustu_m": round((d["ust_kot"] - cati_kotu) / 100, 3),
                         "alan_m2": round(cev * (d["ust_kot"] - cati_kotu) / 100, 3), "boy_m": d["ust_kot"] / 100})
    m["baca"] = baca
    # mahaller
    odalar = []
    for b in y["bolgeler"].values():
        if b["sinif"] not in ("ic", "ek"):
            continue
        yz = [f for f in F if f["bolge"] == b["ad"] and f["kaplama"] == "ic"]
        kiris = [k for k in t.get("kirisler", []) if k.get("bolge") == b["ad"]]
        kiris_m2 = sum((hi - lo) / 100 * vk["kiris_kaplama_cevresi_m"] for k in kiris for lo, hi in k["acik"])
        bosluk = []
        for f in yz:
            for bb in f["bosluklar"]:
                bosluk.append(round(bb["alan_m2"], 4))
        odalar.append({"ad": b["ad"], "sinif": b["sinif"], "tur": "yesil" if b.get("islak") else "beyaz", "cevre_m": round(b["cevre_m"], 3), "alan_m2": round(b["alan_m2"], 3),
                       "duvar_brut_m2": round(sum(f["brut_m2"] for f in yz) + kiris_m2, 3), "kiris_kaplamasi_m2": round(kiris_m2, 3), "bosluk_m2": bosluk,
                       "ic_kose": b["ic_kose"], "dis_kose": b["dis_kose"], "islev": b.get("islev", []),
                       "cati_paneli_altinda": any(dz.get("ust_yapi") == "cati_paneli" and dz["cokgen"].contains(b["net"].representative_point()) for dz in c["duzlemler"])})
    m["odalar"] = odalar
    veranda = [b for b in y["bolgeler"].values() if b["sinif"] == "veranda"]
    m["veranda_m2"] = sum(b["alan_m2"] for b in veranda)
    m["veranda_cevre_m"] = sum(b["cevre_m"] for b in veranda)
    # verandanın brüt ölçüsü (0.4'teki gibi dış ölçüyle): dış çizginin içinde, bina duvarlarının kaplanmış yüzlerine kadar;
    # verandayı çevreleyen korkuluk ve dikmeler brüt alanın içindedir
    m["veranda_brut_m2"], m["veranda_brut_cevre_m"] = 0.0, 0.0
    if veranda:
        diger_kutle = unary_union([g for d in y["duvarlar"] if d["sinif"] not in ("korkuluk", "kolon") for g in [d["geo"]] + d.get("_serit", [])])
    for b in veranda:
        if b.get("poligon"):
            brut = Polygon(b["poligon"])
        else:
            diger_mahal = unary_union([o["ham"] for o in y["bolgeler"].values() if o["sinif"] != "dis" and o is not b] or [Polygon()])
            kalan = cevre.difference(diger_kutle).difference(diger_mahal)
            nokta = b["net"].representative_point()
            brut = next(p for p in (kalan.geoms if kalan.geom_type == "MultiPolygon" else [kalan]) if p.contains(nokta))
        m["veranda_brut_m2"] += brut.area / 1e4
        m["veranda_brut_cevre_m"] += brut.length / 100
    # duvar boyları (karkas) ve panel adetleri
    grup = {}
    for d in y["duvarlar"]:
        g = grup.setdefault(d["sinif"], {"adet": 0, "boy_m": 0.0, "alan_m2": 0.0, "adlar": []})
        g["adet"] += 1
        g["boy_m"] += d["boy"] / 100
        g["alan_m2"] += d["boy"] / 100 * yapi._yukseklik(d) / 100
        g["adlar"].append(d["ad"])
    m["duvar_gruplari"] = {k: {"adet": v["adet"], "boy_m": round(v["boy_m"], 3), "ortalama_yukseklik_m": round(v["alan_m2"] / v["boy_m"], 3), "adlar": v["adlar"]} for k, v in grup.items()}
    # ek yapının (müştemilat) oturumu: kendi duvarlarının dış ölçüsüyle, binanın dış yüzüne kadar
    ek_d = [d for d in y["duvarlar"] if d["sinif"] == "ek"]
    bina_d = [d for d in y["duvarlar"] if d["sinif"] == "dis"]
    m["ek_oturum_m2"] = 0.0
    if ek_d:
        from shapely.geometry import box as _box
        ek_kutu = _box(min(d["kutu"][0] for d in ek_d) - kd, min(d["kutu"][1] for d in ek_d) - kd, max(d["kutu"][2] for d in ek_d) + kd, max(d["kutu"][3] for d in ek_d) + kd)
        bina_kutu = _box(min(d["kutu"][0] for d in bina_d) - kd, min(d["kutu"][1] for d in bina_d) - kd, max(d["kutu"][2] for d in bina_d) + kd, max(d["kutu"][3] for d in bina_d) + kd)
        m["ek_oturum_m2"] = ek_kutu.difference(bina_kutu).area / 1e4
    ek_yuz = [f for f in dis_yuz if f["sinif"] == "ek"]
    m["ek_cevre_m"] = sum(f["boy"] for f in ek_yuz) / 100
    m["ek_ortalama_yukseklik_m"] = (sum(f["brut_m2"] for f in ek_yuz) / m["ek_cevre_m"]) if ek_yuz else 0.0
    # iç duvar boyu: 0.4'teki ölçüyle (kaplanmış iç duvar kütlesinin alanı ÷ kaplanmış kalınlık; birleşimler bir kez, öteki duvarların
    # kaplanmış yüzleri arasında). Karkas boylarının toplamından kaplama kalınlıkları kadar kısadır.
    ic_duvar = [d for d in y["duvarlar"] if d["sinif"] == "ic"]
    m["ic_boy_m"] = 0.0
    if ic_duvar:
        ic_kutle = unary_union([g for d in ic_duvar for g in [d["geo"]] + d.get("_serit", [])])
        t_ic = t["yuz_kaplamalari"][sinif["ic"]["yuz"]["ic"]]["kalinlik"]
        # öteki duvarlar, iç kaplamalarıyla (iç duvarın ucu dış duvarın kaplanmış yüzünde biter)
        oteki = unary_union([d["geo"].buffer(t["yuz_kaplamalari"][sinif[d["sinif"]]["yuz"].get("ic", sinif["ic"]["yuz"]["ic"])]["kalinlik"], join_style=2)
                             for d in y["duvarlar"] if d["sinif"] != "ic"])
        ti = ic_duvar[0]["kalinlik"] + 2 * t_ic
        m["ic_boy_m"] = ic_kutle.difference(oteki).area / ti / 100
        m["ic_karkas_boyu_m"] = sum(d["boy"] for d in ic_duvar) / 100
    # yalıtım: yalıtımlı sınıfların duvarları (bina dış duvarı ve iç duvar)
    yal_dis = [f for f in dis_yuz if sinif[f["sinif"]].get("yalitim")]
    yal_bos = sum(a["alan_m2"] for a in y["acikliklar"] if sinif[y["adli"][a["duvar"]]["sinif"]].get("yalitim"))
    m["yalitim"] = {"dis_brut_m2": sum(f["brut_m2"] for f in yal_dis), "ic_brut_m2": m["ic_boy_m"] * kat_h, "bosluk_m2": yal_bos}
    # OSB takviyesi (dolap ve TV ünitesi gelen duvarlar; tanımda yazılıysa): her duvarın o odaya bakan yüzünün tamamı
    ot = t.get("osb_takviye")
    m["osb_takviye"] = None
    if ot:
        satir = []
        for dv in ot["duvarlar"]:
            yz = [f for f in F if f["bolge"] == dv["mahal"] and f["duvar"] == dv["duvar"] and f["uzun"] and f["kaplama"] == "ic"]
            if not yz:
                raise SystemExit(f"OSB takviyesi: {dv['mahal']} mahalinin {dv['duvar']} duvarına bakan yüzü yok.")
            # duvar yüzünün tamamı: aynı doğrultuda ve bitişik, başka bir duvarın ucuna ait yüz parçaları da (L birleşimde köşe) sayılır
            for f in list(yz):
                d0 = y["adli"][f["duvar"]]
                c0 = yapi._kenar(d0["kutu"], f["kenar"])[1]
                for o in F:
                    if o["bolge"] != dv["mahal"] or o is f or o in yz or o["eksen"] != f["eksen"] or o["kenar"] != f["kenar"] or o["kaplama"] != "ic":
                        continue
                    c1 = yapi._kenar(y["adli"][o["duvar"]]["kutu"], o["kenar"])[1]
                    bitisik = any(abs(a1 - b0) < 0.01 or abs(b1 - a0) < 0.01 for a0, a1 in f["araliklar"] for b0, b1 in o["araliklar"])
                    if abs(c0 - c1) < 0.01 and bitisik:
                        yz.append(o)
            satir.append({"mahal": dv["mahal"], "duvar": dv["duvar"], "duvar_adi": dv.get("duvar_adi", dv["duvar"]), "neden": dv.get("neden"),
                          "boy_m": round(sum(f["boy"] for f in yz) / 100, 4), "brut_m2": sum(f["brut_m2"] for f in yz),
                          "bosluk_m2": round(sum(b["alan_m2"] for f in yz for b in f["bosluklar"]), 4)})
        m["osb_takviye"] = {"duvarlar": satir, "brut_m2": sum(x["brut_m2"] for x in satir), "bosluk_m2": sum(x["bosluk_m2"] for x in satir)}
        m["osb_takviye"]["net_m2"] = m["osb_takviye"]["brut_m2"] - m["osb_takviye"]["bosluk_m2"]
    # çatı
    top = c["kenar_toplam_cm"]
    sacaklar = [e for e in c["kenarlar"] if e["tur"] == "sacak"]
    asik_dz = [dz for dz in c["duzlemler"] if dz.get("ust_yapi") != "cati_paneli"]           # çatı paneli olan düzlemde aşık yok
    asik = {dz["ad"]: c["asik"][dz["ad"]] for dz in asik_dz} if "asik" in c else {}
    makasli = unary_union([dz["cokgen"] for dz in asik_dz]) if asik_dz else None
    panelli = [dz for dz in c["duzlemler"] if dz.get("ust_yapi") == "cati_paneli"]
    import ciz_genel
    inis = ciz_genel.inis_noktalari(c, kur["inis"]["deger"]["orta_inis_esigi_m"] * 100, ct.get("sacak", 30))
    m["cati"] = {
        "yuzey_m2": c["yuzey_m2"], "plan_m2": c["plan_m2"], "makasli_plan_m2": makasli.area / 1e4 if makasli is not None else 0.0,
        "duzlemler": [{"ad": dz["ad"], "egim": dz["egim"], "plan_m2": round(dz["plan_m2"], 3), "yuzey_m2": round(dz["yuzey_m2"], 3),
                       "egimli_boy_m": round(dz["acilim"].bounds[3] / 100, 4), "ust_yapi": dz.get("ust_yapi", "makas")} for dz in c["duzlemler"]],
        "sacak_kenarlari_m": [round(e["boy"] / 100, 4) for e in sacaklar], "sacak_m": top.get("sacak", 0) / 100,
        # iniş kuralındaki cephe boyu: saçak kenarından iki uçtaki saçak payı düşülür (dikdörtgen kırma çatıda cephenin kendisi)
        "cephe_kenarlari_m": [round(max(0.0, e["boy"] - 2 * ct.get("sacak", 30)) / 100, 4) for e in sacaklar],
        # saçak yüzü (yöntem A): saçak kenarı × (topuk + çatı panelinin eğimdeki düşey ölçüsü)
        "sacak_yuzu_m2": sum(e["boy"] / 100 * (ct.get("topuk", 10) + ct.get("panel_kalinligi", 8) * next(d for d in c["duzlemler"] if d["ad"] == e["duzlemler"][0])["kok"]) / 100 for e in sacaklar),
        "mahya_m": top.get("mahya", 0) / 100, "kirma_m": top.get("kirma", 0) / 100, "vadi_m": top.get("vadi", 0) / 100,
        "alin_m": top.get("alin", 0) / 100, "duvar_dibi_m": top.get("duvar_dibi", 0) / 100, "ust_kenar_m": top.get("ust", 0) / 100,
        "kenarlar": [{"tur": e["tur"], "duzlemler": e["duzlemler"], "boy_m": round(e["boy"] / 100, 4)} for e in c["kenarlar"]],
        "asik_siralari": {ad: [{"t_cm": round(s["t"], 1), "boy_m": round(s["boy"] / 100, 3), "tur": s["tur"]} for s in sr] for ad, sr in asik.items()},
        "asik_boyu_m": sum(s["boy"] for sr in asik.values() for s in sr) / 100,
        "inis_noktalari": [[round(p[0], 1), round(p[1], 1), p[2]] for p in inis],
        "kose_adedi": sum(1 for p in inis if p[2] == "kose"),
        "dere_ucu_acik": None,
        "panelli_oturum_m2": sum(sum(b["alan_m2"] for b in y["bolgeler"].values() if b["sinif"] != "dis" and dz["cokgen"].contains(b["net"].representative_point())) for dz in panelli),
        "panelli_plan_m2": sum(dz["plan_m2"] for dz in panelli),
    }
    # çatının bağlı olduğu ölçüler (şilte kuralı): makaslı çatının boyu ve binanın eni
    if makasli is not None:
        mx0, my0, mx1, my1 = makasli.bounds
        ana = max(asik_dz, key=lambda dz: dz["plan_m2"])
        mahya_y = abs(ana["yukari"][0]) > 0.5                 # ana düzlem x yönünde yükseliyorsa mahya y boyunca
        m["cati"]["cati_boyu_m"] = ((my1 - my0) if mahya_y else (mx1 - mx0)) / 100
        bina = [d for d in y["duvarlar"] if d["sinif"] == "dis"]
        bx0, by0 = min(d["kutu"][0] for d in bina) - kd, min(d["kutu"][1] for d in bina) - kd
        bx1, by1 = max(d["kutu"][2] for d in bina) + kd, max(d["kutu"][3] for d in bina) + kd
        m["cati"]["bina_eni_m"] = ((bx1 - bx0) if mahya_y else (by1 - by0)) / 100
        m["bina_olcu_cm"] = [bx1 - bx0, by1 - by0]
    kaplama = ct.get("kaplama", kur["baz_paket_cati_kaplamasi"]["deger"])
    m["dizilim"] = _dizilim(c, kur, kaplama)
    return m


def bilgi_satirlari(y: dict, c: dict, m: dict, kur: dict) -> tuple[list[str], list[str]]:
    t = y["tanim"]
    ct = t["cati"]
    kap = t["yuz_kaplamalari"]
    ic_d = [d for d in y["duvarlar"] if d["sinif"] == "ic"]
    dis_d = [d for d in y["duvarlar"] if d["sinif"] == "dis"]
    pencere = [a for a in y["acikliklar"] if a["tur"] == "pencere"]
    ik = [a for a in y["acikliklar"] if a["tur"] == "ic_kapi"]
    dk = [a for a in y["acikliklar"] if a["tur"] == "dis_kapi"]
    kapali_net = sum(o["alan_m2"] for o in m["odalar"])
    levha = kur["levha_m2"]["boardex"]["deger"]
    ek = sum(x["adet"] * x["cevre_m"] * x["boy_m"] for x in m["kolon_kiris"]) + sum(k["alan_m2"] for k in m["kalkanlar"]) + sum(b["alan_m2"] for b in m["baca"])
    sol = [
        f"Dış ölçü: {sade(m['dis_olcu_cm'][0])} × {sade(m['dis_olcu_cm'][1])} cm · oturum {tr(m['oturum_m2'], 2)} m² (veranda"
        + (" ve müştemilat" if any(o["sinif"] == "ek" for o in m["odalar"]) else "") + " dahil)",
        "Mahaller (kaplanmış yüzler arası): " + " · ".join(f"{o['ad']} {tr(o['alan_m2'])}" for o in m["odalar"]) + f" · veranda {tr(m['veranda_m2'])} m² · kapalı net {tr(kapali_net)} m²",
        f"Duvar: karkas {sade(dis_d[0]['kalinlik'] * 10)} mm · dışta {sade(kap['dis']['kalinlik'])} cm, içte {tr(kap['ic']['kalinlik'], 2)} cm kaplama · yükseklik {t['kat_yuksekligi']} cm"
        + (" · " + ", ".join(f"{sinif_ad}: {v['adet']} panel" for sinif_ad, v in (("dış", m["duvar_gruplari"].get("dis")), ("iç", m["duvar_gruplari"].get("ic"))) if v)),
        (f"Pencereler: üst kot {sade(max(a['z1'] for a in pencere))} cm" if pencere else "Pencere yok")
        + (" · iç kapı boşlukları " + ", ".join(sorted({f"{a['en']} × {a['yuk']}" for a in ik})) if ik else "")
        + (" · dış kapı boşluğu " + ", ".join(sorted({f"{a['en']} × {a['yuk']}" for a in dk})) if dk else ""),
        f"Dış kaplama (Boardex): duvar yüzleri {tr(m['dis_brut_m2'])} − boşluk {tr(m['dis_brut_m2'] - m['dis_net_m2'])} + dikme, kiriş, kalkan ve baca {tr(ek)} = "
        f"{tr(m['dis_net_m2'] + ek)} m² (fire hariç {math.ceil((m['dis_net_m2'] + ek) / levha - 1e-9)} levha)",
    ]
    mc = m["cati"]
    egimler = " · ".join(f"{d['ad']} %{tr(d['egim'] * 100)}" for d in mc["duzlemler"])
    dz = m["dizilim"]
    sag = [
        f"Çatı: {ct.get('tip_adi') or ct['tip'].replace('besik_cumba', 'beşik + cumba').replace('kirma', 'kırma (dört omuz)')} · {len(mc['duzlemler'])} düzlem ({egimler})",
        f"Yöntem: {'B · tavan omegası ve aşık' if ct.get('yontem') == 'omega_asik' else 'A · çatı ve tavan paneli'} · kaplama: {KAPLAMA_ADI.get(ct.get('kaplama'), '—')} · saçak {ct.get('sacak', 30)} cm · topuk {ct.get('topuk', 10)} cm",
        f"Çatı yüzeyi {tr(mc['yuzey_m2'])} m² (plan {tr(mc['plan_m2'])} m²) · mahya kotu {tr(max(k[2] for d in c['duzlemler'] for k in d['ucboyut']), 0)} cm (makas üstü)",
        f"Saçak {tr(mc['sacak_m'], 2)} m · mahya {tr(mc['mahya_m'], 2)} m · kırma {tr(mc['kirma_m'], 2)} m · vadi {tr(mc['vadi_m'], 2)} m · alın (kalkan kenarı) {tr(mc['alin_m'], 2)} m · duvar dibi {tr(mc['duvar_dibi_m'], 2)} m",
        "Kaplama dizilimi: " + " · ".join(f"L {round(b * 10)}: {n}" for b, n in dz["boy_adet"].items()) + f" = {dz['adet']} panel ({sade(dz['kapatma_cm'])} cm kapatır)",
        "Kalkanlar: " + " · ".join(f"{k['ad']} {tr(k['alan_m2'], 2)} m²" for k in m["kalkanlar"]) if m["kalkanlar"] else "Kalkan yok",
        f"Dere inişi {len(mc['inis_noktalari'])} adet (dere hatlarının uçları; 10 m ve daha uzun saçağın ortası) · subasman ve merdiven çizilmedi · ölçüler cm",
    ]
    return sol, sag


def girdi(y: dict, c: dict, m: dict, kur: dict, kaynak: str) -> dict:
    t = y["tanim"]
    ct = t["cati"]
    sinif = t["duvar_siniflari"]
    kapsam = t.get("kapsam", {})
    kat_h = t["kat_yuksekligi"] / 100
    mc = m["cati"]
    dz = m["dizilim"]
    dk = kur["kapi_boslugu_m"]["dis"]["deger"]
    ik = kur["kapi_boslugu_m"]["ic"]["deger"]
    ev = kur["celik"]["et_kalinligi_varsayilan"]["deger"]
    yontem = ct.get("yontem", "omega_asik")
    kaplama = ct.get("kaplama", kur["baz_paket_cati_kaplamasi"]["deger"])
    gr = m["duvar_gruplari"]
    tahmin = t.get("duvar_panelleri") == "tahmin"          # duvarlar üretim paneli değil (katalog modeli): panel adedi kuraldan tahmin edilir
    en_cok = kur["celik"]["panel_boyu_en_cok_m"]["deger"]
    panel_tahmini = lambda snf: sum(math.ceil(d["boy"] / 100 / en_cok - 1e-9) for d in y["duvarlar"] if d["sinif"] == snf)
    et_notu = "panel adedi tahmin; gerçek adet karkas yerleşiminden gelir"
    odalar = [{k: o[k] for k in ("ad", "tur", "cevre_m", "alan_m2", "duvar_brut_m2", "bosluk_m2", "ic_kose", "dis_kose", "islev")} for o in m["odalar"]]
    veranda = [b for b in y["bolgeler"].values() if b["sinif"] == "veranda"]
    elektrik_odalar = [{"ad": o["ad"], "islev": o["islev"]} for o in odalar] + [{"ad": b["ad"], "islev": list(b.get("islev", ["veranda"]))} for b in veranda]
    ic_kapi = [a for a in y["acikliklar"] if a["tur"] == "ic_kapi"]
    dis_kapi = [a for a in y["acikliklar"] if a["tur"] == "dis_kapi"]
    uyari = []
    for a in ic_kapi:
        if [a["en"] / 100, a["yuk"] / 100] != ik:
            uyari.append(f"{a['ad']}: iç kapı boşluğu {a['en']} × {a['yuk']}; kural {round(ik[0] * 100)} × {round(ik[1] * 100)} (modeldeki ölçü kullanıldı)")
    for a in dis_kapi:
        if [a["en"] / 100, a["yuk"] / 100] != dk:
            uyari.append(f"{a['ad']}: dış kapı boşluğu {a['en']} × {a['yuk']}; kural {round(dk[0] * 100)} × {round(dk[1] * 100)} (modeldeki ölçü kullanıldı)")
    # kapı ve pencere kalemleri (kapsama göre)
    kp = []
    for en, yuk, kanat in sorted({(a["en"], a["yuk"], tuple(a.get("kanat", [a["en"] - 10, 200]))) for a in ic_kapi}, reverse=True):
        n = sum(1 for a in ic_kapi if (a["en"], a["yuk"]) == (en, yuk))
        kp.append({"kalem": f"Melamin kapı ({kanat[0]}'lik kanat)", "boyut": f"{en} × {yuk}", "adet": n, "durum": "model",
                   "formul": "iç kapı sayısı; boşluk modeldeki çerçeveden" + ("" if [en / 100, yuk / 100] == ik else f" (kural {round(ik[0] * 100)} × {round(ik[1] * 100)} der)")})
    if kapsam.get("dis_kapi", True) and dis_kapi:
        kp.append({"kalem": "Kompozit çelik kapı", "boyut": "90 × 210", "adet": len(dis_kapi), "durum": "model", "formul": "dış kapı sayısı; ölçü gerçek listelerden"})
    if kapsam.get("pencere", True):
        say: dict[str, int] = {}
        for a in y["acikliklar"]:
            if a["tur"] == "pencere":
                say[a.get("etiket") or f"{a['en']}/{a['yuk']}"] = say.get(a.get("etiket") or f"{a['en']}/{a['yuk']}", 0) + 1
        kp += [{"kalem": ("PVC vasistas" if ad == "60/40" else "PVC pencere"), "boyut": ad, "adet": n, "durum": "model"} for ad, n in say.items()]
    # çelik
    ek_duvarlar = []
    if gr.get("ek"):
        prof = sinif["ek"]["profil"]
        ek_duvarlar.append({"ad": "Müştemilat duvar panelleri", "profil": prof, "birim_taraf": "dis" if prof in kur["celik"]["duvar_kg_m"]["deger"]["dis"] else "ic",
                            "boy_m": round(m["ek_cevre_m"], 2), "yukseklik_m": round(m["ek_ortalama_yukseklik_m"], 3), "panel_adedi": gr["ek"]["adet"],
                            "not": "dış 80 × 45 × 0,8 için motorda birim ağırlık yok; iç duvarın 80 × 45 × 0,8 değeri kullanıldı (varsayım). Boy: dışa bakan yüzlerin toplamı; yükseklik ortalama"})
    if gr.get("korkuluk"):
        kork = [d for d in y["duvarlar"] if d["sinif"] == "korkuluk"]
        boy = sum(d["boy"] for d in kork) / 100
        alan = sum(d["boy"] * yapi._yukseklik(d) for d in kork) / 1e4
        ek_duvarlar.append({"ad": "Veranda korkuluğu ve giriş çerçevesi", "profil": sinif["korkuluk"]["profil"], "birim_taraf": "dis", "boy_m": round(boy, 2),
                            "yukseklik_m": round(alan / boy, 3), "panel_adedi": gr["korkuluk"]["adet"],
                            "not": "kural yok: dış duvarın birim ağırlığı yüksekliğe oranlandı (varsayım). " + ", ".join(f"{d['ad']} {sade(d['boy'])} × {sade(yapi._yukseklik(d))}" for d in kork)})
    for b in m["baca"]:
        ek_duvarlar.append({"ad": "Baca karkası", "profil": sinif["baca"]["profil"], "birim_taraf": "dis", "boy_m": round(b["cevre_m"], 2), "yukseklik_m": round(b["boy_m"], 3),
                            "panel_adedi": 4, "not": "kural yok: dış duvarın birim ağırlığı bacanın çevresi ve boyuyla (varsayım); dört dar panel"})
    dikmeler = [d for d in y["duvarlar"] if d["sinif"] == "kolon"]
    kirisler = t.get("kirisler", [])
    makas = ct.get("makaslar") or {}
    makas_adedi = sum(v.get("adet", 0) for v in makas.values()) or None
    celik = {
        "dis": {"profil": sinif["dis"]["profil"], "boy_m": round(m["bina_cevre_m"], 2), "panel_adedi": panel_tahmini("dis") if tahmin else gr["dis"]["adet"],
                "not": et_notu if tahmin else "panel adedi modelden (duvar panelleri)"},
        "ic": ({"profil": sinif["ic"]["profil"], "boy_m": round(m["ic_boy_m"], 2), "panel_adedi": panel_tahmini("ic") if tahmin else gr["ic"]["adet"],
                "not": et_notu if tahmin else "boy: kaplanmış yüzler arasında (karkas boyu " + tr(m["ic_karkas_boyu_m"], 2) + " m); panel adedi modelden"} if gr.get("ic") else None),
        "ek_duvarlar": ek_duvarlar,
        "dikme": ({"profil": f"80x45x{ev['dikme']}", "adet": len(dikmeler), "boy_m": dikmeler[0]["yukseklik"] / 100,
                   "not": t.get("dikme_notu", "modelden")} if dikmeler else None),
        "kiris": ({"profil": f"80x45x{ev['kiris']}", "boy_m": round(sum(max(k["kutu"][2] - k["kutu"][0], k["kutu"][3] - k["kutu"][1]) for k in kirisler) / 100, 2),
                   **({} if tahmin else {"adet": len(kirisler), "not": "kiriş boyu ve adedi modelden (" + ", ".join(k["ad"] for k in kirisler) + ")"})} if kirisler else None),
        "cati": {"tip": ct["tip"], "profil": f"80x45x{ev['cati']}", "plan_m2": round(mc["makasli_plan_m2"], 2), "oturum_m2": round(m["oturum_m2"], 2),
                 **({"panel_adedi": makas_adedi, "not": f"plan: makaslı çatının saçak dahil planı; adet modelden ({makas_adedi} makas)"} if makas_adedi else {})},
        "tavan_paneli_m2": round(sum(o["alan_m2"] for o in m["odalar"]) + m["veranda_brut_m2"], 2) if yontem == "panel" else None,
        "cati_paneli_m2": round(mc["yuzey_m2"], 2) if yontem == "panel" else None,
        "ek_cati_paneli": ({"oturum_m2": round(m["ek_oturum_m2"], 2), "plan_m2": round(mc["panelli_plan_m2"], 2), "adet": 1,
                            "not": "ek yapının çatısı çatı paneliyle kapatılır (proje notu); 100 m² için verilen ağırlık ek yapının oturum alanına oranlandı; adet modelden"} if mc["panelli_plan_m2"] else None),
    }
    panel_toplam = (gr["dis"]["adet"] + (gr.get("ic") or {}).get("adet", 0) + sum(x["panel_adedi"] for x in ek_duvarlar) + len(dikmeler) + len(kirisler)
                    + (makas_adedi or 0) + (1 if mc["panelli_plan_m2"] else 0))
    duvar_paneli = sum(gr[s]["adet"] for s in ("dis", "ic", "ek", "korkuluk") if gr.get(s))
    g = {
        "sema": "portman.yukleme_girdisi/0.5-taslak",
        "ad": f"{t['kod']} · {t['ad']}",
        "kaynak": kaynak,
        "bina_m2": round(m["oturum_m2"]),
        "oturum_m2": round(m["oturum_m2"], 2),
        "dis_olcu_m": [round(v / 100, 3) for v in m["dis_olcu_cm"]],
        "kapali_olcu_m": [round(v / 100, 3) for v in m["kapali_olcu_cm"]],
        "kat_adedi": 1,
        "oda_sayisi": len(odalar),
        "kat_yuksekligi_m": kat_h,
        "celik": celik,
        **({} if tahmin else {"celik_panel_adedi": panel_toplam, "duvar_paneli_adedi": duvar_paneli}),
        "dis": {
            "cevre_m": round(m["bina_cevre_m"], 3), "duvar_m2": round(m["dis_brut_m2"], 3), "duvar_kalinligi_m": None, "karkas_mm": int(round(next(d for d in y["duvarlar"] if d["sinif"] == "dis")["kalinlik"] * 10)),
            "kolon_kiris": m["kolon_kiris"], "kolon_kiris_varsayim": False,
            "alin_m2": [k["alan_m2"] for k in m["kalkanlar"]],
            "ek_m2": [{"ad": f"baca (çatının üstünde kalan {tr(b['cati_ustu_m'], 2)} m)", "alan_m2": b["alan_m2"]} for b in m["baca"]],
            "bosluklar": [{k: v for k, v in b.items() if k != "tur"} for b in m["dis_bosluklar"]],
            "dis_osb": False,
            "nem_bariyeri": "nem_bariyeri" in t["yuz_kaplamalari"]["dis"].get("malzeme", []),
            "yuzler": m["dis_yuzler"],
        },
        "odalar": odalar,
        "ic_kapi_adedi": len(ic_kapi),
        "ic_duvar_boyu_m": round(m["ic_boy_m"], 2),
        "ic_osb_tum_duvarlar": "osb" in t["yuz_kaplamalari"]["ic"].get("malzeme", []),
        **({"osb_takviye": {"duvarlar": [{k_: x[k_] for k_ in ("mahal", "duvar", "duvar_adi", "neden", "boy_m", "bosluk_m2")} for x in m["osb_takviye"]["duvarlar"]],
                            "brut_m2": round(m["osb_takviye"]["brut_m2"], 2), "bosluk_m2": round(m["osb_takviye"]["bosluk_m2"], 3), "net_m2": round(m["osb_takviye"]["net_m2"], 2)},
            "osb_takviye_teyit": t["osb_takviye"].get("teyit")} if m.get("osb_takviye") else {}),
        "yalitim": {k: round(v, 3) for k, v in m["yalitim"].items()},
        "veranda_tavan_cevresi_m": round(m["veranda_brut_cevre_m"], 2) if veranda else None,
        "elektrik_odalar": elektrik_odalar if all(o["islev"] for o in elektrik_odalar) else None,
        "tavan_m2": {"beyaz": round(sum(o["alan_m2"] for o in odalar if o["tur"] == "beyaz"), 2),
                     "yesil": round(sum(o["alan_m2"] for o in odalar if o["tur"] == "yesil") + m["veranda_brut_m2"], 2)},
        **({"veranda_m2": {"brut": round(m["veranda_brut_m2"], 2), "net": round(m["veranda_m2"], 2), "not": "tavan ve köşebent hesabında brüt (dış ölçüyle) alınır; 0.4'teki gibi"}} if veranda else {}),
        **({"tavan_omegasi_m2": round(sum(o["alan_m2"] for o in m["odalar"] if not o["cati_paneli_altinda"]) + m["veranda_brut_m2"], 2)}
           if any(o["cati_paneli_altinda"] for o in m["odalar"]) else {}),
        "cati": {
            "tip": ct["tip"], "yontem": yontem, "kaplama": kaplama, "egim": max(d["egim"] for d in mc["duzlemler"]),
            "yuzey_m2": round(mc["yuzey_m2"], 2),
            "sacak_kenarlari_m": mc["sacak_kenarlari_m"], "sacak_boyu_toplam_m": round(mc["sacak_m"], 2),
            "cephe_kenarlari_m": mc["cephe_kenarlari_m"], "kose_adedi": mc["kose_adedi"],
            "kose_kaynak": "dere hatlarının (saçakların) uçları; iki saçağın buluştuğu köşe tek sayılır",
            "mahya_hatti_m": round(mc["mahya_m"] + mc["kirma_m"], 2), "mahya_dokumu_m": {"mahya": round(mc["mahya_m"], 2), "kirma": round(mc["kirma_m"], 2)},
            "ters_mahya_m": round(mc["vadi_m"], 2) or None,
            "alin_saci_m": round(mc["alin_m"], 2) or None,
            "duvar_dibi_m": round(mc["duvar_dibi_m"], 2) or None,
            "asik_boyu_m": round(mc["asik_boyu_m"], 2) if yontem == "omega_asik" else None,
            "asik_notu": ", ".join(f"{ad} {len(sr)} sıra" for ad, sr in mc["asik_siralari"].items()),
            "dizilim": {"satirlar": [{"boy_m": round(b / 100, 4), "adet": n} for b, n in dz["boy_adet"].items()], "adet": dz["adet"], "kapatma_m": dz["kapatma_cm"] / 100,
                        "tasma_cm": dz["tasma_cm"], "kesim_payi_mm": dz["kesim_payi_cm"] * 10, "tam_boy": dz["tam_boy"], "cift": dz["cift"], "tek": dz["tek"], "karma": dz["karma"],
                        "panel_m2": round(dz["panel_m2"], 2), "uzatma": dz["uzatma"], "taban": dz["taban"]},
            "cati_boyu_m": round(mc.get("cati_boyu_m", 0), 3) or None, "bina_eni_m": round(mc.get("bina_eni_m", 0), 3) or None,
            "sacak_alti": "sac" if yontem == "omega_asik" else ct.get("sacak_alti", "boardex"),
            **({"sacak_alti_eni_m": ct.get("sacak", 30) / 100} if yontem == "panel" else {"sacak_omegasi": "Saçak omegası"}),
            **({"sacak_yuzu_m2": round(mc["sacak_yuzu_m2"], 2)} if yontem == "panel" and ct.get("sacak_yuzu", "boardex") == "boardex" else {}),
        },
        "kapi_pencere": kp,
        "pencere_dahil": kapsam.get("pencere", True),
        "boya_dahil": kapsam.get("boya", True),
        "vitrifiye_dahil": kapsam.get("vitrifiye", True),
        "bayi": {"gruplar": {"Sıhhi tesisat": bool(kapsam.get("sihhi_tesisat", True)), "Elektrik": bool(kapsam.get("elektrik", True))},
                 "not": "kapsam: projenin teknik özellikleri ve açıklama notları (alıcıya ait olanlar listeye girmez)"},
        "uyarilar": uyari,
    }
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--cikti", type=Path, default=BURADA / "sonuc")
    ap.add_argument("--kaynak", default=None)
    a = ap.parse_args()
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    kur = json.loads((YUKLEME / "kurallar.json").read_text(encoding="utf-8"))
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    m = metraj(y, c, kur)
    g = girdi(y, c, m, kur, a.kaynak or f"Yapı Tanımı 0.5 ({a.tanim.name})")
    a.cikti.mkdir(parents=True, exist_ok=True)
    kod = t["kod"].replace("Ç", "C").replace("-", "")
    (a.cikti / f"{kod}_girdi.json").write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı:", f"{kod}_girdi.json")
    for o in g["odalar"]:
        print(f"  {o['ad']:16s} {o['tur']:6s} çevre {o['cevre_m']:6.2f} m  alan {o['alan_m2']:6.2f} m²  duvar brüt {o['duvar_brut_m2']:6.2f}  boşluk {sum(o['bosluk_m2']):5.2f} m² ({len(o['bosluk_m2'])})")
    print(f"  dış yüzler brüt {m['dis_brut_m2']:.2f} net {m['dis_net_m2']:.2f} m² · bina çevresi {m['bina_cevre_m']:.2f} m · oturum {m['oturum_m2']:.2f} m²")
    return 0


if __name__ == "__main__":
    sys.exit(main())
