"""İE-25 · çatı plan seçildikten sonra, elimizdeki modellerle (pano 41; Lokman 1 Kasım 2026: karar kartı "Plan seçildikten sonra" ve
"var olan modeller üzerinden gidelim"). Karar katmanı: LLM yok, Postgres yok, çizim yok (`karar_ver` İş Emri'ni kurar, motor koşmaz).

- Alan setinde her plan bir kez: banka modelinin çatı varyantları (Ç8801K, Ç8801L) setten çıkar (`secenek.tek_plan`).
- İE-42 (D-94; Lokman 14 Kasım 2026 20:33:41 kartı "Onaydan sonra, eskizdeki gibi"; M-08 bu sözle açılıp D-94'le kapandı): çatı varyantlı
  model setten seçilince (düğme, numara, kod) r01 katalog çatısıyla; "Onayla" modelin çatı setini getirir ("Planınız onaylandı (r01). Şimdi
  çatıyı seçin."; katalog çatısı, K, L; İE-08 A2'nin seti ve görseli). Katalog çatısı r01'i onaylar; K ya da L aynı planı o çatıyla r02 çizer.
  (İE-25'te set plan seçilince, çizimden önce geliyordu.)
- Plan ve çatı aynı istekte yazıldıysa ("Ç8801 çatı L olsun"; set sunulurken saklanan "çatı K olsun") çatı adımı yok, onayda da sorulmaz.
  Kararsız ya da olumsuz çatı sözü planla geldiyse set plandan önce gelir (İE-25 yolu, `_cati_seti_plandan_once`).
- Çatı varyantı olmayan model (KT-02) setten seçilince bugünkü gibi r01 ve onay.
- Çatı seti açıkken gelen yeni ölçü ya da oda sessizce düşmez: talep yeniden okunur (geometri hakemi İE-25 bulgu 5).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
for p in (KOK, KOK / "kanal"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from beyin import karar as K, secenek as SC  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.sema import Talep  # noqa: E402
from kanal import etkilesim as ET  # noqa: E402

NUMARA = "900000000101"                        # gerçek olmayan deneme numarası
BAYI = {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi", "numara": NUMARA}
T88 = {"alan_m2": 88, "oda_programi": "2+1", "yapi_turu": "celik", "kat_sayisi": 1}


@pytest.fixture(scope="module")
def kat():
    return Katalog(kabul_edilmis=None)                     # yedi çelik aday görünür (harness ve altın set gibi)


class Sohbet:
    def __init__(self, kat, tmp_path):
        self.kat, self.k, self.n = kat, Konusma(NUMARA, kok=tmp_path), 0

    def yaz(self, metin: str, **talep):
        self.n += 1
        self.k.son_mesaj_id = f"wamid.CATI{self.n:03d}"
        t = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": metin, **talep})
        return K.karar_ver(t, self.k, BAYI, self.kat, metin)

    def bas(self, kod: str, baslik: str):
        st = self.k.d["secenek_seti"]
        self.n += 1
        g = {"id": f"wamid.CATI{self.n:03d}", "type": "interactive", "reply_id": f"s:{st['id']}:{kod}", "text": baslik}
        e = ET.coz(g, self.k.d)
        self.k.son_mesaj_id = g["id"]
        return K.karar_ver(Talep.model_validate(e["talep"]), self.k, BAYI, self.kat, e["metin"])

    @property
    def set(self) -> dict:
        return self.k.d.get("secenek_seti") or {}

    def kodlar(self) -> list[str]:
        return [a["kod"] for a in self.set.get("adaylar") or []]

    def sira(self, kod: str) -> int:
        return next(a["sira"] for a in self.set["adaylar"] if a["kod"] == kod)

    def onayla(self):
        ie = self.k.d["son_is_emri"]
        self.n += 1
        g = {"id": f"wamid.CATI{self.n:03d}", "type": "interactive", "reply_id": f"o:{ie['is_emri_no']}:{ie['revizyon']}", "text": "Onayla"}
        e = ET.coz(g, self.k.d)
        assert e.get("gecerli"), e
        self.k.son_mesaj_id = g["id"]
        return K.karar_ver(Talep.model_validate(e["talep"]), self.k, BAYI, self.kat, e["metin"])


@pytest.fixture
def s(kat, tmp_path):
    return Sohbet(kat, tmp_path)


def _plan(r) -> str | None:
    return ((r.is_emri or {}).get("yapi") or {}).get("kod")


KARARSIZ = ", çatı K mı L mi bilemedim"


def _cati_seti_plandan_once(s, metin: str = "88 m² 2+1 tek kat çelik", **talep):
    """İE-42'den beri çatı seti plandan önce yalnız talepte kararsız (ya da olumsuz) çatı sözü varken gelir (İE-25 yolu). Bu dosyanın
    set ömrü vakaları (talep değişikliği seti eskitir, oda programı numara değil, soru bütçesi) o seti böyle açar; önce sözsüz talep
    yetiyordu."""
    s.yaz(metin + KARARSIZ, **(talep or T88))
    r = s.bas("Ç8801", "1. Ç8801")
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti" and not s.k.d.get("son_is_emri"), r.mesaj
    return r


def _onay_kaydedildi(s, r, rev: int = 1) -> None:
    assert (r.eylem, r.gerekce, s.k.d["asama"], s.k.d["son_is_emri"]["revizyon"]) == ("cevapla", K.PLAN_ONAYI, "onaylandi", rev), r.mesaj


# ── süzgeç ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_tek_plan_varyanti_tabani_listedeyse_cikarir():
    a = [{"kod": "Ç8801", "varyantlar": ["Ç8801K", "Ç8801L"]}, {"kod": "Ç8801K", "varyantlar": []}, {"kod": "Ç8801L"}, {"kod": "KT02"}]
    assert [x["kod"] for x in SC.tek_plan(a)] == ["Ç8801", "KT02"]
    yalniz = [{"kod": "Ç8801K", "varyantlar": []}, {"kod": "KT02"}]          # tabanı listede yok: varyant kalır
    assert [x["kod"] for x in SC.tek_plan(yalniz)] == ["Ç8801K", "KT02"]


def test_alan_setinde_her_plan_bir_kez(s):
    r = s.yaz("88 m² 2+1 tek kat çelik", **T88)
    assert r.eylem == "secenek" and s.set["tur"] == "alan"
    assert s.kodlar() == ["Ç8801", "KT02", "KT03", "Ç8201"]
    assert "Ç8801K" not in r.mesaj and "Ç8801-K" not in r.mesaj
    assert [b["id"].rsplit(":", 1)[1] for b in r.butonlar] == ["Ç8801", "KT02", "KT03"]


# ── plan seçildi, çatı sonra ───────────────────────────────────────────────────────────────────────────────────────────
def test_dugmeyle_plan_r01_onayda_cati_seti(s):
    """İE-42: plan düğmesi r01'i katalog çatısıyla çizer (çatı sorulmaz); "Onayla" çatı setini getirir, onay henüz kaydedilmez (kanalın
    onay ve mühendis kancaları "plan onaylandı" bekler); K seçilince aynı plan K çatısıyla r02, r02'nin onayı kaydedilir."""
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    alan_id = s.set["id"]
    r = s.bas("Ç8801", "1. Ç8801")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801" and r.is_emri["revizyon"] == 1
    assert (s.set["id"], s.set["durum"], s.set["secilen_kod"]) == (alan_id, "secildi", "Ç8801")
    r = s.onayla()
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti" and s.set["durum"] == "acik"
    assert K.PLAN_ONAYI not in r.gerekce and s.k.d["asama"] == "onay_bekliyor"
    assert s.kodlar() == ["Ç8801", "Ç8801K", "Ç8801L"] and all(a.get("puan") is None for a in s.set["adaylar"])
    assert r.mesaj.startswith("Planınız onaylandı (r01). Şimdi çatıyı seçin. Bu eve 3 çatı uygulanır. Plan aynı kalır; yalnız çatı "
                              "değişir.\n\n1. Ç8801 · katalog çatısı (Beşik + cumba)\n"), r.mesaj
    assert [b["baslik"] for b in r.butonlar] == ["1. Ç8801", "2. Ç8801-K", "3. Ç8801-L"]
    eski = s.k.d["eski_setler"][-1]                                        # alan seti "seçildi" (kayıtta da: depo._set_kaydi)
    assert eski["id"] == alan_id and eski["durum"] == "secildi" and eski["secilen_kod"] == "Ç8801"
    r = s.bas("Ç8801K", "2. Ç8801-K")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K" and r.is_emri["revizyon"] == 2
    assert r.mesaj == "Çatı: Beşik + cumba, doğu ucu kırma (Ç8801-K). Plan aynı. Ön onay planınız hazır (r02).", r.mesaj
    assert s.set["durum"] == "secildi" and s.set["secilen_kod"] == "Ç8801K"
    _onay_kaydedildi(s, s.onayla(), 2)


