"""İE-20 PR-6 (D-88) · prefabrik talep formu: iki ekranlı form tanımı (Flow JSON 7.3 sınırları, standartlar seçili), cevabın çözümü, ölçü
hesabı (Lokman'ın kuralı ve örnekleri), LLM'siz talep, bayiye giden notlar, standart dışı seçimlerin İş Emri'ne işlenmesi, yapı tipi
düğmesi ve hangi formun sunulacağı. Postgres, ağ, LLM ve WhatsApp yok.

Koşum: python -m pytest testler/kalici/test_prefabrik_formu.py -q
"""
from __future__ import annotations

import copy
import json
import re

import pytest

import ayarlar as AY
import etkilesim as ET
import meta_api as M
import talep_formu as TF
import worker as W
from beyin import form_ozellik as FO
from beyin import gorsel_okuma as GO
from beyin import karar as KR
from beyin.sema import Talep

SINIR = {"TextInput": 20, "TextArea": 20, "Dropdown": 20, "RadioButtonsGroup": 30, "CheckboxGroup": 30, "DocumentPicker": 80, "PhotoPicker": 80,
         "Footer": 35}
SECIMLI = ("RadioButtonsGroup", "Dropdown", "CheckboxGroup")
PICKER = ("DocumentPicker", "PhotoPicker")
AYAR_V1 = {"mesaj_katmani": True, "talep_formu": {"acik": True, "talep_flow_id": "1111111111", "revizyon_flow_id": "2222222222", "taslak": True}}
AYAR_PF = {**AYAR_V1, "talep_formu": {**AYAR_V1["talep_formu"], "prefabrik_flow_id": "3333333333"}}
STD = dict(TF.STANDART)
GELEN = {"id": "wamid.TEST000001", "sender": "905550000001"}


def _cevap(**alan) -> dict:
    return TF.cevap_ozeti(json.dumps({"flow_token": "pf:abc123", "kat": "1", "oda": "2+1", "oncelik": "butce", **STD, **alan}, ensure_ascii=False))


# ─── form tanımı ───
def test_form_tanimi_iki_ekran_flow_json_sinirlari():
    t = TF.tanim("prefabrik")
    assert t["version"] == "7.3" and "data_api_version" not in t and "routing_model" not in t      # uç noktasız
    e1, e2 = t["screens"]
    assert (e1["id"], e2["id"]) == (TF.EKRAN["prefabrik"], "OZELLIK_P")
    assert not e1.get("terminal") and e2["terminal"] is True and e2["success"] is True
    for ekran in (e1, e2):
        assert re.fullmatch(r"[A-Z_]+", ekran["id"]) and 0 < len(ekran["title"]) <= 30
        assert all("__example__" in v and v["type"] == "string" for v in ekran.get("data", {}).values())
        cocuklar = ekran["layout"]["children"]
        adlar = [c["name"] for c in cocuklar if "name" in c]
        assert len(adlar) == len(set(adlar))
        assert sum(c["type"] in PICKER for c in cocuklar) <= 1                                   # ekranda en çok bir dosya seçici
        assert [c["type"] for c in cocuklar].count("Footer") == 1 and cocuklar[-1]["type"] == "Footer"
        for c in cocuklar:
            if c["type"] in SINIR:
                assert 0 < len(c["label"]) <= SINIR[c["type"]], c
            if c["type"] in SECIMLI:
                assert 1 <= len(c["data-source"]) <= 20 and all(len(x["title"]) <= 30 for x in c["data-source"])
                assert all(len(x.get("description", "")) <= 300 for x in c["data-source"])
            if "helper-text" in c:
                assert len(c["helper-text"]) <= 80
            if c["type"] in PICKER:
                assert "isteğe bağlı" not in c["label"]            # Meta, 14 Kasım 2026: en az 0 dosyada etikete "(isteğe bağlı)" kendisi ekler
                assert "init-value" not in c and len(c.get("description", "")) <= 300 and c["max-uploaded-documents"] == 1
                assert c["max-file-size-kb"] * 1024 <= GO.EN_BUYUK_BAYT
                for mime in c["allowed-mime-types"]:
                    assert GO.okunabilir_mi(mime, 1000) is None, mime
            for d in re.findall(r"\$\{data\.(\w+)\}", json.dumps(c)):
                assert d in ekran.get("data", {}), d
            for k, v in c.items():                                # Meta: sınır özellikleri tamsayı (12 Kasım: "max-length": "600" reddedildi)
                if k.startswith(("max-", "min-")):
                    assert type(v) is int, (k, v)
    # ekran 1 → ekran 2: geçiş yük taşımaz; ekran 2 ilk ekranın alanlarını genel başvuruyla (`${screen.TALEP_P.form.x}`, Flow JSON 4.0+)
    # cevaba yazar. Meta, 14 Kasım 2026: geçiş yükündeki sayı girişi (`${form.alan}`, `en`, `boy`) ikinci ekranın "string" veri modeline
    # yazılamaz (INVALID_NAVIGATE_ACTION_PAYLOAD); uzun kenar çoğu zaman boştur, tipli geçişe sokulmaz.
    a1 = [c["name"] for c in e1["layout"]["children"] if "name" in c]
    gecis = e1["layout"]["children"][-1]["on-click-action"]
    assert gecis["name"] == "navigate" and gecis["next"] == {"type": "screen", "name": "OZELLIK_P"}
    assert gecis["payload"] == {} and "data" not in e2
    a2 = [c["name"] for c in e2["layout"]["children"] if "name" in c]
    bitis = e2["layout"]["children"][-1]["on-click-action"]
    assert bitis["name"] == "complete"
    assert bitis["payload"] == {**{a: "${screen.TALEP_P.form.%s}" % a for a in a1}, **{a: "${form.%s}" % a for a in a2}}
    # önizleme verisi ilk ekranın verisiyle aynı alanlar (vps/flow_taslak.py önizlemesi ve canlı sunuş)
    assert set(TF.prefabrik_ekran_verisi(None, None)) == set(e1["data"])


