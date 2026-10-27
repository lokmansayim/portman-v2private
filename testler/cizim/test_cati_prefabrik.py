"""İE-17 · Prefabrik evin beşik dışı çatısı (`motor/cati_prefabrik.py`): genel motorun çatı üreticisi prefabrik değerleriyle.

Açılan evlerin İş Emri'leri `testler/cizim/evler/` altında (montaj paftasından okundu; kişi ve bayi adı yok). Burada sayılar paftanın
çatısıyla sabit: düzlem, vadi ve kalkan sayısı, eğim, mahya kotu, kırmanın uç yüzleri. Düzlemlerin saçaklı ayak izini boşluksuz ve
örtüşmesiz örtmesi `cati_uretici.denetle`'den. Beşik bugünkü kuralla (`sunum.cati_tanimi`) ve çeliğin çağrısı (mahya verilmeden) aynı.
"""
from __future__ import annotations
import collections
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import cati_prefabrik as CP, geometry as G, sablon_kopru as K, sunum  # noqa: E402
from motor.genel import cati_genel, cati_uretici as CU  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
VERI = KOK / "testler" / "motor" / "veri"


def _ie(ad: str) -> dict:
    return json.loads(((VERI if ad in ("PK01", "TK01") else EVLER) / f"{ad}.json").read_text(encoding="utf-8"))


def _cati(ie: dict) -> tuple[dict, tuple]:
    plan = G.kur(copy.deepcopy(ie))
    return CP.cati(plan, ie), tuple(float(v) for v in G.govde_kutusu(plan))


def _kenar(c: dict) -> collections.Counter:
    return collections.Counter(k["tur"] for k in cati_genel.cati_kur(c)["kenarlar"])


def test_ap13_besik_cumba():
    # paftada "Beşik + Cumba": ana mahya x boyunca (makaslar derinliği geçer), ön-sol yatak odasının üstünde çapraz cumba, 18,2°
    ie = _ie("AP13")
    c, kutu = _cati(ie)
    assert kutu == (0.0, 0.0, 763.0, 788.0)
    assert c["tip"] == "besik_cumba" and c["tip_adi"] == "beşik + cumba" and c["ust_pay"] == 14.0
    assert [d["ad"] for d in c["duzlemler"]] == ["ana güney", "ana kuzey", "cumba doğu", "cumba batı"]
    assert {d["egim"] for d in c["duzlemler"]} == {0.3288} and all("ust_pay" not in d for d in c["duzlemler"])
    assert [(k["ad"], k["aralik"]) for k in c["kalkanlar"]] == [("batı kalkanı", [0.0, 788.0]), ("doğu kalkanı", [0.0, 788.0]),
                                                                 ("cumbanın güney kalkanı", [0.0, 391.5])]
    assert _kenar(c) == {"alin": 6, "vadi": 2, "mahya": 2, "sacak": 2}
    assert CU.denetle(c, [list(kutu), [0.0, 0.0, 391.5, 0.0]]) == []
    # mahya kotu paftanın kesitiyle: duvar üstünden 149,4 (10 topuk + 424 × 0,3288); cumbanın mahyası 83,4 (burada cumba 5 cm geniş:
    # duvarı Motor'un ızgarasında, İş Emri'nin varsayımı; +0,8)
    kot = sorted({round(max(k["kot"]), 1) for k in cati_genel.cati_kur(c)["kenarlar"] if k["tur"] == "mahya"})
    assert kot == [pytest.approx(250 + 83.4 + 0.8, abs=0.1), pytest.approx(250 + 149.4, abs=0.1)]


def test_ap16_besik_cumba():
    c, kutu = _cati(_ie("AP16"))
    assert kutu == (0.0, 0.0, 763.0, 918.5)
    assert len(c["duzlemler"]) == 4 and len(c["kalkanlar"]) == 3 and _kenar(c)["vadi"] == 2
    assert {d["egim"] for d in c["duzlemler"]} == {0.3288}


