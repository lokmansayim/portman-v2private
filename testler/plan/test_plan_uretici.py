"""İE-14 r3 · P2 + P5: üretim sırası (program → bankadan uyarlama → çözücü → en son sınırlı LLM programı), yeni plan revizyon işlemleri
ve LLM'e giden metinlerin adsızlığı. LLM çağrısı yok: `manuel` arka uç kayıtlı cevap oynatır, `anthropic` istekleri sahte `_post`'la sınanır.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import llm, plan_islem as PI, plan_program as PP, plan_uretici as PU  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402

ORNEK = KOK / "testler" / "plan" / "ornekler"
T95 = {"alan_m2": 95, "oda_programi": "3+1", "cati": {"tip": "kirma"}}
T82 = {"alan_m2": 82, "oda_programi": "2+1", "veranda": {"istiyor": True, "konum": "yan"}}
T60 = {"alan_m2": 60, "oda_programi": "3+1", "ozel_istekler": ["iki banyo olsun", "kiler"]}


def ornek(ad):
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


# ── üretim sırası ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cogu_talepte_llm_yok_ve_iki_gecerli_plan():
    s = PU.uret(T95, ayar={"acik": True, "backend": "anthropic"})          # LLM çağrılsaydı anahtar yokluğundan hata olurdu
    assert s["durum"] == "gecerli" and s["cagri"] == 0 and len(s["adaylar"]) == 2
    for a in s["adaylar"]:
        assert denetle(a["plan"], {"oda_programi": "3+1", "alan_m2": 95})["gecerli"]
        assert a["sozlesme"]["sema"] == "portman.plan/0.1" and a["sozlesme"]["kaynak"]["yol"] == a["yol"]
        assert "kalemler" in a["denetim"]
    assert [d["basamak"] for d in s["denemeler"]] == ["uyarlama+cozucu"]


def test_uyarlama_ve_cozucu_puanla_birlikte_siralanir():
    s = PU.uret(T82, ayar={"acik": False})
    assert {a["yol"] for a in s["adaylar"]} == {"uyarlama", "cozucu"}
    assert s["adaylar"][0]["puan"] <= s["adaylar"][1]["puan"]
    assert s["adaylar"][0]["kaynak"] == "Ç8201"                            # iç kayıt; bayiye ve LLM'e gitmez


def test_sigmayan_programda_son_basamak_llm_programi_ve_degisen():
    hazir = {"program": None, "yeniden": [{"program": {"yatak": 3, "banyo": 1, "depo": 0, "alan_m2": 66}, "ipucu": {}}]}
    s = PU.uret(T60, hazir=hazir)
    assert s["durum"] == "gecerli" and s["yol"] == "llm_program"
    assert [d["basamak"] for d in s["denemeler"]] == ["uyarlama+cozucu", "llm_program"]
    assert "banyo 2 → 1" in s["degisen"] and "depo çıkarıldı" in s["degisen"] and "alan 60 → 66 m²" in s["degisen"]


def test_son_basamak_oda_programini_ve_alan_sinirini_kod_korur():
    hazir = {"program": None, "yeniden": [{"program": {"yatak": 2, "banyo": 1, "alan_m2": 120}, "ipucu": {"yatak_on": 1}}]}
    s = PU.uret(T60, hazir=hazir)
    assert s["program"]["yatak"] == 3                                       # LLM 2 dedi; oda programı değişmez
    assert s["program"]["alan_m2"] == 60 or s["durum"] != "gecerli"        # ±%10 dışı alan reddedilir (60'a döner)


def test_ayar_kapaliyken_son_basamak_cagrilmaz():
    s = PU.uret(T60, ayar={"acik": False})
    assert s["durum"] == "gecersiz" and s["cagri"] == 0 and [d["basamak"] for d in s["denemeler"]] == ["uyarlama+cozucu"]


def test_llm_hatasi_cagri_sayilir_durum_gecersiz(monkeypatch):
    monkeypatch.setattr(llm, "anahtar_bul", lambda *a, **k: "x")
    monkeypatch.setattr(llm, "_post", lambda *a, **k: (_ for _ in ()).throw(llm.LLMHatasi("ağ")))
    s = PU.uret(T60, ayar={"acik": True, "backend": "anthropic", "en_cok_cagri": 2})
    assert s["durum"] == "gecersiz" and s["cagri"] == 1 and s["hata"]


def test_kayit_bicimi():
    s = PU.uret(T82, ayar={"acik": False})
    k = PU.kayit(s, T82, "deneme")
    assert k["yol"] == s["yol"] and k["sure_ms"] >= 0 and len(k["adaylar"]) == 2 and k["program"]["yatak"] == 2
    assert {"yol", "puan", "kaynak", "islemler", "plan"} <= set(k["adaylar"][0])


# ── P5: LLM'e giden metin adsız ───────────────────────────────────────────────────────────────────────────────────────
def _banka_adlari() -> list[str]:
    adlar = set()
    for a in json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8")):
        adlar.add(a["kod"])
        for x in (a.get("sunum") or {}).values():
            if isinstance(x, str) and len(x) > 6:
                adlar.add(x)
    for f in (KOK / "modeller").glob("*.json"):
        t = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(t, dict) and t.get("ad"):
            adlar.add(t["ad"])
    return sorted(adlar)


BANKA_KODU = re.compile(r"\b(Ç|C)\s?\d{4}|\bKT[-\s]?0\d|\bP\d{4}", re.I)


def _yakala(monkeypatch) -> list[str]:
    giden: list[str] = []

    def sahte(sistem, mesajlar, arac_adi, *a, **k):
        giden.append(sistem + "\n" + json.dumps(mesajlar, ensure_ascii=False))
        raise llm.LLMHatasi("yakalandı")
    monkeypatch.setattr(llm, "arac_cagir", sahte)
    return giden


def test_son_basamak_ornekleri_adsiz(monkeypatch):
    giden = _yakala(monkeypatch)
    PU.uret(T60, ayar={"acik": True, "backend": "anthropic", "en_cok_cagri": 1})
    assert giden and "Örnek A" in giden[-1]
    for metin in giden:
        assert not BANKA_KODU.search(metin), BANKA_KODU.search(metin)
        for ad in _banka_adlari():
            assert ad not in metin, ad
        assert "Çocuk Odası" not in metin and "Müştemilat" not in metin and "bankadaki " not in metin.replace("bankadaki gerçek planlar", "")


def test_program_okumasi_ve_islem_okumasi_adsiz(monkeypatch):
    giden = _yakala(monkeypatch)
    PP.oku({"oda_programi": "2+1", "alan_m2": 80, "ozel_istekler": ["şömine olsun"]}, ayar={"acik": True, "backend": "anthropic"})
    PI.oku(ornek("gecerli_3arti1_100"), "salonu doğuya 50 cm büyütün", ayar={"backend": "anthropic"})
    assert len(giden) == 2
    for metin in giden:
        assert not BANKA_KODU.search(metin) and not any(ad in metin for ad in _banka_adlari())


def test_ornek_ozetleri_kod_ve_ad_tasimaz():
    oz = PP.ornek_ozetleri(3)
    assert oz and all(o.startswith("Örnek ") for o in oz)
    assert not any(BANKA_KODU.search(o) for o in oz)


# ── yeni plan revizyonu: koordinatsız işlemler ────────────────────────────────────────────────────────────────────────
def test_duzenle_islemleri_kod_uygular_fark_koddan():
    hazir = {"islemler": [{"op": "oda_buyut", "mahal": "Salon", "yon": "B", "cm": 50, "alinti": "salonu sola büyütün"},
                          {"op": "dis_karkas_140"}], "uygulanamayan": ["çift kat olsun"]}
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "salonu sola 50 büyütün, dışlar 140, çift kat olsun", {"oda_programi": "3+1"}, hazir=hazir)
    assert s["durum"] == "gecerli", s["ihlaller"]
    assert "Salon 25,2 → 27,4 m²" in s["fark"] and "dış ölçü 1250×800 → 1300×800 cm" in s["fark"] and "dış duvarlar 140'lık karkas" in s["fark"]
    assert s["uygulanamayan"] == ["çift kat olsun"] and s["tanim"]["duvar_siniflari"]["dis"]["profil"] == "140x45x1,2"


def test_duzenle_komsu_baska_hizadaysa_uygulanamaz_ve_plan_degismez():
    hazir = {"islemler": [{"op": "oda_buyut", "mahal": "Salon", "yon": "D", "cm": 50, "alinti": "salon doğuya"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "salon doğuya büyüsün", {"oda_programi": "3+1"}, hazir=hazir)
    # Lokman 15.10 (karar 3): plan değişmeyip istek uygulanamadıysa durum "uygulanamadi" (önceden "gecersiz"); plan yine değişmez, gerekçe aynı
    assert s["durum"] == "uygulanamadi" and s["plan"] is None and any("başka hizada" in x for x in s["uygulanamayan"])


def test_duzenle_denetimden_gecmezse_uygulanamadi_gerekceyle():
    # Lokman 16.10 (canlı deneme, G): kurallara uymayan istek konuşmayı kapatmaz; önceden "gecersiz" → yönlendirme idi. Plan aynen,
    # istek bayinin sözü (yoksa işlemin Türkçesi) ve denetçinin kısa gerekçesiyle yazılır; karar Patron'a bilgi verir (kurala_uymayan)
    hazir = {"islemler": [{"op": "kapi_kaldir", "mahal": "Salon", "mahal_b": "Hol"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "salon hol kapısını kaldırın", {"oda_programi": "3+1"}, hazir=hazir)
    assert s["durum"] == "uygulanamadi" and s["plan"] is None and s["kurala_uymayan"] is True
    assert any("ulaşılamıyor" in x for x in s["ihlaller"]) and s["uygulanamayan"][0].startswith("kapı kaldırma: ")


def test_pencere_degmeyen_cepheye_istenirse_yalniz_o_istek_duser():
    # canlı deneme hazırlığı (15.10): pencere odanın değmediği cepheye yazılınca denetçi bütün revizyonu reddediyordu (geçerli küçültme de
    # düşer, konuşma yönlendirmeyle kapanırdı); artık yalnız o istek "uygulayamadım"a düşer, öteki işlemler uygulanır (karar 3'ün yolu)
    islemler = [{"op": "oda_kucult", "mahal": "Salon", "yon": "K", "cm": 30, "alinti": "salonu 30 küçült"},
                {"op": "pencere_ekle", "mahal": "Salon", "cephe": "D", "olcu": "120x120", "alinti": "salona 120x120 pencere"}]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": islemler, "uygulanamayan": []})
    assert s["durum"] == "gecerli", s["ihlaller"]
    assert "Salon 25,2 → 23,5 m²" in s["fark"] and not any("pencere eklendi" in f for f in s["fark"])
    assert s["uygulanamayan"] == ["salona 120x120 pencere: Salon sağ cepheye değmiyor"]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": islemler[1:], "uygulanamayan": []})
    assert s["durum"] == "uygulanamadi" and s["plan"] is None


def test_semaya_uymayan_islem_yalniz_kendini_dusurur():
    # canlı deneme hazırlığı (T4 "çatı L olsun"): LLM çatıyı şemada olmayan "L" diye yazarsa bütün okuma şema hatasına düşüp konuşma
    # yönlendirmeyle kapanıyordu; uymayan işlem bayinin sözüyle "uygulanamayan"a gider, geçerliler uygulanır
    hazir = {"islemler": [{"op": "cati_tipi", "tip": "L", "alinti": "çatı L olsun"},
                          {"op": "pencere_ekle", "mahal": "Salon", "cephe": "G", "olcu": "120x120", "alinti": "salona pencere"}],
             "uygulanamayan": []}
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir=hazir)
    assert s["durum"] == "gecerli" and s["uygulanamayan"] == ["çatı L olsun"] and "pencere eklendi: Salon ön 120/120" in s["fark"]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": hazir["islemler"][:1], "uygulanamayan": []})
    assert s["durum"] == "uygulanamadi" and s["uygulanamayan"] == ["çatı L olsun"]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": "bozuk"})
    assert s["durum"] == "hata" and s["hata"].startswith("işlem şeması")      # liste bile değilse eskisi gibi hata


def test_birlikte_gecmeyen_islemler_tek_tek_denenir():
    # geometri hakemi 15.10 (Önemli 2): Hol güney cephesine değer ama 120'lik pencere sığmaz; birlikte denetimden geçmeyince geçerli küçültme
    # de düşüyordu. Artık işlemler sırayla tek tek denenir: geçen uygulanır, geçmeyen bayinin sözü ve kısa gerekçesiyle yazılır
    islemler = [{"op": "oda_kucult", "mahal": "Salon", "yon": "K", "cm": 30, "alinti": "salonu 30 küçült"},
                {"op": "pencere_ekle", "mahal": "Hol", "cephe": "G", "olcu": "120x120", "alinti": "hole pencere"}]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": islemler, "uygulanamayan": []})
    assert s["durum"] == "gecerli" and "Salon 25,2 → 23,5 m²" in s["fark"], s
    assert s["uygulanamayan"] == ["hole pencere: Hol güney cephesine 1 açıklık sığmıyor"]
    assert len(s["denemeler"]) == 2 and not s["denemeler"][0]["gecerli"] and s["denemeler"][1]["gecerli"]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": islemler[1:], "uygulanamayan": []})
    assert s["durum"] == "uygulanamadi" and s["kurala_uymayan"]            # Lokman 16.10 (G): tek işlem geçmezse de plan aynen, gerekçeli


def test_sonraki_islemin_mumkun_kildigi_erken_islem_yeniden_denenir():
    # geometri hakemi ikinci tur (küçük 1): hole pencere ancak hol genişleyince sığar; tek geçişte pencere düşüyordu
    hol_pen = {"op": "pencere_ekle", "mahal": "Hol", "cephe": "G", "olcu": "120x120", "alinti": "hole 120 pencere"}
    hol_buy = {"op": "oda_buyut", "mahal": "Hol", "yon": "D", "cm": 50, "alinti": "holü 50 genişlet"}
    kapi = {"op": "kapi_kaldir", "mahal": "Hol", "mahal_b": "Banyo", "alinti": "banyo kapısını kaldır"}
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": [hol_pen, hol_buy, kapi], "uygulanamayan": []})
    assert s["durum"] == "gecerli" and "pencere eklendi: Hol ön 120/120" in s["fark"], s
    assert [x.split(":")[0] for x in s["uygulanamayan"]] == ["banyo kapısını kaldır"]


def test_elli_cm_notu_yalniz_uygulanan_isleme_bakar():
    # hakem ikinci tur (küçük 2): ölçüsüz büyütme uygulanmadıysa "50 cm alındı" yazılmaz
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": [
        {"op": "oda_buyut", "mahal": "Salon", "yon": "D", "alinti": "salonu doğuya büyüt"},
        {"op": "pencere_ekle", "mahal": "Salon", "cephe": "G", "olcu": "120x120", "alinti": "salona pencere"}], "uygulanamayan": []})
    assert s["durum"] == "gecerli" and s["uygulanamayan"] and not any("50 cm" in f for f in s["fark"]), s


def test_elli_cm_notu_ayni_sozlu_islemde_dusmez():
    # hakem üçüncü tur: aynı sözle (ya da sözsüz) iki büyütmeden biri düşünce uygulanan ötekinin "50 cm" notu silinmez (işlem kimliğiyle)
    for soz in ("salonu ve yatak odası 3'ü büyütün", ""):
        s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": [
            {"op": "oda_buyut", "mahal": "Salon", "yon": "D", "alinti": soz},
            {"op": "oda_buyut", "mahal": "Yatak Odası 3", "yon": "B", "alinti": soz}], "uygulanamayan": []})
        assert s["durum"] == "gecerli" and s["uygulanamayan"] and "ölçü söylenmediği için 50 cm alındı" in s["fark"], s


def test_kisa_gerekce_tur_adini_atar_mahal_adini_tutar():
    # hakem ikinci tur (küçük 3) ve üçüncü tur: cümle olan önek ("kapı yayları çakışıyor:") atılmaz
    assert PI._kisa("kapı: Hol ile Banyo arasında kapı yok (x)", 60) == "Hol ile Banyo arasında kapı yok"
    assert PI._kisa("Banyo: giriş kapısından kapılarla ulaşılamıyor", 60) == "Banyo: giriş kapısından kapılarla ulaşılamıyor"
    assert PI._kisa("kapı yayları çakışıyor: K2 ile K5 (x)", 60) == "kapı yayları çakışıyor: K2 ile K5"
    assert PI._kisa("çatı kurulamadı: mahya kısa", 60) == "çatı kurulamadı: mahya kısa"


@pytest.mark.parametrize("cevap,beklenen", [
    ({"islemler": [], "uygulanamayan": "çatı L olsun"}, ["çatı L olsun"]),                 # metin harf harf bölünmez (hakem küçük 1)
    ({"islemler": [], "uygulanamayan": [{"istek": "çift kat olsun"}]}, ["çift kat olsun"]),    # nesne süzülüp atılmaz (küçük 2)
    ({"islemler": [{"op": "cati_tipi", "tip": "L"}], "uygulanamayan": []}, ["çatı tipi değişikliği"]),     # iç işlem adı gitmez (küçük 2)
    ({"islemler": [], "uygulanamayan": {"istek": "çift kat olsun"}}, ["çift kat olsun"]),      # ikinci tur: tek nesne de
    ({"islemler": [], "uygulanamayan": [None, "çift kat olsun"]}, ["çift kat olsun"])])        # "None" yazılmaz
def test_semaya_uymayan_cevap_istegi_adiyla_tutar(cevap, beklenen):
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir=cevap)
    assert s["durum"] == "uygulanamadi" and s["uygulanamayan"] == beklenen


def test_llm_tablosu_odanin_dis_cephelerini_yazar():
    t = PI.tablo(ornek("gecerli_3arti1_100")).splitlines()
    assert next(x for x in t if x.startswith("- Salon ")).endswith("; dış cepheler: G, B")
    assert next(x for x in t if x.startswith("- Banyo ")).endswith("; dış cepheler: K")


@pytest.mark.parametrize("islem,beklenen", [
    ({"op": "pencere_ekle", "mahal": "Yatak Odası 3", "cephe": "K", "olcu": "120x120"}, "pencere eklendi: Yatak Odası 3 arka 120/120"),  # cephe yazılır (hakem 16.10)
    ({"op": "cati_tipi", "tip": "besik"}, "çatı beşik"),                   # canlı deneme 16.10 (B): ham değer "kirma" yazılıyordu
    ({"op": "oda_kucult", "mahal": "Salon", "yon": "K", "cm": 30}, "Salon 25,2 → 23,5 m²"),
])
def test_tekil_islemler(islem, beklenen):
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": [islem], "uygulanamayan": []})
    assert s["durum"] == "gecerli", s["ihlaller"]
    assert beklenen in s["fark"]


# ── canlı deneme dönüşü (16.10.2026; Patron kartı, v2026.10.15) ─────────────────────────────────────────────────────────
def test_pencere_olcu_degisikligi_tek_satir():
    # C: "mutfağın penceresini 120x180 yap" → kaldır + ekle; bayiye "eklendi … kaldırıldı" değil, ölçü değişikliği olarak
    islemler = [{"op": "pencere_kaldir", "mahal": "Salon", "cephe": "B", "olcu": "120x120"},
                {"op": "pencere_ekle", "mahal": "Salon", "cephe": "B", "olcu": "120x180"}]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": islemler, "uygulanamayan": []})
    assert s["durum"] == "gecerli" and s["fark"] == ["pencere ölçüsü: Salon sol 120/120 → 120/180"], s["fark"]


@pytest.mark.parametrize("islem,beklenen", [
    ({"op": "oda_buyut", "mahal": "Salon", "cm": 50, "alinti": "salonu 50 cm büyüt"},
     "salonu 50 cm büyüt: hangi yöne (ön, arka, sol, sağ) büyütüleceği belli değil"),
    ({"op": "oda_kucult", "yon": "K", "cm": 50, "alinti": "50 cm küçült"}, "50 cm küçült: hangi oda belli değil"),
    ({"op": "oda_buyut", "alinti": "biraz büyüt"}, "biraz büyüt: hangi oda ve hangi yöne (ön, arka, sol, sağ) büyütüleceği belli değil")])
def test_oda_islemi_eksik_bilgiyi_ayri_soyler(islem, beklenen):
    # D: canlıda yalnız yön eksikken "hangi oda ve hangi yön belli değil" yazıyordu
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": [islem], "uygulanamayan": []})
    assert s["durum"] == "uygulanamadi" and s["uygulanamayan"] == [beklenen] and not s.get("kurala_uymayan")


# ── geometri hakemi (16.10, 19cfd2b) ─────────────────────────────────────────────────────────────────────────────────────
def _pen(*ler):
    return [{"mahal": m, "cephe": c, "olcu": o, "adet": n} for m, c, o, n in ler]


def test_olcu_eslesmesi_yalniz_tek_kaldirma_tek_ekleme():
    # Orta bulgu: aynı mahal ve cephede birden çok pencere değişince ilk kaldırılan ilk eklenenle eşleşiyor, bayiye yanlış "ölçü" yazılıyordu
    e = ornek("gecerli_3arti1_100")
    y = {**e}
    e = {**e, "pencereler": _pen(("Salon", "B", "60x60", 1), ("Salon", "B", "120x120", 1))}
    f = PU.plan_farki(e, {**y, "pencereler": _pen(("Salon", "B", "120x180", 1))})                # küçüğü kaldır, 120x120 → 120x180
    assert not any("ölçüsü" in x for x in f) and "pencere eklendi: Salon sol 120/180" in f
    assert "pencere kaldırıldı: Salon sol 60/60" in f and "pencere kaldırıldı: Salon sol 120/120" in f
    f = PU.plan_farki(e, {**y, "pencereler": _pen(("Salon", "B", "80x120", 1), ("Salon", "B", "120x160", 1))})   # ikisi de değişir
    assert not any("ölçüsü" in x for x in f) and len(f) == 4
    f = PU.plan_farki({**y, "pencereler": _pen(("Salon", "B", "120x120", 1), ("Salon", "G", "120x180", 1))},
                      {**y, "pencereler": _pen(("Salon", "B", "120x180", 1), ("Salon", "G", "120x180", 1))})
    assert f == ["pencere ölçüsü: Salon sol 120/120 → 120/180"]                                  # tek kaldırma + tek ekleme


def test_pencere_satirlari_cephe_ve_adetle():
    # hakem düşük 3: farklı cephede aynı ölçü "eklendi … kaldırıldı" hiçbir şey değişmemiş gibi okunuyordu; adet 2 iki kez yazılıyordu
    y = ornek("gecerli_3arti1_100")
    f = PU.plan_farki({**y, "pencereler": _pen(("Salon", "B", "120x120", 1))}, {**y, "pencereler": _pen(("Salon", "G", "120x120", 1))})
    assert f == ["pencere eklendi: Salon ön 120/120", "pencere kaldırıldı: Salon sol 120/120"]
    f = PU.plan_farki({**y, "pencereler": []}, {**y, "pencereler": _pen(("Salon", "G", "120x120", 2))})
    assert f == ["pencere eklendi: Salon ön 120/120 (2 adet)"]


def test_adetli_pencereden_biri_kaldirilir():
    # hakem (diff dışı): pencere_kaldir adet 2 girdiyi tümden siliyordu
    p = ornek("gecerli_3arti1_100")
    p["pencereler"] = [{**x, "adet": 2} if (x["mahal"], x["cephe"]) == ("Salon", "G") else x for x in p["pencereler"]]
    s = PI.duzenle(p, "x", {"oda_programi": "3+1"}, hazir={"islemler": [{"op": "pencere_kaldir", "mahal": "Salon", "cephe": "G"}],
                                                           "uygulanamayan": []})
    assert s["durum"] == "gecerli", s
    assert [x["adet"] for x in s["plan"]["pencereler"] if (x["mahal"], x["cephe"]) == ("Salon", "G")] == [1]
    assert s["fark"] == ["pencere kaldırıldı: Salon ön 120/180"]


def test_ayni_plan_yeniden_cizilmez():
    # hakem (diff dışı): aynı ölçüde kaldır + ekle (yazılışı farklı, içeriği aynı plan) "gecerli" sayılıp revizyon hakkı yakıyordu
    islemler = [{"op": "pencere_kaldir", "mahal": "Salon", "cephe": "B", "olcu": "120x120"},
                {"op": "pencere_ekle", "mahal": "Salon", "cephe": "B", "olcu": "120x120"}]
    s = PI.duzenle(ornek("gecerli_3arti1_100"), "x", {"oda_programi": "3+1"}, hazir={"islemler": islemler, "uygulanamayan": []})
    assert s["durum"] == "bos" and s["plan"] is None
