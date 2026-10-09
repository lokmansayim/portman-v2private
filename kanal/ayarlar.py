"""İE-06 · Kanal ayarları: /opt/portman/data/settings.json (hosting'teki settings.json'un yerine; aynı anahtarlar).
Webhook, ajan, gönderici ve panel her turda yeniden okur; Lokman vps/ayar.sh ile değiştirir. Sır içermez (anahtarlar /etc/portman'da)."""
from __future__ import annotations

import json
import os
from pathlib import Path

DOSYA = "settings.json"
VARSAYILAN = {
    "enabled": False,                 # ana anahtar: false → webhook sahiplenmez, gönderici göndermez, ajan iş almaz
    "enabled_at": 0,                  # bundan eski mesajlar sahiplenilmez
    "dry_run": True,                  # true → giden satırlar gönderilmez (sonradan da gönderilmez)
    "mode": "patron",                 # patron | kayitli | hepsi
    "llm": {"backend": "anthropic", "model": "claude-opus-5-5", "timeout_s": 60},
    "patron_teknik_not": False,
    "mesaj_katmani": True,
    "ucb_taban_url": None,
    "kayitsiz_cevap": "Bu hat PortatifEv bayileri için Portman planlama hattıdır. Kayıtlı bayi değilseniz lütfen PortatifEv ofisiyle görüşün.",
}
ANAHTARLAR = tuple(VARSAYILAN)


def dosya(veri) -> Path:
    return Path(veri) / DOSYA


def oku(veri) -> dict:
    """Dosya yoksa ya da bozuksa varsayılanlar (enabled=false, dry_run=true: güvenli taraf)."""
    a = {k: (dict(v) if isinstance(v, dict) else v) for k, v in VARSAYILAN.items()}
    try:
        d = json.loads(dosya(veri).read_text(encoding="utf-8"))
    except Exception:
        return a
    if isinstance(d, dict):
        for k, v in d.items():
            if k == "llm" and isinstance(v, dict):
                a["llm"] = {**a["llm"], **v}
            else:
                a[k] = v
    return a


def yaz(veri, anahtar: str, deger) -> dict:
    """Tek anahtarı değiştirir (atomik). Değer JSON olarak yorumlanır ('true', '5', '"metin"'); değilse metin."""
    p = dosya(veri)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    if not isinstance(d, dict):
        d = {}
    if anahtar.startswith("llm."):
        d.setdefault("llm", {})
        d["llm"][anahtar[4:]] = deger
    else:
        d[anahtar] = deger
    p.parent.mkdir(parents=True, exist_ok=True)
    gecici = p.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(gecici, p)
    return oku(veri)


def deger_coz(metin: str):
    try:
        return json.loads(metin)
    except ValueError:
        return metin
