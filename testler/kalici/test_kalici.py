"""İE-02 kabul testleri T1–T9 (docs/is_emirleri/IE-02.md): gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp.

Motor, testin konusu olmadığı yerde hızlı bir sahte üreticiyle değiştirilir (hizli_motor); Motor'un gerçekten koşulduğu
testler test_yeniden_baslatma.py ve kabul_gosterimi.py'de.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici -q
"""
from __future__ import annotations

import threading
import time

import pytest

from conftest import (AYAR, BAYI_B, NUMARA_A, NUMARA_B, geri_al, mesaj, sorgu, talep, tek)

import kalici
import worker as W
from depo import Cakisma, KiraKaybi, satir_id

T_P6001 = talep(ozet="P6001 aynalı", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}])
T_ONAY = talep("onay", "onay")


def isle_hepsi(depo, sahip="test-isleyici", ayar=AYAR) -> list[dict]:
    sonuclar = []
    while (r := kalici.bir_is(depo, ayar, sahip)) is not None:
        sonuclar.append(r)
    return sonuclar


def plan_iste(depo, wa, numara=NUMARA_A, bayi=None, metin="P6001 aynalı", cikarim=T_P6001):
    g = mesaj(metin, cikarim, numara=numara, bayi=bayi)
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    return g, r


# ───────────────────────── temel akış ─────────────────────────
def test_temel_akis_plan_ve_onay(depo, wa, hizli_motor):
    g, r = plan_iste(depo, wa)
    rev = tek(depo, "SELECT * FROM revizyonlar")
    assert rev["rev"] == 1 and rev["durum"] == "onay_bekliyor" and rev["kaynak_mesaj_id"] == g["id"]
    assert [x["kind"] for x in wa.gonderilen] == ["text", "document"]
    time.sleep(1.1)
    o = mesaj("onaylıyorum", T_ONAY)
    assert depo.mesaj_kaydet(o)
    [r2] = isle_hepsi(depo)
    assert r2["gerekce"] == "plan onaylandı"
    rev = tek(depo, "SELECT * FROM revizyonlar")
    assert rev["durum"] == "onaylandi" and rev["onay_mesaj_id"] == o["id"]


def test_satir_id_worker_ile_ayni():
    assert satir_id("wamid.X", 3) == W.satir_id("wamid.X", 3)


# ───────────────────────── T1 tekilleştirme ─────────────────────────
def test_t1_ayni_mesaj_tekrar_gelince_ikinci_is_yok(depo, wa, hizli_motor):
    g = mesaj("P6001 aynalı", T_P6001)
    assert depo.mesaj_kaydet(g) is True
    assert depo.mesaj_kaydet(g) is False
    isle_hepsi(depo)
    assert depo.mesaj_kaydet(g) is False                 # iş bittikten sonra da (geç yeniden teslim)
    assert isle_hepsi(depo) == []
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 2
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1


def test_t1_eszamanli_ayni_mesaj_tek_is(depo):
    g = mesaj("P6001 aynalı", T_P6001)
    sonuc, engel = [], threading.Barrier(8)

    def yaz():
        engel.wait()
        sonuc.append(depo.mesaj_kaydet(g))
    iplikler = [threading.Thread(target=yaz) for _ in range(8)]
    [t.start() for t in iplikler]; [t.join() for t in iplikler]
    assert sorted(sonuc) == [False] * 7 + [True]
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1


