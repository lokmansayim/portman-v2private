"""İE-37 (D-83) · Prefabrik evde çatı seçimi: PA-06 evine üç çatı (PA-06, PA-06-K, PA-06-C). LLM'siz, Postgres'siz.

Lokman 12 Kasım 2026 08:36:09 ("olabilirse başka seçeneklerde sunulsun … salonun üzerine kampanyalı binada olduğu gibi cumba
koyabilirsin") ve 08:41:09 ("burada 1, 2 ve 5 sunulsun"). Seçenekler ayrı aday kaydıdır, görünmesi K-A10 kabulüne bağlıdır. Kabulsüz
yol (harness) ve seçeneği kabul edilmemiş ev bugünkü gibi doğrudan çizilir.

İE-42 (D-94; Lokman 14 Kasım 2026 20:33:41 kartı "Onaydan sonra, eskizdeki gibi"): çatı plan seçilince değil, plan onaylanınca sorulur.
r01 evin kendi çatısıyla gelir; "Onayla" → "Planınız onaylandı (r01). Şimdi çatıyı seçin." seti; evin çatısı seçilirse r01 onaylanır, başka
çatı seçilirse aynı plan o çatıyla r02 → onay. Talepte çatı yazılıysa adım yok. Bu dosyanın İE-37 vakaları bu sıraya göre değişti
(`_cati_seti` artık r01 → onay → set; setten evin çatısı onaydır, başka çatı r02); gerekçe `docs/is_emirleri/IE-42.md` › Testler.
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
from test_celik_revizyon_karar import Sohbet, pen, var  # noqa: E402

PA = {f"PA0{i}" for i in range(1, 9)}
CATILAR = {"PA06K", "PA06C"}
KAYIT = json.loads((CATI_VARYANT_DIR / "PA06.json").read_text(encoding="utf-8"))
EV = next(a for a in json.loads(ADAYLAR_PREFABRIK_JSON.read_text(encoding="utf-8")) if a["kod"] == "PA06")
CATI = {   # D-83 tablosu "Çatılar": kararla yazılan iki çatı (eğim, saçak, topuk evin çatısından)
    "PA06K": {"tip": "kirma", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "kisa_kenar", "makas_ekseni": "x"},
    "PA06C": {"tip": "besik_cumba", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10, "makas_yonu": "uzun_kenar", "makas_ekseni": "y",
              "cumbalar": [{"cephe": "on", "bas_cm": 444.25, "bit_cm": 800, "cikinti_cm": 0, "ana_makas": "cumba_makasindan"}]},
}


def _plan(tmp_path: Path, kabul=PA | CATILAR, m2: float = 85):
    """85 m² 2+1 → öncelik "fark etmez" → alan seti → PA-06 düğmesi → r01 evin kendi çatısıyla (İE-42: çatı sorulmaz)."""
    s = Sohbet(tmp_path, kabul=set(kabul))
    k = s.yaz(f"{m2:g} m2 2+1 prefabrik ev", alan_m2=m2, oda_programi="2+1", yapi_turu="prefabrik")
    if k.eylem == "sor" and "öne çıksın" in (k.mesaj or ""):
        k = s.yaz("fark etmez", niyet="yeni_talep")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "alan", k.mesaj
    k = s.dugme("s:{set}:PA06")
    assert k.eylem == "is_emri" and k.revizyon == 1 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj
    return s, k


def _onayla(s: Sohbet):
    return s.dugme(f"o:{s.plan['is_emri_no']}:{s.plan['revizyon']}")


def _cati_seti(tmp_path: Path, kabul=PA | CATILAR, m2: float = 85):
    """r01 (evin çatısı) → Onayla → çatı seti (İE-42, D-94)."""
    s, _ = _plan(tmp_path, kabul, m2)
    return s, _onayla(s)


def _secildi(s: Sohbet, k, kod: str, rev: int = 2):
    """Onaydan sonraki setten seçim: evin çatısı (PA06) r01'i onaylar (yeni çizim yok); başka çatı aynı planı o çatıyla rNN çizer."""
    if kod == "PA06":
        assert (k.eylem, k.gerekce, s.k.d["asama"]) == ("cevapla", K.PLAN_ONAYI, "onaylandi"), k.mesaj
        assert (s.plan["revizyon"], s.plan["talep"]["kaynak"]) == (1, "PA06"), k.mesaj
    else:
        assert k.eylem == "is_emri" and k.revizyon == rev and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
        assert s.k.d["asama"] == "onay_bekliyor"


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
def test_plan_secilince_r01_onaydan_sonra_cati_seti(tmp_path):
    """İE-42: plan seçilince çatı sorulmaz, r01 evin kendi çatısıyla; "Onayla" çatı setini getirir (eskizin 3. adımı). Set mesajı
    bugünkü setin listesi ve görseliyle; yalnız ilk cümle yeni. Onay henüz kaydedilmez (kanalın onay kancaları "plan onaylandı" bekler)."""
    s, r01 = _plan(tmp_path)
    assert r01.mesaj == "PA-06 seçildi. Ön onay planınız hazır; plan görseli ve PDF ektedir.", r01.mesaj
    assert r01.is_emri["cati"]["tip"] == "besik" and s.k.d["secenek_seti"]["durum"] == "secildi"
    k = _onayla(s)
    st = s.k.d["secenek_seti"]
    assert k.eylem == "secenek" and st["tur"] == "cati_varyanti" and st["durum"] == "acik", k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and s.k.d["asama"] == "onay_bekliyor"
    assert [a["kod"] for a in st["adaylar"]] == ["PA06", "PA06K", "PA06C"]
    assert [a["gorsel"] for a in st["adaylar"]] == ["adaylar/PA06_cati.png", "adaylar/PA06K.png", "adaylar/PA06C.png"]
    assert [b["baslik"] for b in k.butonlar] == ["1. PA-06", "2. PA-06-K", "3. PA-06-C"]
    assert k.mesaj.startswith("Planınız onaylandı (r01). Şimdi çatıyı seçin. Bu eve 3 çatı uygulanır. Plan aynı kalır; yalnız çatı "
                              "değişir.\n\n1. PA-06 · evin çatısı (Beşik, kalkan önde)\n"), k.mesaj
    assert "3. PA-06-C · çatı C (Beşik + salonda cumba)" in k.mesaj and 'örn. "PA-06-K olsun"' in k.mesaj and "öne çıksın" not in k.mesaj
    eski = next(e for e in s.k.d["eski_setler"] if e["tur"] == "alan")
    assert (eski["durum"], eski["secilen_kod"]) == ("secildi", "PA06")


