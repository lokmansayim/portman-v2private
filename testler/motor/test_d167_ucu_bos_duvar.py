"""D-167 (BK-91, PC-52) · ucu boşta iç duvar (`ucu_bos_duvarlar`).

Lokman, 28 Kasım 2026 10:55 UTC, disk arşivinin bekleyen evlerinin görseline: "yarım pano ekle" (52 m² 2+1, HD-220: banyonun alt
duvarından, 59,75'lik panodan sonra aşağı; 58 m², HD-513: banyonun sağ duvarının altında). Motor duvarı mahal sınırından kurar; bu duvar
tek mahalin içindedir. Giriş: {"x": hat, "y": [bağlı uç, serbest uç]} (Motor çerçevesinde, cm); serbest uç panonun fiziksel ucu.

Testler: iki evde yarım pano 62,75 cm, ucu boşta, öteki bütün panolar aynen; anahtarsız İş Emri aynen; hatalı girişler (K21).
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

VERI = KOK / "testler/motor/veri"
EV_52 = VERI / "D167_HD220_52m2.json"
EV_58 = VERI / "D167_HD513_58m2.json"
DUVAR_52 = {"x": 381.5, "y": [198.25, 264.0]}      # banyonun alt duvarının yüzünden (201,25) 62,75
DUVAR_58 = {"x": 577.49, "y": [213.5, 276.25]}     # banyonun sağ duvarı aynı hatta sürer, T'nin aksından 62,75


def _ie(yol: Path, *duvarlar) -> dict:
    ie = json.loads(yol.read_text(encoding="utf-8"))
    if duvarlar:
        ie["ucu_bos_duvarlar"] = list(duvarlar)
    return ie


def _anahtar(q) -> tuple:
    return (q.duvar.yon, round(q.duvar.c, 3), round(q.a0, 3), round(q.a1, 3))


def _fark(once, sonra) -> tuple[set, set]:
    k0 = {_anahtar(q) for q in once.panolar}
    k1 = {_anahtar(q) for q in sonra.panolar}
    return k0 - k1, k1 - k0


@pytest.mark.parametrize("yol,duvar,beklenen", [
    (EV_52, DUVAR_52, ("y", 381.5, 201.25, 264.0)),
    (EV_58, DUVAR_58, ("y", 577.49, 213.5, 276.25)),
])
def test_yarim_pano_eklenir_gerisi_aynen(yol, duvar, beklenen):
    once = G.kur(_ie(yol))
    sonra = G.kur(_ie(yol, duvar))
    kalkan, yeni = _fark(once, sonra)
    assert kalkan == set()
    assert len(yeni) == 1
    yon, c, a0, a1 = next(iter(yeni))
    # Motor y'yi arkadan sayar, plan sonda aynalanır (arka-sol): karşılaştırma aynalanmış çerçevede
    H = sonra.H
    assert (yon, c) == beklenen[:2]
    assert sorted((round(H - a1, 3), round(H - a0, 3))) == [beklenen[2], beklenen[3]]
    assert abs((a1 - a0) - G.YARIM_PANO_CM) < 1e-6
    assert len(sonra.panolar) == len(once.panolar) + 1
    assert len(sonra.ucu_bos_duvarlar) == 1
    d = next(d for d in sonra.duvarlar if d.id == sonra.ucu_bos_duvarlar[0])
    assert d.tur == "ic" and "serbest" in d.uc_notu.values()            # liste serbest uçta çektirme U'su sayar (İE-27)


def test_anahtarsiz_aynen():
    a = G.kur(_ie(EV_52))
    b = G.kur(_ie(EV_52))
    assert [_anahtar(q) for q in a.panolar] == [_anahtar(q) for q in b.panolar]
    assert a.ucu_bos_duvarlar == []


@pytest.mark.parametrize("duvar,mesaj", [
    ({"x": 381.5, "y": [198.25]}, "bir hat ve"),
    ({"x": 381.5, "y": [198.25, 230.0]}, "sonraki aksa"),
    ({"x": 381.5, "y": [198.25, 600.0]}, "boşta değil"),                   # ön dış duvara değer
    ({"x": 507.0, "y": [10.0, 100.0]}, "tek kapalı mahalin"),              # banyo ile yatak odasının duvarı boyunca
    ({"x": 381.5, "y": [261.0, 330.0]}, "bağlı uç bir duvara değmiyor"),   # odanın ortasında, iki ucu boşta
    ({"x": 380.0, "y": [198.25, 264.0]}, "aks üstünde değil"),
    ({"y": 449.25, "x": [507.0, 880.0]}, "değiyor ya da giriyor"),          # sağ dış duvarın gövdesine girer (geometri hakemi)
    ({"y": 449.25, "x": [507.0, 878.5]}, "değiyor ya da giriyor"),          # sağ dış duvarın iç yüzüne değer
])
def test_hatali_giris(duvar, mesaj):
    with pytest.raises(G.IsEmriHatasi, match=mesaj):
        G.kur(_ie(EV_52, duvar))


def test_tam_izgara_hata():
    ie = _ie(EV_52, DUVAR_52)
    ie["yapi"]["dizilim"]["hiza"] = "tam_izgara"
    with pytest.raises(G.IsEmriHatasi, match="tam_izgara"):
        G.kur(ie)


def test_58_l_kosesi_t_olur():
    """58 m²: banyonun sağ duvarı aynı hatta sürer; banyonun alt duvarıyla L köşesi T olur (köşe parçası −1, H +1). Onaylı görseldeki gibi."""
    once, sonra = G.kur(_ie(EV_58)), G.kur(_ie(EV_58, DUVAR_58))
    assert len(sonra.koseler) == len(once.koseler) - 1
    assert len(sonra.h_baglantilar) == len(once.h_baglantilar) + 1


def test_liste_yarim_pano_ve_birlesimler(tmp_path):
    """Liste: 60'lık yarım pano +1; T pano ekine geldiği için o ekteki H 3'lü H olur; serbest uçta çektirme U'su (İE-27)."""
    from motor import prefabrik_liste as PL

    def adetler(ie):
        j = PL.is_emrinden(ie)
        return {(r["grup"], r["kalem"], r["olcu"]): r["adet"] for r in j["satirlar"]}
    once, sonra = adetler(_ie(EV_52)), adetler(_ie(EV_52, DUVAR_52))
    fark = {k: (once.get(k), sonra.get(k)) for k in set(once) | set(sonra) if once.get(k) != sonra.get(k)}
    assert fark[("1001", "60'lık yapıştırma dolu pano", "60 × 625 × 2500")] == (2, 3)
    assert fark[("1002", "3'lü H standart 60 (iç T)", "L 2500")] == (2, 3)
    assert fark[("1002", "H standart 60 (iç pano eki)", "60 × 60 × 2500")] == (6, 5)
    cu = [k for k in fark if k[1].startswith("Çektirme U")]
    assert len(cu) == 1 and fark[cu[0]][1] == (fark[cu[0]][0] or 0) + 1


def test_on_onay_cizimi_dogrulamadan_gecer(tmp_path):
    from motor import dxf_out
    r = dxf_out.uret(_ie(EV_52, DUVAR_52), tmp_path)
    assert r["validation_passed"] is True
    assert r["pdf"]
