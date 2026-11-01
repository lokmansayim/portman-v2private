"""Portman motor v1.1 — DXF/PDF çıktısı (BOM bloklu).

Plan (geometry.kur) → düzenlenebilir DXF (ezdxf) → yeniden aç → doğrula → PDF (PyMuPDF): tek sayfa, dikey A4 (ortada kat planı, üstte ön ve
arka, altta sol ve sağ görünüş; D-31 madde 12). DXF'in öteki çizimleri (net alanlar, saha montaj planı, teknik özellikler) PDF'e girmez.
Blok düzeni Yan Verandalı 6×8,5 (v1.4.3) örneğiyle aynıdır:
  - Üst seviye malzeme blokları: BOM_<kod>_… ; INSERT üzerinde AI_BOM XData = [kod, ANA|KOPYA|MONTAJ]
  - Kapı/pencere doğramaları pano bloğu içinde ayrı BOM_P0x_/BOM_K0x_ INSERT'idir (ayrıca sayılır)
  - Montaj kopyası MNT_ önekli bloklarla; standart dışı panolar mor (renk 6) ve gerçek boy ölçülü
Kaynak doğrama blokları (Güncel Şablon 2024) onaylı referans DXF'ten aktarılır; ölçeklenmez.
"""
from __future__ import annotations
import json, math, time, hashlib, csv
from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf import bbox as ebbox, units
from ezdxf.math import BoundingBox2d, Matrix44
from ezdxf.addons import Importer
from ezdxf.enums import TextEntityAlignment
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, pymupdf
try:
    import pymupdf as fitz
except ImportError:  # eski PyMuPDF
    import fitz
from shapely.geometry import box
from shapely.prepared import prep

from . import geometry as G
from . import veranda as VR
from .katalog import Katalog, pencere_turu

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
PENCERE_UST_KOTU = G.PENCERE_UST_KOTU_CM   # 200: 250 cm duvarda lento 50; yükseklik değişince üst kot sabit tutulur (çıkarım, teyit bekliyor)

PENCERE_KAYNAK = {   # olcu: (kaynak blok, doğal yön, bbox)
    "120x120": ("kaynak-pencere-120120", "V", (53365.182, 8072.861, 53397.006, 8192.861)),
    "60x40":   ("kaynak-pencere-6040",   "V", (53358.249, 7932.278, 53385.862, 7992.278)),
    "120x180": ("kaynak-pencere-120180", "H", (53839.874, 6682.0,   53959.874, 6713.823)),
}
PENCERE_YAZI_CM_HARF = 120 / len("120/120")   # BK-13: 120x120 bloğunda ölçü yazısının harf başına düşen sembol boyu; yeni ölçüde yazı boyu buna göre
IC_KAPI_VARYANT = {   # kanonik V çerçevesi (pano +y, kalınlık +x), 125,5 pano, 82 açıklık
    "SOL_UST": ((7918.93, -54227.719), 90.0, 1.0),
    "SOL_ALT": ((7918.93, 54353.219), 90.0, -1.0),
    "SAG_ALT": ((-7912.93, 54353.219), 270.0, 1.0),
    "SAG_UST": ((-7912.93, -54227.719), 270.0, -1.0),
}
DIS_KAPI_KAYNAK = ("kaynak-dis-kapi", (-54272.601, -7068.569), 97.0, 54287.421, 0.57)
# D-31 madde 6 (Lokman, 29 Ekim 2026 11:21–11:23): banyo ve WC'nin 60×40 penceresi görünüşte vasistas, tek kanat, üstten açılır ("yukarıdan
# aşağıya doğru açılır, yana doğru değil"); sembol Lokman'ın pencere föyündeki 58 × 38 vasistas: kasa, 3 cm içeride kanat, köşelerde gönye
# çizgisi, kanadın alt köşelerinden üst ortasına kesik açılım çizgisi (kırmızı, kaynak ön pencere bloğundaki gibi). Blok cm, 60 × 40.
VASISTAS_OLCULERI = ("60x40",)
# D-31 madde 9 (Lokman, 29 Ekim 2026 11:55: "arka görünüşte ... sağ taraftaki direk mi eksik"): taşan verandanın kolonu görünüşte soluk gri
# dolgulu; gövdenin köşesiyle aynı hizadaki kolon (TK-02 arka) duvarın köşe çizgileriyle çakışıp görünmüyordu.
VERANDA_KOLON_DOLGU = 9
VASISTAS_BLOK = ("on-vasistas", 60.0, 40.0, 3.0)        # ad, doğal en, boy, kasa–kanat payı
# D-31 madde 11 (Lokman, 29 Ekim 2026 11:57: "arka verandadaki pencere aslında sürgülü kapı gibi kullanılıyor"): İş Emri'nde
# `acilis: "surgulu"` yazan pencere görünüşte sürgülü; sembol Lokman'ın föyündeki 197,5 × 197,5 sürgülü kapıdan: çift kasa, ortada bindirmeli
# iki kanat, sabit kanatta cam işareti, sürülen kanatta yön oku (kırmızı, açılım çizgisi gibi). Blok cm, 120 × 180; ölçü ve pano değişmez.
SURGULU_BLOK = ("on-surgulu", 120.0, 180.0, 3.0)          # ad, doğal en, boy, kasa payı
# D-31 madde 14 (Lokman, 29 Ekim 2026 13:14: "görünüşlerdeki sadece ön görünüşde ve sağ görünüşde kodları göster diğerlerinden sil"): düşey
# kot ölçüleri (duvar, tepe, pencere eşiği ve lentosu) yalnız ön ve sağ görünüşte; arka ve solda yatay ölçüler kalır.
KOT_GORUNUSLERI = ("on", "sag")

# D-31 madde 5 (Lokman, 29 Ekim 2026 11:14): aks çizgisi soluk gri (ACI 9) ve veranda kirişi gibi kesik (`VERANDA_KESIK`); okunabilirlik
AKS_KATMANI = ("AKS", 9, "VERANDA_KESIK")

# D-34 (Lokman, 30 Ekim 2026 14:45: "ölçü çizgilerini … beyaz sayfa üzerine daha belirgin bir renk yap", "rengi de mor olsun, yazı rengi genel
# ölçü rengi olsun, siyah olabilir"): görünüşlerin ölçüsü (ON_OLCU; önce açık mavi, ACI 4) ve girintili gövdenin dış parça ölçüsü
# (DIS_PARCA_OLCU) mor çizgiyle (ACI 193; ölçü çizgisi ve uzatma çizgisi de, `dim`), yazısı genel ölçününki (OLCULER, ACI 7: beyaz sayfada siyah).
OLCU_MOR = 193
OLCU_YAZI_RENGI = 7
MOR_OLCU_KATMANLARI = ("ON_OLCU", "DIS_PARCA_OLCU")
DIS_PARCA_PAYI = 30.0            # cm: dış parça ölçüsünün duvarın dış yüzünden uzaklığı (aks harfleri ve genel ölçünün içinde)

LAYERS = [
    AKS_KATMANI, ("AKS_YAZI", 4, "Continuous"), ("DIS_DUVAR_100", 30, "Continuous"), ("IC_DUVAR_60", 30, "Continuous"),
    ("KOSE_PROFIL_100", 8, "Continuous"), ("KOSE_PROFIL_60", 8, "Continuous"), ("IC_UCLU_H_60", 3, "Continuous"),
    ("PENCERE", 10, "Continuous"), ("IC_KAPILAR", 7, "Continuous"), ("ODA_ADLARI", 7, "Continuous"), ("OLCULER", 7, "Continuous"),
    ("OZEL_PANEL_OLCU_CM", 3, "Continuous"), ("VERANDA_PROFIL_100", 1, "VERANDA_KESIK"), ("VERANDA_DIKME", 1, "Continuous"),
    ("ACIK_SINIR", 8, "DASHED"), ("NET_ALAN_GEOMETRISI", 6, "Continuous"),
    ("MONTAJ_STANDART", 7, "Continuous"), ("MONTAJ_OZEL_PANO", 6, "Continuous"), ("MONTAJ_OZEL_OLCU", 6, "Continuous"), ("MONTAJ_YAZI", 4, "Continuous"),
    ("ON_GORUNUS", 7, "Continuous"), ("ON_DERZ", 8, "Continuous"), ("ON_DOGRAMA", 4, "Continuous"), ("ON_CATI", 7, "Continuous"),
    ("ON_TOPUK", 1, "Continuous"), ("ON_OLCU", OLCU_MOR, "Continuous"), ("ON_YAZI", 7, "Continuous"),
    ("CATI_GORUNUS", 7, "Continuous"), ("CATI_OLCU", 4, "Continuous"), ("CATI_YAZI", 7, "Continuous"),
    ("PORTMAN_INFO", 7, "Continuous"), ("OZELLIK_TABLOSU", 7, "Continuous"),
]


AKS_KADEME_CM = 22.0   # İE-17 PR-2: birbirine yazı boyundan yakın iki aksın ikincisinin adı bu kadar dışarıda (AP-15 ve AP-22'de 5 cm arayla
                       # ek aks; TK-03'te 1,2 cm: "2" ile "1′" üst üste biniyordu)
AKS_YAKIN_CM = 18.0


