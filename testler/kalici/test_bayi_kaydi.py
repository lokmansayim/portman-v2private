"""İE-22 · WhatsApp'tan bayi kaydı (Kurulum Panosu satır 111; bayi rehberi §9): kayıtsız numara yazar → ad ve firma sorulur → Patron'a
[Onayla] [Reddet] → onayla kart açılır ve karşılama şablonu gider; red 30 gün yeni talep açmaz, panelden geri alınır; panel yedektir.

Sahte WhatsApp: imzalı Meta webhook gövdeleri (test_webhook.py) ve sahte Graph API (sahte_meta.py); gerçek Postgres; ağ, LLM, WhatsApp
ve canlı yok. Ayar `bayi_kaydi.acik` kapalıyken davranış bugünküyle aynıdır (ilk test).
"""
from __future__ import annotations

import json
import time

import pytest

from conftest import AYAR, sorgu, tek
from test_panel import DOGRU, Istemci, _gonderen, pn  # noqa: F401  (pn: fikstür)
from test_webhook import CEVAP, NUMARA_P, NUMARA_X, app, kanal, metin, post, yuk  # noqa: F401  (app, kanal: fikstür)

import gonderici as G
import kalici
import kayit as KY
import sablonlar as S
import worker as W

NUMARA_Z = "900000000555"            # ikinci kayıtsız (gerçek olmayan)
AYAR_K = {**AYAR, "mode": "kayitli"}
AYAR_G = {**AYAR, "enabled": True, "dry_run": False, "mode": "kayitli", "sablon_patron_bildirim": "portman_patron_bekliyor_v1",
          "sablon_bayi_karsilama": "portman_karsilama_v1"}


@pytest.fixture
def acik(kanal, depo):
    """Ayar açık, mod kayıtlı (canlıdaki mod), Patron kartı var."""
    kanal.ayar_sozlugu.update(mode="kayitli", bayi_kaydi={"acik": True, "gunluk_en_cok": 10})
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    return kanal


def yaz(app, numara: str, m: str | None = None, **ek) -> dict:
    msg = metin(numara, m or "") if m is not None else {**metin(numara, ""), **ek}
    if m is None:
        msg.pop("text", None)
    kod, govde = post(app, yuk([msg]))
    assert kod == 200
    return json.loads(govde)["mesaj"]


def talep_sonu(app, numara: str = NUMARA_X, ad: str = "Ahmet Yılmaz", firma: str = "Yılmaz Yapı") -> None:
    assert yaz(app, numara, "merhaba") == {"kayit:ad+cevap": 1}
    assert yaz(app, numara, ad) == {"kayit:firma+cevap": 1}
    assert yaz(app, numara, firma) == {"kayit:onay_bekliyor+cevap": 1}


def talep_satiri(depo, numara: str = NUMARA_X) -> dict:
    return tek(depo, "SELECT * FROM kayit_talepleri WHERE numara = %s ORDER BY id DESC LIMIT 1", numara)


def dugme(numara: str, reply_id: str, baslik: str = "Onayla", ctx: str | None = None) -> dict:
    m = {"id": f"wamid.KB{time.time_ns()}", "from": numara, "timestamp": str(int(time.time())), "type": "interactive",
         "interactive": {"type": "button_reply", "button_reply": {"id": reply_id, "title": baslik}}}
    if ctx:
        m["context"] = {"id": ctx}
    return m


def isle_hepsi(depo, ayar=AYAR_K):
    out = []
    while (r := kalici.bir_is(depo, ayar, "t")) is not None:
        out.append(r)
    return out


@pytest.fixture
def llmsiz(monkeypatch):
    """LLM çağrılırsa test düşer: kayıt akışı hiçbir adımda LLM'e gitmez."""
    def yok(*a, **k):
        raise AssertionError("LLM çağrıldı")
    monkeypatch.setattr(W, "cikar", yok)


# ───────────────────────── ayar kapalı: bugünkü davranış ─────────────────────────
def test_ayar_kapali_bugunku_sabit_cevap(app, kanal, depo):
    kanal.ayar_sozlugu["mode"] = "kayitli"
    assert yaz(app, NUMARA_X, "merhaba") == {"kayitsiz+cevap": 1}
    assert yaz(app, NUMARA_X, "Ahmet Yılmaz") == {"kayitsiz": 1}
    assert tek(depo, "SELECT count(*) AS n FROM kayit_talepleri")["n"] == 0
    g = tek(depo, "SELECT alici, govde, tur FROM giden")
    assert (g["alici"], g["govde"], g["tur"]) == (NUMARA_X, CEVAP, "cevap")
    assert {r["sonuc"]["eylem"] for r in sorgu(depo, "SELECT sonuc FROM isler")} == {"kayitsiz"}
    kanal.ayar_sozlugu["bayi_kaydi"] = {"acik": "evet"}                 # yalnız true açar
    assert yaz(app, NUMARA_Z, "merhaba") == {"kayitsiz+cevap": 1}


def test_ayarlar_varsayilan_kapali_ve_birlesir(tmp_path):
    import ayarlar as AY
    assert AY.oku(tmp_path)["bayi_kaydi"] == {"acik": False, "gunluk_en_cok": 10}
    AY.yaz(tmp_path, "bayi_kaydi", {"acik": True})
    assert AY.oku(tmp_path)["bayi_kaydi"] == {"acik": True, "gunluk_en_cok": 10}
    assert KY.adim(AY.oku(tmp_path)).gunluk_en_cok == 10 and KY.adim({"bayi_kaydi": {"acik": False}}) is None


