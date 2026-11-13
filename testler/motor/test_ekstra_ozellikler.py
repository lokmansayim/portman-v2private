"""Prefabrik ekstra özellikler · havuz evlerinde yükleme listesinin değişmezleri (BK-29 ek işi; pano 221).

Lokman, 13 Kasım 2026 21:44:01 UTC: "tüm prefabrik projelerinin iç duvarlar 100'lük çatı Sandviç yükseklik 280 gibi tüm testlerini çıkar ve
anlamlı kurallar bul ve sonuç doğru çıkana kadar test et"; 21:44:21 UTC: "yani ekstra ne kadar özellik varsa hepsini test et".

Bu dosya yeni kural koymaz ve hiçbir hedef örneği değiştirmez. Motor'un bugün dokuz havuz evinde (PA-01 … PA-08 ve PA-06C; `is_emri/adaylar/`)
aynı biçimde uyguladığı kuralları sabitler: bir özellik (İş Emri anahtarı) eklenince listenin hangi satırları değişir, hangileri değişmez.
Kurallar 13 Kasım 2026 keşfinden (9 ev × 13 özellik; PF `Ekstra_Ozellik_Testleri/`), dayanakları var olan kararlardan:

- Yükseklik 280 / 300 (`yapi.duvar_yuksekligi_cm`): boy taşıyan her satır aynı adetle yeni boya geçer; pencere üst paneli boy − 200 cm
  (280'de 80 cm: Lokman 6 Kasım 2026 07:50, BK-23; gerçek listeler AP-12 ve AP-28'de 100 × 1250 × 800); çektirme U'su boy − 6 cm ve iniş
  borusunun 50'lik parçası iki tane (BK-25, D-60).
- İç duvar 100 (`yapi.duvar_kalinligi_cm.ic = 10`, BK-18): pano sayısı aynı, 60'lık iç duvar kalemi kalmaz; iç duvar üstü omegası 100'lük
  duvar omegası satırında (M-04).
- Çatı kaplaması (`ozellikler › Çatı Kaplaması`, D-74 / M-16): yalnız Çatı ve Vida grupları değişir; trapez sacta trapez mahya L 1000 (M-11),
  ötekilerde düz mahya L 2800.
- Tavan (ters), iç cephe kaplaması (alçıpan), çatı ve pencere rengi.
- Bileşim: çatı kaplaması ile yükseklik, iç 100, ters tavan ve alçıpan birbirinin satırına dokunmaz.
- İkinci dilim (13 Kasım 23:05 UTC; listenin okuduğu öteki anahtarlar): fugalı dış cephe (`Açıklama`: 100'lük dış panolar aynı ölçü ve
  adetle "(FUGALI)" adını alır, lata satırları girer), metal iniş borusu (`Yağmur İniş Borusu`: yalnız Dere grubu), alıcıya ait pencere,
  dış kapı ve boya (`alici_ait.kalemler` ya da özelliğin "Alıcıya ait" değeri: kalem 0 adetle yazılır), 270 cm yükseklik (prefabrikte
  tanımlı değil: İş Emri durur; Lokman, 13 Ekim 2026).

Bugün çalışmayan yerler `xfail(strict=True)` ile yazılıdır (D-28: çalışmayan şey "çalışıyor" yazılmaz); biri düzelince test kırmızıya döner ve
satır buradan kaldırılır: dış duvar 160 havuz evinde yalnız anahtarla açılmaz; PA-06K'nin (kırma) listesi yazılamaz; sandviç panelde
PA-03'ün veranda çatısının örtüsü listede yok; kiremit desen sacta panel kapamasının adedi yok; shingle satırı yok.
"""
from __future__ import annotations

import copy
import functools
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from motor import geometry as G
from motor import prefabrik_liste as PL

KOK = Path(__file__).resolve().parents[2]
ADAYLAR = KOK / "is_emri" / "adaylar"
EVLER = ["PA01", "PA02", "PA03", "PA04", "PA05", "PA06", "PA07", "PA08", "PA06C"]


def _yapi(**kw):
    def f(ie):
        for a, b in kw.items():
            if isinstance(b, dict):
                ie["yapi"].setdefault(a, {}).update(b)
            else:
                ie["yapi"][a] = b
    return f


