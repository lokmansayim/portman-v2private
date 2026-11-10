"""İE-34 · vps/is_emri_ver.sh (bayinin onayladığı planın İş Emri'ni ver; salt okunur) gerçek Postgres'te, göçleri uygulanmış veritabanıyla.
Yalnız onaylı revizyon gelir; telefon numarasına benzeyen her metin maskelenir; liste gönderen numarasını yazmaz; veritabanı değişmez.
Ağ, canlı, LLM ve WhatsApp yok."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from conftest import NUMARA_A, dsn

KOK = Path(__file__).resolve().parents[2]
BETIK = KOK / "vps" / "is_emri_ver.sh"


def _ie(no: str, rev: int, metin: str) -> dict:
    ie = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
    ie["is_emri_no"] = no; ie["revizyon"] = rev
    ie["talep"] = {"bayi": {"kod": "TSTA", "ad": "Deneme Bayi A"}, "musteri_adi": "Deneme Müşteri", "metin": metin}
    return ie


def _hazirla(depo) -> None:
    import psycopg
    from psycopg.types.json import Jsonb
    with psycopg.connect(dsn(depo.ad), autocommit=True) as c:
        for mid in ("wamid.IE34A", "wamid.IE34B", "wamid.IE34C"):
            c.execute("INSERT INTO mesajlar (id, gonderen, bayi_kod, tur, metin, wa_zamani, ham) VALUES (%s, %s, 'TSTA', 'text', '', now(), '{}')",
                      (mid, NUMARA_A))
        pid = c.execute("INSERT INTO projeler (gonderen, bayi_kod, ilk_is_emri_no) VALUES (%s, 'TSTA', 'PM-TSTA-20261110-1') RETURNING id",
                        (NUMARA_A,)).fetchone()[0]
        satirlar = [(1, "yerini_aldi", "wamid.IE34A", None, "ilk plan"), (2, "onaylandi", "wamid.IE34B", "wamid.IE34C",
                    "Müşteri numarası 0532 123 45 67, veranda önde"), (3, "onay_bekliyor", "wamid.IE34C", None, "üçüncü")]
        for rev, durum, kaynak, onay, metin in satirlar:
            c.execute("INSERT INTO revizyonlar (proje_id, rev, is_emri_no, gonderen, bayi_kod, kaynak_mesaj_id, is_emri, dogrulandi, durum, onay_mesaj_id, "
                      "onaylandi) VALUES (%s, %s, 'PM-TSTA-20261110-1', %s, 'TSTA', %s, %s, true, %s, %s, %s)",
                      (pid, rev, NUMARA_A, kaynak, Jsonb(_ie("PM-TSTA-20261110-1", rev, metin)), durum, onay, datetime.now(timezone.utc) if onay else None))


def _kos(tmp_path: Path, depo, *arg) -> subprocess.CompletedProcess:
    psql = tmp_path / "psql"
    psql.write_text(f'#!/usr/bin/env bash\nexec psql -X -q -tA -d "{dsn(depo.ad)}" "$@"\n', encoding="utf-8"); psql.chmod(0o755)
    return subprocess.run(["bash", str(BETIK), *arg], env={**os.environ, "PM_PSQL": str(psql), "PM_KOK": str(tmp_path / "yok"), "PM_PYTHON": sys.executable},
                          capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)


def _sayim(depo) -> tuple:
    import psycopg
    with psycopg.connect(dsn(depo.ad)) as c:
        return c.execute("SELECT count(*), string_agg(durum || ':' || md5(is_emri::text), ',' ORDER BY rev) FROM revizyonlar").fetchone()


def test_onayli_revizyonun_is_emri_maskeli_gelir(tmp_path, depo):
    _hazirla(depo)
    once = _sayim(depo)
    r = _kos(tmp_path, depo, "PM-TSTA-20261110-1", "2")
    assert r.returncode == 0, r.stderr
    ie = json.loads(r.stdout)
    assert ie["is_emri_no"] == "PM-TSTA-20261110-1" and ie["revizyon"] == 2
    assert ie["talep"]["metin"] == "Müşteri numarası …, veranda önde" and "0532" not in r.stdout and NUMARA_A not in r.stdout
    beklenen = _ie("PM-TSTA-20261110-1", 2, "")
    assert {k: v for k, v in ie.items() if k != "talep"} == {k: v for k, v in beklenen.items() if k != "talep"}   # çizim girdisi aynen
    assert _sayim(depo) == once                                                         # veritabanı değişmedi


def test_onaylanmamis_revizyon_verilmez(tmp_path, depo):
    _hazirla(depo)
    for rev in ("1", "3", "9"):
        r = _kos(tmp_path, depo, "PM-TSTA-20261110-1", rev)
        assert r.returncode == 1 and "onaylı değil ya da yok" in r.stderr and r.stdout == "", (rev, r.stdout, r.stderr)
    r = _kos(tmp_path, depo, "PM-TSTA'; DROP TABLE x; --", "2")
    assert r.returncode == 1 and "biçimi tanınmadı" in r.stderr
    r = _kos(tmp_path, depo, "PM-TSTA-20261110-1", "iki")
    assert r.returncode == 1 and "rev bir sayı olmalı" in r.stderr


def test_liste_numarasiz(tmp_path, depo):
    _hazirla(depo)
    r = _kos(tmp_path, depo)
    assert r.returncode == 0, r.stderr
    assert "PM-TSTA-20261110-1 r02 · bayi TSTA · prefabrik · onaylandı " in r.stdout
    assert "r01" not in r.stdout and "r03" not in r.stdout and NUMARA_A not in r.stdout
