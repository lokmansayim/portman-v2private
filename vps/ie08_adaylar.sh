#!/usr/bin/env bash
# PORTMAN · İE-08 Adım 8 · yedi çelik adayın kabul kaydı (K-A10; root). Kabul eden yedi modeli kabul paketiyle gördükten sonra, yalnız
# kabul ettiği kodlar Postgres `adaylar` tablosuna 'gecerli' + kabul kaydı {kim, tarih, not, karar} ile yazılır (sütun adı
# muhendis_kabulu kalır); kabul edilmeyen aday yazılmaz, bayiye sunulmaz. Geliştirme döneminde kabul eden Lokman'dır (D-11; 13 Ekim
# 2026): 2. argüman boşsa "Lokman". Bayi onayından sonraki teknik kontrol (8b mühendis adımı) ayrıdır, aynen kalır. Ad çıktıya girmez
# (yalnız ilk harf). Canlı değişikliktir: Lokman'ın ayrı onayıyla, sürüm güncellendikten sonra, canlı A2 denemesinden önce koşar.
#   ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/ie08_adaylar.sh "Ç8801,Ç8801K,Ç8801L,Ç8201,KT01,KT02,KT03" "Lokman" 2026-10-13 "kabul notu" "2026-10-13"' > ie08_kabul.txt 2>&1
#   Sunucudaki sürüm kopyası koşulur; betik stdin'le (`bash -s < betik`, `git show … | ssh … 'bash -s'`) GÖNDERİLMEZ: 13 Ekim
#   17:40 UTC'de yazma adımında takıldı (BK-08 madde 5). `-n` ve `timeout` takılmayı önler; Python çağrısının stdin'i de /dev/null.
#   (tırnaklar uzak kabuğun komut dizesinin İÇİNDE olmalı: ssh argümanları boşlukla birleştirir, iki sözcüklü not bölünür.)
#   ... "--kuru" ile başlayan ilk argüman: yazmadan ne yazılacağını söyler (önce kuru koşu, sonra kayıt).
# Sınama: PM_KOK, PM_ETC, PM_PYTHON (venv yerine), PM_PG_DSN (env dosyası yerine).
set -uo pipefail
KURU=""
if [ "${1:-}" = "--kuru" ]; then KURU="--kuru"; shift; fi
KODLAR="${1:-}"; KIM="${2:-Lokman}"; TARIH="${3:-$(date +%Y-%m-%d)}"; NOT="${4:-}"; PAKET="${5:-}"
dur() { echo "DUR: $*" >&2; exit 1; }
[[ "$TARIH" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || dur "3. argüman tarih değil (YYYY-AA-GG); argümanda boşluk varsa tırnaklar uzak komut dizesinin içinde olmalı (yukarıdaki örnek)"
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"
[ -n "$KODLAR" ] || dur "kabul edilen kod listesi boş (örn. Ç8801,Ç8801K,Ç8801L)"
[ -n "$KIM" ] || dur "kabul edenin adı boş"
GUNCEL="$KOK/guncel"; [ -d "$GUNCEL/araclar" ] || GUNCEL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
[ -f "$GUNCEL/araclar/aday_kabul.py" ] || dur "araclar/aday_kabul.py yok: sürüm İE-08 PR-2a'dan eski mi? ($GUNCEL)"
[ -f "$GUNCEL/beyin/veri/adaylar.json" ] || dur "beyin/veri/adaylar.json sürümde yok"
PY="${PM_PYTHON:-$GUNCEL/venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
if [ -n "${PM_PG_DSN:-}" ]; then DSN="$PM_PG_DSN"
elif [ -f "$ETC/agent.env" ]; then DSN="$(grep -E '^PORTMAN_PG_DSN=' "$ETC/agent.env" | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//')"
else DSN="dbname=portman"; fi
[ -n "$DSN" ] || DSN="dbname=portman"
echo "== Portman aday kabul kaydı · $(date '+%Y-%m-%d %H:%M:%S %Z') · sürüm $(cat "$GUNCEL/SURUM" 2>/dev/null || echo '?')"
echo "   kodlar: $KODLAR · tarih: $TARIH · kabul eden: ${KIM:0:1}… (ad çıktıya girmez; D-11)"
cd /tmp
# Ajanla aynı kimlik ve DSN (systemd: PORTMAN_PG_DSN=dbname=portman, kullanıcı portman; guncelle.sh de göçleri böyle koşar)
if [ -n "${PM_OLARAK+x}" ]; then read -r -a OLARAK <<< "$PM_OLARAK"; elif [ "$(id -u)" = "0" ] && id portman >/dev/null 2>&1; then OLARAK=(sudo -u portman); else OLARAK=(); fi
"${OLARAK[@]}" env PORTMAN_PG_DSN="$DSN" HOME="${HOME:-/tmp}" "$PY" "$GUNCEL/araclar/aday_kabul.py" $KURU --kodlar "$KODLAR" --kim "$KIM" --tarih "$TARIH" --not "$NOT" --paket "$PAKET" < /dev/null
RC=$?
[ "$RC" = "0" ] || dur "kabul kaydı yazılamadı (çıkış $RC)"
if [ -n "$KURU" ]; then
    echo "   KURU: hiçbir şey yazılmadı; kaydı yazmak için aynı komutu --kuru olmadan koşun."
else
    echo "   tamam. Canlı A2 denemesi artık bu adayları sunar (bayi 'Ç8801' ya da '88 m² 2+1 çelik' yazınca)."
fi
