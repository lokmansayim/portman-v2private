"""Katalog İş Emri'ne deterministik varyant uygulama. v0.1: ayna_x, ayna_y, pencere_degistir.

Aynalama pano biriminde yapılır; LLM geometriye dokunmaz. Pano indeksleri motorun aday listesinden
(kur() hata mesajındaki 'aday N') hesaplanır; menteşe her aynada ters döner (el değişimi).
"""
from __future__ import annotations
import copy, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from motor import geometry as G  # noqa: E402

DUVAR_X = {"sol": "sag", "sag": "sol"}
DUVAR_Y = {"on": "arka", "arka": "on"}
MENTESE = {"sol": "sag", "sag": "sol"}
KONUM = {"on": "arka", "arka": "on"}


class VaryantHatasi(Exception):
    pass


def _aday_sayisi(is_emri: dict, idx_aciklik: int) -> int:
    """Belirli açıklığın aday pano sayısını motordan öğren (kasıtlı aralık dışı indeksle)."""
    ie = copy.deepcopy(is_emri)
    ie["acikliklar"][idx_aciklik]["pano"] = 999
    try:
        G.kur(ie)
    except G.IsEmriHatasi as e:
        m = re.search(r"\(aday (\d+)\)", str(e))
        if m:
            return int(m.group(1))
        raise VaryantHatasi(f"aday sayısı okunamadı: {e}")
    raise VaryantHatasi("aday sayısı belirlenemedi")


def ayna(is_emri: dict, eksen: str) -> dict:
    """eksen 'x': sol-sağ ayna (x' = nx - x). eksen 'y': ön-arka ayna (y' = ny - y)."""
    if eksen not in ("x", "y"):
        raise VaryantHatasi("eksen x veya y olmalı")
    ie = copy.deepcopy(is_emri)
    nx, ny = ie["yapi"]["grid"]["x_pano"], ie["yapi"]["grid"]["y_pano"]

    # 1) aday pano sayıları (özgün geometride) — yalnız indeksi verilmiş ve yönü tersine dönecek açıklıklar için
    ters_donen = {}
    for i, ac in enumerate(ie["acikliklar"]):
        if ac.get("pano") is None:
            continue
        duvar_yonu = _aciklik_duvar_yonu(is_emri, ac)   # 'x' yatay duvar, 'y' dikey duvar
        if (eksen == "x" and duvar_yonu == "x") or (eksen == "y" and duvar_yonu == "y"):
            ters_donen[i] = _aday_sayisi(is_emri, i)

    # 2) mahaller
    for m in ie["mahaller"]:
        yeni = []
        for x0, y0, x1, y1 in m["konum_pano"]:
            if eksen == "x":
                yeni.append([nx - x1, y0, nx - x0, y1])
            else:
                yeni.append([x0, ny - y1, x1, ny - y0])
        m["konum_pano"] = yeni

    # 3) açıklıklar
    for i, ac in enumerate(ie["acikliklar"]):
        if "duvar" in ac:
            ac["duvar"] = (DUVAR_X if eksen == "x" else DUVAR_Y).get(ac["duvar"], ac["duvar"])
        if "mentese" in ac:
            ac["mentese"] = MENTESE.get(ac["mentese"], ac["mentese"])
        if i in ters_donen:
            ac["pano"] = ters_donen[i] - 1 - ac["pano"]

    # 4) açık sınırlar (mahal çiftleri) — yön bilgisi taşıyorsa çevir
    for s in ie.get("acik_sinirlar", []):
        if isinstance(s, dict) and "duvar" in s:
            s["duvar"] = (DUVAR_X if eksen == "x" else DUVAR_Y).get(s["duvar"], s["duvar"])

    # 5) dikmeler (cm): özgün plan ölçüleriyle
    if ie.get("dikmeler"):
        plan = G.kur(is_emri)
        W, H = plan.W, plan.H
        ie["dikmeler"] = [([W - x - 10.0, y] if eksen == "x" else [x, H - y - 10.0]) for x, y in ie["dikmeler"]]

    # 6) giriş cephesi / varsayımlar / no
    if eksen == "y":
        ie["yapi"]["giris_cephesi"] = KONUM.get(ie["yapi"].get("giris_cephesi", "on"), "on")
    ie.setdefault("varsayimlar", []).append(f"Varyant: ayna_{eksen} uygulandı (pano biriminde deterministik dönüşüm).")
    ie["is_emri_no"] = ie.get("is_emri_no", "PM") + f"-AYNA{eksen.upper()}"
    return ie


def _aciklik_duvar_yonu(is_emri: dict, ac: dict) -> str:
    """Açıklığın oturduğu duvar yatay mı ('x') dikey mi ('y')? Pencerede duvar adı; kapıda iki mahalin komşuluğu."""
    if "duvar" in ac:
        return "x" if ac["duvar"] in ("on", "arka") else "y"
    a, b = ac["arasi"]
    ra = _rects(is_emri, a); rb = _rects(is_emri, b)
    for x0, y0, x1, y1 in ra:
        for u0, v0, u1, v1 in rb:
            if (abs(x1 - u0) < 1e-9 or abs(u1 - x0) < 1e-9) and min(y1, v1) - max(y0, v0) > 1e-9:
                return "y"
            if (abs(y1 - v0) < 1e-9 or abs(v1 - y0) < 1e-9) and min(x1, u1) - max(x0, u0) > 1e-9:
                return "x"
    raise VaryantHatasi(f"{a}–{b} komşu değil")


def _rects(is_emri: dict, ad: str):
    for m in is_emri["mahaller"]:
        if m["ad"] == ad:
            return m["konum_pano"]
    raise VaryantHatasi(f"mahal yok: {ad}")


def pencere_degistir(is_emri: dict, mahal: str | None, eski: str | None, yeni: str) -> dict:
    """Mahal (ve varsa eski ölçü) eşleşen pencerelerin ölçüsünü değiştirir. Eşleşme yoksa hata."""
    ie = copy.deepcopy(is_emri)
    n = 0
    for ac in ie["acikliklar"]:
        if ac["tur"] != "pencere": continue
        if mahal and _norm(ac["mahal"]) != _norm(mahal): continue
        if eski and ac["olcu"] != eski: continue
        ac["olcu"] = yeni; n += 1
    if n == 0:
        raise VaryantHatasi(f"Değiştirilecek pencere bulunamadı (mahal={mahal}, eski={eski})")
    ie.setdefault("varsayimlar", []).append(f"Varyant: {n} pencere {yeni} yapıldı (mahal={mahal or 'tümü'}).")
    return ie


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c"))
