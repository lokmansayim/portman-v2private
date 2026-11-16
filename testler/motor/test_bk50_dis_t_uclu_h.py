"""BK-50 (Lokman, kart 16 Kasım 2026 12:09:48 "Evet, ayrı PR"): 3D'nin H'ları yükleme listesindeki gibi.

İç duvarın dış duvarın pano ekine T ile geldiği yerde liste 3'lü H sayar (İE-27 madde 3); 3D aynı yerde düz H çiziyordu. Eklerin yeri ve
türü artık tek kaynaktan (`prefabrik_liste.ek_yerleri`): liste adedi ve 3D (`ifc_uret.hazirla`) oradan; kart modeli ve montaj rehberi 3D'yi
okur. Ayrıntı `docs/is_emirleri/BK-50.md`.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402

HAVUZ = sorted(p for p in (KOK / "is_emri" / "adaylar").glob("PA*.json"))
TK03 = KOK / "testler" / "motor" / "veri" / "TK03.json"
# 88 m²'nin üç iç T'si: Motor'un planı panonun ortasında olmayan eksiz iç T'ye 3'lü H koyuyor, liste orada çektirme U'su sayıyor. BK-38'in
# açığı (`geometry.ortadaki_h`: "TK-03'ün üç yeri Lokman'ın sözünde yok, dokunulmaz"); bu iş dokunmadı.
IC_T_ACIK = {"TK03": (1, 4)}


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _sayilar(ie: dict) -> tuple[dict, dict]:
    """(liste, 3D): dış pano eki H, dış T 3'lü H, iç pano eki H, iç T 3'lü H."""
    with contextlib.redirect_stdout(io.StringIO()):
        L = PL.is_emrinden(ie)
        g = ifc_uret.hazirla(ie)
    desen = {"dis_ek": r"H \d+ \(dış pano eki\)", "dis_T": r"3'lü H \d+ × \d+ × \d+ \(dış duvar T'si\)",
             "ic_ek": r"H standart \d+ \(iç pano eki\)", "ic_T": r"3'lü H standart \d+ \(iç T\)"}
    liste = {k: sum(s["adet"] or 0 for s in L["satirlar"] if s["grup"] == "1002" and re.fullmatch(d, s["kalem"])) for k, d in desen.items()}
    pe = g.get("pano_ekleri", [])
    ifc = {"dis_ek": sum(e["duvar"] == "dis" and e["cins"] == "pano_eki" for e in pe),
           "dis_T": sum(bool(re.match(r"BOM_B\d+_UCLU_H_DIS_", b["blok"])) for b in g["baglantilar"]),
           "ic_ek": sum(e["duvar"] == "ic" and e["cins"] == "pano_eki" for e in pe),
           "ic_T": sum(bool(re.match(r"BOM_B\d+_UCLU_H_(?!DIS)", b["blok"])) for b in g["baglantilar"])}
    return liste, ifc


@pytest.mark.parametrize("yol", HAVUZ + [TK03], ids=lambda p: p.stem)
def test_3d_h_listeyle_ayni(yol):
    ie = _oku(yol)
    try:
        liste, ifc = _sayilar(ie)
    except PL.ListeYazilmaz as e:
        pytest.skip(f"liste yazılmaz: {e}")
    if yol.stem in IC_T_ACIK:
        assert (liste["ic_T"], ifc["ic_T"]) == IC_T_ACIK[yol.stem]
        liste.pop("ic_T"), ifc.pop("ic_T")
    assert ifc == liste


def test_88m2_uc_dis_t_ve_kart_modeli(tmp_path):
    """88 m²: üç dış T'de 3'lü H (şerit görünüm, sayılan parça B05 bağlantısı, kaynağı yazılı); kart modeli listeyle: dış pano eki 25, dış
    T'si 3'lü H 3."""
    from motor import kart_model as KM
    assert ifc_uret.uret(_oku(TK03), tmp_path / "TK03.ifc")["sema_hatasi"] == 0
    f = ifcopenshell.open(str(tmp_path / "TK03.ifc"))
    seritler = [e.Name for e in f.by_type("IfcMember") if re.match(r"H_UCLU_DIS_", e.Name or "")]
    b05 = [e for e in f.by_type("IfcMember") if re.match(r"BAGLANTI_B05_", e.Name or "")]
    assert len(seritler) == 3 and len(b05) == 3
    assert all(ue.get_psets(e)["PortatifEv_Kapsam"]["Kaynak"].startswith("İE-27: dış duvarın ekine T ile gelen iç duvar") for e in b05)
    say = KM.kart_modeli(tmp_path / "TK03.ifc", tmp_path / "TK03_model.ifc", "besik_cumba")
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    assert (adet["H-01"] + adet["H-02"], adet["H-04"] + adet["H-05"]) == (25, 3)
    assert {g["parca"] for g in say["gorunum"]} >= set(seritler)


def test_kubbenin_iki_ucunda_h_yok():
    """64 m² kubbeli ev: kubbe tabanının iki ucundaki ekte H yok (D-54, açılı köşe direği; liste de saymaz); eskiden 3D orada iki H şeridi
    koyuyordu."""
    ie = _oku(KOK / "is_emri" / "adaylar" / "PA09.json")
    with contextlib.redirect_stdout(io.StringIO()):
        g = ifc_uret.hazirla(ie)
    x0, y0, x1, y1 = g["kubbeler"][0]["taban"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    uclar = [(cx, y0), (cx, y1)] if y1 - y0 > x1 - x0 else [(x0, cy), (x1, cy)]
    yakin = [e for e in g["pano_ekleri"] for (ux, uy) in uclar
             if max(abs((e["rect"][0] + e["rect"][2]) / 2 - ux), abs((e["rect"][1] + e["rect"][3]) / 2 - uy)) <= 10]
    assert yakin == []
