"""D-143 · BK-68 · Montaj paftasında damlalık (kart CK-08).

Lokman, 20 Kasım 2026 19:47:50: "damlalık montaj paftasında görünmüyor"; eskiz kartı 20:01:45 "Eskizdeki gibi". Damlalık (Z) sundurma
panelinin (teras paneli, D-52) duvar kenarında, duvarla trapez sacın birleşiminde (D-133). Kart modeli damlalığı teras başına bir parça
kurar; sayı liste üretecinin D-57 yolu (terasların enlerinin toplamı ÷ 2,8, yukarı) ve listeyle aynı. Montaj paftasının 7. sayfasında
damlalık, parçaları (D1, D2…), panelin soluk kesik çerçevesi ve lejant satırı; teras panelsiz evde sayfa ve özet aynen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret  # noqa: E402
from motor import kart_model as KM  # noqa: E402
from motor.yerlesim import cizim  # noqa: E402
from motor.yerlesim import kenar as KE  # noqa: E402

# İş Emri → (teras, duvar, hat boyu cm, damlalığın dış yüzü cm, stok = liste)
EVLER = {"PA43": (KOK / "is_emri" / "adaylar" / "PA43.json", [("VERANDA", "sag", 453.2)], 2),           # 92 m², sağda teras paneli
         "AP26": (KOK / "testler" / "kor" / "projeler" / "AP26" / "is_emri.json",
                  [("ÖN TERAS", "on", 479.58), ("ARKA TERAS", "arka", 438.58)], 4)}                     # D-57: 918,16 ÷ 280 → 4


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evler(tmp_path_factory):
    out = {}
    for ad, (yol, _h, _n) in EVLER.items():
        d = tmp_path_factory.mktemp(f"d143_{ad}")
        assert KM.main([str(yol), str(d), "--kod", ad]) in (0, 1)       # 1: teras panelinin kendisi "kural yok" (K5b), aynen
        out[ad] = {"klasor": d, "say": _oku(d / f"{ad}_kart_sayim.json"), "ie": _oku(yol)}
    return out


def test_kart_ve_kural():
    kart = next(k for k in _oku(KM.KARTLAR)["kartlar"] if k["kod"] == "CK-08")
    assert kart["yerlesim"] == {"kural": KE.DAMLALIK, "parca": "damlalik", "sinif": "IfcCovering"}
    assert kart["liste"]["satirlar"] == ["Damlalık"] and kart["sayim"] == "boy_kesim" and kart["kaynak"]["durum"] == "lokman"
    assert _oku(KOK / "testler" / "kimlik" / "veri" / "kart_kodlari.json")["kodlar"]["CK-08"] == kart["ad"]
    K = _oku(KM.YERLESIM)["kurallar"][KE.DAMLALIK]
    assert K["parca_boyu"] == {"okunan": "kurallar/liste/prefabrik.json › kurallar.teras_damlaligi.parca_boyu_m"}
    assert K["yontem"]["deger"] == "toplam" and K["kesit"]["durum"] == "varsayim" and "D-143" in K["kaynak"]
    assert KE.DAMLALIK not in KE.KENAR                                   # K3b'nin yedi parçası aynen


@pytest.mark.parametrize("ad", list(EVLER))
def test_sayi_liste_ile_ayni(evler, ad):
    say = evler[ad]["say"]
    _yol, hatlar, n = EVLER[ad]
    parcalar = [p for p in say["kenar"]["parcalar"] if p["kart"] == "CK-08"]
    assert sorted((p["bilgi"]["Cati"], p["bilgi"]["Duvar"], p["boy_cm"]) for p in parcalar) == sorted(hatlar)
    assert all(p["bilgi"]["ParcaBoyu_cm"] == 280 for p in parcalar)
    assert say["kesim_plani"]["CK-08"]["stok"] == say["kenar"]["liste"]["CK-08"] == n


def test_damlalik_duvarin_dis_yuzunde_sacin_ustunde(evler):
    """PA-43: teras sağda, duvarın dış yüzü x = 860; damlalık 860'tan dışarı, panelin duvardaki üstünün (240) üstünde, panelin eni boyunca."""
    f = ifcopenshell.open(str(evler["PA43"]["klasor"] / "PA43_model.ifc"))
    kutu = KM._Kutular()
    dl = [e for e in f.by_type("IfcCovering") if ue.get_psets(e).get(KM.PARCA_SETI, {}).get("KartKodu") == "CK-08"]
    assert [e.Name for e in dl] == ["DAMLALIK_001"]
    (x0, y0, z0), (x1, y1, z1) = kutu(dl[0])
    assert (x0, round(x1, 2)) == pytest.approx((860.0, 864.0), abs=0.01)
    assert (y0, y1) == pytest.approx((0.0, 453.2), abs=0.01)
    plan = ifc_uret.hazirla(evler["PA43"]["ie"])
    assert z0 > plan["dis_verandalar"][0]["cati"]["mahya_kotu"] and z1 - z0 < 20          # sacın üstünde; kesit gösterim (sayı çıkmaz)


def test_yedinci_sayfa(evler):
    import pymupdf
    for ad, (_y, hatlar, n) in EVLER.items():
        metin = " ".join(pymupdf.open(evler[ad]["klasor"] / f"{ad}_yerlesim_planlari.pdf")[6].get_text().split())
        assert f"CK-08 Damlalık L 2800 (Z) model {n} boy · liste {n}" in metin, ad
        assert metin.count("(yer göstermek için)") == len(hatlar) and "D1 · 280" in metin and f"D{n} ·" in metin
        assert "silikonize mastik" in metin


def test_teras_panelsiz_evde_aynen(tmp_path):
    """Teras panelsiz evde damlalık parçası, kesim satırı, liste satırı ve lejant yok (PK-01)."""
    assert KM.main([str(KOK / "testler" / "motor" / "veri" / "PK01.json"), str(tmp_path), "--kod", "PK01"]) == 0
    say = _oku(tmp_path / "PK01_kart_sayim.json")
    assert "CK-08" not in say["kesim_plani"] and "CK-08" not in say["kenar"]["liste"] and KE.DAMLALIK not in say["kenar"]["degerler"]
    assert not any(p["kart"] == "CK-08" for p in say["kenar"]["parcalar"])
    import pymupdf
    metin = " ".join(pymupdf.open(tmp_path / "PK01_yerlesim_planlari.pdf")[6].get_text().split())
    assert "CK-08" not in metin and "damlalık" not in metin.lower()


def test_cizim_renk_ve_sayfa():
    assert "CK-08" in cizim.KENAR_RENK and "CK-08" in cizim.YALNIZ_VARSA and "DAMLALIK_" in cizim.SAYFA[7][1]
