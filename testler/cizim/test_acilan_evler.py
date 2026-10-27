"""İE-17 · Gerileme freni (A6): açılan her ev her koşuda yeniden çizilir; biri bozulursa test düşer.

Açılan evler (`testler/cizim/evler/`, montaj paftasından): Motor'un doğrulaması geçer; Örnek Şablon paftası (`sablon_kopru.pafta`) iki
sayfa, teslim adıyla, yazı çakışmasız; canlı DXF (`dxf_out.uret`) doğrulamadan geçer ve dört görünüşü taşır. Ölçü zincirleri, tepe kotu,
oturum alanı ve çatının mahya kotu sabit: mahya kotu paftanın kesitinden (duvar üstünden, topuk dahil: AP-13 149,4, AP-16 170,86;
AP-01'de kesit yok: 10 + 530 × 0,33, saçak 30 paftanın çatı alanından). Bu bir çizim kilididir; paftaya uygunluk yan yana kıyasla (İE-17 › Kanıt).
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, sablon_kopru as K, sunum  # noqa: E402
from motor.genel import cati_genel  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"

# ev: (çatı şekli, eğim yazısı, oturum m², tepe cm (kaplama dahil), mahya − duvar üstü (paftanın kesiti), ölçü zincirleri)
BEKLENEN = {
    "AP13": ("Beşik + Cumba", "%32,88", 60.12, 413.4, 149.4,
             {"arka": [387, 376], "on": [392, 371], "sol": [276, 188, 324], "sag": [271, 517]}),
    "AP16": ("Beşik + Cumba", "%32,88", 70.08, 434.9, 170.86,
             {"arka": [387, 376], "on": [392, 120, 251], "sol": [470, 188, 261], "sag": [214, 256, 188, 261]}),
    "AP01": ("Kırma", "%33", 140.0, 448.9, 184.9,
             {"arka": [449, 377, 126, 125, 323], "on": [642, 309, 449], "sol": [430, 251, 319], "sag": [300, 319, 381]}),
}


def _ie(ad: str) -> dict:
    return json.loads((EVLER / f"{ad}.json").read_text(encoding="utf-8"))


def test_evler_listesi():
    assert sorted(p.stem for p in EVLER.glob("*.json")) == sorted(BEKLENEN)


@pytest.mark.parametrize("ad", sorted(BEKLENEN))
def test_motor_dogrulamasi_ve_uyarisiz(ad):
    ie = _ie(ad)
    assert sunum.motor_dogrulamasi(copy.deepcopy(ie)) == {"passed": True, "errors": []}
    # kişi ve bayi adı yok: talep yer tutucuyla (paftanın anteti İş Emri'ne girmez)
    assert ie["talep"]["bayi"] == {"kod": ad, "ad": f"Bayi {ad[:2]}-{ad[2:]}"} and ie["talep"]["musteri_adi"] == f"{ad[:2]}-{ad[2:]}"


@pytest.mark.parametrize("ad", sorted(BEKLENEN))
def test_sablon_paftasi(ad, tmp_path):
    import pymupdf
    from matplotlib.backends.backend_pdf import PdfPages
    from motor.genel import yazi_cakisma as YC
    sekil, egim, m2, tepe, mahya, zincir = BEKLENEN[ad]
    ie = _ie(ad)
    r = []
    asil = PdfPages.savefig

    def kaydet(self, figure=None, **k):
        r.append(YC.denetle(figure, f"sayfa_{len(r) + 1}"))
        return asil(self, figure, **k)

    PdfPages.savefig = kaydet
    try:
        o = K.pafta(copy.deepcopy(ie), tmp_path, bilgi={"tarih": "27.10.2026"})
    finally:
        PdfPages.savefig = asil
    assert o["teslim"] is True and o["dogrulama"]["passed"] is True
    assert o["ozellikler"]["Çatı Şekli"] == sekil and o["ozellikler"]["Çatı Eğimi"] == egim
    assert o["oturum_m2"] == pytest.approx(m2) and o["tepe_cm"] == pytest.approx(tepe, abs=0.05)
    assert o["zincirler_cm"] == zincir
    assert [n for n in o["kontrol_notlari"] if n.get("kaynak") != "motor"] == []
    son = r[-2:]
    for k in ("cakisan", "cizgi_kapatan", "sayfa_disi", "yay_kapatan"):
        assert [x[k] for x in son] == [[], []], k
    with pymupdf.open(tmp_path / f"{ad}_pafta.pdf") as d:
        assert d.page_count == 2
        s1 = " ".join(w[4] for w in d[0].get_text("words")); s2 = " ".join(w[4] for w in d[1].get_text("words"))
    for s in ("ÖN GÖRÜNÜŞ", "SOL YAN GÖRÜNÜŞ"):
        assert s in s1, s
    for s in ("ÇATI PLANI", "ARKA GÖRÜNÜŞ", "SOL GÖRÜNÜŞ", "SAĞ GÖRÜNÜŞ"):
        assert s in s2, s
    # mahya kotu paftanın kesitiyle (duvar üstünden; AP-13 ve AP-16'nın cumbası 5 cm geniş, ana mahya aynı)
    t = json.loads((tmp_path / f"{ad}_yapi_tanimi.json").read_text(encoding="utf-8"))
    ck = cati_genel.cati_kur(t["cati"])
    assert max(max(k["kot"]) for k in ck["kenarlar"] if k["tur"] == "mahya") - 250 == pytest.approx(mahya, abs=0.05)


@pytest.mark.parametrize("ad", sorted(BEKLENEN))
def test_canli_dxf_dort_gorunus(ad, tmp_path):
    import ezdxf
    m = dxf_out.uret(copy.deepcopy(_ie(ad)), tmp_path)
    assert m["validation_passed"] is True and m["pdf"]
    doc = ezdxf.readfile(tmp_path / m["dxf"])
    yazi = " ".join(e.dxf.text for e in doc.modelspace().query("TEXT"))
    for s in ("ÖN (GİRİŞ) GÖRÜNÜŞ", "ARKA GÖRÜNÜŞ", "SOL GÖRÜNÜŞ", "SAĞ GÖRÜNÜŞ", f"Çatı: {BEKLENEN[ad][0]} | eğim {BEKLENEN[ad][1]}"):
        assert s in yazi, s
    for s in ("ÖN GÖRÜNÜŞ - ÇALIŞMA", "ÇATI PROFİLİ"):                       # beşiğin ön görünüşü ve profili çizilmez
        assert s not in yazi, s
    # dört görünüş yan yana, birbirine binmeden (adım görünüşün kendi eninden; yan görünüşün eni evin derinliği): görünüş katmanlarının
    # varlıkları x'te dört ayrık küme, sırası ön, arka, sol, sağ; aralar en az 200
    from ezdxf import bbox
    ara = sorted(((b.extmin.x, b.extmax.x, e) for e in doc.modelspace()
                 if e.dxf.layer.startswith("ON_") and not (e.dxftype() == "TEXT" and e.dxf.text.startswith("Çatı:"))
                 for b in [bbox.extents([e])] if b.has_data), key=lambda t: t[:2])
    kume = []
    for a, b, e in ara:
        if kume and a <= kume[-1][1] + 200:
            kume[-1][1] = max(kume[-1][1], b); kume[-1][2].append(e)
        else:
            kume.append([a, b, [e]])
    assert [[x.dxf.text for x in k[2] if x.dxftype() == "TEXT" and "GÖRÜNÜŞ" in x.dxf.text] for k in kume] == \
        [["ÖN (GİRİŞ) GÖRÜNÜŞ"], ["ARKA GÖRÜNÜŞ"], ["SOL GÖRÜNÜŞ"], ["SAĞ GÖRÜNÜŞ"]]
