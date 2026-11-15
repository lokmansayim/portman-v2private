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
    assert TF.celik_notu(oz) == ("Uzun kenarı m²'den hesapladım: 8 × 11 m. Dış duvar 140 mm karkas seçtiniz. Çizime işlerim. "
                                 "İşleyemezsem plan mesajında yazarım.")       # PR-10: plan seçilmeden kesin söz verilmez (canlı C6)
    assert TF.celik_notu(oz, cizim=False) == "Uzun kenarı m²'den hesapladım: 8 × 11 m. Standart dışı seçimlerinizi aldım: dış duvar 140 mm karkas."
    oz = _cevap(alan=88, kaplama="osb_trapez", dis_duvar="140", ek=["cift_yalitim"])      # Motor'un hesaplamadığı kaplama (D-97)
    assert TF.celik_notu(oz) == ("Standart dışı seçimlerinizi aldım: çatı kaplaması trapez sac + OSB, dış duvar 140 mm karkas, "
                                 "çatıda çift kat yalıtım. Çizime yalnız dış duvar 140 mm karkası işlerim. "
                                 "İşleyemezsem plan mesajında yazarım.")
    oz = _cevap(alan=88, pencere_rengi="antrasit", oncelik="montaj")
    assert TF.celik_notu(oz) == ("Standart dışı seçimlerinizi aldım: pencere rengi antrasit gri. Bu seçimler çizimi değiştirmez. "
                                 "Çelik planlarda kısa montaj sıralaması yok.")
    assert TF.celik_notu(_cevap(alan=88)) == "" and TF.celik_notu(_cevap(en=8, boy=11)) == ""       # söylenecek şey yoksa not yok
    assert TF.celik_notu({"form": "prefabrik", "alanlar": {"dis_duvar": "140"}}) == ""
    assert TF.olcu_notu(_cevap(en=8, boy=11)) == ""                                               # prefabrik notu çelik forma yazılmaz
    # formla gelen dosya plan olarak okunduysa (çizim esas) seçimler plana işlenmez; bayiye söylenir
    assert TF.celik_cizim_notu(_cevap(alan=88, kaplama="kiremit", dis_duvar="140")) == (
        "Formdaki standart dışı seçimlerinizi plana işlemedim: çatı kaplaması kiremit desen sac + OSB, dış duvar 140 mm karkas. "
        "Planı gördükten sonra değişiklik olarak yazabilirsiniz.")
    assert TF.celik_cizim_notu(_cevap(alan=88)) == "" and TF.celik_cizim_notu({"form": "prefabrik", "alanlar": {"dis_duvar": "140"}}) == ""
    for kap in ("kiremit", "osb_trapez", "shingle"):
        for cumle in re.split(r"(?<=\.) ", TF.celik_notu(_cevap(en=8, alan=88, kaplama=kap, dis_duvar="140", oncelik="montaj"))):
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
    # form yeniden gelince formun yazdığı satırlarda son form geçerli: standarda dönen seçimin eski değeri taslakta kalmaz;
    # formun yazmadığı satır (bayinin sohbette yazdığı) ve bu formda yine seçilen satır kalır
    assert set(TF.celik_anahtarlari()) == {"Çatı Kaplaması", "Çatı Kaplama Rengi", "İç Duvarlar", "Pencere Rengi", "Ek İstekler"}
    ilk = Talep.model_validate(TF.talep(_cevap(alan=88, kaplama="kiremit", pencere_rengi="antrasit", cati_rengi="kirmizi", ek=["cift_yalitim"])))
    k.birlestir(ilk.model_dump())
    ts["bina_ozellikleri"]["Zemin"] = "laminat"
    k.celik_formu = {"oncelik": "yok", "dis140": False, "anahtarlar": TF.celik_anahtarlari()}
    KR._form_izi(k, ilk)
    assert ts["bina_ozellikleri"] == {"Çatı Kaplaması": "kiremit desen sac + OSB", "Çatı Kaplama Rengi": "kırmızı (RAL 3009)",
                                      "Pencere Rengi": "antrasit gri", "Ek İstekler": "çatıda çift kat yalıtım", "Zemin": "laminat"}
    ikinci = Talep.model_validate(TF.talep(_cevap(alan=88, pencere_rengi="antrasit")))
    k.birlestir(ikinci.model_dump())
    k.celik_formu = {"oncelik": "yok", "dis140": False, "anahtarlar": TF.celik_anahtarlari()}
    KR._form_izi(k, ikinci)
    assert ts["bina_ozellikleri"] == {"Çatı Kaplama Rengi": "antrasit gri", "Pencere Rengi": "antrasit gri", "Zemin": "laminat"}
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
    # PR-10 (canlı C5): PDF başlığının metninde model adı ve m² düşmez; "Uygulanan" ondan sonra gelir
    assert kr.is_emri["talep"]["metin"] == "Ç8801 (Beşik + cumba) · 88 m², 2+1. Uygulanan: dış duvarlar 140'lık karkas (16,5 cm)."
    t = celik.tanim_oku(_celik_adayi("Ç8801"))
    assert KR._zaten_140(varyant.tanim_uygula(t, kr.is_emri["yapi"]["degisiklikler"][0]), []) and not KR._zaten_140(t, [])
    # seçim yoksa, form çelik değilse ya da model zaten 140'lıksa işlem eklenmez (bugünkü plan aynen)
    for kod, taslak in (("Ç8801", {"form": "celik"}), ("Ç8801", {"form_dis140": True}), ("Ç8801", {}), ("KT03", {"form": "celik", "form_dis140": True})):
        k, kr = _plan(tmp_path, kod, taslak)
        assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [] and "Uygulanan" not in kr.mesaj, (kod, taslak)
        assert "140 mm karkastır" not in kr.mesaj, (kod, taslak)
    # formda 80 mm (standart) kaldı ama seçilen model zaten 140'lık (KT-03): bayiye söylenir; form çelik değilse bugünkü metin
    k, kr = _plan(tmp_path, "KT03", {"form": "celik"})
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [] and "Bu planın dış duvarı 140 mm karkastır. Ön onay" in kr.mesaj
    assert "140 mm karkastır" not in _plan(tmp_path, "KT03", {})[1].mesaj


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
    assert ("Dış duvar 140 mm karkası bu plana otomatik işleyemedim. Planı modelin kendi dış duvarıyla çizdim. İsteğinizi talebe yazdım. "
            "Ön onay planınız hazır") in kr.mesaj
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
    # prefabrik formun kimliği yokken de (yapı tipi düğmeleri yok) yapı tipi çelik olan bayiye çelik formu sunulur; ötekiler ilk formun yolu
    yalniz = {**AYAR_V1, "talep_formu": {**AYAR_V1["talep_formu"], "celik_flow_id": "5555555555"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, yalniz)[0] == "celik"
    assert W.talep_formu_sunusu(GELEN, None, {"yapi_turu": "prefabrik"}, yalniz)[0] == "talep"
    assert W.talep_formu_sunusu(GELEN, None, None, yalniz)[0] == "talep"
    # bozuk kimlik sunulmaz
    bozuk = {**AYAR_PF, "talep_formu": {**AYAR_PF["talep_formu"], "celik_flow_id": "12a"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, bozuk)[0] == "talep"
    assert W.YAPI_FORM_METNI["celik"] == "Çelik talep formunu doldurun. İsterseniz talebinizi yazın."


# ─── İE-20 PR-10 · 15 Kasım 2026 canlı denemesinin gözlemleri (v2026.11.15a; PF `WhatsApp_Denetim_celik-formu_v2026.11.15a.md`) ───
def test_yaziyla_secimde_secim_cumlesi_ozel_istege_girmez(tmp_path):
    """Gözlem 1: "KT-02 olsun" yazınca LLM cümleyi özel istek diye de yazıyordu; paftanın özel isteklerinde "KT-02 olsun" çıkıyordu.
    Hedef: yalnız model kodu ve seçim sözcüğü taşıyan özel istek taslağa yazılmaz; düğmeyle seçimle aynı pafta."""
    from beyin.katalog import Katalog
    kat = Katalog()
    k = _konusma(tmp_path)
    t = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "x",
                              "ozel_istekler": ["KT-02 olsun", "KT-03 olsun.", "Ç8801 istiyorum", "KT-02 olsun, zemin laminat", "zemin laminat olsun"]})
    assert KR._secim_kopyasini_birak(k, t, kat).ozel_istekler == ["KT-02 olsun, zemin laminat", "zemin laminat olsun"]
    temiz = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "x", "ozel_istekler": ["zemin laminat olsun"]})
    assert KR._secim_kopyasini_birak(k, temiz, kat) is temiz
    # karar katmanında: çelik formdan sonra yazıyla seçim (LLM'in canlıdaki çıkarımı gibi) → paftanın özel isteklerinde seçim cümlesi yok
    k = _konusma(tmp_path, {"yapi_turu": "celik", "oda_programi": "2+1", "alan_m2": 88.0, "form": "celik"})
    t = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "KT-02 seçildi", "katalog_kodu": "KT02",
                              "ozel_istekler": ["KT-02 olsun"]})
    kr = KR.karar_ver(t, k, {"kod": "TEST", "ad": "Test Bayi"}, kat, metin="KT-02 olsun")
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["kod"] == "KT02", kr
    assert kr.is_emri["bilgi"]["ozel_istekler"] == [] and "ozel_istekler" not in {a for a, v in k.d["taslak"].items() if v}
    assert kr.mesaj == "KT-02 · 92 m², 2+1. Ön onay planınız hazır; plan görseli ve PDF ektedir."
    assert kr.is_emri["talep"]["metin"] == "KT-02 · 92 m², 2+1"                                    # PDF başlığının metni


