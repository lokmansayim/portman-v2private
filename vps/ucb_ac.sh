#!/usr/bin/env bash
# PORTMAN · İE-21 · bayiye 3D sayfasını aç / kapat (root). Canlı değişikliktir: Lokman'ın onayıyla, İE-21'li sürüm kurulduktan sonra
# (guncelle.sh nginx'in /3d/ yolunu ve yayın dizinini nginx_uygula.sh ile zaten açar; bu betik bağlantının bayiye gitmesini açar).
#   ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/ucb_ac.sh' > ie21_ucb_ac.txt 2>&1
#   ssh -n portman-vps 'timeout 60 bash /opt/portman/guncel/vps/ucb_ac.sh kapat' > ie21_ucb_kapat.txt 2>&1
# Açarken sırayla denetler; biri düşerse DUR ve ayar değişmez:
#   1. yayın dizini data/yayin/3d (portman, 755) ve data'dan geçiş (o+x); 2. nginx'te 443 bloğu ve /3d/ konumu;
#   3. depodaki P6001 İş Emri'nden ajanın koduyla örnek sayfa üretilir ve yayımlanır (portman kullanıcısıyla; izinler ajanınkiyle aynı);
#   4. sunucunun kendisinden https://<alan>/3d/<anahtar>/ = 200, CSP başlığı var, gelen baytlar yayımlananla aynı; anahtarsız yol,
#      bilinmeyen anahtar ve başka dosya adı 404, POST 403; 5. ayar ucb_taban_url = https://<alan>/3d (servisler her turda okur).
# Sonda örnek adres yazılır: Lokman telefonda açar (sayfa P6001 referans planıdır; kişi ve bayi verisi yok). Bundan sonra her planda bayiye
# "3D'yi aç" düğmeli bir mesaj daha gider. LLM çağrısı yok, WhatsApp mesajı yok. Kapatırken ayar null olur; yayımlanmış sayfalar durur
# (silmek ayrı onay ister).
# Sınama: PM_KOK, PM_ETC, PM_NGINX_DIR, PM_PYTHON, PM_OLARAK, PM_CURL (ör. "curl --cacert sınama.pem"), PM_TEST=1 (HTTP denetimi atlanır).
set -euo pipefail
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; NGINX_DIR="${PM_NGINX_DIR:-/etc/nginx}"; TEST="${PM_TEST:-}"
DATA="$KOK/data"; YAYIN="$DATA/yayin/3d"
GUNCEL="$KOK/guncel"; [ -f "$GUNCEL/kanal/ucb_yayin.py" ] || GUNCEL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
dur() { echo "DUR: $*" >&2; echo "ayar değişmedi: ucb_taban_url = $(ayar_oku)"; exit 1; }
PY="${PM_PYTHON:-$GUNCEL/venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
ayar_oku() { "$PY" -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])).get("ucb_taban_url")))' "$DATA/settings.json" 2>/dev/null < /dev/null || echo "?"; }
[ -f "$GUNCEL/kanal/ucb_yayin.py" ] || dur "kanal/ucb_yayin.py yok: kurulu sürüm İE-21'den eski ($GUNCEL)"
ALAN="$(cat "$ETC/alan" 2>/dev/null || true)"
[[ "$ALAN" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || dur "alan adı okunamadı ($ETC/alan)"
TABAN="https://$ALAN/3d"
echo "== Portman 3D sayfası · $(date '+%Y-%m-%d %H:%M:%S %Z') · sürüm $(cat "$GUNCEL/SURUM" 2>/dev/null || echo '?') · alan $ALAN"

if [ "${1:-ac}" = "kapat" ]; then
  "$PY" "$GUNCEL/kanal/ayarlar.py" --veri "$DATA" yaz ucb_taban_url null > /dev/null < /dev/null
  echo "   kapatıldı: ucb_taban_url = $(ayar_oku). Yeni planlarda 3D düğmesi gitmez; yayımlanmış sayfalar açılmaya devam eder."
  exit 0
fi
[ "${1:-ac}" = "ac" ] || { echo "kullanım: ucb_ac.sh [ac|kapat]" >&2; exit 2; }

echo "-- [1/5] yayın dizini"
[ -d "$YAYIN" ] || dur "$YAYIN yok (sürüm kurulumunda nginx_uygula.sh açar: bash $GUNCEL/vps/nginx_uygula.sh $GUNCEL)"
[ "$(stat -c %a "$YAYIN")" = "755" ] || dur "$YAYIN izni $(stat -c %a "$YAYIN"), 755 olmalı (nginx_uygula.sh düzeltir)"
[ $(( 0$(stat -c %a "$DATA") & 1 )) = 1 ] || dur "$DATA'dan geçilemiyor (izin $(stat -c %a "$DATA"); nginx_uygula.sh o+x verir)"
echo "   $YAYIN 755 · data $(stat -c %a "$DATA") · sahibi $(stat -c %U "$YAYIN")"

echo "-- [2/5] nginx"
CONF="$NGINX_DIR/sites-available/portman.conf"
grep -q 'listen 443' "$CONF" 2>/dev/null || dur "$CONF'ta 443 bloğu yok (sertifika?)"
grep -qF 'location ~ "^/3d/' "$CONF" || dur "$CONF'ta /3d/ konumu yok (nginx_uygula.sh uygulanmamış)"
echo "   $CONF: 443 ve /3d/ konumu var"

echo "-- [3/5] örnek sayfa (depodaki P6001; ajanın kodu)"
if [ -n "${PM_OLARAK+x}" ]; then read -r -a OLARAK <<< "$PM_OLARAK"; elif [ "$(id -u)" = "0" ] && id portman >/dev/null 2>&1; then OLARAK=(sudo -u portman); else OLARAK=(); fi
cd /tmp
ORNEK="$("${OLARAK[@]}" env HOME=/tmp MPLCONFIGDIR=/tmp "$PY" "$GUNCEL/kanal/ucb_yayin.py" ornek --veri "$DATA" --taban "$TABAN" < /dev/null | tail -1)" || dur "örnek sayfa üretilemedi"
alan_al() { "$PY" -c 'import json,sys; print(json.loads(sys.argv[1]).get(sys.argv[2]) or "")' "$ORNEK" "$1" < /dev/null; }
URL="$(alan_al url)"; ANAHTAR="$(alan_al anahtar)"
[ -n "$URL" ] || dur "örnek yayımlanamadı: $(alan_al yayin_hata)"
SAYFA="$YAYIN/$ANAHTAR/index.html"
[ "$(stat -c %a "$SAYFA")" = "644" ] || dur "örnek sayfanın izni $(stat -c %a "$SAYFA"), 644 olmalı"
echo "   yayımlandı: $(du -k "$SAYFA" | cut -f1) KB · sayfa 644"

echo "-- [4/5] sunucunun kendisinden HTTPS"
if [ -n "$TEST" ]; then
  echo "   PM_TEST: HTTP denetimi atlandı"
else
  read -r -a CURL <<< "${PM_CURL:-curl}"
  GEC="$(mktemp -d /tmp/portman_ucb_dogrula_XXXXXX)"
  kod() { local k; k="$("${CURL[@]}" -sS --noproxy "*" --max-time 20 --resolve "$ALAN:443:127.0.0.1" -o "${2:-/dev/null}" -D "${3:-/dev/null}" -w '%{http_code}' "${@:4}" "https://$ALAN$1" < /dev/null)" || true; echo "${k:-000}"; }
  K="$(kod "/3d/$ANAHTAR/" "$GEC/sayfa" "$GEC/baslik")"
  [ "$K" = "200" ] || dur "örnek adres $K döndü, 200 bekleniyordu"
  cmp -s "$GEC/sayfa" "$SAYFA" || dur "gelen sayfa yayımlanan dosyayla aynı değil"
  grep -qi "^content-security-policy: default-src 'none'" "$GEC/baslik" || dur "CSP başlığı yok"
  grep -qi '^content-type: text/html' "$GEC/baslik" || dur "içerik türü text/html değil"
  K2="$(kod "/3d/")"; K3="$(kod "/3d/AAAAAAAAAAAAAAAAAAAAAA/")"; K4="$(kod "/3d/$ANAHTAR/ornek.ifc")"; K5="$(kod "/3d/$ANAHTAR/" "" "" -X POST)"
  [ "$K2" = "404" ] && [ "$K3" = "404" ] && [ "$K4" = "404" ] && [ "$K5" = "403" ] \
    || dur "beklenmeyen yanıt: anahtarsız $K2, bilinmeyen anahtar $K3, başka dosya $K4 (404 bekleniyordu), POST $K5 (403 bekleniyordu)"
  echo "   örnek 200, baytlar aynı, CSP var · anahtarsız $K2 · bilinmeyen anahtar $K3 · başka dosya $K4 · POST $K5"
fi

echo "-- [5/5] ayar"
"$PY" "$GUNCEL/kanal/ayarlar.py" --veri "$DATA" yaz ucb_taban_url "\"$TABAN\"" > /dev/null < /dev/null
[ "$(ayar_oku)" = "\"$TABAN\"" ] || dur "ayar yazılamadı"
echo "   ucb_taban_url = $(ayar_oku) (servisler her turda okur; yeniden başlatma gerekmez)"
echo "== bitti. Telefonda açın: $URL"
echo "   Bundan sonra her planda bayiye \"3D'yi aç\" düğmeli bir mesaj daha gider. Kapatmak: bash $GUNCEL/vps/ucb_ac.sh kapat"
