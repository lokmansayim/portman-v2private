#!/usr/bin/env python3
"""İE-14 · otomatik çatı üreticisi (ayrı parça; Lokman, 14.10.2026, r2).

Girdi: kapalı ayak izi (dış yüzler, cm; 14a'da dikdörtgen), tip (beşik/kırma), mahya yönü, eğim. Çıktı: Yapı Tanımı 0.5'in `cati`
bölümü (`duzlemler`, `kalkanlar`); bütün sayılar `kurallar/cizim/cati_uretici.json`'dan (anahtar yoksa aynı değer koddan).
Çıktı `cati_genel.cati_kur`'dan geçmek zorundadır (plan denetçisi ve testler koşturur). L ve cumbalı ayak izi 14b.

Kurallar:
- Saçak dış yüzden 30, saçak kotu = duvar üstü + topuk 10; eğim verilmezse %33; üst pay = panel × √(1 + eğim²).
- Mahya verilmezse uzun kenar boyunca. Kırmada mahya her zaman uzun kenardadır (kısa kenarda ters kırma çıkar): verilen mahya
  kısa kenardaysa `CatiHatasi`. Kare ayak izinde kırma piramittir (mahya boyu 0, dört üçgen).
- Beşik: 2 düzlem + uçlarda 2 kalkan (dış yüz çizgisinde). Kırma: 4 düzlem, kalkan yok.

Hesapta LLM yoktur; aynı girdi aynı çatıyı verir. `olc(cati)` bankadaki elle yazılmış çatıyla kıyas için düzlem sayısı, plan alanı ve
kenar toplamlarını (`cati_kur` sınıflamasıyla: saçak, mahya, kırma) verir (K7).
"""
from __future__ import annotations
from .toplam import sum  # noqa: A001 — 3.11 toplama sırası her Python sürümünde (İE-08 GM2; toplam.py)

import json
from pathlib import Path

from . import cati_besik, cati_cumba, cati_kirma, cati_l, cati_ortak

KURAL_YOLU = Path(__file__).resolve().parents[2] / "kurallar" / "cizim" / "cati_uretici.json"
VARSAYILAN = {"sacak_cm": 30, "topuk_cm": 10, "panel_kalinligi_cm": 8, "egim_varsayim": 0.33, "egim_yuzde_aralik": [10, 60],
              "tipler": ["besik", "kirma", "cumba", "l"], "kirma_mahya_en_az_cm": 15}
TIP_ADI = {"besik": "beşik", "kirma": "kırma", "cumba": "beşik + cumba", "l": "L beşik"}


class CatiHatasi(ValueError):
    pass


def kurallar(yol: Path | None = None) -> dict:
    """Kural tablosunun değerleri; dosya ya da anahtar yoksa koddaki varsayılan."""
    k = dict(VARSAYILAN)
    p = Path(yol) if yol else KURAL_YOLU
    if p.exists():
        ham = json.loads(p.read_text(encoding="utf-8"))
        for ad in VARSAYILAN:
            if isinstance(ham.get(ad), dict) and "deger" in ham[ad]:
                k[ad] = ham[ad]["deger"]
    return k


def _kenar_l(blok, kanat) -> str | None:
    """L: kanadın bloğa bitişik olduğu yan; kanat bloğun o kenarını boydan boya örter (aşabilir)."""
    x0, y0, x1, y1 = blok
    a0, b0, a1, b1 = kanat
    if a0 == x1 and b0 <= y0 and b1 >= y1:
        return "D"
    if a1 == x0 and b0 <= y0 and b1 >= y1:
        return "B"
    if b0 == y1 and a0 <= x0 and a1 >= x1:
        return "K"
    if b1 == y0 and a0 <= x0 and a1 >= x1:
        return "G"
    return None


def _kenar(ana, parca) -> str | None:
    """Cumba: parçanın ana dikdörtgene göre bitişik olduğu yan (parça o kenarın içinde): G (güney), K, B, D; değilse None."""
    x0, y0, x1, y1 = ana
    a0, b0, a1, b1 = parca
    if b1 == y0 and a0 >= x0 and a1 <= x1:
        return "G"
    if b0 == y1 and a0 >= x0 and a1 <= x1:
        return "K"
    if a1 == x0 and b0 >= y0 and b1 <= y1:
        return "B"
    if a0 == x1 and b0 >= y0 and b1 <= y1:
        return "D"
    return None


DONUS_CUMBA = {"G": [], "K": ["ay"], "B": ["d"], "D": ["d", "ay"]}        # kanonik: cumba ana gövdenin güneyinde
DONUS_L = {"D": [], "B": ["ax"], "K": ["d"], "G": ["d", "ax"]}            # kanonik: kanat bloğun doğusunda


