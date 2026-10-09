#!/usr/bin/env python3
"""PORTMAN · sır yerleştirme (İE-06, Kapı 5; root; yalnız standart kitaplık, sistem python3 ile koşar).

Değer STANDART GİRDİDEN okunur; ekrana, komut satırına, günlüğe ya da dosya adına yazılmaz. Çıktıda yalnız 12 haneli parmak izi ve
ücretsiz doğrulamanın HTTP sonucu vardır. Mac'ten (pano → ssh; ekrana gelmez):
    pbpaste | ssh portman-vps 'python3 /opt/portman/guncel/vps/sir_koy.py <ad>' > ie06_5_<ad>.txt 2>&1; pbcopy < /dev/null

Adlar, dosyalar (/etc/portman altında, root 0600; öteki satırlar korunur; yazım atomik) ve doğrulama:
    anthropic   ANTHROPIC_API_KEY    llm.env        GET /v1/models (ücretsiz; token harcamaz)
    wa_token    WA_ACCESS_TOKEN      whatsapp.env   GET /<phone_number_id> (wa_pnid yazılmışsa; ücretsiz)
    wa_secret   WA_APP_SECRET        whatsapp.env   32 hex; doğrulama yok (webhook imzasında kullanılır)
    wa_verify   WA_VERIFY_TOKEN      whatsapp.env   16–128 harf/rakam; Kapı 8'de Meta'ya da girilir
    wa_pnid     WA_PHONE_NUMBER_ID   whatsapp.env   sır değil; GET /<pnid> (wa_token yazılmışsa)
Servisleri YENİDEN BAŞLATMAZ: yeni değer 'systemctl restart portman-webhook portman-gonderici portman-agent' ile geçer (oz_test.sh
ajanı yeniden başlatır). Test için: PM_ETC, PM_ANTHROPIC_BASE, PM_GRAPH_BASE, PM_DOGRULAMA=0 (ağa çıkılmaz).
"""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

ETC = os.environ.get("PM_ETC", "/etc/portman")
ANTHROPIC = os.environ.get("PM_ANTHROPIC_BASE", "https://api.anthropic.com/v1").rstrip("/")
GRAPH = os.environ.get("PM_GRAPH_BASE", "https://graph.facebook.com/v23.0").rstrip("/")
DOGRULA = os.environ.get("PM_DOGRULAMA", "1") != "0"
SIRLAR = {
    "anthropic": ("llm.env", "ANTHROPIC_API_KEY", r"sk-ant-[A-Za-z0-9_\-]{20,300}", "Claude API anahtarı (platform.claude.com → Create key)"),
    "wa_token": ("whatsapp.env", "WA_ACCESS_TOKEN", r"[A-Za-z0-9]{40,600}", "WhatsApp erişim belirteci (sistem kullanıcısı, süre Never)"),
    "wa_secret": ("whatsapp.env", "WA_APP_SECRET", r"[0-9a-f]{32}", "Meta app secret (Settings → Basic → App Secret, 32 hex)"),
    "wa_verify": ("whatsapp.env", "WA_VERIFY_TOKEN", r"[A-Za-z0-9_\-]{16,128}", "verify token (openssl rand -hex 24)"),
    "wa_pnid": ("whatsapp.env", "WA_PHONE_NUMBER_ID", r"[0-9]{6,20}", "phone_number_id (WhatsApp → API Setup)"),
}
VARSAYILAN_SATIRLAR = {"whatsapp.env": ["WA_GRAPH_VERSION=v23.0"]}