def _alan_turu(c: dict) -> str:
    """Bileşenin form değerinin Flow JSON türü (Meta'nın geçiş yükü denetimindeki gibi)."""
    if c["type"] == "TextInput" and c.get("input-type") == "number":
        return "number"
    return "array" if c["type"] in PICKER or c["type"] == "CheckboxGroup" else "string"


@pytest.mark.parametrize("tur", ["talep", "revizyon", "prefabrik", "talep2"])
def test_gecis_yuku_sonraki_ekranin_veri_modeliyle_ayni_turde(tur):
    """Meta'nın 14 Kasım 2026 hatası yerelde yakalanır: `navigate` yükündeki her alan sonraki ekranın veri modelinde aynı türle durur,
    veri modelinin her alanı yükte vardır; `${screen.X.form.y}` var olan bir ekranın var olan alanını gösterir."""
    ekranlar = {e["id"]: e for e in TF.tanim(tur)["screens"]}
    alanlar = {kid: {c["name"]: c for c in e["layout"]["children"] if "name" in c} for kid, e in ekranlar.items()}
    for kid, e in ekranlar.items():
        for c in e["layout"]["children"]:
            eylem = c.get("on-click-action") or {}
            for ekran, alan in re.findall(r"\$\{screen\.(\w+)\.form\.(\w+)\}", json.dumps(eylem)):
                assert ekran in ekranlar and alan in alanlar[ekran], (ekran, alan)
            if eylem.get("name") != "navigate":
                continue
            model = ekranlar[eylem["next"]["name"]].get("data", {})
            assert set(eylem["payload"]) == set(model), (kid, sorted(set(eylem["payload"]) ^ set(model)))
            for ad, deger in eylem["payload"].items():
                m = re.fullmatch(r"\$\{form\.(\w+)\}", str(deger))
                if m:
                    assert _alan_turu(alanlar[kid][m.group(1)]) == model[ad]["type"], (kid, ad)
                m = re.fullmatch(r"\$\{data\.(\w+)\}", str(deger))
                if m:
                    assert e["data"][m.group(1)]["type"] == model[ad]["type"], (kid, ad)


def _hepsi(dugum) -> list[dict]:
    """Ekrandaki bütün bileşenler; `If` ve `Switch` dallarındakiler dahil."""
    if isinstance(dugum, list):
        return [x for d in dugum for x in _hepsi(d)]
    if not isinstance(dugum, dict):
        return []
    return ([dugum] if "type" in dugum else []) + [x for k, v in dugum.items() if k != "data-source" for x in _hepsi(v)]


@pytest.mark.parametrize("tur", ["talep", "revizyon", "prefabrik", "talep2"])
def test_alan_adi_formun_butununde_tek(tur):
    """Meta, 14 Kasım 2026 (DUPLICATE_FORM_COMPONENT_NAMES): aynı alan adı `If`'in iki dalında bile iki kez geçemez; ad formun bütün
    ekranlarında tektir."""
    adlar = [c["name"] for e in TF.tanim(tur)["screens"] for c in _hepsi(e["layout"]) if "name" in c]
    assert len(adlar) == len(set(adlar)), sorted(a for a in set(adlar) if adlar.count(a) > 1)


