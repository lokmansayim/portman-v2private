"""Portman çıkarıcı v0.1 — katalog DXF'i → İş Emri JSON (aks tanıma ile).

Yaklaşım (yuvarlama değil, aks tanıma):
  1. Duvar çizgileri (katman 0 / DUVAR) → bitişik parçalar → en büyük bileşen = plan gövdesi → dış kutu (x0, y0, W, H).
  2. W = 125,5·nx + 20, H = 125,5·ny + 10 → nx, ny (yarım pano adımı); artık > toleransa "uyuşmazlık".
  3. Yarım pano hücre ızgarası; her hücre kenarında duvar var mı? (aks ±10,5 cm içindeki paralel çizgi kaplaması
     + kapı/pencere kapatmaları ≥ %50) → taşkın dolgu → mahaller → etiket eşleme (MTEXT) → dikdörtgenlere ayırma.
  4. Pencere (katman Pencere) ve kapı (katman Kapı) sembolleri → duvar/aks, mahal, ölçü, pano indeksi
     (Motor'un aday listesiyle birebir), menteşe (a'dan b'ye bakarken sağ/sol).
  5. Kaynak konumu ile Motor'un yerleştireceği konum arasındaki fark "artık" olarak raporlanır; hiçbir şey sessizce
     yuvarlanmaz. LLM yok; yalnız geometri.

Kullanım:
  python -m motor.cikarici ref_katalog/P6001.dxf --sablon is_emri/P6001_2plus1_6x6.json --cikti cikti/cikarici/P6001
"""
from __future__ import annotations
import argparse, json, math, re, sys, unicodedata
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from motor import geometry as G  # noqa: E402

MOD = G.MOD
DUVAR_KATMANLARI = {"0", "DUVAR", "duvar", "Duvar"}
PENCERE_KATMAN = {"pencere"}
KAPI_KATMAN = {"kapı", "kapi"}
VERANDA_KATMAN = {"veranda"}
AKS_TOL = 10.5          # çizginin aksa dik uzaklığı (dış duvar gövdesi aks dışında: 0..10)
BAG_TOL = 0.6           # uç bitişikliği (cm)
KAPLAMA_ESIK = 0.5      # kenar boyunun bu oranı kadar duvar/kapatma varsa "duvar"
GRID_TOL_CM = 2.5       # nx, ny çözümünde izin verilen artık (cm)

AD_ESLEME = [   # (normalize edilmiş anahtar, ad kökü, tur, açık mı)
    ("yatak odasi", "YATAK ODASI", "yatak_odasi", False), ("ebeveyn", "EBEVEYN YATAK ODASI", "yatak_odasi", False),
    ("cocuk odasi", "COCUK ODASI", "yatak_odasi", False),
    ("yasam alani", "YASAM ALANI", "salon", False), ("yasam", "YASAM ALANI", "salon", False), ("salon", "SALON", "salon", False),
    ("oturma", "OTURMA ODASI", "salon", False),
    ("mutfak", "MUTFAK", "mutfak", False), ("banyo", "BANYO", "banyo", False), ("wc", "WC", "banyo", False),
    ("dus", "DUS", "banyo", False), ("hol", "HOL", "hol", False), ("koridor", "KORIDOR", "hol", False),
    ("antre", "ANTRE", "hol", False), ("giris", "GIRIS", "hol", False),
    ("veranda", "VERANDA", "veranda", True), ("balkon", "BALKON", "balkon", True), ("teras", "TERAS", "teras", True),
    ("sundurma", "SUNDURMA", "sundurma", True),
    ("depo", "DEPO", "depo", False), ("kiler", "KILER", "depo", False), ("calisma", "CALISMA ODASI", "calisma", False),
    ("giyinme", "GIYINME", "giyinme", False), ("camasir", "CAMASIR", "teknik", False), ("teknik", "TEKNIK", "teknik", False),
]
PENCERE_OLCU_RE = re.compile(r"(\d{2,3})\s*[/xX×]\s*(\d{2,3})")
M2_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m\s*[2²]", re.I)


class CikarimHatasi(Exception):
    pass


# ----------------------------------------------------------------------------- yardımcılar
def _norm(s: str) -> str:
    s = s.replace("ı", "i").replace("İ", "i").replace("ş", "s").replace("Ş", "s").replace("ğ", "g").replace("Ğ", "g")
    s = s.replace("ü", "u").replace("Ü", "u").replace("ö", "o").replace("Ö", "o").replace("ç", "c").replace("Ç", "c")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def _mtext_duz(t: str) -> str:
    """MTEXT biçim kodlarını temizle: \\pxqc; {\\f...;metin} \\P satır sonu."""
    t = re.sub(r"\\\\?[pP]x[^;]*;", "", t)
    t = re.sub(r"\\[fF][^;]*;", "", t)
    t = re.sub(r"\\[cC]\d+;", "", t)
    t = re.sub(r"\\[HhWwQqAaLlOoKkTt][^;]*;", "", t)
    t = t.replace("\\P", "\n").replace("{", "").replace("}", "")
    return t.strip()


def _r(v, n=2):
    return round(float(v), n)


def _seg_ekle(segs, a, b, katman):
    x0, y0 = float(a[0]), float(a[1]); x1, y1 = float(b[0]), float(b[1])
    if abs(x0 - x1) < 1e-6 and abs(y0 - y1) < 1e-6:
        return
    if abs(y0 - y1) < 1e-4:
        segs.append(("x", min(x0, x1), max(x0, x1), y0, katman))       # yatay: (yon, a0, a1, c)
    elif abs(x0 - x1) < 1e-4:
        segs.append(("y", min(y0, y1), max(y0, y1), x0, katman))
    else:
        segs.append(("d", x0, y0, x1, y1, katman))                      # diyagonal (yalnız raporlanır)


def _entity_segs(e, segs, katman):
    t = e.dxftype()
    if t == "LINE":
        _seg_ekle(segs, (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y), katman)
    elif t == "LWPOLYLINE":
        pts = [(p[0], p[1]) for p in e.get_points()]
        for a, b in zip(pts, pts[1:]):
            _seg_ekle(segs, a, b, katman)
        if e.closed and len(pts) > 2:
            _seg_ekle(segs, pts[-1], pts[0], katman)
    elif t == "POLYLINE":
        pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        for a, b in zip(pts, pts[1:]):
            _seg_ekle(segs, a, b, katman)
        if e.is_closed and len(pts) > 2:
            _seg_ekle(segs, pts[-1], pts[0], katman)


def _dondur_segs(segs):
    """90° saat yönünün tersine döndür: (x, y) → (-y, x). Yatay çizgi (a0..a1, y=c) → düşey (x=-c, y a0..a1);
    düşey (x=c, y a0..a1) → yatay (y=c, x -a1..-a0)."""
    out = []
    for s in segs:
        if s[0] == "x":
            out.append(("y", s[1], s[2], -s[3]) + tuple(s[4:]))
        elif s[0] == "y":
            out.append(("x", -s[2], -s[1], s[3]) + tuple(s[4:]))
        else:
            out.append(("d", -s[2], s[1], -s[4], s[3]) + tuple(s[5:]))
    return out


def _seg_uclar(s):
    if s[0] == "x":
        return (s[1], s[3]), (s[2], s[3])
    if s[0] == "y":
        return (s[3], s[1]), (s[3], s[2])
    return (s[1], s[2]), (s[3], s[4])


