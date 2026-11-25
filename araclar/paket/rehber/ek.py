"""İE-17 PR-2 köşe kırması ve kubbe (63 m², AP-24): rehberin şablonunda (`sahne.js`) yeri olmayan parçalar, "ek parça" olarak.

Şablonun çatısı beşik yüzlerini kurar; köşe kırmasının tek eğimli mahal çatısı ve kubbe onun dışındadır. Bu parçalar rehbere iki
kaynaktan, kendi geometrileriyle gelir; rehber kendi geometrisini kurmaz (D-28 madde 1):

- **Kart modelinden** (`<kod>_model.ifc`, motorun 3B modeli): mahalin çatısının makasları (kısa ve çapraz makas, MA-06, MA-07), aşıkları,
  kaplaması, deresi ve inişleri; kubbenin pencereleri ve çatısı. Parça IFC'deki üçgenleriyle (`ifc_ucgen`) sahneye gelir.
- **Orijinal üretim çizimlerinden** (Lokman, 24 Kasım 2026 07:35:17: "Montaj Rehberlerinde bundan sonra orjinal üretim çizimleri
  dursun"): kubbenin çelik karkas duvarları, üst bandı ve makasları FrameBuilder dosyalarından (`araclar/uretim/veri/kubbe.json`, BK-76).
  Her çerçeve motorun kubbesindeki yerine (pano, bant, makas) oturtulur; çerçevenin kendi ölçüsü değişmez.

Veri biçimi (`sahne.js` › Ek parçalar): her parça {adim, sira, ad, kod, satir, mat} ve geometri olarak `mesh` ({v: [x, y, z, …] cm,
f: [i, j, k, …]}, plan çerçevesi) ya da `cubuk` ([x0, y0, z0, x1, y1, z1, en, derinlik, nx, ny, nz]: p→q boyunca kutu, derinlik n yönünde).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
URETIM = KOK / "araclar" / "uretim" / "veri" / "kubbe.json"


def ifc_ozellik(ifc_yolu: Path, desen: str) -> dict[str, dict]:
    """Kart modelinde adı desene uyan parçaların bütün özellik setleri, tek sözlükte: {ad: {anahtar: değer}}."""
    import ifcopenshell
    import ifcopenshell.util.element as ue

    f = ifcopenshell.open(str(ifc_yolu))
    out = {}
    for p in f.by_type("IfcProduct"):
        if re.match(desen, p.Name or ""):
            d = {}
            for v in ue.get_psets(p).values():
                d.update({k: x for k, x in v.items() if k != "id"})
            out[p.Name] = d
    return out


def ifc_ucgen(ifc_yolu: Path, adlar: set[str]) -> dict[str, dict]:
    """Kart modelindeki parçaların üçgenleri (cm, plan çerçevesi): {ad: {v: [...], f: [...]}}."""
    import ifcopenshell
    import ifcopenshell.geom
    import numpy as np

    f = ifcopenshell.open(str(ifc_yolu))
    st = ifcopenshell.geom.settings()
    st.set(st.USE_WORLD_COORDS, True)
    out = {}
    for p in f.by_type("IfcProduct"):
        if (p.Name or "") not in adlar:
            continue
        s = ifcopenshell.geom.create_shape(st, p)
        v = (np.array(s.geometry.verts).reshape(-1, 3) * 100).round(2)
        out[p.Name] = {"v": [float(x) for x in v.reshape(-1)], "f": [int(i) for i in s.geometry.faces]}
    return out


def _birlesik(parcalar: list[dict]) -> dict:
    """Birden çok üçgen kümesini tek kümeye toplar."""
    v, f = [], []
    for p in parcalar:
        n = len(v) // 3
        v += p["v"]
        f += [i + n for i in p["f"]]
    return {"v": v, "f": f}


def mahal(ifc_yolu: Path, mahal_adlari: set[str], ls) -> tuple[list[dict], set[str]]:
    """Köşe kırmasının parçaları kart modelinden. Dönen: (ek parçalar, şablonun atlaması gereken IFC adları)."""
    if not mahal_adlari:
        return [], set()
    OZ = ifc_ozellik(ifc_yolu, r"^(MAKAS_\d+|ASIK_\d+|CATI_\d+|DERE_\d+|INIS_\d+)$")
    mahalde = lambda o: (o.get("CatiParcasi") or o.get("Cati") or o.get("Duzlem")) in mahal_adlari   # noqa: E731
    makaslar = sorted(n for n, o in OZ.items() if n.startswith("MAKAS_") and mahalde(o))
    import ifcopenshell
    f = ifcopenshell.open(str(ifc_yolu))
    uyeler = {mk: sorted(p.Name for p in f.by_type("IfcProduct") if (p.Name or "").startswith(mk + "_")) for mk in makaslar}
    tek = {n for n, o in OZ.items() if not n.startswith("MAKAS_") and mahalde(o)}
    U = ifc_ucgen(ifc_yolu, tek | {u for us in uyeler.values() for u in us})
    ek, sira = [], 0
    for mk in makaslar:
        o = OZ[mk]
        kalem = o.get("BOMKalem", mk)
        ek.append({"adim": "makas", "sira": 100 + sira, "ad": kalem.split(" · ")[0], "kod": o.get("KartKodu"), "mat": "truss",
                   "mesh": _birlesik([U[u] for u in uyeler[mk] if u in U]),
                   "satir": [["Bu parça", f"{kalem} ({mk})"], ["Liste", ls(kalem)],
                             ["Kaynak", "yer ve sayı çatı tanımından (çizim, liste ve 3B modelle aynı); geometri kart modelinden"]]})
        sira += 1
    for n in sorted(tek):
        o = OZ[n]
        cati = o.get("Cati") or o.get("Duzlem")
        if n.startswith("ASIK_"):
            ek.append({"adim": "asik", "sira": 300 + sira, "ad": "Aşık (omega)", "kod": o.get("KartKodu"), "mat": "asik", "mesh": U[n],
                       "satir": [["Bu parça", f"{cati} · {n}"], ["Liste", ls("Aşık")], ["Kaynak", "kart modeli"]]})
        elif n.startswith("CATI_"):
            ek.append({"adim": "kaplama", "sira": 300 + sira, "ad": "Trapez sac", "kod": None, "mat": "roof", "mesh": U[n], "osb": True,
                       "satir": [["Bu parça", f"{cati} · tek eğimli yüz"], ["Liste", ls(f"Trapez sac · {cati}")],
                                 ["Kaynak", "kart modelinin çatı yüzeyi; levhalar ayrı gösterilmedi"]]})
        elif n.startswith("DERE_"):
            ek.append({"adim": "dere", "sira": 300 + sira, "ad": "Metal dere", "kod": o.get("KartKodu"), "mat": "gutter", "mesh": U[n],
                       "satir": [["Bu parça", f"{cati} saçağı · {n}"], ["Liste", ls("Metal dere")], ["Kaynak", "kart modeli"]]})
        elif n.startswith("INIS_"):
            ek.append({"adim": "dere", "sira": 300 + sira, "ad": "Metal dere inişi", "kod": o.get("KartKodu"), "mat": "gutter", "mesh": U[n],
                       "satir": [["Bu parça", f"{cati} · {n}"], ["Liste", ls("Metal dere inişi aparatı")], ["Kaynak", "kart modeli"]]})
        sira += 1
    return ek, tek | set(makaslar)


# ---------- kubbe: orijinal üretim çizimleri ----------
EN, DER = 5.4, 8.0          # C 80 × 54: çerçevenin düzleminde 5,4 cm, duvarın içine doğru 8 cm (FrameBuilder dosyası, BK-76)


def _cerceve_cubuklari(fr: dict, A, B, z0: float, nrm, merkez: bool = True) -> list[list[float]]:
    """Üretim çerçevesini plan doğrusu A→B üzerine (yerel x A'dan B'ye, yerel y yukarı, taban `z0`) oturtur. Çerçeve doğrunun ortasına
    ortalanır (`merkez`); çubuklar eksenlerinden (mm → cm)."""
    (ax, ay), (bx, by) = A, B
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    W = fr["ozet"]["dis_olcu_mm"][0] / 10
    x_bas = (L - W) / 2 if merkez else 0.0
    out = []
    for p in fr["parcalar"]:
        x1, y1, x2, y2 = (p[k] / 10 for k in ("x1", "y1", "x2", "y2"))
        P = (ax + ux * (x_bas + x1), ay + uy * (x_bas + x1), z0 + y1)
        Q = (ax + ux * (x_bas + x2), ay + uy * (x_bas + x2), z0 + y2)
        out.append([round(v, 2) for v in (*P, *Q, EN, DER, *nrm)])
    return out


def kubbe(HZ: dict, ifc_yolu: Path, ls) -> tuple[list[dict], set[str]]:
    """Kubbenin parçaları: duvar, bant ve makas üretim çizimlerinden; pencere ve çatı kart modelinden. Dönen: (ek parçalar, motorun
    kubbe parçalarından şablonun çizmediği adlar (bilgi))."""
    KB = HZ.get("kubbeler") or []
    if not KB:
        return [], set()
    if len(KB) != 1:
        raise ValueError(f"{len(KB)} kubbe; üretim çizimleri tek kubbenin (63 m²)")
    kb = KB[0]
    FR = {f["cerceve"]: f for f in json.loads(URETIM.read_text(encoding="utf-8"))}
    ek = []
    H_DUVAR = FR["KUBBE-DUVAR1"]["ozet"]["dis_olcu_mm"][1] / 10
    # duvarlar: yan 1, ön 2, yan 3 — motorun kubbesindeki pano sırası (yan, ön, yan; `_kubbe_girdisi`)
    duvar_ad = {0: "KUBBE-DUVAR1", 1: "KUBBE-DUVAR2", 2: "KUBBE-DUVAR3"}
    for i, q in enumerate(kb["panolar"]):
        fr = FR[duvar_ad[i]]
        (ax, ay), (bx, by) = q["dis_kenar"]
        dx, dy = q["disari"]
        A, B = (ax - dx * 5, ay - dy * 5), (bx - dx * 5, by - dy * 5)          # duvarın ekseni: dış yüzden 5 cm içeride
        ek.append({"adim": "kubbe_duvar", "sira": i, "ad": f"Kubbe duvarı · {fr['dosya'].removesuffix('.csv')}", "kod": None, "mat": "steel",
                   "cubuk": _cerceve_cubuklari(fr, A, B, 0.0, [dx, dy, 0]),
                   "satir": [["Bu parça", f"{fr['dosya'].removesuffix('.csv')} · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm · "
                                          f"{fr['ozet']['cubuk']} çubuk"],
                             ["Profil", "C 80 × 54, 0,8 mm (üretim dosyası)"],
                             ["Yer", f"kubbenin {'ön' if q['tur'] == 'on' else 'yan'} duvarı ({q['boy']:g} cm pano yerine)"],
                             ["Kaynak", "orijinal üretim çizimi (FrameBuilder); yerleşim motorun kubbesinden"]]})
    # üst bant: düz duvarda kubbenin tabanının üstünde (motorun "Kubbe özel pano 100 × 2500 × 500" yeri)
    fr = FR["KUBBE-DUVAR4"]
    x0, y0, x1, y1 = kb["taban"]
    xm = (x0 + x1) / 2
    z_bant = HZ["bina"]["duvar_h"] - fr["ozet"]["dis_olcu_mm"][1] / 10
    ek.append({"adim": "kubbe_duvar", "sira": 3, "ad": "Kubbe üst bandı · KUBBE-DUVAR-4", "kod": None, "mat": "steel",
               "cubuk": _cerceve_cubuklari(fr, (xm, y0), (xm, y1), z_bant, [1, 0, 0]),
               "satir": [["Bu parça", f"KUBBE-DUVAR-4 · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm"],
                         ["Yer", "düz duvarda kubbenin üstü; üstü duvar üstü kotunda (yer varsayım)"], ["Liste", ls("Kubbe özel pano")],
                         ["Kaynak", "orijinal üretim çizimi (FrameBuilder)"]]})
    # makaslar: biri düz duvar boyunca (KMK14), ikisi tepeden ön köşelere (KMK15, KMK16)
    tx, ty = kb["tepe"]
    z_m = kb["sacak_kotu"] - 2.7
    fr = FR["KMK14"]
    L14 = fr["ozet"]["dis_olcu_mm"][0] / 10
    ek.append({"adim": "makas", "sira": 200, "ad": "Kubbe makası · K-MKS-14", "kod": None, "mat": "truss",
               "cubuk": _cerceve_cubuklari(fr, (tx, ty - L14 / 2), (tx, ty + L14 / 2), z_m, [1, 0, 0]),
               "satir": [["Bu parça", f"K-MKS-14 · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm · {fr['ozet']['cubuk']} çubuk"],
                         ["Yer", "düz duvar boyunca, kubbenin tepesinde ortalı (yer varsayım)"], ["Liste", ls("Kubbe makası")],
                         ["Kaynak", "orijinal üretim çizimi (FrameBuilder)"]]})
    s0, s3 = kb["sacak"][1], kb["sacak"][2]                                     # saçağın iki ön köşesi
    for j, (ad, kose) in enumerate((("KMK15", s0), ("KMK16", s3))):
        fr = FR[ad]
        L = fr["ozet"]["dis_olcu_mm"][0] / 10
        dx, dy = kose[0] - tx, kose[1] - ty
        d = math.hypot(dx, dy)
        ux, uy = dx / d, dy / d
        A = (tx + ux * L, ty + uy * L)                                          # alçak ucu köşeye doğru, yüksek ucu tepede
        ek.append({"adim": "makas", "sira": 201 + j, "ad": f"Kubbe makası · K-MKS-{ad[3:]}", "kod": None, "mat": "truss",
                   "cubuk": _cerceve_cubuklari(fr, A, (tx, ty), z_m, [-uy, ux, 0], merkez=False),
                   "satir": [["Bu parça", f"K-MKS-{ad[3:]} · {fr['ozet']['dis_olcu_mm'][0]:g} × {fr['ozet']['dis_olcu_mm'][1]:g} mm · {fr['ozet']['cubuk']} çubuk"],
                             ["Yer", "tepeden kubbenin ön köşesine (yer varsayım)"], ["Liste", ls("Kubbe makası")],
                             ["Kaynak", "orijinal üretim çizimi (FrameBuilder)"]]})
    # kart modelinden: pencereler ve kubbenin çatısı (OSB + membran + shingle)
    OZ = ifc_ozellik(ifc_yolu, r"^(CATI_KUBBE_\d+_\d+|PENCERE_.*)$")
    pen = {n for n in OZ if n.startswith("PENCERE_") and _kubbede(ifc_yolu, n, kb)}
    U = ifc_ucgen(ifc_yolu, pen | {n for n in OZ if n.startswith("CATI_KUBBE")})
    for n in sorted(pen):
        ek.append({"adim": "kubbe_duvar", "sira": 10, "ad": f"PVC pencere {n.split('_')[1].replace('x', '/')} (kubbe)", "kod": None, "mat": "pvc",
                   "mesh": U[n], "satir": [["Bu parça", n], ["Kaynak", "kart modeli (yer motorun kubbesinden)"]]})
    for n in sorted(x for x in U if x.startswith("CATI_KUBBE")):
        ek.append({"adim": "kaplama", "sira": 400, "ad": "Kubbe çatısı (OSB + membran + shingle)", "kod": None, "mat": "roof", "mesh": U[n],
                   "satir": [["Bu parça", n], ["Liste", f"{ls('Kubbe OSB 11 mm')}; {ls('Kubbe üstü membran')}; {ls('Kubbe antrasit shingle')}"],
                             ["Kaynak", "kart modelinin kubbe çatısı"]]})
    return ek, {n for n in pen}


def _kubbede(ifc_yolu: Path, ad: str, kb: dict) -> bool:
    from .veri import ifc_kutulari
    k = ifc_kutulari(ifc_yolu, "^" + re.escape(ad) + "$").get(ad)
    if not k:
        return False
    xs = [p[0] for p in kb["dis"]]
    ys = [p[1] for p in kb["dis"]]
    return min(xs) - 15 <= (k[0] + k[3]) / 2 <= max(xs) + 15 and min(ys) - 15 <= (k[1] + k[4]) / 2 <= max(ys) + 15
