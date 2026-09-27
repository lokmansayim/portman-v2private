"""Motor İş Emri → blender_girdi.json (ifc_uret.py / blender_ciz.py girdisi). Kaynak: Motor'un kurallı planı (bayi PDF'i değil).

Pano, açıklık, köşe, üçlü H, dikme ve veranda profili Motor'un DXF'e yazdığı BOM kodlarıyla aynı kodu taşır.
Böylece IFC'den sayılan BOM, Motor DXF BOM'u ve Astra'nın DWG BOM'u kod kod karşılaştırılabilir.

    python3 cozumleyici/motor_girdi.py is_emri/YAN_VERANDALI_2plus1_6x8p5.json cikti/kiyas_yan/motor_girdi.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import ezdxf
from ezdxf import bbox as ebbox
from shapely.ops import polylabel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from motor import geometry as G                     # noqa: E402
from motor.dxf_out import Cizici                    # noqa: E402
from motor.katalog import Katalog                   # noqa: E402
from cozumleyici.blender_hazirla import PENCERE_ESIK, KAPI_UST, DUVAR_H, LENTO, pano_sinifi, _r   # noqa: E402


def hazirla(ie: dict) -> dict:
    plan = G.kur(ie)
    kat = Katalog()
    c = Cizici(plan, kat)
    c.ciz_plan(0.0, 0.0, "ANA", "", "")          # BOM kodlu INSERT'ler (yalnız ANA rolü)
    etiket = {"".join(k.split()): v for k, v in ie.get("altin_beklenti", {}).get("alanlar", {}).items()}

    def kalem(kod):
        m = kat.malzemeler.get(kod, {})
        return f"{kod} {m.get('label', '')}".strip()

    panolar, acikliklar = [], []
    for d in plan.duvarlar:
        for p in d.panolar:
            _, _, kod = c.pano_blok(p)
            x0, y0, x1, y1 = p.rect()
            L, t = p.boy, 2 * d.h
            pr = {"id": len(panolar), "rect": [_r(x0), _r(y0), _r(x1), _r(y1)], "yon": d.yon, "boy": _r(L), "kalinlik": _r(t),
                  "tur": d.tur, "sinif": pano_sinifi(L, t), "kod": kod, "kalem": kalem(kod), "acikliklar": []}
            ac = p.acilim
            if ac is not None:
                g = p.gap()
                a0, a1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
                if ac.tur == "pencere":
                    en, boy = G.PENCERE_OLCULERI[ac.olcu]
                    z0 = PENCERE_ESIK[ac.olcu]; z1 = min(z0 + boy, KAPI_UST)
                    dk = c.dograma[ac.olcu][1]
                    a = {"tur": "pencere", "olcu": ac.olcu}
                else:
                    z0, z1 = 0.0, KAPI_UST
                    dk = c.dograma["ic82"][1] if ac.tur == "ic_kapi" else (c._dis_kapi_blok(ac.genislik)[1] if ac.tur == "dis_kapi" else None)
                    a = {"tur": "kapi", "alt_tur": ac.tur, "genislik": _r(ac.genislik)}
                a.update({"yon": d.yon, "a0": _r(a0), "a1": _r(a1), "c": _r(d.c), "z0": z0, "z1": z1, "panolar": [pr["id"]],
                          "kod": dk, "kalem": kalem(dk) if dk else "Kapısız geçiş (malzeme değil)", "arasi": list(ac.arasi) if ac.arasi else None,
                          "mahal": ac.mahal})
                pr["acikliklar"].append({"aciklik": len(acikliklar), "a0": a["a0"], "a1": a["a1"], "z0": z0, "z1": z1})
                acikliklar.append(a)
            panolar.append(pr)

    # bağlantı / dikme / veranda profili: Motor DXF'indeki ANA INSERT'lerden (kod + gerçek blok geometrisinin kutusu)
    baglantilar = []
    for e in c.msp.query("INSERT"):
        if not e.has_xdata("AI_BOM"):
            continue
        kod, rol = [v for _, v in e.get_xdata("AI_BOM")]
        if rol != "ANA" or kod[0] not in "BV":
            continue
        bb = ebbox.extents([e])
        x0, y0, x1, y1 = bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y
        m = kat.malzemeler.get(kod, {}); lab = m.get("label", "")
        tur = "dikme" if "dikme" in lab.lower() else ("veranda_profil" if kod[0] == "V" else "baglanti")
        baglantilar.append({"kod": kod, "kalem": kalem(kod), "tur": tur, "rect": [_r(x0), _r(y0), _r(x1), _r(y1)], "blok": e.dxf.name})

    odalar, veranda = [], None
    for ad, m in plan.mahaller.items():
        poly = m.poly.simplify(0.0)
        pl = polylabel(poly, tolerance=1.0)
        kayit = {"ad": ad, "etiket_m2": etiket.get("".join(ad.split())), "net_m2": _r(m.alan_m2, 4), "etiket_xy": [_r(pl.x), _r(pl.y)],
                 "poligon": [[_r(x), _r(y)] for x, y in list(poly.exterior.coords)[:-1]]}
        if m.acik:
            veranda = dict(kayit, tip="bina_ici", tasma_cm=0.0)
        else:
            odalar.append(kayit)

    cati = ie.get("cati", {})
    return {
        "sema": "portman.blender_girdi/0.2",
        "kaynak": {"dosya": f"İş Emri {ie.get('is_emri_no')} r{int(ie.get('revizyon', 1)):02d}",
                   "not": "Motor'un kurallı planı (G.kur). Kodlar Motor DXF'indeki BOM bloklarıyla aynı."},
        "kapsam": {"ic_kapi": True, "gecis_malzeme_degil": True},
        "bina": {"ad": f"{ie.get('talep', {}).get('musteri_adi', '')} — {ie['yapi']['grid']['x_pano']}×{ie['yapi']['grid']['y_pano']} pano",
                 "W": _r(plan.W), "H": _r(plan.H), "duvar_h": float(ie["yapi"].get("duvar_yuksekligi_cm", DUVAR_H)), "lento": LENTO,
                 "cati": {"tip": cati.get("tip", "besik"), "egim": float(cati.get("egim_yuzde", 33)) / 100, "sacak": float(cati.get("sacak_cm", 30)),
                          "topuk": float(cati.get("topuk_cm", 10)), "makas_yonu": "x (kısa kenar)", "renk": "antrasit"}},
        "panolar": panolar, "acikliklar": acikliklar, "baglantilar": baglantilar, "odalar": odalar, "veranda": veranda, "tefris": [],
        "kanit": {"motor_uyarilari": plan.uyarilar}, "uyari": [],
    }


if __name__ == "__main__":
    ie = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    g = hazirla(ie)
    Path(sys.argv[2]).write_text(json.dumps(g, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("pano", len(g["panolar"]), Counter(p["kod"] for p in g["panolar"]))
    print("açıklık", len(g["acikliklar"]), Counter(a["kod"] for a in g["acikliklar"]))
    print("bağlantı", len(g["baglantilar"]), Counter(b["kod"] for b in g["baglantilar"]))
    print("oda", [(o["ad"], o["net_m2"], o["etiket_m2"]) for o in g["odalar"]], "veranda", g["veranda"] and g["veranda"]["net_m2"])
