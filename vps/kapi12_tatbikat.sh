#!/usr/bin/env bash
# PORTMAN · Kapı 12: sürüm geri dönüş tatbikatı (İE-06 Kapı 12; BK-07 S5; root; TEK KOMUT). Sıra: salt okunur ön kontrol →
# nabız zamanlayıcısı durur (tatbikat sırasında Patron'a ücretli uyarı gitmesin) → geri_don.sh (güncel → önceki, sağlık beklenir) →
# guncelle.sh <etiket> ("sürüm zaten kurulu" yolu; venv yeniden kurulmaz; sağlık beklenir; nginx adımı) → nabız zamanlayıcısı
# yeniden başlar → durum.sh. Veritabanına, şemaya ve nginx'e dokunmaz (geri dönüşte önceki sürüm aynı şema ve nginx ile çalışır).
# DURUR (hiçbir şey değişmeden): etiket güncel sürümle aynı değilse; 'onceki' yoksa; açık iş ya da bekleyen giden satırı varsa
# (PM_ZORLA=1 ile geçilir; bekleyen şablon satırı önceki sürümde de tanınır ama tatbikat temiz tabloyla yapılır); sağlık 200 değilse.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/kapi12_tatbikat.sh v2026.10.XX' > bk07_3_kapi12.txt 2>&1
# Sınama: PM_KOK, PM_SYSTEMCTL, PM_PSQL, PM_SAGLIK_URL, PM_SAGLIK_BEKLE, PM_TEST=1, PM_ZORLA=1 ve guncelle.sh'nin PM_* değişkenleri.
set -euo pipefail
ETIKET="${1:-}"
KOK="${PM_KOK:-/opt/portman}"; SYSTEMCTL="${PM_SYSTEMCTL:-systemctl}"; TEST="${PM_TEST:-}"; ZORLA="${PM_ZORLA:-}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"; SAGLIK_URL="${PM_SAGLIK_URL:-http://127.0.0.1:8081/saglik}"
BURASI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"   # -P: fiziksel yol; 'guncel' bağı geri dönüşte değişir, bu sürümün betikleri kullanılmalı
dur() { echo "DUR: $*" >&2; echo "== bitti (durdu)"; exit 1; }
z() { date '+%H:%M:%S'; }
echo "== Kapı 12 · sürüm geri dönüş tatbikatı · $(date '+%Y-%m-%d %H:%M:%S %Z') · etiket: ${ETIKET:-?}"
[[ "$ETIKET" =~ ^v20[0-9]{2}\.[0-9]{2}\.[0-9]{2}[a-z]?$ ]] || dur "etiket biçimi vYYYY.AA.GG[a-z] olmalı; verilen: '${ETIKET}'"
if [ -z "$TEST" ]; then [ "$(id -u)" = "0" ] || dur "root olarak çalıştırılmalı"; fi
cd /tmp
[ -L "$KOK/guncel" ] || dur "güncel sürüm bağlantısı yok ($KOK/guncel)"
[ -L "$KOK/onceki" ] || dur "önceki sürüm yok ($KOK/onceki); dönülecek yer yok"
GUNCEL_SURUM="$(cat "$KOK/guncel/SURUM" 2>/dev/null || echo '?')"; ONCEKI_SURUM="$(cat "$KOK/onceki/SURUM" 2>/dev/null || echo '?')"
[ "$GUNCEL_SURUM" = "$ETIKET" ] || dur "güncel sürüm $GUNCEL_SURUM, verilen etiket $ETIKET; tatbikat yalnız etkin sürümden yapılır"
[ "$ONCEKI_SURUM" != "?" ] || dur "önceki sürüm dizini bozuk ($KOK/onceki)"

echo "-- [0/2] ön kontrol (salt okunur) · $(z)"
ACIK_IS="$($PSQL -c "SELECT count(*) FROM isler WHERE durum IN ('sirada','isleniyor')" 2>/dev/null | head -1 || echo '?')"
BEKLEYEN="$($PSQL -c "SELECT count(*) FROM giden WHERE durum IN ('bekliyor', 'gonderiliyor')" 2>/dev/null | head -1 || echo '?')"   # gonderiliyor: Meta POST'u sürüyor
BEKLEYEN_SABLON="$($PSQL -c "SELECT count(*) FROM giden WHERE durum IN ('bekliyor', 'gonderiliyor') AND kind = 'template'" 2>/dev/null | head -1 || echo '?')"
KOD="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$SAGLIK_URL" 2>/dev/null || echo 000)"
echo "   ön kontrol: açık iş ${ACIK_IS} · bekleyen giden ${BEKLEYEN} (şablon ${BEKLEYEN_SABLON}) · sağlık HTTP $KOD · guncel $GUNCEL_SURUM · onceki $ONCEKI_SURUM"
if [ "$ACIK_IS" != "0" ] || [ "$BEKLEYEN" != "0" ] || [ "$KOD" != "200" ]; then
  [ -n "$ZORLA" ] || dur "ön kontrol geçmedi (açık iş ve bekleyen giden 0, sağlık 200 olmalı); bekleyip yeniden deneyin ya da PM_ZORLA=1"
  echo "   PM_ZORLA: ön kontrol uyarısına rağmen devam"
fi

$SYSTEMCTL stop portman-nabiz.timer >/dev/null 2>&1 || true
echo "   nabız zamanlayıcısı durduruldu (tatbikat boyunca Patron'a uyarı gitmez) · $(z)"
trap '$SYSTEMCTL start portman-nabiz.timer >/dev/null 2>&1 || true; echo "   nabız zamanlayıcısı başlatıldı · $(z)"' EXIT

echo "-- [1/2] geri: $GUNCEL_SURUM → $ONCEKI_SURUM · $(z)"
bash "$BURASI/geri_don.sh" 2>&1 | sed 's/^/   /' || dur "geri dönüşte sağlık gelmedi; servisler $ONCEKI_SURUM'de (çıktı yukarıda). İleri almak için: bash $BURASI/guncelle.sh $ETIKET"
echo "   önceki sürüm ayakta · $(z)"

echo "-- [2/2] ileri: $ONCEKI_SURUM → $ETIKET (guncelle.sh; sürüm zaten kurulu) · $(z)"
bash "$BURASI/guncelle.sh" "$ETIKET" 2>&1 | sed 's/^/   /' || dur "ileri alma düştü (çıktı yukarıda); guncelle.sh sağlık gelmezse kendiliğinden önceki sürüme döner"
echo "== bitti: $(cat "$KOK/guncel/SURUM") etkin · onceki $(cat "$KOK/onceki/SURUM" 2>/dev/null || echo '?') · $(date '+%Y-%m-%d %H:%M:%S %Z')"
