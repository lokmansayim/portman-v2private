"""İE-23 PR-2a · banka modelinde oda büyütme / küçültme (ayar `banka_germe.acik`; LLM-önce okuma açıkken). Kalıcı akış, gerçek Postgres,
elle yazılmış LLM cevabı (manuel arka uç), sahte genel motor. LLM çağrısı yok.

Ç8801K r01 üstünde:
- "mutfağı sağa 20 cm büyütelim" → r02; işlem zarfta (`oda_buyut`, Mutfak, D, 20), mesajda kodun hesapladığı fark (Mutfak ve komşu
  Yatak Odası 1 m²'leri) ve "plan taslaktır" notu;
- "salonu sağa 50 cm büyütelim" → hakem geçirmez (mutfak 9,5 m²'nin altına iner): gerekçeli soru, plan aynen (rev 1), sonra onaylanabilir;
- yön yok → yön sorulur, plan aynen;
- ölçü yok → 50 cm alınır ve bayiye yazılır (hakem geçirirse) ya da gerekçe;
- ayar kapalıyken oda işlemi şemada yok: bugünkü davranış (okuma hata → kural okuması), oda isteği "otomatik uygulayamadım".

Koşum: PORTMAN_TEST_PG="host=127.0.0.1 port=55432 user=postgres" python -m pytest testler/kalici/test_banka_germe.py -q
"""
from __future__ import annotations

import json
import time

from conftest import AYAR, NUMARA_A, mesaj, sorgu, talep
from test_celik_akisi import BAYI_KART, hizli_genel, isle_hepsi, kabul, son_rev  # noqa: F401 (fikstür)


def _islem(**k):
    return {"tur": k.pop("tur"), "aciklik": None, "adaylar": [], "en": None, "yuk": None, "cati_kodu": None, "alinti": "",
            "mahal": None, "yon": None, "cm": None, **k}


def _ayar(tmp_path, cevap: dict, germe: bool = True) -> dict:
    yol = tmp_path / "degisiklik.json"
    yol.write_text(json.dumps(cevap, ensure_ascii=False), encoding="utf-8")
    return {**AYAR, "mesaj_katmani": True, "llm_once_revizyon": {"acik": True, "backend": "manuel", "hazir_dosya": str(yol)},
            "banka_germe": {"acik": germe}}


def _r01(depo):
    from test_celik_akisi import r01
    kabul(depo)
    ilk = r01(depo, "Ç8801K")
    time.sleep(1.1)                                           # İş Emri numarası saniyeye bağlı (bugünkü kural)
    return ilk


def _son_govde(depo) -> str:
    return sorgu(depo, "SELECT govde FROM giden WHERE alici <> 'PATRON' ORDER BY olusturuldu DESC, sira")[0]["govde"]


