"""İE-02 · ajanın hosting'e devri ve eşitleme (dördüncü bağımsız incelemenin bulguları, 28.09).

Ajan (vps/agent.py) SAHTE hosting API'sine bağlıdır (sahte_hosting.py: 600 sn'lik süpürme, hata enjeksiyonu). Bu, ajanın
Python tarafını sınar; gerçek PHP hattını DOĞRULAMAZ (kanal/tests/baglanti_test.php, e2e_kalici.py; portman/lib.php gerekir).

  1. Postgres kapalıyken hosting'ten mesaj alınmaz; alınıp yazılamayan mesaj diske alınır ve kaybolmaz.
  2. Bekleyen cevaplar claim'den (hosting'in süpürmesinden) önce verilir; D-03'ün üç denemesi ve tükenme bildirimi hosting'in
     600 sn'si içinde kalır; başarısız işin bildirimi de hosting'e verilir.
  3. Yalnız bilinen kesin hatalar kesindir; 401, 5xx ve geçici 422 yeniden denenir, süre sınırıyla.
  4. worker=off iken ajan iş almaz, açık işleri bitirir (boşaltma); worker=hosting iken hiçbir şey yapmaz. Yeniden giriş
     yalnız boş veritabanına aktarılır.
  6. Eşitleme: belirsiz satır sonradan kabul görürse işlenir; en yeni satırlar önce; Meta saati (sent/delivered) önce gelir;
     onay sınırdan sonra (aynı saniye değil) yazılmış olmalı; hosting durumlarının her biri.
  7. Tekrar gelen mesaj, ilk işin hosting'e verilemeyen satırlarını yeniden verir; PDF kayıttan sonra değiştiyse verilmez.
"""
from __future__ import annotations

import json
import re
import socket
import time

import psycopg
import pytest

from conftest import AYAR, KOK, NUMARA_A, mesaj, sorgu, talep, tek
from test_kalici import T_ONAY, T_P6001, isle_hepsi

import worker as W


def _durumlar(depo, is_id=None) -> dict:
    q = "SELECT kind, durum FROM giden" + (" WHERE is_id = %s" if is_id else "") + " ORDER BY sira"
    return {r["kind"]: r["durum"] for r in sorgu(depo, q, *([is_id] if is_id else []))}


# ───────────────────────── 1. Postgres kesintisi ─────────────────────────
def test_postgres_kapaliyken_hostingten_mesaj_alinmaz(ajan, depo, hizli_motor, monkeypatch):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    assert A.kalici_hazir(h.settings()) is None
    d = A._kalici["depo"]
    monkeypatch.setattr(d, "saglik", lambda: (_ for _ in ()).throw(psycopg.OperationalError("bağlantı reddedildi")))
    with pytest.raises(psycopg.OperationalError):
        A.kalici_tur(ayar)
    assert "claim" not in h.cagri and h.inbound[g["id"]]["state"] == "queued"


def test_alinip_postgrese_yazilamayan_mesaj_diske_alinir_sonra_islenir(ajan, depo, hizli_motor, monkeypatch):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    d = A._kalici["depo"]
    asil = d.mesaj_kaydet
    monkeypatch.setattr(d, "mesaj_kaydet", lambda job: (_ for _ in ()).throw(psycopg.OperationalError("yeniden başlıyor")))
    with pytest.raises(psycopg.OperationalError):
        A.kalici_tur(ayar)                                        # claim oldu, yazma olmadı
    assert h.inbound[g["id"]]["state"] == "processing" and tek(depo, "SELECT count(*) n FROM mesajlar")["n"] == 0
    assert len(list((W.KANAL / "kalici_bekleyen").glob("*.json"))) == 1
    t_al = time.time()
    assert any("Postgres'e yazılmayı bekliyor" in u for u in A.kalici_uyarilari())
    monkeypatch.setattr(d, "mesaj_kaydet", asil)
    time.sleep(0.5)
    A.kalici_tur(ayar)                                            # Postgres döndü: diskteki mesaj yazılır ve işlenir
    assert tek(depo, "SELECT durum FROM isler WHERE mesaj_id = %s", g["id"])["durum"] == "bitti"
    r = tek(depo, "SELECT (ham->>'_ajan_aldi')::float8 AS aldi, extract(epoch FROM alindi) AS yazildi FROM mesajlar")
    assert r["aldi"] <= t_al < float(r["yazildi"])                # hosting'ten alınma anı, Postgres'e yazılma değil
    assert h.inbound[g["id"]]["state"] == "done" and len(h.outbound) == 2
    assert not list((W.KANAL / "kalici_bekleyen").glob("*.json"))


# ───────────────────────── 2. hosting'in 600 sn'si ─────────────────────────
def test_uzun_kesintiden_sonra_bekleyen_cevap_supurmeden_once_verilir(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(503, {"error": "bakım"})]; h.hatalar["settings"] = [(503, {"error": "bakım"})]   # hosting kapalı
    A.kalici_tur(ayar)                                            # iş bitti, hosting'e verilemedi
    assert set(_durumlar(depo).values()) == {"bekliyor"} and not A._kalici["devir"]          # ulaşılamıyor: aralık yok
    h.kayma = 700                                                 # 10 dakikadan uzun kesinti; hosting süpürmedi (claim yoktu)
    n0 = len(h.cagri)
    A.kalici_tur(ayar)                                            # önce teslim, sonra claim (süpürme)
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.inbound[g["id"]]["state"] == "done"
    tur = h.cagri[n0:]
    assert tur.index("result") < tur.index("claim")


