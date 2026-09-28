"""Gönderen başına konuşma durumu (v0.1: JSON dosyası; canlıda DB tablosu olacak — arayüz aynı kalır).

Durum makinesi: bos → topluyor → is_emri_hazir → uretildi → onay_bekliyor → onaylandi | revizyon
"""
from __future__ import annotations
import json, time
from pathlib import Path

import os
DURUM_DIR = Path(os.environ.get("PORTMAN_DURUM_DIR") or (Path(__file__).resolve().parent / "durum"))
MAX_REVIZYON = 4
MAX_SORU = 4
# D-01 (B2 kararı, Lokman, 28.09): taslak bu süreden uzun süre önce kaldıysa ve bayinin mesajı model koduyla başlıyorsa
# sistem mesajı eski taslağa eklemeden önce sorar: yeni talep mi, o taslağın değişikliği mi?
ESKI_TASLAK_SN = 2 * 3600


def _anahtar(v, alan: str):
    if not isinstance(v, dict):
        return ("_", str(v).strip().lower())
    if alan == "varyantlar":
        tur = v.get("tur"); p = v.get("parametreler") or {}
        if tur in ("ayna_x", "ayna_y"):
            return (tur,)
        if tur == "pencere_degistir":
            return (tur, str(p.get("mahal") or v.get("aciklama") or "").strip().lower())
        return (tur, json.dumps(p, sort_keys=True, ensure_ascii=False), str(v.get("aciklama") or "").strip().lower())
    if alan == "pencereler":
        return (str(v.get("mahal") or "").strip().lower(), v.get("islem"), v.get("duvar"))
    return ("_", json.dumps(v, sort_keys=True, ensure_ascii=False))


def _tekillestir(liste: list, alan: str) -> list:
    """Aynı anahtarlı kayıtlardan sonuncusu kalır; ilk görülme sırası korunur."""
    out = {}
    for v in liste:
        out[_anahtar(v, alan)] = v
    return list(out.values())


class Konusma:
    def __init__(self, gonderen: str, kok: Path = DURUM_DIR):
        self.gonderen = gonderen
        self.path = kok / f"{gonderen}.json"
        kok.mkdir(parents=True, exist_ok=True)
        self.d = json.loads(self.path.read_text()) if self.path.exists() else self._bos()

    @staticmethod
    def _bos() -> dict:
        return {"asama": "bos", "taslak": {}, "soru_sayisi": 0, "revizyon": 0, "son_soru_alani": None,
                "bekleyen_onay": None, "son_is_emri": None, "gecmis": [], "guncellendi": 0, "taslak_zamani": 0}

    def sifirla(self):
        self.d = self._bos(); self.kaydet()

    def kaydet(self):
        self.d["guncellendi"] = int(time.time())
        self.path.write_text(json.dumps(self.d, ensure_ascii=False, indent=1))

    def birlestir(self, talep: dict):
        """Yeni mesajdan gelen dolu alanları taslağa ekle (null olanlar öncekini ezmez).
        Listeler birleşirken tekilleşir: ayna_x/ayna_y bayrak gibidir (bir kez), pencere değişikliği mahal başına sonuncu kazanır."""
        t = self.d["taslak"]
        self.d["taslak_zamani"] = int(time.time())     # D-01: taslağın son değiştiği an (selam ya da soru cevabı saymaz)
        for k, v in talep.items():
            if v in (None, [], {}, ""):
                continue
            if k in ("varyantlar", "ozel_istekler", "belirsizlikler", "pencereler") and isinstance(v, list):
                t[k] = _tekillestir((t.get(k) or []) + v, k)
            elif k == "bina_ozellikleri" and isinstance(v, dict):
                t[k] = {**(t.get(k) or {}), **v}
            elif k in ("niyet", "guven", "ozet"):
                t[k] = v
            elif isinstance(v, dict) and isinstance(t.get(k), dict):
                t[k] = {**t[k], **{kk: vv for kk, vv in v.items() if vv is not None}}
            else:
                t[k] = v

    def not_dus(self, yon: str, metin: str, ek: dict | None = None):
        self.d["gecmis"].append({"t": int(time.time()), "yon": yon, "metin": metin, **(ek or {})})
        self.d["gecmis"] = self.d["gecmis"][-40:]
