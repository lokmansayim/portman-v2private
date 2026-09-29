"""İE-02 · vps/pg_kurulum.sh (kapı D) güvenlik özellikleri, yerel Postgres'te (PM_TEST kipi: paket, pip ve cron adımları atlanır,
bağlantı PM_PG ile verilir). Lokman'ın 28.09 akşam koşulları:
  - yedeklerin otomatik silinmesi ayrı tercih, varsayılanı kapalı;
  - geri yükleme denemesi var olan ve sahipliği doğrulanmamış bir veritabanını silmez;
  - yerel bağlantı şartı sağlanmıyorsa betik uyarıp geçmez, durur.
"""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import psycopg
import pytest

from conftest import ADMIN, KOK

BETIK = KOK / "vps" / "pg_kurulum.sh"
pytestmark = pytest.mark.skipif(not ADMIN, reason="PORTMAN_TEST_PG yok")


def _bag() -> dict:
    return dict(p.split("=", 1) for p in ADMIN.split())


def _pg_secenek(kullanici: str) -> str:
    b = _bag()
    return f"-h {b.get('host', '127.0.0.1')} -p {b.get('port', '5432')} -U {kullanici}"


def _sql(sorgu: str, *arg):
    with psycopg.connect(ADMIN + " dbname=postgres", autocommit=True) as c:
        return c.execute(sorgu, arg).fetchall() if sorgu.lstrip().upper().startswith("SELECT") else c.execute(sorgu, arg)


@pytest.fixture
def ortam(tmp_path):
    ad = "pmk_" + uuid.uuid4().hex[:8]
    olusan = [ad]
    env = {**os.environ, "PM_TEST": "1", "PM_DB": ad, "PM_YEDEK": str(tmp_path / "yedek"), "PM_CRON_DOSYA": str(tmp_path / "cron"),
           "PM_PG": _pg_secenek("postgres"), "PM_PG_PORTMAN": _pg_secenek("portman"), "PM_PG_PORT": _bag().get("port", "5432")}
    yield env, ad, olusan, tmp_path
    for d in olusan + [r[0] for r in _sql("SELECT datname FROM pg_database WHERE datname LIKE 'portman_geri_deneme_%%'")]:
        _sql(f"DROP DATABASE IF EXISTS {d} WITH (FORCE)")


def _kos(env, **ek):
    return subprocess.run(["bash", str(BETIK)], env={**env, **ek}, capture_output=True, text=True, timeout=120)


def test_kurulum_kosar_yedek_silme_varsayilan_kapali_deneme_veritabani_kalmaz(ortam):
    env, ad, _, tmp = ortam
    _sql("CREATE DATABASE portman_geri_deneme")          # eski sabit adla, başkasının açtığı bir veritabanı
    try:
        r = _kos(env)
        assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
        assert "otomatik silme KAPALI" in r.stdout
        cron = (tmp / "cron").read_text()
        assert "-delete" not in cron and "Otomatik silme: kapalı" in cron and r"$(date +\%Y\%m\%d)" in cron
        assert _sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s", ad) == [("portman",)]
        assert _sql("SELECT count(*) FROM pg_database WHERE datname LIKE 'portman_geri_deneme_%%'") == [(0,)]   # yalnız kendi açtığını sildi
        assert _sql("SELECT count(*) FROM pg_database WHERE datname = 'portman_geri_deneme'") == [(1,)]          # başkasınınkine dokunmadı
        assert list((tmp / "yedek").glob("kurulum-deneme-*.dump"))
        assert _kos(env).returncode == 0                                                                   # tekrar çalıştırılabilir
    finally:
        _sql("DROP DATABASE IF EXISTS portman_geri_deneme WITH (FORCE)")


def test_yedek_silme_ayri_tercih(ortam):
    env, _, _, tmp = ortam
    r = _kos(env, PM_YEDEK_SAKLA_GUN="14")
    assert r.returncode == 0, r.stderr[-800:]
    satir = [s for s in (tmp / "cron").read_text().splitlines() if s.startswith("17 3")][0]
    assert "-mtime +14 -delete" in satir and "&& find" in satir and "\\&" not in satir
    assert subprocess.run(["bash", "-n", "-c", satir.split(" postgres ", 1)[1].replace(r"\%", "%")]).returncode == 0
    for kotu in ("abc", "0", "-3", "1 && rm"):
        r = _kos(env, PM_YEDEK_SAKLA_GUN=kotu)
        assert r.returncode != 0 and "PM_YEDEK_SAKLA_GUN geçersiz" in r.stderr


def test_sahibi_baskasi_olan_veritabanina_dokunmaz_durur(ortam):
    env, ad, _, _ = ortam
    _sql(f"CREATE DATABASE {ad}")                        # sahibi postgres
    r = _kos(env)
    assert r.returncode != 0 and "sahibi 'postgres'" in r.stderr
    assert _sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s", ad) == [("postgres",)]


