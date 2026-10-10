#!/usr/bin/env bash
# PORTMAN · sürüm kurulumu (İE-06, Kapı 4 ve sonraki her güncelleme; root). Onaylı AÇIKLAMALI etiketi dağıtım anahtarıyla çeker,
# /opt/portman/surumler/<etiket>/ altına kendi venv'iyle kurar, içe aktarma denetimini ve göçleri (yalnız ekler) koşar, 'onceki' ve
# 'guncel' bağlantılarını değiştirir, servisleri başlatır ve /saglik'i bekler; sağlık gelmezse geri_don.sh ile önceki sürüme döner.
#   ssh portman-vps 'bash -s' < vps/guncelle.sh v2026.10.XX > ie06_4_surum.txt 2>&1      (ilk kez; depo sunucuda yokken)
#   ssh portman-vps 'bash /opt/portman/guncel/vps/guncelle.sh v2026.10.XX'                 (sonrakiler)
# DURUR: etiket biçimi (vYYYY.AA.GG[a-z]); etiket açıklamalı (annotated) değilse; etiket origin/main üzerinde değilse; içe aktarma
# denetimi düşerse (sürüm etkinleşmez); göç hatası. Hiçbir şey SİLMEZ: yarım kalmış sürüm dizini '.yarim-…' adıyla kenara alınır,
# eski sürümler durur (surum_temizle.sh ayrı kapıdır). Çıktıda sır yok.
# Sınama: PM_KOK, PM_ETC, PM_GIT_URL (yerel çıplak depo olabilir), PM_PYTHON, PM_VENV_ATLA=1 (venv yerine PM_PYTHON bağlanır),
# PM_SYSTEMCTL, PM_OLARAK (göç komutunun önüne; boş olabilir), PM_PG_DSN, PM_SAGLIK_URL, PM_SAGLIK_BEKLE, PM_TEST=1 (durum.sh atlanır).
set -euo pipefail
ETIKET="${1:-}"
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"
GIT_URL="${PM_GIT_URL:-git@github.com:lokmansayim/portman-v2private.git}"
PY="${PM_PYTHON:-python3}"
SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"
PG_DSN="${PM_PG_DSN:-dbname=portman}"
SAGLIK_URL="${PM_SAGLIK_URL:-http://127.0.0.1:8081/saglik}"; SAGLIK_BEKLE="${PM_SAGLIK_BEKLE:-60}"
TEST="${PM_TEST:-}"
if [ -n "${PM_OLARAK+x}" ]; then read -r -a OLARAK <<< "$PM_OLARAK"; else OLARAK=(sudo -u portman); fi
SERVISLER="portman-webhook portman-gonderici portman-agent portman-panel"
KAYNAK="$KOK/kaynak"; SURUMLER="$KOK/surumler"; HEDEF="$SURUMLER/$ETIKET"

