"""Disk arşivinin türevleri (İE-43 PR-2): DXF akış özeti ve belge türevleri (PDF, Excel, görsel) geçici arşivde.

DWG çevrimi (LibreDWG wasm, node) CI'da koşmaz; onun kanıtı Mac'teki manifesttir. Burada çevrimden sonraki Python
adımları denenir: büyük DXF'in tek geçişte sıkıştırılıp özetlenmesi, belge türevleri, manifestte ad olmaması,
iki koşuda bitmeyen dosyanın "hata" yazılıp sıranın geçmesi.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "araclar" / "hdd_turev"))
ezdxf = pytest.importorskip("ezdxf")
import turev  # noqa: E402
import turev_belge  # noqa: E402

PROJE = "Zeynep Çağlar 74 m2"


def test_dxf_akis_ozet_ve_aynen_sikistirma(tmp_path):
    d = ezdxf.new("R2018")
    d.header["$INSUNITS"] = 5
    d.layers.add("DUVAR", color=2)
    d.layers.add("ÇATI", color=3).off()
    b = d.blocks.new("100'LÜK PANO")
    b.add_line((0, 0), (1, 1))
    b.add_attdef("NO", (0, 0))
    m = d.modelspace()
    for i in range(3):
        r = m.add_blockref("100'LÜK PANO", (i * 125.5, 10), dxfattribs={"rotation": 90 if i == 2 else 0, "layer": "PANO"})
        r.add_auto_attribs({"NO": str(i)})
    for i in range(5):
        m.add_line((i, 0), (i, 1), dxfattribs={"layer": "DUVAR"})
    m.add_text("Salon 12 m²", height=20, dxfattribs={"layer": "YAZI"}).set_placement((50, 60))
    m.add_mtext("Mutfak\\P" + "x" * 300, dxfattribs={"layer": "YAZI"}).set_location((5, 6))
    kaynak, gz = tmp_path / "a.dxf", tmp_path / "a.dxf.gz"
    d.saveas(kaynak)
    o = turev.dxf_akis(str(kaynak), str(gz))
    assert gzip.decompress(gz.read_bytes()) == kaynak.read_bytes()
    assert o["dxf"]["surum"] == "AC1032" and o["dxf"]["birim"] == 5
    assert o["oge_sayilari"] == {"ATTRIB": 3, "INSERT": 3, "LINE": 5, "MTEXT": 1, "SEQEND": 3, "TEXT": 1}
    assert o["bloklar"] == [{"ad": "100'LÜK PANO", "adet": 3}]
    assert [(e["x"], e["y"], e["aci"], e["katman"]) for e in o["eklemeler"]] == [
        (0.0, 10.0, 0.0, "PANO"), (125.5, 10.0, 0.0, "PANO"), (251.0, 10.0, 90.0, "PANO")]
    salon, mutfak = o["yazilar"]
    assert (salon["t"], salon["x"], salon["y"], salon["h"]) == ("Salon 12 m²", 50.0, 60.0, 20.0)
    assert mutfak["t"].startswith("Mutfak\\P") and len(mutfak["t"]) == 308   # 250'lik parçalar birleşti
    katman = {k["ad"]: k for k in o["katmanlar"]}
    assert katman["DUVAR"]["renk"] == 2 and not katman["DUVAR"]["eksi_yazili"]
    assert katman["ÇATI"]["renk"] == 3 and katman["ÇATI"]["eksi_yazili"]
    assert o["kesik"] == {}


def _arsiv(tmp_path: Path) -> Path:
    import openpyxl
    import pymupdf
    from PIL import Image

    kok = tmp_path / "Portman_HDD_Projeler"
    klasor = kok / PROJE
    klasor.mkdir(parents=True)
    doc = pymupdf.open()
    sayfa = doc.new_page(width=595, height=842)
    sayfa.insert_text((72, 72), "Zemin kat plani 74 m2")
    sayfa.draw_line((100, 200), (400, 200))
    sayfa.draw_rect(pymupdf.Rect(100, 300, 300, 400))
    doc.save(klasor / "Zeynep Çağlar plan.pdf")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Liste"
    ws["A1"], ws["B1"], ws["B2"], ws["B3"] = "Malzeme", "Adet", 4, "=B2*2"
    ws.merge_cells("C1:D1")
    wb.save(klasor / "Yükleme Listesi.xlsx")
    Image.new("RGB", (1200, 800), (200, 100, 50)).save(klasor / "foto.jpg")
    (klasor / "eski.xls").write_bytes(b"\xd0\xcf\x11\xe0")
    dosyalar = sorted(p.name for p in klasor.iterdir())
    (kok / "_portman_analiz").mkdir()
    with open(kok / "_portman_analiz" / "kod_esleme.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["kod", "sira", "proje_klasoru", "dosya", "sha256"])
        for i, ad in enumerate(dosyalar, 1):
            w.writerow(["HD-001", i, PROJE, ad, hashlib.sha256((klasor / ad).read_bytes()).hexdigest()])
    return kok


def _manifest(kok: Path, tur: str) -> list[dict]:
    yol = kok / "_portman_analiz" / "turev" / f"manifest_{tur}.jsonl"
    return [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines()]


def test_belge_turevleri_ve_manifestte_ad_yok(tmp_path):
    kok = _arsiv(tmp_path)
    hedef = kok / "_portman_analiz" / "turev"
    for tur in ("pdf", "excel", "gorsel"):
        assert turev_belge.main([tur, str(kok)]) == 0
        assert turev_belge.main([tur, str(kok)]) == 0           # ikinci koşu bir şey yapmaz
    pdf, = _manifest(kok, "pdf")
    assert pdf["durum"] == "tamam" and pdf["sayfa"] == 1 and pdf["taranmis_olabilir"] is False
    oz = json.loads(gzip.decompress((hedef / pdf["ciktilar"]["json_gz"]["yol"]).read_bytes()))
    s = oz["sayfalar"][0]
    assert "Zemin kat plani" in s["metin"] and s["cizgiler"] and s["dikdortgenler"]
    assert (hedef / pdf["ciktilar"]["png_s1"]["yol"]).exists()
    excel = {d["sira"]: d for d in _manifest(kok, "excel")}
    xlsx, xls = excel[1], excel[3]
    assert xls["durum"] == "hata" and xlsx["durum"] == "tamam"
    oz = json.loads(gzip.decompress((hedef / xlsx["ciktilar"]["json_gz"]["yol"]).read_bytes()))
    hucre = {h[0]: h[1:] for h in oz["sayfalar"][0]["hucreler"]}
    assert hucre["B2"] == [4] and hucre["B3"][1] == "=B2*2" and oz["sayfalar"][0]["birlesik"] == ["C1:D1"]
    foto, = _manifest(kok, "gorsel")
    assert foto["durum"] == "tamam" and foto["konum_var"] is False
    from PIL import Image
    with Image.open(hedef / foto["ciktilar"]["jpg"]["yol"]) as im:
        assert max(im.size) == 640
    for tur in ("pdf", "excel", "gorsel"):
        metin = (hedef / f"manifest_{tur}.jsonl").read_text(encoding="utf-8")
        for parca in ("Zeynep", "Çağlar", "Yükleme", "foto", PROJE):
            assert parca not in metin


def test_belge_iki_kosuda_bitmeyen_hata_olur(tmp_path):
    kok = _arsiv(tmp_path)
    hedef = kok / "_portman_analiz" / "turev"
    hedef.mkdir(parents=True)
    (hedef / "deneme_pdf.json").write_text(json.dumps({"HD-001_2": 2}), encoding="utf-8")
    assert turev_belge.main(["pdf", str(kok)]) == 0
    pdf, = _manifest(kok, "pdf")
    assert pdf["durum"] == "hata" and "iki koşuda" in pdf["hata"]
    assert json.loads((hedef / "deneme_pdf.json").read_text(encoding="utf-8")) == {}


def test_manifest_en_iyi_durum_ve_yeniden(tmp_path):
    # manifest yalnız eklenir: yeniden işlenen dosyada iyi durum geçerli; --yeniden hata,kismi yalnız onları açar
    satirlar = {"manifest_p0.jsonl": [("HD-001", 1, "hata"), ("HD-001", 2, "kismi"), ("HD-002", 1, "hata")],
                "manifest.jsonl": [("HD-001", 1, "tamam"), ("HD-001", 2, "hata")]}
    for ad, L in satirlar.items():
        (tmp_path / ad).write_text("".join(json.dumps({"kod": k, "sira": s, "tur": "dwg", "durum": d}) + "\n"
                                           for k, s, d in L), encoding="utf-8")
    assert turev.manifest_durumlari(str(tmp_path)) == {("HD-001", "1", "dwg"): "tamam", ("HD-001", "2", "dwg"): "kismi",
                                                      ("HD-002", "1", "dwg"): "hata"}
    assert len(turev.oku_manifest(str(tmp_path))) == 3
    assert turev.oku_manifest(str(tmp_path), ("hata", "kismi")) == {("HD-001", "1", "dwg")}


def test_plan_adaylari_obekleme_ve_imza():
    import planlar

    def ev(x0, y0, n=6, m=8):
        L = []
        for i in range(n):
            L += [{"blok": "100 LIK DOLU PANO 125 LİK", "x": x0 + i * 125.5, "y": y0},
                  {"blok": "100 LIK DOLU PANO 125 LİK", "x": x0 + i * 125.5, "y": y0 + m * 125.5}]
        for j in range(m):
            L += [{"blok": "100'LÜK 125'LİK (120x100) PENCERELİ PANO", "x": x0, "y": y0 + j * 125.5},
                  {"blok": "60'LIK 125'LİK KAPILI PANO(80'LİK)", "x": x0 + n * 125.5, "y": y0 + j * 125.5}]
        return L
    kagit = [{"blok": "X PANO", "x": 99999 + i, "y": 0, "kagit": True} for i in range(20)]
    A = planlar.adaylar(ev(0, 0) + ev(5000, 0) + ev(0, 5000, 4, 5) + kagit, 400, 12)
    assert [a["pano"] for a in A] == [28, 28, 18]                    # kağıt alanı sayılmaz
    assert A[0]["imza"] == A[1]["imza"] != A[2]["imza"]               # kopya aynı imza
    assert A[0]["kutu_cm"] == [753.0, 1004.0]
    assert A[0]["turler"] == {"100_dolu": 12, "100_pencere": 8, "60_kapi": 8}
    assert planlar.adaylar(ev(0, 0), 100, 12) == []                   # 125,5 aralık 100 cm eşikte bağlanmaz


def test_ozet_proje_sayilari(tmp_path):
    import ozet

    hedef = tmp_path / "_portman_analiz" / "turev"
    (hedef / "excel" / "HD-002").mkdir(parents=True)
    liste = {"sayfalar": [{"hucreler": [["A1", "Yükleme listesi"], ["B2", 4]]}]}
    (hedef / "excel" / "HD-002" / "1.json.gz").write_bytes(gzip.compress(json.dumps(liste).encode()))
    satirlar = [{"kod": "HD-001", "sira": 1, "tur": "dwg", "durum": "hata"},
                {"kod": "HD-001", "sira": 1, "tur": "dwg", "durum": "tamam", "pano_eklemesi": 40},
                {"kod": "HD-002", "sira": 1, "tur": "excel", "durum": "tamam",
                 "ciktilar": {"json_gz": {"yol": "excel/HD-002/1.json.gz"}}},
                {"kod": "HD-002", "sira": 2, "tur": "gorsel", "durum": "tamam", "konum_var": True}]
    (hedef / "manifest_p0.jsonl").write_text("".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")
    o = ozet.ozet(str(tmp_path))
    assert o["projeler"]["HD-001"] == {"dwg_tamam": 1, "dwg_panolu": 1, "pano_eklemesi": 40}
    assert o["projeler"]["HD-002"]["excel_liste"] == 1 and o["projeler"]["HD-002"]["gorsel_konumlu"] == 1
    assert o["toplam"]["proje_dwg_panolu"] == 1 and o["toplam"]["proje_excel_liste"] == 1
