"""İE-29 PR-2 · Tek uçlu kırmanın (AP-27) yükleme listesi: çatı satırları çatının kendi kenarlarından, makas planı paftadan.

AP-27'nin İş Emri'si `testler/kor/projeler/AP27/is_emri.json` (montaj paftasından; çizimi Lokman 4 Kasım 2026 05:19'da onayladı). Makas
sayıları paftanın makas ve panel yerleşim planından: MK1–MK7 ana makas (mahyaya paralel), MK8–MK14 ve MK17–MK23 iki saçak bandındaki kısa
makaslar, MK15 ve MK24 çapraz, MK16 ve MK25 köşe kısa makası (25); ana makasların arasında P1–P6 çatı paneli. Gerçek liste bu testten
sonra, kendi listemiz commit'lenince açılır (kör). İki ucu kırma çatıda (AP-01) bu kural tutmuyor; İE-33 PR-2'den beri AP-01'in kendi
paftasındaki makas planıyla yazılır (`test_ie33_kirma_liste.py`). LLM yok.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

AP27 = KOK / "testler" / "kor" / "projeler" / "AP27" / "is_emri.json"
AP01 = KOK / "testler" / "cizim" / "evler" / "AP01.json"


def _ie(yol: Path = AP27) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _adet(L: dict, bas: str) -> dict:
    return {s["kalem"]: s["adet"] for s in L["satirlar"] if s["kalem"].startswith(bas)}


@pytest.fixture(scope="module")
def liste() -> dict:
    return PL.liste(PL.model_motor(_ie()))


def test_ap27_makas_plani_paftadaki_gibi(liste):
    assert _adet(liste, "Makas") == {"Makas (ana, mahyaya paralel) · ana çatı": 7, "Makas (kısa) · ana çatı": 14,
                                     "Makas (çapraz, kırma) · ana çatı": 2, "Makas (köşe kısa) · ana çatı": 2}
    assert liste["girdi_ozeti"]["makas"] == 25                                        # paftada MK1–MK25
    assert _adet(liste, "Çatı paneli") == {"Çatı paneli (makas arası) · ana çatı": 6}  # P1–P6
    assert not _adet(liste, "Makas (baş)") and not _adet(liste, "Makas (orta)")


def test_ap27_cati_parcasi_kenarlardan():
    c = PL.model_motor(_ie())["cati"]
    assert len(c) == 1 and c[0]["tip"] == "kirma" and c[0]["kalkan"] == 1
    a = c[0]
    assert (a["aciklik_cm"], a["boy_cm"], a["mahya_boy_cm"]) == (1000.0, 773.0, 303.0)  # mahya kalkan saçağından kırma tepesine
    assert sorted(a["sacak_hatlari_m"]) == [8.33, 8.33, 10.6]                          # üç saçak (kırma yüzünün tabanı 1060)
    assert a["alin_kenarlari_m"] == [5.579, 5.579] and a["kirma_m"] == [7.695, 7.695]
    km = a["kirma_makas"]
    assert (km["aralik"], km["bant_cm"], km["kisa_bant"]) == (8, 128.75, 7)


def test_ap27_kaplama_ve_mahya(liste):
    assert _adet(liste, "Trapez sac ·") == {"Trapez sac · ana çatı": 20}               # kitabın kırma çatı dizilimi, 100 cm'lik şeritler (D-50)
    assert {s["olcu"] for s in liste["satirlar"] if s["kalem"].startswith("Trapez sac ·")} == {"L 5630"}   # eğik 5,58 + taşma
    assert _adet(liste, "Trapez sac mahyası") == {"Trapez sac mahyası": 4 + 8 + 8}     # mahya 3,03 ve iki kırma hattı 7,70, hat başına ÷ 1 (D-50)
    assert not _adet(liste, "Kırma mahyası")                                          # trapezde kırma hattı trapez mahyasında
    assert _adet(liste, "Mahya bandı") == {"Mahya bandı": 2}                           # 3,03 + 2 × 7,70 = 18,42 m ÷ 10
    assert _adet(liste, "Metal dere inişi") == {"Metal dere inişi aparatı": 5}         # iki köşe + iki uç, 10,6 m'lik saçağa bir orta
    assert _adet(liste, "Dere kapağı") == {"Dere kapağı": 2}                           # dere üç saçakta kesintisiz, iki serbest uç


def test_ap27_sandvicte_ayni_dizilim():
    ie = _ie()
    ie["ozellikler"]["Çatı Kaplaması"] = "Sandviç Panel"
    L = PL.liste(PL.model_motor(ie))
    assert sum(_adet(L, "Sandviç panel (").values()) == 20 and not _adet(L, "Trapez sac ·")
    assert L["girdi_ozeti"]["makas"] == 25


def test_iki_ucu_kirma_kendi_kuraliyla():
    """AP-01 (iki ucu kırma, paftada 29 makas) tek uçlu kırmanın kuralıyla tutmuyordu (İE-29'da liste yazılmazdı). İE-33 PR-2: iki ucu
    kırma kendi paftasının makas planıyla (mahyaya dik ana makas, uçlarda kısa ve çapraz makas); tek uçlu kırmanın sayısı aynen."""
    km = PL.model_motor(_ie(AP01))["cati"][0]["kirma_makas"]
    assert km["tur"] == "iki_uclu" and km["ana"] + km["kisa"] + km["capraz"] + km["kose_kisa"] == 29
    assert PL.is_emrinden(_ie(AP01))["girdi_ozeti"]["makas"] == 29
    assert PL.is_emrinden(copy.deepcopy(_ie()))["girdi_ozeti"]["makas"] == 25
