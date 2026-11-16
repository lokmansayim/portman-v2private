"""D-109 · Köşe boşluğundan taşan veranda ve taşan verandada ara kolon (BK-40, PC-45).

Lokman, 15 Kasım 2026 (UTC), eskiz notları: 22:10:48 "kolon ver kiriş kavramları bir birine karıştı kiriş olacak ama kolon olmayacak";
22:16:59 (55 m², nişin ağzındaki kiriş) "bu yeşil niş mi kiriş mi neyse olmayacak"; 22:17:51 (52 m²) "bu olmayacak plana iyice bak bak 242,5
tek kiriş 100*100 profil olacak yani altında 1 tane daha kolon olmayacak"; 22:16:38 (67 m², ortadaki kolon) "aynen böyle olacak doğrusu bu".
Kart 22:30:06 "Doğru, böyle yap" (eskiz r04: yan kiriş tek parça, altında kolon yok; 52 m² 3 kolon, 55 m² 2, 67 m² ortada 1).

Motor `verandalar[].nis` yazılınca verandayı gövdenin köşe boşluğuyla (önü ve yanı açık açık mahal) tek mahal yapar: nişin ağzında kiriş
yok, nişin köşesinde kolon yok (D-38'in köşe kolonu kalkar), boşluğun yanındaki kiriş gövdenin köşesinden ön kolona tek parça.
`ara_kolon` n dış kenara eşit aralıkla n kolon koyar; dış kiriş n + 1 eşit parça. İkisi de yazılmazsa veranda eski yoldan (bayt bayt).
Hedef örnek `veri/D109_kose_verandasi_beklenen.json`; girdiler paftalardan elle girilmiş üç ev (`veri/BK40_52m2.json`, `_55m2`, `_67m2`).
"""
from __future__ import annotations
import contextlib
import copy
import io
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP, geometry as G, prefabrik_liste as PL, veranda as VR  # noqa: E402
from motor.genel import cati_genel  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
BEKLENEN = json.loads((VERI / "D109_kose_verandasi_beklenen.json").read_text(encoding="utf-8"))
EVLER = ("52m2", "55m2", "67m2")


def _ie(ev: str) -> dict:
    return json.loads((VERI / f"BK40_{ev}.json").read_text(encoding="utf-8"))


def _kur(ie: dict):
    with contextlib.redirect_stdout(io.StringIO()):
        return G.kur(copy.deepcopy(ie))


def _r(t) -> list:
    return [round(float(x), 2) for x in t]


def ozet(ie: dict) -> dict:
    """Hedef örneğin karşılaştırdığı değerler: taşan verandanın geometrisi, planın açık kenarları ve dikmeleri, listedeki kolon ve kirişler."""
    p = _kur(ie)
    v = p.dis_verandalar[0]
    with contextlib.redirect_stdout(io.StringIO()):
        N = PL.model_motor(copy.deepcopy(ie))
        L = PL.liste(N)
    kolon = [[r["olcu"], r["adet"]] for r in L["satirlar"] if r["kalem"].startswith("Özel kutu profil (kolon)")]
    kiris = sorted(r["olcu"] for r in L["satirlar"] if r["kalem"] == "Kutu profil (kiriş) 100 × 100" for _ in range(r["adet"]))
    return {"veranda": {"ad": v["ad"], "rect": _r(v["rect"]), "en": round(v["en"], 2), "derinlik": round(v["derinlik"], 2),
                        "kolonlar": sorted(_r(k) for k in v["kolonlar"]), "kenarlar": [_r(e) for e in v["kenarlar"]],
                        "kirisler": [_r(k) for k in v["kirisler"]],
                        "dis_parcalar": [[_r(a), _r(b)] for a, b in v.get("dis_parcalar") or []],
                        "nis": {**v["nis"], "kutu": _r(v["nis"]["kutu"])} if v.get("nis") else None},
            "veranda_m2": round(p.mahaller[v["ad"]].alan_m2, 2),
            "dikme_sayisi": len(p.dikmeler), "kose_kolonu": len(p.kose_kolonlari),
            "acik_kenarlar": sorted(_r(e[:4]) for e in p.acik_kenarlar),
            "liste": {"kolon": kolon, "kirisler": kiris, "ic_kalan_dis_duvar_m": round(N["ic_kalan_dis_duvar_m"], 2), "brut_m2": N["brut_m2"]},
            "cati": cati_ozeti(ie, p)}