def test_kirma_esit_egim():
    # PK-01'in gövdesi kırmayla: dört düzlem, kalkan yok, kırmalar 45° (genel.cati_kirma)
    ie = _ie("PK01")
    ie["cati"] = {**ie["cati"], "tip": "kirma"}
    c, _ = _cati(ie)
    assert c["tip"] == "kirma" and len(c["duzlemler"]) == 4 and c["kalkanlar"] == []
    assert {d["egim"] for d in c["duzlemler"]} == {0.33}
    assert set(_kenar(c)) == {"mahya", "sacak", "kirma"}


def test_ap01_kirma_farkli_uc_egimleri():
    # paftanın çatı şekli: ana yüzler %33, sol kırma yüzü %32,5, sağ %36,2; mahya x boyunca (uzun kenar 1400). Kırma çizgisi saçaklı köşeden
    # mahyanın ucuna: R = (500 + 30) × 0,33 = 174,9; solda 174,9 ÷ 0,325 = 538,2, sağda 174,9 ÷ 0,362 = 483,1 → mahya 1460 − 1021,3 = 438,7
    ie = _ie("AP01")
    c, kutu = _cati(ie)
    assert kutu == (0.0, 0.0, 1400.0, 1000.0)
    assert [(d["ad"], d["egim"]) for d in c["duzlemler"]] == [("güney", 0.33), ("kuzey", 0.33), ("batı", 0.325), ("doğu", 0.362)]
    assert c["kalkanlar"] == [] and CU.denetle(c, [list(kutu)]) == []
    ck = cati_genel.cati_kur(c)
    mahya = [k for k in ck["kenarlar"] if k["tur"] == "mahya"]
    assert len(mahya) == 1 and mahya[0]["plan_boy"] == pytest.approx(438.7, abs=0.1)
    assert max(mahya[0]["kot"]) == pytest.approx(250 + 10 + 174.9, abs=0.05)
    assert collections.Counter(k["tur"] for k in ck["kenarlar"]) == {"sacak": 4, "kirma": 4, "mahya": 1}
    # mahyanın uçları paftanın yazılı eğimleriyle (kodun değeri, paftanın ölçüsü değil): sol kırma duvardan 508,2'de (makas planında 509),
    # sağ 453,1'de (makas planında 459; paftanın %36,2'si ölçüyle %35,8 verir; fark İE-17 › Kaynak paftayla kıyas)
    xs = sorted(p[0] for k in mahya for p in (k["p"], k["q"]))
    assert xs == [pytest.approx(508.2, abs=0.1), pytest.approx(946.9, abs=0.1)]


def test_besik_bugunku_kuralla():
    ie = _ie("PK01")
    plan = G.kur(copy.deepcopy(ie))
    # beşikte köprünün düzlemleri `sunum.cati_tanimi`'ninkiler aynen (kalkanları köprü ekler; BK-14); `cati_prefabrik` çağrılmaz
    assert K.cati(plan, copy.deepcopy(ie))["duzlemler"] == sunum.cati_tanimi(plan, copy.deepcopy(ie))["duzlemler"]
    with pytest.raises(CP.PrefabrikCatiHatasi, match="besik"):
        CP.cati(plan, ie)


def test_celik_cagrisi_mahyasiz_ayni():
    # çelik tarafı mahya vermez: cumba ana gövdenin uzun kenarına bitişik olmalı (inceleme G5) kuralı aynen
    ayak = [[0, 0, 600, 1000], [200, 0, 400, 0]]                            # kısa kenara (güney) bitişik cumba
    with pytest.raises(CU.CatiHatasi, match="uzun kenarına"):
        CU.uret(ayak, "cumba", egim_yuzde=33)
    # İE-17: mahya verilirse ona paralel kenar geçerli (AP-13'te mahya kısa kenar boyunca)
    assert len(CU.uret(ayak, "cumba", mahya="x", egim_yuzde=33)["duzlemler"]) == 4
    with pytest.raises(CU.CatiHatasi, match="paralel kenara"):
        CU.uret(ayak, "cumba", mahya="y", egim_yuzde=33)