def test_t1_d01_sorusu_askidayken_tekrar_gelen_mesaj_sayaci_artirmaz(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    g = mesaj("P6001 yatak odası penceresi 120x180", talep("revizyon", "P6001 pencere", katalog_kodu="P6001"))
    depo.mesaj_kaydet(g); isle_hepsi(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["son_soru_alani"] == "yeni_mi_degisiklik" and d["eski_taslak_soru"] == 1
    belirsiz = mesaj("hmm", talep("diger", "belirsiz"))
    depo.mesaj_kaydet(belirsiz); isle_hepsi(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["eski_taslak_soru"] == 2
    for _ in range(3):                                   # aynı mesaj teknik olarak üç kez daha geliyor
        assert depo.mesaj_kaydet(belirsiz) is False
    isle_hepsi(depo)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["eski_taslak_soru"] == 2 and d["son_soru_alani"] == "yeni_mi_degisiklik"
    s = tek(depo, "SELECT * FROM sorular WHERE durum = 'acik'")
    assert s["deneme"] == 2 and s["kaynak_mesaj_id"] == g["id"]


# ───────────────────────── T2 yeniden başlatma: soru askıdayken süreç değişir ─────────────────────────
def yeni_surecte_isle(depo, *, tek=True) -> dict:
    """İşi ayrı bir Python sürecinde işler (yeniden başlatılmış işleyici): bellekte hiçbir şey taşınmaz. Motor burada
    konu değil, hızlı sahte üreticiyle değiştirilir; gerçek Motor'la yeniden başlatma test_yeniden_baslatma.py'de."""
    import json, os, subprocess, sys, tempfile
    from conftest import KANAL_VERI, KOK
    ayar = Path(tempfile.mkstemp(suffix=".json")[1]); ayar.write_text(json.dumps(AYAR), encoding="utf-8")
    betik = ("import sys; sys.path[:0] = [%r, %r, %r]\n"
             "import conftest\nfrom motor import dxf_out\ndxf_out.uret = conftest.sahte_uret\n"
             "import kalici\nsys.exit(kalici.main(['isle', '--ayar', %r] + (['--tek'] if %r else [])))\n"
             % (str(KOK / "testler" / "kalici"), str(KOK), str(KOK / "kanal"), str(ayar), tek))
    env = {**os.environ, "PORTMAN_PG_DSN": depo.dsn, "PORTMAN_KANAL_DIR": str(W.KANAL)}
    r = subprocess.run([sys.executable, "-c", betik], capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    satirlar = [l for l in r.stdout.splitlines() if l.startswith("{")]
    return json.loads(satirlar[-1]) if satirlar else {}


from pathlib import Path  # noqa: E402

T_PENCERE_DEGISTIR = talep("revizyon", "P6001 yatak odası 1 penceresi 120x180", katalog_kodu="P6001",
                           pencereler=[{"mahal": "Yatak Odası 1", "olcu": "120x180", "islem": "degistir"}])


def test_t2_d01_sorusu_yeniden_baslatmadan_sonra_dogru_cevapla_kapanir(depo, wa, hizli_motor):
    _, r1 = plan_iste(depo, wa)                                   # aynalı r01
    geri_al(depo, NUMARA_A, 3.5)
    g = mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR)
    depo.mesaj_kaydet(g)
    assert yeni_surecte_isle(depo)["eylem"] == "sor"             # süreç 1: soru sorulur, süreç biter
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["alan"], s["durum"], s["kaynak_mesaj_id"]) == ("yeni_mi_degisiklik", "acik", g["id"])
    assert s["bekletilen_talep"]["pencereler"][0]["olcu"] == "120x180" and "120x180" in s["bekletilen_metin"]
    assert s["gecerlilik_sonu"] is not None and s["proje_id"] == r1["proje_id"]
    cevap = mesaj("yeni", talep("diger", "yeni"))
    depo.mesaj_kaydet(cevap)
    r = yeni_surecte_isle(depo)                                   # süreç 2: cevap bekletilen mesaja bağlanır
    assert r["eylem"] == "is_emri"
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["durum"], s["cevap_mesaj_id"]) == ("cevaplandi", cevap["id"])
    yeni = tek(depo, "SELECT * FROM revizyonlar WHERE kaynak_mesaj_id = %s", cevap["id"])
    assert yeni["proje_id"] != r1["proje_id"] and yeni["rev"] == 1       # "yeni": ayrı proje
    assert not _aynali(yeni["is_emri"]) and _pencere_var(yeni["is_emri"], "YATAK ODASI 1", "120x180")
    eski = tek(depo, "SELECT durum FROM revizyonlar WHERE proje_id = %s", r1["proje_id"])
    assert eski["durum"] == "onay_bekliyor"                       # eski proje olduğu gibi


def test_t2_d01_degisiklik_cevabi_ayni_projeye_revizyon(depo, wa, hizli_motor):
    _, r1 = plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    depo.mesaj_kaydet(mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR))
    yeni_surecte_isle(depo)
    cevap = mesaj("değişiklik", talep("diger", "değişiklik"))
    depo.mesaj_kaydet(cevap)
    assert yeni_surecte_isle(depo)["eylem"] == "is_emri"
    r2 = tek(depo, "SELECT * FROM revizyonlar WHERE kaynak_mesaj_id = %s", cevap["id"])
    assert r2["proje_id"] == r1["proje_id"] and r2["rev"] == 2
    assert _aynali(r2["is_emri"]) and _pencere_var(r2["is_emri"], "YATAK ODASI 1", "120x180")
    assert [x["durum"] for x in sorgu(depo, "SELECT durum FROM revizyonlar ORDER BY id")] == ["yerini_aldi", "onay_bekliyor"]


