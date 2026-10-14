"""İE-14 r2 · deterministik yerleşim çözücü: oda programı → plan şeması (LLM yok; aynı program her zaman aynı plan).

Bankadan uyarlama (`plan_uyarlama`) uyan plan vermezse çözücü çalışır. Saf Python; sunucuya yeni paket gerekmez (OR-Tools yok).

Kalıp (dilimleme): kapalı dikdörtgen üç banda bölünür. Önde gündüz bandı (salon, ayrı mutfak, sığmayan yatak odası, köşe veranda), ortada hol
bandı (hol; uçlarda banyo ve depo), arkada gece bandı (yatak odaları, banyo). Hol, kapı isteyen her odanın kenarına en az `OV` cm değer;
hol bandının artan uçları öndeki odalara katılır (L salon, Ç8201 gibi). Kalıp dört yöne kurulur (gündüz bandı güneyde, batıda ya da doğuda;
aynalı) ve şerit veranda bir cephe boyunca dışarıda kalır. Ölçüler 5 cm ızgarada; oda en küçükleri ve 15 cm kuralı ön elemede.

Açıklıklar koddan: kapılar komşuluktan (giriş salona, verandadan ya da güney cepheden; hol her odaya; ayrı mutfak salona), pencereler
işleve göre (salon 120x180 + yan cephede 120x120, yatak odası 120x120, mutfak 120x100, banyo 60x40) mahalin en uzun dış cephesinde.

Her aday `plan_denetim.denetle`'den geçer (geçerliliğe denetçi karar verir). Puan (`puan`, küçük iyi): alan sapması, oda oranları, hol payı,
ıslak hacimlerin yan yana olması, girişin güneyde olması, bayinin verdiği oda alanlarına uzaklık.
"""
from __future__ import annotations

import math
import time

import numpy as np

from beyin.plan_denetim import denetle, kurallar

IZ = 5
OV = 130                    # hol ile kapı isteyen oda arasındaki en kısa ortak kenar (iç kapı 90 + iki yanda birleşim payı)
DIS, IC = 10.5, 5.25        # dış yüzden net yüze (kaplama + karkas + kaplama), iç duvar ekseninden net yüze
H_HOL = 150
BANYO_EN = 190              # gece bandında banyo genişliği (eksenden)
ON_YATAK_EN = 345
DEPO_EN = 150
VERANDA_DERIN = 225         # şerit veranda derinliği (alan verilmezse; Ç8801 225, KT-02 245)
KOSE_VERANDA_EN = 300
HB_EN_COK = 460             # gece bandı derinliği üst sınırı (daha derini dar uzun yatak odası verir)
YATAK_IDEAL = 14.0          # m² net; üstü puanda cezalı (bankada 10,5–16)
PENCERE = {"salon": "120x180", "yatak_odasi": "120x120", "mutfak": "120x100", "banyo": "60x40"}
ISLEV_SIRA = {"salon": 0, "mutfak": 1, "yatak_odasi": 2, "banyo": 3, "hol": 4, "depo": 5, "veranda": 6}


def r5(v: float) -> int:
    return int(round(v / IZ) * IZ)


# ── programın yerleşime hazırlanması ─────────────────────────────────────────────────────────────────────────────────────
def hazirla(program: dict) -> dict:
    """Programdan yerleşim kararları: veranda (konum, örtü, alan), çatı, mutfak. Bu sürümde çizilemeyen bileşim not düşer."""
    notlar: list[str] = []
    v = dict(program.get("veranda") or {})
    tip = program.get("cati_tipi")
    ver = None
    if v.get("istiyor"):
        konum = v.get("konum") or "on"
        ortu = v.get("ortu")
        if konum == "kose" and ortu in ("pergola", "acik"):
            notlar.append("köşe verandada pergola/açık örtü (bu sürümde köşe veranda çatı altında; veranda ön cephede şerit çizildi)")
            konum = "on"
        if ortu is None:
            ortu = "pergola" if (tip == "besik" and konum != "kose") else "cati"
        if ortu == "cati" and tip == "besik":
            notlar.append("çatı altındaki verandayla beşik çatı (beşikte kalkan verandanın açık kenarına oturur; çatı kırma çizildi)")
            tip = "kirma"
        ver = {"konum": konum, "ortu": ortu, "alan_m2": v.get("alan_m2")}
    if tip is None:
        tip = "kirma" if (ver and ver["ortu"] == "cati") else "besik"
    return {"veranda": ver, "cati": tip, "mutfak": program.get("mutfak") or "acik", "notlar": notlar}


