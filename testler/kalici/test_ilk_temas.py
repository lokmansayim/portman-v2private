"""İE-08 8b · M4 (panelden ilk temas ve plansız bilgi), M5 (hitap) ve panelde mühendis kontrolleri (M2/M3: durum, Fiyat verildi).

M4: hiç yazmamış aktif bayi kartına "Karşılama" (başlangıç kaydı: pencere açmaz, konuşmada gelen mesaj gibi görünmez, gönderici yalnız
panel şablonunu gönderir); her aktif bayi kartına "Bilgi hazır"; test/Patron/mühendis kartı ve pasif kart kapalı. Bayinin "Nasıl
çalışır?" düğmesi → tek sayfa PDF (LLM'siz); "Bilgiyi gönder" → sabit cevap + Patron'a metin ve şablon. M5: LLM bağlamında ad ve hitap,
numara yok; selam hitapla. Gerçek Postgres, sahte Graph API; ağ, LLM ve WhatsApp yok.
"""
from __future__ import annotations

import time

import pytest

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek
from test_panel import DOGRU, Istemci, NUMARA_Y, _csrf_oturum, _gonderen, pn  # noqa: F401  (pn: fikstür)

import kalici
import sablonlar as S
import worker as W

AYAR_K = {**AYAR, "enabled": True, "dry_run": False, "sablon_bayi_karsilama": "portman_karsilama_v1",
          "sablon_bayi_bilgi_hazir": "portman_bilgi_hazir_v1", "sablon_patron_bildirim": "portman_patron_bekliyor_v1"}


def isle_hepsi(depo, ayar=AYAR):
    out = []
    while (r := kalici.bir_is(depo, ayar, "t")) is not None:
        out.append(r)
    return out


# ───────────────────────── M4 · panel ─────────────────────────
def test_karsilama_hic_yazmamis_karta_baslangic_kaydi_ve_gonderim(pn, depo):
    from sahte_meta import SahteMeta
    depo.bayi_yaz(NUMARA_Y, ad="Hiç Yazmamış", kod="HY", hitap="Mehmet Bey", rol="bayi")
    c = Istemci(pn); c.giris(DOGRU)
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_Y}")
    assert kod == 200 and f'action="/panel/konusma/{NUMARA_Y}/karsilama"'.encode() in h and f'action="/panel/konusma/{NUMARA_Y}/bilgi"'.encode() in h
    assert b'name="pdf"' not in h                                                       # metin/PDF formu yok (pencere yok)
    csrf = c.csrf(h)
    kod, _, b = c.git("POST", f"/panel/konusma/{NUMARA_Y}/karsilama", {"csrf": csrf})
    assert (kod, c.baslik(b, "Location")) == (302, [f"/panel/konusma/{NUMARA_Y}"])
    r = tek(depo, "SELECT g.sira, g.alici, g.kind, g.kaynak, g.satir, m.tur, m.kaynak AS mk, j.durum FROM giden g JOIN mesajlar m ON m.id = g.mesaj_id "
                  "JOIN isler j ON j.id = g.is_id")
    assert (r["sira"], r["alici"], r["kind"], r["kaynak"], r["tur"], r["mk"], r["durum"]) == (101, NUMARA_Y, "template", "panel", "panel_ilk_temas", "panel", "bitti")
    assert r["satir"]["sablon_anahtari"] == "sablon_bayi_karsilama" and r["satir"]["sablon"]["govde"] == ["Mehmet Bey"]
    assert r["satir"]["sablon"]["dugmeler"] == [{"sub_type": "quick_reply", "index": 0, "payload": S.BILGI_NASIL}]
    assert r["satir"]["body"] == S.sablon_metni(S.BAYI_KARSILAMA["metin"], ["Mehmet Bey"])
    # başlangıç kaydı pencere açmaz, panelin metin çapası olmaz, konuşmada gelen mesaj gibi görünmez
    assert depo.son_gelen_zamani(NUMARA_Y) is None and depo.son_gelen_mesaj(NUMARA_Y) is None
    assert not [m for m in depo.konusma_mesajlari(NUMARA_Y) if m["yon"] == "gelen"]
    assert c.git("POST", f"/panel/konusma/{NUMARA_Y}/gonder", {"csrf": csrf, "metin": "selam"})[0] == 400
    # gönderici: başlangıç kaydına bağlı panel şablonu gider (pencere kapalı; utility)
    meta = SahteMeta(); g = _gonderen(depo, meta, AYAR_K)
    import gonderici as G
    G.tur(depo, g, g.istemci, W.KANAL, AYAR_K)
    s = tek(depo, "SELECT durum, alici_cozuldu FROM giden")
    assert s["durum"] == "kabul_edildi" and s["alici_cozuldu"] == NUMARA_Y
    [y] = meta.gidenler()
    assert y["to"] == NUMARA_Y and y["template"]["name"] == "portman_karsilama_v1"


