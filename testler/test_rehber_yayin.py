"""İE-34 · bayiye montaj rehberi: denetim ve yayın (kanal/rehber_yayin.py), nginx yolu (vps/nginx/portman.conf › /rehber/), yayın dizini
(vps/nginx_uygula.sh) ve yayın betiği (vps/rehber_yayinla.sh, PM_TEST). LLM, WhatsApp, Postgres ve canlı yok.
Rehber hedef örnekten (testler/paket/rehber62/veri.json) İE-18'in koduyla üretilir (araclar/paket/rehber/sayfa.py); yayın baytları değiştirmez.
nginx sınaması yerel nginx varsa koşar (yoksa atlanır): rehber 200, CSP yalnız jsDelivr ve Google Fonts; anahtarsız / bilinmeyen / başka dosya
404, POST 405, sonundaki / düşmüşse 301, anahtar erişim ve hata günlüğüne girmez; /3d/ yolu aynen.

Koşum: python -m pytest testler/test_rehber_yayin.py -q
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

import rehber_yayin as RY     # noqa: E402
import ucb_yayin as UY        # noqa: E402

ALAN = "portman.ornek.invalid"
TABAN = f"https://{ALAN}/rehber"
CONF = KOK / "vps" / "nginx" / "portman.conf"


@pytest.fixture(scope="module")
def rehber(tmp_path_factory) -> Path:
    """62 m² hedef örneğinin rehberi (İE-18 şablonu + hedef verisi), evin altında TK-01 r07 ön onay sayfasıyla (M-13 hedefi)."""
    from araclar.paket.rehber import sayfa
    veri = json.loads((KOK / "testler" / "paket" / "rehber62" / "veri.json").read_text(encoding="utf-8"))
    d = tmp_path_factory.mktemp("rehber")
    return sayfa.yaz(veri, d / "rehber.html", gorseller=[["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ" + "A1234567890" * 4, "Dış görünüş"]])


def _konum(desen: str) -> str:
    s = CONF.read_text(encoding="utf-8")
    m = re.search(re.escape(f'location ~ "^/{desen}/[A-Za-z0-9_-]{{22}}/(index\\.html)?$" {{') + r"(.*?)\n    \}", s, re.S)
    assert m, desen
    return m.group(1)


# ───────────────────────── denetim ─────────────────────────
def test_hedef_rehber_denetimden_gecer(rehber):
    sorun, bilgi = RY.denetle(rehber.read_bytes())
    assert sorun == [] and bilgi["baslik"].endswith(" Montaj Rehberi") and bilgi["boyut"] == rehber.stat().st_size


@pytest.mark.parametrize("bozma, beklenen", [
    (lambda s: b"", "dosya boş"),
    (lambda s: b"\xff\xfe" + s, "UTF-8 değil"),
    (lambda s: s.replace(b" Montaj Rehberi</title>", b"</title>"), "başlık"),
    (lambda s: s.replace(b'<meta name="viewport"', b'<meta name="x"'), "rehber imi yok: telefon ayarı"),
    (lambda s: s.replace(b'id="pafta"', b'id="x"'), "rehber imi yok: pafta verisi"),
    (lambda s: s.replace(b"three@0.160.0/build", b"three@0.159.0/build"), "rehber imi yok: three.js 0.160.0"),
    (lambda s: s + b"<!-- __KAGIT__ -->", "doldurulmamış yer tutucu: __KAGIT__"),
    (lambda s: s + b'<img src="https://ornek.invalid/x.png">', "izinsiz dış adres: ornek.invalid"),
    (lambda s: s + b'<script src="//kotu.example.com/a.js"></script>', "izinsiz dış adres: kotu.example.com"),
    (lambda s: s.replace(b"</title>", "</title><p>Müşteri: 0532 123 45 67</p>".encode()), "telefon numarasına benzeyen 1 dizge"),
    (lambda s: s.replace(b"</title>", "</title><p>+90 532 1234567</p>".encode()), "telefon numarasına benzeyen 1 dizge"),
])
def test_bozuk_dosya_yayimlanmaz(tmp_path, rehber, bozma, beklenen):
    kok = tmp_path / "rehber"; kok.mkdir()
    r = RY.yayinla(bozma(rehber.read_bytes()), kok, TABAN)
    assert r["url"] is None and any(beklenen in x for x in r["sorunlar"]), r["sorunlar"]
    assert list(kok.iterdir()) == []


def test_buyuk_dosya_yayimlanmaz(tmp_path, rehber, monkeypatch):
    monkeypatch.setattr(RY, "EN_COK", 1000)
    kok = tmp_path / "rehber"; kok.mkdir()
    r = RY.yayinla(rehber.read_bytes(), kok, TABAN)
    assert r["url"] is None and r["sorunlar"][0].startswith(f"dosya {rehber.stat().st_size} bayt") and list(kok.iterdir()) == []


def test_olcu_ve_ondalik_telefon_sayilmaz(rehber):
    ek = "</title><p>773 x 1014 cm · 0,879166666666666 · 0.30000000000000004 · 125,5 cm · PM-K1234-20261109-001</p>".encode()
    assert RY.denetle(rehber.read_bytes().replace(b"</title>", ek))[0] == []


# ───────────────────────── yayın ─────────────────────────
def test_yayin_bayt_bayt_izinler_ve_anahtar(tmp_path, rehber):
    kok = tmp_path / "data" / "yayin" / "rehber"; kok.mkdir(parents=True)
    r = RY.yayinla(rehber.read_bytes(), kok, TABAN + "/")
    anahtar = re.fullmatch(rf"https://{re.escape(ALAN)}/rehber/([A-Za-z0-9_-]{{22}})/", r["url"]).group(1)
    assert r["anahtar"] == anahtar and r["sha256"] and r["baslik"].endswith(" Montaj Rehberi")
    sayfa = kok / anahtar / "index.html"
    assert sayfa.read_bytes() == rehber.read_bytes()
    assert (kok / anahtar).stat().st_mode & 0o777 == 0o755 and sayfa.stat().st_mode & 0o777 == 0o644
    assert sorted(p.name for p in (kok / anahtar).iterdir()) == ["index.html"]
    r2 = RY.yayinla(rehber.read_bytes(), kok, TABAN)                 # aynı dosya ikinci kez: yeni anahtar, eskisi ezilmez
    assert r2["anahtar"] != anahtar and sayfa.read_bytes() == rehber.read_bytes()


def test_https_olmayan_taban_ve_eksik_dizin_baglanti_vermez(tmp_path, rehber):
    kok = tmp_path / "rehber"; kok.mkdir()
    assert RY.yayinla(rehber.read_bytes(), kok, f"http://{ALAN}/rehber")["yayin_hata"].startswith("ucb_taban_url https://")
    assert "yayın dizini yok" in RY.yayinla(rehber.read_bytes(), tmp_path / "yok", TABAN)["yayin_hata"]


def test_komut_satiri_standart_girdiden(tmp_path, rehber):
    data = tmp_path / "data"; (data / "yayin" / "rehber").mkdir(parents=True)
    with rehber.open("rb") as f:
        r = subprocess.run([sys.executable, str(KOK / "kanal" / "rehber_yayin.py"), "--veri", str(data), "--taban", TABAN, "-"],
                           stdin=f, capture_output=True, text=True, timeout=60, cwd="/tmp")
    assert r.returncode == 0, r.stderr
    sonuc = json.loads(r.stdout.strip().splitlines()[-1])
    assert (data / "yayin" / "rehber" / sonuc["anahtar"] / "index.html").read_bytes() == rehber.read_bytes()


# ───────────────────────── nginx yapılandırması ─────────────────────────
def test_nginx_rehber_konumu_anahtar_ve_csp():
    blok = _konum("rehber")
    assert UY.ANAHTAR.pattern in CONF.read_text(encoding="utf-8").split('location ~ "^/rehber/')[1].split('"')[0]
    csp = re.search(r'Content-Security-Policy "([^"]+)"', blok).group(1)
    hostlar = set(re.findall(r"https://([a-z0-9.-]+)", csp))
    assert hostlar == set(RY.IZINLI)
    assert csp.startswith("default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net;") and "frame-ancestors 'none'" in csp
    assert "connect-src" not in csp and "*" not in csp
    for satir in ("root /opt/portman/data/yayin;", "access_log /var/log/nginx/portman.access.log pm_rehber;", "log_not_found off;",
                  'if ($request_method !~ ^(GET|HEAD)$) { return 405; }', 'X-Robots-Tag "noindex, nofollow"', "Strict-Transport-Security",
                  "X-Content-Type-Options nosniff", "X-Frame-Options DENY", "Referrer-Policy no-referrer"):
        assert satir in blok, satir
    s = CONF.read_text(encoding="utf-8")
    assert "log_format pm_rehber '$remote_addr $request_method /rehber/- $status" in s
    assert 'location /rehber/ { access_log /var/log/nginx/portman.access.log pm_rehber; return 404; }' in s
    assert "script-src 'unsafe-inline'; style-src" in _konum("3d")             # 3D yolu aynen: dış ağ kapalı


def test_kurulum_gomulu_nginx_kopyasi_ayni():
    k = (KOK / "vps" / "kurulum.sh").read_text(encoding="utf-8")
    ic = k.split("nginx_sablon() { cat <<'EOF'\n", 1)[1].split("\nEOF\n", 1)[0] + "\n"
    assert ic == CONF.read_text(encoding="utf-8")
    assert '"$KOK/data/yayin/rehber"' in k


# ───────────────────────── sunucu betikleri ─────────────────────────
def _kos(betik: str, env: dict, *arg, girdi=None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(KOK / "vps" / betik), *arg], env={**os.environ, **env}, capture_output=True, text=True, timeout=180,
                          stdin=girdi if girdi is not None else subprocess.DEVNULL)


def test_nginx_uygula_rehber_dizinini_acar(tmp_path):
    data = tmp_path / "data"; data.mkdir(); data.chmod(0o750)
    etc = tmp_path / "etc"; etc.mkdir(); (etc / "alan").write_text(ALAN + "\n")
    env = {"PM_ETC": str(etc), "PM_NGINX_DIR": str(tmp_path / "nginx"), "PM_LE_DIR": str(tmp_path / "le"), "PM_DATA": str(data),
           "PM_KULLANICI": subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip(), "PM_TEST": "1"}
    r = _kos("nginx_uygula.sh", env, str(KOK))
    assert r.returncode == 0, r.stderr
    assert f"yayın: {data}/yayin/3d hazır (755; data 751)\n" in r.stdout and f"yayın: {data}/yayin/rehber hazır (755; montaj rehberi, İE-34)\n" in r.stdout
    assert (data / "yayin" / "rehber").stat().st_mode & 0o777 == 0o755 and (data / "yayin" / "3d").stat().st_mode & 0o777 == 0o755


def _yayin_ortam(tmp_path, dizin=True) -> dict:
    kok = tmp_path / "kok"; data = kok / "data"; data.mkdir(parents=True); data.chmod(0o751)
    if dizin:
        (data / "yayin" / "rehber").mkdir(parents=True); (data / "yayin").chmod(0o755); (data / "yayin" / "rehber").chmod(0o755)
    (data / "settings.json").write_text("{}", encoding="utf-8")
    etc = tmp_path / "etc"; etc.mkdir(); (etc / "alan").write_text(ALAN + "\n")
    ngx = tmp_path / "nginx" / "sites-available"; ngx.mkdir(parents=True)
    (ngx / "portman.conf").write_text(CONF.read_text(encoding="utf-8").replace("__ALAN__", ALAN), encoding="utf-8")
    return {"PM_KOK": str(kok), "PM_ETC": str(etc), "PM_NGINX_DIR": str(tmp_path / "nginx"), "PM_PYTHON": sys.executable, "PM_OLARAK": "", "PM_TEST": "1"}


def test_rehber_yayinla_yayimlar_ayar_degismez(tmp_path, rehber):
    env = _yayin_ortam(tmp_path)
    gelen = tmp_path / "rehber_gelen.html"; shutil.copyfile(rehber, gelen)
    r = _kos("rehber_yayinla.sh", env, str(gelen))
    assert r.returncode == 0, r.stdout + r.stderr
    url = re.search(r"kendi telefonunuzda açın: (\S+)", r.stdout).group(1)
    anahtar = re.fullmatch(rf"https://{re.escape(ALAN)}/rehber/([A-Za-z0-9_-]{{22}})/", url).group(1)
    data = Path(env["PM_KOK"]) / "data"
    assert (data / "yayin" / "rehber" / anahtar / "index.html").read_bytes() == rehber.read_bytes()
    assert "denetim tamam: " in r.stdout and "PM_TEST: HTTP denetimi atlandı" in r.stdout and gelen.is_file()
    assert (data / "settings.json").read_text(encoding="utf-8") == "{}"


def test_rehber_yayinla_bozuk_dosyada_durur_hicbir_sey_yayimlanmaz(tmp_path, rehber):
    env = _yayin_ortam(tmp_path)
    gelen = tmp_path / "rehber_gelen.html"
    gelen.write_bytes(rehber.read_bytes().replace(b"</title>", "</title><p>0532 123 45 67</p>".encode()))
    r = _kos("rehber_yayinla.sh", env, str(gelen))
    assert r.returncode == 1 and "DUR: dosya rehber denetiminden geçmedi: telefon numarasına benzeyen 1 dizge var" in r.stderr
    assert "yayımlanmadı." in r.stdout and list((Path(env["PM_KOK"]) / "data" / "yayin" / "rehber").iterdir()) == []


def test_rehber_yayinla_dizin_yoksa_ve_dosya_yoksa_durur(tmp_path, rehber):
    env = _yayin_ortam(tmp_path, dizin=False)
    r = _kos("rehber_yayinla.sh", env, str(rehber))
    assert r.returncode == 1 and "yayin/rehber yok" in r.stderr
    r = _kos("rehber_yayinla.sh", env, str(tmp_path / "yok.html"))
    assert r.returncode == 1 and "dosya yok" in r.stderr
    r = _kos("rehber_yayinla.sh", env)
    assert r.returncode == 2 and "kullanım" in r.stderr


def test_rehber_yayinla_nginx_konumu_yoksa_durur(tmp_path, rehber):
    env = _yayin_ortam(tmp_path)
    conf = Path(env["PM_NGINX_DIR"]) / "sites-available" / "portman.conf"
    conf.write_text(re.sub(r'location ~ "\^/rehber/', 'location ~ "^/x/', conf.read_text(encoding="utf-8")), encoding="utf-8")
    r = _kos("rehber_yayinla.sh", env, str(rehber))
    assert r.returncode == 1 and "/rehber/ konumu yok" in r.stderr


# ───────────────────────── nginx (yerel nginx varsa) ─────────────────────────
def _bos_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def nginx_sunucu(tmp_path_factory, rehber):
    if not shutil.which("nginx") or not shutil.which("openssl"):
        pytest.skip("yerel nginx ya da openssl yok")
    import tempfile                                                # nginx işçisi root değil (nobody/www-data): yol başkasına geçilebilir olmalı
    d = Path(tempfile.mkdtemp(prefix="pm_rehber_ngx_", dir="/var/tmp" if Path("/var/tmp").is_dir() else None)); d.chmod(0o755)
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
    anahtar = RY.yayinla(rehber.read_bytes(), data / "yayin" / "rehber", TABAN)["anahtar"]
    r = subprocess.run(["nginx", "-e", str(d / "error.log"), "-c", str(d / "nginx.conf")], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"nginx başlatılamadı: {r.stderr.strip()[-200:]}")
    time.sleep(0.5)
    ctx = ssl.create_default_context(cafile=str(le / "fullchain.pem")); ctx.check_hostname = False
    yield {"port": p443, "ctx": ctx, "anahtar": anahtar, "sayfa": rehber, "log": d / "access.log", "hata_log": d / "error.log", "kok": d}
    subprocess.run(["nginx", "-e", str(d / "error.log"), "-c", str(d / "nginx.conf"), "-s", "stop"], capture_output=True)


def _iste(s: dict, yol: str, yontem: str = "GET") -> tuple[int, dict, bytes]:
    c = http.client.HTTPSConnection("127.0.0.1", s["port"], context=s["ctx"], timeout=10)
    c.request(yontem, yol, headers={"Host": ALAN})
    r = c.getresponse(); govde = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, govde


def test_nginx_yalniz_anahtarli_rehberi_sunar(nginx_sunucu):
    s, k = nginx_sunucu, nginx_sunucu["anahtar"]
    kod, b, govde = _iste(s, f"/rehber/{k}/")
    assert kod == 200 and govde == s["sayfa"].read_bytes() and b["content-type"].startswith("text/html")
    assert b["content-security-policy"].startswith("default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net;")
    for h in ("strict-transport-security", "x-content-type-options", "x-frame-options", "referrer-policy", "x-robots-tag"):
        assert h in b, h
    assert _iste(s, f"/rehber/{k}/index.html")[0] == 200
    kod, b, _ = _iste(s, f"/rehber/{k}")
    assert kod == 301 and b["location"].endswith(f"/rehber/{k}/")
    for yol in ("/rehber/", "/rehber", f"/rehber/{'A' * 22}/", f"/rehber/{k}/rehber.html", f"/rehber/{k}/.index.html.yeni", f"/rehber/{k}x/",
                "/rehber/../settings.json", "/rehber/%2e%2e/settings.json", f"/3d/{k}/", f"/yayin/rehber/{k}/index.html", "/projects/gizli.json"):
        assert _iste(s, yol)[0] == 404, yol
    assert _iste(s, f"/rehber/{k}/", "POST")[0] == 405
    time.sleep(0.2)
    assert k not in s["log"].read_text(encoding="utf-8").replace(f"/yayin/rehber/{k}/", "")   # /rehber/ yolları erişim günlüğüne anahtarsız
    hata = s["hata_log"].read_text(encoding="utf-8") if s["hata_log"].exists() else ""
    assert k not in hata and "A" * 22 not in hata, hata[-500:]


def test_telefonda_rehber_acilir(nginx_sunucu, tmp_path):
    """iPhone 13 öykünmesi (`testler/rehber_telefon.js`): nginx'in gerçek yapılandırmayla verdiği gövde ve başlıklar (CSP dahil) tarayıcıda
    açılır; CSP ihlali yok, sayfa hatası yok, sahne (canvas) çizilir, adımlar ilerler. three.js 0.160.0 jsDelivr adresinden istenir,
    THREE_DIR'den karşılanır. Node, Playwright ve THREE_DIR yoksa atlanır (CI'da kalan işte kurulu)."""
    from araclar.paket.rehber import iz
    if iz.hazir():
        pytest.skip(f"telefon öykünmesi: {iz.hazir()}")
    s = nginx_sunucu
    kod, basliklar, govde = _iste(s, f"/rehber/{s['anahtar']}/")
    assert kod == 200 and govde == s["sayfa"].read_bytes()
    (tmp_path / "govde.html").write_bytes(govde)
    (tmp_path / "basliklar.json").write_text(json.dumps({k: v for k, v in basliklar.items() if k not in ("content-length", "connection")}), encoding="utf-8")
    cikti = tmp_path / "telefon.json"; ekran = Path(os.environ.get("PM_REHBER_EKRAN") or tmp_path / "telefon.png")
    r = subprocess.run(["node", str(KOK / "testler" / "rehber_telefon.js"), f"https://{ALAN}/rehber/{s['anahtar']}/", str(tmp_path / "govde.html"),
                        str(tmp_path / "basliklar.json"), str(ekran), str(cikti)], capture_output=True, text=True, timeout=300, cwd="/tmp")
    assert r.returncode == 0, r.stderr[-2000:]
    t = json.loads(cikti.read_text(encoding="utf-8"))
    assert t["http"] == 200 and t["csp_basligi"] == basliklar["content-security-policy"]
    assert "bekleme_hatasi" not in t, t
    assert t["csp"] == [] and t["hatalar"] == [] and t["disari"] == [], t
    assert t["baslik"].endswith(" Montaj Rehberi") and t["N"] > 1 and t["adim"] and t["son_adim"] and t["tuval"] and min(t["tuval"]) > 0
    assert t["genislik"] == 390                       # iPhone 13: telefon düzeni (Lokman 9 Kasım 13:36 kartı "Evet, telefon düzeni"); ayarsız 980
    assert ekran.stat().st_size > 10_000
