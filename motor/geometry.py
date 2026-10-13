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
_AKS = {"x": None, "y": None}   # İE-11: aks tabloları (cm; dizin = yarım pano adımı). None → tekdüze ızgara (formül)
_AKS_ANA = {"x": None, "y": None}   # İE-11: ana akslar (tam pano aksları + ek akslar + uç); çizimde aks çizgileri ve ölçü zinciri
_AKS_EK = {"x": [], "y": []}   # İE-11: ek aks değerleri (etiket için)

PENCERE_OLCULERI = {"120x120": (120, 120), "120x180": (120, 180), "60x40": (60, 40)}
KAPI_GENISLIK = {"ic_kapi": 82.0, "dis_kapi": 97.0, "gecis": 82.0}
# İE-11 (PK-01 montaj paftası, 13.10.2026; yalnız `dizilim.pencere` / `dizilim.kapi` anahtarıyla):
PENCERE_ORTALAMA_ESIGI_CM = MOD / 4.0   # oda ortası ızgara panosunun ortasından en çok ¼ pano kaçıyorsa ızgara kalır (paftada 6 pencerenin 4'ü), yoksa pencereli pano odaya ortalanır
KAPI_YASLAMA_CM = 11.5                  # oda kapısı boşluğu menteşe tarafındaki pano ucundan 11,5 cm içeride (paftada 4 kapı: 11,3 / 11,3 / 11,6 / 11,5)
ACIK_MAHAL_TURLERI = {"veranda", "balkon", "sundurma", "teras"}


class IsEmriHatasi(ValueError):
    pass


YENI_ANAHTARLAR = ("duvar_kalinligi_cm", "dis_olcu_cm", "dizilim", "ek_akslar_cm")   # İE-11 (6 Ekim denemesi + genişletme)


PANO_YUKSEKLIKLERI_CM = (250.0, 280.0, 300.0)   # Lokman 13.10.2026 07:28: %80 / %19 / %1; başka ölçü yok (kurallar/model/duvar_tipleri.json PE-DIS-100.pano)


def geometri_anahtari_var(is_emri: dict) -> bool:
    """İE-11 geometri anahtarlarından biri varsa True (yükseklik hariç). Doğrulamanın dış ölçü / açık kenar kuralı buna bağlıdır:
    yükseklik planın geometrisini ve dolayısıyla hangi geometrinin kabul edileceğini değiştirmez (geometri hakemi 2. tur, önemli 1)."""
    yapi = is_emri.get("yapi", {})
    return any(k in yapi for k in YENI_ANAHTARLAR) or any("konum_cm" in m for m in is_emri.get("mahaller", [])) \
        or any(("konum_cm" in a) or ("hizalama" in a) for a in is_emri.get("acikliklar", []))
    # `acikliklar[].dograma` geometri anahtarı değildir (kod incelemesi D1): yalnız BOM işaretini etkiler, kendi varlığıyla çalışır


def yeni_anahtar_var(is_emri: dict) -> bool:
    """İE-11 anahtarlarından biri varsa True. Yoksa Motor eski İş Emri'nde bayt bayt aynı çıktıyı verir (altın testler).
    250 dışı pano yüksekliği (280 / 300) de yeni anahtar sayılır: eski yol her yüksekliğe 2500 kodunu ve 50 lentoyu veriyordu;
    canlıdaki ve altın İş Emri'lerin hepsi 250 (Lokman 13.10.2026 07:28; İE-11 › Lokman'ın kararları)."""
    yapi = is_emri.get("yapi", {})
    yukseklik_farkli = "duvar_yuksekligi_cm" in yapi and abs(float(yapi["duvar_yuksekligi_cm"]) - 250.0) > 1e-9
    return geometri_anahtari_var(is_emri) or yukseklik_farkli


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
            raise IsEmriHatasi(f"Dış ölçü ile grid uyuşmuyor ({ad_}): son aks {son:g} cm, grid {n:g} pano → son pano {son - bas - MOD * (n - 1):g} cm; "
                               f"kesilmiş son pano 62,75'ten büyük ve 125,5'ten küçük ya da eşit olmalı (tam yarım pano için grid'i yarım adımla yazın: {n - 0.5:g})")
    X_SON, Y_SON = xs, ys


def _mm(cm: float) -> str:
    return f"{cm * 10:g}"


def katman(ad: str) -> str:
    """Kalınlık taşıyan katman adını geçerli kalınlığa çevirir (10 / 6 cm'de ad değişmez)."""
    return {"DIS_DUVAR_100": f"DIS_DUVAR_{_mm(T_DIS)}", "IC_DUVAR_60": f"IC_DUVAR_{_mm(T_IC)}",
            "KOSE_PROFIL_100": f"KOSE_PROFIL_{_mm(T_DIS)}", "KOSE_PROFIL_60": f"KOSE_PROFIL_{_mm(T_IC)}",
            "IC_UCLU_H_60": f"IC_UCLU_H_{_mm(T_IC)}", "DIS_UCLU_H_100": f"DIS_UCLU_H_{_mm(T_DIS)}"}.get(ad, ad)


