"""Kapı F (İE-02) betikleri: hosting yedeğinin özeti, Postgres'e aktarma, karşılaştırma, kalıcı modu açma, son doğrulama.

Sahte hosting yedeği (state.json, durum/, projects/), gerçek Postgres, sahte hosting API'si ve sahte systemctl ile. Hiçbir çıktıda
telefon numarası, mesaj metni, WhatsApp kimliği ya da anahtar yok; ön koşul tutmazsa hiçbir şey değişmez."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from conftest import ADMIN, KOK, _admin, dsn

PROJE = "PM-PATRON-20260929-33807"
PATRON = "900000000777"                   # gerçek olmayan deneme numaraları
BAYI = "900000000888"
GIZLI_METIN = "Yeni talep: P6001 aynalı olsun gizlimetin"
BETIK = KOK / "vps" / "kapi_f.py"


def _yedek(kok: Path, veri: Path, kuyruk: bool = False, islenmekte: bool = False, gonderimde: bool = False) -> Path:
    """Hosting'in kanal/ kopyası (yedek) ve VPS'in veri dizini; E'deki gibi: Patron'un r01'i, PDF iki yerde."""
    kanal = kok / "kanal"; (kanal / "durum").mkdir(parents=True)
    rk_h = kanal / "projects" / PROJE / "r01"; rk_h.mkdir(parents=True)
    rk_v = veri / "projects" / PROJE / "r01"; rk_v.mkdir(parents=True)
    pdf = b"%PDF-1.4\n% deneme r01\n"
    for rk in (rk_h, rk_v):
        (rk / f"Portman_{PROJE}_r01.pdf").write_bytes(pdf); (rk / f"Portman_{PROJE}_r01.dxf").write_bytes(b"0\nEOF\n")
    psha = hashlib.sha256(pdf).hexdigest()
    ie = {"is_emri_no": PROJE, "revizyon": 1, "katalog_kodu": "P6001"}
    (kanal / "durum" / f"{PATRON}.json").write_text(json.dumps(
        {"asama": "onay_bekliyor", "taslak": {}, "soru_sayisi": 0, "revizyon": 0, "son_soru_alani": None, "son_is_emri": ie,
         "gecmis": [{"yon": "gelen", "metin": GIZLI_METIN}], "guncellendi": 1759097829.25}, ensure_ascii=False), encoding="utf-8")
    (kanal / "durum" / f"{BAYI}.json").write_text(json.dumps(
        {"asama": "topluyor", "taslak": {"ozet": "x"}, "son_soru_alani": "D-01", "bekleyen_zamani": 1758500000, "revizyon": 0,
         "son_is_emri": None, "gecmis": []}, ensure_ascii=False), encoding="utf-8")
    e_id = "wamid.E" + "A" * 40
    inbound = {
        e_id: {"sender": PATRON, "role": "patron", "bayi": {"kod": "PATRON", "ad": "Patron", "rol": "patron"}, "type": "text",
               "text": GIZLI_METIN, "timestamp": 1759097803, "received_at": 1759097803, "state": "done", "outbound_ids": [f"{e_id}#1", f"{e_id}#2"],
               "result": {"eylem": "is_emri", "is_emri_no": PROJE, "revizyon": 1, "ozet": "gizli özet",
                          "cizim": {"passed": True, "pdf": str(rk_v / f"Portman_{PROJE}_r01.pdf"), "pdf_sha256": psha}}},
        "wamid.ESKI" + "B" * 30: {"sender": BAYI, "role": "bayi", "bayi": {"kod": "B0888", "ad": "Deneme", "rol": "bayi"}, "type": "text",
                                   "text": "eski gizlimetin", "timestamp": 1758500000, "received_at": 1758500000, "state": "failed", "result": None},
        "selftest-1": {"sender": PATRON, "self_test": True, "state": "done", "text": "öz-test"},
    }
    if kuyruk:
        inbound["wamid.KUYRUK" + "C" * 30] = {"sender": PATRON, "role": "patron", "bayi": {"kod": "PATRON", "rol": "patron"}, "type": "text",
                                              "text": "kuyruk gizlimetin", "timestamp": int(time.time()) - 120, "received_at": int(time.time()) - 120,
                                              "state": "queued", "result": None}
    if islenmekte:
        inbound["wamid.YARIM" + "D" * 30] = {"sender": PATRON, "role": "patron", "type": "text", "text": "yarım", "timestamp": 1, "state": "processing"}
    outbound = {
        f"{e_id}#1": {"id": f"{e_id}#1", "inbound_id": e_id, "seq": 1, "kind": "text", "to": PATRON, "body": "gizli cevap",
                      "state": "delivered", "delivery_state": "delivered", "wamid": "wamid.OUT" + "E" * 30},
        f"{e_id}#2": {"id": f"{e_id}#2", "inbound_id": e_id, "seq": 2, "kind": "document", "to": PATRON, "body": f"{PROJE} r01",
                      "file": f"/home/hesap/portman_app/kanal/projects/{PROJE}/r01/Portman_{PROJE}_r01.pdf", "sha256": psha,
                      "state": "read", "delivery_state": "read", "wamid": "wamid.OUT" + "F" * 30},
    }
    if gonderimde:
        outbound["x#1"] = {"id": "x#1", "inbound_id": "wamid.ESKI" + "B" * 30, "seq": 1, "kind": "text", "state": "sending"}
    (kanal / "state.json").write_text(json.dumps({"inbound": inbound, "outbound": outbound}, ensure_ascii=False), encoding="utf-8")
    (kanal / "settings.json").write_text(json.dumps({"enabled": True, "worker": "off", "mode": "patron", "dry_run": False,
                                                     "llm": {"backend": "anthropic", "model": "claude-opus-5-5"}}), encoding="utf-8")
    return kanal


