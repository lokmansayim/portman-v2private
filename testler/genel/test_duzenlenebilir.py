"""D-11 (Lokman, 13 Ekim 2026) · düzenlenebilir çıktılar: genel motorun DXF'i (plan + dört görünüş, katmanlı, cm; `motor/genel/dxf_genel.py`)
ve yükleme listesinin Excel'i (`motor/genel/excel_liste.py`; yalnız kabul paketinde, openpyxl yerel). İkisi de çıktıdır, kaynak değil.

- Yedi modelde DXF yeniden açılır ve denetlenir (audit hatası 0), R2018, $INSUNITS 5 (cm); DUVAR, ACIKLIK, OLCU, YAZI ve CATI katmanlarında
  varlık var; dört görünüş başlığı, mahal adları ve pencere etiketleri yazılı; plan duvar gövdesinin sınırı dış hatla aynı, genel ölçüler
  (DIMENSION) dış ölçüyle aynı; aynı tanım aynı içerik izini verir (`parmak_izi.dxf_ozet`).
- `uret` DXF'i yazar ama çizim setinin dosya listesi ve öteki çıktılar değişmez (Ç8801 altın: plan PNG, liste JSON, IFC izi); kural
  anahtarı yoksa DXF üretilmez (eski davranış).
- Excel: üç sayfa, her liste satırı bir satır, sayılar sayı hücresi, toplamlar JSON'la aynı; kabul paketi DXF ve Excel'i taşır,
  README "kabul eden" ve D-11 der."""
from __future__ import annotations
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "testler" / "referans"))
from motor.genel import dxf_genel, kural, yapi  # noqa: E402

SET = KOK / "kurallar" / "liste" / "setler" / "0.19.json"
MODELLER = ["C8201", "C8801", "C8801K", "C8801L", "KT01", "KT02", "KT03"]
KATMANLAR = {"DUVAR", "ACIKLIK", "OLCU", "YAZI", "CATI"}


@pytest.fixture(scope="module", autouse=True)
def kural_seti():
    eski = os.environ.get("PORTMAN_KURALLAR")
    os.environ["PORTMAN_KURALLAR"] = str(SET)
    try:
        yield
    finally:
        if eski is None:
            os.environ.pop("PORTMAN_KURALLAR", None)
        else:
            os.environ["PORTMAN_KURALLAR"] = eski


