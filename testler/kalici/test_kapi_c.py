"""Kapı C · vps/kapi_c.py: sahte hosting, sahte OpenAI ve sahte systemctl ile uçtan uca. Anahtar değeri hiçbir çıktıda yok;
adım sırası zorunlu; hosting güncellenmeden yeniden başlatılmaz; eski OpenAI anahtarı iptal edilmeden bitmez ve geçici
klasör (eski anahtarlar) ancak her şey doğrulanınca silinir."""
from __future__ import annotations

import http.server
import json
import os
import secrets
import signal
import stat
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
BETIK = KOK / "vps" / "kapi_c.py"

SAHTE_SYSTEMCTL = textwrap.dedent('''\
    #!{py}
    import json, os, signal, subprocess, sys, time
    from pathlib import Path
    durum = Path(os.environ["SAHTE_DURUM"]); d = json.loads(durum.read_text()) if durum.exists() else {{}}
    def canli(pid):
        try: return int(pid) > 0 and (os.kill(int(pid), 0) or True)
        except (OSError, ValueError): return False
    a = sys.argv[1:]
    if a[:1] == ["show"]: print(d.get("pid", 0))
    elif a[:1] == ["is-active"]: print("active" if canli(d.get("pid", 0)) else "inactive")
    elif a[:1] == ["restart"]:
        if canli(d.get("pid", 0)): os.kill(int(d["pid"]), signal.SIGTERM)
        env = dict(s.split("=", 1) for s in Path(os.environ["PM_ENV"]).read_text().splitlines() if "=" in s)
        p = subprocess.Popen(["sleep", "600"], env={{"PORTMAN_API_TOKEN": env["PORTMAN_API_TOKEN"], "PATH": "/usr/bin:/bin"}},
                             start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        d["pid"] = p.pid; durum.write_text(json.dumps(d))
        g = Path(os.environ["PM_HOME"]) / "logs" / "agent.log"; g.parent.mkdir(parents=True, exist_ok=True)
        with g.open("a") as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " başladı vps-agent-v1.1.1 home x api y\\n")
''')


class Sahte:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.hosting_anahtar = ""                 # hosting'teki api_token.txt
        self.panel_openai = ""                    # panelin ayarlar.json'undaki openai_key
        self.openai_gecerli: set[str] = set()
        sahte = self

        class Hd(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def _cevap(self, kod, govde):
                b = json.dumps(govde).encode(); self.send_response(kod); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

            def do_GET(self):
                if self.path.startswith("/kanal_api.php"):
                    if not sahte.hosting_anahtar or self.headers.get("X-Portman-Token") != sahte.hosting_anahtar:
                        return self._cevap(401, {"error": "unauthorized"})
                    return self._cevap(200, {"api": "kanal-api-v1.1", "enabled": True, "openai_key": sahte.panel_openai})
                if self.path == "/v1/models":
                    k = (self.headers.get("Authorization") or "").removeprefix("Bearer ")
                    if k in sahte.openai_gecerli:
                        return self._cevap(200, {"data": [{"id": "gpt-4o-mini"}]})
                    return self._cevap(401, {"error": {"message": f"Incorrect API key provided: {k[:8]}***{k[-4:]}", "code": "invalid_api_key"}})
                self._cevap(404, {})

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Hd)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        port = self.srv.server_address[1]
        self.env_dosya = tmp / "etc" / "agent.env"; self.env_dosya.parent.mkdir()
        self.home = tmp / "opt"; (self.home / "data" / "pending").mkdir(parents=True); (self.home / "logs").mkdir()
        self.depo = tmp / "root" / ".portman_kapi_c"
        sc = tmp / "systemctl"; sc.write_text(SAHTE_SYSTEMCTL.format(py=sys.executable)); sc.chmod(0o755)
        self.ortam = {**os.environ, "PM_ENV": str(self.env_dosya), "PM_HOME": str(self.home), "PM_KAPI_C_DIR": str(self.depo),
                      "PM_OPENAI_BASE": f"http://127.0.0.1:{port}/v1", "PM_SYSTEMCTL": str(sc), "PM_BEKLE_SN": "1",
                      "SAHTE_DURUM": str(tmp / "systemctl.json")}
        self.api = f"http://127.0.0.1:{port}/kanal_api.php"
        self.ciktilar: list[str] = []

    def env_yaz(self, anahtar):
        self.env_dosya.write_text(f"PORTMAN_API_URL={self.api}\nPORTMAN_API_TOKEN={anahtar}\nPORTMAN_HOME=/opt/portman\n")
        os.chmod(self.env_dosya, 0o640)

    def dosyadaki(self):
        return next(s.split("=", 1)[1] for s in self.env_dosya.read_text().splitlines() if s.startswith("PORTMAN_API_TOKEN="))

    def kos(self, adim):
        r = subprocess.run([sys.executable, "-", adim], input=BETIK.read_text(), capture_output=True, text=True, env=self.ortam, timeout=120)
        self.ciktilar.append(r.stdout + r.stderr)
        return r

    def baslat(self):
        subprocess.run([self.ortam["PM_SYSTEMCTL"], "restart", "portman-agent"], env=self.ortam, check=True)

    def kapat(self):
        self.srv.shutdown()
        p = self.tmp / "systemctl.json"
        if p.exists():
            try: os.kill(int(json.loads(p.read_text())["pid"]), signal.SIGTERM)
            except OSError: pass