@pytest.mark.parametrize("kod", ["PA06", "PA06K", "PA06C"])
def test_dugmeyle_cati_secimi(tmp_path, kod):
    """Evin çatısı: r01 aynen onaylanır ("Çatı: … Plan r01 aynen kalır. Onayınız kaydedildi …"). Başka çatı: aynı plan o çatıyla r02
    ("Çatı: Kırma (PA-06-K). Plan aynı. …"); r02'nin onayı kaydedilir, çatı yeniden sorulmaz."""
    s, _ = _cati_seti(tmp_path)
    r01 = s.plan
    k = s.dugme(f"s:{{set}}:{kod}")
    _secildi(s, k, kod)
    sab = json.loads((SABLON_DIR / ("adaylar/PA06.json" if kod == "PA06" else f"adaylar/{kod}.json")).read_text(encoding="utf-8"))
    assert (s.k.d["eski_setler"][-1] if kod == "PA06" else s.k.d["secenek_seti"])["secilen_kod"] == kod
    if kod == "PA06":
        assert k.mesaj.startswith(f"Çatı: Beşik, kalkan önde (PA-06). Plan r01 aynen kalır. Onayınız kaydedildi ({r01['is_emri_no']}, "
                                  "revizyon 1)."), k.mesaj
        return
    ie = k.is_emri
    assert (ie["cati"], ie["mahaller"], ie["acikliklar"], ie["is_emri_no"]) == (sab["cati"], r01["mahaller"], r01["acikliklar"], r01["is_emri_no"])
    ad = {"PA06K": "Kırma", "PA06C": "Beşik + salonda cumba"}[kod]
    assert k.mesaj == (f"Çatı: {ad} ({kod[:2]}-{kod[2:4]}-{kod[4:]}). Plan aynı. Ön onay planınız hazır (r02); PDF'teki 4 görünüş "
                       f"{ad.lower()} çatıyı gösterir."), k.mesaj
    k = _onayla(s)
    assert (k.eylem, k.gerekce, s.k.d["asama"], s.plan["revizyon"]) == ("cevapla", K.PLAN_ONAYI, "onaylandi", 2), k.mesaj


@pytest.mark.parametrize("metin,kod", [("2", "PA06K"), ("3", "PA06C"), ("1", "PA06")])
@pytest.mark.parametrize("niyet", ["revizyon", "diger"])
def test_numarayla_cati_secimi(tmp_path, metin, kod, niyet):
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, niyet=niyet), kod)


def test_yaziyla_cati_kodu(tmp_path):
    """Bayi "PA-06-K olsun" yazar: kod LLM'siz tanınır (`_sozcukler`); LLM'in okuduğu kodla da seçilir."""
    s, _ = _cati_seti(tmp_path)
    assert K._secim_kodlari("PA-06-K olsun", s.kat) == ["PA06K"]
    _secildi(s, s.yaz("PA-06-K olsun", katalog_kodu="PA-06-K"), "PA06K")
    s, _ = _cati_seti(tmp_path / "b")
    _secildi(s, s.yaz("PA-06-K olsun"), "PA06K")


