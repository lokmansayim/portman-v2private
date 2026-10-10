#!/usr/bin/env python3
"""Çok düzlemli çatı: düzlemlerden kenarlar (saçak, mahya, kırma, vadi, alın, duvar dibi), yüzey, kalkan, aşık ve kaplama dizilimi.

Yapı Tanımı 0.5'teki `cati.duzlemler` okunur. Her düzlem planda bir çokgendir (görünen kısmı), bir yöne doğru yükselir:
    kot(p) = saçak kotu + eğim × ((p − saçak çizgisi) · yukarı)
Düzlemler modelden gelir (SKP'deki makas üstü yüzeyler); kesişimleri (kırma, vadi) çokgenlerin ortak kenarlarıdır.

Kenar türleri koddan çıkar:
    iki düzlemin ortak kenarı  yatay ve dışbükey → mahya; eğimli ve dışbükey → kırma; içbükey → vadi; aynı düzlem → yok
    tek düzlemin kenarı        yatay ve alçak → saçak; yatay ve yüksek → üst kenar; eğimli → alın (kalkan kenarı)
Bir duvara dayanan kenarlar koddan bilinemez; tanımda `cati.kenar_ozel` ile `duvar_dibi` yazılır.

Kaplama dizilimi, kırma çatı için kurulan yöntemin (`../2026-10-03_yukleme/cati_acilim.py`; Lokman, 4 Ekim 2026 01:42) genellemesidir:
her yüz gerçek boyutuyla açılır, saçağa dik şeritlere bölünür, dışarıdan bakışla sol köşeden başlanır. Dikdörtgen şerit tam boy panel
alır. Çapraz kesilen parçalar eşlenir: aynı açıyla kesilmiş bir alt parça (düz ucu saçakta) ile bir üst parça (düz ucu mahyada) tek
dikdörtgenden çıkar; karşı yüzdeki aynı türden parça da (kırma çatıdaki gibi, çevrilerek) eş olabilir. Dikdörtgenler panellere
büyükten küçüğe, ilk sığana yerleştirilir. Panel boyları: tam boy şeritlerin boyları; kesik parçalar sığdıkları en kısa boydan.

Hesapta LLM yoktur. Ölçüler cm; alanlar m², boylar m olarak raporlanır.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

TOL = 1e-3
EPS = 1e-6


def tavan(x: float) -> int:
    return int(math.ceil(x - 1e-9))


# ───────────────────────────────────────────────────────────── düzlemler ──
def duzlem_kur(d: dict) -> dict:
    yx, yy = d["yukari"]
    n = math.hypot(yx, yy)
    yx, yy = yx / n, yy / n
    s = d["sacak"]
    ref = (s["x"], 0.0) if "x" in s else (0.0, s["y"])
    kok = math.sqrt(1 + d["egim"] ** 2)
    sag = (yy, -yx)                                   # dışarıdan (saçak tarafından) bakışla sağ

    def yatay(p):                                     # saçak çizgisinden yukarı, planda
        return (p[0] - ref[0]) * yx + (p[1] - ref[1]) * yy

    def kot(p):
        return d["sacak_kotu"] + d["egim"] * yatay(p)

    def yuz(p):                                       # açılım koordinatı: (soldan sağa, saçaktan yukarı eğimli boy)
        return (p[0] * sag[0] + p[1] * sag[1], yatay(p) * kok)

    plan = [tuple(p) for p in d["plan"]]
    plan = [q for i, q in enumerate(plan) if math.hypot(q[0] - plan[i - 1][0], q[1] - plan[i - 1][1]) > TOL]      # üst üste köşeleri at
    cokgen = Polygon(plan)
    if not cokgen.is_valid or cokgen.area < 1:
        raise SystemExit(f"Çatı düzleminin planı geçersiz: {d['ad']}")
    if cokgen.exterior.is_ccw is False:
        plan = plan[::-1]
        cokgen = Polygon(plan)
    # karkas: düzlemin makaslarla taşınan kısmı, görünen kısımdan büyükse (alçak bir çatının altına giren yüz); aşık sıraları buna göre
    karkas = Polygon([yuz(tuple(p)) for p in d["karkas"]]) if d.get("karkas") else None
    return dict(d, yukari=(yx, yy), sag=sag, kok=kok, kot=kot, yatay=yatay, yuz=yuz, plan=plan, cokgen=cokgen,
                plan_m2=cokgen.area / 1e4, yuzey_m2=cokgen.area * kok / 1e4,
                ucboyut=[(p[0], p[1], kot(p)) for p in plan], acilim=Polygon([yuz(p) for p in plan]), acilim_karkas=karkas)


def _ortusme(a0, a1, b0, b1):
    """Doğrusal iki parçanın (a0–a1, b0–b1) ortak kısmı; yoksa None. Planda."""
    ax, ay = a1[0] - a0[0], a1[1] - a0[1]
    L = math.hypot(ax, ay)
    if L < TOL:
        return None
    ux, uy = ax / L, ay / L
    for q in (b0, b1):                                # b, a'nın doğrusunda mı
        if abs((q[0] - a0[0]) * uy - (q[1] - a0[1]) * ux) > 0.05:
            return None
    tb = sorted(((q[0] - a0[0]) * ux + (q[1] - a0[1]) * uy) for q in (b0, b1))
    lo, hi = max(0.0, tb[0]), min(L, tb[1])
    if hi - lo < 0.05:
        return None
    return (a0[0] + ux * lo, a0[1] + uy * lo), (a0[0] + ux * hi, a0[1] + uy * hi), lo, hi


def _ic_nokta(dz: dict, p, q, adim: float = 0.5):
    """p–q kenarının ortasından düzlemin içine doğru küçük bir adım atılmış nokta."""
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    ex, ey = q[0] - p[0], q[1] - p[1]
    L = math.hypot(ex, ey)
    for nx, ny in ((-ey / L, ex / L), (ey / L, -ex / L)):
        c = (mx + nx * adim, my + ny * adim)
        if dz["cokgen"].contains(Point(c)):
            return c
    return None


def kenarlari_bul(duzlemler: list[dict], ozel: list[dict] | None = None) -> list[dict]:
    """Bütün düzlemlerin kenarları, türleriyle. Ortak kenarlar bir kez yazılır."""
    ozel = ozel or []
    ham = []                                          # (düzlem indisi, p, q)
    for i, dz in enumerate(duzlemler):
        pl = dz["plan"]
        for p, q in zip(pl, pl[1:] + pl[:1]):
            ham.append((i, p, q))
    cik: list[dict] = []
    kullanilan: dict[int, list[tuple[float, float]]] = {k: [] for k in range(len(ham))}

    def uzunluk3(dz, p, q):
        return math.hypot(math.hypot(q[0] - p[0], q[1] - p[1]), dz["kot"](q) - dz["kot"](p))

    for a in range(len(ham)):
        ia, pa, qa = ham[a]
        for b in range(a + 1, len(ham)):
            ib, pb, qb = ham[b]
            if ia == ib:
                continue
            o = _ortusme(pa, qa, pb, qb)
            if not o:
                continue
            p, q, lo, hi = o
            A, B = duzlemler[ia], duzlemler[ib]
            if abs(A["kot"](p) - B["kot"](p)) > 1.0 or abs(A["kot"](q) - B["kot"](q)) > 1.0:
                continue                              # planda üst üste ama farklı kotta (ör. saçağın altından geçen alçak çatı)
            kullanilan[a].append((lo, hi))
            ob = _ortusme(pb, qb, p, q)
            kullanilan[b].append((ob[2], ob[3]))
            ic = _ic_nokta(A, p, q)
            fark = (B["kot"](ic) - A["kot"](ic)) if ic else 0.0
            yatay = abs(A["kot"](p) - A["kot"](q)) < 0.5
            if abs(fark) < 0.01:
                tur = "duzlem_ici"
            elif fark > 0:                            # öteki düzlem bu tarafta daha yüksekte kalırdı: dışbükey birleşim
                tur = "mahya" if yatay else "kirma"
            else:
                tur = "vadi"
            cik.append({"tur": tur, "duzlemler": [A["ad"], B["ad"]], "p": p, "q": q, "plan_boy": math.hypot(q[0] - p[0], q[1] - p[1]),
                        "boy": uzunluk3(A, p, q), "kot": [A["kot"](p), A["kot"](q)]})
    for a, (ia, pa, qa) in enumerate(ham):            # ortak olmayan kısımlar
        A = duzlemler[ia]
        L = math.hypot(qa[0] - pa[0], qa[1] - pa[1])
        ux, uy = (qa[0] - pa[0]) / L, (qa[1] - pa[1]) / L
        imlec, bos = 0.0, []
        for lo, hi in sorted(kullanilan[a]):
            if lo - imlec > 0.05:
                bos.append((imlec, lo))
            imlec = max(imlec, hi)
        if L - imlec > 0.05:
            bos.append((imlec, L))
        for lo, hi in bos:
            p, q = (pa[0] + ux * lo, pa[1] + uy * lo), (pa[0] + ux * hi, pa[1] + uy * hi)
            yatay = abs(A["kot"](p) - A["kot"](q)) < 0.5
            ic = _ic_nokta(A, p, q)
            if yatay:
                tur = "sacak" if (ic and A["kot"](ic) > A["kot"](p)) else "ust"
            else:
                tur = "alin"
            for o in ozel:
                if o["duzlem"] == A["ad"] and _ortusme(p, q, tuple(o["p"]), tuple(o["q"])):
                    tur = o["tur"]
            cik.append({"tur": tur, "duzlemler": [A["ad"]], "p": p, "q": q, "plan_boy": hi - lo, "boy": uzunluk3(A, p, q), "kot": [A["kot"](p), A["kot"](q)]})
    return cik


# ─────────────────────────────────────────────────────────────── kalkan ──
def kalkan(duzlemler: list[dict], k: dict, duvar_ustu: float, adim: float = 1.0) -> dict:
    """Kalkan (alın duvarı) çokgeni ve alanı. `ust`: kalkanın üst çizgisini veren düzlemler; `alt`: önünde duran alçak çatının düzlemleri
    (verilmişse kalkan yalnız onların üstünde kalan kısımdır; verilmemişse duvar üstünden başlar). Çizgi: eksen 'y' ise y = konum."""
    adli = {d["ad"]: d for d in duzlemler}
    x0, x1 = k["aralik"]
    c = k["konum"]
    ic_yon = {"kuzey": 1.0, "guney": -1.0, "dogu": 1.0, "bati": -1.0}[k["ic"]]

    def nokta(s, kay):                                # çizgi üzerinde s; kay kadar içeri (ic_yon) ya da dışarı
        return (s, c + kay) if k["eksen"] == "y" else (c + kay, s)

    def kotu(adlar, s, kay):
        en = None
        for ad in adlar:
            dz = adli[ad]
            if dz["cokgen"].buffer(0.01).contains(Point(nokta(s, kay))):
                z = dz["kot"](nokta(s, 0.0))
                en = z if en is None else max(en, z)
        return en

    n = max(2, int(round((x1 - x0) / adim)))
    ust_c, alt_c, alan = [], [], 0.0
    onceki = None
    for i in range(n + 1):
        s = x0 + (x1 - x0) * i / n
        zu = kotu(k["ust"], s, 0.5 * ic_yon)
        if k.get("alt"):
            za = kotu(k["alt"], s, -0.5 * ic_yon)
            za = None if za is None else max(za, duvar_ustu)
        else:
            za = duvar_ustu
        h = (zu - za) if (zu is not None and za is not None and zu > za) else 0.0
        if onceki is not None:
            alan += (h + onceki[1]) / 2 * (s - onceki[0])
        onceki = (s, h)
        if h > 0:
            ust_c.append((s, zu))
            alt_c.append((s, za))
    kose = ust_c + alt_c[::-1]
    return {"ad": k["ad"], "eksen": k["eksen"], "konum": c, "ic": k["ic"], "alan_m2": alan / 1e4, "kose": kose,
            "tepe": max((z for _, z in ust_c), default=None)}


# ───────────────────────────────────────────────────────────────── aşık ──
def asik_siralari(dz: dict, aralik: float, ust_esik: float = 30.0) -> list[dict]:
    """Bir yüzdeki aşık sıraları. Sıralar düzlemin saçak çizgisinden (açılımda t = 0) itibaren `aralik` (cm) aralıkla dizilir; ilk sıra saçak
    çizgisinin üstündedir. Sıranın boyu, yüzün o yükseklikteki genişliğidir. Yüzün bir üst yatay kenarının (mahya, duvar dibi) altındaki son
    sıra ile kenar arasında `ust_esik`ten fazla boşluk kalıyorsa kenara, o kenarın boyunda bir sıra daha konur.
    Yüzün alt kenarı saçak çizgisinin üstünde başlıyorsa o kenara ayrıca sıra konmaz; sıralar yine saçak çizgisinden sayılır.
    Yüz: düzlemin makaslarla taşınan kısmı (`karkas`; verilmemişse görünen kısmı). Alçak bir çatının altına giren yüzde (cumbanın doğu yüzü)
    makaslar ve aşıklar görünen kısımdan uzundur.
    Dayanak (paftalar; ayrıntı `kurallar.json` → `cok_duzlemli_cati`): 90 m² projede son sıra ile mahya arasında 41 cm var, mahyanın 20 cm altında
    bir sıra daha çizili; 62 m² projede boşluk 13 cm, ek sıra yok. Kör test projesinin paftasında ana yüzlerde ek sıra yok (boşluk 22 ve 33 cm),
    sundurmanın duvar dibinde bir sıra var; cumba mahyasının iki yanında ise boşluk 49 cm olduğu halde sıra yok: bu kural oraya birer sıra koyar
    (2,48 + 2,78 m). Paftadaki, verandanın kırma köşesinde eğim yönünde duran iki parça (2,82 + 1,70 m) bu kuralda yoktur.
    6 Ekim'de dondurulan listede kural başkaydı: boşluğa bakılmadan her üst kenarın 20 cm altına bir mahya aşığı (commit 0658a1d)."""
    ac = dz.get("acilim_karkas") or dz["acilim"]
    u0, t0, u1, t1 = ac.bounds
    siralar = []
    k = 0
    while k * aralik < t1 - TOL:
        t = k * aralik
        g = ac.intersection(LineString([(u0 - 1, t + (0.01 if k == 0 else 0.0)), (u1 + 1, t + (0.01 if k == 0 else 0.0))]))
        boy = g.length if not g.is_empty else 0.0
        if boy > 1.0:
            siralar.append({"t": t, "boy": boy, "tur": "sira"})
        k += 1
    # üst yatay kenarlar: açılımın, yüzün içi altında kalan yatay kenarları
    govde = ac.buffer(0.05)
    pts = list(ac.exterior.coords)[:-1]
    for (ua, ta), (ub, tb) in zip(pts, pts[1:] + pts[:1]):
        if abs(ta - tb) > 0.05 or abs(ub - ua) < 1.0:
            continue
        um = (ua + ub) / 2
        if not ac.contains(Point(um, ta - 0.5)) or ac.contains(Point(um, ta + 0.5)):
            continue                                  # alt kenar (saçak) ya da çokgenin içinden geçen çizgi
        alttaki = [s["t"] for s in siralar if s["tur"] == "sira" and s["t"] < ta - TOL and govde.contains(Point(um, s["t"]))]
        bosluk = ta - max(alttaki) if alttaki else ta - t0
        if bosluk > ust_esik + TOL:
            siralar.append({"t": ta, "boy": abs(ub - ua), "tur": "ust_sira"})
    return siralar