# ───────────────────────── 1–2 · kayıtsız numara: ad, firma, Patron'a talep ─────────────────────────
def test_uc_adim_ve_patrona_talep(app, acik, depo, llmsiz):
    assert yaz(app, NUMARA_X, "merhaba, fiyat alabilir miyim") == {"kayit:ad+cevap": 1}
    t = talep_satiri(depo)
    assert (t["durum"], t["ad"], t["firma"]) == ("ad", "", "")
    assert tek(depo, "SELECT govde FROM giden ORDER BY olusturuldu DESC LIMIT 1")["govde"] == KY.SORU_AD
    assert yaz(app, NUMARA_X, "  Ahmet   Yılmaz ") == {"kayit:firma+cevap": 1}
    assert yaz(app, NUMARA_X, "Yılmaz Yapı Ltd.") == {"kayit:onay_bekliyor+cevap": 1}
    t = talep_satiri(depo)
    assert (t["durum"], t["ad"], t["firma"]) == ("onay_bekliyor", "Ahmet Yılmaz", "Yılmaz Yapı Ltd.")
    assert t["son_mesaj_id"] != t["ilk_mesaj_id"]
    rows = sorgu(depo, "SELECT g.sira, g.alici, g.kind, g.tur, g.govde, g.satir FROM giden g WHERE g.mesaj_id = %s ORDER BY sira", t["son_mesaj_id"])
    assert [(r["sira"], r["alici"], r["kind"]) for r in rows] == [(1, NUMARA_X, "text"), (2, "PATRON", "interactive"), (3, "PATRON", "template")]
    assert rows[0]["govde"] == KY.TESEKKUR and rows[0]["tur"] == "kayit"
    dugmeli = rows[1]["satir"]
    ids = [(b["reply"]["id"], b["reply"]["title"]) for b in dugmeli["interactive"]["action"]["buttons"]]
    assert ids == [(f"kayit:onay:{t['id']}", "Onayla"), (f"kayit:red:{t['id']}", "Reddet")]
    assert "Ahmet Yılmaz" in rows[1]["govde"] and "Yılmaz Yapı Ltd." in rows[1]["govde"] and "B0777" in rows[1]["govde"]
    assert NUMARA_X not in rows[1]["govde"] and dugmeli["interactive"]["footer"]["text"] == KY.PATRON_ALTBILGI
    sablon = rows[2]["satir"]
    assert sablon["sablon_anahtari"] == "sablon_patron_bildirim" and sablon["pencere_kapaliysa"] is True
    assert sablon["sablon"]["govde"] == ["B0777", f"KAYIT-{t['id']}"]
    assert sablon["sablon"]["dugmeler"] == [{"sub_type": "url", "index": 0, "text": f"konusma/{NUMARA_X}"}]
    # bayi sorularının hepsi kayıt türünde, Patron'a talep başına bir bildirim; kart yok, iş açılmadı
    assert [r["govde"] for r in sorgu(depo, "SELECT govde FROM giden WHERE alici = %s ORDER BY olusturuldu, sira", NUMARA_X)] == [
        KY.SORU_AD, KY.SORU_FIRMA, KY.TESEKKUR]
    assert depo.bayi_oku(NUMARA_X) is None and depo.acik_is_sayisi() == 0
    assert {r["sonuc"]["eylem"] for r in sorgu(depo, "SELECT sonuc FROM isler")} == {"kayit"}
    assert tek(depo, "SELECT count(*) AS n FROM mesajlar WHERE sahiplenildi")["n"] == 0


def test_gecersiz_cevap_ayni_soru_ve_cevap_siniri(app, acik, depo):
    assert yaz(app, NUMARA_X, "merhaba") == {"kayit:ad+cevap": 1}
    assert yaz(app, NUMARA_X, None, type="image", image={"id": "55501", "mime_type": "image/jpeg"}) == {"kayit:ad+cevap": 1}
    assert yaz(app, NUMARA_X, "0532 123 45 67") == {"kayit:ad+cevap": 1}
    assert yaz(app, NUMARA_X, "x") == {"kayit:ad+cevap": 1}
    govde = [r["govde"] for r in sorgu(depo, "SELECT govde FROM giden WHERE alici = %s ORDER BY olusturuldu", NUMARA_X)]
    assert govde == [KY.SORU_AD] + [KY.SORU_AD_YENIDEN] * 3
    # 24 saatte 4 cevap: sonrası sessiz, ama geçerli cevap talebi ilerletir
    assert yaz(app, NUMARA_X, "y") == {"kayit:ad": 1}
    assert yaz(app, NUMARA_X, "Ayşe Kaya") == {"kayit:firma": 1}
    assert tek(depo, "SELECT count(*) AS n FROM giden WHERE alici = %s", NUMARA_X)["n"] == 4
    with depo.baglan() as c:
        c.execute("UPDATE giden SET olusturuldu = now() - interval '25 hours'")
    assert yaz(app, NUMARA_X, "Kaya İnşaat") == {"kayit:onay_bekliyor+cevap": 1}
    assert talep_satiri(depo)["ad"] == "Ayşe Kaya"
    assert tek(depo, "SELECT count(*) AS n FROM giden WHERE alici = 'PATRON'")["n"] == 2


