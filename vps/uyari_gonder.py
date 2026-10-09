#!/usr/bin/env python3
"""PORTMAN · Patron'a uyarı metni (İE-06, karar 10; nabiz.sh çağırır; sürümün venv python'u ile). WA_* ortamdan (whatsapp.env),
Patron numarası ve son mesaj zamanı Postgres'ten: yalnız 24 saat penceresi açıkken gönderir (ücretsiz servis penceresi; şablon mesaj
yok), aynı metni 6 saatte bir (data/nabiz/uyari_son.json). Çıktıda numara maskeli, sır yok.
    PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=/opt/portman/data python uyari_gonder.py "metin"
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

KOD = Path(__file__).resolve().parent.parent
for _yol in (KOD, KOD / "kanal"):
    if str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))

import meta_api as M                                   # noqa: E402
from depo import Depo, maske                           # noqa: E402

PENCERE_SN = 24 * 3600
SIKLIK_SN = 6 * 3600


def uyari(depo: Depo, istemci: M.GraphIstemci, veri: Path | str, metin: str, simdi: float | None = None) -> str:
    """Dönen: gonderildi | patron yok | pencere kapali | yakin zamanda gonderildi"""
    simdi = simdi or time.time()
    patron = depo.patron_numarasi()
    if not patron:
        return "patron yok"
    son = depo.son_gelen_zamani(patron)
    if son is None or simdi - son > PENCERE_SN:
        return "pencere kapali"
    p = Path(veri) / "nabiz" / "uyari_son.json"
    try:
        kayit = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        kayit = {}
    anahtar = hashlib.sha256(metin.encode("utf-8")).hexdigest()[:16]
    if simdi - float(kayit.get(anahtar) or 0) < SIKLIK_SN:
        return "yakin zamanda gonderildi"
    cevap = istemci.gonder({"messaging_product": "whatsapp", "recipient_type": "individual", "to": patron, "type": "text",
                            "text": {"preview_url": False, "body": metin[:1000]}})
    M.kabul_edilen_wamid(cevap, patron)
    kayit = {k: v for k, v in kayit.items() if simdi - float(v or 0) < 7 * 86400}
    kayit[anahtar] = simdi
    p.parent.mkdir(parents=True, exist_ok=True)
    gecici = p.with_suffix(".json.tmp")
    gecici.write_text(json.dumps(kayit), encoding="utf-8")
    os.replace(gecici, p)
    return "gonderildi"


def main(argv: list[str]) -> int:
    metin = " ".join(argv[1:]).strip() or sys.stdin.read().strip()
    if not metin:
        print("uyarı: metin yok"); return 0
    meta = M.MetaAyar.ortamdan()
    if not meta.tam_mi():
        print("uyarı: WhatsApp ayarı eksik (whatsapp.env); gönderilmedi"); return 0
    veri = os.environ.get("PORTMAN_KANAL_DIR") or "/opt/portman/data"
    try:
        depo = Depo()
        sonuc = uyari(depo, M.GraphIstemci(meta), veri, metin)
        patron = depo.patron_numarasi()
    except Exception as e:
        print("uyarı: gönderilemedi:", type(e).__name__, M.maskele(str(e), meta.access_token)[:160]); return 0
    print(f"uyarı: {sonuc} · patron {maske(patron) if patron else '-'} · metin {len(metin)} karakter")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
