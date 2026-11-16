"""D-118 kilit testi: prefabrikte standart yükseklik 2,50 m.

Lokman, 16 Kasım 2026 20:57:59 UTC: "prefabrik te standart yüksekli ne?"; 20:58:27: "kesin kural bunu mühürle 2,50 m".
Dayanak D-14 (Lokman, 13 Ekim 2026 07:28): %80 H 2500 mm, %19 H 2800, %1 H 3000; başka ölçü yok.

Kural:
- İş Emri yükseklik yazmazsa Motor 2,50 m alır: panolar 2500 mm, lento 50 cm (pencere ve kapı üst kotu 200 cm);
- yükseklik kümesinin ilki 250 (Motor, kural kitabı); yükleme listesinin standart pano yüksekliği 250;
- talep formunun standardı 250 cm, formda "250 cm (standart)" seçili gelir;
- 2,80 ve 3,00 m yalnız yazılırsa (D-14); Motor başka ölçüyü reddeder.
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
from motor import prefabrik_liste as PL  # noqa: E402

ORNEK = KOK / "is_emri" / "adaylar" / "PA01.json"   # 60 m² 2+1, havuzda 2,50 m


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_kume_ve_standart():
    assert G.PANO_YUKSEKLIKLERI_CM[0] == 250.0
    assert set(G.PANO_YUKSEKLIKLERI_CM) == {250.0, 280.0, 300.0}
    assert PL.STANDART_PANO_CM == 250
    dt = _oku(KOK / "kurallar" / "model" / "duvar_tipleri.json")
    assert dt["tipler"]["PE-DIS-100"]["pano"]["yukseklik_cm"][0] == 250


def test_lento_50():
    """2,50 m'de lento 50 cm: pencere ve kapı üst kotu 200 cm (yükseklik − üst kot)."""
    assert G.PENCERE_UST_KOTU_CM == 200.0
    assert 250.0 - G.PENCERE_UST_KOTU_CM == 50.0


def test_talep_formu_standardi():
    from kanal import talep_formu as TF
    assert TF.STANDART["yukseklik"] == "250"
    assert list(TF.YUKSEKLIK) == ["250", "280", "300"]
    f = _oku(KOK / "kanal" / "formlar" / "prefabrik.json")
    ekran = {e["id"]: e for e in f["screens"]}["OZELLIK_P"]
    alan = {c.get("name"): c for c in ekran["layout"]["children"]}["yukseklik"]
    assert alan["init-value"] == "250"
    assert {d["id"]: d["title"] for d in alan["data-source"]}["250"] == "250 cm (standart)"


@pytest.fixture(scope="module")
def yaziz_liste():
    ie = copy.deepcopy(_oku(ORNEK))
    ie["yapi"].pop("duvar_yuksekligi_cm", None)
    N = PL.model_motor(ie)
    return N, PL.liste(N, PL.kurallari_oku())


def test_yukseklik_yazilmazsa_250(yaziz_liste):
    N, L = yaziz_liste
    assert N["H0"] == 250.0
    panolar = [s for s in L["satirlar"] if s["grup"] == "1001" and "pano" in s["kalem"] and s["kalem"] != "Pencere üst panel"]
    assert panolar and all(s["olcu"].endswith("× 2500") for s in panolar)
    ust = [s for s in L["satirlar"] if s["kalem"] == "Pencere üst panel"]
    assert ust and all(s["olcu"].endswith("× 500") for s in ust)   # lento 50 cm


def test_yazili_250_ile_ayni(yaziz_liste):
    """Yükseklik yazılmayan İş Emri ile 250 yazılan İş Emri aynı listeyi verir."""
    _, L0 = yaziz_liste
    L1 = PL.liste(PL.model_motor(_oku(ORNEK)), PL.kurallari_oku())
    satir = lambda L: [(s["kalem"], s["olcu"], s["adet"]) for s in L["satirlar"]]  # noqa: E731
    assert satir(L0) == satir(L1)
