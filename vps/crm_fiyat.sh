#!/usr/bin/env bash
# PORTMAN · CRM stok fiyatlarının günlük çekimi (İE-35, D-72, mühür M-15; root; portman-crm-fiyat.timer her gün 06:15; elle de koşar).
# Lokman, 9 Kasım 2026 13:10: "bundan sonra tek fiyat kaynağımız bu api olacak ve hergün fiyatları çek".
# POST <PM_CRM_ADRES> (IPv4 zorunlu: CRM'in Cloudflare kuralı bu sunucunun IPv4'ünü tanır; anahtar yok) → araclar/crm_fiyat.py denetle
# (biçim; satırda yalnız id, urunkodu, urunadi, olcu, birim, fiyat, kategori kalır; kalem sayısı bir öncekinin %80'inin altına
# düşerse görüntü alınmaz, eski fiyatlar yerinde kalır) → data/crm/crm_<zaman>.json ve data/crm/crm_son.json → rclone copy
# portman-drive:Portman-Fiyat/ (oturumlar teklifi oradaki en yeni görüntüyle üretir; rclone.conf yoksa atlanır). Sonuç
# data/crm/son_cekim.json'a. Hiçbir dosya silinmez (görüntü ~80 KB; yedek.sh data/ ile şifreli yedeğe alır). Çıktıda sır yok.
#   ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/crm_fiyat.sh' > crm_fiyat.txt 2>&1
# Sınama: PM_KOK, PM_ETC, PM_GUNCEL, PM_PYTHON, PM_CURL, PM_RCLONE, PM_UZAK, PM_CRM_ADRES.
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; DATA="$KOK/data"; HEDEF="$DATA/crm"
GUNCEL="${PM_GUNCEL:-$KOK/guncel}"; PY="${PM_PYTHON:-python3}"
CURL="${PM_CURL:-curl}"; RCLONE="${PM_RCLONE:-rclone}"; UZAK="${PM_UZAK:-portman-drive:Portman-Fiyat}"
ADRES="${PM_CRM_ADRES:-https://crm.ikranuryapi.com.tr/api/stok-fiyatlari}"
CONF="$ETC/rclone.conf"
dur() { echo "DUR: $*" >&2; exit 1; }
echo "== Portman CRM fiyat çekimi · $(date '+%Y-%m-%d %H:%M:%S %Z')"
[ -f "$GUNCEL/araclar/crm_fiyat.py" ] || dur "araclar/crm_fiyat.py yok ($GUNCEL): sürüm İE-35'ten eski mi?"
SAHIP=""; id -u portman >/dev/null 2>&1 && SAHIP="-o portman -g portman"
umask 022
install -d -m 755 $SAHIP "$HEDEF"
GECICI="$(mktemp -d "$HEDEF/.gecici.XXXXXX")"
trap 'rm -rf "$GECICI"' EXIT
cd /tmp

KOD="$($CURL -4 -sS --max-time 60 -o "$GECICI/ham.json" -w '%{http_code}' -X POST \
  -H 'Accept: application/json' -H 'Content-Type: application/json' --data '{}' "$ADRES")" || dur "CRM'e ulaşılamadı; eski fiyatlar yerinde"
[ "$KOD" = "200" ] || dur "CRM HTTP $KOD (403 ise Cloudflare kuralı bu sunucunun IPv4'ünü tanımıyor olabilir); eski fiyatlar yerinde"
ONCEKI=(); [ -s "$HEDEF/crm_son.json" ] && ONCEKI=(--onceki "$HEDEF/crm_son.json")
"$PY" "$GUNCEL/araclar/crm_fiyat.py" denetle "$GECICI/ham.json" --yaz "$GECICI/anlik.json" "${ONCEKI[@]}" \
  || dur "CRM yanıtı denetimden geçmedi; eski fiyatlar yerinde"

ZAMAN="$(date +%Y%m%d-%H%M%S)"; AD="crm_$ZAMAN.json"
chmod 644 "$GECICI/anlik.json"; [ -n "$SAHIP" ] && chown portman:portman "$GECICI/anlik.json"
cp -p "$GECICI/anlik.json" "$HEDEF/.crm_son.json.yeni"
mv "$GECICI/anlik.json" "$HEDEF/$AD"
mv -f "$HEDEF/.crm_son.json.yeni" "$HEDEF/crm_son.json"
BOYUT="$(stat -c %s "$HEDEF/$AD")"; SHA="$(sha256sum "$HEDEF/$AD" | cut -c1-64)"
echo "   $AD · $BOYUT B · sha256 ${SHA:0:16}…"

UZAKTA="atlandı (rclone.conf yok)"
if [ -s "$CONF" ]; then
  if $RCLONE --config "$CONF" copy "$HEDEF/$AD" "$UZAK/"; then
    UZAKTA="$UZAK/$AD"; echo "   Drive'a kopyalandı: $UZAKTA"
  else
    UZAKTA="başarısız"; echo "   UYARI: Drive'a kopyalanamadı; görüntü sunucuda: $HEDEF/$AD (sonraki koşuda yeni görüntü gider)"
  fi
else
  echo "   Drive: $UZAKTA"
fi
printf '{"zaman": %s, "dosya": "%s", "boyut": %s, "sha256": "%s", "uzak": "%s"}\n' "$(date +%s)" "$AD" "$BOYUT" "$SHA" "$UZAKTA" > "$HEDEF/.son_cekim.json.yeni"
chmod 644 "$HEDEF/.son_cekim.json.yeni"; [ -n "$SAHIP" ] && chown portman:portman "$HEDEF/.son_cekim.json.yeni"
mv -f "$HEDEF/.son_cekim.json.yeni" "$HEDEF/son_cekim.json"
echo "== bitti ($(date '+%H:%M:%S'))"