def test_d03_kira_ve_deneme_hosting_takili_suresine_sigar(ajan):
    A, h, ayar = ajan
    stale = int(re.search(r"const PM_KANAL_STALE = (\d+);", (KOK / "kanal" / "feature.php").read_text()).group(1))
    assert A.HOSTING_TAKILI_SN == stale == h.STALE
    assert 3 * A.KIRA_SN + 60 < stale                              # üçüncü denemenin sonu ve tükenme bildirimi için pay
    # devir sınırlarının yönü: son deneme süpürmeden önce başlar; "süpürüldü" kabulü süpürmeden sonra
    assert 3 * A.KIRA_SN < stale - A.RISK_PAYI_SN < stale < stale + A.SUPURME_PAYI_SN and A.SUPURME_PAYI_SN >= 30


def test_d03_tukenen_isin_bildirimi_hostinge_verilir(ajan, depo, hizli_motor):
    """Üç denemede de süreç düştü: iş başarısız sayılır, bayiye ve Patron'a bildirim hosting'e verilir (hosting henüz
    vazgeçmeden: üç kira süresi + pay)."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.claim(); depo.mesaj_kaydet(g)
    with depo.baglan() as c:
        c.execute("UPDATE isler SET durum = 'isleniyor', deneme = 3, sahip = 'baska-makine:1', kira_bitis = now() - interval '1 second'")
    h.kayma = 3 * A.KIRA_SN + 30
    A.kalici_tur(ayar)
    j = tek(depo, "SELECT durum, deneme FROM isler")
    assert (j["durum"], j["deneme"]) == ("basarisiz", 3)
    assert sorted(r["to"] for r in h.outbound.values()) == sorted([NUMARA_A, "PATRON"])
    assert h.inbound[g["id"]]["state"] == "failed" and set(_durumlar(depo).values()) == {"hostingte"}


def test_basarisiz_isin_bildirimi_hostinge_verilir(ajan, depo, monkeypatch):
    A, h, ayar = ajan
    monkeypatch.setattr(W, "isle", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("beklenmeyen")))
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    assert tek(depo, "SELECT durum FROM isler")["durum"] == "basarisiz"
    assert sorted(r["to"] for r in h.outbound.values()) == sorted([NUMARA_A, "PATRON"]) and h.inbound[g["id"]]["state"] == "failed"


# ───────────────────────── 3. hata sınıfları ─────────────────────────
@pytest.mark.parametrize("kod, hata", [(401, "unauthorized"), (403, "forbidden"), (500, "sunucu"), (429, "yavaş"), (503, "bakım")])
def test_hostinge_ulasilamiyorsa_sonraki_turda_hemen_yeniden_denenir(ajan, depo, hizli_motor, kod, hata):
    """Hata bütün isteklerde (ör. anahtar yenilenirken 401): hosting'e ulaşılamıyor sayılır; sonuç atılmaz, sonraki turda
    beklemeden yeniden denenir."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(kod, {"error": hata})]; h.hatalar["settings"] = [(kod, {"error": hata})]
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"bekliyor"} and not A._kalici["devir"]
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.inbound[g["id"]]["state"] == "done"


@pytest.mark.parametrize("kod, hata", [(403, "forbidden"), (500, "sunucu"), (422, "file_write"), (422, "kanal_state_lock"),
                                       (422, "document_file_missing"), (422, "bad_result")])
def test_ise_ozgu_hata_araliklarla_yeniden_denenir(ajan, depo, hizli_motor, kod, hata):
    """Hosting ulaşılabilir ama bu işin sonucunu almıyor: sonuç atılmaz; iş aralıkla (30 sn'den başlayarak) yeniden denenir,
    her turda değil."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(kod, {"error": hata})] * 50
    for _ in range(5):
        A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"bekliyor"} and h.cagri.count("result") == 1
    is_id = tek(depo, "SELECT id FROM isler")["id"]
    assert A._kalici["devir"][is_id]["n"] == 1 and A._kalici["devir"][is_id]["sonraki"] > time.time() + 20
    h.hatalar["result"] = []; A._kalici["devir"][is_id]["sonraki"] = 0      # süre doldu, hosting düzeldi
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"hostingte"} and is_id not in A._kalici["devir"]


@pytest.mark.parametrize("kod, hata", [(422, "bad_path"), (422, "pdf_invalid"), (422, "row_inbound_mismatch"), (413, "too large")])
def test_kesin_hosting_hatasi_gonderilmedi_ve_uyari(ajan, depo, hizli_motor, kod, hata):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(kod, {"error": hata})]
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"gonderilmedi"} and not h.outbound
    assert any("2 giden satır gönderilmedi" in u for u in A.kalici_uyarilari())


def test_gecici_hata_uzasa_da_vazgecilmez_uyari_verilir(ajan, depo, hizli_motor):
    """Hosting uzun süre yazamıyor (ör. disk kotası: result 422 file_write, claim de başarısız; settings okunuyor). Hosting'teki
    satır teslim alınabilir durumda kaldığı sürece ajan cevabı atmaz; mesaj alınalı 480 sn olunca bekleme yok sayılır (her
    turda denenir); uzayan devir uyarıya düşer; hosting düzelince cevap verilir."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(422, {"error": "file_write"})] * 2
    A.kalici_tur(ayar)                                            # iş bitti, sonuç verilemedi (işe özgü: aralıkla)
    with depo.baglan() as c:                                      # 700 sn geçti (hosting ve ajan saati birlikte)
        c.execute("UPDATE isler SET bitti = now() - interval '20 minutes'")
        c.execute("UPDATE mesajlar SET ham = jsonb_set(ham, '{_ajan_aldi}', to_jsonb(extract(epoch FROM now()) - 700))")
    A._kalici["son_claim"] = 0; h.kayma = 700                     # o zamandan beri başarılı claim yok: hosting süpürmedi
    h.hatalar["claim"] = [(422, {"error": "kanal_state_lock"})]
    with pytest.raises(Exception):
        A.kalici_tur(ayar)                                        # aralık yok sayılır (480 sn+): denendi, olmadı; claim de olmadı
    assert set(_durumlar(depo).values()) == {"bekliyor"}
    assert any("dakikadan uzun süredir hosting'e verilemiyor" in u for u in A.kalici_uyarilari())
    A.kalici_tur(ayar)                                            # hosting düzeldi: sonuç claim'den (süpürmeden) önce verilir
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.inbound[g["id"]]["state"] == "done"
    assert h.cagri.count("result") == 3


