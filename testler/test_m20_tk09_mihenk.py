"""D-142 · M-20 · Huma Çelik 45 m² bayi teklifi (TK-09 r04) mihenk taşı (D-28 madde 2 ve 3).

Lokman 20 Kasım 2026 14:47:53 UTC: "... tam buradaki yaptığımız iş milat olsun ... bu seviyede mühürle bizim mihenk taşımız olsun".
Kat planı r04 (kart 12:03:54), çatı ve dört görünüş (kart 12:05:35), kâr %25 (kart 12:08:23) onaylı. Girdi depoda: İş Emri,
20 Kasım 12:03 CRM anlık görüntüsü, Kasım istisnası (D-120), ters tavan, öneriler dahil. Motor'un planı ya da listesi, eşleme,
fiyat kodu bu teklifi değiştirirse test kırmızıdır. Bilerek yapılan fark yalnız Lokman'ın onayıyla, mühür açılıp yeni kararla
yeniden dondurulur (D-02); testi geçirmek için hedef değiştirilmez.
D-147 (23 Kasım 2026): mühür Lokman'ın sözüyle açıldı; çatı şiltesi paket fiyatı (680 TL) düzeltildi, taban 190.489,25, bayi 238.111,56."""
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

HEDEF = KOK / "testler" / "mihenk" / "TK09_r04_beklenen.json"
ALAN = ("kalem", "olcu", "birim", "adet", "birim_fiyat", "tutar", "durum", "kaynak", "kdv_orani")


@pytest.fixture(scope="module")
def H():
    return json.loads(HEDEF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def IE(H):
    return json.loads((KOK / H["girdi"]["is_emri"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def R(H, IE):
    g = H["girdi"]
    defter = F.istisnali_defter_sec(KOK / g["crm"], KOK / g["istisna"], datetime.date.fromisoformat(g["tarih"]))
    teklif = T.uret(IE, defter, T.secenekler(IE, g["tavan"]), T.kosullari_oku(None, IE), g["oneri"])
    assert len(teklif["secenekler"]) == 1
    return teklif["secenekler"][0]["fiyat"]


def test_hedef_onayli(H):
    assert H["karar"] == "D-142" and H["muhur"] == "M-20" and (KOK / "KARARLAR" / "D-142.md").exists()
    assert H["onay"]["zaman"] == "2026-11-20T14:47:53Z" and "mihenk taşımız olsun" in H["onay"]["soz"]
    # D-147: CRM 20 Kasım'dan beri cam yününün paket fiyatını yazıyor; çatı şiltesi 680 TL/paket (Lokman 23 Kasım 11:10:32 "mührü aç ve düzelt")
    assert H["duzeltme"]["karar"] == "D-147" and (KOK / "KARARLAR" / "D-147.md").exists() and "mührü aç" in H["duzeltme"]["soz"]


def test_plan_hedefle_ayni(H, IE):
    from motor import dxf_out, geometry
    plan = geometry.kur(IE)
    assert dxf_out.alan_yazisi(plan) == H["plan"]["alan_yazisi"] == "43,69 m² brüt · 40,63 m² net"
    assert len(plan.panolar) == H["plan"]["pano"] == 29


def test_satirlar_hedefle_ayni(H, R):
    bugun = [{k: s.get(k) for k in ALAN} for s in R["satirlar"]]
    hedef = H["satirlar"]
    eksik = [f"{s['kalem']} | {s['olcu']}" for s in hedef if s not in bugun]
    fazla = [f"{s['kalem']} | {s['olcu']}" for s in bugun if s not in hedef]
    assert not eksik and not fazla, f"hedefte olup değişen: {eksik}; yeni ya da değişen: {fazla}"
    assert bugun == hedef, "satırların sırası değişti"


def test_toplamlar_hedefle_ayni(H, R):
    oz, h = R["ozet"], H["ozet"]
    assert (oz["satir"], oz["fiyatli"], len(oz["fiyatsiz"])) == (h["satir"], h["fiyatli"], len(h["fiyatsiz"])) == (105, 102, 1)
    assert oz["toplam"] == h["toplam"] == 190489.25
    assert oz["gruplar"] == h["gruplar"]


def test_bayi_birim_fiyati(H, R):
    assert round(R["ozet"]["toplam"] * (1 + H["bayi"]["kar"]), 2) == H["bayi"]["birim"] == 238111.56
    assert H["bayi"]["kdv_orani"] == 0
