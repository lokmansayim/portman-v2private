#!/usr/bin/env bash
# PORTMAN · Kapı E: Claude'a (Anthropic) geçişten sonra paket öz-testini bir kez daha koşturur.
#   ssh root@<VPS> 'bash -s' < oz_test_yenile.sh
# DEĞİŞİKLİK YAPAR: yalnız /opt/portman/data/self-test-result.json silinir ve portman-agent yeniden başlatılır (anahtar ortamdan
# yüklensin, öz-test koşsun). 1 gerçek LLM çağrısı (şema hatasında +1). WhatsApp'a göndermez. Ön koşullar tutmazsa hiçbir şey yapmaz.
# Yazdırmaz: anahtar, LLM çıktısı; hata metninde anahtara benzeyen her şey gizlenir.
set -u
ENV=/etc/portman/agent.env; SONUC=/opt/portman/data/self-test-result.json
echo "== öz-test yeniden koşturma · $(date '+%Y-%m-%d %H:%M:%S %Z')"
python3 - <<'PY' || { echo "DUR: ön koşul tutmadı; hiçbir şey değişmedi."; exit 1; }
import json, sys, urllib.request
env = {}
for s in open("/etc/portman/agent.env", encoding="utf-8").read().splitlines():
    if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip()
req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-e"})
with urllib.request.urlopen(req, timeout=25) as r:
    llm = (json.loads(r.read().decode()).get("llm") or {})
var = bool(env.get("ANTHROPIC_API_KEY"))
print(f"   hosting ayarı: llm backend {llm.get('backend')} · model {llm.get('model')} · agent.env'de ANTHROPIC_API_KEY: {'var' if var else 'YOK'}")
sys.exit(0 if llm.get("backend") == "anthropic" and var else 1)
PY
rm -f "$SONUC"
systemctl restart portman-agent
echo "   servis yeniden başlatıldı; öz-test bekleniyor (en çok 150 sn)"
for i in $(seq 1 30); do
  sleep 5
  if python3 -c "import json,sys; sys.exit(0 if json.load(open('$SONUC')).get('state') not in (None, 'running') else 1)" 2>/dev/null; then break; fi
done
python3 - <<'PY'
import json, re
try:
    j = json.load(open("/opt/portman/data/self-test-result.json"))
except Exception as e:
    print("   öz-test sonucu yok:", type(e).__name__); raise SystemExit
l = (j.get("adimlar") or {}).get("llm") or {}
maske = lambda s: re.sub(r"sk-[A-Za-z0-9_*.\-]+|[A-Za-z0-9_\-]{20,}", "<gizli>", str(s))
print(f"   durum {j.get('state')} · {j.get('sure_s')} sn · işçi {j.get('surum')}")
print("   adımlar: " + ", ".join(f"{k} {'geçti' if (v or {}).get('passed') else ('atlandı' if (v or {}).get('passed') is None else 'GEÇMEDİ')}"
                              for k, v in (j.get("adimlar") or {}).items() if isinstance(v, dict)))
print(f"   LLM: {l.get('backend')} {l.get('model')} · giriş {l.get('girdi_token')} · çıkış {l.get('cikti_token')} token · tekrar {'evet' if l.get('tekrar') else 'hayır'} · {l.get('sure_ms')} ms")
if l.get("hata"):
    print("   hata:", maske(l["hata"])[:300])
PY
echo "   servis: $(systemctl is-active portman-agent) · PID $(systemctl show portman-agent -p MainPID --value)"
echo "== bitti"
