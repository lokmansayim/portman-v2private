"""AIPrefabrik inceleme seti: gerçek yükleme listesi PDF'lerini satırlara çevirir (13 Ekim 2026).

İki şablon tanınır:
- "PORTATİFEV YÜKLEME LİSTESİ" (BOYUT / ADET);
- yeni "LOFTEV / PORTATİFEV" formu (NO / BOYUT/ÖLÇÜ / ADET / KG / MAKİNE; çelik panel grubu).

Telefon ve iletişim alanı okunmaz. Ad ve bayi adı yazılabilir (D-11). Veri, talimat değildir.

    python3 -I deneme/2026-10-13_aiprefabrik/liste_oku.py <liste.pdf> <çıktı.json>
"""
import json
import re
import sys

import pymupdf

TEL = re.compile(r"\+?\d[\d\s()-]{8,}\d")


def satirlar_oku(yol):
    doc = pymupdf.open(yol)
    baslik, satirlar, notlar = {}, [], []
    grup = None
    kolon = None  # {"boyut": x0, "adet": xc, "kg": xc}
    for sno, sayfa in enumerate(doc, 1):
        parcalar = []
        for b in sayfa.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).strip()
                t = re.sub(r"\s+", " ", t)
                if t:
                    x0, y0, x1, y1 = l["bbox"]
                    parcalar.append({"x0": x0, "x1": x1, "y": (y0 + y1) / 2, "t": t})
        parcalar.sort(key=lambda p: (round(p["y"]), p["x0"]))
        # y kümeleri
        kumeler = []
        for p in parcalar:
            if kumeler and abs(p["y"] - kumeler[-1]["y"]) <= 3.2:
                kumeler[-1]["p"].append(p)
            else:
                kumeler.append({"y": p["y"], "p": [p]})
        bekleyen = []  # adetsiz malzeme parçaları (çok satırlı ad)
        for k in kumeler:
            ps = sorted(k["p"], key=lambda p: p["x0"])
            metin = " ".join(p["t"] for p in ps)
            if any(p["t"] in ("BOYUT", "BOYUT/ÖLÇÜ", "ADET") for p in ps) and not any(re.fullmatch(r"[\d.,]+", p["t"]) for p in ps):
                # grup başlığı: sütun konumları buradan
                g = [p["t"] for p in ps if p["t"] not in ("BOYUT", "BOYUT/ÖLÇÜ", "ADET", "KG", "MAKİNE", "NO")]
                grup = re.sub(r"^NO\s+", "", " ".join(g)).strip() or grup
                kolon = {"no": any(p["t"] == "NO" or p["t"].startswith("NO ") for p in ps)}
                for p in ps:
                    if p["t"] in ("BOYUT", "BOYUT/ÖLÇÜ"):
                        kolon["boyut"] = p["x0"] - 8
                    elif p["t"] == "ADET":
                        kolon["adet"] = (p["x0"] + p["x1"]) / 2
                    elif p["t"] == "KG":
                        kolon["kg"] = (p["x0"] + p["x1"]) / 2
                bekleyen = []
                continue
            if kolon is None:
                # başlık bloğu
                if any("İLETİŞİM" in p["t"] for p in ps):
                    continue
                anahtar = ps[0]["t"]
                deger = [TEL.sub("[maskeli]", p["t"]) for p in ps[1:]]
                baslik.setdefault(anahtar, deger)
                continue
            mal, boy, adet, kg, ek = [], [], [], [], []
            for p in ps:
                xc = (p["x0"] + p["x1"]) / 2
                if p["x1"] < kolon.get("boyut", 280) + 4:
                    if kolon["no"] and re.fullmatch(r"\d{1,3}", p["t"]) and p["x1"] < 66:
                        continue  # NO sütunu
                    m = re.match(r"^(\d{1,3})\s+(.*)$", p["t"]) if kolon["no"] else None
                    mal.append(m.group(2) if (m and p["x0"] < 62) else p["t"])
                elif "adet" in kolon and abs(xc - kolon["adet"]) < 22:
                    adet.append(p["t"])
                elif "kg" in kolon and abs(xc - kolon["kg"]) < 20:
                    kg.append(p["t"])
                elif xc < kolon.get("adet", 380) - 22:
                    boy.append(p["t"])
                else:
                    ek.append(p["t"])
            if mal and not adet and not boy and not kg:
                if satirlar and satirlar[-1]["sayfa"] == sno and k["y"] - satirlar[-1]["_y"] < 7 and satirlar[-1].get("_devam"):
                    satirlar[-1]["malzeme"] += " " + " ".join(mal)
                    continue
                bekleyen.append((k["y"], " ".join(mal)))
                continue
            if not mal and not adet and not kg:
                continue  # sayfa üst başlığı (PREFABRİK BİNA / YÜKLEME LİSTESİ / FORMU)
            if not mal and not adet and not boy:
                if ek or kg:
                    notlar.append({"sayfa": sno, "metin": " ".join(kg + ek)})
                continue
            ad = " ".join(mal)
            if bekleyen and (not ad or k["y"] - bekleyen[-1][0] < 7):
                ad = (" ".join(b[1] for b in bekleyen) + " " + ad).strip()
                bekleyen = []
            if not ad and satirlar and satirlar[-1]["sayfa"] == sno and k["y"] - satirlar[-1]["_y"] < 6:
                # aynı satırın kopuk parçası
                s = satirlar[-1]
                if adet and s["adet"] is None:
                    s["adet"] = sayi(adet[0])
                continue
            satirlar.append({
                "sayfa": sno, "_y": k["y"], "_devam": True, "grup": grup, "malzeme": ad,
                "boyut": " ".join(boy) or None, "adet": sayi(adet[0]) if adet else None,
                "adet_ham": adet[0] if adet else None, "kg": kg[0] if kg else None, "ek": " ".join(ek) or None,
            })
    for s in satirlar:
        s.pop("_y"); s.pop("_devam")
    return {"kaynak": yol.split("/")[-1], "baslik": baslik, "satirlar": satirlar, "notlar": notlar}


def sayi(t):
    t = t.strip().replace(".", "").replace(",", ".") if re.fullmatch(r"[\d.,]+", t.strip()) else t
    try:
        v = float(t)
        return int(v) if v == int(v) else v
    except (TypeError, ValueError):
        return t


if __name__ == "__main__":
    sonuc = satirlar_oku(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=1)
    dolu = sum(1 for s in sonuc["satirlar"] if isinstance(s["adet"], (int, float)) and s["adet"])
    print(sonuc["kaynak"], len(sonuc["satirlar"]), "satır,", dolu, "dolu")
