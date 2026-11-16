"""Havuz denetimi (`araclar/havuz_denetimi.py`): havuz listesi, makas sayımı ve bir evde uçtan uca koşu. Araç yalnız okur."""
import json
from pathlib import Path

from araclar import havuz_denetimi as HD

KOK = Path(__file__).resolve().parent.parent


def test_havuz_evleri_tam_ve_tekil():
    evler = HD.havuz_evleri()
    kodlar = [e["kod"] for e in evler]
    assert len(kodlar) == len(set(kodlar))
    assert all(Path(e["yol"]).exists() for e in evler)
    assert {"prefabrik", "genel"} == {e["motor"] for e in evler}
    assert "PA06K" in kodlar and "KT04" in kodlar               # çatı varyantı ve bankanın kabul modeli de havuzda


def test_kart_kodu_kayittan():
    assert HD._kart_kodu({"kaynak": {"kart_kiyasi": {"kart": "AP-05"}}}) == "AP-05"
    assert HD._kart_kodu({"kaynak": {"dosya": "testler/cizim/evler/AP15.json"}}) == "AP-15"
    assert HD._kart_kodu({"kaynak": {}}) is None


def test_makas_sayimi_parca_parca():
    sat = [{"grup": "1005", "kalem": "Makas (baş) · ana çatı", "adet": 2},
           {"grup": "1005", "kalem": "Makas (orta) · ana çatı", "adet": 5},
           {"grup": "1005", "kalem": "Cumba makası · sağ cumba", "adet": 1},
           {"grup": "1005", "kalem": "Çatı paneli (makas arası) · VERANDA çatısı", "adet": 4},
           {"grup": "1002", "kalem": "Baş makas omegası", "adet": 9}]
    assert HD.makas_sayisi(sat) == 8
    assert HD.parca_makaslari(sat) == {"ana çatı": 7, "sağ cumba": 1}


def test_bir_ev_uctan_uca():
    ie = json.loads((KOK / "is_emri" / "adaylar" / "PA11.json").read_text(encoding="utf-8"))
    r = HD.denetle_prefabrik(ie)
    assert not [b for b in r["bulgular"] if b["sinif"] == "hata"], r["bulgular"]
    assert r["makas"] == r["makas_3d"] and r["makas"]
    assert "| PA11 |" in HD.markdown({"PA11": r})


# ---------------------------------------------------------------- kayıt kapısı (D-112, BK-47)

HATA = {"bulgular": [{"kalem": "HD-05", "sinif": "hata", "metin": "3D kurulamadı: deneme"},
                     {"kalem": "HD-02", "sinif": "uyari", "metin": "deneme uyarısı"},
                     {"kalem": "HD-07", "sinif": "bilgi", "metin": "makas: liste 7, gerçek proje 8"}]}


def test_kayit_kapisi_siniflari():
    dur, uyari = HD.kayit_kapisi(HATA)
    assert len(dur) == 1 and dur[0].startswith("HD-05 3D model (IFC) kurulur") and uyari == ["HD-02: deneme uyarısı"]
    assert HD.kayit_kapisi({"bulgular": HATA["bulgular"][1:]}) == ([], ["HD-02: deneme uyarısı"])
    assert {k for k, s in HD.SINIF.items() if s == "hata"} == {"HD-01", "HD-03", "HD-04", "HD-05", "HD-08", "HD-10"}


def test_havuza_mi():
    assert HD.havuza_mi(True, "test") and HD.havuza_mi(False, "gecerli") and HD.havuza_mi(False, "kosullu")
    assert not HD.havuza_mi(False, "test") and not HD.havuza_mi(True, "gecerli", test_dosyasi=True)


def _yazilan():
    return {p for d in ("is_emri/adaylar", "beyin/veri/havuz", "beyin/veri/cati_varyantlari") for p in (KOK / d).iterdir()}


def test_aday_kaydet_hatali_evi_yazmaz(monkeypatch, capsys):
    """Prefabrik: havuz denetiminde hata veren ev havuza yazılmaz (şablon, görsel, kayıt yok)."""
    import sys
    from araclar import aday_kaydet as AK
    monkeypatch.setattr(HD, "denetle_prefabrik", lambda ie, kart=None: HATA)
    once = _yazilan()
    monkeypatch.setattr(sys, "argv", ["aday_kaydet.py", str(KOK / "is_emri/adaylar/PA11.json"), "--kod", "PA-97", "--durum", "test",
                                      "--havuz", "--standart"])
    assert AK.main() == 1
    cikti = capsys.readouterr().out
    assert "DUR: havuz denetimi geçmedi (D-112)" in cikti and "HD-05" in cikti
    assert _yazilan() == once


def test_aday_kaydet_celik_hatali_evi_yazmaz(monkeypatch, capsys):
    """Çelik: aynı kapı; genel motorun koşusu kapıdan sonra."""
    import sys
    from araclar import aday_kaydet as AK
    monkeypatch.setattr(HD, "denetle_genel", lambda tanim: HATA)
    once = _yazilan()
    monkeypatch.setattr(sys, "argv", ["aday_kaydet.py", "--motor", "genel", "--tanim", "modeller/KT01.json", "--kod", "KT-99",
                                      "--durum", "test", "--havuz"])
    assert AK.main() == 1
    assert "DUR: havuz denetimi geçmedi (D-112)" in capsys.readouterr().out
    assert _yazilan() == once


def test_cati_varyanti_hatali_secenegi_yazmaz(monkeypatch, capsys):
    """Çatı seçeneği: bütün seçenekler dosya yazılmadan denetlenir; hata veren varsa hiçbir dosya yazılmaz."""
    import sys
    from araclar import cati_varyanti_kaydet as CV
    monkeypatch.setattr(HD, "denetle_prefabrik", lambda ie, kart=None: HATA)
    once = _yazilan()
    cati = json.loads((KOK / "is_emri/adaylar/PA06K.json").read_text(encoding="utf-8"))["cati"]
    monkeypatch.setattr(sys, "argv", ["cati_varyanti_kaydet.py", "--taban", "PA-06", "--karar", "D-83", "--cati-adi", "Beşik",
                                      "--varyant", "K", "Kırma", json.dumps(cati)])
    assert CV.main() == 1
    assert "PA-06-K havuz denetimi geçmedi (D-112)" in capsys.readouterr().out
    assert _yazilan() == once
