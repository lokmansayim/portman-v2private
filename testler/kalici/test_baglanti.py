"""İE-02 bağlantı turu (Astra, 28.09 ikinci değerlendirme):
  A. Göç 002: API kabulü ile telefona teslim ayrı; 001'den yükseltme.
  B. Onay zinciri: gönderilen mesaj kimliği → revizyon → proje → gelen cevap; eski onayın reddi VE güncel onayın kabulü.
  C. D-03 kapsamı: yalnız süreç düşmesi / kira kaybı yeniden alınır; ötekiler tekrar edilmez.
  D. Ajanın kalıcı modu (vps/agent.py) SAHTE hosting API ile (testler/kalici/sahte_hosting.py). Bu, ajanın Python tarafını
     sınar; gerçek PHP hattını DOĞRULAMAZ (bkz. kanal/tests/baglanti_test.php, portman/lib.php gerekir).
"""
from __future__ import annotations

import os
import socket
import sys
import time
from pathlib import Path

import psycopg
import pytest

from conftest import ADMIN, AYAR, BAYI_A, KOK, NUMARA_A, _admin, dsn, mesaj, sorgu, talep, tek
from test_kalici import T_ONAY, T_P6001, isle_hepsi, plan_iste

import kalici
import worker as W
from depo import Depo, GOC_DIR, metin_satiri

T_AYNA_Y = talep("revizyon", "aynalı", varyantlar=[{"tur": "ayna_y", "aciklama": "aynalı"}])


# ───────────────────────── A. göç 002 ─────────────────────────
def test_goc_001den_002ye_yukseltme_kabul_zamani_korunur(sablon):
    ad = "t_goc_" + os.urandom(4).hex()
    with _admin() as c:
        c.execute(f"CREATE DATABASE {ad}")
    try:
        d = Depo(dsn(ad))
        with d.baglan() as c:
            c.execute("CREATE TABLE sema_surumu (surum int PRIMARY KEY, ad text NOT NULL, uygulandi timestamptz NOT NULL DEFAULT now())")
            c.execute((GOC_DIR / "001_kalici_akis.sql").read_text(encoding="utf-8"))
            c.execute("INSERT INTO sema_surumu (surum, ad) VALUES (1, '001_kalici_akis.sql')")
            c.execute("INSERT INTO mesajlar (id, gonderen, tur, wa_zamani, ham) VALUES ('wamid.E1', %s, 'text', now(), '{}')", (NUMARA_A,))
            c.execute("INSERT INTO isler (mesaj_id, gonderen, durum) VALUES ('wamid.E1', %s, 'bitti')", (NUMARA_A,))
            c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum, dis_id, iletildi) "
                      "VALUES ('out_eski', 1, 'wamid.E1', 1, %s, 'cevap', 'text', 'x', 'iletildi', 'wamid.G1', '2026-09-28 10:00+00')", (NUMARA_A,))
        assert d.eksik_goc() == [2]
        assert d.goc_uygula() == [2] and d.eksik_goc() == []
        r = tek(d, "SELECT durum, dis_id, kabul_zamani, teslim_durumu FROM giden")
        assert (r["durum"], r["dis_id"], r["teslim_durumu"]) == ("kabul_edildi", "wamid.G1", None)
        import datetime
        assert r["kabul_zamani"] == datetime.datetime(2026, 9, 28, 10, 0, tzinfo=datetime.timezone.utc)
        with pytest.raises(psycopg.errors.CheckViolation):          # eski durum adı artık yazılamaz
            with d.baglan() as c:
                c.execute("UPDATE giden SET durum = 'iletildi'")
    finally:
        with _admin() as c:
            c.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")


def test_depo_hata_satiri_worker_bicimiyle_ayni():
    g = mesaj("x", T_P6001)
    a, b = metin_satiri(g, "metin", 2, "PATRON", "bildirim"), W.giden_metin(g, "metin", 2, "PATRON", "bildirim")
    for s in (a, b):
        s.pop("created_at"); s.pop("updated_at")
    assert a == b


