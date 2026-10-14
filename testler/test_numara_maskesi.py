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
    CEP.replace(" ", "\u00a0"), "+90\u00a0212\u00a0000\u00a007\u00a077", "0212\u2013000\u201307\u201377", "0212\u2009000\u200907\u200977",
]
DOKUNULMAZ = [
    "120x180", "120 x 180", "120/180", "58,37", "56,54 m²", "88 m²", "Ç8801", "KT-02", "13.10.2026", "2026-10-14 13:05",
    "350 400 300 250", "350 400 30 25", "1024 x 860", "1.250.000 TL", "PM-B01-20261014-12345", "PM-B01-20261014-01234",
    "Portman_PM-B01-20261014-12345_r02.pdf", "0 350 400 300", "900 000 07 77", "2 adet 120x120 pencere",
    "540 300 20 10 cm", "532 120 45 67 cm", "oda 540 300 25 25 m olsun", "540 300 2025 mm", "250 300 20 10 x 2",
]


@pytest.mark.parametrize("tel", MASKELENIR)
def test_numara_maskelenir(tel):
    metin = f"müşteri {tel} arayacak"
    assert numara.maskele(metin) == "müşteri … arayacak"
    assert numara.maskele(metin, son_dort=True) == "müşteri …0777 arayacak"


@pytest.mark.parametrize("metin", DOKUNULMAZ)
def test_olcu_tarih_kod_dokunulmaz(metin):
    assert numara.maskele(metin) == metin and numara.maskele(metin, son_dort=True) == metin


def test_bilinen_sinirlar():
    """BK-08 › Riskler: öneksiz sabit hat ("212 000 07 77") maskelenmez (öneksiz 3-3-2-2 yalnız cepte numara sayılır, yoksa "350 400 30 25"
    gibi ölçü listesi de maskelenirdi); birimsiz ve cep biçiminde yazılmış ölçü dizisi ("540 300 20 10") numara sayılır (KVKK önce)."""
    assert numara.maskele("212 000 07 77") == "212 000 07 77"
    assert numara.maskele("540 300 20 10") == "…"


def test_cumle_icinde_yalniz_numara_maskelenir():
    m = f"mutfak penceresi 120x120 olsun, numaram {CEP}, 3 adet; sevk 14.10.2026"
    assert numara.maskele(m) == "mutfak penceresi 120x120 olsun, numaram …, 3 adet; sevk 14.10.2026"
    assert numara.maskele(f"0212 000 07 77 / {CEP}") == "… / …"           # arkasından bölü gelse de numara maskelenir


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


def test_d01_gerekcesine_bayinin_cumlesi_yazilmaz(tmp_path):
    """Gerekçe günlüğe gider (`vps/agent.py`); bayinin cümlesi yazılmaz (beyin.md), yalnız bekleyen talebin kodu (test_b1_b2 aynen)."""
    k = Konusma("900000000101", kok=tmp_path)
    k.d["eski_taslak_soru"] = K.ESKI_TASLAK_EN_COK
    k.d["bekleyen_talep"] = {"katalog_kodu": "P6001"}
    k.d["bekleyen_metin"] = "P6001 aynalı olsun, müşteri Deneme Kişi, tel +90 (212) 000-07-77"
    karar = K._eski_taslak_sor(k)
    assert karar.eylem == "yonlendir" and karar.gerekce == "eski taslak sorusu cevapsız (D-01); bekleyen mesaj: P6001 talebi"
    assert not k.d.get("bekleyen_metin") and not k.d.get("bekleyen_talep")


def test_plan_mesaji_gorsel_gitmezse_yalniz_pdf_der():
    """BK-08 madde 4 (kod incelemesi): mesaj katmanı kapalıysa ya da bayi görseli üretilemediyse "plan görseli" sözü verilmez."""
    m = "Ç8801K. Ön onay planınız hazır; plan görseli ve PDF ektedir."
    assert W.ek_sozu(m, gorsel_var=True) == m
    assert W.ek_sozu(m, gorsel_var=False) == "Ç8801K. Ön onay planınız hazır; PDF ektedir."
    p = "P6001. Ön onay planını hazırlıyorum; birkaç dakika içinde PDF olarak göndereceğim."
    assert W.ek_sozu(p, gorsel_var=False) == p                         # prefabrik metni dokunulmaz
