"""MRD FrameBuilder .csv (Alpha Mini) okuyucu ve yazıcı.

Başlık satırları (UNIT, VERSION, PROFILE, FRAMESET) aynen tutulur. Her COMPONENT satırı:
``COMPONENT,<ad>,<LABEL_NRM|LABEL_INV>,<adet>,<boy>,C,<sırt>,<kanat>,<kalınlık>,<kod>,x1,y1,x2,y2,<işlem>,<yer>,…``
- x1 y1 x2 y2: çubuğun ekseni (kanadın ortası), çerçeve düzleminde mm; uçlar kesim uçlarıdır.
- LABEL_NRM: açık ağız x1→x2 yönünün soluna bakar; LABEL_INV sağına.
- İşlemler: DIMPLE vida deliği, SWAGE köşeleme, NOTCH kertme, LIP_CUT düzleme, CUT kesim;
  yer x1 ucundan mm (Mac `Alpha mini AI/_inceleme/IS-5, IS-8, IS-9`, 11–12 Kasım 2026).
Sayılar Python ``repr(float)`` biçiminde yazılı; satır sonu CRLF, UTF-8.
"""
from __future__ import annotations

from pathlib import Path


def oku(yol: str | Path) -> dict:
    metin = Path(yol).read_bytes().decode("utf-8")
    bom = metin.startswith("﻿")
    metin = metin.lstrip("﻿")
    satirlar = metin.split("\r\n")
    son_bos = satirlar[-1] == ""
    if son_bos:
        satirlar = satirlar[:-1]
    baslik, parcalar = [], []
    for s in satirlar:
        a = s.split(",")
        if a[0] != "COMPONENT":
            baslik.append(a)
            continue
        parcalar.append({
            "ad": a[1], "yon": a[2], "adet": int(a[3]), "boy": float(a[4]), "kesit": a[5],
            "sirt": float(a[6]), "kanat": float(a[7]), "kalinlik": float(a[8]), "kod": a[9],
            "x1": float(a[10]), "y1": float(a[11]), "x2": float(a[12]), "y2": float(a[13]),
            "islemler": [(a[i], float(a[i + 1])) for i in range(14, len(a), 2)],
        })
    cerceve = next((b[1] for b in baslik if b[0] == "FRAMESET"), None)
    return {"baslik": baslik, "cerceve": cerceve, "parcalar": parcalar, "bom": bom, "son_satir_bos": son_bos}


def _f(v: float) -> str:
    return repr(float(v))


def yaz(veri: dict) -> bytes:
    satirlar = [",".join(b) for b in veri["baslik"]]
    for p in veri["parcalar"]:
        a = ["COMPONENT", p["ad"], p["yon"], str(p["adet"]), _f(p["boy"]), p["kesit"], _f(p["sirt"]),
             _f(p["kanat"]), _f(p["kalinlik"]), p["kod"], _f(p["x1"]), _f(p["y1"]), _f(p["x2"]), _f(p["y2"])]
        for ad, yer in p["islemler"]:
            a += [ad, _f(yer)]
        satirlar.append(",".join(a))
    metin = "\r\n".join(satirlar) + ("\r\n" if veri["son_satir_bos"] else "")
    return (("﻿" if veri["bom"] else "") + metin).encode("utf-8")


def ozet(veri: dict) -> dict:
    xs = [p[k] for p in veri["parcalar"] for k in ("x1", "x2")]
    ys = [p[k] for p in veri["parcalar"] for k in ("y1", "y2")]
    islem: dict[str, int] = {}
    for p in veri["parcalar"]:
        for ad, _ in p["islemler"]:
            islem[ad] = islem.get(ad, 0) + 1
    kanat = max((p["kanat"] for p in veri["parcalar"]), default=0.0)
    return {
        "cerceve": veri["cerceve"],
        "cubuk": len(veri["parcalar"]),
        "dis_olcu_mm": [round(max(xs) - min(xs) + kanat, 1), round(max(ys) - min(ys) + kanat, 1)],
        "toplam_boy_m": round(sum(p["boy"] * p["adet"] for p in veri["parcalar"]) / 1000, 2),
        "islem": islem,
    }
