#!/usr/bin/env python3
"""KT-01 Yapı Tanımı 0.5, kıyastan sonra düzeltilmiş hali. Dondurulan tanım (`kt01_tanim_uret.py`) değişmez; düzeltmeler burada, kaynağıyla.
Müşteri projesinin geometrisidir; Lokman'ın onayıyla depoda (8 Ekim 2026 07:23). Profil boyları: `KT01_profil_boylari.json` (`../skp_profil.py` ile SKP modelinden).

Kullanım: python kt01_tanim_duzeltilmis.py cikti.json profil_boylari.json
"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kt01_tanim_uret import tanim as dondurulan      # noqa: E402

t = copy.deepcopy(dondurulan)
duzeltmeler = []

# 1) Müştemilat ıslak hacim: gerçek listenin PENCERE KAPI sayfasında "Müştemilat (Islak Zemin)"; duvar ve tavanı yeşil alçıpan
next(m for m in t["mahaller"] if m["ad"] == "Müştemilat")["islak"] = True
t["duvar_siniflari"]["ek"]["not"] = "açıklama 8: 80x45x08, mineral yün yok. İç yüzü OSB + yeşil alçıpan (gerçek liste: müştemilat ıslak zemin)"
duzeltmeler.append("Müştemilat ıslak hacim (gerçek liste: 'Müştemilat (Islak Zemin)'); projenin çiziminde yazmıyor")

# 2) Kapsam: teknik özelliklerde yalnız dış ve iç cephe boyası alıcıya ait; tavan boyası ve astar listede kalır
t["kapsam"].pop("boya")
t["kapsam"].update({"dis_cephe_boyasi": False, "ic_cephe_boyasi": False})
t["kapsam"]["kaynak"] = "teknik özellikler (dış kapı, pencere, dış cephe boya, iç cephe boya: alıcıya ait) ve açıklama notları 4–6"
duzeltmeler.append("Kapsam: 'boya' tek kalem değil; teknik özelliklerde yalnız dış ve iç cephe boyası alıcıya ait (girdi hatası)")

# 2b) Renk: teknik özelliklerde yazıyor; dondurulan listede listeye taşınmıyordu (gerçek liste rengi kalemin adında yazıyor)
t["renk"] = {"cati": t["teknik_ozellikler"]["Çatı kaplama rengi"], "sacak_alin": t["teknik_ozellikler"]["Saçak ve alın rengi"], "kaynak": "teknik özellikler"}
duzeltmeler.append("Renk tanıma alan olarak yazıldı (teknik özellikler: çatı kaplama rengi, saçak ve alın rengi); listede renkli yazılan kalemlere eklenir")

# 4) Kalkanlar: modeldeki kalkan yüzleri saçak uçlarına kadar (294–1248; cumba 294–730)
for k in t["cati"]["kalkanlar"]:
    k["aralik"] = [294.0, 730.0] if k["ad"].startswith("cumba") else [294.0, 1248.0]
duzeltmeler.append("Kalkanlar modeldeki yüzler gibi saçak uçlarına kadar (kuzey 8,43, cumba 2,00 m²); dondurulan tanımda duvar genişliği kadardı (8,36 ve 1,96)")

# 4b) Cumbanın doğu yüzü: makaslar (MKS8, MKS9, truss10) ve SKP'deki makas üstü yüzey x = 730'a kadar tam dikdörtgen; veranda sundurması üstüne biner.
#     Görünen kısım (vadiye kadar) kaplama dizilimi için; aşıklar karkasın tamamında (aşık paftasında 4 sıra × 278).
cd_ = next(d for d in t["cati"]["duzlemler"] if d["ad"] == "cumba doğu")
cd_["karkas"] = [[512.0, -27.0], [730.0, -27.0], [730.0, 251.0], [512.0, 251.0]]
duzeltmeler.append("Cumbanın doğu yüzünde karkas (makas üstü yüzey) tam dikdörtgen: aşıklar veranda sundurmasının altında da sürer (SKP modeli ve aşık paftası)")

# 5) Karkas modelindeki profil boyları ve et kalınlıkları (`skp_profil.py --json`): her panelde üyelerin boyu ve yan yüzlerden okunan et
boylar = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))


def grup(desen, haric=(), yalniz=None):
    """Adı desene uyan panellerden grup: {"paneller": {ad: profil boyu}, "profil": modelden okunan et ile}. Gruptaki panellerin eti aynı olmalı."""
    sec = {ad: v for ad, v in boylar.items() if re.fullmatch(desen, ad) and ad not in haric and (yalniz is None or ad in yalniz)}
    etler = {v["et_mm"] for v in sec.values()}
    assert len(etler) == 1 and None not in etler, (desen, etler)
    return {"paneller": {ad: v["boy_m"] for ad, v in sec.items()}, "profil": "80x45x" + f"{etler.pop():g}".replace(".", ",")}


ic_adlar = {"D10", "D11", "D12", "D13", "D14", "D15"}
t["celik_modeli"] = {
    "kaynak": "SKP karkas modeli: her paneldeki üyelerin (dikme, başlık, kuşak, çapraz) boylarının toplamı (m) ve üyelerin yan yüzlerinden okunan et kalınlığı",
    "gruplar": {
        "dis": grup(r"D\d+", haric=ic_adlar),
        "ic": grup(r"D\d+", yalniz=ic_adlar),
        "ek": grup(r"MD\d+"),
        "korkuluk": grup(r"VD\d+", haric={"VD3"}),
        "giris_cercevesi": grup(r"VD3"),
        "kolon": grup(r"KLN\d+"),
        "kiris": grup(r"KRS\d+"),
        "makas": grup(r"MKS\d+|truss\d+"),
        "baca": grup(r"BACA\d+"),
        "cati_paneli": grup(r"MPNL\d+"),
    },
}
gruplar = t["celik_modeli"]["gruplar"]
sayilan = {ad for g in gruplar.values() for ad in g["paneller"]}
assert sayilan == set(boylar), sorted(set(boylar) - sayilan)
duzeltmeler.append("Karkas modelindeki profil boyları eklendi (çelik ağırlığı oradan)")

# 3) Profiller modeldeki et kalınlığından: korkuluk ve baca 0,8; giriş çerçevesi (VD3) 1,2. Dondurulan tanımda üçü de 1,2 varsayılmıştı;
#    et kalınlığı modelde okunabiliyordu (üyelerin yan yüzlerindeki paralel düzlem aralığı), okumamıştım. Gerçek liste de aynı profilleri yazıyor.
t["duvar_siniflari"]["korkuluk"]["profil"] = gruplar["korkuluk"]["profil"]
t["duvar_siniflari"]["baca"]["profil"] = gruplar["baca"]["profil"]
next(d for d in t["duvarlar"] if d["ad"] == "VD3")["profil"] = gruplar["giris_cercevesi"]["profil"]
assert (gruplar["korkuluk"]["profil"], gruplar["baca"]["profil"], gruplar["giris_cercevesi"]["profil"]) == ("80x45x0,8", "80x45x0,8", "80x45x1,2")
duzeltmeler.append("Korkuluk ve baca karkası 80 × 45 × 0,8; giriş çerçevesi 1,2: karkas modelindeki et kalınlığından (dondurulan tanımda 1,2 varsayılmıştı; gerçek liste de böyle)")

t["kaynak"]["okunmayanlar"] = ("Bu tanım, kendi listemiz dondurulduktan (6 Ekim 2026 22:47) ve gerçek listeyle kıyaslandıktan sonra düzeltilmiş halidir. "
                               "Montaj paftalarındaki adetler (kaplama, omega, aşık) yine girdi değil; dizilimler koddan çıkar.")
t["duzeltmeler"] = duzeltmeler

if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", sys.argv[1])
    for ad, g in t["celik_modeli"]["gruplar"].items():
        print(f"   {ad:16s} {len(g['paneller']):2d} panel · profil boyu {sum(g['paneller'].values()):7.2f} m · {g['profil']}")
