"""Astra'nın Blender modeli (DWG→Blender aktarımı) ↔ Portman IFC modeli (Motor İş Emri→IFC): eleman eleman kıyas.

Girdi:
  astra_detay.json  : Astra model.blend içindeki her nesnenin dünya kutusu + özellikleri (13_Kiyas/astra_detay.py döker)
  model_data.json   : Astra'nın aktarım verisi (eleman, açıklık, oda; kod ve koordinat)
  bizim .ifc        : cozumleyici/ifc_uret.py çıktısı (IfcOpenShell geometri motoruyla boşluk kesilerek üçgenlenir)
Çıktı: kiyas.json + kiyas_tablosu.csv (her Astra elemanı için eşleşen IFC ürünü, kutu farkı cm, hacim farkı %).

    python3 kiyas_astra.py astra_detay.json model_data.json bizim.ifc cikti_klasoru
"""
from __future__ import annotations
import csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import ifcopenshell.util.element as ue

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cozumleyici.ifc_gorsel import tessellate, hacim   # noqa: E402

TOL = 0.1   # cm; Astra'nın kendi sayısal toleransı (1 mm)


def kutu_birlesim(kutular):
    k = np.array(kutular, dtype=float)
    return [float(k[:, 0].min()), float(k[:, 1].min()), float(k[:, 2].min()), float(k[:, 3].max()), float(k[:, 4].max()), float(k[:, 5].max())]


