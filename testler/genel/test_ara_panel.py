"""İE-16 PR-6b · kırma ucunun ara panelleri (`makas.ara_panelleri`; Lokman, 27 Ekim 2026, B1: "özel çatıların makas aralarında tam
çatı panelinin altına gelecek şekilde ara panel kullanırız") ve uç şeridinde kısalan kırma çaprazı.

- Sayılar kuralın bugünkü sonucu (gerileme). Paftayla kıyası İE-16 › Değişiklik (PR-6b): ÇP-03 18 (paftada MKP01–13), ÇP-07 25 (paftada
  kırma yüzünde Ç panelleri; uç şeridinde panel yok); açılan ÇP-17 ve ÇP-19'unki proje dosyasında (açılan listenin ve paftanın değerleri
  depoya girmez). Kırma ucu olmayan altı projede ara panel yok.
- Geometri: parçalar kendi düzleminin içinde ve birbirine binmez; kırma yüzünün parçaları yüzü bütünüyle örter (panel olmayan küçük parça
  uyarı yazar).
- Kırma çaprazı uç şeridinde: saçak köşesinden ilk ana makasa. Çapraz dışındaki makaslar anahtarsız kuralla aynı.
- Anahtarı olmayan kural kopyası (bugünkü listelerin `setler/8a051c8ff1a5d968.json`'u) ara panel kurmaz, çaprazı eskisi gibi tepeye uzatır.
- Liste ayrı satır yazar ("Ara paneller (kırma ucu)", hakemde makas türü); makas paftası çizer.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest
from shapely.geometry import Polygon

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_genel, girdi_genel, karkas, kural as kurallar_oku, makas, makas_pafta, yapi  # noqa: E402

PROJELER = KOK / "testler" / "celik" / "projeler"
KURAL = karkas.oku(karkas.KURAL)
ONCEKI = karkas.oku(PROJELER / "setler" / "8a051c8ff1a5d968.json")      # PR-6b'den önceki kural (listelerin kopyası), anahtarsız
TANIMLAR = {"CP03": "CP03/CP03.json", "CP06": "CP06/CP06_kural.json", "CP07": "CP07/CP07.json", "CP13": "CP13/CP13.json",
            "CP14": "CP14/CP14.json", "CP04": "CP04/CP04.json", "CP17": "CP17/CP17.json", "CP18": "CP18/CP18.json",
            "CP19": "CP19/CP19.json", "CP20": "CP20/CP20.json"}
YONTEM = {"CP03": "panel", "CP04": "panel"}                              # listelerin yöntemi (öteki sekizi B)
SAYILAR = {"CP03": {"kirma_yuzu": 4, "uc_seridi": 10, "kose": 4}, "CP07": {"kirma_yuzu": 5, "uc_seridi": 14, "kose": 6},
           "CP17": {"kirma_yuzu": 6, "uc_seridi": 13, "kose": 4}, "CP19": {"kirma_yuzu": 5, "uc_seridi": 12, "kose": 4}}


def _yukle(kod: str):
    t = json.loads((PROJELER / TANIMLAR[kod]).read_text(encoding="utf-8"))
    return t, cati_genel.cati_kur(t["cati"]), yapi.kur(t)


def _kur(kod: str, k: dict = KURAL) -> dict:
    t, _, y = _yukle(kod)
    return makas.kur(t, y, k, YONTEM.get(kod))


def test_kural_anahtari():
    """Ara panel yalnız yeni anahtarla (`ara_paneli`: et 0,8, ızgara 60 cm; Lokman'ın B1'i kaynakta); önceki kopyada anahtar yok."""
    ap = karkas.d(KURAL, "ara_paneli")
    assert ap == {"et": "0,8", "profil_araligi_cm": 60} and KURAL["ara_paneli"]["durum"] == "lokman"
    assert "makas aralarında tam çatı panelinin altına" in KURAL["ara_paneli"]["kaynak"]
    assert "ara_paneli" not in ONCEKI
    assert {a: v for a, v in KURAL.items() if a not in ("ara_paneli", "_yol", "_sha256")} == \
           {a: v for a, v in ONCEKI.items() if a not in ("_yol", "_sha256")}


@pytest.mark.parametrize("kod", sorted(TANIMLAR))
def test_ara_panel_sayilari(kod):
    """Bölge bölge sayı (gerileme); kırma ucu olmayan projede ara panel yok."""
    ap = _kur(kod)["ara_panelleri"]
    assert Counter(x["bolge"] for x in ap) == SAYILAR.get(kod, {})
    assert all(x["profil"] == "80x45x0,8" and x["profil_boyu_m"] > 0 for x in ap)


@pytest.mark.parametrize("kod", sorted(SAYILAR))
def test_parcalar_duzlemin_icinde_ve_binmez(kod):
    """Her parça kendi düzleminin içinde, iki parça birbirine binmez; kırma yüzünün parçaları (kırma yüzü ve uç şeridi) yüzün alanını
    örter, eksik kalan yalnız panel olmayan küçük parça (uyarısı yazılı: ÇP-19'un kuzey ucunda planda 69, açılımda 73 cm²); uyarısız
    düzlemde açık 1 cm²'den (kesişimin attığı kırıntı) küçük."""
    t, c, y = _yukle(kod)
    r = makas.kur(t, y, KURAL, YONTEM.get(kod))
    adli = {d["ad"]: d for d in c["duzlemler"]}
    ps = [(x, Polygon(x["plan"])) for x in r["ara_panelleri"]]
    for x, p in ps:
        assert p.difference(adli[x["duzlem"]]["cokgen"].buffer(0.05)).area < 0.01, x["plan"]
    for i, (_, p) in enumerate(ps):
        assert all(p.intersection(q).area < 0.01 for _, q in ps[i + 1:])
    kucuk = [u for u in r["uyarilar"] if u.startswith("ara panel:")]
    for H in {x["duzlem"] for x, _ in ps if x["bolge"] != "kose"}:
        eksik = adli[H]["cokgen"].area - sum(p.area for x, p in ps if x["duzlem"] == H)
        assert -0.5 < eksik < 1.0 + 100.0 * sum(f" {H} düzleminde " in u for u in kucuk), (H, eksik)
    if kod == "CP19":
        assert kucuk == ["ara panel: batı/doğu ailesinin kuzey düzleminde 73 cm² parça, kısa kenarı 8.8 cm (makas kalınlığı 8 cm, en küçük "
                         "parça 100 cm²): panel yok"]
    else:
        assert kucuk == []


@pytest.mark.parametrize("kod", sorted(SAYILAR))
def test_kirma_caprazi_uc_seridinde(kod):
    """Ara panelli kırma ucunda çapraz saçak köşesinden ilk ana makasa uzanır (uç ana makasın konumunda biter), anahtarsız kuralda
    tepeye; çapraz dışındaki makas kayıtları ve çaprazın sayısı iki kuralda aynı."""
    t, c, y = _yukle(kod)
    yeni, eski = makas.kur(t, y, KURAL, YONTEM.get(kod)), makas.kur(t, y, ONCEKI, YONTEM.get(kod))
    assert "ara_panelleri" not in eski
    assert [x for x in yeni["makaslar"] if x["tur"] != "capraz"] == [x for x in eski["makaslar"] if x["tur"] != "capraz"]
    cy, ce = ([x for x in m["makaslar"] if x["tur"] == "capraz"] for m in (yeni, eski))
    assert len(cy) == len(ce) > 0 and all(a["acik_cm"] < b["acik_cm"] for a, b in zip(cy, ce))
    adli, _, aile, _ = makas.aileler(c)
    seritler = makas.kirma_seritleri(adli, aile, yeni["aileler"])
    sinirlar = {(v["ee"], v["serit"][1] if v["i"] == 0 else v["serit"][0]) for v in seritler.values()}
    for x in cy:
        (px, py), (qx, qy) = x["s"]
        assert any(abs((qx if ee == "x" else qy) - kes) < 0.02 for ee, kes in sinirlar), x["s"]
        assert x["h_en_cok_cm"] < max(e["h_en_cok_cm"] for e in ce)


def test_kirma_ucunda_ana_makas_yoksa_uyari(monkeypatch):
    """Kırma yüzünün altından ana makas geçmiyorsa o uçta ara panel kurulmaz, uyarı yazar (sessiz düşme yok)."""
    monkeypatch.setattr(makas, "kirma_seritleri", lambda *a: {})
    r = _kur("CP19")
    assert r["ara_panelleri"] == []
    assert [u for u in r["uyarilar"] if "ana makas geçmiyor" in u] == [
        f"ara panel: batı/doğu ailesinin {H} kırma yüzünün altından ana makas geçmiyor; o uçta ara panel yok" for H in ("güney", "kuzey")]


def test_capraz_ilk_ana_makasi_kesmezse_uyari(monkeypatch):
    """Şerit bulunduğu hâlde kırma çizgisi şeridin sınırını (ilk ana makas) kesmiyorsa çapraz kırpılmaz, kaydı anahtarsız kuralla aynı
    kalır ve uyarı yazar (sessiz düşme yok)."""
    gercek = makas.kirma_seritleri

    def uzak(*a):
        s = gercek(*a)
        for v in s.values():
            v["serit"] = (1e6, 1e6 + 1)
        return s
    monkeypatch.setattr(makas, "kirma_seritleri", uzak)
    t, _, y = _yukle("CP19")
    yeni, eski = makas.kur(t, y, KURAL), makas.kur(t, y, ONCEKI)
    cy, ce = ([x for x in m["makaslar"] if x["tur"] == "capraz"] for m in (yeni, eski))
    assert cy == ce and cy
    assert len([u for u in yeni["uyarilar"] if "çapraz kırpılmadı" in u]) == len(cy)


def _girdi(kod: str) -> dict:
    kur = kurallar_oku.oku()
    t, _, y = _yukle(kod)
    c = cati_genel.cati_kur(t["cati"], kur)
    return girdi_genel.girdi(y, c, girdi_genel.metraj(y, c, kur), kur, "test")


def test_liste_satiri_ve_hakem_turu(monkeypatch):
    """Gruplar ve yükleme girdisi: ara panel ayrı satır, adet ve profil boyu karkas kuralından; hakemde makas türü (ÇP-03'ün
    listesinde "makas paneli"). Anahtarsız kural kopyasında satır yok."""
    from testler.celik.projeler import liste_yap
    kur = kurallar_oku.oku()
    t, _, y = _yukle("CP19")
    kk = karkas.kur(y, t, KURAL)
    g = karkas.gruplar(kk, y, t, KURAL, kur["celik"]["profil_kg_m"]["deger"])
    ap = kk["cati"]["ara_panelleri"]
    assert g["ara_paneli"]["adet"] == len(ap) == 21 and g["ara_paneli"]["profil"] == "80x45x0,8"
    assert round(g["ara_paneli"]["profil_boyu_m"], 3) == round(sum(x["profil_boyu_m"] for x in ap), 3)
    es = [x for x in _girdi("CP19")["celik"]["ek_satirlar"] if x["ad"] == "Ara paneller (kırma ucu)"]
    assert [(x["panel_adedi"], x["profil"]) for x in es] == [(21, "80x45x0,8")] and "karkas kuralından" in es[0]["not"]
    assert liste_yap.celik_turu("Ara paneller (kırma ucu)") == "makas"
    monkeypatch.setenv("PORTMAN_KARKAS", str(PROJELER / "setler" / "8a051c8ff1a5d968.json"))
    assert not [x for x in _girdi("CP19")["celik"].get("ek_satirlar", []) if x["ad"].startswith("Ara panel")]
    assert "ara_paneli" not in karkas.gruplar(karkas.kur(y, t, ONCEKI), y, t, ONCEKI, kur["celik"]["profil_kg_m"]["deger"])


def test_makas_paftasi_ara_panelleri_cizer(tmp_path, monkeypatch):
    """Makas paftası ara panelleri planda çizer (A01…) ve tabloda bölge bölge yazar; anahtarsız kuralda sayı da yazılmaz."""
    yazilan = []
    gercek = makas_pafta.tablo
    monkeypatch.setattr(makas_pafta, "tablo", lambda ax, *a: (gercek(ax, *a), yazilan.append(ax.texts[-1].get_text())))
    t, _, _ = _yukle("CP19")
    r = makas_pafta.ciz(t, tmp_path, "CP19")
    assert r["ara_paneli"] == 21 and (tmp_path / r["png"]).stat().st_size > 0
    assert "Ara panel 21 (A01–A21; kırma ucu: kırma yüzü 5, uç şeridi 12, köşe 4)" in yazilan[0].replace("\n", " ")
    (tmp_path / "eski").mkdir()
    r0 = makas_pafta.ciz(t, tmp_path / "eski", "CP19", kural_k=ONCEKI)
    assert "ara_paneli" not in r0
