"""İE-08 8a PR-2a · çelik bayi akışı A2–A3 (kalıcı akış, gerçek Postgres, kayıtlı LLM çıkarımı, sahte WhatsApp).

A2: "Ç8801" → tek görselde üç çatı seçeneği (katalog, K, L; öncelik sorusu yok; set türü cati_varyanti); "88 m² 2+1 çelik" → alan seti
(soru yok; görselde Ç8801 üçlüsü); "95 m² 3+1 tek kat çelik" → bugünkü davranış (katalog önerisi); dış ölçü → alan yolu (GRID yok);
kabul kaydı yokken aday sunulmaz (K-A10). A3: seçim düğmesi → r01 genel motordan (zarf yapi.sistem celik, tanım gömülmez, sha; satırlar
etkileşim + belge; PDF adı Portman_<no>_rNN.pdf; CTA yok); gerçek motor: PDF 2 sayfa, 1. sayfada TASLAK, antette bayinin adı ve kart
numarası (D-09); Patron kartı numara yazdırmaz; LLM bağlamı ve iş sonucu ham numara taşımaz.
A4 (PR-2b): bayinin sözünden okunan değişiklik aynı projede r02 (pencere ölçüsü, çatı varyantı, dış 140); başlık görseli önce–sonra;
belirsiz cümlede "1 / 2 / Hiçbiri" (görselli, q:okuma); "Hiçbiri" bir kez "Neyi değiştirelim?"; çelik çizim düşerse hak düşmez
(cizim_hatasi: konuşma önceki planda, revizyon satırı yok; PR-2a'daki "doğrulamadan geçmedi" vakası bu kararla değişti); 4 revizyondan
sonra "plan mühendis incelemesine alındı"; prefabrik çizim hatası bugünkü davranışta (A5).
Çoğu test hızlı sahte genel motorla (`sahte_genel`), bir test gerçek motorla (perspektif VTK yoksa atlanır, iş düşmez).

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_celik_akisi.py -q
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from conftest import (AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep)

import kalici
import worker as W

KOK = Path(__file__).resolve().parents[2]
KATMAN = {**AYAR, "mesaj_katmani": True}
UC = {"Ç8801", "Ç8801K", "Ç8801L"}
YEDI = UC | {"Ç8201", "KT01", "KT02", "KT03"}
BAYI_KART = {**BAYI_A, "numara": NUMARA_A}                     # kalıcı akış: depo.gelen_bayisi numara verir (D-09)
T_DIGER = talep("diger", "kısa cevap")


def kabul(depo, kodlar=UC):
    for kod in kodlar:
        depo.aday_yaz(kod, "gecerli", referans_model="Ç8801", muhendis_kabulu={"kim": "test", "tarih": "2026-10-13", "not": ""})


def isle_hepsi(depo, ayar=KATMAN) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def buton(reply_id: str, context_id: str | None = None, bayi=None) -> dict:
    g = mesaj(reply_id.split(":")[-1], T_DIGER, bayi=bayi if bayi is not None else BAYI_KART, context_id=context_id, tur="interactive")
    g["reply_id"] = reply_id; g["reply_kind"] = "button_reply"
    return g


def sahte_genel(tanim_yolu: Path, hedef: Path, is_emri_no=None, revizyon=1, bilgi=None, **k) -> dict:
    """Hızlı sahte genel motor: manifest ve validation genel motorunkiyle aynı anahtarlarla; PDF/PNG içeriği sahte. `bilgi` hata iletisine girmez."""
    hedef = Path(hedef); hedef.mkdir(parents=True, exist_ok=True)
    t = json.loads(Path(tanim_yolu).read_text(encoding="utf-8")); kod = t["kod"].replace("Ç", "C").replace("-", "")
    govde = json.dumps({"no": is_emri_no, "rev": revizyon, "kod": kod, "ad": (bilgi or {}).get("bayi_adi")}, sort_keys=True).encode()
    (hedef / f"{kod}_pafta.pdf").write_bytes(b"%PDF-1.4\n% sahte genel motor\n" + govde)
    (hedef / f"{kod}_plan_bayi.png").write_bytes(b"\x89PNG sahte " + govde)
    (hedef / f"{kod}_bayi_gorsel.png").write_bytes(b"\x89PNG sahte kart " + govde)
    (hedef / f"{kod}.ifc").write_bytes(b"ISO-10303-21; sahte")
    (hedef / f"{kod}_yukleme.json").write_text("{}", encoding="utf-8")
    (hedef / "validation.json").write_text(json.dumps({"passed": True, "errors": [], "warnings": [], "perspektif": {"durum": "ATLANDI"},
                                                       "ifc": {"sema_hatasi": 0, "urunler": {"IfcWall": 13, "IfcWindow": 9, "IfcDoor": 6, "IfcSpace": 7}}}), encoding="utf-8")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return {"motor": "genel", "kod": t["kod"], "passed": True, "warnings": [], "pdf": f"{kod}_pafta.pdf", "pdf_sha256": sha(hedef / f"{kod}_pafta.pdf"),
            "ifc": f"{kod}.ifc", "ifc_sha256": sha(hedef / f"{kod}.ifc"), "plan_bayi": f"{kod}_plan_bayi.png", "bayi_gorsel": f"{kod}_bayi_gorsel.png",
            "bilgi_var": bool(bilgi), "yukleme_json": f"{kod}_yukleme.json", "set": "kurallar.json"}


@pytest.fixture
def hizli_genel(monkeypatch):
    from motor.genel import uret
    monkeypatch.setattr(uret, "uret", sahte_genel)


def set_satiri(depo) -> dict:
    rows = sorgu(depo, "SELECT satir FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu, sira")
    assert rows
    return rows[-1]["satir"]


# ───────────────────────── A2 ─────────────────────────
def test_kabul_kaydi_yokken_celik_aday_sunulmaz(depo, wa, hizli_genel):
    assert depo.mesaj_kaydet(mesaj("Ç8801 olsun", talep(ozet="Ç8801", katalog_kodu="Ç8801"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "yonlendir" and "şablon kodlanmamış" in r["gerekce"]        # bugünkü davranış (K-A10: kabul yok)


def test_c8801_uc_cati_seti_oncelik_sorusu_yok(depo, wa, hizli_genel):
    kabul(depo)
    g1 = mesaj("Ç8801 olsun", talep(ozet="Ç8801 istiyor", katalog_kodu="Ç8801"), bayi=BAYI_KART)
    assert depo.mesaj_kaydet(g1)
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "secenek" and "3 aday" in r1["gerekce"]
    st = sorgu(depo, "SELECT id, durum, adaylar FROM secenek_setleri")[0]
    assert st["durum"] == "acik" and [a["kod"] for a in st["adaylar"]] == ["Ç8801", "Ç8801K", "Ç8801L"] and all(a.get("puan") is None for a in st["adaylar"])
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["secenek_seti"]["tur"] == "cati_varyanti" and d.get("son_soru_alani") == "secenek" and "oncelik_soruldu" not in d["taslak"]
    satir = set_satiri(depo)
    butonlar = [b["reply"]["id"] for b in satir["interactive"]["action"]["buttons"]]
    assert butonlar == [f"s:{st['id']}:Ç8801", f"s:{st['id']}:Ç8801K", f"s:{st['id']}:Ç8801L"]
    assert [b["reply"]["title"] for b in satir["interactive"]["action"]["buttons"]] == ["1. Ç8801", "2. Ç8801-K", "3. Ç8801-L"]
    assert satir.get("file") and satir["file"].endswith("secenekler.png") and Path(satir["file"]).is_file()      # bileşik görsel: üç aday kartı
    assert "çatı seçeneği" in satir["body"] and "fark çatıda" in satir["body"]
    assert sorgu(depo, "SELECT count(*) AS n FROM giden WHERE kind = 'interactive'")[0]["n"] == 1                 # öncelik sorusu sorulmadı


def test_88_m2_2arti1_celik_soru_yok_gorselde_c8801_uclusu(depo, wa, hizli_genel):
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("88 m² 2+1 çelik", talep(ozet="88 m² 2+1 çelik", alan_m2=88, oda_programi="2+1", yapi_turu="celik"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "secenek" and "6 aday" in r["gerekce"]                   # Ç8801/K/L 88, KT-02 92, KT-03 94, Ç8201 82 (±%10 brüt oturum, K-A1)
    st = sorgu(depo, "SELECT adaylar FROM secenek_setleri")[0]["adaylar"]
    assert [a["kod"] for a in st[:3]] == ["Ç8801", "Ç8801K", "Ç8801L"] and all(a["puan"] == 100 for a in st[:3]) and len(st) == 6
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["secenek_seti"]["tur"] == "alan" and "oncelik_soruldu" not in d["taslak"]
    kinds = [r["kind"] for r in sorgu(depo, "SELECT kind FROM giden ORDER BY sira")]
    assert kinds == ["interactive", "interactive"]                                 # görsel + 3 düğme, sonra tam liste (6 aday)


def test_yapi_turu_soylenmeden_celik_aday_sunulmaz(depo, wa, hizli_genel):
    # geometri hakemi (12.10): "88 m² 2+1" (yapı türü yok) prefabrik dalında kalır; kabul kaydı olsa da çelik aday seti açılmaz (prefabrik akışı değişmez)
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("88 m² 2+1", talep(ozet="88 m² 2+1", alan_m2=88, oda_programi="2+1"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] != "secenek" and sorgu(depo, "SELECT count(*) AS n FROM secenek_setleri")[0]["n"] == 0
    d, _ = depo.konusma_oku(NUMARA_A)
    assert not d.get("secenek_seti")
    assert depo.mesaj_kaydet(mesaj("88 m² 2+1 prefabrik", talep(ozet="88 m² 2+1 prefabrik", alan_m2=88, oda_programi="2+1", yapi_turu="prefabrik"), bayi=BAYI_KART))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] != "secenek" and sorgu(depo, "SELECT count(*) AS n FROM secenek_setleri")[0]["n"] == 0


def test_kat_suzgeci_ve_uyan_yoksa_bugunku_davranis(depo, wa, hizli_genel):
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("95 m² 3+1 tek kat çelik", talep(ozet="95 m² 3+1 tek kat çelik", alan_m2=95, oda_programi="3+1", yapi_turu="celik", kat_sayisi=1), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "sor" and "model_veya_olcu" in r["gerekce"]              # yedi aday 2+1: 3+1'e uyan yok → katalog önerisi (İE-07 P2 kat kuralı)
    govde = sorgu(depo, "SELECT govde FROM giden ORDER BY sira")[0]["govde"]
    assert "Ç1151" in govde and "Ç1241" in govde and "çift kat" not in govde
    # 2 kat söylenirse tek katlı yedi aday süzülür
    assert depo.mesaj_kaydet(mesaj("95 m² 2+1 çift katlı çelik", talep(ozet="95 m² 2+1 çift kat çelik", alan_m2=95, oda_programi="2+1", yapi_turu="celik", kat_sayisi=2), bayi=BAYI_KART))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "sor" and "model_veya_olcu" in r2["gerekce"]


def test_dis_olcu_celikte_alan_yolu_grid_yok(depo, wa, hizli_genel):
    kabul(depo, YEDI)
    assert depo.mesaj_kaydet(mesaj("9x10 m 2+1 çelik", talep(ozet="9x10 2+1 çelik", dis_olcu={"en_m": 9, "boy_m": 10}, oda_programi="2+1", yapi_turu="celik"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "secenek" and "7 aday" in r["gerekce"]                   # 90 m² ±%10: yedisi de; GRID_SABLON'a girmedi


# ───────────────────────── A3 ─────────────────────────
def test_secim_r01_genel_motor_satirlar_ve_zarf(depo, wa, hizli_genel):
    kabul(depo)
    assert depo.mesaj_kaydet(mesaj("Ç8801 olsun", talep(ozet="Ç8801 istiyor", katalog_kodu="Ç8801"), bayi=BAYI_KART))
    isle_hepsi(depo); kalici.gonder(depo, wa)
    st = sorgu(depo, "SELECT id, dis_id FROM giden WHERE kind = 'interactive'")[0]
    sid = sorgu(depo, "SELECT id FROM secenek_setleri")[0]["id"]
    assert depo.mesaj_kaydet(buton(f"s:{sid}:Ç8801K", context_id=st["dis_id"]))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri" and "Ç8801K" in r["gerekce"]
    rev = sorgu(depo, "SELECT is_emri_no, rev, is_emri, durum, pdf_yolu, dxf_sha256, ekler FROM revizyonlar")[0]
    ie = rev["is_emri"]
    assert rev["rev"] == 1 and rev["durum"] == "onay_bekliyor" and rev["dxf_sha256"] is None and rev["pdf_yolu"].endswith("C8801K_pafta.pdf")
    assert ie["yapi"]["sistem"] == "celik" and ie["yapi"]["motor"] == "genel" and ie["yapi"]["tanim"] == "modeller/C8801K.json" and ie["yapi"]["degisiklikler"] == []
    assert "mahaller" not in ie and "duvarlar" not in ie                            # tanım gömülmez
    assert ie["yapi"]["tanim_sha256"] == hashlib.sha256((KOK / "modeller" / "C8801K.json").read_bytes()).hexdigest()
    assert ie["bilgi"]["bayi_adi"] == "Deneme Bayi A" and ie["bilgi"]["bayi_telefonu"] == NUMARA_A and "kunye" not in ie     # D-09: kart numarası, gönderici kimliği yok
    assert rev["ekler"]["gorsel"]["filename"] == "C8801K_bayi_gorsel.png" and rev["ekler"]["ifc"]["sema_hatasi"] == 0 and "ucb" not in rev["ekler"]
    assert rev["ekler"]["yukleme_listesi"]["bayiye_gider"] is False
    satirlar = sorgu(depo, "SELECT kind, satir, revizyon_id FROM giden WHERE mesaj_id = (SELECT kaynak_mesaj_id FROM revizyonlar) ORDER BY sira")
    assert [s["kind"] for s in satirlar] == ["interactive", "document"] and all(s["revizyon_id"] for s in satirlar)
    assert sorted(b["reply"]["id"] for b in satirlar[0]["satir"]["interactive"]["action"]["buttons"]) == sorted([f"o:{rev['is_emri_no']}:1", f"r:{rev['is_emri_no']}:1"])
    assert satirlar[0]["satir"]["file"].endswith("C8801K_bayi_gorsel.png") and satirlar[1]["satir"]["filename"] == f"Portman_{rev['is_emri_no']}_r01.pdf"
    st_son = sorgu(depo, "SELECT durum, secilen_kod FROM secenek_setleri")[0]
    assert st_son["durum"] == "secildi" and st_son["secilen_kod"] == "Ç8801K"
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor" and d["revizyon"] == 0 and d["son_is_emri"]["yapi"]["kod"] == "Ç8801K"        # konuşma sıfırlanmadı (taban kod)
    sonuc = sorgu(depo, "SELECT sonuc FROM isler ORDER BY id DESC")[0]["sonuc"]
    assert NUMARA_A not in json.dumps(sonuc, ensure_ascii=False) and sonuc["cizim"]["motor"] == "genel" and sonuc["cizim"]["set"] == "kurallar.json"
    assert NUMARA_A not in W.baglam_ozeti(type("K", (), {"d": d})()) and "Ç8801-K" in W.baglam_ozeti(type("K", (), {"d": d})())
    # eski set düğmesi artık geçersiz; onay düğmesi çalışır
    kalici.gonder(depo, wa)
    assert depo.mesaj_kaydet(buton(f"s:{sid}:Ç8801L", context_id=st["dis_id"]))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "cevapla" and "set zaten seçilmiş" in r2["gerekce"]


def test_varyant_ve_kt_kodu_dogrudan_r01_kt_adsiz(depo, wa, hizli_genel):
    kabul(depo, YEDI)
    for metin, kod, beklenen in (("C8801K olsun", "C8801K", "Ç8801K"), ("KT-01", "KT-01", "KT01"), ("Ç8801 çatı L olsun", "Ç8801", "Ç8801L")):
        time.sleep(1.1)                                       # İş Emri numarası saniyeye bağlı: ardışık planlar aynı numarayı almasın (bugünkü kural)
        assert depo.mesaj_kaydet(mesaj(metin, talep(ozet=metin, katalog_kodu=kod, niyet="yeni_talep"), bayi=BAYI_KART))
        [r] = isle_hepsi(depo)
        assert r["eylem"] == "is_emri" and beklenen in r["gerekce"], (metin, r)
        ie = sorgu(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC")[0]["is_emri"]
        assert ie["yapi"]["kod"] == beklenen
        if beklenen == "KT01":
            assert ie["sunum"]["musteri_projesi"] is True


def test_patron_ve_kart_disi_numara_antete_girmez(depo, wa, hizli_genel):
    kabul(depo)
    patron = {"kod": "PATRON", "ad": "Patron", "rol": "patron", "numara": NUMARA_A}
    g = mesaj("Ç8801K", talep(ozet="Ç8801K", katalog_kodu="Ç8801K"), bayi=patron); g["role"] = "patron"
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri"
    ie = sorgu(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC")[0]["is_emri"]
    assert ie["bilgi"]["bayi_telefonu"] is None and ie["bilgi"]["bayi_adi"] == "Patron"
    # bayi kartındaki numara gönderenden farklıysa (olmamalı) numara yazılmaz; LLM'in müşteri telefonu asla kullanılmaz
    baska = {**BAYI_KART, "numara": "900000000999"}
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("Ç8801L", talep(ozet="Ç8801L", katalog_kodu="Ç8801L", musteri={"telefon": "900000000777", "sevk_adresi": "Deneme Mah. tel 900000000777"},
                                                   ozel_istekler=["müşteri 900000000777 aranacak"], bina_ozellikleri={"Dış boya rengi": "krem 900000000777"}), bayi=baska))
    [r2] = isle_hepsi(depo)
    ie2 = sorgu(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC")[0]["is_emri"]
    assert r2["eylem"] == "is_emri" and ie2["bilgi"]["bayi_telefonu"] is None and "900000000777" not in json.dumps(ie2)   # başka numara reddedilir (D-09)
    assert ie2["bilgi"]["sevk_adresi"] == "Deneme Mah. tel …" and ie2["bilgi"]["ozel_istekler"] == ["müşteri … aranacak"] and ie2["bilgi"]["ozellikler"]["Dış Boya Rengi"] == "krem …"
    # adsız kart: depo numarayı ad olarak verir; antete ad olarak numara yazılmaz (KVKK denetçisi 12.10)
    adsiz = {"kod": "PATRON", "ad": "900000000101", "rol": "patron", "numara": "900000000101"}
    g2 = mesaj("Ç8801K", talep(ozet="Ç8801K", katalog_kodu="Ç8801K"), bayi=adsiz); g2["role"] = "patron"   # varyant kodu: set sorulmaz, doğrudan r01
    time.sleep(1.1)
    assert depo.mesaj_kaydet(g2)
    [r3] = isle_hepsi(depo)
    ie3 = sorgu(depo, "SELECT is_emri FROM revizyonlar ORDER BY id DESC")[0]["is_emri"]
    assert r3["eylem"] == "is_emri", r3.get("gerekce")
    assert ie3["bilgi"]["bayi_adi"] == "" and ie3["bilgi"]["bayi_telefonu"] is None


def test_cati_secildikten_sonra_revizyon_seti_yeniden_sormaz(depo, wa, hizli_genel):
    # kod incelemesi (12.10): katalog çatısı seçilip r01 gittikten sonra aynı kodla gelen revizyon üç çatıyı yeniden sormamalı
    kabul(depo)
    assert depo.mesaj_kaydet(mesaj("Ç8801 olsun", talep(ozet="Ç8801 istiyor", katalog_kodu="Ç8801"), bayi=BAYI_KART))
    isle_hepsi(depo); kalici.gonder(depo, wa)
    sid = sorgu(depo, "SELECT id FROM secenek_setleri")[0]["id"]
    st = sorgu(depo, "SELECT dis_id FROM giden WHERE kind = 'interactive'")[0]
    assert depo.mesaj_kaydet(buton(f"s:{sid}:Ç8801", context_id=st["dis_id"]))
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "is_emri" and "Ç8801 " in r1["gerekce"] + " "
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("sevk adresi Deneme İlçesi olsun", talep(ozet="sevk adresi", katalog_kodu="Ç8801", niyet="revizyon",
                                                                           musteri={"sevk_adresi": "Deneme İlçesi"}), bayi=BAYI_KART))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "is_emri", r2
    revs = sorgu(depo, "SELECT rev, durum, is_emri FROM revizyonlar ORDER BY rev")
    assert [(x["rev"], x["durum"]) for x in revs] == [(1, "yerini_aldi"), (2, "onay_bekliyor")]
    assert revs[1]["is_emri"]["yapi"]["kod"] == "Ç8801" and revs[1]["is_emri"]["bilgi"]["sevk_adresi"] == "Deneme İlçesi"
    assert sorgu(depo, "SELECT count(*) AS n FROM secenek_setleri")[0]["n"] == 1                      # yeni set açılmadı
    # desteklenmeyen varyant (çatı tarifi, kapı) → yönlendirme, sessizce düşmez (K21)
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("çatıyı kırma yap", talep(ozet="çatı kırma", katalog_kodu="Ç8801", niyet="revizyon",
                                                             varyantlar=[{"tur": "cati_degistir", "aciklama": "çatıyı kırma yap", "parametreler": {"tip": "kırma"}}]), bayi=BAYI_KART))
    [r3] = isle_hepsi(depo)
    assert r3["eylem"] == "yonlendir" and "cati_degistir" in r3["gerekce"]


@pytest.mark.skipif(not (KOK / "modeller" / "C8801K.json").exists(), reason="model tanımı yok")
def test_gercek_genel_motor_r01_pdf_antet_taslak(depo, wa):
    """Gerçek genel motor (perspektif VTK varsa çizilir, yoksa iş düşmez): PDF 2 sayfa A4 yatay, 1. sayfada TASLAK, antette ad + kart numarası."""
    kabul(depo)
    assert depo.mesaj_kaydet(mesaj("Ç8801K olsun", talep(ozet="Ç8801K istiyor", katalog_kodu="Ç8801K", bina_ozellikleri={"Dış boya rengi": "krem"},
                                                           ozel_istekler=["çatı antrasit olsun"]), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    rev = sorgu(depo, "SELECT pdf_yolu, durum, ekler, is_emri FROM revizyonlar")[0]
    assert rev["durum"] == "onay_bekliyor" and Path(rev["pdf_yolu"]).is_file()
    import fitz
    with fitz.open(rev["pdf_yolu"]) as d:
        assert len(d) == 2 and (round(d[0].rect.width), round(d[0].rect.height)) == (842, 595)
        s1 = [w[4] for w in d[0].get_text("words")]
    assert "TASLAK" in s1 and "Deneme" in s1 and "Bayi" in s1 and NUMARA_A in s1 and "r01" in s1
    assert "krem" in s1 and "antrasit" in s1                                   # bayinin söylediği özellik satıra, özel istek listeye (K21)
    assert rev["ekler"]["gorsel"]["filename"] == "C8801K_bayi_gorsel.png" and Path(rev["ekler"]["gorsel"]["file"]).stat().st_size <= 5 * 1024 * 1024
    assert rev["ekler"]["ifc"]["sema_hatasi"] == 0 and Path(rev["ekler"]["yukleme_listesi"]["dosya"]).is_file()
    kalici.gonder(depo, wa)
    assert [g["kind"] for g in wa.gonderilen] == ["interactive", "document"]
    assert NUMARA_A not in json.dumps(sorgu(depo, "SELECT sonuc FROM isler")[0]["sonuc"])


def test_ozellik_alanlari_sablonla_ayni():
    from beyin import celik
    from motor.genel import sablon_pafta
    assert celik.OZELLIK_ALANLARI == sablon_pafta.OZELLIK_SIRASI


# ───────────────────────── A4 (PR-2b) ─────────────────────────
def r01(depo, kod: str = "Ç8801K") -> dict:
    """Çelik r01 (varyant ya da KT kodu: set sorulmaz) ve gönderim; dönen: revizyon satırı."""
    assert depo.mesaj_kaydet(mesaj(f"{kod} olsun", talep(ozet=f"{kod} istiyor", katalog_kodu=kod), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    return sorgu(depo, "SELECT id, proje_id, is_emri_no, rev, is_emri, durum, ekler FROM revizyonlar ORDER BY id DESC")[0]


def revize(depo, metin: str, **alan) -> dict:
    time.sleep(1.1)                                           # İş Emri numarası saniyeye bağlı (bugünkü kural)
    assert depo.mesaj_kaydet(mesaj(metin, talep("revizyon", ozet=metin, **alan), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    return r


def son_rev(depo) -> dict:
    return sorgu(depo, "SELECT id, proje_id, is_emri_no, rev, is_emri, durum, ekler FROM revizyonlar ORDER BY id DESC")[0]


def test_r02_pencere_olcusu_ayni_proje_once_sonra(depo, wa, hizli_genel):
    kabul(depo)
    ilk = r01(depo)
    r = revize(depo, "mutfak penceresi 120x120 olsun", pencereler=[{"mahal": "mutfak", "olcu": "120x120", "islem": "degistir"}])
    assert r["eylem"] == "is_emri" and "pencere_olcu" in r["gerekce"], r
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert rev["rev"] == 2 and rev["proje_id"] == ilk["proje_id"] and rev["durum"] == "onay_bekliyor"
    assert [(d["op"], d["aciklik"], d["en"], d["yuk"]) for d in y["degisiklikler"]] == [("pencere_olcu", "P5", 120, 120)]
    assert y["onceki"]["kod"] == "Ç8801K" and y["onceki"]["revizyon"] == 1 and y["tanim"] == "modeller/C8801K.json"
    assert sorgu(depo, "SELECT durum FROM revizyonlar WHERE id = %s", ilk["id"])[0]["durum"] == "yerini_aldi"
    assert rev["ekler"]["gorsel"]["kaynak"] == "once_sonra" and rev["ekler"]["gorsel"]["filename"] == "C8801K_once_sonra.png"
    assert Path(rev["ekler"]["gorsel"]["file"]).is_file() and rev["ekler"]["kart"]["filename"] == "C8801K_bayi_gorsel.png"
    tanim = json.loads((Path(rev["ekler"]["gorsel"]["file"]).parent / "tanim.json").read_text(encoding="utf-8"))
    p5 = next(a for a in tanim["acikliklar"] if a["ad"] == "P5")
    assert (p5["en"], p5["yuk"], p5["alt"], p5["etiket"]) == (120, 120, 80, "120/120")            # çizilen tanımda uygulandı
    satir = sorgu(depo, "SELECT satir, govde FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC, sira DESC")[0]
    assert satir["satir"]["file"].endswith("C8801K_once_sonra.png") and "Uygulanan: Mutfak penceresi" in satir["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["revizyon"] == 1 and d["son_is_emri"]["revizyon"] == 2
    oz = W.baglam_ozeti(type("K", (), {"d": d})())
    assert "uygulanan: Mutfak penceresi" in oz and NUMARA_A not in oz
    # r03: önceki değişiklik birikir (aynı proje)
    r3 = revize(depo, "dışlar 140'lık olsun")
    rev3 = son_rev(depo)
    assert r3["eylem"] == "is_emri" and rev3["rev"] == 3 and rev3["proje_id"] == ilk["proje_id"]
    assert [d["op"] for d in rev3["is_emri"]["yapi"]["degisiklikler"]] == ["pencere_olcu", "dis_karkas_140"]
    t3 = json.loads((Path(rev3["ekler"]["gorsel"]["file"]).parent / "tanim.json").read_text(encoding="utf-8"))
    assert t3["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2" and next(a for a in t3["acikliklar"] if a["ad"] == "P5")["etiket"] == "120/120"


def test_okuma_iki_aday_gorselli_soru_ve_dugme_2(depo, wa, hizli_genel):
    kabul(depo)
    r01(depo); kalici.gonder(depo, wa)
    r = revize(depo, "salondaki sol taraftaki pencere 120x180 olsun", pencereler=[{"mahal": "salon", "olcu": "120x180", "duvar": "sol", "islem": "degistir"}])
    assert r["eylem"] == "sor" and "okuma" in r["gerekce"], r
    soru = sorgu(depo, "SELECT satir, govde, dis_id FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC, sira DESC")[0]
    assert [b["reply"]["id"] for b in soru["satir"]["interactive"]["action"]["buttons"]] == ["q:okuma:1", "q:okuma:2", "q:okuma:0"]
    assert soru["satir"]["file"].endswith("_okuma.png") and Path(soru["satir"]["file"]).is_file()
    assert "öne yakın" in soru["govde"] and "arkaya yakın" in soru["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["son_soru_alani"] == "okuma" and d["revizyon"] == 0 and [a["aciklik"] for a in d["okuma_bekleyen"]["adaylar"]] == ["P3", "P4"]
    assert sorgu(depo, "SELECT alan, durum FROM sorular ORDER BY id DESC")[0] == {"alan": "okuma", "durum": "acik"}
    kalici.gonder(depo, wa)
    dis = sorgu(depo, "SELECT dis_id FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC, sira DESC")[0]["dis_id"]
    time.sleep(1.1)
    assert depo.mesaj_kaydet(buton("q:okuma:2", context_id=dis))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "is_emri", r2
    rev = son_rev(depo)
    assert rev["rev"] == 2 and [(d_["aciklik"], d_["en"], d_["yuk"]) for d_ in rev["is_emri"]["yapi"]["degisiklikler"]] == [("P4", 120, 180)]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["revizyon"] == 1 and "okuma_bekleyen" not in d and d.get("son_soru_alani") is None
    assert sorgu(depo, "SELECT alan, durum FROM sorular ORDER BY id DESC")[0] == {"alan": "okuma", "durum": "cevaplandi"}


def test_okuma_hicbiri_once_soru_sonra_yonlendirme(depo, wa, hizli_genel):
    kabul(depo)
    r01(depo); kalici.gonder(depo, wa)
    assert revize(depo, "yaşam alanı penceresi 160x120")["eylem"] == "sor"           # 3 aday: numaralı metin sorusu (görselsiz)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert len(d["okuma_bekleyen"]["adaylar"]) == 3 and d["son_soru_alani"] == "okuma"
    r = revize(depo, "hiçbiri")
    assert r["eylem"] == "sor" and "okuma_metin" in r["gerekce"]
    assert "Neyi değiştirelim?" in sorgu(depo, "SELECT govde FROM giden ORDER BY olusturuldu DESC, sira DESC")[0]["govde"]
    # bayi açıkça söyler: r02
    r = revize(depo, "yaşam alanının ön cephedeki penceresi 160x180 olsun")
    assert r["eylem"] == "is_emri", r
    assert [(x["aciklik"], x["en"], x["yuk"]) for x in son_rev(depo)["is_emri"]["yapi"]["degisiklikler"]] == [("P1", 160, 180)]
    # ikinci kez "hiçbiri": yönlendirme (insan)
    assert revize(depo, "salondaki sol taraftaki pencere 120x180")["eylem"] == "sor"
    r = revize(depo, "hiçbiri")
    assert r["eylem"] == "sor"
    assert revize(depo, "salondaki sol taraftaki pencere 120x180")["eylem"] == "sor"
    r = revize(depo, "ikisi de değil")
    assert r["eylem"] == "yonlendir" and "hiçbiri" in r["gerekce"]


def test_cati_degisikligi_ayni_proje_r02_tanim_L(depo, wa, hizli_genel):
    kabul(depo)
    ilk = r01(depo)
    r = revize(depo, "çatı L olsun", varyantlar=[{"tur": "cati_degistir", "aciklama": "çatı L olsun", "parametreler": {}}])
    assert r["eylem"] == "is_emri" and "Ç8801L" in r["gerekce"], r
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert rev["rev"] == 2 and rev["proje_id"] == ilk["proje_id"] and y["tanim"] == "modeller/C8801L.json" and y["kod"] == "Ç8801L"
    assert [(d["op"], d["kod"]) for d in y["degisiklikler"]] == [("cati_varyanti", "Ç8801L")] and y["onceki"]["kod"] == "Ç8801K"
    assert rev["ekler"]["gorsel"]["kaynak"] == "once_sonra"
    assert sorgu(depo, "SELECT count(*) AS n FROM secenek_setleri")[0]["n"] == 0                     # çatı seti yeniden sorulmadı
    # r03 pencere: çatı değişikliği tanım dosyasında, listede birikmez; pencere eklenir
    revize(depo, "mutfak penceresi 120x120 olsun")
    y3 = son_rev(depo)["is_emri"]["yapi"]
    assert y3["tanim"] == "modeller/C8801L.json" and [d["op"] for d in y3["degisiklikler"]] == ["pencere_olcu"]


def test_dis_140_c8801_ve_karkas_modelli_kt_yonlendirme(depo, wa, hizli_genel):
    kabul(depo, YEDI)
    r01(depo)
    r = revize(depo, "dışlar 140'lık olsun")
    assert r["eylem"] == "is_emri" and [d["op"] for d in son_rev(depo)["is_emri"]["yapi"]["degisiklikler"]] == ["dis_karkas_140"]
    time.sleep(1.1)
    assert depo.mesaj_kaydet(mesaj("KT-01 yeni talep", talep(ozet="KT-01", katalog_kodu="KT-01"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri" and "KT01" in r["gerekce"]
    r = revize(depo, "dışlar 140'lık olsun")
    assert r["eylem"] == "yonlendir" and "celik_modeli" in r["gerekce"]                              # karkas modeli olan KT: mühendise


def test_celik_cizim_dusunce_hak_dusmez_ve_patron_maskeli(depo, wa, monkeypatch, hizli_genel):
    """A4 "hak düşmez" (PR-2a'daki "doğrulamadan geçmedi" vakasının yerine): çelik çizim düşerse konuşma önceki planda kalır, revizyon
    satırı yazılmaz, eski planın düğmeleri geçerli; bayiye önceki planın geçerli olduğu, Patron'a maskeli hata; sonra aynı istek r02 olur."""
    kabul(depo)
    ilk = r01(depo); kalici.gonder(depo, wa)
    d_once, _ = depo.konusma_oku(NUMARA_A)
    from motor.genel import uret

    def kirik(tanim_yolu, hedef, **k):
        raise RuntimeError("sahte çökme; iletide numara 900000000101 geçiyor")
    monkeypatch.setattr(uret, "uret", kirik)
    r = revize(depo, "mutfak penceresi 120x120 olsun")
    assert r["eylem"] == "cizim_hatasi" and "hak düşmez" in r["gerekce"], r
    assert [(x["rev"], x["durum"]) for x in sorgu(depo, "SELECT rev, durum FROM revizyonlar ORDER BY id")] == [(1, "onay_bekliyor")]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["revizyon"] == d_once["revizyon"] == 0 and d["son_is_emri"]["is_emri_no"] == ilk["is_emri_no"] and d["asama"] == "onay_bekliyor"
    satirlar = sorgu(depo, "SELECT alici, kind, govde FROM giden WHERE mesaj_id = (SELECT mesaj_id FROM isler ORDER BY id DESC LIMIT 1) ORDER BY sira")
    bayiye = [s["govde"] for s in satirlar if s["alici"] == NUMARA_A]
    assert len(bayiye) == 1 and f"önceki planınız ({ilk['is_emri_no']} r01) geçerli, revizyon hakkınız düşmedi" in bayiye[0]
    patron = [s for s in satirlar if s["alici"] == "PATRON"]
    assert [s["kind"] for s in patron] == ["text", "template"] and "900000000101" not in patron[0]["govde"] and "…0101" in patron[0]["govde"]
    sonuc = sorgu(depo, "SELECT sonuc FROM isler ORDER BY id DESC")[0]["sonuc"]
    assert "900000000101" not in json.dumps(sonuc) and sonuc["cizim"]["passed"] is False and "bilgi" not in json.dumps(sonuc["denenen"])
    # eski planın onay düğmesi hâlâ geçerli (onay beklenen plan r01)
    assert ET_coz_gecerli(d, f"o:{ilk['is_emri_no']}:1")
    monkeypatch.setattr(uret, "uret", sahte_genel)
    r = revize(depo, "mutfak penceresi 120x120 olsun")
    assert r["eylem"] == "is_emri" and son_rev(depo)["rev"] == 2


def ET_coz_gecerli(d: dict, kimlik: str) -> bool:
    import etkilesim as ET
    return ET.coz({"reply_id": kimlik}, d, None).get("gecerli") is True


def test_celik_r01_cizim_dusunce_talep_durur(depo, wa, monkeypatch):
    kabul(depo)
    from motor.genel import uret
    monkeypatch.setattr(uret, "uret", lambda tanim_yolu, hedef, **k: (_ for _ in ()).throw(RuntimeError("çöktü")))
    assert depo.mesaj_kaydet(mesaj("Ç8801K", talep(ozet="Ç8801K", katalog_kodu="Ç8801K"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "cizim_hatasi" and sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 0
    assert "talebiniz duruyor, revizyon hakkınız düşmedi" in sorgu(depo, "SELECT govde FROM giden WHERE alici = %s", NUMARA_A)[0]["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert not d.get("son_is_emri") and d.get("revizyon", 0) == 0


def test_dorduncu_revizyondan_sonra_muhendis_incelemesi(depo, wa, hizli_genel):
    kabul(depo)
    r01(depo)
    for i, olcu in enumerate(("120x120", "120x180", "120x120", "120x180"), 2):
        r = revize(depo, f"mutfak penceresi {olcu} olsun")
        assert r["eylem"] == "is_emri" and son_rev(depo)["rev"] == i, (i, r)
    r = revize(depo, "mutfak penceresi 120x120 olsun")
    assert r["eylem"] == "yonlendir" and r["gerekce"] == "revizyon sınırı"
    govde = sorgu(depo, "SELECT govde FROM giden WHERE alici = %s ORDER BY olusturuldu DESC, sira DESC", NUMARA_A)[0]["govde"]
    assert "4 revizyon hakkı doldu; plan mühendis incelemesine alındı." in govde


def test_prefabrik_cizim_dusunce_bugunku_davranis(depo, wa, monkeypatch):
    """A5: pano Motor'u düşerse bugünkü yol (revizyon 'dogrulanmadi', bayiye "doğrulamadan geçmedi"); hak düşmez yalnız çelikte."""
    from motor import dxf_out

    def kirik(ie, hedef, *a, **k):
        raise RuntimeError("pano motoru çöktü")
    monkeypatch.setattr(dxf_out, "uret", kirik)
    assert depo.mesaj_kaydet(mesaj("P6001 olsun", talep(ozet="P6001", katalog_kodu="P6001"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri"
    assert sorgu(depo, "SELECT durum FROM revizyonlar")[0]["durum"] == "dogrulanmadi"
    assert any("doğrulamadan geçmedi" in s["govde"] for s in sorgu(depo, "SELECT govde FROM giden WHERE alici = %s", NUMARA_A))
