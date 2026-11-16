"""D-111 (İE-43 PR-4b) · 92 m² (PA-43, disk arşivi HD-143) iki veranda çatısıyla: evin kendi çatısı verandada panel çatı (paftadaki gibi),
ikinci çatı PA-43-B verandada beşik çatı (Lokman, 16 Kasım 2026 08:08:55 UTC: "… 2 veranda çatı modeli üretime uygun sorun yok 92 m² nin
ikisinide al"). Kayıt `araclar/cati_varyanti_kaydet.py` (havuz tabanı ve `veranda_catilari`); seçenek planı, ana çatıyı ve panoları
değiştirmez; bayi planı onaylayınca çatı seti gelir (D-94, M-08 akışı; kilitleri değişmez)."""
from __future__ import annotations
import copy, json, sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from beyin.katalog import Katalog, CATI_VARYANT_DIR, SABLON_DIR, HAVUZ_DIR   # noqa: E402

KAYIT = json.loads((CATI_VARYANT_DIR / "PA43.json").read_text(encoding="utf-8"))
EV = json.loads((HAVUZ_DIR / "PA43.json").read_text(encoding="utf-8"))
DHDD = (KOK / "KARARLAR" / "D-111.md").read_text(encoding="utf-8")


def _ie(kod: str) -> dict:
    return json.loads((SABLON_DIR / f"adaylar/{kod}.json").read_text(encoding="utf-8"))


def test_kayit():
    assert (KAYIT["taban"], KAYIT["cati_adi"], KAYIT["cati_gorsel"], KAYIT["karar"]) == (
        "PA43", "Beşik; verandada panel çatı", "adaylar/PA43_cati.png", "D-111")
    (v,) = KAYIT["varyantlar"]
    assert (v["kod"], v["gosterim"], v["durum"], v["taban"], v["cati_adi"], v["referans_model"], v["sablon"], v["gorsel"]) == (
        "PA43B", "PA-43-B", "gecerli", "PA43", "Beşik; verandada beşik çatı", "PA-43-B", "adaylar/PA43B.json", "adaylar/PA43B.png")
    assert v["kaynak"]["karar"] == "D-111" and "08:08:55" in v["kaynak"]["metin"] and v["uyarilar"] == []
    assert all(v[k] == EV[k] for k in ("oda_programi", "katalog_m2", "kapali_m2", "veranda_m2", "ozet"))
    assert "PA-43-B" in DHDD and "92 m² nin ikisinide al" in DHDD


def test_yalniz_verandanin_catisi_farkli():
    """Şablonlar yalnız verandanın çatısında (ve seçeneğin kimliğinde) ayrılır: evinki panel, seçeneğinki beşik."""
    ev, b = _ie("PA43"), _ie("PA43B")
    assert ev["verandalar"][0]["cati"] == {"tip": "teras_paneli", "cikma_cm": 201, "egim_yuzde": 10}
    assert b["verandalar"][0]["cati"] == {"tip": "besik"}
    assert (b["is_emri_no"], b["yapi"]["referans_model"]) == ("PM-ADAY-PA43B", "PA-43-B")
    ayni = copy.deepcopy(b)
    ayni["verandalar"][0]["cati"] = ev["verandalar"][0]["cati"]
    ayni["is_emri_no"], ayni["yapi"]["referans_model"] = ev["is_emri_no"], ev["yapi"]["referans_model"]
    assert ayni == ev and ev["cati"]["tip"] == "besik"


def test_plan_ayni_motor_gecer():
    from motor import geometry as G, prefabrik_liste as PL
    p0, p = G.kur(_ie("PA43")), G.kur(_ie("PA43B"))
    assert PL.bina_brut_cm2(p) == PL.bina_brut_cm2(p0) and len(p.panolar) == len(p0.panolar) == 58
    assert {a: m.alan_m2 for a, m in p.mahaller.items()} == {a: m.alan_m2 for a, m in p0.mahaller.items()}
    assert [v["cati"]["tip"] for v in p0.dis_verandalar] == ["teras_paneli"]
    assert [v["cati"]["tip"] for v in p.dis_verandalar] == ["besik"]
    assert not any("çatısı İş Emri'nde yok" in u for u in p0.uyarilar + p.uyarilar)   # iki çatı da yazılı, varsayım yok