def test_gonderici_baslangic_kaydina_metin_gondermez(pn, depo):
    """Başlangıç kaydına bağlı şablon dışı satır (ör. elle yazılmış metin) gerçek gelen mesaj olmadığı için gönderilmez."""
    from sahte_meta import SahteMeta
    import gonderici as G
    depo.bayi_yaz(NUMARA_Y, ad="Hiç Yazmamış", kod="HY", rol="bayi")
    depo.ilk_temas_ekle(NUMARA_Y, lambda g, n: W.giden_metin(g, "metin", n))
    meta = SahteMeta(); g = _gonderen(depo, meta, AYAR_K)
    G.tur(depo, g, g.istemci, W.KANAL, AYAR_K)
    s = tek(depo, "SELECT durum, hata FROM giden")
    assert s["durum"] == "gonderilmedi" and "test_cannot_send" in s["hata"] and meta.gidenler() == []
    assert G.ILK_TEMAS_KAYNAGI == depo.ILK_TEMAS_KAYNAGI


def test_karsilama_yazmis_karta_kapali_bilgi_hazir_son_mesaja_baglanir(pn, depo):
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"], hitap="", rol="bayi")
    assert depo.mesaj_kaydet(mesaj("merhaba", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A))); isle_hepsi(depo)
    c = Istemci(pn); c.giris(DOGRU)
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_A}")
    assert f"/panel/konusma/{NUMARA_A}/karsilama".encode() not in h and f"/panel/konusma/{NUMARA_A}/bilgi".encode() in h
    csrf = c.csrf(h)
    kod, h, _ = c.git("POST", f"/panel/konusma/{NUMARA_A}/karsilama", {"csrf": csrf})
    assert kod == 400 and "yalnız hiç yazmamış karta".encode() in h
    assert c.git("POST", f"/panel/konusma/{NUMARA_A}/bilgi", {"csrf": csrf})[0] == 302
    r = tek(depo, "SELECT g.sira, g.satir, m.tur FROM giden g JOIN mesajlar m ON m.id = g.mesaj_id WHERE g.kind = 'template'")
    assert r["sira"] == 101 and r["tur"] == "text" and r["satir"]["sablon_anahtari"] == "sablon_bayi_bilgi_hazir"
    assert r["satir"]["sablon"]["govde"] == [BAYI_A["ad"]] and r["satir"]["sablon"]["dugmeler"][0]["payload"] == S.BILGI_HAZIR


@pytest.mark.parametrize("rol,aktif", [("test", True), ("patron", True), ("muhendis", True), ("bayi", False)])
def test_ilk_temas_test_patron_muhendis_ve_pasif_kartta_kapali(pn, depo, rol, aktif):
    depo.bayi_yaz(NUMARA_Y, ad="Kart", kod="KK", rol=rol, aktif=aktif)
    c = Istemci(pn); c.giris(DOGRU)
    csrf = _csrf_oturum(c)
    for islem in ("karsilama", "bilgi"):
        kod, h, _ = c.git("POST", f"/panel/konusma/{NUMARA_Y}/{islem}", {"csrf": csrf})
        assert kod == 400 and "Şablon gönderilemez".encode() in h
    assert c.git("GET", f"/panel/konusma/{NUMARA_Y}/karsilama")[0] == 405
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 0


# ───────────────────────── M4 · bayinin düğmeleri ─────────────────────────
def _dugme(reply_id: str) -> dict:
    g = mesaj(reply_id, talep("diger", "x"), tur="interactive", bayi={**BAYI_A, "numara": NUMARA_A})
    g["reply_id"] = reply_id; g["reply_kind"] = "button_reply"
    return g


def test_nasil_calisir_dugmesi_tek_sayfa_pdf_llmsiz(depo):
    import fitz
    g = _dugme(S.BILGI_NASIL)
    assert depo.mesaj_kaydet(g); [r] = isle_hepsi(depo)
    assert r["gerekce"] == "şablon cevabı: nasıl çalışır"
    rows = sorgu(depo, "SELECT kind, alici, dosya, satir FROM giden WHERE mesaj_id = %s ORDER BY sira", g["id"])
    assert [x["kind"] for x in rows] == ["document", "text"] and all(x["alici"] == NUMARA_A for x in rows)
    pdf = rows[0]
    assert "/projects/bilgi/" in pdf["dosya"] and pdf["satir"]["filename"] == "Portman_Nasil_calisir.pdf"
    d = fitz.open(pdf["dosya"])
    assert d.page_count == 1 and "Nasıl çalışır" in d[0].get_text() and "Ç8801" in d[0].get_text()
    assert not sorgu(depo, "SELECT 1 FROM giden WHERE alici = 'PATRON'")
    d0, _ = depo.konusma_oku(NUMARA_A)
    assert (d0 or {}).get("asama") in (None, "bos") and not (d0 or {}).get("gecmis")     # konuşma durumu değişmedi
    # aynı metin → aynı dosya (yeniden yazılmaz)
    yol, sha = W.nasil_calisir_pdf()
    assert str(yol) == pdf["dosya"] and sha == pdf["satir"]["sha256"]