def cati_ozeti(ie: dict, p) -> dict:
    """Çatı (16 Kasım 2026 kartı): 52 ve 55 m²'de verandanın çatısı ana çatının cumbası (düzlemler, iki vadi, cumbanın mahyası), 67 m²'de
    verandanın kendi beşiği (ana çatının kalkan yüzünde)."""
    c, v = ie["cati"], p.dis_verandalar[0]
    o = {"tip": c["tip"], "veranda": v["cati"]["tip"]}
    if CP.tek_veranda_cumbasi(c):
        with contextlib.redirect_stdout(io.StringIO()):
            t = CP.cati(p, ie)
        k = cati_genel.cati_kur(t)["kenarlar"]
        uc = lambda e: sorted([_r(e["p"][:2]), _r(e["q"][:2])])                  # noqa: E731
        o.update({"duzlemler": sorted(d["ad"] for d in t["duzlemler"]), "kalkan": len(t["kalkanlar"]),
                  "vadiler": sorted(uc(e) for e in k if e["tur"] == "vadi"),
                  "cumba_mahyasi": next(uc(e) for e in k if e["tur"] == "mahya" and all(d.startswith("cumba") for d in e["duzlemler"]))})
    return o


@pytest.mark.parametrize("ev", EVLER)
def test_hedef_ornek(ev):
    assert ozet(_ie(ev)) == BEKLENEN["evler"][ev]["sonra"]


def test_52m2_yan_kiris_tek_parca_altinda_kolon_yok():
    p = _kur(_ie("52m2"))
    v = p.dis_verandalar[0]
    assert v["nis"]["yan"] == 1                                         # boşluk sağda
    x0, y0, x1, y1 = v["kenarlar"][2]
    assert (x0, x1) == (1014.0, 1014.0) and round(y1 - y0, 2) == 242.5    # gövdenin köşesinden ön kolona tek parça
    assert p.kose_kolonlari == []                                       # nişin köşesinde kolon yok (D-38'in kolonu kalktı)
    assert not any(abs(r[2] - 1014) < 1 and -1 < r[1] < 11 for r in p.dikmeler)
    assert len(p.dikmeler) == 3                                         # iki köşe + ortada 1
    assert sorted(_r(e[:4]) for e in p.acik_kenarlar) == sorted(_r(e) for e in v["kenarlar"])   # nişin ağzında kiriş yok
    assert "VERANDA" in p.mahaller and len([m for m in p.mahaller.values() if m.acik]) == 1   # tek mahal


def test_55m2_iki_kolon_sol_yan_kiris():
    p = _kur(_ie("55m2"))
    v = p.dis_verandalar[0]
    assert v["nis"]["yan"] == 0 and len(p.dikmeler) == 2 and p.kose_kolonlari == []
    x0, y0, x1, y1 = v["kenarlar"][1]
    assert (x0, x1) == (0.0, 0.0) and round(y1 - y0, 2) == 250.5


def test_67m2_ortada_kolon_on_kiris_iki_parca():
    p = _kur(_ie("67m2"))
    v = p.dis_verandalar[0]
    assert len(v["kolonlar"]) == 3 and v["ara_kolon"] == 1
    orta = sorted(v["kolonlar"])[1]
    assert round((orta[0] + orta[2]) / 2, 3) == round(710.25 / 2, 3)
    assert [round(a[2] - a[0], 3) for a, _k in v["dis_parcalar"]] == [355.125, 355.125]


def test_anahtarsiz_eski_yol():
    """`nis` yazılmazsa köşe boşluğundan taşan veranda bugünkü gibi açık hata; `ara_kolon` yazılmazsa iki köşe dikmesi ve tek dış kiriş."""
    ie = _ie("52m2")
    for v in ie["verandalar"]:
        v.pop("nis"); v.pop("ara_kolon"); v["ad"] = "VERANDA 2"
    with pytest.raises(G.IsEmriHatasi, match="gövdenin dış yüzüne tam oturmuyor"):
        _kur(ie)
    ie = _ie("67m2")
    ie["verandalar"][0].pop("ara_kolon")
    p = _kur(ie)
    v = p.dis_verandalar[0]
    assert len(v["kolonlar"]) == 2 and "dis_parcalar" not in v and "ara_kolon" not in v and "nis" not in v
    o = ozet(ie)
    assert o["liste"]["kolon"] == [["L 2500", 2]] and "L 7102,5" in o["liste"]["kirisler"]


