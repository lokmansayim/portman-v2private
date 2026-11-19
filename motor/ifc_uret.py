"""İE-04 · İş Emri → IFC4 (IfcOpenShell). 23.09 denemesinin (deneme/2026-09-23: 13_Kiyas/kod/motor_girdi.py + ifc_uret.py,
11_Blender/kod/blender_hazirla.py sabitleri) Motor hattına alınmış hâlidir; geometri yeniden yazılmadı.

Girdi Motor'un kurallı planıdır (motor.geometry.kur); kodlar Motor DXF'indeki BOM bloklarıyla aynıdır. Aynı İş Emri'nden PDF, bayi
görseli ve bu IFC üretilir: plan ile 3D ayrı düzenlenemez.

Model düzeni:
  IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey "Zemin Kat"
  Panolar      : IfcWall (tip: PE-DIS-100 / PE-IC-60, malzeme katmanları) + Pset_WallCommon + PortatifEv_Pano + Qto_WallBaseQuantities
  Boşluklar    : IfcOpeningElement → IfcWindow / IfcDoor; iç kapı yalnız boşluk (kapsam dışı)
  Mahaller     : IfcSpace + Qto_SpaceBaseQuantities (net alan çizimden)
  Döşeme, çatı (GABLE_ROOF), makaslar, veranda dikme ve kirişleri, bağlantı profilleri.
Birim: metre (girdi cm). Şema doğrulaması üretim doğruluğu değildir.

    from motor import ifc_uret; ifc_uret.uret(is_emri, Path("cikti.ifc"), baslik="…")
"""
from __future__ import annotations
import json, math
from pathlib import Path

import numpy as np
import ezdxf
from ezdxf import bbox as ebbox
from shapely.ops import polylabel
import ifcopenshell
import ifcopenshell.api
from ifcopenshell.util.shape_builder import ShapeBuilder

from . import geometry as G
from . import veranda as VR
from .dxf_out import Cizici
from .katalog import Katalog

CM = 0.01
api = ifcopenshell.api.run
MOD = 125.5
DUVAR_H = 250.0
LENTO = 50.0
KAPI_UST = DUVAR_H - LENTO                                            # 200: lento kuralı
H_PROFIL_TASMA_CM = 0.4       # İE-12, yalnız 3B gösterim: H şeridi duvar yüzünden taşar (görünüşte seçilsin); kesim ölçüsü değil


def _m(v):
    return float(v) * CM


def _r(v, n=2):
    return round(float(v), n)


def pano_sinifi(L, t):
    if L <= 11.5:
        return "kose"
    if abs(L - MOD) <= 1.2:
        return "tam"
    if abs(L - MOD / 2) <= 1.2:
        return "yarim"
    return "ozel"


def hazirla(ie: dict) -> dict:
    plan = G.kur(ie)
    girinti = {}
    from . import cati_serit
    if plan.girintili:                                # İE-24: çatı ve makaslar çizimdeki çatıdan (ana çatı + cumba), döşeme gövdenin dış çizgisinden
        from . import cati_capraz, cati_prefabrik
        cumbali = (ie.get("cati") or {}).get("tip") == "besik_cumba"
        capraz = cumbali and cati_prefabrik.ana_geri_cm(ie["cati"], plan) is not None
        girinti = {"govde": [[_r(x), _r(y)] for x, y in list(G.govde_cokgeni(plan).exterior.coords)[:-1]],   # İE-15 K6 (TK-04 r07): ana
                   "cati_serit": (cati_capraz.tanim if capraz else _cikintili_cumba_tanimi if cumbali else cati_serit.tanim)(plan, ie)}
        # makaslar geri çekilen çapraz cumba; BK-46: çıkıntılı çapraz cumba (82, 91 m²) ve iki cumba (45 m²) `_cikintili_cumba_tanimi`
        # (eskiden 3D kurulmuyordu); kurulamazsa PrefabrikCatiHatasi (IsEmriHatasi): yanlış çatı çizilmez
    elif cati_serit.mahal_catilari_var(ie):           # İE-17 PR-2 (AP-09): kendi çatısı olan açık mahal ana çatıdan çıkar; çatı çizimdekinin aynısı
        girinti = {"cati_serit": cati_serit.tanim(plan, ie)}
    elif (ie.get("cati") or {}).get("tip") == "kirma":   # BK-46: kırma çatı çizimdekinin aynısı (`cati_prefabrik.cati`); eskiden beşik çiziliyordu
        girinti = {"cati_kirma": _kirma_girdisi(plan, ie)}
    elif (ie.get("cati") or {}).get("tip") == "besik_cumba":    # İE-15 K6: çıkıntısız çapraz cumba; çatı çizimdekinin aynısı (`cati_capraz`)
        from . import cati_capraz
        girinti = {"cati_serit": cati_capraz.tanim(plan, ie)}
    kat = Katalog()
    c = Cizici(plan, kat)
    c.ciz_plan(0.0, 0.0, "ANA", "", "")          # BOM kodlu INSERT'ler (yalnız ANA rolü)
    etiket = {"".join(k.split()): v for k, v in ie.get("altin_beklenti", {}).get("alanlar", {}).items()}

    def kalem(kod):
        m = kat.malzemeler.get(kod, {})
        return f"{kod} {m.get('label', '')}".strip()

    panolar, acikliklar, kubbe_tabani = [], [], {}
    for d in plan.duvarlar:
        for p in d.panolar:
            if p.acilim is not None and p.acilim.tur == "kubbe":   # BK-46: kubbenin tabanı düz duvarda boşluk (çizimdeki gibi, `dxf_out.ciz_plan`);
                kubbe_tabani[(d.id, round(p.a0, 3))] = [_r(v) for v in p.rect()]   # kubbe `kubbeler`'de (eskiden KeyError 'kubbe', 3D yoktu)
                continue
            _, _, kod = c.pano_blok(p)
            x0, y0, x1, y1 = p.rect()
            L, t = p.boy, 2 * d.h
            pr = {"id": len(panolar), "rect": [_r(x0), _r(y0), _r(x1), _r(y1)], "yon": d.yon, "boy": _r(L), "kalinlik": _r(t),
                  "tur": d.tur, "sinif": pano_sinifi(L, t), "kod": kod, "kalem": kalem(kod), "acikliklar": []}
            for ac in p.aciklar:                                # D-46: karkaslı panoda birden çok açıklık
                g = p.bosluk_dortgeni(ac)
                a0, a1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
                if ac.tur == "pencere":
                    pk = G.pencere_kurali(ac.olcu)                  # BK-13: eşik = 200 − boy (bugünkü üçü BOM notlarındaki 80, 20, 160)
                    en, boy = pk.en, pk.boy
                    z0, z1 = pk.esik, pk.ust                        # İE-27 madde 11: 200'ü geçen pencere döşemeden, kısaltılmaz
                    dk = c.dograma[ac.olcu][1]
                    a = {"tur": "pencere", "olcu": ac.olcu}
                else:
                    z0, z1 = 0.0, G.ust_kot()                       # BK-23 (D-55): kapı üstü pencereninkiyle aynı kot (`yapi.lento_cm` yoksa 200)
                    dk = c.dograma["ic82"][1] if ac.tur == "ic_kapi" else (c._dis_kapi_blok(ac.genislik)[1] if ac.tur == "dis_kapi" else None)
                    a = {"tur": "kapi", "alt_tur": ac.tur, "genislik": _r(ac.genislik)}
                a.update({"yon": d.yon, "a0": _r(a0), "a1": _r(a1), "c": _r(d.c), "z0": z0, "z1": z1, "panolar": [pr["id"]],
                          "kod": dk, "kalem": kalem(dk) if dk else "Kapısız geçiş (malzeme değil)", "arasi": list(ac.arasi) if ac.arasi else None,
                          "mahal": ac.mahal})
                pr["acikliklar"].append({"aciklik": len(acikliklar), "a0": a["a0"], "a1": a["a1"], "z0": z0, "z1": z1})
                acikliklar.append(a)
            panolar.append(pr)

    # bağlantı / dikme / veranda profili: Motor DXF'indeki ANA INSERT'lerden (kod + gerçek blok geometrisinin kutusu)
    baglantilar = []
    for e in c.msp.query("INSERT"):
        if not e.has_xdata("AI_BOM"):
            continue
        kod, rol = [v for _, v in e.get_xdata("AI_BOM")]
        if rol != "ANA" or kod[0] not in "BV":
            continue
        bb = ebbox.extents([e])
        x0, y0, x1, y1 = bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y
        m = kat.malzemeler.get(kod, {}); lab = m.get("label", "")
        tur = "dikme" if "dikme" in lab.lower() else ("veranda_profil" if kod[0] == "V" else "baglanti")
        baglantilar.append({"kod": kod, "kalem": kalem(kod), "tur": tur, "rect": [_r(x0), _r(y0), _r(x1), _r(y1)], "blok": e.dxf.name})

    # İE-12 (Lokman 13.10.2026 09:39): her iki panonun arasında H birleştirme profili; dışarıdan 5 cm, eke tam ortalı. Yalnız yeni anahtarlı
    # İş Emri'nde (prefabrik bayi sunumu); eski IFC'ler değişmez. Şerit duvar gövdesinden her yüzde 0,4 cm taşar ki görünüşte seçilsin.
    # Üçlü H olan eklerde şerit yalnız görünümdür (BOM satırı bağlantılarda, B03 / B05).
    # BK-50 (Lokman, kart 16 Kasım 2026 12:09:48 "Evet, ayrı PR"): eklerin yeri ve türü yükleme listesinin kaynağından
    # (`prefabrik_liste.ek_yerleri`, D-28 madde 1): kubbenin iki ucunda H yok (D-54); dış duvarın ekine T ile gelen iç duvarda 3'lü H
    # (İE-27). Motor'un DXF'inde bu T'nin bloğu yok: bağlantı (B05, dış 3'lü H) buradan, DXF'teki 3'lü H bloğunun biçiminde kurulur
    # (dış duvarın kalınlığı × iç duvarın kalınlığı, eke ortalı). Kart modeli ve montaj rehberi 3D'yi okur.
    pano_ekleri = []
    if G.yeni_anahtar_var(ie):
        from . import prefabrik_liste as PL
        w = G.H_PROFIL_GORUNEN_CM / 2.0
        dis_t = [b for b in baglantilar if "_UCLU_H_DIS_" in b["blok"]]
        kod_t = c.kat.baglanti("uclu_h_dis")
        for k in PL.ek_yerleri(plan):
            e, cc, t = k["e"], k["c"], k["h"] + H_PROFIL_TASMA_CM
            rect = [e - w, cc - t, e + w, cc + t] if k["yon"] == "x" else [cc - t, e - w, cc + t, e + w]
            pano_ekleri.append({"duvar": k["duvar"], "cins": k["cins"], "rect": [_r(v) for v in rect]})
            if k.get("ie27") and not any(abs((b["rect"][0] + b["rect"][2]) / 2 - k["x"]) <= k["h"] + 3.5
                                         and abs((b["rect"][1] + b["rect"][3]) / 2 - k["y"]) <= k["h"] + 3.5 for b in dis_t):
                yi = G.T_IC / 2.0
                r = [e - yi, cc - k["h"], e + yi, cc + k["h"]] if k["yon"] == "x" else [cc - k["h"], e - yi, cc + k["h"], e + yi]
                baglantilar.append({"kod": kod_t, "kalem": kalem(kod_t), "tur": "baglanti", "rect": [_r(v) for v in r],
                                    "blok": f"BOM_{kod_t}_UCLU_H_DIS_{G._mm(G.T_DIS)}x{G._mm(G.T_IC)}",
                                    "kaynak": "İE-27: dış duvarın ekine T ile gelen iç duvar (yükleme listesi; Motor DXF'inde blok yok)"})

    odalar, veranda = [], None
    dis_ad = {v["ad"] for v in plan.dis_verandalar}
    for ad, m in plan.mahaller.items():
        if ad in dis_ad:
            continue                                       # BK-14: taşan veranda kendi alanıyla `dis_verandalar`'da
        poly = m.poly.simplify(0.0)
        pl = polylabel(poly, tolerance=1.0)
        kayit = {"ad": ad, "etiket_m2": etiket.get("".join(ad.split())), "net_m2": _r(m.alan_m2, 4), "etiket_xy": [_r(pl.x), _r(pl.y)],
                 "poligon": [[_r(x), _r(y)] for x, y in list(poly.exterior.coords)[:-1]]}
        if m.ek:                                           # BK-46: kubbenin içi mahalin net alanında (`Mahal.ek`); 3D'de odanın hacmine kubbe
            kayit["ek_poligonlar"] = [[[_r(x), _r(y)] for x, y in list(e.exterior.coords)[:-1]] for e in m.ek]   # duvarının boyunca eklenir
        if m.acik:
            veranda = dict(kayit, tip="bina_ici", tasma_cm=0.0)
        else:
            odalar.append(kayit)

    cati = ie.get("cati", {})
    return {
        "sema": "portman.blender_girdi/0.2",
        "kaynak": {"dosya": f"İş Emri {ie.get('is_emri_no')} r{int(ie.get('revizyon', 1)):02d}",
                   "not": "Motor'un kurallı planı (G.kur). Kodlar Motor DXF'indeki BOM bloklarıyla aynı."},
        "kapsam": {"ic_kapi": True, "gecis_malzeme_degil": True},
        "bina": {"ad": f"{ie.get('talep', {}).get('musteri_adi', '')} — {ie['yapi']['grid']['x_pano']}×{ie['yapi']['grid']['y_pano']} pano",
                 "W": _r(plan.W), "H": _r(plan.H), "duvar_h": float(ie["yapi"].get("duvar_yuksekligi_cm", DUVAR_H)),
                 "lento": float(ie["yapi"].get("duvar_yuksekligi_cm", DUVAR_H)) - G.ust_kot(),   # 250 → 50; 280 / 300 → 80 / 100 (D-14; üst kot 200 çıkarım, DXF ile aynı); BK-23: `yapi.lento_cm`
                 "cati": {"tip": cati.get("tip", "besik"), "egim": float(cati.get("egim_yuzde", 33)) / 100, "sacak": float(cati.get("sacak_cm", 30)),
                          "topuk": float(cati.get("topuk_cm", 10)), "makas_yonu": ("y (derinlik)" if cati.get("makas_ekseni") == "y" else "x (kısa kenar)"),
                          **({"makas_ekseni": cati["makas_ekseni"]} if "makas_ekseni" in cati else {}), "renk": "antrasit"}},
        "panolar": panolar, "acikliklar": acikliklar, "baglantilar": baglantilar, "odalar": odalar, "veranda": veranda, "tefris": [],
        **({"pano_ekleri": pano_ekleri} if pano_ekleri else {}), **girinti,
        **({"dis_verandalar": [{"ad": v["ad"], "cephe": v["cephe"], "rect": [_r(t) for t in v["rect"]],
                                "cati": None if v["cati"]["tip"] == "cumba" else VR.cati(v, ie),   # BK-46: PC-38, çatısı ana çatının cumbası
                                "net_m2": _r(plan.mahaller[v["ad"]].alan_m2, 4),
                                **({"poligon": [[_r(x), _r(y)] for x, y in list(plan.mahaller[v["ad"]].poly.simplify(0.0).exterior.coords)[:-1]]}
                                   if v.get("nis") else {}),       # D-109: köşe boşluğuyla tek mahal
                                "etiket_m2": etiket.get("".join(v["ad"].split()))}
                               for v in plan.dis_verandalar]} if plan.dis_verandalar else {}),     # BK-14: dikme ve kiriş baglantilar'da
        **({"kubbeler": [_kubbe_girdisi(kb, kubbe_tabani, ie) for kb in plan.kubbeler]} if plan.kubbeler else {}),
        "kanit": {"motor_uyarilari": plan.uyarilar}, "uyari": [],
    }


