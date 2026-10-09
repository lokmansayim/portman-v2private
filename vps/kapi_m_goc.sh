#!/usr/bin/env bash
# PORTMAN · Kapı M (İE-04, adım M1.4): canlı Postgres'e göç 003'ü (mesaj katmanı; YALNIZ EKLER) uygular. Değişiklik yapan tek komut:
#   /opt/portman/app/kalici.py goc   (portman kullanıcısı olarak, PORTMAN_PG_DSN=dbname=portman; kapı F'teki göçle aynı yol)
# Ön koşullar (biri tutmazsa hiçbir şey yapılmaz):
#   - kurulu paket beklenen v1.3 paketi (PM_BEKLENEN = current.sha256) ve app/goc/003_mesaj_katmani.sql var;
#   - son 3 saat içinde alınmış bir yedek var: /var/backups/portman/portman-m-oncesi-*.dump (kapi_g_yedek.sh; Mac'e kopyalanmış olmalı);
#   - Postgres'te açık iş yok (durum sirada/isleniyor) ve eksik göç tam olarak [3].
# Ne yapar: giden.kind kontrolüne 'image' ve 'interactive' eklenir; revizyonlar.ekler (jsonb, varsayılan {}) eklenir; secenek_setleri ve
#   adaylar tabloları açılır. Var olan hiçbir satır, sütun ya da tablo değişmez/silinmez; v1.2 kodu bu eklere bakmaz.
# Geri alma: gerekmez (ekler durabilir). Veritabanı yedekle EZİLMEZ (Lokman kuralı); yedek yalnız ayrı bir veritabanına geri yükleme içindir.
#   ssh portman-vps 'PM_BEKLENEN=<v1.3 current.sha256> bash -s' < kapi_m_goc.sh > 4_goc.txt
# Yazdırmaz: anahtar, numara, mesaj metni. Test için: PM_HOME, PM_PY, PM_OLARAK, PM_YEDEK, PM_TEST=1 (ön koşullar denetlenir, göç UYGULANMAZ).
# Gövde tek işlevdir ve girdisi /dev/null'dur; Python kodu -c ile verilir (sudo girdiyi yutmasın; bkz. kapi_f_kalici_ac.sh).
ana() {
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PY="${PM_PY:-$PM_HOME/venv/bin/python}"; APP="$PM_HOME/app"; YEDEK="${PM_YEDEK:-/var/backups/portman}"
OLARAK="${PM_OLARAK:-sudo -u portman env PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=$PM_HOME/data}"
BEK="${PM_BEKLENEN:-}"
dur() { echo "DUR: $*"; echo "   hiçbir şey değiştirilmedi."; echo "== bitti (durdu)"; exit 1; }
echo "== Kapı M · göç 003 (mesaj katmanı) · betik 2026-09-30 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- ön koşullar"
[[ "$BEK" =~ ^[0-9a-f]{64}$ ]] || dur "PM_BEKLENEN verilmedi (v1.3 paketinin 64 haneli sha256'sı)"
KURULU="$(cat "$APP/PACKAGE_SHA256" 2>/dev/null || echo -)"
echo "   kurulu paket: ${KURULU:0:16}… · beklenen: ${BEK:0:16}… · aynı: $([[ "$KURULU" == "$BEK" ]] && echo EVET || echo HAYIR) · sürüm: $(cat "$APP/SURUM.txt" 2>/dev/null || echo -)"
[[ "$KURULU" == "$BEK" ]] || dur "kurulu paket beklenen değil; önce v1.3 paketi kurulmuş olmalı (M1.3)"
[ -f "$APP/goc/003_mesaj_katmani.sql" ] || dur "$APP/goc/003_mesaj_katmani.sql yok"
YD="$(ls -t "$YEDEK"/portman-m-oncesi-*.dump 2>/dev/null | head -1 || true)"
[ -n "$YD" ] || dur "yedek yok ($YEDEK/portman-m-oncesi-*.dump; kapi_g_yedek.sh ile alın, Mac'e kopyalayın)"
YAS=$(( $(date +%s) - $(stat -c %Y "$YD") ))
echo "   yedek: $(basename "$YD") · $(stat -c %s "$YD") B · $((YAS / 60)) dk önce"
(( YAS < 3 * 3600 )) || dur "yedek 3 saatten eski; yeni yedek alın"
KOD_ONCE="$(cat <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import depo
d = depo.Depo()
with d.baglan() as c:
    a = c.execute("SELECT count(*) AS n FROM isler WHERE durum IN ('sirada', 'isleniyor')").fetchone()["n"]
    r = c.execute("SELECT count(*) AS n FROM revizyonlar").fetchone()["n"]
    g = c.execute("SELECT count(*) AS n FROM giden").fetchone()["n"]
print(f"eksik_goc={d.eksik_goc()} acik_is={a} revizyonlar={r} giden={g}")
PY
)"
ONCE="$($OLARAK "$PY" -c "$KOD_ONCE" "$APP" 2>&1 | tail -1)"
echo "   Postgres (önce): $ONCE"
[[ "$ONCE" =~ acik_is=0\  ]] || dur "Postgres'te açık iş var ya da bağlanılamadı; bitmesini bekleyin"
[[ "$ONCE" =~ ^eksik_goc=\[3\]\  ]] || dur "beklenen eksik göç [3] değil (uygulanmış ya da paket farklı)"
if [ "${PM_TEST:-}" = "1" ]; then echo "-- PM_TEST=1: göç UYGULANMADI (kuru koşum)"; echo "== bitti"; return 0; fi
echo "-- göç (kalici.py goc)"
OUT="$($OLARAK "$PY" "$APP/kalici.py" goc 2>&1)"; RC=$?; echo "$OUT" | tail -3 | sed 's/^/   /'
KOD_SONRA="$(cat <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import depo
d = depo.Depo()
with d.baglan() as c:
    t = sorted(r["table_name"] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('secenek_setleri','adaylar')"))
    e = c.execute("SELECT count(*) AS n FROM information_schema.columns WHERE table_name='revizyonlar' AND column_name='ekler'").fetchone()["n"]
    k = (c.execute("SELECT pg_get_constraintdef(oid) AS d FROM pg_constraint WHERE conname='giden_kind_check'").fetchone() or {}).get("d") or "-"
    r = c.execute("SELECT count(*) AS n FROM revizyonlar").fetchone()["n"]
    g = c.execute("SELECT count(*) AS n FROM giden").fetchone()["n"]
print(f"eksik_goc={d.eksik_goc()} tablolar={t} revizyonlar.ekler={e} giden_kind_image={'image' in k} giden_kind_interactive={'interactive' in k} revizyonlar={r} giden={g}")
PY
)"
SONRA="$($OLARAK "$PY" -c "$KOD_SONRA" "$APP" 2>&1 | tail -1)"
echo "   Postgres (sonra): $SONRA"
if [ "$RC" = "0" ] && [[ "$SONRA" =~ ^eksik_goc=\[\]\ tablolar=\[\'adaylar\',\ \'secenek_setleri\'\]\ revizyonlar.ekler=1\ giden_kind_image=True\ giden_kind_interactive=True ]]; then
  echo "-- SONUÇ: göç 003 uygulandı. Ajan bir sonraki turda (en çok ~5 dk) 'kalıcı mod bekliyor' uyarısını bırakır ve iş almaya döner."
else
  echo "-- SONUÇ: göç TAMAMLANMADI (çıkış $RC). Ajan iş almaz; günlük ve yukarıdaki satırlar incelenmeli. Yedek dokunulmadan durur."
fi
echo "== bitti"
}
ana "$@" < /dev/null
