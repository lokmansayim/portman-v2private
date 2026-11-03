"""D-28 A11 · Model atölyesinin kontrol sayfasının onaylı hedef örneği (İE-09 PR-8).

Lokman KT-04'ü kontrol sayfası c07 ile kabul etti (1 Kasım 2026 11:45 UTC, karar kartı). O sayfa proje dosyalarında durur; depoda onun
girdisi (c07 çizildiği anki kart, `KT04_kart_c07.json`), kayıtlı tanım ve pimler ile sayfa sayfa içerik izi durur (`hedef.json`).
Sayfa bugünkü koddan yeniden üretilir: çizim `atolye.py ciz`'in ayarlarıyla, sabit üretim zamanıyla (D-02 madde 2), sayfa aynı karttan
(`araclar/atolye.kontrol_sayfasi_yeniden`). İzi hedefle aynı olmalı. Onaylanan sayfadan tek fark paftanın antedindeki üretim tarihidir
(`hedef.json › fark`). Hedef yalnız Lokman'ın onayıyla ve gerekçeli kararla yeniden dondurulur (D-02); testi geçirmek için değiştirilmez.

Yeniden üretim model başına ~20 sn sürer: banka tam izleri gibi `PORTMAN_BANKA_TAM=1` ister (CI ve `ortam_kur.sh --dogrula` koyar)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar import atolye as A  # noqa: E402
from araclar import atolye_sayfa  # noqa: E402

HEDEF = json.loads(Path(__file__).with_name("hedef.json").read_text(encoding="utf-8"))
G = HEDEF["girdi"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_hedef_kaydi_onayli_sayfayla_tutarli():
    o = HEDEF["onay"]
    assert o["kim"] == "Lokman" and o["tarih"] and o["dayanak"] and o["karar"] and o["komut"]
    # girdi depoda ve kayıttaki gibi: c07 anındaki kart, bankanın dondurulmuş tanımı ve pimleri
    kart = json.loads((KOK / G["kart"]).read_text(encoding="utf-8"))
    assert _sha(KOK / G["kart"]) == G["kart_sha256"]
    assert kart["son_cizim"]["no"] == 7 and kart["durum"] == "kontrolde" and kart["son_cizim"]["tanim_sha256"] == G["tanim_sha256"]
    kontrol = json.loads((KOK / "modeller" / "banka" / "KT04" / "kontrol.json").read_text(encoding="utf-8"))
    assert _sha(KOK / G["tanim"]) == G["tanim_sha256"] == kontrol["tanim_sha256"]
    for alan in ("kural_seti", "karkas_kurali"):
        assert G[alan] == kontrol[alan] and _sha(KOK / G[alan]) == G[f"{alan}_sha256"]
    # onay bu çizime: bankadaki kartın kabul kaydı c07
    banka = json.loads((KOK / "modeller" / "banka" / "KT04" / "kart.json").read_text(encoding="utf-8"))
    assert banka["durum"] == "kabul" and banka["kabul"]["cizim"] == 7 and banka["kabul"]["kim"] == "Lokman"
    # hedef onaylanan sayfayla yalnız kayıtlı sayfada (üretim tarihi) ayrılır
    onayli, hedef = o["onaylanan"]["sayfalar"], HEDEF["sayfalar"]
    assert len(onayli) == len(hedef) == 5
    assert [i + 1 for i, (a, b) in enumerate(zip(onayli, hedef)) if a != b] == HEDEF["farkli_sayfalar"] == [3]


def test_sayfa_izi_icerigi_izler(tmp_path):
    # PyMuPDF her kayıtta ayrı bayt yazar; iz içerikten: aynı kart aynı iz, kartta tek değer değişince yalnız o sayfanın izi değişir
    kart = json.loads((KOK / G["kart"]).read_text(encoding="utf-8"))
    a = atolye_sayfa.kontrol_pdf(kart, tmp_path, "KT04", tmp_path / "a.pdf")
    b = atolye_sayfa.kontrol_pdf(kart, tmp_path, "KT04", tmp_path / "b.pdf")
    c = atolye_sayfa.kontrol_pdf(kart | {"durum": "kabul"}, tmp_path, "KT04", tmp_path / "c.pdf")
    ia, ib, ic = A.sayfa_izi(a), A.sayfa_izi(b), A.sayfa_izi(c)
    assert ia == ib and len(ia) == 1 and ia != ic


@pytest.mark.skipif(os.environ.get("PORTMAN_BANKA_TAM") != "1", reason="kontrol sayfasının yeniden üretimi PORTMAN_BANKA_TAM=1 ister (CI koyar)")
def test_kt04_kontrol_sayfasi_onayli_ornekle_ayni(tmp_path):
    kart = json.loads((KOK / G["kart"]).read_text(encoding="utf-8"))
    pdf = A.kontrol_sayfasi_yeniden(kart, KOK / G["tanim"], tmp_path / "KT04_kontrol_c07.pdf")
    izler = A.sayfa_izi(pdf)
    farkli = [i + 1 for i in range(max(len(izler), len(HEDEF["sayfalar"]))) if izler[i:i + 1] != HEDEF["sayfalar"][i:i + 1]]
    assert farkli == [], f"kontrol sayfası onaylı hedef örnekten farklı: sayfa {farkli} (hedef yalnız Lokman'ın onayıyla yeniden dondurulur, D-02)"