# ───────────────────────── B. onay zinciri ─────────────────────────
def hosting_gonderdi(depo, kabul: float, teslim: float | None = None, teslim_durumu: str = "delivered") -> dict[str, str]:
    """Bekleyen satırlar hosting'e verildi; hosting gönderdi (API kabul etti); isteğe bağlı Meta teslim bildirimi geldi.
    Hosting'in giden_durum cevabı biçiminde işlenir (ajanın durum_esitle yolu). Dönen: satır → wamid."""
    ids = [r["id"] for r in sorgu(depo, "SELECT id FROM giden WHERE durum = 'bekliyor' ORDER BY olusturuldu, sira")]
    depo.hostinge_verildi(ids)
    wamid = {}
    for i in ids:
        wamid[i] = "wamid.H" + i[-10:]
        depo.hosting_durumu_isle(i, {"state": teslim_durumu if teslim else "accepted", "wamid": wamid[i], "request_accepted_at": int(kabul),
                                     "delivery_state": teslim_durumu if teslim else None, "delivered_at": int(teslim) if teslim else None})
    return wamid


def _pdf_wamid(depo, rev: int) -> str:
    return tek(depo, "SELECT g.dis_id FROM giden g JOIN revizyonlar r ON r.id = g.revizyon_id WHERE r.rev = %s", rev)["dis_id"]


def test_guncel_revizyonun_dogru_onayi_kabul_edilir_zincir_tam(depo, hizli_motor):
    simdi = time.time()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=simdi - 200)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 100, teslim=simdi - 90)
    pdf = _pdf_wamid(depo, 1)
    o = mesaj("onaylıyorum", T_ONAY, ts=simdi, context_id=pdf); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı"
    onay = tek(depo, "SELECT sonuc->'onay' AS o FROM isler WHERE mesaj_id = %s", o["id"])["o"]
    assert onay["kabul"] is True and onay["sinir"] == "teslim" and onay["pdf_wamid"] == pdf and onay["alinti_id"] == pdf and onay["rev"] == 1
    z = tek(depo, "SELECT * FROM onay_zinciri")
    assert (z["revizyon_durumu"], z["pdf_wamid"], z["gonderim_durumu"], z["teslim_durumu"]) == ("onaylandi", pdf, "kabul_edildi", "delivered")
    assert (z["onay_mesaj_id"], z["onay_alintisi"]) == (o["id"], pdf) and z["proje_id"] is not None
    c = tek(depo, "SELECT * FROM cevap_baglari WHERE mesaj_id = %s", o["id"])
    assert (c["alintilanan_rev"], c["alintilanan_proje"], c["eylem"], c["onay"]["kabul"]) == (1, z["proje_id"], "cevapla", True)


def test_kabul_edilmis_ama_teslim_edilmemis_plana_yazilan_onay_reddedilir(depo, hizli_motor):
    """API kabulü teslim sayılmaz: teslim bildirimi varsa onay teslimden sonra yazılmış olmalı."""
    simdi = time.time()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=simdi - 200)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 100, teslim=simdi - 10)
    erken = mesaj("onaylıyorum", T_ONAY, ts=simdi - 50); depo.mesaj_kaydet(erken)
    [r] = isle_hepsi(depo)
    assert r["gerekce"].startswith("onay bağlanmadı") and "ulaşmadan" in r["gerekce"]
    assert tek(depo, "SELECT sonuc->'onay' AS o FROM isler WHERE mesaj_id = %s", erken["id"])["o"]["kabul"] is False
    gec = mesaj("onaylıyorum", T_ONAY, ts=simdi); depo.mesaj_kaydet(gec)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı" and tek(depo, "SELECT onay_mesaj_id FROM revizyonlar")["onay_mesaj_id"] == gec["id"]


def test_teslim_bildirimi_yoksa_kabul_ani_alt_sinirdir(depo, hizli_motor):
    simdi = time.time()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=simdi - 200)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 100)
    o = mesaj("onaylıyorum", T_ONAY, ts=simdi - 50); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı"
    assert tek(depo, "SELECT sonuc->'onay'->>'sinir' AS s FROM isler WHERE mesaj_id = %s", o["id"])["s"] == "kabul"


def test_meta_teslim_hatasi_verdiyse_onay_kaydedilmez_patrona_bildirilir(depo, hizli_motor):
    simdi = time.time()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=simdi - 200)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 100, teslim=simdi - 90, teslim_durumu="failed")
    o = mesaj("onaylıyorum", T_ONAY, ts=simdi); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert "teyitsiz (failed)" in r["gerekce"]
    assert [x["alici"] for x in sorgu(depo, "SELECT alici FROM giden WHERE mesaj_id = %s ORDER BY sira", o["id"])] == [NUMARA_A, "PATRON"]


