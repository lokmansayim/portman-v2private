#!/usr/bin/env bash
# PORTMAN · Kapı F: aktarma beklerken SALT OKUNUR teşhis. Hiçbir şeyi değiştirmez, hiçbir süreci durdurmaz.
#   ssh portman-vps 'bash -s' < kapi_f_teshis.sh > 5b_teshis.txt
# Gösterir: aktarmayla ilgili süreçler (süre, durum, bekleme noktası), portman veritabanındaki oturumlar (durum, bekleme türü,
# işlem süresi, kimin engellediği, sorgunun ilk 70 karakteri: psycopg değerleri $1 gibi yer tutucuyla gönderir), verilmemiş
# kilitler ve tablolardaki kayıt sayıları. Yazdırmaz: anahtar, numara, mesaj metni.
# Gövde tek işlevdir ve girdisi /dev/null'dur: 'bash -s' betiği girdiden okurken içindeki bir komut (ör. sudo) betiğin kalanını
# yutmasın (29.09 F.5'te aktarmadan sonraki satırlar böyle çalışmadı). Bash işlevi çalıştırmadan önce dosyanın tamamını okur.
ana() {
set -u
cd /tmp
echo "== Kapı F · aktarma teşhisi · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- süreçler (aktarma, göç, sudo)"
ps -eo pid,ppid,etimes,stat,wchan:22,user,args 2>/dev/null | grep -E "depo_aktar|kalici\.py|kapi_f|sudo -u portman|sudo -u postgres" | grep -v grep \
  | sed -E 's/[0-9]{10,}/<sayı>/g' | cut -c1-190 | sed 's/^/   /'
echo "-- portman veritabanındaki oturumlar"
sudo -u postgres psql -X -q -tA -F ' | ' -d postgres -c "SELECT pid, usename, coalesce(application_name, ''), state, coalesce(wait_event_type, '-'), coalesce(wait_event, '-'), coalesce(extract(epoch FROM now() - xact_start)::int, -1) AS islem_sn, pg_blocking_pids(pid), left(regexp_replace(query, '\s+', ' ', 'g'), 70) FROM pg_stat_activity WHERE datname = 'portman' AND pid <> pg_backend_pid()" 2>&1 | sed 's/^/   /'
echo "-- verilmemiş kilitler"
sudo -u postgres psql -X -q -tA -F ' | ' -d portman -c "SELECT pid, locktype, coalesce(relation::regclass::text, '-'), mode FROM pg_locks WHERE NOT granted" 2>&1 | sed 's/^/   /'
echo "-- kayıt sayıları (işlem bitmediyse 0 görünür)"
sudo -u postgres psql -X -q -tA -d portman -c "SELECT 'konusmalar ' || (SELECT count(*) FROM konusmalar) || ' · mesajlar ' || (SELECT count(*) FROM mesajlar) || ' · isler ' || (SELECT count(*) FROM isler) || ' · bayiler ' || (SELECT count(*) FROM bayiler)" 2>&1 | sed 's/^/   /'
echo "-- Postgres servisi: $(systemctl is-active postgresql 2>/dev/null) · portman-agent: $(systemctl is-active portman-agent 2>/dev/null)"
echo "== bitti"
}
ana "$@" < /dev/null
