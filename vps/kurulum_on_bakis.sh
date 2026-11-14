#!/usr/bin/env bash
# PORTMAN · kurulum ön bakışı (D-71, Kurulum Panosu satır 119; SALT OKUNUR; root). Sürüm kurulumundan (guncelle.sh) hemen önce koşulur.
# Hiçbir şeyi değiştirmez; LLM ya da WhatsApp çağırmaz; sır, numara ve mesaj metni yazmaz. Gösterir:
#   1. sürümler (guncel, onceki) ve disk;
#   2. kurulacak etiket sunucudan görünüyor mu (dağıtım anahtarıyla salt okuma `git ls-remote`; guncelle.sh'in [1/7] adımının ön denemesi);
#   3. açık iş ve bekleyen giden (kapi12_tatbikat.sh'in ön kontrolü gibi; ikisi 0 değilse kurulum beklenir);
#   4. kurulumla mesaj doğurabilecek kayıtlar: BK-10 (göç 011, D-19) 24 saati geçmiş ve kararı bekleyen mühendis kontrolü kurulumdan
#      sonraki ilk mesai dakikasında 'zaman_asimi' olur ve Patron'a bir bildirim + pencere kapalıysa ücretli şablon gider; Patron'un fiyat
#      hatırlatması bekleyen kontrol (bugünkü sürümde de vardır, sayı bilgi için); onay bekleyen revizyon (bayi yeniden yazınca kapanır,
#      mesaj gitmez);
#   5. ayarlar: kanal açık mı, dry_run, mesaj katmanı, 3D adresi dolu mu, plan üretimi ve LLM-önce revizyon, yeni özellikler
#      (banka_germe, gorsel_okuma, talep_formu, bayi_kaydi, yarim_pano; ayarda yoksa kapalıdır, kanal/ayarlar.py VARSAYILAN);
#   6. son yedeğin yaşı (nabız dosyası) ve öz-test sonucu (yoksa ajan kurulumdan sonra öz-testi koşar: LLM anahtarı varsa 1 ücretli çağrı).
# Sunucuda kopyası yok (sürümle gelir); kopyası olmayan geçici betik gibi koşulur (AGENTS.md › Sunucu erişimi). Mac'te, commit'e sabit:
#   curl -fsSL https://raw.githubusercontent.com/lokmansayim/portman-v2private/<commit>/vps/kurulum_on_bakis.sh \
#     | ssh portman-vps 'timeout 120 bash -s -- v2026.11.08' > kurulum_on_bakis.txt 2>&1
# Sınama: PM_KOK, PM_ETC, PM_PSQL, PM_GIT_URL (yerel çıplak depo olabilir), PM_GIT_ATLA=1 (etiket denetimi atlanır), PM_TEST=1 (root
# denetimi atlanır), PM_SIMDI (saniye; yedek yaşı için), PM_EN_AZ_MB (boş disk sınırı, varsayılan 2048).
set -uo pipefail
# Gövde bir işlevde: `bash -s` ile stdin'den okunurken betiğin tamamı önce okunur, komutlar stdin olarak /dev/null alır
# (psql, git, ssh betiğin kalanını yutamaz).
ana() {
ETIKET="${1:-}"
KOK="${PM_KOK:-/opt/portman}"; ETC="${PM_ETC:-/etc/portman}"; DATA="$KOK/data"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"
GIT_URL="${PM_GIT_URL:-git@github.com:lokmansayim/portman-v2private.git}"
TEST="${PM_TEST:-}"; SIMDI="${PM_SIMDI:-$(date +%s)}"; EN_AZ_MB="${PM_EN_AZ_MB:-2048}"
cd /tmp
DUR=()
sor() { $PSQL -c "$1" 2>/dev/null | head -1; }
echo "== Portman kurulum ön bakışı · salt okunur · $(date '+%Y-%m-%d %H:%M:%S %Z') · kurulacak etiket: ${ETIKET:-?}"
if [ -z "$TEST" ] && [ "$(id -u)" != "0" ]; then echo "DUR: root olarak çalıştırılmalı"; exit 1; fi
[[ "$ETIKET" =~ ^v20[0-9]{2}\.[0-9]{2}\.[0-9]{2}[a-z]?$ ]] || DUR+=("etiket biçimi vYYYY.AA.GG[a-z] olmalı; verilen: '${ETIKET}'")

echo "-- [1/6] sürümler ve disk"
GUNCEL="$( [ -L "$KOK/guncel" ] && cat "$KOK/guncel/SURUM" 2>/dev/null || echo yok )"
ONCEKI="$( [ -L "$KOK/onceki" ] && cat "$KOK/onceki/SURUM" 2>/dev/null || echo yok )"
echo "   guncel: $GUNCEL · onceki: $ONCEKI · sürüm dizinleri: $(ls -1d "$KOK/surumler"/*/ 2>/dev/null | wc -l)"
[ "$GUNCEL" != "$ETIKET" ] || DUR+=("$ETIKET zaten guncel")
BOS_MB="$(df -Pm "$KOK" 2>/dev/null | awk 'NR == 2 {print $4}')"
echo "   disk ($KOK): boş ${BOS_MB:-?} MB (yeni sürüm dizini ve venv için en az $EN_AZ_MB MB)"
[ -n "${BOS_MB:-}" ] && [ "$BOS_MB" -ge "$EN_AZ_MB" ] 2>/dev/null || DUR+=("diskte $EN_AZ_MB MB'tan az boş yer")

echo "-- [2/6] etiket sunucudan görünüyor mu"
if [ -n "${PM_GIT_ATLA:-}" ]; then
  echo "   atlandı (PM_GIT_ATLA)"
else
  if [ -f "$ETC/deploy_key" ] && [[ "$GIT_URL" != /* ]]; then
    if [ -s "$ETC/known_hosts" ]; then
      export GIT_SSH_COMMAND="ssh -i $ETC/deploy_key -o IdentitiesOnly=yes -o UserKnownHostsFile=$ETC/known_hosts -o StrictHostKeyChecking=yes"
    else
      export GIT_SSH_COMMAND="ssh -i $ETC/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    fi
  fi
  UZAK="$(timeout 60 git ls-remote --tags "$GIT_URL" "refs/tags/$ETIKET" "refs/tags/$ETIKET^{}" 2>&1)"; RC=$?
  if [ "$RC" != "0" ]; then
    echo "   okunamadı (çıkış $RC): $(echo "$UZAK" | head -1 | cut -c1-120)"; DUR+=("etiket sunucudan okunamadı")
  elif [ -z "$UZAK" ]; then
    echo "   yok: $ETIKET GitHub'da değil"; DUR+=("etiket GitHub'da yok")
  else
    NESNE="$(echo "$UZAK" | awk '$2 ~ /\^\{\}$/ {print substr($1, 1, 12)}')"
    if [ -n "$NESNE" ]; then echo "   var: $ETIKET → ${NESNE} (açıklamalı)"
    else echo "   var ama açıklamalı değil: $ETIKET"; DUR+=("etiket açıklamalı değil (guncelle.sh durur)"); fi
  fi
fi

echo "-- [3/6] açık iş ve bekleyen giden"
ACIK_IS="$(sor "SELECT count(*) FROM isler WHERE durum IN ('sirada','isleniyor')")"
BEKLEYEN="$(sor "SELECT count(*) FROM giden WHERE durum IN ('bekliyor', 'gonderiliyor')")"
SEMA="$(sor "SELECT max(surum) FROM sema_surumu")"
echo "   açık iş ${ACIK_IS:-?} · bekleyen giden ${BEKLEYEN:-?} · şema ${SEMA:-?}"
[ "${ACIK_IS:-x}" = "0" ] || DUR+=("açık iş 0 değil (kurulum servisleri birkaç saniye durdurur; iş bitince yeniden koşun)")
[ "${BEKLEYEN:-x}" = "0" ] || DUR+=("bekleyen giden 0 değil")

echo "-- [4/6] kurulumla mesaj doğurabilecek kayıtlar (BK-10, D-19)"
MK_24="$(sor "SELECT count(*) FROM muhendis_kontrolleri WHERE durum = 'bekliyor' AND muhendis IS NOT NULL AND olusturuldu < now() - interval '24 hours'")"
MK_ACIK="$(sor "SELECT count(*) FROM muhendis_kontrolleri WHERE durum = 'bekliyor' AND muhendis IS NOT NULL")"
MK_PATRON="$(sor "SELECT count(*) FROM muhendis_kontrolleri WHERE patron_durum = 'bekliyor'")"
REV_ONAY="$(sor "SELECT count(*) FROM revizyonlar WHERE durum = 'onay_bekliyor'")"
echo "   kararı bekleyen mühendis kontrolü: ${MK_ACIK:-?} (24 saati geçmiş: ${MK_24:-?}) · fiyat hatırlatması bekleyen: ${MK_PATRON:-?} · onay bekleyen revizyon: ${REV_ONAY:-?}"
if [ "${MK_24:-0}" != "0" ]; then
  echo "   NOT: 24 saati geçmiş ${MK_24} kontrol kurulumdan sonraki ilk mesai dakikasında (08:00–20:00 İstanbul) kapanır; her biri için Patron'a"
  echo "        1 bildirim gider, Patron'un 24 saatlik penceresi kapalıysa ücretli şablon (portman_patron_bekliyor_v1)."
fi
echo "   onay bekleyen revizyon bayi yeniden yazınca kapanır (D-19 bayi tarafı); kapanış için bayiye mesaj gitmez"

echo "-- [5/6] ayarlar ($DATA/settings.json; yalnız açık/kapalı)"
if [ -r "$DATA/settings.json" ]; then
  python3 - "$DATA/settings.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
def ac(k):
    v = d.get(k)
    if isinstance(v, dict):
        return "açık" if v.get("acik") is True or v.get("mod") == "acik" else ("gölge" if v.get("mod") == "golge" else "kapalı")
    return "ayarda yok → kapalı" if k not in d else "kapalı"
print(f"   kanal (enabled): {'açık' if d.get('enabled') is True else 'kapalı'} · dry_run: {'evet' if d.get('dry_run') is True else 'hayır'}"
      f" · mesaj katmanı: {'açık' if d.get('mesaj_katmani') is True else 'kapalı'} · 3D adresi (ucb_taban_url): {'dolu' if d.get('ucb_taban_url') else 'boş'}")
print(f"   plan üretimi (İE-14): {ac('plan_uretimi')} · LLM-önce revizyon: {ac('llm_once_revizyon')}")
yeni = [("banka_germe", "oda büyütme, İE-23"), ("gorsel_okuma", "çizim ve PDF okuma, İE-20, satır 83"),
        ("talep_formu", "talep ve revizyon formu, İE-20, satır 110"), ("bayi_kaydi", "WhatsApp'tan bayi kaydı, İE-22, satır 111"),
        ("yarim_pano", "havuz evinde yarım pano uzat / kısalt, İE-39")]
print("   yeni özellikler: " + " · ".join(f"{k} ({a}): {ac(k)}" for k, a in yeni))
acik = [k for k, _ in yeni if ac(k) == "açık"]
print("   yeni özelliklerin hepsi kapalı" if not acik else f"   DİKKAT: açık yeni özellik: {', '.join(acik)}")
PY
else
  echo "   okunamadı: $DATA/settings.json"; DUR+=("settings.json okunamadı")
fi

echo "-- [6/6] son yedek ve öz-test"
YZ="$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1])).get("zaman", 0)))' "$DATA/nabiz/yedek.json" 2>/dev/null || echo 0)"
if [ "$YZ" = "0" ]; then echo "   son yedek: kayıt yok ($DATA/nabiz/yedek.json)"
else echo "   son yedek: $(( (SIMDI - YZ) / 3600 )) saat önce ($(date -d "@$YZ" '+%Y-%m-%d %H:%M %Z' 2>/dev/null || echo "$YZ"))"; fi
# Ajan öz-testi (kanal/worker.py › oz_test) data/self-test-result.json yoksa koşar ve LLM anahtarı varsa 1 ücretli çağrı yapar.
if [ -f "$DATA/self-test-result.json" ]; then
  OZ="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("surum") or "?", d.get("state") or "?")' "$DATA/self-test-result.json" 2>/dev/null || echo '? ?')"
  echo "   öz-test sonucu var (sürüm ${OZ% *}, ${OZ#* }): kurulumda öz-test yeniden koşmaz, LLM çağrısı yok"
else
  echo "   DİKKAT: öz-test sonucu yok: kurulumdan sonra ajan öz-testi koşar; LLM anahtarı varsa 1 ücretli çağrı (~0,03 \$)"
fi

if [ "${#DUR[@]}" -eq 0 ]; then
  echo "== sonuç: KURULABİLİR (hiçbir şey değişmedi)"
else
  printf '   bekle: %s\n' "${DUR[@]}"
  echo "== sonuç: BEKLE (${#DUR[@]} madde; hiçbir şey değişmedi)"
fi
}
ana "$@" < /dev/null
