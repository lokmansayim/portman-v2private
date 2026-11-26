"""D-154 · cumbanın iç ucunda makas (`cati.cumba_ic_makasi`), yalnız yazıldığı evde (BK-79).

Lokman, 26 Kasım 2026 05:50:56 UTC: "sen motora uy yerleşim yerlerinde eşit aralıklara koymuşsa o şekilde kalsın"; 05:52:33 UTC:
"cumbada 2 makas gördüm ana makasın tam önünde 1 tane daha makas var"; 05:56:53 UTC kart "B: Listeye 1 cumba makası ekle".
Ev: Mehmet Kapaklı Tek 63 m² (TK-11); montaj paftasında 14 makas, Motor ve mühürlü liste 13 sayıyordu.

Kural:
- anahtar yoksa çatı tanımı ve liste aynen (cumbanın iç ucunda makas yok; D-44, M-07);
- `cati.cumba_ic_makasi: true` cumbanın iç ucuna, ana çatının kalkan duvarının dış yüzüne bir cumba makası daha koyar; öteki makaslar
  Motor'un yerinde kalır; yükleme listesinde yalnız "Cumba makası" satırı 1 → 2 olur;
- başka değer, cumbasız çatı ve yan yana cumbalar hata (yok sayılmaz).

Hedef örnek değildir: yeni teklif formu Lokman onaylayınca ayrıca dondurulur (D-28 madde 2).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP  # noqa: E402
from motor import geometry as G  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor import sunum  # noqa: E402

R01 = KOK / "testler" / "teklif_formu" / "TK11" / "is_emri.json"          # mühürlü teklifin İş Emri'si (13 makas)
R02 = KOK / "testler" / "teklif_formu" / "TK11_r02" / "is_emri.json"      # r02: yalnız anahtar ve revizyon
ANA = [5.0, 67.75, 193.25, 318.75, 444.25, 569.75, 632.5]
KISA = [391.5, 502.56, 613.62, 724.69]


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _tanim(ie: dict) -> dict:
    return sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie)


def _anahtarli(ie: dict, deger=True) -> dict:
    ie = copy.deepcopy(ie)
    ie.setdefault("cati", {})["cumba_ic_makasi"] = deger
    return ie


@pytest.fixture(scope="module")
def listeler():
    return PL.is_emrinden(_oku(R01)), PL.is_emrinden(_oku(R02))


def test_r02_is_emri_yalniz_anahtar_ve_revizyon():
    """r02 İş Emri mühürlü r01'in aynısıdır; tek fark revizyon ve çatıdaki anahtar."""
    bekle = _anahtarli(_oku(R01))
    bekle["revizyon"] = 2
    assert _oku(R02) == bekle


def test_anahtarsiz_cati_tanimi_aynen():
    """Anahtar yoksa cumbada tek makas (dış uçta baş makas); toplam 13."""
    t = _tanim(_oku(R01))
    ana, cumba = (next(q for q in t["parcalar"] if q["rol"] == r) for r in ("ana", "cumba"))
    assert [m["konum"] for m in ana["makaslar"]] == ANA
    assert cumba["makaslar"] == [{"konum": 758.0, "rol": "bas"}]
    assert len(ana["makaslar"]) + len(cumba["makaslar"]) + len(t["mahal_catilari"][0]["makaslar"]) == 13


def test_anahtarli_cati_tanimi_iceride_bir_makas_daha():
    """Anahtarla cumbanın iç ucunda (ana çatının kalkan duvarının dış yüzü 637,5; eksen 642,5) bir makas daha; gerisi aynı."""
    t0, t1 = _tanim(_oku(R01)), _tanim(_oku(R02))
    cumba = next(q for q in t1["parcalar"] if q["rol"] == "cumba")
    assert cumba["a"][0] == 637.5
    assert cumba["makaslar"] == [{"konum": 642.5, "rol": "orta", "ic_uc": True}, {"konum": 758.0, "rol": "bas"}]
    ana = next(q for q in t1["parcalar"] if q["rol"] == "ana")
    assert [m["konum"] for m in ana["makaslar"]] == ANA                              # ana makaslar Motor'un yerinde
    mh = t1["mahal_catilari"][0]["makaslar"]
    assert [m["konum"] for m in mh if m["rol"] == "kisa"] == KISA                    # kısa makaslar eşit aralıkta (Lokman 05:50:56)
    assert [m["rol"] for m in mh] == ["kisa"] * 4 + ["capraz"]
    next(q for q in t1["parcalar"] if q["rol"] == "cumba")["makaslar"] = [{"konum": 758.0, "rol": "bas"}]
    assert json.dumps(t0, sort_keys=True, default=str) == json.dumps(t1, sort_keys=True, default=str)     # başka hiçbir şey değişmez


