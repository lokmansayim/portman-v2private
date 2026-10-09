"""Kapı M (İE-04) betiği: kapi_m_goc.sh göç 003'ü yalnız ön koşullar tutunca uygular; gerçek Postgres'te 001+002'li bir veritabanı
üzerinde koşar (VPS'teki gibi 'bash -s' ve girdiyi yutan sarmalayıcı). Yedek adı kapi_g_yedek.sh ile 'portman-m-oncesi-…' olarak alınır.
Çıktıda numara, mesaj metni, anahtar yok; hiçbir ön koşul eksikken veritabanına dokunulmaz.
Betik 30.09 tarihli kayıttır (kapı M geçti); fikstür o günkü paket düzenini (göç 001–003) kopyalar, İE-06'nın 004 göçü kapsam dışıdır."""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
import uuid

import pytest

from conftest import ADMIN, KOK, _admin, dsn

import worker

SHA = "3" * 64


def _kos(betik: str, o: dict) -> subprocess.CompletedProcess:
    with open(KOK / "vps" / betik, "rb") as f:
        return subprocess.run(["bash", "-s"], stdin=f, capture_output=True, text=True, env=o, timeout=120)


@pytest.fixture
def db_002():
    """Canlıdaki gibi yalnız 001 ve 002 uygulanmış veritabanı (003 pakette var, veritabanında yok)."""
    import psycopg
    ad = "m_" + uuid.uuid4().hex[:12]
    with _admin() as c:
        c.execute(f"CREATE DATABASE {ad}")
    with psycopg.connect(dsn(ad), autocommit=True) as c:
        c.execute("CREATE TABLE sema_surumu (surum int PRIMARY KEY, ad text NOT NULL, uygulandi timestamptz NOT NULL DEFAULT now())")
        for p in sorted((KOK / "kanal" / "goc").glob("00[12]_*.sql")):
            c.execute(p.read_text(encoding="utf-8"))
            c.execute("INSERT INTO sema_surumu (surum, ad) VALUES (%s, %s)", (int(p.name[:3]), p.name))
    yield ad
    with _admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")


@pytest.fixture
def ortam(tmp_path, db_002):
    home = tmp_path / "home"; app = home / "app"; (app / "goc").mkdir(parents=True)
    # 30.09'daki v1.3 paketinin düzeni: kod dosyaları ve YALNIZ 001–003 göçleri (kopya; sembolik bağ olsa depo.py gerçek kanal/goc'u,
    # yani İE-06'nın 004 göçünü de görürdü ve betiğin "eksik göç tam olarak [3]" ön koşulu hiç tutmazdı). Betik tarihli kayıttır.
    import shutil
    for ad in ("depo.py", "kalici.py", "worker.py", "etkilesim.py"):
        shutil.copy(KOK / "kanal" / ad, app / ad)
    for p in sorted((KOK / "kanal" / "goc").glob("00[123]_*.sql")):
        shutil.copy(p, app / "goc" / p.name)
    for ad in ("beyin", "motor", "is_emri"):             # paket düzeninde kökte dururlar (kalici.py beyin'i içe alır)
        (app / ad).symlink_to(KOK / ad)
    (app / "PACKAGE_SHA256").write_text(SHA); (app / "SURUM.txt").write_text("kanal-v1.3-test\n")
    bin_ = tmp_path / "bin"; bin_.mkdir()
    (bin_ / "yutan").write_text('#!/usr/bin/env bash\ncat > /dev/null\nexec "$@"\n'); (bin_ / "yutan").chmod(0o755)
    host = dict(x.split("=", 1) for x in ADMIN.split())
    baglanti = f"-h {host.get('host', '127.0.0.1')} -p {host.get('port', '5432')} -U {host.get('user', 'postgres')}"
    yedek = tmp_path / "yedek"; yedek.mkdir()
    o = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "PM_HOME": str(home), "PM_PY": os.sys.executable, "PM_BEKLENEN": SHA,
         "PM_OLARAK": f"{bin_ / 'yutan'} env PORTMAN_PG_DSN=postgresql://{host.get('user', 'postgres')}@{host.get('host', '127.0.0.1')}:"
                      f"{host.get('port', '5432')}/{db_002} PORTMAN_KANAL_DIR={tmp_path / 'data'}",
         "PM_PSQL": f"psql -X -q -tA {baglanti}", "PM_PGDUMP": f"pg_dump {baglanti}", "PM_PGRESTORE": "pg_restore", "PM_DB": db_002,
         "PM_YEDEK": str(yedek)}
    return {"o": o, "app": app, "yedek": yedek, "db": db_002}


