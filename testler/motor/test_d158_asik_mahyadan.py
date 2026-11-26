"""D-158 · çok yüzlü çatıda aşık sıraları mahyadan (`cati.asik_siralari: "mahyadan"`), yalnız yazıldığı evde (BK-83).

Lokman, 26 Kasım 2026 23:34:15 UTC, kart "Cumbalı ve verandalı çatıda aşık sıraları nereden sayılsın?": "A: Yalnız bu evde mahyadan".
Ev: Mehmet Kapaklı Tek 63 m² (TK-11). Motor "Mahyadan 60" kuralını (karar C, D-39) yalnız düz beşikte uygular; cumbalı ve verandalı
çatıda kitabın çok düzlemli kuralı sıraları saçaktan sayar. Evin montaj paftasının aşık yerleşim planı sıraları mahyadan sayar.

Kural:
- anahtar yoksa çatı tanımı, sıralar ve liste aynen (saçaktan; M-07 evleri dahil);
- anahtar her yüzün sıralarını yüzün en üst kenarından saydırır: karar C'nin sayımı (`prefabrik_liste.asik_mesafeleri`), saçak eşiği
  liste kuralından (`asik_sacak_esigi_m`); saçak çizgisinde eni olmayan yüzde (alt kenarı dere) saçak sırası yok;
- liste, kart modeli, montaj paftası ve rehber aynı sıraları okur (`cati_genel.cati_kur`); listenin aşık adedi bu evde aynı kalır (41);
- başka değer, düz beşik ve beşik dışı tip hata (yok sayılmaz, K21).

Beklenen sıralar paftadan (`testler/motor/veri/D158_asik_mahyadan_beklenen.json`). Evin İş Emri'ne anahtar ve rehberin hedef örneği
rehber işinde, Lokman'ın onayıyla girer (D-28 madde 2); burada anahtar onaylı teklifin İş Emri'ne yalnız bellekte eklenir.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP  # noqa: E402
from motor import geometry as G  # noqa: E402
from motor import ifc_uret  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor import sunum  # noqa: E402
from motor.genel import cati_genel  # noqa: E402

R02 = KOK / "testler" / "teklif_formu" / "TK11_r02" / "is_emri.json"      # onaylı teklifin İş Emri'si (anahtar yok)
HEDEF = json.loads((KOK / "testler" / "motor" / "veri" / "D158_asik_mahyadan_beklenen.json").read_text(encoding="utf-8"))
PAY = HEDEF["tolerans_cm"]


def _oku(yol: Path = R02) -> dict:
    d = json.loads(yol.read_text(encoding="utf-8"))
    return d.get("is_emri", d) if isinstance(d.get("is_emri"), dict) else d


def _anahtarli(deger="mahyadan", yol: Path = R02) -> dict:
    ie = _oku(yol)
    ie.setdefault("cati", {})["asik_siralari"] = deger
    return ie


def _tanim(ie: dict) -> dict:
    return sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie)


def _siralar(ie: dict) -> dict[str, list[tuple[float, float, str]]]:
    """Yüz adı → [(üst kenardan eğik uzaklık, boy, tür)], üstten alta."""
    ck = cati_genel.cati_kur(_tanim(ie), PL.kurallari_oku()["ortak"])
    out = {}
    for dz in ck["duzlemler"]:
        t1 = (dz.get("acilim_karkas") or dz["acilim"]).bounds[3]
        out[dz["ad"]] = sorted(((t1 - s["t"], s["boy"], s["tur"]) for s in ck["asik"][dz["ad"]]), key=lambda r: r[0])
    return out


def test_anahtarsiz_cati_aynen():
    """Anahtar yoksa tanıma yeni alan girmez; sıralar saçaktan (kitabın çok düzlemli kuralı): 27 sıra, cumba mahyasında kısa sıra."""
    t = _tanim(_oku())
    assert "asik_siralari" not in t
    sr = _siralar(_oku())
    assert sum(len(v) for v in sr.values()) == HEDEF["anahtarsiz"]["sira"]
    assert [r[2] for r in sr["ana çatı ön"]].count("ust_sira") == 2          # mahyada ve cumbanın mahyasında


def test_tanim_kurali_tasir_cati_ayni():
    """Anahtar çatının düzlemlerini, kalkanlarını, makaslarını değiştirmez; tanıma yalnız `asik_siralari` girer (saçak eşiği liste kuralından)."""
    a, b = _tanim(_oku()), _tanim(_anahtarli())
    esik = PL.kurallari_oku()["prefabrik"]["kurallar"]["asik_sacak_esigi_m"]["deger"] * 100
    assert b["asik_siralari"] == {"baslangic": "mahyadan", "sacak_esigi_cm": esik}
    assert json.dumps({k: v for k, v in b.items() if k != "asik_siralari"}, sort_keys=True, default=str) == json.dumps(a, sort_keys=True, default=str)


def test_siralar_paftadaki_gibi():
    """Her yüzde sıralar üst kenardan 60 arayla ve saçakta; boylar paftanın aşık yerleşim planındaki boylar (± 0,5 cm)."""
    sr = _siralar(_anahtarli())
    assert set(sr) == set(HEDEF["yuzler"])
    for ad, h in HEDEF["yuzler"].items():
        r = sr[ad]
        assert all(tur == "sira" for _, _, tur in r), (ad, r)                # üst kenarda ayrı sıra yok: ilk sıra zaten orada
        n = len(h["mahyadan_cm"])
        assert [round(m, 2) for m, _, _ in r[:n]] == [float(m) for m in h["mahyadan_cm"]], ad
        assert len(r) == n + (1 if h["sacak_sirasi"] else 0), (ad, r)
        if h["sacak_sirasi"]:
            assert r[-1][0] - r[-2][0] >= 30.0 - 1e-6                        # karar C: saçağa 30 cm'den az kalan sıra yok
        assert [b for _, b, _ in r] == pytest.approx(h["boy_cm"], abs=PAY), ad
    assert sum(len(v) for v in sr.values()) == HEDEF["toplam"]["sira"]


def test_dikdortgen_yuzde_karar_c_ile_ayni_sayim():
    """Dikdörtgen yüzde sıralar düz beşiğin karar C sayımıyla aynı (`asik_mesafeleri`): dört aşık planının yedi çatısı ve uç değerler."""
    for egik in (347.5, 434.9, 308.6, 439.9, 207.2, 444.8, 237.7, 471.46, 158.58, 120.0, 89.99, 60.0, 45.0, 25.0):
        dz = {"acilim": Polygon([(0, 0), (500, 0), (500, egik), (0, egik)])}
        r = cati_genel.asik_siralari(dz, 60.0, 30.0, mahyadan_sacak_esigi=30.0)
        assert all(s["tur"] == "sira" and s["boy"] == pytest.approx(500.0) for s in r)
        assert sorted(egik - s["t"] for s in r) == pytest.approx(PL.asik_mesafeleri(egik, 60.0, 30.0)), egik


def test_alt_kenari_dere_olan_yuzde_sacak_sirasi_yok_sira_dusmez():
    """Saçak çizgisinde eni olmayan yüzde (alt kenar dere) saçak sırası yoktur; saçağa 30 cm'den az kalan sıra da yerinde kalır."""
    dz = {"acilim": Polygon([(0, 20), (100, 0), (100, 200), (0, 200)])}        # üst kenar 200'de; alt kenar eğik (dere), saçakta en yok
    r = sorted(200 - s["t"] for s in cati_genel.asik_siralari(dz, 60.0, 30.0, mahyadan_sacak_esigi=30.0))
    assert r == pytest.approx([0.0, 60.0, 120.0, 180.0])                      # 180: saçağa 20 cm; saçak sırası yok, sıra düşmez


