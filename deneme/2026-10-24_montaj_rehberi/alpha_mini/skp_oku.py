"""SKP -> dünya uzayında (cm) yüzey ve kenar listesi. openskp 1.3.0 çekirdeğini kullanır."""
import sys, json, gzip, math, collections
import numpy as np
from openskp import _core

INC2CM = 2.54
KIMLIK = [1.0,0,0, 0,1.0,0, 0,0,1.0, 0,0,0, 1.0]

def oku(yol, tanim_atla=("Heather","Lily","Sang","Steve","Susan","Derrick","Bryce","Nancy","Chris","Laura","Sophie","Stacy","Helen","Shinji","Ankur","Niraj","Scott","Rana","Sumele")):
    p = _core.full_parse(yol)
    defs = p["defs_dict"]
    lid = p["layer_id_to_name"]; mid = p.get("material_id_to_name", {})
    yuzler = []; kenarlar = []; dugumler = []
    atlanan = collections.Counter()
    def yuru(def_id, M, yol_ad, derinlik, ust_katman):
        d = defs.get(def_id)
        if d is None: return
        b = d["builder"]
        V = {vid: np.array(_core.transform_point(v, M))*INC2CM for vid, v in b.vertices.items()}
        E = b.edges
        for fid, f in b.faces.items():
            halkalar = []
            for loop in f["loops"]:
                pts = []
                for (eid, yon) in loop:
                    e = E.get(eid)
                    if e is None: pts = None; break
                    v = e[0] if yon == 1 else e[1]
                    if v not in V: pts = None; break
                    pts.append(V[v])
                if pts and len(pts) >= 3: halkalar.append(np.array(pts))
            if not halkalar: atlanan["yuz"] += 1; continue
            yuzler.append({"yol": yol_ad, "katman": lid.get(f.get("layer"), ust_katman), "malzeme": mid.get(f.get("material_id")),
                           "arka_malzeme": mid.get(f.get("back_material_id")), "gizli": bool(f.get("hidden")), "halkalar": halkalar, "fid": fid})
        el = getattr(b, "edge_layers", None) or {}
        for eid, (a, c) in E.items():
            if a in V and c in V:
                kenarlar.append((yol_ad, lid.get(el.get(eid), ust_katman), V[a], V[c]))
        for inst in b.instances:
            ref = inst["ref_idx"]; alt = defs.get(ref) or {}
            ad = inst.get("name") or alt.get("name") or ("Tanim_%s" % ref)
            if any(ad.startswith(t) for t in tanim_atla) and derinlik == 0:
                atlanan["figur"] += 1; continue
            M2 = _core.multiply_matrices(M, inst["matrix"])
            kat = lid.get(inst.get("layer"), ust_katman) if inst.get("layer") else ust_katman
            dugumler.append({"yol": yol_ad + "/" + ad, "tanim": alt.get("name"), "ornek_adi": inst.get("name") or "", "katman": kat,
                             "gizli": bool(inst.get("hidden")), "derinlik": derinlik+1, "matris": [float(x) for x in M2]})
            yuru(ref, M2, yol_ad + "/" + ad, derinlik+1, kat)
    yuru("ROOT", KIMLIK, "", 0, "Layer0")
    return {"p": p, "yuzler": yuzler, "kenarlar": kenarlar, "dugumler": dugumler, "atlanan": dict(atlanan)}

def alan_normal(h):
    # Newell
    n = np.zeros(3)
    for i in range(len(h)):
        a = h[i]; b = h[(i+1) % len(h)]
        n += np.cross(a, b)
    A = np.linalg.norm(n)/2.0
    return A, (n/np.linalg.norm(n) if A > 1e-12 else np.array([0,0,1.0]))

def yuz_alani(f):
    A, n = alan_normal(f["halkalar"][0])
    for h in f["halkalar"][1:]:
        A -= alan_normal(h)[0]
    return A, n

def kutu(noktalar):
    P = np.vstack(noktalar)
    return P.min(axis=0), P.max(axis=0)

if __name__ == "__main__":
    r = oku(sys.argv[1])
    p = r["p"]
    print("surum:", p["version"], "birim:", p["units"], "tanim:", len(p["defs_dict"])-1, "dugum:", len(r["dugumler"]), "yuz:", len(r["yuzler"]), "kenar:", len(r["kenarlar"]), "atlanan:", r["atlanan"])
    if r["yuzler"]:
        mn, mx = kutu([h for f in r["yuzler"] for h in f["halkalar"]])
        print("kutu cm: min", np.round(mn,1), "max", np.round(mx,1), "olcu", np.round(mx-mn,1))
    kat = collections.defaultdict(list)
    for f in r["yuzler"]: kat[f["katman"]].append(f)
    for k, fs in sorted(kat.items(), key=lambda kv: -len(kv[1])):
        mn, mx = kutu([h for f in fs for h in f["halkalar"]])
        A = sum(yuz_alani(f)[0] for f in fs)/1e4
        print("  katman %-28s yuz %6d  alan %9.2f m2  kutu %s .. %s  olcu %s" % (k, len(fs), A, np.round(mn,1), np.round(mx,1), np.round(mx-mn,1)))
