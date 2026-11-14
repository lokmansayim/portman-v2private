"""D-92 (BK-30, PC-39) · tek özel pano kuralı: `yapi.dizilim.tek_ozel_pano`.

Lokman, 14 Kasım 2026 13:24 UTC: "125,5 daha büyük bir ölçü varsa 125,5 ölçüsünü çıkar kalanı özel pano olarak ekle"; 13:21: "durduk yere hiç
bir şey yokken 62,75 pano bölmeyiz"; kart 14:05:21 UTC "Okuma 2: duvar boyunca" ("İki köşe ya da T arasında 125,5'ler çıkar, kalan tek özel
pano olur; pencereli panolar yerinde kalır."). Kalan parçanın yeri: kart 14:27:09 "Montaj köşesinden uzak uçta" (dizilim sonu).

Testler: anahtarsız İş Emri aynen; Motor eskiz tablosuyla birebir (Lokman seçimini o eskizle yaptı); Lokman'ın 85 m² örneği; açıklıklı panolar,
dış ölçü ve odalar yerinde; her aralıkta en çok bir tam olmayan pano; kalan dizilim sonunda; kısa parça silinmez ve uyarılır; yanlış yazım hata.
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

TABLO = json.loads((KOK / "testler/motor/veri/D92_tek_ozel_pano_beklenen.json").read_text(encoding="utf-8"))
DEGISEN = sorted(TABLO["evler"])
DEGISMEYEN = TABLO["degismeyen"]


def _ie(kod: str) -> dict:
    return json.loads((KOK / "is_emri/adaylar" / f"{kod}.json").read_text(encoding="utf-8"))


def _anahtarli(ie: dict, deger="dizilim_sonu") -> dict:
    ie = copy.deepcopy(ie)
    ie["yapi"].setdefault("dizilim", {})["tek_ozel_pano"] = deger
    return ie


def _panolar(plan) -> list:
    return sorted((q.duvar.id, round(q.a0, 4), round(q.a1, 4)) for q in plan.panolar)


def _aciklikli(plan) -> list:
    return sorted((q.duvar.id, round(q.a0, 4), round(q.a1, 4), tuple((a.tur, a.olcu) for a in q.aciklar), q.karkasli)
                  for q in plan.panolar if q.aciklar or q.karkasli)


def test_tablo_bicimi():
    assert TABLO["sema"] == "portman.tek_ozel_pano_beklenen/1"
    assert set(DEGISEN).isdisjoint(DEGISMEYEN)
    assert {k for k, e in TABLO["evler"].items() if "muhur" in e} == {"PA03", "PA22"}   # yalnız bellekte; İş Emri'ne yazılmaz
    for e in TABLO["evler"].values():
        assert e["degisiklik"] and all(set(s) == {"duvar", "once", "sonra"} for s in e["degisiklik"])


@pytest.mark.parametrize("kod", DEGISMEYEN + DEGISEN)
def test_anahtarsiz_is_emri_aynen(kod):
    """Anahtar yoksa işlev koşmaz: plan bugünkü gibi, değişiklik listesi boş."""
    p = G.kur(_ie(kod))
    assert p.tek_ozel_pano == []


@pytest.mark.parametrize("kod", DEGISMEYEN)
def test_degismeyen_evde_anahtar_bir_sey_degistirmez(kod):
    ie = _ie(kod)
    p0, p1 = G.kur(ie), G.kur(_anahtarli(ie))
    assert p1.tek_ozel_pano == []
    assert _panolar(p0) == _panolar(p1)
    assert p0.uyarilar == p1.uyarilar


@pytest.mark.parametrize("kod", DEGISEN)
def test_motor_eskiz_tablosuyla_ayni(kod):
    """Motor'un yeniden dizdiği her aralık eskizdeki gibi (duvar, önce, sonra); başka aralık değişmez."""
    p = G.kur(_anahtarli(_ie(kod)))
    assert p.tek_ozel_pano == TABLO["evler"][kod]["degisiklik"]


