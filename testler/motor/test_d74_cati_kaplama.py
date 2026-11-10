"""D-74 kilit testi: prefabrikte çatı kaplamasının standardı trapez sac, mahyası trapez mahya L 100 (kanat 35 × 35 cm); çelikte tek kat panel.

Lokman, 10 Kasım 2026 04:45 (TK-01 montaj rehberinin 20. adımı): "20. adımda koyduğun Tek Kat panel değil Trapez sac ve Trapez Mahya olacak
Düz mahya'yı Sandviç Panel ve Kiremit Desen Sac'da kullanıyoruz ... bizim ki Trapez Sac 100 kapatır ve Trapez mahya L:100 ve 35x35 olarak al";
04:58: "... bunu kesin mühürle, Trapez Sac bizim Prefabrik evlerde Standardımız, Tek kat panel, Sandviç Panel, OSB+ Nem Bariyeri/Membar+Kiremit
Desen Sac, OSB+membran+Shingle da opsiyonlar ayrıca Tek Kat Panel Çelik Konstrüksiyon yapılarda Standardı Prefabrik çatı kaplama opsiyonları
Çelik Konstrüksiyon içinde aynı".

Kural:
- `kurallar/liste/prefabrik.json › baz_cati_kaplamasi` = `trapez_sac`: İş Emri çatı kaplamasını yazmazsa liste ve kart modeli trapez sac okur
  (`prefabrik_liste.cati_kaplamasi_yazisi`); sac 100 cm kapatır, mahya trapez sac mahyası L 1000 (D-50, M-11);
- kural kitabının `baz_paket_cati_kaplamasi` = `tek_kat_panel` çeliğin standardıdır, prefabrikte okunmaz (`kitapla_farkli`);
- yazılı kaplama (opsiyon) aynen okunur: tek kat panel, sandviç panel, kiremit desen sac bugünkü satırlarıyla;
- trapez sac mahyasının kanadı her yanda 35 cm (kart CK-07, kart modelinin gösterimi);
- tek kat panelde mahya düz mahya L 2800 (Lokman, 10 Kasım 2026 08:33: "Tek kat panelde mahya değişmiyor Düz Mahya L: 2800");
- trapez sacta 5,5 × 60 vida tek satır, kaplama vidası (Lokman, 08:38, karar kartı: "Hayır, bugünkü tek satır kalsın");
- TK-01 r08 (yalnız çatı kaplaması "Trapez Saç"): çatı satırları Lokman'ın 08:33'te onayladığı önce/sonrayla aynı ("tüm hepsine onaylıyorum");
  r07 (M-02 hedef örneği) aynen.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


@pytest.fixture(scope="module")
def N():
    return PL.model_motor(_oku(VERI / "PK01.json"))


def _liste(N: dict, kurallar: dict, kaplama: str | None) -> dict:
    n = copy.deepcopy(N)
    oz = {k: v for k, v in n["ozellikler"].items() if PL._kucuk(k) != "çatı kaplaması"}
    n["ozellikler"] = oz if kaplama is None else {**oz, "Çatı Kaplaması": kaplama}
    return PL.liste(n, kurallar, _oku(VERI / "PK01_pafta_katmani.json"))


def _cati(L: dict) -> dict:
    """1006 Çatı ve kaplama vidalarının (5,5 × 60 / 76 / 110) satırları: kalem → (ölçü, adet)."""
    vida = tuple(f"Trapez vida 5,5 × {b} " for b in (60, 76, 110))
    return {s["kalem"]: (s["olcu"], s["adet"]) for s in L["satirlar"] if s["grup"] == "1006" or s["kalem"].startswith(vida)}


def test_kural_degerleri():
    R = _oku(KOK / "kurallar" / "liste" / "prefabrik.json")
    b = R["kurallar"]["baz_cati_kaplamasi"]
    assert (b["deger"], b["durum"]) == ("trapez_sac", "lokman")
    assert "10 Kasım 2026 04:58 (D-74)" in b["kaynak"] and "Trapez Sac bizim Prefabrik evlerde Standardımız" in b["kaynak"]
    F = {x["konu"]: x for x in R["kitapla_farkli"]}["Baz paketin çatı kaplaması"]
    assert (F["prefabrik"], F["kitap"], F["tur"]) == ("baz_cati_kaplamasi", "baz_paket_cati_kaplamasi", "deger")
    assert "baz_paket_cati_kaplamasi" not in {o["kitap"] for o in R["kitaptan_okunmayan"]}


def test_celikte_tek_kat_panel(kurallar):
    """Çelik (genel motor) kural kitabından okur: baz paketin çatı kaplaması tek kat panel; güncel kitap da prefabriğin sabitlediği set de."""
    for kitap in (_oku(KOK / "kurallar" / "liste" / "kurallar.json"), kurallar["ortak"]):
        assert kitap["baz_paket_cati_kaplamasi"]["deger"] == "tek_kat_panel"
        assert {"tek_kat_panel", "trapez_sac", "sandvic_panel", "osb_kiremit", "osb_shingle"} <= set(kitap["cati_kaplama"]["deger"])


def test_yazilmamis_kaplama_standart_trapez(N, kurallar):
    assert PL.cati_kaplamasi_yazisi({}, kurallar) == ("trapez sac", True)
    assert PL.cati_kaplamasi_yazisi({"Çatı Kaplaması": "  "}, kurallar) == ("trapez sac", True)
    assert PL.cati_kaplamasi_yazisi({"ÇATI KAPLAMASI": "Tek Kat Panel"}, kurallar) == ("tek kat panel", False)
    L = _liste(N, kurallar, None)
    c = _cati(L)
    assert c["Trapez sac · ana çatı"] == ("L 3530", 22)       # PK-01 ana çatı: 2 yüz × ⌈10,60 ÷ 1⌉ (100 cm kapatır, M-11)
    assert c["Trapez sac mahyası"] == ("L 1000", 11)          # ⌈10,60 ÷ 1⌉, bindirme yok
    assert not [k for k in c if k.startswith(("Tek kat çatı paneli", "Sandviç panel", "Metal kiremit"))]
    sac = next(s for s in L["satirlar"] if s["kalem"] == "Trapez sac · ana çatı")
    assert "prefabrik standardı trapez sac (D-74)" in sac["kaynak"]
    # yazılı trapez sac aynı adetleri verir, standart notu yazmaz
    Y = _liste(N, kurallar, "Trapez Saç")
    assert _cati(Y) == c
    assert "D-74" not in next(s for s in Y["satirlar"] if s["kalem"] == "Trapez sac · ana çatı")["kaynak"]


def test_baz_anahtari_kitapta_olmali(N, kurallar):
    K = copy.deepcopy(kurallar)
    K["prefabrik"]["kurallar"]["baz_cati_kaplamasi"]["deger"] = "trapez"
    with pytest.raises(ValueError, match="baz_cati_kaplamasi"):
        _liste(N, K, None)


@pytest.mark.parametrize("kaplama, kalem, mahya", [
    ("Tek Kat Panel", "Tek kat çatı paneli · ana çatı", ("Metal kiremit mahyası", "L 2800")),
    ("Sandviç Panel", "Sandviç panel (100 cm kapatır) · ana çatı", ("Metal kiremit mahyası", "L 2800")),
    ("OSB + Nem Bariyeri + Kiremit Desen Sac", "Metal kiremit (100 cm kapatır) · ana çatı", ("Metal kiremit mahyası", "L 2800")),
])
def test_yazili_opsiyon_aynen(N, kurallar, kaplama, kalem, mahya):
    """Opsiyon İş Emri'ne yazılır ve aynen okunur (düz mahya: metal kiremit mahyası L 2800); standart notu yazılmaz."""
    c = _cati(_liste(N, kurallar, kaplama))
    assert kalem in c and c[mahya[0]][0] == mahya[1]
    assert "Trapez sac mahyası" not in c


