"""İE-20 PR-2 · talep formu ve revizyon formu (WhatsApp Flow, uç noktasız): form tanımları (Flow JSON 7.3 sınırları), cevabın çözümü,
LLM'siz talep, ekran verisi (kartın varsayılanları), Meta yükü ve webhook satırı. Postgres, ağ, LLM ve WhatsApp yok.

Koşum: python -m pytest testler/kalici/test_talep_formu.py -q
"""
from __future__ import annotations

import json
import re

import pytest

import ayarlar as AY
import meta_api as M
import talep_formu as TF
import webhook as WH
import worker as W
from beyin import gorsel_okuma as GO
from beyin.sema import Talep

SINIR = {"TextInput": 20, "TextArea": 20, "Dropdown": 20, "RadioButtonsGroup": 30, "CheckboxGroup": 30, "DocumentPicker": 80, "PhotoPicker": 80,
         "Footer": 35}
SECIMLI = ("RadioButtonsGroup", "Dropdown", "CheckboxGroup")
PICKER = ("DocumentPicker", "PhotoPicker")
FORM = {"mesaj_katmani": True,
        "talep_formu": {"acik": True, "talep_flow_id": "1111111111", "revizyon_flow_id": "2222222222", "taslak": True}}


def bilesenler(tur: str) -> tuple[dict, list[dict]]:
    [ekran] = TF.tanim(tur)["screens"]
    return ekran, ekran["layout"]["children"]


@pytest.mark.parametrize("tur", ["talep", "revizyon"])
def test_form_tanimi_flow_json_sinirlari(tur):
    t = TF.tanim(tur)
    assert t["version"] == "7.3" and "data_api_version" not in t and "routing_model" not in t      # uç noktasız
    ekran, cocuklar = bilesenler(tur)
    assert ekran["id"] == TF.EKRAN[tur] and ekran["terminal"] is True
    assert all("__example__" in v and v["type"] == "string" for v in ekran["data"].values())
    adlar = [c["name"] for c in cocuklar if "name" in c]
    assert len(adlar) == len(set(adlar))
    assert sum(c["type"] in PICKER for c in cocuklar) <= 1                                       # ekranda en çok bir dosya seçici
    for c in cocuklar:
        if c["type"] in SINIR:
            assert 0 < len(c["label"]) <= SINIR[c["type"]], c
        if c["type"] in SECIMLI:
            assert 1 <= len(c["data-source"]) <= 20 and all(len(x["title"]) <= 30 for x in c["data-source"])
        if "helper-text" in c:
            assert len(c["helper-text"]) <= 80
        if c["type"] in PICKER:
            assert "init-value" not in c and len(c.get("description", "")) <= 300 and c["max-uploaded-documents"] == 1
            assert c["max-file-size-kb"] * 1024 <= GO.EN_BUYUK_BAYT                              # PR-1'in okuma sınırı (20 MB)
            for mime in c["allowed-mime-types"]:                                                # PR-1'in okuyabildiği türler
                assert GO.okunabilir_mi(mime, 1000) is None, mime
        for d in re.findall(r"\$\{data\.(\w+)\}", json.dumps(c)):
            assert d in ekran["data"], d
    [footer] = [c for c in cocuklar if c["type"] == "Footer"]
    yuk = footer["on-click-action"]["payload"]
    assert footer["on-click-action"]["name"] == "complete"
    assert {v[len("${form."):-1] for v in yuk.values()} == set(adlar) and set(yuk) == set(adlar)  # her alan cevapta, dosya üst düzeyde


def test_talep_formu_secenekleri_cozumleyiciyle_ayni():
    _e, cocuklar = bilesenler("talep")
    ids = {c["name"]: [x["id"] for x in c["data-source"]] for c in cocuklar if c["type"] in SECIMLI}
    assert ids == {"yapi": list(TF.YAPI), "kat": list(TF.KAT), "oda": list(TF.ODA), "cati": list(TF.CATI), "veranda": list(TF.VERANDA)}
    _e, cocuklar = bilesenler("revizyon")
    assert [x["id"] for c in cocuklar if c["type"] == "CheckboxGroup" for x in c["data-source"]] == list(TF.NEYI)
    # sema ile aynı değerler: veranda konumu ve çatı tipi Talep'te geçerli
    Talep.model_validate({"niyet": "yeni_talep", "guven": "yuksek", "ozet": "x", "veranda": {"konum": "kose"}, "cati": {"tip": "tek_egimli"}})
    # kartın izinli varsayılanları (depo; göç 009'un CHECK'leri) formun seçenekleriyle aynı
    from depo import Depo
    assert Depo.VARSAYILAN_ALANLARI == {"yapi_turu": tuple(TF.YAPI), "kat_sayisi": tuple(int(x) for x in TF.KAT), "cati": tuple(TF.CATI),
                                        "veranda": tuple(TF.VERANDA)}


