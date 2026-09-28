"""İE-02 · VPS'te elle çalıştırılan küçük betikler (kapı C.1 ve E.4): anahtar değeri hiçbir çıktıya yazılmaz."""
from __future__ import annotations

import os
import stat
import subprocess
import sys

from conftest import KOK


def _env_dosyasi(tmp_path, satirlar: list[str]):
    p = tmp_path / "agent.env"
    p.write_text("\n".join(satirlar) + "\n", encoding="utf-8"); os.chmod(p, 0o640)
    return p


def test_anahtar_yenile_degeri_yazdirmaz_oteki_satirlari_korur(tmp_path):
    eski = "a" * 64
    p = _env_dosyasi(tmp_path, ["PORTMAN_API_URL=https://ornek.invalid/kanal_api.php", f"PORTMAN_API_TOKEN={eski}", "PORTMAN_HOME=/opt/portman"])
    r = subprocess.run([sys.executable, str(KOK / "vps" / "anahtar_yenile.py")], capture_output=True, text=True,
                       env={**os.environ, "PORTMAN_AGENT_ENV": str(p)})
    assert r.returncode == 0, r.stderr
    satirlar = p.read_text().splitlines()
    yeni = satirlar[1].split("=", 1)[1]
    assert satirlar[0] == "PORTMAN_API_URL=https://ornek.invalid/kanal_api.php" and satirlar[2] == "PORTMAN_HOME=/opt/portman"
    assert len(yeni) == 64 and yeni != eski and int(yeni, 16) >= 0
    assert eski not in r.stdout + r.stderr and yeni not in r.stdout + r.stderr
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o640
    [yedek] = list(tmp_path.glob("agent.env.before-c-*"))
    assert "PORTMAN_API_TOKEN" not in yedek.read_text() and "PORTMAN_HOME=/opt/portman" in yedek.read_text()
    assert stat.S_IMODE(os.stat(yedek).st_mode) == 0o600


def test_anahtar_yenile_anahtar_satiri_yoksa_dokunmaz(tmp_path):
    p = _env_dosyasi(tmp_path, ["PORTMAN_HOME=/opt/portman"])
    once = p.read_bytes()
    r = subprocess.run([sys.executable, str(KOK / "vps" / "anahtar_yenile.py")], capture_output=True, text=True,
                       env={**os.environ, "PORTMAN_AGENT_ENV": str(p)})
    assert r.returncode != 0 and p.read_bytes() == once and not list(tmp_path.glob("agent.env.before-c-*"))


def test_api_denetim_yalniz_surum_ve_ayar_yazar(tmp_path):
    from sahte_hosting import SahteHosting
    tok = os.urandom(32).hex()
    h = SahteHosting(tmp_path / "h", tok); url = h.basla()
    try:
        p = _env_dosyasi(tmp_path, [f"PORTMAN_API_URL={url}", f"PORTMAN_API_TOKEN={tok}"])
        r = subprocess.run([sys.executable, str(KOK / "vps" / "api_denetim.py")], capture_output=True, text=True,
                           env={**os.environ, "PORTMAN_AGENT_ENV": str(p)})
        assert r.returncode == 0, r.stderr
        assert '"api": "kanal-api-v1.2"' in r.stdout and '"worker": "vps"' in r.stdout and tok not in r.stdout
        assert h.cagri == ["settings"]
    finally:
        h.dur()


def test_anthropic_anahtar_degeri_yazdirmaz_izni_korur(tmp_path):
    """Kapı E (28.09): Claude anahtarı stdin'den agent.env'e; ekrana yalnız parmak izi; yedekte hiçbir anahtar satırı yok."""
    import http.server, json as _json, threading
    tok = "a" * 64
    p = _env_dosyasi(tmp_path, ["PORTMAN_API_URL=https://ornek.invalid/kanal_api.php", f"PORTMAN_API_TOKEN={tok}", "PORTMAN_HOME=/opt/portman"])
    anahtar = "sk-ant-api03-" + "Zx9" * 20

    class Hd(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            ok = self.headers.get("x-api-key") == anahtar
            b = _json.dumps({"data": [{"id": "claude-haiku-4-5-20251001"}]} if ok else {"error": {"type": "authentication_error", "message": "invalid x-api-key " + str(self.headers.get("x-api-key"))}}).encode()
            self.send_response(200 if ok else 401); self.end_headers(); self.wfile.write(b)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Hd); threading.Thread(target=srv.serve_forever, daemon=True).start()
    ortam = {**os.environ, "PM_ENV": str(p), "PM_ANTHROPIC_BASE": f"http://127.0.0.1:{srv.server_address[1]}/v1"}
    betik = str(KOK / "vps" / "anthropic_anahtar.py")
    r = subprocess.run([sys.executable, betik], input=anahtar + "\n", capture_output=True, text=True, env=ortam)
    assert r.returncode == 0, r.stderr
    cikti = r.stdout + r.stderr
    assert anahtar not in cikti and anahtar[7:27] not in cikti and tok not in cikti
    assert "HTTP 200" in cikti and "erişilebilir: evet" in cikti
    satirlar = p.read_text().splitlines()
    assert satirlar[-1] == "ANTHROPIC_API_KEY=" + anahtar and f"PORTMAN_API_TOKEN={tok}" in satirlar
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o640
    [yedek] = list(tmp_path.glob("agent.env.before-anthropic-*"))
    assert "PORTMAN_API_TOKEN" not in yedek.read_text() and "ANTHROPIC" not in yedek.read_text()
    r2 = subprocess.run([sys.executable, betik], input="yanlis-bir-sey", capture_output=True, text=True, env=ortam)   # geçersiz girdi
    assert r2.returncode != 0 and "yanlis" not in r2.stdout + r2.stderr and p.read_text().splitlines()[-1] == "ANTHROPIC_API_KEY=" + anahtar
    ikinci = "sk-ant-api03-" + "Qw7" * 20                                                                            # yenisi eskisinin yerine
    r3 = subprocess.run([sys.executable, betik], input=ikinci, capture_output=True, text=True, env=ortam)
    assert r3.returncode == 0 and "değiştirildi" in r3.stdout and "HTTP 401 authentication_error" in r3.stdout and ikinci not in r3.stdout
    assert sum(s.startswith("ANTHROPIC_API_KEY=") for s in p.read_text().splitlines()) == 1
    srv.shutdown()
