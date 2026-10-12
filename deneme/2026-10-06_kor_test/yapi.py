#!/usr/bin/env python3
"""Genel yapı geometrisi: karkas kutularından (duvar panelleri) mahaller, kaplanan yüzler ve metraj.

Yapı Tanımı 0.5 taslağını okur. 0.4'ten farkı: kapalı kısım dikdörtgen olmak zorunda değildir. Duvarlar, modeldeki
(SKP / DWG) karkas panellerinin plandaki kutularıdır; mahaller bu kutuların çevrelediği bölgelerdir ve koddan çıkar.
Her açık karkas yüzü, baktığı bölgeye göre kaplanır (dışa ve verandaya bakan yüz dış kaplama, odaya bakan yüz iç kaplama).
Kaplama kalınlıkları tanımdaki `yuz_kaplamalari` tablosundandır; mahal ölçüleri kaplanmış yüzler arasındadır
(0.4'teki "duvar kalınlığı katmanların toplamıdır" kuralının aynısı).

Hesapta LLM yoktur: aynı tanım aynı sonucu verir. Bütün ölçüler cm; alanlar ayrıca m² olarak raporlanır.
Yalnız eksenlere paralel duvarlar.

Kullanım:
    python yapi.py tanim.json [--rapor rapor.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

KAPAT = 0.02      # cm; birbirine değen kutuların arasındaki kıl payı aralıkları kapatmak için
TOL = 1e-3
KENARLAR = ("alt", "sag", "ust", "sol")          # kutunun dört kenarı; dış normalleri (0,-1), (1,0), (0,1), (-1,0)
NORMAL = {"alt": (0.0, -1.0), "sag": (1.0, 0.0), "ust": (0.0, 1.0), "sol": (-1.0, 0.0)}
# Açık alanın örtüsü (mahalin `ortu` alanı; Ç8801, 10 Ekim 2026): "cati" çatının altında (alan yazılmamışsa da öyle: eski tanımlar);
# "pergola" ya da "acik" çatısız. Çatısız alanın tavanı yoktur: tavan, tavan paneli, köşebent ve tavan omegası onu saymaz.
ORTULER = ("cati", "pergola", "acik")
ORTU_ADI = {"cati": "çatının altında", "pergola": "pergola", "acik": "üstü açık"}


def catisiz(m: dict) -> bool:
    """Mahal (ya da bölge) çatısız bir açık alan mı (tanımda `ortu: pergola | acik`)."""
    return m.get("ortu") in ("pergola", "acik")


def _kenar(kutu, ad):
    """Kutunun bir kenarı: (eksen, sabit koordinat, bas, son). eksen 'x' ise kenar x boyunca uzanır."""
    x0, y0, x1, y1 = kutu
    return {"alt": ("x", y0, x0, x1), "ust": ("x", y1, x0, x1), "sol": ("y", x0, y0, y1), "sag": ("y", x1, y0, y1)}[ad]


def _halkalar(g):
    if g.is_empty:
        return
    for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
        yield list(p.exterior.coords)
        for h in p.interiors:
            yield list(h.coords)


def _sade(halka):
    """Halkadan doğrusal ara noktaları ve üst üste noktaları atar (kapalı halka; son nokta ilk noktanın tekrarı değildir)."""
    pts = [q for i, q in enumerate(halka[:-1]) if abs(q[0] - halka[i - 1 if i else -2][0]) > TOL or abs(q[1] - halka[i - 1 if i else -2][1]) > TOL]
    n = len(pts)
    return [q for i, q in enumerate(pts)
            if abs((q[0] - pts[i - 1][0]) * (pts[(i + 1) % n][1] - q[1]) - (q[1] - pts[i - 1][1]) * (pts[(i + 1) % n][0] - q[0])) > TOL]


def _parcalar(g):
    """Çokgenin kenar parçaları (doğrusal ara noktalar birleştirilmiş)."""
    for h in _halkalar(g):
        pts = _sade(h)
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            yield ax, ay, bx, by


def _kose_say(p: Polygon) -> tuple[int, int]:
    """İç ve dış köşe sayısı. İç köşe: odanın içinden bakınca 90°'lik köşe. Dış köşe: odaya doğru çıkıntı (270°)."""
    ic = dis = 0

    def say(coords, delik: bool):
        nonlocal ic, dis
        pts = list(coords)[:-1]
        n = len(pts)
        temiz = []
        for i, q in enumerate(pts):
            a, b = pts[i - 1], pts[(i + 1) % n]
            if abs((q[0] - a[0]) * (b[1] - q[1]) - (q[1] - a[1]) * (b[0] - q[0])) > TOL:
                temiz.append(q)
        m = len(temiz)
        alan2 = sum(temiz[i][0] * temiz[(i + 1) % m][1] - temiz[(i + 1) % m][0] * temiz[i][1] for i in range(m))
        yon = 1.0 if alan2 > 0 else -1.0
        for i, q in enumerate(temiz):
            a, b = temiz[i - 1], temiz[(i + 1) % m]
            sol_donus = ((q[0] - a[0]) * (b[1] - q[1]) - (q[1] - a[1]) * (b[0] - q[0])) * yon > 0
            # dış halka: sola dönüş iç köşe. Delik (odanın içindeki kütle): kendi yönünde sola dönüş, odadan bakınca çıkıntıdır.
            if sol_donus != delik:
                ic += 1
            else:
                dis += 1

    say(p.exterior.coords, False)
    for h in p.interiors:
        say(h.coords, True)
    return ic, dis