def _cevap(**alan) -> str:
    return json.dumps({"flow_token": "tf:abc123", **alan})


def test_cevap_ozeti_talep_ve_eslesme():
    oz = TF.cevap_ozeti(_cevap(yapi="prefabrik", kat="1", oda="2+1", alan="", en="7,73", boy="10.14", cati="besik", veranda="on",
                               **{"not": "Salonu geniş tutalım, 0532 111 22 33"},
                               dosya=[{"file_name": "plan.jpg", "mime_type": "image/jpeg", "sha256": "abc=", "id": "3631120727156756"}]))
    assert oz["tur"] == "talep" and oz["token"] == "tf:abc123"
    assert oz["alanlar"] == {"yapi": "prefabrik", "kat": "1", "oda": "2+1", "en": 7.73, "boy": 10.14, "cati": "besik", "veranda": "on",
                             "not": "Salonu geniş tutalım, 0532 111 22 33"}
    assert oz["dosyalar"] == [{"id": "3631120727156756", "file_name": "plan.jpg", "mime_type": "image/jpeg", "sha256": "abc="}]
    t = TF.talep(oz)
    Talep.model_validate(t)
    assert t["niyet"] == "yeni_talep" and t["yapi_turu"] == "prefabrik" and t["kat_sayisi"] == 1 and t["oda_programi"] == "2+1"
    assert t["dis_olcu"] == {"en_m": 7.73, "boy_m": 10.14} and "alan_m2" not in t
    assert t["veranda"] == {"istiyor": True, "konum": "on"} and t["cati"] == {"tip": "besik"}
    assert len(t["ozel_istekler"]) == 1 and "111 22 33" not in t["ozel_istekler"][0]          # not: numara maskeli, LLM'e gitmez
    assert TF.metin(oz) == ("Talep formu: prefabrik, tek kat, 2+1, 7,73 × 10,14 m, beşik çatı, veranda önde. "
                            "Not: Salonu geniş tutalım, 0532 111 22 33 Dosya eklendi.")


def test_cevap_ozeti_gecersiz_degerler_atilir():
    oz = TF.cevap_ozeti(_cevap(yapi="ahsap", kat="3", oda="9+2", alan="-5", en="abc", boy="7", cati="kubbe", veranda="cati",
                               dosya=[{"id": "../x"}, "bozuk"], fazla="x"))
    assert oz["alanlar"] == {"boy": 7.0} and oz["dosyalar"] == []
    t = TF.talep(oz)
    assert {a for a in t if a not in ("niyet", "guven", "ozet")} == set()                         # tek kenar ölçü değil (en ve boy birlikte)
    assert TF.cevap_ozeti("{bozuk")["tur"] == "bilinmiyor" and TF.cevap_ozeti("x" * (TF.CEVAP_EN_COK + 1))["tur"] == "bilinmiyor"
    assert TF.cevap_ozeti({"flow_token": "zz:1"})["tur"] == "bilinmiyor"
    # sözlük olarak da gelir (Meta belgesindeki örnek); boyutu ve alanı kesilir
    assert TF.cevap_ozeti({"flow_token": "tf:x", "alan": 88})["alanlar"] == {"alan": 88.0}


def test_revizyon_cevabi_ve_metni():
    oz = TF.cevap_ozeti(json.dumps({"flow_token": "rv:TF-2026-0001:2", "neyi": ["pencere", "veranda", "yok"], "aciklama": " mutfak penceresi 120x120 "}))
    assert oz["tur"] == "revizyon" and oz["alanlar"] == {"neyi": ["pencere", "veranda"], "aciklama": "mutfak penceresi 120x120"}
    assert TF.metin(oz) == "mutfak penceresi 120x120 (değişecek: pencere, veranda)"
    bos = TF.cevap_ozeti(json.dumps({"flow_token": "rv:TF-2026-0001:2", "dosya": [{"id": "77", "mime_type": "application/pdf"}]}))
    assert TF.metin(bos) == "Revizyon formu. Dosya eklendi." and bos["alanlar"] == {"neyi": []}


