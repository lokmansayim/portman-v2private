"""İE-39 · Havuz evinde bayinin "sağa yarım pano uzat / kısalt" komutu (`beyin/yarim_pano.py`). LLM'siz, Postgres'siz.

Kural D-90 (Lokman, 14 Kasım 2026 09:29:42 UTC, kart "Doğru, işe başlansın"): dış duvar yarım pano kayar, o duvara değen odalar uzar;
veranda ya da çatı açıklığı değişen evde komut durur. İlk dilim (kart 09:53:57 UTC): sağ ve ön duvar.

Hedef örnek `testler/yarim_pano/PA12_sag_arti1.json` (85 m² 3+1, sağa 1 yarım pano): Lokman 14 Kasım 2026 10:11:06 UTC kartı
"Doğru, örnek olsun" (`onay` alanı; D-28). Yalnız Lokman'ın onayıyla ve gerekçeli kararla yeniden dondurulur (D-02). Ev × duvar × komut tablosu `testler/yarim_pano/beklenen_tablo.json`. İkisi bilinçli yazılır:
`python testler/test_yarim_pano.py --dondur` (gerekçe iş emrine).
"""
from __future__ import annotations

import copy
import glob
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from beyin import yarim_pano as Y  # noqa: E402

VERI = KOK / "testler" / "yarim_pano"
TABLO = VERI / "beklenen_tablo.json"
PA12_HEDEF = VERI / "PA12_sag_arti1.json"
EVLER = sorted(Path(f).stem for f in glob.glob(str(KOK / "is_emri" / "adaylar" / "PA*.json")))
KOMUTLAR = [(c, a) for c in Y.DILIM for a in (1, -1)]


def _ie(kod: str) -> dict:
    return json.loads((KOK / "is_emri" / "adaylar" / f"{kod}.json").read_text(encoding="utf-8"))


def _sonuc(kod: str, cephe: str, adim: int) -> str:
    try:
        Y.uygula(_ie(kod), cephe, adim)
        return "temiz"
    except Y.KomutDurdu as e:
        return e.kod


def tablo_uret() -> dict:
    return {kod: {f"{c}{a:+d}": _sonuc(kod, c, a) for c, a in KOMUTLAR} for kod in EVLER}


def pa12_uret() -> dict:
    s = Y.uygula(_ie("PA12"), "sag", 1)
    return {"ozet": Y.ozet(s), "is_emri": s["is_emri"]}


# ---------------------------------------------------------------- tablo: hangi evde ne olur

def test_tablo_evleri_aynı():
    t = json.loads(TABLO.read_text(encoding="utf-8"))["tablo"]
    assert sorted(t) == EVLER, "is_emri/adaylar'a yeni ev girdi ya da çıktı: tabloyu bilinçli yeniden yazın"


@pytest.mark.parametrize("kod", EVLER)
def test_tablo(kod):
    t = json.loads(TABLO.read_text(encoding="utf-8"))["tablo"]
    assert {f"{c}{a:+d}": _sonuc(kod, c, a) for c, a in KOMUTLAR} == t[kod]


def test_tablo_temiz_evler():
    """Bugün temiz çizilen: 85 m² (PA-12) ve 77 m² (PA-24) sağ uzat ve kısalt, 49 m² (PA-23) ön uzat ve kısalt (Lokman'a rapor,
    14 Kasım 09:53; 49 m² ön kısalt hakem bulgusundan sonra: kıyas önce kaydırır, sonra toleransla eşler)."""
    t = json.loads(TABLO.read_text(encoding="utf-8"))["tablo"]
    temiz = sorted((k, kom) for k, v in t.items() for kom, s in v.items() if s == "temiz")
    assert temiz == [("PA12", "sag+1"), ("PA12", "sag-1"), ("PA23", "on+1"), ("PA23", "on-1"), ("PA24", "sag+1"), ("PA24", "sag-1")]


# ---------------------------------------------------------------- kurallar

@pytest.mark.parametrize("cephe", ["sol", "arka"])
def test_dilim_disi_duvar_durur(cephe):
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uygula(_ie("PA12"), cephe, 1)
    assert e.value.kod == "dilim"


@pytest.mark.parametrize("kod", sorted(k.replace("-", "") for k in Y.MUHURLU_EVLER))
def test_muhurlu_ev_durur(kod):
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uygula(_ie(kod), "sag", 1)
    assert e.value.kod == "muhur"


