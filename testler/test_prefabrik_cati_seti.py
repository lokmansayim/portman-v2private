"""İE-37 (D-83) · Prefabrik evde çatı seçimi: Doğan evine (PA-06) üç çatı (PA-06, PA-06-K, PA-06-C). LLM'siz, Postgres'siz.

Lokman 12 Kasım 2026 08:36:09 ("olabilirse başka seçeneklerde sunulsun … salonun üzerine kampanyalı binada olduğu gibi cumba
koyabilirsin") ve 08:41:09 ("burada 1, 2 ve 5 sunulsun"). Plan seçilince "Çatı seçin" seti gelir (İE-25'in çelik adımı gibi); seçenekler
ayrı aday kaydıdır, görünmesi K-A10 kabulüne bağlıdır. Kabulsüz yol (harness) ve seçeneği kabul edilmemiş ev bugünkü gibi doğrudan çizilir.
"""
from __future__ import annotations
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from beyin import karar as K  # noqa: E402
from beyin.katalog import ADAYLAR_PREFABRIK_JSON, CATI_VARYANT_DIR, SABLON_DIR, Katalog  # noqa: E402
from test_celik_revizyon_karar import Sohbet  # noqa: E402

PA = {f"PA0{i}" for i in range(1, 9)}
CATILAR = {"PA06K", "PA06C"}
KAYIT = json.loads((CATI_VARYANT_DIR / "PA06.json").read_text(encoding="utf-8"))
EV = next(a for a in json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8")) if a["kod"] == "PA06")
CATI = {   # D-83 tablosu "Çatılar": kararla yazılan iki çatı (eğim, saçak, topuk evin çatısından)
    "PA06K": {"tip": "kirma", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "kisa_kenar", "makas_ekseni": "x"},
    "PA06C": {"tip": "besik_cumba", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "uzun_kenar", "makas_ekseni": "y",
              "cumbalar": [{"cephe": "on", "bas_cm": 444.25, "bit_cm": 800, "cikinti_cm": 0, "ana_makas": "cumba_makasindan"}]},
}


def _cati_seti(tmp_path: Path, kabul=PA | CATILAR, m2: float = 85):
    """85 m² 2+1 → öncelik "fark etmez" → alan seti → PA-06 düğmesi."""
    s = Sohbet(tmp_path, kabul=set(kabul))
    k = s.yaz(f"{m2:g} m2 2+1 prefabrik ev", alan_m2=m2, oda_programi="2+1", yapi_turu="prefabrik")
    if k.eylem == "sor" and "öne çıksın" in (k.mesaj or ""):
        k = s.yaz("fark etmez", niyet="yeni_talep")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "alan", k.mesaj
    return s, s.dugme("s:{set}:PA06")


# ── kayıt ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_kayit_bicimi():
    assert (KAYIT["taban"], KAYIT["cati_adi"], KAYIT["cati_gorsel"], KAYIT["karar"]) == ("PA06", "Beşik, kalkan önde", "adaylar/PA06_cati.png", "D-83")
    assert [(v["kod"], v["gosterim"], v["cati_adi"]) for v in KAYIT["varyantlar"]] == [
        ("PA06K", "PA-06-K", "Kırma"), ("PA06C", "PA-06-C", "Beşik + salonda cumba")]
    for v in KAYIT["varyantlar"]:
        assert (v["durum"], v["taban"], v["referans_model"], v["kaynak"]["karar"]) == ("gecerli", "PA06", v["gosterim"], "D-83")
        for a in ("yapi_turu", "kat", "oda_programi", "katalog_m2", "kapali_m2", "veranda_m2", "ozet"):
            assert v[a] == EV[a], (v["kod"], a)                      # plan aynı: alanlar evin kaydından
        assert (SABLON_DIR / v["gorsel"]).stat().st_size > 10_000
    assert (SABLON_DIR / KAYIT["cati_gorsel"]).stat().st_size > 10_000
    karar = (KOK / "KARARLAR/D-83.md").read_text(encoding="utf-8")
    assert "burada 1, 2 ve 5 sunulsun" in karar and "PA-06-K" in karar and "PA-06-C" in karar


def test_sablon_evin_sablonu_yalniz_cati_degisir():
    """Şablon evin şablonudur; yalnız kimlik, referans kodu ve `cati` değişir (D-28: elle düzeltme yok); çatı kararın yazdığı."""
    ev = json.loads((SABLON_DIR / EV["sablon"]).read_text(encoding="utf-8"))
    for v in KAYIT["varyantlar"]:
        sab = json.loads((SABLON_DIR / v["sablon"]).read_text(encoding="utf-8"))
        assert sab["is_emri_no"] == f"PM-ADAY-{v['kod']}" and sab["yapi"]["referans_model"] == v["gosterim"]
        assert sab["cati"] == CATI[v["kod"]], v["kod"]
        a, b = copy.deepcopy(ev), copy.deepcopy(sab)
        for d in (a, b):
            d.pop("is_emri_no"); d.pop("cati"); d["yapi"].pop("referans_model")
        assert a == b, v["kod"]


def test_plan_ayni_motor_gecer():
    """Üç çatıda plan aynı (brüt alan, pano, mahaller); çatı Motor'un denetiminden geçer (K23 `uret` ayrıca, gorsel testinde)."""
    from motor import geometry as G, prefabrik_liste as PL
    ev = json.loads((SABLON_DIR / EV["sablon"]).read_text(encoding="utf-8"))
    p0 = G.kur(ev)
    for v in KAYIT["varyantlar"]:
        p = G.kur(json.loads((SABLON_DIR / v["sablon"]).read_text(encoding="utf-8")))
        assert PL.bina_brut_cm2(p) == PL.bina_brut_cm2(p0) and len(p.panolar) == len(p0.panolar)
        assert {a: m.alan_m2 for a, m in p.mahaller.items()} == {a: m.alan_m2 for a, m in p0.mahaller.items()}


@pytest.mark.parametrize("kod", ["PA06", "PA06K", "PA06C"])
def test_cati_gorseli_koddan_bayt_bayt(tmp_path, kod):
    """Çatı görseli Motor'un ön onay PDF'inden (ön ve sol görünüş) bayt bayt yeniden üretilir (`araclar/cati_varyanti_kaydet.ciz`)."""
    sys.path.insert(0, str(KOK / "araclar"))
    import cati_varyanti_kaydet as CV
    sablon = EV["sablon"] if kod == "PA06" else f"adaylar/{kod}.json"
    hedef = KAYIT["cati_gorsel"] if kod == "PA06" else f"adaylar/{kod}.png"
    oz = CV.ciz(json.loads((SABLON_DIR / sablon).read_text(encoding="utf-8")), tmp_path / "c.png")
    assert (tmp_path / "c.png").read_bytes() == (SABLON_DIR / hedef).read_bytes(), kod
    assert oz["brut_cm2"] == 870400 and oz["pano"] == 54


def test_arac_karar_ister(tmp_path):
    arac = [sys.executable, str(KOK / "araclar/cati_varyanti_kaydet.py"), "--taban", "PA-06", "--cati-adi", "x", "--varyant", "Z", "x", "{}"]
    for karar in ("D-999", "yok", "D-80", "D-83"):          # D-83 PA-06-Z'yi yazmaz; D-80 hiçbirini
        r = subprocess.run(arac + ["--karar", karar], capture_output=True, text=True, cwd=tmp_path)
        assert r.returncode == 2 and "Lokman'ın kararıyla" in r.stdout, r.stdout + r.stderr
    assert not (SABLON_DIR / "adaylar/PA06Z.json").exists()


# ── katalog ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_kabulsuz_yolda_gorunmez():
    """Harness `Katalog()`'u kabul kümesiz kurar: çatı seçeneği de görünmez (22 vaka aynen)."""
    for kat in (Katalog(), Katalog(test_adaylari=True), Katalog(kabul_edilmis={"PA06"})):
        assert not {a["kod"] for a in kat.gorunur_adaylar()} & CATILAR
        assert kat.aday("PA-06-K") is None
    tum = Katalog(kabul_edilmis=PA | CATILAR)
    assert tum.aday("pa-06-c")["kod"] == "PA06C" and tum.aday("PA06")["varyantlar"] == ["PA06K", "PA06C"]
    assert tum.aday("PA06")["cati_gorsel"] == "adaylar/PA06_cati.png"
    assert json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8")) == json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8"))
    assert "varyantlar" not in EV                                     # evin kaydı (referans girdi) değişmedi; bağ bellekte


