"""D-133 (BK-61, PC-48) · Taşan verandanın tek eğimli çatısı (sundurma) ana saçağın altında; 45 m²'nin çatı eğimi paftadan.

Lokman, kart 20 Kasım 2026 07:08:08 "Önerdiğim gibi" (soru: "Dört çatı farkında hangi yolla gidelim?"). 80 m² (PA-48, HD-420): sundurmanın
yüksek ucu cephede duvar üstünde (250), çatı %10 ile dışarı iner; kirişler yatay, üstü çatının dış kirişin üstündeki en alçak kotu; kolon
kirişin altına. Önce yüksek uç saçak kotundan (260) yukarı çıkıyordu (285,4), ana saçağın içinden geçiyordu (havuz denetimi HD-02).
45 m² (PA-45, HD-596): eğim %44 (paftanın makas kesiti: saçak ucundan mahyaya 140 cm). Hedef örnek `veri/D133_sundurma_beklenen.json`.
"""
import copy
import json
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
BEK = json.loads((KOK / "testler/motor/veri/D133_sundurma_beklenen.json").read_text(encoding="utf-8"))


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _plan(ie: dict):
    from motor import geometry as G
    return G.kur(copy.deepcopy(ie))


def test_sundurma_kotlari():
    from motor import veranda as VR
    b = BEK["sundurma_80m2"]
    ie = _ie(b["is_emri"])
    plan = _plan(ie)
    (v,) = plan.dis_verandalar
    C = VR.cati(v, ie)
    for k in ("mahya_kotu", "sacak_kotu", "dis_kiris_ustu", "kolon_ustu"):
        assert C[k] == pytest.approx(b[k], abs=0.01), k
    ana_sacak = float(ie["yapi"]["duvar_yuksekligi_cm"]) + float(ie["cati"]["topuk_cm"])
    assert C["mahya_kotu"] < ana_sacak                                    # yüksek uç ana saçağın altında


def test_uyari_yok():
    from motor import veranda as VR
    ie = _ie(BEK["sundurma_80m2"]["is_emri"])
    assert VR.uyarilar(_plan(ie), ie) == []


def test_gorunus_kolon_ve_kiris_catinin_altinda():
    from motor import veranda as VR
    b = BEK["sundurma_80m2"]
    ie = _ie(b["is_emri"])
    plan = _plan(ie)
    for taraf in ("on", "sol", "sag"):
        p = VR.gorunus_parcalari(plan, ie, taraf)
        for tur, bek in (("kolon", b["kolon_ustu"]), ("kiris", b["dis_kiris_ustu"])):
            ust = [max(z for _, z in q["u"]) for q in p if q["tur"] == tur]
            assert ust and all(z == pytest.approx(bek, abs=0.01) for z in ust), (taraf, tur, ust)
        assert not [q for q in p if q["tur"] in ("sacak", "topuk")]          # sundurmada duvar üstünde saçak altı çizgisi ve topuk yok


def test_liste_kolon_boyu():
    from motor import prefabrik_liste as PL
    b = BEK["sundurma_80m2"]
    L = PL.is_emrinden(_ie(b["is_emri"]))
    (k,) = [r for r in L["satirlar"] if r["kalem"].startswith("Özel kutu profil (kolon)")]
    assert (k["olcu"], k["adet"]) == (b["liste_kolon"]["olcu"], b["liste_kolon"]["adet"])
    assert "D-133" in k["formul"]


def test_45m2_egim():
    b = BEK["egim_45m2"]
    assert _ie(b["is_emri"])["cati"]["egim_yuzde"] == b["egim_yuzde"]
    assert _ie("is_emri/adaylar/PA45.json")["cati"]["egim_yuzde"] == b["egim_yuzde"]


def test_tarama_sundurma_yalniz_80m2():
    """Taşan verandada tek eğimli çatı depoda yalnız 80 m²'de (havuz İş Emri'si ve aday şablonu): öteki evlerin çizimi ve listesi aynen."""
    bul = []
    for yol in sorted(KOK.rglob("*.json")):
        if ".git" in yol.parts or "node_modules" in yol.parts:
            continue
        try:
            d = json.loads(yol.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(d, dict) and any(isinstance(v, dict) and (v.get("cati") or {}).get("tip") == "tek_yon"
                                       for v in d.get("verandalar") or []):
            bul.append(yol.relative_to(KOK).as_posix())
    assert bul == ["is_emri/adaylar/PA48.json", "testler/havuz/is_emirleri/HD420.json"]
