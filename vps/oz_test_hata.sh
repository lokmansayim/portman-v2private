#!/usr/bin/env bash
# PORTMAN · SALT OKUNUR: öz-testin LLM adımının hata türü. Hiçbir şeyi değiştirmez; OpenAI'ye istek atmaz.
#   ssh root@<VPS> 'bash -s' < oz_test_hata.sh
# OpenAI'nin hata metni anahtarın bir parçasını içerebilir: "sk-…" ve 20+ karakterlik harf-rakam dizileri <gizli> yapılır.
set -u
python3 - <<'PY'
import json, re
from pathlib import Path
p = Path("/opt/portman/data/self-test-result.json")
try:
    j = json.loads(p.read_text())
except Exception as e:
    print("öz-test sonucu okunamadı:", type(e).__name__); raise SystemExit
l = (j.get("adimlar") or {}).get("llm") or {}
maske = lambda s: re.sub(r"sk-[A-Za-z0-9_*.\-]+|[A-Za-z0-9_\-]{20,}", "<gizli>", str(s))
print("durum:", j.get("state"), "· llm passed:", l.get("passed"))
for k in ("atlandi", "hata"):
    if l.get(k):
        print(f"{k}:", maske(l[k])[:400])
kod = re.search(r"HTTP (\d{3})|\b(40[0-9]|42[0-9]|5\d\d)\b", str(l.get("hata", "")))
print("HTTP kodu:", (kod.group(1) or kod.group(2)) if kod else "-")
for anahtar in ("insufficient_permissions", "Missing scopes", "model.request", "invalid_api_key", "insufficient_quota",
                "model_not_found", "does not have access", "rate_limit", "timed out", "ValidationError", "anahtar"):
    if anahtar.lower() in str(l.get("hata", "")).lower() + str(l.get("atlandi", "")).lower():
        print("içeriyor:", anahtar)
PY
