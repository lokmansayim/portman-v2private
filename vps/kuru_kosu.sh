#!/usr/bin/env bash
# PORTMAN · kuru koşu (İE-06 Kapı 7; İE-07 P1 düzeltmesi; BK-07 S3; root). App secret ile imzalanmış SAHTE bir metni
# 127.0.0.1'deki webhook'a verir; Meta'ya dokunmaz. Gönderen Patron DEĞİL, panelden girilen rol='test' sahte kartıdır (kod TEST;
# gerçek numara değil): Patron konuşmasına iz kalmaz, Patron'un 24 saat penceresi kirlenmez, İş Emri numarası test kartının kendi
# projesinde kalır (10 Ekim'de sahte Patron mesajı r01 üretmiş, ilk gerçek mesaj r02 olmuştu). BK-07: dry_run GEREKMEZ — gönderici
# (kanal/gonderici.py) test kartından doğan ya da ona giden her satırı dry_run ayarından bağımsız 'gonderilmedi: test_karti' ile
# tutar (Patron bildirimi ve şablon dahil); canlıda dry_run false iken de güvenle koşar. Kanal kapalıysa (enabled false) yalnız bu
# koşu için açar (enabled_at = şimdi) ve sonunda kapatır. Ajan işi işler (1 LLM çağrısı; ücretli, Lokman'ın ayrı onayı); satırlar
# panelde test kartının konuşmasında görünür. Sonra sayımları yazar (rapor sorgusunda sütunlar g. önekli: giden ve isler'de aynı
# adlı 'durum' var). Çıktıda numara maskeli, sır yok.
#   ssh portman-vps 'bash /opt/portman/guncel/vps/kuru_kosu.sh' > ie07_kuru.txt 2>&1
# Sınama: PM_ETC, PM_DATA, PM_KOK, PM_PSQL, PM_WEBHOOK_URL, PM_BEKLE, PM_METIN, PM_TEST (psql yerine numara).
set -uo pipefail
ETC="${PM_ETC:-/etc/portman}"; KOK="${PM_KOK:-/opt/portman}"; DATA="${PM_DATA:-$KOK/data}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"; URL="${PM_WEBHOOK_URL:-http://127.0.0.1:8081/webhook}"
BEKLE="${PM_BEKLE:-120}"; METIN="${PM_METIN:-P6001 aynalı (kuru koşu)}"
AYARLAR="$KOK/guncel/kanal/ayarlar.py"; [ -f "$AYARLAR" ] || AYARLAR="$(dirname "$0")/../kanal/ayarlar.py"
dur() { echo "DUR: $*" >&2; exit 1; }
cd /tmp
echo "== Portman kuru koşu · $(date '+%Y-%m-%d %H:%M:%S %Z')"
[ -s "$ETC/whatsapp.env" ] || dur "whatsapp.env yok ya da boş (Kapı 5: sir_koy.py wa_secret, wa_pnid)"
DRY="$(python3 -c 'import json,sys; print("1" if json.load(open(sys.argv[1])).get("dry_run") is True else "0")' "$DATA/settings.json" 2>/dev/null || echo 0)"
ACIK="$(python3 -c 'import json,sys; print("1" if json.load(open(sys.argv[1])).get("enabled") is True else "0")' "$DATA/settings.json" 2>/dev/null || echo 0)"
TEST="${PM_TEST:-$($PSQL -c "SELECT numara FROM bayiler WHERE rol = 'test' AND aktif ORDER BY olusturuldu LIMIT 1" 2>/dev/null | head -1)}"
[[ "$TEST" =~ ^[0-9]{8,15}$ ]] || dur "test göndericisi yok: panelden rol=test, kod TEST, gerçek olmayan bir numarayla kart girin (İE-07; Patron'un numarası kullanılmaz)"
echo "   test kartı …${TEST: -2} · satırlar her zaman tutulur (test_karti; dry_run $([ "$DRY" = 1 ] && echo açık || echo kapalı), gerekmez) · kanal: $([ "$ACIK" = 1 ] && echo açık || echo 'kapalı (bu koşu için açılacak)')"
GERI=""
if [ "$ACIK" != "1" ]; then
  python3 "$AYARLAR" --veri "$DATA" yaz enabled true >/dev/null || dur "ayar yazılamadı"; GERI=1
  trap 'python3 "$AYARLAR" --veri "$DATA" yaz enabled false >/dev/null && echo "   kanal yeniden kapatıldı (enabled false)"' EXIT