def X(i: float) -> float:
    """Düşey aks: dış duvar iç yüzünden başlar (kısa kenar yönü, köşe 10 cm). Aks tablosu varsa oradan (İE-11)."""
    if _AKS["x"] is not None:
        return _AKS["x"][int(round(i * 2))]
    v = T_DIS + MOD * i
    return v if X_SON is None else min(v, X_SON)


def Y(j: float) -> float:
    """Yatay aks: ön duvar orta eksenidir (uzun kenar yönü, köşe 5 cm). Aks tablosu varsa oradan (İE-11)."""
    if _AKS["y"] is not None:
        return _AKS["y"][int(round(j * 2))]
    v = T_DIS / 2.0 + MOD * j
    return v if Y_SON is None else min(v, Y_SON)


def aks_tablosu_kur(ek_akslar, nx2: int, ny2: int, zorunlu: bool = False) -> tuple[int, int]:
    """İE-11: `ek_akslar_cm` verilince (ya da zorunluysa) yarım adım aksları + ek akslardan sıralı aks tablosu kurar.
    Dönen (nx2, ny2) tablo uzunluğudur. Tablo yokken Motor eskisi gibi formülle çalışır."""
    global _AKS, _AKS_ANA, _AKS_EK
    _AKS = {"x": None, "y": None}; _AKS_ANA = {"x": None, "y": None}; _AKS_EK = {"x": [], "y": []}
    if not ek_akslar and not zorunlu:
        return nx2, ny2
    ek = ek_akslar or {}
    yeni = {}; ana = {}; ekler = {}
    for yon, n2, f in (("x", nx2, X), ("y", ny2, Y)):
        taban = [f(k / 2) for k in range(n2 + 1)]          # tablo henüz yok: formül (kesim dahil)
        lo, hi = taban[0], taban[-1]
        tab = list(taban)
        for v in ek.get(yon) or []:
            v = float(v)
            if not (lo + 1e-6 < v < hi - 1e-6):
                raise IsEmriHatasi(f"Ek aks ({yon}) yapının içinde değil: {v} cm (aralık {lo:g}–{hi:g})")
            if not any(abs(v - t) < 1e-6 for t in tab):
                tab.append(v)
        yeni[yon] = sorted(tab)
        tam = [taban[k] for k in range(0, n2 + 1, 2)] + [taban[-1]]
        ekler[yon] = sorted({float(v) for v in (ek.get(yon) or [])
                             if not any(abs(float(v) - t) < 1e-6 for t in tam)})   # tam ızgara aksıyla çakışan ek aks o aksın adını taşır
        ana[yon] = sorted(set(tam + ekler[yon]))
    _AKS = yeni; _AKS_ANA = ana; _AKS_EK = ekler
    return len(yeni["x"]) - 1, len(yeni["y"]) - 1


def aks_durumu_sifirla() -> None:
    """Aks tablosu ve kesim durumunu temizler. `kur()` başında çağrılır: hatayla düşen bir kurulumdan sonraki çağrı eski tabloyu
    ya da kesimi görmez (`olcu_ayarla` ve `aks_tablosu_kur` kendi değerlerini sonra yeniden kurar)."""
    global _AKS, _AKS_ANA, _AKS_EK, X_SON, Y_SON
    _AKS = {"x": None, "y": None}; _AKS_ANA = {"x": None, "y": None}; _AKS_EK = {"x": [], "y": []}
    X_SON = Y_SON = None


def ana_akslar(yon: str):
    """Tablo modunda ana akslar (tam pano aksları + ek akslar + uç), cm; tablo yoksa None (eski çizim yolu)."""
    return None if _AKS_ANA[yon] is None else list(_AKS_ANA[yon])


def ana_aks_etiketleri(yon: str):
    """Tablo modunda ana aks adları: ızgara aksları sırayla (x: A, B, …; y: 1, 2, …), ek aks önceki ızgara aksının adı + ′
    (örn. PK-01'de 205 → "2′"); böylece ek aks numaralandırmayı kaydırmaz. Tablo yoksa None."""
    vals = ana_akslar(yon)
    if vals is None:
        return None
    out, n = [], 0
    for v in vals:
        if any(abs(v - e) < 1e-6 for e in _AKS_EK[yon]):
            out.append((out[-1] if out else "0") + "′")
        else:
            out.append(chr(ord("A") + n) if yon == "x" else str(n + 1)); n += 1
    return out


def aks_dizini(v: float, yon: str) -> int:
    """cm değerinin aks tablosundaki dizini; aks üstünde değilse hata (sessiz yuvarlama yok, K21)."""
    tab = _AKS[yon]
    for k, t in enumerate(tab):
        if abs(t - float(v)) < 1e-6:
            return k
    raise IsEmriHatasi(f"Sınır aks üstünde değil ({yon} = {v} cm); `yapi.ek_akslar_cm` ile ekleyin. Akslar: {[round(t, 2) for t in tab]}")