def test_numarayla_plan_onayda_cati_sozuyle(s):
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    r = s.yaz(str(s.sira("Ç8801")))
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801", r.mesaj
    r = s.onayla()
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti"
    r = s.yaz("L olsun")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801L" and r.is_emri["revizyon"] == 2


def test_numarayla_katalog_catisi_onaydir(s):
    """Onaydan sonraki sette katalog çatısı r01'i onaylar: yeni çizim yok, mesaj çatıyı ve onayı söyler (çelikte plan teknik kontrole)."""
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    s.yaz(str(s.sira("Ç8801")))
    s.onayla()
    r = s.yaz("1")
    _onay_kaydedildi(s, r)
    assert _plan(r) is None and s.k.d["son_is_emri"]["yapi"]["kod"] == "Ç8801"
    assert r.mesaj.startswith("Çatı: Beşik + cumba (Ç8801). Plan r01 aynen kalır. Onayınız kaydedildi ("), r.mesaj
    assert r.mesaj.endswith("Plan teknik kontrole gönderildi; sonucu size bildireceğiz."), r.mesaj


def test_plan_ve_cati_ayni_mesajda_set_atlanir(s):
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    r = s.yaz("Ç8801 çatı L olsun", katalog_kodu="Ç8801")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801L"
    _onay_kaydedildi(s, s.onayla())                                          # çatı yazıldı: onayda çatı seti yok


