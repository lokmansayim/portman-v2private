"""BK-56: montaj paftasının (kart modelinin yerleşim planları) düzenlenebilir DXF'i, PDF'i çizen sayfaların kendisinden (D-28 madde 1).

Hedef örnek 85 m² katalog evi (`is_emri/P8501_r04.json`; r05 PR #267'de). Kıyas: PDF'in bayt bayt aynı kalması, DXF'in yedi sayfası,
her sayfada PDF'teki yazıların DXF'te de olması, planların gerçek ölçekte (cm) modeldeki duvarlarla aynı ölçüde durması, denetim.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

ezdxf = pytest.importorskip("ezdxf")
pymupdf = pytest.importorskip("pymupdf")

from motor import kart_model as KM  # noqa: E402
from motor.yerlesim import cizim  # noqa: E402
from motor.yerlesim import dxf_yaz  # noqa: E402

IE = KOK / "is_emri" / "P8501_r04.json"


@pytest.fixture(scope="module")
def cikti(tmp_path_factory):
    """PDF'in baytları komutla, iki ayrı süreçte kıyaslanır (aynı süreçte art arda iki üretimin PDF'i bugün de bayt bayt aynı değil:
    matplotlib'in süreç içi sayaçları; DXF'ten bağımsız)."""
    import subprocess
    a, b = tmp_path_factory.mktemp("pdfli"), tmp_path_factory.mktemp("dxfli")
    for k, ek in ((a, []), (b, ["--dxf"])):
        subprocess.run([sys.executable, "-m", "motor.kart_model", str(IE), str(k), "--kod", "P8501", *ek], cwd=KOK, capture_output=True,
                       timeout=600)
    c = tmp_path_factory.mktemp("surec_ici")
    say = KM.uret(KM._oku(IE), c, "P8501", dxf=True)
    return {"a": a, "b": b, "say": say, "dxf": b / "P8501_yerlesim_planlari.dxf", "pdf": b / "P8501_yerlesim_planlari.pdf"}


def test_pdf_ayni(cikti):
    """DXF istense de istenmese de PDF bayt bayt aynı (sayfa önce PDF'e yazılır)."""
    assert (cikti["a"] / "P8501_yerlesim_planlari.pdf").read_bytes() == cikti["pdf"].read_bytes()
    assert not (cikti["a"] / "P8501_yerlesim_planlari.dxf").exists()


def test_denetim_ve_sayfalar(cikti):
    d = cikti["say"]["montaj_dxf"]
    assert d["dosya"] == "P8501_yerlesim_planlari.dxf" and d["denetim_hatasi"] == 0 and d["sayfa"] == 7
    doc = ezdxf.readfile(cikti["dxf"])
    assert doc.units == 5 and doc.dxfversion == "AC1032"                       # cm, R2018
    assert not doc.audit().errors
    msp = doc.modelspace()
    sayfa = [e for e in msp if e.dxf.layer == dxf_yaz.SAYFA_KATMANI]
    assert len(sayfa) == len(pymupdf.open(cikti["pdf"])) == 7
    basliklar = [s["ad"] for s in d["sayfalar"]]
    for i, ad in enumerate(("TAVAN OMEGA", "MAKAS VE DERE", "BAŞ MAKAS BETOPAN", "AŞIK", "ÇATI KAPLAMASI", "ELEKTRİK", "ALT ÇERÇEVE"), 1):
        assert ad in basliklar[i - 1]
        assert any(e.dxf.layer.startswith(f"S{i}_") for e in msp)
    # sayfalar yan yana, binmez
    x = [s["sayfa_cm"] for s in d["sayfalar"]]
    assert all(x[i][2] < x[i + 1][0] for i in range(6))


def _kelimeler(s: str) -> set[str]:
    return {w for w in re.split(r"\s+", s.replace("\\P", " ").replace(" ", " ")) if w}


def test_yazilar_pdf_ile_ayni(cikti):
    """Her sayfada PDF'in bütün kelimeleri DXF'in yazılarında (MTEXT) var; DXF kendi kelimesini eklemez."""
    doc = ezdxf.readfile(cikti["dxf"])
    pdf = pymupdf.open(cikti["pdf"])
    for i in range(1, 8):
        dxf_k = set()
        for e in doc.modelspace().query("MTEXT"):
            if e.dxf.layer.startswith(f"S{i}_"):
                dxf_k |= _kelimeler(e.plain_text())
        pdf_k = _kelimeler(pdf[i - 1].get_text())
        assert pdf_k <= dxf_k, (i, sorted(pdf_k - dxf_k)[:10])
        assert dxf_k <= pdf_k, (i, sorted(dxf_k - pdf_k)[:10])


def test_gercek_olcek(cikti):
    """Planlı sayfalarda duvarlar modeldeki ölçüyle (cm) durur: DXF'teki duvar kapsamının eni ve boyu modelin duvarlarınınkiyle aynı."""
    from shapely.ops import unary_union
    from ezdxf import bbox
    m = cizim._model(cikti["b"] / "P8501_model.ifc")
    x0, y0, x1, y1 = unary_union(m["duvar"]).bounds
    doc = ezdxf.readfile(cikti["dxf"])
    for i in (1, 2, 4, 5, 6):
        b = bbox.extents([e for e in doc.modelspace() if e.dxf.layer == f"S{i}_DUVAR" and e.dxftype() == "LWPOLYLINE"])
        assert b.size.x == pytest.approx(x1 - x0, abs=0.01) and b.size.y == pytest.approx(y1 - y0, abs=0.01), i
    # 7. sayfada iki plan (zemin ve çatı), ikisinin de duvarları gerçek ölçekte
    duvar7 = sorted((e for e in doc.modelspace() if e.dxf.layer == "S7_DUVAR" and e.dxftype() == "LWPOLYLINE"),
                    key=lambda e: bbox.extents([e]).center.x)
    assert len(duvar7) == 2 * len(m["duvar"])
    for grup in (duvar7[:len(m["duvar"])], duvar7[len(m["duvar"]):]):
        b = bbox.extents(grup)
        assert b.size.x == pytest.approx(x1 - x0, abs=0.01) and b.size.y == pytest.approx(y1 - y0, abs=0.01)
    # 3. sayfa: her betopan levhası modeldeki levhanın ölçüsünde (görünüşte en × yükseklik)
    import numpy as np
    model_l = set()
    for lv in m["k2"]["BT-01"]:
        v = lv["v"]
        en = max(np.ptp(v[:, 0]), np.ptp(v[:, 1]))
        model_l.add((round(float(en), 1), round(float(np.ptp(v[:, 2])), 1)))
    dxf_l = set()
    for e in doc.modelspace():
        if e.dxf.layer == "S3_BETOPAN" and e.dxftype() == "LWPOLYLINE":
            bb = bbox.extents([e])
            dxf_l.add((round(bb.size.x, 1), round(bb.size.y, 1)))
    assert model_l and model_l <= dxf_l, sorted(model_l - dxf_l)


def test_katman_ve_renk(cikti):
    doc = ezdxf.readfile(cikti["dxf"])
    adlar = {k.dxf.name for k in doc.layers}
    assert {"S1_DUVAR", "S1_YAZI", "S1_PAFTA", "S2_MAKAS", "S2_DERE", "S4_ASIK", "S7_AC-01", "S7_CK-01"} <= adlar
    makas = next(e for e in doc.modelspace() if e.dxf.layer == "S2_MAKAS" and e.dxftype() == "HATCH")
    assert makas.rgb == (0x2c, 0x3e, 0x50)                                     # cizim.RENK["makas"]
    assert "S3_BETOPAN" in adlar and not any(a.startswith("S3_OMEGA") for a in adlar)
    # elektrik simgelerinin kutuları (U, TV, Z) çizim içinde, sayfanın lejant katmanında değil
    kutu = [e for e in doc.modelspace() if e.dxf.layer == "S6_PAFTA" and e.dxftype() == "HATCH"]
    assert len(kutu) == 1                                                      # yalnız lejantın kutusu


def test_hatali_dxf_teslim_adiyla_kalmaz(tmp_path):
    """K23 gibi: denetim geçmezse dosya `.HATALI.dxf` adıyla kalır, teslim adıyla dosya yok."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = dxf_yaz.DxfPafta("X")
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.add_patch(plt.Rectangle((0, 0), 100, 50, color="#2c3e50")); ax.set_aspect("equal"); ax.autoscale_view()
    d.sayfa(fig, "deneme", dxf_yaz.roller(cizim.RENK))
    plt.close(fig)
    d.sayfalar[0]["katmanlar"]["S1_MAKAS"] += 1                               # yazılanla okunan tutmasın
    r = d.kaydet(tmp_path / "X.dxf")
    assert r["dosya"] is None and r["hatali"] == "X.HATALI.dxf" and r["hatalar"]
    assert not (tmp_path / "X.dxf").exists() and (tmp_path / "X.HATALI.dxf").exists()


def test_komut_varsayilan_dxfsiz():
    """`--dxf` yoksa komutun çıktıları aynen (test_kart_model.test_komut); bayrakla DXF de yazılır."""
    import inspect
    assert inspect.signature(KM.uret).parameters["dxf"].default is False
    assert inspect.signature(cizim.ciz).parameters["dxf_yolu"].default is None


def test_okunamayan_dxf_teslim_adiyla_kalmaz(tmp_path, monkeypatch):
    """Yeniden açma hata verirse dosya HATALI adıyla kalır."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = dxf_yaz.DxfPafta("Y")
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.add_patch(plt.Rectangle((0, 0), 100, 50, color="#2c3e50")); ax.set_aspect("equal"); ax.autoscale_view()
    d.sayfa(fig, "deneme", dxf_yaz.roller(cizim.RENK))
    plt.close(fig)
    (tmp_path / "Y.dxf").write_text("eski", encoding="utf-8")                  # önceki koşunun dosyası da kalmaz

    def bozuk(*_a, **_k):
        raise OSError("okunamadı")
    monkeypatch.setattr(ezdxf, "readfile", bozuk)
    r = d.kaydet(tmp_path / "Y.dxf")
    assert r["dosya"] is None and "yeniden açılamadı" in r["hatalar"][0]
    assert not (tmp_path / "Y.dxf").exists() and (tmp_path / "Y.HATALI.dxf").exists()


def test_dxf_hatasi_pdfi_kesmez(tmp_path, monkeypatch):
    """DXF'e çevirme bir sayfada hata verirse PDF yedi sayfayla tamamlanır; DXF teslim adıyla yazılmaz, neden `montaj_dxf`'te."""
    gercek = dxf_yaz.DxfPafta.sayfa

    def sahte(self, fig, ad, roller):
        if "BETOPAN" in ad:
            raise KeyError("deneme")
        return gercek(self, fig, ad, roller)
    monkeypatch.setattr(dxf_yaz.DxfPafta, "sayfa", sahte)
    say = KM.uret(KM._oku(IE), tmp_path, "P8501", dxf=True)
    assert len(pymupdf.open(tmp_path / "P8501_yerlesim_planlari.pdf")) == 7
    assert say["montaj_dxf"]["dosya"] is None and "KeyError" in say["montaj_dxf"]["hatalar"][0]
    assert not list(tmp_path.glob("*.dxf"))