def _olculer(program: dict) -> list[tuple[int, int]]:
    """Dış ölçü adayları (en, boy): bayinin verdiği ölçü ya da alanı ±%3 içinde tutan, oranı 1,0–1,6 olan dikdörtgenler."""
    if program.get("dis_olcu_cm"):
        a, b = program["dis_olcu_cm"]
        return [(b, a), (a, b)] if a != b else [(a, b)]
    A = float(program["alan_m2"]) * 1e4
    out = []
    s = r5(math.sqrt(A / 1.6))
    while s <= math.sqrt(A) + 1:
        L = r5(A / s)
        if L >= s and L / s <= 1.6 + 1e-9:
            out += [(L, s), (s, L)] if L != s else [(L, s)]
        s += 10
    return out


# ── kanonik kalıp ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _net(w: float, d: float, u0, u1, v0, v1, U, V, dis_u=(True, True), dis_v=(True, True)) -> tuple[float, float]:
    """Dikdörtgen odanın yaklaşık net eni ve derinliği (kenar dışta mı içte mi)."""
    nu = w - (DIS if (u0 == 0 and dis_u[0]) else IC) - (DIS if (u1 == U and dis_u[1]) else IC)
    nv = d - (DIS if (v0 == 0 and dis_v[0]) else IC) - (DIS if (v1 == V and dis_v[1]) else IC)
    return nu, nv


def _yeter(islev: str, nu: float, nv: float, kural: dict, pay: float = 0.0) -> bool:
    r = kural["odalar"].get(islev) or {}
    return min(nu, nv) >= r.get("dar_kenar_cm", 0) and nu * nv / 1e4 >= r.get("en_az_m2", 0) * (1 + pay)