def _kademe(akslar) -> list[int]:
    """Aks adlarının kademesi: önceki aksa `AKS_YAKIN_CM`'den yakın aksın adı bir kademe dışarı (önceki kademedeyse içeri). Yakın aks yoksa
    hepsi 0 (çizim aynen)."""
    out = []
    for i, v in enumerate(akslar):
        out.append(1 - out[-1] if i and v - akslar[i - 1] < AKS_YAKIN_CM else 0)
    return out


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
        katalog.yukseklik_cm = float(plan.is_emri["yapi"].get("duvar_yuksekligi_cm", 250))   # 250 / 280 / 300 (D-14; kur() başkasını reddeder)
        self.h_blok_adi_dis = None
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
        self.bolgeler: dict[str, list[str]] = {}     # D-31 madde 12: A4 bayi sayfasının bölgeleri (ad → varlık handle'ları)

    def _bolge(self, ad: str, n0: int) -> None:
        """`n0`'dan sonra çizilen varlıklar A4 bayi sayfasının `ad` bölgesi (handle'lar kaydedilip yeniden açılan DXF'te aynı)."""
        self.bolgeler.setdefault(ad, []).extend(e.dxf.handle for e in list(self.msp)[n0:])

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

    def _pencere_blok(self, olcu):
        """(sarmalayıcı blok adı, malzeme kodu, kaynak blok, doğal yön, kutu). Bugünkü üç ölçü `_dograma_bloklari`'nın bloğu (aynen);
        BK-13: başka ölçüde kaynak 120x120 (en ≤ 60 ise 60x40) sembolü duvar boyunca en'e ölçeklenir (kalınlık aynı; yazı boyu harf başına
        120x120'deki sembol boyuyla sınırlı, dar pencerede küçülür), ölçü yazısı "en/boy" olur. Kod ilk kullanımda tahsis edilir (yalnız bugünkü üç ölçüyü kullanan çizimde yeni kod yok)."""
        if olcu in PENCERE_KAYNAK:
            src, nat, bb = PENCERE_KAYNAK[olcu]; name, kod = self.dograma[olcu]
            return name, kod, src, nat, bb
        pk = G.pencere_kurali(olcu)
        temel = "60x40" if pk.en <= 60 else "120x120"
        tsrc, nat, bb = PENCERE_KAYNAK[temel]; k = pk.en / G.PENCERE_OLCULERI[temel][0]
        bb = (bb[0], bb[1] * k, bb[2], bb[3] * k)                  # doğal yön V: duvar boyu +y
        src = f"kaynak-pencere-{pk.en}x{pk.boy}"
        if olcu not in self.dograma:
            kblk = self.doc.blocks.new(src)
            for e in self.doc.blocks.get(tsrc):
                c = e.copy()
                if c.dxftype() == "TEXT":                         # yazı harf başına 120x120'deki kadar sembol boyu alır: dar pencerede küçülür, taşmaz (geometri hakemi, 23 Ekim)
                    x, y, z = c.dxf.insert; c.dxf.insert = (x, y * k, z); c.dxf.text = yazi = f"{pk.en}/{pk.boy}"
                    c.dxf.height *= min(1.0, pk.en / len(yazi) / PENCERE_YAZI_CM_HARF)
                else:
                    c.transform(Matrix44.scale(1.0, k, 1.0))
                kblk.add_entity(c)
            kod = self.kat.pencere(pk.en, pk.boy, pk.esik); name = f"BOM_{kod}_PENCERE_{pk.en*10}x{pk.boy*10}"
            self.doc.blocks.new(name).add_blockref(src, (0, 0), dxfattribs={"layer": "PENCERE"})
            self.dograma[olcu] = (name, kod)
        name, kod = self.dograma[olcu]
        return name, kod, src, nat, bb

    def _pencere_yazi_ters(self, olcu: str, rot: float) -> bool:
        """D-29 (Lokman, 29 Ekim 2026: "önden bakınca arkadaki yatak odası 1'in 120/180 yazısı ters kalıyor"): pencereli pano `rot` ile
        konunca ölçü yazısı baş aşağı (90° … 270°, sağdan ya da alttan okunmuyor) mu? Bütün çizimlerde (P6001 dahil; D-29 madde 6)."""
        _, _, src, nat, _ = self._pencere_blok(olcu)
        t0 = next((e.dxf.rotation for e in self.doc.blocks.get(src) if e.dxftype() == "TEXT"), None)
        if t0 is None:
            return False
        a = (rot + (0.0 if nat == "V" else 270.0) + t0) % 360.0
        return 90.0 + 1e-6 < a <= 270.0 + 1e-6

    def _pencere_ters_blok(self, olcu: str) -> str:
        """Pencere bloğunun ölçü yazısı kendi ortası çevresinde 180° çevrilmiş eşi (sembol aynı; ad `_Y`, malzeme kodu aynı)."""
        dname, _, src, _, _ = self._pencere_blok(olcu)
        ad = dname + "_Y"
        if ad not in self.doc.blocks:
            kblk = self.doc.blocks.new(src + "-y")
            for e in self.doc.blocks.get(src):
                c = e.copy()
                if c.dxftype() == "TEXT":
                    orta = ebbox.extents([e]).center
                    c.dxf.rotation = (c.dxf.rotation + 180.0) % 360.0
                    c.set_placement((orta.x, orta.y), align=TextEntityAlignment.MIDDLE_CENTER)
                kblk.add_entity(c)
            self.doc.blocks.new(ad).add_blockref(src + "-y", (0, 0), dxfattribs={"layer": "PENCERE"})
        return ad

    def _dis_kapi_blok(self, w):
        key = f"dis{int(w)}"
        if key not in self.dograma:
            kod = self.kat.kapi(w, True); name = f"BOM_{kod}_DIS_KAPI_ACIKLIK{int(w*10)}"
            self.doc.blocks.new(name).add_blockref("kaynak-dis-kapi", (0, 0), dxfattribs={"layer": "IC_KAPILAR", "xscale": w / 97.0})
            self.dograma[key] = (name, kod)
        return self.dograma[key]

    def _h_blok_dis(self):
        """İE-11: dış duvardaki T birleşimi (3'lü H dış). Kaynak blok yok; şematik gövde (dış kalınlık × iç kalınlık)."""
        if self.h_blok_adi_dis:
            return
        kod = self.kat.baglanti("uclu_h_dis"); self.h_blok_adi_dis = f"BOM_{kod}_UCLU_H_DIS_{G._mm(G.T_DIS)}x{G._mm(G.T_IC)}"; self.h_kod_dis = kod
        blk = self.doc.blocks.new(self.h_blok_adi_dis)
        # D-29 (Lokman, 29 Ekim 2026: "yeşil kutular ... bizde öyle bir şey yok"): kutu çizilmez. Gövde kapalı `DIS_UCLU_H_GOVDE` katmanında
        # kalır: sayım (BOM, doğrulama) INSERT'ten, IFC'deki parçanın yeri bloğun kutusundan (`ifc_uret.hazirla`)
        if "DIS_UCLU_H_GOVDE" not in self.doc.layers:
            self.doc.layers.add("DIS_UCLU_H_GOVDE", color=3, linetype="Continuous").off()
        x0, y0, x1, y1 = -G.T_DIS / 2.0, -G.T_IC / 2.0, G.T_DIS / 2.0, G.T_IC / 2.0
        blk.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": "DIS_UCLU_H_GOVDE", "color": 256})
        if G.katman("DIS_UCLU_H_100") not in self.doc.layers:          # katman yalnız dış üçlü H varken açılır (eski DXF'ler değişmez)
            self.doc.layers.add(G.katman("DIS_UCLU_H_100"), color=3, linetype="Continuous")

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

    def pano_blok(self, p: G.Pano, yazi_ters: bool = False):
        """(blok adı, çerçeve, malzeme kodu). Kanonik V çerçevesi: pano +y boyunca, kalınlık +x; dış kapı H çerçevesi. `yazi_ters` (D-29):
        pencerenin ölçü yazısı 180° çevrilmiş blok (`_pencere_ters_blok`), ad `_Y` ile biter."""
        d = p.duvar; L = p.boy; t = 2 * d.h; dis = d.tur == "dis"
        ac = p.acilim
        kind = "DOLU" if ac is None else {"pencere": {"120x120": "P01", "120x180": "P02", "60x40": "P03"}.get(ac.olcu),
                                         "ic_kapi": "K01", "dis_kapi": "K02", "gecis": "OPEN"}[ac.tur]
        if ac is not None and ac.tur == "pencere" and kind is None:
            kind = pencere_turu(ac.olcu)                            # BK-13: üç ölçü dışındaki pencere
        kod = self.kat.pano(dis, L, kind)
        var = ""
        if ac is not None and ac.tur == "ic_kapi":
            var = ac.varyant or G.kapi_varyanti(d, ac); ac.varyant = var
        # İE-11 `dizilim.kapi: mantik`: dış kapı sembolü kaynakta sağ menteşeli (açılma yönünde yürürken); "sol" ise aynalanır. Eski yol: sembol sabit
        dis_ayna = bool(ac is not None and ac.tur == "dis_kapi" and ac.mentese == "sol"
                        and (self.plan.is_emri.get("yapi", {}).get("dizilim") or {}).get("kapi") == "mantik")
        if dis_ayna:
            var = "SOL"
        kay = ac.kayma if ac is not None else 0.0                  # İE-11: boşluk panoda kaydırılmışsa blok geometrisi farklıdır
        yazi_ters = yazi_ters and ac is not None and ac.tur == "pencere"
        name = f"BOM_{kod}_{mm_tag(L)}_{'DIS' if dis else 'IC'}_{kind}" + (f"_{var}" if var else "") \
            + (f"_KAY{'M' if kay < 0 else 'P'}{mm_tag(abs(kay))}" if abs(kay) > 1e-9 else "") + ("_Y" if yazi_ters else "")
        frame = "H" if (ac is not None and ac.tur == "dis_kapi") else "V"
        if name in self.doc.blocks:
            return name, frame, kod
        blk = self.doc.blocks.new(name)
        if ac is None:
            self._rect(blk, 0, 0, t, L); return name, frame, kod
        w = ac.genislik; s = (L - w) / 2.0 + kay                  # kay 0 → eski değer bit bit
        if ac.tur == "pencere":
            dname, _, src, nat, bb = self._pencere_blok(ac.olcu)
            if yazi_ters:
                dname = self._pencere_ters_blok(ac.olcu)
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
            blk.add_blockref(dname, (ix, iy + (L - 125.5) / 2.0 + kay), dxfattribs={"rotation": rot, "xscale": xs, "layer": "IC_KAPILAR"})
        elif ac.tur == "gecis":
            self._rect(blk, 0, 0, t, s); self._rect(blk, 0, s + w, t, L)
            blk.add_line((0, s), (t, s + w), dxfattribs={"layer": "IC_KAPILAR", "linetype": "DASHED"})   # kapısız geçiş işareti
            blk.add_line((0, s + w), (t, s), dxfattribs={"layer": "IC_KAPILAR", "linetype": "DASHED"})
        else:  # dış kapı: H çerçevesi (pano +x, kalınlık +y, kanat +y'ye açılır)
            src, (ix, iy), w0, SRC_LEFT, MARGIN = DIS_KAPI_KAYNAK; dname, _ = self._dis_kapi_blok(w)
            self._rect(blk, 0, 0, s, t); self._rect(blk, s + w, 0, L, t)
            xs = w / w0
            x_ins = s + xs * (MARGIN - SRC_LEFT)
            if dis_ayna:                                            # boşluk ortasına göre ayna: x' = 2·orta − x, xscale −1
                blk.add_blockref(dname, (2 * s + w - x_ins, iy), dxfattribs={"rotation": 0.0, "xscale": -1.0, "layer": "IC_KAPILAR"})
            else:
                blk.add_blockref(dname, (x_ins, iy), dxfattribs={"rotation": 0.0, "layer": "IC_KAPILAR"})
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

    def paylar(self) -> dict:
        """BK-14: taşan verandanın gövde kutusu (0, 0, W, H) dışına çıktığı pay (cm; alt, ust, sol, sag). Veranda yoksa hepsi 0."""
        W, H = self.plan.W, self.plan.H
        rs = [v["rect"] for v in self.plan.dis_verandalar]
        return {"alt": max([0.0] + [-r[1] for r in rs]), "ust": max([0.0] + [r[3] - H for r in rs]),
                "sol": max([0.0] + [-r[0] for r in rs]), "sag": max([0.0] + [r[2] - W for r in rs])}

    def ciz_plan(self, ox: float, oy: float, rol: str, baslik: str, altbaslik: str):
        plan, msp = self.plan, self.msp
        W, H = plan.W, plan.H
        py = self.paylar()
        alt, ust, sol, sag = py["alt"], py["ust"], py["sol"], py["sag"]
        aks, montaj = (rol == "ANA"), (rol == "MONTAJ")
        n0 = len(msp)
        dolu: list = []                                       # bu planda konmuş özel pano ölçü yazılarının kutuları (`_ozel_olcu`)
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
                        if self._pencere_yazi_ters(p.acilim.olcu, rot):
                            name, frame, kod = self.pano_blok(p, yazi_ters=True)
                else:
                    n = p.acilim.icine_normal
                    if d.yon == "x": ins, rot = ((r[0], r[1]), 0.0) if n == "+y" else ((r[2], r[3]), 180.0)
                    else:            ins, rot = ((r[2], r[1]), 90.0) if n == "-x" else ((r[0], r[3]), 270.0)
                self.yerlestir(name, kod, ins, rot, layer, rol, ox, oy)
                if montaj and not standart:
                    self._ozel_olcu(d, r, W, H, ox, oy, "MONTAJ_OZEL_OLCU", dolu)
                if montaj and p.acilim and p.acilim.tur == "pencere":
                    g = p.gap(); cx, cy = (g[0] + g[2]) / 2, (g[1] + g[3]) / 2
                    pkr = G.pencere_kurali(p.acilim.olcu); en, boy = pkr.en, pkr.boy; pk = self.dograma[p.acilim.olcu][1]
                    u = 28 if pkr.pano == 1 else 68                  # BK-13: 251'lik panonun ölçüsü (mor, +40) yazının yerinde; yazı içeri kayar
                    off = u if d.yon == "x" else 0; offx = 0 if d.yon == "x" else u
                    if d.yon == "y" and d.c > W / 2: offx = -u
                    if d.yon == "x" and d.c > H / 2: off = -u
                    self.text(f"{pk} {en}×{boy} cm", (cx + ox + offx, cy + oy + off), 11, "MONTAJ_YAZI", rot=(90.0 if d.yon == "y" else 0.0))
        for k in plan.koseler:
            name, kod = self.kose_blok(k)
            layer = "MONTAJ_STANDART" if montaj else (G.katman("KOSE_PROFIL_100") if k.tur == "dis" else G.katman("KOSE_PROFIL_60"))
            self.yerlestir(name, kod, (k.rect[0], k.rect[1]), 0.0, layer, rol, ox, oy)
        for hb in plan.h_baglantilar:
            if hb.tur == "dis":                                     # İE-11
                self._h_blok_dis()
                self.yerlestir(self.h_blok_adi_dis, self.h_kod_dis, (hb.x, hb.y), hb.rot, "MONTAJ_STANDART" if montaj else G.katman("DIS_UCLU_H_100"), rol, ox, oy)
                continue
            self.yerlestir(self.h_blok_adi, self.h_kod, (hb.x, hb.y), hb.rot, "MONTAJ_STANDART" if montaj else G.katman("IC_UCLU_H_60"), rol, ox, oy)
        # veranda dikmeleri
        if plan.dikmeler:
            kod = self.kat.baglanti("dikme"); name = f"BOM_{kod}_VERANDA_DIKME_100x100"
            if name not in self.doc.blocks: self._rect(self.doc.blocks.new(name), 0, 0, 10, 10)
            for (x0, y0, x1, y1) in plan.dikmeler:
                self.yerlestir(name, kod, (x0, y0), 0.0, "MONTAJ_STANDART" if montaj else "VERANDA_DIKME", rol, ox, oy)
        # veranda profili (her açık kenar bir blok: dış yüz + 10 cm içeri, kesik çizgi)
        dis_ad = {v["ad"] for v in plan.dis_verandalar}
        for ad, m in plan.mahaller.items():
            if not m.acik or ad in dis_ad: continue         # BK-14: taşan verandanın kenarları aşağıda (gövde çizgisi profil değil)
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
        for v in plan.dis_verandalar:                       # BK-14: taşan veranda; iç çizgi kirişin iç yüzü (Plan `kirisler`)
            for j, ((x0, y0, x1, y1), (kx0, ky0, kx1, ky1)) in enumerate(zip(v["kenarlar"], v["kirisler"])):
                vertical = abs(x0 - x1) < 1e-9
                boy = (y1 - y0) if vertical else (x1 - x0)
                rol_ = "ON" if j == 0 else "YAN"            # profilin rolü kenardan (dış kenar ön profil), yönden değil: sol / sağ verandada dış kenar düşey
                kod = self.kat.veranda_profil(boy, rol_)
                # kenar sırası (dış, yan 1, yan 2) adda: iki yanın boyu aynı, iç çizgisi zıt yönde (geometri hakemi, 27 Ekim)
                name = f"BOM_{kod}_VERANDA_{rol_}_{mm_tag(boy)}_{v['cephe'].upper()}_{('DIS', 'YAN1', 'YAN2')[j]}"
                if name not in self.doc.blocks:
                    blk = self.doc.blocks.new(name)
                    ic = [(kx0, ky0, kx1, ky1)]
                    if vertical:
                        sx = (kx1 - x0) if abs(kx0 - x0) < 1e-9 else (kx0 - x0)
                        blk.add_line((0, 0), (0, boy), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                        blk.add_line((sx, 0), (sx, boy), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                    else:
                        sy = (ky1 - y0) if abs(ky0 - y0) < 1e-9 else (ky0 - y0)
                        blk.add_line((0, 0), (boy, 0), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                        blk.add_line((0, sy), (boy, sy), dxfattribs={"layer": "0", "color": 256, "lineweight": 25})
                self.yerlestir(name, kod, (x0, y0), 0.0, "MONTAJ_STANDART" if montaj else "VERANDA_PROFIL_100", rol, ox, oy)
        for (x0, y0, x1, y1) in self._merge_lines(plan.acik_sinir_cizgileri):
            msp.add_line((x0 + ox, y0 + oy), (x1 + ox, y1 + oy), dxfattribs={"layer": "ACIK_SINIR"})
        # mahaller
        etiketler, yerlesecek, nis_yazilari, zincir_h = {}, [], {}, set()
        for ad, m in plan.mahaller.items():
            poly = m.poly.simplify(0.0)
            if rol == "ANA":
                e = msp.add_lwpolyline([(x + ox, y + oy) for x, y in list(poly.exterior.coords)[:-1]], close=True, dxfattribs={"layer": "NET_ALAN_GEOMETRISI"})
                e.set_xdata("PORTMAN_ROOM", [(1000, ad)])
            # etiket, mahalin en büyük dikdörtgen parçasının (aks gridinde) ortasına; L biçimli mahalde koridora değil geniş parçaya
            if m.rects:
                r_big = max(m.rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
                etiket_poly = box(G.X(r_big[0]), G.Y(r_big[1]), G.X(r_big[2]), G.Y(r_big[3])).intersection(poly)
            else:                                           # BK-14: taşan veranda (ızgarada değil)
                etiket_poly = poly
            if etiket_poly.is_empty or etiket_poly.area < 1.0: etiket_poly = poly
            bx0, by0, bx1, by1 = etiket_poly.bounds
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            h = 28 if poly.area > 60000 else 22
            if montaj: h = 18
            h, rot = self._etiket_sigdir(ad, etiket_poly, h)
            etiketler[ad] = (cx, cy, h, rot)
            if montaj:
                self.text(ad, (cx + ox, cy + oy), h, "MONTAJ_YAZI", rot=rot)
            else:                                           # D-31 madde 15 (Patron 13:21): akslı kat planında da her bölmenin adının altında net m²;
                yerlesecek.append((ad, m, poly, cx, cy, h, rot))   # yazılar planın sonunda, ölçülere binmeyecek yere (`_mahal_etiketleri`)
        if aks and G.ana_akslar("x") is not None:          # İE-11: aks tablosu → ana akslar (tam pano + ek aks + uç); ek aks "2′" gibi, numara kaydırmaz
            for x, ad, k in zip(G.ana_akslar("x"), G.ana_aks_etiketleri("x"), _kademe(G.ana_akslar("x"))):
                msp.add_line((x + ox, -35 - alt + oy), (x + ox, H + 41 + ust + oy), dxfattribs={"layer": "AKS"})
                self.text(ad, (x + ox, H + 60 + AKS_KADEME_CM * k + ust + oy), 14, "AKS_YAZI")
            for y, ad, k in zip(G.ana_akslar("y"), G.ana_aks_etiketleri("y"), _kademe(G.ana_akslar("y"))):
                msp.add_line((-35 - sol + ox, y + oy), (W + 35 + sag + ox, y + oy), dxfattribs={"layer": "AKS"})
                self.text(ad, (-53 - AKS_KADEME_CM * k - sol + ox, y + oy), 14, "AKS_YAZI")
        elif aks:
            for i in range(int(plan.nx * 2) + 1):
                if i % 2: continue
                x = G.X(i / 2)
                msp.add_line((x + ox, -35 - alt + oy), (x + ox, H + 41 + ust + oy), dxfattribs={"layer": "AKS"})   # BK-14: taşan veranda payı
                self.text(chr(ord("A") + i // 2), (x + ox, H + 60 + ust + oy), 14, "AKS_YAZI")
            for j in range(int(plan.ny * 2) + 1):
                if j % 2: continue
                y = G.Y(j / 2)
                msp.add_line((-35 - sol + ox, y + oy), (W + 35 + sag + ox, y + oy), dxfattribs={"layer": "AKS"})
                self.text(str(j // 2 + 1), (-53 - sol + ox, y + oy), 14, "AKS_YAZI")
        # ölçüler
        self.dim((ox, oy), (W + ox, oy), (0, -85 - alt + oy), 0)
        self.dim((ox, oy), (ox, H + oy), (-115 - sol + ox, 0), 90)
        if alt or ust:                                      # BK-14: verandalarla genel derinlik
            self.dim((ox, -alt + oy), (ox, H + ust + oy), (-160 - sol + ox, 0), 90)
        if sol or sag:
            self.dim((-sol + ox, oy), (W + sag + ox, oy), (0, -130 - alt + oy), 0)
        if not montaj:
            if G.ana_akslar("x") is not None:               # İE-11
                xs, ys = G.ana_akslar("x"), G.ana_akslar("y")
            else:
                xs = [G.X(i / 2) for i in range(0, int(plan.nx * 2) + 1, 2)] + ([G.X(plan.nx)] if int(plan.nx * 2) % 2 else [])
                ys = [G.Y(j / 2) for j in range(0, int(plan.ny * 2) + 1, 2)] + ([G.Y(plan.ny)] if int(plan.ny * 2) % 2 else [])
            n_z = len(msp)
            for a, b in zip(xs, xs[1:]): self.dim((a + ox, H + oy), (b + ox, H + oy), (0, H + 102 + ust + oy), 0)
            for a, b in zip(ys, ys[1:]): self.dim((W + ox, a + oy), (W + ox, b + oy), (W + 81 + sag + ox, 0), 90)
            zincir_h = {e.dxf.handle for e in list(msp)[n_z:]}
            if aks:
                self._bolge("aks_zinciri", n_z)                   # D-31 madde 13: A4 sayfasının planında yok
            if plan.girintili:                                  # D-34: kapalı gövdenin her dış parçası mor ölçüyle
                self._dis_parca_olculeri(ox, oy)
            for v in plan.dis_verandalar:                   # BK-14: taşan verandanın eni ve derinliği
                vx0, vy0, vx1, vy1 = v["rect"]
                if v["cephe"] in ("on", "arka"):
                    self.dim((vx0 + ox, (vy0 if v["cephe"] == "on" else vy1) + oy), (vx1 + ox, (vy0 if v["cephe"] == "on" else vy1) + oy),
                             (0, (vy0 - 40 if v["cephe"] == "on" else vy1 + 40) + oy), 0)
                    self.dim((vx1 + ox, vy0 + oy), (vx1 + ox, vy1 + oy), (vx1 + 40 + ox, 0), 90)
                else:
                    self.dim(((vx0 if v["cephe"] == "sol" else vx1) + ox, vy0 + oy), ((vx0 if v["cephe"] == "sol" else vx1) + ox, vy1 + oy),
                             ((vx0 - 40 if v["cephe"] == "sol" else vx1 + 40) + ox, 0), 90)
                    self.dim((vx0 + ox, vy1 + oy), (vx1 + ox, vy1 + oy), (0, vy1 + 40 + oy), 0)
            for d in plan.duvarlar:
                for p in d.panolar:
                    if abs(p.boy - G.MOD) < 1e-6: continue
                    self._ozel_olcu(d, p.rect(), W, H, ox, oy, "OZEL_PANEL_OLCU_CM", dolu)
            for ad, m in plan.mahaller.items():
                if not m.acik or not m.cells: continue      # taşan veranda (BK-14) yukarıda ölçülü
                if plan.girintili: continue                 # D-34: açık mahalin eni ve derinliği dış parça ölçüsünde (aynı yer iki kez ölçülmez)
                us = [u for u, v in m.cells]; vs = [v for u, v in m.cells]
                x0, x1 = G.X(min(us) / 2), G.X((max(us) + 1) / 2); y0, y1 = G.Y(min(vs) / 2), G.Y((max(vs) + 1) / 2)
                # dar açık mahalde (tek pano şeridi) ölçü çizgisi plan dışına alınır; yazılarla çakışmasın
                dar = (x1 - x0) < 2 * G.MOD - 1e-6
                son_x = G._AKS["x"][-1] if G._AKS["x"] is not None else G.X(plan.nx)    # İE-11: tablo kipinde son aks tablodan (ek aks ızgarayı büyütmez)
                son_y = G._AKS["y"][-1] if G._AKS["y"] is not None else G.Y(plan.ny)
                if dar and y0 <= G.Y(0) + 1e-6: yb = -45.0
                elif dar and y1 >= son_y - 1e-6: yb = H + 30.0
                else: yb = y0 + 55.0
                self.dim((x0 + ox, y0 + oy), (x1 + ox, y0 + oy), (0, yb + oy), 0)
                if dar and x1 >= son_x - 1e-6: xb = W + 40.0
                elif dar and x0 <= G.X(0) + 1e-6: xb = -80.0
                else: xb = x0 + 33.0
                self.dim((x0 + ox, y0 + oy), (x0 + ox, y1 + oy), (xb + ox, 0), 90)
                nis_yazilari[ad] = f"{fmt((x1 - x0) / G.MOD)} x {fmt((y1 - y0) / G.MOD)} aks modülü"   # net alan planında adın üstünde (`_mahal_etiketleri`)
        if montaj:
            self.text("Mor: standart dışı pano (gerçek uçtan uca boy ölçülü) | Beyaz: standart 125,5 cm pano | Ölçüler cm", (W / 2 + ox, -145 - alt + oy), 13, "MONTAJ_YAZI")
            self.text("Pencere etiketi: malzeme kodu + en×yükseklik | Montaj kopyası BOM'a sayılmaz", (W / 2 + ox, -175 - alt + oy), 13, "MONTAJ_YAZI")
        if yerlesecek:
            self._mahal_etiketleri(yerlesecek, nis_yazilari, n0, ox, oy, aks, zincir_h)
        if aks:                                               # D-31 madde 12–13: A4 sayfasının kat planı, başlıksız (antet sayfanın üstünde) ve
            zincir = set(self.bolgeler.get("aks_zinciri", []))  # 125,5'lik aks ölçü zinciri olmadan
            self.bolgeler["plan"] = [e.dxf.handle for e in list(msp)[n0:] if e.dxf.handle not in zincir]
        self.text(baslik, (W / 2 + ox, H + 206 + ust + oy), 24, "ODA_ADLARI")
        # İE-11: dar yapıda (PK-01 600 cm) alt başlık komşu plana taşıyordu; yeni anahtarlı İş Emri'nde yazı sığacak boya iner (eski yol 15 sabit)
        h_alt = 15 if not G.yeni_anahtar_var(plan.is_emri) else max(9, min(15, int((W + 200) / (max(1, len(altbaslik)) * 0.75))))   # planlar W+300 aralıklı; harf ≈ 0,75·h
        self.text(altbaslik, (W / 2 + ox, H + 168 + ust + oy), h_alt, "ODA_ADLARI")

    _FONT = None

    @classmethod
    def yazi_eni(cls, s: str, h: float) -> float:
        """DejaVu Sans ile CAD yüksekliği h (büyük harf yüksekliği) olan yazının gerçek eni (cm)."""
        if cls._FONT is None:
            import pymupdf
            cls._FONT = pymupdf.Font(fontfile=str(FONT_PATH))
        return cls._FONT.text_length(s, fontsize=h / 0.729)   # DejaVu büyük harf yüksekliği ≈ 0,729 em

    ETIKET_ADIM_CM = 5.0

    def _mahal_etiketleri(self, yerlesecek, nis_yazilari: dict, n0: int, ox: float, oy: float, aks: bool, zincir: set) -> None:
        """Kat planı ve net alan planında mahal adı, altında net m² (D-31 madde 15; Patron 13:21: "SALON yazısının altına m² ... tüm
        bölmeler için"). Yazı grubu mahalin içinde, ortasına en yakın ve bu planın ölçü çizgilerine, ölçü yazılarına ve öteki yazılarına
        binmeyen yere konur (pencere ölçü yazısı dahil); öyle yer yoksa yazı küçülür (en az 14), yine yoksa en az binen yer seçilir; hiç sığmazsa
        ortada 14 boyla ve plan uyarısıyla. Kapının kanat ve yay kutusundan
        ikinci öncelikte kaçınılır. Aks ölçü zinciri (`zincir`; A4'te yok, madde 13) aks çizgisi gibi engel sayılmaz. 90° döndürülmüş yazıda m² okuma yönünde
        altta (sağda). Açık nişin "1 x 1 aks modülü" yazısı yalnız net alan planında, adın üstünde; nişten geniş olduğundan engeli ikinci
        önceliktedir. Akslı kat planında (A4) yazılmaz: m²'ye yer açar, aks bilgisi A4'te yok (madde 13)."""
        sert, yumusak = [], []
        for e in list(self.msp)[n0:]:
            t = e.dxftype()
            if e.dxf.handle in zincir: continue
            if t == "TEXT":
                sert.append(self._yazi_kutusu(e.dxf.text, e.dxf.align_point, e.dxf.height, e.dxf.rotation))
            elif t == "DIMENSION":
                for g in e.get_geometry_block():
                    if g.dxftype() == "LINE": sert.append(self._cizgi_kutusu(g.dxf.start, g.dxf.end))
                    elif g.dxftype() == "MTEXT": sert.append(self._yazi_kutusu(g.text, g.dxf.insert, g.dxf.char_height, g.dxf.get("rotation", 0.0)))
            elif t == "INSERT":
                for g in e.virtual_entities():
                    if g.dxftype() != "INSERT": continue
                    if g.dxf.layer == "IC_KAPILAR":
                        k = self._blok_kutusu(g)
                        if k: yumusak.append(k)
                    elif g.dxf.layer == "PENCERE":              # pencere ölçü yazısı ("120/180") verandaya bakan duvarda mahalin içine düşer (hakem, 29 Ekim)
                        sert.extend(self._pencere_yazilari(g))
        for ad, m, poly, cx, cy, h, rot in yerlesecek:
            alan = f"{m.alan_m2:.2f}".replace(".", ",") + " m²"
            nis = None if aks else nis_yazilari.get(ad)
            ic = poly.buffer(-3.0)
            x0, y0, x1, y1 = poly.bounds
            sinir = (x0 + ox - 200, y0 + oy - 50, x1 + ox + 200, y1 + oy + 50)
            s_yakin = [k for k in sert if self._kesisir(k, sinir)]
            y_yakin = [k for k in yumusak if self._kesisir(k, sinir)]
            adim = self.ETIKET_ADIM_CM
            adaylar = sorted(((x0 + i * adim, y0 + j * adim) for i in range(int((x1 - x0) / adim) + 1) for j in range(int((y1 - y0) / adim) + 1)),
                             key=lambda p: ((p[0] - cx) ** 2 + (p[1] - cy) ** 2, p))
            adaylar.insert(0, (cx, cy))
            ic = prep(ic)
            en_iyi = None
            for hh in sorted({max(14.0, h * f) for f in (1.0, 0.9, 0.8, 0.7, 0.0)}, reverse=True):
                grup0 = self._etiket_grubu(ad, alan, nis, 0.0, 0.0, hh, rot)       # yazı enleri bir kez; adaylarda kaydırılır
                for px, py_ in adaylar:
                    kutular = [(k[0] + px + ox, k[1] + py_ + oy, k[2] + px + ox, k[3] + py_ + oy) for k in grup0]
                    puan = (sum(self._ortusme(k, o) for k in kutular[:2] for o in s_yakin),
                            sum(self._ortusme(k, o) for k in kutular[:2] for o in y_yakin) + sum(self._ortusme(k, o) for k in kutular[2:] for o in s_yakin + y_yakin))
                    if en_iyi is not None and puan >= en_iyi[0]: continue
                    if not all(ic.contains(box(k[0] - ox, k[1] - oy, k[2] - ox, k[3] - oy)) for k in kutular[:2]): continue
                    en_iyi = (puan, px, py_, hh)
                    if puan == (0, 0): break
                if en_iyi and en_iyi[0][0] == 0: break
            if en_iyi is None:                                  # hiçbir aday mahale sığmadı: ortada en küçük boyla, uyarıyla (K16; hakem, 29 Ekim)
                u = f"{ad}: adı ve m²'si mahalin içine sığmadı; ortasına 14 boyla yazıldı, duvara taşabilir"
                if u not in self.plan.uyarilar: self.plan.uyarilar.append(u)
            px, py_, hh = (en_iyi[1], en_iyi[2], en_iyi[3]) if en_iyi else (cx, cy, 14.0)
            (ax, ay), (mx, my), np_ = self._etiket_yerleri(px, py_, hh, rot)
            self.text(ad, (ax + ox, ay + oy), hh, "ODA_ADLARI", rot=rot)
            self.text(alan, (mx + ox, my + oy), min(20, hh), "ODA_ADLARI", rot=rot)
            if nis: self.text(nis, (np_[0] + ox, np_[1] + oy), 13, "ODA_ADLARI", rot=rot)

    @classmethod
    def _pencere_yazilari(cls, ins) -> list:
        """Pencere bloğunun (iç içe: `BOM_P..` → kaynak pencere) yazılarının dünya kutuları."""
        out = []
        for y in ins.virtual_entities():
            if y.dxftype() == "INSERT":
                out.extend(cls._pencere_yazilari(y))
            elif y.dxftype() == "TEXT":
                bb = ebbox.extents([y])
                if bb.has_data: out.append((bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y))
        return out

    _KAPI_KUTULARI: dict = {}

    def _blok_kutusu(self, ins):
        """Kapı INSERT'inin dünya kutusu. Kapı blokları kaynak DXF'in kapısından, adı açıklığı taşır (`BOM_K01_IC_KAPI_ACIKLIK820`);
        blok kutusu ada göre bir kez hesaplanır (binlerce kısa çizgi, her planda yeniden ölçmek yavaş)."""
        onbellek = self._KAPI_KUTULARI
        ad = ins.dxf.name
        if ad not in onbellek:
            bb = ebbox.extents(self.doc.blocks[ad])
            onbellek[ad] = (bb.extmin, bb.extmax) if bb.has_data else None
        k = onbellek[ad]
        if k is None: return None
        m = ins.matrix44()
        pts = [m.transform((x, y, 0.0)) for x in (k[0][0], k[1][0]) for y in (k[0][1], k[1][1])]
        return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))

    @staticmethod
    def _etiket_yerleri(cx, cy, h, rot):
        """Ad, m² ve niş yazısının ortası: ad üstte, m² altta, niş yazısı adın üstünde (90°'de okuma yönünde: üst = −x)."""
        if rot: return (cx - 14, cy), (cx + 18, cy), (cx - 14 - h / 2 - 22, cy)
        return (cx, cy + 14), (cx, cy - 18), (cx, cy + 14 + h / 2 + 22)

    @classmethod
    def _etiket_grubu(cls, ad, alan, nis, cx, cy, h, rot):
        (ax, ay), (mx, my), (nx, ny) = cls._etiket_yerleri(cx, cy, h, rot)
        grup = [cls._yazi_kutusu(ad, (ax, ay), h, 90.0 if rot else 0.0), cls._yazi_kutusu(alan, (mx, my), min(20, h), 90.0 if rot else 0.0)]
        if nis: grup.append(cls._yazi_kutusu(nis, (nx, ny), 13, 90.0 if rot else 0.0))
        return grup

    @classmethod
    def _yazi_kutusu(cls, s, p, h, rot):
        """Ortaya hizalı yazının kutusu (0° ya da 90°)."""
        w = cls.yazi_eni(s, h) / 2
        return (p[0] - h / 2, p[1] - w, p[0] + h / 2, p[1] + w) if abs((rot or 0.0) % 180.0 - 90.0) < 1e-6 else (p[0] - w, p[1] - h / 2, p[0] + w, p[1] + h / 2)

    @staticmethod
    def _cizgi_kutusu(a, b, kalinlik=1.5):
        return (min(a[0], b[0]) - kalinlik, min(a[1], b[1]) - kalinlik, max(a[0], b[0]) + kalinlik, max(a[1], b[1]) + kalinlik)

    @staticmethod
    def _kesisir(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    @staticmethod
    def _ortusme(a, b):
        w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
        return w * h if w > 0 and h > 0 else 0.0

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

    OZEL_OLCU_UZAKLIK_CM = (40, 25, 70, 100)

    def _ozel_olcu(self, d, r, W, H, ox, oy, layer, dolu: list) -> None:
        """Standart dışı panonun ölçüsü, duvarın iç yanında panodan 40 cm uzakta. Yazısı bu planda daha önce konmuş bir özel pano ölçü
        yazısına biniyorsa ölçü çizgisi sırayla 25, 70, 100 cm'e çekilir (D-29 ek: TK-02 yatak odası 3'te 62,75 ile 125 üst üsteydi);
        hiçbiri boş değilse 40'ta kalır. Yazının yeri ölçü stilinden: çizginin üstünde (dimtad 1, dimgap 4, yükseklik 14); 90°'lik ölçüde solunda."""
        boy = (r[3] - r[1]) if d.yon == "y" else (r[2] - r[0])
        yari_en = self.yazi_eni(f"{boy:.2f}".rstrip("0").rstrip(".").replace(".", ","), 14) / 2 + 2
        ic = (1 if d.c < W / 2 else -1) if d.yon == "y" else (1 if d.c < H / 2 else -1)

        def kutu(u):
            if d.yon == "y":
                x = (r[2] + u if ic > 0 else r[0] - u) - 4 - 7
                return (x - 9, (r[1] + r[3]) / 2 - yari_en, x + 9, (r[1] + r[3]) / 2 + yari_en)
            y = (r[3] + u if ic > 0 else r[1] - u) + 4 + 7
            return ((r[0] + r[2]) / 2 - yari_en, y - 9, (r[0] + r[2]) / 2 + yari_en, y + 9)
        u = next((u for u in self.OZEL_OLCU_UZAKLIK_CM
                  if not any(k[0] < b[2] and b[0] < k[2] and k[1] < b[3] and b[1] < k[3] for k in [kutu(u)] for b in dolu)),
                 self.OZEL_OLCU_UZAKLIK_CM[0])
        dolu.append(kutu(u))
        if d.yon == "y":
            xd = r[2] + u if ic > 0 else r[0] - u; xk = r[0] if ic > 0 else r[2]
            self.dim((xk + ox, r[1] + oy), (xk + ox, r[3] + oy), (xd + ox, 0), 90, layer)
        else:
            yd = r[3] + u if ic > 0 else r[1] - u; yk = r[1] if ic > 0 else r[3]
            self.dim((r[0] + ox, yk + oy), (r[2] + ox, yk + oy), (0, yd + oy), 0, layer)

    def _dis_parca_olculeri(self, ox: float, oy: float) -> None:
        """D-34 (Lokman, 30 Ekim 2026 14:45: "mor ile çizdiğim yerleri de ölçeklendir rengi de mor olsun"): girintili gövdede (İE-24) kapalı
        gövdenin dış çizgisinin (`G.kapali_govde_cokgeni`: duvarların dış yüzü; balkon gibi açık mahal dışarıda) her düz parçası kendi dış
        yanında, yüzden `DIS_PARCA_PAYI` uzakta ölçülür (DIS_PARCA_OLCU; mor çizgi, siyah yazı çizginin ortasında, `dim`). Açık mahalin (balkon)
        aks ölçüsü bu planda yazılmaz: eni ve derinliği bu ölçülerde (`ciz_plan`). Dikdörtgen gövdede dış ölçü iki toplam
        ölçüdür; bu ölçü çizilmez (katman da açılmaz, eski çizimler aynen)."""
        from shapely.geometry.polygon import orient
        if "DIS_PARCA_OLCU" not in self.doc.layers:
            self.doc.layers.add("DIS_PARCA_OLCU", color=OLCU_MOR, linetype="Continuous")
        halka = list(orient(G.kapali_govde_cokgeni(self.plan), 1.0).exterior.coords)
        for (xa, ya), (xb, yb) in zip(halka, halka[1:]):
            if math.hypot(xb - xa, yb - ya) < 1.0:
                continue
            if abs(yb - ya) < 1e-6:                           # yatay parça; saat yönü tersinde dışarısı (0, −dx)
                y = ya - math.copysign(DIS_PARCA_PAYI, xb - xa)
                self.dim((min(xa, xb) + ox, ya + oy), (max(xa, xb) + ox, ya + oy), (0, y + oy), 0, "DIS_PARCA_OLCU")
            else:                                             # düşey parça; dışarısı (dy, 0)
                x = xa + math.copysign(DIS_PARCA_PAYI, yb - ya)
                self.dim((xa + ox, min(ya, yb) + oy), (xa + ox, max(ya, yb) + oy), (x + ox, 0), 90, "DIS_PARCA_OLCU")

    def dim(self, p1, p2, base, angle, layer="OLCULER"):
        base = (p1[0], base[1]) if angle == 0 else (base[0], p1[1])
        ozel = {"dimtxt": 14, "dimasz": 9, "dimexe": 6, "dimexo": 5, "dimdec": 2, "dimzin": 8, "dimdsep": ord(",")}
        if layer in MOR_OLCU_KATMANLARI:                          # D-34: çizgiler mor (ölçü bloğunun çizgileri 0 katmanında; renk açık yazılır), yazı siyah
            ozel.update(dimclrd=OLCU_MOR, dimclre=OLCU_MOR, dimclrt=OLCU_YAZI_RENGI)
        if layer == "DIS_PARCA_OLCU":                             # yazı çizginin ortasında: duvarın yanındaki pencere yazısına binmez
            ozel["dimtad"] = 0
        d = self.msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="PORTMAN", dxfattribs={"layer": layer}, override=ozel)
        d.render()

    # ------------------------------------------------------------------ ön görünüş / çatı / tablo
    def _disari_yon(self, d):
        return G.disari_yon(self.plan, d)

    def _vasistas_blok(self):
        """Görünüşün vasistas pencere bloğu (`VASISTAS_BLOK`; D-31 madde 6); ilk kullanımda kurulur (vasistassız çizimde blok yok)."""
        ad, en, boy, k = VASISTAS_BLOK
        if ad in self.doc.blocks:
            return ad
        b = self.doc.blocks.new(ad)
        kasa = [(0.0, 0.0), (en, 0.0), (en, boy), (0.0, boy)]
        kanat = [(k, k), (en - k, k), (en - k, boy - k), (k, boy - k)]
        b.add_lwpolyline(kasa, close=True, dxfattribs={"layer": "0", "color": 7})
        b.add_lwpolyline(kanat, close=True, dxfattribs={"layer": "0", "color": 7})
        for a, c in zip(kasa, kanat):                         # köşe gönyeleri
            b.add_line(a, c, dxfattribs={"layer": "0", "color": 7})
        tepe = (en / 2, boy - k)
        for alt in ((k, k), (en - k, k)):                     # açılım: alt köşelerden üst ortaya, 6 kesik (dolu 0,5)
            for i in range(6):
                t0, t1 = i / 6, (i + 0.5) / 6
                b.add_line((alt[0] + (tepe[0] - alt[0]) * t0, alt[1] + (tepe[1] - alt[1]) * t0),
                           (alt[0] + (tepe[0] - alt[0]) * t1, alt[1] + (tepe[1] - alt[1]) * t1), dxfattribs={"layer": "0", "color": 1})
        return ad

    def _surgulu_blok(self):
        """Görünüşün sürgülü pencere bloğu (`SURGULU_BLOK`; D-31 madde 11); ilk kullanımda kurulur."""
        ad, en, boy, k = SURGULU_BLOK
        if ad in self.doc.blocks:
            return ad
        b = self.doc.blocks.new(ad)
        kutu = lambda x0, y0, x1, y1: b.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": "0", "color": 7})
        kutu(0.0, 0.0, en, boy); kutu(k / 2, k / 2, en - k / 2, boy - k / 2)                 # çift kasa
        o, c = en / 2, 2.0                                                                  # orta, bindirme yarısı
        for x0, x1 in ((k, o + c), (o - c, en - k)):                                        # iki kanat, ortada bindirmeli; her biri çift çizgi
            kutu(x0, k, x1, boy - k); kutu(x0 + 2.5, k + 2.5, x1 - 2.5, boy - k - 2.5)
        for d in (0.0, 6.0):                                                                # sabit kanatta (sol) cam işareti
            b.add_line((o / 2 - 6 + d, boy / 2 - 8), (o / 2 + d, boy / 2 + 2), dxfattribs={"layer": "0", "color": 7})
        y, x0, x1 = boy / 2, o + (en - k - o) * 0.25, o + (en - k - o) * 0.75               # sürülen kanatta (sağ) yön oku
        b.add_line((x0, y), (x1, y), dxfattribs={"layer": "0", "color": 1})
        b.add_line((x0, y - 3), (x0, y + 3), dxfattribs={"layer": "0", "color": 1})
        for dy in (-2.5, 2.5):
            b.add_line((x1, y), (x1 - 4, y + dy), dxfattribs={"layer": "0", "color": 1})
        return ad

    def _on_pencere(self, u0, z0, w, h, olcu, acilis=None):
        """Görünüşte pencere: sürgülü bloğu (`acilis: surgulu`, D-31 madde 11), 60×40 vasistas bloğu (D-31 madde 6), öteki ölçüler kaynak ön
        pencere bloğu (Güncel Şablon 2024); açıklığa ölçekli."""
        if acilis == "surgulu":
            _, en, boy, _ = SURGULU_BLOK
            self.msp.add_blockref(self._surgulu_blok(), (u0, z0), dxfattribs={"xscale": w / en, "yscale": h / boy, "layer": "ON_DOGRAMA"})
        elif olcu in VASISTAS_OLCULERI:
            _, en, boy, _ = VASISTAS_BLOK
            self.msp.add_blockref(self._vasistas_blok(), (u0, z0), dxfattribs={"xscale": w / en, "yscale": h / boy, "layer": "ON_DOGRAMA"})
        else:
            self.msp.add_blockref("kaynak-on-pencere", (u0, z0), dxfattribs={"xscale": w / 77.101, "yscale": h / 116.017, "layer": "ON_DOGRAMA"})

    def ciz_on_gorunus(self, ox, top):
        plan, msp = self.plan, self.msp
        W = plan.W; hy = float(plan.is_emri["yapi"].get("duvar_yuksekligi_cm", 250)); cati = plan.is_emri.get("cati", {})
        egim = float(cati.get("egim_yuzde", 33)) / 100.0; sacak = float(cati.get("sacak_cm", 30)); topuk = float(cati.get("topuk_cm", 10))
        lento = hy - PENCERE_UST_KOTU                        # 250 → 50 (eski değer); 280 / 300 → 80 / 100 (D-14; üst kot 200 çıkarım)
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
                    self._on_pencere(x0 + ox, bot + alt, w, h, p.acilim.olcu, p.acilim.acilis)
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
        on_veranda = {v["ad"] for v in plan.dis_verandalar if v["cephe"] != "arka"}   # BK-14: önde ve yanda taşan veranda; arkadaki gövdenin ardında
        for p in VR.gorunus_parcalari(plan, plan.is_emri, "on") if on_veranda else []:
            if p["veranda"] not in on_veranda:
                continue
            pts = [(u + ox, bot + z) for u, z in p["u"]]
            if p.get("kalkan") or p.get("acik"):                # BK-18 ek: saçak altı çizgisi ON_CATI'de, topuk ON_TOPUK'ta (ana çatınınki gibi)
                msp.add_lwpolyline(pts, dxfattribs={"layer": "ON_TOPUK" if p["tur"] == "topuk" else "ON_CATI"})
            else:
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "ON_CATI" if p["tur"] == "cati" else "ON_GORUNUS"})
        self.text("ÖN GÖRÜNÜŞ - ÇALIŞMA", (W / 2 + ox, top + rise + 100), 26, "ON_YAZI")
        self.text(f"Pencere üst kotu {fmt(hy - lento)} cm | Lento {fmt(lento)} cm | Bina yüksekliği {fmt(hy)} cm", (W / 2 + ox, bot - 150), 15, "ON_YAZI")

    def _veranda_gorunusu(self, taraf, r):
        """D-31: taşan verandanın bu görünüşteki parçaları (`veranda.gorunus_parcalari`; u görünüşün yatayında, `cephe_gorunus.eksen` ile aynı
        başlangıç, z zeminden). Veranda çatısı ana çatının küçüğü gibi: saçak altı çizgisi, iki uçta topuk, iki eğim; kolon ve kiriş (Lokman,
        29 Ekim 2026 11:07–11:11: "tıpa tıp aynısı sadece daha küçüğü"). Eğim yazısı (`yazi`) yalnız ana çatınınkinden farklıysa, bir kez
        (11:55: "%33 eğimi sadece ana çatıda tek tarafta belirtsen yeter"). Karşı cephedeki veranda gövdenin ardında
        kalır, çizilmez. Veranda cephesi görünüşe dikse (yandan bakış) ana çatının görünüşteki siluetinin (`r`) örttüğü parça kırpılır: ana
        çatının saçak bandı veranda çatısının üstünde ve bakana yakın (`veranda.ana_catiya_tasma`; aşarsa uyarı zaten düşer)."""
        from shapely.geometry import LineString, MultiPoint
        from . import cephe_gorunus as CG
        plan, ie = self.plan, self.plan.is_emri
        if not plan.dis_verandalar:
            return []
        karsi = {"on": "arka", "arka": "on", "sol": "sag", "sag": "sol"}
        cephe = {v["ad"]: v["cephe"] for v in plan.dis_verandalar}
        egim = {v["ad"]: float(v["cati"]["egim_yuzde"]) for v in plan.dis_verandalar}
        ana_egim = float((ie.get("cati") or {}).get("egim_yuzde", 33))
        uc, _, _ = CG.eksen(plan, taraf)
        kay = uc(0.0, 0.0) - VR.izdusum(taraf).u(0.0, 0.0)
        ortu = MultiPoint([p for c in r["cizgiler"] for p in c]).convex_hull
        out, gorulen = [], set()
        for p in VR.gorunus_parcalari(plan, ie, taraf):
            if cephe[p["veranda"]] == karsi[taraf]:
                continue
            q = dict(p, u=[(u + kay, z) for u, z in p["u"]])
            imza = (q["tur"], tuple(q["u"]))
            if imza in gorulen:                                  # yandan bakışta üst üste düşen kolon ve kiriş bir kez
                continue
            gorulen.add(imza)
            acik = bool(q.get("kalkan") or q.get("acik"))
            hat = LineString(q["u"] if acik else q["u"] + q["u"][:1])
            if cephe[p["veranda"]] != taraf and ortu.area > 1 and hat.intersects(ortu.buffer(-0.05)):
                kalan = hat.difference(ortu)
                out += [dict(q, u=[(round(a, 4), round(b, 4)) for a, b in g.coords], acik=True) for g in getattr(kalan, "geoms", [kalan])
                        if g.geom_type == "LineString" and g.length > 0.5]
                continue
            out.append(q)
            if q.get("kalkan") and abs(egim[p["veranda"]] - ana_egim) > 1e-6:   # D-31 madde 10: eğim ana çatınınkiyle aynıysa yazılmaz;
                (a, za), (m, zm), _ = q["u"]                                     # farklıysa bir kez, sol eğimde
                out.append({"tur": "yazi", "metin": "%" + fmt(egim[p["veranda"]]), "u": [((a + m) / 2, (za + zm) / 2 + 22)]})
        return out

    def ciz_gorunusler(self, top):
        """İE-17: ön görünüş canlı biçimiyle ve yanına aynı biçimle arka, sol ve sağ görünüş (Lokman ve CIO, 27 Ekim 21:13: prefabrik çıktısı
        bu ön onay PDF'i; genel motordan yalnız çatı geometrisi). Çatı profili (topuk ve saçak) çizilmez (D-31; Lokman, 29 Ekim 11:12).
        Biçim `ciz_on_gorunus`'unki: duvarın dikdörtgeni, pano derzleri, kaynak pencere ve kapı blokları, saçak altı çizgisi ve topuk,
        ölçüler (çatı ve duvar eni, duvar yüksekliği, tepe, en soldaki pencerenin eşiği ve lentosu), % eğim, ON_* katmanları. Geometri
        `cephe_gorunus`'tan: duvar ve açıklıklar Motor'un planından, çatı çizgileri `cati_prefabrik`'in düzlemlerinin izdüşümü. Görünüşler
        yan yana, saçak uçları arası 360 (sağdaki ölçüler 110, ara 250). Duvar üstü `top`.
        D-31 (Lokman, 29 Ekim 2026; CIO 11:07): beşik de dört görünüşle (düzlemler `sunum.cati_tanimi`'nden); taşan veranda yalnız beşikte,
        `_veranda_gorunusu` ile: ana çatının küçüğü gibi (saçak altı, topuk, iki eğim, % eğim), arkadaki veranda gövdenin ardında çizilmez;
        60×40 pencere vasistas (`_on_pencere`); derz yalnız görünen ve cepheye değen duvarlardan (`cephe_gorunus.cephe`)."""
        from . import cephe_gorunus as CG
        plan, msp, ie = self.plan, self.msp, self.plan.is_emri
        hy = float(ie["yapi"].get("duvar_yuksekligi_cm", 250)); cati = ie["cati"]
        topuk = float(cati.get("topuk_cm", 10)); sacak = float(cati.get("sacak_cm", 30))
        bot = top - hy; lento = hy - PENCERE_UST_KOTU
        ox, sag_uc = 0.0, 0.0
        for k, taraf in enumerate(CG.TARAFLAR):
            n0 = len(msp)
            g, r = CG.cephe(plan, taraf), CG.cati_cizgileri(plan, ie, taraf)
            vp = self._veranda_gorunusu(taraf, r) + CG.mahal_cati_parcalari(plan, ie, taraf)    # İE-17 PR-2: ızgaradaki verandanın dikme ve kirişi
            sol_uc = min([r["u0"]] + [u for p in vp for u, _z in p["u"]])
            if k:
                ox = sag_uc + 360.0 - sol_uc
            W = g["en"]
            msp.add_lwpolyline([(ox, bot), (W + ox, bot), (W + ox, top), (ox, top)], close=True, dxfattribs={"layer": "ON_GORUNUS"})
            for u in g["derz"]:
                msp.add_line((u + ox, bot), (u + ox, top), dxfattribs={"layer": "ON_DERZ"})
            for a in g["acikliklar"]:
                w, h = a["u1"] - a["u0"], a["z1"] - a["z0"]
                if a["tur"] == "pencere":
                    self._on_pencere(a["u0"] + ox, bot + a["z0"], w, h, a["olcu"], a.get("acilis"))
                else:
                    msp.add_blockref("kaynak-on-kapi", (a["u0"] + ox, bot), dxfattribs={"xscale": w / 68.697, "yscale": h / 133.557, "layer": "ON_DOGRAMA"})
            xl, xr = r["u0"] + ox, r["u1"] + ox
            msp.add_line((xl, top), (xr, top), dxfattribs={"layer": "ON_CATI"})
            msp.add_line((xl, top), (xl, top + topuk), dxfattribs={"layer": "ON_TOPUK"}); msp.add_line((xr, top), (xr, top + topuk), dxfattribs={"layer": "ON_TOPUK"})
            for ut in r["topuklar"]:                              # D-34: cumbanın görünen saçak ucunda da topuk (taşan verandadaki gibi)
                msp.add_line((ut + ox, top), (ut + ox, top + topuk), dxfattribs={"layer": "ON_TOPUK"})
            for c in r["cizgiler"]:
                msp.add_lwpolyline([(u + ox, bot + z) for u, z in c], dxfattribs={"layer": "ON_CATI"})
            for p in vp:
                pts = [(u + ox, bot + z) for u, z in p["u"]]
                if p["tur"] == "kolon" and not p.get("acik"):   # D-31 madde 9: kolon soluk dolgulu, duvarın önünde (köşedeki kolon görünsün)
                    dolgu = msp.add_hatch(color=VERANDA_KOLON_DOLGU, dxfattribs={"layer": "ON_GORUNUS"})
                    dolgu.paths.add_polyline_path(pts, is_closed=True)
                if p["tur"] == "yazi":
                    self.text(p["metin"], pts[0], 14, "ON_YAZI")
                elif p.get("kalkan") or p.get("acik"):
                    msp.add_lwpolyline(pts, dxfattribs={"layer": "ON_TOPUK" if p["tur"] == "topuk" else "ON_CATI"})
                else:
                    msp.add_lwpolyline(pts, close=p.get("kapali", True), dxfattribs={"layer": "ON_CATI" if p["tur"] == "cati" else "ON_GORUNUS"})
            tu, tz = r["tepe"]; rise = tz - hy
            ud = max([W] + [u for p in vp for u, _z in p["u"]]) + 77      # sağdaki yükseklik ölçüleri verandanın da dışında
            self.dim((xl, top), (xr, top), (0, bot - 110), 0, "ON_OLCU"); self.dim((ox, bot), (W + ox, bot), (0, bot - 67), 0, "ON_OLCU")
            if taraf in KOT_GORUNUSLERI:                          # D-31 madde 14
                self.dim((W + ox, bot), (W + ox, top), (ud + ox, 0), 90, "ON_OLCU"); self.dim((xr, top), (tu + ox, bot + tz), (ud + ox, 0), 90, "ON_OLCU")
            sag_uc = max(xr, ud + 33 + ox)
            pen = [a for a in g["acikliklar"] if a["tur"] == "pencere"]
            if pen and taraf in KOT_GORUNUSLERI:
                a = pen[0]
                self.dim((a["u0"] + ox, bot), (a["u0"] + ox, bot + a["z0"]), (a["u0"] - 33 + ox, 0), 90, "ON_OLCU")
                self.dim((a["u0"] + ox, bot + a["z1"]), (a["u0"] + ox, top), (a["u0"] - 33 + ox, 0), 90, "ON_OLCU")
            yazilan = set()
            for u, z, e in r["egimler"]:                          # D-31 madde 10: aynı eğim görünüşte bir kez, soldaki yüzde
                if round(e * 100, 2) in yazilan:
                    continue
                yazilan.add(round(e * 100, 2))
                self.text("%" + fmt(e * 100), (u + ox, bot + z + 30), 18, "ON_YAZI")
            self.text(f"{CG.AD[taraf]} GÖRÜNÜŞ - ÇALIŞMA", (W / 2 + ox, top + rise + 100), 26, "ON_YAZI")
            if taraf == "on":
                self.text(f"Pencere üst kotu {fmt(hy - lento)} cm | Lento {fmt(lento)} cm | Bina yüksekliği {fmt(hy)} cm", (W / 2 + ox, bot - 150), 15, "ON_YAZI")
            self._bolge(taraf, n0)                                # D-31 madde 12: A4 sayfasında üstte ön ve arka, altta sol ve sağ

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

# D-31 madde 12 (Lokman, 29 Ekim 2026 12:01: "bu dört çizimi üste ön ve arka altta sağ ve sol görünüşler ortada kat planı olacak şekilde A4
# kağıdına dikey olarak tam sığdır yani telefonla açtığı anda görsün kat planını doğal olarak daha büyük çiz tam A4'ün ortasında sınırlara
# dayanacak kadar üst ve alt tarafta kalan boşluklara da görünüşleri çiz"; 12:17 "en önemlisi cep telefonundan tek de okunması"; 12:20
# "ikinci sayfayı artık tamamen kaldır ona ihtiyacımız yok"; 12:21 "önce görünüşleri tam sığdır sonra ortaya kat planını al"): PDF tek
# sayfa, dikey A4. Üstte antet, ön ve arka görünüş, altta sol ve sağ görünüş; dördü aynı ölçekte, geniş satır sayfa enini kenar boşluğuna
# kadar doldurur (en çok 1/100). Kat planı (aksli, başlıksız, aks ölçü zinciri olmadan: madde 13, 12:20 "kat planının 125,5 pano ölçülerini
# tamamen kaldır") iki bandın arasında kalan yerin ortasında, sığan en büyük ölçekle. Plan ve görünüşler DXF'teki çizimin kendisi (yeniden
# açılan DXF'ten); DXF değişmez, öteki çizimleri (net alanlar, saha montaj planı, teknik özellikler) PDF'e girmez.
A4_DIKEY_MM = (210.0, 297.0)
A4_KENAR_MM, A4_ARA_MM = 5.0, 2.5          # sayfa kenarı, bölgeler arası
A4_GORUNUS_EN_BUYUK = 10.0 / 100           # mm / cm: görünüş ölçeği en çok 1/100 (küçük evde görünüş planı ezmesin)
A4_ANTET_OLCEK = 10.0 / 130                # mm / cm: antetin iki satırı (23 ve 20 cm yazı) 1/130
A4_PAY_CM = 10.0                           # bölge kutusunun her yanına (yazının şapkası ve noktası kırpılmasın)


def _bolge_pdf(doc, handles, kutu, w_mm: float, h_mm: float, cfg) -> bytes:
    """Yalnız `handles` varlıkları; `kutu` (model, cm) `w_mm × h_mm` sayfaya tam oturur (oran kutununki)."""
    hs = set(handles)
    backend = pymupdf.PyMuPdfBackend()
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), filter_func=lambda e: e.dxf.handle in hs)
    return backend.get_pdf_bytes(layout.Page(w_mm, h_mm, layout.Units.mm, margins=layout.Margins.all(0)),
                                 settings=layout.Settings(fit_page=True), render_box=kutu)


def a4_yerlesim(kutular: dict) -> dict:
    """A4 bayi sayfasının yerleşimi (mm; sol üst köşe 0, y aşağı): {ad: (x, y, en, boy)} ve {"olcek": {"plan", "gorunus", "antet"}} (mm / cm).
    `kutular`: ad → (en, boy) cm; "plan" zorunlu; "antet", "on", "arka", "sol", "sag" olabilir. Önce görünüşler sayfa enine sığar, sonra plan
    aradaki yerin ortasına (Lokman, 12:21)."""
    W, H = A4_DIKEY_MM; k, g = A4_KENAR_MM, A4_ARA_MM
    en_k = W - 2 * k
    ust = [t for t in ("on", "arka") if t in kutular]; alt = [t for t in ("sol", "sag") if t in kutular]
    sv = min([A4_GORUNUS_EN_BUYUK] + [(en_k - g * (len(s) - 1)) / sum(kutular[t][0] for t in s) for s in (ust, alt) if s])
    aw, ah = kutular.get("antet", (0.0, 0.0))
    sa = min(A4_ANTET_OLCEK, en_k / aw) if aw else 0.0
    out = {"olcek": {"gorunus": sv, "antet": sa}}
    y = k
    if aw:
        out["antet"] = ((W - aw * sa) / 2, y, aw * sa, ah * sa); y += ah * sa + g
    for sira, ust_bant in ((ust, True), (alt, False)):
        if not sira:
            continue
        eni = sum(kutular[t][0] for t in sira) * sv + g * (len(sira) - 1)
        boy = max(kutular[t][1] for t in sira) * sv
        x, yb = (W - eni) / 2, (y if ust_bant else H - k - boy)
        for t in sira:
            w, h = kutular[t][0] * sv, kutular[t][1] * sv
            out[t] = (x, yb + (boy - h), w, h)                          # satırdakiler alt çizgiye hizalı
            x += w + g
        if ust_bant:
            y += boy + g
    y1 = (min(out[t][1] for t in alt) - g) if alt else H - k             # planın yeri: üst bandın altı ile alt bandın üstü arası
    pw, ph = kutular["plan"]
    sp = min(en_k / pw, (y1 - y) / ph)
    out["plan"] = ((W - pw * sp) / 2, (y + y1 - ph * sp) / 2, pw * sp, ph * sp)
    out["olcek"]["plan"] = sp
    return out


A4_BOLGELER = ("antet", "plan", "on", "arka", "sol", "sag")


def a4_bayi_sayfasi(doc, bolgeler: dict, cfg) -> bytes:
    """Tek sayfalı PDF: dikey A4 bayi sayfası (`a4_yerlesim`)."""
    kutu = {}
    for ad in A4_BOLGELER:
        b = ebbox.extents([doc.entitydb[h] for h in bolgeler.get(ad, []) if h in doc.entitydb])
        if b.has_data:
            kutu[ad] = BoundingBox2d([b.extmin - (A4_PAY_CM, A4_PAY_CM, 0), b.extmax + (A4_PAY_CM, A4_PAY_CM, 0)])
    gor = [t for t in ("on", "arka", "sol", "sag") if t in kutu]
    if gor:                                                  # görünüşler aynı düşey aralıkla: duvar altı ve üstü dördünde aynı hizada
        y0, y1 = min(kutu[t].extmin.y for t in gor), max(kutu[t].extmax.y for t in gor)
        for t in gor:
            kutu[t] = BoundingBox2d([(kutu[t].extmin.x, y0), (kutu[t].extmax.x, y1)])
    if "plan" not in kutu:
        raise RuntimeError("A4 bayi sayfasında kat planı bölgesi yok")
    yer = a4_yerlesim({ad: (b.size.x, b.size.y) for ad, b in kutu.items()})
    pt = 72 / 25.4
    out = fitz.open()
    sayfa = out.new_page(width=A4_DIKEY_MM[0] * pt, height=A4_DIKEY_MM[1] * pt)
    for ad, b in kutu.items():
        x, y, w, h = yer[ad]
        if w <= 0 or h <= 0:                                 # sessizce atlanmaz (geometri hakemi, 29 Ekim; K16)
            raise RuntimeError(f"A4 bayi sayfasında {ad} bölgesine yer kalmadı ({w:.1f} × {h:.1f} mm)")
        with fitz.open("pdf", _bolge_pdf(doc, bolgeler[ad], b, w, h, cfg)) as parca:
            sayfa.show_pdf_page(fitz.Rect(x * pt, y * pt, (x + w) * pt, (y + h) * pt), parca, 0)
    return out.tobytes(garbage=3, deflate=True, no_new_id=True)


def alan_yazisi(plan) -> str:
    """D-31 madde 14 (Lokman, 29 Ekim 2026 13:13: "yukarıya m² ve kime ait olduğunu yaz"): antetteki alan. Brüt: kapalı gövdenin dış yüzleri
    (niş ve veranda hariç; `sunum.bina_cizgisi`); net: kapalı odaların net alanları toplamı (açık mahal hariç; montaj rehberindeki m²)."""
    from . import sunum
    brut = sunum.bina_cizgisi(plan).area / 1e4
    net = sum(m.alan_m2 for m in plan.mahaller.values() if not m.acik)
    f2 = lambda v: f"{v:.2f}".replace(".", ",")
    return f"{f2(brut)} m² brüt · {f2(net)} m² net"


def _cati_adi(cati: dict) -> str:
    """Özellik tablosundaki çatı adı: beşik + cumba ve kırmada paftanın yazımı (İE-17; `sunum.CATI_SEKLI`), başka her tipte eski yazım
    (beşik DXF'i bayt bayt aynı)."""
    from .cati_prefabrik import TIPLER
    tip = cati.get("tip", "besik")
    if tip in TIPLER:
        from .sunum import CATI_SEKLI
        return CATI_SEKLI[tip]
    return tip.capitalize()


def uret(is_emri: dict, cikti_dir: Path, ad_govde: str | None = None, pdf_hatada: bool = False) -> dict:
    """İş Emri → DXF (kaydet, yeniden aç, doğrula) → PDF. Doğrulama GEÇMEZSE teslim edilebilir PDF üretilmez (denetim bulgusu F08);
    pdf_hatada=True yalnız tanı için '<ad>.HATALI.pdf' yazar. Dönen manifest'te 'pdf' o zaman None, 'validation_passed' False."""
    from . import validate as V
    cikti_dir = Path(cikti_dir); cikti_dir.mkdir(parents=True, exist_ok=True)
    plan = G.kur(is_emri)
    pafta_uyarilari = [str(u) for u in is_emri.get("pafta_uyarilari", [])]   # İE-11: Motor'un kendi uyarılarını düşürmez (K16)
    t0 = time.time()
    kat = Katalog()
    c = Cizici(plan, kat)
    W, H = plan.W, plan.H
    yapi = is_emri["yapi"]
    stem = ad_govde or f"Portman_{is_emri.get('is_emri_no','IS')}_r{int(is_emri.get('revizyon',1)):02d}"
    baslik = f"{plan.is_emri.get('talep',{}).get('musteri_adi','')} | {_grid_yazi(yapi, ' x ', ' PANO')} | {fmt(W)} × {fmt(H)} cm"
    icerik = is_emri.get("cikti", {}).get("icerik", [])
    py = c.paylar()                                         # BK-14: taşan veranda yoksa hepsi 0 (yerleşim aynı)
    gap = W + 300.0 + py["sol"] + py["sag"]
    c.ciz_plan(0.0, 0.0, "ANA", "KAT PLANI — AKSLI", baslik + " | Model ve ölçüler: cm | 125,5 cm aks düzeni")
    c.ciz_plan(gap, 0.0, "KOPYA", "KAT PLANI — NET ALANLAR", baslik + " | Net alanlar oda adının altında, m²")
    montaj = ("montaj_kopyasi" in icerik) or True
    if montaj:
        c.ciz_plan(2 * gap, 0.0, "MONTAJ", "SAHA MONTAJ PLANI", baslik + " | Standart dışı panolar mor ve ölçülü")
    _yeni = G.yeni_anahtar_var(is_emri)
    _lento = float(yapi.get("duvar_yuksekligi_cm", 250)) - PENCERE_UST_KOTU
    notlar = [f"Pencereler pano ortasında. Pencere üstünden duvar üstüne (lento): {fmt(_lento)} cm.",
              "Net alanlar kapı eşikleri hariç; veranda alanı açık dış kenarlara kadardır.",
              "Açık mahal sınırları bitişik duvar yüzünün devamı kabul edildi."]
    for i, s in enumerate(notlar):
        c.text(s, (gap + W / 2, -145 - py["alt"] - 30 * i), 13, "ODA_ADLARI")
    _cati = is_emri.get("cati", {})
    from .cati_prefabrik import TIPLER as _PREFABRIK_CATI
    _dort = (is_emri.get("cati") or {}).get("tip", "besik") in _PREFABRIK_CATI + ("besik",)      # D-31: beşik de dört görünüş
    _en = W if (not _dort or _cati.get("makas_ekseni", "x") == "x") else H     # İE-17: beşik dışında makasın geçtiği boy
    _rise = float(_cati.get("topuk_cm", 10)) + (_en + 2 * float(_cati.get("sacak_cm", 30))) / 2 * float(_cati.get("egim_yuzde", 33)) / 100.0
    kay = (max(0.0, _rise - 147.445) if _yeni else 0.0) + py["alt"]   # İE-11: eski İş Emri'nde pafta yerleşimi değişmez; BK-14: ön veranda kadar aşağı
    kay2 = kay + max(0.0, float(yapi.get("duvar_yuksekligi_cm", 250)) - 250.0)     # 280 / 300'de ön görünüş uzar, alt yazılar iner
    if _dort:                                               # İE-17: beşik + cumba, kırma; D-31: beşik de → dört görünüş, ön görünüşün biçimiyle
        c.ciz_gorunusler(-600.0 - kay)
    else:                                                   # başka her tip: yalnız ön görünüş
        n0 = len(c.msp); c.ciz_on_gorunus(0.0, -600.0 - kay); c._bolge("on", n0)
    hy = yapi.get("duvar_yuksekligi_cm", 250); cati = is_emri.get("cati", {})
    _olculer = {p.acilim.olcu for p in plan.panolar if p.acilim and p.acilim.tur == "pencere"}
    _pencere_satiri = "PVC doğrama; " + ", ".join(f"{e}×{b}" for e, b in sorted((k.en, k.boy) for k in map(G.pencere_kurali, _olculer)))
    if len(_pencere_satiri) > 64:                         # BK-13: üç ölçü dışında pencere varsa plandakiler; hücreye sığmazsa sayı
        _pencere_satiri = f"PVC doğrama; {len(_olculer)} ölçü, plandaki etiketlerde (en/boy)"
    tab = [("Bina / pano grid", f"{_grid_yazi(yapi, ' × ', ' pano')} — {fmt(W)} × {fmt(H)} cm"),
           ("Sistem", "Prefabrik panel (8 mm fibercement)"), ("Duvar yüksekliği", f"{fmt(hy)} cm"), ("Dış duvar / iç duvar", f"{G._mm(G.T_DIS)} mm / {G._mm(G.T_IC)} mm"),
           ("Pano modülü", "125,5 cm (isteğe bağlı yarım pano 62,75 cm)"),
           ("Çatı", f"{_cati_adi(cati)} — %{fmt(float(cati.get('egim_yuzde',33)))} eğim, {fmt(float(cati.get('sacak_cm',30)))} cm saçak, {fmt(float(cati.get('topuk_cm',10)))} cm topuk"),
           *[(f"{g['mahal'].capitalize()} çatısı", f"Tek eğim panel çatı — %{fmt(float(g['egim_yuzde']))} eğim")      # İE-17 PR-2 (AP-09)
             for g in cati.get("mahal_catilari") or []],
           ("Pencereler", "PVC doğrama; katalog 120×120 / 120×180 / 60×40" if _olculer <= set(G.PENCERE_OLCULERI) else _pencere_satiri),
           ("Kapılar", "Dış: çelik kapı; iç: Amerikan panel kapı"),
           ("Kat sayısı", str(yapi.get("kat_sayisi", 1))), ("Revizyon", f"r{int(is_emri.get('revizyon',1)):02d}")]
    if is_emri.get("ozellikler"):                       # İE-11: paftanın teknik özellikleri İş Emri'nden (PK-01: "Dış Kapı: Alıcıya ait")
        tab = [r for r in tab if r[0] not in ("Pencereler", "Kapılar")] + [(str(k), str(v)) for k, v in is_emri["ozellikler"].items()]
    c.ciz_ozellik_tablosu((3 if montaj else 2) * gap, H + 140 + py["ust"], tab)
    cx = ((3 if montaj else 2) * gap - 300) / 2
    n0 = len(c.msp)
    c.text(LABEL, (cx, H + 320 + py["ust"]), 23, "PORTMAN_INFO")
    _talep = is_emri.get("talep", {})
    _kim = " / ".join(v for v in (str(_talep.get("bayi", {}).get("ad", "")), str(_talep.get("musteri_adi", ""))) if v)
    c.text(f"PORTMAN | {_kim} | {alan_yazisi(plan)} | İş Emri {is_emri.get('is_emri_no','')} r{int(is_emri.get('revizyon',1)):02d}",
           (cx, H + 275 + py["ust"]), 20, "PORTMAN_INFO")         # D-31 madde 14: kime ait ve m² antette
    c._bolge("antet", n0)                                   # D-31 madde 12: A4 sayfasının üstündeki iki satır
    c.text(f"Duvar: {fmt(G.T_DIS)} / {fmt(G.T_IC)} cm | Yükseklik: {fmt(hy)} cm | Pano: 125,5 cm | Çatı: %{fmt(float(cati.get('egim_yuzde',33)))}", (cx, -1090 - kay2), 18, "PORTMAN_INFO")
    c.text("Kural kaydı v1.4.3 ile üretildi. " + ("Üretim/statik hesabı" if _dort else "Yan görünüş ve üretim/statik hesabı")
           + " bu taslağın kapsamında değildir.", (cx, -1130 - kay2), 14, "PORTMAN_INFO")
    c.text("Portman motor v1.1 | Üretim: " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), (cx, -1165 - kay2), 13, "PORTMAN_INFO")
    for i, u in enumerate(plan.uyarilar[:4] + pafta_uyarilari):
        c.text("UYARI: " + u, (cx, -1200 - kay2 - 25 * i), 12, "PORTMAN_INFO")
    plan.uyarilar += pafta_uyarilari                                     # validation.json'da hepsi (Motor + İş Emri)
    dxf = cikti_dir / f"{stem}.dxf"; pdf = cikti_dir / f"{stem}.pdf"
    c.doc.saveas(dxf)
    bom_rows = c.bom()
    if any(p.acilim and p.acilim.dograma == "alıcıya ait" for p in plan.panolar):       # İE-11: alıcıya ait doğrama
        def _dograma_kodu(acl):                           # saf arama: bloklar çizimde zaten tanımlandı, burada yeni tahsis yapılmaz
            k = {"dis_kapi": f"dis{int(acl.genislik)}", "pencere": acl.olcu, "ic_kapi": "ic82"}.get(acl.tur)
            return c.dograma[k][1] if k in c.dograma else None
        toplam, alici = Counter(), Counter()
        for p in plan.panolar:
            if p.acilim and _dograma_kodu(p.acilim):
                toplam[_dograma_kodu(p.acilim)] += 1
                if p.acilim.dograma == "alıcıya ait": alici[_dograma_kodu(p.acilim)] += 1
        for r in bom_rows:
            k = alici.get(r["kod"], 0)
            if not k: continue
            r["alici_adet"] = k
            if k == toplam[r["kod"]] == r["adet"]:          # satırın tamamı alıcıya ait → satır işaretli (yükleme listesine girmez)
                r["alici"] = True
                r["not"] = (r["not"] + " " if r["not"] else "") + "Alıcıya ait: doğrama yükleme listesine girmez (İş Emri)."
            else:                                            # aynı koddan bize ait doğrama da var → satır kalır, yalnız adet düşülür
                r["alici"] = False
                r["not"] = (r["not"] + " " if r["not"] else "") + f"{k} adedi alıcıya ait: yükleme listesine {r['adet'] - k} adet girer (İş Emri)."
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
        pdf.write_bytes(a4_bayi_sayfasi(saved, c.bolgeler, cfg))
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
