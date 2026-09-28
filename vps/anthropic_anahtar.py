#!/usr/bin/env python3
"""PORTMAN · Anthropic (Claude) API anahtarını VPS'e koyar (İE-02, kapı E; Lokman 28.09 23:49: OpenAI'de kredi yok).

Anahtar STANDART GİRDİDEN okunur; ekrana, komut satırına, günlüğe ya da dosya adına yazılmaz. Mac'ten (pano → ssh; ekrana gelmez):
    scp anthropic_anahtar.py root@<VPS>:/root/ && pbpaste | ssh root@<VPS> 'python3 /root/anthropic_anahtar.py'

Yaptığı: /etc/portman/agent.env'deki ANTHROPIC_API_KEY satırını ekler ya da değiştirir. Önce anahtar satırları çıkarılmış bir yedek
alır; dosyanın izni ve sahibi korunur. Anahtarı GET /v1/models ile (ücretsiz, token harcamaz) sınar; yalnız HTTP kodu, hata türü ve
12 haneli parmak izi yazılır. Servisi YENİDEN BAŞLATMAZ: anahtar ajana yeniden başlatmayla geçer (ayrı adım).
Test için: PM_ENV, PM_ANTHROPIC_BASE.
"""
import hashlib, json, os, re, sys, time, urllib.error, urllib.request

ENV = os.environ.get("PM_ENV", "/etc/portman/agent.env")
BASE = os.environ.get("PM_ANTHROPIC_BASE", "https://api.anthropic.com/v1").rstrip("/")
iz = lambda v: hashlib.sha256(v.encode()).hexdigest()[:12]

anahtar = sys.stdin.read().strip()
if not re.fullmatch(r"sk-ant-[A-Za-z0-9_\-]{20,300}", anahtar):
    sys.exit(f"DUR: girdi bir Anthropic API anahtarına benzemiyor (uzunluk {len(anahtar)}); dosyaya dokunulmadı. "
             "Panoya Claude Console'daki anahtarı kopyaladığından emin ol.")
st = os.stat(ENV)
with open(ENV, encoding="utf-8") as f:
    satirlar = f.read().splitlines()
gizli = ("PORTMAN_API_TOKEN=", "ANTHROPIC_API_KEY=")
for n in range(100):   # aynı saniyede ikinci çalıştırma eski yedeğin üzerine yazmasın
    yedek = f"{ENV}.before-anthropic-{time.strftime('%Y%m%d-%H%M%S')}" + (f"-{n}" if n else "")
    try:
        fd = os.open(yedek, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        break
    except FileExistsError:
        continue
else:
    sys.exit("DUR: yedek dosyası oluşturulamadı; dosyaya dokunulmadı.")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("\n".join(s for s in satirlar if not s.startswith(gizli)) + "\n")
eski = [s for s in satirlar if s.startswith("ANTHROPIC_API_KEY=")]
yeni_satirlar = [s for s in satirlar if not s.startswith("ANTHROPIC_API_KEY=")] + ["ANTHROPIC_API_KEY=" + anahtar]
gecici = ENV + ".yeni"
fd = os.open(gecici, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, st.st_mode & 0o777)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("\n".join(yeni_satirlar) + "\n")
os.chown(gecici, st.st_uid, st.st_gid); os.chmod(gecici, st.st_mode & 0o777)
os.replace(gecici, ENV)
son = os.stat(ENV)
print(f"== Anthropic anahtarı agent.env'e yazıldı · {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"   parmak izi {iz(anahtar)} · önceki ANTHROPIC_API_KEY satırı: {'vardı, değiştirildi' if eski else 'yoktu, eklendi'}")
print(f"   izin {oct(son.st_mode & 0o777)} · sahip {son.st_uid}:{son.st_gid} (öncekiyle {'aynı' if (son.st_mode & 0o777, son.st_uid, son.st_gid) == (st.st_mode & 0o777, st.st_uid, st.st_gid) else 'FARKLI'})")
print(f"   anahtar satırları çıkarılmış yedek: {os.path.basename(yedek)}")
req = urllib.request.Request(BASE + "/models", headers={"x-api-key": anahtar, "anthropic-version": "2023-06-01", "User-Agent": "portman-kapi-e"})
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        modeller = [m.get("id") for m in json.loads(r.read().decode()).get("data", [])]
    var = lambda ad: 'evet' if any(str(m).startswith(ad) for m in modeller) else 'HAYIR'
    print(f"   Anthropic GET /v1/models: HTTP 200 · claude-opus-5-5 erişilebilir: {var('claude-opus-5-5')} · claude-haiku-4-5: {var('claude-haiku-4-5')}")
except urllib.error.HTTPError as e:
    try:
        tur = str((json.loads(e.read().decode()).get("error") or {}).get("type") or "")
    except Exception:
        tur = ""
    print(f"   Anthropic GET /v1/models: HTTP {e.code} {re.sub(r'[^a-z_]', '', tur)}")
except OSError as e:
    print(f"   Anthropic GET /v1/models: ulaşılamadı ({type(e).__name__})")
print("   servis yeniden başlatılmadı. Not: bu denetim kredi bakiyesini göstermez; bakiye Claude Console'da görülür.")
