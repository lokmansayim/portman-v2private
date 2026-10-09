"""İE-06 · göç kuralı (docs/is_emirleri/IE-06.md › Sürüm kuralı): 004 ve sonraki göçler yalnız ekler. Önceki sürümün kodu yeni şemada
çalışmalı ki tek komutla sürüm geri dönüşü şemaya dokunmasın. Statik tarama + gerçek Postgres'te tekrar koşulabilirlik."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import KOK

GOC = KOK / "kanal" / "goc"
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
        assert c.execute("SELECT surum FROM sema_surumu ORDER BY surum").fetchall() == [{"surum": 1}, {"surum": 2}, {"surum": 3}, {"surum": 4}]


def test_eski_surumun_insertleri_yeni_semada_calisir(depo):
    """Önceki sürümün (göç 003 dönemi) yazdığı INSERT biçimleri: bayiler (numara, kod, ad, rol) ve mesajlar (kaynak/sahiplenildi vermeden)."""
    with depo.baglan() as c, c.transaction():
        c.execute("INSERT INTO bayiler (numara, kod, ad, rol) VALUES ('900000000111', 'B0111', 'Eski', 'bayi')")
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, metin, wa_zamani, ham) VALUES ('wamid.ESKI', '900000000111', 'text', 'x', now(), '{}')")
        r = c.execute("SELECT hitap, firma, bolge, aktif, kaynak FROM bayiler WHERE numara = '900000000111'").fetchone()
        assert r == {"hitap": "", "firma": "", "bolge": "", "aktif": True, "kaynak": "kanal"}
        assert c.execute("SELECT kaynak, sahiplenildi FROM mesajlar WHERE id = 'wamid.ESKI'").fetchone() == {"kaynak": "vps", "sahiplenildi": True}
