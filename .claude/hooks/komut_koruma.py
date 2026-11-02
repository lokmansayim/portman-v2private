#!/usr/bin/env python3
"""PreToolUse (Bash) · komut frenleri.

Kural kaynağı: AGENTS.md (sunucu erişimi, K14 vps_komut, main'e birleştirme onayı, silme onayı, veritabanı yasakları).
- VPS/hosting erişimi (ssh, scp, sftp, rsync), vps_komut, zorla push, main'e push: ENGEL.
- main dalındayken git merge: ENGEL (main'e birleştirme PR ile, Lokman'ın onayıyla).
- Silme, ağ çağrısı, veritabanı komutu, yerel değişiklikleri geri alma, referans dondurma: SOR.
Girdi stdin'den JSON (tool_input.command). Çıktı: hook JSON'u, çıkış kodu 0.
"""
import json
import os
import re
import subprocess
import sys


def karar(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


try:
    veri = json.load(sys.stdin)
except Exception:
    sys.exit(0)

komut = str((veri.get("tool_input") or {}).get("command") or "")
cwd = veri.get("cwd") or os.getcwd()
BAS = r"(?:^|[\s;&|(`])"  # komut başı ya da zincir ayracı

ENGEL = [
    (BAS + r"(ssh|scp|sftp|rsync)\s", ("VPS'e ve hosting'e asistan bağlanmaz. Betiği hazırla; Lokman kendi Mac'inden koşar, çıktı dosyaya yazılır, sen okursun "
      "(AGENTS.md › Sunucu erişimi, BK-09). Sunucuda kopyası olan betik: `ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/…' > çıktı.txt 2>&1` "
      "(stdin'le gönderilmez); geçici betik: `ssh portman-vps 'timeout 300 bash -s' < betik > çıktı.txt 2>&1`; bir dakikadan uzun iş `setsid` ile "
      "ayrılır, bitiş satırı sunucuda dosyaya yazılır; kendi geri dönüşü olan işe (`guncelle.sh`) `timeout` konmaz.")),
    (r"vps_komut", "`vps_komut` kapalı başlar ve açılmaz (K14)."),
    (r"\bgit\s+push\b[^\n|;&]*(\s-f\b|\s--force\b|\s--force-with-lease\b)", "Zorla push yasak; geçmiş yeniden yazılmaz."),
    (r"\bgit\s+push\b[^\n|;&]*(?:\s|:)main(?:\s|$)", "main'e doğrudan push yok. main'e birleştirme yalnız Lokman'ın onayıyla, PR üzerinden (AGENTS.md › Değişiklik disiplini)."),
    (r"\bgit\s+branch\s+-[dD]\s+main\b", "main dalı silinmez."),
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*\s+(/|~|\$HOME|\.\s*$|\.\.|\*)", "Kök, ev dizini ya da depo kökünü silme yasak."),
    (r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s)", "Veritabanı silme/boşaltma yalnız Lokman'ın onayıyla; veritabanı eski yedekle ezilmez (AGENTS.md › Yasaklar)."),
]
for rx, neden in ENGEL:
    if re.search(rx, komut, flags=re.IGNORECASE if "DROP" in rx else 0):
        karar("deny", neden)

if re.search(r"\bgit\s+merge\b", komut):
    try:
        dal = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        dal = ""
    if dal == "main":
        karar("deny", "main dalındasın: main'e birleştirme yalnız Lokman'ın onayıyla, PR üzerinden yapılır. Önce iş dalına geç.")

SOR = [
    (BAS + r"rm\s", "Silme Lokman'ın onayıyla yapılır (her türlü silme: veri, geçici dosya, Mac'teki dosyalar)."),
    (BAS + r"(curl|wget|http)\s", "Ağ çağrısı: canlı sunucuya, ücretli servise ya da hosting'e dokunmadığını onayla."),
    (BAS + r"(psql|pg_restore|pg_dump|dropdb|createdb)\b", "Veritabanı komutu: yerel test Postgres'i mi (127.0.0.1:55432)? Canlı veri ve yedek kuralı (eski yedekle ezilmez) geçerli."),
    (r"\bgit\s+(reset\s+--hard|checkout\s+--\s|restore\s|clean\s+-[a-z]*f|stash\s+drop)", "Yerel değişiklikleri geri alır; kaybolacak bir şey yok mu, onayla."),
    (r"--dondur\b", "Referans yeniden dondurma gerekçeli bir karara dayanır (D-02); karar dosyası var mı, onayla."),
    (r"\bgit\s+push\b", "Push: iş dalına mı gidiyor? (main'e push engellidir; onay dalın doğruluğu içindir.)"),
]
for rx, neden in SOR:
    if re.search(rx, komut):
        karar("ask", neden)

sys.exit(0)