@pytest.mark.parametrize("deger,ad_mi", [("Ahmet Yılmaz", True), ("Ali", True), ("Al", False), ("12345", False), ("Ahmet 0532 123 4567", False),
                                         ("www http://x.y", False), ("a@b.c Ahmet", False), ("A" * 81, False)])
def test_ad_denetimi(deger, ad_mi):
    assert (KY.ad_coz({"type": "text", "text": deger}) is not None) is ad_mi
    assert KY.ad_coz({"type": "image", "text": "Ahmet Yılmaz"}) is None
    assert KY.firma_coz({"type": "text", "text": "3D Yapı"}) == "3D Yapı" and KY.firma_coz({"type": "text", "text": "Y"}) is None


def test_onay_beklerken_24_saatte_bir_cevap_patrona_tek_bildirim(app, acik, depo):
    talep_sonu(app)
    assert yaz(app, NUMARA_X, "ne oldu?") == {"kayit:onay_bekliyor+cevap": 1}
    assert yaz(app, NUMARA_X, "alo") == {"kayit:onay_bekliyor": 1}
    assert tek(depo, "SELECT govde FROM giden WHERE alici = %s ORDER BY olusturuldu DESC LIMIT 1", NUMARA_X)["govde"] == KY.ONAY_BEKLIYOR
    with depo.baglan() as c:                                          # 25 saat geçti (cevap sınırı da sıfırlanır)
        c.execute("UPDATE kayitsiz_cevaplar SET son = now() - interval '25 hours'")
        c.execute("UPDATE giden SET olusturuldu = olusturuldu - interval '25 hours'")
    assert yaz(app, NUMARA_X, "hâlâ bekliyorum") == {"kayit:onay_bekliyor+cevap": 1}
    assert tek(depo, "SELECT count(*) AS n FROM giden WHERE alici = 'PATRON'")["n"] == 2
    assert talep_satiri(depo)["son_mesaj_id"] == tek(depo, "SELECT id FROM mesajlar ORDER BY alindi DESC LIMIT 1")["id"]


def test_cevapsiz_talep_24_saatte_duser_bastan_baslar(app, acik, depo):
    assert yaz(app, NUMARA_X, "merhaba") == {"kayit:ad+cevap": 1}
    assert yaz(app, NUMARA_X, "Ahmet Yılmaz") == {"kayit:firma+cevap": 1}
    with depo.baglan() as c:
        c.execute("UPDATE kayit_talepleri SET guncellendi = now() - interval '25 hours'")
    assert yaz(app, NUMARA_X, "Yılmaz Yapı") == {"kayit:ad+cevap": 1}
    rows = sorgu(depo, "SELECT durum, ad FROM kayit_talepleri ORDER BY id")
    assert [(r["durum"], r["ad"]) for r in rows] == [("zaman_asimi", "Ahmet Yılmaz"), ("ad", "")]


def test_gunluk_tavan_sabit_cevaba_duser(app, acik, depo):
    acik.ayar_sozlugu["bayi_kaydi"] = {"acik": True, "gunluk_en_cok": 1}
    assert yaz(app, NUMARA_X, "merhaba") == {"kayit:ad+cevap": 1}
    assert yaz(app, NUMARA_Z, "merhaba") == {"kayitsiz+cevap": 1}
    assert tek(depo, "SELECT govde FROM giden WHERE alici = %s", NUMARA_Z)["govde"] == CEVAP
    assert yaz(app, NUMARA_X, "Ahmet Yılmaz") == {"kayit:firma+cevap": 1}            # açık talep tavandan etkilenmez
    assert tek(depo, "SELECT count(*) AS n FROM kayit_talepleri")["n"] == 1


@pytest.mark.parametrize("rol,aktif", [("bayi", False), ("test", False), ("muhendis", False), ("patron", False)])
def test_karti_olan_numara_akisa_girmez(app, acik, depo, rol, aktif):
    depo.bayi_yaz(NUMARA_X, ad="Kart", kod="KK", rol=rol, aktif=aktif)
    assert yaz(app, NUMARA_X, "merhaba") == {"kayitsiz+cevap": 1}
    assert tek(depo, "SELECT count(*) AS n FROM kayit_talepleri")["n"] == 0


def test_eski_mesaj_kayit_akisina_girmez(app, acik, depo):
    m = metin(NUMARA_X, "merhaba", ts=time.time() - 3600)
    kod, govde = post(app, yuk([m]))
    assert json.loads(govde)["mesaj"] == {"kayitsiz": 1}
    assert tek(depo, "SELECT count(*) AS n FROM kayit_talepleri")["n"] == 0 and tek(depo, "SELECT count(*) AS n FROM giden")["n"] == 0


