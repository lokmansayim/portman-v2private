"""İE-06 · kanal/webhook.py: hub doğrulaması, imza, yakalama kuralları (feature.php pm_kanal_capture ile aynı), kayıtsız gönderen,
durum bildirimleri (pm_kanal_status), medya kaydı, /saglik. WSGI uygulaması doğrudan çağrılır; gerçek Postgres; ağ, LLM, WhatsApp yok."""
from __future__ import annotations

import hashlib
import json
import time
from io import BytesIO

import pytest

from conftest import NUMARA_A, mesaj, sorgu, talep, tek

import kalici
import meta_api as M
import nabiz as NB
import webhook as WH

SAHTE_SIR = "sahte-app-" + "0123456789" * 2
VERIFY = "dogrulama-belirteci-xyz"
PNID = "106000000000001"
NUMARA_P = "900000000909"          # Patron (gerçek olmayan)
NUMARA_X = "900000000777"          # kayıtsız
CEVAP = "Bu hat yalnız kayıtlı bayilere açıktır."


@pytest.fixture
def kanal(depo, tmp_path):
    ayar = {"enabled": True, "dry_run": True, "mode": "patron", "kayitsiz_cevap": CEVAP, "enabled_at": 0}
    meta = M.MetaAyar(phone_number_id=PNID, access_token="t" * 40, app_secret=SAHTE_SIR, verify_token=VERIFY)
    k = WH.Kanal(depo=depo, meta=meta, veri=tmp_path / "veri", ayar_oku=lambda: dict(ayar))
    k.ayar_sozlugu = ayar
    return k


@pytest.fixture
def app(kanal):
    return WH.uygulama_olustur(kanal)


def istek(app, metod, yol, govde: bytes = b"", sorgu: str = "", basliklar: dict | None = None):
    env = {"REQUEST_METHOD": metod, "PATH_INFO": yol, "QUERY_STRING": sorgu, "CONTENT_LENGTH": str(len(govde)), "wsgi.input": BytesIO(govde)}
    for a, v in (basliklar or {}).items():
        env["HTTP_" + a.upper().replace("-", "_")] = v
    out = {}

    def sr(status, headers):
        out["status"] = int(status.split()[0]); out["headers"] = dict(headers)
    body = b"".join(app(env, sr))
    return out["status"], body


def post(app, p: dict, imza: str | None = "dogru"):
    govde = json.dumps(p).encode("utf-8")
    bas = {"Content-Type": "application/json"}
    if imza == "dogru":
        bas["X-Hub-Signature-256"] = M.imzala(govde, SAHTE_SIR)
    elif imza:
        bas["X-Hub-Signature-256"] = imza
    return istek(app, "POST", "/webhook", govde, basliklar=bas)


def yuk(mesajlar=(), durumlar=(), adlar: dict | None = None, pnid: str = PNID, field: str = "messages") -> dict:
    v = {"messaging_product": "whatsapp", "metadata": {"display_phone_number": "90 444", "phone_number_id": pnid}}
    if adlar:
        v["contacts"] = [{"wa_id": n, "profile": {"name": a}} for n, a in adlar.items()]
    if mesajlar:
        v["messages"] = list(mesajlar)
    if durumlar:
        v["statuses"] = list(durumlar)
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": field, "value": v}]}]}


_say = [0]


def metin(gonderen: str, metin_: str, ts: float | None = None, mid: str | None = None, **ek) -> dict:
    _say[0] += 1
    return {"id": mid or f"wamid.W{_say[0]:04d}", "from": gonderen, "timestamp": str(int(ts if ts is not None else time.time())), "type": "text",
            "text": {"body": metin_}, **ek}


def durum(mid: str, st: str, ts: float | None = None, alici: str = NUMARA_P, **ek) -> dict:
    return {"id": mid, "status": st, "timestamp": str(int(ts if ts is not None else time.time())), "recipient_id": alici, **ek}


# ───────────────────────── GET doğrulama ve POST girişi ─────────────────────────
def test_hub_dogrulama(app):
    assert istek(app, "GET", "/webhook", sorgu=f"hub.mode=subscribe&hub.verify_token={VERIFY}&hub.challenge=4711") == (200, b"4711")
    assert istek(app, "GET", "/webhook", sorgu="hub.mode=subscribe&hub.verify_token=yanlis&hub.challenge=4711")[0] == 403
    assert istek(app, "GET", "/baska")[0] == 404 and istek(app, "PUT", "/webhook")[0] == 405