@pytest.mark.parametrize("bozuk, mesaj", [
    ({"nis": "SALON"}, "açık mahalin adı"),
    ({"nis": 5}, "açık mahalin adı"),
    ({"ad": "ÖN VERANDA"}, "tek mahal olur"),
    ({"tur": "balkon"}, "türü nişinkiyle aynı"),
    ({"ara_kolon": -1}, "ara_kolon 0 ya da pozitif"),
    ({"ara_kolon": True}, "ara_kolon 0 ya da pozitif"),
    ({"ara_kolon": 1.5}, "ara_kolon 0 ya da pozitif"),
    ({"ara_kolon": 30}, "çok kısa"),
    ({"cati": {"tip": "teras_paneli", "cikma_cm": 130, "egim_yuzde": 5}}, "teras panelinde yan kiriş yok"),
    ({"bas_cm": 507}, "ağzı verandanın iç kenarında değil"),
    ({"nis": None}, "açık mahalin adı"),
    ({"ara_kolon": None}, "ara_kolon 0 ya da pozitif"),
    ({"ara_kolonu": 1}, "bilinmeyen anahtar 'ara_kolonu'; ara_kolon mu"),
    ({"nıs": "VERANDA"}, "bilinmeyen anahtar 'nıs'; nis mi"),
])
def test_hatalar(bozuk, mesaj):
    ie = _ie("52m2")
    ie["verandalar"][0].update(bozuk)
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        _kur(ie)


@pytest.mark.parametrize("dikme", [
    [1004, 0],                                                          # nişin köşesi (sol-alt köşe, gerçek çerçevede)
    [1004, 50],                                                         # yan kirişin altı (nişin içinde)
    [700, 0],                                                           # nişin ağzı
])
def test_niste_is_emri_dikmesi_hata(dikme):
    """Lokman 22:17:51 "altında 1 tane daha kolon olmayacak": nişe yazılan İş Emri dikmesi sessizce kalmaz (K21; geometri hakemi bulgusu)."""
    ie = _ie("52m2")
    ie["dikmeler"] = [dikme]
    with pytest.raises(G.IsEmriHatasi, match=r"nişte \(VERANDA\) İş Emri dikmesi var"):
        _kur(ie)


def test_yalniz_onu_acik_giris_nisine_nis_yazilmaz():
    """TK-01'in giriş nişi (yalnız önü açık) köşe boşluğu değildir; `nis` yazılırsa açık hata, sessizce yutulmaz (K21)."""
    ie = json.loads((VERI / "TK01_r07.json").read_text(encoding="utf-8"))
    on = next(v for v in ie["verandalar"] if v["cephe"] == "on")
    on.pop("ad"); on["nis"] = "GİRİŞ"
    with pytest.raises(G.IsEmriHatasi, match="yalnız bir yanı açık"):
        _kur(ie)


def test_gorunuste_govdenin_ardindaki_kiris_yok():
    """52 m² soldan: sağdaki 242,5'lik yan kirişin gövdenin ardında kalan kısmı (nişin yanı) çizilmez; sağdan: tamamı görünür."""
    ie = _ie("52m2")
    p = _kur(ie)
    with contextlib.redirect_stdout(io.StringIO()):
        sol = [q for q in VR.gorunus_parcalari(p, p.is_emri, "sol") if q["tur"] == "kiris"]
        sag = [q for q in VR.gorunus_parcalari(p, p.is_emri, "sag") if q["tur"] == "kiris"]
    u_sol = [(min(u for u, _z in q["u"]), max(u for u, _z in q["u"])) for q in sol]
    assert all(a >= -1e-6 for a, _b in u_sol)                          # soldan u = −y: gövde u ≤ 0'da, kiriş yalnız taşan kısımda
    u_sag = [(min(u for u, _z in q["u"]), max(u for u, _z in q["u"])) for q in sag]
    assert any(round(b - a, 2) == 242.5 for a, b in u_sag)


