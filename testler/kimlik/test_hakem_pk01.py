"""İE-15 · KH-1 · PK-01'in doğru cevapları ve kıyas aracı (hakem; D-24).

Doğru cevap `veri/PK01_pafta_katmani.json`: mühürlü PK-01 montaj paftasının (SHA proje ayarında) tek genel okuyucuyla okunmuş pano, H ve
makas sayıları, PR #28'in `pafta_katmani.json` biçiminde. Pafta depoya girmez.

- Cevap, `main`'deki eski kod okumasıyla (`testler/motor/veri/PK01_pafta_montaj.json`: pano dikdörtgenleri, köşe, kanat, H konumu ve türü)
  ve PR #28'in PK-01 katmanıyla (H dört satır, baş ve orta makas) aynıdır.
- Liste üreteci (`motor/prefabrik_liste.py`) cevabı değişmeden okur; H ve makas satırlarının pafta sütunu PR #28 katmanıyla aynı çıkar.
- Kıyas aracı bugünkü IFC'de (`motor.ifc_uret`) kapı 1'i geçer: pano 50 (dış 30, iç 20), H 19 / 10 / 5 / 4, makas 2 + 7. H türlerinin
  ayrımı bugünkü IFC'de yok ("modelde yok", bilgi); kart modeli `PortatifEv_Parca.PaftaAnahtari` sözleşmesiyle taşır.
- `PORTMAN_PAFTA_DIZINI` altında `PK01.pdf` (SHA tutarsa) varsa okuyucu cevabı bayt bayt yeniden üretir; yoksa atlanır.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "testler" / "kimlik" / "hakem"))
import kiyas as KY  # noqa: E402
import pafta_oku as PO  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402

CEVAP = KOK / "testler" / "kimlik" / "veri" / "PK01_pafta_katmani.json"
PROJE = KOK / "testler" / "kimlik" / "hakem" / "projeler" / "PK01.json"
MOTOR_VERI = KOK / "testler" / "motor" / "veri"
H_TURU = {("pano_eki", "dübelli & kulaklı"): "dubelli_kulakli", ("pano_eki", "dübelli"): "dubelli", ("pano_eki", "standart"): "standart",
          ("uclu", "dübelli & kulaklı"): "uclu_dubelli_kulakli", ("uclu", "dübelli"): "uclu_dubelli", ("uclu", "standart"): "uclu_standart"}


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cevap():
    return _oku(CEVAP)


@pytest.fixture(scope="module")
def proje():
    return _oku(PROJE)


def test_cevap_bicimi(cevap, proje):
    assert cevap["pafta_sha256"] == proje["pafta_sha256"]
    assert cevap["kaynak"].startswith("PK-01 (AP-19) montaj paftası")
    assert cevap["teyit_bekliyor"] == [] and cevap["ayrinti"]["uyarilar"] == []
    assert cevap["okuyucu"] == {"surum": PO.SURUM, "sayfa_sayisi": 10, "sayfalar": {"h": 3, "makas": 7, "montaj": 2}}
    for k in ("makas_bas", "makas_orta", *(f"h_plani.{a}" for a in ("dis", "h_standart", "uclu_dis", "uclu_standart"))):
        v = cevap
        for a in k.split("."):
            v = v[a]
        assert set(v) == {"adet", "not"} and isinstance(v["adet"], int), k


def test_cevap_main_okumasiyla_ayni(cevap):
    """Pano dikdörtgenleri (±0,3 cm, aynı tür), köşe, kanat ve H konumu ve türü (±0,5 cm) `main`'deki eski okumayla aynı."""
    eski = _oku(MOTOR_VERI / "PK01_pafta_montaj.json")
    em, ym = eski["montaj_plani_s2"], cevap["ayrinti"]["montaj"]
    kalan = list(em["panolar"])
    for p in ym["panolar"]:
        q = min(kalan, key=lambda q: max(abs(a - b) for a, b in zip(p["rect"], q["rect"])))
        assert max(abs(a - b) for a, b in zip(p["rect"], q["rect"])) <= 0.3 and p["tur"] == q["tur"], p
        kalan.remove(q)
    assert not kalan
    assert (ym["kose"], ym["kanat"], ym["kanat_yayi"]) == (len(em["koseler"]), len(em["kanatlar"]), len(em["kanat_yaylari"]))
    eh = [(H_TURU[(h["cins"], h["ad"])], h["xy"]) for h in eski["h_plani_s3"]]
    for k in cevap["ayrinti"]["h_plani"]["konumlar"]:
        q = min(eh, key=lambda q: abs(q[1][0] - k["xy"][0]) + abs(q[1][1] - k["xy"][1]))
        assert q[0] == k["tur"] and max(abs(q[1][0] - k["xy"][0]), abs(q[1][1] - k["xy"][1])) <= 0.5, k
        eh.remove(q)
    assert not eh


def test_cevap_pr28_katmaniyla_ayni(cevap):
    pr28 = _oku(MOTOR_VERI / "PK01_pafta_katmani.json")
    for a in ("dis", "h_standart", "uclu_dis", "uclu_standart"):
        assert cevap["h_plani"][a]["adet"] == pr28["h_plani"][a]["adet"], a
    assert (cevap["makas_bas"]["adet"], cevap["makas_orta"]["adet"]) == (pr28["makas_bas"]["adet"], pr28["makas_orta"]["adet"])
    assert cevap["ayrinti"]["montaj"]["pano"] == {"adet": 50, "std": 29, "ozel": 21, "dis": 30, "ic": 20}


