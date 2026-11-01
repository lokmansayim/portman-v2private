"""İE-17 · Gerileme freni (A6): açılan her ev her koşuda yeniden çizilir; biri bozulursa test düşer.

Açılan evler (`testler/cizim/evler/`, montaj paftasından): Motor'un doğrulaması geçer; canlı ön onay PDF'i (`dxf_out.uret`) doğrulamadan
geçer, PDF çıkar; ön görünüşün yanında arka, sol ve sağ görünüş aynı biçimle, birbirine binmeden; özellik tablosunun çatı satırı paftanın
yazımıyla. Mahya kotu paftanın kesitinden (duvar üstünden, topuk dahil: AP-13 149,4, AP-16 170,86; AP-01'de kesit yok: 10 + 530 × 0,33,
saçak 30 paftanın çatı alanından). D-31 (Lokman, 29 Ekim 2026): beşik (PK-01) de dört görünüşle; ana çatının profili ve alt yazısı
("ÇATI PROFİLİ - TOPUK VE SAÇAK", "Makas … cm'yi geçer …", çatı tipi satırı) bütün paftalardan kalktı (11:12: "çatı profili topuk ve saçak
tamamen kaldır"); 60×40 pencere görünüşte vasistas. Bu bir çizim kilididir; paftaya uygunluk yan yana kıyasla (İE-17 › Kanıt).
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

# ev: (özellik tablosunun çatı satırı, mahya − duvar üstü (paftanın kesiti)); PK-01 beşik: 10 + 660 / 2 × 0,33
BEKLENEN = {
    "AP13": ("Beşik + Cumba — %32,88 eğim, 30 cm saçak, 10 cm topuk", 149.4),
    "AP16": ("Beşik + Cumba — %32,88 eğim, 30 cm saçak, 10 cm topuk", 170.86),
    "AP01": ("Kırma — %33 eğim, 30 cm saçak, 10 cm topuk", 184.9),
    # İE-17 PR-2: AP-15 girintili gövdenin beşiği (ana çatı + öndeki paralel cumba; kesit 145,29, cumba 83,4); AP-22 öne 62,75 taşan çapraz
    # cumba (kesit 147,34 ölçülerden %32,98; %32,88 ile 146,95; cumbanın kesiti 114,36, Motor 114,35)
    "AP15": ("Besik — %32,88 eğim, 30 cm saçak, 10 cm topuk", 145.29),
    "AP22": ("Beşik + Cumba — %32,88 eğim, 30 cm saçak, 10 cm topuk", 146.95),
}
PK01 = ("Besik — %33 eğim, 30 cm saçak, 10 cm topuk", 118.9)      # beşikte çatı adı canlıdaki yazımla (`dxf_out._cati_adi`)
# İE-17 PR-2 (1 Kasım 2026): kat planı aşamasında (sıra kuralı: önce kat planı → Lokman'ın onayı → çatı ve görünüşler). Planları
# `test_pafta_kiyasi.py` ve `testler/motor/test_ie17_pr2.py` denetler; çatıları gelince ön onay PDF'iyle `BEKLENEN`'e geçerler
PLAN_ASAMASI = ("AP03", "AP09")


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
    assert sorted(p.stem for p in EVLER.glob("*.json")) == sorted([*BEKLENEN, *PLAN_ASAMASI])


@pytest.mark.parametrize("ad", PLAN_ASAMASI)
def test_plan_asamasindaki_evler(ad):
    # kat planı kurulur; kişi ve bayi adı yok (talep yer tutucuyla, paftanın anteti İş Emri'ne girmez)
    ie = _ie(ad)
    G.kur(copy.deepcopy(ie))
    assert ie["talep"]["bayi"] == {"kod": ad, "ad": f"Bayi {ad[:2]}-{ad[2:]}"} and ie["talep"]["musteri_adi"] == f"{ad[:2]}-{ad[2:]}"


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
    satir, mahya = PK01 if ad == "PK01" else BEKLENEN[ad]
    for s in BASLIK + [satir]:
        assert yazi.count(s) == 1, s
    assert not [s for s in yazi if "PROFİLİ" in s or "cm'yi geçer" in s or " çatı | " in s]     # D-31: profil ve alt yazısı yok
    assert not [e for e in msp if e.dxf.layer.startswith("CATI_")]
    # tepe ölçüsü (duvar üstünden) paftanın kesitiyle; D-31 madde 14'ten beri kot yalnız ön ve sağ görünüşte (önce dördünde)
    olcu = [round(e.get_measurement(), 2) for e in msp.query("DIMENSION") if e.dxf.layer == "ON_OLCU"]
    assert olcu.count(pytest.approx(mahya, abs=0.05)) >= 2, olcu


def test_gorunusler_birbirine_binmez(cizim):
    # dört görünüş yan yana: ON_* katmanlarının varlıkları x'te dört ayrık küme, sırası ön, arka, sol, sağ, aralar en az 200 (D-31: profil yok)
    from ezdxf import bbox
    ad, m, cikti, msp = cizim
    ara = sorted(((b.extmin.x, b.extmax.x, e) for e in msp if e.dxf.layer.startswith("ON_")
                  for b in [bbox.extents([e])] if b.has_data), key=lambda t: t[:2])
    kume = []
    for a, b, e in ara:
        if kume and a <= kume[-1][1] + 200:
            kume[-1][1] = max(kume[-1][1], b); kume[-1][2].append(e)
        else:
            kume.append([a, b, [e]])
    assert [[x.dxf.text for x in k[2] if x.dxftype() == "TEXT" and "GÖRÜNÜŞ" in x.dxf.text] for k in kume] == [[s] for s in BASLIK]


def test_gorunuste_acikliklar_plandan(cizim):
    # her görünüşte pencere ve kapı bloğu sayısı `cephe_gorunus.cephe`'ninki (o da planla aynı: `test_gorunus_prefabrik`); 60×40 vasistas (D-31)
    ad, m, cikti, msp = cizim
    plan = G.kur(copy.deepcopy(_ie(ad)))
    ac = [a for t in CG.TARAFLAR for a in CG.cephe(plan, t)["acikliklar"]]
    bloklar = [e.dxf.name for e in msp.query("INSERT") if e.dxf.layer == "ON_DOGRAMA"]
    assert len(bloklar) == len(ac) and set(bloklar) <= {"kaynak-on-pencere", "kaynak-on-kapi", dxf_out.VASISTAS_BLOK[0], dxf_out.SURGULU_BLOK[0]}
    surgulu = sum(1 for d in G.kur(copy.deepcopy(_ie(ad))).duvarlar for p in d.panolar if p.acilim and p.acilim.acilis == "surgulu"
                  and p.acilim.tur == "pencere")
    assert bloklar.count(dxf_out.SURGULU_BLOK[0]) == surgulu                 # D-31 madde 11: sürgülü pencere görünüşte sürgülü (AP-15, AP-22)
    assert bloklar.count(dxf_out.VASISTAS_BLOK[0]) == sum(a["olcu"] in dxf_out.VASISTAS_OLCULERI for a in ac)
