"""BK-12 PR-R · IFC makas yeri (`motor/ifc_uret.py › cati`, makaslar x'i geçince).

Kural: baş makaslar uç duvarların ekseninde (5 cm ve boy − 5 cm), orta makaslar boydan boya kesintisiz koşan saçak duvarının pano
eklerinde; PK-01'de paftadaki MK01–MK09 ("125,5 c/c"). İki saçak duvarı da kesintisizse ortak ekler alınır, ekler farklıysa uyarı
yazılır; ikisi de kesintiliyse eşit aralık kalır ve özete uyarı yazılır. Makas sayısı değişmez: yükleme listesi makasları kendi
kuralıyla sayar (`prefabrik_liste.py`, saçak duvarının pano koşusu ÷ 125,5 yukarı + 1), IFC aynı sayıyı verir.
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
from motor import ifc_uret as I, prefabrik_liste as PL  # noqa: E402

PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"
YAN = KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json"
YEDI = [KOK / "is_emri" / f for f in ("ALTIN_2plus1_6x8.json", "P6001_2plus1_6x6.json", "P6001_ayna_x.json", "P6001_ayna_y.json")] + \
       [KOK / "is_emri" / "adaylar" / f"TEST0{i}.json" for i in (1, 2, 3)]
PK01_PAFTA = [5, 116.5, 242, 367.5, 493, 618.5, 744, 869.5, 995]          # MK01–MK09: baş makaslar ve sol duvarın pano ekleri
YAN_KAYNAK = [5, 130.5, 256, 381.5, 507, 632.5, 758, 883.5, 1009, 1071.75]  # ref_yan DXF'inin sol duvarındaki pano ekleri


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _cati(G: dict, yol: Path) -> dict:
    u = I.IfcUretici(G, "makas yeri")
    u.calistir(yol)
    return u.cati_ozet


def _esit(Hd: float) -> list[float]:
    """PR-R'den önceki dizilim: 5 … boy − 5 arası eşit aralık."""
    n = math.ceil((Hd - 10) / 125.5) + 1
    return [round(5 + i * (Hd - 10) / (n - 1), 2) for i in range(n)]


def _boy(G: dict) -> float:
    return max(p["rect"][3] for p in G["panolar"])


def test_pk01_makaslari_paftadaki_eklerde(tmp_path):
    oz = I.uret(_oku(PK01), tmp_path / "pk01.ifc")
    assert oz["sema_hatasi"] == 0
    assert oz["cati"]["makas"] == 9 and oz["cati"]["makas_y_cm"] == PK01_PAFTA and "uyari" not in oz["cati"]
    assert {round(b - a, 2) for a, b in zip(PK01_PAFTA[1:-1], PK01_PAFTA[2:-1])} == {125.5}


def test_yan_verandali_kaynagin_pano_eklerinde(tmp_path):
    c = I.uret(_oku(YAN), tmp_path / "yan.ifc")["cati"]
    assert c["makas"] == 10 and c["makas_y_cm"] == YAN_KAYNAK and "uyari" not in c
    # orta makaslar 125,5 arayla; son açıklık 1009'da başlayan 62,75'lik pano (yarım pano), baş makas uç duvarın ekseninde
    assert {round(b - a, 2) for a, b in zip(c["makas_y_cm"][1:-1], c["makas_y_cm"][2:-1])} == {125.5}
    assert round(c["makas_y_cm"][-1] - c["makas_y_cm"][-2], 2) == 62.75


@pytest.mark.parametrize("yol", YEDI, ids=lambda p: p.stem)
def test_yedi_evde_yer_eskisiyle_ayni(yol, tmp_path):
    ie = _oku(yol)
    c = I.uret(ie, tmp_path / "ev.ifc")["cati"]
    assert c["makas_y_cm"] == _esit(_boy(I.hazirla(copy.deepcopy(ie)))) and "uyari" not in c


@pytest.mark.parametrize("yol", [PK01, YAN] + YEDI, ids=lambda p: p.stem)
def test_makas_sayisi_listeyle_ayni(yol, tmp_path):
    ie = _oku(yol)
    assert I.uret(ie, tmp_path / "ev.ifc")["cati"]["makas"] == PL.liste(PL.model_motor(ie))["girdi_ozeti"]["makas"]


def test_iki_sacak_duvari_kesintiliyse_esit_aralik_ve_uyari(tmp_path):
    """PK-01'in sağ saçak duvarı verandada kesik (205'ten başlar); sol duvardan bir pano çıkınca iki duvar da kesintili."""
    G = I.hazirla(_oku(PK01))
    G["panolar"] = [p for p in G["panolar"] if not (p["yon"] == "y" and p["tur"] == "dis" and p["rect"][0] == 0 and p["rect"][1] == 367.5)]
    c = _cati(G, tmp_path / "kesik.ifc")
    assert c["makas_y_cm"] == _esit(_boy(G)) and c["makas"] == 9
    assert c["uyari"] == ["makas yeri: boydan boya kesintisiz saçak duvarı yok; makaslar eşit aralıklı"]


def test_iki_sacak_duvarinin_ekleri_farkliysa_ortak_ekler_ve_uyari(tmp_path):
    """Bugünkü dokuz evin hiçbirinde iki saçak duvarı birden kesintisiz değil. ALTIN'ın sol duvarı verandada kesik (256'dan başlar);
    5–256 arası tek bir 251'lik panoyla kapanınca iki duvar da kesintisiz olur, sağın 130,5'teki eki solda yoktur: o makas düşer."""
    G = I.hazirla(_oku(KOK / "is_emri" / "ALTIN_2plus1_6x8.json"))
    sol = [p for p in G["panolar"] if p["yon"] == "y" and p["tur"] == "dis" and p["rect"][0] == 0]
    assert min(p["rect"][1] for p in sol) == 256
    ek = copy.deepcopy(min(sol, key=lambda p: p["rect"][1]))
    ek["rect"][1], ek["rect"][3], ek["boy"], ek["acikliklar"] = 5.0, 256.0, 251.0, []
    ek["id"] = max(q["id"] for q in G["panolar"]) + 1
    G["panolar"].append(ek)
    c = _cati(G, tmp_path / "iki_tam.ifc")
    assert c["makas_y_cm"] == [y for y in _esit(_boy(G)) if y != 130.5] and c["makas"] == 8
    assert c["uyari"] == ["makas yeri: iki saçak duvarının pano ekleri farklı; orta makaslar ortak eklerde"]