def test_talepte_yazilan_cati_plan_secilince_islenir(s):
    r = s.yaz("88 m² 2+1 tek kat çelik, çatı K olsun", **T88)
    assert r.eylem == "secenek" and s.set["tur"] == "alan" and s.k.d.get("celik_istek")
    r = s.bas("Ç8801", "1. Ç8801")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K"
    _onay_kaydedildi(s, s.onayla())


@pytest.mark.parametrize("metin", ["88 m² 2+1 tek kat çelik, çatı K mı L mi bilemedim", "88 m² 2+1 tek kat çelik, Ç8801L olmasın"])
def test_talepte_kararsiz_ya_da_olumsuz_cati_secim_degil(s, metin):
    """Kararsız ya da olumsuz çatı sözü planla geldi: set plandan önce (İE-25 yolu); setten seçilen çatı r01'e, onayda yeniden sorulmaz."""
    s.yaz(metin, **T88)
    r = s.bas("Ç8801", "1. Ç8801")
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti"
    r = s.bas("Ç8801K", "2. Ç8801-K")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K" and r.is_emri["revizyon"] == 1
    _onay_kaydedildi(s, s.onayla())


def test_cati_varyanti_olmayan_model_dogrudan_r01(s):
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    r = s.bas("KT02", "2. KT-02")
    assert r.eylem == "is_emri" and _plan(r) == "KT02"
    _onay_kaydedildi(s, s.onayla())


def test_yeni_plan_setinden_banka_modeli_de_cati_sonra(s):
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    s.k.d["secenek_seti"]["tur"] = "yeni_plan"                            # İE-14 setinin banka seçeneği: aynı dal
    r = s.bas("Ç8801", "2. Ç8801")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801"
    r = s.onayla()
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti"


def test_cati_seti_acikken_kararsiz_cumle_yeniden_sunulur(s):
    _cati_seti_plandan_once(s)
    r = s.yaz("çatı K mı L mi bilemedim")
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti" and "Önce listeden seçin" in r.mesaj