def test_cevapta_sayi_da_metin_de_okunur_bos_alan_dusmez():
    """Sayı girişi cevapta sayı (70, 7.73) ya da metin ("70", "7,73") gelebilir; boş alan hiç gelmeyebilir, "" ya da null gelebilir."""
    for alan in ({"alan": 70, "en": 7}, {"alan": "70", "en": "7"}, {"alan": 70.0, "en": 7, "boy": ""}, {"alan": "70", "en": "7,0", "boy": None}):
        t = TF.talep(_cevap(**alan))
        assert t["pano"] == {"nx": 5.5, "ny": 8.0} and t["alan_m2"] == 72.0 and "dis_olcu" not in t, (alan, t)
    for alan in ({"en": 7.73, "boy": 10.14}, {"en": "7,73", "boy": "10,14"}, {"en": "7.73", "boy": "10.14", "alan": ""}, {"en": 10.14, "boy": 7.73}):
        t = TF.talep(_cevap(**alan))
        assert t["pano"] == {"nx": 6.0, "ny": 8.0}, (alan, t)
    assert "pano" not in TF.talep(_cevap(alan="", en="", boy="")) and "pano" not in TF.talep(_cevap(alan=None, en=None, boy=None))


def test_form_secenekleri_cozumleyiciyle_ayni_ve_standartlar_secili():
    e1, e2 = TF.tanim("prefabrik")["screens"]
    c1 = {c["name"]: c for c in e1["layout"]["children"] if "name" in c}
    c2 = {c["name"]: c for c in e2["layout"]["children"] if "name" in c}
    ids = lambda c: [x["id"] for x in c["data-source"]]                      # noqa: E731
    assert ids(c1["kat"]) == list(TF.KAT) and ids(c1["oda"]) == list(TF.ODA) and ids(c1["oncelik"]) == list(TF.ONCELIK)
    assert c1["oncelik"]["required"] is True and c1["oda"]["required"] is True
    assert not c1["alan"].get("required") and not c1["en"].get("required") and not c1["boy"].get("required")
    for alan, (izinli, _anahtar) in TF.OZELLIKLER.items():
        assert ids(c2[alan]) == list(izinli), alan
        assert c2[alan]["init-value"] == TF.STANDART[alan] and c2[alan]["required"] is True       # Lokman: standart özellikler seçili gelsin
    assert set(TF.STANDART) == set(TF.OZELLIKLER)
    assert ids(c2["ek"]) == list(TF.EK) and "init-value" not in c2["ek"]
    # Lokman 13 Kasım 21:26 UTC: çatı rengi standardı antrasit gri, pencere rengi standardı beyaz; ısıtma ve veranda formda yok
    assert TF.STANDART["cati_rengi"] == "antrasit" and TF.STANDART["pencere_rengi"] == "beyaz" and TF.STANDART["kaplama"] == "trapez"
    yazi = json.dumps(TF.tanim("prefabrik"), ensure_ascii=False).lower()
    assert "ısıtma" not in yazi and "veranda" not in yazi and "yapi" not in c1 and "cati" not in c1
    # formun yazıları ile İş Emri'ne işleyen sözlük aynı kelimeler (beyin/form_ozellik.py)
    assert set(FO.YUKSEKLIK_CM) == set(TF.YUKSEKLIK.values()) and set(FO.IC_DUVAR_CM) == set(TF.IC_DUVAR.values())
    assert {y: f"{cm} cm" for y, cm in FO.YUKSEKLIK_CM.items()} == {y: y for y in FO.YUKSEKLIK_CM}
    assert {y: f"{cm * 10} mm" for y, cm in FO.IC_DUVAR_CM.items()} == {y: y for y in FO.IC_DUVAR_CM}
    assert set(FO.CATI_KAPLAMASI) == set(TF.KAPLAMA.values()) and set(FO.CATI_RENGI) == set(TF.CATI_RENGI.values())
    assert set(FO.TAVAN) == set(TF.TAVAN.values()) and FO.ALCIPAN == TF.EK["alcipan"]
    assert FO.STANDART == {"Çatı Kaplaması": TF.KAPLAMA[TF.STANDART["kaplama"]], "Çatı Kaplama Rengi": TF.CATI_RENGI[TF.STANDART["cati_rengi"]],
                           "Tavan": TF.TAVAN[TF.STANDART["tavan"]]}
    assert all(FO._standart_mi(satir, FO.SATIRLAR[satir][v]) for satir, v in FO.STANDART.items())
    assert not any(FO._standart_mi(satir, yazi) for satir, sozluk in FO.SATIRLAR.items() for v, yazi in sozluk.items() if v != FO.STANDART[satir])
    assert {a for _i, a in TF.OZELLIKLER.values()} >= {"Çatı Kaplaması", "Çatı Kaplama Rengi", "Pano Yüksekliği", "İç Duvar", "Tavan"}
    assert TF.EK_OZELLIK == "Ek İstekler"