def test_kodla_ev_secilince_r01_evin_catisiyla(tmp_path):
    """Set açılmadan "PA-06 olsun": r01 evin çatısıyla (İE-42; önce çatı seti geliyordu). Onaydan önce "PA-06-C olsun" revizyondur: r02."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06 olsun", katalog_kodu="PA-06", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.revizyon == 1 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj
    k = s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06C", k.mesaj
    k = _onayla(s)                                        # çatıyı bayi yazdı: onayda çatı seti gelmez
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_ONAYI), k.mesaj


def test_cati_koduyla_ilk_mesaj_seti_atlar(tmp_path):
    """Bayi çatıyı ilk mesajda yazdıysa ("PA-06-K olsun") set gelmez, r01 o çatıyla ve onayda da çatı sorulmaz (D-94: talepte çatı varsa
    adım yok); çatısı tek olan ev (PA-05) bugünkü gibi r01 ve onay."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06-K olsun", katalog_kodu="PA-06-K", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06K" and k.is_emri["cati"]["tip"] == "kirma", k.mesaj
    k = _onayla(s)
    assert (k.eylem, k.gerekce, s.plan["revizyon"]) == ("cevapla", K.PLAN_ONAYI, 1), k.mesaj
    assert "Çatı:" not in k.mesaj
    s = Sohbet(tmp_path / "b", kabul=PA | CATILAR)
    k = s.yaz("PA-05 olsun", katalog_kodu="PA-05", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA05", k.mesaj
    k = _onayla(s)
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_ONAYI), k.mesaj


def test_revizyonda_cati_seti_yeniden_gelmez(tmp_path):
    """Evin kendi çatısıyla çizilmiş planın revizyonu çatıyı yeniden sormaz; plan aynı çatıyla kalır.
    D-86 (Lokman 13 Kasım 2026 21:36:32 kartı "Değişmedi desin"): yalnız kodu yineleyen yazı ("PA-06 olsun") planı değiştirmez; yeni
    revizyon numarası gitmez (önce aynı plan r02 diye yeniden çiziliyordu). Gerçek bir değişiklik r02 üretir: çatı seti yine gelmez,
    LLM'in yinelediği kodla da plan evin çatısında (PA06) kalır. İE-42: çatı seti r02'nin onayında gelir ("Planınız onaylandı (r02)")."""
    s, _ = _plan(tmp_path)
    k = s.yaz("PA-06 olsun", katalog_kodu="PA-06", niyet="revizyon")
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI), k.mesaj
    assert s.plan["revizyon"] == 1 and s.plan["talep"]["kaynak"] == "PA06"
    assert (s.k.d.get("secenek_seti") or {}).get("durum") != "acik"          # çatı seti yeniden açılmadı
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", katalog_kodu="PA-06", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj
    k = _onayla(s)
    assert k.eylem == "secenek" and k.mesaj.startswith("Planınız onaylandı (r02). Şimdi çatıyı seçin."), k.mesaj
    k = s.dugme("s:{set}:PA06K")
    assert k.eylem == "is_emri" and k.revizyon == 3 and k.is_emri["talep"]["kaynak"] == "PA06K", k.mesaj
    assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "YATAK ODASI 1"] == ["120x180"], k.mesaj


def test_revizyonda_cati_degisir(tmp_path):
    """r01 evin çatısıyla; bayi sonra "PA-06-C olsun" yazar (LLM revizyon okur) → aynı plan, cumbalı çatıyla r02. LLM yeni talep
    okursa bugünkü kural geçer (gönderilmiş plandan sonra yeni talep konuşmayı kapatır): cumbalı çatıyla yeni r01, çatı yeniden sorulmaz."""
    s, r01 = _plan(tmp_path)
    r01 = r01.is_emri
    k = s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["cati"]["tip"] == "besik_cumba", k.mesaj
    assert k.is_emri["talep"]["kaynak"] == "PA06C" and (k.is_emri["mahaller"], k.is_emri["acikliklar"]) == (r01["mahaller"], r01["acikliklar"])
    assert (_onayla(s).gerekce, s.plan["revizyon"]) == (K.PLAN_ONAYI, 2)          # çatıyı bayi seçti: onayda set gelmez
    s, _ = _plan(tmp_path / "b")
    k = s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C", niyet="yeni_talep")
    assert k.eylem == "is_emri" and k.revizyon == 1 and k.is_emri["talep"]["kaynak"] == "PA06C", k.mesaj
    assert _onayla(s).gerekce == K.PLAN_ONAYI


