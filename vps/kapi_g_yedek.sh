#!/usr/bin/env bash
# PORTMAN · Kapı G (İE-02) ve sonraki kapılar (M: İE-04): canlı portman veritabanının yedeği (pg_dump -Fc). Ad: portman-<kapı>-<ne>-<tarih>. Yalnız /var/backups/portman altına YENİ bir dosya
# yazar; var olan hiçbir yedeği silmez, üzerine yazmaz. Veritabanını değiştirmez.
#   ssh portman-vps 'PM_AD=portman-g-oncesi-20260929 bash -s' < kapi_g_yedek.sh > 0_pg_yedek.txt
#   scp portman-vps:/var/backups/portman/portman-g-oncesi-20260929.dump yedek/
# Gösterir: dosya, boyut, sahip, sha256; pg_restore ile okunabildiği ve içindeki tablo verisi girdileri; yedek anındaki kayıt
# sayıları. Yazdırmaz: numara, mesaj metni, anahtar.
# Test için: PM_YEDEK, PM_PSQL, PM_PGDUMP, PM_PGRESTORE, PM_DB.
# Gövde tek işlevdir ve girdisi /dev/null'dur (bkz. kapi_f_*.sh: 'bash -s' betiğinin kalanını sudo yutmasın).
ana() {
set -u
cd /tmp
YEDEK="${PM_YEDEK:-/var/backups/portman}"; AD="${PM_AD:-}"; DB="${PM_DB:-portman}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA}"; PGDUMP="${PM_PGDUMP:-sudo -u postgres pg_dump}"; PGRESTORE="${PM_PGRESTORE:-sudo -u postgres pg_restore}"
echo "== Kapı G · Postgres yedeği · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
[[ "$AD" =~ ^portman-[a-z0-9]{1,3}-[a-z]+-[0-9]{8}(-[0-9]+)?$ ]] || { echo "DUR: PM_AD verilmedi ya da biçimi yanlış (ör. portman-g-oncesi-20260929, portman-m-oncesi-20260930)"; exit 1; }
DOSYA="$YEDEK/$AD.dump"
[ -e "$DOSYA" ] && { echo "DUR: $DOSYA zaten var; üzerine yazılmaz (özeti $(sha256sum "$DOSYA" | cut -d' ' -f1))"; exit 1; }
[ -d "$YEDEK" ] || { echo "DUR: $YEDEK yok (kapı D'de kurulmuştu)"; exit 1; }
echo "   yedek anındaki kayıtlar: $($PSQL -d "$DB" -c "SELECT 'konusmalar ' || (SELECT count(*) FROM konusmalar) || ' · mesajlar ' || (SELECT count(*) FROM mesajlar) || ' · isler ' || (SELECT count(*) FROM isler) || ' · projeler ' || (SELECT count(*) FROM projeler) || ' · revizyonlar ' || (SELECT count(*) FROM revizyonlar) || ' · sorular ' || (SELECT count(*) FROM sorular) || ' · giden ' || (SELECT count(*) FROM giden)" 2>&1)"
$PGDUMP -Fc -d "$DB" -f "$DOSYA" || { echo "DUR: pg_dump başarısız (yarım dosya varsa silinmedi: $DOSYA)"; exit 1; }
chmod 600 "$DOSYA"
echo "   dosya: $DOSYA · $(stat -c '%s' "$DOSYA") B · $(stat -c '%U:%G %a' "$DOSYA")"
echo "   sha256: $(sha256sum "$DOSYA" | cut -d' ' -f1)"
LISTE="$($PGRESTORE --list "$DOSYA" 2>&1)"; RC=$?
echo "   pg_restore ile okunuyor: $([ "$RC" = "0" ] && echo evet || echo HAYIR) · tablo verisi girdileri: $(grep -c 'TABLE DATA' <<< "$LISTE") · $(grep 'TABLE DATA' <<< "$LISTE" | awk '{print $(NF-1)}' | sort | tr '\n' ' ')"
echo "   /var/backups/portman'daki öteki yedekler (dokunulmadı): $(ls -1 "$YEDEK" | grep -vx "$AD.dump" | tr '\n' ' ')"
echo "== bitti"
}
ana "$@" < /dev/null
