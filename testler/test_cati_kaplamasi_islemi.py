"""İE-20 PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC "Plana ve listeye işlensin") · `cati_kaplamasi` işlemi ve genel motor.

Çelik talep formunda seçilen çatı kaplaması Yapı Tanımı'nın `cati.kaplama` alanına yazılır (`beyin/varyant.cati_kaplamasi`); genel motor
pafta tablosunu ("Çatı Kaplaması") ve yükleme listesini bu alandan üretir. Bu dosya üç şeyi denetler:
1. İşlem yalnız `cati`'yi değiştirir; standart kaplamada tanım aynen kalır (bugünkü çıktı bayt bayt aynı).
2. Hedef çıktı (Ç8801 + sandviç panel): pafta tablosunda "Sandviç Panel", listede sandviç panel satırları, kapaması ve 5,5 × 110 vida.
3. `varyant.CIZILEN_KAPLAMALAR` genel motorun gerçekten hesapladığı kaplamalardır: kural kitabının altı kaplamasından motorun ürettiği
   her kaplama listededir, üretemediği hiçbir kaplama listede değildir (Motor bir kaplamayı öğrenince bu test listeyi genişlettirir).

Postgres, ağ, LLM ve WhatsApp yok. Koşum: python -m pytest testler/test_cati_kaplamasi_islemi.py -q
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path

import pytest

from beyin import varyant
from motor.genel import kural
from motor.genel import uret as U

KOK = Path(__file__).resolve().parents[1]


def _tanim(kod: str = "C8801") -> dict:
    return json.loads((KOK / "modeller" / f"{kod}.json").read_text(encoding="utf-8"))


def _uret(t: dict, hedef: Path, bayi: bool = False) -> dict | None:
    """Worker'ın çağrısı gibi (`kanal/worker.cizim_genel`: yöntem panel, güncel kural kitabı); perspektifsiz. Motor tanımı reddederse None."""
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "tanim.json").write_text(json.dumps(t, ensure_ascii=False), encoding="utf-8")
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            m = U.uret(hedef / "tanim.json", hedef, is_emri_no="PM-TEST", revizyon=1, set_yolu=None, yontem="panel", perspektif=False,
                       bayi=bayi, kaynak="test", bilgi={"ozellikler": {}, "ozel_istekler": []} if bayi else None)
    except SystemExit:
        return None
    return m if list(hedef.glob("*_yukleme.json")) and list(hedef.glob("*_plan.png")) else None


def _liste(hedef: Path) -> dict:
    [yol] = list(hedef.glob("*_yukleme.json"))
    return json.loads(yol.read_text(encoding="utf-8"))


def test_islem_yalniz_cati_kaplamasini_degistirir():
    t0 = _tanim()
    assert "kaplama" not in t0["cati"] and varyant.kaplama_oku(t0) == "tek_kat_panel" == kural.oku()["baz_paket_cati_kaplamasi"]["deger"]
    t1 = varyant.tanim_uygula(t0, {"op": "cati_kaplamasi", "kaplama": "sandvic_panel"})
    assert t1 is not t0 and "kaplama" not in t0["cati"]                                    # saf: girdi değişmez
    assert varyant.kaplama_oku(t1) == "sandvic_panel"
    assert {a: v for a, v in t1.items() if a != "cati"} == {a: v for a, v in t0.items() if a != "cati"}
    assert {a: v for a, v in t1["cati"].items() if not a.startswith("kaplama")} == t0["cati"]
    # modelin zaten taşıdığı kaplama: tanım aynen (Ç8801'de standart; KT-02 kendi paftasında sandviç panel)
    assert varyant.tanim_uygula(t0, {"op": "cati_kaplamasi", "kaplama": "tek_kat_panel"}) == t0
    kt = _tanim("KT02")
    assert varyant.kaplama_oku(kt) == "sandvic_panel" and varyant.tanim_uygula(kt, {"op": "cati_kaplamasi", "kaplama": "sandvic_panel"}) == kt
    # motorun hesaplamadığı ya da bilinmeyen kaplama: VaryantHatasi (çizim düşmez, kural katmanı bayiye söyler)
    for kotu in ("osb_kiremit", "trapez_sac", "osb_trapez", "osb_shingle", "kamis", None):
        with pytest.raises(varyant.VaryantHatasi):
            varyant.tanim_uygula(t0, {"op": "cati_kaplamasi", "kaplama": kotu})
    assert [varyant.kaplama_adi(x) for x in varyant.CIZILEN_KAPLAMALAR] == ["tek kat panel", "sandviç panel"]