def _yukseklik(d: dict, s: float | None = None) -> float:
    """Duvarın s konumundaki (uzun ekseni boyunca) üst kotu. Sabit ya da iki uç arasında doğrusal."""
    y = d["yukseklik"]
    if not isinstance(y, dict):
        return float(y)
    a, b = d["_bas"], d["_son"]
    if s is None:
        return (y["bas"] + y["son"]) / 2
    t = min(1.0, max(0.0, (s - a) / (b - a)))
    return y["bas"] + (y["son"] - y["bas"]) * t


def _alan_altinda(d: dict, a: float, b: float, yuk: float | None = None) -> float:
    """Duvarın [a, b] aralığında (uzun eksen boyunca) yüz alanı: üst kot boyunca integral. `yuk` verilirse sabit yükseklik."""
    if yuk is not None:
        return (b - a) * yuk
    y = d["yukseklik"]
    if not isinstance(y, dict):
        return (b - a) * float(y)
    return (b - a) * (_yukseklik(d, a) + _yukseklik(d, b)) / 2      # doğrusal üst kot: yamuk; uçların dışı uç kotuyla


def kur(tanim: dict) -> dict:
    """Tanımdan geometri ve metraj. Dönen sözlükte shapely nesneleri de vardır (çizim için); `rapor()` yalın halini verir."""
    kap = tanim["yuz_kaplamalari"]
    sinif = tanim["duvar_siniflari"]
    duvarlar = []
    for d in tanim["duvarlar"]:
        x0, y0, x1, y1 = d["kutu"]
        yon = "x" if (x1 - x0) >= (y1 - y0) else "y"
        e = dict(d, yon=yon, _bas=(x0 if yon == "x" else y0), _son=(x1 if yon == "x" else y1),
                 boy=max(x1 - x0, y1 - y0), kalinlik=min(x1 - x0, y1 - y0), geo=box(x0, y0, x1, y1))
        if e["sinif"] not in sinif:
            raise SystemExit(f"Bilinmeyen duvar sınıfı: {e['sinif']} ({e['ad']})")
        duvarlar.append(e)
    adli = {d["ad"]: d for d in duvarlar}
    if len(adli) != len(duvarlar):
        raise SystemExit("Duvar adları tekil değil.")

    # ── bölgeler: kutuların çevrelediği boşluklar ────────────────────────────
    kutle = unary_union([d["geo"].buffer(KAPAT, join_style=2) for d in duvarlar])
    x0, y0, x1, y1 = kutle.bounds
    cerceve = box(x0 - 500, y0 - 500, x1 + 500, y1 + 500)
    bos = cerceve.difference(kutle)
    ham = [p.buffer(KAPAT, join_style=2) for p in (bos.geoms if bos.geom_type == "MultiPolygon" else [bos])]
    uzak = Point(x0 - 400, y0 - 400)
    dis_ham = next(p for p in ham if p.contains(uzak))
    bolgeler: dict[str, dict] = {}
    for m in tanim["mahaller"]:
        if "ortu" in m and (m["ortu"] not in ORTULER or m["sinif"] != "veranda"):
            raise SystemExit(f"Mahalin örtüsü ({m['ad']}): `ortu` yalnız verandada ve {', '.join(ORTULER)} olabilir; tanımda {m['ortu']}.")
        if m.get("poligon"):        # duvarla çevrili olmayan açık alan (ör. dikmeli açık veranda): dış bölgeden ayrılır
            g = Polygon(m["poligon"]).difference(kutle)
            dis_ham = dis_ham.difference(g)
        else:
            nokta = Point(*m["nokta"])
            aday = [p for p in ham if p.contains(nokta)]
            if len(aday) != 1 or aday[0] is dis_ham:
                raise SystemExit(f"Mahal duvarlarla çevrili değil ya da noktası bir bölgenin içinde değil: {m['ad']}")
            g = aday[0]
        if any(g.equals(b["ham"]) for b in bolgeler.values()):
            raise SystemExit(f"İki mahal aynı bölgeyi gösteriyor: {m['ad']}")
        bolgeler[m["ad"]] = dict(m, ham=g)
    adsiz = [p for p in ham if p is not dis_ham and p.area > 400 and not any(p.equals(b["ham"]) for b in bolgeler.values())
             and not any(p.intersects(Polygon(m["poligon"])) for m in tanim["mahaller"] if m.get("poligon"))]
    if adsiz:
        raise SystemExit("Adı verilmemiş kapalı bölge var: " + "; ".join(f"{p.representative_point().x:.0f},{p.representative_point().y:.0f} ({p.area / 1e4:.2f} m²)" for p in adsiz))
    bolgeler["(dış)"] = {"ad": "(dış)", "sinif": "dis", "ham": dis_ham}

    # ── kaplama şeritleri ve kaplanmış (net) bölgeler ────────────────────────
    def kaplama_adi(d, b):
        return sinif[d["sinif"]]["yuz"].get(b["sinif"])

    for b in bolgeler.values():
        seritler = []
        for d in duvarlar:
            ka = kaplama_adi(d, b)
            if ka is None:
                continue
            t = kap[ka]["kalinlik"]
            for kn in KENARLAR:
                eks, c, a0, a1 = _kenar(d["kutu"], kn)
                cizgi = LineString([(a0, c), (a1, c)] if eks == "x" else [(c, a0), (c, a1)])
                s = cizgi.buffer(t, cap_style=3, join_style=2).intersection(b["ham"])
                if s.area > 1e-6:
                    seritler.append(s)
                    d.setdefault("_serit", []).append(s)
        b["net"] = b["ham"].difference(unary_union(seritler)).buffer(0) if seritler else b["ham"]

    # ── yüzler: her duvar kenarının, her bölgede kaplanmış yüzü ──────────────
    # Kaplanmış bölgenin her kenar parçası, arkasındaki duvar kenarına yazılır. Önce duvarın kendi boyu kadarı; duvarın ucundan
    # taşan köşe payı (çıkıntı köşede kaplama kalınlığı kadar) o uca komşu duvar kenarına eklenir.
    yuzler = []
    for b in bolgeler.values():
        adaylar = []
        for d in duvarlar:
            ka = kaplama_adi(d, b)
            if ka is None:
                continue
            t = kap[ka]["kalinlik"]
            for kn in KENARLAR:
                eks, c, a0, a1 = _kenar(d["kutu"], kn)
                n = NORMAL[kn]
                adaylar.append((d, kn, eks, c + t * (n[1] if eks == "x" else n[0]), a0, a1, t, ka))
        toplanan: dict[tuple, list] = {}
        acikta = 0.0
        for ax, ay, bx, by in _parcalar(b["net"]):
            eks = "x" if abs(ay - by) < TOL else "y"
            sabit, lo, hi = (ay, min(ax, bx), max(ax, bx)) if eks == "x" else (ax, min(ay, by), max(ay, by))
            uygun = [a for a in adaylar if a[2] == eks and abs(a[3] - sabit) < TOL and min(hi, a[5]) - max(lo, a[4]) > -a[6] - TOL]
            # yüz gerçekten bu bölgeye bakıyor olmalı: duvar kenarından bölgeye doğru küçük bir adım bölgenin içinde
            ortusen = []
            for a in uygun:
                i0, i1 = max(lo, a[4]), min(hi, a[5])
                if i1 - i0 > TOL:
                    ortusen.append([i0, i1, a])
            ortusen.sort(key=lambda r: r[0])
            # köşe payları: parçanın, hiçbir duvarın kendi boyuna denk gelmeyen kısımları (duvar ucundan taşan köşe) komşu aralıklara
            # eklenir; her aralık bir boşluktan en çok kendi kaplama kalınlığı kadar alır. Kalanı açık kenardır (duvarsız).
            bosluklar = []
            imlec = lo
            for i, r in enumerate(ortusen):
                if r[0] - imlec > TOL:
                    bosluklar.append((imlec, r[0], i - 1 if i > 0 else None, i))
                imlec = max(imlec, r[1])
            if ortusen and hi - imlec > TOL:
                bosluklar.append((imlec, hi, len(ortusen) - 1, None))
            for g0, g1, sol_i, sag_i in bosluklar:
                kalan = g1 - g0
                if sol_i is not None:
                    pay = min(kalan, ortusen[sol_i][2][6] + TOL)
                    ortusen[sol_i][1] += pay
                    kalan -= pay
                if sag_i is not None and kalan > TOL:
                    pay = min(kalan, ortusen[sag_i][2][6] + TOL)
                    ortusen[sag_i][0] -= pay
                    kalan -= pay
                if kalan > TOL:
                    acikta += kalan
                    b.setdefault("_acik", []).append((eks, sabit, g0, g1))
            if not ortusen:
                acikta += hi - lo
                b.setdefault("_acik", []).append((eks, sabit, lo, hi))
            for i0, i1, a in ortusen:
                toplanan.setdefault((a[0]["ad"], a[1]), []).append((i0, i1, a))
        for (dad, kn), liste in toplanan.items():
            liste.sort(key=lambda r: r[0])
            d, eks, ka = liste[0][2][0], liste[0][2][2], liste[0][2][7]
            birlesik = [[liste[0][0], liste[0][1]]]
            for i0, i1, _ in liste[1:]:
                if i0 <= birlesik[-1][1] + TOL:
                    birlesik[-1][1] = max(birlesik[-1][1], i1)
                else:
                    birlesik.append([i0, i1])
            yuzler.append({"duvar": dad, "sinif": d["sinif"], "kenar": kn, "eksen": eks, "bolge": b["ad"], "bolge_sinifi": b["sinif"],
                           "kaplama": ka, "uzun": eks == d["yon"], "araliklar": [(round(i0, 4), round(i1, 4)) for i0, i1 in birlesik],
                           "boy": sum(i1 - i0 for i0, i1 in birlesik)})
        b["acik_kenar_cm"] = acikta
        # kapalı bir mahalde çevrenin tamamı bir duvar yüzüne yazılmış olmalı
        if b["sinif"] != "dis" and not b.get("poligon"):
            top = sum(y["boy"] for y in yuzler if y["bolge"] == b["ad"])
            if acikta > 0.05 or abs(top - b["net"].length) > 0.05:
                raise SystemExit(f"{b['ad']}: yüzlerin toplamı ({top:.2f}) çevreye ({b['net'].length:.2f}) eşit değil; duvara yazılamayan {acikta:.2f} cm: {b.get('_acik')}")

    # ── açıklıklar ───────────────────────────────────────────────────────────
    acikliklar = []
    for ac in tanim.get("acikliklar", []):
        d = adli.get(ac["duvar"])
        if d is None:
            raise SystemExit(f"Açıklığın duvarı yok: {ac}")
        a0, a1 = ac["bas"], ac["bas"] + ac["en"]
        if a0 < d["_bas"] - TOL or a1 > d["_son"] + TOL:
            raise SystemExit(f"Açıklık duvarın dışına taşıyor: {ac.get('ad')} ({a0}–{a1}; {d['ad']} {d['_bas']}–{d['_son']})")
        z0 = ac.get("alt", 0.0)
        acikliklar.append(dict(ac, a0=a0, a1=a1, z0=z0, z1=z0 + ac["yuk"], alan_m2=ac["en"] * ac["yuk"] / 1e4))

    # ── yüz alanları ─────────────────────────────────────────────────────────
    kat_h = tanim["kat_yuksekligi"]
    for y in yuzler:
        d = adli[y["duvar"]]
        ic_yuz = y["bolge_sinifi"] in ("ic", "ek")
        sabit = d.get("kaplama_yuksekligi")
        brut = 0.0
        for lo, hi in y["araliklar"]:
            if y["uzun"]:
                brut += _alan_altinda(d, lo, hi, sabit)
            else:                                                # uç yüzü: o uçtaki kot
                uc = d["_bas"] if y["kenar"] in ("sol", "alt") else d["_son"]
                brut += (hi - lo) * (sabit or _yukseklik(d, uc))
        bos = []
        if y["uzun"]:
            for ac in acikliklar:
                if ac["duvar"] != d["ad"]:
                    continue
                ort = sum(max(0.0, min(hi, ac["a1"]) - max(lo, ac["a0"])) for lo, hi in y["araliklar"])
                if ort > TOL:
                    bos.append({"ad": ac["ad"], "tur": ac["tur"], "alan_m2": round(ort * (ac["z1"] - ac["z0"]) / 1e4, 4)})
        y["brut_m2"] = brut / 1e4
        y["bosluklar"] = bos
        y["net_m2"] = y["brut_m2"] - sum(x["alan_m2"] for x in bos)
        y["ic_yuz"] = ic_yuz

    # ── mahal özetleri ───────────────────────────────────────────────────────
    for b in bolgeler.values():
        if b["sinif"] == "dis":
            continue
        ic, dk = _kose_say(b["net"]) if b["net"].geom_type == "Polygon" else (0, 0)
        b.update(alan_m2=b["net"].area / 1e4, ham_alan_m2=b["ham"].area / 1e4, cevre_m=b["net"].length / 100, ic_kose=ic, dis_kose=dk)
    return {"tanim": tanim, "duvarlar": duvarlar, "adli": adli, "bolgeler": bolgeler, "yuzler": yuzler, "acikliklar": acikliklar,
            "kutle": kutle, "kat_h": kat_h}


