#!/usr/bin/env bash
# PORTMAN · günlük şifreli yedek (İE-06, karar 9; root; portman-yedek.timer her gece 03:40; elle de koşar).
# pg_dump -Fc portman + /opt/portman/data (nabiz/, checks/, .mpl hariç) → tar → age -r <yedek.pub> → portman-<zaman>.tar.age →
# rclone copy portman-drive:Portman-Yedek/ · Drive'da PM_SAKLA_GUN (30) günden eski KENDİ dosyaları (portman-*.tar.age) silinir ·
# yerelde (/var/backups/portman) en yeni PM_YEREL_TUT (3) kalır. /etc/portman yedeğe GİRMEZ (sırlar). Sonuç data/nabiz/yedek.json'a
# (nabiz.sh yaşına bakar). Geri yükleme: Mac'te age -d, sonra yedek_geri_dene.sh. Yedek yapılandırılmamışsa (yedek.pub ya da
# rclone.conf yok) uyarır ve 0 ile çıkar (Kapı 5'e kadar normal). Çıktıda sır yok.
# Sınama: PM_KOK, PM_ETC, PM_YEDEK_DIR, PM_DB, PM_PG_DUMP, PM_AGE, PM_RCLONE, PM_SAKLA_GUN, PM_YEREL_TUT, PM_UZAK.
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; DATA="$KOK/data"
YEDEK_DIR="${PM_YEDEK_DIR:-/var/backups/portman}"; DB="${PM_DB:-portman}"
PG_DUMP="${PM_PG_DUMP:-sudo -u postgres pg_dump}"; AGE="${PM_AGE:-age}"; RCLONE="${PM_RCLONE:-rclone}"
SAKLA="${PM_SAKLA_GUN:-30}"; TUT="${PM_YEREL_TUT:-3}"; UZAK="${PM_UZAK:-portman-drive:Portman-Yedek}"
CONF="$ETC/rclone.conf"; PUB="$ETC/yedek.pub"
dur() { echo "DUR: $*" >&2; exit 1; }
[[ "$SAKLA" =~ ^[1-9][0-9]{0,3}$ ]] || dur "PM_SAKLA_GUN 1–9999 olmalı"
[[ "$TUT" =~ ^[1-9][0-9]?$ ]] || dur "PM_YEREL_TUT 1–99 olmalı"
echo "== Portman yedek · $(date '+%Y-%m-%d %H:%M:%S %Z')"
if [ ! -s "$PUB" ] || [ ! -s "$CONF" ]; then
  echo "   yedek yapılandırılmadı (yedek_kur.sh age ve drive); yedek alınmadı"; exit 0
fi
cd /tmp; umask 077
install -d -m 700 "$YEDEK_DIR"
ZAMAN="$(date +%Y%m%d-%H%M%S)"; AD="portman-$ZAMAN.tar.age"
GECICI="$(mktemp -d "$YEDEK_DIR/.gecici.XXXXXX")"
trap 'rm -rf "$GECICI"' EXIT
$PG_DUMP -Fc -d "$DB" > "$GECICI/portman.dump" || dur "pg_dump başarısız"
[ -s "$GECICI/portman.dump" ] || dur "pg_dump boş çıktı verdi"
tar -C "$KOK" --exclude='data/nabiz' --exclude='data/checks' --exclude='data/.mpl' --exclude='*.tmp' -cf "$GECICI/data.tar" data || dur "data arşivi alınamadı"
tar -C "$GECICI" -cf - portman.dump data.tar | $AGE -r "$(cat "$PUB")" -o "$GECICI/$AD" || dur "age şifreleme başarısız"
mv "$GECICI/$AD" "$YEDEK_DIR/$AD"; chmod 600 "$YEDEK_DIR/$AD"
BOYUT="$(stat -c %s "$YEDEK_DIR/$AD")"; SHA="$(sha256sum "$YEDEK_DIR/$AD" | cut -c1-64)"
echo "   $AD · $BOYUT B · sha256 ${SHA:0:16}… (dump $(stat -c %s "$GECICI/portman.dump") B, data $(stat -c %s "$GECICI/data.tar") B)"
$RCLONE --config "$CONF" copy "$YEDEK_DIR/$AD" "$UZAK/" || dur "Drive'a kopyalama başarısız; dosya yerelde: $YEDEK_DIR/$AD"
echo "   Drive'a kopyalandı: $UZAK/$AD"
$RCLONE --config "$CONF" delete --min-age "${SAKLA}d" --include 'portman-*.tar.age' "$UZAK/" >/dev/null 2>&1 \
  && echo "   Drive: $SAKLA günden eski portman-*.tar.age dosyaları silindi" || echo "   UYARI: Drive'daki eski yedekler silinemedi (sonraki koşuda yeniden)"
ESKI="$(ls -1t "$YEDEK_DIR"/portman-*.tar.age 2>/dev/null | tail -n +$((TUT + 1)) || true)"
if [ -n "$ESKI" ]; then echo "$ESKI" | xargs -r rm -f; echo "   yerelde en yeni $TUT dosya kaldı ($(echo "$ESKI" | wc -l) eski silindi)"; fi
SAHIP=""; id -u portman >/dev/null 2>&1 && SAHIP="-o portman -g portman"
install -d -m 755 $SAHIP "$DATA/nabiz"
printf '{"zaman": %s, "ad": "yedek", "dosya": "%s", "boyut": %s, "sha256": "%s", "uzak": "%s"}\n' "$(date +%s)" "$AD" "$BOYUT" "$SHA" "$UZAK" > "$DATA/nabiz/yedek.json.tmp"
chmod 644 "$DATA/nabiz/yedek.json.tmp"; [ -n "$SAHIP" ] && chown portman:portman "$DATA/nabiz/yedek.json.tmp"
mv -f "$DATA/nabiz/yedek.json.tmp" "$DATA/nabiz/yedek.json"
echo "== bitti ($(date '+%H:%M:%S'))"
