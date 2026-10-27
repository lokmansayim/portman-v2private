"""İE-21 · bayiye 3D sayfası: yayın (kanal/ucb_yayin.py), sayfa modeli (motor/ucb_sayfa.py), nginx yolu (vps/nginx/portman.conf),
yayın dizini (vps/nginx_uygula.sh) ve canlı açılış betiği (vps/ucb_ac.sh, PM_TEST). LLM, WhatsApp, Postgres ve canlı yok.
nginx sınaması yerel nginx varsa koşar (yoksa atlanır): depodaki yapılandırma kendi sertifikasıyla, ayrı portlarda; sayfa 200 + CSP,
anahtarsız / bilinmeyen / başka dosya 404, POST 403, sonundaki / düşmüşse 301, anahtar günlüğe girmez.

Koşum: python -m pytest testler/test_ucb.py -q
"""
from __future__ import annotations

import http.client
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
for _y in (KOK, KOK / "kanal"):
    if str(_y) not in sys.path:
        sys.path.insert(0, str(_y))

import ayarlar as AY          # noqa: E402
import ucb_yayin as UY        # noqa: E402

TABAN = "https://portman.ornek.invalid/3d"
CELIK_IFC = KOK / "deneme" / "2026-10-10_c8801" / "cizimler" / "C8801K_A" / "C8801K.ifc"
ALAN = "portman.ornek.invalid"


@pytest.fixture(scope="module")
def p6001_sayfa(tmp_path_factory) -> Path:
    from motor import ifc_uret as IU, ucb_sayfa as US
    d = tmp_path_factory.mktemp("p6001")
    ie = json.loads((KOK / "is_emri" / "P6001_2plus1_6x6.json").read_text(encoding="utf-8"))
    IU.uret(ie, d / "P6001.ifc", baslik="P6001")
    return US.uret(d / "P6001.ifc", d / "3d" / "index.html", baslik="P6001 r01")


# ───────────────────────── yayın ─────────────────────────
def test_ayar_yoksa_baglanti_yok(tmp_path, p6001_sayfa):
    (tmp_path / "3d").mkdir()
    assert UY.yayinla(p6001_sayfa, {}, tmp_path / "3d") == {"url": None}
    assert UY.yayinla(p6001_sayfa, {"ucb_taban_url": None}, tmp_path / "3d") == {"url": None}
    assert not list((tmp_path / "3d").iterdir())


def test_https_olmayan_taban_ve_eksik_dizin_baglanti_vermez(tmp_path, p6001_sayfa):
    r = UY.yayinla(p6001_sayfa, {"ucb_taban_url": "http://portman.ornek.invalid/3d"}, tmp_path)
    assert r["url"] is None and "https://" in r["yayin_hata"]
    r = UY.yayinla(p6001_sayfa, {"ucb_taban_url": TABAN}, tmp_path / "yok")
    assert r["url"] is None and "yayın dizini yok" in r["yayin_hata"] and not (tmp_path / "yok").exists()


def test_yayin_bayt_bayt_izinler_ve_anahtar(tmp_path, p6001_sayfa):
    kok = tmp_path / "3d"; kok.mkdir()
    eski = os.umask(0o077)                                     # worker'ın umask'ı; izinler açıkça verilmeli
    try:
        r1 = UY.yayinla(p6001_sayfa, {"ucb_taban_url": TABAN + "/"}, kok)
        r2 = UY.yayinla(p6001_sayfa, {"ucb_taban_url": TABAN}, kok)
    finally:
        os.umask(eski)
    assert r1["url"] == f"{TABAN}/{r1['anahtar']}/" and r1["anahtar"] != r2["anahtar"]
    for r in (r1, r2):
        assert UY.ANAHTAR.fullmatch(r["anahtar"])
        d = kok / r["anahtar"]
        assert (d / "index.html").read_bytes() == p6001_sayfa.read_bytes()
        assert d.stat().st_mode & 0o777 == 0o755 and (d / "index.html").stat().st_mode & 0o777 == 0o644
        assert [x.name for x in d.iterdir()] == ["index.html"]                   # geçici dosya kalmaz


def test_cakisan_anahtar_yeniden_denenir_ezilmez(tmp_path, p6001_sayfa, monkeypatch):
    kok = tmp_path / "3d"; kok.mkdir()
    var = "A" * 22; (kok / var).mkdir(); (kok / var / "index.html").write_text("başkasının sayfası")
    sira = iter([var, var, "B" * 22])
    monkeypatch.setattr(UY, "anahtar_uret", lambda: next(sira))
    r = UY.yayinla(p6001_sayfa, {"ucb_taban_url": TABAN}, kok)
    assert r["anahtar"] == "B" * 22 and (kok / var / "index.html").read_text() == "başkasının sayfası"
    monkeypatch.setattr(UY, "anahtar_uret", lambda: var)
    assert UY.yayinla(p6001_sayfa, {"ucb_taban_url": TABAN}, kok) == {"url": None, "yayin_hata": "boş anahtar bulunamadı"}


