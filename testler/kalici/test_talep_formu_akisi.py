"""İE-20 PR-2 · talep formu ve revizyon formu, kalıcı akış (gerçek Postgres, sahte WhatsApp, kayıtlı okuma; LLM yok).

F1: eksik bilgi sorusu, selam ve "Nasıl çalışır?" cevabı aynı metinle [Talep formu] düğmeli gider; form açık taslağın bilgileri ve bayi
kartının varsayılanlarıyla dolu açılır; ayar kapalıyken bugünkü metin. F2: form cevabı LLM'siz talebe çevrilir → plan; formdaki dosya
PR-1'in okumasından geçer (okuma kapalıysa ya da plan çıkmazsa formun bilgileriyle, dosya Patron'a). F3: "Revize et" → [Revizyon formu];
açıklama bayinin yazısı gibi okunur; eski plan formu, boş form ve yalnız dosyalı form LLM'siz cevaplanır. Webhook: form cevabı ve
dosyası kayda girer. Panel: kartın form varsayılanları (göç 009).

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_talep_formu_akisi.py -q
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import kalici
import meta_api as M
import sablonlar as S
import talep_formu as TF
import worker as W
from test_gorsel_akisi import BASIT, buton, dugmeler
from test_webhook import app, kanal, post, yuk          # noqa: F401  (webhook fikstürleri)

BAYI_KART = {**BAYI_A, "numara": NUMARA_A}
FORM_AYARI = {"acik": True, "talep_flow_id": "1111111111", "revizyon_flow_id": "2222222222", "taslak": True}
PLAN = {"yapi": "prefabrik", "kat": "1", "oda": "2+1", "en": "7,73", "boy": "10,14", "cati": "besik", "veranda": "on"}


def ayar(tmp_path: Path, acik: bool = True, okuma: dict | None = None, gorsel: bool = False) -> dict:
    s = {**AYAR, "mesaj_katmani": True, "talep_formu": {**FORM_AYARI, "acik": acik}}
    if gorsel:
        h = tmp_path / "hazir_gorsel.json"
        h.write_text(json.dumps({"okuma": okuma, "duzeltme": None}, ensure_ascii=False), encoding="utf-8")
        s["gorsel_okuma"] = {"acik": True, "backend": "manuel", "hazir_dosya": str(h), "bekle_sn": 0}
    return s


def isle_hepsi(depo, s: dict) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, s, "test-isleyici")) is not None:
        out.append(r)
    return out


def son_sonuc(depo) -> dict:
    return tek(depo, "SELECT sonuc FROM isler ORDER BY id DESC LIMIT 1")["sonuc"]


def son_satirlar(depo) -> list[dict]:
    return sorgu(depo, "SELECT alici, kind, govde, satir, dis_id FROM giden WHERE mesaj_id = (SELECT mesaj_id FROM isler ORDER BY id DESC LIMIT 1) "
                       "ORDER BY sira")


def bayiye(depo) -> list[dict]:
    return [x for x in son_satirlar(depo) if x["alici"] == NUMARA_A]


def patrona(depo) -> list[dict]:
    return [x for x in son_satirlar(depo) if x["alici"] == "PATRON"]


def form_satiri(depo, wa) -> tuple[dict, str]:
    """Son işin bayiye giden form mesajı (gönderilir; Meta yükü denetlenir) ve dış kimliği."""
    [x] = [x for x in bayiye(depo) if x["kind"] == "interactive" and x["satir"]["interactive"]["type"] == "flow"]
    yuk_ = M.mesaj_yuku(x["satir"], NUMARA_A)                               # gönderici aynı denetimden geçirir
    assert yuk_["interactive"]["action"]["parameters"]["mode"] == "draft"
    kalici.gonder(depo, wa)
    return x["satir"], tek(depo, "SELECT dis_id FROM giden WHERE id = %s", x["satir"]["id"])["dis_id"]


def parametreler(satir: dict) -> dict:
    return satir["interactive"]["action"]["parameters"]


def form_cevabi(depo, tmp_path: Path, token: str, alanlar: dict, context_id: str | None, cikarim: dict | None = None, dosya: str | None = None,
                bayi: dict | None = None) -> dict:
    """Bayi formu gönderir (webhook'un yazdığı biçimde); `dosya` mime ise formda bir dosya, gönderici indirmiş gibi."""
    rj = {"flow_token": token, **alanlar}
    if dosya:
        rj["dosya"] = [{"file_name": "plan.jpg" if dosya != "application/pdf" else "plan.pdf", "mime_type": dosya, "sha256": "x=", "id": "36311207"}]
    oz = TF.cevap_ozeti(json.dumps(rj, ensure_ascii=False))
    g = mesaj(TF.metin(oz), cikarim, bayi=bayi or BAYI_KART, context_id=context_id, tur="interactive")
    g["form"] = oz
    assert depo.mesaj_kaydet(g)
    if dosya:
        depo.gelen_dosya_ekle(g["id"], "36311207", rj["dosya"][0]["file_name"], dosya)
        yol = tmp_path / "gelen_medya" / g["id"][-8:] / rj["dosya"][0]["file_name"]
        yol.parent.mkdir(parents=True, exist_ok=True)
        icerik = b"\xff\xd8\xff sahte cizim"
        yol.write_bytes(icerik)
        d = depo.mesajin_dosyasi(g["id"])
        depo.gelen_dosya_indirildi(d["id"], str(yol), dosya, len(icerik), hashlib.sha256(icerik).hexdigest())
    return g


def soru_al(depo, wa, s) -> tuple[dict, str]:
    """2+1 yazılır, dış ölçü sorulur: soru [Talep formu] düğmeli."""
    assert depo.mesaj_kaydet(mesaj("2+1 istiyorum", talep(ozet="2+1", oda_programi="2+1"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "eksik: dis_olcu", r
    return form_satiri(depo, wa)


def plan_al(depo, wa, tmp_path, s) -> tuple[str, str]:
    """Formla r01; dönen: (İş Emri no, onay mesajının dış kimliği)."""
    satir, dis = soru_al(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], PLAN, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    no = tek(depo, "SELECT is_emri_no FROM revizyonlar ORDER BY id DESC LIMIT 1")["is_emri_no"]
    dis_onay = sorgu(depo, "SELECT dis_id FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC, sira DESC")[0]["dis_id"]
    return no, dis_onay


# ─── F1 · form sunuşu ───
def test_f1_eksik_bilgi_sorusu_formla_kart_ve_taslak_secili(depo, wa, tmp_path):
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"])
    depo.bayi_varsayilanlari_yaz(NUMARA_A, veranda="kose", cati="tek_egimli")
    bayi = depo.gelen_bayisi(NUMARA_A)
    assert bayi["varsayilanlar"] == {"cati": "tek_egimli", "veranda": "kose"}
    s = ayar(tmp_path)
    assert depo.mesaj_kaydet(mesaj("2+1 istiyorum", talep(ozet="2+1", oda_programi="2+1"), bayi=bayi))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and son_sonuc(depo)["form_sunuldu"] == "talep"
    [x] = bayiye(depo)                                                     # ek mesaj yok: düğme sorunun kendisinde
    satir, _ = form_satiri(depo, wa)
    assert satir["body"] == "Dış ölçü (kısa x uzun, metre) ya da yaklaşık m² verir misiniz?"
    p = parametreler(satir)
    assert p["flow_id"] == "1111111111" and p["flow_cta"] == "Talep formu" and p["flow_token"].startswith("tf:")
    veri = p["flow_action_payload"]["data"]
    assert (veri["oda"], veri["yapi"], veri["veranda"], veri["cati"], veri["en"]) == ("2+1", "prefabrik", "kose", "tek_egimli", "")
    assert veri["bilinen"].startswith("Bildiklerim: 2+1.")


def test_f1_ayar_kapaliyken_bugunku_metin(depo, wa, tmp_path):
    s = ayar(tmp_path, acik=False)
    assert depo.mesaj_kaydet(mesaj("2+1 istiyorum", talep(ozet="2+1", oda_programi="2+1"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and "form_sunuldu" not in son_sonuc(depo)
    [x] = bayiye(depo)
    assert x["kind"] == "text" and x["govde"] == "Dış ölçü (kısa x uzun, metre) ya da yaklaşık m² verir misiniz?"
    # kimlik yoksa da (form Meta'da kurulmadan açılırsa) bugünkü metin
    s2 = {**s, "talep_formu": {**FORM_AYARI, "talep_flow_id": None}}
    assert depo.mesaj_kaydet(mesaj("merhaba", talep("selam", "selam"), bayi=BAYI_KART))
    isle_hepsi(depo, s2)
    assert [x["kind"] for x in bayiye(depo)] == ["text"]


def test_f1_selam_anlasilmadi_ve_nasil_calisir(depo, wa, tmp_path):
    s = ayar(tmp_path)
    for metin, t in (("merhaba", talep("selam", "selam")), ("hmm", talep("diger", "anlaşılmadı"))):
        assert depo.mesaj_kaydet(mesaj(metin, t, bayi=BAYI_KART))
        [r] = isle_hepsi(depo, s)
        assert son_sonuc(depo)["form_sunuldu"] == "talep", r
        satir, _ = form_satiri(depo, wa)
        assert satir["body"].startswith(("Merhaba", "Anlayamadım"))
    g = mesaj("Nasıl çalışır?", None, bayi=BAYI_KART, tur="button")
    g["reply_id"] = S.BILGI_NASIL; g["reply_kind"] = "button"
    assert depo.mesaj_kaydet(g)
    isle_hepsi(depo, s)
    kinds = [x["kind"] for x in bayiye(depo)]
    assert kinds == ["document", "interactive"]
    satir, _ = form_satiri(depo, wa)
    assert satir["body"].startswith("Talebinizi bu sohbete yazabilir ya da formu doldurabilirsiniz")


# ─── F2 · form cevabı ───
def test_f2_form_cevabi_llmsiz_plan(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    satir, dis = soru_al(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {**PLAN, "not": "Salon geniş olsun"}, dis)   # kayıtlı LLM çıkarımı yok
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    j = tek(depo, "SELECT cikarim, sonuc FROM isler ORDER BY id DESC LIMIT 1")
    assert j["cikarim"]["form"]["durum"] == "talep" and "talep" not in j["cikarim"]           # LLM çağrılmadı
    assert j["sonuc"]["llm"]["backend"] == "form" and j["sonuc"]["form"] == {"tur": "talep", "durum": "talep", "dosya": 0}
    ie = tek(depo, "SELECT is_emri FROM revizyonlar")["is_emri"]
    assert ie["ozel_istekler"] == ["Salon geniş olsun"] and ie["yapi"]["sistem"] == "prefabrik"
    [onay] = [x for x in bayiye(depo) if x["kind"] == "interactive"]
    assert onay["govde"].endswith(W.FORM_NOTU)                                # not plana özel istek olarak yazıldı; bayiye söylenir


def test_f2_eksik_kalan_yine_formla_sorulur(depo, wa, tmp_path):
    s = ayar(tmp_path)
    satir, dis = soru_al(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], {"yapi": "prefabrik", "kat": "1", "oda": "2+1", "cati": "besik", "veranda": "on"}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "eksik: dis_olcu" and son_sonuc(depo)["form_sunuldu"] == "talep"


def test_f2_formdaki_dosya_okunur_teyit(depo, wa, tmp_path):
    s = ayar(tmp_path, okuma={**BASIT, "yapi_turu": None}, gorsel=True)
    satir, dis = soru_al(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], PLAN, dis, dosya="image/jpeg")
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "çizim okundu: teyit", r
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["okuma"]["yapi_turu"] == "prefabrik"               # okumanın boş bıraktığı yapı tipi formdan
    [x] = [x for x in bayiye(depo) if x["kind"] == "interactive"]
    assert dugmeler(x) == [f"c:{d['cizim_okuma']['iz']}:d", f"c:{d['cizim_okuma']['iz']}:z"]
    j = tek(depo, "SELECT cikarim FROM isler ORDER BY id DESC LIMIT 1")["cikarim"]
    assert j["form"]["dosya"] is True and j["gorsel"]["durum"] == "tamam"
    assert patrona(depo) == []                                                # okunan dosya Patron'a ayrıca bildirilmez (PR-1 gibi)


def test_f2_okuma_kapaliyken_ya_da_plan_cikmazsa_form_bilgileriyle(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)                                                      # görsel okuma kapalı
    satir, dis = soru_al(depo, wa, s)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], PLAN, dis, dosya="application/pdf")
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    assert any("talep formuna dosya ekledi" in x["govde"] for x in patrona(depo))
    # okuma açık, dosya fotoğraf: formun bilgileriyle, bayiye söylenir
    s2 = ayar(tmp_path, okuma={**BASIT, "tur": "fotograf"}, gorsel=True)
    assert depo.mesaj_kaydet(mesaj("yeni talep", talep("yeni_talep", "yeni", oda_programi="2+1"), bayi=BAYI_KART))
    isle_hepsi(depo, s2)
    satir, dis = form_satiri(depo, wa)
    form_cevabi(depo, tmp_path, parametreler(satir)["flow_token"], PLAN, dis, dosya="image/jpeg")
    [r] = isle_hepsi(depo, s2)
    assert r["eylem"] == "is_emri", r
    assert any(x["govde"].startswith("Formdaki dosyadan plan çıkaramadım") for x in bayiye(depo))


def test_f2_tanimayan_form_llmsiz(depo, wa, tmp_path):
    s = ayar(tmp_path)
    satir, dis = soru_al(depo, wa, s)
    form_cevabi(depo, tmp_path, "tf:baska", PLAN, dis)                       # cevaplanan mesajın formu değil
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "form: bilinmiyor" and bayiye(depo)[0]["govde"].startswith("Bu formu tanıyamadım")
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 0


# ─── F3 · revizyon formu ───
def test_f3_revize_et_revizyon_formu_aciklama_okunur(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    no, dis_onay = plan_al(depo, wa, tmp_path, s)
    assert depo.mesaj_kaydet(buton(f"r:{no}:1", dis_onay))
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "plan reddedildi" and son_sonuc(depo)["form_sunuldu"] == "revizyon"
    satir, dis = form_satiri(depo, wa)
    p = parametreler(satir)
    assert satir["body"].startswith("Anladım. Neyi değiştirelim?") and p["flow_id"] == "2222222222" and p["flow_cta"] == "Revizyon formu"
    assert p["flow_token"] == f"rv:{no}:1" and p["flow_action_payload"] == {"screen": "REVIZYON", "data": {
        "plan": f"{no} r01 planı için değişikliğinizi yazın; isterseniz dosya da ekleyin."}}
    # açıklama bayinin yazısı gibi okunur (kayıtlı LLM çıkarımı): r02
    t_rev = talep("revizyon", "aynalı olsun", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı olsun"}])
    form_cevabi(depo, tmp_path, p["flow_token"], {"neyi": ["oda"], "aciklama": "aynalı olsun"}, dis, cikarim=t_rev)
    [r2] = isle_hepsi(depo, s)
    assert r2["eylem"] == "is_emri", r2
    j = tek(depo, "SELECT cikarim FROM isler ORDER BY id DESC LIMIT 1")["cikarim"]
    assert "form" not in j and j["talep"]["niyet"] == "revizyon"
    assert tek(depo, "SELECT metin FROM mesajlar ORDER BY alindi DESC LIMIT 1")["metin"] == "aynalı olsun (değişecek: oda yerleşimi)"
    assert [x["rev"] for x in sorgu(depo, "SELECT rev FROM revizyonlar ORDER BY rev")] == [1, 2]
    # r01'in formu artık eski: LLM'siz, plan değişmez
    form_cevabi(depo, tmp_path, p["flow_token"], {"aciklama": "kapı solda olsun"}, dis, cikarim=t_rev)
    [r3] = isle_hepsi(depo, s)
    assert r3["gerekce"] == "form: eski" and bayiye(depo)[0]["govde"].startswith(f"Bu form {no} r01 planına ait; güncel plan ")
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 2


def test_f3_bos_ve_yalniz_dosyali_revizyon_formu(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path)
    no, dis_onay = plan_al(depo, wa, tmp_path, s)
    assert depo.mesaj_kaydet(buton(f"r:{no}:1", dis_onay))
    isle_hepsi(depo, s)
    satir, dis = form_satiri(depo, wa)
    token = parametreler(satir)["flow_token"]
    form_cevabi(depo, tmp_path, token, {"neyi": ["pencere"]}, dis)
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "form: bos" and bayiye(depo)[0]["govde"].startswith("Neyi nasıl değiştirelim?")
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "revizyon" and d["son_soru_alani"] == "revizyon_ne"
    form_cevabi(depo, tmp_path, token, {}, dis, dosya="application/pdf")
    [r] = isle_hepsi(depo, s)
    assert r["gerekce"] == "form: dosya" and bayiye(depo)[0]["govde"].startswith("Dosyanızı Lokman Bey'e ilettim.")
    assert any("revizyon formuna dosya ekledi" in x["govde"] for x in patrona(depo))
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 1
    # açıklama ve dosya: açıklama okunur (r02), dosya Patron'a
    t_rev = talep("revizyon", "aynalı olsun", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı olsun"}])
    form_cevabi(depo, tmp_path, token, {"aciklama": "aynalı olsun"}, dis, cikarim=t_rev, dosya="image/png")
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri" and any("revizyon formuna dosya ekledi" in x["govde"] for x in patrona(depo))


# ─── webhook ve panel ───
def test_webhook_form_cevabi_ve_dosyasi_kayda_girer(app, depo):  # noqa: F811
    depo.bayi_yaz("900000000909", ad="Patron", rol="patron")
    rj = json.dumps({"flow_token": "tf:abc", **PLAN, "dosya": [{"file_name": "plan.pdf", "mime_type": "application/pdf", "sha256": "x=", "id": "777"}]})
    m = {"id": "wamid.FORM1", "from": "900000000909", "timestamp": str(int(__import__("time").time())), "type": "interactive",
         "context": {"id": "wamid.SORU1"}, "interactive": {"type": "nfm_reply", "nfm_reply": {"name": "flow", "body": "Sent", "response_json": rj}}}
    kod, govde = post(app, yuk([m]))
    assert kod == 200 and json.loads(govde)["mesaj"] == {"sahiplenildi": 1}
    r = tek(depo, "SELECT metin, ham FROM mesajlar")
    assert r["metin"].startswith("Talep formu: prefabrik, tek kat, 2+1, 7,73 × 10,14 m") and r["ham"]["form"]["tur"] == "talep"
    assert [(x["medya_id"], x["mime"]) for x in sorgu(depo, "SELECT medya_id, mime FROM gelen_dosyalar")] == [("777", "application/pdf")]


def test_panel_kart_varsayilanlari(depo):
    import panel as PN
    depo.bayi_yaz(NUMARA_A, ad="Deneme Bayi A")
    assert depo.bayi_varsayilanlari(NUMARA_A) == {} and "varsayilanlar" not in depo.gelen_bayisi(NUMARA_A)
    assert depo.bayi_varsayilanlari_yaz(NUMARA_A, yapi_turu="celik", kat_sayisi="1", cati=None, veranda="arka") == \
        {"yapi_turu": "celik", "kat_sayisi": 1, "veranda": "arka"}
    assert depo.gelen_bayisi(NUMARA_A)["varsayilanlar"] == {"yapi_turu": "celik", "kat_sayisi": 1, "veranda": "arka"}
    html = PN.varsayilan_alanlari(depo.bayi_varsayilanlari(NUMARA_A))
    assert '<option value="celik" selected>' in html and '<option value="arka" selected>' in html and 'name="v_cati"' in html
    try:
        depo.bayi_varsayilanlari_yaz(NUMARA_A, veranda="cati")
        raise AssertionError("geçersiz değer yazıldı")
    except ValueError:
        pass
    assert depo.bayi_varsayilanlari_yaz(NUMARA_A) == {} and "varsayilanlar" not in depo.gelen_bayisi(NUMARA_A)


def test_ayar_kapandiktan_sonra_gelen_form_cevabi_yine_llmsiz(depo, wa, tmp_path, hizli_motor):
    """Form ayarı yalnız sunuşu açar; önceden gönderilmiş formun cevabı ayar kapandıktan sonra gelirse de LLM'siz işlenir."""
    s = ayar(tmp_path, acik=False)
    form_cevabi(depo, tmp_path, "tf:oncekiform", PLAN, None)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri" and tek(depo, "SELECT cikarim FROM isler")["cikarim"]["form"]["durum"] == "talep"
