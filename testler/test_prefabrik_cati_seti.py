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
    kapatır (gönderilmiş plandan sonraki bugünkü kural) ve talep yeniden okunur. Hakem tur 1 (bulgu 9): LLM "revizyon" okusa da m²
    isteği aynı evin planında "değişmedi" diye düşmez; set kapanır, talep yeni m²'yle (oda programı taslaktan) yeniden okunur. Onay iki
    yolda da kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("80 m2 2+1 olsun", alan_m2=80, oda_programi="2+1", niyet="yeni_talep")
    assert k.eylem == "sor" and "öne çıksın" in k.mesaj and not s.k.d.get("cati_adimi") and K.PLAN_ONAYI not in k.gerekce, k.mesaj
    k = s.yaz("fark etmez", niyet="yeni_talep")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "alan", k.mesaj
    assert [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA04", "PA05", "PA06"]
    s, _ = _cati_seti(tmp_path / "b")
    k = s.yaz("80 m2 olsun", alan_m2=80)
    assert k.eylem == "sor" and "öne çıksın" in k.mesaj and not s.k.d.get("cati_adimi") and K.PLAN_ONAYI not in k.gerekce, k.mesaj
    assert "değişmedi" not in k.mesaj and s.k.d["taslak"]["alan_m2"] == 80 and s.k.d["taslak"]["oda_programi"] == "2+1"
    k = s.yaz("fark etmez", niyet="yeni_talep")
    assert k.eylem == "secenek" and [a["kod"] for a in s.k.d["secenek_seti"]["adaylar"]] == ["PA04", "PA05", "PA06"], k.mesaj
    s, _ = _cati_seti(tmp_path / "c")
    k = s.yaz("85 m2 2+1 olsun", alan_m2=85, oda_programi="2+1")             # LLM'in yinelediği aynı m² ve oda: istek değil, çatı sorulur
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.k.d.get("cati_adimi"), k.mesaj


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


# ── İE-42 · geometri hakemi tur 1 (14 Kasım 2026 gece) ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin, alan", [
    ("tamam", {"niyet": "yeni_talep"}),                                          # bulgu 5: içeriksiz "yeni talep" konuşmayı sıfırlamaz
    ("bakalım", {"niyet": "yeni_talep", "katalog_kodu": "PA-06"}),               # LLM'in yinelediği evin kodu
    ("tamam", {"niyet": "diger"}),
])
def test_hakem1_iceriksiz_mesaj_cati_sorar(tmp_path, metin, alan):
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.k.d.get("cati_adimi"), k.mesaj
    assert (s.plan["revizyon"], s.k.d["asama"], s.k.d["secenek_seti"]["durum"]) == (1, "onay_bekliyor", "acik")


def test_hakem1_acik_yeni_talep_sozu_seti_kapatir(tmp_path):
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("yeni talep: 60 m2 1+1 prefabrik", niyet="yeni_talep", alan_m2=60, oda_programi="1+1", yapi_turu="prefabrik")
    assert not k.mesaj.startswith("Hangi çatı olsun?") and not s.k.d.get("cati_adimi") and K.PLAN_ONAYI not in k.gerekce, k.mesaj


def test_hakem1_yalniz_musteri_bilgisi_dusmez(tmp_path):
    """Bulgu 3: set açıkken yalnız müşteri adı ya da sevk adresi taşıyan mesaj istektir: "Hangi çatı olsun?" sorulup düşmez; plan bilgiyle
    r02 olur, r01'in onayı düşer."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("müşteri Ayşe Deneme, sevk adresi Deneme İlçesi", musteri={"ad": "Ayşe Deneme", "sevk_adresi": "Deneme İlçesi"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["talep"]["kaynak"] == "PA06", k.mesaj
    assert (s.plan["talep"]["musteri_adi"], s.plan["kunye"]["sevk_adresi"]) == ("Ayşe Deneme", "Deneme İlçesi")
    assert k.mesaj.endswith("Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir."), k.mesaj


@pytest.mark.parametrize("metin, alan, alanin_yeri", [
    ("1 olsun, sevk adresi Deneme İlçesi", {"musteri": {"sevk_adresi": "Deneme İlçesi"}}, ("kunye", "sevk_adresi", "Deneme İlçesi")),
    ("1 olsun, mutfak dolapları beyaz olsun", {"ozel_istekler": ["mutfak dolapları beyaz olsun"]},
     ("ozel_istekler", None, ["mutfak dolapları beyaz olsun"])),
    ("1 olsun, yatak odası 1 penceresi 120x180 olsun", {"pencereler": [pen("yatak odası 1", "120x180")]}, None),
])
def test_hakem1_evin_catisi_ve_ayni_mesajdaki_bilgi(tmp_path, metin, alan, alanin_yeri):
    """Bulgu 2: evin çatısı seçilip aynı mesajda bilgi ya da istek varsa onay o an kaydedilmez (bilgi düşerdi): plan bilgiyle r02, çatı
    seçilmiş sayılır (r02'nin onayında çatı yeniden sorulmaz)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["talep"]["kaynak"] == "PA06" and K.PLAN_ONAYI not in k.gerekce, k.mesaj
    assert k.mesaj.startswith("Çatı: Beşik, kalkan önde (PA-06).") and "r01 onayınızı geçersiz kıldı" in k.mesaj, k.mesaj
    if alanin_yeri:
        a, b, deger = alanin_yeri
        assert (s.plan[a][b] if b else s.plan[a]) == deger
    k = _onayla(s)
    assert (k.eylem, k.gerekce, s.k.d["asama"]) == ("cevapla", K.PLAN_ONAYI, "onaylandi"), k.mesaj


def test_hakem1_evin_catisi_ve_planda_olan_istek_onaylar(tmp_path):
    """Bulgu 6: evin çatısı + planda zaten olan pencere ölçüsü (D-86: plan değişmedi) çatı seçimini düşürmez: r01 onaylanır, bayiye
    çatı ve zaten olan ölçü yazılır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("1 olsun, yatak odası 1 penceresi 120x120 olsun", pencereler=[pen("yatak odası 1", "120x120")])
    assert (k.eylem, k.gerekce, s.k.d["asama"], s.plan["revizyon"]) == ("cevapla", K.PLAN_ONAYI, "onaylandi", 1), k.mesaj
    assert k.mesaj.startswith("Çatı: Beşik, kalkan önde (PA-06). Plan r01 aynen kalır; YATAK ODASI 1 penceresi zaten 120x120. "
                              "Onayınız kaydedildi"), k.mesaj
    assert s.k.d["cati_secilen"] == "PA06" and not s.k.d.get("cati_adimi")


def test_hakem1_cati_ve_geri_cevrilen_istek_secimi_dusurmez(tmp_path):
    """Bulgu 6: çatı seçimi + otomatik yapılamayan istek (yönlendirme): plan değişmez, set açık kalır, bayiye çatı seçiminin kaydedilmediği
    yazılır ve setin düğmeleri yeniden gider; düğmeyle seçim r02'yi çizer."""
    s, _ = _cati_seti(tmp_path)
    st = s.k.d["secenek_seti"]
    k = s.yaz("2 olsun, verandayı arkaya alın", varyantlar=[var("veranda_degistir", "verandayı arkaya al")])
    assert k.eylem == "yonlendir" and k.mesaj.endswith("değişmedi. Çatı seçiminizi (PA-06-K) kaydetmedim; çatıyı yeniden seçin."), k.mesaj
    assert [b["id"] for b in k.butonlar] == [f"s:{st['id']}:{c}" for c in ("PA06", "PA06K", "PA06C")]
    assert (s.k.d["asama"], s.k.d["secenek_seti"]["durum"], s.plan["revizyon"]) == ("onay_bekliyor", "acik", 1) and s.k.d.get("cati_adimi")
    assert not s.k.d.get("cati_secilen")
    _secildi(s, s.dugme(f"s:{st['id']}:PA06K"), "PA06K")


def test_hakem1_yalniz_cati_degisince_onay_dusme_notu_yok(tmp_path):
    """Bulgu 7: başka çatı + planda zaten olan pencere: plan yalnız çatıda değişti, "r01 onayınızı geçersiz kıldı" yazılmaz; zaten olan
    ölçü yazılır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("2 olsun, yatak odası 1 penceresi 120x120 olsun", pencereler=[pen("yatak odası 1", "120x120")])
    _secildi(s, k, "PA06K")
    assert k.mesaj.startswith("Çatı: Kırma (PA-06-K). Plan aynı; YATAK ODASI 1 penceresi zaten 120x120. Ön onay planınız hazır (r02)"), k.mesaj
    assert "geçersiz kıldı" not in k.mesaj


@pytest.mark.parametrize("metin, niyet, kod", [
    ("K olsun, onaylıyorum", "onay", "PA06K"),
    ("1 olsun, onaylıyorum", "onay", "PA06"),
    ("PA-06-K olsun, fiyatı ne olur?", "soru", "PA06K"),
])
def test_hakem1_onay_ve_soru_sozunde_cati_secimi(tmp_path, metin, niyet, kod):
    """Bulgu 8: LLM "onay" ya da "soru" okusa da mesajdaki açık çatı seçimi okunur (evin çatısı onaylar, başka çatı r02)."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, niyet=niyet), kod)


@pytest.mark.parametrize("metin, niyet, beklenen", [
    ("onaylıyorum", "onay", "Hangi çatı olsun?"),
    ("fiyatı ne olur?", "soru", "Planınız"),
])
def test_hakem1_secimsiz_onay_ve_soru(tmp_path, metin, niyet, beklenen):
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet=niyet)
    assert k.mesaj.startswith(beklenen) and s.k.d.get("cati_adimi") and s.k.d["secenek_seti"]["durum"] == "acik", k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and s.plan["revizyon"] == 1


def test_hakem1_kararsiz_cati_ve_istek_bayiye_yazilir(tmp_path):
    """Çatı sözü kararsız ("olmasın" sözü) ve mesajda başka istek var: "Hangi çatı olsun?" sorulur, öteki isteğin uygulanmadığı yazılır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("1 olsun, mutfak penceresi olmasın", pencereler=[pen("mutfak", None, islem="kaldir")])
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.k.d.get("cati_adimi"), k.mesaj
    assert k.mesaj.endswith("Mesajınızdaki öteki isteği uygulamadım. Önce çatıyı seçin, sonra o isteği yeniden yazın."), k.mesaj


# ── İE-42 · geometri hakemi tur 2 (14 Kasım 2026 gece) ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin, alan", [
    ("1 olsun, yükseklik 260 olsun", {"yukseklik_cm": 260}),
    ("1 olsun, dış kapı çelik olsun", {"dis_kapi": "çelik"}),
    ("PA-06 olsun, veranda olsun", {"katalog_kodu": "PA-06", "veranda": {"istiyor": True}}),
])
def test_hakem2_evin_catisi_ve_uygulanmayan_istek(tmp_path, metin, alan):
    """Y1: evin çatısı + Motor'un plana işlemediği istek (yükseklik, kapı, veranda): plan değişmedi ama onay kaydedilmez (istek sessiz
    düşerdi). Set açık kalır; bayiye isteğin uygulanmadığı ve çatı seçiminin kaydedilmediği yazılır, düğmeler yeniden gider."""
    s, _ = _cati_seti(tmp_path)
    st = s.k.d["secenek_seti"]
    k = s.yaz(metin, **alan)
    assert K.PLAN_ONAYI not in k.gerekce and s.k.d["asama"] == "onay_bekliyor" and s.plan["revizyon"] == 1, k.mesaj
    assert k.mesaj.endswith("değişmedi; isteğinizi plana uygulayamadım. Çatı seçiminizi (PA-06) kaydetmedim; çatıyı yeniden seçin."), k.mesaj
    assert s.k.d.get("cati_adimi") and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan")
    assert [b["id"] for b in k.butonlar] == [f"s:{st['id']}:{c}" for c in ("PA06", "PA06K", "PA06C")]
    _secildi(s, s.dugme(f"s:{st['id']}:PA06"), "PA06")


def test_hakem2_baska_cati_ve_uygulanmayan_istek(tmp_path):
    """Y1'in başka çatıdaki karşılığı: plan yalnız çatıda değişti, istek "Plan aynı" ile düşmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("2 olsun, yükseklik 260 olsun", yukseklik_cm=260)
    _secildi(s, k, "PA06K")
    assert k.mesaj.startswith("Çatı: Kırma (PA-06-K). Plan aynı; isteğinizi plana uygulayamadım. Ön onay planınız hazır (r02)"), k.mesaj


@pytest.mark.parametrize("metin, alan, secim", [
    ("2 olsun, 100 m2 olsun", {"alan_m2": 100}, "PA-06-K"),
    ("PA-06-K olsun, 3+1 olsun", {"katalog_kodu": "PA-06-K", "oda_programi": "3+1"}, "PA-06-K"),
    ("1 olsun, 100 m2 olsun", {"alan_m2": 100}, "PA-06"),
])
def test_hakem2_cati_ve_talep_degisikligi(tmp_path, metin, alan, secim):
    """O1: çatı seçimiyle aynı mesajda m² ya da oda değişti: talep değişikliği önce gelir (istek "Plan aynı" ile düşmezdi). Set kapanır,
    talep yeni talep olur; bayiye çatı seçiminin kaydedilmediği yazılır, onay kaydedilmez. Hakem tur 3: set mesajı "Planınız onaylandı
    (r01)" demişti; cevap önce r01 onayının geçersiz kaldığını yazar."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="revizyon", **alan)
    assert k.mesaj.startswith(f"Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı. Çatı seçiminizi ({secim}) kaydetmedim. "
                              "Önce yeni plan seçilir."), k.mesaj
    assert k.eylem != "is_emri" and K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("cati_adimi") and not s.k.d.get("cati_secilen")
    ts = s.k.d["taslak"]
    assert ts.get("alan_m2") == alan.get("alan_m2", 85) and ts.get("oda_programi") == alan.get("oda_programi", "2+1"), ts


@pytest.mark.parametrize("metin, niyet", [
    ("PA-06-K nasıl bir çatı?", "soru"),
    ("PA-06-K'nın fiyatı ne kadar?", "soru"),
    ("PA-06-K mı PA-06-C mi bilemedim, onaylıyorum", "onay"),
])
def test_hakem2_soru_cumlesindeki_kod_secim_degil(tmp_path, metin, niyet):
    """O2: soru cümlesindeki kod çatı seçimi değildir (K21): plan çizilmez, çatı seçilmiş yazılmaz, set açık kalır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet=niyet)
    assert k.eylem != "is_emri" and K.PLAN_ONAYI not in k.gerekce and s.plan["revizyon"] == 1, k.mesaj
    assert not s.k.d.get("cati_secilen") and s.k.d.get("cati_adimi") and s.k.d["secenek_seti"]["durum"] == "acik"