# ─── ölçü hesabı (Lokman, 13 Kasım 2026 21:26 UTC) ───
def test_olcu_hesabi_lokmanin_ornekleri():
    # "7 m kısa kenar, 70 m² → 710,25 × 1014 (5,5 × 8 pano), 72 m²"
    o = TF.olcu_hesabi(7, None, 70)
    assert (o["nx"], o["ny"], o["en_cm"], o["boy_cm"], o["hesaplanan"]) == (5.5, 8.0, 710.25, 1014.0, "uzun") and round(o["alan_m2"]) == 72
    assert TF.olcu_yazisi(o) == "7,10 × 10,14 m (5,5 × 8 pano), 72 m²"
    # "5 m kısa kenar, 70 m²": kısa kenar 4 pano 522 cm, uzun kenar 70 / 5,22 = 13,41 m → 10,5 pano 1327,75 cm
    o = TF.olcu_hesabi(5, None, 70)
    assert (o["nx"], o["ny"], o["en_cm"], o["boy_cm"]) == (4.0, 10.5, 522.0, 1327.75)
    # kısa kenar = 20 + 62,75 × yarım pano; uzun kenar = 10 + 62,75 × yarım pano
    for o in (TF.olcu_hesabi(7, 10, None), TF.olcu_hesabi(6.3, 9.1, None), TF.olcu_hesabi(4, None, 33), TF.olcu_hesabi(None, 12, 95)):
        assert (o["en_cm"] - 20) / 62.75 == o["nx"] * 2 and (o["boy_cm"] - 10) / 62.75 == o["ny"] * 2
        assert o["nx"] * 2 == int(o["nx"] * 2) and o["ny"] * 2 == int(o["ny"] * 2) and o["en_cm"] <= o["boy_cm"]


def test_olcu_hesabi_kenarlar():
    assert TF.olcu_hesabi(7, 10, None)["hesaplanan"] is None and TF.olcu_hesabi(7, 10, 70) == TF.olcu_hesabi(7, 10, None)   # iki kenar: m² okunmaz
    assert TF.olcu_hesabi(10, 7, None)["nx"] == 5.5                                    # kenarlar ters yazılırsa kısa kenar kısa olandır
    assert TF.olcu_hesabi(None, 10, 70) == {**TF.olcu_hesabi(7, 10, None), "hesaplanan": "kisa"}
    assert TF.olcu_hesabi(710, None, 70) == TF.olcu_hesabi(7.1, None, 70)              # santimetre yazılmış kenar
    assert TF.olcu_hesabi(None, None, 70) is None and TF.olcu_hesabi(7, None, None) is None and TF.olcu_hesabi(None, None, None) is None
    o = TF.olcu_hesabi(9, None, 60)                                                    # m² kısa kenara göre küçük: hesaplanan kenar kısa kalır
    assert o["en_cm"] <= o["boy_cm"]
    # Beyin'in yuvarlaması ile aynı sonuç (karar.pano_sayisi, karar.dis_olcu_cm): hesap iki yerde, kıyas burada (webhook hafif kalsın
    # diye `talep_formu` Beyin'in karar modülünü içe aktarmaz). 1,00 m'den 40,00 m'ye her santimetre.
    for cm in range(100, 4001):
        m = cm / 100
        assert TF.pano(m, TF.KOSE_KISA_CM) == KR.pano_sayisi(m, 20) and TF.pano(m, TF.KOSE_UZUN_CM) == KR.pano_sayisi(m, 10), m
    for nx, ny in ((5.5, 8), (4, 10.5), (6, 8), (3, 3.5)):
        o = TF.olcu_hesabi((KR.MOD * nx + 20) / 100, (KR.MOD * ny + 10) / 100, None)
        assert (o["nx"], o["ny"]) == (nx, ny) and (o["en_cm"], o["boy_cm"]) == KR.dis_olcu_cm(nx, ny)
    assert TF.MODUL_CM == KR.MOD


