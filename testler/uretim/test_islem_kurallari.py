"""BK-78: çerçeve geometrisinden makine işlemleri (araclar/uretim/islem.py).

Kurallar Diamond 70 m² (17 dosya) ve DUVAR1 örnek panosundan çıktı (Mac `Alpha mini AI/_inceleme/IS-8, IS-9`).
Kubbe üretim dosyası (7 dosya, BK-76) kural yazılırken hiç kullanılmadı: kör sınama.
Tolerans 0,6 mm (dosyadaki sayılar SketchUp çizimindeki 0,01 mm'lik oynamaları taşır).
Bilinen tek fark: makas tepesinde iki üst başlıktan hangisinin köşeleneceği geometriden belli olmuyor
(Diamond MKS04'te ve kubbe K-MKS-14'te ikinci başlık; öteki 10 makasta birinci).
"""
from pathlib import Path

from araclar.uretim import islem, mrd

KOK = Path(__file__).resolve().parents[2]
DIAMOND = sorted((KOK / "testler/uretim/veri/diamond_70m2").glob("*.csv"))
DUVAR1 = [KOK / "testler/uretim/veri/duvar1/DUVAR1.csv"]
KUBBE = sorted((KOK / "araclar/uretim/veri/kubbe").glob("*.csv"))


def _topla(dosyalar):
    toplam: dict[str, list[int]] = {}
    for y in dosyalar:
        v = mrd.oku(y)
        for tur, (tut, dosya, fazla) in islem.kiyas(v["parcalar"], islem.uret(v["parcalar"])).items():
            t = toplam.setdefault(tur, [0, 0, 0])
            t[0] += tut
            t[1] += dosya
            t[2] += fazla
    return {k: tuple(v) for k, v in toplam.items()}


def test_veri_yerinde():
    assert (len(DIAMOND), len(KUBBE)) == (17, 7)
    for y in DIAMOND + DUVAR1:
        assert mrd.yaz(mrd.oku(y)) == y.read_bytes()


def test_diamond():
    assert _topla(DIAMOND) == {
        "CUT": (362, 362, 0), "DIMPLE": (1286, 1286, 0), "LIP_CUT": (787, 788, 1),
        "NOTCH": (20, 20, 0), "SWAGE": (685, 686, 1),
    }


def test_duvar1():
    assert _topla(DUVAR1) == {
        "CUT": (28, 28, 0), "DIMPLE": (100, 100, 0), "LIP_CUT": (64, 64, 0),
        "NOTCH": (12, 12, 0), "SWAGE": (55, 55, 0),
    }


def test_kubbe_kor():
    assert _topla(KUBBE) == {
        "CUT": (81, 81, 0), "DIMPLE": (266, 266, 0), "LIP_CUT": (174, 175, 1),
        "NOTCH": (12, 12, 0), "SWAGE": (164, 165, 1),
    }


def test_islemli_dosya_okunur_ve_kiyaslanir(tmp_path):
    """Üretilen işlemlerle yazılan dosya yeniden okunur; kubbe duvarlarında işlemler dosyadakilerle aynı."""
    y = KOK / "araclar/uretim/veri/kubbe/KUBBE-DUVAR-2.csv"
    v = mrd.oku(y)
    hedef = tmp_path / "D2.csv"
    hedef.write_bytes(mrd.yaz(islem.islemli(v)))
    w = mrd.oku(hedef)
    k = islem.kiyas(v["parcalar"], [p["islemler"] for p in w["parcalar"]], haric=())
    assert all(t == d and f == 0 for t, d, f in k.values())