def _kalip(U: int, V: int, s: dict, kural: dict) -> list[dict] | None:
    """Kanonik çerçevede (u: bant boyunca, v: önden arkaya) mahaller: [{ad, islev, r: [[u0, v0, u1, v1], …]}]. Kurulamazsa None."""
    h, hb = s["h"], s["hb"]
    a = V - h - hb
    if a < 300:
        return None
    # gece bandı: yatak odaları, [ayrı mutfak], banyolar (bir uçta; mutfak banyoya bitişik)
    arka = [("yatak_odasi", None)] * s["yatak_arka"]
    islak = [("mutfak", _mutfak_en(hb, kural))] if (s["mutfak"] == "ayri" and s["mutfak_yeri"] == "arka") else []
    nb = (1 if s["banyo_yeri"] == "arka" else 0) + (1 if s["banyo"] == 2 else 0)
    islak += [("banyo", BANYO_EN)] * nb
    arka = arka + islak if s["banyo_ucu"] == "son" else islak[::-1] + arka
    ny = s["yatak_arka"]
    kalan = U - sum(w_ for _, w_ in islak)
    w = r5(kalan / ny) if ny else 0
    if ny and w < 315:
        return None
    enler = [w_ if w_ else w for _, w_ in arka]
    if ny:                                                     # son yatak odası artanı alır
        son = max(i for i, (islev, _) in enumerate(arka) if islev == "yatak_odasi")
        enler[son] += U - sum(enler)
    elif enler:
        enler[-1] += U - sum(enler)
    odalar: list[dict] = []
    u = 0
    for (islev, _), w_ in zip(arka, enler):
        odalar.append({"islev": islev, "bant": "arka", "r": [[u, V - hb, u + w_, V]]})
        u += w_
    # gündüz bandı: [köşe veranda] salon [mutfak] [yatak odaları]
    on: list[tuple[str, int | None]] = []
    if s["kose"]:
        on.append(("veranda", s["kose"]))
    on.append(("salon", None))
    if s["mutfak"] == "ayri" and s["mutfak_yeri"] == "on":
        on.append(("mutfak", _mutfak_en(a, kural)))
    on += [("yatak_odasi", ON_YATAK_EN)] * s["yatak_on"]
    sabit = sum(w_ for _, w_ in on if w_)
    ws = U - sabit
    if ws < 330:
        return None
    u = 0
    for islev, w_ in on:
        u1 = u + (w_ if w_ else ws)
        odalar.append({"islev": islev, "bant": "on", "r": [[u, 0, u1, a]]})
        u = u1
    # hol bandı
    e0 = DEPO_EN if s["depo"] else 0
    e1 = s["banyo_orta_en"] if s["banyo_yeri"] == "orta" else 0
    gerek = [o for o in odalar if o["islev"] in ("yatak_odasi", "banyo", "salon") or (o["islev"] == "mutfak" and o["bant"] == "arka")]
    lo = min(o["r"][0][2] - OV for o in gerek)
    hi = max(o["r"][0][0] + OV for o in gerek)
    if lo > hi:
        orta = (lo + hi) / 2
        lo, hi = r5(orta - OV), r5(orta + OV)
    hx0 = min(lo, U - e1)
    hx1 = max(hi, e0)
    if e0:
        hx0 = e0
    if e1:
        hx1 = U - e1
    hx0, hx1 = max(hx0, e0), min(hx1, U - e1)
    # yakın çizgiye yaslan (15 cm kuralı): hol uçları öndeki/arkadaki sınırlara 25 cm'den yakınsa
    sinirlar = sorted({x for o in odalar for x in (o["r"][0][0], o["r"][0][2])})
    for i, hx in enumerate((hx0, hx1)):
        yakin = [x for x in sinirlar if 0 < abs(x - hx) <= 25]
        if yakin:
            x = min(yakin, key=lambda t: abs(t - hx))
            if i == 0 and not e0:
                hx0 = min(hx0, x)
            elif i == 1 and not e1:
                hx1 = max(hx1, x)
    if hx0 < 100 and not e0:
        hx0 = 0
    if U - e1 - hx1 < 100 and not e1:
        hx1 = U
    if hx1 - hx0 < OV:
        return None
    for o in gerek:                                           # her oda hole OV kadar değmeli
        u0, _, u1, _ = o["r"][0]
        if min(u1, hx1) - max(u0, hx0) < OV:
            return None
    vm0, vm1 = a, a + h
    # artan uçlar (hol bandında holün iki yanı): öndeki odalara katılır, holden dışarı doğru. Hole bitişik 1 m'den dar parçayı hol alır;
    # verandanın üstündeki parça arkadaki odaya (komşu ön odaya dar boğazla bağlanmasın), o örtmüyorsa öndeki komşuya.
    ondekiler = [o for o in odalar if o["bant"] == "on"]
    arkadakiler = [o for o in odalar if o["bant"] == "arka"]
    ekler: list[tuple[dict, list[int]]] = []
    for taraf in ("sol", "sag"):
        p0, p1 = (e0, hx0) if taraf == "sol" else (hx1, U - e1)
        if p1 - p0 <= 0:
            continue
        parcalar = []
        for o in ondekiler:
            u0, _, u1, _ = o["r"][0]
            q0, q1 = max(p0, u0), min(p1, u1)
            if q1 - q0 > 0:
                parcalar.append((q0, q1, o))
        parcalar.sort(key=lambda t: -t[1] if taraf == "sol" else t[0])
        for q0, q1, o in parcalar:
            bitisik = (q1 == hx0) if taraf == "sol" else (q0 == hx1)
            if q1 - q0 < 100 and bitisik:
                if taraf == "sol":
                    hx0 = q0
                else:
                    hx1 = q1
                continue
            if q1 - q0 < 100:
                return None
            sahip = o
            if o["islev"] == "veranda":
                ust = [x for x in arkadakiler if x["r"][0][0] <= q0 and x["r"][0][2] >= q1]
                sahip = ust[0] if ust else next((x for x in ondekiler if x["islev"] != "veranda" and x["r"][0][0] == o["r"][0][2]), None)
                if sahip is None:
                    return None
            ekler.append((sahip, [q0, vm0, q1, vm1]))
    for sahip, r in ekler:
        sahip["r"].append(r)
    odalar.append({"islev": "hol", "bant": "orta", "r": [[hx0, vm0, hx1, vm1]]})
    if e0:
        odalar.append({"islev": "depo", "bant": "orta", "r": [[0, vm0, e0, vm1]]})
    if e1:
        odalar.append({"islev": "banyo", "bant": "orta", "r": [[U - e1, vm0, U, vm1]]})
    # oda en küçükleri: dar kenar ana dikdörtgenle, alan bütün parçalarla (yaklaşık; denetçi kesin karar verir)
    for o in odalar:
        if o["islev"] in ("veranda", "hol"):
            continue
        u0, v0, u1, v1 = o["r"][0]
        nu, nv = _net(u1 - u0, v1 - v0, u0, u1, v0, v1, U, V)
        ek = sum((r[2] - r[0]) * (r[3] - r[1]) for r in o["r"][1:]) * 0.9 / 1e4
        r = kural["odalar"].get(o["islev"]) or {}
        if min(nu, nv) < r.get("dar_kenar_cm", 0) or nu * nv / 1e4 + ek < r.get("en_az_m2", 0) * 1.02:
            return None
    # 15 cm kuralı: farklı iki çizgi en az 20 cm aralıklı
    for k in (0, 1):
        cz = sorted({x for o in odalar for r in o["r"] for x in (r[k], r[k + 2])})
        if any(0 < b - a_ <= 15 for a_, b in zip(cz, cz[1:])):
            return None
    return odalar