# ─── cevap → talep ───
def test_cevap_ozeti_ve_talep():
    oz = _cevap(alan="70", en="7", boy="", kaplama="kiremit", yukseklik="280", dis_duvar="160", ic_duvar="100", ek=["alcipan", "lata"],
                musteri="Ahmet Yılmaz", il="Bursa", ilce="Nilüfer", **{"not": "Salon geniş olsun, 0532 111 22 33"},
                dosya=[{"file_name": "plan.jpg", "mime_type": "image/jpeg", "sha256": "abc=", "id": "3631120727156756"}])
    assert (oz["tur"], oz["form"], oz["token"]) == ("talep", "prefabrik", "pf:abc123")           # webhook ve kuyruk için yine "talep"
    assert oz["alanlar"]["alan"] == 70.0 and oz["alanlar"]["en"] == 7.0 and "boy" not in oz["alanlar"]
    assert oz["dosyalar"] == [{"id": "3631120727156756", "file_name": "plan.jpg", "mime_type": "image/jpeg", "sha256": "abc="}]
    t = TF.talep(oz)
    Talep.model_validate(t)
    assert (t["niyet"], t["yapi_turu"], t["kat_sayisi"], t["oda_programi"]) == ("yeni_talep", "prefabrik", 1, "2+1")
    assert t["pano"] == {"nx": 5.5, "ny": 8.0} and t["alan_m2"] == 72.0 and "dis_olcu" not in t   # uzun kenarı kod hesapladı, bayiye sorulmaz
    assert t["bina_ozellikleri"] == {"Çatı Kaplaması": "kiremit desen sac + OSB + nem bariyeri", "Çatı Kaplama Rengi": "antrasit gri",
                                     "Pano Yüksekliği": "280 cm", "Dış Duvar": "160 mm", "İç Duvar": "100 mm", "Tavan": "alçıpan asma tavan",
                                     "Pencere Rengi": "beyaz",
                                     "Ek İstekler": "iç duvarlarda alçıpan kaplama; H profilde lata, köşelerde yalı baskı"}
    assert "yukseklik_cm" not in t and t["musteri"] == {"ad": "Ahmet Yılmaz", "sevk_adresi": "Nilüfer, Bursa"}
    assert len(t["ozel_istekler"]) == 1 and "111 22 33" not in t["ozel_istekler"][0]            # not: numara maskeli
    assert t["ozet"] == TF.set_basligi(oz) == "Prefabrik, tek kat, 2+1, 72 m²"
    assert "veranda" not in t and "cati" not in t                                              # formda yok; v1'deki sabit beşik + ön veranda yazılmaz
    assert TF.oncelik(oz) == "butce" and TF.oncelik({"tur": "talep", "alanlar": {"oncelik": "butce"}}) is None
    assert TF.metin(oz).startswith("Talep formu: prefabrik, tek kat, 2+1, istenen dış ölçü 7,10 × 10,14 m (5,5 × 8 pano), 72 m², "
                                   "çatı kaplaması kiremit desen sac + OSB + nem bariyeri, pano yüksekliği 280 cm, dış duvar 160 mm")
    assert TF.metin(oz).endswith("Dosya eklendi.")


def test_talep_yalniz_m2_ve_standartlar():
    oz = _cevap(alan="70", oda="3+1", kat="2", oncelik="yok")
    t = TF.talep(oz)
    Talep.model_validate(t)
    assert t["alan_m2"] == 70.0 and "pano" not in t and t["kat_sayisi"] == 2 and t["oda_programi"] == "3+1"
    assert t["bina_ozellikleri"]["Pano Yüksekliği"] == "250 cm"
    assert TF.standart_disi(oz) == [] and TF.olcu_notu(oz) == "" and TF.set_basligi(oz) == "Prefabrik, iki kat, 3+1, 70 m²"
    assert TF.oncelik(oz) == "yok"
    # ölçü hiç yok: talep ölçüsüz; eksik bilgi sohbette sorulur
    t = TF.talep(_cevap())
    assert "alan_m2" not in t and "pano" not in t and TF.set_basligi(_cevap()) == "Prefabrik, tek kat, 2+1"


def test_cevap_gecersiz_degerler_atilir():
    oz = TF.cevap_ozeti(json.dumps({"flow_token": "pf:abc123", "kat": "3", "oda": "9+2", "alan": "-5", "en": "abc", "oncelik": "hiz",
                                    "kaplama": "saz", "cati_rengi": "mor", "yukseklik": "400", "dis_duvar": "50", "ic_duvar": "5", "tavan": "x",
                                    "pencere_rengi": "x", "ek": ["alcipan", "havuz", 5], "fazla": "x"}))
    assert oz["form"] == "prefabrik" and oz["alanlar"] == {"ek": ["alcipan"]}
    t = TF.talep(oz)
    Talep.model_validate(t)
    assert t["bina_ozellikleri"] == {"Ek İstekler": "iç duvarlarda alçıpan kaplama"} and t["yapi_turu"] == "prefabrik"
    assert TF.cevap_ozeti({"flow_token": "pf:"})["tur"] == "bilinmiyor"
    assert TF.cevap_ozeti(json.dumps({"flow_token": "tf:abc123", "yapi": "celik"})).get("form") is None      # v1 form cevabı aynen