def _oz(ad, deger):
    def f(ie):
        oz = ie.setdefault("ozellikler", {})
        for k in [k for k in oz if k.lower() == ad.lower()]:
            del oz[k]
        oz[ad] = deger
    return f


def _alici(kalem):
    def f(ie):
        ie.setdefault("alici_ait", {}).setdefault("kalemler", []).append(kalem)
    return f


OZELLIK = {
    "ic_100": _yapi(duvar_kalinligi_cm={"ic": 10}),
    "dis_160": _yapi(duvar_kalinligi_cm={"dis": 16}),
    "h_280": _yapi(duvar_yuksekligi_cm=280),
    "h_300": _yapi(duvar_yuksekligi_cm=300),
    "tek_kat": _oz("Çatı Kaplaması", "Tek Kat Panel"),
    "sandvic": _oz("Çatı Kaplaması", "Sandviç Panel"),
    "kiremit": _oz("Çatı Kaplaması", "OSB + Nem Bariyeri + Kiremit Desen Sac"),
    "shingle": _oz("Çatı Kaplaması", "OSB + Membran + Shingle"),
    "trapez_osb": _oz("Çatı Kaplaması", "OSB + Trapez Sac"),
    "trapez": _oz("Çatı Kaplaması", "Trapez Sac"),
    "ters": _oz("Tavan", "Ters"),
    "alcipan": _oz("İç Cephe Kaplaması", "Alçıpan"),
    "cati_rengi": _oz("Çatı Kaplama Rengi", "Antrasit"),
    "pencere_rengi": _oz("Pencere Rengi", "Antrasit"),
    "h_270": _yapi(duvar_yuksekligi_cm=270),
    "fugali": _oz("Açıklama", "Fugalı"),
    "metal_inis": _oz("Yağmur İniş Borusu", "Metal"),
    "pencere_alici": _alici("Pencere"),
    "pencere_alici_renk": _oz("Pencere Rengi", "Alıcıya ait"),
    "kapi_alici": _oz("Dış Kapı", "Alıcıya ait"),
    "boya_alici": _alici("Boya"),
    "boya_alici_oz": lambda ie: (_oz("Dış Cephe Boya", "Alıcıya ait")(ie), _oz("İç Cephe Boya", "Alıcıya ait")(ie)),
}
KAPLAMALAR = ["tek_kat", "sandvic", "kiremit", "shingle", "trapez_osb"]


@functools.lru_cache(maxsize=None)
def _ie(ev: str) -> str:
    return (ADAYLAR / f"{ev}.json").read_text(encoding="utf-8")


@functools.lru_cache(maxsize=None)
def _liste(ev: str, *ozellikler: str) -> dict:
    """(grup adı, kalem, ölçü) → adet. Lento ve kalınlık modül durumudur: her listeden sonra varsayılana döner (BK-23 testi gibi)."""
    ie = json.loads(_ie(ev))
    for o in ozellikler:
        OZELLIK[o](ie)
    try:
        L = PL.is_emrinden(copy.deepcopy(ie))
    finally:
        G.lento_ayarla({})
    return {(s["grup_adi"], s["kalem"], s["olcu"]): s["adet"] for s in L["satirlar"]}


def _fark(a: dict, b: dict):
    """(eklenen, çıkan, adedi değişen) anahtarlar."""
    return ({k: b[k] for k in b.keys() - a.keys()}, {k: a[k] for k in a.keys() - b.keys()},
            {k: (a[k], b[k]) for k in a.keys() & b.keys() if a[k] != b[k]})


def _gruplar(*farklar) -> set:
    return {k[0] for f in farklar for k in f}


def _pano(L: dict) -> int:
    return sum(v for k, v in L.items() if k[0] == "Panel" and "üst panel" not in k[1] and "alt panel" not in k[1])


IC_60 = re.compile(r"60'lık .*pano|H standart 60|3'lü H standart 60|3'lü H 100 × 100 × 60|6'lık köşe direği|60'lık alt çerçeve|Çektirme U'su 60")
ALCIPAN = {"Duvar alçıpanı beyaz", "Duvar alçıpanı yeşil", "Alçıpan destek straforu", "Alçıpan vidası"}
ORTU = re.compile(r"^(Trapez sac|Tek kat çatı paneli|Sandviç panel \(100 cm kapatır\)|Metal kiremit \(100 cm kapatır\)) · (.+)$")


