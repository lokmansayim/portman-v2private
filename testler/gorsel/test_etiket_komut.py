"""Etiketli plan üzerinden yazılı düzeltme (Lokman 28 Kasım 2026 05:59:11 UTC "oda ismi versin büyüt veya küçült desin";
kart 06:00:14 "Yarım pano, duvarı sorsun"). Kod okur ve uygular; Motor kuramazsa bayiye nedeni yazılır."""
import copy
import json
from pathlib import Path

import pytest

from beyin import etiket_komut as K
from beyin import etiketli_plan as E
from beyin import gorsel_okuma as g
from motor import geometry as G

VERI = Path(__file__).parent / "veri"


@pytest.fixture(scope="module")
def kroki():
    ie = g.denetle(json.loads((VERI / "DONGU2_kroki_4x5_okuma.json").read_text(encoding="utf-8")))["cevrim"]["is_emri"]
    return ie, E.etiketler(G.kur(copy.deepcopy(ie)))


@pytest.fixture(scope="module")
def ev87():
    ie = json.loads((VERI / "DONGU2_87m2_okunan_is_emri.json").read_text(encoding="utf-8"))
    return ie, E.etiketler(G.kur(copy.deepcopy(ie)))


def _kos(ie, et, metin):
    km, sor = K.oku(metin, et)
    yeni, anladim, olmayan = K.uygula(ie, et, km)
    return yeni, anladim, olmayan, sor


def _m2(ie):
    return {m.ad: round(m.alan_m2, 2) for m in G.kur(copy.deepcopy(ie)).mahaller.values()}


def test_yonsuz_iki_duvar_sorulur(kroki):
    ie, et = kroki
    _, an, ol, _ = _kos(ie, et, "O2'yi büyüt")
    assert not an and ol == ["O2 (WC) hangi duvardan büyüsün? [Sol / Ön]"]


def test_yonlu_yarim_pano(kroki):
    ie, et = kroki
    yeni, an, ol, _ = _kos(ie, et, "O2'yi öne büyüt")
    assert not ol and an[0].startswith("O2 (WC) ön duvarı yarım pano büyüdü")
    assert _m2(yeni)["WC"] == pytest.approx(3.12)
    assert next(m for m in yeni["mahaller"] if m["ad"] == "WC")["konum_cm"] == [[318.75, 10.0, 495.0, 198.25]]


def test_aksa_kadar(kroki):
    ie, et = kroki
    yeni, an, ol, _ = _kos(ie, et, "O2'yi E aksına kadar büyüt")
    assert not ol and "E aksına" in an[0]
    assert next(m for m in yeni["mahaller"] if m["ad"] == "WC")["konum_cm"] == [[256.0, 10.0, 495.0, 135.5]]


def test_dis_duvar_kaymaz(kroki):
    ie, et = kroki
    _, an, ol, _ = _kos(ie, et, "O2'yi sağa büyüt")
    assert not an and "dış duvar" in ol[0] and "[Sol / Ön]" in ol[0]


def test_pencere_olcusu(kroki):
    ie, et = kroki
    yeni, an, ol, _ = _kos(ie, et, "P1 120x180 olsun")
    assert an == ["P1 (WC penceresi) 60x40 → 120x180"]


def test_olumsuz_sorulur(kroki):
    ie, et = kroki
    _, an, ol, sor = _kos(ie, et, "O2'yi büyütmeyin")
    assert not an and not ol and len(sor) == 1


def test_87_hol_saga_yalniz_kendi_boyunca(ev87):
    ie, et = ev87
    yeni, an, ol, _ = _kos(ie, et, "O3 sağa büyüt")
    assert not ol
    once, sonra = _m2(ie), _m2(yeni)
    degisen = {k for k in sonra if sonra[k] != once[k]}
    assert degisen == {"HOL", "BANYO", "SALON"}           # veranda ve yatak odaları aynı


def test_87_motor_kuramazsa_nedeni(ev87):
    ie, et = ev87
    yeni, an, ol, _ = _kos(ie, et, "O2'yi öne büyüt")
    assert yeni == ie and ol == ['"O2\'yi öne büyüt": plan bu değişiklikle kurulamadı (HOL ile YATAK ODASI 1 arasındaki kapıya yer kalmıyor).']
