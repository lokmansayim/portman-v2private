"""BK-38 · Montaj çizimi ile yükleme listesi aynı parçayı gösterir (D-105, PC-42).

Madde 1 (Lokman, 15 Kasım 2026 08:51:58, 140 m² 3+1 eskizine yorum: "evet böyle bir uygulama var duvar tam ise yani 125,5 cm ise ve
böleceğimiz pano tam ortaya geliyorsa 3'lü H kullanmak yerine tam ortaya çektirme U'su koyuyoruz maliyet ve hız açısından"; kart 09:14:09
"Evet, 15 yerin hepsinde"): iç duvarın T ile geldiği yerde geçen duvarın panosu bölünmemişse (ek yok) parça çektirme U'sudur. Liste böyle
sayıyordu (İE-27), çizim ise orada 3'lü H basıyordu: 9 evde 15 yer. Motor artık pano ekinde olmayan H'ı çizmez (`geometry.ortadaki_h`),
Motor'un doğrulaması (K23, `validate.dogrula`) panonun ortasındaki H'ı hata sayar (hakem kalemi).

Madde 2 (kart 09:14:41 "Evet, 1 adet 100'lük"): 100'lük iç duvar dış köşeye gelince listede 1 çektirme U'su (önce yalnız 60'lık iç duvarda).
"""
from __future__ import annotations

import copy
import glob
import json
import re
import sys
from pathlib import Path

import ezdxf
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402

# Değişen 15 yer (Motor çerçevesi, cm): ev → kalkan H'lar. Havuz kayıtları `is_emri/adaylar/`. 15 Kasım 2026'da H sayısı önce → sonra:
# PA03 2 → 1, PA05 4 → 3, PA08 9 → 7, PA12 4 → 3, PA22 6 → 3, PA23 2 → 0, PA25 4 → 1, PA30 4 → 3, PA33 9 → 8. Test sayıyı değil farkı
# kilitler: öteki işler (ör. D-104) aynı evde başka H'a dokunursa bu test onu "değişen yer" saymaz.
DEGISEN = {
    "PA03": [(261.0, 751.25)],
    "PA05": [(444.25, 574.75)],
    "PA08": [(318.75, 430.25), (946.25, 739.0)],
    "PA12": [(381.5, 402.25)],
    "PA22": [(130.5, 618.77), (444.25, 618.77), (444.25, 807.02)],
    "PA23": [(449.25, 381.25), (261.0, 381.25)],
    "PA25": [(444.25, 434.5), (256.0, 622.75), (444.25, 622.75)],
    "PA30": [(381.5, 402.25)],
    "PA33": [(318.75, 454.25)],
}


def _ie(yol) -> dict:
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def _is_emirleri() -> list[Path]:
    """Depodaki pano Motor'u İş Emri'leri: havuz kayıtları, test evleri, kör projeler (kurulamayanlar atlanır)."""
    yollar = sorted({*glob.glob(str(KOK / "is_emri" / "adaylar" / "PA*.json")), *glob.glob(str(KOK / "testler" / "motor" / "veri" / "TK0*.json")),
                     *glob.glob(str(KOK / "testler" / "cizim" / "evler" / "*.json")), *glob.glob(str(KOK / "testler" / "kor" / "projeler" / "*" / "is_emri.json")),
                     *glob.glob(str(KOK / "testler" / "havuz" / "is_emirleri" / "*.json"))})
    return [Path(y) for y in yollar]


def _planlar():
    for yol in _is_emirleri():
        ie = _ie(yol)
        if not isinstance(ie, dict) or "yapi" not in ie or "mahaller" not in ie:
            continue
        try:
            yield yol, ie, G.kur(copy.deepcopy(ie))
        except Exception:                                      # noqa: BLE001 — başka motorun ya da eski şemanın dosyası
            continue


def _t_orta_yerleri(plan) -> list[tuple[float, float]]:
    """Listenin çektirme U'su saydığı T'ler (`prefabrik_liste.model_motor` › `t_orta` ile aynı tanım): iç duvarın ucu bir duvara T ile
    geliyor, uç uca ek değil, geçen duvarın pano ekinde değil."""
    W_ = {d.id: d for d in plan.duvarlar}
    out = []
    for d in plan.duvarlar:
        if d.tur != "ic":
            continue
        for uc in (0, 1):
            m = re.match(r"T→(\d+)(.*)$", d.uc_notu.get(uc, ""))
            if not m or "köşe" in m.group(2):
                continue
            o = W_[int(m.group(1))]
            if any(w is not d and w.yon == d.yon and abs(w.c - d.c) < 1e-6
                   and (abs(w.p1 - d.p0) < 1e-6 if uc == 0 else abs(w.p0 - d.p1) < 1e-6) for w in plan.duvarlar):
                continue
            if not any(abs(p.a1 - d.c) <= o.h + 3.5 for p in o.panolar[:-1]):
                out.append((d.c, o.c) if o.yon == "x" else (o.c, d.c))
    return out


def _hs(plan) -> list[tuple[float, float]]:
    return sorted((round(h.x, 2), round(h.y, 2)) for h in plan.h_baglantilar)


