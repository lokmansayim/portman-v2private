"""BK-49 (D-116) · Disk arşivi Parti 1'in üç evinde yükleme listesi paftadaki gibi (D-111 › Bilinen farklar; Lokman, kart 16 Kasım 2026
08:40:11 "Paftadaki gibi olsun").

- 37 m² (PA-39) ve 59 m² (PA-41): çıkıntısız ön cumbanın makas planı evin paftasından (`cumbalar[0].yavru_makaslari_cm`; kart 12:08:22
  "Her ev kendi paftasındaki gibi"): 37 m²'de kalkan makası + yavru 192, 59 m²'de yalnız kalkan makası. Çatı tanımı (kart modeli, rehber,
  3B) aynı makasları aynı yerde okur; çizimdeki çatı aynı. Yavru makasın boyu listede paftanınki (192); o kesitte dereler arası 62,76
  (paftanın planında 128,8), 3B dereler arasını çizer: bilinen fark, tanımda uyarı (K16; geometri hakemi).
- 92 m² (PA-43): teras panelli verandada 2 yan kiriş, duvardan panelin dış kenarına (`verandalar[].cati.yan_kiris`; kart 12:10:16
  "Yalnız bu evde"). Plan ve çizim aynı (D-56'nın tek dış kirişi), AP-26 (M-12) ve öteki teras panelleri aynı.

Hedef örnek `testler/motor/veri/BK49_pafta_listesi_beklenen.json`; tablo PF Liste_Cumba_Kirma/07."""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor import cati_capraz as CC, cati_prefabrik as CP, geometry as G, prefabrik_liste as PL   # noqa: E402

H = json.loads((KOK / "testler" / "motor" / "veri" / "BK49_pafta_listesi_beklenen.json").read_text(encoding="utf-8"))


def _ie(kod: str) -> dict:
    return json.loads((KOK / H["evler"][kod]["is_emri"]).read_text(encoding="utf-8"))


def _adet(S: list[dict], kalem: str, olcu: str) -> int:
    return sum(r["adet"] for r in S if r["kalem"] == kalem and r["olcu"] == olcu)


@pytest.mark.parametrize("kod", sorted(H["evler"]))
def test_liste_hedef_ornek(kod):
    """Değişen satırlar Lokman'ın onayladığı tablodaki gibi; satır ve makas sayısı hedefteki gibi."""
    assert H["onay"]["soz"] == "Evet, girsin"
    e = H["evler"][kod]
    L = PL.is_emrinden(_ie(kod))
    assert len(L["satirlar"]) == e["toplam_satir"] and L["girdi_ozeti"]["makas"] == e["makas"]
    assert [_adet(L["satirlar"], h["kalem"], h["olcu"]) for h in e["satirlar"]] == [h["motor"] for h in e["satirlar"]]


@pytest.mark.parametrize("kod,sil", [("PA39", "cumba"), ("PA41", "cumba"), ("PA43", "veranda")])
def test_anahtarsiz_eski_liste(kod, sil):
    """Anahtar silinince liste BK-49'dan önceki gibi (`once` sütunu): öteki evler bu yoldan değişmez; satırların geri kalanı aynı."""
    ie = _ie(kod)
    yeni = PL.is_emrinden(ie)["satirlar"]
    eski_ie = copy.deepcopy(ie)
    if sil == "cumba":
        del eski_ie["cati"]["cumbalar"][0]["yavru_makaslari_cm"]
    else:
        del eski_ie["verandalar"][0]["cati"]["yan_kiris"]
    eski = PL.is_emrinden(eski_ie)["satirlar"]
    e = H["evler"][kod]
    assert [_adet(eski, h["kalem"], h["olcu"]) for h in e["satirlar"]] == [h["once"] for h in e["satirlar"]]
    assert PL.is_emrinden(eski_ie)["girdi_ozeti"]["makas"] == e["once_makas"]
    anahtar = lambda S: Counter((r["kalem"], r["olcu"]) for r in S if r["kalem"] not in {h["kalem"] for h in e["satirlar"]})   # noqa: E731
    assert anahtar(yeni) == anahtar(eski)


