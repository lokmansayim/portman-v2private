#!/usr/bin/env bash
# PORTMAN · geri yükleme denemesi (İE-06, Kapı 10; root). Mac'te `age -d -i ~/.config/portman/yedek.key portman-<zaman>.tar.age |
# tar -x` ile çıkan portman.dump dosyası scp ile VPS'e konur; bu betik onu YALNIZ bu çalıştırmanın açıp işaretlediği deneme
# veritabanına (portman_geri_deneme_<çalışma>) yükler, tablo kümesini ve satır sayılarını canlıyla yan yana yazar, deneme
# veritabanını siler. Canlı 'portman' veritabanına DOKUNMAZ; aynı adda başka bir deneme veritabanı varsa dokunmaz ve durur;
# geri yükleme başarısızsa deneme veritabanı incelenmek üzere bırakılır (pg_kurulum.sh'nin kapı D kuralı).
#   scp portman.dump portman-vps:/root/ && ssh portman-vps 'bash /opt/portman/guncel/vps/yedek_geri_dene.sh /root/portman.dump' > ie06_10_geri.txt 2>&1
# Sınama: PM_PG (psql/pg_restore seçenekleri; verilince sudo kullanılmaz), PM_DB, PM_CALISMA.
set -euo pipefail
DOSYA="${1:-}"; DB="${PM_DB:-portman}"
if [ -n "${PM_PG+x}" ]; then read -r -a PG <<< "$PM_PG"; SU=(); else PG=(); SU=(sudo -u postgres); fi
dur() { echo "DUR: $*" >&2; exit 1; }
psql_su() { "${SU[@]}" psql -X -q -v ON_ERROR_STOP=1 "${PG[@]}" "$@"; }
kimlik() { [[ "$1" =~ ^[a-z_][a-z0-9_]*$ ]] || dur "geçersiz ad: $1"; }
[ -s "$DOSYA" ] || dur "dump dosyası verilmedi ya da boş: '${DOSYA}'"
kimlik "$DB"
cd /tmp
echo "== Portman geri yükleme denemesi · $(date '+%Y-%m-%d %H:%M:%S %Z') · dosya $(basename "$DOSYA") ($(stat -c %s "$DOSYA") B, sha256 $(sha256sum "$DOSYA" | cut -c1-16)…)"
[ "$(psql_su -tAc "SELECT count(*) FROM pg_database WHERE datname = '$DB'")" = "1" ] || dur "canlı veritabanı yok: $DB"
CALISMA="${PM_CALISMA:-$(date +%Y%m%d%H%M%S)_$$}"
DENEME="portman_geri_deneme_${CALISMA}"; kimlik "$DENEME"
ISARET="portman-geri-yukleme-denemesi:${CALISMA}"
[ "$(psql_su -tAc "SELECT count(*) FROM pg_database WHERE datname = '$DENEME'")" = "0" ] || dur "'$DENEME' zaten var; dokunulmadı"
psql_su -c "CREATE DATABASE $DENEME" -c "COMMENT ON DATABASE $DENEME IS '$ISARET'"
if ! "${SU[@]}" pg_restore --exit-on-error "${PG[@]}" -d "$DENEME" < "$DOSYA"; then     # stdin: postgres kullanıcısı /root'u okuyamaz
  dur "geri yükleme başarısız; '$DENEME' incelenmek üzere bırakıldı (dump bozuk ya da sürüm uyumsuz)"
fi
echo "-- tablolar (canlı $DB | deneme): satır sayıları"
TABLOLAR_D="$(psql_su -d "$DENEME" -tAc "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")"
TABLOLAR_C="$(psql_su -d "$DB" -tAc "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")"
FARK=0
while IFS= read -r t; do
  [ -n "$t" ] || continue
  nd="$(psql_su -d "$DENEME" -tAc "SELECT count(*) FROM \"$t\"")"
  nc="$(psql_su -d "$DB" -tAc "SELECT count(*) FROM \"$t\"" 2>/dev/null || echo yok)"
  durum="AYNI"; [ "$nd" = "$nc" ] || { durum="FARKLI"; FARK=$((FARK + 1)); }
  printf '   %-22s canlı %8s | deneme %8s  %s\n' "$t" "$nc" "$nd" "$durum"
done <<< "$TABLOLAR_D"
if [ "$TABLOLAR_D" = "$TABLOLAR_C" ]; then echo "   tablo kümesi: AYNI ($(echo "$TABLOLAR_D" | grep -c . ) tablo)"; else echo "   tablo kümesi: FARKLI (canlıda sonradan göç olabilir; dump eski sürümden)"; fi
echo "   satır sayısı farkı olan tablo: $FARK (yedekten sonra gelen kayıtlar normaldir)"
SURUM_D="$(psql_su -d "$DENEME" -tAc "SELECT max(surum) FROM sema_surumu" 2>/dev/null || echo '?')"
echo "   dump şema sürümü: $SURUM_D · canlı: $(psql_su -d "$DB" -tAc "SELECT max(surum) FROM sema_surumu" 2>/dev/null || echo '?')"
if [ "$(psql_su -tAc "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = '$DENEME'")" = "$ISARET" ]; then
  psql_su -c "DROP DATABASE $DENEME"
  echo "   deneme veritabanı silindi (bu çalıştırmanın açıp işaretlediği: $DENEME)"
else
  dur "'$DENEME' işareti beklenenle aynı değil; silinmedi"
fi
echo "== bitti: geri yükleme denemesi tamam; canlıya dokunulmadı"
