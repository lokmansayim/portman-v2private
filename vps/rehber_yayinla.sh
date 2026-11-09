#!/usr/bin/env bash
# PORTMAN · İE-34 · bayiye montaj rehberini yayımla (root). Canlı değişikliktir: her yayın Lokman'ın kendi komutudur. Rehber `main`'deki
# koddan bulutta üretilir (İE-18, `python -m araclar.paket --is-emri … --render`; D-28) ve Lokman'ın Mac'inden sunucuya konur:
#   scp TK-01_montaj_rehberi.html portman-vps:/root/rehber_gelen.html
#   ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/rehber_yayinla.sh /root/rehber_gelen.html' > rehber_yayin.txt 2>&1
# Sırayla denetler; biri düşerse DUR:
#   1. yayın dizini data/yayin/rehber (755) ve data'dan geçiş (o+x); 2. nginx'te 443 bloğu ve /rehber/ konumu;
#   3. dosyanın denetimi ve yayını, portman kullanıcısıyla (kanal/rehber_yayin.py: rehber imleri, izinli dış adresler, telefon numarası yok;
#      sayfa 644). Denetim düşerse hiçbir şey yayımlanmaz;
#   4. sunucunun kendisinden https://<alan>/rehber/<anahtar>/ = 200, gelen baytlar aynı, CSP (yalnız jsDelivr ve Google Fonts), text/html;
#      anahtarsız yol, bilinmeyen anahtar ve başka dosya 404, POST 405. Bu adım düşerse sayfa dizinde kalır (silmek ayrı onay) ama adres verilmez.
# Sonda adres yazılır: Lokman önce kendi telefonunda açar, sonra panelden bayiye metin olarak yollar (1 ücretli servis mesajı). Betik LLM'e ve
# WhatsApp'a bağlanmaz, ayar değiştirmez, hiçbir şey silmez; gelen dosya yerinde kalır.
# Sınama: PM_KOK, PM_ETC, PM_NGINX_DIR, PM_PYTHON, PM_OLARAK, PM_CURL (ör. "curl --cacert sınama.pem"), PM_TEST=1 (HTTP denetimi atlanır).
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; NGINX_DIR="${PM_NGINX_DIR:-/etc/nginx}"; TEST="${PM_TEST:-}"
DATA="$KOK/data"; YAYIN="$DATA/yayin/rehber"
GUNCEL="$KOK/guncel"; [ -f "$GUNCEL/kanal/rehber_yayin.py" ] || GUNCEL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
dur() { echo "DUR: $*" >&2; echo "yayımlanmadı."; exit 1; }
PY="${PM_PYTHON:-$GUNCEL/venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
[ -f "$GUNCEL/kanal/rehber_yayin.py" ] || dur "kanal/rehber_yayin.py yok: kurulu sürüm İE-34'ten eski ($GUNCEL)"
DOSYA="${1:-}"
[ -n "$DOSYA" ] || { echo "kullanım: rehber_yayinla.sh <rehber.html> (ör. /root/rehber_gelen.html)" >&2; exit 2; }
[ -f "$DOSYA" ] || dur "dosya yok: $DOSYA (önce Mac'ten: scp <rehber>.html portman-vps:$DOSYA)"
ALAN="$(cat "$ETC/alan" 2>/dev/null || true)"
[[ "$ALAN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || dur "alan adı okunamadı ($ETC/alan)"
TABAN="https://$ALAN/rehber"
echo "== Portman montaj rehberi yayını · $(date '+%Y-%m-%d %H:%M:%S %Z') · sürüm $(cat "$GUNCEL/SURUM" 2>/dev/null || echo '?') · alan $ALAN"
echo "   dosya $DOSYA · $(stat -c %s "$DOSYA") bayt · sha256 $(sha256sum "$DOSYA" | cut -c1-16)…"

echo "-- [1/4] yayın dizini"
[ -d "$YAYIN" ] || dur "$YAYIN yok (sürüm kurulumunda nginx_uygula.sh açar: bash $GUNCEL/vps/nginx_uygula.sh $GUNCEL)"
[ "$(stat -c %a "$YAYIN")" = "755" ] || dur "$YAYIN izni $(stat -c %a "$YAYIN"), 755 olmalı (nginx_uygula.sh düzeltir)"
[ $(( 0$(stat -c %a "$DATA") & 1 )) = 1 ] || dur "$DATA'dan geçilemiyor (izin $(stat -c %a "$DATA"); nginx_uygula.sh o+x verir)"
echo "   $YAYIN 755 · data $(stat -c %a "$DATA") · sahibi $(stat -c %U "$YAYIN")"

echo "-- [2/4] nginx"
CONF="$NGINX_DIR/sites-available/portman.conf"
grep -q 'listen 443' "$CONF" 2>/dev/null || dur "$CONF'ta 443 bloğu yok (sertifika?)"
grep -qF 'location ~ "^/rehber/' "$CONF" || dur "$CONF'ta /rehber/ konumu yok (nginx_uygula.sh uygulanmamış)"
echo "   $CONF: 443 ve /rehber/ konumu var"

echo "-- [3/4] denetim ve yayın (portman kullanıcısıyla)"
if [ -n "${PM_OLARAK+x}" ]; then read -r -a OLARAK <<< "$PM_OLARAK"; elif [ "$(id -u)" = "0" ] && id portman >/dev/null 2>&1; then OLARAK=(sudo -u portman); else OLARAK=(); fi
cd /tmp
SONUC="$("${OLARAK[@]}" env HOME=/tmp "$PY" "$GUNCEL/kanal/rehber_yayin.py" --veri "$DATA" --taban "$TABAN" - < "$DOSYA" | tail -1)" || dur "yayın betiği çalışmadı"
alan_al() { "$PY" -c 'import json,sys; v=json.loads(sys.argv[1]).get(sys.argv[2]); print("; ".join(v) if isinstance(v, list) else (v or ""))' "$SONUC" "$1" < /dev/null; }
URL="$(alan_al url)"; ANAHTAR="$(alan_al anahtar)"
[ -z "$(alan_al sorunlar)" ] || dur "dosya rehber denetiminden geçmedi: $(alan_al sorunlar)"
[ -n "$URL" ] || dur "yayımlanamadı: $(alan_al yayin_hata)"
SAYFA="$YAYIN/$ANAHTAR/index.html"
cmp -s "$SAYFA" "$DOSYA" || dur "yayımlanan sayfa gelen dosyayla aynı değil ($SAYFA)"
[ "$(stat -c %a "$SAYFA")" = "644" ] || dur "sayfanın izni $(stat -c %a "$SAYFA"), 644 olmalı"
echo "   denetim tamam: $(alan_al baslik) · $(du -k "$SAYFA" | cut -f1) KB · sayfa 644 · baytlar gelen dosyayla aynı"

echo "-- [4/4] sunucunun kendisinden HTTPS"
if [ -n "$TEST" ]; then
  echo "   PM_TEST: HTTP denetimi atlandı"
else
  read -r -a CURL <<< "${PM_CURL:-curl}"
  GEC="$(mktemp -d /tmp/portman_rehber_dogrula_XXXXXX)"
  kod() { local k; k="$("${CURL[@]}" -sS --noproxy "*" --max-time 30 --resolve "$ALAN:443:127.0.0.1" -o "${2:-/dev/null}" -D "${3:-/dev/null}" -w '%{http_code}' "${@:4}" "https://$ALAN$1" < /dev/null)" || true; echo "${k:-000}"; }
  K="$(kod "/rehber/$ANAHTAR/" "$GEC/sayfa" "$GEC/baslik")"
  [ "$K" = "200" ] || dur "adres $K döndü, 200 bekleniyordu (sayfa dizinde kaldı: $SAYFA)"
  cmp -s "$GEC/sayfa" "$SAYFA" || dur "gelen sayfa yayımlanan dosyayla aynı değil"
  grep -qi "^content-security-policy: default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net;" "$GEC/baslik" || dur "rehberin CSP başlığı yok"
  grep -qi '^content-type: text/html' "$GEC/baslik" || dur "içerik türü text/html değil"
  K2="$(kod "/rehber/")"; K3="$(kod "/rehber/AAAAAAAAAAAAAAAAAAAAAA/")"; K4="$(kod "/rehber/$ANAHTAR/rehber.html")"; K5="$(kod "/rehber/$ANAHTAR/" "" "" -X POST)"
  [ "$K2" = "404" ] && [ "$K3" = "404" ] && [ "$K4" = "404" ] && [ "$K5" = "405" ] \
    || dur "beklenmeyen yanıt: anahtarsız $K2, bilinmeyen anahtar $K3, başka dosya $K4 (404 bekleniyordu), POST $K5 (405 bekleniyordu)"
  echo "   rehber 200, baytlar aynı, CSP var · anahtarsız $K2 · bilinmeyen anahtar $K3 · başka dosya $K4 · POST $K5"
fi
echo "== yayımlandı. Önce kendi telefonunuzda açın: $URL"
echo "   Sonra panelden bayiye metin olarak yollayın (1 ücretli servis mesajı)."
