"""6 Ekim 2026 denemesi: İş Emri → pano pano IFC4 modeli ve tek dosyalık 3D sayfası.

    python deneme/2026-10-06_kalinlik_160_100/ifc_3b.py [is_emri.json]

Model Motor'un deneme kopyasındaki `ifc_uret` ile kurulur: her pano ayrı bir IfcWall'dur (BOM kodu, boyu, kalınlığı üzerinde).
Sonra dosya yeniden açılır ve plan, Motor BOM'u ve görünüş paftasıyla karşılaştırılır. Görseller ayrı betikte (`ifc_gorsel.py`, Blender).
Canlı Motor'a dokunmaz. Çıktı: `cikti/<iş emri no>/ifc/`.
"""
from __future__ import annotations
import json, os, sys
from collections import Counter
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
CIKTI = BURASI / "cikti"
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(BURASI))
os.environ.setdefault("PORTMAN_REF_DIR", str(KOK / "kanal"))


def uret(is_emri_yolu: Path) -> dict:
    import yama
    yama.uret(CIKTI)
    sys.path.insert(0, str(CIKTI))
    from motor_k import geometry as G, ifc_uret
    from motor import ucb_sayfa
    import ifcopenshell, ifcopenshell.util.element as ue

    ie = json.loads(Path(is_emri_yolu).read_text(encoding="utf-8"))
    no = ie["is_emri_no"]; rev = int(ie.get("revizyon", 1))
    hedef = CIKTI / no / "ifc"; hedef.mkdir(parents=True, exist_ok=True)
    yol = hedef / f"Portman_{no}_r{rev:02d}.ifc"
    baslik = f"{ie.get('talep', {}).get('musteri_adi', '')} · {no} r{rev:02d}"
    ozet = ifc_uret.uret(json.loads(json.dumps(ie)), yol, baslik=baslik)

    # --- yeniden aç, say, planla karşılaştır
    f = ifcopenshell.open(str(yol))
    plan = G.kur(json.loads(json.dumps(ie)))
    duvarlar = f.by_type("IfcWall")
    boy_ifc = Counter(); kod_ifc = Counter()
    for w in duvarlar:
        ps = ue.get_psets(w)["PortatifEv_Pano"]
        boy_ifc[("dis" if ue.get_psets(w)["Pset_WallCommon"]["IsExternal"] else "ic", round(ps["Boy_cm"], 2), round(ps["Kalinlik_cm"], 2), round(ps["Yukseklik_cm"], 1))] += 1
        kod_ifc[ps["BOMKod"]] += 1
    H0 = float(ie["yapi"].get("duvar_yuksekligi_cm", 250))
    boy_plan = Counter((d.tur, round(p.boy, 2), round(2 * d.h, 2), round(H0, 1)) for d in plan.duvarlar for p in d.panolar)
    pen_plan = sum(1 for p in plan.panolar if p.acilim and p.acilim.tur == "pencere")
    kap_plan = sum(1 for p in plan.panolar if p.acilim and p.acilim.tur in ("ic_kapi", "dis_kapi"))
    denetim = {"pano_adedi": [len(duvarlar), len(plan.panolar)], "pano_boy_kalinlik_yukseklik": boy_ifc == boy_plan,
               "pencere": [len(f.by_type("IfcWindow")), pen_plan], "kapi": [len(f.by_type("IfcDoor")), kap_plan],
               "mahal": [len(f.by_type("IfcSpace")), sum(1 for m in plan.mahaller.values() if not m.acik)],
               "sema_hatasi": ozet["sema_hatasi"]}
    bom_yolu = CIKTI / no / "bom.json"
    if bom_yolu.exists():       # Motor'un DXF'ten saydığı pano kodlarıyla aynı mı?
        motor_bom = {k["kod"]: k["adet"] for k in json.loads(bom_yolu.read_text(encoding="utf-8"))["kalemler"] if k["kod"][0] in "DI"}
        denetim["pano_kodlari_motor_bom_ile_ayni"] = dict(kod_ifc) == motor_bom
    gor_yolu = CIKTI / no / "gorunus" / "gorunus_ozet.json"
    if gor_yolu.exists():       # görünüş paftasındaki dış pano boyları IFC'deki dış panolarla aynı mı?
        g = json.loads(gor_yolu.read_text(encoding="utf-8"))
        gor = Counter(round(b, 2) for boylar in g["cephe_pano_boylari_cm"].values() for b in boylar)
        ifc_dis = Counter()
        for (tur, b, _k, _y), n in boy_ifc.items():
            if tur == "dis":
                ifc_dis[b] += n
        denetim["dis_pano_boylari_gorunus_ile_ayni"] = gor == ifc_dis
        denetim["mahya_kotu_cm"] = [ozet["cati"]["mahya_cm"], round(g["cati"]["zm"], 1)]
    tamam = (denetim["pano_adedi"][0] == denetim["pano_adedi"][1] and denetim["pano_boy_kalinlik_yukseklik"]
             and denetim["pencere"][0] == denetim["pencere"][1] and denetim["kapi"][0] == denetim["kapi"][1]
             and denetim["mahal"][0] == denetim["mahal"][1] and denetim["sema_hatasi"] == 0
             and denetim.get("pano_kodlari_motor_bom_ile_ayni", True) and denetim.get("dis_pano_boylari_gorunus_ile_ayni", True)
             and (("mahya_kotu_cm" not in denetim) or abs(denetim["mahya_kotu_cm"][0] - denetim["mahya_kotu_cm"][1]) < 0.11))
    denetim["gecti"] = bool(tamam)

    html = hedef / f"Portman_{no}_r{rev:02d}_3B.html"
    ucb_sayfa.uret(yol, html, baslik=baslik)
    sinif = Counter(e.is_a() for e in f.by_type("IfcProduct"))
    sonuc = {"is_emri_no": no, "ifc": yol.name, "html": html.name, "ifc_bayt": yol.stat().st_size, "html_bayt": html.stat().st_size,
             "ozet": ozet, "siniflar": dict(sorted(sinif.items())), "denetim": denetim,
             "pano_tipleri": sorted({t.Name for t in f.by_type("IfcWallType")})}
    (hedef / "ifc_ozet.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc | {"hedef": str(hedef), "yol": str(yol)}


if __name__ == "__main__":
    yol = Path(sys.argv[1]) if len(sys.argv) > 1 else BURASI / "is_emri_3arti1_1150x1050.json"
    if not yol.is_absolute() and not yol.exists():
        yol = BURASI / yol
    s = uret(yol)
    print(json.dumps({k: s[k] for k in ("ifc", "ifc_bayt", "html_bayt", "ozet", "siniflar", "pano_tipleri", "denetim")}, ensure_ascii=False, indent=1))
    sys.exit(0 if s["denetim"]["gecti"] else 1)
