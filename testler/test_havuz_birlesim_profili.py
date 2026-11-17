"""BK-37 · Havuz hakeminde birleşim profili kalemi (`araclar/birlesim_hakemi.py`, kart `testler/havuz/profil_kartlari.json`).

Dayanak: Lokman, 15 Kasım 2026 07:59:14 UTC; kapsam CIO'nun okuması (varsayım). Kart paftanın H profil montaj planından okunur
(`araclar/profil_karti.py`); pafta depoya girmez, CI kartı okur.

- Her kayıtta paftayla kaydın birleşim farkı kartta yazılı farkların aynısı: yeni fark ya da kaybolan fark testi kırar. Farkın durumu
  Lokman'ın ev kartından, sözü ve saatiyle (15 Kasım 2026): 140 m² ve 84 m² kabul (kayıt doğru, 08:51:58, 08:54:31); 71 m² ve
  45 m² kayıt hatası (pafta doğru, 08:53:28, 08:53:55). Kayıt düzelince kayıt hatası satırı kart dosyasından silinir: 71 m²'nin ve
  45 m²'nin kaydı Lokman'ın 09:42:35 kartıyla ("Evet, paftadaki gibi") paftaya döndü (İE-40 PR-8, D-87 › Ek), iki satır silindi.
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
LISTESIZ: tuple = ()       # BK-45: iki cumba (PA27–29) ve mahyası y boyunca kırma (PA06K) artık yazılır; liste yazılmayan kayıt yok


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
            assert f["durum"] in ("bekleyen", "kabul", "kayit_hatasi"), (kod, f)
            if f["durum"] != "bekleyen":                      # kabul ve kayıt hatası yalnız Lokman'ın sözüyle ve saatiyle
                assert re.search(r"Lokman .*\d{2}:\d{2}:\d{2} UTC", f.get("soz", "")), (kod, f)
                assert f.get("sonuc"), (kod, f)
    assert {k: sorted({f["durum"] for f in fs}) for k, fs in K["farklar"].items()} == {"PA-08": ["kabul"], "PA-19": ["kabul"]}


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


# 71 m²'nin kayıt hatası satırı (kart dosyasından 15 Kasım 2026'da silindi; kayıt paftaya döndü): komutun KAYIT HATASI yolu kaydın eski
# hâliyle denenir (sağ dış duvarın dayanağı ve karkaslı pano yok)
FARK_71 = {"tur": "pafta_uclu_kayit_degil", "xy": [782.0, 688.2], "yazi": "[782; 688,2] paftada 3'lü H, kayıtta çektirme U'su",
           "durum": "kayit_hatasi", "soz": "Lokman 15 Kasım 2026 08:53:28 UTC", "sonuc": "pafta doğru"}


def test_hakem_komutu_kartlari_ayirir(capsys, monkeypatch, tmp_path):
    assert BH.main(["PA-26"]) == 0                            # 71 m²: kayıt paftaya döndü (Lokman 09:42:35 kartı)
    assert BH.main(["PA-27"]) == 0                            # 45 m²: aynı kart
    assert capsys.readouterr().out.count("GEÇTİ: birleşimler paftayla aynı") == 2
    ie = json.loads(BH.is_emri_yolu("PA-26").read_text(encoding="utf-8"))
    dz = ie["yapi"]["dizilim"]
    dz["dis_pano_dayanagi"] = dz["dis_pano_dayanagi"][:-1]
    dz.pop("karkasli_panolar")
    eski = tmp_path / "PA26_eski.json"
    eski.write_text(json.dumps(ie, ensure_ascii=False), encoding="utf-8")
    K2 = json.loads(json.dumps(K))
    K2["farklar"]["PA-26"] = [FARK_71]
    monkeypatch.setattr(BH, "kartlar", lambda: K2)
    assert BH.main(["PA-26", "--is-emri", str(eski)]) == 1    # eski kayıt: Lokman paftayı doğru buldu, kayıt düzeltilene kadar kalır
    cikti = capsys.readouterr().out
    assert "KAYIT HATASI" in cikti and "paftada 3'lü H, kayıtta çektirme U'su" in cikti
    assert BH.main(["PA-19"]) == 0                            # 84 m²: Lokman kaydın 3'lü H'ını doğru buldu
    assert "2 fark Lokman'ın kartıyla kabul" in capsys.readouterr().out
    assert BH.main(["PA-02"]) == 0
