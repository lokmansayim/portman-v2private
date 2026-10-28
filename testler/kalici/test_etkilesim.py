"""İE-04 · mesaj katmanı (kanal v1.3): seçenek seti, buton/liste cevaplarının kimlikle bağlanması, eski buton reddi, revizyon ve onay
butonları, aynı revizyondan görsel + PDF + IFC + 3D; serbest metin yolu açık. Gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp;
Motor hızlı sahte üreticiyle (ekler gerçek: bayi görseli, IFC, 3D sayfası İş Emri'nden). Test adayları (beyin/veri/adaylar_test.json)
yalnız settings.test_adaylari ile görünür; gerçek seçenek değildir.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_etkilesim.py -q
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import (AYAR, BAYI_B, NUMARA_A, NUMARA_B, mesaj, sorgu, talep, tek)

import etkilesim as ET
import kalici
import worker as W

KATMAN = {**AYAR, "mesaj_katmani": True, "test_adaylari": True}
KATMAN_3D = {**KATMAN, "ucb_taban_url": "https://ornek.invalid/portman/3d"}
T_3ARTI1 = talep(ozet="90 m² civarı 3+1", oda_programi="3+1", alan_m2=90)
T_DIGER = talep("diger", "kısa cevap")


def isle_hepsi(depo, ayar=KATMAN) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def buton(metin: str, reply_id: str, context_id: str | None, numara=NUMARA_A, bayi=None, ts=None) -> dict:
    """feature.php v1.3: etkileşimli cevap satırı (text = görünen başlık; reply_id kimlik; context_id cevaplanan mesaj)."""
    g = mesaj(metin, T_DIGER, numara=numara, bayi=bayi, context_id=context_id, tur="interactive", ts=ts)
    g["reply_id"] = reply_id; g["reply_kind"] = "button_reply"
    return g


def gonderilen_satir(depo, kind: str, sira: int = -1) -> dict:
    rows = sorgu(depo, "SELECT satir, dis_id FROM giden WHERE kind = %s ORDER BY olusturuldu, sira", kind)
    assert rows, f"{kind} satırı yok"
    return rows[sira]


def kimlikler(satir: dict) -> list[str]:
    return sorted(ET.mesaj_kimlikleri(satir))


# ───────────────────────── seçenek seti, öncelik, seçim ─────────────────────────
def test_secenek_akisi_butonla(depo, wa, hizli_motor):
    # 1) tarif → öncelik sorusu butonlarla
    g1 = mesaj("90 m² civarı 3+1 istiyorum", T_3ARTI1)
    assert depo.mesaj_kaydet(g1)
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "sor" and "oncelik" in (r1["gerekce"] or "")
    kalici.gonder(depo, wa)
    soru = gonderilen_satir(depo, "interactive")
    assert kimlikler(soru["satir"]) == ["q:oncelik:butce", "q:oncelik:montaj", "q:oncelik:yasam"]
    assert soru["dis_id"]

    # 2) öncelik butonu → seçenek seti (görsel başlıklı buton mesajı; üç aday)
    depo.mesaj_kaydet(buton("Bütçe önce", "q:oncelik:butce", soru["dis_id"]))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "secenek", r2
    kalici.gonder(depo, wa)
    st = tek(depo, "SELECT * FROM secenek_setleri WHERE durum = 'acik'")
    assert st and [a["kod"] for a in st["adaylar"]] == ["TEST02", "TEST01", "TEST03"]      # bütçe: en küçük kapalı alan öne
    assert all(a["durum"] == "test" for a in st["adaylar"])
    sec = gonderilen_satir(depo, "interactive")
    assert kimlikler(sec["satir"]) == sorted(f"s:{st['id']}:{k}" for k in ("TEST01", "TEST02", "TEST03"))
    assert sec["satir"]["interactive"]["header"]["type"] == "image" and Path(sec["satir"]["file"]).is_file()
    assert "TEST VERİSİ" in sec["satir"]["body"]
    soru_kaydi = tek(depo, "SELECT alan, durum FROM sorular WHERE alan = 'oncelik'")
    assert soru_kaydi["durum"] == "cevaplandi"
    llm = tek(depo, "SELECT cikarim FROM isler ORDER BY id DESC LIMIT 1")["cikarim"]
    assert llm["meta"]["backend"] == "etkilesim"                        # buton cevabında LLM çağrılmadı

    # 3) eski/yanlış buton: hiçbir durum değişmez
    depo.mesaj_kaydet(buton("1. TEST01", "s:ss_0000000000000000:TEST01", sec["dis_id"]))
    [r3] = isle_hepsi(depo)
    assert r3["eylem"] == "cevapla" and "eski buton" in r3["gerekce"]
    assert tek(depo, "SELECT durum FROM secenek_setleri WHERE id = %s", st["id"])["durum"] == "acik"
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 0
    # kimlik doğru ama cevaplanan mesajın butonlarında yok (başka mesaja verilmiş): reddedilir
    depo.mesaj_kaydet(buton("2. TEST02", f"s:{st['id']}:TEST02", soru["dis_id"]))
    [r3b] = isle_hepsi(depo)
    assert r3b["eylem"] == "cevapla" and "butonlarında yok" in r3b["gerekce"]
    assert tek(depo, "SELECT durum FROM secenek_setleri WHERE id = %s", st["id"])["durum"] == "acik"

    # 4) geçerli seçim → r01: görsel başlıklı Onayla/Revize butonları + PDF; set 'secildi'; ekler aynı revizyondan
    depo.mesaj_kaydet(buton("2. TEST02", f"s:{st['id']}:TEST02", sec["dis_id"]))
    [r4] = isle_hepsi(depo)
    assert r4["eylem"] == "is_emri" and r4["revizyon_id"], r4
    kalici.gonder(depo, wa)
    st2 = tek(depo, "SELECT durum, secilen_kod FROM secenek_setleri WHERE id = %s", st["id"])
    assert st2["durum"] == "secildi" and st2["secilen_kod"] == "TEST02"
    rev = tek(depo, "SELECT * FROM revizyonlar")
    assert rev["rev"] == 1 and rev["durum"] == "onay_bekliyor" and rev["is_emri"]["yapi"]["referans_model"] == "P9201"
    ekler = rev["ekler"]
    assert Path(ekler["gorsel"]["file"]).is_file() and Path(ekler["ifc"]["dosya"]).is_file() and Path(ekler["ucb"]["dosya"]).is_file()
    assert ekler["ifc"]["sema_hatasi"] == 0 and ekler["ifc"]["pencere"] == 6 and ekler["ifc"]["kapi"] == 5
    assert ekler["ucb"]["url"] is None                                   # barınak ayarı yok: bağlantı butonu gönderilmez
    son = [x for x in wa.gonderilen if x["id"] in {s["id"] for s in sorgu(depo, "SELECT id FROM giden WHERE mesaj_id = %s", r4["mesaj_id"])}]
    assert [x["kind"] for x in son] == ["interactive", "document"]        # 3D bağlantısı yok (ucb_taban_url ayarı yok): söz veren metin de yok
    onay = gonderilen_satir(depo, "interactive")
    no = rev["is_emri_no"]
    assert kimlikler(onay["satir"]) == sorted([f"o:{no}:1", f"r:{no}:1"])
    assert onay["satir"]["interactive"]["header"]["type"] == "image" and onay["satir"]["file"] == ekler["gorsel"]["file"]
    assert tek(depo, "SELECT revizyon_id FROM giden WHERE id = %s", onay["satir"]["id"])["revizyon_id"] == rev["id"]

    # 5) Revize butonu → "neyi değiştirelim" sorusu; serbest metinle pencere revizyonu → r02 aynı projede
    depo.mesaj_kaydet(buton("Revize et", f"r:{no}:1", onay["dis_id"]))
    [r5] = isle_hepsi(depo)
    assert r5["eylem"] == "sor" and r5["gerekce"] == "plan reddedildi"
    kalici.gonder(depo, wa)
    t_rev = talep("revizyon", "yatak odası 1 penceresi 120x120", pencereler=[{"mahal": "YATAK ODASI 1", "olcu": "120x120", "islem": "degistir"}])
    depo.mesaj_kaydet(mesaj("yatak odası 1 penceresi 120x120 olsun", t_rev))
    [r6] = isle_hepsi(depo)
    assert r6["eylem"] == "is_emri", r6
    kalici.gonder(depo, wa)
    revs = sorgu(depo, "SELECT rev, durum, proje_id FROM revizyonlar ORDER BY rev")
    assert [(x["rev"], x["durum"]) for x in revs] == [(1, "yerini_aldi"), (2, "onay_bekliyor")] and revs[0]["proje_id"] == revs[1]["proje_id"]

    # 6) eski onay butonu (r01) güncel planı onaylamaz; güncel onay butonu (r02) onaylar
    time.sleep(1.1)
    depo.mesaj_kaydet(buton("Onayla", f"o:{no}:1", onay["dis_id"]))
    [r7] = isle_hepsi(depo)
    assert r7["eylem"] == "cevapla" and "eski revizyon butonu" in r7["gerekce"]
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE rev = 2")["durum"] == "onay_bekliyor"
    no2 = tek(depo, "SELECT is_emri_no FROM revizyonlar WHERE rev = 2")["is_emri_no"]     # revizyon numarası yeni İş Emri numarası taşır (bugünkü kural)
    onay2 = gonderilen_satir(depo, "interactive")
    assert f"o:{no2}:2" in kimlikler(onay2["satir"])
    depo.mesaj_kaydet(buton("Onayla", f"o:{no2}:2", onay2["dis_id"]))
    [r8] = isle_hepsi(depo)
    assert r8["gerekce"] == "plan onaylandı", r8
    assert tek(depo, "SELECT durum FROM revizyonlar WHERE rev = 2")["durum"] == "onaylandi"


def test_ucb_baglanti_butonu_ayarla_gelir(depo, wa, hizli_motor, kanal_dizini):
    """İE-21: ayar dolu ve yayın dizini varken sayfa rastgele anahtarlı adrese bayt bayt kopyalanır, bayiye "3D'yi aç" düğmesi gider.
    Adres İş Emri numarası taşımaz (eski biçim …/3d/<no>/r01/ tahmin edilebilirdi; kodsuz bayide numara telefonun son dört hanesini taşır)."""
    import re
    import sablonlar as S
    import ucb_yayin as UY
    (kanal_dizini / "yayin" / "3d").mkdir(parents=True)
    g = mesaj("TEST01 olsun", talep(ozet="TEST01", katalog_kodu="TEST01"))
    depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo, KATMAN_3D)
    assert r["eylem"] == "is_emri"
    kalici.gonder(depo, wa)
    rev = tek(depo, "SELECT is_emri_no, ekler FROM revizyonlar")
    ucb = rev["ekler"]["ucb"]
    assert re.fullmatch(r"https://ornek\.invalid/portman/3d/[A-Za-z0-9_-]{22}/", ucb["url"]) and UY.ANAHTAR.fullmatch(ucb["anahtar"])
    assert rev["is_emri_no"] not in ucb["url"] and ucb["url"] == f"https://ornek.invalid/portman/3d/{ucb['anahtar']}/"
    yayin = kanal_dizini / "yayin" / "3d" / ucb["anahtar"] / "index.html"
    assert yayin.read_bytes() == Path(ucb["dosya"]).read_bytes() and yayin.stat().st_mode & 0o777 == 0o644
    assert yayin.parent.stat().st_mode & 0o777 == 0o755 and not list(yayin.parent.glob(".*"))
    kinds = [x["kind"] for x in wa.gonderilen]
    assert kinds == ["interactive", "document", "interactive"]
    cta = gonderilen_satir(depo, "interactive")["satir"]["interactive"]
    assert cta["type"] == "cta_url" and cta["action"]["parameters"] == {"display_text": S.UCB_DUGME, "url": ucb["url"]}
    assert cta["body"]["text"] == S.ucb_metni(rev["is_emri_no"], 1) and "tek parmakla çevirin" in cta["body"]["text"]
    html = Path(ucb["dosya"]).read_text(encoding="utf-8")
    assert "YATAK ODASI 1" in html and "THREE" in html and "cdnjs" not in html   # gömülü three.js; dış ağ yok


def test_ucb_yayin_dizini_yoksa_baglanti_gitmez(depo, wa, hizli_motor):
    """İE-21: ayar dolu ama yayın dizini yok (nginx_uygula.sh koşmamış) → bozuk bağlantı gönderilmez; sayfa kayıtta, sebep ekte."""
    depo.mesaj_kaydet(mesaj("TEST01 olsun", talep(ozet="TEST01", katalog_kodu="TEST01")))
    [r] = isle_hepsi(depo, KATMAN_3D)
    assert r["eylem"] == "is_emri"
    kalici.gonder(depo, wa)
    ucb = tek(depo, "SELECT ekler FROM revizyonlar")["ekler"]["ucb"]
    assert ucb["url"] is None and "yayın dizini yok" in ucb["yayin_hata"] and Path(ucb["dosya"]).is_file()
    assert [x["kind"] for x in wa.gonderilen] == ["interactive", "document"]


def test_serbest_metin_yolu_acik(depo, wa, hizli_motor):
    """Butonsuz da aynı yol: öncelik metinle, seçim kod yazarak; set metinle de kapanır."""
    depo.mesaj_kaydet(mesaj("90 m² civarı 3+1", T_3ARTI1, numara=NUMARA_B, bayi=BAYI_B))
    [r1] = isle_hepsi(depo); assert r1["eylem"] == "sor"
    depo.mesaj_kaydet(mesaj("fark etmez", T_DIGER, numara=NUMARA_B, bayi=BAYI_B))
    [r2] = isle_hepsi(depo); assert r2["eylem"] == "secenek", r2
    st = tek(depo, "SELECT id, adaylar FROM secenek_setleri WHERE gonderen = %s AND durum = 'acik'", NUMARA_B)
    assert [a["kod"] for a in st["adaylar"]] == ["TEST02", "TEST01", "TEST03"]          # öncelik yok: yalnız alan yakınlığı
    depo.mesaj_kaydet(mesaj("TEST01 olsun", talep(ozet="TEST01 seçildi", katalog_kodu="TEST01"), numara=NUMARA_B, bayi=BAYI_B))
    [r3] = isle_hepsi(depo); assert r3["eylem"] == "is_emri", r3
    assert tek(depo, "SELECT durum, secilen_kod FROM secenek_setleri WHERE id = %s", st["id"]) == {"durum": "secildi", "secilen_kod": "TEST01"}


def test_katman_kapaliyken_v12_davranisi(depo, wa, hizli_motor):
    """settings.mesaj_katmani yokken: seçenek metinle, plan metin + PDF (canlı v1.2 ile aynı satır türleri)."""
    ayar = {**AYAR, "test_adaylari": True}
    depo.mesaj_kaydet(mesaj("90 m² civarı 3+1", T_3ARTI1))
    [r1] = isle_hepsi(depo, ayar); assert r1["eylem"] == "sor"
    depo.mesaj_kaydet(mesaj("bütçe", T_DIGER))
    [r2] = isle_hepsi(depo, ayar); assert r2["eylem"] == "secenek"
    kalici.gonder(depo, wa)
    assert all(x["kind"] == "text" for x in wa.gonderilen) and "Seçmek için kodunu yazın" in wa.gonderilen[-1]["govde"]
    depo.mesaj_kaydet(mesaj("TEST02", talep(ozet="TEST02", katalog_kodu="TEST02")))
    [r3] = isle_hepsi(depo, ayar); assert r3["eylem"] == "is_emri"
    kalici.gonder(depo, wa)
    assert [x["kind"] for x in wa.gonderilen[-2:]] == ["text", "document"]
    assert tek(depo, "SELECT ekler FROM revizyonlar")["ekler"] == {}


def test_test_adaylari_ayarsiz_gorunmez(depo, wa, hizli_motor):
    """test_adaylari yokken (canlı ayar): aday kaydı boş → bugünkü davranış (katalog önerisi sorusu), TEST kodu bulunmaz."""
    depo.mesaj_kaydet(mesaj("90 m² civarı 3+1", T_3ARTI1))
    [r1] = isle_hepsi(depo, {**AYAR, "mesaj_katmani": True})
    assert r1["eylem"] == "sor" and r1["gerekce"] == "eksik: model_veya_olcu"
    assert tek(depo, "SELECT count(*) n FROM secenek_setleri")["n"] == 0
    depo.mesaj_kaydet(mesaj("TEST01 olsun", talep(ozet="TEST01", katalog_kodu="TEST01")))
    [r2] = isle_hepsi(depo, {**AYAR, "mesaj_katmani": True})
    assert r2["eylem"] == "sor" and r2["gerekce"] == "eksik: katalog_kodu"


def test_kimlik_cozumu_birim():
    d = {"asama": "onay_bekliyor", "son_is_emri": {"is_emri_no": "PM-X-1", "revizyon": 2}, "son_soru_alani": None,
         "secenek_seti": {"id": "ss_ab", "durum": "acik", "adaylar": [{"kod": "TEST01"}]}}
    assert ET.coz({"reply_id": "o:PM-X-1:2"}, d)["gecerli"] is True
    assert ET.coz({"reply_id": "o:PM-X-1:1"}, d)["neden"] == "eski revizyon butonu"
    assert ET.coz({"reply_id": "s:ss_ab:TEST01"}, d)["tur"] == "secim"
    assert ET.coz({"reply_id": "s:ss_ab:TEST09"}, d)["neden"] == "kod sette yok"
    assert ET.coz({"reply_id": "q:pencere_islem:degistir"}, d)["neden"] == "soru artık askıda değil"
    assert ET.coz({"reply_id": "Onayla"}, d)["neden"] == "kimlik çözülemedi"          # başlık metni kimlik değildir
    mesajin = {"kind": "interactive", "interactive": {"action": {"buttons": [{"id": "o:PM-X-1:2", "title": "Onayla"}]}}}
    assert ET.coz({"reply_id": "r:PM-X-1:2", "context_id": "wamid.1"}, d, lambda c: mesajin)["neden"] == "kimlik cevaplanan mesajın butonlarında yok"
    satir = W.giden_etkilesim({"id": "wamid.T", "sender": "9000"}, "x", 1, liste={"dugme": "Gör", "bolumler": [{"baslik": "B", "satirlar": [
        {"id": f"s:ss_ab:K{i}", "baslik": f"K{i}", "aciklama": ""} for i in range(12)]}]})
    assert len(ET.mesaj_kimlikleri(satir)) == 10                                     # liste ≤10 satır