def test_neyi_degistirelim_yalniz_bu_planda_yapilabilen_ornekler(tmp_path):
    """Gözlem 4: KT-03'te [Revize et] cevabı "çatı K ya da çatı L" ve "dışlar 140'lık olsun" öneriyordu; KT-03'ün çatı seçeneği yok,
    dış duvarı zaten 140 mm. Hedef: çatı örneği yalnız çatı seçeneği olan modelde, dış 140 örneği yalnız uygulanabilen planda."""
    from beyin.katalog import Katalog
    kat = Katalog()
    yalin = "Neyi değiştirelim? Odayı ve pencere ölçüsünü yazın (örn. \"mutfak penceresi 120x120\")"
    hedef = {"Ç8801": KR._NEYI_DEGISTIRELIM, "Ç8801K": KR._NEYI_DEGISTIRELIM, "Ç8801L": KR._NEYI_DEGISTIRELIM,
             "Ç8201": yalin + "; dış duvar için \"dışlar 140'lık olsun\" yazabilirsiniz.",
             "KT01": yalin + ".", "KT02": yalin + ".", "KT03": yalin + "."}
    assert KR._NEYI_DEGISTIRELIM == yalin + "; çatı için \"çatı K\" ya da \"çatı L\", dış duvar için \"dışlar 140'lık olsun\" yazabilirsiniz."
    for kod, metin in hedef.items():
        a = _celik_adayi(kod)
        assert KR._celik_ornekleri(kat, a, celik.tanim_oku(a), []) == metin, kod
    # dış 140 uygulanmış planda örnek yinelenmez (Ç8801K + form 140); çatı örneği kalır
    k, kr = _plan(tmp_path, "Ç8801K", {"form": "celik", "form_dis140": True})
    assert KR._neyi_degistirelim(k, kat) == yalin + "; çatı için \"çatı K\" ya da \"çatı L\" yazabilirsiniz."
    assert KR.dis140_onerilir(kr.is_emri["yapi"]) is False
    # [Revize et] cevabı KT-03 planında (niyet red; plan onay bekliyor)
    k, kr = _plan(tmp_path, "KT03", {"form": "celik"})
    assert KR.dis140_onerilir(kr.is_emri["yapi"]) is False and KR._neyi_degistirelim(k, kat) == yalin + "."
    k.d["asama"] = "onay_bekliyor"
    red = KR.karar_ver(Talep.model_validate({"niyet": "red", "guven": "yuksek", "ozet": "revize"}), k, {"kod": "TEST", "ad": "Test Bayi"}, kat,
                       metin="Revize et")
    assert red.eylem == "sor" and red.mesaj == "Anladım. " + yalin + ".", red
    # boş revizyon formunun cevabı (`worker.form_cikarimi`): KT-03 ve KT-02'de dış 140 örneği yok, Ç8201'de var
    for kod, var in (("KT03", False), ("KT02", False), ("Ç8201", True), ("Ç8801", True)):
        k, kr = _plan(tmp_path, kod, {"form": "celik"})
        assert KR.dis140_onerilir(kr.is_emri["yapi"]) is var, kod
        k.d["asama"] = "onay_bekliyor"
        token = f"rv:{kr.is_emri['is_emri_no']}:{kr.is_emri['revizyon']}"
        fc = W.form_cikarimi({"form": {"tur": "revizyon", "token": token, "alanlar": {"neyi": ["pencere"]}, "dosyalar": []}}, k.d)
        assert fc["durum"] == "bos", (kod, fc)
        assert fc["mesaj"] == ("Neyi nasıl değiştirelim? Kısaca yazmanız yeterli; örneğin \"mutfak penceresi 120x120\""
                               + (" ya da \"dışlar 140'lık olsun\"." if var else ".")), kod
    assert KR.dis140_onerilir(None) is False and KR.dis140_onerilir({"sistem": "celik", "tanim": "modeller/yok.json"}) is False


def test_on_not_plan_secilmeden_kesin_soz_vermez():
    """Gözlem 5 (C6): ön not "çizime işlenir" diyordu, KT-02 seçilince plan "işleyemedim" dedi. Hedef: ön not kesin söz vermez, sonucu
    plan mesajı söyler. Cümleler D-70'e göre: etken, en çok 20 kelime."""
    tek = TF.celik_notu(_cevap(alan=88, dis_duvar="140"))
    assert tek == "Dış duvar 140 mm karkas seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım."
    cok = TF.celik_notu(_cevap(alan=88, dis_duvar="140", pencere_rengi="antrasit"))
    assert cok == ("Standart dışı seçimlerinizi aldım: dış duvar 140 mm karkas, pencere rengi antrasit gri. "
                   "Çizime yalnız dış duvar 140 mm karkası işlerim. İşleyemezsem plan mesajında yazarım.")
    for not_ in (tek, cok):
        assert "işlenir" not in not_
        for cumle in re.split(r"(?<=\.) ", not_):
            assert len(cumle.split()) <= 20, cumle
    # dış 140 yoksa söz de yok; plan aynı mesajda çıktıysa (cizim=False) çizim cümlesi yazılmaz
    assert TF.celik_notu(_cevap(alan=88, pencere_rengi="antrasit")) == ("Standart dışı seçimlerinizi aldım: pencere rengi antrasit gri. "
                                                                         "Bu seçimler çizimi değiştirmez.")
    assert TF.celik_notu(_cevap(alan=88, dis_duvar="140"), cizim=False) == "Standart dışı seçimlerinizi aldım: dış duvar 140 mm karkas."