@pytest.mark.parametrize("kod", sorted(DEGISEN))
def test_degisen_yerler(kod, monkeypatch):
    """Dokuz evde 15 yer: panonun ortasındaki H kalkar, öteki H'lar yerinde (BK-38'den önceki Motor'la kıyas)."""
    ie = _ie(KOK / "is_emri" / "adaylar" / f"{kod}.json")
    sonra = _hs(G.kur(copy.deepcopy(ie)))
    monkeypatch.setattr(G, "ortadaki_h", lambda plan, hb: None)   # BK-38'den önceki Motor
    once = _hs(G.kur(copy.deepcopy(ie)))
    monkeypatch.undo()
    kalkan = [h for h in once if h not in sonra]
    assert sorted(kalkan) == sorted(DEGISEN[kod]) and all(h in once for h in sonra), (kod, once, sonra)


def test_cizimde_panonun_ortasinda_h_yok_ve_liste_ayni():
    """Depodaki her İş Emri'nde: çizimdeki her H geçen duvarın pano ekinde ya da duvar ucunda (niş T'si); listenin çektirme U'su saydığı
    hiçbir yerde H yok."""
    n = 0
    for yol, _ie_, plan in _planlar():
        n += 1
        assert not [hb for hb in plan.h_baglantilar if G.ortadaki_h(plan, hb)], yol
        for x, y in _t_orta_yerleri(plan):
            assert not any(abs(h.x - x) <= 8.5 and abs(h.y - y) <= 8.5 for h in plan.h_baglantilar), (yol, x, y)
    assert n >= 60


def test_ortadaki_h_tanimi():
    """`ortadaki_h` panonun ortasındaki H'ın geçen duvarını verir; pano ekindeki ve niş T'sindeki H'a None."""
    plan = G.kur(_ie(KOK / "is_emri" / "adaylar" / "PA25.json"))
    assert plan.h_baglantilar and all(G.ortadaki_h(plan, h) is None for h in plan.h_baglantilar)
    yapay = G.HBaglanti(444.25, 434.5, 90.0, "ic")             # kalkan yerlerden biri: geçen duvar 381,5–507 panosunun ortası
    t = G.ortadaki_h(plan, yapay)
    assert t is not None and t.tur == "ic" and t.yon == "x"
    tk = G.kur(_ie(KOK / "testler" / "motor" / "veri" / "TK02.json"))   # dış duvarın pano ekindeki ve nişteki H'lar (iç 100)
    assert any(h.tur == "dis" for h in tk.h_baglantilar) and all(G.ortadaki_h(tk, h) is None for h in tk.h_baglantilar)


def test_dogrulama_ortadaki_h_yi_yakalar(tmp_path, monkeypatch):
    """Hakem kalemi: Motor panonun ortasına H koyarsa doğrulama (K23) düşer, teslim PDF'i yazılmaz."""
    from motor import dxf_out
    ie = _ie(KOK / "is_emri" / "adaylar" / "PA25.json")
    monkeypatch.setattr(G, "ortadaki_h", lambda plan, hb: None)   # BK-38'den önceki Motor
    m = dxf_out.uret(copy.deepcopy(ie), tmp_path, ad_govde="PA25")
    v = json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))
    hatalar = [e for e in v["errors"] if "panonun ortasında" in e]
    assert v["passed"] is False and len(hatalar) == 3, v["errors"]
    assert not (tmp_path / "PA25.pdf").exists()
    monkeypatch.undo()
    m = dxf_out.uret(copy.deepcopy(ie), tmp_path / "sonra", ad_govde="PA25")
    v = json.loads((tmp_path / "sonra" / "validation.json").read_text(encoding="utf-8"))
    n = len(G.kur(copy.deepcopy(ie)).h_baglantilar)             # 15 Kasım 2026: 1 (pano ekindeki iç T)
    assert v["passed"] is True and v["h_connectors"] == n >= 1, v["errors"]
    ins = [e for e in ezdxf.readfile(tmp_path / "sonra" / "PA25.dxf").modelspace().query("INSERT") if "UCLU_H" in e.dxf.name]
    assert len(ins) == 3 * n                                    # ana plan, net alan kopyası, saha montaj planı: her H birer kez
    assert m is not None


@pytest.mark.parametrize("kod, cy", [("PA11", {"t_orta": 2, "dis_kose": 1, "serbest": 1}), ("PA26", {"t_orta": 2, "dis_kose": 1, "serbest": 0})])
def test_100luk_dis_kosede_cektirme_u(kod, cy):
    """Madde 2: 100'lük iç duvarın dış köşeye geldiği yerde listede 1 çektirme U'su (91 m² 3+1, 71 m² 2+1); çizim değişmez."""
    ie = _ie(KOK / "is_emri" / "adaylar" / f"{kod}.json")
    assert ie["yapi"]["duvar_kalinligi_cm"] == {"dis": 10, "ic": 10}
    N = PL.model_motor(ie)
    assert N["cektirme_yerleri"] == cy
    satir = [x for x in PL.liste(N, PL.kurallari_oku())["satirlar"] if x["kalem"].startswith("Çektirme U'su") and x["dayanak"] == "Kural (Lokman 3.11)"]
    assert len(satir) == 1 and satir[0]["adet"] == sum(cy.values()) and satir[0]["kalem"] == "Çektirme U'su 100 (iç duvar)"
    assert "100'lük köşeye gelen 100'lük iç duvar 1" in satir[0]["formul"], satir[0]
    plan = G.kur(copy.deepcopy(ie))                             # köşe direği yerinde: iç duvarın o ucu dış köşede biter
    assert sum(1 for d in plan.duvarlar if d.tur == "ic" for n in d.uc_notu.values() if n.endswith("(dış köşe)")) == 1
