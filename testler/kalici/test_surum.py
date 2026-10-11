"""İE-06 · sürüm ve bakım betikleri sahte dizinlerde (ağ, canlı, LLM, WhatsApp yok):
guncelle.sh (yerel çıplak git deposu, açıklamalı etiket, main denetimi, göçler gerçek Postgres'e, bağlantı değişimi, sağlık 503'te
kendiliğinden geri dönüş), geri_don.sh, surum_temizle.sh (onaysız silmez), sir_koy.py (biçim, atomik yazım, yalnız parmak izi,
ücretsiz doğrulama yerel sahte sunucuya), panel_parola.py (özet kanal/panel.py ile doğrulanır), yedek_kur.sh ve yedek.sh (sahte
rclone/age/pg_dump; belirteç çıktıda yok; nabiz/, checks/ yedeğe girmez), yedek_geri_dene.sh (işaretli deneme veritabanı),
nabiz.sh (+ uyarı), uyari_gonder.py (24 saat penceresi, 6 saat sıklığı), ayar.sh, oz_test.sh, kuru_kosu.sh (imza), arsiv_al.sh, durum.sh."""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from pathlib import Path

import pytest

from conftest import ADMIN, BAYI_A, KOK, NUMARA_A, _admin, dsn, mesaj, sorgu, talep

VPS = KOK / "vps"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@ornek.invalid", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@ornek.invalid"}
NUMARA_P = "900000000909"
BAYI_P = {"kod": "PATRON", "ad": "Patron", "firma": "PortatifEv", "rol": "patron"}


def _kos(betik: str, env: dict, *arg, girdi: str | None = None, zaman: int = 300) -> subprocess.CompletedProcess:
    cmd = (["bash", str(VPS / betik)] if betik.endswith(".sh") else [sys.executable, str(VPS / betik)]) + list(arg)
    return subprocess.run(cmd, env={**os.environ, **env}, input=girdi, capture_output=True, text=True, timeout=zaman,
                          stdin=None if girdi is not None else subprocess.DEVNULL)


def _sahte(bin_: Path, ad: str, icerik: str) -> str:
    p = bin_ / ad; p.write_text(icerik); p.chmod(0o755); return str(p)


class _SahteSunucu:
    """Yerel HTTP sunucusu: istekleri kaydeder, kod ve gövdeyi test belirler."""

    def __init__(self, cevaplar=None, kod=200, uret=None):
        self.istekler = []; self.kod = kod; self.cevaplar = cevaplar or {}; self.uret = uret
        sunucu = self

        class H(http.server.BaseHTTPRequestHandler):
            def _cevapla(self):
                n = int(self.headers.get("Content-Length") or 0)
                govde = self.rfile.read(n) if n else b""
                sunucu.istekler.append({"method": self.command, "path": self.path, "headers": dict(self.headers), "body": govde})
                kod, veri = sunucu.kod, None
                if sunucu.uret is not None:
                    kod, veri = sunucu.uret(self.path)
                for yol, (k, v) in sunucu.cevaplar.items():
                    if self.path.startswith(yol):
                        kod, veri = k, v
                veri = json.dumps(veri if veri is not None else {"ok": kod == 200}).encode()
                self.send_response(kod); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(veri)))
                self.end_headers(); self.wfile.write(veri)

            do_GET = do_POST = _cevapla

            def log_message(self, *a):
                pass

        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def kapat(self):
        self.httpd.shutdown()


# ───────────────────────── sürüm: guncelle.sh, geri_don.sh, surum_temizle.sh ─────────────────────────
@pytest.fixture(scope="module")
def kaynak(tmp_path_factory):
    """Yerel çıplak depo: main'de açıklamalı v2026.10.09 ve (ikinci commit'te) v2026.10.12; hafif v2026.10.10; yan dalda açıklamalı v2026.10.11."""
    tmp = tmp_path_factory.mktemp("git")
    bare = tmp / "kaynak.git"; calisma = tmp / "calisma"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(calisma)], check=True, capture_output=True)
    for d in ("kanal", "beyin", "motor", "is_emri", "vps", "araclar"):
        shutil.copytree(KOK / d, calisma / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "durum", "cikti", "build"))
    (calisma / "SHA256SUMS").write_text("deneme\n")
    shutil.copy(KOK / ".gitattributes", calisma / ".gitattributes")                 # testler/ ve deneme/ export-ignore (Lokman 9.10)
    (calisma / "testler" / "kalici").mkdir(parents=True); (calisma / "testler" / "kalici" / "test_x.py").write_text("# sürüme girmez\n")
    (calisma / "deneme" / "2026-01-01").mkdir(parents=True); (calisma / "deneme" / "2026-01-01" / "x.txt").write_text("sürüme girmez\n")

    def g(*a):
        return subprocess.run(["git", "-C", str(calisma), *a], check=True, capture_output=True, text=True, env={**os.environ, **GIT_ENV})
    g("checkout", "-q", "-B", "main"); g("add", "-A"); g("commit", "-q", "-m", "ilk sürüm")
    g("tag", "-a", "v2026.10.09", "-m", "sürüm 9"); g("tag", "v2026.10.10")
    g("checkout", "-q", "-b", "yan"); (calisma / "YAN").write_text("x\n"); g("add", "-A"); g("commit", "-q", "-m", "yan"); g("tag", "-a", "v2026.10.11", "-m", "yan dal")
    g("checkout", "-q", "main"); (calisma / "IKINCI").write_text("x\n"); g("add", "-A"); g("commit", "-q", "-m", "ikinci"); g("tag", "-a", "v2026.10.12", "-m", "sürüm 12")
    g("push", "-q", "origin", "main", "yan", "--tags")
    return bare


