"""İE-06 · kanal/gonderici.py: Meta göndericisi (feature.php pm_kanal_send kuralları), medya yükleme ve yeniden deneme, belirsiz sonuç,
dry_run ve kapalı kanal, PATRON bildirimi ve 24 saat penceresi, gelen medya indirme, nabız. Gerçek Postgres, sahte Graph API."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import gonderici as G
import kalici
import meta_api as M
import nabiz as NB
import worker as W

PNID = "106000000000001"
NUMARA_P = "900000000909"
BAYI_P = {"kod": "PATRON", "ad": "Patron", "firma": "PortatifEv", "rol": "patron"}
AYAR_AC = {**AYAR, "enabled": True, "dry_run": False}


from sahte_meta import SahteMeta                                 # sahte Graph API (e2e ile ortak)


@pytest.fixture
def meta():
    return SahteMeta()


@pytest.fixture
def gonderen(depo, meta):
    ayar = M.MetaAyar(phone_number_id=PNID, access_token="t" * 40, app_secret="s" * 20, verify_token="v")
    istemci = M.GraphIstemci(ayar, http=meta)
    g = G.GonderenMeta(depo, istemci, W.KANAL, ayar_oku=lambda: AYAR_AC)
    g.istemci = istemci
    return g


def tur(depo, gonderen, ayar=AYAR_AC):
    return G.tur(depo, gonderen, gonderen.istemci, W.KANAL, ayar)


def patron_mesaji(metin_: str, cikarim: dict, ts=None, **ek) -> dict:
    g = mesaj(metin_, cikarim, numara=NUMARA_P, bayi=BAYI_P, ts=ts, **ek)
    g["role"] = "patron"
    return g


def isle_hepsi(depo, ayar=AYAR):
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


# ───────────────────────── metin, alıcı, kabul ─────────────────────────
def test_metin_gonderimi_alici_kabul_ve_nabiz(depo, gonderen, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("merhaba", talep("selam", "selam")))
    [r] = isle_hepsi(depo)
    say = tur(depo, gonderen)
    assert say["kabul_edildi"] == 1 and say["gonderilmedi"] == 0 and say["belirsiz"] == 0
    g = tek(depo, "SELECT dis_id, durum, alici_cozuldu, kabul_zamani FROM giden")
    assert g["dis_id"] == "wamid.OUT0001" and g["durum"] == "kabul_edildi" and g["alici_cozuldu"] == NUMARA_P and g["kabul_zamani"] is not None
    [y] = meta.gidenler()
    assert y["to"] == NUMARA_P and y["type"] == "text" and y["biz_opaque_callback_data"] == tek(depo, "SELECT id FROM giden")["id"]
    assert meta.istekler[0]["headers"]["Authorization"].startswith("Bearer ")
    n = NB.oku(W.KANAL, "gonderici")
    assert n and n["kabul_edildi"] == 1 and n["enabled"] is True and "medya" in n
    assert tur(depo, gonderen)["kabul_edildi"] == 0                                             # ikinci tur: gönderilecek yok


def test_patron_bildirimi_patron_numarasina_ve_penceresi(depo, gonderen, meta):
    # bayinin yazılı olmayan mesajı: bayiye cevap + Patron'a bildirim satırı (alici 'PATRON')
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    depo.mesaj_kaydet(mesaj("", talep("diger"), tur="image", bayi=depo.gelen_bayisi(NUMARA_A)))
    [r] = isle_hepsi(depo)
    assert {x["alici"] for x in sorgu(depo, "SELECT alici FROM giden")} == {"PATRON", NUMARA_A}
    say = tur(depo, gonderen)                                                                    # Patron kayıtlı değil: bildirim gönderilemez
    assert say["kabul_edildi"] == 1 and say["gonderilmedi"] == 1
    assert tek(depo, "SELECT hata FROM giden WHERE alici = 'PATRON'")["hata"] == "Gönderilmedi: recipient_unknown"
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(mesaj("", talep("diger"), tur="image", bayi=depo.gelen_bayisi(NUMARA_A)))
    isle_hepsi(depo)
    say = tur(depo, gonderen)                                                                    # Patron kayıtlı ama hiç yazmamış: pencere kapalı
    assert say["gonderilmedi"] == 1
    assert tek(depo, "SELECT hata FROM giden WHERE alici = 'PATRON' ORDER BY olusturuldu DESC LIMIT 1")["hata"] == "Gönderilmedi: reply_window_closed"
    depo.mesaj_kaydet(patron_mesaji("buradayım", talep("selam", "selam"), ts=time.time() - 60))
    isle_hepsi(depo)
    depo.mesaj_kaydet(mesaj("", talep("diger"), tur="image", bayi=depo.gelen_bayisi(NUMARA_A)))
    isle_hepsi(depo)
    say = tur(depo, gonderen)
    bildirim = tek(depo, "SELECT dis_id, alici_cozuldu, durum FROM giden WHERE alici = 'PATRON' ORDER BY olusturuldu DESC LIMIT 1")
    assert bildirim["durum"] == "kabul_edildi" and bildirim["alici_cozuldu"] == NUMARA_P and bildirim["dis_id"].startswith("wamid.OUT")
    assert any(y["to"] == NUMARA_P and y["type"] == "text" and "Portman" in y["text"]["body"] for y in meta.gidenler())


def test_pencere_kapali_alici_uyusmazligi_ve_kaynak_denetimi(depo, gonderen, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("eski", talep("selam", "selam"), ts=time.time() - 90000))
    isle_hepsi(depo)
    assert tur(depo, gonderen)["gonderilmedi"] == 1
    assert tek(depo, "SELECT hata FROM giden")["hata"] == "Gönderilmedi: reply_window_closed" and meta.gidenler() == []
    depo.mesaj_kaydet(patron_mesaji("yeni", talep("selam", "selam")))
    isle_hepsi(depo)
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET alici = %s WHERE durum = 'bekliyor'", (NUMARA_A,))
    assert tur(depo, gonderen)["gonderilmedi"] == 1
    assert tek(depo, "SELECT hata FROM giden WHERE alici = %s", NUMARA_A)["hata"] == "Gönderilmedi: recipient_mismatch"
    g = patron_mesaji("kaynak", talep("selam", "selam")); g["source"] = "başka"
    depo.mesaj_kaydet(g); isle_hepsi(depo)
    assert tur(depo, gonderen)["gonderilmedi"] == 1
    assert tek(depo, "SELECT hata FROM giden WHERE mesaj_id = %s", g["id"])["hata"] == "Gönderilmedi: inbox_not_verified"
    assert meta.gidenler() == []


# ───────────────────────── belge, görsel, etkileşim, yeniden deneme ─────────────────────────
def test_belge_yukleme_ve_yeniden_deneme(depo, gonderen, meta, hizli_motor):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("P6001 aynalı olsun", talep(ozet="P6001 aynalı", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}])))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri"
    say = tur(depo, gonderen)
    assert say["kabul_edildi"] == 2, say
    belge = tek(depo, "SELECT id, medya_id, dis_id, satir FROM giden WHERE kind = 'document'")
    assert belge["medya_id"] == "1001" and belge["dis_id"].startswith("wamid.OUT")
    yukleme = [i for i in meta.istekler if i["url"].endswith("/media")]
    assert len(yukleme) == 1 and b"%PDF-" in yukleme[0]["data"] and b'name="type"\r\n\r\napplication/pdf' in yukleme[0]["data"]
    [metin, belge_y] = meta.gidenler()
    assert belge_y["type"] == "document" and belge_y["document"]["id"] == "1001" and belge_y["document"]["filename"] == belge["satir"]["filename"]
    # yükleme hatası: ilk deneme satırı bekliyor'a döndürür, ikincisi gönderilmedi yapar; messages POST atılmaz
    meta.hatalar["media"] = True
    depo.mesaj_kaydet(patron_mesaji("P6001 düz", talep(ozet="P6001", katalog_kodu="P6001")))
    isle_hepsi(depo)
    say = tur(depo, gonderen)
    assert say["yeniden"] == 1
    d = tek(depo, "SELECT durum, deneme, medya_id, hata FROM giden WHERE kind = 'document' AND dis_id IS NULL")
    assert d["durum"] == "bekliyor" and d["deneme"] == 1 and d["medya_id"] is None and "bir kez daha" in d["hata"]
    say = tur(depo, gonderen)
    assert say["gonderilmedi"] == 1
    d = tek(depo, "SELECT durum, deneme, hata FROM giden WHERE kind = 'document' AND dis_id IS NULL")
    assert d["durum"] == "gonderilmedi" and d["deneme"] == 2 and d["hata"].startswith("Yükleme/doğrulama başarısız")
    assert len(meta.gidenler()) == 3                                                               # metin satırları gitti, belge gitmedi


def test_etkilesimli_baslik_gorseli_ve_pdf(depo, gonderen, meta, hizli_motor):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    katman = {**AYAR, "mesaj_katmani": True, "test_adaylari": True}
    depo.mesaj_kaydet(patron_mesaji("TEST01 olsun", talep(ozet="TEST01", katalog_kodu="TEST01")))
    [r] = isle_hepsi(depo, katman)
    assert r["eylem"] == "is_emri"
    say = tur(depo, gonderen, {**katman, "enabled": True, "dry_run": False})
    assert say["kabul_edildi"] == 2, say
    y = meta.gidenler()
    assert [x["type"] for x in y] == ["interactive", "document"]
    assert y[0]["interactive"]["header"] == {"type": "image", "image": {"id": "1001"}} and y[1]["document"]["id"] == "1002"
    assert [b["reply"]["title"] for b in y[0]["interactive"]["action"]["buttons"]] == ["Onayla", "Revize et"]
    assert y[0]["interactive"]["footer"]["text"].endswith("r01")
    yuklemeler = [i for i in meta.istekler if i["url"].endswith("/media")]
    assert b"\x89PNG" in yuklemeler[0]["data"] and b"%PDF-" in yuklemeler[1]["data"]


def test_etkilesim_siniri_asan_satir_gonderilmez_denenmez(depo, gonderen, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    g = patron_mesaji("x", talep("selam", "selam")); depo.mesaj_kaydet(g); isle_hepsi(depo)
    satir = W.giden_etkilesim(g, "Seçin", 1, butonlar=[(f"b{i}", f"B{i}") for i in range(3)])
    satir["interactive"]["action"]["buttons"].append({"type": "reply", "reply": {"id": "b4", "title": "B4"}})     # 4 buton: sınır dışı
    with depo.baglan() as c, c.transaction():
        from psycopg.types.json import Jsonb
        c.execute("UPDATE giden SET kind = 'interactive', satir = %s WHERE mesaj_id = %s", (Jsonb(satir), g["id"]))
    say = tur(depo, gonderen)
    assert say["gonderilmedi"] == 1 and say["yeniden"] == 0 and meta.gidenler() == []
    assert "interactive_invalid: buttons" in tek(depo, "SELECT hata FROM giden")["hata"]


def test_messages_post_hatasi_ve_bozuk_cevap_belirsiz(depo, gonderen, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("a", talep("selam", "selam"))); isle_hepsi(depo)
    meta.hatalar["messages"] = True
    assert tur(depo, gonderen)["belirsiz"] == 1
    h = tek(depo, "SELECT durum, hata, deneme FROM giden")
    assert h["durum"] == "belirsiz" and "HTTP 500" in h["hata"] and h["deneme"] == 1
    assert tur(depo, gonderen)["belirsiz"] == 0                                                   # belirsiz satır yeniden denenmez
    meta.hatalar.clear(); meta.cevap_bozuk = True
    depo.mesaj_kaydet(patron_mesaji("b", talep("selam", "selam"))); isle_hepsi(depo)
    assert tur(depo, gonderen)["belirsiz"] == 1
    assert "send_response_uncertain" in tek(depo, "SELECT hata FROM giden ORDER BY olusturuldu DESC LIMIT 1")["hata"]


def test_dry_run_ve_kapali_kanal(depo, gonderen, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("a", talep("selam", "selam"))); isle_hepsi(depo)
    say = tur(depo, gonderen, {**AYAR, "enabled": False, "dry_run": False})
    assert say["enabled"] is False and "kabul_edildi" not in say and tek(depo, "SELECT durum FROM giden")["durum"] == "bekliyor"
    say = tur(depo, gonderen, {**AYAR, "enabled": True, "dry_run": True})
    assert say["tutuldu"] == 1 and tek(depo, "SELECT durum, hata FROM giden")["hata"].startswith("dry_run")
    assert meta.gidenler() == []
    # gönderim sırasında kanal kapanırsa: POST atılmaz, satır bekliyor'a döner
    depo.mesaj_kaydet(patron_mesaji("b", talep("selam", "selam"))); isle_hepsi(depo)
    gonderen.ayar_oku = lambda: {**AYAR, "enabled": False}
    say = tur(depo, gonderen)
    assert say["yeniden"] == 1 and tek(depo, "SELECT durum FROM giden WHERE durum = 'bekliyor'") and meta.gidenler() == []


# ───────────────────────── gelen medya ─────────────────────────
def test_gelen_medya_indirilir_ve_hata_sayilir(depo, gonderen, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    g = patron_mesaji("kroki", talep("diger"), tur="image"); g["media_id"] = "777"
    depo.mesaj_kaydet(g); depo.gelen_dosya_ekle(g["id"], "777", "../../kroki ev.JPG", "image/jpeg")
    say = tur(depo, gonderen, {**AYAR, "enabled": False})
    assert say["medya"] == {"indirildi": 1, "hata": 0}
    d = tek(depo, "SELECT yol, mime, boyut, sha256, hata FROM gelen_dosyalar")
    p = Path(d["yol"])
    assert p.is_file() and p.read_bytes() == meta.medya_icerik and d["boyut"] == len(meta.medya_icerik) and d["mime"] == "image/jpeg"
    assert p.parent.parent == W.KANAL / "gelen_medya" and p.name == "kroki_ev.JPG"                  # yol kaçışı yok, ad temizlendi
    assert G.guvenli_ad(None, "application/pdf", "9") == "medya_9.pdf" and G.guvenli_ad("...", "image/png", "1") == "medya_1.png"
    g2 = patron_mesaji("belge", talep("diger"), tur="document"); g2["media_id"] = "778"
    depo.mesaj_kaydet(g2); depo.gelen_dosya_ekle(g2["id"], "778", "a.pdf", "application/pdf")
    meta.hatalar["indir"] = True
    for i in range(3):
        assert tur(depo, gonderen, {**AYAR, "enabled": False})["medya"] == {"indirildi": 0, "hata": 1}
    assert tur(depo, gonderen, {**AYAR, "enabled": False})["medya"] == {"indirildi": 0, "hata": 0}  # 3 denemeden sonra bırakılır
    d2 = tek(depo, "SELECT deneme, hata, yol FROM gelen_dosyalar WHERE medya_id = '778'")
    assert d2["deneme"] == 3 and d2["yol"] is None and "MetaHatasi" in d2["hata"] and "t" * 40 not in d2["hata"]