def _eksik(ortam: dict) -> list[int]:
    """Paketteki (app/goc: 001–003) depo.py ile eksik göçler; betiğin kendi gördüğü liste budur."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("depo_kapi_m", ortam["app"] / "depo.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.Depo(dsn(ortam["db"])).eksik_goc()


def test_on_kosullar_tutmayinca_dokunmaz(ortam):
    o = ortam["o"]
    assert _eksik(ortam) == [3]
    r = _kos("kapi_m_goc.sh", {**o, "PM_BEKLENEN": ""})
    assert r.returncode == 1 and "DUR: PM_BEKLENEN" in r.stdout
    r = _kos("kapi_m_goc.sh", {**o, "PM_BEKLENEN": "f" * 64})
    assert r.returncode == 1 and "aynı: HAYIR" in r.stdout and "DUR: kurulu paket beklenen değil" in r.stdout
    r = _kos("kapi_m_goc.sh", o)                                        # yedek yok
    assert r.returncode == 1 and "DUR: yedek yok" in r.stdout
    eski = ortam["yedek"] / "portman-m-oncesi-20260101.dump"; eski.write_bytes(b"x")
    t = time.time() - 4 * 3600; os.utime(eski, (t, t))
    r = _kos("kapi_m_goc.sh", o)
    assert r.returncode == 1 and "DUR: yedek 3 saatten eski" in r.stdout
    assert _eksik(ortam) == [3]
    assert "hiçbir şey değiştirilmedi" in r.stdout


def test_yedek_sonra_kuru_kosum_sonra_goc(ortam):
    import psycopg
    o = ortam["o"]
    # 1) yedek: kapi_g_yedek.sh artık portman-m-… adını da kabul eder
    r = _kos("kapi_g_yedek.sh", {**o, "PM_AD": "portman-m-oncesi-20260930"})
    assert r.returncode == 0, r.stdout + r.stderr
    dosya = ortam["yedek"] / "portman-m-oncesi-20260930.dump"
    assert dosya.exists() and f"sha256: {hashlib.sha256(dosya.read_bytes()).hexdigest()}" in r.stdout
    assert _kos("kapi_g_yedek.sh", {**o, "PM_AD": "portman-mm-oncesi-x"}).returncode == 1
    # 2) açık iş varsa durur
    with psycopg.connect(dsn(ortam["db"]), autocommit=True) as c:
        c.execute("INSERT INTO mesajlar (id, gonderen, tur, wa_zamani, ham) VALUES ('wamid.TESTM1', '900000000101', 'text', now(), '{}'::jsonb)")
        c.execute("INSERT INTO isler (mesaj_id, gonderen, durum) VALUES ('wamid.TESTM1', '900000000101', 'sirada')")
    r = _kos("kapi_m_goc.sh", o)
    assert r.returncode == 1 and "DUR: Postgres'te açık iş var" in r.stdout and _eksik(ortam) == [3]
    with psycopg.connect(dsn(ortam["db"]), autocommit=True) as c:
        c.execute("UPDATE isler SET durum = 'bitti'")
    # 3) kuru koşum: ön koşullar tamam, göç uygulanmaz
    r = _kos("kapi_m_goc.sh", {**o, "PM_TEST": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "aynı: EVET" in r.stdout and "Postgres (önce): eksik_goc=[3] acik_is=0" in r.stdout and "göç UYGULANMADI" in r.stdout
    assert _eksik(ortam) == [3]
    # 4) gerçek göç
    r = _kos("kapi_m_goc.sh", o)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "uygulanan göçler: [3]" in out and "SONUÇ: göç 003 uygulandı" in out
    assert "Postgres (sonra): eksik_goc=[] tablolar=['adaylar', 'secenek_setleri'] revizyonlar.ekler=1 giden_kind_image=True giden_kind_interactive=True" in out
    assert _eksik(ortam) == []
    assert "900000000101" not in out and "wamid." not in out
    # 5) ikinci kez: eksik göç [3] değil → durur, hiçbir şey yapmaz
    r = _kos("kapi_m_goc.sh", o)
    assert r.returncode == 1 and "DUR: beklenen eksik göç [3] değil" in r.stdout
