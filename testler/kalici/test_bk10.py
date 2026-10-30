"""BK-10 · 8b sonrası küçük işler (docs/is_emirleri/BK-10.md): mühendis tarafı. Kalıcı akış, gerçek Postgres, sahte genel motor ve WhatsApp.

  - DXF belgesinin açıklamasında ".txt'yi silin" notu (WhatsApp DXF'i düz metin olarak taşır).
  - Karardan ("Patron'a gönder") sonra gelen Excel son karara yeni liste sürümü olarak bağlanır, Patron'a gider; 24 saatten eskiye bağlanmaz.
  - Panelde kontrol satırında Excel indirme bağlantıları (sunucunun listesi, mühendisin indirilen sürümleri).
  - Rehber §4: bayi onaydan sonra yeni revizyon isterse karar bekleyen kontrol 'plan_degisti' olur, mühendise yazılır; karar Patron'a
    ulaşmışsa Patron'a söylenir, fiyat hatırlatması durur; her kontrol bir kez.
  - D-19 (a): kontrol açıldıktan 24 saat sonra karar yoksa 'zaman_asimi', Patron'a tek bildirim; panelden yeniden açılır.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_bk10.py -q
"""
from __future__ import annotations

import time

from conftest import NUMARA_A, sorgu, tek

import muhendis as MH
import panel as PN
from test_celik_akisi import revize
from test_muhendis import (BAYI_A, NUMARA_M, _cipa, _excel_gonder, celik_onay, genel_liste, isle_hepsi, muhendis_isle,  # noqa: F401
                           muhendis_karti, muhendis_mesaji, saat, satirlar)
from test_panel import DOGRU, SIR, Istemci


def panel_istemcisi(depo, kanal_dizini) -> Istemci:
    c = Istemci(PN.Panel(depo=depo, veri=kanal_dizini, sir=SIR, parola=PN.parola_ozeti(DOGRU), ayar_oku=dict))
    assert c.giris(DOGRU)[0] == 302
    return c

PENCERE = {"pencereler": [{"mahal": "mutfak", "olcu": "120x120", "islem": "degistir"}]}


def _kontrol_zamani(depo, no: str, **alan) -> None:
    with depo.baglan() as c, c.transaction():
        for a, v in alan.items():
            c.execute(f"UPDATE muhendis_kontrolleri SET {a} = to_timestamp(%s) WHERE is_emri_no = %s", (v, no))


# ───────────────────────── DXF notu ─────────────────────────
def test_dxf_aciklamasinda_txt_notu(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    g = muhendis_mesaji(reply_id=f"muh:gonder:{no}:1")
    muhendis_isle(depo, g)
    [dxf] = [s for s in satirlar(depo, g["id"]) if s.get("filename", "").endswith(".dxf")]
    assert dxf["body"].endswith(MH.DXF_NOTU) and ".txt'yi silin" in dxf["body"]
    assert not [s for s in satirlar(depo, g["id"]) if s.get("filename", "").endswith((".pdf", ".xlsx")) and ".txt" in s["body"]]


# ───────────────────────── geç gelen Excel ─────────────────────────
def test_karardan_sonra_gelen_excel_son_karara_baglanir_patrona_gider(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    assert muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))["gerekce"] == "mühendis onayladı: Patron'a gönderildi"
    r = _excel_gonder(depo, no)
    assert r["gerekce"] == "liste sürümü (karardan sonra): Patron'a", r
    k = depo.muhendis_kontrolu(no, 1)
    assert [(x["surum"], x["kaynak"]) for x in k["listeler"]] == [(2, "muhendis")]
    assert k["durum"] == "patrona_gonderildi" and k["patron_durum"] == "bekliyor"                    # karar ve fiyat beklentisi aynen
    ss = satirlar(depo, r["mesaj_id"])
    patron = [s for s in ss if s["_alici"] == "PATRON"]
    assert [s["kind"] for s in patron] == ["text", "template", "document"]
    assert "kararından sonra düzeltilmiş liste" in patron[0]["body"] and "sürüm 2" in patron[0]["body"] and NUMARA_A not in patron[0]["body"]
    assert patron[1]["sablon"]["govde"] == [BAYI_A["kod"], no] and patron[2]["file"].endswith("_s2.xlsx")
    assert ss[-1]["_alici"] == NUMARA_M and "Patron'a ilettim" in ss[-1]["body"]