@pytest.mark.parametrize("degis, mesaj", [
    (lambda c: c.pop("egim_yuzde"), "paftadan yazılır"),
    (lambda c: c["cumbalar"].append(dict(c["cumbalar"][0])), "bir cumba yazılır"),
    (lambda c: c["cumbalar"][0].update(cikinti_cm=60), "çıkıntılı cumba"),
    (lambda c: c["cumbalar"][0].update(bit_cm=900), "cephe 763"),
    (lambda c: c["cumbalar"][0].update(cephe="sol", bit_cm=391.5), "paralel kenara"),
    (lambda c: c.update(tip="teras"), "prefabrik çatıda yok"),
    (lambda c: c["cumbalar"][0].update(egim_yuzde=44), "cumba eğimi ana çatıdan farklı \\(%44 ↔ %32,88\\)"),   # PK-03 gibi; kapsam dışı
    (lambda c: c["cumbalar"][0].update(renk="antrasit"), "cumbada tanınmayan alan: renk"),
    (lambda c: c.update(kirma_egimleri={"sol": 30, "sag": 30}), "beşik \\+ cumba çatıda tanınmayan alan: kirma_egimleri"),
])
def test_cumba_hatalari(degis, mesaj):
    # yanlış çatı çizilmez: eksik ya da desteklenmeyen değer hata verir, köprü durur
    ie = _ie("AP13")
    degis(ie["cati"])
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        _cati(ie)
    with pytest.raises(K.KopruHatasi):
        K.tanim(copy.deepcopy(ie))


def test_cumba_egimi_ana_catiyla_ayni_yazilabilir():
    ie = _ie("AP13")
    yaz = copy.deepcopy(ie)
    yaz["cati"]["cumbalar"][0]["egim_yuzde"] = 32.88
    assert _cati(yaz)[0] == _cati(ie)[0]


def test_kirma_tanimayan_alan_hata():
    # kırmaya yazılan cumba yok sayılmaz (dört düzlemli kırma sessizce çizilmez)
    ie = _ie("AP01")
    ie["cati"]["cumbalar"] = [{"cephe": "on", "bas_cm": 0, "bit_cm": 300, "cikinti_cm": 0}]
    with pytest.raises(CP.PrefabrikCatiHatasi, match="kırma çatıda tanınmayan alan: cumbalar"):
        _cati(ie)
    with pytest.raises(K.KopruHatasi, match="tanınmayan alan"):
        K.tanim(copy.deepcopy(ie))


@pytest.mark.parametrize("uc, mesaj", [({"on": 32.5, "arka": 36.2}, "sol, sag için"), ({"sol": 5, "sag": 36.2}, "aralık dışı"),
                                       ({"sol": 10, "sag": 10}, "mahya")])
def test_kirma_uc_egimi_hatalari(uc, mesaj):
    ie = _ie("AP01")
    ie["cati"]["kirma_egimleri"] = uc
    with pytest.raises(CP.PrefabrikCatiHatasi, match=mesaj):
        _cati(ie)


def test_liste_ve_perspektif_frenleri(tmp_path, capsys):
    # İE-17 PR-1: beşik dışı ana çatının yükleme listesi ve perspektifi yazılmaz; beşik kuralıyla yanlış sayı ya da yanlış çatı çıkmaz (A4, A5
    # PR-1b). Motor'un IFC'si ve `model_motor` bugünkü gibi (çatı beşik kurulur): İE-15'in kimlik akışı bunu bilir, beşik dışında çatı
    # katmanları "kural yok" ve komut 1 döner (`testler/kimlik`: kırma çatı vakaları)
    from motor import prefabrik_liste as PL
    for ad in ("AP13", "AP01"):
        (tmp_path / f"{ad}.json").write_text(json.dumps(_ie(ad), ensure_ascii=False), encoding="utf-8")
        assert PL.main([str(tmp_path / f"{ad}.json"), str(tmp_path / ad)]) == 1 and not (tmp_path / ad).exists()
        assert "liste yazılmaz" in capsys.readouterr().err
        assert sunum.perspektif_uret(_ie(ad), tmp_path, ad)["durum"] == "ÇİZİLEMEDİ"
    assert PL.model_motor(_ie("PK01"))["cati"][0]["tip"] == "besik"                 # beşik aynen
    assert PL.main([str(VERI / "PK01.json"), str(tmp_path / "PK01")]) == 0 and (tmp_path / "PK01" / "PK01_liste.json").exists()