def test_onaydan_sonraki_sette_kararsiz_cumle_sorulur(s):
    """Onaydan sonraki sette kararsız çatı cümlesi seçim değil: "Hangi çatı olsun?" (set açık, onay kaydedilmez)."""
    s.yaz("Ç8801 olsun", katalog_kodu="Ç8801", yapi_turu="celik")
    s.onayla()
    r = s.yaz("çatı K mı L mi bilemedim")
    assert r.eylem == "sor" and "Hangi çatı olsun?" in r.mesaj and s.set["durum"] == "acik" and s.k.d["asama"] == "onay_bekliyor"


# ── çatı seti açıkken yeni talep (hakem bulgu 5) ──────────────────────────────────────────────────────────────────────
def test_cati_seti_acikken_yeni_olcu_sessizce_dusmez(s):
    _cati_seti_plandan_once(s)
    cati_id = s.set["id"]
    r = s.yaz("100 m² 2+1 tek kat çelik olsun", **{**T88, "alan_m2": 100})
    assert r.eylem == "secenek" and s.set["tur"] == "alan" and "100 m²" in r.mesaj
    assert "Ç8801" not in s.kodlar()                                       # 100 m² ±%10: KT-01, KT-03, KT-02
    assert any(e["id"] == cati_id and e["durum"] == "eskidi" for e in s.k.d["eski_setler"])


def test_cati_seti_acikken_llm_eski_bilgiyi_yinelerse_secim_bozulmaz(s, tmp_path):
    _cati_seti_plandan_once(s)
    r = s.yaz("K olsun", **{**T88, "alan_m2": 88.0})                       # aynı değer (int/float) yeni talep değildir
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K"
    s2 = Sohbet(s.kat, tmp_path / "onaydan_sonra")                         # onaydan sonraki sette de
    s2.yaz("88 m² 2+1 tek kat çelik", **T88)
    s2.bas("Ç8801", "1. Ç8801")
    s2.onayla()
    r = s2.yaz("K olsun", **{**T88, "alan_m2": 88.0})
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K" and r.is_emri["revizyon"] == 2, r.mesaj


# ── değişmeyenler ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_model_kodu_yazilinca_r01_onayda_cati_seti(s):
    r = s.yaz("Ç8801 olsun", katalog_kodu="Ç8801", yapi_turu="celik")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801" and r.is_emri["revizyon"] == 1
    r = s.onayla()
    assert r.eylem == "secenek" and s.set["tur"] == "cati_varyanti" and s.kodlar() == ["Ç8801", "Ç8801K", "Ç8801L"]
    assert not s.k.d.get("eski_setler")


def test_varyant_kodu_yazilinca_dogrudan_r01(s):
    r = s.yaz("Ç8801K olsun", katalog_kodu="Ç8801K", yapi_turu="celik")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K"
    _onay_kaydedildi(s, s.onayla())


def test_revizyonda_cati_seti_gelmez(s):
    """Seçilmiş çatı revizyonda kalır; çatı yeniden sorulmaz (onayda da)."""
    s.yaz("88 m² 2+1 tek kat çelik", **T88)
    s.bas("Ç8801", "1. Ç8801")
    s.onayla()
    s.bas("Ç8801L", "3. Ç8801-L")
    s.n += 1
    s.k.son_mesaj_id = f"wamid.CATI{s.n:03d}"
    t = Talep.model_validate({"niyet": "revizyon", "guven": "yuksek", "ozet": "dış duvarlar 140 olsun"})
    r = K.karar_ver(t, s.k, BAYI, s.kat, "dış duvarlar 140 olsun")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801L" and r.is_emri["revizyon"] == 3
    _onay_kaydedildi(s, s.onayla(), 3)


def test_model_koduyla_acilan_cati_setinde_llm_baglam_bilgisi_secimi_bozmaz(s):
    s.yaz("Ç8801 olsun", katalog_kodu="Ç8801", yapi_turu="celik")
    s.onayla()
    r = s.yaz("K olsun", oda_programi="2+1", yapi_turu="celik", kat_sayisi=1)    # taslakta olmayan alan değişiklik sayılmaz
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K"


