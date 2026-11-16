"""BK-46 · 3D modelde (IFC, `motor/ifc_uret.py`) çatı hataları (havuz denetimi, 16 Kasım 2026).

Havuz denetimi üç hata buldu: kubbeli evde 3D kurulmuyordu (64, 64, 80 m²); kırma çatı 3D'de beşik çiziliyordu (140, 142, 77, 78 m²);
girintili gövde + çapraz cumbada 3D kurulmuyordu (82, 91, 45, 46, 40 m²). Ayrıca makaslar y'yi geçince (`_cati_y`) makas yeri saçak
duvarının pano eklerinden düzen denetimsiz alınıyordu (BK-12 PR-R'nin x yönündeki denetimi y'de yoktu).

Kural: makas sayısı ve yeri yükleme listesinden (D-28 tek kaynak); listede yer yoksa 3D makası uydurmaz, uyarı yazar (K16).
- Kubbe (D-54): çizimdeki kubbenin aynısı; üç pano, üç yüzlü çatı, üç makas (listede "Kubbe makası" 3).
- İki uçlu kırma (İE-33): ana, kısa ve çapraz makaslar listenin `kirma_makas` planında; sayı ve rol listeyle aynı.
- Tek uçlu kırma (İE-29): kalkan dolgusu var; makaslar AP-27 paftasının makas planında (listede yalnız sayılar), sayı ve rol listeyle aynı.
- Çıkıntılı çapraz cumba: ana çatı + cumba, parça başına makas sayısı listeyle aynı. İki cumbalı evde (liste bugün yazılmıyor) 3D kurulur;
  taşan verandanın cumbasında makas kuralı listede yok, uyarı.
- Makaslar y'yi geçince: sayı her evde listeyle aynı; ekler düzensizse eşit aralık ve uyarı (`_cati_y`, `PortatifEv_Uyari`).

Geometri hakemi (16 Kasım 2026) bulgularından: uç açıklık 125,5 + dış duvar ÷ 2'ye kadar düzenli sayılır (PK-02); çıkıntının içindeki
cumba makası cumbanın yan duvarlarına oturur, ana çatının üstünde değil (91 m²); liste yazılmayan evde uyarı özette ve IFC'de; kubbe
makası TRUSS değil (kart modeli makasları TRUSS'tan sayar); kırma makasında 0,5 cm'den kısa üye yok.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret as I, prefabrik_liste as PL  # noqa: E402

EVLER = KOK / "is_emri" / "adaylar"


def _ie(kod: str) -> dict:
    return json.loads((EVLER / f"{kod}.json").read_text(encoding="utf-8"))


def _uret(kod: str, klasor: Path) -> tuple[dict, ifcopenshell.file]:
    yol = klasor / f"{kod}.ifc"
    with contextlib.redirect_stdout(io.StringIO()):
        oz = I.uret(_ie(kod), yol)
    return oz, ifcopenshell.open(str(yol))


def _liste_makaslari(kod: str) -> list[tuple[str, int]]:
    """Yükleme listesinin makas satırları (1005 grubu; "makas arası" çatı paneli makas değildir): [(kalem, adet)]."""
    L = PL.is_emrinden(copy.deepcopy(_ie(kod)))
    return [(s["kalem"], int(s["adet"])) for s in L["satirlar"]
            if s.get("grup") == "1005" and "makas" in s["kalem"].lower() and "makas arası" not in s["kalem"].lower()]


def _parca(kalem: str) -> str:
    return kalem.split(" · ")[-1].strip().lower() if " · " in kalem else "?"


def _ana_cati(f: ifcopenshell.file):
    return next(r for r in f.by_type("IfcRoof") if r.Name == "ANA_CATI")


def _profil_boyu(m) -> float:
    """Düşey düzlemdeki çubuğun boyu (m): kesitin s ekseni boyunca uzunluğu (`IfcUretici._dikey_prizma`)."""
    it = m.Representation.Representations[0].Items[0]
    s = [p[0] for p in it.SweptArea.OuterCurve.Points.CoordList]
    return max(s) - min(s)


# ---------------------------------------------------------------- kubbe

@pytest.mark.parametrize("kod", ["PA09", "PA16", "PA20"])
def test_kubbe_kurulur(kod, tmp_path):
    """Kubbeli evde 3D kurulur (önce KeyError 'kubbe'); her kubbede üç pano, üç yüz, üç makas; listedeki "Kubbe makası" kadar."""
    oz, f = _uret(kod, tmp_path)
    n_kubbe = len(_ie(kod)["kubbeler"])
    assert oz["kubbe"] == [{"mahal": k["mahal"], "makas": 3, "yuz": 3, "pano": 3} for k in _ie(kod)["kubbeler"]]
    roofs = [r for r in f.by_type("IfcRoof") if r.Name.startswith("KUBBE_CATISI_")]
    assert len(roofs) == n_kubbe
    makas = [a for a in f.by_type("IfcElementAssembly") if a.Name.startswith("MAKAS_KUBBE_")]
    assert len(makas) == 3 * n_kubbe
    assert {(a.PredefinedType, a.ObjectType) for a in makas} == {("USERDEFINED", "KUBBE_MAKASI")}
    assert len([a for a in f.by_type("IfcElementAssembly") if a.PredefinedType == "TRUSS"]) == oz["cati"]["makas"]
    liste = dict(_liste_makaslari(kod))
    assert liste.get("Kubbe makası") == sum(k["makas"] for k in oz["kubbe"])


# ---------------------------------------------------------------- kırma

@pytest.mark.parametrize("kod", ["PA08", "PA33"])
def test_iki_uclu_kirma(kod, tmp_path):
    """İki uçlu kırma 3D'de kırma (HIP_ROOF; önce beşik); makaslar listenin makas planında: sayı ve rol listeyle aynı (29)."""
    oz, f = _uret(kod, tmp_path)
    assert _ana_cati(f).PredefinedType == "HIP_ROOF"
    c = oz["cati"]
    assert c["tip"] == "kirma" and "uyari" not in c
    liste = _liste_makaslari(kod)
    rol_liste = Counter()
    for kalem, adet in liste:
        assert _parca(kalem) == "ana çatı"
        rol = "ana" if kalem.startswith("Makas (ana") else "kisa" if kalem.startswith("Makas (kısa") else \
              "capraz" if kalem.startswith("Makas (çapraz") else kalem
        rol_liste[rol] += adet
    assert Counter(m["rol"] for m in c["makaslar"]) == rol_liste
    assert c["makas"] == sum(rol_liste.values()) == 29
    makas = [a for a in f.by_type("IfcElementAssembly") if a.PredefinedType == "TRUSS" and a.Name.startswith("MAKAS_")]
    assert len(makas) == 29
    # yer listenin makas planından: ana makaslar `ana_x_cm`'de, kısa makaslar her uçta `kisa_y_cm`'de
    ie = _ie(kod)
    km = PL._iki_uclu_kirma_catilari(I.G.kur(copy.deepcopy(ie)), ie)[0][0]["kirma_makas"]
    assert [m["konum_cm"] for m in c["makaslar"] if m["rol"] == "ana"] == [round(x, 2) for x in km["ana_x_cm"]]
    assert [m["konum_cm"] for m in c["makaslar"] if m["rol"] == "kisa"] == [round(y, 2) for u in km["uclar"] for y in u["kisa_y_cm"]]
    # 0,5 cm'den kısa üst başlık üyesi yok (düzlemlerin eşitlendiği yerler birleştirildi)
    ust = [m for m in f.by_type("IfcMember") if m.Name.startswith("MAKAS_") and re.search(r"_UST_\d+$", m.Name)]
    assert ust and min(_profil_boyu(m) for m in ust) >= 0.005


