"""D-104 · Üçlü H yalnız iç duvar dış duvarla aynı kalınlıktaysa (BK-36, PC-41).

Lokman, 15 Kasım 2026 07:32:42 UTC: "bu 71 m² deki üçlü H iç duvarlar 100'lük olduğu için olur ama iç duvarlar 60'lık olursa olmaz köşe
kullanmak zorunda kalırız şöyle bir mantık vereyim standart H'larda 100'lükten 60'lığa geçen redisyon gibi bir malzeme yok". 90 m² 3+1 hedef
evin (TK-01 r08, iç 60) giriş nişine, 07:47:55: "bunlar olmaz buralara mecburen 100'lük köşeler gelecek", 07:48:04: "burasıda aynı"; 71 m²
evin üçlü H'ına 07:48:10: "burası doğru". Kart 07:55:12 "Doğru, hedef örnekler güncellensin" ("90 m2 evin giriş nişinde köşe direği
hâli doğru mu?").

Motor D-29'un niş T'sini (PC-03) ve İş Emri'nin yazdığı üçlü H'ı (D-96, PC-40) yalnız iç duvar dış duvarla aynı kalınlıktaysa kurar. 60'lık
iç duvarlı evde niş T'si kurulmaz, orada köşe direği kalır; yazılmış üçlü H açık hatadır (K21: sessizce köşe direğine dönmez). Hedef örnek:
Lokman'a gösterilen önce/sonra pano diziliminin planı (`veri/D104_nis_kose_beklenen.json`).
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
BEKLENEN = json.loads((VERI / "D104_nis_kose_beklenen.json").read_text(encoding="utf-8"))
D96 = json.loads((VERI / "D96_uclu_h_beklenen.json").read_text(encoding="utf-8"))
NIS = [[386.5, 130.5], [512.0, 130.5]]                      # 90 m² evin giriş nişinin iki ucu (kapı duvarı y 130,5)


def _ie(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _kur(ie: dict):
    with contextlib.redirect_stdout(io.StringIO()):
        return G.kur(copy.deepcopy(ie))


def _ozet(p) -> dict:
    """test_d96_uclu_h._ozet ile aynı."""
    return {"WH": [p.W, p.H],
            "duvarlar": sorted([d.id, d.tur, d.yon, round(d.c, 2), round(d.a0, 2), round(d.a1, 2), [round(q.boy, 2) for q in d.panolar]]
                               for d in p.duvarlar),
            "koseler": sorted([round(v, 2) for v in k.rect] + [k.tur] for k in p.koseler),
            "h": sorted([round(h.x, 2), round(h.y, 2), h.rot, h.tur] for h in p.h_baglantilar)}


def _satirlar(ie: dict) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        L = PL.liste(PL.model_motor(copy.deepcopy(ie)))
    return {(r["grup"], r["kalem"], r["olcu"]): r["adet"] for r in L["satirlar"]}


def test_90m2_girdi_ic_60():
    ie = _ie(BEKLENEN["girdi"])
    assert ie["yapi"]["duvar_kalinligi_cm"] == {"dis": 10, "ic": 6}
    assert "birlesimler" not in ie["yapi"]


def test_90m2_niste_kose_diregi():
    """90 m² hedef evin giriş nişi Lokman'a gösterilen "sonra" planıyla birebir: iki üçlü H yerine 100'lük köşe direği."""
    assert _ozet(_kur(_ie(BEKLENEN["girdi"]))) == BEKLENEN["sonra"]


def test_90m2_yalniz_nis_degisir():
    once, sonra = BEKLENEN["once"], BEKLENEN["sonra"]
    assert once["WH"] == sonra["WH"]
    assert [h for h in once["h"] if h not in sonra["h"]] == [[x, y, r, "dis"] for (x, y), r in zip(NIS, (0.0, 180.0))]
    assert [h for h in sonra["h"] if h not in once["h"]] == []
    assert [k for k in sonra["koseler"] if k not in once["koseler"]] == [[381.5, 125.5, 386.5, 135.5, "dis"], [512.0, 125.5, 517.0, 135.5, "dis"]]
    assert [k for k in once["koseler"] if k not in sonra["koseler"]] == []
    assert all(d[:4] == o[:4] for d, o in zip(sonra["duvarlar"], once["duvarlar"]))
    degisen = {tuple(d[:4]): (o[6], d[6]) for d, o in zip(sonra["duvarlar"], once["duvarlar"]) if d != o}
    assert degisen == {
        (5, "dis", "x", 130.5): ([115.5], [125.5]),                                                   # nişin kapı duvarı
        (10, "dis", "y", 386.5): ([125.5], [120.5]),                                                  # nişin sol yan duvarı
        (11, "ic", "y", 386.5): ([125.5, 125.5, 125.5, 125.5, 125.5, 120.5], [120.5, 125.5, 125.5, 125.5, 125.5, 120.5]),
        (12, "dis", "y", 512.0): ([125.5], [120.5]),                                                  # nişin sağ yan duvarı
        (13, "ic", "y", 512.0): ([125.5, 125.5, 125.5, 122.5], [120.5, 125.5, 125.5, 122.5])}


def test_90m2_liste():
    """Listede köşe direği 6 → 8, dış üçlü H 8 → 6, 60'lık çektirme U'su 0 → 2 (Lokman'a gösterilen fark)."""
    b = _satirlar(_ie(BEKLENEN["girdi"]))
    for grup, kalem, olcu, once, sonra in BEKLENEN["liste_farki"]:
        assert b.get((grup, kalem, olcu)) == sonra, (kalem, olcu, once, sonra)


def test_cizim_dogrulamasi_gecer(tmp_path):
    m = dxf_out.uret(_ie(BEKLENEN["girdi"]), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("warnings")


def test_71m2_ic_100_uclu_h_aynen():
    """71 m² 2+1 (iç 100) yazılan üçlü H'ıyla aynen (Lokman 07:48:10 "burası doğru")."""
    ie = _ie(D96["girdi"])
    assert ie["yapi"]["duvar_kalinligi_cm"]["ic"] == ie["yapi"]["duvar_kalinligi_cm"]["dis"]
    assert _ozet(_kur(ie)) == D96["sonra"]


def test_71m2_ic_60_uclu_h_hata():
    """Aynı ev 60'lık iç duvarla: yazılan üçlü H sessizce köşe direğine dönmez, açık hata (K21)."""
    ie = _ie(D96["girdi"])
    ie["yapi"]["duvar_kalinligi_cm"] = {"dis": 10, "ic": 6}
    with pytest.raises(G.IsEmriHatasi, match=re.escape("iç 60, dış 100 mm") + ".*" + re.escape("(386.5, 758)")):
        _kur(ie)


def test_ic_100_nis_t_kalir():
    """İç duvarı 100'lük olan evde D-29'un niş T'si yerinde (TK-02 giriş nişi, PC-03)."""
    ie = json.loads((VERI / "TK02.json").read_text(encoding="utf-8"))
    p = _kur(ie)
    assert G.T_IC == G.T_DIS
    assert sorted((round(h.x, 2), round(h.y, 2)) for h in p.h_baglantilar if h.tur == "dis" and round(h.y, 2) == 130.5) == [tuple(n) for n in NIS]


def test_nis_olcusu_oda_yaninda():
    """Ön onay çiziminde nişin iki yan duvarının 120,5 ölçüsü nişin içinde değil, salon ve mutfak yanında: dar açık mahalde (tek pano şeridi)
    yan duvarın özel pano ölçüsü kapalı mahalin yanına geçer (`dxf_out.Cizici._dar_acik_mahal_yani`). Nişin adı ve m²'si ölçüye binmez
    (`test_d31_gorunus.test_her_bolmenin_adinin_altinda_net_m2`, TK-01 r06)."""
    from motor.katalog import Katalog
    plan = _kur(_ie(BEKLENEN["girdi"]))
    c = dxf_out.Cizici(plan, Katalog())
    c.ciz_plan(0.0, 0.0, "ANA", "KAT PLANI", "")
    nis = []
    for e in (c.doc.entitydb[h] for h in c.bolgeler["plan"]):
        if e.dxftype() != "DIMENSION" or e.dxf.layer != "OZEL_PANEL_OLCU_CM":
            continue
        cizgi = [(g.dxf.start, g.dxf.end) for g in e.get_geometry_block() if g.dxftype() == "LINE"]
        olcu = [(a, b) for a, b in cizgi if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - 5.0) < 1e-6 and abs(b[1] - 125.5) < 1e-6]
        if olcu:
            nis.append(round(olcu[0][0][0], 2))
    assert len(nis) == 2 and min(nis) < 386.5 - 5 and max(nis) > 512.0 + 5, nis      # nişin yan duvarlarının dışında (salon, mutfak)
