"""İE-08 8b · mühendis teknik kontrolü M1–M3 (kalıcı akış, gerçek Postgres, sahte genel motor, sahte WhatsApp ve sahte Graph API).

M1: bayi çelik planı onaylar → kontrol kaydı + mühendis kartına şablon (alıcı MUHENDIS, gönderimde karttan çözülür); kart yoksa Patron'a
söylenir; prefabrik onayı bugünkü yol (A5/M6). Mühendis "Gönder" → görsel, TASLAK pafta PDF'i, Excel (sunucuda, D-17), DXF (.dxf adıyla
düz metin) ve [Patron'a gönder] [Düzeltme iste]; kısa parça kontrol notları metinde. M2: mühendisin Excel'i liste sürümü olur ve Patron'a
o gider; Patron'a metin + şablon; düzeltme notu Patron'a, bayiye "kontrol sürüyor" (bayinin onay mesajına bağlı, revizyon hakkı aynı).
M3: hatırlatmalar (08:00–20:00 İstanbul, saat başı; 3 saatte Patron'a bir kez; Patron'a 2 saatte bir en çok 3; Fiyat verildi durdurur).

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_muhendis.py -q
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import time
from pathlib import Path

import pytest

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep, tek

import gonderici as G
import kalici
import meta_api as M
import muhendis as MH
import sablonlar as S
import worker as W
from sahte_meta import SahteMeta
from test_celik_akisi import KATMAN, UC, buton, kabul, sahte_genel

KOK = Path(__file__).resolve().parents[2]
LISTE_JSON = KOK / "deneme" / "2026-10-06_kor_test" / "sonuc" / "KT01_duzeltilmis_yukleme.json"
NUMARA_M = "900000000303"          # gerçek olmayan deneme numaraları
NUMARA_P = "900000000909"
BAYI_KART = {**BAYI_A, "numara": NUMARA_A}
PNID = "106000000000001"
AYAR_AC = {**KATMAN, "enabled": True, "dry_run": False, "sablon_muhendis_kontrol": "portman_muhendis_kontrol_v1",
           "sablon_muhendis_hatirlatma": "portman_hatirlatma_v1", "sablon_patron_bildirim": "portman_patron_bekliyor_v1"}
ISTANBUL = MH.ISTANBUL


def saat(gun: int, s: int, dk: int = 0) -> float:
    return dt.datetime(2026, 10, gun, s, dk, tzinfo=ISTANBUL).timestamp()


def sahte_genel_liste(tanim_yolu: Path, hedef: Path, **k) -> dict:
    """sahte_genel + gerçek bir yükleme listesi JSON'u (Excel'e dönüşsün), ASCII DXF ve kısa parça notlu pafta özeti."""
    m = sahte_genel(tanim_yolu, hedef, **k)
    hedef = Path(hedef); kod = Path(m["pdf"]).name.replace("_pafta.pdf", "")
    shutil.copyfile(LISTE_JSON, hedef / m["yukleme_json"])
    (hedef / f"{kod}_cizim.dxf").write_text("  0\nSECTION\n  2\nHEADER\n  0\nENDSEC\n  0\nEOF\n", encoding="ascii")
    (hedef / f"{kod}_pafta_ozet.json").write_text(json.dumps({"kontrol_notlari": [{"zincir": "arka", "konum_cm": 1094, "parca_cm": 8, "not": "x"}]}),
                                                 encoding="utf-8")
    m["duzenlenebilir_dxf"] = f"{kod}_cizim.dxf"
    for a in ("bayi_gorsel", "plan_bayi"):                                          # gönderici türü ilk baytlardan okur: gerçek PNG imzası
        (hedef / m[a]).write_bytes(b"\x89PNG\r\n\x1a\n" + (hedef / m[a]).read_bytes())
    return m


@pytest.fixture
def genel_liste(monkeypatch):
    from motor.genel import uret
    monkeypatch.setattr(uret, "uret", sahte_genel_liste)


def isle_hepsi(depo, ayar=KATMAN) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def muhendis_karti(depo):
    depo.bayi_yaz(NUMARA_M, ad="Deneme Mühendis", rol="muhendis")


def celik_onay(depo, wa) -> dict:
    """Çelik r01 → gönderim → bayinin Onayla düğmesi. Dönen: onaylanan revizyon satırı."""
    kabul(depo, UC)
    assert depo.mesaj_kaydet(mesaj("Ç8801K olsun", talep(ozet="Ç8801K", katalog_kodu="Ç8801K"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo); assert r["eylem"] == "is_emri", r
    kalici.gonder(depo, wa)
    rev = tek(depo, "SELECT * FROM revizyonlar ORDER BY id DESC LIMIT 1")
    time.sleep(1.1)
    o = buton(f"o:{rev['is_emri_no']}:1")
    assert depo.mesaj_kaydet(o)
    [r2] = isle_hepsi(depo)
    assert r2["gerekce"] == "plan onaylandı", r2
    return {**tek(depo, "SELECT * FROM revizyonlar WHERE id = %s", rev["id"]), "onay_mesaj_id": o["id"]}


def muhendis_mesaji(metin: str = "", reply_id: str | None = None, tur: str = "text", **ek) -> dict:
    g = mesaj(metin, talep("diger", "x"), numara=NUMARA_M, bayi={"kod": "B0303", "ad": "Deneme Mühendis", "rol": "muhendis", "numara": NUMARA_M},
              tur="interactive" if reply_id else tur)
    g["role"] = "muhendis"; g.pop("test_cikarim", None)
    if reply_id:
        g["reply_id"] = reply_id; g["reply_kind"] = "button_reply"
    g.update(ek)
    return g


def muhendis_isle(depo, g: dict) -> dict:
    assert depo.mesaj_kaydet(g)
    [r] = isle_hepsi(depo)
    return r


def satirlar(depo, mesaj_id: str) -> list[dict]:
    return [x["satir"] | {"_alici": x["alici"], "_sira": x["sira"], "_kaynak": x["kaynak"]}
            for x in sorgu(depo, "SELECT satir, alici, sira, kaynak FROM giden WHERE mesaj_id = %s ORDER BY sira", mesaj_id)]


# ───────────────────────── M1 ─────────────────────────
def test_celik_onayi_muhendise_bildirim_ve_kontrol_kaydi(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa)
    assert rev["durum"] == "onaylandi"
    no = rev["is_emri_no"]
    ss = satirlar(depo, rev["onay_mesaj_id"])
    assert ss[0]["body"] == f"Onayınız kaydedildi ({no}, revizyon 1). Plan teknik kontrole gönderildi; sonucu size bildireceğiz."
    [sab] = [s for s in ss if s["kind"] == "template"]
    assert sab["_alici"] == "MUHENDIS" and sab["sablon_anahtari"] == "sablon_muhendis_kontrol" and sab["pencere_kapaliysa"] is False
    assert sab["sablon"]["govde"] == [no, "r01"] and sab["sablon"]["dugmeler"] == [{"sub_type": "quick_reply", "index": 0, "payload": f"muh:gonder:{no}:1"}]
    assert sab["body"] == S.sablon_metni(S.MUHENDIS_KONTROL["metin"], [no, "r01"])
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "bekliyor" and k["muhendis"] == NUMARA_M and k["bayi"] == NUMARA_A and k["onay_mesaj_id"] == rev["onay_mesaj_id"]
    assert k["bayi_kod"] == BAYI_A["kod"] and k["patron_durum"] == "yok" and k["listeler"] == []
    # D-17: Excel sunucuda (worker.liste_exceli), bayiye gitmez; bayi satırlarında xlsx/dxf yok
    ex = rev["ekler"]["excel"]
    assert Path(ex["dosya"]).name == f"Portman_{no}_r01_yukleme_listesi.xlsx" and ex["bayiye_gider"] is False
    assert M.belge_turu(Path(ex["dosya"]), Path(ex["dosya"]).read_bytes()) == M.XLSX
    bayiye = sorgu(depo, "SELECT dosya FROM giden WHERE alici = %s AND dosya IS NOT NULL", NUMARA_A)
    assert bayiye and not [b for b in bayiye if b["dosya"].endswith((".xlsx", ".dxf"))]


def test_muhendis_karti_yoksa_patrona_soylenir(depo, wa, genel_liste):
    rev = celik_onay(depo, wa)
    ss = satirlar(depo, rev["onay_mesaj_id"])
    assert not [s for s in ss if s["_alici"] == "MUHENDIS"]
    p, sab = [s for s in ss if s["_alici"] == "PATRON"]
    assert "aktif mühendis kartı yok" in p["body"] and NUMARA_A not in p["body"]
    assert sab["kind"] == "template" and sab["pencere_kapaliysa"] is True and sab["sablon"]["govde"] == [BAYI_A["kod"], rev["is_emri_no"]]   # inceleme: pencere kapalıysa da
    assert depo.muhendis_kontrolu(rev["is_emri_no"], 1)["durum"] == "kart_yok"


def test_prefabrik_onayi_muhendise_gitmez(depo, wa, hizli_motor):
    muhendis_karti(depo)
    T_P = talep(ozet="P6001", katalog_kodu="P6001")
    assert depo.mesaj_kaydet(mesaj("P6001", T_P)); isle_hepsi(depo, AYAR); kalici.gonder(depo, wa)
    time.sleep(1.1)
    o = mesaj("onaylıyorum", talep("onay", "onay"))
    assert depo.mesaj_kaydet(o); [r] = isle_hepsi(depo, AYAR)
    assert r["gerekce"] == "plan onaylandı"
    assert tek(depo, "SELECT count(*) n FROM muhendis_kontrolleri")["n"] == 0
    assert satirlar(depo, o["id"])[0]["body"].endswith("Teklif aşamasına geçiliyor.")
    assert not sorgu(depo, "SELECT 1 FROM giden WHERE alici = 'MUHENDIS'")


def test_muhendis_gonder_dosyalar_ve_dugmeler_llmsiz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    g = muhendis_mesaji(reply_id=f"muh:gonder:{no}:1")
    r = muhendis_isle(depo, g)
    assert r["gerekce"] == "dosyalar gönderildi", r
    ss = satirlar(depo, g["id"])
    assert [s["kind"] for s in ss] == ["image", "document", "document", "document", "interactive"]
    assert all(s["_alici"] == NUMARA_M for s in ss)
    pdf, xlsx, dxf = ss[1], ss[2], ss[3]
    assert pdf["filename"] == f"Portman_{no}_r01.pdf" and pdf["mime"] == "application/pdf" and "TASLAK" in pdf["body"]
    assert xlsx["filename"].endswith("_yukleme_listesi.xlsx") and xlsx["mime"] == M.XLSX == MH.S_XLSX
    assert dxf["filename"] == f"Portman_{no}_r01.dxf" and dxf["mime"] == M.DXF_MIME == MH.S_DXF
    son = ss[4]
    assert "arka 8 cm (@1094)" in son["body"]                                            # D-10 kontrol notu mühendise
    ids = [b["reply"]["id"] for b in son["interactive"]["action"]["buttons"]]
    assert ids == [f"muh:patron:{no}:1", f"muh:duzeltme:{no}:1"]
    assert [b["reply"]["title"] for b in son["interactive"]["action"]["buttons"]] == ["Patron'a gönder", "Düzeltme iste"]
    j = tek(depo, "SELECT cikarim FROM isler WHERE mesaj_id = %s", g["id"])
    assert j["cikarim"] is None                                                          # LLM yok
    assert depo.muhendis_kontrolu(no, 1)["t_dosya"] is not None
    # revizyon kayıtları değişmedi (mühendisin belgeleri revizyona bağlanmaz: onay denetimi etkilenmez)
    assert tek(depo, "SELECT count(*) n FROM giden WHERE mesaj_id = %s AND revizyon_id IS NOT NULL", g["id"])["n"] == 0


def test_baska_numara_ya_da_eski_dugme_isi_bulamaz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    r = muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:gonder:{no}:2"))
    assert r["gerekce"] == "kontrol bulunamadı"
    r = muhendis_isle(depo, muhendis_mesaji(reply_id="muh:sil:x:1"))                        # tanınmayan işlem → yardım
    assert r["gerekce"] == "yardım"


# ───────────────────────── M2 ─────────────────────────
def _excel_gonder(depo, no: str, indir: bool = True) -> dict:
    g = muhendis_mesaji(tur="document", filename="liste_duzeltilmis.xlsx", media_id="555")
    assert depo.mesaj_kaydet(g)
    depo.gelen_dosya_ekle(g["id"], "555", "liste_duzeltilmis.xlsx", M.XLSX)          # webhook gibi (kanal/webhook.py)
    if indir:
        kaynak = Path(depo.revizyon_kaydi(no, 1)["ekler"]["excel"]["dosya"])
        yol = W.KANAL / "gelen_medya" / "x" / "liste_duzeltilmis.xlsx"; yol.parent.mkdir(parents=True, exist_ok=True)
        veri = kaynak.read_bytes(); yol.write_bytes(veri)
        [d] = depo.bekleyen_gelen_dosyalar()
        depo.gelen_dosya_indirildi(d["id"], str(yol), M.XLSX, len(veri), hashlib.sha256(veri).hexdigest())
    [r] = isle_hepsi(depo)
    return {**r, "mesaj_id": g["id"]}


def test_muhendis_exceli_liste_surumu_ve_patrona_gonder(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:gonder:{no}:1"))
    r = _excel_gonder(depo, no)
    assert r["gerekce"] == "liste sürümü"
    k = depo.muhendis_kontrolu(no, 1)
    assert [(x["surum"], x["kaynak"]) for x in k["listeler"]] == [(2, "muhendis")]
    g = muhendis_mesaji(reply_id=f"muh:patron:{no}:1")
    r = muhendis_isle(depo, g)
    assert r["gerekce"] == "mühendis onayladı: Patron'a gönderildi"
    ss = satirlar(depo, g["id"])
    patron = [s for s in ss if s["_alici"] == "PATRON"]
    assert [s["kind"] for s in patron] == ["text", "template", "document"]
    assert "mühendis onayladı; fiyat sizde" in patron[0]["body"] and "sürüm 2" in patron[0]["body"] and NUMARA_A not in patron[0]["body"]
    assert patron[1]["sablon_anahtari"] == "sablon_patron_bildirim" and patron[1]["sablon"]["govde"] == [BAYI_A["kod"], no]
    assert patron[1]["sablon"]["dugmeler"][0]["text"] == f"konusma/{NUMARA_A}"
    assert "/muhendis/" in patron[2]["file"] and patron[2]["file"].endswith("_s2.xlsx") and patron[2]["mime"] == M.XLSX
    assert ss[-1]["_alici"] == NUMARA_M and "Patron'a iletildi" in ss[-1]["body"]
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "patrona_gonderildi" and k["patron_durum"] == "bekliyor" and k["t_karar"] is not None
    # karar verildikten sonra düğme yeniden karar yazmaz
    assert muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:duzeltme:{no}:1"))["gerekce"] == "karar zaten verildi"


def test_excel_indirilmediyse_sunucunun_listesi_gider(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    _excel_gonder(depo, no, indir=False)
    g = muhendis_mesaji(reply_id=f"muh:patron:{no}:1")
    muhendis_isle(depo, g)
    patron = [s for s in satirlar(depo, g["id"]) if s["_alici"] == "PATRON"]
    assert "henüz indirilmedi" in patron[0]["body"] and patron[2]["file"].endswith(f"Portman_{no}_r01_yukleme_listesi.xlsx")


def test_excel_olmayan_dosya_surum_olmaz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    g = muhendis_mesaji(tur="document", filename="not.pdf", media_id="556")
    r = muhendis_isle(depo, g)
    assert r["gerekce"] == "dosya: Excel değil" and depo.muhendis_kontrolu(no, 1)["listeler"] == []


def test_duzeltme_iste_not_patrona_bayiye_kontrol_suruyor_hak_dusmez(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    d_once, _ = depo.konusma_oku(NUMARA_A)
    g = muhendis_mesaji(reply_id=f"muh:duzeltme:{no}:1")
    assert muhendis_isle(depo, g)["gerekce"] == "mühendis düzeltme istedi"
    # bayiye "kontrol sürüyor": bayinin onay mesajına bağlı, sıra 201'den, kaynak sistem
    [b] = [s for s in satirlar(depo, rev["onay_mesaj_id"]) if s["_alici"] == NUMARA_A and s["_sira"] >= 201]
    assert b["body"] == MH.BAYI_KONTROL_SURUYOR and b["_kaynak"] == "sistem"
    k = depo.muhendis_kontrolu(no, 1)
    assert k["durum"] == "duzeltme" and k["bekleyen"] == MH.DUZELTME_NOTU
    g2 = muhendis_mesaji("Arka duvar 8 cm parça olmaz, 0532 123 45 67 numaralı ustayla konuştum")
    assert muhendis_isle(depo, g2)["gerekce"] == "düzeltme notu Patron'a"
    patron = [s for s in satirlar(depo, g2["id"]) if s["_alici"] == "PATRON"]
    assert [s["kind"] for s in patron] == ["text", "template"]
    assert "Arka duvar 8 cm parça olmaz" in patron[0]["body"] and "0532 123 45 67" not in patron[0]["body"]          # numara maskeli
    k = depo.muhendis_kontrolu(no, 1)
    assert k["bekleyen"] is None and "Arka duvar" in k["not_"] and "0532 123 45 67" not in k["not_"]
    d_sonra, _ = depo.konusma_oku(NUMARA_A)
    assert d_sonra == d_once                                                                # bayinin konuşması (revizyon hakkı) değişmedi
    # not beklenmiyorken serbest metin: yardım
    assert muhendis_isle(depo, muhendis_mesaji("merhaba"))["gerekce"] == "yardım"
    # düzeltmeden sonra da Patron'a gönderilebilir
    assert muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))["gerekce"] == "mühendis onayladı: Patron'a gönderildi"


# ───────────────────────── M3 ─────────────────────────
def test_mesai_ve_sure_baslangici():
    assert MH.mesaide_mi(saat(14, 8)) and MH.mesaide_mi(saat(14, 19, 59)) and not MH.mesaide_mi(saat(14, 20)) and not MH.mesaide_mi(saat(14, 7, 59))
    assert MH.sure_baslangici(saat(14, 10, 30)) == saat(14, 10, 30)
    assert MH.sure_baslangici(saat(14, 21)) == saat(15, 8)                               # gece onayı: ertesi gün 08:00
    assert MH.sure_baslangici(saat(15, 3)) == saat(15, 8)                                # sabaha karşı: aynı gün 08:00


def _kontrol_saati(depo, no: str, t: float, **alan) -> None:
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE muhendis_kontrolleri SET sure_baslangici = to_timestamp(%s) WHERE is_emri_no = %s", (t, no))
        for a, v in alan.items():
            c.execute(f"UPDATE muhendis_kontrolleri SET {a} = to_timestamp(%s) WHERE is_emri_no = %s", (v, no))


def _cipa(depo, rev) -> list[dict]:
    return [s for s in satirlar(depo, rev["onay_mesaj_id"]) if s["_sira"] >= 201]


def test_muhendis_hatirlatmasi_saat_basi_mesaide_ve_uc_saatte_patron(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    _kontrol_saati(depo, no, saat(14, 9))
    assert MH.hatirlatma_turu(depo, saat(14, 9, 59))["muhendis"] == 0                   # 1 saat dolmadı
    assert MH.hatirlatma_turu(depo, saat(14, 10, 0))["muhendis"] == 1
    [h] = _cipa(depo, rev)
    assert h["_alici"] == "MUHENDIS" and h["sablon_anahtari"] == "sablon_muhendis_hatirlatma" and h["sablon"]["govde"] == [no, "1"] and h["_kaynak"] == "sistem"
    assert h["sablon"]["dugmeler"][0]["payload"] == f"muh:gonder:{no}:1"
    assert MH.hatirlatma_turu(depo, saat(14, 10, 30))["muhendis"] == 0                  # saat başı: yarım saatte yok
    with depo.baglan() as c, c.transaction():                                            # bir saat sonrası (son hatırlatma 10:00)
        c.execute("UPDATE muhendis_kontrolleri SET son_hatirlatma = to_timestamp(%s)", (saat(14, 10),))
    say = MH.hatirlatma_turu(depo, saat(14, 12, 0))
    assert say["muhendis"] == 1 and say["gecikme"] == 1                                   # 3 saat doldu: Patron'a bir kez
    patron = [s for s in _cipa(depo, rev) if s["_alici"] == "PATRON"]
    assert [s["kind"] for s in patron] == ["text", "template"] and "3 saattir cevap vermedi" in patron[0]["body"] and NUMARA_A not in patron[0]["body"]
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE muhendis_kontrolleri SET son_hatirlatma = to_timestamp(%s)", (saat(14, 12),))
    assert MH.hatirlatma_turu(depo, saat(14, 13, 1))["gecikme"] == 0                     # gecikme bir kez
    assert MH.hatirlatma_turu(depo, saat(14, 21)) == {"muhendis": 0, "gecikme": 0, "patron": 0, "zaman_asimi": 0, "hata": 0}     # mesai dışı (BK-10: sayaçta zaman aşımı da)


def test_gece_onayinda_hatirlatma_08den_sonra(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    _kontrol_saati(depo, no, MH.sure_baslangici(saat(14, 22)))                          # 22:00 onayı → 15 Ekim 08:00
    assert MH.hatirlatma_turu(depo, saat(15, 8, 30))["muhendis"] == 0
    assert MH.hatirlatma_turu(depo, saat(15, 9, 0))["muhendis"] == 1


def test_patron_hatirlatmasi_iki_saatte_bir_en_cok_uc_ve_fiyat_verildi(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))
    _kontrol_saati(depo, no, saat(14, 9), karar_zamani=saat(14, 9), patron_son_hatirlatma=saat(14, 9))
    assert MH.hatirlatma_turu(depo, saat(14, 10, 59))["patron"] == 0
    for t in (saat(14, 11), saat(14, 13), saat(14, 15)):
        assert MH.hatirlatma_turu(depo, t)["patron"] == 1
        with depo.baglan() as c, c.transaction():
            c.execute("UPDATE muhendis_kontrolleri SET patron_son_hatirlatma = to_timestamp(%s)", (t,))
    assert MH.hatirlatma_turu(depo, saat(14, 17, 30))["patron"] == 0                    # en çok 3
    p = [s for s in _cipa(depo, rev) if s["_alici"] == "PATRON"]
    assert [s["kind"] for s in p] == ["text", "template"] * 3 and "fiyat bekleniyor" in p[0]["body"]
    k = depo.muhendis_kontrolu(no, 1)
    assert k["patron_hatirlatma_sayisi"] == 3 and depo.fiyat_verildi(k["id"]) and depo.muhendis_kontrolu(no, 1)["patron_durum"] == "fiyat_verildi"
    assert not depo.fiyat_verildi(k["id"])


def test_panelden_bayiye_gonderim_patron_hatirlatmasini_durdurur(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:patron:{no}:1"))
    assert depo.patron_hatirlatma_durdur(NUMARA_A) == 1
    assert depo.muhendis_kontrolu(no, 1)["patron_durum"] == "durdu"


def test_ajan_dakikada_bir_hatirlatma_turu(depo, ajan, monkeypatch):
    cagri = []
    monkeypatch.setattr(MH, "hatirlatma_turu", lambda d, s=None: cagri.append(s) or {"muhendis": 0})
    ajan._zaman["hatirlatma"] = 0.0
    assert ajan.hatirlatma(depo, {"enabled": False}, 1000.0) is None and cagri == []      # kanal kapalı
    assert ajan.hatirlatma(depo, {"enabled": True}, 1000.0) == {"muhendis": 0}
    assert ajan.hatirlatma(depo, {"enabled": True}, 1030.0) is None                       # 60 sn dolmadı
    assert ajan.hatirlatma(depo, {"enabled": True}, 1061.0) is not None and len(cagri) == 2


# ───────────────────────── gönderici ─────────────────────────
@pytest.fixture
def meta():
    return SahteMeta()


def _gonderen(depo, meta):
    a = M.MetaAyar(phone_number_id=PNID, access_token="t" * 40, app_secret="s" * 20, verify_token="v")
    return G.GonderenMeta(depo, M.GraphIstemci(a, http=meta), W.KANAL, ayar_oku=lambda: AYAR_AC)


def test_gonderici_muhendis_alicisi_ve_excel_dxf_belgeleri(depo, wa, meta, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    g = _gonderen(depo, meta)
    G.tur(depo, g, g.istemci, W.KANAL, AYAR_AC)
    s = tek(depo, "SELECT durum, alici_cozuldu FROM giden WHERE alici = 'MUHENDIS'")
    assert s["durum"] == "kabul_edildi" and s["alici_cozuldu"] == NUMARA_M
    [y] = [y for y in meta.gidenler() if y["type"] == "template"]
    assert y["to"] == NUMARA_M and y["template"]["name"] == "portman_muhendis_kontrol_v1"
    assert y["template"]["components"][1] == {"type": "button", "sub_type": "quick_reply", "index": "0", "parameters": [{"type": "payload", "payload": f"muh:gonder:{no}:1"}]}
    muhendis_isle(depo, muhendis_mesaji(reply_id=f"muh:gonder:{no}:1"))
    G.tur(depo, g, g.istemci, W.KANAL, AYAR_AC)
    belgeler = [y["document"]["filename"] for y in meta.gidenler() if y["type"] == "document" and y["to"] == NUMARA_M]
    assert belgeler == [f"Portman_{no}_r01.pdf", f"Portman_{no}_r01_yukleme_listesi.xlsx", f"Portman_{no}_r01.dxf"]
    kalan = sorgu(depo, "SELECT kind, hata FROM giden WHERE durum <> 'kabul_edildi' AND alici = %s", NUMARA_M)
    assert not kalan, kalan


def test_gonderici_aktif_muhendis_karti_yoksa_gonderilmez(depo, wa, meta, genel_liste):
    muhendis_karti(depo)
    celik_onay(depo, wa)
    depo.bayi_yaz(NUMARA_M, ad="Deneme Mühendis", rol="muhendis", aktif=False)
    g = _gonderen(depo, meta)
    G.tur(depo, g, g.istemci, W.KANAL, AYAR_AC)
    s = tek(depo, "SELECT durum, hata FROM giden WHERE alici = 'MUHENDIS'")
    assert s["durum"] == "gonderilmedi" and "recipient_unknown" in s["hata"]


def test_belge_turu_tanima():
    assert M.belge_turu(Path("a.dxf"), b"  0\nSECTION\n") == M.DXF_MIME
    assert M.belge_turu(Path("a.dxf"), b"0\r\nSECTION\r\n") == M.DXF_MIME
    assert M.belge_turu(Path("a.txt"), b"  0\nSECTION\n") == ""                         # uzantı da gerekir
    assert M.belge_turu(Path("a.xlsx"), b"PK\x03\x04 rastgele") == ""                    # ZIP ama çalışma kitabı değil
    assert M.belge_turu(Path("a.dxf"), b"MZ\x90\x00") == ""


# ───────────────────────── kapanış incelemesi (14.10) ─────────────────────────
def test_kisa_parca_notlarinin_hepsi_gider_cok_ise_ayri_metinde(depo, wa, genel_liste):
    """Geometri hakemi (kritik): KT-03'te 17 not var; ilk 6'yla kesilmez (D-10). 6'dan çoksa hepsi ayrı metinde, düğmeli mesajda sayı."""
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    ozet = next(Path(rev["pdf_yolu"]).parent.glob("*_pafta_ozet.json"))
    notlar = [{"zincir": z, "konum_cm": 10 * i, "parca_cm": 3, "not": "x"} for i, z in enumerate(["arka"] * 3 + ["on"] * 5 + ["sol"] * 5 + ["sag"] * 4)]
    ozet.write_text(json.dumps({"kontrol_notlari": notlar}), encoding="utf-8")
    g = muhendis_mesaji(reply_id=f"muh:gonder:{no}:1"); muhendis_isle(depo, g)
    ss = satirlar(depo, g["id"])
    [liste] = [x for x in ss if x["kind"] == "text"]
    assert liste["body"].count(" cm (@") == 17 and "sag 3 cm (@160)" in liste["body"]
    assert "Kısa parça notu: 17 (ayrı mesajda)." in ss[-1]["body"]
    ozet.unlink()                                                                          # özet yoksa "okunamadı" (yok ile ayrılır)
    g2 = muhendis_mesaji(reply_id=f"muh:gonder:{no}:1"); muhendis_isle(depo, g2)
    assert "kısa parça notları (pafta özeti okunamadı)" in satirlar(depo, g2["id"])[-1]["body"]