@pytest.mark.parametrize("kod, ana", [("PA24", [116.5, 242.0, 367.5, 500.0, 618.5, 744.0, 869.5]),
                                      ("PA34", [130.5, 256.0, 381.5, 507.0, 632.5, 758.0, 883.5])])
def test_tek_uclu_kirma(kod, ana, tmp_path):
    """Tek uçlu kırma 3D'de kırma, kalkanı dolgulu; makaslar AP-27 paftasının makas planından çıkan kuralla (77 m²'de paftadaki yerler;
    güney bant Lokman'ın kartıyla 125,5 arayla, 16 Kasım 2026 09:00). 78 m²'nin paftası yok: beklenen yerler kuralın sonucu (kalkan
    duvarının ekleri, 444,25 atlanır). Sayı ve rol listeyle aynı (7 + 14 + 2 + 2 = 25)."""
    oz, f = _uret(kod, tmp_path)
    roof = _ana_cati(f)
    assert roof.PredefinedType == "HIP_ROOF"
    assert any(p.Name.startswith("ALIN_") for p in f.by_type("IfcPlate"))
    c = oz["cati"]
    assert "uyari" not in c and "PortatifEv_Uyari" not in ue.get_psets(roof)
    rol_liste = Counter()
    for kalem, adet in _liste_makaslari(kod):
        assert _parca(kalem) == "ana çatı"
        rol = {"Makas (ana": "ana", "Makas (kısa": "kisa", "Makas (çapraz": "capraz", "Makas (köşe kısa": "kose_kisa"}[kalem.split(",")[0].split(")")[0]]
        rol_liste[rol] += adet
    assert Counter(m["rol"] for m in c["makaslar"]) == rol_liste == Counter(ana=7, kisa=14, capraz=2, kose_kisa=2)
    assert len([a for a in f.by_type("IfcElementAssembly") if a.PredefinedType == "TRUSS"]) == 25
    assert [m["konum_cm"] for m in c["makaslar"] if m["rol"] == "ana"] == ana        # kalkan duvarının pano ekleri (77 m²'de 430,25 atlanır)
    bant = [5.0, 135.5, 261.0, 386.5, 512.0, 637.5, 700.25]                       # kalkan duvarında, 125,5 arayla, köşeden önceki ek
    assert [m["konum_cm"] for m in c["makaslar"] if m["rol"] == "kisa"] == bant + bant
    # çapraz makas ilk ana makasa kırma hattında varır (45°: 773 − bant derinliği); köşe kısa son kısa makasın kırma hattındaki ucunda
    gy1 = {"PA24": 1000.0, "PA34": 1014.0}[kod]
    assert [m["konum_cm"] for m in c["makaslar"] if m["rol"] == "capraz"] == [773.0 - ana[0], 773.0 - (gy1 - ana[-1])]
    assert [m["konum_cm"] for m in c["makaslar"] if m["rol"] == "kose_kisa"] == [773.0 - 700.25, gy1 - (773.0 - 700.25)]
    ust = [m for m in f.by_type("IfcMember") if m.Name.startswith("MAKAS_") and re.search(r"_UST_\d+$", m.Name)]
    assert min(_profil_boyu(m) for m in ust) >= 0.005