def test_baglanti_kopmasi_ise_ozguyse_otekiler_verilir(ajan, depo, hizli_motor):
    """Büyük gövdede sunucunun erken reddi istemciye bağlantı kopması olarak gelir. Hosting'e ulaşılabildiği için hata o
    işe özgü sayılır; öteki iş aynı turda verilir, kopan iş aralıkla yeniden denenir."""
    A, h, ayar = ajan
    g1 = mesaj("P6001 aynalı", T_P6001); g2 = mesaj("P6001 aynalı", T_P6001, numara="900000000303")
    for g in (g1, g2):
        h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    for g in (g1, g2):
        h.claim(); depo.mesaj_kaydet(g)
    isle_hepsi(depo)
    h.kopar["result"] = 1
    A.hostinge_teslim(A._kalici["depo"])
    d = {r["mesaj_id"]: r["durum"] for r in sorgu(depo, "SELECT DISTINCT mesaj_id, durum FROM giden")}
    assert d == {g1["id"]: "bekliyor", g2["id"]: "hostingte"} and len(A._kalici["devir"]) == 1


def test_supurulmus_satirin_sonucu_mutabakatla_kapanir(ajan, depo, hizli_motor):
    """İşe özgü hata sürüyor (ör. bad_result, satır durumundan önce denetlenir) ve mesaj alındıktan 660 sn sonra başarılı bir
    claim oldu: hosting satırı süpürmüştür. Ajan artık istek atmaz; giden_durum ile bakar, satırlar orada değilse
    'gonderilmedi' (uyarıya düşer). Aynı sonuç hosting'e önceden ulaşmışsa 'hostingte'."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(422, {"error": "bad_result"})] * 50
    A.kalici_tur(ayar)
    with depo.baglan() as c:
        c.execute("UPDATE mesajlar SET ham = jsonb_set(ham, '{_ajan_aldi}', to_jsonb(extract(epoch FROM now()) - 700))")
    n = h.cagri.count("result")
    A.kalici_tur(ayar)                                            # önceki turdaki claim, alındıktan 660 sn sonra: süpürülmüş
    assert set(_durumlar(depo).values()) == {"gonderilmedi"} and "süpürüldü" in tek(depo, "SELECT hata FROM giden LIMIT 1")["hata"]
    assert h.cagri.count("result") == n and "giden_durum" in h.cagri              # istek atılmadı, hosting'e soruldu


def test_supurme_denetimi_hostinge_sorar_cevap_oraya_ulasmissa_kabul(ajan, depo, hizli_motor):
    """Sonuç hosting'e ulaştı ama cevabı kayboldu (bağlantı koptu); hosting ulaşılabilir olduğu için iş aralıkla bekliyor.
    Mesaj alınalı 660 sn'den çok olunca ajan satırı 'süpürüldü' sanıp atmaz: giden_durum'a sorar, satırlar oradaysa
    'hostingte'."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.result_sonrasi_kopar = 1
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"bekliyor"} and len(h.outbound) == 2
    with depo.baglan() as c:
        c.execute("UPDATE mesajlar SET ham = jsonb_set(ham, '{_ajan_aldi}', to_jsonb(extract(epoch FROM now()) - 700))")
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.cagri.count("result") == 1