@pytest.fixture
def surum_ortam(tmp_path, kaynak):
    if not ADMIN:
        pytest.skip("PORTMAN_TEST_PG yok")
    ad = "s_" + uuid.uuid4().hex[:10]
    with _admin() as c:
        c.execute(f"CREATE DATABASE {ad}")
    bin_ = tmp_path / "bin"; bin_.mkdir()
    log = tmp_path / "systemctl.log"
    systemctl = _sahte(bin_, "systemctl", '#!/usr/bin/env bash\necho "$@" >> "$PM_SYSTEMCTL_LOG"\n[ "$1" = is-active ] && echo active\nexit 0\n')
    kok = tmp_path / "opt"; (kok / "data" / "nabiz").mkdir(parents=True); etc = tmp_path / "etc"; etc.mkdir()
    saglik = _SahteSunucu(kod=200)
    saglik.bozuk = False                                   # True → postgres: false (sürüm kapısı düşer); kod 503 tek başına düşürmez (nabiz.sh sorunları)
    surum_dosyasi = kok / "guncel" / "SURUM"
    saglik.uret = lambda yol: (saglik.kod, {"ok": saglik.kod == 200, "postgres": not saglik.bozuk,
                                            "surum": surum_dosyasi.read_text().strip() if surum_dosyasi.exists() else None})
    env = {"PM_KOK": str(kok), "PM_ETC": str(etc), "PM_GIT_URL": str(kaynak), "PM_PYTHON": sys.executable, "PM_VENV_ATLA": "1", "PM_SYSTEMCTL": systemctl,
           "PM_SYSTEMCTL_LOG": str(log), "PM_OLARAK": "", "PM_PG_DSN": dsn(ad), "PM_SAGLIK_URL": saglik.url + "/saglik", "PM_SAGLIK_BEKLE": "4", "PM_TEST": "1"}
    yield {"env": env, "kok": kok, "log": log, "saglik": saglik, "db": ad}
    saglik.kapat()
    with _admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")


