"""İE-25 · yeni planın çatısı plan seçildikten sonra (pano 41; Lokman, 1 Kasım 2026 karar kartı "Plan seçildikten sonra").

Karar katmanı: LLM yok, Postgres yok, çizim yok. Talep elle kurulur (kayıtlı okuma gibi), plan gerçek üreticiyle kör üretilir
(`plan_uretici.uret`, LLM kapalı; worker'ın yaptığı gibi `plan_sonucu`na verilir), düğmeler `kanal/etkilesim.coz`'dan geçer.
A1 çatısız talep → plan üretimi (çatı sorulmaz); A2 yeni plan seçimi → "Çatı seçin" (1. Beşik 2. Kırma); A3 düğme, numara ya da
"kırma olsun" → r01 o çatıyla; A4 çatı altında veranda → set yok, kırma ve nedeni; A5 talepte çatı → set yok; A6 çizilmeyen çatı →
set başında söylenir; A7 revizyon bugünkü gibi. Kanal (kartlar, kayıt) `testler/kalici/test_plan_akisi.py`'de.
"""
from __future__ import annotations

import copy
import json
import sys
from functools import lru_cache
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import celik, celik_okuma as CO, karar as K, plan_uretici as PU, secenek as SC  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.sema import Talep  # noqa: E402
from kanal import etkilesim as ET  # noqa: E402

BAYI = {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi", "numara": "900000000101"}
TALEP = {"alan_m2": 95, "oda_programi": "3+1", "yapi_turu": "celik", "kat_sayisi": 1}


@lru_cache(maxsize=None)
def _uretim(talep_json: str) -> str:
    return json.dumps(PU.uret(json.loads(talep_json), ayar={"acik": False}), ensure_ascii=False)


class Sohbet:
    """Bir bayinin konuşması: yazı (`yaz`) ya da düğme (`dugme`); plan üretimi istenirse worker'ın yaptığı gibi kör üretilir."""

    def __init__(self, kok: Path):
        self.k = Konusma("900000000101", kok=kok)
        self.kat = Katalog(kabul_edilmis=None)
        self.n = 0

    def _hazirla(self):
        self.n += 1
        self.k.son_mesaj_id = f"wamid.CATI{self.n:03d}"
        self.k.plan_uretimi = True

    def _uret(self, r):
        if r.gerekce == K.PLAN_URETIMI and self.k.d.get("plan_istegi"):
            pu = json.loads(_uretim(json.dumps(self.k.d["plan_istegi"]["talep"], sort_keys=True)))
            return K.plan_sonucu(self.k, self.kat, pu, [None, None]), True
        return r, False

    def yaz(self, metin: str, uret: bool = True, **alan):
        self._hazirla()
        alan.setdefault("niyet", "revizyon" if self.k.d.get("son_is_emri") else "yeni_talep")
        t = Talep(guven="yuksek", ozet=alan.pop("ozet", metin[:80]), **alan)
        r = K.karar_ver(t, self.k, BAYI, self.kat, metin)
        return self._uret(r)[0] if uret else r

    def dugme(self, kod: str):
        self._hazirla()
        st = self.k.d.get("secenek_seti") or {}
        etk = ET.coz({"reply_id": f"s:{st.get('id')}:{kod}", "type": "interactive"}, self.k.d)
        assert etk.get("gecerli"), etk
        return K.karar_ver(Talep.model_validate(etk["talep"]), self.k, BAYI, self.kat, etk["metin"])

    @property
    def set(self) -> dict:
        return self.k.d.get("secenek_seti") or {}

    @property
    def yeni(self) -> str:
        return next(a["kod"] for a in self.set["adaylar"] if a.get("durum") == "uretilen")


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path)


def cati_seti(s: Sohbet, mesaj: str = "95 m² 3+1 tek kat çelik", **alan):
    """A1 + A2: çatısız talep → yeni plan seti → yeni plan seçilir → çatı seti."""
    r = s.yaz(mesaj, **{**TALEP, **alan})
    assert r.eylem == "secenek" and s.set["tur"] == "yeni_plan", r
    yeni = s.yeni
    r = s.dugme(yeni)
    return r, yeni


