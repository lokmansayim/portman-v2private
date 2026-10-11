"""Bağımsız incelemenin (28.09) bulguları ve testlerin yakalamadığı mutasyonlar için eklenen testler.

Her test başında hangi bulguyu ya da mutasyonu kapattığı yazılı. Ortam: gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from conftest import (AYAR, BAYI_A, KANAL_VERI, KOK, NUMARA_A, NUMARA_B, geri_al, mesaj, sorgu, talep, tek)
from test_kalici import (T_ONAY, T_P6001, T_PENCERE_DEGISTIR, T_B1_BELIRSIZ, BELIRSIZ, _revizyon_iste, isle_hepsi, plan_iste)

import kalici
import worker as W
from depo import Cakisma, KiraKaybi
from psycopg.types.json import Jsonb


def _tetik(depo, tablo: str, olay: str, kosul: str) -> None:
    """Test için veritabanı düzeyinde çöküş: koşul tutunca işlem hata verir (işin ortasında süreç düşmüş gibi)."""
    with depo.baglan() as c:
        c.execute(f"CREATE OR REPLACE FUNCTION test_patlat() RETURNS trigger AS $$ BEGIN IF {kosul} THEN "
                  f"RAISE EXCEPTION 'test: yarıda kesildi'; END IF; RETURN NEW; END $$ LANGUAGE plpgsql")
        c.execute(f"CREATE TRIGGER test_patlat BEFORE {olay} ON {tablo} FOR EACH ROW EXECUTE FUNCTION test_patlat()")


def _tetigi_kaldir(depo, tablo: str) -> None:
    with depo.baglan() as c:
        c.execute(f"DROP TRIGGER test_patlat ON {tablo}")


# ───────────────────────── kural 4 ve 1: tek işlem (mutasyon M10, M25) ─────────────────────────
def test_isin_bitisi_yazilamazsa_hicbir_sonuc_kalmaz(depo, wa, hizli_motor):
    """Giden satırlar, konuşma, revizyon ve soru kaydı işin bitişiyle aynı işlemde: bitiş yazılamazsa hiçbiri kalmaz;
    iş yeniden alınınca her şey bir kez yazılır."""
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    _tetik(depo, "isler", "UPDATE", "NEW.durum = 'bitti'")
    with pytest.raises(Exception, match="yarıda kesildi"):
        kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, "A")
    for t in ("giden", "revizyonlar", "projeler", "konusmalar", "sorular"):
        assert tek(depo, f"SELECT count(*) n FROM {t}")["n"] == 0, t
    _tetigi_kaldir(depo, "isler")
    time.sleep(1.2)
    r = kalici.bir_is(depo, AYAR, "B")
    assert r["durum"] == "bitti"
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 2 and tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1
    assert kalici.gonder(depo, wa)["kabul_edildi"] == 2 and len(wa.gonderilen) == 2


def test_mesaj_ve_is_birlikte_yazilir(depo):
    """İş yazılamazsa mesaj da yazılmaz; webhook'un tekrarı mesajı yeniden kaydedebilir (tek başına mesaj kalmaz)."""
    g = mesaj("P6001 aynalı", T_P6001)
    _tetik(depo, "isler", "INSERT", "true")
    with pytest.raises(Exception, match="yarıda kesildi"):
        depo.mesaj_kaydet(g)
    assert tek(depo, "SELECT count(*) n FROM mesajlar")["n"] == 0
    _tetigi_kaldir(depo, "isler")
    assert depo.mesaj_kaydet(g) is True and tek(depo, "SELECT count(*) n FROM isler")["n"] == 1


# ───────────────────────── T4 ek (mutasyon: ilk yazma, yalnız sahip denetimi, geri bırakma) ─────────────────────────
def test_ilk_yazmada_da_sessiz_ezme_yok(depo, hizli_motor):
    """Konuşma yokken okunan (sürüm 0) sonuç, arada konuşma oluştuysa yazılmaz."""
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    alinan = depo.is_al("A")
    with depo.baglan() as c:
        c.execute("INSERT INTO konusmalar (gonderen, durum) VALUES (%s, %s)", (NUMARA_A, Jsonb({"asama": "baskasi_yazdi"})))
    cikti = {"satirlar": [W.giden_metin(g, "deneme", 1)], "sonuc": {"eylem": "cevapla", "gerekce": "deneme"}}
    with pytest.raises(Cakisma):
        depo.isi_bitir(alinan["is"], "A", g, 0, None, {"asama": "ezmemeli"}, cikti)
    assert depo.konusma_oku(NUMARA_A)[0]["asama"] == "baskasi_yazdi"