def _uygula(rs: list, islemler: list) -> tuple[list, list]:
    """Dikdörtgenlere sırayla ax (x aynası), ay (y aynası), d (devrik) uygular; her aynanın merkezini döner (geri dönüş için)."""
    merkez = []
    for op in islemler:
        if op == "d":
            rs = [[r[1], r[0], r[3], r[2]] for r in rs]
            merkez.append(None)
        elif op == "ax":
            c = (min(r[0] for r in rs) + max(r[2] for r in rs)) / 2
            rs = [[2 * c - r[2], r[1], 2 * c - r[0], r[3]] for r in rs]
            merkez.append(c)
        else:
            c = (min(r[1] for r in rs) + max(r[3] for r in rs)) / 2
            rs = [[r[0], 2 * c - r[3], r[2], 2 * c - r[1]] for r in rs]
            merkez.append(c)
    return rs, merkez


def _geri(c: dict, islemler: list, merkez: list) -> dict:
    for op, m in reversed(list(zip(islemler, merkez))):
        c = cati_ortak.devrik(c) if op == "d" else (cati_ortak.ayna_y(c, m) if op == "ay" else _ayna_x(c, m))
    return c


def uret(ayak_izi, tip: str = "besik", mahya: str | None = None, egim_yuzde: float | None = None,
         duvar_ustu: float = 270, kural: dict | None = None) -> dict:
    """Ayak izi üstüne çatı. Beşik ve kırma: tek dikdörtgen (x0, y0, x1, y1; dış yüzler), `mahya` "x" ya da "y". Cumba: [ana, cumba]
    (cumba ana gövdenin bir uzun kenarına bitişik). L: [blok, kanat] (kanat bloğun bir kısa kenarına bitişik, onu boydan boya örter).
    Tipe göre üretici ayrı modüldedir (`cati_besik`, `cati_kirma`, `cati_cumba`, `cati_l`); ortak sayılar kural tablosundan."""
    k = kural or kurallar()
    if tip not in k["tipler"]:
        raise CatiHatasi(f"çatı tipi '{tip}' üretilmez (yalnız {', '.join(k['tipler'])})")
    if egim_yuzde is None:
        e = float(k["egim_varsayim"])
    else:
        lo, hi = k["egim_yuzde_aralik"]
        if not lo <= egim_yuzde <= hi:
            raise CatiHatasi(f"eğim %{egim_yuzde} aralık dışı (%{lo}–%{hi})")
        e = round(egim_yuzde / 100, 5)
    b = cati_ortak.baglam(k, e, duvar_ustu)
    S = b["S"]
    if tip in ("besik", "kirma"):
        if len(ayak_izi) and isinstance(ayak_izi[0], (list, tuple)) and len(ayak_izi) > 1:
            raise CatiHatasi(f"{TIP_ADI[tip]} çatı tek dikdörtgenle verilir ({len(ayak_izi)} verildi)")   # öteki sessizce atılmaz (inceleme G9)
        R = ayak_izi[0] if (len(ayak_izi) and isinstance(ayak_izi[0], (list, tuple))) else ayak_izi
        x0, y0, x1, y1 = (float(v) for v in R)
        if x1 <= x0 or y1 <= y0:
            raise CatiHatasi(f"ayak izi boş: {R}")
        uzun = "x" if (x1 - x0) >= (y1 - y0) else "y"
        if mahya not in ("x", "y"):
            mahya = uzun
        elif tip == "kirma" and mahya != uzun and abs((x1 - x0) - (y1 - y0)) > 1e-6:
            raise CatiHatasi("kırmada mahya uzun kenar boyunca olur")
        boy = abs((x1 - x0) - (y1 - y0))                     # kırmada mahya boyu = uzun − kısa kenar (kırmalar 45°)
        if tip == "kirma" and 1e-6 < boy <= float(k["kirma_mahya_en_az_cm"]):
            raise CatiHatasi(f"kırma mahyası {boy:g} cm: çelikte {k['kirma_mahya_en_az_cm']:g} cm ve daha kısa parça çıkmaz (D-10); "
                             "ölçüyü kare ya da en az bu kadar farklı yapın")   # inceleme G3
        duz, kal = (cati_besik if tip == "besik" else cati_kirma).uret((x0, y0, x1, y1), mahya, b)
        yon = "doğu–batı" if mahya == "x" else "kuzey–güney"
        tip_adi, tip_kayit = f"{TIP_ADI[tip]} (mahya {yon})", tip
    else:
        if len(ayak_izi) != 2:
            raise CatiHatasi(f"{TIP_ADI[tip]} çatı iki dikdörtgenle verilir ([ana, cumba] ya da [blok, kanat])")
        ana, parca = (list(map(float, r)) for r in ayak_izi)
        yan = _kenar(ana, parca) if tip == "cumba" else _kenar_l(ana, parca)
        if tip == "cumba" and yan:                           # cumba ana gövdenin uzun kenarına bitişir (mahya uzun kenar boyunca; inceleme G5)
            en_, boy_ = ana[2] - ana[0], ana[3] - ana[1]
            if (yan in ("G", "K") and en_ < boy_) or (yan in ("B", "D") and boy_ < en_):
                raise CatiHatasi("beşik + cumba: cumba ana gövdenin uzun kenarına bitişik olmalı")
        islemler = (DONUS_CUMBA if tip == "cumba" else DONUS_L).get(yan or "")
        if islemler is None:
            raise CatiHatasi(f"{TIP_ADI[tip]}: ikinci parça birinciye bir kenarından bitişik olmalı")
        rs, merkez = _uygula([ana, parca], islemler)
        try:
            duz, kal = (cati_cumba if tip == "cumba" else cati_l).uret(rs[0], rs[1], b)
        except ValueError as ex:
            raise CatiHatasi(f"{TIP_ADI[tip]}: {ex}")
        c = _geri({"duzlemler": duz, "kalkanlar": kal}, islemler, merkez)
        duz, kal = c["duzlemler"], c["kalkanlar"]
        lo, hi = k["egim_yuzde_aralik"]
        for d in duz:                                        # L kanadının hesaplanan eğimi de aralıkta olmalı (inceleme G5)
            if not lo / 100 - 1e-9 <= d["egim"] <= hi / 100 + 1e-9:
                raise CatiHatasi(f"{TIP_ADI[tip]}: '{d['ad']}' eğimi %{d['egim'] * 100:.1f} aralık dışı (%{lo}–%{hi})")
        tip_adi, tip_kayit = TIP_ADI[tip], "besik_cumba"
    return {"tip": tip_kayit, "tip_adi": tip_adi, "tip_kaynak": "İE-14 çatı üreticisi (motor/genel/cati_uretici.py)",
            "sacak": int(S) if float(S).is_integer() else S, "topuk": k["topuk_cm"], "duvar_ustu": duvar_ustu,
            "panel_kalinligi": k["panel_kalinligi_cm"], "duzlemler": duz, "kalkanlar": kal}


