"""D-30 · Prefabrikte son pano 122 cm ve üzeriyse proje tam panoya tamamlanır (Lokman, 29 Ekim 2026 10:48: "122 ve üzeri biten tüm
projeleri tam panoya tamamlar"). Ölçüye kesimde (`yapi.dis_olcu_cm`) son pano kesilmez, dış ölçü tam panoya büyür; eski son aks ve eski
dış ölçü yenisine eşlenir; plan uyarısı yazılır (K16)."""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

TK02 = KOK / "testler" / "motor" / "veri" / "TK02.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_tk02_tam_panoya_tamamlanir():
    """Bayinin 898 × 888'i (iki yönde son pano 125) → 898,5 × 888,5; salonun öndeki ilk panosu ve G–H sırası 125,5 (Lokman 10:46–10:47)."""
    plan = G.kur(_oku(TK02))
    assert (plan.W, plan.H) == (898.5, 888.5)
    assert [u for u in plan.uyarilar if "D-30" in u] == [
        "Dış ölçü 898 × 888 → 898,5 × 888,5 cm: son pano (x: 125, y: 125 cm) 122 ve üzeri olduğu için tam panoya (125,5) tamamlandı (D-30)"]
    boylar = Counter(round(p.boy, 2) for d in plan.duvarlar for p in d.panolar)
    assert 125.0 not in boylar and boylar[125.5] == 39
    salon_sol = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "y" and abs(d.c - 5.0) < 1e-6 and d.p0 < 10)
    assert round(salon_sol.panolar[0].boy, 2) == 125.5


@pytest.mark.parametrize("son_x, son_y, beklenen", [
    (122.0, 121.9, ("x",)),          # x tamamlanır, y kesik kalır
    (121.9, 125.0, ("y",)),
    (125.5, 125.5, ()),              # zaten tam: tamamlama yok, uyarı yok
    (100.0, 63.0, ()),
])
def test_esik_122(son_x, son_y, beklenen):
    """Eşik son panonun boyunda: 122 ve üzeri tamamlanır, altı kesilir (yarım panodan büyük her kesik eskisi gibi)."""
    G.aks_durumu_sifirla(); G.kalinlik_ayarla(10, 6)
    nx = ny = 7.0
    bx, by = G.ilk_aks("x"), G.ilk_aks("y")
    dis = {"x": 2 * bx + G.MOD * (nx - 1) + son_x, "y": 2 * by + G.MOD * (ny - 1) + son_y}
    u = G.olcu_ayarla(dis, nx, ny)
    assert tuple(sorted(G.TAMAMLAMA)) == beklenen and bool(u) == bool(beklenen)
    for yon, son, n, bas in (("x", G.X_SON, nx, bx), ("y", G.Y_SON, ny, by)):
        tam = bas + G.MOD * n
        assert son == pytest.approx(tam if yon in beklenen else dis[yon] - bas)
    G.aks_durumu_sifirla()


def test_eski_kose_yenisine_eslenir():
    """Mahal sınırı, taşan veranda ve cumba ucu eski son aksta ya da eski dış yüzde yazılmışsa yenisine gider (aynı İş Emri, ölçü yazılı)."""
    ie = _oku(TK02)
    arka = next(v for v in ie["verandalar"] if v["cephe"] == "arka")
    arka.update({"bas_cm": 637.5, "bit_cm": 898})                       # bayinin dış ölçüsünde sağ köşeye kadar
    plan = G.kur(ie)
    v = next(v for v in plan.dis_verandalar if v["cephe"] == "arka")
    assert v["rect"][2] == pytest.approx(898.5)                         # yeni dış köşe
    assert max(x for d in plan.duvarlar for x in (d.p0, d.p1) if d.yon == "x") <= 898.5
    assert G.tamamla_cm(888, "x") == 888.5 and G.tamamla_cm(898, "x") == 898.5 and G.tamamla_cm(512, "x") == 512.0