# ───────────────────────── 3 · Patron'un kararı (WhatsApp) ─────────────────────────
def test_patron_onaylar_kart_acilir_karsilama_gider(app, acik, depo, llmsiz):
    talep_sonu(app)
    t = talep_satiri(depo)
    kod, govde = post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}")]))
    assert kod == 200 and json.loads(govde)["mesaj"] == {"sahiplenildi": 1}
    [r] = isle_hepsi(depo)
    assert (r["durum"], r["eylem"], r["gerekce"]) == ("bitti", "kayit", "kayıt onaylandı")
    b = depo.bayi_oku(NUMARA_X)
    assert (b["ad"], b["firma"], b["rol"], b["aktif"], b["kaynak"], b["kod"], b["hitap"]) == ("Ahmet Yılmaz", "Yılmaz Yapı", "bayi", True, "whatsapp", "B0777", "")
    t2 = talep_satiri(depo)
    assert (t2["durum"], t2["karar_kaynagi"]) == ("onaylandi", "whatsapp") and t2["karar_mesaj_id"].startswith("wamid.KB")
    p = tek(depo, "SELECT alici, govde FROM giden WHERE mesaj_id = %s", t2["karar_mesaj_id"])
    assert p["alici"] == NUMARA_P and p["govde"].startswith("Kayıt açıldı: B0777 · Ahmet Yılmaz · Yılmaz Yapı.") and "modunda" not in p["govde"]
    k = tek(depo, "SELECT sira, alici, kind, kaynak, satir FROM giden WHERE mesaj_id = %s AND kind = 'template' AND alici = %s", t["son_mesaj_id"], NUMARA_X)
    assert (k["alici"], k["kaynak"], k["sira"]) == (NUMARA_X, "sistem", 201)
    assert k["satir"]["sablon_anahtari"] == "sablon_bayi_karsilama" and k["satir"]["sablon"]["govde"] == ["Ahmet Yılmaz"]
    assert k["satir"]["sablon"]["dugmeler"] == [{"sub_type": "quick_reply", "index": 0, "payload": S.BILGI_NASIL}]
    # kart açıldı: bayinin sonraki mesajı (mod kayıtlı) sahiplenilir; "Nasıl çalışır?" düğmesi bugünkü PDF yolundan
    assert yaz(app, NUMARA_X, "P6001 olsun") == {"sahiplenildi": 1}
    g = dugme(NUMARA_X, S.BILGI_NASIL, "Nasıl çalışır?")
    assert post(app, yuk([g]))[0] == 200
    with depo.baglan() as c:                                         # ilk talep bu testin konusu değil: yalnız düğmenin işi işlenir
        c.execute("UPDATE isler SET durum = 'bitti' WHERE mesaj_id IN (SELECT id FROM mesajlar WHERE metin = 'P6001 olsun')")
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "şablon cevabı: nasıl çalışır"
    assert tek(depo, "SELECT satir->>'filename' AS f FROM giden WHERE mesaj_id = %s AND kind = 'document'", g["id"])["f"] == "Portman_Nasil_calisir.pdf"


def test_patron_modunda_onay_notu(app, acik, depo):
    talep_sonu(app)
    t = talep_satiri(depo)
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}")]))
    isle_hepsi(depo, {**AYAR, "mode": "patron"})
    assert "'patron' modunda" in tek(depo, "SELECT govde FROM giden WHERE alici = %s", NUMARA_P)["govde"]


def test_patron_reddeder_30_gun_yeni_talep_yok(app, acik, depo, llmsiz):
    talep_sonu(app)
    t = talep_satiri(depo)
    post(app, yuk([dugme(NUMARA_P, f"kayit:red:{t['id']}", "Reddet")]))
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "kayıt reddedildi" and depo.bayi_oku(NUMARA_X) is None
    assert talep_satiri(depo)["durum"] == "reddedildi"
    red = tek(depo, "SELECT alici, kind, kaynak, govde, sira FROM giden WHERE mesaj_id = %s AND sira >= 201", t["son_mesaj_id"])
    assert (red["alici"], red["kind"], red["kaynak"], red["govde"]) == (NUMARA_X, "text", "sistem", KY.RED_BAYIYE)
    assert "30 gün" in tek(depo, "SELECT govde FROM giden WHERE alici = %s", NUMARA_P)["govde"]
    # 30 gün içinde: bugünkü sabit cevap, yeni talep yok
    assert yaz(app, NUMARA_X, "tekrar merhaba") == {"kayitsiz+cevap": 1}
    assert tek(depo, "SELECT count(*) AS n FROM kayit_talepleri")["n"] == 1
    with depo.baglan() as c:                                          # 31 gün geçti
        c.execute("UPDATE kayit_talepleri SET karar_zamani = now() - interval '31 days'")
        c.execute("UPDATE giden SET olusturuldu = olusturuldu - interval '31 days'")
    assert yaz(app, NUMARA_X, "merhaba yine") == {"kayit:ad+cevap": 1}
    assert [r["durum"] for r in sorgu(depo, "SELECT durum FROM kayit_talepleri ORDER BY id")] == ["reddedildi", "ad"]


def test_ikinci_dugme_zaten_karara_baglandi(app, acik, depo):
    talep_sonu(app)
    t = talep_satiri(depo)
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}")]))
    post(app, yuk([dugme(NUMARA_P, f"kayit:red:{t['id']}", "Reddet")]))
    r1, r2 = isle_hepsi(depo)
    assert (r1["gerekce"], r2["gerekce"]) == ("kayıt onaylandı", "kayıt talebi zaten karara bağlandı")
    assert depo.bayi_oku(NUMARA_X)["aktif"] is True and talep_satiri(depo)["durum"] == "onaylandi"
    assert tek(depo, "SELECT count(*) AS n FROM giden WHERE alici = %s AND kind = 'template'", NUMARA_X)["n"] == 1
    son = tek(depo, "SELECT govde FROM giden WHERE alici = %s ORDER BY olusturuldu DESC, sira DESC LIMIT 1", NUMARA_P)["govde"]
    assert son == f"KAYIT-{t['id']} zaten karara bağlandı (onaylandı)."


