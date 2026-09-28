#!/usr/bin/env bash
# PORTMAN · Kapı A (İE-02) · VPS tarafının SALT OKUNUR denetimi. Hiçbir dosyayı, ayarı ya da servisi değiştirmez.
# Mac'ten, Lokman çalıştırır (root parolası sorulur; asistan görmez):
#   ssh root@<VPS> 'bash -s' < kapi_a_salt_okunur.sh > kapi_a_vps_sonuc.txt 2>&1
# Yazdırmaz: eşleşme anahtarı, OpenAI anahtarı, telefon numarası, mesaj kimliği ya da metni. Anahtarlar yalnız 12 haneli
# SHA-256 parmak iziyle gösterilir. Hosting'e yalnız ajanın zaten kullandığı iki okuma isteği gider (op=settings, op=package);
# settings cevabındaki OpenAI anahtarı okunmadan atılır, yalnız "hosting veriyor mu" (evet/hayır) yazılır.
# Test için yollar ortamla değiştirilebilir (PM_HOME, PM_ENV, PM_SERVIS, PM_PID); canlıda verilmez.
set -u
export PM_HOME="${PM_HOME:-/opt/portman}" PM_ENV="${PM_ENV:-/etc/portman/agent.env}" PM_SERVIS="${PM_SERVIS:-portman-agent}"
echo "== Kapı A · VPS salt okunur denetim · betik 2026-09-28c · $(date -u +%Y-%m-%dT%H:%M:%SZ) · $(hostname 2>/dev/null)"
echo "-- işletim: $(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-?}") · python $(python3 -c 'import sys; print(sys.version.split()[0])' </dev/null 2>/dev/null)"

echo "-- servis"
if command -v systemctl >/dev/null 2>&1; then
  systemctl show "$PM_SERVIS" -p ActiveState -p SubState -p UnitFileState -p ActiveEnterTimestamp -p MainPID -p NRestarts \
    -p User -p EnvironmentFiles -p DropInPaths --no-pager </dev/null 2>&1 | sed 's/^/   /'
  PID="${PM_PID:-$(systemctl show "$PM_SERVIS" -p MainPID --value </dev/null 2>/dev/null)}"
else
  echo "   systemctl yok"; PID="${PM_PID:-0}"
fi
export PID

echo "-- Postgres (kapı D için başlangıç durumu; kurulum yapılmaz)"
PG_SERVIS="$(systemctl is-active postgresql </dev/null 2>/dev/null || true)"     # kurulu değilse "inactive" döner; tek satır yazılır
echo "   psql: $(command -v psql || echo yok) · servis: ${PG_SERVIS:-yok}"
echo "-- disk ve bellek: $(df -h "$PM_HOME" 2>/dev/null | awk 'NR==2{print "boş "$4" / "$2}') · $(free -m 2>/dev/null | awk '/^Mem:/{print "kullanılabilir bellek "$7" MB"}')"

python3 - <<'PY'
import hashlib, io, json, os, re, stat, time, urllib.error, urllib.request, zipfile
from pathlib import Path

HOME, ENV, PID = Path(os.environ["PM_HOME"]), Path(os.environ["PM_ENV"]), os.environ.get("PID") or "0"
def iz(b: bytes, n=16): return hashlib.sha256(b).hexdigest()[:n]
def dosya_iz(p: Path, n=16):
    try: return iz(p.read_bytes(), n)
    except OSError as e: return f"okunamadı ({type(e).__name__})"
def tarih(t): return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(t))
def deger(v: str) -> str:            # systemd EnvironmentFile gibi: boşluk ve çevreleyen tırnak atılır
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": v = v[1:-1]
    return v
def gizle(s: str) -> str:             # günlük satırı: mesaj kimliği, uzun rakam dizisi ve anahtar biçimli dizgeler çıkarılır
    s = re.sub(r"wamid\.[A-Za-z0-9+/=_-]+", "wamid.<gizli>", s)
    s = re.sub(r"\b(sk-|EAA)[A-Za-z0-9_-]{8,}", "<gizli>", s)
    s = re.sub(r"[0-9a-f]{32,}", "<gizli>", s)
    return re.sub(r"\d{7,}", lambda m: "…" + m.group(0)[-2:], s)

print("-- uygulama (/opt/portman)")
app = HOME / "app"
surum = (app / "SURUM.txt").read_text(errors="replace").strip() if (app / "SURUM.txt").exists() else "yok"
pksha = (app / "PACKAGE_SHA256").read_text().strip() if (app / "PACKAGE_SHA256").exists() else ""
print(f"   SURUM: {surum}")
print(f"   PACKAGE_SHA256: {pksha[:16] or 'yok'}")
ajan = HOME / "agent.py"
try:
    at = ajan.read_text(errors="replace")
    m = re.search(r'^SURUM\s*=\s*"([^"]+)"', at, re.M)
    print(f"   agent.py: sha {dosya_iz(ajan)} · SURUM {m.group(1) if m else '?'} · değişti {tarih(ajan.stat().st_mtime)}")