def test_muhurlu_evler_kayitla_ayni():
    """Mühürlü evler havuz kaydının metninde mühürle anılan evlerdir (M-07: dört ev, M-12: AP-26). M-16 liste mühürüdür, plan değil."""
    kayitlar = json.loads((KOK / "beyin" / "veri" / "adaylar_prefabrik.json").read_text(encoding="utf-8"))
    kayitlar += [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(KOK / "beyin" / "veri" / "havuz" / "PA*.json")))]
    anilan = {r["gosterim"]: m for r in kayitlar for m in ("M-07", "M-12") if m in json.dumps(r, ensure_ascii=False)}
    assert anilan == Y.MUHURLU_EVLER


@pytest.mark.parametrize("adim", [0, 1.5])
def test_adim_tam_sayi(adim):
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uygula(_ie("PA12"), "sag", adim)
    assert e.value.kod == "adim"


def test_veranda_duvara_degerse_durur():
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uygula(_ie("PA12"), "on", 1)
    assert e.value.kod == "veranda" and "VERANDA" in e.value.neden


@pytest.mark.parametrize("ad", ["SUNDURMA", "ÖN ALAN"])
def test_sundurma_uzamaz(ad):
    """Motor'un açık mahali (veranda, balkon, sundurma, teras) kayan duvara değerse komut durur; adı ne olursa olsun (hakem bulgusu 1)."""
    ie = json.loads((KOK / "is_emri" / "adaylar" / "PA14.json").read_text(encoding="utf-8").replace('"VERANDA"', json.dumps(ad, ensure_ascii=False)))
    for m in ie["mahaller"]:
        if m.get("tur") == "veranda":
            m["tur"] = "sundurma"
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uygula(ie, "sag", 1)
    assert e.value.kod == "veranda" and ad in e.value.neden


def test_cati_acikligi_degisirse_durur():
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uygula(_ie("PA24"), "on", 1)
    assert e.value.kod == "cati" and "1000 → 1062,75" in e.value.neden


def test_girdi_degismez():
    ie = _ie("PA12")
    once = copy.deepcopy(ie)
    Y.uygula(ie, "sag", 1)
    assert ie == once


def test_uzat_sonra_kisalt_eski_plan():
    """Sağa 1 yarım pano uzat, sonra 1 yarım pano kısalt: İş Emri'nin geometrisi eskisinin aynısı (revizyon ve kayıt satırı dışında)."""
    ie0 = _ie("PA12")
    ie1 = Y.uygula(ie0, "sag", 1)["is_emri"]
    ie2 = Y.uygula(ie1, "sag", -1)["is_emri"]
    disla = ("revizyon", "varsayimlar")
    assert {k: v for k, v in ie2.items() if k not in disla} == {k: v for k, v in ie0.items() if k not in disla}


# ---------------------------------------------------------------- 85 m² ev, sağa 1 yarım pano

def test_pa12_sag_arti1_ozet():
    s = Y.uygula(_ie("PA12"), "sag", 1)
    assert s["dis_olcu"] == {"once": [1166.0, 726.0], "sonra": [1228.75, 726.0]}
    assert [(u["ad"], u["once_m2"], u["sonra_m2"]) for u in s["uzayan"]] == [("YATAK ODASI 2", 11.84, 14.59), ("YATAK ODASI 3", 13.53, 15.17)]
    assert s["sayilar"] == {"once": 54, "sonra": 54, "ayni": 42, "kaydi": 9, "degisti": 3}
    alan0 = {m.ad: round(m.alan_m2, 2) for m in s["once"].mahaller.values()}
    alan1 = {m.ad: round(m.alan_m2, 2) for m in s["sonra"].mahaller.values()}
    assert {k for k in alan1 if alan1[k] != alan0[k]} == {"YATAK ODASI 2", "YATAK ODASI 3"}
    assert s["is_emri"]["revizyon"] == 2 and s["is_emri"]["varsayimlar"][-1].startswith("Bayi komutu (İE-39): sağ dış duvar 1 yarım pano")