def test_eski_revizyona_verilen_onay_reddedilir_guncele_verilen_kabul_edilir(depo, hizli_motor):
    simdi = time.time()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=simdi - 400)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 300, teslim=simdi - 290)
    depo.mesaj_kaydet(mesaj("aynalı olsun", T_AYNA_Y, ts=simdi - 200)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 100, teslim=simdi - 90)
    r01, r02 = _pdf_wamid(depo, 1), _pdf_wamid(depo, 2)
    eski = mesaj("onaylıyorum", T_ONAY, ts=simdi - 20, context_id=r01); depo.mesaj_kaydet(eski)
    [r] = isle_hepsi(depo)
    assert "alıntı başka revizyona ait" in r["gerekce"]
    yeni = mesaj("onaylıyorum", T_ONAY, ts=simdi, context_id=r02); depo.mesaj_kaydet(yeni)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı"
    assert [(x["rev"], x["durum"]) for x in sorgu(depo, "SELECT rev, durum FROM revizyonlar ORDER BY rev")] == [(1, "yerini_aldi"), (2, "onaylandi")]
    b = {x["mesaj_id"]: x for x in sorgu(depo, "SELECT * FROM cevap_baglari WHERE mesaj_id IN (%s, %s)", eski["id"], yeni["id"])}
    assert (b[eski["id"]]["alintilanan_rev"], b[eski["id"]]["onay"]["kabul"]) == (1, False)
    assert (b[yeni["id"]]["alintilanan_rev"], b[yeni["id"]]["onay"]["kabul"]) == (2, True)
    assert tek(depo, "SELECT onay_alintisi FROM onay_zinciri WHERE rev = 2")["onay_alintisi"] == r02


# ───────────────────────── C. D-03 kapsamı ─────────────────────────
def _vaka(ad: str) -> dict:
    if ad == "kayitsiz_numara":                                   # yetkisiz: kayıtlı bayi değil
        g = mesaj("P6001 aynalı", T_P6001); g["bayi"] = None; return g
    if ad == "eksik_bilgi_sorusu":                                # cevap bekleme
        return mesaj("6x8 m ev", talep("yeni_talep", "6x8 m ev", dis_olcu={"en_m": 6, "boy_m": 8}))
    if ad == "gecersiz_cikarim":                                  # geçersiz talep: LLM çıktısı şemaya uymuyor
        return mesaj("P6001 aynalı", talep(ozet="x", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x"}]))
    if ad == "llm_hatasi":                                        # LLM çağrısı hata verdi (manuel arka uçta kayıtlı çıktı yok)
        return mesaj("P6001 aynalı", None)
    if ad == "yazisiz_mesaj":
        return mesaj("", None, tur="image")
    raise ValueError(ad)


@pytest.mark.parametrize("ad, beklenen", [("kayitsiz_numara", ("bitti", "yonlendir")), ("eksik_bilgi_sorusu", ("bitti", "sor")),
                                          ("gecersiz_cikarim", ("basarisiz", "hata")), ("llm_hatasi", ("basarisiz", "hata")),
                                          ("yazisiz_mesaj", ("bitti", "cevapla"))])
def test_d03_tekrar_edilmeyen_sonuclar(depo, hizli_motor, monkeypatch, ad, beklenen):
    """D-03 yalnız süreç düşmesi ya da kira kaybında işi yeniden alır. Kayıtlı bir sonuç üreten her durum (yetkisiz numara,
    soru, geçersiz ya da hatalı LLM çıktısı, yazısız mesaj) bir kez yazılır; iş yeniden alınmaz, LLM yeniden çağrılmaz."""
    cagri = []
    asil = W.cikar
    monkeypatch.setattr(W, "cikar", lambda *a, **k: (cagri.append(1), asil(*a, **k))[1])
    depo.mesaj_kaydet(_vaka(ad))
    r = kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, "A")
    assert (r["durum"], r["eylem"]) == beklenen
    time.sleep(1.1)
    assert kalici.bir_is(depo, AYAR, "B") is None
    j = tek(depo, "SELECT durum, deneme FROM isler")
    assert (j["durum"], j["deneme"]) == (beklenen[0], 1)
    assert len(cagri) <= 1
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] >= 1          # bayiye (ve gerekirse Patron'a) bir kez yazıldı