def test_anahtar_deseni_nginx_ile_ayni():
    conf = (KOK / "vps" / "nginx" / "portman.conf").read_text(encoding="utf-8")
    konum = re.search(r'location ~ "\^/3d/(.+?)/\(index', conf)
    assert konum and konum.group(1) == UY.ANAHTAR.pattern
    assert len(UY.anahtar_uret()) == 22 and all(UY.ANAHTAR.fullmatch(UY.anahtar_uret()) for _ in range(200))


def test_ornek_sayfa_p6001(tmp_path):
    (tmp_path / "yayin" / "3d").mkdir(parents=True)
    r = UY.ornek(tmp_path, TABAN, KOK)
    assert r["url"].startswith(TABAN + "/") and (tmp_path / "yayin" / "3d" / r["anahtar"] / "index.html").read_bytes() == Path(r["sayfa"]).read_bytes()
    assert "P6001 örnek" in Path(r["sayfa"]).read_text(encoding="utf-8")


# ───────────────────────── sayfa modeli ─────────────────────────
def _model(ifc: Path) -> list[dict]:
    from motor import ucb_sayfa as US
    return US.model_json(ifc)["elemanlar"]


def test_prefabrik_cati_ve_renk_ifcden(p6001_sayfa):
    m = _model(p6001_sayfa.parent.parent / "P6001.ifc")
    cati = [e for e in m if e.get("cati")]
    assert cati and not any(e["sinif"] == "IfcSpace" for e in cati)
    assert {e["sinif"] for e in m if e["sinif"] == "IfcWall"} and not any(e.get("cati") for e in m if e["sinif"] in ("IfcWall", "IfcWindow", "IfcDoor"))
    for e in m:
        assert sum(g[1] for g in e["g"]) == len(e["i"]) and all(0 <= g[2] < len(e["m"]) for g in e["g"])
        assert all(len(c) == 4 and 0.0 <= c[3] <= 1.0 for c in e["m"])
    # çatı örtüsü IFC'deki malzemenin rengiyle (antrasit; sınıfın kiremit kırmızısı değil)
    ortu = [e for e in cati if e["sinif"] == "IfcSlab"]
    assert ortu and all(max(c[:3]) < 0.45 for e in ortu for c in e["m"])
    odalar = [e for e in m if e["sinif"] == "IfcSpace"]
    assert odalar and all(e["alan"] for e in odalar)


@pytest.mark.skipif(not CELIK_IFC.is_file(), reason="çelik IFC örneği yok")
def test_celik_cati_ve_tavan_gizlenir():
    m = _model(CELIK_IFC)
    cati = {e["sinif"] for e in m if e.get("cati")}
    assert cati and not any(e.get("cati") for e in m if e["sinif"] in ("IfcSpace", "IfcWall", "IfcWindow", "IfcDoor"))
    assert [e for e in m if e["sinif"] == "IfcSpace"]


def test_sayfa_dis_agsiz(p6001_sayfa):
    html = p6001_sayfa.read_text(encoding="utf-8")
    assert "THREE" in html and "OrbitControls" in html and "Çatıyı aç" in html and "Üstten" in html
    assert not re.search(r"""(src|href)\s*=\s*["']?https?://""", html) and "cdnjs" not in html      # bağlantı CSP'yle de kapalı (connect-src yok)


# ───────────────────────── sunucu betikleri ─────────────────────────
def _kos(betik: str, env: dict, *arg) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(KOK / "vps" / betik), *arg], env={**os.environ, **env}, capture_output=True, text=True, timeout=180)