def test_tamamlanmayan_plan_ayni():
    """Dış ölçüsüz ya da son panosu 122'den kısa planlarda tamamlama yok (P6001, PK-01)."""
    for yol in (KOK / "is_emri" / "P6001_2plus1_6x6.json", KOK / "testler" / "motor" / "veri" / "PK01.json"):
        plan = G.kur(_oku(yol))
        assert not [u for u in plan.uyarilar if "D-30" in u] and G.TAMAMLAMA == {}


def test_yarim_izgarada_kisa_son_parca_tamamlanmaz():
    """Geometri hakemi (29 Ekim): yarım ızgarada ve `son_pano: kosu`da son pano koşu başından 125,5'lerle kalan parçadır (en çok 62,75);
    Yan Verandalı 6×8,5'te y 1074,25'te son parça 60,25 cm, 122'den kısa → kesilir, tamamlama ve uyarı yok (eskiden 62,75'e tamamlanıyordu)."""
    ie = _oku(KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json")
    ie["yapi"]["dis_olcu_cm"] = {"x": 773, "y": 1074.25}
    plan = G.kur(ie)
    assert plan.H == 1074.25 and "y" not in G.TAMAMLAMA and not [u for u in plan.uyarilar if "D-30" in u]
    sonlar = {round(d.panolar[-1].boy, 2) for d in plan.duvarlar if d.tur == "dis" and d.yon == "y" and abs(d.p1 - G.Y_SON) < 1e-6}
    assert sonlar == {60.25}
    # son_aks'ta son pano sondan bir önceki (yarım) akstan başlar: 60,25 + 62,75 = 123 → tamamlanır
    assert G.olcu_ayarla({"x": 773, "y": 1074.25}, 6, 8.5, "son_aks") and G.TAMAMLAMA["y"][1] == pytest.approx(G.ilk_aks("y") + G.MOD * 8.5)
    G.aks_durumu_sifirla()


def test_arka_solda_yan_veranda_ucu_kayan_derzle_eslenir():
    """Geometri hakemi (29 Ekim): dizilim arka-solda Motor y'yi arkadan sayar, tamamlama gerçek çerçevede öne düşer, iç y derzleri +0,5 kayar.
    Sol verandanın ucu gerçek çerçevededir; ön köşesi (0) aynen kalır, iç derzdeki ucu (506,5) derzle birlikte 507'ye, arka köşesi 888 → 888,5."""
    ie = _oku(TK02)
    ie["verandalar"].append({"ad": "SOL VERANDA", "cephe": "sol", "bas_cm": 0, "bit_cm": 506.5, "derinlik_cm": 150})
    plan = G.kur(ie)
    sol = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "y" and abs(d.c - 5.0) < 1e-6)
    derzler = {round(sol.p0 + sum(p.boy for p in sol.panolar[:i]), 2) for i in range(1, len(sol.panolar))}
    assert 507.0 in derzler and 506.5 not in derzler
    v = next(v for v in plan.dis_verandalar if v["cephe"] == "sol")
    assert (v["rect"][1], v["rect"][3]) == (0.0, 507.0)
    assert G.tamamla_gercek_cm(0, "y") == 0.0 and G.tamamla_gercek_cm(888, "y") == 888.5 and G.tamamla_gercek_cm(898, "x") == 898.5
    assert G.tamamla_gercek_cm(256, "x") == 256.0                       # x aynalanmaz: iç değer aynen


def test_dikme_koseyle_kayar():
    """Dikme (gerçek çerçeve, sol alt köşe) merkeziyle eşlenir: TK-02'nin sağ ön köşesindeki dikme x'te köşeyle 888 → 888,5'e kayar, y'de ön
    yüzde (arka-solda tamamlama öne düşse de gerçek çerçevede ön yüz yerinde) 0 kalır; iç değer aynen."""
    ie = _oku(TK02)
    ie["dikmeler"] = [[888, 0], [256, 0]]
    plan = G.kur(ie)
    assert plan.dikmeler[:2] == [(888.5, 0.0, 898.5, 10.0), (256.0, 0.0, 266.0, 10.0)]
    assert G.tamamla_gercek_cm(888, "x") == 888.5 and G.tamamla_gercek_cm(887.9, "x") == 887.9
