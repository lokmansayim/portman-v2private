"""İE-27 · Kör ölçüm farklarından Lokman'ın 3 Kasım 2026 09:52 cevaplarıyla değişen liste kuralları (D-45).

Girdiler kör ölçümün açık projelerinin depodaki İş Emri'leri (`testler/kor/projeler/<KOD>/is_emri.json`; bizim okumamız, gerçek liste değil).

- Madde 3: 3'lü H = bir H + bir çektirme U'su; dış duvarın pano ekine T ile gelen iç duvar da 3'lü H'tır (bugüne kadar yalnız
  `dis_duvar_t_bolme` ile sayılıyordu). Dübelli / kulaklı ayrımı yapılmaz (kıyasta).
- Madde 4: köşe direğinin tipi (A, B, C, D, "özel") yok; kaçlık (100 / 60) ve adet. "Özel köşe direği (D)" satırı 100'lük köşeye katılır.
- Madde 6: mahya bandı mahya boyu kadar, ötesi yok.
- Madde 7: temiz su takımı ıslak hacim başına ("2 banyo varsa 2 takım").
- Madde 9: 5,5 × 25 trapez vida satırı (aşık ve omega).
- Madde 13: 60'lık çektirme U'su 3'lü H olmayan yerde: duvar panonun ortasında odalara bölünüyorsa, 100'lük köşede 60'lığa geçişte,
  kapısız yarım kalan bölmede. Pafta kipinde birleşimler okunmadığı için eski sabit kural kalır.
"""
from __future__ import annotations
import copy
import json
import math
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

KOR = KOK / "testler" / "kor" / "projeler"
MOTOR_KIPI = ["AP09", "AP11", "AP14", "AP15", "AP18", "AP21", "AP22", "AP25", "AP26", "AP28", "PK02"]


def _ie(kod: str) -> dict:
    return json.loads((KOR / kod / "is_emri.json").read_text(encoding="utf-8"))


def _liste(N: dict) -> list[dict]:
    return PL.liste(N, PL.kurallari_oku())["satirlar"]


def _kural(ad: str) -> dict:
    return PL.kurallari_oku()["prefabrik"]["kurallar"][ad]


def _adet(satirlar: list[dict], kalem: str) -> int:
    s = [x for x in satirlar if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, [x["kalem"] for x in satirlar])
    return s[0]["adet"]


@pytest.fixture(scope="module")
def modeller():
    return {k: PL.model_motor(_ie(k)) for k in MOTOR_KIPI}


@pytest.fixture(scope="module")
def listeler(modeller):
    return {k: _liste(N) for k, N in modeller.items()}


def test_uclu_h_dis_duvarin_ekine_gelen_ic_duvarda(listeler):
    """PK-02: iç duvarların dışa geldiği beş T'nin hepsi pano ekinde (3'lü H 100 × 100 × 60), iç duvarların birbirine geldiği üçü de."""
    L = listeler["PK02"]
    assert _adet(L, "3'lü H 100 × 100 × 60 (dış duvar T'si)") == 5
    assert _adet(L, "3'lü H standart 60 (iç T)") == 3


def test_uclu_h_sayisi_t_bolme_isaretinden_bagimsiz(modeller):
    """`dis_duvar_t_bolme` işareti olmadan da dış duvarın ekine gelen iç duvar 3'lü H'tır; işaretle sayı değişmez."""
    ie = _ie("PK02")
    ie["yapi"].setdefault("dizilim", {})["dis_duvar_t_bolme"] = True
    isaretli = PL.model_motor(ie)
    say = lambda N: sum(1 for e in N["ekler"] if e["duvar"] == "dis" and e["cins"] == "uclu")
    assert say(isaretli) == say(modeller["PK02"]) == 5


@pytest.mark.parametrize("kod", MOTOR_KIPI)
def test_cektirme_u_60_yerinden(kod, modeller, listeler):
    """Çektirme U'su 60 = eklemsiz T + dış köşeye gelen iç duvar + serbest biten bölme; sabit 2 değil."""
    cy = modeller[kod]["cektirme_yerleri"]
    assert set(cy) == {"t_orta", "dis_kose", "serbest"}
    ic = [x for x in listeler[kod] if x["kalem"].startswith("Çektirme U'su") and x["dayanak"] == "Kural (Lokman 3.11)"]
    assert len(ic) == 1 and ic[0]["adet"] == sum(cy.values()), (kod, cy, ic)
    assert ic[0]["olcu"].endswith(" × 2440") and "pafta kipinde" not in ic[0]["formul"]


def test_cektirme_yerleri_ornek(modeller):
    """AP-11: panonun ortasına gelen üç bölme ve dış köşeye gelen bir iç duvar; PK-02: bütün T'ler pano ekinde, çektirme yok."""
    assert modeller["AP11"]["cektirme_yerleri"] == {"t_orta": 3, "dis_kose": 1, "serbest": 0}
    assert modeller["PK02"]["cektirme_yerleri"] == {"t_orta": 0, "dis_kose": 0, "serbest": 0}


