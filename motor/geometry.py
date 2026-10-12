"""Portman motor v1.1 — geometri çekirdeği.

İş Emri (pano birimli, JSON) → cm cinsinden duvarlar, panolar, köşe parçaları,
açıklıklar, veranda dikmeleri ve net alan poligonları. Çizim (DXF/PDF) ayrı modüldedir.

Kural kaynağı: prefabrik-cizim-kurallari.md v1.4.3, onaylı 2+1 / 6×8 örneği (Astra, 13 Eylül)
ve Yan Verandalı 6×8,5 projesi (7 Eylül, v1.4.3 BOM'lu son örnek).
Bütün ölçüler cm. Koordinat: sol-alt dış köşe (0,0); +x sağa, +y arkaya (kuzey).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math

from shapely.geometry import box, Polygon, MultiPolygon
from shapely.ops import unary_union

MOD = 125.5          # tam pano
T_DIS = 10.0         # dış duvar kalınlığı
T_IC = 6.0           # iç duvar kalınlığı
OUT = "__DIS__"      # bina dışı
X_SON = Y_SON = None  # ölçüye kesimde son aksın yeri (cm); yoksa None

PENCERE_OLCULERI = {"120x120": (120, 120), "120x180": (120, 180), "60x40": (60, 40)}
KAPI_GENISLIK = {"ic_kapi": 82.0, "dis_kapi": 97.0, "gecis": 82.0}
ACIK_MAHAL_TURLERI = {"veranda", "balkon", "sundurma", "teras"}


class IsEmriHatasi(ValueError):
    pass


YENI_ANAHTARLAR = ("duvar_kalinligi_cm", "dis_olcu_cm", "dizilim", "ek_akslar_cm")   # İE-11 (6 Ekim denemesi + genişletme)


def yeni_anahtar_var(is_emri: dict) -> bool:
    """İE-11 anahtarlarından biri varsa True. Yoksa Motor eski İş Emri'nde bayt bayt aynı çıktıyı verir (altın testler)."""
    yapi = is_emri.get("yapi", {})
    return any(k in yapi for k in YENI_ANAHTARLAR) or any("konum_cm" in m for m in is_emri.get("mahaller", [])) \
        or any(("konum_cm" in a) or ("hizalama" in a) or ("dograma" in a) for a in is_emri.get("acikliklar", []))


def kalinlik_ayarla(dis_cm: float, ic_cm: float) -> None:
    """Deneme: dış / iç duvar kalınlığı (cm). Verilmezse 10 / 6."""
    global T_DIS, T_IC
    if not (6.0 <= ic_cm <= dis_cm <= 30.0):
        raise IsEmriHatasi(f"Duvar kalınlığı aralık dışı: dış {dis_cm} / iç {ic_cm} cm")
    if dis_cm == ic_cm:
        raise IsEmriHatasi("Dış ve iç duvar aynı kalınlıkta: katman adları ayrışmıyor (deneme sınırı)")
    T_DIS, T_IC = float(dis_cm), float(ic_cm)


def olcu_ayarla(dis_olcu, nx: float, ny: float) -> None:
    """Deneme: dış ölçü verilirse (cm) son aks yapının bitişine çekilir; son pano özel ölçülü olur. Verilmezse akslar tam modüldür."""
    global X_SON, Y_SON
    X_SON = Y_SON = None
    if not dis_olcu:
        return
    xs, ys = float(dis_olcu["x"]) - T_DIS, float(dis_olcu["y"]) - T_DIS / 2.0
    for ad_, son, bas, n in (("x", xs, T_DIS, nx), ("y", ys, T_DIS / 2.0, ny)):
        if not (bas + MOD * (n - 0.5) < son - 1e-9 and son <= bas + MOD * n + 1e-9):
            raise IsEmriHatasi(f"Dış ölçü ile grid uyuşmuyor ({ad_}): son aks {son} cm, grid {n} pano; son yarım pano 0–62,75 cm aralığında olmalı")
    X_SON, Y_SON = xs, ys


def _mm(cm: float) -> str:
    return f"{cm * 10:g}"


