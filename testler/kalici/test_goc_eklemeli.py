"""İE-06 · göç kuralı (docs/is_emirleri/IE-06.md › Sürüm kuralı): 004 ve sonraki göçler yalnız ekler. Önceki sürümün kodu yeni şemada
çalışmalı ki tek komutla sürüm geri dönüşü şemaya dokunmasın. Statik tarama + gerçek Postgres'te tekrar koşulabilirlik."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import KOK

GOC = KOK / "kanal" / "goc"
GOC_SURUMLERI = sorted(int(p.name[:3]) for p in GOC.glob("[0-9][0-9][0-9]_*.sql"))
YASAK = [(r"\bDROP\s+TABLE\b", "DROP TABLE"), (r"\bDROP\s+COLUMN\b", "DROP COLUMN"), (r"\bRENAME\b", "RENAME"),
         (r"\bALTER\s+COLUMN\s+\S+\s+TYPE\b", "tür değişikliği"), (r"\bSET\s+NOT\s+NULL\b", "sonradan NOT NULL"), (r"\bTRUNCATE\b", "TRUNCATE"),
         (r"\bDELETE\s+FROM\b", "DELETE")]


def _yorumsuz(sql: str) -> str:
    return "\n".join(s.split("--", 1)[0] for s in sql.splitlines())


def test_004_ve_sonrasi_yalniz_ekler():
    dosyalar = sorted(p for p in GOC.glob("[0-9][0-9][0-9]_*.sql") if int(p.name[:3]) >= 4)
    assert dosyalar, "004 göçü yok"
    for p in dosyalar:
        sql = _yorumsuz(p.read_text(encoding="utf-8"))
        for rx, ad in YASAK:
            assert not re.search(rx, sql, re.I), f"{p.name}: {ad} yasak (yalnız ekleme)"
        # ADD COLUMN … NOT NULL yalnız DEFAULT ile (eski satırlar ve eski kodun INSERT'leri bozulmasın)
        for m in re.finditer(r"ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+\S+\s+[^;]*NOT\s+NULL[^;]*;", sql, re.I):
            assert re.search(r"\bDEFAULT\b", m.group(0), re.I), f"{p.name}: varsayılansız NOT NULL sütun: {m.group(0)[:80]}"
        # CREATE TABLE / INDEX ve ADD COLUMN tekrar koşulabilir olmalı
        for m in re.finditer(r"\b(CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)|ADD\s+COLUMN)\b(?!\s+IF\s+NOT\s+EXISTS)", sql, re.I):
            pytest.fail(f"{p.name}: '{m.group(0)}' IF NOT EXISTS olmadan yazılmış")


def test_004_tekrar_kosulabilir(depo):
    """Şablon veritabanında 004 uygulanmış; aynı dosya ikinci kez koşunca hata vermez ve şema aynı kalır."""
    sql = (GOC / "004_bayi_ve_kanal.sql").read_text(encoding="utf-8")
    def sutunlar(c):
        return c.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' ORDER BY 1, 2").fetchall()
    with depo.baglan() as c:
        once = sutunlar(c)
        with c.transaction():
            c.execute(sql)
        assert sutunlar(c) == once
        # İE-08 8b: beklenen sürümler depodaki göç dosyalarından (006 eklendi; her yeni göçte elle sayı yazılmasın)
        assert c.execute("SELECT surum FROM sema_surumu ORDER BY surum").fetchall() == [{"surum": n} for n in GOC_SURUMLERI]


def test_eski_surumun_insertleri_yeni_semada_calisir(depo):
    """Önceki sürümün (göç 003 dönemi) yazdığı INSERT biçimleri: bayiler (numara, kod, ad, rol) ve mesajlar (kaynak/sahiplenildi vermeden)."""
    with depo.baglan() as c, c.transaction():
        c.execute("INSERT INTO bayiler (numara, kod, ad, rol) VALUES ('900000000111', 'B0111', 'Eski', 'bayi')")
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, metin, wa_zamani, ham) VALUES ('wamid.ESKI', '900000000111', 'text', 'x', now(), '{}')")
        r = c.execute("SELECT hitap, firma, bolge, aktif, kaynak FROM bayiler WHERE numara = '900000000111'").fetchone()
        assert r == {"hitap": "", "firma": "", "bolge": "", "aktif": True, "kaynak": "kanal"}
        assert c.execute("SELECT kaynak, sahiplenildi FROM mesajlar WHERE id = 'wamid.ESKI'").fetchone() == {"kaynak": "vps", "sahiplenildi": True}


def test_005_kind_template_kaynak_ve_rol_test(depo):
    """İE-07 göç 005: giden.kind 'template' kabul, giden.kaynak varsayılanı 'ajan', bayiler.rol 'test' kabul; 004 biçimli INSERT'ler
    (kaynak vermeden) çalışır; dosya ikinci kez koşunca şema aynı kalır."""
    sql = (GOC / "005_sablon_ve_kaynak.sql").read_text(encoding="utf-8")
    with depo.baglan() as c, c.transaction():
        c.execute("INSERT INTO bayiler (numara, kod, ad, rol) VALUES ('900000000905', 'TEST', 'Kuru Koşu', 'test')")
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, metin, wa_zamani, ham) VALUES ('wamid.G005', '900000000905', 'text', 'x', now(), '{}')")
        is_id = c.execute("INSERT INTO isler (mesaj_id, gonderen, durum) VALUES ('wamid.G005', '900000000905', 'bitti') RETURNING id").fetchone()["id"]
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum) "
                  "VALUES ('out_g005_1', %s, 'wamid.G005', 1, 'PATRON', 'bildirim', 'template', 'şablon', 'bekliyor')", (is_id,))
        c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum, kaynak) "
                  "VALUES ('out_g005_2', %s, 'wamid.G005', 2, '900000000905', 'cevap', 'text', 'panel metni', 'bekliyor', 'panel')", (is_id,))
        r = c.execute("SELECT id, kaynak FROM giden WHERE is_id = %s ORDER BY sira", (is_id,)).fetchall()
        assert r == [{"id": "out_g005_1", "kaynak": "ajan"}, {"id": "out_g005_2", "kaynak": "panel"}]
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("INSERT INTO giden (id, is_id, mesaj_id, sira, alici, tur, kind, govde, durum) "
                          "VALUES ('out_g005_3', %s, 'wamid.G005', 3, 'PATRON', 'bildirim', 'sticker', 'x', 'bekliyor')", (is_id,))
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("INSERT INTO bayiler (numara, kod, ad, rol) VALUES ('900000000906', 'X', 'x', 'robot')")
    with depo.baglan() as c:
        once = c.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' ORDER BY 1, 2").fetchall()
        with c.transaction():
            c.execute(sql)
        assert c.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' ORDER BY 1, 2").fetchall() == once
        assert c.execute("SELECT kaynak FROM giden WHERE id = 'out_g005_2'").fetchone() == {"kaynak": "panel"}


def test_006_muhendis_kontrolleri_tekrar_kosulabilir(depo):
    """İE-08 8b: 006 iki kez koşar, şema aynı kalır; durum ve Patron durumu CHECK'li; (iş no, rev) tek."""
    sql = (GOC / "006_muhendis.sql").read_text(encoding="utf-8")
    with depo.baglan() as c:
        once = c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'muhendis_kontrolleri' ORDER BY 1").fetchall()
        with c.transaction():
            c.execute(sql)
        assert c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'muhendis_kontrolleri' ORDER BY 1").fetchall() == once
        with c.transaction():
            c.execute("INSERT INTO mesajlar (id, gonderen, tur, metin, wa_zamani, ham) VALUES ('wamid.G6', '900000000111', 'text', 'x', now(), '{}')")
            c.execute("INSERT INTO muhendis_kontrolleri (is_emri_no, rev, bayi, onay_mesaj_id) VALUES ('PM-X-1', 1, '900000000111', 'wamid.G6')")
            r = c.execute("SELECT durum, patron_durum, hatirlatma_sayisi, listeler FROM muhendis_kontrolleri").fetchone()
            assert r == {"durum": "bekliyor", "patron_durum": "yok", "hatirlatma_sayisi": 0, "listeler": []}
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("INSERT INTO muhendis_kontrolleri (is_emri_no, rev, bayi, onay_mesaj_id) VALUES ('PM-X-1', 1, '900000000111', 'wamid.G6')")
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("UPDATE muhendis_kontrolleri SET durum = 'baska'")