def test_olcu_notu_bayiye():
    oz = _cevap(alan="70", en="7")
    assert TF.olcu_notu(oz) == "Ölçüyü pano katına yuvarladım: 7,10 × 10,14 m (5,5 × 8 pano), 72 m². Uzun kenarı m²'den hesapladım."
    assert TF.olcu_notu(oz, olcu=False) == ""
    assert TF.olcu_notu(_cevap(en="7", boy="10")) == "Ölçüyü pano katına yuvarladım: 7,10 × 10,14 m (5,5 × 8 pano), 72 m²."
    n = TF.olcu_notu(_cevap(alan="70", yukseklik="300", dis_duvar="160", ek=["cift_yun"]))
    assert n == ("Standart dışı seçimleriniz talebe yazıldı: pano yüksekliği 300 cm, dış duvar 160 mm, çatıda çift kat mineral yün. "
                 "Dış duvar 160 mm çizimde gösterilmez; çizim 100 mm duvarla hazırlanır.")
    assert TF.olcu_notu({"tur": "talep", "alanlar": {"en": 7.0, "boy": 10.0}}) == ""               # v1 formun cevabına not yok


def test_ekran_verisi_ve_token():
    assert TF.prefabrik_tokeni("abc", False) == "pf:abc" and TF.prefabrik_tokeni("abc", True) == "pf:abc:1"
    assert TF.TOKEN.match("pf:abc:1") and TF.TOKEN.match("tf:abc") and TF.TOKEN.match("rv:PM-1:2") and not TF.TOKEN.match("xx:abc")
    v = TF.prefabrik_ekran_verisi(None, None)
    assert v == {"kat": "1", "oda": "", "alan": "", "en": "", "boy": "", "bilinen": v["bilinen"]} and v["bilinen"].startswith("Bildiğiniz")
    v = TF.prefabrik_ekran_verisi({"varsayilanlar": {"yapi_turu": "prefabrik", "kat_sayisi": 2}},
                                  {"oda_programi": "3+1", "alan_m2": 90, "dis_olcu": {"en_m": 12.5, "boy_m": 7.0}})
    assert (v["kat"], v["oda"], v["alan"], v["en"], v["boy"]) == ("2", "3+1", "90", "7", "12.5")
    assert v["bilinen"].startswith("Bildiklerim: 3+1")
    assert all(isinstance(x, str) for x in v.values())
    # Meta yükü: prefabrik formun kimliği ve ilk ekranı
    satir = TF.etkilesim("prefabrik", "Talebinizi formla iletin.", "3333333333", "pf:abc", v, True)
    p = satir["action"]["parameters"]
    assert (p["flow_id"], p["flow_token"], p["flow_cta"], p["mode"]) == ("3333333333", "pf:abc", "Talep formu", "draft")
    assert p["flow_action_payload"] == {"screen": "TALEP_P", "data": v}


# ─── standart dışı seçimler İş Emri'nde ───
def _ie() -> dict:
    return {"yapi": {"sistem": "prefabrik", "nx": 5.5, "ny": 8}, "ozellikler": {"Çatı Tipi": "Beşik"}}


def test_form_ozellik_standart_secim_is_emrini_degistirmez():
    ie = _ie()
    once = copy.deepcopy(ie)
    assert FO.uygula(ie, TF.talep(_cevap(alan="70"))["bina_ozellikleri"]) == [] and ie == once
    assert FO.uygula(ie, None) == [] and FO.uygula(ie, {}) == [] and ie == once
    # LLM'in serbest yazdığı özellik (formun kelimesi değil) bugünkü gibi yalnız kayıtta kalır
    assert FO.uygula(ie, {"Çatı Kaplaması": "kiremit", "Pano Yüksekliği": "2,80", "İç Duvar": "10 cm", "Tavan": "ters"}) == [] and ie == once


