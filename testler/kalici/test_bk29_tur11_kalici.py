"""BK-29 tur 11 · D-101 çelik eki kalıcı akışta: çelik planda da revizyon talebin numarasını taşır (gerçek Postgres, sahte WhatsApp,
hızlı sahte genel motor).

Kayıt: `revizyonlar` satırları tek numarada rev 1, 2, 3; tek proje; PDF `projects/<no>/rNN/` altında. Bayiye giden PDF adı ve
Onayla / Revize et düğmeleri aynı numarayla, revizyonla ayrılır.
Hak düşmez (İE-08 A4): çelik çizim düşünce konuşma önceki plana döner. Düşen denemenin klasörü `rNN-dusen-<8 hane>` adını alır
(`worker._dusen_klasoru_ayir`); aynı istek yeniden gelince aynı numaranın rNN'i olur.
Mühendis kontrolü (numara, revizyon) çiftiyle tutulur: r01'in kontrolü "plan değişti" olur, r02 onaylanınca kendi kontrolü açılır.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_bk29_tur11_kalici.py -q
"""
from __future__ import annotations
import json
import time
from pathlib import Path

from conftest import NUMARA_A, sorgu

import kalici
import worker as W
from test_celik_akisi import buton, hizli_genel, isle_hepsi, kabul, r01, revize, sahte_genel, son_rev  # noqa: F401
from test_muhendis import celik_onay, genel_liste, muhendis_karti  # noqa: F401
from test_plan_akisi import BAYI_KART, URETIM, _secilmis_yeni_plan, duzenleyici, uretici  # noqa: F401
from test_plan_akisi import isle_hepsi as isle_uretim
from conftest import mesaj, talep

P120 = {"pencereler": [{"mahal": "mutfak", "olcu": "120x120", "islem": "degistir"}]}
P180 = {"pencereler": [{"mahal": "mutfak", "olcu": "120x180", "islem": "degistir"}]}


def _dugmeler(depo, mesaj_id: str) -> list[str]:
    out = []
    for x in sorgu(depo, "SELECT satir FROM giden WHERE mesaj_id = %s AND kind = 'interactive' AND alici <> 'PATRON' ORDER BY sira", mesaj_id):
        out += [b["reply"]["id"] for b in ((x["satir"].get("interactive") or {}).get("action") or {}).get("buttons") or []]
    return out


def _belge_adlari(depo, mesaj_id: str) -> list[str]:
    return [x["satir"].get("filename") for x in sorgu(depo, "SELECT satir FROM giden WHERE mesaj_id = %s AND kind = 'document' ORDER BY sira", mesaj_id)]


def test_celik_revizyonlar_tek_numarada_kalici(depo, wa, hizli_genel):
    kabul(depo)
    ilk = r01(depo); kalici.gonder(depo, wa)
    no = ilk["is_emri_no"]
    r2 = revize(depo, "mutfak penceresi 120x120 olsun", **P120); kalici.gonder(depo, wa)
    assert r2["eylem"] == "is_emri", r2
    r3 = revize(depo, "mutfak penceresi 120x180 olsun", **P180); kalici.gonder(depo, wa)
    assert r3["eylem"] == "is_emri", r3
    satirlar = sorgu(depo, "SELECT rev, is_emri_no, proje_id, durum, pdf_yolu, is_emri FROM revizyonlar ORDER BY rev")
    assert [(x["rev"], x["is_emri_no"]) for x in satirlar] == [(1, no), (2, no), (3, no)]
    assert len({x["proje_id"] for x in satirlar}) == 1
    assert [x["durum"] for x in satirlar] == ["yerini_aldi", "yerini_aldi", "onay_bekliyor"]
    assert [x["ilk_is_emri_no"] for x in sorgu(depo, "SELECT ilk_is_emri_no FROM projeler")] == [no]
    for x in satirlar:
        pdf = Path(x["pdf_yolu"])
        assert pdf.is_file() and pdf.parent == W.KANAL / "projects" / no / f"r{x['rev']:02d}"
        assert x["is_emri"]["is_emri_no"] == no and x["is_emri"]["yapi"]["sistem"] == "celik"
    assert _belge_adlari(depo, r3["mesaj_id"]) == [f"Portman_{no}_r03.pdf"]
    assert sorted(_dugmeler(depo, r3["mesaj_id"])) == sorted([f"o:{no}:3", f"r:{no}:3"])
    assert depo.revizyon(NUMARA_A, no)["rev"] == 3 and depo.revizyon(NUMARA_A, no, 2)["rev"] == 2