def test_hakem2_tamam_ve_kartin_m2_si(tmp_path):
    """O4: "tamam"ı LLM kartın m²'siyle yeni talep okur (87; taslakta 85): bayi sayı yazmadı, konuşma sıfırlanmaz, çatı sorulur."""
    s, _ = _cati_seti(tmp_path)
    no = s.plan["is_emri_no"]
    for niyet in ("yeni_talep", "revizyon", "diger"):
        k = s.yaz("tamam", niyet=niyet, katalog_kodu="PA-06", alan_m2=87)
        assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.plan["is_emri_no"] == no, (niyet, k.mesaj)


@pytest.mark.parametrize("metin, alan", [
    ("müşteri adı Ayşe Deneme", {"musteri": {"ad": "Ayşe Deneme"}}),
    ("mutfak penceresi 120x180 olsun", {"pencereler": [pen("mutfak", "120x180")]}),
])
@pytest.mark.parametrize("niyet", ["diger", "yeni_talep"])
def test_hakem2_diger_ve_yeni_talep_okunan_istek(tmp_path, metin, alan, niyet):
    """O5: "diğer" ya da "yeni talep" okunan istek ve bilgi planın değişikliğidir: set sessizce kapanmaz, konuşma sıfırlanmaz; plan
    değişikliği bugünkü yoldan (r02 ya da pencere sorusu), r01'in onayı düşer."""
    s, _ = _cati_seti(tmp_path)
    no = s.plan["is_emri_no"]
    k = s.yaz(metin, niyet=niyet, **alan)
    assert not k.mesaj.startswith("Anlayamadım") and s.plan["is_emri_no"] == no and not k.mesaj.startswith("Kaç oda"), k.mesaj
    if k.eylem == "is_emri":
        assert k.revizyon == 2 and k.mesaj.endswith("Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir."), k.mesaj
    else:
        assert k.eylem == "sor" and s.k.d.get("cati_onayi_dustu") == 1, k.mesaj


