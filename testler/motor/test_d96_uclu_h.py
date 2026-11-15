"""D-96 · Yazılan köşede köşe direği yerine üçlü H (`yapi.birlesimler` › `t: "uclu_h"`; BK-32, PC-40).

Lokman, 14 Kasım 2026 20:46:54 UTC (71 m² 2+1 evin eskizine): "... 120,5 aksındaki 115,5 pano ana giriş kapısını dik kesen pano orada köşe
direği olmayacak üçlü H olacak yanlış çizmiş mühendis ...". Kart 20:57:28 "Doğru, yanına eklensin" (773 × 888,5 cm üçlü H'lı hâl Motor
eklemesinden sonra ayrı ev olarak girer). Motor D-29'un niş T'sini (iki dış ve bir iç duvar; dış duvarlardan biri iç duvarla aynı hatta
sürer, öteki ona dik) yalnız İş Emri'nin yazdığı noktada kurar; `dis_duvar_t_bolme` ve "kapı duvarının iki ucu" aranmaz. Genel kural değildir
(her evde mi sorusu Lokman'da). Hedef örnek: Lokman'ın onayladığı eskizin planı (`veri/D96_uclu_h_beklenen.json`).
"""
from __future__ import annotations
import contextlib
import copy
import io
import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
BEKLENEN = json.loads((VERI / "D96_uclu_h_beklenen.json").read_text(encoding="utf-8"))
NOKTA = [386.5, 758.0]                                   # Motor çerçevesi (arka-sol: y arkadan); gerçekte x 386,5, önden 130,5


def _ie() -> dict:
    return json.loads((KOK / BEKLENEN["girdi"]).read_text(encoding="utf-8"))


def _anahtarsiz() -> dict:
    ie = _ie()
    ie["yapi"].pop("birlesimler")
    return ie


def _kur(ie: dict):
    with contextlib.redirect_stdout(io.StringIO()):
        return G.kur(copy.deepcopy(ie))


def _ozet(p) -> dict:
    """Duvar.a0/a1 son kurulan ızgaradan okunur: kurulumdan hemen sonra."""
    return {"WH": [p.W, p.H],
            "duvarlar": sorted([d.id, d.tur, d.yon, round(d.c, 2), round(d.a0, 2), round(d.a1, 2), [round(q.boy, 2) for q in d.panolar]]
                               for d in p.duvarlar),
            "koseler": sorted([round(v, 2) for v in k.rect] + [k.tur] for k in p.koseler),
            "h": sorted([round(h.x, 2), round(h.y, 2), h.rot, h.tur] for h in p.h_baglantilar)}


def test_girdi_yalniz_birlesim_anahtari():
    ie = _ie()
    assert ie["yapi"]["birlesimler"] == [{"nokta_cm": NOKTA, "t": "uclu_h"}]
    assert ie["yapi"]["dizilim"]["dis_duvar_t_bolme"] is False      # D-29'un genel yolu bu evde kapalı
    assert ie["yapi"]["dizilim"]["tek_ozel_pano"] == "dizilim_sonu"


def test_anahtarsiz_ev_bugunku_gibi():
    """Anahtarsız hâl eskizin "önce"si: köşe direği yerinde, 7 köşe, dış duvarda üçlü H yok."""
    assert _ozet(_kur(_anahtarsiz())) == BEKLENEN["once"]


def test_motor_eskizle_ayni():
    """Anahtarlı hâl Lokman'ın onayladığı eskizin planıyla birebir (duvarlar, panolar, köşeler, H'lar)."""
    assert _ozet(_kur(_ie())) == BEKLENEN["sonra"]