def _gizli_yok(cikti: str) -> None:
    for s in (PATRON, BAYI, "gizlimetin", "gizli cevap", "gizli özet", "wamid.", "aynalı olsun"):
        assert s not in cikti, s


def test_ozet_bosalma_kuyruk_ve_E_projesi_deger_yazmadan(tmp_path):
    kanal = _yedek(tmp_path / "h", tmp_path / "v", kuyruk=True)
    (kanal / "durum" / f"{BAYI}.json").write_text(json.dumps({"asama": "bos", "not": "sk-ant-api03-" + "Zx9" * 20}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(BETIK), "ozet", str(kanal), "--json", str(tmp_path / "o.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    o = r.stdout
    _gizli_yok(o); assert "Zx9Zx9" not in o and "sk-ant" not in o
    assert "worker': 'off'" in o and "claude-opus-5-5" in o
    assert "aktarılacak 2 {'basarisiz': 1, 'bitti': 1}" in o and "kuyrukta bırakılacak 1" in o and "öz-test/kimliksiz 1" in o
    assert "KUYRUKTA 1 mesaj: patron text" in o and "(LLM çağrısı olur)" in o
    assert "boşalma: tamam" in o and "1 tanesi LLM çağrısı doğurur" in o
    assert "konuşma: 1 · {'asama': 'onay_bekliyor', 'son_is_emri_rev': 1" in o
    assert "'konusmayla_ayni_kisi': True" in o and "'hosting_kopyasi_sha_ayni': True" in o and "'teslim': 'read'" in o
    assert "isabet 1 ['durum/<gizli>']" in o
    j = json.loads((tmp_path / "o.json").read_text())
    _gizli_yok(json.dumps(j, ensure_ascii=False))
    assert j["kaynak"]["gelen"]["kuyrukta"] == 1 and j["kaynak"]["e"]["gelen"]["pdf"] == f"Portman_{PROJE}_r01.pdf"


def test_ozet_bosalmamis_kuyrugu_gosterir(tmp_path):
    kanal = _yedek(tmp_path / "h", tmp_path / "v", islenmekte=True, gonderimde=True)
    r = subprocess.run([sys.executable, str(BETIK), "ozet", str(kanal)], capture_output=True, text=True)
    assert r.returncode == 0 and "boşalma: BİTMEDİ" in r.stdout and "işlenmekte 1" in r.stdout and "gönderimde (pending/uploading/sending) 1" in r.stdout


def _karsilastir(kanal, veri, ad):
    return subprocess.run([sys.executable, str(BETIK), "karsilastir", str(kanal), "--veri", str(veri)], capture_output=True, text=True,
                          env={**os.environ, "PORTMAN_PG_DSN": dsn(ad)})


def test_karsilastir_aktarimdan_sonra_birebir_ve_uyusmazligi_bulur(tmp_path, depo):
    from depo_aktar import ice_aktar
    kanal = _yedek(tmp_path / "h", tmp_path / "v")
    say = ice_aktar(depo, kanal, bos_olmali=True)
    assert say["konusma"] == 2 and say["mesaj"] == 2
    r = _karsilastir(kanal, tmp_path / "v", depo.ad)
    assert r.returncode == 0, r.stdout + r.stderr
    _gizli_yok(r.stdout)
    assert "kayıtlar birebir korundu" in r.stdout and "FARKLI" not in r.stdout
    assert "'vps_pdf_sha_ayni': True" in r.stdout and "projeler/revizyonlar kaydı: 0/0" in r.stdout
    # VPS'teki PDF değişirse ya da bir konuşma farklıysa: uyuşmazlık, çıkış 2
    (tmp_path / "v" / "projects" / PROJE / "r01" / f"Portman_{PROJE}_r01.pdf").write_bytes(b"%PDF-1.4\n% degisti\n")
    with depo.baglan() as c:
        c.execute("UPDATE konusmalar SET durum = durum || '{\"asama\": \"bos\"}'::jsonb WHERE durum->>'asama' = 'topluyor'")
    r = _karsilastir(kanal, tmp_path / "v", depo.ad)
    assert r.returncode == 2 and "UYUŞMAZLIK" in r.stdout
    assert "FARKLI · konuşmaların toplu özeti" in r.stdout and "FARKLI · E: VPS'teki PDF kayıttaki özetle aynı" in r.stdout
    _gizli_yok(r.stdout)


# ───────────────────────── VPS betikleri (sahte ev dizini, sahte hosting, sahte systemctl) ─────────────────────────
SAHTE_SYSTEMCTL = """#!/usr/bin/env bash
case "$1" in
  restart) printf '%s başladı vps-agent-v1.2 home %s api https://ornek.invalid/kanal_api.php mod kalıcı (Postgres)\\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$PM_HOME" >> "$PM_HOME/logs/agent.log"; echo restart >> "$PM_HOME/systemctl.log" ;;
  daemon-reload) echo daemon-reload >> "$PM_HOME/systemctl.log" ;;
  show) if [[ " $* " == *" --value "* ]]; then echo 0; else echo "ActiveState=active"; echo "SubState=running"; echo "MainPID=0"; fi ;;
esac
"""


@pytest.fixture
def ortam(tmp_path, sablon):
    from sahte_hosting import SahteHosting
    tok = os.urandom(32).hex()
    h = SahteHosting(tmp_path / "hosting", tok, worker="off"); url = h.basla()
    home = tmp_path / "home"; (home / "logs").mkdir(parents=True); (home / "data" / "pending").mkdir(parents=True)
    (home / "app").symlink_to(KOK / "kanal")
    (home / "agent.py").write_text('SURUM = "vps-agent-v1.2"\n')
    (home / "logs" / "agent.log").write_text("2026-09-29 00:47:41 başladı vps-agent-v1.2 home x api y mod dosya\n"
                                             "2026-09-29 01:16:43 iş alındı abc kimden …0777 tür text\n"
                                             "2026-09-29 01:17:09 iş bitti abc → is_emri 25.9 s giden: 2\n")
    env = tmp_path / "agent.env"; env.write_text(f"PORTMAN_API_URL={url}\nPORTMAN_API_TOKEN={tok}\nANTHROPIC_API_KEY=sk-ant-api03-{'Qw7' * 20}\n")
    gecis = tmp_path / "gecis"; gecis.mkdir()
    kanal = _yedek(gecis, home / "data")
    import shutil
    shutil.copytree(kanal / "durum", home / "data" / "durum")          # dosya modunda VPS'in kopyası
    (gecis / "kapi_f.py").write_bytes(BETIK.read_bytes())
    ad = "t_" + uuid.uuid4().hex[:12]
    with _admin() as c:
        c.execute(f"CREATE DATABASE {ad}")                 # boş: göç yok (canlıdaki gibi)
    bin_ = tmp_path / "bin"; bin_.mkdir(); (bin_ / "systemctl").write_text(SAHTE_SYSTEMCTL); (bin_ / "systemctl").chmod(0o755)
    host = dict(x.split("=", 1) for x in ADMIN.split())
    o = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "PM_TEST": "1", "PM_HOME": str(home), "PM_ENV": str(env),
         "PM_GECIS": str(gecis), "PM_PY": sys.executable, "PM_SAHIP": f"{os.getuid()}:{os.getgid()}", "PM_DB": ad,
         "PM_PSQL": f"psql -X -q -tA -h {host.get('host', '127.0.0.1')} -p {host.get('port', '5432')} -U {host.get('user', 'postgres')}",
         "PM_OLARAK": f"env PORTMAN_PG_DSN=postgresql://{host.get('user', 'postgres')}@{host.get('host', '127.0.0.1')}:{host.get('port', '5432')}/{ad} "
                      f"PORTMAN_KANAL_DIR={home / 'data'}",
         "PM_ETC": str(tmp_path / "etc"), "PM_DROPIN": str(tmp_path / "dropin"), "PM_BASLANGIC": "2000-01-01 00:00:00",
         "PM_BEKLENEN_STATE_SHA": hashlib.sha256((kanal / "state.json").read_bytes()).hexdigest()}
    (tmp_path / "etc").mkdir()
    yield {"o": o, "h": h, "ad": ad, "home": home, "kanal": kanal, "tok": tok, "tmp": tmp_path}
    h.dur()
    with _admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")


def _kos(betik: str, o: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(KOK / "vps" / betik)], capture_output=True, text=True, env=o, timeout=180)


def _tablo_sayisi(ad: str) -> int:
    import psycopg
    with psycopg.connect(dsn(ad)) as c:
        return c.execute("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'").fetchone()[0]


def _temiz(r: subprocess.CompletedProcess, tok: str) -> str:
    o = r.stdout + r.stderr
    _gizli_yok(o); assert tok not in o and "Qw7Qw7" not in o
    return o


def test_on_durum_salt_okunur(ortam):
    r = _kos("kapi_f_on.sh", ortam["o"])
    o = _temiz(r, ortam["tok"])
    assert "portman içindeki tablo sayısı: 0" in o and "worker off ✓" in o and "elde iş yok ✓" in o and "bekleyen sonuç 0 ✓" in o
    assert f"{PROJE}/r01/Portman_{PROJE}_r01.pdf" in o and "konuşması (VPS kopyası): aşama onay_bekliyor · r01" in o
    assert _tablo_sayisi(ortam["ad"]) == 0


def test_aktar_on_kosul_tutmazsa_hicbir_sey_yapmaz(ortam):
    o = ortam["o"]
    r = _kos("kapi_f_aktar.sh", {**o, "PM_BEKLENEN_STATE_SHA": "0" * 64})          # Mac'te doğrulanandan farklı kopya
    assert r.returncode == 1 and "DUR: kopyadaki state.json" in r.stdout and _tablo_sayisi(ortam["ad"]) == 0
    ortam["h"].worker = "vps"                                                     # işleyici durdurulmamış
    r = _kos("kapi_f_aktar.sh", o)
    assert r.returncode == 1 and "worker off değil" in r.stdout and _tablo_sayisi(ortam["ad"]) == 0
    ortam["h"].worker = "off"
    import psycopg                                                                # beklenmeyen dolu veritabanı
    with psycopg.connect(dsn(ortam["ad"]), autocommit=True) as c:
        c.execute("CREATE TABLE baska (x int)")
    r = _kos("kapi_f_aktar.sh", o)
    assert r.returncode == 1 and "boş değil" in r.stdout and _tablo_sayisi(ortam["ad"]) == 1
    _temiz(r, ortam["tok"])


def test_aktar_kalici_ac_ve_dogrula_uctan_uca(ortam):
    o = ortam["o"]
    r = _kos("kapi_f_aktar.sh", o)
    out = _temiz(r, ortam["tok"])
    assert r.returncode == 0, out
    assert "eksik göç yok" in out and "kayıtlar birebir korundu" in out and "aktarma tamam" in out
    assert '"konusma": 2' in out and '"mesaj": 2' in out
    # ikinci kez: veritabanı artık dolu → durur, hiçbir şeye dokunmaz
    r2 = _kos("kapi_f_aktar.sh", o)
    assert r2.returncode == 1 and "boş değil" in r2.stdout
    # kalıcı mod: worker off değilse açılmaz
    ortam["h"].worker = "vps"
    r3 = _kos("kapi_f_kalici_ac.sh", o)
    assert r3.returncode == 1 and "worker off değil" in r3.stdout and not (ortam["tmp"] / "etc" / "pg.env").exists()
    ortam["h"].worker = "off"
    r4 = _kos("kapi_f_kalici_ac.sh", o)
    out4 = _temiz(r4, ortam["tok"])
    assert r4.returncode == 0, out4
    assert "eksik_goc=[] konusma=2 acik_is=0" in out4 and "kalıcı mod AÇIK" in out4
    assert (ortam["tmp"] / "etc" / "pg.env").read_text() == "PORTMAN_PG_DSN=dbname=portman\n"
    assert f"EnvironmentFile={ortam['tmp'] / 'etc'}/pg.env" in (ortam["tmp"] / "dropin" / "kalici.conf").read_text()
    assert (ortam["home"] / "systemctl.log").read_text().split() == ["daemon-reload", "restart"]
    # ikinci kez açılmaz
    r5 = _kos("kapi_f_kalici_ac.sh", o)
    assert r5.returncode == 1 and "zaten var" in r5.stdout
    # son doğrulama (salt okunur)
    r6 = _kos("kapi_f_dogrula.sh", o)
    out6 = _temiz(r6, ortam["tok"])
    assert r6.returncode == 0, out6
    assert "'mod kalıcı (Postgres)': 1" in out6 and "açık iş: 0" in out6 and "kayıtlar birebir korundu" in out6
    assert "F'den sonra işlenen iş: 0" in out6 and "pg.env: " in out6 and "kalici.conf: VAR" in out6 and "No such file" not in out6


def test_vps_yedegi_anahtar_dosyasi_icermez_ve_uzerine_yazmaz(tmp_path):
    home = tmp_path / "home"; (home / "data" / "durum").mkdir(parents=True); (home / "app").mkdir()
    (home / "data" / "durum" / f"{PATRON}.json").write_text("{}"); (home / "app" / "worker.py").write_text("x = 1\n")
    (home / "agent.py").write_text('SURUM = "vps-agent-v1.2"\n')
    o = {**os.environ, "PM_HOME": str(home), "PM_YEDEK": str(tmp_path / "yedek")}
    r = subprocess.run(["bash", str(KOK / "vps" / "kapi_f_yedek.sh")], capture_output=True, text=True, env=o)
    assert r.returncode == 0, r.stderr
    arsiv = tmp_path / "yedek" / "opt-portman-ie02-f-20260929.tgz"
    assert f"sha256: {hashlib.sha256(arsiv.read_bytes()).hexdigest()}" in r.stdout and "durum/ 1 konuşma" in r.stdout
    assert "anahtar dosyası (agent.env/pg.env): 0" in r.stdout and PATRON not in r.stdout
    once = arsiv.read_bytes()
    r2 = subprocess.run(["bash", str(KOK / "vps" / "kapi_f_yedek.sh")], capture_output=True, text=True, env=o)
    assert r2.returncode == 1 and "üzerine yazılmaz" in r2.stdout and arsiv.read_bytes() == once
