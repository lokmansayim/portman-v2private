"""D-34 · Lokman'ın TK-03 r02 notları (30 Ekim 2026 14:45, işaretli ön onay PDF'i) Motor kuralı olarak: görünüş ölçüsü mor çizgi ve
siyah yazı (PC-25), girintili gövdede kapalı gövdenin her dış parçası mor ölçüyle (PC-26), cumbanın görünen saçak ucunda topuk (PC-27),
sınırın yalnız bir parçası duvarsız (merdiven ağzı, PC-28). Her kural bütün prefabrik çizimlerde aynı çalışır; dikdörtgen gövdede PC-26 ve
PC-27 bir şey çizmez (TK-01, TK-02, P6001 çizgileri aynen; renk değişikliği hedef izlerinde)."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cephe_gorunus as CG, dxf_out, geometry as G  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
TK03 = VERI / "TK03.json"
P6001 = KOK / "is_emri" / "P6001_2plus1_6x6.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tk03(tmp_path_factory):
    import ezdxf
    d = tmp_path_factory.mktemp("tk03")
    m = dxf_out.uret(_oku(TK03), d)
    assert m["validation_passed"] and m["pdf"]
    return ezdxf.readfile(d / m["dxf"]), d / m["pdf"]


def _olculer(doc, katman):
    return [e for e in doc.modelspace().query("DIMENSION") if e.dxf.layer == katman]


def test_gorunus_olculeri_mor_yazi_siyah(tk03):
    """PC-25: görünüşlerin ölçüsü (ON_OLCU) ve dış parça ölçüsü mor (ACI 193; ölçü ve uzatma çizgisi de), yazısı genel ölçünün siyahı;
    PDF'te mor çizgi var."""
    import pymupdf
    doc, pdf = tk03
    assert dxf_out.OLCU_MOR == 193 and dxf_out.OLCU_YAZI_RENGI == 7
    assert doc.layers.get("ON_OLCU").dxf.color == 193 and doc.layers.get("DIS_PARCA_OLCU").dxf.color == 193
    for katman in dxf_out.MOR_OLCU_KATMANLARI:
        olcu = _olculer(doc, katman)
        assert olcu, katman
        for e in olcu:
            o = e.override()
            assert (o.get("dimclrd"), o.get("dimclre"), o.get("dimclrt")) == (193, 193, 7), (katman, e.dxf.handle)
    assert all(e.override().get("dimclrt") in (None, 0, 256) for e in _olculer(doc, "OLCULER"))   # genel ölçü katmanın renginde (siyah)
    mor = (124 / 255, 82 / 255, 165 / 255)
    with pymupdf.open(pdf) as d:
        renkler = {tuple(round(v, 2) for v in (r.get("color") or ())) for r in d[0].get_drawings()}
    assert tuple(round(v, 2) for v in mor) in renkler


def test_dis_parca_olculeri_paftanin_zincirleri(tk03):
    """PC-26: girintili gövdede kapalı gövdenin on dış parçası ölçülü; değerler paftanın dört ölçü zincirindeki on değer (balkonun eni ve
    derinliği dahil). Her ölçü gövdenin dışında; açık mahalin (balkon) aks ölçüsü bu planda yok."""
    from shapely.geometry import Point
    doc, _ = tk03
    pafta = _oku(VERI / "TK03_pafta.json")
    beklenen = sorted(v for z in pafta["olcu_zincirleri"].values() for v in z)
    olcu = _olculer(doc, "DIS_PARCA_OLCU")
    assert len(olcu) == 2 * len(beklenen)                                  # akslı plan ve net alan planı
    degerler = sorted(round(e.get_measurement(), 2) for e in olcu)
    assert all(abs(a - b) < 0.05 for a, b in zip(degerler[::2], beklenen)) and degerler[::2] == degerler[1::2], (degerler, beklenen)
    plan = G.kur(_oku(TK03))
    govde = G.kapali_govde_cokgeni(plan)
    ana = [e for e in olcu if e.dxf.defpoint[0] < plan.W + 200 and abs(e.dxf.defpoint[1]) < plan.H + 200]
    assert all(not govde.contains(Point(e.dxf.defpoint[0], e.dxf.defpoint[1])) for e in ana)
    assert not any(abs(e.get_measurement() - 188.25) < 0.01 for e in doc.modelspace().query("DIMENSION"))   # balkonun aks ölçüsü