def test_uzun_sure_sonra_yeniden_kuyruga_konan_mesajin_cevabi_verilir(ajan, depo, hizli_motor):
    """Cevap hosting'e verilemedi ve satır süpürüldü; yönetici mesajı çok sonra (660 sn'den uzun) kuyruğa geri koydu. Yeni
    alımla hosting'teki süre yeniden başlar: cevap 'süpürüldü' sayılmadan verilir."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.claim(); depo.mesaj_kaydet(g)
    h.inbound[g["id"]]["state"] = "failed"
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"gonderilmedi"}
    with depo.baglan() as c:
        c.execute("UPDATE mesajlar SET ham = jsonb_set(ham, '{_ajan_aldi}', to_jsonb(extract(epoch FROM now()) - 2000))")
    h.yeniden_sirala(g["id"]); A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.inbound[g["id"]]["result"]["eylem"] == "is_emri"


def test_bekleyen_isler_yeni_isi_bekletmez(ajan, depo, hizli_motor):
    """Aralıkla bekleyen çok sayıda iş varken yeni biten iş aynı turda denenir (aday listesine takılmaz)."""
    A, h, ayar = ajan
    A.kalici_hazir(h.settings())
    with depo.baglan() as c:
        for i in range(60):
            mid = f"wamid.ESKI{i:03d}"
            c.execute("INSERT INTO mesajlar (id, gonderen, tur, wa_zamani, ham) VALUES (%s, %s, 'text', now(), '{}')", (mid, NUMARA_A))
            j = c.execute("INSERT INTO isler (mesaj_id, gonderen, durum, bitti) VALUES (%s, %s, 'bitti', now()) RETURNING id",
                          (mid, NUMARA_A)).fetchone()["id"]
            c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, satir) VALUES (%s, %s, %s, 1, %s, "
                      "'cevap', 'text', 'x', '{}')", (f"out_eski{i:03d}", j, mid, NUMARA_A))
            A._kalici["devir"][j] = {"n": 3, "sonraki": time.time() + 300}
    g = mesaj("P6001 aynalı", T_P6001, numara="900000000303"); h.mesaj_gelir(g)
    A.kalici_tur(ayar)
    assert h.inbound[g["id"]]["state"] == "done" and h.cagri.count("result") == 1


def test_gunluge_whatsapp_kimligi_yazilmaz(ajan, depo, hizli_motor, tmp_path):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    h.yeniden_sirala(g["id"]); A.kalici_tur(ayar)
    gunluk = (tmp_path / "logs" / "agent.log").read_text(encoding="utf-8")
    assert "iş alındı → Postgres" in gunluk and "tekrar gelen mesaj" in gunluk and "wamid." not in gunluk


def test_bir_isin_hatasi_otekinin_teslimini_bekletmez(ajan, depo, hizli_motor):
    """İki bitmiş iş; hosting birincisini (ör. WAF 403) reddediyor. İkincisi aynı turda verilir."""
    A, h, ayar = ajan
    g1 = mesaj("P6001 aynalı", T_P6001); g2 = mesaj("P6001 aynalı", T_P6001, numara="900000000303")
    for g in (g1, g2):
        h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    for g in (g1, g2):
        h.claim(); depo.mesaj_kaydet(g)
    isle_hepsi(depo)
    h.hatalar["result"] = [(403, {"error": "forbidden"})]
    A.hostinge_teslim(A._kalici["depo"])
    d = {r["mesaj_id"]: r["durum"] for r in sorgu(depo, "SELECT DISTINCT mesaj_id, durum FROM giden")}
    assert d == {g1["id"]: "bekliyor", g2["id"]: "hostingte"} and h.inbound[g2["id"]]["state"] == "done"


# ───────────────────────── 4. boşaltma ve yeniden giriş ─────────────────────────
def test_kalici_kip_tek_etkin_isleyici():
    import sys
    sys.path.insert(0, str(KOK / "vps"))
    import agent as A
    assert A.kalici_kip({"enabled": True, "worker": "vps"}) == "is_al"
    assert A.kalici_kip({"enabled": True, "worker": "off"}) == "bosalt"
    assert A.kalici_kip({"enabled": True, "worker": "hosting"}) is None
    assert A.kalici_kip({"enabled": False, "worker": "vps"}) is None


def test_worker_off_iken_ajan_is_almaz_acik_isi_bitirip_hostinge_verir(ajan, depo, hizli_motor, monkeypatch):
    """Geri dönüşün (kapı H) boşaltması: ajanın ana döngüsü (tek tur, ONESHOT) worker=off iken claim çağırmaz; Postgres'te
    açık kalan işi bitirir ve sonucunu hosting'e verir. Kuyruktaki yeni mesaj hosting'te bekler."""
    A, h, ayar = ajan
    g1 = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g1)
    h.claim(); depo.mesaj_kaydet(g1)                              # geçişten önce alınmış, Postgres'te açık
    g2 = mesaj("başka", T_P6001, numara="900000000303"); h.mesaj_gelir(g2)
    h.worker = "off"; h.cagri.clear()
    monkeypatch.setattr(A, "ONESHOT", True)
    monkeypatch.setattr(W, "bagimliliklar_hazir", lambda: False)  # öz-test bu testin konusu değil
    import signal
    eski = signal.getsignal(signal.SIGTERM)
    try:
        assert A.main() == 0
    finally:
        signal.signal(signal.SIGTERM, eski)
    assert "claim" not in h.cagri
    assert tek(depo, "SELECT durum FROM isler WHERE mesaj_id = %s", g1["id"])["durum"] == "bitti"
    assert h.inbound[g1["id"]]["state"] == "done" and h.inbound[g2["id"]]["state"] == "queued"
    assert tek(depo, "SELECT count(*) n FROM giden WHERE durum = 'bekliyor'")["n"] == 0


def test_yeniden_giris_yalniz_bos_veritabanina_aktarilir(depo, tmp_path):
    import depo_aktar
    kanal = tmp_path / "k"; (kanal / "durum").mkdir(parents=True)
    (kanal / "durum" / f"{NUMARA_A}.json").write_text(json.dumps({"asama": "bos"}), encoding="utf-8")
    assert depo_aktar.ice_aktar(depo, kanal, bos_olmali=True)["konusma"] == 1
    with pytest.raises(ValueError, match="boş değil"):
        depo_aktar.ice_aktar(depo, kanal, bos_olmali=True)


def test_canli_gecis_varsayilani_kuyruktakileri_is_yapmaz(depo, tmp_path):
    import depo_aktar
    kanal = tmp_path / "k"; (kanal / "durum").mkdir(parents=True)
    g = mesaj("P6001 aynalı", T_P6001); g["state"] = "queued"
    (kanal / "state.json").write_text(json.dumps({"inbound": {g["id"]: g}, "outbound": {}}), encoding="utf-8")
    assert depo_aktar.ice_aktar(depo, kanal)["kuyrukta_birakildi"] == 1
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 0


def test_olu_kira_yalniz_bu_makinedeki_surecler_icin_duser(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    for i, sahip in enumerate((f"{socket.gethostname()}:999999", "baska-makine:123")):
        depo.mesaj_kaydet(mesaj(f"m{i}", T_P6001, numara=f"90000000040{i}"))
    with depo.baglan() as c:
        c.execute("UPDATE isler SET durum = 'isleniyor', deneme = 1, kira_bitis = now() + interval '1 hour', "
                  "sahip = CASE WHEN id = (SELECT min(id) FROM isler) THEN %s ELSE %s END", (f"{socket.gethostname()}:999999", "baska-makine:123"))
    A.kalici_hazir(h.settings())
    k = {r["sahip"]: r["bitti_mi"] for r in sorgu(depo, "SELECT sahip, kira_bitis <= now() AS bitti_mi FROM isler")}
    assert k == {f"{socket.gethostname()}:999999": True, "baska-makine:123": False}


# ───────────────────────── 6. eşitleme ve onay sınırı ─────────────────────────
def test_belirsiz_satir_sonradan_kabul_gorurse_isler_ve_onay_kabul_edilir(ajan, depo, hizli_motor):
    """Hosting gönderimi 'uncertain' saydı; Meta'nın imzalı durum bildirimi sonradan satırı eşledi (wamid, delivered)."""
    A, h, ayar = ajan
    A.kalici_hazir(h.settings())
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g); A.kalici_tur(ayar)
    pdf = next(i for i, r in h.outbound.items() if r["kind"] == "document")
    h.tick(belirsiz={pdf})
    A._kalici["son_esitleme"] = 0; A.kalici_tur(ayar)
    assert _durumlar(depo)["document"] == "belirsiz"
    t = int(time.time()) - 5
    h.outbound[pdf].update(state="delivered", wamid="wamid.GEC0001", request_accepted_at=t + 3,
                           delivery_state="delivered", delivery_events={"a": {"status": "sent", "timestamp": t - 1},
                                                                        "b": {"status": "delivered", "timestamp": t}})
    A._kalici["son_esitleme"] = 0; A.kalici_tur(ayar)
    s = tek(depo, "SELECT durum, dis_id, teslim_durumu FROM giden WHERE kind = 'document'")
    assert (s["durum"], s["dis_id"], s["teslim_durumu"]) == ("kabul_edildi", "wamid.GEC0001", "delivered")
    o = mesaj("onaylıyorum", T_ONAY, context_id="wamid.GEC0001"); h.mesaj_gelir(o); A.kalici_tur(ayar)
    assert tek(depo, "SELECT sonuc->'onay'->>'kabul' AS k FROM isler WHERE mesaj_id = %s", o["id"])["k"] == "true"


