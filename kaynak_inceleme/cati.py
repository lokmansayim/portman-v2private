"""P9401 çatı seçenekleri (A–D): kaynak gövdenin korunması ve öneri parçalarının etiketi.

Seçenekler modele özgü tasarım ÖNERİLERİDİR (Codex devri; Lokman seçimi ve teknik değerlendirme bekliyor). B/C/D'deki
eğim, kot, parapet gibi değerler onaylı ölçü ya da genel katalog kuralı değildir. Bu modül yalnız şunu denetler:

  - kaynak gövde (çatı olmayan bütün düğümler ve ağları) seçenekte birebir aynı mı;
  - A kaynak çatıyı aynen taşıyor mu; B/C/D kaynak çatıyı çıkarıp yalnız `proposal` işaretli yeni parçalar mı ekliyor;
  - öneri parçaları kaynağa ait gibi görünmüyor mu (source_id yok, roof ve proposal işaretli, birim dönüşüm);
  - revizyon kimliği ve kaynak SHA256 doğru mu.
Öneri parçalarının kutusu ve üst kotu bilgi olarak yazılır; hüküm değildir.
"""
from __future__ import annotations

import numpy as np

BIRIM = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def govde_korunumu(kaynak: dict, secenek: dict, harf: str) -> dict:
    hatalar: list[str] = []
    rev = f"{kaynak['code']}-CATI-{harf}-01"
    if secenek.get("revision") != rev:
        hatalar.append(f"revizyon {secenek.get('revision')} ≠ {rev}")
    if secenek.get("source_sha256") != kaynak["source_sha256"]:
        hatalar.append("kaynak SHA256 farklı")
    kaynak_dugum = {n["id"]: n for n in kaynak["nodes"]}
    govde = [n for n in kaynak["nodes"] if not n["roof"]]
    kaynak_cati = [n for n in kaynak["nodes"] if n["roof"]]
    sec_dugum = {n["id"]: n for n in secenek["nodes"]}
    oneriler = [n for n in secenek["nodes"] if n.get("proposal")]
    kaynaktan = [n for n in secenek["nodes"] if not n.get("proposal")]

    # Gövde: her düğüm aynen, ağı aynen
    for n in govde:
        m = sec_dugum.get(n["id"])
        if m is None:
            hatalar.append(f"gövde düğümü eksik: {n['id']}")
        elif m != n:
            hatalar.append(f"gövde düğümü değişmiş: {n['id']}")
        elif secenek["meshes"].get(n["geometry"]) != kaynak["meshes"][n["geometry"]]:
            hatalar.append(f"gövde ağı değişmiş: {n['id']}")
    # Kaynak çatı: A'da aynen var, B/C/D'de yok
    cati_var = [n["id"] for n in kaynak_cati if n["id"] in sec_dugum]
    if harf == "A":
        if len(cati_var) != len(kaynak_cati) or any(sec_dugum[i] != kaynak_dugum[i] for i in cati_var):
            hatalar.append("A: kaynak çatı aynen taşınmıyor")
        if oneriler:
            hatalar.append("A: öneri parçası var")
    else:
        if cati_var:
            hatalar.append(f"{harf}: kaynak çatı düğümü kalmış: {cati_var}")
        if not oneriler:
            hatalar.append(f"{harf}: öneri parçası yok")
    # Kaynaktan gelen her düğüm gerçekten kaynakta aynı biçimde var (sessiz ekleme yok)
    for n in kaynaktan:
        if kaynak_dugum.get(n["id"]) != n:
            hatalar.append(f"kaynakta olmayan ya da farklı düğüm: {n['id']}")
    # Öneri parçaları kaynağa ait gibi görünmemeli
    ozet = []
    for n in oneriler:
        if n.get("source_id") is not None or not n["roof"] or n["world_transform"] != BIRIM or n["id"] in kaynak_dugum:
            hatalar.append(f"öneri etiketi tutarsız: {n['id']} {n['name']}")
        if n["geometry"] not in secenek["meshes"]:
            hatalar.append(f"öneri parçasının ağı yok: {n['id']} {n['name']}")
            continue
        v = np.asarray(secenek["meshes"][n["geometry"]]["vertices"], dtype=float)
        ozet.append({"id": n["id"], "ad": n["name"], "malzeme": n["material"],
                     "ucgen": len(secenek["meshes"][n["geometry"]]["triangles"]),
                     "kutu_m": [np.round(v.min(axis=0), 4).tolist(), np.round(v.max(axis=0), 4).tolist()]})
    return {"secenek": harf, "revizyon": secenek.get("revision"), "gecti": not hatalar, "hatalar": hatalar[:20],
            "govde_dugumu": len(govde), "kaynak_cati_dugumu": len(kaynak_cati), "tasinan_kaynak_cati": len(cati_var),
            "oneri_parcasi": len(oneriler), "oneriler": ozet,
            "kapsam": "Gövde korunumu ve etiket denetimi. Öneri ölçüleri onaylı değildir; teknik tasarım (taşıyıcı, drenaj, "
                      "katman) yapılmadı."}