def test_mesai_suresi_gece_saymaz():
    assert MH.mesai_suresi(saat(14, 18, 30), saat(15, 8)) == 1.5 * 3600
    assert MH.mesai_suresi(saat(14, 21), saat(15, 7)) == 0
    assert MH.mesai_suresi(saat(14, 9), saat(16, 9)) == 2 * 12 * 3600


def test_aksam_onayinda_gecikme_ertesi_sabah_mesai_saatiyle(depo, wa, genel_liste):
    """İnceleme: 18:30 onayı sabah 08:00'de "13 saattir" sayılmaz; 3 mesai saati 09:30'da dolar."""
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    _kontrol_saati(depo, no, saat(14, 18, 30))
    assert MH.hatirlatma_turu(depo, saat(14, 19, 30))["muhendis"] == 1
    say = MH.hatirlatma_turu(depo, saat(15, 8, 0))
    assert say == {"muhendis": 0, "gecikme": 0, "patron": 0, "zaman_asimi": 0, "hata": 0}                 # 1,5 mesai saati
    assert MH.hatirlatma_turu(depo, saat(15, 8, 30))["muhendis"] == 1
    h = [s for s in _cipa(depo, rev) if s["_alici"] == "MUHENDIS"][-1]
    assert h["sablon"]["govde"] == [no, "2"]
    assert MH.hatirlatma_turu(depo, saat(15, 9, 30))["gecikme"] == 1


