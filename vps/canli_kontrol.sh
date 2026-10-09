#!/usr/bin/env bash
# PORTMAN · günlük canlı kontrol · SALT OKUNUR. Hiçbir dosyayı, ayarı, veritabanını ya da servisi değiştirmez; LLM ya da WhatsApp çağrısı yapmaz.
#
# Mac'ten, Lokman çalıştırır:
#   ssh portman-vps 'bash -s' < canli_kontrol.sh > canli_$(date +%Y%m%d).txt
# İsteğe bağlı: PM_BEKLENEN=<64 haneli sha256> (varsayılan: 30.09 20:56'dan beri canlıda olan v1.3 paketi), PM_SAAT=24 (günlük ve sayaç penceresi, saat).
#
# Gösterir: servis (durum, başlangıç, yeniden başlama sayısı) ve kalıcı mod; kurulu paket beklenenle aynı mı; hosting'in bildirdiği
# worker/mode/paket; son öz-test; disk doluluğu; yedekler (son üç dosya, bugünkü var mı, cron satırı); Postgres sayıları (toplam ve son
# PM_SAAT saat: mesaj, iş, giden; açık iş); günlükte hata ve uyarı satırları (numara ve uzun kimlikler maskeli); Claude anahtarı hatırlatması.
# Yazdırmaz: anahtar değeri, telefon numarası, mesaj metni.
# Test için: PM_HOME, PM_ENV, PM_YEDEK, PM_CRON, PM_PSQL (psql komutu), PM_SYSTEMCTL=0.
# Gövde tek işlevdir ve girdisi /dev/null'dur (bkz. kapi_f_*.sh: 'bash -s' betiğinin kalanını sudo yutmasın).
ana() {
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PM_ENV="${PM_ENV:-/etc/portman/agent.env}"
YEDEK="${PM_YEDEK:-/var/backups/portman}"; CRON="${PM_CRON:-/etc/cron.d/portman-pg-yedek}"
BEK="${PM_BEKLENEN:-34ae192c15a88defbb0aea757decc77a8ca21644aa7dc34b88d33b6cd5179810}"
SAAT="${PM_SAAT:-24}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"
[[ "$BEK" =~ ^[0-9a-f]{64}$ ]] || { echo "DUR: PM_BEKLENEN 64 haneli sha256 olmalı"; exit 1; }
[[ "$SAAT" =~ ^[0-9]{1,3}$ ]] || { echo "DUR: PM_SAAT saat sayısı olmalı"; exit 1; }
BAS="$(date -d "-$SAAT hours" '+%Y-%m-%d %H:%M:%S')"
echo "== Portman günlük canlı kontrol · salt okunur · betik 2026-09-30 · $(date '+%Y-%m-%d %H:%M:%S %Z') · pencere: son $SAAT saat ($BAS sonrası)"

echo "-- servis"
if [[ "${PM_SYSTEMCTL:-1}" == "1" ]] && command -v systemctl >/dev/null; then
  systemctl show portman-agent -p ActiveState -p SubState -p ActiveEnterTimestamp -p NRestarts --no-pager 2>&1 | sed 's/^/   /'
  PID="$(systemctl show portman-agent -p MainPID --value 2>/dev/null)"
  echo "   ajan sürecinde PORTMAN_PG_DSN (kalıcı mod): $( { tr '\0' '\n' < "/proc/$PID/environ"; } 2>/dev/null | grep -c '^PORTMAN_PG_DSN=' || true)"
else
  echo "   (systemctl yok ya da kapalı: servis denetimi atlandı)"
fi

echo "-- disk"
df -h / /var 2>/dev/null | awk 'NR==1 || !g[$NF]++ {printf "   %s\n", $0}'

echo "-- yedekler: $YEDEK"
if [[ -d "$YEDEK" ]]; then
  ls -lt --time-style='+%Y-%m-%d %H:%M' "$YEDEK" 2>/dev/null | awk 'NR>1 && NR<=4 {printf "   %s %s  %8s B  %s\n", $6, $7, $5, $8}'
  BUGUN="$YEDEK/portman-$(date +%Y%m%d).dump"
  if [[ -s "$BUGUN" ]]; then echo "   bugünkü yedek: VAR ($(stat -c %s "$BUGUN") B)"; else
    if (( 10#$(date +%H%M) < 320 )); then echo "   bugünkü yedek: henüz saati gelmedi (03:17)"; else echo "   bugünkü yedek: YOK (03:17'de alınmalıydı; cron ve günlüğe bak)"; fi
  fi
  echo "   yedek sayısı: $(ls "$YEDEK"/portman-2*.dump 2>/dev/null | wc -l) · toplam $(du -sh "$YEDEK" 2>/dev/null | cut -f1)"
else
  echo "   YOK: yedek klasörü bulunamadı"
fi
if [[ -f "$CRON" ]]; then echo "   cron: $(grep -v '^#' "$CRON" | grep -v '^$' | head -1 | cut -c1-120)"; else echo "   cron: $CRON YOK"; fi

echo "-- Postgres (portman)"
SQL="SELECT 'konuşma '||(SELECT count(*) FROM konusmalar)||' · mesaj '||(SELECT count(*) FROM mesajlar)||' · iş '||(SELECT count(*) FROM isler)
  ||' · giden '||(SELECT count(*) FROM giden)||' · proje '||(SELECT count(*) FROM projeler)||' · revizyon '||(SELECT count(*) FROM revizyonlar)
  ||' · açık iş '||(SELECT count(*) FROM isler WHERE durum IN ('sirada','isleniyor'))
  ||' · son ${SAAT} saat: mesaj '||(SELECT count(*) FROM mesajlar WHERE alindi >= now() - interval '${SAAT} hours')
  ||', iş '||(SELECT count(*) FROM isler WHERE olusturuldu >= now() - interval '${SAAT} hours')
  ||', giden '||(SELECT count(*) FROM giden WHERE olusturuldu >= now() - interval '${SAAT} hours');"
if OUT="$($PSQL -c "$SQL" 2>&1)"; then echo "   $OUT"; else echo "   sorgu başarısız: $(echo "$OUT" | head -2 | tr '\n' ' ' | cut -c1-160)"; fi

PM_HOME="$PM_HOME" PM_ENV="$PM_ENV" BEK="$BEK" BAS="$BAS" python3 - <<'PY'
import json, os, re, time, urllib.error, urllib.request
from pathlib import Path
HOME, ENV = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"])
BEK, BAS = os.environ["BEK"], os.environ["BAS"]
oku = lambda p: p.read_text(errors="replace").strip() if p.exists() else "-"
kurulu = oku(HOME / "app" / "PACKAGE_SHA256")
print(f"-- paket: kurulu {kurulu[:16]}… · beklenen {BEK[:16]}… · aynı: {'EVET' if kurulu == BEK else 'HAYIR'} · sürüm {oku(HOME / 'app' / 'SURUM.txt')}")
ajan = HOME / "agent.py"
if ajan.exists() and (HOME / "app" / "agent.py").exists():
    print(f"   çalışan agent.py paketteki ile aynı: {'EVET' if ajan.read_bytes() == (HOME / 'app' / 'agent.py').read_bytes() else 'HAYIR'}")
st = HOME / "data" / "self-test-result.json"
if st.exists():
    try:
        j = json.loads(st.read_text(encoding="utf-8")); a = j.get("adimlar") or {}; l = a.get("llm") or {}
        ts = lambda t: time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "-"
        print(f"-- öz-test: {j.get('state')} · sürüm {j.get('surum')} · bitti {ts(j.get('finished_at'))} · adımlar: "
              + " · ".join(f"{k} {v.get('passed') if isinstance(v, dict) else v}" for k, v in a.items())
              + (f" · LLM {l.get('backend')}/{l.get('model')}" if l else ""))
    except Exception as e:
        print(f"-- öz-test sonucu okunamadı ({type(e).__name__})")
else:
    print("-- öz-test: sonuç dosyası YOK")
h = HOME / "data" / "vps-health.json"
if h.exists():
    try:
        j = json.loads(h.read_text(encoding="utf-8"))
        yaz = j.get("written_at") or j.get("zaman") or j.get("time")
        hata = j.get("errors") or []
        print(f"-- sağlık dosyası: {len(hata)} uyarı" + (f" · yazıldı {yaz}" if yaz else "") + ("" if not hata else " · ilk: " + re.sub(r"\d{7,}", "…", str(hata[0]))[:100]))
    except Exception as e:
        print(f"-- sağlık dosyası okunamadı ({type(e).__name__})")
try:
    env = {}
    for s in ENV.read_text().splitlines():
        if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
    adlar = sorted(k for k in env if k)
    print(f"-- agent.env: anahtar adları {adlar} · değişti {time.strftime('%Y-%m-%d %H:%M', time.localtime(ENV.stat().st_mtime))}")
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-canli-kontrol"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode())
    pk = j.get("package") or {}; llm = j.get("llm") or {}
    print(f"-- hosting: worker {j.get('worker')} · mode {j.get('mode')} · dry_run {j.get('dry_run')} · llm {llm.get('backend')}/{llm.get('model')}"
          f" · hosting paketi {str(pk.get('sha256') or '-')[:16]}… · VPS ile aynı: {'EVET' if pk.get('sha256') == kurulu else 'HAYIR'}")
except urllib.error.HTTPError as e:
    print(f"-- hosting: HTTP {e.code}")
except KeyError as e:
    print(f"-- hosting: agent.env'de {e} yok; sorulmadı")
except Exception as e:
    print(f"-- hosting: ulaşılamadı ({type(e).__name__})")
print(f"-- günlük ({BAS} sonrası; yalnız hata, uyarı ve paket/servis olayları; numara ve kimlik maskeli)")
g = HOME / "logs" / "agent.log"; n = 0
for x in (g.read_text(errors="replace").splitlines() if g.exists() else []):
    if x[:19] < BAS: continue
    r = x[20:]
    if re.search(r"hata|HATA|uyar|Traceback|beklenmeyen|başarısız|belirsiz|Postgres|paket|başladı|durduruldu|yeniden başlama|öz-test", r):
        r = re.sub(r"kimden \S+", "kimden …", r); r = re.sub(r"[0-9a-f]{16,}", "…", r); r = re.sub(r"\d{10,}", "…", r)
        print(f"   {x[:19]} · {r[:120]}"); n += 1
        if n >= 40: print("   … (40 satırdan sonrası kesildi)"); break
if n == 0: print("   (pencerede eşleşen satır yok)")
PY
echo "-- hatırlatma: Claude anahtarının bilinen son kullanma tarihi 29.10.2026 (VPS agent.env ve hosting claude_api.json birlikte yenilenir)."
echo "== bitti"
}
ana "$@" < /dev/null
