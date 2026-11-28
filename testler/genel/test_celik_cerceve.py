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


def test_sacak_makasin_parcasi_ic_kesim_15():
    # Lokman 28.11 14:16 "saçaklar olmadı makas şeklinde yeniden çiz", "15'er cm kesince oturdu"
    k = C.kur(_t())
    assert k["sacak_cm"] == 30
    assert [m["uclar_cm"] for m in k["makaslar"]] == [[-30, 885], [915, 1785], [1815, 2685], [2715, 3585], [3615, 4530]]
    for m in k["makaslar"]:
        xs = [x / 10 + m["aks"][0] for c in m["cubuklar"] for x in (c["x1"], c["x2"])]
        assert min(xs) >= m["uclar_cm"][0] - 1e-6 and max(xs) <= m["uclar_cm"][1] + 1e-6
    ic = [c for m in k["makaslar"] for c in m["cubuklar"] if c["ad"] == "KES"]
    assert len(ic) == 8                                   # dört iç birleşim × iki makas
    og = C.cizim_ogeleri(k)
    xs = [p[0] for cz in og["on"]["makas"] for p in cz]
    assert min(xs) == -30 and max(xs) == 4530
    ys = [p[0] for cz in og["yan"]["makas"] for p in cz]
    assert min(ys) == -30 and max(ys) == 2530


def test_ters_mahya_ic_akslarda():
    # Lokman 28.11 14:14:23 "oraya özel ters mahya gelecek": dört iç aks, boy 2500 + 2 × 30
    k = C.kur(_t())
    assert [(tm["aks"], tm["boy_cm"]) for tm in k["ters_mahya"]] == [(900, 2560), (1800, 2560), (2700, 2560), (3600, 2560)]
    og = C.cizim_ogeleri(k)
    assert len(og["on"]["ters_mahya"]) == 8


def test_uc_boyut_ciktilar(tmp_path):
    """3B görünüm (Lokman 28.11 14:19:59 "3 boyutlu verebilir misin?"): iki boyutlu çizimin hesabından, yeni parça yok."""
    import ezdxf
    from motor.genel import celik_cerceve, celik_cerceve_3b

    k = celik_cerceve.uret(TANIM, tmp_path)
    for uz in ("png", "dxf", "html"):
        assert (tmp_path / f"CD4525_iskelet_3b.{uz}").stat().st_size > 1000
    og = celik_cerceve_3b.ogeler(k)
    s = celik_cerceve_3b.sayim(og)
    assert s["MAKAS"] == 4 * sum(m["cubuk"] for m in k["makaslar"])
    assert s["KUSAK"] == 6 and s["MAHYA"] == 5 and s["TERS_MAHYA"] == 4 * 7
    zs = [p[2] for _, p, q in og] + [q[2] for _, p, q in og]
    tepe = k["kolon_yuksekligi"] + max(max(c["y1"], c["y2"]) for m in k["makaslar"] for c in m["cubuklar"]) / 10
    assert min(zs) == 0 and max(zs) == pytest.approx(tepe, abs=0.1)
    doc = ezdxf.readfile(tmp_path / "CD4525_iskelet_3b.dxf")
    assert len(doc.modelspace().query("LINE")) == len(og)
