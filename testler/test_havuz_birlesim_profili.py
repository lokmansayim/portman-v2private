"""BK-37 · Havuz hakeminde birleşim profili kalemi (`araclar/birlesim_hakemi.py`, kart `testler/havuz/profil_kartlari.json`).

Dayanak: Lokman, 15 Kasım 2026 07:59:14 UTC; kapsam CIO'nun okuması (varsayım). Kart paftanın H profil montaj planından okunur
(`araclar/profil_karti.py`); pafta depoya girmez, CI kartı okur.

- Her kayıtta paftayla kaydın birleşim farkı kartta yazılı farkların aynısı: yeni fark ya da kaybolan fark testi kırar. Bekleyen fark
  Lokman'ın ev kartını bekler (15 Kasım 2026: 140 m², 71 m², 45 m², 84 m²).
- Hakemin kaydı okuyuşu yükleme listesinin saydığıyla aynı (3'lü H'lı ek, düz ek, çektirme U'sunun üç yeri): hakem listenin mantığından
  sapmaz.
- Kartın paftası mühürdeki dosya (SHA-256), hizalama birleşimlerin en az %70'inde tutuyor (45 m² 1+1: 20/27; öteki 5 daire dış
  duvarın pano ekleri, birleşim değil).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from araclar import birlesim_hakemi as BH  # noqa: E402

K = BH.kartlar()
KIYASLI = sorted(k for k, v in K["evler"].items() if not v.get("okunamadi"))
KAYITLAR = sorted(p.stem for p in (KOK / "is_emri" / "adaylar").glob("PA[0-9][0-9]*.json"))
LISTESIZ = ("PA06K", "PA27", "PA28", "PA29")       # liste yazılmaz (iki cumba, mahyası y boyunca kırma); hakem yine okur


def test_kart_kaynagi_muhurde():
    muhur = (KOK / "docs" / "notlar" / "2026-10-18_AIPrefabrik_muhur.md").read_text(encoding="utf-8")
    assert len(K["evler"]) >= 20
    for kod, v in K["evler"].items():
        assert re.fullmatch(r"AP-\d\d", v["kart"]), kod
        assert v["pafta_sha256"] in muhur, f"{kod}: pafta mühürdeki dosya değil"
        if v.get("okunamadi"):
            continue
        hz = v["hiza"]
        assert hz["eslesen"] >= 0.70 * hz["daire"], f"{kod}: hizalama {hz['eslesen']}/{hz['daire']}"
        assert all(p["tur"] in ("h", "uclu_h", "dortlu_h") for p in v["h"])


def test_farklar_kayitli_ve_durumlu():
    for kod, fs in K["farklar"].items():
        assert kod in K["evler"]
        for f in fs:
            assert f["durum"] in ("bekleyen", "kabul"), (kod, f)
            if f["durum"] == "kabul":                         # kabul yalnız Lokman'ın ev kartıyla, sözü ve saatiyle
                assert re.search(r"\d{2}:\d{2}", f.get("soz", "")), (kod, f)
    assert sorted(K["farklar"]) == ["PA-08", "PA-19", "PA-26", "PA-27"]


@pytest.mark.parametrize("kod", KIYASLI)
def test_birlesimler_kartla(kod):
    ie = json.loads(BH.is_emri_yolu(kod).read_text(encoding="utf-8"))
    bul, _ = BH.denetle(kod, ie, K["evler"][kod])
    d = BH.durumlar(kod, bul, K["farklar"].get(kod, []))
    assert not d["yeni"], [b["yazi"] for b in d["yeni"]]
    assert not d["kalkan"], [f["yazi"] for f in d["kalkan"]]


@pytest.mark.parametrize("ad", [k for k in KAYITLAR if k not in LISTESIZ])
def test_kayit_okuyusu_listeyle_ayni(ad):
    from motor import prefabrik_liste as PL
    ie = json.loads((KOK / "is_emri" / "adaylar" / f"{ad}.json").read_text(encoding="utf-8"))
    N = PL.model_motor(ie)
    k = BH.kayit_birlesimleri(ie)["sayilar"]
    assert k["uclu_ek"] == sum(e["cins"] == "uclu" for e in N["ekler"])
    assert k["pano_eki"] == sum(e["cins"] == "pano_eki" for e in N["ekler"])
    assert {x: k["cektirme_yerleri"].get(x, 0) for x in ("t_orta", "dis_kose", "serbest")} == N["cektirme_yerleri"]


def test_hakem_komutu_bekleyeni_soyler(capsys):
    assert BH.main(["PA-19"]) == 1
    cikti = capsys.readouterr().out
    assert "BEKLİYOR" in cikti and "paftada düz H, kayıtta 3'lü H" in cikti
    assert BH.main(["PA-02"]) == 0
