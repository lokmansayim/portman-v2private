"""BK-76: Alpha Mini üretim dosyası okuyucuları (araclar/uretim).

Hedef örnekler gerçek üretim dosyalarıdır (Lokman'ın verdiği; 24 Kasım 2026):
- araclar/uretim/veri/kubbe/: kubbe üretim dosyası, 7 MRD FrameBuilder .csv (3 makas, 4 duvar).
- testler/uretim/veri/celik_90m2/: 90 m² çelik evin 7 BadeCAD .bde dosyası (53 pano, 1390 çubuk).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from araclar.uretim import bde, mrd

KOK = Path(__file__).resolve().parents[2]
KUBBE = sorted((KOK / "araclar/uretim/veri/kubbe").glob("*.csv"))
CELIK = sorted((KOK / "testler/uretim/veri/celik_90m2").glob("*.bde"))


def test_dosyalar_yerinde():
    assert len(KUBBE) == 7
    assert len(CELIK) == 7


@pytest.mark.parametrize("yol", KUBBE, ids=lambda p: p.name)
def test_mrd_bayt_bayt(yol):
    assert mrd.yaz(mrd.oku(yol)) == yol.read_bytes()


@pytest.mark.parametrize("yol", CELIK, ids=lambda p: p.name)
def test_bde_bayt_bayt(yol):
    assert bde.yaz(bde.oku(yol)) == yol.read_bytes()


def test_bde_90m2_sayilar():
    panolar = cubuk = 0
    boy = 0.0
    for y in CELIK:
        v = bde.oku(y)
        panolar += len(bde.panolar(v))
        cubuk += len(v["cubuklar"])
        boy += sum(c["boy"] for c in v["cubuklar"])
    assert (panolar, cubuk, round(boy / 1000, 1)) == (53, 1390, 1416.4)


def test_bde_vida_yerleri_birlesimde():
    """Vida sırttan 27 mm, ağız tarafında: 4910 vidanın hepsi birleşimde; 22,5 mm denirse çoğu düşer."""
    tut = top = tut_yanlis = 0
    for y in CELIK:
        v = bde.oku(y)
        a, b = bde.vida_denetimi(v)
        tut, top = tut + a, top + b
        tut_yanlis += bde.vida_denetimi(v, sirttan=22.5)[0]
    assert (tut, top) == (4910, 4910)
    assert tut_yanlis < 0.7 * top


def test_kubbe_ozet():
    o = {y.name: mrd.ozet(mrd.oku(y)) for y in KUBBE}
    assert [o[k]["cubuk"] for k in sorted(o)] == [17, 8, 8, 13, 15, 13, 7]
    assert o["KUBBE-DUVAR-2.csv"]["dis_olcu_mm"] == [1323.9, 2074.0]
    assert sum(x["islem"]["DIMPLE"] for x in o.values()) == 266


def test_kubbe_json_komutla_ayni(tmp_path):
    cikti = tmp_path / "kubbe.json"
    r = subprocess.run([sys.executable, "-m", "araclar.uretim", str(KOK / "araclar/uretim/veri/kubbe"), "--json", str(cikti)],
                       cwd=KOK, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(cikti.read_text()) == json.loads((KOK / "araclar/uretim/veri/kubbe.json").read_text())