# ─── PR-11 (D-97; Lokman, kart 15 Kasım 2026 04:44:37 UTC "Plana ve listeye işlensin") · formda seçilen çatı kaplaması ───
def test_form_kaplamasi_kitabin_anahtariyla():
    """Formun altı kaplama seçeneği kural kitabının altı kaplamasıyla birebir eşlenir. Çizime işlenen: standart dışı seçilen ve genel
    motorun hesapladığı kaplama (sandviç panel; 15 Kasım 2026'dan beri kiremit desen sac + OSB, BK-33, D-98; OSB + membran + shingle,
    BK-33, D-100). Standart (tek kat panel) ve motorun hesaplamadığı iki kaplama (eski formun trapez saclı cevapları) işlenmez."""
    from motor.genel import kural
    assert set(TF.C_KAPLAMA_KITAP) == set(TF.C_KAPLAMA)
    assert set(TF.C_KAPLAMA_KITAP.values()) == set(kural.oku()["cati_kaplama"]["deger"])
    assert TF.C_KAPLAMA_KITAP[TF.C_STANDART["kaplama"]] == kural.oku()["baz_paket_cati_kaplamasi"]["deger"]
    assert TF.celik_kaplamasi(_cevap(alan=88, kaplama="sandvic")) == "sandvic_panel"
    assert TF.celik_kaplamasi(_cevap(alan=88, kaplama="kiremit")) == "osb_kiremit"
    assert TF.celik_kaplamasi(_cevap(alan=88, kaplama="shingle")) == "osb_shingle"                 # BK-33, D-100
    for v in ("tek_kat", "trapez", "osb_trapez"):
        assert TF.celik_kaplamasi(_cevap(alan=88, kaplama=v)) is None, v
    assert TF.celik_kaplamasi({"form": "prefabrik", "alanlar": {"kaplama": "sandvic"}}) is None
    assert varyant.kaplama_adi("sandvic_panel") == "sandviç panel" == TF.C_KAPLAMA["sandvic"]      # bayiye yazılan ad iki yerde aynı
    assert varyant.kaplama_adi("osb_kiremit") == "kiremit desen sac + OSB" == TF.C_KAPLAMA["kiremit"]
    assert varyant.kaplama_adi("osb_shingle") == "OSB + membran + shingle" == TF.C_KAPLAMA["shingle"]
    geri = {v: a for a, v in TF.C_KAPLAMA_KITAP.items()}
    for kap in varyant.CIZILEN_KAPLAMALAR:                                                         # işlenen her kaplamada aynı ad
        assert varyant.kaplama_adi(kap) == TF.C_KAPLAMA[geri[kap]], kap


def test_on_not_cati_kaplamasini_soyler():
    """Hedef metinler (PR-11). Çizime işlenen seçimler: dış duvar 140 mm karkas, sandviç panel ve kiremit desen sac + OSB (BK-33'ten
    beri). Dış 140'ın PR-10 metinleri aynen."""
    tek = TF.celik_notu(_cevap(alan=88, kaplama="sandvic"))
    assert tek == "Çatı kaplaması sandviç panel seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım."
    iki = TF.celik_notu(_cevap(alan=88, kaplama="sandvic", dis_duvar="140"))
    assert iki == ("Standart dışı seçimlerinizi aldım: çatı kaplaması sandviç panel, dış duvar 140 mm karkas. "
                   "Çizime işlerim. İşleyemezsem plan mesajında yazarım.")
    cok = TF.celik_notu(_cevap(alan=88, kaplama="sandvic", dis_duvar="140", pencere_rengi="antrasit"))
    assert cok == ("Standart dışı seçimlerinizi aldım: çatı kaplaması sandviç panel, dış duvar 140 mm karkas, pencere rengi antrasit gri. "
                   "Çizime yalnız dış duvar 140 mm karkası ve çatı kaplamasını işlerim. İşleyemezsem plan mesajında yazarım.")
    biri = TF.celik_notu(_cevap(alan=88, kaplama="sandvic", pencere_rengi="antrasit"))
    assert biri == ("Standart dışı seçimlerinizi aldım: çatı kaplaması sandviç panel, pencere rengi antrasit gri. "
                    "Çizime yalnız çatı kaplamasını işlerim. İşleyemezsem plan mesajında yazarım.")
    # kiremit desen sac + OSB: Motor 15 Kasım 2026'dan beri hesaplar (BK-33, D-98); aynı metinler, kaplamanın formdaki adıyla
    kir = TF.celik_notu(_cevap(alan=88, kaplama="kiremit"))
    assert kir == "Çatı kaplaması kiremit desen sac + OSB seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım."
    kir2 = TF.celik_notu(_cevap(alan=88, kaplama="kiremit", dis_duvar="140", pencere_rengi="antrasit"))
    assert kir2 == ("Standart dışı seçimlerinizi aldım: çatı kaplaması kiremit desen sac + OSB, dış duvar 140 mm karkas, "
                    "pencere rengi antrasit gri. Çizime yalnız dış duvar 140 mm karkası ve çatı kaplamasını işlerim. "
                    "İşleyemezsem plan mesajında yazarım.")
    # motorun hesaplamadığı kaplama bugünkü gibi: çizimi değiştirmez
    assert TF.celik_notu(_cevap(alan=88, kaplama="osb_trapez")) == ("Standart dışı seçimlerinizi aldım: çatı kaplaması trapez sac + OSB. "
                                                                    "Bu seçimler çizimi değiştirmez.")
    # OSB + membran + shingle: Motor 15 Kasım 2026'dan beri hesaplar (BK-33, D-100); sandviç paneldeki metinler
    assert TF.celik_notu(_cevap(alan=88, kaplama="shingle", dis_duvar="140")) == (
        "Standart dışı seçimlerinizi aldım: çatı kaplaması OSB + membran + shingle, dış duvar 140 mm karkas. "
        "Çizime işlerim. İşleyemezsem plan mesajında yazarım.")
    for not_ in (tek, iki, cok, biri, kir, kir2):
        for cumle in re.split(r"(?<=\.) ", not_):
            assert len(cumle.split()) <= 20, cumle