def test_tk01_r08_once_sonra(kurallar):
    """Lokman'a 10 Kasım 2026'da gösterilen TK-01 önce/sonra (proje dosyaları `Cati_Standardi_D74/`): r07 (Tek Kat Panel) ve r08 (Trapez Saç)."""
    once = _cati(PL.is_emrinden(_oku(VERI / "TK01_r07.json"), kurallar))
    sonra = _cati(PL.is_emrinden(_oku(VERI / "TK01_r08.json"), kurallar))
    assert once == {"Tek kat çatı paneli · ana çatı": ("L 5100", 20), "Tek kat çatı paneli · ön veranda çatısı": ("L 2400", 5),
                    "Tek kat çatı paneli · arka veranda çatısı": ("L 1770", 4), "Metal kiremit mahyası": ("L 2800", 6),
                    "Mahya bandı": ("rulo 10 m", 2), "Trapez vida 5,5 × 76 (tek kat panel)": ("adet", 600),
                    "Trapez vida 5,5 × 60 (trapez sac / metal kiremit)": ("adet", 300)}
    assert sonra == {"Trapez sac · ana çatı": ("L 5100", 20), "Trapez sac · ön veranda çatısı": ("L 2400", 5),
                     "Trapez sac · arka veranda çatısı": ("L 1770", 4), "Trapez sac mahyası": ("L 1000", 15),
                     "Mahya bandı": ("rulo 10 m", 2), "Trapez vida 5,5 × 60 (trapez sac)": ("adet", 600)}