except OSError as e:
    print(f"   agent.py okunamadı ({type(e).__name__})")
for f in ("worker.py", "beyin/karar.py", "motor/dxf_out.py", "motor/cikarici.py", "agent.py"):
    print(f"   app/{f}: {dosya_iz(app / f)}")

pkg = HOME / "pkg" / f"{pksha}.zip"
if pksha and pkg.exists():
    raw = pkg.read_bytes()
    print(f"   pkg/{pksha[:12]}….zip: gerçek sha {iz(raw, 12)} ({'adıyla aynı' if hashlib.sha256(raw).hexdigest() == pksha else 'ADIYLA FARKLI'})")
    z = zipfile.ZipFile(io.BytesIO(raw)); adlar = [n for n in z.namelist() if not n.endswith("/")]
    kok = adlar[0].split("/")[0] if adlar and all(a.startswith(adlar[0].split("/")[0] + "/") for a in adlar if "/" in a) and "worker.py" not in adlar else None
    ayni, farkli, eksik = 0, [], []
    for n in adlar:
        yol = app / (n[len(kok) + 1:] if kok else n)
        if not yol.exists(): eksik.append(yol.relative_to(app).as_posix()); continue
        if hashlib.sha256(z.read(n)).digest() == hashlib.sha256(yol.read_bytes()).digest(): ayni += 1
        else: farkli.append(yol.relative_to(app).as_posix())
    paket_adlari = {(n[len(kok) + 1:] if kok else n) for n in adlar} | {"PACKAGE_SHA256"}
    fazla = sorted(p.relative_to(app).as_posix() for p in app.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                   and p.relative_to(app).as_posix() not in paket_adlari)
    print(f"   app ↔ paket: {ayni} dosya aynı · farklı {len(farkli)} {farkli[:8]} · eksik {len(eksik)} {eksik[:8]} · pakette olmayan {len(fazla)} {fazla[:8]}")
    if "agent.py" in {(n[len(kok) + 1:] if kok else n) for n in adlar}:
        pa = z.read(next(n for n in adlar if n.endswith("agent.py") and n.count("/") <= 1))
        print(f"   /opt/portman/agent.py ↔ paketteki agent.py: {'aynı' if pa == ajan.read_bytes() else 'FARKLI'}")
else:
    print(f"   pkg zip: {'yok' if pksha else 'PACKAGE_SHA256 yok'}")

print("-- eşleşme anahtarı (değer yazılmaz; parmak izi = SHA-256'nın ilk 12 hanesi)")
dosya_tok = None
try:
    st = ENV.stat()
    satirlar = ENV.read_text(errors="replace").splitlines()
    anahtarlar = [s.split("=", 1)[0].strip() for s in satirlar if "=" in s and not s.lstrip().startswith("#")]
    toks = [deger(s.split("=", 1)[1]) for s in satirlar if s.startswith("PORTMAN_API_TOKEN=")]
    dosya_tok = toks[0] if len(toks) == 1 else None
    print(f"   agent.env: değişti {tarih(st.st_mtime)} · sahip {st.st_uid}:{st.st_gid} · izin {oct(stat.S_IMODE(st.st_mode))} · "
          f"satır adları {anahtarlar} · CRLF {'var' if chr(13) in ENV.read_text(errors='replace') else 'yok'}")
    print(f"   dosyadaki anahtar: {('parmak izi ' + iz(dosya_tok.encode(), 12) + f' · uzunluk {len(dosya_tok)}') if dosya_tok else 'PORTMAN_API_TOKEN satırı yok ya da birden çok'}")
except OSError as e:
    print(f"   agent.env okunamadı ({type(e).__name__})")
surec_tok = None
try:
    if PID and PID != "0":
        env = Path(f"/proc/{PID}/environ").read_bytes().split(b"\0")
        s = [e.split(b"=", 1)[1].decode(errors="replace") for e in env if e.startswith(b"PORTMAN_API_TOKEN=")]
        surec_tok = s[0] if s else None
        print(f"   çalışan süreç (PID {PID}): {('parmak izi ' + iz(surec_tok.encode(), 12)) if surec_tok else 'anahtar ortamda yok'} · "
              f"dosyayla {'AYNI' if surec_tok and dosya_tok and surec_tok == dosya_tok else 'FARKLI ya da okunamadı'}")
    else:
        print("   çalışan süreç: yok (servis çalışmıyor)")
