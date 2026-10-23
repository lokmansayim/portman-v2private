"""Portman motor v1 — kaydedilmiş DXF'in bağımsız doğrulaması.

Yeniden açılan DXF'ten pano/köşe/açıklık/alan bilgisi okunur ve Plan beklentileriyle (ve varsa altın
beklentilerle) karşılaştırılır. Kod, çizen fonksiyonların ara sonuçlarına değil dosyaya bakar.
"""
from __future__ import annotations
import collections
import re
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

from . import geometry as G



def _bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _rects_of_insert(e):
    return [_bbox(list(s.get_points("xy"))) for s in e.virtual_entities() if s.dxftype() == "LWPOLYLINE" and s.dxf.layer == "0"]


def dogrula(doc, plan: G.Plan, is_emri: dict) -> dict:
    msp = doc.modelspace(); W, H = plan.W, plan.H
    WALL_LAYERS = {G.katman("IC_DUVAR_60"), G.katman("DIS_DUVAR_100")}
    KOSE_LAYERS = {G.katman("KOSE_PROFIL_60"), G.katman("KOSE_PROFIL_100")}
    limit = W + 150.0   # ana plan bölgesi (kopya sağda +300)
    hatalar = []
    # İE-11: boşluğu panoda kaydırılmış açıklıklar (kapı mantığı); anahtar yoksa hepsi 0 → eski denetim
    _r3 = lambda r: tuple(round(v, 3) for v in r)
    kayma_of = {_r3(pn.rect()): pn.acilim.kayma for pn in plan.panolar if pn.acilim and abs(pn.acilim.kayma) > 1e-9}
    panels, koseler, gaps = [], [], []
    kinds = collections.Counter()
    for e in msp:
        if e.dxftype() != "INSERT":
            continue
        L = e.dxf.layer
        if L in WALL_LAYERS or L in KOSE_LAYERS:
            rs = _rects_of_insert(e)
            if not rs:
                hatalar.append(f"Blok malzeme geometrisi yok: {e.dxf.name}"); continue
            outer = _bbox([(r[0], r[1]) for r in rs] + [(r[2], r[3]) for r in rs])
            if outer[0] > limit:
                continue
            if L in KOSE_LAYERS:
                koseler.append(outer); continue
            for s in ("xscale", "yscale", "zscale"):
                if abs(abs(e.dxf.get(s, 1)) - 1) > 1e-9:
                    hatalar.append(f"Ölçekli pano: {e.dxf.name}")
            th = G.T_IC if L == G.katman("IC_DUVAR_60") else G.T_DIS
            if abs(min(outer[2] - outer[0], outer[3] - outer[1]) - th) > 1e-6:
                hatalar.append(f"Duvar kalınlığı uyuşmuyor: {e.dxf.name} {outer}")
            panels.append({"name": e.dxf.name, "layer": L, "rect": outer, "rects": rs})
            if len(rs) == 2:
                a, b = sorted(rs)
                vertical = outer[3] - outer[1] > outer[2] - outer[0]
                gap = (outer[0], a[3], outer[2], b[1]) if vertical else (a[2], outer[1], b[0], outer[3])
                length = (gap[3] - gap[1]) if vertical else (gap[2] - gap[0])
                mid_gap = ((gap[1] + gap[3]) / 2) if vertical else ((gap[0] + gap[2]) / 2)
                mid_pan = ((outer[1] + outer[3]) / 2) if vertical else ((outer[0] + outer[2]) / 2)
                if abs(mid_gap - mid_pan - kayma_of.get(_r3(outer), 0.0)) > 1e-6:
                    hatalar.append(f"Açıklık panoda merkezlenmemiş: {e.dxf.name}" if not kayma_of else f"Açıklık Plan'daki yerinde değil: {e.dxf.name}")
                toks = e.dxf.name.split("_")
                tok = next((t for t in toks if t in ("P01", "P02", "P03", "K01", "K02", "K03", "OPEN") or re.fullmatch(r"P\d+x\d+", t)), "?")   # BK-13: P150x140
                kind = "pencere" if tok.startswith("P") else ("gecis" if tok == "OPEN" else "kapi")
                kinds[kind] += 1
                gaps.append({"kind": kind, "name": e.dxf.name, "gap": gap, "length": round(length, 6)})
            elif len(rs) > 2:
                hatalar.append(f"Beklenmeyen pano yapısı: {e.dxf.name}")
    # çakışma
    rects = [r for p in panels for r in p["rects"]] + koseler
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6:
                hatalar.append(f"Duvar çakışması: {a} / {b}")
    # ayak izi: Plan'ın kendi hesabıyla birebir olmalı (dosya ↔ model)
    fp_file = unary_union([box(*r) for r in rects] + [box(*g["gap"]) for g in gaps])
    fp_solid = unary_union([box(*r) for r in rects] + [box(*g["gap"]) for g in gaps if g["kind"] != "gecis"])   # geçiş boşluğu alana dahil olabilir
    fp_plan = plan.footprint()
    fp_diff = fp_file.symmetric_difference(fp_plan).area
    if fp_diff > 1e-6:
        hatalar.append(f"Dosya ayak izi Plan ile uyuşmuyor (fark {fp_diff:.6f} cm²)")
    ext = _bbox([(r[0], r[1]) for r in rects] + [(r[2], r[3]) for r in rects])
    if G.geometri_anahtari_var(is_emri):
        # İE-11: açık mahal (veranda) dış duvarsız kenara dayanabilir; duvar kutusu Plan ayak iziyle, ayak izi ∪ açık mahaller (0,0,W,H) ile denetlenir
        # (yalnız geometri anahtarıyla; 250 dışı yükseklik tek başına bu kuralı değiştirmez — hakem 2. tur, önemli 1)
        if max(abs(a - b) for a, b in zip(ext, fp_plan.bounds)) > 1e-6:
            hatalar.append(f"Duvarların kutusu {ext} Plan ayak izi {fp_plan.bounds} ile uyuşmuyor")
        tum = unary_union([fp_plan] + [m.poly for m in plan.mahaller.values() if m.acik]).bounds
        if max(abs(a - b) for a, b in zip(tum, (0, 0, W, H))) > 1e-6:
            hatalar.append(f"Dış ölçüler {tum} beklenen (0,0,{W},{H})")
    elif max(abs(a - b) for a, b in zip(ext, (0, 0, W, H))) > 1e-6:                   # eski kural (anahtarsız İş Emri; bayt bayt)
        hatalar.append(f"Dış ölçüler {ext} beklenen (0,0,{W},{H})")
    # net alanlar (ana plan)
    areas = {}
    for e in msp.query('LWPOLYLINE[layer=="NET_ALAN_GEOMETRISI"]'):
        pts = list(e.get_points("xy"))
        if min(p[0] for p in pts) > limit:
            continue
        name = e.get_xdata("PORTMAN_ROOM")[0].value
        poly = Polygon(pts)
        areas[name] = poly.area / 10000.0
        # oda poligonu duvar içine girmemeli
        if poly.intersection(fp_solid).area > 1e-6:
            hatalar.append(f"{name} net alanı duvar/eşik içeriyor")
    for name, m in plan.mahaller.items():
        if name not in areas:
            hatalar.append(f"Net alan geometrisi eksik: {name}")
        elif abs(areas[name] - m.alan_m2) > 1e-6:
            hatalar.append(f"{name} alanı dosyada {areas[name]} / planda {m.alan_m2}")
    # alan yazıları
    texts = [t.dxf.text for t in msp.query('TEXT[layer=="ODA_ADLARI"]')]
    for name, a in areas.items():
        lbl = f"{a:.2f}".replace(".", ",") + " m²"
        if lbl not in texts:
            hatalar.append(f"Alan yazısı yok: {name} {lbl}")
    # ölçü nesneleri
    meas = [round(float(d.get_measurement()), 6) for d in msp.query("DIMENSION") if d.dimtype in (0, 1)]
    for need in (W, H):
        if round(need, 6) not in meas:
            hatalar.append(f"Gerçek dış ölçü nesnesi yok: {need}")
    # İE-11 `dizilim.kapi: mantik`: kapı kanadının süpürdüğü alan (kare, kanat boyu) başka kanatla ya da duvarla çakışmaz
    if ((is_emri.get("yapi", {}).get("dizilim") or {}).get("kapi")) == "mantik":
        sup = []
        for pn in plan.panolar:
            ac = pn.acilim
            if not ac or ac.tur not in ("ic_kapi", "dis_kapi") or not ac.icine_normal:
                continue
            g = pn.gap(); dd = pn.duvar; w = ac.genislik; n = ac.icine_normal
            if dd.yon == "y":
                x0 = dd.c + dd.h if n == "+x" else dd.c - dd.h - w
                sup.append((pn, box(x0, g[1], x0 + w, g[3])))
            else:
                y0 = dd.c + dd.h if n == "+y" else dd.c - dd.h - w
                sup.append((pn, box(g[0], y0, g[2], y0 + w)))
        duvar_govde = unary_union([box(*r) for p_ in panels for r in p_["rects"]] + [box(*k) for k in koseler])
        for i, (pa, ba) in enumerate(sup):
            if ba.intersection(duvar_govde).area > 1e-6:
                hatalar.append(f"Kapı kanadı duvara çarpıyor: {'–'.join(pa.acilim.arasi)}")
            for pb, bb in sup[i + 1:]:
                if ba.intersection(bb).area > 1e-6:
                    hatalar.append(f"Kapı kanatları çakışıyor: {'–'.join(pa.acilim.arasi)} / {'–'.join(pb.acilim.arasi)}")
    # H bağlantıları
    hs = [e for e in msp.query(f'INSERT[layer=="{G.katman("IC_UCLU_H_60")}"]') if e.dxf.insert.x < limit]
    hs_dis = [e for e in msp.query(f'INSERT[layer=="{G.katman("DIS_UCLU_H_100")}"]') if e.dxf.insert.x < limit]   # İE-11
    if len(hs) + len(hs_dis) != len(plan.h_baglantilar):
        hatalar.append(f"H bağlantı sayısı {len(hs)} iç + {len(hs_dis)} dış / beklenen {len(plan.h_baglantilar)}")
    if len(hs_dis) != sum(1 for h in plan.h_baglantilar if h.tur == "dis"):
        hatalar.append(f"Dış üçlü H sayısı {len(hs_dis)} / beklenen {sum(1 for h in plan.h_baglantilar if h.tur == 'dis')}")
    for e, dis in [(e, False) for e in hs] + [(e, True) for e in hs_dis]:
        x, y, rot = e.dxf.insert.x, e.dxf.insert.y, e.dxf.rotation
        dx, dy = {0.0: (1, 0), 90.0: (0, 1), 180.0: (-1, 0), 270.0: (0, -1)}[rot % 360]
        # üç kanalda gerçek pano: gövde iki yanı ve kol yönünde; dış H'de kol sondası dış duvar gövdesini (T_DIS/2) aşar, gövde arkası da sınanır
        kol = (G.T_DIS / 2.0 + 1.0) if dis else 4.0
        probes = [(x + dy, y - dx), (x - dy, y + dx), (x + kol * dx, y + kol * dy)] + ([(x - dx, y - dy)] if dis else [])
        ok = [any(r[0] - 1e-7 <= px <= r[2] + 1e-7 and r[1] - 1e-7 <= py <= r[3] + 1e-7 for r in rects) for px, py in probes]
        if not all(ok):
            hatalar.append(f"H bağlantısı ({x},{y}) kanallarında pano yok: {ok}")
    # beklenen adetler
    exp_pen = sum(1 for p in plan.panolar if p.acilim and p.acilim.tur == "pencere")
    exp_kap = sum(1 for p in plan.panolar if p.acilim and p.acilim.tur in ("ic_kapi", "dis_kapi"))
    exp_gec = sum(1 for p in plan.panolar if p.acilim and p.acilim.tur == "gecis")
    if kinds["pencere"] != exp_pen or kinds["kapi"] != exp_kap or kinds["gecis"] != exp_gec:
        hatalar.append(f"Açıklık adedi dosya {dict(kinds)} / plan pencere {exp_pen} kapı {exp_kap} geçiş {exp_gec}")
    if len(panels) != len(plan.panolar):
        hatalar.append(f"Pano adedi dosya {len(panels)} / plan {len(plan.panolar)}")
    # altın beklentiler (varsa)
    altin = is_emri.get("altin_beklenti")
    altin_sonuc = None
    if altin:
        altin_sonuc = {}
        if "pano" in altin: altin_sonuc["pano"] = (len(panels) == altin["pano"])
        if "pencere" in altin: altin_sonuc["pencere"] = (kinds["pencere"] == altin["pencere"])
        if "kapi" in altin: altin_sonuc["kapi"] = (kinds["kapi"] == altin["kapi"])
        if "gecis" in altin: altin_sonuc["gecis"] = (kinds["gecis"] == altin["gecis"])
        if "bom_counts" in altin:
            got = bom_sayim(doc); altin_sonuc["bom_counts"] = (got == altin["bom_counts"])
            if got != altin["bom_counts"]:
                diff = {k: (got.get(k), altin["bom_counts"].get(k)) for k in set(got) | set(altin["bom_counts"]) if got.get(k) != altin["bom_counts"].get(k)}
                hatalar.append(f"ALTIN BOM sayımı farkı (dosya, beklenen): {diff}")
        if "panel_rects" in altin:
            got_r = sorted([list(map(lambda v: round(v, 3), p["rect"])) for p in panels])
            altin_sonuc["panel_rects"] = (got_r == [list(map(float, r)) for r in altin["panel_rects"]])
        if "corner_rects" in altin:
            got_c = sorted([list(map(lambda v: round(v, 3), c)) for c in koseler])
            altin_sonuc["corner_rects"] = (got_c == [list(map(float, r)) for r in altin["corner_rects"]])
        if "gaps" in altin:
            got_g = sorted([list(map(lambda v: round(v, 3), g["gap"])) for g in gaps])
            altin_sonuc["gaps"] = (got_g == [list(map(float, r)) for r in altin["gaps"]])
        if "dis_olcu" in altin: altin_sonuc["dis_olcu"] = ([W, H] == altin["dis_olcu"])
        if "alanlar" in altin:
            tol = float(altin.get("alan_toleransi_m2", 1e-6))
            altin_sonuc["alanlar"] = all(abs(areas.get(k, -1) - v) <= tol + 1e-9 for k, v in altin["alanlar"].items())
        if "footprint" in altin:
            exp = unary_union([box(*r) for r in altin["footprint"]])
            altin_sonuc["footprint"] = exp.symmetric_difference(fp_file).area < 1e-6
        for k, v in altin_sonuc.items():
            if not v:
                hatalar.append(f"ALTIN TEST başarısız: {k}")
    return {"passed": not hatalar, "errors": hatalar, "outer_cm": [W, H], "panel_grid": [plan.nx, plan.ny], "units": "cm",
            "panel_count": len(panels), "corner_count": len(koseler), "windows": kinds["pencere"], "doors": kinds["kapi"],
            "openings": gaps, "rooms_m2": {k: round(v, 6) for k, v in areas.items()}, "h_connectors": len(hs) + len(hs_dis), **({"h_connectors_dis": len(hs_dis)} if hs_dis else {}),
            "footprint_diff_cm2": round(fp_diff, 6), "wall_overlap": not any("çakışması" in h for h in hatalar),
            "altin": altin_sonuc, "warnings": plan.uyarilar,
            "scope": "Ön onay taslağı; statik, üretim, BOM veya yeni oda tasarımı değildir"}


def bom_sayim(doc) -> dict:
    """Dosyadaki ANA rolündeki üst BOM_ INSERT'lerini ve içlerindeki doğrama INSERT'lerini koda göre sayar."""
    counts = {}
    for e in doc.modelspace():
        if e.dxftype() != "INSERT" or not e.dxf.name.startswith("BOM_") or not e.has_xdata("AI_BOM"):
            continue
        xd = [t.value for t in e.get_xdata("AI_BOM")]
        if len(xd) < 2 or xd[1] != "ANA":
            continue
        counts[xd[0]] = counts.get(xd[0], 0) + 1
        for s in doc.blocks[e.dxf.name]:
            if s.dxftype() == "INSERT" and s.dxf.name.startswith("BOM_"):
                k2 = s.dxf.name.split("_")[1]; counts[k2] = counts.get(k2, 0) + 1
    return dict(sorted(counts.items()))