def tanim(kod: str) -> dict:
    return json.loads((KOK / "modeller" / f"{kod}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dxfler(tmp_path_factory):
    kok = tmp_path_factory.mktemp("dxf")
    return {m: (tanim(m), dxf_genel.ciz(tanim(m), kural.oku(), kok / f"{m}_cizim.dxf"), kok / f"{m}_cizim.dxf") for m in MODELLER}


@pytest.mark.parametrize("model", MODELLER)
def test_dxf_acilir_katmanli_cm(dxfler, model):
    import ezdxf
    from motor.genel.ciz_genel import dis_hat
    t, oz, yol = dxfler[model]
    assert oz["denetim_hatasi"] == 0 and set(oz["katmanlar"]) == KATMANLAR and all(n > 0 for n in oz["katmanlar"].values()), oz
    doc = ezdxf.readfile(yol)
    assert doc.dxfversion == "AC1032" and doc.header["$INSUNITS"] == 5                      # R2018, cm
    msp = doc.modelspace()
    yazilar = {e.dxf.text for e in msp.query("TEXT")}
    assert {"ÖN (GİRİŞ) GÖRÜNÜŞ", "ARKA GÖRÜNÜŞ", "SOL GÖRÜNÜŞ", "SAĞ GÖRÜNÜŞ"} <= yazilar
    y = yapi.kur(t)
    assert {b["ad"].upper() for b in y["bolgeler"].values() if b["sinif"] != "dis"} <= yazilar
    assert {a.get("etiket") or f"{a['en']}/{a['yuk']}" for a in y["acikliklar"] if a["tur"] == "pencere"} <= yazilar
    # plan: duvar gövdesinin dış sınırı dış hatla aynı (kaplama dahil; görünüşler planın altında, ayrı bölgede)
    hat = dis_hat(y)
    bx0, by0 = min(p[0] for h in hat for p in h), min(p[1] for h in hat for p in h)
    bx1, by1 = max(p[0] for h in hat for p in h), max(p[1] for h in hat for p in h)
    pts = [p for e in msp.query("LWPOLYLINE[layer=='DUVAR']") for p in e.get_points("xy") if p[1] > by0 - 30]
    assert abs(min(p[0] for p in pts) - bx0) < 0.02 and abs(max(p[0] for p in pts) - bx1) < 0.02
    assert abs(min(p[1] for p in pts) - by0) < 0.02 and abs(max(p[1] for p in pts) - by1) < 0.02
    olculer = [round(e.get_measurement(), 2) for e in msp.query("DIMENSION")]
    assert round(bx1 - bx0, 2) in olculer and round(by1 - by0, 2) in olculer and oz["olcu"] == len(olculer) >= 20


def test_dxf_ayni_tanim_ayni_icerik(dxfler, tmp_path):
    from parmak_izi import dxf_ozet
    for m in ("C8801", "KT03"):
        t, _, yol = dxfler[m]
        ikinci = dxf_genel.ciz(t, kural.oku(), tmp_path / f"{m}_ikinci.dxf")
        assert ikinci["denetim_hatasi"] == 0 and dxf_ozet(yol) == dxf_ozet(tmp_path / f"{m}_ikinci.dxf")
        assert hashlib.sha256(yol.read_bytes()).hexdigest() != "" and dxf_ozet(yol) != dxf_ozet(dxfler["C8201"][2])


def test_gorunuste_gizli_cizgi_atilir():
    """Ön görünüşte örtülen yüzey kenarları çizilmez: çizilen çatı çizgilerinin toplam boyu, bakışa dönük çatı yüzeylerinin çevrelerinin
    toplamından kısa (Ç8801: ön çatı düzlemi arkadakilerin kenarlarını örter; KT-01: baca ve müştemilat çatısı)."""
    from motor.genel import cati_genel, sahne
    from shapely.geometry import Polygon

    class Say:
        def __init__(self):
            self.boy = {}

        def geo(self, g, katman, dx=0.0, dy=0.0, **ek):
            self.boy[katman] = self.boy.get(katman, 0.0) + (0.0 if g.is_empty else g.length)

        def cizgi(self, *a, **k):
            pass

        def olcu(self, *a, **k):
            pass

        def yazi(self, *a, **k):
            pass

    for m in ("C8801", "KT01"):
        t = tanim(m)
        y = yapi.kur(t); c = cati_genel.cati_kur(t["cati"], kural.oku()); S = sahne.sahne_kur(y, c)
        C = Say()
        dxf_genel.gorunus_ciz(C, S, "on", t["kat_yuksekligi"], 0.0, 0.0)
        cevre = sum(Polygon(s["k2"]).length for s in sahne.izdusum(S, "on") if s["tur"] in ("cati", "alin"))
        assert 0 < C.boy["cati"] < cevre - 50, (m, C.boy, cevre)


def test_uret_dxf_yazar_oteki_ciktilar_ayni(tmp_path):
    """DXF `uret` çıktısına eklenir; çizim setinin dosya listesi (cizim_seti.json) ve Ç8801 altın değerleri (plan PNG, liste JSON, IFC izi)
    değişmez; manifest `duzenlenebilir_dxf`, pano Motor'unun `dxf` anahtarı boş kalır."""
    from motor.genel import iz, uret as U
    m = U.uret(KOK / "modeller" / "C8801.json", tmp_path, is_emri_no=None, revizyon=1, set_yolu=SET, perspektif=False, bayi=False)
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    seti = json.loads((KOK / "kurallar" / "cizim" / "cizim_seti.json").read_text(encoding="utf-8"))
    assert m["passed"] and m["duzenlenebilir_dxf"] == "C8801_cizim.dxf" and (tmp_path / "C8801_cizim.dxf").is_file() and "dxf" not in m
    assert v["ciktilar"]["beklenen"] == len(seti["ciktilar"]) and not any("DXF" in u for u in v["warnings"])
    altin = json.loads((KOK / "modeller" / "altin.json").read_text(encoding="utf-8"))["C8801"]
    assert hashlib.sha256((tmp_path / "C8801_plan.png").read_bytes()).hexdigest() == altin["plan_png_sha256"]
    assert hashlib.sha256((tmp_path / "C8801_yukleme.json").read_bytes()).hexdigest() == altin["yukleme_json_sha256"]
    assert iz.ifc_izi(tmp_path / "C8801.ifc") == altin["ifc_izi"]


def test_kural_anahtari_yoksa_dxf_uretilmez(tmp_path, monkeypatch):
    from motor.genel import uret as U
    monkeypatch.setattr(dxf_genel, "KURAL_DOSYASI", tmp_path / "yok.json")
    m = U.uret(KOK / "modeller" / "C8201.json", tmp_path / "c", is_emri_no=None, revizyon=1, set_yolu=SET, perspektif=False, bayi=False)
    assert m["passed"] and m["duzenlenebilir_dxf"] is None and not list((tmp_path / "c").glob("*.dxf"))


def test_denetimden_gecmeyen_dxf_teslim_adiyla_kalmaz(tmp_path, monkeypatch):
    """Kod incelemesi (13.10, CR19): yeniden açılıp denetlenen DXF'te hata varsa dosya `.HATALI.dxf` olur, manifest ve ekler onu taşımaz
    (önce uyarıya rağmen `duzenlenebilir_dxf` yazılıyor, kabul paketi "DXF var" diyordu). Öteki çıktılar ve `passed` etkilenmez."""
    from motor.genel import uret as U
    gercek = dxf_genel.ciz

    def hatali(*a, **k):
        oz = gercek(*a, **k)
        return {**oz, "denetim_hatasi": 1}
    monkeypatch.setattr(dxf_genel, "ciz", hatali)
    m = U.uret(KOK / "modeller" / "C8201.json", tmp_path, is_emri_no=None, revizyon=1, set_yolu=SET, perspektif=False, bayi=False)
    assert m["passed"] and m["duzenlenebilir_dxf"] is None
    assert not (tmp_path / "C8201_cizim.dxf").exists() and (tmp_path / "C8201_cizim.HATALI.dxf").is_file()
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    assert any("DXF" in u for u in v["warnings"])


@pytest.fixture(scope="module")
def liste(tmp_path_factory):
    from motor.genel import uret as U
    k = tmp_path_factory.mktemp("liste")
    U.uret(KOK / "modeller" / "KT02.json", k, is_emri_no=None, revizyon=1, set_yolu=SET, perspektif=False, bayi=False, yalniz_liste=True)
    return json.loads((k / "KT02_yukleme.json").read_text(encoding="utf-8"))


def test_excel_yukleme_listesi(liste, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from motor.genel import excel_liste
    yol = excel_liste.xlsx_yaz(liste, tmp_path / "KT02_yukleme.xlsx", kaynak="KT02_yukleme.json", set_adi="0.19.json")
    wb = openpyxl.load_workbook(yol)
    assert wb.sheetnames == ["YÜKLEME", "Ara değerler", "Açıklama"]
    ws = wb["YÜKLEME"]
    assert [c.value for c in ws[7]] == ["Sıra", "Kalem", "Boyut", "Adet", "Ölçü", "Birim", "Ağırlık (kg)", "Kural (formül)", "Dayanak", "Not"]
    satirlar = [r for r in ws.iter_rows(min_row=8, values_only=True) if r[1] and (r[0] is not None or str(r[1]).startswith("Toplam"))]
    assert len(satirlar) == len(liste["satirlar"])
    assert [r[1] for r in satirlar] == [(x.get("liste_adi") or x["kalem"]) + (f" ({x['renk']})" if x.get("renk") else "") for x in liste["satirlar"]]
    assert all(isinstance(r[3], int) for r, x in zip(satirlar, liste["satirlar"]) if isinstance(x["adet"], int))
    assert sum(r[6] or 0 for r in satirlar) == pytest.approx(sum(x["kg"] or 0 for x in liste["satirlar"]))
    assert "kaynak değil" in str(ws.cell(5, 1).value) and "D-11" in str(ws.cell(5, 1).value)
    varsayim = [i for i, x in enumerate(liste["satirlar"]) if x["durum"] == "varsayim"]
    if varsayim:                                                    # teyit bekleyen satır renkli
        r = next(c.row for c in ws["B"] if c.value == satirlar[varsayim[0]][1])
        assert ws.cell(r, 2).fill.fgColor.rgb.endswith("FCE4D6")


def test_kabul_paketi_dxf_ve_excel(tmp_path):
    pytest.importorskip("openpyxl")
    sys.path.insert(0, str(KOK / "araclar"))
    import kabul_paketi as KP
    assert KP.main([str(tmp_path), "--kodlar", "KT01", "--perspektifsiz", "--set", str(SET)]) == 0
    assert (tmp_path / "KT01" / "KT01_cizim.dxf").is_file() and (tmp_path / "KT01" / "KT01_yukleme.xlsx").is_file()
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Kabul eden: geliştirme döneminde Lokman (D-11" in readme and "kaynak değil" in readme and "mühendis kabul paketi" not in readme
    assert "mühendis planı" not in (tmp_path / "KT01" / "KISA_PARCALAR.md").read_text(encoding="utf-8")