def test_deneme_adi_varsa_dokunmaz_durur(ortam):
    env, _, olusan, _ = ortam
    ad = "portman_geri_deneme_sinama_1"
    _sql(f"CREATE DATABASE {ad}"); olusan.append(ad)
    r = _kos(env, PM_CALISMA="sinama_1")
    assert r.returncode != 0 and "zaten var; dokunulmadı" in r.stderr
    assert _sql("SELECT count(*) FROM pg_database WHERE datname = %s", ad) == [(1,)]


def _islev(islev: str, arg: str) -> int:
    kod = f'PM_YALNIZ_ISLEVLER=1; PM_PG_PORT=5432; . "{BETIK}"; {islev} "$1"'
    return subprocess.run(["bash", "-c", kod, "_", arg]).returncode


@pytest.mark.parametrize("deger, yerel", [("localhost", True), ("127.0.0.1", True), ("::1", True), ("localhost, 127.0.0.1", True),
                                          ("", True), ("*", False), ("0.0.0.0", False), ("localhost,10.0.0.5", False), ("37.148.213.103", False)])
def test_yerel_dinleme(deger, yerel):
    assert (_islev("yerel_dinleme", deger) == 0) is yerel


@pytest.mark.parametrize("deger, yerel", [("127.0.0.1\n::1", True), ("", True), ("samehost", True),
                                          ("127.0.0.1\n0.0.0.0", False), ("all", False), ("10.0.0.0", False)])
def test_yerel_hba(deger, yerel):
    assert (_islev("yerel_hba", deger) == 0) is yerel


@pytest.mark.parametrize("deger, yerel", [("127.0.0.1:5432\n[::1]:5432", True), ("", True), ("0.0.0.0:5432", False),
                                          ("*:5432", False), ("[::]:5432", False), ("37.148.213.103:5432", False)])
def test_yerel_soketler(deger, yerel):
    assert (_islev("yerel_soketler", deger) == 0) is yerel


# ───────── uçtan uca "durur" sınaması: ayrı, geçici bir Postgres kümesi (yerel olmayan yapılandırmayla) ─────────
_PGBIN = Path("/usr/lib/postgresql/16/bin")


def _kume(tmp_path, listen: str, hba_ek: str = ""):
    import pwd, shutil, socket
    if not (_PGBIN / "initdb").exists():
        pytest.skip("initdb yok")
    try:
        pwd.getpwnam("pgtest")
    except KeyError:
        pytest.skip("pgtest kullanıcısı yok")
    d = Path("/home/pgtest") / f"kume_{uuid.uuid4().hex[:6]}"
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    su = lambda k: subprocess.run(["su", "pgtest", "-c", k], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    r = su(f"{_PGBIN}/initdb -D {d} -U postgres -A trust >/dev/null")
    assert r.returncode == 0, r.stderr
    if hba_ek:
        su(f"echo '{hba_ek}' >> {d}/pg_hba.conf")
    r = su(f"setsid {_PGBIN}/pg_ctl -D {d} -w -o \"-p {port} -k {d} -c listen_addresses='{listen}'\" -l {d}/log start")
    assert r.returncode == 0, r.stdout + r.stderr
    return d, port, lambda: (su(f"{_PGBIN}/pg_ctl -D {d} -m immediate stop"), shutil.rmtree(d, ignore_errors=True))


@pytest.mark.parametrize("listen, hba_ek, beklenen", [("*", "", "listen_addresses='*' yerel değil"),
                                                      ("127.0.0.1", "host all all 0.0.0.0/0 trust", "pg_hba.conf yerel olmayan")])
def test_yerel_olmayan_yapilandirmada_durur_hicbir_sey_olusturmaz(tmp_path, listen, hba_ek, beklenen):
    d, port, kapat = _kume(tmp_path, listen, hba_ek)
    try:
        secenek = f"-h 127.0.0.1 -p {port} -U postgres"
        env = {**os.environ, "PM_TEST": "1", "PM_DB": "portman", "PM_YEDEK": str(tmp_path / "yedek"), "PM_CRON_DOSYA": str(tmp_path / "cron"),
               "PM_PG": secenek, "PM_PG_PORTMAN": f"-h 127.0.0.1 -p {port} -U portman", "PM_PG_PORT": str(port)}
        r = subprocess.run(["bash", str(BETIK)], env=env, capture_output=True, text=True, timeout=120)
        assert r.returncode != 0 and beklenen in r.stderr, r.stdout[-500:] + r.stderr[-500:]
        with psycopg.connect(f"host=127.0.0.1 port={port} user=postgres dbname=postgres") as c:
            assert c.execute("SELECT count(*) FROM pg_roles WHERE rolname = 'portman'").fetchone()[0] == 0
            assert c.execute("SELECT count(*) FROM pg_database WHERE datname LIKE 'portman%%'").fetchone()[0] == 0
        assert not (tmp_path / "cron").exists() and not (tmp_path / "yedek").exists()
    finally:
        kapat()
