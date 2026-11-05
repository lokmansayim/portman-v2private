"""M-12 · AP-26 ön onay çiziminin hedef örneği (D-28 madde 2, D-52; mühür M-12).

Lokman, 5 Kasım 2026 10:17 ("%10 eğimle ve paftadaki gibi 120 derinlikle devam edeyim mi?" sorusuna): "evet onaylıyorum mühürle bu çizim
şeklini". Onaylanan çizim AP-26'nın montaj paftasından İş Emri'nin (`testler/kor/projeler/AP26/is_emri.json`) ön onay çizimidir: paftanın
pencere bölmeleri (120/120 iki kanat, 280/210 sabit + sürgülü + sürgülü + sabit, 200/210 iki bölmeli sürgülü, 50/50 vasistas), arka
terastan yatak odasına komple cam PVC kapı, ön ve arka teras 120 derin, üstleri teras paneli (8 cm, duvarda saçak altının 10 cm altında,
dışarı %10 iner, duvardan 140; kolon 210; yan kiriş yok, D-54: Lokman, 5 Kasım 2026 10:48, "Kaldır, gerçek liste gibi"), karkaslı
kaplama duvar panoları (D-46). İzi `veri/AP26_beklenen.json`: A4 ön onay PDF'inin ve
DXF'in içerik izi, doğrulama özeti, pano BOM'u, dört görünüşün çizgileri (üretim saati yok). Yükleme listesi bu ize girmez: liste aşaması
çizim onayından sonra (sıra kuralı, 29 Ekim 2026).

Bilerek değişirse önce Lokman'ın sözüyle mühür açılır (`python3 .claude/hooks/muhur_koruma.py ac M-12 …`), sonra
`python testler/motor/test_m12_ap26.py --yaz` ve gerekçeli kararla kapanır (D-28 madde 3, D-42).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import ezdxf

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out  # noqa: E402

GIRDI = KOK / "testler" / "kor" / "projeler" / "AP26" / "is_emri.json"
BEKLENEN = KOK / "testler" / "motor" / "veri" / "AP26_beklenen.json"
ONAY = ("AP-26 ön onay çizimi (İE-30, D-52; mühür M-12). Lokman, 4 Kasım 2026 20:42: \"pencereler çizimi tam doğru değil ayrıca teras ayrı "
        "bir teknikler yapılıyor çatı saçağının 10 cm altında çatı paneli olarak kullandığımız bir 8 cm genişliğinde C den oluşan panel "
        "yapıyoruz üzerine yine Trapez sac araya damlalık atıyoruz yani çatı gibi şekilli değil AP26 montaj paftasını iyice incele\"; 21:14 "
        "kartı \"Paftadan, ev ev\"; 5 Kasım 2026 00:36: \"teraslara biraz eğim vereceksin\"; 10:17 (\"%10 eğimle ve paftadaki gibi 120 "
        "derinlikle devam edeyim mi?\" sorusuna): \"evet onaylıyorum mühürle bu çizim şeklini\". 10:48 kartı (\"Teras yan kirişini listeden "
        "ve yan görünüşten kaldırayım mı?\"): \"Kaldır, gerçek liste gibi\" (D-54; M-12 bununla açıldı, iz yalnız yan kirişin kalkmasıyla "
        "yeniden donduruldu).")
GORUNUS_KATMANLARI = ("ON_GORUNUS", "ON_DERZ", "ON_CATI", "ON_TOPUK")


def _gorunusler(dxf: Path) -> list:
    """Dört görünüşün çizgileri (duvar, derz, çatı ve topuk katmanı; ölçü, yazı ve doğrama bloğu hariç): katman ve noktalar, sıralı."""
    out = []
    for e in ezdxf.readfile(dxf).modelspace():
        if e.dxf.layer in GORUNUS_KATMANLARI and e.dxftype() in ("LINE", "LWPOLYLINE"):
            q = e.get_points("xy") if e.dxftype() == "LWPOLYLINE" else (e.dxf.start, e.dxf.end)
            out.append([e.dxf.layer, bool(e.dxftype() == "LWPOLYLINE" and e.closed)] + [[round(x[0], 3), round(x[1], 3)] for x in q])
    return sorted(out)


def _iz(cikti: Path) -> dict:
    """Ön onay çiziminin izi (BK-18'in hedef örnek izi gibi, yükleme listesi hariç): doğrulama özeti, pano BOM'u, görünüş çizgileri, A4
    PDF'inin ve DXF'in içerik izi (`testler/referans/parmak_izi.py`; üretim saati dışarıda)."""
    sys.path.insert(0, str(KOK / "testler" / "referans"))
    from parmak_izi import dxf_ozet, pdf_ozet
    v = json.loads((cikti / "validation.json").read_text(encoding="utf-8"))
    b = json.loads((cikti / "bom.json").read_text(encoding="utf-8"))
    m = json.loads((cikti / "manifest.json").read_text(encoding="utf-8"))
    return {"dogrulama": {k: v[k] for k in ("passed", "errors", "outer_cm", "panel_grid", "panel_count", "corner_count", "windows", "doors",
                                            "h_connectors", "footprint_diff_cm2", "warnings")}
            | {"rooms_m2": {k: round(x, 4) for k, x in v["rooms_m2"].items()},
               "openings": [{"kind": o["kind"], "name": o["name"], "gap": [round(x, 3) for x in o["gap"]]} for o in v["openings"]]},
            "bom": [{k: r[k] for k in ("kod", "malzeme", "olcu_mm", "adet", "birim")} for r in b["kalemler"]],
            "gorunusler": _gorunusler(cikti / m["dxf"]),
            "pdf_izi": pdf_ozet(cikti / m["pdf"]), "dxf_izi": dxf_ozet(cikti / m["dxf"])}


def _uret(cikti: Path) -> dict:
    ie = json.loads(GIRDI.read_text(encoding="utf-8"))
    return dxf_out.uret(json.loads(json.dumps(ie)), cikti, pdf_hatada=False)


def test_m12_hedef_ornek_izi(tmp_path):
    """AP-26'nın ön onay çizimi Lokman'ın 5 Kasım 2026 10:17'de onaylayıp mühürlediği çizimle aynı."""
    m = _uret(tmp_path)
    assert m["validation_passed"] is True and m["pdf"] and m["warnings"] == []
    b = json.loads(BEKLENEN.read_text(encoding="utf-8"))
    assert b["girdi"] == GIRDI.relative_to(KOK).as_posix() and b["onay"] == ONAY
    assert _iz(tmp_path) == b["iz"]


def test_m12_teraslar_paftadaki_gibi():
    """Onaylanan teraslar: 120 derin, teras paneli duvardan 140, %10 (İş Emri'nin mühürlü yeri)."""
    ie = json.loads(GIRDI.read_text(encoding="utf-8"))
    assert [(v["ad"], v["cephe"], v["derinlik_cm"], v["cati"]) for v in ie["verandalar"]] == [
        ("ÖN TERAS", "on", 120, {"tip": "teras_paneli", "cikma_cm": 140, "egim_yuzde": 10}),
        ("ARKA TERAS", "arka", 120, {"tip": "teras_paneli", "cikma_cm": 140, "egim_yuzde": 10})]


if __name__ == "__main__" and "--yaz" in sys.argv:
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        _uret(Path(t))
        BEKLENEN.write_text(json.dumps({"aciklama": "M-12 · AP-26 ön onay çiziminin hedef örneği (D-28 madde 2, D-52): A4 PDF ve DXF içerik izi, "
                                        "doğrulama özeti, pano BOM'u ve görünüş çizgileri (yükleme listesi hariç).",
                                        "girdi": GIRDI.relative_to(KOK).as_posix(), "onay": ONAY, "iz": _iz(Path(t))},
                                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı:", BEKLENEN)