def katman(ad: str) -> str:
    """Kalınlık taşıyan katman adını geçerli kalınlığa çevirir (10 / 6 cm'de ad değişmez)."""
    return {"DIS_DUVAR_100": f"DIS_DUVAR_{_mm(T_DIS)}", "IC_DUVAR_60": f"IC_DUVAR_{_mm(T_IC)}",
            "KOSE_PROFIL_100": f"KOSE_PROFIL_{_mm(T_DIS)}", "KOSE_PROFIL_60": f"KOSE_PROFIL_{_mm(T_IC)}",
            "IC_UCLU_H_60": f"IC_UCLU_H_{_mm(T_IC)}"}.get(ad, ad)


def X(i: float) -> float:
    """Düşey aks: dış duvar iç yüzünden başlar (kısa kenar yönü, köşe 10 cm)."""
    v = T_DIS + MOD * i
    return v if X_SON is None else min(v, X_SON)


def Y(j: float) -> float:
    """Yatay aks: ön duvar orta eksenidir (uzun kenar yönü, köşe 5 cm)."""
    v = T_DIS / 2.0 + MOD * j
    return v if Y_SON is None else min(v, Y_SON)


@dataclass
class Mahal:
    ad: str
    tur: str
    rects: list
    acik: bool = False
    cells: set = field(default_factory=set)
    poly: Optional[Polygon] = None
    alan_m2: float = 0.0


@dataclass
class Acilim:
    tur: str                         # pencere | ic_kapi | dis_kapi | gecis
    olcu: str
    genislik: float
    yukseklik: Optional[float]
    mahal: Optional[str] = None
    arasi: Optional[tuple] = None
    mentese: Optional[str] = None
    disari_normal: Optional[str] = None
    icine_normal: Optional[str] = None
    varyant: Optional[str] = None
    alan_kime: Optional[str] = None  # geçiş boşluğunun alanı hangi mahale yazılır


@dataclass
class Pano:
    duvar: "Duvar"
    a0: float
    a1: float
    acilim: Optional[Acilim] = None

    @property
    def boy(self) -> float:
        return round(self.a1 - self.a0, 6)

    def rect(self) -> tuple:
        d = self.duvar
        if d.yon == "x":
            return (self.a0, d.c - d.h, self.a1, d.c + d.h)
        return (d.c - d.h, self.a0, d.c + d.h, self.a1)

    def rects(self) -> list:
        if not self.acilim:
            return [self.rect()]
        w = self.acilim.genislik
        s = (self.boy - w) / 2.0
        d = self.duvar
        if d.yon == "x":
            return [(self.a0, d.c - d.h, self.a0 + s, d.c + d.h), (self.a1 - s, d.c - d.h, self.a1, d.c + d.h)]
        return [(d.c - d.h, self.a0, d.c + d.h, self.a0 + s), (d.c - d.h, self.a1 - s, d.c + d.h, self.a1)]

    def gap(self) -> Optional[tuple]:
        if not self.acilim:
            return None
        w = self.acilim.genislik
        s = (self.boy - w) / 2.0
        d = self.duvar
        if d.yon == "x":
            return (self.a0 + s, d.c - d.h, self.a1 - s, d.c + d.h)
        return (d.c - d.h, self.a0 + s, d.c + d.h, self.a1 - s)


@dataclass
class Duvar:
    id: int
    yon: str                         # 'x' yatay duvar, 'y' düşey duvar
    hat: int                         # aks indeksi (yarım pano birimi)
    c: float                         # orta eksen (cm)
    h: float                         # yarım kalınlık
    tur: str                         # 'dis' | 'ic'
    cevre: bool                      # gövdesi aks dışında duran dış düşey duvar
    govde_yonu: int                  # +1 gövde aksın +x tarafında, -1 -x, 0 eksende
    n0: int
    n1: int
    edges: list = field(default_factory=list)
    p0: float = 0.0
    p1: float = 0.0
    panolar: list = field(default_factory=list)
    uc_notu: dict = field(default_factory=dict)

    @property
    def a0(self) -> float:
        return X(self.n0 / 2) if self.yon == "x" else Y(self.n0 / 2)

    @property
    def a1(self) -> float:
        return X(self.n1 / 2) if self.yon == "x" else Y(self.n1 / 2)


@dataclass
class Kose:
    rect: tuple
    tur: str                         # 'dis' | 'ic'


@dataclass
class HBaglanti:
    x: float
    y: float
    rot: float