def test_guncelle_ikinci_surum_ve_geri_don(surum_ortam):
    env, kok, log = surum_ortam["env"], surum_ortam["kok"], surum_ortam["log"]
    r = _kos("guncelle.sh", env, "v2026.10.09")
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-3000:]
    s9 = kok / "surumler" / "v2026.10.09"
    assert (s9 / "SURUM").read_text().strip() == "v2026.10.09" and (s9 / "KURULDU").exists() and not (s9 / ".git").exists()
    assert (s9 / "venv" / "bin" / "python").exists() and (s9 / "kanal" / "webhook.py").exists() and not (kok / "kaynak" / "kanal").exists()
    # .gitattributes export-ignore: testler/ ve deneme/ sürüm ağacında yok; beyin/testler/ (öz-testin okuduğu harness vakaları) var
    assert not (s9 / "testler").exists() and not (s9 / "deneme").exists()
    assert (s9 / "beyin" / "testler" / "mesajlar.json").exists() and list((s9 / "beyin" / "testler").glob("cikarim_*.json"))
    assert os.readlink(kok / "guncel") == str(s9) and not (kok / "onceki").exists()
    assert "içe aktarma tamam" in out and "uygulanan göçler: [1, 2, 3, 4, 5]" in out and "sağlık: sürüm v2026.10.09, Postgres bağlı" in out and "etkin" in out
    assert "stop portman-webhook portman-gonderici portman-agent portman-panel" in log.read_text() and "start portman-webhook" in log.read_text()
    assert sorgu(__import__("depo").Depo(dsn(surum_ortam["db"])), "SELECT max(surum) AS s FROM sema_surumu")[0]["s"] == 5
    assert surum_ortam["saglik"].istekler and surum_ortam["saglik"].istekler[0]["path"] == "/saglik"
    # ikinci sürüm: onceki ← 09, guncel ← 12; göç yok. /saglik 503 (nabiz.sh'de duran bir sorun) ama sürüm ve Postgres doğru → kapı geçer
    surum_ortam["saglik"].kod = 503
    r = _kos("guncelle.sh", env, "v2026.10.12")
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-3000:]
    surum_ortam["saglik"].kod = 200
    s12 = kok / "surumler" / "v2026.10.12"
    assert os.readlink(kok / "guncel") == str(s12) and os.readlink(kok / "onceki") == str(s9) and (s12 / "IKINCI").exists()
    assert "uygulanan göçler: yok (güncel)" in out
    # geri dönüş ve yeniden ileri
    r = _kos("geri_don.sh", env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert os.readlink(kok / "guncel") == str(s9) and os.readlink(kok / "onceki") == str(s12) and "v2026.10.12 → v2026.10.09" in r.stdout
    r = _kos("geri_don.sh", env)
    assert r.returncode == 0 and os.readlink(kok / "guncel") == str(s12)
    # aynı etiket yeniden: dosyalar yeniden açılmaz
    r = _kos("guncelle.sh", env, "v2026.10.12")
    assert r.returncode == 0 and "sürüm zaten kurulu" in r.stdout and os.readlink(kok / "guncel") == str(s12)


def test_etiket_denetimleri_hicbir_sey_kurmaz(surum_ortam):
    env, kok = surum_ortam["env"], surum_ortam["kok"]
    for etiket, beklenen in (("v2026.10.10", "açıklamalı (annotated) değil"), ("v2026.10.11", "origin/main üzerinde değil"),
                             ("v1", "etiket biçimi"), ("v2026.10.30", "etiket yok"), ("", "etiket biçimi")):
        r = _kos("guncelle.sh", env, *([etiket] if etiket else []))
        assert r.returncode == 1 and beklenen in r.stderr, (etiket, r.stdout[-400:], r.stderr[-400:])
    assert not list((kok / "surumler").glob("*")) and not (kok / "guncel").exists()


def test_saglik_dusunce_kendiliginden_geri_doner(surum_ortam):
    env, kok, saglik = surum_ortam["env"], surum_ortam["kok"], surum_ortam["saglik"]
    assert _kos("guncelle.sh", env, "v2026.10.09").returncode == 0
    saglik.bozuk = True                                     # postgres: false → yeni sürüm sağlıklı sayılmaz
    r = _kos("guncelle.sh", env, "v2026.10.12")
    out = r.stdout + r.stderr
    assert r.returncode == 1 and "Önceki sürüme dönülüyor" in out and "DUR: sağlık" in out and '"postgres": false' in out
    assert os.readlink(kok / "guncel") == str(kok / "surumler" / "v2026.10.09") and os.readlink(kok / "onceki") == str(kok / "surumler" / "v2026.10.12")
    assert (kok / "surumler" / "v2026.10.12" / "KURULDU").exists()                 # dizin durur, silinmez


def test_ilk_kurulumda_saglik_dusunce_onceki_yok(surum_ortam):
    env, kok, saglik = surum_ortam["env"], surum_ortam["kok"], surum_ortam["saglik"]
    saglik.bozuk = True
    r = _kos("guncelle.sh", env, "v2026.10.09")
    assert r.returncode == 1 and "önceki sürüm yok (ilk kurulum)" in r.stderr and os.readlink(kok / "guncel") == str(kok / "surumler" / "v2026.10.09")
    r = _kos("geri_don.sh", env)
    assert r.returncode == 1 and "önceki sürüm yok" in r.stderr


def test_surum_temizle_onaysiz_silmez(tmp_path):
    kok = tmp_path / "opt"; s = kok / "surumler"; s.mkdir(parents=True)
    t = time.time()
    for i, ad in enumerate(("v2026.10.01", "v2026.10.02", "v2026.10.03", "v2026.10.04", "v2026.10.05")):
        (s / ad).mkdir(); (s / ad / "SURUM").write_text(ad); os.utime(s / ad, (t - 1000 + i * 100, t - 1000 + i * 100))
    os.symlink(s / "v2026.10.05", kok / "guncel"); os.symlink(s / "v2026.10.01", kok / "onceki")
    (s / ".yarim-v2026.10.06-x").mkdir()                       # yarım kalmış dizin: "en yeni 3" sayımına girmez, her zaman aday
    env = {"PM_KOK": str(kok)}
    r = _kos("surum_temizle.sh", env)
    assert r.returncode == 0 and "silinecek: v2026.10.02" in r.stdout and "silinecek: .yarim-v2026.10.06-x" in r.stdout and "PM_ONAY=evet verilmedi" in r.stdout
    assert all((s / f"v2026.10.0{i}").exists() for i in range(1, 6)) and (s / ".yarim-v2026.10.06-x").exists()
    r = _kos("surum_temizle.sh", {**env, "PM_ONAY": "evet"})
    assert r.returncode == 0 and "silindi: v2026.10.02" in r.stdout
    assert not (s / "v2026.10.02").exists() and not (s / ".yarim-v2026.10.06-x").exists() and all((s / f"v2026.10.0{i}").exists() for i in (1, 3, 4, 5))


# ───────────────────────── sırlar: sir_koy.py, panel_parola.py ─────────────────────────
def test_sir_koy_bicim_atomik_yazim_parmak_izi_dogrulama(tmp_path):
    etc = tmp_path / "etc"; etc.mkdir()
    (etc / "llm.env").write_text("BASKA=1\n")
    claude = _SahteSunucu(cevaplar={"/v1/models": (200, {"data": [{"id": "claude-opus-5-5-20260301"}, {"id": "claude-haiku-4-5"}]})})
    graph = _SahteSunucu(cevaplar={"/v23.0/106000000000001": (200, {"display_phone_number": "1 555 0100", "verified_name": "Deneme", "quality_rating": "GREEN"})})
    env = {"PM_ETC": str(etc), "PM_ANTHROPIC_BASE": claude.url + "/v1", "PM_GRAPH_BASE": graph.url + "/v23.0"}
    try:
        anahtar = "sk-ant-" + "a" * 40
        r = _kos("sir_koy.py", env, "anthropic", girdi=anahtar + "\n")
        assert r.returncode == 0, r.stdout + r.stderr
        assert (etc / "llm.env").read_text() == f"BASKA=1\nANTHROPIC_API_KEY={anahtar}\n" and (etc / "llm.env").stat().st_mode & 0o777 == 0o600
        assert "parmak izi " + hashlib.sha256(anahtar.encode()).hexdigest()[:12] in r.stdout and "HTTP 200" in r.stdout and "erişilebilir: evet" in r.stdout
        assert anahtar not in r.stdout + r.stderr
        assert {k.lower(): v for k, v in claude.istekler[0]["headers"].items()}.get("x-api-key") == anahtar
        # biçim denetimi: dosyaya dokunulmaz
        r = _kos("sir_koy.py", env, "wa_secret", girdi="kisa\n")
        assert r.returncode == 1 and "biçimine uymuyor" in r.stderr and not (etc / "whatsapp.env").exists()
        assert _kos("sir_koy.py", env, "bilinmeyen", girdi="x").returncode == 2
        # whatsapp.env: pnid önce (token yok → doğrulama atlanır), sonra token (GET /<pnid>), secret ve verify
        r = _kos("sir_koy.py", env, "wa_pnid", girdi="106000000000001\n")
        assert r.returncode == 0 and "doğrulama atlandı: wa_token" in r.stdout
        belirtec = "A" * 60
        r = _kos("sir_koy.py", env, "wa_token", girdi=belirtec + "\n")
        assert r.returncode == 0 and "HTTP 200" in r.stdout and belirtec not in r.stdout and "…01" in r.stdout
        assert {k.lower(): v for k, v in graph.istekler[0]["headers"].items()}.get("authorization") == "Bearer " + belirtec and "106000000000001" not in r.stdout
        sir = "0123456789abcdef" * 2
        assert _kos("sir_koy.py", env, "wa_secret", girdi=sir).returncode == 0
        assert _kos("sir_koy.py", {**env, "PM_DOGRULAMA": "0"}, "wa_verify", girdi="dogrulama-belirteci-123456").stdout.count("doğrulama atlandı (PM_DOGRULAMA=0)") == 1
        satirlar = (etc / "whatsapp.env").read_text().splitlines()
        assert sorted(s.split("=")[0] for s in satirlar) == ["WA_ACCESS_TOKEN", "WA_APP_SECRET", "WA_GRAPH_VERSION", "WA_PHONE_NUMBER_ID", "WA_VERIFY_TOKEN"]
        assert f"WA_APP_SECRET={sir}" in satirlar and "WA_GRAPH_VERSION=v23.0" in satirlar and (etc / "whatsapp.env").stat().st_mode & 0o777 == 0o600
        # aynı adı yeniden yazmak satırı değiştirir, çoğaltmaz
        _kos("sir_koy.py", env, "wa_token", girdi="B" * 60)
        assert (etc / "whatsapp.env").read_text().count("WA_ACCESS_TOKEN=") == 1 and "WA_ACCESS_TOKEN=" + "B" * 60 in (etc / "whatsapp.env").read_text()
    finally:
        claude.kapat(); graph.kapat()


def test_panel_parola_ozeti_panel_ile_dogrulanir(tmp_path):
    import panel as PN
    etc = tmp_path / "etc"
    env = {"PM_ETC": str(etc)}
    r = _kos("panel_parola.py", env, girdi="kisa\n")
    assert r.returncode == 1 and "en az 12 karakter" in r.stderr and not (etc / "panel.env").exists()
    deger = "deneme-" + "k" * 14
    r = _kos("panel_parola.py", env, girdi=deger + "\n")
    assert r.returncode == 0, r.stderr
    satirlar = dict(s.split("=", 1) for s in (etc / "panel.env").read_text().splitlines())
    assert set(satirlar) == {"PANEL_SIR", "PANEL_PAROLA"} and len(satirlar["PANEL_SIR"]) == 64 and "PANEL_SIR yoktu, üretildi" in r.stdout
    assert PN.parola_dogru(deger, satirlar["PANEL_PAROLA"]) and not PN.parola_dogru(deger + "x", satirlar["PANEL_PAROLA"])
    assert deger not in r.stdout and (etc / "panel.env").stat().st_mode & 0o777 == 0o600
    r = _kos("panel_parola.py", env, girdi="ikinci-" + "p" * 12)
    yeni = dict(s.split("=", 1) for s in (etc / "panel.env").read_text().splitlines())
    assert yeni["PANEL_SIR"] == satirlar["PANEL_SIR"] and yeni["PANEL_PAROLA"] != satirlar["PANEL_PAROLA"] and "PANEL_SIR korundu" in r.stdout


# ───────────────────────── yedek: yedek_kur.sh, yedek.sh, yedek_geri_dene.sh ─────────────────────────
SAHTE_RCLONE = '#!/usr/bin/env bash\necho "$@" >> "$PM_RCLONE_LOG"\nexit 0\n'
SAHTE_AGE = """#!/usr/bin/env bash
# sahte age: -r <alıcı> -o <çıktı>; girdiyi olduğu gibi yazar (şifreleme yok; yalnız akış sınanır)
while [ $# -gt 0 ]; do case "$1" in -o) OUT="$2"; shift ;; -r) echo "$2" >> "$PM_AGE_LOG"; shift ;; esac; shift; done
cat > "$OUT"
"""
SAHTE_PG_DUMP = '#!/usr/bin/env bash\necho "$@" >> "$PM_PG_DUMP_LOG"\nprintf "PGDMP sahte dump %s" "$(date +%s%N)"\n'


def test_yedek_kur_age_ve_drive_belirtec_ekrana_cikmaz(tmp_path):
    etc = tmp_path / "etc"
    env = {"PM_ETC": str(etc), "PM_TEST": "1"}
    r = _kos("yedek_kur.sh", env, "age", girdi="age1kisa\n")
    assert r.returncode == 1 and "age açık anahtarına benzemiyor" in r.stderr and not (etc / "yedek.pub").exists()
    acik = "age1" + "q" * 58
    r = _kos("yedek_kur.sh", env, "age", girdi="Public key: \n" + acik + "\n")
    assert r.returncode == 0 and (etc / "yedek.pub").read_text() == acik + "\n" and (etc / "yedek.pub").stat().st_mode & 0o777 == 0o600
    r = _kos("yedek_kur.sh", env, "drive", girdi='{"access_token": "x"}')
    assert r.returncode == 1 and "rclone authorize" in r.stderr and not (etc / "rclone.conf").exists()
    belirtec = {"access_token": "ya29." + "t" * 40, "token_type": "Bearer", "refresh_token": "1//" + "r" * 30, "expiry": "2026-10-09T00:00:00Z"}
    r = _kos("yedek_kur.sh", env, "drive", girdi="Paste the following into your remote machine --->\n" + json.dumps(belirtec) + "\n<---End paste")
    assert r.returncode == 0, r.stderr
    conf = (etc / "rclone.conf").read_text()
    assert conf.startswith("[portman-drive]\ntype = drive\nscope = drive.file\ntoken = {") and belirtec["refresh_token"] in conf
    assert (etc / "rclone.conf").stat().st_mode & 0o777 == 0o600 and belirtec["access_token"] not in r.stdout and belirtec["refresh_token"] not in r.stdout
    assert _kos("yedek_kur.sh", env, "baska").returncode == 1


def test_yedek_sh_sahte_araclarla(tmp_path):
    bin_ = tmp_path / "bin"; bin_.mkdir()
    kok = tmp_path / "opt"; etc = tmp_path / "etc"; yedek = tmp_path / "yedek"; etc.mkdir()
    (kok / "data" / "nabiz").mkdir(parents=True); (kok / "data" / "checks").mkdir(); (kok / "data" / "projects").mkdir()
    (kok / "data" / "settings.json").write_text("{}"); (kok / "data" / "nabiz" / "agent.json").write_text("{}"); (kok / "data" / "checks" / "x").write_text("x")
    (kok / "data" / "projects" / "p.pdf").write_bytes(b"%PDF")
    env = {"PM_KOK": str(kok), "PM_ETC": str(etc), "PM_YEDEK_DIR": str(yedek), "PM_DB": "deneme_db", "PM_RCLONE_LOG": str(tmp_path / "rclone.log"),
           "PM_AGE_LOG": str(tmp_path / "age.log"), "PM_PG_DUMP_LOG": str(tmp_path / "pgdump.log"), "PM_RCLONE": _sahte(bin_, "rclone", SAHTE_RCLONE),
           "PM_AGE": _sahte(bin_, "age", SAHTE_AGE), "PM_PG_DUMP": _sahte(bin_, "pg_dump", SAHTE_PG_DUMP)}
    r = _kos("yedek.sh", env)
    assert r.returncode == 0 and "yedek yapılandırılmadı" in r.stdout and not yedek.exists()
    (etc / "yedek.pub").write_text("age1" + "q" * 58 + "\n"); (etc / "rclone.conf").write_text("[portman-drive]\ntype = drive\n")
    dosyalar = []
    for i in range(4):
        r = _kos("yedek.sh", env)
        assert r.returncode == 0, r.stdout + r.stderr
        dosyalar = sorted(yedek.glob("portman-*.tar.age"))
        time.sleep(1.1)
    assert len(dosyalar) == 3 and all(p.stat().st_mode & 0o777 == 0o600 for p in dosyalar)
    with tarfile.open(dosyalar[-1]) as dis:
        assert sorted(dis.getnames()) == ["data.tar", "portman.dump"]
        with tarfile.open(fileobj=dis.extractfile("data.tar")) as ic:
            adlar = ic.getnames()
    assert "data/settings.json" in adlar and "data/projects/p.pdf" in adlar and not any("nabiz" in a or "checks" in a for a in adlar)
    log = (tmp_path / "rclone.log").read_text()
    assert f"--config {etc}/rclone.conf copy {dosyalar[-1]} portman-drive:Portman-Yedek/" in log
    assert "delete --min-age 30d --include portman-*.tar.age portman-drive:Portman-Yedek/" in log
    assert (tmp_path / "age.log").read_text().splitlines()[0] == "age1" + "q" * 58 and "-Fc -d deneme_db" in (tmp_path / "pgdump.log").read_text()
    nb = json.loads((kok / "data" / "nabiz" / "yedek.json").read_text())
    assert nb["ad"] == "yedek" and nb["dosya"] == dosyalar[-1].name and nb["boyut"] == dosyalar[-1].stat().st_size and "parola" not in r.stdout.lower()
    assert not list(yedek.glob(".gecici*"))


@pytest.mark.skipif(not ADMIN, reason="PORTMAN_TEST_PG yok")
def test_yedek_geri_dene_isaretli_deneme_veritabani(depo, tmp_path):
    b = dict(p.split("=", 1) for p in ADMIN.split())
    pg = f"-h {b.get('host', '127.0.0.1')} -p {b.get('port', '5432')} -U {b.get('user', 'postgres')}"
    depo.bayi_yaz(NUMARA_A, ad=BAYI_A["ad"], kod=BAYI_A["kod"], rol="bayi")
    dump = tmp_path / "portman.dump"
    subprocess.run(["pg_dump", *pg.split(), "-Fc", "-d", depo.ad, "-f", str(dump)], check=True)
    env = {"PM_PG": pg, "PM_DB": depo.ad, "PM_CALISMA": "sinama_" + uuid.uuid4().hex[:6]}
    try:
        r = _kos("yedek_geri_dene.sh", env, str(dump))
        assert r.returncode == 0, r.stdout + r.stderr
        assert "tablo kümesi: AYNI" in r.stdout and "bayiler" in r.stdout and "deneme veritabanı silindi" in r.stdout and "satır sayısı farkı olan tablo: 0" in r.stdout
        assert NUMARA_A not in r.stdout
        with _admin() as c:
            assert c.execute("SELECT count(*) FROM pg_database WHERE datname = %s", ("portman_geri_deneme_" + env["PM_CALISMA"],)).fetchone()[0] == 0
            c.execute("CREATE DATABASE portman_geri_deneme_" + env["PM_CALISMA"])
        r = _kos("yedek_geri_dene.sh", env, str(dump))
        assert r.returncode == 1 and "zaten var; dokunulmadı" in r.stderr
        assert _kos("yedek_geri_dene.sh", env, str(tmp_path / "yok.dump")).returncode == 1
    finally:
        with _admin() as c:
            c.execute("DROP DATABASE IF EXISTS portman_geri_deneme_" + env["PM_CALISMA"] + " WITH (FORCE)")


# ───────────────────────── nabız ve uyarı ─────────────────────────
def _sertifika(yol: Path, gun: int) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(yol.parent / "privkey.pem"), "-out", str(yol),
                    "-days", str(gun), "-subj", "/CN=portman.ornek.invalid"], check=True, capture_output=True)