def test_panel_karar_verirken_yaris_cakisma_ve_ikinci_tur(app, acik, depo, monkeypatch):
    """Ajan talebi okuduktan sonra panel karar verirse işin kaydı Cakisma ile yazılmaz; iş yeniden sıraya girer, ikinci turda 'zaten'."""
    talep_sonu(app)
    t = talep_satiri(depo)
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}")]))
    asil = KY.isle

    def araya_panel(depo_, gelen, settings=None):
        out = asil(depo_, gelen, settings)
        depo_.kayit_karari_yaz(t["id"], "red", lambda tt, k, kart: KY.karar_satirlari(tt, k, kart, kaynak="panel"))
        return out
    monkeypatch.setattr(KY, "isle", araya_panel)
    r = kalici.bir_is(depo, AYAR_K, "t")
    assert r["durum"] == "cakisma" and depo.bayi_oku(NUMARA_X) is None
    monkeypatch.setattr(KY, "isle", asil)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "kayıt talebi zaten karara bağlandı" and talep_satiri(depo)["durum"] == "reddedildi"
    assert tek(depo, "SELECT count(*) AS n FROM giden WHERE alici = %s AND kind = 'template'", NUMARA_X)["n"] == 0


def test_kart_onaydan_once_panelden_acildiysa_karsilama_gitmez(app, acik, depo):
    talep_sonu(app)
    t = talep_satiri(depo)
    depo.bayi_yaz(NUMARA_X, ad="Elle Açılan", kod="EA", rol="bayi", aktif=False)
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}")]))
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "kayıt onaylandı" and talep_satiri(depo)["durum"] == "onaylandi"
    assert depo.bayi_oku(NUMARA_X)["ad"] == "Elle Açılan"                    # kart ezilmez
    assert "zaten var" in tek(depo, "SELECT govde FROM giden WHERE alici = %s", NUMARA_P)["govde"]
    assert tek(depo, "SELECT count(*) AS n FROM giden WHERE alici = %s AND kind = 'template'", NUMARA_X)["n"] == 0


def test_yabanci_ve_bozuk_dugme(app, acik, depo):
    talep_sonu(app)
    t = talep_satiri(depo)
    depo.bayi_yaz(NUMARA_Z, ad="Başka Bayi", kod="BB", rol="bayi")
    post(app, yuk([dugme(NUMARA_Z, f"kayit:onay:{t['id']}")]))                # bayi kayıt düğmesi gönderemez (Patron değil)
    post(app, yuk([dugme(NUMARA_P, "kayit:onay:abc")]))                          # bozuk kimlik
    post(app, yuk([dugme(NUMARA_P, "kayit:onay:999999")]))                       # olmayan talep
    rs = isle_hepsi(depo)
    assert [r["gerekce"] for r in rs][1:] == ["kayıt düğmesi doğrulanamadı", "kayıt talebi yok"]
    assert rs[0]["eylem"] != "kayit" and depo.bayi_oku(NUMARA_X) is None and talep_satiri(depo)["durum"] == "onay_bekliyor"


