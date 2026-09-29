"""Kapı G (İE-02) betikleri: Postgres yedeği ve her adımdan sonraki salt okunur durum/kanıt. Gerçek Postgres, kayıtlı çıkarım,
sahte WhatsApp ve sahte hosting; VPS'teki gibi 'bash -s' ile ve girdiyi yutan bir sarmalayıcıyla koşulur. Hiçbir çıktıda numara,
mesaj metni, WhatsApp kimliği ya da anahtar yok; yedek var olanın üzerine yazmaz."""
from __future__ import annotations

import hashlib
import os
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
    yield {"o": o, "tok": tok, "tmp": tmp_path}
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
    assert "Patron mesajı 2/7 · LLM çağrısı 3/10 (token'ı bilinmeyen 0) · 10580 giriş + 437 çıkış token · maliyet ≈ 0.0743 $" in out
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
