#!/usr/bin/env python3
"""KT-03 Yapı Tanımı 0.5, kıyastan sonra düzeltilmiş hali. Dondurulan tanım (`kt03_tanim_uret.py`) değişmez; düzeltmeler burada, kaynağıyla.
Yalnız girdi hataları düzeltilir (projenin belgesinde olup yanlış okuduğumuz şeyler); kural ve karar farkları kurallarda kalır.

Kullanım: python kt03_tanim_duzeltilmis.py KT03_duzeltilmis.json KT03.json   (KT03.json: dondurulan tanım; betikteki tanımla aynı olmalı)
"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kt03_tanim_uret as kor      # noqa: E402

t = copy.deepcopy(kor.tanim)
r2 = kor.r2
duzeltmeler = []

# 1) Makas adedi. Makas ve dere paftasında makaslar MK02–MK13 ve MK15–MK36: 34 makas (MK01 ve MK14 numaraları yok). Dondurulan tanımda
#    numaraların kesintisiz olduğu varsayılıp 36 sayılmıştı. Gerçek listede de 34 (4 × 1,2 mm + 30 × 0,8 mm).
mk = t["cati"]["makaslar"]
mk["diger"]["adet"] -= 2
mk["diger"]["not"] = "kırma uçlarının, köşelerin ve vadilerin makasları (MK13, MK15–MK36; MK01 ve MK14 numarası paftada yok)"
assert sum(v["adet"] for v in mk.values()) == 34
duzeltmeler.append("Makas 34 (paftada MK01 ve MK14 numarası yok): dondurulan tanımda numaralar kesintisiz sayılıp 36 yazılmıştı (girdi hatası)")

# 2) Veranda ve sundurma çatısının saçak çizgisi. Makas ve dere paftasında iniş işaretleri ve çatı panellerinin kenarı: veranda çatısının batı saçağı
#    x = −52,8, sundurma çatısının doğu saçağı x = 1077,4 (ana çatının doğu saçağından 8 cm dışarıda). Dondurulan tanımda ikisi de duvar paneli
#    paftasındaki kesit detayından okunmuştu (−51,72 ve 1069,1). Eğimler ve bina duvarındaki kotlar aynı (kesitten).
adli = {d["ad"]: d for d in t["cati"]["duzlemler"]}
XV, XS = -52.8, 1077.4
v = adli["veranda"]
v["plan"] = [[XV if x == v["sacak"]["x"] else x, y] for x, y in v["plan"]]
v["sacak"] = {"x": XV}
v["sacak_kotu"] = r2(224.6 + v["egim"] * XV)
s = adli["sundurma"]
s["plan"] = [[914.2, 378.4], [XS, 378.4], [XS, 540.5], [1069.1, 540.5], [1039.1, 540.5], [914.2, 540.5]]
s["sacak"] = {"x": XS}
s["sacak_kotu"] = r2(240.0 - s["egim"] * (XS - 1031.1))
duzeltmeler.append("Veranda çatısının saçağı x = −52,8, sundurma çatısınınki x = 1077,4 (makas ve dere paftasındaki iniş işaretleri ve panel kenarları): "
                   "dondurulan tanımda kesit detayından −51,72 ve 1069,1 okunmuştu (girdi hatası; sundurma çatısı 8 cm kısaydı)")

t["kaynak"]["okunmayanlar"] = ("Bu tanım, kendi listemiz dondurulduktan (9 Ekim 2026 23:55) ve gerçek listeyle kıyaslandıktan sonra düzeltilmiş halidir. "
                               "Paftalardaki adetler (çatı kaplaması, tavan omegası, aşık, dere inişi) yine girdi değil; makas adedi paftadaki numaralardan, "
                               "saçak çizgileri paftadaki çizimden düzeltildi.")
t["duzeltmeler"] = duzeltmeler

if __name__ == "__main__":
    yol, kor_yolu = Path(sys.argv[1]), Path(sys.argv[2])
    kor_json = json.loads(kor_yolu.read_text(encoding="utf-8"))
    assert kor_json == json.loads(json.dumps(kor.tanim, ensure_ascii=False)), "dondurulan tanım betikteki tanımla aynı değil"
    yol.write_text(json.dumps(t, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı", yol)
    for d in t["duzeltmeler"]:
        print("  -", d[:150])
    for d in t["cati"]["duzlemler"][-2:]:
        print("  ", d["ad"], d["plan"], d["sacak"], d["sacak_kotu"])
