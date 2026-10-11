"""İE-07 P2 (D-07): katalog kaydının yeni sürümü (kat, kaynak, dogrulama), kat süzgeci ve üç düzeltilmiş kayıt.

Postgres gerekmez. Dondurulmuş `katalog_37_proje.json` değişmez (referans girdi); kod `katalog_37_proje_v2.json` okur.
LLM'in "tek kat" sözünü kat_sayisi=1'e çevirmesi burada sınanmaz (kat hazır verilir); o kanıt canlı kapıda, ücretli denemeyle."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

from beyin import katalog as KAT
from beyin.katalog import Katalog
from beyin import karar as KR
from beyin.sema import Talep

CIFT = {"P1142", "P1202", "P1322", "P1422", "P1552", "Ç1142", "Ç1202", "Ç1302", "Ç1322", "Ç1352", "Ç1402", "Ç1552", "Ç2226"}
DONDURULMUS_SHA = "d3e8a755448acf28"   # testler/referans/2026-09-28b/referans_girdiler.json ile aynı dosya


def test_dondurulmus_dosya_degismedi_ve_kod_v2_okur():
    assert hashlib.sha256(KAT.KATALOG_DONDURULMUS_JSON.read_bytes()).hexdigest().startswith(DONDURULMUS_SHA)
    assert KAT.KATALOG_JSON.name == "katalog_37_proje_v2.json" and KAT.KATALOG_JSON.exists()
    eski = {m["code"]: m for m in json.loads(KAT.KATALOG_DONDURULMUS_JSON.read_text(encoding="utf-8"))}
    yeni = {m["code"]: m for m in json.loads(KAT.KATALOG_JSON.read_text(encoding="utf-8"))}
    assert set(eski) == set(yeni) and len(yeni) == 37
    for kod, m in yeni.items():
        assert m["kat"] in (1, 2) and m["kaynak"] in ("katalog_pdf", "cizim_etiketi", "cizim_seti")
        assert m["dogrulama"] in ("yok", "etiket_okundu", "cizim_seti_ile_dogrulandi")
        assert (m["kat"] == 2) == bool(m["storey_plans"]) == (kod in CIFT)
        assert ("çift kat" in m["family"]) == (m["kat"] == 2)
        if kod not in ("Ç8201", "Ç1031", "Ç1151"):     # öteki 34 kayıt dondurulmuş dosyayla aynı (family/kat dışında)
            assert {k: v for k, v in m.items() if k not in ("family", "kat", "kaynak", "dogrulama")} == {k: v for k, v in eski[kod].items() if k != "family"}
            assert m["kaynak"] == "katalog_pdf" and m["dogrulama"] == "yok"
    assert sum(m["kat"] == 2 for m in yeni.values()) == 13


def test_uc_duzeltilmis_kayit():
    k = Katalog()
    c8201, c1031, c1151 = k.bul("Ç8201"), k.bul("Ç1031"), k.bul("Ç1151")
    assert (c8201["total_m2"], c8201["type"], c8201["kat"]) == ("82", "2+1", 1)
    assert dict((a.split("\n")[-1], b) for a, b in c8201["rooms"]) == {"Veranda": "18,4", "2 Yatak Odası": "23,6", "Banyo": "4,3", "Hol": "6,7", "Yaşam Alanı": "23,3"}
    assert c8201["kaynak"] == "cizim_seti" and c8201["dogrulama"] == "cizim_seti_ile_dogrulandi"
    assert (c1031["total_m2"], c1031["type"], c1031["kat"]) == ("103", "2+1", 1)
    assert dict((a.split("\n")[-1], b) for a, b in c1031["rooms"]) == {"Veranda": "16,8", "2 Yatak Odası": "36,6", "Banyo": "4,7", "Hol": "5,8", "Yaşama Mekanı": "32,8"}
    assert c1031["kaynak"] == "cizim_etiketi" and c1031["dogrulama"] == "etiket_okundu" and "Ç1151" in c1031["not"]
    assert (c1151["total_m2"], c1151["type"]) == ("115", "3+1") and c1151["rooms"][0][1] == "16,5"
    assert c1151["rooms"][1:] == [["3 Yatak Odası", "38,6"], ["2 Banyo", "9"], ["Salon + Mutfak", "30,4"], ["Hol", "12"]]
    assert c1151["kaynak"] == "cizim_etiketi" and c1151["dogrulama"] == "etiket_okundu"


def test_kat_suzgeci_ve_etiket():
    k = Katalog()
    kodlar = lambda L: [m["code"] for m in L]
    hepsi = kodlar(k.yakin_modeller(95.0, "3+1", "celik"))            # kat söylenmedi: süzgeç yok (karar 2)
    assert hepsi == ["Ç1142", "Ç1151", "Ç1241"]
    assert Katalog.kisa(k.bul("Ç1142")) == "Ç1142 (114 m², 3+1, çelik çift kat)"   # etiket doğru
    tek = kodlar(k.yakin_modeller(95.0, "3+1", "celik", kat=1))        # "tek kat": çift katlı yok
    assert tek == ["Ç1151", "Ç1241"] and not set(tek) & CIFT          # tek katlı çelik 3+1 yalnız iki model (Ç1351 4+1)
    cift = kodlar(k.yakin_modeller(95.0, "3+1", "celik", kat=2))
    assert cift == ["Ç1142", "Ç1402", "Ç1552"] and set(cift) <= CIFT
    assert "Ç1031" not in kodlar(k.yakin_modeller(110.0, "3+1", "celik"))   # Ç1031 artık 2+1
    assert kodlar(k.yakin_modeller(100.0, "2+1", "celik", kat=1))[:2] == ["Ç1001", "Ç1021"]
    pre = kodlar(k.yakin_modeller(110.0, "3+1", "prefabrik", kat=1))
    assert pre and not set(pre) & CIFT and all(c.startswith("P") for c in pre)


def test_karar_kat_sayisini_yakin_modellere_gecirir(tmp_path):
    """karar.py: alan_m2 + oda + kat_sayisi=1 → öneri listesinde çift katlı model yok; kat_sayisi yokken etiket 'çift kat' der."""
    bayi = {"kod": "TESTKAT", "ad": "Deneme Bayi", "rol": "bayi"}
    k = KR.Konusma("TESTKAT", tmp_path)
    t = Talep(niyet="yeni_talep", oda_programi="3+1", alan_m2=95, yapi_turu="celik", kat_sayisi=1, guven="yuksek", ozet="95 m² 3+1 tek kat çelik")
    kr = KR.karar_ver(t, k, bayi, Katalog(), "95 metrekare 3+1 tek kat çelik olsun")
    assert kr.eylem == "sor" and kr.soru_alani == "model_veya_olcu"
    assert "Ç1151" in kr.mesaj and "Ç1142" not in kr.mesaj and "çift kat" not in kr.mesaj
    k2 = KR.Konusma("TESTKAT2", tmp_path)
    t2 = Talep(niyet="yeni_talep", oda_programi="3+1", alan_m2=95, yapi_turu="celik", guven="yuksek", ozet="95 m² 3+1 çelik")
    kr2 = KR.karar_ver(t2, k2, dict(bayi, kod="TESTKAT2"), Katalog(), "95 metrekare 3+1 çelik olsun")
    assert kr2.eylem == "sor" and "Ç1142 (114 m², 3+1, çelik çift kat)" in kr2.mesaj


def test_sema_kat_aciklamasi():
    p = Talep.model_json_schema()["properties"]["kat_sayisi"]
    assert "tek kat" in p["description"] and "dubleks" in p["description"] and "null" in p["description"]
    assert json.load(open(Path(__file__).resolve().parents[2] / "beyin" / "testler" / "talep_schema.json", encoding="utf-8"))["properties"]["kat_sayisi"] == p
