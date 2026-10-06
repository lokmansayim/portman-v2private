#!/usr/bin/env python3
"""Yapı Tanımı 0.5'ten IFC4 yapı modeli. Yalnız IfcOpenShell; Blender gerekmez.

Model düzeni (23 Eylül denemesindeki `ifc_uret.py` ile aynı yaklaşım):
  IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey "Zemin Kat"
  Duvar panelleri : IfcWall (karkas + kaplamalar tek gövde); Pset_WallCommon + PortatifEv_Duvar + Qto_WallBaseQuantities
  Boşluklar       : IfcOpeningElement → IfcWindow / IfcDoor (kapısız geçit boş kalır); PortatifEv_Dograma (kapsam: listede / alıcıya ait)
  Mahaller        : IfcSpace (kaplanmış yüzler arası) + Qto_SpaceBaseQuantities; tavan: IfcCovering CEILING
  Döşeme          : IfcSlab BASESLAB (kapsam dışı)
  Çatı            : IfcRoof → her düzlem IfcSlab ROOF (kaplama); serbest kenarlarda alın bandı IfcPlate; kalkanlar IfcPlate
  Makaslar        : IfcElementAssembly TRUSS → IfcMember (sadeleştirilmiş: alt başlık, üst başlıklar, dikmeler)
  Veranda         : IfcColumn (dikme), IfcBeam (kiriş), korkuluk duvarları IfcWall; baca IfcChimney
Birim: metre (tanım cm).

Kullanım:
    python ifc_genel.py tanim.json cikti.ifc
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import numpy as np
from ifcopenshell.util.shape_builder import ShapeBuilder
from shapely.geometry import Polygon

import cati_genel
import yapi

BURADA = Path(__file__).resolve().parent
CM = 0.01
api = ifcopenshell.api.run
RENKLER = {
    "cephe": ("Boardex (dış kaplama)", (0.86, 0.84, 0.79), "gypsum"), "ic": ("Alçıpan (iç kaplama)", (0.93, 0.92, 0.89), "gypsum"),
    "korkuluk": ("Korkuluk duvarı (Boardex)", (0.80, 0.78, 0.73), "gypsum"), "pvc": ("PVC doğrama", (0.95, 0.95, 0.94), "plastic"),
    "cam": ("Isıcam", (0.62, 0.80, 0.93), "glass"), "kapi_dis": ("Dış kapı", (0.42, 0.29, 0.18), "steel"), "kapi_ic": ("Melamin iç kapı", (0.90, 0.86, 0.78), "wood"),
    "cati": ("Sandviç panel (antrasit)", (0.27, 0.29, 0.33), "steel"), "alin": ("Alın ve saçak sacı (antrasit)", (0.20, 0.22, 0.25), "steel"),
    "galv": ("Galvaniz karkas", (0.72, 0.74, 0.77), "steel"), "beton": ("Zemin betonu (kapsam dışı)", (0.62, 0.62, 0.60), "concrete"),
    "mahal": ("Mahal hacmi", (0.80, 0.86, 0.95), "space"), "tavan": ("Tavan alçıpanı", (0.95, 0.95, 0.93), "gypsum"),
}


def _m(v):
    return float(v) * CM


class Uretici:
    def __init__(self, tanim: dict, kur: dict, baslik: str):
        self.t = tanim
        self.y = yapi.kur(tanim)
        self.c = cati_genel.cati_kur(tanim["cati"], kur)
        f = self.f = ifcopenshell.file(schema="IFC4")
        self.proje = api("root.create_entity", f, ifc_class="IfcProject", name=baslik)
        api("unit.assign_unit", f, length={"is_metric": True, "raw": "METERS"}, area={"is_metric": True, "raw": "SQUARE_METERS"},
            volume={"is_metric": True, "raw": "CUBIC_METERS"})
        model = api("context.add_context", f, context_type="Model")
        self.body = api("context.add_context", f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)
        self.site = api("root.create_entity", f, ifc_class="IfcSite", name="Parsel")
        self.bina = api("root.create_entity", f, ifc_class="IfcBuilding", name=tanim["ad"])
        self.kat = api("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Zemin Kat")
        api("aggregate.assign_object", f, relating_object=self.proje, products=[self.site])
        api("aggregate.assign_object", f, relating_object=self.site, products=[self.bina])
        api("aggregate.assign_object", f, relating_object=self.bina, products=[self.kat])
        for e in (self.site, self.bina, self.kat):
            api("geometry.edit_object_placement", f, product=e)
        self.sb = ShapeBuilder(f)
        self.stil, self.malz = {}, {}
        for k, (ad, rgb, kat) in RENKLER.items():
            m = api("material.add_material", f, name=ad, category=kat)
            s = api("style.add_style", f, name=ad)
            api("style.add_surface_style", f, style=s, ifc_class="IfcSurfaceStyleShading",
                attributes={"SurfaceColour": {"Name": None, "Red": rgb[0], "Green": rgb[1], "Blue": rgb[2]}, "Transparency": 0.85 if k == "mahal" else (0.5 if k == "cam" else 0.0)})
            api("style.assign_material_style", f, material=m, style=s, context=self.body)
            self.malz[k], self.stil[k] = m, s
        self.say: dict[str, int] = {}

    # ── yardımcılar ─────────────────────────────────────────────────────────
    def urun(self, sinif, ad, predefined=None, kapsa=True, **kw):
        e = api("root.create_entity", self.f, ifc_class=sinif, name=ad, predefined_type=predefined) if predefined else api("root.create_entity", self.f, ifc_class=sinif, name=ad)
        for k, v in kw.items():
            setattr(e, k, v)
        if kapsa:
            api("spatial.assign_container", self.f, relating_structure=self.kat, products=[e])
        api("geometry.edit_object_placement", self.f, product=e)
        self.say[sinif] = self.say.get(sinif, 0) + 1
        return e

    def temsil(self, urun, ogeler, malz=None, stiller=None):
        ogeler = ogeler if isinstance(ogeler, list) else [ogeler]
        rep = self.sb.get_representation(self.body, ogeler)
        api("geometry.assign_representation", self.f, product=urun, representation=rep)
        if stiller:
            for oge, anahtar in zip(ogeler, stiller):
                api("style.assign_item_style", self.f, item=oge, style=self.stil[anahtar])
        elif malz:
            api("style.assign_representation_styles", self.f, shape_representation=rep, styles=[self.stil[malz]])
            api("material.assign_material", self.f, products=[urun], material=self.malz[malz])
        return rep

    def pset(self, urun, ad, ozellik):
        ps = api("pset.add_pset", self.f, product=urun, name=ad)
        api("pset.edit_pset", self.f, pset=ps, properties=ozellik)

    def qto(self, urun, ad, ozellik):
        q = api("pset.add_qto", self.f, product=urun, name=ad)
        api("pset.edit_qto", self.f, qto=q, properties=ozellik)

    def kutu(self, x0, y0, z0, x1, y1, z1):
        prof = self.sb.profile(self.sb.rectangle(size=np.array([_m(x1 - x0), _m(y1 - y0)])))
        return self.sb.extrude(prof, magnitude=_m(z1 - z0), position=np.array([_m(x0), _m(y0), _m(z0)]))

    def prizma_xy(self, pts, z0, z1):
        prof = self.sb.profile(self.sb.polyline([np.array([_m(x), _m(y)]) for x, y in pts], closed=True))
        return self.sb.extrude(prof, magnitude=_m(z1 - z0), position=np.array([0.0, 0.0, _m(z0)]))

    def prizma_dusey(self, eksen, a, b, pts_sz):
        """Düşey düzlemde (s, z) çokgen; eksen 'x' ise s = x ve gövde y: a..b arasında; 'y' ise s = y ve gövde x: a..b arasında."""
        a, b = min(a, b), max(a, b)
        if eksen == "x":            # kesit x–z düzleminde, y boyunca
            prof = self.sb.profile(self.sb.polyline([np.array([_m(s), _m(z)]) for s, z in pts_sz], closed=True))
            return self.sb.extrude(prof, magnitude=_m(b - a), position=np.array([0.0, _m(b), 0.0]),
                                   position_z_axis=np.array([0.0, -1.0, 0.0]), position_x_axis=np.array([1.0, 0.0, 0.0]))
        prof = self.sb.profile(self.sb.polyline([np.array([_m(s), _m(z)]) for s, z in pts_sz], closed=True))
        return self.sb.extrude(prof, magnitude=_m(b - a), position=np.array([_m(a), 0.0, 0.0]),
                               position_z_axis=np.array([1.0, 0.0, 0.0]), position_x_axis=np.array([0.0, 1.0, 0.0]))

    def levha(self, ust3, kalinlik):
        """Eğik levha: üst çokgen (3B) ve düşeyde `kalinlik` kadar aşağısı; kapalı çokyüzlü."""
        n = len(ust3)
        pts = [(_m(x), _m(y), _m(z)) for x, y, z in ust3] + [(_m(x), _m(y), _m(z - kalinlik)) for x, y, z in ust3]
        yuz = [list(range(n)), list(range(2 * n - 1, n - 1, -1))] + [[i, n + i, n + (i + 1) % n, (i + 1) % n] for i in range(n)]
        return self.sb.polygonal_face_set([np.array(p) for p in pts], yuz)

    # ── duvarlar ────────────────────────────────────────────────────────────
    def duvarlar(self):
        y, t = self.y, self.t
        kap = t["yuz_kaplamalari"]
        self.govde = {}
        for d in y["duvarlar"]:
            x0, y0, x1, y1 = d["kutu"]
            pay = {kn: max((kap[f["kaplama"]]["kalinlik"] for f in y["yuzler"] if f["duvar"] == d["ad"] and f["kenar"] == kn), default=0.0) for kn in yapi.KENARLAR}
            gx0, gy0, gx1, gy1 = x0 - pay["sol"], y0 - pay["alt"], x1 + pay["sag"], y1 + pay["ust"]
            self.govde[d["ad"]] = (gx0, gy0, gx1, gy1)
            sinif = d["sinif"]
            h = d["yukseklik"]
            if sinif == "kolon":
                e = self.urun("IfcColumn", d["ad"], "COLUMN")
                self.temsil(e, self.kutu(gx0, gy0, 0, gx1, gy1, h), "cephe")
                self.pset(e, "PortatifEv_Karkas", {"Panel": d["ad"], "Sinif": "veranda dikmesi", "Profil": t["duvar_siniflari"][sinif]["profil"], "Boy_cm": float(h)})
                continue
            if sinif == "baca":
                e = self.urun("IfcChimney", d["ad"])
                self.temsil(e, self.kutu(gx0 if pay["sol"] else x0 - 1.25, gy0 if pay["alt"] else y0 - 1.25, 0, gx1, gy1, d.get("ust_kot", h)), "cephe")
                self.pset(e, "PortatifEv_Karkas", {"Panel": d["ad"], "Sinif": "baca", "UstKot_cm": float(d.get("ust_kot", h)), "Not": d.get("not", "")})
                continue
            dis = sinif in ("dis", "ek", "korkuluk")
            e = self.urun("IfcWall", d["ad"], "PARAPET" if sinif == "korkuluk" and not isinstance(h, dict) and h < 150 else ("SOLIDWALL" if dis else "PARTITIONING"))
            if isinstance(h, dict):                           # üst kotu eğimli duvar
                if d["yon"] == "x":
                    geo = self.prizma_dusey("x", gy0, gy1, [(gx0, 0), (gx1, 0), (gx1, h["son"]), (gx0, h["bas"])])
                else:
                    geo = self.prizma_dusey("y", gx0, gx1, [(gy0, 0), (gy1, 0), (gy1, h["son"]), (gy0, h["bas"])])
                hort = (h["bas"] + h["son"]) / 2
            else:
                geo = self.kutu(gx0, gy0, 0, gx1, gy1, h)
                hort = h
            self.temsil(e, geo, "korkuluk" if sinif == "korkuluk" else ("cephe" if dis else "ic"))
            bos = sum(a["alan_m2"] for a in y["acikliklar"] if a["duvar"] == d["ad"])
            self.pset(e, "Pset_WallCommon", {"IsExternal": dis, "Reference": t["duvar_siniflari"][sinif]["ad"]})
            self.pset(e, "PortatifEv_Duvar", {"Panel": d["ad"], "Sinif": t["duvar_siniflari"][sinif]["ad"], "Profil": t["duvar_siniflari"][sinif]["profil"],
                                               "KarkasBoyu_cm": float(d["boy"]), "KarkasKalinligi_cm": float(d["kalinlik"]), "Yukseklik_cm": float(hort),
                                               "Yalitim": bool(t["duvar_siniflari"][sinif].get("yalitim")), "Not": d.get("not", "")})
            brut = d["boy"] * hort / 1e4
            self.qto(e, "Qto_WallBaseQuantities", {"Length": _m(d["boy"]), "Width": _m(gx1 - gx0 if d["yon"] == "y" else gy1 - gy0), "Height": _m(hort),
                                                   "GrossSideArea": round(brut, 4), "NetSideArea": round(brut - bos, 4)})
            # boşluklar ve doğramalar
            for a in y["acikliklar"]:
                if a["duvar"] != d["ad"]:
                    continue
                o = self.urun("IfcOpeningElement", f"BOSLUK_{a['ad']}", "OPENING", kapsa=False)
                if d["yon"] == "x":
                    kb = (a["a0"], gy0 - 2, a["z0"], a["a1"], gy1 + 2, a["z1"])
                else:
                    kb = (gx0 - 2, a["a0"], a["z0"], gx1 + 2, a["a1"], a["z1"])
                self.temsil(o, self.kutu(*kb))
                api("feature.add_feature", self.f, feature=o, element=e)
                dolgu = self.dograma(a, d, (gx0, gy0, gx1, gy1))
                if dolgu is not None:
                    api("feature.add_filling", self.f, opening=o, element=dolgu)

    def dograma(self, a, d, g):
        gx0, gy0, gx1, gy1 = g
        t = self.t
        kapsam = t.get("kapsam", {})
        orta = ((gy0 + gy1) / 2) if d["yon"] == "x" else ((gx0 + gx1) / 2)

        def k(s0, s1, d0, d1, z0, z1):                        # duvar boyunca s, kalınlık yönünde orta ± d
            return self.kutu(s0, orta + d0, z0, s1, orta + d1, z1) if d["yon"] == "x" else self.kutu(orta + d0, s0, z0, orta + d1, s1, z1)

        a0, a1, z0, z1 = a["a0"], a["a1"], a["z0"], a["z1"]
        if a["tur"] == "pencere":
            fr = 6.0
            e = self.urun("IfcWindow", f"PENCERE_{a.get('etiket', '')}_{a['ad']}", "WINDOW", OverallWidth=_m(a1 - a0), OverallHeight=_m(z1 - z0))
            kasa = [k(a0, a1, -3.5, 3.5, z0, z0 + fr), k(a0, a1, -3.5, 3.5, z1 - fr, z1), k(a0, a0 + fr, -3.5, 3.5, z0 + fr, z1 - fr), k(a1 - fr, a1, -3.5, 3.5, z0 + fr, z1 - fr)]
            if a1 - a0 >= 100:
                m = (a0 + a1) / 2
                kasa.append(k(m - 3, m + 3, -3.5, 3.5, z0 + fr, z1 - fr))
            cam = k(a0 + fr, a1 - fr, -0.6, 0.6, z0 + fr, z1 - fr)
            self.temsil(e, kasa + [cam], stiller=["pvc"] * len(kasa) + ["cam"])
            self.pset(e, "Pset_WindowCommon", {"IsExternal": True})
            self.pset(e, "PortatifEv_Dograma", {"Olcu": a.get("etiket", f"{a['en']}/{a['yuk']}"), "Esik_cm": float(z0), "Kapsam": "listede" if kapsam.get("pencere", True) else "alıcıya ait"})
            return e
        if a["tur"] == "gecit":
            return None
        ic = a["tur"] == "ic_kapi"
        e = self.urun("IfcDoor", f"KAPI_{'IC' if ic else 'DIS'}_{a['ad']}", "DOOR", OverallWidth=_m(a1 - a0), OverallHeight=_m(z1 - z0))
        kasa = [k(a0, a0 + 5, -5, 5, 0, z1), k(a1 - 5, a1, -5, 5, 0, z1), k(a0 + 5, a1 - 5, -5, 5, z1 - 5, z1)]
        kanat = k(a0 + 5, a1 - 5, -2, 2, 0, z1 - 5)
        self.temsil(e, kasa + [kanat], stiller=["pvc"] * 3 + ["kapi_ic" if ic else "kapi_dis"])
        self.pset(e, "Pset_DoorCommon", {"IsExternal": not ic})
        self.pset(e, "PortatifEv_Dograma", {"Olcu": f"{a['en']} × {a['yuk']}", "Kapsam": "listede" if (ic or kapsam.get("dis_kapi", True)) else "alıcıya ait", "Not": a.get("not", "")})
        return e

    # ── kirişler, mahaller, döşeme ──────────────────────────────────────────
    def kirisler(self):
        kd = self.t["yuz_kaplamalari"]["dis"]["kalinlik"]
        for kr in self.t.get("kirisler", []):
            x0, y0, x1, y1 = kr["kutu"]
            dis = kr.get("bolge") == "veranda"
            p = kd if dis else self.t["yuz_kaplamalari"]["ic"]["kalinlik"]
            yatay = (x1 - x0) >= (y1 - y0)
            e = self.urun("IfcBeam", kr["ad"], "BEAM")
            g = (x0, y0 - p, x1, y1 + p) if yatay else (x0 - p, y0, x1 + p, y1)
            self.temsil(e, self.kutu(g[0], g[1], kr["alt"], g[2], g[3], kr["ust"]), "cephe" if dis else "ic")
            self.pset(e, "PortatifEv_Karkas", {"Panel": kr["ad"], "Sinif": "kiriş", "Boy_cm": float(max(x1 - x0, y1 - y0)), "Not": kr.get("not", "")})

    def mahaller(self):
        y, t = self.y, self.t
        for i, b in enumerate(b for b in y["bolgeler"].values() if b["sinif"] != "dis"):
            dis = b["sinif"] == "veranda"
            s = self.urun("IfcSpace", f"M{i + 1:02d}", "EXTERNAL" if dis else "INTERNAL", kapsa=False, LongName=b["ad"])
            api("aggregate.assign_object", self.f, relating_object=self.kat, products=[s])
            poligonlar = [b["net"]] if b["net"].geom_type == "Polygon" else list(b["net"].geoms)
            h = t["kat_yuksekligi"] if b["sinif"] != "ek" else min(yapi._yukseklik(d, d["_bas"]) for d in y["duvarlar"] if d["sinif"] == "ek")
            self.temsil(s, [self.prizma_xy(list(p.exterior.coords)[:-1], 0, h) for p in poligonlar], "mahal")
            self.qto(s, "Qto_SpaceBaseQuantities", {"NetFloorArea": round(b["alan_m2"], 3), "NetPerimeter": round(b["cevre_m"], 3), "Height": _m(h)})
            self.pset(s, "PortatifEv_Mahal", {"Islev": ", ".join(b.get("islev", [])), "Islak": bool(b.get("islak")), "KarkasYuzleriArasi_m2": round(b["ham_alan_m2"], 3),
                                              "CizimEtiketi_m2": float(b.get("etiket_m2") or 0.0), "IcKose": b["ic_kose"], "DisKose": b["dis_kose"]})
            if b["sinif"] != "ek":                          # tavan (ek yapıda çatı panelinin altı)
                tv = self.urun("IfcCovering", f"TAVAN_{b['ad']}", "CEILING")
                self.temsil(tv, [self.prizma_xy(list(p.exterior.coords)[:-1], h - 1.25, h) for p in poligonlar], "tavan")
                self.qto(tv, "Qto_CoveringBaseQuantities", {"NetArea": round(b["alan_m2"], 3)})

    def doseme(self):
        for i, h in enumerate(self.y["bolgeler"]["(dış)"]["net"].interiors):
            s = self.urun("IfcSlab", f"ZEMIN_BETONU_{i + 1}", "BASESLAB")
            self.temsil(s, self.prizma_xy(list(h.coords)[:-1], -15, 0), "beton")
            self.pset(s, "PortatifEv_Kapsam", {"KapsamDisi": True, "Not": "temel ve zemin betonu alıcıya / sahaya ait; yalnız gösterim"})

    # ── çatı ────────────────────────────────────────────────────────────────
    def cati(self):
        c, ct = self.c, self.t["cati"]
        roof = self.urun("IfcRoof", "CATI", "FREEFORM")
        self.pset(roof, "PortatifEv_Cati", {"Tip": ct["tip"], "Yontem": ct.get("yontem", ""), "Kaplama": ct.get("kaplama", ""), "Yuzey_m2": round(c["yuzey_m2"], 2),
                                            "Sacak_m": round(c["kenar_toplam_cm"].get("sacak", 0) / 100, 2), "Mahya_m": round(c["kenar_toplam_cm"].get("mahya", 0) / 100, 2),
                                            "Kirma_m": round(c["kenar_toplam_cm"].get("kirma", 0) / 100, 2), "Vadi_m": round(c["kenar_toplam_cm"].get("vadi", 0) / 100, 2),
                                            "Alin_m": round(c["kenar_toplam_cm"].get("alin", 0) / 100, 2)})
        parcalar = []
        for dz in c["duzlemler"]:
            ust = dz.get("ust_pay", ct.get("ust_pay", 7.0))
            alt = dz.get("alt_pay", ct.get("topuk", 10.0))
            ust3 = [(p[0], p[1], dz["kot"](p) + ust) for p in dz["plan"]]
            sl = self.urun("IfcSlab", f"CATI_{dz['ad']}", "ROOF", kapsa=False)
            self.temsil(sl, self.levha(ust3, 4.0), "cati")
            self.pset(sl, "PortatifEv_Cati", {"Duzlem": dz["ad"], "Egim_yuzde": round(dz["egim"] * 100, 2), "Yuzey_m2": round(dz["yuzey_m2"], 3), "Plan_m2": round(dz["plan_m2"], 3),
                                              "UstYapi": dz.get("ust_yapi", "makas + aşık")})
            self.qto(sl, "Qto_SlabBaseQuantities", {"GrossArea": round(dz["yuzey_m2"], 3)})
            parcalar.append(sl)
            for e in c["kenarlar"]:                          # serbest kenarlarda alın bandı
                if dz["ad"] != e["duzlemler"][0] or e["tur"] not in ("sacak", "alin"):
                    continue
                p, q = e["p"], e["q"]
                zp, zq = dz["kot"](p), dz["kot"](q)
                L = math.hypot(q[0] - p[0], q[1] - p[1])
                ic = dz["cokgen"].representative_point()
                nx, ny = -(q[1] - p[1]) / L, (q[0] - p[0]) / L
                if nx * (ic.x - p[0]) + ny * (ic.y - p[1]) < 0:
                    nx, ny = -nx, -ny                           # düzlemin içine doğru
                kal = 1.0
                u = [(p[0], p[1], zp + ust), (q[0], q[1], zq + ust), (q[0] + nx * kal, q[1] + ny * kal, zq + ust), (p[0] + nx * kal, p[1] + ny * kal, zp + ust)]
                # saçak ucunda bant aşağı, makas üstünden topuk kadar iner; kapalı gövde
                pl = self.urun("IfcPlate", f"ALIN_{dz['ad']}_{e['tur']}", "SHEET", kapsa=False)
                self.temsil(pl, self.levha(u, ust + alt), "alin")
                parcalar.append(pl)
        api("aggregate.assign_object", self.f, relating_object=roof, products=parcalar)
        # kalkanlar
        for k in c["kalkanlar"]:
            if len(k["kose"]) < 3:
                continue
            pol = Polygon(k["kose"]).simplify(0.05)
            pts = list(pol.exterior.coords)[:-1]
            ic_yon = {"kuzey": 1.0, "guney": -1.0, "dogu": 1.0, "bati": -1.0}[k["ic"]]
            a, b = k["konum"], k["konum"] + ic_yon * 3.0
            e = self.urun("IfcPlate", f"KALKAN_{k['ad']}", "SHEET")
            self.temsil(e, self.prizma_dusey("x" if k["eksen"] == "y" else "y", a, b, pts), "cephe")
            self.pset(e, "PortatifEv_Kapsam", {"Kalem": "kalkan (alın duvarı) kaplaması: Boardex", "Alan_m2": round(k["alan_m2"], 3)})

    def makaslar(self):
        ct = self.t["cati"]
        mk = ct.get("makaslar") or {}
        adli = {d["ad"]: d for d in self.c["duzlemler"]}
        duvar_ustu = ct.get("duvar_ustu", 270.0)
        bas = 8.0                                              # başlık yüksekliği (sırt 80 mm)

        def ekle(ad, eksen, a, kal, ust_cizgi):
            """ust_cizgi: [(s, z), ...] makasın üst yüzü; alt başlık duvar üstünde."""
            asm = self.urun("IfcElementAssembly", ad, "TRUSS")
            s0, s1 = ust_cizgi[0][0], ust_cizgi[-1][0]
            uyeler = []
            alt = [(s0, duvar_ustu), (s1, duvar_ustu), (s1, duvar_ustu + bas), (s0, duvar_ustu + bas)]
            m = self.urun("IfcMember", f"{ad}_ALT", "CHORD", kapsa=False)
            self.temsil(m, self.prizma_dusey(eksen, a, a + kal, alt), "galv")
            uyeler.append(m)
            for i, ((sa, za), (sb_, zb)) in enumerate(zip(ust_cizgi, ust_cizgi[1:])):
                m = self.urun("IfcMember", f"{ad}_UST{i + 1}", "CHORD", kapsa=False)
                self.temsil(m, self.prizma_dusey(eksen, a, a + kal, [(sa, za - bas), (sb_, zb - bas), (sb_, zb), (sa, za)]), "galv")
                uyeler.append(m)
            tepe = max(ust_cizgi, key=lambda p: p[1])
            for i, s in enumerate(sorted({tepe[0]} | {s0 + (s1 - s0) * k / 4 for k in (1, 2, 3)})):   # dikmeler
                z = np.interp(s, [p[0] for p in ust_cizgi], [p[1] for p in ust_cizgi]) - bas
                if z - (duvar_ustu + bas) < 5:
                    continue
                m = self.urun("IfcMember", f"{ad}_DIKME{i + 1}", "MEMBER", kapsa=False)
                self.temsil(m, self.prizma_dusey(eksen, a, a + kal, [(s - 2.25, duvar_ustu + bas), (s + 2.25, duvar_ustu + bas), (s + 2.25, z), (s - 2.25, z)]), "galv")
                uyeler.append(m)
            api("aggregate.assign_object", self.f, relating_object=asm, products=uyeler)

        no = 0
        if "tam" in mk:
            x0, x1 = mk["tam"]["x"]
            xm = next(e["p"][0] for e in self.c["kenarlar"] if e["tur"] == "mahya" and set(e["duzlemler"]) == {"batı", "doğu"})
            for yy in mk["tam"]["y"]:
                no += 1
                ekle(f"MAKAS_{no:02d}", "x", yy, mk["tam"]["kalinlik"], [(x0, adli["batı"]["kot"]((x0, yy))), (xm, adli["batı"]["kot"]((xm, yy))), (x1, adli["doğu"]["kot"]((x1, yy)))])
        if "cumba" in mk:
            x0, x1 = mk["cumba"]["x"]
            xc = next(e["p"][0] for e in self.c["kenarlar"] if e["tur"] == "mahya" and "cumba doğu" in e["duzlemler"])
            for yy in mk["cumba"]["y"]:
                no += 1
                ekle(f"MAKAS_{no:02d}", "x", yy, mk["cumba"]["kalinlik"], [(x0, adli["batı"]["kot"]((x0, yy))), (xc, adli["batı"]["kot"]((xc, yy))), (x1, adli["cumba doğu"]["kot"]((x1, yy)))])
        if "veranda" in mk:
            y0, y1 = mk["veranda"]["y"]
            for xx in mk["veranda"]["x"]:
                no += 1
                ekle(f"MAKAS_{no:02d}", "y", xx, mk["veranda"]["kalinlik"], [(y0, adli["veranda"]["kot"]((xx, y0))), (y1, adli["veranda"]["kot"]((xx, y1)))])

    def calistir(self, yol: Path):
        self.duvarlar()
        self.kirisler()
        self.mahaller()
        self.doseme()
        self.cati()
        self.makaslar()
        self.f.write(str(yol))
        return yol


def dogrula(yol: Path) -> dict:
    import ifcopenshell.validate
    m = ifcopenshell.open(str(yol))
    kayit = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(m, kayit)
    from collections import Counter
    say = Counter(e.is_a() for e in m.by_type("IfcProduct"))
    return {"sema": m.schema, "sema_hatasi": len(kayit.statements), "urunler": dict(sorted(say.items())), "ilk_hatalar": [str(s.get("message", s))[:200] for s in kayit.statements[:5]]}


def main() -> int:
    tanim_yolu, cikti = Path(sys.argv[1]), Path(sys.argv[2])
    t = json.loads(tanim_yolu.read_text(encoding="utf-8"))
    kur = json.loads((BURADA.parent / "2026-10-03_yukleme" / "kurallar.json").read_text(encoding="utf-8"))
    u = Uretici(t, kur, f"Portman — {t['kod']} · {t['ad']}")
    cikti.parent.mkdir(parents=True, exist_ok=True)
    u.calistir(cikti)
    d = dogrula(cikti)
    cikti.with_suffix(".ozet.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(d, ensure_ascii=False))
    return 0 if d["sema_hatasi"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
