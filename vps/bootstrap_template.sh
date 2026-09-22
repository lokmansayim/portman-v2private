#!/usr/bin/env bash
# PORTMAN VPS KURULUM — Ubuntu 24.04, root olarak bir kez çalıştırılır.
#   ssh root@<IP> 'bash -s' < bootstrap_vps.sh
# Yaptıkları: sistem güncelleme, Python venv + paketler, 'portman' sistem kullanıcısı, ajan (systemd servisi),
# güvenlik duvarı (yalnız SSH), fail2ban, zaman dilimi. Sonunda ÜRETİLEN EŞLEŞME ANAHTARINI bir kez yazar:
# bu anahtar hostingte portman_app/kanal/api_token.txt dosyasına yapıştırılır (Claude'a ya da sohbete yazılmaz).
# Ajan hostinge yalnız dışarıdan bağlanır; WhatsApp anahtarı bu makineye hiç gelmez. Kurulum tekrar çalıştırılabilir (idempotent).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
API_URL="${PORTMAN_API_URL:-https://portatifev.com/developer/kanal_api.php}"
HOME_DIR=/opt/portman
ENV_FILE=/etc/portman/agent.env

echo "== [1/7] sistem paketleri"
apt-get update -q
apt-get install -y -q python3 python3-venv python3-pip curl unzip ufw fail2ban unattended-upgrades ca-certificates fonts-dejavu-core >/dev/null
timedatectl set-timezone Europe/Istanbul || true

echo "== [2/7] kullanıcı ve dizinler"
id -u portman >/dev/null 2>&1 || useradd --system --home-dir "$HOME_DIR" --shell /usr/sbin/nologin portman
mkdir -p "$HOME_DIR"/{app,data/durum,data/projects,data/pending,logs,pkg} /etc/portman
chown -R portman:portman "$HOME_DIR"
chmod 750 "$HOME_DIR"

echo "== [3/7] Python venv"
if [ ! -x "$HOME_DIR/venv/bin/python" ]; then
  sudo -u portman python3 -m venv "$HOME_DIR/venv"
fi
sudo -u portman "$HOME_DIR/venv/bin/pip" install -q --upgrade pip
sudo -u portman "$HOME_DIR/venv/bin/pip" install -q "ezdxf==1.4.4" "pymupdf==1.26.0" "shapely==2.1.2" "pydantic==2.13.5" "numpy>=2,<3" "pillow>=10"
"$HOME_DIR/venv/bin/python" - <<'PY'
import ezdxf, shapely, pydantic, fitz, numpy, PIL, sys
print("   python", sys.version.split()[0], "| ezdxf", ezdxf.__version__, "| shapely", shapely.__version__, "| pydantic", pydantic.VERSION, "| pymupdf", fitz.VersionBind, "| numpy", numpy.__version__)
PY

echo "== [4/7] ajan"
cat > "$HOME_DIR/agent.py" <<'PYAGENT'
__AGENT_PY__
PYAGENT
chown portman:portman "$HOME_DIR/agent.py"; chmod 640 "$HOME_DIR/agent.py"

echo "== [5/7] eşleşme anahtarı ve ortam"
if [ ! -f "$ENV_FILE" ]; then
  TOKEN="$(openssl rand -hex 32)"
  umask 077
  cat > "$ENV_FILE" <<EOF
PORTMAN_API_URL=$API_URL
PORTMAN_API_TOKEN=$TOKEN
PORTMAN_HOME=$HOME_DIR
PYTHONUNBUFFERED=1
EOF
  chown root:portman "$ENV_FILE"; chmod 640 "$ENV_FILE"
  YENI_ANAHTAR=1
else
  TOKEN="$(grep '^PORTMAN_API_TOKEN=' "$ENV_FILE" | cut -d= -f2-)"
  YENI_ANAHTAR=0
fi

echo "== [6/7] systemd servisi"
cat > /etc/systemd/system/portman-agent.service <<EOF
[Unit]
Description=Portman VPS ajanı (Beyin+Motor işçisi; hosting API'sinden iş çeker)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=portman
Group=portman
EnvironmentFile=$ENV_FILE
WorkingDirectory=$HOME_DIR
ExecStart=$HOME_DIR/venv/bin/python $HOME_DIR/agent.py
Restart=always
RestartSec=5
MemoryMax=6G
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$HOME_DIR

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable portman-agent >/dev/null 2>&1
systemctl restart portman-agent

echo "== [7/7] güvenlik duvarı ve fail2ban"
ufw --force default deny incoming >/dev/null
ufw --force default allow outgoing >/dev/null
ufw allow OpenSSH >/dev/null
ufw --force enable >/dev/null
systemctl enable --now fail2ban >/dev/null 2>&1 || true
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

echo
echo "================================================================"
echo " KURULUM TAMAM.  Servis: systemctl status portman-agent"
echo " Günlük:  journalctl -u portman-agent -f   |  $HOME_DIR/logs/agent.log"
echo " API: $API_URL"
if [ "$YENI_ANAHTAR" = "1" ]; then
  echo
  echo " EŞLEŞME ANAHTARI (bir kez gösterilir; DirectAdmin'de portman_app/kanal/api_token.txt içine tek satır olarak yapıştır):"
  echo
  echo "   $TOKEN"
  echo
  echo " Bu anahtarı sohbete/Claude'a yazma. Kaybolursa: rm $ENV_FILE && bu betiği yeniden çalıştır."
else
  echo " Mevcut eşleşme anahtarı korundu ($ENV_FILE)."
fi
echo "================================================================"