def test_hakem2_talep_degisince_onceki_bilgi_kalir(tmp_path):
    """O6: m² değişikliği yeni talep olur ama önceki mesajların bilgisi düşmez (müşteri, özel istek)."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("85 m2 2+1 prefabrik ev, müşteri Ayşe Deneme, mutfak dolapları beyaz olsun", alan_m2=85, oda_programi="2+1",
              yapi_turu="prefabrik", musteri={"ad": "Ayşe Deneme"}, ozel_istekler=["mutfak dolapları beyaz olsun"])
    if k.eylem == "sor" and "öne çıksın" in (k.mesaj or ""):
        k = s.yaz("fark etmez", niyet="yeni_talep")
    k = s.dugme("s:{set}:PA06")
    assert k.eylem == "is_emri", k.mesaj
    assert _onayla(s).eylem == "secenek"
    k = s.yaz("80 m2 olsun", niyet="revizyon", alan_m2=80)
    ts = s.k.d["taslak"]
    assert (ts.get("musteri") or {}).get("ad") == "Ayşe Deneme" and ts.get("ozel_istekler") == ["mutfak dolapları beyaz olsun"], ts
    assert (ts.get("alan_m2"), ts.get("oda_programi"), ts.get("yapi_turu")) == (80, "2+1", "prefabrik"), ts


def test_hakem2_kodla_secilen_evde_m2_istegi(tmp_path):
    """O8: kodla seçilen evde (taslakta m² yok) "80 m2 olsun" ±%10 toleransa takılmaz: talep değişti (87 m²'lik ev)."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("PA-06 olsun", katalog_kodu="PA-06")
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == "PA06", k.mesaj
    assert _onayla(s).eylem == "secenek"
    k = s.yaz("80 m2 olsun", niyet="revizyon", alan_m2=80)
    assert not k.mesaj.startswith("Hangi çatı olsun?") and not s.k.d.get("cati_adimi") and s.k.d["taslak"].get("alan_m2") == 80, k.mesaj


def test_hakem2_zaten_notu_yalniz_bu_mesajin_odasi(tmp_path):
    """D1: r02'de yatak odası penceresi değişti; çatı setinden K seçilince "Plan aynı" notu önceki revizyonun penceresini yazmaz."""
    s, _ = _plan(tmp_path)
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    st = _onayla(s)
    k = s.dugme("s:{set}:PA06K")
    _secildi(s, k, "PA06K", rev=3)
    assert k.mesaj.startswith("Çatı: Kırma (PA-06-K). Plan aynı. Ön onay planınız hazır (r03)"), k.mesaj


def test_hakem2_pencere_sorusu_hicbiri_yalniz_cati(tmp_path):
    """D2: çatı + iki pencereli oda → "Hangi pencere?" → "hiçbiri": plan yalnız çatıda değişti; "Çatı:" yazılır, onay düşme notu yok."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("2 olsun, salon penceresi 120x180 olsun", pencereler=[pen("salon", "120x180")])
    assert k.eylem == "sor" and k.soru_alani == "pencere_secim", k.mesaj
    k = s.yaz("hiçbiri", niyet="diger")
    _secildi(s, k, "PA06K")
    assert "Çatı: Kırma (PA-06-K). Plan aynı." in k.mesaj and "geçersiz kıldı" not in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin, kod", [("2 olsun onaylıyorum", "PA06K"), ("ikinci çatı olsun, onaylıyorum", "PA06K")])
def test_hakem2_virgulsuz_onay_sozunde_secim(tmp_path, metin, kod):
    """D4: onay sözü virgülsüz ya da sıra sözüyle gelince de seçim okunur."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, niyet="onay"), kod)


def test_hakem2_onay_sozunde_secimsiz_istek_bayiye_yazilir(tmp_path):
    """D4: onay niyetinde seçim yok ama pencere isteği var: "Hangi çatı olsun?" ve isteğin uygulanmadığı yazılır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("onaylıyorum, mutfak penceresi 120x180 olsun", niyet="onay", pencereler=[pen("mutfak", "120x180")])
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert k.mesaj.endswith("Mesajınızdaki öteki isteği uygulamadım. Önce çatıyı seçin, sonra o isteği yeniden yazın."), k.mesaj


# ── İE-42 · geometri hakemi üçüncü tur (14 Kasım 2026 gecesi): istek bayinin sözünden, LLM'in alanından değil (K18) ─────────────────────
def _ayse_seti(tmp_path: Path) -> Sohbet:
    """Müşterisi ve özel isteği olan talep → PA-06 r01 → Onayla → çatı seti."""
    s = Sohbet(tmp_path, kabul=PA | CATILAR)
    k = s.yaz("85 m2 2+1 prefabrik ev, müşteri Ayşe Deneme, mutfak dolapları beyaz olsun", alan_m2=85, oda_programi="2+1",
              yapi_turu="prefabrik", musteri={"ad": "Ayşe Deneme"}, ozel_istekler=["mutfak dolapları beyaz olsun"])
    if k.eylem == "sor" and "öne çıksın" in (k.mesaj or ""):
        k = s.yaz("fark etmez", niyet="yeni_talep")
    assert s.dugme("s:{set}:PA06").eylem == "is_emri"
    assert _onayla(s).eylem == "secenek"
    return s


@pytest.mark.parametrize("metin, alan", [
    ("1 olsun, yükseklik 260 olsun", {}),                                          # LLM alanı yok, istek yalnız sözde
    ("1 olsun, çatı kaplaması kiremit olsun", {"cati": {"kaplama": "kiremit"}}),
    ("1 olsun, çatı eğimi %30 olsun", {}),
    ("1 olsun, mutfak duvarını kaldırın", {}),
    ("1 olsun, banyoya küvet koyalım", {}),
    ("1 olsun, veranda 12 m2 olsun", {"veranda": {"istiyor": True, "alan_m2": 12}}),
])
def test_hakem3_evin_catisi_ve_sozdeki_istek_onay_kaydetmez(tmp_path, metin, alan):
    """Y1 (genel): evin çatısıyla aynı mesajdaki istek Motor'un okuduğu bir alan taşımasa da istektir. Onay kaydedilmez, set açık kalır,
    bayiye isteğin uygulanmadığı ve çatı seçiminin kaydedilmediği yazılır (önce "Onayınız kaydedildi" gidiyordu, istek düşüyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert K.PLAN_ONAYI not in k.gerekce and s.k.d["asama"] == "onay_bekliyor" and not s.k.d.get("onaylanan"), k.mesaj
    assert "isteğinizi plana uygulayamadım" in k.mesaj and "Çatı seçiminizi (PA-06) kaydetmedim" in k.mesaj, k.mesaj
    assert s.k.d.get("cati_adimi") and s.k.d["secenek_seti"]["durum"] == "acik" and s.k.d["taslak"]["alan_m2"] == 85


@pytest.mark.parametrize("metin, alan", [("2 olsun, çatı kaplaması shingle olsun", {"cati": {"kaplama": "shingle"}}),
                                         ("2 olsun, 100 m2 olur mu?", {"niyet": "soru", "alan_m2": 100})])
def test_hakem3_baska_cati_ve_uygulanmayan_istek_yazilir(tmp_path, metin, alan):
    """Y1: başka çatı + uygulanmayan istek (ya da soru): plan yalnız çatıda değişir, istek "Plan aynı; isteğinizi plana uygulayamadım"
    diye yazılır. Soru cümlesindeki m² talebi değiştirmez (bulgu 4)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    _secildi(s, k, "PA06K")
    assert k.mesaj.startswith("Çatı: Kırma (PA-06-K). Plan aynı; isteğinizi plana uygulayamadım."), k.mesaj
    assert s.k.d["taslak"]["alan_m2"] == 85


@pytest.mark.parametrize("metin, alan", [
    ("salon 25 m2 olsun", {"ozel_istekler": ["salon 25 m2 olsun"], "alan_m2": 25}),
    ("1 olsun, veranda 12 m2 olsun", {"veranda": {"istiyor": True, "alan_m2": 12}, "alan_m2": 12}),
    ("2 olsun, yatak odası 15 m2 olsun", {"ozel_istekler": ["yatak odası 15 m2"], "alan_m2": 15}),
    ("1 olsun, arsa 500 m2", {"ozel_istekler": ["arsa 500 m2"], "alan_m2": 500}),
])
def test_hakem3_oda_veranda_arsa_m2_si_evin_m2_si_degil(tmp_path, metin, alan):
    """Bulgu 1: önünde oda, veranda ya da arsa sözü olan m² evin alanı değildir (LLM evin alanı diye okusa da). Plan düşmez, konuşma
    sıfırlanmaz; taslağın m²'si 85 kalır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert "Talebiniz değişti" not in k.mesaj and s.k.d["taslak"]["alan_m2"] == 85 and s.plan["is_emri_no"], k.mesaj


@pytest.mark.parametrize("metin, alan", [("alanı 100 olsun", {"alan_m2": 100}), ("yüz metrekare olsun", {"alan_m2": 100})])
def test_hakem3_birimsiz_m2_sozu_talep_degisikligi(tmp_path, metin, alan):
    """Bulgu 9: birimsiz ya da yazıyla m² (LLM okur, söz destekler) talebin değişikliğidir; sessizce düşmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="revizyon", **alan)
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı. Önce yeni plan seçilir."), k.mesaj
    assert s.k.d["taslak"]["alan_m2"] == 100 and not s.k.d.get("cati_adimi")


def test_hakem3_pencere_olcusu_dis_olcu_degil(tmp_path):
    """Bulgu 8: pencere ölçüsü ("60x40", "1,20x1,20") dış ölçü değildir; LLM'in bağlamdan yinelediği dış ölçü talebi değiştirmez."""
    yanki = {"dis_olcu": {"en_m": 7.5, "boy_m": 11.5}}
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("1 olsun, banyo penceresi 60x40 olsun", pencereler=[pen("banyo", "60x40")], **yanki)
    _secildi(s, k, "PA06")
    assert "BANYO penceresi zaten 60x40" in k.mesaj, k.mesaj
    s, _ = _cati_seti(tmp_path / "b")
    k = s.yaz("mutfak penceresi 1,20x1,20 olsun", pencereler=[pen("mutfak", "120x120")], **yanki)
    assert k.eylem == "sor" and k.soru_alani == "pencere_secim" and "Talebiniz değişti" not in k.mesaj, k.mesaj


def test_hakem3_onceki_revizyonun_notu_onay_kaydettirmez(tmp_path):
    """Bulgu 3: r02'nin çatı setinde "1 olsun, mutfak penceresi 120x120 olsun" (LLM pencere okumadı): önceki revizyonun "zaten" notu bu
    mesajın isteği sayılmaz, onay kaydedilmez."""
    s, _ = _plan(tmp_path)
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.revizyon == 2, k.mesaj
    assert _onayla(s).eylem == "secenek"
    k = s.yaz("1 olsun, mutfak penceresi 120x120 olsun")
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan"), k.mesaj
    assert "isteğinizi plana uygulayamadım" in k.mesaj and "zaten" not in k.mesaj, k.mesaj


def test_hakem3_onay_sozuyle_talep_degisikligi(tmp_path):
    """Bulgu 4: onay sözüyle gelen talep değişikliği de çatı seçiminden önce gelir."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("onaylıyorum, PA-06-K olsun, 3+1 olsun", niyet="onay", oda_programi="3+1")
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı. Çatı seçiminizi (PA-06-K) kaydetmedim."), k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and s.k.d["taslak"]["oda_programi"] == "3+1" and not s.k.d.get("cati_secilen")


@pytest.mark.parametrize("niyet", ["diger", "revizyon", "yeni_talep"])
def test_hakem3_soru_cumlesi_her_niyette_secim_degil(tmp_path, niyet):
    """Bulgu 5: soru cümlesindeki kod her niyette seçim değildir (r02 çizilmez); çatı sorulur."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("PA-06-K nasıl bir çatı?", niyet=niyet)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik", k.mesaj


def test_hakem3_baska_musterinin_talebi(tmp_path):
    """Bulgu 6, 7: başka müşterinin talebi (ad sözde geçiyor, ilk adı farklı) eski planın revizyonu olmaz ve eski müşterinin bilgisini
    taşımaz; bayiye önceki planın onayının kaydedilmediği yazılır."""
    s = _ayse_seti(tmp_path)
    k = s.yaz("Mehmet Deneme için 60 m2 1+1 lazım", niyet="yeni_talep", alan_m2=60, oda_programi="1+1", musteri={"ad": "Mehmet Deneme"},
              ozel_istekler=["mutfak dolapları beyaz olsun"])
    ts = s.k.d["taslak"]
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı."), k.mesaj
    assert ts["musteri"]["ad"] == "Mehmet Deneme" and not ts.get("ozel_istekler"), ts
    s = _ayse_seti(tmp_path / "b")
    no = s.plan["is_emri_no"]
    k = s.yaz("Mehmet Deneme için de aynısından bir tane", niyet="yeni_talep", musteri={"ad": "Mehmet Deneme"}, katalog_kodu="PA-06")
    assert k.mesaj.startswith(f"Önceki planınızın ({no} r01) onayı kaydedilmedi; çatısı seçilmemişti."), k.mesaj
    assert k.revizyon == 1 and not s.k.d.get("onaylanan"), k.mesaj
    s = _ayse_seti(tmp_path / "c")                                              # ad düzeltmesi aynı müşteridir (O5: planın revizyonu)
    k = s.yaz("müşteri adı Ayşe Deneme Yılmaz olsun", niyet="yeni_talep", musteri={"ad": "Ayşe Deneme Yılmaz"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.k.d["taslak"]["ozel_istekler"] == ["mutfak dolapları beyaz olsun"], k.mesaj


@pytest.mark.parametrize("alan", [{"dis_olcu": {"en_m": 7.5, "boy_m": 11.6}}, {"veranda": {"istiyor": True}}, {"yukseklik_cm": 280},
                                  {"cati": {"kaplama": "trapez"}}, {"katalog_kodu": "PA-06", "alan_m2": 87, "oda_programi": "2+1"}])
def test_hakem3_yanki_alanlar_soruyu_bozmaz(tmp_path, alan):
    """Bulgu 10 (O4): "tamam" mesajında LLM'in yinelediği alan (ölçü, veranda, yükseklik, kaplama) istek değildir: çatı sorulur."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("tamam", niyet="yeni_talep", **alan)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.k.d["secenek_seti"]["durum"] == "acik", k.mesaj


def test_hakem3_baska_eve_gecince_onceki_onay_yazilir(tmp_path):
    """Set "Planınız onaylandı (r01)" demişti; bayi başka bir eve geçince onayın kaydedilmediği yazılır."""
    s, _ = _cati_seti(tmp_path)
    no = s.plan["is_emri_no"]
    k = s.yaz("PA-04 olsun", niyet="yeni_talep", katalog_kodu="PA-04")
    assert k.eylem == "is_emri" and k.mesaj.startswith(f"Önceki planınızın ({no} r01) onayı kaydedilmedi; çatısı seçilmemişti."), k.mesaj


# ── İE-42 · geometri hakemi dördüncü tur (15 Kasım 2026 gecesi) ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin, alan", [
    ("1 olsun, yatak odası 1 penceresi 120x120 ve yükseklik 260 olsun", {"pencereler": [pen("yatak odası 1", "120x120")]}),
    ("1 olsun, yatak odaları 120x120 olsun, iç kapılar ahşap olsun",
     {"pencereler": [pen("yatak odası 1", "120x120"), pen("yatak odası 2", "120x120")]}),
])
def test_hakem4_zaten_olan_pencere_ve_baska_istek_onay_kaydetmez(tmp_path, metin, alan):
    """Y-A: planda zaten olan pencere + aynı mesajın başka isteği (aynı cümlede ya da ayrı): istek cümlesi sayısı not sayısıyla değil, her
    cümle notla tümüyle açıklanıyor mu diye kıyaslanır. Onay kaydedilmez; bayiye zaten olan pencere ve öteki isteğin uygulanmadığı yazılır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan"), k.mesaj
    assert "penceresi zaten 120x120; öteki isteğinizi plana uygulayamadım" in k.mesaj and "kaydetmedim" in k.mesaj, k.mesaj


@pytest.mark.parametrize("kod", ["1", "2"])
def test_hakem4_llm_yankisi_pencere_notu_degil(tmp_path, kod):
    """Y-A: LLM'in yinelediği eski pencere ("1 olsun, iç kapılar ahşap olsun" → YATAK ODASI 1 120x120) bayinin sözü değildir: "zaten"
    notu cevaba girmez, onay kaydedilmez, kapı isteği "uygulayamadım" diye yazılır (başka çatıda da)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(f"{kod} olsun, iç kapılar ahşap olsun", pencereler=[pen("yatak odası 1", "120x120")])
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan") and "zaten" not in k.mesaj, k.mesaj
    assert "isteğinizi plana uygulayamadım" in k.mesaj, k.mesaj
    if kod == "2":
        _secildi(s, k, "PA06K")


def test_hakem4_llm_yankisi_pencere_sorusu_acmaz(tmp_path):
    """Y5: sözde pencere yokken LLM'in yinelediği pencere taslağa girmez, "Hangi pencere?" sorusu açılmaz."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("1 olsun, verandayı kaldırın", pencereler=[pen("salon", "120x120")])
    assert k.soru_alani != "pencere_secim" and "pencere" not in k.mesaj.lower() and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, ev 2 katlı olsun", "1 olsun, dubleks olsun", "1 olsun, çelik olsun",
                                   "1 olsun, prefabrik değil çelik olsun"])
def test_hakem4_kat_ve_yapi_sozu_talep_degisikligi(tmp_path, metin):
    """B2: kat ve yapı türü sözü LLM alanı boşken de bayinin sözünden okunur: talep değişti, onay kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin)
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı."), k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan")


@pytest.mark.parametrize("metin", ["PA-06 tek katlı prefabrik, 1 olsun", "1 olsun, 2 katlı olmasın"])
def test_hakem4_evin_kendi_kat_ve_yapi_sozu_talep_degil(tmp_path, metin):
    """B2: evin kendi kat ve yapı sözü ("tek katlı prefabrik") ve olumsuz kat sözü talebi değiştirmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin)
    assert "Talebiniz değişti" not in k.mesaj and s.k.d["taslak"]["alan_m2"] == 85, k.mesaj


@pytest.mark.parametrize("metin, alan", [
    ("1 olsun, 15 m2'lik veranda ekleyin", {"veranda": {"istiyor": True, "alan_m2": 15}, "alan_m2": 15}),
    ("1 olsun, 15 m²'lik teras olsun", {"alan_m2": 15}),
    ("1 olsun, veranda kısmının alanı da 12 m2 olsun", {"alan_m2": 12}),
    ("1 olsun, sundurma 15 m2 olsun", {"alan_m2": 15}),
    ("1 olsun, giriş 12 m2 olsun", {"alan_m2": 12}),
])
def test_hakem4_ekli_ve_uzak_alan_sozu_evin_m2_si_degil(tmp_path, metin, alan):
    """B1: "15 m2'lik veranda", "veranda kısmının alanı da 12 m2", sundurma ve giriş m²'si evin alanı değildir: talep değişmez, onay
    kaydedilmez (istek uygulanmadıysa bayiye yazılır)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert "Talebiniz değişti" not in k.mesaj and K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan"), k.mesaj
    assert s.k.d["taslak"]["alan_m2"] == 85


@pytest.mark.parametrize("metin, alan", [("2 olsun, mutfak 3x4 olsun", {"dis_olcu": {"en_m": 3, "boy_m": 4}}),
                                         ("1 olsun, salonu 5x6 yapın", {"dis_olcu": {"en_m": 5, "boy_m": 6}}),
                                         ("1 olsun, yatak odası 1 3x4 olsun", {})])
def test_hakem4_oda_olcusu_dis_olcu_degil(tmp_path, metin, alan):
    """B8: oda sözüyle gelen ölçü evin dış ölçüsü değildir: talep değişmez, taslak boşalmaz, onay kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert "Talebiniz değişti" not in k.mesaj and "dış ölçü" not in k.mesaj and not s.k.d.get("onaylanan"), k.mesaj
    assert s.k.d["taslak"]["alan_m2"] == 85 and not s.k.d["taslak"].get("dis_olcu"), s.k.d["taslak"]


@pytest.mark.parametrize("metin", ["Mehmet Yılmazın evi için de aynısı lazım", "Mehmet beye de aynısı"])
def test_hakem4_ekli_ad_baska_musteri(tmp_path, metin):
    """B6: ekli ad ("Yılmazın", "beye") da müşterinin adıdır: Ayşe'nin planının revizyonu çizilmez, özel isteği taşınmaz."""
    s = _ayse_seti(tmp_path)
    no = s.plan["is_emri_no"]
    k = s.yaz(metin, niyet="yeni_talep", musteri={"ad": "Mehmet Yılmaz" if "Yılmaz" in metin else "Mehmet Bey"},
              ozel_istekler=["mutfak dolapları beyaz olsun"])
    assert k.eylem != "is_emri" and k.mesaj.startswith(f"Önceki planınızın ({no} r01) onayı kaydedilmedi"), k.mesaj
    assert not s.k.d["taslak"].get("ozel_istekler"), s.k.d["taslak"]


def test_hakem4_baska_musteride_ozel_istek_yankisi_tasinmaz(tmp_path):
    """B7: başka müşterinin talebinde LLM'in yinelediği eski özel istek yeni talebe girmez."""
    s = _ayse_seti(tmp_path)
    s.yaz("Mehmet Deneme için 85 m2 2+1 lazım", niyet="yeni_talep", alan_m2=85, oda_programi="2+1", musteri={"ad": "Mehmet Deneme"},
          ozel_istekler=["mutfak dolapları beyaz olsun"])
    ts = s.k.d["taslak"]
    assert ts["musteri"]["ad"] == "Mehmet Deneme" and not ts.get("ozel_istekler"), ts


@pytest.mark.parametrize("metin", ["1 olsun, onay veriyoruz", "1 olsun, devam edelim", "1 olsun, işleme alın", "1 olsun, saygılar",
                                   "1 olsun, müşteri beğendi", "PA-06'da kalalım", "1 olsun, 85 m²'lik olan", "1 olsun abi",
                                   "1 numaralı çatı olsun hocam", "birinciyi seçiyoruz", "1 olsun saol", "ilk çatı yeterli", "1 yeter",
                                   "1 olsun sağ olun", "1 olsun kolay gelsin", "1'i seçtik, bu şekilde devam", "1 olsun, başka isteğimiz yok",
                                   "evin kendi çatısı olsun", "olduğu gibi kalsın", "1 olsun bu haliyle onaylıyoruz", "1 uygun"])
def test_hakem4_onay_ve_nezaket_sozu_secimdir(tmp_path, metin):
    """O-B, D-D: onay, devam, teşekkür, hitap ve yeterlik sözü istek değildir; ekli sıra sözü ve "evin kendi çatısı" seçimdir: r01 onaylanır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin)
    _secildi(s, k, "PA06")


@pytest.mark.parametrize("metin", ["1 olsun, bir de başka model gönderin", "1 olsun, paravan olur mu?", "1 olsun, 85 değil 95 olsun",
                                   "1 olsun, sağ tarafa kapı", "aynı çatı kalsın, salon büyük olsun", "1 olsun, 2 kat olsun"])
def test_hakem4_istek_ve_soru_onay_kaydetmez(tmp_path, metin):
    """O-C, D-E: "başka model", "paravan" ("para" değil), sayı ve oda isteği seçimle birlikte gelince onay kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan"), k.mesaj


def test_hakem4_fiyat_ve_teslim_sorusu_cevaplanir(tmp_path):
    """D-E: seçimle birlikte gelen fiyat, süre ya da teslim sorusu onayı engellemez ve cevapsız kalmaz."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("1 olsun, teslim ne zaman olur?")
    _secildi(s, k, "PA06")
    assert k.mesaj.endswith("Teklif aşamasına geçiliyor. Fiyat, süre ve teslim bilgisi teklifle gelir."), k.mesaj


def test_hakem4_seti_kapatan_istek_yazilir(tmp_path):
    """Çatı seçimi olmadan gelen ve planı değiştirmeyen istek ("yükseklik 260 olsun") seti kapatır; bayiye uygulanmadığı yazılır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("yükseklik 260 olsun")
    assert k.gerekce == K.PLAN_DEGISMEDI and "değişmedi; isteğinizi plana uygulayamadım. Onaylayabilir" in k.mesaj, k.mesaj


# ── İE-42 · geometri hakemi tur 5 (15 Kasım 2026 gecesi): çatı sözü seçimle çelişmez, istek dar okunur ─────────────────────────────
def _soruldu(s: Sohbet, k):
    """Seçim yok: "Hangi çatı olsun?"; plan r01, set açık, onay kaydedilmedi."""
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert (s.plan["revizyon"], s.k.d["secenek_seti"]["durum"], s.k.d.get("onaylanan")) == (1, "acik", None), k.mesaj
    assert s.k.d.get("cati_adimi") and K.PLAN_ONAYI not in k.gerekce


@pytest.mark.parametrize("metin", ["mevcut çatıdan farklı olsun", "eski çatıdan başka bir çatı olsun", "kendi çatısı farklı olsun",
                                   "evin kendi çatısından farklı bir çatı olsun", "evin kendi çatısı olmasın",
                                   "1 olsun, mevcut çatıdan farklı olsun", "1 olsun, evin kendi çatısı olmasın"])
def test_hakem5_farkli_ve_olumsuz_kendi_cati_secim_degil(tmp_path, metin):
    """Y1: "farklı", "başka" ya da olumsuz sözlü "evin kendi çatısı" evin çatısını seçmez; numarayla birlikte de kararsızlıktır."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin))


@pytest.mark.parametrize("metin", ["1 olsun, kalkan sağ olsun", "1 olsun, çatı sağ olsun", "1 olsun, kalkan sağda olsun"])
def test_hakem5_sag_olsun_yon_sozudur(tmp_path, metin):
    """Y2: "sağ olsun" teşekkür değildir; yön isteği onay kaydettirmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan") and s.plan["revizyon"] == 1, k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, kırmayı alın", "1 olsun, kırmada kalalım", "1 olsun, cumbalı devam edelim",
                                   "1 olsun, müşteri kırmayı beğendi", "1 olsun, K ile devam edelim", "1 olsun, kırma ile devam",
                                   "1 olsun, teklifte K de olsun", "1 olsun, teklifte 2 de olsun", "şimdilik 1 olsun, başka çatıya da bakalım",
                                   "1 olsun, kırma gelsin", "1 olsun, cumba gelsin", "1 olsun, başka çatı modeli de görelim",
                                   "1 olsun, farklı çatı da olsun", "K olsun, kalkan sağ olsun", "2 olsun, cumbalı olsun"])