# ───────────────────────────────────────────────────────── kaplama dizilimi ──
@dataclass
class Parca:
    yuz: str
    serit: int
    u0: float
    u1: float
    tip: str                    # duz | P (düz alt, çapraz üst) | Q (çapraz alt, düz üst) | karma
    yon: str                    # art | azal | '' : çapraz kenar sağa doğru yükseliyor mu
    egim: float                 # çapraz kenarın eğimi (boy / en)
    boy: float                  # parçanın kesileceği dikdörtgenin boyu (taşma dahil)
    kisa: float                 # kısa kenarındaki boy
    tasma: float
    kose: list = field(default_factory=list)
    panel: int = 0
    konum: str = ""

    @property
    def en(self) -> float:
        return self.u1 - self.u0


def _profil(noktalar, u0, u1):
    """Bir kenar zincirinin (u'ya göre sıralı noktalar) biçimi: ('duz', t) | ('capraz', t(u0), t(u1)) | ('karma', ...)."""
    ts = [t for _, t in noktalar]
    if max(ts) - min(ts) < 0.05:
        return ("duz", sum(ts) / len(ts))
    if len(noktalar) == 2:
        return ("capraz", noktalar[0][1], noktalar[1][1])
    # ikiden çok nokta: hepsi aynı doğru üzerinde mi
    (ua, ta), (ub, tb) = noktalar[0], noktalar[-1]
    if all(abs((t - ta) * (ub - ua) - (tb - ta) * (u - ua)) < 0.05 * max(1.0, abs(ub - ua)) for u, t in noktalar):
        return ("capraz", ta, tb)
    return ("karma",)