def test_nabiz_sorunlari_toplar_ve_uyarir(tmp_path):
    bin_ = tmp_path / "bin"; bin_.mkdir()
    kok = tmp_path / "opt"; etc = tmp_path / "etc"; le = tmp_path / "le"; etc.mkdir(); (kok / "data" / "nabiz").mkdir(parents=True)
    (kok / "data" / "settings.json").write_text('{"enabled": false}')
    (etc / "alan").write_text("portman.ornek.invalid\n")
    systemctl = _sahte(bin_, "systemctl", '#!/usr/bin/env bash\nif [ "$1" = is-active ]; then [ "$2" = "$PM_INAKTIF" ] && echo inactive || echo active; fi\nexit 0\n')
    psql = _sahte(bin_, "psql", '#!/usr/bin/env bash\nexit "${PM_PSQL_RC:-0}"\n')
    uyari = _sahte(bin_, "uyari", '#!/usr/bin/env bash\nprintf "%s\\n%s\\n" "$1" "$2" >> "$PM_UYARI_LOG"\necho "uyarı: gonderildi"\n')
    env = {"PM_KOK": str(kok), "PM_ETC": str(etc), "PM_SYSTEMCTL": systemctl, "PM_PSQL": psql, "PM_LE_DIR": str(le), "PM_UYARI": uyari,
           "PM_UYARI_LOG": str(tmp_path / "uyari.log"), "PM_INAKTIF": "", "PM_DISK_ESIK": "101", "PM_OLARAK": ""}
    _sertifika(le / "live" / "portman.ornek.invalid" / "fullchain.pem", 90)
    r = _kos("nabiz.sh", env)
    assert r.returncode == 0 and "sorun yok" in r.stdout and not (tmp_path / "uyari.log").exists()
    assert json.loads((kok / "data" / "nabiz" / "nabiz.json").read_text())["sorunlar"] == []
    # sertifika 10 gün, ajan düşük, Postgres yok, yedek kurulu ama hiç alınmamış, kanal açıkken nabız yok
    _sertifika(le / "live" / "portman.ornek.invalid" / "fullchain.pem", 10)
    (kok / "data" / "settings.json").write_text('{"enabled": true}')
    (etc / "yedek.pub").write_text("age1x\n"); (etc / "rclone.conf").write_text("x\n")
    (kok / "data" / "nabiz" / "gonderici.json").write_text(json.dumps({"zaman": int(time.time()) - 1000}))
    r = _kos("nabiz.sh", {**env, "PM_INAKTIF": "portman-agent", "PM_PSQL_RC": "2"})
    assert r.returncode == 0
    sorunlar = json.loads((kok / "data" / "nabiz" / "nabiz.json").read_text())["sorunlar"]
    assert "portman-agent: inactive" in sorunlar and "postgres: bağlanılamadı" in sorunlar and "yedek: hiç alınmadı" in sorunlar and "agent: nabız yok" in sorunlar
    assert any(s.startswith("sertifika: ") and "gün kaldı" in s for s in sorunlar) and any(s.startswith("gonderici: nabız") and "sn eski" in s for s in sorunlar)
    metin, anahtar = (tmp_path / "uyari.log").read_text().splitlines()[:2]
    assert metin.startswith("Portman uyarı") and "portman-agent: inactive" in metin and "sorun" in r.stdout
    assert anahtar == "agent;gonderici;portman-agent;postgres;sertifika;yedek;"       # sıklık anahtarı: yalnız sorun adları, sıralı
    # yedek yeni, nabızlar taze, sertifika uzun → sorun yok
    _sertifika(le / "live" / "portman.ornek.invalid" / "fullchain.pem", 90)
    for ad in ("agent", "gonderici", "yedek"):
        (kok / "data" / "nabiz" / f"{ad}.json").write_text(json.dumps({"zaman": int(time.time())}))
    r = _kos("nabiz.sh", env)
    assert "sorun yok" in r.stdout and json.loads((kok / "data" / "nabiz" / "nabiz.json").read_text())["sorunlar"] == []