def test_cektirme_serbest_uc_sayilir(modeller):
    """Kapısız yarım kalan bölme: iç duvarın bir ucu `serbest` biterse o uca çektirme U'su gelir."""
    from motor import geometry as G
    plan = G.kur(_ie("PK02"))
    assert not any(n == "serbest" for d in plan.duvarlar for n in d.uc_notu.values())
    N = copy.deepcopy(modeller["PK02"])
    N["cektirme_yerleri"] = {**N["cektirme_yerleri"], "serbest": 2}
    assert _adet(_liste(N), "Çektirme U'su 60") == 2


def test_pafta_kipinde_eski_sabit_kural():
    yp = KOK / "testler" / "kor" / "projeler" / "PK07"
    P = json.loads((yp / "proje.json").read_text(encoding="utf-8"))
    N = PL.model_pafta(json.loads((KOK / P["girdi"]["yapi_pafta"]).read_text(encoding="utf-8")))
    assert "cektirme_yerleri" not in N
    L = _liste(N)
    s = [x for x in L if x["kalem"].startswith("Çektirme U'su") and "pafta kipinde" in x["formul"]]
    assert len(s) == 1 and s[0]["adet"] == _kural("cektirme_u_ic")["deger"] and s[0]["dayanak"] == "Kural (Portatifev)"
    assert not [x for x in L if x["dayanak"] == "Kural (Lokman 3.11)" and x["kalem"].startswith("Çektirme U'su")]


def test_kose_diregi_tipsiz(listeler):
    """Hiçbir listede tipli köşe satırı yok; özel köşe 100'lük köşe satırına katılır."""
    for kod, L in listeler.items():
        assert not [x for x in L if "Özel köşe" in x["kalem"]], kod
    N = copy.deepcopy(PL.model_motor(_ie("PK02")))
    once = _adet(_liste(N), "10'luk köşe direği 100 × 100")
    N["koseler"] = {**N["koseler"], "ozel": 1}
    L = _liste(N)
    assert _adet(L, "10'luk köşe direği 100 × 100") == once + 1 and not [x for x in L if "Özel köşe" in x["kalem"]]


@pytest.mark.parametrize("kod", MOTOR_KIPI)
def test_mahya_bandi_mahya_boyundan(kod, listeler):
    """Mahya bandı = ⌈beşik mahyalarının boyu (+ kırma hatları) ÷ rulo⌉; mahya parçası adedine bağlı değil."""
    L = PL.liste(PL.model_motor(_ie(kod)), PL.kurallari_oku())
    rulo = float(re.search(r"rulo ([\d,]+) m", next(x for x in L["satirlar"] if x["kalem"] == "Mahya bandı")["olcu"]).group(1).replace(",", "."))
    mahya = sum(c["mahya_m"] for c in L["girdi_ozeti"]["cati"] if c["tip"] == "besik")
    assert all(c["tip"] in ("besik", "tek_yon") for c in L["girdi_ozeti"]["cati"]), kod      # kırma yok: hatlar eklenmez
    assert _adet(L["satirlar"], "Mahya bandı") == math.ceil(mahya / rulo - 1e-9), kod


def test_temiz_su_islak_hacim_basina(modeller):
    """İkinci ıslak hacim takımı ikiye katlar; vitrifiye banyo başına (değişmedi)."""
    N = copy.deepcopy(modeller["AP09"])
    tek = {x["kalem"]: x["adet"] for x in _liste(N) if x["grup"] == "1010"}
    banyo = next(x for x in N["kapali"] if x["tur"] == "banyo")
    assert sum(1 for x in N["kapali"] if x["tur"] in ("banyo", "wc", "islak", "lavabo")) == 1
    N["kapali"].append(copy.deepcopy(banyo))
    iki = {x["kalem"]: x["adet"] for x in _liste(N) if x["grup"] == "1010"}
    takim = [k for k, _o, _a in _kural("tesisat_takimi")["deger"]]
    assert takim and all(iki[k] == 2 * tek[k] for k in takim)
    assert iki["Temiz su borusu"] == 2 * tek["Temiz su borusu"] == 12


@pytest.mark.parametrize("kod", MOTOR_KIPI)
def test_trapez_vida_5_5x25(kod, listeler):
    """(aşık × 10 + 3,75'lik omega × 10 + 2,5'lik parça × 6), 50'ye yukarı; adetler listenin kendi satırlarından."""
    L = listeler[kod]
    t = _kural("trapez_vida_5_5x25")
    assert t["durum"] == "lokman" and t["deger"] == {"asik": 10, "omega_3750": 10, "omega_2500": 6, "yuvarlama": 50}
    s = next(x for x in L if x["kalem"] == "Trapez vida 5,5 × 25 (aşık ve omega)")
    asik = sum(x["adet"] for x in L if x["kalem"] == "Aşık")
    assert f"aşık {asik} × 10" in s["formul"]
    v = sum(int(a) * int(b) for a, b in re.findall(r"(\d+) × (\d+)", s["formul"]))
    assert s["adet"] == math.ceil(v / 50) * 50 and s["adet"] % 50 == 0 and s["adet"] >= v and s["grup"] == "1008"