def test_liste_asik_adedi_ayni():
    """Liste: 136 satır; yalnız aşık satırının dayanağı ve hesap yazısı değişir, adet ve aday aynı (41); özet aynı."""
    a, b = PL.is_emrinden(_oku()), PL.is_emrinden(_anahtarli())
    assert len(a["satirlar"]) == len(b["satirlar"]) == HEDEF["liste"]["satir"]
    assert a["ozet"] == b["ozet"]
    fark = [(x, y) for x, y in zip(a["satirlar"], b["satirlar"]) if x != y]
    assert len(fark) == 1
    x, y = fark[0]
    assert x["kalem"] == y["kalem"] == "Aşık" and y["olcu"] == HEDEF["liste"]["asik_olcu"]
    assert x["adet"] == y["adet"] == HEDEF["liste"]["asik_adedi"] and x["aday"] == y["aday"]
    assert {k for k in x if x[k] != y[k]} == {"dayanak", "formul"}
    assert "saçaktan" in x["formul"].split("kubbe")[0] and "27 sıra" in x["formul"]
    assert "26 sıra" in y["formul"] and "D-158" in y["formul"] and y["dayanak"] == "Kural (karar C)"


@pytest.fixture(scope="module")
def kart(tmp_path_factory):
    """Kart modeli (montaj paftasının ve rehberin okuduğu aşık parçaları) anahtarlı İş Emri'yle."""
    from motor import kart_model
    yol = tmp_path_factory.mktemp("d158")
    kart_model.uret(_anahtarli(), yol, "TK11")
    return json.loads((yol / "TK11_kart_sayim.json").read_text(encoding="utf-8"))