# ── A1, A2 ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a1_catisiz_talep_cati_sorulmaz_plan_uretilir(s):
    r = s.yaz("95 m² 3+1 tek kat çelik", uret=False, **TALEP)
    assert r.eylem == "cevapla" and r.gerekce == K.PLAN_URETIMI and "çatı" not in r.mesaj.lower()
    assert s.k.d["plan_istegi"]["talep"]["cati"]["tip"] is None


def test_a2_yeni_plan_secilince_cati_seti(s):
    r, yeni = cati_seti(s)
    assert r.eylem == "secenek" and r.soru_alani == "secenek", r
    st = s.set
    assert st["tur"] == "cati_secimi" and st["durum"] == "acik"
    assert [a["kod"] for a in st["adaylar"]] == [f"{yeni}-B", f"{yeni}-K"]
    assert [b["baslik"] for b in r.butonlar] == ["1. Beşik", "2. Kırma"]
    assert [b["id"] for b in r.butonlar] == [f"s:{st['id']}:{yeni}-B", f"s:{st['id']}:{yeni}-K"]
    assert r.mesaj.startswith("Yeni plan için 2 çatı seçeneği. Plan ikisinde aynı (95 m², 3+1); fark çatıda.")
    assert "1. Beşik\n2. Kırma" in r.mesaj and "kırma olsun" in r.mesaj and "YENI-" not in r.mesaj
    assert all(a["tanim"] is None and a["motor"] == "genel" for a in st["adaylar"])          # set kaydı tanım taşımaz; konuşmada
    cs = s.k.d["cati_secenekleri"]
    assert cs["plan_kodu"] == yeni
    for v, tip in zip(cs["adaylar"], ("besik", "kirma")):
        assert v["cati_tipi"] == tip and v["tanim"]["kod"] == yeni and v["tanim"]["cati"]["tip"] == tip
        assert v["plan"]["cati"]["tip"] == tip and celik.tanim_dogrula(v)
        assert (v["sunum"] or {}).get("cati_adi", "").startswith(K.CATI_SOZU[tip])
    eski = s.k.d["eski_setler"][-1]                                                        # yeni plan seti planın seçimiyle kapandı
    assert eski["tur"] == "yeni_plan" and eski["durum"] == "secildi" and eski["secilen_kod"] == yeni
    assert s.k.d["taslak"]["katalog_kodu"] == yeni and s.k.d["uretilen_plan"]["kod"] == yeni
    assert not s.k.d.get("son_is_emri")                                                     # henüz plan çizilmedi


# ── A3 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _r01(s: Sohbet, r, yeni: str, tip: str):
    assert r.eylem == "is_emri" and r.revizyon == 1, r
    y = r.is_emri["yapi"]
    assert y["kod"] == yeni and y["gosterim"] == "Yeni plan" and y["sistem"] == "celik"                 # planın kendi kodu
    assert y["tanim"]["kod"] == yeni and y["tanim"]["cati"]["tip"] == tip and celik.tanim_dogrula(y)
    assert f"Yeni plan ({K.CATI_SOZU[tip]}" in r.mesaj and "YENI-" not in r.mesaj
    assert s.set["durum"] == "secildi" and s.set["secilen_kod"] == f"{yeni}-{K.CATI_EKI[tip]}"
    assert "cati_secenekleri" not in s.k.d and s.k.d["taslak"]["katalog_kodu"] == yeni
    assert s.k.d["uretilen_plan"]["kod"] == yeni and s.k.d["uretilen_plan"]["plan"]["cati"]["tip"] == tip      # revizyon bu plandan sürer
    assert s.k.d["taslak"]["cati"]["tip"] == tip


@pytest.mark.parametrize("tip", ["besik", "kirma"])
def test_a3_dugmeyle_secim_r01(s, tip):
    _, yeni = cati_seti(s)
    _r01(s, s.dugme(f"{yeni}-{K.CATI_EKI[tip]}"), yeni, tip)


