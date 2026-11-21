"""D-133 (BK-61, PC-48) · 80 m²'nin sundurması panel (teras paneli gibi), ana çatıdan 20 cm aşağıda; 45 m²'nin çatı eğimi paftadan.

Lokman, kart 20 Kasım 2026 07:08:08 "Önerdiğim gibi" (soru: "Dört çatı farkında hangi yolla gidelim?"); önce/sonra çizimine notu 07:54:25
("%5 gibi bir eğim vermen lazım verand a/sundurma paneline ayrıca ana çatıdan 20 cm aşağıda alacak panel sırt kalınlığı 8 cm üzerine çatı
özelliği ne varsa o gelir örneğin trapez sac ise trapez sac gelir onun üstünede Z şeklinde damlalık gelir") ve 12:53:18 ("damlalık bu duvar
ile trapez sacın üstüne geliyor ki duvardan süzülen su trapez sacın üstüne aksın ayrıca araya dyson mastik sıkılıyor"). 80 m² (PA-48,
HD-420): İş Emri'nde `teras_paneli` + `duvar_alti_cm: 20`, %5, panel duvardan 224 (paftanın listesindeki sundurma sacı L 2243). Önce tek
eğimli çatı saçak kotundan (260) yukarı çıkıyordu (285,4), ana saçağın içinden geçiyordu (havuz denetimi HD-02). `duvar_alti_cm` yazmayan
teras paneli 10 ile aynen (D-52, M-12). 45 m² (PA-45, HD-596): eğim %44. Hedef örnek `veri/D133_sundurma_beklenen.json`.
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
    (v,) = _plan(ie).dis_verandalar
    C = VR.cati(v, ie)
    for k in ("mahya_kotu", "sacak_kotu", "dis_kiris_ustu", "kolon_ustu", "kalinlik"):
        assert C[k] == pytest.approx(b[k], abs=0.01), k
    assert C["mahya_kotu"] == pytest.approx(float(ie["yapi"]["duvar_yuksekligi_cm"]) - 20)   # ana çatıdan 20 cm aşağıda


def test_duvar_alti_yazmayan_teras_aynen():
    from motor import veranda as VR
    b = BEK["teras_aynen"]
    ie = _ie(b["is_emri"])
    for v in _plan(ie).dis_verandalar:
        assert VR.cati(v, ie)["mahya_kotu"] == pytest.approx(b["mahya_kotu"])


def test_teras_panelinde_ozel_mahya_yok():
    """Kart 20:02:05 "Yalnız damlalık": teras panelinin duvar kenarında özel mahya yazılmaz (AP-26 da)."""
    from motor import prefabrik_liste as PL
    L = PL.is_emrinden(_ie(BEK["teras_aynen"]["is_emri"]))
    assert not [r for r in L["satirlar"] if r["kalem"] == "Özel mahya (geniş)"]
    assert [r["adet"] for r in L["satirlar"] if r["kalem"] == "Damlalık"] == [4]


def test_duvar_alti_siniri():
    from motor import geometry as G
    ie = _ie(BEK["sundurma_80m2"]["is_emri"])
    for kotu in (0, 60, "20"):
        ie2 = copy.deepcopy(ie)
        ie2["verandalar"][0]["cati"]["duvar_alti_cm"] = kotu
        with pytest.raises(G.IsEmriHatasi):
            G.kur(ie2)


def test_uyari_yok():
    from motor import veranda as VR
    ie = _ie(BEK["sundurma_80m2"]["is_emri"])
    assert VR.uyarilar(_plan(ie), ie) == []


def test_gorunus_kolon_ve_kiris_panelin_altinda():
    from motor import veranda as VR
    b = BEK["sundurma_80m2"]
    ie = _ie(b["is_emri"])
    plan = _plan(ie)
    gordu = 0
    for taraf in ("on", "arka", "sol", "sag"):
        p = [q for q in VR.gorunus_parcalari(plan, ie, taraf) if q.get("veranda")]
        if not p:
            continue
        gordu += 1
        for tur, bek in (("kolon", [b["kolon_ustu"]]), ("kiris", [b["dis_kiris_ustu"], b["yan_kiris"]["ust_duvar"]])):
            ust = [max(z for _, z in q["u"]) for q in p if q["tur"] == tur]   # yan kiriş (D-133 ek) en üstü duvarda, panelin altında
            assert all(any(z == pytest.approx(x, abs=0.01) for x in bek) for z in ust), (taraf, tur, ust)
        ust = max(z for q in p if q["tur"] == "cati" for _, z in q["u"])
        assert ust == pytest.approx(b["mahya_kotu"], abs=0.01)
    assert gordu >= 3


def test_liste():
    from motor import prefabrik_liste as PL
    b = BEK["sundurma_80m2"]
    L = PL.is_emrinden(_ie(b["is_emri"]))
    for kalem, (olcu, adet) in b["liste"].items():
        assert [(r["olcu"], r["adet"]) for r in L["satirlar"] if r["kalem"] == kalem] == [(olcu, adet)], kalem
    assert not [r for r in L["satirlar"] if r["kalem"] in b["listede_yok"]]


def test_egimli_yan_kiris():
    """D-133 ek (kart 20 Kasım 2026 20:19:34 "Eğimli, panelin altında"): 80 m²'de iki yan kiriş duvardan dış kirişin iç yüzüne, üstü
    panelin altında (duvarda 222, dışta 211,3); listede açık kenar − 10 (L 2140), dış kiriş aynen. `yan_kiris: true` yazan ev (92 m²) aynen."""
    from motor import geometry as G, prefabrik_liste as PL, veranda as VR
    b = BEK["sundurma_80m2"]; y = b["yan_kiris"]
    ie = _ie(b["is_emri"])
    v = G.kur(ie).dis_verandalar[0]
    T = VR.teras_paneli(v, ie)
    assert len(T["yan_kirisler"]) == y["adet"]
    for yk in T["yan_kirisler"]:
        assert (round(yk["ust_duvar"], 1), round(yk["ust_dis"], 1)) == (y["ust_duvar"], y["ust_dis"])
    rows = [r for r in PL.is_emrinden(ie)["satirlar"] if r["kalem"] == "Kutu profil (kiriş) 100 × 100"]
    assert sum(r["adet"] for r in rows if r["olcu"] == y["liste"]) == y["adet"]
    assert sum(r["adet"] for r in rows if r["olcu"] == y["dis_kiris"][0]) == y["dis_kiris"][1]
    for yol in ("testler/kor/projeler/AP26/is_emri.json",):     # D-56 / M-12: yazmayan teras panelinde yan kiriş yok
        ie2 = _ie(yol)
        assert all(VR.teras_paneli(v2, ie2)["yan_kirisler"] == [] for v2 in G.kur(ie2).dis_verandalar
                   if v2["cati"]["tip"] == "teras_paneli")


def test_45m2_egim():
    b = BEK["egim_45m2"]
    assert _ie(b["is_emri"])["cati"]["egim_yuzde"] == b["egim_yuzde"]
    assert _ie("is_emri/adaylar/PA45.json")["cati"]["egim_yuzde"] == b["egim_yuzde"]


def test_tarama_duvar_alti_yalniz_80m2():
    """`duvar_alti_cm` depoda yalnız 80 m²'de (havuz İş Emri'si ve aday şablonu); taşan verandada tek eğimli çatı kalmadı. Öteki evler aynen."""
    bul, tek = [], []
    for yol in sorted(KOK.rglob("*.json")):
        if ".git" in yol.parts or "node_modules" in yol.parts:
            continue
        try:
            d = json.loads(yol.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        ver = [v for v in (d.get("verandalar") or []) if isinstance(v, dict)] if isinstance(d, dict) else []
        if any("duvar_alti_cm" in (v.get("cati") or {}) for v in ver):
            bul.append(yol.relative_to(KOK).as_posix())
        if any((v.get("cati") or {}).get("tip") == "tek_yon" for v in ver):
            tek.append(yol.relative_to(KOK).as_posix())
    assert bul == ["is_emri/adaylar/PA48.json", "testler/havuz/is_emirleri/HD420.json"]
    assert tek == []