BELIRSIZ = "P6001, yatak odası 1, 120x180"
T_B1_BELIRSIZ = talep("yeni_talep", "P6001, yatak odası 1 penceresi 120x180.", katalog_kodu="P6001",
                      pencereler=[{"mahal": "Yatak Odası 1", "olcu": "120x180", "islem": None}])


def test_t2_b1_pencere_sorusu_yeniden_baslatmadan_sonra_cevaplanir(depo, hizli_motor):
    g = mesaj(BELIRSIZ, T_B1_BELIRSIZ)
    depo.mesaj_kaydet(g)
    assert yeni_surecte_isle(depo)["eylem"] == "sor"
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["alan"], s["kaynak_mesaj_id"]) == ("pencere_islem", g["id"]) and s["pencere_satiri"] is not None
    cevap = mesaj("değiştir", talep("diger", "değiştir"))
    depo.mesaj_kaydet(cevap)
    assert yeni_surecte_isle(depo)["eylem"] == "is_emri"
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["durum"], s["cevap_mesaj_id"]) == ("cevaplandi", cevap["id"])
    r = tek(depo, "SELECT * FROM revizyonlar")
    assert _pencere_var(r["is_emri"], "YATAK ODASI 1", "120x180")


def test_t2_eksik_bilgi_sorusu_yeniden_baslatmadan_sonra_cevaplanir(depo, hizli_motor):
    g = mesaj("P9999 istiyorum", talep("yeni_talep", "P9999", katalog_kodu="P9999"))
    depo.mesaj_kaydet(g)
    assert yeni_surecte_isle(depo)["eylem"] == "sor"
    s = tek(depo, "SELECT * FROM sorular WHERE durum = 'acik'")
    assert (s["alan"], s["kaynak_mesaj_id"]) == ("katalog_kodu", g["id"])
    cevap = mesaj("P6001", talep("yeni_talep", "P6001", katalog_kodu="P6001"))
    depo.mesaj_kaydet(cevap)
    assert yeni_surecte_isle(depo)["eylem"] == "is_emri"
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["alan"], s["durum"], s["cevap_mesaj_id"]) == ("katalog_kodu", "cevaplandi", cevap["id"])


def test_t2_cevap_devirle_sonuclanirsa_soru_devredildi_kapanir(depo, hizli_motor):
    """Serbest yerleşim v0.1'de yok: oda programı sorusunun cevabı talebi Lokman'a devreder; soru o cevapla kapanır."""
    depo.mesaj_kaydet(mesaj("6x8 m bir ev istiyorum", talep("yeni_talep", "6x8 m ev", dis_olcu={"en_m": 6, "boy_m": 8})))
    assert yeni_surecte_isle(depo)["eylem"] == "sor"
    assert tek(depo, "SELECT alan FROM sorular WHERE durum = 'acik'")["alan"] == "oda_programi"
    cevap = mesaj("2+1", talep("yeni_talep", "2+1", oda_programi="2+1"))
    depo.mesaj_kaydet(cevap)
    assert yeni_surecte_isle(depo)["eylem"] == "yonlendir"
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["durum"], s["cevap_mesaj_id"]) == ("devredildi", cevap["id"])


# ───────────────────────── T3 yarım iş (süreç içinde; gerçek süreç öldürme test_yeniden_baslatma.py'de) ─────────────────────────
class _Coktu(BaseException):
    """Süreç ölümünü taklit eder: Exception değil, hiçbir except yakalamaz."""


