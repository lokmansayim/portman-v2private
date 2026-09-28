"""T3 (gerçek süreç, gerçek Motor): işleyici Motor çizim yaparken öldürülür (SIGKILL); yeniden başlayan işleyici işi bitirir.
Çıktı ve giden satırlar birer kez yazılır; LLM yeniden çağrılmaz (ikinci süreçte kayıtlı çıkarım kaynağı silinmiştir:
çağrılsaydı manuel arka uç hata verirdi). Süre: ~40 sn.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from conftest import AYAR, KANAL_VERI, KOK, mesaj, sorgu, talep, tek

import kalici

T_P6001 = talep(ozet="P6001 aynalı", katalog_kodu="P6001", varyantlar=[{"tur": "ayna_x", "aciklama": "aynalı"}])


def _isleyici(depo, ayar: Path) -> subprocess.Popen:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENAI", "ANTHROPIC"))}
    env.update(PORTMAN_PG_DSN=depo.dsn, PORTMAN_KANAL_DIR=str(KANAL_VERI))
    return subprocess.Popen([sys.executable, str(KOK / "kanal" / "kalici.py"), "isle", "--ayar", str(ayar), "--tek"],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def test_t3_motor_sirasinda_oldurulen_isleyici_yeniden_baslayinca_isi_bitirir(depo, wa, tmp_path):
    ayar = tmp_path / "ayar.json"
    ayar.write_text(json.dumps({**AYAR, "kira_sn": 3}), encoding="utf-8")
    g = mesaj("P6001 aynalı", T_P6001)
    assert depo.mesaj_kaydet(g)

    p1 = _isleyici(depo, ayar)
    son = time.time() + 60
    while time.time() < son and not tek(depo, "SELECT cikarim IS NOT NULL AS var FROM isler")["var"]:
        time.sleep(0.2)
    time.sleep(2.0)                                           # Motor çizimin ortasında (tek plan ~15 sn)
    assert p1.poll() is None, "işleyici erken bitti; Motor sırasında öldürülemedi"
    os.kill(p1.pid, signal.SIGKILL); p1.wait(10)

    j = tek(depo, "SELECT * FROM isler")
    assert (j["durum"], j["deneme"]) == ("isleniyor", 1)
    assert tek(depo, "SELECT count(*) n FROM giden")["n"] == 0
    assert tek(depo, "SELECT count(*) n FROM revizyonlar")["n"] == 0
    assert depo.konusma_oku(g["sender"]) == (None, 0)          # konuşma ilerlemedi

    with depo.baglan() as c:                                   # LLM'in (manuel arka uç) kaynağı silinir
        c.execute("UPDATE mesajlar SET ham = ham - 'test_cikarim' WHERE id = %s", (g["id"],))
    time.sleep(3.2)                                            # kira doldu
    p2 = _isleyici(depo, ayar)
    cikti, hata = p2.communicate(timeout=300)
    assert p2.returncode == 0, hata[-2000:]
    r = json.loads([l for l in cikti.splitlines() if l.startswith("{")][-1])
    assert (r["durum"], r["eylem"]) == ("bitti", "is_emri")

    j = tek(depo, "SELECT * FROM isler")
    assert (j["durum"], j["deneme"]) == ("bitti", 2)
    satirlar = sorgu(depo, "SELECT kind, dosya, sha256 FROM giden ORDER BY sira")
    assert [s["kind"] for s in satirlar] == ["text", "document"]
    pdf = Path(satirlar[1]["dosya"])
    assert pdf.read_bytes()[:5] == b"%PDF-" and hashlib.sha256(pdf.read_bytes()).hexdigest() == satirlar[1]["sha256"]
    rev = tek(depo, "SELECT * FROM revizyonlar")
    assert rev["dogrulandi"] is True and rev["durum"] == "onay_bekliyor"

    assert kalici.gonder(depo, wa)["iletildi"] == 2
    assert depo.mesaj_kaydet(g) is False                       # aynı mesaj yeniden geldi
    assert kalici.bir_is(depo, AYAR, "ucuncu") is None
    assert tek(depo, "SELECT count(*) n FROM isler")["n"] == 1 and len(wa.gonderilen) == 2