def _ortu(L: dict) -> dict:
    """Çatı parçası → (boy, adet): örtünün kendisi (sac ya da panel)."""
    return {m.group(2): (k[2], v) for k, v in L.items() if (m := ORTU.match(k[1]))}


# ── renk ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ev", EVLER)
@pytest.mark.parametrize("renk", ["cati_rengi", "pencere_rengi"])
def test_renk_listeyi_degistirmez(ev, renk):
    assert _liste(ev, renk) == _liste(ev)


# ── yükseklik ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ev", EVLER)
@pytest.mark.parametrize("h", [280, 300])
def test_yukseklik_boy_tasiyan_satirlar_ayni_adetle_yeni_boya_gecer(ev, h):
    t, y = _liste(ev), _liste(ev, f"h_{h}")
    e, c, d = _fark(t, y)
    assert e and Counter((k[1], v) for k, v in e.items()) == Counter((k[1], v) for k, v in c.items())
    mm = h * 10
    for k in e:
        if k[1] == "Pencere üst panel":
            assert k[2].endswith(f"× {mm - 2000}"), k                      # pencere üst kotu 200 cm: 280'de lento 80 cm (BK-23)
        elif k[1].startswith("Çektirme U'su"):
            assert k[2].endswith(f"× {mm - 60}"), k                        # BK-25: çektirme U'su boyla (2440 / 2740 / 2940)
        else:
            assert str(mm) in k[2], k
    for k in c:
        assert re.search(r"2500|2440|× 500$", k[2]), k
    assert not any(str(2500) in k[2] and k[0] == "Panel" and re.search(r"× 2500$", k[2]) and "alçıpan" not in k[1].lower() for k in y), "250'lik pano kaldı"
    assert _pano(y) == _pano(t)
    inis = [k for k in d if "iniş borusu" in k[1]]
    assert len(inis) == 1 and inis[0][2] == "L 500" and d[inis[0]] == (t[inis[0]], 2 * t[inis[0]]), d   # 2000 + 2 × 500 ≥ boy (BK-25)
    assert {k[1] for k in d} - {inis[0][1]} <= ALCIPAN, d                  # duvar alçıpanı boyla artar (alçıpan kaplamalı evde)
    assert _gruplar(e, c, d) <= {"Panel", "Metal aksam", "Dere", "Tavan", "Vida"}


# ── iç duvar 100 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ev", EVLER)
def test_ic_100_pano_sayisi_ayni_60lik_kalem_kalmaz(ev):
    t, y = _liste(ev), _liste(ev, "ic_100")
    assert any(IC_60.search(k[1]) for k in t), "havuz evinin iç duvarı 60'lık olmalı"
    assert not [k for k in y if IC_60.search(k[1])]
    assert _pano(y) == _pano(t)
    assert sum(v for k, v in y.items() if k[1] == "100'lük duvar omegası") > sum(v for k, v in t.items() if k[1] == "100'lük duvar omegası")   # M-04
    assert _gruplar(*_fark(t, y)) <= {"Panel", "Metal aksam", "Tavan", "Vida"}


# ── çatı kaplaması ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ev", EVLER)
@pytest.mark.parametrize("kaplama", KAPLAMALAR)
def test_cati_kaplamasi_yalniz_cati_ve_vida(ev, kaplama):
    assert _gruplar(*_fark(_liste(ev), _liste(ev, kaplama))) <= {"Çatı", "Vida"}


@pytest.mark.parametrize("ev", EVLER)
def test_trapez_standart_ve_trapez_mahya(ev):
    """Kaplama yazılmamış ya da "Trapez Sac" yazılmış ev aynı liste (D-74, M-16); mahya trapez sac mahyası L 1000 (M-11)."""
    L = _liste(ev, "trapez")
    kalemler = {k[1] for k in L}
    assert ("Çatı", "Trapez sac mahyası", "L 1000") in L and "Metal kiremit mahyası" not in kalemler
    assert any(k.startswith("Trapez sac · ") for k in kalemler) and "Trapez vida 5,5 × 60 (trapez sac)" in kalemler
    if "Çatı Kaplaması" not in (json.loads(_ie(ev)).get("ozellikler") or {}):
        assert L == _liste(ev)