def test_nginx_uygula_yayin_dizini_ve_gecis(tmp_path):
    data = tmp_path / "data"; (data / "projects").mkdir(parents=True); data.chmod(0o750); (data / "projects").chmod(0o750)
    (data / "kendi.json").write_text("{}"); (data / "kendi.json").chmod(0o644)
    etc = tmp_path / "etc"; etc.mkdir(); (etc / "alan").write_text(ALAN + "\n")
    env = {"PM_ETC": str(etc), "PM_NGINX_DIR": str(tmp_path / "nginx"), "PM_LE_DIR": str(tmp_path / "le"), "PM_DATA": str(data),
           "PM_KULLANICI": subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip(), "PM_TEST": "1"}
    r = _kos("nginx_uygula.sh", env, str(KOK))
    assert r.returncode == 0, r.stderr
    assert f"yayın: {data}/yayin/3d hazır (755; data 751) · başkasına açıktı, kapatıldı: kendi.json" in r.stdout
    assert (data / "yayin" / "3d").stat().st_mode & 0o777 == 0o755 and data.stat().st_mode & 0o777 == 0o751
    assert (data / "kendi.json").stat().st_mode & 0o777 == 0o640 and (data / "projects").stat().st_mode & 0o777 == 0o750
    r = _kos("nginx_uygula.sh", env, str(KOK))                                   # ikinci koşu aynı sonuç
    assert r.returncode == 0 and f"yayın: {data}/yayin/3d hazır (755; data 751)\n" in r.stdout and "nginx: değişiklik yok" in r.stdout
    r = _kos("nginx_uygula.sh", {**env, "PM_DATA": str(tmp_path / "yok")}, str(KOK))
    assert r.returncode == 0 and "3D yayın dizini atlandı" in r.stdout and not (tmp_path / "yok").exists()


def _ucb_ortam(tmp_path, yayin=True) -> dict:
    kok = tmp_path / "kok"; data = kok / "data"; data.mkdir(parents=True); data.chmod(0o751)
    if yayin:
        (data / "yayin" / "3d").mkdir(parents=True); (data / "yayin").chmod(0o755); (data / "yayin" / "3d").chmod(0o755)
    (data / "settings.json").write_text(json.dumps(AY.VARSAYILAN), encoding="utf-8")
    etc = tmp_path / "etc"; etc.mkdir(); (etc / "alan").write_text(ALAN + "\n")
    ngx = tmp_path / "nginx" / "sites-available"; ngx.mkdir(parents=True)
    (ngx / "portman.conf").write_text((KOK / "vps" / "nginx" / "portman.conf").read_text(encoding="utf-8").replace("__ALAN__", ALAN), encoding="utf-8")
    return {"PM_KOK": str(kok), "PM_ETC": str(etc), "PM_NGINX_DIR": str(tmp_path / "nginx"), "PM_PYTHON": sys.executable, "PM_OLARAK": "", "PM_TEST": "1"}


def test_ucb_ac_ornek_yayimlar_ayari_acar_kapat_geri_alir(tmp_path):
    env = _ucb_ortam(tmp_path)
    ayar = lambda: AY.oku(Path(env["PM_KOK"]) / "data")["ucb_taban_url"]
    r = _kos("ucb_ac.sh", env)
    assert r.returncode == 0, r.stdout + r.stderr
    url = re.search(r"Telefonda açın: (\S+)", r.stdout).group(1)
    anahtar = re.fullmatch(rf"https://{re.escape(ALAN)}/3d/([A-Za-z0-9_-]{{22}})/", url).group(1)
    sayfa = Path(env["PM_KOK"]) / "data" / "yayin" / "3d" / anahtar / "index.html"
    assert sayfa.stat().st_mode & 0o777 == 0o644 and "P6001 örnek" in sayfa.read_text(encoding="utf-8")
    assert "PM_TEST: HTTP denetimi atlandı" in r.stdout and ayar() == f"https://{ALAN}/3d"
    r = _kos("ucb_ac.sh", env, "kapat")
    assert r.returncode == 0 and "kapatıldı: ucb_taban_url = null" in r.stdout and ayar() is None and sayfa.is_file()


def test_ucb_ac_yayin_dizini_yoksa_durur_ayar_degismez(tmp_path):
    env = _ucb_ortam(tmp_path, yayin=False)
    r = _kos("ucb_ac.sh", env)
    assert r.returncode == 1 and "DUR:" in r.stderr and "yayin/3d yok" in r.stderr and "ayar değişmedi: ucb_taban_url = null" in r.stdout
    assert AY.oku(Path(env["PM_KOK"]) / "data")["ucb_taban_url"] is None