def test_imza_ve_govde(app, depo):
    p = yuk([metin(NUMARA_P, "merhaba")])
    assert post(app, p, imza=None)[0] == 401
    assert post(app, p, imza="sha256=" + "0" * 64)[0] == 401
    kod, govde = istek(app, "POST", "/webhook", b"{bozuk", basliklar={"X-Hub-Signature-256": M.imzala(b"{bozuk", SAHTE_SIR)})
    assert kod == 400
    buyuk = b"x" * (M.GOVDE_EN_COK + 1)
    assert istek(app, "POST", "/webhook", buyuk, basliklar={"X-Hub-Signature-256": M.imzala(buyuk, SAHTE_SIR)})[0] == 413
    assert tek(depo, "SELECT count(*) AS n FROM mesajlar")["n"] == 0


def test_kapali_kanal_hicbir_olay_islemez(app, kanal, depo):
    kanal.ayar_sozlugu["enabled"] = False
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    kod, govde = post(app, yuk([metin(NUMARA_P, "merhaba")]))
    assert kod == 200 and json.loads(govde)["atlandi"] == "enabled"
    assert tek(depo, "SELECT count(*) AS n FROM mesajlar")["n"] == 0


# ───────────────────────── yakalama kuralları ─────────────────────────
BEKLENEN_ALANLAR = {"id", "context_id", "reply_id", "reply_kind", "sender", "name", "role", "bayi", "type", "text", "media_id", "filename",
                    "timestamp", "received_at", "phone_number_id", "source", "mode", "state", "attempts", "result", "error", "updated_at"}


