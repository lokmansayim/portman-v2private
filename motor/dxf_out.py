"""Portman motor v1.1 — DXF/PDF çıktısı (BOM bloklu).

Plan (geometry.kur) → düzenlenebilir DXF (ezdxf) → yeniden aç → doğrula → A2 PDF (PyMuPDF).
Blok düzeni Yan Verandalı 6×8,5 (v1.4.3) örneğiyle aynıdır:
  - Üst seviye malzeme blokları: BOM_<kod>_… ; INSERT üzerinde AI_BOM XData = [kod, ANA|KOPYA|MONTAJ]
  - Kapı/pencere doğramaları pano bloğu içinde ayrı BOM_P0x_/BOM_K0x_ INSERT'idir (ayrıca sayılır)
  - Montaj kopyası MNT_ önekli bloklarla; standart dışı panolar mor (renk 6) ve gerçek boy ölçülü
Kaynak doğrama blokları (Güncel Şablon 2024) onaylı referans DXF'ten aktarılır; ölçeklenmez.
"""
from __future__ import annotations
import json, time, hashlib, csv
from pathlib import Path

import ezdxf
from ezdxf import units
from ezdxf.addons import Importer
from ezdxf.enums import TextEntityAlignment
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, pymupdf
try:
    import pymupdf as fitz
except ImportError:  # eski PyMuPDF
    import fitz
from shapely.geometry import box

from . import geometry as G
from .katalog import Katalog

ROOT = Path(__file__).resolve().parent.parent


def _ref(ad: str) -> Path:
    """Referans dosyası (H bloğu kaynağı, bağlantı ölçüleri, yazı tipi). Aranan yerler sırayla: PORTMAN_REF_DIR ortam değişkeni,
    depo kökü, kökteki kanal/ (depo düzeni), motor/ dizini. Dağıtım paketinde kökte; depoda kanal/ altında dururlar (denetim bulgusu F04)."""
    import os
    adaylar = [Path(os.environ["PORTMAN_REF_DIR"])] if os.environ.get("PORTMAN_REF_DIR") else []
    adaylar += [ROOT, ROOT / "kanal", Path(__file__).resolve().parent]
    for d in adaylar:
        if (d / ad).is_file():
            return d / ad
    raise FileNotFoundError(f"referans dosyası bulunamadı: {ad} (aranan: {', '.join(str(d) for d in adaylar)})")


REF_DXF = _ref("ref_source-6x8.dxf")
REF_H = _ref("ref_h-connector.json")
FONT = "DejaVuSans.ttf"
FONT_PATH = _ref(FONT)
LABEL = "ÖN ONAYA SUNULAN TASLAK — ÜRETİM/STATİK PROJESİ DEĞİLDİR"
PENCERE_UST_KOTU = 200.0   # 250 cm duvarda lento 50; yükseklik değişince üst kot sabit tutulur (çıkarım, teyit bekliyor)

PENCERE_KAYNAK = {   # olcu: (kaynak blok, doğal yön, bbox)
    "120x120": ("kaynak-pencere-120120", "V", (53365.182, 8072.861, 53397.006, 8192.861)),
    "60x40":   ("kaynak-pencere-6040",   "V", (53358.249, 7932.278, 53385.862, 7992.278)),
    "120x180": ("kaynak-pencere-120180", "H", (53839.874, 6682.0,   53959.874, 6713.823)),
}
IC_KAPI_VARYANT = {   # kanonik V çerçevesi (pano +y, kalınlık +x), 125,5 pano, 82 açıklık
    "SOL_UST": ((7918.93, -54227.719), 90.0, 1.0),
    "SOL_ALT": ((7918.93, 54353.219), 90.0, -1.0),
    "SAG_ALT": ((-7912.93, 54353.219), 270.0, 1.0),
    "SAG_UST": ((-7912.93, -54227.719), 270.0, -1.0),
}
DIS_KAPI_KAYNAK = ("kaynak-dis-kapi", (-54272.601, -7068.569), 97.0, 54287.421, 0.57)

LAYERS = [
    ("AKS", 4, "CENTER"), ("AKS_YAZI", 4, "Continuous"), ("DIS_DUVAR_100", 30, "Continuous"), ("IC_DUVAR_60", 30, "Continuous"),
    ("KOSE_PROFIL_100", 8, "Continuous"), ("KOSE_PROFIL_60", 8, "Continuous"), ("IC_UCLU_H_60", 3, "Continuous"),
    ("PENCERE", 10, "Continuous"), ("IC_KAPILAR", 7, "Continuous"), ("ODA_ADLARI", 7, "Continuous"), ("OLCULER", 7, "Continuous"),
    ("OZEL_PANEL_OLCU_CM", 3, "Continuous"), ("VERANDA_PROFIL_100", 1, "VERANDA_KESIK"), ("VERANDA_DIKME", 1, "Continuous"),
    ("ACIK_SINIR", 8, "DASHED"), ("NET_ALAN_GEOMETRISI", 6, "Continuous"),
    ("MONTAJ_STANDART", 7, "Continuous"), ("MONTAJ_OZEL_PANO", 6, "Continuous"), ("MONTAJ_OZEL_OLCU", 6, "Continuous"), ("MONTAJ_YAZI", 4, "Continuous"),
    ("ON_GORUNUS", 7, "Continuous"), ("ON_DERZ", 8, "Continuous"), ("ON_DOGRAMA", 4, "Continuous"), ("ON_CATI", 7, "Continuous"),
    ("ON_TOPUK", 1, "Continuous"), ("ON_OLCU", 4, "Continuous"), ("ON_YAZI", 7, "Continuous"),
    ("CATI_GORUNUS", 7, "Continuous"), ("CATI_OLCU", 4, "Continuous"), ("CATI_YAZI", 7, "Continuous"),
    ("PORTMAN_INFO", 7, "Continuous"), ("OZELLIK_TABLOSU", 7, "Continuous"),
]


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fmt(v: float, dec=2) -> str:
    s = f"{v:.{dec}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def mm_tag(boy_cm: float) -> str:
    mm = round(boy_cm * 10, 1)
    return f"{int(mm)}p{int(round((mm - int(mm)) * 10))}"


