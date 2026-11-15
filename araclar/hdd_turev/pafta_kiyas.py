"""pafta_kiyas.py <geo.json> <ie.json> [<çıktı.json>]: paftanın pano dizilimi ↔ Motor'un pano dizilimi, duvar duvar; açıklıkların yeri.
Çerçeve: paftanın Motor çerçevesi (arka-sol: x soldan, y arkadan). Motor'un planı gerçek çerçevede (ön altta) → y = H − y."""
import json, sys
from pathlib import Path
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from motor import geometry as G

def temizle(ie):
    t = {k: v for k, v in ie.items() if not k.startswith("_")}
    t["acikliklar"] = [{k: v for k, v in a.items() if not k.startswith("_")} for a in ie["acikliklar"]]
    return t


def pafta_duvarlari(g):
    R = []
    for d in g["duvarlar"]:
        E = [d["a0"]] + [e for e in d["ekler"] if d["a0"] + 1 < e < d["a1"] - 1] + [d["a1"]]
        R.append({"yon": d["yon"], "c": d["c"], "aks": d.get("aks", d["c"]), "t": d["t"], "dis": d["dis"], "a0": d["a0"], "a1": d["a1"],
                  "parca": [(round(a, 1), round(b, 1)) for a, b in zip(E, E[1:])]})
    return R


def motor_duvarlari(plan):
    H = plan.H
    R = []
    for d in plan.duvarlar:
        if d.yon == "x":      # yatay (y sabit)
            yon, c = "y", H - d.c
            P = [(p.a0, p.a1, p.acilim, p.bosluk(p.acilim) if p.acilim else None) for p in d.panolar]
        else:
            yon, c = "x", d.c
            P = [(H - p.a1, H - p.a0, p.acilim, tuple(sorted(H - v for v in p.bosluk(p.acilim))) if p.acilim else None) for p in d.panolar]
        P.sort()
        R.append({"yon": yon, "c": round(c, 2), "tur": d.tur,
                  "parca": [(round(a, 1), round(b, 1)) for a, b, _, _ in P],
                  "aciklik": [(round(a, 1), round(b, 1), ac.tur, ac.olcu, round(g[0], 1), round(g[1], 1)) for a, b, ac, g in P if ac is not None]})
    return R


def karsilastir(g, ie):
    plan = G.kur(temizle(ie))
    PD, MD = pafta_duvarlari(g), motor_duvarlari(plan)
    satir, fark = [], 0
    for p in sorted(PD, key=lambda d: (d["yon"], d["c"], d["a0"])):
        lo, hi = p["a0"], p["a1"]
        m_parca = []
        for m in MD:
            if m["yon"] == p["yon"] and (abs(m["c"] - p["c"]) <= 3 or abs(m["c"] - p["aks"]) <= 3):
                m_parca += [q for q in m["parca"] if min(q[1], hi) - max(q[0], lo) > 3]
        m_parca.sort()
        boy_p = [round(b - a, 1) for a, b in p["parca"]]
        boy_m = [round(b - a, 1) for a, b in m_parca]
        # karşılaştırma: iç ek noktaları (uçlardaki köşe payları hariç), 1,5 cm toleransla
        ek_p = [b for a, b in p["parca"][:-1]]
        ek_m = [b for a, b in m_parca[:-1]]
        eksik = [e for e in ek_p if not any(abs(e - f) <= 1.5 for f in ek_m)]
        fazla = [f for f in ek_m if lo + 2 < f < hi - 2 and not any(abs(e - f) <= 1.5 for e in ek_p)]
        ayni = not eksik and not fazla
        fark += not ayni
        satir.append({"yon": p["yon"], "c": p["c"], "t": p["t"], "aralik": [lo, hi], "pafta": boy_p, "motor": boy_m,
                      "pafta_ek_motorda_yok": eksik, "motor_ek_paftada_yok": fazla, "ayni": ayni})
    ac_satir = []
    for a in ie["acikliklar"]:
        bas, bit = a["_pafta"]
        hy, hc, hk = (a["_hat"] + [None])[:3]
        bul = None
        for m in MD:
            if m["yon"] != hy or (abs(m["c"] - hc) > 3 and (hk is None or abs(m["c"] - hk) > 3)):
                continue
            for (x0, x1, tur, olcu, g0, g1) in m["aciklik"]:
                if tur == a["tur"] and min(x1, bit) - max(x0, bas) > 20:
                    # aynı hat; yazıdan okunan pencerenin paftadaki aralığı panodur, öteki açıklıklarınki boşluğun kendisi
                    bul = (m["yon"], m["c"], x0, x1) if a.get("_kaynak") == "yazi" else (m["yon"], m["c"], g0, g1)
        ac_satir.append({"tur": a["tur"], "yer": a.get("mahal") or a.get("arasi"), "pafta": [bas, bit], "motor": bul[2:] if bul else None,
                         "kayma": None if not bul else round((bul[2] + bul[3]) / 2 - (bas + bit) / 2, 1)})

    return satir, ac_satir, plan


if __name__ == '__main__':
    g = json.load(open(sys.argv[1]))
    ie = json.load(open(sys.argv[2]))
    satir, ac_satir, plan = karsilastir(g, ie)
    fark = sum(not s['ayni'] for s in satir)
    for s in satir:
        print("AYNI " if s["ayni"] else "FARK ", s["yon"], s["c"], s["t"], "pafta", s["pafta"], "| motor", s["motor"],
              "" if s["ayni"] else f"| eksik {s['pafta_ek_motorda_yok']} fazla {s['motor_ek_paftada_yok']}")
    print("duvar", len(satir), "farklı", fark)
    for s in ac_satir:
        print("açıklık", s["tur"], s["yer"], "pafta", s["pafta"], "motor", s["motor"], "kayma", s["kayma"])
    if len(sys.argv) > 3:
        json.dump({"duvarlar": satir, "acikliklar": ac_satir, "uyarilar": plan.uyarilar}, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