def test_hakem5_cati_adi_ve_etiket_secimle_celisir(tmp_path, metin):
    """Y3: numarayla seçilen çatı ile aynı mesajdaki başka çatı adı, etiketi, numarası ya da "başka çatı" sözü çelişir: "Hangi çatı olsun?"."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin))


@pytest.mark.parametrize("metin", ["1 olsun, 5 numaralı modele geçelim", "1 olsun, L tipi olsun", "1 olsun, model 6 olsun"])
def test_hakem5_setin_disindaki_numara_ve_harf_istektir(tmp_path, metin):
    """Y3: setin dışındaki numara ("5", "6") ve harf ("L" üç çatılı PA-06'da) dolgu değildir: onay kaydedilmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin, mahal", [
    ("1 olsun, yatak odası 1 penceresi 120x120 olsun ve veranda olsun", "yatak odası 1"),
    ("1 olsun, yatak odası 1 penceresi 120x120 olsun ve bir oda daha olsun", "yatak odası 1"),
    ("1 olsun, yatak odası 1 penceresi 120x120 olsun ve banyo penceresi olsun", "yatak odası 1"),
    ("1 olsun, yatak odası 1 penceresi 120x120 olsun ve mutfak salon olsun", "yatak odası 1"),
    ("1 olsun, yatak odası 1 ve salon penceresi 120x120 olsun", "yatak odası 1"),
    ("1 olsun, yatak odaları 120x120 olsun", "yatak odası 1"),
    ("1 olsun, odaların hepsi 120x120 olsun", "yatak odası 1"),
    ("1 olsun, mutfak penceresi 120x120 olsun", "yatak odası 1"),            # not başka odanın
])
def test_hakem5_zaten_notu_odayla_kiyaslanir(tmp_path, metin, mahal):
    """Y4: "zaten" notu cümleyi ancak cümlenin her sözü notun ölçüsü, pencere sözü, dolgu ya da notun odası ise açıklar: öteki oda, "bir
    oda daha", veranda, çoğul ve "hepsi" sözü onay kaydettirmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, pencereler=[pen(mahal, "120x120")])
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, yatak odası 1 penceresi 120x120 olsun", "1 olsun, yatak odasının penceresi 120x120 olsun abi"])
def test_hakem5_zaten_notu_kendi_odasiyla_onaydir(tmp_path, metin):
    """Y4: notun odasıyla (ekli de) yazılmış zaten olan pencere onayı engellemez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, pencereler=[pen("yatak odası 1", "120x120")])
    _secildi(s, k, "PA06")
    assert "YATAK ODASI 1 penceresi zaten 120x120" in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin, alan, degisen", [
    ("1 olsun ama prefabrik olmasın çelik olsun", {"yapi_turu": "celik"}, ("yapi_turu", "celik")),
    ("prefabrik istemiyoruz çelik olsun", {}, ("yapi_turu", "celik")),
    ("1 olsun, tek katlı olmasın 2 katlı olsun", {}, ("kat_sayisi", 2)),
    ("1 olsun, üstüne 1 kat daha", {}, ("kat_sayisi", 2)),
])
def test_hakem5_olumsuz_soz_sonrasi_talep_degisikligi(tmp_path, metin, alan, degisen):
    """O1: olumsuz söz yalnız kendi yapı ya da kat sözünü olumsuzlar ("prefabrik olmasın çelik olsun" çeliktir); "1 kat daha" kat ekler."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı."), k.mesaj
    assert s.k.d["taslak"][degisen[0]] == degisen[1] and not s.k.d.get("onaylanan"), s.k.d["taslak"]


@pytest.mark.parametrize("metin", ["1 olsun, başka değişiklik yok", "1 olsun, başka yok", "1 olsun başka değişiklik istemiyoruz",
                                   "1 olsun, ayrıca teşekkürler", "1 olsun, son halini onaylıyoruz", "1 olsun, başka çatı istemiyoruz"])
def test_hakem5_baska_degisiklik_yok_istek_degil(tmp_path, metin):
    """O2: "başka değişiklik yok" ve "ayrıca teşekkürler" istek değildir: r01 onaylanır."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin), "PA06")


def test_hakem5_baska_cati_ile_degisiklik_yok_plan_ayni(tmp_path):
    """O2: "K olsun, başka değişiklik yok" r02'yi kırma çatıyla çizer; bayiye "uygulayamadım" yazılmaz."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("K olsun, başka değişiklik yok")
    _secildi(s, k, "PA06K")
    assert "Plan aynı." in k.mesaj and "uygulayamadım" not in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin, alan", [
    ("1 olsun, 15 metrekarelik bir veranda ekleyin", {"veranda": {"istiyor": True, "alan_m2": 15}}),
    ("1 olsun, 15 m2 kadar veranda olsun", {"veranda": {"istiyor": True, "alan_m2": 15}}),
    ("1 olsun, 15 m2 büyüklüğünde veranda olsun", {"veranda": {"istiyor": True, "alan_m2": 15}}),
    ("1 olsun, 15 m2 de veranda olsun", {}),
    ("1 olsun, 12 m2 kapalı teras", {}),
    ("1 olsun, yanına 3x4 kulübe yapalım", {}),
    ("1 olsun, 4x5 sera olsun", {}),
])
def test_hakem5_veranda_ve_ek_yapi_olcusu_evin_degil(tmp_path, metin, alan):
    """O3: m²'den sonraki üç sözcükteki veranda ya da teras, evin yanındaki sera ve kulübe evin alanı ya da dış ölçüsü değildir."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **alan)
    assert "Talebiniz değişti" not in k.mesaj and not s.k.d.get("onaylanan"), k.mesaj
    assert s.k.d["taslak"]["alan_m2"] == 85 and not s.k.d["taslak"].get("dis_olcu"), s.k.d["taslak"]


def test_hakem5_ev_m2_si_yuklemde_durur(tmp_path):
    """O3: "95 m2 olsun, veranda kalsın" evin alanıdır (yüklemden sonraki veranda sözü m²'yi verandaya bağlamaz)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("95 m2 olsun, veranda kalsın", alan_m2=95)
    assert k.mesaj.startswith("Talebiniz değişti"), k.mesaj


@pytest.mark.parametrize("metin, kod", [("K ile devam edelim", "PA06K"), ("K'yı alın", "PA06K"), ("K uygundur", "PA06K"),
                                        ("K'da kalalım", "PA06K"), ("2 ile devam edelim", "PA06K"), ("2 yi alın", "PA06K"),
                                        ("ikinciyle devam", "PA06K"), ("1 ile devam edelim", "PA06"),
                                        ("kendi çatısıyla devam edelim", "PA06")])
def test_hakem5_devam_ve_alma_sozu_secimdir(tmp_path, metin, kod):
    """D1: devam, alma ve kalma sözüyle yazılan etiket, numara ve "kendi çatısı" seçimdir."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin), kod)


def test_hakem5_ad_degistirme_baska_musteri_degil(tmp_path):
    """Müşterinin adını değiştirme sözü ("adını … olarak değiştirin") başka müşterinin talebi değildir: plan adla r02 olur."""
    s = _ayse_seti(tmp_path)
    k = s.yaz("müşterinin adını Zeynep Deneme olarak değiştirin", niyet="diger", musteri={"ad": "Zeynep Deneme"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.k.d["taslak"]["musteri"]["ad"] == "Zeynep Deneme", k.mesaj
    assert s.k.d["taslak"]["ozel_istekler"] == ["mutfak dolapları beyaz olsun"]


# ── İE-42 · geometri hakemi altıncı tur (15 Kasım 2026 gece) ──────────────────────────────────────────────────────────────────────────

_Y2_120x180 = dict(pencereler=[pen("yatak odası 2", "120x180")])


@pytest.mark.parametrize("metin, kod", [
    ("K olsun ama yatak odası 2 penceresi 120x180 olsun", "PA06K"), ("2 olsun yatak odası 2 penceresi 120x180 olsun", "PA06K"),
    ("K olsun yatak odası 2 penceresi 120x180", "PA06K"), ("3 olsun ama yatak odası 2 penceresi 120x180 olsun", "PA06C"),
    ("2 olsun kanka, yatak odası 2 penceresi 120x180 olsun", "PA06K"), ("PA06K yatak odası 2 penceresi 120x180", "PA06K"),
    ("ikinci çatı olsun bir de yatak odası 2 penceresini 120x180 yapalım", "PA06K"),
    ("PA-06-K olsun yatak odası 2 penceresi de 120x180 olsun", "PA06K")])
def test_hakem6_virgulsuz_secim_ve_istek(tmp_path, metin, kod):
    """Y1: seçim cümlesi istek cümlesine virgülsüz bağlanınca da (yüklemden sonra ayrılır) çatı seçilir, istek aynı revizyonda uygulanır:
    virgüllü yazımla aynı. Önce set kapanıyor, r02 evin kendi çatısıyla çiziliyor, çatı sessizce düşüyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **_Y2_120x180)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert k.mesaj.startswith("Çatı: ") and "YATAK ODASI 2 penceresi 120x180" in k.mesaj and "geçersiz kıldı" in k.mesaj, k.mesaj
    k = _onayla(s)                                                    # çatı seçildi: r02'nin onayı kaydedilir, çatı yeniden sorulmaz
    assert k.gerekce == K.PLAN_ONAYI and s.k.d["asama"] == "onaylandi", k.mesaj


@pytest.mark.parametrize("metin", ["çatı 2 yatak odası 2 penceresi 120x180", "2 numaralı çatıyla yatak odası 2 penceresi 120x180 olsun",
                                   "yatak odası 2 penceresi 120x180 K olsun", "kırma çatı olsun ve yatak odası 2 penceresi 120x180 olsun"])
def test_hakem6_istek_cumlesinde_cati_atfi_sorulur(tmp_path, metin):
    """Y1: istek cümlesindeki çatı atfı (çatı sözüne bitişik numara ya da etiket, tek başına etiket harfi, seçenekleri ayıran ad) seçim
    okunmadıysa sorulur; öteki isteğin uygulanmadığı da yazılır (çatı da istek de sessizce düşmez)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **_Y2_120x180)
    _soruldu(s, k)
    assert "Mesajınızdaki öteki isteği uygulamadım" in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin, al", [
    ("2. yatak odası penceresi 120x180 olsun", _Y2_120x180), ("2. yatak odasının penceresi 120x180 olsun", _Y2_120x180),
    ("2. odanın penceresi 120x180 olsun", _Y2_120x180),
    ("1. yatak odası penceresi 120x180 olsun", dict(pencereler=[pen("yatak odası 1", "120x180")])),
    ("3. olarak banyo penceresi 80x120 olsun", dict(pencereler=[pen("banyo", "80x120")]))])
def test_hakem6_oda_sira_sayisi_cati_numarasi_degil(tmp_path, metin, al):
    """Y2: oda ya da sıra sözünden önceki sıra sayısı ("2. yatak odası") çatı numarası değildir. Önce "2." ayrı cümle sayılıyor, bayinin
    seçmediği çatı çizilip onaylanıyordu. Tur 7 (Y1, Y2): "N." numaralı listenin maddesi de olabilir ("1. yatak odası …\n2. mutfak …");
    tur 6'nın birleştirmesi listede yanlış çatı çizdiriyordu. Tek başına "N." ve ardından istek: çatı sorulur, öteki isteğin uygulanmadığı
    yazılır (çalışma kuralı 15: iki okuma varsa biri sessizce seçilmez)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **al)
    _soruldu(s, k)
    assert "Mesajınızdaki öteki isteği uygulamadım" in k.mesaj and not s.k.d.get("cati_secilen"), k.mesaj


def test_hakem6_secimle_gelen_oda_sira_sayisi(tmp_path):
    """Y2: "2 olsun, 1. yatak odası penceresi 120x180": çatı 2, pencere birinci yatak odasının. Tur 7: mesajda ayrı seçim cümlesi varken
    "N." maddenin ya da odanın sıra sayısıdır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("2 olsun, 1. yatak odası penceresi 120x180", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "is_emri" and k.is_emri["talep"]["kaynak"] == "PA06K" and "YATAK ODASI 1 penceresi 120x180" in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin, kod", [("Pa-06K olsun", "PA06K"), ("PA-06K", "PA06K"), ("PA06-K", "PA06K"), ("pa 06k", "PA06K"),
                                        ("pa06 k", "PA06K"), ("PA-06C", "PA06C"), ("pa06-c", "PA06C")])
def test_hakem6_kod_yazimi(tmp_path, metin, kod):
    """O1: setin çatı kodu tire ya da boşlukla yazılınca da seçimdir (gösterimine çevrilir). Önce set kapanıyor, "Planınız değişmedi;
    isteğinizi plana uygulayamadım" gidiyordu."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin), kod)


@pytest.mark.parametrize("metin", ["fark etmez", "farketmez siz seçin", "en ucuzu olsun", "standart olsun", "değiştirmeyin",
                                   "ikisi de olur", "müşteriye soralım sonra döneriz", "tamam bakıp dönüş yapacağız",
                                   "1 olsun, müşteriye soralım"])
def test_hakem6_devir_ve_erteleme_sozu_sorulur(tmp_path, metin):
    """O2: seçimi bize bırakan ve erteleyen söz istek değildir: "Hangi çatı olsun?" (set açık). Erteleyen söz seçimle gelse de onay
    kaydedilmez. Önce set kapanıyor, "isteğinizi plana uygulayamadım" gidiyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    _soruldu(s, k)
    assert "öteki isteği" not in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin, kod", [("2 olsun eline sağlık", "PA06K"), ("2 olsun aga", "PA06K"), ("2 olsun saolasın", "PA06K"),
                                        ("2 olsn", "PA06K"), ("2 olcak", "PA06K"), ("ilk çatı kalsın", "PA06")])