def test_karardan_sonra_indirilmemis_excel_panelde_soylenir(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))
    r = _excel_gonder(depo, no, indir=False)
    patron = [s for s in satirlar(depo, r["mesaj_id"]) if s["_alici"] == "PATRON"]
    assert [s["kind"] for s in patron] == ["text", "template"] and "henüz indirilmedi; panelde" in patron[0]["body"]


def test_24_saatten_eski_karara_excel_baglanmaz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))
    _kontrol_zamani(depo, no, karar_zamani=time.time() - MH.ZAMAN_ASIMI_SN - 60)
    r = _excel_gonder(depo, no)
    assert r["gerekce"] == "dosya: açık kontrol yok" and depo.muhendis_kontrolu(no, 1)["listeler"] == []


# ───────────────────────── panelden Excel ─────────────────────────
def test_panelde_kontrol_satirinda_excel_baglantilari(depo, wa, genel_liste, kanal_dizini):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:gonder:{no}:1"))
    _excel_gonder(depo, no)
    k = depo.muhendis_kontrolu(no, 1)
    c = panel_istemcisi(depo, kanal_dizini)
    kod, govde, _ = c.git("GET", f"/panel/konusma/{NUMARA_A}")
    sayfa = govde.decode("utf-8")
    [d] = sorgu(depo, "SELECT id FROM gelen_dosyalar")
    assert kod == 200 and f'href="/panel/kontrol/{k["id"]}/liste"' in sayfa and f'href="/panel/dosya/{d["id"]}">s2 mühendis' in sayfa
    kod, veri, ek = c.git("GET", f"/panel/kontrol/{k['id']}/liste")
    ek = dict(ek)
    assert kod == 200 and ek["Content-Type"] == PN.XLSX and veri[:2] == b"PK" and f"Portman_{no}_r01_yukleme_listesi.xlsx" in ek["Content-Disposition"]
    assert c.git("GET", "/panel/kontrol/999999/liste")[0] == 404


# ───────────────────────── plan değişti ─────────────────────────
def test_onaydan_sonra_revizyon_karar_bekleyen_kontrolu_kapatir(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    r = revize(depo, "mutfak penceresi 120x120 olsun", **PENCERE)
    assert r["eylem"] == "is_emri", r
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "plan_degisti" and k["t_plan_degisti"] is not None
    [m] = [s for s in satirlar(depo, r["mesaj_id"]) if s["_alici"] == "MUHENDIS"]
    assert m["kind"] == "text" and "plan değişti" in m["body"] and f"{no} r01" in m["body"] and NUMARA_A not in m["body"]
    assert not [s for s in satirlar(depo, r["mesaj_id"]) if s["_alici"] == "PATRON"]            # karar yoktu: Patron'a gitmez
    assert sorgu(depo, "SELECT sonuc FROM isler WHERE mesaj_id = %s", r["mesaj_id"])[0]["sonuc"]["plan_degisti"] == [f"{no} r01"]
    # eski düğme: kontrol kapalı (dosya gönderilmez)
    g = muhendis_mesaji(reply_id=f"muh:gonder:{no}:1")
    assert muhendis_isle(depo, g)["gerekce"] == "kontrol kapalı (plan_degisti)"
    [s] = satirlar(depo, g["id"])
    assert s["kind"] == "text" and "bayi onaydan sonra planı değiştirdi" in s["body"]
    assert MH.hatirlatma_turu(depo, saat(14, 12))["muhendis"] == 0                                 # hatırlatma da durdu
    # bir sonraki revizyon aynı kontrolü yeniden bildirmez
    r3 = revize(depo, "dışlar 140'lık olsun")
    assert r3["eylem"] == "is_emri" and not [s for s in satirlar(depo, r3["mesaj_id"]) if s["_alici"] in ("MUHENDIS", "PATRON")]


def test_onaydan_sonra_revizyon_karar_patrondaysa_patrona_soylenir(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))
    r = revize(depo, "mutfak penceresi 120x120 olsun", **PENCERE)
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "patrona_gonderildi" and k["patron_durum"] == "durdu" and k["t_plan_degisti"] is not None
    ss = satirlar(depo, r["mesaj_id"])
    assert not [s for s in ss if s["_alici"] == "MUHENDIS"]
    p, sab = [s for s in ss if s["_alici"] == "PATRON"]
    assert "planı değiştirdi" in p["body"] and "Fiyat hatırlatması durdu" in p["body"] and NUMARA_A not in p["body"]
    assert sab["kind"] == "template" and sab["pencere_kapaliysa"] is True
    assert MH.hatirlatma_turu(depo, saat(14, 15))["patron"] == 0