def _kubbe_girdisi(kb: dict, tabanlar: dict, ie: dict) -> dict:
    """BK-46: kubbenin 3D girdisi, çizimdeki kubbenin aynısından (`G._kubbe_geometrisi`, `G.kubbe_sacagi`; D-54, Lokman 5 Kasım 2026 10:41
    ve 12:05): üç pano (yan 79, ön 125,5) kendi pencereleriyle, iki açılı köşe direği ve düz duvarın ucunda iki kama, kubbe duvarı 203 cm;
    düz duvarda tabanın üstünde ana duvarın bandı (kitapta "Kubbe özel pano 100 × 2500 × 500"; 3 cm kertikle kubbe duvarının üstünden duvar
    üstüne); çatı üç üçgen yüz: saçak kubbenin dış çizgisinden 18,5 dışarıda, kotu kubbe duvarı + topuk; tepe düz duvarda kubbenin ortasında,
    kubbe duvarının üstünden 35 cm. Makas üç (kitabın kubbe takımı "Kubbe makası" 3; biri düz duvar boyunca, ikisi tepeden ön köşelere)."""
    K = G.KUBBE
    topuk = float((ie.get("cati") or {}).get("topuk_cm", 10))
    taban = next(v for (did, a0), v in sorted(tabanlar.items()) if did == kb["duvar"] and abs(a0 - kb["u0"]) < 0.01)
    nok = lambda p: [_r(p[0], 4), _r(p[1], 4)]                                          # noqa: E731
    return {"mahal": kb["mahal"], "cephe": kb["cephe"], "yon": kb["yon"], "u0": _r(kb["u0"], 4), "u1": _r(kb["u1"], 4),
            "dis": [nok(p) for p in kb["dis"]], "ic": [nok(p) for p in kb["ic"]], "bant": [nok(p) for p in kb["bant"]],
            "panolar": [{"tur": q["tur"], "boy": float(q["boy"]), "pencere": q["pencere"], "dis_kenar": [nok(v) for v in q["dis_kenar"]],
                         "disari": [float(v) for v in q["disari"]]} for q in kb["panolar"]],
            "tepe": nok(kb["tepe"]), "sacak": [nok(p) for p in G.kubbe_sacagi(kb, K["sacak_cm"])], "taban": taban,
            "duvar_cm": K["duvar_cm"], "sacak_kotu": K["duvar_cm"] + topuk, "tepe_kotu": K["duvar_cm"] + K["tepe_cm"], "makas": int(K["makas"])}


def tek_uclu_ana_yerleri(ekler: list[float], a: float, b: float, h: float) -> list[float]:
    """BK-46: tek uçlu kırmanın ana makasları kalkan duvarının pano eklerinde (`a`, `b`: iki saçak duvarının ekseni). İki kısa panonun
    (ikisi de 125,5'ten kısa, toplamı 125,5 + dış duvardan uzun değil) arasındaki ek atlanır: AP-27 paftasında 367,5 · 430,25 · 500'de
    430,25 (62,75 + 69,75). Kural iki yönden aynı sonucu verir (geometri hakemi, 16 Kasım: önceki "yakın eki atla" kuralı aynada
    569,75'i alıyordu). İki makasın arası (uçlarda saçak duvarının ekseni) 125,5 + dış duvarı aşarsa `ValueError`."""
    v = [a] + [e for e in ekler if a + 0.01 < e < b - 0.01] + [b]
    sec = [a]
    for i in range(1, len(v) - 1):
        if v[i] - sec[-1] < MOD - 0.01 and v[i + 1] - v[i] < MOD - 0.01 and v[i + 1] - sec[-1] <= MOD + 2 * h + 0.01:
            continue
        sec.append(v[i])
    sec.append(b)
    gen = max(q - p for p, q in zip(sec, sec[1:]))
    if gen > MOD + 2 * h + 0.01:
        raise ValueError(f"tek uçlu kırmada iki ana makasın arası {gen:g} (en çok {MOD + 2 * h:g})")
    return sec[1:-1]