def test_hakem6_whatsapp_yazimi_secimdir(tmp_path, metin, kod):
    """O2: hitap, teşekkür ve yüklemin WhatsApp yazımı seçimi bozmaz."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, niyet="diger"), kod)


def test_hakem6_revizyon_sinirinda_cati_ve_istek(tmp_path):
    """D3: revizyon hakkı dolmuş planda çatıyla gelen öteki istek sınıra takılır (yalnız çatı seçimi takılmaz); çatı seçimi kaydedilmez."""
    s, _ = _plan(tmp_path)
    for i, olcu in enumerate(["120x180", "120x120", "120x180", "120x120"][:K.MAX_REVIZYON]):
        k = s.yaz(f"yatak odası 2 penceresi {olcu} olsun", pencereler=[pen("yatak odası 2", olcu)])
        assert k.eylem == "is_emri" and k.revizyon == i + 2, k.mesaj
    rev = s.plan["revizyon"]
    assert _onayla(s).eylem == "secenek"
    k = s.yaz("2 olsun, yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("yatak odası 1", "120x180")])
    assert k.eylem == "yonlendir" and "revizyon hakkı doldu" in k.mesaj and s.plan["revizyon"] == rev, k.mesaj
    assert not s.k.d.get("onaylanan")


# ── İE-42 · geometri hakemi yedinci tur (15 Kasım 2026 gece) ──────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin", [
    "1. yatak odası penceresi 120x180 olsun\n2. mutfak penceresi 120x120 olsun",
    "1. mutfak penceresi 120x120 olsun\n2. yatak odası penceresi 120x180 olsun",
    "1. yatak odası 2 penceresi 120x180\n2. mutfak tezgahı beyaz", "1. mutfak tezgahı beyaz\n2. yatak odası 2 penceresi 120x180",
    "1. yatak odası 2 penceresi 120x180 olsun\n2. salon kapısı ahşap olsun\n3. banyo fayansı beyaz",
    "2. Yatak odası 1 penceresi 120x180 olsun"])
def test_hakem7_numarali_liste_sorulur(tmp_path, metin):
    """Y1, Y2: numaralı listenin "N." maddesi çatı numarası mı belli değil (mesajda ayrı seçim cümlesi yok): çatı sorulur, öteki isteğin
    uygulanmadığı yazılır. Tur 6'nın birleştirmesiyle bayinin seçmediği çatı r02'de çiziliyor, Onayla'da kaydediliyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **_Y2_120x180)
    _soruldu(s, k)
    assert "Mesajınızdaki öteki isteği uygulamadım" in k.mesaj and not s.k.d.get("cati_secilen"), k.mesaj
    assert _onayla(s).eylem == "sor" and not s.k.d.get("onaylanan")   # Onayla da çatıyı sorar; onay kaydedilmez


@pytest.mark.parametrize("metin, al, kod", [
    ("Çatı 2. Kapılar ahşap olsun", dict(ozel_istekler=["kapılar ahşap"]), "PA06K"),
    ("Seçim 2. Pencereler aynı kalsın", {}, "PA06K"),
    ("Çatı 3. Banyo penceresi 80x120 olsun", dict(pencereler=[pen("banyo", "80x120")]), "PA06C"),
    ("2 olsun. 2. yatak odası penceresi 120x180 olsun", _Y2_120x180, "PA06K"),
    ("Çatı 2 olsun. 2. yatak odasının penceresi 120x180", _Y2_120x180, "PA06K"),
    ("K olsun\n1. yatak odası 2 penceresi 120x180\n2. kapılar ahşap", dict(**_Y2_120x180, ozel_istekler=["kapılar ahşap"]), "PA06K")])
def test_hakem7_secim_cumlesi_ve_numarali_madde(tmp_path, metin, al, kod):
    """Y2: çatı sözüne bitişik "Çatı 2." seçimdir, ardından gelen cümle istektir (tur 6'daki gibi). Mesajda ayrı seçim cümlesi varken
    tek başına "N." maddenin ya da odanın sıra sayısıdır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **al)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod and k.mesaj.startswith("Çatı: "), k.mesaj
    assert s.k.d.get("cati_secilen") == kod


@pytest.mark.parametrize("metin, al", [
    ("3 olsun yatak odası sayısı", dict(oda_programi="3+1")), ("3 olsun oda", dict(oda_programi="3+1")), ("2 olsun banyo", {}),
    ("2 olsun banyo sayısı", {}), ("2 olsun wc", {}), ("2 olacak banyo", {}), ("2 kalsın banyo", {}),
    ("2 olsun pencere sayısı salonda", {}), ("3 olsun yalnız cumba yatak odasının üstünde olsun", {})])
def test_hakem7_devrik_sayi_cumlesi_sorulur(tmp_path, metin, al):
    """Y3: "2 olsun banyo" çatı numarası da oda ya da banyo sayısı da okunur; çatı adlı koşul ("yalnız cumba yatak odasının üstünde")
    seçimi koşula bağlar: bölünmez, sorulur. Tur 6'nın bölmesiyle bayinin seçmediği çatı çiziliyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **al)
    _soruldu(s, k)
    assert not s.k.d.get("cati_secilen"), k.mesaj


@pytest.mark.parametrize("metin, kod", [
    ("yatak odası 2 penceresi 120x180 olsun 2 olsun", "PA06K"), ("yatak odası 2 penceresi 120x180 olsun ikinci çatı olsun", "PA06K"),
    ("yatak odası 2 penceresi 120x180 olsun çatı da 2 olsun", "PA06K"),
    ("yatak odası 2 penceresi 120x180 olsun çatıyı da 2 yapalım", "PA06K"),
    ("yatak odası 2 penceresi 120x180 olsun çatı olarak 2 olsun", "PA06K"),
    ("yatak odası 2 penceresi 120x180 olsun 2 numara olsun", "PA06K"),
    ("yatak odası 2 penceresi 120x180 olsun çatı üçüncü olsun", "PA06C")])
def test_hakem7_istekten_sonra_virgulsuz_secim(tmp_path, metin, kod):
    """Y4: istek önce, seçim sonra ve virgülsüz gelince de çatı seçilir, istek aynı revizyonda uygulanır (virgüllü yazımla aynı). Önce
    set kapanıyor, r02 evin kendi çatısıyla çiziliyor, çatı sessizce düşüyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **_Y2_120x180)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert k.mesaj.startswith("Çatı: ") and "YATAK ODASI 2 penceresi 120x180" in k.mesaj and "geçersiz kıldı" in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin", ["yatak odası 2 penceresi 120x180 olsun çatı ise 2",
                                   "yatak odası 2 penceresi 120x180 olsun çatı tercihimiz 2"])
def test_hakem7_istekten_sonra_okunamayan_secim_sorulur(tmp_path, metin):
    """Y4: istekten sonra gelen ve okunamayan çatı sözü sessizce düşmez: sorulur."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **_Y2_120x180)
    _soruldu(s, k)


@pytest.mark.parametrize("metin", ["1 olsun, daha ucuz olsun", "1 olsun, ikisi de olsun", "1 olsun, ikisi de olur", "en ucuzu olsun",
                                   "Plan aynı kalsın", "plan aynı kalsın teşekkürler", "plan olduğu gibi kalsın"])
def test_hakem7_ucuz_ikisi_ve_plan_ayni_sorulur(tmp_path, metin):
    """O1: ucuzu, pahalıyı ya da ikisini anan söz seçimle çelişir; onay kaydedilmez, sorulur (önce "1 olsun, daha ucuz olsun" r01'i
    onaylıyordu). O2: "plan aynı kalsın" iki türlü okunur ("değişiklik yok" ya da "evin çatısı"): sorulur."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    _soruldu(s, k)


@pytest.mark.parametrize("metin, kod", [("2. sıradaki olsun", "PA06K"), ("2. sıradaki çatı olsun", "PA06K"), ("3. sıradaki çatı", "PA06C"),
                                        ("1. sıradaki kalsın", "PA06"), ("2 olsun, montaj tarihini haber veririz", "PA06K"),
                                        ("evin kendi çatısı olsun", "PA06")])
def test_hakem7_sira_ve_haber_sozu_secimdir(tmp_path, metin, kod):
    """D1: "2. sıradaki olsun" seçimdir (tur 6'nın birleştirmesi soruya çeviriyordu). D2: "haber veririz" tek başına erteleme değildir."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, niyet="diger"), kod)


# ── İE-42 · geometri hakemi sekizinci tur (15 Kasım 2026 gece) ────────────────────────────────────────────────────────────────────────
_Y12_120x180 = dict(pencereler=[pen("yatak odası 1", "120x180"), pen("yatak odası 2", "120x180")])
_LISTE = "1. yatak odası penceresi 120x180 olsun\n2. mutfak penceresi 120x120 olsun"
_LISTE_AL = dict(pencereler=[pen("yatak odası 1", "120x180"), pen("mutfak", "120x120")])


def _set_kapali_r02(s: Sohbet, k):
    """Çatı seçimi yok, istek var: set kapanır, r02 evin kendi çatısıyla (PA06) çizilir, r01 onayı geçersiz kalır, çatı kaydedilmez."""
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj
    assert s.k.d["secenek_seti"]["durum"] == "eskidi" and not s.k.d.get("cati_secilen") and not s.k.d.get("onaylanan"), k.mesaj
    assert "geçersiz kıldı" in k.mesaj and not k.mesaj.startswith("Çatı: "), k.mesaj
    k = _onayla(s)                                       # çatı kaybolmaz: r02'nin onayında çatı yeniden sorulur
    assert k.eylem == "secenek" and k.mesaj.startswith("Planınız onaylandı (r02). Şimdi çatıyı seçin."), k.mesaj


@pytest.mark.parametrize("metin", [
    "yatak odası 1 penceresi 120x180 olsun 2 de", "yatak odası 1 penceresi 120x180 olsun, 2 de",
    "yatak odası 1'in penceresi 120x180 olsun 2'nin de", "yatak odası 1 penceresi 120x180 olsun ikinciye de",
    "yatak odası 1 penceresi 120x180 olsun 2 de olsun", "yatak odası 1 penceresi 120x180 olsun sonuncuya da",
    "yatak odası 1 penceresi 120x180 olsun 2 nolu da", "yatak odası 2 penceresi 120x180 olsun 1 de"])
def test_hakem8_eksiltili_devam_cati_secimi_degil(tmp_path, metin):
    """Y1: istekten sonra gelen eksiltili devam ("… olsun 2 de", "ikinciye de", "2'nin de") isteğin devamıdır: çatı seçmez. Tur 7'de
    bölme "2 de"yi seçim sanıyor, bayinin seçmediği PA-06-K'yi çiziyordu; Onayla onu onaylıyordu."""
    s, _ = _cati_seti(tmp_path)
    _set_kapali_r02(s, s.yaz(metin, **_Y12_120x180))


@pytest.mark.parametrize("metin", ["1 olsun, 2 de olabilir", "2 de olur", "1 olsun 2 de olur"])
def test_hakem8_eksiltili_secim_kararsizdir(tmp_path, metin):
    """Y1: istekten sonra gelmeyen eksiltili numara ("1 olsun, 2 de olabilir") seçimle çelişir ya da karar değildir: sorulur."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin, al", [
    (_LISTE + "\nSon olarak teşekkürler", _LISTE_AL), (_LISTE + "\nSon olarak, teşekkürler", _LISTE_AL),
    (_LISTE + "\nikinci olarak teşekkürler", _LISTE_AL), ("Son haliyle onaylıyoruz", dict(niyet="onay")),
    ("Son haliyle kalsın", {}), ("Son hali güzel", {}), ("son hali uygun", {})])
def test_hakem8_sira_sozu_cati_numarasi_degil(tmp_path, metin, al):
    """Y2, Y3: "son olarak", "son haliyle", "ikinci olarak" sıra sözü değil (sonuncu çatı değil): numaralı listenin kapanışı çatıyı
    seçmez, sorulur. Tur 7'de "Son olarak teşekkürler" PA-06-C'yi çizdiriyor, "Son haliyle onaylıyoruz" PA-06-C r02 açıyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **al)
    _soruldu(s, k)
    assert not s.k.d.get("cati_secilen"), k.mesaj


@pytest.mark.parametrize("metin", ["Son olarak, yatak odası 2 penceresi 120x180 olsun", "İlk olarak, yatak odası 2 penceresi 120x180 olsun",
                                   "Son olarak yatak odası 2 penceresi 120x180 olsun"])
def test_hakem8_son_olarak_istek_cati_secmez(tmp_path, metin):
    """Y2: "Son olarak, …" isteği çatı seçmez (tur 7'de PA-06-C çiziliyordu)."""
    s, _ = _cati_seti(tmp_path)
    _set_kapali_r02(s, s.yaz(metin, **_Y2_120x180))


@pytest.mark.parametrize("metin", ["Şimdilik 1, haber veririz", "1 olsun, haber vereceğiz", "1 olsun ama haber vereceğiz",
                                   "1 olsun, kesinleşince haber vereceğiz", "1 olsun, müşteri karar verince haber vereceğiz",
                                   "Müşteri karar verince haber vereceğiz", "2 olsun, haber vereceğiz"])
def test_hakem8_haber_sozu_ertelemedir(tmp_path, metin):
    """O3: konusu olmayan "haber veririz" kararı erteler: onay kaydedilmez, sorulur. "Montaj tarihini haber veririz" seçimdir (tur 7 D2)."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin, al", [("2 olsun banyo 2 tane", {}), ("2 olsun pencere 2 tane", {}),
                                       ("3 olsun yatak odası 3 tane", dict(oda_programi="3+1")),
                                       ("2 olsun yatak odası 2 tane", dict(oda_programi="2+1"))])
def test_hakem8_devrik_sayi_ve_adet_sorulur(tmp_path, metin, al):
    """Y4: "2 olsun banyo 2 tane" çatı numarası da banyo sayısı da okunur: sorulur; istek sessizce düşmez (tur 7'de PA-06-K çiziliyor,
    "2 olsun pencere 2 tane" BK-29 süzgecinde isteği düşürüyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **al)
    _soruldu(s, k)
    assert "Mesajınızdaki öteki isteği uygulamadım" in k.mesaj, k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, hangisi ucuzsa", "1 olsun, hangisi uygunsa", "1 olsun, hangisi daha ucuzsa o",
                                   "hangisi ucuzsa o olsun", "2 olsun, ikisinden biri", "2 olsun, ikisinin fiyatını da gönderin"])
