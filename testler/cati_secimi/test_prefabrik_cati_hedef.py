"""İE-37 (D-83) · prefabrik evde çatı seçiminin hedef örneği (D-28 madde 2–3): `testler/cati_secimi/ornek_prefabrik.py`'nin bugünkü
çıktısı ↔ Lokman'ın onayladığı `prefabrik_hedef.json` (12 Kasım 2026; dayanak dosyanın `onay` alanında).

Örnek: "85 m² 2+1 prefabrik" → alan seti (PA-06, PA-05, PA-04; her plan bir kez) → PA-06 seçilir → "Çatı seçin" (evin çatısı, PA-06-K,
PA-06-C) → seçilen çatıyla r01. Kıyaslanan: iki setin bayiye giden mesajı, düğmeleri ve bileşik görselinin içerik izi (PNG baytı), alan
setinin "seçildi" kapanışı, üç çatının r01 kararı (kaynak, revizyon, referans kod, çatı, şablon ve sha, mesaj). r01 çizimi (`--r01`) kıyasa
girmez (yavaş); çatı görselleri `testler/test_prefabrik_cati_seti.py`'de yeniden üretilip kıyaslanır. Fark bilerek yapıldıysa
`prefabrik_hedef.json` yalnız Lokman'ın onayıyla ve gerekçeli kararla yeniden donar (D-02); testi geçirmek için hedef değiştirilmez.
LLM, WhatsApp ve Postgres yok.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from testler.cati_secimi import ornek_prefabrik  # noqa: E402

HEDEF = Path(__file__).with_name("prefabrik_hedef.json")


def test_hedef_kaydi_onayli():
    h = json.loads(HEDEF.read_text(encoding="utf-8"))
    onay = h["onay"]
    assert onay["kim"] == "Lokman" and onay["tarih"] and onay["dayanak"], onay
    assert onay["komut"].startswith("python -m testler.cati_secimi.ornek_prefabrik"), onay
    assert "D-83" in onay["karar"], onay


def test_prefabrik_cati_seti_hedefle_ayni(tmp_path):
    h = json.loads(HEDEF.read_text(encoding="utf-8"))
    o = ornek_prefabrik.uret(tmp_path)
    o.pop("_dosyalar")
    beklenen = h["ozet"]
    farklar = [a for a in sorted(set(o) | set(beklenen)) if o.get(a) != beklenen.get(a)]
    assert not farklar, {a: {"simdi": o.get(a), "hedef": beklenen.get(a)} for a in farklar}
