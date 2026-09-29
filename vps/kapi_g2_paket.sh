#!/usr/bin/env bash
# PORTMAN · Kapı G yeniden denemesi (İE-02): VPS'teki paketin, öz-testin ve korunması gereken ayarların SALT OKUNUR denetimi.
# Hiçbir şeyi değiştirmez; LLM ya da WhatsApp çağrısı yapmaz. Yüklemeden önce (beklenen: canlı paket) ve sonra (beklenen: yeni paket):
#   ssh portman-vps 'PM_BEKLENEN=<64 haneli sha256> bash -s' < kapi_g2_paket.sh > 0_paket_once.txt
#   ssh portman-vps 'PM_BEKLENEN=<sha256> PM_KARAR=<karar.py sha256> PM_BASLANGIC="2026-09-29 21:00:00" bash -s' < kapi_g2_paket.sh > 1_paket_sonra.txt
# Gösterir: kurulu paketin özeti ve sürümü; pakette kaç dosya olduğu ve kurulu dizinle birebir aynı olup olmadığı; beyin/karar.py özeti;
# çalışan agent.py'nin paketle aynı olup olmadığı; bir önceki paket (app.old) ve pkg/ arşivi; öz-test sonucu (adımlar, LLM modeli ve
# token'ları); servis, kalıcı mod (süreçte PORTMAN_PG_DSN var mı), drop-in; agent.env'deki anahtar ADLARI ve dosyaların değişme zamanı;
# hosting'in bildirdiği ayar ve paket. PM_BASLANGIC verilirse o andan sonraki paket/öz-test günlük satırları.
# Yazdırmaz: anahtar değeri, telefon numarası, mesaj metni, öz-testin LLM özeti.
# Test için: PM_HOME, PM_ENV, PM_ETC.
# Gövde tek işlevdir ve girdisi /dev/null'dur (bkz. kapi_f_*.sh: 'bash -s' betiğinin kalanını sudo yutmasın).
ana() {
set -u
cd /tmp
PM_HOME="${PM_HOME:-/opt/portman}"; PM_ENV="${PM_ENV:-/etc/portman/agent.env}"; PM_ETC="${PM_ETC:-/etc}"
BEK="${PM_BEKLENEN:-}"; KARAR="${PM_KARAR:-}"; BAS="${PM_BASLANGIC:-}"
[[ "$BEK" =~ ^[0-9a-f]{64}$ ]] || { echo "DUR: PM_BEKLENEN verilmedi (beklenen paketin 64 haneli sha256'sı)"; exit 1; }
[[ -z "$KARAR" || "$KARAR" =~ ^[0-9a-f]{64}$ ]] || { echo "DUR: PM_KARAR 64 haneli sha256 olmalı"; exit 1; }
[[ -z "$BAS" || "$BAS" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]] || { echo "DUR: PM_BASLANGIC biçimi \"YYYY-AA-GG SS:DD:ss\""; exit 1; }
echo "== Kapı G yeniden deneme · paket ve ayar denetimi · salt okunur · betik 2026-09-29 · $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "-- servis"
systemctl show portman-agent -p ActiveState -p MainPID -p ActiveEnterTimestamp -p NRestarts -p DropInPaths --no-pager 2>&1 | sed 's/^/   /'
PID="$(systemctl show portman-agent -p MainPID --value 2>/dev/null)"
echo "   ajan sürecinde PORTMAN_PG_DSN (kalıcı mod): $( { tr '\0' '\n' < "/proc/$PID/environ"; } 2>/dev/null | grep -c '^PORTMAN_PG_DSN=' || true)"
PM_HOME="$PM_HOME" PM_ENV="$PM_ENV" PM_ETC="$PM_ETC" BEK="$BEK" KARAR="$KARAR" BAS="$BAS" python3 - <<'PY'
import hashlib, json, os, re, time, urllib.error, urllib.request, zipfile
from pathlib import Path
HOME, ENV, ETC = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"]), Path(os.environ["PM_ETC"])
BEK, KARAR, BAS = os.environ["BEK"], os.environ["KARAR"], os.environ["BAS"]
APP, PKG, DATA = HOME / "app", HOME / "pkg", HOME / "data"
sha = lambda b: hashlib.sha256(b).hexdigest()
oku = lambda p: p.read_text(errors="replace").strip() if p.exists() else "-"
zaman = lambda p: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)) if p.exists() else "yok"

kurulu = oku(APP / "PACKAGE_SHA256")
print(f"-- kurulu paket: {kurulu[:16]}… · beklenenle aynı: {'EVET' if kurulu == BEK else 'HAYIR'} · sürüm {oku(APP / 'SURUM.txt')}")
z = PKG / f"{BEK}.zip"
if not z.exists():
    print(f"   pkg/{BEK[:16]}….zip YOK: dosya karşılaştırması yapılamadı")
else:
    ham = z.read_bytes()
    print(f"   pkg arşivi: {len(ham)} B · özeti {'arşiv adıyla aynı' if sha(ham) == BEK else 'FARKLI'}")
    with zipfile.ZipFile(z) as zz:
        uyeler = [a for a in zz.namelist() if not a.endswith("/")]
        farkli = [a for a in uyeler if not (APP / a).is_file() or sha((APP / a).read_bytes()) != sha(zz.read(a))]
    fazla = sorted(str(p.relative_to(APP)) for p in APP.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                   and p.suffix != ".pyc" and p.name != "PACKAGE_SHA256" and str(p.relative_to(APP)) not in set(uyeler))
    print(f"   pakette {len(uyeler)} dosya · kurulu dizinle birebir aynı {len(uyeler) - len(farkli)} · farklı ya da eksik {farkli} · pakette olmayan {fazla}")