def test_kirasi_devredilen_is_yeni_sahip_bitirmeden_de_eski_sahibe_yazdirmaz(depo, hizli_motor):
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    a = depo.is_al("A", kira_sn=1)
    time.sleep(1.2)
    b = depo.is_al("B")                                        # B aldı, henüz bitirmedi (iş hâlâ 'isleniyor')
    assert b["is"]["id"] == a["is"]["id"]
    cikti = {"satirlar": [W.giden_metin(g, "A'nın geç sonucu", 1)], "sonuc": {"eylem": "cevapla", "gerekce": "geç"}}
    with pytest.raises(KiraKaybi):
        depo.isi_bitir(a["is"], "A", g, 0, None, {"asama": "A"}, cikti)
    assert not depo.cikarim_kaydet(a["is"]["id"], "A", {"hata": "A"})       # eski sahip çıkarım da yazamaz
    depo.is_geri_birak(a["is"]["id"], "A", "A'nın çakışması")               # eski sahip işi geri bırakamaz
    j = tek(depo, "SELECT * FROM isler")
    assert (j["durum"], j["sahip"], j["cikarim"]) == ("isleniyor", "B", None)


def test_cakisma_deneme_hakkini_tuketmez(depo, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001))
    for _ in range(5):
        a = depo.is_al("A")
        depo.is_geri_birak(a["is"]["id"], "A", "çakışma")
    assert tek(depo, "SELECT deneme FROM isler")["deneme"] == 0
    assert kalici.bir_is(depo, AYAR, "B")["durum"] == "bitti"


def test_kirasi_dolan_is_kayitsiz_cikarimla_alinir_ve_eski_sahip_atilir(depo, hizli_motor, monkeypatch):
    """Çıkarım sürerken kira dolar ve iş başkasına geçerse eski sahibin çıkarımı yazılmaz, sonucu atılır."""
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001))
    asil = W.cikar

    def yavas(*a, **k):
        time.sleep(1.3)
        return asil(*a, **k)
    monkeypatch.setattr(W, "cikar", yavas)
    import threading
    sonuc = {}
    t = threading.Thread(target=lambda: sonuc.setdefault("A", kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, "A")))
    t.start(); time.sleep(1.1)
    monkeypatch.setattr(W, "cikar", asil)
    sonuc["B"] = kalici.bir_is(depo, AYAR, "B")
    t.join()
    assert sonuc["B"]["durum"] == "bitti" and sonuc["A"]["durum"] == "atildi"
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 2


# ───────────────────────── bulgu 1: süresi dolan D-01 sorusundan sonra onay ─────────────────────────
def test_suresi_dolan_d01_sorusundan_sonra_onay_da_denetlenir(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    wa.mod = "belirsiz"
    with depo.baglan() as c:                                    # r01'in PDF'i belirsiz kalmış olsun
        c.execute("UPDATE giden SET durum = 'belirsiz', kabul_zamani = NULL WHERE kind = 'document'")
    wa.mod = "tamam"
    geri_al(depo, NUMARA_A, 3.5)
    depo.mesaj_kaydet(mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR)); isle_hepsi(depo)
    assert depo.konusma_oku(NUMARA_A)[0]["son_soru_alani"] == "yeni_mi_degisiklik"
    geri_al(depo, NUMARA_A, 25)                                 # soru 24 saati geçti
    o = mesaj("onaylıyorum", T_ONAY); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert r["gerekce"].startswith("onay bağlanmadı") and "teyitsiz" in r["gerekce"]
    assert tek(depo, "SELECT count(*) n FROM revizyonlar WHERE durum = 'onaylandi'")["n"] == 0


