#!/usr/bin/env bash
# PORTMAN · BK-04 ön denetim · SALT OKUNUR. Hiçbir dosyayı, ayarı ya da servisi değiştirmez.
# Mac'ten Lokman çalıştırır:
#   ssh portman-vps 'bash -s' < vps/bk04_on_denetim.sh > bk04_1_on_denetim.txt 2>&1
# Ne bakar: servis; agent.env'de Claude anahtarı var mı (yalnız 12 haneli parmak izi); anahtar Anthropic'te geçerli mi
# (GET /v1/models, ücretsiz, token harcamaz; yalnız HTTP kodu); SSH'nin ETKİN ayarları (parolalı giriş açık mı); drop-in dosyaları;
# root'un yetkili anahtar sayısı; son 7 günde parolayla başarısız giriş denemesi SAYISI; ufw ve fail2ban durumu.
# Yazdırmaz: anahtar değeri, yetkili anahtar içeriği, IP adresi, kullanıcı adı listesi.
# Test için: PM_ENV, PM_SSHD_CONF, PM_SSHD_DIR, PM_AUTH_KEYS, PM_ANTHROPIC_BASE.
set -u
PM_ENV="${PM_ENV:-/etc/portman/agent.env}"
PM_SSHD_CONF="${PM_SSHD_CONF:-/etc/ssh/sshd_config}"
PM_SSHD_DIR="${PM_SSHD_DIR:-/etc/ssh/sshd_config.d}"
PM_AUTH_KEYS="${PM_AUTH_KEYS:-/root/.ssh/authorized_keys}"
export PM_ENV PM_ANTHROPIC_BASE="${PM_ANTHROPIC_BASE:-https://api.anthropic.com/v1}"

echo "== BK-04 ön denetim · betik 2026-10-04 · $(date '+%Y-%m-%d %H:%M:%S %Z') · $(hostname 2>/dev/null)"

echo "-- servis portman-agent"
if command -v systemctl >/dev/null 2>&1; then
  systemctl show portman-agent -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp --no-pager </dev/null 2>&1 | sed 's/^/   /'
else
  echo "   systemctl yok (test ortamı)"
fi

echo "-- Claude anahtarı (agent.env)"
python3 - <<'PY'
import hashlib, json, os, re, stat, urllib.error, urllib.request
p = os.environ["PM_ENV"]; base = os.environ["PM_ANTHROPIC_BASE"].rstrip("/")
try:
    st = os.stat(p)
    print(f"   dosya: {p} · izin {oct(st.st_mode & 0o777)} · sahip {st.st_uid}:{st.st_gid}")
    env = {}
    for s in open(p, encoding="utf-8").read().splitlines():
        if "=" in s and not s.lstrip().startswith("#"):
            k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("'\"")
except OSError as e:
    print(f"   DUR: agent.env okunamadı ({type(e).__name__})"); raise SystemExit
k = env.get("ANTHROPIC_API_KEY", "")
if not k:
    print("   ANTHROPIC_API_KEY: YOK"); raise SystemExit
print(f"   ANTHROPIC_API_KEY: var · parmak izi {hashlib.sha256(k.encode()).hexdigest()[:12]} · uzunluk {len(k)}")
req = urllib.request.Request(base + "/models", headers={"x-api-key": k, "anthropic-version": "2023-06-01", "User-Agent": "portman-bk04"})
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        ids = [m.get("id") for m in json.loads(r.read().decode()).get("data", [])]
    print(f"   Anthropic GET /v1/models: HTTP 200 · claude-opus-5-5 erişilebilir: {'evet' if any(str(i).startswith('claude-opus-5-5') for i in ids) else 'HAYIR'}")
except urllib.error.HTTPError as e:
    try: tur = str((json.loads(e.read().decode()).get("error") or {}).get("type") or "")
    except Exception: tur = ""
    print(f"   Anthropic GET /v1/models: HTTP {e.code} {re.sub(r'[^a-z_]', '', tur)}")
except OSError as e:
    print(f"   Anthropic GET /v1/models: ulaşılamadı ({type(e).__name__})")
print("   not: bu denetim son kullanma tarihini ve bakiyeyi göstermez; ikisi Claude Console'da görülür.")
PY

echo "-- SSH etkin ayarlar (sshd -T)"
if command -v sshd >/dev/null 2>&1; then
  sshd -T 2>/dev/null | grep -E '^(passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication|maxauthtries|port) ' | sed 's/^/   /' \
    || echo "   sshd -T çalışmadı (root değil ya da yapılandırma hatası)"
else
  echo "   sshd yok (test ortamı)"
fi
echo "-- SSH drop-in dosyaları ($PM_SSHD_DIR): sshd ilk gördüğü değeri kullanır; dosyalar ad sırasıyla okunur"
if [[ -d "$PM_SSHD_DIR" ]]; then
  for f in "$PM_SSHD_DIR"/*.conf; do
    [[ -e "$f" ]] || { echo "   (dosya yok)"; break; }
    echo "   $(basename "$f"): $(grep -iE '^\s*(PasswordAuthentication|PermitRootLogin|KbdInteractiveAuthentication|PubkeyAuthentication)\b' "$f" | tr -s ' ' | paste -sd ';' - || true)"
  done
else
  echo "   dizin yok"
fi
echo "   ana dosya: $(grep -iE '^\s*(PasswordAuthentication|PermitRootLogin)\b' "$PM_SSHD_CONF" 2>/dev/null | tr -s ' ' | paste -sd ';' - || echo '(satır yok; varsayılanlar geçerli)')"

echo "-- root yetkili anahtarları ($PM_AUTH_KEYS)"
if [[ -f "$PM_AUTH_KEYS" ]]; then
  echo "   adet: $(grep -cE '^(ssh-|ecdsa-|sk-)' "$PM_AUTH_KEYS") · türler: $(awk '/^(ssh-|ecdsa-|sk-)/{print $1}' "$PM_AUTH_KEYS" | sort | uniq -c | awk '{printf "%s×%s ", $2, $1}')"
else
  echo "   DOSYA YOK — parolalı giriş kapatılırsa root giremez; önce anahtar eklenmeli"
fi

echo "-- son 7 günde parolayla başarısız giriş denemesi (sayı; IP ve kullanıcı yazılmaz)"
if command -v journalctl >/dev/null 2>&1; then
  n="$(journalctl -u ssh -u sshd --since '7 days ago' --no-pager 2>/dev/null | grep -c 'Failed password' || true)"
  echo "   Failed password: ${n:-0} · Accepted publickey: $(journalctl -u ssh -u sshd --since '7 days ago' --no-pager 2>/dev/null | grep -c 'Accepted publickey' || true)"
else
  echo "   journalctl yok (test ortamı)"
fi

echo "-- güvenlik duvarı ve fail2ban"
if command -v ufw >/dev/null 2>&1; then ufw status verbose 2>/dev/null | sed 's/^/   /'; else echo "   ufw yok"; fi
echo "   fail2ban: $(systemctl is-active fail2ban 2>/dev/null || echo 'yok')"
echo "== bitti (hiçbir şey değiştirilmedi)"