# ───────────────────────── nginx (yerel nginx varsa) ─────────────────────────
def _bos_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def nginx_sunucu(tmp_path_factory, p6001_sayfa):
    if not shutil.which("nginx") or not shutil.which("openssl"):
        pytest.skip("yerel nginx ya da openssl yok")
    import tempfile                                                # nginx işçisi root değil (nobody/www-data): yol başkasına geçilebilir olmalı
    d = Path(tempfile.mkdtemp(prefix="pm_ucb_ngx_", dir="/var/tmp" if Path("/var/tmp").is_dir() else None)); d.chmod(0o755)
    data = d / "data"; (data / "projects").mkdir(parents=True); (data / "projects" / "gizli.json").write_text("{}")
    (data / "settings.json").write_text("{}")
    le = d / "le" / "live" / ALAN; le.mkdir(parents=True)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", f"/CN={ALAN}", "-addext", f"subjectAltName=DNS:{ALAN}",
                    "-keyout", str(le / "privkey.pem"), "-out", str(le / "fullchain.pem")], check=True, capture_output=True)
    etc = d / "etc"; etc.mkdir(); (etc / "alan").write_text(ALAN + "\n")
    kullanici = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
    for x in (data, data / "projects"):
        x.chmod(0o750)
    r = _kos("nginx_uygula.sh", {"PM_ETC": str(etc), "PM_NGINX_DIR": str(d / "nginx"), "PM_LE_DIR": str(d / "le"), "PM_DATA": str(data),
                                 "PM_KULLANICI": kullanici, "PM_TEST": "1"}, str(KOK))
    assert r.returncode == 0, r.stderr
    p80, p443 = _bos_port(), _bos_port()
    site = (d / "nginx" / "sites-available" / "portman.conf").read_text(encoding="utf-8")
    site = "\n".join(x for x in site.splitlines() if "listen [::]" not in x)
    site = (site.replace("/opt/portman/data", str(data)).replace("/etc/letsencrypt", str(d / "le")).replace("/var/log/nginx/portman.access.log", str(d / "access.log"))
            .replace("/var/www/portman-acme", str(d)).replace("listen 80;", f"listen 127.0.0.1:{p80};").replace("listen 443 ssl http2;", f"listen 127.0.0.1:{p443} ssl;"))
    (d / "site.conf").write_text(site, encoding="utf-8")
    mime = "include /etc/nginx/mime.types;" if Path("/etc/nginx/mime.types").is_file() else "types { text/html html; }"
    (d / "nginx.conf").write_text(f"worker_processes 1; pid {d}/nginx.pid; error_log {d}/error.log;\nevents {{}}\n"
                                  f"http {{ {mime} default_type application/octet-stream; client_body_temp_path {d}/tmp; proxy_temp_path {d}/tmp;"
                                  f" fastcgi_temp_path {d}/tmp; uwsgi_temp_path {d}/tmp; scgi_temp_path {d}/tmp; include {d}/site.conf; }}\n", encoding="utf-8")
    (d / "tmp").mkdir()
    anahtar = UY.yayinla(p6001_sayfa, {"ucb_taban_url": TABAN}, data / "yayin" / "3d")["anahtar"]
    r = subprocess.run(["nginx", "-e", str(d / "error.log"), "-c", str(d / "nginx.conf")], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"nginx başlatılamadı: {r.stderr.strip()[-200:]}")
    time.sleep(0.5)
    ctx = ssl.create_default_context(cafile=str(le / "fullchain.pem")); ctx.check_hostname = False
    yield {"port": p443, "ctx": ctx, "anahtar": anahtar, "sayfa": p6001_sayfa, "log": d / "access.log"}
    subprocess.run(["nginx", "-e", str(d / "error.log"), "-c", str(d / "nginx.conf"), "-s", "stop"], capture_output=True)


def _iste(s: dict, yol: str, yontem: str = "GET") -> tuple[int, dict, bytes]:
    c = http.client.HTTPSConnection("127.0.0.1", s["port"], context=s["ctx"], timeout=10)
    c.request(yontem, yol, headers={"Host": ALAN})
    r = c.getresponse(); govde = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, govde


def test_nginx_yalniz_anahtarli_sayfayi_sunar(nginx_sunucu):
    s, k = nginx_sunucu, nginx_sunucu["anahtar"]
    kod, b, govde = _iste(s, f"/3d/{k}/")
    assert kod == 200 and govde == s["sayfa"].read_bytes() and b["content-type"].startswith("text/html")
    assert b["content-security-policy"].startswith("default-src 'none'; script-src 'unsafe-inline'") and "frame-ancestors 'none'" in b["content-security-policy"]
    for h in ("strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy", "x-robots-tag"):
        assert h in b, h
    assert _iste(s, f"/3d/{k}/index.html")[0] == 200
    kod, b, _ = _iste(s, f"/3d/{k}")
    assert kod == 301 and b["location"].endswith(f"/3d/{k}/")
    for yol in ("/3d/", "/3d", f"/3d/{'A' * 22}/", f"/3d/{k}/x.ifc", f"/3d/{k}/.index.html.yeni", f"/3d/{k}x/", "/settings.json", "/3d/../settings.json",
                "/3d/%2e%2e/settings.json", "/projects/gizli.json", f"/yayin/3d/{k}/index.html"):
        assert _iste(s, yol)[0] == 404, yol
    assert _iste(s, f"/3d/{k}/", "POST")[0] == 403
    time.sleep(0.2)
    assert k not in s["log"].read_text(encoding="utf-8").replace(f"/yayin/3d/{k}/", "")    # /3d/ yolları günlüğe anahtarsız