def test_tek_uclu_ana_yerleri_iki_yonden_ayni():
    """Ana makas seçimi tarama yönüne bağlı değil (geometri hakemi, 16 Kasım: aynada 569,75 seçiliyordu, aralık 188,25)."""
    pa24 = [5.0, 116.5, 242.0, 367.5, 430.25, 500.0, 618.5, 744.0, 869.5, 995.0]
    assert I.tek_uclu_ana_yerleri(pa24, 5.0, 995.0, 5.0) == [116.5, 242.0, 367.5, 500.0, 618.5, 744.0, 869.5]
    ayna = sorted(1000.0 - v for v in pa24)
    assert I.tek_uclu_ana_yerleri(ayna, 5.0, 995.0, 5.0) == [130.5, 256.0, 381.5, 500.0, 632.5, 758.0, 883.5]
    with pytest.raises(ValueError, match="iki ana makasın arası"):
        I.tek_uclu_ana_yerleri([5.0, 300.0, 600.0, 995.0], 5.0, 995.0, 5.0)


def test_tek_uclu_kirma_sayi_tutmazsa_makas_yok(tmp_path, monkeypatch):
    """Listedeki sayı kuralın verdiğiyle tutmazsa 3D makası uydurmaz: makas yok, uyarı özette ve IFC'de (K16)."""
    asil = PL._tek_uclu_kirma_catilari

    def sahte(plan, ie):
        out, t = asil(plan, ie)
        out[0]["kirma_makas"] = {**out[0]["kirma_makas"], "ana": 8}
        return out, t
    monkeypatch.setattr(PL, "_tek_uclu_kirma_catilari", sahte)
    oz, f = _uret("PA24", tmp_path)
    c = oz["cati"]
    assert c["makas"] == 0 and c["makaslar"] == []
    assert any("7 ana makas, listede 8" in u for u in c["uyari"])
    assert "listede 8" in ue.get_psets(_ana_cati(f))["PortatifEv_Uyari"]["MakasYeri"]
    assert not [a for a in f.by_type("IfcElementAssembly") if a.PredefinedType == "TRUSS"]


# ---------------------------------------------------------------- girintili gövde + çapraz cumba