@pytest.mark.parametrize("metin,tip", [("2", "kirma"), ("1", "besik"), ("kırma olsun", "kirma"), ("Beşik çatı yapalım lütfen", "besik"),
                                       ("çatı kırmalı olsun, başka değişiklik yok", "kirma")])
def test_a3_numara_ya_da_soz_ile_secim(s, metin, tip):
    _, yeni = cati_seti(s)
    _r01(s, s.yaz(metin), yeni, tip)


def test_a3_llm_cati_degisikligi_varyanti_yonlendirmez(s):
    """Bayi "kırma olsun" yazınca LLM çatıyı değişiklik (cati_degistir) diye de okuyabilir: çatıyı kod seçti, istek düşmez ve
    "otomatik yapılamıyor" denmez."""
    _, yeni = cati_seti(s)
    r = s.yaz("kırma olsun", cati={"tip": "kirma"}, varyantlar=[{"tur": "cati_degistir", "aciklama": "çatı kırma", "parametreler": {"tip": "kirma"}}])
    _r01(s, r, yeni, "kirma")
    assert "uygulayamadım" not in r.mesaj


@pytest.mark.parametrize("metin", ["kırma olmasın", "beşik mi kırma mı?", "kırmaya gerek yok", "beşik değil kırma", "kırma olur mu?",
                                   "tamam"])
def test_a3_secim_olmayan_mesaj_seti_yeniden_sunar(s, metin):
    _, yeni = cati_seti(s)
    ilk = s.set["id"]
    r = s.yaz(metin)
    assert r.eylem == "secenek" and s.set["tur"] == "cati_secimi" and s.set["id"] != ilk, r
    assert [a["kod"] for a in s.set["adaylar"]] == [f"{yeni}-B", f"{yeni}-K"]
    assert "Önce çatıyı seçin (numara ya da düğme)." in r.mesaj and not s.k.d.get("son_is_emri")
    assert s.k.d["eski_setler"][-1]["id"] == ilk and s.k.d["eski_setler"][-1]["durum"] == "eskidi"


def test_a3_set_acikken_yazilan_istek_secilen_catiya_islenir(s):
    _, yeni = cati_seti(s)
    r = s.yaz("dış duvarlar 140 olsun")
    assert r.eylem == "secenek" and K.CELIK_ISTEK_NOTU in r.mesaj
    r = s.dugme(f"{yeni}-K")
    _r01(s, r, yeni, "kirma")
    assert [d["op"] for d in r.is_emri["yapi"]["degisiklikler"]] == ["dis_karkas_140"]


def test_a3_eski_cati_dugmesi_secimden_sonra(s):
    _, yeni = cati_seti(s)
    st = dict(s.set)
    s.dugme(f"{yeni}-K")
    etk = ET.coz({"reply_id": f"s:{st['id']}:{yeni}-B", "type": "interactive"}, s.k.d)
    assert not etk["gecerli"] and etk["neden"] == "set zaten seçilmiş" and "Kırma zaten seçildi" in etk["mesaj"] and "YENI-" not in etk["mesaj"]


# ── A4, A5, A6 ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a4_cati_altinda_veranda_set_yok_kirma_ve_nedeni(s):
    r = s.yaz("95 m² 3+1 tek kat çelik, ön verandalı", **TALEP, veranda={"istiyor": True, "konum": "on"})
    assert r.eylem == "secenek" and s.set["tur"] == "yeni_plan"
    yeni = s.yeni
    r = s.dugme(yeni)
    assert r.eylem == "is_emri" and r.is_emri["yapi"]["tanim"]["cati"]["tip"] == "kirma", r
    assert r.mesaj.startswith("Veranda çatı altında olduğu için beşik çatı bu planda kurallara uymuyor; plan kırma çatıyla çizildi. ")
    assert s.set["tur"] == "yeni_plan" and s.set["durum"] == "secildi" and s.set["secilen_kod"] == yeni


