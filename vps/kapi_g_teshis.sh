#!/usr/bin/env bash
# PORTMAN · Kapı G adım 4 teşhisi · SALT OKUNUR. Hiçbir şeyi değiştirmez, LLM ya da WhatsApp çağrısı yapmaz.
#   ssh portman-vps 'PM_BASLANGIC="2026-09-29 19:20:00" bash -s' < kapi_g_teshis.sh > g4_teshis.txt
# G'deki her işte: LLM çıkarımının niyeti, dolu alanlarının adları ve pencere satırları (oda, ölçü, işlem, söz niyeti: Patron'un
# deneme mesajındaki plan parametreleri); kural katmanının notları; işin gerekçesi (is_emri/sor/cevapla için sistem metni);
# konuşmanın revizyon sayacı ve askıdaki soru. G'de üretilen her revizyonda: İş Emri'ndeki pencereler ve varyantlar.
# Yazdırmaz: telefon numarası, mesaj metni, WhatsApp kimliği (yalnız md5 izi), müşteri alanları, anahtar.
# Gövde tek işlevdir ve girdisi /dev/null'dur (bkz. kapi_f_*.sh).
ana() {
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PY="${PM_PY:-$PM_HOME/venv/bin/python}"; APP="$PM_HOME/app"
OLARAK="${PM_OLARAK:-sudo -u portman env PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=$PM_HOME/data}"
BAS="${PM_BASLANGIC:-}"
[[ "$BAS" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]] || { echo "DUR: PM_BASLANGIC verilmedi"; exit 1; }
echo "== Kapı G · adım 4 teşhisi · salt okunur · $(date '+%Y-%m-%d %H:%M:%S %Z')"
KOD="$(cat <<'PY'
import sys, time, hashlib
sys.path.insert(0, sys.argv[1])
import depo
bas = time.mktime(time.strptime(sys.argv[2], "%Y-%m-%d %H:%M:%S"))
iz = lambda s: hashlib.md5(s.encode()).hexdigest()[:10] if s else "-"
DISLA = {"niyet", "guven", "ozet", "belirsizlikler", "musteri"}
def pencereler(liste):
    return [{a: p.get(a) for a in ("mahal", "olcu", "islem", "soz_niyeti", "duvar", "islem_kaynak") if p.get(a) not in (None, "")} for p in (liste or [])]
d = depo.Depo()
with d.baglan() as c:
    for j in c.execute("SELECT i.id, i.mesaj_id, i.cikarim, i.sonuc, i.basladi FROM isler i WHERE i.olusturuldu >= to_timestamp(%s) ORDER BY i.id", (bas,)):
        t = (j["cikarim"] or {}).get("talep") or {}; s = j["sonuc"] or {}
        dolu = sorted(k for k, v in t.items() if k not in DISLA and v not in (None, [], {}, ""))
        print(f"-- iş {j['id']} · mesaj {iz(j['mesaj_id'])} · LLM niyet {t.get('niyet')}/{t.get('guven')} · dolu alanlar {dolu}")
        if t.get("pencereler"):
            print(f"   LLM pencere satırları: {pencereler(t['pencereler'])}")
        if t.get("varyantlar"):
            print(f"   LLM varyantlar: {[v.get('tur') for v in t['varyantlar']]}")
        print(f"   sonuç: eylem {s.get('eylem')} · {s.get('is_emri_no') or '-'} r{int(s.get('revizyon') or 0):02d} · aşama {s.get('asama')}"
              + (f" · gerekçe: {s.get('gerekce')}" if s.get("eylem") in ("is_emri", "sor", "cevapla") else ""))
    k = c.execute("SELECT durum FROM konusmalar ORDER BY guncellendi DESC LIMIT 1").fetchone()
    if k:
        dd = k["durum"]
        print(f"-- konuşma (şimdi): aşama {dd.get('asama')} · revizyon sayacı {dd.get('revizyon')} · askıdaki soru {dd.get('son_soru_alani')} · proje {dd.get('proje_id')}"
              f" · son İş Emri {(dd.get('son_is_emri') or {}).get('is_emri_no')} r{int((dd.get('son_is_emri') or {}).get('revizyon') or 0):02d}")
        gb = time.mktime(time.strptime(sys.argv[2], "%Y-%m-%d %H:%M:%S"))
        print("   kural notları (G): " + " | ".join(f"{time.strftime('%H:%M:%S', time.localtime(n.get('t', 0)))} {n.get('metin')}"
                                                   for n in dd.get("gecmis") or [] if n.get("yon") == "kural" and n.get("t", 0) >= gb))
        print("   taslak pencere satırları: " + str(pencereler((dd.get("taslak") or {}).get("pencereler"))))
    for r in c.execute("SELECT rv.is_emri_no, rv.rev, rv.durum, rv.is_emri FROM revizyonlar rv WHERE rv.uretildi >= to_timestamp(%s) ORDER BY rv.id", (bas,)):
        ie = r["is_emri"] or {}
        pen = [f"{a.get('mahal')}: {a.get('olcu')}" for a in ie.get("acikliklar") or [] if a.get("tur") == "pencere"]
        print(f"-- revizyon {r['is_emri_no']} r{r['rev']:02d} ({r['durum']}) · varyantlar {[v.get('tur') if isinstance(v, dict) else v for v in ie.get('varyantlar') or []]}"
              f" · pencereler {pen}")
PY
)"
$OLARAK "$PY" -c "$KOD" "$APP" "$BAS" 2>&1 | sed 's/^/ /'
echo "== bitti"
}
ana "$@" < /dev/null
