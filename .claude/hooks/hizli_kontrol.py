#!/usr/bin/env python3
"""PostToolUse (Edit|Write|MultiEdit) · hızlı sözdizimi denetimi.

Her .py / .sh / .json düzenlemesinden sonra koşar; hata varsa çıkış kodu 2 ile engeller ve hatayı Claude'a gösterir.
Ağ, LLM ve test koşusu yok; yalnız sözdizimi. Tam doğrulama kapanışta (/kapanis) yapılır.
"""
import json
import os
import subprocess
import sys

try:
    veri = json.load(sys.stdin)
except Exception:
    sys.exit(0)

yol = str((veri.get("tool_input") or {}).get("file_path") or "")
if not yol or not os.path.isfile(yol):
    sys.exit(0)

uzanti = os.path.splitext(yol)[1].lower()


def dur(mesaj):
    sys.stderr.write(mesaj.rstrip() + "\n")
    sys.exit(2)


if uzanti == ".py":
    # Projenin sanal ortamı varsa onun Python'u (3.11+), yoksa bu betiği koşturan Python
    aday = [os.environ.get("PORTMAN_VENV", ""), os.path.expanduser("~/.cache/portman-venv")]
    py = sys.executable
    for a in aday:
        if a and os.path.isfile(os.path.join(a, "bin", "python")):
            py = os.path.join(a, "bin", "python")
            break
    r = subprocess.run([py, "-m", "py_compile", yol], capture_output=True, text=True)
    if r.returncode != 0:
        dur(f"Sözdizimi hatası ({os.path.basename(yol)}):\n{r.stderr or r.stdout}")
elif uzanti == ".sh":
    r = subprocess.run(["bash", "-n", yol], capture_output=True, text=True)
    if r.returncode != 0:
        dur(f"Bash sözdizimi hatası ({os.path.basename(yol)}):\n{r.stderr}")
elif uzanti == ".json":
    try:
        with open(yol, encoding="utf-8") as f:
            json.load(f)
    except Exception as e:  # noqa: BLE001
        dur(f"JSON geçersiz ({os.path.basename(yol)}): {e}")
elif os.path.basename(yol) in ("CLAUDE.md", "AGENTS.md"):
    try:
        with open(yol, encoding="utf-8") as f:
            satir = sum(1 for _ in f)
    except OSError:
        satir = 0
    if satir > 200:
        print(json.dumps({"systemMessage": f"{os.path.basename(yol)} {satir} satır; 200 satırı aştı. Ayrıntıyı .claude/rules/ ya da skill'e taşı."}, ensure_ascii=False))

sys.exit(0)
