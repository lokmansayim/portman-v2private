"""İE-08 GM3 · Ç8201'in iki zinciri birleşti: Yapı Tanımı 0.5 (`modeller/C8201.json`) genel motordan geçirilir ve 0.4 hattının dondurulmuş
sonuçlarıyla (`testler/genel/beklenen/C8201_*_0.4.json`; `deneme/2026-10-03_yukleme/sonuc/` kopyası) karşılaştırılır:
metraj (mahal, dış çevre, çelik, çatı, OSB takviye), iki yükleme listesi satır satır, genel dizilim ↔ kırma dizilimi, panel boyu kuralı iki
motorda, Eylül 2026 katmanının değişmezleri. `deneme/2026-10-06_kor_test/saglama.py`'nin (6 Ekim 2026) ana koda taşınmış hâli; kural seti
0.19 pimiyle koşar. Bilinen fark: genel motor mahyanın iki yanına ayrıca mahya aşığı eklemez (aşık yalnız yöntem B'de)."""
from __future__ import annotations
import copy
import itertools
import json
import math
import os
import random
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_acilim, cati_genel, girdi_genel, kural, yapi, yukleme  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
BEKLENEN = Path(__file__).resolve().parent / "beklenen"


def yakin(a, b, tol=0.006):
    return abs(a - b) <= tol


@pytest.fixture(scope="module")
def zincir():
    eski_env = os.environ.get("PORTMAN_KURALLAR")
    os.environ["PORTMAN_KURALLAR"] = str(SET)
    try:
        kur = kural.oku()
        t = json.loads((KOK / "modeller" / "C8201.json").read_text(encoding="utf-8"))
        y = yapi.kur(t)
        c = cati_genel.cati_kur(t["cati"], kur)
        m = girdi_genel.metraj(y, c, kur)
        g = girdi_genel.girdi(y, c, m, kur, "C8201.json")
        eski = json.loads((BEKLENEN / "C8201_girdi_0.4.json").read_text(encoding="utf-8"))
        yield {"kur": kur, "t": t, "y": y, "c": c, "m": m, "g": g, "eski": eski}
    finally:
        if eski_env is None:
            os.environ.pop("PORTMAN_KURALLAR", None)
        else:
            os.environ["PORTMAN_KURALLAR"] = eski_env


def test_metraj_04_ile_ayni(zincir):
    g, eski, m = zincir["g"], zincir["eski"], zincir["m"]
    sorun: list[str] = []
    for o in eski["odalar"]:
        n = next((x for x in g["odalar"] if x["ad"] == o["ad"]), None)
        if n is None:
            sorun.append(f"mahal yok: {o['ad']}"); continue
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
    for k in ("bina_m2", "dis_olcu_m", "kapali_olcu_m", "oda_sayisi", "ic_kapi_adedi", "ic_duvar_boyu_m", "veranda_tavan_cevresi_m", "tavan_m2"):
        if eski[k] != g[k]:
            sorun.append(f"{k}: {eski[k]} / {g[k]}")
    if not yakin(eski["dis"]["cevre_m"], g["dis"]["cevre_m"]) or not yakin(eski["dis"]["cevre_m"] * 2.7, g["dis"]["duvar_m2"]):
        sorun.append(f"dış çevre: {eski['dis']['cevre_m']} / {g['dis']['cevre_m']} · brüt {g['dis']['duvar_m2']}")
    for k in ("kolon_kiris", "alin_m2", "karkas_mm"):
        if eski["dis"][k] != g["dis"][k]:
            sorun.append(f"dis.{k}: {eski['dis'][k]} / {g['dis'][k]}")
    bos = lambda L: sorted((b["ad"], b["adet"], b["en"], b["boy"]) for b in L)
    if bos(eski["dis"]["bosluklar"]) != bos(g["dis"]["bosluklar"]):
        sorun.append("dış boşluklar farklı")
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
    for k in ("tip", "yontem", "kaplama", "egim", "yuzey_m2", "sacak_boyu_toplam_m", "cephe_kenarlari_m", "kose_adedi", "mahya_hatti_m", "bina_eni_m",
              "cati_boyu_m", "sacak_alti", "sacak_alti_eni_m", "sacak_yuzu_m2"):
        if eski["cati"][k] != g["cati"].get(k):
            sorun.append(f"cati.{k}: {eski['cati'][k]} / {g['cati'].get(k)}")
    if sorted(eski["cati"]["sacak_kenarlari_m"]) != sorted(g["cati"]["sacak_kenarlari_m"]):
        sorun.append("cati.sacak_kenarlari_m farklı")
    eo, no = eski["osb_takviye"], g.get("osb_takviye")
    if not no or [(x["mahal"], x["boy_m"], x["bosluk_m2"]) for x in eo["duvarlar"]] != [(x["mahal"], x["boy_m"], x["bosluk_m2"]) for x in no["duvarlar"]] \
            or (eo["brut_m2"], eo["net_m2"]) != (no["brut_m2"], no["net_m2"]):
        sorun.append("osb_takviye farklı")
    # aşık boyu (yöntem B): eski kural halkalarla, genel motor yüz yüz sıralarla; 8 halka = her yüzde 8 sıra (mahya aşığı hariç; bilinen fark)
    halkalar = sum(2 * ((11.54 - 2 * i * 0.6 / math.sqrt(1 + 0.33 ** 2)) + (8.10 - 2 * i * 0.6 / math.sqrt(1 + 0.33 ** 2))) for i in range(8))
    if not yakin(halkalar, m["cati"]["asik_boyu_m"], 0.02):
        sorun.append(f"aşık boyu (halkalar): {halkalar:.2f} / {m['cati']['asik_boyu_m']:.2f}")
    assert sorun == [], sorun


