"""Kaynak inceleme verisinin ortak geometri işlemleri.

`selected.json` (Codex devri, `veri/skp/<kod>/` ve `veri/p9401_cati/<harf>_selected.json`) şu alanları taşır:
code, revision, source_sha256, nodes[{id, name, source_id, world_transform, material, geometry, root, roof, stage,
proposal?}], meshes{geometry: {vertices (m, yerel), triangles, uv, materials}}, materials, notes.

Dünya dönüşümü (`world_transform`) SketchUp'tan gelir: 16 değer, sütun sıralı, öteleme inç, homojen w'ye bölünmüş
(normalize). Köşeler zaten metredir; yalnız öteleme 0,0254 ile metreye çevrilir.

İki hesap kipi vardır:
  - "blender32": Blender'ın mathutils hesabının birebir taklidi (float32 matris ve vektör, float32 çarpım, float64 toplam,
    float32 sonuç). Codex'in kaydettiği IFC koordinatları bununla bayt bayt yeniden üretilir (30.09: P9401'de 82/82 düğüm).
  - "float64": numpy float64. Daha hassastır; blender32'den farkı 1 µm'nin altındadır (P9401'de en çok 0,72 µm).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import numpy as np

INC = 0.0254
KIPLER = ("blender32", "float64")


def secili_oku(yol: str | Path) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def dosya_sha256(yol: str | Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def dunya_matrisi(t: list[float], kip: str = "blender32") -> np.ndarray:
    """Sütun sıralı 16 değerden 4×4 satır matrisi; öteleme metreye çevrilir."""
    if kip not in KIPLER:
        raise ValueError(f"bilinmeyen kip: {kip}")
    if len(t) != 16:
        raise ValueError("world_transform 16 değer olmalı")
    if abs(t[15] - 1.0) > 1e-9 or any(abs(t[i]) > 1e-9 for i in (3, 7, 11)):
        # Okuyucu w'ye bölerek normalize eder; normalize edilmemiş veri sessizce kabul edilmez.
        raise ValueError(f"dönüşüm normalize değil (w={t[15]}, perspektif={t[3]},{t[7]},{t[11]})")
    tip = np.float32 if kip == "blender32" else np.float64
    m = np.array([[t[c * 4 + r] for c in range(4)] for r in range(4)], dtype=tip)
    for r in range(3):
        # mathutils: float32 hücre okunur, Python float'ıyla (float64) çarpılır, float32'ye geri yazılır.
        m[r, 3] = tip(float(m[r, 3]) * INC)
    return m


def dunya_koseleri(t: list[float], koseler: list[list[float]], kip: str = "blender32") -> np.ndarray:
    """Yerel köşeleri dünya koordinatına (m) taşır. Dönüş float64 dizidir; blender32'de değerler float32'ye yuvarlıdır."""
    m = dunya_matrisi(t, kip)
    if not len(koseler):
        return np.zeros((0, 3))
    if kip == "float64":
        v = np.asarray(koseler, dtype=np.float64)
        return v @ m[:3, :3].T + m[:3, 3]
    v = np.asarray(koseler, dtype=np.float32)
    sonuc = np.empty((len(v), 3), dtype=np.float32)
    for r in range(3):
        toplam = np.zeros(len(v), dtype=np.float64)
        for c in range(3):
            toplam = toplam + (m[r, c] * v[:, c]).astype(np.float64)  # float32 çarpım, float64 toplam
        toplam = toplam + np.float64(m[r, 3] * np.float32(1.0))
        sonuc[:, r] = toplam.astype(np.float32)
    return sonuc.astype(np.float64)


def dugum_guid(kaynak_sha256: str, anahtar: str, kimlik) -> str:
    """Kalıcı IFC GlobalId: kaynak SHA256 + anahtar (model kodu ya da revizyon) + düğüm/nesne kimliği."""
    import ifcopenshell.guid

    return ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL, f"{kaynak_sha256}/{anahtar}/{kimlik}").hex)


def ucgen_sayisi(secili: dict) -> int:
    return sum(len(secili["meshes"][n["geometry"]]["triangles"]) for n in secili["nodes"])
