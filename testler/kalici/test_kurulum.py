"""İE-06 · vps/kurulum.sh (Kapı 2) sahte dizinlerde ve yerel Postgres'te (PM_TEST=1: apt, kullanıcı, certbot, ufw, servis yok):
dizinler; dağıtım anahtarı (yalnız açık anahtar ekrana); settings.json varsayılanı kanal/ayarlar.py ile aynı; panel.env oturum
anahtarı (yazdırılmaz); gömülü systemd/nginx/sshd/fail2ban/logrotate dosyaları depodaki kopyalarla birebir; sshd drop-in yalnız
authorized_keys doluyken ve sözdizimi geçmezse geri alınır; sertifika/DNS kararı; ikinci koşu aynı değerleri korur.
test_pg_kurulum.py'den taşınanlar: yalnız yerel dinleme işlevleri, 'portman' veritabanının sahibi başkaysa durur, yerel olmayan
Postgres yapılandırmasında durur ve hiçbir şey oluşturmaz (ayrı geçici küme; initdb ve pgtest yoksa atlanır)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from pathlib import Path

import psycopg
import pytest

from conftest import ADMIN, KOK

import ayarlar as AY

BETIK = KOK / "vps" / "kurulum.sh"
ALAN = "portman.ornek.invalid"
pytestmark = pytest.mark.skipif(not ADMIN, reason="PORTMAN_TEST_PG yok")

SAHTE_SSHD = """#!/usr/bin/env bash
# sahte sshd: -t → 0 (PM_SSHD_BOZUK=1 ise 1); -T → drop-in varsa passwordauthentication no
if [ "${1:-}" = "-t" ]; then [ -n "${PM_SSHD_BOZUK:-}" ] && exit 1; exit 0; fi
if [ "${1:-}" = "-T" ]; then
  if [ -f "$PM_SSHD_DIR/00-portman.conf" ]; then echo "passwordauthentication no"; else echo "passwordauthentication yes"; fi
  echo "permitrootlogin prohibit-password"; exit 0