@pytest.mark.parametrize("girdi,kod", [("PA-06-K", "PA06K"), ("pa06c", "PA06C"), ("PA 06 K", "PA06K"), ("PA-06", "PA06")])
def test_kod_normalize(girdi, kod):
    assert Katalog.kod_normalize(girdi) == kod and Katalog.taban_kod(girdi) == "PA06"


def test_alan_setinde_her_plan_bir_kez(tmp_path):
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("85 m2 2+1 prefabrik ev", alan_m2=85, oda_programi="2+1", yapi_turu="prefabrik")
    k = s.yaz("fark etmez", niyet="yeni_talep")
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA06", "PA05", "PA04"], k.mesaj


# ── karar: çatı seti ve seçim ─────────────────────────────────────────────────────────────────────────────────────────
def test_plan_secilince_cati_seti(tmp_path):
    s, k = _cati_seti(tmp_path)
    st = s.k.d["secenek_seti"]
    assert k.eylem == "secenek" and st["tur"] == "cati_varyanti", k.mesaj
    assert [a["kod"] for a in st["adaylar"]] == ["PA06", "PA06K", "PA06C"]
    assert [a["gorsel"] for a in st["adaylar"]] == ["adaylar/PA06_cati.png", "adaylar/PA06K.png", "adaylar/PA06C.png"]
    assert [b["baslik"] for b in k.butonlar] == ["1. PA-06", "2. PA-06-K", "3. PA-06-C"]
    assert "1. PA-06 · evin çatısı (Beşik, kalkan önde)" in k.mesaj and "3. PA-06-C · çatı C (Beşik + salonda cumba)" in k.mesaj
    assert 'örn. "PA-06-K olsun"' in k.mesaj and "öne çıksın" not in k.mesaj
    eski = next(e for e in s.k.d["eski_setler"] if e["tur"] == "alan")
    assert (eski["durum"], eski["secilen_kod"]) == ("secildi", "PA06")


