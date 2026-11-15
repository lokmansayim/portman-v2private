"""D-108 (BK-41, PC-44) · iç duvarın dış duvar ucunda kalan parça (`geometry._ic_duvar_dis_ucu`).

Lokman, 15 Kasım 2026 22:04 UTC (67 m² 2+1'in banyo duvarlarındaki 120,5 + 64,75'e): "bizim standart panomuz 125,5 cm eğer yarısı olan
62,75 den büyük bir sayı alırsan o tam pano sayılır"; 22:21:41: "standart aks düzenimizi bozma sadece sen orada yanlış ölçü vermiştin ...
aynı akstaki 60'lık duvarlar köşe yerleşim planı/kuralından dolayı 5'er santim kesilir ve 59,75 ile başlar wc"; kart 22:28:26 "Doğru,
59,75 başta".

Testler: uydurma 1+1 evde (banyonun ön duvarı ızgaranın 2 cm dışındaki ek aksta, 67 m²'nin banyosu gibi) banyo ile oda arasındaki duvar
120,5 + 64,75 yerine dış duvar ucunda 59,75, köşede 125,5; öteki bütün panolar aynen; depodaki İş Emri'lerinde kural hiçbir aralığı
değiştirmez (aks düzeni aynen); pano harcaması.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

UYDURMA = KOK / "testler/motor/veri/D108_ic_duvar_uydurma.json"
KOKLER = ("is_emri", "testler", "deneme", "araclar/paket/girdi", "beyin/testler")


def _ie(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _is_emri_mi(ie) -> bool:
    return isinstance(ie, dict) and "yapi" in ie and "mahaller" in ie and ie["yapi"].get("sistem", "prefabrik") != "celik"


def _depo() -> list[Path]:
    """Depodaki bütün prefabrik İş Emri'leri (havuz, hedef örnekler, kör projeler, P6001, 6×8, Yan 6×8,5, denemeler); uydurma ev hariç."""
    out = []
    for kok in KOKLER:
        for y in sorted((KOK / kok).rglob("*.json")):
            if y == UYDURMA:
                continue
            try:
                ie = _ie(y)
            except (ValueError, UnicodeDecodeError):
                continue
            if _is_emri_mi(ie):
                out.append(y)
    return out


DEPO = _depo()


def _panolar(plan) -> dict:
    return {(q.duvar.tur, q.duvar.yon, round(q.duvar.c, 4), round(q.a0, 4), round(q.a1, 4)) for q in plan.panolar}


def _kuralsiz(ie: dict, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(G, "_ic_duvar_dis_ucu", lambda plan: [])
        return G.kur(copy.deepcopy(ie))


def test_pano_harcamasi():
    """62,75'ten büyük parça 1 pano, 62,75 ve küçüğü yarım pano (Lokman 22:04)."""
    assert G.pano_harcamasi([120.5, 64.75]) == 2.0
    assert G.pano_harcamasi([59.75, 125.5]) == 1.5
    assert G.pano_harcamasi([62.75]) == 0.5
    assert G.pano_harcamasi([62.85]) == 1.0
    assert G.YARIM_PANO_CM == G.MOD / 2


def test_uydurma_ev_bugun_120_5_ve_64_75(monkeypatch):
    """Kuralsız Motor uydurma evde 67 m²'nin hatasını verir: banyo ile oda arasındaki duvar köşeden 64,75, arka duvardan 120,5."""
    p = _kuralsiz(_ie(UYDURMA), monkeypatch)
    d = next(d for d in p.duvarlar if d.tur == "ic" and d.yon == "y" and abs(d.c - 261) < 0.01)
    assert [round(q.boy, 2) for q in d.panolar] == [64.75, 120.5]
    assert G.pano_harcamasi([q.boy for q in d.panolar]) == 2.0


def test_uydurma_ev_59_75_dis_duvar_ucunda():
    """Kural: dış duvar ucunda 59,75, köşeye 125,5 (kart 22:28:26 "Doğru, 59,75 başta"); yarım pano az harcanır."""
    p = G.kur(_ie(UYDURMA))
    assert p.ic_duvar_dis_ucu == [{"duvar": "ic y 261", "once": [64.75, 120.5], "sonra": [125.5, 59.75]}]
    d = next(d for d in p.duvarlar if d.tur == "ic" and d.yon == "y" and abs(d.c - 261) < 0.01)
    arka_yuz = p.H - G.T_DIS
    assert [(round(q.a0, 2), round(q.a1, 2)) for q in d.panolar] == [(316.75, 442.25), (442.25, round(arka_yuz, 2))]
    assert round(d.panolar[-1].boy, 2) == 59.75 and abs(d.panolar[-1].a1 - arka_yuz) < 1e-6   # 59,75 arka dış duvarın iç yüzünde
    assert G.pano_harcamasi([q.boy for q in d.panolar]) == 1.5
    assert p.uyarilar == []


def test_uydurma_ev_oteki_panolar_aynen(monkeypatch):
    """Yalnız o aralığın iki panosu değişir: dış duvarlar, öteki iç duvarlar, açıklıklar, ölçü, odalar ve pano sayısı aynen."""
    ie = _ie(UYDURMA)
    p0, p1 = _kuralsiz(ie, monkeypatch), G.kur(copy.deepcopy(ie))
    a, b = _panolar(p0), _panolar(p1)
    assert len(p0.panolar) == len(p1.panolar)
    assert {k for k in a - b} == {("ic", "y", 261.0, 316.75, 381.5), ("ic", "y", 261.0, 381.5, 502.0)}
    assert {k for k in b - a} == {("ic", "y", 261.0, 316.75, 442.25), ("ic", "y", 261.0, 442.25, 502.0)}
    assert (p0.W, p0.H) == (p1.W, p1.H)
    assert {k: round(m.alan_m2, 4) for k, m in p0.mahaller.items()} == {k: round(m.alan_m2, 4) for k, m in p1.mahaller.items()}
    ac = lambda p: sorted((q.duvar.id, round(q.a0, 4), round(q.a1, 4), tuple(a.tur for a in q.aciklar)) for q in p.panolar if q.aciklar)
    assert ac(p0) == ac(p1)


def test_depo_listesi_bos_degil():
    assert len(DEPO) >= 120


@pytest.mark.parametrize("yol", DEPO, ids=lambda y: str(y.relative_to(KOK)))
def test_depodaki_evlerde_kural_bir_sey_degistirmez(yol):
    """Lokman 22:21:41 "standart aks düzenimizi bozma": depodaki hiçbir İş Emri'nde dış duvar ucunda fazla pano harcayan iç duvar
    aralığı yok; kural hiçbir aralığı değiştirmez (havuz, hedef örnekler, mühürlü evler, P6001, 6×8, kör projeler)."""
    try:
        p = G.kur(copy.deepcopy(_ie(yol)))
    except G.IsEmriHatasi as e:
        pytest.skip(f"Motor bu İş Emri'ni bugün de kurmuyor: {e}")
    assert p.ic_duvar_dis_ucu == []
