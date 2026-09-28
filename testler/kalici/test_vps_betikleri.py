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