@pytest.mark.skipif(not ADMIN, reason="PORTMAN_TEST_PG yok")
def test_uyari_gonder_pencere_ve_siklik(depo, kanal_dizini):
    sys.path.insert(0, str(VPS))
    import uyari_gonder as UG
    import meta_api as M
    from sahte_meta import SahteMeta
    meta = SahteMeta(); istemci = M.GraphIstemci(M.MetaAyar(phone_number_id="106000000000001", access_token="t" * 40, app_secret="s" * 20, verify_token="v"), http=meta)
    assert UG.uyari(depo, istemci, kanal_dizini, "deneme uyarısı") == "patron yok"
    depo.bayi_yaz(NUMARA_P, ad="Patron", rol="patron")
    assert UG.uyari(depo, istemci, kanal_dizini, "deneme uyarısı") == "pencere kapali"                 # hiç mesaj yok
    g = mesaj("merhaba", talep(), numara=NUMARA_P, bayi=BAYI_P, ts=time.time() - 25 * 3600); g["role"] = "patron"
    assert depo.mesaj_kaydet(g)
    assert UG.uyari(depo, istemci, kanal_dizini, "deneme uyarısı") == "pencere kapali"                 # 25 saat önce
    g = mesaj("merhaba", talep(), numara=NUMARA_P, bayi=BAYI_P, ts=time.time() - 3600); g["role"] = "patron"
    assert depo.mesaj_kaydet(g)
    assert UG.uyari(depo, istemci, kanal_dizini, "deneme uyarısı") == "gonderildi"
    assert meta.gidenler()[-1]["to"] == NUMARA_P and meta.gidenler()[-1]["text"]["body"] == "deneme uyarısı"
    assert UG.uyari(depo, istemci, kanal_dizini, "deneme uyarısı") == "yakin zamanda gonderildi" and len(meta.gidenler()) == 1
    assert UG.uyari(depo, istemci, kanal_dizini, "başka uyarı") == "gonderildi" and len(meta.gidenler()) == 2
    assert UG.uyari(depo, istemci, kanal_dizini, "deneme uyarısı", simdi=time.time() + 7 * 3600) == "gonderildi"
    assert NUMARA_P not in (kanal_dizini / "nabiz" / "uyari_son.json").read_text()
    # sıklık anahtarı verilince metin değişse de (zaman damgası, sayılar) aynı sorun 6 saat içinde yeniden gitmez
    assert UG.uyari(depo, istemci, kanal_dizini, "Portman uyarı (09.10 19:20): sertifika: 9 gün kaldı", anahtar="sertifika;") == "gonderildi"
    assert UG.uyari(depo, istemci, kanal_dizini, "Portman uyarı (09.10 19:25): sertifika: 8 gün kaldı", anahtar="sertifika;") == "yakin zamanda gonderildi"
    assert UG.uyari(depo, istemci, kanal_dizini, "Portman uyarı (09.10 19:30): disk: %91 dolu", anahtar="disk;") == "gonderildi"