def test_celik_cizim_dusunce_ayni_istek_ayni_numarayla_r02(depo, wa, monkeypatch, hizli_genel):
    """Çizim çökerse (istisna) düşen denemenin klasörü ayrılır; aynı istek yeniden gelince …NNNN r02 olur (yeni numara değil)."""
    kabul(depo)
    ilk = r01(depo); kalici.gonder(depo, wa)
    no = ilk["is_emri_no"]
    kok = W.KANAL / "projects" / no
    from motor.genel import uret
    monkeypatch.setattr(uret, "uret", lambda tanim_yolu, hedef, **k: (_ for _ in ()).throw(RuntimeError("sahte çökme")))
    r = revize(depo, "mutfak penceresi 120x120 olsun", **P120)
    assert r["eylem"] == "cizim_hatasi", r
    assert not (kok / "r02").exists()
    [dusen] = [p for p in kok.iterdir() if p.name.startswith("r02-dusen-")]
    assert (dusen / "failure.json").is_file()
    denenen = sorgu(depo, "SELECT sonuc FROM isler ORDER BY id DESC")[0]["sonuc"]["denenen"]
    assert (denenen["is_emri_no"], denenen["revizyon"]) == (no, 2)                      # düşen deneme de talebin numarasıyla denendi
    monkeypatch.setattr(uret, "uret", sahte_genel)
    r = revize(depo, "mutfak penceresi 120x120 olsun", **P120); kalici.gonder(depo, wa)
    assert r["eylem"] == "is_emri", r
    rev = son_rev(depo)
    assert (rev["rev"], rev["is_emri_no"], rev["proje_id"]) == (2, no, ilk["proje_id"])
    pdf = Path(sorgu(depo, "SELECT pdf_yolu FROM revizyonlar WHERE rev = 2")[0]["pdf_yolu"])
    assert pdf.is_file() and pdf.parent == kok / "r02"
    assert (dusen / "failure.json").is_file()                                           # düşen denemenin kaydı duruyor
    assert sorted(_dugmeler(depo, r["mesaj_id"])) == sorted([f"o:{no}:2", f"r:{no}:2"])


def test_celik_dogrulamadan_gecmeyen_cizimin_yollari_ayrilan_klasorde(depo, wa, monkeypatch, hizli_genel):
    """Çizim üretildi ama doğrulamadan geçmedi (istisna yok): iş kaydındaki PDF yolu ayrılan klasörü gösterir, dosya oradadır."""
    kabul(depo)
    ilk = r01(depo); kalici.gonder(depo, wa)
    no = ilk["is_emri_no"]

    def gecmeyen(tanim_yolu, hedef, **k):
        m = sahte_genel(tanim_yolu, hedef, **k)
        (Path(hedef) / "validation.json").write_text(json.dumps({"passed": False, "errors": ["sahte doğrulama hatası"]}), encoding="utf-8")
        return m
    from motor.genel import uret
    monkeypatch.setattr(uret, "uret", gecmeyen)
    r = revize(depo, "mutfak penceresi 120x120 olsun", **P120)
    assert r["eylem"] == "cizim_hatasi", r
    cizim = sorgu(depo, "SELECT sonuc FROM isler ORDER BY id DESC")[0]["sonuc"]["cizim"]
    pdf = Path(cizim["pdf"])
    assert cizim["passed"] is False and pdf.is_file() and pdf.parent.name.startswith("r02-dusen-") and pdf.parent.parent == W.KANAL / "projects" / no
    assert not (W.KANAL / "projects" / no / "r02").exists()
    assert [(x["rev"], x["durum"]) for x in sorgu(depo, "SELECT rev, durum FROM revizyonlar ORDER BY id")] == [(1, "onay_bekliyor")]


