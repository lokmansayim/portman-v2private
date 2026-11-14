"""İE-20 PR-9 (D-93) · çelik talep formu: iki ekranlı form tanımı (Flow JSON 7.3 sınırları, çeliğin standartları seçili), cevabın çözümü,
ölçü (yuvarlanmaz; tek kenar ve m²'den öteki kenar), LLM'siz talep, bayiye giden not, formdaki dış duvar 140 mm karkasın çizime
işlenmesi ve hangi formun sunulacağı. Postgres, ağ, LLM ve WhatsApp yok.

Koşum: python -m pytest testler/kalici/test_celik_formu.py -q
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import ayarlar as AY
import meta_api as M
import talep_formu as TF
import worker as W
from beyin import celik
from beyin import gorsel_okuma as GO
from beyin import karar as KR
from beyin import secenek as SC
from beyin import varyant
from beyin.konusma import Konusma
from beyin.sema import Talep
from test_prefabrik_formu import AYAR_PF, AYAR_V1, GELEN, PICKER, SECIMLI, SINIR

KOK = Path(KR.__file__).resolve().parents[1]
AYAR_CF = {**AYAR_PF, "talep_formu": {**AYAR_PF["talep_formu"], "celik_flow_id": "5555555555"}}
STD = dict(TF.C_STANDART)


def _cevap(**alan) -> dict:
    return TF.cevap_ozeti(json.dumps({"flow_token": "cf:abc123", "kat": "1", "oda": "2+1", "oncelik": "butce", **STD, **alan}, ensure_ascii=False))


# ─── form tanımı ───
def test_form_tanimi_iki_ekran_flow_json_sinirlari():
    t = TF.tanim("celik")
    assert t["version"] == "7.3" and "data_api_version" not in t and "routing_model" not in t      # uç noktasız
    e1, e2 = t["screens"]
    assert (e1["id"], e2["id"]) == (TF.EKRAN["celik"], "OZELLIK_C")
    assert not e1.get("terminal") and e2["terminal"] is True and e2["success"] is True
    for ekran in (e1, e2):
        assert re.fullmatch(r"[A-Z_]+", ekran["id"]) and 0 < len(ekran["title"]) <= 30
        assert all("__example__" in v and v["type"] == "string" for v in ekran.get("data", {}).values())
        cocuklar = ekran["layout"]["children"]
        adlar = [c["name"] for c in cocuklar if "name" in c]
        assert len(adlar) == len(set(adlar))
        assert sum(c["type"] in PICKER for c in cocuklar) <= 1
        assert [c["type"] for c in cocuklar].count("Footer") == 1 and cocuklar[-1]["type"] == "Footer"
        for c in cocuklar:
            if c["type"] in SINIR:
                assert 0 < len(c["label"]) <= SINIR[c["type"]], c
            if c["type"] in SECIMLI:
                assert 1 <= len(c["data-source"]) <= 20 and all(len(x["title"]) <= 30 for x in c["data-source"]), c
                assert all(set(x) <= {"id", "title"} for x in c["data-source"])
            if "helper-text" in c:
                assert len(c["helper-text"]) <= 80
            if c["type"] in PICKER:
                assert "isteğe bağlı" not in c["label"]            # Meta en az 0 dosyada etikete "(isteğe bağlı)" kendisi ekler
                assert "init-value" not in c and len(c.get("description", "")) <= 300 and c["max-uploaded-documents"] == 1
                assert c["max-file-size-kb"] * 1024 <= GO.EN_BUYUK_BAYT
                for mime in c["allowed-mime-types"]:
                    assert GO.okunabilir_mi(mime, 1000) is None, mime
            for d in re.findall(r"\$\{data\.(\w+)\}", json.dumps(c)):
                assert d in ekran.get("data", {}), d
            for k, v in c.items():
                if k.startswith(("max-", "min-")):
                    assert type(v) is int, (k, v)
    # ekran 1 → ekran 2: geçiş yük taşımaz (sayı girişi tipli geçişe sokulmaz); ekran 2 ilk ekranın alanlarını genel başvuruyla cevaba yazar
    a1 = [c["name"] for c in e1["layout"]["children"] if "name" in c]
    gecis = e1["layout"]["children"][-1]["on-click-action"]
    assert gecis["name"] == "navigate" and gecis["next"] == {"type": "screen", "name": "OZELLIK_C"}
    assert gecis["payload"] == {} and "data" not in e2
    a2 = [c["name"] for c in e2["layout"]["children"] if "name" in c]
    bitis = e2["layout"]["children"][-1]["on-click-action"]
    assert bitis["name"] == "complete"
    assert bitis["payload"] == {**{a: "${screen.TALEP_C.form.%s}" % a for a in a1}, **{a: "${form.%s}" % a for a in a2}}
    assert set(TF.celik_ekran_verisi(None, None)) == set(e1["data"])
    assert TF.DUGME["celik"] == "Talep formu" and len(TF.DUGME["celik"]) <= 20


def test_form_lokmanin_onayladigi_alan_listesi():
    """Hedef örnek: Lokman'ın 14 Kasım 2026 20:40 UTC kartıyla onayladığı alan listesi (D-93). Formda çatı şekli, veranda, ısıtma,
    duvar yüksekliği ve yapı tipi sorusu yok."""
    e1, e2 = TF.tanim("celik")["screens"]
    c1 = {c["name"]: c for c in e1["layout"]["children"] if "name" in c}
    c2 = {c["name"]: c for c in e2["layout"]["children"] if "name" in c}
    ids = lambda c: [x["id"] for x in c["data-source"]]                      # noqa: E731
    yazilar = lambda c: [x["title"] for x in c["data-source"]]               # noqa: E731
    assert (e1["title"], e2["title"]) == ("Çelik talep formu", "Standart özellikler")
    assert list(c1) == ["kat", "oda", "alan", "en", "boy", "oncelik"]
    assert [c1[a]["label"] for a in c1] == ["Kat", "Oda programı", "Yaklaşık alan (m²)", "Kısa kenar (m)", "Uzun kenar (m)", "Önceliğiniz"]
    assert ids(c1["kat"]) == list(TF.KAT) and ids(c1["oda"]) == list(TF.ODA) and ids(c1["oncelik"]) == list(TF.ONCELIK)
    assert yazilar(c1["oncelik"]) == ["Bütçe", "Yaşam alanı", "Kısa montaj", "Fark etmez"]
    assert not c1["alan"].get("required") and not c1["en"].get("required") and not c1["boy"].get("required")
    assert "pano" not in json.dumps(e1, ensure_ascii=False).lower()          # varsayım 1: çelikte ölçü pano katına yuvarlanmaz
    assert list(c2) == ["kaplama", "cati_rengi", "dis_duvar", "ic_duvar", "pencere_rengi", "ek", "musteri", "il", "ilce", "not", "dosya"]
    assert [c2[a]["label"] for a in c2] == ["Çatı kaplaması", "Çatı rengi", "Dış duvar", "İç duvar", "Pencere rengi", "Ek istekler",
                                            "Müşteri / proje adı", "Teslim ili", "Teslim ilçesi", "Not", "Çizim ya da plan"]
    assert yazilar(c2["kaplama"]) == ["Tek kat panel (standart)", "Sandviç panel", "Kiremit desen sac + OSB", "Trapez sac", "Trapez sac + OSB",
                                      "Shingle + OSB"]
    assert yazilar(c2["cati_rengi"]) == ["Antrasit gri (standart)", "Kırmızı (RAL 3009)"]
    assert yazilar(c2["dis_duvar"]) == ["80 mm karkas (standart)", "140 mm karkas"]
    assert yazilar(c2["ic_duvar"]) == ["Alçıpan + 80 mm (standart)", "OSB'li iç duvar"]       # "karkas" sözü 30 karaktere sığmadı
    assert yazilar(c2["pencere_rengi"]) == ["Beyaz (standart)", "Antrasit gri"]
    assert yazilar(c2["ek"]) == ["Çatıda çift kat yalıtım"] and "init-value" not in c2["ek"]
    for alan, (izinli, _anahtar) in TF.C_OZELLIKLER.items():
        assert ids(c2[alan]) == list(izinli), alan
        assert c2[alan]["init-value"] == TF.C_STANDART[alan] and c2[alan]["required"] is True       # standartlar seçili gelir
        assert [("(standart)" in x["title"]) for x in c2[alan]["data-source"]] == [x["id"] == TF.C_STANDART[alan] for x in c2[alan]["data-source"]]
    assert set(TF.C_STANDART) == set(TF.C_OZELLIKLER) == set(TF.C_OZELLIK_ADI) and ids(c2["ek"]) == list(TF.C_EK)
    yazi = json.dumps(TF.tanim("celik"), ensure_ascii=False).lower()
    assert all(x not in yazi for x in ("ısıtma", "veranda", "yükseklik", "beşik", "kırma", "prefabrik"))
    assert "yapi" not in c1 and "cati" not in c1 and "yukseklik" not in c2 and "tavan" not in c2


def test_standartlar_kural_kitabiyla_ayni():
    """Çatı kaplaması standardı kitabın baz paketi (Lokman, 4 Ekim 2026: tek kat panel); altı seçenek kitabın altı kaplaması; dış duvar
    seçenekleri kitabın DIS-80 (baz) ve DIS-140 tipleri; pafta tablosuna yazılan satır adı çelik şablonunun satırı."""
    k = json.loads((KOK / "kurallar" / "liste" / "kurallar.json").read_text(encoding="utf-8"))
    assert k["baz_paket_cati_kaplamasi"]["deger"] == "tek_kat_panel" and TF.C_STANDART["kaplama"] == "tek_kat"
    from motor.genel import girdi_genel as GG
    kitap = next(v for v in vars(GG).values() if isinstance(v, dict) and "osb_shingle" in v and "tek_kat_panel" in v)
    assert len(kitap) == len(TF.C_KAPLAMA) == 6
    tipler = json.dumps(json.loads((KOK / "kurallar" / "model" / "duvar_tipleri.json").read_text(encoding="utf-8")))
    assert "DIS-80" in tipler and "DIS-140" in tipler and list(TF.C_DIS_DUVAR) == ["80", "140"]
    assert (KOK / "kurallar" / "model" / "secenekler" / "dis_karkas_140.json").is_file()
    anahtarlar = {a for _i, a in TF.C_OZELLIKLER.values() if a}
    assert celik.satir_adi("Çatı Kaplama Rengi") == "Çatı Kaplama Rengi" and "Çatı Kaplama Rengi" not in celik.HESAPLANAN_SATIRLAR
    assert {"Çatı Kaplaması", "İç Duvarlar"} <= anahtarlar & celik.HESAPLANAN_SATIRLAR       # çizimden hesaplanır: seçim özel isteğe gider
    assert TF.C_OZELLIKLER["dis_duvar"][1] is None                                           # talebe yazılmaz, çizime işlenir


# ─── cevabın çözümü, ölçü ve talep ───
def test_cevap_ozeti_token_ve_form():
    oz = _cevap(alan=88)
    assert (oz["tur"], oz["form"], oz["token"]) == ("talep", "celik", "cf:abc123")
    assert oz["alanlar"] == {"kat": "1", "oda": "2+1", "oncelik": "butce", **STD, "alan": 88.0}
    assert TF.celik_tokeni("abc") == "cf:abc" and TF.celik_tokeni("abc", taslaktan=True) == "cf:abc:1"
    assert TF.TOKEN.match("cf:abc:1").group(3) == "1" and TF.TOKEN_FORMU == {"pf": "prefabrik", "cf": "celik"}
    # tanınmayan değer atılır; prefabrik formun seçenekleri çelik formda geçmez (ve tersi)
    oz = _cevap(kaplama="tugla", dis_duvar="160", ic_duvar="60", yukseklik="280", tavan="ters", ek=["lata", "cift_yalitim"], oncelik="hiz")
    a = oz["alanlar"]
    assert all(x not in a for x in ("kaplama", "dis_duvar", "ic_duvar", "yukseklik", "tavan", "oncelik")) and a["ek"] == ["cift_yalitim"]
    pf = TF.cevap_ozeti(json.dumps({"flow_token": "pf:abc123", "kat": "1", "oda": "2+1", "dis_duvar": "140", "kaplama": "osb_trapez"}))
    assert pf["form"] == "prefabrik" and "dis_duvar" not in pf["alanlar"] and "kaplama" not in pf["alanlar"]
    # ilk form ve verandasız form aynen: `form` alanı yok
    assert "form" not in TF.cevap_ozeti(json.dumps({"flow_token": "tf:abc123", "yapi": "celik", "kat": "1", "oda": "2+1"}))


def test_olcu_yuvarlanmaz_tek_kenar_ve_m2():
    # iki kenar: bayinin ölçüsü aynen; alan kenarların çarpımı
    oz = _cevap(en=8, boy="11,5", alan=90)
    assert TF.celik_olcusu(oz) == {"en_m": 8.0, "boy_m": 11.5, "hesaplanan": None} and TF.celik_alani(oz) == 92.0
    assert TF.celik_olcusu(_cevap(en=11.5, boy=8))["en_m"] == 8.0                                 # sıra önemli değil
    # tek kenar + m²: öteki kenar m² ÷ kenar; alan bayinin m²'si
    oz = _cevap(en=8, alan=88)
    assert TF.celik_olcusu(oz) == {"en_m": 8.0, "boy_m": 11.0, "hesaplanan": "uzun"} and TF.celik_alani(oz) == 88.0
    oz = _cevap(boy=12, alan=88)
    assert TF.celik_olcusu(oz) == {"en_m": 7.33, "boy_m": 12.0, "hesaplanan": "kisa"}
    assert TF.celik_olcusu(_cevap(en=800, alan=88))["en_m"] == 8.0                                # santimetre yazılmış
    # yalnız m², yalnız tek kenar, saçma ölçü: ölçü uydurulmaz
    assert TF.celik_olcusu(_cevap(alan=88)) is None and TF.celik_alani(_cevap(alan=88)) == 88.0
    assert TF.celik_olcusu(_cevap(en=8)) is None and TF.celik_alani(_cevap(en=8)) is None
    assert TF.celik_olcusu(_cevap(en=30, alan=20)) is None                                        # öteki kenar 1 m'den kısa
    assert TF.celik_olcusu(TF.cevap_ozeti(json.dumps({"flow_token": "pf:abc123", "en": 8, "boy": 11}))) is None   # yalnız çelik form
    assert TF.prefabrik_olcusu(_cevap(en=8, boy=11)) is None                                      # çelik form pano hesabına girmez


def test_talep_llmsiz():
    t = TF.talep(_cevap(alan=88))
    Talep.model_validate(t)
    assert t == {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "Çelik, tek kat, 2+1, 88 m²", "yapi_turu": "celik", "kat_sayisi": 1,
                 "oda_programi": "2+1", "alan_m2": 88.0, "bina_ozellikleri": {"Çatı Kaplama Rengi": "antrasit gri"}}
    assert "pano" not in t and "veranda" not in t and "cati" not in t                             # çatı şekli ve veranda formda yok
    t = TF.talep(_cevap(en=8, boy=11, kaplama="sandvic", cati_rengi="kirmizi", dis_duvar="140", ic_duvar="osb", pencere_rengi="antrasit",
                        ek=["cift_yalitim"], musteri="Ali Veli 0532 111 22 33", il="Bursa", ilce="Nilüfer", **{"not": "teras olsun"}))
    Talep.model_validate(t)
    assert t["dis_olcu"] == {"en_m": 8.0, "boy_m": 11.0} and t["alan_m2"] == 88.0
    assert t["bina_ozellikleri"] == {"Çatı Kaplaması": "sandviç panel", "Çatı Kaplama Rengi": "kırmızı (RAL 3009)", "İç Duvarlar": "OSB'li iç duvar",
                                     "Pencere Rengi": "antrasit gri", "Ek İstekler": "çatıda çift kat yalıtım"}
    assert "0532" not in json.dumps(t) and t["musteri"]["sevk_adresi"] == "Nilüfer, Bursa" and t["ozel_istekler"] == ["teras olsun"]
    # zarf: renk pafta tablosuna; hesaplanan satırlar ve tabloda olmayanlar özel isteğe (`beyin/celik.zarf`)
    oz, kalan = celik.ozellikleri_esle(t["bina_ozellikleri"])
    assert oz == {"Çatı Kaplama Rengi": "kırmızı (RAL 3009)"}
    assert kalan == ["Çatı Kaplaması: sandviç panel", "İç Duvarlar: OSB'li iç duvar", "Pencere Rengi: antrasit gri",
                     "Ek İstekler: çatıda çift kat yalıtım"]
    # boş form: yalnız yapı tipi
    bos = TF.talep(TF.cevap_ozeti(json.dumps({"flow_token": "cf:abc123"})))
    assert bos == {"niyet": "yeni_talep", "guven": "yuksek", "ozet": "Çelik", "yapi_turu": "celik"}


def test_ozet_baslik_ve_bayiye_not():
    oz = _cevap(en=8, alan=88, dis_duvar="140")
    assert TF.metin(oz) == "Talep formu: çelik, tek kat, 2+1, 8 × 11 m, yaklaşık 88 m², dış duvar 140 mm karkas."
    assert TF.set_basligi(oz) == "Çelik, tek kat, 2+1, 88 m²"
    assert TF.celik_notu(oz) == "Uzun kenarı m²'den hesapladım: 8 × 11 m. Dış duvar 140 mm karkas seçtiniz; çizime işlenir."
    assert TF.celik_notu(oz, cizim=False) == "Uzun kenarı m²'den hesapladım: 8 × 11 m. Standart dışı seçimlerinizi aldım: dış duvar 140 mm karkas."
    oz = _cevap(alan=88, kaplama="kiremit", dis_duvar="140", ek=["cift_yalitim"])
    assert TF.celik_notu(oz) == ("Standart dışı seçimlerinizi aldım: çatı kaplaması kiremit desen sac + OSB, dış duvar 140 mm karkas, "
                                 "çatıda çift kat yalıtım. Çizime yalnız dış duvar 140 mm karkas işlenir.")
    oz = _cevap(alan=88, pencere_rengi="antrasit", oncelik="montaj")
    assert TF.celik_notu(oz) == ("Standart dışı seçimlerinizi aldım: pencere rengi antrasit gri. Bu seçimler çizimi değiştirmez. "
                                 "Çelik planlarda kısa montaj sıralaması yok.")
    assert TF.celik_notu(_cevap(alan=88)) == "" and TF.celik_notu(_cevap(en=8, boy=11)) == ""       # söylenecek şey yoksa not yok
    assert TF.celik_notu({"form": "prefabrik", "alanlar": {"dis_duvar": "140"}}) == ""
    assert TF.olcu_notu(_cevap(en=8, boy=11)) == ""                                               # prefabrik notu çelik forma yazılmaz
    for cumle in re.split(r"(?<=\.) ", TF.celik_notu(_cevap(en=8, alan=88, kaplama="kiremit", dis_duvar="140", oncelik="montaj"))):
        assert len(cumle.split()) <= 20, cumle                                                    # D-70: açıklama cümlesi en çok 20 kelime


def test_oncelik_ve_dis140():
    assert TF.celik_onceligi(_cevap(oncelik="butce")) == "butce" and TF.celik_onceligi(_cevap(oncelik="yasam")) == "yasam"
    assert TF.celik_onceligi(_cevap(oncelik="montaj")) == "yok" and TF.celik_onceligi(_cevap(oncelik="yok")) == "yok"
    assert TF.celik_onceligi(TF.cevap_ozeti(json.dumps({"flow_token": "cf:abc123"}))) is None
    assert TF.oncelik(_cevap()) is None and TF.celik_onceligi({"form": "prefabrik", "alanlar": {"oncelik": "butce"}}) is None
    assert TF.celik_dis140(_cevap(dis_duvar="140")) is True and TF.celik_dis140(_cevap()) is False
    # çelik adaylarda bütçe ve yaşam alanı sıralamasının ölçüsü var (kapalı alan, oda alanları); pano sayısı yok (kısa montaj ölçülmez)
    adaylar = [a for a in json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8")) if a.get("yapi_turu") == "celik"]
    assert adaylar and all(a.get("kapali_m2") and (a.get("ozet") or {}).get("odalar") for a in adaylar)
    assert not any((a.get("ozet") or {}).get("pano") for a in adaylar)
    sirali = SC.puanla(adaylar[:3], {"alan_m2": adaylar[0]["katalog_m2"], "oncelik": "yok"})
    assert not any("önceliği" in a["hesap"] for a in sirali)


# ─── form izi taslakta, dış duvar 140 mm karkas çizime ───
def _konusma(tmp_path, taslak: dict | None = None) -> Konusma:
    kok = tmp_path / f"durum{len(list(tmp_path.iterdir()))}"                  # her çağrı yeni konuşma (önceki plan karışmasın)
    kok.mkdir()
    k = Konusma("905550000001", kok)
    k.d["taslak"].update(taslak or {})
    return k


def test_form_izi_taslakta(tmp_path):
    k = _konusma(tmp_path, {"olcu_formdan": True, "form": "prefabrik"})
    k.celik_formu = {"oncelik": "yasam", "dis140": True}
    KR._form_izi(k, Talep.model_validate(TF.talep(_cevap(alan=88, dis_duvar="140"))))
    ts = k.d["taslak"]
    assert ts["form"] == "celik" and ts["oncelik"] == "yasam" and ts["form_dis140"] is True and "olcu_formdan" not in ts
    assert k.celik_formu is None
    # aynı taslağa ikinci form 80 mm ile gelirse seçim kalkar; prefabrik form da kaldırır
    k.celik_formu = {"oncelik": "yok", "dis140": False}
    KR._form_izi(k, Talep.model_validate(TF.talep(_cevap(alan=88))))
    assert "form_dis140" not in ts and ts["oncelik"] == "yok"
    ts["form_dis140"] = True
    k.prefabrik_formu = {"oncelik": "butce"}
    KR._form_izi(k, Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "x"}))
    assert ts["form"] == "prefabrik" and "form_dis140" not in ts


def _celik_adayi(kod: str) -> dict:
    [a] = [a for a in json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8")) if a["kod"] == kod]
    return a


def _plan(tmp_path, kod: str, taslak: dict):
    from beyin.katalog import Katalog
    k = _konusma(tmp_path, {"yapi_turu": "celik", "oda_programi": "2+1", "alan_m2": 88.0, **taslak})
    k.d["son_metin"] = ""
    return k, KR._celik_is_emri_uret(k, {"kod": "TEST", "ad": "Test Bayi"}, Katalog(), _celik_adayi(kod), k.d["taslak"])


def test_formdaki_dis_140_ilk_planda_cizime_islenir(tmp_path):
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_dis140": True})
    assert kr.eylem == "is_emri" and [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["dis_karkas_140"]
    assert [d["op"] for d in kr.is_emri["yapi"]["bu_revizyon"]] == ["dis_karkas_140"]
    assert "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm)." in kr.mesaj and "işlenemedi" not in kr.mesaj
    t = celik.tanim_oku(_celik_adayi("Ç8801"))
    assert KR._zaten_140(varyant.tanim_uygula(t, kr.is_emri["yapi"]["degisiklikler"][0]), []) and not KR._zaten_140(t, [])
    # seçim yoksa, form çelik değilse ya da model zaten 140'lıksa işlem eklenmez (bugünkü plan aynen)
    for kod, taslak in (("Ç8801", {"form": "celik"}), ("Ç8801", {"form_dis140": True}), ("Ç8801", {}), ("KT03", {"form": "celik", "form_dis140": True})):
        k, kr = _plan(tmp_path, kod, taslak)
        assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [] and "Uygulanan" not in kr.mesaj, (kod, taslak)


def test_formdaki_dis_140_uygulanamayan_modelde_plan_dusmez(tmp_path):
    """Karkas modeli olan KT evinde dış 140 otomatik uygulanamaz (sohbette yazılınca yönlendirilir). Formdaki seçim planı düşürmez: plan
    modelin kendi duvarıyla çizilir, seçim özel isteğe yazılır, bayiye söylenir."""
    t = celik.tanim_oku(_celik_adayi("KT01"))
    try:
        varyant.tanim_uygula(t, {"op": "dis_karkas_140"})
        raise AssertionError("KT-01'de dış 140 uygulanabiliyor; test varsayımı değişti")
    except varyant.VaryantHatasi:
        pass
    k, kr = _plan(tmp_path, "KT01", {"form": "celik", "form_dis140": True})
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == []
    assert "Dış duvar 140 mm karkas bu plana otomatik işlenemedi." in kr.mesaj and "isteğiniz talebe yazıldı" in kr.mesaj
    assert "Dış duvar: 140 mm karkas (formdan; çizime işlenemedi)" in kr.is_emri["bilgi"]["ozel_istekler"]
    assert "form_dis140" not in k.d["taslak"]


def test_gorunur_celik_adaylarda_dis_140_ya_islenir_ya_soylenir():
    """Bankadaki her çelik adayda formdaki dış 140 seçimi ya çizime işlenir ya da açıkça söylenir; üçüncü yol (istisna, sessiz düşme) yok."""
    for a in json.loads((KOK / "beyin" / "veri" / "adaylar.json").read_text(encoding="utf-8")):
        if a.get("yapi_turu") != "celik" or not celik.tanim_dogrula(a):
            continue
        t = celik.tanim_oku(a)
        if KR._zaten_140(t, []):
            continue
        try:
            assert KR._zaten_140(varyant.tanim_uygula(t, {"op": "dis_karkas_140"}), []), a["kod"]
        except varyant.VaryantHatasi:
            pass


# ─── hangi form sunulur ───
def test_hangi_form_sunulur():
    assert "celik_flow_id" not in AY.VARSAYILAN["talep_formu"]
    celik_ts = {"yapi_turu": "celik", "oda_programi": "2+1"}
    # kimlik ayarda yok: bugünkü yol (ilk form); davranış aynı
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, AYAR_PF)[0] == "talep"
    assert W.form_kimligi(AYAR_PF, "celik") is None and W.form_kimligi(AYAR_CF, "celik") == "5555555555"
    # kimlik var, yapı tipi çelik (taslak ya da bayi kartı): çelik talep formu
    for bayi, taslak in ((None, celik_ts), ({"varsayilanlar": {"yapi_turu": "celik"}}, None)):
        fs = W.talep_formu_sunusu(GELEN, bayi, taslak, AYAR_CF)
        assert fs[0] == "celik" and fs[1].startswith("cf:") and fs[1].endswith(":1") == (taslak is not None)
        assert fs[2] == TF.celik_ekran_verisi(bayi, taslak) and "yapi" not in fs[2] and "veranda" not in fs[2]
        satir = W.form_satiri(GELEN, "Talebinizi formla iletin.", fs, AYAR_CF)
        p = satir["interactive"]["action"]["parameters"]
        assert p["flow_id"] == "5555555555" and p["flow_action_payload"]["screen"] == "TALEP_C" and p["flow_cta"] == "Talep formu"
        assert set(p["flow_action_payload"]["data"]) == set(TF.tanim("celik")["screens"][0]["data"])
        M.mesaj_yuku(satir, "905550000001")
    assert W.talep_formu_sunusu(GELEN, None, {**celik_ts, "alan_m2": 88}, AYAR_CF)[2]["alan"] == "88"
    # verandasız formun kimliği de varsa çelikte çelik formu önce gelir; prefabrik ve bilinmeyen yapı tipi aynen
    hepsi = {**AYAR_CF, "talep_formu": {**AYAR_CF["talep_formu"], "talep2_flow_id": "4444444444"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, hepsi)[0] == "celik"
    assert W.talep_formu_sunusu(GELEN, None, {"yapi_turu": "prefabrik"}, hepsi)[0] == "prefabrik"
    assert W.talep_formu_sunusu(GELEN, None, None, hepsi)[0] == "yapi_sor"
    # prefabrik formun kimliği yokken (yapı tipi düğmeleri yok) çelik formu sunulmaz: ilk formun yolu
    yalniz = {**AYAR_V1, "talep_formu": {**AYAR_V1["talep_formu"], "celik_flow_id": "5555555555"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, yalniz)[0] == "talep"
    # bozuk kimlik sunulmaz
    bozuk = {**AYAR_PF, "talep_formu": {**AYAR_PF["talep_formu"], "celik_flow_id": "12a"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, bozuk)[0] == "talep"
    assert W.YAPI_FORM_METNI["celik"] == "Çelik talep formunu doldurun. İsterseniz talebinizi yazın."
