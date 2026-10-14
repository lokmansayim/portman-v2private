"""İE-07 P4/P5 · worker ve kalici: Patron bildirimi metin + Meta şablon satırı (yönlendirme, çıkarım hatası, beklenmeyen hata, dosya
penceresi); bayinin 'Dosyaları gönder' hızlı yanıtı LLM'siz sabit cevap; Ç1031 katalog notu yalnız Patron'a (D-07, Lokman karar 1).
Gerçek Postgres; gönderim test_gonderici.py'de. P6001 akışının satırları değişmez (test_kalici temel akış)."""
from __future__ import annotations

import pytest

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import kalici
import sablonlar as S
import worker as W
from depo import kimlik_izi

NUMARA_P = "900000000909"


def isle_hepsi(depo, ayar=AYAR):
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def satirlar(depo, mesaj_id):
    return sorgu(depo, "SELECT sira, alici, tur, kind, govde, kaynak, satir FROM giden WHERE mesaj_id = %s ORDER BY sira", mesaj_id)


def test_yonlendirme_metin_ve_sablon_satiri_talep_kimligi_bos_gitmez(depo):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    g = mesaj("P8501 olsun", talep(ozet="P8501", katalog_kodu="P8501"), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "yonlendir"
    s = satirlar(depo, g["id"])
    assert [(x["alici"], x["kind"], x["kaynak"]) for x in s] == [(NUMARA_A, "text", "ajan"), ("PATRON", "text", "ajan"), ("PATRON", "template", "ajan")]
    sab = s[2]["satir"]
    assert sab["sablon_anahtari"] == "sablon_patron_bildirim" and sab["pencere_kapaliysa"] is True and "ad" not in sab["sablon"]
    assert sab["sablon"]["govde"] == ["TSTA", "T-" + kimlik_izi(g["id"])[:8]]                # İş Emri yok → T-<iz>, asla boş
    assert sab["sablon"]["dugmeler"] == [{"sub_type": "url", "index": 0, "text": f"konusma/{NUMARA_A}"}]
    assert s[2]["govde"] == S.sablon_metni(S.PATRON_BILDIRIM["metin"], sab["sablon"]["govde"])
    assert s[1]["govde"].startswith("Portman yönlendirme:") and "Katalog notu" not in s[1]["govde"]


def test_c1031_notu_yalniz_patrona(depo):
    """D-07 / Lokman karar 1: Ç1031 kaydının notu Patron'a giden yönlendirme metninde; bayiye ek bir şey söylenmez."""
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    g = mesaj("Ç1031 istiyorum", talep(ozet="Ç1031", katalog_kodu="Ç1031"), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "yonlendir"
    s = satirlar(depo, g["id"])
    assert "Ç1031 (103 m², 2+1, çelik tek kat)" in s[0]["govde"] and "Ç1151" not in s[0]["govde"] and "Katalog notu" not in s[0]["govde"]
    assert "Katalog notu (Ç1031): Katalog paftası Ç1151'in planını" in s[1]["govde"]
    assert s[2]["kind"] == "template"


def test_cikarim_hatasi_sablon_satiri(depo, monkeypatch):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")

    def patlak(*a, **k):
        raise RuntimeError("LLM yok")
    monkeypatch.setattr(W, "cikar", patlak)
    g = mesaj("bir şey", None, bayi=depo.gelen_bayisi(NUMARA_A)); g.pop("test_cikarim", None)
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "hata" and r["gerekce"] == "çıkarım hatası"
    s = satirlar(depo, g["id"])
    assert [(x["alici"], x["kind"]) for x in s] == [(NUMARA_A, "text"), ("PATRON", "text"), ("PATRON", "template")]
    assert s[2]["satir"]["sablon"]["govde"][1].startswith("T-")


def test_beklenmeyen_hata_sablon_satiri_ve_son_is_emri(depo, monkeypatch, hizli_motor, wa):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    g1 = mesaj("P6001 aynalı", talep(ozet="P6001 aynalı", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}]), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(g1); [r1] = isle_hepsi(depo); assert r1["eylem"] == "is_emri"
    no = tek(depo, "SELECT is_emri_no FROM revizyonlar")["is_emri_no"]
    assert [x["kind"] for x in satirlar(depo, g1["id"])] == ["text", "document"]        # P6001 akışının satırları değişmedi

    def coken(*a, **k):
        raise RuntimeError("çöktü")
    monkeypatch.setattr(W, "isle", coken)
    g2 = mesaj("onaylıyorum", talep("onay", "onay"), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(g2); [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "hata"
    s = satirlar(depo, g2["id"])
    assert [(x["alici"], x["kind"]) for x in s] == [(NUMARA_A, "text"), ("PATRON", "text"), ("PATRON", "template")]
    assert s[2]["satir"]["sablon"]["govde"] == ["TSTA", no]                                  # taslağın son İş Emri no'su


def test_dosya_dugmesi_llmsiz_cevap_ve_patrona_cift_bildirim(depo, monkeypatch):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")

    def yasak(*a, **k):
        raise AssertionError("LLM çağrılmamalı")
    monkeypatch.setattr(W, "cikar", yasak)
    g = mesaj("Dosyaları gönder", None, bayi=depo.gelen_bayisi(NUMARA_A), tur="button"); g.pop("test_cikarim", None)
    g["reply_id"] = "dosya:PM-TSTA-20261011-1"; g["reply_kind"] = "button"
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "cevapla" and r["gerekce"] == "şablon cevabı: dosya penceresi açıldı"
    s = satirlar(depo, g["id"])
    assert [(x["alici"], x["kind"]) for x in s] == [(NUMARA_A, "text"), ("PATRON", "text"), ("PATRON", "template")]
    assert s[0]["govde"] == "Teşekkürler, dosyalarınızı bu sohbetten iletiyoruz."              # Lokman onayı (ekleme B), aynen
    assert "dosya penceresini açtı (PM-TSTA-20261011-1)" in s[1]["govde"]
    assert s[2]["satir"]["sablon"]["govde"] == ["TSTA", "PM-TSTA-20261011-1"]
    d_sonra, _ = depo.konusma_oku(NUMARA_A)                                                    # konuşma durumu değişmedi (boş kaldı)
    assert d_sonra["asama"] == "bos" and d_sonra["son_is_emri"] is None and d_sonra["gecmis"] == [] and d_sonra["taslak"] == {}


def test_patron_gonderenken_patron_satiri_yok(depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    g = mesaj("P8501 olsun", talep(ozet="P8501", katalog_kodu="P8501"), numara=NUMARA_P, bayi=depo.gelen_bayisi(NUMARA_P))
    g["role"] = "patron"
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "yonlendir"
    assert [(x["alici"], x["kind"]) for x in satirlar(depo, g["id"])] == [(NUMARA_P, "text")]


# BK-08 madde 9: bayinin mesajındaki numara (boşluklu / tireli / +90'lı) Patron bildirimindeki alıntıda maskeli; bayinin satırı aynı.
# Numara uydurma (sabit hat biçiminde, abonesi 000 07 77).
TEL_BOSLUKLU = "0212 000 07 77"


def test_yonlendirmede_patron_alintisi_numarasiz(depo):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    g = mesaj(f"P8501 olsun, müşteri {TEL_BOSLUKLU} arayacak", talep(ozet="P8501", katalog_kodu="P8501"), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "yonlendir"
    s = satirlar(depo, g["id"])
    assert s[1]["alici"] == "PATRON" and "P8501 olsun, müşteri …0777 arayacak" in s[1]["govde"] and "000 07 77" not in s[1]["govde"]


def test_cikarim_hatasinda_patron_alintisi_numarasiz(depo, monkeypatch):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")

    def patlak(*a, **k):
        raise RuntimeError("LLM yok")
    monkeypatch.setattr(W, "cikar", patlak)
    g = mesaj("numaram +90 (212) 000-07-77", None, bayi=depo.gelen_bayisi(NUMARA_A)); g.pop("test_cikarim", None)
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "hata"
    s = satirlar(depo, g["id"])
    assert s[1]["alici"] == "PATRON" and "numaram …0777" in s[1]["govde"] and "07-77" not in s[1]["govde"]