fi
exit 0
"""
SAHTE_KEYGEN = """#!/usr/bin/env bash
# sahte ssh-keygen: -f <yol> → özel ve açık anahtar dosyaları (rastgele içerik; gerçek anahtar değil)
while [ $# -gt 0 ]; do case "$1" in -f) YOL="$2"; shift ;; esac; shift; done
head -c 32 /dev/urandom | base64 > "$YOL"
echo "ssh-ed25519 $(head -c 24 /dev/urandom | base64 | tr -d '/+=') portman-vps-deploy" > "$YOL.pub"
"""
SAHTE_SYSTEMCTL = '#!/usr/bin/env bash\necho "$@" >> "$PM_SYSTEMCTL_LOG"\n'


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
    bin_ = tmp_path / "bin"; bin_.mkdir()
    for isim, icerik in (("sshd", SAHTE_SSHD), ("ssh-keygen", SAHTE_KEYGEN), ("systemctl", SAHTE_SYSTEMCTL)):
        (bin_ / isim).write_text(icerik); (bin_ / isim).chmod(0o755)
    d = {k: tmp_path / k for k in ("kok", "etc", "systemd", "nginx", "sshd", "f2b", "logrotate", "le", "webroot")}
    yetkili = tmp_path / "authorized_keys"; yetkili.write_text("ssh-ed25519 AAAAdeneme deneme@mac\n")
    env = {**os.environ, "PM_TEST": "1", "PM_ALAN": ALAN, "PM_EPOSTA": "ornek@ornek.invalid", "PM_KOK": str(d["kok"]), "PM_ETC": str(d["etc"]),
           "PM_SYSTEMD_DIR": str(d["systemd"]), "PM_NGINX_DIR": str(d["nginx"]), "PM_SSHD_DIR": str(d["sshd"]), "PM_SSH_YETKILI": str(yetkili),
           "PM_FAIL2BAN_DIR": str(d["f2b"]), "PM_LOGROTATE_DIR": str(d["logrotate"]), "PM_LE_DIR": str(d["le"]), "PM_WEBROOT": str(d["webroot"]),
           "PM_SYSTEMCTL": str(bin_ / "systemctl"), "PM_SYSTEMCTL_LOG": str(tmp_path / "systemctl.log"), "PM_SSHD": str(bin_ / "sshd"),
           "PM_SSH_KEYGEN": str(bin_ / "ssh-keygen"), "PM_SUNUCU_IP": "203.0.113.10", "PM_DNS_IP": "", "PM_DB": ad,
           "PM_PG": _pg_secenek("postgres"), "PM_PG_PORTMAN": _pg_secenek("portman"), "PM_PG_PORT": _bag().get("port", "5432")}
    yield {"env": env, "d": d, "db": ad, "tmp": tmp_path, "yetkili": yetkili, "log": tmp_path / "systemctl.log"}
    _sql(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")


def _kos(env, **ek):
    return subprocess.run(["bash", str(BETIK)], env={**env, **ek}, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)


def _nginx_beklenen(sertifika: bool) -> str:
    metin = (KOK / "vps" / "nginx" / "portman.conf").read_text(encoding="utf-8")
    if not sertifika:
        metin = re.sub(r"# --443-BASLA--\n.*?# --443-BITIS--\n", "", metin, flags=re.S)
    return metin.replace("__ALAN__", ALAN)


def test_kurulum_kosar_gomulu_dosyalar_ayni_ikinci_kosu_korur(ortam):
    env, d = ortam["env"], ortam["d"]
    r = _kos(env)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-3000:]
    for p in ("surumler", "kaynak", "data/projects", "data/nabiz", "logs"):
        assert (d["kok"] / p).is_dir()
    assert (d["etc"].stat().st_mode & 0o777) == 0o700 and d["webroot"].is_dir()
    # dağıtım anahtarı: yalnız açık anahtar ekranda
    ozel, acik = (d["etc"] / "deploy_key").read_text(), (d["etc"] / "deploy_key.pub").read_text().strip()
    assert (d["etc"] / "deploy_key").stat().st_mode & 0o777 == 0o600 and acik in out and ozel.strip() not in out
    # settings.json kanal/ayarlar.py varsayılanıyla aynı; alan dosyası
    assert json.loads((d["kok"] / "data" / "settings.json").read_text(encoding="utf-8")) == AY.VARSAYILAN
    assert (d["etc"] / "alan").read_text().strip() == ALAN
    # panel.env: oturum anahtarı var, 600, ekranda yok; llm.env ve whatsapp.env boş ve 600
    satir = [s for s in (d["etc"] / "panel.env").read_text().splitlines() if s.startswith("PANEL_SIR=")]
    assert len(satir) == 1 and re.fullmatch(r"PANEL_SIR=[0-9a-f]{64}", satir[0]) and satir[0][10:] not in out
    for f in ("panel.env", "llm.env", "whatsapp.env"):
        assert (d["etc"] / f).stat().st_mode & 0o777 == 0o600
    # gömülü dosyalar depodaki kopyalarla birebir
    for p in sorted((KOK / "vps" / "systemd").iterdir()):
        assert (d["systemd"] / p.name).read_bytes() == p.read_bytes(), p.name
    assert (d["f2b"] / "portman.local").read_bytes() == (KOK / "vps" / "fail2ban" / "portman.local").read_bytes()
    assert (d["logrotate"] / "portman").read_bytes() == (KOK / "vps" / "logrotate" / "portman").read_bytes()
    assert (d["sshd"] / "00-portman.conf").read_bytes() == (KOK / "vps" / "sshd" / "00-portman.conf").read_bytes()
    assert (d["nginx"] / "sites-available" / "portman.conf").read_text(encoding="utf-8") == _nginx_beklenen(False)
    assert (d["nginx"] / "sites-enabled" / "portman.conf").is_symlink()
    assert "alan adı henüz bu sunucuya bakmıyor" in out and "443 kapalı" in out and "passwordauthentication no" in out
    assert "sshd drop-in yazıldı" in out and "'" + ortam["db"] + "' oluşturuldu" in out
    log = ortam["log"].read_text()
    assert "daemon-reload" in log and "enable portman-webhook portman-agent portman-gonderici portman-panel portman-yedek.timer portman-nabiz.timer" in log
    assert _sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s", ortam["db"]) == [("portman",)]
    assert (d["le"] / "renewal-hooks" / "deploy" / "portman-nginx.sh").stat().st_mode & 0o111
    # ikinci koşu: aynı anahtar, aynı oturum anahtarı, veritabanına dokunmaz
    r2 = _kos(env)
    out2 = r2.stdout + r2.stderr
    assert r2.returncode == 0, out2[-3000:]
    assert (d["etc"] / "deploy_key").read_text() == ozel and (d["etc"] / "panel.env").read_text().count("PANEL_SIR=") == 1
    assert satir[0] in (d["etc"] / "panel.env").read_text() and satir[0][10:] not in out2
    assert "var olan anahtar korundu" in out2 and "panel oturum anahtarı var; korundu" in out2 and "sshd drop-in zaten yerinde" in out2
    assert "zaten var, sahibi portman" in out2 and "settings.json var; korundu" in out2


def test_sertifika_ve_dns_karari(ortam):
    env, d = ortam["env"], ortam["d"]
    # DNS sunucuya bakıyor, sertifika yok → certbot koşulur (PM_TEST: atlanır); e-posta şart
    r = _kos(env, PM_DNS_IP="203.0.113.10", PM_EPOSTA="")
    assert r.returncode == 1 and "PM_EPOSTA gerekli" in r.stderr
    r = _kos(env, PM_DNS_IP="203.0.113.10")
    assert r.returncode == 0 and "sertifika alınıyor" in r.stdout and "PM_TEST: certbot atlandı" in r.stdout
    assert "listen 443" not in (d["nginx"] / "sites-available" / "portman.conf").read_text()
    # sertifika dosyası varsa 443 bloğu yazılır
    (d["le"] / "live" / ALAN).mkdir(parents=True)
    (d["le"] / "live" / ALAN / "fullchain.pem").write_text("sahte\n")
    r = _kos(env)
    assert r.returncode == 0 and "443 açık: yalnız /webhook, /saglik, /panel/" in r.stdout
    assert (d["nginx"] / "sites-available" / "portman.conf").read_text(encoding="utf-8") == _nginx_beklenen(True)


def test_yetkili_anahtar_yoksa_sshd_dokunulmaz_bozuk_sozdizimi_geri_alinir(ortam):
    env, d = ortam["env"], ortam["d"]
    ortam["yetkili"].write_text("")
    r = _kos(env)
    assert r.returncode == 0 and "parolalı giriş KAPATILMADI" in r.stdout and not (d["sshd"] / "00-portman.conf").exists()
    ortam["yetkili"].write_text("ssh-ed25519 AAAAdeneme deneme@mac\n")
    r = _kos(env, PM_SSHD_BOZUK="1")
    assert r.returncode == 1 and "drop-in geri alındı" in r.stderr and not (d["sshd"] / "00-portman.conf").exists()
    r = _kos(env)
    assert r.returncode == 0 and (d["sshd"] / "00-portman.conf").exists()


def test_alan_gerekli_hicbir_sey_olusturmaz(ortam):
    env, d = ortam["env"], ortam["d"]
    for kotu in ("", "Portman.Ornek", "-x.y", "a b"):
        r = _kos(env, PM_ALAN=kotu)
        assert r.returncode == 1 and "PM_ALAN gerekli" in r.stderr
    assert not d["kok"].exists() and not d["etc"].exists()
    assert _sql("SELECT count(*) FROM pg_database WHERE datname = %s", ortam["db"]) == [(0,)]


def test_sahibi_baskasi_olan_veritabanina_dokunmaz_durur(ortam):
    env, d = ortam["env"], ortam["d"]
    _sql(f"CREATE DATABASE {ortam['db']}")                        # sahibi postgres
    r = _kos(env)
    assert r.returncode == 1 and "sahibi 'postgres'" in r.stderr
    assert _sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s", ortam["db"]) == [("postgres",)]
    assert not (d["nginx"] / "sites-available" / "portman.conf").exists()      # Postgres adımı nginx'ten önce; sonrası yazılmadı


def _islev(islev: str, arg: str) -> int:
    kod = f'PM_YALNIZ_ISLEVLER=1; PM_PG_PORT=5432; . "{BETIK}"; {islev} "$1"'
    return subprocess.run(["bash", "-c", kod, "_", arg]).returncode


@pytest.mark.parametrize("deger, yerel", [("localhost", True), ("127.0.0.1", True), ("::1", True), ("localhost, 127.0.0.1", True),
                                          ("", True), ("*", False), ("0.0.0.0", False), ("localhost,10.0.0.5", False), ("203.0.113.10", False)])
def test_yerel_dinleme(deger, yerel):
    assert (_islev("yerel_dinleme", deger) == 0) is yerel


@pytest.mark.parametrize("deger, yerel", [("127.0.0.1\n::1", True), ("", True), ("samehost", True),
                                          ("127.0.0.1\n0.0.0.0", False), ("all", False), ("10.0.0.0", False)])
def test_yerel_hba(deger, yerel):
    assert (_islev("yerel_hba", deger) == 0) is yerel


@pytest.mark.parametrize("deger, yerel", [("127.0.0.1:5432\n[::1]:5432", True), ("", True), ("0.0.0.0:5432", False),
                                          ("*:5432", False), ("[::]:5432", False), ("203.0.113.10:5432", False)])
def test_yerel_soketler(deger, yerel):
    assert (_islev("yerel_soketler", deger) == 0) is yerel


# ───────── uçtan uca "durur" sınaması: ayrı, geçici bir Postgres kümesi (yerel olmayan yapılandırmayla) ─────────
_PGBIN = Path("/usr/lib/postgresql/16/bin")


def _kume(listen: str, hba_ek: str = ""):
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
    return port, lambda: (su(f"{_PGBIN}/pg_ctl -D {d} -m immediate stop"), shutil.rmtree(d, ignore_errors=True))


@pytest.mark.parametrize("listen, hba_ek, beklenen", [("*", "", "listen_addresses='*' yerel değil"),
                                                      ("127.0.0.1", "host all all 0.0.0.0/0 trust", "pg_hba.conf yerel olmayan")])
def test_yerel_olmayan_yapilandirmada_durur_hicbir_sey_olusturmaz(ortam, listen, hba_ek, beklenen):
    port, kapat = _kume(listen, hba_ek)
    try:
        env = {**ortam["env"], "PM_DB": "portman", "PM_PG": f"-h 127.0.0.1 -p {port} -U postgres", "PM_PG_PORTMAN": f"-h 127.0.0.1 -p {port} -U portman",
               "PM_PG_PORT": str(port)}
        r = _kos(env)
        assert r.returncode == 1 and beklenen in r.stderr, r.stdout[-500:] + r.stderr[-500:]
        with psycopg.connect(f"host=127.0.0.1 port={port} user=postgres dbname=postgres") as c:
            assert c.execute("SELECT count(*) FROM pg_roles WHERE rolname = 'portman'").fetchone()[0] == 0
            assert c.execute("SELECT count(*) FROM pg_database WHERE datname LIKE 'portman%%'").fetchone()[0] == 0
        assert not (ortam["d"]["nginx"] / "sites-available").exists() and not (ortam["d"]["systemd"]).exists()
    finally:
        kapat()