# ── çatı isteği (geometri hakemi, 12 Kasım 2026, üç tur): LLM `cati_degistir` okursa çatıyı yalnız seçeneğin kodu seçer; çatının adı
#    seti getirir (ek ve kuruluş okunmaz, tahmin yok, K21); seçeneklerin dışındaki çatı isteği bugünkü gibi yönlendirilir, düşmez ──
@pytest.mark.parametrize("metin,kod", [
    ("PA-06-K çatısı olsun", "PA06K"), ("PA-06-C olsun, salonun üstünde cumba", "PA06C"), ("PA 06 K olsun", "PA06K"),
    ("PA-06 olsun, çatı K olsun", "PA06K"),
])
def test_cati_kodu_secer(tmp_path, metin, kod):
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz(metin, katalog_kodu=metin[:5], yapi_turu="prefabrik", varyantlar=[var("cati_degistir", metin)])
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == kod and k.is_emri["cati"] == CATI[kod], k.mesaj


@pytest.mark.parametrize("metin", [
    "PA-06 olsun, çatı kırma olsun", "PA-06 olsun, kırma çatılı olsun", "PA-06 olsun, salonun üstünde cumba olsun",
    "PA-06 olsun, cumbalı beşik çatı olsun", "PA-06 olsun, çatı beşik olsun", "PA-06 olsun, kırma çatı olmasın",
    "PA-06 olsun, çatıyı değiştirelim", "PA-06 olsun, cumba istemiyoruz kırma olsun", "PA-06 olsun, kırma ve cumba olsun",
    "PA-06 olsun, cumbasız beşik olsun", "PA-06 olsun, kalkansız bir çatı olsun", "PA-06 olsun, kırmadan farklı bir çatı olsun",
    "PA-06 olsun, cumbadan başka bir çatı olsun", "PA-06 olsun, salonda çatı farklı olsun", "PA-06 olsun, o zaman kırma olsun",
    "PA-06 olsun, PA-06-K mı PA-06-C mi", "PA-06 olsun, PA-06-K olmasın", "PA-06 olsun, PA-06-K olsun, cumbalı olsun",
    "PA-06 olsun, PA-06-C olsun, kırma olsun", "şimdilik PA-06 olsun, PA-06-K'yı da görelim", "PA-06 olsun, çatı PA-06-K olsun",
    "PA-06 olsun, kırma çatıyı seçiyorum", "PA-06 olsun, kırma çatı olsun rica ederim", "PA-06 olsun, kırma çatılı olanı istiyoruz",
    "PA-06-K olsun, cumba kalsın", "PA-06-K olsun, kalkan önde kalsın",
])
def test_cati_adi_seti_getirir_secilen_cizilir(tmp_path, metin):
    """Çatının adı, olumsuz ya da kararsız söz: çatı seti (istek setin cevabı); setten seçilen çatı çizilir, yönlendirmeye düşmez."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz(metin, katalog_kodu="PA-06", yapi_turu="prefabrik", varyantlar=[var("cati_degistir", metin.split(", ", 1)[1])])
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti", k.mesaj
    k = s.dugme("s:{set}:PA06C")
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06C", k.mesaj


@pytest.mark.parametrize("metin", [
    "PA-06 olsun, çatı eğimi %40 olsun", "PA-06 olsun, saçak 50 cm olsun", "PA-06 olsun, çatı kırmızı kiremit olsun",
    "PA-06 olsun, çatı sandviç panel olsun", "PA-06 olsun, tek eğimli çatı olsun", "PA-06 olsun, mahya önde olsun",
    "PA-06 olsun, çatı kırma olsun, eğim %40 olsun", "PA-06 olsun, kırma çatı olsun, saçak 60 cm", "PA-06-K olsun, eğim %40 olsun",
    "PA-06 olsun, yatak odasının üstüne cumba olsun", "PA-06 olsun, mutfağın üstüne cumba yapın", "PA-06 olsun, arka cepheye cumba olsun",
    "PA-06 olsun, iki cumba olsun", "PA-06 olsun, mutfak duvarını kırmak istiyoruz, çatıyı da değiştirelim",
    "PA-06 olsun, salona cumba pencere olsun, çatı da değişsin", "PA-06 olsun, mutfak ve salonun üstüne cumba olsun",
    "PA-06 olsun, yatak odası ve salonun üstünde cumba olsun", "PA-06 olsun, çatı kalkar mı",
    "PA-06-C olsun, yatak odasının üstüne de aynı cumbadan olsun", "PA-06-C olsun, cumba yatak odasının üstünde kalacak",
    "PA-06-C olsun, cumba arka cephede dursun", "PA-06 olsun, cumbalı olsun, arka cepheye de aynı cumbadan yapın",
    "PA-06-K olsun, duvar tarafına oluk olsun", "PA-06-K olsun, yağmur oluğu da olsun", "PA-06-K olsun, baca olsun",
])
def test_cati_istegi_seceneklerin_disindaysa_yonlendirilir(tmp_path, metin):
    """Seçeneklerin adı dışında bir şey isteyen çatı cümlesi (eğim, saçak, kaplama, başka oda ya da cephe, sayı) bugünkü gibi
    yönlendirilir; mesaj bayinin cümlesini aynen ve seçilebilecek çatıları yazar. Salon cumbası başka odaya çizilmez; istek düşmez."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz(metin, katalog_kodu=metin[:5], yapi_turu="prefabrik", varyantlar=[var("cati_degistir", metin.split(", ", 1)[1])])
    assert k.eylem == "yonlendir" and "otomatik yapılamıyor" in k.mesaj and "PA-06-K (Kırma)" in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin,aciklama,eylem", [
    ("PA-06 olsun, kırma çatı olsun, zemin kaplaması laminat olsun", "kırma çatı olsun", "secenek"),
    ("PA-06 olsun, kırma çatı yapılsın", "kırma çatı yapılması", "secenek"),
    ("PA-06-C olsun, cumba kalsın", "cumba kalsın", "is_emri"), ("PA-06-C olsun, cumba kalsın", None, "is_emri"),
    ("PA-06-K olsun, cumba kalsın", None, "secenek"), ("PA-06-K'yı alalım", "PA-06-K'yı alalım", "is_emri"),
    ("PA-06-K modelini alalım", "PA-06-K modelini alalım", "is_emri"), ("PA-06-K olsun", "kırma çatıya geçiş", "is_emri"),
    ("PA-06-K olsun", "PA-06-K kırma çatı seçildi", "is_emri"), ("PA-06 olsun, kırma çatı yapalım", "kırma çatı yap", "secenek"),
    ("PA-06 olsun ama kırma çatı olsun", "kırma çatı olsun", "secenek"), ("PA-06 olsun, çatıyı kırma yap", "çatıyı kırma yap", "secenek"),
])
def test_llm_cati_istegi_okunan_cumleyle_kiyaslanir(tmp_path, metin, aciklama, eylem):
    """Hakem yedinci tur: LLM'in çatı isteği bu mesajda okunan cümlelerle karşılanıyorsa (bayinin sözü ya da adlaştırması) seçim ya da set;
    çatı dışı cümle ("zemin kaplaması") isteği yönlendirtmez. "cumba kalsın" kodun çatısıyla çelişirse set, uyarsa o çatı."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz(metin, katalog_kodu=metin[:5], yapi_turu="prefabrik", varyantlar=[var("cati_degistir", aciklama)] if aciklama else [])
    assert k.eylem == eylem, k.mesaj
    if eylem == "is_emri":
        assert k.is_emri["talep"]["kaynak"] == ("PA06C" if "PA-06-C" in metin else "PA06K"), k.mesaj
    else:
        assert s.k.d["secenek_seti"]["tur"] == "cati_varyanti", k.mesaj


@pytest.mark.parametrize("metin,kod", [("PA-06-K'ya geçelim", "PA06K"), ("PA-06-C'ye geçelim", "PA06C"), ("PA-06-K modeline geçelim", "PA06K")])
def test_revizyonda_kodla_gecis_llm_okumasiyla(tmp_path, metin, kod):
    """Hakem sekizinci tur: r01 evin çatısıyla; LLM bayinin sözünü `aciklama`ya yazsa da kodla geçiş seçimdir (yönlendirilmez)."""
    s, _ = _plan(tmp_path)
    k = s.yaz(metin, katalog_kodu=metin[:7], varyantlar=[var("cati_degistir", metin)])
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    s, _ = _cati_seti(tmp_path / "b")
    _secildi(s, s.yaz("ikinci çatı olsun", varyantlar=[var("cati_degistir", "2. çatı")]), "PA06K")
    s, _ = _cati_seti(tmp_path / "c")
    _secildi(s, s.yaz(metin, katalog_kodu=metin[:7], varyantlar=[var("cati_degistir", metin)]), kod)


def test_cumba_kalsin_kodla_celisirse_sorulur(tmp_path):
    """Set açıkken "ikinci çatı olsun, cumba kalsın" (kırma + cumba) seçim değil: soru; r01 PA-06-C'de revizyon "PA-06-K olsun, cumba
    kalsın" çatı setini getirir, cumbasız plan çizilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("ikinci çatı olsun, cumba kalsın")
    assert k.eylem == "sor" and "Hangi çatı olsun?" in k.mesaj, k.mesaj
    s = Sohbet(tmp_path / "b", kabul=PA | CATILAR)
    assert s.yaz("PA-06-C olsun", katalog_kodu="PA-06-C", yapi_turu="prefabrik").eylem == "is_emri"
    k = s.yaz("PA-06-K olsun, cumba kalsın", katalog_kodu="PA-06-K", varyantlar=[var("cati_degistir", "PA-06-K olsun, cumba kalsın")])
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti", k.mesaj


