#!/usr/bin/env bash
# PORTMAN · sürüm kurulumu (İE-06, Kapı 4 ve sonraki her güncelleme; root). Onaylı AÇIKLAMALI etiketi dağıtım anahtarıyla çeker,
# /opt/portman/surumler/<etiket>/ altına kendi venv'iyle kurar, içe aktarma denetimini ve göçleri (yalnız ekler) koşar, 'onceki' ve
# 'guncel' bağlantılarını değiştirir, servisleri başlatır ve /saglik'i bekler; sağlık gelmezse geri_don.sh ile önceki sürüme döner.
# BK-07: sağlık geçince sürümdeki nginx yapılandırmasını uygular (vps/nginx_uygula.sh; nginx -t, yedek, reload; hata sürümü düşürmez).
#   ssh portman-vps 'bash -s' < vps/guncelle.sh v2026.10.XX > ie06_4_surum.txt 2>&1      (tarihli: İE-06 ilk kurulum, depo sunucuda yokken)
#   ssh -n portman-vps "setsid nohup bash -c 'bash /opt/portman/guncel/vps/guncelle.sh v2026.10.XX; echo == çıkış \$?' \
#       > /root/guncelle_v2026.10.XX.txt 2>&1 < /dev/null &"                    (sonrakiler; BK-09 kuralı: uzun iş oturumdan ayrı,
#   ssh -n portman-vps 'tail -5 /root/guncelle_v2026.10.XX.txt' > surum.txt      SSH koparsa yarım kalmaz; son satır "== çıkış N" değilse
#                                                                                 sürüyor. timeout yok: yarıda kesilirse geri_don koşmaz)
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

echo "-- [1/7] kaynak: $GIT_URL"
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

echo "-- [2/7] sürüm dizini: $HEDEF"
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
  echo "-- [3/7] sanal ortam ve içe aktarma denetimi"
  if [ -n "${PM_VENV_ATLA:-}" ]; then
    install -d -m 755 "$HEDEF/venv/bin"
    printf '#!/bin/sh\nexec "%s" "$@"\n' "$(command -v "$PY")" > "$HEDEF/venv/bin/python"; chmod 755 "$HEDEF/venv/bin/python"
    echo "   PM_VENV_ATLA: venv yerine $PY sarmalandı"
  else
    "$PY" -m venv "$HEDEF/venv" || dur "venv açılamadı (python3-venv kurulu mu?)"
    "$HEDEF/venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 || true
    [ -f "$HEDEF/vps/gereksinimler.txt" ] || dur "vps/gereksinimler.txt yok (sunucu paket listesi; v2026.10.10 ve sonrası etiketlerde var)"
    "$HEDEF/venv/bin/pip" install -q --no-cache-dir -r "$HEDEF/vps/gereksinimler.txt" \
      || dur "paketler kurulamadı (vps/gereksinimler.txt; tam sabit; K19 › Uygulanış 2); ağ ve pip çıktısı yukarıda"
    [ -x "$HEDEF/venv/bin/gunicorn" ] || dur "gunicorn kurulmadı"
  fi
  VPY="$HEDEF/venv/bin/python"
  "$VPY" - "$HEDEF" <<'PY' || dur "içe aktarma denetimi düştü; sürüm etkinleştirilmedi (numpy X86_V2 hatasıysa işlemci tipi değişmiş demektir: K19 › Uygulanış 2, geri dönüş numpy 1.26.4)"