def rapor(y: dict) -> dict:
    """Yalın rapor (JSON'a yazılır): mahaller, yüzler, duvar boyları."""
    t = y["tanim"]
    mah = []
    for b in y["bolgeler"].values():
        if b["sinif"] == "dis":
            continue
        yz = [f for f in y["yuzler"] if f["bolge"] == b["ad"]]
        mah.append({"ad": b["ad"], "sinif": b["sinif"], "islev": b.get("islev", []), "islak": bool(b.get("islak")),
                    "alan_m2": round(b["alan_m2"], 3), "karkas_yuzleri_arasi_m2": round(b["ham_alan_m2"], 3), "etiket_m2": b.get("etiket_m2"),
                    "cevre_m": round(b["cevre_m"], 3), "ic_kose": b["ic_kose"], "dis_kose": b["dis_kose"],
                    "duvar_brut_m2": round(sum(f["brut_m2"] for f in yz), 3), "duvar_net_m2": round(sum(f["net_m2"] for f in yz), 3),
                    "bosluklar": [x for f in yz for x in f["bosluklar"]]})
    duvar = [{"ad": d["ad"], "sinif": d["sinif"], "yon": d["yon"], "boy_cm": round(d["boy"], 2), "kalinlik_cm": round(d["kalinlik"], 2),
              "yukseklik_cm": d["yukseklik"], "kutu": d["kutu"]} for d in y["duvarlar"]]
    yuz = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in f.items()} for f in y["yuzler"]]
    return {"sema": "portman.yapi_raporu/0.5-taslak", "kod": t["kod"], "ad": t["ad"], "mahaller": mah, "duvarlar": duvar, "yuzler": yuz,
            "acikliklar": [{k: v for k, v in a.items() if k not in ("a0", "a1")} for a in y["acikliklar"]]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--rapor", type=Path)
    a = ap.parse_args()
    y = kur(json.loads(a.tanim.read_text(encoding="utf-8")))
    r = rapor(y)
    for m in r["mahaller"]:
        et = "" if m["etiket_m2"] is None else f" · çizim etiketi {m['etiket_m2']:.2f}"
        print(f"  {m['ad']:22s} {m['sinif']:8s} alan {m['alan_m2']:6.2f} m² (karkas yüzleri arası {m['karkas_yuzleri_arasi_m2']:6.2f}{et}) · çevre {m['cevre_m']:6.2f} m"
              f" · iç köşe {m['ic_kose']} · dış köşe {m['dis_kose']} · duvar net {m['duvar_net_m2']:6.2f} m²")
    if a.rapor:
        a.rapor.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