def test_bilgiyi_gonder_dugmesi_sabit_cevap_patrona_metin_ve_sablon(depo):
    g = _dugme(S.BILGI_HAZIR)
    assert depo.mesaj_kaydet(g); [r] = isle_hepsi(depo)
    assert r["gerekce"] == "şablon cevabı: bilgi penceresi açıldı"
    rows = sorgu(depo, "SELECT kind, alici, govde, satir FROM giden WHERE mesaj_id = %s ORDER BY sira", g["id"])
    assert (rows[0]["alici"], rows[0]["govde"]) == (NUMARA_A, S.BAYI_BILGI_CEVABI)
    assert [(x["alici"], x["kind"]) for x in rows[1:]] == [("PATRON", "text"), ("PATRON", "template")]
    assert NUMARA_A not in rows[1]["govde"] and rows[2]["satir"]["pencere_kapaliysa"] is True


# ───────────────────────── M5 · hitap ─────────────────────────
def test_llm_baglaminda_ad_ve_hitap_numara_yok(monkeypatch):
    from beyin import llm
    from beyin.konusma import BellekKonusma
    gorulen = []
    monkeypatch.setattr(llm, "cikar_guvenli", lambda metin, baglam, **k: gorulen.append(baglam) or (None, {}))
    ayar = {"llm": {"backend": "anthropic"}}
    W.cikar({"text": "merhaba", "bayi": {"ad": "Deneme Bayi A", "hitap": "Ahmet Bey", "numara": NUMARA_A}}, ayar, BellekKonusma(NUMARA_A, None))
    W.cikar({"text": "merhaba", "bayi": {"ad": NUMARA_A, "hitap": "", "numara": NUMARA_A}}, ayar, BellekKonusma(NUMARA_A, None))
    W.cikar({"text": "merhaba", "bayi": None}, ayar, BellekKonusma(NUMARA_A, None))
    assert gorulen[0] == "bayi: Deneme Bayi A, hitap: Ahmet Bey" and gorulen[1] == "" and gorulen[2] == ""
    assert all(NUMARA_A not in b for b in gorulen)


def test_selam_hitapla_ad_numaraya_dusmusse_numara_yazilmaz(depo):
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"], hitap="Ahmet Bey", rol="bayi")
    g = mesaj("merhaba", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A))
    assert depo.mesaj_kaydet(g); isle_hepsi(depo)
    assert tek(depo, "SELECT govde FROM giden WHERE mesaj_id = %s", g["id"])["govde"].startswith("Merhaba Ahmet Bey. Hangi model")
    depo.bayi_yaz(NUMARA_A, ad="", kod=BAYI_A["kod"], hitap="", rol="bayi")               # ad boş → gelen_bayisi adı numaraya düşürür
    time.sleep(1.1)
    g2 = mesaj("selam", talep("selam", "selam"), bayi=depo.gelen_bayisi(NUMARA_A))
    assert depo.mesaj_kaydet(g2); isle_hepsi(depo)
    govde = tek(depo, "SELECT govde FROM giden WHERE mesaj_id = %s", g2["id"])["govde"]
    assert govde.startswith("Merhaba. Hangi model") and NUMARA_A not in govde


# ───────────────────────── panel · mühendis kontrolleri (M2/M3) ─────────────────────────
def test_panel_kontrol_tablosu_fiyat_verildi_ve_gonderim_durdurur(pn, depo, wa, monkeypatch):
    from motor.genel import uret
    import test_muhendis as TM
    monkeypatch.setattr(uret, "uret", TM.sahte_genel_liste)
    TM.muhendis_karti(depo)
    rev = TM.celik_onay(depo, wa); no = rev["is_emri_no"]
    TM.muhendis_isle(depo, TM.muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))
    k = depo.muhendis_kontrolu(no, 1)
    c = Istemci(pn); c.giris(DOGRU)
    kod, h, _ = c.git("GET", "/panel/")
    assert kod == 200 and "Mühendis kontrolleri".encode() in h and "mühendis onayladı".encode() in h and "fiyat bekleniyor (hatırlatma 0/3)".encode() in h
    assert f'action="/panel/kontrol/{k["id"]}/fiyat"'.encode() in h and NUMARA_A.encode() in h        # bağlantı konuşma sayfasına (panel içi)
    assert c.git("GET", f"/panel/kontrol/{k['id']}/fiyat")[0] == 405
    csrf = c.csrf(h)
    kod, _, b = c.git("POST", f"/panel/kontrol/{k['id']}/fiyat", {"csrf": csrf})
    assert (kod, c.baslik(b, "Location")) == (302, ["/panel/"]) and depo.muhendis_kontrolu(no, 1)["patron_durum"] == "fiyat_verildi"
    # konuşma sayfasında da tablo var; ikinci kontrol yokken panelden gönderim durdurur (yeni bekleyen kontrol açıp sınar)
    with depo.baglan() as cn, cn.transaction():
        cn.execute("UPDATE muhendis_kontrolleri SET patron_durum = 'bekliyor'")
    kod, h, _ = c.git("GET", f"/panel/konusma/{NUMARA_A}")
    assert "Mühendis kontrolleri".encode() in h
    assert c.git("POST", f"/panel/konusma/{NUMARA_A}/gonder", {"csrf": csrf, "metin": "Fiyatınız: …"})[0] == 302
    assert depo.muhendis_kontrolu(no, 1)["patron_durum"] == "durdu"