def test_d01_askidayken_onay_soruyu_yineler_onaylamaz(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    depo.mesaj_kaydet(mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR)); isle_hepsi(depo)
    time.sleep(1.1)
    depo.mesaj_kaydet(mesaj("tamam", T_ONAY)); [r] = isle_hepsi(depo)
    assert r["eylem"] == "sor"
    assert tek(depo, "SELECT deneme FROM sorular WHERE durum = 'acik'")["deneme"] == 2
    assert tek(depo, "SELECT count(*) n FROM revizyonlar WHERE durum = 'onaylandi'")["n"] == 0


# ───────────────────────── bulgu 3: soru kaydının sonucu ─────────────────────────
def test_iptal_edilen_eksik_bilgi_sorusu_dustu(depo, hizli_motor):
    depo.mesaj_kaydet(mesaj("6x8 m ev", talep("yeni_talep", "6x8 m ev", dis_olcu={"en_m": 6, "boy_m": 8}))); isle_hepsi(depo)
    iptal = mesaj("vazgeçtim", talep("red", "iptal")); depo.mesaj_kaydet(iptal); isle_hepsi(depo)
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["alan"], s["durum"], s["cevap_mesaj_id"]) == ("oda_programi", "dustu", iptal["id"])


def test_yeni_talep_ayni_alani_yeniden_sorarsa_yeni_soru_kaydi(depo, hizli_motor):
    ilk = mesaj("6x8 m ev", talep("yeni_talep", "6x8 m ev", dis_olcu={"en_m": 6, "boy_m": 8}))
    depo.mesaj_kaydet(ilk); isle_hepsi(depo)
    ikinci = mesaj("yeni talep: 7x9 m ev", talep("yeni_talep", "7x9 m ev", dis_olcu={"en_m": 7, "boy_m": 9}))
    depo.mesaj_kaydet(ikinci); isle_hepsi(depo)
    eski, yeni = sorgu(depo, "SELECT * FROM sorular ORDER BY id")
    assert (eski["kaynak_mesaj_id"], eski["durum"], eski["cevap_mesaj_id"]) == (ilk["id"], "dustu", ikinci["id"])
    assert (yeni["alan"], yeni["kaynak_mesaj_id"], yeni["durum"], yeni["deneme"]) == ("oda_programi", ikinci["id"], "acik", 1)


def test_d01_bekletilen_mesaj_baska_modelle_duserse_dustu(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    depo.mesaj_kaydet(mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR)); isle_hepsi(depo)
    baska = mesaj("P7401 istiyorum", talep("yeni_talep", "P7401", katalog_kodu="P7401"))
    depo.mesaj_kaydet(baska); isle_hepsi(depo)
    s = tek(depo, "SELECT * FROM sorular WHERE alan = 'yeni_mi_degisiklik'")
    assert (s["durum"], s["cevap_mesaj_id"]) == ("dustu", baska["id"])


def test_d01_bekletilen_mesaj_degisirse_eski_soru_kapanir_yenisi_acilir(depo, wa, hizli_motor):
    """Bekletilen mesaj, cevap denemesi olmayan uzun bir istekle düşer; o istek de eski taslakta model koduyla
    başladığı için yeniden sorulur: bu yeni bir sorudur (kaynağı ikinci mesaj)."""
    plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    ilk = mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR); depo.mesaj_kaydet(ilk); isle_hepsi(depo)
    ikinci = mesaj("P6001 çatı beşik olsun ve veranda da eklensin lütfen", talep("revizyon", "P6001 çatı beşik, veranda", katalog_kodu="P6001",
                                                                              ozel_istekler=["çatı beşik", "veranda"]))
    depo.mesaj_kaydet(ikinci); isle_hepsi(depo)
    sorular = sorgu(depo, "SELECT * FROM sorular ORDER BY id")
    d, _ = depo.konusma_oku(NUMARA_A)
    if d.get("son_soru_alani") == "yeni_mi_degisiklik":       # ikinci mesaj yeniden soru doğurduysa: iki ayrı kayıt
        assert [(s["kaynak_mesaj_id"], s["durum"]) for s in sorular] == [(ilk["id"], "dustu"), (ikinci["id"], "acik")]
    else:                                                      # doğurmadıysa ilk soru düşmüş olmalı
        assert [(s["kaynak_mesaj_id"], s["durum"]) for s in sorular] == [(ilk["id"], "dustu")]