def test_trapez_sacta_vida_tek_satir(N, kurallar):
    """Lokman, 10 Kasım 2026 08:38, karar kartı ("Trapez sacta m² × 2,5 vidası ayrı satır olarak eklensin mi?"): "Hayır, bugünkü tek satır
    kalsın". Trapez sacta 5,5 × 60 vida yalnız kaplama vidası satırı (panel boyundan); m² × 2,5 satırı tek kat panelde ve sandviç panelde.
    Gerçek listeler: kapatması bilinen 7 trapez evde 5,5 × 60 tek satır, kaplama vidası hesabıyla tutuyor; tek kat panelli evde m² satırı var."""
    m2 = "Trapez vida 5,5 × 60 (trapez sac / metal kiremit)"
    for kaplama in (None, "Trapez Saç"):
        c = _cati(_liste(N, kurallar, kaplama))
        assert m2 not in c and [k for k in c if k.startswith("Trapez vida 5,5 × 60")] == ["Trapez vida 5,5 × 60 (trapez sac)"], kaplama
    for kaplama in ("Tek Kat Panel", "Sandviç Panel"):
        assert _cati(_liste(N, kurallar, kaplama))[m2] == ("adet", 200), kaplama          # PK-01: m² × 2,5, 100'e yukarı


@pytest.mark.parametrize("eski, yeni", [("TK01_r07", "TK01_r08"), ("TK02", "TK02_r04")])
def test_yeni_revizyon_yalniz_kaplamada_ayrisir(eski, yeni):
    a, b = _oku(VERI / f"{eski}.json"), _oku(VERI / f"{yeni}.json")
    assert (a["ozellikler"]["Çatı Kaplaması"], b["ozellikler"]["Çatı Kaplaması"]) == ("Tek Kat Panel", "Trapez Saç")
    assert b["revizyon"] == a["revizyon"] + 1
    for x in (a, b):
        for k in ("revizyon", "varsayimlar"):
            x.pop(k)
        x["ozellikler"].pop("Çatı Kaplaması")
    assert a == b


def test_trapez_mahya_kanadi_35():
    Y = _oku(KOK / "kurallar" / "yerlesim" / "prefabrik.json")["kurallar"]
    g = Y["kenar_gosterim"]["kesit_cm"]["deger"]
    assert g["trapez_mahya"] == {"kanat": 35} and g["mahya"] == {"kanat": 26}
    ck = next(k for k in _oku(KOK / "kurallar" / "urun" / "kartlar.json")["kartlar"] if k["kod"] == "CK-07")
    assert "35 × 35 cm kanat" in ck["olcu"] and "L 1000" in ck["olcu"]


def test_kart_modeli_ayni_okur():
    """Kart modeli (İE-15) kaplamayı liste üretecinin işlevinden okur: yazılmamışsa trapez sac (uyarıyla; liste satırın kaynağına yazar)."""
    from motor import kart_model as KM
    from motor import yerlesim
    assert yerlesim.kaplama_yazisi({"ozellikler": {}}) == "trapez sac"
    assert yerlesim.kaplama_yazisi({"ozellikler": {"Çatı Kaplaması": "Sandviç Panel"}}) == "sandviç panel"
    C = yerlesim.degerler(_oku(KM.YERLESIM), _oku(KM.LISTE_KURALLARI))["cati_kaplamasi"]
    uyarilar = []
    assert yerlesim.kaplama_turu({"ozellikler": {}}, C, uyarilar) == ("trapez", None)
    assert uyarilar == [{"katman": "çatı kaplaması",
                         "metin": "İş Emri'nin çatı kaplaması \"yazılı değil\"; prefabrik standardı trapez sac sayıldı (D-74; liste üreteciyle aynı okuma)"}]
    uyarilar = []
    assert yerlesim.kaplama_turu({"ozellikler": {"Çatı Kaplaması": "Trapez Saç"}}, C, uyarilar) == ("trapez", None) and uyarilar == []
    assert yerlesim.kaplama_turu({"ozellikler": {"Çatı Kaplaması": "Tek Kat Panel"}}, C, uyarilar) == ("tek kat", None) and uyarilar == []
    assert yerlesim.trapez_kapatma_m({"ozellikler": {}}, C) == 1.0