@pytest.mark.parametrize("ev", EVLER)
def test_tek_kat_panel_ortusu_trapezle_ayni_yerde_ayni_adet(ev):
    """Tek kat panel de 100 cm kapatır: her çatı parçasında boy ve adet trapez sacınkiyle aynı; mahya düz L 2800, vida 5,5 × 76."""
    t, y = _liste(ev, "trapez"), _liste(ev, "tek_kat")
    assert _ortu(y) == _ortu(t) and _ortu(y)
    kalemler = {k[1] for k in y}
    assert all(k.startswith("Tek kat çatı paneli · ") for k in kalemler if ORTU.match(k))
    assert ("Çatı", "Metal kiremit mahyası", "L 2800") in y and "Trapez sac mahyası" not in kalemler
    assert "Trapez vida 5,5 × 76 (tek kat panel)" in kalemler


@pytest.mark.parametrize("ev", EVLER)
def test_sandvic_panel_satirlari(ev):
    y = _liste(ev, "sandvic")
    kalemler = {k[1] for k in y}
    assert any(k.startswith("Sandviç panel (100 cm kapatır) · ") for k in kalemler)
    assert ("Çatı", "Sandviç panel kapaması", "L 2500") in y and y[("Çatı", "Sandviç panel kapaması", "L 2500")] > 0
    assert ("Çatı", "Metal kiremit mahyası", "L 2800") in y and "Trapez sac mahyası" not in kalemler
    assert "Trapez vida 5,5 × 110 (sandviç panel)" in kalemler
    assert not any(k.startswith(("Trapez sac · ", "Tek kat çatı paneli · ")) for k in kalemler)


@pytest.mark.parametrize("ev", EVLER)
def test_kiremit_desen_sac_satirlari(ev):
    t, y = _liste(ev, "trapez"), _liste(ev, "kiremit")
    kalemler = {k[1] for k in y}
    assert _ortu(y) == _ortu(t) and all(k.startswith("Metal kiremit (100 cm kapatır) · ") for k in kalemler if ORTU.match(k))
    assert y[("Çatı", "OSB 11 mm (çatı)", "1220 × 2440")] > 0 and y[("Çatı", "Nem bariyeri", "m²")] > 0
    assert ("Çatı", "Metal kiremit mahyası", "L 2800") in y and "Trapez vida 5,5 × 60 (metal kiremit)" in kalemler


@pytest.mark.parametrize("ev", EVLER)
def test_trapez_osb_yalniz_osb_ekler(ev):
    t, y = _liste(ev, "trapez"), _liste(ev, "trapez_osb")
    e, c, d = _fark(t, y)
    assert set(e) == {("Çatı", "OSB 11 mm (çatı)", "1220 × 2440")} and not c and not d and y[("Çatı", "OSB 11 mm (çatı)", "1220 × 2440")] > 0


# ── tavan, iç cephe kaplaması ─────────────────────────────────────────────────────────────────────────────────────────────────────────
ASMA = ("60'lık duvar omegası (asma dizme tavan)", "Tavan H'ı L 1185 (asma dizme tavan)", "PVC omega kapak L 3750 (asma dizme tavan)")


@pytest.mark.parametrize("ev", EVLER)
def test_ters_tavan(ev):
    t, y = _liste(ev), _liste(ev, "ters")
    kalemler = {k[1] for k in y}
    assert y[("Metal aksam", "60'lık tavan omegası (ters tavan)", "60 × 3750")] > 0 and not kalemler & set(ASMA)
    assert _gruplar(*_fark(t, y)) <= {"Metal aksam", "Tavan", "Vida"}


@pytest.mark.parametrize("ev", EVLER)
def test_ic_kaplama_alcipan(ev):
    t, y = _liste(ev), _liste(ev, "alcipan")
    e, c, d = _fark(t, y)
    assert y[("Tavan", "Duvar alçıpanı beyaz", "1200 × 2500")] > 0 and y[("Tavan", "Duvar alçıpanı yeşil", "1200 × 2500")] > 0   # yeşil ıslak hacimde
    assert not c and {k[1] for k in list(e) + list(d)} <= ALCIPAN


