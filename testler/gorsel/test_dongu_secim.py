"""Çizim okuma döngüsü tur 1 (27 Kasım 2026): çoğunluğun her okuması kodun tutarsızlık sorusunu doğuruyorsa, doğurmayan okuma seçilir."""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from beyin import gorsel_okuma as GO  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"


def _tk01() -> list[dict]:
    return json.loads((VERI / "DONGU_TK01_uc_okuma.json").read_text(encoding="utf-8"))["okumalar"]


def test_cogunluk_kod_sorusu_doguruyorsa_azinlik_secilir():
    ok = _tk01()
    sec, ozet = GO.cogunluk_sec(ok)
    assert ozet["kod_sorusu"] == [1, 1, 0]
    assert ozet["secilen"] == 2
    den = GO.denetle({**sec, "emin_olunamayanlar": []})
    assert not den["sorular"] and den["cevrim"] is not None


def test_cogunluk_temizse_kural_ayni():
    ok = _tk01()
    sec, ozet = GO.cogunluk_sec([ok[2], ok[2], ok[0]])
    assert ozet["cogunluk"] == 2 and ozet["secilen"] in (0, 1)


def test_tur3_yalniz_kapi_genisligi_sorusu_gitmez():
    assert GO.kapi_genislik_sorusu("Giriş kapısının genişliği çizimde yazmıyor")
    assert GO.kapi_genislik_sorusu("Giriş kapısı kaç cm?")
    assert not GO.kapi_genislik_sorusu("Verandadan salona açılan giriş kapısının genişliği ve tam yeri nedir?")
    assert not GO.kapi_genislik_sorusu("Banyo kapısı hangi odaya açılıyor?")
    assert not GO.kapi_genislik_sorusu("Hol ile salon arasında kapı var mı?")


def test_tur3_kapi_genisligi_notla_duser():
    ok = _tk01()[2]
    den = GO.denetle({**ok, "emin_olunamayanlar": ["Giriş kapısının genişliği çizimde yazmıyor"]})
    assert not den["sorular"]
    assert "kapılar standart genişlikte çizildi" in den["notlar"]


def test_tur4_yerle_tanitilan_pencerenin_olcusu_sorulmaz():
    assert GO.pencere_olcu_sorusu("Üst duvardaki küçük banyo penceresinin ölçüsü nedir?")
    assert not GO.pencere_olcu_sorusu("Banyo penceresi hangi duvarda?")
    assert not GO.pencere_olcu_sorusu("Pencere ölçüsü sol duvarda mı sağ duvarda mı?")
