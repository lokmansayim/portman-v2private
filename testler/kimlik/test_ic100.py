"""İE-18 R1 ek 4 · İç duvarı 100'lük ev (TK-02 = TK-01 + iç 100; BK-18): kimlik kartları (CIO planı, 29 Ekim 2026).

- Kart modeli: D kartının parçaları birden çok pano tipinden gelebilir (iç duvarı 100'lük evde `PE-DIS-100` ve `PE-IC-100`), katmanları ve
  `PortatifEv_PanoTipi` seti (`id` hariç) aynıysa (`_duvar_turu_tasi`); içerik farklıysa kart iki ürünü taşıyamaz, model düşer.
- Evin iç duvar kalınlığı (`ic_duvar_cm`) bugünkü IFC'deki iç panolardan; eşlemenin `ic_duvar_cm` koşulu H-03'ü (iç 60'lık) ve H-07'yi
  (iç 100'lük) ayırır.
- Yeni kartlar (sürüm 5): D-06, D-07, H-07…H-10. Adları ve liste satırları liste üretecinin iç duvar 100'lükken yazdığı satırlar
  (`motor/prefabrik_liste.py`; TK-01'in İş Emri'nin modeli iç panolar 100 mm'ye çekilerek); her biri 60'lık karşılığının 60 → 100'ü.
- Kod kilidi: ilk 57 satır donar (K1–K3b'nin 51'i + bu altı), yeni kod sona eklenir.

TK-02'nin uçtan uca testi (BK-18 main'e girdikten sonra): kart adetleri listeyle, "kural yok" TK-01'inkiyle aynı, paket ve rehber
(iç duvar üstü omegası OM-02, sırtı kuraldan; baş makas omegası saçaktan saçağa; D-32). R1 ek 5 (D-32 ek, Lokman 30 Ekim 07:04): iç duvar
üstü omegası 100'lük duvar omegasıdır; OM-02'nin adı ve satırı "100'lük duvar omegası", parçası 250'lik (kartlar sürüm 6).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import kart_model as KM  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "kimlik" / "veri"
YENI = ("D-06", "D-07", "H-07", "H-08", "H-09", "H-10")
KARSILIK = {"D-06": "I-02", "D-07": "I-03", "H-07": "H-03", "H-08": "H-04", "H-09": "H-05", "H-10": "H-06"}   # 60'lık karşılığı
KILIT_IC100 = "e2d260cdfaa3724599d418411000bd6d58fba0401225ef58949da128ef90a170"   # ilk 57 kod adlarıyla (K1–K3b 51 + bu altı)


def _yuz(s: str) -> str:
    """60'lık adın 100'lük karşılığı (Türkçe ek de değişir)."""
    return s.replace("60'lık", "100'lük").replace("60", "100")


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kartlar() -> dict:
    return {k["kod"]: k for k in _oku(KM.KARTLAR)["kartlar"]}


# ----------------------------------------------------------------------------- küçük IFC
def _dosya():
    f = KM._api("project.create_file", version="IFC4")
    KM._api("root.create_entity", f, ifc_class="IfcProject", name="deneme")
    return f


def _pano_tipi(f, ad: str, katmanlar: list, pt: dict):
    t = KM._api("root.create_entity", f, ifc_class="IfcWallType", name=ad)
    ls = KM._api("material.add_material_set", f, name=ad, set_type="IfcMaterialLayerSet")
    for m, k in katmanlar:
        KM._api("material.add_layer", f, layer_set=ls, material=KM._api("material.add_material", f, name=m)).LayerThickness = k
    KM._api("material.assign_material", f, products=[t], type="IfcMaterialLayerSet", material=ls)
    KM._api("pset.edit_pset", f, pset=KM._api("pset.add_pset", f, product=t, name="PortatifEv_PanoTipi"), properties=pt)
    return t


def _duvar(f, ad: str, tip=None, kalinlik_cm: float | None = None, dis: bool | None = None):
    w = KM._api("root.create_entity", f, ifc_class="IfcWall", name=ad)
    if tip is not None:
        KM._api("type.assign_type", f, related_objects=[w], relating_type=tip)
    if dis is not None:
        KM._api("pset.edit_pset", f, pset=KM._api("pset.add_pset", f, product=w, name="Pset_WallCommon"), properties={"IsExternal": dis})
    if kalinlik_cm is not None:
        KM._api("pset.edit_pset", f, pset=KM._api("pset.add_pset", f, product=w, name="PortatifEv_Pano"), properties={"Kalinlik_cm": kalinlik_cm})
    return w


SANDVIC = [("Sac 0,5", 0.005), ("Poliüretan", 0.09), ("Sac 0,5", 0.005)]


def test_iki_tipten_ayni_icerik_tasinir():
    """`PE-DIS-100` ve `PE-IC-100` aynı katmanlı: kart adı sıradaki ilk tipin katmanlarını ve setini alır (`id` hariç)."""
    f = _dosya()
    dis = _pano_tipi(f, "PE-DIS-100", SANDVIC, {"id": "PE-DIS-100", "Anma_mm": 100})
    ic = _pano_tipi(f, "PE-IC-100", SANDVIC, {"id": "PE-IC-100", "Anma_mm": 100})
    kart = KM._api("root.create_entity", f, ifc_class="IfcWallType", name="100'lük yapıştırma dolu pano")
    kart.Tag = "D-01"
    duvarlar = [_duvar(f, "P1", ic), _duvar(f, "P2", dis), _duvar(f, "P3", ic)]
    oteki = _duvar(f, "P4", ic)                                    # başka kartın parçası (aynı eski tip): kullanımı değişmez
    once = {w.Name: (u.LayerSetDirection, u.DirectionSense, u.OffsetFromReferenceLine)
            for w in duvarlar for u in [ue.get_material(w, should_inherit=False)]}
    assert all(ue.get_material(w, should_inherit=False).is_a("IfcMaterialLayerSetUsage") for w in duvarlar + [oteki])
    KM._duvar_turu_tasi(f, kart, duvarlar)
    assert ue.get_material(kart) == ue.get_material(dis)
    assert ue.get_psets(kart)["PortatifEv_PanoTipi"] | {"id": None} == {"id": None, "Anma_mm": 100}
    # IFC4: her parçanın katman kullanımı kartın katman dizisini gösterir (geometri hakemi, 29 Ekim); yön ve kaçıklık aynı
    for w in duvarlar:
        u = ue.get_material(w, should_inherit=False)
        assert u.ForLayerSet == ue.get_material(kart) and (u.LayerSetDirection, u.DirectionSense, u.OffsetFromReferenceLine) == once[w.Name]
    assert ue.get_material(oteki, should_inherit=False).ForLayerSet == ue.get_material(ic)


def test_ortak_kullanim_duser():
    """Kartın dışındaki bir parçayla ortak katman kullanımı taşınmaz (bugünkü IFC'de her duvarın kendi kullanımı var)."""
    f = _dosya()
    dis = _pano_tipi(f, "PE-DIS-100", SANDVIC, {"id": "PE-DIS-100", "Anma_mm": 100})
    ic = _pano_tipi(f, "PE-IC-100", SANDVIC, {"id": "PE-IC-100", "Anma_mm": 100})
    a, b, c = _duvar(f, "P1", dis), _duvar(f, "P2", ic), _duvar(f, "P3", ic)
    u = ue.get_material(b, should_inherit=False)
    for r in [r for r in f.get_inverse(ue.get_material(c, should_inherit=False)) if r.is_a("IfcRelAssociatesMaterial")]:
        r.RelatingMaterial = u                                     # P2 ile P3 aynı kullanımı paylaşır
    kart = KM._api("root.create_entity", f, ifc_class="IfcWallType", name="kart")
    kart.Tag = "D-01"
    with pytest.raises(ValueError, match="P2 parçasının katman kullanımı bu kartın dışındaki parçalarla ortak"):
        KM._duvar_turu_tasi(f, kart, [a, b])


@pytest.mark.parametrize("fark", ["katman", "set"])
def test_iki_tipten_farkli_icerik_duser(fark):
    f = _dosya()
    a = _pano_tipi(f, "PE-DIS-100", SANDVIC, {"id": "PE-DIS-100", "Anma_mm": 100})
    b = _pano_tipi(f, "PE-IC-60", SANDVIC[:1] + [("Poliüretan", 0.05)] + SANDVIC[2:] if fark == "katman" else SANDVIC,
                   {"id": "PE-IC-60", "Anma_mm": 100 if fark == "katman" else 60})
    kart = KM._api("root.create_entity", f, ifc_class="IfcWallType", name="kart")
    kart.Tag = "D-01"
    with pytest.raises(ValueError, match=r"D-01: parçaları 2 ayrı pano tipinden geliyor \(PE-DIS-100, PE-IC-60\)"):
        KM._duvar_turu_tasi(f, kart, [_duvar(f, "P1", a), _duvar(f, "P2", b)])


def test_tipsiz_parca_duser():
    f = _dosya()
    kart = KM._api("root.create_entity", f, ifc_class="IfcWallType", name="kart")
    kart.Tag = "D-01"
    with pytest.raises(ValueError, match="0 ayrı pano tipinden"):
        KM._duvar_turu_tasi(f, kart, [_duvar(f, "P1")])


@pytest.mark.parametrize("ic, beklenen", [([], ""), ([6, 6], "6"), ([10], "10"), ([6, 10, 10], "6,10")])
def test_ic_duvar_cm(ic, beklenen):
    """İç panoların (`IsExternal` değil) kalınlıkları; dış duvar ve kalınlığı yazmayan pano sayılmaz."""
    f = _dosya()
    _duvar(f, "D1", kalinlik_cm=10, dis=True)
    _duvar(f, "X", dis=False)
    for i, k in enumerate(ic):
        _duvar(f, f"I{i}", kalinlik_cm=k, dis=False)
    assert KM.ic_duvar_cm(f) == beklenen


@pytest.mark.parametrize("ic, kart", [("6", "H-03"), ("10", "H-07")])
def test_ic_h_kalinliga_gore(kartlar, ic, kart):
    """İç pano eki H'ı (`H_PANO_EKI_IC_…`): evin iç duvarı 60'lıksa H-03, 100'lükse H-07; kalınlık yazmayan evde ikisi de eşleşmez."""
    f = _dosya()
    e = KM._api("root.create_entity", f, ifc_class="IfcMember", name="H_PANO_EKI_IC_000")
    uyan = {k for k in ("H-03", "H-07") for m in kartlar[k]["bugunku_ifc"] if KM._uyar(e, m, {"ic_duvar_cm": ic})}
    assert uyan == {kart}
    assert not any(KM._uyar(e, m, {"ic_duvar_cm": ""}) for k in ("H-03", "H-07") for m in kartlar[k]["bugunku_ifc"])
    assert not any(KM._uyar(e, m) for k in ("H-03", "H-07") for m in kartlar[k]["bugunku_ifc"])


# ----------------------------------------------------------------------------- kartlar listeden
def _liste_ic100() -> set[str]:
    """TK-01'in İş Emri'nin modeli, iç panolar 100 mm'ye çekilmiş; bir iç kapı panosu kapısız geçiş: liste üretecinin satır adları."""
    N = PL.model_motor(_oku(KOK / "testler" / "motor" / "veri" / "TK01.json"))
    ic = [p for p in N["panolar"] if p["duvar"] == "ic"]
    assert ic
    for p in ic:
        p["kal_mm"] = 100
    kapi = next(p for p in ic if p["aciklik"] and p["aciklik"]["tur"] == "ic_kapi")
    kapi["aciklik"] = dict(kapi["aciklik"], tur="gecis")
    return {s["kalem"] for s in PL.liste(N)["satirlar"]}


def test_yeni_kartlar_liste_satirlarindan(kartlar):
    """D-28 madde 1: kart liste satırını izler. Yeni kartın satırı iç duvar 100'lükken liste üretecinde var; adı ve satırı 60'lık
    karşılığınınki, 60 → 100; yeri (`bugunku_ifc`, pafta, sayım) karşılığınınkiyle aynı yapıda."""
    satir = _liste_ic100()
    assert "60'lık karkaslı + kasalı pano" not in satir and "H standart 60 (iç pano eki)" not in satir
    for k in YENI:
        y, e = kartlar[k], kartlar[KARSILIK[k]]
        assert y["liste"]["satirlar"] and set(y["liste"]["satirlar"]) <= satir, k
        assert y["liste"]["satirlar"] == [_yuz(s) for s in e["liste"]["satirlar"]], k
        assert y["ad"] == _yuz(e["ad"]) and y["liste"]["grup"] == e["liste"]["grup"], k
        assert (y["sayim"], y["birim"], y["pafta"]) == (e["sayim"], e["birim"], e["pafta"]), k
        assert y["kaynak"]["durum"] == "varsayim" and "BK-18" in y["kaynak"]["dayanak"], k
    assert {k for k, v in kartlar.items() if any("IC_KOSE_100x50" in json.dumps(m) for m in v.get("bugunku_ifc") or [])} == {"B-01"}
    assert {k for k, v in kartlar.items() for m in v.get("bugunku_ifc") or [] if "ic_duvar_cm" in m} == {"H-03", "H-07"}


def test_kod_kilidi_ic100(kartlar):
    """Bu işte eklenen altı kod kilitte; ilk 57 satır donmuştur, yeni kod sona eklenir."""
    kilit = _oku(VERI / "kart_kodlari.json")["kodlar"]
    ilk = dict(list(kilit.items())[:57])
    assert tuple(list(ilk)[51:]) == YENI
    assert all(kilit[k] == kartlar[k]["ad"] for k in YENI)
    assert hashlib.sha256(json.dumps(ilk, ensure_ascii=False, sort_keys=True).encode()).hexdigest() == KILIT_IC100
    assert _oku(KM.KARTLAR)["surum"] == "10"                              # R1 ek 5: OM-02'nin adı düzeltildi (D-32 ek); İE-15 K5: taşan veranda; K5b: KP-02, MA-03; K5b-2: H-11, AL-01, AL-02, IZ-01; BK-19: CK-01, CK-03, CK-04 "nerede"



def test_ic_duvar_kalinligi_tek_kaynak():
    """İç duvar kalınlığı ve satır adındaki yazısı liste üretecinin işlevlerinde (`ic_duvar_kalinligi_mm`, `kalinlik_adi`); rehber de
    bunlardan okur (geometri hakemi, 29 Ekim: kural rehberde kopyalanmaz). İç duvarsız evde kural kitabının `PE-IC-60`'ı."""
    N, K = PL.model_motor(_oku(KOK / "testler" / "motor" / "veri" / "TK01.json")), PL.kurallari_oku()
    assert (PL.ic_duvar_kalinligi_mm(N, K), PL.kalinlik_adi(PL.ic_duvar_kalinligi_mm(N, K))) == (60, "60'lık")
    for p in N["panolar"]:
        if p["duvar"] == "ic":
            p["kal_mm"] = 100
    assert (PL.ic_duvar_kalinligi_mm(N, K), PL.kalinlik_adi(100)) == (100, "100'lük")
    N["panolar"] = [p for p in N["panolar"] if p["duvar"] != "ic"]
    assert PL.ic_duvar_kalinligi_mm(N, K) == 60
    kaynak = (KOK / "araclar" / "paket" / "rehber" / "veri.py").read_text(encoding="utf-8")
    assert "LU.ic_duvar_kalinligi_mm(" in kaynak and "LU.kalinlik_adi(" in kaynak and ">= 100" not in kaynak


# ----------------------------------------------------------------------------- TK-02 uçtan uca (BK-18 main'de)
TK02 = KOK / "testler" / "motor" / "veri" / "TK02.json"
DUVAR100 = "100'lük duvar omegası"                                       # D-32 ek: 100'lük iç duvarın üstü bu satırda


def _kart_sayimi(ie: dict, klasor: Path, ad: str) -> dict:
    from motor import ifc_uret
    ifc_uret.uret(ie, klasor / f"{ad}.ifc")
    return KM.kart_modeli(klasor / f"{ad}.ifc", klasor / f"{ad}_model.ifc", ie["cati"]["tip"], is_emri=ie, plan=ifc_uret.hazirla(ie),
                          elektrik=True, kenar=True)


@pytest.fixture(scope="module")
def tk02(tmp_path_factory):
    ie = _oku(TK02)
    liste = Counter()
    for s in PL.is_emrinden(copy.deepcopy(ie))["satirlar"]:
        liste[s["kalem"]] += s["adet"]
    return ie, _kart_sayimi(ie, tmp_path_factory.mktemp("tk02"), "TK02"), liste


def test_tk02_kart_adetleri_listeyle(tk02, kartlar):
    """TK-02 (TK-01 + iç 100, asma tavan): parça başına sayılan kartın adedi listedeki satırının adedi; iki kartın paylaştığı satırda (dış H
    H-01/H-02, dış T H-08/H-09; dübelli & kulaklı ayrımı modelde) toplam. 60'lık iç kartlar 0. OM-02'nin parçaları "100'lük duvar omegası"
    satırının iki terimini verir: 100'lük iç duvarların üstü ve (İE-15 K5b-2, D-32) girişin nişine bakan dış duvar (`Duvar: dis`); kesim
    planının stoğu satırın adedi. Parçalar duvar omegasının boyuyla (250) bölünür, kesim planı da 250'lik (D-32 ek)."""
    _, say, liste = tk02
    adet = {k["kod"]: k for k in say["kartlar"]}
    for grup in (["D-01"], ["D-06"], ["H-01", "H-02"], ["H-07"], ["H-08", "H-09"], ["H-10"], ["B-01"]):
        assert sum(adet[k]["adet"] for k in grup) == sum(liste[s] for s in kartlar[grup[0]]["liste"]["satirlar"]) > 0, grup
    assert all(adet[k]["adet"] == 0 for k in ("I-01", "I-02", "I-03", "H-03", "H-04", "H-05", "H-06"))
    assert kartlar["OM-02"]["liste"]["satirlar"] == [DUVAR100]
    s = next(x for x in PL.is_emrinden(copy.deepcopy(_oku(TK02)))["satirlar"] if x["kalem"] == DUVAR100)
    terim = {ad.strip(): float(m.replace(",", ".")) for ad, m in re.findall(r"([^+÷]+?) ([\d,]+) m", s["formul"])}
    assert set(terim) == {"çatı kenarına gelmeyen dış duvarlar", "100'lük iç duvarlar"}
    om02 = [p for p in say["yerlesim"]["parcalar"] if p.get("kart") == "OM-02"]
    metre = {d: sum(p["boy_cm"] for p in om02 if (p["bilgi"].get("Duvar") == "dis") == d) / 100 for d in (False, True)}
    assert abs(metre[False] - terim["100'lük iç duvarlar"]) < 0.5 and abs(metre[True] - terim["çatı kenarına gelmeyen dış duvarlar"]) < 0.05
    assert abs(adet["OM-02"]["metre"] - sum(metre.values())) < 1e-6
    assert math.ceil(adet["OM-02"]["metre"] / 2.5 - 1e-9) == say["kesim_plani"]["OM-02"]["stok"] == liste[DUVAR100] == s["adet"]
    assert om02 and max(p["boy_cm"] for p in om02) <= 250 and say["kesim_plani"]["OM-02"]["parca_boyu_cm"] == 250
    assert not [k for k in liste if k.startswith("60'lık iç duvar üstü")]


def test_tk02_kural_yok_tk01_ile_ayni(tk02, tmp_path):
    """TK-02'de "kural yok" TK-01'deki gibi yok (İE-15 K5b: taşan veranda çatısı, tek kat panel ve dikey betopan kuruldu): iç duvarın 100'lük
    olması kartsız parça bırakmaz."""
    _, say, _ = tk02
    from araclar.paket import uret as U
    ie1 = _oku(KOK / next(m for m in U.kayit()["modeller"] if m["kod"] == "TK-01")["is_emri"])
    ky = lambda s: sorted(x["parca"] for x in s["kural_yok"])                                       # noqa: E731
    assert ky(say) == ky(_kart_sayimi(ie1, tmp_path, "TK01")) and len(ky(say)) == 0     # İE-15 K5: 10 → 8 (iki zemin kartsız); K5b: 8 → 0


def test_tk02_paket_ve_rehber(tk02, tmp_path):
    """`python -m araclar.paket TK-02 … --is-emri testler/motor/veri/TK02.json` (çizim masası): paket hatasız; rehberde iç duvar üstü
    omegaları OM-02, sırtı kural dosyasından, satırı "100'lük duvar omegası" (D-32 ek); baş makas omegalarının boyu listenin saçaktan
    saçağa boyu (D-32); genel listede "100'lük duvar omegası" listenin adediyle, D-32'nin ayrı satırı yok."""
    from araclar.paket import uret as U
    _, _, liste = tk02
    cikti = tmp_path / "Modeller"
    assert U.main(["TK-02", str(cikti), "--is-emri", str(TK02), "--gecici", str(tmp_path / "gec")]) == 0
    b = cikti / "prefabrik" / "TK-02"
    bilgi = (b / "TK-02_bilgi.md").read_text(encoding="utf-8")
    for ad in ("montaj_rehberi.html", "model.ifc", "montaj_paftasi.pdf", "yukleme_listesi.xlsx", "bayi_paftasi.pdf"):
        assert f"| `TK-02_{ad}` | Var |" in bilgi, ad
    m = re.search(r'<script type="application/json" id="pafta">(.*?)</script>', (b / "TK-02_montaj_rehberi.html").read_text(encoding="utf-8"), re.S)
    d = json.loads(m.group(1).replace("<\\/", "</"))
    from motor import yerlesim as Y
    sirt = Y.degerler(_oku(KM.YERLESIM), _oku(KM.LISTE_KURALLARI))["tavan_omegasi_yerlesimi"]["sirt_100"]
    ic = [o for o in d["omega_duvar"] if o["tur"] == "ic"]
    assert ic and all(o["kart"] == "OM-02" and o["sirt"] == sirt and o["liste"].startswith(f"{DUVAR100} 100 × 2500 · ") for o in ic)
    L = {s["kalem"]: s for s in PL.is_emrinden(_oku(TK02))["satirlar"]}
    bas_m = float(re.search(r"saçak ucundan saçak ucuna ([\d,]+) m", L["Baş makas omegası"]["formul"]).group(1).replace(",", "."))
    bas = [o for o in d["omega_duvar"] if o["tur"] == "bas"]
    assert len(bas) == 4 and round(sum(o["a1"] - o["a0"] for o in bas) / 100, 2) == bas_m
    genel = {r[1]: r[2] for r in d["genel"] if isinstance(r, list)}
    assert genel[f"{DUVAR100} 100 × 2500"] == f"{liste[DUVAR100]} adet"
    assert not [k for k in genel if "iç duvar üstü omegası" in k]