def test_hakem8_secimi_bize_birakan_soz_sorulur(tmp_path, metin):
    """O4: "hangisi ucuzsa", "ikisinden biri", "ikisinin fiyatını da gönderin" seçimi bize bırakır ya da karar verilmedi: sorulur
    (tur 7'de "1 olsun, hangisi ucuzsa" r01'i onaylıyor, "2 olsun, ikisinin fiyatını da gönderin" PA-06-K çiziyordu)."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin, kod", [("K'da kalalım", "PA06K"), ("Plan aynı kalsın çatı K olsun", "PA06K"),
                                        ("çatı K olsun plan aynı kalsın", "PA06K"), ("plan aynı kalsın 1 olsun", "PA06")])
def test_hakem8_secim_okunur(tmp_path, metin, kod):
    """D1: plan sözü seçim cümlesine virgülsüz bağlansa da çatı seçilir ("Plan aynı kalsın, çatı K olsun" ile aynı); "K'da" eki eksiltili
    "da" değildir."""
    s, _ = _cati_seti(tmp_path)
    _secildi(s, s.yaz(metin, niyet="diger"), kod)


# ── İE-42 · geometri hakemi dokuzuncu tur (15 Kasım 2026 sabaha karşı) ───────────────────────────────────────────────────────────────
_ISTEK_Y2 = "yatak odası 2 penceresi 120x180 olsun, "


@pytest.mark.parametrize("ek", ["çatı 2 de olsun", "çatısı 2 de olsun", "çatı olarak 2 de olur", "çatı 3 de olabilir",
                                "çatı tercihimiz 2 de", "K de olsun", "K da olabilir", "C de olsun", "PA-06-K de olsun", "sonuncu da olur",
                                "çatı K de olsun"])
def test_hakem9_istekten_sonra_eksiltili_cati_sozu_sorulur(tmp_path, ek):
    """Y-1, O-2: istekten sonra gelen eksiltili çatı sözü ("…, çatı 2 de olsun", "…, K da olabilir") çatıya atıftır; seçim mi "o da olur"
    mu belli değil: sorulur, istek uygulanmaz. Tur 8'de rakamlı biçimde çatı sessizce düşüyor, harfli biçimde K seçiliyordu."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(_ISTEK_Y2 + ek, **_Y2_120x180)
    _soruldu(s, k)
    assert "Mesajınızdaki öteki isteği uygulamadım" in k.mesaj and not s.k.d.get("cati_secilen"), k.mesaj


@pytest.mark.parametrize("metin, al", [
    ("Peki 2 olsun banyo 2 tane", {}), ("Ok 2 olsun banyo 2 tane", {}), ("Şimdilik 2 olsun banyo 2 tane", {}),
    ("Bence 2 olsun banyo 2 tane", {}), ("Müşteri 2 olsun dedi banyo 2 tane", {}), ("plan aynı kalsın 2 olsun banyo 2 tane", {}),
    ("2 numara olsun banyo 2 tane", {}), ("Peki 3 olsun yatak odası 3 tane", dict(oda_programi="3+1")), ("Biz de 2 diyoruz", {}),
    ("Müşteri de 2 diyor", {}), ("plan aynı kalsın müşteri 2 diyor", {})])
def test_hakem9_onekli_devrik_sayi_sorulur(tmp_path, metin, al):
    """Y-2: devrik sayı cümlesinin önünde söz olsa da ("Peki 2 olsun banyo 2 tane") ya da sayıdan sonra seçim fiili gelse de ("Biz de 2
    diyoruz") çatı numarası mı oda sayısı mı belli değil: sorulur. Tur 8'de set kapanıyor, çatı sessizce düşüyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, **al))


@pytest.mark.parametrize("metin", ["2 olsun, montaj tarihi ve çatıyı haber veririz", "2 olsun, montaj tarihini ve çatı kararını bildiririz",
                                   "2 olsun, kesin çatıyı ve teslim tarihini haber veririz", "2 olsun, fiyatına göre haber veririz",
                                   "2 olsun, fiyatı gelince haber veririz", "1 olsun, fiyatı öğrenince karar vereceğiz",
                                   "Müşteri karar verecek", "1 olsun, müşteri fiyatı görünce karar verir"])
def test_hakem9_cati_ya_da_kosula_bagli_haber_ertelemedir(tmp_path, metin):
    """Y-3: haberin konusu çatıysa ya da haber bir koşula bağlıysa ("fiyatına göre", "fiyatı gelince") karar ertelenir: sorulur. Tur 8'de
    PA-06-K çiziliyor, Onayla onu kaydediyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin", ["1 olsun, müşteri onaylarsa", "1 olsun, uygunsa", "1 olsun, olursa", "Evin kendi çatısı olsun, müşteri onaylarsa",
                                   "1 olsun müşteri isterse", "1 olsun, müşteri tamam derse", "1 olsun, sorun yoksa",
                                   "1 olsun, müşteri beğenirse onaylarız"])
def test_hakem9_kosullu_soz_onay_degildir(tmp_path, metin):
    """Y-4: koşullu söz ("müşteri onaylarsa", "uygunsa") onay değildir: onay kaydedilmez, sorulur (tur 8'de r01 onaylanıyordu)."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin", ["yatak odalarının ikisinin de penceresi 120x180 olsun", "ikisi de 120x180 olsun",
                                   "yatak odası penceresi ikisi de 120x180 olsun"])
def test_hakem9_istekte_ikisi_pencerelerdir(tmp_path, metin):
    """O-1: ölçülü ya da odalı istekte "ikisi" pencerelerdir: kararsızlık değil; set kapanır, r02 evin çatısıyla (tur 8'de soruluyordu)."""
    s, _ = _cati_seti(tmp_path)
    _set_kapali_r02(s, s.yaz(metin, **_Y12_120x180))


@pytest.mark.parametrize("metin, kod", [("2 olsun, yatak odalarının ikisinin de penceresi 120x180 olsun", "PA06K"),
                                        ("plan olduğu gibi kalsın 2 olsun", "PA06K"), ("2 olsun, bize bildirin", "PA06K"),
                                        ("2 olsun, montaj tarihini haber veririz", "PA06K")])
def test_hakem9_secim_okunur(tmp_path, metin, kod):
    """O-1, D-1: seçimle gelen pencere isteğindeki "ikisi", planı anan "olduğu gibi" ve emir kipindeki "bildirin" seçimi bozmaz."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **(_Y12_120x180 if "pencere" in metin else dict(niyet="diger")))
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


# ── İE-42 · geometri hakemi onuncu tur (15 Kasım 2026 sabaha karşı) ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, müşteri onaylayınca", "1 olsun, müşteri onaylayınca teklif gönderin", "2 olsun, müşteri onaylayınca",
                                   "1 olsun, müşteri daha onaylamadı", "1 olsun, müşteri onaylamadı daha", "1 olsun, müşteri onaylayacak",
                                   "K olsun, müşteri onaylayacak", "1 olsun, müşteri onayladıktan sonra", "1 olsun, müşteri onayından sonra",
                                   "Evin kendi çatısı olsun, müşteri onayından sonra", "2 olsun, müşteri onayından sonra",
                                   "1 olsun, müşteri onayını bekliyoruz", "Evin kendi çatısı olsun, müşteri onayını bekliyoruz",
                                   "1 olsun, müşteriye gönderip onay alalım"])
def test_hakem10_ertelenen_onay_sozu_onay_degildir(tmp_path, metin):
    """Y-1: onay kökü taşıyan ertelenen ya da olumsuz söz ("müşteri onaylayınca", "onayından sonra", "daha onaylamadı", "onaylayacak",
    "onayını bekliyoruz") onay değildir: sorulur. Tur 9'da onay sözü okunmadan silindiği için r01 onaylanıyor ya da çatı çiziliyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin", ["2'yi seçtik banyo 2 tane", "2'yi seçtik banyo 2 tane olsun", "Müşteri 2'yi seçti banyo 2 tane",
                                   "2 numarayı seçtik banyo 2 tane", "Müşteri 2'yi istiyor banyo 2 tane", "Çatıya siz karar verin",
                                   "Siz karar verin", "Çatıyı siz bildirin", "Fiyatları haber verin, ona göre çatıyı seçeriz",
                                   "2 olsun, ikisinin fiyatını da 3 gün içinde gönderin", "2 olsun, ikisinin de 3D görselini gönderin"])
def test_hakem10_secim_sozu_ve_birakma_sorulur(tmp_path, metin):
    """Y-2, O-3, O-4: "2'yi seçtik" (ekli sayı) istekle de çatıya atıftır; çatıyı bize bırakan söz ve "ikisinin fiyatı" (ölçü olmadan
    rakamla da) sorulur. Tur 9'da set kapanıyor ya da PA-06-K çiziliyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))


@pytest.mark.parametrize("metin, kod", [
    ("2 olsun, müşteri Bursa'da", "PA06K"), ("2 olsun, montaj adresi Bursa", "PA06K"), ("K olsun, giriş kapısı terse açılsın", "PA06K"),
    ("2 olsun, sorun varsa arayın", "PA06K"), ("K olsun, veranda ön cephe boyunca olsun", "PA06K"), ("Çatıya gelince, K olsun", "PA06K"),
    ("2 olsun, olabildiğince çabuk gönderin", "PA06K"), ("2 olsun, mümkün olduğunca erken gönderin", "PA06K"),
    ("K olsun, yönetmelik gereğince yapın", "PA06K"), ("2 olsun, kalınca sac kullanın", "PA06K"),
    ("2 olsun, montaj tarihini kesinleşince bildiririz", "PA06K"), ("2 olsun, kesin montaj tarihini bildiririz", "PA06K"),
    ("çatı 2 olsun, pencere 1 olsun", "PA06K"), ("K olsun, kapı 3 olsun", "PA06K"), ("2 olsun, hazır olunca haber verin", "PA06K")])
def test_hakem10_acik_secim_soruya_donmez(tmp_path, metin, kod):
    """O-1, O-2, D-1: koşul ya da zaman bildirmeyen söz ("Bursa", "terse", "boyunca", "olabildiğince", "çatıya gelince"), başka konudaki
    "varsa", montaj tarihinin haberi ve istekteki adet ("pencere 1 olsun") açık seçimi soruya çevirmez (tur 10 kodunda soruluyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


# ── İE-42 · geometri hakemi on birinci tur (15 Kasım 2026 sabaha karşı) ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "2 olsun, müşteri kabul edince", "PA-06-K olsun, müşteri kabul edince", "K olsun, müşteri evet deyince", "3 olsun, kapora yatınca",
    "3 olsun, müşteri tamam deyince", "2 olsun, müşteri imzalayınca", "2 olsun, kredi çıkınca", "2 olsun, banka onayı çıkınca",
    "K olsun, ödeme yapılınca", "2 olsun, avans yatırılınca", "2 olsun, stok varsa", "2 olsun, müşterinin itirazı varsa değiştiririz",
    "2 olsun, fiyat farkı varsa değiştiririz", "2 olsun, müşteri kabul ettikten sonra", "2 olsun, müşteri kabul ettiğinde",
    "2 olsun, müşteri kabul etmeden önce", "2 olsun, müşteri kabul ettiği takdirde", "2 olsun, müşteri kabul etmişse",
    "2 olsun, fiyat makulse", "2 olsun, fiyat düşükse", "PA-06-K mı olsun, müşteri Ayşe Kaya", "2 mi olsun, müşteri Ayşe Kaya",
    "Tamam katalogdaki 3 olsun banyo 2 tane", "katalogtaki 2 numara olsun banyo 2 tane"])
def test_hakem11_kosullu_zamanli_ve_soru_bicimli_secim_sorulur(tmp_path, metin):
    """Y-1, Y-2, Y-3, O-3: zamana ("müşteri kabul edince", "kredi çıkınca", "kabul ettikten sonra") ya da koşula ("stok varsa", "fiyat
    makulse", "kabul etmişse") bağlı seçim, soru biçimli seçim ("PA-06-K mı olsun, müşteri Ayşe Kaya") ve "katalogdaki 3 olsun" + istek
    sorulur. Tur 10 kodunda çoğu başka çatıyı r02 çiziyordu (tek Onayla ile kaydediliyordu) ya da çatı sözü düşüyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))
    _soruldu(s, _onayla(s))                                    # Onayla da seçim değildir: soru yinelenir, onay kaydedilmez


@pytest.mark.parametrize("metin", ["1 olsun, onayımızdır", "1 olsun, onayımdır", "1 olsun, onayımızı veriyoruz", "1 olsun, onaylanmış",
                                   "1 olsun, onaylamak istiyoruz", "1 olsun, onaylayıp gönderiyoruz", "1 olsun, onaylarımızla",
                                   "1 olsun, teklifi bekliyoruz", "Evin kendi çatısı olsun, teklifi bekliyoruz", "1 olsun, teklifinizi bekleriz"])
def test_hakem11_acik_onay_soruya_donmez(tmp_path, metin):
    """O-1, O-2: onay kökünün ertelenmemiş biçimleri onaydır; "teklifi bekliyoruz" müşterinin kararını beklemek değildir (tur 10 kodunda
    soruluyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


@pytest.mark.parametrize("metin, kod", [
    ("2 olsun, müşterinin onayını aldık", "PA06K"), ("2 olsun, yeni çizimi bekliyorum", "PA06K"), ("2 olsun, beklemeden çizin", "PA06K"),
    ("2 olsun, ona göre fiyat verin", "PA06K"), ("2 olsun, buna göre çizin", "PA06K"), ("Çatıya gelince 2 olsun", "PA06K"),
    ("Çatı konusuna gelince 3 olsun", "PA06C"), ("2 olsun, pahalı da olsa", "PA06K"), ("2 olsun, ne olursa olsun", "PA06K")])
def test_hakem11_acik_secim_soruya_donmez(tmp_path, metin, kod):
    """O-2, D-1: "bekliyorum", "ona göre … verin", "çatıya gelince" (söylem sözü, atılır) ve ödünleme ("da olsa", "ne olursa olsun") açık
    seçimi soruya çevirmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


# ── İE-42 × BK-29 tur 9 (main c0a31afb, 15 Kasım 2026): kod ve müşteri adı çatı setinde ───────────────────────────────────────────────
@pytest.mark.parametrize("metin, kod, al", [
    ("PA-06 olsun, müşteri Ayşe Kaya", "PA06", dict(niyet="diger")), ("PA-06-K olsun, müşteri Ayşe Kaya", "PA06K", dict(niyet="diger")),
    ("PA-06, müşteri Ayşe Kaya", "PA06", dict(niyet="onay")),
    ("PA-06-C olsun, müşteri Ayşe Kaya", "PA06C", dict(niyet="yeni_talep", katalog_kodu="PA06C", musteri={"ad": "Ayşe Kaya"}))])
def test_bk29_tur9_kod_ve_musteri_adi_cati_setinde(tmp_path, metin, kod, al):
    """BK-29 tur 9'un kuralı (kod + "müşteri <ad>" o modelin seçimidir, ad müşteri adıdır) çatı setinde de koşar: çatı seçilir, ad plana
    girer, aynı plan r02 çizilir ("r01 onayınızı geçersiz kıldı"). Onay sessizce kaydedilmez, ad düşmez; çatı aynı mesajda seçildiği için
    r02'nin Onayla'sı çatıyı yeniden sormaz."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, **al)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert "geçersiz kıldı" in k.mesaj and not s.k.d.get("onaylanan"), k.mesaj
    assert s.k.d.get("cati_secilen") == kod and (s.k.d["taslak"].get("musteri") or {}).get("ad") == "Ayşe Kaya"
    k = _onayla(s)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 2, k.mesaj


# ── İE-42 · geometri hakemi on ikinci tur (15 Kasım 2026 sabaha karşı) ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "1 olsun, onaylayamadık", "1 olsun, onaylayamayız", "1 olsun, müşteri onaylayamadı", "1 olsun, onaylatmadık", "1 olsun, müşteri onaylatmadı",
    "1 olsun, onaylatamadık", "1 olsun, onaylatamıyoruz", "1 olsun, onaylanamaz", "1 olsun, onaylamak yok", "1 olsun, onaylamak istemiyoruz",
    "Evin kendi çatısı olsun, onaylatmadık", "1 olsun, onay yok", "1 olsun, onayımız yok", "1 olsun, onay daha yok",
    "1 olsun, müşterinin onayı yok", "1 olsun, müşteri onay vermedi", "1 olsun, onay alamadık", "1 olsun, onayı henüz gelmedi",
    "1 olsun, netleşince gönderin", "1 olsun, netleşince işleme alın", "1 olsun, sonra netleşince işleme alın",
    "Evin kendi çatısı olsun, netleşince gönderin", "2 olsun, netleşince gönderin", "3 olsun, avans gelince çizin",
    "2 olsun, kapora yatınca gönderin", "2 olsun, ödeme yapılınca çizin", "2 olsun, sözleşme imzalanınca gönderin",
    "2 olsun, kredi çıkınca gönderin", "2 olsun, stok varsa gönderin", "2 olsun, müşteri onayı varsa çizin", "2 olsun, imkan varsa çizin",
    "1 olsun, itiraz yoksa gönderin", "1 olsun, mümkünse", "PA-06-K olsun, müşteri İsterse"])