@pytest.mark.parametrize("kod, beklenen, cikintida", [("PA05", {"ana çatı": 9, "cumba": 3}, 1), ("PA17", {"ana çatı": 8, "cumba": 4}, 2)])
def test_cikintili_capraz_cumba(kod, beklenen, cikintida, tmp_path):
    """Çıkıntılı çapraz cumbada 3D kurulur (önce hata); parça başına makas sayısı listeyle aynı."""
    oz, f = _uret(kod, tmp_path)
    c = oz["cati"]
    uc = Counter(m["parca"] for m in c["makaslar"])
    liste = Counter()
    for kalem, adet in _liste_makaslari(kod):
        liste[_parca(kalem)] += adet
    assert dict(uc) == dict(liste) == beklenen
    cumba = [m for m in c["makaslar"] if m["parca"] == "cumba"]
    assert [m["rol"] for m in cumba] == ["bas"] + ["orta"] * (len(cumba) - 1)
    farklar = [round(abs(b["konum_cm"] - a["konum_cm"]), 2) for a, b in zip(cumba, cumba[1:])]
    assert set(farklar) == {125.5}                                        # D-47: dış kalkandan 125,5 arayla
    # çıkıntının içindeki makaslar cumbanın yan duvarlarında; ötekiler ana çatının üstünde (91 m²'de çıkıntı 220)
    ie = _ie(kod)
    T = I._cikintili_cumba_tanimi(I.G.kur(copy.deepcopy(ie)), ie)
    q = next(p for p in T["parcalar"] if p["ad"] == "cumba")
    assert [bool(m.get("ana_ustunde")) for m in q["makaslar"]] == [False] * cikintida + [True] * (len(q["makaslar"]) - cikintida)


@pytest.mark.parametrize("kod", ["PA27", "PA28", "PA29"])
def test_iki_cumba(kod, tmp_path):
    """İki cumbalı evde (biri taşan verandanın cumbası) 3D kurulur; gövdenin cumbasında 3 makas, verandanın cumbasında makas yok, uyarı."""
    oz, f = _uret(kod, tmp_path)
    c = oz["cati"]
    uc = Counter(m["parca"] for m in c["makaslar"])
    assert uc["cumba"] == 3 and uc["ana çatı"] == 7
    assert any("SUNDURMA verandasının cumbasında makas kuralı listede yok" in u for u in c["uyari"])
    assert any("yükleme listesi yazılmıyor" in u for u in c["uyari"])
    assert "yükleme listesi yazılmıyor" in ue.get_psets(_ana_cati(f))["PortatifEv_Uyari"]["MakasYeri"]
    with pytest.raises(PL.ListeYazilmaz):                                 # liste bugün yazılmıyor (liste sohbetinin işi)
        _liste_makaslari(kod)


# ---------------------------------------------------------------- makaslar y'yi geçince

@pytest.mark.parametrize("kod, uyarili", [("PA10", False), ("PA12", True), ("PA22", True), ("PA25", True), ("PA30", False), ("PA38", False)])
def test_makas_y_sayisi_listeyle(kod, uyarili, tmp_path):
    """Makaslar y'yi geçince sayı listeyle aynı; saçak duvarının ekleri düzensizse eşit aralık ve uyarı (özet ve IFC)."""
    oz, f = _uret(kod, tmp_path)
    c = oz["cati"]
    assert c["makas_ekseni"] == "y"
    assert c["makas"] == sum(a for _, a in _liste_makaslari(kod)) == len(c["makas_x_cm"])
    uyari = ue.get_psets(_ana_cati(f)).get("PortatifEv_Uyari", {}).get("MakasYeri")
    if uyarili:
        assert c["uyari"] and uyari
    else:
        assert "uyari" not in c and uyari is None
        araliklar = [round(b - a, 2) for a, b in zip(c["makas_x_cm"], c["makas_x_cm"][1:])]
        assert max(araliklar[1:-1] or [0]) <= 125.5


def test_makas_y_uc_acikligi_pk02(tmp_path):
    """Uç açıklık 130,5 (125,5 + dış duvar ÷ 2): saçak duvarının pano eki, düzenli sayılır, uyarı yok (geometri hakemi; PK-02, 739,2 açıklık)."""
    ie = json.loads((KOK / "testler" / "kor" / "projeler" / "PK02" / "is_emri.json").read_text(encoding="utf-8"))
    yol = tmp_path / "PK02.ifc"
    with contextlib.redirect_stdout(io.StringIO()):
        oz = I.uret(ie, yol)
    c = oz["cati"]
    assert c["makas_ekseni"] == "y" and "uyari" not in c
    assert c["makas_x_cm"] == [5.0, 135.5, 261.0, 386.5, 512.0, 637.5, 768.0]