def test_form_izi_kaplamayi_tasir(tmp_path):
    """`form_kaplama` yalnız çelik formun mesajında yazılır; form standarda dönerse ya da prefabrik form gelirse kalkar."""
    k = _konusma(tmp_path)
    k.celik_formu = {"oncelik": "yok", "dis140": False, "kaplama": "sandvic_panel", "anahtarlar": TF.celik_anahtarlari()}
    KR._form_izi(k, Talep.model_validate(TF.talep(_cevap(alan=88, kaplama="sandvic"))))
    assert k.d["taslak"]["form"] == "celik" and k.d["taslak"]["form_kaplama"] == "sandvic_panel"
    assert k.d["taslak"]["form_kaplama_yazi"] == "sandviç panel"                                  # formun özellik satırına yazdığı değer
    k.celik_formu = {"oncelik": "yok", "dis140": False, "kaplama": None, "anahtarlar": TF.celik_anahtarlari()}
    KR._form_izi(k, Talep.model_validate(TF.talep(_cevap(alan=88))))
    assert "form_kaplama" not in k.d["taslak"] and "form_kaplama_yazi" not in k.d["taslak"]
    k.d["taslak"]["form_kaplama"] = "sandvic_panel"
    k.prefabrik_formu = {"oncelik": None}
    KR._form_izi(k, Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": ""}))
    assert k.d["taslak"]["form"] == "prefabrik" and "form_kaplama" not in k.d["taslak"]


def test_formdaki_cati_kaplamasi_ilk_planda_tanima_yazilir(tmp_path):
    """Hedef (PR-11): formda sandviç panel + seçilen plan tek kat panelli (Ç8801) → işlem `cati_kaplamasi`; mesaj ve PDF başlığı
    "Uygulanan: çatı kaplaması sandviç panel."; özel istekte kaplama yok (pafta tablosu gösterir). Dış 140 ile birlikte iki işlem."""
    bo = {"Çatı Kaplaması": "sandviç panel", "Çatı Kaplama Rengi": "antrasit gri"}
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_kaplama": "sandvic_panel", "bina_ozellikleri": dict(bo)})
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [
        {"op": "cati_kaplamasi", "kaplama": "sandvic_panel", "aciklama": "çatı kaplaması sandviç panel"}]
    assert kr.is_emri["yapi"]["uygulanan"] == ["çatı kaplaması sandviç panel"]
    assert "Uygulanan: çatı kaplaması sandviç panel. Ön onay planınız hazır" in kr.mesaj and "işleyemedim" not in kr.mesaj
    assert kr.is_emri["talep"]["metin"] == "Ç8801 (Beşik + cumba) · 88 m², 2+1. Uygulanan: çatı kaplaması sandviç panel."
    assert kr.is_emri["bilgi"]["ozel_istekler"] == [] and kr.is_emri["bilgi"]["ozellikler"] == {"Çatı Kaplama Rengi": "antrasit gri"}
    t0 = celik.tanim_oku(_celik_adayi("Ç8801"))
    t1 = varyant.tanim_uygula(t0, kr.is_emri["yapi"]["degisiklikler"][0])
    assert varyant.kaplama_oku(t0) == "tek_kat_panel" and varyant.kaplama_oku(t1) == "sandvic_panel"
    assert {a: v for a, v in t1.items() if a != "cati"} == {a: v for a, v in t0.items() if a != "cati"}     # geometri aynen
    # dış 140 ile birlikte: önce dış 140, sonra kaplama
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_dis140": True, "form_kaplama": "sandvic_panel", "bina_ozellikleri": dict(bo)})
    assert [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["dis_karkas_140", "cati_kaplamasi"]
    assert "Uygulanan: dış duvarlar 140'lık karkas (16,5 cm); çatı kaplaması sandviç panel." in kr.mesaj
    # plan zaten sandviç panelli (KT-02): işlem yok, özel istek yok, "Uygulanan" yok
    k, kr = _plan(tmp_path, "KT02", {"form": "celik", "form_kaplama": "sandvic_panel", "bina_ozellikleri": dict(bo)})
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [] and "Uygulanan" not in kr.mesaj
    assert kr.is_emri["bilgi"]["ozel_istekler"] == []
    # form çelik değilse ya da seçim yoksa bugünkü plan aynen; formda standart kaldıysa plan modelin kendi kaplamasıyla (VARSAYIM)
    for kod, taslak in (("Ç8801", {"form_kaplama": "sandvic_panel"}), ("Ç8801", {"form": "celik"}), ("KT02", {"form": "celik"})):
        k, kr = _plan(tmp_path, kod, taslak)
        assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [] and "kaplama" not in kr.mesaj, (kod, taslak)
    # OSB + membran + shingle: Motor 15 Kasım 2026'dan beri hesaplar (BK-33, D-100); sandviç paneldeki gibi işlem olur
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_kaplama": "osb_shingle", "form_kaplama_yazi": "OSB + membran + shingle",
                                      "bina_ozellikleri": {"Çatı Kaplaması": "OSB + membran + shingle"}})
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [
        {"op": "cati_kaplamasi", "kaplama": "osb_shingle", "aciklama": "çatı kaplaması OSB + membran + shingle"}]
    assert "Uygulanan: çatı kaplaması OSB + membran + shingle. Ön onay planınız hazır" in kr.mesaj and kr.is_emri["bilgi"]["ozel_istekler"] == []
    # motorun hesaplamadığı kaplama (eski formun trapez sac + OSB cevabı) taslağa `form_kaplama` diye girse bile (olmaması gerekir) plan düşmez,
    # bayiye söylenir (önceki örnek shingle'dı; BK-33 D-100'le hesaplanır oldu)
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_kaplama": "osb_trapez", "form_kaplama_yazi": "trapez sac + OSB",
                                      "bina_ozellikleri": {"Çatı Kaplaması": "trapez sac + OSB"}})
    assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == []
    assert kr.is_emri["bilgi"]["ozel_istekler"] == ["Çatı kaplaması: osb+nem bariyeri+trapez saç (formdan; çizime işlenemedi)"]
    assert ("Çatı kaplaması osb+nem bariyeri+trapez saç seçiminizi bu plana otomatik işleyemedim. Planı modelin kendi çatı kaplamasıyla çizdim. "
            "İsteğinizi talebe yazdım. Ön onay") in kr.mesaj


_BASKA_NOTU = ("Formda çatı kaplaması sandviç panel seçtiniz. Mesajınızda başka bir kaplama yazdınız. Planı modelin kendi çatı kaplamasıyla "
               "çizdim. Yazdığınız kaplamayı talebe yazdım. Ön onay planınız hazır")
_KAP_ORTAK = {"form": "celik", "form_kaplama": "sandvic_panel", "form_kaplama_yazi": "sandviç panel"}


