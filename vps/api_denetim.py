#!/usr/bin/env python3
"""PORTMAN · hosting API'sinin salt okunur denetimi (İE-02, kapı E.4). VPS'te:  ssh root@<VPS> 'python3 -' < vps/api_denetim.py

/etc/portman/agent.env'deki adres ve eşleşme anahtarıyla op=settings çağrılır; yalnız api sürümü, worker, enabled, mode ve
dry_run yazılır. Anahtar ve LLM anahtarı yazılmaz. Hiçbir şey değiştirmez.
Ortam: PORTMAN_AGENT_ENV (varsayılan /etc/portman/agent.env; yalnız test için değiştirilir).
"""
import json, os, urllib.request

e = {}
with open(os.environ.get("PORTMAN_AGENT_ENV", "/etc/portman/agent.env"), encoding="utf-8") as f:
    for s in f:
        if "=" in s and not s.lstrip().startswith("#"):
            k, v = s.rstrip("\n").split("=", 1); e[k.strip()] = v.strip()
r = urllib.request.Request(e["PORTMAN_API_URL"].rstrip("?") + "?op=settings",
                           headers={"X-Portman-Token": e["PORTMAN_API_TOKEN"], "User-Agent": "portman-api-denetim"})
with urllib.request.urlopen(r, timeout=30) as c:
    s = json.load(c)
print(json.dumps({k: s.get(k) for k in ("api", "worker", "enabled", "mode", "dry_run")}, ensure_ascii=False))