def test_yonlendirme_bayinin_cumlesini_aynen_yazar(tmp_path):
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06 olsun, çatı eğimi %40 olsun", katalog_kodu="PA-06", yapi_turu="prefabrik", varyantlar=[var("cati_degistir", "eğim %40")])
    assert k.mesaj.startswith('"çatı eğimi %40 olsun" isteği otomatik yapılamıyor; bu evde çatı için şunlar seçilebilir: PA-06 (Beşik, '
                              'kalkan önde), PA-06-K (Kırma), PA-06-C (Beşik + salonda cumba).'), k.mesaj


def test_cati_istegi_ve_pencere_birlikte(tmp_path):
    """Çatı kodu seçer, pencere cümlesi kendi yolundan uygulanır (aynı mesajda)."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06-K olsun, banyo penceresi 120x50 olsun", katalog_kodu="PA-06-K", yapi_turu="prefabrik",
              varyantlar=[var("cati_degistir", "PA-06-K")], pencereler=[pen("banyo", "120x50")])
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06K" and k.is_emri["cati"]["tip"] == "kirma", k.mesaj
    assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "BANYO"] == ["120x50"], k.mesaj     # şablonda 60x40


def test_cati_seti_acikken_ve_revizyonda_secenek_disi_istek(tmp_path):
    """Seçeneklerin dışındaki çatı isteği yönlendirilir. Set açıkken (İE-42) plan onay bekler kalır, set düşer: sonraki "Onayla" çatıyı
    yeniden sorar (yönlendirilen istek onayı kaydettirmez)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("çatı eğimi %40 olsun", varyantlar=[var("cati_degistir", "çatı eğimi %40")])
    assert k.eylem == "yonlendir" and "otomatik yapılamıyor" in k.mesaj, k.mesaj
    assert s.k.d["asama"] == "onay_bekliyor" and (s.k.d.get("secenek_seti") or {}).get("durum") != "acik"
    k = _onayla(s)
    assert k.eylem == "secenek" and k.mesaj.startswith("Planınız onaylandı (r01). Şimdi çatıyı seçin."), k.mesaj
    s, _ = _plan(tmp_path / "b")
    k = s.yaz("çatı eğimi %40 olsun", varyantlar=[var("cati_degistir", "çatı eğimi %40")])
    assert k.eylem == "yonlendir" and "otomatik yapılamıyor" in k.mesaj, k.mesaj
    s = Sohbet(tmp_path / "c", kabul=PA | CATILAR)          # hakem altıncı tur: "kalacak" sözlü istek düşmez, r02 çizilmez
    assert s.yaz("PA-06-K olsun", katalog_kodu="PA-06-K", yapi_turu="prefabrik").eylem == "is_emri"
    m = "PA-06-C olsun, cumba yatak odasının üstünde kalacak"
    k = s.yaz(m, katalog_kodu="PA-06-C", varyantlar=[var("cati_degistir", "cumba yatak odasının üstünde")])
    assert k.eylem == "yonlendir" and k.mesaj.startswith('"cumba yatak odasının üstünde kalacak" isteği otomatik'), k.mesaj