# ───────────────────────── gönderici: pencere, şablon, alıcı (sahte Graph API) ─────────────────────────
def test_gonderici_patron_penceresi_kapali_sablon_acik_dugmeli(app, acik, depo):
    from sahte_meta import SahteMeta
    talep_sonu(app)
    t = talep_satiri(depo)
    meta = SahteMeta(); g = _gonderen(depo, meta, AYAR_G)
    G.tur(depo, g, g.istemci, W.KANAL, AYAR_G)                               # Patron hiç yazmadı: pencere kapalı
    d = {r["sira"]: r for r in sorgu(depo, "SELECT sira, durum, hata FROM giden WHERE mesaj_id = %s", t["son_mesaj_id"])}
    assert d[1]["durum"] == "kabul_edildi" and d[2]["durum"] == "gonderilmedi" and "reply_window_closed" in d[2]["hata"] and d[3]["durum"] == "kabul_edildi"
    sablon = [y for y in meta.gidenler() if y.get("type") == "template"]
    assert len(sablon) == 1 and sablon[0]["to"] == NUMARA_P and sablon[0]["template"]["name"] == "portman_patron_bekliyor_v1"
    params = [p["text"] for c in sablon[0]["template"]["components"] if c["type"] == "body" for p in c["parameters"]]
    assert params == ["B0777", f"KAYIT-{t['id']}"]
    # ikinci talep: Patron yazmış (pencere açık) → düğmeli mesaj gider, şablon gereksiz
    assert yaz(app, NUMARA_P, "merhaba") == {"sahiplenildi": 1}
    with depo.baglan() as c:
        c.execute("UPDATE isler SET durum = 'bitti' WHERE gonderen = %s", (NUMARA_P,))
    talep_sonu(app, NUMARA_Z, "Ayşe Kaya", "Kaya İnşaat")
    t2 = talep_satiri(depo, NUMARA_Z)
    meta2 = SahteMeta(); g2 = _gonderen(depo, meta2, AYAR_G)
    for _ in range(3):
        G.tur(depo, g2, g2.istemci, W.KANAL, AYAR_G)
    d = {r["sira"]: r for r in sorgu(depo, "SELECT sira, durum, hata, dis_id FROM giden WHERE mesaj_id = %s", t2["son_mesaj_id"])}
    assert d[2]["durum"] == "kabul_edildi" and d[3]["durum"] == "gonderilmedi" and "sablon_gereksiz" in d[3]["hata"]
    [dm] = [y for y in meta2.gidenler() if y.get("type") == "interactive"]
    assert dm["to"] == NUMARA_P and [b["reply"]["id"] for b in dm["interactive"]["action"]["buttons"]] == [f"kayit:onay:{t2['id']}", f"kayit:red:{t2['id']}"]
    # Patron düğmeli mesaja cevap verir (alıntı doğrulanır) → karşılama bayiye şablonla
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t2['id']}", ctx=d[2]["dis_id"])]))
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "kayıt onaylandı"
    meta3 = SahteMeta(); g3 = _gonderen(depo, meta3, AYAR_G)
    for _ in range(3):
        G.tur(depo, g3, g3.istemci, W.KANAL, AYAR_G)
    [k] = [y for y in meta3.gidenler() if y.get("type") == "template"]
    assert k["to"] == NUMARA_Z and k["template"]["name"] == "portman_karsilama_v1"
    # alıntılanan mesajın düğmeleri arasında olmayan kimlik reddedilir
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}", ctx=d[2]["dis_id"])]))
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "kayıt düğmesi doğrulanamadı" and depo.bayi_oku(NUMARA_X) is None


def test_dugmeli_satir_worker_bicimiyle_ayni():
    gelen = {"id": "wamid.ESIT1", "sender": NUMARA_X}
    a = KY.dugmeli_satir(gelen, "Gövde  metni\nikinci satır", 2, NUMARA_X, "bildirim", [("kayit:onay:1", "Onayla"), ("kayit:red:1", "Reddet")], "Alt bilgi")
    b = W.giden_etkilesim(gelen, "Gövde  metni\nikinci satır", 2, butonlar=[("kayit:onay:1", "Onayla"), ("kayit:red:1", "Reddet")], altbilgi="Alt bilgi",
                          tur="bildirim")
    for x in (a, b):
        x.pop("created_at"); x.pop("updated_at")
    assert a == b


# ───────────────────────── 4 · panel (yedek) ─────────────────────────
def test_panel_onayla_reddet_ve_reddi_geri_al(app, acik, depo, pn):
    talep_sonu(app)
    t = talep_satiri(depo)
    c = Istemci(pn); c.giris(DOGRU)
    kod, h, _ = c.git("GET", "/panel/")
    assert kod == 200 and "Onay bekleyen bayi kaydı: <b>1</b>".encode() in h
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_X}")
    assert f"KAYIT-{t['id']}".encode() in h and f'action="/panel/konusma/{NUMARA_X}/kayit_onay"'.encode() in h
    assert f'action="/panel/konusma/{NUMARA_X}/kayit_red"'.encode() in h and "Ahmet Yılmaz".encode() in h
    csrf = c.csrf(h)
    assert c.git("POST", f"/panel/konusma/{NUMARA_X}/kayit_red", {"csrf": csrf, "talep": "999"})[0] == 400        # başka talep
    assert c.git("GET", f"/panel/konusma/{NUMARA_X}/kayit_red")[0] == 405
    kod, _, b = c.git("POST", f"/panel/konusma/{NUMARA_X}/kayit_red", {"csrf": csrf, "talep": str(t["id"])})
    assert (kod, c.baslik(b, "Location")) == (302, [f"/panel/konusma/{NUMARA_X}"])
    t2 = talep_satiri(depo)
    assert (t2["durum"], t2["karar_kaynagi"]) == ("reddedildi", "panel") and depo.bayi_oku(NUMARA_X) is None
    red = tek(depo, "SELECT govde, kaynak FROM giden WHERE mesaj_id = %s AND sira >= 201", t["son_mesaj_id"])
    assert (red["govde"], red["kaynak"]) == (KY.RED_BAYIYE, "panel")
    kod, _, _ = c.git("POST", f"/panel/konusma/{NUMARA_X}/kayit_onay", {"csrf": csrf, "talep": str(t["id"])})
    assert kod == 400 and depo.bayi_oku(NUMARA_X) is None                       # reddedilmiş talep onaylanmaz
    # Patron reddi geri alır → talep yeniden onay bekler → panelden onaylar
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_X}")
    assert f'action="/panel/konusma/{NUMARA_X}/kayit_geri_al"'.encode() in h
    assert c.git("POST", f"/panel/konusma/{NUMARA_X}/kayit_geri_al", {"csrf": csrf, "talep": str(t["id"])})[0] == 302
    t3 = talep_satiri(depo)
    assert (t3["durum"], t3["karar_kaynagi"], t3["karar_zamani"]) == ("onay_bekliyor", None, None)
    assert c.git("POST", f"/panel/konusma/{NUMARA_X}/kayit_onay", {"csrf": csrf, "talep": str(t["id"])})[0] == 302
    b = depo.bayi_oku(NUMARA_X)
    assert (b["ad"], b["kaynak"], b["aktif"]) == ("Ahmet Yılmaz", "whatsapp", True)
    k = tek(depo, "SELECT kaynak, alici, satir FROM giden WHERE kind = 'template' AND alici = %s", NUMARA_X)
    assert k["kaynak"] == "panel" and k["satir"]["sablon_anahtari"] == "sablon_bayi_karsilama"
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_X}")
    assert "kayit_onay".encode() not in h and "Bayi: <b>Ahmet Yılmaz</b>".encode() in h