# ───────────────────────── ayar.sh, oz_test.sh, kuru_kosu.sh, arsiv_al.sh, durum.sh ─────────────────────────
def test_ayar_sh_ve_ayarlar_komut_satiri(tmp_path):
    data = tmp_path / "data"; data.mkdir()
    env = {"PM_KOK": str(tmp_path / "yok"), "PM_DATA": str(data), "PM_PYTHON": sys.executable}
    r = _kos("ayar.sh", env, "enabled", "true")
    assert r.returncode == 0 and "yazıldı: enabled = true (enabled_at = şimdi)" in r.stdout
    a = json.loads((data / "settings.json").read_text())
    assert a["enabled"] is True and a["enabled_at"] >= int(time.time()) - 5
    assert _kos("ayar.sh", env, "dry_run", "false").returncode == 0 and json.loads((data / "settings.json").read_text())["dry_run"] is False
    assert _kos("ayar.sh", env, "llm.model", '"claude-opus-5-5"').returncode == 0
    assert _kos("ayar.sh", env, "kayitsiz_cevap", "Merhaba, bu hat kayıtlı bayilere açıktır.").returncode == 0
    for anahtar, deger in (("mode", "kral"), ("dry_run", "belki"), ("bilinmeyen", "1"), ("enabled_at", "x")):
        r = _kos("ayar.sh", env, anahtar, deger)
        assert r.returncode == 1 and "DUR" in r.stderr, (anahtar, deger)
    r = _kos("ayar.sh", env)
    assert r.returncode == 0 and json.loads(r.stdout)["llm"]["model"] == "claude-opus-5-5" and json.loads(r.stdout)["kayitsiz_cevap"].startswith("Merhaba")
    assert _kos("ayar.sh", env, "tek").returncode == 2


