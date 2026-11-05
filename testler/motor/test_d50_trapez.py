"""D-50 kilit testi (M-11): prefabrik trapez çatıda sac ve mahya standart 100 cm kapatır.

Lokman, 4 Kasım 2026 20:49: "yalnız trapez mahya sac kaç kapatırsa o kadar kapatır yani sac 100 kapatırsa trapez mahyada 100 kapatır";
21:19 karar kartı: "Sac da mahya da 100 cm"; 21:20: "biz bundan sonra standart olarak 100 kapatır yapacağız o yüzden Trapez Mahyada Sacda
100 kapatır olarak kuralla ve mühürle başa dönmeyelim düzelttiğimiz bir yer tekrar bozulmasın".

Bu dosya mühürlü konunun (M-11, `KARARLAR/muhurlu.json`) kilididir: değişirse CI kırmızıdır. Kural:
- prefabrik kural dosyasında `trapez_kapatma_m` = 1,0 ve `trapez_mahyasi` = `sac_kapatmasi`;
- İş Emri kapatma yazmazsa trapez sac her yüzde mahya boyu ÷ 1, mahya L 1000, her beşiğin mahyası ÷ 1 (bindirme düşülmez);
- tedarikçinin 80'lik sacı yalnız İş Emri'nin çatı kaplaması yazarsa ("Trapez Saç (80 cm kapatır)"): sac ÷ 0,8, mahya L 800 ÷ 0,8;
- kural kitabının (çelik, genel motor) 0,8'i ve kitabın trapez mahya kuralı (L 800, 20 cm bindirme) değişmez.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def N():
    return PL.model_motor(_oku(VERI / "PK01.json"))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


def _liste(N: dict, kurallar: dict, kaplama: str) -> dict:
    n = copy.deepcopy(N)
    n["ozellikler"] = {**n["ozellikler"], "Çatı Kaplaması": kaplama}
    return PL.liste(n, kurallar, _oku(VERI / "PK01_pafta_katmani.json"))


def _satir(L: dict, kalem: str) -> dict:
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, len(s))
    return s[0]


def test_kural_degerleri():
    R = _oku(KOK / "kurallar" / "liste" / "prefabrik.json")["kurallar"]
    assert R["trapez_kapatma_m"]["deger"] == 1.0 and R["trapez_kapatma_m"]["durum"] == "lokman"
    assert R["trapez_mahyasi"]["deger"] == "sac_kapatmasi" and R["trapez_mahyasi"]["durum"] == "lokman"
    assert "21:20" in R["trapez_kapatma_m"]["kaynak"] and "20:49" in R["trapez_mahyasi"]["kaynak"]


def test_kitapla_farkli_beyanli():
    F = {b["konu"]: b for b in _oku(KOK / "kurallar" / "liste" / "prefabrik.json")["kitapla_farkli"]}
    assert F["Trapez sac kapatması"]["prefabrik"] == "trapez_kapatma_m"
    assert F["Trapez sac mahyası"]["prefabrik"] == "trapez_mahyasi"


@pytest.mark.parametrize("kaplama", ["Trapez sac", "Trapez Saç", "Trapez sac (100 cm kapatır)"])
def test_standart_100(N, kurallar, kaplama):
    L = _liste(N, kurallar, kaplama)
    ana = next(c for c in N["cati"] if c["tip"] == "besik")
    sac = _satir(L, f"Trapez sac · {ana['ad']}")
    assert "÷ 1⌉" in sac["formul"]
    mahya = _satir(L, "Trapez sac mahyası")
    assert mahya["olcu"] == "L 1000"
    assert "÷ 1," in mahya["formul"] and "100 cm" in mahya["formul"] and "bindirme düşülmez" in mahya["formul"]
    assert (sac["adet"], mahya["adet"]) == (22, 11)          # PK-01 ana çatı: 2 yüz × ⌈10,60 ÷ 1⌉, mahya ⌈10,60 ÷ 1⌉


def test_ismi_yazilan_80lik(N, kurallar):
    L = _liste(N, kurallar, "Trapez Saç (80 cm kapatır)")
    ana = next(c for c in N["cati"] if c["tip"] == "besik")
    sac = _satir(L, f"Trapez sac · {ana['ad']}")
    mahya = _satir(L, "Trapez sac mahyası")
    assert "÷ 0,8⌉" in sac["formul"] and mahya["olcu"] == "L 800" and "÷ 0,8," in mahya["formul"]
    assert (sac["adet"], mahya["adet"]) == (2 * math.ceil(10.60 / 0.8), math.ceil(10.60 / 0.8)) == (28, 14)


def test_kitap_degismedi(kurallar):
    """Çelik ve genel motor kural kitabından okur: kitabın trapez sacı 0,8 kapatır, mahyası L 800 − 20 cm bindirme (D-50 › Değişmeyen).
    Güncel kitap da prefabriğin okuduğu dondurulmuş set de aynı."""
    for kitap in (_oku(KOK / "kurallar" / "liste" / "kurallar.json"), kurallar["ortak"]):
        assert kitap["trapez_sac_kapatma_m"]["deger"] == 0.8
        assert kitap["parca_boyu_m"]["trapez_mahyasi"]["deger"] == 0.8
        assert kitap["bindirme_m"]["trapez_mahyasi"]["deger"] == 0.2