def test_yeni_talep_ve_ilk_plan_kontrole_dokunmaz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    out = {"satirlar": [], "sonuc": {"eylem": "is_emri", "is_emri_no": "PM-X-1", "revizyon": 1}}
    MH.plan_degisti_kancasi(depo, {"id": "x", "sender": NUMARA_A}, {"proje_id": rev["proje_id"]}, out)
    assert out["satirlar"] == [] and "kontrol_guncelle" not in out
    assert depo.muhendis_kontrolu(no, 1)["durum"] == "bekliyor"


# ───────────────────────── D-19 (a): 24 saat ─────────────────────────
def test_24_saatte_karar_yoksa_zaman_asimi_patrona_tek_bildirim(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    acilis = saat(14, 10)
    _kontrol_zamani(depo, no, olusturuldu=acilis, sure_baslangici=acilis, son_hatirlatma=saat(15, 9), gecikme_bildirildi=saat(14, 13))
    assert MH.hatirlatma_turu(depo, saat(15, 9, 59))["zaman_asimi"] == 0                       # 24 saat dolmadı
    say = MH.hatirlatma_turu(depo, saat(15, 10))
    assert say["zaman_asimi"] == 1 and say["muhendis"] == 0 and say["gecikme"] == 0              # hatırlatma yerine kapanış
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "zaman_asimi" and k["t_zaman_asimi"] == saat(15, 10)
    p, sab = [s for s in _cipa(depo, rev) if s["_alici"] == "PATRON"]
    assert "24 saatte karar vermedi" in p["body"] and "Panelden yeniden açabilirsiniz" in p["body"] and NUMARA_A not in p["body"]
    assert sab["kind"] == "template" and sab["sablon"]["govde"] == [BAYI_A["kod"], no]
    assert MH.hatirlatma_turu(depo, saat(15, 12)) == {"muhendis": 0, "gecikme": 0, "patron": 0, "zaman_asimi": 0, "hata": 0}     # tek bildirim
    g = muhendis_mesaji(reply_id=f"muh:patron:{no}:1")
    assert muhendis_isle(depo, g)["gerekce"] == "kontrol kapalı (zaman_asimi)"
    assert depo.muhendis_kontrolu(no, 1)["durum"] == "zaman_asimi"                               # geç karar kapalı kontrolü açmaz


def test_gece_dolan_24_saat_sabah_mesaide_bildirilir(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    _kontrol_zamani(depo, no, olusturuldu=saat(14, 21), sure_baslangici=saat(15, 8))
    assert MH.hatirlatma_turu(depo, saat(15, 22))["zaman_asimi"] == 0                          # mesai dışı
    assert MH.hatirlatma_turu(depo, saat(16, 8))["zaman_asimi"] == 1


def test_duzeltme_isteyen_ya_da_karar_veren_kontrol_zaman_asimina_dusmez(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:duzeltme:{no}:1"))
    _kontrol_zamani(depo, no, olusturuldu=saat(14, 10))
    assert MH.hatirlatma_turu(depo, saat(16, 10))["zaman_asimi"] == 0
    assert depo.muhendis_kontrolu(no, 1)["durum"] == "duzeltme"


def test_panelden_yeniden_ac_bildirim_ve_sure_yeniden(depo, wa, genel_liste, kanal_dizini):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    _kontrol_zamani(depo, no, olusturuldu=saat(14, 10), sure_baslangici=saat(14, 10))
    MH.hatirlatma_turu(depo, saat(15, 10))
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "zaman_asimi"
    c = panel_istemcisi(depo, kanal_dizini)
    h = c.git("GET", "/panel/")[1]
    sayfa = h.decode("utf-8")
    assert "zaman aşımı (24 saat)" in sayfa and f'action="/panel/kontrol/{k["id"]}/ac"' in sayfa
    assert c.git("GET", f"/panel/kontrol/{k['id']}/ac")[0] == 405
    assert c.git("POST", f"/panel/kontrol/{k['id']}/ac", {"csrf": "yanlis"})[0] == 403 and depo.muhendis_kontrolu(no, 1)["durum"] == "zaman_asimi"
    assert c.git("POST", f"/panel/kontrol/{k['id']}/ac", {"csrf": c.csrf(h)})[0] == 302
    k2 = depo.muhendis_kontrolu(no, 1)
    assert k2["durum"] == "bekliyor" and k2["hatirlatma_sayisi"] == 0 and k2["t_gecikme"] is None and k2["t_yeniden"] is not None
    [b] = [s for s in _cipa(depo, rev) if s["_alici"] == "MUHENDIS" and s["_kaynak"] == "panel"]
    assert b["kind"] == "template" and b["sablon_anahtari"] == "sablon_muhendis_kontrol" and b["sablon"]["govde"] == [no, "r01"]
    # 24 saat yeniden açılıştan sayılır: hemen kapanmaz
    simdi = time.time()
    assert MH._hatirlatmalar(k2, simdi + 60, {"muhendis": 0, "gecikme": 0, "patron": 0, "zaman_asimi": 0})[1].get("durum") is None
    assert MH._hatirlatmalar(k2, simdi + MH.ZAMAN_ASIMI_SN + 60, {"muhendis": 0, "gecikme": 0, "patron": 0, "zaman_asimi": 0})[1]["durum"] == "zaman_asimi"
    # açık kontrol yeniden açılmaz
    assert c.git("POST", f"/panel/kontrol/{k['id']}/ac", {"csrf": c.csrf(h)})[0] == 302
    assert len([s for s in _cipa(depo, rev) if s["_alici"] == "MUHENDIS" and s["_kaynak"] == "panel"]) == 1
    assert tek(depo, "SELECT count(*) n FROM muhendis_kontrolleri")["n"] == 1


# ═════════════════════════ bayi tarafı ═════════════════════════
import json  # noqa: E402

import kalici  # noqa: E402
import kayit as KY  # noqa: E402
import worker as W  # noqa: E402
from conftest import mesaj, talep  # noqa: E402
from test_celik_akisi import BAYI_KART, T_DIGER, UC, buton, hizli_genel, kabul  # noqa: E402,F401
from test_plan_akisi import URETIM, t1, uretici  # noqa: E402,F401


def _gorunen(s: dict) -> str:
    """Bayinin ekranda okuduğu metin: gövde, alt bilgi, düğme ve liste başlıkları (düğme kimlikleri görünmez)."""
    i = s.get("interactive") or {}
    a = i.get("action") or {}
    parcalar = [s.get("body") or "", (i.get("body") or {}).get("text") or "", (i.get("footer") or {}).get("text") or "", a.get("button") or ""]
    parcalar += [b["reply"]["title"] for b in a.get("buttons") or []]
    parcalar += [x.get(f) or "" for b in a.get("sections") or [] for x in [b, *(b.get("rows") or [])] for f in ("title", "description")]
    return "\n".join(parcalar)


def bayiye(depo) -> list[dict]:
    return [x["satir"] for x in sorgu(depo, "SELECT satir FROM giden WHERE alici = %s ORDER BY olusturuldu, sira", NUMARA_A)]


# ───────────────────────── satır sonları (F) ─────────────────────────
def test_dugmeli_mesajda_satir_sonlari_kalir():
    g = {"id": "wamid.F1", "sender": NUMARA_A}
    metin = "Üç seçenek hazır:\n\n1. Ç8801  ·  88 m²\n2. Ç8801K · 88 m²\n\n\n\nBirini seçin."
    s = W.giden_etkilesim(g, metin, 1, butonlar=[("x", "1"), ("y", "2")])
    assert s["interactive"]["body"]["text"] == "Üç seçenek hazır:\n\n1. Ç8801 · 88 m²\n2. Ç8801K · 88 m²\n\nBirini seçin."
    assert KY.dugmeli_satir(g, metin, 1, NUMARA_A, "cevap", [("x", "1")])["interactive"]["body"]["text"] == s["interactive"]["body"]["text"]
    assert W._govde("a" * 2000, W.WA_GOVDE).endswith("…") and len(W._govde("a" * 2000, W.WA_GOVDE)) == W.WA_GOVDE
    assert s["interactive"]["action"]["buttons"][0]["reply"]["title"] == "1"                     # başlıklar tek satır (aynen)


# ───────────────────────── iç kod (YENI-…) bayiye yazılmaz ─────────────────────────
def test_uretilen_planin_ic_kodu_bayiye_gorunmez(depo, wa, hizli_genel, uretici):
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    yeni = st["adaylar"][0]["kod"]
    assert yeni.startswith("YENI-")
    for _ in range(2):                                                                  # seçim ve aynı düğmeye ikinci basış
        assert depo.mesaj_kaydet(buton(f"s:{st['id']}:{yeni}"))
        isle_hepsi(depo, URETIM)
    ss = bayiye(depo)
    assert ss[-1]["body"].startswith("Bu seçenek listesinden Yeni plan zaten seçildi.")
    [belge] = [s for s in ss if s["kind"] == "document"]
    assert "Yeni plan" in belge["body"] and "seçildi" not in belge["body"]
    assert not [s for s in ss if "YENI-" in _gorunen(s)], [_gorunen(s) for s in ss if "YENI-" in _gorunen(s)]


# ───────────────────────── ilk çelik planda LLM özeti ─────────────────────────
def test_ilk_celik_planda_llm_ozeti_mesaja_ve_pdf_basligina_girmez(depo, wa, hizli_genel):
    kabul(depo, UC)
    ozet = "Ç8801K istendi; kapı yerini netleştirmeniz gerekiyor"                     # Ç8801K r01 (canlı): LLM özeti soru gibi okunuyordu
    assert depo.mesaj_kaydet(mesaj("Ç8801K olsun", talep(ozet=ozet, katalog_kodu="Ç8801K"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    ss = bayiye(depo)
    assert not [s for s in ss if "netleştir" in _gorunen(s)]
    [belge] = [s for s in ss if s["kind"] == "document"]
    baslik = belge["body"].split(" · ÖN ONAYA SUNULAN TASLAK · ")[1]
    assert baslik == "Ç8801-K (Beşik + cumba, doğu ucu kırma) · 88 m², 2+1"                     # kodun okuması: model, çatı, m², oda
    [plan] = [s for s in ss if s["kind"] == "interactive"]
    assert plan["body"].startswith(baslik + ". Ön onay") and plan["body"].endswith("Ön onay planınız hazır; plan görseli ve PDF ektedir.")


# ───────────────────────── D-19 (b): bayinin açık işi 24 saatte kapanır ─────────────────────────
def _gecmise_al(depo, saat_: float) -> None:
    """Bayinin önceki mesajları `saat_` saat önce yazılmış olsun (WhatsApp gönderim anı)."""
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE mesajlar SET wa_zamani = wa_zamani - make_interval(secs => %s) WHERE gonderen = %s", (saat_ * 3600, NUMARA_A))


def _celik_r01(depo, wa) -> dict:
    kabul(depo, UC)
    assert depo.mesaj_kaydet(mesaj("Ç8801K olsun", talep(ozet="Ç8801K", katalog_kodu="Ç8801K"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo); assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    return tek(depo, "SELECT * FROM revizyonlar ORDER BY id DESC LIMIT 1")


def test_onay_bekleyen_plan_24_saatte_kapanir_eski_onay_dugmesi_gecersiz(depo, wa, hizli_genel):
    rev = _celik_r01(depo, wa)
    _gecmise_al(depo, 25)
    o = buton(f"o:{rev['is_emri_no']}:1"); assert depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "cevapla" and r["gerekce"] != "plan onaylandı", r
    [s] = [x for x in bayiye(depo) if x["inbound_id"] == o["id"]]
    assert s["kind"] == "text" and s["body"].startswith(kalici.ACIK_IS_NOTU) and "şu an açık bir plan yok" in s["body"]
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "zaman_asimi"      # kayıt durur
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "bos" and not d.get("son_is_emri") and "proje_id" not in d
    assert any("D-19: açık iş (onay bekleyen plan)" in g["metin"] for g in d["gecmis"])
    sonuc = tek(depo, "SELECT sonuc FROM isler WHERE mesaj_id = %s", o["id"])["sonuc"]
    assert sonuc["acik_is_kapanisi"]["ne"] == "onay bekleyen plan" and sonuc["acik_is_kapanisi"]["saat"] >= 25
    assert not [x for x in bayiye(depo) if x["kind"] == "template"]                      # kapanış için ücretli şablon yok
    # yeni talep yeni proje açar; eski revizyon dokunulmaz
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("Ç8801K olsun", talep(ozet="Ç8801K", katalog_kodu="Ç8801K"), bayi=BAYI_KART))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "is_emri" and r2["proje_id"] != rev["proje_id"]
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "zaman_asimi"


def test_24_saat_dolmadan_onay_aynen(depo, wa, hizli_genel):
    rev = _celik_r01(depo, wa)
    _gecmise_al(depo, 23)
    time.sleep(1.1)                                                                     # onay, planın gönderim anından sonra (saniye)
    o = buton(f"o:{rev['is_emri_no']}:1"); assert depo.mesaj_kaydet(o)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "plan onaylandı" and "acik_is_kapanisi" not in tek(depo, "SELECT sonuc FROM isler WHERE mesaj_id = %s", o["id"])["sonuc"]


def test_acik_secenek_seti_24_saatte_duser_yeni_mesaj_yeni_talep(depo, wa, hizli_genel, uretici):
    t1(depo)
    st = sorgu(depo, "SELECT id, adaylar FROM secenek_setleri")[0]
    _gecmise_al(depo, 30)
    g = buton(f"s:{st['id']}:{st['adaylar'][0]['kod']}"); assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo, URETIM)
    assert r["eylem"] == "cevapla", r
    assert tek(depo, "SELECT durum FROM secenek_setleri WHERE id = %s", st["id"])["durum"] == "dustu"
    [s] = [x for x in bayiye(depo) if x["inbound_id"] == g["id"]]
    assert s["body"].startswith(kalici.ACIK_IS_NOTU) and "artık geçerli değil" in s["body"]
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 0


def test_acik_soru_24_saatte_duser(depo, wa, hizli_genel):
    assert depo.mesaj_kaydet(mesaj("6x8 m ev", talep("yeni_talep", "6x8 m ev", dis_olcu={"en_m": 6, "boy_m": 8}), bayi=BAYI_KART))
    isle_hepsi(depo)
    assert tek(depo, "SELECT durum FROM sorular")["durum"] == "acik"
    _gecmise_al(depo, 26)
    g = mesaj("merhaba", T_DIGER, bayi=BAYI_KART); assert depo.mesaj_kaydet(g)
    isle_hepsi(depo)
    s = tek(depo, "SELECT durum, cevap_mesaj_id FROM sorular")
    assert (s["durum"], s["cevap_mesaj_id"]) == ("dustu", g["id"])
    d, _ = depo.konusma_oku(NUMARA_A)
    assert not (d.get("taslak") or {}).get("dis_olcu")                                    # eski taslak yeni talebe taşınmaz
    assert bayiye(depo)[-1]["body"].startswith(kalici.ACIK_IS_NOTU)


def test_onaylanmis_proje_24_saatten_sonra_da_revizyonla_ayni_projede(depo, wa, genel_liste):
    """Onaylanan plan bayiden cevap beklemez: iki gün sonraki revizyon isteği aynı projede r02 olur ve kontrol 'plan_degisti' (rehber §4)."""
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    assert kalici.acik_is(depo.konusma_oku(NUMARA_A)[0]) is None
    _gecmise_al(depo, 48)
    r = revize(depo, "mutfak penceresi 120x120 olsun", **PENCERE)
    assert r["eylem"] == "is_emri" and r["proje_id"] == rev["proje_id"], r
    assert depo.muhendis_kontrolu(no, 1)["durum"] == "plan_degisti"
    assert "acik_is_kapanisi" not in tek(depo, "SELECT sonuc FROM isler WHERE mesaj_id = %s", r["mesaj_id"])["sonuc"]


def test_acik_is_tanimi():
    assert kalici.acik_is(None) is None and kalici.acik_is({"asama": "bos", "taslak": {}}) is None
    assert kalici.acik_is({"asama": "onay_bekliyor", "son_is_emri": {"is_emri_no": "X"}}) == "onay bekleyen plan"
    assert kalici.acik_is({"asama": "topluyor", "secenek_seti": {"durum": "acik"}}) == "seçenek seti"
    assert kalici.acik_is({"asama": "topluyor", "son_soru_alani": "oda_programi", "taslak": {"x": 1}}) == "soru"
    assert kalici.acik_is({"asama": "topluyor", "taslak": {"katalog_kodu": "P6001"}}) == "taslak"
    assert kalici.acik_is({"asama": "onaylandi", "son_soru_alani": "x", "son_is_emri": {}}) is None
    assert kalici.acik_is({"asama": "yonlendirildi", "taslak": {"x": 1}}) is None


def test_patronun_sablonuna_cevap_acik_isi_kapatmaz(depo, wa, hizli_genel):
    """Patron pencere kapalıyken "dosyalar hazır" şablonuyla ulaştı; bayinin "Dosyaları gönder" cevabı eski işe dönüş değil (pencereyi Patron açtı)."""
    import sablonlar as S
    rev = _celik_r01(depo, wa)
    _gecmise_al(depo, 25)
    g = buton(f"{S.DOSYA_YUK_ONEKI}{rev['is_emri_no']}"); g["type"] = "button"
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["gerekce"] == "şablon cevabı: dosya penceresi açıldı", r
    [s] = [x for x in bayiye(depo) if x["inbound_id"] == g["id"]]
    assert s["body"] == S.BAYI_DOSYA_CEVABI
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE id = %s", rev["id"])["durum"] == "onay_bekliyor"
    assert depo.konusma_oku(NUMARA_A)[0]["son_is_emri"]["is_emri_no"] == rev["is_emri_no"]