@pytest.mark.parametrize("kod", ["PA06", "PA06K", "PA06C"])
def test_dugmeyle_cati_secimi_r01(tmp_path, kod):
    s, _ = _cati_seti(tmp_path)
    k = s.dugme(f"s:{{set}}:{kod}")
    assert k.eylem == "is_emri", k.mesaj
    ie = k.is_emri
    sab = json.loads((SABLON_DIR / ("adaylar/PA06.json" if kod == "PA06" else f"adaylar/{kod}.json")).read_text(encoding="utf-8"))
    assert (ie["talep"]["kaynak"], ie["revizyon"], ie["cati"], ie["mahaller"]) == (kod, 1, sab["cati"], sab["mahaller"])
    assert (s.k.d["secenek_seti"]["durum"], s.k.d["secenek_seti"]["secilen_kod"]) == ("secildi", kod)


@pytest.mark.parametrize("metin,kod", [("2", "PA06K"), ("3", "PA06C"), ("1", "PA06")])
def test_numarayla_cati_secimi(tmp_path, metin, kod):
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="yeni_talep")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == kod, k.mesaj


def test_yaziyla_cati_kodu(tmp_path):
    """Bayi "PA-06-K olsun" yazar: kod LLM'siz tanınır (`_sozcukler`); LLM'in okuduğu kodla da seçilir."""
    s, _ = _cati_seti(tmp_path)
    assert K._secim_kodlari("PA-06-K olsun", s.kat) == ["PA06K"]
    k = s.yaz("PA-06-K olsun", katalog_kodu="PA-06-K")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06K", k.mesaj