def test_girintisiz_planda_dis_parca_olcusu_yok(tmp_path):
    """PC-26 yalnız girintili gövdede: dikdörtgen gövdenin DXF'inde katman da açılmaz (dış ölçü iki toplam ölçü)."""
    import ezdxf
    m = dxf_out.uret(_oku(P6001), tmp_path)
    doc = ezdxf.readfile(tmp_path / m["dxf"])
    assert "DIS_PARCA_OLCU" not in doc.layers and not _olculer(doc, "DIS_PARCA_OLCU")


def test_cumba_sacak_ucunda_topuk(tk03):
    """PC-27: cumbanın (ve ana çatının) görünüşte görünen saçak ucunda topuk, taşan verandadaki gibi. TK-03: soldan bakışta sol cumbanın ön
    saçak ucu, sağdan bakışta sağ cumbanın arka saçak ucu (Lokman'ın işaretlediği iki yer), önden ve arkadan ana çatının saçak ucu; öteki
    uçlar kalkanın ya da yakın saçağın arkasında. Dikdörtgen gövdede iki uçtakinden başka topuk yok."""
    ie = _oku(TK03)
    plan = G.kur(copy.deepcopy(ie))
    topuk = {t: CG.cati_cizgileri(plan, ie, t)["topuklar"] for t in CG.TARAFLAR}
    assert topuk == {"on": [513.5], "arka": [421.1], "sol": [671.3], "sag": [733.3]}
    doc, _ = tk03
    assert len([e for e in doc.modelspace().query("LINE") if e.dxf.layer == "ON_TOPUK"]) == 2 * 4 + 4
    for yol in (P6001, VERI / "TK01_r07.json", VERI / "TK02.json"):
        ie = _oku(yol)
        p = G.kur(copy.deepcopy(ie))
        assert all(not CG.cati_cizgileri(p, ie, t)["topuklar"] for t in CG.TARAFLAR), yol.name


def test_merdiven_agzi_duvarsiz():
    """PC-28: merdiven ağzı (salona bakan yüzde 548,5–650,4) duvarsız, pano yok; duvar 650,4'ten köşeye; ağız açık sınır çizgisi."""
    plan = G.kur(_oku(TK03))
    y = plan.H - 359.75
    duvar = [d for d in plan.duvarlar if d.yon == "x" and abs(d.c - y) < 1e-6]
    assert [(d.p0, d.p1) for d in duvar] == [(650.4, 828.95)]
    assert not [p for d in plan.duvarlar for p in d.panolar if p.acilim and p.acilim.tur == "gecis"]
    agiz = [c for c in plan.acik_sinir_cizgileri if abs(c[1] - c[3]) < 1e-6 and abs(c[1] - (y - 3.0)) < 1e-6]
    assert min(min(c[0], c[2]) for c in agiz) == 548.5 and max(max(c[0], c[2]) for c in agiz) == 650.4
    assert abs(plan.mahaller["MERDİVEN KOVASI"].alan_m2 - 4.39) < 0.01                  # şerit salona (`serit`)


def test_acik_sinir_parca_hatalari():
    """`parca_cm` bir hat ve aralık ister; uçlar aks üstünde (K21), aralığın tamamı iki mahalin arasındaki iç duvarda."""
    ie = _oku(TK03)

    def parca(p):
        x = copy.deepcopy(ie); x["acik_sinirlar"][-1]["parca_cm"] = p
        return x
    with pytest.raises(G.IsEmriHatasi, match="aks üstünde değil"):
        G.kur(parca({"y": 359.75, "x": [548.5, 640.0]}))
    with pytest.raises(G.IsEmriHatasi, match="iç duvarda değil"):
        G.kur(parca({"y": 359.75, "x": [548.5, 1009]}))
    with pytest.raises(G.IsEmriHatasi, match="bir hat ve bir aralık"):
        G.kur(parca({"y": [359.75, 523.85], "x": [548.5, 650.4]}))