def _tek_uclu_makaslar(plan, t: dict, km: dict) -> list[dict]:
    """BK-46: tek uçlu kırmanın (İE-29) makas yerleri, AP-27 paftasının makas planından (77 m², MK1–MK25), Motor'un planında ölçüldü
    (16 Kasım 2026). Listede yalnız sayılar var (`prefabrik_liste._tek_uclu_kirma_catilari` › `kirma_makas`); sayı listeyle tutmazsa
    `ValueError` (3D'de makas yok, uyarı).
    - Ana makas (mahyaya paralel, kalkan duvarından kırmanın saçağına): kalkan duvarının pano eklerinde; iki kısa panonun arasındaki ek
      atlanır (`tek_uclu_ana_yerleri`; paftada 430,25 atlanmış, mahyadaki 500 alınmış).
    - Kısa makas (mahyaya dik, saçaktan ilk ana makasa ya da kırma hattına), iki saçak bandında: kalkan duvarının ekseninde, sonra kalkan
      duvarının iç yüzünden 125,5 arayla kırma hattının ilk ana makasla buluştuğu yere kadar; sonuncusu saçak duvarının köşeden önceki
      pano ekinde (paftada 700,25). Paftanın güney bandında iki kısa makas 519,7 ve 652,7'de; Lokman kuzey bant gibi 125,5 arayla seçti
      (512 ve 637,5; karar kartı, 16 Kasım 2026 09:00:17 UTC).
    - Çapraz makas: saçak köşesinden kırma hattı boyunca ilk ana makasa. Köşe kısa makas: son kısa makasın kırma hattındaki ucundan
      mahyaya paralel kırmanın saçağına (paftada MK16, MK25).
    Kırma hatları 45° (`cati_prefabrik._tek_uclu_kirma`: eşit eğim). `konum` plandaki koordinat: ana ve köşe kısa makasta kalkan boyunca,
    kısa ve çapraz makasta mahya boyunca (çapraz makasın ilk ana makasa vardığı yer)."""
    kl = t["kalkanlar"][0]
    s = float(t["sacak"])
    h = next(d.h for d in plan.duvarlar if d.tur == "dis")
    gx0, gy0, gx1, gy1 = (float(v) for v in G.govde_kutusu(plan))
    ex, k0 = kl["eksen"], float(kl["konum"])
    lo, hi = (gx0, gx1) if ex == "x" else (gy0, gy1)                 # mahya yönü (u)
    v0, v1 = (gy0, gy1) if ex == "x" else (gx0, gx1)                 # kalkan boyunca (v)
    if abs(k0 - lo) < 0.01:
        sgn = 1.0
    elif abs(k0 - hi) < 0.01:
        sgn = -1.0
    else:
        raise ValueError(f"kalkan {kl['ad']} gövdenin ucunda değil")
    Lm = hi - lo

    def P(u, v):
        return (k0 + sgn * u, v) if ex == "x" else (v, k0 + sgn * u)

    def ekler(yon, c):
        d = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == yon and abs(d.c - c) < 0.01]
        if len(d) != 1:
            raise ValueError(f"tek uçlu kırma: {yon} yönünde {c:g} ekseninde {len(d)} dış duvar (bir beklenir)")
        return sorted({round(v, 2) for p in d[0].panolar for v in (p.a0, p.a1)})

    ana = tek_uclu_ana_yerleri(ekler("y" if ex == "x" else "x", k0 + sgn * h), v0 + h, v1 - h, h)
    if len(ana) != km["ana"]:
        raise ValueError(f"tek uçlu kırmada kalkan duvarının pano eklerinde {len(ana)} ana makas, listede {km['ana']}")
    makaslar = [{"rol": "ana", "kalem": "Makas (ana, mahyaya paralel)", "konum": v, "ust": [P(0.0, v), P(Lm + s, v)],
                 "alt": [P(0.0, v), P(Lm, v)]} for v in ana]
    kose = []
    for vs, va, yon in ((v0, ana[0], 1.0), (v1, ana[-1], -1.0)):     # iki saçak bandı: saçak duvarından ilk ana makasa
        derin = abs(va - vs)
        uj = Lm - derin                                              # kırma hattının ilk ana makasla buluştuğu yer
        us = [h] + [2 * h + k * MOD for k in range(1, int((uj - 2 * h) // MOD) + 2) if 2 * h + k * MOD < uj - 0.01]
        sacak = [sgn * (a - k0) for a in ekler(ex, vs + yon * h)]
        son_ek = max((u for u in sacak if us[-1] + 0.01 < u < Lm - 2 * h - 0.01), default=None)
        if son_ek is not None:
            us.append(son_ek)
        if len(us) != km["kisa_bant"]:
            raise ValueError(f"tek uçlu kırmada saçak bandında {len(us)} kısa makas, listede bant başına {km['kisa_bant']}")
        for u in us:
            d_hip = Lm - u                                           # kırma hattı: köşeden 45°
            ve = va if d_hip >= derin else vs + yon * d_hip
            makaslar.append({"rol": "kisa", "kalem": "Makas (kısa)", "konum": round(k0 + sgn * u, 2), "ust": [P(u, vs - yon * s), P(u, ve)],
                             "alt": [P(u, vs), P(u, ve)]})
        makaslar.append({"rol": "capraz", "kalem": "Makas (çapraz, kırma)", "konum": round(k0 + sgn * uj, 2),
                         "ust": [P(Lm + s, vs - yon * s), P(uj, va)], "alt": [P(Lm, vs), P(uj, va)]})
        u = us[-1]; vk = vs + yon * (Lm - u)
        if Lm - u >= derin:
            raise ValueError("tek uçlu kırmada son kısa makas kırma hattına değil ana makasa varıyor; köşe kısa makasın yeri yok")
        kose.append({"rol": "kose_kisa", "kalem": "Makas (köşe kısa)", "konum": round(vk, 2), "ust": [P(u, vk), P(Lm + s, vk)],
                     "alt": [P(u, vk), P(Lm, vk)]})
    if len(kose) != km["kose_kisa"] or 2 != km["capraz"]:
        raise ValueError(f"tek uçlu kırmada 2 çapraz ve 2 köşe kısa makas, listede {km['capraz']} ve {km['kose_kisa']}")
    return makaslar + kose


def _kirma_girdisi(plan, ie: dict) -> dict:
    """BK-46: kırma çatının 3D girdisi (havuz denetimi HD-10, 16 Kasım 2026: kırma çatı 3D'de beşik çiziliyordu). Düzlemler ve tek uçlu
    kırmanın kalkanı çizimdeki çatıdan (`cati_prefabrik.cati`; ön onay çizimi, görünüşler ve liste aynı tanımı okur). Makaslar yükleme
    listesinin makas planından (D-28 tek kaynak; `prefabrik_liste`). İki uçlu kırmada (İE-33, AP-01 paftası): ana makaslar mahyaya dik
    `ana_x_cm`'de saçaktan saçağa; her uçta kısa makaslar `kisa_y_cm`'de uç duvarın saçağından ilk ana makasa; köşe başına bir çapraz makas,
    saçak köşesinden kırma hattı boyunca ilk ana makasa. Tek uçlu kırmada (İE-29, AP-27 paftası) listede yalnız sayılar var; yerler
    paftanın makas planından (`_tek_uclu_makaslar`), sayılar listeyle denetlenir. Liste yazılmıyorsa ya da yer kuralı tutmuyorsa 3D'de
    makas yok, uyarıyla (K16)."""
    from . import cati_prefabrik as CP
    from . import prefabrik_liste as PL
    t = CP.cati(plan, ie)
    s = float(t["sacak"])
    gx0, gy0, gx1, gy1 = (float(v) for v in G.govde_kutusu(plan))
    makaslar, uyari = [], []
    if t["kalkanlar"]:                                               # İE-29: tek uçlu kırma (AP-27)
        try:
            km = PL._tek_uclu_kirma_catilari(plan, ie)[0][0]["kirma_makas"]
        except PL.ListeYazilmaz as e:
            km = None
            uyari.append(f"makas yeri: yükleme listesi yazılmıyor ({e.neden}); 3D'de makas yok")
        if km is not None:
            try:
                makaslar = _tek_uclu_makaslar(plan, t, km)
            except ValueError as e:
                uyari.append(f"makas yeri: {e}; 3D'de makas yok")
    else:
        try:
            km = PL._iki_uclu_kirma_catilari(plan, ie)[0][0]["kirma_makas"]
        except PL.ListeYazilmaz as e:
            km = None
            uyari.append(f"makas yeri: yükleme listesi yazılmıyor ({e.neden}); 3D'de makas yok")
        if km is not None:
            ax = km["ana_x_cm"]
            for x in ax:
                makaslar.append({"rol": "ana", "kalem": "Makas (ana, mahyaya dik)", "konum": x,
                                 "ust": [(x, gy0 - s), (x, gy1 + s)], "alt": [(x, gy0), (x, gy1)]})
            for u in km["uclar"]:
                sol = u["uc"] == "sol"
                kx, xf, yon, uc = (gx0, ax[0], -1.0, "sol uç") if sol else (gx1, ax[-1], 1.0, "sağ uç")
                for y in u["kisa_y_cm"]:
                    makaslar.append({"rol": "kisa", "kalem": f"Makas (kısa, {uc})", "konum": y,
                                     "ust": [(kx + yon * s, y), (xf, y)], "alt": [(kx, y), (xf, y)]})
                for ky, yk, yd in ((gy0, u["kisa_y_cm"][0], -1.0), (gy1, u["kisa_y_cm"][-1], 1.0)):
                    makaslar.append({"rol": "capraz", "kalem": f"Makas (çapraz, kırma, {uc})", "konum": yk,
                                     "ust": [(kx + yon * s, ky + yd * s), (xf, yk)], "alt": [(kx, ky), (xf, yk)]})
    return {"tanim": t, "tip": "tek_uclu" if t["kalkanlar"] else "iki_uclu", "makaslar": makaslar, "uyari": uyari}


def _cikintili_cumba_tanimi(plan, ie: dict) -> dict:
    """BK-46: girintili gövdede beşik + çapraz cumbanın 3D tanımı (havuz denetimi HD-05, 16 Kasım 2026: çıkıntılı cumbada (82, 91 m²) ve iki
    cumbada (45, 46, 40 m²) 3D kurulmuyordu). `cati_capraz.tanim`'in anahtarlarıyla (`IfcUretici._cati_serit` okur); `cati_capraz.tanim`
    kart modeli ve rehber için yalnız çıkıntısız cumbayı kurar, değişmedi. Düzlemler ve kalkanlar çizimdeki çatıdan (`cati_prefabrik.cati`).
    Makaslar yükleme listesinin kuralıyla (`prefabrik_liste._capraz_cumba_catilari`, D-28): ana çatı kendi dikdörtgeninde dikdörtgen beşiğin
    kuralıyla (`cati_capraz.ana_makaslari`: saçak duvarının pano ekleri, değilse eşit aralık ve uyarı; sayı ⌈(boy − 2 × dış duvar) ÷ 125,5⌉
    + 1); gövdenin cumbası dış uçtaki kalkan duvarının ekseninden 125,5 arayla derelerin birleştiği yere kadar (D-47). Çıkıntının içindeki
    makaslar (ilki kalkan duvarında) cumbanın yan duvarlarına oturan beşik makası; çıkıntının ötesindekiler ana çatının üstünde iki dere
    arasında (geometri hakemi, 16 Kasım: 91 m²'de çıkıntı 220, makas ana çatının saçağından taşıyordu). Liste yazılmıyorsa makaslar
    listenin kuralıyla kurulur, uyarıyla. Taşan verandanın cumbasının (PC-38) makasları listedeki yerde (`makas_konum_cm`: dış kirişin
    ekseninden 125,5 arayla; BK-45, 45 m² paftası MK09–MK10) ve listedeki parça adıyla ("sundurma çatısı"); kirişlerin üstündekiler beşik
    makası, ötekiler ana çatının üstünde. Listede yer yoksa o cumbada makas yok, uyarıyla (K16)."""
    from . import cati_prefabrik as CP
    from .cati_capraz import ana_makaslari
    from .cati_serit import _eksen
    from .genel import cati_genel
    c = ie.get("cati") or {}
    t = CP.cati(plan, ie)
    s, top, H0 = float(t["sacak"]), float(t["topuk"]), float(t["duvar_ustu"])
    eg = float(c["egim_yuzde"]) / 100.0
    zs = H0 + top
    P, K, eksen = _eksen(ie)
    h = next(d.h for d in plan.duvarlar if d.tur == "dis")
    ana_k, rs = CP.cumba_dikdortgenleri(c, tuple(float(v) for v in G.govde_kutusu(plan)), plan)
    (a0, b0), (a1, b1) = K(ana_k[0], ana_k[1]), K(ana_k[2], ana_k[3])
    a0, a1, b0, b1 = min(a0, a1), max(a0, a1), min(b0, b1), max(b0, b1)
    yer, uyarilar = ana_makaslari(plan, eksen, a0, a1, b0, b1, h)
    bm = (b0 + b1) / 2
    parcalar = [{"ad": "ana çatı", "rol": "ana", "a": [a0, a1], "b": [b0, b1], "aciklik_cm": round(b1 - b0, 2), "boy_cm": round(a1 - a0, 2),
                 "mahya": [list(P(a0 - s, bm)), list(P(a1 + s, bm))], "mahya_kotu": round(zs + eg * (bm - b0 + s), 2),
                 "makaslar": [{"konum": round(x, 2), "rol": "bas" if i in (0, len(yer) - 1) else "orta"} for i, x in enumerate(yer)],
                 "makas_yeri": "pano ekleri" if not uyarilar else "eşit aralık", "komsu": None}]
    from . import prefabrik_liste as PL
    lp = []                                                          # cumbaların liste parçaları, `cumbalar` sırasıyla
    try:
        lp = PL._capraz_cumba_catilari(plan, ie)[0][1:]
    except PL.ListeYazilmaz as e:
        uyarilar = uyarilar + [f"makas yeri: yükleme listesi yazılmıyor ({e.neden}); makaslar listenin kuralıyla, liste gelince kıyaslanacak"]
    kenarlar = cati_genel.cati_kur(t)["kenarlar"]
    for j, (u, r) in enumerate(zip(c["cumbalar"], rs)):
        onek = "cumba " if j == 0 else "cumba 2 "
        yuzler = [d["ad"] for d in t["duzlemler"] if d["ad"].startswith(onek) and (j > 0 or not d["ad"].startswith("cumba 2 "))]
        liste_yeri = ((lp[j].get("makas_konum_cm") or {}).get("degerler") if j < len(lp) else None) if "veranda" in u else None
        if "veranda" in u and not liste_yeri:                        # PC-38: taşan verandanın cumbası; yer yalnız listeden (D-28)
            uyarilar = uyarilar + [f"makas yeri: {u['veranda']} verandasının cumbasında makas yeri listede yok; 3D'de makas yok"]
            continue
        mh = [e for e in kenarlar if e["tur"] == "mahya" and set(e["duzlemler"]) <= set(yuzler)]
        if len(mh) != 1:
            raise CP.PrefabrikCatiHatasi(f"beşik + cumba: cumbanın mahyası {len(mh)} kenar (bir beklenir)")
        cephe = u["cephe"]
        cx0, cy0, cx1, cy1 = r
        dis = {"on": cy0, "arka": cy1, "sol": cx0, "sag": cx1}[cephe]
        ic = 1.0 if cephe in ("on", "sol") else -1.0
        eks = 1 if cephe in ("on", "arka") else 0
        birlesim = max(abs(v[eks] - dis) for v in (mh[0]["p"], mh[0]["q"]))
        uzak = [h + i * MOD for i in range(int(math.floor((birlesim - h) / MOD - 1e-9)) + 1)]
        if liste_yeri:                                               # BK-46 eki (BK-45 listesi): verandanın cumbası dış kirişin ekseninden
            uzak = [round(abs(v - dis), 2) for v in liste_yeri]
        cikinti = abs((cy1 - cy0) if eks == 1 else (cx1 - cx0))     # gövdenin çıkıntısı (verandada derinliği): altında yan duvar ya da kiriş
        ca = sorted((dis, dis + ic * birlesim))
        cb = [cx0, cx1] if eks == 1 else [cy0, cy1]
        cbm = (cb[0] + cb[1]) / 2
        parcalar.append({"ad": lp[j]["ad"] if liste_yeri else "cumba" if j == 0 else "cumba 2", "rol": "cumba", "capraz": True, "cephe": cephe, "dis_uc": round(dis, 2),
                         "a": [round(v, 2) for v in ca], "b": [round(v, 2) for v in cb], "aciklik_cm": round(cb[1] - cb[0], 2),
                         "boy_cm": round(birlesim, 2), "mahya": [[round(v, 4) for v in mh[0]["p"]], [round(v, 4) for v in mh[0]["q"]]],
                         "mahya_kotu": round(zs + eg * (cbm - cb[0] + s), 2), "duzlemler": yuzler,
                         "makaslar": [{"konum": round(dis + ic * d_, 2), "rol": "bas" if i == 0 else "orta", "uzaklik": round(d_, 2),
                                       **({} if d_ < cikinti - 1e-6 else {"ana_ustunde": True})} for i, d_ in enumerate(uzak)],
                         "makas_yeri": lp[j]["makas_yeri"] if liste_yeri else
                         f"kalkan duvarının ekseninden {MOD:g} arayla, derelerin birleştiği yere kadar (D-47)", "komsu": "ana çatı"})
    return {**t, "capraz": True, "parcalar": parcalar, "uyarilar": uyarilar}


class IfcUretici:
    def __init__(self, G: dict, proje_adi: str):
        self.G = G
        f = self.f = ifcopenshell.file(schema="IFC4")
        self.proje = api("root.create_entity", f, ifc_class="IfcProject", name=proje_adi)
        api("unit.assign_unit", f, length={"is_metric": True, "raw": "METERS"}, area={"is_metric": True, "raw": "SQUARE_METERS"},
            volume={"is_metric": True, "raw": "CUBIC_METERS"})
        model = api("context.add_context", f, context_type="Model")
        self.body = api("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)
        self.site = api("root.create_entity", f, ifc_class="IfcSite", name="Parsel")
        self.bina = api("root.create_entity", f, ifc_class="IfcBuilding", name=G["bina"].get("ad", "Prefabrik konut"))
        self.kat = api("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Zemin Kat")
        api("aggregate.assign_object", f, relating_object=self.proje, products=[self.site])
        api("aggregate.assign_object", f, relating_object=self.site, products=[self.bina])
        api("aggregate.assign_object", f, relating_object=self.bina, products=[self.kat])
        for e in (self.site, self.bina, self.kat):
            api("geometry.edit_object_placement", f, product=e)
        self.sb = ShapeBuilder(f)
        self.stil = {}; self.malz = {}
        self._malzemeler()

    # ------------------------------------------------------------------ malzeme / stil
    def _stil(self, ad, rgb, saydam=0.0):
        s = api("style.add_style", self.f, name=ad)
        api("style.add_surface_style", self.f, style=s, ifc_class="IfcSurfaceStyleShading",
            attributes={"SurfaceColour": {"Name": None, "Red": rgb[0], "Green": rgb[1], "Blue": rgb[2]}, "Transparency": saydam})
        return s

    def _malzeme(self, anahtar, ad, rgb, kategori, saydam=0.0):
        m = api("material.add_material", self.f, name=ad, category=kategori)
        s = self._stil(ad, rgb, saydam)
        api("style.assign_material_style", self.f, material=m, style=s, context=self.body)
        self.malz[anahtar] = m; self.stil[anahtar] = s
        return m

    def _malzemeler(self):
        self._malzeme("fiber", "Fibercement 8 mm", (0.66, 0.65, 0.62), "concrete")
        self._malzeme("eps", "EPS 16 kg/m³", (0.95, 0.95, 0.92), "insulation")
        self._malzeme("pvc", "PVC doğrama beyaz", (0.95, 0.95, 0.94), "plastic")
        self._malzeme("cam", "Isıcam 4+12+4", (0.70, 0.85, 0.95), "glass", saydam=0.6)
        self._malzeme("celik", "Çelik kapı", (0.25, 0.17, 0.12), "steel")
        self._malzeme("ickapi", "Amerikan panel iç kapı", (0.93, 0.91, 0.86), "wood")
        self._malzeme("sac", "Trapez sac antrasit", (0.12, 0.13, 0.14), "steel")
        self._malzeme("galv", "Galvaniz profil", (0.72, 0.74, 0.77), "steel")
        self._malzeme("profil", "Kutu profil 100×100", (0.30, 0.31, 0.33), "steel")
        self._malzeme("beton", "Beton (bayi/saha)", (0.58, 0.58, 0.56), "concrete")
        self._malzeme("mahal", "Mahal hacmi", (0.80, 0.86, 0.95), "space", saydam=0.85)
        # pano tipleri: katmanlı (8 + EPS + 8)
        self.tip = {}
        for anahtar, kal_mm in (("dis", round(G.T_DIS * 10)), ("ic", round(G.T_IC * 10))):
            eps_mm = kal_mm - 16; standart = kal_mm in (100, 60)
            ad = f"PE-{'DIS' if anahtar == 'dis' else 'IC'}-{kal_mm} {'Dış' if anahtar == 'dis' else 'İç'} sandviç pano {kal_mm} mm"
            t = api("root.create_entity", self.f, ifc_class="IfcWallType", name=ad, predefined_type="SOLIDWALL")
            ls = api("material.add_material_set", self.f, name=ad, set_type="IfcMaterialLayerSet")
            for mat, kal in ((self.malz["fiber"], 8), (self.malz["eps"], eps_mm), (self.malz["fiber"], 8)):
                ly = api("material.add_layer", self.f, layer_set=ls, material=mat)
                api("material.edit_layer", self.f, layer=ly, attributes={"LayerThickness": kal / 1000})
            api("material.assign_material", self.f, products=[t], type="IfcMaterialLayerSet", material=ls)
            ps = api("pset.add_pset", self.f, product=t, name="PortatifEv_PanoTipi")
            api("pset.edit_pset", self.f, pset=ps, properties={
                "Modul_cm": 125.5, "Kalinlik_mm": kal_mm, "Yukseklik_cm": self.G["bina"]["duvar_h"],
                "Kesit": f"8 mm fibercement + {eps_mm} mm EPS (16 kg/m³) + 8 mm fibercement" + ("" if standart else " — katmanlar çıkarım, teyit edilecek"),
                "Kaynak": "PortatifEv 9/2026 fiyat listesi teknik özellikleri" if standart else "Kalınlık: Lokman, 6 Ekim 2026; katmanlar teyit edilecek"})
            self.tip[anahtar] = t

    # ------------------------------------------------------------------ geometri yardımcıları
    def _kutu(self, x, y, z, dx, dy, dz):
        """Yerel koordinatta (cm) dikdörtgen prizma temsil öğesi."""
        prof = self.sb.profile(self.sb.rectangle(size=np.array([_m(dx), _m(dy)])))
        return self.sb.extrude(prof, magnitude=_m(dz), position=np.array([_m(x), _m(y), _m(z)]))

    def _prizma_xz(self, pts_xz, y0, y1):
        """Dünya x-z düzlemindeki kesit (cm), y0..y1 boyunca (dünya koordinatı)."""
        prof = self.sb.profile(self.sb.polyline([np.array([_m(x), _m(z)]) for x, z in pts_xz], closed=True))
        return self.sb.extrude(prof, magnitude=_m(y1 - y0), position=np.array([0.0, _m(y1), 0.0]),
                               position_z_axis=np.array([0.0, -1.0, 0.0]), position_x_axis=np.array([1.0, 0.0, 0.0]))

    def _prizma_xy(self, pts_xy, z0, z1):
        prof = self.sb.profile(self.sb.polyline([np.array([_m(x), _m(y)]) for x, y in pts_xy], closed=True))
        return self.sb.extrude(prof, magnitude=_m(z1 - z0), position=np.array([0.0, 0.0, _m(z0)]))

    def _temsil(self, urun, ogeler, malz=None):
        rep = self.sb.get_representation(self.body, ogeler if isinstance(ogeler, list) else [ogeler])
        api("geometry.assign_representation", self.f, product=urun, representation=rep)
        if malz is not None:
            api("style.assign_representation_styles", self.f, shape_representation=rep, styles=[self.stil[malz]])
        return rep

    def _yerlestir(self, urun, orijin=(0, 0, 0), x_ekseni=(1, 0, 0), ust=None):
        m = np.eye(4)
        xa = np.array(x_ekseni, dtype=float); za = np.array([0, 0, 1.0]); ya = np.cross(za, xa)
        m[:3, 0], m[:3, 1], m[:3, 2] = xa, ya, za
        m[:3, 3] = [_m(orijin[0]), _m(orijin[1]), _m(orijin[2])]
        api("geometry.edit_object_placement", self.f, product=urun, matrix=m, is_si=True)

    def _urun(self, sinif, ad, predefined=None, kapsa=True, **kw):
        e = api("root.create_entity", self.f, ifc_class=sinif, name=ad, predefined_type=predefined) if predefined else \
            api("root.create_entity", self.f, ifc_class=sinif, name=ad)
        for k, v in kw.items():
            setattr(e, k, v)
        if kapsa:
            api("spatial.assign_container", self.f, relating_structure=self.kat, products=[e])
        return e

    def _pset(self, urun, ad, ozellik):
        ps = api("pset.add_pset", self.f, product=urun, name=ad)
        api("pset.edit_pset", self.f, pset=ps, properties=ozellik)

    def _qto(self, urun, ad, ozellik):
        q = api("pset.add_qto", self.f, product=urun, name=ad)
        api("pset.edit_qto", self.f, qto=q, properties=ozellik)

    # ------------------------------------------------------------------ panolar + boşluklar + doğramalar
    SINIF_AD = {"tam": "Tam pano 125,5", "yarim": "Yarım pano 62,75", "ozel": "Özel pano", "kose": "Köşe / bağlantı parçası"}

    def _bom_kalem(self, p, acik_tur):
        if p["sinif"] == "kose":
            return f"{'Dış' if p['kalinlik'] >= 8.5 else 'İç'} köşe/bağlantı parçası {p['kalinlik']:.0f}×{p['boy']:.0f}"
        tur = "Dış" if p["tur"] == "dis" else "İç"
        k = f"{tur} {self.SINIF_AD[p['sinif']].lower()} — " + (f"{', '.join(sorted(set(acik_tur)))}li" if acik_tur else "dolu")
        if p["sinif"] == "ozel":
            k += f" ({p['boy']:.1f} cm)"
        return k

    def panolar(self):
        G = self.G; A = G["acikliklar"]; H = G["bina"]["duvar_h"]
        eke = {pid for a in A if a["tur"] == "pencere" and len(a["panolar"]) > 1 for pid in a["panolar"]}
        self.pano_nesne = {}
        dolgu_yapildi = set()
        for p in G["panolar"]:
            x0, y0, x1, y1 = p["rect"]
            if p["yon"] == "x":
                org, xa, a0 = (x0, y0, 0), (1, 0, 0), x0
            else:
                org, xa, a0 = (x1, y0, 0), (0, 1, 0), y0          # yerel y = dünya -x: kalınlık x1'den içeri
            L, t = p["boy"], p["kalinlik"]
            acik_tur = [(f"pencere {A[x['aciklik']]['olcu']}" if A[x["aciklik"]]["tur"] == "pencere" else f"kapı {round(A[x['aciklik']]['genislik'])}")
                        for x in p["acikliklar"]]
            ad = f"PANO_{'D' if p['tur'] == 'dis' else 'I'}_{p['sinif'].upper()}_{L:.1f}_{p['id']:02d}"
            w = self._urun("IfcWall", ad, predefined="SOLIDWALL" if p["tur"] == "dis" else "PARTITIONING")
            w.Description = p.get("kalem") or self._bom_kalem(p, acik_tur)
            self._yerlestir(w, org, xa)
            self._temsil(w, self._kutu(0, 0, 0, L, t, H))
            api("type.assign_type", self.f, related_objects=[w], relating_type=self.tip["dis" if p["tur"] == "dis" else "ic"])
            bosluk_alani = 0.0
            for x in p["acikliklar"]:
                a = A[x["aciklik"]]
                o = self._urun("IfcOpeningElement", f"BOSLUK_{ad}_{x['aciklik']:02d}", predefined="OPENING", kapsa=False)
                self._yerlestir(o, org, xa)
                self._temsil(o, self._kutu(x["a0"] - a0, -2, x["z0"], x["a1"] - x["a0"], t + 4, x["z1"] - x["z0"]))
                api("feature.add_feature", self.f, feature=o, element=w)
                bosluk_alani += (x["a1"] - x["a0"]) * (x["z1"] - x["z0"])
                self._pset(o, "PortatifEv_Bosluk", {"Aciklik": x["aciklik"], "Tur": a.get("alt_tur", a["tur"]), "BOMKod": a.get("kod") or ""})
                if x["aciklik"] not in dolgu_yapildi:
                    dolgu = self._dograma(x["aciklik"], a, p, org, xa, a0)
                    dolgu_yapildi.add(x["aciklik"])
                    if dolgu is not None:
                        api("feature.add_filling", self.f, opening=o, element=dolgu)
            self._pset(w, "Pset_WallCommon", {"IsExternal": p["tur"] == "dis", "Reference": self.SINIF_AD[p["sinif"]]})
            self._pset(w, "PortatifEv_Pano", {"BOMKalem": w.Description, "PanoSinifi": p["sinif"], "Boy_cm": L, "Kalinlik_cm": t,
                                                "Yukseklik_cm": H, "Acikliklar": ", ".join(acik_tur), "PencerePanoEkinde": p["id"] in eke,
                                                "BOMKod": p.get("kod", ""), "Kaynak": f"{self.G['kaynak']['dosya']} parça #{p['id']}"})
            brut = _m(L) * _m(H)
            self._qto(w, "Qto_WallBaseQuantities", {"Length": _m(L), "Width": _m(t), "Height": _m(H), "GrossSideArea": round(brut, 4),
                                                   "NetSideArea": round(brut - bosluk_alani * CM * CM, 4),
                                                   "GrossVolume": round(brut * _m(t), 5), "NetVolume": round((brut - bosluk_alani * CM * CM) * _m(t), 5)})
            self.pano_nesne[p["id"]] = w

    def _dograma(self, ai, a, p, org, xa, a0):
        """Pencere / dış kapı nesnesi (panonun yerel koordinatında). İç kapı kapsam dışı → None (boşluk kalır)."""
        t = p["kalinlik"]; o0, o1, z0, z1 = a["a0"] - a0, a["a1"] - a0, a["z0"], a["z1"]
        mid = t / 2
        if a["tur"] == "pencere":
            f = 6.0
            ad = f"PENCERE_{a['olcu']}_{ai:02d}"
            e = self._urun("IfcWindow", ad, predefined="WINDOW", OverallWidth=_m(o1 - o0), OverallHeight=_m(z1 - z0))
            self._yerlestir(e, org, xa)
            kasa = [self._kutu(o0, mid - 3.5, z0, o1 - o0, 7, f), self._kutu(o0, mid - 3.5, z1 - f, o1 - o0, 7, f),
                    self._kutu(o0, mid - 3.5, z0 + f, f, 7, z1 - z0 - 2 * f), self._kutu(o1 - f, mid - 3.5, z0 + f, f, 7, z1 - z0 - 2 * f)]
            if o1 - o0 >= 100:
                m = (o0 + o1) / 2
                kasa.append(self._kutu(m - 3, mid - 3.5, z0 + f, 6, 7, z1 - z0 - 2 * f))
            cam = self._kutu(o0 + f, mid - 0.6, z0 + f, o1 - o0 - 2 * f, 1.2, z1 - z0 - 2 * f)
            rep = self.sb.get_representation(self.body, kasa + [cam])
            api("geometry.assign_representation", self.f, product=e, representation=rep)
            for oge in kasa:
                api("style.assign_item_style", self.f, item=oge, style=self.stil["pvc"])
            api("style.assign_item_style", self.f, item=cam, style=self.stil["cam"])
            olcu = a["olcu"].replace("x", "×")
            self._pset(e, "Pset_WindowCommon", {"IsExternal": True})
            self._pset(e, "PortatifEv_Dograma", {"BOMKalem": a.get("kalem") or f"PVC pencere {olcu} (beyaz, 4+12+4)", "BOMKod": a.get("kod") or "",
                                                  "Olcu": a["olcu"], "Esik_cm": z0, "PanoEkinde": len(a["panolar"]) > 1, "Kaynak": self.G["kaynak"]["dosya"]})
            return e
        alt = a.get("alt_tur") or ("dis_kapi" if a["genislik"] >= 95 else "ic_kapi")
        if alt == "gecis":
            self.gecis_bosluk = getattr(self, "gecis_bosluk", 0) + 1
            return None
        if alt == "ic_kapi" and self.G.get("kapsam", {}).get("ic_kapi"):
            ad = f"KAPI_IC_PANEL_{ai:02d}"
            e = self._urun("IfcDoor", ad, predefined="DOOR", OverallWidth=_m(o1 - o0), OverallHeight=_m(z1))
            self._yerlestir(e, org, xa)
            kasa = [self._kutu(o0, -1, 0, 4, t + 2, z1), self._kutu(o1 - 4, -1, 0, 4, t + 2, z1), self._kutu(o0, -1, z1 - 4, o1 - o0, t + 2, 4)]
            kanat = self._kutu(o0 + 4, mid - 2, 0, o1 - o0 - 8, 4, z1 - 4)
            rep = self.sb.get_representation(self.body, kasa + [kanat])
            api("geometry.assign_representation", self.f, product=e, representation=rep)
            for oge in kasa:
                api("style.assign_item_style", self.f, item=oge, style=self.stil["pvc"])
            api("style.assign_item_style", self.f, item=kanat, style=self.stil["ickapi"])
            self._pset(e, "Pset_DoorCommon", {"IsExternal": False})
            self._pset(e, "PortatifEv_Dograma", {"BOMKalem": a.get("kalem") or f"İç kapı {round(a['genislik'])}", "BOMKod": a.get("kod") or "",
                                                  "Kaynak": self.G["kaynak"]["dosya"]})
            return e
        if alt == "dis_kapi":
            ad = f"KAPI_DIS_CELIK_{ai:02d}"
            e = self._urun("IfcDoor", ad, predefined="DOOR", OverallWidth=_m(o1 - o0), OverallHeight=_m(z1))
            self._yerlestir(e, org, xa)
            self._temsil(e, self._kutu(o0 + 3, mid - 2.5, 0, o1 - o0 - 6, 5, z1 - 3), "celik")
            self._pset(e, "Pset_DoorCommon", {"IsExternal": True})
            self._pset(e, "PortatifEv_Dograma", {"BOMKalem": a.get("kalem") or f"Çelik dış kapı {round(a['genislik'])}×{int(z1)}", "BOMKod": a.get("kod") or "",
                                                  "Kaynak": self.G["kaynak"]["dosya"]})
            return e
        # iç kapı: kapsam dışı; boşluğun kendisi BOM'da "iç kapı boşluğu" olarak sayılır
        self.ic_kapi_bosluk = getattr(self, "ic_kapi_bosluk", 0) + 1
        return None

    # ------------------------------------------------------------------ mahaller, döşeme
    def mahaller(self):
        G = self.G; H = G["bina"]["duvar_h"]
        for i, o in enumerate(G["odalar"]):
            s = self._urun("IfcSpace", f"M{i + 1:02d}", predefined="INTERNAL", kapsa=False, LongName=o["ad"])
            api("aggregate.assign_object", self.f, relating_object=self.kat, products=[s])
            self._yerlestir(s)
            hk = ((G.get("kubbeler") or [{}])[0]).get("duvar_cm", H)   # BK-46: kubbenin içi kubbe duvarı boyunca (çatısının altında)
            self._temsil(s, [self._prizma_xy(o["poligon"], 0, H)] + [self._prizma_xy(e, 0, hk) for e in o.get("ek_poligonlar", [])], "mahal")
            self._qto(s, "Qto_SpaceBaseQuantities", {"NetFloorArea": o["net_m2"], "Height": _m(H)})
            self._pset(s, "PortatifEv_Mahal", {"CizimNetAlan_m2": o["net_m2"], "BayiEtiketAlan_m2": o["etiket_m2"] or 0.0,
                                               "EtiketUyumlu": o["etiket_m2"] is not None and abs(o["etiket_m2"] - o["net_m2"]) <= 0.3})
        v = G["veranda"]
        if v:
            s = self._urun("IfcSpace", "M-VERANDA", predefined="EXTERNAL", kapsa=False, LongName="VERANDA")
            api("aggregate.assign_object", self.f, relating_object=self.kat, products=[s])
            self._yerlestir(s)
            self._temsil(s, self._prizma_xy(v["poligon"], 0, H), "mahal")
            self._qto(s, "Qto_SpaceBaseQuantities", {"NetFloorArea": v["net_m2"]})
            self._pset(s, "PortatifEv_Mahal", {"CizimNetAlan_m2": v["net_m2"], "BayiEtiketAlan_m2": v["etiket_m2"] or 0.0, "BinaDisinaTasma_cm": v["tasma_cm"]})

    def doseme(self):
        P = self.G["panolar"]; v = self.G["veranda"]
        Wd = max(p["rect"][2] for p in P); Hd = max(p["rect"][3] for p in P)
        if self.G.get("govde"):                       # İE-24: girintili gövde
            taban = self.G["govde"]
        elif v and v.get("tip") != "bina_ici":
            vx0, vy0 = v["poligon"][0]
            taban = [(0, 0), (vx0, 0), (vx0, vy0), (Wd, vy0), (Wd, Hd), (0, Hd)]
        else:
            taban = [(0, 0), (Wd, 0), (Wd, Hd), (0, Hd)]
        s = self._urun("IfcSlab", "ZEMIN_BETONU", predefined="BASESLAB")
        self._yerlestir(s)
        self._temsil(s, self._prizma_xy(taban, -15, 0), "beton")
        self._pset(s, "PortatifEv_Kapsam", {"BOMKalem": "Zemin betonu — kapsam dışı (bayi/saha)", "KapsamDisi": True})
        self.Wd, self.Hd = Wd, Hd

    # ------------------------------------------------------------------ çatı, makas, veranda
    def cati(self):
        if self.G.get("cati_serit"):                                 # İE-24: girintili gövde (ana çatı + paralel cumba)
            return self._cati_serit()
        if self.G.get("cati_kirma"):                                 # BK-46: kırma çatı (eskiden beşik çiziliyordu)
            return self._cati_kirma()
        if self.G["bina"]["cati"].get("makas_ekseni", "x") == "y":   # makaslar derinliği geçer (derinlik kısa kenar)
            return self._cati_y()
        G = self.G; c = G["bina"]["cati"]; H0 = G["bina"]["duvar_h"]
        s, eg, top = c["sacak"], c["egim"], c["topuk"]
        Wd, Hd = self.Wd, self.Hd; xm = Wd / 2
        zs = H0 + top; zm = zs + (xm + s) * eg; t = 4.0
        roof = self._urun("IfcRoof", "ANA_CATI", predefined="GABLE_ROOF")
        self._yerlestir(roof)
        alan = 2 * math.hypot(xm + s, (xm + s) * eg) * (Hd + 2 * s) / 1e4
        self._pset(roof, "PortatifEv_Cati", {"Egim_yuzde": eg * 100, "Sacak_cm": s, "Topuk_cm": top, "Mahya_cm": round(zm, 1),
                                             "MakasYonu": "kısa kenar (x)", "Ortu": "trapez sac antrasit", "OrtuAlani_m2": round(alan, 2)})
        parcalar = []
        for ad, k in (("CATI_SOL", [(-s, zs + 10), (xm, zm + 10), (xm, zm + 10 + t), (-s, zs + 10 + t)]),
                      ("CATI_SAG", [(xm, zm + 10), (Wd + s, zs + 10), (Wd + s, zs + 10 + t), (xm, zm + 10 + t)])):
            sl = self._urun("IfcSlab", ad, predefined="ROOF", kapsa=False)
            self._yerlestir(sl); self._temsil(sl, self._prizma_xz(k, -s, Hd + s), "sac")
            self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Trapez çatı sacı (antrasit) — yüzey"})
            parcalar.append(sl)
        api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
        # alın dolguları
        zt = lambda x: zs + (min(x, Wd - x) + s) * eg
        alin = [(0, H0), (Wd, H0), (Wd, zt(Wd)), (xm, zt(xm)), (0, zt(0))]
        for ad, ya, yb in (("ALIN_ON", 0, 10), ("ALIN_ARKA", Hd - 10, Hd)):
            pl = self._urun("IfcPlate", ad, predefined="SHEET")
            self._yerlestir(pl); self._temsil(pl, self._prizma_xz(alin, ya, yb), "fiber")
            self._pset(pl, "PortatifEv_Kapsam", {"BOMKalem": "Çatı alın dolgusu (üçgen) — kural teyit edilecek"})
        # makaslar pano eklerinde (BK-12 PR-R): iki baş makas uç duvarların ekseninde, orta makaslar boydan boya kesintisiz
        # koşan saçak duvarının (x = 0 ya da Wd) pano eklerinde; PK-01'de paftadaki MK01–MK09. İki saçak duvarı da kesintisizse
        # ortak ekler alınır. Ekler düzenli olmalı: orta makaslar 125,5 arayla, uçtaki açıklıklar 125,5'ten uzun değil, sayı
        # yükleme listesininkiyle aynı (⌈(boy − 2 × dış duvar) ÷ 125,5⌉ + 1; `prefabrik_liste`). Değilse (iki yanda veranda,
        # L plan, saçak duvarında 251'lik pano, T'de ızgara dışı bölünme) eşit aralık: liste sayısında makas, baş makaslar yine uç
        # duvarların ekseninde (100'lük dış duvarda PR-R'den önceki dizilimle aynı); uyarı özete ve IFC'ye yazılır (K16)
        td = max(p["kalinlik"] for p in G["panolar"])
        n_liste = math.ceil((Hd - 2 * td) / 125.5 - 1e-6) + 1
        def sacak_ekleri(x):
            ar = sorted((p["rect"][1], p["rect"][3]) for p in G["panolar"] if p["yon"] == "y" and p["tur"] == "dis"
                        and abs((p["rect"][0] if x == 0 else p["rect"][2]) - x) < 1e-6)
            tam = (bool(ar) and ar[0][0] <= td + 1e-6 and ar[-1][1] >= Hd - td - 1e-6
                   and all(abs(a[1] - b[0]) < 1e-6 for a, b in zip(ar, ar[1:])))
            return {round(v, 3) for a in ar for v in a if td + 1e-6 < v < Hd - td - 1e-6} if tam else None
        ekler = [e for e in (sacak_ekleri(0), sacak_ekleri(Wd)) if e is not None]
        uyari, ys = [], None
        if not ekler:
            uyari.append(f"makas yeri: boydan boya kesintisiz saçak duvarı yok; eşit aralıklı {n_liste} makas")
        else:
            if len(ekler) == 2 and ekler[0] != ekler[1]:
                uyari.append("makas yeri: iki saçak duvarının pano ekleri farklı; ortak ekler alındı")
            aday = [td / 2] + sorted(set.intersection(*ekler)) + [Hd - td / 2]
            araliklar = [b - a for a, b in zip(aday, aday[1:])]
            if (len(aday) == n_liste and all(abs(a - 125.5) < 0.01 for a in araliklar[1:-1])
                    and all(0 < a < 125.5 + 0.01 for a in (araliklar[0], araliklar[-1]))):
                ys = aday
            else:
                uyari.append(f"makas yeri: saçak duvarının pano ekleri düzensiz ({len(aday)} makas, listede {n_liste}; "
                             f"aralıklar {', '.join(f'{a:g}' for a in (round(x, 2) for x in araliklar))}); eşit aralıklı {n_liste} makas")
        if ys is None:
            ys = [td / 2 + i * (Hd - td) / (n_liste - 1) for i in range(n_liste)]
        if uyari:
            self._pset(roof, "PortatifEv_Uyari", {"MakasYeri": " | ".join(uyari)})
        n = len(ys)
        for i, y in enumerate(ys):
            asm = self._urun("IfcElementAssembly", f"MAKAS_{i + 1:02d}", predefined="TRUSS")
            self._yerlestir(asm)
            self._pset(asm, "PortatifEv_Kapsam", {"BOMKalem": "Çatı makası (baş)" if i in (0, n - 1) else "Çatı makası (orta)", "Aciklik_cm": round(Wd, 1)})
            q1, q3 = xm / 2, xm + xm / 2
            uyeler = (("ALT_BASLIK", [(0, H0), (Wd, H0), (Wd, H0 + 10), (0, H0 + 10)]),
                      ("UST_SOL", [(-s, zs), (xm, zm), (xm, zm + 10), (-s, zs + 10)]),
                      ("UST_SAG", [(xm, zm), (Wd + s, zs), (Wd + s, zs + 10), (xm, zm + 10)]),
                      ("DIKME_ORTA", [(xm - 3, H0 + 10), (xm + 3, H0 + 10), (xm + 3, zt(xm)), (xm - 3, zt(xm))]),
                      ("DIKME_SOL", [(q1 - 3, H0 + 10), (q1 + 3, H0 + 10), (q1 + 3, zt(q1)), (q1 - 3, zt(q1))]),
                      ("DIKME_SAG", [(q3 - 3, H0 + 10), (q3 + 3, H0 + 10), (q3 + 3, zt(q3)), (q3 - 3, zt(q3))]),
                      ("CAPRAZ_SOL", [(q1 - 3, H0 + 10), (q1 + 5, H0 + 10), (xm - 3, zt(xm) - 8), (xm - 11, zt(xm) - 8)]),
                      ("CAPRAZ_SAG", [(q3 - 5, H0 + 10), (q3 + 3, H0 + 10), (xm + 11, zt(xm) - 8), (xm + 3, zt(xm) - 8)]))
            uyeler_e = []
            for ad, k in uyeler:
                m = self._urun("IfcMember", f"MAKAS_{i + 1:02d}_{ad}", predefined="CHORD" if "BASLIK" in ad or "UST" in ad else "MEMBER", kapsa=False)
                self._yerlestir(m); self._temsil(m, self._prizma_xz(k, y - 2.5, y + 2.5), "galv")
                uyeler_e.append(m)
            api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler_e)
        self.cati_ozet = {"mahya_cm": round(zm, 1), "makas": n, "cati_alan_m2": round(alan, 2), "makas_y_cm": [round(y, 2) for y in ys],
                          **({"uyari": uyari} if uyari else {})}

    def _dikey_prizma(self, A, B, kesit, kal=5.0):
        """BK-46: A'dan B'ye düşey düzlemde kesit (s, z) (cm; s A'dan B yönünde), düzlemin iki yanına kal / 2 kalınlıkta. Makas üyeleri
        eksene paralel olmayan çizgilerde (kubbe, kırma ve çapraz makas)."""
        ux, uy = B[0] - A[0], B[1] - A[1]
        L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
        X = np.array([ux, uy, 0.0]); Z = np.array([uy, -ux, 0.0])               # yerel y = Z × X = yukarı
        prof = self.sb.profile(self.sb.polyline([np.array([_m(s), _m(z)]) for s, z in kesit], closed=True))
        pos = np.array([_m(A[0] - Z[0] * kal / 2), _m(A[1] - Z[1] * kal / 2), 0.0])
        return self.sb.extrude(prof, magnitude=_m(kal), position=pos, position_z_axis=Z, position_x_axis=X)

    def _cubuk(self, A, B, zA, zB, h=10.0, kal=5.0):
        """BK-46: A'dan B'ye (plan) zA'dan zB'ye düz çubuk; üst yüzü A–B doğrusunda, h yüksekliğinde (makasın üst başlığı ve alt başlığı)."""
        L = math.hypot(B[0] - A[0], B[1] - A[1])
        return self._dikey_prizma(A, B, [(0.0, zA - h), (L, zB - h), (L, zB), (0.0, zA)], kal)

    def kubbeler(self):
        """BK-46: kubbeler (İE-29 PR-2, D-54), çizimdeki kubbenin aynısından (`_kubbe_girdisi`). Panolar kendi pencereleriyle IfcWall, köşe
        direkleri ve kamalar IfcMember, düz duvarın bandı IfcWall, zemini (kapsam dışı) ve üç yüzlü çatısı (IfcRoof, üç sac levha, üç makas)."""
        H0 = self.G["bina"]["duvar_h"]; t = G.T_DIS
        self.kubbe_ozet = []
        for i, kb in enumerate(self.G.get("kubbeler") or [], start=1):
            hk, ze, za = kb["duvar_cm"], kb["sacak_kotu"], kb["tepe_kotu"]
            # düz duvarın kubbe üstündeki bandı: tabanın boyunca, kubbe duvarının üstünden 3 cm kertikle duvar üstüne
            x0, y0, x1, y1 = kb["taban"]
            bant = self._urun("IfcWall", f"KUBBE_{i}_UST_BANDI", predefined="SOLIDWALL")
            bant.Description = "Kubbe özel pano 100 × 2500 × 500 (ana duvarın kubbe üstündeki bandı)"
            self._yerlestir(bant)
            self._temsil(bant, self._prizma_xy([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], hk - 3, H0))
            api("type.assign_type", self.f, related_objects=[bant], relating_type=self.tip["dis"])
            L_b = max(x1 - x0, y1 - y0)
            self._pset(bant, "Pset_WallCommon", {"IsExternal": True, "Reference": "Kubbe özel pano"})
            self._pset(bant, "PortatifEv_Pano", {"BOMKalem": bant.Description, "PanoSinifi": "kubbe", "Boy_cm": L_b, "Kalinlik_cm": t,
                                                 "Yukseklik_cm": H0 - hk + 3, "Kaynak": "D-54; kitabın kubbe takımı"})
            self._qto(bant, "Qto_WallBaseQuantities", {"Length": _m(L_b), "Width": _m(t), "Height": _m(H0 - hk + 3),
                                                        "GrossSideArea": round(_m(L_b) * _m(H0 - hk + 3), 4), "NetSideArea": round(_m(L_b) * _m(H0 - hk + 3), 4)})
            # üç pano, kendi pencereleriyle (pencere panoya ortalı, `dxf_out._kubbe_plani` gibi)
            for j, q in enumerate(kb["panolar"], start=1):
                A, B = q["dis_kenar"]
                ux, uy = B[0] - A[0], B[1] - A[1]
                if -uy * q["disari"][0] + ux * q["disari"][1] > 0:              # yerel y (kalınlık) içeri baksın
                    A, B = B, A; ux, uy = -ux, -uy
                L = math.hypot(ux, uy); xa = (ux / L, uy / L, 0.0); org = (A[0], A[1], 0.0)
                w = self._urun("IfcWall", f"KUBBE_{i}_PANO_{q['tur'].upper()}_{j}", predefined="SOLIDWALL")
                w.Description = f"Kubbe {'yan' if q['tur'] == 'yan' else 'ön'} panosu {q['boy']:g} × {hk:g}, pencere {q['pencere']}"
                self._yerlestir(w, org, xa)
                self._temsil(w, self._kutu(0, 0, 0, L, t, hk))
                api("type.assign_type", self.f, related_objects=[w], relating_type=self.tip["dis"])
                pk = G.pencere_kurali(q["pencere"]); en = float(pk.en); s = (L - en) / 2.0
                a = {"tur": "pencere", "olcu": q["pencere"], "a0": s, "a1": s + en, "z0": float(pk.esik), "z1": float(pk.ust), "panolar": [None],
                     "kod": "", "kalem": f"PVC pencere {q['pencere'].replace('x', '×')} (kubbe)"}
                o = self._urun("IfcOpeningElement", f"BOSLUK_KUBBE_{i}_{j}", predefined="OPENING", kapsa=False)
                self._yerlestir(o, org, xa)
                self._temsil(o, self._kutu(s, -2, a["z0"], en, t + 4, a["z1"] - a["z0"]))
                api("feature.add_feature", self.f, feature=o, element=w)
                self._pset(o, "PortatifEv_Bosluk", {"Aciklik": -1, "Tur": "pencere", "BOMKod": ""})
                dolgu = self._dograma(100 * i + j, a, {"kalinlik": t}, org, xa, 0.0)
                api("feature.add_filling", self.f, opening=o, element=dolgu)
                self._pset(w, "Pset_WallCommon", {"IsExternal": True, "Reference": "Kubbe panosu"})
                self._pset(w, "PortatifEv_Pano", {"BOMKalem": w.Description, "PanoSinifi": "kubbe", "Boy_cm": q["boy"], "Kalinlik_cm": t,
                                                  "Yukseklik_cm": hk, "Acikliklar": f"pencere {q['pencere']}", "Kaynak": "İE-29 PR-2, D-54"})
                brut = _m(L) * _m(hk); bos = _m(en) * _m(a["z1"] - a["z0"])
                self._qto(w, "Qto_WallBaseQuantities", {"Length": _m(L), "Width": _m(t), "Height": _m(hk), "GrossSideArea": round(brut, 4),
                                                        "NetSideArea": round(brut - bos, 4)})
            # iki açılı köşe direği, düz duvarın ucunda iki kama (`dxf_out._kubbe_plani` ile aynı çokgenler)
            pn, dis, ic, bn = kb["panolar"], kb["dis"], kb["ic"], kb["bant"]
            for k, poly in enumerate(([pn[0]["dis_kenar"][1], dis[1], pn[1]["dis_kenar"][0], ic[1]],
                                      [pn[1]["dis_kenar"][1], dis[2], pn[2]["dis_kenar"][0], ic[2]],
                                      [dis[0], self._kenar_ic(pn[0], t, 0), ic[0], bn[9]],
                                      [dis[3], self._kenar_ic(pn[2], t, 1), ic[3], bn[4]]), start=1):
                e = self._urun("IfcMember", f"KUBBE_{i}_KOSE_DIREGI_{k}", predefined="STUD")
                self._yerlestir(e)
                self._temsil(e, self._prizma_xy([tuple(p) for p in poly], 0.0, hk), "galv")
                self._pset(e, "PortatifEv_Kapsam", {"BOMKalem": "Özel açılı köşe direği + kapaması (kubbe)", "KesimBoyuTanimli": False})
            z = self._urun("IfcSlab", f"KUBBE_{i}_ZEMINI", predefined="FLOOR")
            self._yerlestir(z)
            self._temsil(z, self._prizma_xy([tuple(p) for p in dis], -15, 0), "beton")
            self._pset(z, "PortatifEv_Kapsam", {"BOMKalem": "Kubbe zemini — kapsam dışı (bayi/saha)", "KapsamDisi": True})
            # çatı: üç üçgen yüz, saçak çizgisinde `sacak_kotu`, tepede `tepe_kotu` (görünüşteki çizgiler, `cephe_gorunus._kubbe_gorunusu`)
            S, T = [tuple(p) for p in kb["sacak"]], tuple(kb["tepe"])
            roof = self._urun("IfcRoof", f"KUBBE_CATISI_{i}", predefined="HIP_ROOF")
            self._yerlestir(roof)
            self._pset(roof, "PortatifEv_Cati", {"Kubbe": kb["mahal"], "Sacak_cm": G.KUBBE["sacak_cm"], "SacakKotu_cm": ze, "TepeKotu_cm": za,
                                                 "Ortu": "OSB 11 mm + membran + shingle antrasit (kubbe takımı)"})
            levhalar = []
            for k, (Sa, Sb) in enumerate(zip(S, S[1:]), start=1):
                vx, vy = Sb[0] - Sa[0], Sb[1] - Sa[1]; vl = math.hypot(vx, vy)
                nx, ny = -vy / vl, vx / vl
                if nx * (T[0] - Sa[0]) + ny * (T[1] - Sa[1]) < 0:
                    nx, ny = -nx, -ny
                uz = nx * (T[0] - Sa[0]) + ny * (T[1] - Sa[1])
                sl = self._urun("IfcSlab", f"CATI_KUBBE_{i}_{k}", predefined="ROOF", kapsa=False)
                self._yerlestir(sl)
                self._temsil(sl, self._egik_levha([Sa, Sb, T], Sa, (nx, ny), (za - ze) / uz, ze, 4.0), "sac")
                self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Kubbe kaplaması (OSB + membran + shingle) — yüzey"})
                levhalar.append(sl)
            api("aggregate.assign_object", self.f, relating_object=roof, products=levhalar)
            # üç makas: biri düz duvar boyunca (saçak uçlarından tepeye), ikisi tepeden ön köşelere (yüzlerin birleştiği hat boyunca)
            def kot(P):                                                    # çatı yüzünün altı (levhanın altı) P'de: saçakta ze, tepede za
                return min(self._yuz_kotu(Sa, Sb, T, ze, za, P) for Sa, Sb in zip(S, S[1:]))
            makaslar = [("DUZ_DUVAR", [(S[0], T), (T, S[3])], (dis[0], dis[3])),
                        ("SOL_KOSE", [(T, S[1])], (T, dis[1])), ("SAG_KOSE", [(T, S[2])], (T, dis[2]))]
            for k, (ad, ustler, (Pa, Pb)) in enumerate(makaslar, start=1):
                asm = self._urun("IfcElementAssembly", f"MAKAS_KUBBE_{i}_{k}", predefined="USERDEFINED", ObjectType="KUBBE_MAKASI")
                # TRUSS değil: TRUSS'u ana çatının makası sayan okuyucular (kart modelinin H türü, yerleşim planı) kubbe makasını almasın
                self._yerlestir(asm)
                self._pset(asm, "PortatifEv_Kapsam", {"BOMKalem": "Kubbe makası 80 × 0,8", "Kubbe": kb["mahal"], "Yer": ad})
                uyeler = []
                for n_, (P, Q) in enumerate(ustler, start=1):
                    m = self._urun("IfcMember", f"MAKAS_KUBBE_{i}_{k}_UST_{n_}", predefined="CHORD", kapsa=False)
                    self._yerlestir(m); self._temsil(m, self._cubuk(P, Q, kot(P), kot(Q), 8.0), "galv")
                    uyeler.append(m)
                m = self._urun("IfcMember", f"MAKAS_KUBBE_{i}_{k}_ALT", predefined="CHORD", kapsa=False)
                self._yerlestir(m); self._temsil(m, self._cubuk(tuple(Pa), tuple(Pb), hk + 8, hk + 8, 8.0), "galv")
                uyeler.append(m)
                api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler)
            self.kubbe_ozet.append({"mahal": kb["mahal"], "makas": len(makaslar), "yuz": len(levhalar), "pano": len(kb["panolar"])})

    @staticmethod
    def _kenar_ic(q, t, uc):
        """Kubbe panosunun iç yüzündeki uç (`G._kubbe_geometrisi`'nin `ic_kenar`'ı: dış kenarın ucundan içeri, panoya dik t)."""
        A = q["dis_kenar"][uc]; nx, ny = q["disari"]
        return (A[0] - nx * t, A[1] - ny * t)

    @staticmethod
    def _yuz_kotu(Sa, Sb, T, ze, za, P):
        """Saçak kenarı Sa–Sb (kot ze) ve tepe T (kot za) üçgen yüzünün düzleminde P'nin kotu."""
        vx, vy = Sb[0] - Sa[0], Sb[1] - Sa[1]; vl = math.hypot(vx, vy)
        nx, ny = -vy / vl, vx / vl
        uz = nx * (T[0] - Sa[0]) + ny * (T[1] - Sa[1])
        if uz < 0:
            nx, ny, uz = -nx, -ny, -uz
        return ze + (za - ze) * (nx * (P[0] - Sa[0]) + ny * (P[1] - Sa[1])) / uz

    def _prizma_yz(self, pts_yz, x0, x1):
        """Dünya y-z düzlemindeki kesit (cm), x0..x1 boyunca (dünya koordinatı)."""
        prof = self.sb.profile(self.sb.polyline([np.array([_m(y), _m(z)]) for y, z in pts_yz], closed=True))
        return self.sb.extrude(prof, magnitude=_m(x1 - x0), position=np.array([_m(x0), 0.0, 0.0]),
                               position_z_axis=np.array([1.0, 0.0, 0.0]), position_x_axis=np.array([0.0, 1.0, 0.0]))

    def _cati_y(self):
        """Makaslar y yönünde (derinlik kısa kenar), mahya x boyunca. cati() ile aynı kesit; eksenler yer değiştirir."""
        G = self.G; c = G["bina"]["cati"]; H0 = G["bina"]["duvar_h"]
        s, eg, top = c["sacak"], c["egim"], c["topuk"]
        Wd, Hd = self.Wd, self.Hd; ym = Hd / 2
        td = max(p["kalinlik"] for p in G["panolar"])
        zs = H0 + top; zm = zs + (ym + s) * eg; t = 4.0
        roof = self._urun("IfcRoof", "ANA_CATI", predefined="GABLE_ROOF")
        self._yerlestir(roof)
        alan = 2 * math.hypot(ym + s, (ym + s) * eg) * (Wd + 2 * s) / 1e4
        self._pset(roof, "PortatifEv_Cati", {"Egim_yuzde": eg * 100, "Sacak_cm": s, "Topuk_cm": top, "Mahya_cm": round(zm, 1),
                                             "MakasYonu": "kısa kenar (y)", "Ortu": "trapez sac antrasit", "OrtuAlani_m2": round(alan, 2)})
        parcalar = []
        for ad, k in (("CATI_ON", [(-s, zs + 10), (ym, zm + 10), (ym, zm + 10 + t), (-s, zs + 10 + t)]),
                      ("CATI_ARKA", [(ym, zm + 10), (Hd + s, zs + 10), (Hd + s, zs + 10 + t), (ym, zm + 10 + t)])):
            sl = self._urun("IfcSlab", ad, predefined="ROOF", kapsa=False)
            self._yerlestir(sl); self._temsil(sl, self._prizma_yz(k, -s, Wd + s), "sac")
            self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Trapez çatı sacı (antrasit) — yüzey"})
            parcalar.append(sl)
        api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
        zt = lambda y: zs + (min(y, Hd - y) + s) * eg
        alin = [(0, H0), (Hd, H0), (Hd, zt(Hd)), (ym, zt(ym)), (0, zt(0))]
        for ad, xa, xb in (("ALIN_SOL", 0, td), ("ALIN_SAG", Wd - td, Wd)):
            pl = self._urun("IfcPlate", ad, predefined="SHEET")
            self._yerlestir(pl); self._temsil(pl, self._prizma_yz(alin, xa, xb), "fiber")
            self._pset(pl, "PortatifEv_Kapsam", {"BOMKalem": "Çatı alın dolgusu (üçgen) — kural teyit edilecek"})
        # makaslar pano eklerinde, makaslar x'i geçen beşikle (`cati`) aynı kural (BK-12 PR-R): iki baş makas kalkan duvarların
        # ekseninde, orta makaslar boydan boya kesintisiz koşan saçak duvarının (y = 0 ya da Hd) pano eklerinde; iki saçak duvarı da
        # kesintisizse ortak ekler. Ekler düzenli olmalı (orta makaslar 125,5 arayla, uç açıklıklar 125,5'ten uzun değil, sayı yükleme
        # listesininkiyle aynı: ⌈(boy − 2 × dış duvar) ÷ 125,5⌉ + 1); değilse eşit aralık, listenin sayısında, uyarıyla (K16).
        # BK-46 (havuz denetimi HD-08, 16 Kasım 2026): eskiden x yönündeki her dış duvar panosunun eki makas alıyordu (ön ve arka duvarın
        # bütün ekleri, düzenlilik denetimi yok); 85, 83, 61 m²'de makas listeden fazla, 102 m²'de eksikti. Uç açıklık 125,5 + yarım duvara
        # kadar düzenli: makas y + `kisa_kenar` x'te köşe x yönünde 10 cm, ilk ek dış yüzden 135,5, baş makas 5'te (PK-02 paftası: makaslar
        # 5, 135,5 … 637,5, 768; geometri hakemi, 16 Kasım).
        n_liste = math.ceil((Wd - 2 * td) / 125.5 - 1e-6) + 1

        def sacak_ekleri(y):
            ar = sorted((p["rect"][0], p["rect"][2]) for p in G["panolar"] if p["yon"] == "x" and p["tur"] == "dis"
                        and abs((p["rect"][1] if y == 0 else p["rect"][3]) - y) < 1e-6)
            tam = (bool(ar) and ar[0][0] <= td + 1e-6 and ar[-1][1] >= Wd - td - 1e-6
                   and all(abs(a[1] - b[0]) < 1e-6 for a, b in zip(ar, ar[1:])))
            return {round(v, 3) for a in ar for v in a if td + 1e-6 < v < Wd - td - 1e-6} if tam else None
        ekler = [e for e in (sacak_ekleri(0), sacak_ekleri(Hd)) if e is not None]
        uyari, xs = [], None
        if not ekler:
            uyari.append(f"makas yeri: boydan boya kesintisiz saçak duvarı yok; eşit aralıklı {n_liste} makas")
        else:
            if len(ekler) == 2 and ekler[0] != ekler[1]:
                uyari.append("makas yeri: iki saçak duvarının pano ekleri farklı; ortak ekler alındı")
            aday = [td / 2] + sorted(set.intersection(*ekler)) + [Wd - td / 2]
            araliklar = [b - a for a, b in zip(aday, aday[1:])]
            if (len(aday) == n_liste and all(abs(a - 125.5) < 0.01 for a in araliklar[1:-1])
                    and all(0 < a < 125.5 + td / 2 + 0.01 for a in (araliklar[0], araliklar[-1]))):
                xs = aday
            else:
                uyari.append(f"makas yeri: saçak duvarının pano ekleri düzensiz ({len(aday)} makas, listede {n_liste}; "
                             f"aralıklar {', '.join(f'{a:g}' for a in (round(x, 2) for x in araliklar))}); eşit aralıklı {n_liste} makas")
        if xs is None:
            xs = [td / 2 + i * (Wd - td) / (n_liste - 1) for i in range(n_liste)]
        if uyari:
            self._pset(roof, "PortatifEv_Uyari", {"MakasYeri": " | ".join(uyari)})
        n = len(xs)
        for i, x in enumerate(xs):
            asm = self._urun("IfcElementAssembly", f"MAKAS_{i + 1:02d}", predefined="TRUSS")
            self._yerlestir(asm)
            self._pset(asm, "PortatifEv_Kapsam", {"BOMKalem": "Çatı makası (baş)" if i in (0, n - 1) else "Çatı makası (orta)", "Aciklik_cm": round(Hd, 1)})
            q1, q3 = ym / 2, ym + ym / 2
            uyeler = (("ALT_BASLIK", [(0, H0), (Hd, H0), (Hd, H0 + 10), (0, H0 + 10)]),
                      ("UST_ON", [(-s, zs), (ym, zm), (ym, zm + 10), (-s, zs + 10)]),
                      ("UST_ARKA", [(ym, zm), (Hd + s, zs), (Hd + s, zs + 10), (ym, zm + 10)]),
                      ("DIKME_ORTA", [(ym - 3, H0 + 10), (ym + 3, H0 + 10), (ym + 3, zt(ym)), (ym - 3, zt(ym))]),
                      ("DIKME_ON", [(q1 - 3, H0 + 10), (q1 + 3, H0 + 10), (q1 + 3, zt(q1)), (q1 - 3, zt(q1))]),
                      ("DIKME_ARKA", [(q3 - 3, H0 + 10), (q3 + 3, H0 + 10), (q3 + 3, zt(q3)), (q3 - 3, zt(q3))]),
                      ("CAPRAZ_ON", [(q1 - 3, H0 + 10), (q1 + 5, H0 + 10), (ym - 3, zt(ym) - 8), (ym - 11, zt(ym) - 8)]),
                      ("CAPRAZ_ARKA", [(q3 - 5, H0 + 10), (q3 + 3, H0 + 10), (ym + 11, zt(ym) - 8), (ym + 3, zt(ym) - 8)]))
            uyeler_e = []
            for ad, k in uyeler:
                m = self._urun("IfcMember", f"MAKAS_{i + 1:02d}_{ad}", predefined="CHORD" if "BASLIK" in ad or "UST" in ad else "MEMBER", kapsa=False)
                self._yerlestir(m); self._temsil(m, self._prizma_yz(k, x - 2.5, x + 2.5), "galv")
                uyeler_e.append(m)
            api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler_e)
        self.cati_ozet = {"mahya_cm": round(zm, 1), "makas": n, "cati_alan_m2": round(alan, 2), "makas_ekseni": "y", "aciklik_cm": round(Hd, 1),
                          "makas_x_cm": [round(x, 2) for x in xs], **({"uyari": uyari} if uyari else {})}

    def _teras_kesiti(self, cephe, kutu, za_duvar, za_dis, t):
        """D-52 ek: teras panelinin eğik prizması: plandaki kutu, altı duvar ucunda `za_duvar`, dış uçta `za_dis`,
        düşeyde `t` kalın; kesit verandanın derinliği boyunca, cephe boyunca uzar."""
        X0, Y0, X1, Y1 = kutu
        if cephe in ("on", "arka"):
            w, o = (Y1, Y0) if cephe == "on" else (Y0, Y1)
            return self._prizma_yz([(w, za_duvar), (o, za_dis), (o, za_dis + t), (w, za_duvar + t)], X0, X1)
        w, o = (X1, X0) if cephe == "sol" else (X0, X1)
        return self._prizma_xz([(w, za_duvar), (o, za_dis), (o, za_dis + t), (w, za_duvar + t)], Y0, Y1)

    def _egik_levha(self, cokgen, p0, u, egim, z0, t):
        """Eğik çatı levhası: plan çokgeni (cm), saçak çizgisindeki bir nokta `p0`, planda yukarı yön `u` (birim), eğim; alt yüzü saçakta
        `z0`, kalınlık `t`. Yerel x mahyaya paralel, yerel y eğim boyunca yukarı, yerel z yüzün normali (yukarı)."""
        ux, uy = u; n = math.hypot(1.0, egim)
        X = np.array([uy, -ux, 0.0]); Y = np.array([ux, uy, egim]) / n; Z = np.cross(X, Y)
        yerel = [(((x - p0[0]) * uy - (y - p0[1]) * ux), ((x - p0[0]) * ux + (y - p0[1]) * uy) * n) for x, y in cokgen]
        prof = self.sb.profile(self.sb.polyline([np.array([_m(a), _m(b)]) for a, b in yerel], closed=True))
        return self.sb.extrude(prof, magnitude=_m(t), position=np.array([_m(p0[0]), _m(p0[1]), _m(z0)]), position_z_axis=Z, position_x_axis=X)

    def _makas(self, ad, kalem, ozellik, b0, b1, konum, mahya_x, zs, eg, s):
        """Beşik makası (`_cati_y` ile aynı çubuklar): b0..b1 dış yüzden dış yüze, saçaklar s; mahya x boyunca ise makas y–z düzleminde.
        İE-15 K6 (D-53 madde 7): ana makaslar cumba makasının arkasına geri çekilince b0..b1 çatının ayak izi (açıklık 861, listedeki gibi);
        verandanın üstündeki makas topuğuyla ön kirişe oturur, salonun üstündekinin saçak ucu ön duvarın üstünde."""
        H0 = self.G["bina"]["duvar_h"]; ym = (b0 + b1) / 2; zm = zs + (ym - b0 + s) * eg
        zt = lambda y: zs + (min(y - b0, b1 - y) + s) * eg
        q1, q3 = (b0 + ym) / 2, (ym + b1) / 2
        uyeler = (("ALT_BASLIK", [(b0, H0), (b1, H0), (b1, H0 + 10), (b0, H0 + 10)]),
                  ("UST_1", [(b0 - s, zs), (ym, zm), (ym, zm + 10), (b0 - s, zs + 10)]),
                  ("UST_2", [(ym, zm), (b1 + s, zs), (b1 + s, zs + 10), (ym, zm + 10)]),
                  ("DIKME_ORTA", [(ym - 3, H0 + 10), (ym + 3, H0 + 10), (ym + 3, zt(ym)), (ym - 3, zt(ym))]),
                  ("DIKME_1", [(q1 - 3, H0 + 10), (q1 + 3, H0 + 10), (q1 + 3, zt(q1)), (q1 - 3, zt(q1))]),
                  ("DIKME_2", [(q3 - 3, H0 + 10), (q3 + 3, H0 + 10), (q3 + 3, zt(q3)), (q3 - 3, zt(q3))]),
                  ("CAPRAZ_1", [(q1 - 3, H0 + 10), (q1 + 5, H0 + 10), (ym - 3, zt(ym) - 8), (ym - 11, zt(ym) - 8)]),
                  ("CAPRAZ_2", [(q3 - 5, H0 + 10), (q3 + 3, H0 + 10), (ym + 11, zt(ym) - 8), (ym + 3, zt(ym) - 8)]))
        asm = self._urun("IfcElementAssembly", ad, predefined="TRUSS")
        self._yerlestir(asm)
        self._pset(asm, "PortatifEv_Kapsam", {"BOMKalem": kalem, **ozellik})
        uyeler_e = []
        for u_ad, k in uyeler:
            m = self._urun("IfcMember", f"{ad}_{u_ad}", predefined="CHORD" if "BASLIK" in u_ad or "UST" in u_ad else "MEMBER", kapsa=False)
            self._yerlestir(m)
            self._temsil(m, self._prizma_yz(k, konum - 2.5, konum + 2.5) if mahya_x else self._prizma_xz(k, konum - 2.5, konum + 2.5), "galv")
            uyeler_e.append(m)
        api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler_e)

    def _cati_serit(self):
        """İE-24: girintili gövdenin çatısı `cati_serit.tanim`'den (çizimdeki, görünüşlerdeki ve listedeki çatının aynısı). Her düzlem kendi
        plan çokgeniyle eğik levha (aynı düzlemdeki ana çatı ve cumba yüzü tek levha); kalkan dolguları duvar üstünden (altında başka çatı
        varsa onun yüzünden) çatının altına; makaslar parça parça tanımın makas yerlerinde, dış yüzden dış yüze. Ana çatının makasları
        "Çatı makası (baş/orta)", cumbanınkiler "Cumba makası" (Lokman, 30 Ekim 2026 13:49; kartı kart modelinde).

        İE-15 K6: çapraz cumbada (`cati_capraz`, `capraz`) cumbanın makasları listedeki adıyla "Yavru makas · cumba" (D-47); ilki dış uçtaki
        kalkan duvarının üstünde beşik makası, ötekiler ana çatının üstünde, iki dere arasında (`_ana_ustu_makas`)."""
        from shapely.geometry import Polygon
        G = self.G; T = G["cati_serit"]; H0 = G["bina"]["duvar_h"]
        s, eg_, top = T["sacak"], G["bina"]["cati"]["egim"], T["topuk"]
        zs = H0 + top; t = 4.0
        D = {d["ad"]: d for d in T["duzlemler"]}

        def p0(d):
            return (d["sacak"].get("x", 0.0), d["sacak"].get("y", 0.0))

        def kot(d, x, y):                                       # makas üst başlığının kotu (levhanın altı + 10)
            (ox, oy), (ux, uy) = p0(d), d["yukari"]
            return d["sacak_kotu"] + d["egim"] * ((x - ox) * ux + (y - oy) * uy)
        roof = self._urun("IfcRoof", "ANA_CATI", predefined="GABLE_ROOF")
        self._yerlestir(roof)
        alan = sum(Polygon(d["plan"]).area * math.hypot(1.0, d["egim"]) for d in T["duzlemler"]) / 1e4
        mahya = max(q["mahya_kotu"] for q in T["parcalar"])
        self._pset(roof, "PortatifEv_Cati", {"Egim_yuzde": eg_ * 100, "Sacak_cm": s, "Topuk_cm": top, "Mahya_cm": round(mahya, 1),
                                             "MakasYonu": "ana çatı + çapraz cumba (İE-15 K6)" if T.get("capraz") else "ana çatı + paralel cumba (İE-24)",
                                             "Ortu": "trapez sac antrasit", "OrtuAlani_m2": round(alan, 2)})
        if T.get("uyarilar"):                                   # BK-46 (geometri hakemi): uyarı IFC'de de (K16; `cati`, `_cati_y` gibi)
            self._pset(roof, "PortatifEv_Uyari", {"MakasYeri": " | ".join(T["uyarilar"])})
        parcalar = []
        for j, d in enumerate(T["duzlemler"]):
            sl = self._urun("IfcSlab", f"CATI_{j + 1}", predefined="ROOF", kapsa=False)
            self._yerlestir(sl)
            self._temsil(sl, self._egik_levha(d["plan"], p0(d), d["yukari"], d["egim"], d["sacak_kotu"] + 10, t), "sac")
            self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Trapez çatı sacı (antrasit) — yüzey", "Duzlem": d["ad"]})
            parcalar.append(sl)
        for j, m in enumerate(m for m in T.get("mahal_catilari", []) if m["tip"] != "kirma"):   # İE-17 PR-2: açık mahalin kendi panel çatısı
                                                                    # (dikme ve profil `baglantilar`; köşe kırması yukarıda ana çatının levhası)
            d = m["duzlem"]
            sl = self._urun("IfcSlab", f"MAHAL_CATI_{j + 1}", predefined="ROOF", kapsa=False)
            self._yerlestir(sl)
            self._temsil(sl, self._egik_levha(d["plan"], p0(d), d["yukari"], d["egim"], d["sacak_kotu"], 10.0), "sac")
            self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Çatı paneli (sandviç) — açık mahalin kendi çatısı", "Duzlem": d["ad"], "Mahal": m["mahal"]})
            parcalar.append(sl)
        api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
        self._kalkan_dolgulari(T["kalkanlar"], D, kot, H0)
        # makaslar: parça parça tanımın makas yerlerinde (orta makaslar saçak duvarlarının pano eklerinde; cumbanın iç ucunda makas yok)
        n, yerler = 0, []
        for q in sorted(T["parcalar"], key=lambda q: q["rol"] != "ana"):
            mahya_x = abs(q["mahya"][0][1] - q["mahya"][1][1]) < 1e-6
            b0, b1 = q["b"]
            for m in q["makaslar"]:
                n += 1
                if q["rol"] == "ana":
                    kalem = "Çatı makası (baş)" if m["rol"] == "bas" else "Çatı makası (orta)"
                elif q.get("capraz"):
                    kalem = f"Yavru makas · {q['ad']}"
                else:
                    kalem = f"Cumba makası · {q['ad']}"
                oz = {"Aciklik_cm": round(b1 - b0, 1), "CatiParcasi": q["ad"], "Rol": "baş" if m["rol"] == "bas" else "orta"}
                if m.get("ana_ustunde"):                        # BK-46: iki cumbada her cumba kendi yüzleriyle (`duzlemler`)
                    T_ = {**T, "duzlemler": [d for d in T["duzlemler"] if d["ad"].startswith("ana ") or d["ad"] in q["duzlemler"]]} \
                        if q.get("duzlemler") else T
                    self._ana_ustu_makas(f"MAKAS_{n:02d}", kalem, oz, T_, q, m["konum"], kot, m.get("uclar"))
                else:
                    self._makas(f"MAKAS_{n:02d}", kalem, oz, b0, b1, m["konum"], mahya_x, zs, eg_, s)
                yerler.append({"parca": q["ad"], "rol": m["rol"], "konum_cm": round(m["konum"], 2)})
        self.cati_ozet = {"mahya_cm": round(mahya, 1), "makas": n, "cati_alan_m2": round(alan, 2), "makaslar": yerler,
                          **({"uyari": T["uyarilar"]} if T["uyarilar"] else {})}

    def _kalkan_dolgulari(self, kalkanlar, D, kot, H0):
        """Kalkan dolguları: duvar üstünden (altında başka bir çatı varsa onun yüzünden) üstteki çatının altına; duvarın içinde 10 cm.
        `kot(d, x, y)` makas üst başlığının kotu (levhanın altı − 10); BK-46'da `_cati_serit`'ten ayrıldı (kırma da okur)."""
        from shapely.geometry import Polygon
        for i, k in enumerate(kalkanlar):
            y0, y1 = k["aralik"]; c = k["konum"]; ic = 1.0 if k["ic"] in ("dogu", "kuzey") else -1.0
            yer = (lambda a: (c, a)) if k["eksen"] == "x" else (lambda a: (a, c))
            ust, alt = [D[a] for a in k["ust"]], [D[a] for a in k.get("alt", [])]
            kirik = {y0, y1}
            for d1 in ust + alt:                                # kotların kırıldığı yerler: iki düzlemin kesiştiği nokta
                for d2 in ust + alt:
                    f0, f1 = kot(d1, *yer(0.0)) - kot(d2, *yer(0.0)), kot(d1, *yer(1.0)) - kot(d2, *yer(1.0))
                    if abs(f1 - f0) > 1e-9 and y0 < -f0 / (f1 - f0) < y1:
                        kirik.add(-f0 / (f1 - f0))
            ys = sorted(kirik)

            def alti(ds):                                       # kesitte düzlemlerin (gövdede en alçağı) altı, duvar üstüne kadar
                return Polygon([(ys[0], H0)] + [(a, max(H0, min(kot(d, *yer(a)) for d in ds))) for a in ys] + [(ys[-1], H0)]).buffer(0)
            g = alti(ust).difference(alti(alt)) if alt else alti(ust)
            for n_, pg in enumerate(sorted(getattr(g, "geoms", [g]), key=lambda p_: p_.bounds)):
                if pg.is_empty or pg.area < 1.0:
                    continue
                kesit = list(pg.simplify(0.01).exterior.coords)[:-1]
                a0, a1 = sorted((c, c + 10 * ic))
                pl = self._urun("IfcPlate", f"ALIN_{i + 1}" + (f"_{n_ + 1}" if n_ else ""), predefined="SHEET")
                self._yerlestir(pl)
                self._temsil(pl, self._prizma_yz(kesit, a0, a1) if k["eksen"] == "x" else self._prizma_xz(kesit, a0, a1), "fiber")
                self._pset(pl, "PortatifEv_Kapsam", {"BOMKalem": "Çatı alın dolgusu (üçgen) — kural teyit edilecek", "Kalkan": k["ad"]})

    def _cati_kirma(self):
        """BK-46: kırma çatı (`_kirma_girdisi`): her düzlem kendi plan çokgeniyle eğik levha (`_cati_serit` gibi), tek uçlu kırmada kalkan
        dolgusu; makaslar listenin makas planında, üst başlıkları çatının altını izler (`_yuzey_makasi`). IfcRoof HIP_ROOF."""
        from shapely.geometry import Polygon
        G = self.G; Kg = G["cati_kirma"]; T = Kg["tanim"]; H0 = G["bina"]["duvar_h"]
        s, top, t = T["sacak"], T["topuk"], 4.0
        D = {d["ad"]: d for d in T["duzlemler"]}

        def p0(d):
            return (d["sacak"].get("x", 0.0), d["sacak"].get("y", 0.0))

        def kot(d, x, y):                                       # makas üst başlığının kotu (levhanın altı − 10)
            (ox, oy), (ux, uy) = p0(d), d["yukari"]
            return d["sacak_kotu"] + d["egim"] * ((x - ox) * ux + (y - oy) * uy)

        def yuzey(x, y):                                        # kırma dışbükey: çatının altı en alçak düzlemde (levhanın altı)
            return min(kot(d, x, y) for d in T["duzlemler"]) + 10.0
        roof = self._urun("IfcRoof", "ANA_CATI", predefined="HIP_ROOF")
        self._yerlestir(roof)
        alan = sum(Polygon(d["plan"]).area * math.hypot(1.0, d["egim"]) for d in T["duzlemler"]) / 1e4
        mahya = max(yuzey(*v) for d in T["duzlemler"] for v in d["plan"]) - 10.0
        eg = G["bina"]["cati"]["egim"]
        self._pset(roof, "PortatifEv_Cati", {"Egim_yuzde": eg * 100, "Sacak_cm": s, "Topuk_cm": top, "Mahya_cm": round(mahya, 1),
                                             "MakasYonu": "kırma: " + ("tek uçlu (İE-29)" if Kg["tip"] == "tek_uclu" else "iki uçlu (İE-33)"),
                                             "Ortu": "trapez sac antrasit", "OrtuAlani_m2": round(alan, 2)})
        if Kg["uyari"]:
            self._pset(roof, "PortatifEv_Uyari", {"MakasYeri": " | ".join(Kg["uyari"])})
        parcalar = []
        for j, d in enumerate(T["duzlemler"]):
            sl = self._urun("IfcSlab", f"CATI_{j + 1}", predefined="ROOF", kapsa=False)
            self._yerlestir(sl)
            self._temsil(sl, self._egik_levha(d["plan"], p0(d), d["yukari"], d["egim"], d["sacak_kotu"] + 10, t), "sac")
            self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Trapez çatı sacı (antrasit) — yüzey", "Duzlem": d["ad"]})
            parcalar.append(sl)
        api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
        self._kalkan_dolgulari(T["kalkanlar"], D, kot, H0)
        yerler = []
        for n, m in enumerate(Kg["makaslar"], start=1):
            self._yuzey_makasi(f"MAKAS_{n:02d}", f"{m['kalem']} · ana çatı", {"Rol": m["rol"], "CatiParcasi": "ana çatı"},
                               m["ust"], m["alt"], T["duzlemler"], kot)
            yerler.append({"parca": "ana çatı", "rol": m["rol"], "konum_cm": round(m["konum"], 2)})
        self.cati_ozet = {"mahya_cm": round(mahya, 1), "makas": len(yerler), "cati_alan_m2": round(alan, 2), "makaslar": yerler,
                          "tip": "kirma", **({"uyari": Kg["uyari"]} if Kg["uyari"] else {})}

    def _yuzey_makasi(self, ad, kalem, ozellik, ust, alt, duzlemler, kot, h=10.0):
        """BK-46: çatının altını izleyen makas (kırmada ana, kısa ve çapraz makas). Üst başlık `ust` (plan, saçaktan) boyunca, üstü çatının
        altında (`yuzey`, en alçak düzlem); düzlem değişen yerde kırılır. Alt başlık `alt` boyunca duvar üstünde; kırılma yerlerinde ve
        ortada dikme. Gösterim; kesit ve dolgu çubukları kesim bilgisi değildir. 5 cm'lik başlık eğimin içine girmesin diye üstü çatının
        altından yarım en × en dik eğim kadar aşağıda; çapraz makasın başlığı saçak köşesinden yarım en içeride başlar (geometri hakemi)."""
        H0 = self.G["bina"]["duvar_h"]
        dz = 2.5 * max(d["egim"] for d in duzlemler)
        yuzey_d = lambda d, P: kot(d, *P) + 10.0 - dz                 # noqa: E731 — düzlemin levhasının altı (başlığın yarım eni kadar)
        yuzey = lambda x, y: min(yuzey_d(d, (x, y)) for d in duzlemler)   # noqa: E731 — dışbükey çatı: en alçak düzlem
        (px, py), (qx, qy) = ust
        L0 = math.hypot(qx - px, qy - py)
        if abs(qx - px) > 1e-6 and abs(qy - py) > 1e-6:              # çapraz: başlığın iki kenarı da saçak köşesinin içinde
            tr = 2.5 * max(abs(qx - px) / abs(qy - py), abs(qy - py) / abs(qx - px))
            if L0 > 2 * tr:
                px, py = px + (qx - px) * tr / L0, py + (qy - py) * tr / L0
        nok = lambda u: (px + (qx - px) * u, py + (qy - py) * u)    # noqa: E731
        kirik = {0.0, 1.0}
        for i, d1 in enumerate(duzlemler):                      # iki düzlemin bu çizgide eşitlendiği yer (yalnız en alçak olanlar)
            for d2 in duzlemler[i + 1:]:
                f = lambda u: yuzey_d(d1, nok(u)) - yuzey_d(d2, nok(u))   # noqa: E731
                f0, f1 = f(0.0), f(1.0)
                if abs(f1 - f0) > 1e-9 and 0.0 < -f0 / (f1 - f0) < 1.0:
                    u = -f0 / (f1 - f0)
                    if abs(yuzey(*nok(u)) - yuzey_d(d1, nok(u))) < 1e-6:
                        kirik.add(u)
        L_ust = math.hypot(qx - px, qy - py)
        us = []
        for u in sorted(kirik):                                 # 0,5 cm'den kısa parça yok (geometri hakemi: 0,0044 cm'lik üye)
            if us and (u - us[-1]) * L_ust < 0.5:
                if u == 1.0:
                    us[-1] = 1.0
                continue
            us.append(u)
        uyeler = []
        for k, (u0, u1) in enumerate(zip(us, us[1:]), start=1):
            A, B = nok(u0), nok(u1)
            uyeler.append((f"UST_{k}", self._cubuk(A, B, yuzey(*A), yuzey(*B), h)))
        (ax, ay), (bx, by) = alt
        uyeler.append(("ALT_BASLIK", self._cubuk((ax, ay), (bx, by), H0 + h, H0 + h, h)))
        L = math.hypot(bx - ax, by - ay)
        dikme = sorted({0.5} | {u for u in us if 0.0 < u < 1.0})
        for k, u in enumerate(dikme, start=1):                 # alt başlığın üstünde, üst başlığın altına
            X, Y = nok(u)
            sa = (X - ax) * (bx - ax) / L + (Y - ay) * (by - ay) / L if L > 0 else 0.0
            if not 3.0 < sa < L - 3.0:
                continue
            Pz = (ax + (bx - ax) * sa / L, ay + (by - ay) * sa / L)
            zt = yuzey(*Pz) - h
            if zt - (H0 + h) < 5.0:
                continue
            uyeler.append((f"DIKME_{k}", self._dikey_prizma((ax, ay), (bx, by), [(sa - 3, H0 + h), (sa + 3, H0 + h), (sa + 3, zt), (sa - 3, zt)])))
        asm = self._urun("IfcElementAssembly", ad, predefined="TRUSS")
        self._yerlestir(asm)
        self._pset(asm, "PortatifEv_Kapsam", {"BOMKalem": kalem, **ozellik, "Aciklik_cm": round(L, 1)})
        uyeler_e = []
        for u_ad, oge in uyeler:
            m = self._urun("IfcMember", f"{ad}_{u_ad}", predefined="CHORD" if "BASLIK" in u_ad or "UST" in u_ad else "MEMBER", kapsa=False)
            self._yerlestir(m); self._temsil(m, oge, "galv")
            uyeler_e.append(m)
        api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler_e)

    def _ana_ustu_makas(self, ad, kalem, ozellik, T, q, konum, kot, uclar=None):
        """İE-15 K6: çapraz cumbanın ana çatının üstündeki makası (D-47; paftada "iki ana makasın arasında kısa"): iki dere arasında, alt
        başlığı ana makasların üst başlığının üstünde (ana çatının o kesitteki kotu), üst başlıkları cumbanın yüzleri boyunca mahyaya. Uçları
        çatı tanımında (`uclar`; AP-06 paftasındaki gibi iki ana makasın ekseninden 36,3 dışarıda, `cati_capraz._yavru_yeri`); tanımda yoksa
        topukta (üst başlığın üstü alt başlığın üstüne indiği yerde)."""
        from .cati_capraz import yavru_acikligi
        D = {d["ad"]: d for d in T["duzlemler"]}
        mahya_y = abs(q["mahya"][0][0] - q["mahya"][1][0]) < 1e-6                 # cumbanın mahyası y boyunca: makas x–z düzleminde
        u0, u1 = yavru_acikligi(T, q, konum)
        um = (q["b"][0] + q["b"][1]) / 2
        nok = (lambda u: (u, konum)) if mahya_y else (lambda u: (konum, u))
        ana = [d for n_, d in D.items() if n_.startswith("ana ")]
        z_alt = min(kot(d, *nok(um)) for d in ana) + 10                        # ana makasın üst başlığının üstü
        cumba = [d for n_, d in D.items() if not n_.startswith("ana ")]
        zt = lambda u: min(kot(d, *nok(u)) for d in cumba)                    # cumbanın üst başlığının altı
        # uçlar (topuk): üst başlığın üstü alt başlığın üstüne indiği yerde; alt başlık üst başlığın içinde biter, dereye uzayıp cumbanın
        # yüzünden taşmaz (geometri hakemi, İE-15 K6; rehberde de uçlar derenin üstünde biter). Sayı ve yer listeyle (D-47); boy gösterim
        uc = lambda a: a + (z_alt - 5 - zt(a)) * (um - a) / (zt(um) - zt(a)) if zt(um) - zt(a) > 1e-6 else a
        e0, e1 = (min(uc(u0), um - 10), max(uc(u1), um + 10)) if uclar is None else uclar
        uyeler = (("ALT_BASLIK", [(e0, z_alt), (e1, z_alt), (e1, z_alt + 5), (e0, z_alt + 5)]),
                  ("UST_1", [(e0, zt(e0)), (um, zt(um)), (um, zt(um) + 10), (e0, zt(e0) + 10)]),
                  ("UST_2", [(um, zt(um)), (e1, zt(e1)), (e1, zt(e1) + 10), (um, zt(um) + 10)]),
                  ("DIKME_ORTA", [(um - 3, z_alt + 5), (um + 3, z_alt + 5), (um + 3, zt(um)), (um - 3, zt(um))]))
        asm = self._urun("IfcElementAssembly", ad, predefined="TRUSS")
        self._yerlestir(asm)
        self._pset(asm, "PortatifEv_Kapsam", {"BOMKalem": kalem, **ozellik, "AnaCatininUstunde": True})
        uyeler_e = []
        for u_ad, k in uyeler:
            m = self._urun("IfcMember", f"{ad}_{u_ad}", predefined="CHORD" if "BASLIK" in u_ad or "UST" in u_ad else "MEMBER", kapsa=False)
            self._yerlestir(m)
            self._temsil(m, self._prizma_xz(k, konum - 2.5, konum + 2.5) if mahya_y else self._prizma_yz(k, konum - 2.5, konum + 2.5), "galv")
            uyeler_e.append(m)
        api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler_e)

    def veranda(self):
        v = self.G["veranda"]
        if not v or v.get("tip") == "bina_ici":      # bina içi (köşe) veranda: ana çatı örter; dikme/profil baglantilar'dan
            return
        G = self.G; H0 = G["bina"]["duvar_h"]; c = G["bina"]["cati"]; s, eg, top = c["sacak"], c["egim"], c["topuk"]
        x0 = v["poligon"][0][0]; x1 = v["poligon"][1][0]; yv = v["poligon"][0][1]; ust = v["poligon"][2][1]
        for i, (xa, xb) in enumerate(((x0, x0 + 10), (x1 - 10, x1))):
            col = self._urun("IfcColumn", f"VERANDA_DIKME_{i + 1}", predefined="COLUMN")
            self._yerlestir(col); self._temsil(col, self._prizma_xy([(xa, yv), (xb, yv), (xb, yv + 10), (xa, yv + 10)], 0, H0 - 10), "profil")
            self._pset(col, "PortatifEv_Kapsam", {"BOMKalem": "Veranda dikmesi 100×100 flanşlı kutu profil", "Boy_cm": H0 - 10})
        for ad, (ax0, ay0, ax1, ay1) in (("ON", (x0, yv, x1, yv + 10)), ("ALIN_Y0", (x0, 0, x1 - 10, 10)),
                                          ("YAN_SAG", (x1 - 10, yv + 10, x1, ust)), ("YAN_SOL", (x0, yv + 10, x0 + 10, 0))):
            b = self._urun("IfcBeam", f"VERANDA_KIRIS_{ad}", predefined="BEAM")
            self._yerlestir(b); self._temsil(b, self._prizma_xy([(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)], H0 - 10, H0), "profil")
            self._pset(b, "PortatifEv_Kapsam", {"BOMKalem": "Veranda kirişi 100×100 kutu profil", "Boy_cm": round(max(ax1 - ax0, ay1 - ay0), 1)})
        xm = (x0 + x1) / 2; zs = H0 + top; zm = zs + (xm - x0 + s) * eg; t = 4.0
        roof = self._urun("IfcRoof", "VERANDA_CATISI", predefined="GABLE_ROOF")
        self._yerlestir(roof)
        parcalar = []
        for ad, k in (("VERANDA_CATI_SOL", [(x0 - s, zs + 10), (xm, zm + 10), (xm, zm + 10 + t), (x0 - s, zs + 10 + t)]),
                      ("VERANDA_CATI_SAG", [(xm, zm + 10), (x1 + s, zs + 10), (x1 + s, zs + 10 + t), (xm, zm + 10 + t)])):
            sl = self._urun("IfcSlab", ad, predefined="ROOF", kapsa=False)
            self._yerlestir(sl); self._temsil(sl, self._prizma_xz(k, yv - s, -s), "sac")
            self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": "Trapez çatı sacı (antrasit) — veranda beşiği"})
            parcalar.append(sl)
        api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
        self._pset(roof, "PortatifEv_Cati", {"Not": "Bayinin 27.08 ön görünüşüne göre ikinci (alçak) beşik — teyit edilecek", "Mahya_cm": round(zm, 1)})
        zt = lambda x: zs + (min(x - x0, x1 - x) + s) * eg
        pl = self._urun("IfcPlate", "VERANDA_ALIN", predefined="SHEET")
        self._yerlestir(pl)
        self._temsil(pl, self._prizma_xz([(x0, H0), (x1, H0), (x1, zt(x1)), (xm, zt(xm)), (x0, zt(x0))], yv, yv + 8), "fiber")
        self._pset(pl, "PortatifEv_Kapsam", {"BOMKalem": "Çatı alın dolgusu (üçgen) — kural teyit edilecek"})

    def dis_verandalar(self):
        """BK-14: gövdeden taşan verandanın zemini (kapsam dışı beton), çatısı ve kalkan alın dolgusu. Dikme ve kirişleri Motor DXF'inin BOM
        bloklarından `baglantilar`'da gelir. Çatı düzlemleri `veranda.cati`'den (bayi paftasının çatı planı ve görünüşüyle aynı); kesit ana
        çatınınki gibi duvar üstü + 10 cm'de, 4 cm sac."""
        H0 = self.G["bina"]["duvar_h"]; t = 4.0
        for i, v in enumerate(self.G.get("dis_verandalar", []), start=1):
            x0, y0, x1, y1 = v["rect"]; C = v["cati"]
            if C is not None:                                   # BK-46: çatısı ana çatının cumbası (PC-38) → çatı `cati`'de
                X0, Y0, X1, Y1 = C["kutu"]; zs, zm, eg, s = C["sacak_kotu"], C["mahya_kotu"], C["egim"], C["sacak"]
            sp = self._urun("IfcSpace", f"M-VERANDA-{i}", predefined="EXTERNAL", kapsa=False, LongName=v["ad"])
            api("aggregate.assign_object", self.f, relating_object=self.kat, products=[sp])
            taban = [tuple(q) for q in v.get("poligon") or [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]   # D-109: köşe boşluğuyla tek mahal
            self._yerlestir(sp); self._temsil(sp, self._prizma_xy(taban, 0, H0), "mahal")
            self._qto(sp, "Qto_SpaceBaseQuantities", {"NetFloorArea": v["net_m2"]})
            self._pset(sp, "PortatifEv_Mahal", {"CizimNetAlan_m2": v["net_m2"], "BayiEtiketAlan_m2": v["etiket_m2"] or 0.0,
                                                "BinaDisinaTasma_cm": round(y1 - y0 if v["cephe"] in ("on", "arka") else x1 - x0, 1)})
            z = self._urun("IfcSlab", f"VERANDA_ZEMINI_{i}", predefined="FLOOR")
            self._yerlestir(z); self._temsil(z, self._prizma_xy([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], -15, 0), "beton")
            self._pset(z, "PortatifEv_Kapsam", {"BOMKalem": f"{v['ad']} zemini — kapsam dışı (bayi/saha)", "KapsamDisi": True})
            if C is None:
                continue
            if C["tip"] == "teras_paneli":                      # D-52: teras paneli, 8 cm; üst yüzü duvarda duvar üstünün 10 altında, dışarı
                roof = self._urun("IfcRoof", f"VERANDA_CATISI_{i}", predefined="SHED_ROOF")   # eğimle iner (D-52 ek; `veranda.teras_paneli`)
                self._yerlestir(roof)
                self._pset(roof, "PortatifEv_Cati", {"Veranda": v["ad"], "Egim_yuzde": round(eg * 100, 2), "Sacak_cm": 0.0,
                                                     "Ust_kotu_cm": round(zm, 1), "Dis_ust_kotu_cm": round(zs, 1), "Kalinlik_cm": C["kalinlik"]})
                sl = self._urun("IfcSlab", f"VERANDA_CATI_{i}_1", predefined="ROOF", kapsa=False)
                self._yerlestir(sl); self._temsil(sl, self._teras_kesiti(v["cephe"], (X0, Y0, X1, Y1), zm - C["kalinlik"], zs - C["kalinlik"],
                                                                         C["kalinlik"]), "sac")
                self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": f"Teras paneli (C profilden panel, üstü trapez sac) — {v['ad']}"})
                api("aggregate.assign_object", self.f, relating_object=roof, products=[sl])
                continue
            roof = self._urun("IfcRoof", f"VERANDA_CATISI_{i}", predefined="GABLE_ROOF" if C["tip"] == "besik" else "SHED_ROOF")
            self._yerlestir(roof)
            self._pset(roof, "PortatifEv_Cati", {"Veranda": v["ad"], "Egim_yuzde": round(eg * 100, 2), "Sacak_cm": s, "Mahya_cm": round(zm, 1)})
            boyuna = v["cephe"] in ("on", "arka")              # mahya y boyunca: kesit x–z düzleminde
            parcalar = []
            for j, dz in enumerate(C["duzlemler"]):
                xs = [p[0] for p in dz["plan"]]; ys = [p[1] for p in dz["plan"]]
                ux, uy = dz["yukari"]
                if ux:                                          # eğim x boyunca
                    a0, a1 = (min(xs), max(xs)) if ux > 0 else (max(xs), min(xs))
                    k = [(a0, zs + 10), (a1, zs + 10 + abs(a1 - a0) * eg), (a1, zs + 10 + abs(a1 - a0) * eg + t), (a0, zs + 10 + t)]
                    g = self._prizma_xz(k, min(ys), max(ys))
                else:                                           # eğim y boyunca
                    a0, a1 = (min(ys), max(ys)) if uy > 0 else (max(ys), min(ys))
                    k = [(a0, zs + 10), (a1, zs + 10 + abs(a1 - a0) * eg), (a1, zs + 10 + abs(a1 - a0) * eg + t), (a0, zs + 10 + t)]
                    g = self._prizma_yz(k, min(xs), max(xs))
                sl = self._urun("IfcSlab", f"VERANDA_CATI_{i}_{j + 1}", predefined="ROOF", kapsa=False)
                self._yerlestir(sl); self._temsil(sl, g, "sac")
                self._pset(sl, "PortatifEv_Kapsam", {"BOMKalem": f"Trapez çatı sacı (antrasit) — {v['ad']}"})
                parcalar.append(sl)
            api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
            if C["tip"] == "besik":                             # dış kenardaki kalkan: kirişin üstünden mahyaya üçgen dolgu
                if boyuna:
                    xm = (x0 + x1) / 2; zt = lambda x: zs + (min(x - x0, x1 - x) + s) * eg
                    ya = y0 if v["cephe"] == "on" else y1 - 8
                    g = self._prizma_xz([(x0, H0), (x1, H0), (x1, zt(x1)), (xm, zt(xm)), (x0, zt(x0))], ya, ya + 8)
                else:
                    ym = (y0 + y1) / 2; zt = lambda y: zs + (min(y - y0, y1 - y) + s) * eg
                    xa = x0 if v["cephe"] == "sol" else x1 - 8
                    g = self._prizma_yz([(y0, H0), (y1, H0), (y1, zt(y1)), (ym, zt(ym)), (y0, zt(y0))], xa, xa + 8)
                pl = self._urun("IfcPlate", f"VERANDA_ALIN_{i}", predefined="SHEET")
                self._yerlestir(pl); self._temsil(pl, g, "fiber")
                self._pset(pl, "PortatifEv_Kapsam", {"BOMKalem": "Çatı alın dolgusu (üçgen) — kural teyit edilecek"})

    def baglantilar(self):
        """Köşe / üçlü H / veranda dikmesi / veranda profili (Motor DXF BOM bloklarının plan kutusu).
        Bağlantı ve dikmelerde 250 cm yalnız 3B gösterimdir (kesim boyu değil). Veranda profili: kot varsayım (duvar üstü 10 cm bant)."""
        H0 = self.G["bina"]["duvar_h"]
        mc = (self.G.get("cati_serit") or {}).get("mahal_catilari", [])          # İE-17 PR-2: kendi çatısı olan mahalde dikme kendi kotuna (serbest
        kolon_ust = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, r[4]) for m in mc for r in m["kolonlar"]]   # dikme kirişin altına), profil çatının altına

        def profil_ust(x0, y0, x1, y1):
            from .veranda import kot
            for m in (m for m in mc if m["tip"] != "kirma"):     # köşe kırmasında makas kirişe oturur: profil duvar üstünün 10 altından (BK-14)
                kx0, ky0, kx1, ky1 = m["kutu"]
                if kx0 - 0.5 <= x0 and x1 <= kx1 + 0.5 and ky0 - 0.5 <= y0 and y1 <= ky1 + 0.5:
                    return min(kot(m["duzlem"], x, y) for x in (x0, x1) for y in (y0, y1))
            return H0

        teras = [v for v in (self.G.get("dis_verandalar") or []) if (v["cati"] or {}).get("tip") == "teras_paneli"]   # D-52: kiriş panelin altında,
                                                                                                          # dikme dış kirişin altına
        def teras_verandasi(x0, y0, x1, y1):
            return next((v for v in teras for rx0, ry0, rx1, ry1 in [v["rect"]]
                         if rx0 - 0.5 <= x0 and x1 <= rx1 + 0.5 and ry0 - 0.5 <= y0 and y1 <= ry1 + 0.5), None)

        def egik(rect):                                          # açık yandaki eğik kiriş (geometri hakemi, 1 Kasım): çatının altında, eğimle
            return next((m for m in mc for r in m.get("egik_kirisler", []) if all(abs(a - b) < 0.5 for a, b in zip(r, rect))), None)
        for i, b in enumerate(self.G.get("baglantilar", [])):
            x0, y0, x1, y1 = b["rect"]
            ayak = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            if b["tur"] == "dikme":
                e = self._urun("IfcColumn", f"DIKME_{b['kod']}_{i:02d}", predefined="COLUMN")
                z1 = next((z for cx, cy, z in kolon_ust if abs(cx - (x0 + x1) / 2) < 1 and abs(cy - (y0 + y1) / 2) < 1), H0)
                if teras_verandasi(x0, y0, x1, y1) is not None:
                    z1 = teras_verandasi(x0, y0, x1, y1)["cati"]["kolon_ustu"]
                z0, z1, malz = 0.0, z1, "profil"
            elif b["tur"] == "veranda_profil" and egik(b["rect"]):
                m = egik(b["rect"]); d = m["duzlem"]
                from .cati_serit import kiris_kotu
                e = self._urun("IfcBeam", f"VERANDA_PROFIL_{b['kod']}_{i:02d}", predefined="BEAM")
                kotlar = [z for x, y in ayak for z in kiris_kotu(m, x, y)]
                self._yerlestir(e)               # altı çatının 10 altında; kalınlık yüzün normali boyunca (düşeyde 10)
                self._temsil(e, self._egik_levha(ayak, (d["sacak"].get("x", 0.0), d["sacak"].get("y", 0.0)), d["yukari"], d["egim"],
                                                  d["sacak_kotu"] - 10, 10 / math.hypot(1.0, d["egim"])), "profil")
                self._pset(e, "PortatifEv_Kapsam", {"BOMKalem": b["kalem"], "BOMKod": b["kod"], "Blok": b.get("blok", ""),
                                                    "Kot_cm": f"{min(kotlar):.0f}–{max(kotlar):.0f}", "KesimBoyuTanimli": False,
                                                    "Not": "Kot varsayım (profil kotu kaynakta tanımlı değil); çatının eğimiyle"})
                continue
            elif b["tur"] == "veranda_profil":
                e = self._urun("IfcBeam", f"VERANDA_PROFIL_{b['kod']}_{i:02d}", predefined="BEAM")
                z1 = profil_ust(x0, y0, x1, y1)
                tv = teras_verandasi(x0, y0, x1, y1)
                if tv is not None:                               # D-52 ek, D-56: yalnız dış kiriş, düz, panelin altında
                    z1 = tv["cati"]["dis_kiris_ustu"]
                z0, z1, malz = z1 - 10, z1, "profil"
            else:
                e = self._urun("IfcMember", f"BAGLANTI_{b['kod']}_{i:02d}", predefined="STUD")
                z0, z1, malz = 0.0, H0, "galv"
            self._yerlestir(e)
            self._temsil(e, self._prizma_xy(ayak, z0, z1), malz)
            self._pset(e, "PortatifEv_Kapsam", {"BOMKalem": b["kalem"], "BOMKod": b["kod"], "Blok": b.get("blok", ""),
                                                "Kot_cm": f"{z0:.0f}–{z1:.0f}", "KesimBoyuTanimli": False,
                                                "Not": "Kot varsayım (profil kotu kaynakta tanımlı değil)" if b["tur"] == "veranda_profil"
                                                       else f"{H0:.0f} cm yalnız 3B gösterim; kesim boyu değil",
                                                **({"Kaynak": b["kaynak"]} if b.get("kaynak") else {})})     # BK-50

    def pano_ekleri(self):
        """İE-12: pano eki H profilleri (IfcMember, STUD; galvaniz). Görünen genişlik 5 cm, eke ortalı; yalnız sunum (hazirla'da varsa)."""
        H0 = self.G["bina"]["duvar_h"]
        for i, b in enumerate(self.G.get("pano_ekleri", [])):
            x0, y0, x1, y1 = b["rect"]
            eki = b.get("cins", "pano_eki") == "pano_eki"
            e = self._urun("IfcMember", f"H_{'PANO_EKI' if eki else 'UCLU'}_{'DIS' if b['duvar'] == 'dis' else 'IC'}_{i:03d}", predefined="STUD")
            self._yerlestir(e)
            self._temsil(e, self._prizma_xy([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0, H0), "galv")
            self._pset(e, "PortatifEv_Kapsam", {"BOMKalem": "H birleştirme profili (pano eki)" if eki else "Üçlü H bağlantısı: yüz görünümü (BOM satırı bağlantılarda)",
                                                "KesimBoyuTanimli": False,
                                                "Not": f"Görünen 5 cm, eke ortalı (Lokman 13.10.2026); {H0:.0f} cm yalnız 3B gösterim"})

    def calistir(self, yol: Path):
        self.panolar(); self.baglantilar(); self.pano_ekleri(); self.mahaller(); self.doseme(); self.cati(); self.veranda()
        if self.G.get("kubbeler"):
            self.kubbeler()
        if self.G.get("dis_verandalar"):
            self.dis_verandalar()
        self.f.write(str(yol))
        return yol


# ----------------------------------------------------------------------------- IFC'den BOM (bağımsız sayım)
def ifc_bom(yol: Path):
    import ifcopenshell.util.element as ue
    from collections import Counter, defaultdict
    f = ifcopenshell.open(str(yol))
    say = Counter(); boy = defaultdict(float); kod_say = Counter(); gecis = 0
    for e in f.by_type("IfcProduct"):
        ps = ue.get_psets(e)
        k = None; b = None
        for ad in ("PortatifEv_Pano", "PortatifEv_Dograma", "PortatifEv_Kapsam"):
            if ad in ps and "BOMKalem" in ps[ad]:
                k = ps[ad]["BOMKalem"]; b = ps[ad].get("Boy_cm")
                if ps[ad].get("BOMKod"):
                    kod_say[ps[ad]["BOMKod"]] += 1
        if e.is_a("IfcOpeningElement"):
            dolu = bool(e.HasFillings)
            pb = ps.get("PortatifEv_Bosluk", {})
            if not dolu and pb.get("Tur") in ("kapi", "ic_kapi"):
                k = "İç kapı boşluğu 80×200 (kapı kapsam dışı — bayi)"
            if not dolu and pb.get("Tur") == "gecis":
                gecis += 1
        if k:
            say[k] += 1
            if b and "kutu profil" in k:
                boy[k] += b
    # aynı iç kapı boşluğu iki panoda kesilmez (her boşluk tek panoda); sayım doğrudan
    qto_dis = sum(ue.get_psets(w)["Qto_WallBaseQuantities"]["Length"] for w in f.by_type("IfcWall") if ue.get_psets(w)["Pset_WallCommon"]["IsExternal"]
                  and ue.get_psets(w)["PortatifEv_Pano"]["PanoSinifi"] != "kose")
    qto_ic = sum(ue.get_psets(w)["Qto_WallBaseQuantities"]["Length"] for w in f.by_type("IfcWall") if not ue.get_psets(w)["Pset_WallCommon"]["IsExternal"]
                 and ue.get_psets(w)["PortatifEv_Pano"]["PanoSinifi"] != "kose")
    net_alan = sum(ue.get_psets(w)["Qto_WallBaseQuantities"]["NetSideArea"] for w in f.by_type("IfcWall"))
    ifc_bom.kod_say = kod_say; ifc_bom.gecis = gecis
    return say, boy, {"dis_duvar_m": round(qto_dis, 2), "ic_duvar_m": round(qto_ic, 2), "pano_net_yuzey_m2": round(net_alan, 2)}


def uret(ie: dict, yol: Path, baslik: str | None = None) -> dict:
    """İş Emri → IFC dosyası. Dönen özet: sınıf sayıları ve şema hatası sayısı (0 beklenir)."""
    girdi = hazirla(ie)
    u = IfcUretici(girdi, baslik or f"Portman — {ie.get('is_emri_no', '')} r{int(ie.get('revizyon') or 1):02d}")
    yol = Path(yol); yol.parent.mkdir(parents=True, exist_ok=True)
    u.calistir(yol)
    return ozet(yol) | {"cati": getattr(u, "cati_ozet", None)} | ({"kubbe": u.kubbe_ozet} if getattr(u, "kubbe_ozet", None) else {})


def ozet(yol: Path) -> dict:
    import ifcopenshell.validate
    f = ifcopenshell.open(str(yol))
    kayit = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, kayit)
    hata = sum(1 for s in kayit.statements if str(s.get("level")).lower() == "error")
    return {"duvar": len(f.by_type("IfcWall")), "pencere": len(f.by_type("IfcWindow")), "kapi": len(f.by_type("IfcDoor")),
            "mahal": len(f.by_type("IfcSpace")), "bosluk": len(f.by_type("IfcOpeningElement")), "sema_hatasi": hata}