@pytest.mark.parametrize("tip", ["kirma", "besik"])
def test_a5_talepte_cati_varsa_set_sunulmaz(s, tip):
    r = s.yaz(f"95 m² 3+1 tek kat çelik, {K.CATI_SOZU[tip]} çatı", **TALEP, cati={"tip": tip})
    assert r.eylem == "secenek" and s.set["tur"] == "yeni_plan"
    yeni = s.yeni
    r = s.dugme(yeni)
    assert r.eylem == "is_emri" and r.is_emri["yapi"]["tanim"]["cati"]["tip"] == tip and r.is_emri["yapi"]["kod"] == yeni, r
    assert "kurallara uymuyor" not in r.mesaj


def test_a5_secim_mesajinda_yazilan_cati_plana_islenir(s):
    """Plan çatısız üretildi (beşik); bayi seçerken "kırma" da yazdı: set sunulmaz, plan kırmayla kurulur (kod denetler)."""
    s.yaz("95 m² 3+1 tek kat çelik", **TALEP)
    yeni = s.yeni
    r = s.yaz("yeni planı seçiyorum, kırma çatı olsun", katalog_kodu=yeni, cati={"tip": "kirma"})
    assert r.eylem == "is_emri" and r.is_emri["yapi"]["tanim"]["cati"]["tip"] == "kirma" and r.is_emri["yapi"]["kod"] == yeni, r
    assert "uygulayamadım" not in r.mesaj


def test_a5_yazilan_cati_kurallara_uymazsa_soylenir(s):
    """Veranda çatı altında (kırma çizildi), bayi seçerken beşik yazdı: beşik geçmez, plan kırmayla ve nedeni yazılarak (sessiz düşmez)."""
    s.yaz("95 m² 3+1 tek kat çelik, ön verandalı", **TALEP, veranda={"istiyor": True, "konum": "on"})
    yeni = s.yeni
    r = s.yaz("yeni plan olsun, beşik çatı", katalog_kodu=yeni, cati={"tip": "besik"})
    assert r.eylem == "is_emri" and r.is_emri["yapi"]["tanim"]["cati"]["tip"] == "kirma", r
    assert r.mesaj.startswith("Veranda çatı altında olduğu için beşik çatı bu planda kurallara uymuyor; plan kırma çatıyla çizildi. ")


@pytest.mark.parametrize("tip,soz", [("tek_egimli", "Tek eğimli"), ("teras", "Teras")])
def test_a6_cizilmeyen_cati_set_basinda_soylenir(s, tip, soz):
    r, yeni = cati_seti(s, f"95 m² 3+1 tek kat çelik, {soz.lower()} çatı", cati={"tip": tip})
    assert r.eylem == "secenek" and s.set["tur"] == "cati_secimi", r
    assert r.mesaj.startswith(f"{soz} çatı bu sürümde çizilmiyor; beşik ya da kırma seçin. Yeni plan için 2 çatı seçeneği.")
    _r01(s, s.dugme(f"{yeni}-B"), yeni, "besik")


# ── A7 ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a7_revizyon_ayni_plan_cati_korunur(s):
    _, yeni = cati_seti(s)
    s.dugme(f"{yeni}-K")
    r = s.yaz("dışlar 140 olsun")
    assert r.eylem == "is_emri" and r.revizyon == 2 and r.is_emri["yapi"]["kod"] == yeni, r
    assert r.is_emri["yapi"]["tanim"]["cati"]["tip"] == "kirma" and s.set["tur"] == "cati_secimi" and s.set["durum"] == "secildi"
    assert [d["op"] for d in r.is_emri["yapi"]["degisiklikler"]] == ["dis_karkas_140"]