def test_liste_ureteci_cevabi_okur(cevap):
    """PR #28 katmanının H ve makas anahtarları bu cevapla değişince listenin pafta sütunu aynı kalır, başka hiçbir şey değişmez."""
    pr28 = _oku(MOTOR_VERI / "PK01_pafta_katmani.json")
    yeni = copy.deepcopy(pr28) | {k: cevap[k] for k in ("h_plani", "makas_bas", "makas_orta")} | {"ayrinti": cevap["ayrinti"]}
    N = PL.model_motor(_oku(MOTOR_VERI / "PK01.json"))
    a, b = PL.liste(copy.deepcopy(N), None, pr28), PL.liste(copy.deepcopy(N), None, yeni)
    ayni = lambda L: [(s["grup"], s["kalem"], s["olcu"], s["adet"], s["pafta"], s["aday"]) for s in L["satirlar"]]
    assert ayni(a) == ayni(b)
    okunan = {s["kalem"]: s["pafta"] for s in b["satirlar"] if s["pafta"] is not None}
    assert okunan["H 100 (dış pano eki)"] == 19 and sum(1 for s in b["satirlar"] if s["pafta_notu"].startswith("makas planı MK")) == 2


@pytest.fixture(scope="module")
def pk01_ifc(tmp_path_factory):
    from motor import ifc_uret
    yol = tmp_path_factory.mktemp("ifc") / "PK01.ifc"
    assert ifc_uret.uret(_oku(MOTOR_VERI / "PK01.json"), yol)["sema_hatasi"] == 0
    return yol


def test_kiyas_bugunku_ifc(pk01_ifc, cevap, proje):
    k = KY.kiyasla(pk01_ifc, cevap, proje)
    sonuc = {s["anahtar"]: (s["paftadan"], s["modelden"], s["sonuc"]) for s in k["satirlar"]}
    assert sonuc["ayrinti.montaj.pano.adet"] == (50, 50, "geçer")
    assert (sonuc["ayrinti.montaj.pano.dis"], sonuc["ayrinti.montaj.pano.ic"]) == ((30, 30, "geçer"), (20, 20, "geçer"))
    assert [sonuc[f"h_plani.{a}"] for a in ("dis", "h_standart", "uclu_dis", "uclu_standart")] == \
        [(19, 19, "geçer"), (10, 10, "geçer"), (5, 5, "geçer"), (4, 4, "geçer")]
    assert (sonuc["makas_bas"], sonuc["makas_orta"]) == ((2, 2, "geçer"), (7, 7, "geçer"))
    assert sonuc["ayrinti.h_plani.turler.dubelli_kulakli"] == (12, None, "modelde yok")
    assert k["kapi_1"] == "geçer"
    assert "Metraj kapısı: referans yok, koşulmadı; Patron kabulü kapının yerine geçmez." in KY.md(k)


def test_kiyas_kapi_farki_yakalar(pk01_ifc, cevap, proje):
    bozuk = copy.deepcopy(cevap)
    bozuk["h_plani"]["dis"]["adet"] = 18
    k = KY.kiyasla(pk01_ifc, bozuk, proje)
    s = next(s for s in k["satirlar"] if s["anahtar"] == "h_plani.dis")
    assert (s["fark"], s["sonuc"], k["kapi_1"]) == (1, "geçmez", "geçmez")


def test_kiyas_kart_sozlesmesi(tmp_path, cevap, proje):
    """Kart modeli parçaya `PortatifEv_Parca.PaftaAnahtari` yazarsa o anahtar yalnız bu yoldan sayılır (eşleme kullanılmaz)."""
    import ifcopenshell
    import ifcopenshell.api
    f = ifcopenshell.file(schema="IFC4")
    ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="sınama")
    for i in range(12):
        m = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcMember", name=f"H_PANO_EKI_DIS_{i:03d}")
        ps = ifcopenshell.api.run("pset.add_pset", f, product=m, name="PortatifEv_Parca")
        ifcopenshell.api.run("pset.edit_pset", f, pset=ps, properties={"PaftaAnahtari": "ayrinti.h_plani.turler.dubelli_kulakli"})
    for i in range(7):
        ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcMember", name=f"H_PANO_EKI_DIS_{100 + i:03d}")
    yol = tmp_path / "kart.ifc"
    f.write(str(yol))
    sonuc = {s["anahtar"]: s for s in KY.kiyasla(yol, cevap, proje)["satirlar"]}
    assert (sonuc["ayrinti.h_plani.turler.dubelli_kulakli"]["modelden"], sonuc["ayrinti.h_plani.turler.dubelli_kulakli"]["sonuc"]) == (12, "geçer")
    assert sonuc["ayrinti.h_plani.turler.dubelli_kulakli"]["sayim_yolu"] == "PortatifEv_Parca.PaftaAnahtari"
    assert sonuc["h_plani.dis"]["modelden"] == 19                    # sözleşmesi olmayan anahtar eşlemeyle sayılır


def _pafta() -> Path | None:
    d = os.environ.get("PORTMAN_PAFTA_DIZINI")
    p = Path(d) / "PK01.pdf" if d else None
    return p if p and p.exists() and PO.sha256(p) == _oku(PROJE)["pafta_sha256"] else None


@pytest.mark.skipif(_pafta() is None, reason="PK-01 paftası yok (PORTMAN_PAFTA_DIZINI/PK01.pdf, SHA'sı proje ayarındaki)")
def test_okuyucu_cevabi_yeniden_uretir(cevap, proje):
    assert json.loads(json.dumps(PO.oku(_pafta(), proje), ensure_ascii=False)) == cevap