def test_reddi_geri_al_kart_ya_da_acik_talep_varsa_olmaz(app, acik, depo):
    talep_sonu(app)
    t = talep_satiri(depo)
    depo.kayit_karari_yaz(t["id"], "red")
    with depo.baglan() as c:
        c.execute("UPDATE kayit_talepleri SET karar_zamani = now() - interval '31 days'")
    assert yaz(app, NUMARA_X, "merhaba") == {"kayit:ad+cevap": 1}                 # 30 gün geçti: yeni açık talep
    assert depo.kayit_reddi_geri_al(t["id"]) is None                            # açık talep varken eskisi geri alınmaz
    depo.bayi_yaz(NUMARA_Z, ad="Z", rol="bayi")
    assert depo.kayit_reddi_geri_al(999999) is None


# ───────────────────────── konuşma dökümü (Patron'un baktığı çıktı; CIO 29.10: metinler kapanış dökümünde gösterilir) ─────────────────────────
def _dokum(depo, numaralar: dict) -> list[tuple[str, str, str, str]]:
    """(kimden, kime, metin, düğmeler) sırayla: gelen mesajlar ve Meta'nın kabul ettiği giden satırlar (aynı işlemde yazılan cevap gelen
    mesajdan sonra, sıra numarasıyla). Numaralar yalnız rol adıyla yazılır."""
    satirlar = sorgu(depo, "SELECT * FROM ("
                     " SELECT alindi AS t, 0 AS yon, 0 AS sira, gonderen AS kim, '' AS kime, metin, ham AS veri FROM mesajlar"
                     " UNION ALL"
                     " SELECT olusturuldu, 1, sira, '', coalesce(alici_cozuldu, alici), govde, satir FROM giden WHERE durum = 'kabul_edildi'"
                     ") x ORDER BY t, yon, sira")
    out = []
    for r in satirlar:
        v = r["veri"] or {}
        if r["yon"] == 0:
            dugme = f"[{v.get('text')}]" if v.get("reply_id") else ""
            out.append((numaralar.get(r["kim"], r["kim"]), "Portman", "" if dugme else r["metin"], dugme))
            continue
        if v.get("kind") == "template":
            d = [f"[{x.get('text') or {S.BILGI_NASIL: 'Nasıl çalışır?'}.get(x.get('payload'), x.get('payload'))}]" for x in (v.get("sablon") or {}).get("dugmeler") or []]
            out.append(("Portman", numaralar.get(r["kime"], r["kime"]), f"(şablon {v['sablon_anahtari']}) {r['metin']}", " ".join(d)))
        elif v.get("kind") == "interactive":
            d = [f"[{b['reply']['title']}]" for b in v["interactive"]["action"]["buttons"]]
            out.append(("Portman", numaralar.get(r["kime"], r["kime"]), r["metin"], " ".join(d)))
        elif v.get("kind") == "document":
            out.append(("Portman", numaralar.get(r["kime"], r["kime"]), f"(PDF {v.get('filename')}) {r['metin']}", ""))
        else:
            out.append(("Portman", numaralar.get(r["kime"], r["kime"]), r["metin"], ""))
    return out


def _gonder(depo):
    from sahte_meta import SahteMeta
    g = _gonderen(depo, SahteMeta(), AYAR_G)
    for _ in range(3):
        G.tur(depo, g, g.istemci, W.KANAL, AYAR_G)