def iz(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()[:12]


def satirlar(yol: str) -> list[str]:
    try:
        with open(yol, encoding="utf-8") as f:
            return [s for s in f.read().splitlines() if s.strip()]
    except FileNotFoundError:
        return []


def degisken(yol: str, ad: str) -> str | None:
    for s in satirlar(yol):
        if s.startswith(ad + "="):
            return s[len(ad) + 1:].strip()
    return None


def yaz(yol: str, ad: str, deger: str, varsayilanlar: list[str]) -> bool:
    """ad=deger satırını ekler ya da değiştirir; öteki satırlar korunur; atomik; 0600. Dönen: önceki satır var mıydı."""
    eski = satirlar(yol)
    vardi = any(s.startswith(ad + "=") for s in eski)
    yeni = [s for s in eski if not s.startswith(ad + "=")] + [f"{ad}={deger}"]
    for v in varsayilanlar:
        if not any(s.startswith(v.split("=", 1)[0] + "=") for s in yeni):
            yeni.append(v)
    os.makedirs(os.path.dirname(yol), mode=0o700, exist_ok=True)
    gecici = yol + ".yeni"
    fd = os.open(gecici, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(yeni) + "\n")
    os.chmod(gecici, 0o600)
    os.replace(gecici, yol)
    return vardi


def http_get(url: str, basliklar: dict) -> tuple[int, dict | None, str]:
    req = urllib.request.Request(url, headers={**basliklar, "User-Agent": "portman-sir-koy"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}"), ""
    except urllib.error.HTTPError as e:
        try:
            govde = json.loads(e.read().decode("utf-8") or "{}")
        except ValueError:
            govde = {}
        hata = govde.get("error") if isinstance(govde, dict) else None
        tur = (hata.get("type") if isinstance(hata, dict) else "") or ""
        return e.code, None, re.sub(r"[^A-Za-z_]", "", str(tur))[:40]
    except OSError as e:
        return 0, None, type(e).__name__


def maske(numara: str) -> str:
    n = str(numara or "")
    return ("…" + n[-2:]) if n else "-"


def dogrula(ad: str, deger: str) -> str:
    if not DOGRULA:
        return "doğrulama atlandı (PM_DOGRULAMA=0)"
    wa = os.path.join(ETC, "whatsapp.env")
    if ad == "anthropic":
        kod, govde, hata = http_get(f"{ANTHROPIC}/models", {"x-api-key": deger, "anthropic-version": "2023-06-01"})
        if kod == 200:
            modeller = [str(m.get("id")) for m in (govde or {}).get("data", []) if isinstance(m, dict)]
            return f"Claude GET /v1/models: HTTP 200 · claude-opus-5-5 erişilebilir: {'evet' if any(m.startswith('claude-opus-5-5') for m in modeller) else 'HAYIR'}"
        return f"Claude GET /v1/models: HTTP {kod} {hata} (anahtar reddedildi ya da ağ)".strip()
    if ad in ("wa_token", "wa_pnid"):
        token = deger if ad == "wa_token" else degisken(wa, "WA_ACCESS_TOKEN")
        pnid = deger if ad == "wa_pnid" else degisken(wa, "WA_PHONE_NUMBER_ID")
        if not token or not pnid:
            return f"doğrulama atlandı: {'wa_pnid' if not pnid else 'wa_token'} henüz yazılmadı (ikisi de yazılınca denenir)"
        kod, govde, hata = http_get(f"{GRAPH}/{pnid}?fields=display_phone_number,verified_name,quality_rating", {"Authorization": "Bearer " + token})
        if kod == 200 and govde:
            return (f"Meta GET /{maske(pnid)}: HTTP 200 · numara {maske(str(govde.get('display_phone_number') or '').replace(' ', ''))}"
                    f" · kalite {govde.get('quality_rating', '?')}")
        return f"Meta GET /<pnid>: HTTP {kod} {hata} (belirteç ya da phone_number_id yanlış, ya da ağ)".strip()
    return "doğrulama gerekmiyor"


def main(argv: list[str]) -> int:
    ad = argv[1] if len(argv) > 1 else ""
    if ad not in SIRLAR:
        print("kullanım: sir_koy.py <" + "|".join(SIRLAR) + ">   (değer stdin'den)", file=sys.stderr)
        return 2
    dosya, degisken_adi, desen, aciklama = SIRLAR[ad]
    deger = sys.stdin.read().strip()
    if not re.fullmatch(desen, deger):
        print(f"DUR: girdi '{ad}' biçimine uymuyor ({aciklama}; uzunluk {len(deger)}); dosyaya dokunulmadı. "
              "Panoya doğru değeri kopyaladığından emin ol.", file=sys.stderr)
        return 1
    yol = os.path.join(ETC, dosya)
    vardi = yaz(yol, degisken_adi, deger, VARSAYILAN_SATIRLAR.get(dosya, []))
    st = os.stat(yol)
    print(f"== {ad} → {yol} ({degisken_adi}; önceki satır: {'vardı, değiştirildi' if vardi else 'yoktu, eklendi'}) · izin {oct(st.st_mode & 0o777)}")
    print(f"   parmak izi {iz(deger)}")
    print(f"   {dogrula(ad, deger)}")
    print("   servisler yeniden başlatılmadı: systemctl restart portman-webhook portman-gonderici portman-agent (ya da oz_test.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