def test_celik_dolu_klasorde_yeni_numara_is_donmez(depo, wa, hizli_genel):
    kabul(depo)
    ilk = r01(depo); kalici.gonder(depo, wa)
    no = ilk["is_emri_no"]
    artik = W.KANAL / "projects" / no / "r02"            # kaydı yazılamamış yarım işin klasörü
    artik.mkdir(parents=True)
    (artik / "eski.pdf").write_bytes(b"%PDF-1.4\n% yarim is\n")
    r2 = revize(depo, "mutfak penceresi 120x120 olsun", **P120)
    assert r2["eylem"] == "is_emri", r2
    satirlar = sorgu(depo, "SELECT rev, is_emri_no, proje_id, pdf_yolu FROM revizyonlar ORDER BY rev")
    assert [x["rev"] for x in satirlar] == [1, 2] and satirlar[1]["is_emri_no"] != no
    assert len({x["proje_id"] for x in satirlar}) == 1
    assert [p.name for p in artik.iterdir()] == ["eski.pdf"]               # yarım işin klasörüne dokunulmadı
    yeni = satirlar[1]["is_emri_no"]
    r3 = revize(depo, "mutfak penceresi 120x180 olsun", **P180)
    assert r3["eylem"] == "is_emri", r3
    assert [(x["rev"], x["is_emri_no"]) for x in sorgu(depo, "SELECT rev, is_emri_no FROM revizyonlar ORDER BY rev")] == \
        [(1, no), (2, yeni), (3, yeni)]


def test_muhendis_kontrolu_numara_ve_revizyon_ciftiyle(depo, wa, genel_liste):
    """Onaylı r01'in üstüne revizyon: r01'in kontrolü "plan değişti" olur; aynı numaralı r02 onaylanınca kendi kontrolü açılır."""
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    r = revize(depo, "mutfak penceresi 120x120 olsun", **P120); kalici.gonder(depo, wa)
    assert r["eylem"] == "is_emri" and (son_rev(depo)["rev"], son_rev(depo)["is_emri_no"]) == (2, no), r
    assert depo.muhendis_kontrolu(no, 1)["durum"] == "plan_degisti" and depo.muhendis_kontrolu(no, 2) is None
    time.sleep(1.1)
    assert depo.mesaj_kaydet(buton(f"o:{no}:1"))                           # eski planın düğmesi r02'yi onaylamaz
    [e] = isle_hepsi(depo)
    assert e["gerekce"] != "plan onaylandı" and depo.muhendis_kontrolu(no, 2) is None, e
    time.sleep(1.1)
    assert depo.mesaj_kaydet(buton(f"o:{no}:2"))
    [o] = isle_hepsi(depo)
    assert o["gerekce"] == "plan onaylandı", o
    k1, k2 = depo.muhendis_kontrolu(no, 1), depo.muhendis_kontrolu(no, 2)
    assert k1["durum"] == "plan_degisti" and k2 is not None and k2["durum"] != "plan_degisti" and k2["id"] != k1["id"]


def test_yeni_cizilen_planin_revizyonu_da_numarayi_tasir(depo, wa, hizli_genel, uretici, duzenleyici):
    """İE-14: yeni çizilen planın revizyonu (`karar._yeni_plan_revizyonu`) da aynı kuralla: r02 r01'in numarasıyla."""
    _secilmis_yeni_plan(depo)
    ilk = son_rev(depo)
    assert ilk["rev"] == 1
    duzenleyici["cevap"] = {"islemler": [{"op": "dis_karkas_140"}], "uygulanamayan": []}
    assert depo.mesaj_kaydet(mesaj("dışlar 140'lık olsun", talep("revizyon", ozet="revizyon"), bayi=BAYI_KART))
    [r] = isle_uretim(depo, URETIM)
    assert r["eylem"] == "is_emri", r
    rev = son_rev(depo)
    assert (rev["rev"], rev["is_emri_no"], rev["proje_id"]) == (2, ilk["is_emri_no"], ilk["proje_id"])
    assert isinstance(rev["is_emri"]["yapi"]["tanim"], dict)                           # yeni plan: tanım zarfta gömülü
