#!/usr/bin/env python3
"""PORTMAN · eşleşme anahtarını yenile (İE-02, kapı C.1). VPS'te root olarak:  ssh root@<VPS> 'python3 -' < vps/anahtar_yenile.py

/etc/portman/agent.env içindeki PORTMAN_API_TOKEN satırını yeni rastgele bir değerle değiştirir. Değer ekrana, komut satırına
ya da günlüğe yazılmaz; yalnız 12 haneli parmak izi yazılır. Önce anahtar satırı ÇIKARILMIŞ bir yedek alınır (öteki ayarlar
için; eski anahtar hiçbir yerde saklanmaz). Dosya izni ve sahibi korunur. Hosting'e aktarım ayrı adımdır (kapı C.2).
Ortam: PORTMAN_AGENT_ENV (varsayılan /etc/portman/agent.env; yalnız test için değiştirilir).
"""
import hashlib, os, secrets, sys, time

p = os.environ.get("PORTMAN_AGENT_ENV", "/etc/portman/agent.env")
st = os.stat(p)
with open(p, encoding="utf-8") as f:
    satirlar = f.read().splitlines()
if sum(s.startswith("PORTMAN_API_TOKEN=") for s in satirlar) != 1:
    sys.exit("PORTMAN_API_TOKEN satırı yok ya da birden çok; dosyaya dokunulmadı")
eski_iz = hashlib.sha256(next(s for s in satirlar if s.startswith("PORTMAN_API_TOKEN=")).split("=", 1)[1].strip().encode()).hexdigest()[:12]
yedek = f"{p}.before-c-{time.strftime('%Y%m%d-%H%M%S')}"
fd = os.open(yedek, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("\n".join(s for s in satirlar if not s.startswith("PORTMAN_API_TOKEN=")) + "\n")
yeni = secrets.token_hex(32)
gecici = p + ".yeni"
fd = os.open(gecici, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, st.st_mode & 0o777)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("\n".join("PORTMAN_API_TOKEN=" + yeni if s.startswith("PORTMAN_API_TOKEN=") else s for s in satirlar) + "\n")
os.chown(gecici, st.st_uid, st.st_gid); os.chmod(gecici, st.st_mode & 0o777)      # umask izni daraltmasın
os.replace(gecici, p)
print("eski parmak izi:", eski_iz)
print("yeni parmak izi:", hashlib.sha256(yeni.encode()).hexdigest()[:12])
print("anahtarsız yedek:", yedek)