def test_onaydan_once_durum_eslenir(ajan, depo, hizli_motor):
    """PDF hosting'e verildikten sonra gönderildi ve teslim edildi; son eşitleme bundan önceydi. Bayi hemen onayladı: iş
    işlenmeden önce eşitleme yapılır, onay teslimden sonra yazıldığı görülür ve kabul edilir."""
    A, h, ayar = ajan
    A.kalici_hazir(h.settings())
    g = mesaj("P6001 aynalı", T_P6001, ts=time.time() - 60); h.mesaj_gelir(g); A.kalici_tur(ayar)
    assert _durumlar(depo)["document"] == "hostingte"
    h.tick()
    pdf = next(r for r in h.outbound.values() if r["kind"] == "document")
    h.teslim(pdf["wamid"], "delivered", int(time.time()) - 10)
    A._kalici["son_esitleme"] = time.time()                       # dönemsel eşitleme bu turda sıra beklemesin
    o = mesaj("onaylıyorum", T_ONAY, context_id=pdf["wamid"]); h.mesaj_gelir(o); A.kalici_tur(ayar)
    onay = tek(depo, "SELECT sonuc->'onay' AS o FROM isler WHERE mesaj_id = %s", o["id"])["o"]
    assert (onay["kabul"], onay["sinir"]) == (True, "teslim")


def _plan_ve_gonderim(depo, st: dict, ts_plan: float) -> str:
    depo.mesaj_kaydet(mesaj("P6001 aynalı", T_P6001, ts=ts_plan)); isle_hepsi(depo)
    ids = [r["id"] for r in sorgu(depo, "SELECT id FROM giden WHERE durum = 'bekliyor'")]
    depo.hostinge_verildi(ids)
    pdf = tek(depo, "SELECT id FROM giden WHERE kind = 'document'")["id"]
    depo.hosting_durumu_isle(pdf, {"wamid": "wamid.P" + pdf[-8:], **st})
    return "wamid.P" + pdf[-8:]


def test_meta_gonderim_ani_hosting_saatinden_once_gelir(depo, hizli_motor):
    """Teslim bildirimi yok; Meta 'sent' dedi. Hosting'in saati 5 sn ileride (kabul anı Meta'nın 'sent' anından sonra
    görünüyor). Bayi 'sent'ten 3 sn sonra onayladı: Meta saatine göre kabul edilir."""
    t = int(time.time()) - 100
    w = _plan_ve_gonderim(depo, {"state": "sent", "request_accepted_at": t + 5, "sent_at": t, "delivery_state": "sent"}, t - 50)
    o = mesaj("onaylıyorum", T_ONAY, ts=t + 3, context_id=w); depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    onay = tek(depo, "SELECT sonuc->'onay' AS o FROM isler WHERE mesaj_id = %s", o["id"])["o"]
    assert r["gerekce"] == "plan onaylandı" and (onay["kabul"], onay["sinir"]) == (True, "gonderildi")


@pytest.mark.parametrize("fark, kabul", [(0, False), (1, True)])
def test_onay_siniri_ayni_saniyeyi_kabul_etmez(depo, hizli_motor, fark, kabul):
    t = int(time.time()) - 100
    w = _plan_ve_gonderim(depo, {"state": "delivered", "request_accepted_at": t - 2, "sent_at": t - 1, "delivery_state": "delivered",
                                 "delivered_at": t}, t - 50)
    o = mesaj("onaylıyorum", T_ONAY, ts=t + fark, context_id=w); depo.mesaj_kaydet(o)
    isle_hepsi(depo)
    assert tek(depo, "SELECT sonuc->'onay'->>'kabul' AS k FROM isler WHERE mesaj_id = %s", o["id"])["k"] == str(kabul).lower()