def test_hedef_cikti_sandvic_panel_tabloda_ve_listede(tmp_path):
    """Hedef (D-97): Ç8801'de sandviç panel seçilince pafta tablosu "Sandviç Panel" yazar; listede panel satırlarının adı, kapaması ve
    vidası sandviç panele göredir. Plan ve görünüş çizimi değişmez (kaplama geometriyi değiştirmez)."""
    t0 = _tanim()
    t1 = varyant.tanim_uygula(t0, {"op": "cati_kaplamasi", "kaplama": "sandvic_panel"})
    assert _uret(t0, tmp_path / "once", bayi=True) and _uret(t1, tmp_path / "sonra", bayi=True)
    oz = {ad: json.loads(next((tmp_path / ad).glob("*_pafta_ozet.json")).read_text(encoding="utf-8"))["ozellikler"] for ad in ("once", "sonra")}
    assert oz["once"]["Çatı Kaplaması"] == "Tek Kat Panel" and oz["sonra"]["Çatı Kaplaması"] == "Sandviç Panel"
    assert {a: v for a, v in oz["once"].items() if a != "Çatı Kaplaması"} == {a: v for a, v in oz["sonra"].items() if a != "Çatı Kaplaması"}
    once, sonra = _liste(tmp_path / "once"), _liste(tmp_path / "sonra")
    assert once["cati_kaplamasi_anahtar"] == "tek_kat_panel" and sonra["cati_kaplamasi_anahtar"] == "sandvic_panel"
    satir = lambda y: {(s["grup"], s["kalem"], s["boyut"], s["adet"]) for s in y["satirlar"]}      # noqa: E731
    assert satir(once) - satir(sonra) == {("Çatı kaplamaları", "Tek kat panel", "L 3740 · 100 cm kapatır", 21),
                                          ("Çatı kaplamaları", "Tek kat panel", "L 2480 · 100 cm kapatır", 10),
                                          ("Vida", "Trapez vida (5,5 × 76; tek kat panel)", "adet", 750)}
    assert satir(sonra) - satir(once) == {("Çatı kaplamaları", "Sandviç panel", "L 3740 · 100 cm kapatır", 21),
                                          ("Çatı kaplamaları", "Sandviç panel", "L 2480 · 100 cm kapatır", 10),
                                          ("Çatı kaplamaları", "Sandviç panel kapaması", "L 2500", 10),
                                          ("Vida", "Trapez vida (5,5 × 110; sandviç panel)", "adet", 750)}
    for ad in ("C8801_plan.png", "C8801_gorunusler.png"):                                           # çizimin geometrisi aynı
        assert (tmp_path / "once" / ad).read_bytes() == (tmp_path / "sonra" / ad).read_bytes(), ad


def test_cizilen_kaplamalar_motorun_hesapladiklaridir(tmp_path):
    """Kural kitabının altı kaplamasından genel motorun Ç8801'i ürettiği kaplamalar `varyant.CIZILEN_KAPLAMALAR` ile aynıdır."""
    kitap = list(kural.oku()["cati_kaplama"]["deger"])
    assert len(kitap) == 6 and set(varyant.CIZILEN_KAPLAMALAR) <= set(kitap)
    uretilen = []
    for kap in kitap:
        t = copy.deepcopy(_tanim())
        t["cati"]["kaplama"] = kap
        if _uret(t, tmp_path / kap):
            uretilen.append(kap)
    assert sorted(uretilen) == sorted(varyant.CIZILEN_KAPLAMALAR)
