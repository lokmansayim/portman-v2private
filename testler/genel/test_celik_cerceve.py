"""İE-47: çelik karkas iskelet çizimi (kafes kolon + kafes makas). Beklenen değerler Lokman'ın 28 Kasım 2026 sözlerinden
(`modeller/cerceve/CD4525_cerceve.json › kaynak`): 45,00 × 25,00 m, makas 9 m'yi geçmez, ara kolon 120 (60 + 60), uç 60, %33."""
import json
from pathlib import Path

import pytest

from motor.genel import celik_cerceve as C

KOK = Path(__file__).resolve().parents[2]
TANIM = KOK / "modeller/cerceve/CD4525_cerceve.json"


def _t():
    return json.loads(TANIM.read_text(encoding="utf-8"))


def test_cd4525_akslar_ve_kolonlar():
    k = C.kur(_t())
    assert k["x_akslari"] == [0, 900, 1800, 2700, 3600, 4500]
    assert k["y_akslari"] == [0, 833.33, 1666.67, 2500]
    assert k["ozet"]["kolon"] == 24
    genislik = sorted({c["x"][1] - c["x"][0] for c in k["kolonlar"]})
    assert genislik == [60, 120]
    uc = [c for c in k["kolonlar"] if c["aks"][0] in (0, 4500)]
    assert all(c["x"][1] - c["x"][0] == 60 for c in uc) and len(uc) == 8
    assert all(0 <= c["x"][0] and c["x"][1] <= 4500 and 0 <= c["y"][0] and c["y"][1] <= 2500 for c in k["kolonlar"])
    orta = next(c for c in k["kolonlar"] if c["aks"] == [900, 833.33])
    assert orta["x"] == [840, 960] and orta["y"] == [773.33, 893.33]


def test_cd4525_makaslar():
    k = C.kur(_t())
    assert k["ozet"]["makas_cercevesi"] == 5 and k["ozet"]["makas_toplam"] == 20
    for m in k["makaslar"]:
        assert m["aks"][1] - m["aks"][0] == 900 and m["mesnet_cm"] == 60 and m["egim"] == 0.33
        assert m["tepe_cm"] == 548.5 and m["cubuk"] > 10


@pytest.mark.parametrize("bozuk", [
    lambda t: t["x_akslari"].__setitem__(1, 1000),          # 1000 cm açıklık: makas geçmez
    lambda t: t.__setitem__("y_aks_sayisi", 3),              # 25 m / 2 = 1250 cm
    lambda t: t["x_akslari"].__setitem__(-1, 4400),          # dış ölçüye varmıyor
])
def test_aciklik_siniri_hata(bozuk):
    t = _t()
    bozuk(t)
    with pytest.raises(C.CerceveHatasi):
        C.kur(t)


def test_uret_ciktilar(tmp_path):
    k = C.uret(TANIM, tmp_path)
    for uzanti in ("png", "pdf", "dxf", "json"):
        assert (tmp_path / f"CD4525_iskelet.{uzanti}").stat().st_size > 0
    import ezdxf
    doc = ezdxf.readfile(tmp_path / "CD4525_iskelet.dxf")
    katman = {e.dxf.layer for e in doc.modelspace()}
    assert {"KOLON", "MAKAS"} <= katman
    assert json.loads((tmp_path / "CD4525_iskelet.json").read_text(encoding="utf-8"))["ozet"] == k["ozet"]


def test_yapi_tanimi_dis_olcu():
    from motor.genel import girdi_genel  # noqa: F401  (genel motorun okuduğu tanım)
    t = json.loads((KOK / "modeller/cerceve/CD4525.json").read_text(encoding="utf-8"))
    xs = [v for d in t["duvarlar"] for v in (d["kutu"][0], d["kutu"][2])]
    ys = [v for d in t["duvarlar"] for v in (d["kutu"][1], d["kutu"][3])]
    kap = t["yuz_kaplamalari"]["dis"]["kalinlik"]
    assert (min(xs) - kap, max(xs) + kap, min(ys) - kap, max(ys) + kap) == (0, 4500, 0, 2500)


def test_sacak_payi_30():
    # Lokman 28.11 13:51 "saçaklar 30'ar cm"; 14:11 "saçak paylarını vermeyi unutmuşsun"
    k = C.kur(_t())
    assert k["sacak_cm"] == 30
    ilk, son = k["makaslar"][0]["sacak"], k["makaslar"][-1]["sacak"]
    assert [(s["yon"], s["uc_cm"], s["boy_cm"]) for s in ilk + son] == [(-1, 0, 30), (1, 4500, 30)]
    assert all(m.get("sacak") is None for m in k["makaslar"][1:-1])
    s = ilk[0]
    assert abs((s["ust_cm"] - s["uc_ust_cm"]) - 0.33 * 30) < 0.01
    og = C.cizim_ogeleri(k)
    xs = [p[0] for cz in og["on"]["makas"] for p in cz]
    assert min(xs) == -30 and max(xs) == 4530
    ys = [p[0] for cz in og["yan"]["makas"] for p in cz]
    assert min(ys) == -30 and max(ys) == 2530