def test_patron_mesaji_is_acar_satir_feature_php_bicimindedir(app, depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron", firma="PortatifEv")
    m = metin(NUMARA_P, "P6001 aynalı olsun", context={"id": "wamid.ONCEKI1"})
    kod, govde = post(app, yuk([m], adlar={NUMARA_P: "Lokman"}))
    assert kod == 200 and json.loads(govde)["mesaj"] == {"sahiplenildi": 1}
    r = tek(depo, "SELECT gonderen, bayi_kod, tur, metin, alinti_id, sahiplenildi, kaynak, ham FROM mesajlar")
    assert (r["gonderen"], r["bayi_kod"], r["tur"], r["metin"], r["alinti_id"], r["sahiplenildi"], r["kaynak"]) == (NUMARA_P, "PATRON", "text", "P6001 aynalı olsun", "wamid.ONCEKI1", True, "vps")
    ham = r["ham"]
    assert set(ham) == BEKLENEN_ALANLAR
    assert ham["role"] == "patron" and ham["bayi"] == {"kod": "PATRON", "ad": "Patron", "firma": "PortatifEv", "rol": "patron"}
    assert ham["name"] == "Lokman" and ham["source"] == "Meta imzalı webhook" and ham["phone_number_id"] == PNID and ham["mode"] == "patron"
    assert ham["state"] == "queued" and ham["reply_id"] is None and ham["media_id"] is None
    assert tek(depo, "SELECT durum FROM isler")["durum"] == "sirada" and depo.acik_is_sayisi() == 1
    assert tek(depo, "SELECT count(*) AS n FROM giden")["n"] == 0                                   # sabit cevap yalnız sahiplenilmeyene


def test_buton_cevabi_kimlikle_gelir(app, depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    m = {"id": "wamid.BTN1", "from": NUMARA_P, "timestamp": str(int(time.time())), "type": "interactive", "context": {"id": "wamid.SORU1"},
         "interactive": {"type": "button_reply", "button_reply": {"id": "q:oncelik:butce", "title": "Bütçe önce"}}}
    assert post(app, yuk([m]))[0] == 200
    ham = tek(depo, "SELECT ham FROM mesajlar")["ham"]
    assert (ham["reply_id"], ham["reply_kind"], ham["text"], ham["context_id"], ham["type"]) == ("q:oncelik:butce", "button_reply", "Bütçe önce", "wamid.SORU1", "interactive")
    m2 = dict(m, id="wamid.BTN2", context={"id": "12345"})                                           # geçersiz alıntı kimliği
    post(app, yuk([m2]))
    assert tek(depo, "SELECT alinti_id FROM mesajlar WHERE id = 'wamid.BTN2'")["alinti_id"] is None


def test_kayitli_bayi_patron_modunda_islenmez_sabit_cevap_24_saatte_bir(app, kanal, depo):
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    kod, govde = post(app, yuk([metin(NUMARA_A, "fiyat?")]))
    assert json.loads(govde)["mesaj"] == {"kayitsiz+cevap": 1}
    assert tek(depo, "SELECT sahiplenildi, bayi_kod FROM mesajlar") == {"sahiplenildi": False, "bayi_kod": None}
    assert tek(depo, "SELECT durum, sonuc FROM isler")["sonuc"]["eylem"] == "kayitsiz"
    g = tek(depo, "SELECT alici, govde, durum FROM giden")
    assert g["alici"] == NUMARA_A and g["govde"] == CEVAP and g["durum"] == "bekliyor"
    kod, govde = post(app, yuk([metin(NUMARA_A, "alo?")]))
    assert json.loads(govde)["mesaj"] == {"kayitsiz": 1} and tek(depo, "SELECT count(*) AS n FROM giden")["n"] == 1
    kanal.ayar_sozlugu["mode"] = "kayitli"
    kod, govde = post(app, yuk([metin(NUMARA_A, "P6001 olsun")]))
    assert json.loads(govde)["mesaj"] == {"sahiplenildi": 1} and depo.acik_is_sayisi() == 1
    r = tek(depo, "SELECT ham FROM mesajlar WHERE sahiplenildi ORDER BY alindi DESC LIMIT 1")["ham"]
    assert r["bayi"]["kod"] == "TSTA" and r["role"] == "bayi" and r["mode"] == "kayitli"


def test_kayitsiz_gonderen_ve_hepsi_modu(app, kanal, depo):
    kod, govde = post(app, yuk([metin(NUMARA_X, "merhaba")]))
    assert json.loads(govde)["mesaj"] == {"kayitsiz+cevap": 1} and depo.acik_is_sayisi() == 0
    assert tek(depo, "SELECT ham->>'neden' AS n FROM mesajlar")["n"] == "kayıtsız gönderen"
    kanal.ayar_sozlugu["mode"] = "hepsi"
    kod, govde = post(app, yuk([metin(NUMARA_X, "P6001 olsun")]))
    assert json.loads(govde)["mesaj"] == {"sahiplenildi": 1} and depo.acik_is_sayisi() == 1
    ham = tek(depo, "SELECT ham FROM mesajlar WHERE sahiplenildi")["ham"]
    assert ham["bayi"] is None and ham["role"] == "bayi"
    assert depo.bayi_oku(NUMARA_X) is None                                                            # kayıtsız gönderen kayda girmez


def test_eski_ve_gelecek_mesaj_kuyruga_alinmaz(app, kanal, depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    kod, govde = post(app, yuk([metin(NUMARA_P, "eski", ts=time.time() - 1000)]))
    assert json.loads(govde)["mesaj"] == {"eski": 1}
    kod, govde = post(app, yuk([metin(NUMARA_P, "gelecek", ts=time.time() + 120)]))
    assert json.loads(govde)["mesaj"] == {"eski": 1}
    kanal.ayar_sozlugu["enabled_at"] = int(time.time()) + 30
    kod, govde = post(app, yuk([metin(NUMARA_P, "enabled_at öncesi")]))
    assert json.loads(govde)["mesaj"] == {"eski": 1}
    assert tek(depo, "SELECT count(*) AS n FROM mesajlar WHERE NOT sahiplenildi")["n"] == 3 and depo.acik_is_sayisi() == 0
    assert tek(depo, "SELECT count(*) AS n FROM giden")["n"] == 0                                   # eski mesaja sabit cevap da gitmez
    kanal.ayar_sozlugu["enabled_at"] = 0
    kod, govde = post(app, yuk([metin(NUMARA_X, "kayıtsız ve eski", ts=time.time() - 1000)]))
    assert json.loads(govde)["mesaj"] == {"kayitsiz": 1} and tek(depo, "SELECT count(*) AS n FROM giden")["n"] == 0


def test_atlanan_olaylar(app, depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    tepki = {"id": "wamid.R1", "from": NUMARA_P, "timestamp": str(int(time.time())), "type": "reaction", "reaction": {"emoji": "👍"}}
    kod, govde = post(app, yuk([tepki, metin(NUMARA_P, "x", mid="12345"), metin("abc", "x"), metin(NUMARA_P, "y")]))
    assert json.loads(govde)["mesaj"] == {"atlandi": 3, "sahiplenildi": 1}
    assert post(app, yuk([metin(NUMARA_P, "başka numara")], pnid="999"))[0] == 200
    assert post(app, yuk([metin(NUMARA_P, "başka alan")], field="message_template_status_update"))[0] == 200
    assert post(app, {"object": "page", "entry": []})[0] == 200
    assert tek(depo, "SELECT count(*) AS n FROM mesajlar")["n"] == 1


def test_tekrar_teslim_tek_kayit(app, depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    p = yuk([metin(NUMARA_P, "bir kez")])
    assert json.loads(post(app, p)[1])["mesaj"] == {"sahiplenildi": 1}
    assert json.loads(post(app, p)[1])["mesaj"] == {"tekrar": 1}
    assert tek(depo, "SELECT count(*) AS n FROM mesajlar")["n"] == 1 and tek(depo, "SELECT count(*) AS n FROM isler")["n"] == 1


def test_medya_kaydi_acilir_indirme_gondericiye_kalir(app, depo):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    g = {"id": "wamid.IMG1", "from": NUMARA_P, "timestamp": str(int(time.time())), "type": "image", "image": {"id": "4455", "mime_type": "image/jpeg", "caption": "kroki"}}
    b = {"id": "wamid.DOC1", "from": NUMARA_X, "timestamp": str(int(time.time())), "type": "document",
         "document": {"id": "4456", "mime_type": "application/pdf", "filename": "plan.pdf"}}
    assert post(app, yuk([g, b]))[0] == 200
    rows = sorgu(depo, "SELECT mesaj_id, medya_id, dosya_adi, mime, yol FROM gelen_dosyalar ORDER BY id")
    assert [(r["mesaj_id"], r["medya_id"], r["dosya_adi"], r["mime"], r["yol"]) for r in rows] == \
           [("wamid.IMG1", "4455", None, "image/jpeg", None), ("wamid.DOC1", "4456", "plan.pdf", "application/pdf", None)]
    assert tek(depo, "SELECT metin, ham->>'media_id' AS m FROM mesajlar WHERE id = 'wamid.IMG1'") == {"metin": "kroki", "m": "4455"}
    assert depo.acik_is_sayisi() == 1                                                                # Patron'un görseli iş olur (metin dışı cevap)


# ───────────────────────── durum bildirimleri ─────────────────────────
def _gonderilmis_satir(depo, wa):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    g = mesaj("merhaba", talep("selam", "selam"), numara=NUMARA_P, bayi=depo.gelen_bayisi(NUMARA_P))
    g["role"] = "patron"
    depo.mesaj_kaydet(g)
    kalici.bir_is(depo, {"llm": {"backend": "manuel"}, "patron_teknik_not": False}, "t")
    kalici.gonder(depo, wa)
    return tek(depo, "SELECT id, dis_id FROM giden ORDER BY sira LIMIT 1")


def test_durum_bildirimleri_giden_satirina_islenir(app, depo, wa):
    s = _gonderilmis_satir(depo, wa)
    assert s["dis_id"] == "wamid.OUT0001"
    t0 = int(time.time())
    kod, govde = post(app, yuk(durumlar=[durum("wamid.OUT0001", "sent", t0), durum("wamid.OUT0001", "delivered", t0 + 5)]))
    assert json.loads(govde)["durum"] == {"sent": 1, "delivered": 1}
    r = tek(depo, "SELECT teslim_durumu, extract(epoch FROM gonderildi_zamani)::int AS g, extract(epoch FROM teslim_zamani)::int AS t, durum FROM giden WHERE id = %s", s["id"])
    assert (r["teslim_durumu"], r["g"], r["t"], r["durum"]) == ("delivered", t0, t0 + 5, "kabul_edildi")
    kod, govde = post(app, yuk(durumlar=[durum("wamid.OUT0001", "read", t0 + 9), durum("wamid.OUT0001", "sent", t0 + 1)]))      # geç gelen sent ezmez
    r = tek(depo, "SELECT teslim_durumu, extract(epoch FROM teslim_zamani)::int AS t FROM giden WHERE id = %s", s["id"])
    assert (r["teslim_durumu"], r["t"]) == ("read", t0 + 5)
    kod, govde = post(app, yuk(durumlar=[durum("wamid.OUT0001", "read", t0 + 9)]))                                           # aynı olay yeniden
    assert json.loads(govde)["durum"] == {"tekrar": 1}
    kod, govde = post(app, yuk(durumlar=[durum("wamid.YOK", "delivered"), {"id": "x", "status": "sent"}, durum("wamid.OUT0001", "typing")]))
    assert json.loads(govde)["durum"] == {"eslesmedi": 1, "atlandi": 2}


def test_failed_bildirimi_hata_yazar_ve_opaque_ile_eslesme(app, depo, wa):
    s = _gonderilmis_satir(depo, wa)
    hata = durum("wamid.OUT0001", "failed", errors=[{"code": 131026, "title": "Message undeliverable", "message": "x" * 300}])
    assert json.loads(post(app, yuk(durumlar=[hata]))[1])["durum"] == {"failed": 1}
    r = tek(depo, "SELECT teslim_durumu, hata FROM giden WHERE id = %s", s["id"])
    assert r["teslim_durumu"] == "failed" and r["hata"].startswith("Meta teslimat hatası: 131026 Message undeliverable")
    # wamid yazılamamış (belirsiz) satır: durum bildirimi biz_opaque_callback_data ile eşlenir ve kabul sayılır
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET dis_id = NULL, durum = 'belirsiz', teslim_durumu = NULL, hata = NULL WHERE id = %s", (s["id"],))
    kod, govde = post(app, yuk(durumlar=[durum("wamid.OUT0001", "delivered", biz_opaque_callback_data=s["id"])]))
    assert json.loads(govde)["durum"] == {"delivered": 1}
    r = tek(depo, "SELECT dis_id, durum, teslim_durumu FROM giden WHERE id = %s", s["id"])
    assert (r["dis_id"], r["durum"], r["teslim_durumu"]) == ("wamid.OUT0001", "kabul_edildi", "delivered")
    # alıcı uyuşmazlığı: çözülen alıcı başka numaraysa işlenmez
    depo.alici_cozuldu_kaydet(s["id"], NUMARA_A)
    kod, govde = post(app, yuk(durumlar=[durum("wamid.OUT0001", "read", alici=NUMARA_P)]))
    assert json.loads(govde)["durum"] == {"alici_uyusmadi": 1}
    assert tek(depo, "SELECT teslim_durumu FROM giden WHERE id = %s", s["id"])["teslim_durumu"] == "delivered"


# ───────────────────────── sağlık ve hata yolu ─────────────────────────
def test_saglik(app, kanal, depo):
    kod, govde = istek(app, "GET", "/saglik")
    j = json.loads(govde)
    assert kod == 503 and j["ok"] is False and j["postgres"] is True and any("agent" in s for s in j["sorunlar"])
    NB.yaz(kanal.veri, "agent", surum="test"); NB.yaz(kanal.veri, "gonderici")
    kod, govde = istek(app, "GET", "/saglik")
    j = json.loads(govde)
    assert kod == 200 and j["ok"] and j["ajan_sn"] == 0 and j["sayimlar"]["aktif_bayi"] == 0 and j["enabled"] is True
    assert NUMARA_P not in govde.decode() and "sorunlar" in j
    kanal.ayar_sozlugu["enabled"] = False
    (kanal.veri / "nabiz" / "agent.json").unlink()
    assert istek(app, "GET", "/saglik")[0] == 200                                                     # kapalıyken nabız aranmaz
    # vps/nabiz.sh'nin dosyası: sorun listesi 503'e sayılır (kanal kapalıyken de); eski dosya da sorundur
    NB.yaz(kanal.veri, "nabiz", sorunlar=["sertifika: 9 gün kaldı (certbot renew)"])
    kod, govde = istek(app, "GET", "/saglik")
    assert kod == 503 and "nabiz: sertifika: 9 gün kaldı (certbot renew)" in json.loads(govde)["sorunlar"]
    NB.yaz(kanal.veri, "nabiz", sorunlar=[])
    assert istek(app, "GET", "/saglik")[0] == 200
    (kanal.veri / "nabiz" / "nabiz.json").write_text(json.dumps({"zaman": int(time.time()) - 1000, "ad": "nabiz", "sorunlar": []}))
    kod, govde = istek(app, "GET", "/saglik")
    assert kod == 503 and any(s.startswith("nabiz.sh:") for s in json.loads(govde)["sorunlar"])


def test_islenemeyen_olay_503_meta_yeniden_dener(app, depo, monkeypatch):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")

    def patlat(*a, **k):
        raise RuntimeError("postgres gitti")
    monkeypatch.setattr(depo, "mesaj_kaydet", patlat)
    assert post(app, yuk([metin(NUMARA_P, "x")]))[0] == 503