def test_konusma_dokumu_onay_ve_red(app, acik, depo, llmsiz, tmp_path):
    """Rehber §9'un üç adımı sahte WhatsApp'ta baştan sona; döküm beklenen metinlerle kıyaslanır. PM_KAYIT_DOKUM verilirse Markdown yazılır."""
    import os
    roller = {NUMARA_X: "Bayi A", NUMARA_Z: "Bayi B", NUMARA_P: "Patron"}
    yaz(app, NUMARA_P, "Günaydın")                                           # Patron'un 24 saat penceresi açık
    with depo.baglan() as c:
        c.execute("UPDATE isler SET durum = 'bitti' WHERE gonderen = %s", (NUMARA_P,))
    talep_sonu(app, NUMARA_X, "Ahmet Yılmaz", "Yılmaz Yapı")
    _gonder(depo)
    t = talep_satiri(depo)
    ctx = tek(depo, "SELECT dis_id FROM giden WHERE mesaj_id = %s AND kind = 'interactive'", t["son_mesaj_id"])["dis_id"]
    post(app, yuk([dugme(NUMARA_P, f"kayit:onay:{t['id']}", "Onayla", ctx=ctx)]))
    isle_hepsi(depo)
    _gonder(depo)
    kw = tek(depo, "SELECT dis_id FROM giden WHERE alici = %s AND kind = 'template'", NUMARA_X)["dis_id"]
    nasil = {"id": "wamid.KBNASIL", "from": NUMARA_X, "timestamp": str(int(time.time())), "type": "button", "context": {"id": kw},
             "button": {"text": "Nasıl çalışır?", "payload": S.BILGI_NASIL}}
    post(app, yuk([nasil]))
    isle_hepsi(depo)
    _gonder(depo)
    d = _dokum(depo, roller)
    tid = t["id"]
    beklenen = [
        ("Patron", "Portman", "Günaydın", ""),
        ("Bayi A", "Portman", "merhaba", ""), ("Portman", "Bayi A", KY.SORU_AD, ""),
        ("Bayi A", "Portman", "Ahmet Yılmaz", ""), ("Portman", "Bayi A", KY.SORU_FIRMA, ""),
        ("Bayi A", "Portman", "Yılmaz Yapı", ""), ("Portman", "Bayi A", KY.TESEKKUR, ""),
        ("Portman", "Patron", f"Portman kayıt talebi KAYIT-{tid}: Ahmet Yılmaz · Yılmaz Yapı · kod B0777. Onaylarsanız bayi kartı açılır ve bayiye "
                              "karşılama şablonu gider.", "[Onayla] [Reddet]"),
        ("Patron", "Portman", "", "[Onayla]"),
        ("Portman", "Patron", "Kayıt açıldı: B0777 · Ahmet Yılmaz · Yılmaz Yapı. Bayiye karşılama şablonu gidiyor; hitap ve bölgeyi panelden "
                              "yazabilirsiniz.", ""),
        ("Portman", "Bayi A", "(şablon sablon_bayi_karsilama) " + S.sablon_metni(S.BAYI_KARSILAMA["metin"], ["Ahmet Yılmaz"]), "[Nasıl çalışır?]"),
        ("Bayi A", "Portman", "", "[Nasıl çalışır?]"),
    ]
    assert d[:len(beklenen)] == beklenen
    assert d[len(beklenen)][2].startswith("(PDF Portman_Nasil_calisir.pdf)") and d[len(beklenen) + 1][2] == W.NASIL_TALEP
    # red yolu: ikinci numara
    talep_sonu(app, NUMARA_Z, "Ayşe Kaya", "Kaya İnşaat")
    _gonder(depo)
    t2 = talep_satiri(depo, NUMARA_Z)
    ctx2 = tek(depo, "SELECT dis_id FROM giden WHERE mesaj_id = %s AND kind = 'interactive'", t2["son_mesaj_id"])["dis_id"]
    post(app, yuk([dugme(NUMARA_P, f"kayit:red:{t2['id']}", "Reddet", ctx=ctx2)]))
    isle_hepsi(depo)
    _gonder(depo)
    yaz(app, NUMARA_Z, "Neden olmadı?")
    _gonder(depo)
    d2 = _dokum(depo, roller)[len(d):]
    assert [x[2] for x in d2 if x[1] == "Bayi B"] == [KY.SORU_AD, KY.SORU_FIRMA, KY.TESEKKUR, KY.RED_BAYIYE, CEVAP]
    assert [x[2][:16] for x in d2 if x[1] == "Patron"] == ["Portman kayıt ta", "Kayıt reddedildi"]
    hedef = os.environ.get("PM_KAYIT_DOKUM")
    if hedef:
        def tablo(rows):
            return ["| # | Kimden | Kime | Mesaj | Düğmeler |", "|---|---|---|---|---|"] + [
                f"| {i} | {a} | {b} | {m.replace('|', '/')} | {du} |" for i, (a, b, m, du) in enumerate(rows, 1)]
        metin_ = (["# WhatsApp'tan bayi kaydı · konuşma dökümü (sahte WhatsApp)", "",
                   "Üretim: `testler/kalici/test_bayi_kaydi.py::test_konusma_dokumu_onay_ve_red` (PM_KAYIT_DOKUM). Numaralar ve kişiler deneme "
                   "verisidir; Meta'ya giden mesajlar sahte Graph API'ye gitti. Yalnız Meta'nın kabul ettiği mesajlar yazılır (Patron'un penceresi "
                   "açık olduğu için ücretli Patron şablonu gitmedi).", "", "## Onay yolu", ""] + tablo(d) + ["", "## Red yolu", ""] + tablo(d2)
                  + ["", f"Dökümde görünmeyen metinler: \"{KY.ONAY_BEKLIYOR}\" (onay beklerken 24 saatte bir), \"{KY.SORU_AD_YENIDEN}\" ve "
                     f"\"{KY.SORU_FIRMA_YENIDEN}\" (geçersiz cevapta).", "",
                     "Patron'un 24 saat penceresi kapalıysa düğmeli mesaj Meta'ya gitmez; yerine onaylı Patron şablonu gider ("
                     f"\"{S.sablon_metni(S.PATRON_BILDIRIM['metin'], ['B0777', f'KAYIT-{tid}'])}\", düğmesi paneldeki konuşma sayfası) ve karar "
                     "panelden verilir (sahte WhatsApp uçtan uca testi bölüm 13)."])
        from pathlib import Path
        Path(hedef).write_text("\n".join(metin_) + "\n", encoding="utf-8")
