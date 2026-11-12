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
    """Alt süreç stdin okursa (13 Ekim'deki takılmanın olası yolu: `sudo`, `psql` ya da Python), betik stdin'le gönderildiğinde kalanını
    yutar. Sahte Python stdin'i sonuna kadar okur: `< /dev/null` yoksa sonraki satırlar hiç koşmaz (bu test o yönlendirmeyi korur)."""
    sahte = tmp_path / "sahte_python"
    sahte.write_text("#!/usr/bin/env bash\ncat > /dev/null\necho \"KURU: 1 kayıt yazılacak (sahte)\"\n", encoding="utf-8")
    sahte.chmod(0o755)
    metin = BETIK.read_text(encoding="utf-8") + "\necho SONRAKI_SATIR_CALISTI\n"
    r = subprocess.run(["bash", "-s", "--", "--kuru", "Ç8801", "Lokman", "2026-10-14"], input=metin, capture_output=True, text=True,
                       env={**_ortam(tmp_path), "PM_PYTHON": str(sahte)}, cwd=str(KOK / "vps"), timeout=120)
    assert r.returncode == 0, r.stderr
    assert "hiçbir şey yazılmadı" in r.stdout and "SONRAKI_SATIR_CALISTI" in r.stdout


def test_prefabrik_kodlari_prefabrik_kaydindan_okunur(tmp_path):
    """İE-36/İE-37 (D-80, D-83): sekiz ev ve PA-06'nın çatı seçenekleri `adaylar_prefabrik.json`'da; betik `adaylar.json`'u verseydi
    K-A10 "olmayan kod" diye dururdu (12 Kasım 2026, sürüm hazırlığı)."""
    r = subprocess.run(["bash", str(BETIK), "--kuru", "PA-01,PA-02,PA-03,PA-04,PA-05,PA-06,PA-07,PA-08,PA-06-K,PA-06-C", "Lokman", "2026-11-12"],
                       capture_output=True, text=True, env=_ortam(tmp_path), timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "KURU: 10 kayıt yazılacak (PA01, PA02, PA03, PA04, PA05, PA06, PA07, PA08, PA06K, PA06C)" in r.stdout
    assert "hiçbir şey yazılmadı" in r.stdout and "Lokman" not in r.stdout


def test_celik_ve_banka_kodu_bugunku_kayittan(tmp_path):
    r = subprocess.run(["bash", str(BETIK), "--kuru", "KT04", "Lokman", "2026-11-12"], capture_output=True, text=True, env=_ortam(tmp_path), timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "KURU: 1 kayıt yazılacak (KT04)" in r.stdout


def test_prefabrik_ve_celik_kodu_ayni_kosuda_durur(tmp_path):
    r = subprocess.run(["bash", str(BETIK), "--kuru", "PA-04,Ç8801", "Lokman", "2026-11-12"], capture_output=True, text=True, env=_ortam(tmp_path), timeout=120)
    assert r.returncode == 1
    assert "DUR: prefabrik (PA) ve çelik kodları aynı koşuda verilmez" in r.stderr and "KURU" not in r.stdout
