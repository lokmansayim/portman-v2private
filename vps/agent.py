#!/usr/bin/env python3
"""PORTMAN VPS AJANI v2.0 (İE-06) — Postgres kuyruğundan iş alır, Beyin + Motor ile üretir, giden satırlarını yazar.

Tek sunucu: gelen mesajı webhook (kanal/webhook.py) Postgres'e yazar, bu ajan işler (kanal/kalici.py::bir_is), gönderimi
kanal/gonderici.py yapar. Hosting, claim/result, paket indirme ve komut kanalı yok (K06, K12, K13, K14 → D-05). Bu süreç
WhatsApp'a bağlanmaz; dışarı yalnız LLM çağrısı çıkar (ANTHROPIC_API_KEY, /etc/portman/llm.env → systemd EnvironmentFile).

Ortam: PORTMAN_PG_DSN (dbname=portman), PORTMAN_KANAL_DIR (/opt/portman/data: settings.json, projects/, nabiz/, checks/),
PORTMAN_AGENT_ONESHOT=1 (test: kuyruk boşalınca çık). Kod: /opt/portman/guncel/ (sürüm bağlantısı; vps/guncelle.sh).
Günlüğe numara ve mesaj metni yazılmaz.
"""
from __future__ import annotations

import os
import signal
import socket
import sys
import time
import traceback
from pathlib import Path

KOD = Path(__file__).resolve().parent.parent              # depo kökü (beyin/, motor/, kanal/, is_emri/)
for _yol in (KOD, KOD / "kanal"):
    if str(_yol) not in sys.path:
        sys.path.insert(0, str(_yol))
DATA = Path(os.environ.get("PORTMAN_KANAL_DIR") or "/opt/portman/data")
os.environ.setdefault("PORTMAN_KANAL_DIR", str(DATA))

import ayarlar as AY                                       # noqa: E402
import kalici as K                                         # noqa: E402
import muhendis as MH                                      # noqa: E402  (İE-08 8b: hatırlatmalar)
import nabiz as NB                                         # noqa: E402
import worker as W                                         # noqa: E402
from depo import Depo                                      # noqa: E402

SURUM = "vps-agent-v2.0"
KIRA_SN = 120                       # D-03: 3 deneme × 120 sn
EN_COK_DENEME = 3
BOS_BEKLEME_SN = 2
ONESHOT = os.environ.get("PORTMAN_AGENT_ONESHOT") == "1"
HATIRLATMA_ARALIGI_SN = 60          # İE-08 8b: hatırlatma turu sıklığı
_dur = {"istendi": False}
_zaman = {"hatirlatma": 0.0}
_sayac = {"bitti": 0, "basarisiz": 0, "son": None}


def log(*p) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), "ajan", *p, flush=True)


def surum_etiketi() -> str:
    try:
        return (KOD / "SURUM").read_text(encoding="utf-8").strip() or SURUM
    except OSError:
        return SURUM


def isleme_ayari(ayar: dict) -> dict:
    """worker.isle'nin beklediği ayar sözlüğü (hosting'teki yerel_ayarlar'ın yerine; LLM anahtarı ortamdan, diske yazılmaz)."""
    return {"enabled": ayar.get("enabled") is True, "mode": ayar.get("mode"), "dry_run": ayar.get("dry_run") is True,
            "llm": dict(ayar.get("llm") or {}), "patron_teknik_not": ayar.get("patron_teknik_not", False) is True,
            "mesaj_katmani": ayar.get("mesaj_katmani") is True, "ucb_taban_url": ayar.get("ucb_taban_url") or None,
            "kira_sn": KIRA_SN, "en_cok_deneme": EN_COK_DENEME}


def oz_test(depo: Depo, ayar: dict) -> None:
    """Sürüm başına bir kez (data/self-test-result.json yoksa): Beyin harness, kural, Motor; LLM adımı anahtar varsa 1 çağrı."""
    try:
        W.oz_test(isleme_ayari(ayar))
    except Exception:
        log("öz-test çalıştırılamadı:", traceback.format_exc()[-600:])