# ── geometri hakemi ikinci tur ────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin,talep,beklenen", [
    ("iki katlı olsun", {"kat_sayisi": 2}, "kat"),                                    # taslakta kat yoktu: modelinkiyle (tek kat) kıyas
    ("prefabrik olsun", {"yapi_turu": "prefabrik"}, "yapi"),
    ("3+1 olsun", {"oda_programi": "3+1"}, "oda"),
])
def test_cati_seti_acikken_talep_degisikligi_seti_eskitir(s, metin, talep, beklenen):
    _cati_seti_plandan_once(s, "88 m² 2+1 çelik", alan_m2=88, oda_programi="2+1", yapi_turu="celik")
    cati = dict(s.set)
    r = s.yaz(metin, **talep)
    assert any(e["id"] == cati["id"] and e["durum"] == "eskidi" for e in s.k.d["eski_setler"]), r
    assert not (s.set.get("id") == cati["id"] and s.set.get("durum") == "acik")
    assert s.k.d["taslak"].get("katalog_kodu") != "Ç8801" and not s.k.d.get("son_is_emri")
    # eski çatı düğmesi artık geçmez (plan eski bilgiyle çizilmez)
    g = {"id": "wamid.ESKI", "type": "interactive", "reply_id": f"s:{cati['id']}:Ç8801K", "text": "2. Ç8801-K"}
    assert ET.coz(g, s.k.d)["gecerli"] is False


def test_dis_olcuyle_baslayan_talepte_m2_degisikligi(s):
    _cati_seti_plandan_once(s, "9x10 m 2+1 tek kat çelik", dis_olcu={"en_m": 9, "boy_m": 10}, oda_programi="2+1", yapi_turu="celik",
                            kat_sayisi=1)
    r = s.yaz("100 m² olsun", alan_m2=100)
    assert r.eylem == "secenek" and s.set["tur"] == "alan" and "Ç8801" not in s.kodlar()


def test_revizyon_niyetli_olcu_degisikligi_de_dusmez(s):
    _cati_seti_plandan_once(s)
    s.n += 1
    s.k.son_mesaj_id = f"wamid.CATI{s.n:03d}"
    t = Talep.model_validate({"niyet": "revizyon", "guven": "yuksek", "ozet": "100 m² olsun", "alan_m2": 100})
    r = K.karar_ver(t, s.k, BAYI, s.kat, "100 m² olsun")
    assert r.eylem == "secenek" and s.set["tur"] == "alan" and "100 m²" in r.mesaj


def test_cati_seti_soru_butcesinden_yemez(s):
    s.yaz("çelik ev istiyorum", yapi_turu="celik")
    s.yaz("2+1", oda_programi="2+1")
    s.yaz("88 m²" + KARARSIZ, alan_m2=88)                                    # İE-42: set plandan önce yalnız kararsız sözle
    assert s.set.get("tur") == "alan"
    s.bas("Ç8801", "1. Ç8801")
    assert s.set["tur"] == "cati_varyanti"
    r = s.yaz("mutfak penceresi 120x120 olsun")
    assert r.eylem != "yonlendir" and s.set["durum"] == "acik"                  # set yeniden sunulur, istek saklanır
    r = s.bas("Ç8801K", "2. Ç8801-K")
    assert r.eylem == "is_emri" and _plan(r) == "Ç8801K"


# ── geometri hakemi üçüncü tur ────────────────────────────────────────────────────────────────────────────────────────────
def _eskidi(s, set_id: str) -> bool:
    return any(e["id"] == set_id and e["durum"] == "eskidi" for e in s.k.d.get("eski_setler") or [])