@pytest.mark.parametrize("kaplama, eski_ad", [(None, "C8201_yukleme_0.4.json"), ("sandvic_panel", "C8201_kaplama_sandvic_panel_0.4.json")])
def test_yukleme_listesi_04_ile_satir_satir_ayni(zincir, kaplama, eski_ad):
    gk = copy.deepcopy(zincir["g"])
    if kaplama:
        gk["cati"]["kaplama"] = kaplama
    yeni = yukleme.hesapla(gk, zincir["kur"])["satirlar"]
    esk = json.loads((BEKLENEN / eski_ad).read_text(encoding="utf-8"))["satirlar"]
    anahtar = lambda s: (s["grup"], s["kalem"], s["boyut"], s["adet"], None if s["kg"] is None else round(s["kg"]))
    a, b = [anahtar(s) for s in esk], [anahtar(s) for s in yeni]
    assert a == b, {"0.4'te var genelde yok": [x for x in a if x not in b][:5], "genelde var 0.4'te yok": [x for x in b if x not in a][:5],
                    "sira": sorted(map(str, a)) == sorted(map(str, b))}


def _kirma(px, py, egim):
    y0 = py / 2
    f = lambda ad, plan, yuk, sac: {"ad": ad, "plan": plan, "yukari": yuk, "egim": egim, "sacak_kotu": 280.0, "sacak": sac}
    return [f("ön", [[0, 0], [px, 0], [px - y0, y0], [y0, y0]], [0, 1], {"y": 0}), f("sol", [[0, py], [0, 0], [y0, y0]], [1, 0], {"x": 0}),
            f("arka", [[px, py], [0, py], [y0, y0], [px - y0, y0]], [0, -1], {"y": py}), f("sağ", [[px, 0], [px, py], [px - y0, y0]], [-1, 0], {"x": px})]


def test_genel_dizilim_kirma_dizilimiyle_ayni(zincir):
    fark, deneme = [], 0
    for (px, py), egim, kap, ek in itertools.product([(1154, 810), (1000, 1000), (1260, 640), (900, 700), (1432, 868), (1154, 813), (2010, 915)],
                                                     [0.33, 0.25, 0.4], [100, 87, 80, 110], [0, 1, 2, 3, 10]):
        dz = [cati_genel.duzlem_kur(d) for d in _kirma(px, py, egim)]
        kn = cati_genel.kenarlari_bul(dz)
        boy = math.ceil((py / 2 * math.sqrt(1 + egim ** 2) + 5) * 10 - 1e-9) / 10 + ek
        for paylas in (True, False):
            a = cati_genel.dizilim(dz, kn, kap, 5.0, 0.5, paylas, boylar=[boy])["adet"]
            b = cati_acilim.dizilim(px / 100, py / 100, egim, kap / 100, boy / 100, paylas, "sol", 0.005, 0.05)["adet"]
            deneme += 1
            if a != b:
                fark.append(f"plan {px} × {py}, eğim {egim}, kapatma {kap}, boy {boy}, paylaş {paylas}: genel {a} / kırma {b}")
    assert deneme == 840 and fark == [], fark[:5]


