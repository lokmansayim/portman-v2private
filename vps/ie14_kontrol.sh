#!/usr/bin/env bash
# PORTMAN · İE-14 canlıya alma ve deneme kontrolü (SALT OKUNUR; root). Hiçbir şeyi değiştirmez; LLM ya da WhatsApp çağrısı yapmaz.
# Gösterir: kurulu sürüm, şema, açık iş, bekleyen giden, aktif kartlar (rol · kod · numaranın yalnız son 4 hanesi), İE-14 ayarları,
# sağlık kodu ve — `deneme <dakika>` verilirse — son N dakikanın işleri, plan üretimleri ve gölge okuma kıyasları (numara ve mesaj
# metni yok). Sır yazmaz.
# Sunucuda kopyası yokken (ön kontrol, sürümden önce; Lokman, Mac'ten; AGENTS.md › Sunucu erişimi):
#   ssh portman-vps 'timeout 120 bash -s' < vps/ie14_kontrol.sh > ie14_1_on_kontrol.txt 2>&1
# Sürümden sonra (sunucudaki kopya):
#   ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/ie14_kontrol.sh' > ie14_3_sonra.txt 2>&1
#   ssh -n portman-vps 'timeout 120 bash /opt/portman/guncel/vps/ie14_kontrol.sh deneme 90' > ie14_5_deneme.txt 2>&1
# Sınama: PM_KOK, PM_PSQL, PM_PYTHON, PM_SAGLIK_URL.
set -uo pipefail
KOK="${PM_KOK:-/opt/portman}"; DATA="$KOK/data"; PY="${PM_PYTHON:-python3}"
PSQL="${PM_PSQL:-sudo -u postgres psql -X -q -tA -d portman}"; SAGLIK_URL="${PM_SAGLIK_URL:-http://127.0.0.1:8081/saglik}"
cd /tmp
q() { $PSQL -c "$1" 2>&1 | sed 's/^/   /'; }
var() { [ "$($PSQL -c "SELECT to_regclass('$1') IS NOT NULL" 2>/dev/null)" = "t" ]; }

echo "== PORTMAN · İE-14 kontrol · $(date -u +%FT%TZ) UTC"
echo "-- kurulu sürüm: $(basename "$(readlink -f "$KOK/guncel" 2>/dev/null || echo yok)")"
KOD="$(curl -s -o /dev/null -w '%{http_code}' "$SAGLIK_URL" 2>/dev/null || true)"
echo "-- sağlık: $([ -n "$KOD" ] && [ "$KOD" != "000" ] && echo "$KOD" || echo "yanıt yok")"
echo "-- veritabanı:"
q "SELECT 'şema '||max(surum) FROM sema_surumu"
q "SELECT 'açık iş '||count(*) FROM isler WHERE durum IN ('sirada','isleniyor')"
q "SELECT 'bekleyen giden '||count(*) FROM giden WHERE durum = 'bekliyor'"
for t in plan_uretimleri okuma_kiyaslari; do
  if var "$t"; then q "SELECT '$t: var, '||count(*)||' satır' FROM $t"; else echo "   $t: yok"; fi
done
echo "-- aktif kartlar (rol · kod · numaranın son 4 hanesi):"
q "SELECT rol||' · '||coalesce(nullif(kod,''),'-')||' · …'||right(numara,4) FROM bayiler WHERE aktif ORDER BY rol, kod"
q "SELECT 'aktif kart toplam '||count(*) FROM bayiler WHERE aktif"

echo "-- ayarlar (İE-14 ve kanal anahtarları; sır içermez):"
AY="$KOK/guncel/kanal/ayarlar.py"
if [ -f "$AY" ]; then
  "$PY" - "$AY" "$DATA" <<'PYEOF' 2>&1 | sed 's/^/   /'
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("ayarlar", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
a = m.oku(sys.argv[2])
for k in ("enabled", "dry_run", "mode", "mesaj_katmani", "plan_uretimi", "llm_once_revizyon"):
    print(f"{k}: {json.dumps(a.get(k), ensure_ascii=False)}")
PYEOF
else
  echo "   ayarlar.py yok"
fi

if [ "${1:-}" = "deneme" ]; then
  DK="${2:-90}"
  echo "-- son $DK dakikanın işleri (sıra · durum · eylem · gerekçe · LLM çağrısı):"
  q "SELECT j.id||' · '||j.durum||' · '||coalesce(j.sonuc->>'eylem','-')||' · '||left(coalesce(j.sonuc->>'gerekce','-'),90)
            ||' · çıkarım '||CASE WHEN (j.cikarim->'meta'->>'backend') IN ('anthropic','openai') THEN '1' ELSE '0' END
            ||coalesce(' · plan '||(j.sonuc->'plan_uretimi'->>'cagri'),'')||coalesce(' · düzenleme '||(j.sonuc->'plan_duzenleme'->>'cagri'),'')
            ||coalesce(' · gölge '||(j.sonuc->'okuma_kiyasi'->>'cagri'),'')
     FROM isler j WHERE j.basladi >= now() - make_interval(mins => $DK) ORDER BY j.id"
  echo "-- son $DK dakikanın giden satırları (iş · sıra · tür · durum):"
  q "SELECT g.is_id||' · '||g.sira||' · '||g.kind||' · '||g.durum FROM giden g JOIN isler j ON j.id = g.is_id
     WHERE j.basladi >= now() - make_interval(mins => $DK) ORDER BY g.is_id, g.olusturuldu, g.sira"
  if var plan_uretimleri; then
    echo "-- plan üretimleri (durum · yol · puan · süre ms · çağrı · seçilen plan · İş Emri):"
    q "SELECT durum||' · '||coalesce(yol,'-')||' · '||coalesce(puan::text,'-')||' · '||coalesce(sure_ms::text,'-')||' · '||cagri
              ||' · '||coalesce(plan_kodu,'-')||' · '||coalesce(is_emri_no,'-')
       FROM plan_uretimleri WHERE olusturuldu >= now() - make_interval(mins => $DK) ORDER BY olusturuldu"
  fi
  if var okuma_kiyaslari; then
    echo "-- gölge okuma kıyasları (model · rev · sınıf · çağrı):"
    q "SELECT coalesce(model,'-')||' · r'||coalesce(rev::text,'-')||' · '||sinif||' · '||cagri
       FROM okuma_kiyaslari WHERE olusturuldu >= now() - make_interval(mins => $DK) ORDER BY olusturuldu"
  fi
fi
echo "== bitti"
