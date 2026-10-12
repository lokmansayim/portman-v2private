#!/usr/bin/env python3
"""KT-02 · "ne olur" girdisi (yalnız bilgi): düzeltilmiş B girdisinde iki kural sorusu, gerçek listedeki gibi cevaplanmış sayılır.

    1) Açık sundurma bina alanına girmez: bina alanı 90 m² (montaj paftasındaki alan: veranda dahil, sundurma hariç; bizim oturumumuz
       sundurma dahil 92,27 m², sundurma 1,53 × 1,50 = 2,29 m²). Alana bağlı satırlar: uçlar, inox taş, RYSB vidası, izole bant, 5,5 × 60 vida.
    2) Veranda korkuluğu dış cephe Boardex'ine girmez (gerçek listede korkuluk Betopan). Betopan satırı motorda yok; listedeki 3 levha
       korkuluğun bir yüzüne uyuyor (6,68 m² ÷ 3,125 m² → 3; iki yüzü 13,35 m² → 5).

Kurallar değişmez; bu dosya kural değil, iki sorunun cevabının listeye etkisini ölçmek içindir (`kt02_kiyas.py --ne-olur-b`).
Kullanım: python kt02_ne_olur.py sonuc/KT02_duzeltilmis_B_girdi.json sonuc/KT02_ne_olur_B_girdi.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BINA_M2 = 90        # montaj paftasındaki alan (veranda dahil, açık sundurma hariç)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    kaynak, hedef = Path(sys.argv[1]), Path(sys.argv[2])
    g = json.loads(kaynak.read_text(encoding="utf-8"))       # yöntemi kıyas denetler (listenin `yontem`i omega_asik olmalı)
    d = g["dis"]
    korkuluk = [y for y in d["yuzler"] if y["sinif"] == "korkuluk"]
    if not korkuluk or any(y["bosluklar"] for y in korkuluk):
        raise SystemExit("Girdide boşluksuz korkuluk yüzü bekleniyor")
    k_m2 = sum(y["brut_m2"] for y in korkuluk)
    d["duvar_m2"] = round(d["duvar_m2"] - k_m2, 4)
    d["yuzler"] = [y for y in d["yuzler"] if y["sinif"] != "korkuluk"]
    once = g["bina_m2"]
    g["bina_m2"] = BINA_M2
    g["kaynak"] = (g.get("kaynak") or "") + "; NE OLUR (yalnız bilgi): bina alanı 90 m² (açık sundurma hariç), korkuluk dış cephe Boardex'ine girmez"
    g.setdefault("uyarilar", []).append("Ne olur girdisi: iki kural sorusu gerçek listedeki gibi cevaplanmış sayıldı; kural değil (kt02_ne_olur.py)")
    hedef.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazıldı: {hedef} · bina alanı {once} → {BINA_M2} m² · dış cephe duvar yüzlerinden korkuluk çıktı: {len(korkuluk)} yüz, "
          f"{k_m2:.2f} m²".replace(".", ","))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
