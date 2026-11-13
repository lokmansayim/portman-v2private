"""BK-29 tur 4 (pano 201, 202, 210) · kalıcı akışta tur 2 ve tur 3 canlı bulguları (konuşma her mesajda kayıttan okunur, canlı gibi).

B5: LLM "pencere 120x180 olsun" isteğini hem odasız satır hem varyant olarak yazar; yazılı oda cevabı r02'yi getirir, not bir kez yazılır.
Tur 3 gözlem 2: "Hangisini?" sorusuna "hiçbiri" yeni revizyon üretmez (LLM pencere isteğini serbest istek olarak da yazmıştı).
Tur 3 gözlem 3 (pano 202): yalnız model kodu yazılan mesajın planında metin ve PDF başlığı kodun özeti, LLM'in "anlayamadık" özeti değil.
Gerçek Postgres, kayıtlı LLM çıkarımı (canlıda görülen biçimde), sahte WhatsApp, hızlı Motor.
"""
from __future__ import annotations

from conftest import AYAR, mesaj, sorgu, talep, tek

import kalici

KATMAN = {**AYAR, "mesaj_katmani": True}


def isle_hepsi(depo, ayar=KATMAN) -> list[dict]:
    out = []
    while (r := kalici.bir_is(depo, ayar, "test-isleyici")) is not None:
        out.append(r)
    return out


def bayiye(depo, mesaj_id: str) -> list[dict]:
    return [x for x in sorgu(depo, "SELECT alici, kind, satir, dis_id FROM giden WHERE mesaj_id = %s ORDER BY sira", mesaj_id)
            if x["alici"] != "PATRON"]


def _govde(r: dict) -> str:
    s = r["satir"]
    return (s.get("interactive") or {}).get("body", {}).get("text") or s.get("body") or s.get("text") or ""


def test_yazili_oda_cevabi_ikiz_istekte_kalici(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001", talep(ozet="P6001", katalog_kodu="P6001")))
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "is_emri"
    kalici.gonder(depo, wa)
    t = talep("revizyon", "Pencerenin 120x180 olmasını istiyorsunuz.",
              pencereler=[{"mahal": None, "olcu": "120x180", "islem": "degistir"}],
              varyantlar=[{"tur": "pencere_degistir", "aciklama": "pencere 120x180 olsun", "parametreler": {"yeni": "120x180"}}])
    depo.mesaj_kaydet(mesaj("pencere 120x180 olsun", t))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "sor", r2
    kalici.gonder(depo, wa)
    depo.mesaj_kaydet(mesaj("Yatak odası 1", talep("revizyon", "Yatak odası 1 penceresi", pencereler=[{"mahal": "yatak odası 1", "islem": "degistir"}])))
    [r3] = isle_hepsi(depo)
    assert r3["eylem"] == "is_emri", r3
    kalici.gonder(depo, wa)
    assert [x["rev"] for x in sorgu(depo, "SELECT rev FROM revizyonlar ORDER BY rev")] == [1, 2]
    ie = tek(depo, "SELECT is_emri FROM revizyonlar WHERE rev = 2")["is_emri"]
    assert [a["olcu"] for a in ie["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == "YATAK ODASI 1"] == ["120x180"]
    metinler = " ".join(_govde(x) for x in bayiye(depo, r3["mesaj_id"]))
    assert metinler.count("YATAK ODASI 1 penceresi 120x180") == 1, metinler


def test_hicbiri_yeni_revizyon_uretmez_kalici(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001", talep(ozet="P6001", katalog_kodu="P6001")))
    isle_hepsi(depo); kalici.gonder(depo, wa)
    t = talep("revizyon", "Yaşam alanı penceresinin 120x120 olmasını istiyorsunuz.",
              pencereler=[{"mahal": "yaşam alanı", "olcu": "120x120", "islem": "degistir"}],
              ozel_istekler=["Yaşam alanı penceresi 120x120 olsun"], bina_ozellikleri={"Yaşam alanı penceresi": "120x120"})
    depo.mesaj_kaydet(mesaj("yaşam alanı penceresi 120x120 olsun", t))
    [r2] = isle_hepsi(depo)
    assert r2["eylem"] == "sor", r2
    kalici.gonder(depo, wa)
    depo.mesaj_kaydet(mesaj("hiçbiri", talep("red", "Pencere seçimi için sunulan seçeneklerin hiçbirini istemiyorsunuz.")))
    [r3] = isle_hepsi(depo)
    assert r3["eylem"] == "cevapla", r3
    kalici.gonder(depo, wa)
    assert [x["rev"] for x in sorgu(depo, "SELECT rev FROM revizyonlar ORDER BY rev")] == [1]
    metin = " ".join(_govde(x) for x in bayiye(depo, r3["mesaj_id"]))
    assert metin.startswith("Tamam, o pencereyi değiştirmedim. Planınız (") and "değişmedi" in metin
    assert "istemiyorsunuz" not in metin and "120x120 olmasını" not in metin


def test_yalniz_kod_plan_metni_ve_pdf_basligi_koddan(depo, wa, hizli_motor):
    depo.mesaj_kaydet(mesaj("P6001", talep("diger", '"P6001" yazdınız, ne istediğinizi anlayamadık. Bir katalog kodu mu? Açıklar mısınız?',
                                           belirsizlikler=["kod mu referans mı"])))
    [r1] = isle_hepsi(depo)
    assert r1["eylem"] == "is_emri", r1
    kalici.gonder(depo, wa)
    satirlar = bayiye(depo, r1["mesaj_id"])
    metin = " ".join(_govde(x) for x in satirlar)
    belge = [x for x in satirlar if x["kind"] == "document"]
    assert belge and "anlayamadık" not in metin
    baslik = belge[0]["satir"]["body"]                                         # PDF açıklaması (`worker.giden_belge`)
    assert "anlayamadık" not in baslik and baslik.endswith("ÖN ONAYA SUNULAN TASLAK · P6001 seçildi")   # tur 5: aynı biçim, baslik