def test_pencere_sorusu_ilgisiz_mesajla_dusunce_dustu(depo, hizli_motor):
    depo.mesaj_kaydet(mesaj(BELIRSIZ, T_B1_BELIRSIZ)); isle_hepsi(depo)
    assert tek(depo, "SELECT alan FROM sorular")["alan"] == "pencere_islem"
    iptal = mesaj("vazgeçtim", talep("red", "iptal")); depo.mesaj_kaydet(iptal); isle_hepsi(depo)
    assert tek(depo, "SELECT durum FROM sorular")["durum"] == "dustu"


# ───────────────────────── bulgu 4: bayi kodu benzersiz değil ─────────────────────────
def test_ayni_bayi_kodlu_iki_numara_birbirinin_kaydini_goremez(depo, wa, hizli_motor):
    """Bayi kodu benzersiz değil (feature.php: panelde kod yoksa 'B' + son 4 hane). Yetki ayrımı numarayla yapılır."""
    ortak = {"kod": "B1234", "ad": "Birinci", "rol": "bayi"}
    plan_iste(depo, wa, bayi=ortak)
    time.sleep(1.1)                                            # İş Emri numarası saniyeye bağlı (numara çakışması ayrı testte)
    plan_iste(depo, wa, numara=NUMARA_B, bayi={**ortak, "ad": "İkinci"})
    ra = tek(depo, "SELECT * FROM revizyonlar WHERE gonderen = %s", NUMARA_A)
    assert depo.revizyon(NUMARA_B, ra["is_emri_no"]) is None
    assert [p["id"] for p in depo.projeler(NUMARA_B)] != [p["id"] for p in depo.projeler(NUMARA_A)]
    assert {(b["numara"], b["ad"]) for b in sorgu(depo, "SELECT numara, ad FROM bayiler")} == {(NUMARA_A, "Birinci"), (NUMARA_B, "İkinci")}


def test_ayni_is_emri_numarasi_uretilirse_oteki_bayinin_dosyasi_ezilmez(depo, wa, hizli_motor, monkeypatch):
    """v1.1.1'de İş Emri numarası bayi kodu + saniyeden üretilir. Aynı kodlu iki bayi aynı saniyede plan üretirse numara
    aynı çıkar. İkinci iş ilkinin PDF'inin üzerine yazmaz: Motor önce hazırlık klasörüne yazar, projects/<no>/rNN yalnız
    yoksa açılır; iş çakışma sayılıp sıraya döner ve bir sonraki saniyede yeni numarayla biter."""
    import hashlib, types
    import beyin.karar as KR
    ortak = {"kod": "B1234", "ad": "Birinci", "rol": "bayi"}
    sabit = types.SimpleNamespace(time=lambda: 1790580000.0, strftime=time.strftime)
    monkeypatch.setattr(KR, "time", sabit)
    plan_iste(depo, wa, bayi=ortak)
    ra = tek(depo, "SELECT * FROM revizyonlar")
    pdf_a = Path(tek(depo, "SELECT dosya FROM giden WHERE kind = 'document'")["dosya"])
    once = hashlib.sha256(pdf_a.read_bytes()).hexdigest()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", talep(ozet="P6001 B", katalog_kodu="P6001"), numara=NUMARA_B, bayi={**ortak, "ad": "İkinci"}))
    r = kalici.bir_is(depo, AYAR, "B")
    assert r["durum"] == "cakisma" and "üzerine yazılmaz" in r["neden"]
    assert hashlib.sha256(pdf_a.read_bytes()).hexdigest() == once == ra["pdf_sha256"]
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1
    monkeypatch.setattr(KR, "time", time)                     # zaman ilerledi
    r = kalici.bir_is(depo, AYAR, "B")
    assert r["durum"] == "bitti" and r["eylem"] == "is_emri"
    no = [x["is_emri_no"] for x in sorgu(depo, "SELECT is_emri_no FROM revizyonlar ORDER BY id")]
    assert len(set(no)) == 2
    assert kalici.gonder(depo, wa)["kabul_edildi"] == 2 and hashlib.sha256(pdf_a.read_bytes()).hexdigest() == once