def test_kart_modeli_paftadaki_parca_sayisi(kart):
    """Kart modelinde aşık 48 parça, 156,7 m (paftanın aşık yerleşim planı); sıralar çatı tanımından, 26 sıra."""
    k = next(x for x in kart["kartlar"] if x["kod"] == "AS-01")
    assert k["adet"] == HEDEF["toplam"]["parca"]
    assert k["metre"] == pytest.approx(HEDEF["toplam"]["metre"], abs=0.05)
    asik = [p for p in kart["yerlesim"]["parcalar"] if p.get("kart") == "AS-01"]
    assert len(asik) == HEDEF["toplam"]["parca"]
    assert len({(p["bilgi"]["Cati"], p["bilgi"]["Sira"]) for p in asik}) == HEDEF["toplam"]["sira"]


@pytest.mark.parametrize("deger", ["sacaktan", "mahya", True, 60, ""])
def test_baska_deger_hata(deger):
    with pytest.raises(CP.PrefabrikCatiHatasi, match="asik_siralari"):
        _tanim(_anahtarli(deger))


@pytest.mark.parametrize("yol", ["is_emri/P6001_2plus1_6x6.json", "is_emri/P8501_r05.json", "testler/motor/veri/BK64_PA17_kirma.json"])
def test_baska_catida_yok_sayilmaz(yol):
    """Düz beşikte (sıralar zaten mahyadan, karar C), beşik + cumbada ve kırmada anahtar hata verir: çizim, liste ve 3D model."""
    ie = _anahtarli(yol=KOK / yol)
    with pytest.raises(CP.PrefabrikCatiHatasi, match="asik_siralari"):
        sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie) or CP.cati(G.kur(copy.deepcopy(ie)), ie)
    with pytest.raises((CP.PrefabrikCatiHatasi, PL.ListeYazilmaz), match="asik_siralari"):
        PL.is_emrinden(copy.deepcopy(ie))
    with pytest.raises(CP.PrefabrikCatiHatasi, match="asik_siralari"):
        ifc_uret.hazirla(copy.deepcopy(ie))


def test_tanimda_taninmayan_kural_hata():
    """`cati_kur` tanımdaki kuralı tanımıyorsa sessizce saçaktan saymaz."""
    t = dict(_tanim(_anahtarli()), asik_siralari={"baslangic": "ortadan"})
    with pytest.raises(ValueError, match="asik_siralari"):
        cati_genel.cati_kur(t, PL.kurallari_oku()["ortak"])
