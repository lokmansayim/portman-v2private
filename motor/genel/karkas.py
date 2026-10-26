#!/usr/bin/env python3
"""Çelik karkas kuralı (İE-16 PR-3a): duvarı panellere böler, panelin üyelerini kurar, profil boyunu verir.

Yalnız tanım isterse çalışır (`"karkas": "kural"`); istemeyen tanımın çıktısı bayt bayt aynıdır. Kurallar ve kaynakları
`kurallar/karkas/celik_karkas.json`'dadır (`PORTMAN_KARKAS` ile başka bir kopyası seçilir; liste, hazırlandığı günkü kuralla yeniden
üretilebilmeli). Ağırlık parçaların boyundan: profil boyu × profilin birim ağırlığı (kitapta `celik.profil_kg_m`).

1. **Koşu.** Aynı sınıf, aynı doğrultu, aynı hat (kalınlık), aynı profil ve yükseklikteki, uç uca değen duvarlar tek koşudur: tanım
   duvarı nasıl yazmış olursa olsun (bölmeli ya da bölmesiz) koşu aynıdır. Eğik üst kotlu duvar kendi başına koşudur.
2. **Bölme.** Koşu `ceil(boy / bolme.hedef_cm)` eşit panele bölünür; ek yeri bir açıklığın içine düşerse açıklığın yakın kenarına
   kayar. Panel bu yüzden hedef boyu aşabilir: aşan her panel kayda (`uyarilar`) ve paftaya yazılır, sessiz kalmaz.
3. **Üyeler** (panel başına, cm): alt ve üst başlık; ızgara dikmeleri (panel başından `dikme_araligi_cm` arayla, uçta da bir dikme);
   açıklığın içine düşen ızgara dikmesi kırpıktır (lentonun üstü ve denizliğin altı); açıklığın kenarında, yarım aralık içinde tam dikme
   yoksa kenar dikmesi; açıklığın başlık levhası (net + `levha_payi_cm`) ve pencerede denizlik levhası; kuşaklar (`kusak_kotlari_cm`,
   açıklığın kestiği boy düşülür); çapraz ve birleşim payı (yükseklik × (a + b × boy), m; yazılı kurallar adedini vermez, KT-01'in
   karkas modelinden).
4. **Kolon ve kiriş:** kolon yüksekliği × `kolon.profil_m_m`, kirişin boyu × `kiris.profil_m_m` (KT-01'in karkas modelinden).

Hesapta LLM yoktur: aynı tanım ve aynı kural aynı sonucu verir.

Kullanım:
    python -m motor.genel.karkas tanim.json [--json paneller.json]
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

from . import yapi

KOK = Path(__file__).resolve().parents[2]
KURAL = KOK / "kurallar" / "karkas" / "celik_karkas.json"
DUVAR_SINIFLARI = ("dis", "ic", "ek", "korkuluk")      # karkas kuralının duvar panelleri; baca ve makas PR-3b'de
TOL = 1.0                                                # cm; uç uca değme ve aynı hat toleransı


def yol() -> Path:
    secilen = os.environ.get("PORTMAN_KARKAS")
    return Path(secilen).expanduser().resolve() if secilen else KURAL


def oku(kural_yolu: Path | str | None = None) -> dict:
    y = Path(kural_yolu) if kural_yolu else yol()
    if not y.is_file():
        raise SystemExit(f"Karkas kuralı yok: {y} (PORTMAN_KARKAS yanlış olabilir).")
    k = json.loads(y.read_text(encoding="utf-8"))
    k["_yol"], k["_sha256"] = str(y), hashlib.sha256(y.read_bytes()).hexdigest()
    return k


def d(k: dict, anahtar: str):
    """Kuralın değeri (`deger`)."""
    return k[anahtar]["deger"]


def _profil(w: dict, sinif: dict) -> str | None:
    return w.get("profil") or sinif[w["sinif"]].get("profil")


def kosular(y: dict, t: dict) -> list[dict]:
    """Duvar koşuları (yapi.kur'un duvarlarından; sınıf sırası DUVAR_SINIFLARI, sonra hat ve başlangıç)."""
    sinif = t["duvar_siniflari"]
    gruplar: dict[tuple, list[dict]] = {}
    for w in y["duvarlar"]:
        if w["sinif"] not in DUVAR_SINIFLARI:
            continue
        x0, y0, x1, y1 = w["kutu"]
        hat = (round(x0, 1), round(x1, 1)) if w["yon"] == "y" else (round(y0, 1), round(y1, 1))
        egik = isinstance(w["yukseklik"], dict)
        anahtar = (DUVAR_SINIFLARI.index(w["sinif"]), w["yon"], hat, _profil(w, sinif) or "",
                   w["ad"] if egik else json.dumps(w["yukseklik"]), json.dumps(w.get("ust_kot")), json.dumps(w.get("kaplama_yuksekligi")))
        gruplar.setdefault(anahtar, []).append(w)
    out = []
    for anahtar in sorted(gruplar, key=lambda a: (a[0], a[1], a[2], a[3], a[4], a[5], a[6])):
        ws = sorted(gruplar[anahtar], key=lambda w: w["_bas"])
        zincir = [ws[0]]
        for w in ws[1:] + [None]:
            if w is not None and abs(w["_bas"] - zincir[-1]["_son"]) < TOL:
                zincir.append(w)
                continue
            out.append({"sinif": zincir[0]["sinif"], "yon": zincir[0]["yon"], "hat": anahtar[2], "profil": _profil(zincir[0], sinif),
                        "bas": zincir[0]["_bas"], "son": zincir[-1]["_son"], "duvarlar": [z["ad"] for z in zincir],
                        "yukseklik": zincir[0]["yukseklik"], "_ilk": zincir[0], "_son_d": zincir[-1]})
            zincir = [w] if w is not None else []
    return out


def _acikliklar(y: dict, kosu: dict) -> list[dict]:
    adlar = set(kosu["duvarlar"])
    return sorted((a for a in y["acikliklar"] if a["duvar"] in adlar), key=lambda a: a["a0"])


def bol(kosu: dict, acik: list[dict], k: dict) -> list[tuple[float, float]]:
    """Koşunun panelleri [(baş, son)], mutlak konum (cm). Eşit bölme; açıklığın içine düşen ek yeri yakın kenara kayar (panel hedef
    boyu aşabilir; `kur` aşanı `uyarilar`'a yazar)."""
    b = d(k, "bolme")
    bas, son = kosu["bas"], kosu["son"]
    L = son - bas
    n = max(1, math.ceil(L / b["hedef_cm"] - 1e-9))
    ekler = []
    for i in range(1, n):
        j = bas + L * i / n
        for a in acik:
            if a["a0"] < j < a["a1"]:
                j = a["a0"] if j - a["a0"] <= a["a1"] - j else a["a1"]
        ekler.append(round(j, 1))
    noktalar = [bas] + sorted(set(ekler)) + [son]
    return [(p0, p1) for p0, p1 in zip(noktalar, noktalar[1:]) if p1 - p0 > TOL]


def uyeler(L: float, H: float, acik: list[tuple[float, float, float, float]], k: dict) -> dict[str, float]:
    """Bir panelin üyeleri, tür tür toplam boy (m). acik: [(baş, son, alt kot, üst kot)] panel başından (cm)."""
    S = d(k, "dikme_araligi_cm")
    pay = d(k, "aciklik")["levha_payi_cm"]
    u = {"baslik": 2 * L, "dikme": 0.0, "kirpik": 0.0, "kenar_dikmesi": 0.0, "lento_denizlik": 0.0, "kusak": 0.0}
    xs = [i * S for i in range(int(L // S) + 1)]
    if L - xs[-1] > TOL:
        xs.append(L)
    tam = []
    for x in xs:
        ic = [a for a in acik if a[0] - 0.5 < x < a[1] + 0.5]
        if ic:
            a0, a1, z0, z1 = ic[0]
            u["kirpik"] += max(H - z1, 0.0) + z0
        else:
            u["dikme"] += H
            tam.append(x)
    for a0, a1, z0, z1 in acik:
        for kenar in (a0, a1):
            if not tam or min(abs(kenar - f) for f in tam) > S / 2:
                u["kenar_dikmesi"] += H
        u["lento_denizlik"] += (a1 - a0) + pay
        if z0 > 0:
            u["lento_denizlik"] += (a1 - a0) + pay
    for z in d(k, "kusak_kotlari_cm"):
        if z < H - d(k, "kusak_ust_payi_cm"):
            u["kusak"] += max(L - sum(a1 - a0 for a0, a1, z0, z1 in acik if z0 < z < z1), 0.0)
    cp = d(k, "capraz_payi")
    u = {ad: v / 100 for ad, v in u.items()}
    u["capraz"] = H / 100 * (cp["a_m_m"] + cp["b_m_m2"] * L / 100)
    return u


def kur(y: dict, t: dict, k: dict) -> dict:
    """Paneller (D01…), kolonlar ve kirişler; her biri üyeleri ve profil boyuyla."""
    paneller = []
    for ks in kosular(y, t):
        acik = _acikliklar(y, ks)
        H = yapi._yukseklik(ks["_ilk"]) if len(ks["duvarlar"]) == 1 else float(ks["yukseklik"])
        for p0, p1 in bol(ks, acik, k):
            ap = [(max(a["a0"], p0) - p0, min(a["a1"], p1) - p0, a["z0"], a["z1"]) for a in acik if a["a1"] > p0 + TOL and a["a0"] < p1 - TOL]
            u = uyeler(p1 - p0, H, ap, k)
            x0, y0, x1, y1 = (p0, ks["hat"][0], p1, ks["hat"][1]) if ks["yon"] == "x" else (ks["hat"][0], p0, ks["hat"][1], p1)
            paneller.append({"sinif": ks["sinif"], "profil": ks["profil"], "kosu": ks["duvarlar"], "bas": round(p0, 2), "son": round(p1, 2),
                             "boy_cm": round(p1 - p0, 2), "yukseklik_cm": round(H, 2), "kutu": [round(v, 2) for v in (x0, y0, x1, y1)],
                             "acikliklar": [a["ad"] for a in acik if a["a1"] > p0 + TOL and a["a0"] < p1 - TOL],
                             "uyeler_m": {ad: round(v, 4) for ad, v in u.items()}, "profil_boyu_m": round(sum(u.values()), 4)})
    _adlandir(paneller)
    hedef = d(k, "bolme")["hedef_cm"]
    uyarilar = [f"{p['ad']} ({', '.join(p['kosu'])}): panel {p['boy_cm']} cm, bölmenin hedefi {hedef} cm; ek yeri açıklığın kenarına kaydı"
                for p in paneller if p["boy_cm"] > hedef + TOL]
    kol = d(k, "kolon")["profil_m_m"]
    kolonlar = [{"ad": w["ad"], "yukseklik_cm": yapi._yukseklik(w), "profil_boyu_m": round(kol * yapi._yukseklik(w) / 100, 4)}
                for w in y["duvarlar"] if w["sinif"] == "kolon"]
    kir = d(k, "kiris")["profil_m_m"]
    kirisler = []
    for kr in t.get("kirisler", []):
        if kr.get("celik_grubu", "kiris") != "kiris":
            continue
        bx0, by0, bx1, by1 = kr["kutu"]
        boy = max(bx1 - bx0, by1 - by0)
        kirisler.append({"ad": kr["ad"], "boy_cm": boy, "profil_boyu_m": round(kir * boy / 100, 4)})
    return {"kural": {"yol": _goreli(k["_yol"]), "sha256": k["_sha256"], "sema": k.get("sema")},
            "paneller": paneller, "kolonlar": kolonlar, "kirisler": kirisler, "uyarilar": uyarilar}


def _goreli(p: str) -> str:
    try:
        return Path(p).resolve().relative_to(KOK).as_posix()
    except ValueError:
        return Path(p).name


def _adlandir(paneller: list[dict]) -> None:
    """D01…: önce binanın dış duvarları (batıdan başlayıp saat yönünde, merkezin çevresinde), sonra öteki duvarlar (kuzeyden güneye, batıdan doğuya)."""
    dis = [p for p in paneller if p["sinif"] == "dis"]
    if dis:
        cx = (min(p["kutu"][0] for p in dis) + max(p["kutu"][2] for p in dis)) / 2
        cy = (min(p["kutu"][1] for p in dis) + max(p["kutu"][3] for p in dis)) / 2
    else:
        cx = cy = 0.0

    def aci(p):
        mx, my = (p["kutu"][0] + p["kutu"][2]) / 2, (p["kutu"][1] + p["kutu"][3]) / 2
        return (math.pi - math.atan2(my - cy, mx - cx)) % (2 * math.pi)     # batı 0, kuzey π/2, doğu π, güney 3π/2 (saat yönü)

    sira = sorted(dis, key=lambda p: (round(aci(p), 6), p["kutu"])) + sorted(
        (p for p in paneller if p["sinif"] != "dis"),
        key=lambda p: (DUVAR_SINIFLARI.index(p["sinif"]), -round((p["kutu"][1] + p["kutu"][3]) / 2, 1), round((p["kutu"][0] + p["kutu"][2]) / 2, 1)))
    for i, p in enumerate(sira, 1):
        p["ad"] = f"D{i:02d}"
    paneller.sort(key=lambda p: p["ad"])


def gruplar(kk: dict, y: dict, t: dict, k: dict, kg_m: dict) -> dict:
    """Listenin çelik gruplarına (`girdi_genel` › `celik_modeli` biçimi): {grup: {adet, profil_boyu_m, profil, birim_kg_m?}}.
    Korkuluk sınıfı `girdi_genel`'deki gibi ayrılır: tek profil → korkuluk; birden çok profilde tam boy (≥ 200) olanlar giriş çerçevesi."""
    sinif = t["duvar_siniflari"]
    ek_kg = d(k, "profil_kg_m_ek")

    def kayit(adet: int, boy: float, profil: str | None) -> dict:
        r = {"adet": adet, "profil_boyu_m": round(boy, 3), "profil": profil}
        if profil and profil not in kg_m and profil in ek_kg:
            r["birim_kg_m"] = ek_kg[profil]
        return r

    out: dict[str, dict] = {}
    for s in ("dis", "ic", "ek"):
        ps = [p for p in kk["paneller"] if p["sinif"] == s]
        if ps:
            out[s] = kayit(len(ps), sum(p["profil_boyu_m"] for p in ps), ps[0]["profil"] if len({p["profil"] for p in ps}) == 1 else None)
    kork = [w for w in y["duvarlar"] if w["sinif"] == "korkuluk"]
    profiller = sorted({w.get("profil") or sinif["korkuluk"]["profil"] for w in kork}, reverse=True)
    for tprof in profiller:
        dl = {w["ad"] for w in kork if (w.get("profil") or sinif["korkuluk"]["profil"]) == tprof}
        tam_boy = all(yapi._yukseklik(w) >= 200 for w in kork if w["ad"] in dl)
        grup = "korkuluk" if len(profiller) == 1 or not tam_boy else "giris_cercevesi"
        ps = [p for p in kk["paneller"] if p["sinif"] == "korkuluk" and set(p["kosu"]) <= dl]
        out[grup] = kayit(len(ps), sum(p["profil_boyu_m"] for p in ps), tprof)
    if kk["kolonlar"]:
        out["kolon"] = kayit(len(kk["kolonlar"]), sum(x["profil_boyu_m"] for x in kk["kolonlar"]), None)
    if kk["kirisler"]:
        out["kiris"] = kayit(len(kk["kirisler"]), sum(x["profil_boyu_m"] for x in kk["kirisler"]), None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tanim", type=Path)
    ap.add_argument("--kural", type=Path, default=None, help="karkas kuralı (varsayılan: kurallar/karkas/celik_karkas.json ya da PORTMAN_KARKAS)")
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()
    t = json.loads(a.tanim.read_text(encoding="utf-8"))
    k = oku(a.kural)
    kk = kur(yapi.kur(t), t, k)
    for p in kk["paneller"]:
        print(f"{p['ad']} {p['sinif']:8s} {p['boy_cm']:7.1f} × {p['yukseklik_cm']:5.1f}  {p['profil_boyu_m']:7.2f} m  {', '.join(p['acikliklar'])}")
    for x in kk["kolonlar"] + kk["kirisler"]:
        print(f"{x['ad']} {x['profil_boyu_m']:7.2f} m")
    for u in kk["uyarilar"]:
        print("  UYARI:", u)
    if a.json:
        a.json.write_text(json.dumps(kk, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
