"""İE-25 · çatı seçiminin hedef örneği (D-28 madde 2–3): `testler/cati_secimi/ornek.py`'nin bugünkü çıktısı ↔ Lokman'ın onayladığı
`hedef.json` (1 Kasım 2026; dayanak dosyanın `onay` alanında).

Örnek: "88 m² 2+1 tek kat çelik" → alan seti (her plan bir kez) → Ç8801 seçilir → "Çatı seçin" (katalog, K, L) → seçilen çatıyla r01.
Kıyaslanan: iki setin bayiye giden mesajı, düğmeleri ve bileşik görselinin içerik izi (PNG baytı), alan setinin "seçildi" kapanışı, üç
çatının r01 kararı (kod, revizyon, tanım dosyası ve sha, mesaj). r01 çizimi (`--r01`) kıyasa girmez; genel motorun izleri ayrıca dondurulu.
Fark bilerek yapıldıysa `hedef.json` yalnız Lokman'ın onayıyla ve gerekçeli kararla yeniden donar (D-02); testi geçirmek için hedef
değiştirilmez. LLM, WhatsApp ve Postgres yok.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from testler.cati_secimi import ornek  # noqa: E402

HEDEF = Path(__file__).with_name("hedef.json")


def test_hedef_kaydi_onayli():
    h = json.loads(HEDEF.read_text(encoding="utf-8"))
    onay = h["onay"]
    assert onay["kim"] == "Lokman" and onay["tarih"] and onay["dayanak"], onay
    assert onay["komut"].startswith("python -m testler.cati_secimi.ornek"), onay


def test_cati_seti_hedefle_ayni(tmp_path):
    h = json.loads(HEDEF.read_text(encoding="utf-8"))
    o = ornek.uret(tmp_path)
    o.pop("_dosyalar")
    beklenen = h["ozet"]
    farklar = [a for a in sorted(set(o) | set(beklenen)) if o.get(a) != beklenen.get(a)]
    assert not farklar, {a: {"simdi": o.get(a), "hedef": beklenen.get(a)} for a in farklar}