@pytest.fixture
def s(tmp_path):
    x = Sahte(tmp_path)
    x.eski_e, x.eski_o, x.yeni_o = secrets.token_hex(32), "sk-proj-" + secrets.token_urlsafe(30), "sk-proj-" + secrets.token_urlsafe(30)
    x.env_yaz(x.eski_e); x.hosting_anahtar = x.eski_e; x.panel_openai = x.eski_o; x.openai_gecerli = {x.eski_o}
    x.baslat()
    yield x
    x.kapat()


def _sizinti_yok(s, *degerler):
    hepsi = "\n".join(s.ciktilar)
    for d in degerler:
        assert not any(d[i:i + 8] in hepsi for i in range(len(d) - 7)), "çıktıda anahtar parçası"
    assert "Incorrect API key" not in hepsi


def test_uctan_uca_sira_ve_iptal(s):
    assert s.kos("yenile").returncode == 1                                     # hazırlıksız yenileme yok
    r = s.kos("hazirla"); assert r.returncode == 0, r.stdout + r.stderr
    assert stat.S_IMODE(s.depo.stat().st_mode) == 0o700 and all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in s.depo.iterdir())
    s.panel_openai = s.yeni_o; s.openai_gecerli = {s.eski_o, s.yeni_o}          # Lokman: yeni OpenAI anahtarı panelde
    r = s.kos("yenile"); assert r.returncode == 0, r.stdout
    yeni_e = s.dosyadaki()
    assert yeni_e != s.eski_e and len(yeni_e) == 64 and stat.S_IMODE(s.env_dosya.stat().st_mode) == 0o640
    [yedek] = list(s.env_dosya.parent.glob("agent.env.before-c-*"))
    assert "PORTMAN_API_TOKEN" not in yedek.read_text()
    assert s.kos("yenile").returncode == 1                                     # ikinci kez yenilemez
    assert s.kos("hazirla").returncode == 1                                    # yarım denemenin üstüne yeniden hazırlanmaz
    r = s.kos("ara"); assert r.returncode == 1 and "api_token.txt" in r.stdout  # hosting güncellenmeden ara geçmez…
    assert s.kos("yeniden_baslat").returncode == 1                             # …ve yeniden başlatılmaz
    s.hosting_anahtar = yeni_e                                                 # Lokman: api_token.txt'ye yapıştırdı
    r = s.kos("ara"); assert r.returncode == 0, r.stdout
    assert "✓ hosting eski eşleşme anahtarını reddediyor (401)" in r.stdout
    r = s.kos("yeniden_baslat"); assert r.returncode == 0, r.stdout
    r = s.kos("bitir"); assert r.returncode == 1 and "✗ eski OpenAI anahtarı OpenAI'de geçersiz" in r.stdout and s.depo.exists()
    s.openai_gecerli = {s.yeni_o}                                              # Lokman: eski OpenAI anahtarını iptal etti
    r = s.kos("bitir"); assert r.returncode == 0, r.stdout
    assert "Kapı C tamam" in r.stdout and not s.depo.exists()
    _sizinti_yok(s, s.eski_e, yeni_e, s.eski_o, s.yeni_o)


def test_panelde_openai_degismediyse_ara_durur(s):
    assert s.kos("hazirla").returncode == 0
    assert s.kos("yenile").returncode == 0
    s.hosting_anahtar = s.dosyadaki()
    r = s.kos("ara")
    assert r.returncode == 1 and "✗ panel yeni bir OpenAI anahtarı veriyor" in r.stdout and "servis yeniden başlatılmadı" in r.stdout
    _sizinti_yok(s, s.eski_e, s.dosyadaki(), s.eski_o)


def test_hazirlik_gecmezse_hicbir_sey_yazilmaz(s):
    s.hosting_anahtar = "b" * 64                                               # hosting bugünkü anahtarı kabul etmiyor
    r = s.kos("hazirla")
    assert r.returncode == 1 and not s.depo.exists() and s.dosyadaki() == s.eski_e


def test_temizle_yarim_denemeyi_siler(s):
    assert s.kos("hazirla").returncode == 0 and s.depo.exists()
    r = s.kos("temizle"); assert r.returncode == 0 and not s.depo.exists()
    _sizinti_yok(s, s.eski_e, s.eski_o)
