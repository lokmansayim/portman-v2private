#!/usr/bin/env bash
# PORTMAN · yedek bağlantısı kurulumu (İE-06, Kapı 5; root). Değerler STDIN'den gelir; ekrana ve komut satırına yazılmaz.
#   drive: Mac'teki `rclone authorize "drive" "eyJzY29wZSI6ImRyaXZlLmZpbGUifQ"` çıktısındaki {"access_token": …} bloğu →
#          /etc/portman/rclone.conf (uzak ad portman-drive, yetki drive.file: yalnız rclone'un oluşturduğu dosyalar) ve Drive'da
#          Portman-Yedek klasörü.      pbpaste | ssh portman-vps 'bash /opt/portman/guncel/vps/yedek_kur.sh drive'
#   age:   Mac'teki age-keygen çıktısındaki "age1…" AÇIK anahtarı → /etc/portman/yedek.pub. Gizli anahtar Mac'te kalır.
#          pbpaste | ssh portman-vps 'bash /opt/portman/guncel/vps/yedek_kur.sh age'
# rclone.conf doğrudan yazılır (belirteç komut satırına geçmez). Sınama: PM_ETC, PM_RCLONE, PM_TEST=1 (Drive'a bağlanılmaz).
set -euo pipefail
ETC="${PM_ETC:-/etc/portman}"; RCLONE="${PM_RCLONE:-rclone}"; TEST="${PM_TEST:-}"
NE="${1:-}"
dur() { echo "DUR: $*" >&2; exit 1; }
umask 077
install -d -m 700 "$ETC"
case "$NE" in
drive)
  CONF="$ETC/rclone.conf"
  GIRDI="$(cat || true)"                       # belirteç: ortam değişkeniyle geçer (komut satırına ve ekrana çıkmaz)
  PM_GIRDI="$GIRDI" python3 - "$CONF" <<'PY' || dur "girdi rclone authorize çıktısına benzemiyor ({\"access_token\": …, \"refresh_token\": …}); dosyaya dokunulmadı"
import json, os, re, sys
ham = os.environ.get("PM_GIRDI", "")
m = re.search(r"\{.*\}", ham, re.S)
d = json.loads(m.group(0)) if m else {}
if not (isinstance(d, dict) and d.get("access_token") and d.get("refresh_token")):
    sys.exit(1)
yol = sys.argv[1]
metin = "[portman-drive]\ntype = drive\nscope = drive.file\ntoken = " + json.dumps(d, separators=(",", ":")) + "\nteam_drive = \n"
fd = os.open(yol + ".yeni", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(metin)
os.replace(yol + ".yeni", yol)
PY
  chmod 600 "$CONF"
  echo "== Drive bağlantısı yazıldı: $CONF (uzak: portman-drive, yetki drive.file) · parmak izi $(sha256sum "$CONF" | cut -c1-12)"
  if [ -z "$TEST" ]; then
    $RCLONE --config "$CONF" mkdir portman-drive:Portman-Yedek >/dev/null 2>&1 || dur "Drive'a bağlanılamadı (belirteç geçersiz ya da ağ); rclone.conf yazıldı, yeniden deneyin"
    echo "   Drive: Portman-Yedek klasörü hazır · $( $RCLONE --config "$CONF" lsf portman-drive:Portman-Yedek 2>/dev/null | wc -l ) dosya"
  else
    echo "   PM_TEST: Drive'a bağlanılmadı"
  fi
  ;;
age)
  ANAHTAR="$( { cat || true; } | grep -oE 'age1[0-9a-z]{58}' | head -1 || true)"
  [[ "$ANAHTAR" =~ ^age1[0-9a-z]{58}$ ]] || dur "girdi bir age açık anahtarına benzemiyor (age1… 62 karakter; age-keygen'in 'Public key:' satırı da olur); dosyaya dokunulmadı"
  printf '%s\n' "$ANAHTAR" > "$ETC/yedek.pub.yeni"; mv -f "$ETC/yedek.pub.yeni" "$ETC/yedek.pub"; chmod 600 "$ETC/yedek.pub"
  echo "== age açık anahtarı yazıldı: $ETC/yedek.pub (${ANAHTAR:0:8}…) · gizli anahtar Mac'te kalır (~/.config/portman/yedek.key, kâğıt kopyası)"
  ;;
*) dur "kullanım: yedek_kur.sh drive|age   (değer stdin'den)" ;;
esac
echo "   ilk yedek: her gece 03:40 (portman-yedek.timer); elle: bash /opt/portman/guncel/vps/yedek.sh"
