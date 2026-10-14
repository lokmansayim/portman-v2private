"""BK-08 madde 9 · `beyin/numara.py`: serbest metindeki telefon numaraları boşluklu, tireli, parantezli ve `+90`'lı yazılsa da maskelenir;
ölçü, ondalık, tarih, model kodu ve İş Emri numarası maskelenmez. Üç kullanım: pafta alanları (`celik.numarasiz` → "…"), günlük ve
Patron metni (`worker.maske_numaralar` → "…" + son dört), D-01 yönlendirme gerekçesi (`karar._eski_taslak_sor`). LLM ve Postgres yok.
Numaralar uydurmadır (abone kısmı 000 07 77; cep biçimi çalışma anında kurulur)."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "kanal"))
from beyin import celik, karar as K, numara  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
import worker as W  # noqa: E402

CEP = "0" + "5" + "00 000 07 77"           # cep biçimi (5xx); dosyada düz yazılmaz

MASKELENIR = [
    "0212 000 07 77", "0212-000-0777", "0212-000-07-77", "0 212 000 07 77", "(0212) 000 07 77", "+90 212 000 07 77",
    "+90 (212) 000-07-77", "+902120000777", "0090 212 000 07 77", "0850 000 07 77", "02120000777", "900000000777",
    CEP, CEP[1:], CEP.replace(" ", "-"), "(" + CEP[1:4] + ")" + CEP[4:], "+90" + CEP[1:], "+44 20 7946 0777",
]
DOKUNULMAZ = [
    "120x180", "120 x 180", "120/180", "58,37", "56,54 m²", "88 m²", "Ç8801", "KT-02", "13.10.2026", "2026-10-14 13:05",
    "350 400 300 250", "350 400 30 25", "1024 x 860", "1.250.000 TL", "PM-B01-20261014-12345", "PM-B01-20261014-01234",
    "Portman_PM-B01-20261014-12345_r02.pdf", "0 350 400 300", "900 000 07 77", "2 adet 120x120 pencere",
]


@pytest.mark.parametrize("tel", MASKELENIR)
def test_numara_maskelenir(tel):
    metin = f"müşteri {tel} arayacak"
    assert numara.maskele(metin) == "müşteri … arayacak"
    assert numara.maskele(metin, son_dort=True) == "müşteri …0777 arayacak"


@pytest.mark.parametrize("metin", DOKUNULMAZ)
def test_olcu_tarih_kod_dokunulmaz(metin):
    assert numara.maskele(metin) == metin and numara.maskele(metin, son_dort=True) == metin


def test_bilinen_sinir_oneksiz_sabit_hat():
    """Öneksiz sabit hat ("212 000 07 77") maskelenmez: öneksiz 3-3-2-2 yalnız cepte (5xx) numara sayılır, yoksa ölçü listesi
    ("350 400 30 25") de maskelenirdi. Bilinen sınır; BK-08 › Riskler."""
    assert numara.maskele("212 000 07 77") == "212 000 07 77"


def test_cumle_icinde_yalniz_numara_maskelenir():
    m = f"mutfak penceresi 120x120 olsun, numaram {CEP}, 3 adet; sevk 14.10.2026"
    assert numara.maskele(m) == "mutfak penceresi 120x120 olsun, numaram …, 3 adet; sevk 14.10.2026"


def test_pafta_alanlari_ve_worker_ayni_desen():
    assert celik.numarasiz(f"sevk: Adres 12, tel {CEP}") == "sevk: Adres 12, tel …"
    assert W.maske_numaralar(f"hata: {CEP} / 900000000777") == "hata: …0777 / …0777"


def test_celik_zarfinda_bosluklu_numara_paftaya_girmez():
    aday = {"kod": "Ç8801", "tanim": "modeller/C8801.json"}
    ts = {"musteri": {"sevk_adresi": "Deneme mah. 1, tel 0212 000 07 77"}, "ozel_istekler": [f"müşteri {CEP} arasın"],
          "bina_ozellikleri": {}}
    ie = celik.zarf(aday, {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi"}, None, ts, None)
    b = ie["bilgi"]
    assert b["sevk_adresi"] == "Deneme mah. 1, tel …" and b["ozel_istekler"] == ["müşteri … arasın"]


def test_d01_gerekcesinde_bekleyen_mesaj_numarasiz(tmp_path):
    k = Konusma("900000000101", kok=tmp_path)
    k.d["eski_taslak_soru"] = K.ESKI_TASLAK_EN_COK
    k.d["bekleyen_metin"] = "P6001 aynalı olsun, müşteri +90 (212) 000-07-77"
    karar = K._eski_taslak_sor(k)
    assert karar.eylem == "yonlendir" and "bekleyen mesaj" in karar.gerekce and "P6001" in karar.gerekce
    assert "…0777" in karar.gerekce and "000-07-77" not in karar.gerekce