@pytest.mark.parametrize("metin", ["kırma olsun", "kırmadan farklı olsun", "cumbasız olsun"])
def test_cati_seti_acikken_cati_adi_sorulur(tmp_path, metin):
    """Set açıkken çatının adı seçim yapmaz: "Hangi çatı olsun?" sorulur, set açık kalır, numara cevabı seçer."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, varyantlar=[var("cati_degistir", metin)])
    assert k.eylem == "sor" and "Hangi çatı olsun?" in k.mesaj and "3. PA-06-C (Beşik + salonda cumba)" in k.mesaj, k.mesaj
    assert s.k.d["secenek_seti"]["durum"] == "acik"
    _secildi(s, s.yaz("2", niyet="diger"), "PA06K")


@pytest.mark.parametrize("metin,kod", [("çatı K olsun", "PA06K"), ("K olsun", "PA06K"), ("C olsun", "PA06C"), ("PA-06 olsun", "PA06")])
def test_cati_seti_acikken_etiket_ve_evin_kodu(tmp_path, metin, kod):
    """Set açıkken mesajın etiketi ("çatı K") ve evin kodu seçimdir (LLM varyant okumasa da); evin kodu evin çatısıdır: onay."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, katalog_kodu=None), kod)


@pytest.mark.parametrize("metin,alan", [
    ("kırma olsun", {}), ("cumbalı olan", {}), ("tamam", {}), ("kırma çatıyı seçiyorum", {}), ("kırma olsun", {"niyet": "diger"}),
    ("tamam", {"niyet": "onay"}), ("tamam", {"niyet": "diger"}), ("bakalım", {"katalog_kodu": "PA-06", "alan_m2": 85}),
])
def test_cati_seti_acikken_secim_yoksa_evin_catisi_cizilmez(tmp_path, metin, alan):
    """Hakem dördüncü tur: set açıkken kodsuz ve varyantsız mesaj evin çatısıyla çizilmiyor; "Hangi çatı olsun?" sorulur. İE-42: onay da
    seçim değildir (plan onaylandı, çatı bekleniyor); LLM'in bağlamdan yinelediği kod ve m² istek sayılmaz, onay kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert k.eylem == "sor" and "Hangi çatı olsun?" in k.mesaj and s.k.d["secenek_seti"]["durum"] == "acik", k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and s.k.d["asama"] == "onay_bekliyor" and s.k.d.get("cati_adimi")


def test_cati_seti_acikken_pencere_istegi_plani_degistirir(tmp_path):
    """İE-42 (D-94: "Çatı seti açıkken plan değişirse set kapanır"): set açıkken yalnız pencere isteği planın değişikliğidir. Set kapanır,
    pencere evin çatısıyla r02'de uygulanır, r01'in onayı düşer; r02 onaylanınca çatı yeniden sorulur. (İE-37'de çatı sorulup pencere
    bekliyordu; plan o zaman henüz çizilmemişti.)"""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("banyo penceresi 120x50 olsun", pencereler=[pen("banyo", "120x50")])
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj
    assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "BANYO"] == ["120x50"], k.mesaj
    assert k.mesaj.endswith("Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir."), k.mesaj
    assert s.k.d["asama"] == "onay_bekliyor" and not s.k.d.get("cati_adimi")
    eski = next(e for e in s.k.d["eski_setler"] if e["tur"] == "cati_varyanti")
    assert eski["durum"] == "eskidi"
    k = _onayla(s)                                       # r02'nin onayında çatı yeniden sorulur
    assert k.eylem == "secenek" and k.mesaj.startswith("Planınız onaylandı (r02). Şimdi çatıyı seçin."), k.mesaj
    k = s.yaz("2", niyet="diger")
    _secildi(s, k, "PA06K", rev=3)
    assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "BANYO"] == ["120x50"], k.mesaj


def test_cati_seti_acikken_cati_ve_pencere_birlikte(tmp_path):
    """Set açıkken çatı ve pencere aynı mesajda: çatı seçilir, pencere uygulanır; plan değiştiği için mesaj onayın düştüğünü yazar."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("2 olsun, banyo penceresi 120x50 olsun", pencereler=[pen("banyo", "120x50")])
    _secildi(s, k, "PA06K")
    assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "BANYO"] == ["120x50"], k.mesaj
    assert k.mesaj.startswith("Çatı: Kırma (PA-06-K). ") and k.mesaj.endswith("Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için "
                                                                                "yeniden onay gerekir."), k.mesaj
    assert _onayla(s).gerekce == K.PLAN_ONAYI                # çatı seçildi: r02'nin onayında set gelmez


