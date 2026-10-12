#!/usr/bin/env python3
"""KT-03 · "ne olur" girdisi (yalnız bilgi): düzeltilmiş B girdisinde iki kural sorusu, gerçek listedeki gibi cevaplanmış sayılır.

    1) Çatı panelli veranda ve sundurma çatısının kenarları listedeki gibi: saçaklarında dere var (iki hat, dört serbest uç: dere kapağı;
       iniş kuralı her serbest uca bir iniş koyar), eğik kenarlarında alın sacı var; Boardex şeridi (10 + 15 cm) yok; veranda ve sundurma
       tavanı çatının planı kadar (saçağıyla). Listedeki "özel büküm saçak sacı" satırı motorda yok; bu girdiyle çıkmaz.
    2) Kırma uçlarının çatı panelleri de çatı paneli satırında, paftadaki numaralarla: Ç01–Ç18 (Ç10 yok) = 17 panel.

Kurallar değişmez; bu dosya kural değil, iki sorunun cevabının listeye etkisini ölçmek içindir (`kt03_kiyas.py --ne-olur-b`).
Kullanım: python kt03_ne_olur.py sonuc/KT03_duzeltilmis_B_girdi.json sonuc/KT03_ne_olur_B_girdi.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

CATI_PANELI_PAFTADA = 17     # makas ve dere paftasında Ç01–Ç18, Ç10 numarası yok


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    kaynak, hedef = Path(sys.argv[1]), Path(sys.argv[2])
    g = json.loads(kaynak.read_text(encoding="utf-8"))       # yöntemi kıyas denetler (listenin `yontem`i omega_asik olmalı)
    c, d = g["cati"], g["dis"]
    ek = c.get("ek_cati")
    if not ek or not c.get("panelli_cati_adi"):
        raise SystemExit("Girdide ek yapısız çatı panelli çatı (veranda, sundurma) bekleniyor")
    # 1) panel çatının saçakları: saçak kenarlarından dere hatları çıkınca kalanlar
    kalan = Counter(c["sacak_kenarlari_m"]) - Counter(c["dere"]["hatlar_m"])
    panel_sacak = sorted(kalan.elements(), reverse=True)
    if abs(sum(panel_sacak) - ek["sacak_m"]) > 0.01:
        raise SystemExit(f"Panel çatının saçakları tutmuyor: {panel_sacak} ≠ {ek['sacak_m']}")
    dr = c["dere"]
    dr["hatlar_m"] = dr["hatlar_m"] + panel_sacak
    dr["boy_m"] = round(dr["boy_m"] + sum(panel_sacak), 4)
    dr["uc"] += 2 * len(panel_sacak)
    dr["serbest_uc"] += 2 * len(panel_sacak)
    c["kose_adedi"] += 2 * len(panel_sacak)
    c["alin_saci_m"] = round((c.get("alin_saci_m") or 0) + ek["alin_m"], 4)
    once = len(d["ek_m2"])
    d["ek_m2"] = [x for x in d["ek_m2"] if not x["ad"].startswith("çatı panelinin saçak ve alın kaplaması")]
    if len(d["ek_m2"]) != once - 1:
        raise SystemExit("Dış cephe Boardex'inde çatı panelinin kenar şeridi bulunamadı")
    v_once = g["veranda_m2"]["brut"]
    g["veranda_m2"]["brut"] = g["celik"]["ek_cati_paneli"]["plan_m2"]
    g["tavan_m2"]["yesil"] = round(g["tavan_m2"]["yesil"] + g["veranda_m2"]["brut"] - v_once, 2)    # yeşil tavan veranda tavanını içerir; ıslak hacim aynı kalır
    # 2) kırma uçlarının çatı panelleri
    cp = g["celik"]["ek_cati_paneli"]
    ek_adet = CATI_PANELI_PAFTADA - cp["adet"]
    cp.update({"ad": "Çatı panelleri (kırma uçları, veranda ve sundurma)", "adet": CATI_PANELI_PAFTADA})
    if "celik_panel_adedi" in g:
        g["celik_panel_adedi"] += ek_adet
    g["kaynak"] = (g.get("kaynak") or "") + ("; NE OLUR (yalnız bilgi): veranda ve sundurma çatısında dere, iniş ve alın sacı var, Boardex şeridi yok, "
                                             "tavanı saçağıyla; kırma uçlarının çatı panelleri paftadaki adetle")
    g.setdefault("uyarilar", []).append("Ne olur girdisi: iki kural sorusu gerçek listedeki gibi cevaplanmış sayıldı; kural değil (kt03_ne_olur.py)")
    hedef.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {hedef} · dere hatlarına {panel_sacak} m eklendi, köşe {c['kose_adedi']}, serbest uç {dr['serbest_uc']}, alın sacı {c['alin_saci_m']} m; "
          f"veranda tavanı {v_once} → {g['veranda_m2']['brut']} m²; çatı paneli {CATI_PANELI_PAFTADA - ek_adet} → {CATI_PANELI_PAFTADA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