def yuz_parcalari(dz: dict, kenarlar: list[dict], kapatma: float, tasma: float) -> list[Parca]:
    """Bir yüzün şerit parçaları. Şeritler saçağın sol ucundan başlar (saçağı yoksa yüzün sol ucundan); yüzün solda kalan kısmı varsa
    şeritler o yöne de sürer. Saçak kenarına oturan parçaların boyuna `tasma` eklenir."""
    ac = dz["acilim"]
    u_min, t_min, u_max, t_max = ac.bounds
    sacaklar = [(min(dz["yuz"](e["p"])[0], dz["yuz"](e["q"])[0]), max(dz["yuz"](e["p"])[0], dz["yuz"](e["q"])[0]), dz["yuz"](e["p"])[1])
                for e in kenarlar if e["tur"] == "sacak" and dz["ad"] in e["duzlemler"]]
    capa = min((s[0] for s in sacaklar), default=u_min)
    k0 = -tavan((capa - u_min) / kapatma - EPS) if capa - u_min > TOL else 0
    cik: list[Parca] = []
    k = k0
    while capa + k * kapatma < u_max - TOL:
        a, b = max(capa + k * kapatma, u_min), min(capa + (k + 1) * kapatma, u_max)
        k += 1
        if b - a < TOL:
            continue
        g = ac.intersection(box(a, t_min - 1, b, t_max + 1))
        for p in (g.geoms if g.geom_type in ("MultiPolygon", "GeometryCollection") else [g]):
            if p.geom_type != "Polygon" or p.area < 0.5:
                continue
            pts = list(p.exterior.coords)[:-1]
            pu0, pt0, pu1, pt1 = p.bounds
            # alt ve üst zincir: halka saat yönünün tersine dolaşılır; alt zincir sol-alt köşeden sağ-alt köşeye, üst zincir sağ-üstten sol-üste
            if not p.exterior.is_ccw:
                pts = pts[::-1]
            sol = sorted((q for q in pts if abs(q[0] - pu0) < TOL), key=lambda q: q[1])
            sag_ = sorted((q for q in pts if abs(q[0] - pu1) < TOL), key=lambda q: q[1])

            def zincir(alt: bool):
                bas, son = (sol[0], sag_[0]) if alt else (sag_[-1], sol[-1])
                i, j = pts.index(bas), pts.index(son)
                yol = pts[i:j + 1] if i <= j else pts[i:] + pts[:j + 1]
                return sorted(yol) if alt else sorted(yol)
            alt_p, ust_p = _profil(zincir(True), pu0, pu1), _profil(zincir(False), pu0, pu1)
            sacakta = any(abs(pt0 - st) < 0.05 and min(pu1, s1) - max(pu0, s0) > TOL for s0, s1, st in sacaklar) and alt_p[0] == "duz"
            ek = tasma if sacakta else 0.0
            boy = pt1 - pt0 + ek
            en = pu1 - pu0
            if alt_p[0] == "duz" and ust_p[0] == "duz":
                tip, yon, eg, kisa = "duz", "", 0.0, boy
            elif alt_p[0] == "duz" and ust_p[0] == "capraz":
                tip, yon, eg = "P", ("art" if ust_p[2] > ust_p[1] else "azal"), abs(ust_p[2] - ust_p[1]) / en
                kisa = boy - eg * en
            elif alt_p[0] == "capraz" and ust_p[0] == "duz":
                tip, yon, eg = "Q", ("art" if alt_p[2] > alt_p[1] else "azal"), abs(alt_p[2] - alt_p[1]) / en
                kisa = boy - eg * en
            else:
                tip, yon, eg, kisa = "karma", "", 0.0, boy
            cik.append(Parca(dz["ad"], len(cik) + 1, pu0, pu1, tip, yon, eg, boy, kisa, ek, [(q[0], q[1]) for q in pts]))
    return cik


