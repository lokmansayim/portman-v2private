"""Çözülen SKP (ara/*.pkl) -> teslim dosyaları: GLB (metre, Y-yukarı), model JSON, yüz listesi, dört görünüş.
Kişi ve firma adları çıktıya girmez: düğüm adları kod biçiminde değilse maskelenir."""
import sys, os, re, json, gzip, pickle, collections, math
import numpy as np
import trimesh
import skp_oku, ciz3b, cati_olc

KOD = re.compile(r"^(D|MK|K|P)\d+|^Group#\d+$|^\d+$|^Tanim_\d+$")
def maske(yol, sozluk):
    out = []
    for parca in yol.split("/"):
        if parca == "": out.append(""); continue
        m = re.match(r"^(D|MK|K|P)(\d+)", parca)
        if m: out.append(m.group(1) + m.group(2)); continue
        if KOD.match(parca): out.append(parca); continue
        if parca not in sozluk: sozluk[parca] = "ad_%d" % (len(sozluk) + 1)
        out.append(sozluk[parca])
    return "/".join(out)

def kutu(fs):
    P = np.vstack([h for f in fs for h in f["halkalar"]]); return P.min(0), P.max(0)
def yv(a, n=1): return [round(float(x), n) for x in a]

def ucgenler(f):
    hk = f["halkalar"]
    if len(hk) == 1 and len(hk[0]) == 3: return hk[0][None, :, :]
    n = skp_oku.alan_normal(hk[0])[1]
    h = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    a = np.cross(n, h); a /= np.linalg.norm(a); b = np.cross(n, a)
    P = np.vstack(hk); uv = np.column_stack([P @ a, P @ b])
    son = np.cumsum([len(x) for x in hk]).astype(np.uint32)
    import mapbox_earcut as earcut
    tri = np.array(earcut.triangulate_float64(uv, son)).reshape(-1, 3)
    return P[tri] if len(tri) else np.zeros((0, 3, 3))

RENK = {"LCAD_Wall": (176, 58, 46), "LCAD_Truss": (46, 134, 171), "LCAD_Roof": (60, 150, 90), "Layer0": (190, 190, 185),
        "duvar": (84, 110, 140), "makas": (230, 140, 40), "kiris": (60, 150, 90), "P": (200, 80, 80), "diger": (170, 170, 170)}

def glb_yaz(gruplar, yol):
    sc = trimesh.Scene()
    for ad, (fs, renk) in gruplar.items():
        T = [ucgenler(f) for f in fs]; T = [t for t in T if len(t)]
        if not T: continue
        T = np.vstack(T) / 100.0                      # cm -> m
        T = T[:, :, [0, 2, 1]] * np.array([1, 1, -1])  # Z-yukarı -> Y-yukarı: (x, z, -y)
        m = trimesh.Trimesh(vertices=T.reshape(-1, 3), faces=np.arange(len(T) * 3).reshape(-1, 3), process=False)
        m.merge_vertices()
        m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            name=ad, baseColorFactor=[renk[0], renk[1], renk[2], 255], metallicFactor=0.1, roughnessFactor=0.8, doubleSided=True))
        sc.add_geometry(m, node_name=ad, geom_name=ad)
    sc.export(yol)
    return os.path.getsize(yol)

def yatay_kotlar(W):
    H = collections.defaultdict(float)
    for f in W:
        A, n = skp_oku.yuz_alani(f)
        if abs(n[2]) < 0.99: continue
        P = f["halkalar"][0]; o = P.max(0) - P.min(0); L = max(o[0], o[1]); gen = min(o[0], o[1])
        if L >= 40 and gen >= 3.0: H[round(float(P[0][2]), 1)] += L
    return {("%.1f" % z): round(L / 100, 2) for z, L in sorted(H.items()) if L >= 50}

def cati_ozet(W, T):
    wmn, wmx = kutu(W); tmn, tmx = kutu(T)
    K = cati_olc.duzlemler(T)
    G = collections.defaultdict(list)
    for (yon, s, c), A in K.items(): G[(yon, s)].append((c, A))
    aday = [(sum(a for _, a in L), yon, s, max(c for c, a in L if a > 200)) for (yon, s), L in G.items() if sum(a for _, a in L) >= 3000 and 15 <= s <= 60]
    aday.sort(reverse=True)
    duz = []
    for A, yon, s, c in aday:
        d = {"asagi_yon": [float(yon[0]), float(yon[1])], "egim_yuzde": float(s), "ust_basliklarin_alani_m2": round(A / 1e4, 2)}
        for eks in (0, 1):
            if abs(yon[eks]) > 0.99:
                uc = tmx[eks] if yon[eks] > 0 else tmn[eks]; dv = wmx[eks] if yon[eks] > 0 else wmn[eks]
                d["cati_kutusunun_ucunda_z"] = round(float(c - s / 100 * yon[eks] * uc), 1)
                d["duvar_dis_yuzunde_z"] = round(float(c - s / 100 * yon[eks] * dv), 1)
        duz.append(d)
    mahya = []
    for i, (A, yon, s, c) in enumerate(aday):
        for (A2, y2, s2, c2) in aday[i + 1:]:
            if s2 == s and abs(y2[0] + yon[0]) < 0.02 and abs(y2[1] + yon[1]) < 0.02:
                eks = 0 if abs(yon[0]) > 0.99 else 1
                cp, cn = (c, c2) if yon[eks] > 0 else (c2, c)
                mahya.append({"mahyaya_dik_eksen": "xy"[eks], "z": round(float((cp + cn) / 2), 1), "konum": round(float((cp - cn) / (2 * s / 100)), 1), "egim_yuzde": float(s)})
    return {"kutu": [yv(tmn), yv(tmx)], "olcu": yv(tmx - tmn), "ust_kot": round(float(tmx[2]), 1),
            "duvar_kutusundan_tasma": {"x-": round(float(wmn[0] - tmn[0]), 1), "x+": round(float(tmx[0] - wmx[0]), 1), "y-": round(float(wmn[1] - tmn[1]), 1), "y+": round(float(tmx[1] - wmx[1]), 1)},
            "egimli_duzlemler": duz, "mahya_adaylari": mahya}