def test_esitleme_en_yeni_satirlari_alir(depo):
    with depo.baglan() as c:
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, wa_zamani, ham) VALUES ('wamid.E', %s, 'text', now(), '{}')", (NUMARA_A,))
        j = c.execute("INSERT INTO isler (mesaj_id, gonderen, durum) VALUES ('wamid.E', %s, 'bitti') RETURNING id", (NUMARA_A,)).fetchone()["id"]
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum, hostinge_verildi, olusturuldu) "
                  "SELECT 'out_eski' || i, %s, 'wamid.E', i, %s, 'cevap', 'document', '', 'kabul_edildi', now(), now() - interval '1 day' "
                  "FROM generate_series(1, 250) i", (j, NUMARA_A))
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum, hostinge_verildi) VALUES "
                  "('out_yeni', %s, 'wamid.E', 900, %s, 'cevap', 'document', '', 'hostingte', now()), "
                  "('out_metin', %s, 'wamid.E', 901, %s, 'cevap', 'text', '', 'kabul_edildi', now()), "
                  "('out_belirsiz', %s, 'wamid.E', 902, %s, 'cevap', 'text', '', 'belirsiz', now())", (j, NUMARA_A) * 3)
    ids = depo.esitlenecek_satirlar()
    assert len(ids) == 200 and {"out_yeni", "out_belirsiz", "out_metin"} <= set(ids)


def _hosting_satiri(depo, kind="document") -> str:
    with depo.baglan() as c:
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, wa_zamani, ham) VALUES ('wamid.H', %s, 'text', now(), '{}') "
                  "ON CONFLICT DO NOTHING", (NUMARA_A,))
        j = c.execute("INSERT INTO isler (mesaj_id, gonderen, durum) VALUES ('wamid.H', %s, 'bitti') ON CONFLICT DO NOTHING RETURNING id",
                      (NUMARA_A,)).fetchone()
        j = j["id"] if j else c.execute("SELECT id FROM isler").fetchone()["id"]
        sid = f"out_{kind}{time.time_ns()}"
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum, hostinge_verildi) "
                  "VALUES (%s, %s, 'wamid.H', 1, %s, 'cevap', %s, '', 'hostingte', now())", (sid, j, NUMARA_A, kind))
    return sid


@pytest.mark.parametrize("kind, st, beklenen", [
    ("document", {"state": "uncertain", "error": "belirsiz"}, "belirsiz"),
    ("document", {"state": "held", "error": "reply_window_closed"}, "gonderilmedi"),
    ("document", {"state": "upload_failed", "attempts": 1}, "hostingte"),        # hosting PDF'i bir kez daha dener
    ("document", {"state": "upload_failed", "attempts": 2}, "gonderilmedi"),
    ("text", {"state": "upload_failed", "attempts": 0}, "gonderilmedi"),         # metin yeniden denenmez
    ("document", {"state": "sending", "attempts": 1}, "hostingte"),
])
def test_hosting_durumlari(depo, kind, st, beklenen):
    sid = _hosting_satiri(depo, kind)
    depo.hosting_durumu_isle(sid, st)
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", sid)["durum"] == beklenen


def test_teslim_durumu_geri_gitmez_ilk_teslim_ani_kalir(depo):
    sid = _hosting_satiri(depo)
    t = int(time.time()) - 100
    depo.hosting_durumu_isle(sid, {"state": "delivered", "wamid": "wamid.X", "request_accepted_at": t, "sent_at": t + 1,
                                   "delivery_state": "delivered", "delivered_at": t + 5})
    depo.hosting_durumu_isle(sid, {"state": "sent", "wamid": "wamid.X", "request_accepted_at": t, "sent_at": t + 3,
                                   "delivery_state": "sent", "delivered_at": None})
    assert tek(depo, "SELECT teslim_durumu FROM giden WHERE id = %s", sid)["teslim_durumu"] == "delivered"   # geç gelen 'sent' geri almaz
    depo.hosting_durumu_isle(sid, {"state": "read", "wamid": "wamid.X", "request_accepted_at": t, "sent_at": t + 1,
                                   "delivery_state": "read", "delivered_at": t + 9})
    r = tek(depo, "SELECT teslim_durumu, extract(epoch FROM teslim_zamani)::int AS tz, extract(epoch FROM gonderildi_zamani)::int AS gz "
                  "FROM giden WHERE id = %s", sid)
    assert (r["teslim_durumu"], r["tz"], r["gz"]) == ("read", t + 5, t + 1)


# ───────────────────────── 7. tekrar gelen mesaj ve PDF bütünlüğü ─────────────────────────
def test_tekrar_gelen_mesaj_verilemeyen_cevabi_yeniden_verir(ajan, depo, hizli_motor):
    """İlk işin cevabı hosting'e verilemedi (hosting satırı 'takılı' saymıştı). Yönetici mesajı kuyruğa geri koydu: ikinci iş
    açılmaz, ilk işin cevabı bu alımla verilir; bayi cevabını alır."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.claim(); depo.mesaj_kaydet(g)
    h.inbound[g["id"]]["state"] = "failed"
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"gonderilmedi"} and not h.outbound
    h.yeniden_sirala(g["id"])
    A.kalici_tur(ayar)
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1
    assert set(_durumlar(depo).values()) == {"hostingte"} and len(h.outbound) == 2 and h.inbound[g["id"]]["result"]["eylem"] == "is_emri"


def test_tekrar_gelen_mesaj_teslimi_bekleyen_cevabi_bu_alimla_verir(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(503, {"error": "bakım"})]
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"bekliyor"} and A._kalici["devir"]                   # işe özgü: aralıkla
    h.yeniden_sirala(g["id"])                                     # ör. yönetici hosting'te yeniden kuyruğa koydu
    A.kalici_tur(ayar)
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.inbound[g["id"]]["result"]["eylem"] == "is_emri"


def test_tekrar_gelen_mesaj_hostingin_tuttugu_satiri_yeniden_vermez(ajan, depo, hizli_motor):
    """Satırlar hosting'e verilmiş, hosting göndermemiş ('held': ör. 24 saat penceresi kapalı; sonradan da göndermez).
    Mesaj yeniden kuyruğa konsa da satırlar yeniden verilmez: hosting'teki kararın tekrarı değil, boş sonuçla kapanır."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    h.tick(tutulan=set(h.outbound))
    A._kalici["son_esitleme"] = 0; A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"gonderilmedi"}
    h.yeniden_sirala(g["id"]); A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"gonderilmedi"} and h.inbound[g["id"]]["result"]["eylem"] == "yoksay"
    assert h.cagri.count("result") == 2