# ── bileşim ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("ev", EVLER)
@pytest.mark.parametrize("oteki", ["h_280", "ic_100", "ters", "alcipan"])
@pytest.mark.parametrize("kaplama", ["sandvic", "tek_kat"])
def test_cati_kaplamasi_oteki_ozelliklerle_karismaz(ev, oteki, kaplama):
    """İki özellik birlikte: her satır ya tabandaki, ya yalnız kaplamanın, ya yalnız öteki özelliğin değeridir; ikisi aynı satıra dokunmaz."""
    t, a, b, ab = _liste(ev), _liste(ev, kaplama), _liste(ev, oteki), _liste(ev, oteki, kaplama)
    dok_a = {k for k in a.keys() | t.keys() if a.get(k) != t.get(k)}
    dok_b = {k for k in b.keys() | t.keys() if b.get(k) != t.get(k)}
    assert not dok_a & dok_b
    for k in ab.keys() | t.keys():
        beklenen = a.get(k) if k in dok_a else (b.get(k) if k in dok_b else t.get(k))
        assert ab.get(k) == beklenen, k


# ── bugün çalışmayan yerler (düzelince satır kaldırılır) ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.xfail(strict=True, reason="dış duvar 160 havuz evinde yalnız anahtarla açılmaz: sınırlar 100'lük duvara göre yazılı (İş Emri durur)")
@pytest.mark.parametrize("ev", EVLER)
def test_dis_160_havuz_evinde(ev):
    assert any(k[1].startswith("160'lık") for k in _liste(ev, "dis_160"))


@pytest.mark.xfail(strict=True, reason="PA-06K (iki uçlu kırma, mahya y boyunca): makas planı kıyaslanmadı, liste yazılmaz")
def test_pa06k_listesi():
    assert _liste("PA06K")


@pytest.mark.xfail(strict=True, reason="sandviç panelde PA-03'ün (AP-09 modeli) veranda çatısının örtüsü listede yok; AP-09'un gerçek listesinde veranda örtüsü ayrı satır")
def test_sandvic_veranda_ortusu_pa03():
    assert set(_ortu(_liste("PA03", "sandvic"))) == set(_ortu(_liste("PA03", "trapez")))


@pytest.mark.xfail(strict=True, reason="kiremit desen sacta panel kapamasının adedi için kural yok (satır adetsiz)")
@pytest.mark.parametrize("ev", EVLER)
def test_kiremit_panel_kapamasi_adedi(ev):
    assert all(v is not None for v in _liste(ev, "kiremit").values())


@pytest.mark.xfail(strict=True, reason="OSB + membran + shingle için liste kuralı yok: kaplama tek kat panel gibi sayılıyor, shingle ve membran satırı yok")
@pytest.mark.parametrize("ev", EVLER)
def test_shingle_satiri(ev):
    kalemler = {k[1].lower() for k in _liste(ev, "shingle")}
    assert any("shingle" in k for k in kalemler) and not any(k.startswith("tek kat çatı paneli") for k in kalemler)


# ── İkinci dilim: listenin okuduğu öteki anahtarlar (fugalı dış cephe, metal iniş borusu, alıcıya ait kalemler) ──────────────────────────────

FUGALI = " (FUGALI)"


@pytest.mark.parametrize("ev", EVLER)
def test_fugali_dis_panolar_ayni_olcu_ve_adetle_fugali_adina_gecer(ev):
    """`ozellikler › Açıklama` "Fugalı": 100'lük dış duvar panelleri aynı ölçü ve adetle "(FUGALI)" adını alır; lata satırları girer."""
    taban, y = _liste(ev), _liste(ev, "fugali")
    eklenen, cikan, degisen = _fark(taban, y)
    assert not degisen
    assert cikan and {k[0] for k in cikan} == {"Panel"}
    panel = {k: v for k, v in eklenen.items() if k[0] == "Panel"}
    assert {(g, ad + FUGALI, olcu): n for (g, ad, olcu), n in cikan.items()} == panel       # yalnız ad değişir
    assert _pano(taban) == _pano(y)
    lata = {k: v for k, v in eklenen.items() if k[0] != "Panel"}
    assert lata and {k[0] for k in lata} == {"Tavan"} and all("lata" in k[1].lower() for k in lata)
    assert not any(FUGALI in k[1] for k in y if k[1].startswith("60'lık"))                    # iç duvar panosu fugalı olmaz