def test_oz_test_sh_sonucu_ozetler(tmp_path):
    bin_ = tmp_path / "bin"; bin_.mkdir(); data = tmp_path / "data"; data.mkdir()
    (data / "self-test-result.json").write_text(json.dumps({"state": "passed", "eski": True}))
    yeni = json.dumps({"state": "passed", "surum": "kanal-v2.0", "python": "3.12", "duration_s": 41.2,
                       "adimlar": {"beyin_harness": {"uyumlu": 22, "toplam": 22, "passed": True}, "llm": {"backend": "anthropic", "model": "claude-opus-5-5", "passed": True}}})
    systemctl = _sahte(bin_, "systemctl", f'#!/usr/bin/env bash\n[ "$1" = restart ] && printf %s \'{yeni}\' > "{data}/self-test-result.json"\nexit 0\n')
    r = _kos("oz_test.sh", {"PM_DATA": str(data), "PM_SYSTEMCTL": systemctl, "PM_BEKLE": "5"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "önceki sonuç kenara alındı" in r.stdout and list(data.glob("self-test-result.onceki-*.json")) and "durum: passed" in r.stdout
    assert '"uyumlu": 22' in r.stdout and '"model": "claude-opus-5-5"' in r.stdout


def test_kuru_kosu_imzali_istek_ve_dry_run_kosulu(tmp_path):
    bin_ = tmp_path / "bin"; bin_.mkdir(); etc = tmp_path / "etc"; etc.mkdir(); data = tmp_path / "data"; data.mkdir()
    sir = "0123456789abcdef" * 2
    (etc / "whatsapp.env").write_text(f"WA_APP_SECRET={sir}\nWA_PHONE_NUMBER_ID=106000000000001\n"); (etc / "alan").write_text("portman.ornek.invalid\n")
    (data / "settings.json").write_text(json.dumps({"enabled": False, "dry_run": True, "mode": "patron"}))
    # İE-07: gönderen Patron değil rol='test' kartı; rapor sorgusu g. önekli (giden ve isler'de aynı adlı 'durum' sütunu)
    psql = _sahte(bin_, "psql", '#!/usr/bin/env bash\nSQL="${@: -1}"\ncase "$SQL" in *"rol = \'patron\'"*) echo 900000000909 ;; *"rol = \'test\'"*) echo 900000000905 ;; '
                                '*"durum FROM isler"*) echo bitti ;; *"g.durum = \'bekliyor\'"*) echo 0 ;; *"count(*) FROM mesajlar"*) echo 1 ;; '
                                '*"string_agg(g.kind"*) echo "interactive:gonderilmedi, document:gonderilmedi" ;; *string_agg*) echo "ESKI-SORGU" ;; esac\n')
    webhook = _SahteSunucu(cevaplar={"/webhook": (200, {"ok": True, "mesaj": {"sahiplenildi": 1}, "durum": {}})})
    env = {"PM_ETC": str(etc), "PM_DATA": str(data), "PM_KOK": str(tmp_path / "yok"), "PM_PSQL": psql, "PM_WEBHOOK_URL": webhook.url + "/webhook", "PM_BEKLE": "1"}
    try:
        r = _kos("kuru_kosu.sh", env)
        assert r.returncode == 0, r.stdout + r.stderr
        istek = webhook.istekler[0]
        assert istek["headers"]["X-Hub-Signature-256"] == "sha256=" + hmac.new(sir.encode(), istek["body"], hashlib.sha256).hexdigest()
        yuk = json.loads(istek["body"]); m = yuk["entry"][0]["changes"][0]["value"]["messages"][0]
        assert m["from"] == "900000000905" and m["text"]["body"] == "P6001 aynalı (kuru koşu)" and m["id"].startswith("wamid.KURU")
        assert yuk["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"] == "Kuru Koşu"
        assert yuk["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] == "106000000000001"
        assert "900000000905" not in r.stdout and "900000000909" not in r.stdout and sir not in r.stdout and "…05" in r.stdout and "iş: bitti" in r.stdout
        assert "giden: interactive:gonderilmedi, document:gonderilmedi" in r.stdout and "ESKI-SORGU" not in r.stdout   # rapor satırı dolu (g. öneki)
        assert "test kartı" in r.stdout and "Patron konuşmasında satır yok" in r.stdout
        assert "kanal yeniden kapatıldı" in r.stdout and json.loads((data / "settings.json").read_text())["enabled"] is False
        (data / "settings.json").write_text(json.dumps({"enabled": True, "dry_run": False}))
        r = _kos("kuru_kosu.sh", env)
        assert r.returncode == 1 and "dry_run true değil" in r.stderr and len(webhook.istekler) == 1
        (data / "settings.json").write_text(json.dumps({"enabled": True, "dry_run": True}))
        webhook.cevaplar = {"/webhook": (200, {"ok": True, "mesaj": {"kayitsiz": 1}})}
        r = _kos("kuru_kosu.sh", env)
        assert r.returncode == 1 and "sahiplenilmedi" in r.stderr
        # test kartı yoksa DUR (Patron'un numarasına düşmez)
        psql2 = _sahte(bin_, "psql2", '#!/usr/bin/env bash\nSQL="${@: -1}"\ncase "$SQL" in *"rol = \'patron\'"*) echo 900000000909 ;; *"rol = \'test\'"*) echo "" ;; esac\n')
        r = _kos("kuru_kosu.sh", {**env, "PM_PSQL": psql2})
        assert r.returncode == 1 and "test göndericisi yok" in r.stderr and len(webhook.istekler) == 2
    finally:
        webhook.kapat()


def test_arsiv_al_env_dosyalari_haric(tmp_path):
    bin_ = tmp_path / "bin"; bin_.mkdir(); home = tmp_path / "home"; (home / "data").mkdir(parents=True); cikti = tmp_path / "cikti"; cikti.mkdir()
    (home / "data" / "settings.json").write_text("{}"); (home / "data" / "gizli.env").write_text("X=1"); (home / "data" / "projects").mkdir(); (home / "data" / "projects" / "a.pdf").write_bytes(b"%PDF")
    env = {"PM_HOME": str(home), "PM_CIKTI_DIR": str(cikti), "PM_PG_DUMP": _sahte(bin_, "pg_dump", SAHTE_PG_DUMP), "PM_PG_DUMP_LOG": str(tmp_path / "pgdump.log")}
    r = _kos("arsiv_al.sh", env)
    assert r.returncode == 0, r.stdout + r.stderr
    arsiv = list(cikti.glob("portman-arsiv-*.tgz"))
    assert len(arsiv) == 1 and arsiv[0].stat().st_mode & 0o777 == 0o600 and "sha256" in r.stdout
    with tarfile.open(arsiv[0]) as dis:
        assert sorted(dis.getnames()) == ["data.tar", "portman.dump"]
        with tarfile.open(fileobj=dis.extractfile("data.tar")) as ic:
            adlar = ic.getnames()
    assert "data/settings.json" in adlar and "data/projects/a.pdf" in adlar and "data/gizli.env" not in adlar


def test_durum_sh_salt_okunur_ve_maskeli(tmp_path):
    bin_ = tmp_path / "bin"; bin_.mkdir(); kok = tmp_path / "opt"; etc = tmp_path / "etc"; etc.mkdir(); (kok / "data" / "nabiz").mkdir(parents=True)
    (kok / "surumler" / "v2026.10.09").mkdir(parents=True); (kok / "surumler" / "v2026.10.09" / "SURUM").write_text("v2026.10.09\n"); os.symlink(kok / "surumler" / "v2026.10.09", kok / "guncel")
    (kok / "data" / "nabiz" / "agent.json").write_text(json.dumps({"zaman": int(time.time()), "surum": "v2026.10.09", "enabled": True}))
    env = {"PM_KOK": str(kok), "PM_ETC": str(etc), "PM_ALAN": "portman.ornek.invalid", "PM_LE_DIR": str(tmp_path / "le"), "PM_SAGLIK_URL": "http://127.0.0.1:9/saglik",
           "PM_SYSTEMCTL": _sahte(bin_, "systemctl", '#!/usr/bin/env bash\necho active\n'),
           "PM_SSHD": _sahte(bin_, "sshd", '#!/usr/bin/env bash\necho "passwordauthentication no"\necho "permitrootlogin prohibit-password"\necho "port 22"\n'),
           "PM_UFW": _sahte(bin_, "ufw", '#!/usr/bin/env bash\necho "Status: active"\necho "22/tcp ALLOW Anywhere"\n'),
           "PM_JOURNALCTL": _sahte(bin_, "journalctl", '#!/usr/bin/env bash\necho "mesaj wamid.HBgLOTAwMDAwMDAwMTY3FQIAERgSNzY3 kimden 900000000101 tamam"\n'),
           "PM_PSQL": _sahte(bin_, "psql", '#!/usr/bin/env bash\necho "bayi(aktif) 1 · mesaj 2"\n')}
    r = _kos("durum.sh", env)
    assert r.returncode == 0, r.stdout + r.stderr
    for parca in ("guncel: v2026.10.09", "portman-webhook        active", "passwordauthentication no", "Status: active", "bayi(aktif) 1", "sertifika", "agent", "cevap yok"):
        assert parca in r.stdout, parca
    assert "900000000101" not in r.stdout and "wamid.HBgL" not in r.stdout and "wamid.[…]" in r.stdout and "[…]" in r.stdout


def test_betik_sozdizimi():
    for p in sorted(VPS.glob("*.sh")):
        r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
        assert r.returncode == 0, (p.name, r.stderr)
    for p in ("sir_koy.py", "panel_parola.py", "uyari_gonder.py"):
        assert subprocess.run([sys.executable, "-m", "py_compile", str(VPS / p)]).returncode == 0