@pytest.mark.parametrize("metin", ["PA-06 olsun, çatı aynı kalsın", "PA-06 olsun, zemin kaplaması laminat olsun",
                                   "PA-06 olsun, girişe eğimli rampa yapın"])
def test_cati_istegi_olmayan_cumle_bugunku_yol(tmp_path, metin):
    """Hakem beşinci tur: "kalsın" cümlesi ve çatı dışı "kaplama", "eğimli" sözü çatı isteği değildir; plan evin çatısıyla r01 (İE-42),
    çatı onaydan sonra sorulur."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz(metin, katalog_kodu="PA-06", yapi_turu="prefabrik")
    assert k.eylem == "is_emri" and k.revizyon == 1 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj


@pytest.mark.parametrize("metin,pencere", [("banyo penceresi 120x50 olsun, çatı aynı kalsın", True),
                                           ("kırma kalsın, banyo penceresi 120x50 olsun", True),
                                           ("banyo penceresi 120x50 olsun, çatı olduğu gibi kalsın", True),
                                           ("salonun zemin kaplaması laminat olsun", False)])
def test_cati_secenekli_evde_revizyon_yonlenmez(tmp_path, metin, pencere):
    """r01 PA-06-K; pencere revizyonu ve çatıyı koruyan söz çatı okumasına takılmaz: r02 aynı çatıyla."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    assert s.yaz("PA-06-K olsun", katalog_kodu="PA-06-K", yapi_turu="prefabrik").eylem == "is_emri"
    k = s.yaz(metin, pencereler=[pen("banyo", "120x50")] if pencere else [])
    assert k.eylem != "yonlendir" or "çatı için" not in k.mesaj, k.mesaj
    if pencere:
        assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06K", k.mesaj
        assert [a["olcu"] for a in k.is_emri["acikliklar"] if a.get("mahal") == "BANYO"] == ["120x50"], k.mesaj


@pytest.mark.parametrize("metin,kod", [("2 numaralı çatı olsun", "PA06K"), ("3 numaralı olsun", "PA06C"), ("ikinci çatı olsun", "PA06K"),
                                      ("birinci çatı olsun", "PA06"), ("üçüncü olsun", "PA06C"), ("son çatı olsun", "PA06C")])
def test_cati_seti_acikken_numarali_secim(tmp_path, metin, kod):
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin), kod)