def _ayna_aciklik(ac: dict) -> dict:
    """Dizilim arka-sol: İş Emri gerçek cepheleri yazar; Motor y'de aynalı kurar → ön ↔ arka çevrilir.
    Menteşe çevrilmez: kapı varyantı (`kapi_varyanti`) çizim anında, `_aynala_y` sonrası gerçek çerçevede, gerçek normalle hesaplanır;
    İş Emri'nin menteşesi de gerçek çerçevededir (geometri hakemi, 13.10.2026: takas menteşeyi ters çiziyordu)."""
    a = dict(ac)
    if a.get("duvar") in ("on", "arka"):
        a["duvar"] = "arka" if a["duvar"] == "on" else "on"
    return a


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
    dograma: Optional[str] = None    # İE-11: None | "alıcıya ait"
    kayma: float = 0.0               # İE-11: boşluk merkezinin pano merkezinden kayması (+a yönünde, cm); 0 → ortada (eski)
    mentese_is_emri: Optional[str] = None   # İE-11: İş Emri'nin yazdığı menteşe (yoksa None); `kapi: mantik` kuralı bununla karşılaştırır
    pano_is_emri: Optional[int] = None      # İE-11: İş Emri'nin yazdığı pano dizini (yoksa None)


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
        sl, sr = s + self.acilim.kayma, s - self.acilim.kayma      # kayma 0 → eski formül bit bit (a1 − s)
        d = self.duvar
        if d.yon == "x":
            return [(self.a0, d.c - d.h, self.a0 + sl, d.c + d.h), (self.a1 - sr, d.c - d.h, self.a1, d.c + d.h)]
        return [(d.c - d.h, self.a0, d.c + d.h, self.a0 + sl), (d.c - d.h, self.a1 - sr, d.c + d.h, self.a1)]

    def gap(self) -> Optional[tuple]:
        if not self.acilim:
            return None
        w = self.acilim.genislik
        s = (self.boy - w) / 2.0
        sl, sr = s + self.acilim.kayma, s - self.acilim.kayma
        d = self.duvar
        if d.yon == "x":
            return (self.a0 + sl, d.c - d.h, self.a1 - sr, d.c + d.h)
        return (d.c - d.h, self.a0 + sl, d.c + d.h, self.a1 - sr)


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
    tur: str = "ic"                  # İE-11: "ic" (60) | "dis" (dış duvardaki T; 100×60)


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
    """İş Emri → Plan. Hatayla düşerse modül durumu (aks tablosu, kesim, kalınlık) varsayılana döner: `kur()` dışından
    `X()/Y()/T_DIS` okuyan kod (`cikarici`) yarım kalmış kurulumun değerlerini görmez."""
    try:
        return _kur(is_emri)
    except BaseException:
        aks_durumu_sifirla(); kalinlik_ayarla(10.0, 6.0)
        raise