def test_yalniz_yazilan_koseye_uclu_h():
    once, sonra = BEKLENEN["once"], BEKLENEN["sonra"]
    assert len(once["koseler"]) - len(sonra["koseler"]) == 1
    giden = [k for k in once["koseler"] if k not in sonra["koseler"]]
    assert giden == [[381.5, 125.5, 386.5, 135.5, "dis"]]                      # veranda köşesindeki köşe direği
    assert [h for h in sonra["h"] if h not in once["h"]] == [[386.5, 130.5, 0.0, "dis"]]
    degisen = {(d[0], d[1], d[2], d[3]): (o[6], d[6]) for d, o in zip(sonra["duvarlar"], once["duvarlar"]) if d != o}
    assert all(d[:4] == o[:4] for d, o in zip(sonra["duvarlar"], once["duvarlar"]))
    assert degisen == {
        (5, "dis", "x", 130.5): ([125.5, 62.75, 125.5, 62.75], [120.5, 62.75, 125.5, 62.75]),   # kapı duvarı yan duvarın yüzünde biter
        (8, "dis", "y", 386.5): ([120.5], [125.5]),                                                # veranda yan duvarı (Lokman: 125,5)
        (9, "ic", "y", 386.5): ([120.5, 125.5, 125.5, 125.5, 125.5, 120.5], [125.5, 125.5, 125.5, 125.5, 125.5, 120.5])}


def test_kapi_panosu_ve_liste():
    """Ana giriş kapısının panosu 125,5 → 120,5; listede köşe direği 7 → 6, dış üçlü H 3 → 4 (Lokman'a kartla gösterilen fark)."""
    p = _kur(_ie())
    kapi = next(q for q in p.panolar if q.acilim and q.acilim.tur == "dis_kapi")
    assert round(kapi.boy, 2) == 120.5

    def satirlar(ie):
        with contextlib.redirect_stdout(io.StringIO()):
            L = PL.liste(PL.model_motor(copy.deepcopy(ie)))
        return {(r["grup"], r["kalem"], r["olcu"]): r["adet"] for r in L["satirlar"]}
    a, b = satirlar(_anahtarsiz()), satirlar(_ie())
    fark = {(*k, a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
    assert fark == {tuple(r) for r in BEKLENEN["liste_farki"]}


def test_cizim_dogrulamasi_gecer(tmp_path):
    m = dxf_out.uret(_ie(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("warnings")


def test_nis_t_olan_yerde_degisiklik_yok():
    """D-29'un niş T'si zaten olan yerde (TK-02 giriş nişi, `dis_duvar_t_bolme`) anahtar planı değiştirmez."""
    ie = json.loads((VERI / "TK02.json").read_text(encoding="utf-8"))
    a = _ozet(_kur(ie))
    for nokta in ([386.5, 758.0], [512.0, 758.0]):
        ie2 = copy.deepcopy(ie)
        ie2["yapi"]["birlesimler"] = [{"nokta_cm": nokta, "t": "uclu_h"}]
        assert _ozet(_kur(ie2)) == a, nokta


@pytest.mark.parametrize("b, beklenen", [
    ({"nokta_cm": [10.0, 5.0], "t": "uclu_h"}, "iki dış ve bir iç duvarın köşesi değil"),          # evin dış köşesi (iki dış duvar)
    ({"nokta_cm": [386.5, 381.5], "t": "uclu_h"}, "iki dış ve bir iç duvarın köşesi değil"),       # iki iç duvarın T'si
    ({"nokta_cm": [512.0, 215.25], "t": "uclu_h"}, "iki dış ve bir iç duvarın köşesi değil"),      # iki iç duvarın köşesi
    ({"nokta_cm": [386.5, 758.0], "t": "dortlu_h"}, "t (cektirme_u | uclu_h)"),
    ({"nokta_cm": [386.5, 760.0], "t": "uclu_h"}, "aks üstünde değil"),
])
def test_yanlis_nokta_hata(b, beklenen):
    """Yazılan nokta iki dış ve bir iç duvarın köşesi değilse ya da anahtar yanlışsa sessiz geçilmez (K21)."""
    ie = _ie()
    ie["yapi"]["birlesimler"] = [b]
    with pytest.raises(G.IsEmriHatasi, match=re.escape(beklenen)):
        _kur(ie)


def test_ayni_nokta_iki_kez_hata():
    ie = _ie()
    ie["yapi"]["birlesimler"] = [{"nokta_cm": NOKTA, "t": "uclu_h"}, {"nokta_cm": NOKTA, "t": "cektirme_u"}]
    with pytest.raises(G.IsEmriHatasi, match="aynı nokta iki kez"):
        _kur(ie)