fi
MID="wamid.KURU$(date +%Y%m%d%H%M%S)"
SONUC="$(PM_ETC="$ETC" PM_TEST="$TEST" PM_MID="$MID" PM_METIN="$METIN" PM_URL="$URL" python3 - <<'PY'
import hashlib, hmac, json, os, time, urllib.error, urllib.request
env = {}
with open(os.path.join(os.environ["PM_ETC"], "whatsapp.env"), encoding="utf-8") as f:
    for s in f:
        if "=" in s and not s.startswith("#"):
            a, v = s.rstrip("\n").split("=", 1); env[a] = v
secret, pnid = env.get("WA_APP_SECRET", ""), env.get("WA_PHONE_NUMBER_ID", "")
if not secret or not pnid:
    raise SystemExit("DUR: whatsapp.env'de WA_APP_SECRET ya da WA_PHONE_NUMBER_ID yok")
test = os.environ["PM_TEST"]; ts = int(time.time())
yuk = {"object": "whatsapp_business_account", "entry": [{"id": "KURU", "changes": [{"field": "messages", "value": {
    "messaging_product": "whatsapp", "metadata": {"display_phone_number": "0", "phone_number_id": pnid},
    "contacts": [{"wa_id": test, "profile": {"name": "Kuru Koşu"}}],
    "messages": [{"from": test, "id": os.environ["PM_MID"], "timestamp": str(ts), "type": "text", "text": {"body": os.environ["PM_METIN"]}}]}}]}]}
govde = json.dumps(yuk).encode("utf-8")
imza = "sha256=" + hmac.new(secret.encode("utf-8"), govde, hashlib.sha256).hexdigest()
req = urllib.request.Request(os.environ["PM_URL"], data=govde, method="POST", headers={"Content-Type": "application/json", "X-Hub-Signature-256": imza})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"HTTP {r.status} {r.read().decode('utf-8', 'replace')[:300]}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
except OSError as e:
    print(f"ulaşılamadı: {type(e).__name__}")
PY
)" || dur "$SONUC"
echo "   webhook: $SONUC"
echo "$SONUC" | grep -q '"sahiplenildi": 1' || dur "mesaj sahiplenilmedi (cevap yukarıda: imza, phone_number_id ya da test kartı pasif/yok; rol=test patron modunda da sahiplenilir)"
echo "-- bekleniyor (en çok $BEKLE sn): ajan işi işler, gönderici test kartının satırlarını tutar"
for ((i = 0; i < BEKLE; i++)); do
  D="$($PSQL -c "SELECT durum FROM isler WHERE mesaj_id = '$MID'" 2>/dev/null | head -1)"
  if [ "$D" = "bitti" ] || [ "$D" = "basarisiz" ]; then break; fi
  sleep 2
done
# Gönderici (3 sn tur) bekleyen satırları 'gonderilmedi: test_karti' yapmadan kanal kapatılmasın (satır bekliyor'da kalmasın).
for ((i = 0; i < 30; i++)); do
  B="$($PSQL -c "SELECT count(*) FROM giden g JOIN isler i ON i.id = g.is_id WHERE i.mesaj_id = '$MID' AND g.durum = 'bekliyor'" 2>/dev/null | head -1)"
  [ "${B:-0}" = "0" ] && break
  sleep 1
done
echo "   mesajlar: $($PSQL -c "SELECT count(*) FROM mesajlar WHERE id = '$MID'" 2>/dev/null) · iş: ${D:-yok} · giden: $($PSQL -c "SELECT string_agg(g.kind || ':' || g.durum, ', ' ORDER BY g.sira) FROM giden g JOIN isler i ON i.id = g.is_id WHERE i.mesaj_id = '$MID'" 2>/dev/null)"
echo "   panel: https://$(cat "$ETC/alan" 2>/dev/null || echo '<alan>')/panel/konusma/…${TEST: -2} (test kartı; Patron konuşmasında satır yok)"
echo "== bitti"
