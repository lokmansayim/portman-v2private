"""İE-06 · kanal/meta_api.py: imza, hub doğrulaması, gelen olay çözümü, dosya denetimi, yük kurucuları (feature.php sınırları),
kabul koşulu ve Graph istemcisi (sahte http ile). Ağa, Postgres'e, LLM'e bağlanmaz. Sahte anahtarlar çalışma anında kurulur
(kaynakta anahtara benzeyen dizi yok)."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import pytest

import meta_api as M

SAHTE_SIR = "sahte-app-" + "0123456789" * 2                 # app secret rolünde; gerçek değil
SAHTE_TOKEN = "EAA" + "sahteToken" + "A" * 30               # Meta belirtecine benzer (maskeleme sınanır); gerçek değil
SAHTE_SK = "sk-ant-" + "sahte" * 5
AYAR = M.MetaAyar(phone_number_id="106000000000001", access_token=SAHTE_TOKEN, app_secret=SAHTE_SIR,
                  verify_token="dogrulama-belirteci-xyz", graph_version="v23.0")


# ───────────────────────── imza ve hub ─────────────────────────
def test_imza_dogru_yanlis_eksik():
    govde = b'{"object":"whatsapp_business_account"}'
    bas = "sha256=" + hmac.new(SAHTE_SIR.encode(), govde, hashlib.sha256).hexdigest()
    assert M.imza_gecerli(govde, bas, SAHTE_SIR)
    assert M.imza_gecerli(govde, bas.upper().replace("SHA256=", "sha256="), SAHTE_SIR)    # büyük harfli hex de geçer
    assert M.imzala(govde, SAHTE_SIR) == bas
    assert not M.imza_gecerli(govde, bas, "baska-deger")
    assert not M.imza_gecerli(govde + b" ", bas, SAHTE_SIR)
    assert not M.imza_gecerli(govde, None, SAHTE_SIR)
    assert not M.imza_gecerli(govde, bas[7:], SAHTE_SIR)                                  # 'sha256=' öneki şart
    assert not M.imza_gecerli(govde, bas, "")                                             # app secret yoksa hiçbir şey geçmez


def test_hub_cevabi():
    assert M.hub_cevabi({"hub.mode": "subscribe", "hub.verify_token": "dogrulama-belirteci-xyz", "hub.challenge": "12345"}, "dogrulama-belirteci-xyz") == "12345"
    assert M.hub_cevabi({"hub.mode": "subscribe", "hub.verify_token": "yanlis", "hub.challenge": "12345"}, "dogrulama-belirteci-xyz") is None
    assert M.hub_cevabi({"hub.mode": "unsubscribe", "hub.verify_token": "dogrulama-belirteci-xyz"}, "dogrulama-belirteci-xyz") is None
    assert M.hub_cevabi({"hub.mode": "subscribe", "hub.verify_token": ""}, "") is None


def test_numara_ve_wamid():
    assert M.numara_gecerli("900000000133") and M.numara_gecerli("490000000001")
    assert not M.numara_gecerli("0555") and not M.numara_gecerli("+900000000133") and not M.numara_gecerli("900000000133x")
    assert M.wamid_gecerli("wamid.HBgLOTAwMDAwMDAwMTMzFQIAEhgUM0E5") and not M.wamid_gecerli("12345") and not M.wamid_gecerli("wamid." + "x" * 300)


# ───────────────────────── gelen olay ─────────────────────────
def test_gelen_metin_turleri():
    assert M.gelen_metin({"type": "text", "text": {"body": "P6001 aynalı"}}) == "P6001 aynalı"
    assert M.gelen_metin({"type": "button", "button": {"text": "Onayla", "payload": "o:PM-1:1"}}) == "Onayla"
    assert M.gelen_metin({"type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": "o:X:1", "title": "Onayla"}}}) == "Onayla"
    assert M.gelen_metin({"type": "interactive", "interactive": {"type": "list_reply", "list_reply": {"id": "s:ss:TEST01", "title": "1. TEST01"}}}) == "1. TEST01"
    assert M.gelen_metin({"type": "image", "image": {"id": "123", "caption": "plan"}}) == "plan"
    assert M.gelen_metin({"type": "document", "document": {"id": "123", "filename": "a.pdf"}}) == "a.pdf"
    assert M.gelen_metin({"type": "location", "location": {"name": "Ofis", "latitude": 41.0, "longitude": 29.0}}) == "Konum: Ofis 41.0, 29.0"
    assert M.gelen_metin({"type": "reaction", "reaction": {"emoji": "x"}}) == "" and M.gelen_metin({}) == ""


def test_cevap_kimligi():
    assert M.cevap_kimligi({"type": "interactive", "interactive": {"button_reply": {"id": "o:PM-1:1", "title": "Onayla"}}}) == ("o:PM-1:1", "button_reply")
    assert M.cevap_kimligi({"type": "interactive", "interactive": {"button_reply": {"id": "a"}, "list_reply": {"id": "s:ss:K", "title": "K"}}}) == ("s:ss:K", "list_reply")
    assert M.cevap_kimligi({"type": "button", "button": {"payload": "q:oncelik:butce", "text": "Bütçe"}}) == ("q:oncelik:butce", "button")
    assert M.cevap_kimligi({"type": "text", "text": {"body": "o:PM-1:1"}}) == (None, None)                 # metin kimlik değildir
    assert M.cevap_kimligi({"type": "interactive", "interactive": {"button_reply": {"id": ""}}}) == (None, None)
    assert M.cevap_kimligi({"type": "interactive", "interactive": {"button_reply": {"id": "a\x01b"}}}) == (None, None)
    assert M.cevap_kimligi({"type": "interactive", "interactive": {"button_reply": {"id": "x" * 257}}}) == (None, None)


def test_medya_bilgisi():
    assert M.medya_bilgisi({"type": "document", "document": {"id": "77", "filename": "plan.pdf", "mime_type": "application/pdf"}}) == ("77", "plan.pdf", "application/pdf")
    assert M.medya_bilgisi({"type": "image", "image": {"id": 88}}) == ("88", None, None)
    assert M.medya_bilgisi({"type": "text", "text": {"body": "x"}}) == (None, None, None)


# ───────────────────────── dosya denetimi ─────────────────────────
def _dosya(kok: Path, ad: str, veri: bytes) -> Path:
    p = kok / "projects" / "PM-1" / "r01" / ad
    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(veri)
    return p


def test_dosya_denetle(tmp_path, monkeypatch):
    kok = tmp_path / "kanal"
    pdf = _dosya(kok, "a.pdf", b"%PDF-1.4\nicerik")
    png = _dosya(kok, "a.png", b"\x89PNG\r\n\x1a\n" + b"x" * 10)
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert M.dosya_denetle(str(pdf), ("application/pdf",), kok, sha) == (pdf.resolve(), "application/pdf")
    assert M.dosya_denetle(str(png), ("image/png", "image/jpeg"), kok)[1] == "image/png"
    with pytest.raises(M.DosyaGecersiz, match="local_file_changed"):
        M.dosya_denetle(str(pdf), ("application/pdf",), kok, "0" * 64)
    with pytest.raises(M.DosyaGecersiz, match="file_type_not_allowed"):
        M.dosya_denetle(str(png), ("application/pdf",), kok)
    with pytest.raises(M.DosyaGecersiz, match="file_type_unknown"):
        M.dosya_denetle(str(_dosya(kok, "a.bin", b"ABCDEFGH")), ("application/pdf",), kok)
    disarida = tmp_path / "disarida.pdf"; disarida.write_bytes(b"%PDF-1.4")
    with pytest.raises(M.DosyaGecersiz, match="local_file_invalid"):
        M.dosya_denetle(str(disarida), ("application/pdf",), kok)
    with pytest.raises(M.DosyaGecersiz, match="local_file_invalid"):
        M.dosya_denetle(str(kok / "projects" / "yok.pdf"), ("application/pdf",), kok)
    with pytest.raises(M.DosyaGecersiz, match="local_file_invalid"):
        M.dosya_denetle(str(_dosya(kok, "bos.pdf", b"")), ("application/pdf",), kok)
    monkeypatch.setattr(M, "PDF_EN_COK", 4)
    with pytest.raises(M.DosyaGecersiz, match="pdf_too_large"):
        M.dosya_denetle(str(pdf), ("application/pdf",), kok)
    monkeypatch.setattr(M, "GORSEL_EN_COK", 4)
    with pytest.raises(M.DosyaGecersiz, match="image_too_large"):
        M.dosya_denetle(str(png), ("image/png",), kok)


# ───────────────────────── etkileşimli yük ve sınırlar ─────────────────────────
def _buton_satiri(butonlar, **ek) -> dict:
    return {"id": "out_1", "kind": "interactive", "body": "Seçin", "interactive": {"type": "button", "body": {"text": "Seçin"},
            "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": t}} for i, t in butonlar]}, **ek}}


def test_etkilesim_buton_sinirlari():
    y = M.etkilesim_yuku(_buton_satiri([("o:PM-1:1", "Onayla"), ("r:PM-1:1", "Revize et")]), None)
    assert y["type"] == "button" and [b["reply"]["id"] for b in y["action"]["buttons"]] == ["o:PM-1:1", "r:PM-1:1"]
    with pytest.raises(M.EtkilesimGecersiz, match="buttons"):
        M.etkilesim_yuku(_buton_satiri([(f"b{i}", f"B{i}") for i in range(4)]), None)                   # 4 buton
    with pytest.raises(M.EtkilesimGecersiz, match="buttons"):
        M.etkilesim_yuku(_buton_satiri([]), None)
    with pytest.raises(M.EtkilesimGecersiz, match="button"):
        M.etkilesim_yuku(_buton_satiri([("b1", "x" * 21)]), None)                                      # başlık 21
    with pytest.raises(M.EtkilesimGecersiz, match="button"):
        M.etkilesim_yuku(_buton_satiri([("ayni", "A"), ("ayni", "B")]), None)                          # aynı kimlik
    with pytest.raises(M.EtkilesimGecersiz, match="footer"):
        M.etkilesim_yuku(_buton_satiri([("b1", "A")], footer={"text": "y" * 61}), None)
    with pytest.raises(M.EtkilesimGecersiz, match="header media"):
        M.etkilesim_yuku(_buton_satiri([("b1", "A")], header={"type": "image", "file": "/x.png"}), None)
    y = M.etkilesim_yuku(_buton_satiri([("b1", "A")], header={"type": "image", "file": "/x.png"}, footer={"text": "PM-1 r01"}), "555")
    assert y["header"] == {"type": "image", "image": {"id": "555"}} and y["footer"] == {"text": "PM-1 r01"}
    with pytest.raises(M.EtkilesimGecersiz, match="header type"):
        M.etkilesim_yuku(_buton_satiri([("b1", "A")], header={"type": "video"}), None)
    with pytest.raises(M.EtkilesimGecersiz, match="body"):
        M.etkilesim_yuku({"id": "o", "kind": "interactive", "body": "", "interactive": {"type": "button", "action": {"buttons": [{"id": "b", "title": "B"}]}}}, None)
    with pytest.raises(M.EtkilesimGecersiz, match="type"):
        M.etkilesim_yuku({"id": "o", "kind": "interactive", "body": "x", "interactive": {"type": "product"}}, None)
    # Meta biçimi olmayan (id/title doğrudan) butonlar da kabul edilir (etkilesim.mesaj_kimlikleri ile aynı okuma)
    y = M.etkilesim_yuku({"id": "o", "kind": "interactive", "body": "x", "interactive": {"type": "button", "action": {"buttons": [{"id": "b", "title": "B"}]}}}, None)
    assert y["action"]["buttons"] == [{"type": "reply", "reply": {"id": "b", "title": "B"}}]


def test_etkilesim_liste_ve_cta():
    satirlar = [{"id": f"s:ss:K{i}", "title": f"K{i}", "description": "" if i % 2 else "açıklama"} for i in range(10)]
    liste = {"id": "o", "kind": "interactive", "body": "Tümü", "interactive": {"type": "list", "body": {"text": "Tümü"},
             "action": {"button": "Seçenekleri gör", "sections": [{"title": "Puana göre", "rows": satirlar}]}}}
    y = M.etkilesim_yuku(liste, None)
    assert len(y["action"]["sections"][0]["rows"]) == 10 and "description" not in y["action"]["sections"][0]["rows"][1]
    liste["interactive"]["action"]["sections"][0]["rows"] = satirlar + [{"id": "s:ss:K10", "title": "K10"}]
    with pytest.raises(M.EtkilesimGecersiz, match="rows"):
        M.etkilesim_yuku(liste, None)                                                                   # 11 satır
    liste["interactive"]["action"]["sections"][0]["rows"] = [{"id": "s", "title": "x" * 25}]
    with pytest.raises(M.EtkilesimGecersiz, match="row"):
        M.etkilesim_yuku(liste, None)
    liste["interactive"]["action"]["sections"][0]["rows"] = [{"id": "s", "title": "K", "description": "a" * 73}]
    with pytest.raises(M.EtkilesimGecersiz, match="row"):
        M.etkilesim_yuku(liste, None)
    liste["interactive"]["action"]["sections"][0]["rows"] = [{"id": "s", "title": "K"}]
    liste["interactive"]["action"]["button"] = "x" * 21
    with pytest.raises(M.EtkilesimGecersiz, match="list button"):
        M.etkilesim_yuku(liste, None)
    liste["interactive"]["action"]["button"] = "Gör"; liste["interactive"]["header"] = {"type": "image"}
    with pytest.raises(M.EtkilesimGecersiz, match="list header image"):
        M.etkilesim_yuku(liste, "1")
    cta = {"id": "o", "kind": "interactive", "body": "3D", "interactive": {"type": "cta_url", "body": {"text": "3D"},
           "action": {"name": "cta_url", "parameters": {"display_text": "3D'de gez", "url": "https://ornek.invalid/3d/PM-1/r01/"}}}}
    assert M.etkilesim_yuku(cta, None)["action"]["parameters"]["url"].endswith("/r01/")
    cta["interactive"]["action"]["parameters"]["url"] = "http://ornek.invalid/3d"
    with pytest.raises(M.EtkilesimGecersiz, match="cta_url"):
        M.etkilesim_yuku(cta, None)
    cta["interactive"]["action"]["parameters"] = {"display_text": "x" * 21, "url": "https://ornek.invalid/3d"}
    with pytest.raises(M.EtkilesimGecersiz, match="cta_url"):
        M.etkilesim_yuku(cta, None)


def test_mesaj_yuku_turleri():
    m = M.mesaj_yuku({"id": "out_1", "kind": "text", "body": "x" * 5000}, "900000000133")
    assert m["type"] == "text" and len(m["text"]["body"]) == 4000 and m["text"]["preview_url"] is False
    assert m["biz_opaque_callback_data"] == "out_1" and m["to"] == "900000000133" and m["recipient_type"] == "individual"
    with pytest.raises(ValueError, match="empty_text"):
        M.mesaj_yuku({"id": "out_1", "kind": "text", "body": "  "}, "900000000133")
    d = M.mesaj_yuku({"id": "out_2", "kind": "document", "body": "a" * 1500, "filename": "plan.pdf"}, "900000000133", medya_id="9")
    assert d["document"] == {"id": "9", "filename": "plan.pdf", "caption": "a" * 1000}
    with pytest.raises(ValueError, match="media_id"):
        M.mesaj_yuku({"id": "out_2", "kind": "document", "filename": "plan.pdf"}, "900000000133")
    g = M.mesaj_yuku({"id": "out_3", "kind": "image", "body": "b" * 1100}, "900000000133", medya_id="8")
    assert g["image"] == {"id": "8", "caption": "b" * 1024}
    g2 = M.mesaj_yuku({"id": "out_3", "kind": "image", "body": " "}, "900000000133", medya_id="8")
    assert "caption" not in g2["image"]
    e = M.mesaj_yuku(_buton_satiri([("b1", "A")], header={"type": "image", "file": "/x.png"}), "900000000133", baslik_medya_id="4")
    assert e["type"] == "interactive" and e["interactive"]["header"]["image"]["id"] == "4"


def test_kabul_edilen_wamid():
    ok = {"messaging_product": "whatsapp", "contacts": [{"input": "900000000133", "wa_id": "900000000133"}], "messages": [{"id": "wamid.OUT1"}]}
    assert M.kabul_edilen_wamid(ok, "900000000133") == "wamid.OUT1"
    with pytest.raises(M.MetaHatasi, match="send_response_uncertain"):
        M.kabul_edilen_wamid({**ok, "contacts": [{"input": "900000000199", "wa_id": "900000000199"}]}, "900000000133")
    with pytest.raises(M.MetaHatasi, match="send_response_uncertain"):
        M.kabul_edilen_wamid({**ok, "messages": [{"id": "12345"}]}, "900000000133")
    with pytest.raises(M.MetaHatasi, match="send_response_uncertain"):
        M.kabul_edilen_wamid({}, "900000000133")


def test_maskele():
    s = M.maskele(f"HTTP 401: belirteç {SAHTE_TOKEN} geçersiz; {SAHTE_SK} de", SAHTE_TOKEN)
    assert "EAA" not in s and "sk-ant" not in s and s.count("[GİZLİ]") == 2


# ───────────────────────── Graph istemcisi (sahte http) ─────────────────────────
class SahteHttp:
    def __init__(self, cevaplar):
        self.cevaplar = list(cevaplar); self.istekler = []

    def __call__(self, method, url, headers, data, timeout):
        self.istekler.append({"method": method, "url": url, "headers": headers, "data": data, "timeout": timeout})
        durum, govde = self.cevaplar.pop(0)
        return durum, {}, (json.dumps(govde).encode() if isinstance(govde, (dict, list)) else govde)


def test_gonder_ve_hata_maskeli():
    http = SahteHttp([(200, {"messages": [{"id": "wamid.OUT1"}], "contacts": [{"input": "900000000133", "wa_id": "900000000133"}]}),
                      (401, {"error": {"message": "Invalid OAuth access token " + SAHTE_TOKEN, "type": "OAuthException", "code": 190}})])
    g = M.GraphIstemci(AYAR, http=http)
    c = g.gonder({"to": "900000000133"})
    assert c["messages"][0]["id"] == "wamid.OUT1"
    i = http.istekler[0]
    assert i["method"] == "POST" and i["url"] == "https://graph.facebook.com/v23.0/106000000000001/messages"
    assert i["headers"]["Authorization"] == "Bearer " + AYAR.access_token and i["headers"]["Content-Type"] == "application/json"
    assert json.loads(i["data"]) == {"to": "900000000133"}
    with pytest.raises(M.MetaHatasi) as ei:
        g.gonder({"to": "900000000133"})
    assert ei.value.kod == 401 and "OAuthException" in str(ei.value) and AYAR.access_token not in str(ei.value) and "EAA" not in str(ei.value)


def test_medya_yukle_ve_indir(tmp_path):
    p = tmp_path / "plan.pdf"; p.write_bytes(b"%PDF-1.4 icerik")
    http = SahteHttp([(200, {"id": "123456"}), (200, {"id": "abc"}),
                      (200, {"url": "https://lookaside.invalid/m/1", "mime_type": "image/jpeg", "file_size": 3}), (200, b"\xff\xd8\xff"),
                      (200, {"url": "https://lookaside.invalid/m/2", "mime_type": "application/pdf", "file_size": 99999999})])
    g = M.GraphIstemci(AYAR, http=http)
    assert g.medya_yukle(p, "application/pdf", "plan.pdf") == "123456"
    i = http.istekler[0]
    assert i["url"].endswith("/106000000000001/media") and i["headers"]["Content-Type"].startswith("multipart/form-data; boundary=")
    assert b'name="messaging_product"\r\n\r\nwhatsapp' in i["data"] and b'filename="plan.pdf"' in i["data"] and b"%PDF-1.4 icerik" in i["data"]
    with pytest.raises(M.MetaHatasi, match="media_response"):
        g.medya_yukle(p, "application/pdf", "plan.pdf")
    veri, mime = g.medya_indir("777")
    assert (veri, mime) == (b"\xff\xd8\xff", "image/jpeg")
    assert http.istekler[2]["url"] == "https://graph.facebook.com/v23.0/777" and http.istekler[3]["url"] == "https://lookaside.invalid/m/1"
    assert http.istekler[3]["headers"]["Authorization"].startswith("Bearer ")
    with pytest.raises(M.MetaHatasi, match="media_too_large"):
        g.medya_indir("778")
    with pytest.raises(M.MetaHatasi, match="media_id"):
        g.medya_indir("../x")


def test_ayar_ortamdan_ve_telefon():
    a = M.MetaAyar.ortamdan({"WA_PHONE_NUMBER_ID": "1", "WA_ACCESS_TOKEN": "t", "WA_APP_SECRET": "s", "WA_VERIFY_TOKEN": "v"})
    assert a.tam_mi() and a.graph_version == M.GRAPH_SURUM_VARSAYILAN
    assert not M.MetaAyar.ortamdan({}).tam_mi()
    http = SahteHttp([(200, {"display_phone_number": "+90 555", "verified_name": "PortatifEv"})])
    assert M.GraphIstemci(a, http=http).telefon()["verified_name"] == "PortatifEv"
    assert http.istekler[0]["url"].startswith("https://graph.facebook.com/v23.0/1?fields=")


# ───────────────────────── İE-07: şablon mesajı ─────────────────────────
def _sablon_satiri(**ek) -> dict:
    s = {"id": "out_s1", "kind": "template", "body": "Portman: B1234 kodlu bayinin PM-1 numaralı talebi sizi bekliyor.",
         "sablon": {"ad": "portman_patron_bekliyor_v1", "dil": "tr", "govde": ["B1234", "PM-B1234-20261011-1"],
                    "dugmeler": [{"sub_type": "url", "index": 0, "text": "konusma/900000000133"}]}}
    s["sablon"] = {**s["sablon"], **ek}
    return s


def test_sablon_yuku_ve_mesaj_yuku_template():
    y = M.mesaj_yuku(_sablon_satiri(), "900000000909")
    assert y["type"] == "template" and y["to"] == "900000000909" and y["biz_opaque_callback_data"] == "out_s1"
    assert y["template"] == {"name": "portman_patron_bekliyor_v1", "language": {"code": "tr"}, "components": [
        {"type": "body", "parameters": [{"type": "text", "text": "B1234"}, {"type": "text", "text": "PM-B1234-20261011-1"}]},
        {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": "konusma/900000000133"}]}]}
    q = M.sablon_yuku(_sablon_satiri(dugmeler=[{"sub_type": "quick_reply", "index": 0, "payload": "dosya:PM-B1234-20261011-1"}]))
    assert q["components"][1] == {"type": "button", "sub_type": "quick_reply", "index": "0", "parameters": [{"type": "payload", "payload": "dosya:PM-B1234-20261011-1"}]}
    assert "components" not in M.sablon_yuku({"sablon": {"ad": "x_1", "dil": "tr"}})            # değişkensiz şablon
    assert M.sablon_metni("Merhaba {{1}}, {{2}} hazır.", ["Ahmet Bey", "PM-1"]) == "Merhaba Ahmet Bey, PM-1 hazır."


@pytest.mark.parametrize("ek, alan", [
    ({"ad": ""}, "name"), ({"ad": "Büyük-Ad"}, "name"), ({"dil": "türkçe"}, "language"),
    ({"govde": ["B1234", ""]}, "body 2"), ({"govde": ["B1234", "satır\nsonu"]}, "body 2"), ({"govde": ["çok    boşluk", "PM-1"]}, "body 1"),
    ({"govde": ["x" * 1025, "PM-1"]}, "body 1"), ({"dugmeler": [{"sub_type": "url", "index": 0, "text": ""}]}, "button url"),
    ({"dugmeler": [{"sub_type": "url", "index": 0, "text": "a b"}]}, "button url"), ({"dugmeler": [{"sub_type": "quick_reply", "index": 0, "payload": ""}]}, "button payload"),
    ({"dugmeler": [{"sub_type": "copy_code", "index": 0}]}, "button type"), ({"dugmeler": [{"sub_type": "url", "index": "0", "text": "k"}]}, "button index"),
])
def test_sablon_yuku_gecersiz(ek, alan):
    with pytest.raises(M.SablonGecersiz, match="template_invalid: " + alan):
        M.sablon_yuku(_sablon_satiri(**ek))
    with pytest.raises(ValueError):                                     # gonderici: ValueError → Gonderilmedi
        M.mesaj_yuku(_sablon_satiri(**ek), "900000000909")
