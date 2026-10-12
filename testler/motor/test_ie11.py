"""İE-11 · Pano motorunun genişletilmesi — anahtarlı davranışlar ve PK-01 kabul sayıları.

Eski İş Emri'nin bayt bayt aynı kaldığını `testler/referans/dogrula.py` (altın DXF/PDF izleri) söyler; burada yeni anahtarların davranışı
ve PK-01'in paftadan sayılan değerleri sınanır (`deneme/2026-10-13_pk_01/PK01_okuma.md`).
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

PK01 = KOK / "deneme" / "2026-10-13_pk_01" / "tanim" / "PK01.json"
P6001 = KOK / "is_emri" / "P6001_2plus1_6x6.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _pano_izi(plan) -> list:
    return sorted((d.tur, d.yon, round(d.c, 3), round(p.a0, 3), round(p.a1, 3), p.acilim.tur if p.acilim else "") for d in plan.duvarlar for p in d.panolar)


def test_eski_is_emri_yeni_anahtar_yok():
    ie = _oku(P6001)
    assert G.yeni_anahtar_var(ie) is False
    G.kur(ie)
    assert G._AKS == {"x": None, "y": None}, "anahtarsız İş Emri'nde aks tablosu kurulmamalı (eski kod yolu)"


def test_pk01_kurulum_paftayla():
    ie = _oku(PK01)
    assert G.yeni_anahtar_var(ie)
    plan = G.kur(json.loads(json.dumps(ie)))
    assert (plan.W, plan.H) == (600.0, 1000.0)
    dis = [d for d in plan.duvarlar if d.tur == "dis"]; ic = [d for d in plan.duvarlar if d.tur == "ic"]
    assert sum(len(d.panolar) for d in dis) == 28          # paftanın H sayımından: dış ekler 19 + dış üçlü 5 + 4 köşe → 28 pano
    assert sum(len(d.panolar) for d in ic) == 20
    assert len(plan.koseler) == 7
    assert sum(1 for h in plan.h_baglantilar if h.tur == "ic") == 4
    assert sum(1 for h in plan.h_baglantilar if h.tur == "dis") == 5   # paftada 2 kulaklı + 3 dübelli
    ac = Counter(p.acilim.tur for p in plan.panolar if p.acilim)
    assert ac == {"pencere": 6, "ic_kapi": 5, "dis_kapi": 1}
    dis_boy = {round(p.boy, 2) for d in dis for p in d.panolar}
    assert {37.0, 62.75, 78.0, 83.5, 111.5, 125.5} <= dis_boy             # paftadaki özel boylar
    ic_boy = {round(p.boy, 2) for d in ic for p in d.panolar}
    assert {32.0, 62.75, 120.5, 122.5, 125.5} <= ic_boy
    # ek aks 795 (arkadan) → gerçek çerçevede 205: hol/salon ön duvarı
    assert any(d.yon == "x" and abs(d.c - 205.0) < 1e-6 for d in dis)
    # kesilmiş panolar önde: sol dış duvarın ön ucu 111,5
    sol = next(d for d in dis if d.yon == "y" and abs(d.c - 5.0) < 1e-6)
    assert abs(sol.panolar[0].boy - 111.5) < 1e-6
    # veranda sol duvarı: ızgara hizalı 111,5 + 83,5
    ver = next(d for d in dis if d.yon == "y" and abs(d.c - 266.0) < 1e-6)
    assert [round(p.boy, 2) for p in ver.panolar] == [111.5, 83.5]
    # mahal alanları pafta etiketleriyle ±0,2 m²
    pafta = {"YATAK ODASI 1": 7.5, "BANYO": 4.4, "YATAK ODASI 2": 7.3, "HOL": 6.3, "MUTFAK": 14.9, "SALON": 8.1, "VERANDA": 6.6}
    for ad, m2 in pafta.items():
        assert abs(plan.mahaller[ad].alan_m2 - m2) <= 0.2, (ad, plan.mahaller[ad].alan_m2)
    # alıcıya ait dış kapı işaretli
    assert [p.acilim.dograma for p in plan.panolar if p.acilim and p.acilim.tur == "dis_kapi"] == ["alıcıya ait"]


def test_pk01_uret_dogrulama(tmp_path):
    from motor import dxf_out
    m = dxf_out.uret(_oku(PK01), tmp_path, pdf_hatada=True)
    assert m["validation_passed"] is True and m["pdf"] is not None
    bom = json.loads((tmp_path / "bom.json").read_text(encoding="utf-8"))["kalemler"]
    k03 = [r for r in bom if r["kod"] == "K03"]                       # doğrama satırı; "Dış kapılı özel pano" (D07) işaretlenmez
    assert len(k03) == 1 and k03[0].get("alici") is True and "Alıcıya ait" in k03[0]["not"]
    assert not any(r.get("alici") for r in bom if r["kod"] != "K03"), "alıcıya ait işareti yalnız doğrama satırında olmalı"
    assert any(r["malzeme"].startswith("Üçlü H bağlantı dış") and r["adet"] == 5 for r in bom)


def test_ayna_p6001_ayni_gecometri():
    """dizilim arka-sol: y arkadan sayılan P6001, öndekiyle aynı geometriyi vermeli (ayna iki kez)."""
    ie = _oku(P6001)
    ref = G.kur(json.loads(json.dumps(ie)))
    ny = float(ie["yapi"]["grid"]["y_pano"])
    ayna = json.loads(json.dumps(ie))
    ayna["yapi"]["dizilim"] = {"baslangic": "arka-sol"}
    for m in ayna["mahaller"]:
        m["konum_pano"] = [[x0, ny - y1, x1, ny - y0] for (x0, y0, x1, y1) in m["konum_pano"]]
    for a in ayna["acikliklar"]:
        if "pano" in a and a.get("duvar") in ("sol", "sag"):       # düşey duvarda pano sırası arkadan sayılır; yer karşılaştırılmıyor
            a.pop("pano")
    plan = G.kur(ayna)
    assert (plan.W, plan.H) == (ref.W, ref.H)
    assert len(plan.panolar) == len(ref.panolar) and len(plan.koseler) == len(ref.koseler) and len(plan.h_baglantilar) == len(ref.h_baglantilar)
    assert sorted(round(k.rect[i], 3) for k in plan.koseler for i in range(4)) == sorted(round(k.rect[i], 3) for k in ref.koseler for i in range(4))
    for ad in ref.mahaller:
        assert abs(plan.mahaller[ad].alan_m2 - ref.mahaller[ad].alan_m2) < 1e-6
        assert plan.mahaller[ad].poly.symmetric_difference(ref.mahaller[ad].poly).area < 1e-6
    # panolar: her duvarda pano sayısı, tam modül (125,5) sayısı ve toplam boy aynı. Tek tek boylar ve yerler karşılaştırılmaz:
    # "koşu başından" dizilim arka-solda koşunun öteki ucundan başlar; 125,5'in katı olmayan koşuda artık parça karşı uca düşer
    # ve ucun birleşim payı (dış T_DIS/2 = 5 ↔ iç T_IC/2 = 3) farklı olduğu için iki uç parça 2 cm yer değiştirir
    # (örn. P6001 iç duvar 7: 122,5 + 125,5 + 57,75 ↔ 120,5 + 125,5 + 59,75). Bu beklenen davranıştır (İE-11, D-10: pafta arkadan dizer).
    ozet = lambda p: sorted((d.tur, d.yon, round(d.c, 3), len(d.panolar), sum(1 for pn in d.panolar if abs(pn.boy - G.MOD) < 1e-6),
                             round(sum(pn.boy for pn in d.panolar), 3)) for d in p.duvarlar)
    assert ozet(plan) == ozet(ref)
    assert Counter(pn.acilim.tur for pn in plan.panolar if pn.acilim) == Counter(pn.acilim.tur for pn in ref.panolar if pn.acilim)


def test_konum_cm_aks_disi_hata():
    ie = _oku(PK01)
    ie["mahaller"][3]["konum_cm"] = [[261, 256, 386.5, 800]]   # 800 aks değil
    with pytest.raises(G.IsEmriHatasi):
        G.kur(ie)


def test_dizilim_bilinmeyen_hata():
    ie = _oku(PK01)
    ie["yapi"]["dizilim"] = {"baslangic": "sag-on"}
    with pytest.raises(G.IsEmriHatasi):
        G.kur(ie)
