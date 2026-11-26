"""D-156 · köşe kırmasında kısa makasların yeri paftadan (`cati.mahal_catilari[].kisa_makas_yerleri_cm`), yalnız yazıldığı evde (BK-81).

Lokman, 26 Kasım 2026 10:01:13 UTC (rehber taslağının veranda makasına): "burada bir kesişim sorunu var nasıl otutturdun makasları";
10:19:48 UTC kart "63 m2 evde 4 veranda makası hangi yerlerde dursun?": "A: Paftadaki yerlerde".
Ev: Mehmet Kapaklı Tek 63 m² (TK-11). Eşit aralık kuralı ilk kısa makası cumbanın arka duvar hizasına (391,5) koyar; iki cumba makasının
saçağa uzanan uçları (421,5'e kadar) o makasın içinden geçer. Evin montaj paftasında kısa makaslar 425,5 / 512,75 / 637,75 / 762,75'tedir.

Kural:
- anahtar yoksa çatı tanımı aynen (eşit aralık; AP-03, M-07);
- anahtar kısa makasları yazılan yerlere koyar; sayı, boy, çapraz makas, yükleme listesi ve çatının düzlemleri aynı kalır;
- yanlış sayı, sıra, aralık, yan dışı yer, sayı olmayan değer ve köşe kırması olmayan mahal çatısı hata (yok sayılmaz).

Hedef örnek değildir: evin İş Emri'ne anahtar ve rehberin hedef örneği rehber işinde, Lokman'ın onayıyla girer (D-28 madde 2).
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

R02 = KOK / "testler" / "teklif_formu" / "TK11_r02" / "is_emri.json"      # onaylı teklifin İş Emri'si (14 makas; anahtar yok)
ESIT = [391.5, 502.56, 613.62, 724.69]                                    # kuralın yerleri (eşit aralık)
PAFTA = [425.5, 512.75, 637.75, 762.75]                                   # evin montaj paftası (makas ve dere yerleşim planı)
YARI_KALINLIK = 4.0                                                       # makas çubuğu C 80 × 45: sırt 80 mm, makas düzlemine dik


def _oku() -> dict:
    return json.loads(R02.read_text(encoding="utf-8"))


def _anahtarli(yerler=PAFTA, **ek) -> dict:
    ie = _oku()
    ie["cati"]["mahal_catilari"][0]["kisa_makas_yerleri_cm"] = yerler
    ie["cati"]["mahal_catilari"][0].update(ek)
    return ie


def _tanim(ie: dict) -> dict:
    return sunum.cati_tanimi(G.kur(copy.deepcopy(ie)), ie)


def _kisa(t: dict) -> list[float]:
    return [m["konum"] for m in t["mahal_catilari"][0]["makaslar"] if m["rol"] == "kisa"]


def test_anahtarsiz_cati_tanimi_aynen():
    """Anahtar yoksa kısa makaslar eşit aralıkta; tanıma yeni alan girmez."""
    t = _tanim(_oku())
    assert _kisa(t) == ESIT
    assert "kisa_makas_yerleri" not in t["mahal_catilari"][0]


def test_anahtarli_kisa_makaslar_paftadaki_yerlerde():
    """Anahtarla dört kısa makas paftadaki yerlerde; rol, boy, çapraz makas ve tanımın geri kalanı aynı."""
    t0, t1 = _tanim(_oku()), _tanim(_anahtarli())
    assert _kisa(t1) == PAFTA
    m0, m1 = t0["mahal_catilari"][0], t1["mahal_catilari"][0]
    assert [(m["rol"], m["plan_boy_cm"]) for m in m1["makaslar"]] == [(m["rol"], m["plan_boy_cm"]) for m in m0["makaslar"]]
    assert m1["makaslar"][-1] == m0["makaslar"][-1] and m1["makaslar"][-1]["rol"] == "capraz"       # çapraz makas kırma hattında kalır
    assert m1.pop("kisa_makas_yerleri") == PAFTA
    for q, v in zip(m1["makaslar"], ESIT):
        q["konum"] = v
    assert json.dumps(t0, sort_keys=True, default=str) == json.dumps(t1, sort_keys=True, default=str)     # başka hiçbir şey değişmez


def test_cumba_makaslarinin_ucu_ilk_kisa_makasa_girmez():
    """Kesişimin nedeni ve çözümü: cumba makaslarının ucu cumbanın arka saçağına (421,5) uzanır. Eşit aralıkta ilk kısa makas o ucun
    içindedir (391,5); paftadaki yerde makasın ön yüzü (425,5 − 4) ucun bittiği yerdedir, makaslar değer ama birbirine girmez."""
    t0, t1 = _tanim(_oku()), _tanim(_anahtarli())
    cumba = next(q for q in t1["parcalar"] if q["rol"] == "cumba")
    uc = cumba["b"][1] + float(_oku()["cati"]["sacak_cm"])                 # cumba makasının arka ucu (duvar + saçak)
    assert uc == 421.5
    assert _kisa(t0)[0] + YARI_KALINLIK < uc                              # eşit aralık: kısa makas bütünüyle cumba makaslarının yolunda
    assert _kisa(t1)[0] - YARI_KALINLIK >= uc - 0.01                      # pafta: kısa makasın ön yüzü ucun bittiği yerde


def test_liste_aynen():
    """Yükleme listesi anahtarla da aynıdır (136 satır; 4 kısa makas, boy 155,5): onaylı teklif değişmez."""
    L0, L1 = PL.is_emrinden(_oku()), PL.is_emrinden(_anahtarli())
    for L in (L0, L1):
        L.pop("uretildi", None)
    assert len(L0["satirlar"]) == 136 and L0["girdi_ozeti"]["makas"] == 14
    assert json.dumps(L0, sort_keys=True, ensure_ascii=False, default=str) == json.dumps(L1, sort_keys=True, ensure_ascii=False, default=str)


@pytest.mark.parametrize("yerler, parca", [
    ([425.5, 512.75, 637.75], "kuralın kısa makas sayısı 4"),                      # sayı değişmez (liste aynı kalır)
    ([425.5, 512.75, 637.75, 700.0, 762.75], "kuralın kısa makas sayısı 4"),
    ([425.5, 637.75, 512.75, 762.75], "artan sırada"),
    ([425.5, 425.5, 637.75, 762.75], "artan sırada"),
    ([300.0, 512.75, 637.75, 762.75], "mahalin yanı içinde"),                       # mahalin önünde (yan 391,5–835,75)
    ([425.5, 512.75, 637.75, 835.75], "mahalin yanı içinde"),                       # çapraz makasın ucunda kısa makas olmaz
    ([425.5, 512.75, 600.0, 762.75], "125.5 cm'yi aşıyor"),                         # 600 → 762,75 = 162,75
    ([391.5, 425.5, 512.75, 637.75], "125.5 cm'yi aşıyor"),                         # son kısa makastan çapraz makasa 198
])
def test_yanlis_yerler_hata(yerler, parca):
    with pytest.raises(CP.PrefabrikCatiHatasi, match="kisa_makas_yerleri_cm") as e:
        _tanim(_anahtarli(yerler))
    assert parca in str(e.value)


@pytest.mark.parametrize("deger", [True, 425.5, "425,5", [], [425.5, "512,75", 637.75, 762.75], [425.5, True, 637.75, 762.75], None])
def test_sayi_listesi_olmayan_deger_hata(deger):
    """Anahtar yazıldıysa sayı listesidir; null da yok sayılmaz (yazılmayacaksa anahtar yazılmaz)."""
    with pytest.raises(CP.PrefabrikCatiHatasi, match="kisa_makas_yerleri_cm sayı listesi"):
        _tanim(_anahtarli(deger))


def test_tek_yon_mahal_catisinda_hata():
    """Tek eğimli panel çatıda makas yoktur; anahtar yalnız köşe kırmasında yazılır."""
    ie = _anahtarli()
    mc = ie["cati"]["mahal_catilari"][0]
    mc.pop("yuz_egimi_yuzde")
    mc.update(tip="tek_yon", egim_yuzde=10)
    with pytest.raises(CP.PrefabrikCatiHatasi, match="yalnız köşe kırmasında"):
        _tanim(ie)


def test_liste_ve_3d_model_ayni_hatayi_verir():
    """Yanlış yer listeyi ve 3D modeli de durdurur (çatı tanımı tek kaynak)."""
    from motor import ifc_uret
    ie = _anahtarli([425.5, 512.75, 637.75])
    with pytest.raises(PL.ListeYazilmaz, match="kisa_makas_yerleri_cm"):
        PL.is_emrinden(copy.deepcopy(ie))
    with pytest.raises(G.IsEmriHatasi, match="kisa_makas_yerleri_cm"):
        ifc_uret.hazirla(copy.deepcopy(ie))


def test_3d_model_kisa_makaslar_paftadaki_yerlerde(tmp_path):
    """3D model çatı tanımını okur: 14 makas; kısa makaslar paftadaki yerlerde, çapraz makas yerinde."""
    from motor import ifc_uret
    oz = ifc_uret.uret(_anahtarli(), tmp_path / "ev.ifc")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    mk = oz["cati"]["makaslar"]
    assert oz["cati"]["makas"] == len(mk) == 14
    assert [m["konum_cm"] for m in mk if m["rol"] == "kisa"] == PAFTA
    assert [m["konum_cm"] for m in mk if m["rol"] == "capraz"] == [835.75]