@pytest.mark.parametrize("ev", EVLER)
def test_metal_inis_borusu_pvc_parcalarin_yerine_gecer(ev):
    """`Yağmur İniş Borusu` "Metal": PVC borunun iki satırı çıkar, iniş başına bir metal boru girer; yalnız Dere grubu değişir."""
    taban, y = _liste(ev), _liste(ev, "metal_inis")
    eklenen, cikan, degisen = _fark(taban, y)
    assert not degisen and _gruplar(eklenen, cikan) == {"Dere"}
    assert all("PVC dere iniş borusu" in k[1] for k in cikan) and len(cikan) == 2
    (k, n), = eklenen.items()
    assert k[1] == "Metal iniş borusu"
    assert n == next(v for kk, v in cikan.items() if kk[2] == "L 2000")                       # iniş sayısı aynı


@pytest.mark.parametrize("ev", EVLER)
def test_pencere_aliciya_aitse_pencere_ve_baglantilari_listeden_cikar(ev):
    """Pencere alıcıya ait: pencere ve vasistas satırları çıkar, "Pencere grubu" 0 adetle yazılır; pano sayısı aynı kalır.
    İki yazım (`alici_ait.kalemler` ve `Pencere Rengi: Alıcıya ait`) aynı listeyi verir."""
    taban, y = _liste(ev), _liste(ev, "pencere_alici")
    assert y == _liste(ev, "pencere_alici_renk")
    eklenen, cikan, degisen = _fark(taban, y)
    assert not degisen and eklenen == {("Kapı ve pencere", "Pencere grubu", "—"): 0}
    assert _gruplar(cikan) <= {"Kapı ve pencere", "Boya", "Metal aksam", "Vida"}
    assert not any(k[1].startswith(("PVC pencere", "PVC vasistas")) for k in y)
    assert {k for k in taban if k[1].startswith(("PVC pencere", "PVC vasistas"))} <= set(cikan)
    assert _pano(taban) == _pano(y)


@pytest.mark.parametrize("ev", EVLER)
def test_dis_kapi_aliciya_aitse_yalniz_kapinin_adedi_sifirlanir(ev):
    taban, y = _liste(ev), _liste(ev, "kapi_alici")
    eklenen, cikan, degisen = _fark(taban, y)
    assert not eklenen and not cikan
    assert degisen and all(k[0] == "Kapı ve pencere" and "kapı" in k[1].lower() and yeni == 0 for k, (_eski, yeni) in degisen.items())


@pytest.mark.parametrize("ev", EVLER)
def test_boya_aliciya_aitse_boya_satirlari_cikar(ev):
    """Boya alıcıya ait: boya kovaları çıkar, "Boya grubu" 0 adetle yazılır; mastik kalır. İki yazım aynı listeyi verir."""
    taban, y = _liste(ev), _liste(ev, "boya_alici")
    assert y == _liste(ev, "boya_alici_oz")
    eklenen, cikan, degisen = _fark(taban, y)
    assert not degisen and eklenen == {("Boya", "Boya grubu", "—"): 0}
    assert cikan and _gruplar(cikan) == {"Boya"} and not any("mastik" in k[1].lower() for k in cikan)


@pytest.mark.parametrize("ev", EVLER)
@pytest.mark.parametrize("ozellik", ["fugali", "metal_inis", "pencere_alici", "kapi_alici", "boya_alici"])
@pytest.mark.parametrize("oteki", ["h_280", "ic_100", "sandvic"])
def test_ikinci_dilim_oteki_ozelliklerle_karismaz(ev, ozellik, oteki):
    """Özelliğin dokunduğu gruplar, öteki özellik yazılıyken de aynıdır (iki özellik birbirinin satırını bozmaz)."""
    tek = _gruplar(*_fark(_liste(ev), _liste(ev, ozellik)))
    birlikte = _gruplar(*_fark(_liste(ev, oteki), _liste(ev, oteki, ozellik)))
    assert birlikte == tek


@pytest.mark.parametrize("ev", EVLER)
def test_yukseklik_270_prefabrikte_tanimli_degil(ev):
    """Prefabrik pano yüksekliği yalnız 250 / 280 / 300 cm (Lokman, 13 Ekim 2026); 270 çelik karkasın yüksekliğidir. Liste sessizce
    250 ya da 280 saymaz, İş Emri durur."""
    with pytest.raises(G.IsEmriHatasi, match="270 cm tanımlı değil"):
        _liste(ev, "h_270")