def test_t3_yarim_is_kurtarilir_llm_yeniden_cagrilmaz(depo, wa, monkeypatch):
    from motor import dxf_out
    from conftest import sahte_uret
    cagri = []
    asil_cikar = W.cikar
    monkeypatch.setattr(W, "cikar", lambda *a, **k: (cagri.append(1), asil_cikar(*a, **k))[1])

    def coken(*a, **k):
        raise _Coktu()
    monkeypatch.setattr(dxf_out, "uret", coken)
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    with pytest.raises(_Coktu):
        kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, "isleyici-1")
    j = tek(depo, "SELECT * FROM isler")
    assert (j["durum"], j["deneme"], j["cikarim"] is not None) == ("isleniyor", 1, True)
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 0 and depo.konusma_oku(NUMARA_A) == (None, 0)
    assert kalici.bir_is(depo, AYAR, "isleyici-2") is None     # kira dolmadan kimse almaz
    time.sleep(1.2)
    monkeypatch.setattr(dxf_out, "uret", sahte_uret)
    r = kalici.bir_is(depo, AYAR, "isleyici-2")
    assert r["eylem"] == "is_emri" and cagri == [1]              # LLM yalnız ilk denemede çağrıldı
    j = tek(depo, "SELECT * FROM isler")
    assert (j["durum"], j["deneme"]) == ("bitti", 2)
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 2 and tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1


def test_t3_deneme_hakki_bitince_basarisiz_ve_bildirim(depo, monkeypatch):
    from motor import dxf_out

    def coken(*a, **k):
        raise _Coktu()
    monkeypatch.setattr(dxf_out, "uret", coken)
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001))
    for i in range(3):
        with pytest.raises(_Coktu):
            kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, f"isleyici-{i}")
        time.sleep(1.1)
    assert kalici.bir_is(depo, AYAR, "isleyici-4") is None
    j = tek(depo, "SELECT * FROM isler")
    assert j["durum"] == "basarisiz" and j["deneme"] == 3 and "3 denemede" in j["hata"]
    satirlar = sorgu(depo, "SELECT alici, tur FROM giden ORDER BY sira")
    assert [(s["alici"], s["tur"]) for s in satirlar] == [(NUMARA_A, "cevap"), ("PATRON", "bildirim")]


# ───────────────────────── T4 sessiz ezme yok ─────────────────────────
def test_t4_eski_surumle_yazma_reddedilir(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    d0, s0 = depo.konusma_oku(NUMARA_A)
    g = mesaj("aynalı olsun", talep("revizyon", "aynalı", varyantlar=[{"tur": "ayna_y", "aciklama": "aynalı"}]))
    depo.mesaj_kaydet(g)
    alinan = depo.is_al("yavas-isleyici")
    geri_al(depo, NUMARA_A, 0.01)                                # başka bir yazma: sürüm artar
    cikti = {"satirlar": [W.giden_metin(g, "deneme", 1)], "sonuc": {"eylem": "cevapla", "gerekce": "deneme"}}
    with pytest.raises(Cakisma):
        depo.isi_bitir(alinan["is"], "yavas-isleyici", g, s0, d0, dict(d0, asama="ezilmemeli"), cikti)
    d1, s1 = depo.konusma_oku(NUMARA_A)
    assert s1 == s0 + 1 and d1["asama"] != "ezilmemeli"
    assert tek(depo, "SELECT count(*) n FROM giden WHERE mesaj_id = %s", g["id"])["n"] == 0
    depo.is_geri_birak(alinan["is"]["id"], "yavas-isleyici", "çakışma")
    r = kalici.bir_is(depo, AYAR, "ikinci")                      # yeniden sıraya girdi; güncel durumla işlenir
    assert r["durum"] == "bitti" and r["eylem"] == "is_emri"


def test_t4_kirasi_devredilen_isin_gec_sonucu_atilir(depo, hizli_motor):
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g)
    alinan = depo.is_al("A", kira_sn=1)
    time.sleep(1.2)
    r = kalici.bir_is(depo, AYAR, "B")
    assert r["durum"] == "bitti"
    d, s = depo.konusma_oku(NUMARA_A)
    cikti = {"satirlar": [W.giden_metin(g, "geç kalan sonuç", 1)], "sonuc": {"eylem": "cevapla", "gerekce": "geç"}}
    with pytest.raises(KiraKaybi):
        depo.isi_bitir(alinan["is"], "A", g, s, d, d, cikti)
    assert [x["govde"] for x in sorgu(depo, "SELECT govde FROM giden WHERE sira = 1")] != ["geç kalan sonuç"]
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 2 and depo.konusma_oku(NUMARA_A)[1] == s


