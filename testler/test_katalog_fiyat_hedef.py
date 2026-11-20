"""D-128 · 60 m² katalog evinin (P6001 r03) fiyat listesi hedef örneği (D-28 madde 2 ve 3).

Lokman 19 Kasım 2026 19:51:44 UTC "onaylıyorum" dedi: 17 Kasım'da main'deki kodla üretilen liste (116 satır, KDV hariç
279.017,06 TL). Girdi depoda: İş Emri, 16 Kasım 06:19 CRM anlık görüntüsü, Kasım istisnası (D-120), tarih 17.11.2026, öneriler dahil.
Motor'un listesi, eşleme, D-119 ya da D-120 kodu değişip bu listeyi değiştirirse test kırmızıdır. Fark bilerek yapıldıysa hedef
yalnız Lokman'ın onayıyla ve gerekçeli kararla yeniden dondurulur (D-02); testi geçirmek için hedef değiştirilmez."""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import fiyatla as F  # noqa: E402
from araclar import teklif as T  # noqa: E402

HEDEF = KOK / "testler" / "katalog_fiyat" / "P6001_r03_beklenen.json"
ALAN = ("kalem", "olcu", "birim", "adet", "birim_fiyat", "tutar", "durum", "kaynak", "kdv_orani")


@pytest.fixture(scope="module")
def H():
    return json.loads(HEDEF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def R(H):
    g = H["girdi"]
    ie = json.loads((KOK / g["is_emri"]).read_text(encoding="utf-8"))
    defter = F.istisnali_defter_sec(KOK / g["crm"], KOK / g["istisna"], datetime.date.fromisoformat(g["tarih"]))
    teklif = T.uret(ie, defter, T.secenekler(ie, None), T.kosullari_oku(None, ie), g["oneri"])
    assert len(teklif["secenekler"]) == 1
    return teklif["secenekler"][0]["fiyat"]


def test_hedef_onayli(H):
    assert H["karar"] == "D-128" and (KOK / "KARARLAR" / "D-128.md").exists()
    assert H["onay"]["soz"] == "onaylıyorum" and H["onay"]["zaman"] == "2026-11-19T19:51:44Z"


def test_satirlar_hedefle_ayni(H, R):
    bugun = [{k: s.get(k) for k in ALAN} for s in R["satirlar"]]
    hedef = H["satirlar"]
    eksik = [f"{s['kalem']} | {s['olcu']}" for s in hedef if s not in bugun]
    fazla = [f"{s['kalem']} | {s['olcu']}" for s in bugun if s not in hedef]
    assert not eksik and not fazla, f"hedefte olup değişen: {eksik}; yeni ya da değişen: {fazla}"
    assert bugun == hedef, "satırların sırası değişti"


def test_toplamlar_hedefle_ayni(H, R):
    oz, h = R["ozet"], H["ozet"]
    assert (oz["satir"], oz["fiyatli"], oz["fiyatsiz"]) == (h["satir"], h["fiyatli"], h["fiyatsiz"]) == (116, 116, [])
    assert oz["toplam"] == h["toplam"] == 279017.06
    assert (oz["kdv"]["kdv"], oz["kdv"]["dahil"]) == (h["kdv"], h["kdv_dahil"]) == (45125.57, 324142.63)
    assert oz["gruplar"] == h["gruplar"]