def _mutfak_en(derinlik: int, kural: dict) -> int:
    """Ayrı mutfağın bant boyunca eni: en az alanı ve dar kenarı tutan en küçük 5 cm katı (bir yanı dış duvar sayılır)."""
    for w in range(265, 500, 5):
        if _yeter("mutfak", w - IC - IC, derinlik - DIS - IC, kural, pay=0.03):
            return w
    return 500


def _banyo_orta_en(h: int, kural: dict) -> int:
    for w in range(185, 400, 5):
        if _yeter("banyo", w - DIS - IC, h - 2 * IC, kural, pay=0.02):
            return w
    return 400


# ── kanonikten plana ─────────────────────────────────────────────────────────────────────────────────────────────────────
def _donustur(r, yon: str, ayna: bool, U: int, V: int, ox: int, oy: int) -> list[int]:
    u0, v0, u1, v1 = r
    if ayna:
        u0, u1 = U - u1, U - u0
    if yon == "G":
        x0, y0, x1, y1 = u0, v0, u1, v1
    elif yon == "B":
        x0, y0, x1, y1 = v0, u0, v1, u1
    else:                                                    # "D": gündüz bandı doğuda
        x0, y0, x1, y1 = V - v1, u0, V - v0, u1
    return [int(x0 + ox), int(y0 + oy), int(x1 + ox), int(y1 + oy)]


def adlandir(odalar: list[dict], mutfak: str) -> None:
    """Bayiye görünen adlar (tekil, Türkçe)."""
    yat = [o for o in odalar if o["islev"] == "yatak_odasi"]
    ban = [o for o in odalar if o["islev"] == "banyo"]
    for o in odalar:
        if o["islev"] == "salon":
            o["ad"] = "Salon - Mutfak" if mutfak == "acik" else "Salon"
        elif o["islev"] == "yatak_odasi":
            o["ad"] = f"Yatak Odası {yat.index(o) + 1}"
        elif o["islev"] == "banyo":
            o["ad"] = "Banyo" if len(ban) == 1 else f"Banyo {ban.index(o) + 1}"
        else:
            o["ad"] = {"mutfak": "Mutfak", "hol": "Hol", "depo": "Depo", "veranda": "Veranda"}[o["islev"]]