def test_kaplama_kiyasi_genis_desen():
    """Geometri hakemi (PR-11, ikinci ve üçüncü tur): kıyas dar eşleşmeyle değil geniş desenle, sözcük kökleriyle. "ayni" yalnız
    kaplamanın adı; "baska" başka bir çatı malzemesini anan her yazım ve tablonun "Çatı Kaplaması" satırına yazılmış, seçilen kaplamayı
    anmayan her değer; "ek" başka malzeme anmayan her şey (kalınlık, ek, yabancı yazım: seçim işlenir, söz özel istekte kalır)."""
    kiyas = lambda d, **kw: KR._kaplama_kiyasi(d, "sandvic_panel", ("sandviç panel",), **kw)               # noqa: E731
    for d in ("sandviç panel", "Sandviç Panel", "SANDVİÇ PANEL", "sandviç", "Sandviç"):
        assert kiyas(d) == kiyas(d, satir=True) == "ayni", d
    for d in ("sandviç panel 5 cm", "sandviç paneli", "sandviç panel olsun", "5 cm sandviç panel", "sandviç panel (kırmızı)",
              "sandviç çatı paneli", "sandwich panel", "4 cm poliüretan sandviç panel", "kiremit rengi sandviç panel",
              "kiremit kırmızısı sandviç"):
        assert kiyas(d) == kiyas(d, satir=True) == "ek", d
    for d in ("çift kat yalıtım", "panel", "kiremit kırmızısı", "saçak 50 cm", "çatı penceresi", "çatı eğimi %40", "çatı arası", ""):
        assert kiyas(d) == "ek", d                                                 # çatı sözü ama malzeme yok
    for d in ("kiremit", "kiremit desen sac", "kiremit desen sac + OSB", "shingle", "OSB + membran + shingle", "şıngıl", "trapez sac",
              "trapez", "tek kat panel", "tek kat", "tek katlı panel", "sandviç değil kiremit", "sandviç yerine tek kat panel",
              "galvaniz sac", "boyalı sac", "çatı sac olsun", "onduline", "eternit", "marsilya kiremidi", "alüminyum"):
        assert kiyas(d) == kiyas(d, satir=True) == "baska", d
    for d in ("5 cm", "antrasit", "çift kat yalıtım", "membranlı"):                # tablonun kaplama satırına yazılmış, sandviç anmıyor
        assert kiyas(d, satir=True) == "baska" and kiyas(d) == "ek", d
    for d in ("çatı oluğu galvaniz olsun", "çatı penceresi alüminyum", "çatı saçağı galvaniz", "alüminyum çatı penceresi",
              "galvaniz oluk"):                                                    # hakem, 4. tur: çatının parçası, örtüsü değil
        assert kiyas(d) == "ek", d
    for d in ("çatı galvaniz, pencereler antrasit", "çatı sac olsun, oluk da galvaniz", "çatı sacı antrasit"):
        assert kiyas(d) == "baska", d
    for d in ("sac", "galvaniz sac", "alüminyum"):                                 # çatıdan söz etmeyen yerde cephe de olabilir
        assert kiyas(d, baglam=False) == "ek", d
    for d in ("kiremit", "shingle olsun", "trapez sac", "onduline"):               # çatıya özgü malzeme: bağlamsız da sayılır
        assert kiyas(d, baglam=False) == "baska", d
    assert KR._kaplama_kiyasi("sandviç panel", "tek_kat_panel") == "baska" and KR._kaplama_kiyasi("tek kat panel", "tek_kat_panel") == "ayni"
    for a in ("Çatı Kaplaması", "Çatı kaplaması", "cati kaplamasi", "Kaplama", "Çatı kaplama", "Çatı Malzemesi", "Çatı", "Çatı örtüsü"):
        assert KR._kaplama_satiri_mi(a), a
    for a in ("Çatı Kaplama Rengi", "Çatı rengi", "Çatı Şekli", "Çatı Eğimi", "Dış Duvarlar", "Pencere Rengi", "Ek İstekler", "Zemin",
              "Malzeme", "Dış cephe kaplaması", "Çatı Oluğu", "Çatı penceresi", "Çatı saçağı"):
        assert not KR._kaplama_satiri_mi(a), a
    for x in ("çatı kiremit olsun", "Çatıya OSB + nem bariyeri", "kaplama shingle olsun"):
        assert KR._kaplama_istegi_mi(x), x
    for x in ("dış cephe kaplaması trapez sac", "zemin kaplaması laminat", "mutfak tezgahı granit", "saçak 50 cm olsun"):
        assert not KR._kaplama_istegi_mi(x), x
    # taslaktan okuma: tablonun öteki satırları ve çatı olmayan yerler sayılmaz; "çatı"sız serbest istekte çatıya özgü malzeme sayılır
    ts = {"form_kaplama_yazi": "sandviç panel",
          "bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel", "Dış Duvarlar": "trapez sac", "Çatı Kaplama Rengi": "kiremit kırmızısı",
                               "Malzeme": "kiremit", "Cephe": "galvaniz sac", "Çatı": "çift kat yalıtım",
                               "Dış Cephe Kaplaması": "trapez sac", "Cephe Malzemesi": "trapez sac",     # hakem, 4. tur: çatı değil
                               "Duvar Kaplaması": "kiremit desen sac", "Çatı Oluğu": "galvaniz"},
          "ozel_istekler": ["kiremit olsun", "dış cephe trapez sac", "zemin laminat", "çatı sac olsun", "sac kapı", "shingle olsun",
                            "çatı oluğu galvaniz olsun"]}
    assert KR._kaplama_sozleri(ts, "sandvic_panel") == (["Çatı Kaplaması"], ["Malzeme: kiremit", "kiremit olsun", "çatı sac olsun",
                                                                           "shingle olsun"])