@pytest.mark.parametrize("ev, olculer, olmayan", [
    ("52m2", {635.5, 242.5, 117.0}, {627.5}),
    ("55m2", {449.25, 250.5, 125.0}, {439.25}),
])
def test_cizim_olculeri(tmp_path, ev, olculer, olmayan):
    """Ön onay çiziminde köşe verandasının eni, boşluk yanındaki yan kirişin boyu ve öteki yandaki taşma; nişin kendi ölçüsü yok. DXF
    yeniden açılıp doğrulanır (K23)."""
    import ezdxf
    from motor import dxf_out
    with contextlib.redirect_stdout(io.StringIO()):
        m = dxf_out.uret(_ie(ev), tmp_path)
    assert m["validation_passed"] and m["pdf"]
    doc = ezdxf.readfile(tmp_path / m["dxf"])
    olcu = {round(d.get_measurement(), 2) for d in doc.modelspace().query("DIMENSION")}
    assert olculer <= olcu and not (olmayan & olcu)


def _cumbasiz(ie: dict) -> dict:
    """Aynı ev, verandanın çatısı Motor'un varsayılan beşiği (16 Kasım kartından önceki girdi)."""
    ie = copy.deepcopy(ie)
    ie["cati"]["tip"] = "besik"; ie["cati"].pop("cumbalar")
    ie["verandalar"][0].pop("cati")
    return ie


def test_ifc_girdisi_birlesik_mahal():
    from motor import ifc_uret
    with contextlib.redirect_stdout(io.StringIO()):
        g = ifc_uret.hazirla(_cumbasiz(_ie("52m2")))
    v = g["dis_verandalar"][0]
    assert round(v["net_m2"], 2) == BEKLENEN["evler"]["52m2"]["sonra"]["veranda_m2"] and len(v["poligon"]) == 6


# --- Çatı: Lokman, 16 Kasım 2026 07:03:57 "cumbalı çatıda kurallarını bir yokla bir sıkıntın var gibi"; çatı eskizi kartı 08:05:51
# "52/55 öneri doğru, 67 böyle" (soru: "Köşe verandasının çatısı bu eskizdeki gibi mi olsun?"; eskiz PF Kose_Verandasi_Motor/
# 2026-11-16_cati_eskiz_r01/): 52 ve 55 m²'de verandanın çatısı ana çatının cumbası, iki vadiyle girer; 67 m²'de verandanın beşiği.

@pytest.mark.parametrize("ev, cephe_x", [("52m2", 696.25), ("55m2", 224.62)])
def test_veranda_cumbasi_iki_vadi(ev, cephe_x):
    """Cumbanın mahyası verandanın ortasında, cepheye dik; iki vadi ana çatının ön yüzüyle mahyanın iç ucunda birleşir. 52 m²'de ortadaki
    kolon cumbanın tepesinin altında (paftanın veranda profili)."""
    ie = _ie(ev)
    p = _kur(ie)
    o = cati_ozeti(ie, p)
    (a, b) = o["cumba_mahyasi"]
    assert a[0] == b[0] and abs(a[0] - cephe_x) < 0.01                   # mahya cepheye dik, verandanın ortasında
    ic = max(a, b, key=lambda q: q[1])
    assert len(o["vadiler"]) == 2 and all(ic in vd for vd in o["vadiler"])
    v = p.dis_verandalar[0]
    if ev == "52m2":
        orta = sorted(v["kolonlar"])[1]
        assert abs((orta[0] + orta[2]) / 2 - a[0]) < 0.01
    assert not any(u.startswith(f"Veranda {v['ad']}: çatısı") for u in p.uyarilar)   # varsayım ve "dere çizimde yok" uyarısı yok