def test_mutfak_saga_20_r02_fark_ve_taslak_notu(depo, wa, hizli_genel, tmp_path):
    ilk = _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=20, alinti="mutfağı sağa 20 cm büyütelim")]})
    assert depo.mesaj_kaydet(mesaj("mutfağı sağa 20 cm büyütelim", talep("revizyon", ozet="mutfak büyüsün"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri" and "oda_buyut" in r["gerekce"], r
    rev = son_rev(depo)
    y = rev["is_emri"]["yapi"]
    assert rev["rev"] == 2 and rev["proje_id"] == ilk["proje_id"]
    assert [(d["op"], d["mahal"], d["yon"], d["cm"]) for d in y["degisiklikler"]] == [("oda_buyut", "Mutfak", "D", 20)]
    assert y["uygulanan"] == ["Mutfak sağa 20 cm büyütüldü"]
    govde = _son_govde(depo)
    assert "Mutfak 10,05 → 10,82 m²; Yatak Odası 1 12,74 → 11,97 m²; Hol ile Yatak Odası 1 arasındaki kapı 20 cm sağa kaydı" in govde, govde
    assert "plan taslaktır; mühendis kontrolünde kesinleşir" in govde
    c = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]
    assert c["degisiklik"]["durum"] == "tamam" and c["degisiklik"]["germe"] is True


def test_ayni_mesajda_iki_oda_istegi_ikisi_de_uygulanir(depo, wa, hizli_genel, tmp_path):
    """Geometri hakemi 31.10 (bulgu 2): tekilleştirme anahtarı oda ve yönü de içerir; ikinci oda isteği sessiz düşmez (K21)."""
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=20, alinti="mutfağı sağa 20"),
                                         _islem(tur="oda_buyut", mahal="Banyo", yon="K", cm=50, alinti="banyoyu arkaya 50")]})
    assert depo.mesaj_kaydet(mesaj("mutfağı sağa 20, banyoyu arkaya 50 cm büyütelim", talep("revizyon", ozet="mutfak ve banyo"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri", r
    y = son_rev(depo)["is_emri"]["yapi"]
    assert [(d["mahal"], d["yon"], d["cm"]) for d in y["degisiklikler"]] == [("Mutfak", "D", 20), ("Banyo", "K", 50)]
    assert y["uygulanan"] == ["Mutfak sağa 20 cm büyütüldü", "Banyo arkaya 50 cm büyütüldü"]
    govde = _son_govde(depo)
    assert "Mutfak 10,05 → 10,82 m²" in govde and "Banyo 4,68 → 5,91 m²; Yatak Odası 1 11,97 → 10,69 m²" in govde, govde


def test_cizim_tanimi_ayni_germe(depo, wa, hizli_genel, tmp_path):
    """Çizime giden tanım (zarftaki değişiklikler sırayla, `worker._cizim_tanimi`) kararın uyguladığıyla aynı (iki kod, bir kaynak: D-28)."""
    import worker as W
    from beyin import tanim_germe as TG
    from beyin.yapi_kimligi import tanim_sha_icerik
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=20, alinti="mutfağı sağa 20")]})
    assert depo.mesaj_kaydet(mesaj("mutfağı sağa 20", talep("revizyon", ozet="mutfak"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri", r
    y = son_rev(depo)["is_emri"]["yapi"]
    t = W._cizim_tanimi(y["tanim"], y["degisiklikler"])
    t0 = W._cizim_tanimi(y["tanim"], [])
    beklenen, _ = TG.oda_degistir(t0, "Mutfak", "D", 20)
    assert tanim_sha_icerik(t) == tanim_sha_icerik(beklenen)


def test_salonu_saga_50_hakem_gecirmez_plan_aynen(depo, wa, hizli_genel, tmp_path):
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Yaşam Alanı", yon="D", cm=50, alinti="salonu sağa 50 cm büyütelim")]})
    assert depo.mesaj_kaydet(mesaj("salonu sağa 50 cm büyütelim", talep("revizyon", ozet="salon büyüsün"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "sor" and r["gerekce"] == "banka germe: hakem geçirmedi, plan aynen", r
    govde = _son_govde(depo)
    assert "Yaşam Alanı sağa 50 cm büyütme isteğinizi otomatik uygulayamadım: Mutfak 8,12 m²'ye iner (mutfak için en az 9,5 m²)" in govde, govde
    assert "Planınız aynen geçerli" in govde
    assert son_rev(depo)["rev"] == 1                                                    # plan değişmedi; hak düşmez
    d, _ = depo.konusma_oku(NUMARA_A)
    assert d["asama"] == "onay_bekliyor"                                                # plan bayide: Onayla çalışır
    # karar katmanı (kalıcı akışın onay denetimi PDF'in teslim bildirimini ister; bu test onu kurmaz; test_plan_akisi C2 ile aynı)
    import kalici
    import worker as W
    from beyin.karar import karar_ver
    from beyin.sema import Talep
    k = kalici.BellekKonusma(NUMARA_A, d)
    kr = karar_ver(Talep.model_validate(talep("onay", ozet="onay")), k, BAYI_KART, W.katalog_nesnesi(ayar, kabul_edilmis=depo.kabul_edilmis_adaylar()),
                   metin="onaylıyorum")
    assert kr.gerekce == "plan onaylandı" and k.d["asama"] == "onaylandi" and k.d["son_soru_alani"] is None


def test_yon_yoksa_sorulur_sonra_tam_istek_r02(depo, wa, hizli_genel, tmp_path):
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", cm=20, alinti="mutfağı 20 cm büyütelim")]})
    assert depo.mesaj_kaydet(mesaj("mutfağı 20 cm büyütelim", talep("revizyon", ozet="mutfak"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "sor" and r["gerekce"] == "banka germe: yön yok", r
    assert "\"mutfağı 20 cm büyütelim\" için yönü yazar mısınız: öne, arkaya, sola ya da sağa?" in _son_govde(depo)
    assert son_rev(depo)["rev"] == 1
    time.sleep(1.1)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=20, alinti="mutfağı sağa 20")]})
    assert depo.mesaj_kaydet(mesaj("mutfağı sağa 20", talep("revizyon", ozet="mutfak"), bayi=BAYI_KART))
    [r2] = isle_hepsi(depo, ayar)
    assert r2["eylem"] == "is_emri" and son_rev(depo)["rev"] == 2, r2


def test_olcu_yoksa_50_cm_ve_bayiye_yazilir(depo, wa, hizli_genel, tmp_path):
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Banyo", yon="K", alinti="banyoyu arkaya büyütelim")]})
    assert depo.mesaj_kaydet(mesaj("banyoyu arkaya büyütelim", talep("revizyon", ozet="banyo"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "is_emri", r
    y = son_rev(depo)["is_emri"]["yapi"]
    assert [(d["op"], d["mahal"], d["yon"], d["cm"], d.get("cm_varsayilan")) for d in y["degisiklikler"]] == [("oda_buyut", "Banyo", "K", 50, True)]
    assert "(ölçü yazılmadığı için 50 cm aldım)" in _son_govde(depo)


def test_ayar_kapaliyken_oda_istegi_bugunku_gibi(depo, wa, hizli_genel, tmp_path):
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="uygulanamaz", alinti="mutfağı sağa 20 cm büyütelim")]}, germe=False)
    assert depo.mesaj_kaydet(mesaj("mutfağı sağa 20 cm büyütelim", talep("revizyon", ozet="mutfak büyüsün"), bayi=BAYI_KART))
    [r] = isle_hepsi(depo, ayar)
    assert r["eylem"] == "yonlendir" and son_rev(depo)["rev"] == 1, r
    govde = _son_govde(depo)
    assert "isteğini otomatik uygulayamadım" in govde and "oda büyütme" not in govde
    c = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]
    assert "germe" not in c["degisiklik"]


def test_ayar_kapaliyken_oda_islemi_semada_yok(depo, wa, hizli_genel, tmp_path):
    """Kapalıyken LLM `oda_buyut` yazsa bile şema geçirmez (okuma hata → bugünkü kural okuması); plan değişmez."""
    _r01(depo)
    ayar = _ayar(tmp_path, {"islemler": [_islem(tur="oda_buyut", mahal="Mutfak", yon="D", cm=20, alinti="mutfağı sağa 20")]}, germe=False)
    assert depo.mesaj_kaydet(mesaj("mutfağı sağa 20 cm büyütelim", talep("revizyon", ozet="mutfak büyüsün"), bayi=BAYI_KART))
    isle_hepsi(depo, ayar)
    c = sorgu(depo, "SELECT cikarim FROM isler ORDER BY id DESC")[0]["cikarim"]
    assert c["degisiklik"]["durum"] == "hata" and son_rev(depo)["rev"] == 1
