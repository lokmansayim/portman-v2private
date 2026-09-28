#!/usr/bin/env bash
# PORTMAN · SALT OKUNUR: ajan günlüğündeki 'api:' hatalarının zamanı, türü (HTTP kodu ya da bağlantı), işlemi ve hosting'in
# kısa hata kodu. Hiçbir şeyi değiştirmez. Anahtar, ham hata metni, numara ya da mesaj yazılmaz.
#   ssh root@<VPS> 'bash -s' < gunluk_api_hatalari.sh
# Test için: PM_GUNLUK (günlük yolu), PM_BASLANGIC ("YYYY-MM-DD HH:MM:SS"; varsayılan 28.09 20:00, A/C/D pencerelerini kapsar).
set -u
echo "== ajan günlüğü · 'api:' hataları · $(date '+%Y-%m-%d %H:%M:%S %Z') · sunucu saat dilimi $(timedatectl show -p Timezone --value 2>/dev/null || date +%Z)"
echo "   servis başlama anı: $(systemctl show portman-agent -p ActiveEnterTimestamp --value 2>/dev/null || echo '?')"
PM_GUNLUK="${PM_GUNLUK:-/opt/portman/logs/agent.log}" PM_BASLANGIC="${PM_BASLANGIC:-2026-09-28 20:00:00}" python3 - <<'PY'
import collections, json, os, re
from pathlib import Path
g = Path(os.environ["PM_GUNLUK"]); bas = os.environ["PM_BASLANGIC"]
satirlar = [s for s in g.read_text(errors="replace").splitlines() if s[:19] >= bas] if g.exists() else []
print(f"   günlük: {g} · {bas} sonrası {len(satirlar)} satır (zamanlar sunucunun yerel saatiyle; günlük aynı saati yazar)")

def cozumle(s):
    m = re.match(r"(\S+ \S+) api: (?:HTTP (\d{3}) (\w+): (.*)|bağlantı (\w+): (.*)|(.*))$", s)
    if not m:
        return s[:19], "?", "?", ""
    zaman, kod, op, govde, bop, neden, diger = m.groups()
    if kod:
        try:
            kisa = str(json.loads(govde).get("error", ""))
        except Exception:
            kisa = "json değil"
        return zaman, f"HTTP {kod}", op, re.sub(r"[^A-Za-zçğıöşüÇĞİÖŞÜ_ -]", "", kisa)[:30]
    if bop:
        return zaman, "bağlantı", bop, re.sub(r"[^A-Za-zçğıöşüÇĞİÖŞÜ _-]", "", neden)[:40]
    return zaman, "diğer", "-", re.sub(r"[^A-Za-zçğıöşüÇĞİÖŞÜ _-]", "", diger or "")[:40]

olaylar = []
for s in satirlar:
    if " api:" in s:
        olaylar.append(("hata",) + cozumle(s))
    elif " başladı " in s:
        olaylar.append(("başladı", s[:19], "", "", ""))
    elif " beklenmeyen" in s:
        olaylar.append(("beklenmeyen", s[:19], "", "", ""))
for tur, zaman, sinif, op, kisa in olaylar:
    print(f"   {zaman} · " + (f"api: {sinif} · işlem {op} · {kisa}" if tur == "hata" else tur))
baslamalar = [z for t, z, *_ in olaylar if t == "başladı"]
son = baslamalar[-1] if baslamalar else None
hatalar = [(z, s, o, k) for t, z, s, o, k in olaylar if t == "hata"]
once = [h for h in hatalar if son and h[0] < son]; sonra = [h for h in hatalar if not son or h[0] >= son]
print(f"   özet: toplam {len(hatalar)} 'api:' hatası · son başlamadan ({son or '-'}) önce {len(once)}, sonra {len(sonra)}")
for ad, grup in (("önce", once), ("sonra", sonra)):
    if grup:
        say = collections.Counter(f"{s} {o} {k}".strip() for _, s, o, k in grup)
        print(f"   {ad}: " + "; ".join(f"{k} × {n}" for k, n in say.most_common()) + f" · ilk {grup[0][0]} · son {grup[-1][0]}")
PY
echo "== bitti"
