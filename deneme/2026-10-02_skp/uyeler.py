"""81 m² modelde (üye tipleri katman adıyla gelen çerçeve) üyeleri çıkarır: panel, tip, kutu, boy.
Girdi: ara/08_81m2.pkl (kaydet.py). Çıktı: ara/08_uyeler.pkl; aktar.py bunu okur."""
import pickle, collections, re, json, numpy as np
r = pickle.load(open("ara/08_81m2.pkl","rb"))
Y = r["yuzler"]
byyol = collections.defaultdict(list)
for f in Y: byyol[f["yol"]].append(f)
uyeler = []
for yol, fs in byyol.items():
    p = yol.split("/")
    if len(p) < 3: continue
    ust = p[1]
    if not re.match(r"(D|MK|K|P)\d+", ust): continue
    P = np.vstack([h for f in fs for h in f["halkalar"]]); mn, mx = P.min(0), P.max(0)
    tip = collections.Counter(f["katman"] for f in fs if f["katman"] not in ("wall", "Layer0"))
    t = tip.most_common(1)[0][0] if tip else "?"
    o = mx - mn; eks = int(np.argmax(o))
    uyeler.append({"panel": ust, "ad": "/".join(p[2:]), "tip": t, "mn": mn, "mx": mx, "olcu": o, "eksen": "xyz"[eks], "boy": float(o[eks]), "yuz": len(fs)})
print("üye sayısı:", len(uyeler))
print("tipler:", collections.Counter(u["tip"] for u in uyeler).most_common())
pk = collections.Counter(u["panel"] for u in uyeler)
print("panel başına üye:", sorted(pk.items(), key=lambda kv: (re.sub(r"\d+","",kv[0]), int(re.findall(r"\d+", kv[0])[0]))))
pickle.dump(uyeler, open("ara/08_uyeler.pkl","wb"))
# kesit: düşey bir Stud'un x-y kutusu ve bir Nog'un kesiti
for t in ("Stud", "KingStud", "Nog", "TopPlate", "BottomPlate", "WebBrace"):
    us = [u for u in uyeler if u["tip"] == t and u["panel"].startswith("D")]
    if us:
        c = collections.Counter(tuple(np.round(np.sort(u["olcu"])[:2], 1)) for u in us)
        print("  kesit (küçük iki ölçü) %-12s n=%d: %s" % (t, len(us), c.most_common(4)))
# toplam boy (m) tipe ve panel türüne göre
T = collections.defaultdict(float)
for u in uyeler: T[(re.sub(r"\d+","",u["panel"]), u["tip"])] += u["boy"]/100
tot = collections.defaultdict(float)
for (pt, t), v in sorted(T.items()): tot[pt] += v
print("toplam üye boyu (m):", {k: round(v,1) for k, v in tot.items()}, "genel", round(sum(tot.values()),1))
