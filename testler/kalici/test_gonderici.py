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


NUMARA_T = "900000000905"            # kuru koşu test kartı (rol=test; gerçek numara değil)


def test_test_karti_satirlari_her_zaman_tutulur_gercek_bayi_gider(depo, gonderen, meta):
    """BK-07 S3: dry_run kapalıyken bile test kartından doğan satırlar (bayi cevabı, PATRON metni ve şablonu) ve panelden karta
    yazılan satır 'test_karti' ile tutulur; Meta'ya ne mesaj ne medya gider. Aynı turda gerçek bayinin satırı gider."""
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.bayi_yaz(NUMARA_T, ad="Kuru Koşu", kod="TEST", rol="test")
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    depo.mesaj_kaydet(patron_mesaji("buradayım", talep("selam", "selam"), ts=time.time() - 60)); isle_hepsi(depo)
    tur(depo, gonderen); meta.istekler.clear()
    # test kartı: yönlendirme (P8501 kodlanmamış) → karta metin + PATRON metni + PATRON şablonu; hepsi tutulur
    gt = mesaj("P8501 olsun", talep(ozet="P8501", katalog_kodu="P8501"), numara=NUMARA_T, bayi=depo.gelen_bayisi(NUMARA_T))
    depo.mesaj_kaydet(gt); isle_hepsi(depo)
    # panelden karta yazılan satır da tutulur
    p = W.giden_metin(gt, "Panelden: deneme", 101); p["kaynak"] = "panel"
    p_id = _satir_ekle(depo, gt["id"], p, kaynak="panel")
    # gerçek bayi aynı turda: gider
    ga = mesaj("merhaba", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A))
    depo.mesaj_kaydet(ga); isle_hepsi(depo)
    gonderen.ayar_oku = lambda: AYAR_SABLON                                                        # dry_run False, şablon adları tanımlı
    say = G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    assert "tutuldu" not in say and say["kabul_edildi"] == 1 and say["belirsiz"] == 0
    t_rows = sorgu(depo, "SELECT alici, kind, durum, hata FROM giden WHERE mesaj_id = %s ORDER BY sira", gt["id"])
    assert len(t_rows) >= 4 and {r["alici"] for r in t_rows} == {NUMARA_T, "PATRON"}
    assert all(r["durum"] == "gonderilmedi" and r["hata"].startswith("Gönderilmedi: test_karti") for r in t_rows)
    assert tek(depo, "SELECT durum, hata FROM giden WHERE id = %s", p_id)["hata"].startswith("Gönderilmedi: test_karti")
    assert tek(depo, "SELECT durum FROM giden WHERE mesaj_id = %s", ga["id"])["durum"] == "kabul_edildi"
    assert [y["to"] for y in meta.gidenler()] == [NUMARA_A]                                       # Patron'a ve karta hiçbir şey gitmedi
    assert not any("/media" in i["url"] for i in meta.istekler)                                    # medya yüklemesi yok


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


# ───────────────────────── İE-07: şablon satırları ve panel satırı ─────────────────────────
import sablonlar as S

AYAR_SABLON = {**AYAR_AC, "sablon_patron_bildirim": "portman_patron_bekliyor_v1", "sablon_bayi_dosyalar_hazir": "portman_dosyalar_hazir_v1"}


def _satir_ekle(depo, gelen_id: str, s: dict, kaynak: str = "ajan") -> str:
    """Test: isi_bitir'in yazdığı biçimde ek giden satırı (worker/panel yolu A6–A7'de; burada yalnız gönderici kuralları sınanır)."""
    from psycopg.types.json import Jsonb
    with depo.baglan() as c, c.transaction():
        is_id = c.execute("SELECT id FROM isler WHERE mesaj_id = %s", (gelen_id,)).fetchone()["id"]
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, satir, kaynak) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                  (s["id"], is_id, gelen_id, s["seq"], s["to"], s.get("tur") or "cevap", s.get("kind") or "text", s.get("body") or "", Jsonb(s), kaynak))
    return s["id"]


def _gonderen_sablon(depo, meta, ayar=None):
    a = M.MetaAyar(phone_number_id=PNID, access_token="t" * 40, app_secret="s" * 20, verify_token="v")
    g = G.GonderenMeta(depo, M.GraphIstemci(a, http=meta), W.KANAL, ayar_oku=lambda: ayar or AYAR_SABLON)
    return g


def _yonlendirme_satirlari(depo, bayi_msg_ts=None):
    """Bayi mesajı → yönlendirme (P8501 şablonu kodlanmamış): worker bayiye metin (1), Patron'a metin (2) ve Patron şablonu (3) yazar."""
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    g = mesaj("P8501 olsun", talep(ozet="P8501", katalog_kodu="P8501"), bayi=depo.gelen_bayisi(NUMARA_A), ts=bayi_msg_ts)
    depo.mesaj_kaydet(g); isle_hepsi(depo)
    rows = sorgu(depo, "SELECT id, kind FROM giden WHERE mesaj_id = %s AND alici = 'PATRON' ORDER BY sira", g["id"])
    assert [r["kind"] for r in rows] == ["text", "template"]
    return g, rows[0]["id"], rows[1]["id"]