def test_kayittan_sonra_degisen_pdf_hostinge_verilmez(ajan, depo, hizli_motor, monkeypatch):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    asil = A.hostinge_teslim
    cagri = {"n": 0}

    def ilk_turda_bozan(d):
        cagri["n"] += 1
        if cagri["n"] == 2:                                       # iş bittikten sonraki teslimden hemen önce
            yol = tek(depo, "SELECT dosya FROM giden WHERE kind = 'document'")["dosya"]
            with open(yol, "ab") as f:
                f.write(b"degisti")
        return asil(d)
    monkeypatch.setattr(A, "hostinge_teslim", ilk_turda_bozan)
    A.kalici_tur(ayar)
    assert _durumlar(depo) == {"text": "hostingte", "document": "gonderilmedi"}
    assert [r["kind"] for r in h.outbound.values()] == ["text"]


# ───────────────────────── beşinci inceleme ─────────────────────────
def test_nul_karakterli_mesaj_yazilir_kuyrugu_tikamaz(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001\x00 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    assert tek(depo, "SELECT metin FROM mesajlar")["metin"] == "P6001 aynalı" and h.inbound[g["id"]]["state"] == "done"


def test_postgrese_yazilamayan_mesaj_hatali_klasorune_alinir_ajan_surer(ajan, depo, hizli_motor, monkeypatch):
    A, h, ayar = ajan
    kotu = mesaj("x", T_P6001, numara="900000000303"); iyi = mesaj("P6001 aynalı", T_P6001)
    A.kalici_hazir(h.settings())
    d = A._kalici["depo"]; asil = d.mesaj_kaydet
    monkeypatch.setattr(d, "mesaj_kaydet", lambda job: (_ for _ in ()).throw(psycopg.errors.DataError("bozuk")) if job["id"] == kotu["id"] else asil(job))
    h.mesaj_gelir(kotu)
    A.kalici_tur(ayar)                                            # alındı, yazılamadı: diske (tur sürer)
    h.mesaj_gelir(iyi)
    A.kalici_tur(ayar)                                            # disktekini hatali/'ya alır, yeni mesajı alır ve işler
    assert not list((W.KANAL / "kalici_bekleyen").glob("*.json")) and len(list((W.KANAL / "kalici_bekleyen" / "hatali").glob("*.json"))) == 1
    assert h.inbound[iyi["id"]]["state"] == "done"
    assert any("veri hatası" in u for u in A.kalici_uyarilari())


def test_diskte_bekleyen_tekrar_mesajin_kapanisi_reddedilse_de_ajan_surer(ajan, depo, hizli_motor):
    """Diskte bekleyen mesaj Postgres'te zaten var ve bitmiş (ör. geri dönüş ve yeniden giriş arasında kalmış); hosting'teki
    satırı artık işlenmekte değil. Boş sonuçla kapatma 422 alır; bu bir engel değildir."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    A.bekleyene_yaz(h.inbound[g["id"]] | {"id": g["id"]})
    A.kalici_tur(ayar)
    assert not list((W.KANAL / "kalici_bekleyen").glob("*.json")) and tek(depo, "SELECT count(*) n FROM isler")["n"] == 1


def test_postgreste_acik_is_varken_yeni_mesaj_alinmaz(ajan, depo, hizli_motor, monkeypatch):
    A, h, ayar = ajan
    A.kalici_hazir(h.settings())
    K = A._kalici["K"]
    monkeypatch.setattr(K, "bir_is", lambda *a, **k: None)         # iş işlenemiyor (ör. durum okunamıyor)
    g1 = mesaj("P6001 aynalı", T_P6001); g2 = mesaj("başka", T_P6001, numara="900000000303")
    h.mesaj_gelir(g1); A.kalici_tur(ayar)
    h.mesaj_gelir(g2); A.kalici_tur(ayar)
    assert h.cagri.count("claim") == 1 and h.inbound[g2["id"]]["state"] == "queued"


def test_meta_metin_satirini_iletemediyse_uyari(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings()); A.kalici_tur(ayar)
    h.tick()
    metin = next(r for r in h.outbound.values() if r["kind"] == "text")
    A._kalici["son_esitleme"] = 0; A.kalici_tur(ayar)             # kabul edildi (henüz Meta bildirimi yok)
    h.teslim(metin["wamid"], "failed")
    A._kalici["son_esitleme"] = 0; A.kalici_tur(ayar)
    assert tek(depo, "SELECT teslim_durumu FROM giden WHERE kind = 'text'")["teslim_durumu"] == "failed"
    assert any("1 satırı Meta iletemedi" in u for u in A.kalici_uyarilari())


def test_hosting_mesaji_hic_bilmiyorsa_mutabakat(ajan, depo, hizli_motor):
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.claim(); depo.mesaj_kaydet(g)
    del h.inbound[g["id"]]                                        # hosting'in kaydında yok (inbound_unknown)
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"gonderilmedi"} and "giden_durum" in h.cagri


def test_tekrar_gelen_mesaj_basarisiz_isin_bildirimini_yeniden_verir(ajan, depo, monkeypatch):
    A, h, ayar = ajan
    monkeypatch.setattr(W, "isle", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("beklenmeyen")))
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.claim(); depo.mesaj_kaydet(g)
    h.inbound[g["id"]]["state"] = "failed"                        # hosting 'takılı' saymıştı
    A.kalici_tur(ayar)
    assert tek(depo, "SELECT durum FROM isler")["durum"] == "basarisiz" and set(_durumlar(depo).values()) == {"gonderilmedi"}
    h.yeniden_sirala(g["id"]); A.kalici_tur(ayar)
    assert sorted(r["to"] for r in h.outbound.values()) == sorted([NUMARA_A, "PATRON"])


def _ana_dongu_bir_sure(A, sn: float = 1.0):
    """Ajanın ana döngüsü (main) kısa bir süre koşar ve durdurulur (SIGTERM bayrağı)."""
    import signal
    import threading
    eski = signal.getsignal(signal.SIGTERM)
    zam = threading.Timer(sn, lambda: A._dur.__setitem__("istendi", True)); zam.start()
    try:
        return A.main()
    finally:
        zam.cancel(); A._dur["istendi"] = False; signal.signal(signal.SIGTERM, eski)


@pytest.mark.parametrize("isci, acik", [("hosting", True), ("vps", False)])
def test_ana_dongu_hosting_isliyorken_ya_da_kapaliyken_hicbir_sey_yapmaz(ajan, depo, hizli_motor, monkeypatch, isci, acik):
    A, h, ayar = ajan
    g1 = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g1)
    h.claim(); depo.mesaj_kaydet(g1)                              # Postgres'te açık iş
    g2 = mesaj("başka", T_P6001, numara="900000000303"); h.mesaj_gelir(g2)
    h.worker, h.enabled = isci, acik; h.cagri.clear()
    monkeypatch.setattr(W, "bagimliliklar_hazir", lambda: False)
    assert _ana_dongu_bir_sure(A) == 0
    assert "claim" not in h.cagri and "result" not in h.cagri and "giden_durum" not in h.cagri
    assert tek(depo, "SELECT durum FROM isler")["durum"] == "sirada" and h.inbound[g2["id"]]["state"] == "queued"


def test_ice_aktarma_komutu_dolu_veritabanina_aktarmaz(depo, tmp_path):
    kanal = tmp_path / "k"; (kanal / "durum").mkdir(parents=True)
    (kanal / "durum" / f"{NUMARA_A}.json").write_text(json.dumps({"asama": "bos"}), encoding="utf-8")
    import subprocess, sys
    komut = [sys.executable, str(KOK / "kanal" / "depo_aktar.py"), "ice", "--kanal", str(kanal)]
    env = {**__import__("os").environ, "PORTMAN_PG_DSN": depo.dsn}
    assert subprocess.run(komut, capture_output=True, text=True, env=env).returncode == 0
    r = subprocess.run(komut, capture_output=True, text=True, env=env)
    assert r.returncode != 0 and "boş değil" in r.stderr


def test_bosaltmada_acik_is_yokken_de_mesaj_alinmaz(ajan, depo, hizli_motor, monkeypatch):
    """worker=off, Postgres'te açık iş yok, hosting kuyruğunda mesaj var: ajan claim çağırmaz (hosting de vermezdi; ajan
    buna güvenmez)."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    h.worker = "off"; h.cagri.clear()
    monkeypatch.setattr(W, "bagimliliklar_hazir", lambda: False)
    assert _ana_dongu_bir_sure(A) == 0
    assert "settings" in h.cagri and "claim" not in h.cagri and h.inbound[g["id"]]["state"] == "queued"