def test_dosyasi_degismis_pdf_gonderilmez(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    pdf = Path(tek(depo, "SELECT dosya FROM giden WHERE kind = 'document'")["dosya"])
    pdf.write_bytes(pdf.read_bytes() + b"%degisti")
    say = kalici.gonder(depo, wa)
    assert say["gonderilmedi"] == 1 and [x["kind"] for x in wa.gonderilen] == ["text"]


def test_baska_bayinin_mesajini_alintilamak_onayi_etkilemez(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    a_pdf = tek(depo, "SELECT dis_id FROM giden WHERE kind = 'document'")["dis_id"]
    plan_iste(depo, wa, numara=NUMARA_B, bayi={"kod": "TSTB", "ad": "B", "rol": "bayi"})
    time.sleep(1.1)
    depo.mesaj_kaydet(mesaj("onaylıyorum", T_ONAY, numara=NUMARA_B, bayi={"kod": "TSTB", "ad": "B", "rol": "bayi"}, context_id=a_pdf))
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı"
    assert tek(depo, "SELECT gonderen FROM revizyonlar WHERE durum = 'onaylandi'")["gonderen"] == NUMARA_B


# ───────────────────────── gönderim durumları (mutasyon: süre, durum koruması) ─────────────────────────
def test_yeni_baslayan_gonderim_belirsiz_sayilmaz(depo, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    r = depo.gonderime_al()
    assert depo.yarim_gonderimleri_belirsiz_say() == 0
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", r["id"])["durum"] == "gonderiliyor"


def test_gec_gelen_sonuc_iletilmis_satiri_bozmaz_gec_teyit_kaybolmaz(depo, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    r1 = depo.gonderime_al(); depo.gonderim_sonucu(r1["id"], "kabul_edildi", dis_id="wamid.X1")
    depo.gonderim_sonucu(r1["id"], "belirsiz", hata="geç gelen zaman aşımı")
    assert tek(depo, "SELECT durum, dis_id FROM giden WHERE id = %s", r1["id"]) == {"durum": "kabul_edildi", "dis_id": "wamid.X1"}
    r2 = depo.gonderime_al()
    with depo.baglan() as c:
        c.execute("UPDATE giden SET gonderim_basladi = now() - interval '11 minutes' WHERE id = %s", (r2["id"],))
    assert depo.yarim_gonderimleri_belirsiz_say() == 1
    depo.gonderim_sonucu(r2["id"], "kabul_edildi", dis_id="wamid.X2")     # gönderici sonunda cevap aldı
    s = tek(depo, "SELECT durum, dis_id, hata FROM giden WHERE id = %s", r2["id"])
    assert (s["durum"], s["dis_id"]) == ("kabul_edildi", "wamid.X2") and "sonra" in s["hata"]
    assert depo.gonderime_al() is None                           # yeniden gönderilecek satır yok


# ───────────────────────── göç, hata yolu, geçiş ─────────────────────────
def test_goc_ikinci_kez_bir_sey_uygulamaz(depo):
    assert depo.goc_uygula() == []
    from depo import GOC_DIR
    beklenen = sorted(int(p.name[:3]) for p in GOC_DIR.glob("[0-9][0-9][0-9]_*.sql"))
    assert beklenen[:2] == [1, 2] and [r["surum"] for r in sorgu(depo, "SELECT surum FROM sema_surumu ORDER BY surum")] == beklenen


def test_beklenmeyen_hatada_yarim_durum_yazilmaz(depo, monkeypatch):
    asil = W.isle

    degisti = []

    def bozuk(gelen, settings, k=None, cikarim=None, **kw):
        k.d["asama"] = "yarim_kalmis"; k.d["taslak"] = {"bozuk": True}; degisti.append(1)
        raise RuntimeError("beklenmeyen")
    monkeypatch.setattr(W, "isle", bozuk)
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    r = kalici.bir_is(depo, AYAR, "A")
    assert r["durum"] == "basarisiz" and degisti == [1]          # durum gerçekten yarıda değişti, sonra hata
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "bos" and d["taslak"] == {}
    # İE-07: Patron'a metin + şablon satırı (pencere kapalıysa şablon gider)
    assert [(x["alici"], x["kind"]) for x in sorgu(depo, "SELECT alici, kind FROM giden ORDER BY sira")] == [(NUMARA_A, "text"), ("PATRON", "text"), ("PATRON", "template")]
    monkeypatch.setattr(W, "isle", asil)


def test_gecis_islenmekte_olan_mesaj_varken_yapilmaz(depo, tmp_path):
    import depo_aktar
    kanal = tmp_path / "kanal"; (kanal / "durum").mkdir(parents=True)
    g = mesaj("P6001", T_P6001, mid="wamid.YARIM1")
    (kanal / "state.json").write_text(json.dumps({"inbound": {"wamid.YARIM1": {**g, "state": "processing"}}}), encoding="utf-8")
    with pytest.raises(ValueError, match="işlenmekte"):
        depo_aktar.ice_aktar(depo, kanal)
    assert tek(depo, "SELECT count(*) n FROM mesajlar")["n"] == 0


# ───────────────────────── SIGTERM: iş bitirilip çıkılır ─────────────────────────
def test_sigterm_eldeki_isi_bitirip_cikar(depo):
    ayar = Path(tempfile.mkstemp(suffix=".json")[1]); ayar.write_text(json.dumps(AYAR), encoding="utf-8")
    betik = ("import sys, time; sys.path[:0] = [%r, %r, %r]\n"
             "import conftest\nfrom motor import dxf_out\n"
             "def yavas(*a, **k):\n    time.sleep(2.5)\n    return conftest.sahte_uret(*a, **k)\n"
             "dxf_out.uret = yavas\nimport kalici\nsys.exit(kalici.main(['isle', '--ayar', %r, '--bos-bekle', '0.2']))\n"
             % (str(KOK / "testler" / "kalici"), str(KOK), str(KOK / "kanal"), str(ayar)))
    env = {**os.environ, "PORTMAN_PG_DSN": depo.dsn, "PORTMAN_KANAL_DIR": str(W.KANAL)}
    p = subprocess.Popen([sys.executable, "-c", betik], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001))
    son = time.time() + 60
    while time.time() < son and tek(depo, "SELECT durum FROM isler")["durum"] != "isleniyor":
        time.sleep(0.1)
    time.sleep(0.5)
    p.send_signal(signal.SIGTERM)
    cikti, hata = p.communicate(timeout=60)
    assert p.returncode == 0, hata[-1500:]
    j = tek(depo, "SELECT * FROM isler")
    assert (j["durum"], j["deneme"]) == ("bitti", 1)
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 2
    satirlar = [json.loads(l) for l in cikti.splitlines() if l.startswith("{")]
    assert satirlar and all(set(x) <= {"durum", "is_id", "eylem", "giden", "proje_id", "revizyon_id"} for x in satirlar)
    assert "900000" not in cikti and "aynalı" not in cikti          # numara ve bayinin metni çıktıya yazılmadı


# ───────────────────────── ikinci inceleme turu (34c1888) ─────────────────────────
def _pdf_yerinde(depo) -> Path:
    r = tek(depo, "SELECT r.pdf_yolu, g.dosya FROM revizyonlar r JOIN giden g ON g.revizyon_id = r.id ORDER BY r.id DESC LIMIT 1")
    p = Path(r["pdf_yolu"])
    assert r["pdf_yolu"] == r["dosya"] and p.is_file() and ".hazirlik" not in p.parts and p.parent.parent.parent == W.KANAL / "projects"
    return p


def test_pdf_yolu_kayitta_ve_satirda_yerinde_hazirlik_temiz(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    _pdf_yerinde(depo)
    assert not any((W.KANAL / "projects" / ".hazirlik").glob("*"))


def test_cakisma_tasinan_dosyalari_siler_numara_bosalir(depo, hizli_motor, monkeypatch):
    """Dosya yerine taşındıktan sonra kayıt çakışırsa bu işin projects/<no>/rNN'i ve hazırlığı silinir."""
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    asil = kalici._yerlestir

    def tasi_sonra_baskasi_yazsin(cikti, hazirlik):
        yer = asil(cikti, hazirlik)
        with depo.baglan() as c:                               # taşımadan sonra başka bir yazma
            c.execute("INSERT INTO konusmalar (gonderen, durum) VALUES (%s, %s)", (NUMARA_A, Jsonb({"asama": "baskasi"})))
        tasi_sonra_baskasi_yazsin.hedef = yer[0][1]          # İE-04: _yerlestir [(kaynak, hedef), …] döner
        return yer
    monkeypatch.setattr(kalici, "_yerlestir", tasi_sonra_baskasi_yazsin)
    r = kalici.bir_is(depo, AYAR, "A")
    assert r["durum"] == "cakisma"
    assert not tasi_sonra_baskasi_yazsin.hedef.exists()
    assert not any((W.KANAL / "projects" / ".hazirlik").glob("*"))
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 0


def test_commit_sonrasi_baglanti_hatasinda_dosya_yerinde_kalir(depo, hizli_motor, monkeypatch):
    """Kayıt yazıldı ama istemci hata aldı (ör. COMMIT sırasında bağlantı koptu): yazılmış revizyonun PDF'i silinmez."""
    import psycopg
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    asil = depo.isi_bitir

    def yazip_hata_ver(*a, **k):
        asil(*a, **k)
        raise psycopg.OperationalError("bağlantı koptu")
    monkeypatch.setattr(depo, "isi_bitir", yazip_hata_ver)
    with pytest.raises(psycopg.OperationalError):
        kalici.bir_is(depo, AYAR, "A")
    assert tek(depo, "SELECT durum FROM isler")["durum"] == "bitti"
    _pdf_yerinde(depo)


def test_hicbir_sey_sorulmadiysa_soru_kaydi_acilmaz(depo, hizli_motor):
    """Kaydı olmayan eski bir soru askıdayken (ör. tablo öncesinden) selam gelir: bu mesaj o sorunun kaynağı sayılmaz."""
    with depo.baglan() as c:
        from beyin.konusma import Konusma
        d = Konusma._bos(); d.update(asama="topluyor", son_soru_alani="oda_programi", taslak={"dis_olcu": {"en_m": 6, "boy_m": 8}})
        c.execute("INSERT INTO konusmalar (gonderen, durum) VALUES (%s, %s)", (NUMARA_A, Jsonb(d)))
    depo.mesaj_kaydet(mesaj("merhaba", talep("selam", "selam"))); [r] = isle_hepsi(depo)
    assert r["eylem"] != "sor"
    assert tek(depo, "SELECT count(*) n FROM sorular")["n"] == 0


def test_soru_kaydi_kural_katmaninin_askidaki_sorusunu_izler(depo, wa, hizli_motor):
    """"Neyi değiştirelim?" (plan reddedildi) kural katmanında askıdaki soru olarak tutulmuyor (son_soru_alani boş);
    soru kaydı da açılmaz. Soru kaydı yalnız konuşmadaki askıdaki soruyu izler, kendi sorusunu uydurmaz."""
    plan_iste(depo, wa)
    depo.mesaj_kaydet(mesaj("beğenmedim", talep("red", "beğenmedim"))); [r] = isle_hepsi(depo)
    assert r["eylem"] == "sor" and depo.konusma_oku(NUMARA_A)[0]["son_soru_alani"] is None
    assert tek(depo, "SELECT count(*) n FROM sorular")["n"] == 0


def test_kirasi_devredilen_eski_sahip_yeni_sahibin_hazirlik_dosyalarini_silmez(depo, monkeypatch):
    """Üçüncü tur (N25): her denemenin hazırlık klasörü ayrı. Eski sahip KiraKaybi'nden sonra kendi klasörünü temizlerken
    aynı işi yürüten yeni sahibin henüz taşınmamış dosyalarını silmemeli."""
    import threading
    from motor import dxf_out
    from conftest import sahte_uret

    def yavas(ie, hedef, *a, **k):
        m = sahte_uret(ie, hedef)                  # dosyalar önce yazılır, sonra Motor "sürer"
        time.sleep(2.0)
        return m
    monkeypatch.setattr(dxf_out, "uret", yavas)
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001))
    sonuc = {}
    a = threading.Thread(target=lambda: sonuc.setdefault("A", kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, "A")))
    a.start(); time.sleep(1.3)                     # A'nın kirası doldu, A hâlâ Motor'da
    b = threading.Thread(target=lambda: sonuc.setdefault("B", kalici.bir_is(depo, AYAR, "B")))
    b.start(); a.join(); b.join()
    assert sonuc["A"]["durum"] == "atildi" and sonuc["B"]["durum"] == "bitti"
    _pdf_yerinde(depo)
