"""uydur.py <geo.json> <ie.json> <çıktı ie.json>: Motor'un pano dizilimini paftanınkine yaklaştıran dayanaklar (dizilim.dis_pano_dayanagi).
Farklı her duvar için: paftadaki ekler (açıklık panosu hariç) aks tablosundaki bir aks + 125,5k ise o duvara dayanak yazılır; Motor yeniden
kurulur; dayanak yalnız o duvar aynı olur ve başka duvar bozulmazsa kalır. Pafta düzeltilmez; kalan farklar kıyasta."""
import copy, json, sys
from pathlib import Path
KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiyas as K
MOD = 125.5


def aks_tablosu(g):
    T = {}
    for k in ("x", "y"):
        boy = g["W"] if k == "x" else g["H"]
        ilk = g["ilk"][k]
        n = int(round((boy - 2 * ilk) / (MOD / 2)))
        T[k] = sorted({round(ilk + i * MOD / 2, 2) for i in range(n + 1)} | {boy - ilk} | set(g["ek"][k]))
    return T


def dene(g, ie):
    try:
        satir, ac, plan = K.karsilastir(g, ie)
    except Exception as e:
        return None, str(e)
    kisa = sum(1 for p in plan.panolar if p.boy < 10 - 1e-6)     # 10 cm'den kısa pano: dayanak artık bıraktı
    return (satir, ac, kisa), None


def pembe(s):
    """Duvarda 5 cm içinde karşılığı olmayan ek sayısı (paftanınki ve Motor'unki): yan yana resimde pembe kalan farklar."""
    def ekler(boylar):
        x, E = s["aralik"][0], []
        for b in boylar[:-1]:
            x += b
            E.append(x)
        return E
    P, M = ekler(s["pafta"]), ekler(s["motor"])
    lo, hi = s["aralik"]
    return sum(1 for e in P if not any(abs(e - f) <= 5.1 for f in M)) + \
        sum(1 for f in M if lo + 2 < f < hi - 2 and not any(abs(e - f) <= 5.1 for e in P))


def puan(sonuc):
    satir, ac = sonuc[:2]
    atilan = sonuc[3] if len(sonuc) > 3 else 0          # Motor'un yerleştiremediği (geçici atılan) açıklık yerinde değildir
    return (sum(not s["ayni"] for s in satir), atilan + sum(1 for a in ac if not yerinde(a)), sum(pembe(s) for s in satir))


def yerinde(a):
    """Açıklık paftadaki yerinde mi: pencere 1,6 cm; kapı 5 cm (paftadaki yay kanadın kendisi, Motor'un boşluğu 82 / 90)."""
    return a["kayma"] is not None and abs(a["kayma"]) <= (5.1 if a["tur"] in ("ic_kapi", "dis_kapi") else 1.6)


def dene_esnek(g, ie):
    """Duvar uydururken: pafta dizinleriyle Motor düşerse (aday listesi değişti) dizinsiz denenir."""
    r, h = dene(g, ie)
    if r is not None:
        return r, None
    y = dizinsiz(ie)
    for n in range(5):                 # yalnız duvar uydurmak için: Motor'un yerleştiremediği açıklık geçici olarak atılır
        r, h2 = dene(g, y)
        if r is not None:
            return r + (n,), None
        k = next((i for i, a in enumerate(y["acikliklar"]) if hatadaki(a, h2)), None)
        if k is None:
            break
        y = copy.deepcopy(y); y["acikliklar"].pop(k)
    return None, h


def hatadaki(a, h):
    """Motor'un hata iletisindeki açıklık bu mu (tür ve oda; Motor ön ↔ arka cephe adını aynada çevirir)."""
    if f"'tur': '{a['tur']}'" not in h or ("olcu" in a and f"'olcu': {a['olcu']!r}" not in h):
        return False
    return repr(a["arasi"]) in h if "arasi" in a else f"'mahal': {a.get('mahal')!r}" in h


def dizinsiz(ie):
    """Açıklıkların pano dizinleri atılmış kopya: duvar uydurulurken Motor'un aday listesi değişir, dizin sonra yeniden denenir."""
    y = copy.deepcopy(ie)
    for a in y["acikliklar"]:
        a.pop("pano", None)
    return y