import sys
kok = sys.argv[1]; sys.path[:0] = [kok, kok + "/kanal"]
import numpy, ezdxf, fitz, shapely, psycopg, matplotlib, PIL, ifcopenshell, pydantic   # noqa
# K19 (Uygulanış 2, BK-07): numpy 2.x; içe aktarma yetmez, derlenmiş çekirdek bu işlemcide gerçekten çalışmalı (X86_V2 hatası ilk
# işlemde çıkar; işlemci tipi "host"tan geri alınırsa burada durur, sürüm etkinleşmez — güvenli duruş)
a = numpy.arange(12, dtype=float).reshape(3, 4)
iz = float((a @ a.T).trace()); kok2 = float(numpy.sqrt(numpy.array([16.0]))[0])
assert abs(iz - 506.0) < 1e-9 and abs(kok2 - 4.0) < 1e-12, (iz, kok2)
import beyin.karar, motor.dxf_out, kalici, webhook, panel, gonderici, ayarlar, nabiz, meta_api   # noqa
import motor.genel.uret, motor.genel.iz   # noqa  (İE-08: genel motor paketi; kural kitabı ve modeller sürümle gider)
import os
for p in ("kurallar/liste/kurallar.json", "kurallar/cizim/cizim_seti.json", "modeller/C8801.json", "modeller/altin.json"):
    assert os.path.exists(os.path.join(kok, p)), f"sürüm ağacında {p} yok (İE-08: kurallar/ ve modeller/ sürümle gider)"
print(f"   içe aktarma tamam: python {sys.version.split()[0]} · numpy {numpy.__version__} (hesap tamam) · ezdxf {ezdxf.__version__} · matplotlib {matplotlib.__version__}"
      f" · pillow {PIL.__version__} · PyMuPDF {getattr(fitz, 'VersionBind', '?')} · shapely {shapely.__version__}"
      f" · psycopg {psycopg.__version__} · pydantic {pydantic.__version__} · ifcopenshell {ifcopenshell.version}")
PY
  echo "-- [3b/7] perspektif denemesi (BK-07: VTK ekransız çizebiliyor mu; AYRI süreç, en çok 60 sn; sonuç ne olursa olsun sürüm etkinleşir)"
  # vtk kurulu mu: find_spec içe aktarmaz (import vtk, OSMesa/EGL yokken çökebilir; çökme "kurulu değil" sanılmasın)
  if [ -f "$HEDEF/vps/perspektif_dene.py" ] && "$VPY" -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("vtk") else 1)' >/dev/null 2>&1; then
    PERS_DIR="$(mktemp -d)"; RC=0
    timeout 60 "$VPY" "$HEDEF/vps/perspektif_dene.py" "$PERS_DIR" > "$PERS_DIR/cikti.txt" 2>/dev/null || RC=$?
    PERS="$(tail -n 1 "$PERS_DIR/cikti.txt" 2>/dev/null || true)"; rm -rf "$PERS_DIR"     # deneme PNG'si ve çıktısı; kalıcı iz yok
    if [ "$RC" = "124" ]; then PERS="ÇİZİLEMEDİ (60 sn içinde bitmedi)"
    elif [ "$RC" -ge 128 ] 2>/dev/null; then PERS="ÇİZİLEMEDİ (süreç çöktü, sinyal $((RC - 128)); libOSMesa/EGL kurulu değil: apt-get install libosmesa6, Lokman'ın onayıyla)"
    elif [ -z "$PERS" ]; then PERS="ÇİZİLEMEDİ (çıktı yok, çıkış kodu $RC)"; fi
    case "$PERS" in TAMAM*) ;; *) PERS="$PERS → pilot perspektifsiz (Lokman 11.10)" ;; esac
  else
    PERS="VTK yok (denenmedi; vps/gereksinimler.txt'te vtk yoksa ya da kurulmadıysa) → pilot perspektifsiz"
  fi
  echo "   perspektif: $PERS"
  printf '%s · %s\n' "$PERS" "$(date '+%Y-%m-%d %H:%M:%S')" > "$HEDEF/PERSPEKTIF"
  echo "-- [3c/7] genel motor denemesi (İE-08: Ç8801 ana koddaki paketle çizilir, altın değerle karşılaştırılır; AYRI süreç, en çok 120 sn; bilgi amaçlı, sürüm etkinleşir)"
  if [ -f "$HEDEF/vps/genel_dene.py" ]; then
    GENEL_DIR="$(mktemp -d)"; RC=0
    timeout 120 "$VPY" "$HEDEF/vps/genel_dene.py" "$GENEL_DIR" > "$GENEL_DIR/cikti.txt" 2>/dev/null || RC=$?
    GENEL="$(tail -n 1 "$GENEL_DIR/cikti.txt" 2>/dev/null || true)"; rm -rf "$GENEL_DIR"     # deneme çıktıları; kalıcı iz yok
    if [ "$RC" = "124" ]; then GENEL="ÇİZİLEMEDİ (120 sn içinde bitmedi)"
    elif [ "$RC" -ge 128 ] 2>/dev/null; then GENEL="ÇİZİLEMEDİ (süreç çöktü, sinyal $((RC - 128)))"
    elif [ -z "$GENEL" ]; then GENEL="ÇİZİLEMEDİ (çıktı yok, çıkış kodu $RC)"; fi
    case "$GENEL" in AYNI*) ;; *) GENEL="$GENEL → Lokman karar verir (İE-08 Soru 17; çelik adaylar kosullu yapılabilir)" ;; esac
  else
    GENEL="yok (vps/genel_dene.py bu sürümde yok; İE-08 öncesi etiket)"
  fi
  echo "   genel motor: $GENEL"
  printf '%s · %s\n' "$GENEL" "$(date '+%Y-%m-%d %H:%M:%S')" > "$HEDEF/GENEL"
  date '+%Y-%m-%d %H:%M:%S' > "$HEDEF/KURULDU"