def test_sablon_pencere_kapaliyken_gider_metin_duser(depo, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("eski", talep("selam", "selam"), ts=time.time() - 90000)); isle_hepsi(depo)   # Patron 25 saat önce yazdı
    g, metin_id, sab_id = _yonlendirme_satirlari(depo)
    gonderen = _gonderen_sablon(depo, meta)
    say = G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    assert tek(depo, "SELECT durum, hata FROM giden WHERE id = %s", metin_id)["hata"] == "Gönderilmedi: reply_window_closed"
    s = tek(depo, "SELECT durum, dis_id, alici_cozuldu FROM giden WHERE id = %s", sab_id)
    assert s["durum"] == "kabul_edildi" and s["alici_cozuldu"] == NUMARA_P and s["dis_id"].startswith("wamid.OUT")
    [y] = [y for y in meta.gidenler() if y["type"] == "template"]
    assert y["to"] == NUMARA_P and y["template"]["name"] == "portman_patron_bekliyor_v1" and y["template"]["language"] == {"code": "tr"}
    assert y["template"]["components"][0]["parameters"][0]["text"] == "TSTA"
    assert y["template"]["components"][1] == {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": f"konusma/{NUMARA_A}"}]}
    assert y["biz_opaque_callback_data"] == sab_id and say["kabul_edildi"] >= 1


def test_sablon_pencere_acikken_gereksiz_metin_gider(depo, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("buradayım", talep("selam", "selam"), ts=time.time() - 60)); isle_hepsi(depo)
    g, metin_id, sab_id = _yonlendirme_satirlari(depo)
    gonderen = _gonderen_sablon(depo, meta)
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", metin_id)["durum"] == "kabul_edildi"
    s = tek(depo, "SELECT durum, hata FROM giden WHERE id = %s", sab_id)
    assert s["durum"] == "gonderilmedi" and s["hata"].startswith("Gönderilmedi: sablon_gereksiz")
    assert not [y for y in meta.gidenler() if y["type"] == "template"]


def test_sablon_tanimsiz_sablon_yok_ve_gunlukte_numara_yok(depo, meta, capsys):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("eski", talep("selam", "selam"), ts=time.time() - 90000)); isle_hepsi(depo)
    g, metin_id, sab_id = _yonlendirme_satirlari(depo)
    gonderen = _gonderen_sablon(depo, meta, ayar=AYAR_AC)                 # şablon adı ayarda yok
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_AC)
    s = tek(depo, "SELECT durum, hata FROM giden WHERE id = %s", sab_id)
    assert s["durum"] == "gonderilmedi" and s["hata"].startswith("Gönderilmedi: sablon_yok (sablon_patron_bildirim)")
    assert not [y for y in meta.gidenler() if y["type"] == "template"]
    cikti = capsys.readouterr().out
    assert "şablon tanımsız" in cikti and NUMARA_P not in cikti and NUMARA_A not in cikti
    # ayar sonradan girilince aynı satır gönderilmez (gonderilmedi kesindir); yeni satır gider
    sab2 = S.patron_bildirim_satiri(g, 9, depo.gelen_bayisi(NUMARA_A), "PM-TSTA-20261011-1", None)
    sab2_id = _satir_ekle(depo, g["id"], sab2)
    gonderen2 = _gonderen_sablon(depo, meta)
    G.tur(depo, gonderen2, gonderen2.istemci, W.KANAL, AYAR_SABLON)
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", sab2_id)["durum"] == "kabul_edildi"
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", sab_id)["durum"] == "gonderilmedi"
    [y] = [y for y in meta.gidenler() if y["type"] == "template"]
    assert y["template"]["components"][0]["parameters"][1]["text"] == "PM-TSTA-20261011-1"


def test_sablon_gecersiz_degisken_gonderilmez_denenmez(depo, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("eski", talep("selam", "selam"), ts=time.time() - 90000)); isle_hepsi(depo)
    g, metin_id, sab_id = _yonlendirme_satirlari(depo)
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET satir = jsonb_set(satir, '{sablon,govde}', '[\"TSTA\", \"\"]') WHERE id = %s", (sab_id,))
    gonderen = _gonderen_sablon(depo, meta)
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    s = tek(depo, "SELECT durum, hata, deneme FROM giden WHERE id = %s", sab_id)
    assert s["durum"] == "gonderilmedi" and "template_invalid: body 2" in s["hata"] and s["deneme"] == 1
    assert not [y for y in meta.gidenler() if y["type"] == "template"]