def test_listede_yalniz_cumba_makasi_degisir(listeler):
    """Yükleme listesi: 136 satır; yalnız 'Cumba makası · sağ cumba' 1 → 2; toplam makas 13 → 14."""
    L0, L1 = listeler
    assert (L0["girdi_ozeti"]["makas"], L1["girdi_ozeti"]["makas"]) == (13, 14)
    assert len(L0["satirlar"]) == len(L1["satirlar"]) == 136
    assert L1["ozet"]["kural_yok"] == 0
    fark = [(a, b) for a, b in zip(L0["satirlar"], L1["satirlar"]) if a != b]
    assert len(fark) == 1
    a, b = fark[0]
    assert a["kalem"] == b["kalem"] == "Cumba makası · sağ cumba" and b["olcu"] == "L 4515"
    assert (a["adet"], b["adet"]) == (1, 2)
    assert {k for k in a if a[k] != b[k]} == {"adet", "formul"}
    assert "iç uçta 1" in b["formul"] and "iç uçta" not in a["formul"]


@pytest.mark.parametrize("deger", [False, 1, "evet", None])
def test_baska_deger_hata(deger):
    """Anahtar yalnız true olur; false, sayı ya da yazı yok sayılmaz. None (yazılmamış gibi) anahtarsızla aynıdır."""
    ie = _anahtarli(_oku(R01), deger)
    if deger is None:
        assert _tanim(ie) == _tanim(_oku(R01))
        return
    with pytest.raises(CP.PrefabrikCatiHatasi, match="cumba_ic_makasi"):
        _tanim(ie)


def test_cumbasiz_ve_yan_yana_cumbali_cati_hata():
    """Düz beşikte (cumba yok), yan yana cumbalarda ve beşik dışı çatıda anahtar hata verir (sessizce yok sayılmaz). Düz beşikte çatı
    tanımı kurulmaz; çizim, liste ve 3D model aynı hatayı verir (`cati_serit.ic_makas_denetle`)."""
    from motor import ifc_uret
    duz = _anahtarli(_oku(KOK / "is_emri" / "adaylar" / "PA06.json"))
    for yol in (_tanim, PL.is_emrinden, ifc_uret.hazirla):
        with pytest.raises(G.IsEmriHatasi, match="cumba_ic_makasi"):
            yol(copy.deepcopy(duz))
    PL.is_emrinden(_anahtarli(_oku(KOK / "is_emri" / "adaylar" / "PA06.json"), None))          # null yazılmamış gibidir
    ikiz = _anahtarli(_oku(KOK / "is_emri" / "adaylar" / "PA13.json"))
    with pytest.raises(CP.PrefabrikCatiHatasi, match="yan yana"):
        _tanim(ikiz)
    kirma = _anahtarli(_oku(KOK / "is_emri" / "adaylar" / "PA08.json"))
    with pytest.raises(CP.PrefabrikCatiHatasi, match="cumba_ic_makasi"):
        CP.cati(G.kur(copy.deepcopy(kirma)), kirma)
    with pytest.raises(PL.ListeYazilmaz, match="cumba_ic_makasi"):
        PL.is_emrinden(copy.deepcopy(kirma))
    with pytest.raises(G.IsEmriHatasi, match="cumba_ic_makasi"):
        ifc_uret.hazirla(copy.deepcopy(kirma))


def test_kart_modeli_ve_3d_model_14_makas(tmp_path):
    """Kart modeli ve 3D model çatı tanımını okur: cumba makası kartı 2, toplam 14 makas (7 ana + 2 cumba + 4 kısa + 1 çapraz)."""
    from motor import kart_model
    kart_model.uret(_oku(R02), tmp_path, "TK-11")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    s = json.loads((tmp_path / "TK-11_kart_sayim.json").read_text(encoding="utf-8"))
    adet = {k["kod"]: k["adet"] for k in s["kartlar"] if k["kod"].startswith("MA-")}
    assert adet == {"MA-01": 2, "MA-02": 5, "MA-03": 0, "MA-04": 2, "MA-05": 0, "MA-06": 4, "MA-07": 1}
    assert sum(1 for k in s["bilesen"] if k.startswith("MAKAS_") and "KUBBE" not in k) == 14
    assert not [k for k in s["kural_yok"] if k["parca"].startswith("MAKAS_") and "KUBBE" not in k["parca"]]     # her makas bir karta bağlı