def test_hakem12_olumsuz_onay_ve_bagli_secim_sorulur(tmp_path, metin):
    """Y-1, Y-2, Y-3, O-4, O-5: onay kökünün olumsuz biçimi ("onaylayamadık", "onaylatmadık", "onaylanamaz"), onaydan sonra "yok" ya da
    olumsuz fiil ("onay yok", "onaylamak istemiyoruz", "onay vermedi"), emirle biten "netleşince" ve müşterinin ya da paranın zamanı
    ("kapora yatınca gönderin"), sorun sözü olmayan "varsa" + emir ("stok varsa gönderin") sorulur. Tur 11 kodunda çoğu onay diye
    kaydediliyordu ya da başka çatıyı r02 çiziyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger"))
    _soruldu(s, _onayla(s))                                    # Onayla da seçim değildir: soru yinelenir, onay kaydedilmez


@pytest.mark.parametrize("metin, kod, ad", [
    ("PA-06-K olsun, müşteri Nursen Kaya", "PA06K", "Nursen Kaya"), ("PA-06-K olsun, müşteri Ersan Yılmaz", "PA06K", "Ersan Yılmaz"),
    ("PA-06-K olsun müşteri Ersen Kaya", "PA06K", "Ersen Kaya"), ("PA-06-K olsun, müşteri Nurşen Arslan", "PA06K", "Nurşen Arslan")])
def test_hakem12_kod_ve_rsen_adli_musteri_cati_setinde(tmp_path, metin, kod, ad):
    """O-1: "-rsen/-rsan" ile biten müşteri adı ("Nursen", "Ersan") koşul eki değildir: BK-29 tur 9 kuralı çalışır, çatı seçilir, ad
    plana girer, plan r02 (tur 11 kodunda soruluyor, ad "öteki istek" diye düşüyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod and (s.k.d["taslak"].get("musteri") or {}).get("ad") == ad, k.mesaj


@pytest.mark.parametrize("metin, kod, al", [
    ("Neyse, 2 olsun", "PA06K", {}), ("2 olsun, ev Fransa'ya gidecek", "PA06K", {}), ("2 olsun, müşteri Fransa'da", "PA06K", {}),
    ("2 olsun, mümkünse yatak odası 2 penceresi 120x180 olsun", "PA06K", dict(pencereler=[pen("yatak odası 2", "120x180")])),
    ("2 olsun, yatak odası 2 penceresi 120x180 olsun, müşteri Fransa'da", "PA06K", dict(pencereler=[pen("yatak odası 2", "120x180")])),
    ("2 olsun, yatak odası 2 penceresi 120x180 olsun, uzunca olsun", "PA06K", dict(pencereler=[pen("yatak odası 2", "120x180")])),
    ("2 olsun, yatak odası 2 penceresi 120x180 olsun, kapıdan girildiğinde solda kalsın", "PA06K",
     dict(pencereler=[pen("yatak odası 2", "120x180")])),
    ("2 olsun, 2'nin fiyatı ne olacak?", "PA06K", {}), ("K olsun, K'nın fiyatı ne olacak?", "PA06K", {}),
    ("PA-06-K olsun. PA-06-K'nın fiyatı ne kadar olacak?", "PA06K", {}), ("2 olsun. 2 numaranın montajı kaç gün olacak?", "PA06K", {}),
    ("2 olsun, çizim bitince gönderin", "PA06K", {}), ("2 olsun, müsait olunca gönderin", "PA06K", {})])
def test_hakem12_acik_secim_soruya_donmez(tmp_path, metin, kod, al):
    """O-1, O-2, O-3: "Neyse", yer adı ("Fransa"), planın bir yerini anan istekteki koşul ve zaman ("mümkünse yatak odası 2 penceresi …",
    "kapıdan girildiğinde …", "uzunca"), seçilen çatının fiyat ya da süre sorusu ("2'nin fiyatı ne olacak?") ve bizim işimizin zamanı
    ("çizim bitince gönderin") açık seçimi soruya çevirmez (tur 11 kodunda soruluyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger", **al)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


@pytest.mark.parametrize("metin", ["1 olsun, 1'in teslimi ne zaman olacak?", "1 olsun, onaylıyoruz, sorun yok", "1 olsun, onaylıyoruz, değişiklik yok",
                                   "1 olsun, onayımızdır, başka isteğimiz yok", "1 olsun, müşteri onaylamış", "1 olsun, onaylamak istiyoruz"])
def test_hakem12_acik_onay_soruya_donmez(tmp_path, metin):
    """O-2 ve Y-1'in öbür yanı: evin kendi çatısının süre sorusu ve olumlu onay ("onaylamış", "onaylıyoruz, sorun yok") onaydır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi on üçüncü tur (15 Kasım 2026 sabah) ──────────────────────────────────────────────────────────────────────
_Y2 = dict(pencereler=[pen("yatak odası 2", "120x180")])


@pytest.mark.parametrize("metin, al", [
    ("1 olsun, 2'nin çatısı mı olsa?", {}), ("1 olsun, ama 2'nin çatısı mı olsa?", {}), ("1 olsun, 2'nin kırması mı olsa?", {}),
    ("1 olsun, 3'ün çatısı mı olsa?", {}), ("1 olsun, 2'nin mi olsa?", {}), ("1 olsun. 2 numaranın çatısı mı olsun?", {}),
    ("1 olsun, PA-06-K'nın çatısı mı olsa?", {}), ("PA-06 olsun, PA-06-K'nın çatısı mı olsa?", {}), ("2 olsun, 3'ün çatısı mı olsa?", {}),
    ("1 olsun, yoksa 2'nin çatısı mı olsun?", {}), ("PA-06-K'nın çatısı mı olsun, müşteri Ayşe Kaya", {}),
    ("PA-06-K'nın çatısı mı olsun, yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2'nin çatısı mı olsun, yatak odası 2 penceresi 120x180 olsun", _Y2), ("1 olsun, 2'nin fiyatı ne olacak?", {}),
    ("1 olsun, onaylamaktan vazgeçtik", {}), ("1 olsun, onaylamakta tereddüt ediyoruz", {}), ("1 olsun, onaylamaktan çekiniyoruz", {}),
    ("1 olsun, onaylamak için erken", {}), ("1 olsun, onay veremem", {}), ("1 olsun, müşteri onay vermez", {}),
    ("2 olsun, Fiyat Uygunsa", {}), ("1 olsun, Fiyat Uygunsa", {}), ("1 olsun, İtiraz Yoksa", {}), ("1 olsun, müşteri istersen", {}),
    ("2 olsun yatak odası 2 penceresi 120x180 olsun kapora yatınca", _Y2),
    ("2 olsun, kapora yattıktan sonra yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, fiyatı uygunsa yatak odası 2 penceresi 120x180 olsun", _Y2), ("2 olsun, ödeme bitince gönderin", {}),
    ("2 olsun, kapora hazır olunca çizin", {}), ("2 olsun, sözleşme tamamlanınca çizin", {}), ("2 olsun, arsa hazırlanınca gönderin", {}),
    ("2 olsun, inşaat bitince gönderin", {}), ("2 olsun, evraklar hazırlanınca gönderin", {})])
def test_hakem13_ilgi_ekli_secim_sorusu_cekince_ve_bagli_zaman_sorulur(tmp_path, metin, al):
    """Yüksek-1, Yüksek-2, Orta-2, Orta-3, Orta-4: ilgi ekli seçim sorusu ("2'nin çatısı mı olsa?"; ilgi eki yalnız fiyat, teslim, süre,
    montaj sözüyle sorunun konusudur), sorudaki başka çatının fiyatı ("1 olsun, 2'nin fiyatı ne olacak?": 1 mi, fiyata göre 2 mi), çekince
    ("onaylamaktan vazgeçtik", "onay veremem"), büyük harfli koşul ("Fiyat Uygunsa"), plan isteğine bağlanmış para zamanı ve koşulu
    ("… kapora yatınca", "fiyatı uygunsa …") ve işimiz dışındaki zaman ("ödeme bitince", "kapora hazır olunca") sorulur. On ikinci tur
    kodunda çoğu onay kaydediyor ya da sorulan çatıyı çiziyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger", **al))
    _soruldu(s, _onayla(s))                                    # Onayla da seçim değildir: soru yinelenir, onay kaydedilmez


@pytest.mark.parametrize("metin", ["1 olsun, onaylıyoruz başka değişiklik istemiyoruz", "1 olsun, onaylıyoruz, değişiklik istemiyoruz",
                                   "1 olsun, onaylıyoruz değişiklik gerekmiyor", "PA-06 olsun, onaylıyoruz başka değişiklik istemiyoruz",
                                   "Evin kendi çatısı olsun, onaylıyoruz başka değişiklik istemiyoruz", "1 olsun, onaylamaktayız",
                                   "1 olsun, onaylamıştık", "1 olsun, onaylattık"])
def test_hakem13_olumlu_onay_soruya_donmez(tmp_path, metin):
    """Orta-1 ve Yüksek-2'nin öbür yanı: "başka değişiklik istemiyoruz" onayın olumsuzu değildir; "onaylamaktayız", "onaylamıştık" onaydır."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


@pytest.mark.parametrize("metin, kod", [("2 olsun, onaylıyoruz başka değişiklik istemiyoruz", "PA06K"), ("2 olsun, sıra gelince çizin", "PA06K"),
                                        ("2 olsun, PA-06-C'nin fiyatı ne olur?", "PA06K"), ("2 olsun, çizim tamamlanınca gönderin", "PA06K")])
def test_hakem13_acik_secim_soruya_donmez(tmp_path, metin, kod):
    """Orta-1, Düşük: "başka değişiklik istemiyoruz", sıramızın zamanı ve yüklemsiz fiyat sorusu açık seçimi soruya çevirmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


# ── İE-42 · geometri hakemi on dördüncü tur (15 Kasım 2026 sabah) ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin, al", [
    ("1 olsun, emin değiliz", {}), ("2 olsun, kararsızız", {}), ("1 olsun, bilemedik", {}), ("2 olsun, karar veremedik", {}),
    ("1 olsun, bilmiyoruz", {}), ("Evin kendi çatısı olsun, onaydan emin değiliz", {}), ("1 olsun, emin olamadık", {}),
    ("1 olsun, karar vermedik", {}), ("Bilemedim, 1 olsun", {}), ("2 olsun, çatıda değişiklik istemiyoruz", {}),
    ("Çatıda değişiklik istemiyoruz, 2 olsun", {}), ("2 olsun, çatıda değişiklik yok", {}), ("Çatıda değişiklik istemiyoruz", {}),
    ("Çatıda değişiklik gerekmiyor", {}), ("2 olsun, tapu alındığında yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, havale yapıldığında yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, teklif kabul edildiğinde yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, sipariş verildiğinde yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, anlaşma sağlandığında yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, havale gelince yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, stok varsa yatak odası 2 penceresi 120x180 olursa iyi olur", _Y2), ("2 olsun, müşteri onaylarsa iyi olur", {}),
    ("1 olsun, 2'nin rengi ne olacak?", {}), ("1 olsun, 2'ninki mi olsa?", {}), ("1 olsun, onaylamaya hazır değiliz", {}),
    ("1 olsun, onay isteğimize cevap vermediler", {}), ("1 olsun, onay sorunu çözülmedi", {}),
    ("2 olsun, yatak odası penceresi usta gelince 120x180 olsun", _Y2), ("2 olsun, kapora parası yatınca gönderin", {})])
def test_hakem14_kararsizlik_catida_degisiklik_ve_bagli_zaman_sorulur(tmp_path, metin, al):
    """Yüksek-1, Orta-4, Orta-5, Düşük: seçimle gelen kararsızlık sözü ("emin değiliz", "karar veremedik", "kararsızız"), çatıya bağlı
    "değişiklik istemiyoruz" (evin kendi çatısıdır: başka çatıyla çelişir; tek başına sorulur), istekteki işimiz dışındaki zaman ("tapu
    alındığında …", "havale gelince …"), sorudaki başka çatının özelliği ve olumsuz onay ("onaylamaya hazır değiliz") sorulur. On üçüncü
    tur kodunda bir kısmı r02 çiziyor, "Çatıda değişiklik istemiyoruz" seti döngüye sokuyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger", **al))
    _soruldu(s, _onayla(s))                                    # Onayla da seçim değildir: soru yinelenir, onay kaydedilmez


@pytest.mark.parametrize("metin, kod, al", [
    ("2 olsun, yatak odası 2 penceresi 120x180 yapabilirseniz sevinirim", "PA06K", _Y2),
    ("2 olsun, yatak odası 2 penceresi 120x180 olursa iyi olur", "PA06K", _Y2),
    ("2 olsun, yatak odası 2 penceresi 120x180 ederseniz iyi olur", "PA06K", _Y2),
    ("1 olsun, yatak odası 2 penceresi 120x180 yapabilirseniz sevinirim", "PA06", _Y2),
    ("2 olsun, kapıdan girince soldaki yatak odası 2 penceresi 120x180 olsun", "PA06K", _Y2),
    ("2 olsun, salondan geçince sağdaki yatak odası 2 penceresi 120x180 olsun", "PA06K", _Y2),
    ("2 olsun, salona girdikten sonra sağdaki yatak odası 2 penceresi 120x180 olsun", "PA06K", _Y2),
    ("2 olsun, yatak odasına gelince penceresi 120x180 olsun", "PA06K", _Y2),
    ("Çatıya gelince 2, pencereye gelince 120x180 olsun", "PA06K", _Y2),
    ("2 olsun, 2'nin rengi ne olacak?", "PA06K", {}), ("2 olsun, 2'nin eğimi ne olacak?", "PA06K", {}),
    ("2 olsun. 2'nin kaplaması ne olacak?", "PA06K", {}), ("2 olsun, 2'nin de fiyatı ne olacak?", "PA06K", {}),
    ("2 olsun, 2'nin toplam fiyatı ne olacak?", "PA06K", {}), ("Planda değişiklik istemiyoruz, çatı 2 olsun", "PA06K", {}),
    ("2 olsun, mümkünse salona paravan koyun", "PA06K", {}),
    ("2 olsun, yatak odası 1'e gelince penceresi 120x120 olsun", "PA06K", dict(pencereler=[pen("yatak odası 1", "120x120")]))])
def test_hakem14_acik_secim_soruya_donmez(tmp_path, metin, kod, al):
    """Orta-1, Orta-2, Orta-3, Düşük: istekteki nezaket koşulu ("… yapabilirseniz sevinirim"), planın bir yerine giden hareket ("kapıdan
    girince soldaki …"), seçilen çatının özelliğini soran ilgi eki ("2'nin rengi ne olacak?") ve "paravan" açık seçimi soruya çevirmez
    (on üçüncü tur kodunda soruluyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger", **al)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


def test_hakem14_nezaketli_istek_secimsiz_r02(tmp_path):
    """Orta-1: çatı seçimi olmadan gelen nezaketli istek ("… yapabilirseniz sevinirim") soru değildir: r02 evin kendi çatısıyla çizilir."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz("yatak odası 2 penceresi 120x180 yapabilirseniz sevinirim", niyet="diger", **_Y2)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06", k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, 2+1'in fiyatı ne olacak?", "1 olsun, onaylıyoruz sorun yok",
                                   "1 olsun, onaylıyoruz başka değişiklik istemiyoruz"])