def test_sohbette_yazilan_baska_kaplama_dusmez(tmp_path):
    """Geometri hakemi (PR-11): formda sandviç panel seçiliyken bayi başka bir kaplama yazarsa (LLM aynı özellik satırına, başka adlı bir
    satıra ya da serbest isteğe yazar) söz silinmez ve çizim onun tersini göstermez. Son söz bayinin cümlesidir: form seçimi çizime
    işlenmez, yazdığı kaplama özel isteğe gider, bayiye söylenir (ön not "işleyemezsem plan mesajında yazarım" demişti)."""
    # başka kaplama: aynı satır (Ç8801 tek kat panelli, KT-02 kendi kaplaması sandviç panel), başka adlı satır, serbest istek
    for kod, ek, beklenen in (
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "kiremit"}}, ["Çatı Kaplaması: kiremit"]),
            ("KT02", {"bina_ozellikleri": {"Çatı Kaplaması": "kiremit"}}, ["Çatı Kaplaması: kiremit"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel", "Çatı kaplaması": "kiremit desen sac"}},
             ["Çatı kaplaması: kiremit desen sac"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel", "Kaplama": "kiremit"}}, ["Kaplama: kiremit"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel", "Çatı Malzemesi": "shingle"}}, ["Çatı Malzemesi: shingle"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel"}, "ozel_istekler": ["çatı kiremit olsun"]},
             ["çatı kiremit olsun"]),
            # üçüncü tur: desende olmayan malzeme, "çatı"sız serbest istek, başka adlı satır
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "galvaniz sac"}}, ["Çatı Kaplaması: galvaniz sac"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "onduline"}}, ["Çatı Kaplaması: onduline"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel", "Malzeme": "kiremit"}}, ["Malzeme: kiremit"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel"}, "ozel_istekler": ["kiremit olsun"]}, ["kiremit olsun"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel"}, "ozel_istekler": ["trapez sac olsun"]}, ["trapez sac olsun"]),
            ("Ç8801", {"bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel"}, "ozel_istekler": ["çatı sac olsun"]}, ["çatı sac olsun"])):
        k, kr = _plan(tmp_path, kod, {**_KAP_ORTAK, **ek})
        assert kr.eylem == "is_emri" and kr.is_emri["yapi"]["degisiklikler"] == [], (kod, ek)
        assert kr.is_emri["bilgi"]["ozel_istekler"] == beklenen and "Uygulanan" not in kr.mesaj, (kod, ek)
        assert _BASKA_NOTU in kr.mesaj, kr.mesaj                                                   # bayiye söylenir
        assert not {"form_kaplama", "form_kaplama_yazi", "form_kaplama_once"} & set(k.d["taslak"])
    # aynı kaplama, ek bilgiyle ya da başka yazımla: seçim işlenir; bilgi özel istekte kalır (tabloyla çelişmez)
    for bo, beklenen in (({"Çatı Kaplaması": "sandviç panel 5 cm"}, ["Çatı Kaplaması: sandviç panel 5 cm"]),
                         ({"Çatı Kaplaması": "4 cm poliüretan sandviç panel"}, ["Çatı Kaplaması: 4 cm poliüretan sandviç panel"]),
                         ({"Çatı Kaplaması": "sandwich panel"}, ["Çatı Kaplaması: sandwich panel"]),
                         ({"Çatı Kaplaması": "sandviç panel", "Çatı": "çift kat yalıtım"}, ["Çatı: çift kat yalıtım"]),
                         ({"Çatı Kaplaması": "Sandviç Panel"}, []), ({"çatı kaplaması": "sandviç"}, []),
                         ({"Çatı Kaplaması": "SANDVİÇ PANEL"}, [])):
        k, kr = _plan(tmp_path, "Ç8801", {**_KAP_ORTAK, "bina_ozellikleri": dict(bo)})
        assert [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi"], bo
        assert kr.is_emri["bilgi"]["ozel_istekler"] == beklenen and "başka bir kaplama" not in kr.mesaj, bo
    # `form_kaplama_yazi` taşınmamış taslak: kitabın adıyla kıyas yeter
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_kaplama": "sandvic_panel", "bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel"}})
    assert [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi"] and kr.is_emri["bilgi"]["ozel_istekler"] == []


def test_formdan_once_yazilan_kaplama_son_soz_degildir(tmp_path):
    """Geometri hakemi (ikinci ve üçüncü tur, sıra): bayi önce sohbette kiremit yazdı, sonra (taslaktan doldurulan) formda sandviç panel
    seçti. Son söz formdur: eski sözler "formdan önce" diye işaretlenir ve form seçimini durdurmaz. Hiçbiri silinmez (karma satırdaki
    yalıtım bilgisi düşmez); özel istekte kalır. Bayi aynı sözü formdan sonra yeniden yazarsa işaret kalkar: o artık son sözdür."""
    def form_gelir(k, **ek):
        t = Talep.model_validate({**TF.talep(_cevap(alan=88, kaplama="sandvic")), **ek})
        k.birlestir(t.model_dump())
        k.celik_formu = {"oncelik": "yok", "dis140": False, "kaplama": "sandvic_panel", "anahtarlar": TF.celik_anahtarlari()}
        KR._form_izi(k, t, "")
        return k.d["taslak"]

    k = _konusma(tmp_path)
    k.d["taslak"].update({"bina_ozellikleri": {"Çatı kaplaması": "kiremit", "Çatı Malzemesi": "kiremit + 10 cm taşyünü",
                                               "Çatı": "çift kat yalıtım"},
                          "ozel_istekler": ["çatı kiremit olsun", "zemin laminat"]})
    ts = form_gelir(k)
    assert ts["bina_ozellikleri"]["Çatı Kaplaması"] == "sandviç panel"
    assert ts["bina_ozellikleri"]["Çatı Malzemesi"] == "kiremit + 10 cm taşyünü" and ts["bina_ozellikleri"]["Çatı"] == "çift kat yalıtım"
    assert ts["form_kaplama_once"] == ["Çatı kaplaması: kiremit", "Çatı Malzemesi: kiremit + 10 cm taşyünü", "çatı kiremit olsun"]
    assert ts["ozel_istekler"] == ["çatı kiremit olsun", "zemin laminat"]
    taslak = {kk: v for kk, v in ts.items() if kk.startswith("form") or kk in ("bina_ozellikleri", "ozel_istekler")}
    k2, kr = _plan(tmp_path, "Ç8801", json.loads(json.dumps(taslak)))
    assert [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi"] and "başka bir kaplama" not in kr.mesaj
    assert "Çatı Malzemesi: kiremit + 10 cm taşyünü" in kr.is_emri["bilgi"]["ozel_istekler"]              # bilgi düşmedi
    # formdan sonra bayi aynı cümleyi yeniden yazar: işaret kalkar, form seçimi işlenmez, bayiye söylenir
    t2 = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "", "ozel_istekler": ["çatı kiremit olsun"]})
    k.birlestir(t2.model_dump())
    KR._form_izi(k, t2, "çatı kiremit olsun")
    assert "form_kaplama_once" not in k.d["taslak"]                                # aynı malzemeyi anan eski sözlerin hepsi son söz oldu
    taslak = {kk: v for kk, v in k.d["taslak"].items() if kk.startswith("form") or kk in ("bina_ozellikleri", "ozel_istekler")}
    k3, kr = _plan(tmp_path, "Ç8801", json.loads(json.dumps(taslak)))
    assert kr.is_emri["yapi"]["degisiklikler"] == [] and _BASKA_NOTU in kr.mesaj
    # LLM satırı bağlamdan yineledi ama bayinin mesajı kaplama anmıyor (K18): işaret durur
    k = _konusma(tmp_path)
    k.d["taslak"].update({"ozel_istekler": ["çatı kiremit olsun"]})
    form_gelir(k)
    t3 = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "", "ozel_istekler": ["çatı kiremit olsun"]})
    k.birlestir(t3.model_dump())
    KR._form_izi(k, t3, "Ç8801 olsun")
    assert k.d["taslak"]["form_kaplama_once"] == ["çatı kiremit olsun"]
    # hakem, 4. tur: bayi sözü formdan sonra yeniden yazdı, LLM alan doldurmadı (cümle taslakta zaten var): işaret yine kalkar
    k = _konusma(tmp_path)
    k.d["taslak"].update({"ozel_istekler": ["çatı kiremit olsun", "çatı oluğu galvaniz olsun"]})
    assert form_gelir(k)["form_kaplama_once"] == ["çatı kiremit olsun"]
    t4 = Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": ""})
    k.birlestir(t4.model_dump())
    KR._form_izi(k, t4, "çatı kiremit olsun dedim")
    assert "form_kaplama_once" not in k.d["taslak"]
    taslak = {kk: v for kk, v in k.d["taslak"].items() if kk.startswith("form") or kk in ("bina_ozellikleri", "ozel_istekler")}
    k4, kr = _plan(tmp_path, "Ç8801", json.loads(json.dumps(taslak)))
    assert kr.is_emri["yapi"]["degisiklikler"] == [] and _BASKA_NOTU in kr.mesaj
    assert "çatı kiremit olsun" in kr.is_emri["bilgi"]["ozel_istekler"]
    # bayinin mesajı çatı malzemesi anmıyor ve LLM alan doldurmuyor: işaret durur
    k = _konusma(tmp_path)
    k.d["taslak"].update({"ozel_istekler": ["çatı kiremit olsun"]})
    form_gelir(k)
    k.birlestir(t4.model_dump())
    KR._form_izi(k, t4, "pencereler antrasit olsun")
    assert k.d["taslak"]["form_kaplama_once"] == ["çatı kiremit olsun"]
    # formun kendi notunda yazılan kaplama aynı mesajdadır: "formdan önce" sayılmaz
    k = _konusma(tmp_path)
    assert "form_kaplama_once" not in form_gelir(k, ozel_istekler=["çatı shingle olsun"])


