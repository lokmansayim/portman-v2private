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
