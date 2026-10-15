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
    # İE-07: Meta onaylı şablon adları (WhatsApp Manager'da onaylanınca Lokman ayar.sh ile girer; None = tanımsız → satır 'sablon_yok')
    "sablon_patron_bildirim": None,       # Patron'a: "[bayi kodu] kodlu bayinin [iş no] numaralı talebi sizi bekliyor" (url düğmesi)
    "sablon_bayi_dosyalar_hazir": None,   # bayiye: "Merhaba [hitap], [iş no] numaralı projenizin dosyaları hazır" (hızlı yanıt)
    # İE-08 8b (docs/kanal/2026-10-14_Meta_sablon_basvurusu_8b.md): mühendis bildirimi ve hatırlatması, bayiye karşılama ve bilgi hazır
    "sablon_muhendis_kontrol": None,      # mühendise: "[iş no] numaralı işin [rNN] revizyonu … teknik kontrolünüzü bekliyor" (hızlı yanıt Gönder)
    "sablon_muhendis_hatirlatma": None,   # mühendise: "Hatırlatma: [iş no] … [saat] saattir sizi bekliyor" (hızlı yanıt Gönder)
    "sablon_bayi_karsilama": None,        # bayiye (panelden, hiç yazmamış karta): "Merhaba [hitap], Portman bayi kaydınız onaylandı…" (Nasıl çalışır?)
    "sablon_bayi_bilgi_hazir": None,      # bayiye (panelden): "Merhaba [hitap], talebinizle ilgili bilgi hazır…" (Bilgiyi gönder)
    "sablon_dil": "tr",                   # şablonların Meta'daki dil kodu
    # İE-14 (D-18; r3): uyan çelik model yoksa yeni plan (program → bankadan uyarlama → çözücü; LLM koordinat yazmaz). Yapısal talepte LLM
    # çağrısı yok; tanınmayan serbest istek için 1, sığmayan programda en son en çok `en_cok_cagri` (ücretli). Kapalıyken bugünkü davranış.
    "plan_uretimi": {"acik": False, "model": "claude-opus-5-5", "effort": "low", "en_cok_cagri": 2, "timeout_s": 60},
    # İE-14 r3 (P4): çelik banka modelinin revizyonunda LLM-önce okuma. `mod`: "kapali" (kural okuması, celik_okuma) · "golge" (kural karar
    # verir; LLM aynı mesajı gölgede okur, iki okuma okuma_kiyaslari'na yazılır; mesaj başına 1 ücretli çağrı) · "acik" (LLM-önce karar).
    # Geriye uyum: `acik: true` ve `mod` yoksa "acik".
    "llm_once_revizyon": {"acik": False, "model": "claude-opus-5-5", "effort": "low", "timeout_s": 60},   # `mod` yok = kapali (inceleme C5)
}
ANAHTARLAR = tuple(VARSAYILAN)
SABLON_ANAHTARLARI = ("sablon_patron_bildirim", "sablon_bayi_dosyalar_hazir", "sablon_muhendis_kontrol", "sablon_muhendis_hatirlatma",
                      "sablon_bayi_karsilama", "sablon_bayi_bilgi_hazir")


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
            if k in ("llm", "plan_uretimi", "llm_once_revizyon") and isinstance(v, dict):
                a[k] = {**a[k], **v}
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


MODLAR = ("patron", "kayitli", "hepsi")


def _sablon_kaliplari():
    """Şablon adı ve dil kalıpları kanal/meta_api.py ile aynı (gönderim anında da aynı kuralla denetlenir)."""
    import sys as _sys
    kok = str(Path(__file__).resolve().parent)
    if kok not in _sys.path:
        _sys.path.insert(0, kok)
    import meta_api as _M
    return _M.SABLON_AD_KALIBI, _M.SABLON_DIL_KALIBI
MANTIKSAL = ("enabled", "dry_run", "patron_teknik_not", "mesaj_katmani")


def main(argv=None) -> int:
    """Komut satırı (vps/ayar.sh): `ayarlar.py [--veri DIZIN] oku` · `ayarlar.py [--veri DIZIN] yaz <anahtar> <değer>`.
    'enabled true' yazılınca enabled_at da şimdi olur (eski mesajlar sahiplenilmesin). Sır içermez."""
    import argparse
    import sys
    import time
    ap = argparse.ArgumentParser(description="Portman kanal ayarları (settings.json)")
    ap.add_argument("--veri", default=os.environ.get("PORTMAN_KANAL_DIR") or "/opt/portman/data")
    alt = ap.add_subparsers(dest="komut", required=True)
    alt.add_parser("oku")
    y = alt.add_parser("yaz"); y.add_argument("anahtar"); y.add_argument("deger")
    ns = ap.parse_args(argv)
    if ns.komut == "yaz":
        llm_alt = ns.anahtar[4:] if ns.anahtar.startswith("llm.") else None
        if ns.anahtar not in ANAHTARLAR and llm_alt not in VARSAYILAN["llm"]:
            print(f"DUR: bilinmeyen anahtar '{ns.anahtar}'. Geçerli: {', '.join(ANAHTARLAR)}, " + ", ".join("llm." + k for k in VARSAYILAN["llm"]), file=sys.stderr)
            return 1
        deger = deger_coz(ns.deger)
        if ns.anahtar in MANTIKSAL and not isinstance(deger, bool):
            print(f"DUR: {ns.anahtar} için değer true ya da false olmalı", file=sys.stderr); return 1
        if ns.anahtar == "mode" and deger not in MODLAR:
            print(f"DUR: mode şunlardan biri olmalı: {', '.join(MODLAR)}", file=sys.stderr); return 1
        if ns.anahtar == "enabled_at" and not isinstance(deger, int):
            print("DUR: enabled_at tam sayı (epoch) olmalı", file=sys.stderr); return 1
        ad_kalibi, dil_kalibi = _sablon_kaliplari()
        if ns.anahtar in SABLON_ANAHTARLARI and deger is not None and not (isinstance(deger, str) and ad_kalibi.match(deger)):
            print(f"DUR: {ns.anahtar} Meta şablon adı olmalı (küçük harf, rakam, alt çizgi) ya da null", file=sys.stderr); return 1
        if ns.anahtar == "sablon_dil" and not (isinstance(deger, str) and dil_kalibi.match(deger)):
            print("DUR: sablon_dil 'tr' gibi bir dil kodu olmalı", file=sys.stderr); return 1
        yaz(ns.veri, ns.anahtar, deger)
        if ns.anahtar == "enabled" and deger is True:
            yaz(ns.veri, "enabled_at", int(time.time()))
        print(f"yazıldı: {ns.anahtar} = {json.dumps(deger, ensure_ascii=False)}" + (" (enabled_at = şimdi)" if ns.anahtar == "enabled" and deger is True else ""))
    print(json.dumps(oku(ns.veri), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