def test_kodla_ev_secilince_cati_seti(tmp_path):
    """Set açılmadan "PA-06 olsun": yine çatı seti (plan seçildi, çatı yazılmadı)."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06 olsun", katalog_kodu="PA-06", yapi_turu="prefabrik")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti", k.mesaj
    k = s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06C", k.mesaj


def test_cati_koduyla_ilk_mesaj_seti_atlar(tmp_path):
    """Bayi çatıyı ilk mesajda yazdıysa ("PA-06-K olsun") set gelmez, r01 o çatıyla; çatısı tek olan ev (PA-05) bugünkü gibi r01."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06-K olsun", katalog_kodu="PA-06-K", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06K" and k.is_emri["cati"]["tip"] == "kirma", k.mesaj
    s = Sohbet(tmp_path / "b", kabul=PA | CATILAR)
    k = s.yaz("PA-05 olsun", katalog_kodu="PA-05", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA05", k.mesaj


def test_revizyonda_cati_seti_yeniden_gelmez(tmp_path):
    """Evin kendi çatısıyla çizilmiş planın revizyonu çatıyı yeniden sormaz; plan aynı çatıyla r02 olur."""
    s, _ = _cati_seti(tmp_path)
    k = s.dugme("s:{set}:PA06")
    assert k.eylem == "is_emri" and k.revizyon == 1
    k = s.yaz("PA-06 olsun", katalog_kodu="PA-06", niyet="revizyon")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj


def test_revizyonda_cati_degisir(tmp_path):
    """r01 evin çatısıyla; bayi sonra "PA-06-C olsun" yazar (LLM revizyon okur) → aynı plan, cumbalı çatıyla r02. LLM yeni talep
    okursa bugünkü kural geçer (gönderilmiş plandan sonra yeni talep konuşmayı kapatır): cumbalı çatıyla yeni r01, çatı yeniden sorulmaz."""
    s, _ = _cati_seti(tmp_path)
    r01 = s.dugme("s:{set}:PA06").is_emri
    k = s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["cati"]["tip"] == "besik_cumba", k.mesaj
    assert k.is_emri["talep"]["kaynak"] == "PA06C" and (k.is_emri["mahaller"], k.is_emri["acikliklar"]) == (r01["mahaller"], r01["acikliklar"])
    s, _ = _cati_seti(tmp_path / "b")
    s.dugme("s:{set}:PA06")
    k = s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C", niyet="yeni_talep")
    assert k.eylem == "is_emri" and k.revizyon == 1 and k.is_emri["talep"]["kaynak"] == "PA06C", k.mesaj


def test_kismi_kabul(tmp_path):
    """Yalnız kırma kabul edildiyse set iki çatı; hiçbiri kabul edilmediyse plan evin çatısıyla doğrudan (bugünkü yol)."""
    s, k = _cati_seti(tmp_path, kabul=PA | {"PA06K"})
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA06", "PA06K"], k.mesaj
    s, k = _cati_seti(tmp_path / "b", kabul=PA)
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06" and k.is_emri["cati"]["tip"] == "besik", k.mesaj


def test_cati_seti_acikken_olcu_degisirse_set_eskir(tmp_path):
    """İE-25 kuralı prefabrikte de: çatı seti açıkken yeni m² sessizce düşmez; set eskir, talep yeniden okunur."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("80 m2 olsun", alan_m2=80, niyet="yeni_talep")
    eski = next(e for e in s.k.d["eski_setler"] if e["tur"] == "cati_varyanti")
    assert eski["durum"] == "eskidi"
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "alan", k.mesaj
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA04", "PA05", "PA06"]


def test_kart_altyazisi():
    from motor import bayi_gorseli as BG
    a = {**KAYIT["varyantlar"][1], "sunum": {"cati_adi": "Beşik + salonda cumba"}}
    assert BG.kart_altyazisi({**a, "cati_karti": True}) == ["Çatı: Beşik + salonda cumba", "87 m² katalog · kapalı 72,6 m²"]
    assert BG.kart_altyazisi(a) == ["Beşik + salonda cumba · 87 m² katalog · kapa"]     # işaretsiz: bugünkü tek satır (değişmez)