def _bilesenler(segs):
    """Uç bitişikliğine (BAG_TOL) göre bağlı bileşenler; her bileşen segment indeks listesi."""
    n = len(segs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj: parent[ri] = rj

    # ızgara kovalama ile uç noktaları eşle
    kova = {}
    for i, s in enumerate(segs):
        for p in _seg_uclar(s):
            k = (round(p[0] / BAG_TOL), round(p[1] / BAG_TOL))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in kova.get((k[0] + dx, k[1] + dy), []):
                        union(i, j)
            kova.setdefault(k, []).append(i)
    # T birleşimleri: bir ucun başka bir segmentin gövdesine değmesi
    for i, s in enumerate(segs):
        if s[0] == "d": continue
        for p in _seg_uclar(s):
            for j, t in enumerate(segs):
                if t[0] == "d" or i == j: continue
                if t[0] == "x" and abs(p[1] - t[3]) <= BAG_TOL and t[1] - BAG_TOL <= p[0] <= t[2] + BAG_TOL:
                    union(i, j)
                elif t[0] == "y" and abs(p[0] - t[3]) <= BAG_TOL and t[1] - BAG_TOL <= p[1] <= t[2] + BAG_TOL:
                    union(i, j)
    gruplar = {}
    for i in range(n):
        gruplar.setdefault(find(i), []).append(i)
    return list(gruplar.values())


def _bbox(segs, idx=None):
    xs, ys = [], []
    for i, s in enumerate(segs):
        if idx is not None and i not in idx: continue
        for p in _seg_uclar(s):
            xs.append(p[0]); ys.append(p[1])
    return min(xs), min(ys), max(xs), max(ys)


def _kaplama(araliklar, lo, hi):
    """[lo,hi] aralığının, verilen aralık listesiyle kaplanan toplam uzunluğu."""
    ar = sorted((max(lo, a), min(hi, b)) for a, b in araliklar if min(hi, b) > max(lo, a))
    top, cur = 0.0, None
    for a, b in ar:
        if cur is None: cur = [a, b]
        elif a <= cur[1]: cur[1] = max(cur[1], b)
        else: top += cur[1] - cur[0]; cur = [a, b]
    if cur: top += cur[1] - cur[0]
    return top


# ----------------------------------------------------------------------------- çıkarıcı
class Cikarici:
    def __init__(self, dxf_path: str | Path, plan_secici: str | None = None):
        self.path = Path(dxf_path)
        self.doc = ezdxf.readfile(str(self.path))
        self.msp = self.doc.modelspace()
        self.uyusmazlik: list[str] = []      # kural ile çizim arasındaki farklar
        self.notlar: list[str] = []
        self.plan_secici = plan_secici

    # ---- 1. duvar çizgileri ve plan gövdesi
    def _plan_bolgesi(self):
        """Master DXF: 'PORT - Pxxxx' etiketi paftanın sol altında; plan gövdesi etiketin sağında, aynı satırda."""
        if not self.plan_secici:
            return None
        for e in self.msp.query("MTEXT TEXT"):
            t = _mtext_duz(e.text if e.dxftype() == "MTEXT" else e.dxf.text)
            if re.search(r"\b" + re.escape(_norm(self.plan_secici)) + r"\b", _norm(t)):
                x, y = e.dxf.insert.x, e.dxf.insert.y
                return (x - 60, y - 2600, x + 2700, y + 150)
        raise CikarimHatasi(f"Plan seçici etiketi bulunamadı: {self.plan_secici}")

    def duvar_govdesi(self):
        """Duvar çizgileri (katman 0/DUVAR) + köprü olarak pencere/kapı sembolleri → bağlı bileşenler. Pafta çerçeveleri
        (çok büyük kutu) ve tek çizgiler (başlık altı) elenir. Seçici verilmişse etiketin paftasındaki bütün gövdeler,
        verilmemişse dosyadaki bütün gövdeler birleştirilir (pencere boşlukları duvar çizgilerini parçalayabilir)."""
        segs, kopru = [], []
        for e in self.msp:
            kat = _norm(e.dxf.layer)
            if e.dxftype() not in ("LINE", "LWPOLYLINE", "POLYLINE"):
                continue
            if e.dxf.layer in DUVAR_KATMANLARI:
                _entity_segs(e, segs, e.dxf.layer)
            elif kat in PENCERE_KATMAN or kat in KAPI_KATMAN:
                _entity_segs(e, kopru, e.dxf.layer)
        diyag = [s for s in segs if s[0] == "d"]
        segs = [s for s in segs if s[0] != "d"]
        kopru = [s for s in kopru if s[0] != "d"]
        if diyag:
            self.notlar.append(f"{len(diyag)} diyagonal duvar çizgisi yok sayıldı (v0.1 yalnız aksa paralel duvar)")
        if not segs:
            raise CikarimHatasi("Duvar çizgisi bulunamadı (katman 0 / DUVAR)")
        n_duvar = len(segs)
        gruplar = _bilesenler(segs + kopru)
        bolge = self._plan_bolgesi()
        govdeler = []
        for g in gruplar:
            duvar_idx = [i for i in g if i < n_duvar]
            if len(duvar_idx) < 4:
                continue
            x0, y0, x1, y1 = _bbox(segs, set(duvar_idx))
            if (x1 - x0) > 2500 or (y1 - y0) > 2500:      # pafta çerçevesi / cetvel
                continue
            uz = sum((segs[i][2] - segs[i][1]) for i in duvar_idx)
            if uz < 150:
                continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if bolge and not (bolge[0] <= cx <= bolge[2] and bolge[1] <= cy <= bolge[3]):
                continue
            govdeler.append((uz, duvar_idx, (x0, y0, x1, y1)))
        if not govdeler:
            raise CikarimHatasi("Plan gövdesi bulunamadı (duvar bileşeni yok)")
        govdeler.sort(key=lambda t: -t[0])
        if not bolge:
            # tek plan dosyası: en büyük gövdeye kutu olarak yakın (≤ 60 cm) olanları da al; uzak parçalar (lejant vb.) dışarıda
            ana = govdeler[0][2]; secilen = [govdeler[0]]
            PAY = 60.0
            for g in govdeler[1:]:
                b = g[2]
                if not (b[0] > ana[2] + PAY or b[2] < ana[0] - PAY or b[1] > ana[3] + PAY or b[3] < ana[1] - PAY):
                    secilen.append(g)
            if len(govdeler) > len(secilen):
                self.notlar.append(f"{len(govdeler) - len(secilen)} uzak duvar parçası yok sayıldı")
            govdeler = secilen
        idx = [i for g in govdeler for i in g[1]]
        if len(govdeler) > 1:
            self.notlar.append(f"Plan gövdesi {len(govdeler)} parçadan birleştirildi (pencere/boşluk kesintileri)")
        govde = [segs[i] for i in idx]
        # ---- yön: kısa kenar (köşe +20) x'te olmalı; gerekirse 90° döndür
        x0, y0, x1, y1 = _bbox(govde)
        W, H = x1 - x0, y1 - y0
        def artik(W, H):
            nx2, ny2 = round((W - 20) / MOD * 2), round((H - 10) / MOD * 2)
            return max(abs(W - (MOD * nx2 / 2 + 20)), abs(H - (MOD * ny2 / 2 + 10)))
        self.donus = False
        if artik(H, W) + 0.5 < artik(W, H):
            self.donus = True
            govde = _dondur_segs(govde)
            x0, y0, x1, y1 = _bbox(govde); W, H = x1 - x0, y1 - y0
            self.notlar.append(f"Plan 90° döndürüldü (kısa kenar x'e alındı): kaynak {_r(H)}×{_r(W)} → {_r(W)}×{_r(H)}")
        self.segs_all = segs
        self.govde = govde
        self.x0, self.y0 = x0, y0
        self.W, self.H = W, H
        # yerel koordinatta duvar çizgileri: (a0, a1, c)
        self.yatay = [(s[1] - x0, s[2] - x0, s[3] - y0) for s in self.govde if s[0] == "x"]
        self.dusey = [(s[1] - y0, s[2] - y0, s[3] - x0) for s in self.govde if s[0] == "y"]
        return self.govde

    def P(self, x, y):
        """Ham DXF noktası → (döndürülmüş) yerel koordinat."""
        if self.donus:
            x, y = -y, x
        return (float(x) - self.x0, float(y) - self.y0)

    def _yuz_temas(self, yon, c, a):
        """(yon, c) yüz çizgisi üzerinde a noktasına değen (≤1 cm) duvar çizgisi var mı?"""
        cizgiler = self.yatay if yon == "x" else self.dusey
        return any(abs(cc - c) <= 0.6 and a0 - 1.0 <= a <= a1 + 1.0 for a0, a1, cc in cizgiler)

    def L(self, p):
        return self.P(p[0], p[1])

    # ---- 2. grid çözümü
    def grid_cozumle(self):
        nx = (self.W - 20.0) / MOD; ny = (self.H - 10.0) / MOD
        nx2, ny2 = round(nx * 2), round(ny * 2)
        rx = self.W - (MOD * nx2 / 2 + 20.0); ry = self.H - (MOD * ny2 / 2 + 10.0)
        self.artik = (_r(rx), _r(ry))
        if max(abs(rx), abs(ry)) <= GRID_TOL_CM:
            self.mod, self.aks_tol = "aks", MOD / 4 - 0.4      # duvarlar en yakın aksa; sapma raporlanır
        elif max(abs(rx), abs(ry)) <= MOD / 4 + 4:
            self.mod, self.aks_tol = "uyarlama", MOD / 4 - 0.4
            self.uyusmazlik.append(f"MODÜLE UYARLAMA: dış ölçü {_r(self.W)}×{_r(self.H)} modüle oturmuyor (artık W {_r(rx)}, H {_r(ry)} cm); "
                                   f"en yakın grid {nx2/2}×{ny2/2} ({_r(MOD*nx2/2+20)}×{_r(MOD*ny2/2+10)}) alındı, duvarlar en yakın aksa atandı — onay gerekir")
        else:
            raise CikarimHatasi(f"Dış kutu modüle oturmuyor: W={_r(self.W)} (artık {_r(rx)}), H={_r(self.H)} (artık {_r(ry)})")
        if self.mod == "aks" and (abs(rx) > 0.05 or abs(ry) > 0.05):
            self.uyusmazlik.append(f"Dış ölçü artığı: W {_r(rx)} cm, H {_r(ry)} cm (kural: 125,5·n+20 / +10)")
        self.nx2, self.ny2 = nx2, ny2
        self.nx, self.ny = nx2 / 2, ny2 / 2
        if nx2 < 4 or ny2 < 4:
            raise CikarimHatasi("Grid en az 2×2 pano olmalı")
        return self.nx, self.ny

    # ---- 3. semboller (pencere / kapı / veranda)
    def sembolleri_oku(self):
        pen_segs, kapi_polys, ver_segs = [], [], []
        for e in self.msp:
            kat = _norm(e.dxf.layer)
            if kat in PENCERE_KATMAN:
                _entity_segs(e, pen_segs, e.dxf.layer)
            elif kat in KAPI_KATMAN and e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()] if e.dxftype() == "LWPOLYLINE" else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                kapi_polys.append([self.L(p) for p in pts])
            elif kat in VERANDA_KATMAN:
                _entity_segs(e, ver_segs, e.dxf.layer)
        # yerel koordinata çevir, kutu içi süz
        def icinde(x, y):
            return -15 <= x <= self.W + 15 and -15 <= y <= self.H + 15
        if self.donus:
            pen_segs = _dondur_segs(pen_segs); ver_segs = _dondur_segs(ver_segs)
        self.pen_segs = []
        for s in pen_segs:
            if s[0] == "d": continue
            if s[0] == "x":
                a0, a1, c = s[1] - self.x0, s[2] - self.x0, s[3] - self.y0
                if icinde(a0, c): self.pen_segs.append(("x", a0, a1, c))
            else:
                a0, a1, c = s[1] - self.y0, s[2] - self.y0, s[3] - self.x0
                if icinde(c, a0): self.pen_segs.append(("y", a0, a1, c))
        self.kapi_polys = [p for p in kapi_polys if all(icinde(x, y) for x, y in p)]
        self.ver_segs = ver_segs
        # pencere kümeleri (bitişik kutular)
        kumeler = []
        for s in self.pen_segs:
            if s[0] == "x": bb = [s[1], s[3], s[2], s[3]]
            else: bb = [s[3], s[1], s[3], s[2]]
            yer = None
            for k in kumeler:
                if not (bb[0] > k[2] + 1.5 or bb[2] < k[0] - 1.5 or bb[1] > k[3] + 1.5 or bb[3] < k[1] - 1.5):
                    k[0], k[1], k[2], k[3] = min(k[0], bb[0]), min(k[1], bb[1]), max(k[2], bb[2]), max(k[3], bb[3]); yer = k; break
            if yer is None:
                kumeler.append(bb)
        # birleştirme turu (zincirleme)
        degisti = True
        while degisti:
            degisti = False
            for i in range(len(kumeler)):
                for j in range(i + 1, len(kumeler)):
                    a, b = kumeler[i], kumeler[j]
                    if not (a[0] > b[2] + 1.5 or a[2] < b[0] - 1.5 or a[1] > b[3] + 1.5 or a[3] < b[1] - 1.5):
                        kumeler[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                        kumeler.pop(j); degisti = True; break
                if degisti: break
        self.pencere_kutulari = [k for k in kumeler if max(k[2] - k[0], k[3] - k[1]) >= 30]
        # veranda profili (katman Veranda) bina kutusunun dışına taşıyor mu?
        vx, vy = [], []
        for sg in ver_segs:
            if sg[0] == "d": continue
            for pt in _seg_uclar(sg):
                lx, ly = pt[0] - self.x0, pt[1] - self.y0
                if -600 <= lx <= self.W + 600 and -600 <= ly <= self.H + 600:
                    vx.append(lx); vy.append(ly)
        self.veranda_tasma = None
        if vx:
            t = (max(0.0, -min(vx)), max(0.0, max(vx) - self.W), max(0.0, -min(vy)), max(0.0, max(vy) - self.H))
            if max(t) > 3:
                self.veranda_tasma = tuple(_r(v) for v in t)
                self.uyusmazlik.append(f"Veranda profili bina kutusunun dışına taşıyor (sol {t[0]:.1f}, sağ {t[1]:.1f}, ön {t[2]:.1f}, arka {t[3]:.1f} cm); "
                                       f"Motor v1 yalnız kutu içindeki kısmı çizer (L biçimli taban desteklenmiyor)")
        return self.pencere_kutulari, self.kapi_polys

    # ---- 3b. pencere sembolü olmayan çizimler: kasa çentikleri (duvar kalınlığını kesen kısa çizgiler) çiftlerinden pencere
    STANDART_PENCERE = (60, 90, 100, 120, 150, 180, 200)

    def pencereleri_centiklerden(self):
        """Katman 0'daki kasa çentikleri: aksa dik, duvar kalınlığı boyunda (5–12 cm) kısa çizgiler. Aynı aks üzerinde
        standart aralıklı (60/90/100/120/150/180/200 ±2) ardışık çift → pencere adayı (kapı ve Pencere-katmanı
        pencereleriyle çakışanlar elenir). Yalnız dış/açık tarafı olan duvarlarda kullanılır (pencere oraya konur)."""
        adaylar = []
        def centikler(cizgiler, c):
            out = []
            for a0, a1, cc in cizgiler:      # cizgiler: aksa dik çizgiler (a0,a1 = aks-dik doğrultudaki uzanım, cc = aks boyu konum)
                L = a1 - a0
                if 5 <= L <= 12.5 and a0 >= c - 11.5 and a1 <= c + 11.5:
                    out.append(cc)
            return sorted(set(round(v, 2) for v in out))
        def ciftle(pozlar):
            secilen, kullanilan = [], set()
            for i in range(len(pozlar) - 1):
                if i in kullanilan: continue
                d = pozlar[i + 1] - pozlar[i]
                if any(abs(d - w) <= 2.5 for w in self.STANDART_PENCERE):
                    secilen.append((pozlar[i], pozlar[i + 1])); kullanilan.add(i); kullanilan.add(i + 1)
            return secilen
        # düşey akslar: yatay kısa çizgiler (self.yatay: (a0,a1,y)) → cc=y
        for h in range(self.nx2 + 1):
            c = self._aks_x(h)
            poz = centikler([(a0, a1, y) for a0, a1, y in self.yatay], c)
            for p0, p1 in ciftle(poz):
                adaylar.append(("y", c, p0, p1))
        for h in range(self.ny2 + 1):
            c = self._aks_y(h)
            poz = centikler([(a0, a1, x) for a0, a1, x in self.dusey], c)
            for p0, p1 in ciftle(poz):
                adaylar.append(("x", c, p0, p1))
        # kapı ve mevcut pencere çakışmalarını ele
        kapilar = []
        for p in self.kapi_polys:
            if len(p) != 3: continue
            kp = self._kapi_coz(p)
            if kp: kapilar.append((kp["yon"], kp["c"], kp["a0"], kp["a1"]))
        mevcut = []
        for k in self.pencere_kutulari:
            if k[2] - k[0] >= k[3] - k[1]: mevcut.append(("x", (k[1] + k[3]) / 2, k[0], k[2]))
            else: mevcut.append(("y", (k[0] + k[2]) / 2, k[1], k[3]))
        eklenen = 0
        for yon, c, p0, p1 in adaylar:
            def cakisir(lst):
                return any(y == yon and abs(cc - c) <= 12 and min(b, p1) - max(a, p0) > 5 for y, cc, a, b in lst)
            if cakisir(kapilar) or cakisir(mevcut):
                continue
            if yon == "y": self.pencere_kutulari.append([c - 5, p0, c + 5, p1])
            else: self.pencere_kutulari.append([p0, c - 5, p1, c + 5])
            eklenen += 1
        if eklenen:
            self.notlar.append(f"{eklenen} pencere kasa çentiklerinden çıkarıldı (Pencere katmanı yok/eksik)")
        return eklenen

    # ---- 4. kenar duvar tespiti + taşkın dolgu
    def _aks_x(self, h): return G.X(h / 2)
    def _aks_y(self, h): return G.Y(h / 2)

    def duvar_kenarlari(self):
        """edge_y[(u, v)] : u=0..nx2 düşey kenar (hücre (u-1,v)|(u,v) arası); edge_x[(v, u)] : v=0..ny2 yatay kenar.
        Her duvar çizgisi EN YAKIN aksa atanır (|sapma| ≤ aks_tol); sapmalar aks başına raporlanır."""
        yatay = [(a0, a1, y) for a0, a1, y in self.yatay if a1 - a0 >= 3]
        dusey = [(a0, a1, x) for a0, a1, x in self.dusey if a1 - a0 >= 3]
        # kapatmalar: pencere kutuları ve kapı açıklıkları (aks boyunca aralık)
        kapatma_x, kapatma_y = [], []   # (c, a0, a1)
        for k in self.pencere_kutulari:
            if k[2] - k[0] >= k[3] - k[1]: kapatma_x.append(((k[1] + k[3]) / 2, k[0], k[2]))
            else: kapatma_y.append(((k[0] + k[2]) / 2, k[1], k[3]))
        for p in self.kapi_polys:
            kp = self._kapi_coz(p)
            if kp:
                if kp["yon"] == "x": kapatma_x.append((kp["c"], kp["a0"], kp["a1"]))
                else: kapatma_y.append((kp["c"], kp["a0"], kp["a1"]))
        def duvarlara_kumele(cizgiler):
            """Paralel yüz çizgilerini duvarlara kümele: aralarında ≤ 12 cm ve boyuna ≥ 15 cm örtüşme → aynı duvar.
            Döner: [(c_orta, [(a0,a1,c), ...])]"""
            n = len(cizgiler); parent = list(range(n))
            def find(i):
                while parent[i] != i:
                    parent[i] = parent[parent[i]]; i = parent[i]
                return i
            sirali = sorted(range(n), key=lambda i: cizgiler[i][2])
            for ii in range(n):
                i = sirali[ii]
                for jj in range(ii + 1, n):
                    j = sirali[jj]
                    if cizgiler[j][2] - cizgiler[i][2] > 12.5: break
                    if min(cizgiler[i][1], cizgiler[j][1]) - max(cizgiler[i][0], cizgiler[j][0]) >= 15:
                        ri, rj = find(i), find(j)
                        if ri != rj: parent[ri] = rj
            gruplar = {}
            for i in range(n):
                gruplar.setdefault(find(i), []).append(cizgiler[i])
            out = []
            for g in gruplar.values():
                cs = sorted(set(round(c, 2) for _, _, c in g))
                out.append(((cs[0] + cs[-1]) / 2, cs[-1] - cs[0], g))
            return out
        def ata(cizgiler, c0, n2, uzunluk_esik):
            """duvar kümelerini (orta eksene göre) en yakın aks indeksine dağıt; (h → [(a0,a1)]), (h → [(sapma, uzunluk, kalınlık)])"""
            hatlar, sapmalar = {}, {}
            for c_orta, kal, grup in duvarlara_kumele(cizgiler):
                h = round((c_orta - c0) / (MOD / 2))
                if not (0 <= h <= n2): continue
                sap = c_orta - (c0 + h * MOD / 2)
                if abs(sap) > self.aks_tol: continue
                uz = sum(a1 - a0 for a0, a1, _ in grup)
                hatlar.setdefault(h, []).extend((a0, a1) for a0, a1, _ in grup)
                if uz >= uzunluk_esik:
                    sapmalar.setdefault(h, []).append((sap, uz, kal))
            return hatlar, sapmalar
        y_hat, y_sap = ata(yatay, G.Y(0), self.ny2, 30)
        x_hat, x_sap = ata(dusey, G.X(0), self.nx2, 30)
        ky_hat, _ = ata([(a0, a1, c) for c, a0, a1 in kapatma_x], G.Y(0), self.ny2, 0)
        kx_hat, _ = ata([(a0, a1, c) for c, a0, a1 in kapatma_y], G.X(0), self.nx2, 0)
        edge_x, edge_y, detay = {}, {}, {}
        for v in range(self.ny2 + 1):
            cizgiler = y_hat.get(v, []); kap = ky_hat.get(v, [])
            for u in range(self.nx2):
                lo, hi = self._aks_x(u), self._aks_x(u + 1)
                k1 = _kaplama(cizgiler, lo, hi); k2 = _kaplama(kap, lo, hi)
                edge_x[(v, u)] = _kaplama(cizgiler + kap, lo, hi) / (hi - lo) >= KAPLAMA_ESIK
                detay[("x", v, u)] = (_r(k1), _r(k2))
        for u in range(self.nx2 + 1):
            cizgiler = x_hat.get(u, []); kap = kx_hat.get(u, [])
            for v in range(self.ny2):
                lo, hi = self._aks_y(v), self._aks_y(v + 1)
                k1 = _kaplama(cizgiler, lo, hi); k2 = _kaplama(kap, lo, hi)
                edge_y[(u, v)] = _kaplama(cizgiler + kap, lo, hi) / (hi - lo) >= KAPLAMA_ESIK
                detay[("y", u, v)] = (_r(k1), _r(k2))
        self.edge_x, self.edge_y, self.edge_detay = edge_x, edge_y, detay
        # aks sapmaları: duvar orta eksenlerinin aksa uzaklığı (dış duvar aks dışında olabilir: ±5 normal)
        self.aks_sapmalari = []
        for yon, sapd, n2 in (("Y", y_sap, self.ny2), ("X", x_sap, self.nx2)):
            for h, lst in sorted(sapd.items()):
                for sap, uz, kal in lst:
                    if uz < 60: continue
                    normal = 5.5 if (h in (0, n2) or kal >= 9) else 1.0     # dış duvar gövdesi aks dışında → ±5 normal
                    self.aks_sapmalari.append({"aks": f"{yon}({h/2})", "kayma": _r(sap), "kalinlik": _r(kal), "uzunluk": _r(uz)})
                    if abs(sap) > normal:
                        self.uyusmazlik.append(f"Duvar {yon}({h/2}) [{_r(kal)} cm, {_r(uz)} cm]: çizimde eksen aks{sap:+.2f} cm → bu aksa taşındı (uyarlama)")
        return edge_x, edge_y

    def taskin_dolgu(self):
        cells = {(u, v) for u in range(self.nx2) for v in range(self.ny2)}
        comp, gruplar = {}, []
        for c in sorted(cells):
            if c in comp: continue
            yigin, grup = [c], set()
            comp[c] = len(gruplar)
            while yigin:
                u, v = yigin.pop(); grup.add((u, v))
                komsu = []
                if not self.edge_y[(u, v)] and u - 1 >= 0: komsu.append((u - 1, v))
                if not self.edge_y[(u + 1, v)] and u + 1 < self.nx2: komsu.append((u + 1, v))
                if not self.edge_x[(v, u)] and v - 1 >= 0: komsu.append((u, v - 1))
                if not self.edge_x[(v + 1, u)] and v + 1 < self.ny2: komsu.append((u, v + 1))
                for n in komsu:
                    if n not in comp:
                        comp[n] = len(gruplar); yigin.append(n)
            gruplar.append(grup)
        self.gruplar = gruplar
        return gruplar

    # ---- 5. etiketler
    def etiketler(self):
        oda, pencere_etiket, diger, dis = [], [], [], []
        for e in self.msp.query("MTEXT TEXT"):
            ham = e.text if e.dxftype() == "MTEXT" else e.dxf.text
            t = _mtext_duz(ham)
            ix, iy = e.dxf.insert.x, e.dxf.insert.y
            if e.dxftype() == "MTEXT":
                ap = int(e.dxf.get("attachment_point", 1) or 1); w = float(e.dxf.get("width", 0.0) or 0.0); h = float(e.dxf.char_height or 10)
                satir_sayisi = max(1, ham.count("\\P") + 1)
                if w <= 0: w = 0.6 * h * max((len(sat) for sat in _mtext_duz(ham).split("\n")), default=4)
                if ap in (1, 4, 7): ix += w / 2
                elif ap in (3, 6, 9): ix -= w / 2
                if ap in (1, 2, 3): iy -= h * satir_sayisi * 0.8
                elif ap in (7, 8, 9): iy += h * satir_sayisi * 0.8
            x, y = self.L((ix, iy))
            if not (-40 <= x <= self.W + 40 and -40 <= y <= self.H + 40):
                continue
            m = PENCERE_OLCU_RE.search(t)
            if m and len(t) <= 12:
                pencere_etiket.append((x, y, int(m.group(1)), int(m.group(2)))); continue
            satirlar = [s.strip() for s in t.split("\n") if s.strip()]
            ad_satiri = next((s for s in satirlar if not M2_RE.search(s)), satirlar[0] if satirlar else "")
            m2 = None
            for s in satirlar:
                mm = M2_RE.search(s)
                if mm: m2 = float(mm.group(1).replace(",", "."))
            n = _norm(ad_satiri)
            hit = next(((kok, tur, acik) for anahtar, kok, tur, acik in AD_ESLEME if anahtar in n), None)
            if hit and 0 <= x <= self.W and 0 <= y <= self.H:
                oda.append({"x": x, "y": y, "metin": ad_satiri, "kok": hit[0], "tur": hit[1], "acik": hit[2], "m2": m2})
            elif hit and -250 <= x <= self.W + 250 and -250 <= y <= self.H + 250:
                dis.append({"x": x, "y": y, "metin": ad_satiri, "kok": hit[0], "tur": hit[1], "acik": hit[2], "m2": m2})
            else:
                diger.append((t[:40], _r(x), _r(y)))
        self.oda_etiketleri, self.pencere_etiketleri, self.diger_etiketler, self.dis_etiketler = oda, pencere_etiket, diger, dis
        return oda

    def _hucre(self, x, y):
        u = int(math.floor((x - G.X(0)) / (MOD / 2))); v = int(math.floor((y - G.Y(0)) / (MOD / 2)))
        return (min(max(u, 0), self.nx2 - 1), min(max(v, 0), self.ny2 - 1))

    def mahalleri_kur(self):
        gruplar = self.gruplar
        grup_etiket = {i: [] for i in range(len(gruplar))}
        for et in self.oda_etiketleri:
            c = self._hucre(et["x"], et["y"])
            gi = next(i for i, g in enumerate(gruplar) if c in g)
            grup_etiket[gi].append(et)
        # etiketsiz bölgeler: kutu dışı etiketler ve çok etiketli bölgelerin fazla etiketleri en yakın bölgeye taşınır
        yedek = list(self.dis_etiketler)
        for gi, g in enumerate(gruplar):
            if len(grup_etiket[gi]) > 1:
                ets = grup_etiket[gi]
                # bölge merkezine en yakın etiket kalır, diğerleri yedek havuzuna girmez (açık sınır olabilir) — yalnız kutu dışı etiketler taşınır
        def hucre_merkezleri(g):
            return [(G.X(u / 2) + MOD / 4, G.Y(v / 2) + MOD / 4) for (u, v) in g]
        for gi, g in enumerate(gruplar):
            if grup_etiket[gi] or not yedek:
                continue
            merk = hucre_merkezleri(g)
            def uzaklik(et):
                return min(math.hypot(et["x"] - cx, et["y"] - cy) for cx, cy in merk)
            en_yakin = min(yedek, key=uzaklik)
            if uzaklik(en_yakin) <= 300:
                grup_etiket[gi].append(en_yakin); yedek.remove(en_yakin)
                self.notlar.append(f"Kutu dışındaki '{en_yakin['metin']}' etiketi ({_r(en_yakin['x'])},{_r(en_yakin['y'])}) en yakın etiketsiz bölgeye atandı")
        mahaller = []   # (etiket, cells)
        self.dis_bolgeler = []
        for gi, g in enumerate(gruplar):
            ets = grup_etiket[gi]
            if len(ets) == 0:
                # bina dışı mı? (kutu kenarındaki kenarlarının çoğunda duvar yok → L/T tabanın boş köşesi)
                sinir, acik = 0, 0
                for (u, v) in g:
                    for (var, kenar) in ((u == 0, self.edge_y.get((0, v))), (u == self.nx2 - 1, self.edge_y.get((self.nx2, v))),
                                         (v == 0, self.edge_x.get((0, u))), (v == self.ny2 - 1, self.edge_x.get((self.ny2, u)))):
                        if var:
                            sinir += 1; acik += (0 if kenar else 1)
                if sinir >= 2 and acik >= max(2, sinir * 0.6):
                    self.dis_bolgeler.append(set(g))
                    self.uyusmazlik.append(f"Bina dışı bölge ({len(g)} yarım hücre, ilk hücre {min(g)}): taban dikdörtgen değil (L/T biçim) — Motor v1 desteklemiyor, bölge İş Emri'ne alınmadı")
                    continue
                self.uyusmazlik.append(f"Etiketsiz kapalı bölge ({len(g)} yarım hücre; ilk hücre {min(g)}) — 'MAHAL-{gi}' adı verildi")
                mahaller.append(({"kok": f"MAHAL-{gi}", "tur": "diger", "acik": False, "m2": None, "metin": ""}, set(g)))
            elif len(ets) == 1:
                mahaller.append((ets[0], set(g)))
            else:
                # açık sınır (duvarsız geçiş): hücreleri en yakın etikete ver
                self.uyusmazlik.append(f"Bir bölgede {len(ets)} etiket ({', '.join(e['metin'] for e in ets)}): duvarsız geçiş → en yakın etikete bölündü (acik_sinir)")
                parca = {id(e): set() for e in ets}
                for (u, v) in g:
                    cx, cy = G.X(u / 2) + MOD / 4, G.Y(v / 2) + MOD / 4
                    e = min(ets, key=lambda e: math.hypot(e["x"] - cx, e["y"] - cy))
                    parca[id(e)].add((u, v))
                for e in ets:
                    mahaller.append((e, parca[id(e)]))
                for i in range(len(ets)):
                    for j in range(i + 1, len(ets)):
                        self.acik_sinir_adaylari.append((ets[i], ets[j]))
        # adlandırma: aynı kökten birden çok → alana göre 1,2,...
        kokler = {}
        for et, cells in mahaller:
            kokler.setdefault(et["kok"], []).append((et, cells))
        self.mahaller = []
        for kok, lst in kokler.items():
            lst.sort(key=lambda t: -(t[0]["m2"] or len(t[1])))
            for i, (et, cells) in enumerate(lst):
                ad = kok if len(lst) == 1 else f"{kok} {i + 1}"
                et["ad"] = ad
                self.mahaller.append({"ad": ad, "tur": et["tur"], "acik": et["acik"], "cells": cells, "etiket": et})
        self.cell_owner = {c: m["ad"] for m in self.mahaller for c in m["cells"]}
        return self.mahaller

    @staticmethod
    def dikdortgenler(cells: set) -> list:
        """Yarım hücre kümesini en büyük dikdörtgenlerle (açgözlü) kapla; modül biriminde döner."""
        kalan = set(cells); out = []
        while kalan:
            en_iyi = None
            for (u0, v0) in sorted(kalan):
                # bu köşeden başlayan en geniş dikdörtgenler
                maxw = 0
                while (u0 + maxw, v0) in kalan: maxw += 1
                for w in range(1, maxw + 1):
                    h = 0
                    while all((u0 + i, v0 + h) in kalan for i in range(w)): h += 1
                    if en_iyi is None or w * h > en_iyi[0]:
                        en_iyi = (w * h, u0, v0, w, h)
            _, u0, v0, w, h = en_iyi
            for i in range(w):
                for j in range(h):
                    kalan.discard((u0 + i, v0 + j))
            out.append([u0 / 2, v0 / 2, (u0 + w) / 2, (v0 + h) / 2])
        out.sort(key=lambda r: (-(r[2] - r[0]) * (r[3] - r[1]), r[0], r[1]))
        return out

    # ---- 6. açıklıklar
    def _kapi_coz(self, pts):
        """3 noktalı kapı sembolü: iki nokta duvar yüzü üzerinde (kasa), üçüncü kanat ucu; menteşe = kanat ucuyla
        duvar boyu koordinatını paylaşan kasa noktası."""
        if len(pts) != 3:
            return None
        A, B, C = pts
        ciftler = [((A, B), C), ((A, C), B), ((B, C), A)]
        adaylar = []
        for (p, q), r in ciftler:
            if abs(p[1] - q[1]) < 0.6 and abs(p[0] - q[0]) > 20:      # yatay duvar yüzü adayı
                yon, c = "x", p[1]; a0, a1 = min(p[0], q[0]), max(p[0], q[0])
                mentese = p if abs(p[0] - r[0]) < 0.6 else (q if abs(q[0] - r[0]) < 0.6 else None)
                if mentese is None: continue
                # kasa noktalarına değen eş doğrultulu duvar çizgisi sayısı (kanat ucu için değil)
                puan = int(self._yuz_temas("x", c, a0)) + int(self._yuz_temas("x", c, a1))
                acilis = 1 if r[1] > c else -1
                adaylar.append((puan, {"yon": yon, "c": c, "a0": a0, "a1": a1, "genislik": a1 - a0, "mentese_a": mentese[0], "acilis": acilis, "kanat": r}))
            if abs(p[0] - q[0]) < 0.6 and abs(p[1] - q[1]) > 20:      # düşey duvar yüzü adayı
                yon, c = "y", p[0]; a0, a1 = min(p[1], q[1]), max(p[1], q[1])
                mentese = p if abs(p[1] - r[1]) < 0.6 else (q if abs(q[1] - r[1]) < 0.6 else None)
                if mentese is None: continue
                puan = int(self._yuz_temas("y", c, a0)) + int(self._yuz_temas("y", c, a1))
                acilis = 1 if r[0] > c else -1
                adaylar.append((puan, {"yon": yon, "c": c, "a0": a0, "a1": a1, "genislik": a1 - a0, "mentese_a": mentese[1], "acilis": acilis, "kanat": r}))
        if not adaylar:
            return None
        adaylar.sort(key=lambda t: -t[0])
        if len(adaylar) > 1 and adaylar[0][0] == adaylar[1][0]:
            self.uyusmazlik.append(f"Kapı sembolü belirsiz (iki kasa adayı eşit puanlı): {[(_r(x), _r(y)) for x, y in pts]}")
        return adaylar[0][1]

    def _en_yakin_aks(self, yon, c):
        if yon == "x":
            h = round((c - G.Y(0)) / (MOD / 2)); h = min(max(h, 0), self.ny2); return h, c - self._aks_y(h)
        h = round((c - G.X(0)) / (MOD / 2)); h = min(max(h, 0), self.nx2); return h, c - self._aks_x(h)

    def _komsu_odalar(self, yon, hat, a_orta):
        """Aks hattının iki yanındaki hücre sahipleri (neg, pos) — pos: +y (yatay duvar) / +x (düşey duvar)."""
        if yon == "x":
            u = int(math.floor((a_orta - G.X(0)) / (MOD / 2))); u = min(max(u, 0), self.nx2 - 1)
            neg = self.cell_owner.get((u, hat - 1), G.OUT) if hat - 1 >= 0 else G.OUT
            pos = self.cell_owner.get((u, hat), G.OUT) if hat < self.ny2 else G.OUT
        else:
            v = int(math.floor((a_orta - G.Y(0)) / (MOD / 2))); v = min(max(v, 0), self.ny2 - 1)
            neg = self.cell_owner.get((hat - 1, v), G.OUT) if hat - 1 >= 0 else G.OUT
            pos = self.cell_owner.get((hat, v), G.OUT) if hat < self.nx2 else G.OUT
        return neg, pos

    def _acik_mi(self, ad):
        if ad == G.OUT: return True
        return next(m["acik"] for m in self.mahaller if m["ad"] == ad)

    def acikliklari_cikar(self):
        acikliklar = []
        # pencereler
        for k in self.pencere_kutulari:
            yatay = (k[2] - k[0]) >= (k[3] - k[1])
            if yatay: yon, c, a0, a1 = "x", (k[1] + k[3]) / 2, k[0], k[2]
            else: yon, c, a0, a1 = "y", (k[0] + k[2]) / 2, k[1], k[3]
            hat, sapma = self._en_yakin_aks(yon, c)
            if abs(sapma) > self.aks_tol:
                self.uyusmazlik.append(f"Pencere ({_r(a0)}–{_r(a1)}) hiçbir aksa oturmuyor (sapma {_r(sapma)})"); continue
            orta = (a0 + a1) / 2
            neg, pos = self._komsu_odalar(yon, hat, orta)
            # mahal: kapalı taraf
            if not self._acik_mi(neg) and self._acik_mi(pos): mahal, taraf = neg, -1
            elif not self._acik_mi(pos) and self._acik_mi(neg): mahal, taraf = pos, +1
            elif not self._acik_mi(neg) and not self._acik_mi(pos):
                self.uyusmazlik.append(f"Pencere ({_r(a0)}–{_r(a1)}) iki kapalı mahal arasında ({neg}/{pos}); {neg} alındı"); mahal, taraf = neg, -1
            else:
                self.uyusmazlik.append(f"Pencere ({_r(a0)}–{_r(a1)}) iki açık taraf arasında; atlandı"); continue
            # mahalin hangi duvarı: taraf -1 → mahal aksın eksi yanında → duvar mahalin +yönünde
            if yon == "x": duvar = "arka" if taraf == -1 else "on"
            else: duvar = "sag" if taraf == -1 else "sol"
            # ölçü etiketi (en yakın)
            etiket = None
            if self.pencere_etiketleri:
                cx, cy = (orta, c) if yon == "x" else (c, orta)
                etiket = min(self.pencere_etiketleri, key=lambda e: math.hypot(e[0] - cx, e[1] - cy))
                if math.hypot(etiket[0] - cx, etiket[1] - cy) > 120: etiket = None
            gen = a1 - a0
            if etiket:
                w, h = etiket[2], etiket[3]
                if abs(w - gen) > 3:
                    self.uyusmazlik.append(f"{mahal} {duvar} penceresi: etiket {w}/{h} ama çizim genişliği {_r(gen)}")
                olcu = f"{w}x{h}"
            else:
                w = int(round(gen)); olcu = {120: "120x120", 60: "60x40"}.get(w, f"{w}x?")
                self.uyusmazlik.append(f"{mahal} {duvar} penceresi: ölçü etiketi bulunamadı, genişlikten {olcu}")
            kaynak_olcu = olcu
            if olcu not in G.PENCERE_OLCULERI:
                try:
                    w0, h0 = (int(v) for v in olcu.lower().split("x"))
                except Exception:
                    w0, h0 = int(round(gen)), 120
                olcu = min(G.PENCERE_OLCULERI, key=lambda k: abs(G.PENCERE_OLCULERI[k][0] - w0) * 2 + abs(G.PENCERE_OLCULERI[k][1] - h0))
                self.uyusmazlik.append(f"{mahal} {duvar} penceresi: katalog dışı ölçü {kaynak_olcu} → çizim için en yakın katalog ölçüsü {olcu} (UYARLAMA, onay gerekir)")
            acikliklar.append({"tur": "pencere", "olcu": olcu, "mahal": mahal, "duvar": duvar,
                               "_kaynak": {"yon": yon, "hat": hat, "a0": _r(a0), "a1": _r(a1), "orta": _r(orta), "aks_sapma": _r(sapma), "kaynak_olcu": kaynak_olcu}})
        # kapılar
        for p in self.kapi_polys:
            if len(p) == 2:
                continue        # kapı eşik/karşı yüz çizgisi (3 noktalı sembolün eşlikçisi)
            kp = self._kapi_coz(p)
            if not kp:
                self.uyusmazlik.append(f"Kapı sembolü çözülemedi: {[(_r(x), _r(y)) for x, y in p]}"); continue
            hat, sapma = self._en_yakin_aks(kp["yon"], kp["c"])
            if abs(sapma) > self.aks_tol:
                self.uyusmazlik.append(f"Kapı ({_r(kp['a0'])}–{_r(kp['a1'])}) hiçbir aksa oturmuyor (sapma {_r(sapma)})"); continue
            orta = (kp["a0"] + kp["a1"]) / 2
            neg, pos = self._komsu_odalar(kp["yon"], hat, orta)
            icine, disindan = (pos, neg) if kp["acilis"] > 0 else (neg, pos)
            if G.OUT in (icine, disindan):
                self.uyusmazlik.append(f"Kapı ({_r(kp['a0'])}–{_r(kp['a1'])}) bina dışına açılıyor; Motor v1 dışa açılan kapıyı desteklemiyor — atlandı"); continue
            if icine == disindan:
                self.uyusmazlik.append(f"Kapı ({_r(kp['a0'])}–{_r(kp['a1'])}) aynı mahalin ({icine}) iki hücresi arasında (duvar akslara oturmadı) — atlandı"); continue
            tur = "dis_kapi" if (self._acik_mi(icine) or self._acik_mi(disindan)) else "ic_kapi"
            # menteşe: a(dışından) → b(içine) bakarken sağ/sol
            # yatay duvar: bakış +y ise sağ = +x; bakış -y ise sağ = -x. düşey duvar: bakış +x ise sağ = -y; bakış -x ise sağ = +y
            h_ofs = kp["mentese_a"] - orta
            if kp["yon"] == "x": sag = (h_ofs > 0) if kp["acilis"] > 0 else (h_ofs < 0)
            else: sag = (h_ofs < 0) if kp["acilis"] > 0 else (h_ofs > 0)
            std = 82.0 if tur == "ic_kapi" else 90.0
            if abs(kp["genislik"] - std) > 1:
                self.uyusmazlik.append(f"{disindan}→{icine} kapısı: çizimde {_r(kp['genislik'])} cm, İş Emri {int(std)} (standart)")
            acikliklar.append({"tur": tur, "olcu": int(std), "arasi": [disindan, icine], "mentese": "sag" if sag else "sol",
                               "_kaynak": {"yon": kp["yon"], "hat": hat, "a0": _r(kp["a0"]), "a1": _r(kp["a1"]), "orta": _r(orta),
                                           "genislik": _r(kp["genislik"]), "aks_sapma": _r(sapma)}})
        self.acikliklar = acikliklar
        return acikliklar

    # ---- 7. İş Emri ve pano indeksleri (Motor ile birebir)
    def is_emri(self, kod: str | None = None) -> dict:
        kod = kod or self.path.stem
        mahaller = []
        for m in self.mahaller:
            mahaller.append({"ad": m["ad"], "tur": m["tur"], "konum_pano": self.dikdortgenler(m["cells"])})
        acik_sinirlar = [[a["ad"], b["ad"]] for a, b in self.acik_sinir_adaylari]
        ie = {
            "is_emri_no": f"PM-KATALOG-{kod}",
            "revizyon": 1,
            "talep": {"bayi": {"kod": "KATALOG", "ad": "Çıkarıcı"}, "musteri_adi": f"KATALOG {kod}",
                      "metin": f"{self.path.name} dosyasından otomatik çıkarıldı (motor/cikarici v0.1)"},
            "yapi": {"sistem": "prefabrik", "kat_sayisi": 1, "duvar_yuksekligi_cm": 250, "olcu_kaynagi": "serbest",
                     "referans_model": kod, "grid": {"x_pano": self.nx, "y_pano": self.ny}, "kisa_kenar": "x",
                     "giris_cephesi": "on", "dis_dusey_duvar": "aks_disinda"},
            "mahaller": mahaller,
            "acik_sinirlar": acik_sinirlar,
            "acikliklar": [{k: v for k, v in a.items() if not k.startswith("_")} for a in self.acikliklar],
            "cati": {"tip": "besik", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "kisa_kenar"},
            "cikti": {"pdf": True, "dxf": True, "pafta": "A2", "icerik": ["aksli_plan", "alanli_kopya", "montaj_kopyasi", "on_gorunus", "cati_profili", "ozellik_tablosu"]},
            "varsayimlar": [f"Otomatik çıkarım: {self.path.name}; kaynak konumlar ve artıklar cikarim_raporu.json'da."],
            "eksikler": [],
        }
        # pano indeksleri: Motor'un aday listesi
        self._pano_indeksleri(ie)
        return ie

    def _pano_indeksleri(self, ie):
        try:
            plan = G.kur({**ie, "acikliklar": []})     # panolar açıklıklardan bağımsız; çakışma denetimi sonra
        except G.IsEmriHatasi as e:
            self.uyusmazlik.append(f"Motor İş Emri'ni kurmadı (pano indeksleri hesaplanamadı): {e}")
            return
        NORMAL = {"sol": "-x", "sag": "+x", "on": "-y", "arka": "+y"}
        for ac, ham in zip(ie["acikliklar"], self.acikliklar):
            k = ham["_kaynak"]
            if ac["tur"] == "pencere":
                w = G.PENCERE_OLCULERI[ac["olcu"]][0] if ac["olcu"] in G.PENCERE_OLCULERI else k["a1"] - k["a0"]
                cand = G._edges_of_room_side(plan.duvarlar, ac["mahal"], NORMAL[ac["duvar"]])
            else:
                w = float(ac["olcu"]); cand = G._edges_between(plan.duvarlar, ac["arasi"][0], ac["arasi"][1])
            panolar = []
            for d, k0, k1 in cand:
                lo = G.X(k0 / 2) if d.yon == "x" else G.Y(k0 / 2)
                hi = G.X(k1 / 2) if d.yon == "x" else G.Y(k1 / 2)
                for p in d.panolar:
                    mid = (p.a0 + p.a1) / 2
                    if mid - w / 2 >= lo - 1e-6 and mid + w / 2 <= hi + 1e-6 and p not in [q for _, q in panolar]:
                        panolar.append((d, p))
            panolar.sort(key=lambda dp: dp[1].a0)
            if not panolar:
                self.uyusmazlik.append(f"{ac['tur']} {ac.get('mahal') or ac.get('arasi')}: Motor'da uygun pano yok"); continue
            # kaynak açıklıkla en çok örtüşen pano — yalnız kaynakla aynı doğrultu ve aks hattındaki duvarlar
            ayni_hat = [i for i, (d, p) in enumerate(panolar) if d.yon == k["yon"] and d.hat == k["hat"]]
            if not ayni_hat:
                self.uyusmazlik.append(f"{ac['tur']} {ac.get('mahal') or ac.get('arasi')}: kaynak açıklığın duvarı ({k['yon']} hat {k['hat']/2}) Motor aday listesinde yok; ilk aday alındı")
                ayni_hat = list(range(len(panolar)))
            en = max(ayni_hat, key=lambda i: min(panolar[i][1].a1, k["a1"]) - max(panolar[i][1].a0, k["a0"]))
            d, p = panolar[en]
            ortusme = min(p.a1, k["a1"]) - max(p.a0, k["a0"])
            motor_orta = (p.a0 + p.a1) / 2
            fark = k["orta"] - motor_orta
            k["motor_pano"] = [_r(p.a0), _r(p.a1)]; k["motor_orta"] = _r(motor_orta); k["fark_cm"] = _r(fark); k["aday_sayisi"] = len(panolar)
            if ortusme < w * 0.5:
                self.uyusmazlik.append(f"{ac['tur']} {ac.get('mahal') or ac.get('arasi')}: kaynak açıklık ({k['a0']}–{k['a1']}) hiçbir aday panoyla yarıdan çok örtüşmüyor")
            varsayilan = (len(panolar) - 1) // 2
            if en != varsayilan or len(panolar) > 1:
                ac["pano"] = en; ham["pano"] = en
            if abs(fark) > 3:
                self.uyusmazlik.append(f"{ac['tur']} {ac.get('mahal') or ' → '.join(ac.get('arasi', []))} ({ac.get('duvar', '')}): kaynak merkez {k['orta']}, Motor pano merkezi {_r(motor_orta)} → fark {_r(fark)} cm (pano {en}/{len(panolar)})")
        for _ in range(12):
            try:
                self.plan = G.kur(ie); break
            except G.IsEmriHatasi as e:
                msg = str(e)
                # hatayı doğuran açıklığı bul (mesajda sözlük gösterimi var) ve düşür
                dusen = None
                for i, ac in enumerate(ie["acikliklar"]):
                    if str(ac) in msg or (ac.get("mahal") and f"{ac['mahal']} mahalinin" in msg) or (ac.get("arasi") and f"{ac['arasi'][0]}–{ac['arasi'][1]}" in msg):
                        dusen = i; break
                if dusen is None:
                    self.uyusmazlik.append(f"Motor İş Emri'ni kurmadı: {msg[:200]}"); self.plan = plan; break
                ac = ie["acikliklar"].pop(dusen); self.acikliklar.pop(dusen)
                self.uyusmazlik.append(f"Açıklık düşürüldü (Motor: {msg[:120]}): {ac.get('tur')} {ac.get('mahal') or ac.get('arasi')}")
                ie.setdefault("eksikler", []).append(f"{ac.get('tur')} {ac.get('mahal') or ac.get('arasi')}: {msg[:100]}")

    # ---- 8. hepsi
    def calistir(self, kod=None):
        self.acik_sinir_adaylari = []
        self.duvar_govdesi(); self.grid_cozumle(); self.sembolleri_oku(); self.pencereleri_centiklerden(); self.etiketler()
        self.duvar_kenarlari(); self.taskin_dolgu(); self.mahalleri_kur()
        self.acikliklari_cikar()
        ie = self.is_emri(kod)
        return ie

    def rapor(self, ie) -> dict:
        return {
            "dosya": self.path.name, "kutu": {"x0": _r(self.x0), "y0": _r(self.y0), "W": _r(self.W), "H": _r(self.H)},
            "grid": {"x_pano": self.nx, "y_pano": self.ny},
            "mahaller": [{"ad": m["ad"], "tur": m["tur"], "etiket": m["etiket"].get("metin"), "etiket_m2": m["etiket"].get("m2"),
                          "yarim_hucre": len(m["cells"]), "brut_m2": _r(len(m["cells"]) * (MOD / 2) ** 2 / 1e4)} for m in self.mahaller],
            "acikliklar": [{**{k: v for k, v in a.items() if not k.startswith("_")}, "kaynak": a["_kaynak"]} for a in self.acikliklar],
            "aks_sapmalari": self.aks_sapmalari, "mod": self.mod, "artik": self.artik, "donus": self.donus,
            "uyusmazlik": self.uyusmazlik, "notlar": self.notlar,
            "diger_etiketler": self.diger_etiketler,
            "motor_uyarilari": getattr(self, "plan", None).uyarilar if getattr(self, "plan", None) else None,
        }


# ----------------------------------------------------------------------------- tanı görseli
def tani_png(cik: "Cikarici", ie: dict, yol: Path):
    """Hücre sahipliği + tespit edilen duvar kenarları + pencere/kapı + etiket çapaları (kaynak çizgileriyle üst üste)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(9, 9 * cik.H / cik.W))
    renkler = plt.cm.tab20.colors
    adlar = [m["ad"] for m in cik.mahaller]
    for m in cik.mahaller:
        col = renkler[adlar.index(m["ad"]) % len(renkler)]
        for (u, v) in m["cells"]:
            ax.add_patch(Rectangle((G.X(u / 2), G.Y(v / 2)), MOD / 2, MOD / 2, facecolor=col, alpha=0.35, edgecolor="none"))
    for a0, a1, y in cik.yatay:
        ax.plot([a0, a1], [y, y], color="k", lw=0.6)
    for a0, a1, x in cik.dusey:
        ax.plot([x, x], [a0, a1], color="k", lw=0.6)
    for (v, u), var in cik.edge_x.items():
        if var: ax.plot([G.X(u / 2), G.X((u + 1) / 2)], [G.Y(v / 2)] * 2, color="red", lw=1.4, alpha=0.7)
    for (u, v), var in cik.edge_y.items():
        if var: ax.plot([G.X(u / 2)] * 2, [G.Y(v / 2), G.Y((v + 1) / 2)], color="red", lw=1.4, alpha=0.7)
    for k in cik.pencere_kutulari:
        ax.add_patch(Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], facecolor="deepskyblue", edgecolor="blue", lw=1))
    for p in cik.kapi_polys:
        if len(p) == 3:
            xs = [q[0] for q in p] + [p[0][0]]; ys = [q[1] for q in p] + [p[0][1]]
            ax.plot(xs, ys, color="green", lw=1)
    for et in cik.oda_etiketleri:
        ax.plot(et["x"], et["y"], "k+", ms=8)
        ax.text(et["x"], et["y"] + 8, et.get("ad", et["kok"]), fontsize=6, ha="center", color="darkblue")
    for m in cik.mahaller:
        us = [u for u, v in m["cells"]]; vs = [v for u, v in m["cells"]]
        ax.text(G.X((min(us) + max(us) + 1) / 4), G.Y((min(vs) + max(vs) + 1) / 4), m["ad"], fontsize=7, ha="center", va="center", weight="bold")
    ax.set_xlim(-30, cik.W + 30); ax.set_ylim(-30, cik.H + 30); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(f"{cik.path.name} {cik.plan_secici or ''} — {cik.nx}×{cik.ny} ({cik.mod})", fontsize=9)
    fig.savefig(yol, dpi=120, bbox_inches="tight", facecolor="white"); plt.close(fig)


# ----------------------------------------------------------------------------- şablonla karşılaştırma
def _cells(ie):
    out = {}
    for m in ie["mahaller"]:
        s = set()
        for r in m["konum_pano"]:
            s |= G._cells_of_rect([float(v) for v in r])
        out[m["ad"]] = s
    return out


def _etkin_pano(ie, ac):
    """Şablondaki açıklığın etkin pano indeksi ve Motor konumu (verilmemişse Motor varsayılanı)."""
    try:
        plan = G.kur(ie)
    except G.IsEmriHatasi:
        return None
    NORMAL = {"sol": "-x", "sag": "+x", "on": "-y", "arka": "+y"}
    if ac["tur"] == "pencere":
        w = G.PENCERE_OLCULERI[ac["olcu"]][0]; cand = G._edges_of_room_side(plan.duvarlar, ac["mahal"], NORMAL[ac["duvar"]])
    else:
        w = float(ac.get("olcu", G.KAPI_GENISLIK[ac["tur"]])); cand = G._edges_between(plan.duvarlar, ac["arasi"][0], ac["arasi"][1])
    panolar = []
    for d, k0, k1 in cand:
        lo = G.X(k0 / 2) if d.yon == "x" else G.Y(k0 / 2); hi = G.X(k1 / 2) if d.yon == "x" else G.Y(k1 / 2)
        for p in d.panolar:
            mid = (p.a0 + p.a1) / 2
            if mid - w / 2 >= lo - 1e-6 and mid + w / 2 <= hi + 1e-6 and p not in [q for _, q in panolar]:
                panolar.append((d, p))
    panolar.sort(key=lambda dp: dp[1].a0)
    if not panolar: return None
    idx = ac.get("pano"); idx = (len(panolar) - 1) // 2 if idx is None else idx
    if not (0 <= idx < len(panolar)): return None
    d, p = panolar[idx]
    return {"pano": idx, "aday": len(panolar), "a0": _r(p.a0), "a1": _r(p.a1), "orta": _r((p.a0 + p.a1) / 2)}


def karsilastir(ie: dict, sablon: dict, cik: "Cikarici") -> dict:
    r = {"grid": {"cikarim": ie["yapi"]["grid"], "sablon": sablon["yapi"]["grid"], "esit": ie["yapi"]["grid"] == sablon["yapi"]["grid"]},
         "mahaller": [], "acikliklar": [], "ozet": {}}
    c1, c2 = _cells(ie), _cells(sablon)
    ok_m = 0
    for ad in sorted(set(c1) | set(c2)):
        a, b = c1.get(ad), c2.get(ad)
        if a is None or b is None:
            r["mahaller"].append({"ad": ad, "durum": "yalnız çıkarımda" if b is None else "yalnız şablonda"}); continue
        fark1, fark2 = sorted(a - b), sorted(b - a)
        esit = not fark1 and not fark2; ok_m += esit
        r["mahaller"].append({"ad": ad, "durum": "eşit" if esit else "farklı", "yarim_hucre": len(a),
                              "fazla": [[u / 2, v / 2] for u, v in fark1][:10], "eksik": [[u / 2, v / 2] for u, v in fark2][:10]})

    def anahtar(ac):
        return ("pencere", ac["mahal"], ac["duvar"]) if ac["tur"] == "pencere" else (ac["tur"], frozenset(ac["arasi"]))
    s_map = {}
    for ac in sablon["acikliklar"]:
        s_map.setdefault(anahtar(ac), []).append(ac)
    ok_a = 0
    for ac, ham in zip(ie["acikliklar"], cik.acikliklar):
        k = anahtar(ac); es = s_map.get(k, [])
        satir = {"cikarim": {kk: v for kk, v in ac.items()}, "kaynak": ham["_kaynak"]}
        if not es:
            satir["durum"] = "şablonda yok"
        else:
            s = es.pop(0); satir["sablon"] = s
            farklar = []
            if str(ac.get("olcu")) != str(s.get("olcu")): farklar.append(f"ölçü {ac.get('olcu')} ≠ {s.get('olcu')}")
            if ac["tur"] != "pencere" and ac["arasi"] != s["arasi"]: farklar.append(f"yön {ac['arasi']} ≠ {s['arasi']}")
            if ac.get("mentese") and ac.get("mentese") != s.get("mentese", "sag"): farklar.append(f"menteşe {ac.get('mentese')} ≠ {s.get('mentese', 'sag')}")
            ep_c = _etkin_pano(ie, ac); ep_s = _etkin_pano(sablon, s)
            satir["etkin_pano"] = {"cikarim": ep_c, "sablon": ep_s}
            if ep_c and ep_s and ep_c["pano"] != ep_s["pano"]:
                farklar.append(f"pano {ep_c['pano']} ≠ {ep_s['pano']} (şablon {'varsayılan' if s.get('pano') is None else 'açık'})")
            satir["durum"] = "eşit" if not farklar else "farklı"; satir["farklar"] = farklar; ok_a += not farklar
        r["acikliklar"].append(satir)
    for k, lst in s_map.items():
        for s in lst:
            r["acikliklar"].append({"sablon": s, "durum": "çıkarımda yok"})
    r["ozet"] = {"mahal_esit": f"{ok_m}/{max(len(c1), len(c2))}", "aciklik_esit": f"{ok_a}/{max(len(ie['acikliklar']), len(sablon['acikliklar']))}",
                 "uyusmazlik_sayisi": len(cik.uyusmazlik)}
    return r


def _md_rapor(ie, rap, kars) -> str:
    L = [f"# Çıkarım raporu — {rap['dosya']}", "",
         f"Dış kutu {rap['kutu']['W']} × {rap['kutu']['H']} cm → grid **{rap['grid']['x_pano']} × {rap['grid']['y_pano']} pano**.", ""]
    L += ["## Mahaller", "| Ad | Tür | Etiket | Etiket m² | Brüt m² (hücre) | Şablon |", "|---|---|---|---|---|---|"]
    kmap = {m["ad"]: m for m in kars["mahaller"]} if kars else {}
    for m in rap["mahaller"]:
        d = kmap.get(m["ad"], {}).get("durum", "—")
        if d == "farklı":
            d += f" (fazla {kmap[m['ad']]['fazla']}, eksik {kmap[m['ad']]['eksik']})"
        L.append(f"| {m['ad']} | {m['tur']} | {m['etiket']} | {m['etiket_m2']} | {m['brut_m2']} | {d} |")
    L += ["", "## Açıklıklar (kaynak konum → Motor pano)", "| Tür | Mahal / arası | Duvar | Ölçü | Pano | Menteşe | Kaynak (cm) | Motor pano merkezi | Fark | Şablon |", "|---|---|---|---|---|---|---|---|---|---|"]
    kl = kars["acikliklar"] if kars else [None] * len(rap["acikliklar"])
    for a, k in zip(rap["acikliklar"], kl):
        src = a["kaynak"]
        d = k.get("durum", "") if k else "—"
        if k and k.get("farklar"): d += ": " + "; ".join(k["farklar"])
        L.append(f"| {a['tur']} | {a.get('mahal') or ' → '.join(a['arasi'])} | {a.get('duvar', '')} | {a['olcu']} | {a.get('pano', 'vars.')} | {a.get('mentese', '')} | "
                 f"{src['a0']}–{src['a1']} | {src.get('motor_orta', '?')} ({src.get('motor_pano', '?')}) | {src.get('fark_cm', '?')} | {d} |")
    if kars:
        for k in kars["acikliklar"]:
            if k.get("durum") == "çıkarımda yok":
                s = k["sablon"]; L.append(f"| {s['tur']} | {s.get('mahal') or ' → '.join(s['arasi'])} | {s.get('duvar', '')} | {s['olcu']} | | | | | | çıkarımda yok |")
    L += ["", "## Uyuşmazlıklar (çizim ≠ kural) ve notlar"]
    L += [f"- {u}" for u in rap["uyusmazlik"]] or ["- (yok)"]
    L += [f"- (not) {n}" for n in rap["notlar"]]
    if rap.get("motor_uyarilari"):
        L += ["", "## Motor uyarıları"] + [f"- {u}" for u in rap["motor_uyarilari"]]
    if kars:
        L += ["", f"**Özet:** mahal {kars['ozet']['mahal_esit']} eşit, açıklık {kars['ozet']['aciklik_esit']} eşit, {kars['ozet']['uyusmazlik_sayisi']} uyuşmazlık."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="DXF → İş Emri çıkarıcı")
    ap.add_argument("dxf"); ap.add_argument("--kod"); ap.add_argument("--sablon"); ap.add_argument("--cikti", default=None)
    ap.add_argument("--secici", help="Master DXF'te plan etiketi (ör. P7001)")
    ap.add_argument("--motor", action="store_true", help="Çıkarılan İş Emri'ni Motor ile çiz")
    a = ap.parse_args(argv)
    cik = Cikarici(a.dxf, plan_secici=a.secici)
    ie = cik.calistir(a.kod or a.secici)
    rap = cik.rapor(ie)
    kars = None
    if a.sablon:
        sablon = json.loads(Path(a.sablon).read_text(encoding="utf-8"))
        kars = karsilastir(ie, sablon, cik)
    out = Path(a.cikti or (ROOT / "cikti" / "cikarici" / (a.kod or a.secici or Path(a.dxf).stem)))
    out.mkdir(parents=True, exist_ok=True)
    (out / "is_emri.json").write_text(json.dumps(ie, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "cikarim_raporu.json").write_text(json.dumps({"rapor": rap, "karsilastirma": kars}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    md = _md_rapor(ie, rap, kars)
    (out / "cikarim_raporu.md").write_text(md, encoding="utf-8")
    try:
        tani_png(cik, ie, out / "tani.png")
    except Exception as e:  # tanı görseli isteğe bağlı
        print("tanı görseli üretilemedi:", e)
    print(md)
    if a.motor:
        from motor import dxf_out
        res = dxf_out.uret(ie, out / "motor")
        print("Motor:", {k: v for k, v in res.items() if k in ("dxf", "pdf", "sure_s", "dogrulama")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
