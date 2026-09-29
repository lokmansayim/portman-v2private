#!/usr/bin/env bash
# PORTMAN · Kapı G (İE-02): kabul gösteriminin her adımından sonra SALT OKUNUR durum ve kanıt. Hiçbir şeyi değiştirmez.
#   ssh portman-vps 'PM_BASLANGIC="2026-09-29 19:40:00" bash -s' < kapi_g_durum.sh > g1_durum.txt
# Gösterir: servis ve kalıcı mod, hosting ayarı, G başladıktan sonraki günlük olayları; G'de açılan her iş (mesaj izi, eylem, niyet,
# proje ve revizyon, LLM token'ları, onay denetimi); sorular (doğuran ve kapatan mesaj); projeler ve revizyonlar (PDF adı, özeti,
# gönderim ve teslim durumu); giden satırlar; mesaj başına iş sayısı; açık iş; token üzerinden maliyet ve sınırlar.
# Yeniden deneme turu (29.09 20:45 onayı): sınırlar Patron mesajı 7, LLM çağrısı 9, 0,30 $, giden WhatsApp 12; PM_BASLANGIC'ten sonra
# başlayan paket öz-testinin LLM çağrısı ve token'ları da sayılır (yükleme öncesindeki an verilmelidir).
# Yazdırmaz: telefon numarası, mesaj metni, WhatsApp kimliği (yalnız md5 izi, ilk 10 hane), anahtar, gerekçenin serbest metni.
# Test için: PM_HOME, PM_ENV, PM_PY, PM_OLARAK, PM_BASLANGIC.
# Gövde tek işlevdir ve girdisi /dev/null'dur (bkz. kapi_f_*.sh: 'bash -s' betiğinin kalanını sudo yutmasın).
ana() {
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PM_ENV="${PM_ENV:-/etc/portman/agent.env}"; PY="${PM_PY:-$PM_HOME/venv/bin/python}"; APP="$PM_HOME/app"
OLARAK="${PM_OLARAK:-sudo -u portman env PORTMAN_PG_DSN=dbname=portman PORTMAN_KANAL_DIR=$PM_HOME/data}"
BAS="${PM_BASLANGIC:-}"
[[ "$BAS" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]] || { echo "DUR: PM_BASLANGIC verilmedi (\"YYYY-AA-GG SS:DD:ss\", G'nin başladığı an)"; exit 1; }
echo "== Kapı G · durum ve kanıt · salt okunur · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z') · G başlangıcı $BAS"
echo "-- servis"
systemctl show portman-agent -p ActiveState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
PID="$(systemctl show portman-agent -p MainPID --value 2>/dev/null)"
echo "   ajan sürecinde PORTMAN_PG_DSN (kalıcı mod): $( { tr '\0' '\n' < "/proc/$PID/environ"; } 2>/dev/null | grep -c '^PORTMAN_PG_DSN=' || true)"
PM_HOME="$PM_HOME" PM_ENV="$PM_ENV" BAS="$BAS" python3 - <<'PY'
import json, os, re, urllib.error, urllib.request
from pathlib import Path
HOME, ENV, BAS = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"]), os.environ["BAS"]
try:
    env = {}
    for s in ENV.read_text().splitlines():
        if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-g"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode())
    pk = (HOME / "app" / "PACKAGE_SHA256").read_text().strip() if (HOME / "app" / "PACKAGE_SHA256").exists() else ""
    print(f"-- hosting: worker {j.get('worker')} · mode {j.get('mode')} · dry_run {j.get('dry_run')} · llm {(j.get('llm') or {}).get('backend')}/{(j.get('llm') or {}).get('model')}"
          f" · paket {'VPS ile aynı' if (j.get('package') or {}).get('sha256') == pk else 'FARKLI'}")
except urllib.error.HTTPError as e:
    print(f"-- hosting: HTTP {e.code}")
except Exception as e:
    print(f"-- hosting: ulaşılamadı ({type(e).__name__})")
print(f"-- günlük ({BAS} sonrası; numara ve metin yazılmaz)")
g = HOME / "logs" / "agent.log"
for x in (g.read_text(errors="replace").splitlines() if g.exists() else []):
    if x[:19] < BAS: continue
    r = x[20:]
    if r.startswith(("başladı", "durduruldu", "iş ", "tekrar gelen", "öz-test", "kalıcı mod bekliyor", "yeniden başlama", "hosting sonucu", "diskteki", "paket", "agent.py")) \
            or " api:" in " " + r or r.startswith("beklenmeyen") or r.startswith("Postgres"):
        r = re.sub(r"kimden \S+", "kimden …", r)
        print(f"   {x[:19]} · {re.sub(r'[0-9a-f]{16,}', '…', r)[:120]}")
PY
KOD="$(cat <<'PY'
import sys, time, hashlib, json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import depo
bas = time.mktime(time.strptime(sys.argv[2], "%Y-%m-%d %H:%M:%S"))
iz = lambda s: hashlib.md5(s.encode()).hexdigest()[:10] if s else "-"
GIRIS, CIKIS = 4.0, 20.0          # claude-opus-5-5, $/1M token (resmî fiyat sayfası)
d = depo.Depo()
with d.baglan() as c:
    isler = c.execute("SELECT i.id, i.mesaj_id, i.durum, i.deneme, i.cikarim, i.sonuc, i.hata IS NOT NULL AS hata, m.tur, m.alinti_id, "
                      "to_char(m.wa_zamani AT TIME ZONE 'Europe/Istanbul', 'HH24:MI:SS') AS yazildi, "
                      "(SELECT count(*) FROM giden g WHERE g.is_id = i.id) AS giden "
                      "FROM isler i JOIN mesajlar m ON m.id = i.mesaj_id WHERE i.olusturuldu >= to_timestamp(%s) ORDER BY i.id", (bas,)).fetchall()
    print(f"-- G'deki işler ({len(isler)})")
    cagri = 0; gt = 0; ct = 0; bilinmeyen = 0; maliyet = 0.0
    st = Path(sys.argv[3]) / "self-test-result.json"          # yeni paketin öz-testi bu turda koştuysa (1 LLM çağrısı) sayılır
    try:
        oz = json.loads(st.read_text(encoding="utf-8")) if st.exists() else {}
    except Exception:
        oz = {}
    ol = (oz.get("adimlar") or {}).get("llm") or {}
    if (oz.get("started_at") or 0) >= bas and ("girdi_token" in ol or ol.get("passed") is False):
        n = 1 + int(ol.get("tekrar") or 0); cagri += n
        if ol.get("girdi_token") is not None and ol.get("cikti_token") is not None:
            gt += ol["girdi_token"]; ct += ol["cikti_token"]
            maliyet += (ol["girdi_token"] * GIRIS / 1e6 + ol["cikti_token"] * CIKIS / 1e6) * (2 if ol.get("tekrar") else 1)
        else:
            bilinmeyen += n
        print(f"-- paket öz-testi (bu turda): {oz.get('state')} · sürüm {oz.get('surum')} · LLM {ol.get('model')} · çağrı {n} · "
              f"{ol.get('girdi_token')}+{ol.get('cikti_token')} token · tekrar {'EVET' if ol.get('tekrar') else 'hayır'}")
    for j in isler:
        s = j["sonuc"] or {}; ck = j["cikarim"] or {}; m = ck.get("meta") or s.get("llm") or {}
        n = (1 + int(m.get("tekrar") or 0)) if ck else 0
        cagri += n
        gi, co = m.get("girdi_token"), m.get("cikti_token")
        if gi is not None and co is not None:
            gt += gi; ct += co
            mal = gi * GIRIS / 1e6 + co * CIKIS / 1e6
            if m.get("tekrar"):
                mal *= 2                  # ilk (şemaya uymayan) çağrının token'ları kaydedilmez: aynı büyüklükte sayılır (tahmin)
            maliyet += mal
        elif ck:
            bilinmeyen += n
        o = s.get("onay") or {}
        print(f"   iş {j['id']} · mesaj {iz(j['mesaj_id'])} · {j['yazildi']} · {j['tur']} · alıntı {iz(j['alinti_id'])} · {j['durum']} (deneme {j['deneme']})"
              f" · eylem {s.get('eylem')} · niyet {s.get('niyet')}/{s.get('guven')} · {s.get('is_emri_no') or '-'} r{int(s.get('revizyon') or 0):02d}"
              f" · aşama {s.get('asama')} · giden {j['giden']}")
        print(f"      LLM {m.get('model')} · çağrı {n} · {gi}+{co} token · tekrar {'EVET' if m.get('tekrar') else 'hayır'} · {m.get('sure_ms')} ms"
              + (f" · çıkarım HATASI" if ck.get("hata") else "") + (" · iş hatası" if j["hata"] else ""))
        if o:
            print(f"      onay denetimi: kabul {o.get('kabul')} · denetlenen {o.get('is_emri_no')} r{int(o.get('rev') or 0):02d} · sınır {o.get('sinir')} · neden {o.get('neden')}")
    print("-- sorular (G'de açılan)")
    for r in c.execute("SELECT s.id, s.alan, s.kaynak_mesaj_id, s.cevap_mesaj_id, s.durum, s.deneme, s.proje_id, "
                       "to_char(s.soruldu AT TIME ZONE 'Europe/Istanbul', 'HH24:MI:SS') AS soruldu, to_char(s.kapandi AT TIME ZONE 'Europe/Istanbul', 'HH24:MI:SS') AS kapandi "
                       "FROM sorular s WHERE s.soruldu >= to_timestamp(%s) ORDER BY s.id", (bas,)):
        print(f"   soru {r['id']} · alan {r['alan']} · doğuran mesaj {iz(r['kaynak_mesaj_id'])} · {r['durum']} (deneme {r['deneme']}) · kapatan mesaj {iz(r['cevap_mesaj_id'])}"
              f" · proje {r['proje_id']} · soruldu {r['soruldu']} · kapandı {r['kapandi']}")
    print("-- projeler ve revizyonlar (G'de açılan)")
    for r in c.execute("SELECT z.proje_id, z.is_emri_no, z.rev, z.revizyon_durumu, z.pdf_wamid, z.gonderim_durumu, z.teslim_durumu, "
                       "to_char(z.kabul_zamani AT TIME ZONE 'Europe/Istanbul', 'HH24:MI:SS') AS kabul, to_char(z.gonderildi_zamani AT TIME ZONE 'Europe/Istanbul', 'HH24:MI:SS') AS gonderildi, "
                       "to_char(z.teslim_zamani AT TIME ZONE 'Europe/Istanbul', 'HH24:MI:SS') AS teslim, z.onay_mesaj_id, z.onay_alintisi, rv.kaynak_mesaj_id, rv.pdf_yolu, rv.pdf_sha256 "
                       "FROM onay_zinciri z JOIN revizyonlar rv ON rv.id = z.revizyon_id WHERE rv.uretildi >= to_timestamp(%s) ORDER BY z.revizyon_id", (bas,)):
        print(f"   proje {r['proje_id']} · {r['is_emri_no']} r{r['rev']:02d} · {r['revizyon_durumu']} · doğuran mesaj {iz(r['kaynak_mesaj_id'])} · PDF {str(r['pdf_yolu'] or '').split('/')[-1]}"
              f" {str(r['pdf_sha256'] or '')[:16]} · PDF mesajı {iz(r['pdf_wamid'])} {r['gonderim_durumu']} · api kabul {r['kabul']} · Meta gönderdi {r['gonderildi']}"
              f" · teslim {r['teslim_durumu']} {r['teslim']} · onay mesajı {iz(r['onay_mesaj_id'])} (alıntı {iz(r['onay_alintisi'])})")
    print("-- giden satırlar (G)")
    for r in c.execute("SELECT g.is_id, g.sira, g.kind, g.tur, g.durum, g.dis_id, g.teslim_durumu, g.hostinge_verildi IS NOT NULL AS hostinge FROM giden g "
                       "WHERE g.olusturuldu >= to_timestamp(%s) ORDER BY g.olusturuldu, g.sira", (bas,)):
        print(f"   iş {r['is_id']} · {r['sira']} · {r['kind']}/{r['tur']} · {r['durum']} · hosting'e verildi {r['hostinge']} · WhatsApp mesajı {iz(r['dis_id'])} · teslim {r['teslim_durumu']}")
    en = c.execute("SELECT coalesce(max(n), 0) AS n FROM (SELECT count(*) AS n FROM isler GROUP BY mesaj_id) k").fetchone()["n"]
    acik = c.execute("SELECT count(*) AS n FROM isler WHERE durum IN ('sirada', 'isleniyor')").fetchone()["n"]
    gm = c.execute("SELECT count(*) AS n FROM mesajlar WHERE alindi >= to_timestamp(%s)", (bas,)).fetchone()["n"]
    gd = c.execute("SELECT count(*) AS n FROM giden WHERE olusturuldu >= to_timestamp(%s)", (bas,)).fetchone()["n"]
    uy = d.gonderilemeyen_sayisi(24, 300)
print(f"-- sağlık: açık iş {acik} · mesaj başına en çok iş {en} · son 24 saat {uy}")
print(f"== sayaçlar (bu tur): Patron mesajı {gm}/7 · LLM çağrısı {cagri}/9 (öz-test dahil; token'ı bilinmeyen {bilinmeyen}) · {gt} giriş + {ct} çıkış token"
      f" · maliyet ≈ {maliyet:.4f} $ / 0,30 $ (Opus 4 $ + 20 $ / 1M; tekrar varsa ilk çağrı aynı büyüklükte sayıldı) · giden WhatsApp {gd}/12")
PY
)"
$OLARAK "$PY" -c "$KOD" "$APP" "$BAS" "$PM_HOME/data" 2>&1 | sed 's/^/ /'
echo "== bitti"
}
ana "$@" < /dev/null