def _ayna_x(c: dict, cx: float) -> dict:
    """x → 2·cx − x: devrik + y aynası + devrik ile."""
    return cati_ortak.devrik(cati_ortak.ayna_y(cati_ortak.devrik(c), cx))


def denetle(cati: dict, ayak_izi: list) -> list[str]:
    """Ortak denetim (her tip): `cati_kur`'dan geçer; düzlemler ayak izinin saçakla genişletilmiş birleşimini boşluksuz ve örtüşmesiz
    örter; desteksiz üst kenar ('ust') yok. Dönüş: bulgular."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    from . import cati_genel
    bulgu = []
    try:
        c = cati_genel.cati_kur(cati)
    except (SystemExit, Exception) as e:
        return [f"cati_kur: {e}"]
    S = float(cati.get("sacak") or 30)
    rs = ayak_izi if (len(ayak_izi) and isinstance(ayak_izi[0], (list, tuple))) else [ayak_izi]
    hedef = unary_union([box(r[0] - S, r[1] - S, r[2] + S, r[3] + S) for r in rs])
    poli = [Polygon(d["plan"]) for d in cati["duzlemler"]]
    toplam = sum(p.area for p in poli)
    birlesim = unary_union(poli)
    if abs(birlesim.area - hedef.area) > 1 or abs(toplam - birlesim.area) > 1:
        bulgu.append(f"düzlemler saçaklı ayak izini tam örtmüyor (hedef {hedef.area:.0f}, birleşim {birlesim.area:.0f}, toplam {toplam:.0f} cm²)")
    ust = [e for e in c["kenarlar"] if e["tur"] == "ust"]
    if ust:
        bulgu.append(f"desteksiz üst kenar: {len(ust)}")
    return bulgu


def olc(cati: dict) -> dict:
    """Kıyas ölçüleri (K7): düzlem sayısı, plan alanı (cm²), kenar türlerinin plan boyu toplamı (cm; `cati_kur` sınıflaması)."""
    from . import cati_genel
    c = cati_genel.cati_kur(cati)
    top: dict[str, float] = {}
    for e in c["kenarlar"]:
        top[e["tur"]] = top.get(e["tur"], 0.0) + e["plan_boy"]
    return {"duzlem": len(cati["duzlemler"]), "plan_cm2": round(c["plan_m2"] * 1e4, 1),
            "kenar_plan_cm": {t: round(v, 2) for t, v in sorted(top.items())}, "kalkan": len(cati.get("kalkanlar", []))}