def hatirlatma(depo: Depo, ayar: dict, simdi: float | None = None) -> dict | None:
    """İE-08 8b (M3): dakikada bir mühendis ve Patron hatırlatmaları (kanal/muhendis.py; satırları gönderici gönderir). Kanal kapalıyken
    (enabled false) koşmaz. Hata iş döngüsünü durdurmaz."""
    simdi = time.time() if simdi is None else simdi
    if ayar.get("enabled") is not True or simdi - _zaman["hatirlatma"] < HATIRLATMA_ARALIGI_SN:
        return None
    _zaman["hatirlatma"] = simdi
    try:
        say = MH.hatirlatma_turu(depo, simdi)
    except Exception as e:
        if type(e).__module__.startswith("psycopg"):
            raise
        log("hatırlatma turu düştü:", type(e).__name__)
        return None
    if any(say.values()):
        log("hatırlatma:", say)
    return say


def tur(depo: Depo, ayar: dict, sahip: str) -> dict | None:
    """Bir iş işler (yoksa None). Nabız her turda yazılır. İE-08 8b: dakikada bir hatırlatma turu."""
    hatirlatma(depo, ayar)
    r = None
    if ayar.get("enabled") is True:
        r = K.bir_is(depo, isleme_ayari(ayar), sahip)
        if r is not None:
            _sayac["bitti" if r.get("durum") == "bitti" else "basarisiz"] += r.get("durum") in ("bitti", "basarisiz")
            _sayac["son"] = {"is_id": r.get("is_id"), "durum": r.get("durum"), "eylem": r.get("eylem"), "zaman": int(time.time())}
            log("iş", r.get("is_id"), r.get("durum"), "→", r.get("eylem"), f"({r.get('gerekce')})", "giden:", r.get("giden"))
    NB.yaz(DATA, "agent", surum=surum_etiketi(), enabled=ayar.get("enabled") is True, bitti=_sayac["bitti"], basarisiz=_sayac["basarisiz"], son=_sayac["son"])
    return r


def main() -> int:
    log("başladı", SURUM, "sürüm", surum_etiketi(), "veri", DATA)
    signal.signal(signal.SIGTERM, lambda *_: _dur.__setitem__("istendi", True))
    for d in (DATA, DATA / "projects", DATA / "checks", DATA / "nabiz"):
        d.mkdir(parents=True, exist_ok=True)
    depo = Depo()
    sahip = K.isleyici_adi()
    hazir = False; son_uyari = 0.0; oz_test_yapildi = False; baslangic = time.time()
    while not _dur["istendi"]:
        try:
            if not hazir:
                eksik = depo.eksik_goc()
                if eksik:
                    if time.time() - son_uyari > 300:
                        log("göç bekleniyor:", eksik, "(vps/guncelle.sh uygular); iş alınmıyor"); son_uyari = time.time()
                    NB.yaz(DATA, "agent", surum=surum_etiketi(), enabled=False, sorun=f"göç eksik {eksik}")
                    time.sleep(10); continue
                n = depo.olu_kiralari_birak(socket.gethostname(), sahip)
                if n:
                    log("yeniden başlama:", n, "yarım işin kirası düşürüldü (D-03)")
                hazir = True
            ayar = AY.oku(DATA)
            if not oz_test_yapildi:
                oz_test(depo, ayar); oz_test_yapildi = True
            r = tur(depo, ayar, sahip)
            if r is None:
                if ONESHOT and depo.acik_is_sayisi() == 0 and time.time() - baslangic > 1:
                    log("oneshot: iş yok"); return 0
                bitis = time.time() + BOS_BEKLEME_SN
                while time.time() < bitis and not _dur["istendi"]:
                    time.sleep(0.2)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            if type(e).__module__.startswith("psycopg"):
                if time.time() - son_uyari > 300:
                    log("Postgres'e ulaşılamadı:", type(e).__name__, str(e)[:120]); son_uyari = time.time()
                hazir = False
            else:
                log("beklenmeyen:", traceback.format_exc()[-800:])
            time.sleep(15)
    log("durduruldu (SIGTERM): eldeki iş bitti")
    return 0


if __name__ == "__main__":
    sys.exit(main())