def test_form_ozellik_standart_disi_isler():
    ie = _ie()
    bo = TF.talep(_cevap(alan="70", kaplama="kiremit", cati_rengi="kirmizi", yukseklik="280", dis_duvar="160", ic_duvar="100", tavan="ters",
                         pencere_rengi="antrasit", ek=["alcipan", "lata", "cift_yun"]))["bina_ozellikleri"]
    assert FO.uygula(ie, bo) == ["pano yüksekliği 280 cm", "iç duvar 100 mm"]
    assert ie["yapi"]["duvar_yuksekligi_cm"] == 280 and ie["yapi"]["duvar_kalinligi_cm"] == {"dis": 10, "ic": 10}   # dış 160 çizime girmez
    assert ie["ozellikler"] == {"Çatı Tipi": "Beşik", "Çatı Kaplaması": "Kiremit Desen Sac + OSB + Nem Bariyeri",
                                "Çatı Kaplama Rengi": "Kırmızı (RAL 3009)", "Tavan": "Ters", "İç Cephe Kaplaması": "Alçıpan"}
    # revizyonda önceki planda olan değer yeniden not edilmez; İş Emri yine işlenir
    ie2 = _ie()
    assert FO.uygula(ie2, bo, onceki=ie) == [] and ie2["yapi"]["duvar_yuksekligi_cm"] == 280 and ie2["ozellikler"] == ie["ozellikler"]
    ie3 = _ie()
    assert FO.uygula(ie3, {"Pano Yüksekliği": "300 cm"}, onceki=ie) == ["pano yüksekliği 300 cm"] and ie3["yapi"]["duvar_yuksekligi_cm"] == 300
    # seçim şablondan küçükse plan küçültülmez; bayiye söylenir (bir kez)
    ie4 = {"yapi": {"sistem": "prefabrik", "duvar_yuksekligi_cm": 280, "duvar_kalinligi_cm": {"dis": 10, "ic": 10}}}
    std = TF.talep(_cevap(alan="70"))["bina_ozellikleri"]
    assert FO.uygula(ie4, std) == ["bu hazır plan 280 cm pano yüksekliğiyle çizilir; formdaki 250 cm işlenmedi",
                                   "bu hazır plan 100 mm iç duvarla çizilir; formdaki 60 mm işlenmedi"]
    assert ie4["yapi"] == {"sistem": "prefabrik", "duvar_yuksekligi_cm": 280, "duvar_kalinligi_cm": {"dis": 10, "ic": 10}}
    assert FO.uygula(copy.deepcopy(ie4), std, onceki=ie4) == []
    # çelik İş Emri'ne dokunulmaz
    celik = {"yapi": {"sistem": "celik"}}
    assert FO.uygula(celik, bo) == [] and celik == {"yapi": {"sistem": "celik"}}


def test_formdaki_secim_hazir_planin_ozelliginden_once_gelir():
    # PA-06'nın şablonu: OSB + nem bariyeri + trapez, ters tavan, alçıpan (Doğan evinin kendi özellikleri)
    sablon = {"Çatı Kaplaması": "OSB + Nem Bariyeri + Trapez Saç", "Tavan": "Ters", "İç Cephe Kaplaması": "Alçıpan", "Dış Kapı": "Çelik Kapı"}
    std = TF.talep(_cevap(alan="87"))["bina_ozellikleri"]
    ie = {"yapi": {"sistem": "prefabrik"}, "ozellikler": dict(sablon)}
    assert FO.uygula(ie, std) == []
    assert ie["ozellikler"] == {"Çatı Kaplaması": "Trapez Sac", "Tavan": "Asma", "Dış Kapı": "Çelik Kapı"}     # standart seçildi: satırlar standarda
    # şablon zaten standartsa (PA-04: "Trapez Saç", "Antrasit", "Asma") hiçbir şey değişmez
    pa04 = {"yapi": {"sistem": "prefabrik"}, "ozellikler": {"Çatı Kaplaması": "Trapez Saç", "Çatı Kaplama Rengi": "Antrasit", "Tavan": "Asma"}}
    once = copy.deepcopy(pa04)
    assert FO.uygula(pa04, std) == [] and pa04 == once
    # formda alçıpan ve ters tavan seçilirse şablonun satırları kalır
    ie = {"yapi": {"sistem": "prefabrik"}, "ozellikler": dict(sablon)}
    FO.uygula(ie, TF.talep(_cevap(alan="87", tavan="ters", ek=["alcipan"]))["bina_ozellikleri"])
    assert ie["ozellikler"] == {**sablon, "Çatı Kaplaması": "Trapez Sac"}
    # formdan gelmeyen talep (LLM'in serbest özelliği) şablona dokunmaz
    ie = {"yapi": {"sistem": "prefabrik"}, "ozellikler": dict(sablon)}
    assert FO.uygula(ie, {"Çatı Kaplama Rengi": "antrasit gri", "Dış Boya": "beyaz"}) == [] and ie["ozellikler"] == sablon
    # gerçek havuz: standart form her hazır planda çatı kaplamasını trapez sac, tavanı asma bırakır
    for kod in ("PA03", "PA04", "PA06"):
        ie = _sablon(kod)
        FO.uygula(ie, std)
        oz = ie.get("ozellikler") or {}
        assert FO._standart_mi("Çatı Kaplaması", oz.get("Çatı Kaplaması", "trapez")) and oz.get("Tavan", "Asma") == "Asma", (kod, oz)
        assert "İç Cephe Kaplaması" not in oz


def _sablon(kod: str) -> dict:
    import json as _json
    from pathlib import Path
    kok = Path(KR.__file__).resolve().parents[1]
    [a] = [a for a in _json.loads((kok / "beyin" / "veri" / "adaylar_prefabrik.json").read_text(encoding="utf-8")) if a["kod"] == kod]
    return _json.loads((kok / "is_emri" / a["sablon"]).read_text(encoding="utf-8"))