def test_hakem14_acik_onay_soruya_donmez(tmp_path, metin):
    """Orta-3: oda programı ("2+1'in fiyatı") çatı numarası değildir; olumsuz fiilden hemen önceki sorun sözü onayı olumsuzlamaz."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi on beşinci tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────
_Y2_ISTEK = "2 olsun, yatak odası 2 penceresi 120x180 olsun "


@pytest.mark.parametrize("metin, al", [
    ("1 olsun. 2 mi daha iyi?", {}), ("1 olsun. 2'nin şekli mi daha iyi?", {}), ("1 olsun. 2'nin mi daha iyi olur?", {}),
    ("1 olsun. 2'nin kırması daha mı güzel?", {}), ("Evin kendi çatısı olsun, kırma mı daha iyi?", {}),
    (_Y2_ISTEK + "hanım beğenirse iyi olur", _Y2), (_Y2_ISTEK + "patron kabul ederse iyi olur", _Y2),
    (_Y2_ISTEK + "ucuz olursa iyi olur", _Y2), (_Y2_ISTEK + "havale gelirse iyi olur", _Y2),
    (_Y2_ISTEK + "tutar uygun çıkarsa sevinirim", _Y2), (_Y2_ISTEK + "paraya sıkışmazsak iyi olur", _Y2),
    ("2 olsun, usta eve gelince yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, eve dönünce yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, kapılar gelince yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, mutfakçıyla görüşünce yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, yatak odası 2 penceresi ölçü gelince 120x180 olsun", _Y2),
    ("2 olsun, salona bakınca söyleriz yatak odası 2 penceresi 120x180 olsun", _Y2),
    ("2 olsun, yatak odası 2 penceresi paranın gelmesine göre 120x180 olsun", _Y2), ("2 olsun, fiyata göre", {}),
    ("2 olsun, çatıda kararsızız", {})])
def test_hakem15_karsilastirma_sorusu_kosullu_ve_zamanli_secim_sorulur(tmp_path, metin, al):
    """Y-1, O-1, O-2, O-6: çatıları kıyaslayan soru ("1 olsun. 2 mi daha iyi?"), isteğin fiili olmayan nezaketli koşul ("hanım beğenirse
    iyi olur", "ucuz olursa iyi olur"), yön eki almış oda ya da kapı olmadan hareket zamanı ("usta eve gelince", "kapılar gelince") ve
    "-e göre" bağı ("paranın gelmesine göre") sorulur. On dördüncü tur kodunda kıyas sorusu onay kaydediyor, öteki r02 çiziyordu."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger", **al))
    _soruldu(s, _onayla(s))                                    # Onayla da seçim değildir: soru yinelenir, onay kaydedilmez


@pytest.mark.parametrize("metin, kod, al", [
    ("2 olsun, kararımız değişmez", "PA06K", {}), ("2 olsun, kararımızdan dönmeyiz", "PA06K", {}), ("Kararsızlık yok, 2 olsun", "PA06K", {}),
    ("2 olsun, iç kapı modelinde kararsızız", "PA06K", {}),
    ("2 olsun, yatak odası 2 penceresi 120x180 yapabilirseniz sevinirim", "PA06K", _Y2),
    ("2 olsun, kapıdan girildiğinde soldaki yatak odası 2 penceresi 120x180 olsun", "PA06K", _Y2)])
def test_hakem15_acik_secim_soruya_donmez(tmp_path, metin, kod, al):
    """O-5 ve O-1, O-2'nin öbür yanı: kesin karar ("kararımız değişmez"), başka konunun kararsızlığı ve isteğin kendi fiiliyle nezaket ya
    da yön ekli yerin zamanı açık seçimi soruya çevirmez."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger", **al)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == kod, k.mesaj
    assert s.k.d.get("cati_secilen") == kod


@pytest.mark.parametrize("metin", ["1 olsun, çatıda değişiklik istemiyoruz", "PA-06 olsun, çatıda değişiklik istemiyoruz",
                                   "Evin kendi çatısı olsun, çatıda değişiklik istemiyoruz",
                                   "Çatıda değişiklik istemiyoruz, evin kendi çatısı olsun", "1 olsun, onaylıyoruz başka söyleyeceğimiz yok",
                                   "1 olsun, onaylıyoruz başka diyeceğimiz yok", "1 olsun, 2 + 1'in fiyatı ne olacak?"])
def test_hakem15_acik_onay_soruya_donmez(tmp_path, metin):
    """O-3, O-4, D-2: evin çatısıyla gelen "çatıda değişiklik istemiyoruz", araya söz giren "başka söyleyeceğimiz yok" ve boşluklu oda
    programı ("2 + 1'in") onaydır (on dördüncü tur kodunda soruluyordu)."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


@pytest.mark.parametrize("metin", [
    "2 olsun, eve girince soldaki yatak odası 2 penceresi 120x180 olsun",
    "2 olsun, içeri girince sağdaki yatak odası 2 penceresi 120x180 olsun",
    "2 olsun, salona oturunca karşıdaki yatak odası 2 penceresi 120x180 olsun",
    "2 olsun, salondan bakınca soldaki yatak odası 2 penceresi 120x180 olsun",
    "2 olsun, yatak odası 2 penceresi 120x180 olursa çok iyi olur",
    "2 olsun, yatak odası 2 penceresi 120x180 yaparsanız çok sevinirim",
    "2 olsun, yatak odası 2 penceresi 120x180 yapabilirseniz bizi memnun edersiniz"])
def test_hakem16_konum_betimi_ve_pekistirmeli_rica_r02(tmp_path, metin):
    """Tur 16 (on beşinci tur düzeltmesinin taramasında): zaman sözünün hemen ardından konum sözü ve oda ("eve girince soldaki yatak
    odası") yerin betimidir; isteğin fiiliyle nezaket arasındaki pekiştirme ("olursa çok iyi olur", "yapabilirseniz bizi memnun
    edersiniz") ricadır. İkisi de açık seçimdir: r02 çizilir."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger", **_Y2)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06K", k.mesaj
    assert s.k.d.get("cati_secilen") == "PA06K"


@pytest.mark.parametrize("metin", [
    "2 olsun, usta gelince soldaki yatak odası 2 penceresi 120x180 olsun",
    "2 olsun, eve gelince yatak odası 2 penceresi 120x180 olsun",
    "2 olsun, yatak odası 2 penceresi 120x180 olsun hanım beğenirse çok sevinirim",
    "2 olsun, yatak odası 2 penceresi 120x180 olsun ucuz olursa çok iyi olur"])
def test_hakem16_kisinin_zamani_ve_kosulu_sorulur(tmp_path, metin):
    """Tur 16'nın öbür yanı: konum sözü yer olmayan sözün ("usta gelince") zamanını betim yapmaz; pekiştirme isteğin fiili olmayan
    koşulu ("hanım beğenirse çok sevinirim", "ucuz olursa çok iyi olur") rica yapmaz. Seçim sorulur."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger", **_Y2))


# ── İE-42 · geometri hakemi on altıncı tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────
_Y2_ = "2 olsun, {} yatak odası 2 penceresi 120x180 olsun"


@pytest.mark.parametrize("metin, al", [
    ("1 olsun, hangisi daha iyi?", {}), ("1 olsun, ikincisi daha mı iyi?", {}), ("1 olsun, sonuncusu daha mı iyi?", {}),
    ("2 olsun, hangisi daha iyi?", {}), ("1 olsun, karar yok", {}), ("1 olsun, son karar müşterinin", {}),
    ("1 olsun, karar müşteride", {}), ("2 olsun, son karar müşterinin", {}), ("2 olsun, mutfak tamam ama kararsızız", {}),
    ("Odalar güzel ama kararsızız, 2 olsun", {}), (_Y2_.format("usta eve gelince soldaki"), _Y2),
    (_Y2_.format("akşam eve gelince soldaki"), _Y2), (_Y2_.format("Hollanda'dan dönünce"), _Y2), (_Y2_.format("kapıcıya gelince"), _Y2),
    ("2 olsun, yatak odası 2 penceresi 120x180 olmazsa iyi olur", _Y2),
    ("2 olsun, yatak odası 2 penceresi 120x180 yaparsanız memnun olmayız", _Y2), ("2 olsun, müşterinin cevabına göre", {}),
    ("2 olsun, bütçeye bağlı", {}), ("2 olsun, duruma bakarak", {}), ("2 olsun, kaporanın yatmasına bağlı", {})])
def test_hakem16_kiyas_karar_sahibi_ve_kosul_sorulur(tmp_path, metin, al):
    """Y-A, Y-B (önceden var): "hangisi daha iyi?", sıra sözüyle kıyas ("ikincisi daha mı iyi?"), "karar yok", "son karar müşterinin"
    onay ya da çatı kaydediyordu. O-D (gerileme): yer sözünden sonraki kararsızlık ("mutfak tamam ama kararsızız") r02 çizdiriyordu.
    O-E, O-G, O-H, O-I (önceden var ya da gerileme): öznenin zamanı ("usta eve gelince soldaki"), yer olmayan söz ("Hollanda'dan",
    "kapıcıya"), olumsuz nezaket ("olmazsa iyi olur", "memnun olmayız") ve "-e göre/bağlı/bakarak" bağı. Seçim sorulur."""
    s, _ = _cati_seti(tmp_path)
    _soruldu(s, s.yaz(metin, niyet="diger", **al))


@pytest.mark.parametrize("metin, al", [
    ("2 olsun, teslim 3 hafta mı?", {}), ("2 olsun, 2'nin rengi mi olacak?", {}),
    ("2 olsun, kapıdan girince soldaki yatak odası 2 penceresini 120x180 istiyoruz", _Y2),
    ("2 olsun, kapıdan girince soldaki yatak odası 2 penceresi 120x180 olsun teşekkür ederiz", _Y2),
    ("2 olsun, yatak odasına girince penceresini 120x180 istiyorum", _Y2), (_Y2_.format("dışarıdan bakınca sağdaki"), _Y2),
    (_Y2_.format("içeriden bakınca sağdaki"), _Y2), ("2 olsun, fiyata göre en uygunu bu", {})])
def test_hakem16_acik_secim_soruya_donmez(tmp_path, metin, al):
    """O-A, O-B, O-C, O-F (gerileme): birimli sayı ("teslim 3 hafta mı?"), yüklemli soruda seçilen çatının ilgi eki, isteğin birinci
    kişi fiili ("istiyoruz", "teşekkür ederiz"), "dışarıdan bakınca" ve değer sözlü "göre" açık seçimi soruya çevirmez: r02."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger", **al)
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["talep"]["kaynak"] == "PA06K", k.mesaj
    assert s.k.d.get("cati_secilen") == "PA06K"


@pytest.mark.parametrize("metin", ["1 olsun, teslim 3 hafta mı?", "1 olsun. Teslim 2 haftada mı?", "Evin kendi çatısı olsun, teslim 3 hafta mı?"])
def test_hakem16_acik_onay_soruya_donmez(tmp_path, metin):
    """O-A (gerileme): teslim süresi sorusundaki sayı setin numarası değildir; evin çatısı r01'i onaylar."""
    s, _ = _cati_seti(tmp_path)
    k = s.yaz(metin, niyet="diger")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj
