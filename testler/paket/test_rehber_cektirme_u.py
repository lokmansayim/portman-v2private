"""Montaj rehberinde çektirme U'su yükleme listesiyle aynı yerde ve aynı sayıda (D-28 madde 1: aynı sayıyı iki kod üretiyorsa biri kaynaktır,
öteki onu okur). Kaynak `motor.prefabrik_liste.birlesim_uclari`: iç duvarın bir duvara panonun ortasında T ile girdiği yer, dış köşeye
geldiği yer (100'lük köşede 60'lığa geçiş; D-104 ile 90 m² 3+1'in giriş nişi) ve kapısız serbest biten bölmenin ucu (İE-27; Lokman,
3 Kasım 2026 09:52, madde 13). Önceden rehber yalnız dış duvara pano ortasında giren U'yu çiziyordu: 90 m² 3+1'de listede 2 / sahnede 0,
80 m² 2+1'de 2 / 0, 88 m²'de 8 / 4. Lokman, 15 Kasım 2026 22:19 UTC: "rehberi bozma canlıda kalsın sen sadece depodakileri düzelt"."""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
VERI = KOK / "testler" / "motor" / "veri"

T, K, S = ("iç duvar bu duvara panonun ortasında T ile girer", "iç duvar köşe direğinde biter; dış duvardan incedir",
           "kapısız bölmenin serbest ucu")
EVLER = {   # İş Emri, kart kodu, rehber kodu, beklenen U'lar (tür → adet), U'ların yeri (cm, Motor çerçevesi)
    "TK01_r08": ("TK01", "TK-01", {K: 2}, {(386.5, 135.5), (512.0, 135.5)}),
    "TK04_r08": ("TK04", "TK-04", {T: 1, K: 1}, {(318.75, 515.0), (381.5, 203.25)}),
    "TK03": ("TK03", "TK-03", {T: 4, K: 2, S: 2}, {(650.4, 513.55), (551.5, 349.45), (1006.0, 349.45), (1226.7, 298.55),
                                                  (548.5, 242.0), (548.5, 513.55), (780.6, 693.3), (831.95, 352.45)}),
    "TK02_r04": ("TK02", "TK-02", {}, set()),      # iç 100 (BK-18): listede 0, rehberde 0
}


@pytest.fixture(scope="module", params=sorted(EVLER))
def rehber(request, tmp_path_factory):
    from motor import kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ad = request.param
    kart_kodu, kod, _, _ = EVLER[ad]
    ie = json.loads((VERI / f"{ad}.json").read_text(encoding="utf-8"))
    kart = tmp_path_factory.mktemp(f"{ad}_rehber")
    kart_model.uret(copy.deepcopy(ie), kart, kart_kodu)
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    return ad, veri.kur(copy.deepcopy(ie), kart, kart_kodu, L, kod), L


def test_listeyle_ayni_sayida(rehber):
    ad, d, L = rehber
    liste = sum(s["adet"] for s in L if s["kalem"].startswith("Çektirme U'su") and ("(iç duvar)" in s["kalem"] or s["kalem"] == "Çektirme U'su 60"))
    assert len(d["ceku"]) == liste == sum(EVLER[ad][2].values()), (ad, len(d["ceku"]), liste)


def test_yeri_ve_turu(rehber):
    ad, d, _ = rehber
    assert Counter(u["bu"] for u in d["ceku"]) == Counter(EVLER[ad][2])
    assert {tuple(u["xy"]) for u in d["ceku"]} == EVLER[ad][3]
    for u in d["ceku"]:
        assert u["t"] == 6 and sorted(map(abs, u["yon"])) == [0, 1]      # 60'lık iç duvar; U duvar boyunca, ucun içine bakar