def kumeler(v, esik):
    s = np.sort(np.asarray(v)); k = [[s[0]]]
    for a in s[1:]:
        if a - k[-1][-1] > esik: k.append([a])
        else: k[-1].append(a)
    return k

def main(ad, no, m2, cikti_ad):
    r = pickle.load(open("ara/%s.pkl" % ad, "rb"))
    Y = r["yuzler"]; p = r["p"]; soz = {}
    for f in Y: f["yol_m"] = maske(f["yol"], soz)
    dis = []
    if ad.startswith("08"):
        dis = [f for f in Y if np.vstack(f["halkalar"]).mean(0)[1] >= 2500]
        Y = [f for f in Y if np.vstack(f["halkalar"]).mean(0)[1] < 2500]
    W, T = cati_olc.sec({"yuzler": Y}, ad)
    wmn, wmx = kutu(W)
    model = {"sema": "portman.skp_aktarim/0.1", "birim": "cm",
             "kaynak": {"no": no, "dosya_adindaki_alan_m2": m2, "sketchup_surumu": str(p["version"]).strip("{}"), "dosya_birimi": p["units"], "okuyucu": "openskp 1.3.0"},
             "sayilar": {"yuz": len(Y), "kenar": len(r["kenarlar"]), "dugum": len(r["dugumler"]), "bina_disi_cizim_yuzu": len(dis)},
             "katmanlar": [], "duvar": {"kutu": [yv(wmn), yv(wmx)], "olcu": yv(wmx - wmn), "taban_alani_m2": round(float((wmx[0]-wmn[0]) * (wmx[1]-wmn[1]) / 1e4), 2)},
             "cati": cati_ozet(W, T)}
    kat = collections.defaultdict(list)
    for f in Y: kat[f["katman"]].append(f)
    for k, fs in sorted(kat.items(), key=lambda kv: -len(kv[1])):
        mn, mx = kutu(fs); model["katmanlar"].append({"ad": k, "yuz": len(fs), "kutu": [yv(mn), yv(mx)]})
    gruplar = collections.OrderedDict()
    if ad.startswith("08"):
        U = pickle.load(open("ara/08_uyeler.pkl", "rb"))
        def pkod(s):
            m = re.match(r"^(D|MK|K|P)(\d+)", s); return m.group(1) + m.group(2)
        pan = collections.defaultdict(list)
        for u in U: pan[pkod(u["panel"])].append(u)
        P = []
        for k in sorted(pan, key=lambda s: (re.sub(r"\d+", "", s), int(re.findall(r"\d+", s)[0]))):
            us = pan[k]; mn = np.min([u["mn"] for u in us], axis=0); mx = np.max([u["mx"] for u in us], axis=0); o = mx - mn
            eks = 0 if o[0] > o[1] else 1
            kayit = {"kod": k, "tur": {"D": "duvar paneli", "MK": "makas", "K": "kiriş paneli", "P": "panel"}[re.sub(r"\d+", "", k)],
                     "kutu": [yv(mn), yv(mx)], "boy_ekseni": "xy"[eks], "boy": round(float(o[eks]), 1), "yukseklik": round(float(o[2]), 1),
                     "uye_sayisi": len(us), "uye_tipleri": dict(collections.Counter(u["tip"] for u in us).most_common()),
                     "toplam_profil_boyu_m": round(sum(u["boy"] for u in us) / 100, 2)}
            if k.startswith("D"):
                kayit["dikme_akslari"] = sorted(round(float((u["mn"][eks] + u["mx"][eks]) / 2 - mn[eks]), 1) for u in us if u["tip"] in ("Stud", "KingStud") and u["olcu"][2] > 200)
                kayit["yatay_kusak_kotlari"] = sorted({round(float(u["mn"][2]), 1) for u in us if u["tip"] == "Nog"})
                ac = []
                for h in [u for u in us if u["tip"].startswith("HeaderPlate")]:
                    sill = [s for s in us if s["tip"].startswith("SillPlate") and s["mn"][eks] < h["mx"][eks] and s["mx"][eks] > h["mn"][eks]]
                    ac.append({"bas": round(float(h["mn"][eks] - mn[eks]), 1), "baslik_boyu": round(float(h["mx"][eks] - h["mn"][eks]), 1),
                               "net_en": round(float(h["mx"][eks] - h["mn"][eks] - 10.8), 1), "ust_kot": round(float(h["mn"][2]), 1),
                               "denizlik_ust_kotu": round(float(max(s["mx"][2] for s in sill)), 1) if sill else None,
                               "tur": "pencere" if sill else "kapı"})
                kayit["acikliklar"] = sorted(ac, key=lambda a: a["bas"])
            P.append(kayit)
        model["paneller"] = P
        model["profil_kesiti_mm"] = {"govde": 80.0, "baslik": 54.0, "dudak": 10.0, "et": 1.2, "kaynak": "bir dikmenin uç yüzünden okundu"}
        model["makas_akslari"] = {"eksen": "x", "konum": sorted(round(float(np.mean([u["mn"][0] + 4.0 for u in pan[k]])), 1) for k in pan if k.startswith("MK") and (np.max([u["mx"] for u in pan[k]], axis=0) - np.min([u["mn"] for u in pan[k]], axis=0))[0] < 12)}
        for f in Y:
            ilk = f["yol_m"].split("/")[1] if "/" in f["yol_m"] else "kok"
            gruplar.setdefault(ilk, ([], RENK["duvar"] if ilk.startswith("D") else RENK["makas"] if ilk.startswith("MK") else RENK["kiris"] if ilk.startswith("K") else RENK["P"] if ilk.startswith("P") else RENK["diger"]))[0].append(f)
    else:
        model["duvar"]["yatay_yuz_kotlari_m"] = yatay_kotlar(W)
        G = collections.Counter()
        for f in W:
            A, n = skp_oku.yuz_alani(f)
            if abs(n[2]) >= 0.99:
                P_ = f["halkalar"][0]; o = P_.max(0) - P_.min(0); G[round(float(min(o[0], o[1])), 1)] += 1
        model["duvar"]["karkas_derinlikleri_cm"] = {str(k): v for k, v in G.most_common(3)}
        cen = np.array([np.vstack(f["halkalar"]).mean(0) for f in T])
        ana = 0 if (wmx[0] - wmn[0]) > (wmx[1] - wmn[1]) else 1      # makaslar uzun kenar boyunca dizilir
        ks = [k for k in kumeler(cen[:, ana], 12.0) if len(k) >= 60]
        model["makas_akslari"] = {"eksen": "xy"[ana], "konum": [round(float(np.mean(k)), 1) for k in ks]}
        for f in Y: gruplar.setdefault(f["katman"], ([], RENK.get(f["katman"], RENK["diger"])))[0].append(f)
    a = model["makas_akslari"]["konum"]; model["makas_akslari"]["aralik"] = [round(a[i + 1] - a[i], 1) for i in range(len(a) - 1)]
    os.makedirs("teslim", exist_ok=True)
    boy = glb_yaz(gruplar, "teslim/%s.glb" % cikti_ad)
    json.dump(model, open("teslim/%s_model.json" % cikti_ad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with gzip.open("teslim/%s_yuzler.json.gz" % cikti_ad, "wt", encoding="utf-8") as fp:
        json.dump({"birim": "cm", "eksen": "z yukarı", "yuzler": [{"d": f["yol_m"], "k": f["katman"], "h": [np.round(h, 2).tolist() for h in f["halkalar"]]} for f in Y]}, fp, ensure_ascii=False, separators=(",", ":"))
    for f in Y: f["katman_asil"] = f["katman"]
    if ad.startswith("08"):
        for f in Y:
            ilk = f["yol_m"].split("/")[1] if "/" in f["yol_m"] else "kök"
            f["katman"] = "duvar paneli (D)" if ilk.startswith("D") else "makas (MK)" if ilk.startswith("MK") else "kiriş paneli (K)" if ilk.startswith("K") else "P" if ilk.startswith("P") else "diğer"
    ciz3b.pafta(Y, "teslim/%s_gorunus.png" % cikti_ad, baslik="SKP no %d · %d m² · çelik karkas (SketchUp %s)" % (no, m2, model["kaynak"]["sketchup_surumu"]))
    print(cikti_ad, "glb", boy, "bayt; yüz", len(Y), "; maskelenen ad", len(soz))
    return model

if __name__ == "__main__":
    for ad, no, m2, c in (("11_90m2", 11, 90, "skp11_90m2_celik"), ("01_62m2_celik", 1, 62, "skp01_62m2_celik"), ("08_81m2", 8, 81, "skp08_81m2_celik")):
        if len(sys.argv) > 1 and sys.argv[1] not in ad: continue
        m = main(ad, no, m2, c)
        print(json.dumps({k: m[k] for k in ("duvar", "cati", "makas_akslari")}, ensure_ascii=False)[:1500])