@dataclass
class Plan:
    nx: float
    ny: float
    W: float
    H: float
    mahaller: dict
    duvarlar: list
    koseler: list
    h_baglantilar: list
    dikmeler: list                   # veranda dikmeleri: (x0,y0,x1,y1)
    acik_kenarlar: list
    acik_sinir_cizgileri: list
    uyarilar: list
    is_emri: dict

    @property
    def panolar(self) -> list:
        return [p for d in self.duvarlar for p in d.panolar]

    def footprint(self):
        rects = [box(*r) for p in self.panolar for r in p.rects()] + [box(*k.rect) for k in self.koseler]
        gaps = [box(*p.gap()) for p in self.panolar if p.acilim]
        return unary_union(rects + gaps)


def _cells_of_rect(rect):
    x0, y0, x1, y1 = rect
    for v in (x0, y0, x1, y1):
        if abs(v * 2 - round(v * 2)) > 1e-9:
            raise IsEmriHatasi(f"Mahal koordinatı yarım pano adımında değil: {rect}")
    if x1 <= x0 or y1 <= y0:
        raise IsEmriHatasi(f"Geçersiz mahal dikdörtgeni: {rect}")
    return {(u, v) for u in range(int(round(x0 * 2)), int(round(x1 * 2))) for v in range(int(round(y0 * 2)), int(round(y1 * 2)))}


