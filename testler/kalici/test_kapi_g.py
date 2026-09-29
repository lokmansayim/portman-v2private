"""Kapı G (İE-02) betikleri: Postgres yedeği ve her adımdan sonraki salt okunur durum/kanıt. Gerçek Postgres, kayıtlı çıkarım,
sahte WhatsApp ve sahte hosting; VPS'teki gibi 'bash -s' ile ve girdiyi yutan bir sarmalayıcıyla koşulur. Hiçbir çıktıda numara,
mesaj metni, WhatsApp kimliği ya da anahtar yok; yedek var olanın üzerine yazmaz."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import time

import pytest

from conftest import ADMIN, KOK, NUMARA_A, dsn, mesaj, talep

import kalici

T_P6001 = talep(ozet="P6001 aynalı", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}])
T_ONAY = talep("onay", "onay")
GIZLI = "gizlimetin-onaylıyorum"


def _kos(betik: str, o: dict) -> subprocess.CompletedProcess:
    with open(KOK / "vps" / betik, "rb") as f:
        return subprocess.run(["bash", "-s"], stdin=f, capture_output=True, text=True, env=o, timeout=120)


def _temiz(o: str, *gizli: str) -> None:
    for s in (NUMARA_A, "wamid.", GIZLI, *gizli):
        assert s not in o, s


@pytest.fixture
def ortam(tmp_path, depo):
    from sahte_hosting import SahteHosting
    tok = os.urandom(32).hex()
    h = SahteHosting(tmp_path / "hosting", tok); url = h.basla()
    home = tmp_path / "home"; (home / "logs").mkdir(parents=True); (home / "app").symlink_to(KOK / "kanal")
    (home / "logs" / "agent.log").write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} iş alındı → Postgres abc kimden …0101 tür text\n")
    env = tmp_path / "agent.env"; env.write_text(f"PORTMAN_API_URL={url}\nPORTMAN_API_TOKEN={tok}\n")
    bin_ = tmp_path / "bin"; bin_.mkdir()
    (bin_ / "yutan").write_text('#!/usr/bin/env bash\ncat > /dev/null\nexec "$@"\n'); (bin_ / "yutan").chmod(0o755)
    (bin_ / "systemctl").write_text('#!/usr/bin/env bash\nif [[ " $* " == *" --value "* ]]; then echo 0; else echo ActiveState=active; fi\n')
    (bin_ / "systemctl").chmod(0o755)
    host = dict(x.split("=", 1) for x in ADMIN.split())
    baglanti = f"-h {host.get('host', '127.0.0.1')} -p {host.get('port', '5432')} -U {host.get('user', 'postgres')}"
    o = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "PM_HOME": str(home), "PM_ENV": str(env), "PM_PY": os.sys.executable,
         "PM_OLARAK": f"{bin_ / 'yutan'} env PORTMAN_PG_DSN=postgresql://{host.get('user', 'postgres')}@{host.get('host', '127.0.0.1')}:"
                      f"{host.get('port', '5432')}/{depo.ad}",
         "PM_PSQL": f"psql -X -q -tA {baglanti}", "PM_PGDUMP": f"pg_dump {baglanti}", "PM_PGRESTORE": "pg_restore",
         "PM_DB": depo.ad, "PM_YEDEK": str(tmp_path / "yedek")}
    (tmp_path / "yedek").mkdir()
    yield {"o": o, "tok": tok, "tmp": tmp_path, "h": h, "home": home}
    h.dur()


def _plan_ve_onay(depo, wa):
    g = mesaj("P6001 aynalı gizlimetin", T_P6001)
    assert depo.mesaj_kaydet(g)
    assert kalici.bir_is(depo, {"llm": {"backend": "manuel"}, "patron_teknik_not": False}, "t")["eylem"] == "is_emri"
    kalici.gonder(depo, wa)
    time.sleep(1.1)
    o = mesaj(GIZLI, T_ONAY)
    assert depo.mesaj_kaydet(o)
    assert kalici.bir_is(depo, {"llm": {"backend": "manuel"}, "patron_teknik_not": False}, "t")["gerekce"] == "plan onaylandı"
    kalici.gonder(depo, wa)
    with depo.baglan() as c:                        # canlıdaki gibi ölçülmüş token'lar (manuel arka uçta 0)
        ids = [r["id"] for r in c.execute("SELECT id FROM isler ORDER BY id")]
        for i, (gi, co, tk) in zip(ids, [(5280, 337, 0), (5300, 100, 1)]):
            c.execute("UPDATE isler SET cikarim = jsonb_set(cikarim, '{meta}', %s::jsonb) WHERE id = %s",
                      (f'{{"backend": "anthropic", "model": "claude-opus-5-5", "girdi_token": {gi}, "cikti_token": {co}, "tekrar": {tk}, "sure_ms": 4000}}', i))
    return g, o


def test_durum_kanit_ve_maliyet_deger_yazmadan(ortam, depo, wa, hizli_motor):
    bas = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 5))
    g, o = _plan_ve_onay(depo, wa)
    r = _kos("kapi_g_durum.sh", {**ortam["o"], "PM_BASLANGIC": bas})
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    _temiz(out, ortam["tok"], g["id"], o["id"])
    iz = hashlib.md5(g["id"].encode()).hexdigest()[:10]
    assert f"mesaj {iz}" in out and "eylem is_emri" in out and "onay denetimi: kabul True" in out
    assert "LLM claude-opus-5-5 · çağrı 1 · 5280+337 token" in out and "çağrı 2 · 5300+100 token · tekrar EVET" in out
    # 5280×4 + 337×20 = 0,027860 $; ikincisi tekrarlı: (5300×4 + 100×20)×2 = 0,046400 $ → 0,0743
    assert "Patron mesajı 2/7 · LLM çağrısı 3/9 (öz-test dahil; token'ı bilinmeyen 0) · 10580 giriş + 437 çıkış token · maliyet ≈ 0.0743 $ / 0,30 $" in out
    assert "giden WhatsApp 3/12" in out and "açık iş 0 · mesaj başına en çok iş 1" in out
    assert "onaylandi" in out and "PDF Portman_" in out
    r2 = _kos("kapi_g_durum.sh", {**ortam["o"], "PM_BASLANGIC": ""})
    assert "DUR: PM_BASLANGIC" in r2.stdout


def test_yedek_yeni_dosya_okunur_ve_uzerine_yazmaz(ortam, depo, wa, hizli_motor):
    _plan_ve_onay(depo, wa)
    o = {**ortam["o"], "PM_AD": "portman-g-oncesi-20260929"}
    r = _kos("kapi_g_yedek.sh", o)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    _temiz(out, ortam["tok"])
    dosya = ortam["tmp"] / "yedek" / "portman-g-oncesi-20260929.dump"
    assert f"sha256: {hashlib.sha256(dosya.read_bytes()).hexdigest()}" in out and "pg_restore ile okunuyor: evet" in out
    assert "isler" in out and "revizyonlar 1" in out
    once = dosya.read_bytes()
    r2 = _kos("kapi_g_yedek.sh", o)
    assert r2.returncode == 1 and "üzerine yazılmaz" in r2.stdout and dosya.read_bytes() == once
    r3 = _kos("kapi_g_yedek.sh", {**ortam["o"], "PM_AD": "../baska"})
    assert r3.returncode == 1 and "biçimi yanlış" in r3.stdout


def test_teshis_deger_yazmadan(ortam, depo, wa, hizli_motor):
    bas = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 5))
    g, o = _plan_ve_onay(depo, wa)
    r = _kos("kapi_g_teshis.sh", {**ortam["o"], "PM_BASLANGIC": bas})
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    _temiz(out, ortam["tok"], g["id"], o["id"])
    assert "LLM niyet yeni_talep/yuksek · dolu alanlar ['katalog_kodu', 'varyantlar']" in out and "LLM varyantlar: ['ayna_x']" in out
    assert "-- konuşma (şimdi): aşama onaylandi" in out and "-- revizyon PM-TSTA-" in out and "r01 (onaylandi)" in out


def test_durum_bu_turdaki_oz_testi_sayar_oncekini_saymaz(ortam, depo, wa, hizli_motor):
    """Yeniden deneme turu: yükleme öncesindeki andan sonra koşan paket öz-testi 1 LLM çağrısı olarak sayaçlara girer."""
    import json
    bas_t = time.time() - 5
    bas = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(bas_t))
    veri = ortam["home"] / "data"; veri.mkdir()
    st = {"state": "passed", "surum": "kanal-v1.2-20260929-2052", "started_at": int(bas_t) - 3600, "finished_at": int(bas_t) - 3590,
          "adimlar": {"llm": {"passed": True, "model": "claude-opus-5-5", "girdi_token": 5309, "cikti_token": 488, "tekrar": 0, "ozet": "gizliozet"}}}
    (veri / "self-test-result.json").write_text(json.dumps(st))
    _plan_ve_onay(depo, wa)
    out = _kos("kapi_g_durum.sh", {**ortam["o"], "PM_BASLANGIC": bas}).stdout
    assert "paket öz-testi" not in out and "LLM çağrısı 3/9" in out            # önceki paketin öz-testi bu tura girmez
    st["started_at"] = int(bas_t) + 2; st["finished_at"] = int(bas_t) + 20
    (veri / "self-test-result.json").write_text(json.dumps(st))
    out = _kos("kapi_g_durum.sh", {**ortam["o"], "PM_BASLANGIC": bas}).stdout
    assert "-- paket öz-testi (bu turda): passed · sürüm kanal-v1.2-20260929-2052 · LLM claude-opus-5-5 · çağrı 1 · 5309+488 token · tekrar hayır" in out
    # 0,0743 + 5309×4/1M + 488×20/1M (0,021236 + 0,00976) = 0,1053
    assert "LLM çağrısı 4/9 (öz-test dahil; token'ı bilinmeyen 0) · 15889 giriş + 925 çıkış token · maliyet ≈ 0.1053 $ / 0,30 $" in out
    assert "gizliozet" not in out


def test_paket_denetimi_deger_yazmadan(ortam):
    """kapi_g2_paket.sh: kurulu paket, dosya dosya karşılaştırma, karar.py özeti, öz-test, korunan ayarların adları, hosting paketi."""
    import io, json, zipfile
    home, tmp = ortam["home"], ortam["tmp"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("worker.py", "# işçi\n"); z.writestr("beyin/karar.py", "# karar\n"); z.writestr("agent.py", "# ajan\n"); z.writestr("SURUM.txt", "kanal-v1.2-deneme\n")
    ham = buf.getvalue(); sha = hashlib.sha256(ham).hexdigest(); karar = hashlib.sha256(b"# karar\n").hexdigest()
    (home / "app").unlink()
    (home / "pkg").mkdir(); (home / "pkg" / f"{sha}.zip").write_bytes(ham); (home / "pkg" / ("e" * 64 + ".zip")).write_bytes(b"eski")
    with zipfile.ZipFile(io.BytesIO(ham)) as z:
        z.extractall(home / "app")
    (home / "app" / "PACKAGE_SHA256").write_text(sha); (home / "app" / "beyin" / "__pycache__").mkdir(); (home / "app" / "beyin" / "__pycache__" / "k.pyc").write_bytes(b"x")
    (home / "app.old").mkdir(); (home / "app.old" / "PACKAGE_SHA256").write_text("e" * 64); (home / "app.old" / "SURUM.txt").write_text("kanal-v1.2-eski\n")
    (home / "agent.py").write_text("# ajan\n")
    (home / "data").mkdir()
    (home / "data" / "self-test-result.json").write_text(json.dumps({"state": "passed", "surum": "kanal-v1.2-deneme", "started_at": int(time.time()), "finished_at": int(time.time()),
        "sure_s": 9, "adimlar": {"beyin_harness": {"passed": True}, "llm": {"passed": True, "backend": "anthropic", "model": "claude-opus-5-5", "girdi_token": 5309,
        "cikti_token": 488, "tekrar": 0, "sure_ms": 4000, "niyet": "yeni_talep", "katalog_kodu": "P6001", "ozet": "gizliozet"}}}))
    bas = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 5))
    (home / "logs" / "agent.log").write_text(f"{time.strftime('%Y-%m-%d %H:%M:%S')} paket güncelleniyor: kanal-v1.2-deneme {sha[:12]} {len(ham)} B\n"
                                             f"{time.strftime('%Y-%m-%d %H:%M:%S')} iş alındı → Postgres abc kimden …0101 tür text\n")
    etc = tmp / "etc"; (etc / "portman").mkdir(parents=True); (etc / "portman" / "pg.env").write_text("PORTMAN_PG_DSN=dbname=portman\n")
    (etc / "systemd" / "system" / "portman-agent.service.d").mkdir(parents=True); (etc / "systemd" / "system" / "portman-agent.service.d" / "kalici.conf").write_text("[Service]\n")
    gizli = "sk-ant-gizlideger-0123456789"
    env = Path(ortam["o"]["PM_ENV"]); env.write_text(env.read_text() + f"ANTHROPIC_API_KEY={gizli}\n")
    from sahte_hosting import SahteHosting
    h = ortam["h"]; h.settings = lambda: {**SahteHosting.settings(h), "package": {"sha256": sha, "size": len(ham), "surum": "kanal-v1.2-deneme"}}
    o = {**ortam["o"], "PM_ETC": str(etc), "PM_BEKLENEN": sha, "PM_KARAR": karar, "PM_BASLANGIC": bas}
    r = _kos("kapi_g2_paket.sh", o)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    _temiz(out, ortam["tok"], gizli, "gizliozet", sha[16:])
    assert f"-- kurulu paket: {sha[:16]}… · beklenenle aynı: EVET · sürüm kanal-v1.2-deneme" in out
    assert "pakette 4 dosya · kurulu dizinle birebir aynı 4 · farklı ya da eksik [] · pakette olmayan []" in out
    assert "beyin/karar.py: " + karar[:16] + "… · beklenenle aynı: EVET" in out and "çalışan agent.py paketteki ile aynı: EVET" in out
    assert "app.old): eeeeeeeeeeeeeeee… · sürüm kanal-v1.2-eski" in out
    assert "-- öz-test: passed" in out and "LLM: anthropic/claude-opus-5-5 · 5309+488 token · tekrar 0" in out
    assert "anahtar adları ['PORTMAN_API_URL', 'PORTMAN_API_TOKEN', 'ANTHROPIC_API_KEY']" in out and "pg.env: var" in out and "kalici.conf: var" in out
    assert "worker vps · mode patron" in out and "hosting paketi: " + sha[:16] + "… · " + str(len(ham)) + " B · sürüm kanal-v1.2-deneme · beklenenle aynı: EVET" in out
    assert "paket güncelleniyor" in out and "iş alındı" not in out
    (home / "app" / "beyin" / "karar.py").write_text("# başka\n")
    out = _kos("kapi_g2_paket.sh", o).stdout
    assert "farklı ya da eksik ['beyin/karar.py']" in out and "beklenenle aynı: HAYIR" in out
    out = _kos("kapi_g2_paket.sh", {**o, "PM_BEKLENEN": "f" * 64}).stdout
    assert "-- kurulu paket: " + sha[:16] + "… · beklenenle aynı: HAYIR" in out and "zip YOK" in out
    assert "DUR: PM_BEKLENEN" in _kos("kapi_g2_paket.sh", {**o, "PM_BEKLENEN": ""}).stdout