dur() { echo "DUR: $*" >&2; echo "== bitti (durdu; sürüm etkinleşmedi)"; exit 1; }
echo "== Portman sürüm kurulumu (İE-06) · betik 2026-10-09 · $(date '+%Y-%m-%d %H:%M:%S %Z') · etiket: ${ETIKET:-?}"
[[ "$ETIKET" =~ ^v20[0-9]{2}\.[0-9]{2}\.[0-9]{2}[a-z]?$ ]] || dur "etiket biçimi vYYYY.AA.GG[a-z] olmalı (ör. v2026.10.12); verilen: '${ETIKET}'"
if [ -z "$TEST" ]; then [ "$(id -u)" = "0" ] || dur "root olarak çalıştırılmalı"; fi
cd /tmp
umask 022
if [ -f "$ETC/deploy_key" ] && [[ "$GIT_URL" != /* ]]; then
  if [ -s "$ETC/known_hosts" ]; then    # kurulum.sh GitHub'ın yayımlanmış ed25519 anahtarını yazar; uymuyorsa: ssh-keyscan -t ed25519 github.com > /etc/portman/known_hosts
    export GIT_SSH_COMMAND="ssh -i $ETC/deploy_key -o IdentitiesOnly=yes -o UserKnownHostsFile=$ETC/known_hosts -o StrictHostKeyChecking=yes"
  else
    export GIT_SSH_COMMAND="ssh -i $ETC/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
  fi
fi

echo "-- [1/6] kaynak: $GIT_URL"
if [ ! -d "$KAYNAK/.git" ]; then
  git clone -q --no-checkout "$GIT_URL" "$KAYNAK" || dur "depo çekilemedi (dağıtım anahtarı GitHub'a eklendi mi?)"
fi
git -C "$KAYNAK" fetch -q --force --tags origin main || dur "origin/main ve etiketler çekilemedi"
TUR="$(git -C "$KAYNAK" cat-file -t "refs/tags/$ETIKET" 2>/dev/null || echo yok)"
[ "$TUR" != "yok" ] || dur "etiket yok: $ETIKET (önce Kapı M: main'de açıklamalı etiket açılıp itilir)"
[ "$TUR" = "tag" ] || dur "etiket açıklamalı (annotated) değil: $ETIKET ($TUR). Kapı M etiketi 'git tag -a' ile açılır"
COMMIT="$(git -C "$KAYNAK" rev-parse "refs/tags/$ETIKET^{commit}")"
git -C "$KAYNAK" merge-base --is-ancestor "$COMMIT" refs/remotes/origin/main || dur "etiket origin/main üzerinde değil: $ETIKET → ${COMMIT:0:12}"
echo "   etiket $ETIKET → ${COMMIT:0:12} · main üzerinde · $(git -C "$KAYNAK" tag -l --format='%(taggerdate:short) %(contents:subject)' "$ETIKET")"

echo "-- [2/6] sürüm dizini: $HEDEF"
if [ -d "$HEDEF" ] && [ ! -f "$HEDEF/KURULDU" ]; then
  KENAR="$SURUMLER/.yarim-$ETIKET-$(date +%Y%m%d%H%M%S)"
  mv "$HEDEF" "$KENAR"; echo "   yarım kalmış dizin kenara alındı: $KENAR (silinmedi)"
fi
if [ -f "$HEDEF/KURULDU" ]; then
  echo "   sürüm zaten kurulu ($(cat "$HEDEF/KURULDU")); dosyalar ve venv yeniden kurulmuyor"
else
  install -d -m 755 "$HEDEF"
  git -C "$KAYNAK" archive --format=tar "refs/tags/$ETIKET" | tar -x -C "$HEDEF"
  printf '%s\n' "$ETIKET" > "$HEDEF/SURUM"; printf '%s\n' "$COMMIT" > "$HEDEF/SURUM_COMMIT"
  echo "   dosyalar açıldı ($(find "$HEDEF" -type f | wc -l) dosya; .git yok)"
  echo "-- [3/6] sanal ortam ve içe aktarma denetimi"
  if [ -n "${PM_VENV_ATLA:-}" ]; then
    install -d -m 755 "$HEDEF/venv/bin"
    printf '#!/bin/sh\nexec "%s" "$@"\n' "$(command -v "$PY")" > "$HEDEF/venv/bin/python"; chmod 755 "$HEDEF/venv/bin/python"
    echo "   PM_VENV_ATLA: venv yerine $PY sarmalandı"
  else
    "$PY" -m venv "$HEDEF/venv" || dur "venv açılamadı (python3-venv kurulu mu?)"
    "$HEDEF/venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
    [ -f "$HEDEF/vps/gereksinimler.txt" ] || dur "vps/gereksinimler.txt yok (sunucu paket listesi; v2026.10.10 ve sonrası etiketlerde var)"
    "$HEDEF/venv/bin/pip" install -q --no-cache-dir -r "$HEDEF/vps/gereksinimler.txt" \
      || dur "paketler kurulamadı (vps/gereksinimler.txt; tam sabit, numpy 1.x: K19); ağ ve pip çıktısı yukarıda"
    [ -x "$HEDEF/venv/bin/gunicorn" ] || dur "gunicorn kurulmadı"
  fi
  VPY="$HEDEF/venv/bin/python"
  "$VPY" - "$HEDEF" <<'PY' || dur "içe aktarma denetimi düştü; sürüm etkinleştirilmedi (K19 numpy notu: vps/gereksinimler.txt başı, docs/is_emirleri/IE-06.md › Riskler)"
import sys
kok = sys.argv[1]; sys.path[:0] = [kok, kok + "/kanal"]
import numpy, ezdxf, fitz, shapely, psycopg, matplotlib, PIL, ifcopenshell, pydantic   # noqa
# K19: içe aktarma yetmez, NumPy'nin derlenmiş çekirdeği bu işlemcide gerçekten çalışmalı (X86_V2 hatası ilk işlemde çıkar)
a = numpy.arange(12, dtype=float).reshape(3, 4)
iz = float((a @ a.T).trace()); kok2 = float(numpy.sqrt(numpy.array([16.0]))[0])
assert abs(iz - 506.0) < 1e-9 and abs(kok2 - 4.0) < 1e-12, (iz, kok2)
import beyin.karar, motor.dxf_out, kalici, webhook, panel, gonderici, ayarlar, nabiz, meta_api   # noqa
print(f"   içe aktarma tamam: python {sys.version.split()[0]} · numpy {numpy.__version__} (hesap tamam) · ezdxf {ezdxf.__version__} · matplotlib {matplotlib.__version__}"
      f" · pillow {PIL.__version__} · PyMuPDF {getattr(fitz, 'VersionBind', '?')} · shapely {shapely.__version__}"
      f" · psycopg {psycopg.__version__} · pydantic {pydantic.__version__} · ifcopenshell {ifcopenshell.version}")
PY
  date '+%Y-%m-%d %H:%M:%S' > "$HEDEF/KURULDU"
fi
VPY="$HEDEF/venv/bin/python"

echo "-- [4/6] göçler (kalici.py goc; yalnız eksikler, yalnız ekler)"
GOC="$("${OLARAK[@]}" env PORTMAN_PG_DSN="$PG_DSN" PORTMAN_KANAL_DIR="$KOK/data" "$VPY" "$HEDEF/kanal/kalici.py" goc 2>&1)" || { echo "$GOC" | tail -5; dur "göç uygulanamadı; sürüm etkinleştirilmedi"; }
echo "   $GOC"

echo "-- [5/6] bağlantılar ve servisler"
ESKI="$( [ -L "$KOK/guncel" ] && readlink -f "$KOK/guncel" || true )"
$SYSTEMCTL stop $SERVISLER >/dev/null 2>&1 || true
if [ -n "$ESKI" ] && [ "$ESKI" != "$(readlink -f "$HEDEF")" ]; then
  ln -sfn "$ESKI" "$KOK/onceki.yeni"; mv -T "$KOK/onceki.yeni" "$KOK/onceki"
fi
ln -sfn "$HEDEF" "$KOK/guncel.yeni"; mv -T "$KOK/guncel.yeni" "$KOK/guncel"
$SYSTEMCTL daemon-reload >/dev/null 2>&1 || true
$SYSTEMCTL start $SERVISLER || dur "servisler başlatılamadı (journalctl -u portman-webhook)"
echo "   guncel → $(readlink "$KOK/guncel") · onceki → $( [ -L "$KOK/onceki" ] && readlink "$KOK/onceki" || echo yok)"

echo "-- [6/6] sağlık: $SAGLIK_URL (en çok $SAGLIK_BEKLE sn; ölçüt: cevapta surum=$ETIKET ve postgres=true — nabiz.sh'nin eski sorunları bu kapıyı düşürmez)"
OK=""; SON=""
for ((i = 0; i < SAGLIK_BEKLE; i++)); do
  SON="$(curl -s --max-time 5 "$SAGLIK_URL" 2>/dev/null || true)"
  if printf '%s' "$SON" | PM_ETIKET="$ETIKET" python3 -c 'import json, os, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
sys.exit(0 if isinstance(d, dict) and d.get("surum") == os.environ["PM_ETIKET"] and d.get("postgres") is True else 1)'; then OK=1; break; fi
  sleep 1
done
if [ -z "$OK" ]; then
  echo "   sağlık ölçütü sağlanmadı (son cevap: ${SON:0:200}). Önceki sürüme dönülüyor." >&2
  if [ -L "$KOK/onceki" ]; then
    PM_KOK="$KOK" PM_SYSTEMCTL="$SYSTEMCTL" PM_TEST="$TEST" bash "$HEDEF/vps/geri_don.sh" || true
  else
    echo "   önceki sürüm yok (ilk kurulum): servisler bu sürümde kaldı; journalctl -u portman-webhook -n 50" >&2
  fi
  dur "sağlık $SAGLIK_BEKLE sn içinde yeni sürümle ve Postgres bağlantısıyla cevap vermedi"
fi
echo "   sağlık: sürüm $ETIKET, Postgres bağlı · ${SON:0:300}"
if [ -z "$TEST" ] && [ -f "$HEDEF/vps/durum.sh" ]; then bash "$HEDEF/vps/durum.sh" || true; fi
echo "== bitti: $ETIKET etkin ($(date '+%Y-%m-%d %H:%M:%S %Z'))"