def es_boyu(p: Parca, q: Parca, kapatma: float, pay: float) -> float:
    """Aynı açıyla kesilmiş iki parçanın tek dikdörtgenden çıkması için gereken boy (bkz. cati_acilim.es_boyu)."""
    return max(p.boy, q.boy, p.boy + q.boy - p.egim * kapatma + pay)


def dizilim(duzlemler: list[dict], kenarlar: list[dict], kapatma: float, tasma: float, pay: float, paylas: bool = True,
            boylar: list[float] | None = None, boy_birlestirme: float = 10.0) -> dict:
    """Kaplama dizilimi. `boylar` verilirse yalnız o panel boyları kullanılır (cm); verilmezse tam boy şeritlerin boyları
    (mm'ye yukarı; birbirine `boy_birlestirme` cm'den yakın boylar uzun olanda birleşir). Dönen: paneller, boy başına adet."""
    yuzler = {dz["ad"]: yuz_parcalari(dz, kenarlar, kapatma, tasma) for dz in duzlemler}
    yukari = {dz["ad"]: dz["yukari"] for dz in duzlemler}
    hepsi = [p for dz in duzlemler for p in yuzler[dz["ad"]]]
    sira = {id(p): i for i, p in enumerate(hepsi)}

    def karsi(a: str, b: str) -> bool:
        return abs(yukari[a][0] + yukari[b][0]) < 1e-6 and abs(yukari[a][1] + yukari[b][1]) < 1e-6

    # 1) panel boyları
    if boylar is None:
        tam = sorted({math.ceil(p.boy * 10 - 1e-6) / 10 for p in hepsi if p.tip == "duz" and p.en > kapatma - TOL}, reverse=True)
        for dz in duzlemler:                          # tam boy şeridi olmayan yüz: en uzun parçasının boyu
            if not any(p.tip == "duz" and p.en > kapatma - TOL for p in yuzler[dz["ad"]]) and yuzler[dz["ad"]]:
                tam.append(math.ceil(max(p.boy for p in yuzler[dz["ad"]]) * 10 - 1e-6) / 10)
        tam = sorted(set(tam), reverse=True)
        boylar = []
        for b in tam:                                 # yakın boylar uzun olanda birleşir
            if boylar and boylar[-1] - b <= boy_birlestirme + TOL:
                continue
            boylar.append(b)
    boylar = sorted(boylar)
    en_uzun = boylar[-1]

    def sigdigi_boy(x: float) -> float | None:
        return next((b for b in boylar if x <= b + EPS), None)

    # 2) dikdörtgenler: düz ve karma parçalar tek başına; çapraz parçalar eşleriyle
    dikd: list[dict] = []
    for p in hepsi:
        if p.tip in ("duz", "karma"):
            p.konum = "tam" if p.tip == "duz" else "karma"
            dikd.append({"boy": p.boy, "parcalar": [p]})
    capraz = sorted((p for p in hepsi if p.tip in ("P", "Q")), key=lambda p: (-p.boy, sira[id(p)]))
    bitti: set[int] = set()
    for p in capraz:
        if id(p) in bitti:
            continue
        bitti.add(id(p))
        es = None
        if paylas:
            for q in capraz:
                if id(q) in bitti or abs(q.egim - p.egim) > 1e-3 * max(1.0, p.egim) or q.yon != p.yon:
                    continue
                dogal = q.tip != p.tip                                        # alt parça + üst parça: çevirmeden
                cevrik = q.tip == p.tip and karsi(p.yuz, q.yuz)                # aynı tür: karşı yüzde, çevrilerek (kırma çatı kuralı)
                if not (dogal or cevrik):
                    continue
                if sigdigi_boy(es_boyu(p, q, kapatma, pay)) is None:
                    continue
                if sigdigi_boy(es_boyu(p, q, kapatma, pay)) > (sigdigi_boy(p.boy) or en_uzun) + EPS:
                    continue                                                  # eş yüzünden daha uzun panele geçilmez
                es = q
                break
        if es is None:
            p.konum = "tek"
            dikd.append({"boy": p.boy, "parcalar": [p]})
        else:
            bitti.add(id(es))
            p.konum, es.konum = "alt", "üst"
            dikd.append({"boy": es_boyu(p, es, kapatma, pay), "parcalar": [p, es]})

    # 3) dikdörtgenler panellere: büyükten küçüğe, ilk sığana; yeni panel sığdığı en kısa boydan
    dikd.sort(key=lambda d: (-d["boy"], sira[id(d["parcalar"][0])]))
    paneller: list[dict] = []
    for d in dikd:
        if sigdigi_boy(d["boy"]) is None:
            raise SystemExit(f"Parça panel boylarının hiçbirine sığmıyor: {d['boy']:.1f} cm ({d['parcalar'][0].yuz})")
        yer = next((pn for pn in paneller if d["boy"] + pay <= pn["kalan"] + EPS), None)
        if yer is not None:
            yer["kalan"] -= d["boy"] + pay
            yer["dikdortgenler"].append(d)
        else:
            b = sigdigi_boy(d["boy"])
            paneller.append({"boy": b, "kalan": b - d["boy"], "dikdortgenler": [d]})
    paneller.sort(key=lambda pn: min(sira[id(p)] for d in pn["dikdortgenler"] for p in d["parcalar"]))
    for no, pn in enumerate(paneller, start=1):
        pn["no"] = no
        for d in pn["dikdortgenler"]:
            for p in d["parcalar"]:
                p.panel = no
    adet: dict[float, int] = {}
    for pn in paneller:
        adet[pn["boy"]] = adet.get(pn["boy"], 0) + 1
    kaplanan = sum(dz["yuzey_m2"] for dz in duzlemler)
    return {"kapatma_cm": kapatma, "tasma_cm": tasma, "kesim_payi_cm": pay, "paylas": paylas, "boylar_cm": boylar, "yuzler": yuzler, "paneller": paneller,
            "adet": len(paneller), "boy_adet": {b: adet.get(b, 0) for b in sorted(adet, reverse=True)},
            "panel_m2": sum(pn["boy"] for pn in paneller) * kapatma / 1e4, "yuzey_m2": kaplanan,
            "parca_adedi": len(hepsi), "tam_boy": sum(1 for p in hepsi if p.konum == "tam"),
            "cift": sum(1 for p in hepsi if p.konum == "alt"), "tek": sum(1 for p in hepsi if p.konum == "tek"),
            "karma": sum(1 for p in hepsi if p.konum == "karma")}