def test_d03_beklenmeyen_hata_tekrar_edilmez(depo, monkeypatch):
    monkeypatch.setattr(W, "isle", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hata")))
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001))
    assert kalici.bir_is(depo, {**AYAR, "kira_sn": 1}, "A")["durum"] == "basarisiz"
    time.sleep(1.1)
    assert kalici.bir_is(depo, AYAR, "B") is None and tek(depo, "SELECT deneme FROM isler")["deneme"] == 1


def test_d03_belirsiz_gonderim_is_tekrarina_karismaz(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001)); isle_hepsi(depo)
    wa.mod = "belirsiz"; kalici.gonder(depo, wa); wa.mod = "tamam"
    assert kalici.bir_is(depo, AYAR, "B") is None
    assert tek(depo, "SELECT durum, deneme FROM isler") == {"durum": "bitti", "deneme": 1}
    assert kalici.gonder(depo, wa)["kabul_edildi"] == 0 and {x["durum"] for x in sorgu(depo, "SELECT durum FROM giden")} == {"belirsiz"}


# ───────────────────────── D. ajan kalıcı modu (sahte hosting; fikstür: conftest.ajan) ─────────────────────────
def test_ajan_uctan_uca_claim_postgres_teslim_esitleme(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    assert A.kalici_hazir(h.settings()) is None
    assert A.kalici_tur(ayar) is True
    assert tek(depo, "SELECT durum FROM isler WHERE mesaj_id = %s", g["id"])["durum"] == "bitti"
    assert h.inbound[g["id"]]["state"] == "done" and len(h.outbound) == 2
    belge = next(r for r in h.outbound.values() if r["kind"] == "document")
    assert belge["file"].startswith("projects/") and (h.kok / belge["file"]).is_file()
    assert {x["durum"] for x in sorgu(depo, "SELECT durum FROM giden")} == {"hostingte"}
    import json as _j
    assert _j.loads(h.durum[g["sender"]])["asama"] == "onay_bekliyor" and "proje_id" not in _j.loads(h.durum[g["sender"]])
    h.tick()
    ts = int(time.time()) - 1
    h.teslim(belge["wamid"] if "wamid" in belge else h.outbound[belge["id"]]["wamid"], "delivered", ts)
    A._kalici["son_esitleme"] = 0
    A.kalici_tur(ayar)
    s = tek(depo, "SELECT durum, dis_id, kabul_zamani, teslim_durumu, extract(epoch FROM teslim_zamani) AS t FROM giden WHERE kind = 'document'")
    assert (s["durum"], s["dis_id"], s["teslim_durumu"], int(s["t"])) == ("kabul_edildi", h.outbound[belge["id"]]["wamid"], "delivered", ts)
    metin = tek(depo, "SELECT durum, teslim_durumu, teslim_zamani FROM giden WHERE kind = 'text'")
    assert (metin["durum"], metin["teslim_durumu"], metin["teslim_zamani"]) == ("kabul_edildi", None, None)   # kabul teslim değil


def test_ajan_cevabi_kaybolan_teslimi_guvenle_yeniden_dener(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.result_sonrasi_kopar = 1                                    # hosting kaydetti, cevap istemciye ulaşmadı
    A.kalici_tur(ayar)
    assert {x["durum"] for x in sorgu(depo, "SELECT durum FROM giden")} == {"bekliyor"} and len(h.outbound) == 2
    A.kalici_tur(ayar)                                            # yeniden dene → "işlenmekte değil" → giden_durum: satırlar orada
    assert {x["durum"] for x in sorgu(depo, "SELECT durum FROM giden")} == {"hostingte"}
    assert len(h.outbound) == 2 and h.cagri.count("result") == 2 and "giden_durum" in h.cagri


def test_ajan_ayni_kanal_mesaji_yeniden_gelince_ikinci_is_acmaz(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    h.yeniden_sirala(g["id"])                                     # aynı kanal mesajı yeniden kuyrukta
    A.kalici_tur(ayar)
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1 and tek(depo, "SELECT count(*) n FROM mesajlar")["n"] == 1
    assert len(h.outbound) == 2 and h.inbound[g["id"]]["state"] == "done"
    assert h.inbound[g["id"]]["result"]["eylem"] == "yoksay"


def test_ajan_ilk_is_surerken_ayni_mesaj_gelirse_satir_ilk_isle_kapanir(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001)
    depo.mesaj_kaydet(g); h.mesaj_gelir(g)                        # ör. geçişte Postgres'e alınmış, hosting'te de kuyrukta
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1
    assert h.inbound[g["id"]]["state"] == "done" and len(h.outbound) == 2 and h.inbound[g["id"]]["result"]["eylem"] == "is_emri"


def test_ajan_yeniden_baslayinca_olu_surecin_isini_hemen_alir(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    h.claim()                                                     # eski süreç hosting'ten aldı …
    depo.mesaj_kaydet(g)
    depo.is_al(f"{socket.gethostname()}:999999", kira_sn=300)    # … Postgres'te kiraladı ve öldü
    assert A.kalici_hazir(h.settings()) is None                   # yeni süreç: ölü kirayı düşürür
    A.kalici_tur(ayar)
    j = tek(depo, "SELECT durum, deneme FROM isler")
    assert (j["durum"], j["deneme"]) == ("bitti", 2) and h.inbound[g["id"]]["state"] == "done"


def test_ajan_hosting_satiri_birakmissa_satirlar_gonderilmedi(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.claim(); depo.mesaj_kaydet(g)
    h.inbound[g["id"]]["state"] = "failed"                        # hosting 600 sn sonra "takılı" saydı
    A._kalici["K"].bir_is(depo, {**ayar, "kira_sn": 300}, "A")
    A.hostinge_teslim(depo)
    assert {x["durum"] for x in sorgu(depo, "SELECT durum FROM giden")} == {"gonderilmedi"} and not h.outbound
    assert "hosting kabul etmedi" in tek(depo, "SELECT hata FROM giden LIMIT 1")["hata"]


def test_ajan_eski_hosting_apisiyle_ya_da_eksik_gocle_calismaz(ajan, depo):
    A, h, ayar = ajan
    h.api = "kanal-api-v1.1"
    assert "kanal-api-v1.2 gerekli" in A.kalici_hazir(h.settings())
    h.api = "kanal-api-v1.2"
    with depo.baglan() as c:
        c.execute("DELETE FROM sema_surumu WHERE surum = 2")
    assert "göçü uygulanmamış: [2]" in A.kalici_hazir(h.settings())


def test_kanit_sorgulari_calisir_ve_numara_yazmaz(depo, hizli_motor):
    """vps/kanit_sorgulari.sql: canlıda salt okunur kanıt için; SQL geçerli, telefon numarası maskeli."""
    import shutil, subprocess
    simdi = time.time()
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=simdi - 200)); isle_hepsi(depo)
    hosting_gonderdi(depo, kabul=simdi - 100, teslim=simdi - 90)
    depo.mesaj_kaydet(mesaj("onaylıyorum", T_ONAY, ts=simdi, context_id=_pdf_wamid(depo, 1))); isle_hepsi(depo)
    r = subprocess.run([shutil.which("psql"), "-X", "-v", "ON_ERROR_STOP=1", "-d", depo.dsn, "-f", str(KOK / "vps" / "kanit_sorgulari.sql")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    assert "onaylandi" in r.stdout and "mesaj_basina_en_cok_is" in r.stdout and "meta_gonderdi" in r.stdout
    assert NUMARA_A not in r.stdout and NUMARA_A[:3] + "…" + NUMARA_A[-2:] in r.stdout
    assert "P6001 aynalı" not in r.stdout and "onaylıyorum" not in r.stdout          # mesaj metni yazılmaz


def test_canli_gosterim_provasi_sahte_hosting(ajan, depo, hizli_motor):
    """IE-02-canli.md kapı G'nin provası: aynı yedi adım, kayıtlı LLM çıkarımı ve sahte hosting ile. Canlı gösterimde LLM
    gerçek, hosting gerçek; burada gösterilen yalnız beklenen sonuçların ajan + Postgres + kural katmanında tuttuğudur."""
    import json as _j
    A, h, ayar = ajan
    A.kalici_hazir(h.settings())

    def gonder_ve_teslim():
        h.tick()
        for r in h.outbound.values():
            if r["state"] == "accepted" and r["kind"] == "document" and not r.get("delivery_events"):
                h.teslim(r["wamid"], "delivered", int(time.time()) - 2)

    # 1 · "P6001 aynalı olsun" → r01
    m1 = mesaj("P6001 aynalı olsun", T_P6001); h.mesaj_gelir(m1); A.kalici_tur(ayar); gonder_ve_teslim()
    pdf1 = next(r["wamid"] for r in h.outbound.values() if r["kind"] == "document")
    # 2 · belirsiz pencere sözü → B1 sorusu
    m2 = mesaj("yatak odası 1, 120x180", talep("revizyon", "yatak odası 1 penceresi 120x180",
                                               pencereler=[{"mahal": "Yatak Odası 1", "olcu": "120x180", "islem": None}]))
    h.mesaj_gelir(m2); A.kalici_tur(ayar); gonder_ve_teslim()
    s = tek(depo, "SELECT * FROM sorular WHERE durum = 'acik'")
    assert (s["alan"], s["kaynak_mesaj_id"]) == ("pencere_islem", m2["id"])
    # 3 · servis yeniden başlatılır (yeni süreç: bellekteki her şey gider)
    A._kalici.update(depo=None, K=None, son_esitleme=0.0)
    assert A.kalici_hazir(h.settings()) is None
    # 4 · "değiştir" → soruya bağlanır, aynı projede r02
    m4 = mesaj("değiştir", talep("diger", "değiştir")); h.mesaj_gelir(m4); A.kalici_tur(ayar); gonder_ve_teslim()
    assert tek(depo, "SELECT durum, cevap_mesaj_id FROM sorular") == {"durum": "cevaplandi", "cevap_mesaj_id": m4["id"]}
    r01, r02 = sorgu(depo, "SELECT * FROM revizyonlar ORDER BY rev")
    assert (r02["rev"], r02["proje_id"], r02["kaynak_mesaj_id"]) == (2, r01["proje_id"], m4["id"])
    pdf2 = next(r["wamid"] for r in h.outbound.values() if r["kind"] == "document" and r["wamid"] != pdf1)
    # 5 · r01'i alıntılayan onay → reddedilir (dönemsel eşitleme beklenmeden: işlemeden önce eşitlenir)
    A._kalici["son_esitleme"] = time.time()
    m5 = mesaj("onaylıyorum", T_ONAY, context_id=pdf1); h.mesaj_gelir(m5); A.kalici_tur(ayar)
    assert "alıntı başka revizyona ait" in tek(depo, "SELECT sonuc->>'gerekce' AS g FROM isler WHERE mesaj_id = %s", m5["id"])["g"]
    # 6 · r02'yi alıntılayan onay → kabul
    A._kalici["son_esitleme"] = time.time()
    m6 = mesaj("onaylıyorum", T_ONAY, context_id=pdf2); h.mesaj_gelir(m6); A.kalici_tur(ayar)
    o = tek(depo, "SELECT sonuc->'onay' AS o FROM isler WHERE mesaj_id = %s", m6["id"])["o"]
    assert (o["kabul"], o["rev"], o["sinir"], o["pdf_wamid"]) == (True, 2, "teslim", pdf2)
    assert [(x["rev"], x["durum"]) for x in sorgu(depo, "SELECT rev, durum FROM revizyonlar ORDER BY rev")] == [(1, "yerini_aldi"), (2, "onaylandi")]
    # 7 · aynı kanal mesajı yeniden → ikinci iş yok
    n = len(h.outbound)
    h.yeniden_sirala(m1["id"]); A.kalici_tur(ayar)
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 5 and len(h.outbound) == n      # beş mesaj, beş iş
    assert tek(depo, "SELECT max(n) m FROM (SELECT count(*) n FROM isler GROUP BY mesaj_id) k")["m"] == 1
    # bayiye giden metinler (sahte hosting'in gönderdiği sırayla)
    metinler = [r["body"] for r in sorted(h.outbound.values(), key=lambda r: (r["created_at"], r["seq"])) if r["kind"] == "text"]
    assert any("zaten bir pencere var" in t for t in metinler) and any("güncel plan" in t for t in metinler)
    assert any("Onayınız kaydedildi" in t and "revizyon 2" in t for t in metinler)


def test_tekrar_dene_betigi_ikinci_is_acmaz(depo, hizli_motor):
    import subprocess
    g = mesaj("P6001 aynalı", T_P6001); depo.mesaj_kaydet(g); isle_hepsi(depo)
    env = {**os.environ, "PORTMAN_PG_DSN": depo.dsn}
    r = subprocess.run([sys.executable, str(KOK / "vps" / "tekrar_dene.py"), g["id"][:16]], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[-500:]
    assert "yeni iş açıldı mı: hayır" in r.stdout and "iş sayısı: 1" in r.stdout
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1