@pytest.mark.parametrize("kod,hedef", [("PA43", "adaylar/PA43_cati.png"), ("PA43B", "adaylar/PA43B.png")])
def test_cati_gorseli_koddan_bayt_bayt(tmp_path, kod, hedef):
    sys.path.insert(0, str(KOK / "araclar"))
    import cati_varyanti_kaydet as CV
    oz = CV.ciz(_ie(kod), tmp_path / "c.png")
    assert (tmp_path / "c.png").read_bytes() == (SABLON_DIR / hedef).read_bytes(), kod
    assert oz["pano"] == 58


def test_katalog_ve_onaydan_sonra_cati_seti():
    from beyin import karar
    assert Katalog().aday("PA43") is None and Katalog().aday("PA43B") is None          # K-A10: kabulsüz görünmez
    kat = Katalog(kabul_edilmis={"PA43", "PA43B"})
    assert kat.aday("PA-43-B")["kod"] == "PA43B" and kat.aday("PA43")["varyantlar"] == ["PA43B"]
    assert kat.aday("PA43")["cati_adi"] == "Beşik; verandada panel çatı" and Katalog.taban_kod("PA43B") == "PA43"
    taban, uygun = karar._plan_cati_secenekleri(kat, {"yapi": {}, "talep": {"kaynak": "PA43"}})
    assert taban["kod"] == "PA43" and [a["kod"] for a in uygun] == ["PA43", "PA43B"]
    assert karar._plan_cati_secenekleri(kat, {"yapi": {}, "talep": {"kaynak": "PA43B"}}) is None   # seçenekle çizilen planda set yok
    assert karar._plan_cati_secenekleri(Katalog(kabul_edilmis={"PA43"}), {"yapi": {}, "talep": {"kaynak": "PA43"}}) is None


def test_arac_cati_uygula():
    sys.path.insert(0, str(KOK / "araclar"))
    import cati_varyanti_kaydet as CV
    ie = _ie("PA43")
    a = copy.deepcopy(ie); CV.cati_uygula(a, {"tip": "kirma"})                         # bugünkü yol: ana çatı
    assert a["cati"] == {"tip": "kirma"} and a["verandalar"] == ie["verandalar"]
    a = copy.deepcopy(ie); CV.cati_uygula(a, {"veranda_catilari": {"VERANDA": {"tip": "besik"}}})
    assert a["cati"] == ie["cati"] and a["verandalar"][0]["cati"] == {"tip": "besik"}
    for yanlis in ({}, {"veranda_catilari": {"BALKON": {"tip": "besik"}}}, {"verandalar": []}, []):
        with pytest.raises(SystemExit):
            CV.cati_uygula(copy.deepcopy(ie), yanlis)
    assert CV.ev_kaydi("PA43")["gosterim"] == "PA-43" and CV.ev_kaydi("PA06")["gosterim"] == "PA-06" and CV.ev_kaydi("PA99") is None


def test_kayit_kapisindan_gecti():
    """D-112 (havuz denetimi kapısı): beş ev ve PA-43-B kapıdan geçerek yazıldı; hata yok, uyarılar kayıtta.
    37 ve 59 m² HD-06 (cumbanın yavru makası; 37 m²'de ana çatının düzensiz pano ekleri), PA-43-B HD-09 (veranda beşiğinde 3D makas)."""
    from beyin.katalog import havuz_kayitlari
    evler = {a["kod"]: a for a in havuz_kayitlari(yapi="prefabrik")}
    beklenen = {"PA39": ["HD-06"], "PA40": [], "PA41": ["HD-06"], "PA42": [], "PA43": []}
    for kod, kalemler in beklenen.items():
        d = evler[kod]["kaynak"]["havuz_denetimi"]
        assert (d["sonuc"], d["karar"]) == ("geçti", "D-112"), kod
        assert sorted({u.split(":")[0] for u in d["uyarilar"]}) == kalemler, kod
    d = KAYIT["varyantlar"][0]["kaynak"]["havuz_denetimi"]
    assert (d["sonuc"], d["karar"]) == ("geçti", "D-112") and [u.split(":")[0] for u in d["uyarilar"]] == ["HD-09"]