def izgara(mahaller: list[dict], W: int, H: int):
    """5 cm hücre etiketleri: mahal sırası, veranda −2, boş −1."""
    lab = np.full((W // IZ, H // IZ), -1, dtype=int)
    for i, m in enumerate(mahaller):
        for x0, y0, x1, y1 in m["dikdortgenler"]:
            lab[x0 // IZ:x1 // IZ, y0 // IZ:y1 // IZ] = -2 if m["islev"] == "veranda" else i
    return lab


def cepheler(mahaller: list[dict], W: int, H: int) -> dict[str, dict[str, int]]:
    """Mahal → cephe → en uzun dış (ya da verandaya bakan) koşu, cm. Veranda yüzü ayrıca 'veranda' anahtarında."""
    lab = izgara(mahaller, W, H)
    nx, ny = lab.shape
    out: dict[str, dict[str, int]] = {}
    for i, m in enumerate(mahaller):
        if m["islev"] == "veranda":
            continue
        d: dict[str, int] = {}
        ver = 0
        for ce, (dx, dy) in {"G": (0, -1), "K": (0, 1), "B": (-1, 0), "D": (1, 0)}.items():
            en_uzun, kosu = 0, 0
            maske = lab == i
            komsu = np.full_like(lab, -1)
            if dx == 0:
                if dy == -1:
                    komsu[:, 1:] = lab[:, :-1]
                else:
                    komsu[:, :-1] = lab[:, 1:]
            else:
                if dx == -1:
                    komsu[1:, :] = lab[:-1, :]
                else:
                    komsu[:-1, :] = lab[1:, :]
            sinir = maske & (komsu < 0)
            ver += int((maske & (komsu == -2)).sum()) * IZ
            # koşu: sınır hücreleri cephe boyunca ardışık
            dizi = sinir.any(axis=1 if dx == 0 else 0)
            for b in dizi:
                kosu = kosu + 1 if b else 0
                en_uzun = max(en_uzun, kosu)
            if en_uzun:
                d[ce] = en_uzun * IZ
        out[m["ad"]] = d
        if ver:
            out[m["ad"]]["veranda"] = ver
    return out


def acikliklar(mahaller: list[dict], W: int, H: int, komsular: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Kapı ve pencere listeleri (plan şeması biçiminde). `komsular`: iç kapı isteyen mahal çiftleri."""
    ce = cepheler(mahaller, W, H)
    ver = next((m["ad"] for m in mahaller if m["islev"] == "veranda"), None)
    salon = next(m["ad"] for m in mahaller if m["islev"] == "salon")
    kapilar = []
    if ver and ce[salon].get("veranda", 0) >= 150:
        kapilar.append({"arasinda": [ver, salon]})
    elif ce[salon].get("G", 0) >= 200:
        kapilar.append({"arasinda": ["dis", salon], "cephe": "G"})
    else:
        kapilar.append({"arasinda": ["dis", salon]})
    kapilar += [{"arasinda": [a, b]} for a, b in komsular]
    pencereler = []
    for m in mahaller:
        olcu = PENCERE.get(m["islev"])
        if not olcu or not ce.get(m["ad"]):
            continue
        sira = sorted(((L, c) for c, L in ce[m["ad"]].items() if c != "veranda"), key=lambda t: (-t[0], "GKBD".index(t[1])))
        if m["islev"] == "salon":                              # salonun büyük penceresi önde (güney), sığıyorsa
            sira.sort(key=lambda t: (not (t[1] == "G" and t[0] >= 300), -t[0], "GKBD".index(t[1])))
        if not sira:
            continue
        L, c = sira[0]
        pencereler.append({"mahal": m["ad"], "cephe": c, "olcu": olcu, "adet": 1})
        if m["islev"] == "salon" and len(sira) > 1 and sira[1][0] >= 250:
            pencereler.append({"mahal": m["ad"], "cephe": sira[1][1], "olcu": "120x120", "adet": 1})
    return kapilar, pencereler


def _plan(odalar: list[dict], yon: str, ayna: bool, U: int, V: int, W: int, H: int, ver: dict | None, serit: tuple | None,
          hz: dict, program: dict) -> dict:
    ox = oy = 0
    if serit:
        ce, d = serit
        ox, oy = (d, 0) if ce == "B" else (0, 0)
        oy = d if ce == "G" else oy
    mahaller = []
    for o in odalar:
        m = {"islev": o["islev"], "dikdortgenler": [_donustur(r, yon, ayna, U, V, ox, oy) for r in o["r"]]}
        if o["islev"] == "veranda":
            m["ortu"] = ver["ortu"]
        mahaller.append(m)
    if serit:
        ce, d = serit
        r = {"G": [0, 0, W, d], "K": [0, H - d, W, H], "B": [0, 0, d, H], "D": [W - d, 0, W, H]}[ce]
        mahaller.append({"islev": "veranda", "dikdortgenler": [r], "ortu": ver["ortu"]})
    adlandir(mahaller, hz["mutfak"])
    mahaller.sort(key=lambda m: (ISLEV_SIRA[m["islev"]], m["ad"]))
    hol = next(m["ad"] for m in mahaller if m["islev"] == "hol")
    salon = next(m["ad"] for m in mahaller if m["islev"] == "salon")
    komsu = [(salon, hol)]
    for m in mahaller:
        if m["islev"] in ("yatak_odasi", "banyo", "depo"):
            komsu.append((hol, m["ad"]))
        elif m["islev"] == "mutfak":
            komsu.append((salon, m["ad"]))
    kapilar, pencereler = acikliklar(mahaller, W, H, komsu)
    p = {"dis_olcu": {"en": W, "boy": H}, "mahaller": [{k: v for k, v in m.items()} for m in mahaller], "kapilar": kapilar,
         "pencereler": pencereler, "cati": {"tip": hz["cati"]}, "gerekce": f"çözücü: gündüz bandı {yon}{' aynalı' if ayna else ''}"}
    if program.get("egim_yuzde"):
        p["cati"]["egim_yuzde"] = program["egim_yuzde"]
    if program.get("dis_karkas") == 140:
        p["dis_karkas"] = 140
    return p


# ── puan ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def puan(plan: dict, ozet: dict, program: dict) -> float:
    """Küçük iyi. Denetçinin özetindeki net alanlarla."""
    W, H = plan["dis_olcu"]["en"], plan["dis_olcu"]["boy"]
    brut = W * H / 1e4
    p = 0.0
    if program.get("alan_m2"):
        p += 2.0 * abs(brut - program["alan_m2"]) / program["alan_m2"] * 100
    alan = ozet.get("odalar_m2") or {}
    islev = {m["ad"]: m["islev"] for m in plan["mahaller"]}
    kapali = sum(alan.values()) or 1
    p += 40 * sum(v for k, v in alan.items() if islev.get(k) == "hol") / kapali     # hol payı
    for m in plan["mahaller"]:
        if m["islev"] in ("veranda", "hol"):
            continue
        r = max(m["dikdortgenler"], key=lambda t: (t[2] - t[0]) * (t[3] - t[1]))
        oran = max(r[2] - r[0], r[3] - r[1]) / max(1, min(r[2] - r[0], r[3] - r[1]))
        p += 3 * max(0.0, oran - 1.6)
        p += 0.6 * max(0, len(m["dikdortgenler"]) - 1)
        if m["islev"] == "banyo":
            p += 0.8 * max(0.0, alan.get(m["ad"], 0) - 6)
    yat = [alan[k] for k, i in islev.items() if i == "yatak_odasi" and k in alan]
    if len(yat) > 1:
        p += 0.5 * (max(yat) - min(yat))
    p += 0.4 * sum(max(0.0, a - YATAK_IDEAL - 2) for a in yat)
    for h in program.get("oda_hedefleri") or []:
        ad = [k for k, i in islev.items() if i == h["islev"] and k in alan]
        if ad:
            p += 1.5 * min(abs(alan[k] - h["m2"]) for k in ad)
    giris = plan["kapilar"][0]
    if "dis" in giris["arasinda"] and giris.get("cephe") != "G":
        p += 3
    if not _islak_bitisik(plan):
        p += 2
    return round(p, 3)


def _islak_bitisik(plan: dict) -> bool:
    """Banyo mutfakla (ya da açık mutfaklı salonla) duvar paylaşıyor mu."""
    def kenar(a, b):
        for r in a["dikdortgenler"]:
            for q in b["dikdortgenler"]:
                if (r[2] == q[0] or q[2] == r[0]) and min(r[3], q[3]) - max(r[1], q[1]) >= 100:
                    return True
                if (r[3] == q[1] or q[3] == r[1]) and min(r[2], q[2]) - max(r[0], q[0]) >= 100:
                    return True
        return False
    ms = plan["mahaller"]
    mut = [m for m in ms if m["islev"] == "mutfak"] or [m for m in ms if m["islev"] == "salon"]
    return any(kenar(b, m) for b in ms if b["islev"] == "banyo" for m in mut)


# ── çözüm ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _secenekler(program: dict, hz: dict, kural: dict):
    n = int(program["yatak"])
    banyo = int(program.get("banyo") or 1)
    for yatak_on in range(0, min(n, 2) + 1):
        for mutfak_yeri in (("on", "arka") if hz["mutfak"] == "ayri" else ("on",)):
            for banyo_yeri in ("orta", "arka"):
                for banyo_ucu in ("son", "bas"):
                    if banyo_yeri == "orta" and banyo == 1 and banyo_ucu == "bas" and mutfak_yeri == "on":
                        continue
                    h = H_HOL if banyo_yeri == "arka" else 210
                    yield {"yatak_arka": n - yatak_on, "yatak_on": yatak_on, "banyo_yeri": banyo_yeri, "banyo_ucu": banyo_ucu, "h": h,
                           "banyo": banyo, "mutfak": hz["mutfak"], "mutfak_yeri": mutfak_yeri, "depo": int(program.get("depo") or 0),
                           "banyo_orta_en": _banyo_orta_en(h, kural)}


def _kaba_puan(odalar: list[dict], W: int, H: int, program: dict, yon: str) -> float:
    """Kanonik çerçevede, plan kurmadan yaklaşık puan (eksenden alanlar × 0,93): denetlenecek sırayı belirler."""
    p = 0.0
    if program.get("alan_m2"):
        p += 2.0 * abs(W * H / 1e4 - program["alan_m2"]) / program["alan_m2"] * 100
    alan = [(o, sum((r[2] - r[0]) * (r[3] - r[1]) for r in o["r"]) / 1e4 * 0.93) for o in odalar if o["islev"] != "veranda"]
    kapali = sum(a for _, a in alan) or 1
    p += 40 * sum(a for o, a in alan if o["islev"] == "hol") / kapali
    yat = []
    for o, a in alan:
        if o["islev"] == "hol":
            continue
        r = o["r"][0]
        p += 3 * max(0.0, max(r[2] - r[0], r[3] - r[1]) / max(1, min(r[2] - r[0], r[3] - r[1])) - 1.6)
        p += 0.6 * (len(o["r"]) - 1)
        if o["islev"] == "banyo":
            p += 0.8 * max(0.0, a - 6)
        if o["islev"] == "yatak_odasi":
            yat.append(a)
    if len(yat) > 1:
        p += 0.5 * (max(yat) - min(yat))
    p += 0.4 * sum(max(0.0, a - YATAK_IDEAL - 2) for a in yat)
    for h in program.get("oda_hedefleri") or []:
        aa = [a for o, a in alan if o["islev"] == h["islev"]]
        if aa:
            p += 1.5 * min(abs(a - h["m2"]) for a in aa)
    if yon != "G":
        p += 1.5                                               # giriş güneyde olmayabilir (kesin puan açıklıklarla)
    return round(p, 3)


def adaylar(program: dict, kural: dict | None = None) -> list[dict]:
    """Ön elemeden geçen kalıplar, kaba puanla sıralı (plan kurulmamış; `kur` ile kurulur). Belirlenimci."""
    kural = kural or kurallar()
    hz = hazirla(program)
    ver = hz["veranda"]
    out = []
    for W, H in _olculer(program):
        if max(W, H) / min(W, H) > 1.6 + 1e-9:
            continue
        serit = None
        cW, cH = W, H
        if ver and ver["konum"] != "kose":
            ce = {"on": "G", "arka": "K", "yan": "D"}[ver["konum"]]
            L = W if ce in ("G", "K") else H
            d = r5(min(300, max(150, (ver["alan_m2"] * 1e4 / L) if ver.get("alan_m2") else VERANDA_DERIN)))
            serit = (ce, d)
            if ce in ("G", "K"):
                cH = H - d
            else:
                cW = W - d
        for yon in ("G", "B", "D"):
            U, V = (cW, cH) if yon == "G" else (cH, cW)
            for s in _secenekler(program, hz, kural):
                a_min = 345 if (s["mutfak"] == "ayri" and s["mutfak_yeri"] == "on") else 320
                for hb in range(320, min(V - s["h"] - a_min, HB_EN_COK) + 1, 20):
                    kose = 0
                    if ver and ver["konum"] == "kose":
                        a = V - s["h"] - hb
                        kose = r5(min(450, max(200, (ver["alan_m2"] * 1e4 / a) if ver.get("alan_m2") else KOSE_VERANDA_EN)))
                    odalar = _kalip(U, V, {**s, "hb": hb, "kose": kose}, kural)
                    if odalar is None:
                        continue
                    kalip = {"yon": yon, "hb": hb, **{k: s[k] for k in ("yatak_on", "banyo_yeri", "banyo_ucu", "h", "mutfak_yeri")}}
                    on = _kaba_puan(odalar, W, H, program, yon)
                    for ayna in (False, True):
                        out.append({"on_puan": on, "W": W, "H": H, "U": U, "V": V, "odalar": odalar, "serit": serit, "ayna": ayna,
                                    "kalip": {**kalip, "ayna": ayna}})
    out.sort(key=lambda a: (a["on_puan"], a["W"], a["H"], str(a["kalip"])))
    return out


def kur(a: dict, program: dict) -> dict:
    """`adaylar`'ın bir girdisinden plan şeması."""
    hz = hazirla(program)
    return _plan(a["odalar"], a["kalip"]["yon"], a["ayna"], a["U"], a["V"], a["W"], a["H"], hz["veranda"], a["serit"], hz, program)


def topoloji(kalip: dict) -> tuple:
    """Aynası, dönüğü ve ölçüsü ayrı sayılmayan yerleşim imzası: iki seçenek birbirinin aynası ya da 90° dönüğü olmasın."""
    return tuple(kalip.get(k) for k in ("yatak_on", "banyo_yeri", "banyo_ucu", "mutfak_yeri"))


def coz(program: dict, n: int = 2, kural: dict | None = None, en_cok_denetim: int = 60, kod: str = "YENI") -> dict:
    """Program → denetçiden geçen, yerleşimi birbirinden farklı en iyi n plan. Dönüş: {adaylar: [{plan, tanim, ozet, puan, kalip, yol}],
    denetim, sure_ms, notlar, ihlaller}. İstisna fırlatmaz; hiçbir aday geçmezse `adaylar` boş, `ihlaller` son denetimin ihlalleri."""
    t0 = time.time()
    kural = kural or kurallar()
    hz = hazirla(program)
    talep = {"oda_programi": f"{program['yatak']}+{program.get('salon', 1)}", "alan_m2": program.get("alan_m2")}
    gecen, denetim, son_ihlal = [], 0, []
    gorulen = set()
    try:
        liste = adaylar(program, kural)
    except (KeyError, ValueError, TypeError) as e:
        return {"adaylar": [], "denetim": 0, "sure_ms": int((time.time() - t0) * 1000), "notlar": hz["notlar"],
                "ihlaller": [f"program: {type(e).__name__}: {e}"]}
    for a in liste:
        if denetim >= en_cok_denetim or len(gecen) >= n:
            break
        if topoloji(a["kalip"]) in gorulen:
            continue
        denetim += 1
        plan = kur(a, program)
        d = denetle(plan, talep, kural, kod=kod)
        if not d["gecerli"]:
            son_ihlal = d["ihlaller"]
            continue
        gorulen.add(topoloji(a["kalip"]))
        gecen.append({"plan": plan, "tanim": d["tanim"], "ozet": d["ozet"], "puan": puan(plan, d["ozet"], program),
                      "kalip": a["kalip"], "yol": "cozucu"})
    gecen.sort(key=lambda g: g["puan"])
    return {"adaylar": gecen, "denetim": denetim, "sure_ms": int((time.time() - t0) * 1000), "notlar": hz["notlar"],
            "ihlaller": [] if gecen else son_ihlal[:8]}