def test_arada_fiyat_verildiyse_hatirlatma_yazilmaz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    k = depo.muhendis_kontrolu(no, 1)
    assert depo.kontrol_satir_ekle(k["id"], k["onay_mesaj_id"], [W.giden_metin({"id": k["onay_mesaj_id"], "sender": NUMARA_A}, "x", 0, "PATRON")],
                                   {"hatirlatma_sayisi": 9}, beklenen={"durum": "patrona_gonderildi", "patron_durum": "bekliyor"}) == []
    assert depo.muhendis_kontrolu(no, 1)["hatirlatma_sayisi"] == 0 and not _cipa(depo, rev)


def test_test_kartinin_kontrolu_hatirlatma_dogurmaz(depo, wa, genel_liste):
    muhendis_karti(depo)
    rev = celik_onay(depo, wa); no = rev["is_emri_no"]
    depo.bayi_yaz(NUMARA_A, ad="Kuru koşu", kod="TEST", rol="test")
    _kontrol_saati(depo, no, saat(14, 9))
    assert MH.hatirlatma_turu(depo, saat(14, 12)) == {"muhendis": 0, "gecikme": 0, "patron": 0, "zaman_asimi": 0, "hata": 0}


def test_xlsx_calisma_kitabi_zip_sonunda_da_taninir(tmp_path):
    import io
    import zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", "x" * 300000)
        z.writestr("xl/workbook.xml", "<workbook/>")
    assert M.belge_turu(Path("a.xlsx"), b.getvalue()) == M.XLSX
