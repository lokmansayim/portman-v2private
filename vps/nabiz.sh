#!/usr/bin/env bash
# PORTMAN · nabız denetimi (İE-06, karar 10; root; portman-nabiz.timer 5 dakikada bir). Bakar: dört servis, Postgres, sertifika
# (≥ PM_SERT_GUN=14 gün), disk (< PM_DISK_ESIK=%90), son yedek yaşı (< PM_YEDEK_SAAT=26; yalnız yedek kuruluysa), ajan ve
# gönderici nabzı (< PM_NABIZ_SN=180 sn; yalnız kanal açıkken). Sonuç data/nabiz/nabiz.json'a yazılır; webhook /saglik bu
# dosyadaki sorunları 503'e sayar (dış izleyici görür). Sorun varsa Patron'a WhatsApp metni: uyari_gonder.py (24 saat penceresi
# açıksa; aynı sorun 6 saatte bir). Hiçbir şeyi değiştirmez; her zaman 0 ile çıkar (zamanlayıcı düşmesin). Çıktıda sır ve numara yok.
# Sınama: PM_KOK, PM_ETC, PM_SYSTEMCTL, PM_PSQL, PM_LE_DIR, PM_ALAN, PM_UYARI (komut), PM_DISK_ESIK, PM_YEDEK_SAAT, PM_NABIZ_SN, PM_SERT_GUN.
set -uo pipefail
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; DATA="$KOK/data"
SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"
LE_DIR="${PM_LE_DIR:-/etc/letsencrypt}"; ALAN="${PM_ALAN:-$(cat "$ETC/alan" 2>/dev/null || true)}"
DISK_ESIK="${PM_DISK_ESIK:-90}"; YEDEK_SAAT="${PM_YEDEK_SAAT:-26}"; NABIZ_SN="${PM_NABIZ_SN:-180}"; SERT_GUN="${PM_SERT_GUN:-14}"
UYARI="${PM_UYARI:-$KOK/guncel/venv/bin/python $KOK/guncel/vps/uyari_gonder.py}"
if [ -n "${PM_OLARAK+x}" ]; then read -r -a OLARAK <<< "$PM_OLARAK"; else OLARAK=(runuser -u portman --); fi   # uyarı portman olarak (peer: root rolü yok)
SAHIP=""; id -u portman >/dev/null 2>&1 && SAHIP="-o portman -g portman"
SIMDI="$(date +%s)"
SORUN=()
cd /tmp

for s in portman-webhook portman-gonderici portman-agent portman-panel; do
  d="$($SYSTEMCTL is-active "$s" 2>/dev/null || true)"
  [ "$d" = "active" ] || SORUN+=("$s: ${d:-bilinmiyor}")
done
$PSQL -c "SELECT 1" >/dev/null 2>&1 || SORUN+=("postgres: bağlanılamadı")
if [ -n "$ALAN" ]; then
  SERT="$LE_DIR/live/$ALAN/fullchain.pem"
  if [ -f "$SERT" ]; then
    BITIS="$(openssl x509 -enddate -noout -in "$SERT" 2>/dev/null | cut -d= -f2 || true)"
    if [ -n "$BITIS" ]; then
      GUN=$(( ( $(date -d "$BITIS" +%s) - SIMDI ) / 86400 ))
      [ "$GUN" -ge "$SERT_GUN" ] || SORUN+=("sertifika: $GUN gün kaldı (certbot renew)")
    else
      SORUN+=("sertifika: okunamadı")
    fi
  else
    SORUN+=("sertifika: yok (kurulum.sh Kapı 3)")
  fi
fi
YUZDE="$(df --output=pcent "$KOK" 2>/dev/null | tail -1 | tr -dc '0-9' || true)"
if [ -n "$YUZDE" ] && [ "$YUZDE" -ge "$DISK_ESIK" ]; then SORUN+=("disk: %$YUZDE dolu"); fi
if [ -s "$ETC/yedek.pub" ] && [ -s "$ETC/rclone.conf" ]; then
  YZ="$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1])).get("zaman", 0)))' "$DATA/nabiz/yedek.json" 2>/dev/null || echo 0)"
  if [ "$YZ" = "0" ]; then SORUN+=("yedek: hiç alınmadı")
  elif [ $(( SIMDI - YZ )) -gt $(( YEDEK_SAAT * 3600 )) ]; then SORUN+=("yedek: $(( (SIMDI - YZ) / 3600 )) saat önce (sınır $YEDEK_SAAT)"); fi
fi
ACIK="$(python3 -c 'import json,sys; print("1" if json.load(open(sys.argv[1])).get("enabled") is True else "0")' "$DATA/settings.json" 2>/dev/null || echo 0)"
if [ "$ACIK" = "1" ]; then
  for ad in agent gonderici; do
    Z="$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1])).get("zaman", 0)))' "$DATA/nabiz/$ad.json" 2>/dev/null || echo 0)"
    if [ "$Z" = "0" ]; then SORUN+=("$ad: nabız yok")
    elif [ $(( SIMDI - Z )) -gt "$NABIZ_SN" ]; then SORUN+=("$ad: nabız $(( SIMDI - Z )) sn eski"); fi
  done
fi

install -d -m 755 $SAHIP "$DATA/nabiz" 2>/dev/null || true
python3 - "$DATA/nabiz/nabiz.json" "$SIMDI" "${SORUN[@]+"${SORUN[@]}"}" <<'PY' || true
import json, os, sys
yol, simdi, sorunlar = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
gecici = yol + ".tmp"
with open(gecici, "w", encoding="utf-8") as f:
    json.dump({"zaman": simdi, "ad": "nabiz", "sorunlar": sorunlar}, f, ensure_ascii=False)
os.chmod(gecici, 0o644); os.replace(gecici, yol)
PY
if [ ${#SORUN[@]} -eq 0 ]; then
  echo "nabız $(date '+%Y-%m-%d %H:%M:%S'): sorun yok"
else
  echo "nabız $(date '+%Y-%m-%d %H:%M:%S'): ${#SORUN[@]} sorun: $(IFS='; '; echo "${SORUN[*]}")"
  if [ -n "$UYARI" ]; then
    METIN="Portman uyarı ($(date '+%d.%m %H:%M')): $(IFS='; '; echo "${SORUN[*]}")"
    # Sıklık anahtarı yalnız sorun ADLARINDAN (':' öncesi; sıralı): zaman damgası ve sayılar değişse de aynı sorun 6 saatte bir gider
    ANAHTAR="$(printf '%s\n' "${SORUN[@]}" | cut -d: -f1 | sort -u | tr '\n' ';')"
    if [ -s "$ETC/whatsapp.env" ]; then set -a; . "$ETC/whatsapp.env"; set +a; fi      # WA_* ortamdan geçer; komut satırına çıkmaz
    "${OLARAK[@]}" env PORTMAN_PG_DSN="${PORTMAN_PG_DSN:-dbname=portman}" PORTMAN_KANAL_DIR="$DATA" $UYARI "$METIN" "$ANAHTAR" 2>&1 | sed 's/^/   /' || echo "   uyarı gönderilemedi"
  fi
fi
exit 0