def test_panel_boyu_kurali_iki_motorda_ayni(zincir):
    kur = zincir["kur"]
    assert kur["kirma_cati_dizilim"]["deger"]["baslangic"] == "sol", "kural `sol` değil; karşılaştırma o gün yeniden kurulur"
    rnd = random.Random(20261007)
    yv_mm = (kur.get("panel_boyu_yuvarlama_mm") or {}).get("deger") or 1
    tasma_m = kur["cati_kaplama_tasma_m"]["deger"]
    fark, deneme, uzayan = [], 0, 0
    for _ in range(50):
        px = round(rnd.uniform(6, 16), rnd.choice((1, 2)))
        py = round(rnd.uniform(4, px), rnd.choice((1, 2)))
        egim = rnd.choice((0.25, 0.30, 0.33, 0.40))
        dz = [cati_genel.duzlem_kur(d) for d in _kirma(round(px * 100), round(py * 100), egim)]
        kn = cati_genel.kenarlari_bul(dz)
        taban = math.ceil((py / 2 * math.sqrt(1 + egim ** 2) + tasma_m) * 1000 / yv_mm - 1e-9) * yv_mm / 1000
        for kaplama in ("tek_kat_panel", "trapez_sac", "osb_kiremit"):
            deneme += 1
            gn = girdi_genel._dizilim({"duzlemler": dz, "kenarlar": kn}, kur, kaplama)
            kr_ = cati_acilim.kural_dizilimi(kur, {"plan_m": [px, py], "egim": egim, "panel_boyu_m": taban, "panel_boyu_kaynak": "kural"}, kaplama)
            genel = (gn["adet"], [round(x * 10) for x in gn["boylar_cm"]], [u.get("neden", "var") for u in gn["uzatma"]],
                     gn["taban"]["adet"], [round(x * 10) for x in gn["taban"]["boylar"]])
            kirma_ = (kr_["adet"], [round(kr_["boy_m"] * 1000)], [kr_["uzatma"].get("neden", "var")] if kr_["uzatma"] else [],
                      kr_["taban_adet"], [round(kr_["taban_boy_m"] * 1000)])
            uzayan += bool(kr_["uzatma"])
            if genel != kirma_:
                fark.append(f"plan {px} × {py} m, eğim {egim}, {kaplama}: genel {genel} / kırma {kirma_}")
    assert deneme == 150 and fark == [], fark[:5]


def test_eylul_2026_katmaninin_degismezleri(zincir):
    kur, g = zincir["kur"], zincir["g"]
    katmansiz = {a: v for a, v in kur.items() if a != "sablon_2026"}
    girdiler = [("genel Ç8201", g), ("0.4 girdisi", json.loads((BEKLENEN / "C8201_girdi_0.4.json").read_text(encoding="utf-8")))]
    oz = lambda x: (x["grup"], x["kalem"], x["boyut"], x["adet"], x["olcu"], x["brut"], x["birim"], x["kg"], x["formul"])
    sorun = []
    for ad, gi in girdiler:
        v = yukleme.hesapla(copy.deepcopy(gi), kur)
        if any(x["durum"] == yukleme.SABLON for x in v["satirlar"]):
            sorun.append(f"katman ({ad}): varsayılan hesapta `sablon` durumlu satır var")
        v0 = yukleme.hesapla(copy.deepcopy(gi), katmansiz)
        fark = [(x["kalem"], y_["kalem"]) for x, y_ in zip(v["satirlar"], v0["satirlar"]) if (oz(x), x["durum"]) != (oz(y_), y_["durum"])]
        if fark or len(v["satirlar"]) != len(v0["satirlar"]):
            sorun.append(f"katman ({ad}): varsayılan hesap, katman kurallardan silinince değişiyor: {fark[:3]}")
        gs = copy.deepcopy(gi); gs["sablon"] = "2026"
        k_ = yukleme.hesapla(gs, kur)
        taban = [oz(x) for x in v["satirlar"]]
        for x in k_["satirlar"]:
            farkli = oz(x) not in taban
            if farkli != (x["durum"] == yukleme.SABLON):
                sorun.append(f"katman ({ad}): {x['kalem']} {'farklı ama `sablon` değil' if farkli else '`sablon` ama varsayılandakiyle aynı'}")
    assert sorun == [], sorun