def test_ekran_verisi_taslak_kart_sabit():
    assert TF.ekran_verisi(None, None) == {"yapi": "prefabrik", "kat": "1", "cati": "besik", "veranda": "on", "oda": "", "alan": "", "en": "",
                                           "boy": "", "bilinen": "Bildiğiniz kadarını doldurmanız yeterli; eksik kalanı sohbette sorarım."}
    kart = {"varsayilanlar": {"yapi_turu": "celik", "veranda": "kose", "cati": "uydurma"}}
    d = TF.ekran_verisi(kart, None)
    assert (d["yapi"], d["veranda"], d["cati"]) == ("celik", "kose", "besik")                     # geçersiz kart değeri sabit varsayılana düşer
    taslak = {"yapi_turu": "prefabrik", "oda_programi": "3+1", "dis_olcu": {"en_m": 7.5, "boy_m": 9.0}, "veranda": {"konum": "yan"}}
    d = TF.ekran_verisi(kart, taslak)
    assert (d["yapi"], d["oda"], d["en"], d["boy"], d["veranda"]) == ("prefabrik", "3+1", "7.5", "9", "yan")
    assert d["bilinen"].startswith("Bildiklerim: 3+1, 7,5 × 9 m. ")
    [ekran] = TF.tanim("talep")["screens"]
    assert set(d) == set(ekran["data"]) and all(isinstance(v, str) for v in d.values())


def test_meta_yuku_flow_ve_sinirlar():
    satir = W.giden_form({"id": "wamid.G1", "sender": "900000000101"}, "Kaç oda istiyorsunuz? (örn. 2+1, 3+1, tek oda)", 1, "talep", FORM,
                         "tf:abc", TF.ekran_verisi(None, None))
    yuk = M.mesaj_yuku(satir, "900000000101")
    i = yuk["interactive"]
    assert yuk["type"] == "interactive" and i["type"] == "flow" and i["body"]["text"].startswith("Kaç oda")
    p = i["action"]["parameters"]
    assert i["action"]["name"] == "flow" and p["flow_id"] == "1111111111" and p["flow_cta"] == "Talep formu" and p["flow_token"] == "tf:abc"
    assert p["flow_message_version"] == "3" and p["flow_action"] == "navigate" and p["mode"] == "draft"
    assert p["flow_action_payload"]["screen"] == "TALEP" and p["flow_action_payload"]["data"]["yapi"] == "prefabrik"
    yayinda = W.giden_form({"id": "wamid.G1", "sender": "900000000101"}, "x", 1, "talep", {**FORM, "talep_formu": {**FORM["talep_formu"], "taslak": False}},
                           "tf:abc", {})
    assert "mode" not in M.mesaj_yuku(yayinda, "900000000101")["interactive"]["action"]["parameters"]
    for bozuk in ({"flow_id": "abc"}, {"flow_cta": "x" * 21}, {"flow_action": "data_exchange"}, {"mode": "published2"},
                  {"flow_action_payload": {"screen": "kucuk", "data": {}}}, {"flow_token": ""}):
        s = json.loads(json.dumps(satir))
        s["interactive"]["action"]["parameters"].update(bozuk)
        with pytest.raises(M.EtkilesimGecersiz):
            M.mesaj_yuku(s, "900000000101")


def test_form_kimligi_ayarla():
    assert AY.VARSAYILAN["talep_formu"] == {"acik": False, "talep_flow_id": None, "revizyon_flow_id": None, "taslak": True}
    assert W.form_kimligi({"mesaj_katmani": True, "talep_formu": AY.VARSAYILAN["talep_formu"]}, "talep") is None      # varsayılan kapalı
    assert W.form_kimligi(FORM, "talep") == "1111111111" and W.form_kimligi(FORM, "revizyon") == "2222222222"
    assert W.form_kimligi({**FORM, "mesaj_katmani": False}, "talep") is None
    assert W.form_kimligi({**FORM, "talep_formu": {**FORM["talep_formu"], "talep_flow_id": "12a"}}, "talep") is None


