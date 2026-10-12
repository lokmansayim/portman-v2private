"""Kural seti: hangi dosyanın okunacağı tek yerden.

Güncel set kural kitabındaki `kurallar/liste/kurallar.json`dır (depo kökünde). Kural setleri veridir ve sürümlüdür: bir liste, hazırlandığı
günkü setle yeniden üretilebilmelidir. Eski bir set `PORTMAN_KURALLAR` ortam değişkeniyle seçilir (dosya yolu); `kurallar/liste/setler/`
altında eski setlerin kopyası durur (ör. 7 Ekim 2026 03:46 kıyası `setler/0.12.json` ile üretilir: `../2026-10-06_kor_test/kiyas_kos.sh`).
Kodda yeni bir davranış her zaman kural dosyasındaki bir anahtara bağlanır; anahtar yoksa eski davranış sürer.
"""
from __future__ import annotations

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