def test_007_plan_uretimleri_tekrar_kosulabilir(depo):
    """İE-14: 007 iki kez koşar, şema aynı kalır; durum CHECK'li; mesaj başına tek üretim kaydı."""
    sql = (GOC / "007_plan_uretimleri.sql").read_text(encoding="utf-8")
    with depo.baglan() as c:
        once = c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'plan_uretimleri' ORDER BY 1").fetchall()
        with c.transaction():
            c.execute(sql)
        assert c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'plan_uretimleri' ORDER BY 1").fetchall() == once
        with c.transaction():
            c.execute("INSERT INTO mesajlar (id, gonderen, tur, metin, wa_zamani, ham) VALUES ('wamid.G7', '900000000111', 'text', 'x', now(), '{}')")
            c.execute("INSERT INTO plan_uretimleri (mesaj_id, gonderen, durum) VALUES ('wamid.G7', '900000000111', 'gecerli')")
            r = c.execute("SELECT cagri, talep, denemeler, is_emri_no FROM plan_uretimleri").fetchone()
            assert r == {"cagri": 0, "talep": {}, "denemeler": [], "is_emri_no": None}
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("INSERT INTO plan_uretimleri (mesaj_id, gonderen, durum) VALUES ('wamid.G7', '900000000111', 'gecerli')")
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("UPDATE plan_uretimleri SET durum = 'baska'")


def test_007_r3_sutunlari_ve_008_okuma_kiyaslari_tekrar_kosulabilir(depo):
    """İE-14 r3: 007'nin yalnız ekleyen sütunları ve 008 (gölge okuma kıyası) iki kez koşar, şema aynı kalır; mesaj başına tek kıyas."""
    with depo.baglan() as c:
        kol = {r["column_name"] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'plan_uretimleri'").fetchall()}
        assert {"yol", "puan", "sure_ms", "program", "adaylar", "degisen"} <= kol
        once = c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'okuma_kiyaslari' ORDER BY 1").fetchall()
        assert once
        for ad in ("007_plan_uretimleri.sql", "008_okuma_kiyaslari.sql"):
            with c.transaction():
                c.execute((GOC / ad).read_text(encoding="utf-8"))
        assert c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'okuma_kiyaslari' ORDER BY 1").fetchall() == once
        with c.transaction():
            c.execute("INSERT INTO mesajlar (id, gonderen, tur, metin, wa_zamani, ham) VALUES ('wamid.G8', '900000000111', 'text', 'x', now(), '{}')")
            c.execute("INSERT INTO okuma_kiyaslari (mesaj_id, gonderen, sinif) VALUES ('wamid.G8', '900000000111', 'aynı')")
            assert c.execute("SELECT kural, llm, cagri, etiket FROM okuma_kiyaslari").fetchone() == {"kural": {}, "llm": {}, "cagri": 0, "etiket": None}
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("INSERT INTO okuma_kiyaslari (mesaj_id, gonderen, sinif) VALUES ('wamid.G8', '900000000111', 'aynı')")