def test_ikinci_yeni_plan_secilirse_cati_seti_onun_icin(s):
    s.yaz("95 m² 3+1 tek kat çelik", **TALEP)
    ikinci = [a["kod"] for a in s.set["adaylar"] if a.get("durum") == "uretilen"][1]
    r = s.dugme(ikinci)
    assert r.eylem == "secenek" and [a["kod"] for a in s.set["adaylar"]] == [f"{ikinci}-B", f"{ikinci}-K"]
    assert r.mesaj.startswith("Yeni plan 2 için 2 çatı seçeneği.")
    _r01_kod = s.dugme(f"{ikinci}-K")
    assert _r01_kod.is_emri["yapi"]["kod"] == ikinci and _r01_kod.is_emri["yapi"]["gosterim"] == "Yeni plan 2"


def test_banka_modeli_cati_adimi_degismez(s):
    """Ç8801 (çatı varyantlı banka modeli) ve Ç8201 (çatı seçeneği yok) bugünkü gibi: yeni çatı adımı yalnız yeni planda."""
    r = s.yaz("Ç8201 istiyorum", katalog_kodu="Ç8201", yapi_turu="celik")
    assert r.eylem == "is_emri" and "cati_secenekleri" not in s.k.d


# ── yardımcılar ────────────────────────────────────────────────────────────────────────────────────────────────────
def test_taban_kod_yeni_plan_cati_eki():
    assert Katalog.taban_kod("YENI-1A2B3C-K") == "YENI-1A2B3C" == Katalog.taban_kod("YENI-1A2B3C-B") == Katalog.taban_kod("YENI-1A2B3C")
    assert Katalog.taban_kod("Ç8801K") == "Ç8801" and Katalog.taban_kod("P6001") == "P6001" and Katalog.taban_kod("KT-03") == "KT03"
    assert Katalog.taban_kod("YENI-1A2B3C-L") == "YENI-1A2B3C-L"                 # yalnız beşik ve kırma eki


@pytest.mark.parametrize("metin,tip", [
    ("kırma olsun", "kirma"), ("beşik", "besik"), ("Beşik çatılı olsun", "besik"), ("kırmalı yapalım", "kirma"), ("KIRMA", "kirma"),
    ("kırma olsun başka değişiklik yok", "kirma"), ("beşiğe dönelim", "besik"),
    ("kırma olmasın", None), ("beşik istemiyoruz", None), ("kırma yok", None), ("kırmaya gerek yok", None), ("beşik mi kırma mı?", None),
    ("beşik değil kırma", None), ("kırma olur mu?", None), ("beşik olsun. kırma da olur", None), ("çatı olsun", None), ("", None),
    ("kırmızı olsun", None)])
def test_cati_tipi_secimi_okumasi(metin, tip):
    assert CO.cati_tipi_secimi(metin) == tip


def test_cati_secimi_mesaji_turkce_m2():
    a = [{"kod": "YENI-AAAAAA-B", "gosterim": "Beşik", "sira": 1}, {"kod": "YENI-AAAAAA-K", "gosterim": "Kırma", "sira": 2}]
    m = SC.cati_secimi_mesaji(a, {"kod": "YENI-AAAAAA", "gosterim": "Yeni plan", "katalog_m2": 95.06, "oda_programi": "3+1"})
    assert m == ("Yeni plan için 2 çatı seçeneği. Plan ikisinde aynı (95,1 m², 3+1); fark çatıda.\n\n1. Beşik\n2. Kırma\n\n"
                 "Birini seçin ya da yazın (örn. \"kırma olsun\").")
    assert "(88 m², 2+1)" in SC.cati_secimi_mesaji(a, {"kod": "x", "gosterim": "Yeni plan", "katalog_m2": 88.0, "oda_programi": "2+1"})


def test_set_kaydi_konusmada_kucuk_kalir(s):
    """Set kaydı (secenek_setleri tablosuna giden) tanım ve plan taşımaz; çatı tanımları konuşmada, seçimle silinir."""
    _, yeni = cati_seti(s)
    assert len(json.dumps(s.set, ensure_ascii=False)) < 4000
    s.dugme(f"{yeni}-B")
    assert "cati_secenekleri" not in s.k.d and copy.deepcopy(s.k.d)