def test_supurme_sinirindan_once_sonuc_denenir(ajan, depo, hizli_motor):
    """Mesaj 620 sn önce alındı; hosting'in süresi (600) dolmuş olabilir ama süpürüldüğü kesin değil (660 sn payı): ajan
    sonucu vermeyi dener, 'süpürüldü' saymaz."""
    A, h, ayar = ajan
    g = mesaj("P6001 aynalı", T_P6001); h.mesaj_gelir(g)
    A.kalici_hazir(h.settings())
    h.hatalar["result"] = [(500, {"error": "sunucu"})]
    A.kalici_tur(ayar)
    with depo.baglan() as c:
        c.execute("UPDATE mesajlar SET ham = jsonb_set(ham, '{_ajan_aldi}', to_jsonb(extract(epoch FROM now()) - 620))")
    A._kalici["son_claim"] = time.time()
    A.kalici_tur(ayar)
    assert set(_durumlar(depo).values()) == {"hostingte"} and h.cagri.count("result") == 2


def test_supurmeden_donen_claim_supurme_sayilmaz(ajan, depo, hizli_motor):
    """Ayarlar önbellekte hâlâ worker=vps iken hosting'te worker=off yapıldı: claim 'reason' ile süpürmeden döner; ajan bunu
    süpürme saymaz."""
    A, h, ayar = ajan
    A.kalici_hazir(h.settings())
    h.worker = "off"
    A.kalici_tur(ayar, is_al=True)
    assert "claim" in h.cagri and A._kalici["son_claim"] == 0
    h.worker = "vps"
    A.kalici_tur(ayar, is_al=True)
    assert A._kalici["son_claim"] > 0


def test_devir_uyarisi_zamanla_kaybolmaz(depo):
    with depo.baglan() as c:
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, wa_zamani, ham) VALUES ('wamid.D', %s, 'text', now(), '{}')", (NUMARA_A,))
        j = c.execute("INSERT INTO isler (mesaj_id, gonderen, durum, bitti) VALUES ('wamid.D', %s, 'bitti', now() - interval '25 hours') "
                      "RETURNING id", (NUMARA_A,)).fetchone()["id"]
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, olusturuldu) VALUES "
                  "('out_d', %s, 'wamid.D', 1, %s, 'cevap', 'text', 'x', now() - interval '25 hours')", (j, NUMARA_A))
    assert depo.gonderilemeyen_sayisi(24, 300)["devir_bekliyor"] == 1
