"""İE-06 · bayi kimlik kartı (göç 004), kayıtsız gönderen, webhook olay tekilleştirme, durum bildirimi eşlemesi, gelen medya kaydı ve
panel sorguları (kanal/depo.py). Gerçek Postgres; ağ, LLM, WhatsApp yok."""
from __future__ import annotations

import time

import pytest

from conftest import NUMARA_A, NUMARA_B, mesaj, sorgu, talep, tek

import depo as D

NUMARA_P = "900000000909"          # gerçek olmayan deneme numarası (Patron)
NUMARA_X = "900000000777"          # kayıtsız


def test_bayi_yaz_oku_turetme_ve_dogrulama(depo):
    p = depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron", hitap="Bey", firma="PortatifEv", bolge="Marmara")
    assert p["kod"] == "PATRON" and p["rol"] == "patron" and p["aktif"] is True and p["kaynak"] == "panel"
    b = depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", rol="bayi", hitap="Hanım", firma="A İnşaat", bolge="Ege")
    assert b["kod"] == "B" + NUMARA_A[-4:]                                    # kod boşsa feature.php kuralıyla türetilir
    assert depo.bayi_oku(NUMARA_A)["firma"] == "A İnşaat" and depo.bayi_oku("yok") is None
    b2 = depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="ABC", rol="bayi", aktif=False)
    assert b2["kod"] == "ABC" and b2["aktif"] is False and b2["hitap"] == ""   # güncelleme bütün alanları yazar
    assert depo.gelen_bayisi(NUMARA_A) is None                                # pasif bayi kayıtsız sayılır
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="ABC", rol="bayi", aktif=True)
    assert depo.gelen_bayisi(NUMARA_A) == {"kod": "ABC", "ad": "Deneme Bayi A", "firma": "", "rol": "bayi"}
    assert depo.gelen_bayisi(NUMARA_P)["kod"] == "PATRON" and depo.patron_numarasi() == NUMARA_P
    m = depo.bayi_yaz(NUMARA_B, ad="Mühendis", rol="muhendis")
    assert m["rol"] == "muhendis"
    liste = depo.bayi_listesi()
    assert [x["numara"] for x in liste][0] == NUMARA_P and len(liste) == 3    # patron önce
    with pytest.raises(ValueError, match="numara"):
        depo.bayi_yaz("+90 555", ad="x")
    with pytest.raises(ValueError, match="rol"):
        depo.bayi_yaz(NUMARA_A, ad="x", rol="yonetici")
    assert depo.patron_numarasi() == NUMARA_P
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron", aktif=False)
    assert depo.patron_numarasi() is None


def test_mesaj_kaydet_kimlik_kartina_dokunmaz(depo):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA", hitap="Bey", firma="A İnşaat", bolge="Ege")
    assert depo.mesaj_kaydet(mesaj("P6001 aynalı", talep(ozet="P6001"), bayi=depo.gelen_bayisi(NUMARA_A)))
    b = depo.bayi_oku(NUMARA_A)
    assert (b["hitap"], b["firma"], b["bolge"], b["kod"]) == ("Bey", "A İnşaat", "Ege", "TSTA")
    assert tek(depo, "SELECT kaynak, sahiplenildi FROM mesajlar") == {"kaynak": "vps", "sahiplenildi": True}


def test_kayitsiz_mesaj_is_acmaz_sabit_cevap_24_saatte_bir(depo):
    g = mesaj("merhaba fiyat?", talep(), numara=NUMARA_X, bayi=None)
    g["role"] = "bayi"; g["neden"] = "kayıtsız gönderen"
    r = depo.kayitsiz_mesaj_kaydet(g, "Portman yalnız kayıtlı bayilere açıktır; lütfen ofisi arayın.")
    assert r == {"yeni": True, "cevap": True}
    assert depo.kayitsiz_mesaj_kaydet(g, "x") == {"yeni": False, "cevap": False}               # tekrar teslim
    j = tek(depo, "SELECT durum, sonuc FROM isler")
    assert j["durum"] == "bitti" and j["sonuc"]["eylem"] == "kayitsiz"
    assert tek(depo, "SELECT sahiplenildi, bayi_kod FROM mesajlar") == {"sahiplenildi": False, "bayi_kod": None}
    c = tek(depo, "SELECT alici, kind, govde, durum FROM giden")
    assert c["alici"] == NUMARA_X and c["durum"] == "bekliyor" and "kayıtlı" in c["govde"]
    g2 = mesaj("alo", talep(), numara=NUMARA_X, bayi=None)
    assert depo.kayitsiz_mesaj_kaydet(g2, "x") == {"yeni": True, "cevap": False}             # 24 saat dolmadı: ikinci cevap yok
    assert tek(depo, "SELECT count(*) AS n FROM giden")["n"] == 1
    with depo.baglan() as c2, c2.transaction():
        c2.execute("UPDATE kayitsiz_cevaplar SET son = now() - interval '25 hours'")
    g3 = mesaj("alo 2", talep(), numara=NUMARA_X, bayi=None)
    assert depo.kayitsiz_mesaj_kaydet(g3, "x")["cevap"] is True
    assert tek(depo, "SELECT sayi FROM kayitsiz_cevaplar")["sayi"] == 2
    g4 = mesaj("sessiz", talep(), numara=NUMARA_B, bayi=None)
    assert depo.kayitsiz_mesaj_kaydet(g4, None) == {"yeni": True, "cevap": False}            # cevap metni yoksa cevap yok
    assert depo.acik_is_sayisi() == 0                                                            # hiçbiri ajana iş olmadı


