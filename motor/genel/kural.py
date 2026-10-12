"""Kural seti: hangi dosyanın okunacağı tek yerden.

Güncel set kural kitabındaki `kurallar/liste/kurallar.json`dır (depo kökünde). Kural setleri veridir ve sürümlüdür: bir liste, hazırlandığı
günkü setle yeniden üretilebilmelidir. Eski bir set `PORTMAN_KURALLAR` ortam değişkeniyle seçilir (dosya yolu); `kurallar/liste/setler/`
altında eski setlerin kopyası durur (ör. 7 Ekim 2026 03:46 kıyası `setler/0.12.json` ile üretilir: `../2026-10-06_kor_test/kiyas_kos.sh`).
Kodda yeni bir davranış her zaman kural dosyasındaki bir anahtara bağlanır; anahtar yoksa eski davranış sürer.
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

BURADA = Path(__file__).resolve().parent
KITAP = BURADA.parents[1] / "kurallar" / "liste"          # kural kitabının liste bölümü (10 Ekim 2026'dan beri; önce bu klasördeydi)


def yol() -> Path:
    secilen = os.environ.get("PORTMAN_KURALLAR")
    return Path(secilen).expanduser().resolve() if secilen else KITAP / "kurallar.json"


def oku() -> dict:
    y = yol()
    if not y.is_file():
        raise SystemExit(f"Kural dosyası yok: {y} (PORTMAN_KURALLAR yanlış olabilir).")
    return json.loads(y.read_text(encoding="utf-8"))


@contextlib.contextmanager
def secili(set_yolu: Path | str | None):
    """Blok boyunca kural setini seçer (`PORTMAN_KURALLAR`); çıkışta eski değeri geri koyar. `None` ise dokunmaz.
    Tek yer: uret, bayi görseli ve şablon paftası aynı seçimi bununla yapar (İE-08)."""
    eski = os.environ.get("PORTMAN_KURALLAR")
    if set_yolu is not None:
        os.environ["PORTMAN_KURALLAR"] = str(Path(set_yolu).expanduser().resolve())
    try:
        yield
    finally:
        if set_yolu is not None:
            if eski is None:
                os.environ.pop("PORTMAN_KURALLAR", None)
            else:
                os.environ["PORTMAN_KURALLAR"] = eski