# ──────────────────────────────────────────────────────────────── toplu ──
def cati_kur(cati: dict, kurallar: dict | None = None) -> dict:
    """Tanımdaki çatıdan bütün türetilenler. `kurallar` verilirse aşık ve dizilim de hesaplanır."""
    dzl = [duzlem_kur(d) for d in cati["duzlemler"]]
    kn = kenarlari_bul(dzl, cati.get("kenar_ozel"))
    top: dict[str, float] = {}
    for e in kn:
        top[e["tur"]] = top.get(e["tur"], 0.0) + e["boy"]
    kalkanlar = [kalkan(dzl, k, cati.get("duvar_ustu", 270.0)) for k in cati.get("kalkanlar", [])]
    cik = {"duzlemler": dzl, "kenarlar": kn, "kenar_toplam_cm": top, "kalkanlar": kalkanlar,
           "yuzey_m2": sum(d["yuzey_m2"] for d in dzl), "plan_m2": unary_union([d["cokgen"] for d in dzl]).area / 1e4}
    if kurallar:
        ar = kurallar["asik"]["aralik_m"]["deger"] * 100
        cd = kurallar["cok_duzlemli_cati"]["deger"]
        cik["asik"] = {d["ad"]: asik_siralari(d, ar, ust_esik=cd["ust_sira_esigi_m"] * 100) for d in dzl}
        cik["dere"] = dere_hatlari(dzl, kn, kurallar, cati.get("sacak", 30.0))
    return cik