def dizin_uydur(g, ie, sonuc):
    """Duvarlar uydurulduktan sonra: paftadan gelen dizin Motor'da hata verirse atılır; yerinde olmayan açıklık için 0..7 dizinleri denenir."""
    for _ in range(len(ie["acikliklar"])):
        r, h = dene(g, ie)
        if r is not None:
            sonuc = r; break
        k = next((i for i, a in enumerate(ie["acikliklar"]) if "pano" in a and hatadaki(a, h)), None)
        if k is None:
            print("Motor hatası (dizin dışı):", h[:200]); return ie, None
        print("dizin atıldı:", ie["acikliklar"][k].get("mahal") or ie["acikliklar"][k].get("arasi"), "←", h[:120])
        ie = copy.deepcopy(ie); ie["acikliklar"][k].pop("pano")
    else:
        return ie, None
    for i in range(len(ie["acikliklar"])):
        if yerinde(sonuc[1][i]):
            continue
        en = None
        kay = lambda r: abs(r[1][i]["kayma"]) if r[1][i]["kayma"] is not None else 1e9
        for n in range(8):
            y = copy.deepcopy(ie); y["acikliklar"][i]["pano"] = n; y["acikliklar"][i].pop("_oda_ortasi", None)
            r, h = dene(g, y)
            if r is None or puan(r) > puan(sonuc):
                continue
            # paftadaki yerine en yakın pano (duvarın dizilimi farklıysa tam yeri olmayabilir); en az 5 cm iyileşme
            if kay(r) < kay(sonuc) - 5 and (en is None or (puan(r), kay(r)) < (puan(en[1]), kay(en[1]))):
                en = (y, r)
        if en:
            print("dizin bulundu:", en[0]["acikliklar"][i].get("mahal") or en[0]["acikliklar"][i].get("arasi"), en[0]["acikliklar"][i]["pano"],
                  puan(sonuc), "→", puan(en[1]))
            ie, sonuc = en
    return ie, sonuc