@pytest.mark.parametrize("metin,talep,mesajda", [
    ("3+1 olsun", {"oda_programi": "3+1"}, "3+1"),
    ("100 m² olsun", {"alan_m2": 100}, "100 m²"),
])
def test_llm_baglamdaki_kodu_yinelerse_degisiklik_gizlenmez(s, metin, talep, mesajda):
    """Bulgu 1: çatı seti açıkken taslakta Ç8801 var, LLM bağlamdan "Ç8801"i yineler (mesajda kod yok): değişiklik yine okunur."""
    _cati_seti_plandan_once(s)
    cati_id = s.set["id"]
    r = s.yaz(metin, katalog_kodu="Ç8801", **talep)
    assert _eskidi(s, cati_id) and r.eylem != "is_emri" and not s.k.d.get("son_is_emri")
    assert s.k.d["taslak"].get("katalog_kodu") is None and mesajda in r.mesaj


@pytest.mark.parametrize("metin,oda", [("1+1 olsun", "1+1"), ("1+1", "1+1"), ("2+2 olsun", "2+2")])
def test_oda_programi_set_numarasi_degil(s, metin, oda):
    """Bulgu 2: "1+1 olsun" setin 1. seçeneği değildir; oda değişikliğidir (çatı seti eskir, plan çizilmez)."""
    _cati_seti_plandan_once(s)
    cati_id = s.set["id"]
    r = s.yaz(metin, oda_programi=oda)
    assert _eskidi(s, cati_id) and r.eylem != "is_emri" and not s.k.d.get("son_is_emri")
    assert oda in r.mesaj                                                     # bayiye yeni oda programıyla döner


def test_m2_ile_baslayan_talepte_dis_olcu_degisikligi_yeni_alanla(s):
    """Bulgu 3: 88 m² talebinde "dış ölçü 10x10" taslaktaki eski m²'nin yerine geçer; yeni set 100 m²'yle kurulur."""
    _cati_seti_plandan_once(s)
    cati_id = s.set["id"]
    r = s.yaz("dış ölçü 10x10 m olsun", dis_olcu={"en_m": 10, "boy_m": 10})
    assert _eskidi(s, cati_id) and r.eylem == "secenek" and s.set["tur"] == "alan"
    assert "100 m²" in r.mesaj and "Ç8801" not in s.kodlar() and "alan_m2" not in s.k.d["taslak"]


def test_tek_kenarli_dis_olcu_degisikligi(s):
    """Bulgu 4: yalnız bir kenar gelirse taslaktakiyle birleşir (9x10 → 7x10, 70 m²); Ç8801'in çatı seti eskir."""
    _cati_seti_plandan_once(s, "9x10 m 2+1 tek kat çelik", dis_olcu={"en_m": 9, "boy_m": 10}, oda_programi="2+1", yapi_turu="celik",
                            kat_sayisi=1)
    cati_id = s.set["id"]
    r = s.yaz("kısa kenar 7 metre olsun", dis_olcu={"en_m": 7})
    assert _eskidi(s, cati_id) and r.eylem != "is_emri" and not s.k.d.get("son_is_emri")
    assert s.k.d["taslak"]["dis_olcu"] == {"en_m": 7.0, "boy_m": 10.0}


def test_m2_ile_baslayan_talepte_tek_kenar_sorulur(s):
    _cati_seti_plandan_once(s)
    cati_id = s.set["id"]
    r = s.yaz("kısa kenar 7 metre olsun", dis_olcu={"en_m": 7})
    assert _eskidi(s, cati_id) and r.eylem == "sor" and r.soru_alani == "dis_olcu" and not s.k.d.get("son_is_emri")


@pytest.mark.parametrize("metin,talep,mesajda", [
    ("Ç8801 olmasın, 3+1 olsun", {"oda_programi": "3+1"}, "3+1"),
    ("Ç8801 yerine 100 m² olsun", {"alan_m2": 100}, "100 m²"),
])
def test_kaynak_ya_da_olumsuz_kodla_gelen_degisiklik_dusmez(s, metin, talep, mesajda):
    """Dördüncü tur: değişimin kaynağı ya da olumsuz cümledeki kod seçim değildir; talep değişikliği çatı setini eskitir."""
    _cati_seti_plandan_once(s)
    cati_id = s.set["id"]
    r = s.yaz(metin, **talep)
    assert _eskidi(s, cati_id) and r.eylem != "is_emri" and not s.k.d.get("son_is_emri") and mesajda in r.mesaj