def nfm(rj, mid="wamid.FORM1", ctx="wamid.SORU1") -> dict:
    return {"id": mid, "from": "900000000101", "timestamp": "1", "type": "interactive", "context": {"id": ctx},
            "interactive": {"type": "nfm_reply", "nfm_reply": {"name": "flow", "body": "Sent", "response_json": rj}}}


def test_webhook_satiri_form_cevabi():
    assert M.form_cevabi({"type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": "x"}}}) is None
    assert M.form_cevabi({"type": "text", "text": {"body": "x"}}) is None
    m = nfm(_cevap(yapi="celik", oda="3+1", alan="88", cati="besik", veranda="on", kat="1"))
    s = WH.kuyruk_satiri(m, m["id"], "900000000101", "interactive", 1, {}, {"kod": "TSTA", "rol": "bayi"}, {"mode": "patron"}, "1", 1)
    assert s["form"]["tur"] == "talep" and s["reply_id"] is None and s["context_id"] == "wamid.SORU1"
    assert s["text"] == "Talep formu: çelik, tek kat, 3+1, yaklaşık 88 m², beşik çatı, veranda önde."
    # form olmayan mesajın satırı değişmez (alan eklenmez)
    t = {"id": "wamid.T1", "from": "900000000101", "timestamp": "1", "type": "text", "text": {"body": "merhaba"}}
    assert "form" not in WH.kuyruk_satiri(t, t["id"], "900000000101", "text", 1, {}, None, {}, "1", 1)


def test_satir_tokeni():
    satir = W.giden_form({"id": "wamid.G1", "sender": "900000000101"}, "x", 1, "revizyon", FORM, "rv:TF-1:1", {"plan": "p"})
    assert TF.satir_tokeni(satir) == "rv:TF-1:1" and TF.satir_tokeni({"kind": "text"}) is None


def test_form_mesaji_govdesi_ve_sunus_kurali():
    """Kod incelemesi (27.10): form düğmeli mesaj metnin satır sonlarını korur; gövdeye (1024) sığmayan metin formla gitmez (bugünkü düz
    metin, kesilmez). Talep formunun token'ı taslaktan doldurulduysa ':1' taşır (cevap açık taslağı tamamlar), doldurulmadıysa taşımaz."""
    from types import SimpleNamespace as NS
    gelen = {"id": "wamid.SORU1", "sender": "900000000101"}
    r = W.giden_form(gelen, "Birinci satır.\n\nİkinci satır.", 0, "talep", FORM, "tf:abc", TF.ekran_verisi(None, None))
    assert r["interactive"]["body"]["text"] == "Birinci satır.\n\nİkinci satır."
    assert M.mesaj_yuku(r, "900000000101")["interactive"]["body"]["text"] == "Birinci satır.\n\nİkinci satır."

    class K:
        def __init__(self, d):
            self.d = d
    soru = NS(eylem="sor", soru_alani="dis_olcu", gerekce="eksik: dis_olcu")
    bos = K({"asama": "yeni", "taslak": {}})
    dolu = K({"asama": "topluyor", "taslak": {"oda_programi": "2+1"}})
    fs = W.form_sunusu(gelen, soru, bos, None, FORM, "Dış ölçü?")
    assert fs[0] == "talep" and TF.TOKEN.match(fs[1]).group(3) is None
    fs = W.form_sunusu(gelen, soru, dolu, None, FORM, "Dış ölçü?")
    assert fs[1].endswith(":1") and fs[2]["oda"] == "2+1"
    assert W.form_sunusu(gelen, soru, dolu, None, FORM, "x" * (W.WA_GOVDE + 1)) is None
    rev = NS(eylem="sor", soru_alani="revizyon_ne", gerekce="revizyon")
    k = K({"asama": "onay_bekliyor", "son_is_emri": {"is_emri_no": "IE-2610-0001", "revizyon": 2}})
    fs = W.form_sunusu(gelen, rev, k, None, FORM, "Neyi değiştirelim?")
    assert fs[:2] == ("revizyon", "rv:IE-2610-0001:2") and fs[3:] == ("IE-2610-0001", 2)
    # aynı planın formu güncel sayılır (sunuş ve çözüm aynı revizyonu okur)
    g = {"form": {"tur": "revizyon", "token": fs[1], "alanlar": {"neyi": ["pencere"]}, "dosyalar": []}}
    assert W.form_cikarimi(g, k.d)["durum"] == "bos"
