"""BK-29 tur 10 · D-101 kalıcı akışta: prefabrik revizyon talebin numarasını taşır (gerçek Postgres, sahte WhatsApp, hızlı Motor).

Kayıt: `revizyonlar` satırları tek numarada rev 1, 2, 3; tek proje; PDF `projects/<no>/rNN/` altında (göç 001: UNIQUE (is_emri_no, rev)).
Bayiye giden: PDF adı ve Onayla / Revize et düğmeleri aynı numarayla, revizyonla ayrılır.
Yarım kalmış iş: sıradaki revizyon klasörü kayıtsız doluysa (`kalici.bir_is`: COMMIT'te kopan iş klasörünü bırakır) revizyon yeni
numara alır; iş "üzerine yazılmaz" çakışmasıyla sıraya dönüp durmaz.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_bk29_tur10_kalici.py -q
"""
from __future__ import annotations
import time
from pathlib import Path

from conftest import AYAR, NUMARA_A, mesaj, sorgu, talep

import kalici
import worker as W

KATMAN = {**AYAR, "mesaj_katmani": True}


def isle_hepsi(depo, ayar=KATMAN, en_cok: int = 5) -> list[dict]:
    out = []
    while len(out) < en_cok and (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def _r01(depo, wa) -> str:
    depo.mesaj_kaydet(mesaj("P6001", talep(ozet="P6001", katalog_kodu="P6001")))
    [r] = isle_hepsi(depo)
    assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    time.sleep(1.1)                       # numara saatten kurulur: sonraki plan başka saniyede (eski yolda başka numara çıkardı)
    return sorgu(depo, "SELECT is_emri_no FROM revizyonlar WHERE rev = 1")[0]["is_emri_no"]


def _pencere(depo, wa, olcu: str) -> dict:
    t = talep("revizyon", f"Yatak odası 1 penceresi {olcu}", pencereler=[{"mahal": "yatak odası 1", "olcu": olcu, "islem": "degistir"}])
    depo.mesaj_kaydet(mesaj(f"yatak odası 1 penceresi {olcu} olsun", t))
    sonuc = isle_hepsi(depo)
    kalici.gonder(depo, wa)
    assert len(sonuc) == 1, sonuc         # tek iş, tek sonuç: iş sıraya geri dönmedi
    return sonuc[0]


def _dugmeler(depo, mesaj_id: str) -> list[str]:
    out = []
    for x in sorgu(depo, "SELECT satir FROM giden WHERE mesaj_id = %s AND kind = 'interactive' AND alici <> 'PATRON' ORDER BY sira", mesaj_id):
        out += [b["reply"]["id"] for b in ((x["satir"].get("interactive") or {}).get("action") or {}).get("buttons") or []]
    return out


def test_revizyonlar_tek_numarada_kalici(depo, wa, hizli_motor):
    no = _r01(depo, wa)
    r2 = _pencere(depo, wa, "120x180")
    assert r2["eylem"] == "is_emri", r2
    time.sleep(1.1)
    r3 = _pencere(depo, wa, "120x160")
    assert r3["eylem"] == "is_emri", r3
    satirlar = sorgu(depo, "SELECT rev, is_emri_no, proje_id, durum, pdf_yolu, is_emri FROM revizyonlar ORDER BY rev")
    assert [(x["rev"], x["is_emri_no"]) for x in satirlar] == [(1, no), (2, no), (3, no)]
    assert len({x["proje_id"] for x in satirlar}) == 1
    assert [x["durum"] for x in satirlar] == ["yerini_aldi", "yerini_aldi", "onay_bekliyor"]
    assert [x["ilk_is_emri_no"] for x in sorgu(depo, "SELECT ilk_is_emri_no FROM projeler")] == [no]
    for x in satirlar:
        pdf = Path(x["pdf_yolu"])
        assert pdf.is_file() and pdf.parent == W.KANAL / "projects" / no / f"r{x['rev']:02d}"
        assert pdf.name == f"Portman_{no}_r{x['rev']:02d}.pdf"
        assert x["is_emri"]["is_emri_no"] == no and x["is_emri"]["kunye"]["proje_kodu"] == no
    assert sorted(_dugmeler(depo, r3["mesaj_id"])) == sorted([f"o:{no}:3", f"r:{no}:3"])
    assert depo.revizyon(NUMARA_A, no)["rev"] == 3 and depo.revizyon(NUMARA_A, no, 2)["rev"] == 2


def test_dolu_klasorde_yeni_numara_is_donmez(depo, wa, hizli_motor):
    no = _r01(depo, wa)
    artik = W.KANAL / "projects" / no / "r02"            # kaydı yazılamamış yarım işin klasörü
    artik.mkdir(parents=True)
    (artik / "eski.pdf").write_bytes(b"%PDF-1.4\n% yarim is\n")
    r2 = _pencere(depo, wa, "120x180")
    assert r2["eylem"] == "is_emri", r2
    satirlar = sorgu(depo, "SELECT rev, is_emri_no, proje_id, pdf_yolu FROM revizyonlar ORDER BY rev")
    assert [x["rev"] for x in satirlar] == [1, 2] and satirlar[1]["is_emri_no"] != no
    assert len({x["proje_id"] for x in satirlar}) == 1                     # aynı proje: revizyon sayısı sürer
    yeni = satirlar[1]["is_emri_no"]
    assert Path(satirlar[1]["pdf_yolu"]).parent == W.KANAL / "projects" / yeni / "r02"
    assert [p.name for p in artik.iterdir()] == ["eski.pdf"]               # yarım işin klasörüne dokunulmadı: üzerine yazılmaz
    time.sleep(1.1)
    r3 = _pencere(depo, wa, "120x160")                                     # sonraki revizyon son planın numarasını taşır
    assert r3["eylem"] == "is_emri", r3
    assert [(x["rev"], x["is_emri_no"]) for x in sorgu(depo, "SELECT rev, is_emri_no FROM revizyonlar ORDER BY rev")] == \
        [(1, no), (2, yeni), (3, yeni)]
