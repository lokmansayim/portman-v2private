"""İE-17 · Gerileme freni (A6): açılan her ev her koşuda yeniden çizilir; biri bozulursa test düşer.

Açılan evler (`testler/cizim/evler/`, montaj paftasından): Motor'un doğrulaması geçer; canlı ön onay PDF'i (`dxf_out.uret`) doğrulamadan
geçer, PDF çıkar; ön görünüşün yanında arka, sol ve sağ görünüş aynı biçimle, birbirine binmeden, sağda ana çatının profili ve çatının
alt yazısı; özellik tablosunun çatı satırı paftanın yazımıyla. Mahya kotu paftanın kesitinden (duvar üstünden, topuk dahil: AP-13 149,4,
AP-16 170,86; AP-01'de kesit yok: 10 + 530 × 0,33, saçak 30 paftanın çatı alanından). Beşik bugünkü gibi (tek ön görünüş ve profil;
bayt bayt aynılık `testler/referans/dogrula.py`'nin P6001 adımında). Bu bir çizim kilididir; paftaya uygunluk yan yana kıyasla
(İE-17 › Kanıt).
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cephe_gorunus as CG, dxf_out, geometry as G, sunum  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
VERI = KOK / "testler" / "motor" / "veri"
BASLIK = [f"{CG.AD[t]} GÖRÜNÜŞ - ÇALIŞMA" for t in CG.TARAFLAR]

# ev: (özellik tablosunun çatı satırı, mahya − duvar üstü (paftanın kesiti), profilin ve çatının alt yazısı)
BEKLENEN = {
    "AP13": ("Beşik + Cumba — %32,88 eğim, 30 cm saçak, 10 cm topuk", 149.4,
             ["Makas 788 cm'yi geçer; ana mahya 823 cm (alın saçaklarıyla), cumbanın mahyası 225,75 cm. Ölçüler cm.",
              "Beşik + Cumba çatı | cumba ön cephede 0–391,5 cm, eğim ana çatıyla aynı (%32,88)"]),
    "AP16": ("Beşik + Cumba — %32,88 eğim, 30 cm saçak, 10 cm topuk", 170.86,
             ["Makas 918,5 cm'yi geçer; ana mahya 823 cm (alın saçaklarıyla), cumbanın mahyası 225,75 cm. Ölçüler cm.",
              "Beşik + Cumba çatı | cumba ön cephede 0–391,5 cm, eğim ana çatıyla aynı (%32,88)"]),
    "AP01": ("Kırma — %33 eğim, 30 cm saçak, 10 cm topuk", 184.9,
             ["Makas 1000 cm'yi geçer; mahya 438,7 cm, kırma uçları arası. Ölçüler cm.",
              "Kırma çatı | uç yüzler sol %32,5 · sağ %36,2"]),
}


def _ie(ad: str) -> dict:
    return json.loads(((VERI if ad == "PK01" else EVLER) / f"{ad}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=sorted(BEKLENEN) + ["PK01"])
def cizim(request, tmp_path_factory):
    import ezdxf
    ad = request.param
    cikti = tmp_path_factory.mktemp(ad)
    m = dxf_out.uret(copy.deepcopy(_ie(ad)), cikti)
    return ad, m, cikti, ezdxf.readfile(cikti / m["dxf"]).modelspace()


def _yazilar(msp) -> list[str]:
    return [e.dxf.text for e in msp.query("TEXT")]


def test_evler_listesi():
    assert sorted(p.stem for p in EVLER.glob("*.json")) == sorted(BEKLENEN)


@pytest.mark.parametrize("ad", sorted(BEKLENEN))
def test_motor_dogrulamasi_ve_uyarisiz(ad):
    ie = _ie(ad)
    assert sunum.motor_dogrulamasi(copy.deepcopy(ie)) == {"passed": True, "errors": []}
    # kişi ve bayi adı yok: talep yer tutucuyla (paftanın anteti İş Emri'ne girmez)
    assert ie["talep"]["bayi"] == {"kod": ad, "ad": f"Bayi {ad[:2]}-{ad[2:]}"} and ie["talep"]["musteri_adi"] == f"{ad[:2]}-{ad[2:]}"


def test_on_onay_pdf(cizim):
    ad, m, cikti, msp = cizim
    assert m["validation_passed"] is True and m["pdf"] and (cikti / m["pdf"]).stat().st_size > 0
    yazi = _yazilar(msp)
    if ad == "PK01":                       # beşik: bugünkü tek ön görünüş ve profil
        assert yazi.count("ÖN GÖRÜNÜŞ - ÇALIŞMA") == 1 and not set(BASLIK[1:]) & set(yazi)
        assert "Makas kısa kenarı geçer; mahya uzun kenar boyunca uzanır. Ölçüler cm." in yazi
        return
    satir, mahya, alt = BEKLENEN[ad]
    for s in BASLIK + ["ÇATI PROFİLİ - TOPUK VE SAÇAK", satir] + alt:
        assert yazi.count(s) == 1, s
    # tepe ölçüsü (duvar üstünden) paftanın kesitiyle; dört görünüşte ve profilde aynı sayı
    olcu = [round(e.get_measurement(), 2) for e in msp.query("DIMENSION") if e.dxf.layer in ("ON_OLCU", "CATI_OLCU")]
    assert olcu.count(pytest.approx(mahya, abs=0.05)) >= 5, olcu


def test_gorunusler_birbirine_binmez(cizim):
    # dört görünüş yan yana: ON_* katmanlarının varlıkları x'te dört ayrık küme, sırası ön, arka, sol, sağ, aralar en az 200; profil (CATI_*)
    # en sağda, sağ görünüşten en az 200 ötede
    from ezdxf import bbox
    ad, m, cikti, msp = cizim
    if ad == "PK01":
        pytest.skip("beşik: tek ön görünüş")
    ara = sorted(((b.extmin.x, b.extmax.x, e) for e in msp if e.dxf.layer.startswith("ON_")
                  for b in [bbox.extents([e])] if b.has_data), key=lambda t: t[:2])
    kume = []
    for a, b, e in ara:
        if kume and a <= kume[-1][1] + 200:
            kume[-1][1] = max(kume[-1][1], b); kume[-1][2].append(e)
        else:
            kume.append([a, b, [e]])
    assert [[x.dxf.text for x in k[2] if x.dxftype() == "TEXT" and "GÖRÜNÜŞ" in x.dxf.text] for k in kume] == [[s] for s in BASLIK]
    profil = [b.extmin.x for e in msp if e.dxf.layer.startswith("CATI_") for b in [bbox.extents([e])] if b.has_data]
    assert min(profil) > kume[-1][1] + 200


def test_gorunuste_acikliklar_plandan(cizim):
    # her görünüşte pencere ve kapı bloğu sayısı `cephe_gorunus.cephe`'ninki (o da planla aynı: `test_gorunus_prefabrik`)
    ad, m, cikti, msp = cizim
    if ad == "PK01":
        pytest.skip("beşik: tek ön görünüş")
    plan = G.kur(copy.deepcopy(_ie(ad)))
    beklenen = sum(len(CG.cephe(plan, t)["acikliklar"]) for t in CG.TARAFLAR)
    bloklar = [e.dxf.name for e in msp.query("INSERT") if e.dxf.layer == "ON_DOGRAMA"]
    assert len(bloklar) == beklenen and set(bloklar) <= {"kaynak-on-pencere", "kaynak-on-kapi"}