def test_t4_art_arda_iki_degisiklik_ikisi_de_uygulanir(depo, wa, hizli_motor):
    plan_iste(depo, wa, metin="P6001", cikarim=talep(ozet="P6001", katalog_kodu="P6001"))
    g1 = mesaj("aynalı olsun", talep("revizyon", "aynalı", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}]))
    g2 = mesaj("yatak odası 1 penceresi 120x180 olsun", talep("revizyon", "yatak odası 1 penceresi 120x180",
               pencereler=[{"mahal": "Yatak Odası 1", "olcu": "120x180", "islem": "degistir"}]))
    depo.mesaj_kaydet(g1); depo.mesaj_kaydet(g2)
    sonuclar, engel = [], threading.Barrier(3)

    def isleyici(ad):
        engel.wait()
        for _ in range(50):
            r = kalici.bir_is(depo, AYAR, ad)
            if r is not None:
                sonuclar.append(r)
            if tek(depo, "SELECT count(*) n FROM isler WHERE durum IN ('sirada', 'isleniyor')")["n"] == 0:
                return
            time.sleep(0.02)
    iplikler = [threading.Thread(target=isleyici, args=(f"i{i}",)) for i in range(3)]
    [t.start() for t in iplikler]; [t.join() for t in iplikler]
    assert sorted(r["durum"] for r in sonuclar) == ["bitti", "bitti"]
    j1, j2 = sorgu(depo, "SELECT * FROM isler WHERE mesaj_id IN (%s, %s) ORDER BY id", g1["id"], g2["id"])
    assert j2["basladi"] >= j1["bitti"]                          # aynı göndericinin işleri sırayla
    son = tek(depo, "SELECT * FROM revizyonlar ORDER BY id DESC LIMIT 1")
    assert son["rev"] == 3 and _aynali(son["is_emri"]) and _pencere_var(son["is_emri"], "YATAK ODASI 1", "120x180")


