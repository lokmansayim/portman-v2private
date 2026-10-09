#!/usr/bin/env bash
# PORTMAN · öz-test (İE-06, Kapı 5; root). Var olan self-test-result.json kenara alınır (self-test-result.onceki-<zaman>.json;
# silinmez), ajan yeniden başlatılır ve sürüm başına bir kez koşan öz-test yeniden koşar: Beyin harness (22 vaka), kural, Motor;
# LLM anahtarı varsa 1 çağrı (ücretli, ~0,03 $; Lokman'ın ayrı onayı), yoksa "atlandı". WhatsApp'a göndermez. Sonuç beklenir
# (en çok PM_BEKLE=300 sn) ve özetlenir. Sınama: PM_DATA, PM_SYSTEMCTL, PM_BEKLE.
set -uo pipefail
DATA="${PM_DATA:-/opt/portman/data}"; SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; BEKLE="${PM_BEKLE:-300}"
SONUC="$DATA/self-test-result.json"
cd /tmp
echo "== Portman öz-test · $(date '+%Y-%m-%d %H:%M:%S %Z')"
if [ -f "$SONUC" ]; then
  ESKI="$DATA/self-test-result.onceki-$(date +%Y%m%d-%H%M%S).json"; mv "$SONUC" "$ESKI"; echo "   önceki sonuç kenara alındı: $(basename "$ESKI")"
fi
$SYSTEMCTL restart portman-agent || { echo "DUR: ajan yeniden başlatılamadı" >&2; exit 1; }
for ((i = 0; i < BEKLE; i++)); do
  if [ -f "$SONUC" ] && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("state") not in (None, "running") else 1)' "$SONUC" 2>/dev/null; then break; fi
  sleep 1
done
[ -f "$SONUC" ] || { echo "DUR: $BEKLE sn içinde sonuç dosyası oluşmadı (journalctl -u portman-agent -n 50)" >&2; exit 1; }
python3 - "$SONUC" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"   durum: {d.get('state')} · sürüm {d.get('surum')} · python {d.get('python')} · süre {d.get('duration_s', d.get('sure_s', '?'))} sn")
for ad, v in (d.get("adimlar") or {}).items():
    if not isinstance(v, dict):
        print(f"   {ad}: {v}"); continue
    ozet = {k: v[k] for k in ("passed", "uyumlu", "toplam", "eylem", "backend", "model", "atlandi", "skipped", "hata", "error") if k in v}
    print(f"   {ad}: {json.dumps(ozet, ensure_ascii=False)[:200]}")
if d.get("error") or d.get("hata"):
    print(f"   HATA: {str(d.get('error') or d.get('hata'))[:300]}")
PY
echo "== bitti"