def test_olay_tekillestirme_ve_durum_satiri(depo, wa):
    assert depo.olay_kaydet("wamid.A1", "mesaj") and not depo.olay_kaydet("wamid.A1", "mesaj")
    assert depo.olay_kaydet("x" * 500, "durum")                                                # anahtar kırpılır, hata yok
    depo.bayi_yaz(NUMARA_A, ad="A", kod="TSTA")
    g = mesaj("merhaba", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(g)
    import kalici
    [r] = [kalici.bir_is(depo, {"llm": {"backend": "manuel"}, "patron_teknik_not": False}, "t")]
    assert r["eylem"] in ("cevapla", "sor", "yonlendir")
    satir = tek(depo, "SELECT id FROM giden ORDER BY sira LIMIT 1")["id"]
    assert depo.giden_durum_satiri("wamid.OUT0001", satir) is None                              # henüz denenmedi: opaque eşlemez
    kalici.gonder(depo, wa)                                                                     # sahte WhatsApp wamid.OUT0001 verir
    assert depo.giden_durum_satiri("wamid.OUT0001", None)["id"] == satir
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET dis_id = NULL WHERE id = %s", (satir,))                     # wamid yazılamamış satır
    assert depo.giden_durum_satiri("wamid.OUT0001", satir)["id"] == satir                       # opaque ile bulunur (deneme ≥ 1)
    depo.alici_cozuldu_kaydet(satir, NUMARA_A); depo.medya_id_kaydet(satir, "123")
    assert tek(depo, "SELECT alici_cozuldu, medya_id FROM giden WHERE id = %s", satir) == {"alici_cozuldu": NUMARA_A, "medya_id": "123"}


def test_gonderim_geri_birak_ve_dry_run(depo):
    depo.bayi_yaz(NUMARA_A, ad="A", kod="TSTA")
    g = mesaj("x", talep(), bayi=depo.gelen_bayisi(NUMARA_A)); depo.mesaj_kaydet(g)
    import kalici
    kalici.bir_is(depo, {"llm": {"backend": "manuel"}, "patron_teknik_not": False}, "t")
    r = depo.gonderime_al()
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", r["id"])["durum"] == "gonderiliyor"
    depo.gonderim_geri_birak(r["id"], "medya yüklenemedi; bir kez daha denenecek")
    assert tek(depo, "SELECT durum, hata, deneme FROM giden WHERE id = %s", r["id"])["durum"] == "bekliyor"
    n = depo.dry_run_tut()
    assert n >= 1 and tek(depo, "SELECT durum, hata FROM giden WHERE id = %s", r["id"])["hata"].startswith("dry_run")
    assert depo.gonderime_al() is None


def test_gelen_medya_kaydi_ve_panel_sorgulari(depo, tmp_path):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA", hitap="Bey")
    g = mesaj("kroki ekte", talep(), bayi=depo.gelen_bayisi(NUMARA_A), tur="image", ts=time.time() - 10)
    g["media_id"] = "555"; depo.mesaj_kaydet(g)
    depo.gelen_dosya_ekle(g["id"], "555", None, "image/jpeg"); depo.gelen_dosya_ekle(g["id"], "555", None, "image/jpeg")   # ikinci kez: tek kayıt
    [d] = depo.bekleyen_gelen_dosyalar()
    assert d["medya_id"] == "555" and d["gonderen"] == NUMARA_A and d["deneme"] == 0
    depo.gelen_dosya_hatasi(d["id"], "bağlantı")
    assert depo.bekleyen_gelen_dosyalar()[0]["deneme"] == 1
    yol = tmp_path / "kroki.jpg"; yol.write_bytes(b"\xff\xd8\xff")
    depo.gelen_dosya_indirildi(d["id"], str(yol), "image/jpeg", 3, "abc")
    assert depo.bekleyen_gelen_dosyalar() == [] and depo.gelen_dosya(d["id"])["yol"] == str(yol)
    [f] = depo.gelen_dosyalari(NUMARA_A)
    assert f["indirildi"] is True and f["mime"] == "image/jpeg"
    # kayıtsız bir numaradan mesaj + panel listesi
    gx = mesaj("fiyat?", talep(), numara=NUMARA_X, bayi=None); depo.kayitsiz_mesaj_kaydet(gx, "yönlendirme")
    liste = depo.konusma_listesi()
    assert [x["gonderen"] for x in liste] == [NUMARA_X, NUMARA_A]                              # yeniden eskiye
    assert liste[1]["ad"] == "Deneme Bayi A" and liste[1]["n"] == 1 and liste[0]["ad"] is None and liste[0]["sahiplenildi"] is False
    k = depo.konusma_mesajlari(NUMARA_X)
    assert [x["yon"] for x in k] == ["gelen", "giden"] and k[1]["durum"] == "bekliyor"
    assert depo.konusma_mesajlari(NUMARA_A)[0]["kind"] == "image"
    s = depo.sayimlar()
    assert s["aktif_bayi"] == 1 and s["bekleyen_giden"] == 1 and s["gelen_24s"] == 2 and s["bekleyen_medya"] == 0
    depo.panel_giris_kaydet("basarisiz", "ip1"); depo.panel_giris_kaydet("basarisiz", "ip2"); depo.panel_giris_kaydet("basarili", "ip1")
    assert depo.panel_basarisiz_sayisi(15) == 2 and depo.panel_basarisiz_sayisi(15, "ip1") == 1


def test_son_gelen_zamani(depo):
    assert depo.son_gelen_zamani(NUMARA_A) is None
    t = time.time() - 3600
    depo.mesaj_kaydet(mesaj("a", talep(), ts=t)); depo.mesaj_kaydet(mesaj("b", talep(), ts=t - 100))
    assert abs(depo.son_gelen_zamani(NUMARA_A) - int(t)) < 2