def test_panel_satiri_penceresi_bayinin_son_mesajindan(depo, meta):
    """kaynak='panel' satırı bayinin son mesajına bağlıdır; pencere o mesajın değil, bayinin son gelen mesajının zamanıyla ölçülür."""
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A", kod="TSTA")
    eski = mesaj("merhaba", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A), ts=time.time() - 90000)
    depo.mesaj_kaydet(eski); isle_hepsi(depo)
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET durum = 'gonderilmedi', hata = 'test' WHERE mesaj_id = %s", (eski["id"],))
    p1 = W.giden_metin(eski, "Panelden: merhaba", 101); p1["kaynak"] = "panel"
    p1_id = _satir_ekle(depo, eski["id"], p1, kaynak="panel")
    gonderen = _gonderen_sablon(depo, meta)
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    assert tek(depo, "SELECT hata FROM giden WHERE id = %s", p1_id)["hata"] == "Gönderilmedi: reply_window_closed"
    # bayi şimdi yazdı: eski mesaja bağlı panel satırı da gider (pencere son gelenden), şablon satırı her durumda gider
    yeni = mesaj("buradayım", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A), ts=time.time() - 30)
    depo.mesaj_kaydet(yeni); isle_hepsi(depo)
    p2 = W.giden_metin(eski, "Panelden: tekrar", 102); p2["kaynak"] = "panel"
    p2_id = _satir_ekle(depo, eski["id"], p2, kaynak="panel")
    sab = S.bayi_dosyalar_hazir_satiri(yeni["id"], 101, NUMARA_A, depo.gelen_bayisi(NUMARA_A), "PM-TSTA-20261011-1")
    sab_id = _satir_ekle(depo, yeni["id"], sab, kaynak="panel")
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    assert tek(depo, "SELECT durum, alici_cozuldu FROM giden WHERE id = %s", p2_id) == {"durum": "kabul_edildi", "alici_cozuldu": NUMARA_A}
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", sab_id)["durum"] == "kabul_edildi"
    [y] = [y for y in meta.gidenler() if y["type"] == "template"]
    assert y["to"] == NUMARA_A and y["template"]["name"] == "portman_dosyalar_hazir_v1"
    assert y["template"]["components"][1]["parameters"] == [{"type": "payload", "payload": "dosya:PM-TSTA-20261011-1"}]
    # alıcı uyuşmazlığı panel satırında da yakalanır (bayinin mesajına başka numara bağlanamaz)
    p3 = W.giden_metin(eski, "yanlış alıcı", 103, to="900000000777"); p3["kaynak"] = "panel"
    p3_id = _satir_ekle(depo, eski["id"], p3, kaynak="panel")
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, AYAR_SABLON)
    assert tek(depo, "SELECT hata FROM giden WHERE id = %s", p3_id)["hata"] == "Gönderilmedi: recipient_mismatch"


def test_dry_run_sablonu_da_tutar(depo, meta):
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("eski", talep("selam", "selam"), ts=time.time() - 90000)); isle_hepsi(depo)
    g, metin_id, sab_id = _yonlendirme_satirlari(depo)
    gonderen = _gonderen_sablon(depo, meta)
    say = G.tur(depo, gonderen, gonderen.istemci, W.KANAL, {**AYAR_SABLON, "dry_run": True})
    assert say["tutuldu"] >= 2 and tek(depo, "SELECT hata FROM giden WHERE id = %s", sab_id)["hata"].startswith("dry_run") and meta.gidenler() == []


def test_sablon_metin_dustuyse_pencere_acik_olsa_da_gider_ve_dil_ayardan(depo, meta):
    """İnceleme düzeltmesi: 'sablon_gereksiz' yalnız eşlik eden metin satırı gerçekten gittiyse; metin belirsiz/gonderilmedi ise şablon gider. Dil ayardan."""
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    depo.mesaj_kaydet(patron_mesaji("buradayım", talep("selam", "selam"), ts=time.time() - 60)); isle_hepsi(depo)    # pencere açık
    g, metin_id, sab_id = _yonlendirme_satirlari(depo)
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET durum = 'belirsiz', hata = 'test: POST sonrası hata' WHERE id = %s", (metin_id,))
    ayar = {**AYAR_SABLON, "sablon_dil": "tr_TR"}
    gonderen = _gonderen_sablon(depo, meta, ayar=ayar)
    G.tur(depo, gonderen, gonderen.istemci, W.KANAL, ayar)
    assert tek(depo, "SELECT durum FROM giden WHERE id = %s", sab_id)["durum"] == "kabul_edildi"
    [y] = [y for y in meta.gidenler() if y["type"] == "template"]
    assert y["template"]["language"] == {"code": "tr_TR"} and y["template"]["name"] == "portman_patron_bekliyor_v1"
    # metin satırı hâlâ sıradaysa şablon bekler (YenidenDene), gönderilmez
    g2, metin2, sab2 = _yonlendirme_satirlari(depo)
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE giden SET durum = 'gonderiliyor', gonderim_basladi = now() WHERE id = %s", (metin2,))
    say = G.tur(depo, gonderen, gonderen.istemci, W.KANAL, ayar)
    assert tek(depo, "SELECT durum, hata FROM giden WHERE id = %s", sab2)["durum"] == "bekliyor" and say.get("yeniden") == 1
    assert len([y for y in meta.gidenler() if y["type"] == "template"]) == 1
