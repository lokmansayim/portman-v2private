"""Yerleşim katmanlarının girdisi: bugünkü IFC'nin kurulduğu plan (`motor.ifc_uret.hazirla`) ve İş Emri'nin özellikleri.

Koordinat Motor'unkidir (cm; sol-ön dış köşe 0,0; +x sağa, +y arkaya). Duvarlar pano dikdörtgenlerinden kurulur: aynı türde, aynı yönde
ve aynı eksendeki bitişik panolar tek duvar parçasıdır; iç köşe bağlantısı (iç duvarın L köşesindeki parça) ekseni üstünde olduğu duvarın
ucuna eklenir. Bu modül `ifc_uret`'i yüklemez; planı çağıran verir (`kart_model.uret`).
"""
from __future__ import annotations

from dataclasses import dataclass

YAPISMA_CM = 0.5            # iki dikdörtgen bu kadar yakınsa bitişik sayılır (pano uçları ve bağlantılar Motor'da tam sayıya oturur)


@dataclass(frozen=True)
class Duvar:
    tur: str                # "dis" | "ic"
    yon: str                # uzandığı eksen: "x" | "y"
    c: float                # ekseni (öteki koordinat)
    h: float                # yarı kalınlık
    a0: float               # uzandığı eksende baş
    a1: float               # uzandığı eksende son

    @property
    def yuzler(self) -> tuple[float, float]:
        return self.c - self.h, self.c + self.h


def _duvarlar(panolar: list[dict], baglantilar: list[dict]) -> list[Duvar]:
    gruplar: dict[tuple, list[tuple[float, float, float]]] = {}
    for p in panolar:
        x0, y0, x1, y1 = p["rect"]
        c, a0, a1, h = ((y0 + y1) / 2, x0, x1, (y1 - y0) / 2) if p["yon"] == "x" else ((x0 + x1) / 2, y0, y1, (x1 - x0) / 2)
        gruplar.setdefault((p["tur"], p["yon"], round(c, 2)), []).append((a0, a1, h))
    duvarlar = []
    for (tur, yon, c), parcalar in sorted(gruplar.items()):
        parcalar.sort()
        h = max(p[2] for p in parcalar)
        u0, u1 = parcalar[0][:2]
        for a0, a1, _h in parcalar[1:]:
            if a0 <= u1 + YAPISMA_CM:
                u1 = max(u1, a1)
            else:
                duvarlar.append(Duvar(tur, yon, c, h, u0, u1)); u0, u1 = a0, a1
        duvarlar.append(Duvar(tur, yon, c, h, u0, u1))
    # iç köşe bağlantısı: ekseni bir iç duvarın ekseninde ve o duvarın ucuna bitişikse duvar o kadar uzar (PK-01: 198,25 ekseni 741'e)
    out = []
    for d in duvarlar:
        a0, a1 = d.a0, d.a1
        if d.tur == "ic":
            for b in baglantilar:
                bx0, by0, bx1, by1 = b["rect"]
                bc, b0, b1 = ((by0 + by1) / 2, bx0, bx1) if d.yon == "x" else ((bx0 + bx1) / 2, by0, by1)
                if abs(bc - d.c) > YAPISMA_CM:
                    continue
                if abs(b1 - a0) <= YAPISMA_CM:
                    a0 = min(a0, b0)
                elif abs(b0 - a1) <= YAPISMA_CM:
                    a1 = max(a1, b1)
        out.append(Duvar(d.tur, d.yon, d.c, d.h, a0, a1))
    return out


def kucuk(x) -> str:
    """Türkçe küçük harf (`motor/prefabrik_liste.py` ile aynı): "İ" → "i", "I" → "ı"."""
    return str(x).replace("İ", "i").replace("I", "ı").lower()


def tavan_turu(ozellikler: dict) -> str:
    """Liste üreteciyle aynı okuma (`motor/prefabrik_liste.py`): özellikte "ters" geçiyorsa ters tavan, değilse asma dizme."""
    kucuk_ = {kucuk(k): kucuk(v) for k, v in (ozellikler or {}).items()}
    return "ters" if "ters" in kucuk_.get("tavan", kucuk_.get("tavan şekli", "asma")) else "asma"


def _tavan_yazili(ozellikler: dict) -> bool:
    return any(kucuk(k) in ("tavan", "tavan şekli") for k in (ozellikler or {}))


def kur(ie: dict, plan: dict, makaslar: list[dict]) -> dict:
    """`plan`: `motor.ifc_uret.hazirla(ie)`; `makaslar`: kart modelindeki makasların yeri ({ad, rol: bas | orta, konum}; konum makasın
    dizildiği eksende, cm). Dönen sözlük yerleşim modüllerinin tek girdisidir; `uyarilar` varsayılan okumaları ve girdide olup planda
    olmayanları yazar (sayımda ve planlarda görünür)."""
    from motor.geometry import ACIK_MAHAL_TURLERI
    P = plan["panolar"]
    W, H = max(p["rect"][2] for p in P), max(p["rect"][3] for p in P)            # bugünkü IFC'nin çatısıyla aynı dış ölçü (`ifc_uret.doseme`)
    b = plan["bina"]
    c = b["cati"]
    baslangic = ((ie.get("yapi") or {}).get("dizilim") or {}).get("baslangic", "on-sol")
    acik = [plan["veranda"]] if plan.get("veranda") else []
    uyarilar = []
    oz = ie.get("ozellikler") or {}
    if not _tavan_yazili(oz):
        uyarilar.append({"katman": "tavan omegası", "metin": "İş Emri'nde Tavan yazılı değil; asma dizme sayıldı (liste üreteciyle aynı okuma)"})
    acik_ie = [m.get("ad", "?") for m in ie.get("mahaller", []) if m.get("tur") in ACIK_MAHAL_TURLERI]
    if len(acik_ie) > len(acik):                                    # `hazirla` tek açık mahal verir (sonuncusu)
        kalan = [a for a in acik_ie if a not in {v["ad"] for v in acik}]
        uyarilar.append({"katman": "tavan omegası", "metin": f"İş Emri'nde {len(acik_ie)} açık mahal, bugünkü IFC'nin planında {len(acik)}; "
                                                             f"{', '.join(kalan)} için omega kurulmadı"})
    koseler = [x for x in plan.get("baglantilar", []) if x["tur"] == "baglanti" and "iç köşe" in kucuk(x["kalem"])]
    return {
        "W": W, "H": H, "duvar_h": b["duvar_h"],
        "cati": {"tip": c["tip"], "egim": c["egim"], "sacak": c["sacak"], "topuk": c["topuk"], "makas_ekseni": c.get("makas_ekseni", "x")},
        "duvarlar": _duvarlar(P, koseler),
        "odalar": [{"ad": o["ad"], "poligon": o["poligon"]} for o in plan["odalar"]],
        "acik": [{"ad": v["ad"], "poligon": v["poligon"]} for v in acik],
        "engeller": [x["rect"] for x in plan.get("baglantilar", []) if x["tur"] in ("veranda_profil", "dikme")],
        "ozellikler": oz,
        "tavan": tavan_turu(oz),
        "cati_tipi": (ie.get("cati") or {}).get("tip", "besik"),
        "baslangic": {"x": "min", "y": "max" if baslangic.startswith("arka") else "min"},
        "makaslar": makaslar,
        "uyarilar": uyarilar,
    }