@pytest.mark.parametrize("kod,yavru", [("PA39", [192.0]), ("PA41", [])])
def test_cati_tanimi_ayni_makaslar(kod, yavru):
    """Çatı tanımı (kart modeli, montaj rehberi ve 3B buradan okur) listeyle aynı makasları kurar: kalkan makası + paftanın yavruları,
    125,5 arayla (AP-06'nın kısa yavru kuralı yok). Paftanın boyu o kesitteki dereler arasından uzunsa tanım bunu uyarı olarak yazar (K16):
    37 m²'de L 1920 ↔ 62,76. Çizimdeki çatı (`cati_prefabrik.cati`) aynı."""
    ie = _ie(kod)
    plan = G.kur(ie)
    tn = CC.tanim(plan, ie)
    m = tn["parcalar"][1]["makaslar"]
    assert [x["uzaklik"] for x in m] == [5.0 + i * G.MOD for i in range(1 + len(yavru))]
    assert [x.get("boy_cm") for x in m[1:]] == yavru and not any("uclar" in x for x in m)
    cu = [u for u in tn["uyarilar"] if "makas yeri (cumba)" in u]
    assert cu == ([f"makas yeri (cumba): yavru makasın boyu evin paftasından L 1920 (yeri 130.5); o kesitte dereler arası 62.76 cm, 3B "
                   "makası dereler arasında çizer (D-116)"] if yavru else [])
    eski = copy.deepcopy(ie)
    del eski["cati"]["cumbalar"][0]["yavru_makaslari_cm"]
    assert CP.cati(plan, ie) == CP.cati(G.kur(eski), eski)


def test_teras_paneli_plani_ayni():
    """92 m²: yan kiriş yalnız listede; planın verandası (çizim, 3B, kart modeli) D-56'daki gibi tek dış kirişle, anahtarsızla aynı.
    Bilinen fark (D-116 Karar 2): liste 3 kiriş (4532 + 2 × 2010), plan ve kart modeli 1."""
    ie = _ie("PA43")
    eski = copy.deepcopy(ie)
    del eski["verandalar"][0]["cati"]["yan_kiris"]
    (v,), (v0,) = G.kur(ie).dis_verandalar, G.kur(eski).dis_verandalar
    assert v["kirisler"] == v0["kirisler"] and len(v["kirisler"]) == 1
    assert v["cati"] == {**v0["cati"], "yan_kiris": True}


def test_anahtar_denetimi():
    """Yanlış yazılan anahtar yok sayılmaz, hata verir (K21); liste yolunda `ListeYazilmaz` (teklif aracı yakalar)."""
    ie = _ie("PA39")
    for deger in ([0], ["192"], 192, [True]):
        bozuk = copy.deepcopy(ie)
        bozuk["cati"]["cumbalar"][0]["yavru_makaslari_cm"] = deger
        with pytest.raises(CP.PrefabrikCatiHatasi):
            CC.tanim(G.kur(bozuk), bozuk)
    cikintili = copy.deepcopy(ie)
    cikintili["cati"]["cumbalar"][0]["ana_makas"] = "cumba_makasindan"
    with pytest.raises(CP.PrefabrikCatiHatasi):
        CP.pafta_yavrulari(cikintili["cati"]["cumbalar"][0])
    for deger in ([192, 150, 100], [1920], [383.75]):       # derelerin birleştiği yere sığmaz; kalkan makasından (383,75) kısa değil
        sigmaz = copy.deepcopy(ie)
        sigmaz["cati"]["cumbalar"][0]["yavru_makaslari_cm"] = deger
        with pytest.raises(CP.PrefabrikCatiHatasi):
            CC.tanim(G.kur(sigmaz), sigmaz)
        with pytest.raises(PL.ListeYazilmaz):
            PL.is_emrinden(sigmaz)
    t = _ie("PA43")
    t["verandalar"][0]["cati"]["yan_kiris"] = False
    with pytest.raises(G.IsEmriHatasi):
        G.kur(t)