# ───────────────────────────────────────────────────────────────── dere ──
def sacak_cephesi(e: dict, kenarlar: list[dict], sacak: float) -> float:
    """Bir saçak kenarının altındaki cephenin boyu: kenarın, çatının dış köşesinde biten her ucundan saçak payı düşülür.
    Vadide biten uçta pay yoktur (saçak orada duvar hizasında biter). Dikdörtgen kırma çatıda cephenin kendisidir."""
    boy = e["boy"]
    for p in (e["p"], e["q"]):
        komsu = {o["tur"] for o in kenarlar if o is not e and any(math.hypot(p[0] - r[0], p[1] - r[1]) < 1.0 for r in (o["p"], o["q"]))}
        if "vadi" not in komsu:
            boy -= sacak
    return max(0.0, boy)


def dere_hatlari(duzlemler: list[dict], kenarlar: list[dict], kurallar: dict, sacak: float = 30.0) -> dict:
    """Dere hatları: dereli düzlemlerin saçak kenarları. Çatı panelli çatıda (ek yapı) dere yoktur (kör test projesinin listesi ve dere paftası).
    Kural seti 0.18'den beri (`panel_cati_kenarlari`; Lokman, 10 Ekim 2026: veranda, sundurma ve müştemilat "o 5 görseldeki gibi") tek eğimli
    çatı panelli bütün çatıların saçağında da dere vardır; anahtar yoksa eski davranış.
    Uç: bir hattın ucu; iki hattın buluştuğu köşe tek uçtur. Serbest uç: başka bir hatla buluşmayan uç (dere kapağı oraya gelir)."""
    pk = (kurallar.get("panel_cati_kenarlari") or {}).get("deger")
    panelli_dere = pk["dere"] if pk else kurallar["ek_yapi_ve_korkuluk"]["deger"]["cati_panelli_cati"]["dere"]
    adli = {d["ad"]: d for d in duzlemler}
    hatlar = [e for e in kenarlar if e["tur"] == "sacak" and (panelli_dere or adli[e["duzlemler"][0]].get("ust_yapi") != "cati_paneli")]
    uclar: list[list] = []                            # [x, y, kaç hattın ucu]
    for e in hatlar:
        for p in (e["p"], e["q"]):
            for u in uclar:
                if math.hypot(u[0] - p[0], u[1] - p[1]) < 1.0:
                    u[2] += 1
                    break
            else:
                uclar.append([p[0], p[1], 1])
    return {"hatlar": [{"duzlem": e["duzlemler"][0], "p": e["p"], "q": e["q"], "boy": e["boy"], "cephe": sacak_cephesi(e, kenarlar, sacak)} for e in hatlar],
            "boy": sum(e["boy"] for e in hatlar), "uclar": uclar,
            "uc": len(uclar), "serbest_uc": sum(1 for u in uclar if u[2] == 1)}
