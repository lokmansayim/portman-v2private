"""İE-17 PR-1b/K7 · dört evin yükleme listesi (AP-15, AP-09, AP-03, AP-22). Liste çizimdeki çatıdan sayılır (D-28 tek kod): girintili
gövde ve açık mahalin kendi çatısı `cati_serit`'ten, beşik + çapraz cumba `cati_prefabrik`'ten; saçak, alın, dere içi ve kırma kenarları
çatının kendi kenarlarından (`cati_genel.cati_kur`). Evlerin kat planı ve çatısı mühürlüdür (M-07); bu dosya yalnız listeyi sabitler.

Makas yerleri (Lokman, 2 Kasım 2026 16:50, karar kartı: cumbanın iç ucuna makas "Bugünkü gibi konmasın"): orta makaslar saçak duvarının
pano eklerinde, ilk makas baş makasın kalkan duvarı kalınlığı kadar ötesine kadar; cumbada baş makas dış uçta, iç uçta makas yok.
AP-03'ün gerçek yükleme listesiyle kıyas (13 Ekim kaydı, E3) `docs/is_emirleri/IE-17.md` › PR-1b/K7 tablosunda."""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"


def _ie(kod: str) -> dict:
    return json.loads((EVLER / f"{kod}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def listeler():
    return {k: PL.is_emrinden(_ie(k)) for k in ("AP15", "AP09", "AP03", "AP22")}


@pytest.fixture(scope="module")
def catilar():
    return {k: {c["ad"]: c for c in PL.model_motor(_ie(k))["cati"]} for k in ("AP15", "AP09", "AP03", "AP22")}


def _adet(L: dict, kalem: str) -> int:
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, [x["kalem"] for x in L["satirlar"] if x["grup"] in ("1002", "1005", "1006", "1011")])
    return s[0]["adet"]


def _makaslar(L: dict) -> dict:
    return {x["kalem"]: x["adet"] for x in L["satirlar"] if x["grup"] == "1005" and "akas" in x["kalem"]}


def test_dort_evin_listesi_yazilir(listeler):
    """Dört evin listesi yazılır; makas toplamı listenin özetiyle aynı."""
    for k, L in listeler.items():
        assert L["satirlar"], k
        assert sum(_makaslar(L).values()) == L["girdi_ozeti"]["makas"], k


def test_ap15_makaslar_pano_eklerinde(listeler, catilar):
    """AP-15: ana çatıda 7 makas (2 baş + 5 orta; paftanın MK01–07'si, eşit aralıkla 8 değil), cumbada dış uçta 1 baş makas."""
    assert _makaslar(listeler["AP15"]) == {"Makas (baş) · ana çatı": 2, "Makas (orta) · ana çatı": 5, "Cumba makası · ön cumba": 1}
    assert catilar["AP15"]["ana çatı"]["makas_yeri"] == "pano ekleri"


def test_ap15_cumbanin_gorunen_sacagi(catilar):
    """AP-15'in cumbası 27,75 cm çıkıyor; saçağının ortası ana çatının 30'luk kalkan saçağının altına düşer. Kenar atılmaz, görünen kısmı
    (27,75 cm) sayılır; cumbanın öteki yanı ana çatının saçağıyla tek hat (8,607 m ana çatıda)."""
    c = catilar["AP15"]
    assert c["ana çatı"]["sacak_hatlari_m"] == [8.607, 8.33]
    assert c["ön cumba"]["sacak_hatlari_m"] == [0.278]


def test_ap09_cumba_ve_panel_cati(listeler):
    """AP-09: cumbada 3 makas (dış uçta baş + pano eklerinde 2; iç uca makas konmaz, Lokman 2 Kasım 16:50). Veranda %10 eğimli hafif çelik
    çatı paneli: makas ve aşık yerine panel; kenarları panel çatı kitabından (özel büküm saçak sacı, sundurma kapama, duvar dibi özel mahya)."""
    L = listeler["AP09"]
    assert _makaslar(L)["Cumba makası · ön cumba"] == 3
    assert _makaslar(L)["Makas (baş) · ana çatı"] + _makaslar(L)["Makas (orta) · ana çatı"] == 7
    assert _adet(L, "Özel büküm saçak sacı") == 2 and _adet(L, "Sundurma kapama") == 2 and _adet(L, "Özel mahya (geniş)") == 2
    assert _adet(L, "Tek kat çatı paneli · VERANDA çatısı") == 4


def test_ap22_capraz_cumba(listeler, catilar):
    """AP-22: ana çatı 9 makas (pano koşusu 9940 ÷ 1255 yukarı + 1; paftanın MK01–09'u), çapraz cumbada 3 yavru makas (MK10–12); cumbanın
    iki deresi ters mahya."""
    L = listeler["AP22"]
    assert _makaslar(L)["Makas (baş) · ana çatı"] == 2 and _makaslar(L)["Makas (orta) · ana çatı"] == 7
    assert _makaslar(L)["Yavru makas · cumba"] == 3
    assert catilar["AP22"]["cumba"]["dere_ici_m"] == [4.608, 4.608]
    assert _adet(L, "Ters mahya (dere içi)") == 4 and _adet(L, "Ters mahya kenar kutusu") == 8


def test_ap03_kose_kirmasi(listeler, catilar):
    """AP-03: verandanın köşe kırması ana çatının yüzü; 4 kısa makas ve kırmada 1 çapraz makas. Toplam 12 makas; gerçek liste 13, fark
    cumbanın iç ucundaki makas (Lokman 2 Kasım 16:50: konmasın). Dere içi (cumbayla) 1 ters mahya + 2 kenar kutusu, kırma hattı 1 kırma
    mahyası (gerçek listeyle aynı). Kırmanın ana çatının kalkan saçağı altında süren ucu alın sayılmaz."""
    L = listeler["AP03"]
    assert _makaslar(L) == {"Makas (baş) · ana çatı": 2, "Makas (orta) · ana çatı": 4, "Cumba makası · sağ cumba": 1,
                            "Kısa makas · VERANDA çatısı": 4, "Çapraz makas (kırma) · VERANDA çatısı": 1}
    v = catilar["AP03"]["VERANDA çatısı"]
    assert v["alin_kenarlari_m"] == [] and v["dere_ici_m"] == [2.258] and v["kirma_m"] == [1.822]
    assert _adet(L, "Ters mahya (dere içi)") == 1 and _adet(L, "Ters mahya kenar kutusu") == 2
    assert _adet(L, "Kırma mahyası (metal kiremit mahyası, çapraz eğim)") == 1
    assert catilar["AP03"]["sağ cumba"]["sacak_hatlari_m"] == []         # cumbanın saçağını verandanın deresi keser


def test_ap03_gercek_listeyle_tutanlar(listeler):
    """AP-03'ün gerçek listesiyle (E3) aynı çıkan çatı ve dere kalemleri; farklar iş emrinin tablosunda."""
    L = listeler["AP03"]
    gercek = {"Saçak sacı (30'luk, 3'ü menfezli)": 10, "Metal dere": 6, "Dere kelepçesi": 48, "100'lük duvar omegası": 3,
              "100'lük alt çerçeve": 9, "Özel kutu profil (kolon) 100 × 100": 1, "Mahya bandı": 2}
    assert {k: _adet(L, k) for k in gercek} == gercek
    assert sorted(x["olcu"] for x in L["satirlar"] if x["kalem"] == "Kutu profil (kiriş) 100 × 100") == ["L 1155", "L 4342,5"]


def test_kirma_ana_cati_yazilmaz():
    """Kırma ana çatının (AP-01) prefabrik kuralı kitapta yok: liste yazılmaz."""
    with pytest.raises(PL.ListeYazilmaz, match="kırmada kitapta prefabrik kural yok"):
        PL.is_emrinden(_ie("AP01"))
