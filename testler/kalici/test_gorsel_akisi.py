"""İE-20 PR-1 · görsel ve PDF ile talep, kalıcı akış (gerçek Postgres, kayıtlı okuma: manuel arka uç, LLM yok; sahte WhatsApp).

G1: plan resmi → okunanın özeti + okunan yerleşimin görseli, [Doğru] [Düzelt] (`c:<iz>:d|z`); tutmayan ölçü "emin olamadım" (soru,
düğmesiz). G2: PDF aynı yoldan. G3: [Düzelt] → "Neyi düzelteyim?" → düzeltme yazısı → yeniden teyit ("Düzelttim: …"); eski düğme
geçersiz. G4: [Doğru] → İş Emri r01 (`talep.kaynak` cizim-okuma); TK-01 BK-14'süz çizilemez (bayiye ve Patron'a), BK-14'le teklif r04'ün
geometrisi; okumadan çizilen planın revizyonu aynı projede r02 ("Uygulanan: …"). G5: çelik okuma İE-14 yolundan r01. G6: fotoğraf → ölçü
ve oda sayısı sorulur. G7: ayar kapalıyken bugünkü cevap. Dosya inmediyse "alamadım" + Patron; yeniden alınan iş okumayı yeniden yaptırmaz.

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_gorsel_akisi.py -q
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from conftest import AYAR, BAYI_A, NUMARA_A, mesaj, sorgu, talep

import kalici
import worker as W
from beyin import gorsel_okuma as GO

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "gorsel" / "veri"
BAYI_KART = {**BAYI_A, "numara": NUMARA_A}


def okuma(ad: str) -> dict:
    return {a: v for a, v in json.loads((VERI / ad).read_text(encoding="utf-8")).items() if not a.startswith("_")}


def kalip(o: dict) -> dict:
    """Okumanın kalıptan geçmiş biçimi (konuşmada böyle durur)."""
    return GO.CizimOkumasi.model_validate(o).model_dump(mode="json")


BASIT = okuma("BASIT_2p1_okuma.json")
TK01 = okuma("TK01_okuma.json")
CELIK = okuma("CELIK_2p1_okuma.json")


def ayar(tmp_path: Path, oku: dict | None = None, duzeltme: dict | None = None, acik: bool = True) -> dict:
    """Kayıtlı okuma (`okuma`) ve düzeltme (`duzeltme`) tek dosyada; dosya her çağrıda yeniden yazılabilir (sıradaki cevap)."""
    h = tmp_path / "hazir_gorsel.json"
    h.write_text(json.dumps({"okuma": oku, "duzeltme": duzeltme}, ensure_ascii=False), encoding="utf-8")
    return {**AYAR, "mesaj_katmani": True,
            "gorsel_okuma": {"acik": acik, "backend": "manuel", "hazir_dosya": str(h), "bekle_sn": 0}}


def isle_hepsi(depo, s: dict) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, s, "test-isleyici")) is not None:
        out.append(r)
    return out


def cizim_gonder(depo, tmp_path: Path, tur: str = "image", mime: str = "image/jpeg", indir: bool = True, metin: str = "") -> dict:
    """Bayi çizim gönderir: mesaj + gelen dosya kaydı; `indir` ise gönderici indirmiş gibi dosya yazılır."""
    g = mesaj(metin, None, bayi=BAYI_KART, tur=tur)
    g["media_id"] = "MEDYA" + g["id"][-6:]
    assert depo.mesaj_kaydet(g)
    depo.gelen_dosya_ekle(g["id"], g["media_id"], "plan.pdf" if mime == "application/pdf" else "plan.jpg", mime)
    if indir:
        yol = tmp_path / "gelen_medya" / g["media_id"] / ("plan.pdf" if mime == "application/pdf" else "plan.jpg")
        yol.parent.mkdir(parents=True, exist_ok=True)
        icerik = b"%PDF-1.4 sahte cizim" if mime == "application/pdf" else b"\xff\xd8\xff sahte cizim"
        yol.write_bytes(icerik)
        dosya = depo.mesajin_dosyasi(g["id"])
        depo.gelen_dosya_indirildi(dosya["id"], str(yol), mime, len(icerik), hashlib.sha256(icerik).hexdigest())
    return g


def buton(reply_id: str, context_id: str | None = None) -> dict:
    g = mesaj(reply_id.split(":")[-1], talep("diger", "kısa cevap"), bayi=BAYI_KART, context_id=context_id, tur="interactive")
    g["reply_id"] = reply_id; g["reply_kind"] = "button_reply"
    return g


def yaz(depo, metin: str, t: dict) -> None:
    assert depo.mesaj_kaydet(mesaj(metin, t, bayi=BAYI_KART))


def son_satirlar(depo) -> list[dict]:
    return sorgu(depo, "SELECT alici, kind, govde, satir FROM giden WHERE mesaj_id = (SELECT mesaj_id FROM isler ORDER BY id DESC LIMIT 1) ORDER BY sira")


def bayiye(depo) -> list[dict]:
    return [s for s in son_satirlar(depo) if s["alici"] == NUMARA_A]


def patrona(depo) -> list[dict]:
    return [s for s in son_satirlar(depo) if s["alici"] == "PATRON"]


def dugmeler(satir: dict) -> list[str]:
    return [b["reply"]["id"] for b in satir["satir"]["interactive"]["action"]["buttons"]]


def teyit_al(depo, wa, tmp_path, s, **k) -> tuple[dict, str]:
    """Çizim gönderilir, teyit mesajı gelir; dönen: (teyit satırı, giden dış kimliği)."""
    cizim_gonder(depo, tmp_path, **k)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "çizim okundu: teyit", r
    [satir] = [x for x in bayiye(depo) if x["kind"] == "interactive"]
    kalici.gonder(depo, wa)
    dis = sorgu(depo, "SELECT dis_id FROM giden WHERE kind = 'interactive' ORDER BY olusturuldu DESC, sira DESC")[0]["dis_id"]
    return satir, dis


# ─── G1 · G2 ───
def test_g1_resim_okunur_teyit_gorselli_dugmeli(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    satir, _ = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    co = d["cizim_okuma"]
    assert co["durum"] == "teyit" and dugmeler(satir) == [f"c:{co['iz']}:d", f"c:{co['iz']}:z"]
    assert satir["govde"].startswith("Çiziminizden şunları okudum:") and "Tek katlı prefabrik, gövde 7,73 × 8,88 m" in satir["govde"]
    assert "Okuduğum yerleşim görselde. Doğru mu?" in satir["govde"] and len(satir["govde"]) <= 1024
    g = Path(satir["satir"]["file"])
    assert g.is_file() and g.name == "okunan_yerlesim.png" and satir["satir"]["sha256"] == hashlib.sha256(g.read_bytes()).hexdigest()
    assert sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 0                # teyitsiz plan yok
    j = sorgu(depo, "SELECT cikarim, sonuc FROM isler ORDER BY id DESC")[0]
    assert j["cikarim"]["gorsel"]["durum"] == "tamam" and j["cikarim"]["gorsel"]["cagri"] == 0       # okuma iş satırında (yeniden deneme okutmaz)
    assert j["sonuc"]["cizim_okuma"]["iz"] == co["iz"] and NUMARA_A not in json.dumps(j["sonuc"])


def test_g2_pdf_ayni_yoldan(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    satir, _ = teyit_al(depo, wa, tmp_path, s, tur="document", mime="application/pdf")
    assert "Çiziminizden şunları okudum" in satir["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["dosya"]["mime"] == "application/pdf"


def test_desteklenmeyen_dosya_turu(depo, tmp_path):
    s = ayar(tmp_path, BASIT)
    cizim_gonder(depo, tmp_path, tur="document", mime="application/zip")
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "cevapla" and "türü okunmuyor" in r["gerekce"]
    assert "Bu dosya türünü okuyamıyorum" in bayiye(depo)[0]["govde"] and "Lokman Bey'e ilettim" in bayiye(depo)[0]["govde"]
    assert any("okunamayan bir dosya" in p["govde"] and "application/zip" in p["govde"] for p in patrona(depo))


def test_dosya_inmediyse_alamadim_ve_patron(depo, tmp_path):
    s = ayar(tmp_path, BASIT)
    cizim_gonder(depo, tmp_path, indir=False)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "cevapla" and "indirilemedi" in r["gerekce"]
    assert "Gönderdiğiniz dosyayı alamadım" in bayiye(depo)[0]["govde"]
    p = patrona(depo)
    assert p and "indirilemedi" in p[0]["govde"] and NUMARA_A not in p[0]["govde"]


def test_g7_ayar_kapali_bugunku_cevap(depo, tmp_path):
    for s in (ayar(tmp_path, BASIT, acik=False), {**AYAR, "mesaj_katmani": True}):
        cizim_gonder(depo, tmp_path)
        [r] = isle_hepsi(depo, s)
        assert "Şu an yalnız yazılı talepleri işleyebiliyorum" in bayiye(depo)[0]["govde"]
        j = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]
        assert j["cikarim"] is None                                    # okuma yapılmadı


def test_g6_fotograf_olcu_ve_oda_sayisi_sorulur(depo, tmp_path):
    s = ayar(tmp_path, {"tur": "fotograf", "ozet": "tek katlı bir evin dış fotoğrafı"})
    cizim_gonder(depo, tmp_path)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "cevapla" and "plan değil" in r["gerekce"]
    m = bayiye(depo)[0]["govde"]
    assert "Dış ölçüyü" in m and "oda sayısını" in m


def test_okuma_hatasi_bayiye_ve_patrona(depo, tmp_path):
    s = ayar(tmp_path, {"tur": "plan", "odalar": "bozuk"})
    cizim_gonder(depo, tmp_path)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "hata"
    assert bayiye(depo)[0]["govde"].startswith("Çiziminizi şu an okuyamadım")
    assert any("çizimi okunamadı" in p["govde"] for p in patrona(depo))


# ─── G4 ───
def test_g4_dogru_dugmesi_is_emri_r01(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    iz = d["cizim_okuma"]["iz"]
    assert depo.mesaj_kaydet(buton(f"c:{iz}:d", context_id=dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri" and r["gerekce"] == f"şablon {GO.KAYNAK}", r
    rev = sorgu(depo, "SELECT is_emri_no, rev, is_emri, durum FROM revizyonlar")[0]
    ie = rev["is_emri"]
    assert rev["rev"] == 1 and rev["durum"] == "onay_bekliyor" and ie["talep"]["kaynak"] == "cizim-okuma"
    beklenen = GO.denetle(BASIT)["cevrim"]["is_emri"]
    assert ie["mahaller"] == beklenen["mahaller"] and ie["acikliklar"] == beklenen["acikliklar"] and ie["yapi"]["referans_model"] == "CIZIM"
    m = [x for x in bayiye(depo) if x["kind"] == "interactive"][0]
    assert "Çiziminizdeki plan (7,73 × 8,88 m, 2+1)." in m["govde"]
    assert sorted(dugmeler(m)) == sorted([f"o:{rev['is_emri_no']}:1", f"r:{rev['is_emri_no']}:1"])
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor" and d["cizim_okuma"]["durum"] == "cizildi"
    # aynı düğmeye yeniden basmak: okuma artık açık değil, ikinci plan çizilmez
    assert depo.mesaj_kaydet(buton(f"c:{iz}:d"))
    [r2] = isle_hepsi(depo, s)
    assert r2["eylem"] == "cevapla" and sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 1
    assert "artık açık değil" in bayiye(depo)[0]["govde"]


def test_g4_yaziyla_dogru(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    teyit_al(depo, wa, tmp_path, s)
    yaz(depo, "doğru, çizebilirsiniz", talep("onay", "okuma doğru"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri"


def test_g4_tk01_bk14_yokken_cizilemez_bayiye_ve_patrona(depo, tmp_path, monkeypatch):
    monkeypatch.setattr(GO, "bk14_var", lambda: False)
    s = ayar(tmp_path, TK01)
    cizim_gonder(depo, tmp_path)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "yonlendir" and "otomatik çizilemez" in r["gerekce"] and "veranda" in r["gerekce"]
    [g] = bayiye(depo)
    assert g["kind"] == "image" and Path(g["satir"]["file"]).is_file()           # okunan yerleşim + altyazı
    assert "Bu planı şu an otomatik çizemiyorum" in g["govde"] and "Lokman Bey'e iletiyorum" in g["govde"] and len(g["govde"]) <= 1024
    assert any(p["govde"].startswith("Portman yönlendirme:") for p in patrona(depo))
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["durum"] == "devredildi" and d["asama"] == "yonlendirildi"


def test_g4_tk01_bk14_ile_teklif_r04_geometrisi(depo, wa, tmp_path, monkeypatch, hizli_motor):
    """Hedef örnek: TK-01 okunur, teyit edilir; İş Emri teklif çalışmasının r04'üyle (bayiye giden r03 paftası) geometri olarak aynı."""
    monkeypatch.setattr(GO, "bk14_var", lambda: True)
    s = ayar(tmp_path, TK01)
    satir, dis = teyit_al(depo, wa, tmp_path, s)
    assert "Veranda: önde 3,86 × 1,81 m, arkada 2,61 × 1,30 m." in satir["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:d", context_id=dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri"
    ie = sorgu(depo, "SELECT is_emri FROM revizyonlar")[0]["is_emri"]
    beklenen = okuma("TK01_beklenen.json")
    for a in ("mahaller", "acikliklar", "verandalar", "cati"):
        assert ie[a] == beklenen[a], a
    assert ie["yapi"] == {**beklenen["yapi"], "referans_model": "CIZIM"}


# ─── G3 ───
def test_g3_duzelt_dugmesi_sonra_yazi_yeniden_teyit_eski_dugme_gecersiz(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    eski = d["cizim_okuma"]["iz"]
    assert depo.mesaj_kaydet(buton(f"c:{eski}:z", context_id=dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and "Neyi düzelteyim?" in bayiye(depo)[0]["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["durum"] == "duzeltme"
    yeni = json.loads(json.dumps(BASIT))
    next(x for x in yeni["odalar"] if x["ad"] == "SALON")["alan_m2"] = 20
    s = ayar(tmp_path, BASIT, {"niyet": "duzeltme", "okuma": yeni, "degisenler": ["salon 20 m²"]})
    yaz(depo, "salon 20 m² olacak", talep("diger", "salon 20 m²"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "çizim okundu: teyit"
    [m] = [x for x in bayiye(depo) if x["kind"] == "interactive"]
    assert m["govde"].startswith("Düzelttim: salon 20 m²; Salon 19 → 20 m².") and "salon 20 m²" in m["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["iz"] != eski and d["cizim_okuma"]["okuma"] == kalip(yeni)
    j = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]
    assert j["gorsel_duzeltme"]["niyet"] == "duzeltme"                 # düzeltme okuması da iş satırında
    kalici.gonder(depo, wa)
    assert depo.mesaj_kaydet(buton(f"c:{eski}:d"))                     # eski okumanın düğmesi
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "cevapla" and "daha önceki bir okumasına ait" in bayiye(depo)[0]["govde"]
    assert sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 0


def test_g3_tutmayan_olcu_soru_sonra_cevap_teyit(depo, tmp_path, hizli_motor):
    bozuk = json.loads(json.dumps(BASIT))
    next(z for z in bozuk["zincirler"] if z["kenar"] == "ust")["olculer_cm"] = [387, 126, 280]
    s = ayar(tmp_path, bozuk)
    cizim_gonder(depo, tmp_path)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and "soru" in r["gerekce"]
    [g] = bayiye(depo)
    assert g["kind"] == "image" and "Şunlardan emin olamadım" in g["govde"] and "Üstteki ölçü zinciri 387 + 126 + 280 = 793 cm" in g["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["durum"] == "soru" and d["cizim_okuma"]["sorular"]
    s = ayar(tmp_path, bozuk, {"niyet": "duzeltme", "okuma": BASIT, "degisenler": ["sağdaki oda 260 cm"]})
    yaz(depo, "sağdaki 260 olacak, toplam 773", talep("diger", "ölçü cevabı"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and r["gerekce"] == "çizim okundu: teyit"


def test_g3_iptal_ve_degisiklik_cikmazsa_sorar(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    teyit_al(depo, wa, tmp_path, s)
    s = ayar(tmp_path, BASIT, {"niyet": "duzeltme", "okuma": BASIT, "degisenler": []})
    yaz(depo, "hmm bakalım", talep("diger", "belirsiz"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and "değişiklik yok" in r["gerekce"]
    s = ayar(tmp_path, BASIT, {"niyet": "iptal"})
    yaz(depo, "vazgeçtim", talep("diger", "vazgeçti"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "cevapla" and "çizimden okumayı bıraktım" in bayiye(depo)[0]["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "cizim_okuma" not in d


# ─── okumadan çizilen planın revizyonu ───
def test_cizilmis_planin_revizyonu_ayni_proje_r02(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:d", context_id=dis))
    isle_hepsi(depo, s)
    ilk = sorgu(depo, "SELECT id, proje_id, is_emri_no FROM revizyonlar")[0]
    yeni = json.loads(json.dumps(BASIT))
    next(p for p in yeni["pencereler"] if p["oda"] == "MUTFAK")["olcu"] = "120x180"
    s = ayar(tmp_path, BASIT, {"niyet": "duzeltme", "okuma": yeni, "degisenler": ["mutfak penceresi 120x180"]})
    time.sleep(1.1)                                                      # İş Emri numarası saniyeye bağlı (bugünkü kural)
    yaz(depo, "mutfak penceresi 120x180 olsun", talep("revizyon", "mutfak penceresi 120x180"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    rev = sorgu(depo, "SELECT proje_id, rev, is_emri FROM revizyonlar ORDER BY id DESC")[0]
    assert rev["rev"] == 2 and rev["proje_id"] == ilk["proje_id"] and rev["is_emri"]["talep"]["kaynak"] == "cizim-okuma"
    assert {"tur": "pencere", "olcu": "120x180", "mahal": "MUTFAK", "duvar": "sag"} in rev["is_emri"]["acikliklar"]
    assert sorgu(depo, "SELECT durum FROM revizyonlar WHERE id = %s", ilk["id"])[0]["durum"] == "yerini_aldi"
    m = [x for x in bayiye(depo) if x["kind"] == "interactive"][0]
    assert m["govde"].startswith("Uygulanan: mutfak penceresi 120x180; pencereler değişti.")
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["durum"] == "cizildi" and d["cizim_okuma"]["okuma"] == kalip(yeni) and d["revizyon"] == 1


def test_baska_katalog_talebi_okumayi_kapatir(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    teyit_al(depo, wa, tmp_path, s)
    yaz(depo, "P6001 olsun", talep(ozet="P6001 istiyor", katalog_kodu="P6001"))
    [r] = isle_hepsi(depo, s)
    assert r.get("eylem") != "sor" or "çizim" not in (r.get("gerekce") or "")
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "cizim_okuma" not in d


# ─── G5 · çelik ───
def test_g5_celik_okuma_r01_ie14_yolu(depo, wa, tmp_path, monkeypatch):
    from test_celik_akisi import sahte_genel
    from motor.genel import uret
    monkeypatch.setattr(uret, "uret", sahte_genel)
    s = ayar(tmp_path, CELIK)
    satir, dis = teyit_al(depo, wa, tmp_path, s)
    assert "Tek katlı çelik, gövde 11,00 × 8,50 m" in satir["govde"]
    d, _ = depo.konusma_oku(NUMARA_A)
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:d", context_id=dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    ie = sorgu(depo, "SELECT is_emri FROM revizyonlar")[0]["is_emri"]
    assert ie["yapi"]["sistem"] == "celik" and ie["yapi"]["motor"] == "genel"


# ─── yeniden alınan iş okumayı yeniden yaptırmaz ───
def test_yeniden_alinan_is_okumayi_yeniden_yaptirmaz(depo, tmp_path, monkeypatch, hizli_motor):
    s = ayar(tmp_path, BASIT)
    cagri = []
    asil = GO.oku
    monkeypatch.setattr(GO, "oku", lambda *a, **k: (cagri.append(1), asil(*a, **k))[1])

    class Cokus(BaseException):
        pass

    def coker(*a, **k):
        raise Cokus()
    asil_isle = W.isle
    monkeypatch.setattr(W, "isle", coker)
    cizim_gonder(depo, tmp_path)
    with pytest.raises(Cokus):
        kalici.bir_is(depo, s, "test-isleyici")                          # okuma yapıldı ve kaydedildi, sonra süreç çöktü
    assert len(cagri) == 1
    with depo.baglan() as c, c.transaction():
        c.execute("UPDATE isler SET kira_bitis = now() - interval '1 second'")
    monkeypatch.setattr(W, "isle", asil_isle)
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "sor" and len(cagri) == 1


def test_medya_bekle_inene_kadar_bekler(depo, tmp_path):
    g = cizim_gonder(depo, tmp_path, indir=False)
    dosya = depo.mesajin_dosyasi(g["id"])
    yol = tmp_path / "gec.jpg"
    uyunan = []

    def uyu(sn):
        uyunan.append(sn)
        if len(uyunan) == 2:                                             # gönderici ikinci turda indirdi
            yol.write_bytes(b"\xff\xd8\xff")
            depo.gelen_dosya_indirildi(dosya["id"], str(yol), "image/jpeg", 3, hashlib.sha256(b"\xff\xd8\xff").hexdigest())
    d = kalici.medya_bekle(depo, g, {"gorsel_okuma": {"bekle_sn": 30}}, uyu=uyu)
    assert d and d["yol"] == str(yol) and len(uyunan) == 2
    for _ in range(3):
        depo.gelen_dosya_hatasi(dosya["id"], "deneme")
    g2 = cizim_gonder(depo, tmp_path, indir=False)
    for _ in range(3):
        depo.gelen_dosya_hatasi(depo.mesajin_dosyasi(g2["id"])["id"], "deneme")
    assert kalici.medya_bekle(depo, g2, {"gorsel_okuma": {"bekle_sn": 30}}, uyu=lambda sn: None) is None   # üç denemede inmedi
    uyunan.clear()
    assert kalici.medya_bekle(depo, {"id": "wamid.YOK"}, {}, uyu=uyunan.append) is None                    # kayıt hiç gelmedi
    assert len(uyunan) == kalici.DOSYA_KAYDI_SN


def test_medya_bekle_dosya_kaydi_mesajdan_sonra_gelir(depo, tmp_path):
    """Webhook mesajı ve dosya kaydını ayrı yazar; ajan araya girerse dosya kaydı beklenir (inceleme bulgusu, 27 Ekim)."""
    g = mesaj("", None, bayi=BAYI_KART, tur="image")
    g["media_id"] = "MEDYA" + g["id"][-6:]
    assert depo.mesaj_kaydet(g)
    yol = tmp_path / "sonra.jpg"

    def uyu(sn):
        if depo.mesajin_dosyasi(g["id"]) is None:                        # webhook dosya kaydını şimdi yazdı, gönderici indirdi
            depo.gelen_dosya_ekle(g["id"], g["media_id"], "plan.jpg", "image/jpeg")
            yol.write_bytes(b"\xff\xd8\xff")
            depo.gelen_dosya_indirildi(depo.mesajin_dosyasi(g["id"])["id"], str(yol), "image/jpeg", 3,
                                       hashlib.sha256(b"\xff\xd8\xff").hexdigest())
    d = kalici.medya_bekle(depo, g, {"gorsel_okuma": {"bekle_sn": 30}}, uyu=uyu)
    assert d and d["yol"] == str(yol)


def test_ilgisiz_yazi_okumayi_kapatir_soru_kapatmaz(depo, wa, tmp_path, hizli_motor):
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    yaz(depo, "fiyatı ne kadar olur?", talep("soru", "fiyat sordu"))
    [r] = isle_hepsi(depo, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["cizim_okuma"]["durum"] == "teyit"                          # soru okumayı kapatmaz: düğme hâlâ çalışır
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:d", context_id=dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri"
    s2 = ayar(tmp_path, BASIT, {"niyet": "baska_talep"})
    cizim_gonder(depo, tmp_path)                                         # ikinci çizim: yeni okuma
    [r] = isle_hepsi(depo, s2)
    assert r["gerekce"] == "çizim okundu: teyit"
    yaz(depo, "7x4 m 2+1 ön verandalı bir ev daha lazım", talep(ozet="7x4 2+1 ön verandalı"))
    [r] = isle_hepsi(depo, s2)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "cizim_okuma" not in d and r["gerekce"] != "çizim okundu: teyit"
    j = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]
    assert j["gorsel_duzeltme"]["niyet"] == "baska_talep"


def test_duzeltten_sonra_dogru_yazisi_plan(depo, wa, tmp_path, hizli_motor):
    """[Düzelt]'e basıp vazgeçen bayi "doğru" yazarsa okuma yeniden denetlenir ve plan çizilir (sorusu olan okumada çizilmez)."""
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:z", context_id=dis))
    isle_hepsi(depo, s)
    yaz(depo, "yok yok doğru, onaylıyorum", talep("onay", "okuma doğru"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri"


def test_revizyonda_yeni_varsayim_bayiye_yazilir(depo, wa, tmp_path, hizli_motor):
    """Okumadan çizilmiş planın revizyonu teyitsiz yeniden çizilir; değişiklikle gelen yeni varsayım (ölçüsüz pencere) mesajda yazar."""
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:d", context_id=dis))
    isle_hepsi(depo, s)
    yeni = json.loads(json.dumps(BASIT))
    yeni["pencereler"].append({"oda": "MUTFAK", "kenar": "alt", "olcu": None})
    s = ayar(tmp_path, BASIT, {"niyet": "duzeltme", "okuma": yeni, "degisenler": ["mutfağa öne pencere"]})
    time.sleep(1.1)
    yaz(depo, "mutfağa öne bir pencere ekleyin", talep("revizyon", "mutfağa pencere"))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri", r
    m = [x for x in bayiye(depo) if x["kind"] == "interactive"][0]["govde"]
    assert m.startswith("Uygulanan: mutfağa öne pencere; pencereler değişti. Varsaydığım: ölçüsü yazmayan pencereler: 120x120 (Mutfak).")


def test_duzelt_dugmesinden_sonra_dogru_dugmesi_plan(depo, wa, tmp_path, hizli_motor):
    """[Düzelt]'e yanlışlıkla basan bayi aynı mesajın [Doğru]'suyla planı alır; yazıyla "doğru" demekle aynı (inceleme, 27 Ekim)."""
    s = ayar(tmp_path, BASIT)
    _, dis = teyit_al(depo, wa, tmp_path, s)
    d, _ = depo.konusma_oku(NUMARA_A)
    iz = d["cizim_okuma"]["iz"]
    for _ in range(2):                                                   # iki kez [Düzelt]: ikisi de "Neyi düzelteyim?"
        assert depo.mesaj_kaydet(buton(f"c:{iz}:z", context_id=dis))
        [r] = isle_hepsi(depo, s)
        assert r["eylem"] == "sor" and "Neyi düzelteyim?" in bayiye(depo)[0]["govde"]
    assert depo.mesaj_kaydet(buton(f"c:{iz}:d", context_id=dis))
    [r] = isle_hepsi(depo, s)
    assert r["eylem"] == "is_emri" and sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 1


def test_ayar_kapaninca_acik_okuma_llm_siz_kapanir(depo, wa, tmp_path, hizli_motor, monkeypatch):
    """Ayar kapanınca açık okumaya gelen yazı LLM'le düzeltilmez (ücretli çağrı yok), bugünkü yoldan işlenir; okumanın düğmesi plan
    çizmez, bayiye çizimden talebin kapalı olduğu yazılır (G7; inceleme, 27 Ekim)."""
    monkeypatch.setattr(W, "gorsel_duzelt", lambda *a, **k: pytest.fail("ayar kapalıyken düzeltme çağrısı"))
    kapali = ayar(tmp_path, BASIT, acik=False)
    _, dis = teyit_al(depo, wa, tmp_path, ayar(tmp_path, BASIT))
    d, _ = depo.konusma_oku(NUMARA_A)
    assert depo.mesaj_kaydet(buton(f"c:{d['cizim_okuma']['iz']}:d", context_id=dis))
    [r] = isle_hepsi(depo, kapali)
    assert r["eylem"] == "cevapla" and r["gerekce"] == "çizim okuması kapalı"
    assert bayiye(depo)[0]["govde"].startswith("Çizimden talep şu an kapalı.")
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "cizim_okuma" not in d and sorgu(depo, "SELECT count(*) AS n FROM revizyonlar")[0]["n"] == 0
    kalici.gonder(depo, wa)
    teyit_al(depo, wa, tmp_path, ayar(tmp_path, BASIT))                  # yeni okuma açık; ayar kapanır, bayi yazar
    yaz(depo, "salon 20 m² olsun", talep("diger", "salon 20 m²"))
    [r] = isle_hepsi(depo, kapali)
    assert r.get("eylem") != "hata" and "Düzelttim" not in " ".join(x["govde"] or "" for x in bayiye(depo))
    d, _ = depo.konusma_oku(NUMARA_A)
    assert "cizim_okuma" not in d
    j = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"] or {}
    assert "gorsel_duzeltme" not in j