fi
VPY="$HEDEF/venv/bin/python"

echo "-- [4/7] göçler (kalici.py goc; yalnız eksikler, yalnız ekler)"
GOC="$("${OLARAK[@]}" env PORTMAN_PG_DSN="$PG_DSN" PORTMAN_KANAL_DIR="$KOK/data" "$VPY" "$HEDEF/kanal/kalici.py" goc 2>&1)" || { echo "$GOC" | tail -5; dur "göç uygulanamadı; sürüm etkinleştirilmedi"; }
echo "   $GOC"

echo "-- [5/7] bağlantılar ve servisler"
ESKI="$( [ -L "$KOK/guncel" ] && readlink -f "$KOK/guncel" || true )"
$SYSTEMCTL stop $SERVISLER >/dev/null 2>&1 || true
if [ -n "$ESKI" ] && [ "$ESKI" != "$(readlink -f "$HEDEF")" ]; then
  ln -sfn "$ESKI" "$KOK/onceki.yeni"; mv -T "$KOK/onceki.yeni" "$KOK/onceki"
fi
ln -sfn "$HEDEF" "$KOK/guncel.yeni"; mv -T "$KOK/guncel.yeni" "$KOK/guncel"
$SYSTEMCTL daemon-reload >/dev/null 2>&1 || true
$SYSTEMCTL start $SERVISLER || dur "servisler başlatılamadı (journalctl -u portman-webhook)"
echo "   guncel → $(readlink "$KOK/guncel") · onceki → $( [ -L "$KOK/onceki" ] && readlink "$KOK/onceki" || echo yok)"

echo "-- [6/7] sağlık: $SAGLIK_URL (en çok $SAGLIK_BEKLE sn; ölçüt: cevapta surum=$ETIKET ve postgres=true — nabiz.sh'nin eski sorunları bu kapıyı düşürmez)"
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

echo "-- [7/7] nginx yapılandırması (BK-07: sürümdeki vps/nginx/portman.conf; nginx -t, yedek, reload; hata sürümü düşürmez)"
if [ -f "$HEDEF/vps/nginx_uygula.sh" ]; then
  PM_ETC="$ETC" PM_SYSTEMCTL="$SYSTEMCTL" PM_TEST="$TEST" bash "$HEDEF/vps/nginx_uygula.sh" "$HEDEF" 2>&1 | sed 's/^/   /' || echo "   UYARI: nginx yapılandırması uygulanamadı; sürüm etkin, eski nginx yapılandırması duruyor (bash $HEDEF/vps/nginx_uygula.sh $HEDEF)" >&2
else
  echo "   nginx_uygula.sh bu sürümde yok; atlandı"
fi
if [ -z "$TEST" ] && [ -f "$HEDEF/vps/durum.sh" ]; then bash "$HEDEF/vps/durum.sh" || true; fi
echo "== bitti: $ETIKET etkin ($(date '+%Y-%m-%d %H:%M:%S %Z'))"