def test_revizyonda_cati_adi_seti_getirir(tmp_path):
    """r01 evin çatısıyla; onaydan önce revizyonda "çatı kırma olsun" → çatı seti; seçilen çatıyla r02 (plan aynı)."""
    s, r01 = _plan(tmp_path)
    r01 = r01.is_emri
    k = s.yaz("çatı kırma olsun", varyantlar=[var("cati_degistir", "çatı kırma olsun")])
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti", k.mesaj
    k = s.dugme("s:{set}:PA06K")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06K", k.mesaj
    assert k.is_emri["mahaller"] == r01["mahaller"]


def test_cati_istegi_secenek_gorunmezse_bugunku_yol(tmp_path):
    """Seçenekleri kabul edilmemiş evde çatı isteği bugünkü gibi yönlendirilir (sessizce düşmez)."""
    s = Sohbet(tmp_path, kabul=PA)
    k = s.yaz("PA-06 olsun, çatı kırma olsun", katalog_kodu="PA-06", yapi_turu="prefabrik", varyantlar=[var("cati_degistir", "çatı kırma")])
    assert k.eylem == "yonlendir" and "otomatik yapılamıyor" in k.mesaj, k.mesaj


def test_kismi_kabul(tmp_path):
    """Yalnız kırma kabul edildiyse set iki çatı ("Bu eve 2 çatı uygulanır"); hiçbiri kabul edilmediyse onayda çatı sorulmaz, onay kaydedilir
    (bugünkü yol; öteki 28 ev de böyle)."""
    s, k = _cati_seti(tmp_path, kabul=PA | {"PA06K"})
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA06", "PA06K"], k.mesaj
    assert k.mesaj.startswith("Planınız onaylandı (r01). Şimdi çatıyı seçin. Bu eve 2 çatı uygulanır."), k.mesaj
    s, k = _cati_seti(tmp_path / "b", kabul=PA)
    assert (k.eylem, k.gerekce, s.plan["cati"]["tip"]) == ("cevapla", K.PLAN_ONAYI, "besik"), k.mesaj
    assert k.mesaj.startswith("Onayınız kaydedildi"), k.mesaj


def test_cati_seti_acikken_olcu_degisirse_set_eskir(tmp_path):
    """İE-25 kuralı prefabrikte de: çatı seti açıkken yeni m² sessizce düşmez. İE-42: plan çizilmiş olduğu için yeni talep konuşmayı
    kapatır (gönderilmiş plandan sonraki bugünkü kural) ve talep yeniden okunur; revizyon okunursa çatı seti düşer, plan onay bekler
    (BK-29), "Onayla" çatıyı yeniden sorar. Onay iki yolda da kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("80 m2 2+1 olsun", alan_m2=80, oda_programi="2+1", niyet="yeni_talep")
    assert k.eylem == "sor" and "öne çıksın" in k.mesaj and not s.k.d.get("cati_adimi") and K.PLAN_ONAYI not in k.gerekce, k.mesaj
    k = s.yaz("fark etmez", niyet="yeni_talep")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "alan", k.mesaj
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA04", "PA05", "PA06"]
    s, _ = _cati_seti(tmp_path / "b")
    k = s.yaz("80 m2 olsun", alan_m2=80)
    assert (s.k.d["asama"], s.k.d["secenek_seti"]["durum"], s.k.d.get("cati_adimi")) == ("onay_bekliyor", "dustu", None), k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and "değişmedi" in k.mesaj, k.mesaj
    assert _onayla(s).mesaj.startswith("Planınız onaylandı (r01). Şimdi çatıyı seçin.")


def test_kabul_araci_cati_kodlarini_tanir(capsys):
    """K-A10 kabul aracı prefabrik kaydıyla çatı kodlarını da yazabilir (her kod ayrı; `--kuru` yazmaz); kayıtta olmayan kod durur."""
    from araclar import aday_kabul
    ev = str(ADAYLAR_PREFABRIK_JSON)
    assert aday_kabul.main(["--kodlar", "PA-06,PA-06-K,PA-06-C", "--tarih", "2026-11-12", "--adaylar", ev, "--kuru"]) == 0
    assert "3 kayıt yazılacak (PA06, PA06K, PA06C)" in capsys.readouterr().out
    assert aday_kabul.main(["--kodlar", "PA-06-Z", "--tarih", "2026-11-12", "--adaylar", ev, "--kuru"]) == 2
    assert "olmayan kod: PA06Z" in capsys.readouterr().out


def test_kart_altyazisi():
    from motor import bayi_gorseli as BG
    a = {**KAYIT["varyantlar"][1], "sunum": {"cati_adi": "Beşik + salonda cumba"}}
    assert BG.kart_altyazisi({**a, "cati_karti": True}) == ["Çatı: Beşik + salonda cumba", "87 m² katalog · kapalı 72,6 m²"]
    assert BG.kart_altyazisi(a) == ["Beşik + salonda cumba · 87 m² katalog · kapa"]     # işaretsiz: bugünkü tek satır (değişmez)
