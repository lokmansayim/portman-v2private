#!/usr/bin/env python3
"""KT-02 Yapı Tanımı 0.5, kıyastan sonra düzeltilmiş hali. Dondurulan tanım (`kt02_tanim_uret.py`) değişmez; düzeltmeler burada, kaynağıyla.
Yalnız girdi hataları düzeltilir (projenin belgesinde olup yanlış okuduğumuz şeyler); kural ve karar farkları kurallarda kalır.

Kullanım: python kt02_tanim_duzeltilmis.py KT02_duzeltilmis.json KT02.json   (KT02.json: dondurulan tanım; çelik modeli oradan)
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kt02_tanim_uret as kor      # noqa: E402

t = copy.deepcopy(kor.tanim)
duzeltmeler = []

# 1) Sundurmanın çatısı ana çatıya vadilerle bağlanır (cumba gibi): sundurmanın iki yüzü ana saçağın üstünden geçip ana çatının batı yüzüyle
#    kesişir; sundurmanın mahyası kesişme noktasına kadar sürer. Kaynak: çatı kaplaması yerleşim paftasında ana batı yüzünün saçak kenarındaki
#    çentik ve gerçek listedeki ters mahya (3,05 m: iki vadi) ile kenar kutuları; dere paftasında ana saçağın sundurma önünde kesilmesi.
#    Dondurulan tanımda sundurmanın çatısı ana saçağın ucunda bitiyordu (üstte kalan üçgen kalkan sayılmıştı): alın sacı, baş makas Z'si ve
#    dere kapağı fazla; ters mahya, kenar kutusu eksik; saçak ve dere boyu 2,1 m uzun çıkmıştı.
E, XB, SX0, SY0, SY1 = kor.E, kor.XB, kor.SX0, kor.SY0, kor.SY1
SYM, SXA = kor.SYM, kor.SXA
XV = XB + (SY1 - SY0) / 2                     # vadilerin buluştuğu nokta (sundurma mahyasının doğu ucu): x = −27 + 105 = 78
r2 = kor.r2
adli = {d["ad"]: d for d in t["cati"]["duzlemler"]}
adli["batı"]["plan"] = [[r2(x), r2(y)] for x, y in
                       [[XB, kor.YS], [kor.XM, kor.YM0], [kor.XM, kor.YM1], [XB, kor.YN], [XB, SY1], [XV, SYM], [XB, SY0]]]
adli["batı"]["not"] = "ana çatının batı yüzü; sundurmanın çatısı bu yüze iki vadiyle bağlanır (çentik)"
adli["sundurma güney"]["plan"] = [[r2(x), r2(y)] for x, y in [[SX0, SY0], [XB, SY0], [XV, SYM], [SXA, SYM]]]
adli["sundurma güney"]["not"] = "sundurma çatısı; ana saçağın üstünden geçip ana çatının batı yüzüyle vadi yapar"
adli["sundurma kuzey"]["plan"] = [[r2(x), r2(y)] for x, y in [[XB, SY1], [SX0, SY1], [SXA, SYM], [XV, SYM]]]
adli["sundurma kuzey"]["not"] = "sundurma çatısı; ana saçağın üstünden geçip ana çatının batı yüzüyle vadi yapar"
t["cati"]["kalkanlar"] = []
duzeltmeler.append("Sundurmanın çatısı ana çatıya iki vadiyle bağlanır (çatı kaplaması paftasındaki çentik; listede ters mahya 3,05 m ve 4 kenar kutusu): "
                   "dondurulan tanımda ana saçağın ucunda bitiyordu ve üstte kalan üçgen kalkan sayılmıştı (girdi hatası)")

t["kaynak"]["okunmayanlar"] = ("Bu tanım, kendi listemiz dondurulduktan (9 Ekim 2026 21:40) ve gerçek listeyle kıyaslandıktan sonra düzeltilmiş halidir. "
                               "Paftalardaki adetler (çatı kaplaması, tavan omegası, aşık, dere inişi) yine girdi değil; yalnız biçim düzeltildi.")
t["duzeltmeler"] = duzeltmeler

if __name__ == "__main__":
    yol, kor_yolu = Path(sys.argv[1]), Path(sys.argv[2])
    # çelik modeli dondurulan tanımdakiyle aynı (üretim dosyası): dondurulan tanımdan alınır; tanımın geri kalanı betikteki dondurulan tanımla aynı olmalı
    kor_json = json.loads(kor_yolu.read_text(encoding="utf-8"))
    beklenen = json.loads(json.dumps(kor.tanim, ensure_ascii=False))
    assert {k: v for k, v in kor_json.items() if k != "celik_modeli"} == beklenen, "dondurulan tanım betikteki tanımla aynı değil"
    t["celik_modeli"] = kor_json["celik_modeli"]
    yol.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", yol)
    for d in t["duzeltmeler"]:
        print("  -", d[:140])