def kur(is_emri: dict) -> Plan:
    yapi = is_emri["yapi"]
    _k = yapi.get("duvar_kalinligi_cm") or {}
    kalinlik_ayarla(float(_k.get("dis", 10.0)), float(_k.get("ic", 6.0)))
    if yapi.get("sistem", "prefabrik") != "prefabrik":
        raise IsEmriHatasi("v1 yalnız prefabrik sistemi destekler")
    if int(yapi.get("kat_sayisi", 1)) != 1:
        raise IsEmriHatasi("v1 yalnız tek kat destekler")
    if yapi.get("kisa_kenar", "x") != "x":
        raise IsEmriHatasi("v1'de kısa kenar (köşe 10 cm) x yönünde olmalı")
    if yapi.get("ozel_pano") and any(abs(float(v)) > 1e-9 for v in yapi["ozel_pano"].values()):
        raise IsEmriHatasi("v1 özel pano (ruhsat ölçüsü) desteklemiyor")
    nx, ny = float(yapi["grid"]["x_pano"]), float(yapi["grid"]["y_pano"])
    nx2, ny2 = int(round(nx * 2)), int(round(ny * 2))
    if abs(nx2 - nx * 2) > 1e-9 or abs(ny2 - ny * 2) > 1e-9 or nx < 2 or ny < 2:
        raise IsEmriHatasi("Grid yarım pano adımında ve en az 2×2 olmalı")
    olcu_ayarla(yapi.get("dis_olcu_cm"), nx, ny)
    W, H = (MOD * nx + 2.0 * T_DIS, MOD * ny + T_DIS) if X_SON is None else (X_SON + T_DIS, Y_SON + T_DIS / 2.0)
    dis_v_konum = yapi.get("dis_dusey_duvar", "aks_disinda")   # 'aks_disinda' (v1.4.3 son örnek) | 'eksende' (eski 6×8)
    uyarilar = []

    # ---------------- mahaller
    mahaller: dict[str, Mahal] = {}
    cell_owner: dict[tuple, str] = {}
    for m in is_emri["mahaller"]:
        ad = m["ad"]
        if ad in mahaller:
            raise IsEmriHatasi(f"Mahal adı tekrar ediyor: {ad}")
        mh = Mahal(ad=ad, tur=m["tur"], rects=[list(map(float, r)) for r in m["konum_pano"]], acik=(m["tur"] in ACIK_MAHAL_TURLERI))
        for rect in mh.rects:
            for cell in _cells_of_rect(rect):
                u, v = cell
                if not (0 <= u < nx2 and 0 <= v < ny2):
                    raise IsEmriHatasi(f"{ad} grid dışına taşıyor: {rect}")
                if cell in cell_owner:
                    raise IsEmriHatasi(f"{ad} ile {cell_owner[cell]} çakışıyor (hücre {u/2},{v/2})")
                cell_owner[cell] = ad
                mh.cells.add(cell)
        mahaller[ad] = mh
    eksik = [(u / 2, v / 2) for u in range(nx2) for v in range(ny2) if (u, v) not in cell_owner]
    if eksik:
        raise IsEmriHatasi(f"Grid tamamen mahallere bölünmemiş; boş hücreler: {eksik[:8]}")

    acik_ciftler, strip_sahibi = set(), {}
    for s in is_emri.get("acik_sinirlar", []):
        a, b = (s["arasi"] if isinstance(s, dict) else s)
        strip_sahibi[frozenset((a, b))] = (s.get("serit", a) if isinstance(s, dict) else a)
        acik_ciftler.add(frozenset((a, b)))
        for n in (a, b):
            if n not in mahaller:
                raise IsEmriHatasi(f"Açık sınırda bilinmeyen mahal: {n}")

    def owner(u, v):
        return cell_owner[(u, v)] if (0 <= u < nx2 and 0 <= v < ny2) else OUT

    def is_out(name):
        return name == OUT or mahaller[name].acik

    def sinif(a, b):
        if a == b:
            return None
        if a == OUT or b == OUT:
            m = mahaller[b] if a == OUT else mahaller[a]
            return "acik_profil" if m.acik else "dis"
        ma, mb = mahaller[a], mahaller[b]
        if ma.acik and mb.acik:
            return "acik_sinir"
        if ma.acik or mb.acik:
            return "dis"
        if frozenset((a, b)) in acik_ciftler:
            return "acik_sinir"
        return "ic"

    edges = []
    for u in range(0, nx2 + 1):
        for v in range(0, ny2):
            a, b = owner(u - 1, v), owner(u, v); s = sinif(a, b)
            if s: edges.append(("y", u, v, a, b, s))
    for v in range(0, ny2 + 1):
        for u in range(0, nx2):
            a, b = owner(u, v - 1), owner(u, v); s = sinif(a, b)
            if s: edges.append(("x", v, u, a, b, s))

    # ---------------- duvar koşuları
    duvarlar: list[Duvar] = []
    acik_kenarlar, acik_sinir_edges = [], []
    by_line: dict = {}
    for e in edges:
        yon, hat, k, a, b, s = e
        if s == "acik_profil":
            if yon == "y":
                x = 0.0 if hat == 0 else (W if hat == nx2 else X(hat / 2))
                acik_kenarlar.append((x, Y(k / 2), x, Y((k + 1) / 2), yon, hat, a, b))
            else:
                y = 0.0 if hat == 0 else (H if hat == ny2 else Y(hat / 2))
                acik_kenarlar.append((X(k / 2), y, X((k + 1) / 2), y, yon, hat, a, b))
            continue
        if s == "acik_sinir":
            acik_sinir_edges.append(e); continue
        by_line.setdefault((yon, hat, s), []).append((k, a, b))
    wid = 0
    for (yon, hat, s), lst in sorted(by_line.items()):
        lst.sort()
        runs, cur = [], [lst[0]]
        for item in lst[1:]:
            if item[0] == cur[-1][0] + 1: cur.append(item)
            else: runs.append(cur); cur = [item]
        runs.append(cur)
        for run in runs:
            h = T_DIS / 2 if s == "dis" else T_IC / 2
            cevre, govde = False, 0
            if yon == "y":
                ax = X(hat / 2)
                if s == "dis":
                    # dış taraf hangi yanda? (neg=-x tarafı a, pos=+x tarafı b)
                    neg_out = all(is_out(a) for k, a, b in run); pos_out = all(is_out(b) for k, a, b in run)
                    if hat == 0: neg_out, pos_out = True, False
                    if hat == nx2: neg_out, pos_out = False, True
                    if dis_v_konum == "aks_disinda" or hat in (0, nx2):
                        if neg_out and not pos_out: c, cevre, govde = ax - h, True, -1
                        elif pos_out and not neg_out: c, cevre, govde = ax + h, True, +1
                        else:
                            c = ax; uyarilar.append(f"Düşey dış duvar {hat/2}: dış taraf belirsiz, eksene ortalandı")
                    else:
                        c = ax
                else:
                    c = ax
            else:
                c = Y(hat / 2)
            d = Duvar(id=wid, yon=yon, hat=hat, c=c, h=h, tur=s, cevre=cevre, govde_yonu=govde, n0=run[0][0], n1=run[-1][0] + 1,
                      edges=[(k, a, b) for k, a, b in run])
            d.p0, d.p1 = d.a0, d.a1
            duvarlar.append(d); wid += 1

    # ---------------- birleşimler (nokta tabanlı)
    def pt_of_end(d, uc):
        n = d.n0 if uc == 0 else d.n1
        return (n, d.hat) if d.yon == "x" else (d.hat, n)

    ends_at, through_at = {}, {}
    for d in duvarlar:
        for uc in (0, 1):
            ends_at.setdefault(pt_of_end(d, uc), []).append((d, uc))
        for n in range(d.n0 + 1, d.n1):
            P = (n, d.hat) if d.yon == "x" else (d.hat, n)
            through_at.setdefault(P, []).append(d)

    def stop_at_face(d, uc, o):
        if uc == 0: d.p0 = o.c + o.h
        else:       d.p1 = o.c - o.h

    koseler, h_bag = [], []

    def L_kose(Hw, H_uc, Vw, V_uc, tur):
        H_side = +1 if H_uc == 0 else -1          # H duvarı köşenin hangi tarafında uzanıyor
        v_extender = (Vw.govde_yonu != 0 and H_side != Vw.govde_yonu)
        if v_extender:
            # V uzatan: V, H'nin orta eksenine kadar; H, V'nin yüzünde (aks) biter; köşe parçası V şeridinde
            if V_uc == 0: Vw.p0 = Hw.c
            else:         Vw.p1 = Hw.c
            if H_uc == 0: Hw.p0 = Vw.c + Vw.h
            else:         Hw.p1 = Vw.c - Vw.h
            ys = (Hw.c - Hw.h, Hw.c) if V_uc == 0 else (Hw.c, Hw.c + Hw.h)
            koseler.append(Kose((Vw.c - Vw.h, ys[0], Vw.c + Vw.h, ys[1]), tur))
        else:
            # H uzatan: H, V'nin orta eksenine kadar; V, H'nin yüzünde biter; köşe parçası H şeridinde
            if H_uc == 0: Hw.p0 = Vw.c
            else:         Hw.p1 = Vw.c
            if V_uc == 0: Vw.p0 = Hw.c + Hw.h
            else:         Vw.p1 = Hw.c - Hw.h
            xs = (Vw.c - Vw.h, Vw.c) if H_uc == 0 else (Vw.c, Vw.c + Vw.h)
            koseler.append(Kose((xs[0], Hw.c - Hw.h, xs[1], Hw.c + Hw.h), tur))
        Hw.uc_notu[H_uc] = f"L→{Vw.id}"; Vw.uc_notu[V_uc] = f"L→{Hw.id}"

    Hs = lambda lst: [(d, uc) for d, uc in lst if d.yon == "x"]
    Vs = lambda lst: [(d, uc) for d, uc in lst if d.yon == "y"]
    for P in set(ends_at) | set(through_at):
        ends = ends_at.get(P, []); thr = through_at.get(P, [])
        if not ends:
            continue
        if thr:
            if len(thr) > 1:
                uyarilar.append(f"Aks noktası {P}: iki geçen duvar (+ birleşim); yüz kuralı uygulandı")
            for d, uc in ends:
                o = next((t for t in thr if t.yon != d.yon), None)
                if o is None:
                    uyarilar.append(f"Aks noktası {P}: duvar {d.id} aynı hatta geçen duvarla çakışıyor"); continue
                stop_at_face(d, uc, o); d.uc_notu[uc] = f"T→{o.id}"
            t = thr[0]
            branches = [(d, uc) for d, uc in ends if d.tur == "ic" and d.yon != t.yon]
            if t.tur == "ic" and len(branches) == 1 and len(thr) == 1:
                d, uc = branches[0]
                if d.yon == "x": h_bag.append(HBaglanti(d.a0 if uc == 0 else d.a1, d.c, 0.0 if uc == 0 else 180.0))
                else:            h_bag.append(HBaglanti(d.c, d.a0 if uc == 0 else d.a1, 90.0 if uc == 0 else 270.0))
            continue
        ext = [(d, uc) for d, uc in ends if d.tur == "dis"]
        ic = [(d, uc) for d, uc in ends if d.tur == "ic"]
        if Hs(ext) and Vs(ext):
            (Hw, H_uc), (Vw, V_uc) = Hs(ext)[0], Vs(ext)[0]
            L_kose(Hw, H_uc, Vw, V_uc, "dis")
            if len(ext) > 2:
                uyarilar.append(f"Aks noktası {P}: ikiden fazla dış duvar ucu; ilk çift köşe yapıldı")
            for d, uc in ic:
                o = Vw if d.yon == "x" else Hw
                stop_at_face(d, uc, o); d.uc_notu[uc] = f"T→{o.id} (dış köşe)"
        elif Hs(ic) and Vs(ic) and not ext:
            (Hw, H_uc), (Vw, V_uc) = Hs(ic)[0], Vs(ic)[0]
            L_kose(Hw, H_uc, Vw, V_uc, "ic")
            if len(ic) > 2:
                uyarilar.append(f"Aks noktası {P}: iç duvar + birleşimi; kural tanımsız")
        elif ext and ic and len(ends) == 2 and ((Hs(ext) and Vs(ic)) or (Vs(ext) and Hs(ic))):
            (Hw, H_uc) = (Hs(ext) or Hs(ic))[0]; (Vw, V_uc) = (Vs(ext) or Vs(ic))[0]
            L_kose(Hw, H_uc, Vw, V_uc, "dis")
            uyarilar.append(f"Aks noktası {P}: dış-iç L köşe; v1.4.3 100×50 kuralı el ile kontrol edilmeli")
        elif len(ends) == 1:
            ends[0][0].uc_notu[ends[0][1]] = "serbest"
        else:
            uyarilar.append(f"Aks noktası {P}: çözümsüz birleşim {[(d.id, uc) for d, uc in ends]}")

    # ---------------- pano ayrıştırma
    for d in duvarlar:
        splits = []
        if d.tur == "ic":
            for (u, v), lst in ends_at.items():
                if d.yon == "x" and v == d.hat and d.n0 < u < d.n1 and any(o.yon != d.yon for o, _ in lst):
                    splits.append(X(u / 2))
                if d.yon == "y" and u == d.hat and d.n0 < v < d.n1 and any(o.yon != d.yon for o, _ in lst):
                    splits.append(Y(v / 2))
        marks = sorted(set([d.a0, d.a1] + splits))
        sinirlar = []
        for s0, s1 in zip(marks, marks[1:]):
            k = math.ceil((s1 - s0) / MOD - 1e-9)
            sinirlar += [s0 + MOD * i for i in range(1, k)]
        sinirlar += splits
        pts = [d.p0] + sorted(s for s in set(sinirlar) if d.p0 + 1e-9 < s < d.p1 - 1e-9) + [d.p1]
        d.panolar = [Pano(d, pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        for p in d.panolar:
            if p.boy < 20 - 1e-9:
                uyarilar.append(f"Duvar {d.id}: {p.boy} cm'lik çok kısa pano (özel pano kuralı doğrulanmalı)")
            if p.boy > MOD + 1e-6:
                uyarilar.append(f"Duvar {d.id}: {p.boy} cm'lik uzun özel pano (125,5 üstü) — doğrulanmalı")

    # ---------------- açıklıklar
    NORMAL = {"sol": "-x", "sag": "+x", "on": "-y", "arka": "+y"}
    for ac in is_emri.get("acikliklar", []):
        tur = ac["tur"]
        if tur == "pencere":
            if ac["olcu"] not in PENCERE_OLCULERI:
                raise IsEmriHatasi(f"Katalog dışı pencere ölçüsü: {ac['olcu']}")
            w, hh = PENCERE_OLCULERI[ac["olcu"]]
            mahal = ac["mahal"]
            if mahal not in mahaller:
                raise IsEmriHatasi(f"Pencere için bilinmeyen mahal: {mahal}")
            normal = NORMAL[ac["duvar"]]
            cand = _edges_of_room_side(duvarlar, mahal, normal)
            if not cand:
                raise IsEmriHatasi(f"{mahal} mahalinin {ac['duvar']} tarafında dış duvar yok")
            acl = Acilim("pencere", ac["olcu"], float(w), float(hh), mahal=mahal, disari_normal=normal)
        else:
            if tur not in KAPI_GENISLIK:
                raise IsEmriHatasi(f"Bilinmeyen açıklık türü: {tur}")
            a, b = ac["arasi"]
            for n in (a, b):
                if n not in mahaller and n != OUT:   # verandasız yapıda dış kapı doğrudan dışarı açılır
                    raise IsEmriHatasi(f"Açıklık için bilinmeyen mahal: {n}")
            w = float(ac.get("olcu", KAPI_GENISLIK[tur]))
            cand = _edges_between(duvarlar, a, b)
            if OUT in (a, b):   # dışarı açılan kapı: cephe İş Emri'nde yazılır ("duvar": on | arka | sol | sag)
                if ac.get("duvar") not in NORMAL:
                    raise IsEmriHatasi(f"Dışarı açılan kapıda cephe (duvar) yazılmalı: {ac}")
                cand = _edges_of_room_side(duvarlar, b if a == OUT else a, NORMAL[ac["duvar"]])
            if not cand:
                raise IsEmriHatasi(f"{a}–{b} arasında duvar yok: {ac}")
            acl = Acilim(tur, str(int(w)) if w == int(w) else str(w), w, None, arasi=(a, b), mentese=ac.get("mentese", "sag"),
                         alan_kime=ac.get("alan_kime", a))
        panolar = []
        for d, k0, k1 in cand:
            lo = X(k0 / 2) if d.yon == "x" else Y(k0 / 2)
            hi = X(k1 / 2) if d.yon == "x" else Y(k1 / 2)
            for p in d.panolar:
                mid = (p.a0 + p.a1) / 2
                if mid - acl.genislik / 2 >= lo - 1e-6 and mid + acl.genislik / 2 <= hi + 1e-6 and p not in [q for _, q in panolar]:
                    panolar.append((d, p))
        panolar.sort(key=lambda dp: dp[1].a0)
        if not panolar:
            raise IsEmriHatasi(f"Açıklık için uygun pano yok: {ac}")
        idx = ac.get("pano")
        if idx is None:
            idx = (len(panolar) - 1) // 2
        if not (0 <= idx < len(panolar)):
            raise IsEmriHatasi(f"Açıklık pano indeksi aralık dışı: {ac} (aday {len(panolar)})")
        d, p = panolar[idx]
        if p.acilim:
            raise IsEmriHatasi(f"Aynı panoya iki açıklık: {ac}")
        if acl.genislik > p.boy - 4:
            raise IsEmriHatasi(f"Açıklık panodan geniş: {ac} (pano {p.boy})")
        if tur != "pencere":
            acl.icine_normal = _normal_from_to(d, a, b)
        p.acilim = acl

    # ---------------- veranda dikmeleri (İş Emri'nde cm konum: sol-alt köşe, 10×10)
    dikmeler = [(float(x), float(y), float(x) + 10.0, float(y) + 10.0) for x, y in is_emri.get("dikmeler", [])]

    # ---------------- açık sınırlar ve net alanlar
    acik_sinir_cizgileri = []
    ekle, cikar = {ad: [] for ad in mahaller}, {ad: [] for ad in mahaller}
    runs_by = {}
    for yon, hat, k, a, b, s in acik_sinir_edges:
        runs_by.setdefault((yon, hat, frozenset((a, b))), []).append((k, a, b))
    for (yon, hat, pair), lst in runs_by.items():
        lst.sort(); groups, cur = [], [lst[0]]
        for item in lst[1:]:
            if item[0] == cur[-1][0] + 1: cur.append(item)
            else: groups.append(cur); cur = [item]
        groups.append(cur)
        for run in groups:
            k0, k1 = run[0][0], run[-1][0] + 1
            _, a, b = run[0]
            sahip = strip_sahibi.get(pair, a)
            hs = [d.h for d in duvarlar if d.yon == yon and d.hat == hat and (d.n1 == k0 or d.n0 == k1)]
            if len(set(hs)) > 1:
                uyarilar.append(f"Açık sınır {a}–{b}: iki ucunda farklı kalınlıkta duvar; ilki esas alındı")
            h = hs[0] if hs else T_IC / 2
            for k, _a, _b in run:
                _acik_strip(k, yon, hat, a, b, sahip, h, acik_sinir_cizgileri, ekle, cikar)

    wall_geoms = [box(*p.rect()) for d in duvarlar for p in d.panolar] + [box(*k.rect) for k in koseler]   # dikme izleri alandan düşülmez
    walls = unary_union(wall_geoms)
    gecis_ekle = {}
    for d in duvarlar:
        for p in d.panolar:
            if p.acilim and p.acilim.tur == "gecis":
                gecis_ekle.setdefault(p.acilim.alan_kime, []).append(box(*p.gap()))
    for ad, m in mahaller.items():
        cells = [box(X(u / 2), Y(v / 2), X((u + 1) / 2), Y((v + 1) / 2)) for (u, v) in m.cells]
        poly = unary_union(cells)
        if m.acik:
            acik_hatlar = set()
            for (x0, y0, x1, y1, yon, hat, a, b) in acik_kenarlar:
                if ad not in (a, b):
                    continue
                acik_hatlar.add((yon, hat))
                if yon == "y":
                    cx = X(hat / 2); poly = unary_union([poly, box(min(cx, x0), y0, max(cx, x0), y1)])
                else:
                    cy = Y(hat / 2); poly = unary_union([poly, box(x0, min(cy, y0), x1, max(cy, y0))])
            corners = {(0, 0): box(0, 0, X(0), Y(0)), (nx2 - 1, 0): box(X(nx), 0, W, Y(0)),
                       (0, ny2 - 1): box(0, Y(ny), X(0), H), (nx2 - 1, ny2 - 1): box(X(nx), Y(ny), W, H)}
            for (cu, cv), cb in corners.items():
                if (cu, cv) in m.cells and ("y", 0 if cu == 0 else nx2) in acik_hatlar and ("x", 0 if cv == 0 else ny2) in acik_hatlar:
                    poly = unary_union([poly, cb])
        if ekle[ad]: poly = unary_union([poly] + ekle[ad])
        if cikar[ad]: poly = poly.difference(unary_union(cikar[ad]))
        poly = poly.difference(walls)
        if ad in gecis_ekle:
            poly = unary_union([poly] + gecis_ekle[ad])
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda g: g.area)
            uyarilar.append(f"{ad} net alanı birden çok parçaya bölündü; en büyük parça alındı")
        m.poly = poly
        m.alan_m2 = poly.area / 10000.0

    profil = [(x0, y0, x1, y1) for (x0, y0, x1, y1, *_r) in acik_kenarlar]
    return Plan(nx, ny, W, H, mahaller, duvarlar, koseler, h_bag, dikmeler, profil, acik_sinir_cizgileri, uyarilar, is_emri)


def _acik_strip(k, yon, hat, a, b, sahip, h, cizgiler, ekle, cikar):
    diger = b if sahip == a else a
    if yon == "y":
        x = X(hat / 2); y0, y1 = Y(k / 2), Y((k + 1) / 2)
        xs = x + h if sahip == a else x - h
        cizgiler.append((xs, y0, xs, y1)); strip = box(min(x, xs), y0, max(x, xs), y1)
    else:
        y = Y(hat / 2); x0, x1 = X(k / 2), X((k + 1) / 2)
        ys = y + h if sahip == a else y - h
        cizgiler.append((x0, ys, x1, ys)); strip = box(x0, min(y, ys), x1, max(y, ys))
    ekle[sahip].append(strip); cikar[diger].append(strip)


def _edges_of_room_side(duvarlar, mahal, normal):
    out = []
    for d in duvarlar:
        if d.tur != "dis":
            continue
        ks = []
        for k, a, b in d.edges:
            if d.yon == "y":
                if (normal == "+x" and a == mahal) or (normal == "-x" and b == mahal): ks.append(k)
            else:
                if (normal == "+y" and a == mahal) or (normal == "-y" and b == mahal): ks.append(k)
        if ks:
            out.append((d, min(ks), max(ks) + 1))
    return out


def _edges_between(duvarlar, a, b):
    out = []
    for d in duvarlar:
        ks = [k for k, x, y in d.edges if {x, y} == {a, b}]
        if ks:
            out.append((d, min(ks), max(ks) + 1))
    return out


def _normal_from_to(d, a, b):
    for k, x, y in d.edges:
        if {x, y} == {a, b}:
            if d.yon == "y": return "+x" if x == a else "-x"
            return "+y" if x == a else "-y"
    raise IsEmriHatasi("kapı normali bulunamadı")


def kapi_varyanti(d, ac) -> str:
    """İç kapı panosu kaynak blok varyantı (SOL/SAG × ALT/UST). Kanonik pano çerçevesi: pano +y boyunca, kalınlık +x."""
    n, m = ac.icine_normal, (ac.mentese or "sag")
    if d.yon == "y":
        taraf = "SAG" if n == "+x" else "SOL"
        uc = ("UST" if m == "sol" else "ALT") if n == "+x" else ("ALT" if m == "sol" else "UST")
    else:
        taraf = "SOL" if n == "+y" else "SAG"
        uc = ("ALT" if m == "sol" else "UST") if n == "+y" else ("UST" if m == "sol" else "ALT")
    return f"{taraf}_{uc}"