kp = APP / "beyin" / "karar.py"
if kp.exists():
    ks = sha(kp.read_bytes())
    print(f"   beyin/karar.py: {ks[:16]}…" + (f" · beklenenle aynı: {'EVET' if ks == KARAR else 'HAYIR'}" if KARAR else ""))
ajan = HOME / "agent.py"
if ajan.exists() and (APP / "agent.py").exists():
    print(f"   çalışan agent.py paketteki ile aynı: {'EVET' if ajan.read_bytes() == (APP / 'agent.py').read_bytes() else 'HAYIR'}")
print(f"-- bir önceki paket (app.old): {oku(HOME / 'app.old' / 'PACKAGE_SHA256')[:16]}… · sürüm {oku(HOME / 'app.old' / 'SURUM.txt')}")
print("   pkg/ arşivi (dokunulmadı): " + " ".join(f"{p.name[:16]}…({p.stat().st_size} B, {zaman(p)[5:16]})" for p in sorted(PKG.glob("*.zip"), key=lambda p: p.stat().st_mtime)))
st = DATA / "self-test-result.json"
if st.exists():
    try:
        j = json.loads(st.read_text(encoding="utf-8"))
        a = j.get("adimlar") or {}
        l = a.get("llm") or {}
        ts = lambda t: time.strftime("%H:%M:%S", time.localtime(t)) if t else "-"
        print(f"-- öz-test: {j.get('state')} · sürüm {j.get('surum')} · başladı {ts(j.get('started_at'))} · bitti {ts(j.get('finished_at'))} · {j.get('sure_s')} sn")
        print("   adımlar: " + " · ".join(f"{k} {v.get('passed') if isinstance(v, dict) else v}" for k, v in a.items()))
        if l:
            print(f"   LLM: {l.get('backend')}/{l.get('model')} · {l.get('girdi_token')}+{l.get('cikti_token')} token · tekrar {l.get('tekrar')} · {l.get('sure_ms')} ms"
                  f" · niyet {l.get('niyet')} · katalog {l.get('katalog_kodu')}" + (f" · atlandı/hata: {str(l.get('atlandi') or l.get('hata'))[:120]}" if l.get("passed") is not True else ""))
    except Exception as e:
        print(f"-- öz-test sonucu okunamadı ({type(e).__name__})")
else:
    print("-- öz-test: sonuç dosyası YOK (yeni paket kurulduysa öz-test henüz koşmadı)")
print("-- korunan ayarlar (yalnız adlar ve değişme zamanları)")
try:
    adlar = [s.split("=", 1)[0].strip() for s in ENV.read_text().splitlines() if "=" in s and not s.lstrip().startswith("#")]
    print(f"   agent.env: değişti {zaman(ENV)} · anahtar adları {adlar}")
except Exception as e:
    print(f"   agent.env okunamadı ({type(e).__name__})")
for p in (ETC / "portman" / "pg.env", ETC / "systemd" / "system" / "portman-agent.service.d" / "kalici.conf"):
    print(f"   {p}: {'var' if p.exists() else 'YOK'} · değişti {zaman(p)}")
try:
    env = {}
    for s in ENV.read_text().splitlines():
        if "=" in s: k, v = s.split("=", 1); env[k.strip()] = v.strip().strip("\"'")
    req = urllib.request.Request(env["PORTMAN_API_URL"].split("?")[0] + "?op=settings", headers={"X-Portman-Token": env["PORTMAN_API_TOKEN"], "User-Agent": "portman-kapi-g2"})
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode())
    pk = j.get("package") or {}
    print(f"-- hosting: worker {j.get('worker')} · mode {j.get('mode')} · dry_run {j.get('dry_run')} · llm {(j.get('llm') or {}).get('backend')}/{(j.get('llm') or {}).get('model')}")
    print(f"   hosting paketi: {str(pk.get('sha256') or '-')[:16]}… · {pk.get('size')} B · sürüm {pk.get('surum')} · beklenenle aynı: {'EVET' if pk.get('sha256') == BEK else 'HAYIR'}")
except urllib.error.HTTPError as e:
    print(f"-- hosting: HTTP {e.code}")
except Exception as e:
    print(f"-- hosting: ulaşılamadı ({type(e).__name__})")
if BAS:
    print(f"-- günlük ({BAS} sonrası: paket, öz-test, başlama)")
    g = HOME / "logs" / "agent.log"
    for x in (g.read_text(errors="replace").splitlines() if g.exists() else []):
        if x[:19] < BAS: continue
        r = x[20:]
        if r.startswith(("paket", "agent.py", "öz-test", "başladı", "durduruldu", "beklenmeyen", "yeniden başlama")) or " api:" in " " + r:
            print(f"   {x[:19]} · {re.sub(r'[0-9a-f]{16,}', '…', r)[:120]}")
PY
echo "== bitti"
}
ana "$@" < /dev/null
