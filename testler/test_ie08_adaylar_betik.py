"""BK-08 madde 5 · `vps/ie08_adaylar.sh` kuru koşusu (Postgres'siz, sunucusuz; `PM_*` ile yerel kopyada):
- kuru koşu "artık bu adayları sunar" demez, hiçbir şeyin yazılmadığını söyler (13 Ekim akşamı canlı kuru koşu bunu yanlış söylüyordu);
- betik stdin'le gönderilse bile Python çağrısı betiğin kalanını yutmaz (`< /dev/null`; 13 Ekim 17:40 UTC'de boruyla gönderilen betik
  yazma adımında takılmıştı; başlıktaki örnek artık sunucudaki kopyayı `ssh -n … timeout 120 bash …` ile koşar)."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
BETIK = KOK / "vps" / "ie08_adaylar.sh"


def _ortam(tmp_path: Path) -> dict:
    e = dict(os.environ)
    e.update(PM_KOK=str(tmp_path / "yok"), PM_ETC=str(tmp_path / "etc"), PM_PYTHON=sys.executable, PM_PG_DSN="dbname=kullanilmaz", PM_OLARAK="")
    return e


def test_kuru_kosu_yazmadigini_soyler(tmp_path):
    r = subprocess.run(["bash", str(BETIK), "--kuru", "Ç8801,Ç8801K", "Lokman", "2026-10-14", "not", "paket"],
                       capture_output=True, text=True, env=_ortam(tmp_path), timeout=120)
    assert r.returncode == 0, r.stderr
    assert "KURU: 2 kayıt yazılacak" in r.stdout and "hiçbir şey yazılmadı" in r.stdout
    assert "artık bu adayları sunar" not in r.stdout
    assert "Lokman" not in r.stdout                                             # ad çıktıya girmez (yalnız ilk harf)


def test_stdin_ile_gonderilse_de_kalan_satirlar_yutulmaz(tmp_path):
    metin = BETIK.read_text(encoding="utf-8") + "\necho SONRAKI_SATIR_CALISTI\n"
    r = subprocess.run(["bash", "-s", "--", "--kuru", "Ç8801", "Lokman", "2026-10-14"], input=metin, capture_output=True, text=True,
                       env=_ortam(tmp_path), cwd=str(KOK / "vps"), timeout=120)
    assert r.returncode == 0, r.stderr
    assert "hiçbir şey yazılmadı" in r.stdout and "SONRAKI_SATIR_CALISTI" in r.stdout
