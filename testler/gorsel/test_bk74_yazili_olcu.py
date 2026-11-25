"""BK-74 (D-152; Lokman, kart 24 Kasım 2026 06:56:26 UTC "Çeyrek panoya kadar kaydırsın"): bayinin çizimde yazdığı oda ölçüsü en
yakın pano aksına çeyrek panoya (31,375 cm) kadar oturur, bayiye notla yazılır; iki aks eşit yakınsa sorulur, aynı sınır için tek soru.
Pano oturunca oda alanı en çok %25 değişebilir. LLM yok: girdi sunucunun 23 Kasım Opus 5.5 okumasıdır (`veri/BK74_TK04_okuma.json`,
kampanyalı 80 m² el krokisi; bayi çizimi depoya girmez). Hedef örnek Lokman'ın onayladığı TK-04 r08 planıdır (proje dosyaları
Teklif_Calisma/TK-04/is_emri_r08.json): sol yarıda salon, banyo, hol ve yatak odası 1 aynı yerde. Sağ kenar 840 ↔ 888,5 farkı
Lokman'ın sonradan verdiği "yarım pano sağa uzat" revizyonudur (r03), bu işin konusu değildir.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import gorsel_okuma as GO  # noqa: E402
from motor import geometry as G  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"

# TK-04 r08 (onaylı) mahallerinin sol yarısı
R08 = {"YATAK ODASI 1": [[5, 10, 318.75, 386.5]], "BANYO": [[318.75, 10, 507, 261]],
       "HOL": [[318.75, 261, 507, 386.5], [381.5, 386.5, 507, 700.25]], "SALON": [[5, 386.5, 381.5, 888.5]]}


def okuma() -> dict:
    o = json.loads((VERI / "BK74_TK04_okuma.json").read_text(encoding="utf-8"))
    return {**o, "emin_olunamayanlar": []}          # bayi okuyucunun kendi sorularına "doğru" der


def test_tk04_yazili_410_aksa_oturur_plan_cizilir():
    den = GO.denetle(okuma())
    assert not den["sorular"], den["sorular"]
    ie = den["cevrim"]["is_emri"]
    mh = {m["ad"]: [[round(v, 2) for v in q] for q in m["konum_cm"]] for m in ie["mahaller"]}
    for ad, konum in R08.items():
        assert mh[ad] == konum, (ad, mh[ad])
    assert any("yazılı oda ölçülerini en yakın pano aksına oturttum" in n and "410 → 381,5 cm" in n for n in den["notlar"]), den["notlar"]
    p = G.kur(copy.deepcopy(ie))
    alan = {m.ad: round(m.alan_m2, 2) for m in p.mahaller.values() if m.poly is not None}
    assert (alan["SALON"], alan["BANYO"], alan["YATAK ODASI 1"], alan["HOL"]) == (18.35, 4.52, 11.42, 5.9)   # r08 ile aynı


def test_yazili_sinir_iki_aksa_esit_uzaksa_bir_kez_sorulur():
    """Mahya girişten arkaya (makas x, ızgara 10'dan): 355 cm 323,75 ve 386,5 akslarına 31,25 / 31,5 cm; hangisi olduğunu kod seçmez.
    Hol, salon ve giriş aynı sınırı paylaşır: tek soru (önce üç kez soruluyordu)."""
    o = okuma()
    o["cati"] = {**o["cati"], "mahya": "giristen_arkaya"}
    for z in o["zincirler"]:
        if z["kenar"] == "alt":
            z["olculer_cm"] = [355.0, 485.0]
    for x in o["odalar"]:
        x["dikdortgenler"] = [[355.0 if v == 410.0 else v for v in r] for r in x["dikdortgenler"]]
    den = GO.denetle(o)
    assert den["cevrim"] is None
    s = [q for q in den["sorular"] if "(355 cm) pano ızgarasına oturmuyor" in q]
    assert len(s) == 1, den["sorular"]