def _kur(is_emri: dict) -> Plan:
    aks_durumu_sifirla()                                   # önceki (hatalı bitmiş) kurulumun tablosu ve kesimi sızmasın
    yapi = is_emri["yapi"]
    _k = yapi.get("duvar_kalinligi_cm") or {}
    kalinlik_ayarla(float(_k.get("dis", 10.0)), float(_k.get("ic", 6.0)))
    if yapi.get("sistem", "prefabrik") != "prefabrik":
        raise IsEmriHatasi("v1 yalnız prefabrik sistemi destekler")
    _hy = float(yapi.get("duvar_yuksekligi_cm", 250))
    if not any(abs(_hy - h) < 1e-9 for h in PANO_YUKSEKLIKLERI_CM):   # K21: sessizce 2500 koduna düşmez
        raise IsEmriHatasi(f"Prefabrik pano yüksekliği {_hy:g} cm tanımlı değil; yalnız 250 / 280 / 300 cm (Lokman 13.10.2026)")
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
    # İE-11: dizilim başlangıcı ve aks tablosu
    dizilim = yapi.get("dizilim") or {}
    baslangic = dizilim.get("baslangic", "on-sol")
    if baslangic not in ("on-sol", "arka-sol"):
        raise IsEmriHatasi(f"dizilim.baslangic bilinmiyor: {baslangic} (on-sol | arka-sol)")
    ayna_y = baslangic == "arka-sol"
    hiza = dizilim.get("hiza", "kosu")                     # İE-11: "kosu" (koşu başından 125,5; eski) | "izgara" (ızgara akslarına hizalı)
    if hiza not in ("kosu", "izgara"):
        raise IsEmriHatasi(f"dizilim.hiza bilinmiyor: {hiza} (kosu | izgara)")
    dis_t_bolme = bool(dizilim.get("dis_duvar_t_bolme", False))   # İE-11: dış duvar iç T'de bölünür, oraya dış üçlü H
    konum_cm_var = any("konum_cm" in m for m in is_emri["mahaller"])
    nx2, ny2 = aks_tablosu_kur(yapi.get("ek_akslar_cm"), nx2, ny2, zorunlu=ayna_y or konum_cm_var)
    tablo = _AKS["x"] is not None
    grid_nx, grid_ny = nx, ny                                 # İş Emri ızgarası (Plan.nx/ny, pafta yazısı, bayi görseli): ek akslarla değişmez
    if tablo:
        nx, ny = nx2 / 2.0, ny2 / 2.0                         # son aks dizini (tablo); hücre sayısı nx2 × ny2
        W, H = X(nx) + T_DIS, Y(ny) + T_DIS / 2.0
    else:
        W, H = (MOD * nx + 2.0 * T_DIS, MOD * ny + T_DIS) if X_SON is None else (X_SON + T_DIS, Y_SON + T_DIS / 2.0)
    dis_v_konum = yapi.get("dis_dusey_duvar", "aks_disinda")   # 'aks_disinda' (v1.4.3 son örnek) | 'eksende' (eski 6×8)
    if dis_v_konum not in ("aks_disinda", "eksende", "cevre_aks_disinda"):   # İE-11: 'cevre_aks_disinda' → yalnız çevre duvarı aks dışında,
        raise IsEmriHatasi(f"dis_dusey_duvar bilinmiyor: {dis_v_konum} (aks_disinda | eksende | cevre_aks_disinda)")   # veranda duvarı aksa ortalı (PK-01)
    pencere_kurali = dizilim.get("pencere", "pano")         # İE-11: "pano" (İş Emri dizini / orta aday; eski) | "oda_ortasi"
    kapi_kurali = dizilim.get("kapi", "is_emri")            # İE-11: "is_emri" (menteşe İş Emri'nden, kapı panoda ortada; eski) | "mantik"
    if pencere_kurali not in ("pano", "oda_ortasi"):
        raise IsEmriHatasi(f"dizilim.pencere bilinmiyor: {pencere_kurali} (pano | oda_ortasi)")
    if kapi_kurali not in ("is_emri", "mantik"):
        raise IsEmriHatasi(f"dizilim.kapi bilinmiyor: {kapi_kurali} (is_emri | mantik)")
    kose_kurali = dizilim.get("kose", "eski")               # İE-11: "eski" (gövdesi aks dışındaki V uzar) | "oda" (kollar arasında kapalı oda → V uzar)
    if kose_kurali not in ("eski", "oda"):
        raise IsEmriHatasi(f"dizilim.kose bilinmiyor: {kose_kurali} (eski | oda)")
    uyarilar = []

    # ---------------- mahaller
    mahaller: dict[str, Mahal] = {}
    cell_owner: dict[tuple, str] = {}
    for m in is_emri["mahaller"]:
        ad = m["ad"]
        if ad in mahaller:
            raise IsEmriHatasi(f"Mahal adı tekrar ediyor: {ad}")
        if "konum_cm" in m:                                   # İE-11: cm sınırlar (akslar; dış yüzlerden)
            rects = [[aks_dizini(r[0], "x") / 2, aks_dizini(r[1], "y") / 2, aks_dizini(r[2], "x") / 2, aks_dizini(r[3], "y") / 2] for r in m["konum_cm"]]
        elif tablo:                                           # pano birimi → cm → tablo dizini
            rects = []
            for r in m["konum_pano"]:
                cm = [T_DIS + MOD * float(r[0]), T_DIS / 2.0 + MOD * float(r[1]), T_DIS + MOD * float(r[2]), T_DIS / 2.0 + MOD * float(r[3])]
                # ölçüye kesimde yalnız ızgaranın SON aksı (r = nx / ny) kesilmiş yere eşlenir; grid dışı değer kırpılmaz, aks_dizini hata verir (K21)
                for i, (son, n) in ((0, (X_SON, grid_nx)), (2, (X_SON, grid_nx)), (1, (Y_SON, grid_ny)), (3, (Y_SON, grid_ny))):
                    if son is not None and abs(float(r[i]) - n) < 1e-9: cm[i] = son
                rects.append([aks_dizini(cm[0], "x") / 2, aks_dizini(cm[1], "y") / 2, aks_dizini(cm[2], "x") / 2, aks_dizini(cm[3], "y") / 2])
        else:
            rects = [list(map(float, r)) for r in m["konum_pano"]]
        mh = Mahal(ad=ad, tur=m["tur"], rects=rects, acik=(m["tur"] in ACIK_MAHAL_TURLERI))
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
        if kose_kurali == "oda":                  # İE-11 (PK-01 paftası): kollar arasında kapalı oda varsa V uzar, köşe parçası odanın dışında
            V_side = +1 if V_uc == 0 else -1
            u, v = Vw.hat, Hw.hat
            v_extender = not is_out(owner(u if H_side > 0 else u - 1, v if V_side > 0 else v - 1))
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
            if (t.tur == "ic" or dis_t_bolme) and len(branches) == 1 and len(thr) == 1:
                d, uc = branches[0]
                # simge geçen duvarın merkezinde (t.c): eksendeki duvarda aks, gövdesi aks dışındaki yan dış duvarda gövde ortası (hakem 2. tur 6)
                if d.yon == "x": h_bag.append(HBaglanti(t.c, d.c, 0.0 if uc == 0 else 180.0, t.tur))
                else:            h_bag.append(HBaglanti(d.c, t.c, 90.0 if uc == 0 else 270.0, t.tur))
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

    # ---------------- açıklık listesi (aynalı çerçevede) ve oda ortası pencere hedefleri (İE-11; bölmeden önce gerekir)
    NORMAL = {"sol": "-x", "sag": "+x", "on": "-y", "arka": "+y"}
    acikliklar = [(_ayna_aciklik(a) if ayna_y else a) for a in is_emri.get("acikliklar", [])]
    pencere_hedef = {}          # açıklık sırası → [duvar id, oda net merkezi, aks aralığı lo, hi, seçilen pano başı]
    if pencere_kurali == "oda_ortasi":
        for i, ac in enumerate(acikliklar):
            if ac.get("tur") != "pencere" or "pano" in ac or ac.get("olcu") not in PENCERE_OLCULERI or ac.get("mahal") not in mahaller \
                    or ac.get("duvar") not in NORMAL:
                continue                                        # hatalı girdi aşağıdaki döngüde açık hata verir; "pano" yazılmışsa o geçerli
            cand = _edges_of_room_side(duvarlar, ac["mahal"], NORMAL[ac["duvar"]])
            if not cand:
                continue
            d, k0, k1 = max(cand, key=lambda c: c[2] - c[1])
            lo, hi = (X(k0 / 2), X(k1 / 2)) if d.yon == "x" else (Y(k0 / 2), Y(k1 / 2))
            lo, hi = min(lo, hi), max(lo, hi)
            nlo, nhi = _oda_net_araligi(duvarlar, d, lo, hi)
            pencere_hedef[i] = [d.id, (nlo + nhi) / 2.0, lo, hi, None]

    # ---------------- pano ayrıştırma
    for d in duvarlar:
        splits = []
        if d.tur == "ic" or dis_t_bolme:
            for (u, v), lst in ends_at.items():
                if d.yon == "x" and v == d.hat and d.n0 < u < d.n1 and any(o.yon != d.yon for o, _ in lst):
                    splits.append(X(u / 2))
                if d.yon == "y" and u == d.hat and d.n0 < v < d.n1 and any(o.yon != d.yon for o, _ in lst):
                    splits.append(Y(v / 2))
        marks = sorted(set([d.a0, d.a1] + splits))
        sinirlar = []
        for s0, s1 in zip(marks, marks[1:]):
            if hiza == "izgara":                                  # İE-11 (PK-01 paftası): segment başı yarım ızgaradaysa koşu başından
                bas = T_DIS if d.yon == "x" else T_DIS / 2.0       # 125,5; değilse önce bir sonraki tam aksa kadar parça, sonra 125,5
                yarim = (s0 - bas) / (MOD / 2.0)
                if abs(yarim - round(yarim)) < 1e-6:
                    k = math.ceil((s1 - s0) / MOD - 1e-9)
                    sinirlar += [s0 + MOD * i for i in range(1, k)]
                else:
                    v = bas + MOD * (math.floor((s0 - bas) / MOD + 1e-9) + 1)
                    while v < s1 - 1e-9:
                        sinirlar.append(v); v += MOD
                continue
            k = math.ceil((s1 - s0) / MOD - 1e-9)
            sinirlar += [s0 + MOD * i for i in range(1, k)]
        sinirlar += splits
        pts = [d.p0] + sorted(s for s in set(sinirlar) if d.p0 + 1e-9 < s < d.p1 - 1e-9) + [d.p1]
        for i, hedef in pencere_hedef.items():                # İE-11 `dizilim.pencere: oda_ortasi`
            did, mrk, lo, hi, _ = hedef
            if did != d.id:
                continue
            w = float(PENCERE_OLCULERI[acikliklar[i]["olcu"]][0])
            lo_p, hi_p = max(lo, d.p0), min(hi, d.p1)
            parca = next(((a, b) for a, b in zip(pts, pts[1:]) if a - 1e-9 <= mrk <= b + 1e-9 and a >= lo_p - 1e-6 and b <= hi_p + 1e-6), None)
            if parca and abs((parca[0] + parca[1]) / 2.0 - mrk) <= PENCERE_ORTALAMA_ESIGI_CM + 1e-6 and parca[1] - parca[0] >= w + 4 - 1e-9:
                hedef[4] = parca[0]; continue                  # ızgara panosu oda ortasına yeterince yakın: ek kesim yok
            q0, q1 = mrk - MOD / 2.0, mrk + MOD / 2.0
            if q0 < lo_p - 1e-6 or q1 > hi_p + 1e-6:
                uyarilar.append(f"Pencere {acikliklar[i].get('mahal')} {acikliklar[i].get('olcu')}: oda duvarı 125,5'lik pencereli panoya dar; ızgara panosunda kaldı")
                continue
            pts = [pts[0]] + sorted(set([q for q in pts[1:-1] if not (q0 - 1e-9 < q < q1 + 1e-9)] + [q for q in (q0, q1) if pts[0] + 1e-9 < q < pts[-1] - 1e-9])) + [pts[-1]]
            hedef[4] = q0
        d.panolar = [Pano(d, pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        for p in d.panolar:
            if p.boy < 20 - 1e-9:
                uyarilar.append(f"Duvar {d.id}: {p.boy} cm'lik çok kısa pano (özel pano kuralı doğrulanmalı)")
            if p.boy > MOD + 1e-6:
                uyarilar.append(f"Duvar {d.id}: {p.boy} cm'lik uzun özel pano (125,5 üstü) — doğrulanmalı")

    # ---------------- açıklıklar
    for i_ac, ac in enumerate(acikliklar):
        tur = ac["tur"]
        if "konum_cm" in ac or "hizalama" in ac:               # İE-11 madde 4 (cm konumlu / odada ortalı açıklık) PR-2'ye ertelendi; sessizce yutulmaz (K21)
            raise IsEmriHatasi(f"Açıklıkta konum_cm / hizalama henüz desteklenmiyor (İE-11 PR-2); pano dizini kullanın: {ac}")
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
                         alan_kime=ac.get("alan_kime", a), mentese_is_emri=ac.get("mentese"))
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
        acl.pano_is_emri = idx
        hedef = pencere_hedef.get(i_ac)
        if idx is None and hedef is not None and hedef[4] is not None:     # İE-11 oda ortası pencere: bölmede seçilen pano
            idx = next((j for j, (dd, pp) in enumerate(panolar) if dd.id == hedef[0] and abs(pp.a0 - hedef[4]) < 1e-6), None)
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
        if ac.get("dograma") not in (None, "alıcıya ait"):    # K21: bilinmeyen değer sessizce yutulmaz
            raise IsEmriHatasi(f"Açıklıkta dograma yalnız \"alıcıya ait\" olabilir: {ac}")
        acl.dograma = ac.get("dograma")           # İE-11: "alıcıya ait" → boşluk var, doğrama blok olarak çizilir, BOM satırı işaretli (listeye girmez)
        p.acilim = acl

    # ---------------- veranda dikmeleri (İş Emri'nde cm konum: sol-alt köşe, 10×10)
    dikmeler = [(float(x), float(y), float(x) + 10.0, float(y) + 10.0) for x, y in is_emri.get("dikmeler", [])]
    # arka-solda da aynalanmaz: dikmeler İş Emri'nde gerçek çerçevede (cm) ve yalnız çizimde kullanılır (alandan düşülmez)

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
    plan = Plan(grid_nx, grid_ny, W, H, mahaller, duvarlar, koseler, h_bag, dikmeler, profil, acik_sinir_cizgileri, uyarilar, is_emri)
    if ayna_y:
        _aynala_y(plan, ny2)
    if kapi_kurali == "mantik":
        _kapi_mantigi(plan)
    return plan


def _aynala_y(plan: "Plan", ny2: int) -> None:
    """İE-11, dizilim arka-sol: Motor y'yi arka duvardan saydı; Plan gerçek yöne (ön altta) çevrilir. Pano boyları ve sayıları
    değişmez; yalnız konumlar y → H − y, normaller ±y, H açıları 90 ↔ 270, aks tablosu tersine. `ny2` hücre sayısıdır (aks tablosu
    uzunluğu − 1; ek aks varsa İş Emri ızgarasından çok). Menteşe çevrilmez (varyant gerçek çerçevede hesaplanır)."""
    global _AKS, _AKS_ANA
    from shapely import affinity
    H = plan.H
    def ny_(v):
        return {"+y": "-y", "-y": "+y"}.get(v, v)
    for d in plan.duvarlar:
        if d.yon == "x":
            d.c = H - d.c; d.hat = ny2 - d.hat
            d.edges = [(k, b, a) for (k, a, b) in d.edges]
            for p in d.panolar:
                if p.acilim:
                    p.acilim.disari_normal = ny_(p.acilim.disari_normal); p.acilim.icine_normal = ny_(p.acilim.icine_normal)
        else:
            d.p0, d.p1 = H - d.p1, H - d.p0
            d.n0, d.n1 = ny2 - d.n1, ny2 - d.n0
            d.edges = [(ny2 - 1 - k, a, b) for (k, a, b) in d.edges][::-1]
            d.uc_notu = {1 - uc: n for uc, n in d.uc_notu.items()}
            for p in d.panolar:
                p.a0, p.a1 = H - p.a1, H - p.a0
            d.panolar.reverse()
    plan.koseler = [Kose((x0, H - y1, x1, H - y0), k.tur) for k in plan.koseler for (x0, y0, x1, y1) in [k.rect]]
    plan.h_baglantilar = [HBaglanti(h.x, H - h.y, {90.0: 270.0, 270.0: 90.0}.get(h.rot, h.rot), h.tur) for h in plan.h_baglantilar]
    plan.acik_kenarlar = [(x0, H - y0, x1, H - y1) for (x0, y0, x1, y1) in plan.acik_kenarlar]
    plan.acik_sinir_cizgileri = [(x0, H - y0, x1, H - y1) for (x0, y0, x1, y1) in plan.acik_sinir_cizgileri]
    for m in plan.mahaller.values():
        if m.poly is not None and not m.poly.is_empty:
            m.poly = affinity.scale(m.poly, xfact=1.0, yfact=-1.0, origin=(0.0, H / 2.0))
        m.rects = [[x0, ny2 / 2.0 - y1, x1, ny2 / 2.0 - y0] for (x0, y0, x1, y1) in m.rects]
        m.cells = {(u, ny2 - 1 - v) for (u, v) in m.cells}
    if _AKS["y"] is not None:
        _AKS["y"] = [H - v for v in reversed(_AKS["y"])]
    if _AKS_ANA["y"] is not None:
        _AKS_ANA["y"] = [H - v for v in reversed(_AKS_ANA["y"])]
    _AKS_EK["y"] = [H - v for v in reversed(_AKS_EK["y"])]


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


def _oda_net_araligi(duvarlar, d, lo, hi):
    """İE-11: d duvarı boyunca [lo, hi] aks aralığının net hali — uçta d'ye değen dik duvarın gövdesi düşülür (PK-01: mutfak ön duvarı
    10 … 256, salon ön duvarı 389,5 … 590)."""
    for w in duvarlar:
        if w.yon == d.yon:
            continue
        if not (min(w.p0, w.p1) <= d.c + d.h + 1e-6 and max(w.p0, w.p1) >= d.c - d.h - 1e-6):
            continue                                            # w, d'nin hattına değmiyor
        if abs(w.c - lo) <= w.h + 1e-6:
            lo = max(lo, w.c + w.h)
        if abs(w.c - hi) <= w.h + 1e-6:
            hi = min(hi, w.c - w.h)
    return lo, hi


def _dayanak(duvarlar, d, e, isaret) -> bool:
    """İE-11 kapı mantığı: d duvarındaki pano ucunda (e, d boyunca cm) açılma tarafına (isaret ±1, d'ye dik eksende) giden dik bir duvar var mı?
    Kanat açıkken o duvara yaslanır."""
    for w in duvarlar:
        if w.yon == d.yon or abs(w.c - e) > w.h + 1e-6:
            continue
        lo_w, hi_w = min(w.p0, w.p1), max(w.p0, w.p1)
        if isaret > 0 and lo_w <= d.c + d.h + 1e-6 and hi_w > d.c + d.h + 1.0:
            return True
        if isaret < 0 and hi_w >= d.c - d.h - 1e-6 and lo_w < d.c - d.h - 1.0:
            return True
    return False


def _kapi_mantigi(plan: "Plan") -> None:
    """İE-11 `dizilim.kapi: mantik` (Lokman 13.10.2026: "iç oda kapılarının kanatları birbirine doğru açılır"; PK-01 montaj paftası).
    Gerçek çerçevede, aynadan sonra koşar. Her kapı için:
      1. Pano: İş Emri dizin vermediyse aday panolardan, ucunda açılma tarafına dik duvar (dayanak) olan seçilir (kanat duvara yaslanır).
      2. Menteşe ucu: dayanaklı uç; iki uç da dayanaklıysa komşu panoda (aynı hat, kavşağın öte yanı) kapı olan uç — kanatlar birbirine
         doğru açılır, ikisi de bölmeye yaslanır; yine eşitse a0 ucu (sol / ön). Hiç dayanak yoksa İş Emri menteşesi kalır.
      3. Oda kapısı (iç kapı) menteşe ucuna kayar: boşluk o pano ucundan KAPI_YASLAMA_CM içeride. Dış kapı panoda ortada kalır (pafta).
    İş Emri menteşe yazdıysa ve kural farklı diyorsa İş Emri geçerli, uyarı yazılır."""
    duvarlar = plan.duvarlar
    tum = [(d, p) for d in duvarlar for p in d.panolar]
    isaret_of = {"+x": 1, "-x": -1, "+y": 1, "-y": -1}

    def dayanaklar(d, p, n):
        k = isaret_of[n]
        return _dayanak(duvarlar, d, p.a0, k), _dayanak(duvarlar, d, p.a1, k)

    def sigar(p, acl):
        return acl.genislik <= p.boy - 4 + 1e-9

    # 1) pano seçimi (yalnız dizinsiz kapılar)
    for d, p in list(tum):
        acl = p.acilim
        if not acl or acl.tur not in ("ic_kapi", "dis_kapi") or acl.pano_is_emri is not None:
            continue
        a, b = acl.arasi
        cand = _edges_between(duvarlar, a, b) if OUT not in (a, b) else [(d, 0, 0)]
        adaylar = []
        for dd, k0, k1 in cand:
            if OUT in (a, b):
                adaylar = [(d, p)]; break
            lo = X(k0 / 2) if dd.yon == "x" else Y(k0 / 2); hi = X(k1 / 2) if dd.yon == "x" else Y(k1 / 2)
            lo, hi = min(lo, hi), max(lo, hi)
            for pp in dd.panolar:
                mid = (pp.a0 + pp.a1) / 2
                if mid - acl.genislik / 2 >= lo - 1e-6 and mid + acl.genislik / 2 <= hi + 1e-6 and (pp.acilim is None or pp is p) and sigar(pp, acl):
                    adaylar.append((dd, pp))
        dayanakli = [(dd, pp) for dd, pp in adaylar if any(dayanaklar(dd, pp, _normal_from_to(dd, a, b)))]
        if dayanakli and (d, p) not in dayanakli:
            dayanakli.sort(key=lambda dp: (dp[0].id, dp[1].a0))
            dd, pp = dayanakli[(len(dayanakli) - 1) // 2]
            p.acilim = None; acl.icine_normal = _normal_from_to(dd, a, b); pp.acilim = acl

    # 2–3) menteşe ucu ve kayma
    def komsu_kapi(d, p, uc):
        e = p.a0 if uc == 0 else p.a1
        for dd in duvarlar:
            if dd.yon != d.yon or abs(dd.c - d.c) > 1e-6:
                continue
            for q in dd.panolar:
                if q is p or not q.acilim or q.acilim.tur not in ("ic_kapi", "dis_kapi"):
                    continue
                if (uc == 0 and abs(q.a1 - e) < 1e-6) or (uc == 1 and abs(q.a0 - e) < 1e-6):
                    return True
        return False

    for d in duvarlar:
        for p in d.panolar:
            acl = p.acilim
            if not acl or acl.tur not in ("ic_kapi", "dis_kapi"):
                continue
            n = acl.icine_normal
            d0, d1 = dayanaklar(d, p, n)
            if d0 and d1:
                k0, k1 = komsu_kapi(d, p, 0), komsu_kapi(d, p, 1)
                uc = 1 if (k1 and not k0) else 0
            elif d0 or d1:
                uc = 0 if d0 else 1
            else:
                uc = None
            if uc is None:
                continue                                        # dayanak yok: İş Emri menteşesi ve ortalı kapı kalır
            # menteşe adı: açılma yönünde yürürken sol / sağ (`mentese_ucu`, `kapi_varyanti` ile aynı sözleşme)
            acl.mentese = "sol"
            kural = "sol" if mentese_ucu(acl) == uc else "sag"
            if acl.mentese_is_emri is not None and acl.mentese_is_emri != kural:
                plan.uyarilar.append(f"Kapı {'–'.join(acl.arasi)}: İş Emri menteşesi '{acl.mentese_is_emri}', kapı mantığı '{kural}' diyor; İş Emri uygulandı")
                kural = acl.mentese_is_emri
            acl.mentese = kural; acl.varyant = None
            uc = mentese_ucu(acl)
            if acl.tur == "ic_kapi":
                s = (p.boy - acl.genislik) / 2.0
                if s > KAPI_YASLAMA_CM:
                    acl.kayma = (s - KAPI_YASLAMA_CM) if uc == 1 else -(s - KAPI_YASLAMA_CM)


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


def mentese_ucu(ac) -> int:
    """Menteşenin panonun hangi ucunda olduğu: 0 → a0 (−x / ön), 1 → a1 (+x / arka). Sözleşme `kapi_varyanti` ile aynı: menteşe adı,
    açılma yönünde (icine_normal) yürürken sol / sağ."""
    sol_eksen = {"+x": 1, "-x": -1, "+y": -1, "-y": 1}[ac.icine_normal]   # sol vektörün duvar ekseni boyunca işareti
    yon = sol_eksen if (ac.mentese or "sag") == "sol" else -sol_eksen
    return 1 if yon > 0 else 0


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


H_PROFIL_GORUNEN_CM = 5.0   # İE-12 (Lokman 13.10.2026 09:39): pano eki H profili dışarıdan bakınca 5 cm, eke tam ortalı


def pano_ekleri(plan: "Plan") -> list:
    """İE-12: bir duvardaki ardışık iki panonun her eki (Lokman 13.10.2026 09:39: "her panonun arasına H birleştirme profili gelir").
    Ekte üçlü H varsa (iç duvar T'si ya da dış duvar T bölmesi; `plan.h_baglantilar`) `cins` "uclu", yoksa "pano_eki".
    Yalnız okur; Motor'un çizimini ve sayımını değiştirmez. PK-01 paftasıyla: pano eki 19 dış + 10 iç, üçlü 5 dış + 4 iç."""
    cik = []
    for d in plan.duvarlar:
        for a, b in zip(d.panolar, d.panolar[1:]):
            e = a.a1
            x, y = (e, d.c) if d.yon == "x" else (d.c, e)
            uclu = any(abs(h.x - x) <= d.h + 3.5 and abs(h.y - y) <= d.h + 3.5 for h in plan.h_baglantilar)
            cik.append({"duvar": d.tur, "yon": d.yon, "c": d.c, "h": d.h, "e": e, "x": x, "y": y, "cins": "uclu" if uclu else "pano_eki"})
    return cik