def test_revizyonda_yazilan_baska_kaplama_islemi_cikarir(tmp_path):
    """Geometri hakemi (ikinci tur): r01 formdan sandviç panelle çizildi; r02'de bayi "çatı kaplaması kiremit olsun" yazdı. Zarftaki
    kaplama işlemi çıkar (plan modelin kendi kaplamasına döner: liste bayinin son sözüne karşın sandviç saymaz), yazdığı kaplama özel
    isteğe gider, bayiye söylenir. Aynı kaplamanın ek bilgisi ("poliüretan sandviç panel") işlemi çıkarmaz."""
    from beyin.katalog import Katalog
    for deger, kalir in (("kiremit", False), ("galvaniz sac", False), ("onduline", False), ("poliüretan sandviç panel", True)):
        k, kr = _plan(tmp_path, "Ç8801", {**_KAP_ORTAK, "bina_ozellikleri": {"Çatı Kaplaması": "sandviç panel"}})
        assert [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi"]
        k.d["son_metin"] = f"çatı kaplaması {deger} olsun"
        k.d["taslak"]["varyantlar"] = []
        k.d["taslak"].setdefault("bina_ozellikleri", {})["Çatı Kaplaması"] = deger
        k.son_llm = {"pencere": False, "varyantlar": [], "bilgi": {"Çatı Kaplaması": deger}}
        kr2 = KR._celik_is_emri_uret(k, {"kod": "TEST", "ad": "Test Bayi"}, Katalog(), _celik_adayi("Ç8801"), k.d["taslak"])
        assert kr2.eylem == "is_emri" and kr2.is_emri["revizyon"] == 2, kr2
        ops = [d["op"] for d in kr2.is_emri["yapi"]["degisiklikler"]]
        t = W._cizim_tanimi(kr2.is_emri["yapi"]["tanim"], kr2.is_emri["yapi"]["degisiklikler"])
        assert kr2.is_emri["bilgi"]["ozel_istekler"] == [f"Çatı Kaplaması: {deger}"]
        if kalir:
            assert ops == ["cati_kaplamasi"] and varyant.kaplama_oku(t) == "sandvic_panel" and "plandan çıkardım" not in kr2.mesaj
        else:
            assert ops == [] and varyant.kaplama_oku(t) == "tek_kat_panel"
            assert ("Mesajınızda başka bir çatı kaplaması yazdınız. Sandviç panel seçiminizi plandan çıkardım. Planı modelin kendi çatı "
                    "kaplamasıyla çizdim. Yazdığınız kaplamayı talebe yazdım. Ön onay planınız hazır") in kr2.mesaj, kr2.mesaj
            assert kr2.is_emri["yapi"]["uygulanan"] == []


def test_kiremit_desen_sac_ayni_kurallarla(tmp_path):
    """Kiremit desen sac + OSB (BK-33, D-98; Motor 15 Kasım 2026'dan beri hesaplar) sandviç panelin kurallarıyla işlenir (D-97). Kıyas:
    "ayni" kaplamanın formdaki adı, ilk sözcüğü ve pafta tablosunun yazdığı ad; "ek" kendi adını anan söz ("sac" yalnız adın içinde,
    "kiremit desen"in hemen ardında kaplamanın kendi sözcüğüdür); "baska" başka bir çatı malzemesi ve adın dışındaki her "sac" (geometri
    hakemi, 5. tur: "kiremit istemiyorum sac olsun"). İlk planda işlem tanıma yazılır; revizyonda başka kaplama yazılırsa çıkar."""
    from beyin.katalog import Katalog
    ad = "kiremit desen sac + OSB"
    kiyas = lambda d, **kw: KR._kaplama_kiyasi(d, "osb_kiremit", (ad,), **kw)                             # noqa: E731
    for d in (ad, "Kiremit Desen Sac + OSB", "kiremit", "OSB + Nem Bariyeri + Kiremit Desen Sac"):   # sonuncusu pafta tablosunun adı
        assert kiyas(d) == kiyas(d, satir=True) == "ayni", d
    for d in ("kiremit desen sac", "kiremit desen sac olsun", "kiremit desenli sac", "kiremit desen sac kırmızı", "boyalı kiremit desen sac",
              "metal kiremit", "kiremit kırmızısı"):
        assert kiyas(d) == kiyas(d, satir=True) == "ek", d
    assert kiyas("çift kat yalıtım") == "ek"
    for d in ("sandviç panel", "tek kat panel", "trapez sac", "trapez sac + OSB", "shingle", "OSB + membran + shingle",
              "kiremit değil sandviç", "galvaniz sac", "çatı alüminyum olsun", "onduline",
              "çatı sac olsun", "boyalı sac", "çatı düz sac olsun", "çatı sacı antrasit", "kiremit istemiyorum sac olsun"):
        assert kiyas(d) == kiyas(d, satir=True) == "baska", d
    for d in ("çatı düz sac olsun", "kiremit istemiyorum sac olsun"):              # hakem 5. tur B1: serbest istekte de aynı sonuç
        assert KR._kaplama_sozleri({"form_kaplama_yazi": ad, "ozel_istekler": [d]}, "osb_kiremit")[1] == [d], d
    assert KR._kaplama_kiyasi("Sandviç Panel", "sandvic_panel", ("sandviç panel",), satir=True) == "ayni"
    ortak = {"form": "celik", "form_kaplama": "osb_kiremit", "form_kaplama_yazi": ad}
    for deger, kalir in (("sandviç panel", False), ("shingle", False), ("boyalı sac", False), ("boyalı kiremit desen sac", True)):
        k, kr = _plan(tmp_path, "Ç8801", {**ortak, "bina_ozellikleri": {"Çatı Kaplaması": ad}})
        assert [(d["op"], d["kaplama"]) for d in kr.is_emri["yapi"]["degisiklikler"]] == [("cati_kaplamasi", "osb_kiremit")]
        assert kr.is_emri["bilgi"]["ozel_istekler"] == [] and f"Uygulanan: çatı kaplaması {ad}." in kr.mesaj, kr.mesaj
        assert varyant.kaplama_oku(W._cizim_tanimi(kr.is_emri["yapi"]["tanim"], kr.is_emri["yapi"]["degisiklikler"])) == "osb_kiremit"
        k.d["son_metin"] = f"çatı kaplaması {deger} olsun"
        k.d["taslak"]["varyantlar"] = []
        k.d["taslak"].setdefault("bina_ozellikleri", {})["Çatı Kaplaması"] = deger
        k.son_llm = {"pencere": False, "varyantlar": [], "bilgi": {"Çatı Kaplaması": deger}}
        kr2 = KR._celik_is_emri_uret(k, {"kod": "TEST", "ad": "Test Bayi"}, Katalog(), _celik_adayi("Ç8801"), k.d["taslak"])
        assert kr2.eylem == "is_emri" and kr2.is_emri["revizyon"] == 2, kr2
        ops = [d["op"] for d in kr2.is_emri["yapi"]["degisiklikler"]]
        t = W._cizim_tanimi(kr2.is_emri["yapi"]["tanim"], kr2.is_emri["yapi"]["degisiklikler"])
        assert kr2.is_emri["bilgi"]["ozel_istekler"] == [f"Çatı Kaplaması: {deger}"]
        if kalir:
            assert ops == ["cati_kaplamasi"] and varyant.kaplama_oku(t) == "osb_kiremit" and "plandan çıkardım" not in kr2.mesaj
        else:
            assert ops == [] and varyant.kaplama_oku(t) == "tek_kat_panel"
            assert ("Mesajınızda başka bir çatı kaplaması yazdınız. Kiremit desen sac + OSB seçiminizi plandan çıkardım. Planı modelin "
                    "kendi çatı kaplamasıyla çizdim. Yazdığınız kaplamayı talebe yazdım. Ön onay planınız hazır") in kr2.mesaj, kr2.mesaj


def test_cati_kaplamasi_revizyonda_kalir(tmp_path):
    """Kaplama işlemi `yapi.degisiklikler`'de birikir: aynı projenin sonraki revizyonu ve çatı varyantı değişimi onu taşır."""
    from beyin.katalog import Katalog
    k, kr = _plan(tmp_path, "Ç8801", {"form": "celik", "form_kaplama": "sandvic_panel"})
    assert [d["op"] for d in kr.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi"]
    k.d["son_metin"] = "çatı K olsun"
    k.d["taslak"]["varyantlar"] = []
    kr2 = KR._celik_is_emri_uret(k, {"kod": "TEST", "ad": "Test Bayi"}, Katalog(), _celik_adayi("Ç8801K"), k.d["taslak"])
    assert kr2.eylem == "is_emri" and kr2.is_emri["revizyon"] == 2, kr2
    assert [d["op"] for d in kr2.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi", "cati_varyanti"]
    t = W._cizim_tanimi(kr2.is_emri["yapi"]["tanim"], kr2.is_emri["yapi"]["degisiklikler"])
    assert varyant.kaplama_oku(t) == "sandvic_panel"
    # çatı değişmeyen sonraki revizyon (r03): kaplama yine zarfta ve çizim tanımında
    k.d["son_metin"] = "mutfak penceresi 120x120 olsun"
    k.d["taslak"]["varyantlar"] = []
    k.d["taslak"]["pencereler"] = [{"mahal": "mutfak", "en": 120, "yukseklik": 120}]
    kr3 = KR._celik_is_emri_uret(k, {"kod": "TEST", "ad": "Test Bayi"}, Katalog(), _celik_adayi("Ç8801K"), k.d["taslak"])
    assert kr3.eylem == "is_emri" and kr3.is_emri["revizyon"] == 3, kr3
    assert [d["op"] for d in kr3.is_emri["yapi"]["degisiklikler"]] == ["cati_kaplamasi", "pencere_olcu"]   # çatı artık planın kendisi
    assert varyant.kaplama_oku(W._cizim_tanimi(kr3.is_emri["yapi"]["tanim"], kr3.is_emri["yapi"]["degisiklikler"])) == "sandvic_panel"


# ─── İE-20 PR-12 (D-102) · çelik formun ikinci sürümü: trapez sac yok, shingle satırı OSB + membran + shingle ───
AYAR_CF2 = {**AYAR_CF, "talep_formu": {**AYAR_CF["talep_formu"], "celik2_flow_id": "6666666666"}}
YAYIMLI_CELIK_SHA = "9057e44c735d1d56ac86b86a4e9cd661248720eace9d8b10209a38148a7d5f74"


def _kaplama_secenekleri(tanim: dict) -> list[tuple[str, str]]:
    c = next(c for c in tanim["screens"][1]["layout"]["children"] if c.get("name") == "kaplama")
    return [(x["id"], x["title"]) for x in c["data-source"]]


def test_celik2_yayimli_formun_trapez_sacsiz_kopyasi():
    """Hedef liste Lokman'ın sözü (15 Kasım 2026 05:23:34 UTC: "Trapez Sac çelik konstrüksiyonda yok ... seçenek olarak çelikte sunma";
    05:23:08: "OSB + mebran + Shingle olacak"; 07:54:18: "çelikte Trapez sacı komple kaldır"; 07:54:29: "yani Trapez sac + OSB de
    olmasın". 05:28:14 kartındaki "Yalnız trapez sac kalksın" seçimi 07:54 sözleriyle değişti: trapez sac + OSB de yok). Yayımlı form
    (`celik.json`, Meta'da değişmez) bayt bayt aynı kalır; yeni form onun kopyasıdır, yalnız çatı kaplaması seçenekleri değişir."""
    import hashlib
    assert hashlib.sha256((TF.FORMLAR / "celik.json").read_bytes()).hexdigest() == YAYIMLI_CELIK_SHA
    eski, yeni = TF.tanim("celik"), TF.tanim("celik2")
    assert _kaplama_secenekleri(yeni) == [("tek_kat", "Tek kat panel (standart)"), ("sandvic", "Sandviç panel"),
                                          ("kiremit", "Kiremit desen sac + OSB"), ("shingle", "OSB + membran + shingle")]
    assert [i for i, _ in _kaplama_secenekleri(eski) if i not in dict(_kaplama_secenekleri(yeni))] == ["trapez", "osb_trapez"]
    assert all(len(t) <= 30 for _, t in _kaplama_secenekleri(yeni))                                   # Meta: seçenek başlığı ≤ 30
    for t in (eski, yeni):                                                                            # öteki her şey aynı
        next(c for c in t["screens"][1]["layout"]["children"] if c.get("name") == "kaplama")["data-source"] = []
    assert eski == yeni
    assert TF.EKRAN["celik2"] == TF.EKRAN["celik"] and TF.DUGME["celik2"] == TF.DUGME["celik"]
    # bayiye okunan adlar: shingle Lokman'ın sırasıyla; "trapez" ve "osb_trapez" yalnız eski formun cevabı için durur
    assert TF.C_KAPLAMA["shingle"] == "OSB + membran + shingle" and TF.C_KAPLAMA["trapez"] == "trapez sac"
    assert TF.C_KAPLAMA["osb_trapez"] == "trapez sac + OSB"
    assert set(dict(_kaplama_secenekleri(TF.tanim("celik2")))) == set(TF.C_KAPLAMA) - {"trapez", "osb_trapez"}
    assert "trapez" not in (TF.FORMLAR / "celik2.json").read_text(encoding="utf-8").lower()             # hiçbir trapez saclı seçenek


def test_celik2_kimligi_varsa_celik_formun_yerine_sunulur():
    assert "celik2_flow_id" not in AY.VARSAYILAN["talep_formu"]
    celik_ts = {"yapi_turu": "celik", "oda_programi": "2+1"}
    assert W.form_kimligi(AYAR_CF, "celik2") is None and W.form_kimligi(AYAR_CF2, "celik2") == "6666666666"
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, AYAR_CF)[0] == "celik"                         # kimlik yok: davranış aynı
    for bayi, taslak in ((None, celik_ts), ({"varsayilanlar": {"yapi_turu": "celik"}}, None)):
        fs = W.talep_formu_sunusu(GELEN, bayi, taslak, AYAR_CF2)
        assert fs[0] == "celik2" and fs[1].startswith("cf:") and fs[1].endswith(":1") == (taslak is not None)
        assert fs[2] == TF.celik_ekran_verisi(bayi, taslak)
        satir = W.form_satiri(GELEN, "Talebinizi formla iletin.", fs, AYAR_CF2)
        p = satir["interactive"]["action"]["parameters"]
        assert p["flow_id"] == "6666666666" and p["flow_action_payload"]["screen"] == "TALEP_C" and p["flow_cta"] == "Talep formu"
        assert set(p["flow_action_payload"]["data"]) == set(TF.tanim("celik2")["screens"][0]["data"])
        M.mesaj_yuku(satir, "905550000001")
    # eski formun kimliği olmadan da sunulur; prefabrik ve bilinmeyen yapı tipi aynen
    yalniz = {**AYAR_PF, "talep_formu": {**AYAR_PF["talep_formu"], "celik2_flow_id": "6666666666"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, yalniz)[0] == "celik2"
    assert W.talep_formu_sunusu(GELEN, None, {"yapi_turu": "prefabrik"}, AYAR_CF2)[0] == "prefabrik"
    assert W.talep_formu_sunusu(GELEN, None, None, AYAR_CF2)[0] == "yapi_sor"
    # bozuk kimlik sunulmaz: yayımlı çelik formu
    bozuk = {**AYAR_CF, "talep_formu": {**AYAR_CF["talep_formu"], "celik2_flow_id": "12a"}}
    assert W.talep_formu_sunusu(GELEN, None, celik_ts, bozuk)[0] == "celik"
    assert W.YAPI_FORM_METNI["celik2"] == W.YAPI_FORM_METNI["celik"]


def test_celik2_cevabi_ayni_yoldan_okunur():
    """Yeni formun cevabı eski formunkiyle aynı token ve aynı alanlarla gelir. Eski formdan yolda kalmış "trapez" ve "osb_trapez"
    cevapları okunur (özel isteğe yazılır)."""
    oz = _cevap(alan=88, kaplama="shingle")
    assert (oz["tur"], oz["form"]) == ("talep", "celik") and TF.celik_standart_disi(oz) == ["çatı kaplaması OSB + membran + shingle"]
    assert TF.talep(oz)["bina_ozellikleri"]["Çatı Kaplaması"] == "OSB + membran + shingle" and TF.celik_kaplamasi(oz) == "osb_shingle"
    assert TF.celik_notu(oz) == "Çatı kaplaması OSB + membran + shingle seçtiniz. Çizime işlerim. İşleyemezsem plan mesajında yazarım."   # BK-33, D-100
    eski = _cevap(alan=88, kaplama="trapez")
    assert TF.celik_standart_disi(eski) == ["çatı kaplaması trapez sac"] and TF.talep(eski)["bina_ozellikleri"]["Çatı Kaplaması"] == "trapez sac"
    eski2 = _cevap(alan=88, kaplama="osb_trapez")
    assert TF.celik_standart_disi(eski2) == ["çatı kaplaması trapez sac + OSB"] and TF.celik_kaplamasi(eski2) is None
    assert TF.talep(eski2)["bina_ozellikleri"]["Çatı Kaplaması"] == "trapez sac + OSB"