# ─── yapı tipi düğmesi ve form sunuşu ───
def test_yapi_tipi_dugmesi():
    r = ET.coz({"reply_id": "y:abc123:prefabrik"}, {})
    assert r["gecerli"] is True and (r["tur"], r["secim"], r["metin"]) == ("yapi", "prefabrik", "prefabrik")
    Talep.model_validate(r["talep"])
    assert r["talep"]["niyet"] == "yeni_talep" and r["talep"]["yapi_turu"] == "prefabrik"
    r = ET.coz({"reply_id": "y:abc123:celik"}, None)
    assert r["gecerli"] is True and r["talep"]["yapi_turu"] == "celik" and r["metin"] == "çelik"
    assert ET.coz({"reply_id": "y:abc123:ahsap"}, {})["neden"] == "bilinmeyen yapı tipi"
    # açık plan eski düğmeyle kapanmaz
    d = {"asama": "onay_bekliyor", "son_is_emri": {"is_emri_no": "PM-X-1", "revizyon": 2}}
    r = ET.coz({"reply_id": "y:abc123:prefabrik"}, d)
    assert r["gecerli"] is False and r["neden"] == "açık plan varken yapı tipi düğmesi" and "PM-X-1 r02" in r["mesaj"]
    assert ET.coz({"reply_id": "y:abc123:prefabrik"}, {**d, "asama": "onaylandi"})["gecerli"] is True
    # bugünkü düğmeler aynen
    assert ET.coz({"reply_id": "o:PM-X-1:2"}, d)["gecerli"] is True


def test_hangi_form_sunulur():
    # prefabrik formun kimliği ayarda yok: bugünkü talep formu (kurulum davranışı değiştirmez)
    assert "prefabrik_flow_id" not in AY.VARSAYILAN["talep_formu"]
    fs = W.talep_formu_sunusu(GELEN, None, None, AYAR_V1)
    assert fs[0] == "talep" and fs[1].startswith("tf:") and fs[2] == TF.ekran_verisi(None, None)
    assert W.talep_formu_sunusu(GELEN, None, None, {"mesaj_katmani": True}) is None
    # kimlik var, yapı tipi bilinmiyor: iki düğme
    fs = W.talep_formu_sunusu(GELEN, None, None, AYAR_PF)
    assert fs[0] == "yapi_sor" and fs[2:] == (None, None, None)
    satir = W.form_satiri(GELEN, "Merhaba. Talebinizi yazın.", fs, AYAR_PF)
    i = satir["interactive"]
    assert i["type"] == "button" and satir["body"] == "Merhaba. Talebinizi yazın.\n\n" + W.YAPI_SORUSU
    assert [(b["reply"]["id"], b["reply"]["title"]) for b in i["action"]["buttons"]] == [(f"y:{fs[1]}:prefabrik", "Prefabrik"), (f"y:{fs[1]}:celik", "Çelik")]
    assert all(ET.BUTON_ID.match(b["reply"]["id"]) for b in i["action"]["buttons"])
    uzun = "x" * (W.WA_GOVDE - 10)                                             # soru sığmıyorsa metin düşmez; düğmeler yine gider
    satir = W.form_satiri(GELEN, uzun, fs, AYAR_PF)
    assert satir["body"] == uzun and len(satir["interactive"]["action"]["buttons"]) == 2
    M.mesaj_yuku(satir, "905550000001")                                                           # gönderici aynı denetimden geçirir
    # taslakta ya da bayi kartında prefabrik: doğrudan prefabrik form
    for bayi, taslak in ((None, {"yapi_turu": "prefabrik", "oda_programi": "2+1"}), ({"varsayilanlar": {"yapi_turu": "prefabrik"}}, None)):
        fs = W.talep_formu_sunusu(GELEN, bayi, taslak, AYAR_PF)
        assert fs[0] == "prefabrik" and fs[1].startswith("pf:") and fs[1].endswith(":1") == (taslak is not None)
        assert fs[2] == TF.prefabrik_ekran_verisi(bayi, taslak)
        satir = W.form_satiri(GELEN, "Talebinizi formla iletin.", fs, AYAR_PF)
        p = satir["interactive"]["action"]["parameters"]
        assert p["flow_id"] == "3333333333" and p["flow_action_payload"]["screen"] == "TALEP_P"
        M.mesaj_yuku(satir, "905550000001")
    # çelik: çelik formu kurulana kadar bugünkü talep formu (Lokman'ın kart seçimi, 13 Kasım 21:32 UTC)
    fs = W.talep_formu_sunusu(GELEN, None, {"yapi_turu": "celik"}, AYAR_PF)
    assert fs[0] == "talep" and fs[1].startswith("tf:") and fs[2]["yapi"] == "celik"
    assert W.form_kimligi(AYAR_PF, "prefabrik") == "3333333333" and W.form_kimligi(AYAR_V1, "prefabrik") is None