def _grid_yazi(yapi, ayrac, ek) -> str:
    """Pano grid yazısı. Ölçüye kesimde: tam pano sayısı + kesilen son parçanın boyu."""
    nx, ny = float(yapi['grid']['x_pano']), float(yapi['grid']['y_pano'])
    if G.X_SON is None:
        return f"{fmt(nx)}{ayrac}{fmt(ny)}{ek}"
    def bir(boy):
        tam = int((boy + 1e-9) // G.MOD); kalan = boy - tam * G.MOD
        return f"{tam}{ek}" + (f" + {fmt(kalan)} cm" if kalan > 1e-6 else "")
    if G._AKS["x"] is not None:                              # İE-11: tablo modunda uçlar tablodan
        return f"{bir(G._AKS['x'][-1] - G._AKS['x'][0])}{ayrac}{bir(G._AKS['y'][-1] - G._AKS['y'][0])}"
    return f"{bir(G.X(nx) - G.X(0))}{ayrac}{bir(G.Y(ny) - G.Y(0))}"


class Cizici:
    def __init__(self, plan: G.Plan, katalog: Katalog):
        self.plan, self.kat = plan, katalog
        katalog.t_dis_cm, katalog.t_ic_cm = G.T_DIS, G.T_IC
        katalog.yukseklik_cm = float(plan.is_emri["yapi"].get("duvar_yuksekligi_cm", 250))
        self.doc = ezdxf.new("R2018", setup=True)
        doc = self.doc
        doc.units = units.CM
        doc.linetypes.add("VERANDA_KESIK", pattern=[30.0, 12.0, -18.0], description="Veranda profili 12 cizgi / 18 bosluk")
        for name, color, lt in [(G.katman(n), c, l) for n, c, l in LAYERS]:
            doc.layers.add(name, color=color, linetype=lt)
        doc.layers.get("NET_ALAN_GEOMETRISI").off()
        doc.layers.get("NET_ALAN_GEOMETRISI").dxf.plot = 0
        doc.styles.add("PORTMAN", font=FONT)
        for style in doc.styles:
            style.dxf.font = FONT
        for a in ("PORTMAN_ROOM", "AI_BOM", "PORTMAN_PANO"):
            doc.appids.add(a)
        ds = doc.dimstyles.duplicate_entry("EZDXF", "PORTMAN")
        ds.dxf.dimtxt = 14; ds.dxf.dimasz = 9; ds.dxf.dimexe = 6; ds.dxf.dimexo = 5; ds.dxf.dimtad = 1
        ds.dxf.dimgap = 4; ds.dxf.dimdec = 2; ds.dxf.dimzin = 8; ds.dxf.dimdsep = ord(","); ds.dxf.dimtxsty = "PORTMAN"
        ds.dxf.dimblk = "ARCHTICK"; ds.dxf.dimlfac = 1.0; ds.dxf.dimtih = 0; ds.dxf.dimtoh = 0
        self.msp = doc.modelspace()
        self._import_kaynak()
        self._dograma_bloklari()
        self._h_blok()
        self.bom_kayit = []     # (rol, kod, blok, x, y)

    # ------------------------------------------------------------------ bloklar
    def _import_kaynak(self):
        src = ezdxf.readfile(REF_DXF)
        imp = Importer(src, self.doc)
        for n in ["kaynak-ic-kapi", "kaynak-dis-kapi", "kaynak-pencere-120120", "kaynak-pencere-120180",
                  "kaynak-pencere-6040", "kaynak-on-pencere", "kaynak-on-kapi"]:
            imp.import_block(n)
        imp.finalize()

    def _dograma_bloklari(self):
        """Kaynak doğramaları BOM kodlu sarmalayıcı bloklara al (ayrı sayılabilsin)."""
        self.dograma = {}
        for olcu, (src, nat, bb) in PENCERE_KAYNAK.items():
            en, boy = G.PENCERE_OLCULERI[olcu]; kod = self.kat.pencere(en, boy)
            name = f"BOM_{kod}_PENCERE_{en*10}x{boy*10}"
            blk = self.doc.blocks.new(name); blk.add_blockref(src, (0, 0), dxfattribs={"layer": "PENCERE"})
            self.dograma[olcu] = (name, kod)
        k1 = self.kat.kapi(82, False); n1 = f"BOM_{k1}_IC_KAPI_ACIKLIK820"
        self.doc.blocks.new(n1).add_blockref("kaynak-ic-kapi", (0, 0), dxfattribs={"layer": "IC_KAPILAR"}); self.dograma["ic82"] = (n1, k1)

    def _dis_kapi_blok(self, w):
        key = f"dis{int(w)}"
        if key not in self.dograma:
            kod = self.kat.kapi(w, True); name = f"BOM_{kod}_DIS_KAPI_ACIKLIK{int(w*10)}"
            self.doc.blocks.new(name).add_blockref("kaynak-dis-kapi", (0, 0), dxfattribs={"layer": "IC_KAPILAR", "xscale": w / 97.0})
            self.dograma[key] = (name, kod)
        return self.dograma[key]

    def _h_blok_dis(self):
        """İE-11: dış duvardaki T birleşimi (3'lü H dış). Kaynak blok yok; şematik gövde (dış kalınlık × iç kalınlık)."""
        if getattr(self, "h_blok_adi_dis", None):
            return
        kod = self.kat.baglanti("uclu_h_dis"); self.h_blok_adi_dis = f"BOM_{kod}_UCLU_H_DIS_{G._mm(G.T_DIS)}x{G._mm(G.T_IC)}"; self.h_kod_dis = kod
        blk = self.doc.blocks.new(self.h_blok_adi_dis)
        self._rect(blk, -G.T_DIS / 2.0, -G.T_IC / 2.0, G.T_DIS / 2.0, G.T_IC / 2.0)

    def _h_blok(self):
        data = json.loads(REF_H.read_text()); ax, ay = 7546.678040288549, 806.98966762085
        kod = self.kat.baglanti("uclu_h"); self.h_blok_adi = f"BOM_{kod}_UCLU_H_{G._mm(G.T_IC)}"; self.h_kod = kod
        blk = self.doc.blocks.new(self.h_blok_adi)
        for tags in data["entities"]:
            d = dict(tags)
            kk = G.T_IC / 6.0   # kaynak blok 60 mm iç duvar içindir
            blk.add_line(((float(d[10]) - ax) * kk, (float(d[20]) - ay) * kk), ((float(d[11]) - ax) * kk, (float(d[21]) - ay) * kk), dxfattribs={"layer": "0", "color": 256})

    def _rect(self, blk, x0, y0, x1, y1):
        blk.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": "0", "color": 256})

    def pano_blok(self, p: G.Pano):
        """(blok adı, çerçeve, malzeme kodu). Kanonik V çerçevesi: pano +y boyunca, kalınlık +x; dış kapı H çerçevesi."""
        d = p.duvar; L = p.boy; t = 2 * d.h; dis = d.tur == "dis"
        ac = p.acilim
        kind = "DOLU" if ac is None else {"pencere": {"120x120": "P01", "120x180": "P02", "60x40": "P03"}.get(ac.olcu, "PXX"),
                                         "ic_kapi": "K01", "dis_kapi": "K02", "gecis": "OPEN"}[ac.tur]
        kod = self.kat.pano(dis, L, kind)
        var = ""
        if ac is not None and ac.tur == "ic_kapi":
            var = ac.varyant or G.kapi_varyanti(d, ac); ac.varyant = var
        name = f"BOM_{kod}_{mm_tag(L)}_{'DIS' if dis else 'IC'}_{kind}" + (f"_{var}" if var else "")
        frame = "H" if (ac is not None and ac.tur == "dis_kapi") else "V"
        if name in self.doc.blocks:
            return name, frame, kod
        blk = self.doc.blocks.new(name)
        if ac is None:
            self._rect(blk, 0, 0, t, L); return name, frame, kod
        w = ac.genislik; s = (L - w) / 2.0
        if ac.tur == "pencere":
            src, nat, bb = PENCERE_KAYNAK[ac.olcu]; dname, _ = self.dograma[ac.olcu]
            self._rect(blk, 0, 0, t, s); self._rect(blk, 0, s + w, t, L)
            orta = (t - 10.0) / 2.0
            if nat == "V": ins, rot = (t - bb[2] - orta, s - bb[1]), 0.0
            else:          ins, rot = (t - bb[3] - orta, s + bb[2]), 270.0
            blk.add_blockref(dname, ins, dxfattribs={"rotation": rot, "layer": "PENCERE"})
        elif ac.tur == "ic_kapi":
            self._rect(blk, 0, 0, t, s); self._rect(blk, 0, s + w, t, L)
            (ix, iy), rot, xs = IC_KAPI_VARYANT[var]; dname, _ = self.dograma["ic82"]
            if var.startswith("SAG"): ix += t - 6.0   # kaynak yerleşim 60 mm duvarın +x yüzüne göredir
            if abs(w - 82) > 1e-6:
                self.plan.uyarilar.append(f"İç kapı {w} cm: kaynak kapı sembolü 82 cm'lik; sembol ölçeklenmedi")
            blk.add_blockref(dname, (ix, iy + (L - 125.5) / 2.0), dxfattribs={"rotation": rot, "xscale": xs, "layer": "IC_KAPILAR"})
        elif ac.tur == "gecis":
            self._rect(blk, 0, 0, t, s); self._rect(blk, 0, s + w, t, L)
            blk.add_line((0, s), (t, s + w), dxfattribs={"layer": "IC_KAPILAR", "linetype": "DASHED"})   # kapısız geçiş işareti
            blk.add_line((0, s + w), (t, s), dxfattribs={"layer": "IC_KAPILAR", "linetype": "DASHED"})
        else:  # dış kapı: H çerçevesi (pano +x, kalınlık +y, kanat +y'ye açılır)
            src, (ix, iy), w0, SRC_LEFT, MARGIN = DIS_KAPI_KAYNAK; dname, _ = self._dis_kapi_blok(w)
            self._rect(blk, 0, 0, s, t); self._rect(blk, s + w, 0, L, t)
            xs = w / w0
            blk.add_blockref(dname, (s + xs * (MARGIN - SRC_LEFT), iy), dxfattribs={"rotation": 0.0, "layer": "IC_KAPILAR"})
        return name, frame, kod

    def kose_blok(self, k: G.Kose):
        x0, y0, x1, y1 = k.rect; wmm, hmm = int(round((x1 - x0) * 10)), int(round((y1 - y0) * 10))
        kod = self.kat.baglanti("dis_kose" if k.tur == "dis" else "ic_kose")
        name = f"BOM_{kod}_{'DIS' if k.tur == 'dis' else 'IC'}_KOSE_{wmm}x{hmm}"
        if name not in self.doc.blocks:
            self._rect(self.doc.blocks.new(name), 0, 0, x1 - x0, y1 - y0)
        return name, kod

    def mnt(self, name):
        """Montaj kopyası için MNT_ sarmalayıcı blok (sayıma girmez)."""
        m = "MNT_" + name
        if m not in self.doc.blocks:
            self.doc.blocks.new(m).add_blockref(name, (0, 0), dxfattribs={"layer": "0"})
        return m

    # ------------------------------------------------------------------ plan
    def yerlestir(self, name, kod, ins, rot, layer, rol, ox, oy, extra=None):
        bname = self.mnt(name) if rol == "MONTAJ" else name
        attrs = {"rotation": rot, "layer": layer}
        if extra: attrs.update(extra)
        e = self.msp.add_blockref(bname, (ins[0] + ox, ins[1] + oy), dxfattribs=attrs)
        e.set_xdata("AI_BOM", [(1000, kod), (1000, rol)])
        self.bom_kayit.append((rol, kod, bname, round(ins[0] + ox, 3), round(ins[1] + oy, 3)))
        return e

    def ciz_plan(self, ox: float, oy: float, rol: str, baslik: str, altbaslik: str):
        plan, msp = self.plan, self.msp
        W, H = plan.W, plan.H
        aks, alanlar, montaj = (rol == "ANA"), (rol == "KOPYA"), (rol == "MONTAJ")
        for d in plan.duvarlar:
            for p in d.panolar:
                name, frame, kod = self.pano_blok(p)
                r = p.rect(); standart = abs(p.boy - G.MOD) < 1e-6
                if montaj: layer = "MONTAJ_STANDART" if standart else "MONTAJ_OZEL_PANO"
                else:      layer = G.katman("DIS_DUVAR_100") if d.tur == "dis" else G.katman("IC_DUVAR_60")
                if frame == "V":
                    ins, rot = ((r[0], r[1]), 0.0) if d.yon == "y" else ((r[0], r[3]), 270.0)
                    if p.acilim and p.acilim.tur == "pencere":
                        n = p.acilim.disari_normal
                        if d.yon == "y": ins, rot = ((r[0], r[1]), 0.0) if n == "-x" else ((r[2], r[3]), 180.0)
                        else:            ins, rot = ((r[2], r[1]), 90.0) if n == "-y" else ((r[0], r[3]), 270.0)
                else:
                    n = p.acilim.icine_normal
                    if d.yon == "x": ins, rot = ((r[0], r[1]), 0.0) if n == "+y" else ((r[2], r[3]), 180.0)
                    else:            ins, rot = ((r[2], r[1]), 90.0) if n == "-x" else ((r[0], r[3]), 270.0)
                self.yerlestir(name, kod, ins, rot, layer, rol, ox, oy)
                if montaj and not standart:
                    if d.yon == "y":
                        side = 1 if d.c < W / 2 else -1
                        xd = r[2] + 40 if side > 0 else r[0] - 40
                        self.dim((r[0] + ox if side > 0 else r[2] + ox, r[1] + oy), (r[0] + ox if side > 0 else r[2] + ox, r[3] + oy), (xd + ox, 0), 90, "MONTAJ_OZEL_OLCU")
                    else:
                        side = 1 if d.c < H / 2 else -1
                        yd = r[3] + 40 if side > 0 else r[1] - 40
                        self.dim((r[0] + ox, r[1] + oy if side > 0 else r[3] + oy), (r[2] + ox, r[1] + oy if side > 0 else r[3] + oy), (0, yd + oy), 0, "MONTAJ_OZEL_OLCU")
                if montaj and p.acilim and p.acilim.tur == "pencere":
                    g = p.gap(); cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
                    en, boy = G.PENCERE_OLCULERI[p.acilim.olcu]; pk = self.dograma[p.acilim.olcu][1]
                    off = 28 if d.yon == "x" else 0; offx = 0 if d.yon == "x" else 28
                    if d.yon == "y" and d.c > W / 2: offx = -28
                    if d.yon == "x" and d.c > H / 2: off = -28
                    self.text(f"{pk} {en}×{boy} cm", (cx + ox + offx, cy + oy + off), 11, "MONTAJ_YAZI", rot=(90.0 if d.yon == "y" else 0.0))
        for k in plan.koseler:
            name, kod = self.kose_blok(k)
            layer = "MONTAJ_STANDART" if montaj else (G.katman("KOSE_PROFIL_100") if k.tur == "dis" else G.katman("KOSE_PROFIL_60"))
            self.yerlestir(name, kod, (k.rect[0], k.rect[1]), 0.0, layer, rol, ox, oy)
        for hb in plan.h_baglantilar:
            if getattr(hb, "tur", "ic") == "dis":                   # İE-11
                self._h_blok_dis()
                self.yerlestir(self.h_blok_adi_dis, self.h_kod_dis, (hb.x, hb.y), hb.rot, "MONTAJ_STANDART" if montaj else G.katman("IC_UCLU_H_60"), rol, ox, oy)
                continue
            self.yerlestir(self.h_blok_adi, self.h_kod, (hb.x, hb.y), hb.rot, "MONTAJ_STANDART" if montaj else G.katman("IC_UCLU_H_60"), rol, ox, oy)
        # veranda dikmeleri
        if plan.dikmeler:
            kod = self.kat.baglanti("dikme"); name = f"BOM_{kod}_VERANDA_DIKME_100x100"
            if name not in self.doc.blocks: self._rect(self.doc.blocks.new(name), 0, 0, 10, 10)
            for (x0, y0, x1, y1) in plan.dikmeler:
                self.yerlestir(name, kod, (x0, y0), 0.0, "MONTAJ_STANDART" if montaj else "VERANDA_DIKME", rol, ox, oy)
        # veranda profili (her açık kenar bir blok: dış yüz + 10 cm içeri, kesik çizgi)
        for ad, m in plan.mahaller.items():
            if not m.acik: continue
            ring = list(m.poly.simplify(0.0).exterior.coords)
            segs = []
            for (ax_, ay_), (bx_, by_) in zip(ring, ring[1:]):
                if (abs(ax_ - bx_) < 1e-9 and (abs(ax_) < 1e-9 or abs(ax_ - W) < 1e-9)) or (abs(ay_ - by_) < 1e-9 and (abs(ay_) < 1e-9 or abs(ay_ - H) < 1e-9)):
                    segs.append((min(ax_, bx_), min(ay_, by_), max(ax_, bx_), max(ay_, by_)))
            pts_all = [(x0, y0) for (x0, y0, x1, y1) in segs] + [(x1, y1) for (x0, y0, x1, y1) in segs] + [(x0, y1) for (x0, y0, x1, y1) in segs] + [(x1, y0) for (x0, y0, x1, y1) in segs]
            for (x0, y0, x1, y1) in segs:
                vertical = abs(x0 - x1) < 1e-9
                boy = (y1 - y0) if vertical else (x1 - x0)
                kod = self.kat.veranda_profil(boy, "YAN" if vertical else "ON")
                name = f"BOM_{kod}_VERANDA_{'YAN' if vertical else 'ON'}_{mm_tag(boy)}"
                if name not in self.doc.blocks:
                    blk = self.doc.blocks.new(name)
                    if vertical:
                        sx = 10.0 if x0 < W / 2 else -10.0
                        ya = 10.0 if pts_all.count((x0, y0)) > 1 else 0.0; yb = boy - (10.0 if pts_all.count((x0, y1)) > 1 else 0.0)
                        blk.add_line((0, 0), (0, boy), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                        blk.add_line((sx, ya), (sx, yb), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                    else:
                        sy = 10.0 if y0 < H / 2 else -10.0
                        xa = 10.0 if pts_all.count((x0, y0)) > 1 else 0.0; xb = boy - (10.0 if pts_all.count((x1, y0)) > 1 else 0.0)
                        blk.add_line((0, 0), (boy, 0), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                        blk.add_line((xa, sy), (xb, sy), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                self.yerlestir(name, kod, (x0, y0), 0.0, "MONTAJ_STANDART" if montaj else "VERANDA_PROFIL_100", rol, ox, oy)
        for (x0, y0, x1, y1) in self._merge_lines(plan.acik_sinir_cizgileri):
            msp.add_line((x0 + ox, y0 + oy), (x1 + ox, y1 + oy), dxfattribs={"layer": "ACIK_SINIR"})
        # mahaller
        etiketler = {}
        for ad, m in plan.mahaller.items():
            poly = m.poly.simplify(0.0)
            if rol == "ANA":
                e = msp.add_lwpolyline([(x + ox, y + oy) for x, y in list(poly.exterior.coords)[:-1]], close=True, dxfattribs={"layer": "NET_ALAN_GEOMETRISI"})
                e.set_xdata("PORTMAN_ROOM", [(1000, ad)])
            # etiket, mahalin en büyük dikdörtgen parçasının (aks gridinde) ortasına; L biçimli mahalde koridora değil geniş parçaya
            r_big = max(m.rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
            etiket_poly = box(G.X(r_big[0]), G.Y(r_big[1]), G.X(r_big[2]), G.Y(r_big[3])).intersection(poly)
            if etiket_poly.is_empty or etiket_poly.area < 1.0: etiket_poly = poly
            bx0, by0, bx1, by1 = etiket_poly.bounds
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            h = 28 if poly.area > 60000 else 22
            if montaj: h = 18
            h, rot = self._etiket_sigdir(ad, etiket_poly, h)
            etiketler[ad] = (cx, cy, h, rot)
            if alanlar:
                if rot:
                    self.text(ad, (cx + ox + 16, cy + oy), h, "ODA_ADLARI", rot=rot)
                    self.text(f"{m.alan_m2:.2f}".replace(".", ",") + " m²", (cx + ox - 12, cy + oy), min(20, h), "ODA_ADLARI", rot=rot)
                else:
                    self.text(ad, (cx + ox, cy + oy + 14), h, "ODA_ADLARI")
                    self.text(f"{m.alan_m2:.2f}".replace(".", ",") + " m²", (cx + ox, cy + oy - 18), min(20, h), "ODA_ADLARI")
            else:
                self.text(ad, (cx + ox, cy + oy), h, "ODA_ADLARI" if not montaj else "MONTAJ_YAZI", rot=rot)
        if aks and G.ana_akslar("x") is not None:          # İE-11: aks tablosu → ana akslar (tam pano + ek aks + uç)
            for i, x in enumerate(G.ana_akslar("x")):
                msp.add_line((x + ox, -35 + oy), (x + ox, H + 41 + oy), dxfattribs={"layer": "AKS"})
                self.text(chr(ord("A") + i), (x + ox, H + 60 + oy), 14, "AKS_YAZI")
            for j, y in enumerate(G.ana_akslar("y")):
                msp.add_line((-35 + ox, y + oy), (W + 35 + ox, y + oy), dxfattribs={"layer": "AKS"})
                self.text(str(j + 1), (-53 + ox, y + oy), 14, "AKS_YAZI")
        elif aks:
            for i in range(int(plan.nx * 2) + 1):
                if i % 2: continue
                x = G.X(i / 2)
                msp.add_line((x + ox, -35 + oy), (x + ox, H + 41 + oy), dxfattribs={"layer": "AKS"})
                self.text(chr(ord("A") + i // 2), (x + ox, H + 60 + oy), 14, "AKS_YAZI")
            for j in range(int(plan.ny * 2) + 1):
                if j % 2: continue
                y = G.Y(j / 2)
                msp.add_line((-35 + ox, y + oy), (W + 35 + ox, y + oy), dxfattribs={"layer": "AKS"})
                self.text(str(j // 2 + 1), (-53 + ox, y + oy), 14, "AKS_YAZI")
        # ölçüler
        self.dim((ox, oy), (W + ox, oy), (0, -85 + oy), 0)
        self.dim((ox, oy), (ox, H + oy), (-115 + ox, 0), 90)
        if not montaj:
            if G.ana_akslar("x") is not None:               # İE-11
                xs, ys = G.ana_akslar("x"), G.ana_akslar("y")
            else:
                xs = [G.X(i / 2) for i in range(0, int(plan.nx * 2) + 1, 2)] + ([G.X(plan.nx)] if int(plan.nx * 2) % 2 else [])
                ys = [G.Y(j / 2) for j in range(0, int(plan.ny * 2) + 1, 2)] + ([G.Y(plan.ny)] if int(plan.ny * 2) % 2 else [])
            for a, b in zip(xs, xs[1:]): self.dim((a + ox, H + oy), (b + ox, H + oy), (0, H + 102 + oy), 0)
            for a, b in zip(ys, ys[1:]): self.dim((W + ox, a + oy), (W + ox, b + oy), (W + 81 + ox, 0), 90)
            for d in plan.duvarlar:
                for p in d.panolar:
                    if abs(p.boy - G.MOD) < 1e-6: continue
                    r = p.rect()
                    if d.yon == "y":
                        side = 1 if d.c < W / 2 else -1; xd = r[2] + 40 if side > 0 else r[0] - 40
                        self.dim((r[0] + ox if side > 0 else r[2] + ox, r[1] + oy), (r[0] + ox if side > 0 else r[2] + ox, r[3] + oy), (xd + ox, 0), 90, "OZEL_PANEL_OLCU_CM")
                    else:
                        side = 1 if d.c < H / 2 else -1; yd = r[3] + 40 if side > 0 else r[1] - 40
                        self.dim((r[0] + ox, r[1] + oy if side > 0 else r[3] + oy), (r[2] + ox, r[1] + oy if side > 0 else r[3] + oy), (0, yd + oy), 0, "OZEL_PANEL_OLCU_CM")
            for ad, m in plan.mahaller.items():
                if not m.acik: continue
                us = [u for u, v in m.cells]; vs = [v for u, v in m.cells]
                x0, x1 = G.X(min(us) / 2), G.X((max(us) + 1) / 2); y0, y1 = G.Y(min(vs) / 2), G.Y((max(vs) + 1) / 2)
                # dar açık mahalde (tek pano şeridi) ölçü çizgisi plan dışına alınır; yazılarla çakışmasın
                dar = (x1 - x0) < 2 * G.MOD - 1e-6
                if dar and y0 <= G.Y(0) + 1e-6: yb = -45.0
                elif dar and y1 >= G.Y(plan.ny) - 1e-6: yb = H + 30.0
                else: yb = y0 + 55.0
                self.dim((x0 + ox, y0 + oy), (x1 + ox, y0 + oy), (0, yb + oy), 0)
                if dar and x1 >= G.X(plan.nx) - 1e-6: xb = W + 40.0
                elif dar and x0 <= G.X(0) + 1e-6: xb = -80.0
                else: xb = x0 + 33.0
                self.dim((x0 + ox, y0 + oy), (x0 + ox, y1 + oy), (xb + ox, 0), 90)
                cx, cy, hh, rot = etiketler[ad]
                pos = (cx + ox + 16 + hh / 2 + 13, cy + oy) if rot else (cx + ox, cy + oy + (hh / 2 + 24 + (14 if alanlar else 0)))
                self.text(f"{fmt((x1 - x0) / G.MOD)} x {fmt((y1 - y0) / G.MOD)} aks modülü", pos, 13, "ODA_ADLARI", rot=rot)
        if montaj:
            self.text("Mor: standart dışı pano (gerçek uçtan uca boy ölçülü) | Beyaz: standart 125,5 cm pano | Ölçüler cm", (W / 2 + ox, -145 + oy), 13, "MONTAJ_YAZI")
            self.text("Pencere etiketi: malzeme kodu + en×yükseklik | Montaj kopyası BOM'a sayılmaz", (W / 2 + ox, -175 + oy), 13, "MONTAJ_YAZI")
        self.text(baslik, (W / 2 + ox, H + 206 + oy), 24, "ODA_ADLARI")
        self.text(altbaslik, (W / 2 + ox, H + 168 + oy), 15, "ODA_ADLARI")

    _FONT = None

    @classmethod
    def yazi_eni(cls, s: str, h: float) -> float:
        """DejaVu Sans ile CAD yüksekliği h (büyük harf yüksekliği) olan yazının gerçek eni (cm)."""
        if cls._FONT is None:
            import pymupdf
            cls._FONT = pymupdf.Font(fontfile=str(FONT_PATH))
        return cls._FONT.text_length(s, fontsize=h / 0.729)   # DejaVu büyük harf yüksekliği ≈ 0,729 em

    @classmethod
    def _etiket_sigdir(cls, ad: str, poly, h: float):
        """Mahal adını mahalin içine sığdır: dar-uzun mahalde 90° döndür, gerekirse küçült (en az 14)."""
        x0, y0, x1, y1 = poly.bounds
        bw, bh = x1 - x0, y1 - y0
        genislik = cls.yazi_eni(ad, h) + 8
        rot = 0.0
        if genislik > 0.85 * bw and bh > 1.5 * bw:   # belirgin dar-uzun şerit → döndür
            rot = 90.0
            uygun = 0.85 * bh
        else:
            uygun = 0.85 * bw
        if genislik > uygun:
            h = max(14.0, h * uygun / genislik)
        return h, rot

    @staticmethod
    def _merge_lines(segs):
        out = []
        for s in sorted(segs):
            x0, y0, x1, y1 = s; merged = False
            for i, (a0, b0, a1, b1) in enumerate(out):
                if abs(x0 - x1) < 1e-9 and abs(a0 - a1) < 1e-9 and abs(a0 - x0) < 1e-9 and abs(b1 - y0) < 1e-9: out[i] = (a0, b0, a1, y1); merged = True; break
                if abs(y0 - y1) < 1e-9 and abs(b0 - b1) < 1e-9 and abs(b0 - y0) < 1e-9 and abs(a1 - x0) < 1e-9: out[i] = (a0, b0, x1, b1); merged = True; break
            if not merged: out.append(s)
        return out

    def text(self, s, pos, h, layer, align=TextEntityAlignment.MIDDLE_CENTER, rot=0.0):
        self.msp.add_text(s, dxfattribs={"height": h, "layer": layer, "style": "PORTMAN", "rotation": rot}).set_placement(pos, align=align)

    def dim(self, p1, p2, base, angle, layer="OLCULER"):
        base = (p1[0], base[1]) if angle == 0 else (base[0], p1[1])
        d = self.msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="PORTMAN", dxfattribs={"layer": layer},
                                    override={"dimtxt": 14, "dimasz": 9, "dimexe": 6, "dimexo": 5, "dimdec": 2, "dimzin": 8, "dimdsep": ord(",")})
        d.render()

    # ------------------------------------------------------------------ ön görünüş / çatı / tablo
    def _disari_yon(self, d):
        for k, a, b in d.edges:
            ma, mb = self.plan.mahaller.get(a), self.plan.mahaller.get(b)
            a_out = (a == G.OUT) or (ma is not None and ma.acik); b_out = (b == G.OUT) or (mb is not None and mb.acik)
            if a_out and not b_out: return "-x" if d.yon == "y" else "-y"
            if b_out and not a_out: return "+x" if d.yon == "y" else "+y"
        return None

    def ciz_on_gorunus(self, ox, top):
        plan, msp = self.plan, self.msp
        W = plan.W; hy = float(plan.is_emri["yapi"].get("duvar_yuksekligi_cm", 250)); cati = plan.is_emri.get("cati", {})
        egim = float(cati.get("egim_yuzde", 33)) / 100.0; sacak = float(cati.get("sacak_cm", 30)); topuk = float(cati.get("topuk_cm", 10)); lento = hy - PENCERE_UST_KOTU
        bot = top - hy
        msp.add_lwpolyline([(ox, bot), (W + ox, bot), (W + ox, top), (ox, top)], close=True, dxfattribs={"layer": "ON_GORUNUS"})
        xs = set()
        on_duvarlar = [d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x" and self._disari_yon(d) == "-y"]
        for d in on_duvarlar:
            for p in d.panolar: xs.add(p.a0); xs.add(p.a1)
        for d in plan.duvarlar:
            if d.tur == "dis" and d.yon == "y": xs.add(d.c - d.h); xs.add(d.c + d.h)
        for x in sorted(xs):
            if 1e-6 < x < W - 1e-6: msp.add_line((x + ox, bot), (x + ox, top), dxfattribs={"layer": "ON_DERZ"})
        for d in on_duvarlar:
            for p in d.panolar:
                if not p.acilim: continue
                g = p.gap(); x0, x1 = g[0], g[2]; w = x1 - x0
                if p.acilim.tur == "pencere":
                    h = p.acilim.yukseklik; alt = hy - lento - h
                    msp.add_blockref("kaynak-on-pencere", (x0 + ox, bot + alt), dxfattribs={"xscale": w / 77.101, "yscale": h / 116.017, "layer": "ON_DOGRAMA"})
                elif p.acilim.tur == "dis_kapi":
                    h = hy - lento
                    msp.add_blockref("kaynak-on-kapi", (x0 + ox, bot), dxfattribs={"xscale": w / 68.697, "yscale": h / 133.557, "layer": "ON_DOGRAMA"})
        tw = W + 2 * sacak; rise = topuk + (tw / 2) * egim
        xl, xr, xm = -sacak + ox, W + sacak + ox, W / 2 + ox
        msp.add_line((xl, top), (xr, top), dxfattribs={"layer": "ON_CATI"})
        msp.add_line((xl, top), (xl, top + topuk), dxfattribs={"layer": "ON_TOPUK"}); msp.add_line((xr, top), (xr, top + topuk), dxfattribs={"layer": "ON_TOPUK"})
        msp.add_line((xl, top + topuk), (xm, top + rise), dxfattribs={"layer": "ON_CATI"}); msp.add_line((xm, top + rise), (xr, top + topuk), dxfattribs={"layer": "ON_CATI"})
        self.dim((xl, top), (xr, top), (0, bot - 110), 0, "ON_OLCU"); self.dim((ox, bot), (W + ox, bot), (0, bot - 67), 0, "ON_OLCU")
        self.dim((W + ox, bot), (W + ox, top), (W + 77 + ox, 0), 90, "ON_OLCU"); self.dim((xr, top), (xm, top + rise), (W + 77 + ox, 0), 90, "ON_OLCU")
        pen = [p for d in on_duvarlar for p in d.panolar if p.acilim and p.acilim.tur == "pencere"]
        if pen:
            p = min(pen, key=lambda q: q.gap()[0]); g = p.gap(); h = p.acilim.yukseklik; ust = hy - lento; alt = ust - h
            self.dim((g[0] + ox, bot), (g[0] + ox, bot + alt), (g[0] - 33 + ox, 0), 90, "ON_OLCU"); self.dim((g[0] + ox, bot + ust), (g[0] + ox, top), (g[0] - 33 + ox, 0), 90, "ON_OLCU")
        self.text("%" + fmt(egim * 100), (W / 4 + ox, top + rise / 2 + 30), 18, "ON_YAZI"); self.text("%" + fmt(egim * 100), (3 * W / 4 + ox, top + rise / 2 + 30), 18, "ON_YAZI")
        self.text("ÖN GÖRÜNÜŞ - ÇALIŞMA", (W / 2 + ox, top + rise + 100), 26, "ON_YAZI")
        self.text(f"Pencere üst kotu {fmt(hy - lento)} cm | Lento {fmt(lento)} cm | Bina yüksekliği {fmt(hy)} cm", (W / 2 + ox, bot - 150), 15, "ON_YAZI")

    def ciz_cati_profili(self, ox, oy):
        plan, msp = self.plan, self.msp
        W = plan.W; cati = plan.is_emri.get("cati", {})
        egim = float(cati.get("egim_yuzde", 33)) / 100.0; sacak = float(cati.get("sacak_cm", 30)); topuk = float(cati.get("topuk_cm", 10))
        tw = W + 2 * sacak; rise = topuk + (tw / 2) * egim
        xl, xr, xm = ox - sacak, ox + W + sacak, ox + W / 2
        lw = {"layer": "CATI_GORUNUS", "lineweight": 35}
        msp.add_line((xl, oy), (xr, oy), dxfattribs=lw)
        msp.add_line((xl, oy), (xl, oy + topuk), dxfattribs={**lw, "color": 1}); msp.add_line((xr, oy), (xr, oy + topuk), dxfattribs={**lw, "color": 1})
        msp.add_line((xl, oy + topuk), (xm, oy + rise), dxfattribs=lw); msp.add_line((xm, oy + rise), (xr, oy + topuk), dxfattribs=lw)
        self.dim((xl, oy), (xr, oy), (0, oy - 120), 0, "CATI_OLCU"); self.dim((xl, oy), (ox, oy), (0, oy - 60), 0, "CATI_OLCU")
        self.dim((ox, oy), (ox + W, oy), (0, oy - 60), 0, "CATI_OLCU"); self.dim((ox + W, oy), (xr, oy), (0, oy - 60), 0, "CATI_OLCU")
        self.dim((xl, oy), (xl, oy + topuk), (xl - 63, 0), 90, "CATI_OLCU"); self.dim((xr, oy), (xm, oy + rise), (xr + 74, 0), 90, "CATI_OLCU")
        self.text("%" + fmt(egim * 100), (ox + W / 4, oy + rise / 2 + 35), 23, "CATI_YAZI"); self.text("%" + fmt(egim * 100), (ox + 3 * W / 4, oy + rise / 2 + 35), 23, "CATI_YAZI")
        self.text("TOPUK", (xl - 53, oy + 53), 14, "CATI_YAZI")
        self.text("ÇATI PROFİLİ - TOPUK VE SAÇAK", (xm, oy + rise + 130), 25, "CATI_YAZI")
        self.text(f"İki yanda {fmt(sacak)} cm saçak | İki uçta {fmt(topuk)} cm topuk | Eğim %{fmt(egim*100)} (derece değil)", (xm, oy + rise + 95), 17, "CATI_YAZI")
        self.text("Makas kısa kenarı geçer; mahya uzun kenar boyunca uzanır. Ölçüler cm.", (xm, oy - 180), 16, "CATI_YAZI")

    def ciz_ozellik_tablosu(self, ox, oy, satirlar):
        msp = self.msp; w1, w2, rh = 300.0, 640.0, 34.0; n = len(satirlar) + 1
        msp.add_lwpolyline([(ox, oy), (ox + w1 + w2, oy), (ox + w1 + w2, oy - rh * n), (ox, oy - rh * n)], close=True, dxfattribs={"layer": "OZELLIK_TABLOSU"})
        msp.add_line((ox + w1, oy - rh), (ox + w1, oy - rh * n), dxfattribs={"layer": "OZELLIK_TABLOSU"})
        self.text("TEKNİK ÖZELLİKLER", (ox + (w1 + w2) / 2, oy - rh / 2), 16, "OZELLIK_TABLOSU")
        for i, (k, v) in enumerate(satirlar, start=1):
            y = oy - rh * i
            msp.add_line((ox, y), (ox + w1 + w2, y), dxfattribs={"layer": "OZELLIK_TABLOSU"})
            self.text(k, (ox + 10, y - rh / 2), 12, "OZELLIK_TABLOSU", TextEntityAlignment.MIDDLE_LEFT)
            self.text(v, (ox + w1 + 10, y - rh / 2), 12, "OZELLIK_TABLOSU", TextEntityAlignment.MIDDLE_LEFT)

    # ------------------------------------------------------------------ BOM
    def bom(self):
        """ANA rolündeki üst blokların malzeme kodlarına göre sayımı + doğrama iç INSERT'leri."""
        counts = {}
        for rol, kod, bname, x, y in self.bom_kayit:
            if rol != "ANA": continue
            counts[kod] = counts.get(kod, 0) + 1
            for e in self.doc.blocks[bname]:
                if e.dxftype() == "INSERT" and e.dxf.name.startswith("BOM_"):
                    k2 = e.dxf.name.split("_")[1]; counts[k2] = counts.get(k2, 0) + 1
        rows = []
        for kod in sorted(counts):
            m = self.kat.malzemeler.get(kod, {})
            rows.append({"kod": kod, "grup": m.get("group", ""), "malzeme": m.get("label", ""), "olcu_mm": m.get("dimensions_mm"), "adet": counts[kod], "birim": "adet", "not": m.get("note", "")})
        return rows


# ---------------------------------------------------------------------- üretim akışı

def uret(is_emri: dict, cikti_dir: Path, ad_govde: str | None = None, pdf_hatada: bool = False) -> dict:
    """İş Emri → DXF (kaydet, yeniden aç, doğrula) → PDF. Doğrulama GEÇMEZSE teslim edilebilir PDF üretilmez (denetim bulgusu F08);
    pdf_hatada=True yalnız tanı için '<ad>.HATALI.pdf' yazar. Dönen manifest'te 'pdf' o zaman None, 'validation_passed' False."""
    from . import validate as V
    cikti_dir = Path(cikti_dir); cikti_dir.mkdir(parents=True, exist_ok=True)
    plan = G.kur(is_emri)
    plan.uyarilar[:0] = list(is_emri.get("pafta_uyarilari", []))
    t0 = time.time()
    kat = Katalog()
    c = Cizici(plan, kat)
    W, H = plan.W, plan.H
    yapi = is_emri["yapi"]
    stem = ad_govde or f"Portman_{is_emri.get('is_emri_no','IS')}_r{int(is_emri.get('revizyon',1)):02d}"
    baslik = f"{plan.is_emri.get('talep',{}).get('musteri_adi','')} | {_grid_yazi(yapi, ' x ', ' PANO')} | {fmt(W)} × {fmt(H)} cm"
    icerik = is_emri.get("cikti", {}).get("icerik", [])
    gap = W + 300.0
    c.ciz_plan(0.0, 0.0, "ANA", "KAT PLANI — AKSLI", baslik + " | Model ve ölçüler: cm | 125,5 cm aks düzeni")
    c.ciz_plan(gap, 0.0, "KOPYA", "KAT PLANI — NET ALANLAR", baslik + " | Net alanlar oda adının altında, m²")
    montaj = ("montaj_kopyasi" in icerik) or True
    if montaj:
        c.ciz_plan(2 * gap, 0.0, "MONTAJ", "SAHA MONTAJ PLANI", baslik + " | Standart dışı panolar mor ve ölçülü")
    notlar = [f"Pencereler pano ortasında. Pencere üstünden duvar üstüne (lento): {fmt(float(yapi.get('duvar_yuksekligi_cm', 250)) - PENCERE_UST_KOTU)} cm.",
              "Net alanlar kapı eşikleri hariç; veranda alanı açık dış kenarlara kadardır.",
              "Açık mahal sınırları bitişik duvar yüzünün devamı kabul edildi."]
    for i, s in enumerate(notlar):
        c.text(s, (gap + W / 2, -145 - 30 * i), 13, "ODA_ADLARI")
    _cati = is_emri.get("cati", {})
    _rise = float(_cati.get("topuk_cm", 10)) + (W + 2 * float(_cati.get("sacak_cm", 30))) / 2 * float(_cati.get("egim_yuzde", 33)) / 100.0
    kay = max(0.0, _rise - 147.445) if G.yeni_anahtar_var(is_emri) else 0.0   # İE-11: eski İş Emri'nde pafta yerleşimi değişmez
    kay2 = kay + max(0.0, float(yapi.get("duvar_yuksekligi_cm", 250)) - 250.0)
    c.ciz_on_gorunus(0.0, -600.0 - kay)
    c.ciz_cati_profili(gap, -550.0 - kay)
    hy = yapi.get("duvar_yuksekligi_cm", 250); cati = is_emri.get("cati", {})
    tab = [("Bina / pano grid", f"{_grid_yazi(yapi, ' × ', ' pano')} — {fmt(W)} × {fmt(H)} cm"),
           ("Sistem", "Prefabrik panel (8 mm fibercement)"), ("Duvar yüksekliği", f"{fmt(hy)} cm"), ("Dış duvar / iç duvar", f"{G._mm(G.T_DIS)} mm / {G._mm(G.T_IC)} mm"),
           ("Pano modülü", "125,5 cm (isteğe bağlı yarım pano 62,75 cm)"),
           ("Çatı", f"{cati.get('tip','besik').capitalize()} — %{fmt(float(cati.get('egim_yuzde',33)))} eğim, {fmt(float(cati.get('sacak_cm',30)))} cm saçak, {fmt(float(cati.get('topuk_cm',10)))} cm topuk"),
           ("Pencereler", "PVC doğrama; katalog 120×120 / 120×180 / 60×40"), ("Kapılar", "Dış: çelik kapı; iç: Amerikan panel kapı"),
           ("Kat sayısı", str(yapi.get("kat_sayisi", 1))), ("Revizyon", f"r{int(is_emri.get('revizyon',1)):02d}")]
    if is_emri.get("ozellikler"):                       # İE-11: paftanın teknik özellikleri İş Emri'nden (PK-01: "Dış Kapı: Alıcıya ait")
        tab = [r for r in tab if r[0] not in ("Pencereler", "Kapılar")] + [(str(k), str(v)) for k, v in is_emri["ozellikler"].items()]
    c.ciz_ozellik_tablosu((3 if montaj else 2) * gap, H + 140, tab)
    cx = ((3 if montaj else 2) * gap - 300) / 2
    c.text(LABEL, (cx, H + 320), 23, "PORTMAN_INFO")
    c.text(f"PORTMAN | {is_emri.get('talep',{}).get('bayi',{}).get('ad','')} / {is_emri.get('talep',{}).get('musteri_adi','')} | İş Emri {is_emri.get('is_emri_no','')} r{int(is_emri.get('revizyon',1)):02d}", (cx, H + 275), 20, "PORTMAN_INFO")
    c.text(f"Duvar: {fmt(G.T_DIS)} / {fmt(G.T_IC)} cm | Yükseklik: {fmt(hy)} cm | Pano: 125,5 cm | Çatı: %{fmt(float(cati.get('egim_yuzde',33)))}", (cx, -1090 - kay2), 18, "PORTMAN_INFO")
    c.text("Kural kaydı v1.4.3 ile üretildi. Yan görünüş ve üretim/statik hesabı bu taslağın kapsamında değildir.", (cx, -1130 - kay2), 14, "PORTMAN_INFO")
    c.text("Portman motor v1.1 | Üretim: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), (cx, -1165 - kay2), 13, "PORTMAN_INFO")
    for i, u in enumerate(plan.uyarilar[:4]):
        c.text("UYARI: " + u, (cx, -1200 - kay2 - 25 * i), 12, "PORTMAN_INFO")
    dxf = cikti_dir / f"{stem}.dxf"; pdf = cikti_dir / f"{stem}.pdf"
    c.doc.saveas(dxf)
    bom_rows = c.bom()
    alici = [p for p in plan.panolar if p.acilim and p.acilim.dograma == "alıcıya ait"]   # İE-11
    if alici:
        kodlar = {c._dis_kapi_blok(p.acilim.genislik)[1] for p in alici if p.acilim.tur == "dis_kapi"} | {c.dograma[p.acilim.olcu][1] for p in alici if p.acilim.tur == "pencere"}
        for r in bom_rows:
            if r["kod"] in kodlar:
                r["not"] = (r["not"] + " " if r["not"] else "") + "Alıcıya ait: doğrama yükleme listesine girmez (İş Emri)."; r["alici"] = True
    (cikti_dir / "bom.json").write_text(json.dumps({"is_emri_no": is_emri.get("is_emri_no"), "sayim_kapsami": "yalnız ANA rolündeki üst BOM_ blokları + içlerindeki doğrama INSERT'leri",
                                                     "birim": "adet; ölçüler mm", "kalemler": bom_rows, "yeni_kodlar": kat.yeni}, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(cikti_dir / "bom.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["Kod", "Grup", "Malzeme", "Ölçü (mm)", "Adet", "Birim", "Not"])
        for r in bom_rows: w.writerow([r["kod"], r["grup"], r["malzeme"], "×".join(str(v) for v in (r["olcu_mm"] or []) if v is not None), r["adet"], r["birim"], r["not"]])
    kat.kaydet_kopya(cikti_dir / "malzeme_katalogu.guncel.json")
    saved = ezdxf.readfile(dxf)
    audit = saved.audit()
    checks = V.dogrula(saved, plan, is_emri)
    checks["saved_dxf_audit_errors"] = len(audit.errors); checks["saved_dxf_audit_fixes"] = len(audit.fixes)
    checks["bom_counts_from_file"] = V.bom_sayim(saved)
    (cikti_dir / "validation.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    gecti = checks.get("passed") is True
    pdf_yazildi = None
    if gecti or pdf_hatada:
        if not gecti:
            pdf = cikti_dir / f"{stem}.HATALI.pdf"      # yalnız tanı; teslim edilmez
        backend = pymupdf.PyMuPdfBackend()
        cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE, color_policy=config.ColorPolicy.COLOR, min_lineweight=0.15)
        Frontend(RenderContext(saved), backend, config=cfg).draw_layout(saved.modelspace())
        page = layout.Page(594, 420, layout.Units.mm, margins=layout.Margins.all(12))
        pdf.write_bytes(backend.get_pdf_bytes(page, settings=layout.Settings(fit_page=True)))
        with fitz.open(pdf) as document:
            if len(document) != 1 or not document[0].get_drawings():
                raise RuntimeError("PDF boş veya tek sayfa değil")
            document[0].get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False).save(cikti_dir / ("preview.png" if gecti else "preview.HATALI.png"))
        pdf_yazildi = pdf
    manifest = {"is_emri_no": is_emri.get("is_emri_no"), "revizyon": is_emri.get("revizyon", 1), "generated_at": int(time.time()),
                "duration_s": round(time.time() - t0, 2), "dxf": dxf.name,
                "pdf": pdf_yazildi.name if (pdf_yazildi and gecti) else None, "dxf_sha256": sha256(dxf),
                "pdf_sha256": sha256(pdf_yazildi) if (pdf_yazildi and gecti) else None,
                "tani_pdf": pdf_yazildi.name if (pdf_yazildi and not gecti) else None,
                "pdf_skipped_reason": None if gecti else "doğrulama geçmedi; teslim PDF'i üretilmedi",
                "validation_passed": checks.get("passed"), "warnings": plan.uyarilar, "generator": "portman-motor-v1.1",
                "generator_sha256": {f: sha256(ROOT / "motor" / f) for f in ("geometry.py", "dxf_out.py", "validate.py", "katalog.py")},
                "reference_dxf_sha256": sha256(REF_DXF), "pdf_generated_from_reopened_dxf": True, "yeni_kodlar": [e["code"] for e in kat.yeni]}
    (cikti_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti_dir / "is_emri.json").write_text(json.dumps(is_emri, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