@pytest.mark.parametrize("kod", DEGISEN)
def test_aciklikli_panolar_dis_olcu_ve_odalar_yerinde(kod):
    """Pencereli panolar yerinde kalır (kartın sözü); kapı, karkaslı pano, dış ölçü, oda alanları ve pano toplam boyu aynı."""
    ie = _ie(kod)
    p0, p1 = G.kur(ie), G.kur(_anahtarli(ie))
    assert _aciklikli(p0) == _aciklikli(p1)
    assert (p0.W, p0.H) == (p1.W, p1.H)
    assert {a: round(m.alan_m2, 4) for a, m in p0.mahaller.items()} == {a: round(m.alan_m2, 4) for a, m in p1.mahaller.items()}
    for d0, d1 in zip(p0.duvarlar, p1.duvarlar):
        assert d0.id == d1.id and (d0.p0, d0.p1) == (d1.p0, d1.p1)
        assert abs(sum(q.boy for q in d0.panolar) - sum(q.boy for q in d1.panolar)) < 1e-6
        assert all(abs(a.a1 - b.a0) < 1e-6 for a, b in zip(d1.panolar, d1.panolar[1:]))   # boşluksuz, üst üste binmeden


@pytest.mark.parametrize("kod", DEGISEN + DEGISMEYEN)
def test_her_aralikta_en_cok_bir_ozel_pano(kod):
    """Kuralın sonucu: iki köşe, T ya da açıklıklı pano arasında açıklıksız panolardan en çok biri tam değildir; 125,5'i aşan yok (D-69)."""
    p = G.kur(_anahtarli(_ie(kod)))
    for d in p.duvarlar:
        for grup in G.tek_pano_araliklari(p, d):
            if grup[0].aciklar or grup[0].karkasli:
                continue
            assert sum(1 for q in grup if q.boy < G.TEK_PANO_TAM_ESIGI_CM) <= 1, (kod, d.id, [q.boy for q in grup])
            assert all(q.boy <= G.MOD + 1e-6 for q in grup)


@pytest.mark.parametrize("kod", DEGISEN)
def test_kalan_dizilim_sonunda(kod):
    """Lokman, kart 14:27:09 "Montaj köşesinden uzak uçta": yeniden dizilen aralıkta tam olmayan pano dizilimin sonunda; arka-solda düşey
    duvarda ön uçta."""
    arka_sol = TABLO["evler"][kod]["baslangic"] == "arka-sol"
    for s in TABLO["evler"][kod]["degisiklik"]:
        sonra = s["sonra"][::-1] if arka_sol and s["duvar"].split()[1] == "y" else s["sonra"]   # dizilim sırası
        assert all(b >= G.TEK_PANO_TAM_ESIGI_CM for b in sonra[:-1]), s   # sondan önceki hepsi tam (köşe/T payıyla 120,5; 122,5 da tam)
        assert all(abs(b - G.MOD) < 1e-6 for b in sonra[1:-1]), s         # aradakiler 125,5


def test_lokmanin_ornegi_85m2():
    """Lokman 13:12 ve 13:21 (85 m² ev, sağ duvar 2 yarım pano uzatılmış, 1291,5 × 726): "62,75 ile 89,25 tek pano haline gelir ... 125,5 +
    26,5 olur aynı aksdaki iç duvar panolarıda aynı mantıkda olur". Motor: üst ve alt dış duvarın sağ ucu 125,5 + 26,5; aynı akstaki iç duvar
    125,5 + 21,5 (bugün 62,75 + 89,25 ve 62,75 + 84,25)."""
    from beyin import yarim_pano as Y
    ie1, _ = Y.kaydir(_ie("PA12"), "sag", 2 * Y.YARIM)
    p0, p1 = G.kur(ie1), G.kur(_anahtarli(ie1))
    assert (p0.W, p0.H) == (p1.W, p1.H) == (1291.5, 726.0)
    sag = lambda p, tur, c: [round(q.boy, 2) for d in p.duvarlar if d.yon == "x" and d.tur == tur and abs(d.c - c) < 0.5 for q in d.panolar][-2:]
    assert sag(p0, "dis", 721) == [62.75, 89.25] and sag(p1, "dis", 721) == [125.5, 26.5]
    assert sag(p0, "dis", 5) == [62.75, 89.25] and sag(p1, "dis", 5) == [125.5, 26.5]
    assert sag(p0, "ic", 273.75) == [62.75, 84.25] and sag(p1, "ic", 273.75) == [125.5, 21.5]
    assert len(p0.panolar) == len(p1.panolar) == 57