def kutu_fark(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def astra_elemanlari(detay, md):
    """Her kaynak eleman: fiziksel mesh parçalarının dünya kutusu ve kutu-hacim toplamı (Astra parçaları eksen hizalı kutu)."""
    parca = defaultdict(list)
    for n in detay["nesneler"]:
        o = n["ozellik"]
        if n["tur"] != "MESH" or o.get("scope") != "physical" or not o.get("product_code"):
            continue
        parca[o["source_entity_id"]].append(n)
    el = {}
    for e in md["elements"]:
        ps = parca.get(e["entity_id"], [])
        kut = [p["kutu_cm"] for p in ps]
        hac = sum((k[3] - k[0]) * (k[4] - k[1]) * (k[5] - k[2]) for k in kut) / 1e6
        el[e["entity_id"]] = {"kod": e["product_code"], "tur": e["type"], "kaynak": e["source_path"], "parca": len(ps),
                              "parca_adlari": sorted(p["ozellik"].get("subpart_id", "") for p in ps),
                              "kutu": kutu_birlesim(kut) if kut else None, "hacim_m3": round(hac, 5)}
    ac = {}
    for o in md["openings"]:
        ps = parca.get(o["entity_id"], [])
        ac[o["entity_id"]] = {"kod": o["product_code"], "tur": o["type"], "kutu_plan": o["bounds_cm"], "en": o["width_cm"], "yuk": o["height_cm"],
                              "esik": o["sill_z_cm"], "parca": sorted(p["ozellik"].get("subpart_id", "") for p in ps),
                              "parca_kutu": kutu_birlesim([p["kutu_cm"] for p in ps]) if ps else None}
    return el, ac


def bizim_urunler(ifc_yol):
    f, shapes = tessellate(Path(ifc_yol))
    out = []
    for sh in shapes:
        e = f.by_id(sh["id"])
        v = sh["verts"].reshape(-1, 3) * 100.0
        ps = ue.get_psets(e)
        kod = ""
        for ad in ("PortatifEv_Pano", "PortatifEv_Dograma", "PortatifEv_Kapsam", "PortatifEv_Bosluk"):
            kod = kod or ps.get(ad, {}).get("BOMKod", "")
        out.append({"id": sh["id"], "sinif": e.is_a(), "ad": e.Name, "kod": kod,
                    "kutu": [round(float(x), 3) for x in list(v.min(axis=0)) + list(v.max(axis=0))],
                    "hacim_m3": round(abs(hacim(sh["verts"], sh["faces"])), 5), "psets": ps})
    return f, out


def kiyasla(detay, md, ifc_yol):
    A_el, A_ac = astra_elemanlari(detay, md)
    f, B = bizim_urunler(ifc_yol)
    fiziksel = [b for b in B if b["sinif"] in ("IfcWall", "IfcMember", "IfcColumn", "IfcBeam") and b["kod"]]
    bos = [b for b in B if b["sinif"] == "IfcOpeningElement"]
    dograma = [b for b in B if b["sinif"] in ("IfcWindow", "IfcDoor")]
    satirlar, kullanilan = [], set()
    for eid, a in A_el.items():
        aday = [b for b in fiziksel if b["id"] not in kullanilan and b["kod"] == a["kod"]]
        if a["kutu"] is None:
            # Astra'da 3B gövdesi olmayan (yalnız referans çizgisi) eleman: plan kutusu model_data'dan
            e = next(x for x in md["elements"] if x["entity_id"] == eid)
            pts = [p for s in e.get("source_lines", []) for p in s["points"]]
            plan = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
            en_iyi = min(aday, key=lambda b: kutu_fark(plan, [b["kutu"][0], b["kutu"][1], b["kutu"][3], b["kutu"][4]]), default=None)
            fark = kutu_fark(plan, [en_iyi["kutu"][0], en_iyi["kutu"][1], en_iyi["kutu"][3], en_iyi["kutu"][4]]) if en_iyi else None
            if en_iyi: kullanilan.add(en_iyi["id"])
            satirlar.append({"astra_kaynak": a["kaynak"], "kod": a["kod"], "tur": a["tur"], "astra_kutu_cm": plan, "astra_3B": "yok (referans çizgisi)",
                             "bizim": en_iyi and en_iyi["ad"], "bizim_sinif": en_iyi and en_iyi["sinif"], "bizim_kutu_cm": en_iyi and en_iyi["kutu"],
                             "plan_kutu_fark_cm": fark and round(fark, 3), "kutu_fark_cm": None, "astra_hacim_m3": 0.0,
                             "bizim_hacim_m3": en_iyi and en_iyi["hacim_m3"], "hacim_fark_yuzde": None,
                             "durum": "plan eşleşti; Astra 3B yok" if fark is not None and fark <= TOL else "FARK"})
            continue
        en_iyi = min(aday, key=lambda b: kutu_fark(a["kutu"], b["kutu"]), default=None)
        fark = kutu_fark(a["kutu"], en_iyi["kutu"]) if en_iyi else None
        plan_fark = kutu_fark([a["kutu"][i] for i in (0, 1, 3, 4)], [en_iyi["kutu"][i] for i in (0, 1, 3, 4)]) if en_iyi else None
        if en_iyi: kullanilan.add(en_iyi["id"])
        hf = round((en_iyi["hacim_m3"] / a["hacim_m3"] - 1) * 100, 3) if en_iyi and a["hacim_m3"] else None
        if fark is not None and fark <= TOL and (hf is None or abs(hf) <= 0.5):
            durum = "AYNI"
        elif plan_fark is not None and plan_fark <= TOL:
            durum = "plan aynı; kot/hacim farklı"
        else:
            durum = "FARK"
        satirlar.append({"astra_kaynak": a["kaynak"], "kod": a["kod"], "tur": a["tur"], "astra_kutu_cm": a["kutu"], "astra_3B": ",".join(a["parca_adlari"]),
                         "bizim": en_iyi and en_iyi["ad"], "bizim_sinif": en_iyi and en_iyi["sinif"], "bizim_kutu_cm": en_iyi and en_iyi["kutu"],
                         "plan_kutu_fark_cm": plan_fark and round(plan_fark, 3), "kutu_fark_cm": fark and round(fark, 3),
                         "astra_hacim_m3": a["hacim_m3"], "bizim_hacim_m3": en_iyi and en_iyi["hacim_m3"], "hacim_fark_yuzde": hf, "durum": durum})
    artan = [b for b in fiziksel if b["id"] not in kullanilan]
    # açıklıklar: Astra plan kutusu + eşik/üst kot ↔ bizim IfcOpeningElement (boşluk) kutusu
    ac_satir, kul2 = [], set()
    for eid, a in A_ac.items():
        k = a["kutu_plan"]; z0, z1 = a["esik"], a["esik"] + a["yuk"]
        hedef = [k[0], k[1], z0, k[2], k[3], z1]
        def fark_b(b):
            bb = b["kutu"]; x0, y0, x1, y1 = bb[0], bb[1], bb[3], bb[4]
            # boşluk duvarı ±2 cm aşar: kalınlık doğrultusunda duvar yüzüne kırp
            if (k[2] - k[0]) < (k[3] - k[1]): x0, x1 = max(x0, k[0]), min(x1, k[2])
            else: y0, y1 = max(y0, k[1]), min(y1, k[3])
            return kutu_fark(hedef, [x0, y0, bb[2], x1, y1, bb[5]])
        en = min((b for b in bos if b["id"] not in kul2), key=fark_b, default=None)
        fk = fark_b(en) if en else None
        if en: kul2.add(en["id"])
        dol = None
        if en:
            o = f.by_id(en["id"])
            dol = [r.RelatedBuildingElement.is_a() + ":" + (r.RelatedBuildingElement.Name or "") for r in o.HasFillings] or ["dolgu yok"]
        ac_satir.append({"kod": a["kod"], "tur": a["tur"], "astra_plan_kutu": k, "astra_kot": [z0, z1], "astra_en": a["en"],
                         "bizim_bosluk": en and en["ad"], "bizim_kutu": en and en["kutu"], "fark_cm": fk and round(fk, 3), "bizim_dolgu": dol,
                         "durum": "AYNI" if fk is not None and fk <= TOL else "FARK"})
    # odalar
    od = []
    ifc_alan = {}
    for s in f.by_type("IfcSpace"):
        ps = ue.get_psets(s)
        ifc_alan["".join((s.LongName or "").split())] = ps.get("Qto_SpaceBaseQuantities", {}).get("NetFloorArea")
    for r in md["rooms"]:
        b = ifc_alan.get("".join(r["name"].split()))
        od.append({"oda": r["name"], "astra_m2": round(r["area_m2"], 4), "bizim_m2": b, "fark_m2": None if b is None else round(b - r["area_m2"], 4)})
    ozet = {
        "eleman": {"astra": len(A_el), "eslesen_AYNI": sum(s["durum"] == "AYNI" for s in satirlar),
                   "plan_ayni_kot_farkli": sum(s["durum"].startswith("plan aynı") for s in satirlar),
                   "astra_3B_yok": sum(s["durum"].startswith("plan eşleşti") for s in satirlar), "FARK": sum(s["durum"] == "FARK" for s in satirlar),
                   "bizde_fazla": [(b["sinif"], b["ad"], b["kod"]) for b in artan]},
        "aciklik": {"astra": len(A_ac), "AYNI": sum(s["durum"] == "AYNI" for s in ac_satir), "FARK": sum(s["durum"] == "FARK" for s in ac_satir)},
        "oda_max_fark_m2": max(abs(o["fark_m2"]) for o in od if o["fark_m2"] is not None),
        "astra_kod": dict(Counter(a["kod"] for a in A_el.values()) + Counter(a["kod"] for a in A_ac.values() if a["kod"])),
        "bizim_kod": dict(Counter(b["kod"] for b in fiziksel) + Counter(b["psets"].get("PortatifEv_Dograma", {}).get("BOMKod") for b in dograma)),
        "bizde_ek_nesne": dict(Counter(b["sinif"] for b in B if not b["kod"] and b["sinif"] not in ("IfcOpeningElement",))),
    }
    return {"ozet": ozet, "elemanlar": satirlar, "acikliklar": ac_satir, "odalar": od}


if __name__ == "__main__":
    detay = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    md = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
    k = kiyasla(detay, md, sys.argv[3])
    (out / "kiyas.json").write_text(json.dumps(k, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(out / "kiyas_tablosu.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Kod", "Tür", "Astra kaynak", "Astra 3B parçalar", "Bizim IFC ürünü", "IFC sınıfı", "Plan kutu farkı cm", "3B kutu farkı cm",
                    "Astra hacim m³", "Bizim hacim m³", "Hacim farkı %", "Durum"])
        for s in sorted(k["elemanlar"], key=lambda s: (s["durum"] != "FARK", s["kod"])):
            w.writerow([s["kod"], s["tur"], s["astra_kaynak"], s["astra_3B"], s["bizim"], s["bizim_sinif"], s["plan_kutu_fark_cm"], s["kutu_fark_cm"],
                        s["astra_hacim_m3"], s["bizim_hacim_m3"], s["hacim_fark_yuzde"], s["durum"]])
        w.writerow([])
        w.writerow(["Kod", "Tür", "Astra plan kutusu", "Astra kot (eşik–üst)", "Bizim boşluk", "Fark cm", "Bizim dolgu", "Durum"])
        for s in k["acikliklar"]:
            w.writerow([s["kod"], s["tur"], s["astra_plan_kutu"], s["astra_kot"], s["bizim_bosluk"], s["fark_cm"], " / ".join(s["bizim_dolgu"] or []), s["durum"]])
        w.writerow([])
        w.writerow(["Oda", "Astra m²", "Bizim m²", "Fark m²"])
        for o in k["odalar"]:
            w.writerow([o["oda"], o["astra_m2"], o["bizim_m2"], o["fark_m2"]])
    print(json.dumps(k["ozet"], ensure_ascii=False, indent=1))
