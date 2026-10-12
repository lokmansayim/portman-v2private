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
from .dxf_out import Cizici
from .katalog import Katalog

CM = 0.01
api = ifcopenshell.api.run
MOD = 125.5
DUVAR_H = 250.0
LENTO = 50.0
PENCERE_ESIK = {"120x120": 80.0, "120x180": 20.0, "60x40": 160.0}   # BOM notlarındaki eşik yükseklikleri (23.09)
KAPI_UST = DUVAR_H - LENTO                                            # 200: lento kuralı


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
    kat = Katalog()
    c = Cizici(plan, kat)
    c.ciz_plan(0.0, 0.0, "ANA", "", "")          # BOM kodlu INSERT'ler (yalnız ANA rolü)
    etiket = {"".join(k.split()): v for k, v in ie.get("altin_beklenti", {}).get("alanlar", {}).items()}

    def kalem(kod):
        m = kat.malzemeler.get(kod, {})
        return f"{kod} {m.get('label', '')}".strip()

    panolar, acikliklar = [], []
    for d in plan.duvarlar:
        for p in d.panolar:
            _, _, kod = c.pano_blok(p)
            x0, y0, x1, y1 = p.rect()
            L, t = p.boy, 2 * d.h
            pr = {"id": len(panolar), "rect": [_r(x0), _r(y0), _r(x1), _r(y1)], "yon": d.yon, "boy": _r(L), "kalinlik": _r(t),
                  "tur": d.tur, "sinif": pano_sinifi(L, t), "kod": kod, "kalem": kalem(kod), "acikliklar": []}
            ac = p.acilim
            if ac is not None:
                g = p.gap()
                a0, a1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
                if ac.tur == "pencere":
                    en, boy = G.PENCERE_OLCULERI[ac.olcu]
                    z0 = PENCERE_ESIK[ac.olcu]; z1 = min(z0 + boy, KAPI_UST)
                    dk = c.dograma[ac.olcu][1]
                    a = {"tur": "pencere", "olcu": ac.olcu}
                else:
                    z0, z1 = 0.0, KAPI_UST
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

    odalar, veranda = [], None
    for ad, m in plan.mahaller.items():
        poly = m.poly.simplify(0.0)
        pl = polylabel(poly, tolerance=1.0)
        kayit = {"ad": ad, "etiket_m2": etiket.get("".join(ad.split())), "net_m2": _r(m.alan_m2, 4), "etiket_xy": [_r(pl.x), _r(pl.y)],
                 "poligon": [[_r(x), _r(y)] for x, y in list(poly.exterior.coords)[:-1]]}
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
                 "W": _r(plan.W), "H": _r(plan.H), "duvar_h": float(ie["yapi"].get("duvar_yuksekligi_cm", DUVAR_H)), "lento": LENTO,
                 "cati": {"tip": cati.get("tip", "besik"), "egim": float(cati.get("egim_yuzde", 33)) / 100, "sacak": float(cati.get("sacak_cm", 30)),
                          "topuk": float(cati.get("topuk_cm", 10)), "makas_yonu": "x (kısa kenar)", **({"makas_ekseni": cati["makas_ekseni"]} if "makas_ekseni" in cati else {}), "renk": "antrasit"}},
        "panolar": panolar, "acikliklar": acikliklar, "baglantilar": baglantilar, "odalar": odalar, "veranda": veranda, "tefris": [],
        "kanit": {"motor_uyarilari": plan.uyarilar}, "uyari": [],
    }


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
            self._temsil(s, self._prizma_xy(o["poligon"], 0, H), "mahal")
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
        if v and v.get("tip") != "bina_ici":
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
        # makaslar
        n = math.ceil((Hd - 10) / 125.5) + 1
        for i in range(n):
            y = 5 + i * (Hd - 10) / (n - 1)
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
        self.cati_ozet = {"mahya_cm": round(zm, 1), "makas": n, "cati_alan_m2": round(alan, 2)}

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
        # makaslar pano akslarında: iki baş makas kalkan duvarların ekseninde, orta makaslar ön duvarın pano eklerinde
        # (P6001'in gerçek yükleme listesinde 6 pano boyunca 2 baş + 5 orta makas; çıkarım, teyit bekliyor)
        ekler = sorted({round(v, 3) for p in G["panolar"] if p["yon"] == "x" and p["tur"] == "dis" for v in (p["rect"][0], p["rect"][2])})
        xs = [td / 2] + [x for x in ekler if td + 1e-6 < x < Wd - td - 1e-6] + [Wd - td / 2]
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
        self.cati_ozet = {"mahya_cm": round(zm, 1), "makas": n, "cati_alan_m2": round(alan, 2), "makas_ekseni": "y", "aciklik_cm": round(Hd, 1), "makas_x_cm": [round(x, 2) for x in xs]}

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

    def baglantilar(self):
        """Köşe / üçlü H / veranda dikmesi / veranda profili (Motor DXF BOM bloklarının plan kutusu).
        Bağlantı ve dikmelerde 250 cm yalnız 3B gösterimdir (kesim boyu değil). Veranda profili: kot varsayım (duvar üstü 10 cm bant)."""
        H0 = self.G["bina"]["duvar_h"]
        for i, b in enumerate(self.G.get("baglantilar", [])):
            x0, y0, x1, y1 = b["rect"]
            ayak = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            if b["tur"] == "dikme":
                e = self._urun("IfcColumn", f"DIKME_{b['kod']}_{i:02d}", predefined="COLUMN")
                z0, z1, malz = 0.0, H0, "profil"
            elif b["tur"] == "veranda_profil":
                e = self._urun("IfcBeam", f"VERANDA_PROFIL_{b['kod']}_{i:02d}", predefined="BEAM")
                z0, z1, malz = H0 - 10, H0, "profil"
            else:
                e = self._urun("IfcMember", f"BAGLANTI_{b['kod']}_{i:02d}", predefined="STUD")
                z0, z1, malz = 0.0, H0, "galv"
            self._yerlestir(e)
            self._temsil(e, self._prizma_xy(ayak, z0, z1), malz)
            self._pset(e, "PortatifEv_Kapsam", {"BOMKalem": b["kalem"], "BOMKod": b["kod"], "Blok": b.get("blok", ""),
                                                "Kot_cm": f"{z0:.0f}–{z1:.0f}", "KesimBoyuTanimli": False,
                                                "Not": "Kot varsayım (profil kotu kaynakta tanımlı değil)" if b["tur"] == "veranda_profil"
                                                       else f"{H0:.0f} cm yalnız 3B gösterim; kesim boyu değil"})

    def calistir(self, yol: Path):
        self.panolar(); self.baglantilar(); self.mahaller(); self.doseme(); self.cati(); self.veranda()
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
    return ozet(yol) | {"cati": getattr(u, "cati_ozet", None)}


def ozet(yol: Path) -> dict:
    import ifcopenshell.validate
    f = ifcopenshell.open(str(yol))
    kayit = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, kayit)
    hata = sum(1 for s in kayit.statements if str(s.get("level")).lower() == "error")
    return {"duvar": len(f.by_type("IfcWall")), "pencere": len(f.by_type("IfcWindow")), "kapi": len(f.by_type("IfcDoor")),
            "mahal": len(f.by_type("IfcSpace")), "bosluk": len(f.by_type("IfcOpeningElement")), "sema_hatasi": hata}