def test_kisa_parca_kalir_ve_uyarilir():
    """Kısa kalan parça silinmez (soru Lokman'da); Motor'un var olan "çok kısa pano" uyarısı yeni panoya da düşer, kalkan panonunki kalkar."""
    p = G.kur(_anahtarli(_ie("PA08")))
    kisa = [q for q in p.panolar if q.boy < 20]
    assert [round(q.boy, 2) for q in kisa] == [9.5]
    assert f"Duvar {kisa[0].duvar.id}: 9.5 cm'lik çok kısa pano (özel pano kuralı doğrulanmalı)" in p.uyarilar
    assert sum("çok kısa pano" in u for u in p.uyarilar) == 1
    p0 = G.kur(_ie("PA08"))
    assert not any("çok kısa pano" in u for u in p0.uyarilar)


@pytest.mark.parametrize("kod, cephe, cm", [("PA16", "sag", 1.0), ("PA12", "sag", 99.5), ("PA24", "on", 77.0)])
def test_kalan_kose_payindan_kisa_hata(kod, cephe, cm):
    """Geometri hakemi bulgusu (14 Kasım): aks üstünde kalan köşe ya da T payından kısaysa son pano eksi boyda olurdu (PA16 sağ +1 cm: iç
    duvar 122,5 + 125,5 + 125,5 + (−4)). Motor bunu sessizce çizmez ya da listeye geçirmez: açık hata (K21). Kısa parçanın kuralı Lokman'da."""
    from beyin import yarim_pano as Y
    ie1, _ = Y.kaydir(_ie(kod), cephe, cm)
    G.kur(ie1)                                                   # anahtarsız: kurulur
    with pytest.raises(G.IsEmriHatasi, match="köşe ya da T payından kısa"):
        G.kur(_anahtarli(ie1))


def test_hic_pano_eksi_ya_da_sifir_boyda_degil():
    """Anahtarla kurulan her havuz evinde her pano pozitif boyda."""
    for kod in DEGISEN + DEGISMEYEN:
        p = G.kur(_anahtarli(_ie(kod)))
        assert all(q.boy > 0 for q in p.panolar), kod


@pytest.mark.parametrize("deger", ["basta", True, "", "dizilim sonu"])
def test_bilinmeyen_deger_hata(deger):
    with pytest.raises(G.IsEmriHatasi, match="tek_ozel_pano"):
        G.kur(_anahtarli(_ie("PA12"), deger))


def test_yapi_altinda_yazilirsa_hata():
    ie = copy.deepcopy(_ie("PA12"))
    ie["yapi"]["tek_ozel_pano"] = "dizilim_sonu"
    with pytest.raises(G.IsEmriHatasi, match="yapi.dizilim altında"):
        G.kur(ie)


def test_cektirme_u_ile_cakisma_hata():
    """D-49 madde 3: çektirme U'lu T panonun ortasındadır. Kural o T'ye ek koyacaksa sessizce 3'lü H olmaz: açık hata (K21). 140 m² evde iç
    duvarın 59,75 + 125,5 + 59,75'i 122,5 + 122,5 olur; yeni ek, bugün panonun ortasında kalan T'ye denk gelir."""
    ie = _ie("PA08")
    p0 = G.kur(ie)
    d = next(d for d in p0.duvarlar if d.tur == "ic" and d.yon == "x" and abs(d.c - 739) < 0.5)
    p1 = G.kur(_anahtarli(ie))
    d1 = next(w for w in p1.duvarlar if w.id == d.id)
    yeni_ek = [round(a.a1, 4) for a in d1.panolar[:-1] if all(abs(a.a1 - b.a1) > 1e-6 for b in d.panolar[:-1])]
    t = next(w for w in p0.duvarlar if w.yon == "y" and any(abs(w.c - e) <= 3.5 for e in yeni_ek)
             and min(w.a0, w.a1) - 1 <= d.c <= max(w.a0, w.a1) + 1)
    ayna = (ie["yapi"].get("dizilim") or {}).get("baslangic") == "arka-sol"
    y_motor = p0.H - d.c if ayna else d.c                       # birleşim noktası Motor çerçevesinde (arka-solda y arkadan)
    ie2 = copy.deepcopy(ie)
    ie2["yapi"]["birlesimler"] = list(ie2["yapi"].get("birlesimler") or []) + [{"nokta_cm": [t.c, y_motor], "t": "cektirme_u"}]
    G.kur(ie2)                                                   # anahtarsız: T panonun ortasında, geçerli
    with pytest.raises(G.IsEmriHatasi, match="çektirme U"):
        G.kur(_anahtarli(ie2))