@pytest.mark.parametrize("ev", ("52m2", "55m2"))
def test_veranda_cumbasi_liste_cizimden(ev):
    """Liste (TASLAK) cumbayı çizimdeki çatıdan sayar (AP-22'nin çapraz cumbası gibi, D-47): saçak hatları ve dere içi çatının kendi
    kenarlarından; cumbanın altı taşan veranda (kalkanı dış kirişin üstünde). Ana çatının ön saçağı cumbanın altında sayılmaz."""
    ie = _ie(ev)
    p = _kur(ie)
    with contextlib.redirect_stdout(io.StringIO()):
        N = PL.model_motor(copy.deepcopy(ie))
        k = cati_genel.cati_kur(CP.cati(p, ie))["kenarlar"]
    toplam = lambda tur: sum(e["plan_boy"] for e in k if e["tur"] == tur) / 100                  # noqa: E731 (m; liste 3 hanede yuvarlar)
    assert [c["ad"] for c in N["cati"]] == ["ana çatı", "cumba"]
    assert abs(sum(h for c in N["cati"] for h in c["sacak_hatlari_m"]) - toplam("sacak")) < 0.005
    cb = N["cati"][1]
    assert abs(sum(cb["dere_ici_m"]) - sum(e["boy"] for e in k if e["tur"] == "vadi") / 100) < 0.005
    assert cb["kalkan_kirisli"] and cb["acik"] and "cikintisiz" not in cb


@pytest.mark.parametrize("bozma", [
    lambda ie: ie["cati"]["cumbalar"][0].update(cephe="arka"),
    lambda ie: ie["cati"]["cumbalar"][0].update(bas_cm=0),
    lambda ie: ie["cati"]["cumbalar"][0].pop("cephe"),
])
def test_veranda_cumbasi_liste_yanlis_tanim(bozma):
    """Çizimin kurmadığı veranda cumbasını liste de yazmaz (K21; geometri hakemi, 16 Kasım)."""
    ie = _ie("52m2")
    bozma(ie)
    with pytest.raises(PL.ListeYazilmaz):
        with contextlib.redirect_stdout(io.StringIO()):
            PL.model_motor(ie)


def test_veranda_cumbasi_ifc_ve_kart_modeli_kurmaz():
    """IFC ve kart modeli köşe verandasının cumbasını bu sürümde kurmaz: açık hata (yanlış çatı kurulmaz)."""
    from motor import cati_capraz, ifc_uret
    ie = _ie("52m2")
    with pytest.raises(CP.PrefabrikCatiHatasi, match="köşe verandasının cumbasını kart modeli ve IFC"):
        with contextlib.redirect_stdout(io.StringIO()):
            ifc_uret.hazirla(ie)
    with pytest.raises(CP.PrefabrikCatiHatasi, match="köşe verandasının cumbasını"):
        cati_capraz.tanim(_kur(ie), ie)


@pytest.mark.parametrize("bozma, hata, mesaj", [
    (lambda ie: ie["cati"]["cumbalar"][0].update(cephe="arka"), CP.PrefabrikCatiHatasi, "verandası VERANDA on cephesinde"),
    (lambda ie: ie["cati"]["cumbalar"][0].update(bas_cm=0), CP.PrefabrikCatiHatasi, "yalnız cephe ve veranda"),
    (lambda ie: ie["verandalar"][0].pop("cati"), G.IsEmriHatasi, None),
    (lambda ie: ie["cati"].update(tip="besik"), G.IsEmriHatasi, "ana çatı besik_cumba olur"),
])
def test_veranda_cumbasi_yanlis_tanim_hata(bozma, hata, mesaj):
    """Yanlış yazılan veranda cumbası sessizce çizilmez (K21)."""
    ie = _ie("52m2")
    bozma(ie)
    with pytest.raises(hata, match=mesaj):
        p = _kur(ie)
        with contextlib.redirect_stdout(io.StringIO()):
            CP.cati(p, ie)


def test_67m2_veranda_besigi_aynen():
    """67 m²: verandanın çatısı İş Emri'nde beşik (kartla); çizim karttan önceki varsayımla aynı, varsayım uyarısı yok."""
    ie = _ie("67m2")
    p = _kur(ie)
    assert p.dis_verandalar[0]["cati"]["tip"] == "besik" and not any("çatısı İş Emri'nde yok" in u for u in p.uyarilar)
    ie.get("verandalar")[0].pop("cati")
    q = _kur(ie)
    assert q.dis_verandalar[0]["cati"] == p.dis_verandalar[0]["cati"]
