"""BK-71 (D-145) · çizim okuyucunun ikinci bakışı: kod soru çıkarınca okuyucu çizime soruların listesiyle bir kez daha bakar; hangi
okumanın bayiye gideceğine kod karar verir. LLM yok: manuel arka uç, girdi BK-70'in 22 Kasım okumaları (`veri/BK70_*`). Ayar kapalıyken
(varsayılan) akış bugünküyle aynıdır.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kanal"))
from beyin import gorsel_okuma as GO  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"


def _okuma(ad: str) -> dict:
    return json.loads((VERI / f"BK70_{ad}_okuma.json").read_text(encoding="utf-8"))


def _sorusuz(o: dict) -> dict:
    return {**o, "emin_olunamayanlar": []}


def test_ikinci_bakis_soruyu_azaltirsa_kod_onu_secer():
    ilk = _okuma("TK06")
    den = GO.denetle(ilk)
    assert den["sorular"]
    b = GO.ikinci_bakis(ilk, den["sorular"], Path("yok.png"), "image/png", ayar={"backend": "manuel"},
                        hazir={"niyet": "duzeltme", "okuma": _sorusuz(ilk), "degisenler": ["çizimde ölçü yazıyor"]})
    assert b["durum"] == "tamam" and b["cagri"] == 0 and b["degisenler"]
    okuma, den2, secildi = GO.ikinci_bakis_sec(ilk, den, b["okuma"])
    assert secildi and not den2["sorular"] and den2["cevrim"]["is_emri"]


def test_ikinci_bakis_soruyu_azaltmazsa_ilk_okuma_kalir():
    ilk = _okuma("TK06")
    den = GO.denetle(ilk)
    okuma, den2, secildi = GO.ikinci_bakis_sec(ilk, den, ilk)          # aynı okuma: soru sayısı aynı
    assert not secildi and okuma is ilk and den2 is den
    okuma, _, secildi = GO.ikinci_bakis_sec(ilk, den, None)            # ikinci bakış hata verdi
    assert not secildi and okuma is ilk


def test_ikinci_bakis_bos_okuma_hata_doner():
    b = GO.ikinci_bakis(_okuma("TK06"), ["x"], Path("yok.png"), "image/png", ayar={"backend": "manuel"},
                        hazir={"niyet": "duzeltme", "okuma": None})
    assert b["durum"] == "hata" and b["okuma"] is None


def _gorsel_oku(tmp_path, ikinci_bakis: bool, ikinci: dict | None):
    import worker
    resim = tmp_path / "cizim.png"
    resim.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    hazir = {"okuma": _okuma("TK06")}
    if ikinci is not None:
        hazir["ikinci_bakis"] = ikinci
    hd = tmp_path / "hazir.json"
    hd.write_text(json.dumps(hazir, ensure_ascii=False), encoding="utf-8")
    settings = {"gorsel_okuma": {"acik": True, "backend": "manuel", "hazir_dosya": str(hd), "max_tokens": 8000, "timeout_s": 10,
                                 "ikinci_bakis": ikinci_bakis}}
    return worker.gorsel_oku({"text": ""}, settings, {"yol": str(resim), "mime": "image/png", "boyut": 72, "sha256": "x"})


def test_worker_ayar_kapaliyken_ikinci_bakis_yok(tmp_path):
    s = _gorsel_oku(tmp_path, False, {"niyet": "duzeltme", "okuma": _sorusuz(_okuma("TK06"))})
    assert s["durum"] == "tamam" and "ikinci_bakis" not in s
    assert s["okuma"] == _okuma("TK06")


def test_worker_ayar_acikken_ikinci_okuma_secilir(tmp_path):
    s = _gorsel_oku(tmp_path, True, {"niyet": "duzeltme", "okuma": _sorusuz(_okuma("TK06")), "degisenler": ["a"]})
    ib = s["ikinci_bakis"]
    assert ib["secildi"] and ib["soru_once"] > 0 and ib["soru_sonra"] == 0
    assert s["okuma"]["emin_olunamayanlar"] == []


def test_worker_ikinci_bakis_hata_verirse_ilk_okuma_kalir(tmp_path):
    s = _gorsel_oku(tmp_path, True, None)                              # kayıtlı cevap yok → manuel arka uç hata verir
    assert s["durum"] == "tamam" and s["okuma"] == _okuma("TK06")
    assert s["ikinci_bakis"]["durum"] == "hata" and not s["ikinci_bakis"]["secildi"]


def test_varsayilan_ayarda_ikinci_bakis_kapali():
    import ayarlar
    assert ayarlar.VARSAYILAN["gorsel_okuma"]["ikinci_bakis"] is False


# D-148 (Lokman 23 Kasım 11:54:43, 11:55:43): standartlar sorulmaz; plan onayından sonra formda gider
def test_d148_standart_sorulari_bayiye_gitmez_not_yazilir():
    o = {**_okuma("TK06"), "emin_olunamayanlar": ["Kat sayısı ve yapı türü (prefabrik/çelik) belirtilmemiş",
                                                  "Çatı tipi ve duvar yüksekliği belirtilmemiş (görünüş yok)",
                                                  "'Bina Yüksekliği 2500 mm' duvar yüksekliği mi, toplam yükseklik mi?"]}
    den = GO.denetle(o)
    assert not den["sorular"] and den["cevrim"]["is_emri"]
    assert any("formda gelecek" in n for n in den["notlar"])


def test_d148_pencere_kapi_ve_zincir_sorulari_kalir():
    for s in ("Pencere yükseklikleri ve banyo penceresinin ölçüsü nedir?", "Giriş kapısının genişliği yazmıyor",
              "Üst ölçü zinciri 261+126+188+324 = 899 ediyor, toplamda 898 yazıyor; hangisi doğru?"):
        assert not GO.standart_sorusu(s), s
    for s in ("Kat sayısı yazmıyor; tek kat mı?", "Çatı eğimi ve saçak taşması yazmıyor (görünüşte mahya yüksekliği 142 cm)",
              "Yapı türü (prefabrik/çelik) yazmıyor"):
        assert GO.standart_sorusu(s), s