# ───────────────────────── T5 gönderim sonucu belirsiz ─────────────────────────
def test_t5_belirsiz_gonderim_yeniden_gonderilmez(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    wa.mod = "belirsiz"
    assert kalici.gonder(depo, wa)["belirsiz"] == 2
    ilk = len(wa.gonderilen)
    wa.mod = "tamam"
    assert kalici.gonder(depo, wa)["kabul_edildi"] == 0 and len(wa.gonderilen) == ilk
    assert {x["durum"] for x in sorgu(depo, "SELECT durum FROM giden")} == {"belirsiz"}


def test_t5_yarida_kalan_gonderim_belirsiz_sayilir(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    r = depo.gonderime_al()                                       # gönderici bu satırı aldı ve süreç düştü
    with depo.baglan() as c:
        c.execute("UPDATE giden SET gonderim_basladi = now() - interval '11 minutes' WHERE id = %s", (r["id"],))
    say = kalici.gonder(depo, wa)
    assert say["yarim_belirsiz"] == 1 and say["kabul_edildi"] == 1
    assert r["id"] not in [x["id"] for x in wa.gonderilen]
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", r["id"])["durum"] == "belirsiz"


def test_t5_kesin_gonderilmeyen_satir_isaretlenir(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    wa.mod = "gonderilmedi"
    assert kalici.gonder(depo, wa)["gonderilmedi"] == 2 and wa.gonderilen == []


# ───────────────────────── T6 bayi ayrımı ─────────────────────────
def test_t6_baska_bayinin_kaydi_okunamaz_ve_onayi_etkilemez(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    plan_iste(depo, wa, numara=NUMARA_B, bayi=BAYI_B)
    ra = tek(depo, "SELECT * FROM revizyonlar WHERE bayi_kod = 'TSTA'")
    rb = tek(depo, "SELECT * FROM revizyonlar WHERE bayi_kod = 'TSTB'")
    assert depo.revizyon(NUMARA_B, ra["is_emri_no"]) is None and depo.cikti_yolu(NUMARA_B, ra["is_emri_no"]) is None
    assert depo.revizyon(NUMARA_A, ra["is_emri_no"])["id"] == ra["id"]
    assert [p["ilk_is_emri_no"] for p in depo.projeler(NUMARA_B)] == [rb["is_emri_no"]]
    time.sleep(1.1)
    depo.mesaj_kaydet(mesaj("onaylıyorum", T_ONAY, numara=NUMARA_B, bayi=BAYI_B)); isle_hepsi(depo)
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", ra["id"])["durum"] == "onay_bekliyor"
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rb["id"])["durum"] == "onaylandi"


def test_t6_baska_bayinin_cevabi_askidaki_soruyu_kapatmaz(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    depo.mesaj_kaydet(mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR)); isle_hepsi(depo)
    depo.mesaj_kaydet(mesaj("yeni", talep("diger", "yeni"), numara=NUMARA_B, bayi=BAYI_B)); isle_hepsi(depo)
    s = tek(depo, "SELECT * FROM sorular WHERE gonderen = %s", NUMARA_A)
    assert s["durum"] == "acik"
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["son_soru_alani"] == "yeni_mi_degisiklik" and d.get("bekleyen_talep")


# ───────────────────────── T7 eski revizyonun onayı ─────────────────────────
def _revizyon_iste(depo):
    g = mesaj("aynalı olsun", talep("revizyon", "aynalı", varyantlar=[{"tur": "ayna_y", "aciklama": "aynalı"}]))
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri"
    return r


def test_t7_iletilmeden_yazilan_onay_yeni_revizyonu_onaylamaz(depo, wa, hizli_motor):
    plan_iste(depo, wa)                                           # r01 gönderildi (API kabul etti)
    _revizyon_iste(depo)                                          # r02 hazır, henüz gönderilmedi
    o = mesaj("onaylıyorum", T_ONAY)                              # bayi r01'i görüp yazdı
    depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert r["gerekce"].startswith("onay bağlanmadı")
    assert [x["durum"] for x in sorgu(depo, "SELECT durum FROM revizyonlar ORDER BY rev")] == ["yerini_aldi", "onay_bekliyor"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor"
    kalici.gonder(depo, wa)                                       # r02 gönderildi (API kabul etti)
    time.sleep(1.1)
    o2 = mesaj("onaylıyorum", T_ONAY); depo.mesaj_kaydet(o2)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı"
    assert tek(depo, "SELECT rev, onay_mesaj_id FROM revizyonlar WHERE durum = 'onaylandi'") == {"rev": 2, "onay_mesaj_id": o2["id"]}


def test_t7_eski_revizyonu_alintilayan_onay_reddedilir(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    r01_pdf = tek(depo, "SELECT dis_id FROM giden WHERE kind = 'document'")["dis_id"]
    _revizyon_iste(depo); kalici.gonder(depo, wa)
    time.sleep(1.1)
    o = mesaj("onaylıyorum", T_ONAY, context_id=r01_pdf); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert "alıntı" in r["gerekce"]
    assert tek(depo, "SELECT count(*) n FROM revizyonlar WHERE durum = 'onaylandi'")["n"] == 0
    son = tek(depo, "SELECT govde FROM giden WHERE mesaj_id = %s", o["id"])["govde"]
    assert "r01" in son and "r02" in son


def test_t7_iletimi_belirsiz_revizyon_onaylanmaz_patrona_bildirilir(depo, wa, hizli_motor):
    plan_iste(depo, wa)
    _revizyon_iste(depo)
    wa.mod = "belirsiz"; kalici.gonder(depo, wa); wa.mod = "tamam"
    time.sleep(1.1)
    o = mesaj("onaylıyorum", T_ONAY); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert "teyitsiz" in r["gerekce"]
    assert [x["alici"] for x in sorgu(depo, "SELECT alici FROM giden WHERE mesaj_id = %s ORDER BY sira", o["id"])] == [NUMARA_A, "PATRON"]


# ───────────────────────── T8 yedek ayrı veritabanına geri yüklenir ─────────────────────────
def test_t8_yedek_ayri_veritabaninda_geri_yuklenir_ve_akis_surer(depo, wa, hizli_motor, tmp_path):
    import shutil, subprocess
    from conftest import ADMIN, _admin, dsn
    from depo import Depo
    plan_iste(depo, wa)
    geri_al(depo, NUMARA_A, 3.5)
    depo.mesaj_kaydet(mesaj("P6001 yatak odası 1 penceresi 120x180 olsun", T_PENCERE_DEGISTIR)); isle_hepsi(depo)
    yedek = tmp_path / "portman.dump"
    subprocess.run([shutil.which("pg_dump"), "-Fc", "-f", str(yedek), "-d", depo.dsn], check=True)
    hedef = depo.ad + "_geri"
    with _admin() as c:
        c.execute(f"CREATE DATABASE {hedef}")
    try:
        subprocess.run([shutil.which("pg_restore"), "--exit-on-error", "-d", dsn(hedef), str(yedek)], check=True)
        geri = Depo(dsn(hedef))
        tablolar = ["bayiler", "mesajlar", "isler", "konusmalar", "sorular", "projeler", "revizyonlar", "giden", "sema_surumu"]
        for t in tablolar:
            assert sorgu(depo, f"SELECT * FROM {t} ORDER BY 1") == sorgu(geri, f"SELECT * FROM {t} ORDER BY 1"), t
        cevap = mesaj("değişiklik", talep("diger", "değişiklik"))
        geri.mesaj_kaydet(cevap)
        [r] = isle_hepsi(geri)
        assert r["eylem"] == "is_emri"
        s = tek(geri, "SELECT * FROM sorular")
        assert (s["durum"], s["cevap_mesaj_id"]) == ("cevaplandi", cevap["id"])
        assert tek(geri, "SELECT max(rev) m FROM revizyonlar")["m"] == 2
        assert tek(depo, "SELECT durum FROM sorular")["durum"] == "acik"      # asıl veritabanı etkilenmedi
        yeni_id = tek(geri, "SELECT nextval('isler_id_seq') n")["n"]
        assert yeni_id > tek(depo, "SELECT max(id) m FROM isler")["m"]         # dizi değerleri de geri geldi
    finally:
        with _admin() as c:
            c.execute(f"DROP DATABASE IF EXISTS {hedef} WITH (FORCE)")


# ───────────────────────── T9 JSON ↔ Postgres ─────────────────────────
def test_t9_json_postgres_json_kayipsiz_ve_bekleyen_soru_surer(depo, tmp_path, hizli_motor):
    import json
    from beyin.konusma import Konusma
    from beyin.karar import karar_ver
    from beyin.katalog import Katalog
    from beyin.sema import Talep
    import depo_aktar
    kanal = tmp_path / "kanal"
    # dosya düzeninde (bugünkü canlı düzen) bir D-01 sorusu askıda: aynalı taslak, 3,5 saat sonra model kodlu mesaj
    k = Konusma(NUMARA_A, kanal / "durum")
    karar_ver(Talep.model_validate(T_P6001), k, BAYI_A_KARAR, Katalog(), metin="P6001 aynalı")
    d = json.loads(k.path.read_text()); 
    for a in ("guncellendi", "taslak_zamani"):
        d[a] -= 3 * 3600 + 1800
    k.path.write_text(json.dumps(d, ensure_ascii=False))
    k = Konusma(NUMARA_A, kanal / "durum")
    karar = karar_ver(Talep.model_validate(T_PENCERE_DEGISTIR), k, BAYI_A_KARAR, Katalog(),
                      metin="P6001 yatak odası 1 penceresi 120x180 olsun")
    assert karar.soru_alani == "yeni_mi_degisiklik"
    ikinci = Konusma(NUMARA_B, kanal / "durum"); ikinci.d["taslak"] = {"katalog_kodu": "P7401"}; ikinci.kaydet()
    kuyruk = {"wamid.ESKI1": {**mesaj("P6001 aynalı", T_P6001, mid="wamid.ESKI1"), "state": "done"},
              "wamid.BEKLEYEN1": {**mesaj("değişiklik", talep("diger", "değişiklik"), mid="wamid.BEKLEYEN1"), "state": "queued"}}
    (kanal / "state.json").write_text(json.dumps({"version": 1, "inbound": kuyruk, "outbound": {}}, ensure_ascii=False))
    once = {p.name: json.loads(p.read_text()) for p in (kanal / "durum").glob("*.json")}
    say = depo_aktar.ice_aktar(depo, kanal, sirada_olanlar="is")          # hosting'siz: kuyruktaki mesaj iş olur
    assert say == {"konusma": 2, "konusma_atlandi": 0, "soru": 1, "mesaj": 2, "mesaj_atlandi": 0, "sirada": 1, "kuyrukta_birakildi": 0}
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["alan"], s["kaynak_mesaj_id"], s["durum"]) == ("yeni_mi_degisiklik", None, "acik") and "120x180" in s["bekletilen_metin"]
    assert depo_aktar.ice_aktar(depo, kanal, sirada_olanlar="is")["konusma_atlandi"] == 2   # ikinci kez: üzerine yazılmaz
    assert depo.mesaj_kaydet(kuyruk["wamid.ESKI1"]) is False                        # işlenmiş mesaj yeniden gelirse işlenmez
    geri = tmp_path / "geri"
    depo_aktar.disa_aktar(depo, geri)
    assert {p.name: json.loads(p.read_text()) for p in (geri / "durum").glob("*.json")} == once
    [r] = isle_hepsi(depo)                                          # geçişte sıradaki cevap, askıdaki soruya bağlanır
    assert r["mesaj_id"] == "wamid.BEKLEYEN1" and r["eylem"] == "is_emri"
    s = tek(depo, "SELECT * FROM sorular")
    assert (s["durum"], s["cevap_mesaj_id"]) == ("cevaplandi", "wamid.BEKLEYEN1")
    ie = tek(depo, "SELECT is_emri FROM revizyonlar")["is_emri"]
    assert _aynali(ie) and _pencere_var(ie, "YATAK ODASI 1", "120x180")


# ───────────────────────── yardımcılar ─────────────────────────
import json as _json  # noqa: E402
from conftest import BAYI_A, KOK  # noqa: E402

BAYI_A_KARAR = BAYI_A
_SABLON = _json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))


def _konum(ie: dict, ad: str):
    m = next((x for x in ie.get("mahaller", []) if x["ad"] == ad), None)
    return [list(map(float, r)) for r in (m or {}).get("konum_pano") or []]


def _aynali(ie: dict | None) -> bool:
    return ie is not None and _konum(ie, "YATAK ODASI 1") != _konum(_SABLON, "YATAK ODASI 1")


def _pencere_var(ie: dict | None, mahal: str, olcu: str) -> bool:
    return bool(ie) and any(a["tur"] == "pencere" and a.get("mahal") == mahal and a.get("olcu") == olcu for a in ie["acikliklar"])


# ───────────────────────── G-1/G-2 (29.09 canlı kapı G, Opus 5.5) ─────────────────────────
def test_g1_g2_canli_sira_opus_cikarimiyla_soru_cevaplanir_ve_r02_ayni_projede(depo, wa, hizli_motor):
    """Canlıdaki sıra, canlıdaki çıkarım biçimiyle: Opus kısa "değiştir"e bağlamdaki pencere isteğini (satır + varyant, niyet
    revizyon) yeniden doldurdu. v1.2'de soru 'dustu' kapanıyor, plan r03 oluyordu; beklenen: soru 'cevaplandi', aynı projede r02."""
    P = [{"mahal": "yatak odası 1", "olcu": "120x180", "islem": "degistir"}]
    V = [{"tur": "pencere_degistir", "aciklama": "yatak odası 1 penceresi 120x180", "parametreler": {"mahal": "yatak odası 1", "yeni": "120x180"}}]
    plan_iste(depo, wa)
    g2 = mesaj("yatak odası 1, 120x180", talep("revizyon", "yatak odası 1 penceresi 120x180", guven="orta", pencereler=P, varyantlar=V))
    assert depo.mesaj_kaydet(g2)
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "sor"
    kalici.gonder(depo, wa)
    g3 = mesaj("değiştir", talep("revizyon", "yatak odası 1 penceresi 120x180", katalog_kodu="P6001", pencereler=P, varyantlar=V))
    assert depo.mesaj_kaydet(g3)
    [r3] = isle_hepsi(depo)
    assert r3["eylem"] == "is_emri"
    soru = tek(depo, "SELECT * FROM sorular")
    assert (soru["alan"], soru["durum"], soru["kaynak_mesaj_id"], soru["cevap_mesaj_id"]) == ("pencere_islem", "cevaplandi", g2["id"], g3["id"])
    revler = sorgu(depo, "SELECT proje_id, rev, durum FROM revizyonlar ORDER BY id")
    assert [(r["rev"], r["durum"]) for r in revler] == [(1, "yerini_aldi"), (2, "onay_bekliyor")]
    assert revler[0]["proje_id"] == revler[1]["proje_id"] == soru["proje_id"]