def main():
    g = json.load(open(sys.argv[1]))
    ie_yazili = json.load(open(sys.argv[2]))
    ie = ie_yazili
    T = aks_tablosu(g)
    sonuc, hata = dene_esnek(g, ie)
    if sonuc is None:
        print("Motor hatası:", hata); raise SystemExit(2)
    print("başlangıç", puan(sonuc))
    eklenen = []
    for s in [s for s in sonuc[0] if not s["ayni"]]:
        # paftanın iç ekleri; dayanak anahtarı: duvar yatay (my 'y') → x aksı; düşey (my 'x') → y aksı
        anahtar = "x" if s["yon"] == "y" else "y"
        lo_w, hi_w = s["aralik"]
        ekler, x = [], lo_w
        for b in s["pafta"][:-1]:
            x += b
            ekler.append(round(x, 2))
        # ekler, aynı kalıntılı (aks + 125,5k) ardışık kümelere bölünür; her küme için bir dayanak (aralığı komşu eklerin arası)
        def kalinti(e, a):
            return abs(((e - a) / MOD) - round((e - a) / MOD)) * MOD <= 1.5
        kumeler = []
        for e in ekler:
            if kumeler and kalinti(e, kumeler[-1][0]):
                kumeler[-1].append(e)
            else:
                kumeler.append([e])
        sinir = [lo_w] + ekler + [hi_w]
        dis = s["t"] == 10.0 and (abs(s["c"] - 5) < 2 or abs(s["c"] - ((g["W"] if s["yon"] == "x" else g["H"]) - 5)) < 2)
        tek, ekstra = [], []
        yakin = lambda v: min(T[anahtar], key=lambda t: abs(t - v))
        hat = g["AX"] if anahtar == "x" else g["AY"]                 # duvarı olan akslar önce: duvar ucu kesen duvarın yüzündedir
        def uc(v, duvar_ucu):
            if not duvar_ucu and abs(yakin(v) - v) <= 1.6:            # paftanın kendi eki: aks tablosundaki yeri
                return yakin(v)
            h = min(hat, key=lambda t: abs(t - v))
            return h if abs(h - v) <= 6 else yakin(v)

        def yaz(aday, lo, hi):
            dy = {anahtar: aday, "aralik_cm": [lo, hi]}
            if dis:
                dy["cephe"] = ({"x": "sol", "y": "arka"} if s["c"] < 300 else {"x": "sag", "y": "on"})[s["yon"]]
            else:
                dy["ic_duvarlar"] = True
                dy["duvar_cm"] = min(T[s["yon"]], key=lambda t: abs(t - s["c"]))
            return dy
        # Motor'un paftada olmayan eki: paftanın o parçası tek pano (ör. kapının bütün duvarı); parçanın ucuna dayanak, ek kalkar
        for f in s["motor_ek_paftada_yok"]:
            i = next((i for i in range(len(sinir) - 1) if sinir[i] < f < sinir[i + 1]), None)
            if i is None:
                continue
            lo, hi = uc(sinir[i], sinir[i] == lo_w), uc(sinir[i + 1], sinir[i + 1] == hi_w)
            if hi - lo > 1 and sinir[i + 1] - sinir[i] < MOD + 3:
                for aday in (lo, hi):
                    dy = yaz(aday, lo, hi)
                    if dy not in tek + ekstra:
                        (tek if aday == lo else ekstra).append(dy)
        for km in kumeler:
            i0, i1 = sinir.index(km[0]), sinir.index(km[-1])
            lo_, hi_ = (lo_w, hi_w) if len(kumeler) == 1 else (sinir[i0 - 1], sinir[i1 + 1])
            lo, hi = uc(lo_, lo_ == lo_w), uc(hi_, hi_ == hi_w)
            # duvar ucu kesen duvarın yüzünde, aks onun ortasında (yarı kalınlık); komşu ek aksta değilse kümenin kendi ucu
            if abs(lo - lo_) > 6:
                lo = yakin(km[0]) if abs(yakin(km[0]) - km[0]) <= 1.6 else None
            if abs(hi - hi_) > 6:
                hi = yakin(km[-1]) if abs(yakin(km[-1]) - km[-1]) <= 1.6 else None
            if lo is None or hi is None or hi - lo < MOD - 1:
                continue
            sap = lambda a: max(abs(((e - a) / MOD) - round((e - a) / MOD)) * MOD for e in km)
            # tam tutan aks; yoksa (ya da ek olarak) 5 cm'ye kadar kayan akslar (Motor'un köşe ya da T payı paftanınkinden farklı)
            secenek, kal = [], set()
            for a in sorted((a for a in T[anahtar] if lo <= a <= hi and sap(a) <= 5.1), key=sap):
                if round(a % MOD, 1) not in kal:         # aynı kalıntılı akslar aynı ekleri verir
                    kal.add(round(a % MOD, 1)); secenek.append(a)
            ilk_ = True
            for aday in secenek:
                dy = yaz(aday, lo, hi)
                (tek if ilk_ else ekstra).append(dy)
                ilk_ = False
        denemeler = [[dy] for dy in tek + ekstra] + ([tek] if len(tek) > 1 else [])
        en = None
        for grup in denemeler:
            yeni = copy.deepcopy(ie)
            yeni["yapi"]["dizilim"].setdefault("dis_pano_dayanagi", []).extend(grup)
            r, h = dene_esnek(g, yeni)
            if r is None:
                print("ret (Motor):", grup, h[:160]); continue
            print("deneme", grup, puan(r))
            if r[2] > sonuc[2]:
                print("ret (kısa pano):", grup); continue
            if puan(r) < puan(sonuc) and (en is None or puan(r) < puan(en[1])):
                en = (yeni, r, grup)
        if en:
            print("kabul", en[2], puan(sonuc), "→", puan(en[1]))
            ie, sonuc = en[0], en[1]
            eklenen.extend(en[2])
    yeni = copy.deepcopy(ie_yazili)
    yeni["yapi"]["dizilim"] = ie["yapi"]["dizilim"]
    ie, son = dizin_uydur(g, yeni, sonuc)
    if son is not None:
        sonuc = son
    if eklenen:
        ie.setdefault("varsayimlar", []).append(
            "Pano dizilimi paftadan: " + "; ".join(f"{d.get('duvar_cm', d.get('cephe'))} hattında {list(d)[0]} {d[list(d)[0]]:g}'dan 125,5"
                                                  for d in eklenen) + " (dizilim.dis_pano_dayanagi).")
    json.dump(ie, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
    print("son", puan(sonuc))


if __name__ == "__main__":
    main()