except OSError as e:
    print(f"   süreç ortamı okunamadı ({type(e).__name__})")

print("-- hosting (ajanın anahtarıyla iki okuma isteği; anahtar ve OpenAI anahtarı yazılmaz)")
url = None
try:
    for s in ENV.read_text(errors="replace").splitlines():
        if s.startswith("PORTMAN_API_URL="): url = deger(s.split("=", 1)[1]).rstrip("?")
except OSError:
    pass
tok = surec_tok or dosya_tok
if not (url and tok):
    print("   atlandı: adres ya da anahtar yok")
else:
    def istek(op):
        r = urllib.request.Request(f"{url}?op={op}", headers={"X-Portman-Token": tok, "User-Agent": "portman-kapi-a"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(r, timeout=25) as c:
                return c.status, c.read(), t0, time.time()
        except urllib.error.HTTPError as e:
            return e.code, e.read()[:200], t0, time.time()
        except Exception as e:
            return None, f"{type(e).__name__}: {str(e)[:80]}".encode(), t0, time.time()
    kod, govde, t0, t1 = istek("settings")
    print(f"   op=settings ({'çalışan süreçteki' if surec_tok else 'dosyadaki'} anahtarla): HTTP {kod}"
          + (" → hosting bu anahtarı ŞU AN kabul ediyor" if kod == 200 else " → kabul edilmedi" if kod == 401 else ""))
    if kod == 200:
        s = json.loads(govde)
        openai_var = bool(s.pop("openai_key", None)); govde = None
        pk = s.get("package") or {}
        print(f"   api {s.get('api')} · enabled {s.get('enabled')} · worker {s.get('worker')} · mode {s.get('mode')} · dry_run {s.get('dry_run')} · "
              f"vps_komut {s.get('vps_komut')} · llm {(s.get('llm') or {}).get('backend')}/{(s.get('llm') or {}).get('model')}")
        print(f"   hosting OpenAI anahtarını bu anahtarla veriyor mu: {'EVET' if openai_var else 'hayır'} (değer okunmadı)")
        print(f"   hosting paketi: {pk.get('surum')} · sha {str(pk.get('sha256'))[:16]} · {pk.get('size')} B · değişti {tarih(pk['mtime']) if pk.get('mtime') else '?'}")
        if isinstance(s.get("now"), int):
            print(f"   saat farkı (hosting − VPS): {s['now'] - round((t0 + t1) / 2):+d} sn (±{round(t1 - t0)} sn)")
        kod2, zipb, _, _ = istek("package")
        if kod2 == 200:
            zs = hashlib.sha256(zipb).hexdigest()
            print(f"   hosting'in verdiği paket: gerçek sha {zs[:16]} · settings'teki ile {'aynı' if zs == pk.get('sha256') else 'FARKLI'} · "
                  f"VPS'teki kurulu paketle {'aynı' if zs == pksha else 'FARKLI'}")
        else:
            print(f"   op=package: HTTP {kod2}")
    else:
        print(f"   cevap: {gizle(govde.decode(errors='replace'))[:160]}")

print("-- veri (yalnız sayılar)")
d = HOME / "data"
for ad, desen in (("gönderilemeyip bekleyen sonuç (data/pending)", "pending/*.json"), ("konuşma durumu (data/durum)", "durum/*.json")):
    print(f"   {ad}: {len(list(d.glob(desen)))}")
ot = d / "self-test-result.json"
if ot.exists():
    try:
        j = json.loads(ot.read_text()); print(f"   öz-test: {j.get('state')} · {j.get('finished_at')} · {j.get('sure_s')} sn")
    except Exception:
        print("   öz-test: okunamadı")

print("-- günlük (logs/agent.log; kimlik ve numaralar gizlenir)")
g = HOME / "logs" / "agent.log"
if g.exists():
    satirlar = g.read_text(errors="replace").splitlines()
    sinir = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 86400))
    son24 = [s for s in satirlar if s[:19] >= sinir]
    print(f"   toplam {len(satirlar)} satır · son 24 saat {len(son24)} · 'api:' hatası {sum(' api:' in s for s in son24)} · "
          f"'beklenmeyen' {sum('beklenmeyen' in s for s in son24)} · 'iş bitti' {sum('iş bitti' in s for s in son24)}")
    for s in [s for s in satirlar if " başladı " in s][-3:]:
        print("   " + gizle(s)[:160])
    hatalar = [s for s in son24 if " api:" in s or "beklenmeyen" in s]
    if hatalar:
        print("   son hata: " + gizle(hatalar[-1])[:160])
else:
    print("   agent.log yok")
PY
echo "== bitti"