def test_pa12_sag_arti1_beklenen_ornek():
    h = json.loads(PA12_HEDEF.read_text(encoding="utf-8"))
    u = pa12_uret()
    assert u["is_emri"] == h["is_emri"]
    assert json.loads(json.dumps(u["ozet"], ensure_ascii=False)) == h["ozet"]


def test_pa12_hedef_onayli():
    h = json.loads(PA12_HEDEF.read_text(encoding="utf-8"))
    assert h["onay"]["kim"] == "Lokman" and "Doğru, örnek olsun" in h["onay"]["soz"]


def test_pa12_sag_arti1_cizim(tmp_path):
    """Ön onay çizimi doğrulamadan geçer (K23); önce/sonra pano dizilimi ve bayi plan görseli yazılır."""
    oz = Y.uret(_ie("PA12"), "sag", 1, tmp_path)
    for ad in oz["dosyalar"].values():
        assert (tmp_path / ad).is_file(), ad
    v = json.loads((tmp_path / "cizim" / "validation.json").read_text(encoding="utf-8"))
    assert v["passed"] is True


def test_kisaltmada_kalkan_panolar_once_planinda():
    """Kısaltmada silinen panolar önceki planda 'degisti' (görselde pembe; çalışma kuralı 12, hakem bulgusu 3)."""
    s = Y.uygula(_ie("PA12"), "sag", -1)
    assert s["sayilar"] == {"once": 54, "sonra": 51, "ayni": 42, "kaydi": 9}
    from collections import Counter
    assert Counter(s["siniflar_once"].values()) == {"ayni": 42, "kaydi": 9, "degisti": 3}


def test_dogrulama_gecmezse_dosya_yazilmaz(tmp_path, monkeypatch):
    """K23: çizim doğrulaması geçmezse hedef klasöre hiçbir dosya yazılmaz (hakem bulgusu 4)."""
    from motor import dxf_out
    monkeypatch.setattr(dxf_out, "uret", lambda ie, d, ad_govde=None: {"validation_passed": False})
    with pytest.raises(Y.KomutDurdu) as e:
        Y.uret(_ie("PA12"), "sag", 1, tmp_path / "cikti")
    assert e.value.kod == "cizim"
    assert not any((tmp_path / "cikti").rglob("*"))


def test_on_duvar_kisalt_pa23():
    """Ön kısalt: Motor 62,5 cm kısaltır (D-30); kıyas önce kaydırır, sonra eşler, kapılar yerinde (hakem bulgusu 2)."""
    s = Y.uygula(_ie("PA23"), "on", -1)
    assert s["d_motor"] == -62.5 and s["notlar"]
    assert s["sayilar"] == {"once": 40, "sonra": 38, "ayni": 32, "kaydi": 6}


def test_on_duvar_pa23():
    """Ön duvar (gerçek çerçevede ön y = 0): yerinde kalan panolar 'aynı', ön duvar 'kaydı'; Motor son panoyu tamamlar (D-30)."""
    s = Y.uygula(_ie("PA23"), "on", 1)
    assert s["d_motor"] == 63.0 and s["notlar"]
    assert s["sayilar"] == {"once": 40, "sonra": 40, "ayni": 32, "kaydi": 6, "degisti": 2}
    assert [u["ad"] for u in s["uzayan"]] == ["SALON & MUTFAK"]


if __name__ == "__main__" and "--dondur" in sys.argv:
    VERI.mkdir(parents=True, exist_ok=True)
    TABLO.write_text(json.dumps({"aciklama": "İE-39: is_emri/adaylar/PA*.json × sağ ve ön × 1 yarım pano uzat (+1) ve kısalt (-1); "
                                 "'temiz' ya da durma kodu (beyin/yarim_pano.KomutDurdu.kod).", "tablo": tablo_uret()},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    eski = json.loads(PA12_HEDEF.read_text(encoding="utf-8")) if PA12_HEDEF.is_file() else {}
    PA12_HEDEF.write_text(json.dumps({"aciklama": "İE-39: 85 m² 3+1 (PA-12, is_emri/adaylar/PA12.json) sağ dış duvar 1 yarım pano uzat.",
                                      "onay": eski.get("onay"), "girdi": "is_emri/adaylar/PA12.json", "komut": {"cephe": "sag", "adim": 1},
                                      **pa12_uret()}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("yazıldı:", TABLO.relative_to(KOK), PA12_HEDEF.relative_to(KOK))
